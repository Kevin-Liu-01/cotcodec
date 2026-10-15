#!/usr/bin/env bash
#SBATCH --job-name=g2c-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:15:00
#SBATCH --no-requeue
# CPU-only (no GRES) check of the g2c-precision-layout-v1 scripts in the two images (their own
# baked source). vLLM image: config inheritance from G2b, prompt rendering with each model
# tokenizer, EngineArgs and CacheConfig for every engine (the forced block is user-specified),
# the block rule against G2b's resolved blocks, the parsers; plus a second read-only source
# pass (vLLM 0.31.0's update_block_size_for_backend and where the engine syncs the enlarged
# block back). Research image: tiny random Qwen3.5 on CPU (scorer, GDN swap, r4 membership,
# input checks). No GPU, no network, no model weights read (tokenizer and config files only).
set -Eeuo pipefail
: "${G2C_OUT:?}"; : "${G2C_VLLM_IMAGE:?}"; : "${G2C_RESEARCH_IMAGE:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
mkdir -p "${G2C_OUT}"
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=4g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env HF_HUB_OFFLINE=1
  --env TRANSFORMERS_OFFLINE=1 --env USER=cotcodec --env LOGNAME=cotcodec
  --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor --env TRITON_CACHE_DIR=/tmp/triton
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}" --workdir /workspace/cotcodec)
for image in "${G2C_VLLM_IMAGE}" "${G2C_RESEARCH_IMAGE}"; do
  nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${image}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
  [[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
done
set +e
docker run "${common[@]}" --volume /home/kevin/cotcodec-runs/hf-cache:/model-cache:ro \
  "${G2C_VLLM_IMAGE}" python scripts/run_g2c_rollouts.py selftest \
  > "${G2C_OUT}/rollouts-selftest.json" 2> "${G2C_OUT}/rollouts-selftest.stderr"
echo "rollouts selftest exit $?" | tee -a "${G2C_OUT}/exits.txt"
docker run "${common[@]}" --env OMP_NUM_THREADS=8 "${G2C_RESEARCH_IMAGE}" \
  python scripts/run_g2c_teacher_force.py selftest \
  > "${G2C_OUT}/teacher-force-selftest.json" 2> "${G2C_OUT}/teacher-force-selftest.stderr"
echo "teacher-force selftest exit $?" | tee -a "${G2C_OUT}/exits.txt"
docker run "${common[@]}" "${G2C_VLLM_IMAGE}" python scripts/run_g2c_rollouts.py plan \
  > "${G2C_OUT}/rollouts-plan.json" 2> "${G2C_OUT}/rollouts-plan.stderr"
echo "rollouts plan exit $?" | tee -a "${G2C_OUT}/exits.txt"
read -r -d '' vinner <<'INNER' || true
set -u
V=/usr/local/lib/python3.12/dist-packages/vllm
show() { echo "== ${1#$V/}:$2-$3"; sed -n "$2,$3p" "$1" | nl -ba -v "$2"; }
echo "== vllm $(sed -n 's/^__version__ = version = //p' "$V/_version.py")"
I="$V/platforms/interface.py"; sha256sum "$I" | sed "s#$V/##"; show "$I" 610 710
C="$V/v1/engine/core_client.py"; sha256sum "$C" | sed "s#$V/##"; show "$C" 820 870
U="$V/v1/executor/uniproc_executor.py"; sha256sum "$U" | sed "s#$V/##"; show "$U" 60 90
M="$V/v1/executor/multiproc_executor.py"; sha256sum "$M" | sed "s#$V/##"; show "$M" 685 705
A="$V/engine/arg_utils.py"; sha256sum "$A" | sed "s#$V/##"; show "$A" 568 573; show "$A" 2205 2226
K="$V/config/cache.py"; sha256sum "$K" | sed "s#$V/##"; show "$K" 56 80; show "$K" 160 180
INNER
docker run "${common[@]}" --entrypoint /bin/bash "${G2C_VLLM_IMAGE}" -c "${vinner}" \
  > "${G2C_OUT}/vllm-block-size-source-2.txt" 2>&1
echo "source pass 2 exit $?" | tee -a "${G2C_OUT}/exits.txt"
