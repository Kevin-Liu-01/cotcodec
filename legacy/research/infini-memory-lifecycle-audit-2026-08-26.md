# Infini Memory Exact-Source Lifecycle Audit — 2026-08-26

## Result

`INFINI_MEMORY_ADMISSION_KILLED_UNCONFINED_USER_PATH_DESTRUCTIVE_DELETE_AND_NONATOMIC_INDEX`

The pinned Infini Memory revision `ddac08ec468e0382e4f14239d94991ab19ae981a`
passed its normal public add, BM25 search, get/list, update, document deletion,
user deletion, and fresh-process restart controls. It failed the preregistered
storage-confinement and interrupted-write gates in two clean, network-disabled,
non-root Linux ARM64 Docker volumes.

## Reproduced findings

- `user_id` is joined directly into `root / data_root / user_id`. Relative IDs
  escaped the configured data root, absolute IDs overrode it, and an
  alias-equivalent ID shared storage with the canonical ID.
- Public `delete_user` repeats the same unvalidated join and passes the result to
  `shutil.rmtree`. The contained escape fixture recursively deleted a user tree
  outside the configured data root.
- Public update writes Markdown before saving `index.json`. A forced index-save
  exception left new Markdown content paired with old summary, token, and update
  metadata; the mismatch survived two fresh-process restarts.
- Public document deletion unlinks Markdown before saving `index.json`. A forced
  index-save exception left a durable index entry whose file was absent; the
  dangling entry survived two fresh-process restarts.
- A truncated `index.json` is caught by the broad loader exception and silently
  projected as `{"docs": []}` while the indexed Markdown remains present. The
  empty public view survived another restart.

## Positive controls and diagnostics

- Normal public add/get, BM25 search, update, document deletion, user deletion,
  and restart persistence passed in both clean repetitions.
- Bounded scans of retained current regular files found none of the three
  deleted plaintext canaries in either repetition. This is not secure-erasure
  evidence.
- Each repetition charged one deterministic local rewrite call, three BM25
  queries over four documents, and three direct-Markdown queries reading four
  files. Timings are diagnostics only, not sustained throughput or a causal
  retrieval-quality comparison.
- The exact committed `uv.lock` was installed frozen. Runtime model/provider
  calls, external API calls, GPU calls, and H100-hours were all zero.

## Evidence and boundary

- Stable projection: `a431ee72891d0d107360b34f62108174cf0d05fa3bd2749aa0d5414db6ca9027`
- Portable evidence:
  `research/evidence/memory/infini-memory-lifecycle-negative-v1.json`
- Portable evidence file SHA-256:
  `83c0a970811278d0b4b81f54d2c1a0651981bca9ca9e858a4ca427bd744ca6ba`
- Raw report SHA-256:
  `b18bb5eccb9500de18ec24f98a217d5bc8ebc235d46a378e3c4073daa5c74cd5`
- Raw manifest SHA-256:
  `38b7e55d3750eab2be85d29c99b9aa0a26619f479f1f4de94c19c71b3b521fc2`

This is exact-source lifecycle and storage-boundary evidence only. It is not
extraction quality, topic-rewrite quality, semantic retrieval quality, secure
filesystem erasure, sustained throughput, concurrent multi-process correctness,
H100 actor quality, or publication evidence. H100 admission is forbidden for
this revision. A newer immutable revision or explicit reviewed repair arm must
add canonical user-ID validation, root confinement for reads and recursive
deletion, and atomic generation or journal recovery across Markdown, index, and
event state, then pass the same doctor.
