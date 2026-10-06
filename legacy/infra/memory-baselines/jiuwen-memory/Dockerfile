# syntax=docker/dockerfile:1.7
ARG COTCODEC_BASE_IMAGE
FROM ${COTCODEC_BASE_IMAGE}

ARG COTCODEC_DOCTOR_SHA256
ARG COTCODEC_SOURCE_ARCHIVE_SHA256
ARG COTCODEC_SOURCE_TREE

USER root
COPY jiuwen-source/ /opt/jiuwen-memory/
COPY lifecycle_doctor.py /opt/cotcodec/lifecycle_doctor.py

WORKDIR /opt/jiuwen-memory
RUN test "$(sha256sum uv.lock | cut -d' ' -f1)" = \
      "e2a62926d1fd01ad9ecf4a8b305791146bace9ddac5ed941a95490ab66a85d0c" \
    && uv sync --frozen --no-dev --extra sqlite \
    && uv pip install --python .venv/bin/python --no-deps \
      gmssl==3.2.2 pycryptodomex==3.23.0 sqlite-vec==0.1.9 \
    && test "$(sha256sum /opt/cotcodec/lifecycle_doctor.py | cut -d' ' -f1)" = \
      "$COTCODEC_DOCTOR_SHA256" \
    && .venv/bin/python -c \
      "import importlib.metadata as m; assert m.version('gmssl') == '3.2.2'; assert m.version('pycryptodomex') == '3.23.0'; assert m.version('sqlite-vec') == '0.1.9'"

RUN mkdir -p /state /tmp/home \
    && chown -R 65532:65532 /state /tmp/home /opt/cotcodec /opt/jiuwen-memory

LABEL org.opencontainers.image.source="https://github.com/openJiuwen-ai/agent-memory" \
      org.opencontainers.image.revision="600432b55e480bec5948ee40089884ccf15a7c5d" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.cotcodec.source-tree="$COTCODEC_SOURCE_TREE" \
      org.cotcodec.source-archive-sha256="$COTCODEC_SOURCE_ARCHIVE_SHA256" \
      org.cotcodec.doctor-sha256="$COTCODEC_DOCTOR_SHA256" \
      org.cotcodec.discovery-only="true" \
      org.cotcodec.repair-overlay="gmssl==3.2.2,pycryptodomex==3.23.0,sqlite-vec==0.1.9"

ENV HOME=/tmp/home \
    PYTHONPATH=/opt/jiuwen-memory \
    PYTHONUNBUFFERED=1

VOLUME ["/state"]
USER 65532:65532
WORKDIR /tmp
ENTRYPOINT ["/opt/jiuwen-memory/.venv/bin/python", "/opt/cotcodec/lifecycle_doctor.py"]
