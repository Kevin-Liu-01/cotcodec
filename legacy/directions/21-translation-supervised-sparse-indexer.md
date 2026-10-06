# Direction 21: Translation-Supervised Sparse Indexer

**Status:** OPEN on 2026-09-01 — wave-5 executable Phase-0 doctor (NumPy, PASS) plus decision-rule, partition and λ_x re-registration applied; judged 61 (wave 2), 66 (wave 3), 62 (wave 4; lower of 62/69, a recorded dip); wave-5 text unjudged; caps 74/79/89; not pilot-ready
**Priority:** GPU entry point and re-pinned image next; the NumPy Phase-0 doctor exists and passes; then the ≤ 4 GPU-h Phase-0 kill screen before any identification run
**Experiment contract:** `experiments/architectures/translation-supervised-sparse-indexer.yaml`
**Phase-0 doctor:** `harness/translation_supervised_indexer.py`, `scripts/run_translation_supervised_indexer_doctor.py --output data/results/translation-supervised-sparse-indexer/phase0-doctor.json` (PHASE0_DOCTOR_PASS 2026-09-01; executability and gate semantics only; synthetic numbers), `tests/test_translation_supervised_indexer_doctor.py`
**Proposal:** `research/proposals/2026-09-01-translation-supervised-sparse-indexer.md`

## Research question

Do the learned top-k indexers that DeepSeek-V3.2 (DSA), Qwen3.8-Next (QSA),
GLM-5.3-Flash and SpotAttention attach to sparse-attention layers lose more
cross-script selection recall than the full-attention target they are distilled
from — once monolingual and cross-lingual queries are equally non-literal — and,
if a residual cross-script shortfall survives the best label-free target
aggregation (chosen on absolute cross-script recall, not on the excess
statistic), does corpus-given sentence-alignment supervision of the *detached*
indexer raise absolute cross-script recall on languages the alignment loss
never saw?

The claim scope is **attachment-capability**: a detachable indexer on frozen
released checkpoints (a retrofit population until Phase 0b or Phase 2 speaks).
The load-bearing new content is the diagnostic, not the loss. The
architecture-causal version (indexer objective inside QSA-style continued
pretraining, or from-scratch hybrids with a parity tokenizer) is a gated Phase 2
under a separate contract.

## Mechanism

```text
Indexer (DSA token form; QSA block form with compress ratio 4), per sparse layer:
  I_t(s) = sum_{j=1..H_I} w_{t,j} * ReLU(q^I_{t,j} . k^I_s),   s <= t
  S_t    = Top-k_s I_t(s);  the sparse layer attends over S_t only
Distillation from the frozen layer (no gradient into the backbone):
  L_I    = KL( P^T_t || softmax_s I_t(s) ),  T in {head-sum (DSA), max-pool (QSA),
           retrieval-head-weighted}
Translation view on a bilingual document pair with the corpus's own sentence
alignment {(u_i, v_i)}, C = [D_b ; SEP ; D_a] and the reverse:
  A(t)   = tokens of v_i for a query token t in u_i, mapped to indexer granularity
  L_x    = -(1/|Q|) sum_{t in Q} log sum_{s in N(A(t))} softmax_s I_t(s)
  L_I'   = L_I + lambda_x L_x,   lambda_x in {0.25, 0.5}
Same-form controls: L_perm (labels permuted within document), L_half (whole
other-language half), L_sem (monolingual TyDi QA question -> gold passage, no
parallel data, iso-token).
Evaluation (never uses alignment labels); four query conditions share (H, N, p):
  ML mono-literal (verbatim needle sentence)        -> ceiling row only
  MN mono-non-literal (Belebele question in l_N)    -> reference leg
  CS cross same-script, CX cross cross-script (same question, human-translated)
  Held-out cross-script pairs: (l_N = X, l_Q = en) and (l_N = en, l_Q = X),
  X in {ja, ko, bn, ta, el, he, ka}  -> 14 pairs, both directions
  R_A(cond) for A in {ind^T, T, U};  U = fixed reference = union over heads of
  each head's own top-k under the frozen full attention (same k per head;
  superset budget; identical for every T); U_k = budget-matched sensitivity row
  Delta_A = R_A(MN) - R_A(CX)
  xi_T    = Delta_ind^T - Delta_T      (own-target excess; K1's uniform null; descriptive)
  xi^U_T  = Delta_ind^T - Delta_U      (excess over the fixed reference)
  S_T     = R^U(CX) - R_ind^T(CX)      (absolute cross-script shortfall from the reference)
  Lambda  = R(ML) - R(MN)              (literalness gap; reported separately)
  T*      = argmax_T R_ind^T(CX) on development languages at rho = 12.5%,
            subject to R_ind^T(MN) >= max_T' R_ind^T'(MN) - 2;  frozen before test
  D       = R_c(CX) - R_b(CX),  c = (T*)+L_x, b = (T*) KL-only   (PRIMARY, absolute points;
            read once on the Phase-1 primary passage partition)
  lambda_x* = argmax over {0.25, 0.5} of R_c(CX) on development languages within the
            2-point MN band (registered Phase-1 pre-step; frozen before the five-seed arms)
  se_D_up^2 = 2 sigma_up^2 / 5 + se_prompt^2   (wave 5: sigma_up = upper 80 percent chi-square
            bound of the pooled Phase-0a seed SD at its honest df, 6 on the 0.6B base;
            se_prompt = paired passage-cluster bootstrap SE of a null hs-vs-mp contrast on
            the Phase-0 audit partition at the primary prompt count)
  kappa   = max(0, min(3, 6 - 2 se_D_up))   (K2b threshold; confirm at max(6, MDE(se_D_up));
            both fixed from measured noise before Phase 1; kappa = 0 withholds Phase 1)
  rho_x   = D / xi^U_T*                (secondary, descriptive, intervals propagated)
```

Inference is unchanged. The label is a corpus property (ParaDocs, TED2020),
symmetric across scripts, and no external word aligner is used. Wave 4 moved
T* from argmin ξ_T to argmax CX recall because ξ_T subtracts the target's own
gap, so a cross-lingually weak target (retrieval heads are literal copy heads)
could shrink ξ without improving the indexer.

## Closest work and delta

| Closest work | Source | Same | Delta |
|---|---|---|---|
| DSA lightning indexer (KL to head-summed attention; 2.1B-token frozen warm-up, 943.7B unfrozen) | [2512.02556](https://arxiv.org/abs/2512.02556) | indexer and KL recipe | alignment-supervised selection term; per-language selection audit against the target and a fixed reference |
| QSA compressed-block indexer with max-pooled KL target (Eq. 17; only aggregate MMMLU 81.8 → 81.1 reported multilingually, Table 2; HTML read through §3.2) | [2608.30320](https://arxiv.org/abs/2608.30320) | block form, max-pool target (arm) | drop-in objective for that indexer; QSA recipe is a label-free counterfactual, not the proposal |
| SpotAttention frozen-backbone KL selector, dual top-p, English dense parity | [2606.22874](https://arxiv.org/abs/2606.22874) | frozen KL-only arm (re-implemented; no public code) | its cross-lingual audit plus a fix; its top-p rule is a mandatory control |
| Oracle-Guided Sparse Prefill: frozen KL indexer plus attention-mass top-k oracle separating budget feasibility from indexer error | [2606.07703](https://arxiv.org/abs/2606.07703) | monolingual precursor of the indexer-versus-target decomposition | cross-lingual axis; literalness control; fixed-reference comparison across aggregations |
| Guided/supervised NMT attention (Liu 2016, Chen 2016, Garg 2019); AlignAtt4LLM | [1609.04186](https://arxiv.org/abs/1609.04186), [1607.01628](https://arxiv.org/abs/1607.01628), [1909.02074](https://arxiv.org/abs/1909.02074), [2606.03967](https://arxiv.org/abs/2606.03967) | loss form on main attention | object is a detached selection indexer of a decoder-only sparse LM; corpus sentence labels; inference unchanged |
| Lost in Compression (cross-lingual gap of learned compressors tracks supervision data) | [2608.26175](https://arxiv.org/abs/2608.26175) | achieved-budget protocol adopted | attention indexers, not prompt compressors |
| NoLiMa, RULER, induction heads (literal-match retrieval is easy; non-literal collapses) | [2502.05167](https://arxiv.org/abs/2502.05167), [2404.06654](https://arxiv.org/abs/2404.06654), [2209.11895](https://arxiv.org/abs/2209.11895) | motivates the non-literal reference leg | none claimed; these are why the wave-2 statistic was not identified |
| Retrieval heads; RTPurbo (low-dimensional retrieval subspace, 16-dim indexer, top-k inferior to top-p) | [2404.15574](https://arxiv.org/abs/2404.15574), [2605.16928](https://arxiv.org/abs/2605.16928) | retrieval-head-weighted target (arm) | measured per language against the other aggregations and against the fixed reference; the reason T* is no longer chosen on ξ |
| MLNeedle, OneRuler, MGAL (dense cross-lingual long-context behaviour) | [2408.10151](https://arxiv.org/abs/2408.10151), [2503.01996](https://arxiv.org/abs/2503.01996), [2608.20853](https://arxiv.org/abs/2608.20853) | mandatory dense baselines and endpoints | localizes the gap to the selection component or exonerates it |

No direct prior art found through 2026-09-01 under the wave-1 novelty triad,
the wave-2 rechecks, the wave-2 novelty refuter's coverage (13 hostsearch,
10 WebSearch, 10 WebFetch; 10 of 13 arXiv boolean queries returned HTTP 429; 4
OpenReview hits unread) and the wave-4 read of the QSA HTML through §3.2, for
an alignment-supervised detached selection indexer or a per-language selection
audit of a learned sparse indexer. QSA tables after §3.2 and the GLM-5.3 report
remain unread. Pending a signed provider-distinct novelty review.

## Cheapest decisive pilot

CPU doctor (exists; ran 2026-09-01; no GPU):
`uv run python scripts/run_translation_supervised_indexer_doctor.py --output
data/results/translation-supervised-sparse-indexer/phase0-doctor.json` →
PHASE0_DOCTOR_PASS, 10 registered cases, 25 s, 16 pytest tests. It implements
the indexer, the hs/mp/rh targets and KL, R^U with a brute-force check and
U_k, selection recall and Δ/ξ/S/Λ/T*/λ_x/D, L_x with mass accounting and the
L_perm/L_half controls, the concatenation builder, the development/audit/
primary passage split with fail-closed reads, the noise model and κ, and every
gate as a pure function. Synthetic-case numbers (a two-script toy, not any
model): KL-only head-sum indexer CX 19–54 with R^T(CX) = R^U(CX) = 100 and
MN 98–100 (ξ_hs 52.2/80.0/46.5 at seeds 42–44), L_x repair D 51.0/80.5/46.5
on a language never seen by L_x, permuted-label gain −42.5/−13.8/−50.0,
other-half gain 12.0/29.0/6.8, shifted-script gain −0.5/−6.8/−1.5; max-pool
excluded from T* by the MN band despite the best CX. Its `evidence_grade`
says executability and gate semantics only. Still open on CPU: the
tokenizer-based TR-NIAH builder with the achieved-token ledger and exact
50-gram plus MinHash dedup on real corpora; a 20-prompt indexer-versus-target
smoke run on real hidden states in the re-pinned container under a Slurm
dry-run the wrapper accepts; the Q-head padding or gather path for fla
`parallel_nsa` (both bases fail its HQ/H ≥ 16 assertion).

Phase 0a (≤ 4 GPU-h, one job, the pilot of record): frozen `qwen3-0.6b-base`
(indexers on all 28 layers) and `qwen3.5-4b-base` (Qwen/Qwen3.5-4B-Base @
1001bb4d…, registered and fetched with a receipt on 2026-09-01; indexers on
its full-attention layers, placement to be re-read from the Base config);
three target aggregations × two indexer forms × 3 seeds per base plus a
three-point learning-rate sweep (block-form head-sum, seed 42, 0.6B), all in
one frozen-teacher stream on 50M tokens (half bilingual concatenations from
ParaDocs/TED2020, half FineWeb-2); E1 for indexer, target and fixed reference
on 4,000 audit-partition Belebele prompts per base — 2,000 at 8K, 1,200 at
16K, 800 at 32K — in held-out languages across the four conditions; adequacy
gate (English literal recall within 5 points of R^T); dense monolingual and
cross-lingual TR-NIAH headroom on 1,200 prompts per base. On development
languages: learning rate and T* (argmax CX recall within the 2-point MN band)
are frozen (λ_x moves to the Phase-1 pre-step). On the audit partition of the
held-out pairs: ξ_T (K1), the Δ_T and S_T sanity rows, K2a. Then the noise
model — σ̂ (6 df), σ_up, se_prompt (passage-cluster bootstrap) and κ — is
computed and recorded. Budget 2.64 base, 3.3 with reserve, cap 4 (E1 row
1.40 GPU-h with attention-score and indexer-scoring FLOPs included); the
once-only adequacy extension is a second conditional job (cap 1.5) that
displaces Phase 0b.
Decision: ξ_T ≥ 10 for some T and base, K2a not fired, κ above 0 → Phase 1;
ξ_T ≤ 5 everywhere → publish the localization negative and stop; K2a → publish
the recipe finding and stop the alignment line; κ = 0 → withhold Phase 1 and
publish the noise model.

Phase 1 (≤ 10 GPU-h, gated): pre-step — (T*)+L_x at λ_x 0.25 and 0.5 on
development languages only (block form, seed 42, 0.6B, about 0.04 GPU-h),
λ_x frozen by development CX recall within the MN band and recorded; then
arms (a) KL-T* monolingual, (b) KL-T* bilingual [primary counterfactual], (b′)/(b″) the other aggregations, (c) KL-T* + L_x
[primary treatment], (c′) head-sum + L_x [DSA-style secondary], (d) L_perm,
(e) L_half, (i) L_sem, (h) dim ladder 64/256 for (b) and (c) — 13 block-form
configurations × **five seeds 42–46, unconditional** = 65 indexers; token form
for (b), (c) × 3 seeds (descriptive); 4B replicate of (b), (c), (d), (i) × 2
seeds (descriptive); dense LoRA pair (j) LM-only and (k) LM + L_x; training-free
controls at eval only; E1 on all five seeds, E2 on seeds 42–44. Primary
endpoint: D = (c) − (b) on the 14 held-out cross-script pairs at ρ = 12.5%, 8K,
read once on the primary passage partition: confirm at D ≥ max(6, MDE) with
the 99% paired passage-cluster interval excluding zero and MN within 1 point;
K2b at D ≤ κ; the band between is pre-registered inconclusive (no claim, no
promotion). Budget 7.74 base, 9.7 with reserve, cap 10.

Phase 0b (optional, ≤ 2 GPU-h, descriptive): inference-only probe of the
production QSA indexer in Qwen3.8-Flash-Next on 120 prompts with a 6 s abort
threshold; dropped if the adequacy-extension job ran. Total ≤ 16 GPU-h;
Phase 2 is a separate contract.

## Controls

Strongest label-free target T* (by absolute CX recall within the MN band;
primary) and the DSA head-sum recipe (secondary); full aggregation ladder with
the Δ_T and S_T rows for K2a against the fixed reference R^U (and the
budget-matched U_k sensitivity row); learning-rate sweep on development
languages; L_perm and L_half with inertness preconditions (|d − b| ≤ 1,
|e − b| ≤ 1); information-matched L_sem; dense LoRA pair (LM-only, LM + L_x);
achieved-budget ρ, fixed k, fertility-scaled k, SpotAttention dual top-p;
larger k at matched measured latency, PIVOT-style re-scoring, NSA pooled-key
selection, SWA plus sinks at matched KV bytes; oracle needle-block with random
fill, random-plus-needle, needle-absent; MLNeedle and OneRuler dense baselines;
literal-copy ceiling and Λ; indexer dim ladder; iso-token and iso-order in one
teacher stream; held-out languages never seen by any supervised loss; both
query directions; prefix-invariance audit; per-language floor and English E3
non-regression; five seeds for every block-form Phase-1 arm.

## Falsifiers

- K1: ξ_T ≤ 5 for every aggregation on both bases (adequacy gate passed).
- K2a (absolute form): with S_hs = R^U(CX) − R_ind^hs(CX) ≥ 3, the best
  label-free indexer's CX gain over the head-sum indexer reaches ≥ 80% of S_hs.
- K2b: D ≤ κ, κ = max(0, min(3, 6 − 2·se_D_up)), se_D_up² = 2·σ_up²/5 +
  se_prompt² from the measured Phase-0a noise model (σ̂ at 6 df, upper 80%
  bound; passage-cluster bootstrap se_prompt); under the assumed inputs
  σ̂ = 2, se_prompt = 1.3 this is κ ≈ 1.6 with MDE ≈ 7.5; κ under D under the
  confirm threshold is inconclusive, not a kill and not a pass; κ = 0
  withholds Phase 1.
- K3: with inertness holding, the L_perm or L_half absolute gain reaches ≥ 80%
  of D.
- K4: the L_sem absolute gain reaches ≥ 50% of D on held-out cross-script pairs.
- K5: a training-free control at matched budget recovers ≥ 80% of the E2 gain.
- K6: the L_x-specific dense LoRA gain reaches ≥ 80% of the sparse E2 gain.
- K7: gains confined to in-training languages (kill); E1 gains without E2
  gains are inconclusive, not a kill (E2 MDE ≈ 8.4 EM points at 3 seeds and
  1,500 prompts, above the registered 8).
- K8: any held-out language loses over 2 recall points or English E3 loses
  over 0.5.
- K9: dense cross-lingual TR-NIAH EM under 40% on both bases withdraws the E2
  claim; a sparse floor under R^T − 5 makes E2 contrasts on that base
  floor-bound. Any E2 score above dense counts only with oracle-sign agreement.

## Compute

Phase 0a ≤ 4, Phase 1 ≤ 10, Phase 0b ≤ 2 GPU-h on the 8 × H100 node; assumed
30% MFU (297 TFLOPS/GPU, 2.0 TB/s effective; the H100 page lists 1,979 BF16
TFLOPS with sparsity and 3.35 TB/s, fetched 2026-09-01), measured by the first
job and re-verified before Phase 1. Pilot image of record (wave 5):
`cotcodec-research:999f5583-architecture`, image ID
`sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad`,
repo digest
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`
(Slurm job 353 from commit 999f5583; torch 2.11.0+cu128, transformers 5.15.0,
fla 0.5.2, triton 3.6.0). It still lacks tilelang (being added: fla 0.5.2
refuses the gated GDN backward on Hopper under Triton below 3.7.1, fla #640),
peft and this contract's code, so it must be rebuilt and re-pinned before
image_id is filled; the older discovery image (15d6abc0…) and the jobs
335–341 image (3f58e525…) are provenance anchors only. Checkpoint receipts
exist on fal-h100-01 (job 356, /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/)
for qwen3.5-4b-base and nine other pilot checkpoints, not yet for
qwen3-0.6b-base, and none is copied into the manifest. The contract carries
the wrapper's declarable manifest fields
(runtime docker-single-node-discovery-v1, 8 × H100 for 30 minutes = the 4 GPU-h
Phase-0a cap, seeds, run_root, model id and revision, command) and omits
image_id, git_sha, source_sha256 and the model receipt digests because none
exist; `scripts/submit_docker_research_job.py --dry-run` therefore exits 1 at
"image_id must be an exact local Docker sha256 image ID" (re-run in wave 5,
same rejection; wave 3 was rejected at the runtime field). Seeds 42/43/44 in
Phase 0a; 42–46 unconditional for block-form Phase-1 arms; κ and the confirm
threshold fixed from the measured Phase-0a noise model before Phase 1 is
submitted (the wave-4 seed-only MDE of 4.3 is withdrawn; about 7.5 under the
assumed inputs). SIGUSR1 arrives 180 s before the
time limit (`--signal=B:USR1@180` in the batch script); checkpoints every 15
minutes; fresh-job resume test per phase. Tinker is not used (no indexer
access; key absent).

## Kevin advantage

The pilot depends on no private asset. What makes it easy here: a Docker/Slurm
harness that trains many detached indexers in one shared frozen-teacher stream
under one sbatch; a repository whose product is exactly this instrument
(per-language achieved-token ledger, indexer-versus-target and
indexer-versus-fixed-reference selection recall, sealed receipts); General
Translation's document-level parallel pairs with alignment QA as an optional
upgrade for low-resource cross-script pairs and as the Phase-2
continued-pretraining corpus; and a genuine deployment interest —
cross-lingual long-context retrieval over translation memories under a sparse
indexer — that no sparse-attention lab has stated.

## Negative-result value

K1 localizes the cross-lingual long-context gap to attention mass rather than
selection — the first component-level answer to what MLNeedle, OneRuler and
MGAL only describe — and leaves a portable selection-recall instrument. K2a is a
free recipe finding comparing the DSA and QSA target choices per language, now
with the Δ_T row saying whose *target* is cross-lingually weak. K2b says
bilingual exposure alone repairs indexers. The inconclusive band publishes the
measured seed variance of indexer recall, which no indexer paper reports; κ = 0
says the instrument is too noisy for two-arm contrasts at this scale. K3 says a
mass-concentration regularizer is what indexers need. K4 says parallel data is
not the active ingredient, redirecting the program away from its unique asset
early. K6 says alignment supervision is a generic attention fix. The literalness
gap Λ is publishable alone as the first literal-versus-semantic decomposition
for learned selectors. Phase 0b reports whether a production indexer agrees
either way.

## 2026-09-01 wave-3 identification re-registration

Wave 1 killed the candidate (identification 0.8, feasibility 0.8; novelty not
refuted). Wave 2 repaired it to attachment-capability with sealed non-label
endpoints and public data and scored 64/61 (lower authoritative; cap 89), with
identification still refuted (0.72) because the counterfactual for every L_x
claim was the head-sum KL arm and the kill statistic compared a verbatim-copy
monolingual query with a zero-overlap cross-lingual query. Wave 3 applied the
judges' union highest-impact fix as one repair: non-literal ξ with the Belebele
question-as-query reference and a literal ceiling row; T* as the primary
counterfactual with K2a/K2b; inertness preconditions; L_sem and LM-only LoRA
arms; G1/G2 headroom gates, oracle-sign rule and needle-absent control on the
generation endpoint; 2606.07703 cited; RTPurbo id corrected to 2605.16928;
adequacy gate; parallel_nsa head-padding; Phase 0b at 6 s and 120 prompts;
qwen3.5-4b relabelled post-trained. Budget re-derived to 4 + 10 + 2 = 16 GPU-h.
Two fresh reviewers scored the wave-3 text 66/66.

## 2026-09-01 wave-4 decision-rule and T*/K2a re-registration

Score history: wave 1 killed (0) → wave 2 61 → wave 3 66 → wave 4 unjudged.
The wave-3 reviewers found two new fatal defects: (A) at the registered P1
gate the confirm (≥ 6 points) and kill (under 3 points) regions were 3 points
apart inside the design's own 5.6-point MDE, the recovery ratio divided by a
Phase-0 estimate with no interval, the wrapper dry-run rejected the contract,
and the "only real image" claim was stale against job 335–341 receipts; (B) T*
= argmin ξ_T and K2a on ξ_T*/ξ_hs could be satisfied by a cross-lingually
weaker target. Wave 4 applied the union of both highest-impact fixes (they were
compatible): T* by absolute CX recall within a 2-point MN band; one fixed
reference R^U shared by every aggregation with a budget-matched U_k sensitivity
row; K2a on the head-sum indexer's absolute cross-script shortfall (evaluable
when S_hs ≥ 3); ξ_T kept as K1's uniform null and as a descriptive table with a
Δ_T sanity row; the primary endpoint restated as the absolute gain D ≥ 6 with
five unconditional seeds for block-form arms (MDE about 4.3), K2b at D ≤ κ from
the measured Phase-0a seed SD so the regions are at least two SEs apart, a
pre-registered inconclusive band, Phase 1 withheld if κ = 0, and ρ_x demoted to
descriptive with propagated intervals; the contract given the wrapper's
declarable manifest fields and the dry-run re-run (now exits 1 at image_id,
recorded verbatim); image provenance corrected to both recorded real images and
the SIGUSR1 offset to 180 s. Without inventing evidence, the TED policy, TyDi QA
card and H100 page were fetched (TyDi QA license found conflicting and now gates
the L_sem arm), the QSA HTML was read through §3.2 (only aggregate MMMLU;
max-pool target Eq. 17 confirmed), a learning-rate sweep was added, and the 14
held-out cross-script pairs were enumerated. Budgets: Phase 0a 2.37/3.0/cap 4;
Phase 1 7.7/9.6/cap 10; total 16 GPU-h. Pending re-judging.

## 2026-09-01 wave-5 executable doctor and noise-model re-registration

Score history: wave 1 killed (0) → wave 2 61 → wave 3 66 → wave 4 62 (lower of
62/69; a dip, recorded) → wave 5 unjudged. The wave-4 reviewers' fatal defects:
(A, authoritative) the decision rule rested on a noise model the text
contradicted — σ̂ had 6 df on the 0.6B base, not 12; the seed-only SE of 1.26
ignored the stated prompt SE of 1.3 (combined MDE near 6.2, separation about
1.7 SE); and the Phase-0a gates read the same sealed prompts as D; (B) λ_x was
declared frozen in Phase 0a where no L_x indexer is trained and Phase 1 had no
λ_x sweep; the E1 FLOP row was reproducible only with attention FLOPs
excluded. Wave 5 applied both as one compatible repair: a three-way passage
partition (development / Phase-0 audit / Phase-1 primary) with fail-closed
reads; σ̂ at its honest 6 df with an upper 80 percent chi-square bound;
se_prompt measured by a paired passage-cluster bootstrap of a null hs-vs-mp
contrast; se_D_up² = 2·σ_up²/5 + se_prompt²; κ = max(0, min(3, 6 − 2·se_D_up))
and confirm at max(6, MDE(se_D_up)), both fixed from measured noise with
pre-registered fallbacks; E2 MDE stated (about 8.4) and K7's "E1 without E2"
demoted to inconclusive; a budgeted Phase-1 λ_x pre-step on development
languages; the E1 row re-derived with unambiguous prompt counts and
attention-score plus indexer-scoring FLOPs (Phase 0a 2.64/3.3/cap 4; the
adequacy extension a second conditional job). The executable pilot now
exists: `harness/translation_supervised_indexer.py`,
`scripts/run_translation_supervised_indexer_doctor.py` and 16 tests; the
doctor passed on 10 registered synthetic cases in 25 s (receipt
`data/results/translation-supervised-sparse-indexer/phase0-doctor.json`,
evidence grade executability and gate semantics only), and the contract
carries a `reference_doctor` block (validator PASS). Provenance: the rebuilt
fla image cited as the pilot image with what it still lacks; ten checkpoint
receipts cited; the 4B arms moved to the now-registered qwen3.5-4b-base; the
dry-run re-run still exits at image_id. Compute stays FAIL: no GPU entry
point, no image with this code, no accepted dry-run, no evidence bundle, no
signed review. Pending re-judging.
