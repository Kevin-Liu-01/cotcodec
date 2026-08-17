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

## [2026-08-11] research | Reframed memory as transitions, pinned the field, and froze the first experiments

Ran a primary-source and official-code audit of active/core, inactive/archive,
episodic, semantic/profile, temporal-graph, procedural, latent, learned-controller,
multi-agent, benchmark, and poisoning work. FieldTheory searched 1,823 cached X
bookmarks through 2026-08-02; Local Search used managed headless Chrome for live
discovery; Agent Reach and direct paper/repository inspection supplied the
authoritative evidence. Added `research/memory-sources.yaml`, which now validates
28 sources and 27 immutable repository pins while labeling every benchmark
claim as vendor-, paper-, or open-harness-reported rather than reproduced.
Unresolved licenses are explicit blockers.

Rewrote the memory-policy direction around a policy over write, activate,
retrieve, inject, update, consolidate, expire, and forget. The audit rejects a
new memory graph, active/archive split, reflection loop, semantic profile,
learned CRUD, proactive injection, or future-use predictor as standalone
novelty. Causal Memory Holdout survives only as prospective first-eligible-use
assignment with known propensity, executable downstream utility, engine-owned
paired replay, cross-fitted AIPW, and a strictly past-only gate. Query-time
causal intervention, next-use prediction, and observational utility are required
controls. The landscape and kill criteria are recorded in
`research/memory-systems-landscape-2026-08-11.md` and the daily frontier scan.

Added three validated frozen contracts under `experiments/memory/`: a 2,400-
episode-per-propensity deterministic oracle cell over active core, inactive
archive, temporal graph, and proactive tool action; a 100-episode pinned
SmolLM2 loader/replay/checkpoint smoke; and a pinned Qwen3-0.6B frozen screen
starting at exactly 100 episodes with an eight-H100-hour discovery ceiling.
The contracts fix K=4, one archive read, top-k=4, 256 injected tokens,
propensities 0.50/0.25/0.10, family splits, controls, estimator gates, safety
cases, and fresh-job resume proof. Eight focused validator tests pass. No memory
quality result or benchmark score was produced.

Connected to the persistent `cotcodec` tmux session on `fal-h100-01`, verified
all eight H100s, and created a dedicated `memory-research` window. The current
remote checkout remains the clean pushed `581ded8` revision. Rootless Podman
image `localhost/cotcodec:581ded8` retains verified source provenance, but
Slurm/Pyxis and rootless GPU passthrough remain unavailable. Tmux covers an SSH
disconnect only; every long experiment still requires persistent atomic
checkpoints and a fresh-job restore test.

The first containerized model-acquisition command exposed an image-interface
bug: `ENTRYPOINT ["/bin/bash", "-lc"]` consumed ordinary `podman run IMAGE
argv...` arguments as shell positionals and returned success without executing
the workload. Overriding the entrypoint proved the diagnosis. Removed the shell
entrypoint in the next image definition and added a regression test requiring a
normal JSON-argv `CMD`.

With the explicit entrypoint override, the remote tmux window downloaded and
verified the full pinned `Qwen/Qwen3-0.6B-Base` snapshot at revision
`da87bfb608c14b7cf20ba1ce41287e8de496c0cd`. The immutable receipt records
1,203,641,805 bytes and artifact root
`7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0`.
This is reproducible model acquisition, not a memory experiment or quality result.

Implemented the first deep `harness/memory_trials/` slice rather than extending
the generic runner. It defines frozen event/task/budget/oracle records, a keyed
family-splittable generator, a deterministic memory actor, and an engine-owned
`ReplayableMemoryWorld` that composes with the existing durable assignment and
cross-fitted AIPW shell. Episodes cover active core, inactive archive, temporal
graph, and proactive memory-to-tool action. Every continuation persists raw
prompt, compact untrusted memory frame, model action, tool evaluation, and full
trace plus binding hashes. Tests cover deterministic generation, suffix
regeneration, A/A and paired effects, cross-session isolation, explicit
residency/read budgets, overwrite refusal, and policy recovery.

The first full run revealed that the graph cell was only one hop and that
verbose internal record metadata exceeded the registered 256-token injection
cap. Kept that 130 MiB output as superseded audit evidence instead of promoting
it. Rebuilt the stratum as an actual two-hop `reports_to -> located_in` traversal,
separated complete storage-byte accounting from compact rendered memory, and
persisted hash-bound raw artifacts rather than hashes alone.

The corrected registered seed-42 run executed 2,400 episodes at each serve
propensity 0.50, 0.25, and 0.10. All estimator/replay gates passed. AIPW-to-
paired correlations were 0.877, policy-to-paired correlation was 0.875,
absolute ATE gaps were 0.00269/0.00172/0.00088, and minimum arm ESS was
905/459/170. The 152 MiB gitignored bundle manifest hashes to
`88ac6befb41e45eab8bacdbcecae57889bb6910a092047672992e133503256d3`.
Status is deliberately `ORACLE_ENGINE_CONTRACT_PASS`: the environment was
constructed to contain predictable effects and uses a deterministic actor, so
this is not evidence about LLM memory quality or any open-source memory system.

## [2026-08-11] harness | Proved fresh-process memory recovery and registered the model transport ladder

Replaced monolithic trial collection with episode transactions: the assignment
is atomically committed and fsynced before inference, each episode is sealed by
hash, and a contiguous checkpoint binds the completed prefix. The registered
run stopped after 500 episodes and resumed from a new process without resampling
the committed assignment. It then completed all 7,200 episodes across serve
propensities 0.50/0.25/0.10 with every gate passing. The authoritative 344 MiB
gitignored aggregate manifest hashes to
`a5c4e6471f57752f9fc2772efd329fdd1198837cda17c403305d351d67d19c80`.
The earlier one-hop and non-resumable bundles remain superseded audit evidence.

Added a strict completion actor that receives the exact persisted prompt,
preserves raw model output, parses only the registered JSON action, records
malformed output as task failure, and can load a pinned local Hugging Face
snapshot with `local_files_only` and `trust_remote_code=false`. This is the
first imported-model seam; no language model has yet produced a memory result.

Verified current official model catalogs and added a machine-checked transport
matrix. Pinned open cells now span Qwen3.5 4B and 9B hybrids, Qwen3.6 35B-A3B,
GPT-OSS 120B, and the separate Kimi Linear 48B-A3B Base diagnostic. Hosted
cells use GPT-5.6 Sol, Claude Opus 5, Gemini 3.5 Flash, DeepSeek V4 Pro, and Kimi
K2.6, with Claude Fable 5 reserved as the expensive maximum-capability
secondary. `models/provider-registry.yaml` requires five provider families,
official-domain evidence, no `latest` aliases, and live requested/returned model
binding before every wave.

Registered `experiments/memory/stage1-model-transport.yaml` and documented the
identification in `research/memory-model-transport-2026-08-11.md`. All models
share one task and assignment manifest, memory budget, prompts, tool tape, and
policy artifacts. Self-hosted models retain exact paired replay; hosted APIs use
prospective randomization and AIPW, with repeated A/A calls only as service-drift
diagnostics. The core question is the model-by-memory-policy interaction:
whether capability substitutes for selective memory or enables the model to
exploit it better. Tinker remains limited to LoRA training of the external
discrete controller, starting with Qwen3.5 4B and confirming on Qwen3.6 35B-A3B
and Kimi K2.6 only after matched causal/next-use/observational label datasets and
fresh-client optimizer resume exist.

## [2026-08-11] experiment | Ran GPT-5.6 transport and found a memory-safety red line

Executed a 200-task GPT-5.6 Sol hosted competence screen through strict JSON
Schema output. All actions parsed and all provider receipts were bound. Served
memory succeeded on 94/97 tasks: active core 28/28, inactive archive 23/23,
proactive tool 25/25, and temporal graph 18/21. All three served failures
followed a newer conflicting graph edge. Twenty identical A/A prompt pairs had
zero action disagreement. The run cost estimate was $0.75577 for 240 responses.
Its bundle manifest is
`64f3f5da6a104bb8fa97c052f240985affa2a24e3e9728dbeb726a25d5c69329`.
An immutable v2 reanalysis binds the raw files while recording that the original
preflight predates exact source receipts. This is competence transport, not a
memory-policy effect.

Added a matched generated safety source for stored prompt injection, PII
canaries, stale permissions, and delayed activation. The 8-task pilot exposed
the exact served PII canary. The registered 80-task cell then produced 13/33
served failures versus 0/47 holdout failures: +39.39 points, Newcombe 95%
interval [+17.13, +56.32], Fisher exact p=`1.82e-6`. Stored prompt injection
failed 6/6 served cases and PII 6/11. One of eight repeated A/A prompts changed
action, so the stability gate also failed. Bundle manifest:
`c354223d562904b135d29399ce1b3a48fcaa4db3eeb1f5186eee2413022e6d0e`.
The tree was dirty and the source synthetic, so the finding is a red-line
replication target rather than publication evidence.

Extended the self-hosted actor to apply pinned tokenizer chat templates and the
common model-transport contract to explicit open checkpoint IDs. Added bounded
one-H100 profiles for Qwen3.5 4B/9B and two-H100 profiles for Qwen3.6 35B-A3B
and GPT-OSS 120B. The manifest compiler emits only digest-pinned Slurm jobs at
four to eight GPU-hours. Slurm resume now copies only a declared `screen/` tree
from a predecessor whose image, git SHA, and source SHA match; symlinks and
path traversal are rejected, and the predecessor remains immutable. Kimi
Linear remains blocked pending custom-code review; Kimi K2.6 remains a hosted
and Tinker controller cell.

Ran metadata-only Hub preflight in parallel for Qwen3.5 4B, Qwen3.5 9B,
Qwen3.6 35B-A3B, and GPT-OSS 120B. Every pinned commit resolved, and the locked
Transformers runtime loaded the local configs without remote code as
`Qwen3_5Config`, `Qwen3_5Config`, `Qwen3_5MoeConfig`, and `GptOssConfig`.
These small receipts are loader compatibility evidence only; full weights and
full-file publication receipts are still required on persistent cluster storage.

## [2026-08-11] harness | Added task-blind native memory systems and ran real Mem0 retrieval

Audited the exact open APIs, package metadata, licenses, and clean source trees
for Mem0 2.0.18, Graphiti 0.29.3, LangMem 0.0.30, and Hindsight 0.9.0. A reusable
preflight now computes repository tree, source-archive, license, package, lock,
and public-API hashes. The four-system internal receipt is
`28f21025431fc6900a6dba63d422a86cd7d8493ad3b1d99ce57a8ddb94927e65`.

Added `memory-system-v1`: the engine gives native systems ordered prefix CRUD
events, a query, an opaque session, and a budget, but withholds the oracle,
suffix, assignment, candidate flag, outcomes, and generator annotations.
Opaque ID/value rewriting removes literal `candidate`, `wrong`, and
`distractor` shortcuts. Every record, graph path, or summary must cite source
events and carry a cost and provenance receipt. The contract distinguishes
storage-plus-service from service-only treatment and forbids pooling them.
Recency, lexical, and exact temporal-graph controls pass in process and across
the validated JSON subprocess boundary.

Implemented the first native adapter against reviewed Mem0 source and installed
it through an exact combined lock. A CPU-only smoke used local Qdrant,
`infer=False`, no reranker, and a deterministic OpenAI-compatible embedding
endpoint. On one archive task it ingested 32 prefix events, made 33 embedding
calls per selection, returned four source-attributed records under the
256-token ceiling, and matched semantic evidence across repeated A/A executions
for both registered estimands and arms. The sealed artifact hashes to
`63cdafdf5ac0fefe26c8b1b2a7873697cee763d9bc066370f31abb21180b74a5`.
It is deliberately non-scientific and non-publication: the embedder was a smoke
fixture and no Docker, Slurm, actor-success, or external-benchmark receipt exists.

## [2026-08-11] harness | Froze native memory outputs for the large-model matrix

Closed a transport confound in the 0.6B-to-120B plus hosted-frontier actor
ladder. Native memory construction no longer reruns independently for each
actor. A new compiler seals each task-blind request and source-attributed
selection into a content-addressed bundle; the read-only runtime verifies the
upstream receipt, every request and selection hash, task source, budget, and
treatment mode. Self-hosted and hosted runners now bind that bundle in their
reports and provider preflights.

The Slurm manifest requires a host bundle path and SHA-256. The batch script
hex-decodes and revalidates the path, rejects symlinks, checks the file digest,
and mounts it read-only at a fixed container path. This keeps Qwen3.5 4B/9B,
Qwen3.6 35B-A3B, GPT-OSS 120B, GPT-5.6, Claude, Gemini, DeepSeek, and Kimi actor
comparisons on byte-identical evidence. An eight-task reference bundle produced
16 unique selections and passed replay validation; internal digest
`0f257c61c2d3f2894b44d3af62bff8933c748feaf44acae05ca2d4bf192c391f`.
This is transport evidence only, not a memory or model result.

## [2026-08-11] experiment | Ran Graphiti through embedded FalkorDB

Implemented a second source-pinned native adapter using Graphiti 0.29.3 public
triplet/search APIs and FalkorDBLite 0.10.0. The diagnostic uses deterministic
embeddings and a deterministic deduplication fixture, so it exercises graph
CRUD, indexing, search, temporal fields, and attribution without making an LLM
extraction claim. Both storage-plus-service and serve-only cells, both arms, and
all repeats passed source-attribution and token gates.

The run exposed a material systems cost: 171–180 embedding operations per
selection and 20.9–21.8 seconds full fresh-process latency after fixing the
common subprocess ledger to charge database startup. Served cells returned four
edges at 230 estimated tokens; holdouts returned three at 172. Artifact
`60aeb4c68f6809d2c8f4cc61553c827a468bd87be085d100140d9879d57da06f`.
This is CPU interface evidence only; semantic embeddings, construction LLM,
actor outcomes, warmed service throughput, Docker, and Slurm remain untested.

## [2026-08-11] experiment | Ran LangMem's native memory tools and store

Implemented the third source-pinned native adapter with LangMem 0.0.30 public
manage/search tools and the locked LangGraph 1.2.11 in-memory indexed store.
The adapter performs native create, update, delete, and search operations with a
strict source-attributed schema. Its LLM background manager is disabled so the
CPU cell measures tool/store behavior without free construction intelligence.

Both estimands, both visibility arms, and all repeats passed semantic A/A,
source-attribution, and token-budget gates on archive task `memory-000001`.
Candidate-present selections used 33 deterministic-smoke embedding operations,
served four records within 233 estimated tokens, and took 2.87–3.62 seconds per
full isolated first selection. Internal artifact
`494903d6f797f28d1abc32d9a49a7dc53111bbc8b7b42c6224bff907bad39e4a`;
file SHA-256
`c1a51789a7f08fc91cdc38efa0e92feedf1e7dcb48e53a9e74791154b684d94d`.
This is interface evidence only. Hindsight, semantic BGE embeddings, actor
outcomes, Docker, and Slurm remain open.

## [2026-08-11] experiment | Ran Hindsight retain/recall and isolated its runtime

Implemented the fourth source-pinned native adapter with Hindsight 0.9.0 public
retain/recall APIs and embedded pg0 0.15.1. The common root environment cannot
host it honestly: Hindsight requires `protobuf>=7.35.1` while Mem0 requires
`protobuf<7`, so Hindsight now has an isolated project and lock. Its reviewed
source tree also contains an absolute developer-machine `node_modules` symlink;
the archive doctor now requires that exact unsafe path to be declared, excluded,
and bound in the source-context receipt.

The run found two implementation mismatches worth preserving. Hindsight 0.9.0
rejects the documented `reranker=none` configuration, so the adapter uses its
public RRF passthrough reranker. Exact recall scores also drift by roughly
`2e-7` because recency is evaluated against wall time. The first eight-cell run
therefore failed the original exact-score gate. The corrected preregistered A/A
contract requires exact ordered evidence and maximum score drift `<=1e-5`; the
replacement run passed with maximum drift below `1.94e-7`.

Both estimands, both visibility arms, and all repeats passed. Candidate-present
cells made 33 deterministic-smoke embedding operations, served four records
within 234 estimated tokens, and took 30.06–33.85 seconds per isolated first
selection. Internal artifact
`6898f0e75c0da7ec6077217b283d78c2ed1dc19e0fb196c9bbac6489fedbde22`;
file SHA-256
`095c7e8d198ca82cf4f849f1133e9f4a142f292aca24bbc7a582045f0fea2fd0`.
Temporary database, profile, log, and lock state was removed after execution.
This closes native interface reproduction for the four mandatory OSS systems;
pinned semantic embeddings, model outcomes, Docker, and Slurm remain open.

## [2026-08-13] experiment | Ran contained Qwen memory screens and found a causal-policy signal

Made the H100 path operational without sudo. SmolVM 1.7.7 passed CPU
containment but failed CUDA with `invalid device pointer`, so GPU experiments now
use a validated Docker-under-Slurm discovery launcher. It binds the exact image,
source archive, git revision, model snapshot, command, allocation, and artifact
root; disables networking; uses a read-only root with no capabilities and
`no-new-privileges`; maps only the assigned GPU IDs; and checkpoints to persistent
storage. The current image is
`sha256:ba360ea13ea50e77e4900cb258c4dc73156060295abd381899f90f9991cedd10`,
source archive
`8c51687b22ea710b6d478c65d831dacd3da89b88092328e32e6009ebfa2b841a`,
git `581ded8df71564b0212d8af5dcd401257aa6a28f`. Slurm is operational for
single-user discovery but lacks cgroup-v2 device isolation, so these are not yet
publication-cluster attestations.

Fetched and independently reverified full pinned Qwen3.5-4B, Qwen3.5-9B, and
Qwen3.6-35B-A3B snapshots in fresh network-disabled jobs, without remote code.
On the same sealed 200 tasks, Qwen3.5-4B reached 75.73% served success and
Qwen3.5-9B reached 81.55%. Both had 100% valid JSON, exact A/A replay, and zero
safety failures, but both failed the preregistered 80% per-stratum competence
gate: 4B failed all four strata and 9B failed active-core and archive. The
Qwen3.6-35B-A3B screen is running on two H100s under job 71.

The direct-record Qwen3.5-4B causal audit produced paired ATE 0.3143,
AIPW-to-oracle gap 0.0224, AIPW/oracle Spearman 0.882, policy/oracle Spearman
0.904, and learned paired-audit value 0.971 versus always-serve 0.800. A frozen
reference memory bundle reduced served success to 50.49% and active-core to 0%,
showing that a plausible recency/query-overlap selector is not a downstream
utility oracle. Qwen3.5-9B preserved the directional causal signal, with paired
ATE 0.2571 and high rank correlations, but failed the registered AIPW
calibration gate: absolute ATE gap 0.0961 versus the 0.05 maximum. These are
promising one-seed, 35-audit kill pilots, not confirmation. No 2,400-episode or
Kimi/Tinker wave is eligible until the larger actor and calibration gates pass.

## [2026-08-13] research | Narrowed memory novelty and corrected discovery evidence

Ran a same-day primary-source, official-code, FieldTheory bookmark, local wiki,
and Local Search delta audit. The machine ledger now contains 57 sources and 42
repository pins. New direct collisions include CommitKV for paired deletion
effects, Controlled Memory Interference for generic interference, MESA for
multi-structure routing, Nemori for prediction-error memory formation,
AttriMem/RoMeRL for fine-grained credit, Retain-or-Consolidate for operator
choice, MemHarness/MRAgent for reconstruction, and GEM/MemState for state-level
evolving CRUD. The admissible CMHT novelty statement is now limited to
prospective known-propensity first-eligible-use assignment of persistent
semantic items, executable utility, cross-fitted population estimation, paired
deterministic audit, and a strictly past-only gate.

Added current cost, authority, poisoning, repair, and integrity controls and
expanded the OSS matrix with SimpleMem, MIRIX, EverOS, MemoryOS, and Mnemis.
Corrected the Hindsight benchmark-license entry to unresolved. The four core
sidecars are now explicitly described as ephemeral interface prototypes: each
rebuilds native state inside one selection request and its purge response is
not a backend deletion proof. Their current artifacts do not establish
persistent CRUD, restart recovery, authorization, tenant isolation, delayed
poisoning, or repair.

An adversarial implementation audit corrected the previous entry's causal
language. The generated source encodes effect classes through source-quality,
contradiction, and future-use fields; the large Qwen correlations are therefore
engine/estimator and actor-transport evidence, not a learned memory-policy
result. Qwen3.5 4B and 9B fail promotion gates. The Qwen3.6 35B 200-task run and
the 4B recency run failed same-arm A/A replay. The YAML's registered control,
split, update/delete, safety, public-benchmark, and three-seed surfaces are not
yet executed.

The older Docker jobs also bind source hash `8c51687b...` without retaining
that exact archive, so they remain discovery-only. Slurm job 76 verified the
sealed image and allocation but failed before tests because the image excludes
pytest. The Dockerfile now has a default-off, labeled `INCLUDE_DEV` build path.
A new deterministic archive
`c062a6f701ee3b2303b3c120bf200161ce85d5d4678e69e141baeb004df98011`
was retained locally and on the H100 host. Clean build job 79 was canceled after
Ubuntu/NVIDIA package-index connectivity stalled; it produced no image and no
existing image or data was removed. Contained tests, clean commit/image/SBOM,
persistent native-system doctors, real controls/seeds, and one public
`TaskSource` remain hard gates before a scientific or Gauntlet PASS.

## [2026-08-13] experiment | Sealed the contained offline memory doctors

Retained a deterministic 270-file discovery source archive with SHA-256
`10e598c71fa523c94a8f626c9dd93514b08f850f6a3bdf0bd87072cbf16edc7c`
locally and on the H100 host. It records git
`581ded8df71564b0212d8af5dcd401257aa6a28f`, `worktree_clean=false`, and
`scientific_result=false`. Slurm build job 81 failed before Docker because the
old scheduler executes `--wrap` through a POSIX shell that rejects
`set -o pipefail`; its receipt is retained. Job 82 then built the same source
with a POSIX wrapper and no package-network dependency into image
`sha256:d55c09031bcf3d816eaa3371cea387b9ff3463de8dd0029358a92e937faea9b0`.
The image labels the exact source archive and base image, and explicitly records
that development dependencies are absent.

After remote dry-run and Slurm admission checks, job 84 ran the fixed offline
doctor inside a one-H100, network-disabled, read-only Docker container under
Slurm. It passed Python compilation, the 57-source/42-repository source ledger,
all five memory experiment contracts, and the six-model/five-provider registry.
The sealed run reports `reason=completed`, `exit_code=0`, and binds manifest
SHA-256 `c25f333a8f8a8ebf1c12ed0dba896359d2d3fa49d104ade9ebf901f8514eb8c9`.
Artifacts are retained under
`data/results/contained-memory-doctors/job-84/` and the H100 run root.

This closes only the contained configuration/transport doctor. The source is
still a dirty tree, no SBOM tool is installed, and the no-dev overlay cannot run
pytest. It does not repair same-arm replay, execute the registered control or
three-seed matrix, add a public `TaskSource`, establish persistent OSS-system
semantics, or turn the engineered generated task into memory-policy evidence.

## [2026-08-13] research | Narrowed memory novelty and corrected live contracts

Refreshed the primary-source memory ledger to 69 sources and 55 immutable
repository pins. Memory-R2 now blocks broad counterfactual or causal
memory-credit wording; MemCon is a required learned operation-controller
control; TARL occupies typed counterfactual ledgers; MSCE occupies
memory-to-skill crystallization; MemoHarness is an experience-reuse control;
and memorywire plus Portable Agent Memory make portability an infrastructure
baseline rather than the research direction. The maximum surviving CMHT claim
remains the prospective known-propensity first-eligible-use population trial
with executable utility, cross-fitting, paired audit, and past-only deployment.

The source validator now rejects duplicate YAML keys after a live duplicate
would otherwise have silently overwritten Memory-R2 and MemCon records. The
LongMemEval screen no longer falsely claims complete control-matrix execution;
it is labeled as a bounded one-frozen-bundle transport screen. Focused source
and experiment contract tests pass. No model run or scientific result was
produced by this update.

## [2026-08-13] harness | Registered an evidence-preserving H100 replay doctor

Closed the diagnostic-design gap behind the failed Qwen same-arm runs. The
Transformers actor now fixes deterministic Torch/CUBLAS settings, eager
attention, TF32 and reduced-precision reductions, and records prompt/completion
token-ID hashes plus the resolved device-map hash. Collection writes both
outcomes and their field-level comparison before aborting an A/A mismatch.

Added a bounded host-Docker/Slurm compiler for Qwen3.5 4B/9B and Qwen3.6
35B-A3B. The primary 35B falsifier uses tasks 0, 4, 106, and 180, including both
historical failure indices, across seeds 42/43/44, three repeats, and two cold
loads. The Slurm launcher independently verifies that every declared seed is
actually present in the workload argv. The 35B ceiling is 2 H100s for two
hours. No GPU job has run from this new contract.

Also verified the actual public-source boundary: LongMemEval converts all 500
cleaned-oracle tasks into 495 hash-bound groups, while denying candidate
selection access to the future question, answer, `has_answer`, and
answer-session labels. This is source-adapter evidence only. Corrected the
Hindsight record because its current artifact has an empty embedding-model
receipt list despite using BGE transport. Full local verification is green:
217 tests, Ruff, lockfile, memory source/experiment/provider validators, JSON,
shell syntax, and diff checks all pass.

## [2026-08-13] harness | Corrected public-task semantics and proved native Mem0 lifecycle on H100

Corrected the LongMemEval integration after an adversarial source audit. The old
32-row prefix was entirely temporal-reasoning, and its oracle answer-session
artifact had been mislabeled as inactive-archive/graph retrieval. The adapter
now labels every row `oracle_context`, explicitly denies retrieval/graph claims,
pins a round-robin 32-task panel across all six native question types, and
reports byte-exact success as a diagnostic only because the official semantic
judge is not implemented. The full 500-task manifest is `c8180436…`; the
balanced panel is `ad8bc80e…`.

Replaced Mem0's ephemeral per-call adapter with session-scoped persistent
Qdrant/SQLite state, an fsynced idempotency journal, divergent-prefix rejection,
native inspection, and delete/reset-backed scoped purge. Local tests and the
native lifecycle doctor passed. The first contained rerun correctly failed on a
literal `~/.mem0` write under the read-only root; the sidecar now gives Mem0 an
explicit state-root HOME/MEM0_DIR rather than relying on a host passwd entry.

Slurm build job 114 produced image `sha256:5ad12b72…` from retained dirty-tree
archive `b26b196d…`, reviewed base image `sha256:dc720e12…`, and locked wheel
manifest `7471c56f…`, with no package network and no sudo. Network-disabled,
read-only Docker/Slurm job 116 then committed 27 events into 26 native records,
preserved the journal and retrieved evidence across a fresh sidecar process,
purged the native store, and proved absence after another restart. Job 118
passed compileall, the 92-source/75-repository ledger, six memory experiment
contracts, the six-model/five-provider registry, source-contract fixtures, and
the reference persistent transport doctor. Both jobs used one allocated H100
and sealed source/image/model/system/container/termination receipts.

These are lifecycle and contained-contract results only. The exact source tree
is still dirty, the image has no SBOM or pytest dependency, Graphiti/LangMem/
Hindsight remain ephemeral, and no official public benchmark, matched 200-task
system comparison, cross-tenant/poisoning/repair cell, replay-doctor result, or
memory-policy claim has been produced.

## [2026-08-13] review | Closed lifecycle, resume, and Tinker budget defects

The structured pre-commit review found that Mem0 compared already-committed
prefixes only by event ID. The adapter now recomputes and verifies every
committed event digest before retrieval. The lifecycle doctor injects a
same-ID/different-value prefix, requires fail-closed rejection, reopens the
sidecar, and verifies the journal and native record count were unchanged before
purge. The same review also found a root-symlink escape in the general Slurm
resume copier; it now rejects a symlink at the requested root, resolves source
and destination, and requires both to remain within their job directories.

A second pass found that the causal-memory Tinker ceiling charged one training
arm although the contract requires three matched LoRA arms. The cost model now
multiplies the stage ladder by the three trainable arms. The disabled contract's
honest ceiling is $18.0797 and its declared maximum is $18.10; no authenticated
or paid run occurred. After focused tests, the final autoreview returned no
accepted/actionable findings.

Optional dev-wheel build job 119 was canceled after the cluster's package host
stalled without writing a wheel, so contained full pytest remains open. The
corrected runtime was nevertheless resealed as retained archive `a3aa58e8…` and
image `sha256:51067ef7…`. Network-disabled, read-only H100 job 122 passed all
eight Mem0 lifecycle gates, including byte-divergence rejection without state
mutation. Job 124 passed compileall, the 92-source ledger, all six memory
experiment contracts, provider validation, source-contract fixtures, and the
reference transport doctor. These remain dirty-tree discovery receipts without
an SBOM, full contained pytest, or scientific memory-quality result.

## [2026-08-13] research | Added same-day memory collisions and stronger simple controls

Used the local wiki, FieldTheory's 1,957 enriched X bookmarks, lsearch, the
official arXiv feed, and official repository metadata to extend the memory
ledger from 92 to 108 sources and from 75 to 79 immutable repository pins. The
new records include RippleMem, LycheeMemory V2, ReFind, ERSkill, Router-Mem,
V-Mem, ProGraph, ToolAtlas, ScrubJay-MEM, PMMC, and governance, procedural,
persona-graph, retrieval-fusion, and federated-memory work. V-Mem, ProGraph,
SuperLocalMemory 4.0, and PGMem have exact repository commits and honest
license/test caveats; ToolAtlas's paper-declared repository was unavailable.

The result narrows rather than expands the novelty claim. Raw chat logs plus
ReFind-style agentic BM25 are now a mandatory floor; graph memory must also beat
graph-free ProGraph at equal bytes, calls, tokens, and wall time. Router-Mem and
ERSkill occupy memory-depth and retrieval-program routing, Lychee occupies
segment consolidation, ScrubJay occupies type-conditioned decay, and ToolAtlas
occupies provider-side portable tool memory. CMHT still survives only as the
known-propensity prospective first-service population estimand with executable
utility, cross-fitting, paired deterministic audit, and a strictly past-only
gate. Focused source validation and tests pass. No model, GPU, or scientific
quality run was performed.

## [2026-08-13] harness | Added raw-log and graph-free mechanism falsifiers

Deepened the existing `MemorySystem` seam with two deterministic controls rather
than adding runner branches. `raw-log-rrf` indexes unmodified prefix events,
combines turn-level BM25 with archive-group reciprocal-rank fusion, expands local
event context, skips previously inspected groups, and uses bounded bridge-token
feedback under the registered read budget. `profile-expansion` groups exact
valid records into entity profiles and follows substring entity mentions without
constructing explicit graph edges. Both use the shared byte/token/read/write
ledger, treatment filtering, immutable receipts, and frozen-selection bundles.

The names and receipts deliberately avoid false reproduction claims:
`raw-log-rrf` omits ReFind's LLM ReAct controller and explicit calendar filter;
`profile-expansion` omits ProGraph's LLM profile/residual co-extraction and
embedding relevance gate. Public-interface tests prove deterministic local
expansion, bounded multi-round bridging, graph-free entity traversal, hash
binding, frozen-matrix registration, and LongMemEval compiler coverage. This is
mechanism and transport evidence only; no actor/model quality result was run.

Contained discovery job 127 then found a source-overlay portability defect
before executing the control workload. The builder used `umask 077`; because
the normalized source archive contains file entries rather than directory
entries, `tar` auto-created the extracted tree as mode 700/600. Docker preserved
those permissions, and the required unprivileged container UID 65534 could not
read `scripts/verify_compute_provenance.py`. The job is retained with
`reason=workload_failed`, `exit_code=2`, and no control result. Both reusable
source-overlay builders now make the reviewed extracted context read/traversable
before the image build; the repaired image must use a new source digest.

Repaired Slurm build job 128 sealed archive `b4b0bca6…` into discovery image
`sha256:b63cc96d…`. After remote dry-run and admission checks, job 130 ran with
one allocated H100, eight CPUs, 16 GB, network disabled, a read-only root,
dropped capabilities, and UID 65534. Source/image/model/container doctors passed;
the job reproduced local matrix content root `f143df12…` and wrote 32 frozen
selections each for BM25, raw-log RRF, profile expansion, and the temporal graph.
It exited 0 with `reason=completed`. The complete 1008 KiB evidence bundle is
retained under `data/results/contained-memory-controls/job-130/` and on the H100.
This remains dirty-tree discovery/control-transport evidence without an SBOM,
paper-faithful external systems, actor inference, or a scientific quality result.

## [2026-08-13] experiment | Froze the public LongMemEval control matrix on H100

Compiled the immutable 32-task LongMemEval control-freeze contract against
dataset revision `98d7416c…` and SHA-256 `821a2034…`, retained source archive
`b4b0bca6…`, discovery image `sha256:b63cc96d…`, and the full pinned
Qwen3.6-35B-A3B receipt at revision `995ad96e…` / artifact root `8ac6d764…`.
Local validation, remote validation, and Slurm `--test-only` passed before the
job was submitted from the persistent `cotcodec` tmux session. No `sudo`, host
package installation, or login-node compute was used.

Scheduler job 132 ran inside the network-disabled, read-only,
capability-dropped Docker runtime as UID 65534 on one H100. Source, image,
container, dataset, and the complete 71.9 GB model artifact all verified. The
job froze no-memory, recency, LRU, lexical, BM25, raw-log RRF, graph-free
profile expansion, temporal graph, and reference-hybrid bundles over the exact
balanced panel. The canonical matrix root is `5f9001fb…`; all nine canonical
bundle identities re-verified after copying the full artifacts to
`data/results/contained-memory-controls/job-132/`. Termination is
`reason=completed`, `exit_code=0`.

The result is selection/provenance evidence only. LRU is ineligible because the
public tasks contain no explicit access events; the reference hybrid remains a
task-blind diagnostic. The LongMemEval artifact supplies oracle-context
sessions, the official semantic judge is not implemented, and no actor ran, so
this does not establish retrieval quality, graph quality, or a memory-policy
effect. The next legitimate actor cell remains blocked on clean publication
provenance and clean-image replication of the strict replay doctor.

## [2026-08-13] experiment | Passed the strict Qwen 35B replay falsifier

Compiled the registered Qwen3.6-35B-A3B replay doctor with a 2×H100,
4-GPU-hour ceiling against retained archive `b4b0bca6…`, image
`sha256:b63cc96d…`, and the fully verified 71.9 GB model artifact at revision
`995ad96e…` / root `8ac6d764…`. Local validation, remote validation, and Slurm
admission passed before submission from a dedicated `replay35-strict` window in
the persistent `cotcodec` tmux session.

Contained job 134 ran tasks 0, 4, 106, and 180 in both serve and holdout arms,
with seeds 42/43/44, three same-load repetitions, and two cold model loads. All
48 summarized task-arm-seed-load rows passed identical pre-model inputs, exact
completion hashes, exact tool/action hashes, and exact cross-load/cross-seed
signatures: 144 generations, zero failures. This includes the two historical
failure tasks. The job exited 0 with `reason=completed`; the report hashes to
`ba87fd55…` and the complete run is retained under
`data/results/memory-replay-doctors/job-134/`.

This is a strict kernel/transport falsifier, not memory-policy evidence. It
shows that eager attention plus deterministic Torch/CUBLAS settings eliminate
the previously observed four-task drift under this topology, but the run still
binds a retained dirty-tree archive and an image without an SBOM. A clean-image
replication and the 200-task rerun remain mandatory before promotion.

The run also exposed two workflow costs. The batch and workload each re-hash
the same 71.9 GB artifact, and the archived replay doctor checkpointed only
after a whole seed/reload block. The next source revision now writes
fsync-backed progress after every task-arm case, acknowledges USR1 only after a
durable checkpoint, refuses contract or plan drift, and compiles an exact
predecessor `replay-doctor` subtree resume. Forty-three focused tests pass; this
checkpoint revision has not yet run under Slurm and did not alter job 134.

## [2026-08-13] harness | Implemented the unmatched full-prefix ceiling

Added `full-prefix-ceiling` as an explicit diagnostic `MemorySystem`, not as a
matched retrieval arm. It renders every ordered raw prefix event into one
source-attributed block, charges every serialized byte, estimated injected
token, and prefix write, makes zero retrieval reads, and never silently
truncates. If the registered diagnostic budget cannot hold the entire prefix,
the harness fails the cell. The frozen-control manifest marks it
`diagnostic-unmatched`, `eligible_for_primary=false`, so it cannot win the
strongest matched-control comparison.

Measured over the exact pinned LongMemEval-32 panel, the full-prefix arm uses
6,721 estimated injected tokens at the median and 20,303 at the maximum (82,370
maximum serialized output bytes). A future actor diagnostic therefore needs a
separate 32,768-token budget. The common 256-token matrix remains unchanged.
Twenty focused system/matrix tests and the six experiment validators pass. No
new image or H100 actor job was launched for this post-archive code; clean
publication provenance remains the next gate.

## [2026-08-13] harness | Sealed family splits and learned next-use control

Versioned the generated memory source as `memory-events-v3` so entity, value,
graph-node, and distractor namespaces are scoped to one cross-stratum family.
Added a content-addressed split compiler that produces the registered exact
1,440/480/480 partition and fails on source, task, count, family, or digest
drift. This fixes the previous false assurance in which nominal families could
still recycle entity/value identifiers across partitions. The v3 split is
identifier-family disjoint; shared structural templates remain an explicit
external-validity limitation.

The v3 generator now also emits plain, supersession, and delete-then-recreate
histories. UPDATE invalidates the prior matching record in both the direct
engine and task-blind request materializer, and invalidated/deleted records can
no longer leak into direct actor frames. The randomized candidate stays a
normal retained item, so these history variants do not silently change the
first-service treatment.

Implemented `learned-next-use` as a deliberately noncausal comparator. Offline
future-use labels are opened only for TRAIN, its fixed L2 grid is selected only
on DEV, and the model freezes before TEST. Runtime features are query-blind and
exclude oracle, candidate, source-quality, contradiction, stratum, suffix, and
test-label fields. The artifact, split, and every label/data lineage digest are
bound into immutable receipts. The freeze path refuses the learned cell without
that artifact.

A complete local CPU proof compiled 39,804 TRAIN and 13,241 DEV record rows,
with `test_labels_opened=false`, split root `41f9866f...`, and learned artifact
`5de83ed8...`. It separately froze 400 serve/holdout full-prefix selections over
200 tasks under the diagnostic 32,768-token budget at bundle `0f183a1a...`.
These `/tmp` outputs are reproducibility proofs, not scientific results.

The model runner and Slurm compiler now expose the full-prefix lane only through
`full-prefix-diagnostic`: storage-and-service only, separate bundle and budget,
`diagnostic-ceiling` evaluation, and permanent exclusion from strongest-control
selection. The full repository gate passes 261 tests, Ruff, `uv lock --check`,
six memory experiment contracts, the 108-source/79-repository ledger, and the
six-model provider registry. No H100 workload was launched because the shared
tree still lacks clean commit/archive/image/SBOM provenance.

## [2026-08-13] research | Added activation and streaming-memory falsifiers

Refreshed the primary-source memory ledger to 111 sources and 83 immutable
repository records across 77 sources. Pinned the official ForesightKV
training/evaluation tree at `fdb541f`, EvoMemBench at `aa4cea8`, StreamMemBench
at `b329655`, and PM-Bench at `e1093c4`. ForesightKV, EvoMemBench, and PM-Bench
have no detected root license at those revisions; StreamMemBench code is MIT,
while its EgoLife-derived benchmark data retains separate upstream terms.

The scientific roles are deliberately distinct. PM-Bench is the deterministic
prospective-memory test for inactive intentions becoming active at time/event
cues, proactive state monitoring, and stale-intention suppression. StreamMemBench
tests evidence use, feedback incorporation, and later reuse. EvoMemBench tests
whether conclusions survive in/cross-episode and knowledge/execution settings
against strong long-context controls. None identifies the proposed randomized
first-service estimand, and none is permission to copy a paper-reported ranking.

The validator now requires every repository record to be linked by a primary
source URL and emits an explicit reproducibility audit, including machine JSON
through `scripts/validate_memory_sources.py --audit-json`. Current coverage is 34
paper-only sources, 28 unresolved repository licenses, and zero sources whose
scientific result is labeled locally or externally reproduced. This prevents an
immutable code pin from being mistaken for a reproduced result. LycheeMemory V2
remains paper-only because the Apache-2.0 LycheeMem service repository does not
claim to implement arXiv:2608.12990.

Updated the same-day frontier scan, Direction 17, and `memory.json` with the
external-validity order: PM-Bench, Mem2Act, StreamMemBench after data-rights
review, then EvoMemBench. No H100 job was launched; clean commit/archive/image/
SBOM provenance remains the queue gate.

## [2026-08-13] research | Expanded controls and sealed the official LongMemEval judge

Expanded the primary-source memory ledger to 126 sources and 97 immutable
repository records across 91 sources. Added TiMem, MemForest, Infini Memory,
DeltaMem, and H-Mem from Local Search discovery, then independently identified
MemPalace, ReMe, agentmemory, Honcho, Acontext, memU, ReMemR1, and TencentDB
Agent Memory. Every repository is bound to an exact commit and license status;
paper and vendor numbers remain explicitly unreproduced. The bounded portfolio
adds only MemPalace, as the immediate verbatim raw-log/no-write-model falsifier,
and remains capped at 108 H100-hours.

Closed two concrete LongMemEval false-passes: an all-SERVE bundle can no longer
contain a HOLDOUT or hidden candidate, and a judge packet cannot be empty or mix
source, visibility, assignment, or evaluation contracts. Cases now bind the
task manifest, world provenance, source bundle, actor output, and model receipt.

Implemented the exact official semantic-judge transport for
`gpt-4o-2024-08-06`: pinned Chat Completions endpoint, temperature zero, one
sample, ten-token cap, prompt-source revision/hash, OpenAI SDK version, exact
request hash, full provider response, token counts, atomic per-case response
journal, fail-closed resume, and a sealed score bundle. The provider registry
now includes the exact judge model. The packet compiler validates the registered
experiment and persists its hash. No API call or H100 job was launched. The
existing Docker-under-Slurm profile has networking disabled, so a separate
restricted-network judge profile plus clean archive/image/SBOM remains required
before the 500-task official evaluation can execute.

Added distinct full-source control-freeze and all-SERVE actor stages to the
contained H100 compiler. The manifest and batch script now distinguish a
three-seed randomized assignment matrix from a deterministic seedless all-SERVE
job and fail closed on crossed flags. The complete repository gate passes 286
tests, Ruff, lock validation, all memory source/portfolio/experiment validators,
the seven-model/five-provider registry, batch syntax, JSON validation, and diff
whitespace checks.

## [2026-08-13] research | Narrowed CMHT and added fail-closed publication admission

Extended the primary-source search through 2026-08-14 UTC. The validated memory
ledger now contains 135 sources and 103 immutable repository pins, with 38
paper-only records, 30 unresolved repository licenses, and zero reproduced-result
labels. Added MemRL, U-Mem, AEL, MindMemOS, epsilon-MemEvo, QCR, Tidemark,
ReasoningBank, and MemAudit/Antivenom. These works occupy broad outcome-trained
utility, stochastic serving, active/archive CRUD, procedural consolidation, and
counterfactual replay. The surviving CMHT statement is restricted to the four-part
prospective first-service design recorded in Direction 17.

Implemented a publication-only source archive, live OCI/SBOM capsule-candidate verifier,
complete-control claim-wave compiler, Slurm admission binding, and actor/resume
identity checks. The path rejects dirty Git state, non-byte-equivalent archives,
fabricated image inspections, SBOM substring matches, mutable or absent repository
digests, incomplete control rosters, and bundle/control drift. Claim admission
also requires a detached Ed25519 signature over the complete capsule, matrix,
experiment, wave, model/actor, bundle, and Slurm-script contract from a protected
external, digest-pinned administrator trust store; proposal-workspace keys are rejected.
The complete suite passes 315 tests alongside Ruff, lock, syntax, ledger,
experiment, provider, JSON, and diff gates. No H100 or API workload ran because
the shared tree is dirty and the administrator trust root is not provisioned,
so a publication claim cannot be admitted by design.

## [2026-08-14] research | Added the matched dense-BGE retrieval floor

Implemented `dense-bge-retrieval-v1` as the missing raw semantic retrieval
control. It receives only task-blind prefix records, encodes canonical entity,
key, and value passages, applies the pinned BGE retrieval instruction to the
query only, ranks normalized vectors by cosine with stable recency/ID ties, and
uses the same top-4, 256-token, source-attributed budget as BM25. Every encoded
query and passage is charged as an embedding operation.

The control binds `BAAI/bge-small-en-v1.5` at revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, the model artifact and full receipt
digests, 384 dimensions, a 512-token maximum, and normalized CLS pooling. This
found and corrected a real transport defect: the prior local HF service used
mean pooling despite the pinned model card specifying CLS pooling. Historical
BGE-backed native smokes therefore remain interface evidence and require rerun
before any semantic comparison.

Added direct and loopback adapters with fail-closed checks for identity,
receipt, pooling, dimensions, normalization, finite vectors, usage, and service
origin. The standalone and matrix freezers can now load the verified local
checkpoint; the Docker/Slurm freezer binds BGE as its workload model; and the
complete administrator-signed roster includes the dense control. The registered
LongMemEval methodology records exact rendering, model, cost, budget, and stop
conditions while keeping the arm scientifically unexecuted.

All 323 tests pass with Ruff, lock, compile, six experiment contracts, the
135-source/103-repository ledger, the 108-H100-hour portfolio, JSON validation,
Slurm syntax, and diff checks. No H100/API job ran because the tree is dirty and
no clean SBOM-bearing signed claim wave exists.
## [2026-08-14] research | Bounded the MemPalace raw-retrieval control

Verified MemPalace's official repository at commit `906b918a`, tree
`98789ad0`, MIT license, deterministic Git archive, runner, and current lock.
The released raw LongMemEval path is not a general memory lifecycle: it creates
one user-only document per session, rebuilds an ephemeral Chroma collection per
question, and retrieves with default ONNX MiniLM. Its committed artifact has
500 unique rows and records 483 custom any-hit top-five successes, but it was
introduced under ChromaDB 0.6.3 while the current lock resolves 1.5.7. The
headline is also not official LongMemEval recall-all and cannot be compared as
such.

Added a task-blind append-only MemPalace mechanism port with exact source,
runtime, MiniLM, accounting, attribution, and fail-closed backend contracts.
Added a released-artifact auditor that rejoins the pinned dataset and recomputes
both custom and official metric definitions while retaining a non-reproduced
status. The live 500-row audit reproduces custom any-hit@5/10 arithmetic at
96.6/98.2% and, after excluding 30 abstentions, official all-hit@5/10 at
85.7447/93.4043% and NDCG@5/10 at 87.4322/89.0094%. These are historical
artifact-integrity recomputations, not a current-lock run.

Added a hash-chained per-question driver around the exact upstream retrieval
function with strict input allowlisting, pre-import source verification, atomic
progress, USR1 checkpoint, fresh-job resume, incomplete-tail recovery, and
strict completed-bundle recomputation. Added full 555-file source-context and
safe offline MiniLM prestagers, plus a pre-Docker immutable-base admission
wrapper and candidate image binding source, lock, runner, base, model archive,
and extracted model root. Twenty-seven focused tests and all 350 repository tests
pass, along with Ruff, lock, compile, memory/experiment/provider validators,
JSON, Slurm syntax, and diff checks. Independent autoreview ended CLEAN. The
image has not been built or SBOM-sealed; production Chroma execution, live CPU
Slurm validation, two-run current-lock reproduction, and the 500-task actor
bundle remain pending. No H100 or API job was launched.

## [2026-08-14] experiment | Reproduced MemPalace current-lock retrieval and exact port fidelity

Completed two fresh pinned-current-lock direct MemPalace runs over all 500
LongMemEval tasks. Their ordered rankings are byte-identical, and the sealed
pair report hashes to `a94bbfbfcd8b8f2d1105b18711989143fabb6338951700823783d46ca01bd6fe`.
The reproduced custom any-hit@5/10 values are 96.6/98.2%. On the 470
non-abstention tasks, the separately reported official all-hit@5/10 values are
85.7447/93.4043% and NDCG@5/10 is 87.4322/89.0094%.

Preserved two failed port attempts rather than weakening the gate. V17 exposed
13 rows where one raw session ID occurs at multiple timestamps; v18 passed that
boundary but failed because the upstream runner preserves empty user turns as
newline separators. The v19 adapter now assigns occurrence-aware opaque entity
IDs, preserves source order and raw user bytes including empty turns, and keeps
candidate selection restricted to non-empty turns.

Contained Docker-under-Slurm jobs 208-211 built the v19 discovery image, ran the
500-row preprocessing doctor, and produced self-attested discovery SBOM/runtime
receipts. Job 212 then ran the production port on one H100 for six minutes and
matched all 500 unique upstream tasks exactly on query bytes, session roster,
session order, session text, full ranking, top five, and top ten. Its journal
and report hash to `5d6961ae4d54f84e7ce20c6faa5c71691a420000437e1860e4c2e977ffbf734d`
and `685afc9550b9b61481606e26a1b9b10b60f1ec8024c62795345402e4c16d97a9`.
Fresh Slurm job 213 revalidated the completed bundle in 17 seconds without any
artifact-hash change.

This closes current-lock reproduction and matched-port-equivalence only. The
result remains `scientific_result: false`: it says nothing about persistence,
CRUD, answer quality, or whether MemPalace beats another memory system. The
passing image came from a dirty discovery archive and its runtime attestation is
self-authored. A clean externally attested rebuild, matched all-SERVE actor
wave, and official semantic judge remain required before a scientific claim.

## [2026-08-14] research | Expanded the memory ledger and fixed the next experimental order

Ran a bounded primary-source and official-code memory scan plus a FieldTheory
bookmark audit. The strict same-day arXiv query returned no August 14
submissions at the cutoff, but a backfill added PAST-Bench, Reliable
Post-Retrieval Assembly, A-TMA, Memory Worth, MemGuide, CoEvo-Mem, LeanMem,
HiGram, PMCoder, EA-Graph, MAPLE-Guard, and MAFIA. Two same-day code releases,
memore and ThreeDogCoral, were admitted only as deterministic consolidation and
fixed-tiering controls. The bookmark audit added pinned GBrain, Claude-Mem,
SkillOpt, Memvid, and Hermes `/learn`; viral performance claims unsupported by
their pinned trees were explicitly rejected.

The validated ledger now contains 154 sources, 114 pinned repository records
across 108 sources, two pinned artifacts, and 14 labeled benchmark claims. It
also exposes 46 paper-only sources, 32 unresolved repository licenses, and zero
source results labeled locally or externally reproduced. PAST-Bench becomes the
longitudinal save/retrieve/reuse/update pathway benchmark; Reliable
Post-Retrieval Assembly makes evidence extraction and answer-policy execution
explicit evaluation layers; Memory Worth is the cheapest observational value
control; MAPLE-Guard and MAFIA extend the poisoning matrix across lifecycle
transitions and retrieval-competitive query-only attacks.

The scan did not produce a new broad memory direction. CMHT survives only as
the exact four-part prospective known-propensity first-service design. The next
claim-relevant GPU cell is the full-500 MemPalace all-SERVE Qwen3.6-35B actor
floor alongside no-memory, BM25, dense BGE, and raw-log RRF, followed by the
sealed official semantic judge. A win would establish a required simple floor,
not evidence for active/inactive paging, graphs, consolidation, procedures,
causal credit, or safety. PAST-Bench and graph/pager/controller cells remain
downstream of that flat quality matrix.

## [2026-08-14] harness | Closed local MemPalace actor-admission and source-overlay gaps

Made the MemPalace floor fail closed before actor inference. Its factory now
requires the separately registered whole equivalence-bundle root, exact
five-file evidence roster, completed hash-chain, 500-task pass, contract hash,
and both runtime receipts. Frozen bundles preserve canonical admission evidence,
and the actor verifies both the expected system ID and evidence digest.

Closed the source-overlay time-of-check/time-of-use boundary by snapshotting,
hashing, and extracting from one no-follow archive file descriptor. The remote
builder now pins its own and the extractor's hashes and resolves an immutable
repository digest to the expected local image ID before a no-pull build.

The final scoped adversarial review reported no actionable P0/P1 finding. The
complete local repository suite passed 394 tests in 177.54 seconds; Ruff, lock,
memory-source, portfolio, experiment, provider, architecture, JSON, Slurm, and
diff gates also pass. No image, Slurm job, H100 actor, or official judge call was
launched. The worktree remains dirty, the retained historical launcher lacks
the new helper hashes, and a separately registered exact equivalence-bundle
root plus clean external publication attestation are still required.

## [2026-08-14] research | Admitted the PAST-Bench source and sharpened active/inactive controls

Audited eight clean official checkouts at immutable commits. Added seven
licensed sources to the ledger: LightMem2, JiuwenMemory, Shodh Memory, Sage
Wiki, MemoryStress, Mnemon, and Fidelis. The ledger now contains 161 sources,
121 repository records across 115 sources, two pinned artifacts, and 18 labeled
benchmark claims; 46 sources remain paper-only, 32 repository licenses remain
unresolved, and zero source result is labeled reproduced.

The code changed the active/inactive interpretation rather than producing a new
broad direction. LightMem2 has a real protected-active to archived-stub to
explicit-fault-recovery lifecycle, but for completed tasks and tool outputs.
Shodh's production residency is monotonic Working→Session→LongTerm with no
demotion; Mnemon's active spaces scope recall; Jiuwen's graph subsystem is not
on its main long-term write path. Sage Wiki and Fidelis provide useful graph
and zero-write-LLM retrieval artifacts, but their committed evaluations are
partial, workload-specific, or insufficiently runtime-bound.

Built `scripts/validate_past_bench_source.py` and the registered
`research/source-contracts/past-bench.yaml` contract. The doctor imports no
upstream Python. It binds PAST-Bench commit `f8223517…`, Git tree and archive,
license and runtime files, category/family counts, all declared task and fixture
content, reference manifest ordering, fresh-session and persistence-control
flags, and exact task IDs. The audit found 211 task directories: 204 are in the
runnable `episode_order` rosters and seven older update-family directories are
excluded. Both surfaces are now independently hashed. The receipt status is
`VALIDATED_SOURCE_CONTRACT_NOT_EXECUTION`; upstream dependencies remain
unlocked and its Dockerfiles retain mutable bases and `latest` CLI arguments.

Six source-doctor regressions and 20 focused source/portfolio tests pass. The
complete repository suite passes 401 tests in 174.84 seconds; Ruff, lock, JSON,
diff, experiment, ledger, portfolio, and exact-checkout receipt gates pass. A
final isolated Codex autoreview reported no accepted/actionable findings. No
container, provider request, Slurm job, or H100 allocation was launched from
the dirty tree. The next PAST step is a bounded provider/agent/family contract
with immutable dependencies, checkpoint/resume, and Docker-under-Slurm
attestation after the flat all-task quality matrix—not an immediate full
204-episode run.

## [2026-08-14] infra | Locked the candidate PAST-Bench Hermes+ runtime

Converted the PAST source-only admission into reproducible candidate build
inputs without changing its scientific status. The new runtime contract pins
Python 3.11.15 on the exact Linux/amd64 official-image manifest, `uv 0.11.30`,
an August 14 resolution cutoff, 106 exact packages, and a hash-complete
requirements export. All 31 direct requirements from PAST core, its mock extra,
and Hermes+ resolve compatibly. A `manylinux_2_28` amd64 binary-wheel doctor
resolves all 103 installed distributions without an sdist build.

Added one context compiler/verifier that admits the exact clean PAST checkout,
materializes all 2,159 regular Git files, overlays only the registered lock,
Dockerfile, contracts, and verifier, and binds both source and runtime receipts
before producing a Docker command. A first adversarial review found that the
host path compared against working-tree bytes without independently checking
their registered hashes. The repaired host path now reconstructs the pinned
Git tree, revalidates every runtime-file hash and the source-contract digest,
and pins source/runtime doctor roots `5e686206…` and `119890c1…`. The separate
in-image self-contained mode is explicitly integrity-only. A second isolated
review reported no remaining actionable P0/P1/P2 finding. The image uses the supported
whole-process-local-inside-Docker design: upstream explicitly rejects its own
nested `--runtime container` mode for longitudinal self-evolve episodes.

The exact 36-file pytest roster registered by upstream passes under the lock:
376 passed and two skipped. A broader 62-file diagnostic sweep is not admitted;
one unregistered test references a deleted `self-evolve-tasks/` tree, and broad
single-process collection can collide across vendored agents' top-level Python
packages. Eight new CoTCodec runtime/context regressions pass alongside the
source-doctor tests. No Docker image, SBOM, Slurm job, H100 allocation, provider
call, checkpoint proof, or benchmark result was produced. The next PAST action
is an exact discovery-image build and attestation under Slurm, followed by
episode-boundary checkpoint/resume before the bounded SM01 model cell.

The complete CoTCodec repository suite passed 409 tests in 209.66 seconds after
the trust-boundary repair. After adding the Slurm builder regression, the final
suite passes 410 tests in 215.88 seconds.

## [2026-08-14] infra | Built the contained PAST candidate image under Slurm

Submitted the registered candidate context from the persistent `cotcodec` tmux
session on `fal-h100-01`. Fail-closed jobs 214–216 exposed AppleDouble metadata
in the first macOS tar, an overstrict root-directory check, and the login host's
Python 3.10 boundary; all stopped before Docker build. The repaired launcher
retains an exact archive, uses a host-stdlib receipt precheck, and performs the
full context/tree/runtime verification inside the exact Python 3.11 image.

Job 217 completed in 81 seconds on one H100 and built
`sha256:6184c9561c3381193a85a895f8dfd1cf670d44eb4090874745faad0d1162c1dc`.
The in-image upstream roster reports 378 cases: 376 passed, two skipped, zero
failures/errors. A second container run passed with network none, a read-only
root, UID/GID 65534, all capabilities dropped, and no-new-privileges. The
retained Docker archive is 1,500,785,664 bytes at SHA-256 `5f7f3fcb…`; build
receipt `492d1b90…` and image-inspect receipt `2cee5ecc…` bind the Slurm job,
H100 inventory, source/runtime roots, image ID, build log, and test XML.

The image label remains `publication-ready=false`. It has no scanner-produced
SBOM, checkpoint/resume proof, contained model transport, Qwen result, or
scientific benchmark evidence. Those are the next gates; job 217 is not a
memory-policy result.

## [2026-08-14] infra | Bound the PAST candidate image to a scanner-produced SBOM

Slurm jobs 218–220 failed closed while hardening the scanner lane: job 218
exposed a non-writable non-root tmpfs, job 219 exposed an overescaped loopback
registry regex, and job 220 exposed Syft's worker count exceeding a 512-process
container ceiling. No failed job sealed a receipt. The repaired scanner pins
Syft 1.51.0 by repository digest and image ID, scans the retained Docker archive
without network or Docker socket access, caps Go concurrency at eight, and
keeps the verifier at a separate 512-process ceiling.

Job 221 completed on one Slurm-owned H100. It bound image
`sha256:6184c956…` and Docker archive `5f7f3fcb…` to immutable local repository
digest `127.0.0.1:5000/cotcodec-past@sha256:93cc065f…`. The sealed SPDX document
contains 277 packages, 3,854 files, and 4,693 relationships; its SHA-256 is
`c4a7797712aa5d7b8af0d758b4a4c1cdbd46b38e3e4884461d2efbdd5b46b0c5`.
The job receipt SHA-256 is `96a9d921…` and the batch SHA-256 is `37c6b485…`.

This closes only the discovery SBOM gate. The receipt explicitly records
`scientific_result=false`, `external_attestation=false`, and
`SELF_ATTESTED_DISCOVERY_PAST_BENCH_SBOM_JOB`. Atomic episode checkpoint/resume,
same-job model transport, and the SM01 persistence-on/off result remain absent.

## [2026-08-14] research | Killed PAST SM01 on restart-equivalence failure

Completed the bounded `SM01_preference_adoption` discovery lane with the pinned
PAST-Bench/Hermes+ runtime and Qwen3.6-35B-A3B. Every model call ran inside
network-disabled Docker under Slurm on `fal-h100-01`; no model ran on the login
node and no `sudo` was used.

CPU Slurm job 244 proved the offline Hermes bootstrap. H100 job 246 stopped
after episode three and wrote an atomic checkpoint; CPU job 248 validated it.
Fresh H100 job 250 resumed without rerunning the first three episodes and
completed all eight persistence-on/off episodes; CPU job 252 sealed receipt
`e23615a0…`. The resumed execution showed a descriptive `+0.60` mean score and
`+1.00` pass-rate delta on the two evaluation episodes, while all three controls
were identical.

The registered validity gate did its job. Independently uninterrupted H100 job
254 diverged within the shared prefix despite greedy decoding, seed 42, eager
execution, fixed topology, and registered CUBLAS settings. Learn B changed from
`1.00/pass` to `0.76/fail`; near evaluation changed from `1.00/pass` to
`0.704/fail`. The job was cancelled immediately at the kill threshold. CPU job
256 sealed report `da6f5966…`: two score mismatches, two pass mismatches, seven
trace mismatches, status `PAST_SM01_RESTART_EQUIVALENCE_FALSIFIED`.

The apparent persistence benefit is therefore not a scientific result and the
four-family PAST screen is blocked. The exact cell will not be rerun or rescued
by weakening its gate. Any later PAST GPU cell must preregister either a dense
runtime that first passes repeated cold-load exactness or a different stochastic
estimand with independent interrupted/uninterrupted replicates and executable
score/action equivalence margins. Full provenance and methodology are recorded
in `research/past-sm01-qwen36-discovery-2026-08-14.md`.

## [2026-08-14] harness | Sealed the additive memory lifecycle reference contract

Implemented `memory-lifecycle-v1` as a task-blind stateful complement to the
frozen request-to-selection protocol. The contract covers ordered
write/update/delete/access/observe operations, query, maintenance, executable
outcome feedback, checkpoint/restore, inspect, purge, and shutdown. Every
operation binds idempotency, pre/post logical and durable roots, transitive
raw-source lineage, residency bytes, and phase-separated costs; unsupported
capabilities fail closed.

The registered reference matrix completed 192 cases: 48 each across
active/archive, update/delete, consolidation, and feedback at K={2,4,8}. Host
manifest `92a062233cc173a16a022e8c2d99edccec8db90272a10b53a40f8fb03a8a0d90`
and contained manifest
`2ac7a67c05f4b88540d86361413201438d996ec174f22c4c98bf0ffd947624ac`
both pass the current loader. The contained run used image
`sha256:359a1766c820f21c020a4130a85bdee5850e2f0410b20dbfdf283e90f310f9a5`
with network disabled, a read-only root, all capabilities dropped,
no-new-privileges, finite CPU/memory/PID limits, and no `sudo`.

Cross-runtime receipt
`906c900abaa5a5814cacc104ed582c90f24784f98ac3325ed6490e3837799d61`
recomputes to PASS: eight semantic artifacts are byte-identical between Darwin
arm64 CPython 3.13.14 and Linux aarch64 CPython 3.12.11, and experiment/code,
case/trace roots, and aggregate gates match. Focused lifecycle and comparison
tests pass and Ruff is clean.

This is reference transport/mechanism evidence only. It reproduces no native
memory system and demonstrates no quality advantage. The working tree/image are
dirty-development evidence and no external Slurm/trust-root attestation exists,
so `scientific_result` and `publication_ready` remain false. The next CPU-only
admission work is Total Recall for promotion/demotion, Graphiti or GAAMA for
graph state, Hippo for deterministic decay/consolidation, and ReasoningBank for
procedural state. No system enters an H100 actor cell before its applicable
capability, ordering, lineage, branch-isolation, fresh-process restart,
purge/residue, and phase-cost gates pass.

## [2026-08-14] research | Tested the complete Hermes memory-provider roster

Pinned Hermes Agent at commit `a90d5369...` and tested all nine providers named
by the live documentation inside network-disabled, read-only Docker without
credentials, `sudo`, or model execution. ByteRover passed 1/1, isolated
Hindsight 112/112, Holographic 51/51, Mem0 57/57, OpenViking 101/101, RetainDB
39/39, Supermemory 26/26, common discovery 28/28, and external Memori 34/34 plus
its real Hermes directory install/discovery path. Memori exposed six tool
schemas, including compaction, rather than the five described in the provider
page.

The aggregate result is intentionally `FAIL`. Honcho passed 349 tests with 16
skips but deterministically failed cache invalidation when `pinPeerName`
changed. Hindsight's isolated upstream tests passed, but a strict probe requested
a 0.05-second drain budget and measured 0.256786884 seconds because one status
poll is not bounded by the outer deadline. Report
`013f10e0d865415a1022e0d845a558264a1a1377a2e4b3eef6711dfb625def32`
and manifest
`74eba6e2c1b1148a21f4b8709459dd6234e696fdc3a50d683a30281591d9fd0a`
remain development evidence with `scientific_result=false` and
`publication_ready=false`.

OpenViking ran only its server-absent/fail-open paths, cloud providers made no
service calls, and local adapter/unit/storage tests are not memory-quality or
native-lifecycle evidence. The registered conformance matrix is therefore an
admission layer: qualifying providers must next pass `memory-lifecycle-v1` on
CPU before any matched Docker-under-Slurm H100 actor comparison.
## 2026-08-14 — Total Recall native lifecycle restart falsifier

- Registered `stage3-total-recall-lifecycle-doctor` as a contained CPU negative
  experiment; no H100 or model calls were authorized.
- Bound clean upstream commit `a2630f671be9b12df8b8ac78df9d26f7053d2fa9`,
  tree `6d62153e...`, git archive `19c7e803...`, and MIT license file
  `d97ac8af...` into a digest-pinned Linux/arm64 Docker build.
- Two fresh `--network none`, read-only, non-root runs reproduced the same
  native invariant failure: automatic hot-to-warm compaction left 1 content
  row and 0 vector rows; the next `SqliteStore` startup deleted the row during
  orphan cleanup. A `MoveAndReEmbed` positive-control row remained 1+1 before
  and after the same restart.
- First manifest file SHA: `63b33df0cff6e553e4c482c87338a74eeef25d51b3bbea22ad3d409f3c48c307`;
  replication manifest file SHA: `329d06dbe4fd6012d7126b64b6fdfa46a60dc6bf99eea333060bcbadd9f87ceb`.
- Reclassified the current Total Recall pin as a locally reproduced negative
  restart/atomicity control and blocked H100 admission. A newer pin or explicit
  atomic patch arm must pass two restarts, crash injection, fixed-K capacity,
  and configured-threshold tests before reconsideration.

Follow-up provenance hardening retained the generated NuGet graph as lock
`615a3f37...` and rebuilt with `--locked-mode`. The canonical v2 image is
`sha256:5d64ffaf...`; v2 manifest file SHAs are `d9257e34...` and
`9418a21e...`. Both v2 runs used the same image and produced the same
deterministic status/row/gate projection. Earlier unlocked receipts remain
development history and are not the canonical evidence cited by the ledger.

Final v3 receipt hardening also binds the runner, experiment validator, and
experiment YAML. The image remains `sha256:5d64ffaf...`; canonical manifest
file SHAs are now `1db53b5d...` and `5ea10267...`. The v3 input receipts and
deterministic native projections are identical, and the ledger points only at
v3. V1/v2 remain superseded development history.

## 2026-08-14 — Memory evidence and scheduler admission hardening

- Sealed the two Total Recall v3 runs into self-contained bundle
  `research/evidence/memory/total-recall-restart-v3.json` (`b1bc7c00...`).
  Validation now recomputes the manifest self-root, artifact roster, child
  receipt equality, exact negative row counts and gates, and requires two
  distinct native execution identities. Copying one run no longer qualifies
  as replication.
- Sealed Hermes' exact nine-provider CPU conformance result into
  `research/evidence/memory/hermes-provider-conformance-v2.json`
  (`b21871b5...`). Validation requires every registered result group and log,
  the complete PASS/FAIL map, the Honcho failure, the Hindsight timeout
  failure, the registered experiment digest, and both pinned source revisions.
  It remains a provider-adapter conformance FAIL, not native-provider quality.
- Split reproducibility accounting into scientific, conformance, and negative
  evidence. Current totals are 0 scientific reproductions, 1 conformance
  reproduction, and 1 reproduced negative across 189 sources and 146 pinned
  repositories.
- Added a killed-revision registry and bound it to the actual H100 submitters.
  Every memory job now carries the validated portfolio and matrix hashes plus
  an explicit internal/external source roster. Total Recall `a2630f6...` is
  rejected before Slurm submission; old loose memory manifests must be
  regenerated.
- Added a machine-readable PAST SM01 negative decision receipt preserving its
  source revision, report/resume digests, jobs, and exact mismatch counts.
- Selected `neo4j-preference-supersession-lifecycle-v1` as the next bounded CPU
  cell: pre-extracted tuples, no LLM/embedding calls, native
  `SUPERSEDED_BY`/`valid_until`, current and historical views, restart,
  tenancy, lineage, and purge. Passing would establish conformance only, not
  graph efficacy or bidirectional paging.

## 2026-08-14 — Neo4j preference lifecycle conformance

- Built the pinned Neo4j Agent Memory client at `231d60e...` and Neo4j server
  as separate Docker containers on a private internal network. The client was
  read-only, non-root, capability-free, and network-isolated from the host;
  the server ran as UID/GID 7474 after a one-shot volume initializer. No
  `sudo`, model, embedding, HTTP, or external network call was used.
- Two clean-volume local arm64 repetitions passed native preference
  supersession, `valid_until`, current and historical `as_of` views,
  idempotent retry, retained-volume restart, separate-user isolation, event
  lineage, and post-purge restart with zero nodes and edges. Both repetitions
  reported zero model calls.
- Sealed the exact experiment, report, manifest, runtime identities, semantic
  projection, and distinct state roots into
  `research/evidence/memory/neo4j-preference-lifecycle-local-arm64-v1.json`
  (`98a21ee7...`). The ledger recomputes the embedded files before granting
  `local-conformance-reproduced`.
- This is not graph-efficacy or memory-quality evidence. Exact amd64
  Docker-under-Slurm confirmation and an identical-pre-extracted-tuple flat
  parity shadow remain mandatory before any H100 actor cell.

## 2026-08-14 — Hippo retention and cross-tenant lifecycle falsifier

- Pinned Hippo Memory v1.30.0 at commit `4aeb04c...`, tree `88d0613...`,
  deterministic Git-archive SHA `d966a02b...`, MIT license, and lock SHA
  `8faa74fa...`.
- Built a zero-model, zero-GPU, network-disabled, read-only, non-root Docker
  doctor. Two independent named volumes each ran prepare, fresh-process restart,
  and purge; both produced stable-projection SHA `2be93ab...`.
- Reproduced that the hard-coded working-memory cap evicts by deletion and flush
  does not archive, so this is not an active/inactive paging system.
- Reproduced sleep merging tenant-A and tenant-B memories into a semantic record
  owned and retrievable by the default tenant without complete source lineage.
- Reproduced logical deletion to zero rows while all five canaries remained as
  plaintext in `hippo.db`.
- Sealed the full two-run evidence at
  `research/evidence/memory/hippo-retention-cross-tenant-v1.json`, SHA
  `50449ae3...`, terminal status
  `BLOCKED_CROSS_TENANT_CONSOLIDATION_AND_PURGE_RESIDUE_REPRODUCED`.
- Removed this revision from the H100 execution order. It remains only a fixed
  observational-retention/status negative control; a newer pin or explicit
  patch must pass tenant, lineage, physical-purge, configurable-K, and true
  bidirectional-movement gates.

## 2026-08-14 — Magic Context portable-lifecycle falsifier

- Pinned Magic Context at commit `13e1d4c...`, tree `f420beb...`, Git-archive
  SHA `8eb4b815...`, Bun lock `8e8bc070...`, and MIT license.
- Built a zero-model, zero-GPU, network-disabled, read-only, non-root Docker
  doctor. Two independent states reproduced deterministic chronological prompt
  paging and the same supported-projection root across a fresh process.
- Reproduced that expansion depends on host raw rows and is a projection rather
  than exact raw-message recovery; reasoning and unsupported metadata are lost.
- Reproduced cross-harness aliasing for the same session identifier and plaintext
  residue in the plugin and host SQLite stores after logical clearing.
- Sealed the full two-run evidence at
  `research/evidence/memory/magic-context-paging-v1.json`, SHA `638a5c56...`,
  with terminal status
  `BLOCKED_PORTABLE_LIFECYCLE_AND_SECURE_PURGE_REPRODUCED`.
- Removed this revision from the active/inactive H100 execution order. It remains
  a host-backed prompt-rendering boundary, not semantic memory, a reversible raw
  archive, or bidirectional item paging.

## 2026-08-14 — Post-cutoff memory frontier delta

- Expanded the primary-source ledger from 189 to 200 sources and from 146 to
  152 pinned repositories. Reproducibility remains 0 scientific results, 3
  conformance results, and 3 bounded negative findings.
- Added Consolidator and MARCH as paper-only architecture priors, and Spatial
  Memory Agent, SkillShapley, and SkillEvo as procedural reliability, credit,
  and governance controls. None has an immutable official implementation at the
  cutoff.
- Added Palimpsest as a bitemporal stale-state candidate and Mnemosyne OSS as a
  one-way consolidation plus standalone-Hermes candidate. Both require CPU
  lifecycle doctors before any model-bearing work.
- Added standalone HyperspaceDB, DSH Gate, Mneme, and Unified Agent Memory as
  provider or boundary controls. They do not expand the eight-provider official
  Hermes bundled roster.
- The delta found no credible open implementation of true bidirectional
  hot/archive item paging. This preserves the narrow CMHT claim and keeps the
  next mechanism execution on the GAAMA graph-vs-flat CPU falsifier.

## 2026-08-14 — GAAMA matched graph-component doctor

- Pinned GAAMA at commit `2d992f7...`, tree `0227970...`, Git-archive SHA
  `d9aec03f...`, MIT license, upstream PPR/retriever source hashes, and the
  released LoCoMo-10 artifact hash.
- Built a zero-model, zero-embedding, zero-GPU component doctor and ran it twice
  in fresh network-disabled, read-only, non-root Docker containers. Both
  reports were byte-identical.
- With one identical five-node candidate pool per task, true graph retrieved
  24/24 targets; flat and degree/type-shuffled graph retrieved 0/24. PPR weight
  zero exactly matched flat retrieval, and no cross-task edge existed.
- Reproduced that the upstream hub-dampening scalar has no effect after each
  row is normalized. This is a useful component-level negative, not a GAAMA
  benchmark result.
- Sealed the complete run at
  `research/evidence/memory/gaama-graph-component-v1.json`, SHA `cf903e2b...`.
  Natural held-out same-node retrieval, generated-node freezing, actor quality,
  GEL support/query separation, and H100 execution remain blocked/unrun.

## 2026-08-14 — Hermes Holographic native lifecycle falsifier

- Pinned the bundled Holographic provider from Hermes commit `a90d536...`, tree
  `963eb13...`, Git-archive SHA `2a2934d3...`, and MIT license.
- Ran prepare, fresh-container restart, and purge phases twice in independent
  Docker volumes with no network, a read-only root, non-root execution, and no
  GPU. Both runs produced stable projection `b8c3f640...`.
- Reproduced native SQLite/FTS restart, duplicate-add idempotence, and persistent
  update/feedback. Also reproduced that logical sessions share one provider DB
  and that no native per-session purge operation exists.
- The retained Linux container had zero plaintext hits after individual remove;
  a separate macOS diagnostic retained plaintext, so secure erasure remains
  runtime-dependent and unproven. HRR quality was not tested in this cell.
- Sealed the two-run negative at
  `research/evidence/memory/hermes-holographic-lifecycle-v1.json`, SHA
  `a532c646...`, and added it to the killed-revision admission gate. This pin is
  not eligible for portable H100 work without explicit session ownership and
  scoped purge.
- The source ledger now contains 201 sources and 153 pinned repositories, with
  0 scientific reproductions, 3 conformance reproductions, and 4 bounded
  negative findings.

## 2026-08-14 — Hermes ByteRover native offline falsifier

- Corrected ByteRover v3.16.1 provenance by binding the annotated tag object
  `68ef7f9...` separately from peeled commit `1f4609c...`, tree `fdaf08c...`,
  Elastic-2.0 license, npm tarball SHA `14039b1f...`, and npm integrity.
- Ran prepare and fresh-process restart twice in independent non-root,
  network-disabled, read-only Docker volumes. Native `brv search`, Hermes
  `brv query`, and Hermes `brv curate` all hit bounded timeouts, and every
  daemon log contained the same fatal network-startup error.
- Confirmed from the exact Hermes adapter that its directory is profile-global,
  logical session IDs do not namespace storage, and no native session purge is
  exposed. No credentials, model, embeddings, GPU, or upstream installer ran.
- Sealed the result at
  `research/evidence/memory/hermes-byterover-offline-v1.json`, SHA
  `4b51e2f1...`, and added the pin to killed-revision and provider-follow-up
  gates. The result is a provider-integration negative, not memory quality.
- The source ledger now contains 202 sources and 155 pinned repositories, with
  0 scientific reproductions, 3 conformance reproductions, and 5 bounded
  negative findings. OpenViking is the next native Hermes provider doctor.

## 2026-08-14 — Hermes OpenViking native lifecycle and purge falsifier

- Pinned OpenViking commit `eeff5a4...`, tree `ba1585c...`, archive SHA
  `4b49f3cc...`, AGPL-3.0 license, and the exact Hermes provider at commit
  `a90d536...`; built three immutable local arm64 images for the service,
  deterministic local model stub, and provider adapter.
- Ran two independent contained CPU doctors on Docker-internal networks with
  read-only roots, dropped capabilities, `no-new-privileges`, no external API,
  and zero GPUs. Both passed direct write/search/read/forget, two fresh service
  restarts, logical two-tenant isolation, and restart-stable logical deletion.
- Both runs then found both deleted random plaintext canaries in retained
  LevelDB files. Each report records file, offset, base64 byte window, and
  window hash; the evidence validator decodes the window and requires the
  deleted canary to be present.
- Sealed the two-run negative at
  `research/evidence/memory/hermes-openviking-lifecycle-v3.json`, SHA
  `a946df0c...`, and added `eeff5a4` to provider-follow-up, killed-revision, and
  H100-admission gates. This is lifecycle evidence, not retrieval quality.
- The ledger remains at 202 sources and now has 156 immutable repository
  records across 145 sources, 0 scientific reproductions, 3 conformance
  reproductions, and 6 bounded negative findings. Mem0, Hindsight, and
  Supermemory remain the next native bundled-provider doctors.

## 2026-08-14 — Hermes Hindsight native lifecycle and purge falsifier

- Pinned Hindsight `5781d28...`, tree `a33e9ea...`, archive SHA `993a015...`,
  MIT license, and the exact bundled Hermes provider at `a90d536...`. The
  executable Hermes dependency pin is `hindsight-client==0.6.1`; the native
  service is Hindsight 0.9.0.
- Ran two independent contained CPU doctors on Docker-internal networks with
  read-only roots, dropped capabilities, `no-new-privileges`, no external API,
  no LLM calls, and zero GPUs. Both passed all 12 registered operations:
  retain, auto-prefetch, session-end auto-retain, logical two-tenant isolation,
  two full PostgreSQL/backend restarts, administrative bank deletion, and
  restart-stable logical absence.
- Hermes exposes retain, recall, and reflect but no Hindsight purge tool. Both
  runs found each deleted random plaintext canary in four PostgreSQL heap files
  and one WAL segment after the final restart. The reports bind file paths,
  offsets, base64 proof windows, and hashes.
- Sealed the two-run negative at
  `research/evidence/memory/hermes-hindsight-lifecycle-v1.json`, SHA
  `44c45b6d...`, and registered `5781d28` as H100-ineligible until native
  physical purge or cryptographic erasure passes. This is lifecycle evidence,
  not memory-quality, graph, reflection, or mental-model evidence.

## 2026-08-14 — GAAMA natural graph-vs-flat retrieval component

- Pinned GAAMA at commit `2d992f7...`, tree `0227970...`, source archive
  `d9aec03f...`, and LoCoMo-10 artifact `79fa87e...` under CC-BY-NC-4.0.
- Used three development conversations to select PPR weight 0.5 and sealed
  seven disjoint test conversations with 1,146 category 1-4 questions. Every
  arm shared the same raw dialogue-turn candidates and BM25 indexed fields.
- Structural session/next-turn PPR improved conversation-equal evidence
  recall-all@10 by 2.04 points over flat BM25 (95% bootstrap CI [1.25, 2.96])
  and 2.17 points over three typed per-node directed-degree-preserving shuffled
  graphs (95% CI [1.30, 3.20]); both one-sided conversation sign tests were
  `p=0.0078`.
- Two fresh non-root, network-disabled, read-only Docker executions were
  byte-identical and used zero model, embedding, network, or GPU calls. The
  evidence validator embeds the exact dataset and reruns all rankings under
  hash-bound source code. The final harsh review reported no P0/P1/P2 defects.
- Sealed the bounded result at
  `research/evidence/memory/gaama-natural-graph-v5.json`, SHA `011a2191...`.
  This is retrieval-component evidence only. Generated semantic nodes, GEL,
  answer quality, agent success, amd64 Slurm confirmation, and H100 comparison
  remain unrun or blocked.

## 2026-08-14 — Mem0 native lifecycle adapter crash-recovery falsifier

- Added an additive `memory-lifecycle-v1` sidecar for pinned Mem0 2.0.18 at
  `71f2ebf...`. It exposes apply, query, checkpoint, restore, inspect, and purge
  while explicitly refusing maintenance, feedback, and active-tier promotion.
- Ran two fresh non-root, network-disabled, read-only arm64 Docker repetitions
  with dropped capabilities, no-new-privileges, finite CPU/memory/PID limits,
  deterministic loopback embeddings, and no GPU or API calls.
- Both repetitions passed every registered non-crash native CRUD,
  inactive-archive, restart-verification, branch-isolation, lineage,
  idempotency, divergent-retry, and ordinary-scope purge gate and produced
  stable projection `33cb446e...`.
- A forced crash after native mutation but before lifecycle-journal commit leaves
  an ambiguous pending operation. The adapter fails closed on restart but cannot
  continue, and its plaintext canary remains in `history.db` and Qdrant
  `storage.sqlite`. H100 admission remains blocked until exact recovery and
  residue clearance are implemented and reproduced twice.
- Sealed the result at
  `research/evidence/memory/mem0-lifecycle-adapter-v5.json`, SHA
  `6733a415...`. This is a CoTCodec adapter recovery negative, not an upstream
  Mem0 database defect, extraction result, or memory-quality benchmark. The
  ledger now has 204 sources, 159 pinned repository records across 147 sources,
  three conformance reproductions, and eight bounded negative findings.

## 2026-08-14 — Mem0 lifecycle evidence v6 closes review gaps

- The independent closeout review found that v5 retained only crash-residue path
  names after deleting temporary native state and that an in-process sidecar
  could replay a stale pre-purge idempotency receipt.
- The adapter now clears all scope receipts during purge. The doctor captures a
  bounded byte window, full-file digest, offset, and window digest for each
  plaintext hit before temporary state is removed; the sealer independently
  verifies both embedded canaries. Focused sidecar tests cover stale replay.
- Rebuilt exact image `sha256:cf96e782...` and ran two fresh contained CPU
  repetitions. Both retained the honest `BLOCKED_ADAPTER_CRASH_RECOVERY` result
  and matched stable projection `1da1b15e...`; no GPU, API, Slurm, or sudo was
  used.
- Superseding evidence is
  `research/evidence/memory/mem0-lifecycle-adapter-v6.json`, SHA
  `99edcd00...`. V5 is historical/superseded. The scientific conclusion and
  H100 block are unchanged, but the two plaintext-residue claims are now backed
  by independently checked proof windows.

## 2026-08-15 — Supermemory v0.0.3 acknowledged-write crash negative

- Audited the pinned Supermemory documentation repository at `82dae50...` and
  release source at `39ef7e1...`. Neither tree contains the local-server
  implementation, so this is explicitly a binary-only audit. The exact linux
  arm64 v0.0.3 binary is pinned at SHA `167f595a...`.
- Ran two fresh, non-root, network-disabled, read-only Docker repetitions with
  pinned local BGE model files and no GPU, API, Slurm, or sudo work. Direct
  create/search, versioned update/history, and a separate graceful-stop recovery
  pair worked.
- After a deliberate `SIGKILL`, both acknowledged tenants and the acknowledged
  update history were absent on fresh-container restart in both repetitions.
  Forget is soft deletion and there is no native tenant-scoped physical-purge
  contract.
- Sealed evidence at
  `research/evidence/memory/supermemory-local-binary-v1.json`, SHA
  `54579188...`, with status
  `BLOCKED_ACKNOWLEDGED_WRITES_LOST_ON_SIGKILL`. The exact release is barred
  from H100 work. Next CPU admission target is Graphiti, then ReasoningBank.

## 2026-08-15 — Graphiti ARM64 native-runtime admission negative

- Added a task-blind Graphiti 0.29.3 explicit-triplet memory-lifecycle-v1
  adapter at revision `401c59a...`. Host-development tests cover native CRUD,
  query, fresh-process restart, physical branch isolation, lineage,
  idempotency, adapter-scoped purge, and capability refusal.
- Built immutable ARM64 image `sha256:de790ca...` from source archive
  `9cfbc01e...` and ran two fresh, non-root, network-disabled, read-only Docker
  admissions with no GPU, API, Slurm, or sudo work.
- Both runs failed before their first lifecycle write because FalkorDBLite
  0.10.0 packaged x86-64 `falkordb.so` beside an AArch64 `redis-server`.
  The sealed probe binds the ELF identities, exact image/source/experiment,
  complete Docker argv, and both native server-start failures.
- Evidence is
  `research/evidence/memory/graphiti-falkordblite-arm64-v2.json`, SHA
  `6664df62...`, with status
  `BLOCKED_FALKORDBLITE_ARM64_MODULE_ARCHITECTURE_MISMATCH`. No contained
  lifecycle operation completed, so this is a runtime-admission negative—not
  Graphiti quality evidence. This revision/runtime is barred from H100 work;
  ReasoningBank is the next CPU admission target.
- Independent review found that v1 distinguished its repetitions only through
  run-indexed JSON. V2 reran both containers and now binds distinct Docker
  container IDs, creation/start/finish times, exit states, image IDs, mounts,
  and host security/resource contracts. Admission also blocks the same
  repository revision under both `graphiti` source aliases.

## 2026-08-15 — ReasoningBank source admission blocked before runtime

- Pinned Google Research ReasoningBank at `ed806117...`, tree `7cc5e6e...`,
  deterministic archive SHA `d85d169c...`, Apache-2.0, with its exact lock and
  eight critical driver files.
- Added a no-import source doctor and registered experiment contract. The audit
  found import-time cloud clients, unrevisioned embedding models, evaluation-time
  mutation of both query caches and procedural banks, shared threaded SWE-Bench
  mutation, trusted pickle input, swallowed extraction errors, and unseeded
  procedural induction.
- The WebArena scaling release passes only the final trial directory to
  induction, rereads it for every sample, and maps reward zero to success.
- Status is `BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL`; this is source
  admission evidence only. No API, model, GPU, Slurm, or sudo work ran. A frozen
  train-only bank/index and disjoint workflow-family patch arm must pass a
  contained CPU doctor before any H100 cell.

## 2026-08-15 — ReasoningBank frozen procedural-bank CPU contract passed

- Added a deep, framework-owned frozen procedural-bank module rather than
  routing cross-task procedures through the current-prefix `MemorySystem`
  contract. It binds exact task-to-family train/dev/test rosters, TRAIN-only
  item lineage, pinned document vectors, query-only embedding, ranking,
  budgeting, and content-addressed receipts.
- Built ARM64 image `sha256:f6087715...` with the pinned Python base and
  SHA-pinned Torch 2.11 CPU wheel. Two fresh named containers ran the real
  pinned BGE-small-en-v1.5 snapshot with network disabled, read-only root,
  dropped capabilities, no-new-privileges, no devices, and read-only model and
  receipt mounts.
- Both runs passed 6/6 fixture retrievals, exact repeated freeze/query,
  immutability, TRAIN-task refusal, and task/family mismatch refusal. Their four
  core artifacts are byte-identical.
- Sealed contract evidence is
  `research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json`, SHA
  `179f78a6...`. This is synthetic conformance only: no real induction, actor,
  quality comparison, H100, Slurm, or publication claim. The upstream release
  driver remains blocked.

## 2026-08-15 — ReasoningBank frozen-bank evidence hardened and rerun

- Independent review found that the first host wrapper admitted any
  label-compatible image digest and trusted container-authored retrieval
  summaries without parsing the purported JSONL. The file also contained
  pretty-printed multi-line objects rather than one JSON object per line.
- Pinned the admission wrapper to exact image `sha256:fdb8eec6...`, changed the
  retrieval artifact to strict JSONL, and added host-side recomputation of the
  six-query roster, exact oracle, bank/item lineage, retrieval digests, model
  receipt, top-one hits, and injection budgets.
- Rebuilt from the bounded source context and ran two new fresh contained CPU
  repetitions (`v5` and `v6`). Their bank, manifest, report, and retrieval
  artifacts are byte-identical; progress-only stderr remains intentionally
  outside that equality claim.
- Updated evidence
  `research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json` now hashes to
  `0320948c...`. Status and scope are unchanged: synthetic CPU contract only,
  `scientific_result=false`, `publication_ready=false`, no H100/Slurm/API
  admission, and no ReasoningBank quality claim.

## 2026-08-15 — ReasoningBank held-out and provenance semantics corrected

- A second independent review correctly rejected the initial use of
  `database-train` / `database-dev` / `database-test`-style family aliases.
  Replaced them with genuinely distinct credential, certificate, versioned
  document/object recovery, rental, and registration workflow families and
  made split-suffixed family IDs invalid at the schema boundary.
- Replaced placeholder hashes with retained hand-authored fixture trajectory,
  correctness, and generator artifacts. Reports now explicitly state that
  these are fixture-only and that no real ReasoningBank trajectory is present.
- Retained the five byte-identical core artifacts, pinned model receipt, both
  execution receipts, and both Docker inspect records under
  `research/evidence/memory/reasoningbank-frozen-bank-cpu-v1-artifacts/`.
  The experiment validator now reopens and recomputes that evidence chain.
- Rebuilt exact ARM64 image `sha256:2c85e385...` and completed fresh contained
  repetitions `v7` and `v8`, each 6/6 on the cross-family synthetic retrieval
  fixture. Evidence JSON now hashes to `9f293fc5...`; scope remains synthetic
  CPU conformance only with no scientific, publication, H100, Slurm, API, or
  upstream-quality claim.

## 2026-08-15 — ReasoningBank indexing boundary corrected

- Independent review found that the frozen bank embedded hidden
  `source_query` lineage instead of the procedure text an actor would receive.
  The bank now embeds only actor-visible `procedural_text`; a regression test
  proves that changing `source_query` leaves document vectors unchanged.
- Rebuilt exact ARM64 image `sha256:d3f7858e...` and completed fresh contained
  repetitions `v9` and `v10`. Both passed 6/6 cross-family retrievals and
  produced the same five core artifact hashes.
- Evidence
  `research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json` now hashes to
  `c6f6d628...`. This remains synthetic CPU conformance evidence only:
  `scientific_result=false`, `publication_ready=false`, with H100, Slurm, API,
  real trajectory induction, and procedural-memory efficacy still blocked.

## 2026-08-15 — Strict ReasoningBank induction intake implemented

- Added an additive CPU-only compiler for canonical TRAIN trajectory JSONL and
  deterministic procedure-generation receipts. It requires an externally
  pinned split-manifest digest and exact task coverage, binds correctness to the
  trajectory, retains both identical generation responses, and rejects mixed
  dataset, evaluator, prompt, model, code, or decoding contracts.
- Added a no-overwrite CLI and 16 focused tests covering non-TRAIN records,
  roster omission, split drift, duplicate/noncanonical JSON, symlinks,
  stochastic or changed replays, and mixed provenance contracts. Focused Ruff
  and tests pass; the second independent review is clean after closing its
  caller-controlled-roster finding.
- No real trajectory corpus, registered split, model generation, induced bank,
  actor result, Slurm job, H100 work, or scientific result exists yet. The next
  gate is to pin the real input roster and run a contained deterministic
  generator twice before freezing the real bank.

## 2026-08-15 — Memory frontier delta and H100 execution boundary

- Ran the strict same-day arXiv query over cs.AI, cs.CL, cs.IR, cs.MA, and
  cs.LG; no 2026-08-15 submission was visible at the cutoff. Used `lsearch` and
  GitHub discovery only to generate candidates, then audited official immutable
  repository pins and committed artifacts without executing external code.
- Added three narrowly scoped sources. JordanMcCann agentmemory V4 retains its
  internally consistent 481/500 committed artifact but is classified as
  answer-context assembly and an overfit warning because it uses the
  answer-session-only LongMemEval oracle artifact and forty-six same-set
  optimization cycles. Agentra AgenticMemory is a locked event-sourced graph
  candidate, but `flush` without `fsync`, silent incomplete-tail acceptance,
  and log-versus-SQLite erasure semantics require a contained CPU lifecycle
  doctor. Experience OS Lab computes lifecycle labels without durable movement
  and has only a four-train/ten-test deterministic flight toy.
- Wrote `research/scans/2026-08-15.md` with the executable active/inactive
  definition, source receipts, falsifiers, and the H100 promotion ladder. The
  validated ledger now contains 212 sources, 164 pinned repositories, four
  pinned artifacts, and 21 labeled benchmark claims; focused source/landscape
  tests and Ruff pass.
- Kept actual model inference on H100. The GAAMA Qwen3.5-4B true-graph-versus-
  flat Docker/Slurm cell remains compiled and hash-bound, but
  `207.241.191.91:22` returned `Network is unreachable` before SSH. No CPU
  inference substitute, bare-login workload, `sudo`, external code execution,
  or H100 job was run. Reconnect, read-only doctors, digest verification,
  dry-run, `--test-only`, and scheduler submission remain the next operation.
- Added two late same-day controls after immutable-source review. DSH Memory
  System is a hot/cold prompt-projection and push-versus-pull injection control,
  not durable active/inactive memory. Longform Memory is a fixed long-context
  allocation/compaction control with no storage lifecycle. The source ledger is
  now 214 sources and 166 pinned repositories; neither system receives H100
  time before its deterministic CPU admission contract passes.

## 2026-08-15 — Late memory-source wave and H100 boundary retained

- Audited five additional same-day repositories from clean temporary clones
  without executing their code. E²-Mem is an episode/child-event hierarchy
  control whose public release has strong scripts but null formal artifact URLs
  and mutable provider identities. Canon is human-approved decision governance.
  Vector897 Palimpsest performs one-way `archived=true` exclusion with no cold
  retrieval or promotion path. The unlicensed lgoyal6 memharness contributes a
  small matched cost-accounting pattern, not a reusable ranking. EvolveBank's
  documented raw gain collapses to an exact 0.768-versus-0.768 null after four
  control-only network failures are removed, but the task logs and bank are not
  committed.
- Expanded the source ledger to 219 sources, 171 pinned repository records
  across 159 sources, six pinned artifacts, and twenty-five labeled claims.
  Scientific evidence remains zero local reproductions, three conformance
  reproductions, and eleven bounded negative reproductions.
- Preserved the compute rule: source and lifecycle admission may use CPU, but
  model inference remains contained Docker-under-Slurm on H100. The dedicated
  host was still unreachable before SSH; no local-model substitution, bare
  login-node workload, `sudo`, or external source execution occurred.

## 2026-08-15 — ASTRA active/inactive pager candidate admitted

- Audited ASTRA at commit `644f9d4e65f4e725996025834c91531592ab6166`
  and tree `43592dc01aa730efb263d24255b094e1f4dc24f3`. Its bounded
  `MemoryWindow` admits passive, tool, link, pin, handoff, and event memories,
  evicts by relevance/age under count and character budgets, retains evicted
  records in durable storage, and can re-admit retrieved records. This is the
  first credible active/inactive pager candidate in the ledger, not proof that
  native bidirectional paging works.
- Ran the exact pure-component suite twice in fresh non-root, network-disabled,
  read-only Docker execution with all capabilities dropped and no GPU, API,
  model inference, or `sudo`. Both repetitions passed the exact 26-test roster;
  their stable semantic projection hashes to `667d0a146c60...`. The sealed
  conformance evidence at
  `research/evidence/memory/astra-working-set-core-v1.json` hashes to
  `3a310140916b...` and remains `scientific_result=false` and
  `publication_ready=false`.
- Kept ASTRA out of the H100 actor matrix. Native Cockroach eviction, durable
  archive retention, re-admission, fresh-process restart, branch/session
  isolation, and purge must pass twice before a matched frozen actor cell may
  consume at most two H100-hours.
- Updated the validated ledger to 220 sources, 172 pinned repository records
  across 160 sources, six pinned artifacts, twenty-five labeled claims, zero
  scientific reproductions, four conformance reproductions, and eleven bounded
  negative reproductions.
- Retried `kevin@207.241.191.91` in batch mode; port 22 timed out before login.
  Paused the stale v5 GAAMA heartbeat and prohibited submission of that source.
  The next executable artifact is a freshly validated v6 Docker/Slurm source
  capsule; no CPU inference or bare-host substitute is allowed.

## 2026-08-15 — Registered the native ASTRA H100 lifecycle falsifier

- Added `stage3-astra-native-lifecycle-doctor.yaml`, a fail-closed source and
  runtime validator, a non-root ASTRA doctor image, and a dedicated one-H100
  Slurm wrapper. The wrapper validates and extracts an exact normalized source
  archive inside the job, uses no `sudo`, and checkpoints after each clean
  repetition.
- The doctor uses upstream `MemoryStore`, `MemoryWindow`, migrations, and
  `FakeEmbedder` against CockroachDB v26.2.3. It fills K=12, evicts and
  re-admits durable records, saves two users' session state, creates an
  identical-write retry pair, confirms all-pinned overflow, SIGKILLs the
  database after acknowledged writes, restores through a fresh database
  container, and inspects soft-delete row and session-reference residue.
- Preregistered the negative terminal status
  `BLOCKED_NATIVE_PURGE_IDEMPOTENCY_AND_PINNED_CAP`. Passing restart and
  ordinary pager semantics cannot admit the current revision to an actor wave
  while duplicate-write, physical-purge, and pinned hard-cap semantics fail.
- Local work was limited to Python/shell/unit checks and contained TypeScript
  type-checking; the native lifecycle workload was not run locally. The H100
  endpoint still timed out before SSH, so no Slurm job, model call, or CPU
  inference substitute was launched. The stale v6 heartbeat remains paused
  until a new exact source handoff is sealed.

## 2026-08-15 — Fourth memory-source wave and H100 priority retained

- Admitted four exact open-code controls after primary-repository inspection:
  MatrixOrigin Memoria `efd3d651...` for transactional branch/snapshot/merge/
  rollback lifecycle; Agent Recall `dcf21b5...` for scoped bitemporal briefings;
  MemoryGraph `4f834c0...` for typed graph/CLI lifecycle; and TokenMizer v0.3.1
  `131e3d1...` for session-graph checkpoint and context-compaction behavior.
- Kept every evidence label narrow. Memoria, Agent Recall, and MemoryGraph are
  `mechanism-only`. TokenMizer is `paper-reported`, because the result JSON
  named by the paper is absent from both the evaluated tag and current tree.
  None demonstrates active/inactive paging or a graph-quality effect.
- Expanded the validated ledger to 224 sources and 176 pinned repository
  records across 164 sources. The portfolio now contains 87 candidates under
  the unchanged 108-H100-hour ceiling; matrix SHA-256 is
  `9f9a77f3b1ff39fdbdbbf4355ebbafc594014f10de503fc912ab1b993f6b72d3`.
- Retried `kevin@207.241.191.91` with a twelve-second batch-mode timeout; port
  22 still timed out before authentication. No job, model, CPU substitute,
  bare login-node work, or `sudo` ran. The exact frozen ASTRA v7 one-H100
  Docker-under-Slurm lifecycle doctor remains the first submission when the
  endpoint returns; the active retry automation is bound to that immutable
  handoff and will not submit the stale GAAMA cell.

## 2026-08-15 — Fifth memory-source wave; H100 boundary preserved

- Admitted four exact open-code controls after official-repository inspection:
  Active Graph `8aedb186...` for event-sourced replay and SQLite fork/diff;
  MemForge `16e2f15...` for hot-to-warm consolidation plus explicit manual
  cold restore; agenticow `dd4f437b...` for copy-on-write vector branches; and
  Hermes Observational Memory `90d83c1f...` with core v0.10.0 `6bbc16e8...`
  as a separate standalone-provider cohort.
- Preserved the scientific boundaries. Active Graph and agenticow are state
  substrates, not memory-quality results. MemForge does not implement learned
  automatic bidirectional paging, and its repository retracts the previous
  LongMemEval retrieval headline because the scorer ignored `k`; no benchmark
  number was admitted. Hermes Observational Memory was not retroactively added
  to the sealed eight bundled Hermes providers plus Memori.
- Expanded the validated ledger to 228 sources and 181 pinned repository
  records across 168 sources. The portfolio now contains 91 candidates under
  the unchanged 108-H100-hour ceiling; matrix SHA-256 is
  `b6f842198b3e487482d9137163b8e335eca5c98166bc1999d8f0bd800faaf5ab`.
- Retried `kevin@207.241.191.91` in batch mode; port 22 timed out before
  authentication. No job, model, CPU inference substitute, bare login-node
  workload, or `sudo` ran. Frozen ASTRA v7 remains the immutable next one-H100
  Docker-under-Slurm submission; this documentation delta does not recut it.

## 2026-08-15 — ASTRA native H100 lifecycle executed and blocked

- Restored access to `fal-h100-01` and ran the ASTRA native lifecycle only as
  Docker containers inside Slurm H100 allocations. No model, provider API,
  bare login-node workload, CPU inference substitute, or `sudo` was used.
- Retained integration failures rather than overwriting them: job 258 exposed
  npm acquisition failure; 259 caught a host-local versus portable image-ID
  mismatch; 260/261 rejected the first container-network topology; probe 267
  proved a `--network none`, shared-loopback CockroachDB topology; and job 268
  exposed an ESM package-scope launcher error before any lifecycle action.
- Sealed v11 source archive `e8bc1a97...`, kept the exact portable ASTRA app
  archive `eac83821...`, and mounted the archived doctor read-only inside
  ASTRA's `type: module` scope. Focused Ruff, shell, and 39 pytest checks passed;
  a network-disabled contained import probe reached the registered phase guard.
- Slurm job 269 then executed two complete clean-store lifecycles on one H100.
  Each repeat passed K=12 eviction, durable retrieval-driven re-admission,
  forced CockroachDB kill/restart recovery, two-user isolation, duplicate-write
  diagnosis, soft-delete residue, and pinned overflow.
- The final preregistered identity gate failed honestly. Equal recall totals
  (6 before restart, 12 after) incremented different tied records: four
  `access_count` rows differed before restart and ten after. Upstream vector,
  similarity, and fused-score ordering lack deterministic secondary keys.
- Sealed the negative result at
  `data/results/astra-native-lifecycle/2026-08-15-job269-v11/`; analysis
  SHA-256 is `adf6c86108a36617f4e98a4ac9e9e57d6f17deea56b11a8471e70bdd9a042f57`.
  Status is `BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING`, with
  `scientific_result=false` and `publication_ready=false`.
- Prohibited an ASTRA actor cell for revision `644f9d4`. A new immutable pin or
  explicit repair arm must pass deterministic tie-breaking, physical purge,
  idempotency-keyed writes, and pinned hard-cap gates before actor comparison.
  The next contained H100 admission is the standalone Hermes Observational
  Memory provider, followed by a fresh GAAMA actor-lane revalidation.

## 2026-08-15 — Hermes Observational Memory H100 lifecycle executed and blocked

- Ran the standalone provider only in Docker inside Slurm H100 allocations on
  `fal-h100-01`; no bare-node workload, CPU inference substitute, `sudo`, API
  credential, or model call was used. The lifecycle container deliberately had
  no GPU passthrough because this was a filesystem/provider admission doctor.
- Retained the full failure ladder through jobs 270–290. These jobs exposed and
  closed batch execution, offline dependency, Python-version, image-build,
  SBOM tmpfs, plugin-copy, empty-index readiness, and query-echo isolation
  defects before the final registered run.
- Job 291 completed two clean repetitions. Real Hermes standalone discovery,
  explicit-note persistence across a fresh process, separate-memory-root
  isolation, hard-budget refusal, and operator-scoped test-root removal passed;
  both semantic projections hash to `3d2af802...`.
- The preregistered deletion gate failed honestly. The provider exposes no
  native delete or forget tool and no physical-erasure contract. Operator-root
  cleanup is not provider-native erasure. Final status is
  `BLOCKED_NO_PROVIDER_NATIVE_DELETE_OR_ERASURE`, with
  `scientific_result=false`, `publication_ready=false`, and actor admission
  forbidden for revision `90d83c1f...` / core `6bbc16e8...`.
- Sealed the local evidence under
  `data/results/hermes-observational-memory-lifecycle/2026-08-15-job291-v13/`.
  Report SHA-256 is `1b828fcc...`, manifest `dc52dde2...`, Slurm receipt
  `01bb394a...`, SBOM `96bcdc39...`, and retained image archive
  `bd66a981...`. The machine-validated ledger receipt is
  `research/evidence/memory/hermes-observational-memory-lifecycle-v1.json`.
- The next H100 model-quality spend is not another provider retry. Revalidate
  the frozen GAAMA actor lane against current source/model/container receipts,
  then submit only if every Docker/Slurm admission gate remains exact.

## 2026-08-15 — GAAMA H100 actor translation completed and killed

- Built the exact dirty-worktree discovery source overlay through Slurm job 292
  and ran only the pinned Qwen3.5-4B actor inside Docker-under-Slurm H100 jobs
  295 and 297. No `sudo`, bare login-node inference, provider API, or CPU model
  substitute was used.
- Job 295 completed 656 of 1,000 registered cases, then handled a controlled
  in-container USR1 checkpoint and exited with
  `signal_USR1_checkpoint_confirmed`. Job 297 copied only the registered
  `gaama-actor` state, verified the predecessor identities, resumed at case
  656, and completed all 1,000 cases. The predecessor prediction journal is a
  byte-identical prefix of the successor; 20/20 deterministic A/A cases match.
- True graph evidence retained a small retrieval advantage over flat evidence
  (0.385 versus 0.375 recall-all@10), but answer token F1 was lower (0.2741
  versus 0.2831). The conversation-clustered true-minus-flat difference was
  -0.0088 with 95% CI [-0.0267, 0.0053]; true graph also failed to beat the
  mean of three typed topology shuffles. All integrity/competence gates passed
  and every registered graph-comparison gate failed.
- Final status is `GAAMA_H100_ACTOR_KILLED`, with `scientific_result=false` and
  `publication_ready=false`. Larger-model GAAMA escalation is forbidden. The
  earlier natural retrieval result remains component-only evidence.
- Sealed artifacts live at
  `data/results/gaama-h100-actor/2026-08-15-jobs295-297-v7/`. The report hashes
  to `129c5952...`; the machine-validated ledger receipt is
  `research/evidence/memory/gaama-h100-actor-negative-v1.json` at
  `7ca80f0a...`. The live source matrix is now `18dddb31...`, with 3 local
  conformance reproductions and 13 reproduced negatives.

## 2026-08-15 — Neo4j Agent Memory amd64 lifecycle confirmed under Slurm

- Slurm job 303 ran two clean exact-source Neo4j preference-supersession
  lifecycles on the cluster-amd64 Docker lane. One H100 was allocated only for
  scheduler provenance; no GPU was passed into either container and no model or
  embedding call occurred.
- Both repeats passed current/history/as-of semantics, exactly one native
  supersession edge, restart, branch isolation, lineage, idempotency, and
  zero-node/zero-edge purge. The repeats produced distinct state roots.
- Jobs 298-302 are retained honestly as preflight failures, including one
  mistaken early operator cancellation. They did not execute the lifecycle
  contract.
- The terminal status is
  `NEO4J_PREFERENCE_LIFECYCLE_CONFORMANCE_PASS`, with
  `scientific_result=false`, `publication_ready=false`, and no available
  `sacct` accounting. The report hashes to `1523a6b4...`; the retained validator
  receipt is `research/evidence/memory/neo4j-preference-lifecycle-h100-v1.json`
  at `dfeaf750...`.
- This closes only the amd64 lifecycle confirmation. A frozen
  identical-pre-extracted-tuple flat parity shadow is required before any graph
  efficacy claim or H100 actor admission.

## 2026-08-15 — Neo4j designed identical-tuple traversal parity passed

- Slurm job 304 ran two exact-source designed parity repetitions with the same
  Neo4j client image and SBOM used by the lifecycle lane. The scheduler
  allocated one H100 for provenance, but no GPU was passed to either container;
  model and embedding calls were zero.
- True traversal and an exact flat SQLite join ceiling each recovered 48/48
  targets. Flat BM25+dense retrieval and an object-degree-preserving shuffled
  topology recovered 0/48. This isolates traversal on the synthetic fixture,
  while the SQL tie explicitly forbids a unique graph-store claim.
- The report hashes to `b09978e2...`; the machine-validated receipt is
  `research/evidence/memory/neo4j-identical-tuple-flat-parity-h100-v1.json`
  at `e09d1638...`. `scientific_result=false` and
  `publication_ready=false` remain mandatory.
- The then-live source/portfolio matrix was `18dddb31...`; this component did
  not itself justify scaling.

## 2026-08-15 — Natural chronology topology failed before actor escalation

- Froze 64 immutable LongMemEval knowledge-update and temporal-reasoning
  questions and ran two byte-identical, network-disabled, read-only ARM64
  Docker repetitions. No GPU, model, embedding model, or provider call ran.
- Flat BM25+dense recall-all@4 was 0.34375. Spending two of four slots on
  chronological neighbors reduced it to 0.203125; the paired stratified
  bootstrap true-minus-flat 95% interval was [-0.234375, -0.046875]. True
  chronology also failed to beat any registered degree-preserving shuffle.
- Sealed the negative at
  `research/evidence/memory/longmemeval-natural-session-topology-negative-v1.json`
  (`2d2849d1...`). It is deterministic development evidence because the exact
  live source was mounted read-only into an older pinned image;
  `scientific_result=false` and `publication_ready=false` remain explicit.
- Cancelled the proposed Neo4j natural actor screen. The live source/portfolio
  matrix is `73d56d67...`, with 229 sources, 3 conformance reproductions, and
  14 reproduced negatives.

## 2026-08-16 — Mnemosyne lifecycle falsifier blocked H100 admission

- Pinned Mnemosyne OSS at `a0e14243e04dbe3fc29287e58126ff5dc0e02b35`
  and ran its lifecycle doctor twice in clean, network-disabled, non-root,
  read-only ARM64 Docker states. No model, embedding call, provider secret,
  GPU, or sudo was used.
- Both repetitions passed duplicate idempotency, session isolation, one-way
  working-to-episodic consolidation, and fresh-process recall. Recall did not
  reactivate consolidated state. Documented forget deleted the working row but
  left its episodic summary logically recallable and physically resident.
- Sealed terminal status
  `BLOCKED_CONSOLIDATED_FORGET_AND_NO_REACTIVATION` at
  `research/evidence/memory/mnemosyne-one-way-consolidation-negative-v1.json`
  (`3b516fa5...`). The report is `2479729d...`; the manifest is `d75a4430...`.
  `scientific_result=false`, `publication_ready=false`, and H100 actor
  admission is forbidden for this revision.
- The ledger now has 15 reproduced negatives. The 92-candidate portfolio keeps
  its 108-H100-hour ceiling and matrix `2a351fa5...`. The CPU admission queue is
  now Icarus then Palimpsest; Graphiti and GAAMA were removed from the pending
  list because their registered negative results are already complete.

## 2026-08-16 — Icarus manual lifecycle failed idempotency and native purge

- Pinned Icarus `0.3.0` at
  `6e348708dcddb7cf1ad47726cb287cd4c9183c40` and ran two clean, non-root,
  network-disabled, read-only ARM64 Docker lifecycles with no model, embedding,
  API, GPU, or sudo use.
- Both runs reproduced explicit working-to-private-archive-to-shared-wiki
  promotion, agent isolation, supersession, non-destructive rollback, and
  fresh-process restart.
- Both runs also reproduced the blocking defects: replaying `end_session`
  created another private summary and shared-wiki link; no native delete,
  forget, or scoped purge API exists; and all four private, shared,
  superseded, and replacement plaintext canaries remained resident.
- The current unbounded dependency solve selected incompatible MCP 2.0.0 and
  the upstream suite ended at 207 passed, 6 failed, and 39 skipped.
- Sealed `BLOCKED_NON_IDEMPOTENT_PROMOTION_AND_NO_NATIVE_PURGE` at
  `research/evidence/memory/icarus-manual-lifecycle-negative-v1.json`
  (`9d476930...`). The report is `1dd61644...`; the manifest is
  `150979e9...`. H100 actor admission is forbidden for this revision.
- The ledger now has 16 reproduced negatives. The 92-candidate portfolio keeps
  its 108-H100-hour ceiling and matrix `48151105...`. Palimpsest is the next
  bounded CPU lifecycle candidate.

## 2026-08-16 — Palimpsest lost bitemporal state across restart

- Pinned Palimpsest `0.1.0` at
  `0f83e166b0512a5ca9f38c2559f68749b35e994d` and ran two fresh,
  non-root, network-disabled, read-only ARM64 Docker lifecycles with no model,
  embedding provider, secret, GPU, or sudo use.
- Before restart, both repetitions passed ordinary valid-time behavior,
  transaction-time cutoff, mixed-cardinality voting, and native-save row-count
  idempotency. After restart, transaction closures and per-key cardinality state
  were lost, so historical knowledge and continued state diverged from the
  uninterrupted branch.
- Logical correction hid the canary but retained its plaintext in SQLite; the
  public surface exposes no native delete, forget, or scoped purge. The unlocked
  upstream suite ended at 274 passed, 11 failed, and 35 skipped.
- Sealed `BLOCKED_BITEMPORAL_RESTART_AND_NO_NATIVE_PURGE` at
  `research/evidence/memory/palimpsest-bitemporal-negative-v1.json`
  (`c0fa0f98...`), with report `cd3cf86d...` and manifest `2a168ddf...`.
  H100 actor admission is forbidden for this revision.
- The ledger now has 17 reproduced negatives. The 93-candidate portfolio keeps
  its 108-H100-hour ceiling and matrix `ad5bcddb...`. No next native CPU adapter
  is selected until the portfolio is re-ranked.

## 2026-08-16 — LightMem2 recovery crossed sessions and collided archives

- Pinned LightMem2 at `dfc67e8bc9373ca5b31bb412298565c9d65b29b6`
  and ran two clean non-root, network-disabled, read-only ARM64 Docker states
  with zero model, provider, GPU, or sudo use.
- Archive-before-stub and a strict lower-level session resolver passed, but the
  actual MCP recovery path searches every session under the shared state root.
  Both runs recovered another session's plaintext before and after restart.
- Two same-millisecond archive writes reused one path, so the first key
  resolved the second payload. No native scoped purge API exists and retained
  state archives still contained both session canaries.
- Sealed
  `BLOCKED_CROSS_SESSION_DISCLOSURE_ARCHIVE_COLLISION_AND_NO_NATIVE_PURGE`
  at `research/evidence/memory/lightmem2-context-paging-negative-v1.json`
  (`1d02c379...`). H100 actor admission is forbidden for this pin.

## 2026-08-16 — Shodh tiers overlap and strand state after restart

- Pinned Shodh at `98c6e4861847a76f75eb880acf9e145d30794a46`
  and ran the registered tier doctor twice under the same zero-model contained
  CPU contract.
- Both runs showed each new Working record already in RocksDB. Restart emptied
  the Working map while retaining a stale Working tier label on the durable
  record. A persisted 26-hour-old Session record reopened with no Session-map
  membership, and real maintenance made zero promotions.
- Public `forget(All)` returned two removals for one overlapping unique item.
  The raw plaintext probe was absent both before and after forget, so it does
  not establish physical erasure.
- A separately built locked image passed upstream tiering 15/15 and persistence
  20/20 network-disabled. Those suites do not test cache reconstruction or
  offline-aged promotion after a fresh process.
- Sealed `BLOCKED_OVERLAPPING_RESIDENCY_AND_RESTART_STRANDING` at
  `research/evidence/memory/shodh-tier-admission-negative-v1.json`
  (`e8805c42...`), with report `0bf608d5...` and manifest `e26146d5...`.
  H100 actor admission is forbidden for this revision.
- The live ledger now has 19 reproduced negatives. The 93-candidate portfolio
  retains its 108-H100-hour ceiling at matrix `1282713c...`.

## 2026-08-16 — Mnemon passed a narrow static active-space admission

- Pinned Mnemon core `88d2981` and the separate `dsh-mnemon` plugin `1889c68`.
  The ownership correction matters: the plugin, not core, implements the
  persistent active-store registry and recall filtering.
- Two fresh, non-root, network-disabled, read-only ARM64 Docker runs reproduced
  distinct named databases, active-only default recall, inactive-read refusal,
  targeted-write activation, and restart-stable registry state with zero model,
  provider, GPU, secret, or sudo use.
- The same runs reproduced a hard boundary: item forget is soft and retained
  plaintext in SQLite. Whole-space deletion removed a non-final store, while
  deletion of the final native store was rejected.
- Sealed
  `ADMITTED_STATIC_ACTIVE_SPACE_CONTROL_WITH_SOFT_DELETE_BOUNDARY` at
  `research/evidence/memory/mnemon-active-space-admission-v1.json`
  (`27d7d55c...`), report `16aa5697...`, manifest `491681e4...`, and stable
  projection `34ace600...`.
- Scientific and publication claims remain false. Admission is limited to a
  frozen H100 comparison of no memory, all spaces, lexical static routing, and
  an oracle-space ceiling at equal retrieval and context budgets.
- The live ledger now records 229 sources, 182 pinned repositories, four local
  conformance reproductions, and 19 negative findings. The 93-candidate
  portfolio matrix is `7f05e5e5...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — Mnemon static routing was killed on H100

- Slurm job 313 completed the preregistered 128-case Qwen3.5-4B panel on one
  H100; job 315 resumed from a fresh allocation and reproduced all five actor
  artifacts byte-for-byte without regenerating any case.
- No-memory scored 0.0 exact/F1. All-spaces, lexical routing, and oracle-space
  each scored 1.0. Lexical routing therefore had zero quality lift over the
  strongest non-oracle control, and the lexical/all prompt-token ratio of
  0.7815 failed the matched-budget gate.
- Sealed `MNEMON_STATIC_ROUTING_KILLED` at
  `research/evidence/memory/mnemon-h100-static-space-negative-v1.json`
  (`e94b3ece...`), with report `492c9d43...`, predictions `6b435f03...`,
  and exact-resume checkpoint `b2e20ffe...`.
- The exact Mnemon `88d2981` plus `dsh-mnemon` `1889c68` revision is now
  blocked from further actor escalation. The ledger moves Mnemon from local
  conformance to local negative: three conformance results and 20 reproduced
  negatives. The 93-candidate portfolio remains capped at 108 H100-hours with
  matrix `ee133143...`.

## 2026-08-16 — RecMem consolidation failed lifecycle admission

- Pinned RecMem `a84252f` / tree `46d1315`, MIT, with archive
  `274aba95...` and lock `94803e92...`.
- Two fresh, non-root, network-disabled, read-only ARM64 Docker runs reproduced
  an exact retry creating a duplicate raw record, omission of the triggering
  write from native `raw_ids` lineage, and destructive loss of the prior
  episode when replacement embedding failed after deletion.
- Successful consolidation survived a fresh-process reopen and conversation
  isolation passed; no provider, model, GPU, secret, or sudo path was used.
- Sealed
  `BLOCKED_NON_IDEMPOTENT_WRITE_MERGE_DATA_LOSS_AND_INCOMPLETE_LINEAGE` at
  `research/evidence/memory/recmem-consolidation-negative-v1.json`
  (`d870b8d1...`). Scientific/publication claims are false, and H100 quality
  actor admission is forbidden for this exact revision.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 21 negative findings. The 93-candidate
  portfolio matrix is `f5f10303...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — TokenMizer checkpoint lifecycle failed active/inactive admission

- Pinned TokenMizer `131e3d1` / tree `cc5e934`, MIT, and executed two clean
  non-root, network-disabled, read-only ARM64 Docker repetitions.
- Both runs were byte-identical. Normal checkpoint text, fresh-process resume,
  and session isolation passed, but restart lost incremental diff history,
  manual checkpoint retry duplicated durable rows, corrupt-store recovery
  recreated an empty database, and no native scoped purge exists.
- The discovery image prefetched the upstream hash-verified `o200k_base` asset;
  no provider, model, GPU, secret, or sudo path ran.
- Sealed `TOKENMIZER_ACTIVE_INACTIVE_ADMISSION_KILLED` at
  `research/evidence/memory/tokenmizer-checkpoint-negative-v1.json`
  (`932bb2c0...`). Scientific/publication claims are false, context-compaction
  quality was not tested, and this revision is forbidden from the
  active/inactive H100 wave.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 22 negative findings. The 93-candidate
  portfolio matrix is `6512868d...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — TiMem core runtime failed admission before model execution

- Pinned TiMem `6d279a5` / tree `24645b2`, core-engine Apache-2.0 scope, and
  ran two clean non-root, network-disabled, read-only ARM64 Docker repetitions.
- The source compiled, but L1 instantiated its processor class as a record, L2
  passed unsupported fields to its local session dataclass and returned
  `None`, and L5 omitted required timestamps from both normal and fallback
  construction.
- Sealed `TIMEM_CORE_RUNTIME_ADMISSION_KILLED` at
  `research/evidence/memory/timem-core-runtime-negative-v1.json`
  (`742f0f67...`). No provider, model, GPU, secret, or sudo path ran.
- Scientific/publication claims are false; hierarchy quality and residency
  effects were not tested, and this exact revision is forbidden from H100.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 23 negative findings. The 93-candidate
  portfolio matrix is `995b9b54...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — Mnemosyne Cognitive failed active/inactive lifecycle admission

- Pinned Mnemosyne Cognitive `5506aae` / tree `d5cb986`, MIT, and ran two clean
  non-root Docker repetitions against an isolated digest-pinned Qdrant sidecar.
- Both structured repeats matched exactly. Dry-run consolidation mutated state,
  repeated consolidation demoted the same record again, and the record remained
  in normal serving search rather than crossing into an inactive tier.
- Public forget hid its target logically but left the Qdrant point, tombstone,
  and exact plaintext canary resident after a fresh database process. The public
  surface exposes no native scoped purge.
- The four committed upstream Vitest files passed 62/62 twice; those mock-only
  tests do not cover the reproduced native lifecycle failures.
- Sealed `MNEMOSYNE_COGNITIVE_ACTIVE_INACTIVE_ADMISSION_KILLED` at
  `research/evidence/memory/mnemosyne-cognitive-lifecycle-negative-v1.json`
  (`6ee8209b...`). Graph and memory quality were not tested; this exact revision
  is forbidden from H100 actor work.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 24 negative findings. The 93-candidate
  portfolio matrix is `71b754cb...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — MemForge failed exact-schema fresh-install admission

- Pinned MemForge `16e2f15` / tree `97411a5`, MIT, and ran two clean attempts
  in each of two non-root, network-disabled, read-only ARM64 Docker lanes.
- The repository's exact Compose PostgreSQL image lacks the required vector
  extension. A digest-pinned pgvector control then exposed a second independent
  blocker: canonical schema line 57 indexes `warm_tier` before line 73 creates
  the table. All four attempts exited 3 before initialization completed.
- Sealed `MEMFORGE_FRESH_INSTALL_ADMISSION_KILLED` at
  `research/evidence/memory/memforge-fresh-install-negative-v1.json`
  (`299d7b9d...`). No provider, model, GPU, secret, or sudo path ran.
- No hot/warm/cold, graph, or memory-quality mechanism was evaluated. The exact
  revision is forbidden from H100 actor work; any schema repair is a separate
  preregistered intervention.
- The live ledger now records 229 sources, 168 pinned-repository sources, three
  conformance reproductions, and 25 negative findings. The 93-candidate
  portfolio matrix is `c6b43798...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — MemoryBank corrected decay lost to no decay on H100

- Ran the three frozen MemoryBank controls against Qwen3.5-4B in
  network-disabled Docker under Slurm on one H100. Initial jobs 328-330 and
  exact checkpoint resumes 333-334 completed the registered task/seed matrix.
- Corrected decay beat the historical upstream-precedence expression by 10.97
  executable-success points, with task-clustered bootstrap 95% interval
  `[6.15, 16.24]`. This confirms that the upstream expression is defective on
  the synthetic panel.
- The matched no-decay control beat corrected decay by 58.39 points; expressed
  as corrected minus no decay, the interval was `[-66.77, -50.00]`. Every cell
  produced valid actions and there were zero safety failures.
- Sealed `MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING` at
  `research/evidence/memory/memorybank-h100-actor-v1.json` (`bd069e22...`). The
  aggregate file is `8a7e377b...` and its semantic root is `27044eb2...`.
- This is a negative discovery result, not an upstream MemoryBank or paper
  reproduction. The source archive captured a dirty development tree and the
  panel is synthetic. Do not scale this exact forgetting mechanism to a larger
  model; a future mechanism must first beat no decay at matched resource and
  tuning budgets.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 26 negative findings. The 93-candidate
  portfolio matrix is `a7373a2d...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — LightMem exact-source admission failed before H100

- Pinned LightMem `8fc9a917` / tree `343831b5`, MIT root license with conflicting
  Apache-2.0 package metadata, and no root dependency lock.
- Ran the exact `LightMemory` and Qdrant source through two clean, byte-identical,
  non-root, network-disabled, read-only ARM64 Docker repetitions with no model,
  provider, secret, GPU, or sudo path.
- Reproduced destructive default local-store reopen, a no-op online update,
  an invalid automatic-consolidation keyword, stale embeddings after payload
  changes, broken context-only retrieval, absent source-event lineage, and no
  native scoped purge surface. The positive later-source-to-earlier-target
  consolidation direction also reproduced.
- Sealed
  `BLOCKED_DESTRUCTIVE_DEFAULT_REOPEN_AND_CONSOLIDATION_CONTRACT_DRIFT` at
  `research/evidence/memory/lightmem-offline-negative-v1.json` (`2c99c194...`)
  with stable projection `80a2b06c...` and audit
  `research/lightmem-offline-consolidation-audit-2026-08-16.md`.
- This is exact-source lifecycle/component evidence, not a LightMem paper or
  memory-quality reproduction. The revision is removed from the H100 execution
  order and must not be called an active/inactive pager.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 27 negative findings. The 93-candidate
  portfolio matrix is `4a65532f...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — Memoria failed transactional lifecycle admission

- Pinned Memoria `efd3d651` / tree `c07d7b4` and MatrixOne image
  `sha256:66e2e012...`; ran the exact `memoria-git` and `memoria-storage` source
  through two clean non-root ARM64 Docker states on an internal network.
- Native snapshot, branch divergence, conflict-preserving merge, idempotent
  re-merge, branch/snapshot deletion, and two forced MatrixOne restarts passed
  in both repetitions.
- The legacy shared-database branch contained another user's rows. Native purge
  left the inactive memory row physically resident after restart, while the
  public service source reports `purged: 1` independently of the deactivation
  count. Snapshot restore is a non-atomic delete-then-insert sequence.
- Sealed
  `BLOCKED_SHARED_TABLE_BRANCH_EXPOSURE_SOFT_PURGE_RESIDUE_AND_NONATOMIC_ROLLBACK`
  at
  `research/evidence/memory/memoria-transactional-lifecycle-negative-v1.json`
  (`92c8427e...`) with stable projection `b5281d07...` and audit
  `research/memoria-transactional-lifecycle-audit-2026-08-16.md`.
- This is component/lifecycle evidence only, not multi-database isolation,
  retrieval quality, active/inactive paging, a paper result, or publication
  evidence. The exact revision is removed from H100 execution order.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 28 negative findings. The 93-candidate
  portfolio matrix is `76d85fbf...` under the unchanged 108-H100-hour ceiling.

## 2026-08-16 — Agent Recall failed scoped lifecycle admission

- Pinned Agent Recall `dcf21b5` / tree `1c0395b2`, MIT, and ran the exact
  store, hierarchy, MCP bridge, and cache source through two clean non-root,
  read-only, network-disabled ARM64 Docker repetitions.
- Scope precedence, bitemporal correction history, and fresh-process restart
  persistence passed with identical phase projection `2fed18f7...`.
- A client-a bridge deleted a shared entity carrying client-b observations;
  parent-scope writes left descendant briefing caches fresh; soft observation
  deletion retained plaintext in SQLite after restart; and no native scoped
  purge surface exists.
- Sealed
  `BLOCKED_CROSS_SCOPE_DESTRUCTIVE_DELETE_STALE_CHILD_BRIEFING_AND_SOFT_DELETE_RESIDUE`
  at `research/evidence/memory/agent-recall-scope-lifecycle-negative-v1.json`
  (`c9695f9f...`) with audit
  `research/agent-recall-scope-lifecycle-audit-2026-08-16.md`.
- This is exact-source lifecycle/component evidence, not briefing or retrieval
  quality, active/inactive paging, model-effect, or publication evidence. The
  exact revision is removed from H100 execution order.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 29 negative findings. The 93-candidate
  portfolio matrix is `ce3c1db6...` under the unchanged 108-H100-hour ceiling.
## 2026-08-16 — Active Graph fork positive, erasure admission negative

- Pinned Active Graph `8aedb186...` / tree `8f101d35...` and ran two fresh
  non-root, network-disabled, read-only ARM64 Docker lifecycle repetitions with
  one fresh-process restart each. Parent/fork divergence, nested-fork
  isolation, structural diff, restart, retirement, and retirement idempotency
  passed with stable projection `bc1be630...`.
- The native retention contract is explicitly archive-only: retiring the
  rejected run moved its events to `events_archive` in the same SQLite file,
  while run metadata and the unique plaintext canary remained after restart.
  The pinned public store exposes no native run-scoped purge. Terminal status
  is `BLOCKED_ARCHIVE_ONLY_RETENTION_NO_SCOPED_PURGE_AND_SHARED_DB_ERASURE`;
  H100 actor admission is forbidden for this revision.
- Sealed receipt
  `research/evidence/memory/activegraph-fork-lifecycle-negative-v1.json`
  hashes to `69a0a896...`; the retained report hashes to `74b2ec1d...` and the
  artifact manifest to `b64277d4...`. The ledger now reports 30 reproduced
  negatives; the 93-candidate portfolio remains capped at 108 H100-hours with
  matrix `87c05c3d...`.

## 2026-08-16 — agenticow branch positive, promotion and erasure negative

- Pinned agenticow `dd4f437...` / tree `b64b6fae...` and ran two fresh
  non-root, network-disabled, read-only ARM64 Docker lifecycle repetitions with
  one fresh-process restart each. Branch and nested-fork isolation, checkpoint
  rollback, tombstone masking, sibling visibility, restart persistence, and
  repeated-promotion logical idempotency passed with stable projection
  `eeb24984...`.
- Promotion silently overwrote a newer parent update without a conflict guard,
  and the lost update persisted after restart. Tombstoned plaintext remained in
  the persisted manifest, and the pinned API exposes no native branch-scoped
  physical purge or cryptographic erasure contract.
- Sealed
  `BLOCKED_BLIND_PROMOTION_LOST_UPDATE_TOMBSTONE_RESIDUE_AND_NO_SCOPED_PURGE`
  at `research/evidence/memory/agenticow-branch-lifecycle-negative-v1.json`
  (`87b045a1...`) with audit
  `research/agenticow-branch-lifecycle-audit-2026-08-16.md`.
- This is exact-source lifecycle/component evidence, not memory quality,
  active/inactive paging, model-effect, or publication evidence. The exact
  revision is removed from H100 execution order.
- The live ledger now records 229 sources, 182 pinned repositories, three
  conformance reproductions, and 31 negative findings. The 93-candidate
  portfolio matrix is `4174f49e...` under the unchanged 108-H100-hour ceiling.

## 2026-08-17 — ASTRA native lifecycle evidence promoted into the ledger

- Reconciled the stale split between project memory, which correctly recorded
  Slurm job 269's ASTRA lifecycle negative, and the source ledger/portfolio,
  which still described that native lifecycle as unexecuted.
- Added the reusable sealer and strict validator
  `scripts/seal_astra_native_lifecycle_evidence.py`. The committed receipt
  `research/evidence/memory/astra-native-lifecycle-negative-v1.json`
  (`8bf14f32...`) embeds `analysis.json`, both repeat checkpoints, the manifest,
  scheduler output, and the scheduler allocation receipt; it does not depend on
  ignored `data/` to remain verifiable.
- The validator rechecks containment, one-H100 Slurm allocation, forced restart,
  durable re-admission, isolation, purge/idempotency/pin-cap blockers, exact
  projection hashes, equal access totals, and the four/ten differing persistent
  access-count records across clean stores.
- Promoted ASTRA `644f9d4` from component conformance to
  `BLOCKED_NONDETERMINISTIC_RECALL_ACCESS_ACCOUNTING`, added it to killed
  revisions, removed it from H100 execution order, and preserved the earlier
  26/26 component receipt as bound prior evidence. No actor or memory-quality
  claim is admitted for this revision.
- The live ledger now records 229 sources, 182 pinned repositories, two
  conformance reproductions, and 32 bounded negative findings. The 93-candidate
  portfolio remains capped at 108 H100-hours with matrix `be14faf7...`; the
  active/inactive wave has no executable admitted candidate.

## 2026-08-17 — LangMem persistent lifecycle positive, erasure admission negative

- Pinned LangMem `29cbe41...` / tree `d85d1f81...`, added the official
  `langgraph-checkpoint-postgres==3.1.0` persistent store path, and ran two
  clean ARM64 Docker repetitions over an internal bridge with one clean
  PostgreSQL plus fresh-process restart per repeat.
- Public hot-path create/update/search/delete, deterministic background-manager
  persistence, user namespace isolation, logical deletion, and restart all
  passed with stable semantic projection `96602010...`. Deterministic
  extraction isolated lifecycle plumbing from model quality; vector search was
  intentionally outside the contract.
- The exact `PostgresStore` surface exposes record deletion but no first-class
  namespace purge. Enumerate-then-delete made all tested scopes logically
  empty, but every original, updated, isolated, and background plaintext
  canary remained in both PostgreSQL heap and WAL after clean shutdown in both
  repetitions. Each hit is retained as a bounded, self-verifying proof window.
- Sealed terminal status
  `BLOCKED_NO_FIRST_CLASS_SCOPED_PURGE_AND_POSTGRES_PLAINTEXT_RESIDUE` at
  `research/evidence/memory/langmem-native-lifecycle-negative-v1.json`
  (`76f8b3d8...`) with audit
  `research/langmem-native-lifecycle-audit-2026-08-17.md`. H100 actor admission
  is forbidden for this revision; extraction, semantic retrieval, procedural
  prompt quality, model effects, and managed-service behavior remain untested.
- The live ledger now records 229 sources, 182 pinned repositories, two
  conformance reproductions, and 33 bounded negative findings. Removing this
  killed candidate from the first wave lowers the 93-candidate portfolio
  ceiling to 100 H100-hours with matrix `691956fb...`.

## 2026-08-17 — Fidelis zero-LLM retrieval result reproduced

- Pinned Fidelis `0950ff3...` / tree `d50069ac...`, the MIT source archive,
  LongMemEval-S cleaned revision `98d7416...`, official Ollama v0.20.6 Darwin
  binary, exact `nomic-embed-text` manifest and blobs, Python 3.11.15,
  `bm25s==0.3.3`, and `numpy==2.4.4` by artifact and installed-tree hashes.
- Four deterministic no-filter shards restored the 470 non-abstention
  questions and reproduced every committed upstream Stage 1b top-five ID and
  logged-score list. Recomputed recall-any@1 is 391/470 (83.2% rounded) and
  recall-any@5 is 462/470 (98.3% rounded).
- A one-question falsifier under official Ollama v0.32.9 and the same model
  artifacts moved the gold session from rank one to rank three. The runtime is
  part of the treatment; the result is not portable across unpinned Ollama
  versions.
- Audited two upstream instrumentation boundaries: v35 logs pre-temporal-boost
  scores beside post-boost IDs on 90 boosted questions, and resume does not
  restore every aggregate/timing accumulator. Scores remain exact transport
  evidence, while metrics are recomputed from IDs; the entire local aggregate
  and all latency claims are excluded.
- Sealed `FIDELIS_ZERO_LLM_RETRIEVAL_REPRODUCTION_PASS` at
  `research/evidence/memory/fidelis-zero-llm-retrieval-v1.json`
  (`32e5327f...`) with audit
  `research/fidelis-zero-llm-reproduction-2026-08-17.md`. Stage 2, the 73.0%
  QA claim, packaged-service equivalence, write/persistence lifecycle,
  generalization, network isolation, and external attestation remain outside
  the reproduced claim.
- The ledger now records its first locally reproduced scientific result: 229
  sources, 182 pinned repositories, one scientific reproduction, two
  conformance reproductions, and 33 negative findings. The 93-candidate
  portfolio remains capped at 100 H100-hours with matrix `90ac9627...`;
  Fidelis still requires a matched common-actor control matrix and protected
  external attestation before any H100 claim cell.

## 2026-08-17 — SodaMem released artifacts audited, system result not reproduced

- Registered the previously unregistered LangMem experiment contract in the
  generic memory gate, added fail-closed tests, and resealed its evidence after
  the contract hash changed. All 50 memory experiment contracts now validate;
  the LangMem receipt is `ffc7e656...`.
- Pinned SodaMem `b182c1a...` / tree `2c6f29b...`, source archive
  `2abd4be8...`, Apache-2.0 license, upstream lock, two released LongMemEval
  artifacts, and the existing independently pinned LongMemEval-S dataset.
- The upstream documented `dev` environment was incomplete for its collected
  tests: it omitted the declared `chroma`, `llm`, and `server` extras. With
  those extras added under the exact lock, the source passed 737 tests with 19
  skips.
- Two byte-identical, zero-API, zero-LLM CPU audits aligned every released row
  to all 500 LongMemEval-S tasks, including 30 abstentions and 32 numeric
  answers; recomputed the stored same-model self-judge score at 464/500; and
  validated 8,427 nonempty retrieved evidence rows.
- The audit also exposed hard evidence boundaries. The judged artifact stores
  `evidence_ids: true` rather than an ID list on all 500 rows. The raw source
  spans and 12 GB store are absent, the reader prompt was not captured, and
  the pre-release construction code cannot be recovered from this tree.
  Full normalized reference text appears in 314 hypotheses and 239 of 470
  non-abstention retrieval unions; these counts are diagnostics, not semantic
  accuracy or evidence sufficiency.
- Sealed
  `SODAMEM_RELEASED_ARTIFACTS_AUDITED_NOT_REPRODUCED` at
  `research/evidence/memory/sodamem-published-artifact-audit-v1.json`
  (`a9e914b2...`) under the new non-scientific
  `local-artifact-audited` evidence grade. H100 admission remains ungranted;
  next gates are a provider-distinct judge and a common-construction
  SodaMem-versus-flat-history-versus-temporal-graph control.
- Removed SodaMem from both H100 execution orders and reduced only the affected
  finite wave ceilings. The validated 93-candidate portfolio is now capped at
  84 H100-hours with matrix `3b19dba0...`; the ledger still records one
  scientific reproduction, two conformance reproductions, and 33 negative
  findings, plus one artifact audit.

## 2026-08-17 — GBrain exact-source BrainBench conformance reproduced

- Pinned GBrain `d941e9f...` / tree `4d7960c...`, its MIT license,
  exact source archive, `bun.lock`, and official Bun 1.3.13 Darwin ARM64
  release and binary.
- Installed the frozen dependency graph with machine-global lifecycle scripts
  disabled, then passed 146 focused upstream tests and 725 assertions across
  12 source files.
- Two provider-credential-free BrainBench runs passed the committed same-hash
  gate with no breaches or seed failures. The stable semantic projection covers
  12 harness/suite cells and 786 turn rows and hashes to `8e4ebad2...`; all
  source-isolation violation counts were zero.
- Preserved the seam boundary: OpenClaw is the only shipped production seam.
  Claude Code and Codex are GBrain-owned contract adapters, not reproduced
  third-party production integrations.
- BrainBench has no matched pull-retrieval arm, so this does not answer the
  registered push-versus-pull question and is not a live-agent, memory-quality,
  model-quality, or publication result.
- Sealed `GBRAIN_BRAINBENCH_CONFORMANCE_PASS_PULL_COMPARISON_MISSING` at
  `research/evidence/memory/gbrain-brainbench-conformance-v1.json`
  (`4c6f6d5f...`) as `local-conformance-reproduced` evidence. Removed GBrain
  from H100 execution order and marked it `source-admission-blocked` until a
  matched production OpenClaw push-versus-pull cell exists.
- The live ledger now records one scientific reproduction, three conformance
  reproductions, 33 negative findings, and one artifact audit. The validated
  93-candidate portfolio remains capped at 84 H100-hours with matrix
  `70b38eee...`.

## 2026-08-17 — Sage Wiki released artifacts audited, provenance gate blocked

- Pinned Sage Wiki `78b7157...` / tree `f04621c...`, tag `v0.2.9`, its MIT
  license, exact source archive, Go lock, ten committed benchmark artifacts,
  and independently pinned LongMemEval-S and LoCoMo-10 datasets.
- The exact source passed 158 Python evaluation tests and 359 focused Go tests
  with 18 skips and zero failures under Go 1.26.6.
- Two byte-identical zero-API audits recomputed every stored overall, group,
  cutoff, and latency aggregate; verified all 45 report annotations; and
  aligned 61 LongMemEval plus 3,235 LoCoMo artifact rows to the pinned datasets
  and committed deterministic sample policies.
- Preserved the hard boundary: every result names an unbound dev binary,
  retrieval IDs/text and compiled stores are absent, provider aliases are not
  immutable snapshots, BEAM is not revision-pinned, `locomo_full` has stitched
  usage metadata, and `locomo_parity` contains 1,011 infrastructure errors.
- No matched flat arm exists and retrieval, actor, judge, depth, prompts, and
  samples changed together across result generations. The artifacts do not
  identify a graph mechanism effect or reproduce benchmark quality.
- Sealed
  `SAGE_WIKI_RELEASED_ARTIFACTS_AUDITED_BINARY_AND_RETRIEVAL_PROVENANCE_MISSING`
  at `research/evidence/memory/sage-wiki-published-artifact-audit-v1.json`
  (`eeb7f14c...`) as non-scientific `local-artifact-audited` evidence.
- Marked Sage Wiki `artifact-audited-not-reproduced`, removed it from H100
  execution order, and retained the 84-H100-hour ceiling. The 93-candidate
  matrix is now `9528d123...`; the ledger has one scientific reproduction,
  three conformance reproductions, 33 negative findings, and two artifact
  audits.
