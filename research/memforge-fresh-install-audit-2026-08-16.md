# MemForge Fresh-Install Admission Audit — 2026-08-16

## Verdict

`MEMFORGE_FRESH_INSTALL_ADMISSION_KILLED`

The exact pinned MemForge revision cannot initialize its canonical PostgreSQL
schema. This is a CPU/container admission failure, not a memory-quality result.
H100 actor work is forbidden for this revision.

## Bound source and runtime

- Repository: `https://github.com/salishforge/memforge`
- Commit: `16e2f15c5881a38911f64ca81b3dc0b25d6207ec`
- Tree: `97411a5c0318c3f4b1d273ab0696b915184fca3a`
- Git archive SHA-256: `e2f588676aa06e95cb07cc20224e336a1ce7ff1b9b5757fa808f57323b4b0b93`
- Canonical schema SHA-256: `95ee46167dcbaf7617669e7720680978f640f6ae7cf4b37cad32f5d5db82779f`
- Official Compose image: `postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685`
- pgvector control: `pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`

Both lanes ran twice from clean ephemeral data directories with network
disabled, a read-only root filesystem, all capabilities dropped,
`no-new-privileges`, explicit non-root UIDs, bounded CPU/memory/PIDs, no
provider secrets, no model calls, and no GPU.

## Reproduced blockers

1. The repository's Compose image is plain PostgreSQL 16. The exact schema
   stops at line 14 because the `vector` extension is unavailable.
2. The digest-pinned pgvector control passes extension creation, then stops at
   line 57 because it creates `warm_tier_occurred_idx` before the `warm_tier`
   table begins at line 73.
3. All four fresh-install attempts exited with code 3 and the registered error
   markers. No attempt completed initialization.

## Claim boundary

This evidence does not evaluate hot-to-warm consolidation, warm-to-cold
triage, cold restore, graph retrieval, memory quality, or a repaired schema.
Any reordered-schema or other patched run is a separate intervention and needs
its own preregistered contract. The unpatched revision cannot enter an H100
actor wave.

## Evidence

- Artifact root: `data/results/memforge-fresh-install/2026-08-16-local-docker-v1`
- Evidence receipt: `research/evidence/memory/memforge-fresh-install-negative-v1.json`
- Validator: `scripts/validate_memforge_fresh_install_evidence.py`
