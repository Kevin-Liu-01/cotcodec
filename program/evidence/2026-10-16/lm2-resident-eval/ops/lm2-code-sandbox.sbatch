#!/usr/bin/env bash
#SBATCH --job-name=lm2-code-sandbox
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=01:30:00
#SBATCH --no-requeue
#SBATCH --output=/home/kevin/cotcodec-runs/stage0/lm2-resident-eval/ops/slurm-lm2-code-sandbox-%j.out
# LM2 (D129): grade model-written programs (LiveCodeBench tests) CPU only, in a locked-down
# container. This is the only LM2 step that executes model output, and it never gets a GPU:
#   - the Slurm job holds no GRES and refuses to start if Slurm or the environment shows a GPU;
#   - Docker's default runtime must be runc (no NVIDIA hook), the run names --runtime runc, passes
#     no --gpus or --device, and sets NVIDIA_VISIBLE_DEVICES=void; the grader then refuses to run
#     if any /dev/nvidia* or /dev/dri node or a non-loopback network interface is visible;
#   - --network none, --read-only root, a size-capped noexec-free tmpfs at /tmp for the programs,
#     --cap-drop ALL, no-new-privileges, user 65534, pid, memory and CPU limits;
#   - the source tree and the input are mounted read-only; verdicts leave only through stdout.
# Inputs (sbatch --export): LM2_SRC (clean checkout), LM2_INPUT (code-input.jsonl), LM2_OUT
# (verdicts path), LM2_WORKERS (default 28).
set -Eeuo pipefail
: "${SLURM_JOB_ID:?run through sbatch}"
: "${LM2_SRC:?clean checkout}"; : "${LM2_INPUT:?code-input.jsonl}"; : "${LM2_OUT:?verdicts path}"
for name in SLURM_JOB_GPUS SLURM_STEP_GPUS SLURM_GPUS SLURM_GPUS_ON_NODE CUDA_VISIBLE_DEVICES GPU_DEVICE_ORDINAL; do
  [[ -z "${!name:-}" ]] || { echo "$name is set; refusing"; exit 2; }
done
if scontrol show job "$SLURM_JOB_ID" | tr ' ' '\n' | grep -E '^(TRES|TresPerNode|TresPerJob|TresPerTask)=' | grep -qiE 'gres/gpu|gpu:'; then
  echo "allocated a GPU; refusing"; exit 2
fi
rt="$(docker info --format '{{.DefaultRuntime}}')"
[[ "$rt" == runc ]] || { echo "docker default runtime is $rt, not runc; refusing"; exit 2; }
IMAGE=sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848
[[ "$(docker image inspect --format '{{.Id}}' "$IMAGE")" == "$IMAGE" ]] || { echo "image missing"; exit 2; }
( cd "$LM2_SRC" && [[ -z "$(git status --porcelain)" ]] ) || { echo "source tree is not clean"; exit 2; }
IN_DIR="$(dirname "$LM2_INPUT")"; IN_NAME="$(basename "$LM2_INPUT")"
echo "source $(cd "$LM2_SRC" && git rev-parse HEAD); input $(sha256sum "$LM2_INPUT" | cut -d' ' -f1); grader $(sha256sum "$LM2_SRC/scripts/lm2_code_grader.py" | cut -d' ' -f1)"
docker run --rm -i --runtime runc --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=8g \
  --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 2048 --cpus "${SLURM_CPUS_PER_TASK:-32}" --memory 88g --memory-swap 88g \
  --user 65534:65534 --workdir /tmp \
  -e NVIDIA_VISIBLE_DEVICES=void -e NVIDIA_DRIVER_CAPABILITIES= -e HOME=/tmp \
  -v "$LM2_SRC:/src:ro" -v "$IN_DIR:/input:ro" \
  --entrypoint /usr/bin/python3 "$IMAGE" \
  -I /src/scripts/lm2_code_grader.py --input "/input/$IN_NAME" --workers "${LM2_WORKERS:-28}" \
  > "$LM2_OUT" 2> "${LM2_OUT%.jsonl}.stderr.txt"
echo "verdicts $(wc -l < "$LM2_OUT") $(sha256sum "$LM2_OUT" | cut -d' ' -f1)"
