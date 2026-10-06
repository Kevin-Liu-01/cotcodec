FROM node@sha256:0711b541c1c33a8a530ac4f0d391baa9a15b3d804695b1b24a47daa5fb60e74d

ARG COTCODEC_LIGHTMEM2_TREE
ARG COTCODEC_LIGHTMEM2_SOURCE_SHA256
ARG COTCODEC_LIGHTMEM2_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec LightMem2 context-paging admission"
LABEL org.opencontainers.image.source="https://github.com/zjunlp/LightMem2"
LABEL org.opencontainers.image.revision="dfc67e8bc9373ca5b31bb412298565c9d65b29b6"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_LIGHTMEM2_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_LIGHTMEM2_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_LIGHTMEM2_DOCTOR_SHA256}"

WORKDIR /opt/lightmem2/source
COPY upstream/ .
RUN corepack enable \
    && pnpm install --frozen-lockfile \
    && cp -R /root/.cache/node/corepack/v1/pnpm/10.32.1 /opt/pnpm \
    && chmod -R a+rX /opt/pnpm \
    && ln -sf /opt/pnpm/bin/pnpm.cjs /usr/local/bin/pnpm \
    && ln -sf /opt/pnpm/bin/pnpx.cjs /usr/local/bin/pnpx

COPY doctor.ts /opt/cotcodec/doctor.ts

ENV HOME=/tmp/lightmem2-home \
    NODE_ENV=test \
    NO_COLOR=1

USER 65532:65532
ENTRYPOINT ["node", "--import", "tsx", "/opt/cotcodec/doctor.ts"]
