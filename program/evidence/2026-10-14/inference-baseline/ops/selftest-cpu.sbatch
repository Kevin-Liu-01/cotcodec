#!/usr/bin/env bash
#SBATCH --job-name=ib-selftest-cpu
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
# CPU-only (no GRES) parse check of inference-baseline-v1 in the overlay: vLLM parsers accept
# every engine, bench serve and bench throughput argv. No model, no GPU, no network.
set -Eeuo pipefail
: "${IB_IMAGE_ID:?}"
: "${IB_OUT:?}"
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
[[ "$(docker info --format "{{.DefaultRuntime}}")" == runc ]] || { echo "runtime not runc" >&2; exit 2; }
common=(--rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=2g --cap-drop ALL
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES=)
nodes="$(docker run "${common[@]}" --entrypoint /bin/sh "${IB_IMAGE_ID}" -c "ls -1 /dev/nvidia* 2>/dev/null || true")"
[[ -z "${nodes}" ]] || { echo "container sees ${nodes}" >&2; exit 2; }
docker run "${common[@]}" "${IB_IMAGE_ID}" python scripts/run_inference_baseline.py selftest > "${IB_OUT}/selftest.json" 2> "${IB_OUT}/selftest.stderr"
docker run "${common[@]}" "${IB_IMAGE_ID}" python -m pytest -q -p no:cacheprovider tests/test_inference_baseline.py > "${IB_OUT}/pytest.txt" 2>&1 || true
echo done
