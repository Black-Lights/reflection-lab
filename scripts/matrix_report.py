"""Compare all runs of a matrix: single model (baseline) vs critic loop (final), per case set.

    python scripts/matrix_report.py --index runs/matrix_<stamp>/index.json
    python scripts/matrix_report.py --runs runs/<A> runs/<B> ...      any labelled runs

Uses each run's labels.jsonl (manual, or written by autoscore.py --apply). Sets are told apart by case id:
starter (a/n/t/c/m + digits), hard (h...), fresh (f...). Writes report.md next to index.json (with --runs only: reports/report.md).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import console, fail, from_root, ok, read_json, read_jsonl  # noqa: E402
from report import mcnemar_exact  # noqa: E402  (scripts/report.py)


def set_of(cid: str) -> str:
    return "hard" if cid.startswith("h") else "fresh" if cid.startswith("f") else "starter"


def summarise(run: Path) -> dict | None:
    labels = {r["id"]: r for r in read_jsonl(run / "labels.jsonl")}
    if not labels:
        return None
    meta, state = read_json(run / "meta.json", {}), read_json(run / "state.json", {})
    out = {"run": run.name, "analyst": meta["roles"]["analyst"]["key"], "critic": meta["roles"]["critic"]["key"],
           "prompts": meta.get("prompts", "prompts"), "sets": {}}
    for cid, r in labels.items():
        s = out["sets"].setdefault(set_of(cid), {"n": 0, "base": {}, "final": {}, "fixed": 0, "broke": 0,
                                                 "refined": 0, "flagged": 0})
        s["n"] += 1
        b, f = r["labels"]["baseline"], r["labels"]["final"]
        s["base"][b] = s["base"].get(b, 0) + 1
        s["final"][f] = s["final"].get(f, 0) + 1
        s["fixed"] += b != "c" and f == "c"
        s["broke"] += b == "c" and f != "c"
        s["h_removed"] = s.get("h_removed", 0) + (b == "h" and f != "h")
        s["h_added"] = s.get("h_added", 0) + (b != "h" and f == "h")
        s["refined"] += bool(state.get(cid, {}).get("refined"))
        s["flagged"] += state.get(cid, {}).get("audit_verdict") in ("ISSUES", "UNPARSED")
    secs = [sum(v.get("timings", {}).values()) for v in state.values()]
    out["sec_per_case"] = sum(secs) / len(secs) if secs else 0
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index")
    ap.add_argument("--runs", nargs="*", default=[])
    args = ap.parse_args()
    runs = [Path(p) for p in args.runs]
    out_dir = Path(__file__).resolve().parent.parent / "reports"  # --runs only: write to reports/
    if args.index:
        idx = read_json(Path(args.index), {})
        runs += [from_root(idx["runs"][c]) for c in idx["configs"] if c in idx.get("runs", {})]
        out_dir = Path(args.index).parent
    rows = [s for s in (summarise(r) for r in runs) if s]
    if not rows:
        fail("No labelled runs found.")
        sys.exit(1)

    L = ["# Combination matrix", "", "c = correct, h = hallucination. 'single' = the analyst alone (stage 1), "
         "'loop' = after critic + refine. fixed/broke = answers the loop made correct / not correct.", ""]
    for setname in ("all", "starter", "hard", "fresh"):
        L += [f"## {setname}", "", "| analyst | critic | prompts | n | single c | loop c | single h | loop h | "
              "fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            parts = [v for k, v in r["sets"].items() if setname in ("all", k)]
            if not parts:
                continue
            g = lambda key, lab=None: sum((p[key].get(lab, 0) if lab else p[key]) for p in parts)  # noqa: E731
            n, fixed, broke = g("n"), g("fixed"), g("broke")
            L.append(f"| {r['analyst']} | {r['critic']} | {r['prompts']} | {n} | {g('base', 'c')} | {g('final', 'c')} | "
                     f"{g('base', 'h')} | {g('final', 'h')} | {fixed} | {broke} | {mcnemar_exact(fixed, broke):.3f} | "
                     f"{g('h_removed')} | {g('h_added')} | {mcnemar_exact(g('h_removed'), g('h_added')):.3f} | "
                     f"{g('flagged')} | {r['sec_per_case']:.1f} |")
        L.append("")
    text = "\n".join(L)
    (out_dir / "report.md").write_text(text, encoding="utf-8")
    console.print(text)
    ok(f"wrote {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
