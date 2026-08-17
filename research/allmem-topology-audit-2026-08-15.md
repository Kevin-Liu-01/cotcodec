# All-Mem topology and evidence-recovery audit

Date: 2026-08-15  
Source: [paper](https://arxiv.org/abs/2603.19595), [official repository](https://github.com/LvCan926/All-Mem)  
Revision: `f5d6912717b0d6c65a19ba2660fb9b6637d4d50e`

All-Mem is a direct active-anchor plus archived-evidence graph prior. Its
bounded active nodes seed retrieval; typed graph expansion can recover archived
neighbors; offline SPLIT, MERGE, and UPDATE operations replace active topology.
This occupies broad novelty claims around active anchors, archived evidence,
and LLM-directed graph repair.

The contained CPU doctor used the exact pinned source in a non-root,
network-disabled, read-only-root Docker image with no provider secret, model
call, GPU, or sudo. It created matched UPDATE, SPLIT, and MERGE cases, saved the
native pickle, and loaded it in a fresh container. Two clean states reproduced:

- UPDATE creates a typed `version` path to the archived predecessor and query
  expansion recovers that predecessor.
- SPLIT children inherit the original source identifier but have no typed path
  to the archived original node.
- The MERGE node inherits both source identifiers but has no typed path to
  either archived source node.
- Semantic topology is stable after a fresh process when equal-content ties are
  normalized. Exact ordering of the two duplicate source records changed in one
  restart, so no exact tie-order claim is admitted.

The result is a bounded negative lifecycle invariant, not a memory-quality or
graph-efficacy result. This revision also lacks tenant/session ownership,
archive-to-active promotion, atomic crash recovery, native scoped purge, a lock,
and upstream result artifacts. It is therefore blocked from H100 admission.

Unblocking requires a newer immutable revision or explicit patch arm with
transitive typed recovery edges for every derived source, deterministic scope
ownership, zero-residue purge, atomic two-restart recovery, and a matched
flat-versus-topology model-bearing cell.

Canonical evidence: `research/evidence/memory/allmem-topology-v1.json`.
