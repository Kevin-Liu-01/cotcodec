#!/usr/bin/env bash
# LM2 (D129): collect the text-free records into a staging directory for the repository.
# Copies, per GPU job: the driver's summary and metrics, the active chat template (template text,
# not model output), and the lane's job records; the manifests and their checks; the grading
# rows (text-free) and sandbox verdicts; the dataset receipt and the MathArena aggregates; the
# operator logs and scontrol records. It never copies responses-*.jsonl (model text), server logs,
# code-input.jsonl (program text) or the evaluation files. Writes stage-SHA256SUMS.txt.
# Usage: lm2-stage-evidence.sh <stage dir>
set -Eeuo pipefail
source "$(dirname "$0")/lm2-env.sh"
OUT="${1:?stage dir}"
mkdir -p "$OUT"/{jobs,manifests,grading,data,ops,inspect}
for arm_dir in "$R"/runs/*/; do
  arm=$(basename "$arm_dir")
  for job_dir in "$arm_dir"[0-9]*/; do
    job=$(basename "$job_dir")
    dst="$OUT/jobs/$arm/$job"
    mkdir -p "$dst"
    for f in command.json job.env manifest.json gpu-prolog.env gpu-compute-apps-prolog.csv \
      provenance-verification.txt model-verification.txt container-doctor.txt termination.env \
      resume-receipt.json; do
      [[ -f "$job_dir/$f" ]] && cp "$job_dir/$f" "$dst/"
    done
    if [[ -d "$job_dir/lm2" ]]; then
      for f in "$job_dir"/lm2/summary-*.json "$job_dir"/lm2/metrics-*.jsonl "$job_dir"/lm2/active-chat-template-*.jinja; do
        [[ -f "$f" ]] && cp "$f" "$dst/"
      done
    fi
    [[ -f "$arm_dir/slurm-$job.out" ]] && tail -40 "$arm_dir/slurm-$job.out" > "$dst/slurm-tail.txt"
  done
done
cp "$R"/manifests/*.yaml "$R"/manifests/*.dry-run.json "$R"/manifests/*.test-only.txt "$OUT/manifests/" 2>/dev/null || true
cp "$R"/manifests/*.submit.txt "$OUT/manifests/" 2>/dev/null || true
G="$R/grading"
cp "$G/main/grades.jsonl" "$OUT/grading/grades-budget5120.jsonl"
cp "$G/b4096/grades.jsonl" "$OUT/grading/grades-budget4096.jsonl"
cp "$G/c16k/grades.jsonl" "$OUT/grading/grades-nocap.jsonl"
cp "$G/code-verdicts.jsonl" "$G"/censored-*.jsonl "$OUT/grading/"
cp "$G/early/code-verdicts-early.stderr.txt" "$G/c16k/code-verdicts-new.stderr.txt" "$OUT/grading/" 2>/dev/null || true
cp "$G/sandbox-selftest-verdicts.jsonl" "$G/sandbox-selftest-verdicts.stderr.txt" "$OUT/grading/" 2>/dev/null || true
cp "$R/inspect/sandbox-selftest.jsonl" "$OUT/grading/sandbox-selftest-input.jsonl"
cp "$DATA/receipt.json" "$OUT/data/dataset-receipt.json"
cp "$R/inspect/matharena/matharena-priors.json" "$OUT/data/" 2>/dev/null || true
for m in "$R"/inspect/*.meta.json; do
  python3 - "$m" "$OUT/inspect/$(basename "$m")" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
keep = {k: v for k, v in d["meta"].items() if not k.startswith("tokenizer.ggml.")}
json.dump({"version": d["version"], "tensors": d["tensors"], "meta": keep}, open(sys.argv[2], "w"), indent=1)
PY
done
cp "$R"/ops/jobs.log "$R"/ops/preflight.log "$OUT/ops/" 2>/dev/null || true
cp "$R"/ops/scontrol-*.txt "$OUT/ops/" 2>/dev/null || true
for f in "$R"/ops/slurm-*.out; do tail -60 "$f" > "$OUT/ops/$(basename "$f").tail.txt"; done
(cd "$OUT" && find . -type f ! -name stage-SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > stage-SHA256SUMS.txt)
echo "staged $(wc -l < "$OUT/stage-SHA256SUMS.txt") files"
