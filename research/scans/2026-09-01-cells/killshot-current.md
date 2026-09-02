# Kill-shot scan — CoTCodec current candidate directions (cell: killshot-current)

Date: 2026-09-01. Window of interest: prior art published or surfaced after 2026-08-10 (the last
sweep cutoff). Every finding below was opened at its primary source (arxiv.org/abs page, GitHub API,
or Hugging Face API) during this session; nothing is cited from memory. Dates are arXiv v1
submission dates unless noted. "First-party" = claims taken from the authors' own abstract/README;
"peer-reviewed" = venue acceptance stated by the authors on the primary page (EMNLP 2026, KDD 2026,
ICML 2026 workshops), not independently replicated by us.

Honesty statement: this is a bounded search under the coverage listed at the end. "No direct prior
found" always means "through 2026-09-01 under the coverage below", never global novelty.

## Executive verdicts

| Direction | Verdict | One-line reason |
|---|---|---|
| 16 Portable Sidecar Update Dynamics | STILL_OPEN (narrow) | Post-08-10 work occupies TTT inner-loop efficiency/design space and cross-model transfer of frozen memory/KV state via thin target-side maps; nobody evaluates a task-conditioned online sidecar rule on a held-out task x base cell. New mandatory neighbor: Cross-Model Memory Transfer (2608.17050). PorTAL baseline data has a newly reported label-position defect (issue #28). |
| 17 Causal Memory Holdout Trials | NARROWED | Hindsight Memory-PRM (2608.29605) now occupies intervention-calibrated per-entry memory credit ("one controlled deletion-and-reanswer per probe", no per-operation labels, no Monte-Carlo replay) as a proxy reward for memory management; SCM-based causal pathway tracing (2608.30198) and stage-wise controlled exposure evaluation (2608.30177) occupy causal analysis. Residual: prospective known-propensity assignment at first service + write-time-only covariates + paired replay oracle. New kill-risk: reward-SNR floor result (2608.10441) says learned per-instance acquisition routing never beat random and a matched-moment noise placebo reproduced >=100% of the oracle's apparent gain. |
| 18 Translation-Equivariant Byte Boundaries | STILL_OPEN | Closest new work supervises dynamic byte chunks toward a frozen subword LM's targets (When Tokenizers Fail, EMNLP 2026) — monolingual, not parallel-translation transport. Romanized pretraining (One Form, EMNLP 2026) is a cheap cross-lingual-parity baseline the pilot must beat. A pre-registered negative on sharing byte-level vocabularies (2608.28151) is a caution for shared-boundary claims. No translation-transported boundary-mass prior found. |
| Rollout-Value Operator Scheduling | NARROWED | Token-level dynamic operator routing under immediate LM loss is now densely occupied (LoGo 2608.29539, Switch Attention EMNLP 2026, NAtS-L, Mixture of Layers, HubRouter, Flux Attention). The uncited 2603.20997 shows content-based routing needs pairwise computation and segment-level routing reaches only 15-29% of token-level — a structural constraint on any scheduler. ITR (2608.18230) is an alternative non-immediate value criterion for compute allocation. No rollout-valued (full stateful continuation under measured latency/HBM) scheduler found. |
| Coded Delta Memory (diagnostic) | NARROWED | Interference measurement/erasure (QED 2608.13668), state-anomaly detection/neutralization (SANE 2608.22354), incremental capacity (Proteus 2608.16844), and redundancy-based KV repair (TwinKV 2608.27128) occupy the "detect and repair recurrent-state trouble" axis; no parity/erasure code with a syndrome inside DeltaNet state found after 08-10 (or before). SANE's norm-anomaly statistic is a free syndrome baseline the kill cell must beat. |

## Findings (all opened at primary source)

### Direction 16 — Portable Sidecar Update Dynamics

1. **Cross-Model Memory Transfer via Target-Side Reader Adaptation** — https://arxiv.org/abs/2608.17050 — 2026-08-17 — arXiv, first-party.
   Claim: Engram-style hashed memory trained on a source model is frozen and attached to a different target model with only a small target-side reader adapted; the paper asks whether the frozen memory or the target-side reader matters more for cross-backbone transfer.
   Occupies: cross-base portability of a learned external memory object with a thin per-base reader — the "portable object + light per-base alignment" factorization applied to memory.
   Relevance: closest post-08-10 neighbor to Direction 16's mechanism (portable state + base alignment); must enter the collision ledger and serve as the "static frozen-memory + reader" control against the online sidecar rule. Verdict anchor: STILL_OPEN (narrow) — it ports a static memory table, not an online task-conditioned update rule, and does not evaluate a held-out task x base cell.

2. **Rethinking Expressivity and Efficiency in Test-Time Training (E²-TTT)** — https://arxiv.org/abs/2608.21308 — 2026-08-21 (v2 2026-08-26) — arXiv, first-party; code https://github.com/zeyun-zhong/E2-TTT (created 2026-08-16), checkpoints zeyun-zhong/e2-ttt-{mlp,swiglu}-{340M,1.3B}-15B on Hugging Face (2026-08-30).
   Claim: under the standard chunk-start-gradient approximation, derives a closed-form state transition that exactly reproduces chunk-end fast-weight and momentum states of the per-token recurrence; models to 1.3B trained from scratch; on par with TTT/hybrid baselines on LM, better on in-context recall.
   Occupies: TTT inner-loop efficiency (chunk-parallel exact per-token dynamics).
   Relevance: a stronger native TTT control for D16's "native TTT update" baseline row; released 340M/1.3B checkpoints are directly usable as a source base.

3. **Modular TTT: Rethinking Test-Time Training as Composable Modules** — https://arxiv.org/abs/2608.07110 — 2026-08-07 (surfaced; code https://github.com/ByteDance-Seed/Modular-TTT created 2026-06-22, pushed 2026-08-10, 46 stars) — arXiv, first-party.
   Claim: represents the inner learner as a DAG exposing fast-weight network, loss, learning rate, weight decay, and normalization as explicit design dimensions and auto-composes train-view/query-view rules.
   Occupies: the factorized design space of TTT update rules.
   Relevance: D16's "portable network emits rho, eta, u, v" is a point in this design space; Modular TTT is the natural implementation substrate and a required citation; it does not study portability across bases.

4. **Fast Weight Attention for Continual Learning** — https://arxiv.org/abs/2608.27763 — 2026-08-27 — arXiv, first-party.
   Claim: studies the fast-weight state transition as an online learning rule under read-after-write semantics; derives normalized first-order updates (Falcon-1/2/3 and inner-product variants) for prefix-aligned pairs.
   Occupies: new hand-derived update-rule families for fast-weight memories.
   Relevance: additional "ordinary/analytic update rule" controls for D16; reinforces that the broad "new update rule" claim is occupied.

5. **portallib issue #28: TruthfulQA and SciQ gold answer is always at choice index 0** — https://github.com/ramp-public/portallib/issues/28 — 2026-09-01 — GitHub, third-party report against first-party data.
   Claim: at pinned revision d35f1e8a of RampPublic/portallib-tasks, 100% of truthfulqa (204 val / 613 train) and sciq (1,000 val / 11,679 train) rows have gold_idx == 0 because prepare_dataset.py never shuffles choices.
   Occupies: n/a (data-quality defect).
   Relevance: two of PorTAL's 14 tasks are position-exploitable; any D16 pilot using PorTAL's task set as the static-PorTAL baseline must re-shuffle or drop these tasks and re-run baselines. No portallib commits after 2026-07-27 and no release after v0.2.1 (2026-07-25) as of 2026-09-01.

6. **UpgradeBench: A Decision-Centric Benchmark for Upgrading Fine-Tuned LLM Specialists** — https://arxiv.org/abs/2608.20918 — 2026-08-21 — arXiv, first-party.
   Claim: longitudinal benchmark over four consecutive Qwen releases plus OLMo lineage, six tasks, two sizes; asks whether specialization assets transfer across versions and what recovery resources are usable.
   Occupies: evaluation protocol for "port vs retrain" adapter decisions across base-model releases.
   Relevance: the natural external-validity ladder for any portable-adaptation claim (PorTAL-style or D16); it evaluates static adapters, not online update rules.

7. **A Universal Context-Reuse Layer for Cross-Model KV Sharing** — https://arxiv.org/abs/2608.30963 — 2026-08-31 — arXiv, first-party (see also Cross-Model KV Cache Transfer in LLM Families, https://arxiv.org/abs/2608.03893, 2026-08-04: closed-form ridge mapper, one source layer explains 56% of target key variance on Qwen3 14B->32B).
   Claim: translates KV state from a source model into a representation consumable by a different target model across scale, architecture, tokenizer, and family; Qwen2.5-7B -> 1.5B raises LongBench2 from 27.59% to 34.48%.
   Occupies: thin learned maps that port activations/state across bases.
   Relevance: the "task-blind, capacity-capped base alignment" in D16 has a cousin in KV-translation layers; a KV-translation control (port the state, not the rule) belongs in the baseline table.

8. **Test-time training and the write-in / read-out of new knowledge in small language models** — https://github.com/sxewc/ttt-knowledge-writein-readout — 2026-08-09 (repo) — GitHub, first-party, no paper found.
   Claim: parameter-efficient TTT on a frozen base reliably drives a large write-in signal (gold-token rank collapse, several nats of log-prob gain) while read-out QA accuracy stays at floor; a double dissociation across layer band, training stream, and update budget.
   Occupies: negative evidence on TTT-style feedback injection producing usable behavior.
   Relevance: supports D16's insistence on freezing one feedback encoding and measuring prequential action accuracy rather than write-in metrics; unreviewed, single-repo evidence.

Also surfaced (not in repo): third-party PorTAL derivatives on Hugging Face — devingupta/portal-ablate-sum5-{1.7b,4b,8b-refit} and portal-search-4b (2026-08-10/11), manihani4/portal-vlm-* (2026-08-02, PorTAL applied to VLMs); Ramp's HF org has no artifacts after 2026-07-25.

### Direction 17 — Causal Memory Holdout Trials

9. **Hindsight Memory-PRM: Supervising Memory Management with Auditable Hindsight Credit** — https://arxiv.org/abs/2608.29605 — 2026-08-30 — arXiv, first-party. Verdict anchor: NARROWED.
   Claim: exploits retrieval hits and answer-time citations twice — offline to train an operation-conditioned memory-utility critic, and online where "one controlled deletion-and-reanswer per probe" settles an intervention-calibrated entry-level presence credit propagated along version chains as an action-level proxy reward, with no per-operation human labels and no Monte-Carlo replay; 8B policy reaches 77.5% on held-out LoCoMo vs API teacher 65.1%, 79.0% on LongMemEval.
   Occupies: intervention-calibrated per-entry memory credit as a training signal; "auditable hindsight credit" wording; operation-conditioned utility critics.
   Relevance: kills any "first intervention-calibrated item credit for memory management" wording. It intervenes at answer time (post-hoc, query-conditioned deletion), so it does not identify a prospective first-service effect and its critic is operation-conditioned rather than write-time-only. D17 must add it as a mandatory control and explicitly contrast prospective known-propensity assignment vs post-hoc deletion probes.

10. **When Errors Become Memories: Causal Pathway Tracing in Multi-Turn Memory-Augmented LLMs** — https://arxiv.org/abs/2608.30198 — 2026-08-31 — arXiv, first-party.
   Claim: an SCM over questions, responses, and memory states; intervenes on two entry pathways (internal memory updating, external question feedback) to build four counterfactual trajectories and quantify downstream effects and interaction at four levels.
   Occupies: interventional/counterfactual analysis of memory error propagation.
   Relevance: occupies "causal analysis of memory effects" as an evaluation object; does not learn a service policy or randomize serving. Cite as the causal-analysis neighbor.

11. **Understanding Stage-Wise Utility-Risk Trade-offs in LLM Agent Memory (MemGauge)** — https://arxiv.org/abs/2608.30177 — 2026-08-31 — arXiv, first-party.
   Claim: separately varies writing admission, management policy, and retrieval exposure under matched clean and poisoned conditions across 11 LLMs and two benchmarks; finds a threshold-like risk transition during writing and coupled utility/risk growth during retrieval exposure.
   Occupies: controlled stage-wise exposure evaluation of memory pipelines.
   Relevance: an exposure-manipulation framework, but at the configuration level, not randomized item-level assignment; useful template for D17's safety-by-arm reporting.

12. **Detecting an Effect Is Not Learning to Act on It: A Reward-SNR Floor for LLM Acquisition Agents** — https://arxiv.org/abs/2608.10441 — 2026-08-11 — arXiv, first-party.
   Claim: even when an acquired auxiliary signal helps on average and an in-sample oracle shows sizable gains, learned per-instance acquisition routing never beat random across per-impression, cluster, regime, and uplift-tree granularities; a matched-moment noise placebo reproduced >=100% of the oracle's apparent gain; a reward-SNR floor governs learnability.
   Occupies: a general identification limit on learning when to use an acquired signal.
   Relevance: direct kill-risk for D17's write-time gate — the paired oracle can show a true average effect while no deployable gate can learn per-item timing. The Gauntlet proposal must add a matched-moment noise-placebo control and a reward-SNR estimate as pre-registered gates.

13. **Coverage, Not Credit: Failure-Credit Routing of Zeroth-Order Perturbation Budgets Does Not Improve On-Pool Sample Efficiency for LLM Agents** — https://arxiv.org/abs/2608.28011 — 2026-08-28 — arXiv, first-party negative result.
   Claim: across synthetic environments and frozen Qwen2.5-1.5B/3B and SmolLM2-1.7B agents, six allocation schemes, paired seeds, and sign-flip tests, credit-routed perturbation budgets showed no statistically detectable improvement over uniform allocation (no gain >= 2 points); inverse-propensity debiasing did not rescue routing.
   Occupies: negative evidence that trajectory-level credit should drive budget allocation.
   Relevance: another credit-does-not-help-allocation negative; supports D17's requirement that the learned gate beat random/uniform under matched budget.

14. **Utility Under Attack: Agent Memory Poisoning and the Limits of Content Screening and Provenance Ranking** — https://arxiv.org/abs/2608.21230 — 2026-08-21 — arXiv, first-party.
   Claim: poisoning 1.2% of a LongMemEval corpus with plain false assertions drops accuracy from 0.850 to 0.300; a four-stage write-time screener rejects 0 of 360 poisoned memories; shipped provenance weighting is indistinguishable from no defense (p=0.80).
   Occupies: limits of content-only and provenance-weighted defenses.
   Relevance: D17's write-time covariates include source/provenance; this result says provenance alone will not carry a safety endpoint, consistent with the TMA-NM origin-binding requirement already in the direction file.

15. **Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents** — https://arxiv.org/abs/2608.15008 — 2026-08-15 — arXiv, first-party.
   Claim: controlled harness over dense/sparse indices, text records, structural and hierarchical stores, refinement memories, parametric updates, and activation-compatible mechanisms; three backbones, four suites, 26 metrics; no single substrate dominates.
   Occupies: substrate-level matched evaluation.
   Relevance: supports D17's matched-control policy; the substrate is orthogonal to the first-service estimand.

16. **The Retriever Should Remember: Experience-Amortized Reranking (EARM)** — https://arxiv.org/abs/2608.22767 — 2026-08-24 — arXiv, first-party.
   Claim: stores sparse query-memory LLM relevance scores in an online matrix and completes it via causal matrix completion to rerank under a fixed scoring budget.
   Occupies: retrieval-time experience reuse; "causal" here refers to matrix completion, not treatment effects.
   Relevance: a query-time learned control, not a prospective service-effect estimator.

17. **ContextPilot: Teaching Agents for Proactive Context Management via Fine-grained RL** — https://arxiv.org/abs/2608.28476 — 2026-08-28 — EMNLP 2026 main (peer-reviewed per abstract).
   Claim: RL for proactive context management with fine-grained credit assignment to context-editing actions instead of trajectory-level reward.
   Occupies: action-level credit for context/memory edits via RL.
   Relevance: mandatory RL controller control; still trajectory-derived credit, not randomized item exposure.

18. **Memory Reward Inflation in Self-Improving LLM Agents (Echo Gap)** — https://arxiv.org/abs/2608.00017 — 2026-06-29 (surfaced; not in repo) — arXiv, first-party.
   Claim: LLM-assessed stored scores act as proxy rewards; incorrect episodes receive inflated rewards and errors compound through memory rather than averaging out.
   Occupies: failure analysis of LLM-scored memory utility.
   Relevance: motivates D17's executable-utility outcome; cite for why reflection/LLM-score controls are expected to fail.

Already in repo (confirmed present, no new delta): RoMeRL 2608.02508, GPM 2608.12476, LycheeMemory V2 2608.12990, ERSkill 2608.12720, ReFind 2608.12888, Router-Mem 2608.01285, Consolidator 2608.11701, MARCH 2608.12435, Controlled Memory Interference 2608.07622, Dependency-Guided Rollback 2608.10502, Formal Definition of Agent Memory 2608.11654, Total Recall at What Cost 2608.11879, MemHarness 2607.28272.
Not in repo, opened, judged adjacent-only: Explicit State Elicitation Is Not Enough 2608.17247 (audit protocol with a 160-example counterfactual set), Cost-Utility Alignment 2608.26195 (attribution survey), AUDITA 2608.22160 (certified causal attribution in MAS), DreamLedger 2608.23863 (execution-settled credit gating for world-model predictions in robotics — conceptually a "credit file" gate, not memory items), Privileged Likelihood Is Not Automatically Value 2608.09263 (token-credit checks), CaSKG 2608.25500 (counterfactual probes to calibrate skill-graph edges), StateMemBench 2608.19652, MemoryLake on MemoryArena 2608.13883, A Storage-Retrieval Gap in Parametric KG Memory 2608.25489, InjecMEM 2608.23471, MemToC 2608.26295, Dual-Layer Agentic Memory 2608.22215, Weighted Memory Tree 2608.20631, Remember/Verify/Ask 2608.19564, RENDER 2608.23568, UTILMEM 2608.30508, HiPS 2608.25329 (EMNLP 2026), D²ACCI 2608.17756, Structurally Indirect Prerequisite Eviction 2608.20400.

### Direction 18 — Translation-Equivariant Byte Boundaries

19. **When Tokenizers Fail: Byte-Level Chunking for Zero-Shot Transfer to Low-Resource Languages** — https://arxiv.org/abs/2608.27658 — 2026-08-27 — EMNLP 2026 (peer-reviewed per abstract). Verdict anchor: STILL_OPEN.
   Claim: an adapted hierarchical byte network initializes byte embeddings from a frozen subword LM and applies a chunk alignment loss projecting dynamically grouped byte chunks toward precomputed subword targets, enabling zero-shot transfer to script-sharing low-resource languages without massive training.
   Occupies: external supervision of dynamic byte-chunk formation/representation by a frozen subword tokenization target (monolingual).
   Relevance: the nearest post-08-10 neighbor to "supervise where a tokenizer-free model forms boundaries"; it uses subword targets in one language, not parallel-translation transport across languages, so D18's boundary-transport delta survives but the "first supervised dynamic byte boundaries" wording does not.

20. **What Tokens are Learned when Tokenization is Optimized Jointly with Language Modeling?** — https://arxiv.org/abs/2608.17325 — 2026-08-18 — arXiv, first-party.
   Claim: across 18 typologically and script-diverse languages, jointly optimized tokenization (SSLMs, H-Nets) alters token structure; H-Nets prioritize byte-level efficiency with longer tokens and very low overlap with subword vocabularies; agglutinative languages show more dynamic segmentation.
   Occupies: cross-lingual analysis of learned dynamic segmentation.
   Relevance: predicts that entropy/H-Net-style boundaries diverge from linguistic units per typology — the motivating gap for translation-aligned boundaries; also the natural diagnostic protocol for D18's "aligned-boundary" metric.

21. **One Form to Transfer Them All: Pretraining Multilingual Language Models Beyond Native Orthography** — https://arxiv.org/abs/2608.25904 — 2026-08-26 — EMNLP 2026 main (peer-reviewed per abstract).
   Claim: controlled autoregressive pretraining at 467M/709M/1.03B over eight languages in four typological pairs; romanized pretraining yields the strongest cross-lingual transfer and the advantage widens with scale; IPA beats orthographic text in most settings.
   Occupies: script equalization as the cross-lingual transfer lever.
   Relevance: a cheap "input-representation" baseline that D18's parity claim must beat at matched compute; add romanized-input BPE Transformer as a sixth arm.

22. **Nested Byte-Level Vocabularies Are Cheap to Deploy and Expensive to Share: A Pre-Registered Negative Result** — https://arxiv.org/abs/2608.28151 — 2026-08-28 — arXiv, pre-registered negative result, first-party.
   Claim: 30 models (3.1M/10.6M bodies, 200M tokens); slicing is bit-exact and removes 66% of deployed weights, but a shared multi-size model trails a fixed-cap specialist by 3.64% bits per byte at 32k (1% margin) and 2.96% at 8k (2% margin).
   Occupies: negative evidence that one model sharing several byte-level vocabulary granularities pays a BPB tax.
   Relevance: caution for D18's shared-boundary claim — sharing compute units across languages may cost BPB; D18's falsifier "bits per byte worsens enough to erase the task gain" gets a concrete magnitude to pre-register against.

23. **Vowel Signs Are Not Letters: A Pre-tokenization Ceiling on Multilingual Tokenizer Fertility** — https://arxiv.org/abs/2608.26449 — 2026-08-26 — arXiv, first-party.
   Claim: GPT-2's \p{L}+ pre-tokenizer splits abugida words at every vowel sign; a training-free fertility lower bound affects all 17 abugidas in a 26-language parallel corpus (1.47x Tibetan to 9.02x Thai) while Latin/Cyrillic/Hangul/Han are 1.00x.
   Occupies: pre-tokenization artifacts in byte-level BPE parity measurements.
   Relevance: D18's BPE control must use a fixed pre-tokenizer, else parity gaps are artifacts; Korean (Hangul) is unaffected, Thai-class scripts would be.

24. **OmniAlign: A Unified Multilingual Aligner for Word and Sentence Alignment** — https://arxiv.org/abs/2608.18474 — 2026-08-19 — arXiv, first-party (see also CTFAlign/MDPAlign, https://arxiv.org/abs/2608.21023, EMNLP 2026 main, document-level training-free word alignment).
   Claim: one lightweight encoder-only model performs word-level alignment from contextual token similarity and m-n sentence alignment via embeddings plus dynamic programming.
   Occupies: multilingual aligners (enabler, not collision).
   Relevance: candidate frozen aligners for D18's weighted span links; two independent 2026 aligners reduce aligner-choice risk.

25. **EntropyMoE: Entropy-Aware Sparse Expert Routing for Tokenizer-Free LLMs** — https://arxiv.org/abs/2608.06398 — 2026-07-31 (surfaced; not in repo) — arXiv, first-party.
   Claim: replaces dense FFNs in the global patch Transformer with top-k experts routed directly from patch entropy, with byte coverage in workload accounting.
   Occupies: using the patch-entropy signal to allocate compute beyond boundary formation.
   Relevance: shows entropy-derived compute allocation is being extended; D18's claim must stay on boundary formation, not "entropy-aware compute".

Also opened: Dynamic Multi-Byte Prediction 2608.15454 (speed), ReconSpan 2608.12756 (reconstruction-guided latent tokenization), Adaptive Targeted Dynamic Chunking 2605.30080 (pre-cutoff, not in repo; curriculum on compression ratio), Equity with Efficiency 2606.15044 (pre-cutoff, not in repo; Parity-aware BPE on the efficiency-equity Pareto frontier in 11 SEA languages at 1.5B — independent support for D18's fair-BPE control), Tokenization Premium 2608.09046, Writing-System-Level Tokenizer Adaptation 2608.00582, ACTD cross-tokenizer distillation 2608.29662, Tokenization as the Hidden Variable 2608.26319, H-Net++ 2508.05628 (2025; Persian; 73.8% F1 on gold morphological boundaries — not in repo). No withdrawal or version change for BLT (v1 only), H-Net (v2 2025-07-15), Titans (v1); Parallel Tokenizers has a v2 (2026-07-27).

### Rollout-Value Operator Scheduling

26. **LoGo: Token-Level Dynamic Local-Global Attention** — https://arxiv.org/abs/2608.29539 — 2026-08-30 — arXiv, first-party. Verdict anchor: NARROWED.
   Claim: each layer has coupled local and global branches; all tokens get local attention and a learned gate activates full-context attention only for tokens needing long-range information, using span as the budget proxy.
   Occupies: token-level dynamic allocation between cheap and expensive attention operators trained with the ordinary LM objective.
   Relevance: together with Switch Attention, NAtS-L, Mixture of Layers, HubRouter and Flux Attention, per-token operator choice is occupied; what remains unclaimed is valuing full stateful continuations under measured latency/HBM instead of the immediate loss.

27. **When Does Content-Based Routing Work? Representation Requirements for Selective Attention in Hybrid Sequence Models** — https://arxiv.org/abs/2603.20997 — 2026-03-22 (v2; pre-cutoff but absent from repo) — arXiv, first-party.
   Claim: 20+ controlled experiments (200K-1.4B, 15+ routers); every high-precision router uses pairwise token comparison; recurrent models (Mamba-1.4B 29%), memory banks (12%), bandits (0.7-3.6%), contrastive pretraining (1.6%) all fail; bidirectional Mamba + pairwise comparison reaches 99.5%; segment-level routing achieves only 15-29% of token-level.
   Occupies: identification/feasibility limits of operator routing.
   Relevance: a structural kill-risk for any cheap scheduler — the router itself needs pairwise compute, and segment-level scheduling (the natural granularity for latency/HBM accounting) is much weaker. Must be cited and its protocol reused.

28. **Switch Attention: Towards Dynamic and Fine-grained Hybrid Transformers** — https://arxiv.org/abs/2603.26380 — 2026-03-27 (v3 online 2026-08-29) — EMNLP 2026 main (peer-reviewed per abstract).
   Claim: per-token, per-layer routing between full attention and sliding-window attention replacing static alternating hybrid patterns.
   Occupies: fine-grained dynamic hybrid routing (peer-reviewed).
   Relevance: the peer-reviewed occupant of dynamic operator routing; mandatory baseline.

29. **Allocating Recurrent Compute in Looped Language Models** — https://arxiv.org/abs/2608.18230 — 2026-08-18 — arXiv, first-party.
   Claim: values an additional recurrent application by whether it exposes a new cross-position influence direction observable at the readout (Iterative Transport Rank, marginal ITR); MixerLoop repeats Gated DeltaNet mixers while applying the FFN once; compared at 15M and 110M.
   Occupies: a non-immediate-loss value criterion for compute allocation in recurrent/looped models.
   Relevance: closest thing found to "value the continuation rather than the next-token loss"; different object (depth loops) but its ITR statistic is a candidate value signal or control for a rollout-value scheduler.

30. **Sliding-window beats linear attention** — https://arxiv.org/abs/2608.28444 — 2026-08-28 — arXiv, first-party negative/comparative.
   Claim: sliding-window attention with sinks performs as well as or better than post-trained linear-attention retrofits across multiple LLMs and tasks including NIAH.
   Occupies: negative evidence for the linear-attention operator arm in retrofit settings.
   Relevance: any operator scheduler that includes linear/delta recurrence must show it beats SWA-with-sinks at matched cost; otherwise the scheduling problem collapses to local/global attention (LoGo/SwiAttn territory).

31. **The Mask Is Not the Model: Auditing Prefix Invariance in Attention, State-Space, and Hybrid Sequence Models** — https://arxiv.org/abs/2608.22876 — 2026-08-24 — arXiv, first-party.
   Claim: a two-forward-pass audit localizes causality leaks per layer; in 192 injected-fault trials on eight checkpoints mask inspection detected none while the audit localized 192/192; found and fixed an inter-chunk axis defect in Zamba2 and Nemotron-H chunked scans.
   Occupies: causality auditing for hybrids.
   Relevance: after the SR-TTT retraction lesson already in the program, this audit should be a mandatory doctor for every hybrid/operator experiment (Directions 16, coded delta, operator scheduling).

Also opened: Qwen3.8-Next architecture report 2608.30320 (2026-08-31; layer-wise GDN + 1-in-4 attention later replaced by Qwen Sparse Attention; operator mix static), HARTS 2608.28158 (systems for RL rollouts over hybrid-attention models), VI-MoLE 2608.02528 (certified value-of-information routing with counterfactual risk for LoRA experts — occupies "value-of-information routing" wording), Thinking Hard Not Smart 2608.07968 (models fail to ration shared test-time compute), Mixture of Layers 2605.09516, NAtS-L 2602.03681 (in repo), HubRouter 2604.22442 (retrofit reported as a negative case), Flux Attention 2604.07394, Raven 2607.25357, DART 2608.02032, Linear Attention Architectures 2607.07953, Massive Activations in Hybrid Linear Attention 2608.12149, Gated Recurrent Transformers 2608.15062 (title only). Cacheable by Design 2608.18261 is a pre-registered negative on training MoE routers for locality (adjacent to latency-aware routing).

### Coded Delta Memory (diagnostic)

32. **SANE: State Anomaly Neutralization for Stable Extreme-Context Delta-Rule Models** — https://arxiv.org/abs/2608.22354 — 2026-08-23 (v2 2026-08-25) — arXiv, first-party. Verdict anchor: NARROWED.
   Claim: tracking RWKV-7 to 100M tokens reveals localized norm explosion atop a sparse substrate rather than global saturation; adaptive tanh compression at chunk boundaries (alpha in [3,5]) matches baseline on 11 short-context benchmarks while stabilizing extreme-context extrapolation.
   Occupies: detecting and neutralizing anomalous entries inside delta-rule recurrent state.
   Relevance: a norm-anomaly statistic is a free "syndrome" the coded-delta kill cell must beat; the failure geometry (few channels accumulate extreme values) is also exactly the correlated-multi-block regime that breaks a single-erasure code assumption.

33. **The Query Knows What to Forget: A Second Erase Direction for Linear Attention (QED)** — https://arxiv.org/abs/2608.13668 — 2026-08-13 — arXiv, first-party.
   Claim: adds a query-derived erase direction orthogonal to the key in Gated DeltaNet-2, cancelling old-state content measured along the query; improves retrieval past the training window and about doubles usable context on S-NIAH-1.
   Occupies: interference measured through reads and corrected by an extra erase direction.
   Relevance: occupies "measure interference inside the state and act on it"; the coded-delta syndrome must show detectability beyond what a query-side interference measurement already gives.

34. **TwinKV: A Composable Repair Pass for KV Cache Eviction via Pairwise Key Redundancy** — https://arxiv.org/abs/2608.27128 — 2026-08-27 — arXiv, first-party.
   Claim: a leave-one-out probe finds attention magnitude unrelated to a token's causal contribution (Spearman rho = -0.004); a training-free pairwise key-redundancy signal identifies orphaned evictions and composes with existing policies as a repair pass.
   Occupies: redundancy-based detection/repair in KV memory; causal-contribution probing of memory entries.
   Relevance: redundancy as a repair signal is occupied for KV caches; the coded-delta cell's redundancy must be about recurrent state and must report the same leave-one-out causal audit.

Also opened: Proteus 2608.16844 (incremental memory activation to reduce interference), DAMP 2608.27513 (quantization error energy concentrated in a small subset of state entries), DeltaLog 2608.15533 and DASC 2608.30386 (serving-side recurrent-state handling), Dynamic Compression in Recurrent Networks 2608.17896, Tensor Cache 2605.22884 and Echo 2605.06997 (pre-cutoff, not in repo). The date-filtered arXiv query for error-correcting/erasure/parity/syndrome x (associative memory | KV cache | recurrent state | linear attention | Hopfield) returned only GraniKV 2608.15584 and a superconducting-qubit paper: no coded recurrent-state memory after 2026-08-10.

## Occupied axes (post-08-10 or newly surfaced)

| Axis | What is taken | Primary URLs |
|---|---|---|
| Token-level dynamic operator/span routing under immediate LM loss | Learned per-token gates choosing local vs global or linear vs softmax attention; peer-reviewed occupant exists | 2608.29539, 2603.26380, 2602.03681, 2605.09516, 2604.22442, 2604.07394 |
| Identification limits of content-based routing | Routers need pairwise comparison; segment-level routing 15-29% of token-level | 2603.20997 |
| Intervention-calibrated per-entry memory credit as training signal | Answer-time deletion-and-reanswer probes settle entry credit propagated along version chains; operation-conditioned utility critic | 2608.29605 |
| Causal/counterfactual analysis of memory pipelines | SCM-based pathway interventions; stage-wise controlled exposure evaluation | 2608.30198, 2608.30177, 2608.17247 |
| TTT inner-loop design space and efficiency | Composable inner learners; exact chunk-parallel per-token dynamics; future-utility TTT objective; analytic fast-weight update families | 2608.07110, 2608.21308, 2608.01672, 2608.27763 |
| Cross-model transfer of frozen memory / KV state via thin target-side maps | Frozen hashed memory + adapted reader; closed-form and learned KV translation across sizes and families | 2608.17050, 2608.03893, 2608.30963 |
| Externally supervised dynamic byte chunking; entropy-routed byte compute; script equalization | Chunk alignment loss to frozen subword targets; patch-entropy expert routing; romanized pretraining for transfer | 2608.27658, 2608.06398, 2608.25904 |
| Interference detection/erasure and anomaly neutralization in delta-rule state; redundancy-based KV repair | Query-derived erase direction; norm-anomaly tanh compression; pairwise key redundancy repair | 2608.13668, 2608.22354, 2608.27128 |

## Open gaps (searched for and not found)

1. Prospective, known-propensity randomization of one retained memory item at its first eligible service, with write-time-only covariates and a paired deterministic replay oracle. Searched: arXiv API date-filtered (memory AND agent AND causal|randomized|counterfactual|propensity|credit assignment: 26 hits, none matching), HF papers x2, OpenAlex x2, WebSearch x2, 150+ August memory titles. Closest: Hindsight Memory-PRM (post-hoc deletion), SMSR/AttriMem (in repo). Kevin advantage: deterministic Docker/Slurm replay harness and the existing causal_memory_trials.py spine; Tinker for the Stage-2 controller. Caveat: 2608.10441's reward-SNR floor must be pre-registered as a gate.
2. Parallel-translation (unbalanced optimal transport) supervision of BLT/H-Net boundary mass across aligned spans. Searched: arXiv API x4 (byte+patch, tokenizer-free, tokeniz*+multilingual, OT+alignment+language), HF papers x4, OpenAlex x2, WebSearch x2, ~80 August tokenization/byte titles. Closest: When Tokenizers Fail (subword targets, monolingual), ReconSpan. Kevin advantage: General Translation parallel data and terminology sets; 8xH100 for the 20M-125M matched grid.
3. Task-conditioned online sidecar update rule with task-blind cross-operator alignment, evaluated on a sealed held-out task x base cell. Searched: arXiv API x2, HF papers x3, OpenAlex x3, GitHub x3, WebSearch x2, D16 title sweep. Closest: Cross-Model Memory Transfer (static memory + reader), Modular TTT, PorTAL. Kevin advantage: pinned Qwen3-0.6B-Base + Mamba-130M pair; Tinker access to Kimi/Qwen/GLM for a scale-only base; portallib baselines (after fixing issue #28).
4. A rollout-valued operator scheduler (value full stateful continuations under measured latency/HBM) rather than immediate-loss token routing. Searched: arXiv API (rv_router 124 hits, rv_mod 0), HF papers x2, OpenAlex x2, WebSearch x2, routing title sweep. Found only immediate-loss routers and ITR for looped depth. Kevin advantage: measured latency/HBM ledger on 8xH100 with Slurm; but 2603.20997 and 2608.28444 make this a high-collision, feasibility-constrained gap.
5. A parity/erasure code with an explicit syndrome inside DeltaNet recurrent state. Searched: arXiv API cd_coded (2 irrelevant hits), cd_delta (12 hits, none coded), HF papers x2, OpenAlex x1, coded-keyword title sweep. Kevin advantage: none unique; retain only as a negative-result cell with SANE and QED as controls.

## Queries run (98 distinct; modality in brackets)

WebSearch (10 executed before the session budget was exhausted): "Byte Latent Transformer" multilingual patch boundaries parallel data alignment 2026; LLM agent memory randomized exposure causal effect propensity holdout 2026 arXiv; PorTAL portable task adaptation Ramp follow-up portable LoRA generation across base models 2026; arXiv August 2026 "test-time" adaptation "cross-model" transfer learned update rule frozen backbone sidecar; arXiv 2026 dynamic patching byte-level language model cross-lingual "patch" boundaries alignment translation supervision; "memory" agent "randomized" "propensity" OR "inverse propensity" retrieval effect estimation 2026 arXiv agentic memory value; arXiv 2026 learned router chooses between softmax attention and linear attention per token OR per segment hybrid "operator" routing lookahead value; "erasure" OR "error-correcting" code recurrent state OR "KV cache" OR "associative memory" transformer 2026 arXiv parity syndrome; H-Net dynamic chunking multilingual follow-up 2026 arXiv hierarchical byte model cross-lingual chunk boundaries; "Mixture-of-Depths" OR "Mixture-of-Recursions" router trained with rollout OR "future loss" OR "lookahead" instead of immediate loss 2026. (Ten further WebSearch queries were refused: budget 200/200.)

arXiv API (15, all with submittedDate:[20260810 TO 20260901] unless noted): d18_byte_patch; d18_tokfree; d18_tok_multi; d18_ot; d17_mem_causal; d17_mem_agent (100 max); d16_learned; d16_hyper; rv_router; rv_mod; cd_coded; cd_delta; d18_blt_all (no date filter); d16_portal_all (no date filter); neg (retract*/negative result/fail to replicate/null result AND LM). Exact encoded strings are in scratchpad/sweep/axbatch.sh and axbatch.out.

Hugging Face papers search (20, filtered to publishedAt >= 2026-08-01): byte-level dynamic patching multilingual cross-lingual boundaries; tokenizer-free hierarchical dynamic chunking; tokenization parallel corpus cross-lingual alignment optimal transport; agent memory causal credit assignment randomized memory value; LLM agent long-term memory management RL retrieval policy; learned optimizer meta-learning update rule LM adaptation; test-time training fast weights LM; hypernetwork LoRA generation cross-model transfer portable adapters; hybrid attention router linear/softmax token-level routing; mixture of depths adaptive computation routing rollout value inference cost; error-correcting code associative memory recurrent state redundancy; DeltaNet linear attention memory interference capacity erasure; KV cache erasure coding fault tolerance serving; negative result replication failure LM memory TTT; randomized holdout memory item serving agent causal effect write-time policy; translation supervised segmentation byte boundaries parallel data tokenizer-free; portable update rule transfer across base models meta-learned sidecar frozen LLM; routing between attention and state space operators trained with rollout value latency; Byte Latent Transformer multilingual language parity patch length; unbalanced optimal transport word alignment.

OpenAlex (14, from_publication_date 2026-08-10 unless noted): byte latent transformer patch (from 08-01); agent memory causal randomized counterfactual credit; byte-level tokenizer-free patch boundaries multilingual; learned optimizer meta-learned update rule LM; hybrid attention routing linear attention token-level router; error-correcting associative memory recurrent state parity; test-time training LM fast weights; LoRA hypernetwork cross-model transfer adapters; tokenization cross-lingual parity optimal transport alignment (0 hits); DeltaNet gated delta rule recurrent state; memory holdout randomized serving propensity agent (1 irrelevant hit); byte patch boundary translation aligned multilingual tokenizer-free; mixture of sequence operators routing attention recurrence budget; retraction correction LM memory results.

GitHub repo search (14): byte latent transformer; agent memory causal; portallib; hybrid attention router linear attention (0); hnet dynamic chunking; agent memory created>2026-08-10; memory causal credit agent LLM created>2026-06-01; token-level hybrid attention routing (0); learned optimizer language model 2026 (0); erasure coded KV cache (0); cross-lingual tokenizer alignment parallel (0); test-time training created>2026-08-01; tokenizer-free byte-level language model created>2026-07-15; Modular TTT test-time training. GitHub API reads: portallib commits/releases/issues (#28 body), E2-TTT README and repo, sxewc README, ByteDance-Seed/Modular-TTT repo.

Hugging Face model API (7): search blt; hnet; byte-latent; portal (author RampPublic); PorTAL; author RampPublic listing; author zeyun-zhong listing; plus model card devingupta/portal-search-4b.

Kevin's X bookmarks via ft (12 successful): "byte latent transformer"; "agent memory causal"; "PorTAL"; "test time training"; "BLT"; "learned optimizer"; "memory"; list --query PorTAL --json; list bytes/tokenizer-free after 2026-08-01; list attention/linear attention/DeltaNet/SSM/Mamba/hybrid after 2026-08-10; list memory AND agent after 2026-08-10; list LoRA/adapter/test-time/optimizer/fast weights/hypernetwork after 2026-08-10. Result: no post-08-10 bookmark relevant to these five directions; the only PorTAL bookmarks are Ramp's 2026-07-01 launch and 2026-07-27 open-sourcing posts.

arxiv.org monthly listing title sweep (6 keyword sweeps over 12,037 titles: cs.CL 2026-08 = 2,535, cs.LG 2026-08 = 4,118, cs.AI 2026-08 = 5,384, plus 2026-09 pages): D18 byte/patch/tokeniz/chunk/vocabulary; D17 memor* x agent/LLM/retrieval/credit/causal/counterfactual/random/holdout/evict/consolidat; D16 learned optimizer/meta-learn/update rule/fast weight/TTT/hypernetwork/portable/cross-model/sidecar/plasticity; routing hybrid attention/linear attention/state space/DeltaNet/Mamba/recurren/MoD/adaptive compute/token-level routing/local-global; coded erasure/parity/error-correct/syndrome/redundan/fault-tolera/coded/Hopfield/associative memory/interference; negatives (negative result/null result/does not/fails to/is not/pre-registered/replicat/retract/post-mortem/revisit/myth/illusion/really/actually) intersected with direction keywords.

Primary-source opens: ~80 arxiv.org/abs pages (title, date, comments, abstract) plus version histories for 2412.09871, 2507.07955, 2603.06642, 2501.00663, 2407.04620, 2510.06128.

## Coverage limits

- The session's WebSearch budget (200 calls, shared) was exhausted after 10 queries in this cell; Jina reader (r.jina.ai) refused anonymous requests from this network (AS7018 reputation block); Semantic Scholar returned 429 on every call; arXiv HTML search and WebFetch-to-arXiv returned 429; DuckDuckGo HTML returned a bot challenge. Replacement modalities were the arXiv API (slow, backoff), OpenAlex, Hugging Face papers search, GitHub, Hugging Face model API, ft bookmarks, and arxiv.org monthly listings.
- Not searched directly: OpenReview, ACL Anthology, Google Scholar, lab blogs (Meta FAIR, Google, Thinking Machines, Ramp) beyond GitHub/HF artifacts, live X/Twitter search, Papers with Code, stat.ML/eess listings. Citation counts unavailable (Semantic Scholar down).
- The listing sweep is title-only; papers whose titles lack the keywords were missed unless another modality surfaced them. Abstracts were read for keyword hits; full texts were not read, so quantitative claims are as stated in abstracts.
- arXiv API date filtering used submittedDate; papers first submitted before 2026-08-10 but revised after (e.g., Switch Attention v3) were caught only via other routes.
- Kevin's bookmark index covers 2,038 bookmarks synced 2026-09-01; FTS5 hyphen handling required rephrasing some queries.
- The PorTAL blog page could not be re-fetched (Jina blocked); PorTAL status is taken from the GitHub API (commits, releases, issue #28) and Hugging Face API.
- "Peer-reviewed" labels are taken from authors' venue statements in abstracts; no independent replications of any reported number were found or performed.
