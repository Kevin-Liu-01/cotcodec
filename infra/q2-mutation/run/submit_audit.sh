#!/usr/bin/env bash
# Submit the CPU-only audit packet job of one scored mutation run on the H100
# host (LO-VM image: the VM's LibreOffice renders the pages):
#   1. harness.q2_mutation.audit sample: candidate pool, stratified sample,
#      shams, every P1 flip of the control run, Kevin's spot-check list;
#   2. harness.q2_mutation.audit packets: one blind packet per item, sharded so
#      each shard fits a lane study artifact (the open-weight rater's input).
# sample.jsonl (labels, verdicts) stays on the host next to the packets and is
# never mounted into a rater job. GPU-less, network-less (q2-mutation-cpu.sbatch).
#
# Usage (on the host): submit_audit.sh <git-sha> <mutation-run> <controls-run> \
#          <audit-name> <metric-image-id> <lo-image-id> [workers]
# The split is the one the mutation run recorded; any split but dev needs the
# frozen ledger row and Q2M_PREREG_FROZEN (check_frozen.py), as the runs did.
set -Eeuo pipefail
sha="$1"; mrun="$2"; crun="$3"; name="$4"; metric="$5"; lo="$6"; workers="${7:-8}"
root=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation
src="${root}/src/${sha}"
mut="${root}/runs/${mrun}"
ctl="${root}/runs/${crun}"
out="${root}/audits/${name}"
batch="${src}/infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
[[ -f "${src}/.git_sha" && "$(cat "${src}/.git_sha")" == "${sha}" ]] || { echo "stage ${sha} first" >&2; exit 2; }
[[ -f "${mut}/score/outcomes.jsonl" ]] || { echo "${mut} has no scored outcomes" >&2; exit 2; }
[[ -f "${ctl}/summary.json" ]] || { echo "${ctl} has no control summary" >&2; exit 2; }
[[ ! -e "${out}" ]] || { echo "${out} exists; version the audit name" >&2; exit 2; }
split="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["split"])' "${mut}/submitted.json")"
csplit="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["split"])' "${ctl}/submitted.json")"
[[ "${split}" == "${csplit}" ]] || { echo "mutation run is ${split}, control run is ${csplit}" >&2; exit 2; }
python3 "${src}/infra/q2-mutation/run/check_frozen.py" --src "${src}" --sha "${sha}" \
  --split "${split}" --metric "${metric}" --lo "${lo}"
mkdir -p "${out}"
hex() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]).encode().hex())' "$@"; }

argv=$(hex sh -c "cd /src && python3 -m harness.q2_mutation.audit sample --run /ro/mut --controls /ro/controls \
     --sanitized /src/program/evidence/q2-mutation/sanitized-tasks \
     --file-cache /inputs/file_cache_1e112283/files --out /out \
     --path-map /ro/build/=/ro/mut/build/ --path-map /out/=/ro/controls/lo/ \
  && python3 -m harness.q2_mutation.audit packets --items /out/items.jsonl \
     --sanitized /src/program/evidence/q2-mutation/sanitized-tasks --out /out/packets \
     --workers ${workers}")
job=$(sbatch --parsable --cpus-per-task="${workers}" --mem=64G --time=03:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${lo}",Q2M_ARGV_JSON_HEX="${argv}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${out}",Q2M_INPUTS="${root}/inputs",Q2M_EXTRA_RO="${mut}:/ro/mut+${ctl}:/ro/controls",Q2M_TMPFS_SIZE=32g \
  "${batch}")
printf '{"audit": "%s", "split": "%s", "mutation_run": "%s", "controls_run": "%s", "git_sha": "%s", "job": %s}\n' \
  "${name}" "${split}" "${mrun}" "${crun}" "${sha}" "${job}" | tee "${out}/submitted.json"
