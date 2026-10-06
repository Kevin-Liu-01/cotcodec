# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=docker.io/library/python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7
FROM ${BASE_IMAGE}

ARG BASE_IMAGE
ARG COTCODEC_CODE_SHA256
ARG TORCH_CPU_WHEEL_SHA256=70ecb2659af6373b7c5336e692e665605b0201ea21ff51aaea47e1d75ea6b5aa

LABEL org.opencontainers.image.title="cotcodec-reasoningbank-frozen-bank-doctor" \
      org.opencontainers.image.source="https://github.com/Kevin-Liu-01/cotcodec" \
      org.opencontainers.image.cotcodec-code-sha256="${COTCODEC_CODE_SHA256}" \
      org.opencontainers.image.cotcodec-torch-cpu-wheel-sha256="${TORCH_CPU_WHEEL_SHA256}" \
      org.opencontainers.image.cotcodec-scientific-result="false" \
      org.opencontainers.image.cotcodec-base-image="${BASE_IMAGE}"

WORKDIR /opt/cotcodec
ENV HOME=/tmp \
    HF_HOME=/tmp/huggingface \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/cotcodec

RUN python -m pip install --no-cache-dir \
      "https://download-r2.pytorch.org/whl/cpu/torch-2.11.0%2Bcpu-cp312-cp312-manylinux_2_28_aarch64.whl#sha256=${TORCH_CPU_WHEEL_SHA256}" \
    && python -m pip install --no-cache-dir --index-url https://pypi.org/simple \
      httpx==0.28.1 \
      pydantic==2.13.4 \
      pyyaml==6.0.3 \
      transformers==5.15.0

COPY harness/__init__.py ./harness/__init__.py
COPY harness/memory_trials/__init__.py ./harness/memory_trials/__init__.py
COPY harness/memory_trials/schema.py ./harness/memory_trials/schema.py
COPY harness/memory_trials/systems.py ./harness/memory_trials/systems.py
COPY harness/memory_trials/dense_control.py ./harness/memory_trials/dense_control.py
COPY harness/memory_trials/procedural_bank.py ./harness/memory_trials/procedural_bank.py
COPY scripts/fetch_open_model.py ./scripts/fetch_open_model.py
COPY scripts/run_hf_embedding_server.py ./scripts/run_hf_embedding_server.py
COPY scripts/dense_bge_factory.py ./scripts/dense_bge_factory.py
COPY scripts/run_reasoningbank_frozen_bank_doctor.py ./scripts/run_reasoningbank_frozen_bank_doctor.py
COPY models/registry.yaml ./models/registry.yaml

RUN chmod -R a+rX /opt/cotcodec

ENTRYPOINT ["python", "/opt/cotcodec/scripts/run_reasoningbank_frozen_bank_doctor.py"]
