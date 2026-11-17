"""Find model files you already have. Read-only: nothing is moved, copied or deleted.

    python scripts/find_models.py                 scan roots + caches from config.toml
    python scripts/find_models.py --root <local-path>/ai    scan extra folders too
    python scripts/find_models.py --no-register   don't write models.local.json

Writes reports/model_inventory.md + .json, and registers any .litertlm file that
matches a catalog entry (e.g. Gemma 4 E4B, Qwen3 1.7B) in models.local.json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    HAVE_RICH, REPORTS, console, expand, human_size, load_config, load_model_paths, ok,
    save_model_paths, step, warn, write_json,
)

MODEL_EXT = {
    ".litertlm": "LiteRT-LM bundle",
    ".task": "MediaPipe/LiteRT task bundle",
    ".tflite": "TFLite model",
    ".gguf": "GGUF (llama.cpp / Ollama / LM Studio)",
    ".safetensors": "safetensors weights",
    ".bin": "binary weights",
    ".pt": "PyTorch weights",
    ".pth": "PyTorch weights",
    ".ckpt": "checkpoint",
    ".onnx": "ONNX model",
    ".mlmodel": "CoreML model",
    ".engine": "TensorRT engine",
}
ALWAYS_LIST = {".litertlm", ".task"}

# Architectures the LiteRT `litert-torch export_hf` converter documents as supported.
LITERT_CONVERTIBLE = {
    "Gemma3ForCausalLM", "Gemma3nForCausalLM", "Gemma4ForCausalLM", "Gemma3ForConditionalGeneration",
    "Gemma4ForConditionalGeneration", "LlamaForCausalLM", "MistralForCausalLM", "Qwen2ForCausalLM",
    "Qwen3ForCausalLM", "SmolLM3ForCausalLM",
}

FAMILY_PATTERNS = [
    ("gemma", r"gemma"), ("qwen", r"qwen"), ("llama", r"llama"), ("phi", r"\bphi[-_]?\d"),
    ("mistral", r"mistral|mixtral"), ("smollm", r"smol"), ("deepseek", r"deepseek"),
    ("stable-diffusion", r"stable[-_]?diffusion|\bsd[-_]?(1\.5|2|xl|3)|sdxl"), ("flux", r"\bflux"),
    ("vae", r"\bvae\b"), ("lora", r"lora"), ("controlnet", r"controlnet"), ("clip", r"\bclip"),
    ("whisper", r"whisper"), ("embedding", r"embed|bge|e5[-_]|minilm|nomic"), ("yolo", r"yolo"),
    ("sam", r"\bsam[-_]?\d?\b|segment[-_]?anything"), ("vit", r"\bvit\b|siglip|dino"),
]
IMAGE_FAMILIES = {"stable-diffusion", "flux", "vae", "lora", "controlnet", "yolo", "sam", "vit", "clip"}


def default_cache_dirs() -> list[Path]:
    home = Path.home()
    env = os.environ
    dirs = [
        Path(env["HF_HOME"]) / "hub" if env.get("HF_HOME") else home / ".cache" / "huggingface" / "hub",
        home / ".lmstudio" / "models",
        home / ".cache" / "lm-studio" / "models",
        Path(env["OLLAMA_MODELS"]) if env.get("OLLAMA_MODELS") else home / ".ollama" / "models",
        home / "jan" / "models",
        home / "AppData" / "Local" / "nomic.ai" / "GPT4All",
        # llama.cpp `-hf` / `--hf-repo` downloads (LLAMA_CACHE overrides the default location)
        Path(env["LLAMA_CACHE"]) if env.get("LLAMA_CACHE") else home / "AppData" / "Local" / "llama.cpp",
        home / ".cache" / "llama.cpp",
        home / "Downloads",
    ]
    return [d for d in dirs if d.exists()]


def guess_family(*texts: str) -> str:
    """Try the most specific text first (file name), then broader ones (folders)."""
    for text in texts:
        t = text.lower().replace(".ollama", "")
        for fam, pat in FAMILY_PATTERNS:
            if re.search(pat, t):
                return fam
    return "unknown"


def usability(entry: dict) -> str:
    ext, fam = entry.get("ext"), entry.get("family")
    if ext in (".litertlm", ".task"):
        return "READY (LiteRT-LM)"
    if entry.get("kind") == "hf-model":
        if entry.get("architecture") in LITERT_CONVERTIBLE:
            return "CONVERTIBLE (litert-torch export_hf)"
        if entry.get("architecture"):
            return "HF checkpoint (not on converter list)"
    if entry.get("kind") == "diffusers-pipeline" or fam in IMAGE_FAMILIES:
        return "IMAGE model (later: vision/multimodal)"
    if ext == ".gguf":
        return "GGUF (PC-only: llama.cpp/Ollama, e.g. as judge)"
    return "other"


class Scanner:
    def __init__(self, skip_dirs: set[str], min_bytes: int):
        self.skip = {s.lower() for s in skip_dirs}
        self.min_bytes = min_bytes
        self.entries: list[dict] = []
        self.seen_real: set[str] = set()
        self.dirs_scanned = 0
        self.current = ""

    def scan(self, root: Path, status=None) -> None:
        stack = [root]
        while stack:
            d = stack.pop()
            self.dirs_scanned += 1
            self.current = str(d)
            if status and self.dirs_scanned % 50 == 0:
                status.update(f"[cyan]Scanning[/cyan] {self.dirs_scanned} folders · {len(self.entries)} models found · {str(d)[-70:]}")
            try:
                with os.scandir(d) as it:
                    items = list(it)
            except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
                continue
            names = {i.name for i in items}
            # A Hugging Face style model folder: config.json + weights. Record it as one model.
            if "config.json" in names and any(n.endswith((".safetensors", ".bin")) for n in names):
                self._add_hf_dir(d, items)
            if "model_index.json" in names:  # diffusers pipeline (image generation)
                self._add_diffusers(d)
            for it in items:
                try:
                    if it.is_dir(follow_symlinks=False):
                        if it.name.lower() not in self.skip and not it.name.startswith("."):
                            stack.append(Path(it.path))
                        elif it.name in (".cache", ".ollama", ".lmstudio"):
                            stack.append(Path(it.path))
                        continue
                    ext = Path(it.name).suffix.lower()
                    if ext not in MODEL_EXT and not it.name.startswith("sha256-"):
                        continue
                    st = os.stat(it.path)  # follows HF cache symlinks
                    if st.st_size < self.min_bytes and ext not in ALWAYS_LIST:
                        continue
                    real = os.path.realpath(it.path)
                    if real in self.seen_real:
                        continue
                    self.seen_real.add(real)
                    self._add_file(Path(it.path), ext, st.st_size)
                except OSError:
                    continue

    def _add_file(self, path: Path, ext: str, size: int) -> None:
        if path.name.startswith("sha256-") and "ollama" in str(path).lower():
            if size < self.min_bytes:
                return
            ext = ".gguf"  # Ollama blobs are GGUF files without extension
        e = {
            "kind": "file", "path": str(path), "name": path.name, "ext": ext,
            "format": MODEL_EXT.get(ext, "ollama blob"), "size": size,
            "family": "unknown" if path.name.startswith("sha256-") else guess_family(path.name, path.parent.name, str(path)),
        }
        e["usable"] = usability(e)
        self.entries.append(e)

    def _add_hf_dir(self, d: Path, items) -> None:
        try:
            cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        arch = (cfg.get("architectures") or [None])[0]
        size = 0
        for it in items:
            if it.name.endswith((".safetensors", ".bin")):
                try:
                    size += os.stat(it.path).st_size
                    self.seen_real.add(os.path.realpath(it.path))
                except OSError:
                    pass
        e = {
            "kind": "hf-model", "path": str(d), "name": d.name, "ext": "", "format": "Hugging Face checkpoint",
            "size": size, "architecture": arch, "model_type": cfg.get("model_type"),
            "family": guess_family(f"{arch} {cfg.get('model_type')}", d.name, str(d)),
        }
        e["usable"] = usability(e)
        self.entries.append(e)

    def _add_diffusers(self, d: Path) -> None:
        e = {"kind": "diffusers-pipeline", "path": str(d), "name": d.name, "ext": "", "size": 0,
             "format": "diffusers pipeline", "family": guess_family(d.name, str(d))}
        e["usable"] = usability(e)
        self.entries.append(e)


def ollama_names(models_dir: Path) -> dict[str, str]:
    """Map Ollama blob digests to model names using the manifests."""
    names = {}
    man = models_dir / "manifests"
    if not man.exists():
        return names
    for f in man.rglob("*"):
        if f.is_file():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for layer in data.get("layers", []):
                    if layer.get("mediaType", "").endswith("image.model"):
                        digest = layer["digest"].replace(":", "-")
                        names[digest] = f"{f.parent.name}:{f.name}"
            except Exception:
                continue
    return names


def register_matches(cfg: dict, entries: list[dict]) -> dict:
    """Match local .litertlm files to catalog keys and save to models.local.json."""
    paths = load_model_paths()
    found = {}
    for m in cfg.get("catalog", []):
        pat = re.compile(m["match"], re.I)
        cands = [e for e in entries if e.get("ext") == ".litertlm" and pat.search(e["path"].lower())]
        if cands:
            best = sorted(cands, key=lambda e: e["size"])[0]  # smallest = most quantized
            found[m["key"]] = best["path"]
    for k, p in found.items():
        if paths.get(k) != p:
            paths[k] = p
    return found, paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", action="append", default=[], help="extra folder to scan (repeatable)")
    ap.add_argument("--no-caches", action="store_true", help="skip default cache folders")
    ap.add_argument("--no-register", action="store_true", help="don't update models.local.json")
    args = ap.parse_args()

    cfg = load_config()
    sc = cfg.get("scan", {})
    roots = [expand(r) for r in sc.get("roots", [])] + [expand(r) for r in args.root]
    named = [expand(r) for r in sc.get("named_folders", [])]
    for n in named:
        if not n.exists():
            warn(f"Named folder not found: {n}  (check the exact folder name and fix config.toml → scan.named_folders)")
    roots += [n for n in named if n.exists()]
    if sc.get("include_default_caches", True) and not args.no_caches:
        roots += default_cache_dirs()
    # remove roots nested in other roots
    roots = [r for r in dict.fromkeys(roots) if r.exists()]
    roots = [r for r in roots if not any(r != o and str(r).lower().startswith(str(o).lower() + os.sep) for o in roots)]

    console.rule("Reflection Lab · model scan (read-only)")
    for r in roots:
        console.print(f"  • {r}")
    scanner = Scanner(set(sc.get("skip_dirs", [])), int(sc.get("min_size_mb", 20)) * 1024 * 1024)
    t0 = time.time()
    if HAVE_RICH:
        with console.status("Scanning…") as status:
            for r in roots:
                scanner.scan(r, status)
    else:
        for r in roots:
            step(f"Scanning {r}")
            scanner.scan(r)
    entries = scanner.entries

    # Give Ollama blobs their model names (from <models>/manifests)
    blob_dirs = {Path(e["path"]).parent.parent for e in entries if e["name"].startswith("sha256-")}
    for models_dir in blob_dirs:
        names = ollama_names(models_dir)
        for e in entries:
            if e["name"] in names and Path(e["path"]).parent.parent == models_dir:
                e["name"] = f"ollama:{names[e['name']]}"
                e["family"] = guess_family(e["name"])
                e["usable"] = usability(e)

    ok(f"Scanned {scanner.dirs_scanned} folders in {time.time() - t0:.1f}s · {len(entries)} model entries")

    groups: dict[str, list[dict]] = {}
    for e in sorted(entries, key=lambda e: (-e["size"])):
        groups.setdefault(e["usable"], []).append(e)

    order = ["READY (LiteRT-LM)", "CONVERTIBLE (litert-torch export_hf)", "GGUF (PC-only: llama.cpp/Ollama, e.g. as judge)",
             "IMAGE model (later: vision/multimodal)", "HF checkpoint (not on converter list)", "other"]
    md = ["# Model inventory", "", f"Scanned: {', '.join(str(r) for r in roots)}", ""]
    for g in order:
        items = groups.get(g, [])
        if not items:
            continue
        if HAVE_RICH:
            from rich.table import Table

            t = Table(title=f"{g} · {len(items)}", title_justify="left", show_lines=False)
            for col in ("name", "family", "size", "path"):
                t.add_column(col, overflow="fold")
            for e in items[:60]:
                extra = f" ({e['architecture']})" if e.get("architecture") else ""
                t.add_row(e["name"] + extra, e["family"], human_size(e["size"]) if e["size"] else "-", e["path"])
            console.print(t)
            if len(items) > 60:
                console.print(f"  … and {len(items) - 60} more (see report)")
        else:
            console.print(f"\n{g} ({len(items)})")
            for e in items[:60]:
                console.print(f"  {e['name']:<50} {human_size(e['size']):>10}  {e['path']}")
        md += [f"## {g} ({len(items)})", "", "| Name | Family | Arch | Size | Path |", "|---|---|---|---|---|"]
        for e in items:
            md.append(f"| {e['name']} | {e['family']} | {e.get('architecture') or ''} | "
                      f"{human_size(e['size']) if e['size'] else '-'} | `{e['path']}` |")
        md.append("")

    found, paths = register_matches(cfg, entries)
    md += ["## Matched to project models", ""]
    for m in cfg.get("catalog", []):
        p = found.get(m["key"])
        line = f"- **{m['key']}** ({m['role']}): " + (f"found → `{p}`" if p else "not found locally")
        md.append(line)
        (ok if p else warn)(f"{m['key']:<20} " + (f"found: {p}" if p else "not found locally"))

    REPORTS.mkdir(exist_ok=True)
    write_json(REPORTS / "model_inventory.json", entries)
    (REPORTS / "model_inventory.md").write_text("\n".join(md), encoding="utf-8")
    if not args.no_register and found:
        save_model_paths(paths)
        ok("Registered matches in models.local.json")
    console.print(f"Report: {REPORTS / 'model_inventory.md'}")


if __name__ == "__main__":
    main()
