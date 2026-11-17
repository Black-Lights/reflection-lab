"""Vectara hallucination-leaderboard style benchmark: summarise documents, score with HHEM-2.1-open.

    python scripts/bench_hhem.py --runtime fake --n 3                       test the script, no models
    python scripts/bench_hhem.py --model gemma-4-e4b                        baseline summaries (200 docs)
    python scripts/bench_hhem.py --model gemma-4-e4b --critic qwen3-1.7b    baseline + critic -> refiner loop
    python scripts/bench_hhem.py --no-score ...                             generate only, score later
    python scripts/bench_hhem.py --score-only runs/bench_hhem_<stamp>       (re)score an existing run on CPU

Documents: HF dataset vectara/hhem_leaderboard_datasets, file leaderboard_dataset.csv (1006 docs, the file
the leaderboard backend in the HF space vectara/leaderboard reads, src/envs.py DATASET_PATH). The live
leaderboard has since moved to a private 7,700-article set, a new prompt and the commercial HHEM-2.3, so
numbers here follow the leaderboard's method but are not directly comparable with the current table.

--prompt-version
  legacy  (default) the prompt the leaderboard backend uses with these documents (src/envs.py SYSTEM_PROMPT +
          USER_PROMPT + "\\nPassage:\\n" + document), joined with a newline as that code does for models
          without a system role (Gemma).
  current the prompt in the README of github.com/vectara/hallucination-leaderboard (checked 2026-11-17).

Metrics, as in vectara/leaderboard src/backend (util.py, model_operations.py):
  valid summary              at least 5 words (util.is_summary_valid) and not the refusal sentence
  answer rate                valid summaries / documents
  HHEM score                 HHEM-2.1-open(document, summary), summary normalised markdown -> plain text first
  factual consistency rate   % of valid summaries with score >= 0.5; hallucination rate = 100 - that
  average summary length     words in valid summaries (leaderboard: spaCy alphabetic tokens; here: alphabetic runs)
With --critic, the critic audits each summary with critic.txt (QUESTION = the summarisation request) and
the generator rewrites it with refiner.txt unless the verdict is OK; the result is scored as "loop".
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.bench_common import (  # noqa: E402
    add_common_args, critic_refine, finish_meta, load_llm, md_table, preflight, run_stage, setup,
    verdict_counts, write_jsonl,
)
from lab.common import ok, read_json, read_jsonl, step  # noqa: E402

HHEM_ID = "vectara/hallucination_evaluation_model"
# Pinned: the revision whose remote code (modeling_hhem_v2.py) was read on 2026-11-17; it runs with
# trust_remote_code, so a new upstream version is not picked up silently.
HHEM_REVISION = "de9a5e6ba9ba49531a022dba17e35ffeb2a6fad8"
DATA_REPO = "vectara/hhem_leaderboard_datasets"
DATA_FILES = ["leaderboard_dataset.csv", "leaderboard_dataset_revised.csv", "sample_dataset.csv"]
THRESHOLD = 0.5

LEGACY_SYSTEM = ("You are a chat bot answering questions using data. You must stick to the answers provided "
                 "solely by the text in the passage provided.")
LEGACY_USER = ("You are asked the question 'Provide a concise summary of the following passage, covering the "
               "core pieces of information described': ")
CURRENT = (
    "Your task is to provide a concise and factual summary for the given passage.\n"
    "Rules\n"
    "1. Summarize using only the information in the given passage. Do not infer. Do not use your internal knowledge.\n"
    "2. Do not provide a preamble or explanation, output only the summary.\n"
    "3. Summaries should never exceed 20 percent of the original text's length.\n"
    "4. Maintain the tone of the passage.\n"
    "If you are unable to summarize the text due to missing, unreadable, irrelevant or insufficient content, "
    "respond only with:\n"
    "\"I am unable to summarize this text.\"\n"
    "Here is the passage:\n"
)
# What the critic sees as QUESTION: the summarisation request of each prompt version.
REQUEST = {
    "legacy": "Provide a concise summary of the following passage, covering the core pieces of information described.",
    "current": "Provide a concise and factual summary for the given passage, using only the information in the passage.",
}
REFUSAL = "unable to summarize this text"
VARIANTS = {"baseline": "baseline", "final": "loop"}


def build_prompt(source: str, version: str) -> str:
    if version == "legacy":
        return f"{LEGACY_SYSTEM}\n{LEGACY_USER}\nPassage:\n{source}"
    return CURRENT + source


def load_docs(fname: str) -> list[dict]:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(DATA_REPO, fname, repo_type="dataset")
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{"id": f"d{i:04d}", "row": i, "dataset": r["dataset"], "source": r["text"]} for i, r in enumerate(rows)]


# --------------------------------------------------------------------------- scoring
def is_valid(summary) -> bool:
    return isinstance(summary, str) and len(summary.split()) >= 5 and REFUSAL not in summary.lower()


_MD = None


def normalize(summary: str) -> str:
    """vectara/leaderboard util.normalize_summary: markdown -> plain text, drop '*', collapse whitespace."""
    global _MD
    s = summary.replace("<bos>", "").replace("<eos>", "")
    try:
        if _MD is None:
            from markdown_it import MarkdownIt
            from mdit_plain.renderer import RendererPlain
            _MD = MarkdownIt(renderer_cls=RendererPlain)
        s = _MD.render(s)
    except ImportError:  # pip install mdit_plain; without it only '*' and spaces are cleaned
        pass
    return re.sub(r"\s{2,}", " ", s.replace("*", ""))


def alpha_words(s: str) -> int:
    return len(re.findall(r"[^\W\d_]+", s))


def load_hhem(threads: int):
    import torch
    from transformers import AutoModelForSequenceClassification

    if threads:
        torch.set_num_threads(threads)
    step(f"loading {HHEM_ID} on CPU (first time: ~440 MB download to the Hugging Face cache)")
    model = AutoModelForSequenceClassification.from_pretrained(HHEM_ID, revision=HHEM_REVISION,
                                                               trust_remote_code=True)
    model.to("cpu").eval()
    return model, HHEM_REVISION


def score_run(run_dir: Path, threads: int = 0) -> None:
    items = read_jsonl(run_dir / "results.jsonl")
    variants = [v for v in VARIANTS if any(v in it for it in items)]
    model, revision = load_hhem(threads)
    todo = sum(1 for it in items for v in variants if is_valid(it.get(v)))
    done, t0 = 0, time.time()
    for it in items:
        cache: dict = {}
        for v in variants:
            s = it.get(v)
            if not is_valid(s):
                it.pop(f"{v}_hhem", None)
                continue
            norm = normalize(s)
            if norm not in cache:
                cache[norm] = round(float(model.predict([(it["source"], norm)])[0]), 4)
            it[f"{v}_hhem"] = cache[norm]
            done += 1
            print(f"[hhem {done}/{todo}] {it['id']} {VARIANTS[v]}: {it[f'{v}_hhem']:.3f}"
                  f"{'  HALLUCINATED' if it[f'{v}_hhem'] < THRESHOLD else ''}"
                  f"  (~{(time.time() - t0) / done * (todo - done) / 60:.1f} min left)", flush=True)
    write_jsonl(run_dir / "results.jsonl", items)
    write_summary(run_dir, items, variants, revision)


def metrics(items: list[dict], v: str) -> dict:
    valid = [it for it in items if is_valid(it.get(v))]
    scores = [it[f"{v}_hhem"] for it in valid if f"{v}_hhem" in it]
    fcr = 100 * sum(s >= THRESHOLD for s in scores) / len(scores) if scores else float("nan")
    return {
        "n": len(items), "valid": len(valid), "scored": len(scores),
        "answer_rate": 100 * len(valid) / len(items) if items else 0.0,
        "fcr": fcr, "hr": 100 - fcr,
        "avg_words": sum(alpha_words(it[v]) for it in valid) / len(valid) if valid else 0.0,
        "mean_score": sum(scores) / len(scores) if scores else float("nan"),
        "errors": sum(1 for it in items if v in it.get("errors", {})),
    }


def write_summary(run_dir: Path, items: list[dict], variants: list[str], revision) -> None:
    meta = read_json(run_dir / "meta.json", {})
    a = meta.get("args", {})
    rows, res = [], {}
    for v in variants:
        m = res[v] = metrics(items, v)
        rows.append([VARIANTS[v], m["hr"], m["fcr"], m["answer_rate"], m["avg_words"],
                     f"{m['mean_score']:.3f}", f"{m['scored']}/{m['n']}", m["errors"]])
    table = md_table(["variant", "hallucination rate %", "factual consistency rate %", "answer rate %",
                      "avg summary length (words)", "mean HHEM", "scored/N", "errors"], rows)
    out = [
        f"# HHEM leaderboard-style benchmark · {run_dir.name}", "",
        f"- generator: `{a.get('model')}` ({a.get('backend')}, runtime {a.get('runtime')})"
        + (f" · critic: `{a.get('critic')}` ({a.get('critic_backend')}), prompts `{a.get('prompts')}`"
           if a.get("critic") else ""),
        f"- documents: {len(items)} sampled (seed {a.get('seed')}) from `{DATA_REPO}/{a.get('dataset')}`",
        f"- prompt version: `{a.get('prompt_version')}` · greedy decoding · max_output_tokens "
        f"{meta.get('generation', {}).get('max_output_tokens')}",
        f"- scorer: `{HHEM_ID}` (HHEM-2.1-open, CPU) revision `{revision}` · hallucinated if score < {THRESHOLD}",
        "",
        table,
        "",
    ]
    if "final" in variants:
        both = [it for it in items if "baseline_hhem" in it and "final_hhem" in it]
        fixed = sum(1 for it in both if it["baseline_hhem"] < THRESHOLD <= it["final_hhem"])
        broken = sum(1 for it in both if it["final_hhem"] < THRESHOLD <= it["baseline_hhem"])
        out += [
            "## Critic loop", "",
            f"- critic verdicts: {verdict_counts(items)} · refined: {sum(1 for it in items if it.get('refined'))}",
            f"- paired, on {len(both)} documents scored in both variants: hallucinated -> consistent {fixed}, "
            f"consistent -> hallucinated {broken}, hallucinated in both "
            f"{sum(1 for it in both if max(it['baseline_hhem'], it['final_hhem']) < THRESHOLD)}",
            "- note: refiner.txt asks for at most 120 words, so loop summaries can be shorter than baseline ones.",
            "",
        ]
    out += [
        "## How to read this", "",
        "Same method as the Vectara leaderboard backend (valid = at least 5 words; rates over valid summaries;",
        "answer rate over all documents). Differences: the public leaderboard now uses HHEM-2.3 (commercial) on a",
        "private dataset and only scores documents that every model answered; word counts here are alphabetic runs,",
        "not spaCy tokens. Compare variants within this folder rather than with the public table.",
    ]
    (run_dir / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    finish_meta(run_dir, hhem_revision=revision, metrics={VARIANTS[v]: res[v] for v in variants})
    print("\n" + table)
    ok(f"Summary: {run_dir / 'summary.md'}")


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap, n_default=200)
    ap.add_argument("--prompt-version", choices=["legacy", "current"], default="legacy")
    ap.add_argument("--dataset", choices=DATA_FILES, default=DATA_FILES[0])
    ap.add_argument("--no-score", action="store_true", help="generate only; score later with --score-only")
    ap.add_argument("--score-only", metavar="RUN_DIR", help="score the summaries of an existing run folder")
    ap.add_argument("--hhem-threads", type=int, default=0, help="CPU threads for HHEM (default: torch default)")
    args = ap.parse_args()

    if args.score_only:
        score_run(Path(args.score_only), args.hhem_threads)
        return

    cfg, gen, run_dir = setup(args, "hhem")
    docs = load_docs(args.dataset)
    rng = random.Random(args.seed)
    items = [docs[i] for i in sorted(rng.sample(range(len(docs)), min(args.n, len(docs))))]
    ok(f"{len(items)} of {len(docs)} documents sampled (seed {args.seed})")

    preflight([build_prompt(it["source"], args.prompt_version) for it in items], gen, "summary")
    llm = load_llm(cfg, args.runtime, args.model, args.backend, gen)
    try:
        run_stage(llm, items, lambda it: build_prompt(it["source"], args.prompt_version), "baseline", gen,
                  run_dir / "calls.jsonl", "summary")
    finally:
        llm.close()
    if args.critic:
        critic_refine(cfg, args, gen, items, run_dir, doc_fn=lambda it: it["source"],
                      question_fn=lambda it: REQUEST[args.prompt_version])
    write_jsonl(run_dir / "results.jsonl", items)
    ok(f"Summaries saved: {run_dir / 'results.jsonl'}")

    if args.no_score:
        finish_meta(run_dir)
        print(f"Score later (CPU): python scripts/bench_hhem.py --score-only \"{run_dir}\"")
        return
    score_run(run_dir, args.hhem_threads)


if __name__ == "__main__":
    main()
