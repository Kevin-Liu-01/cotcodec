#!/bin/sh
# Run the reachability stage with N parallel workers inside the LO-VM container.
# Usage: reach.sh <jobs.jsonl> <out-dir> [workers]
set -eu
jobs="$1"; out="$2"; workers="${3:-8}"
cd /src
i=0
while [ "$i" -lt "$workers" ]; do
  TMPDIR=/tmp python3 -m harness.q2_mutation.reachability --jobs "$jobs" \
    --osworld /inputs/OSWorld --out "$out" --soffice /usr/bin/soffice \
    --profile-template /home/user/.config/libreoffice/4/user \
    --worker "$i" --workers "$workers" > "$out/worker-$i.log" 2>&1 &
  i=$((i + 1))
done
wait
cat "$out"/worker-*.log
