"""Grade a run's answers automatically with per-case rules (no model needed).

    python scripts/autoscore.py --run runs/<dir>              write labels_auto.jsonl + review.md
    python scripts/autoscore.py --run runs/<dir> --compare    agreement with the manual labels.jsonl
    python scripts/autoscore.py --run runs/<dir> --apply      also write labels.jsonl (never over manual labels),
                                                              taking review_overrides.json into account

Rules come from the case's own "check" field, else from tests/rules.json (frozen sets). Rule types:
  answer   every expect group must match; else a refusal = wrong refusal (r), an unsupported number =
           hallucination (h, flagged), otherwise incomplete (i)
  refuse   the answer must say the document does not say; an unsupported number = h (flagged)
  premise  expect = the correction of the false premise; a bare refusal = r
  partial  expect = the answerable part, plus a "not stated" for the other part
  incomplete_if: patterns that mean partial content (incomplete) when expect fails
Any forbid pattern = h. "Unsupported number" = a number in the answer that is not in the document or
question, not in the rule's allow list and not a small integer. Flagged answers are listed in review.md;
put corrected labels in review_overrides.json as {"<id>": {"baseline": "c", "final": "i"}}.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import ROOT, console, fail, ok, read_json, read_jsonl, warn  # noqa: E402

VERSION = "auto-rules v1"
REFUSAL = re.compile(
    r"(does not|doesn't|do not|did not|didn't|does n't)\s+(explicitly\s+)?(say|state|mention|specify|provide|include|"
    r"contain|give|indicate|report|explain|list)|not (explicitly )?(stated|mentioned|specified|provided|given|scheduled|"
    r"included|reported|set|available|indicated|known)|\bno (information|mention|figure|date|details?|data|pet deposit|"
    r"fee)\b|has not been (scheduled|set|decided|given|made)|cannot be determined|is unknown", re.I)


def norm(t: str) -> str:
    t = (t or "").replace("−", "-").replace(" ", " ").replace(" ", " ")
    return re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", t)  # 1,250 / 1 250 -> 1250


def numbers(t: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", norm(t))]


def matches(groups, text: str) -> bool:
    return all(any(re.search(p, text, re.I) for p in g) for g in groups)


def grade(case: dict, rule: dict, answer: str) -> tuple[str, str, bool]:
    """Return (label, reason, needs_review)."""
    a = norm(answer)
    if not a.strip():
        return "i", "empty answer", True
    for p in rule.get("forbid", []):
        if re.search(p, a, re.I):
            return "h", f"forbidden: {p}", False
    allowed = set(numbers(case["document"])) | set(numbers(case["question"])) | {float(x) for x in rule.get("allow", [])}
    unsupported = [n for n in numbers(a) if n not in allowed and not (n.is_integer() and n <= 12)]
    refusal = bool(REFUSAL.search(a))
    hit = matches(rule.get("expect", []), a)
    t = rule.get("type", "answer")
    us = f" unsupported numbers {unsupported}" if unsupported else ""
    # incomplete_if: partial credit when the expected content is missing (e.g. a conditional half-answer)
    if not hit and any(re.search(p, a, re.I) for p in rule.get("incomplete_if", [])):
        return "i", "partial content (incomplete_if)" + us, bool(unsupported)
    if t == "answer":
        if hit:
            return "c", "expected content" + us, bool(unsupported)
        if refusal:
            return "r", "refused an answerable question", False
        if unsupported:
            return "h", "expected content missing;" + us, True
        return "i", "expected content missing", False
    if t == "refuse":
        if unsupported:
            return "h", "number not in the document;" + us, True
        if refusal:
            return "c", "says it is not stated", False
        return "h", "no refusal (check)", True
    if t == "premise":
        if hit:
            return "c", "premise corrected" + us, bool(unsupported)
        if refusal:
            return "r", "bare refusal, premise not corrected", False
        return "i", "premise not corrected (check)", True
    if t == "partial":
        if hit and refusal:
            return "c", "answerable part + not-stated part" + us, bool(unsupported)
        if hit:
            return ("h" if unsupported else "i"), "missing part not flagged as not stated;" + us, True
        if refusal:
            return "r", "answerable part refused", False
        return "i", "answerable part missing (check)", True
    return "i", f"unknown rule type {t}", True


def load_rules(cases_file: Path) -> tuple[dict, dict]:
    cases = {c["id"]: c for c in read_jsonl(cases_file)}
    shared = read_json(ROOT / "tests" / "rules.json", {}) or {}
    rules = {cid: (c.get("check") or shared.get(cid)) for cid, c in cases.items()}
    return cases, rules


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--compare", action="store_true", help="compare with the manual labels.jsonl")
    ap.add_argument("--apply", action="store_true", help="write labels.jsonl if the run has none")
    args = ap.parse_args()

    run = Path(args.run)
    state, meta = read_json(run / "state.json", {}), read_json(run / "meta.json", {})
    cases_file = Path(meta.get("cases_file", ROOT / "tests" / "cases.jsonl"))
    if not cases_file.is_absolute():
        cases_file = ROOT / cases_file
    cases, rules = load_rules(cases_file)
    overrides = read_json(run / "review_overrides.json", {}) or {}
    out, review = [], [f"# Review sheet · {run.name}", "", "Flagged by the rules; check and put corrections in "
                       "review_overrides.json.", ""]
    for cid in meta.get("case_ids", list(state)):
        rec = state.get(cid, {})
        if "baseline" not in rec or "final" not in rec:
            continue
        rule = rules.get(cid)
        if not rule:
            warn(f"{cid}: no rule, skipped")
            continue
        labels, flags = {}, {}
        for cond in ("baseline", "final"):
            lab, why, chk = grade(cases[cid], rule, rec[cond])
            labels[cond], flags[cond] = lab, {"reason": why, "review": chk}
        if rec["baseline"].strip() == rec["final"].strip():
            flags["final"] = flags["baseline"]
        reviewed = cid in overrides
        if reviewed:
            labels.update(overrides[cid])
        out.append({"id": cid, "labels": labels, "flags": flags, "identical": rec["baseline"].strip() == rec["final"].strip(),
                    "labeller": VERSION + (" + Claude review" if reviewed else ""), "critic": "", "comment": ""})
        for cond in ("baseline", "final"):
            if flags[cond]["review"] and not reviewed and not (cond == "final" and out[-1]["identical"]):
                review += [f"## {cid} · {cond} → {labels[cond]} ({flags[cond]['reason']})", "",
                           f"Q: {cases[cid]['question']}", "", f"Ref: {cases[cid]['reference']}", "",
                           "> " + rec[cond].replace("\n", "\n> "), ""]
    with open(run / "labels_auto.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run / "review.md").write_text("\n".join(review), encoding="utf-8")
    n_rev = sum(1 for line in review if line.startswith("## "))
    ok(f"{len(out)} cases graded → labels_auto.jsonl; {n_rev} answers flagged → review.md")

    if args.compare:
        manual = {r["id"]: r for r in read_jsonl(run / "labels.jsonl")}
        agree = total = 0
        for r in out:
            m = manual.get(r["id"])
            if not m:
                continue
            for cond in ("baseline", "final"):
                total += 1
                if m["labels"][cond] == r["labels"][cond]:
                    agree += 1
                else:
                    console.print(f"  {r['id']:<5} {cond:<8} manual={m['labels'][cond]} auto={r['labels'][cond]}  "
                                  f"({r['flags'][cond]['reason']})")
        console.print(f"Agreement with manual labels: {agree}/{total}" + (f" = {agree / total:.0%}" if total else ""))
    if args.apply:
        lp = run / "labels.jsonl"
        if lp.exists() and lp.read_text(encoding="utf-8").strip():
            fail(f"{lp} already has labels; not overwritten (auto labels are in labels_auto.jsonl)")
        else:
            lp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
            ok(f"wrote {lp}")


if __name__ == "__main__":
    main()
