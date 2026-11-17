"""Merge blind A/B answer labels and critic judgments into <run>/labels.jsonl (label.py format).
Refuses to touch an existing non-empty labels.jsonl.

usage: python merge_labels.py <run_dir> <labelling_dir> <labeller>
"""
import json
import sys
from pathlib import Path

run_dir, d, labeller = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
out = run_dir / "labels.jsonl"
if out.exists() and out.read_text(encoding="utf-8").strip():
    sys.exit(f"{out} already has labels; not overwriting")
key = json.loads((d / "blind_key.json").read_text(encoding="utf-8"))
ans = json.loads((d / "answer_labels.json").read_text(encoding="utf-8"))
cri = json.loads((d / "critic_labels.json").read_text(encoding="utf-8"))
meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
assert set(key) == set(ans) == set(cri), "label files do not cover the same cases"
lines = []
for cid in meta["case_ids"]:
    k, a, c = key[cid], ans[cid], cri[cid]
    if k["identical"]:
        labels = {"baseline": a["single"], "final": a["single"]}
    else:
        labels = {k["order"][0]: a["A"], k["order"][1]: a["B"]}
    comment = " | ".join(x for x in (a.get("comment", ""), ("critic: " + c["comment"]) if c.get("comment") else "") if x)
    lines.append(json.dumps({"id": cid, "labels": labels, "order": k["order"], "identical": k["identical"],
                             "critic": c["critic"], "comment": comment, "labeller": labeller},
                            ensure_ascii=False))
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(lines)} labels to {out}")
