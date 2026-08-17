FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_PALIMPSEST_GIT_SHA
ARG COTCODEC_PALIMPSEST_TREE
ARG COTCODEC_PALIMPSEST_SOURCE_SHA256
ARG COTCODEC_PALIMPSEST_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Palimpsest bitemporal admission"
LABEL org.opencontainers.image.source="https://github.com/joe51111jwd/palimpsest"
LABEL org.opencontainers.image.revision="0f83e166b0512a5ca9f38c2559f68749b35e994d"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_PALIMPSEST_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_PALIMPSEST_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_PALIMPSEST_DOCTOR_SHA256}"

WORKDIR /opt/palimpsest/source
COPY upstream/ .
RUN uv pip install --system '.[dev]'

COPY doctor.py /opt/cotcodec/doctor.py

ENV HOME=/tmp/palimpsest-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["python"]
