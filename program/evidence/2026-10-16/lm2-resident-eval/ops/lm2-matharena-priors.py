#!/usr/bin/env python3
"""LM2: per-model output-token and accuracy summaries from MathArena's published outputs (priors
for sizing and an external reference; aggregate numbers only, no text). CPU only, host."""
import json, sys, urllib.request
from pathlib import Path
import pyarrow.parquet as pq

SETS = {
    "aime_2026": ("MathArena/aime_2026_outputs", "f916cfc3eebc6ffbbf57d70918e79804d740806f"),
    "hmmt_feb_2026": ("MathArena/hmmt_feb_2026_outputs", None),
}
out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
summary = {}
for name, (repo, rev) in SETS.items():
    if rev is None:
        with urllib.request.urlopen(f"https://huggingface.co/api/datasets/{repo}", timeout=60) as r:
            rev = json.load(r)["sha"]
    dest = out_dir / f"{name}_outputs.parquet"
    if not dest.exists():
        url = f"https://huggingface.co/datasets/{repo}/resolve/{rev}/data/train-00000-of-00001.parquet"
        with urllib.request.urlopen(url, timeout=600) as r, dest.open("wb") as f:
            f.write(r.read())
    t = pq.read_table(dest, columns=["model_name", "model_config", "output_tokens", "correct"]).to_pylist()
    agg = {}
    for row in t:
        k = f"{row['model_config']}"
        a = agg.setdefault(k, {"model_name": row["model_name"], "n": 0, "tok": 0, "correct": 0})
        a["n"] += 1; a["tok"] += int(row["output_tokens"] or 0); a["correct"] += bool(row["correct"])
    summary[name] = {"repo": repo, "revision": rev, "configs": {
        k: {"model_name": v["model_name"], "n": v["n"], "mean_output_tokens": round(v["tok"] / v["n"]),
            "accuracy": round(100 * v["correct"] / v["n"], 1)} for k, v in sorted(agg.items())}}
(out_dir / "matharena-priors.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
for name, s in summary.items():
    for k, v in s["configs"].items():
        low = k.lower()
        if any(w in low for w in ("gpt-oss", "qwen3-235b", "qwen3_235b", "deepseek", "v4")):
            print(name, k, v)
