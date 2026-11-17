"""Build the FACTS Grounding subset used by bench_facts.py: tests/facts_subset.jsonl.

    python scripts/prep_facts.py                 50 examples, seed 0, at most ~3,500 tokens (refuses to overwrite)
    python scripts/prep_facts.py --force         rebuild the file (only before the first real run)

Source: HF dataset google/FACTS-grounding-public, examples.csv (860 public examples; columns
system_instruction, user_request, context_document, full_prompt). Keeps the examples whose
system_instruction + context_document + user_request is at most --max-tokens, estimated as characters / 4
(790 of 860 fit 3,500 on 2026-11-17), then samples --n of them with --seed. Each line keeps the original
row number ("row") so the subset can be traced and rebuilt. No model is used, so there is no --runtime.
Treat the written file like tests/cases.jsonl: frozen once real runs have used it.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.common import ROOT, fail, ok  # noqa: E402

REPO = "google/FACTS-grounding-public"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", "--limit", dest="n", type=int, default=50, help="examples to keep (default 50)")
    ap.add_argument("--seed", type=int, default=0, help="sampling seed (default 0)")
    ap.add_argument("--max-tokens", type=int, default=3500,
                    help="max estimated tokens (chars / 4) of system instruction + document + request (default 3500)")
    ap.add_argument("--out", default=str(ROOT / "tests" / "facts_subset.jsonl"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing subset file")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and not args.force:
        fail(f"{out} already exists. It may already have been used in runs; pass --force to rebuild it.")
        sys.exit(1)

    import pandas as pd
    from huggingface_hub import hf_hub_download

    df = pd.read_csv(hf_hub_download(REPO, "examples.csv", repo_type="dataset"), keep_default_na=False)
    rows = []
    for i, r in enumerate(df.itertuples(index=False)):
        est = (len(r.system_instruction) + len(r.context_document) + len(r.user_request)) // 4
        if est <= args.max_tokens:
            rows.append({"id": f"facts_{i:03d}", "row": i, "est_tokens": est,
                         "system_instruction": r.system_instruction, "user_request": r.user_request,
                         "context_document": r.context_document, "full_prompt": r.full_prompt})
    ok(f"{len(rows)} of {len(df)} examples fit {args.max_tokens} estimated tokens")
    pick = sorted(random.Random(args.seed).sample(range(len(rows)), min(args.n, len(rows))))
    subset = [rows[i] for i in pick]

    import json

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in subset:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    est = [r["est_tokens"] for r in subset]
    ok(f"wrote {len(subset)} examples to {out} (seed {args.seed}; estimated tokens min {min(est)}, "
       f"median {sorted(est)[len(est) // 2]}, max {max(est)})")


if __name__ == "__main__":
    main()
