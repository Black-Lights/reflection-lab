"""Build the public, path-free copy of the project in .public/ (its own git repo, own history).

    python scripts/export_public.py                       refresh .public/ and check it for leaks
    python scripts/export_public.py --commit "message"    ... and commit in .public/
    python scripts/export_public.py --commit "msg" --push ... and push .public/ to its 'origin' remote

Copies every file git does not ignore (so local notes, local config, machine reports and models stay
out), skips test/fake runs, and rewrites machine-specific absolute paths in text files to placeholders:
project root -> ".", model folder -> "<models>", home -> "~", any other drive path -> "<local-path>".
The export stops with an error if a drive path, a personal string or a token-like string is left.
Personal strings to block can be listed (one per line) in .public-blocklist (git-ignored).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import ROOT, console, fail, ok, warn  # noqa: E402

OUT = ROOT / ".public"
TEXT = {".py", ".md", ".json", ".jsonl", ".txt", ".toml", ".ps1", ".sh", ".csv", ".yml", ".yaml", ".html",
        ".svg", ".gitignore", ".gitkeep", ""}
SKIP_RUN_NAMES = re.compile(r"_(fake|fake-test|logcheck|gpucheck|portabletest|stagetest|t\d+)$")
ALLOWED_DRIVE = re.compile(r"(?i)\b[A-Z]:[\\/]+(ai-models|path[\\/]to)\b")  # placeholders used in docs
TOKEN = re.compile(r"\bhf_[A-Za-z0-9]{30,}\b|\bsk-[A-Za-z0-9]{20,}\b")
DRIVE = re.compile(r"(?i)\b[A-Z]:(\\\\|\\|/)")


def files_to_export() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    keep = []
    for f in out:
        parts = Path(f).parts
        if parts and parts[0] == "runs" and len(parts) > 1 and SKIP_RUN_NAMES.search(parts[1]):
            continue
        if f in ("runs/LATEST.txt",) or parts[0] in (".public",):
            continue
        keep.append(f)
    return keep


def replacements() -> list[tuple[re.Pattern, str]]:
    home = Path.home()
    pairs = [(ROOT, "."), (home, "~"), (Path(sys.base_prefix), "<python>")]
    # the configured download / model folders of this machine (from config.local.toml), if any
    try:
        from lab.common import load_config
        cfg = load_config()
        d = cfg.get("download", {}).get("dir")
        if d and Path(d).is_absolute():
            pairs.append((Path(d), "<models>"))
        for k in ("hf_token_file",):
            v = cfg.get("download", {}).get(k)
            if v:
                pairs.append((Path(v), "<token-file>"))
        for f in cfg.get("scan", {}).get("named_folders", []) + cfg.get("scan", {}).get("roots", []):
            pairs.append((Path(f), "<model-folder>"))
    except Exception:
        pass
    pairs.sort(key=lambda p: -len(str(p[0])))  # longest prefix first
    out = []
    for path, new in pairs:
        s = str(path)
        for variant in {s, s.replace("\\", "/"), s.replace("\\", "\\\\")}:
            out.append((re.compile(re.escape(variant), re.I), new))
    return out


def sanitize(text: str, reps) -> str:
    for rx, new in reps:
        text = rx.sub(new.replace("\\", "\\\\"), text)
    # any other absolute drive path that is left (a file name after it is kept)
    return re.sub(r"(?i)\b[A-Z]:(?:\\\\|\\|/)(?:[^\"'\s<>|*?:,;)\]]+(?:\\\\|\\|/))*", "<local-path>/", text) \
        if DRIVE.search(ALLOWED_DRIVE.sub("", text)) else text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", help="commit message for .public/")
    ap.add_argument("--push", action="store_true", help="git push .public/ to its origin")
    args = ap.parse_args()

    reps = replacements()
    block = [ln.strip() for ln in (ROOT / ".public-blocklist").read_text(encoding="utf-8").splitlines()
             if ln.strip()] if (ROOT / ".public-blocklist").exists() else []
    files = files_to_export()
    OUT.mkdir(exist_ok=True)
    # remove previously exported files that no longer exist (keep .git)
    wanted = set(files)
    for p in OUT.rglob("*"):
        rel = p.relative_to(OUT).as_posix()
        if p.is_file() and not rel.startswith(".git/") and rel not in wanted:
            p.unlink()
    problems = []
    for f in files:
        src, dst = ROOT / f, OUT / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in TEXT or src.name in (".gitignore",):
            try:
                text = src.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src, dst)
                continue
            clean = sanitize(text, reps)
            leftover = DRIVE.search(ALLOWED_DRIVE.sub("", clean))
            if leftover:
                problems.append(f"{f}: drive path left near '{clean[max(0, leftover.start() - 30):leftover.end() + 30]}'")
            if TOKEN.search(clean):
                problems.append(f"{f}: token-like string")
            for b in block:
                if re.search(r"" + re.escape(b) + r"", clean, re.I):  # whole words only
                    problems.append(f"{f}: blocked string '{b}'")
            dst.write_text(clean, encoding="utf-8", newline="")
        else:
            shutil.copy2(src, dst)
    if problems:
        for p in problems[:40]:
            fail(p)
        fail(f"{len(problems)} problem(s): nothing committed. Fix the sources or the replacements.")
        sys.exit(1)
    ok(f"exported {len(files)} files to {OUT} — no drive paths, tokens or blocked strings")

    if args.commit:
        if not (OUT / ".git").exists():
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=OUT, check=True)
            subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=OUT, check=True)
        subprocess.run(["git", "add", "-A"], cwd=OUT, check=True)
        from lab.common import GIT_TRAILER
        r = subprocess.run(["git", "commit", "-q", "-m", args.commit + GIT_TRAILER], cwd=OUT)
        (ok if r.returncode == 0 else warn)("committed in .public/" if r.returncode == 0 else "nothing to commit")
    if args.push:
        r = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=OUT)
        (ok if r.returncode == 0 else fail)("pushed" if r.returncode == 0 else "push failed")


if __name__ == "__main__":
    main()
