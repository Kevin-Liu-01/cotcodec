ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG HERMES_GIT_SHA
ARG HERMES_SOURCE_SHA256

LABEL org.opencontainers.image.source="https://github.com/NousResearch/hermes-agent" \
      org.opencontainers.image.revision="${HERMES_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${HERMES_SOURCE_SHA256}"

WORKDIR /opt/hermes-source
COPY upstream/ ./

WORKDIR /opt/cotcodec
COPY doctor.py ./doctor.py

RUN chmod -R a+rX /opt/hermes-source /opt/cotcodec

ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1

USER 65532:65532
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
