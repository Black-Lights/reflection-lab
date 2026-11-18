# HHEM leaderboard-style benchmark · bench_hhem_20261118-015131

- generator: `gemma-4-e4b` (gpu, runtime python) · critic: `gemma-4-e4b` (gpu), prompts `prompts_v2`
- documents: 200 sampled (seed 0) from `vectara/hhem_leaderboard_datasets/leaderboard_dataset.csv`
- prompt version: `legacy` · greedy decoding · max_output_tokens 512
- scorer: `vectara/hallucination_evaluation_model` (HHEM-2.1-open, CPU) revision `de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8` · hallucinated if score < 0.5

| variant | hallucination rate % | factual consistency rate % | answer rate % | avg summary length (words) | mean HHEM | scored/N | errors |
|---|---|---|---|---|---|---|---|
| baseline | 0.5 | 99.5 | 100.0 | 74.9 | 0.905 | 200/200 | 0 |
| loop | 0.5 | 99.5 | 100.0 | 74.9 | 0.905 | 200/200 | 0 |

## Critic loop

- critic verdicts: {'OK': 192, 'ISSUES': 8} · refined: 8
- paired, on 200 documents scored in both variants: hallucinated -> consistent 0, consistent -> hallucinated 0, hallucinated in both 1
- note: refiner.txt asks for at most 120 words, so loop summaries can be shorter than baseline ones.

## How to read this

Same method as the Vectara leaderboard backend (valid = at least 5 words; rates over valid summaries;
answer rate over all documents). Differences: the public leaderboard now uses HHEM-2.3 (commercial) on a
private dataset and only scores documents that every model answered; word counts here are alphabetic runs,
not spaCy tokens. Compare variants within this folder rather than with the public table.
