---
name: infra-memory-baselines-skill
description: Procedure for exact-source, contained, CPU-first lifecycle doctors for external memory systems.
---

# cotcodec / infra/memory-baselines

## Purpose
<!-- agent-docs:fill:purpose -->

Each directory contains the smallest contained runtime needed to falsify or admit
an external memory system's native lifecycle before expensive actor experiments.

## Mental model & key files
<!-- agent-docs:fill:model -->

- A baseline directory normally contains a `Dockerfile` and one public-API or
  native-interface doctor.
- The paired experiment YAML lives in `experiments/memory/`; the runner,
  validator, and sealer live in `scripts/`; focused tests live in `tests/`.
- `research/memory-sources.yaml` and the portfolio matrix own durable decisions.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Pin repository revision/tree, license, dependency closure, platform, and image.
- Start with CPU, network disabled where possible, no provider secrets, and no
  external model calls for lifecycle-only gates.
- Include normal CRUD/restart/isolation controls plus system-specific falsifiers
  for interruption, retry/idempotency, ownership teardown, and physical residue.
- Use two clean states for a stable decision and never reuse output directories.
- A repair changes the treatment: name and preregister it separately.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

- Add baseline: inspect upstream source/license/API first, then write the contract.
- Debug pre-result failure: preserve it, fix only the harness defect, and rerun
  under a new versioned stage/output path.
- Seal result: verify source/image hashes, both projections, manifests, and logs.

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Hostnames and available devices do not define allocation; record scheduler GPU count.
- Logical deletion is not physical erasure. Scan stopped durable state only when
  the claim boundary explicitly includes residue.
- Upstream route or dependency drift is a provenance failure, not a treatment result.
