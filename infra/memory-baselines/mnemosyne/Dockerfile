FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_MNEMOSYNE_GIT_SHA
ARG COTCODEC_MNEMOSYNE_TREE
ARG COTCODEC_MNEMOSYNE_SOURCE_SHA256
ARG COTCODEC_MNEMOSYNE_LOCK_SHA256
ARG COTCODEC_MNEMOSYNE_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Mnemosyne lifecycle admission"
LABEL org.opencontainers.image.source="https://github.com/mnemosyne-oss/mnemosyne"
LABEL org.opencontainers.image.revision="a0e14243e04dbe3fc29287e58126ff5dc0e02b35"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_MNEMOSYNE_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_MNEMOSYNE_SOURCE_SHA256}"
LABEL org.cotcodec.lock-sha256="${COTCODEC_MNEMOSYNE_LOCK_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_MNEMOSYNE_DOCTOR_SHA256}"

WORKDIR /opt/mnemosyne/source
COPY . .
COPY doctor.py /opt/cotcodec/doctor.py

RUN uv sync --frozen --extra test --no-dev

ENV HOME=/tmp/mnemosyne-home \
    MNEMOSYNE_DATA_DIR=/tmp/mnemosyne-data \
    MNEMOSYNE_NO_EMBEDDINGS=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532

ENTRYPOINT ["/opt/mnemosyne/source/.venv/bin/python"]
