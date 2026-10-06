# syntax=docker/dockerfile:1.7
FROM docker.io/library/python@sha256:77923445c077d8eb971b14b2b114a1d9cd4a87edb4c75654820ca4832ee8cb15

ARG PAST_RUNTIME_CONTRACT_SHA256
ARG PAST_SOURCE_RECEIPT_SHA256

LABEL org.opencontainers.image.title="cotcodec-past-bench-hermes-plus" \
      org.opencontainers.image.source="https://github.com/Gen-Verse/PAST-Bench" \
      org.opencontainers.image.revision="f8223517ae7491e776b69793d9f11e9d074ab42e" \
      org.opencontainers.image.base.name="docker.io/library/python:3.11.15-slim-bookworm" \
      org.opencontainers.image.base.digest="sha256:77923445c077d8eb971b14b2b114a1d9cd4a87edb4c75654820ca4832ee8cb15" \
      org.opencontainers.image.cotcodec-past-runtime-contract-sha256="${PAST_RUNTIME_CONTRACT_SHA256}" \
      org.opencontainers.image.cotcodec-past-source-receipt-sha256="${PAST_SOURCE_RECEIPT_SHA256}" \
      org.opencontainers.image.cotcodec-checkpoint-runtime="episode-boundary-v1" \
      org.opencontainers.image.cotcodec-publication-ready="false"

ENV VIRTUAL_ENV=/opt/past-bench-venv \
    PATH=/opt/past-bench-venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PAST_BENCH_AGENT_REGISTRY=/opt/past-bench/source/configs/agents.yaml \
    PAST_BENCH_RUNTIME_CACHE=/state/runtime-cache \
    HOME=/state/home

RUN python -c \
      'import re,sys; assert re.fullmatch(r"[0-9a-f]{64}", sys.argv[1]); assert re.fullmatch(r"[0-9a-f]{64}", sys.argv[2])' \
      "${PAST_RUNTIME_CONTRACT_SHA256}" "${PAST_SOURCE_RECEIPT_SHA256}" \
    && python -m venv "${VIRTUAL_ENV}"

COPY .cotcodec/requirements.lock /opt/past-bench-lock/requirements.lock
RUN python -m pip install \
      --require-hashes \
      --only-binary=:all: \
      --no-cache-dir \
      --requirement /opt/past-bench-lock/requirements.lock

COPY . /opt/past-bench/source
WORKDIR /opt/past-bench/source

RUN python .cotcodec/prepare_past_bench_runtime.py \
      --context /opt/past-bench/source \
      --verify-only \
      --self-contained \
    && python .cotcodec/apply_checkpoint_overlay.py \
      --source-root /opt/past-bench/source \
      --checkpoint-module /opt/past-bench/source/.cotcodec/checkpoint_runtime.py \
      > /opt/past-bench-lock/checkpoint-overlay.txt \
    && (cd /opt/past-bench/source/.cotcodec \
      && python checkpoint_runtime_selftest.py) \
    && python -m pip install \
      --no-deps \
      --no-build-isolation \
      /opt/past-bench/source \
    && python -m pip install \
      --no-deps \
      --no-build-isolation \
      /opt/past-bench/source/agents/hermes-plus \
    && python -m pytest \
      --override-ini=addopts='-p no:cacheprovider' \
      --junitxml=/opt/past-bench-lock/upstream-tests.xml \
    && python -c \
      'import importlib.metadata as m; assert m.version("past-bench") == "1.0.0"; assert m.version("hermes-plus") == "0.4.0"' \
    && chmod -R a-w /opt/past-bench/source /opt/past-bench-venv /opt/past-bench-lock \
    && chmod -R a+rX /opt/past-bench/source /opt/past-bench-venv /opt/past-bench-lock

WORKDIR /work
ENTRYPOINT ["/opt/past-bench-venv/bin/past-bench"]
CMD ["--help"]
