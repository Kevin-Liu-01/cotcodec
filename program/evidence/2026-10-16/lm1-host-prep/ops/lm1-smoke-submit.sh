#!/usr/bin/env bash
# LM1 host prep: render the smoke test's lane manifest (4 H100s, 14-minute limit = 0.933 GPU-h
# cap; the overlay image of commit $1; gpt-oss-120b-mxfp4-gguf as the lane's pinned model, whose
# full snapshot the lane re-hashes in the container), dry-run and test-only it through the lane's
# submitter from the checkout of that commit, then, with "submit", record the queue and the GPUs
# and submit it. Submission is refused unless the other project's job holds physical GPU 0 (so
# Slurm cannot hand it to this job) and four other GPUs are free; the driver also refuses GPU 0's
# UUID (experiments/lm1/lm1-host-smoke-v1.json).
# Usage: lm1-smoke-submit.sh <commit short id> [check|submit]
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
S="${1:?commit short id}"; MODE="${2:-check}"
CO="$R/checkout"
B="$R/builds/llamacpp-overlay-$S"
A="$R/capsule/source-$S.tar.gz"
M="$R/manifests/smoke-$S.yaml"
mkdir -p "$R/manifests" "$R/runs"
cd "$CO"
[[ -z "$(git status --porcelain)" && "$(git rev-parse --short=8 HEAD)" == "$S" ]] || { echo "checkout is not a clean $S"; exit 2; }
IMAGE=$(tr -d ' \n' < "$B/image-id.txt")
[[ "$IMAGE" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "no overlay image id"; exit 2; }
python3 - "$B" "$IMAGE" "$(sha256sum "$A" | cut -d' ' -f1)" "$(git rev-parse HEAD)" <<'PY'
import json, sys
b, image, capsule, git = sys.argv[1:]
prov = json.load(open(f"{b}/provenance-verification.json"))
rec = json.load(open(f"{b}/build-receipt.json"))
checks = {
    "provenance PASS": prov.get("status") == "PASS",
    "provenance commit": prov.get("git_sha") == git,
    "provenance capsule": prov.get("source_sha256") == capsule,
    "receipt image": rec.get("overlay_image_id") == image,
    "receipt commit": rec.get("git_sha") == git,
    "llama.cpp commit": rec.get("llama_cpp_commit") == "620d2225cc436ab0b001e3200e590e3b286ef9ab",
}
bad = [k for k, ok in checks.items() if not ok]
if bad:
    sys.exit(f"overlay build record fails: {bad}")
PY
MID=gpt-oss-120b-mxfp4-gguf
REC="$RECEIPTS/$MID.json"
REV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['revision'])" "$REC")
ROOT=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['artifact_root_sha256'])" "$REC")
PLAN=experiments/lm1/lm1-host-smoke-v1.json
cat > "$M" <<YAML
# LM1 host prep (D125) smoke test: every GGUF candidate in stock llama.cpp b11669 on 4 H100s
# (layer split, all layers on GPU); one greedy prefill, decode and chat request each.
# Slurm limit 14 min x 4 H100 = 0.933 GPU-h cap; the driver stops starting models about 10 min in
# (the lane sends USR1 180 s before the limit).
runtime: docker-single-node-discovery-v1
name: lm1-host-smoke
image_id: $IMAGE
git_sha: "$(git rev-parse HEAD)"
source_sha256: "$(sha256sum "$A" | cut -d' ' -f1)"
run_root: $R/runs/smoke
resources:
  gpu_type: h100
  gpus: 4
  cpus: 32
  memory_gb: 128
  minutes: 14
budget:
  max_gpu_hours: 0.94
randomness_contract: deterministic
seeds: []
model:
  cache_host_path: $C
  model_id: $MID
  revision: "$REV"
  receipt_sha256: "$(sha256sum "$REC" | cut -d' ' -f1)"
  artifact_root_sha256: "$ROOT"
command:
  - "python"
  - "scripts/run_lm1_smoke.py"
  - "run"
  - "--plan"
  - "$PLAN"
  - "--expected-plan-sha256"
  - "$(sha256sum "$PLAN" | cut -d' ' -f1)"
  - "--output-dir"
  - "/outputs/lm1smoke"
  - "--allocation-minutes"
  - "10"
YAML
sub() { uv run --locked python scripts/submit_docker_research_job.py "$M" "$@"; }
sub --dry-run > "${M%.yaml}.dry-run.json" 2>&1 || { echo "dry-run failed"; tail -5 "${M%.yaml}.dry-run.json"; exit 2; }
sub --test-only > "${M%.yaml}.test-only.txt" 2>&1 || { echo "test-only failed"; tail -5 "${M%.yaml}.test-only.txt"; exit 2; }
if [[ "$MODE" != submit ]]; then echo "checks passed: $(tail -1 "${M%.yaml}.test-only.txt")"; exit 0; fi
# GPU 0 must be held by the other project's job, so Slurm cannot allocate it here.
gres_used=$(scontrol show nodes -d | sed -n 's/^ *GresUsed=//p')
[[ "$gres_used" =~ IDX:0([,-]|\)) ]] || { echo "GPU 0 is not allocated to another job ($gres_used); not submitting"; exit 4; }
lama=$(squeue -h -o "%i %j %T %b" | awk '$2 ~ /^transcreate-/ && $3 == "RUNNING"' | head -1)
[[ -n "$lama" ]] || { echo "no running transcreate job holds GPU 0; not submitting"; exit 4; }
{ echo "== smoke $S at $(date -u +%FT%TZ)"; squeue -h -o "%i %j %T %M %b"; echo "GresUsed=$gres_used";
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } >> "$R/ops/preflight.log"
sub > "${M%.yaml}.submit.txt" 2>&1 || { echo "submit failed"; tail -5 "${M%.yaml}.submit.txt"; exit 2; }
J="$(tail -1 "${M%.yaml}.submit.txt")"
log_job "LM1 smoke test job $J submitted (4 H100, limit 14 min = 0.933 GPU-h cap; overlay $IMAGE; $(basename "$M"))"
echo "$J"
