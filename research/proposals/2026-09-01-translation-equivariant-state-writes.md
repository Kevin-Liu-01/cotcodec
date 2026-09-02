# Research Direction: Translation-Equivariant State Writes

**Status:** draft; wave-3 identification repair applied; not pilot-ready (Compute doctor FAIL, no signed reviews)
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted before this spec; arXiv API, Semantic Scholar and Jina blocked from the Mac (arXiv abstracts reached only through the H100-host relay and arxiv.org/abs pages); no OpenReview titles resolved (forum pages CAPTCHA-blocked), no ACL Anthology, Google Scholar or patent search beyond the 2026-09-01 verification pass; nothing executed on fal-h100-01 or Tinker; no parallel corpus exists in the repository; wave 3 made no new network calls, so every source status below is inherited from the wave-1/wave-2 refuters and the wave-2 owner note; the Olmo model cards, 2605.12770 and 2608.27115 were read by the wave-2 refuters and not re-opened here
**Budgets:** queries=60; wall_minutes=600; tokens=900000; dollars=40; waves=3; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/translation-equivariant-state-writes/bundle.json

## Claim and Research Question

A fixed-size recurrent state that stores meaning should write the same thing for two translations of the same span. The object is the per-head **pure write** of a Gated DeltaNet (GDN) layer over a span `a` after a shared prefix `c`, `W(a|c) = S(c⊕a) − S_{v=0}(c,a)`, where `S_{v=0}(c,a)` is the state after running the span from `S(c)` with the value inputs zeroed (decay and erase kept, writes removed). Wave 2 supervised the raw segment delta `D = S(c⊕a) − S(c)`; both wave-2 judges showed that `D` carries a content-independent prefix term `(∏α − 1)S(c)` shared by every translation pair, so the old loss was satisfiable through prefix identity. Wave 3 replaces the object, the negatives, the control, and the phase-0 gates so that this shortcut is impossible by construction.

Research question, two phases:

- **Phase 0 (frozen, within-model kill screen).** On `allenai/Olmo-Hybrid-7B` (unregistered; revision `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf`), does the GDN state carry cross-lingual recall at all (D-zero vs a matched distractor-span perturbation), is the cross-lingual gap a storage-format effect rather than readout interference (N-scaling contrast at N in {8, 32, 128}), and does a training-free rank-capped linear transport of `W` already close the gap? `allenai/Olmo-3-1025-7B` (revision `a81bae42db3975be1671e27b9c9a56da1a9f980f`) is a **throughput-matched, not architecture-matched**, descriptive reference and supplies a cross-lingual EM floor gate; it is no longer a kill gate.
- **Phase 1 (from scratch, 57M SWA-512 + GDN hybrids).** Does supervising `W` in half the GDN heads on public bitext, with same-prefix negatives, close ≥ 50% of the cross-lingual recall gap on surface-disjoint, beyond-window keys, at equal monolingual recall and LM loss, and beat the same loss on the S(c)-free projection pooling `P(a) = Σ_t β_t v_t k_tᵀ` (A2) by ≥ 5 EM points?

**Claim scope (contract sense):** architecture-causal — the contract has matched from-scratch arms and controls. **Claim scope (what the pilot can actually establish):** the phase-1 causal contrast is *which object inside a fixed hybrid is supervised* (recurrence-weighted write vs its decay-free pooling), not GDN-vs-softmax. The architecture-level contrast is registered as a conditional arm A4′ (dense + the same projection-alignment loss) and is **not claimed unless A4′ runs** (see Cheapest Decisive Pilot). Both judges flagged the label; this is the honest resolution compatible with the contract validator.

## Strategic Fit and Why Now

Three labs now ship 3-linear : 1-global hybrids (Kimi K3, Qwen3.8-Next, GLM-5.3-Flash) and none reports language- or script-controlled behaviour of the recurrent state (sweep gap seq-operators G1; benchmarks-eval G2: no translation-paired recall probes exist). The first matched-scale open hybrid/dense sibling pair (Olmo Hybrid vs Olmo 3 7B, Apache-2.0, native `transformers` support with exposed recurrent states) appeared 2026-04 and has been used once as a matched instrument, monolingually (2606.20936). fla `chunk_gated_delta_rule` accepts `initial_state`, returns the final state, and its backward accepts `dht`, so a loss on a state or on a state difference is differentiable without a custom kernel. Kevin's assets (8xH100 with a Docker/Slurm/checkpoint harness; optional General Translation span-aligned corpora) make the 18-run from-scratch grid a two-day job; the pilot itself needs only public data. The fit with Kevin's "PorTAL-shaped" preference is the object: a translation-equivariance constraint on the *write* of a recurrent operator, not another harness layer.

## Primary-Source Evidence

Every number below appears in the claim registry with its locator and status. Statuses: VERIFIED = passage located by a wave-2 refuter/owner with URL; FIRST_PARTY = lab blog/card/README/preprint self-report; UNVERIFIABLE_ACCESS = not opened under this coverage; DERIVED = this proposal's own arithmetic, unexecuted.

- Substrate: Olmo Hybrid: From Theory to Practice and Back — https://arxiv.org/abs/2604.03444 (2026-04-03) and the Ai2 blog https://allenai.org/blog/olmohybrid — 24 GDN + 8 full-attention layers at positions 3, 7, ..., 31; training throughput matched to Olmo 3 7B; blog reports RULER-64K 85.0 vs 70.9 and Olmo 3's MMLU with 49% fewer tokens (first-party).
- Confounds between the two Olmo checkpoints, read from the model cards by the wave-2 identification and feasibility refuters (https://huggingface.co/allenai/Olmo-Hybrid-7B, https://huggingface.co/allenai/Olmo-3-1025-7B and their `config.json`): data mix `allenai/dolma3_mix-6T` (the Olmo 3 32B mix) vs `allenai/dolma3_mix-6T-1025`; stage-1 tokens 5.50T vs 5.93T; cosine vs piecewise LR schedule; hidden 3840/30 heads vs 4096/32; GDN key/value head dims 96/192; stage-2 checkpoint merging vs none; `rope_theta = null` (NoPE) in the hybrid's attention layers vs RoPE theta 5e5 with YaRN in Olmo 3. These are listed as confounds and are why the pair is descriptive only.
- State access: `transformers` `modeling_olmo_hybrid.py` reads `cache_params.layers[i].recurrent_states` and calls `chunk_gated_delta_rule(initial_state=..., output_final_state=True)` on chunked prefill — https://github.com/huggingface/transformers/blob/main/src/transformers/models/olmo_hybrid/modeling_olmo_hybrid.py ; native support since transformers 5.8.1 (https://pypi.org/project/transformers/5.8.1/).
- Kernel: fla v0.5.2 — https://pypi.org/project/flash-linear-attention/0.5.2/ and https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/gated_delta_rule/chunk.py (backward accepts `dht`, returns `dh0`).
- Instrument baselines: MLNeedle — https://arxiv.org/abs/2408.10151 (2024-08-19; NAACL 2025); OneRuler — https://arxiv.org/abs/2503.01996 (2025-03-03; instruction/context language mismatch swings dense models up to 20%).
- Recall carriers in hybrids: Gather-and-Aggregate — https://arxiv.org/abs/2504.18574 ; Attention Amnesia — https://arxiv.org/abs/2606.11052 ; recurrent-recall interference: Zoology — https://arxiv.org/abs/2312.04927 ; Based — https://arxiv.org/abs/2402.18668.
- Closest instrument prior: Comparing Transformers and Hybrid Models at the Token Level — https://arxiv.org/abs/2606.20936 (2026-06-18; same Olmo pair, monolingual token-level loss).
- New in wave 3 (located by the wave-2 novelty refuter): WriteSAE — https://arxiv.org/abs/2605.12770 (post-hoc write interventions on GDN/Mamba-2/RWKV-7 recurrent caches; makes D-zero/delta replacement a known intervention type); Procrustes rotation on FLORES-200/Tatoeba/OPUS pairs with causal patching of rotated residuals — https://arxiv.org/abs/2608.27115 (same logic as the training-free transport gate, on transformer residual streams). GI-SAE functional-swap criterion — https://arxiv.org/abs/2608.23809.
- Parallel-data null in the wrong regime: Leino & Tiedemann — https://arxiv.org/abs/2603.29026 (1.4B/200B); Middle-Layer Representation Alignment — https://arxiv.org/abs/2502.14830.
- Data: FLORES+ — https://huggingface.co/datasets/openlanguagedata/flores_plus (CC BY-SA 4.0, gated terms; dev 997 / devtest 1,012 sentences); FineWeb-2 — https://huggingface.co/datasets/HuggingFaceFW/fineweb-2 (ODC-By 1.0); FineWeb — https://huggingface.co/datasets/HuggingFaceFW/fineweb ; ParaCrawl v9 En–De 278,310,907 pairs and bonus En–Zh 14,170,585 pairs (CC0) — https://paracrawl.eu/ ; SCB-MT-EN-TH-2020 — https://huggingface.co/datasets/airesearch/scb_mt_enth_2020 (CC BY-SA 4.0, ~1M pairs).
- Throughput anchors: llm.c GPT-2 124M ~4M tok/s on 8xH100 (commenter report, ~500K tok/s/GPU) — https://github.com/karpathy/llm.c/discussions/481 ; Gated DeltaNet 1.3B ~47K tok/s at 4K on one H100 (Fig. 3) — https://arxiv.org/abs/2412.06464.
- Statistics: Adding Error Bars to Evals — https://arxiv.org/abs/2411.00640 (clustered SEs, paired differences, `n = (z_{α/2}+z_β)²(ω²+σ²_A/K_A+σ²_B/K_B)/δ²`; 3-point difference at 80% power ≈ 969 questions); Pre-training under infinite compute — https://arxiv.org/abs/2509.14786 (loss asymptote moves ≤ 0.02 across 3 seeds at 200M tokens, ~300M scale; first-party).
- Monitor fragility across 13 languages — https://arxiv.org/abs/2605.27901 (future monitorability test set).

### Claim registry

Protocol followed: `ext/ars/academic-pipeline/references/claim_verification_protocol.md` (E1 registry, E2 tracing; status per row). "Verified by" names the pass that located the passage; wave 3 made no network calls.

| claim_id | claim text | source URL + locator | status | verified by |
|---|---|---|---|---|
| C01 | Olmo-Hybrid-7B: 32 layers = 24 linear_attention + 8 full_attention at layers 3,7,...,31; GDN key dim 96, value dim 192; 30 heads; hidden 3840; 7.43B params; saved with transformers 5.8.1 | https://huggingface.co/allenai/Olmo-Hybrid-7B/resolve/4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf/config.json | VERIFIED | wave-2 feasibility refuter |
| C02 | Olmo-3-1025-7B: 24 sliding_attention (window 4096) + 8 full_attention at the same positions; hidden 4096; 32 heads; 7.30B; RoPE theta 5e5 with YaRN | https://huggingface.co/allenai/Olmo-3-1025-7B/resolve/a81bae42db3975be1671e27b9c9a56da1a9f980f/config.json | VERIFIED | wave-2 identification + feasibility refuters |
| C03 | Hybrid card: Olmo 3 32B data mix (`dolma3_mix-6T`), cosine LR schedule, 5.50T stage-1 tokens, stage-2 merged; Olmo 3 7B: `dolma3_mix-6T-1025`, piecewise schedule, 5.93T, no merging | https://huggingface.co/allenai/Olmo-Hybrid-7B (model card, training section); https://huggingface.co/datasets/allenai/dolma3_mix-6T ; https://huggingface.co/datasets/allenai/dolma3_mix-6T-1025 | FIRST_PARTY | wave-2 identification refuter |
| C04 | Released hybrid checkpoint uses no RoPE (`rope_theta = null`; code comment "Released ckpt don't use any ROPE") | https://github.com/huggingface/transformers/blob/main/src/transformers/models/olmo_hybrid/modeling_olmo_hybrid.py | VERIFIED | wave-2 identification refuter |
| C05 | Ai2 blog: training throughput matched; RULER-64K 85.0 vs 70.9; reaches Olmo 3 MMLU with 49% fewer tokens | https://allenai.org/blog/olmohybrid (results section) | FIRST_PARTY | wave-2 identification refuter (WebFetch summary) |
| C06 | `olmo_hybrid` GDN forward reads `cache_params.layers[i].recurrent_states[0]` and calls `chunk_gated_delta_rule(initial_state=..., output_final_state=True)` on chunked prefill | https://github.com/huggingface/transformers/blob/main/src/transformers/models/olmo_hybrid/modeling_olmo_hybrid.py | VERIFIED | wave-2 feasibility refuter |
| C07 | fla `chunk_gated_delta_rule` accepts `initial_state`, returns final state; backward accepts `dht` and returns `dh0` | https://github.com/fla-org/flash-linear-attention/blob/main/fla/ops/gated_delta_rule/chunk.py | VERIFIED | wave-2 feasibility refuter |
| C08 | fla v0.5.2 released 2026-07-27; transformers 5.8.1 released 2026-05-13 | https://pypi.org/project/flash-linear-attention/0.5.2/ ; https://pypi.org/project/transformers/5.8.1/ | VERIFIED | wave-2 feasibility refuter |
| C09 | FLORES+ dev 997 / devtest 1,012 sentences; CC BY-SA 4.0; gated terms; configs eng_Latn, deu_Latn, spa_Latn, cmn_Hans, tha_Thai, ben_Beng | https://huggingface.co/datasets/openlanguagedata/flores_plus (dataset card) | VERIFIED | wave-2 feasibility refuter |
| C10 | ParaCrawl v9 En–De 278,310,907 pairs; bonus En–Zh 14,170,585 pairs; CC0 | https://paracrawl.eu/ (release tables) | FIRST_PARTY | wave-2 feasibility refuter |
| C11 | SCB-MT-EN-TH-2020 ~1M En–Th pairs, CC BY-SA 4.0 | https://huggingface.co/datasets/airesearch/scb_mt_enth_2020 | FIRST_PARTY | wave-2 owner |
| C12 | FineWeb-2 ODC-By 1.0 with deu_Latn, cmn_Hani, tha_Thai configs; FineWeb ODC-By 1.0 | https://huggingface.co/datasets/HuggingFaceFW/fineweb-2 ; https://huggingface.co/datasets/HuggingFaceFW/fineweb | FIRST_PARTY | wave-2 owner (FineWeb-2 via HF API; FineWeb from card memory) |
| C13 | OneRuler: instruction/context language mismatch swings dense models up to 20% | https://arxiv.org/abs/2503.01996 (abstract) | FIRST_PARTY | wave-1 refuter |
| C14 | MLNeedle: cross-lingual needle retrieval on dense 2024 transformers; NAACL 2025 | https://arxiv.org/abs/2408.10151 | FIRST_PARTY | wave-1 refuter |
| C15 | 2606.20936: on the Olmo pair the hybrid's loss advantage nearly vanishes on repeated n-grams; monolingual; no state intervention | https://arxiv.org/abs/2606.20936 (abstract) | FIRST_PARTY | wave-2 novelty refuter |
| C16 | WriteSAE performs post-hoc write interventions on GDN/Mamba-2/RWKV-7 recurrent caches | https://arxiv.org/abs/2605.12770 (abstract) | FIRST_PARTY | wave-2 novelty refuter |
| C17 | 2608.27115 fits a Procrustes rotation on FLORES-200/Tatoeba/OPUS pairs and causally patches rotated residuals across monolingual transformers on factual cloze | https://arxiv.org/abs/2608.27115 ; https://arxiv.org/html/2608.27115 | FIRST_PARTY | wave-2 novelty refuter (HTML) |
| C18 | Gather-and-Aggregate / Attention Amnesia: hybrid recall concentrates in a few softmax heads | https://arxiv.org/abs/2504.18574 ; https://arxiv.org/abs/2606.11052 | FIRST_PARTY | wave-1 refuter |
| C19 | Zoology / Based: recurrent-recall interference grows with the number of stored associations for fixed-size states | https://arxiv.org/abs/2312.04927 ; https://arxiv.org/abs/2402.18668 | FIRST_PARTY | wave-2 identification refuter |
| C20 | Leino & Tiedemann: bitext in the mixture barely moves residual alignment at 1.4B / 200B tokens | https://arxiv.org/abs/2603.29026 (abstract) | FIRST_PARTY | wave-1 refuter |
| C21 | llm.c: ~4M tok/s GPT-2 124M on 8xH100 (~500K tok/s/GPU) reported by a commenter; main post is 8xA100 | https://github.com/karpathy/llm.c/discussions/481 | FIRST_PARTY | wave-2 feasibility refuter |
| C22 | Gated DeltaNet 1.3B ~47K tok/s at 4K context on one H100 (Fig. 3) | https://arxiv.org/abs/2412.06464 (Fig. 3) | FIRST_PARTY | wave-2 feasibility refuter |
| C23 | Error-bars power formula and "3-point difference at 80% power ≈ 969 questions" | https://arxiv.org/abs/2411.00640 (Sec. on power) | FIRST_PARTY | sweep benchmarks-eval cell [F8] |
| C24 | Loss asymptote varies ≤ 0.02 across 3 seeds at 200M tokens (~300M params) | https://arxiv.org/abs/2509.14786 | FIRST_PARTY | sweep benchmarks-eval cell [F7] |
| C25 | Monitors trained in one language are fragile across 13 languages | https://arxiv.org/abs/2605.27901 (abstract) | UNVERIFIABLE_ACCESS (abstract-level only) | sweep latent-reasoning cell |
| C26 | Olmo Hybrid paper full text; Ai2 blog "matched" statement in full context; OpenReview titles for the cross-lingual SSM queries | https://arxiv.org/abs/2604.03444 ; https://allenai.org/blog/olmohybrid ; https://openreview.net/forum?id=8cDoHzqDXP | UNVERIFIABLE_ACCESS | none (abstract/summary only; forum CAPTCHA) |
| C27 | Pilot arithmetic: 57M models, 200M tokens/run, 150K tok/s/GPU planning, 0.370 GPU-h per plain run, alignment factor 1.5 → 0.556 GPU-h, phase 0 3.8 GPU-h, phase 1 12.0 GPU-h incl. 25% reserve, total 15.8 ≤ 16 | this document, Cheapest Decisive Pilot | DERIVED | wave-3 owner (unexecuted; smoke run replaces) |
| C28 | Power: with seed-paired difference SD 3 EM points, 3 seeds give power 0.37 for δ = 5 and 0.66 for δ = 8; 5 seeds give 0.79 / 0.99; prompt level: 785 paired prompts detect δ = 5 points at SD 0.5 (1,538 at SD 0.7) | this document, Evaluation section (scipy noncentral-t, computed 2026-09-01) | DERIVED | wave-3 owner |

## Closest Prior Work

| Prior | Date | What it does | Why it does not occupy this claim |
|---|---|---|---|
| MLNeedle (2408.10151) | 2024-08 | cross-lingual needle retrieval on dense transformers | no recurrent operator, no state intervention, no training signal; baseline |
| OneRuler (2503.01996) | 2025-03 | multilingual RULER on dense models | no hybrids, no state; motivates language-mismatch cells |
| WriteSAE (2605.12770) | 2026-05 | post-hoc write interventions on GDN/Mamba-2/RWKV-7 caches | interventions are monolingual and interpretability-motivated; here D-zero is an *application* of a known intervention type to a cross-lingual question, not a new technique |
| Procrustes residual patching (2608.27115) | 2026-08 | rotation fitted on bitext, patched into transformer residuals on cloze | residual stream of transformers, not recurrent-state writes; the training-free transport gate here is the recurrent analogue and is registered as a kill, not a contribution |
| GI-SAE (2608.23809) | 2026-08 | functional-swap criterion on SAE features | transformer features; supplies the criterion only |
| Gather-and-Aggregate (2504.18574), Attention Amnesia (2606.11052) | 2025-04 / 2026-06 | hybrid recall lives in few softmax heads | motivates D-zero and the SWA-512 phase-1 design |
| Token-level Olmo pair comparison (2606.20936) | 2026-06 | same Olmo pair as a matched instrument, monolingual | no cross-lingual axis, no state intervention; closest instrument prior |
| Leino & Tiedemann (2603.29026); Middle-Layer Alignment (2502.14830) | 2026-03 / 2025-02 | bitext exposure and residual alignment in transformers | different regime and object; A5/A0 run the exposure contrast live |
| Olmo Hybrid (2604.03444) | 2026-04 | the substrate | no cross-lingual or state-level recall analysis |

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Pure-write object `W(a|c) = S(c⊕a) − S_{v=0}(c,a)` as the target of a translation-equivariance loss | WriteSAE 2605.12770 (write interventions, no loss); Middle-Layer Alignment 2502.14830 (residual object) | no | the object is the recurrence-weighted write of a GDN head with the prefix carry removed by algebra; supervised, not just intervened on | 0.55 |
| Same-prefix InfoNCE with translation positives and content-only negatives | LaBSE/SONAR-style bitext contrastive losses (standard) | loss form yes | applied to state writes behind a bitwise-shared prefix so prefix identity cannot carry the objective | 0.6 |
| Translation-paired MQAR (TP-MQAR-v2) with digit-only EM and surface-disjoint keys | MLNeedle 2408.10151; OneRuler 2503.01996 | no | recall (not needle) framing, key-language x query-language matrix, N-scaling, surface-shortcut split | 0.65 |
| Within-model state interventions on a frozen hybrid (D-zero with matched perturbation, rank-capped transport, swap) | WriteSAE 2605.12770; 2608.27115; GI-SAE 2608.23809 | partly | each intervention type has an individual prior; the cross-lingual recall question and the matched-perturbation control are new; contribution rests on the phase-0 result, not the technique | 0.5 |
| Throughput-matched Olmo pair as a *descriptive* reference with confounds listed | 2606.20936 | instrument yes | cross-lingual axis added; no causal use of the pair | 0.7 |

Novelty wording: No direct prior art found through 2026-09-01 under arXiv API x22 (wave-1 refuter ~21 queries; wave-2 owner x3; wave-2 novelty refuter x15 returned HTTP 429 and were substituted by 8 arxiv.org/search abstract-field queries), Hugging Face papers x6, OpenReview x3 (titles unresolved), Crossref x2, WebFetch of ~18 abstracts, and Kevin's X bookmarks. The loss form is standard; the object and the instrument are the delta. This is not a global-priority claim; collision risk for the instrument half is medium because the Olmo pair is public and cheap to probe.

## Mechanism and Falsifiable Predictions

**GDN recurrence (fla convention, per layer l, head h).** `S_t = S_{t−1} · α_t (I − β_t k_t k_tᵀ) + β_t v_t k_tᵀ`. The recurrence is affine in the state, so after a span `a = (a_1..a_T)` from `S_0 = S(c)`:

```text
S(c⊕a) = S(c) · ∏_{t=1..T} α_t (I − β_t k_t k_tᵀ)          (prefix carry: decay + erase acting on S(c))
       + Σ_{t=1..T} β_t v_t k_tᵀ · ∏_{s>t} α_s (I − β_s k_s k_sᵀ)   (pure write: W(a|c))
```

**Wave-3 object.** `W(a|c) := S(c⊕a) − S_{v=0}(c,a)`, where `S_{v=0}(c,a)` is computed by a second `chunk_gated_delta_rule` call over the span with `initial_state = S(c)` and `v ≡ 0` (keeps α, β, k; removes writes). By the identity above, `W` equals the state obtained by running the span from `S_0 = 0` with the same projections, so Judge B's proposed "recurrence with zero initial state" arm is algebraically the same object and is absorbed into A1 rather than run separately; the fp64 CPU doctor checks `S_{S0=0}(a) == S(c⊕a) − S_{v=0}(c,a)` to 1e-10. The wave-2 shortcut term `(∏α − 1)S(c)` is absent from `W` by construction; `W` still depends on `c` through the projections (k, v, α, β are functions of the residual stream), which is what the same-prefix negatives control.

**Treatment (A1).** `L = L_LM + λ (L_eq + L_nce)` on head subset E (half the heads of every GDN layer). `L_eq = mean_{(l,h)∈E} (1 − cos(vec W^A, vec W^B))` for a bitext pair `(a^A, a^B)` behind the same prefix `c`. `L_nce = −log exp(s(W^A, W^B)/τ) / Σ_{B'} exp(s(W^A, W^{B'})/τ)`, `s` = cosine over concatenated E-head writes, `τ = 0.07`, `λ ∈ {0.1, 0.3}` (selected on FLORES+ dev, never on test). **Negatives (all behind the identical prefix `c`, so the prefix is common to positive and negatives and only content discriminates):** ≥ 2 same-prefix random language-B sentences from the same bitext document neighbourhood; ≥ 2 same-prefix hard negatives that share a named-entity string or a number with `a^A` but are not its translation; plus the batch's other-prefix spans as extras. Heads outside E carry no alignment term.

**Decisive control (A2, same-layer projection alignment, no recurrence).** Identical `L_eq + L_nce`, λ, τ, negatives, layers and heads on `P(a) = Σ_{t∈a} β_t v_t k_tᵀ`, the decay-free, erase-free pooling of the same E heads' projections over the same span (same d_k x d_v shape, already S(c)-free). A1 − A2 isolates "align the recurrence-weighted write" from "align the projections that feed it".

**Placebo (A3, language-marginal).** Same loss form and λ with `a^B` replaced by a content-independent random language-B sentence behind the same prefix. Reading (per Judge A): A3 tests language-ID removal on the write, which is itself a candidate mechanism; A3 ≈ A1 therefore means "the gain is language-marginal alignment, not translation equivariance", not "regularization".

**Instrument: TP-MQAR-v2.** N facts of the form "key sentence in language A, then sep_A, then a 4-digit ASCII code" among language-A distractors; query of the form "key translated into language B, then sep_B"; digit-only exact match. Key types built from FLORES+ devtest: surface-disjoint (NFKC + casefold, no shared alphanumeric token ≥ 3 chars, no shared digit string, and — new in wave 3 — no shared BPE/SentencePiece subword of ≥ 4 characters under the evaluated model's tokenizer, since En↔De/Es cognates share subwords) and surface-shared (complement). N ∈ {8, 32, 128}; contexts 4K (8K for N = 128).

**Pre-registered sanity check (prefix floor).** On the frozen hybrid, report `cos(W^A, W^B)` for translation pairs against the floor `cos(W^A, W^{B'})` for same-prefix non-translation spans, and the same two quantities for the old object `D`. Reject the wave-3 object if the translation-pair cosine of `W` is not above its same-prefix floor by ≥ 0.05 on average in ≥ 2/3 of E heads (then the write does not separate content even before training and the loss has nothing to align); publish the `D` numbers as documentation of the wave-2 defect.

**Predictions (embarrassing if wrong).**

- P0a (descriptive, no kill): Olmo-Hybrid-7B's cross-lingual gap `G(N) = EM[A=B] − EM[A≠B]` on surface-disjoint keys at N = 8 is ≥ 8 EM points larger than Olmo-3-1025-7B's, 95% prompt-clustered bootstrap CI excluding 0 — reported with the confound list, not used as a gate.
- P0b (within-model, kill): D-zero on the fact span removes ≥ 30% of the hybrid's cross-lingual recall (relative) **and** exceeds the matched distractor-span perturbation by ≥ 10 points; **kill criterion** if the fact-minus-control difference is ≤ 10 points (state is a bystander or the drop is state/KV inconsistency).
- P0c (storage vs readout, kill): the gap exists where interference is minimal, `G(8) ≥ 8` points with monolingual EM ≥ 80%, and does not blow up with load, `G(128)/G(8)` below 2 while monolingual EM stays ≥ 60%; **kill criterion** if `G(8) ≤ 3` (states already store meaning at low load) or `G(128)/G(8) ≥ 2` (readout interference dominates; the write-format premise is unsupported and the training arm is not run).
- P0d (transport, kill, now fireable): a rank-capped (r ≤ 64) per-head ridge/Procrustes map on `W`, fitted in dual form on 997 FLORES+ dev pairs x 8 prefixes, closes ≤ 40% of the hybrid's gap on devtest keys; **kill criterion** if closure ≥ 80% (meaning up to a linear language transform; training redundant). Report identity-map and random-rotation controls alongside.
- P1 (phase 1, 3 seeds, beyond-window surface-disjoint keys): A1 closes ≥ 50% of A0's gap with monolingual EM within 2 points and held-out LM loss within 0.5%; A2 closes ≤ 25%; A3 ≤ 10%; A1 − A2 ≥ 5 EM points, same-signed in all 3 seed pairs. **Falsifier:** A1 − A2 below 5 points paired over seeds, or A3 closes ≥ 50% of A1's closure, or LM loss > 1% worse, or `mean ||W||` in E heads shrinks > 30%, or A5 (no bitext) ≈ A0 within 2 points while A1 beats only A5.
- P2 (held-out functional criteria, not optimized by the loss): (i) closure on surface-disjoint keys within 10 points of closure on surface-shared keys; (ii) `G(N)` for A1 at N ∈ {8, 32, 128} shrinks at every N (not only at N = 8); (iii) swap `S ← S_{v=0}(c,a^A) + W^B` on devtest keys behind never-trained prefixes preserves ≥ 80% recall in A1 vs ≤ 40% in A0. The swap is a secondary criterion because it is monotone in the trained cosine; the primary endpoint is recall EM, which the loss never sees.

**Strongest counter-argument (devil's advocate).** The cross-lingual gap in GDN states may be entirely a readout phenomenon — the state stores the same content as the KV cache, and a translated query simply has a smaller `qᵀS` margin over N−1 distractors, rescued in the dense model by softmax's winner-take-all — in which case aligning writes cannot help and only a readout-side change (or QED-style query-derived erase) can. P0c is the pre-registered test of exactly this account, and its "readout dominates" branch kills the training arm before any from-scratch GPU is spent. **What's missing:** a direct margin measurement is descriptive only (we log the correct-value logit minus best-distractor logit at the answer position, by N and query language); we have no theory predicting the *size* of a storage-format gap, so the thresholds 8 and 3 points are conventions borrowed from the wave-2 design, not derived; and 57M SWA-512 hybrids may not reproduce the 7B regime even if both phases pass.

## Cheapest Decisive Pilot

**CPU doctor (0 GPU-h, gate for everything).** Build TP-MQAR-v2 from FLORES+ devtest (En, De, Es; Zh/Th reserved for extensions); key-type split incl. the subword filter; 5 hand-checked separator phrases per language; leakage doctor (retrieval-impossible control at chance 1e-4, value-permutation control, first-token key perturbation); fp64 exactness of `W` on a 2-layer GDN (fla vs pure PyTorch; `S_{S0=0}(a) == S(c⊕a) − S_{v=0}(c,a)`; `S(c)` bitwise identical across a pair); prefix-floor computation plan; dedup (exact + MinHash 5-gram) of all FLORES+ sentences against the phase-1 streams.

**Phase 0 — frozen within-model kill screen (3.8 GPU-h incl. 25% reserve; 2 GPUs).** Models (both unregistered; to be added to `models/registry.yaml` with the 40-hex revisions above): `allenai/Olmo-Hybrid-7B` and `allenai/Olmo-3-1025-7B`, Apache-2.0. Cells: {En, De, Es} key x query (9 cells) x 2 key types x N ∈ {8, 32, 128} x 100 prompts; the dense model runs N ∈ {8, 32} only (its SWA-4096 layers do not cover the 8K prompts needed at N = 128, and the pair is descriptive). Hybrid interventions on surface-disjoint keys: D-zero on the fact span and D-zero on an equal-length distractor span at the same offset distribution (9 cells x 3 N x 100 each); rank-capped transport with identity and random-rotation controls (6 cross cells x 3 N x 100, controls at N = 32 only); swap (6 x 3 x 100). Gates: language-competence (monolingual EM ≥ 60% at N = 8 in both models) **and** dense cross-lingual EM floor (Olmo-3 cross-lingual EM ≥ 40% at N = 8 on surface-disjoint keys) per language pair, else the pair is dropped; if no pair passes, phase 0 reports instrument-only results and the candidate stops. Budget: ~3,600 dense prompts at ~0.4 s + ~15,000 hybrid-type prompts at ~0.57 s average (N = 128 at 8K ~0.9 s) = ~2.8 GPU-h; transport fitting (7,976 paired writes per head in dual form) + gates + smoke 0.3 GPU-h; x1.25 = 3.8 GPU-h.

**Phase 1 — from-scratch identifiability (≤ 12.0 GPU-h incl. 25% reserve; gated on P0b, P0c, P0d all passing).** 57M models: 12 layers, d = 512, SwiGLU 1536, 8 heads, tied 32K SentencePiece unigram tokenizer trained on the mixture. Hybrid: 9 GDN layers (k dim 64, v dim 128; per-head state 8,192 dims; E = 4 heads/layer) + 3 SWA-512 attention layers at 4, 8, 12, so a fact more than 512 tokens before the query is recalled only through the state. Dense (A4): 12 full-attention layers, params matched within 3% via FFN width. Arms x 3 seeds: A0 hybrid, bitext, λ = 0; A1 treatment; A2 projection control; A3 language-marginal placebo; A4 dense, λ = 0; A5 hybrid on an iso-token monolingual-only stream. **Conditional A4′** (dense + A2's projection-alignment loss on the K/V projections of the corresponding layers) runs only if the smoke run measures ≥ 200K tok/s/GPU, which is when it fits under the 16 GPU-h ceiling; otherwise it is deferred to a new contract and no GDN-vs-softmax claim is made. Data per run 200M tokens: 75% monolingual (En 60M FineWeb; De 30M, Zh 30M, Th 30M FineWeb-2), 20% prefix-sharing bitext (ParaCrawl En–De 16M, En–Zh 14M, SCB-MT En–Th 10M), 5% same-language synthetic recall curriculum with ParaCrawl keys and digit values; FLORES+ keys and the cross-lingual cells are never trained on. LR sweep: 4 values x A0 x 1 seed x 60M tokens (the winner is used for every arm; alignment arms inherit it — a conservative bias against the treatment). Throughput: planning 150K tok/s/GPU (~5% of dense bf16 peak; anchors C21, C22 are far above and far below this regime), measured by a 50M-token smoke run; tokens/run = min(200M, T_measured x 1,333 s) with a 120M floor below which phase 1 is deferred. Cost at 150K tok/s: plain arms 9 x 0.370 = 3.3 GPU-h; alignment arms (prefix duplication, `v = 0` counterfactual pass, 4 same-prefix negative spans; factor 1.5) 9 x 0.556 = 5.0; sweep 0.44; evaluation incl. N-scaling and swap 0.8; sum 9.6; x1.25 = 12.0. **Total 3.8 + 12.0 = 15.8 GPU-h ≤ 16.** If A0's seed SD of the gap exceeds 3 points, A0/A1/A2 receive 2 more seeds under a separate 3.7 GPU-h line (new contract).

**Optional (not part of the pilot).** Instrument-only cells on registered `qwen3.5-4b` (GDN hybrid) and `kimi-linear-48b-a3b-base` (KDA); General Translation span-aligned corpora for sub-sentence spans and Bn/Ja/Ar; never customer content.

## Controls, Baselines, and Ablations

- A2 same-layer projection alignment: same E heads, loss, λ, τ, same-prefix negatives, pooling shape; no recurrence (decisive).
- A3 language-marginal placebo: content-independent pairing behind the same prefix (tests language-ID removal).
- A0 hybrid baseline (bitext, λ = 0) and A5 no-bitext iso-token rung: the bitext-exposure contrast runs live in the pilot's regime instead of importing 2603.29026's null.
- A4 dense full-attention transformer (iso-parameter within 3%, iso-token, iso-corpus, same tokenizer and seeds; λ = 0) — descriptive; A4′ conditional (same loss on a dense model) is the only arm that would license an architecture-level statement.
- Frozen: D-zero with a matched equal-length distractor-span perturbation; rank-capped transport with identity and random-rotation controls; swap on never-trained prefixes; surface-disjoint vs surface-shared keys; retrieval-impossible and value-permutation leakage controls; digit-only EM; language-competence and dense cross-lingual EM floor gates; the Olmo pair as a throughput-matched descriptive reference with the C03/C04 confounds listed.
- Published baselines cited: MLNeedle and OneRuler for the instrument; WriteSAE for the intervention type; 2608.27115 for training-free bitext transport; QED (2608.13668), MARCH and SWA+sinks (2608.28444) become mandatory only if a recall-improvement claim beyond this pilot is made.
- Held-out LM loss and FLORES+ devtest bits-per-byte per language never see the alignment terms; 4x OOD length (1K–8K) on beyond-window facts.

## Evaluation, Statistics, and Leakage Checks

Protocols followed: `.claude/skills/experimental-design/SKILL.md`, `.claude/skills/statistical-power/SKILL.md`, and `ext/ars/academic-paper-reviewer/references/statistical_reporting_standards.md`.

**Primary endpoint.** Closure of the cross-lingual recall gap on surface-disjoint TP-MQAR-v2 keys at beyond-window positions, A1 minus A2, in EM points; unit of analysis = seed-paired arm difference, with prompts clustered by FLORES+ key sentence; aggregation = paired-by-seed mean difference with prompt-clustered bootstrap 95% CI; report effect sizes (EM-point differences with CIs and Cohen's d on seed-paired differences), seed SD, and the resolution ratio per comparison.

**Minimum worthwhile effect.** 5 EM points for A1 − A2 (below this the write object is not worth its 1.5x training cost over projection alignment); 50% gap closure for A1 vs A0.

**Noise estimate and power (C28).** The seed-level SD of a cross-lingual EM gap at 57M is unknown; the nearest published floor is a loss-asymptote spread ≤ 0.02 across 3 seeds at ~300M (C24), which does not convert to EM. Assumed seed-paired difference SD = 3 EM points (assumption, pre-registered check). Closed form (paired t, two-sided α = 0.05, scipy noncentral t): 3 seeds give power 0.37 at δ = 5 and 0.66 at δ = 8; 5 seeds give 0.79 and 0.99. Three seeds are therefore a **kill screen**, not a confirmation: a same-signed A1 − A2 ≥ 5 in 3/3 seeds with a prompt-level CI excluding 0 promotes to the +2-seed line; a single opposite-signed seed kills. Prompt level (C23 formula with ω = 0, K = 1): 785 paired prompts detect 5 points at 80% power for a paired-difference SD of 0.5 (1,538 at 0.7); each seed evaluates 1,800 surface-disjoint cross-cell prompts (6 cells x 3 N x 100), which meets the 0.5 case and nearly the 0.7 case.

**Randomization and blocking.** Seeds {42, 43, 44} are shared across arms: A0/A1/A2/A3/A5 share initialization and data order per seed (A4 has its own init per seed, same data order); arm-by-seed jobs are scheduled on the 8 GPUs in a Latin-square order so no arm is confounded with a GPU or a time slot; evaluation prompt sets and fact positions are fixed per seed by a recorded permutation; λ and LR are chosen on FLORES+ dev only.

**Multiplicity.** One primary endpoint; the four secondaries (P2 i–iii, A5 vs A0) are Holm-corrected; phase-0 kills are pre-registered thresholds, not tests.

**Assumption checks.** Paired differences inspected for sign consistency (3 seeds cannot support normality tests); prompt-level CIs use clustered bootstrap; EM near 0 or 100 in any cell is flagged as floor/ceiling compression and that cell is excluded from ratio-based statistics (P0c).

**Leakage.** FLORES+ dedup against training (exact + MinHash 5-gram); values are per-prompt random digit codes never present in training; retrieval-impossible and value-permutation controls at chance; keys never appear in the synthetic curriculum; transport maps fitted on dev, evaluated on devtest; test prompts sealed with hashes before any phase-1 run.

## Compute and Reproducibility

Discovery image (verified on fal-h100-01, 2026-09-01; used for the CPU doctor and phase-0 smoke only):

- immutable image: `127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
- Image ID `sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2`; labels `org.opencontainers.image.revision=581ded8df71564b0212d8af5dcd401257aa6a28f`, `source-tree-sha256=2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322`, `runtime-profile=architecture-source-overlay`; created 2026-08-16.
- Contents: CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0, accelerate, triton; **no** vllm, peft, fla or flash-attn. transformers 5.15.0 already carries the native `olmo_hybrid` module (≥ 5.8.1), but the pilot **must be rebuilt** from the new code with `flash-linear-attention≥0.5.2`, `sentencepiece`, `datasets`, and `datasketch` (MinHash) added, then **re-pinned by digest**; no digest is invented here.

Launch (dry run first, then the real submit, both through `sbatch` on the single-node Slurm):

```bash
uv run python scripts/submit_docker_research_job.py experiments/architectures/translation-equivariant-state-writes.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/architectures/translation-equivariant-state-writes.yaml
# the submitter wraps: sbatch infra/slurm/host-single-node/docker-research.sbatch COMPILED_JOB_MANIFEST
```

The submitter validates a compiled job manifest; none has been compiled for this contract yet, so the dry run has not been executed (Compute doctor FAIL).

`seeds: [42, 43, 44]`
`gpu_hours: 16` (ceiling; phase 0 3.8 + phase 1 12.0 = 15.8 planned)

Checkpoints: atomic, every 15 minutes, to `/home/kevin/cotcodec-runs/translation-equivariant-state-writes/ARM/SEED/`; SIGUSR1 checkpoint handling and a fresh-job continuation equivalence test on the smoke run before any grid job; each (arm, seed) is one 1-GPU job, phase 0 uses 2 GPUs. Artifacts: TP-MQAR-v2 prompt manifests and hashes, per-cell EM tables with clustered CIs, intervention logs (D-zero, matched control, transport maps with ranks, swaps), prefix-floor tables for `W` and `D`, throughput smoke ledger, per-run configs, LM-loss and bits-per-byte curves, seed-paired difference tables. Cost ceiling: 16 GPU-h; the +2-seed and A4′-deferred lines require new contracts. The host's Slurm 21.08.5 lacks cgroup-v2 device isolation, so this is the discovery lane, not the publication lane.

## Safety, Data Rights, and Monitorability

**Monitorability.** Chain-of-thought is untouched and there is no action channel; the intervention is a pretraining auxiliary loss on recurrent-state writes plus read-only state interventions on frozen models. A meaning-level state could help a monitor trained in one language transfer to others, or could remove surface cues monitors rely on; both directions are reported if the direction proceeds, against the 13-language fragility set (C25).

**Data rights.** ParaCrawl CC0; FLORES+ CC BY-SA 4.0 with gated acceptance of terms (the derived TP-MQAR-v2 is released share-alike); SCB-MT-EN-TH-2020 CC BY-SA 4.0; FineWeb/FineWeb-2 ODC-By 1.0 with attribution (FineWeb's license is from card memory and must be re-verified before release); Olmo checkpoints Apache-2.0. **General Translation parallel data: license and customer-consent status unknown; it is optional, not required by any prediction, and customer content is never used.** IP: the contribution is a loss on top of fla kernels with no kernel-level delta-rule change, so the NVIDIA "Gated delta networks" patent flag (US20260105282A1, pending) does not attach; state interventions are inference-time reads/writes of a cache, not a kernel.

**Red lines.** Stop if any released artifact contains FLORES+ or bitext text beyond CC BY-SA/CC0 terms; stop if the derived instrument leaks sealed test prompts; no customer data; no model is trained on any language's text whose source license forbids it.

### Integrity gate

Protocol followed: `ext/ars/academic-pipeline/references/ai_research_failure_modes.md` (7 modes).

| Mode | Status | How this proposal addresses it |
|---|---|---|
| 1 Implementation bug passing self-review | INSUFFICIENT EVIDENCE (no code yet) | fp64 CPU doctor for `W` identity, bitwise-identical `S(c)`, leakage controls at chance; every number will come from a logged run with exit code 0 |
| 2 Hallucinated citation | CLEAR under coverage | claim registry with URL + locator + status per row; UNVERIFIABLE_ACCESS rows marked |
| 3 Hallucinated experimental result | CLEAR | no result is reported; all numbers are predictions, thresholds, or DERIVED arithmetic labelled as such |
| 4 Shortcut reliance | ADDRESSED by design | prefix-identity shortcut removed by the `W` object and same-prefix negatives; copy shortcut by surface-disjoint keys with a subword filter and entity/number hard negatives; language-ID shortcut read out by A3; readout-interference alternative tested by P0c |
| 5 Bug reframed as insight | GUARDED | "surprising" branches (e.g. hybrid gap smaller than dense) are pre-registered as kills, not findings; any inversion triggers reproduction from scratch before reporting |
| 6 Methodology fabrication | CLEAR | no Methods-as-executed text exists; the contract YAML is the pre-registration and run configs will be hashed into the evidence bundle |
| 7 Frame-lock | FLAGGED, mitigated | the frame "state stores surface" is one of three pre-registered outcomes; P0c's readout branch and P0d's transport branch each end the training arm; the Olmo pair's demotion in wave 3 is an explicit back-out from a wave-2 commitment |

## Negative-Result Value

Phase 0 alone produces the first within-model, state-intervention measurement of cross-lingual recall in a 2026 GDN hybrid, with a descriptive matched-throughput dense reference: "state is a bystander" (P0b), "readout interference, not storage" (P0c), or "meaning up to a rank-64 linear transform" (P0d) each closes sweep gap G2 cheaply and is publishable, and the `W`-vs-`D` prefix-floor table documents a shortcut that any future recurrent-state alignment loss must avoid. Phase-1 negatives: A1 ≈ A2 says the recurrence-weighted write adds nothing over projection alignment; A3 ≈ A1 says the gain is language-ID removal; closure only on surface-shared keys documents a copy shortcut; A5 ≈ A0 with A1 > A5 only says the effect is bitext exposure. TP-MQAR-v2 and the intervention toolkit remain the G2/G20 instrument in every branch.

**What's missing** (devil's advocate, continued): a positive phase 1 at 57M with SWA-512 does not transfer to 7B full-attention-every-4th-layer hybrids where softmax heads can carry recall; the proposal claims only the 57M regime and states the transfer question as future work with its own contract.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | cell notes: design/wave2/translation-equivariant-state-writes.md, wave2-result.json refuter votes (novelty/identification/feasibility), sweep/seq-operators.md, sweep/benchmarks-eval.md, sweep/synthesis.md sections 2 and 5; no snapshots hashed yet | hash source snapshots into evidence/translation-equivariant-state-writes/bundle.json (does not exist yet) |
| Citation | PASS-candidate | claim registry C01–C28: every number has a URL and locator; FIRST_PARTY and UNVERIFIABLE_ACCESS marked; protocol ext/ars/academic-pipeline/references/claim_verification_protocol.md | independent line-by-line audit; re-open C03, C05, C17, C25, C26 |
| Novelty | PASS-candidate | wave-2 novelty refuter: not refuted (0.6); blind discrimination: different mechanism, prior does not dominate (0.93, vs MLNeedle); WriteSAE and 2608.27115 added; rerun of blind discrimination against 2608.27115 pending | signed provider-distinct novelty audit; rerun discrimination vs 2608.27115 |
| Design | PASS-candidate | contract experiments/architectures/translation-equivariant-state-writes.yaml passes scripts/validate_architecture_experiments.py; W object, same-prefix negatives, matched A2, within-model phase-0 kills, power justification C28 | implement the CPU doctor and audit its output |
| Compute | FAIL | no real model loop, no rebuilt digest-pinned image with fla, no container smoke, no Slurm dry run, no resume receipt; discovery image lacks fla | rebuild and re-pin the image; compile the job manifest; run the dry run and smoke; attest |
| Safety | PASS-candidate | monitorability, data rights (GT license unknown, optional), red lines and the 7-mode integrity gate are stated; no runtime evidence | runtime data-rights receipts and release audit |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-1 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned)

Reviewer B: FAIL | provider=anthropic | model=claude | run_id=wave2-judge-2 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json (internal preliminary, NOT provider-distinct, unsigned)

Both reviews are internal wave-2 judge scorecards from the same provider, unsigned and not from the protected trust store; the accepted score is therefore capped at 89 and the proposal is NOT pilot-ready regardless of content. The judges' criterion-bound form (ext/ars/academic-paper-reviewer/references/quality_rubrics.md; calibration NOT_CALIBRATED) is to be filled by the wave-3 judges, not by this owner.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 7 | 7 | fits G1/G2/G20; architecture-causal label questioned by both judges (wave 3: scope narrowed, A4′ conditional) |
| Primary-source evidence | 5 | 5 | Olmo cards read via refuter summaries; 2608.27115 and WriteSAE were missing from priors (wave 3: added; not re-opened) |
| Defensible novelty delta | 5 | 5 | recombination of known ingredients; delta rests on the W object and the instrument |
| Mechanism and falsifiability | 6 | 6 | wave-2 D object leaked the prefix (wave 3: W object, prefix-floor check) |
| Controls and causal identification | 3 | 3 | prefix-identity shortcut; unmatched Olmo pair used as a gate; unfireable transport gate (wave 3: same-prefix negatives, within-model kills, rank-capped dual transport) |
| Evaluation and statistics | 6 | 5 | swap endpoint equalled the training objective; no N-scaling (wave 3: held-out functional criteria, N in {8,32,128}, power C28) |
| Feasibility and information per GPU-hour | 6 | 7 | arithmetic holds with reserve; throughput planning number unverified until the smoke run |
| Reproducibility and artifact contract | 7 | 6 | no image with fla, no manifest, no receipts |
| Safety, data rights, and monitorability | 8 | 8 | public data, Apache-2.0 checkpoints, GT data optional |
| Independent adversarial review quality | 6 | 5 | same-provider internal judges, unsigned |
| **Total** | **59** | **57** | Lower total is authoritative: 57; caps 89 (unsigned reviews), 79 (no executable pilot), 74 (novelty coverage) do not bind below 57 |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | killed before judging: identification REFUTED (0.8) — pilot could not separate aligning the recurrent write from its strongest control; feasibility REFUTED (0.7) — no matched sibling, phase-2 budget infeasible (research/gauntlet/2026-09-01-frontier/wave1-ledger.md, row 7) | wave-2 repairs: Olmo matched pair, D-zero, same-layer projection control A2, surface-disjoint keys, digit-only EM, live A5/A0 bitext contrast, re-budget to 14.8 GPU-h | entered wave 2 |
| 2 | 57 | training objective leaked the shared prefix (`D` contains `(∏α − 1)S(c)`, identical for both translations; negatives sat behind other prefixes; A1 − A2 and the swap endpoint reproduced the shortcut); Olmo "matched pair" premise contradicted by the model cards; transport gate unfireable (18,432-dim ridge from ~1k pairs) | none in wave 2 (judged as submitted) | ranked 4th of 4 survivors; 4 candidates killed |
| 3 | unjudged | same as wave 2 (both judges' highest-impact fix, implemented as their union) | supervised object changed to the pure write `W(a|c) = S(c⊕a) − S_{v=0}(c,a)` (Judge B's zero-initial-state arm shown algebraically identical and absorbed); ≥ 2 same-prefix negatives plus same-prefix entity/number hard negatives; A2 kept S(c)-free and matched on negatives; pre-registered prefix-floor check for `W` vs `D`; P2 replaced by held-out functional criteria and an N ∈ {8, 32, 128} margin contrast; Olmo pair relabelled throughput-matched with C03/C04 confounds listed and P0a demoted to descriptive; phase-0 kills made within-model (D-zero with matched distractor perturbation; storage-vs-readout N-scaling; rank-capped dual-form transport with 8 prefixes per pair, identity and rotation controls); dense cross-lingual EM floor gate added; WriteSAE 2605.12770 and 2608.27115 added to priors; claim scope narrowed in prose with conditional A4′; budget re-cut (LR sweep on A0 only, 100 prompts/cell) to 15.8 GPU-h | Compute doctor FAIL, unsigned reviews; not pilot-ready; blind discrimination rerun vs 2608.27115 pending |

The evidence bundle `evidence/translation-equivariant-state-writes/bundle.json` does not exist yet; source snapshots, query logs, reviewer outputs, doctor outputs, container and Slurm attestations and the hash-chained audit JSONL must be created below that directory and hashed before any doctor can pass. Each review receipt must be Ed25519-signed by a provider-specific key from the external trust store configured as `COTCODEC_TRUSTED_ATTESTORS_PATH` in protected CI; this document cannot score itself upward.
