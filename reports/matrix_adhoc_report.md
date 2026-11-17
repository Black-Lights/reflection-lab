# Combination matrix

c = correct, h = hallucination. 'single' = the analyst alone (stage 1), 'loop' = after critic + refine. fixed/broke = answers the loop made correct / not correct.

## all

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 104 | 88 | 89 | 2 | 1 | 3 | 2 | 1.000 | 22 | 1.8 |

## starter

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 30 | 27 | 29 | 0 | 0 | 2 | 0 | 0.500 | 5 | 1.8 |

## hard

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 42 | 34 | 33 | 1 | 1 | 0 | 1 | 1.000 | 9 | 1.8 |

## fresh

| analyst | critic | prompts | n | single c | loop c | single h | loop h | fixed | broke | p (McNemar) | flagged | s/case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma-4-e4b | gemma-4-e4b | prompts | 32 | 27 | 27 | 1 | 0 | 1 | 1 | 1.000 | 8 | 1.8 |
