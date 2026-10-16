#!/usr/bin/env bash
# LM1 host prep: submit the stock llama.cpp CUDA base image build
# (infra/slurm/host-single-node/build-llamacpp-image.sbatch; CPU only, no GRES) from the git
# archive of commit $1, with the llama.cpp source archive staged under $R/llama.cpp-src/.
# Usage: lm1-build-image.sh <commit short id>
set -Eeuo pipefail
source "$(dirname "$0")/lm1-env.sh"
SHORT="${1:?commit short id}"
SRC="$R/src/${SHORT}"
[[ "$(cut -c1-8 "$SRC/.git_sha")" == "${SHORT}" ]] || { echo "source is not ${SHORT}"; exit 2; }
TAR="$R/llama.cpp-src/llama.cpp-620d2225.tar"
ROOT="$R/builds/llamacpp-base-${SHORT}"
[[ ! -e "$ROOT" ]] || { echo "$ROOT exists"; exit 2; }
mkdir -p "$R/builds" /home/kevin/cotcodec-runs/builds
"$(dirname "$0")/lm1-preflight.sh" "llama.cpp image build ${SHORT}"
j=$(sbatch --parsable --export=ALL,COTCODEC_BUILD_SOURCE="$SRC",COTCODEC_LLAMACPP_SOURCE="$TAR",COTCODEC_BUILD_ROOT="$ROOT" \
  --output="$R/ops/slurm-llamacpp-build-%j.out" \
  "$SRC/infra/slurm/host-single-node/build-llamacpp-image.sbatch")
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch printed no job id: '$j'"; exit 2; }
log_job "llama.cpp base image build job $j submitted (CPU only, no GRES; source ${SHORT}; root $(basename "$ROOT"))"
echo "$j"
