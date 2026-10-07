#!/usr/bin/env bash
# Submit the three CPU-only Slurm jobs of one control run on the H100 host:
#   1. metric image: build gold/do-nothing jobs for a split, score them raw
#      (no save) under both venvs;
#   2. LO-VM image: GUI-faithful save of every job (reachability stage);
#   3. metric image: merge the saved files and score them under both venvs.
# Jobs 2 and 3 depend on the previous job succeeding.
#
# Usage (on the host): submit_controls.sh <git-sha> <split> <run-name> \
#          <metric-image-id> <lo-image-id> [workers]
# Only the dev split may be run before the preregistration freeze.
set -Eeuo pipefail
sha="$1"; split="$2"; name="$3"; metric="$4"; lo="$5"; workers="${6:-16}"
root=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation
src="${root}/src/${sha}"
run="${root}/runs/${name}"
batch="${src}/infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
[[ -f "${src}/.git_sha" ]] || { echo "stage ${sha} first" >&2; exit 2; }
[[ ! -e "${run}" ]] || { echo "${run} exists; version the run name" >&2; exit 2; }
if [[ "${split}" != "dev" && "${Q2M_PREREG_FROZEN:-}" != "q2-evaluator-mutation-v1" ]]; then
  echo "only the dev split runs before the preregistration freeze" >&2
  exit 2
fi
mkdir -p "${run}/raw" "${run}/lo" "${run}/saved"
hex() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]).encode().hex())' "$@"; }

a1=$(hex sh -c "/src/infra/q2-mutation/run/make_jobs.sh ${split} /out/jobs.jsonl \
  && /src/infra/q2-mutation/run/score.sh /out/jobs.jsonl /out/raw ${workers} 2")
j1=$(sbatch --parsable --cpus-per-task="${workers}" --mem=96G --time=03:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${metric}",Q2M_ARGV_JSON_HEX="${a1}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/raw",Q2M_INPUTS="${root}/inputs",Q2M_TMPFS_SIZE=32g \
  "${batch}")

a2=$(hex sh -c "/src/infra/q2-mutation/run/reach.sh /ro/raw/jobs.jsonl /out ${workers}")
j2=$(sbatch --parsable --dependency=afterok:"${j1}" --cpus-per-task="${workers}" --mem=96G --time=03:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${lo}",Q2M_ARGV_JSON_HEX="${a2}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/lo",Q2M_INPUTS="${root}/inputs",Q2M_EXTRA_RO="${run}/raw:/ro/raw",Q2M_TMPFS_SIZE=32g \
  "${batch}")

a3=$(hex sh -c "cd /src && /opt/venv-lock/bin/python -m harness.q2_mutation.controls merge-lo \
  --jobs /ro/raw/jobs.jsonl --lo-rows \$(ls /ro/lo/reachability-*.jsonl) --out /out/jobs-saved.jsonl \
  && sed 's#\"/out/files/#\"/ro/lo/files/#g' /out/jobs-saved.jsonl > /out/jobs-saved-mounted.jsonl \
  && /src/infra/q2-mutation/run/score.sh /out/jobs-saved-mounted.jsonl /out/saved ${workers} 2")
j3=$(sbatch --parsable --dependency=afterok:"${j2}" --cpus-per-task="${workers}" --mem=96G --time=03:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${metric}",Q2M_ARGV_JSON_HEX="${a3}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/saved",Q2M_INPUTS="${root}/inputs",Q2M_EXTRA_RO="${run}/raw:/ro/raw+${run}/lo:/ro/lo",Q2M_TMPFS_SIZE=32g \
  "${batch}")

printf '{"run": "%s", "split": "%s", "git_sha": "%s", "jobs": [%s, %s, %s]}\n' \
  "${name}" "${split}" "${sha}" "${j1}" "${j2}" "${j3}" | tee "${run}/submitted.json"
