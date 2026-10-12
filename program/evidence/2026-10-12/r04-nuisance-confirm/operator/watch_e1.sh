#!/bin/sh
# Poll squeue every 30 s; log changes to watch.log; exit 0 once a job whose name has "4b-e1"
# was seen and the queue is then empty; exit 2 at the deadline (arg 1 seconds, default 10800).
S=/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/r04op
L=$S/watch.log
end=$(( $(date +%s) + ${1:-10800} ))
seen=0; last=""
while [ $(date +%s) -lt $end ]; do
  q=$(perl -e 'alarm shift; exec @ARGV' 40 ssh -o BatchMode=yes fal-h100-01 'squeue -h -o "%i|%j|%T|%M"' 2>/dev/null | tr '\n' ';')
  rc=$?
  if [ "$q" != "$last" ]; then echo "$(date -u +%FT%TZ) [$q]" >> $L; last="$q"; fi
  case "$q" in *4b-e1*) seen=1;; esac
  if [ $seen -eq 1 ] && [ -z "$q" ]; then
    # confirm empty twice, 20 s apart (ssh failure also gives empty output)
    sleep 20
    q2=$(perl -e 'alarm shift; exec @ARGV' 40 ssh -o BatchMode=yes fal-h100-01 'squeue -h -o "%i|%j|%T|%M"; echo OK' 2>/dev/null | tr '\n' ';')
    if [ "$q2" = "OK;" ]; then echo "$(date -u +%FT%TZ) E1 4B done, queue empty" >> $L; exit 0; fi
  fi
  sleep 30
done
echo "$(date -u +%FT%TZ) deadline" >> $L; exit 2
