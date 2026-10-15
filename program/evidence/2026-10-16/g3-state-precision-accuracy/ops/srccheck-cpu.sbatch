#!/usr/bin/env bash
#SBATCH --job-name=g3-srccheck-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
# G3 read-only source check (CPU, no GRES, no network): vLLM 0.31.0's v1 scheduler, which request
# it preempts when the block pool is full and how a preempted request resumes. Prints the lines
# with numbers from the main run's image.
set -Eeuo pipefail
: "${G3_OUT:?}"; : "${G3_VLLM_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
mkdir -p "$G3_OUT"
read -r -d '' inner <<'INNER' || true
set -u
V=/usr/local/lib/python3.12/dist-packages/vllm
echo "== vllm $(sed -n 's/^__version__ = version = //p' "$V/_version.py")"
F="$V/v1/core/sched/scheduler.py"; sha256sum "$F" | sed "s#$V/##"
grep -n "preempt" "$F" | head -60
for n in $(grep -n "def _preempt_request\|preempted_req = \|self.running.pop()\|RequestStatus.PREEMPTED\|num_computed_tokens = 0" "$F" | cut -d: -f1 | head -12); do
  echo "== ${F#$V/}:$((n-6))-$((n+10))"; sed -n "$((n-6)),$((n+10))p" "$F" | nl -ba -v $((n-6))
done
echo "== ${F#$V/}:1538-1590 (_preempt_request)"; sed -n "1538,1590p" "$F" | nl -ba -v 1538
O="$V/outputs.py"; sha256sum "$O" | sed "s#$V/##"; echo "== outputs.py: num_preemptions"; grep -n "num_preemptions\|class RequestOutput" "$O" | head
INNER
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env NVIDIA_VISIBLE_DEVICES=void \
  --env CUDA_VISIBLE_DEVICES= --label "cotcodec.slurm_job=${SLURM_JOB_ID}" \
  --entrypoint /bin/bash "$G3_VLLM_IMAGE" -c "$inner" > "$G3_OUT/vllm-scheduler-preemption${G3_SUFFIX:-}.txt" 2>&1
echo "exit $?" >> "$G3_OUT/vllm-scheduler-preemption${G3_SUFFIX:-}.txt"
