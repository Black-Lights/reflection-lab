"""Run many analyst/critic/prompt combinations in a row, then grade each run automatically.

    python scripts/run_matrix.py --config gemma-4-e4b:gemma-4-e4b:prompts --config qwen3-4b:gemma-4-e4b:prompts_v2
    python scripts/run_matrix.py --preset grid          the grid of 2026-11-17 (6 pairs x prompts, prompts_v2)
    python scripts/run_matrix.py --preset grid --dry-run   list what would run
    python scripts/run_matrix.py --index runs/matrix_<stamp>/index.json   resume: skip finished configs

A config is ANALYST:CRITIC:PROMPTS[:tools] (catalog keys, prompts folder; ":tools" adds --analyst-tools). All case files given with --sets are merged
into one file in the matrix folder, so every config sees the same cases. Each config is one
run_experiment.py run (same live view), followed by autoscore.py --apply. Progress: runs/matrix_<stamp>/index.json.
Afterwards: python scripts/matrix_report.py --index runs/matrix_<stamp>/index.json
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    ROOT, RUNS, console, fail, from_root, git_snapshot, ok, read_json, read_jsonl, rel_to_root, stamp, step,
    write_json,
)

SETS = ["tests/cases.jsonl", "tests/cases_hard.jsonl", "tests/cases_fresh.jsonl"]
PAIRS = [("gemma-4-e4b", "gemma-4-e4b"), ("gemma-4-e4b", "qwen3-4b"), ("qwen3-4b", "gemma-4-e4b"),
         ("qwen3-4b", "qwen3-4b"), ("gemma-4-e4b", "qwen3-1.7b"), ("qwen3-1.7b", "gemma-4-e4b")]
PRESETS = {"grid": [f"{a}:{c}:{p}" for p in ("prompts", "prompts_v2") for a, c in PAIRS]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", action="append", default=[], help="ANALYST:CRITIC:PROMPTS[:tools] (repeatable)")
    ap.add_argument("--preset", choices=sorted(PRESETS))
    ap.add_argument("--sets", nargs="+", default=SETS, help="case files to merge")
    ap.add_argument("--index", help="existing index.json to resume")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.index:
        idx_path = Path(args.index)
        idx = read_json(idx_path, {})
        mdir = idx_path.parent
    else:
        configs = list(args.config) + (PRESETS[args.preset] if args.preset else [])
        if not configs:
            fail("Give --config or --preset")
            sys.exit(1)
        mdir = RUNS / f"matrix_{stamp()}"
        idx = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "sets": args.sets, "configs": configs, "runs": {}}
        idx_path = mdir / "index.json"
        if args.dry_run:
            for c in configs:
                console.print(f"  {c}")
            console.print(f"{len(configs)} configs × {sum(len(read_jsonl(ROOT / s)) for s in args.sets)} cases")
            return
        mdir.mkdir(parents=True)
        lines = []
        for s in args.sets:
            lines += [(ROOT / s).read_text(encoding="utf-8").strip()]
        (mdir / "cases_all.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        write_json(idx_path, idx)

    py = sys.executable
    for n, cfg in enumerate(idx["configs"], 1):
        if cfg in idx["runs"] and (from_root(idx["runs"][cfg]) / "outputs.jsonl").exists():
            ok(f"[{n}/{len(idx['configs'])}] {cfg} already done")
            continue
        analyst, critic, prompts, *extra = cfg.split(":")  # optional 4th part "tools" = --analyst-tools
        tools = "tools" in extra
        name = f"mx-{analyst}+{critic}-{Path(prompts).name}" + ("-tools" if tools else "")
        step(f"[{n}/{len(idx['configs'])}] {cfg}")
        before = set(RUNS.glob("*_" + name))
        cmd = [py, str(ROOT / "scripts" / "run_experiment.py"), "--cases", rel_to_root(mdir / "cases_all.jsonl"),
               "--analyst", analyst, "--critic", critic, "--prompts", prompts, "--name", name]
        if tools:
            cmd.append("--analyst-tools")
        t0 = time.time()
        rc = subprocess.call(cmd, cwd=ROOT)
        new = sorted(set(RUNS.glob("*_" + name)) - before)
        if not new:
            fail(f"{cfg}: no run folder created (exit {rc})")
            continue
        run_dir = new[-1]
        idx["runs"][cfg] = rel_to_root(run_dir)
        idx.setdefault("minutes", {})[cfg] = round((time.time() - t0) / 60, 1)
        write_json(idx_path, idx)
        subprocess.call([py, str(ROOT / "scripts" / "autoscore.py"), "--run", str(run_dir), "--apply"], cwd=ROOT)
        git_snapshot(f"matrix {mdir.name}: {cfg} done and graded")
    ok(f"Matrix done: {idx_path}")
    console.print(f"Next: python scripts/matrix_report.py --index {idx_path}")


if __name__ == "__main__":
    main()
