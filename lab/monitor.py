"""Background sampler for RAM, VRAM, GPU load and GPU temperature (shown in the live view)."""
from __future__ import annotations

import shutil
import subprocess
import threading

try:
    import psutil
except ImportError:  # optional
    psutil = None


def query_gpu() -> dict | None:
    """One nvidia-smi sample. Returns None if there is no NVIDIA GPU / driver."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip().splitlines()
        if not out:
            return None
        name, used, total, util, temp = [x.strip() for x in out[0].split(",")]
        return {
            "name": name,
            "vram_used_mb": float(used),
            "vram_total_mb": float(total),
            "gpu_util": float(util),
            "gpu_temp": float(temp),
        }
    except Exception:
        return None


class SysMonitor:
    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self.latest: dict = {}
        self.peak_vram_mb = 0.0
        self.peak_ram_used_gb = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> "SysMonitor":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            snap = {}
            if psutil:
                vm = psutil.virtual_memory()
                snap["ram_used_gb"] = (vm.total - vm.available) / 1e9
                snap["ram_total_gb"] = vm.total / 1e9
                snap["proc_rss_gb"] = psutil.Process().memory_info().rss / 1e9
                self.peak_ram_used_gb = max(self.peak_ram_used_gb, snap["ram_used_gb"])
            gpu = query_gpu()
            if gpu:
                snap.update(gpu)
                self.peak_vram_mb = max(self.peak_vram_mb, gpu["vram_used_mb"])
            self.latest = snap
            self._stop.wait(self.interval)

    def line(self) -> str:
        s = self.latest
        parts = []
        if "ram_used_gb" in s:
            parts.append(f"RAM {s['ram_used_gb']:.1f}/{s['ram_total_gb']:.1f} GB (this process {s['proc_rss_gb']:.1f})")
        if "vram_used_mb" in s:
            parts.append(
                f"VRAM {s['vram_used_mb']/1024:.1f}/{s['vram_total_mb']/1024:.1f} GB · GPU {s['gpu_util']:.0f}% · {s['gpu_temp']:.0f}°C"
            )
        return "   ".join(parts) or "(no RAM/GPU stats: install psutil; NVIDIA driver needed for GPU stats)"
