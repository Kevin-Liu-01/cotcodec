FROM docker.io/library/python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ARG SOURCE_REVISION
ARG SOURCE_TREE
ARG SOURCE_ARCHIVE_SHA256
ARG DOCTOR_SHA256

LABEL org.opencontainers.image.source="https://github.com/Concyclics/MemForest" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="MIT" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/memforest

COPY source/requirements.txt /tmp/memforest-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/memforest-requirements.txt

COPY source/ /opt/memforest/
COPY doctor.py /opt/cotcodec/doctor.py

RUN mkdir -p /state /opt/cotcodec \
    && chown -R 65532:65532 /state /opt/cotcodec /opt/memforest

WORKDIR /opt/memforest
USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
