ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /opt/neo4j-agent-memory
COPY upstream/ ./
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv sync --frozen --no-dev --extra nams

COPY doctor.py /opt/cotcodec/doctor.py
USER 65532:65532
ENTRYPOINT ["/opt/neo4j-agent-memory/.venv/bin/python", "/opt/cotcodec/doctor.py"]
