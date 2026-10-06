# syntax=docker/dockerfile:1.7
ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE} AS mempalace-builder

ARG COTCODEC_IMAGE
USER root
RUN python -c \
      'import re,sys; assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", sys.argv[1]), "COTCODEC_IMAGE must be immutable name@sha256"' \
      "${COTCODEC_IMAGE}"
COPY --from=mempalace_source . /opt/mempalace/source
WORKDIR /opt/mempalace/source
RUN test -f .cotcodec-original-dockerignore \
    && rm .dockerignore \
    && mv .cotcodec-original-dockerignore .dockerignore \
    && PYTHONPATH=/workspace/cotcodec \
      python /workspace/cotcodec/scripts/prepare_mempalace_source_context.py \
      --output-dir /opt/mempalace/source \
      --verify-only \
    && test "$(sha256sum benchmarks/longmemeval_bench.py | cut -d' ' -f1)" = \
      "c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d" \
    && test "$(sha256sum uv.lock | cut -d' ' -f1)" = \
      "9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da" \
    && test "$(sha256sum LICENSE | cut -d' ' -f1)" = \
      "81dc6cc278d80f0f1b028ecd86af30d61e441b9ae53d9d9a2ed19389ba657a5d" \
    && test "$(sha256sum pyproject.toml | cut -d' ' -f1)" = \
      "269ebdab137e27db20efdf7a9d0ddb6079e917b44f470b4848f5a2d2309be182" \
    && uv sync --frozen --no-dev --no-editable \
    && .venv/bin/python -c \
      "import importlib.metadata; assert importlib.metadata.version('chromadb') == '1.5.7'; assert importlib.metadata.version('onnxruntime') == '1.24.4'"

ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE}

ARG COTCODEC_IMAGE
ARG MEMPALACE_REVISION=906b918a7c6ebb2a9198a6bf5a78f30a173fea56
ARG MEMPALACE_TREE=98789ad017781f52550b511fcedd9e00c3346761
ARG MEMPALACE_SOURCE_ARCHIVE_SHA256=efbc106cb344a1c5031268909adc2fb5c11cc783ec61adccbe3da0867b4d25c7
ARG MEMPALACE_RUNNER_SHA256=c4b4ba3da9e2d7e0e3f27bc93918877fe5f46e202be9ff98b1e90c7e0124628d
ARG MEMPALACE_UV_LOCK_SHA256=9cea6756cee6b4a4c24d03c23e92116e62479d0d062c1cd3af8da806d1aeb4da
ARG MINILM_ARCHIVE_SHA256=913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3
ARG MINILM_ARTIFACT_ROOT_SHA256

LABEL org.opencontainers.image.title="cotcodec-mempalace-reproduction" \
      org.opencontainers.image.source="https://github.com/MemPalace/mempalace" \
      org.opencontainers.image.revision="${MEMPALACE_REVISION}" \
      org.opencontainers.image.cotcodec-base-reference="${COTCODEC_IMAGE}" \
      org.opencontainers.image.mempalace-tree="${MEMPALACE_TREE}" \
      org.opencontainers.image.mempalace-source-archive-sha256="${MEMPALACE_SOURCE_ARCHIVE_SHA256}" \
      org.opencontainers.image.mempalace-runner-sha256="${MEMPALACE_RUNNER_SHA256}" \
      org.opencontainers.image.mempalace-uv-lock-sha256="${MEMPALACE_UV_LOCK_SHA256}" \
      org.opencontainers.image.minilm-archive-sha256="${MINILM_ARCHIVE_SHA256}" \
      org.opencontainers.image.minilm-artifact-root-sha256="${MINILM_ARTIFACT_ROOT_SHA256}" \
      org.opencontainers.image.cotcodec-publication-ready="false"

USER root
COPY --from=mempalace-builder /opt/mempalace/source /opt/mempalace/source
COPY --from=minilm_model . /data/.cache/chroma/onnx_models/all-MiniLM-L6-v2

ENV HOME=/data \
    PYTHONPATH=/workspace/cotcodec \
    PYTHONUNBUFFERED=1 \
    ANONYMIZED_TELEMETRY=FALSE

WORKDIR /workspace/cotcodec
RUN test -n "${MINILM_ARTIFACT_ROOT_SHA256}" \
    && PYTHONPATH=/workspace/cotcodec \
       /opt/mempalace/source/.venv/bin/python \
       scripts/prepare_chroma_minilm.py \
       --output-dir /data/.cache/chroma/onnx_models/all-MiniLM-L6-v2 \
       --verify-only \
    && test "$(/opt/mempalace/source/.venv/bin/python -c \
      'import json,pathlib; print(json.loads(pathlib.Path("/data/.cache/chroma/onnx_models/all-MiniLM-L6-v2/cotcodec-minilm-receipt.json").read_text(encoding="utf-8"))["artifact_root_sha256"])')" = \
      "${MINILM_ARTIFACT_ROOT_SHA256}" \
    && chmod -R a-w /opt/mempalace/source /data/.cache/chroma \
    && chmod -R a+rX /opt/mempalace/source /data/.cache/chroma

ENTRYPOINT ["/opt/mempalace/source/.venv/bin/python", "/workspace/cotcodec/scripts/run_mempalace_upstream_reproduction.py"]
