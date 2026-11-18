# FACTS Grounding responses · bench_facts_20261118-022257

- generator: `gemma-4-e4b` (gpu, runtime python) · critic: `gemma-4-e4b` (gpu), prompts `prompts_v2_long`
- examples: 50 from `.\tests\facts_subset.jsonl` · greedy · max_num_tokens 4096, max_output_tokens 512
- errors: 0 · critic verdicts {'OK': 34, 'ISSUES': 16} · refined 16

| variant | responses | avg words |
|---|---|---|
| baseline | 50 | 151.7 |
| loop | 50 | 161.4 |

Judge by hand with `judging_sheet.md`, fill `judgments.jsonl`, then run `python scripts/bench_facts.py --score ".\runs\bench_facts_20261118-022257"`.
Note: refiner.txt asks for at most 120 words, which can make long-form answers ineligible.

## Scores from judgments.jsonl

| variant | judged | eligible % | grounded % | FACTS score % (eligible and grounded) |
|---|---|---|---|---|
| baseline | 50 | 94.0 | 88.0 | 82.0 |
| loop | 50 | 92.0 | 80.0 | 74.0 |
