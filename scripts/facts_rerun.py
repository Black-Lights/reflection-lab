"""Rerun the FACTS calls that corrupted numbers, on another backend or context size, and compare.

    python scripts/facts_rerun.py runs/bench_facts_<stamp> --backend cpu          the diagnostic (slow, ~5 GB RAM)
    python scripts/facts_rerun.py runs/bench_facts_<stamp> --backend gpu          same settings: is it reproducible?
    python scripts/facts_rerun.py runs/bench_facts_<stamp> --max-num-tokens 8192  more KV cache room on the GPU
    python scripts/facts_rerun.py runs/bench_facts_<stamp> --runtime fake         test the script, no model

Which calls: by default every call in that run whose output has a number found in none of its inputs or a
malformed figure (scripts/facts_numbers.py), plus --controls clean calls with long prompts (8,000+ characters)
so that a backend that adds new errors is noticed too. --ids facts_428:final,facts_105:audit picks calls by hand.
Each prompt is rebuilt exactly as bench_facts.py built it (dataset full_prompt for the draft; the run's own
prompts/critic.txt and prompts/refiner.txt for the audit and the rewrite) and checked against the logged
prompt length. Decoding settings come from the original run's meta.json (greedy, seed, output limit).
Bench calls never stream (run_stage passes no token callback), so streaming is not a factor.

Output: runs/facts_rerun_<stamp>/ with meta.json, calls.jsonl and report.md: per call the novel numbers
before and after, and whether the text is identical to the original.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.bench_common import load_llm, md_table, run_stage  # noqa: E402
from lab.common import ROOT, RUNS, fail, load_config, ok, stamp, warn, write_json  # noqa: E402
from run_experiment import fill  # noqa: E402  (bench_common put scripts/ on the path)

sys.path.insert(0, str(ROOT / "scripts"))
import facts_numbers as FN  # noqa: E402


def build_prompt(stage: str, item: dict, src: dict, tpl: dict) -> str:
    if stage == "baseline":
        return src["full_prompt"]
    doc, q = src["context_document"], src["user_request"]
    if stage == "audit":
        return fill(tpl["critic.txt"], document=doc, question=q, draft=item["baseline"])
    return fill(tpl["refiner.txt"], document=doc, question=q, draft=item["baseline"], audit=item["audit"])


def pick(run: Path, docs: dict, ids: str | None, controls: int) -> list[dict]:
    rows = FN.analyse(run, docs)["rows"]
    if ids:
        want = {tuple(x.split(":")) for x in ids.split(",")}
        return [r for r in rows if (r["id"], r["stage"]) in want]
    bad = [r for r in rows if r["novel"] or r["malformed"]]
    clean = sorted((r for r in rows if not (r["novel"] or r["malformed"] or r["double_words"])
                    and r["prompt_chars"] >= 8000 and r["n_numbers"] > 0),
                   key=lambda r: -r["prompt_chars"])[:controls]
    for r in clean:
        r["control"] = True
    return bad + clean


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path, help="the runs/bench_facts_<stamp> folder to rerun calls from")
    ap.add_argument("--backend", choices=["cpu", "gpu"], default="cpu")
    ap.add_argument("--runtime", default="python", help="python (LiteRT-LM) or fake (no model)")
    ap.add_argument("--max-num-tokens", type=int, default=0, help="context size; 0 keeps the original run's")
    ap.add_argument("--ids", help="id:stage pairs, comma separated (default: every corrupted call)")
    ap.add_argument("--controls", type=int, default=4, help="clean long-prompt calls to add (default 4)")
    ap.add_argument("--subset", type=Path, default=ROOT / "tests" / "facts_subset.jsonl")
    args = ap.parse_args()

    run = args.run if args.run.is_absolute() else ROOT / args.run
    meta0 = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    src = {x["id"]: x for x in map(json.loads, args.subset.open(encoding="utf-8"))}
    docs = {k: v["context_document"] for k, v in src.items()}
    items = {x["id"]: x for x in map(json.loads, (run / "results.jsonl").open(encoding="utf-8"))}
    tpl = {f: (run / "prompts" / f).read_text(encoding="utf-8") for f in ("critic.txt", "refiner.txt")} \
        if (run / "prompts").exists() else {}
    originals = {(c["id"], c["field"]): c for c in map(json.loads, (run / "calls.jsonl").open(encoding="utf-8"))}

    chosen = pick(run, docs, args.ids, args.controls)
    if not chosen:
        fail("no calls selected")
        sys.exit(1)
    if any(r["stage"] != "baseline" for r in chosen) and not tpl:
        fail(f"{run} has no prompts/ folder, so audits and rewrites cannot be rebuilt")
        sys.exit(1)

    a0 = meta0["args"]
    calls = []
    for r in chosen:
        prompt = build_prompt(r["stage"], items[r["id"]], src[r["id"]], tpl)
        logged = int(originals[(r["id"], r["stage"])].get("prompt_chars") or 0)
        if logged and len(prompt) != logged:
            warn(f"{r['id']} {r['stage']}: rebuilt prompt is {len(prompt)} chars, the run logged {logged}")
        calls.append({"id": f"{r['id']}:{r['stage']}", "item": r["id"], "stage": r["stage"], "prompt": prompt,
                      "model": a0["critic"] if r["stage"] == "audit" else a0["model"],
                      "control": r.get("control", False), "before": r})

    cfg = load_config()
    gen = dict(meta0["generation"])
    if args.max_num_tokens:
        gen["max_num_tokens"] = args.max_num_tokens
    out = RUNS / f"facts_rerun_{stamp()}"
    out.mkdir(parents=True)
    write_json(out / "meta.json", {"bench": "facts_rerun", "source_run": run.name, "args": {**vars(args),
               "run": str(args.run), "subset": str(args.subset)}, "generation": gen,
               "calls": [c["id"] for c in calls], "started": time.strftime("%Y-%m-%d %H:%M:%S")})
    ok(f"{len(calls)} calls ({sum(c['control'] for c in calls)} controls) -> {out}")

    for key in dict.fromkeys(c["model"] for c in calls):
        group = [c for c in calls if c["model"] == key]
        llm = load_llm(cfg, args.runtime, key, args.backend, gen)
        try:
            run_stage(llm, group, lambda c: c["prompt"], "output", gen, out / "calls.jsonl",
                      f"{key} {args.backend}")
        finally:
            llm.close()

    rows, tot = [], {"before": 0, "after": 0, "same": 0}
    for c in calls:
        b = c["before"]
        allowed = set(FN.numbers(FN.inputs_for(c["stage"], items[c["item"]], docs[c["item"]])))
        allowed |= {n.split(".")[0] for n in allowed}
        text = c.get("output") or ""
        after = [n for n in FN.numbers(text) if n not in allowed] + FN.MALFORMED.findall(text)
        before = b["novel"] + b["malformed"]
        same = text.strip() == (originals[(c["item"], c["stage"])]["output"] or "").strip()
        tot["before"] += len(before)
        tot["after"] += len(after)
        tot["same"] += same
        rows.append([c["id"] + (" (control)" if c["control"] else ""), f"{len(c['prompt']):,}",
                     ", ".join(before) or "none", ", ".join(after) or "none", "yes" if same else "no",
                     f"{c.get('timings', {}).get('output', 0):.0f}"])
    head = (f"# FACTS rerun · {args.backend.upper()}" + (f", max_num_tokens {args.max_num_tokens}" if
            args.max_num_tokens else "") + f" · from `{run.name}`\n\n"
            f"Made by `scripts/facts_rerun.py`. Runtime `{args.runtime}`, greedy, settings of the original run.\n\n"
            f"- corrupted or novel numbers: {tot['before']} in the original calls, {tot['after']} in the rerun\n"
            f"- outputs identical to the original: {tot['same']} of {len(calls)}\n\n")
    (out / "report.md").write_text(head + md_table(
        ["call", "prompt chars", "novel before", "novel after", "identical", "seconds"], rows) + "\n",
        encoding="utf-8")
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta.update(totals=tot, finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    write_json(out / "meta.json", meta)
    ok(f"novel numbers {tot['before']} -> {tot['after']}; identical {tot['same']}/{len(calls)}; {out / 'report.md'}")


if __name__ == "__main__":
    main()
