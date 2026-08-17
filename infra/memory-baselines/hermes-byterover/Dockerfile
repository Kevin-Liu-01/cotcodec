FROM node:22.21.1-bookworm-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c

ARG BYTEROVER_REVISION
ARG BYTEROVER_TARBALL_SHA256
ARG HERMES_REVISION

LABEL org.opencontainers.image.source="https://github.com/campfirein/byterover-cli" \
      org.opencontainers.image.revision="${BYTEROVER_REVISION}" \
      org.cotcodec.byterover-tarball-sha256="${BYTEROVER_TARBALL_SHA256}" \
      org.cotcodec.hermes-revision="${HERMES_REVISION}"

COPY raw/baselines/byterover-cli/byterover-cli-3.16.1.tgz /tmp/byterover-cli.tgz
RUN test "$(sha256sum /tmp/byterover-cli.tgz | cut -d' ' -f1)" = "${BYTEROVER_TARBALL_SHA256}" \
    && npm install --global --ignore-scripts /tmp/byterover-cli.tgz \
    && rm /tmp/byterover-cli.tgz \
    && test "$(brv --version)" = "byterover-cli/3.16.1 linux-arm64 node-v22.21.1"

WORKDIR /opt/doctor
COPY raw/baselines/hermes-agent/plugins/memory/byterover/__init__.py ./hermes-byterover.py
COPY infra/memory-baselines/hermes-byterover/doctor.mjs ./doctor.mjs

RUN chmod -R a+rX /opt/doctor /usr/local/lib/node_modules/byterover-cli

ENV HOME=/state/home \
    BRV_DATA_DIR=/state/brv-data \
    NO_COLOR=1

USER node:node
ENTRYPOINT ["node", "/opt/doctor/doctor.mjs"]
