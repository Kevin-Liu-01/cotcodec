ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COTCODEC_ALLMEM_GIT_SHA
ARG COTCODEC_ALLMEM_SOURCE_SHA256
LABEL org.opencontainers.image.source="https://github.com/LvCan926/All-Mem" \
      org.opencontainers.image.revision="${COTCODEC_ALLMEM_GIT_SHA}" \
      org.cotcodec.source-archive-sha256="${COTCODEC_ALLMEM_SOURCE_SHA256}" \
      org.cotcodec.experiment="allmem-topology-recovery-v1" \
      org.cotcodec.publication-ready="false"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/all-mem \
    HOME=/tmp \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN python -m pip install --no-cache-dir --only-binary=:all: \
      numpy==1.24.3 \
      scipy==1.15.3 \
      networkx==3.2.1 \
      scikit-learn==1.6.1 \
      joblib==1.5.1 \
      threadpoolctl==3.6.0 \
      requests==2.32.4

WORKDIR /opt/all-mem
COPY upstream/ ./
COPY doctor.py /opt/cotcodec/doctor.py

RUN python - <<'PY'
from all_mem.core import HashEmbeddingModel
assert HashEmbeddingModel().encode("deterministic doctor").shape == (384,)
PY

USER 65532:65532
ENTRYPOINT ["python", "/opt/cotcodec/doctor.py"]
