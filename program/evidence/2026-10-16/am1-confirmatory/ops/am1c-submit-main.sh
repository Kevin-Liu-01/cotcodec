#!/usr/bin/env bash
# am1-memory-credit-v1 (CONFIRMATORY; frozen, ledger row 23): write the registered GPU job's lane
# manifest (registration section 17: 90 minutes, 2 H100, the image built from the freeze commit's
# capsule, the held-out artifact hash-bound), run the submitter's dry run and test-only check, and
# submit only with "submit", after the post-build CPU selftest passed on this image and the
# preflight finds no GPU job of this program and 2 free H100s.
# Usage: am1c-submit-main.sh <overlay image id> [submit]
set -Eeuo pipefail
FREEZE=9ad36b10dcbd324647e4a98c3a150f954f7123f6
SHORT=${FREEZE:0:8}
IMAGE="${1:?overlay image id}"; MODE="${2:-check}"
R=/home/kevin/cotcodec-runs/stage0/am1-memory-credit-v1
C="$R/checkout"
ART="$R/study-artifact.json"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
G=$(git rev-parse HEAD); [[ "$G" == "${FREEZE}" ]] || { echo "checkout is not at the freeze commit"; exit 2; }
ST="$R/selftest-postbuild-${SHORT}/exits.txt"
grep -qx "image ${IMAGE} src baked config experiments/am1/am1-memory-credit-v1.yaml" "$ST" \
  && grep -qx "study selftest exit 0" "$ST" && grep -qx "study plan exit 0" "$ST" \
  || { echo "no passing post-build selftest for ${IMAGE}"; exit 2; }
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
RECEIPT=/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['artifact_root_sha256'])")
REV=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['revision'])")
MIN=90
mkdir -p "$R/runs/main"
M="$R/manifests/main-${SHORT}.yaml"
[[ ! -e "$M" || "${MODE}" != submit ]] || grep -q "^image_id: ${IMAGE}$" "$M" || { echo "manifest exists for another image"; exit 2; }
cat > "$M" <<YAML
# am1-memory-credit-v1 (CONFIRMATORY; registration program/preregistrations/am1-memory-credit-v1.md,
# frozen in ledger row 23, freeze commit ${FREEZE}): the registered GPU job,
# scripts/memcredit_study.py run --config experiments/am1/am1-memory-credit-v1.yaml, in the
# cotcodec-vllm cu129 overlay built from the freeze commit's source capsule. Phases reader (Qwen3-8B
# eager, batch-invariant; GPU 0 canonical, GPU 1 shuffled), judge (Qwen3-32B eager on both GPUs),
# extra (Qwen3-8B second judge on GPU 0, HF eager-attention signals on GPU 1) on 2 H100; Slurm
# limit ${MIN} min = 3.0 GPU-h cap. The lane's model is the judge, Qwen3-32B (full receipt in
# cotcodec-receipts); the driver re-verifies the reader, Qwen3-8B, against cotcodec-receipts-cpu-lane.
runtime: docker-single-node-discovery-v1
name: am1-memory-credit-v1
image_id: ${IMAGE}
git_sha: "${G}"
source_sha256: "${SRC}"
run_root: ${R}/runs/main
container_profile: vllm
resources:
  gpu_type: h100
  gpus: 2
  cpus: 32
  memory_gb: 256
  minutes: ${MIN}
budget:
  max_gpu_hours: 3.0
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
  source_id: am1-memory-credit-v1-heldout-pools
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
  - experiments/am1/am1-memory-credit-v1.yaml
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
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run > "$R/manifests/main-${SHORT}.dry-run.json" && echo "dry run ok"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only > "$R/manifests/main-${SHORT}.test-only.txt" 2>&1 && echo "test-only ok"
cat "$R/manifests/main-${SHORT}.test-only.txt"
[[ "${MODE}" == submit ]] || exit 0
[[ ! -e "$R/manifests/main-${SHORT}.submit.txt" ]] || { echo "already submitted once; a second submission is not allowed by this script"; exit 2; }
bash "$R/ops/am1c-preflight.sh" "main ${SHORT}" 2
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$R/manifests/main-${SHORT}.submit.txt" 2>&1
J=$(tail -1 "$R/manifests/main-${SHORT}.submit.txt")
echo "$(date -u +%FT%TZ) registered GPU job submitted: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 2 H100, limit ${MIN} min)" | tee -a "$R/ops/jobs.log"
