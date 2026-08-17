# Hermes memory-provider conformance — 2026-08-14

Status: development evidence only. `scientific_result=false`.

Sealed development artifacts:

- report SHA-256:
  `013f10e0d865415a1022e0d845a558264a1a1377a2e4b3eef6711dfb625def32`
- manifest SHA-256:
  `74eba6e2c1b1148a21f4b8709459dd6234e696fdc3a50d683a30281591d9fd0a`
- experiment-contract SHA-256:
  `1fd5f7620894fac8a4ecfcc9a56552075920747a8c815ecd8ae8b7c570300c23`
- aggregate status: `FAIL`; `publication_ready=false`

## Outcome

The current Hermes documentation says that Hermes ships with eight external
memory providers, but its comparison table names nine when the separately
packaged Memori integration is included. The executable roster at the pinned
source revisions is:

`byterover`, `hindsight`, `holographic`, `honcho`, `mem0`, `memori`,
`openviking`, `retaindb`, and `supermemory`.

All testing ran in Docker with no network, a read-only root filesystem, all
Linux capabilities dropped, and `no-new-privileges`. No provider credentials
were present and no host package, provider install script, or `sudo` command was
used. These results establish import, schema, unit-contract, and local-storage
behavior only; they do not compare memory quality.

| Provider | Executed evidence | Result | Honest interpretation |
| --- | --- | --- | --- |
| ByteRover | Bundled provider unit group plus native offline doctor | 1 unit test passed; offline status blocked | The exact v3.16.1 CLI, npm bytes, tag object, peeled commit, and Hermes adapter are pinned. Native `search` and Hermes `query`/`curate` all hit the daemon's fatal network startup path under network-none; storage is profile-global and no session purge exists. |
| Hindsight | Bundled provider unit group plus native lifecycle falsifier | 112 unit tests passed; lifecycle status blocked | Exact Hermes retain/recall/prefetch/session-end retention, two tenants, two full restarts, and restart-stable logical bank deletion passed twice. Both runs retained each deleted plaintext canary in four PostgreSQL heap files plus WAL, and Hermes exposes no Hindsight purge tool. The strict timeout defect below also remains. |
| Holographic | Bundled provider unit group plus native lifecycle falsifier | 51 unit tests passed; lifecycle status blocked | Native SQLite/FTS restart, idempotence, update, and feedback passed twice, but logical sessions share one global database and no native session purge exists. HRR quality remains untested. |
| Honcho | Bundled and Honcho-specific groups | 349 passed, 16 skipped, 1 failed | Deterministic cache-invalidation defect; no live Honcho service. |
| Mem0 | Bundled provider unit group | 57 passed | Adapter tests only in this matrix. The separate CoTCodec Mem0 lifecycle job remains the native persistence evidence. |
| OpenViking | Bundled and OpenViking-specific groups | 101 passed | The local server was absent and the provider logged its unavailable/fail-open path. This is not a native OpenViking result. |
| RetainDB | Bundled provider groups | 39 passed | Cloud adapter contract only; no credential or service call. |
| Supermemory | Bundled provider unit group | 26 passed | Adapter contract only; no hosted or self-hosted service. |
| Memori | Official integration tests plus Hermes install/discovery | 34 passed; install and load passed | The external package installs into Hermes, is discovered as the ninth provider, and exposes six schemas. No cloud request was made. |
| Common discovery/configuration | Bundled common tests | 28 passed | Shared loader and configuration contract passed. |

Counts overlap the upstream suite boundaries and must not be summed into one
sample size. The initial full `tests/plugins/memory` run produced 329 passed,
one skipped, and two failed. Provider-isolated runs are reported separately so
cross-test state and cold-start behavior remain visible rather than being
averaged away.

## Reproducibility receipt

- Hermes repository: `https://github.com/NousResearch/hermes-agent`
- Hermes commit: `a90d5369f76c87c98547d2e283aa26d5cfabf322`
- Hermes tree: `963eb136bfb21fd0b296a40529cbb3575c610874`
- Hermes `git archive` stream SHA-256:
  `2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514`
- Hermes version/license: `0.20.1`, MIT
- Memori repository: `https://github.com/MemoriLabs/Memori`
- Memori commit: `538b61f245295aa1a43df8033879f8293627f74d`
- Memori tree: `6efd92a1d65c49dec682850d29401899f83d6268`
- Memori repository license: Apache-2.0
- `hermes-memori` wheel: version `0.1.8`, SHA-256
  `d15840b7e4ce791c348e0e4ec366f05f221779df7a37815a6305b232b84e631f`
- `memori` wheel: version `3.3.6` for Linux ARM64, SHA-256
  `85e216a3b264a78693e11498d794c92dabdefaf55f78fa031dc834366f337a5b`
- Registered Linux x86-64/H100 `memori` wheel SHA-256:
  `96405cd5095f51cbc69b565726a9938bf5cb6adc16d8834652be35e58586e483`
  (pinned for the later cluster image; not executed in this ARM64 cell).
- Runtime image:
  `ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b`
- Runtime image ID:
  `sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b`
- Python dependencies: exact Hermes `uv.lock`, `dev` and `hindsight`
  extras, plus the two exact Memori wheels above.

The Memori checkout describes root package version `3.3.7`, while the latest
released wheel available to the integration was `3.3.6`. The source checkout
and released runtime are therefore separate evidence identities.

## Reproduced defects and drift

### Honcho cache signature does not follow `pinPeerName`

`TestPinTransition::test_cache_busting_signature_reflects_pin_peer_name`
fails both inside the full Honcho group and alone. Rewriting `honcho.json` from
`pinPeerName: true` to `false` leaves
`GatewayRunner._extract_cache_busting_config(...)` reporting `true`. A gateway
may therefore reuse an agent cache across a configuration transition that was
intended to invalidate it.

### Hindsight drain timeout does not bound one status operation

The full memory suite initially failed:

- `test_prefetch_waits_for_server_completion_before_recall`
- `test_prefetch_proceeds_after_server_wait_timeout`

Both later passed in a fresh isolated run, making this a reproducible timing
flake rather than a deterministic assertion failure. The contract defect is
still concrete: `_wait_for_server_retain_ops` checks its drain deadline before
calling `_is_retain_op_complete`, but that call uses the general Hindsight
request timeout (120 seconds by default). One status poll can therefore exceed
the configured `prefetch_retain_drain_timeout`; the outer deadline cannot
interrupt it. The upstream test also allows three seconds for a registered
0.3-second budget, masking substantial overrun. A deterministic strict probe
requested a 0.05-second budget and measured 0.256786884 seconds. Treat this
provider as failing the strict bounded-latency gate until the status call
receives the remaining budget or an independent cancellation boundary.

### Documentation and package drift

- The provider page says “8 external provider plugins” but lists nine with
  Memori.
- Memori exposes six tools, including `memori_compaction`; the provider page
  describes five and omits compaction.
- `hermes-memori` registers a general `hermes_agent.plugins` entry point but
  installs a directory into `$HERMES_HOME/plugins/memori` for the dedicated
  memory-provider loader. The real install/discovery path passed.

## Next executable ladder

1. Holographic is complete as a negative lifecycle cell. Do not admit this pin
   to a portable H100 study; test only a newer pin or explicit session-scoping
   wrapper, and keep HRR quality separate with a pinned NumPy runtime.
2. ByteRover is complete as a negative provider-boundary cell. Do not admit
   v3.16.1 to H100; require a newer pin or explicit local/offline patch arm,
   session scoping, and native purge before retesting.
3. OpenViking is complete as a native negative: exact Hermes transport, direct
   CRUD, two-tenant logical isolation, and fresh restart passed twice, but both
   deleted plaintext canaries remained in retained LevelDB files. Do not admit
   `eeff5a4` to H100 quality work without native purge or cryptographic erasure.
4. Hindsight is complete as a native negative. Do not admit `5781d28` to H100:
   exact Hermes transport, two-tenant logical isolation, two restarts, and
   logical bank deletion passed, but deleted plaintext remained in PostgreSQL
   heap and WAL files and the provider exposes no purge tool. Require native
   physical purge or cryptographic erasure in a newer pin or explicit repair.
5. Mem0 and Supermemory: run digest-pinned self-hosted services through
   `memory-lifecycle-v1`, including restart, branch isolation, deletion, purge,
   lineage, and phase-cost receipts.
6. Honcho, RetainDB, and Memori: keep contract-only until a credentialed service
   cell is explicitly authorized. Pin endpoints and capture request/response
   receipts without exposing secrets.
7. Only providers that pass the CPU lifecycle gate may enter the frozen actor
comparison. Model-bearing cells run in Docker under Slurm on H100s with the
same tasks, memory bytes, read budget, actor, and judge.

The Holographic lifecycle evidence is sealed at
`research/evidence/memory/hermes-holographic-lifecycle-v1.json` (SHA-256
`a532c646f24463a30910959f70c278c816d331a36b79efb1e75980604c31451d`).
Two fresh container volumes produced the same stable projection. The Linux
container had no plaintext hits after individual deletion, while a separate
macOS diagnostic did; this does not establish portable secure erasure.

The ByteRover evidence is sealed at
`research/evidence/memory/hermes-byterover-offline-v1.json` (SHA-256
`4b51e2f1b63317e7ddaa596d4fb99b0bff16d8d55e5a0147c4c9ce32210ef15a`).
Two fresh volumes produced stable projection `22f74a8d...`; no credential,
model, network, GPU, or upstream install script was used.

The OpenViking evidence is sealed at
`research/evidence/memory/hermes-openviking-lifecycle-v3.json` (SHA-256
`a946df0c072cc168a01fd1ec0c3ed7004b84959587762b03618f5a7ad00eb074`).
Two independent contained runs each passed direct CRUD, two fresh restarts,
logical tenant isolation, and restart-stable logical deletion. Both runs then
reproduced plaintext residue for both deleted tenant canaries in LevelDB, with
byte windows embedded in the sealed receipt. This is a lifecycle negative, not
an OpenViking retrieval-quality result.

The Hindsight evidence is sealed at
`research/evidence/memory/hermes-hindsight-lifecycle-v1.json` (SHA-256
`68176f77d759be15497203dac3d7e449c609c76507e5d8242af88a2a62064c1b`).
Two independent contained runs each passed all 12 registered operations,
including exact Hermes-provider prefetch and session-end retain, two-tenant
logical isolation, two full database/backend restarts, and restart-stable
logical bank deletion. Each deleted canary nevertheless remained in four
PostgreSQL heap files and one WAL segment. This is a lifecycle negative, not a
Hindsight quality, graph, reflection, or mental-model result.

The first model-bearing comparison must include no-memory, raw BM25, dense raw
retrieval, and full-prefix ceiling controls. A bundled provider win cannot be
attributed to its advertised memory mechanism until construction, retrieval,
and controller components are ablated under matched cost.
