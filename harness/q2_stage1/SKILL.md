---
name: harness-q2-stage1-skill
description: Procedure for the Q2 Stage S1a code (q2-stage1-rescoped-v1, draft) in harness/q2_stage1/: the analysis (estimators, records, rules, plan) and the G0 build (episode runner, engine bridge, VM lane, rescoring, comparator, anchor checks, GLMM).
---

# cotcodec / harness / q2_stage1

## Purpose
<!-- agent-docs:fill:purpose -->

`q2-stage1-rescoped-v1` (Stage S1a, a draft registration) measures the
between- and within-session rerun floor and the harness effect of the
certified harness pair on Qwen3.5-4B and 9B. This package is its registered
code: what the analysis computes, how the decision rules read it, how the
caps, constants and orders are derived, and the G0 items that run the
episodes: the episode runner, the engine bridge, the VM lane, offline
rescoring, the corrected comparator, the anchor's CPU checks and the GLMM.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `estimators.py` works on one outcome array `y` of shape
  `(..., Z, K, H, S, R)` (sizes, tasks, harnesses OSW=0 and GA=1, sessions,
  reruns; NaN = missing); leading dimensions are simulation replicates or
  bootstrap resamples, so the simulation and the analysis share the code.
- `records.py` is the episode-record schema the driver must write
  (`q2-stage1a-episode-v1`) and the anchor schema; it builds `y`, keeps
  infrastructure losses apart from agent-caused events (`IRError`, metric
  exceptions), and holds first divergence and uncertified keysym exposure.
- `rules.py` holds DR0-DR5, DR-A and P1-P5 with their frozen thresholds
  (M = 0.13 and 0.18).
- `plan.py` holds the caps and the remainder rule, the K-rule and anchor-size
  rule from A0 records, CPU feasibility, the task draw and every seeded order;
  `scripts/render_q2_stage1_plan.py` writes the plan file from it.
- `analysis.py` is the registered report (`python -m harness.q2_stage1.analysis`).
- G0 build (CPU-tested; nothing here has run a model):
  - `driver.py` runs one episode inside the GPU-less episode container (the
    metric image) in the VM's network namespace: boot wait, OSWorld setup
    (`osworld_live.py`), guard warm-up, settles, 15 turns of a harness client
    (`agents.py`) through the certified IR and `DesktopEnv.step`, the restart
    check, `DesktopEnv.evaluate()` and the capture; `mode: setup-only` is G0
    item 5.
  - `agents.py` holds H-OSW-fixed and H-GA: upstream prompts and layouts,
    checked against `tests/fixtures/q2_stage1/upstream_messages.json`.
  - `engine.py` is the client over the bridge socket; `bridge.py` is the GPU
    job's workload (vLLM plus the socket forwarder, D13); `fake_engine.py`
    stands in for vLLM in tests and the development smoke only.
  - `lane.py` is the VM job's host process (`s1a-vm.sbatch`): manifest rules,
    continuous dispatch, re-queue, stop, fill rule, snapshots, submission.
  - `rescore.py` rescores captured states raw and corrected, merges
    `corrected_score` into records, and validates `zinv.py` on the stored
    checker-mutation confirm campaign.
  - `anchor.py`: public run settings, the evaluator diff, the prompt check
    and the in-container vLLM check. `glmm.py` writes the GLMM input;
    `glmm.R` fits it in `infra/q2-stage1/glmm/`.
  - `design_diffs.md` lists every difference from the upstream harnesses.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never add files under `harness/q2/`: action-path v2 admits an acceptance
  campaign only if every file there is pinned by a frozen table (its design
  decision 35). S1a code lives here.
- The registration's section 20 pins each file's SHA-256;
  `tests/test_q2_stage1_prereg.py` fails on any drift. Refresh the table when
  code changes, before the freeze; after it, a change is a new experiment id.
- Every estimand is conditional on the realized sessions: the bootstrap
  resamples tasks only.
- The base set is the primary analysis set; extension blocks are a secondary.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change an estimator, rule or the plan | Run `uv run pytest -q tests/test_q2_stage1_*.py`, then update section 20 of the registration |
| Re-run operating characteristics | `program/proposals/evidence/2026-10-08-q2-stage1-rescoped/analysis/sim_s1a_v2.py` (sections in parallel, then `merge`) |
| Fill the freeze constants | `scripts/render_q2_stage1_plan.py --constants a0.json --dev-setup dev.json --out plan.json` |
| Run a VM job (dev smoke, setup check, A0, A1) | Write a lane manifest (`experiments/manifests/q2-stage1/`), check `squeue`, then on the host from the exported tree `python3 -E -s -m harness.q2_stage1.lane submit MANIFEST --source-dir .` |
| Rescore captures / validate the comparator | `s1a-cpu.sbatch` run mode, metric image: `python -m harness.q2_stage1.rescore capture|merge|validate-zinv` |
| Change a harness client | Regenerate nothing: `tests/test_q2_stage1_agents.py` must still match the upstream fixture; record any intended difference in `design_diffs.md` |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `pi_share` truncates a negative X at 0 and defines 0/0 as 0, also inside
  bootstrap resamples; the untruncated X is reported beside it.
- The sign-flip tests are the primary X and session tests; the label
  permutations lose their size under a session excess and are sensitivities.
- The K floor is 24 only once D47 is amended (registration section 18, item
  18); pass `k_floor=32` to `freeze_constants` until then.
- The episode runner imports OSWorld (in the metric image) lazily; tests use
  fakes for the guest, the engine and the OSWorld session. AF_UNIX paths must
  stay short (tests use `/tmp`).
- The lane runs under the host's Python 3.10 with the standard library plus
  numpy and PyYAML; keep `lane.py` and what it imports 3.10-compatible.
- `fake_engine.py` is refused for anything but `purpose: development`.
