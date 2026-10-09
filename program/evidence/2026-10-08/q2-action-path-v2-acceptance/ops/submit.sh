#!/usr/bin/env bash
# Submit q2-action-path-v2 validity-control campaigns from the read-only export, one
# manifest at a time: the submitter's --dry-run (kept under ops/dryrun/), --test-only, then
# the submission, logged to ops/submissions.log. Right after each submission it starts
# scripts/record_slurm_end_states.sh for that job (detached, 24 h limit), so the Slurm end
# state is caught before Slurm forgets the job.
#   submit.sh [--cap N] LABEL RENDERED_FILE...
# --cap N waits (polling squeue every 20 s) until fewer than N of this user's jobs named
# like the manifest's job name are pending or running before each submission.
set -euo pipefail
ROOT="$HOME/cotcodec-runs/q2-action-path-v2"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="$ROOT/src/$SHA"
R="$ROOT/manifests/rendered"
cap=0
if [[ "${1:-}" == "--cap" ]]; then
  cap="$2"
  shift 2
fi
label="${1:?label}"
shift
mkdir -p "$ROOT/ops/dryrun" "$ROOT/runs/slurm-state"
cd "$E"
for file in "$@"; do
  manifest="$R/$file"
  name="$(python3 -B -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["name"])' "$manifest")"
  if [[ "$cap" -gt 0 ]]; then
    while [[ "$(timeout 60 squeue -h -u "$(id -un)" -n "$name" -o %i | wc -l)" -ge "$cap" ]]; do
      sleep 20
    done
  fi
  timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" --dry-run \
    >"$ROOT/ops/dryrun/${file%.yaml}.json"
  timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" --test-only \
    >"$ROOT/ops/dryrun/${file%.yaml}.test-only.txt" 2>&1
  job="$(timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" | tr -d '[:space:]')"
  [[ "$job" =~ ^[1-9][0-9]*$ ]] || { echo "submission of $file failed: $job" >&2; exit 1; }
  setsid nohup timeout 86400 bash "$E/scripts/record_slurm_end_states.sh" \
    "$ROOT/runs/slurm-state" "$job" >"$ROOT/ops/watch-$job.log" 2>&1 </dev/null &
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $label job=$job manifest=$file" \
    | tee -a "$ROOT/ops/submissions.log"
done
