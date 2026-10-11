#!/bin/sh
# Run the R04 save stage with N parallel workers inside a LibreOffice container.
# Usage: resave.sh <items.jsonl> <out-dir> <workers> <only-file|-> <cell> [<cell> ...]
# Like infra/q2-mutation/run/reach.sh: one process per worker, each on its own display.
set -eu
jobs="$1"; out="$2"; workers="$3"; only="$4"; shift 4
cd /src
logs="$out/logs/${Q2M_SLURM_JOB_ID:-local}"
mkdir -p "$logs"
extra=""
if [ "$only" != "-" ]; then extra="--only $only"; fi
pids=""
i=0
while [ "$i" -lt "$workers" ]; do
  # shellcheck disable=SC2086
  TMPDIR=/tmp python3 -m harness.r04_nuisance.resave --jobs "$jobs" \
    --osworld /inputs/OSWorld --out "$out" \
    --profile-template /home/user/.config/libreoffice/4/user \
    --worker "$i" --workers "$workers" $extra --cells "$@" > "$logs/worker-$i.log" 2>&1 &
  pids="$pids $!"
  i=$((i + 1))
done
status=0
for pid in $pids; do wait "$pid" || status=1; done
cat "$logs"/worker-*.log
exit "$status"
