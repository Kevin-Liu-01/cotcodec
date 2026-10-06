ARG BASE_IMAGE=cotcodec-research:8c51687b-architecture
FROM ${BASE_IMAGE}

ARG HERMES_GIT_SHA
ARG HERMES_GIT_TREE
ARG HERMES_ARCHIVE_SHA256
ARG PLUGIN_GIT_SHA
ARG PLUGIN_GIT_TREE
ARG PLUGIN_ARCHIVE_SHA256
ARG CORE_GIT_SHA
ARG CORE_GIT_TREE
ARG CORE_ARCHIVE_SHA256

LABEL org.opencontainers.image.source="https://github.com/NousResearch/hermes-agent" \
    org.opencontainers.image.revision="${HERMES_GIT_SHA}" \
    ai.cotcodec.hermes.git_tree="${HERMES_GIT_TREE}" \
    ai.cotcodec.hermes.archive_sha256="${HERMES_ARCHIVE_SHA256}" \
    ai.cotcodec.hermes_observational_memory.git_sha="${PLUGIN_GIT_SHA}" \
    ai.cotcodec.hermes_observational_memory.git_tree="${PLUGIN_GIT_TREE}" \
    ai.cotcodec.hermes_observational_memory.archive_sha256="${PLUGIN_ARCHIVE_SHA256}" \
    ai.cotcodec.observational_memory.git_sha="${CORE_GIT_SHA}" \
    ai.cotcodec.observational_memory.git_tree="${CORE_GIT_TREE}" \
    ai.cotcodec.observational_memory.archive_sha256="${CORE_ARCHIVE_SHA256}" \
    ai.cotcodec.study="hermes-observational-memory-lifecycle-v1"

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/workspace/cotcodec/.venv \
    PATH=/workspace/cotcodec/.venv/bin:${PATH} \
    UV_NO_PROGRESS=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/hermes

WORKDIR /opt/hermes

COPY hermes/ ./
RUN test "${HERMES_GIT_SHA}" = "a90d5369f76c87c98547d2e283aa26d5cfabf322" && \
    test "${HERMES_GIT_TREE}" = "963eb136bfb21fd0b296a40529cbb3575c610874" && \
    /workspace/cotcodec/.venv/bin/python -c \
      'import sys; assert sys.version_info[:2] == (3, 12)'

COPY wheels/ /opt/wheels/
RUN printf '%s  %s\n' \
      d743b32823af544468fc666621850931ae77c0225d8c162db43b878cbdb5f4e4 \
      /opt/wheels/observational_memory-0.10.0-py3-none-any.whl \
      7bd4a95571adadfc271746fa146a4bcfd89c0cf731e49c3d1ad863290adbe8ae \
      /opt/wheels/rank_bm25-0.2.2-py3-none-any.whl \
      e7dd01a46700b1967487141a66ac1a3cf0dd8ebf1f08db37d46389401512ca97 \
      /opt/wheels/numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl \
      ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc \
      /opt/wheels/pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl \
      | sha256sum -c - && \
    uv pip install --python /workspace/cotcodec/.venv/bin/python --no-deps \
      /opt/wheels/numpy-2.4.3-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl \
      /opt/wheels/pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl \
      /opt/wheels/rank_bm25-0.2.2-py3-none-any.whl \
      /opt/wheels/observational_memory-0.10.0-py3-none-any.whl

COPY plugin/ /opt/hermes-observational-memory/
COPY doctor.py /opt/cotcodec/doctor.py
RUN chmod -R a+rX \
      /opt/hermes \
      /opt/hermes-observational-memory \
      /opt/wheels \
      /opt/cotcodec

RUN test "${PLUGIN_GIT_SHA}" = "90d83c1ff768d80f99f4e3ef4d76269f90e1c808" && \
    test "${PLUGIN_GIT_TREE}" = "5cf00ebd8f4d57673469e2e45f3954ac37d875af" && \
    test "${CORE_GIT_SHA}" = "6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208" && \
    test "${CORE_GIT_TREE}" = "96f4288c19b78b0bdda8568efa0c5b1435d64552" && \
    /workspace/cotcodec/.venv/bin/python -c \
      'import importlib.metadata as m; assert m.version("observational-memory") == "0.10.0"; assert m.version("rank-bm25") == "0.2.2"; assert m.version("numpy") == "2.4.3"; assert m.version("pyyaml") == "6.0.3"'

ENTRYPOINT ["/workspace/cotcodec/.venv/bin/python", "/opt/cotcodec/doctor.py"]
