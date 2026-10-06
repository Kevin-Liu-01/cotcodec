# Hermes Observational Memory lifecycle intake — 2026-08-15

## Verdict

Retain Hermes Observational Memory as a **reproduced standalone-provider
lifecycle negative**, not as a tenth member of the already sealed Hermes
conformance roster and not as memory-quality evidence. Docker-under-Slurm H100
job 291 reproduced standalone discovery, bounded startup context, BM25
retrieval, explicit note persistence across a fresh process, isolated memory
roots, budget refusal, and operator-scoped test-root removal twice. It also
confirmed the admission blocker: the provider exposes no native delete,
forget, purge, or physical-erasure contract. Status is
`BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE`; an actor cell is forbidden for
this revision.

## Immutable sources

- Hermes Agent `a90d5369f76c87c98547d2e283aa26d5cfabf322`, tree
  `963eb136bfb21fd0b296a40529cbb3575c610874`, archive SHA-256
  `2a2934d3c8379816b2e3919f4cf1191f04e93f136da6f2128246d368644a9514`,
  MIT.
- Hermes plugin `90d83c1ff768d80f99f4e3ef4d76269f90e1c808`, tree
  `5cf00ebd8f4d57673469e2e45f3954ac37d875af`, archive SHA-256
  `33d6bc75ff850fdf9140d225bc6636c3cc22f0c015f897c546ce226b7cc551c4`,
  version 1.5.1, MIT.
- Observational Memory core v0.10.0
  `6bbc16e81ad1258ee1e8ba37c9efcc6ce36a0208`, tree
  `96f4288c19b78b0bdda8568efa0c5b1435d64552`, archive SHA-256
  `0d103be2c781b0ac546a5fa16cb81c1f877513675b83ca33b06cd7fa4d8312f0`,
  MIT. The exact PyPI wheel SHA-256 is
  `d743b32823af544468fc666621850931ae77c0225d8c162db43b878cbdb5f4e4`.

The plugin dependency is only the range
`observational-memory>=0.10.0,<0.11`; publication or conformance execution must
replace that range with the exact wheel or pinned source above.

The contained lifecycle image deliberately installs only the exact Hermes
source needed for its real standalone-provider discovery/loader path plus the
offline-pinned Observational Memory, Rank-BM25, NumPy, and PyYAML wheels. It is
an `exact-source-minimal-provider-loader-slice`, not a claim that the full
Hermes CLI dependency graph or agent loop was installed or tested.

After the cluster's package-index DNS failed during the first locked full-Hermes
build attempt, the registered discovery image was narrowed further to use the
already-cached CoTCodec research image ID
`sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10`
only as an offline OS/Python/uv substrate. This base is exact but not a clean
publication capsule; the lifecycle result remains discovery-only even if all
provider gates pass.

## Mechanism boundary

The provider's exact tool roster is `om_context`, `om_search`, and
`om_remember`. It loads a bounded startup payload derived from `profile.md` and
`active.md`, optionally augments it with query-specific retrieval, and appends
explicit notes to local observation Markdown before rebuilding startup/search
state. Optional incremental or session-end writeback sends Hermes turns through
the observer; reflection and OM Cluster synchronization are separate estimands.

This is push-plus-pull context continuity and one-way consolidation. It is not
automatic bidirectional active/inactive paging: startup files are generated
views, explicit notes enter the durable store, and there is no provider action
that demotes and later promotes a bounded actor-visible record.

## Registered falsifier

`experiments/memory/stage4-hermes-observational-memory-lifecycle-doctor.yaml`
hashes to
`76e91c4058f91ee4a472b22d221daafa5ce3ab94a18b141a77fcaedf74ed5607`.
It requires:

- exact offline wheel/plugin install and real Hermes standalone discovery;
- zero API credentials, model calls, or measured external network calls;
- an empty-root baseline, explicit note, BM25 search, bounded startup context,
  and two fresh-process restarts;
- two physically separate memory roots with no cross-root recall;
- a hard-budget writeback-refusal probe without silently breaking the session;
- an explicit audit showing no native delete/forget tool;
- a full retained-file manifest and plaintext scan before and after an
  operator-scoped test-root purge.

The operator cleanup is not evidence of provider-native erasure. The lifecycle
doctor itself is registered as a one-H100 Slurm allocation (16 CPUs, 64 GiB,
30 minutes, 0.5 H100-hour hard ceiling) while deliberately denying the Docker
container GPU passthrough and making zero model calls. That keeps all execution
inside the requested H100/Slurm boundary without misrepresenting a filesystem
provider doctor as GPU inference. H100 actor admission remains forbidden until
an exact final image and SBOM exist, two contained repetitions agree, and the
system supplies native deletion or cryptographic erasure.

## Executed evidence and boundary

Slurm job 291 ran the exact offline provider stack in Docker inside a one-H100
allocation. The lifecycle container intentionally received no GPU passthrough:
the H100 allocation supplies scheduler/GPU provenance while the filesystem
provider doctor makes zero model calls, zero API calls, and no claim of useful
GPU computation. Two clean repetitions produced the same semantic projection,
SHA-256 `3d2af80275a690e1acfc9455a37b8b60c81bae7e37011c3597e9b1ece8cd4c67`.

The retained local evidence root is
`data/results/hermes-observational-memory-lifecycle/2026-08-15-job291-v13/`.
The report hashes to `1b828fcc043428b90d5bbb7c8c1a2260f3ba79878b89dd71068b11796dfb4325`,
the 26-row manifest to
`dc52dde2feb0548a568c9cc8545d7a45f611aee4515304e47f7ee4d58d9f3c8e`,
the Slurm job receipt to
`01bb394adf93147ee6a6240b7831b6bf4c6183dd4eb6fd500a5f19ee2a337142`,
and the SPDX SBOM to
`96bcdc392d46eaa0b973ecb77fe480c6a34df40b0f422d5a2b83dff728ceb833`.
The exact 24 GB image archive remains retained on the H100 host and is bound by
SHA-256 `bd66a9816f964afc114c89de9e0ee20363203f95800c4b50ac830113c590d6b9`.
The machine-checked negative receipt is
`research/evidence/memory/hermes-observational-memory-lifecycle-v1.json`.

This is discovery-only evidence from a normalized dirty-worktree source archive
and an exact but non-publication base image. It proves neither memory quality
nor native erasure. Removing an operator-owned test directory is cleanup, not a
provider deletion primitive. A newer immutable provider revision or explicit
repair arm must expose native deletion or cryptographic erasure and pass the
same two-run doctor before any H100 actor comparison.
