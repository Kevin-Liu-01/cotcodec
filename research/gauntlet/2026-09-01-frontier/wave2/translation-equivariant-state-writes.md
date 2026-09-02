# translation-equivariant-state-writes — wave-2 repaired candidate (C2)

Repair owner note, 2026-09-01. Wave-1 verdicts: novelty NOT refuted (0.6; "recombination of known ingredients;
novelty rests on the new object and the instrument"), identification REFUTED (0.8), feasibility REFUTED (0.7).
Every objection is mapped to a fix or an accepted limitation in §"Repairs made". Nothing below depends on
General Translation data; GT data is an optional upgrade only.

## Claim

A fixed-size recurrent state that stores meaning should write the same segment delta for two translations of
the same span. On a matched hybrid/dense pair the translation-paired MQAR instrument, with state-level
interventions (delta-zeroing, training-free delta transport, delta swap), first measures whether a 2026 GDN
hybrid's recurrent state stores meaning or surface (phase 0, the kill screen). If the state carries recall and
shows a hybrid-specific cross-lingual gap that a training-free linear transport cannot close, supervising the
per-head state delta on public bitext in half the GDN heads closes >= 50% of that gap at equal monolingual
recall and LM loss, and beats a same-layer projection-alignment control that has no recurrence (phase 1).

**claim_scope.** architecture-causal.

## Mechanism

Hybrid with Gated DeltaNet (GDN) layers. Per layer l and head h the state follows the fla convention
S_t = S_{t-1} (alpha_t (I - beta_t k_t k_t^T)) + beta_t v_t k_t^T (fla `chunk_gated_delta_rule`, which accepts
`initial_state` and returns the final state; its backward accepts `dht`, so a loss on a final state is
differentiable: https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/gated_delta_rule/chunk.py).

**Segment delta.** For a span a after a shared prefix c: D^{(l,h)}(a | c) = S(c ⊕ a) - S(c). For a parallel pair
(a^A, a^B) both spans follow the same prefix, so S_before = S(c) is bitwise identical and D^A, D^B differ only
in the span. Computation: one pass over c (output final state), two short passes over a^A and a^B with
`initial_state = S(c)`. Note (identification refuter, accepted): D = sum_t (prod decays) beta_t v_t k_t^T +
(prod alpha_t (I - beta_t k_t k_t^T) - I) S_before, i.e. a recurrence-weighted bilinear pooling of the span's
projections plus an erase term acting on S_before. The decisive control below removes exactly the recurrence.

**Treatment loss (arm A1).** L = L_LM + lambda (L_eq + L_nce), on head subset E = half the heads of every GDN
layer. L_eq = mean_{l, h in E} (1 - cos(vec D^A, vec D^B)). L_nce = -log( exp(s(D^A, D^B)/tau) /
sum_{B' in batch} exp(s(D^A, D^{B'})/tau) ), s = cosine over concatenated E-head deltas, tau = 0.07, lambda in
{0.1, 0.3}. Negatives: the batch's other spans PLUS >= 2 hard negatives per anchor that share a named entity
string or a number with a^A but are not its translation (entity-grouped sampling from the bitext). Heads
outside E carry no alignment term.

**Decisive control (arm A2, same-layer projection alignment, no recurrence).** Identical L_eq + L_nce, lambda,
tau, negatives, layers and heads, applied to P^{(l,h)}(a) = sum_{t in a} beta_t v_t k_t^T — the decay-free,
erase-free bilinear pooling of the same E heads' projections over the same span (same d_k x d_v shape). A1 - A2
isolates "align the recurrent write" from "align the projections that feed it".

**Placebo (arm A3, language-marginal).** Identical loss form and lambda, but a^B is replaced by a random
non-translation span of language B drawn by a permutation sampled independently of content. By construction
the pairing carries no information about the content of a^A (only the language marginal), so any A3 gain is
regularization or language-marginal alignment, not translation equivariance.

**Instrument: TP-MQAR-v2 (translation-paired MQAR).** N facts, each "<key sentence in language A> <separator_A>
<4-digit ASCII code>", among distractor sentences in language A; query = "<key sentence translated into
language B> <separator_B>"; answer = the code, scored by exact match on digits only (answer-language-invariant;
removes the value-translation confound). Key-language x query-language matrix; N in {8, 32}; context 4K (phase
0) and 1K–8K (phase 1, 4x training length). Two key types, built in phase 0 from FLORES+ devtest: surface-disjoint
(after NFKC + casefold, no shared alphanumeric token >= 3 chars, no shared digit string, and for Zh/Th no Latin
token at all) and surface-shared (the complement: shared names or numbers). The surface-disjoint subset is the
primary endpoint; the surface-shared subset is the copy-shortcut probe.

**State-level interventions (frozen or trained models, no gradients).** (i) D-zero: after the fact span,
S <- S_before in all GDN layers — recall that survives is carried by attention. (ii) Training-free transport:
per-head ridge map W_h fitted on 2 x 997 FLORES+ dev pairs (min ||W_h vec D^A - vec D^B||^2 + mu ||W_h||^2, rank
capped by SVD), applied as S <- S_before + unvec(W_h vec D^A) before a language-B query — if this closes the
gap, the state already stores meaning up to a linear language transform and training is redundant. (iii) Swap:
S <- S_before + D^B (E heads in phase 1; all heads in phase 0) and re-read (GI-SAE's interchangeability
criterion). All three require only the recurrent-state handle that transformers exposes for `olmo_hybrid`
(`cache_params.layers[i].recurrent_states`, `torch_chunk_gated_delta_rule` fallback to fla).

**Phase-1 architecture choice.** From-scratch hybrids use sliding-window attention (window 512) in the 1-in-4
attention layers, so a fact placed > 512 tokens before the query can be recalled only through the recurrent
state (beyond-window recall). This makes the causal carrier the state by construction instead of by
assumption (Gather-and-Aggregate 2504.18574 and Attention Amnesia 2606.11052 show hybrid recall otherwise
concentrates in a few softmax heads). The dense control is a full-attention transformer.

## What is new (downgraded per the novelty refuter)

The loss form is standard (translation-pair cosine + InfoNCE as in LaBSE/SONAR/Middle-Layer alignment/PreAlign);
MQAR, cross-lingual NIAH (MLNeedle, OneRuler) and the functional-swap criterion (GI-SAE) exist. What has no
located prior is (a) the object — the per-head recurrent-state segment delta of a GDN hybrid — as the target
of a translation-equivariance loss, and (b) the instrument — translation-paired recall with state-level
interventions (delta-zeroing, training-free delta transport, delta swap) on a matched hybrid/dense pair. The
Olmo pair has been used once as a matched instrument (2606.20936: monolingual token-level loss; no cross-lingual
axis, no state intervention). No direct prior art found through 2026-09-01 under: arXiv API x7 (cross-lingual x
linear attention/GDN/SSM/hybrid x recall; translation/parallel data x recurrent state x
equivariance/alignment; Olmo Hybrid), HF papers x2, OpenReview x1 (forum pages CAPTCHA-blocked, titles
unverified), plus the wave-1 novelty refuter's ~21 queries.

## Closest priors (delta each)

- MLNeedle — https://arxiv.org/abs/2408.10151 — 2024-08-19 — cross-lingual needle retrieval on dense 2024
  transformers; no recurrent operators, no capacity curves, no matched pair, no intervention. Baseline.
- OneRuler — https://arxiv.org/abs/2503.01996 — 2025-03-03 — multilingual RULER; instruction/context language
  mismatch swings dense models up to 20%; motivates the matched-pair difference-of-differences design. Baseline.
- On the limited utility of parallel data (Leino & Tiedemann) — https://arxiv.org/abs/2603.29026 — 2026-03-30 —
  bitext in the mixture barely moves residual alignment at 1.4B/200B; here bitext exposure is a live arm (A5 vs
  A0) in our regime, not an imported null, and the loss acts on the write.
- Middle-Layer Representation Alignment — https://arxiv.org/abs/2502.14830 — 2025-02-20 — residual-stream
  alignment of transformers; replaced as the decisive control by same-layer projection alignment (A2), which
  matches layers, heads, pooling shape and loss scale.
- GI-SAE — https://arxiv.org/abs/2608.23809 — 2026-08 — functional-swap criterion on SAE features of
  transformers; here applied to recurrent-state deltas.
- Gather-and-Aggregate (Bick, Xing, Gu) — https://arxiv.org/abs/2504.18574 — 2025-04 — recall in hybrids is
  delegated to a few softmax heads; motivates D-zero and the SWA design. Attention Amnesia —
  https://arxiv.org/abs/2606.11052 — 2026-06 — repairs hybrid long-context recall by restoring softmax W_Q/W_K.
- Comparing Transformers and Hybrid Models at the Token Level — https://arxiv.org/abs/2606.20936 — 2026-06-18 —
  same Olmo pair as a matched instrument; hybrid loss advantage vanishes on repeated n-grams (copying is
  attention's job). Monolingual; no state intervention. Closest instrument prior.
- Olmo Hybrid: From Theory to Practice and Back — https://arxiv.org/abs/2604.03444 — 2026-04-03 — the substrate;
  Ai2 blog (https://allenai.org/blog/olmohybrid): same Olmo 3 data mix, 6T tokens, 3:1 GDN, throughput-matched
  to Olmo 3 7B.
- PICASO — https://arxiv.org/abs/2502.17605 — 2025-02 — composes SSM states; English, no learned loss.

## Falsifiable predictions

- P0a (phase 0, frozen, surface-disjoint keys, N = 16, 4K, cells En<->De and En<->Es): Olmo-Hybrid-7B's
  cross-lingual gap G = EM[A = B] - EM[A != B] exceeds Olmo-3-1025-7B's gap by >= 8 EM points (paired bootstrap
  over prompts, 95% CI excluding 0). Embarrassing if the two gaps are within 3 points.
- P0b (D-zero): zeroing the fact's GDN span deltas in all 24 linear layers of Olmo-Hybrid-7B removes >= 30% of
  its cross-lingual recall (relative); embarrassing if <= 10% (attention carries recall; state is a bystander).
- P0c (training-free transport): per-head ridge transport fitted on FLORES+ dev closes <= 40% of the hybrid's
  gap on devtest keys; embarrassing if >= 80% (state already stores meaning up to a linear transform).
- P1 (phase 1, 57M SWA-512 + GDN hybrids, 3 seeds, beyond-window facts, surface-disjoint keys): A1 closes >= 50%
  of A0's cross-lingual gap with monolingual EM within 2 points and held-out LM loss within 0.5%; A2 closes
  <= 25%; A3 closes <= 10%; the A1 - A2 difference is >= 5 points and same-signed in all 3 seed pairs.
- P2 (shortcut and swap): A1's closure on surface-disjoint keys is within 10 points of its closure on
  surface-shared keys; swapping D^A -> D^B in E heads preserves >= 80% of recall in A1 vs <= 40% in A0.

## Kill conditions

- Phase 0: hybrid-specific gap <= 3 points (fixed-size states already store meaning; publish the instrument
  result and stop the training arm); or D-zero removes <= 10% of recall (state is not the carrier); or
  training-free transport closes >= 80% of the gap (training redundant).
- Phase 1: A1 does not beat A2 by >= 5 points paired over seeds (projection alignment suffices; the write
  object adds nothing); or A3 (placebo) closes >= 50% of what A1 closes (regularization, not equivariance); or
  closure appears on surface-shared keys but not surface-disjoint keys (copy shortcut); or LM loss > 1% worse or
  mean ||D|| in E heads shrinks > 30% (collapse/tax); or A5 (no bitext) equals A0 within 2 points while A1 is
  only better than A5 (the effect is bitext exposure, not the loss).
- Gates that abort rather than reinterpret: phase-0 language-competence gate (monolingual A = B EM at N = 8
  must be >= 60% in BOTH Olmo models for a language, else the language is dropped; if no non-English language
  passes, phase 0 cannot be run on this pair and the candidate falls back to instrument-only cells with no
  causal claim); phase-1 recall gate (A0 monolingual in-window EM >= 70% at N = 8 at 200M tokens, else phase 1
  is extended with a new budget line, not re-read).

## Cheapest decisive pilot = Phase 0 kill screen (<= 3.2 GPU-h, 8xH100 node, 2 GPUs in parallel)

Phase 0 decides three kill conditions and is the gate for phase 1. CPU doctor first, then the frozen screen.

**CPU doctor (no GPU).** Build TP-MQAR-v2 from FLORES+ devtest (En, De, Es, Zh, Th; 1,012 multi-way parallel
sentences); split into surface-disjoint / surface-shared subsets; per-language separator strings (5 short
phrases, hand-checked); leakage doctor: retrieval-impossible control (key absent -> EM at chance 1e-4),
value-permutation control, first-token key perturbation; exact-delta check on a 2-layer GDN in fp64 (fla vs
pure PyTorch: D^A, D^B are exact span deltas; S_before bitwise identical across the pair); dedup of all FLORES+
sentences against phase-1 training data (exact + MinHash 5-gram).

**Frozen screen.** Models (add to models/registry.yaml with 40-hex revisions):
- `allenai/Olmo-Hybrid-7B` revision `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` (Apache-2.0; `olmo_hybrid`, 24
  GDN + 8 full-attention layers at positions 4, 8, ..., 32; transformers >= 5.8.1 native; recurrent states
  exposed) — https://huggingface.co/allenai/Olmo-Hybrid-7B
- `allenai/Olmo-3-1025-7B` revision `a81bae42db3975be1671e27b9c9a56da1a9f980f` (Apache-2.0; `olmo3`, 24
  sliding-attention (window 4096) + 8 full-attention layers at the same positions) —
  https://huggingface.co/allenai/Olmo-3-1025-7B
  Ai2 describes the pair as the Olmo 3 blueprint with the hybrid substitution, same data mix, 6T tokens,
  throughput-matched (hidden 3840 vs 4096; vocab 100352 vs 100278, same tokenizer family). At 4K context the
  dense model's SWA layers see the whole prompt, so the only architectural difference is 24 GDN vs 24 softmax
  layers. Limitation: both cards list English; hence the language-competence gate and Latin-script cells only.
Cells: languages {En, De, Es} -> 9 key x query cells; 2 key types; N in {8, 32}; 150 prompts per cell; 4K
context (8K as a secondary run only if budget remains). Interventions on the hybrid: D-zero (9 cells), transport
(6 cross cells), swap (6 cross cells). ~19,800 prompt evaluations plus transport fitting.
Budget: 7B forward at 4K ~= 57 TFLOP -> ~0.14 s at ~400 TFLOP/s; <= 8 generated tokens ~0.12 s; chunked prefill
with state snapshots +50% -> ~0.4 s/prompt; 19,800 x 0.4 s = 2.2 GPU-h; transport fitting + gates + smoke 0.3
GPU-h; total 2.5 GPU-h; +25% reserve = 3.2 GPU-h. Optional instrument-only cells (no causal claim; separate
budget): registry `qwen3.5-4b`, `kimi-linear-48b-a3b-base` (98 GB bf16, >= 2 GPUs, remote code).

**Phase 1 (gated on phase 0 passing all three kills; <= 11.6 GPU-h incl. reserve).** From-scratch 57M models:
12 layers, d = 512, SwiGLU 1536, 8 heads, tied 32K SentencePiece unigram tokenizer trained on the phase-1
mixture (embedding 16.4M, body ~41M). Hybrid arms: 9 GDN layers (k dim 64, v dim 128) + 3 SWA-512 attention
layers at 4, 8, 12. Dense arm: 12 full-attention layers, params matched within 3% via FFN width. Arms x 3 seeds:
A0 hybrid, bitext in mixture, lambda = 0 (baseline); A1 treatment; A2 same-layer projection control; A3
language-marginal placebo; A4 dense full-attention, lambda = 0; A5 hybrid on an iso-token monolingual-only
stream (bitext replaced by monolingual text of the same languages and proportions). Data per run (200M tokens):
75% monolingual (En 60M, De 30M, Zh 30M, Th 30M), 20% bitext presented as prefix-sharing pairs (En–De 16M,
En–Zh 14M, En–Th 10M), 5% synthetic monolingual recall curriculum (facts and queries in the SAME language only;
keys from ParaCrawl sentences, digit values; the cross-lingual cells and FLORES+ keys are never seen in
training). LR sweep: 4 values x {A0, A1} x 1 seed x 60M tokens; the winner per arm is used for all seeds.
Evaluation: TP-MQAR-v2 at 1K–8K on beyond-window facts, swap tests, held-out LM loss, FLORES+ devtest
bits-per-byte per language.
Throughput basis (cited): llm.c GPT-2 124M reaches 3.91M tok/s on 8xH100 = ~489K tok/s/GPU with custom CUDA at
1024 context (https://github.com/karpathy/llm.c/discussions/481); Gated DeltaNet 1.3B trains at ~30–45K tok/s
on one H100 at 4K (2412.06464 Fig. 3, ~32% MFU with fla Triton kernels). A 57M PyTorch + fla model will not
reach either MFU; planning number 150K tok/s/GPU (~5% of H100 dense bf16 peak at 0.34 GFLOP/token), verified in
a 50M-token smoke run; gate: measured < 100K tok/s -> cut tokens/run to 160M. Cost: plain arms (A0, A4, A5)
9 runs x 200M / 150K tok/s = 9 x 0.37 GPU-h = 3.3; alignment arms (A1–A3; prefix duplication for bitext pairs
and delta extraction, factor 1.3) 9 x 0.48 = 4.3; LR sweep 8 x 60M x (1.15 avg factor) = 1.1; evaluation 0.6;
sum 9.3 GPU-h; +25% reserve = 11.6 GPU-h. Phase 0 + phase 1 = 14.8 GPU-h <= 16. Seeds: 3 per arm; if A0's
seed SD of the cross-lingual gap exceeds 3 points, A0/A1/A2 get 2 more seeds (+2.9 GPU-h, separate line).
Jobs: digest-pinned Docker via sbatch, fla v0.5.2, SIGUSR1 checkpoint + fresh-job resume, checkpoints to
/home/kevin/cotcodec-runs.

**pilot_gpu_hours.** 3.2 (phase 0, the cheapest decisive pilot); phase 1 gated at 11.6; total 14.8.

## Controls (all named)

Frozen: matched hybrid/dense pair (Olmo-Hybrid-7B vs Olmo-3-1025-7B, same data/tokens/tokenizer family);
D-zero ablation; training-free per-head ridge/Procrustes transport (state-surgery control); swap test;
surface-disjoint vs surface-shared key types; retrieval-impossible and value-permutation leakage controls;
language-competence gate; digit-only exact match. From scratch (iso-parameter within 3%, iso-tokens,
iso-corpus, same tokenizer and seeds): A0 baseline (bitext, lambda = 0); A2 same-layer projection alignment
(same E heads, loss, lambda, tau, negatives, no recurrence); A3 language-marginal placebo (content-independent
pairing); A4 dense full-attention transformer; A5 no-bitext iso-token ladder rung; hard negatives sharing
entities/numbers; beyond-window facts (SWA-512) so recall is state-carried by construction; held-out LM loss
never sees the alignment terms; 4x OOD length; paired-by-seed differences with clustered SEs; optional
middle-layer hidden-state alignment (2502.14830) as a secondary control. Published baselines to cite for the
instrument: MLNeedle, OneRuler (dense cross-lingual retrieval); QED (2608.13668), MARCH and SWA+sinks
(2608.28444) remain the mandatory recall-interference baselines if the direction reaches a recall-improvement
claim beyond the pilot.

## Public data plan (no GT data required)

- Evaluation keys and transport-fitting pairs: FLORES+ (`openlanguagedata/flores_plus`, CC BY-SA 4.0, gated
  acceptance of terms; 230 varieties incl. deu_Latn, spa_Latn, cmn_Hans, tha_Thai, ben_Beng; dev 997 / devtest
  1,012 sentences) — https://huggingface.co/datasets/openlanguagedata/flores_plus. Dev -> transport maps;
  devtest -> TP-MQAR-v2 keys. Derived instrument released CC BY-SA 4.0 (share-alike).
- Monolingual pretraining: FineWeb-2 (`HuggingFaceFW/fineweb-2`, ODC-By 1.0; configs deu_Latn, cmn_Hani,
  tha_Thai; ben_Beng available for extensions) — https://huggingface.co/datasets/HuggingFaceFW/fineweb-2;
  English from `HuggingFaceFW/fineweb` (ODC-By 1.0 per dataset card).
- Bitext: ParaCrawl v9 En–De (278.3M pairs) and ParaCrawl bonus En–Zh (14.17M pairs), both CC0 —
  https://paracrawl.eu/ ; SCB-MT-EN-TH-2020 (`airesearch/scb_mt_enth_2020`, CC BY-SA 4.0, ~1M En–Th pairs) —
  https://huggingface.co/datasets/airesearch/scb_mt_enth_2020. Sentence-level alignment suffices because keys
  are whole sentences and bitext spans are whole sentences.
- Checkpoints: Olmo-Hybrid-7B and Olmo-3-1025-7B (Apache-2.0), revisions above. Kernels: fla v0.5.2
  (https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2).
- Optional GT upgrade (not required by any prediction): sub-sentence span alignment for shorter spans,
  professionally translated separators/keys in Bn/Ja/Ar, Thai/Bengali quality audit. Never customer content.

## Kevin advantage (honest)

Not required for the pilot: it runs entirely on public data and Apache-2.0 checkpoints. Real but optional: GT's
span-aligned corpora and in-house translators extend the instrument to sub-sentence spans and to Bn/Ja/Ar;
the 8xH100 node and the Docker/Slurm/checkpoint harness make the 18-run phase-1 grid a two-day job; two hybrid
families are already registered for instrument-only extensions (qwen3.5-4b GDN, kimi-linear-48b-a3b-base KDA).

## collision_risk

medium. The mechanism half (equivariance loss on the recurrent write) has no located prior; the instrument half
is cheap for others to run now that a matched Olmo pair exists and has already been used once as a matched
instrument (2606.20936, monolingual). Searches: wave-1 novelty refuter (~21 queries, listed in wave1-verdicts)
plus this owner's arXiv x3, HF papers x1, OpenReview x1 on 2026-09-01 (log: design/wave2/tesw-search.log).

## Monitorability and safety

CoT untouched; no action channel. A meaning-level state may help monitors trained in one language transfer
(testable later against 2605.27901's 13-language fragility set) or remove surface cues monitors use — report
both. Data rights: CC0 (ParaCrawl), CC BY-SA 4.0 (FLORES+, SCB-MT; derived instrument share-alike), ODC-By
(FineWeb/FineWeb-2, attribution), Apache-2.0 checkpoints; GT data optional, never customer content. IP: no
kernel-level delta-rule change (the loss sits on top of fla kernels), so the NVIDIA gated-delta patent flag
does not apply to the contribution.

## Negative-result value

Phase 0 alone yields the first matched hybrid-vs-dense cross-lingual recall measurement with state-level
ablations: "states store meaning" (gap within 3 points), "attention carries hybrid recall" (D-zero), or
"meaning up to a linear transform" (transport) each close G2 cheaply and are publishable. Phase 1 negatives:
A1 = A2 says the write object is redundant given projection alignment (extends 2603.29026's family to
recurrent writes); A3 = A1 says the gain is regularization; closure only on surface-shared keys documents a
copy shortcut that any future cross-lingual state claim must control for. TP-MQAR-v2 remains the G2/G20
instrument in every branch.

## targets_gaps

G2 (language/script-controlled probes of recurrent state), G20 (0.1–1B evaluation instruments); benchmarks-eval
G2, seq-operators G1.

## Repairs made (wave-1 objection -> fix or accepted limitation)

Identification refuter:
1. Causal path misidentified (recall carried by softmax heads; loss on D acts via representation alignment;
   middle-layer control mismatched in layers/pooling/scale) -> phase 0 D-zero ablation measures the state's
   share of recall on the frozen hybrid (kill if <= 10%); phase-1 hybrids use SWA-512 so beyond-window recall
   is state-carried by construction; decisive control is now same-layer projection alignment A2 (same E heads,
   loss, lambda, tau, negatives, pooling shape; no recurrence); the middle-layer control is demoted to optional.
2. No matched dense control (Qwen3.5-4B vs Qwen3-4B confounded; Kimi has no sibling) -> phase 0 uses Ai2's
   throughput-matched Olmo-Hybrid-7B vs Olmo-3-1025-7B (same 6T data mix, tokenizer family, 8 full-attention
   layers at the same positions; revisions given); phase 1 adds a from-scratch full-attention dense arm A4
   iso-params/tokens/tokenizer/seeds; "hybrid-specific gap" is defined as the difference-of-differences; Qwen/Kimi
   cells are instrument-only with no causal claim. Accepted limitation: Olmo cards list English -> Latin-script
   cells only, with a language-competence gate that aborts rather than reinterprets.
3. Surface shortcut (shared entities satisfy the loss and the swap test) -> surface-disjoint vs surface-shared
   key subsets (NFKC/casefold filter); entity/number-sharing hard negatives in InfoNCE; P2 requires closure on
   surface-disjoint keys within 10 points of surface-shared; kill if closure is surface-shared only.
4. P3 is a tokenizer-fertility prediction -> dropped as a headline prediction and kill condition; script decay
   is exploratory only, reported token-count-matched (filler-padded Latin spans) with a romanized-input
   control.
5. Bitext-only null imported from the wrong regime -> A5 (no bitext, iso-token) and A0 (bitext, lambda = 0) run
   live in the same 57M/200M regime; nothing is pre-registered as null; kill if A1's gain is explained by A0 - A5.
6. Generation EM conflates retrieval with value translation -> values are 4-digit ASCII codes; EM on digits
   only.
Feasibility refuter:
7. Frozen screen not decisive (no matched sibling) -> Olmo pair as above; state access verified in transformers'
   `modeling_olmo_hybrid.py` (`recurrent_states`, `chunk_gated_delta_rule`); three phase-0 kills are identifiable.
8. Phase-2 budget infeasible (19–35B tokens in 12 GPU-h) -> re-budgeted with cited throughput (llm.c 489K
   tok/s/GPU at 124M; GDN 1.3B 30–45K tok/s at 4K, Fig. 3 of 2412.06464); planning 150K tok/s/GPU with a
   smoke-run gate; 57M models, 200M tokens/run, 6 arms x 3 seeds + 8-run LR sweep at 60M tokens; 9.3 GPU-h +25%
   = 11.6 GPU-h, gated behind a 3.2 GPU-h phase 0; total 14.8 <= 16. The 60–135M "rungs" claim is withdrawn; one
   rung (57M) only.
9. Kimi-Linear phase (98 GB, remote code, Python MoE loop) not credible at <= 2 GPU-h -> removed from the
   pilot; optional instrument-only extension with its own budget.
10. Data-endpoint gaps (Bengali unscored, sub-sentence alignment vs "no customer content") -> Bengali removed
    from the pilot (extension only); keys are whole sentences so sentence-level public bitext suffices; GT data
    optional and never customer content.
Novelty refuter caveats:
11. "Recombination of known ingredients; novelty rests on the object and the instrument" -> what_is_new
    downgraded accordingly; 2606.20936 (Olmo pair as a matched monolingual instrument) added as the closest
    instrument prior; collision_risk raised to medium for the instrument half.

## Coverage limits

OpenReview forum pages CAPTCHA-blocked (10 untitled hits unverified); Semantic Scholar unavailable; arXiv
abstracts and HTML only (no PDFs); Olmo-Hybrid/Olmo-3 pretraining language coverage taken from model cards and
the Ai2 blog, not verified against data manifests; FineWeb (English) license taken from memory of the dataset
card (FineWeb-2 verified ODC-By via the HF API); throughput planning number is an assumption to be replaced by
the smoke-run measurement.
