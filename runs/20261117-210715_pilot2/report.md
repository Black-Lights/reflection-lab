# Report · 20261117-210715_pilot2

Analyst: **gemma-4-e4b** · Critic: **qwen3-1.7b** · runtime python · 30 labelled cases

Labelled by: claude-opus-5-5 (blind A/B, answers labelled before audits were revealed; owner asked Claude to label) (30 cases)
Critic verdict rule: `verdict_line`

## Outcomes

| | Single model (baseline) | With critic loop (final) |
|---|---|---|
| correct | 27/30 = 90% (95% CI 74%–97%) | 27/30 = 90% (95% CI 74%–97%) |
| hallucination | 0/30 = 0% (95% CI 0%–11%) | 0/30 = 0% (95% CI 0%–11%) |
| incomplete | 2/30 = 7% (95% CI 2%–21%) | 2/30 = 7% (95% CI 2%–21%) |
| wrong refusal | 1/30 = 3% (95% CI 1%–17%) | 1/30 = 3% (95% CI 1%–17%) |

## Is the difference real?

- Hallucinations removed by the loop: **0**, introduced by the loop: **0** (McNemar exact p = 1.000)
- Answers that became correct: **0**, became not-correct: **0** (p = 1.000)
- p < 0.05 means the difference is unlikely to be luck. With ~30 cases expect wide intervals: grow the test set before drawing conclusions.

## Critic (Stage 2)

- Flagged 15 drafts; 2 of them were really wrong → precision 13%
- Of 3 wrong drafts it caught 2 → recall 67%
- False alarms: 13, missed: 1
- Labeller's rating of the audits: right 16, false alarm 12, mixed 2

## Refiner (Stage 3)

- Refined 15 cases: fixed 0, broke 0

## By category

| Category | n | Halluc. baseline | Halluc. final | Correct baseline | Correct final |
|---|---|---|---|---|---|
| answerable | 8 | 0 | 0 | 8 | 8 |
| counterfactual | 4 | 0 | 0 | 4 | 4 |
| multihop | 4 | 0 | 0 | 3 | 3 |
| numeric | 6 | 0 | 0 | 4 | 4 |
| trap | 8 | 0 | 0 | 8 | 8 |

## Speed (PC)

- Stage 1 0.7s · Stage 2 1.0s · Stage 3 1.1s (avg per call)
- Whole loop per case: 2.2s vs single model 0.7s
- Peak VRAM 3.0 GB · peak RAM used 11.57 GB

## Look at these cases

- Hallucination fixed by the loop: -
- Hallucination introduced by the loop: -
- Made correct by the loop: -
- Made worse by the loop: -

Labels: c correct, h hallucination, i incomplete, r wrong refusal. Open transcript.md in the run folder to read them.