# harness/q2_mutation

Offline harness for the Q2 OSWorld-Verified checker-mutation study
(preregistration draft: `program/preregistrations/q2-evaluator-mutation-v1.md`).
Branches: harness `stage0/q2-mut-harness` (this code), specs
`stage0/q2-mut-specs`, operators `stage0/q2-mut-operators`, integration
`stage0/q2-evaluator-mutation`.

## Modules

| Module | Runs in | Role |
|---|---|---|
| `schema.py` | anywhere (stdlib) | Binding record formats, `q2-mutation-schema-v1`. Other branches copy it verbatim. |
| `tasks.py` | repo venv | Scope (205 offline-checkable, web-free tasks), classification, sanitization, seeded splits |
| `controls.py` | metric image | Gold and do-nothing jobs; merges the save stage's outputs |
| `reachability.py` | LO-VM image (Python 3.10, stdlib) | GUI-faithful LibreOffice save: Xvfb + openbox, the VM's LibreOffice and profile, postconfig replay, pyautogui keys |
| `offline_eval.py` | metric image, per venv | The pinned `DesktopEnv.evaluate()` with a stub VM; fresh processes, repeat scoring, `error` verdicts |
| `stats.py` | anywhere | Task-cluster bootstrap, Wilson, zero-event bounds, MDE, Hajek audit weights, κ |
| `raters.py` | anywhere | D9 model-rater audit: sample, blind packets, consensus, label error |
| `vm_injection.py` | anywhere | Corrected in-VM injection plan for the fidelity gate (executed later on the VM runtime) |
| `report.py` | anywhere | Summary of a control run |

## Images (H100 host, CPU-only, built through `q2-mutation-cpu.sbatch`)

| Image | ID | Contents |
|---|---|---|
| metric | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` | `/opt/venv-lock` (OSWorld uv.lock, Python 3.12.13, pandas 3.0.1) and `/opt/venv-scout` (scoping venv, pandas 2.3.3) |
| LO-VM | `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361` | The VM's own userland (LibreOffice `1:7.3.7-0ubuntu0.22.04.4`, profile, pyautogui) plus xvfb at the VM's X server version and openbox |
| vmprobe | `sha256:0cde2db147f4eefea82b1807ac2f4c4bfc725157eedf2d3e678fd2d3c969a1f9` | qemu-img and debugfs, to read the VM disk without root |

Every input is listed with revision, size, SHA-256 and licence in
`program/evidence/q2-mutation/harness/inputs-manifest.json`.

## Running a control run (dev split only before the freeze)

```bash
# local: commit, then stage the exact tree on the host
SHA=$(git rev-parse HEAD)
git archive --format=tar HEAD | ssh fal-h100-01 \
  "d=~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA; mkdir -p \$d && tar -x -C \$d && echo $SHA > \$d/.git_sha"
# host: three dependent CPU-only Slurm jobs (raw scoring, save, saved scoring)
bash ~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA/infra/q2-mutation/run/submit_controls.sh \
  $SHA dev dev-controls-vN <metric-image-id> <lo-vm-image-id> 16
# then summarize
python -m harness.q2_mutation.report runs/dev-controls-vN --out summary.json
```

`submit_controls.sh` refuses any split other than `dev` unless
`Q2M_PREREG_FROZEN=q2-evaluator-mutation-v1` is set after the freeze.

## Scoring a mutant set (operators branch output)

Write one `ScoreJob` per mutant (JSONL: `mutant_id`, `task_id`, `files` mapping
VM path to a path inside the container), run `reach.sh` in the LO-VM image,
`controls.py merge-lo`, then `score.sh` in the metric image. Office mutants of
the `document_model` stratum always go through the save stage; the
`script_writer` stratum is scored raw with `saved_via: none`.

## Invariants

- No container gets a GPU, a network, or capabilities; the batch script
  refuses to run if `/dev/nvidia*` is visible.
- Nothing from `evaluator`, gold files or this harness's checker-derived
  outputs reaches the blind spec author or the raters.
- Mutant documents stay on the host; only recipes, hashes and verdicts are
  committed.
