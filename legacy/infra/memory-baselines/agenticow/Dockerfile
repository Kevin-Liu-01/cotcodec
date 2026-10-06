FROM node:22.21.1-bookworm-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c

ARG SOURCE_ARCHIVE_SHA256
ARG SOURCE_TREE
ARG SOURCE_REVISION
ARG DOCTOR_SHA256

LABEL org.opencontainers.image.source="https://github.com/ruvnet/agenticow" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="MIT" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

WORKDIR /opt/agenticow
COPY source/ ./
RUN npm ci --omit=dev --ignore-scripts=false \
    && npm cache clean --force \
    && chown -R 65532:65532 /opt/agenticow

COPY --chown=65532:65532 doctor.mjs /opt/cotcodec/doctor.mjs
RUN mkdir -p /state && chown 65532:65532 /state

USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["node", "/opt/cotcodec/doctor.mjs"]
