# TokenMizer checkpoint lifecycle audit — 2026-08-16

## Verdict

TokenMizer revision `131e3d1569de3e8f70c198ade4e791b47f63dc41` is killed as an active/inactive memory control. It is a representation and context-checkpoint mechanism, not bidirectional item residency, and its restart/change-history and recovery contracts failed a contained lifecycle doctor.

Terminal status: `TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED`.

## Contained method

- Exact MIT source revision/tree `cc5e934078e91b8265d2ac398d35bcef71cf4a3f` and archive `a0f8ad51...`.
- Two clean non-root ARM64 Docker runs with network disabled, read-only root, all capabilities dropped, no new privileges, and no GPU/provider/model calls.
- Fresh-process checkpoint continuation, continuous-versus-restarted graph diffs, repeated manual checkpoint, corrupt-database recovery, session isolation, and scoped-purge surface.
- The first offline attempt also showed that the normal image lazily downloads `o200k_base` at checkpoint time. The discovery image prefetched the asset using tiktoken's upstream expected hash so later runtime calls remained offline.

## Reproduced findings

1. Continuous execution reports only the new node in the second checkpoint diff; after a fresh manager restart, the second diff falsely reports both the old and new nodes as added because prior snapshots are process-local.
2. An exact repeated manual checkpoint creates a second durable checkpoint row; no caller idempotency identity exists.
3. When the SQLite checkpoint database is unreadable, initialization deletes it and recreates an empty database. Both durable checkpoint rows were lost.
4. The public checkpoint manager exposes no session-scoped delete or purge operation.
5. Snapshot content, resume text, and session isolation passed across a normal fresh-process reopen.

## Claim boundary

No context-compaction quality or downstream task utility was evaluated. This result removes TokenMizer from the active/inactive H100 wave. A future context-compaction study may still compare its frozen resume rendering to raw-prefix and rolling-summary controls under a separate preregistered contract after checkpoint idempotency, restart-diff continuity, offline assets, and scoped deletion are addressed.

## Evidence

- Receipt: `research/evidence/memory/tokenmizer-checkpoint-negative-v1.json`
- Artifacts: `data/results/tokenmizer-checkpoint/2026-08-16-local-docker-v1/`
- Stable projection: `5a9cb5226d51b464f20576bbda3de2d3609fa7016dae88c2d2c4bb92a0765f86`
- Image: `sha256:a1827caaef364fcff624b4d61cec6e79f6c883a0e4b6a68955f6f1290f315c34`
