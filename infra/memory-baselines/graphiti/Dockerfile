# syntax=docker/dockerfile:1.7
ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE}

USER root
COPY --from=graphiti_source . /opt/graphiti-source

WORKDIR /workspace/cotcodec
RUN uv sync --frozen --no-dev --extra memory-graphiti --no-install-package graphiti-core \
    && uv pip install \
       --python /workspace/cotcodec/.venv/bin/python \
       --no-deps /opt/graphiti-source \
    && /workspace/cotcodec/.venv/bin/python -c \
       "import importlib.metadata; assert importlib.metadata.version('graphiti-core') == '0.29.3'; assert importlib.metadata.version('falkordblite') == '0.10.0'"

ENV PYTHONPATH=/workspace/cotcodec \
    PYTHONUNBUFFERED=1 \
    EMBEDDING_DIM=384

ENTRYPOINT ["/workspace/cotcodec/.venv/bin/python", "/workspace/cotcodec/infra/memory-baselines/graphiti_sidecar.py"]
