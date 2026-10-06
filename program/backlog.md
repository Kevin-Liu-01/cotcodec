# Backlog and dropped lines

Source: the ranked dossier in `evidence/2026-10-06/question-dossier.md`. Every
entry there has the corrected question, closest priors, first experiment and
kill criteria. Keys below match the dossier.

## Backfill queue (preemptible, in order)

Run these only on GPUs the three main questions are not using, and only after
their own prerequisites exist.

| Order | Key | Question | First step | Est. GPU-h | Waits on |
|---|---|---|---|---|---|
| 1 | E6 | Cross-script sparse-indexer recall | Now Q3 | 1.5 | Q3 prerequisites |
| 2 | C1 | Timing census for self-hosted computer-use agents | Folded into Q2's cost card | 2.5 | Q2 runtime |
| 3 | E4 | Distilling in-context learning into a portable write rule (D19) | Teacher-strength gate | 2 | Contract refresh |
| 4 | C5 | What drives FP4 training instability (Codex's fourth) | Phase 1 emulated grid x scale at matched storage | 47 | Gauntlet |
| 5 | C3 | Do answer selection and per-question re-attempts stack (Codex's second) | Stage 0 decodability check | 6 | Throughput probe |
| 6 | E3 | Translation-supervised byte boundaries (D18) | Headroom probe on released checkpoints | 0.5 | Contract refresh |
| 7 | E5 | Recurrent-state gates and token fertility (D20) | Decay-vs-interference decomposition | 3 | Contract refresh |
| 8 | E7 | Translation-equivariant recurrent writes (D22) | G1 gate | 2.5 | Contract refresh |

The contracts and doctors for E3, E4, E5 and E7 are archived under
`legacy/experiments/architectures/` and `legacy/scripts/`. Restoring one means
moving it back, re-running its doctor, and re-checking its priors against the
dossier's corrections.

## Gated studies (need the Q2 noise floor first)

| Key | Question | Est. GPU-h | Waits on |
|---|---|---|---|
| S2 | Arabic in computer-use agents: script vs mirrored layout | 15 | Relay i18n extraction, oracle gate, power gate at about 5 pp MDE |
| S3 | Does RL on one GUI interface or UI language transfer to the others? | 150 | Q2 noise floor, S2's locale fixture, Relay at 100+ templates, a pixel harness under 5% blocked, a shared action space, a read of the Cobra PDF |

## Dropped

| Key | Line | Reason |
|---|---|---|
| C4 | Specification robustness (Codex's third) | SpecRL (2604.05820) and Spec-Harness (2604.00280) cover weak specifications; the remainder is a methods note |
| C6 | Switchable attention (Codex's fifth) | Existing switching does not remove the KV cache; the cost side duplicates HCache, ArkVale, ShadowKV and others |
| E1 | Paper 1: reasoning-language routing | Failed the correctness gate; CLSR owns test-time routing; its claims are withdrawn. The reasoning-language question survives as an arm of S2 |
| E2 | D17 causal memory holdout | CMP (2610.02070) owns known-propensity identification; strong null prior |
| E8 | Memory lifecycle audits | Workshop-tier; the audited Letta `memory()` tool was removed upstream (PR #4745) |
| E9 | Relay interface, guide and history lab | Failed the correctness gate; main effects published; underpowered at 18 tasks. Interface main effects fold into Q2 |

## Open obligations from dropped lines

- **E8:** disclose the Letta symlink finding and the post-deletion plaintext
  residue to letta-ai before any write-up. This is an outward action and needs
  Kevin's go-ahead. The doctor that found it is kept privately, not in this
  public repository.
- **E1:** the claims in `legacy/directions/01-language.md` are withdrawn.
