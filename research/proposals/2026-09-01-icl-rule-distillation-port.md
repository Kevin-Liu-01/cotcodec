# Research Direction: Portable In-Context Write-Rule Distillation (icl-rule-distillation-port)

**Status:** draft
**Owner:** Kevin Liu
**Source cutoff:** 2026-09-01
**Coverage limits:** WebSearch budget exhausted mid-sweep; arXiv API, Semantic Scholar and Jina blocked from the Mac (HTTP 429/401), arXiv reached only through the H100-host relay and abstract pages; OpenReview note bodies unreadable; no ACL Anthology, Google Scholar, patent or Chinese-venue search beyond the 2026-09-01 verification pass; ICLR 2027 submissions invisible; nothing executed on the H100 node or on Tinker; no parallel corpus exists in the repository
**Budgets:** queries=80; wall_minutes=600; tokens=900000; dollars=40; waves=6; gpu_hours=16
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/icl-rule-distillation-port/bundle.json

## Claim and Research Question

**Claim (portability-protocol scope; rescoped in wave 3, identification hardened in wave 4).** The content-dependent
part of a frozen softmax transformer's in-context update can be distilled into an explicit rank-8 fast-weight write rule
at a canonical 64-d interface such that, on held-out task families the distillation loss never sees, the rule reproduces
the teacher's own 8-shot predictions (teacher fidelity) more faithfully than an iso-parameter gradient-form rule (the same
MLP width and parameter count, update direction constrained to the key, w_i = k_i) trained at the same interface, on the
same gold-plus-shuffled-label episode mix, with the same hyperparameter-search budget and compute, and that the win is
carried by the free write direction (clamping w_i to k_i in the trained rule costs fidelity); and that the same frozen
rule, attached through label-free maps strictly after recurrent sublayers of licensed pure-recurrent bases trained on the
same corpus, tokenizer and token budget, keeps a measurable fraction of that fidelity with no demonstrations in the window.

**Research question.** Is the object worth porting between sequence-operator families the *write rule* (how a context
item becomes a state update), rather than weights (Generative Adapter, Doc-to-LoRA) or state (Cache-to-Cache, KV
translation)? Concretely: (i) does behavioural distillation of a transformer's in-context update produce a rule that is
more than a gradient-form (key-directed) update at a low-rank interface and at matched capacity, judged by fidelity to
the teacher's predictions and errors rather than by accuracy alone; (ii) does that rule survive a label-free port to DeltaNet, GLA, RetNet, HGRN2,
GSA and Mamba bases that have no KV cache to receive state; (iii) do its writes carry content beyond the frozen
encoder's own language invariance (write in English, read in a held-out language).

**What this is not.** It is not an architecture-causal claim: every arm is a frozen pretrained retrofit and no matched
from-scratch arm is budgeted (wave-3 rescope, both judges). It is not a new kernel, a new memory product, or a claim
about Mamba specifically. The pre-registered collapse case is explicit: if the distilled rule ties a sibling rule distilled
by the same KL objective from a different transformer teacher at the same interface, the fidelity is not specific to the
source teacher and the result is reported as a Fast Weight Layers / SRWM-class learned rule, not as the teacher's update.

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
SR-TTT-derived causality doctors this protocol needs; (e) the residual interface (rank-8 64x64 state at four sites with
base-specific rank-8 P/Q) is Direction 16's own (directions/16-portable-learning-dynamics.md,
experiments/architectures/portable-sidecar-update.yaml), reused deliberately so that a result here is directly a test of
that direction's premise; the interface is not part of the claimed delta.

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
- Derived rules used as R_lin's special cases on the secondary grid: Kaczmarz normalisation — https://arxiv.org/abs/2605.08587;
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
- ICL-as-GD lineage that defines the null (wave-4 additions; abstract pages opened 2026-09-01/02): von Oswald et al.
  2022 — https://arxiv.org/abs/2212.07677 (linear self-attention implements a GD step on regression); Akyürek et al.
  2022 — https://arxiv.org/abs/2211.15661 (ICL on linear regression implements GD, ridge and Bayesian estimators); Dai
  et al. 2022 — https://arxiv.org/abs/2212.10559 (attention has a dual form of GD; ICL as implicit finetuning); von
  Oswald et al. 2023, mesa-optimization — https://arxiv.org/abs/2309.05858; Shen et al. 2023 —
  https://arxiv.org/abs/2310.08540 (negative evidence at scale: ICL and GD differ in order sensitivity and in how they
  modify the output distribution; the origin of this proposal's order-sensitivity and error-agreement secondaries, C29).
- Write-rule taxonomies that name the cells of the gradient-form ladder: MIRAS — https://arxiv.org/abs/2504.13173
  (memory type, attentional bias, retention gate, learning algorithm); Test-time regression —
  https://arxiv.org/abs/2501.12352 (regression weights, regressor class, optimiser); delta-rule fast weight programmers,
  Schlag et al. 2021 — https://arxiv.org/abs/2102.11174 (origin of the delta-rule special case in R_lin).
- Context distillation, the objective family the distillation loss belongs to: Snell et al. 2022 —
  https://arxiv.org/abs/2209.15189 (a student without the context matches the teacher's outputs with the context).
  Askell et al. 2021 — https://arxiv.org/abs/2112.00861 is credited by wave-3 Reviewer B with the earlier use; its
  abstract page does not mention the technique and its body was not opened, so the attribution is recorded, not verified.
- In-repo prior with the identical interface: directions/16-portable-learning-dynamics.md and
  experiments/architectures/portable-sidecar-update.yaml (rank-8 factorised 64x64 state at four evenly spaced layers;
  task-blind rank-8 base projections as the only base-specific parameters; C30).

First-party versus independent: every 2026 item above is a first-party preprint or model card; peer-reviewed status is
confirmed only for Function Vectors (ICLR 2024), Pan et al. (Findings of EMNLP 2023), Min et al. (EMNLP 2022), and
Raventós et al. (NeurIPS 2023). The wave-4 additions were opened at abstract level only; their peer-review venues were
not recorded by this cell and they carry no quantitative claim here except C29. No number below was reproduced on
hardware by this cell.

### Claim registry

Protocol followed: the ARS claim verification protocol (scratchpad/ext/ars/academic-pipeline/references/
claim_verification_protocol.md, Phase E1-E3). Status vocabulary: VERIFIED = the locator was opened by a gauntlet cell on
2026-09-01 and the number matched; FIRST_PARTY = the number is the authors' or vendor's own statement without an
independent replication located; UNVERIFIABLE_ACCESS = the source body could not be reached from this network. Design
thresholds (rank 8, 64-d interface, 8 demonstrations, 2:1 gold-to-shuffled mix, 0.10 fidelity effect, 0.05 TR tolerance,
400 queries, 10-point eligibility floor, 1 percent iso-parameter tolerance, 4-point search grid, 0.05 clamp
co-condition, 3-of-4 and 2-of-4 licensed-port thresholds, 0.10 teacher-disagreement precondition, budget lines) are
pre-registered choices recorded in the contract YAML, not claims about the world, and are therefore not registered as
claims.

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
| C24 | Budget ledger (wave 4): Stage B 5.6, C 2.4, D 3.3, E 3.3 GPU-h; program 14.6 GPU-h; decisive pilot A+B+C 8.0; kill screen A+B 5.6; all at 25% MFU (247 TFLOPS per GPU) with 25% reserve per stage | derived in this proposal from C01, C02, C05, C11 and model parameter counts; wave-2 lines recomputed by the feasibility refuter, wave-4 lines recomputed by this cell (the wave-3 registry row was stale against the ledger, as both wave-3 reviewers noted) | VERIFIED (arithmetic only; no measurement) |
| C25 | Power under the stated noise model with the decision rule "two-sided 95% t-interval on family-level means, lower bound above 0": 0.78 at a 0.10 effect with 8 eligible families and 3 seeds; 0.89 at 10 families; 0.95 at 12; 0.98 at a 0.15 effect with 8 families; one-directional Type-I 0.028 (nominal 0.025). One-sided t at alpha 0.05: power 0.89, Type-I 0.053. Percentile bootstrap on 8 clusters: one-directional Type-I 0.060. Wild-cluster bootstrap, two-sided at 0.05: Type-I 0.054, power 0.76. Seeds 2/3/5: 0.74/0.78/0.80. All SDs at 0.5x / 2x: 0.999 / 0.27 | re-simulated by this cell on 2026-09-02 UTC (4,000 draws, 999 bootstrap resamples, numpy 2.5.2, scipy 1.18.0, seed 42; script scratchpad/wave4-icl/power_sim.py, superseded in wave 5 by harness/icl_rule_distillation.py simulate_attribution_tree_power, whose single-leaf numbers reproduce these and whose full-tree numbers are C38). The wave-3 row reported 0.77 / 0.03 for the t-interval rule but described a one-sided test; wave-3 Reviewer B's 0.89 / 0.053 is the one-sided figure. Both reproduce; the description now matches the rule | VERIFIED (computed; noise SDs remain assumptions) |
| C26 | Wave-1 novelty refuter ran 16 arXiv, 9 DDG, 5 HF and 1 OpenReview queries; wave-2 repair ran 6 hostsearch calls; both judges scored 62/100 | research/gauntlet/2026-09-01-frontier/wave1-ledger.md, wave2-ledger.md, wave2-result.json | VERIFIED (in-repo) |
| C27 | Cross-lingual needle retrieval on softmax transformers is already established (MLNeedle, NAACL 2025; ONERULER) | https://arxiv.org/abs/2408.10151 and https://arxiv.org/abs/2503.01996 | FIRST_PARTY (abstract-level; cited as mandatory baselines by the verification pass) |
| C28 | fla-hub 1.3B-100B licenses re-checked: gla, retnet, hgrn2 and gsa carry license:mit; delta_net and mamba carry no license field and no license tag; revisions unchanged from C02 (delta_net b4dcbbafd4fde802717bdec3008d4aba9cb3a1f8, mamba 49d177eaa9fedd6ff74aab256a02140299df5e99, gla 46b15820a4df269e99aed9d709e017677c15d24b, retnet 7fddefc4d5e196a8d1f076bb7612d54321b3effe, hgrn2 2f413dd9b63591b9b177bbf940942ea7eb70abfe, gsa 1e4ffdae4fcff8c78ec06c47cd2330fcece61200) | https://huggingface.co/api/models/fla-hub/gla-1.3B-100B and the five sibling endpoints (cardData.license, tags, sha) | VERIFIED (this cell, 2026-09-02 01:33 UTC) |
| C29 | Shen et al. 2023: ICL and GD show different sensitivity to demonstration order and modify the output distribution differently; the ICL-GD equivalence is called an open hypothesis | https://arxiv.org/abs/2310.08540 (abstract) | FIRST_PARTY (abstract-level) |
| C30 | Direction 16's contract specifies a rank-8 factorised 64x64 episode state at four evenly spaced layers with task-blind rank-8 base projections as the only base-specific parameters and the update M_(j+1) = Pi_r[rho M + eta u v^T] | directions/16-portable-learning-dynamics.md (Mechanism); experiments/architectures/portable-sidecar-update.yaml (intervention.mechanism) | VERIFIED (in-repo) |
| C31 | Wave-3 reviewer totals 61 (reviewer 1) and 57 (reviewer 2); the lower total 57 is authoritative; score history 62 → 62 → 57 | research/gauntlet/2026-09-01-frontier/wave3-result.json and wave3-ledger.md row for 19-icl-rule-distillation-port | VERIFIED (in-repo) |
| C32 | Parameter counts at the stated widths: R_theta about 1.02e5 (266 inputs, hidden 256, 130 outputs); R_gf hidden about 305 and R_adapt hidden about 293 so that both match R_theta within 1 percent; R_lin about 4.1e3 | arithmetic from the Mechanism block; the Stage-A parameter-count doctor asserts it at run time | VERIFIED (arithmetic only) |
| C33 | PRISMA-style counts: wave 1 — 31 queries (16 arXiv, 9 DDG, 5 HF, 1 OpenReview), records identified and screened not counted at the time; wave 2 — 6 hostsearch calls, 5 records included; wave 4 — 10 records identified from the two wave-3 reviews, 10 abstract pages opened, 9 included, 1 recorded with a caveat | research/gauntlet/2026-09-01-frontier/wave1-ledger.md, wave2-ledger.md, wave3-result.json; this cell's WebFetch log | VERIFIED (in-repo and this cell) for the counted items; UNKNOWN for the wave-1 identified and screened counts |
| C34 | Remaining pilot checkpoint revisions and license fields: transformer-1.3B-100B d6f66f4181fa669e5863327815b44533e3a395e7 (MIT); transformer-2.7B-100B e29b06c913e05827bfb534844267c8d9f673feda (MIT); startlux gdn-1.3b-isp-hybrid-3to1-50b 0ced446e767709a15cbe2004948eac1fdea443db (Apache-2.0); Qwen3-1.7B-Base ea980cb0a6c2ae4b936e82123acc929f1cec04c1 (Apache-2.0); transformerpp-2.7b 15a431b71c40c284138c379d07d4008a28fea397, mamba2-2.7b 99b226cc377d131cccc610ed4346db564f381f1e, mamba2attn-2.7b 5e0f47f0003095d6bdda3ad6fd7f3f41f274accb, pythia-2.8b 2a259cdd96a4beb1cdf467512e3904197345f6a9 (all Apache-2.0) | https://huggingface.co/api/models/fla-hub/transformer-2.7B-100B and the seven sibling endpoints (sha, cardData.license, tags); tabulated in directions/19-icl-rule-distillation-port.md | VERIFIED (this cell, 2026-09-02 01:51 UTC) |
| C35 | Rebuilt pilot image cotcodec-research:999f5583-architecture: image ID sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad, repo digest 127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d, built by Slurm job 353 from commit 999f5583; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0; tilelang being added because fla guards the gated GDN backward on Hopper under Triton below 3.7.1 (fla issue 640); supersedes the discovery image in C23 for pilots | wave-5 spec brief UPDATE (fal-h100-01 docker inspect reported by the orchestrator); https://github.com/fla-org/flash-linear-attention/issues/640 | FIRST_PARTY (host inspection reported to this cell, not re-run by it; the tilelang addition is in progress, not finished) |
| C36 | Fetched checkpoint receipts exist under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ on fal-h100-01 for registry ids qwen3.5-4b-base, qwen3-1.7b-base, transformer-1.3b-100b, gla-1.3b-100b, transformer-340m-10b, gla-340m-15b, gdn-1.3b-isp-hybrid-3to1-50b, gdn-340m-isp-hybrid-3to1-10b, e2-ttt-mlp-1.3b-15b, rwkv7-1.5b-world; for this direction: transformer-1.3b-100b artifact root 7b6675e3f5e9dccdbec2940b5aa846835d124f16a7b609155859af4b0a736be6 (2,730,912,365 bytes), gla-1.3b-100b da4eb9fb3ebb11863a7f4b959494c0d112140b9d01429c00da000ec087c37420 (2,733,360,812 bytes), gdn-1.3b-isp-hybrid-3to1-50b 34b36f5b54a4f719b64d600d05cc4d58b0e14f6a0fa63c4ea1fede7b4fd56ef7 (5,732,906,548 bytes), qwen3-1.7b-base 231d93ceda83766be8724d6eb37c48e97219f2fd3018cb64ec20860f88944321 (3,452,692,285 bytes); none yet for transformer-2.7b-100b, delta-net-1.3b-100b, mamba-1.3b-100b | wave-5 spec brief UPDATE and the orchestrator's receipts-summary.json (revision, artifact_root_sha256, total_bytes per id) | FIRST_PARTY (reported to this cell; receipt files not opened by it) |
| C37 | Phase-0 doctor receipt data/results/icl-rule-distillation-port/phase0-doctor.json: status PHASE0_DOCTOR_PASS, 66 of 66 gates, 15.4 s, seed 42, numpy 2.5.2, scipy 1.18.0, Python 3.13.14, payload sha256 cc8e8a12a844bfef7f2541cae41108fde03a95bdd68da8f0da61bdde967d921e, implementation sha256 edfdc373f8b398d99ac55845eb9a7f404d1a8804f6fddc546252ddc6762135d7. Synthetic-case numbers (16-d state, 4 tasks, sigma 0.25, 8 demonstrations): dMMSE-versus-ridge separation 0.550, key-span ceiling gap 0.499 (oracle-realised), R_theta fidelity to dMMSE 0.942 (ridge -0.110), R_gf 0.379 (ridge 0.836), R_adapt 0.377 (ridge 0.840), R_lin 0.365 (ridge 0.817), D(R_theta, R_gf) 0.563, D(R_gf, R_lin) 0.015, D(R_gf, R_adapt) 0.002, w-clamp cost 5.215 with key-span residual 0, rho-clamp 0.920, eta-clamp 0.934, negative-control optimisation-only gap 0.094 with key-span gap 0, permuted-teacher fidelity at most -0.278, all selected learning rates 3e-3 (grid edge); pytest 17 passed, ruff clean | the receipt at data/results/icl-rule-distillation-port/phase0-doctor.json (a git-ignored path; the hashes above identify it) and scripts/run_icl_rule_distillation_doctor.py; tests/test_icl_rule_distillation_doctor.py | VERIFIED (executed by this cell on 2026-09-01; synthetic-case numbers, no model) |
| C38 | Full attribution-tree Monte-Carlo under the assumed noise SDs (0.08 family, 0.06 seed, 0.035 query; 3 seeds; 4,000 draws; seed 42; clamp, sibling and audit gates assumed to pass): true effect 0.10, 8 families, 4 function-induction families: primary leaf (interval excludes 0 and point ≥ 0.10) 0.509, re-tiered class condition 0.518 (wave-4 two-sided 0.279), CONFIRMED 0.386, CLASS_UNRESOLVED 0.123, INCONCLUSIVE 0.278, K1 0.212; 5 class families: CONFIRMED 0.394; 3 class families: CONFIRMED 0, CLASS_UNRESOLVED 0.499; effect 0.15: CONFIRMED 0.847, CLASS_UNRESOLVED 0.091, INCONCLUSIVE 0.042, K1 0.020; null: CONFIRMED 0.001, K1 0.978, INCONCLUSIVE 0.020 | harness/icl_rule_distillation.py simulate_attribution_tree_power, exercised in the phase-0 doctor receipt (C37), case attribution_tree_semantics_and_power | VERIFIED (computed by this cell; the SDs remain assumptions) |
| C39 | models/registry.yaml (commit 53773c3, 2026-09-01 18:39 -0700) registers transformer-1.3b-100b, transformer-2.7b-100b, gla-1.3b-100b, delta-net-1.3b-100b (license unresolved), mamba-1.3b-100b (license unresolved), gdn-1.3b-isp-hybrid-3to1-50b and qwen3-1.7b-base with the 40-hex revisions of C01, C02, C03, C11 and C34; fla-hub retnet, hgrn2 and gsa 1.3B-100B, state-spaces transformerpp-2.7b, mamba2-2.7b, mamba2attn-2.7b and EleutherAI/pythia-2.8b are not registered | models/registry.yaml in this repository; git log for 53773c3 | VERIFIED (in-repo, this cell) |

## Closest Prior Work

All items were opened at abstract or HTML level by a gauntlet cell. The wave-3 repair added items 8-12, named by both
wave-2 judges; the wave-4 repair adds items 13-17, named by the two wave-3 reviewers, each opened before inclusion.

1. Can Gradient Descent Simulate Prompting? — https://arxiv.org/abs/2506.20989 (2025-06-26). Meta-trained same-model
   gradient step emulates conditioning; not externalised, not ported. Here the rule is externalised at a canonical
   interface, frozen, ported across operator families, and compared with an iso-capacity gradient-form ladder.
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
   distilled rule ties the cross-teacher KL sibling (K6).
7. Algorithm Distillation — https://arxiv.org/abs/2210.14215. Distils an algorithm INTO a sequence model (reverse
   direction).
8. Trained Persistent Memory for frozen decoder-only / encoder-decoder LLMs (Jeong) — https://arxiv.org/abs/2603.22329
   and https://arxiv.org/abs/2603.16413. The closest FRAMING prior: it already states "a universal write rule shared
   across backbones plus architecture-specific read paths". Its write rule is a fixed attention/Hebbian aggregation with
   frozen random write projections, trained with LM loss, evaluated on two same-family models, never ported and never
   compared with ICL or GD (C18). Delta here: the rule is learned by distillation from a transformer's in-context
   behaviour, compared head-to-head with an iso-capacity gradient-form ladder at the same interface, ported frozen
   across operator families, and evaluated on teacher fidelity on held-out families.
9. FAAST — https://arxiv.org/abs/2605.04651. Closed-form pseudoinverse fast weights on frozen hidden states as an
   alternative to ICL; model-agnostic; a fixed rule, not distilled, not transferred. It is a natural extra special case
   for the derived-rule grid and is added there.
10. Language Models Need Sleep — https://arxiv.org/abs/2605.26099. A learned local rule writing context into SSM-block
    fast weights inside one end-to-end-trained model; not distilled from a transformer, not ported.
11. Cross-model Control — https://arxiv.org/abs/2410.17599. A portable logit-shift tiny LM across tokenizers and
    architectures: it transfers a delta language model, not an in-context update rule, and needs no write/read state.
12. ICLCA — https://arxiv.org/abs/2406.02847. Exact ICL-to-bias conversion in linearized transformers; analytic, single
    model, no port.
13. The ICL-as-GD lineage that defines this proposal's null: von Oswald et al. 2022 — https://arxiv.org/abs/2212.07677
    (2022-12-15; linear self-attention implements a gradient step on regression); Akyürek et al. 2022 —
    https://arxiv.org/abs/2211.15661 (2022-11-28; ICL on linear regression implements GD, ridge and Bayesian
    estimators); Dai et al. 2022 — https://arxiv.org/abs/2212.10559 (2022-12-20; attention has a dual form of GD, ICL as
    implicit finetuning); von Oswald et al. 2023, mesa-optimization — https://arxiv.org/abs/2309.05858 (2023-09-11;
    autoregressive transformers implement gradient-based optimisation of a principled objective in the forward pass);
    Shen et al. 2023 — https://arxiv.org/abs/2310.08540 (2023-10-12; negative evidence on pretrained LMs: ICL and GD
    differ in order sensitivity and in how they modify the output distribution, C29). Delta here: these works analyse or
    test a same-model equivalence, mostly in linear or synthetic settings; none distils the update into an external rule,
    none compares it with an iso-capacity gradient-form ladder at a fixed interface, none ports it. Shen's two
    discriminators are the origin of the order-sensitivity and error-agreement secondaries.
14. Write-rule taxonomies: MIRAS — https://arxiv.org/abs/2504.13173 (2025-04-17; memory type, attentional bias, retention
    gate and learning algorithm as design axes); Test-time regression — https://arxiv.org/abs/2501.12352 (2025-01-21;
    attention, linear attention, SSMs and fast weights as regressors defined by weights, function class and optimiser).
    These taxonomies classify architectures by construction and name the cells of the gradient-form ladder used here
    (R_lin, R_adapt and R_gf are key-directed regressors with a linear, content-adaptive-linear or nonlinear error map).
    Delta: the question here is which cell a frozen transformer's behaviour occupies, measured by distillation, not which
    cell to build.
15. Linear Transformers Are Secretly Fast Weight Programmers, Schlag et al. 2021 — https://arxiv.org/abs/2102.11174
    (2021-02-22). Delta-rule fast weights with an adaptive learning rate, trained end to end inside one model: the origin
    of R_lin's delta-rule special case; not distilled from a teacher, not ported.
16. Context distillation: Learning by Distilling Context, Snell et al. 2022 — https://arxiv.org/abs/2209.15189
    (2022-09-30). A student without the context is trained to match the teacher's outputs with the context; Doc-to-LoRA
    (item 3) inherits the objective. Askell et al. 2021 — https://arxiv.org/abs/2112.00861 (2021-12-01) is credited by
    wave-3 Reviewer B with the earlier use; the abstract page does not mention the technique and the body was not opened.
    Delta: context distillation writes the context into one model's weights; here the trained object is a base-independent
    external write rule and the base receives no gradients.
17. In-repo: Direction 16, Portable Sidecar Update Dynamics — directions/16-portable-learning-dynamics.md and
    experiments/architectures/portable-sidecar-update.yaml (status NARROWED 2026-09-01). Identical interface by design
    (C30): rank-8 factorised 64x64 state at four evenly spaced layers, base-specific rank-8 P/Q, M_(j+1) = Pi_r[rho M +
    eta u v^T]. Direction 16 ports a task-conditioned online sidecar trained on a prequential outcome loss with a task
    latent across a held-out task-base cell on typed tool tasks. Delta: no task latent, no outcome stream; the rule is
    distilled by KL from a transformer's in-context behaviour, scored on teacher fidelity against a nested gradient-form
    ladder at iso-capacity, and ported across six operator families; a K1 result here is Direction 16's premise test.

Also relevant, not collisions: Memory Decoder — https://arxiv.org/abs/2508.09874; Latent Context Compilation —
https://arxiv.org/abs/2602.21221; Hebbian/gradient plasticity fast-weight modules — https://arxiv.org/abs/2510.21908;
meta-learned update rules that generalize across architectures — https://arxiv.org/abs/1804.00222 (weakens the
"learned rules transfer" surprise, does not distil from ICL or target frozen LMs).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Write rule distilled by KL from a frozen transformer's in-context behaviour into an external rank-8 fast-weight memory | Doc-to-LoRA (https://arxiv.org/abs/2602.15902); Can GD Simulate Prompting (https://arxiv.org/abs/2506.20989) | no | Prior emits per-model WHAT (adapter or gradient step); here the HOW (write rule) is the trained object and the base stays frozen with no test-time gradients | 0.60 |
| Canonical 64-d rank-8 interface at four sites with base-specific rank-8 P/Q ports | In-repo Direction 16 / portable-sidecar-update.yaml (C30); Trained Persistent Memory (https://arxiv.org/abs/2603.22329); Cache-to-Cache (https://arxiv.org/abs/2510.03215) | yes | The interface is the repository's own and carries no novelty; it is reused so that this study tests Direction 16's premise. Jeong shares the framing (universal write, per-backbone read) with a fixed Hebbian rule and LM loss; C2C transfers state through a projector. What differs here is what is trained at the interface and how it is scored, not the interface | 0.90 (that the interface itself is not new) |
| Nested gradient-form ladder R_lin ⊂ R_adapt ⊂ R_gf ⊂ R_theta at iso-capacity, same loss, episode mix, search budget and compute, with a pre-registered attribution tree and clamp ablations (wave 4) | MIRAS (https://arxiv.org/abs/2504.13173); Test-time regression (https://arxiv.org/abs/2501.12352); Shen et al. (https://arxiv.org/abs/2310.08540); Falcon (https://arxiv.org/abs/2608.27763); Kaczmarz (https://arxiv.org/abs/2605.08587); OSDN (https://arxiv.org/abs/2605.13473); FAAST (https://arxiv.org/abs/2605.04651) | no | Taxonomies name the cells and derived-rule papers build them; Shen tests ICL against GD inside one model with order and output-distribution probes; none locates a frozen transformer's implicit rule within a nested ladder by matched behavioural distillation with a capacity-matched decisive control | 0.60 |
| Cross-teacher KL sibling as the live collapse control (wave 4) | Context distillation (https://arxiv.org/abs/2209.15189); Fast Weight Layers (https://arxiv.org/abs/2212.02475) | no | Tests whether fidelity is specific to the source teacher rather than to any KL-distilled ICL rule; an identification device, not a novelty claim | 0.50 |
| Teacher-fidelity endpoint on held-out families with a matched gold-plus-shuffled placebo (wave-3) | Function Vectors (https://arxiv.org/abs/2310.15213); TR/TL (https://arxiv.org/abs/2305.09731) | no | Priors measure accuracy and TR/TL of the base; here fidelity to the teacher's per-query predictions and errors is the primary object and the placebo is in-distribution for every rule | 0.65 |
| Frozen-rule port to six pure-recurrent 1.3B-100B bases on one corpus, tokenizer and budget | Attention-to-Mamba weight distillation (https://arxiv.org/abs/2604.14191); XKV (https://arxiv.org/abs/2608.20617) | no | Priors transfer weights or state; here the rule is transferred to bases with no KV cache and the site is strictly after a recurrent sublayer | 0.55 |
| Downstream-attention read-path ablation on hybrids (wave-3) | none located | no | Replaces the inert adjacent-layer site factor; a genuine counterfactual on whether softmax downstream of the injection carries the readout | 0.50 |
| Write-A/read-B held-out-language probe of the writes' content | MLNeedle (https://arxiv.org/abs/2408.10151); ONERULER (https://arxiv.org/abs/2503.01996) | no | Priors probe softmax retrieval across languages; here the probe is of an explicit external write against an encoder-invariance baseline (R_gf with lambda_eq = 0), with a pre-registered null | 0.50 |

Novelty wording: No direct prior art found through 2026-09-01 under the coverage stated in the header (H100-host arXiv
relay, HF papers, Crossref, OpenReview titles only, WebFetch abstract pages, GitHub and Hugging Face metadata, the wave-1
refuter's 31 queries, the wave-2 repair's 6 hostsearch calls, and the wave-4 repair's 10 opened abstract pages plus the
Hugging Face API license re-check; Semantic Scholar, OpenReview bodies, ACL Anthology, patents and Chinese venues not
searched). The wave-2 novelty refuter did not refute (confidence 0.6) and the blind discrimination judged the mechanism
different from its nearest prior (confidence 0.88). Collision risk stays high: the intersection of context-to-weights,
state-transfer and TTT vocabularies is crowded and a 2026 paper under different wording could exist. This is not a
global-priority claim and is pending a signed provider-distinct audit.

PRISMA-style screening counts (C33; partial, as the Novelty protocol row of research-gauntlet-loop.md requires): wave 1 —
31 queries, records identified and screened not counted at the time (UNKNOWN), 7 priors included (items 1-7); wave 2 — 6
hostsearch calls, 5 records identified, screened and included (items 8-12); wave 4 — 10 records identified from the two
wave-3 reviews, 10 abstract pages opened and screened, 9 included (items 13-17 including the in-repo Direction 16), 1
recorded with a caveat (Askell 2021). No record was excluded after screening. The wave-1 identified and screened counts
cannot be reconstructed and are reported as unknown rather than estimated.

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
parameters (about 2.7e5 at d_b = 2048 over four sites). R_theta is a 2-layer MLP: 266 inputs (k, v, e, M k, ||k||, i
and 8 state statistics), hidden width 256, 130 outputs (rho, eta, u, w), about 1.02e5 parameters (C32), shared across
sites and bases.
Gradient-form ladder at the same interface (wave 4); every rung writes in the key direction, w_i = k_i:
  R_lin (linear preconditioned GD, about 4.1e3 parameters; the wave-3 R_GD):
    u_i = W e_i     eta_i = eta_0 (i+1)^(-gamma) / (||k_i||^2 + eps)^beta     rho_i = rho_0
    learned W in R^(64x64) and scalars (eta_0, gamma, beta, rho_0); contains the delta rule (W = I, beta = gamma = 0),
    Kaczmarz (beta = 1), OSDN diagonal (W diagonal), Falcon normalised rules and FAAST pseudoinverse steps as special cases.
  R_adapt (content-adaptive preconditioned GD, iso-parameter with R_theta; wave-3 Reviewer A's arm):
    (rho_i, eta_i, d_i) = MLP_psi(the same 266 inputs)     u_i = (W_0 + diag(d_i)) e_i     learned dense W_0
    hidden width about 293 so that the total matches R_theta within 1 percent; linear in the error given the context.
  R_gf (nonlinear gradient-form rule, iso-parameter with R_theta; wave-3 Reviewer B's arm; the decisive control):
    (rho_i, eta_i, u_i) = MLP_phi(the same 266 inputs)     w_i = k_i
    the R_theta network with the w head removed and hidden width about 305 so that the total matches within 1 percent.
  R_theta = R_gf plus a free write direction w_i, the only degree of freedom outside gradient form.
  Nesting: R_lin ⊂ R_adapt exactly (d_i = 0); R_adapt ⊂ R_gf up to the shared width; R_gf ⊂ R_theta exactly (w_i = k_i).
Post-hoc clamp ablations on the trained R_theta (evaluation only, no retraining):
  w-clamp: w_i := k_i        rho-clamp: rho_i := mean over i of rho_i        eta-clamp: eta_i := mean over i of eta_i
Distillation loss (source only; distillation families D only; gold AND shuffled-label episodes, 2:1):
  L_dist = sum_i sum_q KL( p_T(. | q, c_(≤ i)) || p_(T,M_i)(. | q) )      with c the gold or the shuffled episode
  truncated BPTT through the 8 writes, over the rule parameters (theta, phi, psi, or W and scalars), P_T, Q_T;
  every rule family receives the same written hyperparameter search at the same development budget (Evaluation).
Cross-lingual equivariance (Stage D only, training pairs en-de/es/zh):
  L_eq = || Delta M(c_i) - Delta M(c_i^B) ||_F^2       evaluated behaviourally on held-out languages (write en, read B).
Port to target b': freeze the rule; fit P_b' by ridge regression of span-pooled target residuals onto the source's
canonical keys and Q_b' by functional matching of next-token log-prob shifts under a fixed bank of 8 injected random
rank-1 M's, both on 2k x 512-token FineWeb-Edu sequences containing no task family.
```

**Wave-3 identification repair (union of both wave-2 judges' highest-impact fix; retained).**

(a) *Matched placebo.* The teacher's own shuffled-label episodes enter the distillation stream of every rule (R_theta,
every rung of the gradient-form ladder, the cross-teacher sibling since wave 4, and the random-theta P/Q fit) at a
fixed 2:1 gold-to-shuffled ratio; on a shuffled
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
accuracy across three demonstration permutations). A rule that beats R_gf on accuracy but not on fidelity is reported as
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

**Wave-4 identification repair (union of both wave-3 reviewers' highest-impact fix; where they differed, the option that
strengthens identification was chosen and is named).** Both reviewers found the same defect: R_GD (about 4.1e3
parameters, linear in the error) against R_theta (about 1e5 parameters, free write) under the same KL loss is a
nested-class contest with a 25x capacity gap, so a P1 win could not separate "not GD" from "not linear". Reviewer A
asked for a content-adaptive preconditioned-GD arm at iso-parameter count as the decisive control; Reviewer B asked for
an iso-parameter nonlinear gradient-form arm. Both are added as a nested ladder, and R_gf (Reviewer B's arm) is the
decisive control because it is the larger gradient-form class at matched capacity: a win over it isolates the single
remaining non-GD degree of freedom, the free write direction, which the w-clamp ablation then tests directly. R_adapt
(Reviewer A's arm) is the attribution rung that says whether nonlinearity in the error map matters when R_theta ties
R_gf. Further changes: (g) a pre-registered attribution tree replaces the single P1 threshold, with the w-clamp
ablation and the function-induction class as required co-conditions of a P1 win; (h) K1 is redefined against R_gf;
(i) the CE-trained sibling, which both reviewers found inert on a fidelity endpoint, is replaced by a sibling distilled
by the same KL objective from a different transformer teacher (fla-hub/transformer-2.7B-100B, iso-tokenizer, C02), so
that K6 is live, with a teacher-disagreement precondition; (j) P2/K3 are closed on the four licensed pure-recurrent
targets (C28) with an explicit MIXED outcome at exactly 2 of 4; (k) a written per-arm hyperparameter search at equal
development budget for every rule family; (l) the decision-bearing interval is the two-sided 95% t-interval on
family-level means, with the percentile bootstrap demoted to a reported sensitivity after re-simulation (C25); (m)
Direction 16 is discriminated in the Novelty Ledger and items 13-17 are added after opening each abstract.

**Wave-5 executability repair (union of both wave-4 reviewers' highest-impact fix; the proposal was judged 66/65 before
it).** Both wave-4 reviewers named the same fatal defect, nothing executable after four waves, and Reviewer 2 added that
the attribution tree's stated power (0.78) belonged to one leaf of a conjunction whose class co-condition had power
0.21-0.48 at 3-5 class families under the proposal's own noise model and routed a miss to K1. The repair: (n) Stage A(a),
(b), (e) and (g) are now real code, harness/icl_rule_distillation.py (the canonical interface, the rule ladder with
hand-written truncated-BPTT gradients, the finite-task-prior dMMSE regime with its exact key-span ceiling, the clamp
ablations, the two-pass causality audit, the parameter-count and Pi_8 doctors, the attribution tree and its power
simulation), executed by `scripts/run_icl_rule_distillation_doctor.py --output
data/results/icl-rule-distillation-port/phase0-doctor.json` on a CPU with NumPy/SciPy only (C37: PHASE0_DOCTOR_PASS, 66
of 66 registered gates, 15.4 s; tests/test_icl_rule_distillation_doctor.py, 17 tests including two tamper cases and a
finite-difference gradient check for every rung); (o) the class co-condition is re-tiered to a class point estimate ≥
0.10 with a one-sided 80% lower bound above 0, requires at least 4 eligible function-induction families (Reviewer 1's
minimum), and a miss routes to the pre-registered non-kill CLASS_UNRESOLVED instead of K1, with the full-tree Monte-Carlo
(C38) replacing the single-leaf power statement; (p) the contract's arms name the registered direction-19 ids instead of
stand-ins and the false "not registered" sentences are removed (C39); (q) the rebuilt fla 0.5.2 image and the fetched
checkpoint receipts are cited (C35, C36) and the contract carries a reference_doctor block. Not done, because each needs
the node or a model: the tokenizer, loader, MFU and TR-fidelity doctors on real episodes, the container smoke, the sbatch
dry-run and the evidence bundle; Compute therefore stays FAIL.

**Falsifiable predictions (pre-registered).** Let D(a, b) = F(a) - F(b) on eligible held-out families with the two-sided
95% t-interval on family-level paired means (Evaluation).

- P1 (identifiability, Stage B, source only; the attribution tree is decision-bearing; re-tiered in wave 5 and
  implemented as attribution_tree in harness/icl_rule_distillation.py with the decision order K2, K4, K1, K6,
  INCONCLUSIVE, UNATTRIBUTED, class). Primary leaf: D(R_theta, R_gf) ≥ 0.10 with the two-sided 95% interval excluding 0.
  Co-conditions: the w-clamp ablation of the trained R_theta costs ≥ 0.05 fidelity (the win is carried by the free write
  direction); D(R_theta, S_x) ≥ 0.05 against the cross-teacher sibling on families where the two teachers disagree on
  ≥ 0.10 of queries (K6 if not; UNINFORMATIVE if no such family exists); F(random-theta with fitted P/Q) ≤ 0.5 x
  F(R_theta) and every arm passing the TR-fidelity gate on at least 8 eligible families (K4 if not); and the class
  co-condition: at least 4 eligible function-induction families (families whose labels are computed from the input
  rather than looked up) with a class point estimate ≥ 0.10 and a one-sided 80% lower bound above 0. P1 is CONFIRMED
  only if the primary leaf and every co-condition hold. CLASS_UNRESOLVED (pre-registered non-kill, wave 5) if the
  primary leaf, clamp, sibling and reservoir conditions hold but the class co-condition fails or fewer than 4
  function-induction families are eligible: no port, per-class report, and extending the family pool is the only
  permitted follow-up. UNATTRIBUTED if the primary leaf holds but the w-clamp costs below 0.05: the gap is not carried by
  the pre-registered non-GD structure; reported as an unexplained iso-capacity difference, no port. INCONCLUSIVE if
  D(R_theta, R_gf) lies between 0.05 and 0.10 with the interval excluding 0: reported, no port. K1 only when the primary
  leaf itself fails (below). Ladder readings reported alongside: D(R_gf, R_lin) and D(R_gf, R_adapt). Secondary: mean
  r_TL(R_theta) ≥ 0.60 and r_TL(R_theta) - r_TL(R_gf) ≥ 0.15 on admitted families.
- P2 (port, Stage C, licensed targets gla, retnet, hgrn2, gsa; delta_net and mamba are run and reported as
  discovery-only and never counted, C28): ported D(R_theta, R_gf) ≥ 0.05 on at least 3 of the 4 licensed targets that
  pass the per-base eligibility gate, with at least 3 eligible; exactly 2 of 4 is the pre-registered MIXED outcome
  (partial portability, per-operator report, no portability claim, no upgrade contract); fewer than 3 eligible licensed
  targets is UNMEASURABLE. The same-family port transformer-1.3B to transformer-2.7B retains ≥ 0.6 of the source F;
  under the downstream-attention patch on the hybrid, after-GDN fidelity retains ≥ 0.7 of its unpatched value (if ≤ 0.5,
  downstream softmax carried the readout).
- P3 (content vs surface, Stage D, held-out languages sw/hi/th/ar/tr/id/vi/ja): with lambda_eq = 0 the write-en/read-B
  fidelity gap of R_theta is within 0.10 of R_gf's gap (encoder invariance explains it); with lambda_eq trained on
  en-de/es/zh only, the held-out-language gap shrinks by ≥ 0.15 at ≤ 0.05 monolingual fidelity cost; R_gf with lambda_eq
  is also run so that the shrinkage is not attributable to the co-fitted P alone. If the lambda_eq = 0 gap is already
  ≤ 0.05, P3 is declared null. Stage D reuses the Stage-B selected hyperparameters per rule (no re-search).
- P4 (dynamics signatures, held-out episodes; secondary, Holm-corrected, not a co-condition): the effective step
  s_i = eta_i ||u_i|| ||w_i|| decays with i (Spearman rho ≤ -0.5 over i = 1..8) and on key-collision episodes the emitted
  rho_i for the colliding direction falls below 0.7. R_adapt and R_gf can express both, so P4 characterises the teacher's
  dynamics rather than separating R_theta from gradient form; the rho-clamp and eta-clamp ablations report how much
  fidelity each policy carries.

**Kill criteria (falsifiers).** K1 (primary leaf only; a class-level miss is CLASS_UNRESOLVED, never K1): D(R_theta,
R_gf) below 0.05 or the interval including 0 on the source → at this
interface, capacity and eligible family set the teacher's content-dependent update is behaviourally a gradient-form
(key-directed) rule; the ladder gives the bounded reading: if D(R_gf, R_lin) ≥ 0.10, "GD with a learned
content-dependent preconditioner" (with D(R_gf, R_adapt) saying whether nonlinearity in the error map is needed); if
D(R_gf, R_lin) is below 0.05, "linear preconditioned GD suffices"; reported per family class (binding-dominated eligible
sets make associative rules the natural solution) and stop. K2: fewer than 8 held-out families pass the eligibility gate
on the source → unmeasurable at this scale; report and stop. K3: ported D(R_theta, R_gf) ≥ 0.05 on fewer than 2 of the 4
licensed pure-recurrent targets → the distilled rule does not port across operators (exactly 2 is MIXED, not a kill);
K3b: the downstream-attention patch removes ≥ 0.5 of after-GDN fidelity on the hybrid → the readout depended on softmax.
K4: any audit failure (two-forward-pass prefix-invariance audit not identical at fp32 tolerance; a poisoned
demonstration persisting after the declared reset; random-theta ≥ 0.5 x R_theta; any arm failing the TR-fidelity gate
on more than half of the eligible families; the parameter-count doctor reporting R_gf or R_adapt outside 1 percent of
R_theta; the phase-0 doctor failing any registered gate on the implementation at its frozen hash). K5: lambda_eq costs more than
0.10 monolingual fidelity or fails to shrink the held-out-language gap. K6
(collapse): D(R_theta, S_x) below 0.05 on families where the 1.3B and 2.7B teachers disagree on ≥ 0.10 of queries → the
fidelity is not specific to the source teacher; report as a Fast Weight Layers / SRWM-class learned ICL rule; if the
teachers disagree on fewer than 0.10 of queries on every eligible family, K6 is UNINFORMATIVE and is reported as such.

**Strongest counter-argument (devil's advocate).** The wave-3 objection, that R_theta's function class strictly
contains R_GD so a fidelity win is the default expectation of distillation, is met by the iso-parameter ladder and the
clamp co-condition, but three weaker forms survive. (1) Optimisation, not structure: at equal parameter count the free
write head may simply be easier to optimise under KL; the w-clamp ablation on the trained rule answers this only
together with R_gf's own training at the same budget and search, so the two must be read jointly and an UNATTRIBUTED
outcome is pre-registered for the case where they disagree. (2) Surface biases: non-GD structure in the teacher's
behaviour, including majority-label and recency effects, registers as a fidelity win without demonstrating a content
update; matching the teacher's errors and order sensitivity is evidence of matching the HOW including its biases, which
a portable rule should carry, and the family-class requirement keeps a binding-only win from counting. (3) Teacher
agreement: if the 1.3B and 2.7B teachers agree on most held-out queries the cross-teacher sibling cannot lose and K6 is
uninformative; the disagreement precondition makes that outcome explicit rather than a silent pass. The pre-registered
ceiling stands: if the eligible held-out set is dominated by exact-recall binding tasks, R_lin is at capacity and a K1
tie is expected there and is not an interesting negative.

**What's missing.** A from-scratch matched arm (deferred by the rescope); an independent replication of the fla-hub
ladder's corpus identity for delta_net and mamba (inferred from the DeltaNet paper, not card-stated) and their licenses
(absent as of 2026-09-02, C28); a Stage-A model loop actually executed (the CPU phase-0 doctor, including the
parameter-count doctor, is executed since wave 5 on a synthetic regime; the model-side doctors, loader and MFU smokes are
not); a measured, not assumed, MFU on the node; and a pilot estimate of the three noise SDs that the power table assumes.

## Cheapest Decisive Pilot

Public data only; General Translation data is an optional upgrade. Substrate revisions are listed in the direction file.
Seven direction-19 checkpoints are registered in models/registry.yaml (commit 53773c3, C39: transformer-1.3b-100b,
transformer-2.7b-100b, gla-1.3b-100b, delta-net-1.3b-100b, mamba-1.3b-100b, gdn-1.3b-isp-hybrid-3to1-50b,
qwen3-1.7b-base) and the contract's arms name them; four carry fetched receipts on fal-h100-01 (C36). fla-hub retnet,
hgrn2 and gsa (three of the four licensed P2/K3 targets), the state-spaces 2.7B triplet and pythia-2.8b are not yet
registered, so Stages C and E cannot be enabled.

**Stage A (CPU, fp64, 0 GPU-h): algebra, causality and regime doctors.** *Executable part, run in wave 5:* `uv run python
scripts/run_icl_rule_distillation_doctor.py --output data/results/icl-rule-distillation-port/phase0-doctor.json`
(implementation harness/icl_rule_distillation.py; tests tests/test_icl_rule_distillation_doctor.py; NumPy/SciPy only, no
torch, 15.4 s on the Mac). The receipt at that path (a git-ignored results directory, as for every doctor receipt in this
repository; its hashes are in C37) is PHASE0_DOCTOR_PASS with 66 of 66 registered gates and evidence grade
SYNTHETIC_EXECUTABILITY_AND_GATE_SEMANTICS_ONLY (C37); every number that follows is a synthetic-case number and proves
that the code paths execute and the gates have the intended semantics, nothing about a pretrained model. Registered
cases: (a) the finite-task-prior regime of Raventós et al. (C16) with a 16-d state, 4 unit-norm tasks, sigma 0.25 and 8
demonstrations, in which the dMMSE teacher differs from ridge by 0.55 of its variance and the exact key-span ceiling,
realised through the write code path by an oracle rule, caps every w_i = k_i rule at 0.50 fidelity (the readout row of
any key-directed rule started from M = 0 lies in the span of the 8 keys, an 8-dimensional subspace of the 16-d state);
after the written 4-point search at equal budget (all four rules select 3e-3, a grid edge, flagged), R_theta reaches
0.94 fidelity to dMMSE and -0.11 to ridge, while R_gf 0.38, R_adapt 0.38 and R_lin 0.37 sit under the ceiling and track
ridge (0.84, 0.84, 0.82); ladder readings D(R_theta, R_gf) 0.56, D(R_gf, R_lin) 0.015, D(R_gf, R_adapt) 0.002; the
w-clamp of the trained R_theta costs 5.2 fidelity points and confines the readout to the key span (residual 0), while
the rho- and eta-clamps cost 0.02 and 0.01; (b) a Gaussian-prior negative control whose teacher is ridge itself, inside
the key span, so the gradient-form null is true by construction: the regime statistic reports non-separation (key-span
gap 0) and the trained R_theta still beats R_gf by 0.094 at the carried-over learning rates, which the doctor reports as
optimisation-only and refuses to attribute, an executed instance of counter-argument (1) below; (c) a permuted-teacher
control in which every rule's fidelity collapses to at most -0.28; (d) the two-pass causality audit: probe absence,
prefix invariance (deviation 0), zero-state read and reset attestation pass, and a probe leaked into Pass W as a ninth
demonstration is detected; (e) Pi_8 is inert for eight rank-one writes from M = 0 and truncates a ninth, so the rank
constraint advertised in the Mechanism block is asserted to be a no-op inside an 8-shot episode (Reviewer 1's point);
(f) the parameter-count doctor at the pilot interface: R_theta 101,762; R_gf hidden 305 gives 101,631 (-0.13%);
R_adapt hidden 293 gives 101,731 (-0.03%); R_lin 4,100 (C32, now asserted by code) and the w := k clamp reproduces the
w-head-dropped R_gf network at fp64 tolerance; (g) attribution-tree routing on crafted inputs for every bucket and the
Monte-Carlo of the full tree (C38); (h) eighteen degenerate inputs each raise RuleContractError. The synthetic teacher's
predictive distribution is Gaussian with fixed variance, so the squared prediction gap the doctor minimises equals the
proposal's KL objective up to a constant. *Not executable without the node or a model, still owed before Stage B:* the
TR-fidelity gate on real gold-plus-shuffled episodes, the tokenizer doctor asserting piece-id identity across the
fla-hub 1.3B-100B and startlux tokenizers (C02, C03), the P/Q factorisation doctor on real residuals, the loader smoke
on the registered ids, and a 10-minute throughput smoke on one GPU inside the rebuilt image that measures MFU for a
hooked eager pass.

**Stage B (≤ 6 GPU-h ceiling, 5.6 estimated including reserve): identifiability on the source; the kill screen.** Source
fla-hub/transformer-1.3B-100B (C01). B0 denominator audit (gold / random-label / calibrated zero-shot) on 14 candidate
families. B-search: per-arm hyperparameter search at equal development budget, 4 configurations x 1,500 development
episodes x 1 epoch for each rule family (R_theta, R_gf, R_adapt, R_lin; the cross-teacher sibling with its 2.7B
teacher; a 4-point ridge grid for the random-theta P/Q fit), selection by development KL (Evaluation). B1 distillation
runs of 6k episodes x 2 epochs each at the selected configuration, 2:1 gold-to-shuffled: R_theta x3 seeds, R_gf x3,
R_adapt x2, R_lin x2, random-theta x2, cross-teacher sibling S_x x2 (KL target: fla-hub/transformer-2.7B-100B's own
8-shot predictions, C02). B2 special-case derived rules (delta, Kaczmarz, OSDN-diagonal, Falcon, FAAST) on R_lin's
fitted interface with a 16-point scalar grid on D. B3 held-out evaluation: fidelity endpoints, w-/rho-/eta-clamp
ablations of R_theta, TR-fidelity gate, r_TL, per-step curves, three demonstration permutations on 200 queries per
family, teacher-teacher agreement per family. Apply the attribution tree; stop if K1, K2 or K6 fires or the outcome is
UNATTRIBUTED or INCONCLUSIVE.

**Stage C (≤ 2.5 GPU-h ceiling, 2.4 estimated, gated on P1 CONFIRMED): port on the iso-ladder.** Licensed targets
fla-hub/{gla, retnet, hgrn2, gsa}-1.3B-100B (MIT, C28) carry P2/K3; fla-hub/{delta_net, mamba}-1.3B-100B (no license
field, C28) are run and reported as discovery-only and never counted. Sites strictly after recurrent sublayers;
same-family reference fla-hub/transformer-2.7B-100B; downstream-attention read-path ablation inside startlux
gdn-1.3b-isp-hybrid-3to1-50b (C03). Ported rules: R_theta x3, R_gf x3, R_lin x2. Per-base G_TL gate on every target
(C0). Label-free P/Q on FineWeb-Edu sample-10BT.

**Stage D (≤ 3.3 GPU-h, gated on P1 CONFIRMED): content vs surface inside one multilingual base.** Qwen/Qwen3-1.7B-Base
(C11); distil R_theta and R_gf each with lambda_eq in {0, lambda}, at the Stage-B selected hyperparameters (no
re-search), on SIB-200 plus MASSIVE English demonstrations and en-de/es/zh parallel pairs (C08, C09); evaluate
write-en/read-B on held-out languages and on the held-out dataset (train L_eq on SIB-200 topics, test on MASSIVE
scenarios, and vice versa).

**Stage E (≤ 3.3 GPU-h, gated on C): independent-ladder replication.** Pile 300B triplet (C04):
state-spaces/transformerpp-2.7b (source; R_theta x2, R_gf x2 at Stage-B hyperparameters) to mamba2-2.7b and
mamba2attn-2.7b (second read-path ablation), with EleutherAI/pythia-2.8b as the same-family reference. Needs pinned
mamba_ssm and causal-conv1d wheels.

**Budget ledger (C05 anchor; 25% MFU = 247 TFLOPS per GPU assumed; 25% reserve per stage; C24, recomputed in wave 4).**
FLOPs per token: teacher forward 2N, frozen-base forward plus activation backward 4N, evaluation forward 2N; episode =
384 demonstration tokens plus 8 steps x 8 probes x 28 tokens = 2,176 tokens; N = 1.3e9 for the source and 2.7e9 for the
cross-teacher sibling's teacher (per-pass 4N_1.3 + 2N_2.7 = 1.06e10 FLOPs per token).

| Stage | Item | FLOPs | GPU-h |
|---|---|---|---|
| B0 | 14 fam x 3 cond x 400 q x 700 tok x 2N (1.3e9) | 3.1e16 | 0.035 |
| B-search | 4 rule families x 6k passes x 2,176 tok x 6N, plus S_x 6k passes x 2,176 tok x 1.06e10, plus the random-theta ridge grid | 5.6e17 | 0.62 |
| B1 | 12 runs (R_theta x3, R_gf x3, R_adapt x2, R_lin x2, random x2) x 12k episode-passes x 2,176 tok x 6N | 12 x 2.0e17 | 2.75 |
| B1-S_x | 2 runs x 12k episode-passes x 2,176 tok x 1.06e10 | 2 x 2.8e17 | 0.62 |
| B2 | 5 rules x 16 grid x 6 fam x 200 q x 500 tok x 2N | 1.2e17 | 0.13 |
| B3 | 33 passes (14 arm-seeds, teacher conditions, 6 clamp ablations) x 8 fam x 400 q x 600 tok x 2N plus 15 x 3 permutations x 8 fam x 200 q x 600 tok x 2N | 2.8e17 | 0.31 |
| B total | x1.25 reserve | | 5.6 |
| C0 | per-base gate: 7 bases x 8 fam x 3 cond x 400 q x 700 tok x 2N | 1.3e17 | 0.14 |
| C-align | 72 fits (9 target-configs x 8 rule-seeds) x 1.05e6 tok x (4N_t + 2N_s) | 7.0e17 | 0.79 |
| C-eval | 10 target-configs x 19 passes x 8 fam x 400 q x 500 tok x 2N plus patched hybrid passes | 8.8e17 | 0.98 |
| C total | x1.25 | | 2.4 |
| D0 | 2 sets x 9 langs x 3 cond x 400 q x 600 tok x 2N (1.7e9) | 4.4e16 | 0.05 |
| D1 | 8 runs (R_theta and R_gf x lambda_eq in {0, lambda} x 2 seeds) x 12k passes x 2,176 tok x 6N (1.7e9) | 8 x 2.7e17 | 2.40 |
| D2 | 8 x 2 x 2 x 9 x 300 q x 500 tok x 2N | 1.5e17 | 0.16 |
| D total | x1.25 | | 3.3 |
| E-distil | 4 runs (R_theta x2, R_gf x2) x 12k passes x 2,176 tok x 6N (2.7e9) | 4 x 4.2e17 | 1.90 |
| E-align + eval | 16 fits + 4 configs x 11 passes | 6.5e17 | 0.73 |
| E total | x1.25 | | 3.3 |
| Program | | | 14.6 of 16 |

Decisive pilot (A + B + C) 8.0 GPU-h estimated (8.5 by stage ceilings); kill screen (A + B) 5.6 (6.0 ceiling). The
wave-4 changes add 2.3 GPU-h to B (the two iso-parameter rungs, the cross-teacher sibling's 2.7B teacher, the written
search and the clamp passes) and nothing to C, D or E, which now compare R_gf instead of R_lin at the same run counts;
the program stays inside the 16 GPU-h envelope with 1.4 GPU-h of slack. If the Stage-A throughput smoke measures MFU
below 12.5%, halve B1 and D1 episodes (3k x 2), run R_adapt and R_lin at one seed, and drop Stage E before touching C or
D.

## Controls, Baselines, and Ablations

- Native ICL with gold demonstrations; native ICL with shuffled labels (task-recognition-only reference; C07, Pan et
  al., Min et al.); contextual-calibration zero-shot as the zero-shot reference; held-out formats and task categories.
- R_gf, the iso-parameter nonlinear gradient-form rule (w_i = k_i) at the same interface, distillation loss, episode mix,
  P/Q co-fitting, hyperparameter-search budget and compute, with the parameter count matched to R_theta within 1 percent.
  This is the decisive control (wave 4).
- R_adapt, the iso-parameter content-adaptive preconditioned-GD rule (attribution rung), and R_lin, the linear
  preconditioned-GD rule containing delta, Kaczmarz, OSDN-diagonal, Falcon and FAAST as special cases, each special case
  also run with a scalar grid on R_lin's fitted interface (secondary grid).
- Cross-teacher KL-distilled sibling S_x: same student base, interface, episodes, mix, search budget and compute; KL
  target = fla-hub/transformer-2.7B-100B's own 8-shot predictions. Separates "this teacher's update" from "any
  KL-distilled ICL rule"; live only where the two teachers disagree on ≥ 0.10 of queries (reported per family). Replaces
  the wave-3 CE-trained sibling, which both wave-3 reviewers found unable to tie on a fidelity endpoint.
- Post-hoc clamp ablations of the trained R_theta (w := k, rho := mean, eta := mean), evaluation only; the w-clamp is a
  required co-condition of P1.
- Random-theta reservoir with fitted P/Q (0.5x kill; randomly initialised transformers already do in-context recall).
- Same-family ports (transformer-1.3B to transformer-2.7B; transformerpp-2.7b to pythia-2.8b) as port-fidelity upper
  references.
- Downstream-attention read-path ablation on startlux gdn-1.3b hybrid and mamba2attn-2.7b (wave-3 replacement for the
  inert adjacent-layer site factor).
- Iso-corpus / iso-tokenizer / iso-token-budget ladders by construction (fla-hub 1.3B-100B; Pile 2.7B triplet); the two
  ladders differ in corpus, tokenizer and recipe, so agreement across them is the replication test.
- No-update (M = 0) code-path check (inert by construction: the read adds exactly 0).
- Encoder-invariance baseline for P3: R_gf with lambda_eq = 0; R_gf with lambda_eq also run so P shrinkage is not
  attributed to the rule by default; held-out languages and held-out dataset.
- Audits on every arm: two-forward-pass prefix-invariance CI gate, TR-fidelity CI gate, hash-chained write log, reset
  attestation, single-adversarial-demonstration poisoning probe with persistence check across reset.
- Named but unbudgeted upper references for same-family ports only: MentorPulse live mentor
  (https://arxiv.org/abs/2608.20927), Engram reader transfer (https://arxiv.org/abs/2608.17050), KV translation
  (https://arxiv.org/abs/2608.30963).

## Evaluation, Statistics, and Leakage Checks

**Endpoints.** Primary: D(R_theta, R_gf) = F(R_theta) - F(R_gf) on the source over eligible held-out families (F defined
in Mechanism (b)), accepted only through the attribution tree in P1 (function-induction class, w-clamp co-condition,
sibling and reservoir gates). Secondary, Holm-corrected as one family: the ladder readings D(R_gf, R_lin) and
D(R_gf, R_adapt); r_TL gap on admitted families; error-agreement kappa; per-step curve distance; order-sensitivity
agreement; rho- and eta-clamp costs; per-target ported fidelity; hybrid patched-vs-unpatched ratio; Stage D gap
shrinkage.

**Minimum worthwhile effect.** 0.10 fidelity points on the primary endpoint (a tenth of the held-out queries whose
teacher-matching prediction is explained by the distilled rule and not by GD); 0.05 on the per-target port and sibling
comparisons. Below 0.10 on the source the rule is not worth porting.

**Noise estimate (assumed; no pilot exists).** Query-sampling noise on a paired 400-query agreement-rate difference about
0.035 (binomial); seed-to-seed distillation noise 0.06 (unknown, assumed); family heterogeneity of the true effect 0.08
(unknown, assumed). Under these assumptions the family-level SD of the mean difference is 0.089 at 3 seeds, giving
d_z about 1.1 at a 0.10 effect. The Stage-B run replaces all three with measured values before Stage C.

**Decision-bearing interval and seed/sample count (simulation, C25; re-run in wave 4).** The decision statistic is the
two-sided 95% t-interval on family-level paired mean differences (df = families minus 1); a comparison is positive when
the lower bound is above 0 and the point estimate meets its threshold. A 4,000-draw simulation under the noise model
(fam_eff = delta + N(0, 0.08^2); obs = fam_eff + N(0, 0.06^2) + N(0, 0.035^2) per seed; 3 seeds; numpy 2.5.2, scipy
1.18.0, seed 42) gives power 0.78 at a 0.10 effect with 8 eligible families, 0.89 with 10, 0.95 with 12, 0.98 at a 0.15
effect with 8, and one-directional Type-I 0.028 under the null (nominal 0.025). The wave-3 text described a one-sided
t-test at alpha 0.05 while reporting the t-interval numbers; the one-sided rule gives power 0.89 and Type-I 0.053, as
wave-3 Reviewer B found, and is not used. The 8-cluster percentile bootstrap that wave 3 named as the primary interval
has a simulated one-directional Type-I of 0.060 (about 2.4x nominal), confirming Reviewer B's finding; it is reported as
a sensitivity only. A wild-cluster (Rademacher) bootstrap on family residuals is the second sensitivity (Type-I 0.054,
power 0.76, two-sided at 0.05). Family count dominates: 2, 3 and 5 seeds give power 0.74, 0.78 and 0.80. Halving all
three SDs gives 0.999; doubling them gives 0.27, so the SDs measured in Stage B decide whether 8 families suffice or the
K2 threshold must rise. The pre-registered rule is therefore: at least 8 eligible held-out families (else K2), 3 seeds
on R_theta and R_gf (42, 43, 44), 2 seeds on R_adapt, R_lin, S_x and random-theta, and the power sensitivity table over
0.5x to 2x of each assumed SD is reported alongside the interval rather than a single number.

**Full-tree power (wave 5, C38; Reviewer 2's defect).** The 0.78 above is the probability that the primary leaf's
interval excludes 0; it is not the probability of the CONFIRMED verdict, which is a conjunction. The harness function
simulate_attribution_tree_power (4,000 draws, seed 42, the same assumed SDs; clamp, sibling and audit gates assumed to
pass) gives, at a true 0.10 effect with 8 eligible families and 4 function-induction families: CONFIRMED 0.39,
CLASS_UNRESOLVED 0.12, INCONCLUSIVE 0.28 (the interval excludes 0 but the point estimate falls below 0.10, which
happens about half the time when the true effect equals the threshold), K1 0.21; with 5 class families CONFIRMED 0.39
and CLASS_UNRESOLVED 0.10; with 3 class families CONFIRMED 0 by construction (the class co-condition is unmeasurable and
routes to CLASS_UNRESOLVED, 0.50). At a true 0.15 effect: CONFIRMED 0.85, CLASS_UNRESOLVED 0.09, INCONCLUSIVE 0.04, K1
0.02. Under the null: CONFIRMED 0.001, K1 0.978. The re-tiered class condition passes 0.52 at 4 class families against
0.28 for wave 4's two-sided interval, and a class miss no longer produces K1, so the kill screen no longer kills a true
0.10 effect more often than it confirms it (0.21 against 0.39). The honest cost is stated rather than hidden: a true
effect exactly at the minimum worthwhile size is CONFIRMED well under half the time, and the pre-registered reading of
INCONCLUSIVE or CLASS_UNRESOLVED at Stage B is "extend the family pool or stop", never "port". These are Monte-Carlo
frequencies under assumed SDs, not measurements; Stage B replaces the SDs.

**Per-arm hyperparameter search (written grid, equal development budget).** Every rule family receives the same search
before its seeded runs: 4 configurations x 1,500 development episodes (held-out episodes of the distillation families
only) x 1 epoch, selection by development KL to the teacher. Grid: learning rate in {1e-4, 3e-4, 1e-3, 3e-3}, with AdamW
(weight decay 0.01, cosine schedule, batch 32 episodes, KL temperature 1, truncated BPTT through 8 writes, P/Q
initialised from the top-64 principal directions of source residuals) fixed and identical across R_theta, R_gf,
R_adapt and S_x; R_lin uses the same learning-rate grid with W initialised at I; random-theta's P/Q fit uses a 4-point
ridge grid {1e-3, 1e-2, 1e-1, 1}. The selected configuration per rule is frozen in the run manifest and carried
unchanged into Stages D and E (no re-search; a pre-registered transfer). An arm whose selected configuration sits at a
grid edge is reported as such.

**Reporting standard.** Every comparison reports the paired effect with the family-level t-interval, the wild-cluster
and percentile bootstrap intervals as sensitivities, per-family and per-seed effects, the paired d_z, and exact
p-values; assumption checks (normality of family-level differences, absence of one dominating family via
leave-one-family-out) are reported; non-significant secondary results are reported in full; no observed-power
statements.

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

Pilot image (rebuilt with the architecture extra; exists on fal-h100-01, built by Slurm job 353 from commit 999f5583;
C35): tag cotcodec-research:999f5583-architecture, immutable image
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d` (image ID
sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad; torch 2.11.0+cu128, transformers 5.15.0,
flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0). tilelang is being added to the image because fla guards
the gated GDN backward on Hopper under Triton below 3.7.1 (fla issue 640), so the GDN hybrid's read-path ablation needs
either tilelang or a Triton 3.7.1 rebuild; mamba_ssm and causal-conv1d for Stage E are not in it. The image has not
been exercised by this contract: no container smoke, sbatch dry-run or fresh-job resume receipt exists for
icl-rule-distillation-port, so Compute stays FAIL. The earlier discovery image
`127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3` (image ID
sha256:ca32b5c26b92fbe2a7054ae96543cd62928b0493896ec355b869b612022aa9a2; created 2026-08-16; CUDA 12.8.1, torch
2.11.0+cu128, transformers 5.15.0; no fla; C23) is superseded for pilots and kept here only as provenance.

Checkpoint receipts (C36; reported by the wave-5 brief and its receipt summary, files not opened by this cell): registry
ids qwen3.5-4b-base, qwen3-1.7b-base, transformer-1.3b-100b, gla-1.3b-100b, transformer-340m-10b, gla-340m-15b,
gdn-1.3b-isp-hybrid-3to1-50b, gdn-340m-isp-hybrid-3to1-10b, e2-ttt-mlp-1.3b-15b and rwkv7-1.5b-world now have receipts
under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ on fal-h100-01. For this direction that covers the Stage-B
source transformer-1.3b-100b (artifact root sha256 7b6675e3f5e9dccdbec2940b5aa846835d124f16a7b609155859af4b0a736be6,
2,730,912,365 bytes), the licensed target gla-1.3b-100b (da4eb9fb3ebb11863a7f4b959494c0d112140b9d01429c00da000ec087c37420,
2,733,360,812 bytes), the hybrid gdn-1.3b-isp-hybrid-3to1-50b
(34b36f5b54a4f719b64d600d05cc4d58b0e14f6a0fa63c4ea1fede7b4fd56ef7, 5,732,906,548 bytes) and the Stage-D base
qwen3-1.7b-base (231d93ceda83766be8724d6eb37c48e97219f2fd3018cb64ec20860f88944321, 3,452,692,285 bytes);
transformer-2.7b-100b, delta-net-1.3b-100b and mamba-1.3b-100b are registered without receipts, and retnet, hgrn2, gsa,
the state-spaces triplet and pythia-2.8b are not registered.

Phase-0 doctor (CPU; needs neither the image nor a GPU and runs inside or outside the container):
`uv run python scripts/run_icl_rule_distillation_doctor.py --output data/results/icl-rule-distillation-port/phase0-doctor.json`
(receipt written at that path; data/results/ is git-ignored by repository convention, as for every doctor receipt, so
the run is identified by its payload sha256 cc8e8a12a844bfef7f2541cae41108fde03a95bdd68da8f0da61bdde967d921e and
implementation sha256 edfdc373f8b398d99ac55845eb9a7f404d1a8804f6fddc546252ddc6762135d7; numpy 2.5.2, scipy 1.18.0,
Python 3.13.14; C37). The receipt is written with an exclusive create, so a re-run is a new file, never an overwrite;
the evidence bundle must carry a hashed copy.

Slurm submission (single node, Docker lane, no Pyxis):

```bash
uv run python scripts/submit_docker_research_job.py experiments/architectures/icl-rule-distillation-port.yaml --dry-run
uv run python scripts/submit_docker_research_job.py experiments/architectures/icl-rule-distillation-port.yaml
# the submit script wraps: sbatch infra/slurm/host-single-node/docker-research.sbatch
```

Machine fields: `seeds: [42, 43, 44]`; `gpu_hours: 16` (envelope; decisive pilot 8.0; program 14.6); `gpus: 1` per job.

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
delta_net and mamba cards state no license (re-checked through the Hugging Face API on 2026-09-02 UTC, C28) and are
discovery-only, never counted in P2/K3, until confirmed (the registered delta-net-1.3b-8k carries the same blocker,
C21); startlux Apache-2.0; state-spaces and Pythia Apache-2.0; Qwen3 Apache-2.0; Moonshot MIT.
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
  suspiciously round effects or identical CIs across arms are flagged in the analysis script. Status today: PARTIAL.
  The CPU phase-0 doctor exits 0 with a hashed receipt (C37); its hand-written truncated-BPTT gradients are checked
  against central finite differences for every rung in the test suite, its ceilings are realised through the actual
  write code path by oracle rules rather than asserted analytically, and its causality audit is shown to catch a
  leaked probe; the model-side doctors have not run.
- Mode 2, hallucinated citation: every URL in this proposal was opened by a gauntlet cell at abstract or HTML level;
  status per claim in the Claim registry; Semantic Scholar batch verification was not possible (429).
- Mode 3, hallucinated experimental result: no experimental result about a model is reported anywhere in this proposal;
  the only executed numbers are the synthetic-case numbers of the phase-0 doctor (C37, C38), labelled as such wherever
  they appear and pointing to the receipt with its payload and implementation hashes. Any future number about
  a model must point to a run directory and manifest hash.
- Mode 4, shortcut reliance: the matched placebo (a) and the fidelity endpoint (b) exist because the wave-2 endpoint
  could be won by a shortcut (nonlinear rule on off-manifold shuffled inputs); the iso-parameter ladder and the written
  per-arm search exist because the wave-3 endpoint could be won by capacity or by an under-tuned baseline; the
  random-theta reservoir and the cross-teacher sibling rule out "any associative rule" and "any KL-distilled ICL rule";
  the w-clamp co-condition and the family-class requirement rule out unattributed and binding-only wins.
- Mode 5, bug reframed as insight: P4's dynamics signature is the most seductive result; it is admitted only if it
  replicates across the two ladders and survives the leave-one-family-out check. "Surprising" results are re-run from a
  fresh environment before reporting.
- Mode 6, methodology fabrication: every hyperparameter in this proposal must match the run manifest that the sbatch
  wrapper hashes; the Methods of any write-up are generated from the manifest, not written free-hand.
- Mode 7, frame-lock: the wave-3 rescope to portability-protocol is itself a frame correction; the pre-registered
  collapse (K6) and the bounded K1 reading prevent the study from being locked into an "architecture" story it cannot
  support. If Stage B yields K1, the study stops rather than escalating.

## Negative-Result Value

K1 gives a bounded behavioural result on an iso-ladder at 1.3B with two readings the ladder separates: at a 64-d rank-8
interface and matched capacity, the transformer's content-dependent in-context update is not distinguishable from a
gradient-form rule by fidelity to its own predictions and errors, and either a linear preconditioner suffices
(D(R_gf, R_lin) small) or a learned content-dependent preconditioner is needed (D(R_gf, R_lin) large, with R_adapt
saying whether the error map must be nonlinear). Reported per family class, it says which task classes admit which GD
description, a quantitative input to the ICL-as-GD debate (item 13) at a scale Shen et al. tested only with order and
output-distribution probes, and it empties Direction 16's premise for a few GPU-hours. K2 gives a measured floor: at
1.3B-1.7B, label-dependent ICL is confined to binding and function-induction families. K3 or MIXED gives the first
cross-family behavioural measurement of in-context update portability on licensed iso-ladder bases, with the read-path
ablation saying whether softmax carried it. A P3 null shows that the frozen encoder's language invariance alone explains
cross-lingual memory readout, closing the ttt-fastweights G4 question cheaply. K6 turns the study into a clean
replication of Fast Weight Layers on modern bases, with the added fact that a KL-distilled ICL rule is not
teacher-specific at this granularity. An UNATTRIBUTED outcome is itself informative: an iso-capacity fidelity gap that
neither the write direction nor the forgetting policy carries points at optimisation rather than structure.

**Strongest counter-argument to the whole direction.** Even a positive result may be "a better associative rule at a
convenient interface" rather than "the transformer's update": the iso-parameter ladder and the w-clamp co-condition
locate the win in a named structural degree of freedom, but only fidelity on teacher-wrong queries, order sensitivity
and the cross-teacher sibling tie the rule to this teacher, and all three are noisy at 400 queries. **What's missing** to
close that gap is a from-scratch matched arm in which the same rule is trained jointly with a small base, which the
rescope defers; a larger held-out family pool, which 1.3B bases do not offer; and measured rather than assumed noise
SDs, which only the Stage-B run provides.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS-candidate | Cell notes: research/gauntlet/2026-09-01-frontier/wave2/icl-rule-distillation-port.md (repair), wave2-result.json (three refuter votes with 63 evidence URLs, blind discrimination, two judges), wave3-result.json (two wave-3 reviewers, 61/57), wave1-ledger.md; sweep notes learned-update-rules.md, ttt-fastweights.md, adapter-portability.md, seq-operators.md, synthesis.md and the four verify-*.md notes; wave-4 WebFetch of 10 abstract pages and the Hugging Face API license re-check (C28). The evidence bundle named in the header (evidence/icl-rule-distillation-port/bundle.json) does not exist yet | Create the bundle; snapshot every primary URL with HTTP 200 and SHA-256 into it |
| Citation | PASS-candidate | Every number carries a URL and a status in the Claim registry (39 rows); C24 recomputed and C25 re-simulated in wave 4; C35-C39 added in wave 5 (rebuilt image and receipts as FIRST_PARTY reports from the brief, the doctor receipt and tree Monte-Carlo as VERIFIED synthetic computations, the registry state as VERIFIED in-repo); first-party items are marked; protocol claim_verification_protocol.md followed | Independent line-by-line citation audit; re-open C07, C13 tables; open Askell 2021's body; open the receipt files and docker inspect on the host to lift C35 and C36 from FIRST_PARTY |
| Novelty | PASS-candidate | Wave-2 novelty refuter did not refute (0.6); blind discrimination different mechanism (0.88); five wave-2-judge-named priors (items 8-12) and the five wave-3-reviewer-named groups (items 13-17, including the in-repo Direction 16 interface) added and discriminated; PRISMA-style counts recorded where they exist (C33); collision risk high | Signed provider-distinct novelty review after proposal freeze; Semantic Scholar and OpenReview body search when reachable; reconstruct wave-1 screening counts |
| Design | PASS-candidate | Contract experiments/architectures/icl-rule-distillation-port.yaml passes validate_architecture_experiments.py and now carries a reference_doctor block bound to harness/icl_rule_distillation.py and scripts/run_icl_rule_distillation_doctor.py; the phase-0 doctor executes on CPU and passes 66 of 66 registered gates (C37: positive control, Gaussian-prior negative control, permuted-teacher control, leaked-probe tamper, degenerate-input rejection, tree routing and power); pytest 17 passed including finite-difference gradient checks and two tamper cases; ruff clean; matched placebo, fidelity primary endpoint, iso-parameter gradient-form ladder with the re-tiered attribution tree (CLASS_UNRESOLVED, 4-family class minimum) and clamp co-condition, cross-teacher sibling, licensed-target P2/K3 with a MIXED outcome, written per-arm search, per-base gate, read-path ablation, six falsifiers, full-tree power (C38); protocols experimental-design/SKILL.md, statistical-power/SKILL.md, statistical_reporting_standards.md, devils_advocate_agent.md followed | Implement the model-side Stage-A doctors (TR-fidelity gate on real episodes, tokenizer identity, P/Q factorisation, loader smoke) and the analysis script for real runs; hash-freeze both |
| Compute | FAIL | No real model loop executed by this contract; the rebuilt image cotcodec-research:999f5583-architecture with fla 0.5.2 exists and is digest-pinned (C35) but tilelang is still being added and no container smoke, sbatch dry-run or fresh-job resume receipt exists for icl-rule-distillation-port; four of the pilot checkpoints carry fetched receipts (C36) and three registered ones do not; MFU assumed, not measured; the CPU phase-0 doctor (C37) is executed but is model-free by design; the wave-4 program estimate of 14.6 of 16 GPU-h leaves 1.4 GPU-h of slack | Finish the tilelang addition and re-pin; run the container smoke, the Stage-A throughput smoke and `submit_docker_research_job.py --dry-run` on the node; fetch receipts for transformer-2.7b-100b, delta-net-1.3b-100b and mamba-1.3b-100b; attest all of it in the bundle |
| Safety | PASS-candidate | Monitorability (hash-chained write log, reset attestation, poisoning probe), data rights (all licenses listed and re-checked on 2026-09-02; GT data license unknown and excluded; delta_net/mamba discovery-only and never counted), red lines, and the seven-mode integrity gate are specified | Runtime isolation and poisoning-probe evidence from a real run |

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=anthropic | model=claude (internal wave-4 reviewer 1, NOT provider-distinct, unsigned) | run_id=wave4-reviewer-1 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json

Reviewer B: FAIL | provider=anthropic | model=claude (internal wave-4 reviewer 2, NOT provider-distinct, unsigned) | run_id=wave4-reviewer-2 | artifact=research/gauntlet/2026-09-01-frontier/wave4-result.json

Both reviews are internal wave-4 reviewer scorecards from the same provider, unsigned and without a protected trust
root; the wave-2 judges (62/62, wave2-result.json) and the wave-3 reviewers (61/57, wave3-result.json) are retained in
the Iteration Log. They are recorded for traceability only; the Gauntlet requires two provider-distinct, Ed25519-signed
reviews, so the accepted score is capped at 89 and the proposal is NOT pilot-ready regardless of the scorecard below.
Both wave-4 reviewers filled the criterion-bound form: Reviewer A — Originality, Methodological Rigor, Evidence
Sufficiency, Literature Integration and Significance PARTLY_MEETS (the first four decision-bearing), Argument Coherence
and Writing Quality MEETS; Reviewer B — Originality, Methodological Rigor, Evidence Sufficiency and Literature
Integration PARTLY_MEETS (decision-bearing), Argument Coherence, Writing Quality and Significance MEETS; calibration
NOT_CALIBRATED for both. Both named the same fatal defect (nothing executable after four waves) and Reviewer B named the
mis-stated tree power; the wave-5 repair addresses both with executed code and a re-tiered tree, and syncs the contract
to the registry. Evidence Sufficiency and Reproducibility remain open until the bundle, the container smoke, the sbatch
dry-run and the model-side Stage-A attestations exist; Originality remains open until a signed provider-distinct novelty
review and the unsearched venues are covered.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 7 | 6 | Rule-as-object framing fits G5/G2/G6/G7; every arm is a frozen retrofit near the excluded strap-on class, so no architecture-level claim is reachable inside this contract; Kevin advantage partial (public substrate) |
| Primary-source evidence | 7 | 7 | 34-row registry at wave 4 with C24 and C25 replicated by Reviewer A; C07, C13 table-level numbers not re-opened; Askell 2021 unverified; C21 and the "not registered" sentences stale against registry commit 53773c3 (fixed in wave 5, C39); evidence bundle absent |
| Defensible novelty delta | 6 | 6 | Component confidences 0.50-0.65 with the interface explicitly not new; blind discrimination (0.88) dates from wave 2 and was not re-run after the ladder; bounded absences named by Reviewer A (model stitching / relative representations for the P/Q port, ICL distillation 2212.10670, differentiable plasticity and Titans as the learned-gate lineage, MOHAWK cross-architecture distillation) not yet added; unsigned |
| Mechanism and falsifiability | 7 | 7 | Two-pass structural causality and six kill criteria; Pi_8 truncation is a no-op for 8 rank-one writes from M = 0 (now asserted by the phase-0 doctor rather than advertised); the linear read path cannot express softmax's normalised competitive read, which makes K1 structurally likely |
| Controls and causal identification | 7 | 8 | Wave-4 ladder with R_gf decisive, cross-teacher sibling with a disagreement precondition, licensed-target P2/K3, written search credited by both; remaining defects: no pre-registered minimum function-induction count (added in wave 5: 4) and the post-hoc w-clamp on a co-adapted network attributes weakly (the synthetic doctor shows a 0.094 optimisation-only gap in a non-separating regime, so the regime precondition is now part of the code path) |
| Evaluation and statistics | 7 | 6 | Reviewer B: the stated 0.78 power belonged to one leaf; the class co-condition had power 0.21-0.48 and a miss routed to K1 (re-tiered in wave 5 with the full-tree Monte-Carlo, C38: CONFIRMED 0.39 / CLASS_UNRESOLVED 0.12 / INCONCLUSIVE 0.28 / K1 0.21 at a true 0.10 effect); noise SDs assumed, not measured |
| Feasibility and information per GPU-hour | 6 | 6 | MFU assumed at 25% for hooked eager passes where 10-15% is plausible (fallback stated); wave-4 program 14.6 of 16 GPU-h; retnet, hgrn2 and gsa unregistered so Stage C cannot be enabled |
| Reproducibility and artifact contract | 5 | 5 | Doctor FAIL with acceptedScore 0; header names a non-existent bundle; no code, no fla-pinned image, no Stage-A doctor at wave 4 (wave 5: CPU phase-0 doctor written and executed, rebuilt fla 0.5.2 image and four receipts cited, reference_doctor in the contract; bundle, smoke and dry-run still absent) |
| Safety, data rights, and monitorability | 8 | 8 | Write log, reset attestation, poisoning probe, licenses re-checked; GT data license unknown and excluded |
| Independent adversarial review quality | 6 | 6 | Internal, same-provider, unsigned reviewers only; criterion-bound form filled, NOT_CALIBRATED |
| **Total** | **66** | **65** | Lower total (65) is authoritative; wave-4 reviewer totals before the wave-5 repair; score history 62 → 62 → 57 → 65 is recorded, dip included; accepted Gauntlet score is 0 until the bundle exists |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 | Killed before judging: identification REFUTED (0.8; predicted effects not attributable to the transformer's distilled update; Pythia-160m gain within noise; derived rules undertuned; cross-operator sites on attention layers) and feasibility REFUTED (0.8; no data named; budget not credible); novelty not refuted (0.6). See research/gauntlet/2026-09-01-frontier/wave1-ledger.md row 5 | Repair owner rebuilt endpoint (r_TL), scale (1.3B iso-ladders), substrates, controls (R_GD superset, sibling, reservoir), data plan and FLOP ledger; kept the rule-as-object delta | Entered wave 2 |
| 2 | 62 | Primary endpoint r_TL not a matched placebo across R_theta (nonlinear, trained only on gold) and R_GD (linear in e_i): the P1 gap could be produced with zero content information; no TR-fidelity gate, no teacher-fidelity endpoint; eligibility gate on the source only; architecture-causal label without a from-scratch arm; inert adjacent-layer site factor | Judged only; both judges 62/62, identification 3/10; blind discrimination: different mechanism (0.88), prior does not dominate | Ranked 1 of wave 2; passed to spec with one repair allowed |
| 3 | 62 | Same as wave 2 (identification) | Applied the union of both judges' highest-impact fix as one identification repair: (a) teacher shuffled-label episodes in every rule's distillation stream plus a 0.05 TR-fidelity CI gate; (b) teacher fidelity on held-out families as the primary endpoint with error-agreement, per-step and order-sensitivity secondaries; (c) per-base eligibility gate; (d) claim rescoped to portability-protocol; (e) inert site factor replaced by a downstream-attention read-path ablation; (f) Jeong, FAAST, Sleep, Cross-model Control and ICLCA added and discriminated. Ledger updated (+1.2 GPU-h, program 12.3) | Judged in wave 3: 61/57 (lower authoritative 57), a 5-point dip from wave 2 |
| 4 | 57 | Wave-3 reviewers 61/57 (history 62 → 62 → 57, the dip is kept): the decisive control R_GD (about 4.1e3 parameters, linear in the error) against R_theta (about 1e5 parameters, free write) under the same KL loss was a nested-class contest with a 25x capacity gap, so a P1 win could not separate "not GD" from "not linear"; the CE-trained sibling could not tie on a fidelity endpoint, leaving K6 inert; P2 (4 of 6) versus K3 (0 of 6) left 1-3 of 6 unassigned while two of six targets have no license; no written per-arm hyperparameter search; the 8-cluster percentile bootstrap inflated Type-I; C24 stale and C25 mis-described; Direction 16's identical interface and the ICL-as-GD and write-rule-taxonomy literature absent | Applied the union of both reviewers' highest-impact fix as one identification repair: nested gradient-form ladder R_lin ⊂ R_adapt ⊂ R_gf ⊂ R_theta with R_gf (Reviewer B's iso-parameter nonlinear gradient-form rule) as the decisive control, chosen over Reviewer A's R_adapt because it is the larger gradient-form class at matched capacity and isolates the free write direction, with R_adapt kept as the attribution rung; pre-registered attribution tree with the w-clamp ablation and the function-induction class as required co-conditions of P1; K1 redefined against R_gf; cross-teacher KL sibling with a teacher-disagreement precondition replaces the CE sibling so K6 is live; P2/K3 closed on the four licensed targets (3 of 4 pass, exactly 2 MIXED, below 2 kill; licenses re-checked 2026-09-02 UTC); written per-arm search grid at equal development budget; two-sided t-interval on family means made decision-bearing after re-simulating C25 (power 0.78, Type-I 0.028; percentile bootstrap 0.060 demoted to a sensitivity) and recomputing C24; Direction 16 discriminated in the Novelty Ledger; ICL-as-GD lineage, MIRAS, test-time regression, Schlag 2021 and context distillation added after opening each abstract; PRISMA counts recorded where they exist. Ledger +2.3 GPU-h in B (program 14.6 of 16; decisive pilot 8.0) | Judged in wave 4: 66/65 (lower authoritative 65), up from 57 |
| 5 | 65 | Wave-4 reviewers 66/65 (history 62 → 62 → 57 → 65): both name the same fatal defect, nothing executable after four waves (no Stage-A code, no parameter-count doctor, no analysis script, no fla-pinned image, bundle absent, research_direction_doctor status FAIL with acceptedScore 0) plus a contract stale against models/registry.yaml (seven direction-19 ids registered in commit 53773c3 while the arms used stand-ins and the text said none was registered); Reviewer B: the tree's 0.78 power belongs to one leaf, the class co-condition has power 0.21-0.48 at 3-5 class families under the proposal's own noise model and a miss routes to K1, so the kill screen would falsely kill a true 0.10 effect more often than confirm it; Reviewer A: no pre-registered minimum function-induction family count | Applied the union of both reviewers' highest-impact fix as one executability repair: harness/icl_rule_distillation.py, scripts/run_icl_rule_distillation_doctor.py and tests/test_icl_rule_distillation_doctor.py written, linted, tested (17 passed) and executed (PHASE0_DOCTOR_PASS, 66 of 66 gates, 15.4 s, CPU, NumPy/SciPy only; C37) with a positive control in the dMMSE regime, a Gaussian-prior negative control, a permuted-teacher control, a leaked-probe tamper case, degenerate-input rejection, and the parameter-count, Pi_8 and clamp code-path doctors; all numbers labelled synthetic-case; attribution tree re-tiered (class point estimate ≥ 0.10 with a one-sided 80% lower bound above 0, at least 4 eligible function-induction families, CLASS_UNRESOLVED as a pre-registered non-kill, K1 on the primary leaf only) and the full-tree Monte-Carlo reported (C38); contract arms synced to the registered ids with the false "not registered" sentences removed (C39); rebuilt image cotcodec-research:999f5583-architecture (fla 0.5.2, triton 3.6.0; tilelang pending) and the fetched checkpoint receipts cited (C35, C36); reference_doctor block added to the contract; waves budget raised from 4 to 6 to cover this wave and one more | Not re-judged; score unchanged at 65 pending wave-5 review; Compute remains FAIL (no model loop, container smoke or sbatch dry-run attested); the evidence bundle still does not exist |

The accepted score remains zero until the hashed evidence bundle at evidence/icl-rule-distillation-port/bundle.json,
the protected trust root, two signed provider-distinct reviews, the tilelang-complete re-pinned pilot image, the Stage-A
container smoke and Slurm dry-run attestations, and the hash-chained audit JSONL exist. The wave-5 phase-0 doctor lifts
the "nothing executable" defect for the CPU part of Stage A only; it proves executability and gate semantics on a
synthetic regime and nothing about a pretrained model. A prose proposal cannot score itself upward; every PASS-candidate
above is a claim about what the evidence bundle must show, not a PASS.
