#!/usr/bin/env bash
#SBATCH --job-name=ib-gdn-dtype-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
# CPU-only (no GRES), read-only source check for inference-baseline-v1: print the vLLM source
# lines that set the gated-DeltaNet (GDN) recurrent-state dtype and shape, in both overlay
# images used by jobs a-f and g-h. No model, no GPU, no network; the image root is read-only.
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
echo "== vllm package"; ls -d "$V"; grep -n -E "^(__version__|version|__version_tuple__|commit_id)" "$V/_version.py" || true
echo "== files that mention mamba_ssm_dtype or mamba_ssm_cache_dtype"
grep -rln --include='*.py' -E "mamba_ssm_dtype|mamba_ssm_cache_dtype" "$V" | sort
echo "== every line"
grep -rn --include='*.py' -E "mamba_ssm_dtype|mamba_ssm_cache_dtype" "$V" | sort
F="$V/model_executor/layers/mamba/mamba_utils.py"
echo "== sha256"; sha256sum "$F" "$V/model_executor/models/config.py" "$V/config/cache.py" "$V/model_executor/models/qwen3_next.py" "$V/model_executor/models/qwen3_5.py" 2>&1
echo "== $F: gated_delta_net_state_dtype"; grep -n -A 24 "def gated_delta_net_state_dtype" "$F"
echo "== $F: _mamba_state_dtype"; grep -n -A 20 "def _mamba_state_dtype" "$F"
echo "== $F: gated_delta_net_state_shape"; grep -n -A 28 "def gated_delta_net_state_shape" "$F"
for M in qwen3_next qwen3_5; do
  echo "== models/$M.py: get_mamba_state_dtype_from_config / shape"
  grep -n -A 16 -E "def get_mamba_state_(dtype|shape)_from_config" "$V/model_executor/models/$M.py" || true
done
echo "== models/config.py: context of mamba_ssm lines"
for n in $(grep -n -E "mamba_ssm_dtype|mamba_ssm_cache_dtype" "$V/model_executor/models/config.py" | cut -d: -f1); do
  echo "-- line $n"; sed -n "$((n>12?n-12:1)),$((n+6))p" "$V/model_executor/models/config.py" | nl -ba -v $((n>12?n-12:1))
done
echo "== models/config.py lines 625-660"; sed -n '625,660p' "$V/model_executor/models/config.py" | nl -ba -v 625
echo "== config/cache.py: mamba_ssm_cache_dtype"; grep -n -B 2 -A 8 "mamba_ssm_cache_dtype" "$V/config/cache.py" | head -60
echo "== page-size padding code"
grep -rn --include='*.py' -E "Padding mamba page size|attention page size is >= mamba page size" "$V" | sort
P=$(grep -rln --include='*.py' "Padding mamba page size" "$V" | head -1)
if [ -n "$P" ]; then
  n=$(grep -n "attention page size is >= mamba page size" "$P" | head -1 | cut -d: -f1)
  echo "-- $P lines $((n-45))-$((n+30))"; sed -n "$((n-45)),$((n+30))p" "$P" | nl -ba -v $((n-45))
fi
echo "== MambaSpec page_size_bytes"
S=$(grep -rln --include='*.py' "class MambaSpec" "$V" | head -1); echo "$S"
n=$(grep -n "class MambaSpec" "$S" | cut -d: -f1); sed -n "${n},$((n+40))p" "$S" | nl -ba -v "$n"
INNER
for image in sha256:16bea3e4af794246e3dd8a6e1f6866987bc795857b7ab3f0095c2767b6c8e961 \
             sha256:9e411974772f044300795537d6f11aff553a0c6ebd82165d674950985282a6d8; do
  short="${image#sha256:}"; short="${short:0:8}"
  { echo "image ${image}"; docker run "${common[@]}" --entrypoint /bin/sh "${image}" -c "${inner}"; } \
    > "${IB_OUT}/vllm-gdn-dtype-${short}.txt" 2>&1
done
echo done
