# syntax=docker/dockerfile:1.7
# cotcodec-q1-gates: the Q1 gate/audit image, derived from the pinned research image, with
# the committed source embedded so the discovery lane can run it directly.
#
# Base: cotcodec-research:0b3ecef0-architecture, image ID
# sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29, local
# registry digest below (torch 2.11.0+cu128, Triton 3.6.0, Python 3.12.3, CUDA 12.8,
# compute-sanitizer present). The base is NGC-derived and carries the NVIDIA Deep
# Learning Container License; never push this image to a public registry (the host's
# 127.0.0.1:5000 registry is private and only gives it a content digest).
#
# Adds only what the Q1 stack needs:
#   python-dotenv, tomli, pyarrow, ninja  - KernelBench tooling, parquet reads, CUDA
#                                           load_inline for KernelBench's adversarial kernels
#   pydantic-settings==2.10.1, pytest     - test-only: b_native imports the unmodified
#                                           KernelGYM config module; pytest for in-image tests
#   libq1_poison_alloc.so                 - audit A4 dual-poison CUDAPluggableAllocator
#   /workspace/cotcodec                   - the committed source at GIT_SHA (the base's
#                                           older source tree is removed; its .venv is kept)
#
# The lane (infra/slurm/host-single-node/docker-research.sbatch) requires the labels
# org.opencontainers.image.revision == the manifest's git_sha and
# org.opencontainers.image.source-tree-sha256 == its source_sha256 (sha256 of
# `git archive --format=tar GIT_SHA`), and /etc/cotcodec-provenance.json with both, so a
# lane job can only run the code this image embeds. No `uv sync` runs here: the base's
# environment is kept as the Q1 tests validated it, plus the packages above.
#
# KernelGYM, KernelBench-M and other unlicensed code are never copied into this image;
# fidelity jobs receive the unmodified clones as a hash-bound study artifact at run time.
#
# Build only through infra/slurm/host-single-node/build-q1-gates-image.sbatch (CPU-only
# Slurm job, clean clone, host networking for PyPI, push to the private local registry).
ARG BASE_IMAGE=127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d
FROM ${BASE_IMAGE}

ARG GIT_SHA=unknown
ARG GIT_TREE=unknown
ARG SOURCE_TREE_SHA256=unknown
ARG BASE_IMAGE_ID=unknown
LABEL org.opencontainers.image.title="cotcodec-q1-gates" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source-tree-sha256="${SOURCE_TREE_SHA256}" \
      org.opencontainers.image.cotcodec-git-sha="${GIT_SHA}" \
      org.opencontainers.image.cotcodec-git-tree="${GIT_TREE}" \
      org.opencontainers.image.cotcodec-runtime-profile="q1-gates" \
      org.opencontainers.image.cotcodec-base-image-id="${BASE_IMAGE_ID}" \
      org.opencontainers.image.cotcodec-dev-dependencies="false" \
      org.opencontainers.image.base.digest="sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d" \
      org.opencontainers.image.source="https://github.com/Kevin-Liu-01/cotcodec" \
      org.cotcodec.license.base="NVIDIA Deep Learning Container License (NGC-derived)"

RUN uv pip install --python /workspace/cotcodec/.venv/bin/python --no-cache \
        python-dotenv==1.1.1 \
        tomli==2.2.1 \
        pyarrow==21.0.0 \
        ninja==1.13.0 \
        pydantic-settings==2.10.1 \
        pytest==8.4.2 \
    && /workspace/cotcodec/.venv/bin/python -c "import torch, triton; assert torch.__version__.startswith('2.11.0'), torch.__version__; assert triton.__version__ == '3.6.0', triton.__version__"

COPY harness/q1/audit/poison_alloc.c /opt/q1/poison_alloc.c
RUN gcc -O2 -Wall -Wextra -shared -fPIC -o /opt/q1/libq1_poison_alloc.so /opt/q1/poison_alloc.c \
        -I/usr/local/cuda/include -L/usr/local/cuda/lib64 -lcudart \
    && sha256sum /opt/q1/poison_alloc.c /opt/q1/libq1_poison_alloc.so > /opt/q1/SHA256SUMS

ENV Q1_POISON_ALLOC_SO_PATH=/opt/q1/libq1_poison_alloc.so

WORKDIR /workspace/cotcodec
RUN test -d /workspace/cotcodec/.venv \
    && find /workspace/cotcodec -mindepth 1 -maxdepth 1 ! -name .venv -exec rm -rf -- {} +
COPY . /workspace/cotcodec
RUN python scripts/check_harness_env.py \
    && python -c "import harness.q1.worker, harness.q1.pilot, harness.q1.study_artifact, harness.q1.gates.kbv_native" \
    && cmp /opt/q1/poison_alloc.c harness/q1/audit/poison_alloc.c \
    && GIT_SHA_VALUE="${GIT_SHA}" SOURCE_SHA_VALUE="${SOURCE_TREE_SHA256}" \
       python infra/research/write_provenance.py /etc/cotcodec-provenance.json \
    && chmod -R a+rX /workspace/cotcodec /etc/cotcodec-provenance.json /opt/q1
