# lm-evaluation-harness · bench_lmeval_20261118-002145

- model: `qwen3-4b` (gpu, runtime python) through lab/lmeval_litert.py, greedy, max_num_tokens 4096
- tasks: gsm8k_cot,ifeval · limit 50 per task (first N documents; split over subtasks of a group) · few-shot task default
- requests 100 · clipped to fit the context 0 · cut at a stop string 0 · errors 0 · generation time 8.1 min

| task | metric | filter | score % | stderr % | n |
|---|---|---|---|---|---|
| gsm8k_cot | exact_match | strict-match | 8.0 | 3.9 | 50 |
| gsm8k_cot | exact_match | flexible-extract | 62.0 | 6.9 | 50 |
| ifeval | prompt_level_strict_acc | none | 86.0 | 5.0 | 50 |
| ifeval | inst_level_strict_acc | none | 90.8 | - | 50 |
| ifeval | prompt_level_loose_acc | none | 84.0 | 5.2 | 50 |
| ifeval | inst_level_loose_acc | none | 89.5 | - | 50 |

Scores are lm_eval's own metrics. Each request was one user message in a fresh conversation (the model's
chat template applied by LiteRT-LM), so they are not directly comparable with base-model leaderboard runs.
