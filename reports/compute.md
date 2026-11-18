# Time and compute

Generated 2026-11-18 04:51 by `scripts/compute_report.py`. Every model run used one laptop GPU (one model loaded at a time), so GPU time equals the runs' wall time.

## Totals

| | |
|---|---|
| Period | 17 Nov 20:56 to 18 Nov 02:48 (5.86 h elapsed) |
| Runs with real models | 48 (0 unfinished or running) |
| GPU wall time | 4.85 h |
| Time inside model calls | 4.25 h over 6,724 calls |
| Model loads (grid and pilots) | 48 loads, 4.6 min |
| Text generated | 2.42 M characters (roughly 0.60 M tokens) |
| GPU energy | 0.35 kWh (0.05 measured over 6 runs, 0.30 estimated) |
| Peak VRAM / RAM in a run | 4.1 GB / 12.8 GB |

Energy estimates use 72 W, the mean GPU board power over the measured runs (2,115 samples every 5 s, from 2026-11-18 01:55:21). Runs before the power logger started are estimates.

## By experiment

| Experiment | Runs | GPU wall time | Model calls | Time in calls | Mean s per call | GPU energy |
|---|---|---|---|---|---|---|
| Development (smoke, pilots, checks) | 7 | 7.7 min | 314 | 5.7 min | 1.10 | 9 Wh (est.) |
| Grid (analyst x critic x prompts, 104 questions) | 14 | 1.59 h | 3,492 | 1.54 h | 1.59 | 115 Wh (est.) |
| Agent benchmark (30 tool-use tasks) | 12 | 34.2 min | 360 | 21.1 min | 3.52 | 42 Wh (part est.) |
| lm-evaluation-harness | 6 | 39.5 min | 384 | 29.2 min | 4.56 | 48 Wh (est.) |
| RAGTruth (critic detection) | 4 | 1.13 h | 1,200 | 1.12 h | 3.36 | 82 Wh (est.) |
| HHEM leaderboard documents | 3 | 31.4 min | 808 | 24.8 min | 1.84 | 36 Wh (part est.) |
| FACTS Grounding subset | 2 | 14.9 min | 166 | 14.6 min | 5.27 | 19 Wh |

## By model

| Model | Calls | Time in calls | Mean s per call | Characters out | Loads | Load time |
|---|---|---|---|---|---|---|
| qwen3-4b | 2,080 | 1.98 h | 3.42 | 793,171 | 10 | 1.5 min |
| gemma-4-e4b | 3,053 | 1.41 h | 1.66 | 662,762 | 26 | 2.0 min |
| qwen3-1.7b | 1,591 | 51.9 min | 1.96 | 960,438 | 12 | 1.1 min |

Agent runs count the agent's first pass per task; verifier and rewrite time is in the wall time only.

## What the loop costs (grid runs)

Seconds of model time per question. One model = the analyst's draft only; loop = draft + audit + rewrite (the rewrite is skipped when the critic says OK) + model loads (swap mode reloads per stage).

| Analyst | Critic | Prompts | Questions | One model, s | Critic, s | Refiner, s | Loads, s | Loop, s | Loop / one model | Rewrites |
|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 104 | 0.86 | 0.66 | 0.27 | 0.05 | 1.83 | 2.1x | 22 |
| gemma-4-e4b | qwen3-4b | prompts | 104 | 0.98 | 2.45 | 0.71 | 0.15 | 4.29 | 4.4x | 52 |
| qwen3-4b | gemma-4-e4b | prompts | 104 | 1.92 | 0.96 | 1.04 | 0.19 | 4.12 | 2.1x | 44 |
| qwen3-4b | qwen3-4b | prompts | 104 | 1.90 | 2.55 | 1.38 | 0.08 | 5.91 | 3.1x | 56 |
| gemma-4-e4b | qwen3-1.7b | prompts | 104 | 0.96 | 1.39 | 0.90 | 0.13 | 3.38 | 3.5x | 77 |
| qwen3-1.7b | gemma-4-e4b | prompts | 104 | 0.88 | 1.07 | 0.56 | 0.13 | 2.65 | 3.0x | 59 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2 | 104 | 1.13 | 0.64 | 0.05 | 0.05 | 1.87 | 1.7x | 2 |
| gemma-4-e4b | qwen3-4b | prompts_v2 | 104 | 1.13 | 3.15 | 0.86 | 0.14 | 5.28 | 4.7x | 64 |
| qwen3-4b | gemma-4-e4b | prompts_v2 | 104 | 2.31 | 0.74 | 0.19 | 0.20 | 3.44 | 1.5x | 7 |
| qwen3-4b | qwen3-4b | prompts_v2 | 104 | 2.30 | 2.87 | 1.44 | 0.07 | 6.68 | 2.9x | 52 |
| gemma-4-e4b | qwen3-1.7b | prompts_v2 | 104 | 1.13 | 0.95 | 1.06 | 0.13 | 3.27 | 2.9x | 78 |
| qwen3-1.7b | gemma-4-e4b | prompts_v2 | 104 | 1.24 | 0.87 | 0.22 | 0.14 | 2.47 | 2.0x | 17 |
| gemma-4-e4b + tools | gemma-4-e4b | prompts_v2_tools | 104 | 1.44 | 0.65 | 0.04 | 0.05 | 2.18 | 1.5x | 2 |
| qwen3-4b + tools | qwen3-4b | prompts_v2_tools | 104 | 2.92 | 2.90 | 1.56 | 0.09 | 7.48 | 2.6x | 48 |

## Claude Code (the assistant that built and ran all this)

| | Main session | Subagents |
|---|---|---|
| Sessions / agents | 1 | 6 |
| First to last message | 2026-11-17 20:24:30 to 2026-11-18 04:51:51 (8.5 h) | |
| Active time (gaps over 5 min left out) | 3.9 h | 1.0 h |
| API responses | 404 | 155 |
| Tool calls | 504 | 168 |
| Input tokens (uncached) | 0.9 k | 0.3 k |
| Input tokens written to cache | 1.09 M | 929.4 k |
| Input tokens read from cache | 151.65 M | 18.86 M |
| Output tokens | 615.7 k | 261.7 k |

Models: claude-opus-5-5 (559 responses).

## Every run

| Run | Experiment | Start | Wall time | Calls | GPU energy | |
|---|---|---|---|---|---|---|
| 20261117-203657_fake | dev | 17 Nov 20:36 | 0.0 min | 8 | - | fake runtime |
| 20261117-205632_smoke | dev | 17 Nov 20:56 | 0.8 min | 6 | 1 Wh (est.) |  |
| 20261117-205818_pilot | dev | 17 Nov 20:58 | 1.5 min | 90 | 2 Wh (est.) |  |
| 20261117-210715_pilot2 | dev | 17 Nov 21:07 | 1.3 min | 75 | 2 Wh (est.) |  |
| 20261117-211143_logcheck | dev | 17 Nov 21:11 | 0.2 min | 2 | 0 Wh (est.) |  |
| 20261117-213155_hard | dev | 17 Nov 21:31 | 2.7 min | 119 | 3 Wh (est.) |  |
| 20261117-213618_gpucheck | dev | 17 Nov 21:36 | 0.6 min | 17 | 1 Wh (est.) |  |
| 20261117-220255_smoke-q4 | dev | 17 Nov 22:02 | 0.5 min | 5 | 1 Wh (est.) |  |
| 20261117-220336_mx-gemma-4-e4b+gemma-4-e4b-prompts | grid | 17 Nov 22:03 | 3.2 min | 230 | 4 Wh (est.) |  |
| 20261117-220649_mx-gemma-4-e4b+qwen3-4b-prompts | grid | 17 Nov 22:06 | 7.5 min | 260 | 9 Wh (est.) |  |
| 20261117-221418_mx-qwen3-4b+gemma-4-e4b-prompts | grid | 17 Nov 22:14 | 7.2 min | 252 | 9 Wh (est.) |  |
| 20261117-222129_mx-qwen3-4b+qwen3-4b-prompts | grid | 17 Nov 22:21 | 10.3 min | 264 | 12 Wh (est.) |  |
| 20261117-223147_mx-gemma-4-e4b+qwen3-1.7b-prompts | grid | 17 Nov 22:31 | 5.9 min | 285 | 7 Wh (est.) |  |
| 20261117-223741_mx-qwen3-1.7b+gemma-4-e4b-prompts | grid | 17 Nov 22:37 | 4.6 min | 267 | 6 Wh (est.) |  |
| 20261117-224220_mx-gemma-4-e4b+gemma-4-e4b-prompts_v2 | grid | 17 Nov 22:42 | 3.3 min | 210 | 4 Wh (est.) |  |
| 20261117-224537_mx-gemma-4-e4b+qwen3-4b-prompts_v2 | grid | 17 Nov 22:45 | 9.2 min | 272 | 11 Wh (est.) |  |
| 20261117-225449_mx-qwen3-4b+gemma-4-e4b-prompts_v2 | grid | 17 Nov 22:54 | 6.0 min | 215 | 7 Wh (est.) |  |
| 20261117-230049_mx-qwen3-4b+qwen3-4b-prompts_v2 | grid | 17 Nov 23:00 | 11.6 min | 260 | 14 Wh (est.) |  |
| 20261117-231226_mx-gemma-4-e4b+qwen3-1.7b-prompts_v2 | grid | 17 Nov 23:12 | 5.7 min | 286 | 7 Wh (est.) |  |
| 20261117-231809_mx-qwen3-1.7b+gemma-4-e4b-prompts_v2 | grid | 17 Nov 23:18 | 4.3 min | 225 | 5 Wh (est.) |  |
| 20261117-232245_mx-gemma-4-e4b+gemma-4-e4b-prompts_v2_tools-tools | grid | 17 Nov 23:22 | 3.8 min | 210 | 5 Wh (est.) |  |
| 20261117-232634_mx-qwen3-4b+qwen3-4b-prompts_v2_tools-tools | grid | 17 Nov 23:26 | 13.0 min | 256 | 16 Wh (est.) |  |
| agent_20261117-220823_fake-test | agent | 17 Nov 22:08 | 0.0 min | 3 | - | fake runtime |
| agent_20261117-233935_gemma-core | agent | 17 Nov 23:39 | 1.5 min | 30 | 2 Wh (est.) |  |
| agent_20261117-234103_qwen4b-core | agent | 17 Nov 23:41 | 2.3 min | 30 | 3 Wh (est.) |  |
| agent_20261117-234322_qwen17-core | agent | 17 Nov 23:43 | 1.5 min | 30 | 2 Wh (est.) |  |
| agent_20261117-234450_gemma-all | agent | 17 Nov 23:44 | 1.8 min | 30 | 2 Wh (est.) |  |
| agent_20261117-234636_qwen4b-all | agent | 17 Nov 23:46 | 3.1 min | 30 | 4 Wh (est.) |  |
| agent_20261117-234942_qwen17-all | agent | 17 Nov 23:49 | 1.3 min | 30 | 2 Wh (est.) |  |
| agent_20261117-235100_gemma+gemma | agent | 17 Nov 23:51 | 2.0 min | 30 | 2 Wh (est.) |  |
| agent_20261117-235258_gemma+qwen4b | agent | 17 Nov 23:52 | 3.6 min | 30 | 4 Wh (est.) |  |
| agent_20261117-235634_qwen4b+gemma | agent | 17 Nov 23:56 | 3.0 min | 30 | 4 Wh (est.) |  |
| agent_20261117-235931_qwen4b+qwen4b | agent | 17 Nov 23:59 | 4.2 min | 30 | 5 Wh (est.) |  |
| agent_20261118-023811_gemma+qwen4b-retry | agent | 18 Nov 02:38 | 4.4 min | 30 | 6 Wh |  |
| agent_20261118-024235_qwen4b+qwen4b-retry | agent | 18 Nov 02:42 | 5.7 min | 30 | 7 Wh |  |
| bench_facts_20261118-022257 | facts | 18 Nov 02:22 | 8.7 min | 116 | 11 Wh |  |
| bench_facts_20261118-023139 | facts | 18 Nov 02:31 | 6.2 min | 50 | 8 Wh |  |
| bench_hhem_20261118-015131 | hhem | 18 Nov 01:51 | 13.6 min | 408 | 16 Wh (est.) |  |
| bench_hhem_20261118-020507 | hhem | 18 Nov 02:05 | 11.9 min | 200 | 14 Wh |  |
| bench_hhem_20261118-021701 | hhem | 18 Nov 02:17 | 5.9 min | 200 | 6 Wh |  |
| bench_lmeval_20261118-000408 | lmeval | 18 Nov 00:04 | 11.0 min | 100 | 13 Wh (est.) |  |
| bench_lmeval_20261118-001507 | lmeval | 18 Nov 00:15 | 6.6 min | 28 | 8 Wh (est.) |  |
| bench_lmeval_20261118-002145 | lmeval | 18 Nov 00:21 | 9.9 min | 100 | 12 Wh (est.) |  |
| bench_lmeval_20261118-003139 | lmeval | 18 Nov 00:31 | 4.4 min | 28 | 5 Wh (est.) |  |
| bench_lmeval_20261118-003604 | lmeval | 18 Nov 00:36 | 4.8 min | 100 | 6 Wh (est.) |  |
| bench_lmeval_20261118-004054 | lmeval | 18 Nov 00:40 | 2.8 min | 28 | 3 Wh (est.) |  |
| bench_ragtruth_20261118-004343 | ragtruth | 18 Nov 00:43 | 16.2 min | 300 | 19 Wh (est.) |  |
| bench_ragtruth_20261118-005955 | ragtruth | 18 Nov 00:59 | 13.1 min | 300 | 16 Wh (est.) |  |
| bench_ragtruth_20261118-011303 | ragtruth | 18 Nov 01:13 | 26.8 min | 300 | 32 Wh (est.) |  |
| bench_ragtruth_20261118-013954 | ragtruth | 18 Nov 01:39 | 11.6 min | 300 | 14 Wh (est.) |  |
