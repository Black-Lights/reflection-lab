"""Log GPU power, GPU load, VRAM, CPU load and RAM every few seconds, for the compute report.

    python scripts/compute_logger.py                    sample every 5 s until Ctrl+C
    python scripts/compute_logger.py --interval 10
    python scripts/compute_logger.py --out runs/compute/my_log.csv

Rows are appended to a CSV (default runs/compute/samples.csv), so a restart continues the same log.
GPU columns come from nvidia-smi and stay empty without an NVIDIA GPU; CPU and RAM need psutil.
scripts/compute_report.py integrates power over each run's time window to get its energy.
Sampling costs about 30 MB of RAM and no GPU time.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import RUNS, console  # noqa: E402

try:
    import psutil
except ImportError:  # optional
    psutil = None

FIELDS = ["time", "gpu_power_w", "gpu_util", "vram_mb", "gpu_temp", "sm_clock_mhz", "cpu_util", "ram_used_gb"]
GPU_QUERY = "power.draw,utilization.gpu,memory.used,temperature.gpu,clocks.sm"


def gpu_sample() -> list[str]:
    if not shutil.which("nvidia-smi"):
        return [""] * 5
    try:
        out = subprocess.run(["nvidia-smi", f"--query-gpu={GPU_QUERY}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        vals = [v.strip() for v in out[0].split(",")]
        return [("" if v.startswith("[") else v) for v in vals]  # "[N/A]" -> empty
    except Exception:
        return [""] * 5


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=5.0, help="seconds between samples (default 5)")
    ap.add_argument("--out", default=str(RUNS / "compute" / "samples.csv"))
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new = not out.exists() or out.stat().st_size == 0
    if psutil:
        psutil.cpu_percent(None)  # first call primes the counter
    console.print(f"Logging every {args.interval:g} s to {out}  (Ctrl+C to stop)")
    n, last_print = 0, 0.0
    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        try:
            while True:
                t0 = time.time()
                g = gpu_sample()
                cpu = f"{psutil.cpu_percent(None):.0f}" if psutil else ""
                ram = ""
                if psutil:
                    vm = psutil.virtual_memory()
                    ram = f"{(vm.total - vm.available) / 1e9:.2f}"
                w.writerow([datetime.now().isoformat(timespec="seconds"), *g, cpu, ram])
                f.flush()
                n += 1
                if t0 - last_print >= 60:
                    console.print(f"  {datetime.now():%H:%M:%S}  GPU {g[0] or '-'} W, {g[1] or '-'} %, "
                                  f"{g[2] or '-'} MiB, {g[3] or '-'} °C · CPU {cpu or '-'} % · RAM {ram or '-'} GB · {n} rows")
                    last_print = t0
                time.sleep(max(0.0, args.interval - (time.time() - t0)))
        except KeyboardInterrupt:
            console.print(f"stopped after {n} rows")


if __name__ == "__main__":
    main()
