FROM rust@sha256:867f1d1162913c401378a8504fb17fe2032c760dc316448766f150a130204aad

ARG COTCODEC_SHODH_REVISION
ARG COTCODEC_SHODH_TREE
ARG COTCODEC_SHODH_ARCHIVE_SHA256
ARG COTCODEC_SHODH_DOCTOR_SHA256

LABEL org.opencontainers.image.title="CoTCodec Shodh Memory tier admission"
LABEL org.opencontainers.image.source="https://github.com/varun29ankuS/shodh-memory"
LABEL org.opencontainers.image.revision="${COTCODEC_SHODH_REVISION}"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.cotcodec.discovery-only="true"
LABEL org.cotcodec.source-tree="${COTCODEC_SHODH_TREE}"
LABEL org.cotcodec.source-archive-sha256="${COTCODEC_SHODH_ARCHIVE_SHA256}"
LABEL org.cotcodec.doctor-sha256="${COTCODEC_SHODH_DOCTOR_SHA256}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       clang \
       cmake \
       g++ \
       libclang-dev \
       libssl-dev \
       make \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/shodh
COPY upstream/ .
COPY doctor.rs src/bin/cotcodec_shodh_doctor.rs

ENV SHODH_OFFLINE=true \
    SHODH_ALLOW_SIMPLIFIED_EMBEDDINGS=1 \
    CARGO_NET_OFFLINE=true \
    CARGO_BUILD_JOBS=1 \
    CARGO_INCREMENTAL=0 \
    CARGO_PROFILE_DEV_DEBUG=0 \
    CXXFLAGS="-g0" \
    HOME=/tmp/shodh-home

# The network-enabled image build resolves only the checked-in Cargo.lock.
# Measured executions call the prebuilt doctor with network disabled. Upstream
# tests are compiled and run one at a time in bounded child containers so a
# test-link OOM cannot prevent retaining the admission image and its receipt.
RUN CARGO_NET_OFFLINE=false cargo build --locked --bin cotcodec_shodh_doctor

USER 65532:65532
ENTRYPOINT ["/bin/sh", "-c"]
