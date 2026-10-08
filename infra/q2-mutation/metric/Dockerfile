# OSWorld metric runtime for the Q2 evaluator-mutation harness.
#
# /opt/venv-lock   primary: OSWorld uv.lock at b138d348 exported for Python 3.12
#                  (pandas 3.0.1), installed with --require-hashes --no-deps.
#                  Only the local agent client agp-client is left out.
# /opt/venv-scout  dependency-sensitivity arm: the scoping venv's exact package
#                  versions (pandas 2.3.3, torch 2.5.1+cpu), --no-deps.
#
# The container runs GPU-less (D12); torch's CUDA libraries in venv-lock are
# installed because the lock pins them, never used.
FROM ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl file netpbm ffmpeg \
      libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
ARG UV_VERSION=0.11.30
ARG UV_SHA256=04bc7d180d6138bf6dc08387acf507a823f397a98fea55da36b0ccc7fbce3b68
RUN curl -fsSL -o /tmp/uv.tgz \
      "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" \
 && echo "${UV_SHA256}  /tmp/uv.tgz" | sha256sum -c - \
 && tar -xzf /tmp/uv.tgz -C /usr/local/bin --strip-components=1 \
 && rm /tmp/uv.tgz
ENV UV_PYTHON_INSTALL_DIR=/opt/python UV_CACHE_DIR=/tmp/uv-cache UV_NO_CONFIG=1 \
    UV_PYTHON_PREFERENCE=only-managed
RUN uv python install 3.12.13
COPY osworld-lock-export.txt scout-venv-freeze.txt venv_fingerprint.py /opt/q2/
RUN uv venv --python 3.12.13 /opt/venv-lock \
 && uv pip install --python /opt/venv-lock/bin/python --require-hashes --no-deps \
      -r /opt/q2/osworld-lock-export.txt \
 && rm -rf /tmp/uv-cache
RUN uv venv --python 3.12.13 /opt/venv-scout \
 && uv pip install --python /opt/venv-scout/bin/python --no-deps \
      --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      -r /opt/q2/scout-venv-freeze.txt \
 && rm -rf /tmp/uv-cache
RUN for v in lock scout; do \
      /opt/venv-$v/bin/python /opt/q2/venv_fingerprint.py > /opt/q2/venv-$v.fingerprint.json; \
    done \
 && sha256sum /opt/q2/osworld-lock-export.txt /opt/q2/scout-venv-freeze.txt > /opt/q2/requirements.sha256
ENV MPLCONFIGDIR=/tmp/mpl XDG_CACHE_HOME=/tmp/cache PYTHONDONTWRITEBYTECODE=1
