# Report · 20261117-213155_hard

Analyst: **gemma-4-e4b** · Critic: **qwen3-1.7b** · runtime python · 42 labelled cases

Labelled by: claude-opus-5-5 (blind A/B, answers labelled before audits were revealed; owner asked Claude to label) (42 cases)
Critic verdict rule: `verdict_line`

## Outcomes

| | Single model (baseline) | With critic loop (final) |
|---|---|---|
| correct | 34/42 = 81% (95% CI 67%–90%) | 30/42 = 71% (95% CI 56%–83%) |
| hallucination | 1/42 = 2% (95% CI 0%–12%) | 1/42 = 2% (95% CI 0%–12%) |
| incomplete | 5/42 = 12% (95% CI 5%–25%) | 7/42 = 17% (95% CI 8%–31%) |
| wrong refusal | 2/42 = 5% (95% CI 1%–16%) | 4/42 = 10% (95% CI 4%–22%) |

## Is the difference real?

- Hallucinations removed by the loop: **0**, introduced by the loop: **0** (McNemar exact p = 1.000)
- Answers that became correct: **0**, became not-correct: **4** (p = 0.125)
- p < 0.05 means the difference is unlikely to be luck. With ~30 cases expect wide intervals: grow the test set before drawing conclusions.

## Critic (Stage 2)

- Flagged 35 drafts; 7 of them were really wrong → precision 20%
- Of 8 wrong drafts it caught 7 → recall 88%
- False alarms: 28, missed: 1
- Labeller's rating of the audits: false alarm 28, right 8, mixed 6

## Refiner (Stage 3)

- Refined 35 cases: fixed 0, broke 4

## By category

| Category | n | Halluc. baseline | Halluc. final | Correct baseline | Correct final |
|---|---|---|---|---|---|
| answerable | 4 | 0 | 0 | 4 | 4 |
| counterfactual | 4 | 0 | 0 | 4 | 4 |
| false_premise | 7 | 0 | 0 | 6 | 6 |
| multihop | 4 | 0 | 0 | 3 | 2 |
| numeric | 9 | 1 | 1 | 3 | 0 |
| partial | 5 | 0 | 0 | 5 | 5 |
| trap | 9 | 0 | 0 | 9 | 9 |

## Speed (PC)

- Stage 1 0.9s · Stage 2 1.4s · Stage 3 1.4s (avg per call)
- Whole loop per case: 3.5s vs single model 0.9s
- Peak VRAM 3.0 GB · peak RAM used 11.3 GB

## Look at these cases

- Hallucination fixed by the loop: -
- Hallucination introduced by the loop: -
- Made correct by the loop: -
- Made worse by the loop: hn02 (c→i), hn03 (c→i), hn06 (c→r), hm01 (c→r)

Labels: c correct, h hallucination, i incomplete, r wrong refusal. Open transcript.md in the run folder to read them.