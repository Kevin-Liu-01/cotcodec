#!/usr/bin/env bash
# Submit the three CPU-only Slurm jobs of one mutation run on the H100 host
# (blind spec -> operator -> mutant -> GUI-faithful save -> checker verdict):
#   1. metric image: control jobs for the split (gold pairing), mutation
#      targets, blind specs validated and copied to JSON;
#   2. LO-VM image: base / initial / null saves, planning with the blind specs,
#      UNO application, purity against the null mutant, deduplication, then the
#      GUI-faithful save stage (reach.sh) on admitted mutants and null mutants;
#   3. metric image: the K2 fidelity sample (job list only, no verdict), merge
#      saved files, score under both venvs (VerdictRow JSONL), re-check
#      operator purity on the saved files, report.
# Jobs 2 and 3 depend on the previous job succeeding. Every container is
# GPU-less and network-less (q2-mutation-cpu.sbatch, decisions D12 and D13).
#
# Usage (on the host): submit_mutants.sh <git-sha> <split> <run-name> \
#          <metric-image-id> <lo-image-id> [workers] [apply-to: gold|base]
# Only the dev split runs before the preregistration freeze; the campaign
# driver also refuses any other split unless the staged tree carries the
# frozen ledger row and Q2M_PREREG_FROZEN=q2-evaluator-mutation-v1 is set.
set -Eeuo pipefail
sha="$1"; split="$2"; name="$3"; metric="$4"; lo="$5"; workers="${6:-16}"; apply_to="${7:-gold}"
[[ "${apply_to}" == "gold" || "${apply_to}" == "base" ]] || { echo "apply-to is gold or base" >&2; exit 2; }
root=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation
src="${root}/src/${sha}"
run="${root}/runs/${name}"
batch="${src}/infra/slurm/host-single-node/q2-mutation-cpu.sbatch"
[[ -f "${src}/.git_sha" ]] || { echo "stage ${sha} first" >&2; exit 2; }
[[ "$(cat "${src}/.git_sha")" == "${sha}" ]] || { echo "${src}/.git_sha mismatch" >&2; exit 2; }
[[ ! -e "${run}" ]] || { echo "${run} exists; version the run name" >&2; exit 2; }
# Host-side: .git_sha, and for any split but dev the frozen ledger row (hash
# chain and digest), Q2M_PREREG_FROZEN, the pinned image IDs and apply-to. The
# code, catalog, spec, split and input digests are checked inside the
# containers (`campaign guard` in jobs 1 and 3, `campaign targets`).
python3 "${src}/infra/q2-mutation/run/check_frozen.py" --src "${src}" --sha "${sha}" \
  --split "${split}" --metric "${metric}" --lo "${lo}" --apply-to "${apply_to}"
frozen_env=()
if [[ "${split}" != "dev" ]]; then
  frozen_env=(env Q2M_PREREG_FROZEN=q2-evaluator-mutation-v1)
fi
mkdir -p "${run}/prep" "${run}/build" "${run}/score"
hex() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]).encode().hex())' "$@"; }
py=/opt/venv-lock/bin/python
guard="cd /src && ${py} -m harness.q2_mutation.campaign guard --split ${split} --src /src --inputs /inputs"

a1=$(hex "${frozen_env[@]}" sh -c "${guard} && /src/infra/q2-mutation/run/make_jobs.sh ${split} /out/jobs.jsonl \
  && cd /src && ${py} -m harness.q2_mutation.campaign targets --src /src --osworld /inputs/OSWorld \
     --jobs /out/jobs.jsonl --split ${split} --out /out")
j1=$(sbatch --parsable --cpus-per-task=4 --mem=16G --time=00:30:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${metric}",Q2M_ARGV_JSON_HEX="${a1}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/prep",Q2M_INPUTS="${root}/inputs",Q2M_TMPFS_SIZE=8g \
  "${batch}")

a2=$(hex sh -c "cd /src && python3 -m harness.q2_mutation.campaign build \
     --targets /ro/prep/targets.jsonl --out /out \
     --profile-template /home/user/.config/libreoffice/4/user --shards 8 --apply-to ${apply_to} \
  && mkdir -p /out/lo && /src/infra/q2-mutation/run/reach.sh /out/scoring-jobs.jsonl /out/lo ${workers}")
j2=$(sbatch --parsable --dependency=afterok:"${j1}" --cpus-per-task="${workers}" --mem=96G --time=04:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${lo}",Q2M_ARGV_JSON_HEX="${a2}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/build",Q2M_INPUTS="${root}/inputs",Q2M_EXTRA_RO="${run}/prep:/ro/prep",Q2M_TMPFS_SIZE=32g \
  "${batch}")

# The K2 fidelity sample is drawn from the build's job list before any
# verdict exists (campaign k2-sample; preregistration section 10).
a3=$(hex "${frozen_env[@]}" sh -c "${guard} && ${py} -m harness.q2_mutation.campaign k2-sample \
     --jobs /ro/build/scoring-jobs.jsonl --sanitized /src/program/evidence/q2-mutation/sanitized-tasks \
     --out /out/k2-sample.jsonl \
  && ${py} -m harness.q2_mutation.campaign merge \
     --jobs /ro/build/scoring-jobs.jsonl --lo-rows \$(ls /ro/build/lo/reachability-*.jsonl) \
     --out /out/jobs-saved.jsonl --path-map /out/=/ro/build/ \
  && /src/infra/q2-mutation/run/score.sh /out/jobs-saved.jsonl /out/mut ${workers} 2 \
  && ${py} -m harness.q2_mutation.campaign recheck --mutations /ro/build/mutations.jsonl \
     --admission /ro/build/admission.jsonl --saved-jobs /out/jobs-saved.jsonl --out /out/recheck.jsonl \
  && ${py} -m harness.q2_mutation.campaign report --run /out --mutations /ro/build/mutations.jsonl \
     --admission /ro/build/admission.jsonl \
     --probe-touched /src/program/evidence/q2-mutation/harness/probe_touched.json")
j3=$(sbatch --parsable --dependency=afterok:"${j2}" --cpus-per-task="${workers}" --mem=96G --time=04:00:00 \
  --export=ALL,Q2M_MODE=run,Q2M_IMAGE_ID="${metric}",Q2M_ARGV_JSON_HEX="${a3}",Q2M_SOURCE="${src}",Q2M_RUN_DIR="${run}/score",Q2M_INPUTS="${root}/inputs",Q2M_EXTRA_RO="${run}/build:/ro/build",Q2M_TMPFS_SIZE=32g \
  "${batch}")

printf '{"run": "%s", "split": "%s", "git_sha": "%s", "apply_to": "%s", "jobs": [%s, %s, %s]}\n' \
  "${name}" "${split}" "${sha}" "${apply_to}" "${j1}" "${j2}" "${j3}" | tee "${run}/submitted.json"
