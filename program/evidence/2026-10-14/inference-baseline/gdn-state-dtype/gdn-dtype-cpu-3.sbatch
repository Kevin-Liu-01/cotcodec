#!/usr/bin/env bash
#SBATCH --job-name=ib-gdn-dtype-cpu-3
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
# CPU-only (no GRES), read-only source check for inference-baseline-v1 (third pass: the second failed on an ambiguous grep):
# print, with line numbers, the vLLM 0.31.0 source that sets the gated-DeltaNet state dtype for
# Qwen3.5 and Qwen3.6-MoE, in both overlay images. No model, no GPU, no network; read-only root.
set -Eeuo pipefail
: "${IB_OUT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=256m --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES=)
read -r -d '' inner <<'INNER' || true
set -u
if ls /dev/nvidia* >/dev/null 2>&1; then echo "container sees GPU device nodes"; exit 2; fi
V=/usr/local/lib/python3.12/dist-packages/vllm
show() { echo "== ${1#$V/}:$2-$3"; sed -n "$2,$3p" "$1" | nl -ba -v "$2"; }
echo "== vllm $(sed -n 's/^__version__ = version = //p' "$V/_version.py")"
C="$V/model_executor/models/config.py"; U="$V/model_executor/layers/mamba/mamba_utils.py"
Q="$V/model_executor/models/qwen3_5.py"; I="$V/platforms/interface.py"; K="$V/v1/kv_cache_interface.py"
sha256sum "$C" "$U" "$Q" "$I" "$K" | sed "s#$V/##"
echo "== ${C#$V/}: MODELS_CONFIG_MAP entries for Qwen3_5"; grep -n -E '"Qwen3_5[A-Za-z]*": ' "$C"
n=$(grep -n "^class Qwen3_5ForConditionalGenerationConfig" "$C" | cut -d: -f1); show "$C" "$n" "$((n+26))"
show "$U" 96 131
n=$(grep -n "def gated_delta_net_state_shape" "$U" | cut -d: -f1); show "$U" "$((n-1))" "$((n+21))"
echo "== ${Q#$V/}: classes that define get_mamba_state_dtype_from_config"
awk '/^class /{c=$0; l=NR} /def get_mamba_state_dtype_from_config/{print l": "c"  ->  line "NR}' "$Q"
show "$I" 987 1018
n=$(grep -n "^class MambaSpec" "$K" | head -1 | cut -d: -f1); show "$K" "$n" "$((n+36))"
INNER
for image in sha256:16bea3e4af794246e3dd8a6e1f6866987bc795857b7ab3f0095c2767b6c8e961 \
             sha256:9e411974772f044300795537d6f11aff553a0c6ebd82165d674950985282a6d8; do
  short="${image#sha256:}"; short="${short:0:8}"
  { echo "image ${image}"; docker run "${common[@]}" --entrypoint /bin/sh "${image}" -c "${inner}"; } \
    > "${IB_OUT}/vllm-gdn-dtype-v3-${short}.txt" 2>&1
done
echo done
