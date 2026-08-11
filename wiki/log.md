# CoTCodec Research Log

Chronological record of all operations. Append-only.

## [2026-04-28] project-init | Repository scaffolded

Created the CoTCodec research repository with:
- `memory.json` — project state, direction, exploration strategies, Danqi's confirmation
- `AGENTS.md` — master operating guide incorporating patterns from Kevin's toolkit
  (brain-agent loop, no-one-off-work, compiled truth, deterministic collectors,
  cross-modal review, GBrain/GStack patterns, Claude Code harness architecture)
- Wiki identity files (SOUL.md, USER.md, HEARTBEAT.md)
- Directory structure: harness/, data/, experiments/, automations/, skills/, raw/
- Evaluation harness scaffolded with conditions, benchmarks, metrics, routing

Key decision: Danqi confirmed as advisor for Fall 2026. Field moving fast —
infrastructure must be model-agnostic and benchmark-pluggable. Phase 1
(foundation building) runs now through August 2026.

## [2026-04-28] research | Generalized to 12 orchestration variables + frontier research spec

Reframed from "language paper" to "orchestration variables research program."
Language is Paper 1; 11 additional variables mapped with hypotheses, conditions,
connections, and prior work. Created `directions/` with docs for all 12 variables.

Built frontier research intelligence infrastructure:
- `research/frontier-research-spec.md` — full operational spec covering 30+ sources
  across 3 tiers (labs, academic, community), 7 research threads, signal scoring
  rubric, competitive intelligence tracking, execution schedule
- `automations/frontier-research.md` — weekly scan automation with concrete search
  queries for arXiv, lab blogs, X, HN, Reddit, Semantic Scholar, GitHub
- `skills/frontier-research.md` — research scan skill
- `research/scans/` — directory for weekly scan reports

Source coverage: Anthropic, OpenAI, DeepSeek, DeepMind, Meta, Qwen, Mistral, xAI,
Cohere (labs); arXiv cs.CL/AI/MA/SE, ACL, Semantic Scholar, HF Papers, Papers With
Code, Princeton/Stanford/CMU/UW NLP (academic); X, HN, Reddit, GitHub, Alignment
Forum, Interconnects, The Gradient (community).

Competitive groups tracked: DeepSeek Research, Microsoft (EfficientXLang),
Li et al. (UPenn), Wang et al. (LMU Munich), Schut/Gal (Oxford).

## [2026-04-28] intel | Full intelligence source audit

Audited all Kevin's data sources for research intelligence:

- **294 X bookmarks** (168 unique accounts) — extracted 60+ research-relevant
  bookmarks covering agent harnesses, memory architecture, token optimization,
  subagent orchestration, benchmark infrastructure
- **41 installed skills** — mapped 13 research-relevant + 3 design/viz skills
- **51 Obsidian clips** — 8 research-relevant clips identified
- **378 wiki pages** — key pages mapped for each orchestration variable
- **10 key people to track** — @garrytan, @karpathy, @rauchg, @shawmakesmagic,
  @akseljoonas, @mvanhorn, @hwchase17, @affaanmustafa, @iamfakeguru, @himanshustwts
- **10 primary research tools** — last30days, agent-reach, Jina Reader,
  Semantic Scholar API, arXiv API, GitHub CLI, Exa, qmd, defuddle, nia-docs

Key signals captured:
- Claude Managed Agents (Anthropic official harness) — compatibility requirement
- Caveman token optimization (65% savings) — reasoning format baseline
- Claude Code reverse-engineering — compaction policy data points
- GBrain v0.11 Minions — delegation topology evidence
- ml-intern (HuggingFace) — automated research loop pattern

Built: `research/intelligence-sources.md` (comprehensive inventory)
Updated: `memory.json` with key signals, people, tool inventory

## [2026-04-28] intel | Deep intelligence audit — every bookmark, every follow

Full audit of all Kevin's data sources:

**X Bookmarks (294):**
- Every bookmark read, classified into 6 categories (agent_architecture: 147,
  design_engineering: 104, research: 13, tools: 4, career: 5, other: 21)
- 160 research-relevant signals extracted and mapped to 12 orchestration variables
- 53 unique linked URLs/repos cataloged
- Variable 3 (Memory policy) richest with 31 signals
- Variable 12 (Instruction hierarchy) has 18 signals
- Variable 8 (Verification cadence) has 16 signals
- Variable 11 (Delegation topology) has 13 signals

**X Following (172):**
- Full list pulled via `twitter following kevskgs --json`
- Classified: ai_ml_research (80), design (31), dedalus (10), infra (11),
  founders (8), agent_builders (4), other (28)
- 41 accounts overlap between following and bookmarks (highest signal)
- Key followed accounts not in bookmarks identified as monitoring gaps

**Cross-reference:**
- 33 tiered people to track (6 Tier 1, 14 Tier 2, 13 Tier 3)
- 6 direction docs enriched with community evidence

Built: `research/bookmark-signals.md` (329 lines — all 160 signals by variable)
Built: `research/x-following-analysis.md` (319 lines — full following classified)
Rewrote: `research/intelligence-sources.md` (complete inventory)
Enriched: `directions/02,03,08,09,11,12.md` with bookmark evidence
Updated: `memory.json` with full audit data + 33 people tracking list

## [2026-04-28] models+benchmarks | Frontier model update, harness-beats-model, degradation detection

**Model landscape updated to April 2026 frontier:**
- Frontier tier: Claude Opus 4.7 Adaptive (Elo 1503, SWE 87.6%), GPT-5.5
  (agentic 90.1, long-context 87.5), DeepSeek V4 Pro (overall 85, 9x cheaper, MIT)
- Strong tier: Sonnet 4.6, GPT-5.4 (Toolathlon 54.6%), DeepSeek V3.2, Gemini 3 Pro
  (tau-bench 85.4%)
- Baseline old: Sonnet 3.5, GPT-4o (for harness-beats-model hypothesis)
- All experiment YAMLs and model references updated

**Two new research directions:**
- `directions/13-harness-beats-model.md` — can old model + optimized orchestration
  beat new model + naive orchestration? Directly motivated by Anthropic April 23
  postmortem (3 harness-level changes caused perceived model degradation)
- `directions/14-degradation-detection.md` — McNemar's test statistical framework
  (ICLR 2026) + OrchVar-Canary custom benchmark for catching harness regressions

**Benchmark overhaul (2 existing + 6 new + 2 custom):**
- Added: MCP-Atlas (1K tasks, 36 MCP servers), Toolathlon (108 multi-system),
  SWE-bench Verified (500 human-validated), Amazing Agent Race (1400 DAG puzzles)
- Custom: OrchVar-Canary (regression detection, inspired by Anthropic postmortem),
  Multilingual-Agent-Fidelity (semantic fidelity under language switching)
- New module: `harness/metrics/degradation.py` — McNemar's test, Bonferroni/Fisher/Simes
  aggregation, canary task categories

**3 new experiments:**
- `harness_beats_model_01.yaml` — old + orchestrated vs. new + naive
- `degradation_canary_01.yaml` — validate canary catches simulated Anthropic bugs
- `frontier_comparison_01.yaml` — all 4 frontier models, all 7 conditions, 10 seeds

## [2026-04-28] research | Deep research on model degradation + harness-beats-model evidence

Researched the full 2026 "model quality crisis" across all major providers:

**Quantified harness-beats-model evidence:**
- SWE-bench: 42% → 78% from scaffolding alone (model swap < 1.3pts)
- AdaptOrch (arXiv 2602.16873): formal proof orchestration variance > model selection
- Vercel: 80% → 100% by reducing tools 15 → 2
- LangChain: +13.7pts from harness iteration only

**Provider-specific degradation mapped to orchestration variables:**
- GPT-5: hallucination 12%→23%, code length 187→62 lines (token economics, quantization, RLHF)
- Sonnet 4.6: 25→480 errors/week (19x), 1400+ events over 50 sessions (GitHub #46935)
- Gemini 3.1 Pro: formatting regression, attention drift, capacity issues
- DeepSeek V4: multi-turn stagnation from reasoning suffix constraints (V2)
- Cursor Composer 2: shipped Kimi K2.5 as own model — proved harness IS the product

Updated: directions/13 with full evidence from all providers + quantified data,
directions/14 with cross-provider degradation table, memory.json with evidence + papers

## [2026-04-29] signal | CRITICAL — Abstract Chain-of-Thought (IBM Research)

**Paper:** "Thinking Without Words: Efficient Latent Reasoning with Abstract
Chain-of-Thought" — Ramji, Naseem, Fernandez Astudillo (IBM Research AI)
**URL:** https://arxiv.org/abs/2604.22709
**Tweet:** https://x.com/KeshavRamji/status/2048743883580817620

A learned discrete codebook of 64 abstract tokens achieves **11.6x fewer
reasoning tokens** than verbal CoT while matching performance. The model
learns a "reasoning language" — power-law distribution emerges over the
abstract vocabulary, akin to Zipf's law in natural language.

Key results: MATH-500 (11.6x compression, 90.6% vs 92.6%), AlpacaEval
(2.2x, 36.7% vs 34.3% — EXCEEDS verbal), HotpotQA (4.3x), GPQA-Diamond
(7.9x), AIME'25 (2.7x).

Impact on CoTCodec:
1. **Changes the reasoning format spectrum.** Our language routing (20-40%
   savings) sits between compressed English and abstract tokens (80-92%).
2. **Validates our thesis.** The paper cites DeepSeek-R1-Zero language mixing
   as motivation. Same observation that started CoTCodec, taken further.
3. **Different tradeoff.** Abstract-CoT requires post-training (warm-up + RL).
   Language routing is inference-time only — no model modification.
4. **Open question for agents.** NOT tested on tool-use tasks. Does abstract
   reasoning preserve tool argument fidelity? This is our gap to fill.
5. **Framing update.** "Language routing is the best inference-time approach;
   abstract CoT is the best post-training approach."

Updated: directions/01 (language impact), directions/02 (full rewrite with
Abstract-CoT integration), LaTeX bibliography (5 new entries including
ramji2026abstractcot), memory.json landscape_tracking, wiki timeline.

## [2026-04-29] research | Interpretable Abstract Reasoning — efficiency vs. monitorability

Built `directions/15-interpretable-abstract-reasoning.md` from the safety debate
around Abstract-CoT. Key insight from community discussion: abstract tokens
destroy CoT monitorability, which OpenAI (Baker et al., arXiv 2503.11926) and
METR showed is the most effective safety monitoring signal.

**5 concrete research directions developed:**

1. **Structured abstract tokens** — typed/vectorized/grounded tokens that
   deterministically map to semantic categories instead of random init
2. **Hybrid CoT** — abstract reasoning with verbal checkpoints at decision
   points. Checkpoint frequency IS an orchestration variable (maps to V8).
3. **Monitorability tax** — new term in optimization: U(π) = Success − λ_c·Cost
   − λ_t·Latency − λ_s·SafetyRisk − **λ_m·MonitorabilityCost**. Measure the
   Pareto frontier of efficiency vs. monitorability.
4. **Abstract tokens on agent benchmarks** — our unique gap. First to test
   abstract reasoning on tool-use tasks (tool arg precision, multi-step state,
   error diagnosis, schema fidelity).
5. **Learned orchestration language spectrum** — Human language → Compressed
   → Structured → Abstract discrete → Continuous latent. Where on this spectrum
   should each agent task type sit?

Added 2 new LaTeX bibliography entries (baker2025monitoring, metr2025cotinformative).
Updated optimization target with MonitorabilityCost term.

## [2026-04-29] roadmap | Replanned program order and added repo-local paper source

Integrated the new directions into an explicit program sequence instead of
keeping them as a flat list of interesting ideas.

**Program-order decisions:**
- Pulled `Variable 14: degradation detection` into the foundation layer.
  Rationale: after Anthropic's April 23 postmortem, regression detection is
  required infrastructure, not a later paper.
- Kept `Variable 1: language` as Paper 1. Rationale: still the cleanest
  inference-time intervention with the best measurement story.
- Pulled `Variable 13: harness beats model` forward as the first meta-result.
  Rationale: it is the strongest umbrella argument for the full research thesis.
- Reframed `Variable 2 + Variable 15` as the next major paper on reasoning
  media, abstract reasoning, and monitorability tax.
- Deferred lower-tractability coordination work until the harness and canaries
  are trustworthy.

Built:
- `research/research-plan.md` — repo-level roadmap with program order, near-term
  execution plan, deferrals, and success criteria before Fall 2026
- `paper/language-orchestration-research-spec.tex` — repo-local LaTeX source for
  the Paper 1 research spec

Updated:
- `memory.json` — new `research_plan` section, revised phase-1 goals, updated
  current priorities, new repo LaTeX source path, refreshed next actions

## [2026-04-29] harness | Experiment schema operationalized + canary smoke path built

Turned the roadmap into runnable harness artifacts instead of leaving the
experiment layer half-ahead-of-the-parser.

Built:
- `research/experiment-backlog.md` — execution backlog mapping roadmap tracks to
  concrete experiment files, statuses, and blockers
- `scripts/validate_experiments.py` — validates every experiment YAML and prints
  the expanded run matrix
- `harness/yaml_utils.py` — YAML loader with Ruby stdlib fallback so config
  parsing works even when PyYAML is missing in the environment
- `harness/conditions/degraded.py` — degraded English regression conditions for
  `english_only_low_effort`, `english_only_no_thinking_cache`, and
  `english_only_25word_limit`
- `harness/benchmarks/specs/orchvar_canary_tasks.yaml` — tracked seed task set
  for the custom regression benchmark

Updated:
- `harness/config.py` — experiment configs now support model matrices, grouped
  runs, and richer YAML shapes without exploding on `models:` or grouped
  condition definitions
- `harness/runner.py` — benchmark registry expanded; runner now executes grouped
  run specs and no longer requires `rich` just to start
- `harness/benchmarks/orchvar_canary.py` — custom canary benchmark now loads a
  repo-local task spec and can enumerate tasks in a smoke run
- `harness/metrics/__init__.py` + `harness/metrics/degradation.py` — removed
  eager optional-dependency imports that blocked basic harness execution

Verified:
- `python3 scripts/validate_experiments.py` passes for all current YAMLs
- `python3 -m harness.runner experiments/degradation_canary_01.yaml` now runs
  through config parsing, benchmark loading, task enumeration, and trace flush
  successfully; the remaining blocker is the still-stubbed agent execution loop
  rather than experiment schema drift

## [2026-04-29] env | Harness preflight added after dependency failures

Built `scripts/check_harness_env.py` after repeated missing-dependency failures
(`yaml`, `rich`, `tiktoken`, `numpy`, `scipy`, `pandas`, `pdflatex`) during
schema validation and smoke-run work.

Current verified state from the script:
- config parsing: ready (via Ruby YAML fallback)
- canary smoke runs: ready
- full stats stack: blocked pending Python deps
- paper compilation: blocked pending LaTeX install

This turns environment drift into an explicit preflight check instead of a
surprise during experiment runs.

## [2026-08-10] frontier | Portable architectures, PorTAL audit, and Research Gauntlet 100

Ran the first broad architecture-adjacent frontier scan using primary papers,
official repositories, Agent Reach, lsearch, the local wiki, and FieldTheory's
cache of 1,823 X bookmarks. Three independent research cells audited architecture
collisions, PorTAL's released implementation/evaluation, and the empirical
Claude-of-Duty improvement loop.

**Research decisions:**

1. Lead with a narrowly controlled Coded Delta Memory mechanism pilot.
2. Keep Portable Sidecar Update Dynamics at formal interface/split stage; its
   broad learned-update novelty claim did not survive adversarial review.
3. Keep Edit-Stable State Algebra, Translation-Equivariant Byte Patches, and
   Bidirectional Plan Repair as bounded follow-ons.
4. Deprioritize generic attention replacement, static attention/SSM mixtures,
   surprise-gated memory, generic latent loops, diffusion+MoE, and default
   many-agent parallelism because of direct collisions or weak identification.

**Important corrections:**

- PorTAL is a credible factorization, but the released target alignment still
  uses target-task labels, prefix evaluation biases HellaSwag, and validation is
  reused for selection/reporting. Reproduce it with stratified/full evaluation
  and an untouched test split before extension.
- SR-TTT v2 retracts its earlier exact-memory result after off-by-one and
  noncausal leakage. Startup causality and generation exact match are now
  mandatory memory gates.
- Claude-of-Duty's own assessment ended at 5.05/10 and always lost blind
  comparison to CoD. Parallel directory waves increased coupled defects;
  sequential ownership produced the largest gain. The adopted workflow fans
  out discovery/disproof only and serializes synthesis.
- Independent artifact review scored the architecture memo 39/100 and portable
  dynamics 43/100. It exposed missing learned-optimizer/update-rule precedents,
  target-task leakage, undefined state interfaces, omitted HOLA/LTE baselines,
  and unsupported compute accounting. The program was rewritten: Coded Delta
  is first; portable dynamics is now one explicit sidecar equation plus a
  task-blind held-out task–base pairing and no approved claim-scale budget.

**Built:**

- `research/frontier-systems-program-2026-08-10.md` — ranked eight-direction
  portfolio, falsifiers, pilots, compute envelopes, and twelve-week plan
- `research/scans/2026-08-10.md` — durable frontier scan and landscape update
- `research/fieldtheory-possibilities-2026-08-10.md` — four FieldTheory runs,
  scores, promoted prerequisites, and negative findings
- `directions/16-portable-learning-dynamics.md` — architecture-adjacent direction
- `skills/research-direction-improve.md`, proposal template, Cursor rule, and
  deterministic `scripts/research_direction_doctor.py`
- `infra/research/Dockerfile`, `infra/slurm/research.sbatch`, compute doctor,
  and immutable artifact contract

**Compute audit:** `fal-h100-01` exposes 8×H100 80GB, 208 CPU threads, 1.7 TiB
RAM, 22 TB disk, Docker/Podman, and NVIDIA container tooling. Slurm commands and
Pyxis/Enroot were not visible in PATH. The `kevin` account cannot access the
Docker daemon and noninteractive sudo requires a password, but rootless Podman
is available as the OCI builder. Slurm provenance remains blocked until the host
administrator installs Slurm + Munge + Pyxis/Enroot; direct-host runs remain
smoke tests only.

**FieldTheory execution order:** all four background jobs succeeded. The
highest-leverage result was the Executable Agent Loop Spine (96×89), followed
by deterministic canary oracles and a paired regression gate. Those are now
explicit prerequisites before spending architecture-scale H100 budget.

**Gauntlet correction:** the first rule implementation scored 24/100 in a harsh
implementation review because an empty proposal could fabricate a 100 with
self-declared PASS rows and fake-shaped URLs. That exact exploit is now a
negative test. The doctor requires section-scoped evidence and a hashed bundle
of source snapshots, query logs, provider-distinct review artifacts bound to the
proposal hash, real-model/container/Slurm attestations, six doctor artifacts,
and a hash-chained audit log. The current repo/host therefore cannot truthfully
issue a Compute PASS yet.

**Slurm correction:** replaced the fixed 8×H100/24-hour job with a one-H100,
two-hour safe default and manifest-driven submitter. The submitter rejects
allocations above the declared GPU-hour ceiling, requires three seeds and full
OCI/source digests, and exports an allowlist rather than the full caller
environment. The batch job forwards preemption signals and records checkpoint
confirmation and termination state.

Updated `memory.json` with the scan date, due advisor outreach, H100 host state,
new frontier signals, and revised next actions.

### [2026-08-10] Follow-up | Third critic wave and executable trust/compute gates

Ran two additional bounded adversarial waves instead of forcing the artifacts to
100. The latest scored snapshots were 87/100 for the frontier memo, 74/100 for
Portable Sidecar Update Dynamics, and 62/100 for workflow/compute implementation;
each score preceded fixes to the defects it exposed and is retained rather than
retroactively inflated.

Scientific corrections:

- Coded Delta now claims fixed systematic/parity block coding, not learned sparse
  routing; its diagnostics include block-error covariance, correctable erasure
  fraction, and the full syndrome/six-decode/cache latency ledger.
- Portable Sidecar now uses rank-factorized base projections, a causal
  read→act→observe→write clock, frozen anchor-task latents, a disjoint development
  split, identical outcome streams for matched dynamic baselines, and multiple
  held-out tasks/bases as the future generalization units.
- Coded Delta is approved only for Gauntlet proposal drafting. Portable Sidecar
  is interface-prototype-ready only. Neither is approved for a claim-bearing GPU
  matrix.

Implementation corrections:

- Research reviews are Ed25519-bound to proposal and evidence-root hashes. A
  promotion run requires a CI-pinned external, non-writable trust store; the
  repo-local example is rejected.
- The doctor calls the same Slurm manifest validator as submission, enforces
  cumulative query/time/token/dollar/GPU budgets and a structured successful
  audit termination, and requires image provenance verification.
- Slurm commands are JSON argv arrays executed without a user-controlled shell;
  OCI/export injection, non-finite budgets, allocations above 64 GPU-hours, and
  extra visible GPUs are rejected.
- The image embeds git/archive provenance and verifies it against the manifest
  before workload execution. Exact command, manifest, system inventory, Slurm
  output, allocation doctor, and termination state persist per job.

Remote rootless Podman image `localhost/cotcodec:smoke-20260810` now has local ID
`4c4f881a42e70ae27d749f3248a7e0e7183083271f84a8ba142e4e776fb397b6`.
Container environment, embedded-provenance wiring, output mounts, four trace
files, and one result summary passed. This remains wiring evidence: the real
agent loop is a stub, the default runner has no checkpoint/resume consumer, the
host lacks Slurm/Pyxis, and rootless GPU passthrough lacks NVIDIA CDI/OCI hooks.
Those blockers prevent an honest Compute PASS or Gauntlet 100.

## [2026-08-10] compute | Added checkpoint-first open-model import strategy

Made imported open checkpoints an explicit program primitive rather than an
informal convenience. Ollama/MLX cover fast local smokes; Hugging Face
Transformers/Accelerate cover language-model fine-tuning and architecture
surgery; Diffusers covers Stable Diffusion-family and other diffusion
backbones; vLLM/SGLang/TGI cover high-throughput serving. Architecture proposals
must prefer adapters, sidecars, checkpoint transplant, or continued training
when those isolate the hypothesis without foundation pretraining.

Publication provenance now explicitly includes the immutable model revision,
weight hashes, tokenizer/processor, generation config, license, and remote code.
Mutable Ollama tags or Hub branches remain discovery aliases only.

## [2026-08-10] compute | Added tmux operator session and checkpoint boundary

Added `scripts/tmux-research-session.sh` and made `tmux` part of the cluster
login doctor. The cluster control session now explicitly lives in tmux for
editors, submissions, monitoring, logs, and interactive clients. Submitted
batch jobs remain Slurm-owned.

Recorded the failure boundary: tmux survives SSH/laptop disconnect, but not a
login-node reboot, cluster shutdown, drain, time limit, or cancellation. Long
jobs require atomic versioned checkpoints on persistent storage with complete
training/RNG/data-cursor provenance, two generations, and a tested restore in a
fresh job. Node-local `/tmp` is never the sole checkpoint location.

## [2026-08-10] research | Converted architecture ideas into test contracts

Added `research/architecture-experiment-methodologies.md` and four validated
contracts for Coded Delta Memory, Portable Sidecar Update Dynamics,
Translation-Equivariant Byte Patches, and Bidirectional Plan Repair. Each now
specifies claim scope, model arms, split identity, contamination checks,
matched controls, one primary endpoint, minimum effect, statistics, falsifiers,
GPU ceiling, persistent checkpoint behavior, and required artifacts. The
validator rejects causal architecture claims without a matched from-scratch
control and rejects blocked contracts that masquerade as runnable.

Added a pinned open-model registry plus receipt-producing downloader and an
offline safe loader. The complete SmolLM2-135M snapshot at commit
`93efa2f097d58c2a74874c7e644dbc9b0cee75a2` downloaded 272,445,324 bytes,
hashed to artifact root
`afc2a60e11b26e76c000afdaac6f94a5b18130e211d285533363706495cadc85`, and
passed deterministic CPU generation with finite logits and remote code
disabled.

At Kevin's request, added official Kimi Linear 48B-A3B Base as a scale-only
KDA/attention/MoE cell. Its pinned metadata/custom-code snapshot hashed to
`297a9a41781db8407e4aec382d10097852cd07c53afeea5a2bbeeadc844e3c54` without
executing code or downloading weights. Full Kimi work remains blocked on code
review/vendoring and an 8-H100 tensor-parallel load, checkpoint, exit, and
fresh-job restore proof. The cheap Qwen/Mamba cell must pass first.

## [2026-08-10] research | Prototyped portable orchestration capsules

Investigated the idea of strapping reusable memory, verification, retry,
compaction, routing, and safety logic onto arbitrary agents. The broad novelty
claim failed immediately: AgentHarnessProtocol, Agent Control Specification,
HarnessX, Natural-Language Agent Harnesses/IHR, Vercel HarnessAgent, Agent
Lightning, SkillOpt, and Portable Agent Memory already cover protocols,
processors, adapters, training interfaces, portable skills, or memory transfer.

Reframed Direction 17 around the narrower empirical question: can one fixed
stateful policy preserve event/action semantics and task lift across
heterogeneous hook runtimes, and can declared capability loss predict failure?
Added a draft Gauntlet proposal with Novelty, Compute, and Safety honestly FAIL.

Implemented `harness/capsules/` with immutable lifecycle schemas, per-hook
effect manifests, fail-closed capability compilation, ordered/idempotent event
delivery, exclusive-effect conflict rejection, and context-byte ceilings. Added
a session-scoped provenance memory graph whose recalled tool content remains
untrusted data, plus a verify-before-final capsule. Eight unit tests cover
cross-manifest replay parity, missing capabilities, budget refusal, session
isolation, injection framing, idempotency, transactional conflict rollback, and
verification.

The deterministic reference replay achieved 100% normalized action parity for
three synthetic events over CoTCodec and AHP-shaped capability manifests. This
is schema evidence only: no live AHP, LangChain, OpenAI Agents SDK, AG2, or
Vercel adapter has run, so no portability or task-improvement claim is made.

## [2026-08-10] infrastructure | Added Tinker and Kimi managed-training path

Pinned the official Tinker SDK at 0.23.3 and registered a bounded capsule-policy
post-training contract. The scientific design keeps the external capsule fixed
while training separate rank-16 LoRAs for a cheap Qwen3.5-4B smoke and a
Kimi-K2.6 target cell. Base, prompt-only, capsule-only, LoRA-only,
capsule-aware-LoRA, and native-host arms isolate whether training helps the
model cooperate with the capsule rather than replacing it. This makes no LoRA
weight-portability claim.

The contract freezes current Tinker model IDs, context limits, token prices,
three seeds, data roles, controls, falsifiers, checkpoint policy, and a $6
declared ceiling. Its estimated token-plus-storage maximum is $5.2823; delayed
billing usage remains a required reconciliation. Execution remains disabled
until the rendered datasets, two live adapters, Tinker access, capability receipt,
digest-pinned image, cluster secret injection, and Qwen checkpoint/resume test
exist.

Added an offline/online Tinker doctor, strict JSONL SFT runner, remote full-state
plus sampler checkpoints, optimizer-preserving resume receipts, final adapter
download hashing, and a CPU-only Slurm/Pyxis submit path. Tinker owns the remote
GPUs; Slurm still owns the reproducible client. Manifests reject GPU requests,
embedded credentials, mutable images, traversal, non-finite costs, and jobs over
the safety ceiling. No authenticated request or paid training run was made
because `TINKER_API_KEY` is not present.

## [2026-08-10] research | Replaced the strap-on direction with causal mechanism bets

Kevin clarified that portable strap-on behavior is infrastructure, not the
research contribution. Moved the capsule specification to
`research/infrastructure/portable-orchestration-capsules.md`, archived its
proposal as a rejected direction audit, and marked the Tinker capsule cell as
enabling infrastructure. Capsules, Docker, Slurm, tmux, checkpoints, model
loaders, and the Qwen-to-Kimi ladder remain valuable experimental machinery but
cannot supply the novelty claim.

Ran a second-wave discovery and kill audit over future-value memory,
transactional fast state, operator routing, coded recurrence, edit-stable state,
translation-conditioned patching, and diffusion repair. Direct work or fatal
identification problems killed the broad forms: ForesightKV/KVP/AgeMem/MemexRL
occupy future-aware memory control; MemTX/ChronoMem/TrustMem occupy verified
memory transactions; MoD/RouteLMT/counterfactual MoE/Meta-Attention occupy hard
budget routing; Coded Hopfield/Expander Hopfield/GhostServe preempt broad coded
memory; and a coherent DeltaNet overwrite may be a wrong but valid codeword with
zero syndrome. These negative results remain in the record.

Promoted `directions/17-causal-memory-holdout-trials.md` as the strongest narrow
survivor. It randomizes one eligible memory item to serving or non-serving
holdout with known propensity, audits the causal estimator against paired replay
from an identical snapshot, then trains a strictly past-only memory gate. Added
an executable contract with a CPU symbolic oracle, frozen Qwen screen, controls,
feature-time leakage tests, statistics, safety, an eight-GPU-hour ceiling, and a
conditional Tinker Qwen/Kimi scale-up. The proposal's accepted Gauntlet score is
honestly 0 because signed reviews, protected evidence, the real agent loop,
safety output, immutable container, and Slurm attestation are missing.

Added `directions/18-translation-equivariant-byte-boundaries.md` as the
architecture moonshot. It applies unbalanced optimal transport to aligned
translation-span boundary probability mass in a BLT-style byte model. The
candidate delta is dynamic boundary formation, not cross-lingual hidden-state
alignment or tokenizer fairness. A 20M–50M matched-patch/FLOP screen must beat
entropy patching and fixed-boundary representation alignment before any 125M or
1B request. Tinker cannot implement this architecture surgery.

## [2026-08-10] research | Built the two CPU identifiability paths

Implemented `harness/causal_memory_trials.py` as a narrow causal-study runtime,
not a generic plugin framework. It owns content-addressed prefix events, direct
feature lineage, suffix-permutation checks, deterministic assignment, an
`fsync` journal committed before continuation, serve/holdout exposure, A/A and
paired replay receipts, group-cross-fitted ridge nuisances, AIPW pseudo-outcomes,
and a past-only effect policy. Audit episodes are excluded from all nuisance and
policy fitting. Raw and analysis manifests bind inputs, code/runtime identities,
snapshots, folds, nuisances, pseudo-outcomes, reports, and hashes.

The registered 2,000-episode designed-effect reference passed at propensities
0.50, 0.25, and 0.10. After excluding every audit episode from nuisance and
policy fitting, effective sample sizes were 1517, 1138, and 546 and minimum-arm
ESS was 758, 382, and 146. AIPW-to-oracle Spearman was 0.435, 0.474, and 0.488;
absolute ATE gaps were 0.016, 0.032, and 0.025; policy-to-oracle Spearman was
0.294, 0.294, and 0.237. The aggregate status is deliberately named
`SYMBOLIC_SENSITIVITY_PLUMBING_PASS`, not `PASS`. These numbers
validate the implementation against a world constructed to contain a
predictable effect. They are not evidence that real agent memories have such an
effect. In-process adapters can still lie consistently about prefix time or
replay RNG/tool state; the live path therefore requires engine-owned event and
tool instrumentation plus reviewed adapter code before any scientific status.
The next scientific step is the registered 20–40-step tool generator,
family-disjoint splits, deterministic evaluators, and a frozen Qwen adapter.

Implemented `harness/translation_boundaries.py` as a model-free reference for
debiased, position-aware unbalanced transport over causal byte-boundary mass.
The cross primal now exactly includes transport, coupling-KL, and marginal-KL
terms; self-cost and mass corrections remove entropic bias. Link confidence is
separate from left/right mass fractions. Tests cover SciPy primal equivalence,
zero-mass continuity, edge ownership, unequal lengths, one-to-many allocation,
wrong-link permutations, overallocation, and non-convergence. The doctor scored
aligned unequal-length profiles at 0.0107 loss versus 0.0811 for a shifted
control. This proves only that
the proposed objective is executable and alignment-sensitive; Torch gradient
checks, BLT integration, matched model controls, data licensing, and the novelty
audit remain open.

Added machine-readable commands, thresholds, and artifact contracts to both
architecture YAMLs. The complete suite now reports 72 passing tests, all five
architecture contracts validate, and `uv lock --check` passes. No GPU, Tinker,
Kimi, API, Docker, or Slurm job was launched for these CPU references.

Retained the local 25 MiB causal bundle at
`data/results/causal-memory-holdout/stage0-seed42/`; its sensitivity manifest is
SHA-256 `a4705716ea162347b1f13b9287d84867901f10f4435f1d5fee31e24d56fb4069`.
The boundary doctor receipt at
`data/results/translation-boundaries/reference-doctor.json` is SHA-256
`9747145490d6011533cdab9ede19e7520925fe2262e3b772797e2437c191cd27`.
These gitignored local receipts are reproducibility aids, not signed Gauntlet
evidence or publication artifacts.
