#!/usr/bin/env bash
#SBATCH --job-name=g3-lme-probe-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# G3 CPU-only (no GRES) sizing probe: LongMemEval-S full-haystack prompt lengths in the Qwen3.5
# tokenizer, inside G2c's vLLM overlay image (sha256:7f6d49d7). No GPU, no network.
set -Eeuo pipefail
R=/home/kevin/cotcodec-runs/stage0/g3-state-precision-accuracy
IMG=sha256:7f6d49d75fe5d6cefd3fc348129c48e141ab607118a55b7897a47df8bf988ff3
LME=/home/kevin/cotcodec-runs/inputs/longmemeval/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
OUT="$R/probe/lme-lengths"; mkdir -p "$OUT"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home \
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1 \
  --env TRANSFORMERS_OFFLINE=1 --env OMP_NUM_THREADS=8 \
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" \
  --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  --volume "$LME:/inputs/lme.json:ro" \
  --volume "$R/ops/lme_len_probe.py:/probe/lme_len_probe.py:ro" \
  --volume "$OUT:/outputs:rw" \
  --entrypoint python "$IMG" /probe/lme_len_probe.py > "$OUT/stdout.json" 2> "$OUT/stderr.txt"
echo "exit $?" >> "$OUT/stdout.json"
