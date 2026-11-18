"""Grade a run's answers automatically with per-case rules (no model needed).

    python scripts/autoscore.py --run runs/<dir>              write labels_auto.jsonl + review.md
    python scripts/autoscore.py --run runs/<dir> --compare    agreement with the manual labels.jsonl
    python scripts/autoscore.py --run runs/<dir> --apply      also write labels.jsonl (refreshes its own earlier auto labels, never manual ones),
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

VERSION = "auto-rules v2"
# v2 (2026-11-17, after an independent review of 133 grid answers): wrong content is checked BEFORE a
# refusal phrase can excuse it; clock times are compared as times; LaTeX maths is stripped; forbid
# patterns ignore negated mentions ("net profit is not stated"); tests/rules.json overrides a case's
# own "check" rule, so frozen case files never need editing.
REFUSAL = re.compile(
    r"(does not|doesn't|do not|did not|didn't|does n't)\s+(explicitly\s+|directly\s+)?(say|state|mention|specify|"
    r"provide|include|contain|give|indicate|report|explain|list|discuss|address)|not (explicitly |directly )?(stated|"
    r"mentioned|specified|provided|given|scheduled|included|reported|set|available|indicated|known|discussed)|"
    r"\bno (information|mention|figure|date|details?|data|pet deposit|fee|recommendation)\b|has not been (scheduled|"
    r"set|decided|given|made)|cannot be determined|is unknown", re.I)
NEG = re.compile(r"\b(not|no|never|neither|nor|without)\b|n't\b", re.I)
TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
CONSTANTS = {100.0, 60.0, 24.0, 365.0, 52.0}  # percent factor, minutes/hours, days, weeks


def norm(t: str) -> str:
    t = (t or "").replace("\u2212", "-").replace("\u00a0", " ").replace("\u202f", " ")
    t = re.sub(r"\\text\{([^}]*)\}", r"\1", t)  # LaTeX from model output: $22 - 18 = 4$, \times
    for a, b in (("\\times", "×"), ("\\cdot", "·"), ("\\(", ""), ("\\)", ""), ("\\[", ""), ("\\]", ""), ("$", "")):
        t = t.replace(a, b)
    return re.sub(r"(?<=\d)[, ](?=\d{3}\b)", "", t)  # 1,250 / 1 250 -> 1250


def clock_times(t: str) -> set[str]:
    return {f"{int(h)}:{m}" for h, m in TIME.findall(norm(t))}


def numbers(t: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", TIME.sub(" ", norm(t)))]


def matches(groups, text: str) -> bool:
    return all(any(re.search(p, text, re.I) for p in g) for g in groups)


def forbidden(pattern: str, a: str) -> bool:
    """A forbid pattern counts unless the mention is negated right before or right after it."""
    for m in re.finditer(pattern, a, re.I):
        if NEG.search(a[max(0, m.start() - 40):m.start()]) or re.match(r"\s*(not\b|n't\b)", a[m.end():], re.I):
            continue
        return True
    return False


def grade(case: dict, rule: dict, answer: str) -> tuple[str, str, bool]:
    """Return (label, reason, needs_review)."""
    a = norm(answer)
    if not a.strip():
        return "i", "empty answer", True
    for p in rule.get("forbid", []):
        if forbidden(p, a):
            return "h", f"forbidden: {p}", False
    src = case["document"] + " " + case["question"]
    allowed = set(numbers(src)) | {float(x) for x in rule.get("allow", [])} | CONSTANTS
    unsupported = [n for n in numbers(a) if n not in allowed and not (n.is_integer() and n <= 12)]
    unsupported += sorted(clock_times(a) - clock_times(src) - set(rule.get("allow_times", [])))
    refusal = bool(REFUSAL.search(a))
    hit = matches(rule.get("expect", []), a)
    t = rule.get("type", "answer")
    us = f" unsupported {unsupported}" if unsupported else ""
    # incomplete_if: partial credit when the expected content is missing (e.g. a conditional half-answer)
    if not hit and any(re.search(p, a, re.I) for p in rule.get("incomplete_if", [])):
        return ("h" if unsupported else "i"), "partial content (incomplete_if)" + us, bool(unsupported)
    if t == "answer":
        if hit:
            return "c", "expected content" + us, bool(unsupported)
        if unsupported:
            return "h", "wrong value:" + us, True
        if refusal:
            return "r", "refused an answerable question", False
        return "i", "expected content missing", False
    if t == "refuse":
        if unsupported:
            return "h", "value not in the document:" + us, True
        if refusal:
            return "c", "says it is not stated", False
        return "h", "no refusal (check)", True
    if t == "premise":
        if hit:
            return "c", "premise corrected" + us, bool(unsupported)
        if unsupported:
            return "h", "premise not corrected, value not in the document:" + us, True
        if refusal:
            return "r", "bare refusal, premise not corrected", False
        return "i", "premise not corrected (check)", True
    if t == "partial":
        if hit and refusal:
            return "c", "answerable part + not-stated part" + us, bool(unsupported)
        if unsupported:
            return "h", "value not in the document:" + us, True
        if hit:
            return "i", "missing part not flagged as not stated", True
        if refusal:
            return "r", "answerable part refused", False
        return "i", "answerable part missing (check)", True
    return "i", f"unknown rule type {t}", True


def load_rules(cases_file: Path) -> tuple[dict, dict]:
    cases = {c["id"]: c for c in read_jsonl(cases_file)}
    shared = read_json(ROOT / "tests" / "rules.json", {}) or {}
    rules = {cid: (shared.get(cid) or c.get("check")) for cid, c in cases.items()}  # rules.json wins
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
        raw = dict(labels)  # the rules' own verdict, kept next to any reviewed override
        reviewed = cid in overrides
        if reviewed:
            labels.update(overrides[cid])
        out.append({"id": cid, "labels": labels, "auto_labels": raw, "flags": flags,
                    "identical": rec["baseline"].strip() == rec["final"].strip(),
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
        existing = read_jsonl(lp) if lp.exists() else []
        if existing and not all(str(r.get("labeller", "")).startswith("auto-rules") for r in existing):
            fail(f"{lp} has manual labels; not overwritten (auto labels are in labels_auto.jsonl)")
        else:
            lp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
            ok(f"wrote {lp}")


if __name__ == "__main__":
    main()
