FROM docker.io/library/python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ARG SOURCE_REVISION
ARG SOURCE_TREE
ARG SOURCE_ARCHIVE_SHA256
ARG DOCTOR_SHA256
ARG WHEELHOUSE_MANIFEST_SHA256
ARG REQUIREMENTS_SHA256

LABEL org.opencontainers.image.source="https://github.com/GuyMannDude/mnemo-cortex" \
      org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.licenses="MIT" \
      org.cotcodec.source-tree="${SOURCE_TREE}" \
      org.cotcodec.source-archive-sha256="${SOURCE_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.wheelhouse-manifest-sha256="${WHEELHOUSE_MANIFEST_SHA256}" \
      org.cotcodec.requirements-sha256="${REQUIREMENTS_SHA256}" \
      org.cotcodec.discovery-only="true" \
      org.cotcodec.upstream-container-git="absent"

ENV HOME=/state/home \
    MNEMO_PASSPORT_DIR=/state/passport \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/mnemo

COPY source/ /opt/mnemo/
COPY wheels/ /opt/wheels/
COPY requirements-linux-x86_64-cp312.txt /opt/cotcodec/requirements-linux-x86_64-cp312.txt
COPY wheelhouse-manifest.json /opt/cotcodec/wheelhouse-manifest.json
RUN python -m pip install \
      --no-cache-dir \
      --no-index \
      --find-links=/opt/wheels \
      --require-hashes \
      --requirement /opt/cotcodec/requirements-linux-x86_64-cp312.txt \
    && python -m pip install \
      --no-cache-dir \
      --no-index \
      --find-links=/opt/wheels \
      --no-build-isolation \
      --no-deps \
      /opt/mnemo

COPY doctor.py /opt/cotcodec/doctor.py
RUN mkdir -p /state/home /state/passport /opt/cotcodec \
    && chown -R 65532:65532 /state /opt/cotcodec /opt/mnemo

WORKDIR /opt/mnemo
USER 65532:65532
VOLUME ["/state"]
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
