# Agent benchmark · agent_20261118-023811_gemma+qwen4b-retry

Agent **gemma-4-e4b** · tools core · verifier qwen3-4b · 30 tasks

| level | n | success | answer ok | calls ok | avg calls | success after verify | fixed | broke |
|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 5 | 5 | 5 | 1.0 | 5 | 0 | 0 |
| 2 | 6 | 6 | 6 | 6 | 1.7 | 6 | 0 | 0 |
| 3 | 5 | 2 | 2 | 5 | 3.2 | 3 | 1 | 0 |
| 4 | 5 | 2 | 3 | 2 | 3.6 | 3 | 1 | 0 |
| 5 | 5 | 4 | 4 | 5 | 1.0 | 4 | 0 | 0 |
| 6 | 4 | 2 | 2 | 4 | 4.5 | 1 | 0 | 1 |
| all | 30 | 21 | 22 | 27 | 2.4 | 22 | 2 | 1 |

Failed: ag12, ag14, ag15, ag17, ag18, ag19, ag22, ag28, ag30
Errors: 0