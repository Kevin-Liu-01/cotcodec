#!/usr/bin/env bash
#SBATCH --job-name=g2b-srccheck-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:08:00
#SBATCH --no-requeue
# CPU-only (no GRES), read-only source check for g2b-state-dtype-v1 (EXPLORATORY): print, with
# line numbers, (1) how vLLM 0.31.0 exposes and applies the GDN recurrent-state dtype
# (mamba_ssm_cache_dtype), its GDN prefill/decode kernels' state handling, and the offline
# metrics API, from the G2 pilot's vLLM overlay; (2) the transformers 5.15 Qwen3.5 GatedDeltaNet
# forward and the FLA 0.5.2 kernels the trainer path calls, from the G2 pilot's research overlay.
# No model weights, no GPU, no network; read-only root.
set -Eeuo pipefail
: "${G2B_OUT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
VLLM_IMAGE=sha256:fabad63386d3c39b296e037491d6a6a3b5457c3af31e57764c80ca33c4dec011
RESEARCH_IMAGE=sha256:95bb9a2d6602f743be1f0556e0aa3283de28a3330991f6996a9d66ffc35c080a
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env USER=cotcodec
  --env TRITON_CACHE_DIR=/tmp/triton --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}")
read -r -d '' vinner <<'INNER' || true
set -u
if ls /dev/nvidia* >/dev/null 2>&1; then echo "container sees GPU device nodes"; exit 2; fi
V=/usr/local/lib/python3.12/dist-packages/vllm
F=/usr/local/lib/python3.12/dist-packages/flashinfer
echo "== vllm $(sed -n 's/^__version__ = version = //p' "$V/_version.py")"
hdr() { echo; echo "######## $*"; }
show() { echo "== ${1#$V/}:$2-$3"; sed -n "$2,$3p" "$1" | nl -ba -v "$2"; }
grepn() { local f="$1"; shift; echo "== grep ${f#$V/}: $*"; grep -n -E "$@" "$f" | head -60; }
hdr "1. CacheConfig: MambaDType and the mamba dtype fields"
C="$V/config/cache.py"; sha256sum "$C" | sed "s#$V/##"
grepn "$C" "MambaDType|mamba_ssm_cache_dtype|mamba_cache_dtype|mamba_cache_mode|mamba_block_size"
n=$(grep -n "^MambaDType" "$C" | head -1 | cut -d: -f1); [[ -n "$n" ]] && show "$C" "$n" "$((n+2))"
n=$(grep -n "    mamba_cache_dtype:" "$C" | head -1 | cut -d: -f1); [[ -n "$n" ]] && show "$C" "$n" "$((n+14))"
hdr "2. CLI flags"
grepn "$V/engine/arg_utils.py" "mamba.ssm.cache.dtype|mamba_ssm_cache_dtype|mamba_cache_dtype"
hdr "3. dtype string map"
grep -rn -E "STR_DTYPE_TO_TORCH_DTYPE *=|^ *\"bfloat16\": torch.bfloat16" "$V/utils/" | head
hdr "4. GDN layer: where the state cache is read and written"
grep -rln -E "ssm_state" "$V/model_executor" "$V/v1" 2>/dev/null | head -30
for f in $(grep -rln -E "class .*GatedDeltaNet" "$V/model_executor" | head -5); do
  sha256sum "$f" | sed "s#$V/##"
  grepn "$f" "class |def |ssm_state|conv_state|initial_state|chunk_gated_delta_rule|fused_recurrent|fused_sigmoid|flashinfer|FlashInfer|dtype|float32|\.to\("
done
hdr "5. vLLM FLA ops (state load and store)"
ls "$V/model_executor/layers/fla/ops/" 2>/dev/null
for f in "$V/model_executor/layers/fla/ops/fused_recurrent.py" "$V/model_executor/layers/fla/ops/fused_sigmoid_gating.py" "$V/model_executor/layers/fla/ops/chunk.py" "$V/model_executor/layers/fla/ops/chunk_delta_h.py"; do
  [[ -f "$f" ]] && { sha256sum "$f" | sed "s#$V/##"; grepn "$f" "def |h0|ht|initial_state|final_state|float32|\.to\(|dtype"; }
done
hdr "6. FlashInfer GDN"
ls "$F" 2>/dev/null | grep -i -E "gdn|delta|mamba" ; grep -rln -i -E "gated_delta|gdn" "$F" 2>/dev/null | grep -v "\.cu$\|\.cuh$" | head -10
for f in $(grep -rln -i -E "def .*gdn|def .*gated_delta" "$F" 2>/dev/null | grep "\.py$" | head -4); do
  echo "== $f"; grep -n -i -E "def |dtype|float32|bfloat16|state" "$f" | head -50
done
grep -rn -i -E "flashinfer.*(gdn|gated_delta)|(gdn|gated_delta).*flashinfer|VLLM_USE_FLASHINFER.*GDN|GDN.*BACKEND|gdn_prefill" "$V" 2>/dev/null | grep -v "^Binary" | head -30
hdr "7. Offline metrics: LLM.get_metrics, metric names"
L="$V/entrypoints/llm.py"; grepn "$L" "def get_metrics|disable_log_stats|log_stats"
n=$(grep -n "def get_metrics" "$L" | head -1 | cut -d: -f1); [[ -n "$n" ]] && show "$L" "$n" "$((n+20))"
grep -n -E "^def |^class |^    def " "$V/v1/metrics/reader.py" 2>/dev/null | head -30
grepn "$V/v1/metrics/loggers.py" "name=\"vllm:(num_preemptions|num_requests_running|num_requests_waiting|kv_cache_usage_perc|cache_config_info|generation_tokens|prompt_tokens)"
grepn "$V/v1/metrics/loggers.py" "cache_config|log_metrics_info|info_metric|def log\("
hdr "8. SchedulerStats and preemption counting"
S="$V/v1/metrics/stats.py"; grepn "$S" "class |num_running|num_waiting|kv_cache_usage|preempt"
grepn "$V/v1/core/sched/scheduler.py" "preempt|num_preempted"
hdr "9. KV-cache sizing log lines and num_gpu_blocks in the front end"
grep -rn -E "GPU KV cache size|Maximum concurrency|num_gpu_blocks" "$V/v1/core/kv_cache_utils.py" | head -20
grep -rn -E "num_gpu_blocks" "$V/v1/engine/core_client.py" "$V/v1/engine/llm_engine.py" "$V/v1/engine/core.py" "$V/v1/engine/utils.py" 2>/dev/null | head -20
hdr "10. SamplingParams and parallel-sampling seeds"
grepn "$V/sampling_params.py" "ignore_eos|min_tokens|    seed|output_kind|logprobs_mode"
grep -n -E "seed" "$V/v1/engine/parallel_sampling.py" 2>/dev/null | head
hdr "11. LLMEngine add_request / abort_request / step"
grepn "$V/v1/engine/llm_engine.py" "def add_request|def abort_request|def step|def get_metrics|def has_unfinished"
hdr "12. Qwen3.5 GDN state dtype from config (already cited by inference-baseline-v1)"
grepn "$V/model_executor/models/config.py" "class Qwen3_5ForConditionalGenerationConfig|mamba_ssm_dtype"
grepn "$V/model_executor/layers/mamba/mamba_utils.py" "def _mamba_state_dtype|temporal_state_dtype|conv_state_dtype"
INNER
read -r -d '' rinner <<'INNER' || true
set -u
if ls /dev/nvidia* >/dev/null 2>&1; then echo "container sees GPU device nodes"; exit 2; fi
python - <<'PY'
import importlib.util, inspect, sys
import torch, transformers
print("python", sys.version.split()[0], "torch", torch.__version__, "transformers", transformers.__version__)
for m in ("fla", "flash_attn", "flash_attn_interface", "causal_conv1d", "kernels", "triton"):
    spec = importlib.util.find_spec(m)
    print(m, "installed" if spec else "absent", getattr(spec, "origin", None) if spec else "")
import fla
print("fla", getattr(fla, "__version__", "?"))
import transformers.models.qwen3_5.modeling_qwen3_5 as mq
print("== modeling_qwen3_5:", inspect.getsourcefile(mq))
names = [n for n, o in vars(mq).items() if inspect.isclass(o) and o.__module__ == mq.__name__]
print("classes:", names)
for n in names:
    if "GatedDeltaNet" in n or n.endswith("DecoderLayer") or n.endswith("Attention") or "RMSNormGated" in n:
        print(f"######## class {n}")
        print(inspect.getsource(getattr(mq, n)))
for fn in ("torch_causal_conv1d_update", "apply_mask_to_padding_states", "l2norm"):
    if hasattr(mq, fn):
        print(f"######## {fn}"); print(inspect.getsource(getattr(mq, fn)))
for n in names:
    if n.endswith("TextModel"):
        print(f"######## {n}.forward"); print(inspect.getsource(getattr(mq, n).forward))
print("######## module globals that look like kernels")
for k, v in vars(mq).items():
    if any(s in k for s in ("causal_conv1d", "chunk_gated", "recurrent_gated", "FusedRMSNormGated", "is_fast_path")):
        print(k, "=", v)
from fla.ops.gated_delta_rule import chunk_gated_delta_rule, fused_recurrent_gated_delta_rule
print("######## fla chunk_gated_delta_rule", inspect.signature(chunk_gated_delta_rule))
print(inspect.getsourcefile(chunk_gated_delta_rule))
src = inspect.getsource(inspect.getmodule(chunk_gated_delta_rule))
for i, line in enumerate(src.splitlines(), 1):
    if any(s in line for s in ("def ", "initial_state", "final_state", "float32", "dtype", "cu_seqlens", "chunk_gated_delta_rule_fwd_h(")):
        print(f"{i:5d} {line}")
print("######## fla fused_recurrent_gated_delta_rule", inspect.signature(fused_recurrent_gated_delta_rule))
import fla.ops.common.chunk_delta_h as cdh
src = inspect.getsource(cdh)
print("== fla.ops.common.chunk_delta_h:", inspect.getsourcefile(cdh))
for i, line in enumerate(src.splitlines(), 1):
    if any(s in line for s in ("def ", "new_empty", "torch.empty", "dtype", "float32", "b_h", "tl.store(p_h", "h0", "ht")):
        print(f"{i:5d} {line}")
try:
    import fla.modules.convolution as conv
    print("######## fla.modules.convolution:", inspect.getsourcefile(conv))
    for name in ("causal_conv1d", "ShortConvolution"):
        obj = getattr(conv, name, None)
        if obj is not None:
            print(name, inspect.signature(obj) if callable(obj) and not inspect.isclass(obj) else "")
    print(inspect.signature(conv.causal_conv1d))
except Exception as exc:
    print("conv import error", repr(exc))
try:
    from fla.ops.utils import prepare_sequence_ids
    print("prepare_sequence_ids", inspect.signature(prepare_sequence_ids))
except Exception as exc:
    print("prepare_sequence_ids", repr(exc))
try:
    import torch.nn.attention.varlen as vl
    print("######## torch.nn.attention.varlen", [n for n in dir(vl) if not n.startswith("_")])
    print(inspect.signature(vl.varlen_attn)); print((vl.varlen_attn.__doc__ or "")[:2500])
except Exception as exc:
    print("torch varlen", repr(exc))
import transformers.modeling_flash_attention_utils as fau
print("######## flash attention utils:", [n for n in dir(fau) if "pack" in n.lower() or "varlen" in n.lower() or "cu_seq" in n.lower()])
PY
INNER
docker image inspect --format '{{.Id}} {{json .RepoTags}}' "${VLLM_IMAGE}" "${RESEARCH_IMAGE}" > "${G2B_OUT}/images.txt"
{ echo "image ${VLLM_IMAGE}"; docker run "${common[@]}" --entrypoint /bin/sh "${VLLM_IMAGE}" -c "${vinner}"; } > "${G2B_OUT}/vllm-source.txt" 2>&1 || echo "vllm part exit $?"
{ echo "image ${RESEARCH_IMAGE}"; docker run "${common[@]}" --workdir /workspace/cotcodec --entrypoint /bin/sh "${RESEARCH_IMAGE}" -c "${rinner}"; } > "${G2B_OUT}/research-source.txt" 2>&1 || echo "research part exit $?"
echo done
