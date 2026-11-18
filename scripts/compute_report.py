"""Time and compute used by every run: wall time, model time, calls, GPU energy, and the Claude session.

    python scripts/compute_report.py                 -> reports/compute.md + reports/compute.json
    python scripts/compute_report.py --no-claude     skip the Claude Code session totals
    python scripts/compute_report.py --claude-dir DIR   transcripts folder (default ~/.claude/projects/<this project>)

Sources, all already written by the scripts:
- run_experiment folders (meta.json started/finished, events.jsonl load + call seconds and output characters),
- agent_* folders (meta.json, results.jsonl seconds per task; older runs: folder stamp to summary.md time),
- bench_* folders (meta.json started/finished, calls.jsonl seconds per call),
- runs/compute/*.csv from scripts/compute_logger.py (GPU power every few seconds). A run whose time window is
  at least 80 % covered by samples gets MEASURED energy (mean power x wall time); any other run gets an
  ESTIMATE (wall time x the mean power of the measured runs). GPU board power only: CPU, screen and the
  rest of the laptop are not included.
- Claude Code transcripts (*.jsonl, subagents included): API responses, tokens, tool calls, active time.
Runs with the fake runtime are listed but left out of the totals; matrix_* and queue_* folders only group runs.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import ROOT, RUNS, console, ok, write_json  # noqa: E402

TS = "%Y-%m-%d %H:%M:%S"
CATEGORY = {"dev": "Development (smoke, pilots, checks)", "grid": "Grid (analyst x critic x prompts, 104 questions)",
            "agent": "Agent benchmark (30 tool-use tasks)", "lmeval": "lm-evaluation-harness",
            "ragtruth": "RAGTruth (critic detection)", "hhem": "HHEM leaderboard documents",
            "facts": "FACTS Grounding subset"}


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in (TS, "%Y%m%d-%H%M%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _jsonl(p: Path):
    if not p.exists():
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _meta(d: Path) -> dict:
    try:
        return json.loads((d / "meta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _last_mtime(d: Path) -> datetime:
    return datetime.fromtimestamp(max(p.stat().st_mtime for p in d.rglob("*") if p.is_file()))


def _model(name: str) -> str:
    return re.sub(r"\s*\[.*\]$", "", name or "?")


# ------------------------------------------------------------------ runs
def collect_runs() -> list[dict]:
    runs = []
    for d in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        n = d.name
        if n.startswith(("matrix_", "queue_")) or n == "compute":
            continue
        m = _meta(d)
        r = {"name": n, "calls": 0, "call_s": 0.0, "loads": 0, "load_s": 0.0, "out_chars": 0,
             "by_model": defaultdict(lambda: {"calls": 0, "call_s": 0.0, "loads": 0, "load_s": 0.0, "out_chars": 0}),
             "peak_vram_mb": m.get("peak_vram_mb"), "peak_ram_gb": m.get("peak_ram_used_gb")}
        if n.startswith("agent_"):
            st = re.match(r"agent_(\d{8}-\d{6})_(.*)", n)
            r.update(category="agent", fake=m.get("runtime") == "fake" or "fake" in n,
                     start=_dt(m.get("started")) or _dt(st.group(1)),
                     end=_dt(m.get("finished")) or (datetime.fromtimestamp((d / "summary.md").stat().st_mtime)
                                                    if (d / "summary.md").exists() else None))
            for row in _jsonl(d / "results.jsonl"):
                bm = r["by_model"][m.get("model", "?")]
                bm["calls"] += 1
                bm["call_s"] += row.get("seconds", 0.0)
                bm["out_chars"] += len(row.get("answer") or "")
        elif n.startswith("bench_"):
            kind = n.split("_")[1]
            args = m.get("args", {})
            r.update(category=kind, fake=args.get("runtime") == "fake", start=_dt(m.get("started")),
                     end=_dt(m.get("finished")))
            for row in _jsonl(d / "calls.jsonl"):
                bm = r["by_model"][_model(row.get("model") or args.get("model") or args.get("critic"))]
                bm["calls"] += 1
                bm["call_s"] += row.get("seconds", 0.0)
                bm["out_chars"] += len(row.get("output") or row.get("raw") or "")
        elif re.match(r"\d{8}-\d{6}_", n):
            r.update(category="grid" if n.split("_", 1)[1].startswith("mx-") else "dev",
                     fake=m.get("runtime") == "fake", start=_dt(m.get("started")) or _dt(n[:15]),
                     end=_dt(m.get("finished")))
            r["stages"] = {1: [0, 0.0], 2: [0, 0.0], 3: [0, 0.0]}
            roles = m.get("roles") or {}
            r["config"] = {"analyst": (roles.get("analyst") or {}).get("key"), "critic": (roles.get("critic") or {}).get("key"),
                           "prompts": m.get("prompts", "prompts"), "tools": bool(m.get("analyst_tools"))}
            for ev in _jsonl(d / "events.jsonl"):
                if ev.get("event") == "call":
                    if ev.get("stage") in (1, 2, 3):
                        r["stages"][ev["stage"]][0] += 1
                        r["stages"][ev["stage"]][1] += ev.get("seconds", 0.0)
                    bm = r["by_model"][_model(ev.get("model"))]
                    bm["calls"] += 1
                    bm["call_s"] += ev.get("seconds", 0.0)
                    bm["out_chars"] += ev.get("chars", 0)
                elif ev.get("event") == "load":
                    bm = r["by_model"][_model(ev.get("model"))]
                    bm["loads"] += 1
                    bm["load_s"] += ev.get("seconds", 0.0)
        else:
            continue
        r["finished"] = r["end"] is not None
        if r["end"] is None:  # still running or interrupted: last file write
            r["end"] = _last_mtime(d)
        if r["start"] is None:
            continue
        for bm in r["by_model"].values():
            for k in ("calls", "call_s", "loads", "load_s", "out_chars"):
                r[k] += bm[k]
        r["wall_s"] = max(0.0, (r["end"] - r["start"]).total_seconds())
        r["by_model"] = {k: dict(v) for k, v in r["by_model"].items()}
        runs.append(r)
    return runs


# ------------------------------------------------------------------ energy
def load_samples() -> list[tuple[datetime, float]]:
    out = []
    for p in sorted((RUNS / "compute").glob("*.csv")) if (RUNS / "compute").exists() else []:
        with open(p, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t, w = _dt(row.get("time")), row.get("gpu_power_w")
                if t and w:
                    try:
                        out.append((t, float(w)))
                    except ValueError:
                        pass
    return sorted(out)


def add_energy(runs: list[dict], samples: list[tuple[datetime, float]]) -> dict:
    gaps = sorted((b[0] - a[0]).total_seconds() for a, b in zip(samples, samples[1:]))
    step = gaps[len(gaps) // 2] if gaps else 5.0
    for r in runs:
        inside = [w for t, w in samples if r["start"] <= t <= r["end"]]
        r["coverage"] = min(1.0, len(inside) * step / r["wall_s"]) if r["wall_s"] else 0.0
        if inside and r["coverage"] >= 0.8:
            r["mean_power_w"] = sum(inside) / len(inside)
            r["energy_wh"], r["energy_kind"] = r["mean_power_w"] * r["wall_s"] / 3600, "measured"
    measured = [r for r in runs if r.get("energy_kind") == "measured" and not r["fake"]]
    if measured:
        p_ref = sum(r["energy_wh"] for r in measured) * 3600 / sum(r["wall_s"] for r in measured)
    else:
        busy = [w for _, w in samples if w > 20]  # no finished measured run yet: mean of loaded samples
        p_ref = sum(busy) / len(busy) if busy else None
    for r in runs:
        if r.get("energy_kind") != "measured":
            r["energy_wh"] = p_ref * r["wall_s"] / 3600 if p_ref else None
            r["energy_kind"] = "estimated" if p_ref else "none"
    return {"reference_power_w": p_ref, "sample_step_s": step, "n_samples": len(samples),
            "samples_from": samples[0][0].strftime(TS) if samples else None,
            "samples_to": samples[-1][0].strftime(TS) if samples else None}


# ------------------------------------------------------------------ Claude session
KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def claude_usage(folder: Path) -> dict | None:
    files = sorted(folder.glob("*.jsonl")) + sorted(folder.glob("*/subagents/*.jsonl"))
    if not files:
        return None

    def one(paths: list[Path]) -> dict:
        usage, tot = {}, defaultdict(int)
        models, times = defaultdict(int), []
        for p in paths:
            for row in _jsonl(p):
                ts = row.get("timestamp")
                if ts:
                    try:
                        times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                    except ValueError:
                        pass
                msg = row.get("message") if row.get("type") == "assistant" else None
                if not isinstance(msg, dict):
                    continue
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        tot["tool_calls"] += 1
                mid = msg.get("id") or row.get("requestId")
                u = msg.get("usage")
                if not u or not mid or msg.get("model") == "<synthetic>":
                    continue
                prev = usage.setdefault(mid, {"model": msg.get("model", "?")})
                for k in KEYS:
                    prev[k] = max(prev.get(k, 0), int(u.get(k) or 0))
        for u in usage.values():
            tot["responses"] += 1
            models[u["model"]] += 1
            for k in KEYS:
                tot[k] += u[k]
        times.sort()
        active = sum(min((b - a).total_seconds(), 300) for a, b in zip(times, times[1:]))  # gaps over 5 min = idle
        span = (times[-1] - times[0]).total_seconds() if len(times) > 1 else 0
        return {**tot, "models": dict(models), "active_h": active / 3600, "span_h": span / 3600,
                "first": times[0].astimezone().strftime(TS) if times else None,
                "last": times[-1].astimezone().strftime(TS) if times else None}

    main_files = [p for p in files if p.parent == folder]
    sub_files = [p for p in files if p.parent != folder]
    return {"main": one(main_files), "subagents": one(sub_files) if sub_files else None,
            "n_sessions": len(main_files), "n_subagents": len(sub_files)}


# ------------------------------------------------------------------ report
def h(s: float) -> str:
    return f"{s / 3600:.2f} h" if s >= 3600 else f"{s / 60:.1f} min"


def wh(x) -> str:
    return "-" if x is None else f"{x:.0f} Wh"


def tok(n: int) -> str:
    return f"{n / 1e6:.2f} M" if n >= 1e6 else f"{n / 1e3:.1f} k"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-claude", action="store_true")
    ap.add_argument("--claude-dir", default="")
    ap.add_argument("--out", default=str(ROOT / "reports" / "compute.md"))
    args = ap.parse_args()

    runs = collect_runs()
    energy = add_energy(runs, load_samples())
    real = [r for r in runs if not r["fake"]]
    claude = None
    if not args.no_claude:
        cdir = Path(args.claude_dir) if args.claude_dir else \
            Path.home() / ".claude" / "projects" / re.sub(r"[:\\/]", "-", str(ROOT))
        claude = claude_usage(cdir) if cdir.exists() else None

    L = [f"# Time and compute", "", f"Generated {datetime.now():%Y-%m-%d %H:%M} by `scripts/compute_report.py`. "
         "Every model run used one laptop GPU (one model loaded at a time), so GPU time equals the runs' wall time.", ""]
    if real:
        t0, t1 = min(r["start"] for r in real), max(r["end"] for r in real)
        e_m = sum(r["energy_wh"] for r in real if r["energy_kind"] == "measured")
        e_e = sum(r["energy_wh"] or 0 for r in real if r["energy_kind"] == "estimated")
        n_m = sum(r["energy_kind"] == "measured" for r in real)
        L += ["## Totals", "", "| | |", "|---|---|",
              f"| Period | {t0:%d %b %H:%M} to {t1:%d %b %H:%M} ({h((t1 - t0).total_seconds())} elapsed) |",
              f"| Runs with real models | {len(real)} ({sum(not r['finished'] for r in real)} unfinished or running) |",
              f"| GPU wall time | {h(sum(r['wall_s'] for r in real))} |",
              f"| Time inside model calls | {h(sum(r['call_s'] for r in real))} over {sum(r['calls'] for r in real):,} calls |",
              f"| Model loads (grid and pilots) | {sum(r['loads'] for r in real)} loads, {h(sum(r['load_s'] for r in real))} |",
              f"| Text generated | {sum(r['out_chars'] for r in real) / 1e6:.2f} M characters (roughly {sum(r['out_chars'] for r in real) / 4e6:.2f} M tokens) |",
              f"| GPU energy | {(e_m + e_e) / 1000:.2f} kWh ({e_m / 1000:.2f} measured over {n_m} runs, {e_e / 1000:.2f} estimated) |",
              f"| Peak VRAM / RAM in a run | {max((r['peak_vram_mb'] or 0) for r in real) / 1024:.1f} GB / "
              f"{max((r['peak_ram_gb'] or 0) for r in real):.1f} GB |", ""]
        if energy["reference_power_w"]:
            L += [f"Energy estimates use {energy['reference_power_w']:.0f} W, the mean GPU board power over the measured "
                  f"runs ({energy['n_samples']:,} samples every {energy['sample_step_s']:.0f} s, from "
                  f"{energy['samples_from']}). Runs before the power logger started are estimates.", ""]

        L += ["## By experiment", "", "| Experiment | Runs | GPU wall time | Model calls | Time in calls | Mean s per call | GPU energy |",
              "|---|---|---|---|---|---|---|"]
        for cat in CATEGORY:
            rs = [r for r in real if r["category"] == cat]
            if not rs:
                continue
            calls, cs = sum(r["calls"] for r in rs), sum(r["call_s"] for r in rs)
            ew = [r["energy_wh"] for r in rs if r["energy_wh"] is not None]
            kinds = {r["energy_kind"] for r in rs}
            L.append(f"| {CATEGORY[cat]} | {len(rs)} | {h(sum(r['wall_s'] for r in rs))} | {calls:,} | {h(cs)} | "
                     f"{cs / calls if calls else 0:.2f} | {wh(sum(ew) if ew else None)}"
                     f"{'' if kinds == {'measured'} else ' (est.)' if kinds == {'estimated'} else ' (part est.)'} |")
        L.append("")

        bym = defaultdict(lambda: defaultdict(float))
        for r in real:
            for k, v in r["by_model"].items():
                for f2, x in v.items():
                    bym[k][f2] += x
        L += ["## By model", "", "| Model | Calls | Time in calls | Mean s per call | Characters out | Loads | Load time |",
              "|---|---|---|---|---|---|---|"]
        for k, v in sorted(bym.items(), key=lambda kv: -kv[1]["call_s"]):
            L.append(f"| {k} | {int(v['calls']):,} | {h(v['call_s'])} | {v['call_s'] / v['calls'] if v['calls'] else 0:.2f} | "
                     f"{int(v['out_chars']):,} | {int(v['loads'])} | {h(v['load_s'])} |")
        L += ["", "Agent runs count the agent's first pass per task; verifier and rewrite time is in the wall time only.", ""]

        grid = [r for r in real if r["category"] == "grid" and r.get("stages") and r["stages"][1][0]]
        if grid:
            L += ["## What the loop costs (grid runs)", "",
                  "Seconds of model time per question. One model = the analyst's draft only; loop = draft + audit + "
                  "rewrite (the rewrite is skipped when the critic says OK) + model loads (swap mode reloads per stage).", "",
                  "| Analyst | Critic | Prompts | Questions | One model, s | Critic, s | Refiner, s | Loads, s | Loop, s | Loop / one model | Rewrites |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
            for r in grid:
                n = r["stages"][1][0]
                s1, s2, s3 = (r["stages"][i][1] / n for i in (1, 2, 3))
                ld = r["load_s"] / n
                cfg = r["config"]
                L.append(f"| {cfg['analyst']}{' + tools' if cfg['tools'] else ''} | {cfg['critic']} | {cfg['prompts']} | {n} | "
                         f"{s1:.2f} | {s2:.2f} | {s3:.2f} | {ld:.2f} | {s1 + s2 + s3 + ld:.2f} | "
                         f"{(s1 + s2 + s3 + ld) / s1 if s1 else 0:.1f}x | {r['stages'][3][0]} |")
            L.append("")

    if claude:
        c, s = claude["main"], claude["subagents"]
        L += ["## Claude Code (the assistant that built and ran all this)", "",
              "| | Main session | Subagents |", "|---|---|---|",
              f"| Sessions / agents | {claude['n_sessions']} | {claude['n_subagents']} |",
              f"| First to last message | {c['first']} to {c['last']} ({c['span_h']:.1f} h) | |",
              f"| Active time (gaps over 5 min left out) | {c['active_h']:.1f} h | {s['active_h']:.1f} h |" if s else
              f"| Active time (gaps over 5 min left out) | {c['active_h']:.1f} h | - |",
              f"| API responses | {c['responses']:,} | {s['responses']:,} |" if s else f"| API responses | {c['responses']:,} | - |",
              f"| Tool calls | {c['tool_calls']:,} | {s['tool_calls']:,} |" if s else f"| Tool calls | {c['tool_calls']:,} | - |"]
        for k, label in (("input_tokens", "Input tokens (uncached)"), ("cache_creation_input_tokens", "Input tokens written to cache"),
                         ("cache_read_input_tokens", "Input tokens read from cache"), ("output_tokens", "Output tokens")):
            L.append(f"| {label} | {tok(c[k])} | {tok(s[k]) if s else '-'} |")
        mc = defaultdict(int)
        for part in (c, s or {"models": {}}):
            for m2, n2 in part["models"].items():
                mc[m2] += n2
        L += ["", "Models: " + ", ".join(f"{m2} ({n2} responses)" for m2, n2 in mc.items()) + ".", ""]

    L += ["## Every run", "", "| Run | Experiment | Start | Wall time | Calls | GPU energy | |", "|---|---|---|---|---|---|---|"]
    for r in runs:
        L.append(f"| {r['name']} | {r['category']} | {r['start']:%d %b %H:%M} | {h(r['wall_s'])} | {r['calls']:,} | "
                 f"{'-' if r['fake'] else wh(r['energy_wh'])}{' (est.)' if r['energy_kind'] == 'estimated' and not r['fake'] else ''} | "
                 f"{'fake runtime' if r['fake'] else '' if r['finished'] else 'unfinished or running'} |")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    write_json(out.with_suffix(".json"), {"energy": energy, "claude": claude, "runs": [
        {**{k: v for k, v in r.items() if k not in ("start", "end")}, "start": r["start"].strftime(TS),
         "end": r["end"].strftime(TS)} for r in runs]})
    console.print("\n".join(L[:40]))
    ok(f"wrote {out} and {out.with_suffix('.json').name}")


if __name__ == "__main__":
    main()
