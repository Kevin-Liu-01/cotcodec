#!/usr/bin/env bash
# Submit one q2-action-path-v2 volume campaign (A4 or A7 at N*) from the read-only export,
# only on a quiet Slurm queue.
#   submit_volume.sh LABEL RENDERED_FILE
# ops/submit_rung.sh with its own queue-check log. Section 9's foreign-load rule binds only a
# ladder rung, but A4 and A7 run N* = 32 VM containers, about 3 below the roughly 35 that the
# host's fs.inotify.max_user_instances (128) let get dnsmasq in rung 40 (job 1025); another
# job's containers could push a boot over it. So, as for a rung, it runs the submitter's
# --dry-run (kept under ops/dryrun/) and --test-only first, then reads the whole Slurm queue
# (every user, every state) and submits only if it is empty. Otherwise it submits nothing and
# exits 3, and the operator waits and runs it again. Right after the submission it starts
# scripts/record_slurm_end_states.sh for the job (detached, 24 h limit) and logs the
# submission to ops/submissions.log and the queue check to ops/volume-queue-checks.log. A
# rerun under section 6.1 submits the same rendered file again under its own label.
set -euo pipefail
ROOT="$HOME/cotcodec-runs/q2-action-path-v2"
SHA=bf99a645c3782b2c59a75b6f463461b2515d0d97
E="$ROOT/src/$SHA"
R="$ROOT/manifests/rendered"
label="${1:?label}"
file="${2:?rendered file}"
manifest="$R/$file"
[[ -f "$manifest" ]] || { echo "no such manifest: $manifest" >&2; exit 2; }
mkdir -p "$ROOT/ops/dryrun" "$ROOT/runs/slurm-state"
cd "$E"
timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" --dry-run \
  >"$ROOT/ops/dryrun/${file%.yaml}.json"
timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" --test-only \
  >"$ROOT/ops/dryrun/${file%.yaml}.test-only.txt" 2>&1
queue="$(timeout 60 squeue -h -o '%i|%u|%T|%C|%j')"
stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ -n "$queue" ]]; then
  echo "$stamp $label $file not-quiet rows=$(wc -l <<<"$queue")" \
    | tee -a "$ROOT/ops/volume-queue-checks.log"
  sed 's/^/  /' <<<"$queue" | tee -a "$ROOT/ops/volume-queue-checks.log"
  exit 3
fi
echo "$stamp $label $file quiet" >>"$ROOT/ops/volume-queue-checks.log"
job="$(timeout 300 python3 -B scripts/submit_vm_campaign.py "$manifest" | tr -d '[:space:]')"
[[ "$job" =~ ^[1-9][0-9]*$ ]] || { echo "submission of $file failed: $job" >&2; exit 1; }
setsid nohup timeout 86400 bash "$E/scripts/record_slurm_end_states.sh" \
  "$ROOT/runs/slurm-state" "$job" >"$ROOT/ops/watch-$job.log" 2>&1 </dev/null &
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $label job=$job manifest=$file" \
  | tee -a "$ROOT/ops/submissions.log"
