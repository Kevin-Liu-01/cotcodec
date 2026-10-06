# CoTCodec Research Plan

Updated: 2026-04-29
Status: active replan during `phase_1_foundation`

## Executive Direction

CoTCodec is no longer just a "language paper." It is a research program about
**orchestration variables** for tool-using agents, with language as the first
clean intervention.

The current sequencing should be:

1. Keep **Variable 1 (language)** as Paper 1 because it is still the cleanest
   inference-time intervention.
2. Pull **Variable 14 (degradation detection)** into the foundation layer.
   Without regression detection, every later result is suspect.
3. Pull **Variable 13 (harness beats model)** forward as the first meta-result.
   It is the strongest justification for why this whole research program matters.
4. Reframe **Variable 2 + Variable 15** as the next major paper: reasoning
   media, compression, and monitorability.
5. Delay lower-tractability coordination variables until the harness, canaries,
   and measurement pipeline are stable.

## What Changed

Three updates materially changed the plan:

- **Abstract-CoT changed the efficiency ceiling.** Language routing is still the
  best inference-time-only intervention, but it now sits on a broader reasoning
  media spectrum that ends in learned abstract tokens.
- **The 2026 degradation wave changed the bar for evidence.** Anthropic's
  April 23 postmortem showed that harness-level changes can dominate perceived
  model quality. That makes degradation detection core infrastructure, not a
  side experiment.
- **The benchmark landscape improved.** MCP-Atlas, Toolathlon, Amazing Agent
  Race, and SWE-bench Verified make it possible to test orchestration variables
  on realistic agent trajectories instead of toy reasoning tasks.

## Program Order

| Order | Track | Variables | Why now | Exit criteria |
|------:|-------|-----------|---------|---------------|
| 1 | Trustworthy harness | 14 + core infra | Every later result depends on this | Canary benchmark runs; per-sample regression tests wired in |
| 2 | Paper 1: language routing | 1 + structured/compressed baselines from 2 | Easiest to manipulate and measure | Pilot results on at least 2 agent benchmarks |
| 3 | Meta result: harness vs. model | 13 | Strongest framing result for the whole thesis | Pareto comparison old+orchestrated vs. new+naive |
| 4 | Paper 2: reasoning media | 2 + 15 | Abstract-CoT makes reasoning format the next frontier | Efficiency-monitorability study scoped and benchmarked |
| 5 | Paper 3: state management | 3, 4, 5, 9 | These are the next highest-leverage orchestration variables | Memory/context/observation study designed |
| 6 | Paper 4+: control and coordination | 6, 7, 8, 10, 11, 12 | Important but more coupled and harder to isolate | Stable harness and reusable evaluation stack |

## Priority Stack

### Track A: Foundation Infrastructure

Primary goal: make the harness trustworthy enough that negative results are
credible.

Immediate work:

- Finish trace collection and token/cost accounting end-to-end.
- Build `OrchVar-Canary` as a fast regression suite.
- Add McNemar-style per-sample regression testing.
- Set up local-model pilots so benchmark plumbing can be validated cheaply.
- Add message-type decomposition to the metrics pipeline.

Key artifacts:

- `experiments/degradation_canary_01.yaml`
- `harness/metrics/degradation.py`
- reproducible baseline summaries in `data/results/`

### Track B: Paper 1 — Language as an Orchestration Variable

Primary claim: internal language choice changes the cost-latency-success
frontier of agent trajectories, or fails to do so in a precisely measurable way.

Core conditions:

- `english_only`
- `internal_chinese`
- `controlled_chinese`
- `english_compressed`
- `structured_english`
- `dynamic_router`
- `polish_stress`

Benchmarks to prioritize first:

- `tau-bench`
- `MCP-Atlas`
- `Toolathlon`

Success criteria:

- Message-type decomposition identifies where savings arise.
- Tool-call correctness and safety are measured, not assumed.
- Dynamic router is compared against every fixed condition.

### Track C: Harness Beats Model

Primary claim: orchestration variance can match or exceed model-generation
variance on agent tasks.

This track is the best umbrella result for the entire program because it turns
"interesting harness tricks" into a scientific statement about where performance
actually comes from.

Priority comparison sets:

- `claude-sonnet-3.5` + optimized orchestration vs. `claude-opus-4.7-adaptive` + naive orchestration
- `gpt-4o` + optimized orchestration vs. `gpt-5.5` + naive orchestration
- later: cross-provider Pareto frontiers with consistent benchmark slices

Key artifact:

- `experiments/harness_beats_model_01.yaml`

### Track D: Paper 2 — Reasoning Media and Monitorability

Primary claim: the right question after language is not "which language is
best," but "which reasoning medium is best for which agent message type under
an explicit monitorability budget?"

This paper should unify:

- free-form natural language reasoning
- compressed English
- structured protocols
- symbolic or program-like reasoning
- hybrid abstract + verbal checkpoints
- fully abstract reasoning when provider/model support exists

This is where the `MonitorabilityCost` term becomes a first-class part of the
objective.

### Track E: Later Variable Clusters

Once the measurement stack is reliable, the most promising next cluster is:

- `03-memory-policy`
- `04-context-allocation`
- `05-observation-granularity`
- `09-compaction-policy`

These variables are tightly coupled and likely dominate long-horizon agent
behavior more than planning or delegation in the near term.

## What To Defer For Now

These are still important, but they should not steal attention before the first
four tracks are operational:

- `10-tool-scheduling`
- `11-delegation-topology`
- `12-instruction-hierarchy` beyond the safety subset already needed for Paper 1
- full-scale `06-planning-depth` and `07-retry-recovery` sweeps before the
  canary and baseline infrastructure are stable

## Near-Term Execution Plan

### May 2026

- Make the harness runnable end-to-end on local models.
- Wire in token accounting, latency, and outcome summaries.
- Run `pilot_01_tau_bench.yaml` on a tiny slice.
- Stand up the first `OrchVar-Canary` task set.

### June 2026

- Run `pilot_02_all_conditions.yaml` on at least one tool benchmark.
- Produce the first message-type decomposition plots.
- Run `degradation_canary_01.yaml` to validate regression sensitivity.
- Establish naive baselines for old and frontier model tiers.

### July 2026

- Run the first `harness_beats_model_01.yaml` comparison.
- Decide whether Paper 1 needs a narrower benchmark set for statistical power.
- Draft the Paper 2 design note around monitorability tax and abstract reasoning.

### August 2026

- Lock the Paper 1 evaluation design.
- Prepare a concrete update for Danqi with benchmark choice, conditions, and
  the first meta-result.
- Decide whether Variable 15 is ready to become the formal Paper 2 proposal.

## Success Criteria Before Fall 2026

By the time advisor discussions restart, the project should have:

- a working benchmark harness with trustworthy trace collection
- a regression canary that catches orchestration failures quickly
- pilot evidence for or against Paper 1's language thesis
- one credible harness-vs-model comparison figure
- a written Paper 2 framing around reasoning media and monitorability

## Bottom Line

The clean version of the plan is:

- Build the measuring instrument first.
- Use language as the first publishable intervention.
- Use degradation detection to keep the measurements honest.
- Use harness-vs-model to justify the whole program.
- Use abstract reasoning and monitorability as the next frontier once the first
  paper is grounded.
