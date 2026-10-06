FROM ghcr.io/astral-sh/uv@sha256:d1e005e6f5aac724b7554db95f1c128a77d8d35b59ebe70e188852b4bdad3a3d

ARG COTCODEC_TOKENMIZER_GIT_SHA
ARG COTCODEC_TOKENMIZER_TREE
ARG COTCODEC_TOKENMIZER_SOURCE_SHA256
ARG COTCODEC_TOKENMIZER_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec TokenMizer checkpoint admission"
LABEL org.opencontainers.image.source="https://github.com/Shweta-Mishra-ai/tokenmizer"
LABEL org.opencontainers.image.revision="${COTCODEC_TOKENMIZER_GIT_SHA}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_TOKENMIZER_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_TOKENMIZER_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_TOKENMIZER_DOCTOR_SHA256}"

WORKDIR /opt/tokenmizer/source
COPY . .
COPY .cotcodec/doctor.py /opt/cotcodec/doctor.py
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv sync --no-dev
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN mkdir -p "${TIKTOKEN_CACHE_DIR}" \
    && .venv/bin/python -c "import tiktoken; tiktoken.get_encoding('o200k_base')" \
    && chmod -R a-w "${TIKTOKEN_CACHE_DIR}"

ENV HOME=/tmp/tokenmizer-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["/opt/tokenmizer/source/.venv/bin/python", "/opt/cotcodec/doctor.py"]
