"""Run the Analyst → Critic → Refiner experiment with a live view.

    python scripts/run_experiment.py --runtime fake --limit 3     test the pipeline without models
    python scripts/run_experiment.py --limit 2                    smoke test with real models
    python scripts/run_experiment.py                              full run (all cases)
    python scripts/run_experiment.py --resume runs/<folder>       continue an interrupted run

For each test case:
  baseline = Stage 1 output (Analyst alone)       ← the "single model" answer
  audit    = Stage 2 output (Critic reviews the baseline)
  final    = Stage 3 output (Analyst refines using the audit), or the baseline if the critic said OK

Everything is saved as it happens in runs/<timestamp>_<name>/:
  state.json      all results so far (used for --resume)
  transcript.md   human-readable log of every prompt and answer (open it while it runs)
  events.jsonl    one line per model call with timings
  outputs.jsonl   final per-case results (written at the end)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import (  # noqa: E402
    ROOT, RUNS, append_jsonl, console, fail, load_config, ok, read_json, read_jsonl, rel_to_root,
    resolve_model, stamp, warn, write_json,
)
from lab.llm import BaseLLM, clean_output, make_llm  # noqa: E402
from lab.monitor import SysMonitor  # noqa: E402

try:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    print("rich is required for the live view: pip install rich")
    sys.exit(1)

STAGES = {
    1: ("Stage 1 · Analyst draft", "analyst", "analyst.txt"),
    2: ("Stage 2 · Critic audit", "critic", "critic.txt"),
    3: ("Stage 3 · Analyst refine", "analyst", "refiner.txt"),
}
VERDICT_RE = re.compile(r"VERDICT\s*:\s*\**\s*(OK|ISSUES)", re.I)


def fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", v)
    return template


def parse_verdict(audit: str, source: str = "verdict_line") -> tuple[str, int]:
    """Return (verdict, number of tagged issue lines).

    source = "verdict_line": the VERDICT line decides; tagged lines are only counted.
             Qwen3 1.7B writes "VERDICT: OK" and then filler lines such as "[MISSING] ... which is
             addressed in the draft" (every audit in the 2026-11-17 pilot), so letting the lines
             override an explicit OK turned all 30 audits into ISSUES.
    source = "issue_lines": the old rule; any tagged line turns an OK into ISSUES.
    Without a VERDICT line, tagged lines mean ISSUES and no lines mean UNPARSED.
    """
    m = VERDICT_RE.search(audit)
    issues = len(re.findall(r"^\s*[-*•]\s*\[(UNSUPPORTED|WRONG|MISSING)\]", audit, re.M | re.I))
    if m:
        v = m.group(1).upper()
        if source == "issue_lines" and v == "OK" and issues:
            v = "ISSUES"
        return v, issues
    return ("ISSUES" if issues else "UNPARSED"), issues


class LiveView:
    """Everything shown on screen while the run is going."""

    def __init__(self, run_dir: Path, total_cases: int, mon: SysMonitor):
        self.run_dir = run_dir
        self.total = total_cases
        self.mon = mon
        self.stage_title = "Starting"
        self.model = ""
        self.case_label = ""
        self.question = ""
        self.done = 0
        self.todo = 0
        self.stream = ""
        self.status = "loading…"
        self.call_times: list[float] = []
        self.t0 = time.time()
        self.log: list[str] = []

    def on_token(self, piece: str) -> None:
        self.stream += piece

    def note(self, msg: str) -> None:
        self.log.append(time.strftime("%H:%M:%S ") + msg)
        self.log = self.log[-4:]

    def render(self):
        elapsed = time.time() - self.t0
        avg = sum(self.call_times) / len(self.call_times) if self.call_times else 0
        remaining = (self.todo - self.done) * avg if avg else 0
        bar_w = 30
        frac = self.done / self.todo if self.todo else 0
        bar = "█" * int(bar_w * frac) + "░" * (bar_w - int(bar_w * frac))
        head = Text.assemble(
            (f"{self.stage_title}", "bold magenta"), "   model: ", (self.model, "bold"),
            f"\n{bar} {self.done}/{self.todo}   elapsed {elapsed/60:.1f} min",
            f"   avg {avg:.1f}s/call" if avg else "",
            f"   ~{remaining/60:.1f} min left in this stage" if remaining else "",
            f"\nstatus: {self.status}\n", (self.mon.line(), "dim"),
        )
        tail = self.stream[-1600:]
        out_lines = tail.splitlines()[-12:]
        return Group(
            Panel(head, title=f"Reflection Lab · run {self.run_dir.name}", border_style="cyan"),
            Panel(Text(self.question or "-", style="yellow"), title=f"Case {self.case_label}", border_style="yellow"),
            Panel(Text("\n".join(out_lines) or "…"), title="Model output (live)", border_style="green", height=14),
            Panel(Text("\n".join(self.log) or "-", style="dim"), title="Log", border_style="dim"),
        )


def transcript_add(path: Path, case: dict, stage: int, model: str, prompt: str, output: str, secs: float) -> None:
    title = STAGES[stage][0]
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## {case['id']} · {title} · {model} · {secs:.1f}s\n\n")
        f.write(f"**Question:** {case['question']}\n\n")
        f.write("<details><summary>prompt</summary>\n\n```text\n" + prompt + "\n```\n</details>\n\n")
        f.write("```text\n" + output + "\n```\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(ROOT / "tests" / "cases.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="only the first N cases")
    ap.add_argument("--ids", default="", help="comma-separated case ids, e.g. a01,t03")
    ap.add_argument("--runtime", choices=["python", "cli", "fake"], help="override config [run].runtime")
    ap.add_argument("--mode", choices=["swap", "coresident"], help="override config [run].mode")
    ap.add_argument("--analyst", help="catalog key for the analyst (default from config)")
    ap.add_argument("--critic", help="catalog key for the critic (default from config)")
    ap.add_argument("--analyst-backend", choices=["gpu", "cpu"])
    ap.add_argument("--critic-backend", choices=["gpu", "cpu"])
    ap.add_argument("--prompts", default="prompts",
                    help="folder with analyst.txt, critic.txt, refiner.txt (relative to the project), e.g. prompts_v2")
    ap.add_argument("--analyst-tools", action="store_true",
                    help="give the analyst (stages 1 and 3) a calculator and date_add tool; calls go to state.json")
    ap.add_argument("--name", default="", help="label for the run folder")
    ap.add_argument("--resume", default="", help="path of a run folder to continue")
    args = ap.parse_args()

    cfg = load_config()
    run_cfg = dict(cfg.get("run", {}))
    gen = dict(cfg.get("generation", {}))
    runtime = args.runtime or run_cfg.get("runtime", "python")
    mode = args.mode or run_cfg.get("mode", "swap")
    roles = {
        "analyst": {"key": args.analyst or cfg["models"]["analyst"]["key"],
                    "backend": args.analyst_backend or cfg["models"]["analyst"].get("backend", "gpu")},
        "critic": {"key": args.critic or cfg["models"]["critic"]["key"],
                   "backend": args.critic_backend or cfg["models"]["critic"].get("backend", "gpu")},
    }
    for r in roles.values():
        r["path"] = resolve_model(cfg, r["key"])

    # ---------------------------------------------------------------- cases
    cases = read_jsonl(Path(args.cases))
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",")}
        cases = [c for c in cases if c["id"] in wanted]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        fail("No test cases selected.")
        sys.exit(1)

    # ---------------------------------------------------------------- run folder
    if args.resume:
        run_dir = Path(args.resume)
        state = read_json(run_dir / "state.json", {})
        meta = read_json(run_dir / "meta.json", {})
        roles = {k: dict(v) for k, v in meta.get("roles", roles).items()}  # copies: meta must stay JSON
        for r in roles.values():  # a stored path may come from another machine: fall back to the catalog
            p = Path(r["path"]) if r.get("path") else None
            r["path"] = p if p and p.exists() else resolve_model(cfg, r["key"])
        runtime, mode = meta.get("runtime", runtime), meta.get("mode", mode)
        ok(f"Resuming {run_dir}")
    else:
        name = args.name or ("fake" if runtime == "fake" else f"{roles['analyst']['key']}+{roles['critic']['key']}")
        run_dir = RUNS / f"{stamp()}_{name}"
        run_dir.mkdir(parents=True)
        src_prompts = Path(args.prompts) if Path(args.prompts).is_absolute() else ROOT / args.prompts
        if not all((src_prompts / STAGES[s][2]).exists() for s in STAGES):
            fail(f"{src_prompts} must contain {', '.join(STAGES[s][2] for s in STAGES)}")
            sys.exit(1)
        shutil.copytree(src_prompts, run_dir / "prompts")
        shutil.copy(ROOT / "config.toml", run_dir / "config.toml")
        state = {}
        meta = {
            "runtime": runtime, "mode": mode, "generation": gen, "cases_file": rel_to_root(args.cases),
            "prompts": src_prompts.name, "analyst_tools": bool(args.analyst_tools),
            "case_ids": [c["id"] for c in cases], "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "roles": {k: {**v, "path": str(v["path"]) if v["path"] else None} for k, v in roles.items()},
        }
        write_json(run_dir / "meta.json", meta)
        (run_dir / "transcript.md").write_text(f"# Transcript · {run_dir.name}\n", encoding="utf-8")
    (RUNS / "LATEST.txt").write_text(str(run_dir.resolve()), encoding="utf-8")

    prompts_dir = run_dir / "prompts"
    templates = {s: (prompts_dir / STAGES[s][2]).read_text(encoding="utf-8") for s in STAGES}

    if runtime != "fake":
        for role, r in roles.items():
            if not r["path"] or not Path(r["path"]).exists():
                fail(f"No model file for {role} '{r['key']}'. Run scripts/find_models.py and scripts/get_models.py.")
                sys.exit(1)

    console.rule("Reflection Lab · experiment")
    console.print(f"runtime={runtime}  mode={mode}  cases={len(cases)}  folder={run_dir}")
    for role, r in roles.items():
        console.print(f"  {role:<8} {r['key']} on {r['backend']}  ({r['path']})")
    console.print(f"  live transcript: {run_dir / 'transcript.md'}")

    for c in cases:
        state.setdefault(c["id"], {"id": c["id"], "category": c["category"], "question": c["question"],
                                   "reference": c["reference"], "note": c.get("note", ""), "timings": {}})

    def save():
        write_json(run_dir / "state.json", state)

    mon = SysMonitor().start()
    view = LiveView(run_dir, len(cases), mon)
    llms: dict[str, BaseLLM] = {}

    def get_llm(role: str) -> BaseLLM:
        r = roles[role]
        key = f"{r['key']}|{r['backend']}"
        if key in llms:
            return llms[key]
        if mode == "swap":  # free memory before loading another model
            for k in list(llms):
                view.note(f"unloading {k}")
                llms.pop(k).close()
        llm = make_llm(runtime, r["key"], r["path"], r["backend"], gen, run_cfg)
        view.model = llm.name
        view.status = f"loading {llm.name} …"
        view.note(f"loading {llm.name}")
        llm.load()
        view.note(f"loaded in {llm.load_seconds:.1f}s")
        append_jsonl(run_dir / "events.jsonl", {"event": "load", "model": llm.name, "seconds": llm.load_seconds})
        llms[key] = llm
        return llm

    def needs(stage: int, rec: dict) -> bool:
        if stage == 1:
            return "baseline" not in rec
        if stage == 2:
            return "baseline" in rec and "audit" not in rec
        if stage == 3:
            return "audit" in rec and "final" not in rec
        return False

    def do_call(stage: int, case: dict) -> None:
        rec = state[case["id"]]
        title, role, _ = STAGES[stage]
        if stage == 3 and gen.get("skip_refine_if_ok", True) and rec.get("audit_verdict") == "OK":
            rec["final"], rec["refined"] = rec["baseline"], False
            view.note(f"{case['id']}: critic said OK → keep draft")
            view.done += 1
            save()
            return
        llm = get_llm(role)
        prompt = fill(templates[stage], document=case["document"], question=case["question"],
                      draft=rec.get("baseline", ""), audit=rec.get("audit", ""))
        view.stage_title, view.model = title, llm.name
        view.case_label = f"{case['id']} ({case['category']})"
        view.question = case["question"]
        view.stream, view.status = "", "generating…"
        t = time.time()
        use_tools = bool(meta.get("analyst_tools")) and stage in (1, 3)
        try:
            raw = llm.generate(prompt, on_token=view.on_token, **({"tools": True} if use_tools else {}))
            err = None
            if use_tools:
                tl = getattr(llm, "last_tool_log", None) or []
                rec.setdefault("tool_calls", {})[f"stage{stage}"] = tl
                if tl:
                    view.note(f"{case['id']}: {len(tl)} tool call(s)")
                    prompt += "\n\n[tool calls]\n" + "\n".join(
                        f"{c['name']}({c['args']}) -> {c['result']}" for c in tl)
        except Exception as e:  # keep going; record the error
            raw, err = "", f"{type(e).__name__}: {e}"
            view.note(f"{case['id']}: ERROR {err}")
            append_jsonl(run_dir / "events.jsonl", {"event": "error", "case": case["id"], "stage": stage,
                                                    "error": err, "trace": traceback.format_exc()})
        secs = time.time() - t
        text, flags = clean_output(raw, gen.get("strip_think_tags", True))
        if not view.stream:
            view.stream = text
        view.call_times.append(secs)
        rec["timings"][f"stage{stage}"] = round(secs, 2)
        if flags:
            rec.setdefault("flags", {}).update(flags)
        transcript_add(run_dir / "transcript.md", case, stage, llm.name, prompt, raw or f"[ERROR] {err}", secs)
        view.done += 1
        if err:
            # Leave the field unset so --resume retries it; later stages skip this case.
            rec.setdefault("errors", {})[f"stage{stage}"] = err
            append_jsonl(run_dir / "events.jsonl", {"event": "call", "case": case["id"], "stage": stage,
                                                    "model": llm.name, "seconds": round(secs, 2), "error": err})
            save()
            return
        rec.get("errors", {}).pop(f"stage{stage}", None)
        if stage == 1:
            rec["baseline"] = text
            rec["models_analyst"] = llm.name
        elif stage == 2:
            rec["audit"] = text
            rec["audit_verdict"], rec["audit_issues"] = parse_verdict(text, gen.get("verdict_source", "verdict_line"))
            rec["audit_ok_with_lines"] = bool(VERDICT_RE.search(text)) and rec["audit_verdict"] == "OK" \
                and rec["audit_issues"] > 0  # critic said OK but still listed tagged lines
            rec["models_critic"] = llm.name
            view.note(f"{case['id']}: verdict {rec['audit_verdict']} ({rec['audit_issues']} issues)")
        else:
            rec["final"], rec["refined"] = text, True
        append_jsonl(run_dir / "events.jsonl", {"event": "call", "case": case["id"], "stage": stage,
                                                "model": llm.name, "seconds": round(secs, 2), "chars": len(raw)})
        save()

    interrupted = False
    try:
        with Live(get_renderable=view.render, console=console, refresh_per_second=8, screen=False):
            if mode == "swap":
                for stage in (1, 2, 3):
                    todo = [c for c in cases if needs(stage, state[c["id"]])]
                    view.stage_title, view.done, view.todo, view.call_times = STAGES[stage][0], 0, len(todo), []
                    for c in todo:
                        do_call(stage, c)
            else:
                fields = {1: "baseline", 2: "audit", 3: "final"}
                view.done = 0
                view.todo = sum(1 for c in cases for f in fields.values() if f not in state[c["id"]])
                view.stage_title = "All stages, case by case" 
                for c in cases:
                    for stage in (1, 2, 3):
                        if needs(stage, state[c["id"]]):
                            do_call(stage, c)
            view.status = "finished"
    except KeyboardInterrupt:
        interrupted = True
    except Exception as e:  # e.g. model failed to load on this backend
        for llm in llms.values():
            llm.close()
        llms.clear()
        mon.stop()
        save()
        append_jsonl(run_dir / "events.jsonl", {"event": "fatal", "error": f"{type(e).__name__}: {e}",
                                                "trace": traceback.format_exc()})
        console.print(traceback.format_exc())
        fail(f"Stopped: {type(e).__name__}: {e}")
        console.print("Hints: if a model failed to load on the GPU, retry with --analyst-backend cpu or "
                      "--critic-backend cpu. If it says out of memory, close other GPU apps or use mode=swap. "
                      f"Continue later with: --resume \"{run_dir}\"")
        sys.exit(1)
    finally:
        for llm in llms.values():
            llm.close()
        mon.stop()
        save()

    if interrupted:
        warn(f"Interrupted. Continue with: python scripts/run_experiment.py --resume \"{run_dir}\"")
        return

    # ---------------------------------------------------------------- outputs
    rows = [state[c["id"]] for c in cases]
    with open(run_dir / "outputs.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["peak_vram_mb"] = mon.peak_vram_mb
    meta["peak_ram_used_gb"] = round(mon.peak_ram_used_gb, 2)
    write_json(run_dir / "meta.json", meta)

    verdicts = {}
    for r in rows:
        verdicts[r.get("audit_verdict", "?")] = verdicts.get(r.get("audit_verdict", "?"), 0) + 1
    errors = sum(1 for r in rows if r.get("errors"))
    if errors:
        warn(f"{errors} case(s) had errors (see events.jsonl). Retry them with --resume \"{run_dir}\"")
    changed = sum(1 for r in rows if r.get("refined"))
    console.rule("Done")
    ok(f"{len(rows)} cases · critic verdicts {verdicts} · refined {changed} · errors {errors}")
    if meta.get("peak_vram_mb"):
        console.print(f"Peak VRAM {meta['peak_vram_mb']/1024:.1f} GB · peak RAM used {meta['peak_ram_used_gb']} GB")
    console.print(f"Results: {run_dir}")
    console.print("Next: [bold]python scripts/label.py[/bold] (blind-label the answers), then "
                  "[bold]python scripts/report.py[/bold]")


if __name__ == "__main__":
    main()
