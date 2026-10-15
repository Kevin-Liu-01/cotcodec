#!/usr/bin/env bash
#SBATCH --job-name=am3g-pins-in-image
#SBATCH --partition=research
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
# Ad hoc, development dry run: the section 16 pins of a later draft of the registration (mounted
# read-only) against the files inside the dry-run image (no GPU, no network). Expected to differ
# only in files changed after the image commit.
set -Eeuo pipefail
[[ -z "${CUDA_VISIBLE_DEVICES:-}" && -z "${SLURM_JOB_GPUS:-}" ]] || { echo "GPU allocated" >&2; exit 2; }
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=1g --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" --env HOME=/tmp/home \
  --env NVIDIA_VISIBLE_DEVICES=void --env CUDA_VISIBLE_DEVICES= --workdir /workspace/cotcodec \
  --volume "$2:/tmp/registration.md:ro" "$1" python -c "
import sys, hashlib; sys.path[:0] = [\".\", \"scripts\"]
from pathlib import Path
import memcredit_keepset_search as ks
pins = ks.code_pins(Path(\"/tmp/registration.md\"))
missing = [p for p in pins if not Path(p).is_file()]
differ = [p for p in pins if Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest() != pins[p]]
print(\"pins\", len(pins), \"missing in image\", missing, \"differ from the draft\", differ)
"
