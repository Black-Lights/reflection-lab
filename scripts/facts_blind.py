"""One blind FACTS judging sheet across several bench_facts runs, split into parts for several judges.

    python scripts/facts_blind.py --runs runs/bench_facts_A runs/bench_facts_B --parts 3
        -> runs/facts_blind_<stamp>/part_1.md ... + template_part_1.jsonl ... + key.json (do not open while judging)
    python scripts/facts_blind.py --merge runs/facts_blind_<stamp>
        -> fills judgments.jsonl in every source run (blank one kept as judgments_blank.jsonl) and scores each run

Each example shows the request and the context document once, then every distinct response from all runs and
variants (baseline, loop) under a shuffled letter. Identical texts are shown once and judged once. The judge
cannot tell which model or variant wrote a response. Judges fill eligible / grounded (true or false) and a
short note per letter in judgments_part_<k>.jsonl (a copy of the template).
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_facts import CRITERIA, score  # noqa: E402
from lab.common import ROOT, RUNS, fail, ok, read_json, read_jsonl, rel_to_root, stamp, write_json  # noqa: E402


def shown_texts(run: Path) -> dict[str, dict[str, str]]:
    """{example id: {response number shown in that run's sheet: text}} using the run's own key."""
    key = read_json(run / "judging_key.json", {})
    out = {}
    for r in read_jsonl(run / "results.jsonl"):
        texts = {}
        for n, variant in key.get(r["id"], {}).items():
            texts[n] = r["final"] if variant == "loop" else r["baseline"]
        out[r["id"]] = texts
    return out


def build(runs: list[Path], parts: int, seed: int) -> None:
    subset = {c["id"]: c for c in read_jsonl(ROOT / "tests" / "facts_subset.jsonl")}
    per_run = {r.name: shown_texts(r) for r in runs}
    ids = [i for i in subset if any(i in t for t in per_run.values())]
    rng = random.Random(seed)
    out = RUNS / f"facts_blind_{stamp()}"
    out.mkdir(parents=True)
    key, examples = {}, []
    for i in ids:
        texts = []
        for t in per_run.values():
            for txt in t.get(i, {}).values():
                if txt is not None and txt not in texts:
                    texts.append(txt)
        rng.shuffle(texts)
        letters = dict(zip(string.ascii_uppercase, texts))
        key[i] = letters
        examples.append((i, letters))
    # split into parts of about equal reading length
    sizes = [len(subset[i]["context_document"]) + sum(len(t) for t in L.values()) for i, L in examples]
    target, k, acc = sum(sizes) / parts, 1, 0.0
    part_of = {}
    for (i, _), s in zip(examples, sizes):
        if acc >= target * k and k < parts:
            k += 1
        part_of[i] = k
        acc += s
    for p in range(1, parts + 1):
        L = ["# FACTS Grounding, blind judging sheet, part " + str(p), "", CRITERIA.replace(
            "Record the verdicts in `judgments.jsonl`", f"Record the verdicts in `judgments_part_{p}.jsonl`").replace(
            "then run\n`python scripts/bench_facts.py --score <this folder>`", "one line per response letter"), "",
            "Every response is judged on its own. Responses are labelled A, B, C in random order.", "", "## Examples", ""]
        tmpl = []
        for n, (i, letters) in enumerate([e for e in examples if part_of[e[0]] == p], 1):
            c = subset[i]
            L += ["---", "", f"### {n}. {i}", "", f"**System instruction:** {c['system_instruction']}", "",
                  f"**User request:** {c['user_request']}", "",
                  f"**Context document** ({len(c['context_document'].split())} words):", "", "~~~~text",
                  c["context_document"], "~~~~", ""]
            for letter, txt in letters.items():
                L += [f"**Response {letter}:**", "", "~~~~text", txt, "~~~~", ""]
                tmpl.append({"id": i, "response": letter, "eligible": None, "grounded": None, "note": ""})
        (out / f"part_{p}.md").write_text("\n".join(L), encoding="utf-8")
        with open(out / f"template_part_{p}.jsonl", "w", encoding="utf-8") as f:
            for t in tmpl:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
    write_json(out / "key.json", {"runs": [rel_to_root(r) for r in runs], "seed": seed, "texts": key})
    ok(f"wrote {out}: {len(examples)} examples, {sum(len(L) for L in key.values())} distinct responses, {parts} parts")
    for p in range(1, parts + 1):
        print(f"  part {p}: {sum(1 for v in part_of.values() if v == p)} examples, "
              f"{(out / f'part_{p}.md').stat().st_size / 1e3:.0f} kB")


def merge(blind: Path) -> None:
    meta = read_json(blind / "key.json", {})
    judged = {}
    for p in sorted(blind.glob("judgments_part_*.jsonl")):
        for j in read_jsonl(p):
            if j.get("eligible") is not None and j.get("grounded") is not None:
                judged[(j["id"], meta["texts"][j["id"]][j["response"]])] = j
    if not judged:
        fail("no filled judgments_part_*.jsonl lines")
        sys.exit(1)
    for rel in meta["runs"]:
        run = ROOT / rel
        blank = run / "judgments_blank.jsonl"
        if not blank.exists():
            shutil.copy(run / "judgments.jsonl", blank)
        rows, missing = [], 0
        for t in read_jsonl(blank):
            txt = shown_texts(run)[t["id"]].get(str(t["response"]))
            j = judged.get((t["id"], txt))
            if j:
                t.update(eligible=j["eligible"], grounded=j["grounded"], note=j.get("note", ""))
            else:
                missing += 1
            rows.append(t)
        with open(run / "judgments.jsonl", "w", encoding="utf-8") as f:
            for t in rows:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        print(f"\n{run.name}: {len(rows) - missing} judged, {missing} missing")
        score(run)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", help="bench_facts run folders to combine")
    ap.add_argument("--parts", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--merge", help="facts_blind folder with filled judgments_part_*.jsonl")
    args = ap.parse_args()
    if args.merge:
        merge(Path(args.merge))
    elif args.runs:
        build([Path(r) for r in args.runs], args.parts, args.seed)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
