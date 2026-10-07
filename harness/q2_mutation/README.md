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
| `operators/` | LO-VM image (planning, UNO application) and anywhere (snapshots, purity) | The 64-operator catalog (`q2-mut-operators-v1`), spec binding and witness rules, `uno_apply.py`, the stdlib purity oracle |
| `campaign.py` | metric image, LO-VM image, anywhere (per subcommand) | Joins blind specs, operators and the scorer: `targets`, `build`, `merge`, `recheck`, `report`, `export`, `pins` |

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

## A mutation run (spec -> operator -> mutant -> save -> verdict)

`infra/q2-mutation/run/submit_mutants.sh` submits three dependent CPU-only
Slurm jobs through `q2-mutation-cpu.sbatch`:

1. metric image: control jobs for the split (`make_jobs.sh`), then
   `campaign targets`: every gold file an operator family can mutate (office
   OOXML, text and config files that no postconfig conversion derives), with
   the task's other gold files as context; the blind specs are validated and
   copied to JSON.
2. LO-VM image: `campaign build` saves the gold (base), the initial file and
   the null mutant (base saved once more) with `uno_apply.py`, plans every
   operator of the family from the blind spec only, applies the recipes,
   checks purity against the null mutant and dedupes; then `reach.sh` runs the
   GUI-faithful save stage on every admitted mutant and one null job per
   target.
3. metric image: `campaign merge` (MutationResult ids kept), `score.sh` under
   both venvs (VerdictRow JSONL), `campaign recheck` (operator purity on the
   saved mutant against the saved null mutant) and `campaign report`.

```bash
bash ~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA/infra/q2-mutation/run/submit_mutants.sh \
  $SHA dev dev-mutants-vN <metric-image-id> <lo-vm-image-id> 16
# locally, after copying the run's prep/, build/ and score/ JSON files:
uv run python -m harness.q2_mutation.campaign export --run <run copy> \
  --out program/evidence/q2-mutation/integration/dev-mutants-vN
```

Outcome per mutant and venv (`campaign.classify`): `not_admitted`,
`not_scored`, `normalized` (the edit did not survive the save),
`null_not_pass` (the saved null mutant of the target does not pass, so no
label can be read), `error`, `nondeterministic`, `ambiguous`, or `evaluable`
with event `FN` / `FN_alt` / `FP_R` / `FP_F` or `ok`. Cells a scoping probe
touched (`PROBE_OPERATOR_MAP`) are kept out of the rate tables.

Every split but `dev` is refused unless the staged tree carries the frozen
ledger row of `q2-evaluator-mutation-v1`, `Q2M_PREREG_FROZEN` is set, and the
tree's digests equal the preregistration's `q2m_pins` block
(`campaign pins` prints them). `submit_target_counts.sh` only counts targets
per split (no spec, mutant or checker) and runs for every split.

The controls-only path is still available: `controls.py mutation-jobs`
builds scoring jobs from any `MutationResult` JSONL whose files follow
`<files_root>/<mutant_id>/<VM path without the leading slash>`.

Released evidence (`campaign export`) carries redacted recipes: free text of
32 characters or more in a recipe (a `must_equal` value holds a whole gold
paragraph) is replaced by its SHA-256 and length, and purity details are
dropped. Mutant documents and full recipes stay on the host.

## Invariants

- No container gets a GPU, a network, or capabilities; the batch script
  refuses to run if `/dev/nvidia*` is visible.
- Nothing from `evaluator`, gold files or this harness's checker-derived
  outputs reaches the blind spec author or the raters.
- Mutant documents and full recipes stay on the host; only redacted recipes,
  hashes, outcomes and verdicts are committed.
- Operators read only the blind spec, the LibreOffice-saved gold and the
  LibreOffice-saved initial file: `campaign build` gets no task config, no
  checker and no verdict.
