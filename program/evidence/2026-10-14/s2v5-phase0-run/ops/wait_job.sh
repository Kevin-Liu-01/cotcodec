#!/usr/bin/env bash
# wait.sh JOB: wait up to 3.5 min for the background watcher of JOB to end; print state.
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2v5-ops
W=$S/host-logs/watch-$1.stdout
for i in $(seq 1 7); do [ -s $W ] && break; sleep 30; done
date -u +%T; cat $W; tail -1 $S/host-logs/watch-$1.log
pgrep -f "watch_job.sh $1" >/dev/null && echo watcher-alive || echo watcher-gone
