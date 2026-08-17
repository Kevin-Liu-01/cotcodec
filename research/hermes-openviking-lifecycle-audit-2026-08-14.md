# Hermes OpenViking Native Lifecycle Audit — 2026-08-14

## Verdict

OpenViking commit `eeff5a497360aa4481cf32e18a0d9376f4412f4c`
supports native direct memory CRUD through the exact bundled Hermes provider,
fresh-process restart, logical tenant isolation, and restart-stable logical
deletion in this contained CPU doctor. It does **not** provide physical erasure
at this pin: after both records were forgotten and the backend was restarted,
both plaintext canaries remained in retained LevelDB files.

Terminal status:
`BLOCKED_NATIVE_PHYSICAL_PURGE_RESIDUE`.

This is a negative lifecycle result, not memory-quality evidence. The tested
revision is barred from H100 actor-quality work until a native physical purge or
cryptographic-erasure mechanism passes the same retained-state scan.

## Frozen identities

- OpenViking repository: `https://github.com/volcengine/OpenViking`
- OpenViking commit: `eeff5a497360aa4481cf32e18a0d9376f4412f4c`
- OpenViking tree: `ba1585c175c9ce77a7c7438d2ae9bd82978f32f3`
- OpenViking archive SHA-256:
  `4b49f3cca288720e7f77011b8f0fec13019b182c313e8fd5835ce54a60e983e0`
- OpenViking license: AGPL-3.0
- Hermes repository commit:
  `a90d5369f76c87c98547d2e283aa26d5cfabf322`
- Hermes OpenViking provider SHA-256:
  `58c7675588ff893ce1418eab008ae116215ce3cf3efccd85f81a6bdb5b5cbb6e`

The doctor used three immutable local image IDs:

- OpenViking:
  `sha256:4b917e25cce8d71a35f6a50f67ff235f0805c179f786c72b71601f26050bca51`
- deterministic model stub:
  `sha256:6136cd68a7bed538b224756278fb15344e79e2c19b9640d9b942e41170ade440`
- exact Hermes adapter:
  `sha256:ac1f3e164a6751ee42f225456880231b392ac383b071b71c22c989ea5292274d`

All containers used read-only root filesystems, all Linux capabilities were
dropped, `no-new-privileges` was set, GPUs were disabled, and communication was
limited to a Docker-internal network. The model stub supplied deterministic
16-dimensional token-hash embeddings and an inert empty-JSON chat response.
No external API was reachable. OpenViking used the host UID/GID only for its
private bind-mounted state directory; the adapter and stub ran as `65532:65532`.

## Executed lifecycle

The exact Hermes provider executed, in order:

1. tenant A write;
2. backend stop and fresh restart;
3. tenant A search and exact-URI recovery;
4. proof that tenant B could not retrieve tenant A's record;
5. tenant B write;
6. proof that tenant A could not retrieve tenant B's record;
7. tenant A read after restart;
8. logical forget for tenant A;
9. logical forget for tenant B;
10. backend stop and fresh restart;
11. proof that both logical deletions survived restart.

All ten recorded operations returned `PASS`, and every provider invocation
reported active prompt integration. Tenant URIs were distinct and rooted under
their respective `viking://user/user-a/` and `viking://user/user-b/` namespaces.

## Falsifier

After the final clean shutdown, the doctor enumerated and hashed all 44 retained
files (2,997,399 bytes) and searched their bytes for both random canaries. The
tenant-A canary remained in:

- `data/vectordb/context/store/000005.ldb`
- `data/vectordb/context/store/000008.ldb`

The tenant-B canary remained in:

- `data/vectordb/context/store/000008.ldb`

Both reports include, for every hit, the file path, byte offset, bounded
base64-encoded byte window, and window SHA-256. The evidence validator decodes
each window and requires the deleted canary bytes to be present. This prevents
the terminal negative from resting on a self-declared residue Boolean.

## Claim boundary and next gate

Supported: exact Hermes-provider transport, native direct CRUD, fresh restart,
logical tenant isolation, and logical deletion at this source/runtime pin.

Not supported: physical deletion, secure purge, memory quality, progressive-
disclosure quality, agent improvement, H100 admission, or publication claims.

The next admissible OpenViking cell is either a newer upstream revision or an
explicitly labeled patch/wrapper arm with native purge or cryptographic erasure.
It must reproduce zero plaintext residue after a fresh restart before any
matched actor-quality experiment. L0/L1/L2 progressive disclosure remains a
separate mechanism question and cannot override this lifecycle failure.

## Evidence

- Registered experiment:
  `experiments/memory/stage4-hermes-openviking-lifecycle-doctor.yaml`
- Raw local result:
  `data/results/hermes-openviking/2026-08-14-lifecycle-doctor-v2/` and
  `data/results/hermes-openviking/2026-08-14-lifecycle-doctor-v3/`
- Self-contained sealed evidence:
  `research/evidence/memory/hermes-openviking-lifecycle-v3.json`
- Evidence SHA-256:
  `a946df0c072cc168a01fd1ec0c3ed7004b84959587762b03618f5a7ad00eb074`

The result is `scientific_result: false` and `publication_ready: false` because
it is a single local-arm64 discovery run in a dirty development tree without a
protected external runtime attestation. The reproduced purge defect is still a
hard admission blocker for the exact source and image identities above.
