#!/usr/bin/env bash
#SBATCH --job-name=am3g-gate-in-image
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
# Ad hoc, development dry run: inside the dry-run image (no GPU, no network), check that every
# file pinned in section 16 of the image copy of the registration exists with its digest (what the
# post-freeze gate checks), and that the ledger and registration are in the image.
set -Eeuo pipefail
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home \
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --workdir /workspace/cotcodec \
  "$1" python -c "
import sys; sys.path[:0] = [\".\", \"scripts\"]
from pathlib import Path
import memcredit_keepset_search as ks, memcredit_am3g as g
reg = Path(g.REGISTRATION)
print(\"registration in image:\", reg.is_file(), \"ledger in image:\", Path(g.LEDGER).is_file())
print(\"pins:\", ks.check_code_pins(reg, Path(\".\")))
print(\"frozen:\", ks.registration_frozen(Path(g.LEDGER), reg, g.EXPERIMENT))
try:
    g.gate(\"heldout\")
except g.Am3gError as exc:
    print(\"gate refuses (expected before the freeze):\", str(exc)[:120])
"
