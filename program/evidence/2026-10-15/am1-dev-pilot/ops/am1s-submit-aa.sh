#!/usr/bin/env bash
# AM1 cross-GPU A/A diagnostic (EXPLORATORY): write the diagnostic job's manifest, run the submitter's dry run
# and test-only check, and submit only when no G2c GPU job is queued or running.
# Usage: am1s-submit-aa.sh <commit short id> <overlay image id> <artifact path> [submit]
set -Eeuo pipefail
SHORT="${1:?commit short id}"; IMAGE="${2:?overlay image id}"; ART="${3:?artifact}"; MODE="${4:-check}"
R=/home/kevin/cotcodec-runs/stage0/am1-study
C="$R/checkout"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
G=$(git rev-parse HEAD); [[ "${G:0:8}" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
RECEIPT=/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['artifact_root_sha256'])")
REV=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['revision'])")
MIN=22
mkdir -p "$R/runs/aa"
cat > "$R/manifests/aa-${SHORT}.yaml" <<YAML
# AM1 cross-GPU A/A diagnostic (EXPLORATORY): scripts/memcredit_study.py run --config
# experiments/am1/memcredit-study-v1-aa.yaml in the cotcodec-vllm cu129 overlay built from the
# same commit. Phases fresh, swapcache, eager (Qwen3-8B reader, batch-invariant, first 16
# development questions, canonical) and judge (Qwen3-32B) on 2 H100; Slurm limit ${MIN} min =
# 0.73 GPU-h cap. The lane's model is the judge, Qwen3-32B; the driver re-verifies Qwen3-8B.
runtime: docker-single-node-discovery-v1
name: am1-study-aa
image_id: ${IMAGE}
git_sha: "${G}"
source_sha256: "${SRC}"
run_root: ${R}/runs/aa
container_profile: vllm
resources:
  gpu_type: h100
  gpus: 2
  cpus: 32
  memory_gb: 256
  minutes: ${MIN}
budget:
  max_gpu_hours: 0.74
randomness_contract: assignment-seed-matrix
seeds: [42, 43, 44]
seed_binding:
  flag: "--seeds"
model:
  cache_host_path: /home/kevin/cotcodec-runs/hf-cache
  model_id: qwen3-32b
  revision: "${REV}"
  receipt_sha256: "${RSHA}"
  artifact_root_sha256: "${ROOT_SHA}"
study_artifact:
  source_id: memcredit-study-dev-pools
  revision: "${G}"
  license: MIT
  host_path: ${ART}
  sha256: "${SHA}"
  size_bytes: ${SIZE}
command:
  - python
  - scripts/memcredit_study.py
  - run
  - "--config"
  - experiments/am1/memcredit-study-v1-aa.yaml
  - "--seeds"
  - "42"
  - "43"
  - "44"
  - "--output-dir"
  - /outputs/am1
  - "--allocation-minutes"
  - "${MIN}"
  - "--evidence"
  - /inputs/study-artifact.json
  - "--expected-evidence-sha256"
  - "${SHA}"
YAML
M="$R/manifests/aa-${SHORT}.yaml"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run > "$R/manifests/aa-${SHORT}.dry-run.json" && echo "dry run ok"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only > "$R/manifests/aa-${SHORT}.test-only.txt" 2>&1 && echo "test-only ok"
cat "$R/manifests/aa-${SHORT}.test-only.txt"
[[ "${MODE}" == submit ]] || exit 0
bash "$R/ops/am1s-preflight.sh" "aa ${SHORT}"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$R/manifests/aa-${SHORT}.submit.txt" 2>&1
J=$(tail -1 "$R/manifests/aa-${SHORT}.submit.txt")
echo "$(date -u +%FT%TZ) A/A diagnostic job submitted: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 2 H100, limit ${MIN} min)" | tee -a "$R/ops/jobs.log"
