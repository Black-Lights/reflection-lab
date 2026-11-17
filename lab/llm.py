"""Thin wrapper around the model runtimes so the experiment code never changes.

Three runtimes:
  python : LiteRT-LM Python API (`pip install litert-lm-api`, `import litert_lm`)
  cli    : the `litert-lm` command-line tool (reloads the model on every call: slower,
           but useful if the Python API is not available on Windows)
  fake   : no model at all, for testing the pipeline and the live view

The Python calls were checked against litert-lm-api 0.19.2 (Windows wheel exists):
Engine(model_path, backend=Backend.GPU()|CPU(), max_num_tokens=...),
engine.create_conversation(thinking_config=, sampler_config=, max_output_tokens=),
conversation.send_message(...) -> Message (dict subclass), send_message_async(...) -> iterator.
If a newer version changes this: run `python scripts/check_env.py --probe-api` and adapt this file.
"""
from __future__ import annotations

import contextlib
import gc
import random
import re
import shutil
import subprocess
import time
import zlib
from pathlib import Path
from typing import Callable, Optional

TokenCallback = Optional[Callable[[str], None]]

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S)


def clean_output(text: str, strip_think: bool = True) -> tuple[str, dict]:
    """Remove <think>…</think> blocks (Qwen3). Returns (clean_text, flags)."""
    flags = {}
    if strip_think and "<think>" in text:
        flags["had_thinking"] = True
        text = _THINK_BLOCK.sub("", text)
        if "<think>" in text:  # thinking never closed: ran out of tokens
            flags["thinking_truncated"] = True
            text = text.split("<think>")[0]
    return text.strip(), flags


def _extract_text(resp) -> str:
    """Handle the documented dict shape plus a few plausible alternatives."""
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        content = resp.get("content")
        if isinstance(content, list):
            return "".join(
                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
            )
        if isinstance(content, str):
            return content
        if "text" in resp:
            return str(resp["text"])
    for attr in ("text", "content"):
        if hasattr(resp, attr):
            return _extract_text(getattr(resp, attr))
    return str(resp)


class BaseLLM:
    runtime = "base"

    def __init__(self, key: str, path: Path | None, backend: str, gen: dict):
        self.key = key
        self.path = path
        self.backend = backend
        self.gen = gen
        self.load_seconds = 0.0

    @property
    def name(self) -> str:
        return f"{self.key} [{self.runtime}/{self.backend}]"

    def load(self) -> None: ...

    def generate(self, prompt: str, on_token: TokenCallback = None, **kw) -> str:
        """kw: tools=True gives the model a calculator and date_add (python runtime only)."""
        raise NotImplementedError

    def close(self) -> None: ...


# --------------------------------------------------------------------------- fake
class FakeLLM(BaseLLM):
    """Deterministic stand-in. Streams text slowly so you can watch the live view."""

    runtime = "fake"

    def load(self) -> None:
        t = time.time()
        time.sleep(0.3)
        self.load_seconds = time.time() - t

    def generate(self, prompt: str, on_token: TokenCallback = None, **kw) -> str:
        rnd = random.Random(zlib.crc32(prompt.encode("utf-8")))
        if prompt.rstrip().endswith("YOUR AUDIT:"):
            text = (
                "VERDICT: ISSUES\n- [UNSUPPORTED] The draft adds a detail not in the document."
                if rnd.random() < 0.4
                else "VERDICT: OK"
            )
        elif prompt.rstrip().endswith("FINAL ANSWER:"):
            text = "(fake refined answer) The document states the relevant fact."
        else:
            text = rnd.choice(
                [
                    "(fake answer) According to the document, the answer is stated in paragraph one.",
                    "(fake answer) The document does not say.",
                    "(fake answer) It was probably about 50, although the text is unclear. [UNSURE]",
                ]
            )
        out = ""
        for word in text.split(" "):
            piece = word + " "
            out += piece
            if on_token:
                on_token(piece)
            time.sleep(0.02)
        return out.strip()


# --------------------------------------------------------------------------- python API
class PyLiteRT(BaseLLM):
    runtime = "python"

    def __init__(self, *a, log_level: str = "error", **kw):
        super().__init__(*a, **kw)
        self._stack: contextlib.ExitStack | None = None
        self.engine = None
        self.lm = None
        self.log_level = log_level

    def load(self) -> None:
        import litert_lm  # noqa: WPS433  (pip install litert-lm-api)

        self.lm = litert_lm
        # The native runtime prints ~180 INFO/WARNING lines per model load straight to the console
        # (no NPU found, KV-cache buffer hints, unused audio/vision parts), which break the live view.
        # None of them are errors (checked 2026-11-17). Must be set before Engine() to take effect.
        level = getattr(getattr(litert_lm, "LogSeverity", None), str(self.log_level).upper(), None)
        if level is not None and hasattr(litert_lm, "set_min_log_severity"):
            litert_lm.set_min_log_severity(level)
        backend = litert_lm.Backend.GPU() if self.backend == "gpu" else litert_lm.Backend.CPU()
        t = time.time()
        self._stack = contextlib.ExitStack()
        kwargs = {"backend": backend}
        if self.gen.get("max_num_tokens"):  # context window (prompt + answer)
            kwargs["max_num_tokens"] = int(self.gen["max_num_tokens"])
        engine = litert_lm.Engine(str(self.path), **kwargs)
        # Documented usage is `with Engine(...) as engine:`; keep it open across calls.
        self.engine = self._stack.enter_context(engine) if hasattr(engine, "__enter__") else engine
        self.load_seconds = time.time() - t

    def _conversation(self, tools=None):
        """Fresh conversation per call (no memory between test cases). tools: Python functions or None.

        Verified against litert-lm-api 0.19.2: create_conversation(*, thinking_config,
        sampler_config, max_output_tokens, system_message, ...). Older versions may lack
        some keywords, so we retry with fewer.
        """
        lm = self.lm
        full: dict = {"max_output_tokens": int(self.gen.get("max_output_tokens", 512))}
        enable = bool(self.gen.get("enable_thinking", False))
        try:
            full["thinking_config"] = lm.ThinkingConfig(
                enable_thinking=enable, thinking_token_budget=-1 if enable else 0
            )
        except Exception:
            pass
        if self.gen.get("greedy", True):
            try:  # top_k=1 → always pick the most likely token (reproducible runs)
                full["sampler_config"] = lm.SamplerConfig(top_k=1, seed=int(self.gen.get("seed", 0)))
            except Exception:
                pass
        attempts = [full, {k: v for k, v in full.items() if k != "sampler_config"},
                    {"max_output_tokens": full["max_output_tokens"]}, {}]
        if tools:
            attempts = [{**a, "tools": tools} for a in attempts]
        last_err = None
        for kw in attempts:
            try:
                return self.engine.create_conversation(**kw)
            except TypeError as e:  # keyword not supported by this version
                last_err = e
        raise RuntimeError(f"create_conversation failed: {last_err}")

    def generate(self, prompt: str, on_token: TokenCallback = None, tools: bool = False, **kw) -> str:
        """tools=True: the model may call calculator and date_add (LiteRT-LM automatic tool calling).
        The calls of the last generate() are in self.last_tool_log ([] without tools)."""
        self.last_tool_log, tool_fns = [], None
        if tools:
            from lab.agent_env import make_math_tools  # noqa: WPS433

            tool_fns, self.last_tool_log = make_math_tools()
        with self._conversation(tool_fns) as conv:
            if not tool_fns and on_token and self.gen.get("stream", True) and hasattr(conv, "send_message_async"):
                # Yields Message chunks (dict subclass) as text is produced.
                out = ""
                for chunk in conv.send_message_async(prompt):
                    piece = _extract_text(chunk)
                    if out and piece.startswith(out):  # cumulative chunks → take the new part
                        delta, out = piece[len(out):], piece
                    else:  # delta chunks
                        delta, out = piece, out + piece
                    if delta:
                        on_token(delta)
                return out
            resp = conv.send_message(prompt)
            text = _extract_text(resp)
            if on_token:
                on_token(text)
            return text

    def close(self) -> None:
        if self._stack is not None:
            self._stack.close()
        self.engine = None
        self._stack = None
        gc.collect()


# --------------------------------------------------------------------------- CLI
class CliLiteRT(BaseLLM):
    """Calls `litert-lm run <model> --backend=... --prompt=...` and streams stdout live."""

    runtime = "cli"

    def __init__(self, *a, exe: str = "litert-lm", extra_args=None, output_filter: str = "", **kw):
        super().__init__(*a, **kw)
        self.exe = exe
        self.extra_args = list(extra_args or [])
        self.filter = re.compile(output_filter) if output_filter else None

    def load(self) -> None:
        if not shutil.which(self.exe):
            raise RuntimeError(f"'{self.exe}' not found on PATH. Install with: pip install litert-lm")

    def generate(self, prompt: str, on_token: TokenCallback = None, **kw) -> str:
        cmd = [self.exe, "run", str(self.path), f"--backend={self.backend}", f"--prompt={prompt}"]
        cmd += self.extra_args
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        lines = []
        assert proc.stdout is not None
        for line in proc.stdout:
            if self.filter and self.filter.search(line):
                continue  # drop runtime log lines
            lines.append(line)
            if on_token:
                on_token(line)
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"litert-lm exited with code {proc.returncode}: {''.join(lines)[-500:]}")
        return "".join(lines)


def make_llm(runtime: str, key: str, path: Path | None, backend: str, gen: dict, run_cfg: dict) -> BaseLLM:
    if runtime == "fake":
        return FakeLLM(key, path, backend, gen)
    if path is None or not Path(path).exists():
        raise FileNotFoundError(
            f"No model file for '{key}'. Run: python scripts/find_models.py, then python scripts/get_models.py"
        )
    if runtime == "python":
        return PyLiteRT(key, Path(path), backend, gen, log_level=run_cfg.get("runtime_log_level", "error"))
    if runtime == "cli":
        return CliLiteRT(
            key,
            Path(path),
            backend,
            gen,
            exe=run_cfg.get("cli_exe", "litert-lm"),
            extra_args=run_cfg.get("cli_extra_args", []),
            output_filter=run_cfg.get("cli_output_filter", ""),
        )
    raise ValueError(f"Unknown runtime '{runtime}' (use python, cli or fake)")
