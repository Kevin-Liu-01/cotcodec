---
name: cotcodec-skill
description: Repository-wide procedure for CoTCodec research, experiments, evidence, documentation, and release hygiene.
---

# cotcodec — working here

## Purpose
<!-- agent-docs:fill:purpose -->

CoTCodec is a research program and executable evaluation harness for making
agent-orchestration choices explicit, measurable, and optimizable. Paper 1
studies language; the shared harness and evidence ledger cover the broader
orchestration-variable program.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `memory.json` is compiled project state and the active priority ledger.
- `wiki/log.md` is the append-only operational timeline.
- `directions/` owns research hypotheses; `experiments/` owns preregistered runs.
- `harness/` executes conditions and benchmarks; `scripts/` validates and seals.
- `research/evidence/` contains portable decision bundles. Raw/local exhaust
  belongs under ignored `data/`, never in Git by accident.
- `README.md` is the human entry point; `AGENTS.md` is the complete operating
  reference; directory `SKILL.md` files own local procedures.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Read `wiki/SOUL.md`, `wiki/USER.md`, `wiki/HEARTBEAT.md`, and `memory.json`
  before substantive work.
- Preregister falsifiers, budgets, claim boundaries, and stop conditions before
  observing treatment results. Never rewrite a completed experiment contract.
- Preserve negative and pre-result evidence. Create versioned reruns instead of
  overwriting failed output directories.
- Separate deterministic infrastructure admission from live-model or scientific
  claims. CPU conformance never implies H100 admission or memory quality.
- Bind source revision, tree, license, dependencies, image/model identity, and
  execution hashes for any result used in a research decision.
- Keep `memory.json` compiled truth and `wiki/log.md` timeline synchronized.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Continue research | Read `memory.json` priorities and the latest `wiki/log.md` entry. |
| Run an experiment | Read `skills/run-experiment.md`, then its YAML contract. |
| Add a benchmark | Read `harness/benchmarks/SKILL.md` and the base adapter. |
| Change orchestration logic | Read the nearest `harness/**/SKILL.md` and paired tests. |
| Add a memory system | Read `infra/memory-baselines/SKILL.md` and portfolio/source validators. |
| Ship evidence | Run the source, experiment, evidence, and portfolio validators that route the artifact. |
| Update docs | Refresh Agent-Docs, README/current-state pages, `memory.json`, and `wiki/log.md`. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- Many benchmark adapters are intentionally stubs; presence is not readiness.
- `data/` can contain multi-gigabyte models, databases, source trees, and Docker
  artifacts. Inspect ignored/untracked files before staging.
- Exact-source lifecycle jobs often use CPU allocations on GPU hosts. A host name
  containing `h100` does not prove that a GPU was requested or used.
- The historical `~/Documents/GitHub/kevin-wiki` path may be absent locally;
  set `KEVIN_WIKI_ROOT` for `scripts/run-agent-docs.ts` when needed.
