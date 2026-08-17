FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_TIMEM_GIT_SHA
ARG COTCODEC_TIMEM_TREE
ARG COTCODEC_TIMEM_SOURCE_SHA256
ARG COTCODEC_TIMEM_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec TiMem core runtime admission"
LABEL org.opencontainers.image.source="https://github.com/TiMEM-AI/TiMEM"
LABEL org.opencontainers.image.revision="${COTCODEC_TIMEM_GIT_SHA}"
LABEL org.opencontainers.image.licenses="Apache-2.0-core-only"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_TIMEM_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_TIMEM_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_TIMEM_DOCTOR_SHA256}"

WORKDIR /opt/timem/source
COPY . .
COPY .cotcodec/doctor.py /opt/cotcodec/doctor.py

ENV HOME=/tmp/timem-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["python3", "/opt/cotcodec/doctor.py"]
