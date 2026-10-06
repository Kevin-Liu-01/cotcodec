FROM node:22.21.1-bookworm-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c

ARG COTCODEC_MNEMOSYNE_GIT_SHA
ARG COTCODEC_MNEMOSYNE_TREE
ARG COTCODEC_MNEMOSYNE_SOURCE_SHA256
ARG COTCODEC_MNEMOSYNE_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Mnemosyne Cognitive lifecycle admission"
LABEL org.opencontainers.image.source="https://github.com/28naem-del/mnemosyne"
LABEL org.opencontainers.image.revision="${COTCODEC_MNEMOSYNE_GIT_SHA}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_MNEMOSYNE_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_MNEMOSYNE_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_MNEMOSYNE_DOCTOR_SHA256}"

WORKDIR /opt/mnemosyne/source
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json ./
COPY src ./src
COPY tests ./tests
RUN npm run build && npm run typecheck

COPY .cotcodec/doctor.mjs /opt/cotcodec/doctor.mjs

ENV HOME=/tmp/mnemosyne-home \
    NODE_ENV=production

USER 65534:65534
ENTRYPOINT ["node", "/opt/cotcodec/doctor.mjs"]
