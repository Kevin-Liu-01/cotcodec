FROM debian@sha256:817e6cf99d6fc127ff4ffe8580049b60deba0adfbbb2bd65ddc3ef8fbb7aade0

ARG COTCODEC_MEMORIA_GIT_SHA
ARG COTCODEC_MEMORIA_TREE
ARG COTCODEC_MEMORIA_SOURCE_SHA256
ARG COTCODEC_MEMORIA_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Memoria transactional lifecycle admission"
LABEL org.opencontainers.image.source="https://github.com/matrixorigin/Memoria"
LABEL org.opencontainers.image.revision="${COTCODEC_MEMORIA_GIT_SHA}"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_MEMORIA_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_MEMORIA_SOURCE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_MEMORIA_DOCTOR_SHA256}"

COPY cotcodec-memoria-doctor /usr/local/bin/cotcodec-memoria-doctor

ENV HOME=/tmp/home RUST_BACKTRACE=1
USER 65532:65532
ENTRYPOINT ["/usr/local/bin/cotcodec-memoria-doctor", "--nocapture", "--test-threads=1"]
