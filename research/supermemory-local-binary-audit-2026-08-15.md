# Supermemory v0.0.3 local-server lifecycle audit

Status: `BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL`

This is a binary-only native lifecycle negative. It is not an open-source server
reproduction, a memory-quality result, a benchmark result, or publication-grade
evidence.

## Bound identities

- Documentation repository: `supermemoryai/supermemory` at
  `82dae50ef458139823b3bfd3ebaaaac90ffd8a7c`.
- Release source commit: `39ef7e1e5ea01b34d2cdd1801d0d227d445a985d`.
- The inspected repository and release trees contain documentation, clients, and
  MCP code, but no local-server implementation.
- Linux arm64 server binary: 214,510,741 bytes, SHA-256
  `167f595afdb6fba3f6ef12e23b31aa99d177684b188376072d4b46f60d3b4d8e`.
- Local embedding model: `Xenova/bge-base-en-v1.5` at
  `4d6cd88e18e51a5e020c2c305726d76ada9c03cf`, with all four consumed files
  hash-bound in the source receipt.
- Doctor image: `sha256:a08e414b959d30b08e781e985a4a6ab28272ae335002bd63ccae18bca41532fa`.

## Execution

Two repetitions used fresh Docker volumes, non-root UID/GID 65532, a read-only
root filesystem, dropped capabilities, `no-new-privileges`, finite CPU/memory/PID
limits, and `--network none`. The model files and doctor code were read-only
mounts. No GPU, API, Slurm, or sudo operation was used.

Each repetition independently exercised:

1. direct create and tenant-scoped search;
2. a versioned update and version-history read;
3. a second tenant;
4. deliberate `SIGKILL` after both writes were acknowledged;
5. fresh-container restart on the retained volume;
6. a separate acknowledged recovery pair followed by graceful stop and restart;
7. soft forget, cross-tenant isolation, and plaintext-at-rest inspection.

## Result

Both repetitions produced the same stable projection:

- direct create/search, versioned update, and history worked before the crash;
- both acknowledged tenants were absent after `SIGKILL` restart;
- the acknowledged version history was absent after `SIGKILL` restart;
- the separately graceful-stopped recovery pair survived a fresh restart;
- no cross-container plaintext disclosure was observed;
- soft-forgotten data disappeared from normal search and list operations;
- the other tenant remained visible;
- provider plaintext was not detected in the retained state;
- the release exposes no native tenant-scoped physical purge contract.

The result isolates crash durability from ordinary graceful persistence: the
server can persist acknowledged data across a graceful stop, but this release did
not preserve the same class of acknowledged writes across the injected hard
crash. The current remote-embedding configuration variables were also ignored by
the v0.0.3 binary, so the doctor pins and supplies the local model instead.

## Evidence and admission

- Raw result root: `data/results/supermemory-local-binary/2026-08-15-doctor-v1/`.
- Raw manifest root:
  `938dd87f02aa45f9d3d9441793c6bc47661634812e1734bb683795ff6fe3ae39`.
- Stable projection:
  `8d9f6a55e132099da9b07c9fc32a62fd88b8d04e7cc8f7523ae4d8894c2b72a0`.
- Tracked evidence:
  `research/evidence/memory/supermemory-local-binary-v1.json`.
- Tracked evidence SHA-256:
  `545791886d57487147d84d2b160f0105eb40ab5450f6802a2c0ec4bfaae0ba61`.

The exact documentation revision and v0.0.3 release are forbidden from H100
promotion. Admission requires either a newer immutable release or an explicit
source-auditable patch that preserves acknowledged writes across `SIGKILL` in two
fresh contained repetitions and provides a tenant-scoped physical-purge or
cryptographic-erasure contract.
