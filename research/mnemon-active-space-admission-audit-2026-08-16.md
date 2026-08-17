# Mnemon active-space admission audit — 2026-08-16

## Verdict

The CPU lifecycle result remains valid, but the registered H100 answer-quality
follow-up **killed the static-space routing hypothesis** at the pinned revision.
Mnemon plus `dsh-mnemon` remains a useful implementation reference for isolated
named stores and explicit query scopes; it is not evidence for learned paging,
access control, item-level physical erasure, or a quality advantage from static
space selection.

Terminal H100 status: `MNEMON_STATIC_ROUTING_KILLED`.

Do not escalate this revision to a larger actor. Any future routing hypothesis
must define a materially different mechanism, a new preregistered panel, and a
matched prompt-budget contract.

## Immutable sources

- Mnemon core: <https://github.com/mnemon-dev/mnemon>, revision
  `88d2981edeb18a5ebe048af472f6f96527615454`, tree
  `056fd6d91cf391aaf7667990fdfcef784c670fc1`, Apache-2.0, archive SHA-256
  `a7dba5eea43bc727b0360ba598312067eb2e599525eded3f929fb942ebb781c6`.
- `dsh-mnemon`: <https://github.com/omdsh-dev/dsh-mnemon>, revision
  `1889c68400e52a391ee9a6eedf15bf44bc39dd06`, tree
  `87024a203721069a5dbb01b013dcca9475df3328`, MIT, archive SHA-256
  `6d168ff938b4fcf5bac27e4a7b753f18b987cefb2ce45cdb7795cc7231cc5027`.

Source inspection corrected the ownership boundary: Mnemon core owns isolated
named SQLite graph stores and deterministic CRUD/search. The active-store
registry, default-recall filtering, inactive-read rejection, and targeted-write
activation belong to `dsh-mnemon`.

## Reproduced contract

Two fresh runs used image
`sha256:758216ed7cf9fa7794ab4e63efac2a08b4af92a78b99ae378ab6b512e6d9db5f`
with runtime network disabled, read-only root, UID/GID 65532, all capabilities
dropped, no-new-privileges, no providers, no secrets, zero GPUs, and zero model
or embedding calls.

Both repetitions reproduced:

- distinct native databases for two named spaces;
- default recall restricted to the plugin's active set;
- rejection of an explicit read from an inactive space;
- automatic activation after a targeted write;
- active-registry persistence across a fresh service construction;
- core soft-forget hiding the item while retaining its unique plaintext row;
- whole-space deletion removing the non-final store directory; and
- rejection of deletion of the last native store.

The stable semantic projection SHA-256 is
`34ace60034308da2e72669ed06f8bb6ca378b35a3e32fa807d4c732fe71b1e48`.

## Evidence

- Evidence: `research/evidence/memory/mnemon-active-space-admission-v1.json`
- Evidence SHA-256:
  `27d7d55c664748bf7bc5fb6e1ad53d17cb35a50d9497329851dc1eaa4155debb`
- Retained run directory:
  `data/results/mnemon-active-space/2026-08-16-local-docker-v1`
- Report SHA-256:
  `16aa569771c987ad2206f496a130e84080cac1ef360f50195890082208d76acc`
- Manifest SHA-256:
  `491681e4d06cf5da303cd5e0057d405763aeeae1c417e41b85cf39a1813ba80f`

The evidence is `scientific_result=false` and `publication_ready=false`.

## Claim boundary and H100 gate

The frozen panel contained 32 synthetic discovery tasks and four arms:
no-memory, all-spaces, deterministic lexical routing, and oracle-space. Job 313
ran all 128 cases under Docker through Slurm on one H100 with the pinned
Qwen3.5-4B artifact. Job 315 mounted the completed predecessor and reproduced
all five finalized actor artifacts byte-for-byte in a fresh allocation.

Results:

- no-memory exact match: `0.0`;
- all-spaces exact match/token F1: `1.0 / 1.0`;
- lexical-router exact match/token F1: `1.0 / 1.0`;
- oracle-space exact match/token F1: `1.0 / 1.0`;
- lexical-minus-all-spaces token F1: `0.0`; and
- lexical/all-spaces prompt-token ratio: `0.7815468114`, outside the registered
  matched nonempty budget band.

A/A determinism, nonempty completions, no-memory lift, lexical exact minimum,
and lexical/oracle equality passed. The quality-lift and matched-budget gates
failed. Because all-spaces already saturated the task, the panel cannot support
a routing-quality benefit, and scaling the same revision/model hypothesis would
be post-hoc fishing.

H100 evidence:

- Evidence:
  `research/evidence/memory/mnemon-h100-static-space-negative-v1.json`
- Evidence SHA-256:
  `e94b3ece8a972d35da0f60b454cf2dbce34916abfdfbcb8152761c68cf399846`
- Primary/resume Slurm jobs: `313` / `315`
- Primary report SHA-256:
  `492c9d431b2f8b0b8b28ba43e829cac43d8b5cc03036bd209863a7c61d6e89d5`
- Predictions SHA-256:
  `6b435f03c4a8126155719fd5f237c480dab60a4bef8edc0794910b0c893c469a`
- Source image:
  `sha256:d9ca96642e4c6621500d3c6f605ce3a613414bd5ae64b1907f0b2675cf8a51bb`

The result is a local negative reproduction with `scientific_result=false` and
`publication_ready=false`. It tests a synthetic answer-transport falsifier, not
external memory quality. It cannot be described as learned promotion,
demotion, ACL enforcement, or secure forgetting.
