# syntax=docker/dockerfile:1.7
ARG COTCODEC_IMAGE
FROM ${COTCODEC_IMAGE}

USER root
COPY --from=mem0_source . /opt/mem0-source

WORKDIR /workspace/cotcodec
RUN uv sync --frozen --no-dev --extra memory-mem0 --no-install-package mem0ai \
    && uv pip install \
       --python /workspace/cotcodec/.venv/bin/python \
       --no-deps /opt/mem0-source \
    && /workspace/cotcodec/.venv/bin/python -c \
       "import importlib.metadata; assert importlib.metadata.version('mem0ai') == '2.0.18'"

ENV MEM0_TELEMETRY=false \
    PYTHONPATH=/workspace/cotcodec \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/workspace/cotcodec/.venv/bin/python", "/workspace/cotcodec/infra/memory-baselines/mem0_sidecar.py"]
