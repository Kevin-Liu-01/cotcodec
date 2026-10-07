---
name: harness-q2-mutation-skill
description: Procedure for the Q2 OSWorld checker-mutation harness (q2-evaluator-mutation-v1) in harness/q2_mutation/.
---

# cotcodec / harness / q2_mutation

## Purpose
<!-- agent-docs:fill:purpose -->

q2-evaluator-mutation-v1 measures how often OSWorld-Verified's file-state
checkers reject correct end states and accept wrong ones. Blind requirement
specs label each mutant; operators edit gold files; the VM's own LibreOffice
re-saves every office candidate before the pinned `DesktopEnv.evaluate()`
scores it. Runbook: `README.md` in this directory.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `schema.py` is binding across branches; copy it verbatim, never edit it here.
- `campaign.py` drives a run: `targets` -> `build` -> `reach.sh` -> `merge` ->
  scoring -> `recheck` -> `report` -> `export`; `guard` and `pins` enforce
  the preregistration.
- `reachability.py` is the GUI-faithful save stage; `save_failures` decides
  whether a candidate was really saved, and `step_may_write` which unemulated
  steps exclude a task.
- `controls.py` builds gold and do-nothing jobs and merges saved files;
  `offline_eval.py` scores; `report.py` summarizes control runs (K1, P1).
- `operators/` is the 64-operator catalog with its stdlib snapshot, diff and
  purity oracle; its sources are hashed into `catalog_sha256`.
- `raters.py`, `packets.py` and `stats.py` hold the D9/D23 audit: sample, blind
  packet (built from the operators' snapshot), answer rule, consensus,
  adjudication and the K3 bound; `audit.py` builds samples, packets and the
  summary; `rater_runner.py` makes the model calls (one per rater per item,
  hashed receipts); `analysis.py` is the registered headline.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- An office candidate is scored only after its save wrote every office file;
  otherwise it is an infrastructure exclusion, never a verdict.
- Every exclusion has its own status in `campaign.classify`; nothing is
  relabelled or silently dropped.
- Committed evidence goes through `campaign export` only: recipes can quote
  gold text, mutant files are third-party content and stay on the host.
- Every code change inside the pinned tree moves `code_tree_sha256`; refresh
  the preregistration's pins block (`campaign pins`) and rerun the dev
  campaign before the freeze. README and SKILL files are outside the digest.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change harness, operator or infra code | Run the Q2 tests, then `uv run python -m harness.q2_mutation.campaign pins --root .` and update the pins block. |
| Run on the host | Stage `git archive HEAD` under `src/<sha>`; dev split only before the freeze. |
| Add a release file | Route it through `campaign export` and extend `tests/test_q2_mutation_integration_evidence.py`. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `reachability.py` runs under the LO-VM image's Python 3.10 with the
  standard library only; `uno_apply.py` must stay Python 3.8 compatible.
- A LibreOffice save is not byte-deterministic, so mutant ids change between
  runs while sites, labels and outcomes reproduce.
- The GPU device files on the host are world-writable: every container runs
  without `--gpus` through `q2-mutation-cpu.sbatch`.
