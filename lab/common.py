"""Shared helpers: paths, config, console output, JSON files.

Works with the standard library only, so check_env.py can run before anything
is installed. If `rich` is installed, output is coloured.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"
MODELS_LOCAL = ROOT / "models.local.json"
REPORTS = ROOT / "reports"
RUNS = ROOT / "runs"

# --------------------------------------------------------------------------- console
# Windows: when output is piped (e.g. captured by Claude Code) Python uses the legacy code page,
# which can't print symbols like ✓ or →. Force UTF-8 and never crash on a character.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

try:
    from rich.console import Console

    console = Console(highlight=False)
    HAVE_RICH = True
except ImportError:  # plain fallback before `pip install rich`
    HAVE_RICH = False
    _MARKUP = re.compile(r"\[/?[a-z0-9 _#.,=-]*\]")

    class _PlainConsole:
        def print(self, *args, **kwargs):
            print(*[_MARKUP.sub("", str(a)) for a in args])

        def rule(self, title: str = "", **kwargs):
            print(f"\n==== {_MARKUP.sub('', title)} ====")

        def input(self, prompt: str = "") -> str:
            return input(_MARKUP.sub("", prompt))

    console = _PlainConsole()


def step(msg: str) -> None:
    """Print a visible 'what I'm doing now' line."""
    console.print(f"[bold cyan]▶ {msg}[/bold cyan]")


def ok(msg: str) -> None:
    console.print(f"[green]✓ {msg}[/green]")


def warn(msg: str) -> None:
    console.print(f"[yellow]! {msg}[/yellow]")


def fail(msg: str) -> None:
    console.print(f"[bold red]✗ {msg}[/bold red]")


# --------------------------------------------------------------------------- config
def _load_toml(path: Path) -> dict:
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            fail("Python 3.11+ is required (tomllib missing). Install Python 3.11 or 3.12.")
            sys.exit(1)
    with open(path, "rb") as f:
        return tomllib.load(f)


LOCAL_CONFIG_PATH = ROOT / "config.local.toml"  # machine-specific overrides, git-ignored


def _merge(base: dict, extra: dict) -> dict:
    for k, v in extra.items():
        base[k] = _merge(dict(base[k]), v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return base


def load_config() -> dict:
    """config.toml, with config.local.toml (if present) merged over it table by table."""
    cfg = _load_toml(CONFIG_PATH)
    if LOCAL_CONFIG_PATH.exists():
        cfg = _merge(cfg, _load_toml(LOCAL_CONFIG_PATH))
    return cfg


def expand(p: str | os.PathLike) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(p))))


# --------------------------------------------------------------------------- json helpers
def read_json(path: Path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append_jsonl(path: Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- models
def load_model_paths() -> dict:
    """key -> absolute path of a .litertlm file (written by find_models / get_models)."""
    return read_json(MODELS_LOCAL, {}) or {}


def save_model_paths(paths: dict) -> None:
    write_json(MODELS_LOCAL, paths)


def catalog_by_key(cfg: dict) -> dict:
    return {m["key"]: m for m in cfg.get("catalog", [])}


def resolve_model(cfg: dict, key: str) -> Path | None:
    """Explicit override in [paths] wins, then models.local.json."""
    override = cfg.get("paths", {}).get(key)
    if override:
        return expand(override)
    found = load_model_paths().get(key)
    return Path(found) if found else None


# --------------------------------------------------------------------------- misc
def rel_to_root(p) -> str:
    """Path as a string relative to the project when it lies inside it (portable run records)."""
    p = Path(p)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p)


def from_root(p) -> Path:
    """Inverse of rel_to_root: relative paths are taken from the project folder."""
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def latest_run_dir() -> Path | None:
    marker = RUNS / "LATEST.txt"
    if marker.exists():
        p = Path(marker.read_text(encoding="utf-8").strip())
        if p.exists():
            return p
    runs = sorted([d for d in RUNS.glob("*") if d.is_dir()])
    return runs[-1] if runs else None


# --------------------------------------------------------------------------- git
GIT_TRAILER = ("\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
               "Claude-Session: https://claude.ai/code/session_01NR9PfPebyPP1GTzSGrZFan")


def git_snapshot(message: str) -> bool:
    """Commit everything (results included) so nothing is lost if a run or a session stops.
    Silent no-op when the project is not a git repo or nothing changed. Never pushes."""
    import subprocess

    if not (ROOT / ".git").exists():
        return False
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, capture_output=True, timeout=120)
        r = subprocess.run(["git", "commit", "-q", "-m", message + GIT_TRAILER], cwd=ROOT,
                           capture_output=True, timeout=120)
        return r.returncode == 0
    except Exception:
        return False
