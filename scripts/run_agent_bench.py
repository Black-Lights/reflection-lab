"""Tool-use (agent) benchmark in the Brightwater Outdoor shop world, with an optional verifier loop.

    python scripts/run_agent_bench.py --model gemma-4-e4b                      30 tasks, 10 shop tools
    python scripts/run_agent_bench.py --model qwen3-4b --tools all             + 10 distractor tools
    python scripts/run_agent_bench.py --model gemma-4-e4b --verifier qwen3-4b  agent, then verifier + rewrite
    python scripts/run_agent_bench.py --model gemma-4-e4b --verifier qwen3-4b --retry   ... + a second tool-using attempt
    python scripts/run_agent_bench.py --model gemma-4-e4b --ids ag18,ag22 --runtime fake

Each task is one conversation with LiteRT-LM automatic tool calling (tools = Python functions from
lab/agent_env.py, every call logged). Scored automatically (see tests/make_agent_tasks.py): answer patterns,
required calls, forbidden actions. With --verifier, a second model audits the answer against the tool log
(prompts_agent/verifier.txt) and, on ISSUES, the agent rewrites its answer from the log (refiner.txt);
it cannot take new actions. Output: runs/agent_<stamp>_<name>/results.jsonl, summary.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.agent_env import SYSTEM, make_tools  # noqa: E402
from lab.common import ROOT, RUNS, console, fail, load_config, ok, read_jsonl, resolve_model, stamp, step, write_json  # noqa: E402
from lab.llm import clean_output  # noqa: E402
from run_experiment import parse_verdict  # noqa: E402  (scripts/run_experiment.py)


# ------------------------------------------------------------------ scoring
def _val_ok(want, got) -> bool:
    if isinstance(want, str) and want.startswith("~"):
        return re.search(want[1:], str(got), re.I) is not None
    if isinstance(want, (int, float)) and not isinstance(want, bool):
        try:
            return abs(float(got) - want) <= 0.011
        except (TypeError, ValueError):
            return False
    return str(got).strip().lower() == str(want).strip().lower()


def call_matches(req: dict, call: dict) -> bool:
    if call["name"] != req["name"]:
        return False
    for k, v in req.get("args", {}).items():
        vals = [call["args"][k]] if k in call["args"] else list(call["args"].values())
        if not any(_val_ok(v, x) for x in vals):
            return False
    return True


def score(task: dict, answer: str, log: list[dict]) -> dict:
    a = answer or ""
    answer_ok = all(any(re.search(p, a, re.I) for p in g) for g in task["expect"]) and \
        not any(re.search(p, a, re.I) for p in task.get("forbid", []))
    missing = [r["name"] for r in task.get("required", []) if not any(call_matches(r, c) for c in log)]
    bad = [c["name"] for c in log if c["name"] in task.get("forbidden", [])
           and not (isinstance(c["result"], dict) and "error" in c["result"])]
    return {"answer_ok": answer_ok, "calls_ok": not missing and not bad, "missing_calls": missing,
            "forbidden_done": bad, "success": answer_ok and not missing and not bad}


def log_text(log: list[dict]) -> str:
    return "\n".join(f"{i}. {c['name']}({json.dumps(c['args'], ensure_ascii=False)}) -> "
                     f"{json.dumps(c['result'], ensure_ascii=False)}" for i, c in enumerate(log, 1)) or "(no tool calls)"


# ------------------------------------------------------------------ models
class Model:
    def __init__(self, key: str, max_tokens: int, fake: bool):
        self.key, self.fake = key, fake
        if fake:
            return
        import litert_lm as L
        self.L = L
        L.set_min_log_severity(L.LogSeverity.ERROR)
        path = resolve_model(load_config(), key)
        if not path or not Path(path).exists():
            raise FileNotFoundError(f"no model file for {key}")
        t = time.time()
        self.engine = L.Engine(str(path), backend=L.Backend.GPU(), max_num_tokens=max_tokens)
        self.engine.__enter__()
        console.print(f"  loaded {key} in {time.time() - t:.1f}s")

    def ask(self, text: str, tools=None, system: str | None = None) -> str:
        if self.fake:
            return "The document does not say."
        L = self.L
        kw = dict(thinking_config=L.ThinkingConfig(enable_thinking=False, thinking_token_budget=0),
                  sampler_config=L.SamplerConfig(top_k=1, seed=0), max_output_tokens=512)
        if tools:
            kw["tools"] = tools
        if system:
            kw["system_message"] = system
        with self.engine.create_conversation(**kw) as conv:
            r = conv.send_message(text)
        content = r.get("content") or []
        return clean_output("".join(c.get("text", "") for c in content if isinstance(c, dict)))[0]

    def close(self):
        if not self.fake:
            self.engine.__exit__(None, None, None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="catalog key of the agent")
    ap.add_argument("--verifier", help="catalog key of the verifier (enables the verify + rewrite loop)")
    ap.add_argument("--retry", action="store_true",
                    help="with --verifier: on ISSUES the agent redoes the task WITH tools (prompts_agent/retry.txt) "
                         "instead of only rewriting its answer")
    ap.add_argument("--tools", choices=["core", "all"], default="core")
    ap.add_argument("--tasks", default=str(ROOT / "tests" / "agent_tasks.jsonl"))
    ap.add_argument("--ids", default="")
    ap.add_argument("--max-num-tokens", type=int, default=4096)
    ap.add_argument("--runtime", choices=["python", "fake"], default="python")
    ap.add_argument("--name", default="")
    args = ap.parse_args()

    started = time.strftime("%Y-%m-%d %H:%M:%S")
    tasks = read_jsonl(Path(args.tasks))
    if args.ids:
        tasks = [t for t in tasks if t["id"] in {x.strip() for x in args.ids.split(",")}]
    fake = args.runtime == "fake"
    name = args.name or f"{args.model}{'+' + args.verifier if args.verifier else ''}-{args.tools}{'-retry' if args.retry else ''}"
    out = RUNS / f"agent_{stamp()}_{name}"
    out.mkdir(parents=True)
    pa = ROOT / "prompts_agent"
    tmpl = {k: (pa / f"{k}.txt").read_text(encoding="utf-8") for k in ("verifier", "refiner")}
    results = []

    step(f"Agent pass: {args.model}, {len(tasks)} tasks, tools={args.tools}")
    m = Model(args.model, args.max_num_tokens, fake)
    for t in tasks:
        tools, log = make_tools(args.tools, t.get("env"))
        t0, err = time.time(), ""
        try:
            ans = m.ask(t["task"], tools=tools, system=SYSTEM)
        except Exception as e:  # context overflow, malformed tool call, ...
            ans, err = "", f"{type(e).__name__}: {str(e)[:200]}"
        sc = score(t, ans, log)
        results.append({"id": t["id"], "level": t["level"], "task": t["task"], "answer": ans, "log": log, "error": err,
                        "seconds": round(time.time() - t0, 2), "n_calls": len(log), **sc})
        mark = "[green]✓[/green]" if sc["success"] else "[red]✗[/red]"
        console.print(f"  {mark} {t['id']} L{t['level']} {len(log)} calls {time.time() - t0:.1f}s  "
                      f"{'' if sc['answer_ok'] else 'answer✗ '}{'missing ' + ','.join(sc['missing_calls']) if sc['missing_calls'] else ''}"
                      f"{' FORBIDDEN ' + ','.join(sc['forbidden_done']) if sc['forbidden_done'] else ''}{' ERR ' + err if err else ''}")
    m.close()

    if args.verifier:
        step(f"Verifier pass: {args.verifier}")
        v = Model(args.verifier, args.max_num_tokens, fake)  # the agent was unloaded above (swap: one model at a time)
        for r in results:
            r["audit"] = v.ask(tmpl["verifier"].replace("{task}", r["task"]).replace("{log}", log_text(r["log"]))
                               .replace("{answer}", r["answer"] or "(no answer)")) if not r["error"] else ""
            r["verdict"] = parse_verdict(r["audit"])[0] if r["audit"] else "SKIPPED"
        v.close()
        step(f"Rewrite pass: {args.model}")
        m = Model(args.model, args.max_num_tokens, fake)
        task_by_id = {t["id"]: t for t in tasks}
        retry_tmpl = (pa / "retry.txt").read_text(encoding="utf-8") if args.retry else ""
        for r in results:
            log_all = r["log"]
            if r["verdict"] == "ISSUES" and args.retry:
                # second tool-using attempt, guided by the audit; actions already done are listed so they are not repeated
                done = [f"{c['name']}({json.dumps(c['args'], ensure_ascii=False)}) -> {json.dumps(c['result'], ensure_ascii=False)}"
                        for c in r["log"] if c["name"] in ("create_refund", "send_email")
                        and not (isinstance(c["result"], dict) and "error" in c["result"])]
                tools2, log2 = make_tools(args.tools, task_by_id[r["id"]].get("env"))
                prompt = (retry_tmpl.replace("{task}", r["task"]).replace("{audit}", r["audit"])
                          .replace("{answer}", r["answer"] or "(no answer)").replace("{done}", "\n".join(done) or "(none)"))
                try:
                    r["final"] = m.ask(prompt, tools=tools2, system=SYSTEM)
                except Exception as e:  # e.g. context window full
                    r["final"], r["retry_error"] = r["answer"], f"{type(e).__name__}: {str(e)[:200]}"
                r["retry_log"] = log2
                log_all = r["log"] + log2
            elif r["verdict"] == "ISSUES":
                r["final"] = m.ask(tmpl["refiner"].replace("{task}", r["task"]).replace("{log}", log_text(r["log"]))
                                   .replace("{answer}", r["answer"] or "(no answer)").replace("{audit}", r["audit"]))
            else:
                r["final"] = r["answer"]
            fs = score(task_by_id[r["id"]], r["final"], log_all)
            r["final_success"], r["final_answer_ok"] = fs["success"], fs["answer_ok"]
        m.close()

    with open(out / "results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    L = [f"# Agent benchmark · {out.name}", "", f"Agent **{args.model}** · tools {args.tools} · verifier "
         f"{args.verifier or '-'} · {len(results)} tasks", "", "| level | n | success | answer ok | calls ok | avg calls |"
         + (" success after verify | fixed | broke |" if args.verifier else ""),
         "|---|---|---|---|---|---|" + ("---|---|---|" if args.verifier else "")]
    for lvl in sorted({r["level"] for r in results}) + ["all"]:
        rs = [r for r in results if lvl == "all" or r["level"] == lvl]
        row = (f"| {lvl} | {len(rs)} | {sum(r['success'] for r in rs)} | {sum(r['answer_ok'] for r in rs)} | "
               f"{sum(r['calls_ok'] for r in rs)} | {sum(r['n_calls'] for r in rs) / len(rs):.1f} |")
        if args.verifier:
            row += (f" {sum(r['final_success'] for r in rs)} | {sum(r['final_success'] and not r['success'] for r in rs)} |"
                    f" {sum(r['success'] and not r['final_success'] for r in rs)} |")
        L.append(row)
    L += ["", "Failed: " + ", ".join(f"{r['id']}" for r in results if not r["success"]),
          f"Errors: {sum(bool(r['error']) for r in results)}"]
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")
    write_json(out / "meta.json", {"model": args.model, "verifier": args.verifier, "tools": args.tools,
                                   "max_num_tokens": args.max_num_tokens, "tasks": args.tasks, "retry": bool(args.retry),
                                   "runtime": args.runtime, "started": started,
                                   "finished": time.strftime("%Y-%m-%d %H:%M:%S")})
    console.print("\n".join(L))
    ok(f"wrote {out}")


if __name__ == "__main__":
    main()
