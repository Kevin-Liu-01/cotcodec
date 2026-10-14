#!/usr/bin/env bash
# AM1 Step 0 (EXPLORATORY): write the main job's manifest, run the submitter's dry run and
# test-only check, and submit only when no G2b job is running (logged to ops/preflight.log).
# Usage: am1-submit-main.sh <commit short id> <overlay image id> [submit]
set -Eeuo pipefail
SHORT="${1:?commit short id}"; IMAGE="${2:?overlay image id}"; MODE="${3:-check}"
R=/home/kevin/cotcodec-runs/stage0/am1-step0
C="$R/checkout"
ART="$R/prepare/study-artifact.json"
cd "$C"
[[ -z "$(git status --porcelain)" ]] || { echo dirty; exit 2; }
G=$(git rev-parse HEAD); [[ "${G:0:8}" == "${SHORT}" ]] || { echo "checkout is not at ${SHORT}"; exit 2; }
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
MIN=75
mkdir -p "$R/runs/main"
cat > "$R/manifests/main-${SHORT}.yaml" <<YAML
# AM1 Step 0 (EXPLORATORY), main job: scripts/memcredit_step0.py in the cotcodec-vllm cu129
# overlay built from the same commit. Sessions bi-a, default-a, bi-b, default-b, bi-c
# (experiments/am1/memcredit-step0-v1.yaml) on 1 H100; Slurm limit ${MIN} min = 1.25 GPU-h cap.
# The lane's model is a verification placeholder (the smallest full receipt in the lane's
# receipt root); the reader, Qwen3-8B, is re-verified by the driver against its full receipt in
# cotcodec-receipts-cpu-lane (fetch job 1333) before any engine starts.
runtime: docker-single-node-discovery-v1
name: am1-step0-main
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
  max_gpu_hours: 1.25
randomness_contract: assignment-seed-matrix
seeds: [42, 43, 44]
seed_binding:
  flag: "--seeds"
model:
  cache_host_path: /home/kevin/cotcodec-runs/hf-cache
  model_id: qwen3-0.6b-base
  revision: "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
  receipt_sha256: "e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df"
  artifact_root_sha256: "7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0"
study_artifact:
  source_id: memcredit-step0-pools
  revision: "${G}"
  license: MIT
  host_path: ${ART}
  sha256: "${SHA}"
  size_bytes: ${SIZE}
command:
  - python
  - scripts/memcredit_step0.py
  - run
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
M="$R/manifests/main-${SHORT}.yaml"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run > "$R/manifests/main-${SHORT}.dry-run.json" && echo "dry run ok"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only > "$R/manifests/main-${SHORT}.test-only.txt" 2>&1 && echo "test-only ok"
cat "$R/manifests/main-${SHORT}.test-only.txt"
[[ "${MODE}" == submit ]] || exit 0
{ echo "== main ${SHORT} at $(date -u +%FT%TZ)"; echo "-- squeue"; squeue -h -o "%i %j %T %M %b";
  echo "-- gpus"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader; } \
  | tee -a "$R/ops/preflight.log"
if squeue -h -o "%j" | grep -q '^g2b'; then echo "a G2b job is running; not submitting" >&2; exit 3; fi
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$R/manifests/main-${SHORT}.submit.txt" 2>&1
J=$(tail -1 "$R/manifests/main-${SHORT}.submit.txt")
echo "$(date -u +%FT%TZ) main job submitted: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 1 H100, limit ${MIN} min)" | tee -a "$R/ops/jobs.log"
