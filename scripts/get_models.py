"""Show which project models are present and download the missing ones from Hugging Face.

    python scripts/get_models.py                       status table only (no downloads)
    python scripts/get_models.py --plan                show which files would be downloaded and their size
    python scripts/get_models.py --required --yes      download all required models that are missing
    python scripts/get_models.py --get qwen3-4b --yes  download specific models

Downloads go to [download] dir in config.toml (default ./models), keeping the file name from
the Hugging Face repo, and are registered in models.local.json. The Hugging Face token comes from
HF_TOKEN in the environment or from [download] hf_token_file; it is never printed.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    ROOT, console, expand, fail, human_size, load_config, load_model_paths, ok, save_model_paths, step, warn,
)

TOKEN_VARS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN")


def download_dir(cfg: dict, override: str | None = None) -> Path:
    """Folder for new downloads: --dest, else [download] dir, else ./models. Relative = from ROOT."""
    p = expand(override or cfg.get("download", {}).get("dir") or "models")
    return p if p.is_absolute() else ROOT / p


def hf_token(cfg: dict) -> tuple[str | None, str]:
    """Return (token, where it came from). The token itself must never be printed or logged."""
    for var in TOKEN_VARS:
        if os.environ.get(var):
            return os.environ[var], f"environment variable {var}"
    f = cfg.get("download", {}).get("hf_token_file")
    if not f:
        return None, "none (anonymous)"
    path = expand(f)
    if not path.exists():
        warn(f"hf_token_file not found: {path}  (continuing without a token)")
        return None, "none (anonymous)"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, sep, val = line.partition("=")
        if sep and key.strip() in TOKEN_VARS:
            val = val.split(" #")[0].strip().strip('"').strip("'")
            if val:
                return val, f"{key.strip()} in {path}"
    warn(f"No HF_TOKEN line in {path}  (continuing without a token)")
    return None, "none (anonymous)"


def pick_file(repo: str, hint: str, token: str | None = None,
              exact: str | None = None) -> tuple[str, int | None, list[tuple[str, int | None]]]:
    """Choose the .litertlm file in a repo. Returns (filename, size, all_candidates).

    `exact` (catalog `file`) pins the file name; otherwise `hint` and a size heuristic decide.
    """
    from huggingface_hub import HfApi

    info = HfApi(token=token).model_info(repo, files_metadata=True)
    files = [(s.rfilename, getattr(s, "size", None)) for s in info.siblings if s.rfilename.endswith(".litertlm")]
    if not files:
        raise RuntimeError(f"No .litertlm file in {repo}")
    if exact:
        pinned = [f for f in files if f[0] == exact]
        if not pinned:
            raise RuntimeError(f"Pinned file {exact!r} is not in {repo} (available: {', '.join(f for f, _ in files)})")
        return pinned[0][0], pinned[0][1], files
    cands = files
    if hint:
        hinted = [f for f in files if hint.lower() in f[0].lower()]
        cands = hinted or files
    # Avoid web-only / float variants when there is a choice; then prefer the smallest.
    preferred = [f for f in cands if "web" not in f[0].lower()] or cands
    best = sorted(preferred, key=lambda f: f[1] or 1 << 62)[0]
    return best[0], best[1], files


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true", help="look up file names and sizes for missing models")
    ap.add_argument("--required", action="store_true", help="download all missing required models")
    ap.add_argument("--get", nargs="*", default=[], help="model keys to download")
    ap.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    ap.add_argument("--dest", help="download folder (overrides [download] dir in config.toml)")
    args = ap.parse_args()

    cfg = load_config()
    paths = load_model_paths()
    catalog = cfg.get("catalog", [])
    overrides = cfg.get("paths", {})

    console.rule("Reflection Lab · project models")
    status = {}
    for m in catalog:
        p = overrides.get(m["key"]) or paths.get(m["key"])
        present = bool(p) and Path(p).exists()
        status[m["key"]] = present
        mark = "[green]present[/green]" if present else ("[red]missing[/red]" if m["required"] else "[yellow]missing (optional)[/yellow]")
        console.print(f"  {m['key']:<20} {m['role']:<28} {mark}  {p or ''}")

    want = set(args.get)
    if args.required:
        want |= {m["key"] for m in catalog if m["required"] and not status[m["key"]]}
    unknown = want - {m["key"] for m in catalog}
    if unknown:
        fail(f"Unknown model keys: {', '.join(sorted(unknown))}")
        sys.exit(1)

    if not (want or args.plan):
        missing_req = [m["key"] for m in catalog if m["required"] and not status[m["key"]]]
        if missing_req:
            console.print(f"\nNext: [bold]python scripts/get_models.py --plan[/bold] then "
                          f"[bold]--required --yes[/bold] to download {', '.join(missing_req)}")
        else:
            ok("All required models are present.")
        return

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        fail("huggingface_hub is not installed: pip install huggingface_hub")
        sys.exit(1)

    dest = download_dir(cfg, args.dest)
    token, token_src = hf_token(cfg)
    console.print(f"\nDownload folder: {dest}\nHugging Face token: {token_src}")

    targets = [m for m in catalog if (m["key"] in want) or (args.plan and not want and not status[m["key"]])]
    plan = []
    for m in targets:
        step(f"Looking up {m['repo']}")
        try:
            fname, size, allf = pick_file(m["repo"], m.get("file_hint", ""), token, m.get("file"))
        except Exception as e:
            fail(f"{m['key']}: {e}")
            if "401" in str(e) or "403" in str(e) or "gated" in str(e).lower():
                console.print("   Either the repo needs a login/licence (run `hf auth login` and accept the licence on the "
                              "model page) or a firewall/proxy blocks huggingface.co.")
            continue
        plan.append((m, fname, size))
        console.print(f"   → {fname}  ({human_size(size) if size else 'size unknown'})")
        if len(allf) > 1:
            console.print("     other files: " + ", ".join(f"{f} ({human_size(s) if s else '?'})" for f, s in allf if f != fname))

    total = sum(s or 0 for _, _, s in plan)
    if args.plan:  # plan only, never download (also with --get / --required)
        free = shutil.disk_usage(dest if dest.exists() else dest.anchor).free
        console.print(f"\nPlanned download: {human_size(total)} → {dest}  (free on that drive: {human_size(free)})")
        return

    dest.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(dest).free
    if total and total * 1.1 > free:
        fail(f"Not enough disk space: need {human_size(total)}, free {human_size(free)}")
        sys.exit(1)
    if not args.yes:
        if not sys.stdin.isatty():
            fail("Confirmation needed: re-run with --yes after the user agreed.")
            sys.exit(2)
        ans = input(f"Download {len(plan)} file(s), {human_size(total)}? [y/N] ").strip().lower()
        if ans != "y":
            warn("Cancelled.")
            return

    for m, fname, size in plan:
        step(f"Downloading {m['repo']}/{fname} ({human_size(size) if size else '?'}) → {dest}")
        try:
            p = hf_hub_download(repo_id=m["repo"], filename=fname, local_dir=str(dest), token=token)
        except Exception as e:
            fail(f"Download failed for {m['key']}: {e}")
            continue
        paths[m["key"]] = str(Path(p).resolve())
        save_model_paths(paths)
        ok(f"{m['key']} ready: {p}")


if __name__ == "__main__":
    main()
