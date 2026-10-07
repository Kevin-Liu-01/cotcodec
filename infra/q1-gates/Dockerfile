# syntax=docker/dockerfile:1.7
# cotcodec-q1-gates: the Q1 gate/audit image, derived from the pinned research image.
#
# Base: cotcodec-research:0b3ecef0-architecture, image ID
# sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29, local
# registry digest below (torch 2.11.0+cu128, Triton 3.6.0, Python 3.12.3, CUDA 12.8,
# compute-sanitizer present). The base is NGC-derived and carries the NVIDIA Deep
# Learning Container License; never push this image to a public registry.
#
# Adds only what the Q1 stack needs:
#   python-dotenv, tomli, pyarrow, ninja  - KernelBench tooling, parquet reads, CUDA
#                                           load_inline for KernelBench's adversarial kernels
#   pydantic-settings==2.10.1, pytest     - test-only: b_native imports the unmodified
#                                           KernelGYM config module; pytest for in-image tests
#   libq1_poison_alloc.so                 - audit A4 dual-poison CUDAPluggableAllocator
#
# KernelGYM, KernelBench-M and other unlicensed code are never copied into this image;
# b_native mounts a scratch clone read-only at run time.
#
# Build (host, through the existing build path; bridge networking has no DNS):
#   docker build --network=host -f infra/q1-gates/Dockerfile \
#     --build-arg GIT_SHA=$(git rev-parse HEAD) -t cotcodec-q1-gates:<sha8> .
ARG BASE_IMAGE=127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d
FROM ${BASE_IMAGE}

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="cotcodec-q1-gates" \
      org.opencontainers.image.revision="${GIT_SHA}" \
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
