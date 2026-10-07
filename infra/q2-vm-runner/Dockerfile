# GPU-less runner for Q2 VM campaigns (decision D12).
#
# Standard-library Python only: the runner code (harness/q2/vm) is bind-mounted
# read-only at run time and talks to the guest over HTTP and to QEMU's monitor
# over a socket. No CUDA, no torch, no pip packages. Built on the host with
# `docker build --network=host` (bridge DNS is unreliable there) inside a
# CPU-only Slurm job; the resulting local image ID is what manifests pin.
FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -c "import json, socket, urllib.request, hashlib, statistics"

LABEL org.opencontainers.image.title="cotcodec-q2-vm-runner" \
      org.opencontainers.image.licenses="MIT" \
      cotcodec.role="q2-vm-runner" \
      cotcodec.gpu="none"

USER 65534:65534
WORKDIR /src
ENTRYPOINT []
