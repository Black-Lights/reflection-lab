"""Draw the README figures as static SVG (light and dark mode inside each file) from labelled runs.

    python scripts/make_figures.py --matrix runs/matrix_<stamp>/index.json      -> docs/img/grid.svg
    python scripts/make_figures.py --agent                                       -> docs/img/agent.svg
    python scripts/make_figures.py --critics                                     -> docs/img/critics.svg
    python scripts/make_figures.py --cost                                        -> docs/img/cost.svg (needs reports/compute.json)

Colours: the validated categorical pair (slot 1 blue = one model, slot 2 orange = with the loop),
checked with the dataviz validator for both themes. Rows carry direct labels, so colour is never the only cue.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab.common import ROOT, from_root, ok, read_json, read_jsonl  # noqa: E402

STYLE = """<style>
  .bg{fill:#fcfcfb} .t1{fill:#0b0b0b;font:600 15px system-ui,-apple-system,'Segoe UI',sans-serif}
  .t2{fill:#52514e;font:400 12.5px system-ui,-apple-system,'Segoe UI',sans-serif}
  .t3{fill:#52514e;font:500 12px system-ui,-apple-system,'Segoe UI',sans-serif}
  .grid{stroke:#e4e3df;stroke-width:1} .axis{stroke:#b9b8b2;stroke-width:1}
  .s1{fill:#2a78d6} .s2{fill:#eb6834} .link{stroke:#b9b8b2;stroke-width:2} .ring{stroke:#fcfcfb;stroke-width:2}
  @media (prefers-color-scheme: dark){
    .bg{fill:#1a1a19} .t1{fill:#f0efec} .t2,.t3{fill:#c3c2b7} .grid{stroke:#2e2e2c} .axis{stroke:#5a5955}
    .s1{fill:#3987e5} .s2{fill:#d95926} .link{stroke:#5a5955} .ring{stroke:#1a1a19}}
</style>"""
SHORT = {"gemma-4-e4b": "Gemma E4B", "qwen3-4b": "Qwen3 4B", "qwen3-1.7b": "Qwen3 1.7B"}
PNAME = {"prompts": "v1", "prompts_v2": "v2", "prompts_v2_tools": "v2 + tools"}


def grid_rows(index: Path) -> list[dict]:
    from matrix_report import summarise  # noqa: E402
    idx = read_json(index, {})
    rows = []
    for c in idx["configs"]:
        if c not in idx.get("runs", {}):
            continue
        s = summarise(from_root(idx["runs"][c]))
        if not s:
            continue
        parts = list(s["sets"].values())
        g = lambda k, lab: sum(p[k].get(lab, 0) for p in parts)  # noqa: E731
        rows.append({"label": f"{SHORT.get(s['analyst'], s['analyst'])} + {SHORT.get(s['critic'], s['critic'])}",
                     "prompts": PNAME.get(s["prompts"], s["prompts"]), "n": sum(p["n"] for p in parts),
                     "c": (g("base", "c"), g("final", "c")), "h": (g("base", "h"), g("final", "h"))})
    return rows


def dumbbell_panel(x0: int, y0: int, w: int, rows: list[dict], key: str, lo: int, hi: int, title: str, row_h: int) -> list[str]:
    out = [f'<text class="t1" x="{x0}" y="{y0 - 34}">{title}</text>']
    sx = lambda v: x0 + (v - lo) / (hi - lo) * w  # noqa: E731
    step = max(1, (hi - lo) // 5)
    for v in range(lo, hi + 1, step):
        out.append(f'<line class="grid" x1="{sx(v):.1f}" y1="{y0 - 12}" x2="{sx(v):.1f}" y2="{y0 + row_h * len(rows) - 8}"/>')
        out.append(f'<text class="t2" x="{sx(v):.1f}" y="{y0 - 16}" text-anchor="middle">{v}</text>')
    for i, r in enumerate(rows):
        y = y0 + i * row_h + row_h / 2 - 4
        a, b = r[key]
        out.append(f'<line class="link" x1="{sx(a):.1f}" y1="{y:.1f}" x2="{sx(b):.1f}" y2="{y:.1f}"/>')
        for v, cls in ((a, "s1"), (b, "s2")):
            out.append(f'<circle class="{cls} ring" cx="{sx(v):.1f}" cy="{y:.1f}" r="6"><title>{r["label"]} ({r["prompts"]}): '
                       f'{"one model" if cls == "s1" else "with loop"} {v}</title></circle>')
        right = max(a, b)
        out.append(f'<text class="t3" x="{sx(right) + 12:.1f}" y="{y + 4:.1f}">{a} → {b}</text>')
    return out


def draw_grid(index: Path, out: Path) -> None:
    rows = grid_rows(index)
    row_h, top, left = 30, 132, 250
    H = top + row_h * len(rows) + 56
    W = 1000
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="Correct answers and hallucinations out of {rows[0]["n"]} cases, one model versus the critic loop, '
         f'for each analyst and critic pair and prompt version">', STYLE,
         f'<rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="14"/>',
         '<text class="t1" x="24" y="34">One model vs the critic loop, same 104 questions</text>',
         '<circle class="s1" cx="30" cy="56" r="6"/><text class="t2" x="42" y="60">one model (the analyst\'s draft)</text>',
         '<circle class="s2" cx="250" cy="56" r="6"/><text class="t2" x="262" y="60">with the loop (critic + rewrite)</text>']
    for i, r in enumerate(rows):
        y = top + i * row_h + row_h / 2
        L.append(f'<text class="t2" x="24" y="{y:.1f}">{r["label"]}</text>')
        L.append(f'<text class="t3" x="{left - 14}" y="{y:.1f}" text-anchor="end">{r["prompts"]}</text>')
        if i and r["prompts"] != rows[i - 1]["prompts"]:
            L.append(f'<line class="axis" x1="24" y1="{top + i * row_h - 4}" x2="{W - 24}" y2="{top + i * row_h - 4}"/>')
    cmin = min(min(r["c"]) for r in rows)
    lo_c = max(0, (cmin // 10) * 10)
    L += dumbbell_panel(left, top, 330, rows, "c", lo_c, rows[0]["n"], "Correct answers", row_h)
    hmax = max(max(r["h"]) for r in rows)
    L += dumbbell_panel(left + 420, top, 240, rows, "h", 0, max(10, ((hmax + 4) // 5) * 5), "Hallucinations (lower is better)", row_h)
    L.append(f'<text class="t2" x="24" y="{H - 20}">Gemma 4 E4B, Qwen3 4B and Qwen3 1.7B on LiteRT-LM (GPU, greedy). '
             f'v1 and v2 are the prompt versions in prompts/ and prompts_v2/.</text>')
    L.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    ok(f"wrote {out} ({len(rows)} rows)")


AGENT_STYLE = STYLE.replace(".link{", ".s3{fill:#1baf7a} .link{").replace(
    ".s2{fill:#d95926}", ".s2{fill:#d95926} .s3{fill:#199e70}")
MODELS = ["gemma-4-e4b", "qwen3-4b", "qwen3-1.7b"]


def agent_runs() -> dict:
    """{(model, tools): [results]} for the plain agent runs (no verifier)."""
    out = {}
    for d in sorted((ROOT / "runs").glob("agent_2026*")):
        m = read_json(d / "meta.json", {})
        if not m or m.get("verifier") or "fake" in d.name:
            continue
        out[(m["model"], m["tools"])] = read_jsonl(d / "results.jsonl")
    return out


def draw_agent(out: Path) -> None:
    runs = agent_runs()
    levels = [1, 2, 3, 4, 5, 6]
    names = {1: "lookup", 2: "2-step chain", 3: "policy + maths", 4: "conditions", 5: "errors", 6: "long chain"}
    W, H = 1000, 470
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Tool-use benchmark: tasks solved per difficulty level for three models, and totals with 10 or 20 tools">',
         AGENT_STYLE, f'<rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="14"/>',
         '<text class="t1" x="24" y="34">Tool-use benchmark: 30 tasks in a small shop world</text>']
    for i, m in enumerate(MODELS):
        L.append(f'<rect class="s{i + 1}" x="{24 + i * 150}" y="50" width="12" height="12" rx="3"/>'
                 f'<text class="t2" x="{42 + i * 150}" y="60">{SHORT[m]}</text>')
    # panel A: tasks solved per level, 10 shop tools
    x0, y0, ph, gw = 60, 130, 240, 88
    L.append('<text class="t1" x="24" y="96">Solved per level (10 shop tools)</text>')
    for frac in (0, 0.5, 1):
        y = y0 + ph - frac * ph
        L.append(f'<line class="grid" x1="{x0}" y1="{y:.0f}" x2="{x0 + gw * 6}" y2="{y:.0f}"/>'
                 f'<text class="t2" x="{x0 - 8}" y="{y + 4:.0f}" text-anchor="end">{int(frac * 100)}%</text>')
    for j, lv in enumerate(levels):
        gx = x0 + j * gw + 10
        for i, m in enumerate(MODELS):
            rs = [r for r in runs.get((m, "core"), []) if r["level"] == lv]
            if not rs:
                continue
            k, n = sum(r["success"] for r in rs), len(rs)
            h = max(2, ph * k / n)
            bx = gx + i * 23
            L.append(f'<rect class="s{i + 1}" x="{bx}" y="{y0 + ph - h:.1f}" width="20" height="{h:.1f}" rx="4">'
                     f'<title>{SHORT[m]}, level {lv}: {k} of {n}</title></rect>'
                     f'<text class="t3" x="{bx + 10}" y="{y0 + ph - h - 5:.1f}" text-anchor="middle">{k}</text>')
        L.append(f'<text class="t3" x="{gx + 33}" y="{y0 + ph + 18}" text-anchor="middle">L{lv}</text>'
                 f'<text class="t2" x="{gx + 33}" y="{y0 + ph + 34}" text-anchor="middle">{names[lv].split(",")[0]}</text>')
    # panel B: totals with 10 vs 20 tools
    bx0, bw = 640, 300
    L.append(f'<text class="t1" x="{bx0 - 20}" y="96">Total solved: 10 tools → 20 tools</text>')
    for v in (0, 10, 20, 30):
        x = bx0 + v / 30 * bw
        L.append(f'<line class="grid" x1="{x:.0f}" y1="118" x2="{x:.0f}" y2="290"/>'
                 f'<text class="t2" x="{x:.0f}" y="112" text-anchor="middle">{v}</text>')
    for i, m in enumerate(MODELS):
        a = sum(r["success"] for r in runs.get((m, "core"), []))
        b = sum(r["success"] for r in runs.get((m, "all"), []))
        y = 150 + i * 52
        L.append(f'<text class="t2" x="{bx0 - 20}" y="{y - 14}">{SHORT[m]}</text>'
                 f'<line class="link" x1="{bx0 + a / 30 * bw:.1f}" y1="{y}" x2="{bx0 + b / 30 * bw:.1f}" y2="{y}"/>'
                 f'<circle class="s{i + 1} ring" cx="{bx0 + a / 30 * bw:.1f}" cy="{y}" r="6"><title>10 tools: {a}</title></circle>'
                 f'<rect class="s{i + 1} ring" x="{bx0 + b / 30 * bw - 6:.1f}" y="{y - 6}" width="12" height="12" rx="2">'
                 f'<title>20 tools: {b}</title></rect>'
                 f'<text class="t3" x="{bx0 + max(a, b) / 30 * bw + 14:.1f}" y="{y + 4}">{a} → {b}</text>')
    L.append(f'<text class="t2" x="{bx0 - 20}" y="328">circle = 10 shop tools, square = plus 10 distractor tools</text>')
    L.append(f'<text class="t2" x="24" y="{H - 24}">A task counts only if the answer is right, every required call was made with the '
             'right arguments and no forbidden action (such as a refund outside the policy) happened.</text>')
    L.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    ok(f"wrote {out}")


CRITIC_STYLE = AGENT_STYLE.replace(".link{", ".ref{fill:#a3a29b} .link{").replace(
    ".s3{fill:#199e70}", ".s3{fill:#199e70} .ref{fill:#6f6e69}")
# RAGTruth paper (Niu et al., 2024, Table 5, response level, full test set): (label, P, R, F1)
RAGTRUTH_PAPER = [("GPT-4-turbo, prompted", 46.9, 97.9, 63.4), ("GPT-3.5-turbo, prompted", 37.1, 92.3, 52.9),
                  ("SelfCheckGPT, GPT-3.5-turbo", 49.7, 71.9, 58.8), ("LMvLM, GPT-4-turbo", 36.2, 77.8, 49.4),
                  ("Llama-2-13B fine-tuned", 76.9, 80.7, 78.7)]
RAGTRUTH_PREVALENCE = 34.9  # hallucinated share of the 2,700 test responses (943)


def critic_runs() -> list[tuple[str, str, float, float, float]]:
    """[(model, prompts, P_w, R_w, F1_w)] from the newest real run per (critic, prompts)."""
    best = {}
    for d in sorted((ROOT / "runs").glob("bench_ragtruth_*")):
        m = read_json(d / "meta.json", {})
        a = m.get("args", {})
        if not m.get("finished") or a.get("runtime") == "fake" or not (d / "summary.md").exists():
            continue
        for line in (d / "summary.md").read_text(encoding="utf-8").splitlines():
            if line.startswith("| overall |"):
                c = [x.strip() for x in line.strip("|").split("|")]
                best[(a["critic"], a.get("prompts", "prompts"))] = (float(c[6]), float(c[7]), float(c[8]))
    order = [("gemma-4-e4b", "prompts_v2"), ("qwen3-4b", "prompts_v2"), ("qwen3-1.7b", "prompts_v2"), ("qwen3-1.7b", "prompts")]
    return [(k[0], k[1], *best[k]) for k in order if k in best]


def draw_critics(out: Path) -> None:
    ours = critic_runs()
    rows = [(f"{SHORT[m]} ({PNAME.get(p, p)} prompts)", f"s{MODELS.index(m) + 1}", P, R, F) for m, p, P, R, F in ours]
    rows += [(lab, "ref", P, R, F) for lab, P, R, F in RAGTRUTH_PAPER]
    flag = RAGTRUTH_PREVALENCE
    rows.append(("Flag every response", "ref", flag, 100.0, 2 * flag * 100 / (flag + 100)))
    W, rh, top, lx = 1000, 27, 132, 24
    H = top + rh * len(rows) + 24 + 70
    px0, pw, gap = 270, 214, 24
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="RAGTruth: precision, recall and F1 of each critic at spotting hallucinated responses, with the paper baselines">',
         CRITIC_STYLE, f'<rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="14"/>',
         '<text class="t1" x="24" y="34">Can the critic spot a hallucinated answer? (RAGTruth, 300 responses)</text>',
         '<text class="t2" x="24" y="56">Coloured rows: the critics in this project. Grey rows: the RAGTruth paper. '
         'Numbers re-weighted to the full test split.</text>']
    for j, (name, idx) in enumerate((("Precision", 2), ("Recall", 3), ("F1", 4))):
        x0 = px0 + j * (pw + gap)
        L.append(f'<text class="t1" x="{x0}" y="{top - 44}">{name}</text>')
        for v in (0, 50, 100):
            x = x0 + v / 100 * (pw - 34)  # same scale as the bars; 34 px left for the value label
            L.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 16}" x2="{x:.1f}" y2="{top + rh * len(rows)}"/>'
                     f'<text class="t2" x="{x:.1f}" y="{top - 18}" text-anchor="{"start" if v == 0 else "end" if v == 100 else "middle"}">{v}</text>')
        for i, r in enumerate(rows):
            y = top + i * rh + (10 if i >= len(ours) else 0)
            v = r[idx]
            w = max(2.0, v / 100 * (pw - 34))
            L.append(f'<rect class="{r[1]}" x="{x0}" y="{y + 6}" width="{w:.1f}" height="12" rx="4">'
                     f'<title>{r[0]}: {name.lower()} {v:.1f}</title></rect>'
                     f'<text class="t3" x="{x0 + w + 5:.1f}" y="{y + 16}">{v:.0f}</text>')
    for i, r in enumerate(rows):
        y = top + i * rh + (10 if i >= len(ours) else 0)
        L.append(f'<text class="t2" x="{lx}" y="{y + 16}">{r[0]}</text>')
    yb = top + rh * len(rows) + 30
    L.append(f'<text class="t2" x="24" y="{yb}">Positive = hallucinated. A critic that flags everything gets recall 100 and precision '
             f'{flag:.1f}, the share of hallucinated responses; both Qwen3 critics sit there.</text>')
    L.append(f'<text class="t2" x="24" y="{yb + 20}">Sample: 150 hallucinated and 150 clean responses (QA, summaries, data-to-text). '
             'Paper rows: Niu et al. 2024, Table 5, full test set.</text>')
    L.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    ok(f"wrote {out}")


def draw_cost(out: Path) -> None:
    """Model seconds per question, one model vs the loop, per grid configuration (from reports/compute.json)."""
    data = read_json(ROOT / "reports" / "compute.json", {})
    rows = []
    for r in data.get("runs", []):
        st, cfg = r.get("stages"), r.get("config")
        if r.get("category") != "grid" or not st or not cfg or not st["1"][0]:
            continue
        n = st["1"][0]
        one = st["1"][1] / n
        loop = (st["1"][1] + st["2"][1] + st["3"][1] + r["load_s"]) / n
        rows.append({"label": f"{SHORT[cfg['analyst']]}{' + calc' if cfg['tools'] else ''} + {SHORT[cfg['critic']]}",
                     "prompts": PNAME.get(cfg["prompts"], cfg["prompts"]), "one": one, "loop": loop,
                     "rewrites": st["3"][0], "n": n})
    W, rh, top = 1000, 30, 110
    H = top + rh * len(rows) + 70
    x0, pw, hi = 330, 560, 8
    sx = lambda v: x0 + v / hi * pw  # noqa: E731
    L = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Model seconds per question: the analyst alone against the full loop, per configuration">',
         STYLE, f'<rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="14"/>',
         '<text class="t1" x="24" y="34">What the loop costs: model seconds per question</text>',
         f'<circle class="s1" cx="30" cy="56" r="6"/><text class="t2" x="42" y="60">one model (the draft)</text>'
         f'<circle class="s2" cx="210" cy="56" r="6"/><text class="t2" x="222" y="60">loop (draft, audit, rewrite when needed, model loads)</text>']
    for v in range(0, hi + 1, 2):
        L.append(f'<line class="grid" x1="{sx(v):.1f}" y1="{top - 14}" x2="{sx(v):.1f}" y2="{top + rh * len(rows) - 6}"/>'
                 f'<text class="t2" x="{sx(v):.1f}" y="{top - 20}" text-anchor="middle">{v} s</text>')
    for i, r in enumerate(rows):
        y = top + i * rh + rh / 2 - 4
        L.append(f'<text class="t2" x="24" y="{y + 4:.1f}">{r["label"]}</text>'
                 f'<text class="t3" x="{x0 - 16}" y="{y + 4:.1f}" text-anchor="end">{r["prompts"]}</text>'
                 f'<line class="link" x1="{sx(r["one"]):.1f}" y1="{y:.1f}" x2="{sx(r["loop"]):.1f}" y2="{y:.1f}"/>'
                 f'<circle class="s1 ring" cx="{sx(r["one"]):.1f}" cy="{y:.1f}" r="6"><title>one model: {r["one"]:.2f} s</title></circle>'
                 f'<circle class="s2 ring" cx="{sx(r["loop"]):.1f}" cy="{y:.1f}" r="6"><title>loop: {r["loop"]:.2f} s, '
                 f'{r["rewrites"]} rewrites of {r["n"]}</title></circle>'
                 f'<text class="t3" x="{sx(r["loop"]) + 12:.1f}" y="{y + 4:.1f}">{r["loop"] / r["one"]:.1f}x</text>')
    L.append(f'<text class="t2" x="24" y="{H - 30}">104 questions per configuration, one model loaded at a time on a laptop RTX 3060. '
             'The rewrite runs only when the critic reports issues,</text>')
    L.append(f'<text class="t2" x="24" y="{H - 12}">so the cost follows how often the critic objects.</text>')
    L.append("</svg>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    ok(f"wrote {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", help="matrix index.json")
    ap.add_argument("--cost", action="store_true", help="draw docs/img/cost.svg from reports/compute.json")
    ap.add_argument("--agent", action="store_true", help="draw docs/img/agent.svg from runs/agent_*")
    ap.add_argument("--critics", action="store_true", help="draw docs/img/critics.svg from runs/bench_ragtruth_*")
    ap.add_argument("--out", default=str(ROOT / "docs" / "img"))
    args = ap.parse_args()
    if args.matrix:
        draw_grid(Path(args.matrix), Path(args.out) / "grid.svg")
    if args.agent:
        draw_agent(Path(args.out) / "agent.svg")
    if args.critics:
        draw_critics(Path(args.out) / "critics.svg")
    if args.cost:
        draw_cost(Path(args.out) / "cost.svg")


if __name__ == "__main__":
    main()
