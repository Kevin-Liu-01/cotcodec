# ASTRA active/inactive working-set audit — 2026-08-15

## Verdict

ASTRA is the first source in the 2026-08-15 delta that implements a credible
bidirectional active/inactive **working-set mechanism** rather than merely
labelling records hot or archived. A bounded `MemoryWindow` admits durable
records, evicts them without deleting the backing memory, persists the active
set, and allows later retrieval to admit a durable nonresident record again.

The native result is now sharper and negative. Slurm job 269 executed two clean
H100-allocated, Docker-contained CockroachDB lifecycles. In each repeat,
ordinary K=12 eviction, durable retrieval-driven re-admission, acknowledged
state after forced database-process restart, user isolation, duplicate-write
diagnosis, soft-delete residue, and pinned overflow behaved as registered.
However, the two normalized state projections were not identical. Total recall
access increments matched (6 before restart and 12 after restart), but they
landed on different tied records: four records differed before restart and ten
after restart.

This fails the preregistered clean-store identity gate. At this revision ASTRA
is a credible pager mechanism **shape**, but not an admissible deterministic
pager for an actor comparison. Its recall query and JavaScript fusion sort have
no deterministic secondary key for equal vector/fused scores, so clean stores
can reinforce different items from identical inputs. Physical purge,
idempotency-keyed writes, and a hard cap under all-pinned saturation also remain
absent. No H100 actor cell is allowed.

The raw negative bundle is retained at
`data/results/astra-native-lifecycle/2026-08-15-job269-v11/`. Its six job
artifacts are embedded and hash-bound in the committed, self-contained receipt
`research/evidence/memory/astra-native-lifecycle-negative-v1.json`. The receipt
validator rechecks both repeat checkpoints, scheduler output, scheduler
allocation, containment arguments, lifecycle semantics, and the exact
cross-repeat access-count divergence. `analysis.json` hashes to
`adf6c86108a36617f4e98a4ac9e9e57d6f17deea56b11a8471e70bdd9a042f57`.
This is discovery-grade lifecycle evidence (`scientific_result=false` and
`publication_ready=false`), not memory-quality evidence.

## Immutable source receipt

- Repository: <https://github.com/cyh7789/astra>
- Commit: `644f9d4e65f4e725996025834c91531592ab6166`
- Tree: `43592dc01aa730efb263d24255b094e1f4dc24f3`
- `git archive --format=tar` SHA-256:
  `f283ca328a080bd6c8c7fac723d490f3d73d15a71f0b7290090bd371957f3d48`
- License: MIT; `LICENSE` SHA-256
  `f109128ffcc7d51c9f9ee414f04b7b2c6a633808b4d565138ca43e0c77dbd86a`
- `package-lock.json` SHA-256:
  `44ffc76a024117bd76488a4878e8b372c9aab9abe1abfd9489bf17135218c2b5`
- Tracked files: 88

## Mechanism contract

The active set is constrained by both record count and rendered character
budget. Admission sources are passive retrieval, explicit memory tools, linked
records, events, pins, and cross-scene handoff. Refresh updates relevance
without duplicating a resident. Nonpinned eviction sorts first by oldest
`lastRelevantTurn`, then by lower score. Turn TTL, absolute expiry, scene
privacy, and exponential session-gap cooling can remove residents. The
serialized active set stores record IDs plus admission metadata; record content
remains in the durable memory table.

This is a real pager candidate because eviction removes a record only from the
window. A later `safeRecall` can fetch the durable record and `admitScored` can
make it active again. Job 269 demonstrated that database path and restart twice,
but also demonstrated that tied recall candidates receive nondeterministic
access reinforcement. The mechanism is therefore demonstrated but
actor-inadmissible at this pin.

## Contained component reproduction

Dependency acquisition ran in a container with `npm ci --ignore-scripts`.
Tests then ran twice under the immutable local image
`node@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c`
with network disabled, a read-only root filesystem, all Linux capabilities
dropped, and `no-new-privileges` enabled. No sudo, model, API, or GPU was used.

The exact test roster was:

- `tests/memory-window.test.ts`: 7 assertions
- `tests/retrieval.test.ts`: 12 assertions
- `tests/guards.test.ts`: 7 assertions

Both runs passed 26/26 assertions. The canonical semantic projections were
byte-identical and hash to
`667d0a146c6021a5c193af0a1724de7706630df4ff5e05bbee362c4476d3412d`.
The distinct raw run hashes are
`4f67f63d672b15dd958285b09266ea4994442424744c76625d07ed390434af24`
and
`24ee2a79eb0632d52981a7e110e338bc50725796c010d5a11785c831e02bbb72`.

The self-contained evidence bundle is
`research/evidence/memory/astra-working-set-core-v1.json`, SHA-256
`3a310140916bd73dc525e5cd2a614978b40b106602411dc22eb7532f5e24258e`.
The ledger validator decodes every embedded file, rechecks the image identity,
recomputes the exact test roster and two-run semantic projection, and refuses
failed, duplicate, missing, or drifted executions.

## Executed H100 lifecycle gate

The exact registered job uses
`infra/slurm/host-single-node/astra-lifecycle.sbatch`. It requests one H100,
sixteen CPUs, 64 GiB, and thirty minutes, but passes no GPU into either runtime
container. The allocation is a target-host/Slurm admission receipt; the doctor
itself uses ASTRA's deterministic 1024-dimensional `FakeEmbedder` and makes
zero model or provider calls. Both ASTRA and CockroachDB run in read-only,
capability-dropped containers with external networking disabled. CockroachDB
binds only `127.0.0.1`, and ASTRA joins that exact container network namespace.

The preregistered terminal expectation was
`BLOCKED_NATIVE_PURGE_IDEMPOTENCY_AND_PINNED_CAP`: ordinary unpinned K=12
eviction, durable re-admission, forced-restart recovery, and user isolation
must pass, while identical retries should create two rows, soft deletion should
leave a queryable plaintext row and stale session reference, and thirteen
pinned records should exceed K=12. Two clean stores must yield one identical
semantic projection. The status is a falsification gate, not a desired success.
Job 269 reached both per-repeat terminal expectations but correctly failed the
cross-repeat projection gate.

The only projection differences are per-record `access_count` values; after
removing those values and their dependent projection hashes, both repeat
projections hash to
`5c947f1b251659dccbee26cab6e1f45b6911eb4d52149ed5a3ff0d8d6b1a31eb`.
That does not make the result harmless: access count is persistent memory-policy
state and can alter later eviction or ranking. The upstream candidate query
orders only by vector distance/similarity, and the final JavaScript sort uses
only fused score. No record ID or insertion ordinal breaks ties.

Execution history is retained rather than rewritten: job 258 exposed an npm
acquisition failure; 259 caught a host-local versus portable image-ID mismatch;
260/261 rejected the first container-network topology; probe 267 established
the loopback-only CockroachDB topology; 268 exposed an ESM launcher boundary;
and 269 produced the two real lifecycle checkpoints and negative result. None
of the pre-269 jobs is counted as lifecycle evidence.

Do not freeze ASTRA actor frames from this revision. A repaired/new immutable
pin must first add deterministic recall tie-breaking and then pass the same
two-clean-store gate, in addition to closing physical purge,
idempotency-keyed writes, and pin-saturation capacity. Only then may a 32-episode,
2-H100-hour actor screen compare paging with recency, true LRU, BM25/dense
inactive archive, and full-prefix under one frozen task and prompt manifest.

Kill the pager claim on any restart mismatch, missing durable re-promotion,
nondeterministic persistent recall state, capacity violation outside the
preregistered pin diagnostic, cross-user bleed, purge residue, or failure to
beat recency/LRU after all administration and rendered-token costs are charged.
