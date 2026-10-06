FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_RECMEM_GIT_SHA
ARG COTCODEC_RECMEM_TREE
ARG COTCODEC_RECMEM_SOURCE_SHA256
ARG COTCODEC_RECMEM_LOCK_SHA256
ARG COTCODEC_RECMEM_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec RecMem consolidation admission"
LABEL org.opencontainers.image.source="https://github.com/CaiusDai/RecMem"
LABEL org.opencontainers.image.revision="${COTCODEC_RECMEM_GIT_SHA}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_RECMEM_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_RECMEM_SOURCE_SHA256}"
LABEL org.cotcodec.lock-sha256="${COTCODEC_RECMEM_LOCK_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_RECMEM_DOCTOR_SHA256}"

WORKDIR /opt/recmem/source
COPY . .
COPY .cotcodec/doctor.py /opt/cotcodec/doctor.py
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv sync --frozen --no-dev

ENV HOME=/tmp/recmem-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["/opt/recmem/source/.venv/bin/python", "/opt/cotcodec/doctor.py"]
