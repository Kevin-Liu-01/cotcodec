# Frontier Systems Research Program — 2026-08-10

## Executive verdict

Do not start by inventing “another attention replacement.” That space is
crowded, scale-sensitive, and easy to fool with weak memory tests. The best
program for this compute and this team's strengths is:

1. **Causal Memory Holdout Trials** — randomize one eligible memory item to
   serving or non-serving holdout, audit the propensity estimator against paired
   replay, and train a strictly past-only memory policy. This is the strongest
   narrow novelty survivor and the cheapest decisive mechanism pilot.
2. **Translation-Equivariant Byte Boundaries** — transport BLT-style boundary
   probability mass across aligned translations. This is the strongest
   architecture-level moonshot and uniquely matches the team's translation
   advantage.
3. **Rollout-Value Operator Scheduling** — value full stateful continuations
   under measured latency/HBM cost rather than immediate next-token loss.
4. **Portable Sidecar Update Dynamics** — retain only as a high-collision
   missing-cell contract test.
5. **Coded Delta, edit summaries, and diffusion repair** — keep as diagnostic or
   negative-result cells, not lead novelty claims.

Coded Delta no longer leads. Coded Hopfield and expander memories directly
precede error-correcting associative memory, GhostServe codes KV state, and a
coherent DeltaNet overwrite can produce a wrong but valid codeword with zero
syndrome. Future-use memory, transactional state, and immediate-loss operator
routing also failed broad novelty or identification checks. Portable capsules,
Tinker, Kimi, Docker, Slurm, and checkpointing are experimental infrastructure;
they are not the contribution. None of the surviving directions is pilot-ready
until its remaining doctors pass.

This report does not claim global novelty. It reports testable hypotheses found
through 2026-08-10 under the coverage below and labels their collision risk.
Internet search cannot prove the absence of prior art.

## Evidence and coverage

### Sources used

- Ramp's PorTAL report, code, pinned recipes, model cards, and open issues.
- Primary papers and official code from arXiv, ACL Anthology, PMLR, NeurIPS,
  Google/DeepMind, Meta, Moonshot, Hugging Face, and GitHub.
- Agent Reach with Exa, Jina Reader, GitHub CLI, RSS, and public web sources.
- `lsearch` through a local Chromium search endpoint for independent discovery.
- FieldTheory's local cache of 1,823 Kevin-selected X bookmarks, current through
  2026-08-02, grouped into architecture, harness, compute, and graph seeds.
- Three independent subagent tracks: architecture collision scan, PorTAL code
  audit, and adversarial research-loop design.

### Coverage limits

- Reddit and live X search were unavailable because authenticated backends were
  not configured. FieldTheory provided the user's historical X signal but not
  a live global X search.
- PorTAL has no arXiv paper as of the cutoff. Its main quantitative claims are
  first-party, not peer-reviewed or independently replicated.
- Several 2026 architecture papers are new preprints. Their claims require
  reproduction before being treated as foundations.
- FieldTheory bookmarks generate hypotheses; they do not validate scientific
  claims. Every promoted claim below is tied back to a primary source.

## What the frontier already occupies

| Family | Representative primary work | What is already taken | Remaining gap |
|---|---|---|---|
| Structured recurrence | [Mamba-2](https://arxiv.org/abs/2405.21060), [Gated DeltaNet](https://arxiv.org/abs/2412.06464) | Fast selective state, gating, targeted delta writes | Exact ordered recall, edits, confidence, and state composition |
| Production linear hybrids | [Kimi Linear](https://arxiv.org/abs/2510.26692), [Kimi code](https://github.com/MoonshotAI/Kimi-Linear) | KDA plus periodic global attention; real long-context kernels | Operator mix is statically wired; state has no explicit error syndrome |
| Test-time learning | [TTT layers](https://arxiv.org/abs/2407.04620), [Titans](https://arxiv.org/abs/2501.00663), [MIRAS](https://arxiv.org/abs/2504.13173) | Hidden state as a learned model and online optimization | Stability, poisoning, reset, deletion, and portable update rules |
| Adaptive depth | [Mixture-of-Recursions](https://arxiv.org/abs/2507.10524), recurrent-depth reasoning, Mixture-of-Depths | Token-wise depth and recursion routing | Routing among qualitatively different sequence operators |
| Latent reasoning | [Coconut](https://arxiv.org/abs/2412.06769), Abstract-CoT, Thinking States, DiscoLoop | Continuous/discrete hidden reasoning and recurrent thinking | Tool use, monitorability, and causal tests against shortcuts |
| Diffusion language | [LLaDA](https://arxiv.org/abs/2502.09992), [MDLM](https://arxiv.org/abs/2406.07524), Block Diffusion | Non-autoregressive masked generation and bidirectional refinement | A use case where repeated passes beat AR at equal wall time |
| Tokenizer-free compute | [Byte Latent Transformer](https://arxiv.org/abs/2412.09871) | Entropy-based dynamic byte patches at scale | Semantically equivalent compute units across languages |
| Portable adaptation | [PorTAL](https://labs.ramp.com/research/portal-portable-task-adaptation/), Text-to-LoRA, LoRAGen, Cross-LoRA | Hypernetworks and cross-model adapter transfer | Candidate sidecar-update delta under missing task–base cell evaluation |
| Graph agent memory | [Graph-based Agent Memory](https://arxiv.org/abs/2602.05665) and multiple products | Entity/relation memory and deterministic agent DAGs | Causal attribution over orchestration traces and localized plan repair |

### Important invalidation signal

[SR-TTT v2](https://arxiv.org/html/2603.06642v2) retracts its original exact
memory gains after finding off-by-one and noncausal leakage. Corrected evaluation
reported 0% exact match in all 2,250 paired trials. Every memory experiment in
this program therefore requires startup-causality perturbations, generation
exact match, and separate storage/addressing/readout diagnostics before scale.

## PorTAL: what is real and what is not

The released PorTAL configuration learns a 256-dimensional task latent, a
shared canonical hypernetwork core with base-specific learned layer embeddings,
and a base alignment that emits ordinary per-layer LoRA weights. On a new base
it freezes the latent/core and refits the alignment. “Thin” is only relative to
the base: the released Qwen3-8B alignment has 13,632,640 parameters, about 3.56×
one exported q/v-r8 adapter, although it is amortized across 14 tasks.

Ramp reports:

- 98% of per-task LoRA lift on unseen Qwen3-8B;
- 94% on cross-family Gemma-3-4B;
- roughly half as much calibration data to reach the reported LoRA plateau;
- only 14% recovered lift for its Cross-LoRA baseline.

Those are promising internal three-seed results, but the strong “learn once,
move anywhere” interpretation is unsupported:

- the released Qwen3-8B recipe still uses up to 1,000 examples for each of 14
  tasks, so target-task labels are still required;
- the public artifacts use one seed and do not reproduce the exact blog sweep;
- no released scripts reproduce the per-task LoRA, Cross-LoRA, or data-sweep
  comparisons end to end;
- evaluation selects `rows[:1000]`; [issue #27](https://github.com/ramp-public/portallib/issues/27)
  shows that HellaSwag becomes only the ActivityNet prefix rather than a
  representative sample;
- the validation macro score is used for both best-epoch selection and reporting;
  there is no untouched test set;
- only multiple-choice tasks are tested, with no generative, agent, tool-schema,
  or true held-out-task evaluation;
- the calibration comparison uses PorTAL r8 versus a per-task full-module r16
  LoRA, so it is not an iso-capacity causal comparison;
- Cross-LoRA is training-free while PorTAL receives labeled target-base data;
- released Mistral and Inkling recipes **use** norm-equalized gradients and a
  changed choice-loss weight, but no ablation establishes that they are required.

The contribution is a credible new factorization and systems recipe, not a new
primitive. Transferring **how a model updates** remains a hypothesis, not a
cleanly unclaimed axis; learned optimizers, local learned update rules, and
transferable test-time adaptation already occupy much of it.

## Rejected or deprioritized ideas

| Tempting idea | Decision | Collision or flaw |
|---|---|---|
| Better generic linear attention | Reject | Mamba-2, Gated DeltaNet, KDA, Qwen hybrids; no new state capability |
| Static attention/SSM mixture | Reject | Jamba, Nemotron-H, Falcon-H1, Kimi, Qwen already occupy it |
| Surprise-gated memory | Reject for now | Titans/GdWM/TRIM-KV plus the SR-TTT causality failure |
| Generic latent loop with halting | Reject | Recurrent depth, MoR, Coconut, Thinking States, DiscoLoop |
| Diffusion plus MoE | Reject | LLaDA MoE already scales this combination |
| Graph RAG for agents | Deprioritize | Useful product pattern, weak new scientific mechanism |
| “Train once, port a LoRA” | Deprioritize | PorTAL, Trans-LoRA, Cross-LoRA, CAST, LoRAGen |
| More agents in parallel | Reject as a default | Coupled work amplifies integration defects; independent cells only |

## Ranked research portfolio

These are ordinal triage judgments after adversarial review, not fabricated
novelty probabilities or Gauntlet scores.

| Rank | Direction | Collision risk | Pilot definition | Information/GPU-hour |
|---:|---|---|---|---|
| 1 | Causal Memory Holdout Trials | Medium | Exact one-item estimand and CPU oracle specified | Very high |
| 2 | Translation-Equivariant Byte Boundaries | Medium | Small matched-compute screen specified | High |
| 3 | Rollout-Value Operator Scheduling | High | Needs stateful rollout-value contract | Medium-high |
| 4 | Portable Sidecar Update Dynamics | High | Missing-cell contract only | Medium if narrowed |
| 5 | Coded Delta diagnostic | Very high | Syndrome kill cell only | High negative value |
| 6 | Rank-Adaptive Edit Summaries | High | Theory/bytes/latency tradeoff study | Medium-high |
| 7 | Causal Orchestration Graphs | Medium | Blocked by executable loop | High later |
| 8 | Geometry-Compiled Base Alignment | High | Insufficient model families | Medium |

### 1. Causal Memory Holdout Trials

**Claim.** Known-propensity serving-versus-holdout assignment for one eligible
memory item can identify downstream executable-task effects; paired deterministic
replay can audit the estimator; and those cross-fitted effects can train a
strictly past-only memory gate that beats observational or next-use controls.

**Delta.** CMI intervenes at query time; Xiong et al. and MSCE derive
observational future/history utility; ForesightKV/KVP use future attention or
decoding utility; AgeMem/MemexRL use RL. No direct primary work combining
longitudinal randomized eligibility, propensity estimation, paired replay audit,
and a learned write-time policy was found under the recorded cutoff.

**Pilot.** One randomized item per 2,000 deterministic episodes, propensity
`0.5`, CPU paired oracle first, then a frozen Qwen screen with a small effect
head. Require effective sample size at least 400, sealed paired-effect rank
correlation at least `0.20`, and at least three points of executable-success
lift over the strongest non-randomized learned control at memory budget `K=4`.
The normative mechanism, controls, leakage checks, Tinker/Qwen/Kimi ladder, and
falsifiers are in `directions/17-causal-memory-holdout-trials.md` and
`experiments/architectures/causal-memory-holdout.yaml`.

**Status.** Scientific draft only. Accepted Gauntlet score is zero because the
signed reviews, protected evidence, real loop, safety run, digest-pinned image,
and Slurm attestation do not exist.

### Diagnostic A. Coded Delta Memory

**Second-wave verdict.** Do not claim a new error-correcting memory primitive.
[Coded Hopfield Networks](https://www.vincent-gripon.com/files/articles/2010-istc.pdf)
and [Expander Hopfield memory](https://proceedings.neurips.cc/paper/2019/hash/97008ea27052082be055447be9e85612-Abstract.html)
directly establish coding/self-decoding associative memory, while
[GhostServe](https://arxiv.org/abs/2605.00831) erasure-codes LLM KV state. More
fatally, a coherent semantic overwrite can be wrong while remaining a valid
codeword, giving zero syndrome. Independent projections may create disagreement
but also destroy the assumed code relation and single-erasure model. The cell
below survives only to test whether natural DeltaNet collisions ever have enough
detectable, single-block-correctable mass to justify further work.

**Claim.** A fixed systematic/parity code over independently projected recurrent
state blocks can expose an interference syndrome and correct some localized
block errors better than equal-budget uncoded state, replication, or exact-cache
controls.

**Concrete first code.** Start with a systematic `(k=4,r=2)` real-valued code.
Split each value into four equal shards and form two fixed random-orthogonal
parity shards. Six independently projected causal DeltaNet blocks write one
source/parity shard each using the ordinary gated delta rule. On read, decode
the four source shards and compute parity residuals. If the syndrome crosses a
threshold fixed on development episodes, remove each candidate block in turn,
choose the single-block erasure that minimizes residual, and reconstruct that
shard from parity; otherwise return the uncorrected read. The baseline and coded
variants receive the same total state bytes, key/value projection parameters,
and measured FLOPs. This tests single-block erasure correction first; learned
routing and learned codes are later ablations, not part of the primary claim.

**Why it may work.** Delta rules improve overwrite behavior but offer no signal
that two memories have collided. Redundancy can trade a small amount of capacity
for detectability and graceful degradation. The model can spend global-attention
or replay compute only when the syndrome says recurrence is unreliable.

**Closest collisions.** Multihead DeltaNet; [HOLA](https://arxiv.org/abs/2607.02303),
which routes high-residual writes to a bounded exact cache;
[LTE](https://arxiv.org/abs/2510.20787), which learns eviction for hybrid
linear/exact memory; Artificial Hippocampus Networks; Kanerva-style sparse
memory; and [Expander Hopfield memory](https://proceedings.neurips.cc/paper/2019/hash/97008ea27052082be055447be9e85612-Abstract.html).
The diagnostic delta is narrower: measure whether a correction syndrome *inside*
recurrent state predicts any naturally occurring interference after state bytes,
FLOPs, and wall time match. Injected faults cannot support a semantic-memory
claim.

**Cheapest decisive pilot.** Separate three conditions: natural overload,
adversarial near-key collisions, and injected state noise. Use controlled MQAR
episodes with ordered multi-token values, updates, deletes, and contradictions.
At equal state bytes and measured FLOPs, compare ordinary multihead DeltaNet,
wider heads, independent replicated states without correction, and exact HOLA
and causal LTE reproductions whose key/value metadata, cache bytes, eviction,
and read cost enter the ledger. The registered primary endpoint is area under a
fixed exact-recall capacity curve at load ratios `{0.5,0.75,1,1.25,1.5,2}`;
injected noise cannot establish the main claim. Require a ≥5 normalized-AUC
point gain. Report block-error covariance and the fraction of failures whose
best syndrome explanation is a correctable single-block erasure; correlated
multi-block failures directly test the code's core assumption. Report every
seed effect and a hierarchical bootstrap over episodes
within each of three training seeds; three seeds are a kill screen, not final
confirmation. Syndrome quality uses AURC/ECE. A secondary intervention sends at
most 2% of alarmed tokens to a fixed 128-token exact window and compares the
same budget assigned randomly.

**Falsifier.** Reject if gains disappear after matching head count/state bytes,
if an equal-budget replica or bounded exact cache matches them, if syndrome-guided
correction does not beat the same code with correction disabled, or if overhead
removes batch-1 wall-time gains. The matched-compute ledger includes parity and
syndrome calculation, all six candidate erasure decodes, cache metadata, and
correction latency rather than charging only recurrent writes.

**Compute.** The ≤16 GPU-hour ceiling is provisional and is not approved: six variants ×
three seeds × one short mechanism run plus 25% compile/evaluation reserve. No
job is submitted until a one-cell timing doctor fixes model size, steps, tokens,
seconds/step, peak HBM, and the exact manifest ledger. Later 100M/350M envelopes
are planning ranges, not approved budgets.

### 2. Portable Sidecar Update Dynamics

**Narrow claim.** A task-conditioned, episode-scoped low-rank sidecar update
rule can port to a held-out task–base pairing using a task-blind, low-capacity
alignment. This is missing-cell compositional sidecar portability, not a fully
held-out task and base and not transfer of native Transformer versus DeltaNet
recurrence.

The normative mechanism is specified in `directions/16-portable-learning-dynamics.md`.
In brief, each of four evenly spaced layers owns `M_j^l ∈ R^(64×64)`, stored at
rank eight. At action step `j`, read
`z_j^l=P_b^l h_j^l`, `h'_j^l=h_j^l+Q_b^l M_j^l z_j^l`; only after emitting the
action and receiving structured outcome `o_j`, write
`M_(j+1)^l=Π_8[ρ_j^l M_j^l+η_j^l u_j^l(v_j^l)ᵀ]`. The portable network emits
scalar `ρ,η` and 64-vectors `u,v`; state resets at episode boundaries. The
base projections are rank-8 factorizations rather than dense matrices, using
`64(d_b+64)` parameters across four layers (about 266K at width 4096), with
rank reduced if necessary to respect the registered
`min(1M, 0.1% of base parameters)` cap.

**Closest collisions.** PorTAL, TTT/Titans, differentiable plasticity,
[Meta-Learning Bidirectional Update Rules](https://proceedings.mlr.press/v139/sandler21a.html),
[local meta-learned update rules](https://arxiv.org/abs/1804.00222),
[learned learned optimizers](https://arxiv.org/abs/2009.11243),
[ALFA](https://arxiv.org/abs/2011.00209), [VeLO](https://arxiv.org/abs/2211.09760),
[Celo2](https://arxiv.org/abs/2602.19142), and
[Meta-TTL](https://arxiv.org/abs/2604.00830). These collapse the novelty claim
to a narrow task-conditioned sidecar representation and held-out-pair transfer
protocol; no “new primitive” claim is justified.

**Identification split.** Meta-train the rule on `T_meta` and at least one
Transformer plus one recurrent/hybrid source. Fit anchor-task latents only on
`T_anchor × B_source`, freeze them, and use those frozen latents to fit the
target alignment on `T_anchor × b_target`. Use disjoint `T_dev × B_dev` pairings
for rank, horizon, checkpoint, and threshold selection. Fit a new task latent on
`τ_new × b_source`, then freeze everything and evaluate `τ_new × b_target` with
zero target-cell calibration/training data. The pre-registered causal online
outcome stream remains available equally to all dynamic methods. Split schema
generators, namespaces, ontologies, and composition families.

**Baselines.** Static PorTAL and matched LoRA rank/module sweeps; ordinary SGD,
RLS/delta, native TTT/DeltaNet updates; a direct per-base learned updater; common
sidecar without portability; same latent with static deltas; same rule without
task conditioning; in-context adaptation; and oracle per-base rules. Match
evidence, update count, state lifetime/bytes, reset frequency, inference FLOPs,
search budget, source meta-training amortization, and wall time.

**Falsifier.** Reject if alignment-only or permutation controls recover the task,
if the sealed task–base pairing does not beat the common-sidecar and fresh-optimizer
baselines, or if the break-even task count is impractical. The ≤16 H100-hour
phase is an interface/throughput contract test, not a claim test.

### Diagnostic B. Rank-Adaptive Edit Summaries

**Claim.** Measure the rank, bytes, approximation error, and edit latency needed
to summarize order-sensitive recurrent segment transitions. Do not promise a
small exact certificate for arbitrary edits.

**Why it may matter.** Agent conversations and code histories are edited trees,
not immutable streams. But exact DeltaNet contributions are suffix-dependent,
and exact composed affine operators generally grow rank and storage with segment
length. The useful result may be an impossibility/tradeoff curve rather than a
new memory architecture.

**Closest collisions.** Associative scans, segment trees, reversible models,
checkpoint-and-replay, and [exact deletion analysis](https://arxiv.org/abs/2607.27539).

**Pilot.** Compare exact dense segment trees, checkpoint replay, and rank-`r`
summaries on branching conversations and append/update/delete tasks. Measure
state/logit error, empirical rank growth, bytes, and latency.

**Falsifier.** Reject the compact-summary direction if required rank grows
approximately linearly or storage approaches the ordinary KV cache.

### 2. Translation-Equivariant Byte Boundaries

**Claim.** BLT-style dynamic boundary probability mass should be transported
across aligned translation spans instead of being learned only from next-byte
entropy. Unbalanced transport allows morphology, omission, and reordering. The
claim is about boundary formation, not translation-invariant latent states.

**Why this team.** Translation infrastructure can produce controlled parallel
views, terminology sets, error categories, and rare-language stress tests that
generic architecture groups cannot cheaply assemble.

**Closest collisions.** BLT entropy patches; ByT5/Charformer;
[Parallel Tokenizers](https://arxiv.org/abs/2510.06128),
[Conditional Unigram Tokenization](https://openreview.net/forum?id=lnWJWNA8YW),
and [Parity-Aware BPE](https://aclanthology.org/2026.acl-long.342/); multilingual
representation steering; rate–utility and shared concept-space work:
[Rate–Utility Frontiers](https://arxiv.org/abs/2607.16117),
[ACL 2025](https://aclanthology.org/2025.acl-long.1536/) and
[EACL 2026](https://aclanthology.org/2026.eacl-long.145/).

**Pilot.** Freeze a small BLT global model and train patcher/local modules first
on equal byte budgets for English, Chinese, Korean, and Polish. Compare entropy
patching, equal extra data without alignments, fixed-boundary hidden-state
alignment, word-boundary supervision, and unbalanced boundary transport at
identical patch-count histograms and measured FLOPs. Only then request a 125M
confirmation.

**Metrics.** Bits/byte, downstream translation, reasoning/tool schema fidelity,
robustness to spelling/script variation, patch length by language, actual
throughput, and whether shared patches causally transfer under intervention.

**Falsifier.** Reject if gains vanish after matching the patch-length histogram,
bytes, FLOPs, or wall time; if representation consistency performs equally well;
or if aligned-boundary scores improve without task-level fidelity.

### 5. Bidirectional Diffusion for Closed-Loop Plan Repair

**Claim.** Generate a typed action DAG with masked observation slots, execute
the next ready node, insert the observation, and re-denoise only the affected
subgraph. Bidirectional refinement can revise predecessors and successors
without regenerating an entire left-to-right plan.

**Closest collisions.** LLaDA/MDLM, diffusion planning, autoregressive
plan-execute-replan, graph workflow engines, verifier reranking.

**Pilot.** Fine-tune an open LLaDA/Dream checkpoint; do not pretrain diffusion
from scratch. Start on PDDL and stochastic API tasks, then browser/tool traces.

**Metrics.** Success, invalid actions, nodes revised, unnecessary replanning,
batch-1 latency, total network evaluations, and FLOPs including verifier budget.

**Falsifier.** Reject if AR plus verifier matches success at equal compute, if
partial re-denoising is not localized, or if repeated passes lose on wall time.

### 6. Budgeted Mixture of Sequence Operators

**Claim.** Route segments among local softmax attention, coded/delta recurrence,
latent recurrent iterations, and skip under a hard state/FLOP budget. Train
against counterfactual per-operator utility, not a soft efficiency penalty.

**Delta.** MoD/MoR route depth. Kimi/Qwen use fixed operator ratios. This router
chooses the sequence primitive based on retrieval, streaming, or refinement need.

**Pilot.** 135M then 350M on a controlled mix of recall, language modeling,
state tracking, and compositional reasoning. Compare each pure operator, a
static 3:1 hybrid, MoD, and MoR.

**Falsifier.** Reject if a static hybrid matches quality, the router collapses,
or dispatch overhead erases measured TTFT/TPOT gains.

### 7. Causal Orchestration Graphs

**Claim.** Compile agent traces into typed causal DAGs and support graph surgery:
replay an identical trajectory while intervening on language, memory, tool
selection, verification, or delegation nodes. Attribute success changes to
specific orchestration edges rather than aggregate prompt variants.

**Why it matters.** LangGraph-style products represent execution, and graph
memory represents knowledge, but neither gives CoTCodec a causal experimental
object. Event-sourced trace DAGs can make interactions among the 12 variables
measurable and permit minimal counterfactual re-execution.

**Pilot.** Instrument OrchVar-Canary and one real benchmark. Compare ordinary
full-run ablations against node/edge interventions with matched random seeds and
mocked deterministic tool results.

**Falsifier.** Reject the causal claim if intervention estimates fail to predict
held-out full reruns or if stochastic API nondeterminism dominates effect size.

### 8. Geometry-Compiled Base Alignment

**Claim.** Predict PorTAL's base alignment directly from model topology plus
cheap weight/activation sketches, eliminating labeled target-task refitting.

**Pilot.** Meta-train a set/graph hypernetwork across 12–20 open models using
layer type, width, SVD sketches, and unlabeled activation covariance. Hold out
entire families. Compare PorTAL, Cross-LoRA, CAST, and fresh LoRA.

**Falsifier.** Reject if it cannot beat Cross-LoRA without target-task labels or
if it needs labeled task examples to recover more than 50% of LoRA lift.

This is high-upside but needs more model families and weight movement than the
first seven directions, so it should not lead the program.

## Harness and workflow: Research Gauntlet 100

The portable “strap-on” layer is research infrastructure, not Direction 17.
`research/infrastructure/portable-orchestration-capsules.md` prototypes
capability-negotiated memory and verification capsules, but the broad
universal-sidecar claim is rejected: AHP, ACS, HarnessX, NLAH/IHR, Vercel
HarnessAgent, Agent Lightning, SkillOpt, and Portable Agent Memory already
occupy the abstraction. A synthetic two-manifest replay passes; no live
portability claim exists. Direction 17 is now Causal Memory Holdout Trials.

The useful Claude-of-Duty result is not its seed prompt. The repository's own
assessment says the game reached only 5.05/10 and every blind reviewer chose
real Call of Duty. Parallel directory waves improved the score only +0.46 and
left defects at 66; one sequential owner improved +1.00 and cut defects 66→26.

The adopted rule is therefore:

```
preflight doctors -> independent discovery -> novelty audit -> candidate contract
  -> two adversarial reviews -> fix the largest defect -> repeat
```

The deterministic contract lives in:

- `skills/research-direction-improve.md`
- `.cursor/rules/research-direction-improvement.mdc`
- `scripts/research_direction_doctor.py`
- `scripts/research_gauntlet_record.py`
- `research/proposals/evidence/_schema.json`
- `research/proposals/_template.md`

The first implementation failed its own harsh review at 24/100: an almost
empty Markdown file could manufacture a 100 using self-declared PASS rows and
fake-shaped URLs. That failure became a permanent negative test. Version 2
requires section-scoped content plus a bundle of hashed source snapshots,
queries, doctor outputs, two provider-distinct review artifacts bound to the
proposal hash, real-model/container/Slurm attestations, and a hash-chained audit
log. Hashes make mutation detectable; they do not prove that an author or
provider is honest, so independent review remains a social and technical gate.

FieldTheory reinforced four workflow choices:

- write eight loop exits before writing the prompt;
- separate ontology, knowledge base, and agent “brain” layers;
- use Cloudflare's pattern: recon, independent hunt, disproof, gap fill,
  deduplication, reachability trace, feedback, report;
- copy ml-intern's paper→citation→dataset→sandbox→train→diagnose loop, but
  pre-register metrics and preserve negative runs.

Its four completed possibility runs also exposed the repo's binding constraint:
the Executable Agent Loop Spine scored 96×89 on leverage×specificity, followed
by deterministic canary fixtures and paired regression gates. The architecture
bookmark seed instead produced harness ideas because FieldTheory applies the
seed to the current repository; this is a readiness finding, not proof that the
architecture space is exhausted. The full local audit, job IDs, promoted ideas,
and negative findings are in
`research/fieldtheory-possibilities-2026-08-10.md`.

`100/100` means pilot-ready. It does not mean true, globally novel, or perfect.
Missing a falsifier caps a proposal at 59; incomplete novelty coverage at 74;
no executable pilot at 79; no independent review at 89.

## Checkpoint-first model acquisition

The H100 program should import the strongest compatible open checkpoint before
considering foundation pretraining. Ollama/MLX are the shortest path to local
behavioral and harness smokes. Hugging Face Transformers/Accelerate are the
default for language-model training and architecture surgery; Diffusers is the
default for Stable Diffusion-family and other diffusion backbones; vLLM,
SGLang, or TGI provide high-throughput serving when needed.

This materially changes the cost envelope. Portable sidecars, coded-memory
attachments, translation objectives, diffusion plan repair, and agent evals can
often begin from imported weights using adapters, checkpoint transplant, or
continued training rather than full pretraining. A proposal must still justify
that the frozen checkpoint exposes the required interface and that retained
pretraining behavior does not confound the mechanism claim.

Every imported model is an experimental dependency: pin the Hub revision and
weight hashes, tokenizer/processor, generation configuration, license, and
remote model code. Ollama tags and mutable Hub branches are discovery aliases,
not publication provenance. Stable Diffusion is a useful vision/diffusion
backbone, not a substitute for the language or agent benchmark model.

The executable acquisition and testing protocol now lives in
`research/architecture-experiment-methodologies.md`, with pinned inputs in
`models/registry.yaml` and validated contracts in
`experiments/architectures/`. The registry includes small Transformer and
Mamba discovery bases, FLA DeltaNet, BLT, LLaDA, SDXL, and the official Kimi
Linear 48B-A3B Base checkpoint. Kimi is a scale-only KDA/attention/MoE cell:
its 20 weight shards and custom modeling/tokenizer code require review,
vendoring, and an 8-H100 tensor-parallel load/restore proof before execution.
It cannot replace the cheap matched from-scratch control.

## Compute architecture: durable control, Slurm data plane

```text
Vercel/Native SDK or local control plane
  durable manifest, approvals, live status, artifact links
                         |
                         v
Slurm + Pyxis/Enroot on bare metal
  digest-pinned OCI image, H100 allocation, preemption, job arrays
                         |
                         v
Immutable artifact plane
  configs, traces, checkpoints, metrics, logs, source hashes
```

Vercel AI SDK, Native-style terminal interfaces, and agent-browser are useful
control surfaces. They are not the scientific execution environment. Training
runs belong on bare-metal Slurm so allocation, priority, cancellation,
preemption, GPU accounting, and job provenance remain explicit.

The human control session runs inside `tmux` on the login host so laptop or SSH
disconnects do not kill editors, monitors, or interactive clients. `tmux` is not
a scheduler or checkpoint system: login-node reboot, cluster shutdown, drain,
timeout, and cancellation still kill processes. Scientific durability requires
atomic, versioned checkpoints on persistent storage and a tested restore in a
fresh Slurm job; submitted batch jobs themselves are owned by Slurm.

The current host audit found 8×H100 80GB, 1.7 TiB RAM, 208 CPU threads, 22 TB
disk, Docker, and Podman. The `kevin` account cannot access the Docker daemon
and noninteractive `sudo` requires a password. Rootless Podman built
`localhost/cotcodec:smoke-20260810` (local image ID
`4c4f881a42e70ae27d749f3248a7e0e7183083271f84a8ba142e4e776fb397b6`); the
container doctor, embedded-provenance verifier, stats stack, persistent output
mount, and harness wiring smoke
passed. The harness agent loop is still a placeholder, so its zero-rate output
is not a model result. Rootless GPU passthrough failed because Podman 3.4.4 has
no NVIDIA CDI device or OCI hook. The audit also did **not** find `sbatch`,
`srun`, `sinfo`, Enroot, or Apptainer in `PATH`. Slurm/Pyxis and GPU-container
validation remain administrator blockers.

The repo now defines:

- `infra/research/Dockerfile` — digest-pinned CUDA 12.8, pinned uv, locked Python environment;
- `infra/slurm/research.sbatch` — one-H100 safe default, preemption forwarding,
  checkpoint confirmation, and immutable OCI/source checks;
- `scripts/submit_research_job.py` — manifest resource/GPU-hour validation and
  allowlisted Slurm environment export;
- `scripts/check_compute_env.sh` — separate builder, login, allocation, and
  container doctors;
- `infra/README.md` — build, publish, submit, and artifact contract.

## Evaluation contract for every architecture experiment

### Quality controls

- identical dataset, tokenizer/bytes, optimizer, schedule, parameter budget,
  training FLOPs, and seed set where the mechanism permits;
- report iso-parameter, iso-FLOP, and iso-wall-time views;
- strongest simple baseline at matched state bytes and kernel maturity;
- three seeds before interpretation; five near a paper claim;
- untouched test set; validation only for selection;
- no prefix slicing of benchmark rows; stratify or evaluate full sets.

### Memory diagnostics

1. Was the item stored?
2. Was the right slot/state addressed?
3. Did the retrieved content reach output logits?

Test ordered multi-token recall, duplicates, near-duplicates, updates, deletes,
contradictions, early/middle/late positions, state corruption, exact generation,
and startup causality. NIAH alone is not acceptable.

### Systems metrics

- TTFT, TPOT, p50/p95/p99 latency, and worst stall;
- batch sizes 1/8/32;
- prefill and decode separately;
- peak HBM, tokens/s, GPU occupancy, MFU, and kernel fallback;
- compilation/warm-up cost;
- total network evaluations for diffusion;
- reset, deletion, and cross-request isolation for online memory.

### Safety and monitoring

- prompt/tool-output injection;
- cross-user state bleed and persistent poisoning;
- refusal consistency across languages;
- exact tool schema and argument fidelity;
- latent/recurrent state probeability;
- overthinking and unsafe-policy success versus recurrence depth;
- data licensing and provenance for parallel translations.

## Twelve-week execution plan

| Week | Work | Gate |
|---:|---|---|
| 0–1 | Install Slurm+Pyxis, publish OCI image, run doctors | One digest-pinned H100 job completes and resumes from checkpoint |
| 1–2 | Reproduce PorTAL public artifacts; fix stratified/full evaluation and test split | Public numbers characterized; evaluator bias quantified |
| 2–3 | Build common memory microbench and causality suite | Transformer/Gated DeltaNet baselines reproduce across 3 seeds |
| 3–5 | Portable sidecar formal split, interface, and one-cell contract | Missing-cell protocol is executable and timing closes or defer |
| 3–5 | Coded Delta Memory mechanism pilot in parallel job arrays | Wins at matched state bytes and confidence predicts failures or kill |
| 6 | Independent Gauntlet review | At most two directions survive |
| 7–9 | 100–350M scaling confirmation for survivors | Scaling slope and wall time remain favorable |
| 7–9 | Translation-equivariant 125M pilot if data is ready | Gain survives matched patch count/compute |
| 10 | Agent/tool-use evaluation and safety sweep | No project red line crossed |
| 11–12 | Five-seed final matrix, artifact release, paper decision | One clean positive or informative negative result |

### Compute envelopes

| Stage | Typical scale | Budget |
|---|---|---:|
| Algebra/mechanism unit tests | matrices to 50M | 1–16 GPU-hours |
| 100–150M pilot | 2–5B tokens | 40–120 GPU-hours |
| 350M confirmation | 5–10B tokens | 120–300 GPU-hours |
| 1–1.3B scale check | 20–30B tokens | 400–900 GPU-hours |
| Portable-sidecar one-cell contract | one split cell × 3 seeds | ≤16 GPU-hours |
| Portable-sidecar claim matrix | methods × splits × tasks × seeds | TBD only after measured one-cell timing |

Do not attempt to reproduce Kimi's multi-trillion-token result or LLaDA MoE's
23.5T-token run. Use the H100s to establish mechanisms and scaling slopes.

## Immediate next actions

1. Keep the verified rootless Podman smoke image as wiring evidence; ask the
   host administrator for Slurm + Munge + Pyxis/Enroot and NVIDIA CDI/OCI hooks
   on `fal-h100-01`, then publish a clean committed image by registry digest.
2. Reproduce PorTAL before extending it; fix evaluation sampling and add a true
   test split first.
3. Run the pinned SmolLM2 acquisition/loader smoke, then implement the shared
   memory/correctness microbench independently of the current agent harness.
4. Implement the Causal Memory Holdout CPU oracle and complete its protected
   novelty/design reviews first. Keep Coded Delta as a falsification diagnostic
   and Portable Sidecar Update Dynamics at interface-contract stage.
5. Contact Danqi now: the scheduled August landscape/design review is due, and
   PorTAL/Kimi/latent-memory developments materially change the fall framing.

## Primary source index

- [PorTAL report](https://labs.ramp.com/research/portal-portable-task-adaptation/)
- [PorTAL code](https://github.com/ramp-public/portallib)
- [Text-to-LoRA](https://proceedings.mlr.press/v267/charakorn25a.html)
- [Cross-LoRA](https://arxiv.org/abs/2508.05232)
- [Trans-LoRA](https://proceedings.neurips.cc/paper_files/paper/2024/file/708fdc7911f11585ee7161518e509ae6-Paper-Conference.pdf)
- [Mamba-2 / Structured State Space Duality](https://arxiv.org/abs/2405.21060)
- [Gated DeltaNet](https://arxiv.org/abs/2412.06464)
- [Kimi Linear](https://github.com/MoonshotAI/Kimi-Linear)
- [TTT layers](https://arxiv.org/abs/2407.04620)
- [Titans](https://arxiv.org/abs/2501.00663)
- [Meta-Learning Bidirectional Update Rules](https://proceedings.mlr.press/v139/sandler21a.html)
- [Meta-Learning Update Rules for Unsupervised Representation Learning](https://arxiv.org/abs/1804.00222)
- [Learned learned optimizers](https://arxiv.org/abs/2009.11243)
- [ALFA](https://arxiv.org/abs/2011.00209)
- [VeLO](https://arxiv.org/abs/2211.09760)
- [Celo2](https://arxiv.org/abs/2602.19142)
- [Meta-TTL](https://arxiv.org/abs/2604.00830)
- [HOLA](https://arxiv.org/abs/2607.02303)
- [LTE](https://arxiv.org/abs/2510.20787)
- [Expander Hopfield memory](https://proceedings.neurips.cc/paper/2019/hash/97008ea27052082be055447be9e85612-Abstract.html)
- [Byte Latent Transformer](https://arxiv.org/abs/2412.09871)
- [LLaDA](https://arxiv.org/abs/2502.09992)
- [Coconut](https://arxiv.org/abs/2412.06769)
- [Mixture-of-Recursions](https://arxiv.org/abs/2507.10524)
- [Cross-lingual consistency RL](https://arxiv.org/abs/2606.01464)
- [Shared multilingual concept spaces](https://aclanthology.org/2026.eacl-long.145/)
- [Claude-of-Duty assessment and harness](https://github.com/mshumer/Claude-of-Duty)
- [Vercel AI SDK 7 harness abstraction](https://vercel.com/blog/ai-sdk-7)
