"""Generate FACTS Grounding responses for tests/facts_subset.jsonl and write a judging sheet.

    python scripts/bench_facts.py --runtime fake --limit 3                    test the script, no model
    python scripts/bench_facts.py --model gemma-4-e4b                         baseline responses (50)
    python scripts/bench_facts.py --model gemma-4-e4b --critic qwen3-1.7b     + critic -> refiner loop
    python scripts/bench_facts.py --score runs/bench_facts_<stamp>            score a filled judgments.jsonl

Input: tests/facts_subset.jsonl (made by scripts/prep_facts.py). The model receives the dataset's full_prompt
(system instruction + user request + context document) as one user message, greedy decoding.
With --critic: critic.txt with document = context_document, question = user_request, draft = response; then
refiner.txt unless the verdict is OK.
Output in runs/bench_facts_<stamp>/:
  results.jsonl      one line per example (baseline, audit, verdict, final, timings)
  judging_sheet.md   FACTS criteria at the top, then per example: request, document, response(s). With a loop
                     the two responses appear in random order (seed) as Response 1 / 2; identical ones once.
  judging_key.json   which response number is baseline / loop (do not open while judging)
  judgments.jsonl    blank template: fill eligible / grounded (true/false) per response, then run --score
  summary.md
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.bench_common import (  # noqa: E402
    add_common_args, critic_refine, finish_meta, load_llm, md_table, preflight, run_stage, setup,
    verdict_counts, write_jsonl,
)
from lab.common import ROOT, fail, ok, read_json, read_jsonl  # noqa: E402

CRITERIA = """## How to judge (FACTS Grounding criteria)

Source: FACTS Grounding technical report (Jacovi et al., 2024), sections 3.1 and 3.2. Judge every response
on its own, using only the context document (no outside knowledge).

1. **Eligibility.** Does the response sufficiently address the user's request? *Eligible* if it answers the
   request; *ineligible* otherwise, for example when it is so vague or evasive that it skips what the request
   asks for, even if everything it says is true. Ineligible responses count as inaccurate.
2. **Grounding (factuality).** The response is *accurate* if all the claims in it are grounded in the context
   document (or do not require grounding, e.g. greetings, disclaimers); it is *not accurate* if a single claim
   that bears information is not grounded: it contradicts the document or cannot be verified from it.

Score of a response = 1 if eligible AND grounded, else 0. FACTS score = the mean over responses.
Record the verdicts in `judgments.jsonl` (eligible / grounded: true or false, plus a short note), then run
`python scripts/bench_facts.py --score <this folder>`. The official LLM-judge prompts are in the dataset's
evaluation_prompts.csv; this sheet uses their criteria, not their wording.
"""


def load_subset(path: Path) -> list[dict]:
    if not path.exists():
        fail(f"{path} not found. Run first: python scripts/prep_facts.py")
        sys.exit(1)
    return read_jsonl(path)


def blind_responses(it: dict, rng: random.Random) -> list[tuple[str, str | None]]:
    """[(variant, text)] in the order shown. Identical responses are shown once as 'both'."""
    base, final = it.get("baseline"), it.get("final", "absent")
    if final == "absent":
        return [("baseline", base)]
    if final == base:
        return [("both", base)]
    pair = [("baseline", base), ("loop", final)]
    if rng.random() < 0.5:
        pair.reverse()
    return pair


def write_sheet(run_dir: Path, items: list[dict], seed: int) -> None:
    rng = random.Random(seed)
    key, template = {}, []
    out = [f"# FACTS Grounding judging sheet · {run_dir.name}", "", CRITERIA, "## Examples", ""]
    for n, it in enumerate(items, 1):
        shown = blind_responses(it, rng)
        key[it["id"]] = {str(i): v for i, (v, _) in enumerate(shown, 1)}
        out += [
            "---", "", f"### {n}. {it['id']}", "",
            f"**System instruction:** {it['system_instruction'].strip()}", "",
            f"**User request:** {it['user_request'].strip()}", "",
            f"**Context document** ({len(it['context_document'].split())} words):", "",
            "~~~~text", it["context_document"].strip(), "~~~~", "",
        ]
        for i, (variant, text) in enumerate(shown, 1):
            label = f"Response {i}" + (" (both variants gave this same text)" if variant == "both" else "")
            body = text if text is not None else f"(no response: {it.get('errors')})"
            out += [f"**{label}:**", "", "~~~~text", body.strip(), "~~~~", ""]
            template.append({"id": it["id"], "response": i, "eligible": None, "grounded": None, "note": ""})
        out += ["**Verdict:** " + " · ".join(f"Response {i}: eligible __ grounded __" for i in range(1, len(shown) + 1)),
                ""]
    (run_dir / "judging_sheet.md").write_text("\n".join(out), encoding="utf-8")
    (run_dir / "judging_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    write_jsonl(run_dir / "judgments.jsonl", template)


def score(run_dir: Path) -> None:
    key = read_json(run_dir / "judging_key.json", {})
    judged = [j for j in read_jsonl(run_dir / "judgments.jsonl") if j.get("eligible") is not None
              and j.get("grounded") is not None]
    if not judged:
        fail("judgments.jsonl has no filled lines (eligible and grounded must be true or false)")
        sys.exit(1)
    per: dict = {}
    for j in judged:
        variant = key.get(j["id"], {}).get(str(j["response"]), "?")
        for v in (["baseline", "loop"] if variant == "both" else [variant]):
            per.setdefault(v, []).append(j)
    rows = []
    for v, js in sorted(per.items()):
        elig = sum(bool(j["eligible"]) for j in js)
        grounded = sum(bool(j["grounded"]) for j in js)
        both = sum(bool(j["eligible"]) and bool(j["grounded"]) for j in js)
        rows.append([v, len(js), 100 * elig / len(js), 100 * grounded / len(js), 100 * both / len(js)])
    table = md_table(["variant", "judged", "eligible %", "grounded %", "FACTS score % (eligible and grounded)"], rows)
    with open(run_dir / "summary.md", "a", encoding="utf-8") as f:
        f.write("\n## Scores from judgments.jsonl\n\n" + table + "\n")
    print(table)
    ok(f"Scores appended to {run_dir / 'summary.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap, n_default=0)
    ap.add_argument("--subset", default=str(ROOT / "tests" / "facts_subset.jsonl"))
    ap.add_argument("--score", metavar="RUN_DIR", help="compute scores from a filled judgments.jsonl")
    args = ap.parse_args()
    if args.score:
        score(Path(args.score))
        return

    items = load_subset(Path(args.subset))
    if args.n:
        items = items[: args.n]
    cfg, gen, run_dir = setup(args, "facts")
    ok(f"{len(items)} FACTS examples from {args.subset}")

    preflight([it["full_prompt"] for it in items], gen, "response")
    llm = load_llm(cfg, args.runtime, args.model, args.backend, gen)
    try:
        run_stage(llm, items, lambda it: it["full_prompt"], "baseline", gen, run_dir / "calls.jsonl", "response")
    finally:
        llm.close()
    if args.critic:
        critic_refine(cfg, args, gen, items, run_dir, doc_fn=lambda it: it["context_document"],
                      question_fn=lambda it: it["user_request"])
    write_jsonl(run_dir / "results.jsonl", [{k: v for k, v in it.items() if k not in ("context_document",
                                                                                         "full_prompt")} for it in items])
    write_sheet(run_dir, items, args.seed)

    def words(v):
        got = [len(it[v].split()) for it in items if it.get(v)]
        return sum(got) / len(got) if got else 0.0

    rows = [["baseline", sum(1 for it in items if it.get("baseline")), words("baseline")]]
    if args.critic:
        rows.append(["loop", sum(1 for it in items if it.get("final")), words("final")])
    out = [
        f"# FACTS Grounding responses · {run_dir.name}", "",
        f"- generator: `{args.model}` ({args.backend}, runtime {args.runtime})"
        + (f" · critic: `{args.critic}` ({args.critic_backend}), prompts `{args.prompts}`" if args.critic else ""),
        f"- examples: {len(items)} from `{args.subset}` · greedy · max_num_tokens {gen.get('max_num_tokens')}, "
        f"max_output_tokens {gen.get('max_output_tokens')}",
        f"- errors: {sum(1 for it in items if it.get('errors'))}"
        + (f" · critic verdicts {verdict_counts(items)} · refined {sum(1 for it in items if it.get('refined'))}"
           if args.critic else ""), "",
        md_table(["variant", "responses", "avg words"], rows), "",
        "Judge by hand with `judging_sheet.md`, fill `judgments.jsonl`, then run "
        f"`python scripts/bench_facts.py --score \"{run_dir}\"`.",
    ]
    if args.critic:
        out.append("Note: refiner.txt asks for at most 120 words, which can make long-form answers ineligible.")
    (run_dir / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    finish_meta(run_dir)
    ok(f"Judging sheet: {run_dir / 'judging_sheet.md'}")


if __name__ == "__main__":
    main()
