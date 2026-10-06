# cross-family-adapter-port — wave-2 repair (2026-09-01)

Repair owner note. Wave-1 verdicts: novelty NOT refuted (0.6; delta shrunk), identification REFUTED (0.8),
feasibility REFUTED (0.8). This rewrite keeps the object (a task adapter trained on a softmax transformer,
transported label-free onto bases of other sequence-operator families) and the dose variable (softmax coverage),
replaces the identification design with a lineage x operator 2x2 on an iso-corpus/iso-budget/iso-tokenizer Pile
trio, moves every General-Translation-dependent, Tinker-dependent, or scale-confounded arm out of the pilot into
separately gated phases, and re-budgets against a cited throughput anchor with a 25% reserve.

**dropped = false.** The novelty delta (cross-operator-family port + pre-registered coverage dose + same-lineage
linearized target as the identification instrument) survives every repair; no repair collapses it into Theseus,
PorTAL, UpgradeBench, or Where-Should-LoRA-Go (see §4).

---

## 1. Name and claim

**slug.** cross-family-adapter-port

**claim.** A rank-8 q/v LoRA trained on a softmax transformer can be transported, without target-side labels
(source model present, no task inputs), onto a base of a different sequence-operator family through
activation-space alignment at depth-matched sites; the fraction of fresh-LoRA lift that survives is governed by
the target's pre-registered *softmax coverage* c(T; L_eval), not by how similar the two bases' representations are —
tested by holding corpus, tokenizer, token budget, and even weight lineage fixed while only the operator changes.

**claim_scope.** portability-protocol (the phase-0 question is causal: operator vs representational similarity).

## 2. Mechanism (unchanged algebra, re-specified sites, dose, and estimand)

Source S (softmax transformer) carries per-task LoRA factors dW_S(l) = B_S(l) A_S(l) (rank 8) on q_proj and v_proj
at every layer; trained with labels on the task's train split (recipe in §7). Target T of another operator family.

*Label-free alignment (Theseus-class algebra; not claimed as new).* Run N = 2,000 unlabeled generic-text sequences
(FineWeb-Edu sample-10BT, 256 tokens each, disjoint from all task data) through both frozen bases. At the
depth-matched site pair (l_S, l_T) take the **RMS-normed inputs to the q/v projections** (what LoRA actually sees),
mask massive-activation dimensions (dims whose median |h| exceeds 50x the median over dims, per the fixed-bias
characterisation of 2402.17762), and fit R_in = argmin_R sum ||R h_T - h_S||^2 + lambda ||R||^2 (ridge; whitened
Procrustes reported alongside). Held-out alignment R^2 (500 held-out sequences) is recorded per site as a covariate.
Transport A_T = A_S R_in. Fit B_T by functional matching of the source adapter's residual effect: B_T = argmin_B
sum_x ||f_T,l(x; W_T + B A_T) - f_T,l(x; W_T) - R_out delta_S(x)||^2, <= 150 gradient steps, batch 8 x 256 tokens,
on the same generic text. No step reads task labels or task inputs.

*Sites (fixed in advance).* Hybrids: attention-pathway q/v only. Linearized transformer (Hedgehog/LoLCATs): its
q/v projections (identical shapes to S, so direct copy is defined). GLA: q_proj/v_proj of the linear-attention
layer. Mamba/Mamba2: in_proj rows producing C (query-analogue) and x (value-analogue). The "add GDN q/v sites"
sub-prediction of wave 1 is dropped (pre-explained by native placement, 2604.22127).

*Dose (pre-registered).* softmax coverage c(T; L_eval) = (1/n_mix) sum_l 1[layer l has a softmax attention branch]
x min(1, w_l / L_eval), w_l = window (infinite for global). Consequences: E2-TTT (512-token window in all 24 layers)
has c = 1 for prompts <= 512 tokens and c = 0.25 with a 2,048-token distractor prefix; a LoLCATs-style w = 64 model
has item-dependent c; the primary linearized target is built windowless (pure Hedgehog feature maps) so c = 0.

*Estimand.* Primary endpoint: test accuracy on held-out task items under **held-out prompt formats** (never used by
any fitting step; 2608.09490). Retention r = (acc_port - acc_base) / (acc_fresh - acc_base) where acc_base is the
unadapted target under the same format and verbalizer, acc_fresh is the target's fresh labeled LoRA at the same
sites and rank (recipe §7). Inclusion rule: a task enters the macro average for a target only if
acc_fresh - acc_base >= 5 pp with a paired-bootstrap 95% CI excluding 0; otherwise absolute lifts are reported.
If the permuted-task placebo port shows r > 0.10, the content-only ratio r_adj = (acc_port - acc_perm) /
(acc_fresh - acc_perm) is reported as well.

## 3. Identification design (the repair)

**Phase 0 — the lineage x operator 2x2 on a Pile trio (the cheapest decisive pilot).**
Source S = EleutherAI/pythia-160m (rev 50f5173d932e8e61f858120bcb800b97af589f46, Apache-2.0, Pile, 300B tokens).

| target | operator | softmax coverage c | weight lineage | corpus / budget | role |
|---|---|---|---|---|---|
| T1 EleutherAI/pythia-160m-deduped (rev 582159a2dfe3e712a8d47ae83dec95ae3bde8e7e, Apache-2.0) | softmax | 1 | different weights | Pile-dedup, 300B | full-attention (within-family) arm; direct copy defined |
| T2 Hedgehog-linearized pythia-160m (built in phase 0; windowless) | linear attention | 0 | **same** non-attention weights as S | S's weights + 40M FineWeb-Edu tokens | same-lineage f=0 instrument |
| T3 state-spaces/mamba2-130m (rev 3a5aea0c25d0fb43cc360e2c2aac82c26e3eed49, Apache-2.0) | SSM (Mamba-2) | 0 | different | Pile, 300B | iso-corpus, iso-budget f=0 rung |
| T4 (discovery only) state-spaces/mamba-130m-hf (rev 1e76775f628fbf1350fbe4dbb3d971ba64af25a1, no license metadata) | SSM (Mamba-1) | 0 | different | Pile, 300B | replicate T3 |

Tokenizer: pythia-160m, pythia-160m-deduped and EleutherAI/gpt-neox-20b tokenizer.json are byte-identical
(sha256 prefix c24618a1b3e6a381, verified 2026-09-01); mamba-130m-hf/mamba-370m-hf ship a re-serialized copy
(b074ad869d4f45d1) whose vocabulary equality is a phase-0 doctor check; mamba2-130m uses the gpt-neox-20b tokenizer
via mamba_ssm (vocab 50,277 vs 50,304 padded).

What the 2x2 separates: if T2 (same lineage, c = 0) retains as much as T1 (different lineage, c = 1), the
representational-similarity/corpus explanation wins and the dose claim is dead; if T2 collapses toward T3, the
operator governs. T3 vs T2 separates "f = 0" from "different weights". Corpus and token budget are constant
across S, T1, T3 (Pile, 300B), so the wave-1 confound (Platonic-similarity tracking data/scale) cannot produce
the predicted ordering.

**Phase 1 — the 340M dose ladder (gated on phase 0 passing).** Source: fla-hub/transformer-340M-10B
(rev b838e8e117845a79efb99339be042e389dd7b38b; hidden 1024, 24 layers, 32 heads; **no license on the card —
discovery-only until resolved**; licensed fallback TinyLlama/TinyLlama_v1.1 rev ff3c701f2424c7625fdefb9dd470f45ef18b02d6,
Apache-2.0, same Llama-2 32k vocabulary but tokenizer.model NOT byte-identical (9e556afd vs dadfd56d) and 22 x 2048
geometry, i.e. a Theseus-style cross-scale hop to be flagged). All 340M targets share hidden 1024 / 24 layers /
32,000 vocab, so q/v LoRA factors are shape-compatible everywhere and direct copy is always defined.

| cell | c | corpus / tokens (paper-stated) | note |
|---|---|---|---|
| startlux gdn-340m-pas-fa-layer04 / -12 / -20 (Apache-2.0) | 1/24 | FineWeb-Edu, 10B, identical recipe (2608.12149 §D.1) | three spike morphologies at fixed dose = within-dose control |
| startlux gdn-nooutgate-340m-pas-fa-layer12 | 1/24 | same | gating variant at fixed dose |
| startlux gdn-340m-isp-hybrid-3to1 (rev eec9dbb045ddeb90bc53750ac1c68a493af1aa0f) | 8/24 = 1/3 | same | attention layers [2,5,...,23] |
| fla-hub/gla-340M-15B (rev 6e04029dc090a2c55df712f18814db80aa39894f, MIT) | 0 | SlimPajama, 15B | corpus-matched to the fla-hub source |
| zeyun-zhong/e2-ttt-swiglu-340M-15B @ prompts <= 512 (MIT) | 1 | FineWeb-Edu, 15B | softmax-covered rung (reclassified) |
| same checkpoint @ 2,048-token unlabeled distractor prefix | 0.25 | same | within-model dose manipulation |

Confound table disclosed in advance: source corpus (fla-hub card empty; SlimPajama by fla-hub convention) differs
from the FineWeb-Edu rungs but is constant across all startlux/E2-TTT cells, so within-ladder contrasts
(1/24 vs 1/3; short vs long E2-TTT; morphology triplet) are corpus-clean; GLA is the source-corpus-matched c = 0 rung.
Pre-registered analysis: Spearman rho(c, r) over the 8 cells; partial rho controlling for held-out alignment R^2;
within-dose spread across pas-fa-04/12/20 vs between-dose spread.

**Phases 2–3 (outside the 16 GPU-h pilot; separately gated; listed so the claim keeps its scope).**
Phase 2 tokenizer/fertility axis on public parallel data (§8): byte-span-anchored vs token-position-anchored
alignment; from-scratch 60M bytes / BPE-8k / BPE-32k triplet on identical FineWeb-2 bytes (10 languages);
Qwen3-0.6B-Base -> Qwen3.5-4B and -> allenai/Bolmo-1B hops. Phase 3 Tinker adapter zoo + Mantel screen, funded only
if the Mantel statistic computed on the local ladders (11 source-target pairs from phases 0–1, free from the fresh
LoRAs already trained) rank-correlates >= 0.6 with measured retention; the wave-1 Kimi-K2.6 vs Kimi-Linear pairing
is replaced by the scale-matched Qwen3-8B vs Qwen3.5-9B-Base pair; the site-attribution arm is re-labelled a
LoRA-level replication of QK-Restore (2606.11052), not a new claim.

## 4. What is new (downgraded per the novelty refuter)

- The alignment algebra (Procrustes/ridge R_in, functional matching for B) is Theseus's (2602.12952), applied at
  new sites. The contribution is (a) the object — a task adapter ported from a softmax transformer onto GLA / GDN
  hybrid / TTT / SSM bases, which no prior transports; (b) the pre-registered softmax-coverage dose with its
  context-length dependence; (c) the identification instrument — a same-lineage windowless linearized target that
  separates operator family from representational similarity, which no adapter-transfer paper uses.
- Cross-tokenizer porting per se is NOT new (PorTAL already crosses Qwen3 -> Gemma/Mistral vocabularies); only
  byte-span anchoring with fertility as a dose remains new, and it is demoted to phase 2.
- The hybrid recall-damage arm substantially duplicates Attention Amnesia's QK-Restore; it is re-labelled a
  LoRA-level replication (phase 3), and the wave-1 "measures damage without attribution" sentence is withdrawn.
- No direct prior art found through 2026-09-01 (novelty refuter: 9 host calls, 7 WebSearch, WebFetch on all
  priors; this repair: arXiv API query on adapter x {Mamba, linear attention, state space, hybrid} x {transfer,
  port, transport} x LoRA and HF-papers "transfer LoRA adapter across architectures Mamba linear attention",
  both 2026-09-01, returning only native-adaptation work — 2604.22127, Memba 2506.18184, 2411.15224) for porting a
  task adapter onto a KDA/GDN/GLA/DeltaNet/TTT/Mamba base or for coverage-dose identification with a same-lineage
  linearized target. Coverage limits: Semantic Scholar unavailable; DDG blocked; OpenReview PDF of fEeBgr6nlZ unread.

## 5. Closest priors (each opened unless marked)

| prior | url | date | delta |
|---|---|---|---|
| PorTAL (Ramp Labs) | https://labs.ramp.com/research/portal-portable-task-adaptation/ | 2026-07-01 (portallib 2026-07-27) | labeled 1,000-example refit per target, softmax bases only (Gemma-4-E2B's 4:1 SWA/global mix included); we refit label-free onto non-softmax operators and measure a dose. First-party numbers (98%/94%) partly shortcut-driven (portallib #27/#28). |
| Theseus | https://arxiv.org/abs/2602.12952 | 2026-02-13 | supplies the transport algebra; only width/depth mismatches within ViT/T5 families, equal layer counts; never a non-softmax operator. |
| Where Should LoRA Go? | https://arxiv.org/abs/2604.22127 | 2026-04-24 | native LoRA placement in hybrids (attention pathway wins; GDN backbone -14.8 pp); transfers nothing; fixes our site policy and explains why the wave-1 GDN-site sub-prediction was dropped. |
| UpgradeBench | https://arxiv.org/abs/2608.20918 | 2026-08-21 | direct-copy retention law and annotation-free teacher relabel (R = 0.96–1.05) within transformers; learned mappings on shape-incompatible hops deferred — both baselines are mandatory here. |
| On the Importance of Trivial Baselines (OpenReview fEeBgr6nlZ; PDF not read) | https://openreview.net/forum?id=fEeBgr6nlZ | 2026-05-23 | direct copy beats CrossLoRA/ProLoRA between related bases; mandatory baseline, defined on our whole 32k and Pile ladders. |
| Attention Amnesia in Hybrid LLMs | https://arxiv.org/abs/2606.11052 | 2026-06-09 | attributes post-SFT NIAH collapse to W_Q/W_K and proposes QK-Restore; our recall arm becomes its LoRA-level replication. |
| LoLCATs | https://arxiv.org/abs/2410.10254 | 2024-10-14 | linearizes a base with attention transfer + LoRA; here used as an identification instrument (same-lineage c=0 target), not a method; windowless Hedgehog variant is primary. |
| Cross-Model Memory Transfer via Target-Side Reader Adaptation (Engram) | https://arxiv.org/abs/2608.17050 | 2026-08-17 | frozen artifact + thin labeled reader within transformers; control. |
| Universal Hypernetworks for Arbitrary Models | https://arxiv.org/abs/2604.02215 | 2026-04-02 | full-weight generation across heterogeneous architectures; adjacent, no adapter port, no shared task latent. |
| Massive Activations in Hybrid Linear Attention LLMs | https://arxiv.org/abs/2608.12149 | 2026-08-13 | pre-attention spikes co-vary with attention density; the reason alignment is fit on masked, normed inputs with R^2 as covariate, and the pas-fa triplet is the within-dose control. |

## 6. Falsifiable predictions

Phase 0 (160M Pile trio; macro over included tasks; 3 seeds; paired clustered SEs):
- P0-1 transport works within family: r(T1) >= 0.70 and >= direct copy - 0.05.
- P0-2 operator, not lineage: r(T2) <= r(T1) - 0.30 although T2 shares every non-attention weight with S and
  reaches held-out alignment R^2 >= 0.90 at every site.
- P0-3 f=0 rungs cluster: r(T3) <= 0.30 and |r(T2) - r(T3)| <= 0.15.
- P0-4 dose is a weight-space phenomenon: teacher-relabel retention varies by <= 0.10 across T1–T3 while the port
  varies by >= 0.30.
- P0-5 placebos inert: permuted-task port and random-orthogonal-R port give r <= 0.10 on every target.
Phase 1 (340M ladder):
- P1-1 Spearman rho(c, r) >= 0.7 over the 8 cells (c in {1, 1/3, 1/24, 0.25, 0}).
- P1-2 within-dose spread across pas-fa-04/12/20 <= 0.10 (spike morphology does not govern).
- P1-3 GLA (source-corpus-matched, c = 0) retains <= min over FineWeb-Edu hybrids (c >= 1/24) - 0.10.
- P1-4 E2-TTT: r(short) - r(2,048-prefix) >= 0.20 within one checkpoint.
- P1-5 partial rho(c, r | held-out R^2) >= 0.5.

## 7. Recipes fixed in advance

Fresh-LoRA oracle (denominator) and source adapters: rank 8 / alpha 16 on q_proj, v_proj (PorTAL geometry); up to
2,000 train examples, 5 epochs, batch 32 (not PorTAL's 4 — pre-registered deviation for GPU utilisation), lr swept
over {1e-4, 3e-4, 1e-3} at seed 0 on a 1,000-item dev split, best epoch by dev macro accuracy, 2 further seeds at
the best lr; seed SD reported. Single-token verbalizers fixed across the ladder (vocab identical within a ladder) so
evaluation is one forward per item; a secondary all-linear r16 oracle is reported as the best-achievable reference.

Tasks (phase 0/1, English; all public, license-named): SIB-200 eng_Latn topic-7 (Davlan/sib200, CC-BY-SA-4.0),
MASSIVE en-US intent-60 and scenario-18 (AmazonScience/massive, CC-BY-4.0), Banking77 (PolyAI/banking77,
CC-BY-4.0), DBpedia-14 (fancyzhx/dbpedia_14, CC-BY-SA-3.0), XNLI-en (facebook/xnli, CC-BY-NC-4.0, research use);
under the inclusion rule at 340M: Belebele eng_Latn MC (facebook/belebele, CC-BY-SA-4.0), PAWS-X en ("other",
free), and the 12 portallib tasks with shuffled choices (RampPublic/portallib-tasks rev ffc3c0e4, Apache-2.0 code)
for PorTAL comparability. Calibration text: HuggingFaceFW/fineweb-edu sample-10BT (ODC-By).

## 8. Public data plan (no General Translation data required)

Phases 0–1 use only the datasets in §7. Phase 2 (tokenizer/fertility axis): sentence pairs from FLORES+
(openlanguagedata/flores_plus, CC-BY-SA-4.0, rev 5fec6c13); translation-paired *tasks* whose items are the same across
languages — SIB-200 (CC-BY-SA-4.0, 205 languages), Belebele (CC-BY-SA-4.0, 122 variants), MASSIVE (CC-BY-4.0, 51
languages); word/byte-span alignments from SimAlign (https://github.com/cisnlp/simalign, MIT) or awesome-align
(https://github.com/neulab/awesome-align, BSD-3) run on FLORES+/SIB-200 pairs; multilingual pretraining bytes for the
60M triplet from HuggingFaceFW/fineweb-2 (ODC-By, rev af9c1333). General Translation's span-aligned production
corpora are an optional upgrade (more in-domain anchors, more abugida/CJK coverage), never a dependency.

## 9. Kill conditions

- K1 r(T2) >= r(T1) - 0.10: lineage/representational similarity governs, not the operator — dose claim dead
  (residual finding: adapters port across operators when lineage is shared; publish as such, stop the ladder).
- K2 r(T1) < 0.50: the transport machinery fails within family at 160M — dead at this scale (one 340M retry allowed
  before closing).
- K3 port <= max(direct copy, Cross-LoRA, Theseus) + 0.05 on every target where alignment is non-trivial — the
  learned alignment is inert.
- K4 teacher relabel >= port + 0.20 on every target and dose-flat — no practical portability value (the causal
  finding may stand; the protocol claim dies).
- K5 any placebo r > 0.20 — the evaluation measures format, not content; redesign before phase 1.
- K6 (phase 1) rho(c, r) < 0.3, or within-dose morphology spread > between-dose spread, or partial rho | R^2 < 0.2.
- K7 fresh LoRA on 64 labeled target examples matches the label-free port.
- K8 gains vanish under held-out prompt formats.

## 10. Cheapest decisive pilot and budget

Throughput anchor (cited): E2-TTT reports ~132 H100-hours to pretrain its 340M model on 15B tokens in plain PyTorch
(arXiv 2608.21308v2, App. B.1) = 31.6k tokens/s per H100 for full fwd+bwd at 340M; its Fig. 5 reports kTPS/TFLOPS at
340M/1.3B on one H100 (batch 4, 2K). We budget LoRA/alignment passes at 30k tok/s effective for 160M and 15k tok/s for
340M (>= 2x safety factor for small-batch fine-tuning), eval-only forward at 3x the training rate, then add a 25%
reserve. LoLCATs' README states a 7–8B linearization takes "a couple hours on one 40GB A100" on ~40M tokens; at 160M
we budget 0.4 GPU-h. Unit costs: 160M fresh/relabel run (0.8M train tokens + 0.5M eval tokens) ~35 s; port fit
(150 x 8 x 256 tokens + eval) ~25 s; eval-only ~6 s. 340M: 70 s / 50 s / 12 s.

Phase 0 doctors (CPU, no GPU): transport algebra on a planted-rotation 2-layer transformer/DeltaNet pair; signed-
permutation gauge check; tokenizer byte-identity and vocabulary-equality doctors (Pile trio; 32k ladder;
mamba2 vs gpt-neox-20b); gradient-access audit that no alignment step reads labels or task inputs; verbalizer
single-token check per ladder; inclusion-rule power analysis (n_test, SE); massive-dim mask report per checkpoint.

Phase 0 GPU (8 x H100, ~30 min wall-clock), 6 tasks x 3 seeds:
| item | runs | GPU-h |
|---|---|---|
| source LoRAs on pythia-160m (3 lr @ seed 0 + 2 seeds) | 30 | 0.29 |
| fresh oracles on T1, T2, T3 | 90 | 0.88 |
| ports (R_in per target + B_T per task/seed) | 54 | 0.38 |
| teacher relabel (UpgradeBench recipe, best lr) | 54 | 0.53 |
| generic-text KD at matched compute (seed 0) | 18 | 0.13 |
| Cross-LoRA + Theseus (seed 0, T1 and T3) | 24 | 0.20 |
| direct copy (eval only) | 54 | 0.09 |
| permuted-task placebo (eval only) + random-R placebo (seed 0) | 54 + 18 | 0.22 |
| Hedgehog linearization of pythia-160m (40M FineWeb-Edu tokens) + quality gate | 1 | 0.40 |
| subtotal | | 3.12 |
| 25% reserve | | 0.78 |
| **phase 0 total** | | **3.9 (declared 4.0)** |

Phase 1 GPU (gated on P0-1..P0-3 passing and K1–K5 not firing), 8 cells x 6 tasks x 3 seeds:
source LoRAs 0.58; fresh oracles (lr sweep on 2 cells) 168 runs 3.27; ports 144 runs 2.0; relabel seed 0 0.93;
direct copy 0.48; Cross-LoRA + Theseus seed 0 1.07; placebos 1.15 -> subtotal 9.48, +25% = 11.85 (declared 12).
Pilot total 16 GPU-h; **pilot_gpu_hours = 4 (phase 0 is the cheapest decisive pilot).**

Engineering dependencies named: a GPT-NeoX Hedgehog/LoLCATs path (LoLCATs code covers Llama/Mistral; the attention
swap for GPTNeoXAttention with parallel residual is a small port, Apache-2.0 code); mamba_ssm CUDA kernels or the
transformers eager Mamba path at 130M; fla 0.5.2 pinned for startlux; e2_ttt package for E2-TTT. All in digest-
pinned Docker images through Slurm with SIGUSR1 checkpoint/resume.

## 11. Controls

Fresh labeled LoRA on the target at matched sites/rank (denominator) and all-linear r16 (best-achievable);
direct copy / identity alignment wherever shapes allow (UpgradeBench; fEeBgr6nlZ) — defined on both ladders;
annotation-free teacher relabel on the task's unlabeled train inputs (UpgradeBench recipe) at matched compute;
generic-text output distillation (source-adapted vs base output shift on the same 2,000 calibration sequences) at
matched compute — the function-level analogue that isolates whether weight-space transport adds anything;
Cross-LoRA (2508.05232) and Theseus (2602.12952); PorTAL label-fitted refit on two 340M cells (upper reference;
first-party numbers); permuted-task adapter (provably carries no task-t label information: disjoint label spaces)
and random-orthogonal R (drawn independently of any activation) as inert placebos; alignment fit with and without
massive-dim masking, held-out R^2 covariate, partial correlation; pas-fa-04/12/20 morphology triplet and
nooutgate variant at fixed dose; E2-TTT short vs long-prefix within-model dose; 64-labeled-example fresh LoRA
(cheap-labels bound); held-out prompt formats (2608.09490); two-forward-pass prefix-invariance audit on adapted
hybrids (2608.22876); 3 seeds with paired clustered SEs; token/GPU-hour ledger; model+adapter as the tested object.
Phase-2-only controls: token-position anchoring, greedy byte-prefix token alignment, BLD/ACTD output distillation,
parity-aware / \p{L}+-fixed BPE arm (2606.15044, 2608.26449), romanized-input arm (2608.25904), Hyper-X language x
task adapter (2205.12148), Engram reader (2608.17050), KV-translation activation port (2608.30963). Phase-3-only:
permuted-task Mantel null; Tinker module-coverage table.

## 12. Kevin advantage (honest)

The decisive pilot has no unique-asset dependency: phases 0–1 need the 8 x H100 node, the sealed Docker/Slurm/
checkpoint harness (sealed task x base x seed cells with SIGUSR1 resume), and public data. Unique pieces enter only
later: General Translation's span-aligned production parallel corpora as an upgrade for phase-2 anchors across
abugida/CJK/Latin scripts; registered cross-family targets with pinned revisions (qwen3.5-4b, qwen3.5-9b,
kimi-linear-48b-a3b-base, llada-8b-base, mamba-130m-hf; Bolmo-1B and the Pile trio to register); Tinker as the
adapter-zoo factory for phase 3.

## 13. Collision risk

medium. Searches: wave-1 novelty refuter (9 host calls, 7 WebSearch, WebFetch on every prior, portallib README/
issues, RampPublic HF org, X bookmarks) plus this repair's arXiv-API and HF-papers recency queries (2026-09-01):
nothing ports an adapter onto a non-softmax operator. Groups able to move quickly: Ramp (portallib updated
2026-08-29), the Theseus authors, the LoLCATs/Hedgehog group (Hazy Research), the Attention Amnesia and
Where-Should-LoRA-Go authors. IP: NVIDIA US20260105282A1 (gated delta networks, pending) concerns kernels/
architecture; an adapter-level port on released GDN checkpoints is not a kernel contribution — low exposure, noted.

## 14. Monitorability and safety

Weight-space adapters; the reasoning medium is unchanged. Ported adapters can carry source behaviours (including
backdoors) across families: a refusal/harm regression and a poisoned-source-task transfer measurement (one task with
a planted trigger -> label association; trigger transfer rate on every target) are mandatory phase-0 deliverables.
Data rights: Pythia Apache-2.0; mamba2-130m Apache-2.0; mamba-130m-hf no license metadata (discovery-only);
LoLCATs code Apache-2.0; startlux Apache-2.0; E2-TTT MIT; fla-hub gla MIT; fla-hub transformer-340M-10B unlicensed
(discovery-only; licensed fallback TinyLlama Apache-2.0, flagged cross-scale); TinyLlama SlimPajama; task data as
listed in §7–8 (XNLI CC-BY-NC-4.0 limits commercial reuse of that arm); FineWeb-Edu/FineWeb-2 ODC-By; portallib
Apache-2.0. Parallel data (phase 2) is used only as unlabeled paired stimulus, never redistributed.

## 15. Negative-result value

K1 firing (same-lineage linearized target retains like a transformer) establishes that task adapters live in
operator-agnostic residual directions when lineage is shared — a positive statement about linearization retrofits
(LoLCATs-class) inheriting adapters for free, and a bound on the "no weight-space method for shape-incompatible
hops" clause of UpgradeBench. K2/K3 (transport fails or alignment inert) confirms UpgradeBench's direct-copy law
across operators and closes G3 as a weight-space gap. K4 (relabel dominates, dose-flat) tells every PorTAL successor
that cross-family porting should go through function/relabel, with numbers. Either way the deliverables stand: the
first sealed multi-family task x base portability cell with inclusion-rule hygiene and shuffled choices, a
public Pile-trio/32k-ladder harness with pinned revisions, the massive-dim mask and alignment-R^2 report per
checkpoint (local-model G3), and a "LoRA is / is not immune to Attention Amnesia" replication in phase 3.

## 16. targets_gaps

G3 (porting a task adapter across operator families), G4 (label-free base alignment; parallel-data calibration
deferred to phase 2), bookmarks G3 (PorTAL-style portability onto a hybrid linear-attention base), benchmarks-eval
G1 (seed/MDE norms via the inclusion rule and power analysis), local-model G3 (LoRA throughput/memory report on
2026 hybrids at 340M); G22 only in phase 3.

## 17. Repairs made (wave-1 objection -> fix or accepted limitation)

Identification lens:
1. Iso-vocab but not iso-corpus/iso-budget; confounds collinear with f_attn -> phase 0 moved to the Pile trio
   (pythia-160m -> pythia-160m-deduped / mamba2-130m: same corpus, same 300B budget, byte-identical tokenizer) plus a
   same-weight-lineage linearized target; at 340M the dose contrasts are within the startlux suite (FineWeb-Edu 10B,
   identical recipe per 2608.12149 §D.1) and GLA is the source-corpus-matched c=0 rung; residual source-corpus
   mismatch at 340M is disclosed as a constant offset, not a dose correlate.
2. Dose ill-defined on E2-TTT -> pre-registered softmax coverage c(T; L_eval) with a window term; E2-TTT is c=1 at
   <= 512 tokens and c=0.25 under a 2,048-token prefix (now a within-model dose manipulation, P1-4); the primary
   linearized target is windowless so c=0 is exact.
3. Massive activations confound alignment -> R fit on RMS-normed q/v inputs with massive dims masked (2402.17762
   criterion), masked/unmasked both reported, held-out R^2 per site as covariate, partial correlation pre-registered
   (P1-5, K6), and the startlux pas-fa-04/12/20 triplet added as the fixed-dose morphology control (P1-2).
4. "Adding GDN q/v sites lowers retention" pre-explained by native placement -> sub-prediction dropped; site policy
   fixed; the denominator is the fresh LoRA at the same sites and rank.
5. Teacher-relabel control absent and the method is source-present -> UpgradeBench relabel and generic-text KD at
   matched compute are mandatory in phases 0 and 1; the claim now says "without target-side labels, source model
   present"; relabel dose-flatness is a prediction (P0-4) and relabel dominance is a kill (K4).
6. Undertuned denominator -> fixed recipe with lr sweep and best-epoch-on-dev, batch 32, seed SD reported;
   task suite switched to large-lift classification tasks; inclusion rule (>= 5 pp lift with CI) and SE budget so
   retention differences of 0.3 are resolvable with 3 seeds.
7. Screen and site arms confounded by scale/post-training -> both removed from the pilot; Mantel validated against
   measured retention on 11 local pairs before any hosted spend; Kimi-K2.6 pairing replaced by Qwen3-8B vs
   Qwen3.5-9B-Base; the recall arm re-labelled a QK-Restore LoRA replication. Accepted limitation: Tinker exposes only
   coarse {attn, mlp, unembed} toggles, so a 5-group Shapley at 1T is not possible from hosted exports.
8. PorTAL numbers first-party and shortcut-driven; 0.6B -> 4B hop changes everything at once; LoLCATs-style control
   missing -> PorTAL numbers labelled first-party (issues #27/#28 cited); the 0.6B -> 4B hop removed from the pilot
   (phase 2); the same-lineage linearized target is now the central instrument.

Feasibility lens:
1. Parallel-data assumption unsupported -> phases 0–1 need no parallel data; phase 2 names FLORES+, SIB-200,
   Belebele, MASSIVE, FineWeb-2 with licenses and SimAlign/awesome-align for spans; GT data optional only.
2. Tinker boundary (no key, stale SDK, ~$150 zoo, no adapter import) -> Tinker removed from the pilot; phase 3 gated
   on key + SDK doctor + local Mantel validation; the refuter's cost estimate (~$150 for a five-base zoo) accepted.
3. Not decisive (no held-out softmax target; E2-TTT misclassified; 3-level dose with ties; near-chance
   denominators) -> held-out softmax targets pythia-160m-deduped (phase 0) and E2-TTT@short (340M); dose now 5 levels
   plus two within-model manipulations; large-lift classification tasks with the inclusion rule replace the
   near-chance MC suite at small scale (portallib suite kept only for comparability at 340M).
4. Budget (~45 GPU-h for 3 seeds) and licenses -> re-budgeted with the E2-TTT throughput anchor and a 25% reserve:
   4 GPU-h phase 0 + 12 GPU-h phase 1; unlicensed fla-hub transformer and mamba-130m-hf are discovery-only, with
   TinyLlama (Apache-2.0, flagged cross-scale) and mamba2-130m (Apache-2.0) as publication-eligible substitutes.

Novelty lens caveats: what_is_new downgraded (algebra = Theseus; cross-tokenizer per se = PorTAL; recall arm =
QK-Restore replication); trivial-baselines paper and Universal Hypernetworks added as priors/baselines.
