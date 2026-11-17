# Reflection Lab

Can two small language models that fit on a phone catch each other's mistakes? This repository tests
that on a laptop GPU, with the same `.litertlm` model files an Android phone runs through
[LiteRT-LM](https://ai.google.dev/edge/litert-lm). One model answers a question from a document. A
second model checks the answer against the document. The first model then rewrites its answer, but
only if the check found a problem.

![The analyst, critic and refiner loop](docs/img/loop.svg)

## Goal

Small on-device models hallucinate: they state things the source document does not say, or get a
number wrong. The cheapest fix on a phone is a second small model acting as a critic. This project
measures whether that loop gives more correct answers than the first model alone, what it costs in
time, and how often it turns a correct answer into a wrong one.

Everything is measured on the same questions twice. The analyst's draft is the one-model baseline and
the loop's final answer is compared with it, question by question, with McNemar's exact test.

## The loop

```mermaid
flowchart LR
    D["Document + question"] --> A["Analyst<br/>(Gemma 4 E4B)"]
    A -->|"draft = one-model answer"| C["Critic<br/>(second model)"]
    C -->|"VERDICT: OK"| K["Keep the draft"]
    C -->|"VERDICT: ISSUES<br/>+ quoted evidence"| R["Refiner<br/>(analyst rewrites)"]
    K --> F["Final answer"]
    R --> F
```

The critic must start its reply with `VERDICT: OK` or `VERDICT: ISSUES`, then list problems tagged
`[UNSUPPORTED]`, `[WRONG]` or `[MISSING]`. The verdict line decides whether the refiner runs. Prompts
live in [`prompts/`](prompts) (first version), [`prompts_v2/`](prompts_v2) (calculations count as
supported, every issue must quote the document, the refiner may not delete a correct calculation) and
[`prompts_v2_tools/`](prompts_v2_tools) (v2 plus a calculator and a date tool for the analyst).

## Models and hardware

| Model | File | Size | Role | GPU memory |
|---|---|---|---|---|
| Gemma 4 E4B | `gemma-4-E4B-it.litertlm` | 3.4 GB | analyst, also tried as critic | about 3.0 GB |
| Qwen3 4B | `qwen3_4b_mixed_int4.litertlm` | 2.3 GB | critic, also tried as analyst | about 4.2 GB |
| Qwen3 1.7B | `Qwen3_1.7B.litertlm` (int8) | 1.6 GB | first critic | under 3 GB |

All three come from the [litert-community](https://huggingface.co/litert-community) repositories on
Hugging Face. The Gemma file is the one the Android app loads (the `-gpu` file in the same repository
is the web build). Runs use the LiteRT-LM Python API 0.19.2 on the GPU backend with greedy decoding
(`top_k = 1`, seed 0) and thinking turned off, so a rerun gives the same text. The test machine is a
Windows 11 laptop with an RTX 3060 Laptop GPU (6 GB), a Ryzen 7 5800H and 16 GB of RAM. Two models do
not fit in 6 GB together, so the pipeline loads one model at a time ("swap" mode): all drafts, then all
audits, then all rewrites.

## Test sets

All documents are fictional, so a model cannot answer from memory. The counterfactual documents
contradict real facts on purpose (emperor penguins breeding in the Arctic, a Soviet Moon landing in
1971), and the answer has to follow the document.

| Set | Cases | What it checks |
|---|---|---|
| [`tests/cases.jsonl`](tests/cases.jsonl) | 30 | starter set: answerable, numeric, trap (answer not in the text), counterfactual, multi-hop |
| [`tests/cases_hard.jsonl`](tests/cases_hard.jsonl) | 42 | longer documents with near-miss numbers, corrected values, superseded rules, false premises ("Why did the board reject...?" when no decision was taken), half-answerable questions |
| [`tests/cases_fresh.jsonl`](tests/cases_fresh.jsonl) | 32 | hold-out set written after the hard-set results, used to judge prompt changes fairly |
| [`tests/agent_tasks.jsonl`](tests/agent_tasks.jsonl) | 30 | tool-use tasks in a small shop world (see below) |

Each set was written from known failure patterns before any model saw it, then frozen. An independent
review checked every reference answer of the hard set before its first run.

## Grading

Every answer gets one label: **c** correct, **h** hallucination (states something the document does
not support, including an invented answer to a trap), **i** incomplete (nothing false, but part of the
question unanswered) or **r** wrong refusal ("the document does not say" when it does).

The starter and hard runs were labelled blind: answers were shuffled into A and B, labelled, and only
then was the critic's audit shown. For the larger grid, [`scripts/autoscore.py`](scripts/autoscore.py)
applies per-case rules (the value the answer must contain, whether it must say "not stated", world
knowledge that marks a hallucination, and any number that appears nowhere in the document). It agreed
with all 144 manual labels on those two runs. Answers it is unsure about go to a review sheet.

```mermaid
flowchart LR
    T["Test sets"] --> X["run_experiment.py<br/>draft, audit, rewrite"]
    X --> S["state.json<br/>transcript.md"]
    S --> G["autoscore.py<br/>rules per case"]
    S --> L["blind A/B labels"]
    G --> M["matrix_report.py<br/>single vs loop, McNemar"]
    L --> M
```

## Results so far

Status on 17 November 2026. The combination grid, the agent benchmark and the standard benchmarks are
still running.

| Run | Analyst | Critic | Prompts | Correct, one model | Correct, with loop | Fixed | Broken |
|---|---|---|---|---|---|---|---|
| starter set | Gemma 4 E4B | Qwen3 1.7B | v1 | 27 / 30 | 27 / 30 | 0 | 0 |
| hard set | Gemma 4 E4B | Qwen3 1.7B | v1 | 34 / 42 | 30 / 42 | 0 | 4 |
| all 104 cases | Gemma 4 E4B | Gemma 4 E4B | v1 | 88 / 104 | 89 / 104 | 3 | 2 |

Gemma 4 E4B rarely hallucinates on these documents: one invented fact in the 42 hard cases. It handled
every trap, false premise and counterfactual. Its mistakes are calculations it leaves unfinished. It
quotes "385 million and 412 million" but never says "27 million", or it answers "the document does not
say" when the answer takes one subtraction. The Qwen3 1.7B critic made this worse, because it treats a
calculated number as unsupported. In four hard cases it called a correct difference wrong and the
rewrite deleted it. Gemma checking itself was neutral overall: it finished some calculations and
deleted others.

## Agent benchmark

[`lab/agent_env.py`](lab/agent_env.py) is a small, deterministic shop called Brightwater Outdoor:
four orders, three customers, five products, a policy text, shipping rates and a fixed date
(17 November 2026). It has ten tools (`get_order`, `get_customer`, `get_product`, `list_products`,
`get_shipping_rate`, `search_policy`, `calculator`, `date_add`, `create_refund`, `send_email`) and ten
plausible distractors (currency conversion, weather, stock prices and others) for the limit tests.

```mermaid
sequenceDiagram
    participant T as Task
    participant A as Agent model
    participant S as Shop tools
    participant V as Verifier model
    T->>A: "Return the pack from A-1047 and email the refund ID"
    A->>S: get_order("A-1047")
    S-->>A: order, delivered 2026-11-06
    A->>S: search_policy("returns")
    A->>S: create_refund("A-1047", 116.10)
    A->>S: send_email(...)
    A->>T: answer
    A-->>V: answer + full tool log
    V-->>A: VERDICT, quoted log lines
```

The 30 tasks climb in six levels: a single lookup, two-step chains, policy plus arithmetic, actions
with conditions (a refund only inside the 30-day window), errors and missing data (a flaky service, an
unknown order, a country with no shipping rate), and chains of four to six calls. A task passes only if
the answer is right, every required call was made with the right arguments, and no forbidden action
happened. [`scripts/run_agent_bench.py`](scripts/run_agent_bench.py) runs each model with ten or twenty
tools, alone or with a verifier that checks the answer against the tool log.

## Standard benchmarks

| Benchmark | What it measures here | Script |
|---|---|---|
| [Vectara HHEM leaderboard](https://github.com/vectara/hallucination-leaderboard) | hallucination rate of summaries of the leaderboard's public documents, scored by HHEM-2.1-open on the CPU | [`bench_hhem.py`](scripts/bench_hhem.py) |
| [RAGTruth](https://arxiv.org/abs/2401.00396) | how well each critic detects hallucinated responses (precision, recall, F1) | [`bench_ragtruth.py`](scripts/bench_ragtruth.py) |
| [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | GSM8K (chain of thought), IFEval and MMLU-Pro, 50 questions each, through a LiteRT-LM model class | [`bench_lmeval.py`](scripts/bench_lmeval.py) |
| [FACTS Grounding](https://huggingface.co/datasets/google/FACTS-grounding-public) | 50 public examples that fit a 4k context, judged blind by hand against the FACTS criteria | [`bench_facts.py`](scripts/bench_facts.py) |

## Running it yourself

You need Python 3.11 or newer and about 6 GB of disk for the two default models. A GPU with 4 GB or
more is recommended; the CPU backend works but is slow.

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
./bootstrap.sh
source .venv/bin/activate
```

Then, on any system:

```bash
python scripts/find_models.py                        # read-only scan for models you already have
python scripts/get_models.py --plan                  # files and sizes that would be downloaded
python scripts/get_models.py --required --yes        # Gemma 4 E4B + Qwen3 1.7B into ./models
python scripts/run_experiment.py --runtime fake --limit 3            # pipeline check, no model
python scripts/run_experiment.py --limit 2 --name smoke              # first real test
python scripts/run_experiment.py --cases tests/cases_hard.jsonl --prompts prompts_v2 --name hard
python scripts/autoscore.py --run runs/<folder> --apply              # grade it
python scripts/report.py --run runs/<folder>                         # rates, intervals, McNemar
python scripts/run_matrix.py --preset grid                           # every analyst/critic/prompt pair
python scripts/run_agent_bench.py --model gemma-4-e4b --verifier qwen3-4b
```

Machine-specific settings (your model folders, a download folder outside the project, a Hugging Face
token file) go in `config.local.toml`, which git ignores. Copy
[`config.local.example.toml`](config.local.example.toml) to start. On Windows,
`.\open_window.ps1 scripts\<script>.py <args>` runs a script in its own window with a live view.
[`START_PROMPT.md`](START_PROMPT.md) is a starting prompt for doing all of this with Claude Code, and
[`CLAUDE.md`](CLAUDE.md) holds the project rules and the verified facts about the runtime.

The standard benchmarks need extra packages:
`pip install torch --index-url https://download.pytorch.org/whl/cpu` and then
`pip install -r requirements-bench.txt`.

## Repository layout

```
lab/            runtimes (LiteRT-LM Python API, CLI, fake), config, GPU monitor, shop world, benchmark helpers
scripts/        experiment, grading, reports, grid, queue, agent and standard benchmarks, public export
prompts*/       analyst, critic and refiner prompts (v1, v2, v2 with tools) and the agent verifier prompts
tests/          frozen test sets, their generators, grading rules, agent tasks, FACTS subset
runs/           every run: meta.json, state.json, transcript.md, events.jsonl, labels, reports
docs/img/       illustrations used in this README
```

## Limitations

The sets are small (30, 42 and 32 cases), so the confidence intervals are wide and a difference of a
few answers is not significant. Labels for the starter and hard sets come from an AI labeller (Claude),
done blind, and the grading rules for the larger grid were written by the same hand, so they are
checked against the manual labels and the changed answers are read individually. Everything runs on
one laptop GPU; a phone's GPU may give slightly different text. All prompts and documents are in
English.
