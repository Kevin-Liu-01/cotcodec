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
  - `lane.py` is the VM job's host process (`s1a-vm.sbatch`): manifest rules
    (registered jobs' slots must be the plan's), continuous dispatch, re-queue, stop,
    fill rule, snapshots, submission. `scripts/render_q2_stage1_manifest.py` renders a
    registered job's manifest from the plan, and the GPU half from its template.
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
| Fill the freeze constants | On the host, `scripts/render_q2_stage1_plan.py --a0a-run-dir <A0a lane run> --a0a-bridge-dir <its GPU job's bridge dir> --n-star N --action-path-step-p95 <accepted attempt's step_p95_n1_s> --out plan.json` (it calls `plan.a0a_measurements`: nothing is typed; `python3 -m harness.q2_stage1.plan a0a-measurements` prints the same inputs) |
| Run a VM job (dev smoke, setup check, A0, A1) | A0a and A1: render the lane manifest from the plan (`scripts/render_q2_stage1_manifest.py vm --purpose a0a --n-star N`, or `--purpose a1 --plan <frozen plan> --size Z --session S --prior-run-dirs <every earlier A1 job's run dir>`), then the GPU half from it (`... gpu --vm-manifest <VM manifest> --vm-job-id ID --values V`); the lane refuses slots that differ, an earlier A1 job that fired DR0, an S2 job before the 12 h gap, and a GPU job whose engine argv or Slurm limit is not the registered one. Development and setup checks: write it by hand (`experiments/manifests/q2-stage1/`). Check `squeue`, then on the host from the exported tree `python3 -E -s -m harness.q2_stage1.lane submit MANIFEST --source-dir .`; a registered job takes exactly `plan.vm_job_cpus(V)` CPUs, and a temporary host-load cap (`--host-load-max-cpus 8`) is for development and setup-check jobs only |
| Judge an A1 job (DR0) | `python3 -m harness.q2_stage1.rules dr0 --run-dir <its lane run dir> --plan <frozen plan>` (exit 3: DR0 fired, no further job starts) |
| Cost card (DR4, P5) | `python3 -m harness.q2_stage1.analysis costs --run-dir <A1 run dir> [...] --out costs.json` (the GPU job's Slurm EndTime minus StartTime as the VM lane recorded them, over the episodes that ran to an end; accounting is off on the host) |
| Rescore captures / validate the comparator | `s1a-cpu.sbatch` run mode, metric image: `python -m harness.q2_stage1.rescore capture|merge|validate-zinv` |
| Change a harness client | Regenerate nothing: `tests/test_q2_stage1_agents.py` must still match the upstream fixture; record any intended difference in `design_diffs.md` |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `pi_share` truncates a negative X at 0 and defines 0/0 as 0, also inside
  bootstrap resamples; the untruncated X is reported beside it.
- The sign-flip tests are the primary X and session tests; the label
  permutations lose their size under a session excess and are sensitivities.
- The K floor follows the anchor branch (section 6.2; D47, D49 (i)): 32 when the
  anchor does not run, whatever is passed; 24 only when it runs and `k_floor=24` is
  passed after item 18 is signed. `freeze_constants` defaults to 32.
- The episode runner imports OSWorld (in the metric image) lazily; tests use
  fakes for the guest, the engine and the OSWorld session. AF_UNIX paths must
  stay short (tests use `/tmp`).
- The lane runs under the host's Python 3.10 with the standard library plus
  numpy and PyYAML; keep `lane.py` and what it imports 3.10-compatible.
- `fake_engine.py` is refused for anything but `purpose: development`.
- The offline-setup exclusion (`plan.offline_exclusions`, registration section 5.4) is
  applied once from G0 item 5's second-pass records; `plan.OFFLINE_EXCLUDED` holds it and
  the draw runs on `plan.eligible_pool`. A failed setup reply (not 200, or a non-zero
  `returncode`) is a `task_setup` loss; a failed postconfig reply is recorded only.
