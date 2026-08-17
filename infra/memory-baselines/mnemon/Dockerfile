FROM golang@sha256:ab1d1823abb55a9504d2e3e003b75b36dbeb1cbcc4c92593d85a84ee46becc6c AS sources

ARG MNEMON_REVISION
ARG MNEMON_TREE
ARG MNEMON_ARCHIVE_SHA256
ARG DSH_MNEMON_REVISION
ARG DSH_MNEMON_TREE
ARG DSH_MNEMON_ARCHIVE_SHA256

RUN git init /src/mnemon \
    && git -C /src/mnemon remote add origin https://github.com/mnemon-dev/mnemon \
    && git -C /src/mnemon fetch --depth 1 origin "${MNEMON_REVISION}" \
    && git -C /src/mnemon checkout --detach FETCH_HEAD \
    && test "$(git -C /src/mnemon rev-parse HEAD)" = "${MNEMON_REVISION}" \
    && test "$(git -C /src/mnemon rev-parse HEAD^{tree})" = "${MNEMON_TREE}" \
    && test "$(git -C /src/mnemon archive --format=tar HEAD | sha256sum | cut -d' ' -f1)" = "${MNEMON_ARCHIVE_SHA256}" \
    && git init /src/dsh-mnemon \
    && git -C /src/dsh-mnemon remote add origin https://github.com/omdsh-dev/dsh-mnemon \
    && git -C /src/dsh-mnemon fetch --depth 1 origin "${DSH_MNEMON_REVISION}" \
    && git -C /src/dsh-mnemon checkout --detach FETCH_HEAD \
    && test "$(git -C /src/dsh-mnemon rev-parse HEAD)" = "${DSH_MNEMON_REVISION}" \
    && test "$(git -C /src/dsh-mnemon rev-parse HEAD^{tree})" = "${DSH_MNEMON_TREE}" \
    && test "$(git -C /src/dsh-mnemon archive --format=tar HEAD | sha256sum | cut -d' ' -f1)" = "${DSH_MNEMON_ARCHIVE_SHA256}"

FROM golang@sha256:ab1d1823abb55a9504d2e3e003b75b36dbeb1cbcc4c92593d85a84ee46becc6c AS mnemon-build

WORKDIR /opt/mnemon
COPY --from=sources /src/mnemon .
RUN CGO_ENABLED=0 go build -mod=readonly -trimpath -o /out/mnemon .

FROM node@sha256:0711b541c1c33a8a530ac4f0d391baa9a15b3d804695b1b24a47daa5fb60e74d AS plugin-build

ENV PNPM_HOME=/pnpm
ENV PATH=/pnpm:$PATH
WORKDIR /opt/dsh-mnemon
COPY --from=sources /src/dsh-mnemon .
RUN corepack enable \
    && pnpm install --frozen-lockfile --ignore-scripts \
    && pnpm run build \
    && pnpm prune --prod

FROM node@sha256:0711b541c1c33a8a530ac4f0d391baa9a15b3d804695b1b24a47daa5fb60e74d

ARG MNEMON_REVISION
ARG MNEMON_TREE
ARG MNEMON_ARCHIVE_SHA256
ARG DSH_MNEMON_REVISION
ARG DSH_MNEMON_TREE
ARG DSH_MNEMON_ARCHIVE_SHA256
ARG DOCTOR_SHA256

LABEL org.opencontainers.image.source="https://github.com/mnemon-dev/mnemon" \
      org.opencontainers.image.revision="${MNEMON_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0 AND MIT" \
      org.cotcodec.mnemon-tree="${MNEMON_TREE}" \
      org.cotcodec.mnemon-archive-sha256="${MNEMON_ARCHIVE_SHA256}" \
      org.cotcodec.dsh-mnemon-revision="${DSH_MNEMON_REVISION}" \
      org.cotcodec.dsh-mnemon-tree="${DSH_MNEMON_TREE}" \
      org.cotcodec.dsh-mnemon-archive-sha256="${DSH_MNEMON_ARCHIVE_SHA256}" \
      org.cotcodec.doctor-sha256="${DOCTOR_SHA256}" \
      org.cotcodec.discovery-only="true"

COPY --from=mnemon-build /out/mnemon /usr/local/bin/mnemon
COPY --from=plugin-build /opt/dsh-mnemon/lib /opt/dsh-mnemon/lib
COPY --from=plugin-build /opt/dsh-mnemon/node_modules /opt/dsh-mnemon/node_modules
COPY --from=plugin-build /opt/dsh-mnemon/package.json /opt/dsh-mnemon/package.json
COPY --from=sources /src/mnemon/LICENSE /opt/sources/mnemon/LICENSE
COPY --from=sources /src/mnemon/go.mod /opt/sources/mnemon/go.mod
COPY --from=sources /src/mnemon/go.sum /opt/sources/mnemon/go.sum
COPY --from=sources /src/mnemon/cmd/memory/store.go /opt/sources/mnemon/store.go
COPY --from=sources /src/mnemon/cmd/memory/forget.go /opt/sources/mnemon/forget.go
COPY --from=sources /src/mnemon/internal/memory/store/node.go /opt/sources/mnemon/node.go
COPY --from=sources /src/dsh-mnemon/LICENSE /opt/sources/dsh-mnemon/LICENSE
COPY --from=sources /src/dsh-mnemon/package.json /opt/sources/dsh-mnemon/package.json
COPY --from=sources /src/dsh-mnemon/pnpm-lock.yaml /opt/sources/dsh-mnemon/pnpm-lock.yaml
COPY --from=sources /src/dsh-mnemon/src/memory-bodies.ts /opt/sources/dsh-mnemon/memory-bodies.ts
COPY --from=sources /src/dsh-mnemon/src/service.ts /opt/sources/dsh-mnemon/service.ts
COPY --from=sources /src/dsh-mnemon/src/runner.ts /opt/sources/dsh-mnemon/runner.ts
COPY infra/memory-baselines/mnemon/doctor.mjs /opt/cotcodec/doctor.mjs

USER 65532:65532
ENTRYPOINT ["node", "/opt/cotcodec/doctor.mjs"]
