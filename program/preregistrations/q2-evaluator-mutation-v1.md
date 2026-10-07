# q2-evaluator-mutation-v1: OSWorld-Verified checker mutation audit

**Status: DRAFT for the second review, not frozen.** Every pin below is
filled from the integration branch `stage0/q2-evaluator-mutation`, and no
value is left open. This draft answers the first adversarial review
(2026-10-07): save failures are excluded, the control path is guarded, the
audit packet and the K3 bound are rebuilt, K6 and P1 are restated against the
pre-freeze evidence, and the power of P3 and P4 is recomputed with the probe
exclusion (sections 4-10, 12, 14-16). After the review, freeze with

```bash
uv run python scripts/preregister.py freeze q2-evaluator-mutation-v1 \
  program/preregistrations/q2-evaluator-mutation-v1.md
uv run python scripts/preregister.py verify q2-evaluator-mutation-v1
```

and commit the ledger. The ledger's `git_head_at_freeze` is the harness
commit. No confirmatory mutant is planned, built or scored before the freeze.
Development-split runs (harness validation, the gold fixed point on dev tasks,
the end-to-end campaign on dev tasks) are allowed and are reported as
exploratory.

## 1. Question

How often do OSWorld-Verified's file-state checkers (a) reject end states that
satisfy the task instruction (false negatives) and (b) accept end states that
violate it (false positives), when every office end state reaches the checker
the way it does in the real pipeline, re-saved by the VM's own LibreOffice?

Scope: the 205 offline-checkable, web-free tasks of OSWorld-Verified
(`test_nogdrive.json`, 361 tasks). Classes 1A/1B/1V/1C; live-state (class 2),
web and infeasible tasks are out of scope.

## 2. Identity and pins

| Object | Pin |
|---|---|
| OSWorld | `b138d348256078fa634fc3b73567a7337c793e6b`; evaluators and tasks last changed in `0514b9a262c5e49007a5724e3e6c84171566ae66` (Apache-2.0) |
| File cache | HF `xlangai/ubuntu_osworld_file_cache` at `1e112283c4ecb08d6fed8069bca7de74fa2f12aa`; 447 files fetched, every LFS file verified against its oid (apache-2.0 card; third-party document content) |
| VM image | HF `xlangai/ubuntu_osworld` at `a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133`; `Ubuntu.qcow2.zip` 12,273,896,463 B, SHA-256 `b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712`; extracted `Ubuntu.qcow2` SHA-256 `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313` |
| LibreOffice | the VM's own Ubuntu build, `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, "LibreOffice 7.3.7.2 30(Build:2)" (not TDF's build). The LO-VM image runs the VM's extracted `/usr`, `/etc`, dpkg database, LibreOffice profile and the user's site-packages with PyAutoGUI 0.9.54 (205,028 files, tree SHA-256 `fceee6501ff0d1f1a33500b36663624c220f1598140fa271040b5e97a9de30bf`) plus xvfb `2:21.1.4-2ubuntu1.7~22.04.8` (the VM's X server version, deb SHA-256 `f8c64bc652e3dc1a1041e85025267f574c27f86b00d7965545a8b3ec41a60cd4`) and openbox 3.6.1-10; no VM package changes; one passwd entry for the runtime uid |
| LO-VM image | `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`, used for the base, initial and null-mutant saves, operator application (`uno_apply.py`) and the GUI-faithful save stage. The operators' own validation (Slurm 431-433) used the earlier build `sha256:894b2623dceb43e8468a2adbd6e03a532ea9683d4b7754cd79fa0d58a331f909` of the same LibreOffice package from the first VM userland extraction; the integration runs used `f5b4c40e` |
| LibreOffice profile | the VM's `registrymodifications.xcu` (SHA-256 `6b5ec88d1570a8ad85932eb53a1a6f8370053d3ac60b30fe759c14135e902ef2`): `WarnAlienFormat=false`, `ShowTipOfTheDay=false`, Writer default filter "MS Word 2007 XML" |
| Metric image | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (ubuntu:22.04 `sha256:5ec03bb3…6401`, Python 3.12.13, uv 0.11.30) |
| Lock-exact venv (primary) | OSWorld `uv.lock` exported for Python 3.12 with hashes, agp-client left out; requirements SHA-256 `3f463d6f3331a80c3054dfd8aced1dabb56adf8ee8b6fa7441e25435f626c2a3`; installed-RECORD fingerprint `f2c9e208d2bdb888668e64143f0603ce92f56cee2fd1002f0211d2c2287db810`; pandas 3.0.1, numpy 1.26.4, python-pptx 1.0.2, python-docx 1.2.0, openpyxl 3.1.5, torch 2.5.1 |
| Scoping venv (sensitivity) | the scoping agent's 129 package versions (pandas 2.3.3, torch 2.5.1+cpu); requirements SHA-256 `5ae07a7a527c22ff580a171692ccbc608f563e6c7264b0819a92ff1c41bd6fb7`; fingerprint `e591c8875c353ecbf6ec38b6c9c467e01b4164cc129744bd51e27c993310417a`. It is not the leaderboard-era set the reviewed plan asked for (section 14): it shares numpy, openpyxl, python-docx, python-pptx, lxml, PyMuPDF, RapidFuzz, scikit-image, formulas and borb with the lock-exact venv and differs in 63 of the 125 shared packages, among them pandas (3.0.1 vs 2.3.3), opencv-python-headless (4.11.0.86 vs 4.8.1.78), chardet (6.0.0.post1 vs 7.6.0) and beautifulsoup4 (4.14.3 vs 4.15.0) |
| Task export | `program/evidence/q2-mutation/sanitized-tasks.manifest.json` (205 tasks), SHA-256 in the pins block |
| Splits | `program/evidence/q2-mutation/splits.json`, seed 42, stratified by domain × task class: dev 32, confirm 120, reserve 53 |
| Requirement specs | `program/evidence/q2-mutation/specs/` from `stage0/q2-mut-specs` at `287d523374354e40af4c1f54bd06e46c3de6a955`: 205 YAML specs, 598 requirements, author `blind-model-author-v1`. Set SHA-256 = SHA-256 of the sorted lines `{file sha256}  {file name}` (`campaign.spec_set_sha256`). Blindness check: `program/evidence/q2-mutation/integration/blind-spec-provenance.json` |
| Operator catalog | `q2-mut-operators-v1`, `catalog_sha256` (hash over the operator descriptions and the sources of `harness/q2_mutation/operators/`), 64 operators listed in Appendix A; validated at `7c429bcb793369649bc7970ccad0fba290ad2772`, merged unchanged from `stage0/q2-mut-operators` at `0d7f0857cc0a6d0007466a05ee08a44a467cf957` |
| Harness and campaign code | code-tree SHA-256 over every file of `harness/q2_mutation/` (README and SKILL files excepted), `infra/q2-mutation/`, `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`, `scripts/q2_mutation_export_tasks.py` and `scripts/q2_mutation_operators.py` (`campaign.code_tree_sha256`); schema `q2-mutation-schema-v1`; operator snapshot version 2 (pptx slide backgrounds, shape outlines and text-body properties added after the review) |
| Mounted inputs | `osworld_tree_sha256` over `desktop_env/` and `evaluation_examples/` of the host's clean checkout at `b138d348` (git status clean, 537 files); `vm_baseline_tree_sha256` over the 75 VM config-baseline files; every file-cache file re-hashed against `program/evidence/q2-mutation/harness/file-cache-receipts.tsv` (447 files, its SHA-256 pinned); the probe map input `probe_touched.json` (SHA-256 pinned) |

Machine-readable pins. Before any job is submitted, `check_frozen.py` on the
host refuses a staged tree whose `.git_sha` is not the submitted commit, and,
for every split but `dev`, a tree without this file's frozen ledger row (hash
chain checked), without `Q2M_PREREG_FROZEN`, or with image IDs or an
application mode other than below. Inside the containers, `campaign guard`
(jobs 1 and 3 of both the control and the mutation runs) and `campaign
targets` refuse every split but `dev` unless the same holds and `campaign
pins` on the staged tree equals the digests below; for every split, `guard`
also refuses mounted inputs whose OSWorld tree, VM baseline or file cache
differ from the pins:

```json
{
 "q2m_pins": 1,
 "experiment_id": "q2-evaluator-mutation-v1",
 "code_tree_sha256": "4d08c7a2b49d5f8282b37b6f168855adf0ecb70e0a0cdbe60fc494b4b47e7551",
 "operator_catalog_sha256": "7f6d44f5cc848188bc7f6c5bd4d98846505f9a97a10d8ed75510155758fbb46a",
 "operator_catalog_version": "q2-mut-operators-v1",
 "operators": 64,
 "spec_set_sha256": "05d4fb2074a7fa53046dff9f5d075b2b45ac014889eaae23d625c1894056de62",
 "specs": 205,
 "sanitized_manifest_sha256": "40ef4a459086b86f4971d3f938402df6c2749bd16a2acc2822f25261ebc70380",
 "splits_sha256": "2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9",
 "schema_sha256": "65d91703754b4026b15f6c53a4a6069da723b58d749730770da2910c1edf427d",
 "probe_touched_sha256": "4115740770f6fa88c03742f455f7c9b373d73fe0424ae16540461d12860fa929",
 "file_cache_receipts_sha256": "9a3e06a48afe95c2286d0fa26d56edf947e1a5e0f121d414d565b58d30abe5fb",
 "osworld_tree_sha256": "4153c68678fedd44a285800b45f4b7e538336a044f614f748f432a7ce5246076",
 "vm_baseline_tree_sha256": "f32538182c72aa44ca348a42fcc1c04a1faf35b2c18a8f76d8af1d3bfafcb1df",
 "metric_image_id": "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230",
 "lo_vm_image_id": "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361",
 "apply_to": "gold",
 "mutation_split": "confirm",
 "seeds": [
  42,
  43,
  44
 ],
 "specs_branch_commit": "287d523374354e40af4c1f54bd06e46c3de6a955",
 "operators_branch_commit": "0d7f0857cc0a6d0007466a05ee08a44a467cf957",
 "harness_branch_commit": "65c90aae12c042f010856c589f145647f1733c0d"
}
```

Licences of runtime packages that are run but never vendored: PyMuPDF 1.27.1
(AGPL-3.0 or commercial), borb 2.1.25 (AGPL-3.0-or-later or commercial),
mutagen 1.47.0 (GPL-2.0+), formulas 1.3.3 (EUPL-1.1+). Mutant documents and
full recipes are never released; redacted recipes, verdicts and outcome rows
are (section 16).

## 3. Design

**Candidates.** Each candidate is a set of end-state files for one task. Kinds:
the task's gold (where every metric pairs a `vm_file` result with a
`cloud_file` gold that is not one of the task's own inputs), do-nothing (the
initial state), operator mutants (`MutationResult`, schema v1) and one null
mutant per mutation target.

**Mutation targets.** A target is one gold file of a confirm task with a
complete gold whose type an operator family handles (`.xlsx`, `.docx`,
`.pptx`; text and config files such as `.txt`, `.csv`, `.json`, `.ini`) and
which no postconfig conversion derives (`campaign.select_targets`). The
task's other gold files are the target's context and are placed unchanged
with every mutant. Tasks without a complete gold, LibreOffice-native files
(`.odt`, `.ods`), media, images and archives have no target and are listed.

**Mutant pipeline** (`infra/q2-mutation/run/submit_mutants.sh`, three
CPU-only Slurm jobs; `harness/q2_mutation/campaign.py`):

1. `targets` (metric image): control jobs, targets, blind specs to JSON.
2. `build` (LO-VM image): the base (LibreOffice-save of the gold through
   `uno_apply.py`, `.uno:Save` on the document frame under Xvfb with the VM
   profile) and the LibreOffice-saved initial file; planning of every operator
   of the target's family from the blind spec, the base and the task delta
   (base vs saved initial) only; each office recipe applied to the raw gold
   and saved once (`--apply-to gold`), so a mutant and its null mutant (the
   base) are each one LibreOffice round trip from the gold; text and config
   recipes splice characters of the gold; purity checks against the null
   mutant; deduplication by snapshot digest within a (task, operator) cell.
3. The GUI-faithful save stage (`reach.sh`) on every admitted mutant and null
   mutant, then `merge`, scoring under both venvs (`score.sh`, two fresh
   processes each), `recheck` (purity re-run on the saved mutant against the
   saved null mutant) and `report`.

The operators never read a task config, a checker or a verdict.

**Labels.** Fixed at planning time from the blind requirement spec, never
from a checker, by the witness rules W-E, W-A, W-R and W-F (Appendix A):
`should_pass_equiv`, `should_pass_alt_solution`, `should_fail_violation`
(witness names at least one `req_id` with a high or medium binding that pins
the edited aspect), `should_fail_extra_change`, `ambiguous`. Spec entries
marked `[AMBIGUOUS]` are questions, not freedoms.

**Strata.** All 64 operators are in the `document_model` stratum (edits made
through LibreOffice's document model, or character splices of text files);
it is the headline. A `script_writer` stratum (byte-level edits LibreOffice
normalizes on load) would be reported separately and never pooled; the
frozen catalog has no such operator.

**Reachability stage (GUI-faithful save).** Every office candidate is placed
at its VM path in a fresh copy of the VM profile, opened by non-headless
LibreOffice under Xvfb before any postconfig step, and the task's postconfig
is replayed step by step: `wmctrl -Fa` activation, keystrokes through the VM's
pyautogui, sleeps, and `libreoffice --convert-to` with its exact filter
string. Tasks without a postconfig save get one agent-equivalent save
(open, activate, Ctrl+S) per OOXML/ODF candidate. File-only postconfig steps
(downloads, `diff`/`ls` captured to the cache directory) run after the saves.
Every save records whether the file changed, its write time and any dialog.
A candidate counts as saved only if every office file it places has a save
event that wrote it, no save timed out, no open or activation failed and every
postconfig conversion of a placed file produced its output
(`reachability.save_failures`); otherwise the candidate is excluded at
`merge` as `save_failed` (section 8) and is never scored on its pre-save
bytes.

**Scoring.** The unmodified pinned `DesktopEnv.evaluate()` with a stubbed VM:
one non-FAIL action, the offline file-cache shim for `get_cloud_file` (other
URLs refused), live getters refused. Each candidate is scored in fresh
processes twice (`score.sh`, `--repeat 2`); a candidate whose two scorings
disagree is `nondeterministic` (S5) and leaves P2-P5. Every candidate whose
verdicts differ between the venvs is rescored five times in fresh processes
in each venv after the run (`offline_eval --repeat 5`) before it counts for
S1.

**Verdicts.** `pass` iff score == 1.0; `fail` otherwise; `error` iff
`evaluate()` raised (OSWorld's `run.py` logs and skips such a task, so an
error is neither pass nor fail). Credit (raw score) is kept for
leaderboard-impact statements.

**Dependency sets.** Primary: lock-exact venv. Sensitivity: scoping venv,
which measures sensitivity to the package differences listed in section 2
only, not to the dependency versions in use when the leaderboard results were
produced (section 14).

## 4. Primary metrics (lock-exact venv, document_model stratum, confirm split)

The mutation metrics P2-P5 are computed on evaluable mutants (section 7):
admitted, the targeted edit survives the save stage, the target's saved null
mutant passes, the verdict is not `error`, the candidate's scorings agree,
and the (task, operator) cell was not touched by a scoping probe (section 12).

- **P1 Gold fixed-point false negative.** Unit: task. Population: non-dev
  in-scope tasks with a complete gold (confirm and reserve splits; 109 tasks:
  77 confirm, 32 reserve). Event: the raw gold passes and
  LibreOffice-save(gold) through the reachability stage does not. A gold
  counts only if its save wrote every office file and neither scoring timed
  out; the others are listed. Every flip goes to the audit; a flip is a
  confirmed false negative when the audit accepts the saved gold as a correct
  result. Reported: raw flip share and audit-confirmed share with exact
  Clopper-Pearson 95% intervals (`stats.clopper_pearson`). The headless
  scoping round trip already saved 93 of the 109 golds (a different save path
  and build) and flipped 7 of 63 gold-passing confirm golds and 1 of 26
  reserve golds. P1 is therefore reported in two parts: on those 93 tasks it
  is a pre-specified replication of that measurement under the GUI-faithful
  save (not a confirmatory test); on the 16 golds the probe never saved (10
  confirm, 6 reserve) it is confirmatory, but with 16 tasks even zero flips
  leave a Clopper-Pearson 95% interval of 0-20.6%.
- **P2 FN per checker family.** Share of evaluable should-pass mutants
  (`should_pass_equiv` plus audit-accepted `should_pass_alt_solution`) whose
  verdict is not pass.
- **P3 FP_R, pooled over checker families.** Share of evaluable
  `should_fail_violation` mutants whose verdict is pass. Per-family rates are
  descriptive (section 6).
- **P4 FP_F, pooled over checker families.** Share of evaluable
  `should_fail_extra_change` mutants whose verdict is pass, counted only where
  the audit rejects the file. Always reported separately from P3. Per-family
  rates are descriptive (section 6).
- **P5 Task-level escape rate.** Share of evaluable confirm tasks (at least
  one evaluable `should_pass_equiv` or `should_fail_violation` mutant) with at
  least one FN or FP_R event.

A checker family is the set of distinct metric functions of a task, joined by
`+` when there are several (`campaign.checker_family`); `compare_table` rule
types and `compare_pptx_files` facets are descriptive sub-families. Family
rates are the unweighted mean over tasks of per-task rates (tasks weighted
equally; at most three mutants per task and operator, site seeds 42, 43, 44).

## 5. Secondary metrics

- S1 Dependency flips: candidates whose verdict differs between the two venvs,
  counted only when each venv gives the same verdict on five fresh-process
  scorings. Its scope is the package differences of section 2 (pandas 3.0.1
  vs 2.3.3, opencv-python-headless, chardet, beautifulsoup4 and 59 others);
  it is not a measurement of leaderboard-era drift.
- S2 Script-writer stratum rates (P2-P4 on that stratum; empty for this
  catalog).
- S3 Reachability normalization per operator: share of admitted mutants whose
  targeted edit is absent after the save (operator purity re-run on the saved
  file against the saved null mutant).
- S4 Save timing: share of postconfig saves whose write took longer than the
  0.5 s the VM waits before reading the file.
- S5 Nondeterministic checkers: candidates whose repeated scorings disagree.
- S6 Audit agreement with the a-priori labels, per label class.
- S7 Null-mutant failures: share of targets whose saved null mutant does not
  pass, with the target list (their mutants are excluded from P2-P5).

## 6. Task subset, sample sizes and minimum detectable effects

Counted before the freeze without specs, mutants or checkers
(`submit_target_counts.sh`, Slurm 457, `program/evidence/q2-mutation/integration/target-counts-v1.json`):

| Split | Tasks | Tasks with a target | Targets (xlsx / pptx / docx / text) | No complete gold | Other files skipped |
|---|---:|---:|---|---:|---|
| dev | 32 | 17 | 17 (7 / 5 / 4 / 1) | 13 | 3 no operator family, 1 derived |
| confirm | 120 | 67 | 68 (32 / 22 / 13 / 1) | 43 | 11 no operator family, 5 derived |
| reserve | 53 | 28 | 28 (12 / 8 / 5 / 3) | 21 | 7 no operator family |

- Mutation population: the 67 confirm tasks with a target. The 43 confirm
  tasks without a complete gold get no mutant; they need constructed,
  spec-based positive controls, which are out of this experiment.
- Planned mutants: the dev campaign planned 275 mutants on 17
  targets (16.2 per target) and admitted 271, so the confirm split is
  expected to yield about 1,100 planned and 1,080 admitted mutants (68
  targets), of which the dev run made 78% evaluable.
- Pooled and family rates: task-cluster percentile bootstrap, 10,000
  resamples, seed 42 (`harness/q2_mutation/stats.py`). Wilson or exact
  intervals only for task-level proportions.
- Family floor: a family rate is inferential only with at least 8 evaluable
  tasks and 20 evaluable mutants; otherwise descriptive. The target counts
  bound the families at 32 tasks (`compare_table`, the xlsx targets), 22
  (`compare_pptx_files` and its variants) and 13 (all docx checkers
  together). No inferential claim is made at the operator × checker cell
  level.
- The probe exclusion (section 12) removes whole label classes from
  probe-touched tasks. Counted before the freeze from task configs and
  `probe_touched.json` only: of the 67 confirm target tasks, 11 have
  violation cells untouched by a probe (5 docx, 4 pptx, 2 xlsx) and 19 have
  extra-change cells untouched (10 xlsx, 5 docx, 4 pptx, 1 text);
  equivalence and alternative-solution cells are untouched except
  `*.eq.doc_property`. On dev the same counts were 6 and 7 of 17, and
  `dev-mutants-v4` made evaluable 5 of the 6 violation-untouched tasks
  (26 mutants) and 2 of the 7 extra-untouched tasks (6 mutants).
- Expected evaluable confirm tasks per label class, outside probe-touched
  cells, from the dev ratios, and the minimum detectable pooled rate
  (one-sided α = 0.05, power 0.8, null rate 5%) and zero-event exact
  one-sided 95% upper bound at that size:

  | Label class (metric) | Expected tasks | Mutants per task (dev) | ICC assumed | MDR | Zero-event bound |
  |---|---:|---:|---:|---:|---:|
  | `should_pass_equiv` (P2) | 59 | 4.0 | 0.5 | 11.5% | 4.95% |
  | `should_pass_alt_solution` (FN_alt, P2 after audit) | 20 | 5.6 | 0.5 | 16.5% | 13.9% |
  | `should_fail_violation` (P3) | 9 | 5.2 | 0.5 | 23.4% | 28.3% |
  | `should_fail_extra_change` (P4) | 5 | 3.0 | 1.0 | 39.4% | 45.1% |

  P3 and P4 are therefore inferential only as pooled rates over all
  checker families, and only for large effects; no family-level P3 or P4
  inference is possible (each family is below the 8-task floor), and K7 cannot
  fire for them. The probe-touched violation and extra-change cells are still
  built, scored and reported as exploratory, family by family. Adding the
  reserve split's 28 targets would raise the expected P3 and P4 sizes to
  about 14 and 8 tasks (MDR 19.2% and 31.5%); it is not part of this
  registration.
- Intra-task correlation measured on the dev campaign (exploratory, one-way
  ANOVA estimator over evaluable mutants outside probe-touched cells, lock
  venv, `dev-mutants-v4`): FN 0.28, FP_R 0.13; FP_F and FN_alt undefined
  (no event outside probe cells). With 15 dev tasks these estimates are
  imprecise; the design uses the larger of the dev estimate and 0.5 for FN
  and FP_R, and 1.0 for FP_F.
- Minimum detectable rate (one-sided α = 0.05, power 0.8, null rate 5%):

  | Evaluable tasks | ICC 0.13 / 0.31 / 0.5 / 1.0, 3 mutants per task | ICC 0.13 / 0.31 / 0.5, 6 mutants per task |
  |---:|---|---|
  | 67 | 9.8% / 10.5% / 11.2% / 12.8% | 8.8% / 9.9% / 10.8% |
  | 59 | 10.2% / 11.0% / 11.7% / 13.4% | 9.1% / 10.2% / 11.2% |
  | 32 | 12.3% / 13.4% / 14.4% / 16.9% | 10.7% / 12.3% / 13.8% |
  | 22 | 14.0% / 15.4% / 16.7% / 19.8% | 12.1% / 14.1% / 15.8% |
  | 13 | 17.1% / 19.0% / 20.9% / 25.1% | 14.5% / 17.2% / 19.7% |

- Exact one-sided 95% upper bound with zero events: 4.4% at 67 tasks, 4.95%
  at 59, 8.9% at 32, 12.7% at 22, 20.6% at 13, 28.3% at 9, 45.1% at 5. With
  one event at 67 tasks the bound exceeds 5%.

## 7. Admission, evaluability and quarantine

Per mutant and venv, `campaign.classify` assigns exactly one status, the
first that applies in this order:

| Status | Rule | In P2-P5 |
|---|---|---|
| `not_admitted` | a build-time purity check failed (`applied`, `survived_save`, `edit_landed`, `no_collateral_change`, and the declared `forbidden_kinds_absent`, `observable_preserved`, `appearance_preserved`, `same_items`, `expected_values`, `expected_deltas`, `expected_formulas`), or a duplicate | no, counted per operator and check |
| `save_failed` | the GUI-faithful save of the mutant or of its null mutant did not write every office file (section 8), or an office candidate reached the scorer unsaved | no, infrastructure |
| `unemulated` | the task has a setup or postconfig step the harness cannot replay that may write a file the checker reads (section 8) | no, infrastructure; tasks listed |
| `not_scored` | no verdict row or no post-save purity row | no, counted as infrastructure |
| `normalized` | post-save purity against the saved null mutant fails (the edit did not survive the save stage) | no, S3 |
| `infra_timeout` | the mutant's or its null mutant's scoring exceeded 300 s on every attempt (one try and two retries) | no, infrastructure |
| `null_not_pass` | the target's saved null mutant does not pass under this venv | no, S7 |
| `error` | `evaluate()` raised | no, counted per checker |
| `nondeterministic` | the mutant's or its null mutant's repeated scorings disagree | no, S5 |
| `ambiguous` | label `ambiguous` | no, counted per witness rule and verdict |
| `evaluable` | all of the above clear | yes: event FN, FN_alt, FP_R or FP_F when the verdict disagrees with the label, otherwise `ok` |

- `should_pass_alt_solution` enters P2 only after audit acceptance; before
  the audit its events are reported as `FN_alt`.
- `should_fail_extra_change` enters P4 only where the audit rejects the file.
- Every quarantine reason is counted and reported.

## 8. Infrastructure failures (excluded and counted, never relabeled)

- LibreOffice open, activation or save failure or timeout, or a postconfig
  conversion of a placed file that produces nothing
  (`reachability.save_failures`): the job is left out at `merge`
  (`jobs-saved.excluded.jsonl`) and its mutant, or every mutant of the
  target when it is the null mutant, is `save_failed`. A gold whose save
  failed is not a P1 outcome.
- A UNO application error or timeout (the mutant is not admitted).
- A scoring process that exceeds 300 s, retried at most twice with every
  retry counted; if the last attempt also times out, the row keeps verdict
  `error` (the schema has no other) and its note says `infra_failed`, which
  makes the mutant `infra_timeout` and keeps the control out of K1 and P1.
- A container failure.
- A candidate whose repeated scorings disagree (it moves to S5).
- A setup or postconfig step the harness cannot emulate that may write a file
  the checker reads: typed text (`pyautogui.write`, such as a file name in a
  save dialog), shell commands, scripts and package installs. Closing or
  launching a window and setup keystrokes without typed text are taken as
  not writing (`reachability.step_may_write`). The whole task is excluded
  (`unemulated`) and listed. Counted before the freeze from task configs
  only: no task with a mutation target is affected in any split; in the
  confirm split it removes one gold task through a postconfig that types an
  export file name and one through a setup script that writes a file, both
  from K1 and P1 (the other affected confirm tasks have no gold and enter
  neither).

A checker exception is not an infrastructure failure; it is verdict `error`.

## 9. Audit (decision D9)

- Raters: two model raters from different providers (Anthropic
  `claude-opus-5`, OpenAI `gpt-5.6-sol`; `harness/q2_mutation/raters.py`),
  labelled "model raters" in every result. Prompt `RATER_PROMPT_V1`.
- Blind packet: instruction, initial files, candidate (a 100-dpi render of up
  to 20 pages, the structure listing and a structural difference against the
  initial files). Never gold, checker verdict, score, operator, family, label
  or witness. The listing and the difference are built from the operators'
  own snapshot model (`packets.py` over `operators/_snapshot.py` and
  `_diff.py`), which records run formatting (highlight, colour, font, size,
  shading), paragraph properties, styles, headers, footers, notes, cell
  styles, shape fills, outlines, text-body properties and slide backgrounds,
  not from python-docx, python-pptx or openpyxl, so the raters do not share
  the checkers' blind spots.
- Sample, disjoint strata in priority order: all `should_pass_alt_solution`
  mutants (cap 150), all label-verdict disagreements (cap 200), 100 random
  agreements, each with its inclusion probability; plus 10% sham items
  (LibreOffice-saved gold, do-nothing; at most two per task); every P1 flip.
  Mutants labelled `ambiguous` and `error` verdicts are outside the sample
  (`raters.stratum_of`); ambiguous mutants are reported as counts per witness
  rule and verdict, never as rates.
- Spec author and raters: the blind specs that fix every label were written
  by Claude Opus 5.5 (Anthropic; `blind-spec-provenance.json`), and rater 1
  is Anthropic's `claude-opus-5`. To keep a shared-provider bias from
  hiding label errors, each rater's disagreement with the labels is reported
  on its own (`raters.summarize`, `per_rater`), and unresolved items are
  never dropped from the K3/K4 statistic.
- Decision per item: both raters accept → accept; both reject → reject;
  otherwise unresolved, sent to Kevin, whose answer (accept or reject)
  decides it. Label error uses Hajek weights; an item still unresolved at
  analysis counts as a label error. The estimate with unresolved items
  dropped is reported as a sensitivity analysis only.
- Human spot check: a stratified sample (max(5, 10%) per stratum plus 5 shams)
  for Kevin. Results state that the human check is pending until it is done.

## 10. Decision rules and kill criteria

Each criterion's sample sizes are checked in section 6; where the
pre-freeze evidence already makes a criterion unlikely to fire, it says so.

- **K1 Harness validity (first step after the freeze, before any mutant is
  scored).** On confirm tasks with a complete gold, raw gold must pass and raw
  do-nothing must fail in at least 90% of tasks under the lock-exact venv;
  otherwise stop, fix, and rerun under a new experiment id. (On the dev split
  this check passed 19/19 before the freeze.)
- **K2 VM fidelity gate.** At least 80 task-candidate pairs across at least
  three domains run through the corrected injection plan
  (`harness/q2_mutation/vm_injection.py`). A checker family with any
  unexplained disagreement between in-VM and offline verdicts is dropped from
  the headline or the harness is fixed and rerun as a new id.
- **K3 Label validity.** If Cohen's κ between the model raters on real items
  is below 0.6, or a label group's weighted label error has a one-sided 95%
  upper bound above 10%, that group is relabeled by Kevin or dropped from the
  headline. The bound (`stats.label_error_bound`) is the larger of the
  task-cluster bootstrap's 95th percentile and the exact Clopper-Pearson
  bound at the Kish effective sample size (rounded down) with the weighted
  error count rounded up, so it cannot collapse to zero when no error is
  observed (its exact part is 7.2% for 40 equally weighted items without an
  error and 11.3% with one). A group with fewer than 30 audited items, fewer than 8 tasks
  or a Kish effective size below 29 (the smallest size whose zero-error bound
  is under 10%) is insufficiently audited and treated as failing K3.
- **K4 Operator design.** If audited label error (the Hajek estimate, with
  unresolved items counted as errors) exceeds 10% in both the should-pass and
  the should-fail group, stop and redesign under a new id.
- **K5 Normalization.** An operator whose edit the reachability stage erases
  in more than 50% of its mutants is reported only as a normalization finding.
- **K6 Adequacy (negative result).** If at least 59 confirm tasks are
  evaluable for P5, P5 has zero escapes (exact one-sided 95% upper bound
  below 5%; at 59-67 tasks one escape already exceeds it), and P1 has at most
  one confirmed flip, publish "adequate under this operator set". With fewer
  than 59 evaluable tasks no adequacy claim is made, and the result says so.
  The pre-freeze evidence makes this rule very unlikely to fire, and the
  registration expects no adequacy claim: on dev,
  `pptx.eq.zorder_nonoverlap` failed `compare_pptx_files` on 2 of 5 pptx
  targets (the checker pairs shapes by position in the shape list), and there
  are 22 pptx confirm targets; the headless scoping round trip flipped 7 of 63
  gold-passing confirm golds; and 59 evaluable tasks is about what the dev
  ratios predict before any flip leaves as `null_not_pass`. K6 stays as
  written so the rule is fixed in advance.
- **K6b Adequacy per family and error type (pre-specified, descriptive).**
  A checker family with at least 29 evaluable confirm tasks for one error
  type and no event of that type is reported as having no detected error of
  that type under this operator set, with an exact one-sided 95% upper bound
  below 10%. At the sizes
  of section 6 only the xlsx family (`compare_table`, 32 targets) can reach 29
  tasks, and only for P2.
- **K7 Unreliable family.** A family whose P2, P3 or P4 task-cluster 95% lower
  bound exceeds 5% is reported as unreliable for that error type. For P2 this
  is feasible at 32 tasks for true rates of about 14% or more and at 22 tasks
  of about 17%. For P3 and P4 the probe exclusion leaves at most 11 and 19
  confirm tasks across all families (section 6), below the 8-task family
  floor in every family, so K7 cannot fire for P3 or P4 per family; P3 and
  P4 are inferential only as pooled rates (section 6).
- **K8 Prior art.** Before drafting, rerun `orx` and keyword search including
  citers of AgentRewardBench and ABC. If a mutation audit of desktop CUA
  checkers has appeared, pivot the note to the reachability, gold fixed-point
  and dependency-drift findings.
- **K9 Null-mutant coverage.** If more than 25% of confirm targets end
  `null_not_pass`, the mutation rates are reported as covering only the
  remaining targets, and the excluded checker families are named.

## 11. Priors

- How Benchmarks Mis-Score Computer-Use Agents, arXiv 2607.28367
  (https://arxiv.org/abs/2607.28367, 2026-07-30): of 57 OSWorld zero-reward
  trajectories, 8 (14.0%) were evaluator false negatives; PASS verdicts were
  not audited.
- Measuring the Checker, arXiv 2609.22220 (https://arxiv.org/abs/2609.22220,
  2026-09-02): the KernelBench official check missed 1,248 of 7,384 witnessed
  mutants (16.9%).
- AgentRewardBench, arXiv 2504.08942 (https://arxiv.org/abs/2504.08942,
  2025-04): official rule-based evaluators reached precision 83.8 and recall
  55.9 against expert labels on web-agent trajectories (Table 1), a
  false-positive measurement for rule-based web checkers.
- ABC, Establishing Best Practices for Building Rigorous Agentic Benchmarks,
  arXiv 2507.02825 (https://arxiv.org/abs/2507.02825, 2025-07): OSWorld scores
  0 on O.g.2 because its state check verifies only the relevant states and
  does not check extra harmful actions (Table 13), a qualitative prior for P4.
- Claim boundary: no mutation-based per-checker FN/FP audit of desktop CUA
  state checkers was found through 2026-10-06 under `orx` keyword and
  embedding search plus the citation trails of 2607.28367 and 2609.22220.

## 12. Exploratory, not confirmatory

- Dev-split results (harness validation, P1 on dev tasks, the end-to-end
  campaign of section 15, timing).
- Scoping-probe numbers (run split 34/38, F-CELL 12/30, headless round trip
  10/106): pre-reachability, Ubuntu `0ubuntu0.22.04.13` build, headless;
  disclosed, never pooled.
- Every (task, operator) cell touched by a scoping probe
  (`program/evidence/q2-mutation/harness/probe_touched.json`, 207 tasks) is
  kept out of P2-P5 and reported separately. 63 of the 120 confirm tasks
  carry at least one touched cell. The mapping from probe ops to operator
  ids is fixed here (`campaign.PROBE_OPERATOR_MAP`; patterns are shell-style
  over operator names). It errs toward exploratory: an unrelated-edit probe
  (a typo in body text or a table, an edited cell) shows how the task's
  checker treats unrequested changes, so it touches every extra-change
  operator of the task, including deletions and formatting edits (changed
  after the review, which found `docx.extra.delete_unrelated_paragraph`
  confirmatory on a task whose checker the typo probe had already shown to
  ignore paragraphs); a revert probe (run on xlsx cells only) touches every
  violation operator.

  | Probe op | Operators whose cells it touches |
  |---|---|
  | `controls:gold+do_nothing(raw)` | none (controls) |
  | `lo_rt:gold_headless_save(ubuntu .13)` | none (P1 is handled separately) |
  | `equiv:E-META` | `*.eq.doc_property` |
  | `equiv:E-ZIP` | none (byte-level, no document_model operator) |
  | `runsplit:E-RUNSPLIT-TOUCHED`, `runsplit:E-RUNSPLIT-UNTOUCHED` | none (byte-level) |
  | `mutants:F-TYPO`, `mutants_v2:F-TYPO-BODY` | `*.extra.*`, `docx.viol.text_edit`, `pptx.viol.text_edit`, `xlsx.viol.value_perturb`, `text.viol.line_edit` |
  | `mutants_v2:F-TYPO-TABLE` | `*.extra.*`, `pptx.viol.table_cell_text` |
  | `mutants_v2:F-CELL` | `*.extra.*`, `xlsx.viol.value_perturb` |
  | `mutants:R-REVERT`, `mutants_v2:R-REVERT` | `*.viol.*` |

  Seven Impress golds were also split-run and saved headless by a review
  agent that did not record their task ids; they cannot be mapped and are
  disclosed.
- The two probe-informed operators (`docx.extra.edit_unrelated_table_cell`,
  `pptx.viol.table_cell_text`) are reported as exploratory everywhere.
- P1 on the 93 golds the headless round trip saved is a pre-specified
  replication of that probe under the GUI-faithful save, not a confirmatory
  test (section 4); only the 16 unprobed golds are confirmatory for P1.
- Operators added after the freeze.

## 13. Reported regardless of outcome

P1-P5 and S1-S7 with intervals; per-task distributions; the status table of
section 7 per operator and per checker family; every quarantine, error and
infrastructure-failure count with reasons, including every job excluded at
`merge` and every task excluded as `unemulated`; each rater's disagreement
with the labels and the number of items Kevin adjudicated; the
excluded-task and no-target lists; the dependency-flip table; the save-timing table; the fidelity-gate
table; rater κ, sham accuracy and the pending human check; the scoping-probe
numbers labelled pre-reachability; and the deviations below.

## 14. Deviations from the reviewed plan

- The VM runs Ubuntu's LibreOffice build `0ubuntu0.22.04.4`, not TDF's; the
  save stage and operator application run the VM's own userland instead of a
  TDF tarball.
- Split seed 42 (the program's seed rule and the shared interface), not
  20261006.
- Experiment id `q2-evaluator-mutation-v1` and this path, per the program's
  shared interface.
- Intent predicates on an independent stack are replaced by spec witnesses,
  operator purity checks on the saved file, and the D9 audit.
- Human raters are replaced by provider-distinct model raters (D9).
- The mutation population is the 67 confirm tasks with a complete gold and a
  mutable file, not all 120: a mutant is an edit of a gold end state.
- Mutants carry one LibreOffice round trip more than a raw gold before the
  save stage (the UNO application save); the null mutant carries the same,
  and targets whose null mutant fails are excluded (S7, K9).
- The dependency-sensitivity arm is the scoping agent's venv, not the plan's
  leaderboard-era set (OSWorld's `requirements.txt` with setup.py
  constraints, resolved with `uv --exclude-newer 2025-07-28`). That set
  cannot be resolved as specified: `requirements.txt` at `b138d348` requires
  `daytona>=0.184.0` (first upload 2026-06-03) and `ui-tars>=0.4.2.2`
  (2025-12-11), both after the cutoff, so building it needs a choice of
  which requirements to drop. S1 is narrowed to the measured package
  differences (sections 2 and 5).
- Mutants labelled `ambiguous` (37 of 271 admitted on dev) are counted per
  witness rule and verdict but not audited, following the harness's sampler
  (`raters.stratum_of`); the operators' proposal sent them to the blind
  audit.
- Label error counts unresolved rater disagreements as errors unless Kevin
  adjudicates them, and K3 uses an exact bound with a minimum audited size
  (sections 9 and 10); the reviewed plan excluded unresolved items and used
  the bootstrap interval alone.
- Mutation rates P3 and P4 are inferential only as pooled rates; the probe
  exclusion leaves too few tasks for family-level inference (section 6).

## 15. Integration validation on the development split (exploratory)

Four end-to-end campaigns ran on the 17 dev targets through the three
CPU-only Slurm jobs (no GPU, no network, `/dev/nvidia*` absent in every
receipt). `dev-mutants-v4` ran at commit
`6ad6af6be3d471e8ccebdf99da2732f13c132f8e`, whose code tree is the one pinned
above (after the review's fixes). The exports, with recipes redacted, are
committed under `program/evidence/q2-mutation/integration/` and checked by
`tests/test_q2_mutation_integration_evidence.py`.

| Run | Code | Recipes applied to | Planned | Admitted | Evaluable (lock) | Ambiguous | `null_not_pass` | Normalized |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dev-mutants-v1` (Slurm 453-455) | `2cc8559` | base (null = base saved again) | 275 | 271 | 203 | 27 | 40 (2 targets) | 1 |
| `dev-mutants-v2` (Slurm 458-460) | `99992bc` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v3` (Slurm 461-463) | `17aac70` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v4` (Slurm 475-477), pinned code | `6ad6af6` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |

- Build: 4 of 275 planned mutants failed build-time purity (two
  `docx.alt.para_direct_for_style` changed the resolved appearance; two
  `xlsx.viol.formula_ref_shift` left the value unchanged, i.e. equivalent
  mutants). Admitted labels: 111 equiv, 28 alternative, 68 violation,
  27 extra change, 37 ambiguous. The snapshot v2 fields (pptx backgrounds,
  outlines, text-body properties) admitted and rejected the same mutants.
- Save stage (each run): 288 jobs, 286 saves, all written, no dialog,
  slowest write 0.30 s (0.40 s in v4), no open or activation failure, no
  job excluded at merge (`save_failed` 0), no unemulated step, no scoring
  timeout, no nondeterministic scoring; the lock-exact and scoping venvs
  gave the same verdict on every candidate.
- Post-save purity held for 270 of 271 admitted mutants; one
  `pptx.viol.drop_char_format` colour removal did not survive the save (S3).
- Null mutants: in v1, two targets failed: af23762e (the known gold
  fixed-point flip) and 5cfb9197, whose gold after three LibreOffice round
  trips fails `compare_pptx_files` although it passes after one. Applying
  recipes to the raw gold (v2, the registered mode) recovered 5cfb9197;
  only af23762e (28 mutants) remains excluded.
- Evaluable: 215 mutants on 15 tasks, 95 of them in probe-touched cells under
  the review's probe map (83 under the earlier map). Outside those cells,
  candidate checker errors (unaudited): `pptx.eq.zorder_nonoverlap` fails
  `compare_pptx_files` on 5cfb9197 and e4ef0baf (6 equivalence mutants, FN);
  `docx.viol.drop_char_format` (a highlight removal) passes
  `compare_docx_files_and_ignore_new_lines` on 5bc63fb9 (3 violation
  mutants, FP_R). `docx.extra.delete_unrelated_paragraph` and
  `docx.extra.edit_unrelated_paragraph` pass `compare_docx_tables` on
  936321ce (6 extra-change mutants, FP_F); both cells are now probe-touched
  (the typo probe had shown the checker ignores paragraphs) and exploratory.
  Task escapes (FN or FP_R): 3 of 15 tasks.
- Reproducibility: v1-v4 planned every mutant at the same site with the same
  label; v2, v3 and v4 gave the same admission, status, event and verdict
  for all 275 mutants under both venvs (v4 after the review's changes to the
  save-failure rule, the snapshot and the probe map), and v1 differed from
  them only on 5cfb9197. Mutant ids differ between the runs because a
  LibreOffice save is not byte-deterministic (document timestamps) and each
  recipe carries the SHA-256 of its base file.
- Controls at the same code (`dev-controls-v7`, Slurm 478-480,
  `harness/dev-controls-v7-summary.json`): K1 19/19 under both venvs; P1 one
  flip in 19 golds (af23762e; Clopper-Pearson 95% 0.13%-26.0%); no gold
  save failed; 2 dev tasks without a gold excluded as `unemulated`
  (postconfig typed text).

These numbers size the confirmatory design; they are never pooled with it.

## 16. Release

Released: sanitized tasks, specs, the operator catalog, redacted recipes
(`campaign export`: free-text leaves of 32 characters or more, or with
non-ASCII characters, in a recipe become `{redacted_sha256, chars}`, long
quoted spans in witness arguments likewise, purity details dropped), the
recipe SHA-256, verdict rows, outcome rows and summaries. Each recipe names
the SHA-256 of its base file (`input_sha256`); base files, mutant files and
full recipes stay in the host run root, and planning is deterministic given
the base, so a holder of the base files can regenerate every recipe and
check its mutant id. The mutant file itself is the recipe's steps applied to
the file each release row names in `applied_input_sha256` (`applied_to`:
under `--apply-to gold`, the raw gold, not the base), so it is reproducible
from the gold plus the recipe. A LibreOffice save is not byte-deterministic,
so a fresh base save yields new ids with the same sites and labels (section
15). Not released: mutant documents, base files, full recipes, gold or
initial files.

## 17. Freeze checklist

- [x] Every value the earlier draft left open is filled (pins block,
      catalog, specs, probe mapping, dev intra-task correlation, image).
- [x] Dev-split harness validation (gold, do-nothing, gold fixed point,
      determinism, timing) recorded as exploratory evidence.
- [x] Dev-split end-to-end campaign recorded; intra-task correlation measured;
      MDE table updated.
- [x] Spec set and operator catalog hashes recorded; blind-author provenance
      checked (`integration/blind-spec-provenance.json`).
- [x] First adversarial review answered: save failures excluded, control
      path guarded, packet and K3 bound rebuilt, K6/P1 and P3/P4 power
      restated, probe map widened, input pins added; dev rerun at the new
      code tree (`dev-mutants-v4`, `dev-controls-v7`) and pins refreshed.
- [ ] Reviewed by a second agent; lower of two review scores recorded.
- [ ] Kevin's go-ahead on decisions D2 (upstream defect reports stay
      unsent) and D9 (model raters) still stands.

## Appendix A. Operator catalog `q2-mut-operators-v1` (64 operators)

Label class is nominal; the label of each mutant comes from its witness rule.
Probe-informed operators are marked with a dagger (†).

| Family | Equivalence (E) | Alternative solution (A) | Violation (R) | Extra change (F) |
|---|---|---|---|---|
| xlsx | `xlsx.eq.doc_property`, `xlsx.eq.view_zoom`, `xlsx.eq.view_selection`, `xlsx.eq.active_sheet` | `xlsx.alt.literal_for_formula`, `xlsx.alt.reference_for_literal`, `xlsx.alt.sum_range_expand`, `xlsx.alt.plus_chain_to_sum`, `xlsx.alt.average_to_sum_count`, `xlsx.alt.absolute_refs`, `xlsx.alt.concat_to_ampersand`, `xlsx.alt.named_style_for_direct` | `xlsx.viol.value_perturb`, `xlsx.viol.formula_ref_shift`, `xlsx.viol.clear_bound_cell`, `xlsx.viol.drop_char_format`, `xlsx.viol.number_format_change` | `xlsx.extra.edit_unrelated_value`, `xlsx.extra.clear_unrelated_row`, `xlsx.extra.rename_unrelated_sheet`, `xlsx.extra.delete_unrelated_sheet`, `xlsx.extra.format_unrelated_cell` |
| docx | `docx.eq.doc_property`, `docx.eq.view_zoom` | `docx.alt.char_style_for_direct`, `docx.alt.para_direct_for_style`, `docx.alt.highlight_as_shading`, `docx.alt.case_via_format` | `docx.viol.text_edit`, `docx.viol.drop_char_format`, `docx.viol.para_align_change`, `docx.viol.line_spacing_change`, `docx.viol.delete_bound_paragraph` | `docx.extra.edit_unrelated_paragraph`, `docx.extra.delete_unrelated_paragraph`, `docx.extra.edit_unrelated_table_cell` †, `docx.extra.format_unrelated_run` |
| pptx | `pptx.eq.doc_property`, `pptx.eq.subvisible_nudge`, `pptx.eq.zorder_nonoverlap` | `pptx.alt.textbox_for_placeholder`, `pptx.alt.case_via_format` | `pptx.viol.text_edit`, `pptx.viol.table_cell_text` †, `pptx.viol.drop_char_format`, `pptx.viol.move_shape`, `pptx.viol.delete_bound_shape` | `pptx.extra.edit_unrelated_text`, `pptx.extra.delete_unrelated_slide`, `pptx.extra.add_textbox`, `pptx.extra.edit_notes` |
| text | `text.eq.trailing_newline` | none | `text.viol.line_edit` | `text.extra.unrelated_line_edit`, `text.extra.unrelated_line_delete` |
| config | `config.eq.trailing_newline`, `config.eq.json_reformat`, `config.eq.json_key_reorder`, `config.eq.ini_kv_spacing` | `config.alt.json_number_repr` | `config.viol.value_change`, `config.viol.key_delete` | `config.extra.unrelated_value_change`, `config.extra.unrelated_key_delete` |

Witness rules (`harness/q2_mutation/operators/__init__.py`): W-E-SILENT /
W-E-ALLOWED give `should_pass_equiv`, W-E-CONFLICT gives `ambiguous`;
W-A-SILENT / W-A-ALLOWED give `should_pass_alt_solution`, W-A-PINNED gives
`should_fail_violation`, W-A-MENTIONED, W-A-REPRESENTATION and W-A-STRUCTURE
give `ambiguous` unless the spec frees the aspect; W-R-PINNED / W-R-TEXT give
`should_fail_violation`, W-R-WEAK-BINDING and W-R-UNPINNED give `ambiguous`;
W-F-UNREQUESTED gives `should_fail_extra_change`, W-F-COSMETIC gives
`ambiguous`, W-F-ALLOWED gives `should_pass_equiv` for a cosmetic change and
`ambiguous` for a content change, and any rule ending in FLAGGED (an
`[AMBIGUOUS]` spec entry) gives `ambiguous`.
Planning, binding, sites and admission follow
`program/evidence/q2-mutation/operators/prereg-operators-section.md`, which
this registration adopts with two changes: recipes are applied to the raw
gold (section 3), and ambiguous mutants are counted but not audited
(section 9).
