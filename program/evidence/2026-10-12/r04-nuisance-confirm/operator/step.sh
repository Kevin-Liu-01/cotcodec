#!/bin/sh
# One foreground poll of at most ~215 s: call `next` every 60 s, log changes, stop early on a
# change of state. Exit 0 normally, 1 on a failure/cap/error line, 3 on complete.
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/r04op
L=$S/drive.log
end=$(( $(date +%s) + ${1:-70} ))
last=$(tail -1 $L | cut -d' ' -f2-)
while :; do
  out=$($S/host.sh next)
  if [ -n "$out" ] && [ "$out" != "$last" ]; then
    echo "$(date -u +%FT%TZ) $out" >> $L; echo "$(date -u +%H:%M:%S) $out"
    case "$out" in
      *'"complete"'*) exit 3;;
      *failed*|*cap_reached*|*Traceback*|*rror*|*refus*) exit 1;;
    esac
    exit 0
  fi
  [ -z "$out" ] && echo "empty reply"
  [ $(( $(date +%s) + 20 )) -gt $end ] && { echo "$(date -u +%H:%M:%S) unchanged: $last"; exit 0; }
  sleep 15
done
