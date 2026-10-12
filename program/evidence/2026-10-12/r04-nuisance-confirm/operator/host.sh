#!/bin/sh
# usage: host.sh next|status [extra args]; runs the host tool from the freeze export
cmd="$1"; shift
perl -e 'alarm shift; exec @ARGV' 150 ssh -o BatchMode=yes fal-h100-01 "export R04_PREREG_FROZEN=r04-checker-nuisance-invariance-v1; SRC=~/cotcodec-runs/stage0/r04-nuisance/src/e312e996fe7d3d032016bc1f6195cc3b7449af68; python3 \$SRC/infra/r04-nuisance/run/r04_host.py $cmd --name r04-registered-v1 $*" 2>&1 | grep -v -E '([0-9]{1,3}\.){3}[0-9]{1,3}'
