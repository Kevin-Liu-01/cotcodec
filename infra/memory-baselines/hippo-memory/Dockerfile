ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COTCODEC_HIPPO_GIT_SHA
ARG COTCODEC_HIPPO_SOURCE_SHA256
LABEL org.opencontainers.image.source="https://github.com/kitfunso/hippo-memory" \
      org.opencontainers.image.revision="${COTCODEC_HIPPO_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${COTCODEC_HIPPO_SOURCE_SHA256}"

WORKDIR /opt/hippo
COPY upstream/ ./
RUN npm ci --ignore-scripts \
    && npm run build \
    && npm prune --omit=dev

COPY doctor.mjs /opt/cotcodec/doctor.mjs
USER 65532:65532
ENTRYPOINT ["node", "/opt/cotcodec/doctor.mjs"]
