"""Turn a labelled run into numbers: did the critic loop reduce hallucinations?

    python scripts/report.py                   latest run
    python scripts/report.py --run runs/<dir>
    python scripts/report.py --compare runs/<dirA> runs/<dirB>   side-by-side of two labelled runs

Writes report.md into the run folder. Statistics:
  - rates with Wilson 95% confidence intervals
  - McNemar exact test on the paired baseline vs final outcomes (same questions)
  - critic precision/recall: did it flag the drafts that were actually wrong?
With ~30 cases this is a pilot: intervals are wide, look at the direction and the examples.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import HAVE_RICH, console, fail, latest_run_dir, read_json, read_jsonl  # noqa: E402

NAMES = {"c": "correct", "h": "hallucination", "i": "incomplete", "r": "wrong refusal"}
CRITIC_NAMES = {"y": "right", "f": "false alarm", "m": "missed problem", "x": "mixed"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for b vs c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cdf = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * cdf)


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def analyse(run_dir: Path) -> dict:
    state = read_json(run_dir / "state.json", {})
    labels = {r["id"]: r for r in read_jsonl(run_dir / "labels.jsonl")}
    meta = read_json(run_dir / "meta.json", {})
    ids = [i for i in meta.get("case_ids", list(state)) if i in labels]
    n = len(ids)
    res = {"run": run_dir.name, "n": n, "meta": meta, "cond": {}, "by_cat": {}, "labellers": {}}
    for i in ids:  # label.py writes no "labeller" field, so a missing one means the owner labelled
        who = labels[i].get("labeller", "owner (label.py)")
        res["labellers"][who] = res["labellers"].get(who, 0) + 1
    for cond in ("baseline", "final"):
        counts = {k: 0 for k in NAMES}
        for i in ids:
            counts[labels[i]["labels"][cond]] += 1
        res["cond"][cond] = counts

    # paired tests
    def paired(flag):
        b = sum(1 for i in ids if flag(labels[i]["labels"]["baseline"]) and not flag(labels[i]["labels"]["final"]))
        c = sum(1 for i in ids if not flag(labels[i]["labels"]["baseline"]) and flag(labels[i]["labels"]["final"]))
        return b, c, mcnemar_exact(b, c)

    res["halluc_pair"] = paired(lambda x: x == "h")  # (fixed, introduced, p)
    res["correct_pair"] = paired(lambda x: x != "c")  # (became correct, became wrong, p)

    # per category
    for i in ids:
        cat = state[i].get("category", "?")
        d = res["by_cat"].setdefault(cat, {"n": 0, "baseline_h": 0, "final_h": 0, "baseline_c": 0, "final_c": 0})
        d["n"] += 1
        for cond in ("baseline", "final"):
            lab = labels[i]["labels"][cond]
            d[f"{cond}_h"] += lab == "h"
            d[f"{cond}_c"] += lab == "c"

    # critic: did it flag drafts that were not correct?
    tp = fp = fn = tn = 0
    for i in ids:
        flagged = state[i].get("audit_verdict") in ("ISSUES", "UNPARSED")
        wrong = labels[i]["labels"]["baseline"] != "c"
        tp += flagged and wrong
        fp += flagged and not wrong
        fn += (not flagged) and wrong
        tn += (not flagged) and (not wrong)
    res["critic"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                     "precision": tp / (tp + fp) if tp + fp else None,
                     "recall": tp / (tp + fn) if tp + fn else None,
                     "self_rated": {}}
    for i in ids:
        cr = labels[i].get("critic")
        if cr:
            res["critic"]["self_rated"][cr] = res["critic"]["self_rated"].get(cr, 0) + 1

    # refiner effect on refined cases
    refined = [i for i in ids if state[i].get("refined")]
    res["refiner"] = {
        "refined": len(refined),
        "fixed": sum(1 for i in refined if labels[i]["labels"]["baseline"] != "c" and labels[i]["labels"]["final"] == "c"),
        "broke": sum(1 for i in refined if labels[i]["labels"]["baseline"] == "c" and labels[i]["labels"]["final"] != "c"),
    }

    # timings
    t = {1: [], 2: [], 3: []}
    for i in ids:
        for s in (1, 2, 3):
            v = state[i].get("timings", {}).get(f"stage{s}")
            if v is not None and not (s == 3 and not state[i].get("refined")):
                t[s].append(v)
    res["timing"] = {s: (sum(v) / len(v) if v else None) for s, v in t.items()}
    per_case_loop = [sum(state[i].get("timings", {}).values()) for i in ids]
    res["timing"]["loop_per_case"] = sum(per_case_loop) / len(per_case_loop) if per_case_loop else None
    res["examples"] = {
        "fixed": [i for i in ids if labels[i]["labels"]["baseline"] == "h" and labels[i]["labels"]["final"] != "h"],
        "introduced": [i for i in ids if labels[i]["labels"]["baseline"] != "h" and labels[i]["labels"]["final"] == "h"],
        "became_correct": [f"{i} ({labels[i]['labels']['baseline']}→c)" for i in ids
                           if labels[i]["labels"]["baseline"] != "c" and labels[i]["labels"]["final"] == "c"],
        "became_wrong": [f"{i} (c→{labels[i]['labels']['final']})" for i in ids
                         if labels[i]["labels"]["baseline"] == "c" and labels[i]["labels"]["final"] != "c"],
    }
    return res


def to_markdown(r: dict) -> str:
    n = r["n"]
    L = [f"# Report · {r['run']}", ""]
    roles = r["meta"].get("roles", {})
    L.append(f"Analyst: **{roles.get('analyst', {}).get('key')}** · Critic: **{roles.get('critic', {}).get('key')}** · "
             f"runtime {r['meta'].get('runtime')} · {n} labelled cases")
    L.append("")
    L.append("Labelled by: " + "; ".join(f"{who} ({k} cases)" for who, k in r.get("labellers", {}).items()))
    vs = r["meta"].get("generation", {}).get("verdict_source", "issue_lines (older runs)")
    L.append(f"Critic verdict rule: `{vs}`")
    L += ["", "## Outcomes", "", "| | Single model (baseline) | With critic loop (final) |", "|---|---|---|"]
    for k, name in NAMES.items():
        cells = []
        for cond in ("baseline", "final"):
            x = r["cond"][cond][k]
            lo, hi = wilson(x, n)
            cells.append(f"{x}/{n} = {pct(x / n) if n else '-'} (95% CI {pct(lo)}–{pct(hi)})")
        L.append(f"| {name} | {cells[0]} | {cells[1]} |")
    fixed, introduced, p = r["halluc_pair"]
    L += ["", "## Is the difference real?", "",
          f"- Hallucinations removed by the loop: **{fixed}**, introduced by the loop: **{introduced}** "
          f"(McNemar exact p = {p:.3f})",
          f"- Answers that became correct: **{r['correct_pair'][0]}**, became not-correct: **{r['correct_pair'][1]}** "
          f"(p = {r['correct_pair'][2]:.3f})",
          "- p < 0.05 means the difference is unlikely to be luck. With ~30 cases expect wide intervals: "
          "grow the test set before drawing conclusions."]
    c = r["critic"]
    prec = f"{pct(c['precision'])}" if c["precision"] is not None else "-"
    rec = f"{pct(c['recall'])}" if c["recall"] is not None else "-"
    L += ["", "## Critic (Stage 2)", "",
          f"- Flagged {c['tp'] + c['fp']} drafts; {c['tp']} of them were really wrong → precision {prec}",
          f"- Of {c['tp'] + c['fn']} wrong drafts it caught {c['tp']} → recall {rec}",
          f"- False alarms: {c['fp']}, missed: {c['fn']}",
          "- Labeller's rating of the audits: " +(", ".join(f"{CRITIC_NAMES.get(k, k)} {v}" for k, v in c["self_rated"].items()) or "-")]
    f = r["refiner"]
    L += ["", "## Refiner (Stage 3)", "",
          f"- Refined {f['refined']} cases: fixed {f['fixed']}, broke {f['broke']}"]
    L += ["", "## By category", "", "| Category | n | Halluc. baseline | Halluc. final | Correct baseline | Correct final |",
          "|---|---|---|---|---|---|"]
    for cat, d in sorted(r["by_cat"].items()):
        L.append(f"| {cat} | {d['n']} | {d['baseline_h']} | {d['final_h']} | {d['baseline_c']} | {d['final_c']} |")
    t = r["timing"]
    fmt = lambda v: f"{v:.1f}s" if v is not None else "-"  # noqa: E731
    L += ["", "## Speed (PC)", "",
          f"- Stage 1 {fmt(t[1])} · Stage 2 {fmt(t[2])} · Stage 3 {fmt(t[3])} (avg per call)",
          f"- Whole loop per case: {fmt(t['loop_per_case'])} vs single model {fmt(t[1])}"]
    if r["meta"].get("peak_vram_mb"):
        L.append(f"- Peak VRAM {r['meta']['peak_vram_mb'] / 1024:.1f} GB · peak RAM used {r['meta'].get('peak_ram_used_gb')} GB")
    ex = r["examples"]
    L += ["", "## Look at these cases", "",
          f"- Hallucination fixed by the loop: {', '.join(ex['fixed']) or '-'}",
          f"- Hallucination introduced by the loop: {', '.join(ex['introduced']) or '-'}",
          f"- Made correct by the loop: {', '.join(ex.get('became_correct', [])) or '-'}",
          f"- Made worse by the loop: {', '.join(ex.get('became_wrong', [])) or '-'}",
          "", "Labels: c correct, h hallucination, i incomplete, r wrong refusal. "
          "Open transcript.md in the run folder to read them."]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="")
    ap.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    args = ap.parse_args()

    if args.compare:
        rows = [analyse(Path(p)) for p in args.compare]
        console.rule("Comparison")
        for r in rows:
            n = r["n"] or 1
            console.print(f"{r['run']}: baseline halluc {r['cond']['baseline']['h']}/{r['n']} ({pct(r['cond']['baseline']['h']/n)}), "
                          f"final halluc {r['cond']['final']['h']}/{r['n']} ({pct(r['cond']['final']['h']/n)}), "
                          f"critic precision {r['critic']['precision']}, recall {r['critic']['recall']}")
        return

    run_dir = Path(args.run) if args.run else latest_run_dir()
    if not run_dir or not (run_dir / "labels.jsonl").exists():
        fail("No labels found. Run scripts/label.py first.")
        sys.exit(1)
    r = analyse(run_dir)
    if r["n"] == 0:
        fail("No labelled cases yet.")
        sys.exit(1)
    md = to_markdown(r)
    (run_dir / "report.md").write_text(md, encoding="utf-8")
    if HAVE_RICH:
        from rich.markdown import Markdown

        console.print(Markdown(md))
    else:
        print(md)
    console.print(f"\nSaved: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
