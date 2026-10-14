R=/home/kevin/cotcodec-runs/stage0/q2-stage1e
X=$R/src/f6144d6bf745d944cb016cfc2b9894e1dbf7eb66
PLAN=$X/program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json
OPSC=fb4458a664f4ec5de363b54b0344e8638d76b02f
OPS=$R/analysis-ops/$OPSC/ops/q2e-analysis
A=/home/kevin/cotcodec-runs/stage0/q2-stage1e/analysis/e-v1
INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs
VMS="1219 1222 1251 1254 1265 1268 1272 1275"
RUNS=(); for VM in $VMS; do RUNS+=(--run-dir $R/runs/$VM); done
DR0S=(); for VM in $VMS; do DR0S+=(--dr0 $A/dr0-$VM.json); done
export R X PLAN OPSC OPS A INPUTS
EOP() { python3 -E -s -B $OPS/e_ops.py "$@"; }
set -o noclobber
