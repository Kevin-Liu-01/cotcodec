#!/usr/bin/env bash
# Submit one CPU-only Slurm job (metric image) that counts mutation targets per
# split: tasks with a complete gold, gold files per operator family, and the
# skip reasons. It builds the control job list (task configs and file cache
# only) and runs `campaign targets --count-only`: no spec is read, no mutant is
# made and no checker runs, so it is allowed for every split before the
# preregistration freeze. The counts size the confirmatory design.
#
# Usage (on the host): submit_target_counts.sh <git-sha> <run-name> <metric-image-id>
set -Eeuo pipefail
sha="$1"; name="$2"; metric="$3"
root=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation
src="${root}/src/${sha}"
run="${root}/runs/${name}"
batch="${src}/infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
[[ -f "${src}/.git_sha" ]] || { echo "stage ${sha} first" >&2; exit 2; }
[[ "$(cat "${src}/.git_sha")" == "${sha}" ]] || { echo "${src}/.git_sha mismatch" >&2; exit 2; }
[[ ! -e "${run}" ]] || { echo "${run} exists; version the run name" >&2; exit 2; }
mkdir -p "${run}"
hex() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]).encode().hex())' "$@"; }
py=/opt/venv-lock/bin/python
steps=""
for split in dev confirm reserve; do
  steps="${steps}/src/infra/q2-mutation/run/make_jobs.sh ${split} /out/jobs-${split}.jsonl && \
cd /src && ${py} -m harness.q2_mutation.campaign targets --src /src --osworld /inputs/OSWorld \
--jobs /out/jobs-${split}.jsonl --split ${split} --out /out --count-only && "
done
argv=$(hex sh -c "${steps}true")
job=$(sbatch --parsable --cpus-per-task=2 --mem=8G --time=00:20:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${metric}",Q2M_ARGV_JSON_HEX="${argv}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}",Q2M_INPUTS="${root}/inputs",Q2M_TMPFS_SIZE=4g \
  "${batch}")
printf '{"run": "%s", "git_sha": "%s", "jobs": [%s]}\n' "${name}" "${sha}" "${job}" \
  | tee "${run}/submitted.json"
