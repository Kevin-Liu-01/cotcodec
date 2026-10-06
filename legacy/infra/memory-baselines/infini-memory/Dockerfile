FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG SOURCE_REVISION
ARG SOURCE_TREE
ARG SOURCE_ARCHIVE_SHA256
ARG DOCTOR_SHA256

LABEL org.opencontainers.image.source="https://github.com/infinigence/Infini-Memory" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/infini-memory/src \
    PATH=/opt/infini-memory/.venv/bin:${PATH}

COPY source/ /opt/infini-memory/
WORKDIR /opt/infini-memory
RUN uv sync --frozen --no-dev --no-install-project

COPY doctor.py /opt/cotcodec/doctor.py
RUN mkdir -p /state /opt/cotcodec \
    && chown -R 65532:65532 /state /opt/cotcodec /opt/infini-memory

USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
