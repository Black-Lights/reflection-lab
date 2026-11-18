"""Find numbers a model wrote that appear in none of the texts it was given (FACTS runs, no model needed).

    python scripts/facts_numbers.py runs/bench_facts_<stamp> [runs/bench_facts_<stamp> ...]
    python scripts/facts_numbers.py runs/bench_facts_<stamp> --out reports/facts_numbers.md

FACTS answers copy figures from the context document and almost never calculate, so a number in an output
that is in none of that call's inputs is nearly always a copying error. The inputs per stage:
  baseline  the context document (plus system instruction and user request)
  audit     the document and the baseline draft
  final     the document, the draft and the audit
Integers up to 12 are ignored (list numbering, "three" written as 3). Also counted: malformed figures with
two decimal points ("149.9.95"), doubled percent signs and doubled words ("the the").
Reads calls.jsonl (output and prompt length per call) and tests/facts_subset.jsonl (the documents).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import ROOT  # noqa: E402

NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*")
MALFORMED = re.compile(r"\d\.\d+\.\d|%%")
DOUBLE_WORD = re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.I)
STAGES = ("baseline", "audit", "final")


def numbers(text: str) -> list[str]:
    out = []
    for m in NUM.finditer(text or ""):
        n = m.group(0).rstrip(".,").replace(",", "")
        if n and not (n.isdigit() and int(n) <= 12):
            out.append(n)
    return out


def inputs_for(stage: str, item: dict, doc: str) -> str:
    base = " ".join([doc, item.get("system_instruction", ""), item.get("user_request", "")])
    if stage == "baseline":
        return base
    if stage == "audit":
        return base + " " + item.get("baseline", "")
    return base + " " + item.get("baseline", "") + " " + (item.get("audit") or "")


def context(text: str, token: str, width: int = 45) -> str:
    i = text.find(token)
    if i < 0:
        return token
    s = text[max(0, i - width): i + len(token) + width].replace("\n", " ")
    return "..." + s + "..."


def analyse(run: Path, docs: dict) -> dict:
    items = {x["id"]: x for x in map(json.loads, (run / "results.jsonl").open(encoding="utf-8"))}
    calls = [json.loads(l) for l in (run / "calls.jsonl").open(encoding="utf-8")]
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    rows = []
    for c in calls:
        stage = c["field"]
        if stage not in STAGES or c.get("output") is None:
            continue
        item, doc = items[c["id"]], docs[c["id"]]
        allowed = set(numbers(inputs_for(stage, item, doc)))
        allowed |= {n.split(".")[0] for n in allowed}  # "June 2018.76" (footnote glued on) still allows 2018
        found = numbers(c["output"])
        novel = [n for n in found if n not in allowed]
        rows.append({
            "id": c["id"], "stage": stage, "prompt_chars": int(c.get("prompt_chars") or 0),
            "n_numbers": len(found), "novel": novel,
            "novel_ctx": [context(c["output"], n) for n in novel],
            "malformed": MALFORMED.findall(c["output"]),
            "double_words": [m.group(0) for m in DOUBLE_WORD.finditer(c["output"])],
        })
    a = meta["args"]
    label = a["model"] + (f" + {a['critic']} critic" if a.get("critic") else "")
    return {"run": run.name, "label": label, "rows": rows}


def summarise(res: dict) -> list[dict]:
    by = defaultdict(list)
    for r in res["rows"]:
        by[r["stage"]].append(r)
    out = []
    for stage in STAGES:
        rs = by.get(stage)
        if not rs:
            continue
        nums = sum(r["n_numbers"] for r in rs)
        novel = sum(len(r["novel"]) for r in rs)
        out.append({
            "stage": stage, "calls": len(rs), "numbers": nums, "novel": novel,
            "novel_pct": 100 * novel / nums if nums else 0.0,
            "calls_with_novel": sum(1 for r in rs if r["novel"]),
            "malformed": sum(len(r["malformed"]) for r in rs),
            "double_words": sum(len(r["double_words"]) for r in rs),
            "median_prompt_chars": sorted(r["prompt_chars"] for r in rs)[len(rs) // 2],
        })
    return out


def by_length(rows: list[dict], edges=(4000, 8000, 12000)) -> list[tuple[str, int, int, int]]:
    bins = []
    lo = 0
    for hi in list(edges) + [10 ** 9]:
        rs = [r for r in rows if lo <= r["prompt_chars"] < hi]
        name = f"{lo:,} to {hi:,}" if hi < 10 ** 9 else f"{lo:,} and over"
        bins.append((name, len(rs), sum(r["n_numbers"] for r in rs), sum(len(r["novel"]) for r in rs)))
        lo = hi
    return bins


def report(results: list[dict]) -> str:
    L = ["# Numbers that appear in none of the model's inputs (FACTS runs)", "",
         "Made by `scripts/facts_numbers.py`. A *novel* number is one the model wrote that is in none of the texts",
         "that call received (see the script's help for the inputs per stage). Integers up to 12 are ignored.", ""]
    all_rows = []
    for res in results:
        L += [f"## {res['label']} · `{res['run']}`", "",
              "| stage | calls | numbers written | novel | novel % | calls with a novel number | malformed | doubled words | median prompt chars |",
              "|---|---|---|---|---|---|---|---|---|"]
        for s in summarise(res):
            L.append(f"| {s['stage']} | {s['calls']} | {s['numbers']} | {s['novel']} | {s['novel_pct']:.1f} | "
                     f"{s['calls_with_novel']} | {s['malformed']} | {s['double_words']} | {s['median_prompt_chars']:,} |")
        L.append("")
        all_rows += res["rows"]
        flagged = [r for r in res["rows"] if r["novel"] or r["malformed"] or r["double_words"]]
        if flagged:
            L += ["Every flagged output:", ""]
            for r in flagged:
                bits = [f"`{n}` {c}" for n, c in zip(r["novel"], r["novel_ctx"])]
                bits += [f"malformed `{m}`" for m in r["malformed"]]
                bits += [f"doubled `{d}`" for d in r["double_words"]]
                L.append(f"- {r['id']} {r['stage']} ({r['prompt_chars']:,} prompt chars): " + "; ".join(bits))
            L.append("")
    L += ["## By prompt length (all runs and stages together)", "",
          "| prompt chars | calls | numbers written | novel | novel % |", "|---|---|---|---|---|"]
    for name, calls, nums, novel in by_length(all_rows):
        L.append(f"| {name} | {calls} | {nums} | {novel} | {100 * novel / nums if nums else 0:.1f} |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", type=Path, help="runs/bench_facts_<stamp> folders")
    ap.add_argument("--subset", type=Path, default=ROOT / "tests" / "facts_subset.jsonl")
    ap.add_argument("--out", type=Path, help="write the markdown report here (default: print it)")
    args = ap.parse_args()
    docs = {x["id"]: x["context_document"] for x in map(json.loads, args.subset.open(encoding="utf-8"))}
    text = report([analyse(r, docs) for r in args.runs])
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
