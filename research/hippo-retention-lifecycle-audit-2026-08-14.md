# Hippo Memory retention and lifecycle audit — 2026-08-14

## Decision

Hippo Memory revision `4aeb04c68ff079ff1713c977ac4d2a96757cff44`
is a useful fixed retention/status control, but it is **not** an active/inactive
paging system and is blocked from the H100 actor wave. Two clean, contained CPU
executions reproduced cross-tenant sleep consolidation and plaintext deletion
residue.

This is a negative lifecycle result, not a benchmark-quality result and not a
claim about later Hippo revisions.

## Immutable inputs

- Repository: <https://github.com/kitfunso/hippo-memory>
- Revision: `4aeb04c68ff079ff1713c977ac4d2a96757cff44`
- Git tree: `88d0613e1e5aaec6d1c401c200d5ad3372af0828`
- Deterministic Git archive SHA-256:
  `d966a02bf1c811f191e94fa21317a3a2a3a9797ff7f3da93caa114a794845bb8`
- License: MIT; license SHA-256:
  `c3e197e295e989f797bf994a98ee514179c5ea031320af0823b2bb4c8b05a09d`
- Package lock SHA-256:
  `8faa74fa7fb588dadc67fe8579c605750f14f1bc2a8060c3c81c1de2225ff200`
- Experiment: `experiments/memory/stage3-hippo-retention-cross-tenant-doctor.yaml`
- Tracked evidence:
  `research/evidence/memory/hippo-retention-cross-tenant-v1.json`

## Method

The doctor imported the clean pinned source into a digest-pinned Node 24 Linux
image. Runtime used Docker with network disabled, a read-only root filesystem,
all capabilities dropped, `no-new-privileges`, fixed non-root UID/GID 65532,
one CPU, 768 MiB, and no GPU, model call, embedding, provider key, replay, trace
capture, extraction, or physics pass. A narrowly scoped initialization container
used only `CHOWN` on a fresh named volume so the non-root subject could write its
SQLite state.

Each of two independent named volumes ran three fresh processes: prepare,
restart, and purge. The experiment exercised:

1. the hard-coded 20-item session working-memory cap;
2. one retrieval plus one positive outcome on a retained episodic item;
3. sleep consolidation over overlapping records owned by two tenants;
4. fresh-process restart; and
5. logical deletion followed by a direct SQLite canary scan.

## Reproduced findings

- Working-memory overflow deleted the evicted item; flush did not move it to an
  archive. The implementation therefore has separate stores without a
  bidirectional residency transition.
- Retrieval and a positive outcome increased the same record's retention
  strength. This supports use as a fixed observational-retention control.
- Sleep merged one tenant-A and two tenant-B records into one semantic record
  owned by the default tenant. All three canaries were present and retrievable
  through the default tenant.
- The derived semantic record carried no complete transitive source lineage.
- Fresh-process restart preserved the normalized state exactly.
- Logical deletion reached zero rows, but all five canaries remained as
  plaintext substrings in `hippo.db`.
- Both clean states produced the identical stable-projection SHA-256:
  `2be93ab777f551f57289ced9c24d7c513dffb82b0bd841d7e2250c876ab504fe`.

Terminal status:
`BLOCKED_CROSS_TENANT_CONSOLIDATION_AND_PURGE_RESIDUE_REPRODUCED`.

## Admission rule

Do not allocate H100 time or call this revision active/inactive memory. A later
pin or explicit patch arm must first partition every sleep candidate and derived
record by tenant, preserve transitive source lineage, expose a scoped purge with
zero physical residue, support a configurable active capacity, and demonstrate
real move/demotion and promotion semantics across two fresh restarts. Outcome
feedback, learned rescue, and sleep consolidation must remain separate ablation
arms.

## Limits

The executions were local arm64 development evidence, not externally attested
Slurm runs and not publication artifacts. The doctor deliberately disabled all
model-bearing features, so it evaluates deterministic lifecycle invariants only.
It does not estimate task quality, causal utility, or performance on H100.
