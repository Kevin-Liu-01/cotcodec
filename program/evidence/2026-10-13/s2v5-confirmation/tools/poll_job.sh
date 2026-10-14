#!/usr/bin/env bash
# Read-only poll of one confirmation job: queue state, per-campaign sessions done, trials and
# failed trials so far, the batch end line. One line.
J="$1"
perl -e 'alarm shift; exec @ARGV' 60 ssh -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR fal-h100-01 "
  t=\$(date -u +%FT%TZ); q=\$(squeue -a -h -o '%i:%j:%T' | tr '\n' ' ');
  R=\$HOME/cotcodec-runs/stage0/s2v5/confirm/runs/$J; s='';
  for d in \$R/[0-9][0-9]-*; do [ -d \"\$d\" ] || continue;
    nc=\$(ls \$d/cycles 2>/dev/null | grep -c '^cycle-[0-9]*\.json\$');
    nt=\$(cat \$d/cycles/cycle-*.trials.jsonl 2>/dev/null | grep -c '\"cell\"');
    nf=\$(cat \$d/cycles/cycle-*.trials.jsonl 2>/dev/null | grep -c '\"pass\": false');
    rc=\$([ -f \$d/receipt.json ] && echo R || echo -);
    s=\"\$s \$(basename \$d):sessions=\$nc,trials=\$nt,fail=\$nf,\$rc\"; done;
  e=\$(grep -h 'lane_exit=\|driver_exit=' \$R/preflight.txt \$R/[0-9][0-9]-*/preflight.txt 2>/dev/null | tr '\n' ';');
  st=\$(cat \$R/slurm-state/$J.txt 2>/dev/null | grep -oE 'JobState=[A-Z_]+|ExitCode=[^ ]+' | tr '\n' ' ');
  echo \"\$t q=[\$q]\$s end=[\$e] slurm=[\$st]\"" 2>&1 | sed -E 's/([0-9]{1,3}\.){3}[0-9]{1,3}/<ip>/g' | tr '\n' ' '
echo
