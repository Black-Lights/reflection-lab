# lm-evaluation-harness · bench_lmeval_20261118-001507

- model: `gemma-4-e4b` (gpu, runtime python) through lab/lmeval_litert.py, greedy, max_num_tokens 4096
- tasks: mmlu_pro · limit 28 per task (first N documents; split over subtasks of a group) · few-shot task default
- requests 28 · clipped to fit the context 2 · cut at a stop string 1 · errors 0 · generation time 4.6 min

| task | metric | filter | score % | stderr % | n |
|---|---|---|---|---|---|
| mmlu_pro | exact_match | custom-extract | 60.7 | 9.4 | 28 |

Scores are lm_eval's own metrics. Each request was one user message in a fresh conversation (the model's
chat template applied by LiteRT-LM), so they are not directly comparable with base-model leaderboard runs.
