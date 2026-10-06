ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COTCODEC_ASTRA_GIT_SHA
ARG COTCODEC_ASTRA_SOURCE_SHA256
LABEL org.opencontainers.image.source="https://github.com/cyh7789/astra" \
      org.opencontainers.image.revision="${COTCODEC_ASTRA_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${COTCODEC_ASTRA_SOURCE_SHA256}"

WORKDIR /opt/astra
COPY upstream/ ./
RUN npm ci --ignore-scripts

COPY doctor.ts /opt/astra/cotcodec-doctor.ts
USER 65532:65532
ENTRYPOINT ["node", "--import", "tsx", "/opt/astra/cotcodec-doctor.ts"]
