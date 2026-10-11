---
name: harness-q2-mutation-k2-skill
description: Procedure for the K2 VM-fidelity executor of the checker-mutation study (addendum q2-evaluator-mutation-v1-k2, frozen in ledger row 17) in harness/q2_mutation_k2/.
---

# cotcodec / harness / q2_mutation_k2

## Purpose
<!-- agent-docs:fill:purpose -->

The checker-mutation study (`q2-evaluator-mutation-v1`, frozen) scored every
mutant offline and carries the label "offline harness, VM fidelity unverified"
because its K2 gate had no executor. This package is that executor and its
addendum's code (`program/preregistrations/q2-evaluator-mutation-v1-k2.md`,
frozen in ledger row 17; its registered `k2` job ran once, as Slurm job 1186,
from an export of the freeze commit `7d9c881a`): it injects each sampled candidate into the certified OSWorld VM through
the frozen plan of `harness/q2_mutation/vm_injection.py`, lets the VM's
LibreOffice save it as the pipeline does, scores it with the pinned
`DesktopEnv.evaluate()` and compares the in-VM verdict with the offline one.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `executor.py` runs one run inside the episode container (metric image) in a
  fresh VM's network namespace: S1a's boot wait, setup, warm-up and restart
  checks (`harness/q2_stage1/driver.py`, `osworld_live.py`, unchanged), then
  the plan's ops through `VMOps` (`LiveOps` in the VM; a fake in tests).
- `guest/k2_guest.py` is the guest-side helper (hash, close_app,
  remove_locks, windows, wait_written), shipped through `/execute`.
- `rules.py` classifies runs and pairs (the parent's four causes) and holds the
  fitness gate and outcomes; `report.py` builds `k2-pairs.jsonl`,
  `k2-summary.json` and, for the registered job only, `k2-report.json` (the
  parent analysis's `--k2-report`); `candidates.py` writes the K2-C list.
- `lane.py` is the host side: S1a's `Lane` with K2 slots, manifest rules
  (development on dev-split items before the freeze; only the registered `k2`
  job after it), rendering, host checks and submission through
  `infra/slurm/host-single-node/q2m-k2-vm.sbatch`.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Never edit `harness/q2_mutation/`, `infra/q2-mutation/`, `harness/q2/` or
  `harness/q2_stage1/`: their bytes are frozen by the parent, action-path v2
  and S1a registrations. K2 code lives here.
- Nothing here reads an audit summary, decision, adjudication pool or answer,
  spot check or rater output; `report.check_input` refuses such paths and a
  test scans the imports.
- The addendum's section 2 pins every file here (README and SKILL excepted);
  the addendum is frozen, so any change to them is a new experiment id (the
  registration's section 6 repair rule names `q2-evaluator-mutation-v1-k2-r1`).
- Mutant documents and captures stay on the host; only records (digests,
  verdicts, timings, stdout-stripped replies) are committed.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change executor or rules | `uv run pytest -q tests/test_q2_mutation_k2_*.py`, then refresh the code table |
| Development run (dev split) | On the host from an exported tree: `python3 -E -s -m harness.q2_mutation_k2.lane render --base BASE.json --sample ... --sample-summary .../k2-sample.summary.json --jobs <dev run>/build/scoring-jobs.jsonl --out M.json`, check `squeue`, then `lane submit M.json --source-dir .` |
| Registered `k2` job (after the freeze) | Export the **freeze commit** (the commit that adds only the ledger row), never its parent `git_head_at_freeze`: the lane reads the row from the export's tree. Render from the pinned confirm `scoring-jobs.jsonl` (render refuses another), validate, submit the rendered manifest unedited on an empty queue; the `k2` manifest must name the registered run root, and a second `k2` job under it is refused |
| Report | `python -m harness.q2_mutation_k2.report --run-dir RUN --sample ... --verdicts ... --notes-summary ... --out-dir OUT` (the `k2` job: one run dir, `--repo` a checkout holding the freeze commit, whose `harness/` tree digest must equal the receipt's; the K2-C digest comes from the frozen registration) |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- The lane runs under the host's Python 3.10 with the standard library; keep
  `lane.py` and what it imports 3.10-compatible.
- The plan's `postconfig`, `hash post_postconfig` and `evaluate` ops are one
  pinned `evaluate()` call; `post_postconfig` is the digest of the bytes the
  getters read (no guest call may sit between the save and the read).
- A context file a postconfig `--convert-to` derives is never uploaded.
