# TiMem core runtime admission — 2026-08-16

## Verdict

Pinned TiMem revision `6d279a5f5d40ee229e1995df15c182cb2062c71c`
is `TIMEM_CORE_RUNTIME_ADMISSION_KILLED`. Two clean, byte-identical,
network-disabled ARM64 Docker executions reproduced three independent failures
in the released core memory-level constructors before any provider or model
call. This is a source-runtime negative, not a memory-quality result.

## Reproduced failures

- L1's `_create_fragment` calls `L1FragmentMemory(id=..., session_id=..., ...)`,
  but `L1FragmentMemory` is the processor class whose constructor accepts only
  `config`. The actual call raises on the unexpected `id` keyword.
- L2 defines a local `SessionMemory` dataclass, then constructs it with
  unsupported `level`, `content`, `child_memory_ids`, and `updated_at` fields.
  The public summarizer catches the resulting `TypeError` and returns `None`.
- L5 requires `updated_at` on `UserDeepProfile`, `ExpertServicePattern`,
  `CrossDimensionInsight`, and `HighLevelMemory`, but omits it from both the
  normal construction path and the fallback. The fallback therefore raises a
  second `TypeError` instead of returning a memory.

The `timem/` Python tree compiles; these are runtime contract defects rather
than syntax failures. The source also has no upstream dependency lock, and its
package metadata says 1.0.0 while the README announces 1.1.0.

## Containment and provenance

- Source commit: `6d279a5f5d40ee229e1995df15c182cb2062c71c`
- Source tree: `24645b2c9f2c9b40e5da7762f2159afa321edd2e`
- Deterministic archive SHA-256: `44e15508366070028c6e4b79f3f94137e8bff90956c627cb0073bf2efa5e6fbe`
- Image ID: `sha256:7d2ad09126337eaa3403d3bcda7210d2ebdeae07a99ca3b628e9f3124eea9ad6`
- Runtime: non-root, read-only root, all capabilities dropped,
  no-new-privileges, network none, no GPU, no secrets, no sudo
- Stable projection: `f46736fa962cb71feb7edbf9055e378467b00b604e2df4d8f8b0aecb48a68f22`

## Claim boundary and next gate

This result does not test temporal-hierarchy quality, graph retrieval, active
versus inactive residency, or any reported benchmark. The exact revision is
forbidden from H100 actor work. A newer immutable pin or explicit repair arm
must first pass the same two-repeat constructor doctor, bind a resolved lock,
and then complete a separate lifecycle/config admission. Only after that may a
preregistered hierarchy-versus-fixed-batching actor cell run at matched
construction calls and recalled tokens.
