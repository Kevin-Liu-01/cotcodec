FROM python@sha256:9bb659dc6d5218917236f3711e866a5634bb4c2f208de9d4533aa4863f57c1d3

ARG SOURCE_REVISION
ARG SOURCE_TREE
ARG SOURCE_ARCHIVE_SHA256
ARG DOCTOR_SHA256

RUN python -m pip install --no-cache-dir PyYAML==6.0.2

WORKDIR /opt/agent-recall
COPY source/agent_recall /opt/agent-recall/agent_recall
COPY doctor.py /opt/cotcodec/doctor.py

RUN mkdir /state && chown 65532:65532 /state

LABEL org.opencontainers.image.source="https://github.com/mnardit/agent-recall" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="MIT" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

ENV HOME=/tmp/home \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/agent-recall

USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
