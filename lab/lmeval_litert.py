"""lm-evaluation-harness model "litert": generate_until tasks through lab.llm (LiteRT-LM, or fake).

    import lab.lmeval_litert                     # registers the model name "litert" with lm_eval
    lm_eval.simple_evaluate(model="litert", model_args={"key": "gemma-4-e4b"}, tasks=["gsm8k_cot"], limit=50)

model_args: key (catalog key; default config [models.analyst]), runtime (python | fake), backend (gpu | cpu),
max_num_tokens (context window; default config), max_gen_toks (optional cap on every request), seed,
log_path (jsonl with one line per request).

How a request is run:
  - fresh conversation per request, greedy decoding (top_k = 1) and the config [generation] settings;
  - the whole lm_eval context is sent as ONE user message; LiteRT-LM applies the model's own chat template
    (few-shot examples stay inside that message; lm_eval's apply_chat_template is not used);
  - max_gen_toks becomes max_output_tokens, clipped so prompt + answer fit max_num_tokens (prompt length from
    Engine.tokenize when the runtime has it, otherwise chars / 4);
  - `until` stop strings are applied to the finished text (lm_eval's postprocess_generated_text). LiteRT-LM has
    no stop-string option, so generation itself ends at the model's end of turn or max_output_tokens;
  - Qwen3 <think> blocks are removed (config strip_think_tags).
LiteRT-LM exposes no token log-probabilities, so loglikelihood tasks raise NotImplementedError.
"""
from __future__ import annotations

import time
from pathlib import Path

from lm_eval.api.model import LM
from lm_eval.api.registry import register_model
from lm_eval.models.utils import normalize_gen_kwargs, postprocess_generated_text

from lab.common import append_jsonl, load_config, ok, resolve_model, step
from lab.llm import clean_output, make_llm

TEMPLATE_MARGIN = 32  # tokens left free for the chat-template wrapper around the prompt


@register_model("litert")
class LiteRTLM(LM):
    def __init__(self, key: str | None = None, runtime: str = "python", backend: str | None = None,
                 max_num_tokens: int | None = None, max_gen_toks: int | None = None, seed: int = 0,
                 log_path: str | None = None, **_ignored) -> None:
        super().__init__()
        cfg = load_config()
        self.gen = dict(cfg.get("generation", {}))
        self.gen.update(greedy=True, seed=int(seed))
        if max_num_tokens:
            self.gen["max_num_tokens"] = int(max_num_tokens)
        self.key = key or cfg["models"]["analyst"]["key"]
        roles = {m["key"]: m for m in cfg.get("models", {}).values() if isinstance(m, dict) and "key" in m}
        backend = backend or roles.get(self.key, {}).get("backend", "gpu")
        self.cap = int(max_gen_toks) if max_gen_toks else None
        self.log_path = Path(log_path) if log_path else None
        self.stats = {"requests": 0, "clipped": 0, "cut_at_stop": 0, "errors": 0, "seconds": 0.0}
        self.llm = make_llm(runtime, self.key, resolve_model(cfg, self.key), backend, dict(self.gen),
                            cfg.get("run", {}))
        step(f"loading {self.llm.name}")
        self.llm.load()
        ok(f"loaded in {self.llm.load_seconds:.1f}s")

    # ------------------------------------------------------------------ helpers
    def _prompt_tokens(self, text: str) -> int:
        engine = getattr(self.llm, "engine", None)
        if engine is not None and hasattr(engine, "tokenize"):
            try:
                return len(engine.tokenize(text))
            except Exception:  # fall back to the estimate
                pass
        return len(text) // 4

    def close(self) -> None:
        self.llm.close()

    # ------------------------------------------------------------------ lm_eval API
    def generate_until(self, requests, disable_tqdm: bool = False) -> list[str]:
        results = []
        total = len(requests)
        for i, req in enumerate(requests, 1):
            context, gen_kwargs = req.args
            kw = normalize_gen_kwargs(dict(gen_kwargs or {}), default_max_gen_toks=256)
            until = [u for u in kw.get("until", []) if u]
            want = min(kw["max_gen_toks"], self.cap) if self.cap else kw["max_gen_toks"]
            n_prompt = self._prompt_tokens(context)
            room = int(self.gen.get("max_num_tokens", 4096)) - n_prompt - TEMPLATE_MARGIN
            n_out = min(want, room)
            text, err, secs = "", None, 0.0
            if n_out < 1:
                err = f"prompt of {n_prompt} tokens leaves no room in max_num_tokens {self.gen.get('max_num_tokens')}"
            else:
                self.stats["clipped"] += int(n_out < want)
                self.llm.gen["max_output_tokens"] = n_out  # read when the conversation is created
                t = time.time()
                try:
                    raw = self.llm.generate(context)
                    text, _flags = clean_output(raw, self.gen.get("strip_think_tags", True))
                except Exception as e:  # keep going: an empty answer scores 0
                    err = f"{type(e).__name__}: {e}"
                secs = time.time() - t
            answer = postprocess_generated_text(text, until, None)
            self.stats["cut_at_stop"] += int(answer != text)
            self.stats["errors"] += int(err is not None)
            self.stats["requests"] += 1
            self.stats["seconds"] += secs
            self.cache_hook.add_partial("generate_until", req.args, answer)
            results.append(answer)
            if self.log_path:
                append_jsonl(self.log_path, {
                    "task": req.task_name, "doc_id": req.doc_id, "prompt_tokens": n_prompt, "max_gen_toks": want,
                    "max_output_tokens": n_out, "until": until, "seconds": round(secs, 2), "raw": text,
                    "answer": answer, "error": err})
            status = f"ERROR {err}" if err else f"{len(answer.split())} words"
            print(f"[{req.task_name} {i}/{total}] doc {req.doc_id}: {secs:.1f}s, prompt {n_prompt} tok, "
                  f"max_out {n_out}, {status}", flush=True)
        return results

    def loglikelihood(self, requests, disable_tqdm: bool = False):
        raise NotImplementedError("LiteRT-LM gives no token log-probabilities: use generate_until tasks only.")

    def loglikelihood_rolling(self, requests, disable_tqdm: bool = False):
        raise NotImplementedError("LiteRT-LM gives no token log-probabilities: use generate_until tasks only.")
