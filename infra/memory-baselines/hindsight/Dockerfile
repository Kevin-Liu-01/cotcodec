# syntax=docker/dockerfile:1.7
ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE}

USER root
COPY --from=hindsight_source . /opt/hindsight-source

WORKDIR /workspace/cotcodec
RUN UV_PROJECT_ENVIRONMENT=/opt/hindsight-runtime \
    uv sync --frozen --project infra/memory-baselines/hindsight \
    && uv pip install \
       --python /opt/hindsight-runtime/bin/python \
       --no-deps \
       /opt/hindsight-source/hindsight-api-slim \
       /opt/hindsight-source/hindsight-clients/python \
       /opt/hindsight-source/hindsight-embed \
       /opt/hindsight-source/hindsight-all \
    && /opt/hindsight-runtime/bin/python -c \
       "import importlib.metadata; assert importlib.metadata.version('hindsight-all') == '0.9.0'; assert importlib.metadata.version('hindsight-api-slim') == '0.9.0'; assert importlib.metadata.version('pg0-embedded') == '0.15.1'"

ENV PYTHONPATH=/workspace/cotcodec \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/opt/hindsight-runtime/bin/python", "/workspace/cotcodec/infra/memory-baselines/hindsight_sidecar.py"]
