# CoTCodec Experiment Backlog

Updated: 2026-04-29

This is the execution view of the research plan. The goal is to keep the
sequence concrete: which experiments are runnable now, which are blocked, and
what each experiment is supposed to prove.

## Current Rule

No experiment graduates to a paid, multi-seed run until:

- the config parses cleanly
- the benchmark adapter loads tasks
- traces flush to disk
- metrics summarize without manual patching

If any of those fail, it is still harness work, not science.

## Priority Queue

| Priority | Experiment | File | Purpose | Status | Main blocker |
|---------:|------------|------|---------|--------|--------------|
| 0 | Canary smoke | `degradation_canary_01.yaml` | Prove the regression harness catches known-bad orchestration changes | Partially runnable | actual agent loop still stubbed |
| 1 | Language pilot | `pilot_01_tau_bench.yaml` | Validate trace interception and metric plumbing on core Paper 1 conditions | Config-ready | `tau_bench` adapter not implemented |
| 2 | All-conditions pilot | `pilot_02_all_conditions.yaml` | Get first directional signal across all language conditions | Config-ready | `tau_bench` adapter not implemented |
| 3 | Full tau-bench | `full_01_tau_bench.yaml` | Publication-grade Paper 1 single-model run | Planned | benchmark + real model execution |
| 4 | Harness beats model | `harness_beats_model_01.yaml` | Meta-result: orchestration variance vs model-generation variance | Config-ready | benchmark + real model execution |
| 5 | Frontier comparison | `frontier_comparison_01.yaml` | Cross-provider language-routing comparison | Config-ready | benchmark + cost budget |

## Experiment Readiness

### Ready at the config layer

- `experiments/degradation_canary_01.yaml`
- `experiments/frontier_comparison_01.yaml`
- `experiments/full_01_tau_bench.yaml`
- `experiments/harness_beats_model_01.yaml`
- `experiments/pilot_01_tau_bench.yaml`
- `experiments/pilot_02_all_conditions.yaml`

Meaning:

- the parser understands their model and condition structure
- benchmark names resolve through the runner registry
- the canary-only regression conditions exist as first-class condition IDs

### Ready at the benchmark layer

- `orchvar_canary`

Meaning:

- repo-local task spec exists
- adapter can load task definitions now

### Still blocked

- `tau_bench`
- `api_bank`
- `mcp_atlas`
- `toolathlon`
- `swe_bench_verified`
- `agent_race`
- `multilingual_fidelity`

These still need real task loaders and evaluation logic.

## Immediate Build Order

### Step 1: Canary Path

Goal: make the regression harness the first fully self-hosted vertical slice.

Deliverables:

- repo-local canary task set
- canary adapter task loading
- degraded English baseline conditions
- experiment config validation

Exit criterion:

- `python3 scripts/validate_experiments.py` passes
- `python -m harness.runner experiments/degradation_canary_01.yaml` reaches task enumeration without schema errors

### Step 2: tau-bench Pilot Path

Goal: make one external benchmark run end-to-end.

Deliverables:

- `tau_bench` task loader
- minimal evaluation wrapper
- trace flush for `pilot_01_tau_bench.yaml`

Exit criterion:

- first 5-task pilot writes traces and summaries without manual repair

### Step 3: Paper 1 Signal

Goal: get the first actual evidence for or against the language thesis.

Deliverables:

- `pilot_02_all_conditions.yaml` results
- message-type decomposition
- initial safety read

Exit criterion:

- one chart answering where token savings arise, if anywhere

### Step 4: Meta Result

Goal: run the first harness-vs-model comparison.

Deliverables:

- naive baselines for old/strong/frontier tiers
- orchestrated runs for old models
- first Pareto comparison

Exit criterion:

- one figure answering whether orchestration closes or beats the generation gap

## Canary Categories in the Repo

The initial repo-local `OrchVar-Canary` task set covers:

- `reasoning_depth`
- `context_recall`
- `verbosity_sensitive`
- `multi_turn_memory`
- `tool_argument_precision`
- `safety_canary`

Location:

- `harness/benchmarks/specs/orchvar_canary_tasks.yaml`

This is intentionally small. It is a seed set for the regression harness, not
the final benchmark.

## What To Build Next

The highest-leverage next code change is still `tau_bench` task loading.
Until one external benchmark runs end-to-end, the rest of the experiment matrix
is a very well-labeled intention.
