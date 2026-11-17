"""Blind export of a run for labelling: answers shuffled into A/B exactly like scripts/label.py.
Writes blind_items.md (what the judge reads) and blind_key.json (the A/B mapping; the judge must
not open it until all answer labels are written).

usage: python blind_export.py <run_dir> <cases.jsonl> <out_dir>
"""
import json
import random
import sys
from pathlib import Path

run_dir, cases_file, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
docs = {}
for line in cases_file.read_text(encoding="utf-8").splitlines():
    if line.strip():
        c = json.loads(line)
        docs[c["id"]] = c

md, key = [f"# Blind items · {run_dir.name}", ""], {}
for cid in meta.get("case_ids", list(state)):
    rec = state[cid]
    identical = rec["baseline"].strip() == rec["final"].strip()
    order = ["baseline", "final"]
    random.Random(f"{run_dir.name}:{cid}").shuffle(order)  # same seed as label.py
    key[cid] = {"order": order, "identical": identical}
    md += [f"## {cid} · {rec.get('category', '')}", "",
           "**Document:** " + docs[cid]["document"], "",
           "**Question:** " + rec["question"], "",
           "**Reference:** " + rec["reference"] + (f" (note: {rec['note']})" if rec.get("note") else ""), ""]
    if identical:
        md += ["**Answer (both versions identical):**", "", "> " + rec["baseline"].replace("\n", "\n> "), ""]
    else:
        for letter, which in zip("AB", order):
            md += [f"**Answer {letter}:**", "", "> " + rec[which].replace("\n", "\n> "), ""]
out.mkdir(parents=True, exist_ok=True)
(out / "blind_items.md").write_text("\n".join(md), encoding="utf-8")
(out / "blind_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
print(f"wrote {len(key)} items; identical pairs: {sum(v['identical'] for v in key.values())}")
