# Design-phase brief (2026-09-01) — invent, then try to kill

Read first: context.md (brief + honesty rules + network routes), sweep/synthesis.md (occupied map, open
gaps, kill-shot verdicts, new-since-08-10). Also skim /Users/kevinliu/repos/cotcodec/research/frontier-systems-program-2026-08-10.md
sections "What the frontier already occupies" and "Rejected or deprioritized ideas".

## Already rejected or deprioritized (do not re-propose without a NEW delta that names why the rejection no longer holds)
- better generic linear attention; static attention/SSM mixtures; surprise-gated memory (Titans/TRIM-KV + SR-TTT causality failure);
  generic latent loop with halting; diffusion+MoE; graph RAG for agents; "train once, port a LoRA" (PorTAL/Trans-LoRA/Cross-LoRA/CAST/LoRAGen);
  Coded Delta Memory as a primitive (Coded Hopfield, Expander Hopfield, GhostServe; zero-syndrome coherent overwrite);
  portable orchestration capsules / strap-on harness layers (infrastructure, not research).
- Current live candidates (do not duplicate; you MAY propose something that subsumes or sharpens them if the kill-shot verdict says STILL_OPEN):
  Causal Memory Holdout Trials (dir 17), Translation-Aligned Byte Boundary Transport (dir 18), Portable Sidecar Update Dynamics (dir 16),
  Rollout-Value / Budgeted Mixture of Sequence Operators, Bidirectional Diffusion Plan Repair, Rank-Adaptive Edit Summaries.

## What a candidate must contain (all fields, no exceptions)
1. name (kebab-case slug) and one-line claim
2. claim_scope: attachment-capability | architecture-causal | portability-protocol | systems-pipeline
3. mechanism: one precise paragraph, with the update/attention/objective equations in plain text where possible
4. what_is_new: the delta stated against the THREE closest priors (each with URL and date) — one sentence each
5. falsifiable_predictions: 2-4 predictions with numbers (effect size, metric, scale) that would be embarrassing if wrong
6. kill_conditions: what result kills the direction
7. cheapest_decisive_pilot: CPU/no-LM phase-0 doctor (algebra, causality, leakage) → 20M-135M matched from-scratch or frozen-checkpoint screen; give GPU-hours ≤ 16 on 8×H100, model ids from models/registry.yaml where possible (smollm2-135m, qwen3-0.6b-base, qwen3.5-4b, mamba-130m-hf, kimi-linear-48b-a3b-base, blt-1b, llada-8b-base), or a Tinker stage (Qwen3.5-4B / Kimi-K2.6 LoRA) with token budget
8. controls: matched iso-parameter / iso-FLOP / iso-wall-time controls and the strongest published baseline
9. kevin_advantage: which asset makes this uniquely feasible (parallel translation data at General Translation; 8×H100; Tinker access to Kimi-K2.6/Qwen3.5/GLM-5.3; the Docker/Slurm/checkpoint harness) — or "none" honestly
10. collision_risk: low | medium | high, with the search you ran
11. monitorability_and_safety: does the mechanism reduce CoT/action monitorability? data rights?
12. negative_result_value: what we learn if it fails

## Inventor angles (one inventor per angle; propose 3 candidates each, at least one "moonshot" and one "cheap decisive")
A. translation-supervised architecture: parallel translations as a training VIEW that supervises where/how compute is spent (boundaries, routing, depth, experts, attention span) — beyond dir 18 boundary transport
B. portability factorization after PorTAL: port across ARCHITECTURE FAMILIES (transformer ↔ Gated-DeltaNet/KDA hybrid ↔ diffusion), across tokenizers/byte models, or port update RULES/states rather than weights
C. sequence-operator state semantics: state with explicit provenance, ordered recall, edit/delete/undo guarantees, or confidence — without re-proposing Coded Delta
D. reasoning media + monitorability by construction: latent/abstract reasoning tokens that a weaker monitor can decode by design; tool-use compatible
E. test-time learning with causal guarantees: fast weights whose write/read causality, reset, deletion, and poisoning resistance are provable and testable (learn from the SR-TTT retraction)
F. cross-lingual compute equity at the architecture level: fix tokenizer fertility inequity inside the model (not in the tokenizer) so equal semantic content costs equal compute
G. agent-native sequence architecture: architecture (not harness) that treats tool calls/results/receipts as typed inputs — e.g., attention or state that is aware of action/observation boundaries
H. cross-domain import wildcard: control theory, coding/information theory, distributed systems, neuroscience, compilers — an idea that has no LM analog yet
I. LoRA-only architecture probes on a 1T model: what can be learned ABOUT architecture through Tinker LoRA/RL access to Kimi-K2.6 (e.g., probing/steering KDA state, teaching new operators via adapters) — and what cannot
J. diffusion/non-AR for agents: a use where iterative refinement beats AR at equal wall-clock in tool-using loops

## Output discipline
- Never write "completely novel". Write "No direct prior art found through 2026-09-01 under <what you searched>".
- Every prior gets a URL. If you did not open it, say so.
- Prefer mechanisms testable at ≤ 135M parameters first. A moonshot still needs a cheap identifiability screen.
- Save your full note to design/<angle>-<inventor>.md and return the structured object.

## Occupancy shifts found 2026-09-01 in the arXiv triage (sweep/arxiv-triage-*.md) — read these three notes in full
Newly OCCUPIED (do not re-propose; use as mandatory baselines where relevant):
- Sparse-attention-for-global-layer substitution at continued pretraining (Qwen3.8-Next QSA 2608.30320; A.X K2 Sparse Gated Attention). Gated residual / hyper-connections (Qwen3.8-Next; Motif 3).
- Interference control inside delta-rule state: query-derived erase (QED 2608.13668), content-routed state anchors (MARCH). Any recall/interference claim must baseline against both, plus SWA+sinks (2608.28444).
- Hybrid serving state algebra: DASC (2608.30386), Tail-Replay (2608.30310), TreeWY (2608.20961), DeltaLog, DAMP, HARTS — compact-state-summary / edit-summary claims must beat tail replay.
- Frozen-base sidecar fast-weight memory (MoNe), closed-form chunkwise TTT to 1.3B (E2-TTT), fast-weight update-rule taxonomy (Falcon-1/2/3, 2608.27763).
- Adaptive depth: MixerLoop, CDB, Gated Recurrent Transformer (beats MoR 9/9, 2608.15062), RouteSparse (budgeted routing among ATTENTION PATTERNS with a certificate); looped LMs for compositional tool calling (2608.18171).
- Diffusion-native asynchronous tool interaction staked as an architecture (CID 2608.10438, no empirics) — kills the NOVELTY of bidirectional diffusion plan repair; dLLM baselines must use CAI-DLLM/CARVE-class decoding, not vanilla LLaDA.
- Portable adaptation: frozen artifact + thin target-side alignment is doubly occupied (Engram reader transfer 2608.17050; MentorPulse 2608.20927); budgeted rank allocation (Omni2LoRA 2608.09227). Only UPDATE-RULE portability remains for dir 16.
- Automated harness evolution incl. cross-model-family harness portability (HarnessLens, StarHarness, PILOT, OpsHarness, Aspire); memory/skill admission gating (AdmitOR, Recuris); Harness-RL credit assignment; pixels-as-history (VERA).
- Byte-level: externally supervised byte-chunk boundaries and MT-evaluated byte compression ("When Tokenizers Fail", "Autocompleting Tokenizers"); nested/sliceable byte vocabularies are a preregistered NEGATIVE (2608.28151); abugida fertility floors 1.47x-9.02x quantified (Vowel Signs).
- CoT monitorability: tool-return unfaithfulness (FACE-Eval), hidden-CoT detection (HCDS), capability-auditability tradeoff (Why2Speak), Intent-as-a-Tool, legible mid-layer latent chains (2608.24958).
- Evaluation protocol mandates: model+harness as the tested solver (F2PF 28%->49% from context policy alone), paired passes with token/dollar ledger, all-k-of-k reliability (APIFlow-Bench), false-completion rate (FrontierChallenge: 75.5% of failing runs claim completion), truncation-recovery confound for operator routers (BRANCH r=0.72).
- Negative: "LM-head bottleneck is harmful" is NOT established (causal negative); fast weights aggregate rather than remember episodes (LongVU-TTT).

Axes the triage found STILL OPEN or nearly empty (candidates should aim here or somewhere the triage did not even name):
- explicit error syndrome / confidence inside recurrent state (baselines: QED, MARCH, SWA+sinks)
- routing among QUALITATIVELY DIFFERENT sequence operators under a hard budget (RouteSparse is patterns-only; EEI survey names this open)
- porting HOW a sidecar updates across held-out task-base pairs (dir 16 remnant)
- cross-lingual monitorability of reasoning (one n=8 case study exists) — a fit for parallel translation assets
- translation-supervised byte-boundary FORMATION with a delta over externally supervised boundaries (dir 18 remnant)
- randomized causal identification of memory value (dir 17; learned gating alone no longer discriminates); borrow the inverted-IFEval oracle world (2608.11095)
- stability, poisoning, reset, and deletion guarantees for fast weights (read-after-write causal semantics from 2608.27763; SR-TTT retraction)
- non-suffix edits on long-retention state units with rank analysis (Diag B remnant)
- causal tests against shortcuts and monitorability of what a loop computes
- a positive equal-wall-time diffusion-vs-AR result on agent tasks (concept staked by CID; empirics open)

## Search routes for refuters (the session WebSearch budget is EXHAUSTED)
Use: WebFetch on arxiv.org/abs pages, GitHub, lab blogs; `gh search repos|code`; HF API; `ft search`;
and the H100-host-proxied APIs from context.md (arXiv API via ssh; Jina via ssh). Space host requests >= 4 s.
Concrete helper: /private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/tools/hostsearch.sh {ddg|arxiv|openreview|hfpapers|crossref|abs|jina} <arg> (see context.md).

## Strongest named gaps from the finished sweep cells (each was searched and came back empty; cite the cell note)
- seq-operators G1: script/language-controlled evaluation of hybrid recurrent-state recall and hybrid ratio — production hybrids report one multilingual aggregate at most; parallel translations let "only the language change" probes exist.
- seq-operators G2: independent iso-compute multi-seed comparison of depth-axis operators (pre-norm vs Block/Full AttnRes vs mHC vs Gated Residual) at 0.1–1B.
- seq-operators G3: mechanism of the NoPE-in-hybrids disagreement (Kimi/Solar extrapolate at 1M vs Qwen3.8-Next endless generation after post-training).
- seq-operators G5: open reproducible <=1B from-scratch reference of the K3 stack (KDA lower-bounded decay + full-rank gate, NoPE global, Block AttnRes, MTP) — infrastructure-shaped prerequisite.
- seq-operators G6: translation-equivariance of learned sparse indexers (DSA/QSA/CSA) — nobody asked whether selected blocks correspond across translations or whether parallel data can supervise a language-invariant indexer.
- learned-update-rules G1: cross-operator-family transfer of a LEARNED inner-loop update rule at LM scale; G4: parallel translations as a meta-training/evaluation objective for update rules (same content in two languages must induce the same state write); G6: distilling a transformer's implicit ICL update (its HOW) into an explicit recurrent fast-weight rule.
- benchmarks-eval G1: seed-count / minimum-detectable-effect norms for 0.1–1B architecture comparisons (10 seeds x 3 sizes x 3 mixers is feasible in days); G2: cross-lingual translation-paired MQAR/NIAH probes do not exist.
- bookmarks G2: independent AttnRes replication <=1B and depth-attention weights as a probe on parallel data; G3: PorTAL-style portability onto a hybrid linear-attention base with generative/translation tasks; G4: LM-scale complex/rotational decay in delta-rule memory.
- tinker-rl G1: effect of Tinker's shared-outer MoE LoRA on expert routing at 1T; G4: one training script, two backends (hosted Kimi-K2.6 vs local open-tinker/skyrl-tx with full internals) to separate mechanism from scale.
- harness-ecosystem G2: harness-invariance as a trained model property; G3: heavy-to-minimal harness distillation with a parity endpoint.
- ttt-fastweights: stability/poisoning/reset/deletion of fast weights remain open; fast weights "aggregate rather than remember" (LongVU-TTT).

## Kill-shot verdicts on the current repo directions (killshot-current.md)
dir 16 STILL_OPEN (narrow; new mandatory controls: Engram reader transfer 2608.17050, E2-TTT, Modular TTT, Falcon rules, KV-translation layers 2608.30963) · dir 17 NARROWED (Hindsight Memory-PRM 2608.29605 occupies intervention-calibrated per-entry memory credit; dir 17 survives only as prospective randomized identification) · dir 18 STILL_OPEN (closest: "When Tokenizers Fail" supervises byte chunks toward a frozen subword LM — monolingual) · rollout-value operator scheduling NARROWED (LoGo 2608.29539, Switch Attention, NAtS-L, Mixture of Layers, HubRouter, Flux Attention occupy token-level dynamic operator routing under immediate loss) · Coded Delta NARROWED (QED, SANE 2608.22354, Proteus 2608.16844, TwinKV 2608.27128).
Production convergence: three labs (Kimi K3, Qwen3.8-Next, GLM-5.3-Flash) independently ship 3 linear : 1 global hybrids; sparse-for-global substitution and gated residuals are now standard. Proposing "another hybrid ratio" is dead.

## More named gaps (latent-reasoning.md, local-model-ecosystem.md)
- latent-reasoning 1: monitorability of latent/abstract media on TOOL-USE agent tasks (latent papers measure tokens/accuracy; monitorability papers measure explicit CoT; the one crossover, 2608.04928, is 1B math/QA).
- latent-reasoning 2: translation-equivariant abstract reasoning codes — same abstract trace for semantically equivalent problems across languages, monitor trained in one language tested in others (2605.27901 shows monitors are fragile across 13 languages but proposes no medium).
- latent-reasoning 3: controlled reproduction of Abstract-CoT with token-necessity ablations at 4B–8B (no official code; three third-party attempts negative or stalled).
- latent-reasoning 4/5: interpretable-by-construction latents (MUX, J-CoT, DiscoLoop, Thinking States) under obfuscation pressure and for tool-argument fidelity; cross-medium monitorability-tax curve at matched accuracy with one fixed monitor (= Direction 15C).
- latent-reasoning 6: multi-turn agent-loop evaluation of looped/recurrent-depth LMs (Ouro, Huginn) with tool feedback, depth vs monitorability.
- local-model G1/G2: no sub-10B open KDA base with native transformers support; no released BASE checkpoints for any 2026 KDA/QSA hybrid (Kimi-K3-Base, GLM-5.3-Flash-Base, Qwen3.8-*-Base all 401). A ≤1–3B KDA:global hybrid pretrained/distilled locally (teacher: Kimi-Linear-48B-A3B-Base) would be the first open small KDA base.
- local-model G3: no reproducible LoRA/full-FT memory+throughput report for 2026 hybrids on H100-class nodes.
- local-model G4: no translation (FLORES/WMT) evaluation or translation fine-tuning of 2026 open hybrids across attention families at matched size.
- local-model G5: no independent replication of K3 "2.5x scaling efficiency" or Qwen3.8-Next "1/9 FLOPs" at any scale; ≤1B ablations of AttnRes/Gated Residual/n-gram embeddings are feasible with native `qwen4_exp`/`glm5_next` reference modules.


## VERIFICATION PASS CORRECTIONS (2026-09-01, read before dedup/judging)
- G19 routing half is OCCUPIED: SARA (arXiv 2606.25821, Findings of ACL 2026) and RA-MoE (2605.28306) already supervise MoE routing with parallel translated data. Drop or reframe any candidate whose mechanism is "parallel data → consistent expert routing"; only the compute-per-semantic-unit ledger survives.
- G14 clause "interpretable-by-construction latents as a monitor channel" is partly OCCUPIED by ALCA (ACL 2026, 2026.acl-long.1570: latent safety deliberation + restricted self-decoding). Surviving: tool-use tasks, obfuscation pressure, cross-lingual monitor transfer.
- G2 must be stated as recurrent-state/hybrid behaviour with content fixed across translations: cross-lingual needle retrieval on softmax transformers exists (MLNeedle 2408.10151 NAACL 2025; ONERULER 2503.01996). Cite both as baselines.
- Kimi-K2.6 checkpoint = 595.2 GB INT4; K3 = 1.561 TB shards. Qwen3.8-Next "Full AttnRes = GR" holds only without GatedNorm. "256 configs per scale" is one paper's ablation (2608.11859), not a norm.
- Patents: NVIDIA US20260105282A1 "Gated delta networks" (pending) and Google WO2025230701A1 compressive memory — flag IP exposure for kernel-level delta-rule contributions.
- AttnRes: four third-party replications with gains, one 1B negative (+6.9% worse PPL, routing collapse) — G9 is live.
- Tooling: hostsearch.sh ddg is bot-blocked from the host; use arxiv/openreview/hfpapers/crossref routes and WebFetch instead.
