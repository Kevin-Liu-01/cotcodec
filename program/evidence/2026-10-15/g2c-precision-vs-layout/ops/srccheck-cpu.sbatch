#!/usr/bin/env bash
#SBATCH --job-name=g2c-srccheck-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:08:00
#SBATCH --no-requeue
# CPU-only (no GRES), read-only source check for g2c-precision-layout-v1 (EXPLORATORY): how
# vLLM 0.31.0 chooses the hybrid attention block size for a GDN model, whether a user-set
# block_size is kept or overridden, how the GDN (mamba) page is padded to the attention page,
# and how the attention kernel block size is chosen. Image: G2b's vLLM overlay (git ef7ee50c,
# vLLM 0.31.0), which ran G2b's rollouts. No model weights, no GPU, no network; read-only root.
set -Eeuo pipefail
: "${G2C_OUT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
VLLM_IMAGE=sha256:f86cd2c181940e9db5c49930750d6bcd496e532af2fa0401024675d372592ff1
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --env USER=cotcodec
  --env TRITON_CACHE_DIR=/tmp/triton --env TORCHINDUCTOR_CACHE_DIR=/tmp/inductor
  --label "cotcodec.slurm_job=${SLURM_JOB_ID}")
read -r -d '' vinner <<'INNER' || true
set -u
if ls /dev/nvidia* >/dev/null 2>&1; then echo "container sees GPU device nodes"; exit 2; fi
V=/usr/local/lib/python3.12/dist-packages/vllm
echo "== vllm $(sed -n 's/^__version__ = version = //p' "$V/_version.py")"
# Print the function (or class) enclosing each line that matches a pattern, with line numbers.
enclosing() {  # <pattern> <file...>
  python3 - "$@" <<'PY'
import ast, re, sys
pattern, files = sys.argv[1], sys.argv[2:]
root = "/usr/local/lib/python3.12/dist-packages/vllm/"
for path in files:
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()
    hits = [i + 1 for i, line in enumerate(lines) if re.search(pattern, line)]
    if not hits:
        continue
    tree = ast.parse(text)
    nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    shown = set()
    for hit in hits:
        best = None
        for n in nodes:
            start = min([n.lineno] + [d.lineno for d in n.decorator_list])
            if start <= hit <= n.end_lineno and (best is None or n.end_lineno - start < best[1] - best[0]):
                best = (start, n.end_lineno)
        span = best or (max(1, hit - 15), min(len(lines), hit + 15))
        if span in shown:
            continue
        shown.add(span)
        print(f"== {path.replace(root, '')}:{span[0]}-{span[1]} (pattern {pattern!r}, hit line {hit})")
        for k in range(span[0], span[1] + 1):
            print(f"{k:6d}\t{lines[k - 1]}")
PY
}
grepr() { echo "== grep -rn $1 (vllm/)"; grep -rn -E "$1" "$V" --include=*.py | sed "s#$V/##" | head -"${2:-40}"; }
echo; echo "######## 1. where the hybrid attention block size is set and the mamba page padded"
grepr "Setting attention block size|Padding mamba page size" 10
files=$(grep -rl -E "Setting attention block size|Padding mamba page size" "$V" --include=*.py)
for f in $files; do sha256sum "$f" | sed "s#$V/##"; done
enclosing "Setting attention block size|Padding mamba page size" $files
echo; echo "######## 2. user_specified_block_size, _block_size_resolved, effective_attention_block_size"
grepr "user_specified_block_size|_block_size_resolved|effective_attention_block_size" 60
C="$V/config/cache.py"; sha256sum "$C" | sed "s#$V/##"
echo "== grep config/cache.py: block_size|BlockSize|page_size_padded"
grep -n -E "block_size|BlockSize|page_size_padded" "$C" | head -60
enclosing "user_specified_block_size = |_block_size_resolved =|def effective_attention_block_size" "$C"
echo; echo "######## 3. the CLI / EngineArgs block_size"
A="$V/engine/arg_utils.py"; sha256sum "$A" | sed "s#$V/##"
echo "== grep engine/arg_utils.py: block.size"
grep -n -E "block.size" "$A" | head -40
echo; echo "######## 4. platform hook (cuda) and callers of the hybrid update"
P="$V/platforms/cuda.py"; sha256sum "$P" | sed "s#$V/##"
echo "== grep platforms/cuda.py: block_size"; grep -n -E "block_size" "$P" | head -40
I="$V/platforms/interface.py"; [[ -f "$I" ]] && { sha256sum "$I" | sed "s#$V/##"; echo "== grep platforms/interface.py: def |block_size"; grep -n -E "def .*block|block_size" "$I" | head -60; }
grepr "update_block_size_for_backend|verify_and_update_config\(|_align_hybrid_block_size|HybridAttentionMambaModelConfig" 40
echo; echo "######## 5. attention kernel block size (logical block split for the kernel)"
grepr "kernel_block_size|get_supported_kernel_block_sizes|kv lcm block sizes" 60
enclosing "kv lcm block sizes" "$V/v1/core/kv_cache_utils.py"
echo; echo "######## 6. the GDN (mamba) spec page size and padding"
K="$V/v1/kv_cache_interface.py"; sha256sum "$K" | sed "s#$V/##"
enclosing "page_size_padded" "$K"
echo; echo "######## 7. flash-attn backend supported kernel block sizes"
for f in "$V/v1/attention/backends/flash_attn.py"; do
  [[ -f "$f" ]] && { sha256sum "$f" | sed "s#$V/##"; enclosing "def get_supported_kernel_block_sizes|MultipleOf" "$f"; }
done
INNER
{ echo "image ${VLLM_IMAGE}"; docker run "${common[@]}" --entrypoint /bin/bash "${VLLM_IMAGE}" -c "${vinner}"; } > "${G2C_OUT}/vllm-block-size-source.txt" 2>&1 || echo "vllm part exit $?"
echo done
