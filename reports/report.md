# Combination matrix

c = correct, h = hallucination. 'single' = the analyst alone (stage 1), 'loop' = after critic + refine. fixed/broke = answers the loop made correct / not correct.

## all

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 104 | 98 | 99 | 5 | 4 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 2 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 104 | 91 | 94 | 7 | 4 | 5 | 2 | 0.453 | 4 | 1 | 0.375 | 48 | 7.4 |

## starter

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 30 | 26 | 29 | 0 | 0 | 3 | 0 | 0.250 | 0 | 0 | 1.000 | 12 | 7.4 |

## hard

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 42 | 39 | 39 | 2 | 2 | 0 | 0 | 1.000 | 0 | 0 | 1.000 | 0 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 42 | 37 | 36 | 3 | 2 | 0 | 1 | 1.000 | 2 | 1 | 1.000 | 21 | 7.4 |

## fresh

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | h removed | h added | p (h) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts_v2_tools | 32 | 29 | 30 | 3 | 2 | 1 | 0 | 1.000 | 1 | 0 | 1.000 | 2 | 2.1 |
| qwen3-4b | qwen3-4b | prompts_v2_tools | 32 | 28 | 29 | 4 | 2 | 2 | 1 | 1.000 | 2 | 0 | 0.500 | 15 | 7.4 |
