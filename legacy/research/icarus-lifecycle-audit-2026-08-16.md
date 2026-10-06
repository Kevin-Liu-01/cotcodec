# Icarus lifecycle audit — 2026-08-16

## Decision

The exact pinned Icarus revision is a useful manual three-layer lifecycle floor,
but it is **not admitted to an H100 actor or memory-quality experiment**.
Two independent clean-state contained runs ended at:

```text
BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE
```

The result is a negative lifecycle reproduction, not a scientific quality
result and not evidence of autonomous active/inactive paging.

## Immutable source and runtime

- Repository: <https://github.com/esaradev/icarus-memory-infra>
- Commit: `6e348708dcddb7cf1ad47726cb287cd4c9183c40`
- Tree: `fcdbae5db3ed582f679bac2b7348818e20b6e91c`
- Version: `0.3.0`
- License: MIT
- `git archive` tar SHA-256: `e0a396bd48be2f2a30d751ed10d6ab1a2a2c80dda094e6334b33f87045d19c05`
- Runtime: local Linux/arm64 Docker, `--network none`, read-only root,
  all capabilities dropped, `no-new-privileges`, non-root UID/GID 65532,
  one CPU, one GiB, and no model, embedding, API, GPU, or sudo use.
- Image ID: `sha256:bc3dd9e4e9f8048f538c759ffdbaf47787b92fcd2c5c710495283899fb0a1cff`

The repository has no resolved lock. The current contained solve selected MCP
2.0.0 against the upstream `mcp>=1.0` range; the upstream suite produced 207
passes, 6 failures, and 39 skips because `mcp.server.fastmcp` is absent in that
major version. This is a separate reproducibility defect.

## What reproduced twice

- Explicit working-memory findings were archived privately at session end.
- Caller-selected findings were promoted to the shared Markdown wiki.
- Another agent could not see the private attempt; the originating agent could.
- Supersession persisted the replacement and marked the old entry.
- Rollback was non-destructive and persisted.
- Fresh-process restart preserved the private archive, shared wiki, isolation,
  supersession, rollback, and duplicate-promotion state.

These results support only a **manual lifecycle and provenance control**. The
caller chooses promotion; Icarus does not supply a learned or autonomous
residency policy.

## Falsifiers reproduced twice

1. Replaying the same `end_session` request created another private session
   summary and another shared-wiki link. Promotion is not request-idempotent.
2. The public surface exposes no native delete, forget, or scoped purge API.
3. The purge probe retained all four random plaintext canaries: private,
   shared, superseded, and replacement values.

The third-party source was not patched or repaired during this audit.

## Evidence

- Sealed evidence: `research/evidence/memory/icarus-manual-lifecycle-negative-v1.json`
- Evidence SHA-256: `9d476930a05dda1239b38bd35b71388eac3e0030a408a599b2d0b11052b9b6e4`
- Retained report: `data/results/icarus-lifecycle/2026-08-16-local-docker-v1/report.json`
- Report SHA-256: `1dd616442c88ad962262d8e4b7f238bca0d2f99fff418725e1600e170d5372c1`
- Retained manifest: `data/results/icarus-lifecycle/2026-08-16-local-docker-v1/manifest.json`
- Manifest SHA-256: `150979e9f4039b5d0386c1b334205da2808cff60036c0bf3d582479bbef88d3d`
- Stable semantic projection SHA-256: `e8207fbeebfd4e2193f371f4ae41dd653a8cf5bb85decb064feaa29407d9a7d7`

The evidence validator replays all six phase artifacts from the embedded bundle,
checks the exact experiment and code hashes, validates the contained Docker
argv and image labels, and rejects favorable rewrites.

## Admission boundary

The pinned revision may re-enter only as a newer immutable source pin or an
explicit patch arm that passes all of the following under the same doctor:

- a locked dependency graph;
- request-idempotent session close and promotion;
- scoped native deletion or cryptographic erasure;
- fresh-process zero-residue proof;
- preserved archive isolation, supersession, rollback, and restart behavior.

Until then, `h100_actor_admission=forbidden-for-this-revision`.
