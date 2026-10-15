#!/usr/bin/env bash
# AM5: write the GPU job's lane manifest (scripts/memcredit_am5.py run, 1 H100, the image built
# from commit $1's capsule, the ablated artifact hash-bound), run the submitter's dry run and
# test-only check, and submit only with "submit", after the CPU selftest passed on this image and
# the preflight finds no GPU job of this program and a free H100. The docker-research lane runs
# the container read-only, --cap-drop ALL, no-new-privileges, the user's uid:gid, a tmpfs /tmp,
# no network and only the allocated GPU (--gpus device=). One submission per commit.
# Usage: am5-submit.sh <commit short id> <image id> [check|submit]
set -Eeuo pipefail
source "$(dirname "$0")/am5-env.sh"
SHORT="${1:?commit short id}"; IMAGE="${2:?image id}"; ACT="${3:-check}"
check_image "$IMAGE"
check_checkout "$SHORT"
G=$(git rev-parse HEAD)
ST="$R/selftest-${SHORT}/exits.txt"
grep -qx "image ${IMAGE}" "$ST" && grep -qx "am5 selftest exit 0" "$ST" \
  && grep -qx "am5 plan exit 0" "$ST" || { echo "no passing post-build selftest for ${IMAGE}" >&2; exit 2; }
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ABL_ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ABL_ART")
PIN=$(uv run --locked --offline python -c "import yaml;print(yaml.safe_load(open('experiments/am5/am5-evidence-ablated-dev.yaml'))['population']['artifact_sha256'])")
[[ "$SHA" == "$PIN" ]] || { echo "the ablated artifact is not the pinned one" >&2; exit 2; }
MIN=$(uv run --locked --offline python -c "import yaml;print(yaml.safe_load(open('experiments/am5/am5-evidence-ablated-dev.yaml'))['job']['minutes'])")
CAP=$(python3 -c "import math,sys;print(f'{math.ceil(int(sys.argv[1])/60*100)/100:.2f}')" "$MIN")
RECEIPT=$HOME/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['artifact_root_sha256'])" "$RECEIPT")
REV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['revision'])" "$RECEIPT")
mkdir -p "$R/runs/dev-ablated" "$R/manifests"
M="$R/manifests/dev-ablated-${SHORT}.yaml"
cat > "$M" <<YAML
# AM5 (exploratory; development split, evidence sessions removed): scripts/memcredit_am5.py run in
# the cotcodec-vllm cu129 overlay built from commit ${SHORT}'s capsule. Steps on 1 H100, in order:
# readers Qwen3-8B (eager batch-invariant), OLMo-2-1124-7B-Instruct (eager batch-invariant,
# default-mode fallback only if it does not complete) and Qwen3.5-9B (eager, default mode), 71
# requests per pool; then the Qwen3-32B judge (eager, batch-invariant). Slurm limit ${MIN} min =
# ${CAP} GPU-h cap. The lane's model is the judge, Qwen3-32B; the driver re-verifies every other
# model against its receipt and the config's pins.
runtime: docker-single-node-discovery-v1
name: am5-dev-ablated
image_id: ${IMAGE}
git_sha: "${G}"
source_sha256: "${SRC}"
run_root: ${R}/runs/dev-ablated
container_profile: vllm
resources:
  gpu_type: h100
  gpus: 1
  cpus: 16
  memory_gb: 128
  minutes: ${MIN}
budget:
  max_gpu_hours: ${CAP}
randomness_contract: assignment-seed-matrix
seeds: [42, 43, 44]
seed_binding:
  flag: "--seeds"
model:
  cache_host_path: ${HOME}/cotcodec-runs/hf-cache
  model_id: qwen3-32b
  revision: "${REV}"
  receipt_sha256: "${RSHA}"
  artifact_root_sha256: "${ROOT_SHA}"
study_artifact:
  source_id: memcredit-study-dev-ablated-pools
  revision: "${G}"
  license: MIT
  host_path: ${ABL_ART}
  sha256: "${SHA}"
  size_bytes: ${SIZE}
command:
  - python
  - scripts/memcredit_am5.py
  - run
  - "--seeds"
  - "42"
  - "43"
  - "44"
  - "--output-dir"
  - /outputs/am5
  - "--allocation-minutes"
  - "${MIN}"
  - "--evidence"
  - /inputs/study-artifact.json
  - "--expected-evidence-sha256"
  - "${SHA}"
YAML
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run \
  > "$R/manifests/dev-ablated-${SHORT}.dry-run.json" || { echo "dry run failed" >&2; exit 2; }
echo "dry run ok" >&2
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only \
  > "$R/manifests/dev-ablated-${SHORT}.test-only.txt" 2>&1 || { cat "$R/manifests/dev-ablated-${SHORT}.test-only.txt" >&2; echo "test-only failed" >&2; exit 2; }
echo "test-only ok" >&2
case "$ACT" in
  check) exit 0 ;;
  submit) T="$R/manifests/dev-ablated-${SHORT}.submit.txt"
          [[ ! -e "$T" ]] || { echo "already submitted once from this commit" >&2; exit 2; } ;;
  *) echo "action is check or submit" >&2; exit 2 ;;
esac
bash "$(dirname "$0")/am5-preflight.sh" "dev-ablated ${ACT} ${SHORT}" 1
rm -f "$T.tmp"
if ! uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$T.tmp" 2>&1; then
  echo "the submitter failed; nothing was recorded as submitted ($T.tmp kept)" >&2; exit 2
fi
J=$(tail -1 "$T.tmp")
[[ "$J" =~ ^[0-9]+$ ]] || { echo "no job id on the submitter's last line ($T.tmp kept)" >&2; exit 2; }
mv "$T.tmp" "$T"
log_job "am5 dev-ablated GPU job ${ACT}: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 1 H100, limit ${MIN} min)"
echo "$J"
