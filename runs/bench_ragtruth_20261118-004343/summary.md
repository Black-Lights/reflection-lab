# RAGTruth critic benchmark · bench_ragtruth_20261118-004343

- critic: `qwen3-1.7b` (gpu, runtime python), prompts `prompts`, greedy decoding
- data: `wandb/RAGTruth-processed` test split; balanced sample of 300 (seed 0), 300 with a prediction, 0 failed calls
- dropped as too long before sampling: none
- critic verdicts: {'ISSUES': 292, 'OK': 8} (OK = clean; ISSUES and UNPARSED = hallucinated; verdict_source `verdict_line`)

| subset | n | P % | R % | F1 % | acc % | P % (weighted) | R % (weighted) | F1 % (weighted) | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|---|
| overall | 300 | 51.4 | 100.0 | 67.9 | 52.7 | 36.5 | 100.0 | 53.5 | 150/142/0/8 |
| QA | 100 | 52.6 | 100.0 | 69.0 | 55.0 | 19.4 | 100.0 | 32.5 | 50/45/0/5 |
| Summary | 100 | 51.5 | 100.0 | 68.0 | 53.0 | 23.8 | 100.0 | 38.4 | 50/47/0/3 |
| Data2txt | 100 | 50.0 | 100.0 | 66.7 | 50.0 | 64.3 | 100.0 | 78.3 | 50/50/0/0 |

Positive class = hallucinated. "Weighted" columns re-weight each (task, label) cell to its share of the full test split, so they estimate what the paper's numbers would be; the unweighted precision is inflated by the 50/50 sample. Recall does not depend on the mix within a task.

## Paper baselines (RAGTruth, arXiv 2401.00396v2, Table 5, response level, full test set)

| method | QA P | QA R | QA F1 | D2T P | D2T R | D2T F1 | Sum P | Sum R | Sum F1 | All P | All R | All F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prompt gpt-3.5-turbo | 18.8 | 84.4 | 30.8 | 65.1 | 95.5 | 77.4 | 23.4 | 89.2 | 37.1 | 37.1 | 92.3 | 52.9 |
| Prompt gpt-4-turbo | 33.2 | 90.6 | 45.6 | 64.3 | 100.0 | 78.3 | 31.5 | 97.6 | 47.6 | 46.9 | 97.9 | 63.4 |
| SelfCheckGPT gpt-3.5-turbo | 35.0 | 58.0 | 43.7 | 68.2 | 82.8 | 74.8 | 31.1 | 56.5 | 40.1 | 49.7 | 71.9 | 58.8 |
| LMvLM gpt-4-turbo | 18.7 | 76.9 | 30.1 | 68.0 | 76.7 | 72.1 | 23.3 | 81.9 | 36.2 | 36.2 | 77.8 | 49.4 |
| Finetuned Llama-2-13B | 61.6 | 76.3 | 68.2 | 85.4 | 91.0 | 88.1 | 64.0 | 54.9 | 59.1 | 76.9 | 80.7 | 78.7 |

The paper's test split and wandb/RAGTruth-processed share the 2,700 test responses (this script does not verify that the two splits are identical item for item).
