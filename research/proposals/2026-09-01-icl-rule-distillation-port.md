# Research Direction: Portable In-Context Write-Rule Distillation (icl-rule-distillation-port)

**Status:** draft
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted mid-sweep; arXiv API, Semantic Scholar and Jina blocked from the Mac (HTTP 429/401), arXiv reached only through the H100-host relay and abstract pages; OpenReview note bodies unreadable; no ACL Anthology, Google Scholar, patent or Chinese-venue search beyond the 2026-09-01 verification pass; ICLR 2027 submissions invisible; nothing executed on the H100 node or on Tinker; no parallel corpus exists in the repository
**Budgets:** queries=80; wall_minutes=600; tokens=900000; dollars=40; waves=4; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/icl-rule-distillation-port/bundle.json

## Claim and Research Question

**Claim (portability-protocol scope, rescoped in wave 3).** The content-dependent part of a frozen softmax
transformer's in-context update can be distilled into an explicit rank-8 fast-weight write rule at a canonical 64-d
interface such that, on held-out task families the distillation loss never sees, the rule reproduces the teacher's own
8-shot predictions (teacher fidelity) more faithfully than a dense-preconditioned-GD superset rule trained at the same
interface, on the same gold-plus-shuffled-label episode mix, with the same compute; and that the same frozen rule,
attached through label-free maps strictly after recurrent sublayers of pure-recurrent bases trained on the same corpus,
tokenizer and token budget, keeps a measurable fraction of that fidelity with no demonstrations in the window.

**Research question.** Is the object worth porting between sequence-operator families the *write rule* (how a context
item becomes a state update), rather than weights (Generative Adapter, Doc-to-LoRA) or state (Cache-to-Cache, KV
translation)? Concretely: (i) does behavioural distillation of a transformer's in-context update produce a rule that is
more than preconditioned gradient descent at a low-rank interface, judged by fidelity to the teacher's predictions and
errors rather than by accuracy alone; (ii) does that rule survive a label-free port to DeltaNet, GLA, RetNet, HGRN2,
GSA and Mamba bases that have no KV cache to receive state; (iii) do its writes carry content beyond the frozen
encoder's own language invariance (write in English, read in a held-out language).

**What this is not.** It is not an architecture-causal claim: every arm is a frozen pretrained retrofit and no matched
from-scratch arm is budgeted (wave-3 rescope, both judges). It is not a new kernel, a new memory product, or a claim
about Mamba specifically. The pre-registered collapse case is explicit: if the distilled rule ties a label-trained
sibling rule at the same interface, the result is an instance of Fast Weight Layers / SRWM and is reported as such.

## Strategic Fit and Why Now

CoTCodec's frontier program wants factorizations that make something portable across models (the PorTAL move), not
another strap-on memory layer. This direction targets gaps G5 (porting an update rule rather than weights), G2
(language-controlled probes of recurrent state through write-A/read-B), G6 (behavioural evaluation of update-rule
variants with causality audits) and G7 (reset, deletion and poisoning attestation) of the 2026-09-01 sweep synthesis.

Why now: (a) iso-corpus, iso-tokenizer, iso-token-budget ladders of 1.3B recurrent and transformer bases exist publicly
(fla-hub 1.3B-100B on SlimPajama; the Pile 300B 2.7B triplet), which removes the matching confound that killed the
wave-1 version; (b) 2026 work has multiplied derived fast-weight rules (Modular TTT, Falcon normalised rules, Kaczmarz
and OSDN preconditioning) without asking whether a transformer's implicit rule is any of them; (c) the state-transfer
line (Cache-to-Cache, XKV, KV translation) has shown the *reverse* direction is crowded, so the rule-as-object framing
is the remaining open seam; (d) the repository already has SIGUSR1-resumable truncated-BPTT harness pieces and the
SR-TTT-derived causality doctors this protocol needs.

Kevin's asset fit is honest but partial: the pilot substrate is public; the unique pieces are the 8xH100 node with a
residual-hook harness, the already-registered Kimi-Linear-48B-A3B-Base for a later multilingual cross-operator pair,
and General Translation's span-aligned parallel demonstration sets as an optional upgrade to the equivariance stage.
Tinker cannot help here (no hidden states, no optimizer access).

## Primary-Source Evidence

Primary sources for the mechanism, the controls and the substrate, with the role each plays:

- Function Vectors, Todd et al., ICLR 2024 — https://arxiv.org/abs/2310.15213 and
  https://github.com/ericwtodd/function_vectors (MIT; 29 abstractive + 28 extractive task files): the held-out task
  suite and the shuffled-label reference (Table 2: GPT-J still reaches 39.1% on shuffled-label prompts, which is why a
  gold-minus-shuffled numerator is required and why the placebo must be matched across rules).
- Task recognition vs task learning, Pan et al. 2023 — https://arxiv.org/abs/2305.09731; Min et al. 2022 —
  https://arxiv.org/abs/2202.12837: the TR/TL decomposition the endpoints use.
- Contextual calibration — https://arxiv.org/abs/2102.09690: the zero-shot reference.
- Pretraining task diversity and the dMMSE regime, Raventós et al. 2023 — https://arxiv.org/abs/2306.15063: Stage A
  regime where the implicit predictor is provably not ridge/GD.
- Learning without training (implicit low-rank patch view of ICL) — https://arxiv.org/abs/2507.16003; Can GD Simulate
  Prompting — https://arxiv.org/abs/2506.20989: the two analytic/meta-learned same-model priors the delta is measured
  against.
- Derived rules used as the superset control's special cases: Kaczmarz normalisation — https://arxiv.org/abs/2605.08587;
  OSDN diagonal preconditioning — https://arxiv.org/abs/2605.13473; Falcon normalised rules —
  https://arxiv.org/abs/2608.27763; Modular TTT — https://arxiv.org/abs/2608.07110.
- Reservoir control motivation (random transformers already do in-context recall) — https://arxiv.org/abs/2410.04368.
- Causality audit sources for the two-forward-pass prefix-invariance gate — https://arxiv.org/abs/2603.06642 and
  https://arxiv.org/abs/2608.22876.
- Substrate: fla-hub/transformer-1.3B-100B — https://huggingface.co/fla-hub/transformer-1.3B-100B; the 1.3B-100B
  recurrent ladder (delta_net, gla, retnet, hgrn2, gsa, mamba) under https://huggingface.co/fla-hub;
  startlux-models/gdn-1.3b-isp-hybrid-3to1-50b — https://huggingface.co/startlux-models/gdn-1.3b-isp-hybrid-3to1-50b;
  state-spaces/mamba2attn-2.7b — https://huggingface.co/state-spaces/mamba2attn-2.7b; Qwen/Qwen3-1.7B-Base —
  https://huggingface.co/Qwen/Qwen3-1.7B-Base; fla v0.5.2 —
  https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2.
- Data: SIB-200 — https://huggingface.co/datasets/Davlan/sib200; MASSIVE —
  https://huggingface.co/datasets/AmazonScience/massive; FineWeb-Edu —
  https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu; Super-NaturalInstructions —
  https://github.com/allenai/natural-instructions.
- Throughput anchor: llm.c GPT-2 1.6B at 381,690 tok/s and 47.4% bf16 MFU on 8xH100 —
  https://github.com/karpathy/llm.c/discussions/677 (first-party log line).
- Cross-lingual retrieval baselines required by the verification pass for any G2 claim: MLNeedle —
  https://arxiv.org/abs/2408.10151; ONERULER — https://arxiv.org/abs/2503.01996.

First-party versus independent: every 2026 item above is a first-party preprint or model card; peer-reviewed status is
confirmed only for Function Vectors (ICLR 2024), Pan et al. (Findings of EMNLP 2023), Min et al. (EMNLP 2022), and
Raventós et al. (NeurIPS 2023). No number below was reproduced on hardware by this cell.

### Claim registry

Protocol followed: the ARS claim verification protocol (scratchpad/ext/ars/academic-pipeline/references/
claim_verification_protocol.md, Phase E1-E3). Status vocabulary: VERIFIED = the locator was opened by a gauntlet cell on
2026-09-01 and the number matched; FIRST_PARTY = the number is the authors' or vendor's own statement without an
independent replication located; UNVERIFIABLE_ACCESS = the source body could not be reached from this network. Design
thresholds (rank 8, 64-d interface, 8 demonstrations, 2:1 gold-to-shuffled mix, 0.10 fidelity effect, 0.05 TR tolerance,
400 queries, 10-point eligibility floor, budget lines) are pre-registered choices recorded in the contract YAML, not
claims about the world, and are therefore not registered as claims.

| claim_id | claim text | source URL + locator | status |
|---|---|---|---|
| C01 | fla-hub/transformer-1.3B-100B: revision d6f66f4181fa669e5863327815b44533e3a395e7, MIT, 24 layers, width 2048, 32k vocab, 100B SlimPajama tokens | https://huggingface.co/fla-hub/transformer-1.3B-100B (model card, config.json, /revision/ endpoint) | VERIFIED (wave-2 feasibility refuter) |
| C02 | fla-hub 1.3B-100B ladder revisions: delta_net b4dcbbaf…, gla 46b15820…, retnet 7fddefc4…, hgrn2 2f413dd9…, gsa 1e4ffdae…, mamba 49d177ea…, transformer-2.7B e29b06c9…; tokenizer.model blob sha256 dadfd56d7667… identical across all eight repos; MIT on transformer/gla/retnet/hgrn2/gsa, no license field on delta_net and mamba cards | https://huggingface.co/fla-hub/gla-1.3B-100B and sibling repos (config.json, tokenizer.model) | VERIFIED (wave-2 feasibility refuter) |
| C03 | startlux gdn-1.3b-isp-hybrid-3to1-50b: 24 layers, attention at 0-based layers 2,5,8,11,14,17,20,23, vocab 32000, Apache-2.0, revision 0ced446e767709a15cbe2004948eac1fdea443db, fla v0.5.2 pin | https://huggingface.co/startlux-models/gdn-1.3b-isp-hybrid-3to1-50b/raw/main/config.json | VERIFIED (wave-2 identification and feasibility refuters) |
| C04 | state-spaces/mamba2attn-2.7b: attention at 0-based layers 9,18,27,36,45,56 of 64; transformerpp-2.7b, mamba2-2.7b, mamba2attn-2.7b trained on 300B Pile tokens; Apache-2.0 | https://huggingface.co/state-spaces/mamba2attn-2.7b/blob/main/config.json and https://github.com/state-spaces/mamba/blob/main/README.md | VERIFIED (wave-2 feasibility refuter) |
| C05 | llm.c GPT-2 1.6B trains at 381,690 tok/s at 47.4% bf16 MFU on 8xH100 | https://github.com/karpathy/llm.c/discussions/677 (log line) | FIRST_PARTY (author log; wording verified verbatim by wave-2 feasibility refuter) |
| C06 | Function Vectors suite: 29 abstractive and 28 extractive task files, MIT | https://github.com/ericwtodd/function_vectors/tree/main/dataset_files | VERIFIED (wave-2 feasibility refuter) |
| C07 | GPT-J reaches 39.1% on shuffled-label prompts | https://arxiv.org/abs/2310.15213 (Table 2) | FIRST_PARTY (peer-reviewed ICLR 2024; table read by wave-2 identification refuter, not re-opened by this cell) |
| C08 | SIB-200: 205 languages, 7 topics, 701/99/204 train/dev/test per language, CC-BY-SA-4.0, parallel FLORES-200 sentences | https://huggingface.co/datasets/Davlan/sib200 (dataset card) | VERIFIED (wave-2 feasibility refuter) |
| C09 | MASSIVE: 51 languages, 18 scenarios / 60 intents, 11,514/2,033/2,974 per language, CC-BY-4.0, human translations of SLURP | https://huggingface.co/datasets/AmazonScience/massive (dataset card) | VERIFIED (wave-2 feasibility refuter) |
| C10 | fla v0.5.2 released 2026-07-27 (GitHub tag and PyPI), commit 9c8e42e762fce087c27b673af4922795d9edb85e; fla Mamba layer has a slow_forward fallback without mamba_ssm | https://github.com/fla-org/flash-linear-attention/releases/tag/v0.5.2 and https://github.com/fla-org/flash-linear-attention/blob/v0.5.2/fla/layers/mamba.py | VERIFIED (wave-2 feasibility refuter) |
| C11 | Qwen/Qwen3-1.7B-Base revision ea980cb0a6c2ae4b936e82123acc929f1cec04c1, Apache-2.0 | https://huggingface.co/Qwen/Qwen3-1.7B-Base | VERIFIED (wave-2 feasibility refuter) |
| C12 | Hidden states classify statement truth at 71-83% (Azaria and Mitchell) | https://arxiv.org/abs/2304.13734 (abstract) | FIRST_PARTY (abstract-level; motivates the matched-placebo repair) |
| C13 | Gold-minus-random-label gap on classification is about 3-5 points at OPT-2.7B | https://arxiv.org/abs/2305.09731 (Figure 2 region) | FIRST_PARTY (peer-reviewed; figure read in wave 2, not re-opened) |
| C14 | Phone-book lookup: Pythia at or above 410M near-perfect; Mamba degrades only from about 70 entries | https://arxiv.org/abs/2402.01032 (abstract and Figure 1) | FIRST_PARTY (abstract-level) |
| C15 | Mamba-2.8B is on par with Pythia/GPT-J on 27 function-induction ICL tasks | https://arxiv.org/abs/2402.03170 (abstract) | FIRST_PARTY (abstract-level) |
| C16 | In the finite-task-prior regime a small pretrained transformer behaves as the discrete Bayesian (dMMSE) predictor, not ridge regression | https://arxiv.org/abs/2306.15063 (Section 3) | FIRST_PARTY (peer-reviewed NeurIPS 2023) |
| C17 | DeltaNet/Gated DeltaNet training throughput is slightly below Mamba2, Transformer++ with FlashAttention-2 fastest at 2K | https://arxiv.org/abs/2412.06464 (Figure 3) | FIRST_PARTY (author figure) |
| C18 | Trained Persistent Memory (Jeong): universal write rule shared across backbones plus architecture-specific read paths; fixed aggregation P_t = gamma P_(t-1) + A^T V; tested only on GPT-2-124M and Flan-T5-XL; never ported, never compared with ICL or GD | https://arxiv.org/html/2603.22329v1 and https://arxiv.org/html/2603.16413v1 | VERIFIED (HTML opened by wave-2 novelty refuter) |
| C19 | Doc-to-LoRA: KL(teacher-with-context, student-without) objective, rank-8 LoRA, requires retraining the hypernetwork for a new target LLM | https://arxiv.org/html/2602.15902 | VERIFIED (HTML opened by wave-2 novelty refuter) |
| C20 | Moonlight-16B-A3B and Kimi-Linear-48B-A3B-Base: both MIT, both 5.7T tokens, identical tiktoken.model blob b6c497a7469b… | https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base and https://huggingface.co/moonshotai/Moonlight-16B-A3B (cards) | FIRST_PARTY (card-stated; blob identity checked by wave-2 note) |
| C21 | Kimi-Linear-48B-A3B-Base is registered at revision 3b171c17bfc4ee348599b6781a2ca8715c21c8dc; fla-hub/delta_net-1.3B-8K-100B is registered as delta-net-1.3b-8k with an unresolved model-card license | models/registry.yaml in this repository | VERIFIED (in-repo) |
| C22 | NVIDIA US20260105282A1 "Gated delta networks" is a pending patent application | verification pass note (research/gauntlet/2026-09-01-frontier/design-brief.md, VERIFICATION PASS CORRECTIONS) | UNVERIFIABLE_ACCESS (patent office not reachable from this cell; carried from the verification pass) |
| C23 | Discovery image: ID sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2; repo digest sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3; revision 581ded8df71564b0212d8af5dcd401257aa6a28f; created 2026-08-16; CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0; no vllm, peft, fla or flash-attn | fal-h100-01 docker inspect recorded in the 2026-09-01 spec brief | VERIFIED (host inspection, 2026-09-01) |
| C24 | Budget ledger: Stage B 3.2, C 2.1, D 2.5, E 3.3 GPU-h, program 11.1 GPU-h at 25% MFU (247 TFLOPS per GPU) with 25% reserve per stage | derived in this proposal from C01, C05, C11 and model parameter counts; recomputed line by line by the wave-2 feasibility refuter | VERIFIED (arithmetic only; no measurement) |
| C25 | Power: 0.77 at a 0.10 fidelity effect with 8 eligible families and 3 seeds; 0.88 at 10 families; 0.98 at a 0.15 effect with 8 families; Type-I 0.03 under the null | computed by this cell with numpy 2.5.2 and scipy 1.18.0 from the simulation described in Evaluation | VERIFIED (computed; assumptions marked unknown) |
| C26 | Wave-1 novelty refuter ran 16 arXiv, 9 DDG, 5 HF and 1 OpenReview queries; wave-2 repair ran 6 hostsearch calls; both judges scored 62/100 | research/gauntlet/2026-09-01-frontier/wave1-ledger.md, wave2-ledger.md, wave2-result.json | VERIFIED (in-repo) |
| C27 | Cross-lingual needle retrieval on softmax transformers is already established (MLNeedle, NAACL 2025; ONERULER) | https://arxiv.org/abs/2408.10151 and https://arxiv.org/abs/2503.01996 | FIRST_PARTY (abstract-level; cited as mandatory baselines by the verification pass) |

## Closest Prior Work

All items were opened at abstract or HTML level by a gauntlet cell. The wave-3 repair adds items 8-12, named by both
judges, and discriminates against each.

1. Can Gradient Descent Simulate Prompting? — https://arxiv.org/abs/2506.20989 (2025-06-26). Meta-trained same-model
   gradient step emulates conditioning; not externalised, not ported. Here the rule is externalised at a canonical
   interface, frozen, ported across operator families, and compared with a preconditioned-GD superset.
2. Learning without training: the implicit dynamics of ICL — https://arxiv.org/abs/2507.16003 (v4 2026-06-02). Analytic
   low-rank MLP patch inside one block of one model. Here the update is a learned rule obtained by behavioural
   distillation and tested cross-family.
3. Generative Adapter — https://arxiv.org/abs/2411.05877; Doc-to-LoRA — https://arxiv.org/abs/2602.15902. Context to
   per-model weight-update generators (WHAT, per model); Doc-to-LoRA uses the same KL objective and rank 8 but its own
   text says the hypernetwork must be retrained for a new target LLM (C19). Here the object is the rule and the state is
   base-independent.
4. Cache-to-Cache — https://arxiv.org/abs/2510.03215; XKV — https://arxiv.org/abs/2608.20617; KV translation —
   https://arxiv.org/abs/2608.30963. Transfer KV or latent STATE between frozen LMs. Here the RULE is transferred and the
   targets have no KV cache.
5. Modular TTT — https://arxiv.org/abs/2608.07110; Falcon rules — https://arxiv.org/abs/2608.27763. Learned or derived
   inner rules within one family, not distilled from a transformer and never transferred; used here as the derived-rule
   control family.
6. Fast Weight Layers — https://arxiv.org/abs/2212.02475; SRWM — https://arxiv.org/abs/2202.05780. Learned fast-weight
   sidecars improving in-context adaptation on a base: the weaker occupied claim this proposal collapses into if the
   distilled rule ties a label-trained sibling.
7. Algorithm Distillation — https://arxiv.org/abs/2210.14215. Distils an algorithm INTO a sequence model (reverse
   direction).
8. Trained Persistent Memory for frozen decoder-only / encoder-decoder LLMs (Jeong) — https://arxiv.org/abs/2603.22329
   and https://arxiv.org/abs/2603.16413. The closest FRAMING prior: it already states "a universal write rule shared
   across backbones plus architecture-specific read paths". Its write rule is a fixed attention/Hebbian aggregation with
   frozen random write projections, trained with LM loss, evaluated on two same-family models, never ported and never
   compared with ICL or GD (C18). Delta here: the rule is learned by distillation from a transformer's in-context
   behaviour, compared head-to-head with a GD superset at the same interface, ported frozen across operator families,
   and evaluated on teacher fidelity on held-out families.
9. FAAST — https://arxiv.org/abs/2605.04651. Closed-form pseudoinverse fast weights on frozen hidden states as an
   alternative to ICL; model-agnostic; a fixed rule, not distilled, not transferred. It is a natural extra special case
   for the derived-rule grid and is added there.
10. Language Models Need Sleep — https://arxiv.org/abs/2605.26099. A learned local rule writing context into SSM-block
    fast weights inside one end-to-end-trained model; not distilled from a transformer, not ported.
11. Cross-model Control — https://arxiv.org/abs/2410.17599. A portable logit-shift tiny LM across tokenizers and
    architectures: it transfers a delta language model, not an in-context update rule, and needs no write/read state.
12. ICLCA — https://arxiv.org/abs/2406.02847. Exact ICL-to-bias conversion in linearized transformers; analytic, single
    model, no port.

Also relevant, not collisions: Memory Decoder — https://arxiv.org/abs/2508.09874; Latent Context Compilation —
https://arxiv.org/abs/2602.21221; Hebbian/gradient plasticity fast-weight modules — https://arxiv.org/abs/2510.21908;
meta-learned update rules that generalize across architectures — https://arxiv.org/abs/1804.00222 (weakens the
"learned rules transfer" surprise, does not distil from ICL or target frozen LMs).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Write rule distilled by KL from a frozen transformer's in-context behaviour into an external rank-8 fast-weight memory | Doc-to-LoRA (https://arxiv.org/abs/2602.15902); Can GD Simulate Prompting (https://arxiv.org/abs/2506.20989) | no | Prior emits per-model WHAT (adapter or gradient step); here the HOW (write rule) is the trained object and the base stays frozen with no test-time gradients | 0.60 |
| Canonical 64-d interface with base-specific rank-8 P/Q ports fitted label-free | Trained Persistent Memory (https://arxiv.org/abs/2603.22329); Cache-to-Cache (https://arxiv.org/abs/2510.03215) | partly | Jeong shares the framing (universal write, per-backbone read) but uses a fixed Hebbian rule, LM loss and no port; C2C transfers state through a projector rather than a rule | 0.55 |
| Head-to-head against a dense-preconditioned-GD superset trained at the same interface, loss, episode mix and compute | Falcon (https://arxiv.org/abs/2608.27763); Kaczmarz (https://arxiv.org/abs/2605.08587); OSDN (https://arxiv.org/abs/2605.13473); FAAST (https://arxiv.org/abs/2605.04651) | no | Priors propose derived rules; none asks whether a transformer's implicit rule is one of them under a matched behavioural distillation | 0.60 |
| Teacher-fidelity endpoint on held-out families with a matched gold-plus-shuffled placebo (wave-3) | Function Vectors (https://arxiv.org/abs/2310.15213); TR/TL (https://arxiv.org/abs/2305.09731) | no | Priors measure accuracy and TR/TL of the base; here fidelity to the teacher's per-query predictions and errors is the primary object and the placebo is in-distribution for every rule | 0.65 |
| Frozen-rule port to six pure-recurrent 1.3B-100B bases on one corpus, tokenizer and budget | Attention-to-Mamba weight distillation (https://arxiv.org/abs/2604.14191); XKV (https://arxiv.org/abs/2608.20617) | no | Priors transfer weights or state; here the rule is transferred to bases with no KV cache and the site is strictly after a recurrent sublayer | 0.55 |
| Downstream-attention read-path ablation on hybrids (wave-3) | none located | no | Replaces the inert adjacent-layer site factor; a genuine counterfactual on whether softmax downstream of the injection carries the readout | 0.50 |
| Write-A/read-B held-out-language probe of the writes' content | MLNeedle (https://arxiv.org/abs/2408.10151); ONERULER (https://arxiv.org/abs/2503.01996) | no | Priors probe softmax retrieval across languages; here the probe is of an explicit external write against an encoder-invariance baseline (R_GD with lambda_eq = 0), with a pre-registered null | 0.50 |

Novelty wording: No direct prior art found through 2026-09-01 under the coverage stated in the header (H100-host arXiv
relay, HF papers, Crossref, OpenReview titles only, WebFetch abstract pages, GitHub and Hugging Face metadata, the wave-1
refuter's 31 queries and the wave-2 repair's 6 hostsearch calls; Semantic Scholar, OpenReview bodies, ACL Anthology,
patents and Chinese venues not searched). The wave-2 novelty refuter did not refute (confidence 0.6) and the blind
discrimination judged the mechanism different from its nearest prior (confidence 0.88). Collision risk stays high: the
intersection of context-to-weights, state-transfer and TTT vocabularies is crowded and a 2026 paper under different
wording could exist. This is not a global-priority claim and is pending a signed provider-distinct audit.

## Mechanism and Falsifiable Predictions

Frozen source transformer T. An episode is eight formatted demonstrations c_1..c_8 = (x_i, y_i) plus probe queries q of
the same task. Two structurally separated passes make causality a property of the code, not of a penalty:

```text
Pass W (write), per demonstration c_i encoded alone by the frozen base, pooled residuals at K = 4 sites
(depth fractions 0.25 / 0.50 / 0.75 / 1.00; on non-transformer bases always the residual after a recurrent sublayer):
  k_i = P_b^k hbar^k(x_i)          v_i = P_b^k hbar^k(y_i)          e_i = v_i - M_i^k k_i
  (rho_i, eta_i, u_i, w_i) = R_theta(k_i, v_i, e_i, M_i^k k_i, ||k_i||, i, stats(M_i^k))     rho in [0,1], eta ≥ 0
  M_(i+1)^k = Pi_8[ rho_i M_i^k + eta_i u_i w_i^T ]                                          Pi_8 = rank-8 truncation
Pass R (read), probes processed with M frozen, probes never enter Pass W:
  h^k ← h^k + Q_b^k M^k P_b^k h^k        at each site k
Interface: M^k in R^(64x64) rank 8; P_b^k (64 x d_b) and Q_b^k (d_b x 64) rank-8 factorised, the only base-specific
parameters (about 2.7e5 at d_b = 2048 over four sites). R_theta is a 2-layer MLP, width 256, about 1e5 parameters,
shared across sites and bases.
Superset control at the same interface (R_GD):
  u_i = W e_i     w_i = k_i     eta_i = eta_0 (i+1)^(-gamma) / (||k_i||^2 + eps)^beta     rho_i = rho_0
  learned W in R^(64x64) and scalars (eta_0, gamma, beta, rho_0); contains the delta rule (W = I, beta = gamma = 0),
  Kaczmarz (beta = 1), OSDN diagonal (W diagonal), Falcon normalised rules and FAAST pseudoinverse steps as special cases.
Distillation loss (source only; distillation families D only; gold AND shuffled-label episodes, 2:1):
  L_dist = sum_i sum_q KL( p_T(. | q, c_(≤ i)) || p_(T,M_i)(. | q) )      with c the gold or the shuffled episode
  truncated BPTT through the 8 writes, over theta (or W and scalars), P_T, Q_T.
Cross-lingual equivariance (Stage D only, training pairs en-de/es/zh):
  L_eq = || Delta M(c_i) - Delta M(c_i^B) ||_F^2       evaluated behaviourally on held-out languages (write en, read B).
Port to target b': freeze the rule; fit P_b' by ridge regression of span-pooled target residuals onto the source's
canonical keys and Q_b' by functional matching of next-token log-prob shifts under a fixed bank of 8 injected random
rank-1 M's, both on 2k x 512-token FineWeb-Edu sequences containing no task family.
```

**Wave-3 identification repair (the single change applied in this spec; union of both judges' highest-impact fix).**

(a) *Matched placebo.* The teacher's own shuffled-label episodes enter the distillation stream of every rule (R_theta,
R_GD, the label-trained sibling, and the random-theta P/Q fit) at a fixed 2:1 gold-to-shuffled ratio; on a shuffled
episode the KL target is p_T under the shuffled context. Shuffled writes are therefore in-distribution for all rules.
A TR-fidelity CI gate runs before any r_TL is admitted: for each arm and eligible held-out family,
|Delta_shuf(rule) - Delta_shuf(T)| ≤ 0.05, where Delta_shuf(rule) = acc(rule, shuffled writes, no context) - acc(calibrated
zero-shot) and Delta_shuf(T) = acc(T, random-label 8-shot) - acc(T, calibrated zero-shot). A family that fails the gate
for an arm has that arm's r_TL marked inadmissible (reported, not averaged).

(b) *Teacher fidelity is the primary endpoint.* On held-out families H, per base b and family F:
F(rule; b, F) = agreement rate between the rule's argmax prediction (no demonstrations in the window) and the teacher's
own 8-shot argmax prediction on the same query and the same (gold or shuffled) episode, minus the agreement obtained with
M = 0. Secondary fidelity endpoints: error agreement (Cohen's kappa restricted to queries the teacher gets wrong),
per-step accuracy-curve distance (L1 over i = 1..8), and order-sensitivity agreement (Spearman between rule and teacher
accuracy across three demonstration permutations). A rule that beats R_GD on accuracy but not on fidelity is reported as
"a better associative rule", not as the teacher's update.

(c) *Per-base eligibility.* The eligibility gate G_TL(b, F) ≥ 10 points with the 95% CI excluding 5 on at least 400
queries is applied on every base b, including every recurrent target, not only on the source; ported fidelity and r_TL
use per-base denominators and per-base eligible sets.

(d) *Rescope.* claim_scope is portability-protocol. No architecture-causal claim is made; the from-scratch matched arm is
deferred to a separate contract that would only be opened if the protocol result is positive.

(e) *Genuine read-path counterfactual.* The adjacent-layer site-type factor on the startlux hybrid (sets A and G are
neighbouring layers on one residual stream with softmax attention downstream of both) is dropped. It is replaced by a
downstream-attention read-path ablation: for probes read at after-GDN sites, every attention sublayer downstream of the
injection has its output patched to its M = 0 value from the paired no-write pass, so the injection can propagate only
through GDN and MLP sublayers. Fidelity with and without the patch is compared. The six pure-recurrent targets, which
contain no softmax anywhere, remain the primary cross-operator test.

(f) *Priors.* Items 8-12 of Closest Prior Work are added and discriminated.

**Falsifiable predictions (pre-registered).**

- P1 (identifiability, Stage B, source only, held-out families): F(R_theta) - F(R_GD) ≥ 0.10 with the paired
  family-clustered 95% bootstrap CI excluding 0; F(R_theta) exceeds the label-trained sibling by ≥ 0.05; F(random-theta
  with fitted P/Q) ≤ 0.5 x F(R_theta); every arm passes the TR-fidelity gate on at least 8 eligible families. Secondary:
  mean r_TL(R_theta) ≥ 0.60 and r_TL(R_theta) - r_TL(R_GD) ≥ 0.15 on admitted families.
- P2 (port, Stage C): on at least 4 of the 6 pure-recurrent targets, ported F(R_theta) exceeds ported F(R_GD) by ≥ 0.05
  with per-base eligibility; the same-family port transformer-1.3B to transformer-2.7B retains ≥ 0.6 of the source F;
  under the downstream-attention patch on the hybrid, after-GDN fidelity retains ≥ 0.7 of its unpatched value (if ≤ 0.5,
  downstream softmax carried the readout).
- P3 (content vs surface, Stage D, held-out languages sw/hi/th/ar/tr/id/vi/ja): with lambda_eq = 0 the write-en/read-B
  fidelity gap of R_theta is within 0.10 of R_GD's gap (encoder invariance explains it); with lambda_eq trained on
  en-de/es/zh only, the held-out-language gap shrinks by ≥ 0.15 at ≤ 0.05 monolingual fidelity cost; R_GD with lambda_eq
  is also run so that the shrinkage is not attributable to the co-fitted P alone. If the lambda_eq = 0 gap is already
  ≤ 0.05, P3 is declared null.
- P4 (dynamics signature, held-out episodes): the effective step s_i = eta_i ||u_i|| ||w_i|| decays with i (Spearman
  rho ≤ -0.5 over i = 1..8) and on key-collision episodes the emitted rho_i for the colliding direction falls below 0.7,
  a content-conditional forgetting policy that constant-rho R_GD cannot express.

**Kill criteria (falsifiers).** K1: F(R_theta) - F(R_GD) below 0.05 or CI including 0 on the source → at this interface
and on these eligible families the teacher's content-dependent update is behaviourally indistinguishable from
preconditioned GD; report as a bounded behavioural result (not as a general confirmation, since binding-dominated
eligible sets make associative rules the natural solution) and stop. K2: fewer than 8 held-out families pass the
eligibility gate on the source → unmeasurable at this scale; report and stop. K3: ported F(R_theta) ≤ ported F(R_GD) on
every pure-recurrent target → the distilled rule does not port across operators; K3b: the downstream-attention patch
removes ≥ 0.5 of after-GDN fidelity on the hybrid → the readout depended on softmax. K4: any audit failure (two-forward-
pass prefix-invariance audit not identical at fp32 tolerance; a poisoned demonstration persisting after the declared
reset; random-theta ≥ 0.5 x R_theta; any arm failing the TR-fidelity gate on more than half of the eligible families).
K5: lambda_eq costs more than 0.10 monolingual fidelity or fails to shrink the held-out-language gap. K6 (collapse):
R_theta ties the label-trained sibling within 0.05 → report as Fast Weight Layers / SRWM instance.

**Strongest counter-argument (devil's advocate).** The distilled rule's function class strictly contains R_GD, so any
non-GD structure in the teacher's behaviour, including surface biases such as majority-label and recency effects, will
register as a fidelity win without demonstrating that the rule has captured a *content* update rather than the
teacher's biases. The fidelity endpoint answers half of this: matching the teacher's errors and order sensitivity is
evidence of matching the HOW including its biases, which is what a portable rule should carry. The other half is the
pre-registered ceiling: if the eligible held-out set is dominated by exact-recall binding tasks, R_GD is at capacity and
a rank-8 M with 8 pairs is the associative-recall solution, so a K1 tie is expected there and is not an interesting
negative. The mitigation is to report fidelity per family class (binding, function induction, classification) and to
require the win on the function-induction class specifically.

**What's missing.** A from-scratch matched arm (deferred by the rescope); an independent replication of the fla-hub
ladder's corpus identity for delta_net and mamba (inferred from the DeltaNet paper, not card-stated); a Stage-A model
loop actually executed; and a measured, not assumed, MFU on the node.

## Cheapest Decisive Pilot

Public data only; General Translation data is an optional upgrade. Substrate revisions are listed in the direction file
and in the contract's blocked_by list; none of the 1.3B ladder checkpoints is yet in the model registry.

**Stage A (CPU, fp64, 0 GPU-h): algebra, causality and regime doctors.** (a) Synthetic ICL in the finite-task-prior regime
of Raventós et al. (C16), where the 2-layer transformer's implicit predictor is dMMSE rather than ridge/GD: distil
R_theta with a 16-d state and check that it tracks dMMSE while R_GD tracks ridge; kill before any GPU if R_theta cannot
beat R_GD here. (b) Prefix-invariance and probe-absence audits on the two-pass code path. (c) TR-fidelity gate code path
on synthetic gold-plus-shuffled episodes. (d) Tokenizer doctor asserting piece-id identity across the fla-hub 1.3B-100B
and startlux tokenizers (C02, C03). (e) Rank/algebra doctor for Pi_8 and the P/Q factorisation. (f) Loader smoke on the
registered smollm2-135m, qwen3-0.6b-base and mamba-130m-hf ids; a 10-minute throughput smoke on one GPU that measures
MFU for a hooked eager pass.

**Stage B (≤ 4 GPU-h including reserve): identifiability on the source; the kill screen.** Source
fla-hub/transformer-1.3B-100B (C01). B0 denominator audit (gold / random-label / calibrated zero-shot) on 14 candidate
families. B1 distillation runs of 6k episodes x 2 epochs each, 2:1 gold-to-shuffled: R_theta x3 seeds, R_GD x3,
random-theta x2, label-trained sibling x2. B2 special-case derived rules (delta, Kaczmarz, OSDN-diagonal, Falcon, FAAST)
on R_GD's fitted interface with a 16-point scalar grid on D. B3 held-out evaluation: fidelity endpoints, TR-fidelity
gate, r_TL, per-step curves, three demonstration permutations on 200 queries per family. Stop if K1, K2 or K6 fires.

**Stage C (≤ 2.5 GPU-h, gated on B): port on the iso-ladder.** Targets fla-hub/{delta_net, gla, retnet, hgrn2, gsa,
mamba}-1.3B-100B (C02), sites strictly after recurrent sublayers; same-family reference fla-hub/transformer-2.7B-100B;
downstream-attention read-path ablation inside startlux gdn-1.3b-isp-hybrid-3to1-50b (C03). Per-base G_TL gate on every
target (C0). Label-free P/Q on FineWeb-Edu sample-10BT.

**Stage D (≤ 2.5 GPU-h, gated on B): content vs surface inside one multilingual base.** Qwen/Qwen3-1.7B-Base (C11);
distil R_theta and R_GD each with lambda_eq in {0, lambda} on SIB-200 plus MASSIVE English demonstrations and
en-de/es/zh parallel pairs (C08, C09); evaluate write-en/read-B on held-out languages and on the held-out dataset (train
L_eq on SIB-200 topics, test on MASSIVE scenarios, and vice versa).

**Stage E (≤ 3.5 GPU-h, gated on C): independent-ladder replication.** Pile 300B triplet (C04):
state-spaces/transformerpp-2.7b (source) to mamba2-2.7b and mamba2attn-2.7b (second read-path ablation), with
EleutherAI/pythia-2.8b as the same-family reference. Needs pinned mamba_ssm and causal-conv1d wheels.

**Budget ledger (C05 anchor; 25% MFU = 247 TFLOPS per GPU assumed; 25% reserve per stage; C24).** FLOPs per token:
teacher forward 2N, frozen-base forward plus activation backward 4N, evaluation forward 2N; episode = 384
demonstration tokens plus 8 steps x 8 probes x 28 tokens = 2,176 tokens.

| Stage | Item | FLOPs | GPU-h |
|---|---|---|---|
| B0 | 14 fam x 3 cond x 400 q x 700 tok x 2N (1.3e9) | 3.1e16 | 0.035 |
| B1 | 10 runs x 12k episode-passes x 2,176 tok x 6N | 10 x 2.0e17 | 2.30 |
| B2 | 5 rules x 16 grid x 6 fam x 200 q x 500 tok x 2N | 1.2e17 | 0.13 |
| B3 | 23 passes x 8 fam x 400 q x 600 tok x 2N plus 3 permutations x 8 fam x 200 q | 1.3e17 | 0.14 |
| B total | x1.25 reserve | | 3.3 |
| C0 | per-base gate: 7 bases x 8 fam x 3 cond x 400 q x 700 tok x 2N | 1.3e17 | 0.14 |
| C-align | 72 fits (9 target-configs x 8 rule-seeds) x 1.05e6 tok x (4N_t + 2N_s) | 7.0e17 | 0.79 |
| C-eval | 10 target-configs x 19 passes x 8 fam x 400 q x 500 tok x 2N plus patched hybrid passes | 8.8e17 | 0.98 |
| C total | x1.25 | | 2.4 |
| D0 | 2 sets x 9 langs x 3 cond x 400 q x 600 tok x 2N (1.7e9) | 4.4e16 | 0.05 |
| D1 | 8 runs (R_theta and R_GD x lambda_eq in {0, lambda} x 2 seeds) x 12k passes x 2,176 tok x 6N (1.7e9) | 8 x 2.7e17 | 2.40 |
| D2 | 8 x 2 x 2 x 9 x 300 q x 500 tok x 2N | 1.5e17 | 0.16 |
| D total | x1.25 | | 3.3 |
| E-distil | 4 runs x 12k passes x 2,176 tok x 6N (2.7e9) | 4 x 4.2e17 | 1.90 |
| E-align + eval | 16 fits + 4 configs x 11 passes | 6.5e17 | 0.73 |
| E total | x1.25 | | 3.3 |
| Program | | | 12.3 of 16 |

Decisive pilot (A + B + C) ≤ 6 GPU-h; kill screen (A + B) ≤ 4. The wave-3 changes add about 0.4 GPU-h to B and C (the
per-base gate, the permutations and the patched passes) and 0.8 GPU-h to D (R_GD with lambda_eq); the program stays
inside the 16 GPU-h envelope with 3.7 GPU-h of slack. If the Stage-A throughput smoke measures MFU below 12.5%, halve B1
and D1 episodes (3k x 2) and drop Stage E before touching C or D.

## Controls, Baselines, and Ablations

- Native ICL with gold demonstrations; native ICL with shuffled labels (task-recognition-only reference; C07, Pan et
  al., Min et al.); contextual-calibration zero-shot as the zero-shot reference; held-out formats and task categories.
- R_GD superset at the same interface, distillation loss, episode mix, P/Q co-fitting and compute, containing delta,
  Kaczmarz, OSDN-diagonal, Falcon and FAAST as special cases, each also run with a scalar grid on R_GD's fitted interface.
  This is the decisive control.
- Label-trained sibling rule at the same interface (cross-entropy on labels, same gold-plus-shuffled episodes), Stage B
  head-to-head; separates "distilled HOW" from "any learned rule".
- Random-theta reservoir with fitted P/Q (0.5x kill; randomly initialised transformers already do in-context recall).
- Same-family ports (transformer-1.3B to transformer-2.7B; transformerpp-2.7b to pythia-2.8b) as port-fidelity upper
  references.
- Downstream-attention read-path ablation on startlux gdn-1.3b hybrid and mamba2attn-2.7b (wave-3 replacement for the
  inert adjacent-layer site factor).
- Iso-corpus / iso-tokenizer / iso-token-budget ladders by construction (fla-hub 1.3B-100B; Pile 2.7B triplet); the two
  ladders differ in corpus, tokenizer and recipe, so agreement across them is the replication test.
- No-update (M = 0) code-path check (inert by construction: the read adds exactly 0).
- Encoder-invariance baseline for P3: R_GD with lambda_eq = 0; R_GD with lambda_eq also run so P shrinkage is not
  attributed to the rule by default; held-out languages and held-out dataset.
- Audits on every arm: two-forward-pass prefix-invariance CI gate, TR-fidelity CI gate, hash-chained write log, reset
  attestation, single-adversarial-demonstration poisoning probe with persistence check across reset.
- Named but unbudgeted upper references for same-family ports only: MentorPulse live mentor
  (https://arxiv.org/abs/2608.20927), Engram reader transfer (https://arxiv.org/abs/2608.17050), KV translation
  (https://arxiv.org/abs/2608.30963).

## Evaluation, Statistics, and Leakage Checks

**Endpoints.** Primary: F(R_theta) - F(R_GD) on the source over eligible held-out families (defined in Mechanism (b)).
Secondary, Holm-corrected as one family: r_TL gap on admitted families; error-agreement kappa; per-step curve distance;
order-sensitivity agreement; per-target ported fidelity; hybrid patched-vs-unpatched ratio; Stage D gap shrinkage.

**Minimum worthwhile effect.** 0.10 fidelity points on the primary endpoint (a tenth of the held-out queries whose
teacher-matching prediction is explained by the distilled rule and not by GD); 0.05 on the per-target port and sibling
comparisons. Below 0.10 on the source the rule is not worth porting.

**Noise estimate (assumed; no pilot exists).** Query-sampling noise on a paired 400-query agreement-rate difference about
0.035 (binomial); seed-to-seed distillation noise 0.06 (unknown, assumed); family heterogeneity of the true effect 0.08
(unknown, assumed). Under these assumptions the family-level SD of the mean difference is 0.089 at 3 seeds, giving
d_z about 1.1 at a 0.10 effect.

**Seed and sample count (simulation, C25).** A 4,000-draw simulation of the family-clustered one-sample test on
family-level means (script: fam_eff = delta + N(0, 0.08^2); obs = fam_eff + N(0, 0.06^2) + N(0, 0.035^2) per seed;
t-test on family means at alpha 0.05 one-directional) gives power 0.77 at a 0.10 effect with 8 eligible families and 3
seeds, 0.88 with 10 families, 0.98 at a 0.15 effect with 8 families; Type-I 0.03 under the null. Family count dominates:
moving from 2 to 3 seeds adds at most 0.04 power. The pre-registered rule is therefore: at least 8 eligible held-out
families (else K2), 3 seeds on the main arms (42, 43, 44), 2 seeds on secondary arms, and the power sensitivity table is
reported alongside the CI rather than a single number. A sensitivity analysis over the assumed SDs (0.5x to 2x) is part
of the analysis script.

**Reporting standard.** Every comparison reports the paired effect with a family-clustered bootstrap 95% CI, per-family
and per-seed effects, the paired d_z, and exact bootstrap p-values; assumption checks (normality of family-level
differences, absence of one dominating family via leave-one-family-out) are reported; non-significant secondary results
are reported in full; no observed-power statements.

**Randomization and blocking.** Seeds 42/43/44 are assigned to (rule, base) cells through a fixed permutation table
committed before enablement; episode order and shuffled-label permutations are drawn from the seed; evaluation queries
are identical across arms (paired design). Arm scheduling on the node is round-robin across arms within each stage, one
GPU per job, so drift in node state is blocked across arms rather than confounded with one arm. Arm labels are hashed
in the evaluation logs and unblinded only after the analysis script's hash is recorded.

**Leakage checks.** Distillation families D and held-out families H are disjoint by task identity and by format template
(separator, template, label space); held-out queries are n-gram-checked against every demonstration in any training
episode; FineWeb-Edu alignment sequences are filtered for held-out task strings; SIB-200 and MASSIVE held-out languages
never appear in L_eq training; per-family results are always reported, never only the macro mean; the sealed test
manifest (task list, query ids, permutations) is hashed before any GPU run.

## Compute and Reproducibility

Discovery image (exists on fal-h100-01, verified 2026-09-01; C23): immutable image
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3` (image ID
sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2; labels
org.opencontainers.image.revision=581ded8df71564b0212d8af5dcd401257aa6a28f,
source-tree-sha256=2d960d1a5cf6fd64cdd0baba0a2c752ad6216b8443d741cb7deef9e07d031322,
runtime-profile=architecture-source-overlay; created 2026-08-16; CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0,
accelerate, triton). This image contains no fla, peft, flash-attn or vllm. The pilot therefore needs a rebuilt image
from the new code with flash-linear-attention 0.5.2 (commit 9c8e42e762fce087c27b673af4922795d9edb85e) pinned, plus
mamba_ssm and causal-conv1d wheels for Stage E only, re-pinned by digest before enablement; the digest above is the
discovery image, not the pilot image.

Slurm submission (single node, Docker lane, no Pyxis):

```bash
uv run python scripts/submit_docker_research_job.py experiments/architectures/icl-rule-distillation-port.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/architectures/icl-rule-distillation-port.yaml
# the submit script wraps: sbatch infra/slurm/host-single-node/docker-research.sbatch
```

Machine fields: `seeds: [42, 43, 44]`; `gpu_hours: 16` (envelope; decisive pilot 6; program 12.3); `gpus: 1` per job.

Checkpoints every 10 minutes to /home/kevin/cotcodec-runs/icl-rule-distillation-port/(stage)/(arm)/(seed)/ with atomic
rename; SIGUSR1 triggers a checkpoint and a clean exit; every truncated-BPTT run must pass the fresh-job continuation
equivalence test (resume from checkpoint reproduces the uninterrupted loss trajectory at fp32 tolerance) before its
results are admitted. Artifact paths: write logs (hash-chained JSONL), reset attestations, per-query prediction tables
for rule and teacher, P/Q fits, ledgers of tokens, FLOPs and wall time per arm, and the sealed test manifest hash, all
below the run directory and mirrored into evidence/icl-rule-distillation-port/. Preemption: jobs are resumable from the
last checkpoint by a fresh sbatch submission; no job exceeds 4 wall-hours. Cost ceiling: 16 GPU-h on the owned node
(no marginal cloud cost); dollars=40 covers tool and API costs only. The publication lane (cgroup-v2 Slurm plus Pyxis)
is not available on this host; results from the Docker lane are discovery-grade.

## Safety, Data Rights, and Monitorability

**Monitorability.** A base-independent 64-d state lets one probe read the memory on every base, which is a
monitorability gain over per-model opaque fast weights; but hidden state replaces visible demonstrations. The protocol
therefore logs every write (rho_i, eta_i, effective step, key/value hashes) in a hash-chained JSONL, attests every reset,
and runs a single-adversarial-demonstration poisoning probe with a persistence check across the declared reset. No
hidden chain-of-thought is stored; only framework-visible records.

**Data rights.** Function Vectors MIT; Super-NaturalInstructions Apache-2.0 for task files with per-task instance
licenses recorded; SIB-200 CC-BY-SA-4.0 (share-alike applies only if derived data were redistributed; none is);
MASSIVE CC-BY-4.0 with attribution; FineWeb-Edu ODC-By 1.0; fla-hub transformer/gla/retnet/hgrn2/gsa MIT; fla-hub
delta_net and mamba cards state no license and are discovery-only until confirmed (the registered delta-net-1.3b-8k
carries the same blocker, C21); startlux Apache-2.0; state-spaces and Pythia Apache-2.0; Qwen3 Apache-2.0; Moonshot MIT.
The General Translation parallel demonstration sets are an optional upgrade only: their license for research use is
unknown at this time and must be cleared in writing before any use; the pilot uses no GT data. IP: NVIDIA
US20260105282A1 (gated delta networks, pending; C22) is flagged; the sidecar rule is not a kernel-level delta-rule
contribution and touches no GDN kernel.

**Red lines (stop the study).** A poisoned demonstration whose effect persists after the declared reset; any read that
depends on a probe's own tokens (prefix-invariance audit failure); any refusal or safety regression above 5 points on
the base's own safety suite when the sidecar is attached; more than 10% degradation of tool-argument fidelity on the
in-repo tool-schema stress set; any cross-episode state bleed.

### Integrity gate

Protocol followed: the seven AI-research failure modes (scratchpad/ext/ars/academic-pipeline/references/
ai_research_failure_modes.md).

- Mode 1, implementation bug passing self-review: CLEAR by design, not by evidence — Stage A doctors (dMMSE regime,
  prefix invariance, rank/algebra, TR-gate code path) must pass with exit code 0 and saved logs before any GPU run;
  suspiciously round effects or identical CIs across arms are flagged in the analysis script. Status today:
  INSUFFICIENT EVIDENCE (no code executed).
- Mode 2, hallucinated citation: every URL in this proposal was opened by a gauntlet cell at abstract or HTML level;
  status per claim in the Claim registry; Semantic Scholar batch verification was not possible (429).
- Mode 3, hallucinated experimental result: no experimental result is reported anywhere in this proposal; all numbers
  are sources, budgets or pre-registered thresholds. Any future number must point to a run directory and manifest hash.
- Mode 4, shortcut reliance: the matched placebo (a) and the fidelity endpoint (b) exist precisely because the wave-2
  endpoint could be won by a shortcut (nonlinear rule on off-manifold shuffled inputs); the random-theta reservoir and
  the label-trained sibling rule out "any associative rule" and "any learned rule"; family-class reporting rules out
  binding-only wins.
- Mode 5, bug reframed as insight: P4's dynamics signature is the most seductive result; it is admitted only if it
  replicates across the two ladders and survives the leave-one-family-out check. "Surprising" results are re-run from a
  fresh environment before reporting.
- Mode 6, methodology fabrication: every hyperparameter in this proposal must match the run manifest that the sbatch
  wrapper hashes; the Methods of any write-up are generated from the manifest, not written free-hand.
- Mode 7, frame-lock: the wave-3 rescope to portability-protocol is itself a frame correction; the pre-registered
  collapse (K6) and the bounded K1 reading prevent the study from being locked into an "architecture" story it cannot
  support. If Stage B yields K1, the study stops rather than escalating.

## Negative-Result Value

K1 gives a bounded behavioural result on an iso-ladder at 1.3B: at a 64-d rank-8 interface, and on the eligible
held-out families, the transformer's content-dependent in-context update is not distinguishable from preconditioned GD
by fidelity to its own predictions and errors. Reported per family class, it says which task classes admit a GD
description and which do not, which is a quantitative input to the ICL-as-GD literature and empties Direction 16's
premise for a few GPU-hours. K2 gives a measured floor: at 1.3B-1.7B, label-dependent ICL is confined to binding and
function-induction families. K3 gives the first cross-family behavioural measurement of in-context update portability
(GD emulation versus online GD versus Bayes filter), with the read-path ablation saying whether softmax carried it. A P3
null shows that the frozen encoder's language invariance alone explains cross-lingual memory readout, closing the
ttt-fastweights G4 question cheaply. K6 turns the study into a clean replication of Fast Weight Layers on modern bases.

**Strongest counter-argument to the whole direction.** Even a positive result may be "a better associative rule at a
convenient interface" rather than "the transformer's update": nothing but fidelity on teacher-wrong queries and order
sensitivity separates the two, and both are noisy at 400 queries. **What's missing** to close that gap is a
from-scratch matched arm in which the same rule is trained jointly with a small base, which the rescope defers, and a
larger held-out family pool, which 1.3B bases do not offer.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | Cell notes: research/gauntlet/2026-09-01-frontier/wave2/icl-rule-distillation-port.md (repair), wave2-result.json (three refuter votes with 63 evidence URLs, blind discrimination, two judges), wave1-ledger.md; sweep notes learned-update-rules.md, ttt-fastweights.md, adapter-portability.md, seq-operators.md, synthesis.md and the four verify-*.md notes | Snapshot every primary URL with HTTP 200 and SHA-256 into the evidence bundle |
| Citation | PASS-candidate | Every number carries a URL and a status in the Claim registry (27 rows); first-party items are marked; protocol claim_verification_protocol.md followed | Independent line-by-line citation audit; re-open C07, C13 tables |
| Novelty | PASS-candidate | Wave-2 novelty refuter did not refute (0.6); blind discrimination different mechanism (0.88); five judge-named priors added and discriminated; collision risk high | Signed provider-distinct novelty review after proposal freeze; Semantic Scholar and OpenReview body search when reachable |
| Design | PASS-candidate | Contract experiments/architectures/icl-rule-distillation-port.yaml passes validate_architecture_experiments.py; matched placebo, fidelity primary endpoint, per-base gate, read-path ablation, six falsifiers, power simulation; protocols experimental-design/SKILL.md, statistical-power/SKILL.md, statistical_reporting_standards.md, devils_advocate_agent.md followed | Implement Stage A doctors and the analysis script; freeze its hash |
| Compute | FAIL | No real model loop executed; no pilot image with fla 0.5.2 built or digest-pinned; no container smoke run; no Slurm dry-run attested; MFU assumed, not measured | Rebuild and pin the image; run the Stage-A throughput smoke and the sbatch dry-run; attest in the bundle |
| Safety | PASS-candidate | Monitorability (hash-chained write log, reset attestation, poisoning probe), data rights (all licenses listed; GT data license unknown and excluded; delta_net/mamba discovery-only), red lines, and the seven-mode integrity gate are specified | Runtime isolation and poisoning-probe evidence from a real run |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude (internal preliminary judge 1, NOT provider-distinct, unsigned) | run_id=wave2-judge-1 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json

Reviewer B: FAIL | provider=anthropic | model=claude (internal preliminary judge 2, NOT provider-distinct, unsigned) | run_id=wave2-judge-2 | artifact=research/gauntlet/2026-09-01-frontier/wave2-result.json

Both reviews are internal wave-2 judge scorecards from the same provider, unsigned and without a protected trust root.
They are recorded for traceability only; the Gauntlet requires two provider-distinct, Ed25519-signed reviews, so the
accepted score is capped at 89 and the proposal is NOT pilot-ready regardless of the scorecard below.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 7 | 7 | Rule-as-object framing fits G5/G2/G6/G7; Kevin advantage partial (public substrate) |
| Primary-source evidence | 7 | 8 | 27-row claim registry; several table-level numbers not re-opened this wave (C07, C13) |
| Defensible novelty delta | 5 | 5 | Recombination with high collision risk; five judge-named priors now discriminated; unsigned |
| Mechanism and falsifiability | 7 | 7 | Six kill criteria and four predictions; K1 reading bounded per judges |
| Controls and causal identification | 3 | 3 | Wave-2 defect: unmatched placebo, no fidelity endpoint, per-source-only gate, inert site factor, architecture-causal label; all addressed in wave 3 but not yet re-judged |
| Evaluation and statistics | 6 | 6 | Power now simulated (0.77 at 8 families); noise SDs assumed, not measured |
| Feasibility and information per GPU-hour | 7 | 7 | Ledger recomputed by the feasibility refuter; MFU assumed; program 12.3 of 16 GPU-h |
| Reproducibility and artifact contract | 6 | 6 | Discovery image real but lacks fla; pilot image not built; no evidence bundle |
| Safety, data rights, and monitorability | 8 | 7 | Write log, reset attestation, poisoning probe, licenses; GT data license unknown and excluded |
| Independent adversarial review quality | 6 | 6 | Internal, same-provider, unsigned judges only |
| **Total** | **62** | **62** | Lower total is authoritative; wave-2 judged total before the wave-3 repair; accepted Gauntlet score is 0 until the bundle exists |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | Killed before judging: identification REFUTED (0.8; predicted effects not attributable to the transformer's distilled update; Pythia-160m gain within noise; derived rules undertuned; cross-operator sites on attention layers) and feasibility REFUTED (0.8; no data named; budget not credible); novelty not refuted (0.6). See research/gauntlet/2026-09-01-frontier/wave1-ledger.md row 5 | Repair owner rebuilt endpoint (r_TL), scale (1.3B iso-ladders), substrates, controls (R_GD superset, sibling, reservoir), data plan and FLOP ledger; kept the rule-as-object delta | Entered wave 2 |
| 2 | 62 | Primary endpoint r_TL not a matched placebo across R_theta (nonlinear, trained only on gold) and R_GD (linear in e_i): the P1 gap could be produced with zero content information; no TR-fidelity gate, no teacher-fidelity endpoint; eligibility gate on the source only; architecture-causal label without a from-scratch arm; inert adjacent-layer site factor | Judged only; both judges 62/62, identification 3/10; blind discrimination: different mechanism (0.88), prior does not dominate | Ranked 1 of wave 2; passed to spec with one repair allowed |
| 3 | 62 | Same as wave 2 (identification) | Applied the union of both judges' highest-impact fix as one identification repair: (a) teacher shuffled-label episodes in every rule's distillation stream plus a 0.05 TR-fidelity CI gate; (b) teacher fidelity on held-out families as the primary endpoint with error-agreement, per-step and order-sensitivity secondaries; (c) per-base eligibility gate; (d) claim rescoped to portability-protocol; (e) inert site factor replaced by a downstream-attention read-path ablation; (f) Jeong, FAAST, Sleep, Cross-model Control and ICLCA added and discriminated. Ledger updated (+1.2 GPU-h, program 12.3) | Not re-judged; score unchanged pending wave-4 review |

The accepted score remains zero until the hashed evidence bundle at evidence/icl-rule-distillation-port/bundle.json,
the protected trust root, two signed provider-distinct reviews, the rebuilt and digest-pinned pilot image, the Stage-A
container smoke and Slurm dry-run attestations, and the hash-chained audit JSONL exist. A prose proposal cannot score
itself upward; every PASS-candidate above is a claim about what the evidence bundle must show, not a PASS.
