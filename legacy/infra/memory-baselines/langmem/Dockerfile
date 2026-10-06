# syntax=docker/dockerfile:1.7
ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE}

USER root
COPY --from=langmem_source . /opt/langmem-source

WORKDIR /workspace/cotcodec
RUN uv sync --frozen --no-dev --extra memory-langmem --no-install-package langmem \
    && uv pip install \
       --python /workspace/cotcodec/.venv/bin/python \
       --no-deps /opt/langmem-source \
    && /workspace/cotcodec/.venv/bin/python -c \
       "import importlib.metadata; assert importlib.metadata.version('langmem') == '0.0.30'; assert importlib.metadata.version('langgraph') == '1.2.11'"

ENV PYTHONPATH=/workspace/cotcodec \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/workspace/cotcodec/.venv/bin/python", "/workspace/cotcodec/infra/memory-baselines/langmem_sidecar.py"]
