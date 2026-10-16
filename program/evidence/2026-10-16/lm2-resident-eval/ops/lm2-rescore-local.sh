#!/usr/bin/env bash
# LM2 (D129) post-check rescoring, CPU only, from text-free files in this evidence directory
# (run from the repository root). No GPU, no host access, no model text.
#   1. Censored rows for every request still running when a job ended, from the per-task tables
#      the server logs give (jobs/<arm>/<job>/server-tasks.jsonl, ops/lm2-parse-server-log.py):
#      ds4 Q2 jobs 1842, 1933, 1955 and UD-IQ3_XXS job 1865. Qwen job 1987 keeps the
#      metrics-based rows (its unfinished math prompts have no completed row to give their
#      length), with the log's minimum n_gen over its 13 unfinished first-wave requests (5,003).
#   2. finalize at 5,120 (primary), 4,096 (with Qwen) and no budget (the 16K completed-only
#      reading): per key, the earliest attempt with a determined outcome counts.
set -Eeuo pipefail
E=program/evidence/2026-10-16/lm2-resident-eval
G=$E/grading
PRE=$G/pre/grades-pre-c16k.jsonl
CAPS=(--cap math=20 --cap code=20 --cap knowledge=20)
LA=(--length-arms v4f-q8 v4f-q2 v4f-iq3)
run() { uv run --locked python scripts/lm2_score.py "$@"; }
mkdir -p "$G/censored"
run censor-tasks --pre "$PRE" --tasks "$E/jobs/v4f-q2/1842/server-tasks.jsonl" --arm v4f-q2 \
  --run-id 20261016T064613Z-1 --job 1842 "${CAPS[@]}" --max-tokens 16384 "${LA[@]}" \
  --out "$G/censored/v4f-q2-1842.jsonl"
run censor-tasks --pre "$PRE" --tasks "$E/jobs/v4f-q2/1933/server-tasks.jsonl" --arm v4f-q2 \
  --run-id 20261016T075553Z-1 --job 1933 "${CAPS[@]}" --max-tokens 16384 "${LA[@]}" \
  --out "$G/censored/v4f-q2-1933.jsonl"
run censor-tasks --pre "$PRE" --tasks "$E/jobs/v4f-q2/1955/server-tasks.jsonl" --arm v4f-q2 \
  --run-id 20261016T081313Z-1 --job 1955 "${CAPS[@]}" --max-tokens 8192 "${LA[@]}" \
  --out "$G/censored/v4f-q2-1955.jsonl"
run censor-tasks --pre "$PRE" --tasks "$E/jobs/v4f-iq3/1865/server-tasks.jsonl" --arm v4f-iq3 \
  --run-id 20261016T065325Z-1 --job 1865 "${CAPS[@]}" --max-tokens 16384 "${LA[@]}" \
  --out "$G/censored/v4f-iq3-1865.jsonl"
# Qwen: its holes inside the determined prefix (3 math, 6 code, 7 knowledge items) are all
# first-wave requests the log shows unfinished (each n_gen >= 5,003).
python3 - "$PRE" "$G/censored/qwen235-q3-1987.jsonl" <<'PY'
import json, sys
pre = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
meta = {r["item_id"]: r for r in pre}
done = {(r["item_id"], r["seed"]) for r in pre if r["arm"] == "qwen235-q3"}
caps = {"math": 3, "code": 6, "knowledge": 7}
out = []
for item, m in sorted(meta.items(), key=lambda kv: (kv[1]["task"], kv[1]["rank"])):
    if m["rank"] >= caps[m["task"]]:
        continue
    for seed in (42, 43, 44):
        if (item, seed) in done:
            continue
        out.append({
            "key": f"qwen235-q3|{m['task']}|{item}|{seed}", "arm": "qwen235-q3", "task": m["task"],
            "item_id": item, "source": m["source"], "seed": seed, "rank": m["rank"],
            "job_id": "20261016T084718Z-1", "slurm_job": "1987", "min_tokens": 5003,
            "completion_tokens": 5003, "max_tokens": 5120, "finish_reason": "length",
            "finish_reason_raw": None, "censored": True, "over_analysis_cap": True,
            "has_final": False, "has_answer": False, "correct": False,
            "final_found": "unfinished_at_job_end", "seed_assignment": "first_wave_all_unfinished",
        })
with open(sys.argv[2], "w") as fh:
    for row in out:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
print(json.dumps({"qwen_censored_rows": len(out)}))
PY
V=$G/code-verdicts.jsonl
CENS=("$G"/censored/*.jsonl)
run finalize --pre "$G/pre/grades-pre-main.jsonl" --verdicts "$V" --censored "${CENS[@]}" \
  --max-rank 20 --analysis-cap 5120 --out "$G/grades-budget5120.jsonl"
run finalize --pre "$G/pre/grades-pre-b4096.jsonl" --verdicts "$V" --censored "${CENS[@]}" \
  --max-rank 20 --analysis-cap 4096 --out "$G/grades-budget4096.jsonl"
run finalize --pre "$G/pre/grades-pre-c16k.jsonl" --verdicts "$V" --max-rank 20 \
  --analysis-cap 1000000 --out "$G/grades-nocap.jsonl"
shasum -a 256 "$G"/grades-*.jsonl "$G"/censored/*.jsonl
