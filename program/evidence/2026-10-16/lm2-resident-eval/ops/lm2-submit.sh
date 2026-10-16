#!/usr/bin/env bash
# LM2 (D129): render one arm's lane manifest (the overlay image of commit $1, the arm's GPU count
# from the plan, gpt-oss-120b-mxfp4-gguf as the lane's pinned model so the model cache is mounted
# and that snapshot is re-hashed in the container; the served arm's own receipt is checked by the
# driver, and every served file was re-hashed by a CPU job), dry-run and test-only it through the
# lane's submitter from the checkout of that commit, then with "submit" record the queue and
# submit it. Submission is refused unless another project's job holds physical GPU 0, so Slurm
# cannot hand it to this job; the driver also refuses GPU 0's UUID.
# Usage: lm2-submit.sh <commit short id> <arm> <pilot|main> <slurm minutes> <check|submit> \
#          [extra driver arguments, e.g. --cap math=40 --slots 24]
# Env: LM2_RESUME_JOB=<job id> copies that job's /outputs/lm2 into the new job (same commit only).
set -Eeuo pipefail
source "$(dirname "$0")/lm2-env.sh"
S="${1:?commit short id}"; ARM="${2:?arm}"; PHASE="${3:?pilot|main}"; MIN="${4:?minutes}"
MODE="${5:?check|submit}"; shift 5
CO="$R/checkout"
B="$R/builds/llamacpp-overlay-$S"
A="$R/capsule/source-$S.tar.gz"
TAG="${PHASE}-${ARM}-$(date -u +%H%M%S)"
M="$R/manifests/$TAG.yaml"
mkdir -p "$R/manifests" "$R/runs/$ARM"
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
PLAN=experiments/lm2/lm2-resident-eval-v1.json
GPUS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['arms'][sys.argv[2]]['gpus'])" "$PLAN" "$ARM")
CAP=$(python3 -c "import math,sys; print(math.ceil(int(sys.argv[1])*int(sys.argv[2])/60*10000)/10000)" "$GPUS" "$MIN")
DRV_MIN=$((MIN - 2))
MID=gpt-oss-120b-mxfp4-gguf
REC="$RECEIPTS/$MID.json"
REV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['revision'])" "$REC")
ROOT=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['artifact_root_sha256'])" "$REC")
{
cat <<YAML
# LM2 (D129, EXPLORATORY) $PHASE: arm $ARM on $GPUS H100 in stock llama.cpp b11669 (layer split, all
# layers on GPU). Slurm limit $MIN min x $GPUS H100 = $CAP GPU-h cap; the driver stops at its own
# budget ($DRV_MIN min after it starts, less a 200 s reserve; the lane sends USR1 180 s before the limit).
runtime: docker-single-node-discovery-v1
name: lm2-$PHASE-$ARM
image_id: $IMAGE
git_sha: "$(git rev-parse HEAD)"
source_sha256: "$(sha256sum "$A" | cut -d' ' -f1)"
run_root: $R/runs/$ARM
resources:
  gpu_type: h100
  gpus: $GPUS
  cpus: 16
  memory_gb: 128
  minutes: $MIN
budget:
  max_gpu_hours: $CAP
randomness_contract: assignment-seed-matrix
seeds: [42, 43, 44]
seed_binding:
  flag: "--seeds"
model:
  cache_host_path: $C
  model_id: $MID
  revision: "$REV"
  receipt_sha256: "$(sha256sum "$REC" | cut -d' ' -f1)"
  artifact_root_sha256: "$ROOT"
YAML
if [[ -n "${LM2_RESUME_JOB:-}" ]]; then
  echo "resume_from_job_id: \"$LM2_RESUME_JOB\""
  echo "resume_subpath: lm2"
fi
echo "command:"
for a in python scripts/run_lm2_eval.py run --plan "$PLAN" --expected-plan-sha256 "$(sha256sum "$PLAN" | cut -d' ' -f1)" \
  --arm "$ARM" --phase "$PHASE" --seeds 42 43 44 --output-dir /outputs/lm2 --allocation-minutes "$DRV_MIN" "$@"; do
  echo "  - \"$a\""
done
} > "$M"
sub() { uv run --locked python scripts/submit_docker_research_job.py "$M" "$@"; }
sub --dry-run > "${M%.yaml}.dry-run.json" 2>&1 || { echo "dry-run failed"; tail -5 "${M%.yaml}.dry-run.json"; exit 2; }
sub --test-only > "${M%.yaml}.test-only.txt" 2>&1 || { echo "test-only failed"; tail -5 "${M%.yaml}.test-only.txt"; exit 2; }
if [[ "$MODE" != submit ]]; then echo "checks passed: $(tail -1 "${M%.yaml}.test-only.txt") ($M)"; exit 0; fi
gres_used=$(scontrol show nodes -d | sed -n 's/^ *GresUsed=//p')
[[ "$gres_used" =~ IDX:0([,-]|\)) ]] || { echo "GPU 0 is not allocated to another job ($gres_used); not submitting"; exit 4; }
lama=$(squeue -h -o "%i %j %T %b" | awk '$2 ~ /^transcreate-/ && $3 == "RUNNING"' | head -1)
[[ -n "$lama" ]] || { echo "no running transcreate job holds GPU 0; not submitting"; exit 4; }
{ echo "== $TAG at $(date -u +%FT%TZ)"; squeue -h -o "%i %j %T %M %b"; echo "GresUsed=$gres_used";
  nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } >> "$R/ops/preflight.log"
sub > "${M%.yaml}.submit.txt" 2>&1 || { echo "submit failed"; tail -5 "${M%.yaml}.submit.txt"; exit 2; }
J="$(tail -1 "${M%.yaml}.submit.txt")"
log_job "LM2 $PHASE $ARM job $J submitted ($GPUS H100, limit $MIN min = $CAP GPU-h cap; overlay $IMAGE; $(basename "$M"); extra: $*)"
nohup bash "$R/ops/lm2-capture-end.sh" "$J" "LM2 $PHASE $ARM" > /dev/null 2>&1 < /dev/null &
echo "$J"
