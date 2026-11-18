# Combination matrix

c = correct, h = hallucination. 'single' = the analyst alone (stage 1), 'loop' = after critic + refine. fixed/broke = answers the loop made correct / not correct.

## all

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 104 | 89 | 90 | 3 | 1 | 3 | 2 | 1.000 | 2 | 0 | 0.500 | 22 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts | 104 | 89 | 91 | 3 | 1 | 4 | 2 | 0.688 | 2 | 0 | 0.500 | 52 | 4.1 |
| qwen3-4b | gemma-4-e4b | prompts | 104 | 92 | 85 | 6 | 6 | 0 | 7 | 0.016 | 1 | 1 | 1.000 | 44 | 3.9 |
| qwen3-4b | qwen3-4b | prompts | 104 | 92 | 91 | 6 | 6 | 3 | 4 | 1.000 | 2 | 2 | 1.000 | 56 | 5.8 |
| gemma-4-e4b | qwen3-1.7b | prompts | 104 | 89 | 81 | 3 | 1 | 0 | 8 | 0.008 | 2 | 0 | 0.500 | 77 | 3.2 |
| qwen3-1.7b | gemma-4-e4b | prompts | 104 | 74 | 80 | 14 | 8 | 9 | 3 | 0.146 | 6 | 0 | 0.031 | 59 | 2.5 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2 | 104 | 97 | 99 | 6 | 4 | 2 | 0 | 0.500 | 2 | 0 | 0.500 | 2 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts_v2 | 104 | 97 | 97 | 6 | 3 | 4 | 4 | 1.000 | 5 | 2 | 0.453 | 64 | 5.1 |
| qwen3-4b | gemma-4-e4b | prompts_v2 | 104 | 97 | 98 | 7 | 6 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 7 | 3.2 |
| qwen3-4b | qwen3-4b | prompts_v2 | 104 | 97 | 99 | 7 | 5 | 3 | 1 | 0.625 | 3 | 1 | 0.625 | 52 | 6.6 |
| gemma-4-e4b | qwen3-1.7b | prompts_v2 | 104 | 97 | 98 | 6 | 4 | 1 | 0 | 1.000 | 2 | 0 | 0.500 | 78 | 3.1 |
| qwen3-1.7b | gemma-4-e4b | prompts_v2 | 104 | 90 | 92 | 12 | 10 | 2 | 0 | 0.500 | 2 | 0 | 0.500 | 17 | 2.3 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 104 | 101 | 102 | 2 | 1 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 2 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 104 | 92 | 94 | 5 | 4 | 5 | 3 | 0.727 | 3 | 2 | 1.000 | 48 | 7.4 |

## starter

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 30 | 27 | 29 | 0 | 0 | 2 | 0 | 0.500 | 0 | 0 | 1.000 | 5 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts | 30 | 27 | 28 | 0 | 0 | 1 | 0 | 1.000 | 0 | 0 | 1.000 | 10 | 4.1 |
| qwen3-4b | gemma-4-e4b | prompts | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 12 | 3.9 |
| qwen3-4b | qwen3-4b | prompts | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 13 | 5.8 |
| gemma-4-e4b | qwen3-1.7b | prompts | 30 | 27 | 27 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 15 | 3.2 |
| qwen3-1.7b | gemma-4-e4b | prompts | 30 | 25 | 27 | 1 | 0 | 2 | 0 | 0.500 | 1 | 0 | 1.000 | 13 | 2.5 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2 | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts_v2 | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 17 | 5.1 |
| qwen3-4b | gemma-4-e4b | prompts_v2 | 30 | 29 | 29 | 1 | 1 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 2 | 3.2 |
| qwen3-4b | qwen3-4b | prompts_v2 | 30 | 29 | 30 | 1 | 0 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 13 | 6.6 |
| gemma-4-e4b | qwen3-1.7b | prompts_v2 | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 16 | 3.1 |
| qwen3-1.7b | gemma-4-e4b | prompts_v2 | 30 | 29 | 29 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 3 | 2.3 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 30 | 26 | 29 | 0 | 0 | 3 | 0 | 0.250 | 0 | 0 | 1.000 | 12 | 7.4 |

## hard

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 42 | 34 | 33 | 1 | 1 | 0 | 1 | 1.000 | 0 | 0 | 1.000 | 9 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts | 42 | 34 | 34 | 1 | 0 | 1 | 1 | 1.000 | 1 | 0 | 1.000 | 23 | 4.1 |
| qwen3-4b | gemma-4-e4b | prompts | 42 | 35 | 31 | 3 | 2 | 0 | 4 | 0.125 | 1 | 0 | 1.000 | 18 | 3.9 |
| qwen3-4b | qwen3-4b | prompts | 42 | 35 | 34 | 3 | 2 | 1 | 2 | 1.000 | 2 | 1 | 1.000 | 24 | 5.8 |
| gemma-4-e4b | qwen3-1.7b | prompts | 42 | 34 | 30 | 1 | 1 | 0 | 4 | 0.125 | 0 | 0 | 1.000 | 35 | 3.2 |
| qwen3-1.7b | gemma-4-e4b | prompts | 42 | 30 | 32 | 5 | 3 | 3 | 1 | 0.625 | 2 | 0 | 0.500 | 24 | 2.5 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2 | 42 | 39 | 39 | 3 | 3 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts_v2 | 42 | 39 | 38 | 3 | 1 | 1 | 2 | 1.000 | 3 | 1 | 0.625 | 27 | 5.1 |
| qwen3-4b | gemma-4-e4b | prompts_v2 | 42 | 39 | 39 | 3 | 3 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 1 | 3.2 |
| qwen3-4b | qwen3-4b | prompts_v2 | 42 | 39 | 40 | 3 | 2 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 22 | 6.6 |
| gemma-4-e4b | qwen3-1.7b | prompts_v2 | 42 | 39 | 39 | 3 | 2 | 0 | 0 | 1.000 | 1 | 0 | 1.000 | 35 | 3.1 |
| qwen3-1.7b | gemma-4-e4b | prompts_v2 | 42 | 35 | 36 | 6 | 5 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 8 | 2.3 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 42 | 40 | 40 | 1 | 1 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 42 | 38 | 36 | 1 | 2 | 0 | 2 | 0.500 | 1 | 2 | 1.000 | 21 | 7.4 |

## fresh

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 32 | 28 | 28 | 2 | 0 | 1 | 1 | 1.000 | 2 | 0 | 0.500 | 8 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts | 32 | 28 | 29 | 2 | 1 | 2 | 1 | 1.000 | 1 | 0 | 1.000 | 19 | 4.1 |
| qwen3-4b | gemma-4-e4b | prompts | 32 | 27 | 24 | 3 | 4 | 0 | 3 | 0.250 | 0 | 1 | 1.000 | 14 | 3.9 |
| qwen3-4b | qwen3-4b | prompts | 32 | 27 | 27 | 3 | 4 | 2 | 2 | 1.000 | 0 | 1 | 1.000 | 19 | 5.8 |
| gemma-4-e4b | qwen3-1.7b | prompts | 32 | 28 | 24 | 2 | 0 | 0 | 4 | 0.125 | 2 | 0 | 0.500 | 27 | 3.2 |
| qwen3-1.7b | gemma-4-e4b | prompts | 32 | 19 | 21 | 8 | 5 | 4 | 2 | 0.688 | 3 | 0 | 0.250 | 22 | 2.5 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2 | 32 | 28 | 30 | 3 | 1 | 2 | 0 | 0.500 | 2 | 0 | 0.500 | 2 | 1.8 |
| gemma-4-e4b | qwen3-4b | prompts_v2 | 32 | 28 | 29 | 3 | 2 | 3 | 2 | 1.000 | 2 | 1 | 1.000 | 20 | 5.1 |
| qwen3-4b | gemma-4-e4b | prompts_v2 | 32 | 29 | 30 | 3 | 2 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 4 | 3.2 |
| qwen3-4b | qwen3-4b | prompts_v2 | 32 | 29 | 29 | 3 | 3 | 1 | 1 | 1.000 | 1 | 1 | 1.000 | 17 | 6.6 |
| gemma-4-e4b | qwen3-1.7b | prompts_v2 | 32 | 28 | 29 | 3 | 2 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 27 | 3.1 |
| qwen3-1.7b | gemma-4-e4b | prompts_v2 | 32 | 26 | 27 | 6 | 5 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 6 | 2.3 |
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 32 | 31 | 32 | 1 | 0 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 2 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 32 | 28 | 29 | 4 | 2 | 2 | 1 | 1.000 | 2 | 0 | 0.500 | 15 | 7.4 |
