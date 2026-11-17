"""Shared helpers for the standard-benchmark scripts (scripts/bench_*.py).

The benchmarks reuse the experiment's own pieces, unchanged:
  - `fill` and `parse_verdict` from scripts/run_experiment.py (same prompt filling, same verdict rule),
  - `make_llm` / `clean_output` from lab/llm.py with the config [generation] settings (greedy, seed).

Models are run stage by stage (all drafts, unload, all audits, unload, all refinements), like
run_experiment's "swap" mode, so only one model is in VRAM at a time.
Output folder: runs/bench_<name>_<YYYYmmdd-HHMMSS>/ . runs/LATEST.txt is never touched, so
label.py and report.py keep pointing at the last experiment run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from lab.common import ROOT, RUNS, append_jsonl, fail, load_config, ok, resolve_model, stamp, step, warn, write_json
from lab.llm import BaseLLM, clean_output, make_llm

sys.path.insert(0, str(ROOT / "scripts"))
from run_experiment import fill, parse_verdict  # noqa: E402  (same functions the experiment uses)

PROMPT_FILES = ("critic.txt", "refiner.txt")


# --------------------------------------------------------------------------- arguments
def add_common_args(ap: argparse.ArgumentParser, n_default: int, model: bool = True, critic: str = "optional"):
    """--runtime --n/--limit --seed --max-num-tokens, plus model/critic choices."""
    ap.add_argument("--runtime", choices=["python", "fake"], default="python",
                    help="python = LiteRT-LM models; fake = no model, to test the script (default python)")
    ap.add_argument("--n", "--limit", dest="n", type=int, default=n_default, help=f"number of items (default {n_default})")
    ap.add_argument("--seed", type=int, default=0, help="seed for sampling the items (default 0)")
    ap.add_argument("--max-num-tokens", type=int, default=0,
                    help="override config [generation].max_num_tokens (context window per call)")
    if model:
        ap.add_argument("--model", help="catalog key of the generator (default: config [models.analyst])")
        ap.add_argument("--backend", choices=["gpu", "cpu"], help="backend of the generator (default from config)")
    if critic != "none":  # "optional": loop only if --critic is given; "default": config [models.critic]
        ap.add_argument("--critic", help="catalog key of the critic" + (
            " (default: config [models.critic])" if critic == "default"
            else "; if given, also run the critic -> refiner loop"))
        ap.add_argument("--critic-backend", choices=["gpu", "cpu"], help="backend of the critic (default from config)")
        ap.add_argument("--prompts", default="prompts", help="folder with critic.txt and refiner.txt (default prompts)")
        ap.set_defaults(critic_default=(critic == "default"))
    return ap


def setup(args, bench: str) -> tuple[dict, dict, Path]:
    """Read config, build the generation settings, create the run folder. Returns (cfg, gen, run_dir)."""
    cfg = load_config()
    gen = dict(cfg.get("generation", {}))
    if not gen.get("greedy", True):
        warn("config [generation].greedy is false; benchmarks force greedy decoding (top_k = 1)")
    gen["greedy"] = True
    gen["seed"] = args.seed
    if args.max_num_tokens:
        gen["max_num_tokens"] = args.max_num_tokens
    if getattr(args, "model", "x") is None:
        args.model = cfg["models"]["analyst"]["key"]
    if getattr(args, "backend", "x") is None:
        args.backend = cfg["models"]["analyst"].get("backend", "gpu")
    if getattr(args, "critic", "x") is None and getattr(args, "critic_default", False):
        args.critic = cfg["models"]["critic"]["key"]
    if getattr(args, "critic_backend", "x") is None:
        args.critic_backend = cfg["models"]["critic"].get("backend", "gpu")
    run_dir = RUNS / f"bench_{bench}_{stamp()}"
    run_dir.mkdir(parents=True)
    if getattr(args, "critic", None):
        src = Path(args.prompts) if Path(args.prompts).is_absolute() else ROOT / args.prompts
        missing = [f for f in PROMPT_FILES if not (src / f).exists()]
        if missing:
            fail(f"{src} lacks {', '.join(missing)}")
            sys.exit(1)
        (run_dir / "prompts").mkdir()
        for f in PROMPT_FILES:
            shutil.copy(src / f, run_dir / "prompts" / f)
    meta = {"bench": bench, "args": vars(args), "generation": gen, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    write_json(run_dir / "meta.json", meta)
    ok(f"Run folder: {run_dir}")
    return cfg, gen, run_dir


def templates(run_dir: Path) -> dict:
    return {f: (run_dir / "prompts" / f).read_text(encoding="utf-8") for f in PROMPT_FILES}


def finish_meta(run_dir: Path, **extra) -> None:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    meta.update(extra, finished=time.strftime("%Y-%m-%d %H:%M:%S"))
    write_json(run_dir / "meta.json", meta)


# --------------------------------------------------------------------------- models
def load_llm(cfg: dict, runtime: str, key: str, backend: str, gen: dict) -> BaseLLM:
    path = resolve_model(cfg, key)
    llm = make_llm(runtime, key, path, backend, dict(gen), cfg.get("run", {}))
    step(f"loading {llm.name} ({path})")
    llm.load()
    ok(f"loaded in {llm.load_seconds:.1f}s")
    return llm


def est_tokens(text: str) -> int:
    """Rough token estimate (chars / 4), used only for length checks."""
    return len(text) // 4


def preflight(prompts: list[str], gen: dict, label: str) -> int:
    """Warn about prompts that may not fit the context window. Returns how many may overflow."""
    limit = int(gen.get("max_num_tokens", 4096)) - int(gen.get("max_output_tokens", 512))
    over = sum(1 for p in prompts if est_tokens(p) > limit)
    if over:
        warn(f"{label}: {over}/{len(prompts)} prompts are estimated above {limit} tokens "
             f"(max_num_tokens - max_output_tokens); they may fail. Raise --max-num-tokens if so.")
    return over


def run_stage(llm: BaseLLM, items: list[dict], prompt_fn, field: str, gen: dict, log: Path, label: str) -> None:
    """One model call per item: item[field] = cleaned output. Errors are recorded and the run continues."""
    total = len(items)
    t_stage = time.time()
    for i, it in enumerate(items, 1):
        prompt = prompt_fn(it)
        t = time.time()
        try:
            raw, err = llm.generate(prompt), None
        except Exception as e:  # keep going; one bad item must not stop a long run
            raw, err = "", f"{type(e).__name__}: {e}"
        secs = time.time() - t
        text, flags = clean_output(raw, gen.get("strip_think_tags", True))
        it[field] = text if err is None else None
        it.setdefault("timings", {})[field] = round(secs, 2)
        if flags:
            it.setdefault("flags", {}).update({f"{field}_{k}": v for k, v in flags.items()})
        if err:
            it.setdefault("errors", {})[field] = err
        append_jsonl(log, {"id": it["id"], "field": field, "model": llm.name, "seconds": round(secs, 2),
                           "prompt_chars": len(prompt), "output": raw, "error": err})
        eta = (time.time() - t_stage) / i * (total - i)
        status = f"ERROR {err}" if err else f"{len(text.split())} words"
        print(f"[{label} {i}/{total}] {it['id']}: {secs:.1f}s, {status}  (~{eta/60:.1f} min left)", flush=True)


def critic_refine(cfg: dict, args, gen: dict, items: list[dict], run_dir: Path, doc_fn, question_fn) -> None:
    """Stage 2 (critic audits item['baseline']) and stage 3 (generator refines unless the verdict is OK).

    Sets audit, audit_verdict, audit_issues, refined and final on every item that has a baseline.
    """
    tpl = templates(run_dir)
    log = run_dir / "calls.jsonl"
    todo = [it for it in items if it.get("baseline")]

    def critic_prompt(it):
        return fill(tpl["critic.txt"], document=doc_fn(it), question=question_fn(it), draft=it["baseline"])

    preflight([critic_prompt(it) for it in todo], gen, "critic")
    llm = load_llm(cfg, args.runtime, args.critic, args.critic_backend, gen)
    try:
        run_stage(llm, todo, critic_prompt, "audit", gen, log, "critic")
    finally:
        llm.close()
    source = gen.get("verdict_source", "verdict_line")
    for it in todo:
        if it.get("audit") is not None:
            it["audit_verdict"], it["audit_issues"] = parse_verdict(it["audit"], source)

    skip_ok = gen.get("skip_refine_if_ok", True)
    refine = [it for it in todo if it.get("audit") is not None and not (skip_ok and it["audit_verdict"] == "OK")]
    refine_ids = {id(it) for it in refine}
    for it in todo:
        if it.get("audit") is not None and id(it) not in refine_ids:
            it["final"], it["refined"] = it["baseline"], False

    def refine_prompt(it):
        return fill(tpl["refiner.txt"], document=doc_fn(it), question=question_fn(it),
                    draft=it["baseline"], audit=it["audit"])

    if not refine:
        ok("critic said OK for every item: nothing to refine")
        return
    preflight([refine_prompt(it) for it in refine], gen, "refiner")
    llm = load_llm(cfg, args.runtime, args.model, args.backend, gen)
    try:
        run_stage(llm, refine, refine_prompt, "final", gen, log, "refine")
    finally:
        llm.close()
    for it in refine:
        it["refined"] = it.get("final") is not None


def verdict_counts(items: list[dict]) -> dict:
    out: dict = {}
    for it in items:
        v = it.get("audit_verdict", "none")
        out[v] = out.get(v, 0) + 1
    return out


# --------------------------------------------------------------------------- output
def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def md_table(header: list[str], rows: list[list]) -> str:
    def cell(x):
        return f"{x:.1f}" if isinstance(x, float) else str(x)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows]
    return "\n".join(lines)


def prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    """Precision, recall, F1 in percent (0 when undefined)."""
    p = 100 * tp / (tp + fp) if tp + fp else 0.0
    r = 100 * tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f
