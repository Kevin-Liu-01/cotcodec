R=/home/kevin/cotcodec-runs/stage0/q2-stage1
X=$R/src/d5f57988ab94e0c098feddb744b78b73b5ad88ca
PLAN=$X/program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json
OPSC=6d85529b1f84e1c9bd6a01b693c0eab76d0054c6
OPS=$R/ops/$OPSC/ops/s1a-analysis
A=/home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1
INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs
VMS="1045 1048 1051 1062"
COSTVMS="1045 1048 1051 1062"
RUNS=(); for VM in $VMS; do RUNS+=(--run-dir $R/runs/$VM); done
COSTRUNS=(); for VM in $COSTVMS; do COSTRUNS+=(--run-dir $R/runs/$VM); done
DR0S=(); for VM in $VMS; do DR0S+=(--dr0 $A/dr0-$VM.json); done
step() { sbatch --parsable --job-name="s1a-$1" --output="$A/logs/%x-%j.out" "$OPS/cpu-step.sbatch" "$OPS/$2" "${@:3}"; }
set -o noclobber                         # a shell redirection never overwrites an output
