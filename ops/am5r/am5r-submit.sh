#!/usr/bin/env bash
# am5-ablated-cost-v2: write one population's GPU-job lane manifest (scripts/memcredit_am5r.py
# run, 1 H100, the image built from commit $2's capsule, the population's study artifact
# hash-bound), run the submitter's dry run and test-only check, and submit only with "submit",
# after the population's post-build CPU selftest passed on this image and the preflight finds no
# GPU job of this program and a free H100. "rerun" submits the registration's one allowed rerun,
# only when the rerun rule's record for the submitted job says "rerun" (am5r-rerun-decision.sh;
# registration section 8). A failed dry run or test-only check stops the script; a submission's
# output is kept as <...>.submit.txt only when the submitter exited 0 with a job id on its last
# line, so a failure before sbatch does not use up the submission. The held-out population passes
# the freeze gate (memcredit_am5r.gate) first, before the manifest and the dry run.
# Usage: am5r-submit.sh dev|reg <commit short id> <image id> <population> [check|submit|rerun]
set -Eeuo pipefail
source "$(dirname "$0")/am5r-env.sh" "${1:?mode}"
SHORT="${2:?commit short id}"; IMAGE="${3:?image id}"; POP="${4:?population}"; ACT="${5:-check}"
allowed_population "$POP"
check_image "$IMAGE"
check_checkout "$SHORT"
G=$(git rev-parse HEAD)
# The held-out population runs only after the freeze: the checkout's freeze gate (the ledger row
# with the registration file's SHA-256, every section 16 code pin) runs before anything else,
# so a refused gate leaves no manifest and calls no submitter.
if [[ "$POP" == heldout ]]; then
  uv run --locked --offline python -c "import sys;sys.path[:0]=['.','scripts'];import memcredit_am5r as r;r.gate('heldout')" >&2 \
    || { echo "the freeze gate refuses the held-out population; nothing written or submitted" >&2; exit 2; }
fi
ST="$R/selftest-${POP}-${SHORT}/exits.txt"
grep -qx "image ${IMAGE} population ${POP}" "$ST" && grep -qx "am5r selftest exit 0" "$ST" \
  && grep -qx "am5r plan exit 0" "$ST" || { echo "no passing post-build selftest of ${POP} for ${IMAGE}" >&2; exit 2; }
ART=$(artifact_for "$POP")
SRC=$(sha256sum "$R/capsule/source-${SHORT}.tar.gz" | cut -d" " -f1)
SHA=$(sha256sum "$ART" | cut -d" " -f1); SIZE=$(stat -c %s "$ART")
PIN=$(uv run --locked --offline python -c "import yaml,sys;print(yaml.safe_load(open('experiments/am5/am5-ablated-cost-v2.yaml'))['populations'][sys.argv[1]]['artifact_sha256'])" "$POP")
[[ "$SHA" == "$PIN" ]] || { echo "the ${POP} artifact is not the pinned one" >&2; exit 2; }
MIN=$(uv run --locked --offline python -c "import yaml,sys;print(yaml.safe_load(open('experiments/am5/am5-ablated-cost-v2.yaml'))['jobs'][sys.argv[1]]['minutes'])" "$POP")
CAP=$(python3 -c "import math,sys;print(f'{math.ceil(int(sys.argv[1])/60*100)/100:.2f}')" "$MIN")
RECEIPT=$HOME/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-32b.json
RSHA=$(sha256sum "$RECEIPT" | cut -d" " -f1)
ROOT_SHA=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['artifact_root_sha256'])" "$RECEIPT")
REV=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['revision'])" "$RECEIPT")
mkdir -p "$R/runs/${POP}" "$R/manifests"
M="$R/manifests/${POP}-${SHORT}.yaml"
cat > "$M" <<YAML
# am5-ablated-cost-v2 (${AM5R_MODE}; population ${POP}): scripts/memcredit_am5r.py run in the
# cotcodec-vllm cu129 overlay built from commit ${SHORT}'s capsule. Steps on 1 H100, in order:
# readers Qwen3-8B (eager batch-invariant; the replay control's gated reader), OLMo-2-1124-7B-Instruct
# (eager batch-invariant, default-mode fallback only if it does not complete) and Qwen3.5-9B (eager,
# default mode), 71 requests per pool; then the Qwen3-32B judge (eager, batch-invariant). Slurm
# limit ${MIN} min = ${CAP} GPU-h cap. The lane's model is the judge, Qwen3-32B; the driver
# re-verifies every other model against its receipt and the config's pins.
runtime: docker-single-node-discovery-v1
name: am5r-${POP}
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
  - scripts/memcredit_am5r.py
  - run
  - "--population"
  - ${POP}
  - "--seeds"
  - "42"
  - "43"
  - "44"
  - "--output-dir"
  - /outputs/am5r
  - "--allocation-minutes"
  - "${MIN}"
  - "--evidence"
  - /inputs/study-artifact.json
  - "--expected-evidence-sha256"
  - "${SHA}"
YAML
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --dry-run \
  > "$R/manifests/${POP}-${SHORT}.dry-run.json" || { echo "dry run failed" >&2; exit 2; }
echo "dry run ok" >&2
uv run --locked --offline python scripts/submit_docker_research_job.py "$M" --test-only \
  > "$R/manifests/${POP}-${SHORT}.test-only.txt" 2>&1 || { cat "$R/manifests/${POP}-${SHORT}.test-only.txt" >&2; echo "test-only failed" >&2; exit 2; }
echo "test-only ok" >&2
case "$ACT" in
  check) exit 0 ;;
  submit) T="$R/manifests/${POP}-${SHORT}.submit.txt"
          [[ ! -e "$T" ]] || { echo "already submitted once from this commit; a rerun is 'rerun'" >&2; exit 2; } ;;
  rerun) S="$R/manifests/${POP}-${SHORT}.submit.txt"
         [[ -e "$S" ]] || { echo "nothing to rerun" >&2; exit 2; }
         J0=$(tail -1 "$S")
         D="$R/rerun-decision-${POP}-${J0}.json"
         [[ -f "$D" ]] && python3 -c "import json,sys;sys.exit(json.load(open(sys.argv[1]))['decision']!='rerun')" "$D" \
           || { echo "the rerun rule's record for job ${J0} does not say rerun ($D)" >&2; exit 2; }
         T="$R/manifests/${POP}-${SHORT}.rerun.txt"
         [[ ! -e "$T" ]] || { echo "the one allowed rerun was used" >&2; exit 2; } ;;
  *) echo "action is check, submit or rerun" >&2; exit 2 ;;
esac
bash "$(dirname "$0")/am5r-preflight.sh" "$AM5R_MODE" "${POP} ${ACT} ${SHORT}" 1
rm -f "$T.tmp"
if ! uv run --locked --offline python scripts/submit_docker_research_job.py "$M" > "$T.tmp" 2>&1; then
  echo "the submitter failed; nothing was recorded as submitted ($T.tmp kept)" >&2; exit 2
fi
J=$(tail -1 "$T.tmp")
[[ "$J" =~ ^[0-9]+$ ]] || { echo "no job id on the submitter's last line ($T.tmp kept)" >&2; exit 2; }
mv "$T.tmp" "$T"
log_job "am5r ${POP} GPU job ${ACT}: $J (git ${SHORT}, image ${IMAGE:7:8}, artifact ${SHA:0:8}, 1 H100, limit ${MIN} min)"
echo "$J"
