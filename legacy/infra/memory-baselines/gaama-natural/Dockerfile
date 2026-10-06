ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COTCODEC_GAAMA_GIT_SHA
ARG COTCODEC_GAAMA_SOURCE_SHA256

LABEL org.opencontainers.image.source="https://github.com/swarna-kpaul/gaama" \
      org.opencontainers.image.revision="${COTCODEC_GAAMA_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${COTCODEC_GAAMA_SOURCE_SHA256}"

WORKDIR /opt/gaama-source
COPY upstream/ ./

WORKDIR /opt/cotcodec
COPY harness/ ./harness/
COPY doctor.py ./doctor.py

RUN chmod -R a+rX /opt/gaama-source /opt/cotcodec

ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/cotcodec

USER 65532:65532
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
