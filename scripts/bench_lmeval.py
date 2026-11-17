"""Run lm-evaluation-harness generate_until tasks on a LiteRT-LM model (lm_eval model "litert").

    python scripts/bench_lmeval.py --runtime fake --limit 2                 test the script, no model
    python scripts/bench_lmeval.py --model gemma-4-e4b                      gsm8k_cot, ifeval, mmlu_pro (50 each)
    python scripts/bench_lmeval.py --model qwen3-1.7b --tasks gsm8k_cot --limit 100

Default tasks (output_type generate_until in the installed lm_eval 0.4.13, checked 2026-11-17):
  gsm8k_cot   8-shot chain of thought; exact match, "strict-match" ("The answer is N.") and "flexible-extract"
  ifeval      0-shot instruction following; prompt/instruction-level strict and loose accuracy
  mmlu_pro    5-shot chain of thought over 14 subject subtasks; exact match on "the answer is (X)"
--limit is per task. For a group such as mmlu_pro it is split over the subtasks (ceil(limit / 14) each, so
50 -> 4 per subject = 56 questions). lm_eval takes the FIRST N documents of each (sub)task, not a random sample.
mmlu_pro asks for max_gen_toks 2048 and ifeval 1280; the model class clips each request so prompt + answer fit
max_num_tokens (config, or --max-num-tokens), and summary.md reports how many were clipped.
Results: runs/bench_lmeval_<stamp>/ with summary.md, results.jsonl (one line per scored document),
calls.jsonl (one line per model call) and lm_eval_results.json (lm_eval's full output).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# ifeval needs NLTK's punkt_tab; keep that download inside the project instead of %APPDATA%.
os.environ.setdefault("NLTK_DATA", str(ROOT / ".venv" / "nltk_data"))
Path(os.environ["NLTK_DATA"]).mkdir(parents=True, exist_ok=True)

from lab.bench_common import add_common_args, finish_meta, md_table, setup, write_jsonl  # noqa: E402
from lab.common import ok, step  # noqa: E402

DEFAULT_TASKS = "gsm8k_cot,ifeval,mmlu_pro"
SKIP_KEYS = {"doc", "arguments", "resps", "filtered_resps", "doc_hash", "prompt_hash", "target_hash", "metrics"}


def metric_rows(task: str, res: dict, n: int) -> list[list]:
    rows = []
    for key, val in res.items():
        if "," not in key or "_stderr" in key or not isinstance(val, (int, float)):
            continue
        metric, filt = key.split(",", 1)
        se = res.get(f"{metric}_stderr,{filt}")
        rows.append([task, metric, filt, f"{100 * val:.1f}",
                     f"{100 * se:.1f}" if isinstance(se, (int, float)) else "-", n])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap, n_default=50, critic="none")
    ap.add_argument("--tasks", default=DEFAULT_TASKS, help=f"comma-separated lm_eval task names (default {DEFAULT_TASKS})")
    ap.add_argument("--num-fewshot", type=int, help="override the tasks' few-shot count")
    ap.add_argument("--max-gen-toks", type=int, default=0, help="cap on max_gen_toks for every request (default: none)")
    ap.add_argument("--bootstrap-iters", type=int, default=1000, help="lm_eval bootstrap iterations for stderr")
    args = ap.parse_args()
    cfg, gen, run_dir = setup(args, "lmeval")

    import lm_eval
    from lm_eval.tasks import TaskManager

    from lab.lmeval_litert import LiteRTLM  # registers "litert"

    tm = TaskManager()
    lm = LiteRTLM(key=args.model, runtime=args.runtime, backend=args.backend,
                  max_num_tokens=gen.get("max_num_tokens"), max_gen_toks=args.max_gen_toks or None,
                  seed=args.seed, log_path=str(run_dir / "calls.jsonl"))
    rows, samples_out, raw = [], [], {}
    try:
        for task in [t.strip() for t in args.tasks.split(",") if t.strip()]:
            leaves = list(tm.load([task])["tasks"])
            per = math.ceil(args.n / len(leaves)) if len(leaves) > 1 else args.n
            step(f"{task}: {len(leaves)} subtask(s), limit {per} per subtask")
            res = lm_eval.simple_evaluate(
                model=lm, tasks=[task], num_fewshot=args.num_fewshot, limit=per, task_manager=tm,
                log_samples=True, bootstrap_iters=args.bootstrap_iters, random_seed=args.seed,
                numpy_random_seed=args.seed, torch_random_seed=args.seed, fewshot_random_seed=args.seed)
            if res is None:
                continue
            nsamp = res.get("n-samples", {})
            n_task = sum(v.get("effective", 0) for k, v in nsamp.items() if k in leaves)
            top = res.get("groups", {}).get(task) or res["results"].get(task, {})
            rows += metric_rows(task, top, n_task)
            for sub, items in res.get("samples", {}).items():
                for s in items:
                    resp = s.get("resps") or [[""]]
                    samples_out.append({
                        "task": sub, "doc_id": s.get("doc_id"), "target": s.get("target"),
                        "response": resp[0][0] if resp and resp[0] else "",
                        "filtered": s.get("filtered_resps"), "filter": s.get("filter"),
                        "scores": {k: v for k, v in s.items() if k not in SKIP_KEYS
                                   and k not in ("doc_id", "target", "filter")}})
            raw[task] = {k: v for k, v in res.items() if k != "samples"}
    finally:
        lm.close()

    write_jsonl(run_dir / "results.jsonl", samples_out)
    (run_dir / "lm_eval_results.json").write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")
    table = md_table(["task", "metric", "filter", "score %", "stderr %", "n"], rows)
    st = lm.stats
    out = [
        f"# lm-evaluation-harness · {run_dir.name}", "",
        f"- model: `{args.model}` ({args.backend}, runtime {args.runtime}) through lab/lmeval_litert.py, greedy, "
        f"max_num_tokens {gen.get('max_num_tokens')}",
        f"- tasks: {args.tasks} · limit {args.n} per task (first N documents; split over subtasks of a group) · "
        f"few-shot {'task default' if args.num_fewshot is None else args.num_fewshot}",
        f"- requests {st['requests']} · clipped to fit the context {st['clipped']} · cut at a stop string "
        f"{st['cut_at_stop']} · errors {st['errors']} · generation time {st['seconds'] / 60:.1f} min", "",
        table, "",
        "Scores are lm_eval's own metrics. Each request was one user message in a fresh conversation (the model's",
        "chat template applied by LiteRT-LM), so they are not directly comparable with base-model leaderboard runs.",
    ]
    (run_dir / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    finish_meta(run_dir, stats=st)
    print("\n" + table)
    ok(f"Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
