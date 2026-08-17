FROM python@sha256:9bb659dc6d5218917236f3711e866a5634bb4c2f208de9d4533aa4863f57c1d3

ARG SOURCE_REVISION
ARG SOURCE_TREE
ARG SOURCE_ARCHIVE_SHA256
ARG DOCTOR_SHA256

RUN python -m pip install --no-cache-dir click==8.2.1 pydantic==2.11.7

WORKDIR /opt/activegraph
COPY source/activegraph /opt/activegraph/activegraph
COPY doctor.py /opt/cotcodec/doctor.py

RUN mkdir /state && chown 65532:65532 /state

LABEL org.opencontainers.image.source="https://github.com/yoheinakajima/activegraph" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

ENV HOME=/tmp/home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/activegraph

USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
