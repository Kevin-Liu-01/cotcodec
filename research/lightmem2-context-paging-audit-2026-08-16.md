# LightMem2 context-paging lifecycle audit — 2026-08-16

## Decision

Pinned LightMem2 revision `dfc67e8bc9373ca5b31bb412298565c9d65b29b6`
is **not admitted to an H100 actor-quality run**. Its archive-before-pointer-stub
ordering works, but the deployed MCP recovery path searches every session under
the shared state root, archive filenames can collide within one millisecond,
and the artifact-store API has no native scoped purge.

Terminal status:
`BLOCKED_CROSS_SESSION_DISCLOSURE_ARCHIVE_COLLISION_AND_NO_NATIVE_PURGE`.
This is local negative lifecycle evidence with `scientific_result=false` and
`publication_ready=false`; it is not a memory-quality result.

## Immutable source and runtime

- Repository: <https://github.com/zjunlp/LightMem2>
- Revision: `dfc67e8bc9373ca5b31bb412298565c9d65b29b6`
- Tree: `559fbe66aec30fc8920a8d1217712f5673837116`
- Version: `0.1.0-beta.1`
- License: MIT, SHA-256
  `82ae945b07c46324863ffea0c5b269d2cebf724bbb3377e2b2786219430bd02d`
- Git archive SHA-256:
  `973b68b4cf35dcf7fcc29f2c813e8d61f820d71decb391bae9b0bde314f58169`
- Dependency lock SHA-256:
  `c4f920b7aca698dc3b922ec0e4be4a8f5f91a6a1ab49530a73c7bace8fa16235`
- Docker image:
  `sha256:0ecd89daaab43e1e351de5a5c64a437f4b315e65109c45787bdd646dd5afce49`
- Runtime: Linux ARM64, UID/GID `65532:65532`, read-only root, no network,
  all capabilities dropped, no-new-privileges, no GPU, no API/model calls.

The registered relevant upstream suite ran 49 tests: 47 passed and 2 failed.
Both failures are the same package-boundary defect: the MCP product surface
imports undeclared `@lightmem2/kernel`. This audit therefore does not claim the
entire upstream workspace is healthy.

## Reproduced findings

Two independent clean Docker volumes produced an identical semantic projection
with SHA-256
`bb2a508f6053a0ae0a17dc3e3120dc828724d3234dd4bdecb57f4af8d0d6ada1`:

1. Canonical eviction persisted the original task payload before replacing it
   with the pointer stub.
2. The strict lower-level resolver rejected the same key in a different
   session, demonstrating that a safe primitive exists.
3. The actual MCP recovery function called the cross-session resolver and
   recovered session B's canary without accepting a session/tenant parameter.
   The disclosure survived a fresh process restart.
4. Two writes with the same `Date.now()` value and segment ID reused one archive
   path. Both lookup keys remained, but the first key resolved the second
   payload after the overwrite.
5. The public artifact-store surface contained only `archive`, `read`, and
   `resolve`. No native scoped purge existed; both session canaries remained in
   the retained state tar and the other session was still recoverable.

The evidence sealer safely parses both retained state tars, proves both plaintext
canaries remain, proves the overwritten first collision payload does not remain
in the archive files, binds all source/runtime/argv hashes, and recomputes the
two-run projection.

## Claim boundary

Supported:

- archive-before-stub ordering for the exercised canonical eviction path;
- strict per-session lookup as a lower-level control;
- local reproduction of cross-session MCP recovery, collision overwrite, and
  absent native scoped purge at the pinned revision.

Not supported:

- general semantic-memory paging;
- bidirectional active/inactive promotion;
- secure deletion or tenant-safe recovery;
- actor task quality, token savings, or vendor benchmark numbers;
- scientific or publication provenance.

## Admission gate

Only a newer immutable upstream revision or an explicitly labeled repair arm
may re-enter admission. It must bind recovery to the authenticated current
session/tenant, use collision-safe no-overwrite archive identities with content
verification and atomic lookup publication, expose scoped purge or cryptographic
erasure with zero residue, repair the MCP dependency graph, and pass this same
two-clean-state doctor before any H100 actor run.

## Retained evidence

- Bundle: `research/evidence/memory/lightmem2-context-paging-negative-v1.json`
- Bundle SHA-256:
  `1d02c379962b58ed584ad68d9844cba6a5bed9346871c6a12f06c861fa5cb102`
- Raw report SHA-256:
  `97b20714cebf496e993ebc8bbf8ba688cd2e88b68117affe93fd394452709c97`
- Raw manifest SHA-256:
  `c79612bb9925159f9d9ca7d0cf807284aa7a8b5ba6f499328374b105abed9020`
- Upstream relevant-suite output SHA-256:
  `a4b7925a3468cf102c4b12f70688b238ed386299d7785ec49c7330cd64610abc`

Validation:

```bash
uv run python scripts/validate_lightmem2_context_paging_experiment.py
uv run python scripts/seal_lightmem2_context_paging_evidence.py --validate-only
uv run pytest -q tests/test_lightmem2_context_paging_doctor.py
```
