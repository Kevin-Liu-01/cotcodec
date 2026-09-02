# Direction 18: Translation-Aligned Byte Boundary Transport

**Status:** STILL_OPEN on 2026-09-01 — mechanism unclaimed; five new control arms required before the 20M identifiability screen
**Priority:** CPU/20M-model identifiability screen before any 1B run
**Experiment contract:** `experiments/architectures/translation-equivariant-byte-patches.yaml`

## Research question

Can parallel translations supervise where a tokenizer-free model spends global
compute, so semantically corresponding byte spans form corresponding dynamic
patches across languages without sacrificing bits per byte?

BLT allocates compute from next-byte entropy. The proposed mechanism adds
**debiased unbalanced optimal-transport supervision on boundary mass** across aligned
translation spans. The narrow candidate delta is boundary formation itself—not
ordinary cross-lingual embedding alignment and not a fairer BPE vocabulary.

## Mechanism

For two translations `x^a` and `x^b`, a frozen aligner produces weighted span
links. A causal byte encoder emits boundary mass `p_i` and patch states `z_j`.
Within each aligned span pair, position-aware unbalanced transport maps boundary
mass and patch states. Separately weighted source and target fractions allow
one-to-many translations, and the frozen span alignment—not the local solver—
represents phrase reordering:

```text
L = L_byte
  + lambda_b * UOT(boundary_mass_a, boundary_mass_b | aligned_spans)
  + lambda_z * UOT(stopgrad(z_a), z_b | aligned_spans)
  + lambda_r * patch_rate_penalty
```

The boundary head remains causal at inference. Translation, target-side bytes,
and alignments are training views only. Collapse is discouraged by the ordinary
next-byte objective, a fixed target patch-rate range, and a fixed-boundary
representation-alignment control.

## Closest work and delta

- BLT learns entropy-based dynamic byte patches.
- Parallel Tokenizers and Conditional Unigram Tokenization use parallel data to
  learn tokenization, but not BLT boundary mass or latent global-compute units.
- Parity-Aware BPE equalizes compression across languages.
- multilingual contrastive learning and activation-patching work study shared
  concept spaces but do not supervise dynamic byte boundaries.
- Rate–Utility Frontiers shows that bytes preserve cross-lingual alignment well
  under controlled content/capacity; it motivates the test but does not learn
  translation-aligned patch boundaries.

No direct prior for translation-transported BLT boundary mass was found through
2026-08-10 under the recorded search coverage. This remains pending a full
signed novelty audit.

## Implemented reference doctor (2026-08-10)

`harness/translation_boundaries.py` implements a model-free NumPy reference for
weighted byte-span links and entropic unbalanced Sinkhorn transport over causal
boundary mass. It prices genuinely unaligned mass separately from linked-mass
KL, supports unequal byte lengths and fractional one-to-many links, and fails
closed on span overallocation or solver non-convergence. The reported loss is
the debiased unbalanced Sinkhorn divergence: its cross primal includes transport
cost, coupling KL, and marginal KL; self-cost and unbalanced-mass corrections
remove entropic self-bias. Run it with:

```bash
uv run python scripts/run_boundary_transport_doctor.py \
  --output data/results/translation-boundaries/reference-doctor.json
```

The registered doctor requires an aligned unequal-length profile to score less
than 80% of a shifted-boundary control, correct links to beat a permuted
alignment, exact fractional mass accounting, and every solver block to reach
tolerance. A tiny cross primal is independently checked against SciPy
optimization. Passing proves that the proposed boundary loss is executable and
alignment-sensitive. It does not demonstrate differentiability through BLT,
better language modeling, or architectural novelty. The next build is a Torch
loss with gradient checks, followed by the 20M–50M matched model/control grid.

## Decisive pilot

Start with a 20M–50M BLT-compatible model on license-cleared English, Chinese,
Korean, and Polish parallel text. Keep all translations of one semantic item in
one split. Match bytes, target patch count, parameters, training FLOPs, and
wall time across:

1. entropy-only BLT;
2. entropy BLT plus state alignment with frozen boundaries;
3. boundary transport only;
4. full boundary plus state transport;
5. parity-aware SentencePiece/BPE Transformer;
6. fixed-stride byte patches.

Primary endpoint: macro exact terminology and tool-schema fidelity across the
four languages at matched bits per byte and patch FLOPs. Require at least three
points over entropy BLT, with no language losing more than five points. Secondary
diagnostics are aligned-boundary transport cost, patch-rate parity, retrieval of
parallel spans, bits per byte, actual throughput, and spelling/script stress.

Use paired semantic-item bootstraps, cluster translations of the same item,
report all seed and language effects, and freeze objective weights on disjoint
domains. A 125M confirmation is requested only after the small model passes.

## Falsifiers

- fixed-boundary representation alignment matches the full method;
- gains disappear after matching patch count, bytes, FLOPs, or wall time;
- aligned-boundary scores improve but task fidelity does not;
- the method overfits aligner errors, literal translations, or one script;
- bits per byte worsens enough to erase the task gain;
- a fair BPE tokenizer achieves the same frontier more cheaply.

## Model boundary

Use the reviewed open BLT/Hugging Face implementation and train the boundary
head or small model directly. Tinker is LoRA-only and cannot alter byte patch
formation. Kimi may generate adversarial terminology/tool tasks or serve as a
downstream evaluator, but it is not evidence for the architecture claim.

## 2026-09-01 kill-shot update

Verdict from the 2026-09-01 frontier sweep: **STILL_OPEN**. Four cells searched
independently; no source transports boundary probability across translation
alignments. Nearest neighbours and new mandatory control arms:

| Control arm | Source | Why required |
|---|---|---|
| Externally supervised monolingual boundaries (POS/subword targets on a frozen subword LM) | When Tokenizers Fail, [2608.27658](https://arxiv.org/abs/2608.27658) (EMNLP 2026 self-reported) | closest collision; boundary-only delta must beat it |
| Compute-matched within-patch redistribution | Scratchpad Patching, [2605.09630](https://arxiv.org/abs/2605.09630) | patchifier choice stops mattering once within-patch compute is redistributed |
| Parity-aware BPE with the `\p{L}+` regex fixed | [2606.15044](https://arxiv.org/abs/2606.15044), Vowel Signs [2608.26449](https://arxiv.org/abs/2608.26449) | unpatched BPE controls are invalid on the 17 abugidas |
| Entropy/predictability byte pruning on the same MT pairs | Autocompleting Tokenizers, [2608.15080](https://arxiv.org/abs/2608.15080) | monolingual byte pruning already evaluated on MT |
| Romanized-input arm | One Form to Transfer Them All, [2608.25904](https://arxiv.org/abs/2608.25904) | cheap cross-lingual parity baseline |

Add MAGNET per-script predictors ([2407.08818](https://arxiv.org/abs/2407.08818))
to the collision list; use OmniAlign ([2608.18474](https://arxiv.org/abs/2608.18474))
or CTFAlign/MDPAlign ([2608.21023](https://arxiv.org/abs/2608.21023)) as the
frozen aligner; prefer Bolmo-1B (Apache-2.0) over CC-BY-NC BLT-1B as the retrofit
base; keep the delta to boundary formation and ablate the patch-state term. Kill
risks to pre-register: representation alignment barely moves with parallel data
([2603.29026](https://arxiv.org/abs/2603.29026)); nested byte vocabularies are a
pre-registered negative ([2608.28151](https://arxiv.org/abs/2608.28151)). The
parallel corpus this direction assumes does not exist in the repository; its
inventory (languages, scripts, segment lengths, volume, license) is a blocking
input.
