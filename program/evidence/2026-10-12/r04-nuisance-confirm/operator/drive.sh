#!/bin/sh
# Calls `r04_host.py next` every 60 s; prints state changes; exits on complete, any failure,
# the cap, an error, or 5 consecutive empty replies (ssh trouble).
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/r04op
last=""; empty=0
while true; do
  out=$($S/host.sh next)
  if [ -z "$out" ]; then empty=$((empty+1)); [ $empty -ge 5 ] && { echo "$(date -u +%FT%TZ) 5 empty replies"; exit 2; }; sleep 60; continue; fi
  empty=0
  if [ "$out" != "$last" ]; then echo "$(date -u +%FT%TZ) $out"; last="$out"; fi
  case "$out" in
    *'"complete"'*) exit 0;;
    *failed*|*cap_reached*|*Traceback*|*rror*|*SystemExit*|*refus*) exit 1;;
  esac
  sleep 60
done
