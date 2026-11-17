"""Blind labelling of a run's answers (you are the judge).

    python scripts/label.py                    label the latest run
    python scripts/label.py --run runs/<dir>   label a specific run
    python scripts/label.py --redo t03         re-label one case
    python scripts/label.py --no-critic        skip the critic-quality question

For each case you see the document, the question and the reference answer, then
two answers, "A" and "B", in random order: one is the single-model baseline, the
other is the final answer after the critic loop. You don't know which is which.

Labels for each answer
  c  correct      everything stated is supported by the document, nothing important missing
  h  hallucination  states something not in, or contradicting, the document (incl. inventing an
                    answer when the document doesn't say)
  i  incomplete   nothing false, but misses part of what was asked
  r  wrong refusal  says "the document does not say" although it does
Progress is saved after every case; press q to stop and continue later.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    HAVE_RICH, ROOT, append_jsonl, console, fail, latest_run_dir, ok, read_json, read_jsonl, write_json,
)

LABELS = {"c": "correct", "h": "hallucination", "i": "incomplete", "r": "wrong refusal"}
CRITIC = {"y": "critic right", "f": "false alarm", "m": "missed a real problem", "x": "mixed"}


def ask(prompt: str, allowed: set[str]) -> str:
    while True:
        try:
            ans = input(prompt).strip().lower()
        except EOFError:
            return "q"
        if ans in allowed or ans == "q":
            return ans
        console.print(f"[red]Type one of: {', '.join(sorted(allowed))} (or q to stop)[/red]")


def show(title: str, body: str, style: str = "white") -> None:
    if HAVE_RICH:
        from rich.panel import Panel
        from rich.text import Text

        console.print(Panel(Text(body or "(empty)"), title=title, border_style=style))
    else:
        console.print(f"\n--- {title} ---\n{body or '(empty)'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="")
    ap.add_argument("--redo", default="", help="comma-separated case ids to label again")
    ap.add_argument("--no-critic", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run) if args.run else latest_run_dir()
    if not run_dir or not (run_dir / "state.json").exists():
        fail("No run found. Run scripts/run_experiment.py first.")
        sys.exit(1)
    state = read_json(run_dir / "state.json", {})
    meta = read_json(run_dir / "meta.json", {})
    cases_file = Path(meta.get("cases_file", ROOT / "tests" / "cases.jsonl"))
    if not cases_file.is_absolute():
        cases_file = ROOT / cases_file
    if not cases_file.exists():  # project folder moved since the run
        cases_file = ROOT / "tests" / "cases.jsonl"
    docs = {c["id"]: c for c in read_jsonl(cases_file)}

    labels_path = run_dir / "labels.jsonl"
    existing = {r["id"]: r for r in read_jsonl(labels_path)}
    redo = {x.strip() for x in args.redo.split(",") if x.strip()}
    if redo:  # drop old labels for these ids
        kept = [r for k, r in existing.items() if k not in redo]
        labels_path.write_text("", encoding="utf-8")
        for r in kept:
            append_jsonl(labels_path, r)
        existing = {r["id"]: r for r in kept}

    todo = [cid for cid in meta.get("case_ids", list(state)) if cid not in existing
            and "baseline" in state.get(cid, {}) and "final" in state.get(cid, {})]
    skipped = [cid for cid in meta.get("case_ids", list(state)) if cid not in existing and cid not in todo]
    console.rule(f"Blind labelling · {run_dir.name}")
    console.print(f"{len(existing)} labelled, {len(todo)} to go"
                  + (f", {len(skipped)} incomplete cases skipped (errors?)" if skipped else ""))
    console.print("Labels: [bold]c[/bold]=correct  [bold]h[/bold]=hallucination  "
                  "[bold]i[/bold]=incomplete  [bold]r[/bold]=wrong refusal   [bold]q[/bold]=stop for now\n")

    for n, cid in enumerate(todo, 1):
        rec, case = state[cid], docs.get(cid, {})
        console.rule(f"{n}/{len(todo)} · case {cid} · {rec.get('category', '')}")
        show("Document", case.get("document", "(document not found)"), "blue")
        show("Question", rec["question"], "yellow")
        ref = rec["reference"] + (f"\n(note: {rec['note']})" if rec.get("note") else "")
        show("Reference answer", ref, "magenta")

        identical = rec["baseline"].strip() == rec["final"].strip()
        order = ["baseline", "final"]
        random.Random(f"{run_dir.name}:{cid}").shuffle(order)
        got: dict[str, str] = {}
        if identical:
            show("Answer (both versions identical)", rec["baseline"], "green")
            a = ask("Label [c/h/i/r]: ", set(LABELS))
            if a == "q":
                break
            got = {"baseline": a, "final": a}
        else:
            for letter, which in zip("AB", order):
                show(f"Answer {letter}", rec[which], "green")
            a = ask("Label for A [c/h/i/r]: ", set(LABELS))
            if a == "q":
                break
            b = ask("Label for B [c/h/i/r]: ", set(LABELS))
            if b == "q":
                break
            got = {order[0]: a, order[1]: b}

        critic = ""
        if not args.no_critic:
            title = ("Critic audit (it reviewed this answer)" if identical else
                     f"Critic audit (it reviewed answer {'AB'[order.index('baseline')]}, the single-model draft)")
            show(title, rec.get("audit", ""), "red")
            critic = ask("Was the critic right? [y]es / [f]alse alarm / [m]issed problem / mi[x]ed: ", set(CRITIC))
            if critic == "q":
                break
        comment = input("Comment (optional, Enter to skip): ").strip() if sys.stdin.isatty() else ""
        append_jsonl(labels_path, {"id": cid, "labels": got, "order": order, "identical": identical,
                                   "critic": critic, "comment": comment})
        ok(f"saved {cid}: baseline={LABELS[got['baseline']]}, final={LABELS[got['final']]}")

    done = len(read_jsonl(labels_path))
    console.rule()
    console.print(f"{done} cases labelled in {labels_path}")
    console.print("Next: [bold]python scripts/report.py[/bold]")
    write_json(run_dir / "labels_progress.json", {"labelled": done})


if __name__ == "__main__":
    main()
