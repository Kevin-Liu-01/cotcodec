ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COTCODEC_MAGIC_CONTEXT_GIT_SHA
ARG COTCODEC_MAGIC_CONTEXT_SOURCE_SHA256

LABEL org.opencontainers.image.source="https://github.com/cortexkit/magic-context" \
      org.opencontainers.image.revision="${COTCODEC_MAGIC_CONTEXT_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${COTCODEC_MAGIC_CONTEXT_SOURCE_SHA256}"

WORKDIR /opt/magic-context
COPY upstream/ ./
RUN bun install --frozen-lockfile --ignore-scripts

WORKDIR /opt/cotcodec
COPY doctor.ts ./doctor.ts

ENV HOME=/tmp \
    XDG_CACHE_HOME=/tmp/cache \
    XDG_DATA_HOME=/state/xdg \
    MAGIC_CONTEXT_LOG_PATH=/tmp/magic-context.log

USER 65532:65532
ENTRYPOINT ["bun", "/opt/cotcodec/doctor.ts"]
