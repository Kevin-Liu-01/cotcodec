FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_ICARUS_GIT_SHA
ARG COTCODEC_ICARUS_TREE
ARG COTCODEC_ICARUS_SOURCE_SHA256
ARG COTCODEC_ICARUS_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Icarus lifecycle admission"
LABEL org.opencontainers.image.source="https://github.com/esaradev/icarus-memory-infra"
LABEL org.opencontainers.image.revision="6e348708dcddb7cf1ad47726cb287cd4c9183c40"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_ICARUS_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_ICARUS_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_ICARUS_DOCTOR_SHA256}"

WORKDIR /opt/icarus/source
COPY upstream/ .
RUN uv pip install --system '.[dev]'

COPY doctor.py /opt/cotcodec/doctor.py

ENV HOME=/tmp/icarus-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["python"]
