"""Evaluate a critic as a response-level hallucination detector on RAGTruth.

    python scripts/bench_ragtruth.py --runtime fake --n 12                 test the script, no model
    python scripts/bench_ragtruth.py                                       config critic (qwen3-1.7b), 300 responses
    python scripts/bench_ragtruth.py --critic qwen3-4b --prompts prompts   another critic / prompt set

Data: HF dataset wandb/RAGTruth-processed, test split (2,700 responses, 900 each of QA, Summary, Data2txt).
Fields used: id, query (the task's user request), context (the source), output (the response), task_type,
hallucination_labels_processed {evident_conflict, baseless_info}: hallucinated if either count > 0 (this
matches a non-empty hallucination_labels list on all 2,700 rows, checked 2026-11-17); model and quality are kept.

Sample: balanced and stratified, n/6 per (task type, label) cell (default 300 -> 50 per cell), seed 0, after
dropping items whose filled critic prompt is estimated (chars/4) above max_num_tokens - max_output_tokens.
Prediction: prompts/critic.txt with document = context, question = query, draft = output, parsed with
run_experiment.parse_verdict (config verdict_source): OK = no hallucination; ISSUES or UNPARSED = hallucination.

Metrics: precision, recall and F1 of the "hallucinated" class, overall and per task type, on the balanced
sample, plus a "test-set weighted" estimate that re-weights each (task, label) cell to its share of the full
test split, because precision depends on how common hallucinations are and the paper reports on the full split.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.bench_common import (  # noqa: E402
    add_common_args, est_tokens, fill, finish_meta, load_llm, md_table, parse_verdict, prf, run_stage, setup,
    templates, write_jsonl,
)
from lab.common import ok, warn  # noqa: E402

REPO, TEST_FILE = "wandb/RAGTruth-processed", "data/test-00000-of-00001.parquet"
TASKS = ["QA", "Summary", "Data2txt"]
# RAGTruth (arXiv 2401.00396v2), Table 5: response-level detection on the full test set.
# Columns: QA P R F1 | Data-to-text P R F1 | Summarization P R F1 | Overall P R F1.
PAPER = [
    ("Prompt gpt-3.5-turbo", 18.8, 84.4, 30.8, 65.1, 95.5, 77.4, 23.4, 89.2, 37.1, 37.1, 92.3, 52.9),
    ("Prompt gpt-4-turbo", 33.2, 90.6, 45.6, 64.3, 100.0, 78.3, 31.5, 97.6, 47.6, 46.9, 97.9, 63.4),
    ("SelfCheckGPT gpt-3.5-turbo", 35.0, 58.0, 43.7, 68.2, 82.8, 74.8, 31.1, 56.5, 40.1, 49.7, 71.9, 58.8),
    ("LMvLM gpt-4-turbo", 18.7, 76.9, 30.1, 68.0, 76.7, 72.1, 23.3, 81.9, 36.2, 36.2, 77.8, 49.4),
    ("Finetuned Llama-2-13B", 61.6, 76.3, 68.2, 85.4, 91.0, 88.1, 64.0, 54.9, 59.1, 76.9, 80.7, 78.7),
]


def load_test() -> list[dict]:
    import pandas as pd
    from huggingface_hub import hf_hub_download

    df = pd.read_parquet(hf_hub_download(REPO, TEST_FILE, repo_type="dataset"))
    rows = []
    for r in df.itertuples(index=False):
        lab = r.hallucination_labels_processed
        rows.append({"id": f"rt{r.id}", "task_type": r.task_type, "query": r.query, "context": r.context,
                     "output": r.output, "model": r.model, "quality": r.quality,
                     "label": int(lab["evident_conflict"] > 0 or lab["baseless_info"] > 0)})
    return rows


def sample_balanced(rows: list[dict], n: int, seed: int) -> list[dict]:
    cells = [(t, y) for t in TASKS for y in (1, 0)]
    per, extra = divmod(n, len(cells))
    rng = random.Random(seed)
    out = []
    for i, (t, y) in enumerate(cells):
        pool = sorted((r for r in rows if r["task_type"] == t and r["label"] == y), key=lambda r: r["id"])
        k = per + (1 if i < extra else 0)
        if len(pool) < k:
            warn(f"cell {t}/{'hallucinated' if y else 'clean'}: only {len(pool)} items, wanted {k}")
        out += rng.sample(pool, min(k, len(pool)))
    return out


def scores(items: list[dict], weight=lambda it: 1.0) -> list:
    tp = sum(weight(it) for it in items if it["label"] and it["pred"])
    fp = sum(weight(it) for it in items if not it["label"] and it["pred"])
    fn = sum(weight(it) for it in items if it["label"] and not it["pred"])
    tn = sum(weight(it) for it in items if not it["label"] and not it["pred"])
    p, r, f = prf(tp, fp, fn)
    acc = 100 * (tp + tn) / (tp + fp + fn + tn) if items else 0.0
    return [p, r, f, acc]


def write_summary(run_dir: Path, args, items: list[dict], pop: dict, dropped: dict) -> str:
    scored = [it for it in items if "pred" in it]
    samp = {}
    for it in scored:
        samp[(it["task_type"], it["label"])] = samp.get((it["task_type"], it["label"]), 0) + 1

    def w(it):  # cell weight: full-test-split count / sample count
        return pop[(it["task_type"], it["label"])] / samp[(it["task_type"], it["label"])]

    rows = []
    for name, group in [("overall", scored)] + [(t, [it for it in scored if it["task_type"] == t]) for t in TASKS]:
        if not group:
            continue
        cm = [sum(1 for it in group if it["label"] == y and it["pred"] == p) for y, p in ((1, 1), (0, 1), (1, 0), (0, 0))]
        rows.append([name, len(group)] + scores(group) + scores(group, w)[:3] + ["/".join(map(str, cm))])
    table = md_table(["subset", "n", "P %", "R %", "F1 %", "acc %", "P % (weighted)", "R % (weighted)",
                      "F1 % (weighted)", "TP/FP/FN/TN"], rows)
    verdicts = {}
    for it in scored:
        verdicts[it["verdict"]] = verdicts.get(it["verdict"], 0) + 1
    paper = md_table(["method", "QA P", "QA R", "QA F1", "D2T P", "D2T R", "D2T F1", "Sum P", "Sum R", "Sum F1",
                      "All P", "All R", "All F1"], [list(r) for r in PAPER])
    out = [
        f"# RAGTruth critic benchmark · {run_dir.name}", "",
        f"- critic: `{args.critic}` ({args.critic_backend}, runtime {args.runtime}), prompts `{args.prompts}`, "
        "greedy decoding",
        f"- data: `{REPO}` test split; balanced sample of {len(items)} (seed {args.seed}), "
        f"{len(scored)} with a prediction, {len(items) - len(scored)} failed calls",
        f"- dropped as too long before sampling: {dropped or 'none'}",
        f"- critic verdicts: {verdicts} (OK = clean; ISSUES and UNPARSED = hallucinated; "
        f"verdict_source `{args.verdict_source}`)", "",
        table, "",
        "Positive class = hallucinated. \"Weighted\" columns re-weight each (task, label) cell to its share of the "
        "full test split, so they estimate what the paper's numbers would be; the unweighted precision is "
        "inflated by the 50/50 sample. Recall does not depend on the mix within a task.", "",
        "## Paper baselines (RAGTruth, arXiv 2401.00396v2, Table 5, response level, full test set)", "",
        paper, "",
        "The paper's test split and wandb/RAGTruth-processed share the 2,700 test responses (this script does "
        "not verify that the two splits are identical item for item).",
    ]
    (run_dir / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap, n_default=300, model=False, critic="default")
    ap.add_argument("--verdict-source", choices=["verdict_line", "issue_lines"],
                    help="override config [generation].verdict_source")
    args = ap.parse_args()
    cfg, gen, run_dir = setup(args, "ragtruth")
    args.verdict_source = args.verdict_source or gen.get("verdict_source", "verdict_line")
    tpl = templates(run_dir)["critic.txt"]

    def prompt(it):
        return fill(tpl, document=it["context"], question=it["query"], draft=it["output"])

    rows = load_test()
    pop: dict = {}
    for r in rows:
        pop[(r["task_type"], r["label"])] = pop.get((r["task_type"], r["label"]), 0) + 1
    limit = int(gen.get("max_num_tokens", 4096)) - int(gen.get("max_output_tokens", 512))
    fits, dropped = [], {}
    for r in rows:
        if est_tokens(prompt(r)) <= limit:
            fits.append(r)
        else:
            key = f"{r['task_type']}/{'hal' if r['label'] else 'clean'}"
            dropped[key] = dropped.get(key, 0) + 1
    items = sample_balanced(fits, args.n, args.seed)
    ok(f"{len(items)} responses sampled from {len(rows)} ({len(rows) - len(fits)} too long for {limit} tokens)")

    llm = load_llm(cfg, args.runtime, args.critic, args.critic_backend, gen)
    try:
        run_stage(llm, items, prompt, "audit", gen, run_dir / "calls.jsonl", "critic")
    finally:
        llm.close()
    for it in items:
        if it.get("audit") is not None:
            it["verdict"], it["issues"] = parse_verdict(it["audit"], args.verdict_source)
            it["pred"] = int(it["verdict"] != "OK")
    write_jsonl(run_dir / "results.jsonl", [{k: v for k, v in it.items() if k != "context"} for it in items])
    table = write_summary(run_dir, args, items, pop, dropped)
    finish_meta(run_dir, sample_size=len(items))
    print("\n" + table)
    ok(f"Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
