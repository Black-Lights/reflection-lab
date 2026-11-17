"""Check what is installed and what is missing. Standard library only (rich optional).

    python scripts/check_env.py              full check, writes reports/env_report.md + .json
    python scripts/check_env.py --probe-api  also list what the installed litert_lm module offers
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import REPORTS, ROOT, console, step, write_json  # noqa: E402

IS_WIN = platform.system() == "Windows"
results: list[dict] = []


def record(area: str, item: str, status: str, detail: str = "", fix: str = "") -> None:
    results.append({"area": area, "item": item, "status": status, "detail": detail, "fix": fix})
    colour = {"OK": "green", "WARN": "yellow", "MISSING": "red", "INFO": "cyan"}[status]
    line = f"[{colour}]{status:<7}[/{colour}] {area:<9} {item:<26} {detail}"
    console.print(line)
    if fix and status in ("WARN", "MISSING"):
        console.print(f"          [dim]fix: {fix}[/dim]")


def run(cmd: list[str], timeout: int = 10) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- system
def check_system() -> None:
    step("System")
    record("system", "OS", "INFO", f"{platform.system()} {platform.release()} ({platform.version()})")
    cpu = platform.processor()
    if IS_WIN:
        cpu = run(["powershell", "-NoProfile", "-Command",
                   "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"]) or cpu
    elif Path("/proc/cpuinfo").exists():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    record("system", "CPU", "INFO", f"{cpu} · {os.cpu_count()} threads")

    total_gb = avail_gb = None
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        total_gb, avail_gb = vm.total / 1e9, vm.available / 1e9
    except ImportError:
        if IS_WIN:
            import ctypes

            class MEMSTAT(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]

            ms = MEMSTAT()
            ms.dwLength = ctypes.sizeof(MEMSTAT)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
            total_gb, avail_gb = ms.ullTotalPhys / 1e9, ms.ullAvailPhys / 1e9
        elif Path("/proc/meminfo").exists():
            info = dict(l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines() if ":" in l)
            total_gb = int(info["MemTotal"].split()[0]) / 1e6
            avail_gb = int(info["MemAvailable"].split()[0]) / 1e6
    if total_gb:
        status = "OK" if avail_gb and avail_gb > 6 else "WARN"
        record("system", "RAM", status, f"{total_gb:.1f} GB total, {avail_gb:.1f} GB free",
               "close browsers/other apps before running models")

    drive = Path(ROOT.anchor or "/")
    usage = shutil.disk_usage(drive)
    free_gb = usage.free / 1e9
    record("system", f"Disk free ({drive})", "OK" if free_gb > 15 else "WARN", f"{free_gb:.0f} GB free",
           "need ~10 GB for the planned models")

    if IS_WIN:
        try:
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem")
            val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
            record("system", "Long paths", "OK" if val == 1 else "WARN", f"LongPathsEnabled={val}",
                   "optional: enable long paths (admin) if Hugging Face downloads fail with path errors")
        except Exception:
            record("system", "Long paths", "INFO", "could not read registry")


def check_gpu() -> None:
    step("GPU")
    if not shutil.which("nvidia-smi"):
        record("gpu", "nvidia-smi", "WARN", "not found", "install/update the NVIDIA driver; CPU backend still works")
        return
    out = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
               "--format=csv,noheader,nounits"])
    if not out:
        record("gpu", "nvidia-smi", "WARN", "no output")
        return
    name, driver, total, used = [x.strip() for x in out.splitlines()[0].split(",")]
    record("gpu", "GPU", "OK", f"{name} · driver {driver}")
    free = (float(total) - float(used)) / 1024
    record("gpu", "VRAM", "OK" if free > 4.5 else "WARN",
           f"{float(total)/1024:.1f} GB total, {free:.1f} GB free",
           "close games/browsers using the GPU; use backend=cpu for the critic if needed")


# --------------------------------------------------------------------------- python
PACKAGES = [
    # (import name, distribution names to look up, required, install hint)
    ("litert_lm", ["litert-lm-api", "litert-lm"], True, "pip install litert-lm-api"),
    ("huggingface_hub", ["huggingface_hub", "huggingface-hub"], True, "pip install huggingface_hub"),
    ("rich", ["rich"], True, "pip install rich"),
    ("psutil", ["psutil"], True, "pip install psutil"),
]


def check_python() -> None:
    step("Python")
    v = sys.version_info
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    status = "OK" if (3, 11) <= (v.major, v.minor) <= (3, 13) else "WARN"
    record("python", "Python", status, f"{platform.python_version()} at {sys.executable}",
           "use Python 3.11 or 3.12 (py -3.12 -m venv .venv)")
    record("python", "Virtual env", "OK" if in_venv else "WARN",
           "active" if in_venv else "not in a venv", "run bootstrap.ps1, then .venv\\Scripts\\activate")
    for mod, dists, required, hint in PACKAGES:
        version = None
        for d in dists:
            try:
                version = md.version(d)
                break
            except md.PackageNotFoundError:
                continue
        try:
            importlib.import_module(mod)
            record("python", mod, "OK", f"version {version or '?'}")
        except Exception as e:  # ImportError or DLL load failure on Windows
            detail = "not installed" if isinstance(e, ImportError) and version is None else f"import failed: {e}"
            record("python", mod, "MISSING" if required else "WARN", detail, hint)


def probe_litert_api() -> None:
    step("LiteRT-LM Python API surface (for adapting lab/llm.py)")
    try:
        import litert_lm  # type: ignore
    except Exception as e:
        record("litert", "import litert_lm", "MISSING", str(e), "pip install litert-lm-api")
        return
    public = sorted(n for n in dir(litert_lm) if not n.startswith("_"))
    record("litert", "module members", "INFO", ", ".join(public)[:600])
    for cls_name in ("Engine", "Conversation", "Backend", "ThinkingConfig", "SamplerConfig", "SessionConfig"):
        cls = getattr(litert_lm, cls_name, None)
        if cls is None:
            record("litert", cls_name, "INFO", "not present")
            continue
        members = sorted(n for n in dir(cls) if not n.startswith("_"))
        record("litert", cls_name, "INFO", ", ".join(members)[:400])
        try:
            import inspect

            sig = str(inspect.signature(cls))
            record("litert", f"{cls_name} signature", "INFO", sig[:300])
        except Exception:
            pass


# --------------------------------------------------------------------------- tools
def check_tools() -> None:
    step("Command-line tools")
    tools = [
        ("litert-lm", "pip install litert-lm  (LiteRT-LM CLI, optional fallback runtime)", False),
        ("hf", "comes with huggingface_hub (pip install -U huggingface_hub)", False),
        ("git", "https://git-scm.com/download/win", False),
        ("uv", "optional: pip install uv", False),
        ("ollama", "optional, only for running GGUF models as a PC-side judge later", False),
    ]
    for exe, hint, required in tools:
        path = shutil.which(exe)
        record("tools", exe, "OK" if path else ("MISSING" if required else "WARN"), path or "not found", hint)


def check_network_and_auth() -> None:
    step("Network and Hugging Face login")
    try:
        socket.create_connection(("huggingface.co", 443), timeout=4).close()
        record("network", "huggingface.co", "OK", "reachable")
    except OSError as e:
        record("network", "huggingface.co", "WARN", f"not reachable: {e}", "check internet/proxy")
    try:
        from huggingface_hub import get_token  # type: ignore

        tok = get_token()
        record("hf", "login token", "OK" if tok else "WARN", "present (not shown)" if tok else "none",
               "only needed for gated models: run `hf auth login`")
    except Exception:
        record("hf", "login token", "INFO", "huggingface_hub not installed yet")


# --------------------------------------------------------------------------- main
def write_report() -> None:
    REPORTS.mkdir(exist_ok=True)
    write_json(REPORTS / "env_report.json", results)
    lines = ["# Environment report", "", "| Status | Area | Item | Detail | Fix |", "|---|---|---|---|---|"]
    for r in results:
        detail = r["detail"].replace("|", "/")
        lines.append(f"| {r['status']} | {r['area']} | {r['item']} | {detail} | {r['fix']} |")
    missing = [r for r in results if r["status"] == "MISSING"]
    warns = [r for r in results if r["status"] == "WARN"]
    lines += ["", f"**{len(missing)} missing, {len(warns)} warnings.**"]
    (REPORTS / "env_report.md").write_text("\n".join(lines), encoding="utf-8")
    console.rule("Summary")
    console.print(f"[bold]{len(missing)} missing[/bold], {len(warns)} warnings. "
                  f"Report: {REPORTS / 'env_report.md'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe-api", action="store_true", help="list the litert_lm Python API")
    args = ap.parse_args()
    console.rule("Reflection Lab · environment check")
    check_system()
    check_gpu()
    check_python()
    check_tools()
    check_network_and_auth()
    if args.probe_api:
        probe_litert_api()
    write_report()


if __name__ == "__main__":
    main()
