#!/usr/bin/env bash
#SBATCH --job-name=g2b-srccheck-cpu-2
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:08:00
#SBATCH --no-requeue
# CPU-only (no GRES), read-only source check, second pass, for g2b-state-dtype-v1 (EXPLORATORY):
# the vLLM 0.31.0 Qwen GDN forward (prefill backend choice, decode kernel choice and the state
# store), LLM.get_metrics and the preemption counter; the transformers 5.15 causal-conv fallback,
# Qwen3_5Model wiring and attention-interface registration. Same images as the first pass.
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
show() { echo "== ${1#$V/}:$2-$3"; sed -n "$2,$3p" "$1" | nl -ba -v "$2"; }
Q="$V/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py"
sha256sum "$Q" | sed "s#$V/##"
show "$Q" 86 150
show "$Q" 186 300
n=$(wc -l < "$Q"); show "$Q" 372 "$n"
L="$V/entrypoints/llm.py"; n=$(grep -n "def get_metrics" "$L" | head -1 | cut -d: -f1); show "$L" "$n" "$((n+22))"
E="$V/v1/engine/llm_engine.py"; n=$(grep -n "def get_metrics" "$E" | head -1 | cut -d: -f1); show "$E" "$n" "$((n+10))"
show "$E" 306 340
G="$V/v1/metrics/loggers.py"; show "$G" 500 530; show "$G" 570 590; show "$G" 670 690
grep -n -E "num_preempted_reqs|counter_num_preempted|gauge_scheduler_running|gauge_kv_cache_usage|\.set\(scheduler_stats" "$G" | head -20
show "$V/v1/metrics/reader.py" 1 80
K="$V/v1/core/kv_cache_utils.py"; show "$K" 2440 2475
grep -rn -E "GPU KV cache size" "$V/v1" | head -5
B="$V/v1/attention/backends/gdn_attn.py"; grep -n -E "def |spec|decode|num_decodes|state_dtype" "$B" | head -60
INNER
read -r -d '' rinner <<'INNER' || true
set -u
if ls /dev/nvidia* >/dev/null 2>&1; then echo "container sees GPU device nodes"; exit 2; fi
python - <<'PY'
import inspect
import transformers
import transformers.models.qwen3_5.modeling_qwen3_5 as mq
for name in ("causal_conv1d_fn", "causal_conv1d_update", "torch_chunk_gated_delta_rule"):
    fn = getattr(mq, name)
    print(f"######## {name}: wrapped by", getattr(fn, "__module__", "?"), getattr(fn, "__qualname__", "?"))
    try:
        print(inspect.getsource(fn))
    except Exception as exc:
        print("getsource failed", repr(exc))
    inner = inspect.unwrap(fn)
    if inner is not fn:
        print("-- unwrapped:"); print(inspect.getsource(inner))
    for cell in getattr(fn, "__closure__", None) or ():
        v = cell.cell_contents
        if callable(v):
            print("-- closure callable:", getattr(v, "__module__", "?"), getattr(v, "__qualname__", "?"))
print("######## Qwen3_5Model.__init__ and forward")
print(inspect.getsource(mq.Qwen3_5Model.__init__))
print(inspect.getsource(mq.Qwen3_5Model.forward))
print("######## Qwen3_5ForConditionalGeneration.__init__")
print(inspect.getsource(mq.Qwen3_5ForConditionalGeneration.__init__))
print("######## create_recurrent_attention_mask")
print(inspect.getsource(mq.create_recurrent_attention_mask))
from transformers import AttentionInterface, AttentionMaskInterface
print("######## AttentionInterface.register", inspect.signature(AttentionInterface.register))
import transformers.modeling_utils as mu
print("######## PreTrainedModel.set_attn_implementation", inspect.signature(mu.PreTrainedModel.set_attn_implementation))
src = inspect.getsource(mu.PreTrainedModel.set_attn_implementation)
print(src[:4000])
import transformers.integrations.sdpa_attention as sa
print("######## sdpa_attention_forward"); print(inspect.getsource(sa.sdpa_attention_forward))
import transformers.integrations.hub_kernels as hk
print("######## hub_kernels names", [n for n in dir(hk) if "kernel" in n.lower()][:40])
PY
INNER
{ echo "image ${VLLM_IMAGE}"; docker run "${common[@]}" --entrypoint /bin/bash "${VLLM_IMAGE}" -c "${vinner}"; } > "${G2B_OUT}/vllm-source-2.txt" 2>&1 || echo "vllm part exit $?"
{ echo "image ${RESEARCH_IMAGE}"; docker run "${common[@]}" --workdir /workspace/cotcodec --entrypoint /bin/bash "${RESEARCH_IMAGE}" -c "${rinner}"; } > "${G2B_OUT}/research-source-2.txt" 2>&1 || echo "research part exit $?"
echo done
