# Reflection Lab · project memory for Claude Code

## Goal
Find out whether a **Generator → Critic → Refiner** loop with two small on-device models reduces
hallucinations compared with one model alone:

- **Analyst:** Gemma 4 E4B (`.litertlm`, LiteRT-LM) writes a draft answer from a document. This draft is the **baseline**.
- **Critic:** Qwen3 1.7B (or 4B) audits the draft against the document and lists problems.
- **Refiner:** Gemma rewrites the draft using the audit. This is the **final** answer.

This is Phase 1 (PC prototyping). The phone port (Android, LiteRT-LM) comes later. Use the same
`.litertlm` files the phone would use.

## Machine used for the experiments
Windows laptop · AMD Ryzen 7 5800H · 16 GB RAM · NVIDIA RTX 3060 Laptop GPU with **6 GB VRAM**.
Machine-specific paths (model folders, download folder, token file) live in `config.local.toml` and
`CLAUDE.local.md`, both git-ignored. `config.local.toml` is merged over `config.toml` by `load_config()`.
Pinned files (catalog `file`): `gemma-4-E4B-it.litertlm` (the phone/Android file; `-gpu` is the web
build), `Qwen3_1.7B.litertlm` (int8, chosen over the int4 wi4b32 file) and `qwen3_4b_mixed_int4.litertlm`.
RAM is the tight resource on a 16 GB laptop: check free memory before real runs.

## Ground rules
1. **The owner wants to see what is going on.**
   - Before every command, say in one plain line what it does and why.
   - Short commands (under ~1 min): run them directly, then summarise the result in 2–5 lines.
   - Long jobs (scanning <model-folder>, downloads, experiments): start them in a **separate window** with
     `.\open_window.ps1 <script> <args>` so the owner watches the live view. Then follow progress by
     reading the files (`runs\LATEST.txt` → `state.json`, `transcript.md`, `events.jsonl`;
     `reports\*.md`) and report back.
   - After each phase: a short summary of what worked, what failed, and what's next.
2. **Stop and ask the owner before:** installing anything outside `.venv` (winget, system Python,
   drivers, CUDA), any download over 1 GB, changing which models are used, deleting anything.
3. **The owner's files are read-only.** Never move, rename, copy or delete anything outside this project
   folder. Use existing models where they are, by path (`models.local.json`, or `[paths]` in
   `config.toml`). Never copy multi-GB model files.
4. Never print, log or commit Hugging Face tokens.
5. `tests/cases.jsonl` is the frozen test set. Don't edit it after the first real run unless the owner
   asks, and never train on it. To add cases, edit `tests/make_cases.py` and regenerate, before real runs.
   The same applies to `tests/cases_hard.jsonl` (from `tests/make_cases_hard.py`) once it has had a real
   run. Never tune cases on model outputs: write them from failure patterns, freeze, then run.
6. Fix problems in `lab/` and `scripts/` properly rather than with one-off workarounds. Keep every script
   runnable on its own with `--help`.

## Layout
```
bootstrap.ps1            create .venv, install packages, run the environment check
open_window.ps1          run a script in its own PowerShell window (live view)
config.toml              roles, backends, generation settings, scan folders, model catalog
models.local.json        (generated) catalog key -> local .litertlm path
prompts/                 analyst.txt, critic.txt, refiner.txt  ({document} {question} {draft} {audit})
tests/cases.jsonl        30 starter cases: answerable, numeric, trap, counterfactual, multihop
tests/make_cases.py      source of the cases
tests/cases_hard.jsonl   42 harder cases (2026-11-17): adds false_premise and partial; longer documents.
                         Frozen before its first run, sha256 0d3d080f…5aff0855 (independently reviewed first)
tests/make_cases_hard.py source of the hard cases (--help); run with run_experiment.py --cases tests\cases_hard.jsonl
tests/cases_fresh.jsonl  32 hold-out cases with built-in "check" rules (make_cases_fresh.py), for judging prompt changes
tests/rules.json         grading rules for the frozen starter + hard sets (case files stay untouched)
tests/agent_tasks.jsonl  30 tool-use tasks in 6 levels (make_agent_tasks.py), shop world in lab/agent_env.py
prompts_v2/              analyst/critic/refiner v2: calculations count as supported, critic must quote evidence,
                         refiner may not delete correct calculations (use with run_experiment.py --prompts prompts_v2)
prompts_agent/           verifier.txt + refiner.txt for the agent verify loop
scripts/autoscore.py     rule-based grading (labels_auto.jsonl, review.md, --compare, --apply); agreed 144/144 with
                         Claude's manual labels on pilot2 + hard (rules tuned on those, so spot-check new runs)
scripts/run_matrix.py    many analyst:critic:prompts configs in a row on the merged sets, auto-graded
scripts/matrix_report.py single vs loop per config and per set (starter / hard / fresh), McNemar
scripts/run_agent_bench.py  tool-use benchmark, --tools core|all, optional --verifier loop
scripts/compute_logger.py  GPU power/load, VRAM, CPU, RAM every 5 s -> runs/compute/samples.csv (own window, Ctrl+C)
scripts/compute_report.py  time + compute per run, per experiment, per model, loop cost per question, GPU energy
                         (measured where the logger ran, else estimated), Claude session tokens -> reports/compute.md
scripts/facts_numbers.py   numbers in FACTS outputs that are in none of the call's inputs, by stage and prompt length
                         (no model) -> reports/facts_numbers.md
lab/common.py            config, paths, console, json helpers (stdlib-only)
lab/llm.py               runtimes: python (litert_lm), cli (litert-lm command), fake (no model)
lab/monitor.py           RAM / VRAM / GPU temperature sampler for the live view
scripts/check_env.py     what's installed / missing  -> reports/env_report.md
scripts/find_models.py   read-only scan for model files -> reports/model_inventory.md, models.local.json
scripts/get_models.py    status / --plan / --required --yes downloads from Hugging Face -> [download] dir
scripts/run_experiment.py  the 3-stage pipeline with live view -> runs/<stamp>_<name>/
scripts/label.py         blind A/B labelling by the owner (interactive)
scripts/report.py        rates, 95% CIs, McNemar test, critic precision/recall -> runs/<dir>/report.md
```

## Resuming work
Long jobs are resumable: `run_experiment.py --resume runs\<dir>`, `run_matrix.py --index <index.json>`,
`run_queue.py <queue> --from N`. The queue and the matrix commit to git after every job/config
(`git_snapshot` in lab/common.py, never pushes). The current run state and checklist are in CLAUDE.local.md.

## Hardware notes
- VRAM per model (measured): Gemma E4B ~3.0 GB, Qwen3 4B ~4.2 GB. It stays flat while a model is loaded;
  that is expected. Both together (7.2 GB) do not fit in 6 GB, so keep mode = "swap" for those pairs.
- Under sustained load the RTX 3060 reaches 87 °C and the driver applies software thermal slowdown
  (1.25 of 2.1 GHz). Results are unaffected; runs are slower. Fan mode / cooling helps.

## First session: phases
**Phase 0 · Orient.** Read README.md and this file. Run `dir <model-folder>` and fix
`scan.named_folders` in `config.toml` if the real folder names differ (ask if unclear).

**Phase 1 · Environment.** Run `powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1`.
Show the owner the summary of `reports\env_report.md`. Resolve MISSING items (ask first for anything
system-wide). Keep the `--probe-api` output in mind: it lists the installed `litert_lm` API.

**Phase 2 · What models are already there.** `.\open_window.ps1 scripts\find_models.py`
(a scan of all of <model-folder> can take several minutes). Then read `reports\model_inventory.md` and give a
short summary: LiteRT-ready models, convertible HF checkpoints, GGUF models, image models, and which
project models were matched. If a needed model exists in another format (HF checkpoint), note it, but
don't convert yet: downloading the ready `.litertlm` is faster.

**Phase 3 · Get missing models.** `python scripts\get_models.py --plan` → show the files and sizes →
ask the owner → `.\open_window.ps1 scripts\get_models.py --required --yes`.
Optional extras: `--get qwen3-4b gemma-4-e2b`.

**Phase 4 · Pipeline check without models.** `.\open_window.ps1 scripts\run_experiment.py --runtime fake --limit 3`.
Confirm the live view renders properly in the owner's terminal.

**Phase 5 · Smoke test with real models.** `.\open_window.ps1 scripts\run_experiment.py --limit 2 --name smoke`.
Then check `state.json`, `events.jsonl` and `transcript.md`:
- Load or GPU errors → retry with `--analyst-backend cpu` and/or `--critic-backend cpu` (and tell the owner).
- Out of VRAM → keep `mode = "swap"` and/or run the critic on CPU.
- Qwen3 thinking: look for `had_thinking` / `thinking_truncated` flags. If thinking is truncated, raise
  `max_output_tokens` or use the `qwen3-0.6b-nothink` file to compare.
- Show the owner one full example (draft, audit, final) from `transcript.md`, plus timings and peak VRAM.

**Phase 6 · Full run.** `.\open_window.ps1 scripts\run_experiment.py --name pilot` (30 cases).
Then the owner labels in their own window: `.\open_window.ps1 scripts\label.py` (interactive: you
can't answer for the owner). Then `python scripts\report.py`, and summarise `report.md`.

## Verified facts / known uncertainties
- `litert-lm-api` 0.19.2 (PyPI, Windows wheel available), `import litert_lm`. Verified API:
  `Engine(model_path, backend=Backend.GPU()|Backend.CPU(), max_num_tokens=...)` (context manager);
  `engine.create_conversation(thinking_config=ThinkingConfig(enable_thinking, thinking_token_budget),
  sampler_config=SamplerConfig(top_k, top_p, temperature, seed), max_output_tokens=..., system_message=...)`;
  `conv.send_message(str) -> Message` (dict subclass, text at `["content"][0]["text"]`);
  `conv.send_message_async(str) -> iterator of Message chunks`.
- **Verified on this machine (2026-11-17, smoke + 30-case pilot, swap mode):** GPU backend works on
  Windows + RTX 3060 for both `gemma-4-E4B-it.litertlm` and `Qwen3_1.7B.litertlm`. Peak VRAM 3.0 GB
  (one model at a time). Load: Gemma 17.5 s cold, about 4 s once the file is in the Windows cache; Qwen
  5 to 12 s. Calls about 1 s each; the whole pilot took 92 s. `enable_thinking=False` works for Qwen3
  (no `<think>` in 30 audits). Still unverified: whether stream chunks are deltas or cumulative
  (`lab/llm.py` handles both).
- **Critic format quirk (Qwen3 1.7B):** it often writes `VERDICT: OK` and then tagged lines anyway
  (every pilot audit had a `[MISSING]` line). The first pilot (`runs\20261117-205818_pilot`) used the old
  rule (tagged lines override OK), so all 30 became ISSUES and all were refined. Since then
  `[generation] verdict_source = "verdict_line"` (owner's choice): the VERDICT line decides, lines are
  only counted, and `audit_ok_with_lines` marks the contradiction. `runs\20261117-210715_pilot2` is the
  run to label: 15 OK / 15 ISSUES, 15 refined. Drafts and audits were identical across both pilots
  (greedy decoding is reproducible on this machine).
- **Pilot2 result (labelled by Claude at the owner's request, blind A/B; trail in
  `runs\20261117-210715_pilot2\claude_labelling\`):** Gemma alone 27/30 correct, **0 hallucinations**;
  the loop fixed 0 and broke 0. Gemma's 3 misses were arithmetic left undone (n01, n04) and one wrong
  refusal on an inference (m04), not inventions. Critic precision 13%, recall 67% (2/3); it flags
  correct "the document does not say" refusals on every trap. The refiner ignored all false alarms.
  Conclusion: the 30 starter cases are too easy to show an effect; harder cases are the next step.
- **Hard-set result (`runs\20261117-213155_hard`, 42 cases, Claude-labelled blind):** Gemma alone 34/42
  correct, 1 hallucination (hn04, an arithmetic slip stated as fact); it handled every trap, false
  premise, partial and counterfactual. Its misses are unfinished arithmetic/inference (5 incomplete,
  2 wrong refusals). **The loop made things worse: 30/42 correct, fixed 0, broke 4** (hn02, hn03, hn06,
  hm01): the Qwen3 1.7B critic calls correct *derived* numbers wrong or "not stated", and the refiner
  defers to it. Critic precision 20%, recall 88% (flags 35/42). Over both sets: fixed 0, broke 4.
  The failure is in the critic/refiner prompts' handling of inference, not in Gemma.
- GPU check (2026-11-17): both models run on the RTX 3060's "3D" engine (Task Manager: GPU 1, NVIDIA),
  90-100% while answering; the idle stretches are model loads (4-5 s each, disk/CPU).
  `report.py` prints who labelled (`labeller` field; missing = owner via label.py).
- **Console noise:** LiteRT-LM prints ~180 harmless INFO/WARNING lines per model load (no NPU found,
  `Failed to get buffer requirements for tensor kv_cache_*`, unused audio/vision encoder). `[run]
  runtime_log_level = "error"` calls `litert_lm.set_min_log_severity` before each Engine and silences
  them (verified: 0 lines). Set it to "warning" or "info" when debugging a load or GPU problem.
- `get_models.py` uses the catalog `file` when set; otherwise it picks the smallest non-web `.litertlm`
  and prints the alternatives. Read the model card before trusting the heuristic: for Gemma 4 the
  smallest non-"web" file (`-gpu`) is actually the web build. `--plan` never downloads.
- Fallback runtime: `runtime = "cli"` uses the `litert-lm` command (install with `bootstrap.ps1 -WithCli`).
  It reloads the model on every call, so it is slow, but it isolates Python API problems.
- Greedy decoding (`top_k = 1`, seed 0) is on, so runs are comparable. The owner's PC and phone can still differ slightly.

## Useful commands
```
.\.venv\Scripts\Activate.ps1
python scripts\check_env.py --probe-api
python scripts\find_models.py --root <local-path>/folder
python scripts\get_models.py
python scripts\run_experiment.py --ids t01,t06,n04 --name traps
python scripts\run_experiment.py --resume runs\<folder>
python scripts\run_experiment.py --critic qwen3-4b --critic-backend cpu --name critic4b
python scripts\report.py --compare runs\<A> runs\<B>
```

## Definition of done (session 1)
- No MISSING core items in `reports\env_report.md`.
- `reports\model_inventory.md` exists, and the required models are present and registered.
- Smoke test: 2 cases through all 3 stages with real models, with timings and peak VRAM reported.
- Full pilot run done (or running), and the owner knows how to label and get the report.

## Later (only when the owner asks)
More test cases (200–500), public benchmarks (FACTS Grounding, Vectara HHEM, RAGTruth for the critic),
circuit tracing of Qwen3 (Neuronpedia / Colab), LoRA fine-tuning (Colab, Unsloth), conversion with
`litert-torch export_hf` (needs more than 16 GB RAM for E4B; use Kaggle), phone port.

## Local notes
@CLAUDE.local.md
