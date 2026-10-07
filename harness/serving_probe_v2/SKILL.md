---
name: harness-serving-probe-v2-skill
description: Procedure for the vLLM serving-throughput probe v2 core (serving-throughput-probe-v2) in harness/serving_probe_v2/.
---

# cotcodec / harness / serving_probe_v2

## Purpose
<!-- agent-docs:fill:purpose -->

serving-throughput-probe-v2 re-measures the Q2 serving cells that
serving-throughput-probe-v1 did not deliver or invalidated, under a corrected
contamination rule, a launch-window ledger and a like-for-like control X1.
`scripts/run_vllm_throughput_probe_v2.py` owns engines, gates and persistence
by subclassing v1's runner.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `config.py` loads `experiments/serving/serving-throughput-probe-v2.yaml`
  with v1's validators plus v2's rules: required and optional points, the
  warm-up that must dominate every later point, the launch window's static fit.
- `contamination.py`: the compute-process poller, G0.8's empty-GPU condition,
  the G0.9 reservation (pid or device mode) and the per-point checks.
- `schedule.py`: the launch-window ledger (required time reserved; reruns and
  optional points from slack only).
- `client.py` and `requests.py`: prompt-token-id digests and prebuilt replay
  history, so two engines send identical token sequences.
- `x1.py`: dummy-weight admissibility on identical prompts.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- The v1 package and driver are frozen with serving-throughput-probe-v1 and are
  imported, never edited; v2's digest covers them too.
- A PID in the engine's tree is the engine's; other PIDs count as the engine's
  only when they appeared on a GPU that was empty at G0.8, before G0.9.
- A rerun never takes reserved time: it runs after every required first
  attempt of its phase, and only from slack.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change a point, threshold or any probe code | Before freezing: rerun `run_vllm_throughput_probe_v2.py digest` and update the registration's two hash lines. After: a new experiment id. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- NVML inside a container reports host-namespace PIDs that `/proc` there
  cannot resolve; the reservation step records which attribution applied.
