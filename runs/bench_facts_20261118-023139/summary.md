# FACTS Grounding responses · bench_facts_20261118-023139

- generator: `qwen3-4b` (gpu, runtime python)
- examples: 50 from `.\tests\facts_subset.jsonl` · greedy · max_num_tokens 4096, max_output_tokens 512
- errors: 0

| variant | responses | avg words |
|---|---|---|
| baseline | 50 | 174.8 |

Judge by hand with `judging_sheet.md`, fill `judgments.jsonl`, then run `python scripts/bench_facts.py --score ".\runs\bench_facts_20261118-023139"`.

## Scores from judgments.jsonl

| variant | judged | eligible % | grounded % | FACTS score % (eligible and grounded) |
|---|---|---|---|---|
| baseline | 50 | 94.0 | 48.0 | 42.0 |
