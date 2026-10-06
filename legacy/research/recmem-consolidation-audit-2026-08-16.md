# RecMem consolidation lifecycle audit — 2026-08-16

## Verdict

RecMem revision `a84252f6e5587fd4a8caac03ec9f6c732b7a7f35` is blocked from an H100 quality actor. Two clean, network-disabled Docker repetitions reproduced the same lifecycle defects. This is a negative mechanism/admission result, not a memory-quality result.

Terminal status: `BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE`.

## What was tested

- Exact MIT-licensed Git revision and tree `46d131594833547b275cf278db665976dc63b2f1`.
- Deterministic local Qdrant, embedding, and memory-operation test doubles; zero provider or model-backend calls.
- Two fresh container states with read-only root, non-root user, all capabilities dropped, no new privileges, and no network.
- Duplicate retry, recurrence-trigger lineage, failed replacement atomicity, conversation isolation, and fresh-process restart.

## Reproduced findings

1. Repeating an identical write creates a second durable raw record. The public add path has no caller-owned idempotency identity.
2. The write that triggers consolidation appears in the rendered episodic text but is absent from the episode's native `raw_ids` lineage.
3. Episodic replacement removes the prior record before embedding the replacement. An injected replacement-embedding failure loses the prior episode and falls back to a raw write.
4. A successful consolidation survives fresh-process reopen, and isolated conversations stayed isolated in this doctor.

## Claim boundary and next gate

The run does not evaluate recurrence quality or downstream task utility. It establishes that this revision cannot safely enter an actor comparison because its write and replacement semantics can duplicate or lose durable state and cannot fully attribute the resulting episode.

Admit only a newer immutable revision or an explicitly labeled repair arm that adds caller-owned idempotency keys, atomic replace-or-keep episodic merges, and complete source-event lineage including the triggering write, then passes this same two-clean-state doctor.

## Evidence

- Evidence receipt: `research/evidence/memory/recmem-consolidation-negative-v1.json`
- Canonical artifacts: `data/results/recmem-consolidation/2026-08-16-local-docker-v1/`
- Stable projection SHA-256: `6c25871f30b3cf9a2cfcf84b95041c5b59642315e105a783125dd5d9f6e12fcc`
- Container image ID: `sha256:3c6b4da614d823dcc8dcaf0706b011facd4e18b47b15c9fbfc89bf64bf5d5d2b`
