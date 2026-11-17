"""Run a list of project scripts one after another (GPU jobs must not overlap), with a status file.

    python scripts/run_queue.py queues/after_grid.txt
    python scripts/run_queue.py queues/after_grid.txt --from 5      resume at line item 5

Queue file: one job per line, `scripts/<name>.py <args>` (run with this venv's python, from the project
folder). Blank lines and lines starting with # are skipped. Special line:
    WAIT_MATRIX runs/matrix_<stamp>/index.json    wait until every config of that matrix has finished
Progress: runs/queue_<stamp>_<file>/status.json (job, exit code, minutes) and log.jsonl. After every job
the whole project (results included) is committed to git (lab.common.git_snapshot), so nothing is lost.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    ROOT, RUNS, append_jsonl, console, fail, from_root, git_snapshot, ok, read_json, stamp, step, write_json,
)


def matrix_done(index: Path) -> bool:
    idx = read_json(index, {})
    runs = idx.get("runs", {})
    return bool(idx) and all(c in runs and (from_root(runs[c]) / "outputs.jsonl").exists() for c in idx.get("configs", []))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queue")
    ap.add_argument("--from", dest="start", type=int, default=1, help="1-based job number to start at")
    args = ap.parse_args()
    qfile = Path(args.queue)
    jobs = [ln.strip() for ln in qfile.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    out = RUNS / f"queue_{stamp()}_{qfile.stem}"
    out.mkdir(parents=True)
    status = {"queue": str(qfile), "jobs": jobs, "done": [], "current": None}
    write_json(out / "status.json", status)
    for n, job in enumerate(jobs, 1):
        if n < args.start:
            continue
        status["current"] = {"n": n, "job": job, "started": time.strftime("%H:%M:%S")}
        write_json(out / "status.json", status)
        step(f"[{n}/{len(jobs)}] {job}")
        t0 = time.time()
        if job.startswith("WAIT_MATRIX"):
            index = ROOT / job.split(maxsplit=1)[1]
            while not matrix_done(index):
                time.sleep(30)
            rc = 0
        else:
            parts = shlex.split(job, posix=False)
            rc = subprocess.call([sys.executable, str(ROOT / parts[0]), *parts[1:]], cwd=ROOT,
                                 env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        rec = {"n": n, "job": job, "exit": rc, "minutes": round((time.time() - t0) / 60, 1),
               "finished": time.strftime("%H:%M:%S")}
        status["done"].append(rec)
        append_jsonl(out / "log.jsonl", rec)
        (ok if rc == 0 else fail)(f"[{n}/{len(jobs)}] exit {rc} after {rec['minutes']} min")
        write_json(out / "status.json", status)
        if not job.startswith("WAIT_"):
            git_snapshot(f"queue {qfile.stem} job {n}/{len(jobs)} (exit {rc}): {job[:90]}")
    status["current"] = None
    status["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    write_json(out / "status.json", status)
    console.print(json.dumps(status["done"], indent=1))


if __name__ == "__main__":
    main()
