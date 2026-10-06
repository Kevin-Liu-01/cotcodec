FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b

ARG HERMES_GIT_SHA
ARG HERMES_GIT_TREE
ARG TARGETARCH

LABEL org.opencontainers.image.source="https://github.com/NousResearch/hermes-agent" \
    org.opencontainers.image.revision="${HERMES_GIT_SHA}" \
    ai.cotcodec.hermes.git_tree="${HERMES_GIT_TREE}" \
    ai.cotcodec.study="hermes-memory-provider-conformance-v1"

ENV UV_PYTHON=3.13 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/hermes

# Resolve the exact upstream lock before copying the source so ordinary code
# changes do not invalidate the dependency layer.
COPY pyproject.toml uv.lock LICENSE ./
# Upstream excludes Markdown from Docker contexts, while pyproject.toml names
# README.md as package metadata. Match the official image's placeholder step.
RUN touch README.md && \
    uv sync --frozen --extra dev --extra hindsight --no-install-project

COPY . .
RUN test "${HERMES_GIT_SHA}" = "a90d5369f76c87c98547d2e283aa26d5cfabf322" && \
    test "${HERMES_GIT_TREE}" = "963eb136bfb21fd0b296a40529cbb3575c610874" && \
    uv sync --frozen --extra dev --extra hindsight && \
    case "${TARGETARCH}" in \
      arm64) MEMORI_WHEEL="https://files.pythonhosted.org/packages/e8/45/42a8ab0face6187a2afae6cf9f75cc9317c2aa8e69915a4a57e53ce60ad6/memori-3.3.6-cp310-abi3-manylinux_2_28_aarch64.whl#sha256=85e216a3b264a78693e11498d794c92dabdefaf55f78fa031dc834366f337a5b" ;; \
      amd64) MEMORI_WHEEL="https://files.pythonhosted.org/packages/ef/c1/70cd163eaf1983695a5f6fe92af79d19f3ff90561d16cfcd6847b23b8512/memori-3.3.6-cp310-abi3-manylinux_2_28_x86_64.whl#sha256=96405cd5095f51cbc69b565726a9938bf5cb6adc16d8834652be35e58586e483" ;; \
      *) echo "unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    uv pip install \
      "https://files.pythonhosted.org/packages/38/82/eb5e101b151e5f9122d3fc388f59c16249a6ada21465357ab779fa32815b/hermes_memori-0.1.8-py3-none-any.whl#sha256=d15840b7e4ce791c348e0e4ec366f05f221779df7a37815a6305b232b84e631f" \
      "${MEMORI_WHEEL}" \
      botocore==1.43.72 \
      faiss-cpu==1.15.0 \
      grpcio==1.83.0 \
      jmespath==1.1.0 \
      numpy==2.5.2 \
      protobuf==5.29.6 \
      pyfiglet==1.0.4

ENTRYPOINT ["/opt/hermes/.venv/bin/python", "-m", "pytest"]
CMD ["-q", "tests/plugins/memory"]
