#!/usr/bin/env bash
# am3-nonabstain-generality-v1: write one population's GPU-job lane manifest (scripts/memcredit_am3g.py
# run, 1 H100, the image built from commit $2's capsule, the population's study artifact
# hash-bound), run the submitter's dry run and test-only check, and submit only with "submit",
# after the population's post-build CPU selftest passed on this image and the preflight finds no
# GPU job of this program and a free H100. "rerun" submits the registration's one allowed rerun
# of a job that ended incomplete for an infrastructure reason (registration section 8).
# Usage: am3g-submit.sh dev|reg <commit short id> <image id> <population> [check|submit|rerun]
set -Eeuo pipefail
source "$(dirname "$0")/am3g-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; IMAGE="${3:?image id}"; POP="${4:?population}"; ACT="${5:-check}"
allowed_population "$POP"
check_checkout "$SHORT"
G=$(git rev-parse HEAD)
ST="$R/selftest-${POP}-${SHORT}/exits.txt"
grep -qx "image ${IMAGE} population ${POP}" "$ST" && grep -qx "am3g selftest exit 0" "$ST" \
  && grep -qx "am3g plan exit 0" "$ST" || { echo "no passing post-build selftest of ${POP} for ${IMAGE}"; exit 2; }
ART=$(artifact_for "$POP")
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
PIN=$(uv run --locked --offline python -c "import yaml,sys;print(yaml.safe_load(open('experiments/am3/am3-nonabstain-generality-v1.yaml'))['populations'][sys.argv[1]]['artifact_sha256'])" "$POP")
[[ "$SHA" == "$PIN" ]] || { echo "the ${POP} artifact is not the pinned one"; exit 2; }
MIN=$(uv run --locked --offline python -c "import yaml,sys;print(yaml.safe_load(open('experiments/am3/am3-nonabstain-generality-v1.yaml'))['jobs'][sys.argv[1]]['minutes'])" "$POP")
CAP=$(python3 -c "import math,sys;print(f'{math.ceil(int(sys.argv[1])/60*100)/100:.2f}')" "$MIN")
RECEIPT=$HOME/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['artifact_root_sha256'])" "$RECEIPT")
REV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['revision'])" "$RECEIPT")
mkdir -p "$R/runs/${POP}" "$R/manifests"
M="$R/manifests/${POP}-${SHORT}.yaml"
cat > "$M" <<YAML
# am3-nonabstain-generality-v1 (${AM3G_MODE}; population ${POP}): scripts/memcredit_am3g.py run in the
# cotcodec-vllm cu129 overlay built from commit ${SHORT}'s capsule. Steps on 1 H100, in order:
# readers Qwen3-8B (anchor, eager batch-invariant), OLMo-2-1124-7B-Instruct (eager batch-invariant,
# default-mode fallback only if it does not complete) and Qwen3.5-9B (eager, default mode), 71
# requests per pool; then the Qwen3-32B and Qwen3-8B judges (eager, batch-invariant). Slurm limit
# ${MIN} min = ${CAP} GPU-h cap. The lane's model is the primary judge, Qwen3-32B; the driver
# re-verifies every other model against its receipt and the config's pins.
runtime: docker-single-node-discovery-v1
name: am3g-${POP}
image_id: ${IMAGE}
git_sha: "${G}"
source_sha256: "${SRC}"
run_root: ${R}/runs/${POP}
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
  source_id: $(source_id_for "$POP")
  revision: "${G}"
  license: MIT
  host_path: ${ART}
  sha256: "${SHA}"
  size_bytes: ${SIZE}
command:
  - python
  - scripts/memcredit_am3g.py
  - run
  - "--population"
  - ${POP}
  - "--seeds"
  - "42"
  - "43"
  - "44"
  - "--output-dir"
  - /outputs/am3g
  - "--allocation-minutes"
  - "${MIN}"
  - "--evidence"
  - /inputs/study-artifact.json
  - "--expected-evidence-sha256"
  - "${SHA}"
YAML
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run > "$R/manifests/${POP}-${SHORT}.dry-run.json" && echo "dry run ok"
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only > "$R/manifests/${POP}-${SHORT}.test-only.txt" 2>&1 && echo "test-only ok"
cat "$R/manifests/${POP}-${SHORT}.test-only.txt"
case "$ACT" in
  check) exit 0 ;;
  submit) T="$R/manifests/${POP}-${SHORT}.submit.txt"
          [[ ! -e "$T" ]] || { echo "already submitted once from this commit; a rerun is 'rerun'"; exit 2; } ;;
  rerun) [[ -e "$R/manifests/${POP}-${SHORT}.submit.txt" ]] || { echo "nothing to rerun"; exit 2; }
         T="$R/manifests/${POP}-${SHORT}.rerun.txt"
         [[ ! -e "$T" ]] || { echo "the one allowed rerun was used"; exit 2; } ;;
  *) echo "action is check, submit or rerun"; exit 2 ;;
esac
bash "$(dirname "$0")/am3g-preflight.sh" "$AM3G_MODE" "${POP} ${ACT} ${SHORT}" 1
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$T" 2>&1
J=$(tail -1 "$T")
log_job "am3g ${POP} GPU job ${ACT}: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 1 H100, limit ${MIN} min)"
