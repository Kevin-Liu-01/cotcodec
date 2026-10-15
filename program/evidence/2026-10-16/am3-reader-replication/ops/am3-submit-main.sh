#!/usr/bin/env bash
# AM3 (EXPLORATORY): write the GPU job's lane manifest (scripts/memcredit_am3.py run, 1 H100,
# the image built from commit $1's capsule, the pilot's development artifact hash-bound), run the
# submitter's dry run and test-only check, and submit only with "submit", after the post-build
# CPU selftest passed on this image and the preflight finds no GPU job of this program and a free
# H100. Usage: am3-submit-main.sh <commit short id> <overlay image id> [submit]
set -Eeuo pipefail
SHORT="${1:?commit short id}"; IMAGE="${2:?overlay image id}"; MODE="${3:-check}"
R=/home/kevin/cotcodec-runs/stage0/am3-reader-replication
C="$R/checkout"
ART=/home/kevin/cotcodec-runs/stage0/am1-study/runs/main/1411/study-artifact.json
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
G=$(git rev-parse HEAD); [[ "${G:0:8}" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
ST="$R/selftest-postbuild-${SHORT}/exits.txt"
grep -qx "image ${IMAGE} src baked" "$ST" && grep -qx "am3 selftest exit 0" "$ST" \
  && grep -qx "am3 plan exit 0" "$ST" || { echo "no passing post-build selftest for ${IMAGE}"; exit 2; }
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
[[ "$SHA" == 15567cf14a0c38c1f9edec1f47feceb2a6fccf116338e5957182d03f1d996ebc ]] || { echo "not the pilot's artifact"; exit 2; }
RECEIPT=/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['artifact_root_sha256'])")
REV=$(python3 -c "import json;print(json.load(open('$RECEIPT'))['revision'])")
MIN=55
mkdir -p "$R/runs/main" "$R/manifests"
M="$R/manifests/main-${SHORT}.yaml"
cat > "$M" <<YAML
# AM3 (EXPLORATORY, development split only; D117): scripts/memcredit_am3.py run in the
# cotcodec-vllm cu129 overlay built from commit ${SHORT}'s capsule. Steps on 1 H100, in order:
# readers Qwen3-8B (anchor, eager batch-invariant), OLMo-2-1124-7B-Instruct and Qwen3.5-9B (eager,
# batch-invariant, each with a default-mode fallback run only if it does not complete), 71
# requests per pool on the pilot's 126 pools; then the Qwen3-32B and Qwen3-8B judges (eager,
# batch-invariant). Slurm limit ${MIN} min = 0.92 GPU-h cap. The lane's model is the primary judge,
# Qwen3-32B; the driver re-verifies every other model against its receipt.
runtime: docker-single-node-discovery-v1
name: am3-reader-replication
image_id: ${IMAGE}
git_sha: "${G}"
source_sha256: "${SRC}"
run_root: ${R}/runs/main
container_profile: vllm
resources:
  gpu_type: h100
  gpus: 1
  cpus: 16
  memory_gb: 128
  minutes: ${MIN}
budget:
  max_gpu_hours: 0.92
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
  - scripts/memcredit_am3.py
  - run
  - "--seeds"
  - "42"
  - "43"
  - "44"
  - "--output-dir"
  - /outputs/am3
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
[[ ! -e "$R/manifests/main-${SHORT}.submit.txt" ]] || { echo "already submitted once from this commit"; exit 2; }
bash "$R/ops/am3-preflight.sh" "main ${SHORT}" 1
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$R/manifests/main-${SHORT}.submit.txt" 2>&1
J=$(tail -1 "$R/manifests/main-${SHORT}.submit.txt")
echo "$(date -u +%FT%TZ) AM3 GPU job submitted: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 1 H100, limit ${MIN} min)" | tee -a "$R/ops/jobs.log"
