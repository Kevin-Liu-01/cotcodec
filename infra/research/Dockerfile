# syntax=docker/dockerfile:1.7
FROM docker.io/nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_SHA=unknown
ARG SOURCE_TREE_SHA256=unknown
ARG UV_EXTRA=none
ARG INCLUDE_DEV=false

LABEL org.opencontainers.image.title="cotcodec-research" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.source-tree-sha256="${SOURCE_TREE_SHA256}" \
      org.opencontainers.image.cotcodec-runtime-profile="${UV_EXTRA}" \
      org.opencontainers.image.cotcodec-dev-dependencies="${INCLUDE_DEV}" \
      org.opencontainers.image.source="https://github.com/Kevin-Liu-01/cotcodec"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --break-system-packages --no-cache-dir uv==0.11.30

WORKDIR /workspace/cotcodec

RUN mkdir -p /inputs /outputs /cache/huggingface

ENV HF_HOME=/cache/huggingface \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/workspace/cotcodec/.venv \
    PATH=/workspace/cotcodec/.venv/bin:${PATH}

COPY pyproject.toml uv.lock README.md ./
RUN if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"; else dev_flag="--no-dev"; fi \
    && if [ "${UV_EXTRA}" = "none" ]; then \
        uv sync --frozen "${dev_flag}" --no-install-project; \
    else \
        uv sync --frozen "${dev_flag}" --no-install-project --extra "${UV_EXTRA}"; \
    fi

COPY . .
RUN if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"; else dev_flag="--no-dev"; fi \
    && if [ "${UV_EXTRA}" = "none" ]; then \
        uv sync --frozen "${dev_flag}"; \
    else \
        uv sync --frozen "${dev_flag}" --extra "${UV_EXTRA}"; \
    fi \
    && python scripts/check_harness_env.py \
    && GIT_SHA_VALUE="${GIT_SHA}" SOURCE_SHA_VALUE="${SOURCE_TREE_SHA256}" \
       python infra/research/write_provenance.py /etc/cotcodec-provenance.json

CMD ["python", "scripts/check_harness_env.py"]
