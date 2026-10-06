FROM python@sha256:ecb0ac954790dd64a0d518d699b9c61a91780c42b0d877c802dbaffd04db66f9

ARG COTCODEC_LIGHTMEM_GIT_SHA
ARG COTCODEC_LIGHTMEM_TREE
ARG COTCODEC_LIGHTMEM_SOURCE_SHA256
ARG COTCODEC_LIGHTMEM_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec LightMem offline consolidation admission"
LABEL org.opencontainers.image.source="https://github.com/zjunlp/LightMem"
LABEL org.opencontainers.image.revision="${COTCODEC_LIGHTMEM_GIT_SHA}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_LIGHTMEM_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_LIGHTMEM_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_LIGHTMEM_DOCTOR_SHA256}"

WORKDIR /opt/lightmem/source
COPY upstream/ .
COPY doctor.py /opt/cotcodec/doctor.py

ENV HOME=/tmp/lightmem-home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
