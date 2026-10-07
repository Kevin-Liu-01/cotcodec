# q2-evaluator-mutation-v1: OSWorld-Verified checker mutation audit

**Status: DRAFT for a third review, not frozen.** Every pin below is
filled from the integration branch `stage0/q2-evaluator-mutation`, and no
value is left open. The first adversarial review (2026-10-07) was answered in
the previous draft. This draft answers the second review (2026-10-07, 55/100,
not ready to freeze), whose seven blocking defects are fixed here:

1. K3 and K4 are computed on the two label classes that enter the metrics
   without an audit gate (`should_pass_equiv`, `should_fail_violation`);
   alternative-solution acceptance and extra-change rejection are reported
   under S6; K3 has one registered consequence (sections 5, 9, 10).
2. A rater runner is in the pinned tree (`harness/q2_mutation/rater_runner.py`)
   with the D23 raters, fixed parameters, one call per rater per item,
   transport-only retries, the first-token rule, `unsure` for every
   non-answer, shams and P1 flips in the sample, and hashed receipts. The
   open-weight rater runs as a lane job under a registered GPU cap; a
   development smoke ran on dev packets (sections 2, 9, 15).
3. K2 has a registered sample, executor rule, closed list of explanations and
   a fallback label (section 10).
4. P3 is counted at the code's cell-level rule; the section 6 table, the dev
   sentence and K7 are corrected, and the family floor decides where K7
   applies (sections 6, 10).
5. The two probe-informed operators are probe-touched in code everywhere
   (`campaign.PROBE_INFORMED_OPERATORS`; section 12).
6. P1 is a replication only, on golds with an office file the save stage
   rewrites; the other golds are listed as not exposed (sections 4, 12).
7. The branch carries main's six-row ledger and decisions D1-D23.

The registered analysis is code (`harness/q2_mutation/analysis.py`), so no
choice is left to make after a confirmatory verdict is read. After the third
review and Kevin's sign-offs (section 17), freeze with

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
| Raters (decision D23) | Anthropic rater: Messages API, model `claude-opus-5-5`, the id the API names recorded by `rater_runner` before the first call (the run stops if it differs) and from every response. Open-weight rater (the independent one): `Qwen/Qwen3.5-9B` at Hugging Face revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, model receipt SHA-256 `0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3` (artifact root `9845026dbe255e24b105224eebbb5436d315713b9a5c53c434137896b160c5b1`, Apache-2.0), verified by the lane in every job |
| Rater runner and serving | `harness/q2_mutation/rater_runner.py` (inside the code-tree pin), prompt `RATER_PROMPT_V1`; vLLM 0.31.0 (commit `db9527a46873454610df6dbedf79a36d6bf1a7f6`) in the cu129 overlay of `vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` (image ID `sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b`), built by `scripts/build_vllm_overlay_on_h100.sh` from a source capsule of the frozen commit; the serving probes validated this base, variant and checkpoint (`program/evidence/2026-10-07/serving-throughput-probe-v2/`) |

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
 "code_tree_sha256": "8123ed7f72b72365f7f7658957ea7ea0a5cf4b00becfc777e5dd60ce052ba7ff",
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
 "harness_branch_commit": "65c90aae12c042f010856c589f145647f1733c0d",
 "raters": {
  "anthropic_model": "claude-opus-5-5",
  "open_weight_model_id": "qwen3.5-9b",
  "open_weight_repo": "Qwen/Qwen3.5-9B",
  "open_weight_revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
  "open_weight_receipt_sha256": "0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3",
  "vllm_base_image_id": "sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b",
  "open_weight_gpu_hours_cap": 1.0
 }
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
disagree is `nondeterministic` (S5) and leaves P2-P5. A candidate whose
verdicts differ between the venvs while each venv's two scorings agree is
rescored five times in fresh processes in each venv in the same Slurm job
(`harness/q2_mutation/dependency_flips.py`, wired into job 3 of a mutation
run and jobs 1 and 3 of a control run); it counts for S1 only if all five
agree within each venv.

**Verdicts.** `pass` iff score == 1.0; `fail` otherwise; `error` iff
`evaluate()` raised (OSWorld's `run.py` logs and skips such a task, so an
error is neither pass nor fail). A scoring that failed for a harness cause
keeps verdict `error` in its row but is an infrastructure exclusion
(`infra_failed`, sections 7 and 8): a timeout after its retries, a scoring
process that died without a result, a live getter, a refused network fetch
(`offline_eval.infra_reason`). Credit (raw score) is kept for
leaderboard-impact statements.

**Dependency sets.** Primary: lock-exact venv. Sensitivity: scoping venv,
which measures sensitivity to the package differences listed in section 2
only, not to the dependency versions in use when the leaderboard results were
produced (section 14).

## 4. Primary metrics (lock-exact venv, document_model stratum, confirm split)

The mutation metrics P2-P5 are computed on evaluable mutants (section 7):
admitted, the targeted edit survives the save stage, the target's saved null
mutant passes, the verdict is not `error`, the candidate's scorings agree,
and the (task, operator) cell is not probe-touched (a scoping-probe cell or
a probe-informed operator, section 12). The registered computation is
`harness/q2_mutation/analysis.py` (`headline`).

- **P1 Gold fixed-point false negative (pre-specified replication only).**
  Unit: task. Population: non-dev in-scope tasks with a complete gold whose
  gold places at least one office file the save stage rewrites
  (`reachability.LO_SAVE_EXTENSIONS`: `.docx`, `.xlsx`, `.pptx`, `.odt`,
  `.ods`, `.odp`; `report.save_exposed`), minus tasks excluded as
  `unemulated` (section 8). Counted before the freeze from task configs
  (`integration/prefreeze-counts-v2/counts.json`): 92 tasks (67 confirm, 25
  reserve). Event: the raw gold passes and LibreOffice-save(gold) through the
  reachability stage does not. A gold counts only if its save wrote every
  office file and neither scoring failed for an infrastructure cause; the
  others are listed. Every flip goes to the audit (stratum `p1_flip`); a
  flip is a confirmed false negative when the audit decision is accept.
  Reported: raw flip share and audit-confirmed share with exact
  Clopper-Pearson 95% intervals (zero flips in 92 gives 0-3.9%). The headless
  scoping round trip already saved all 92 of these golds (a different save
  path and build) and flipped 7 of 63 gold-passing confirm golds and 1 of 26
  reserve golds, so P1 has no confirmatory component: it replicates that
  measurement under the GUI-faithful save. The 15 golds with no office file
  (8 confirm: jpg, gif, two png, two zip, pdf, py; 7 reserve: two txt, csv,
  pdf, mp3, two png) are not exposed to the save stage, so their saved gold
  is byte-identical to the raw one; they are listed as not exposed and never
  counted. Two confirm golds (2a729ded, e8172110) are excluded as
  `unemulated`.
- **P2 FN per checker family.** Population: evaluable `should_pass_equiv`
  mutants plus the `should_pass_alt_solution` mutants whose audit decision is
  accept; an alternative-solution mutant the audit rejects, leaves unresolved
  or never sampled stays out of P2 and is reported under S6. Event: the
  verdict is not pass.
- **P3 FP_R, pooled over checker families.** Population: evaluable
  `should_fail_violation` mutants. Event: the verdict is pass. A family rate
  is inferential only above the family floor (section 6), otherwise
  descriptive.
- **P4 FP_F, pooled over checker families.** Population: evaluable
  `should_fail_extra_change` mutants, except a mutant the checker passes
  whose audit decision is not reject (accepted, unresolved or not sampled):
  such a mutant leaves P4's numerator and denominator, because its label is
  not confirmed. Event: the checker passes the mutant and the audit rejects
  it. Extra-change mutants the checker fails stay in the denominator. The
  estimate with unresolved passed mutants counted as events is a
  sensitivity analysis. Always reported separately from P3; family rates as
  for P3.
- **P5 Task-level escape rate.** Share of evaluable confirm tasks (at least
  one evaluable `should_pass_equiv` or `should_fail_violation` mutant) with at
  least one FN or FP_R event, with an exact Clopper-Pearson 95% interval.

A checker family is the set of distinct metric functions of a task, joined by
`+` when there are several (`campaign.checker_family`); `compare_table` rule
types and `compare_pptx_files` facets are descriptive sub-families. Every
pooled and family rate is a task-equal mean: the unweighted mean over tasks
of each task's share of its evaluable mutants with the event (at most three
mutants per task and operator, site seeds 42, 43, 44), with the task-cluster
percentile bootstrap (10,000 resamples, seed 42, two-sided 95%).

## 5. Secondary metrics

- S1 Dependency flips: candidates whose verdict differs between the two venvs
  while each venv's two fresh-process scorings agree (`campaign.build_report`
  `venv_disagreements`, `report.aggregate` `dependency_flips`), counted only
  when five further fresh-process scorings in each venv all agree
  (`dependency_flips.py`; `report.json` `s1`, `confirmed_at_repeat_5`);
  candidates that fail the confirmation are reported as unstable (S5). Its
  scope is the package differences of section 2
  (pandas 3.0.1 vs 2.3.3, opencv-python-headless, chardet, beautifulsoup4 and
  59 others); it is not a measurement of leaderboard-era drift.
- S2 Script-writer stratum rates (P2-P4 on that stratum; empty for this
  catalog).
- S3 Reachability normalization per operator: share of admitted mutants whose
  targeted edit is absent after the save (operator purity re-run on the saved
  file against the saved null mutant).
- S4 Save timing: share of all saves of the save stage (postconfig saves and
  agent-equivalent saves) whose write took longer than the 0.5 s the VM waits
  before reading the file (`campaign.reachability_summary`).
- S5 Nondeterministic checkers: candidates whose repeated scorings disagree.
- S6 Audit agreement with the a-priori labels, per label class
  (`raters.summarize` `by_label_class`): decisions, the Hajek-weighted share
  agreeing with the label and the unresolved share for each of the four
  label classes; for the audit-gated classes, the share of
  `should_pass_alt_solution` mutants accepted and of
  `should_fail_extra_change` mutants rejected. Also each rater's answers on
  its own, sham accuracy per rater, and the P1 flip decisions.
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
- Checker families of the 67 confirm target tasks (from task configs,
  `integration/prefreeze-counts-v2/counts.json`): `compare_table` 31,
  `compare_pptx_files` 21, `compare_docx_files` 5, `compare_docx_images` 2,
  `compare_docx_tables` 2, `compare_line_spacing` 2, and one task each for
  `check_tabstops`, `compare_csv+compare_table`,
  `compare_pptx_files_tolerant` and `evaluate_strike_through_last_paragraph`.
  The 13 docx targets are spread over six families.
- Planned mutants: the dev campaign planned 275 mutants on 17
  targets (16.2 per target) and admitted 271, so the confirm split is
  expected to yield about 1,100 planned and 1,080 admitted mutants (68
  targets), of which the dev run made 78% evaluable.
- Pooled and family rates: task-cluster percentile bootstrap, 10,000
  resamples, seed 42 (`harness/q2_mutation/stats.py`). Wilson or exact
  intervals only for task-level proportions.
- Family floor: a family rate is inferential only with at least 8 evaluable
  tasks and 20 evaluable mutants (`analysis.FAMILY_MIN_TASKS`,
  `FAMILY_MIN_MUTANTS`); otherwise it is descriptive. The floor alone decides
  whether K7 and K6b apply to a family and metric; no inferential claim is
  made at the operator × checker cell level.
- The probe exclusion (section 12) works at the (task, operator) cell
  (`campaign.is_probe_touched`), so a probe removes only the operators it
  maps to. Counted before the freeze from task configs and
  `probe_touched.json` only, at that cell-level rule (with the probe-informed
  operators touched everywhere; `integration/prefreeze-counts-v2/recount.py`):
  of the 67 confirm target tasks, 40 have at least one planned violation
  operator outside probe-touched cells (22 pptx, 13 docx, 5 xlsx; by checker
  family `compare_pptx_files` 21, `compare_docx_files` 5, `compare_table` 5,
  at most 2 for every other family) and 14 have an extra-change operator
  outside them (8 xlsx, 4 pptx, 2 docx; `compare_table` 8,
  `compare_pptx_files` 4). Equivalence and alternative-solution cells are
  untouched except `*.eq.doc_property`. On dev the same counts are 12 and 3
  of 17 target tasks, and `dev-mutants-v4` made 5 of the 12 evaluable for
  P3 outside probe-touched cells (26 mutants; one of them, e4ef0baf, a
  `compare_pptx_files` task, one of 4 such dev tasks) and 2 of the 3 for P4
  (6 mutants). Many tasks with an untouched violation operator have no site
  for it (no requirement binds the aspect), so the task count is an upper
  bound on P3's population.
- Expected evaluable confirm tasks per label class, outside probe-touched
  cells, from the dev ratios (P3: 40 × 5/12; P4: 14 × 2/3; P2: 67 × 15/17
  and 67 × 5/17), and the minimum detectable pooled rate (one-sided α = 0.05,
  power 0.8, null rate 5%, normal approximation with the cluster design
  effect) and zero-event exact one-sided 95% upper bound at that size:

  | Label class (metric) | Expected tasks | Mutants per task (dev) | ICC assumed | MDR | Zero-event bound |
  |---|---:|---:|---:|---:|---:|
  | `should_pass_equiv` (P2) | 59 | 4.0 | 0.5 | 11.5% | 4.95% |
  | `should_pass_alt_solution` (P2 after the audit) | 20 | 5.6 | 0.5 | 16.5% | 13.9% |
  | `should_fail_violation` (P3) | 17 | 5.2 | 0.5 | 17.7% | 16.2% |
  | `should_fail_extra_change` (P4, before the audit gate) | 9 | 3.0 | 1.0 | 29.8% | 28.3% |

  P3 and P4 are therefore inferential mainly as pooled rates, and only for
  large effects. A P3 family rate can be inferential only where it reaches
  the family floor; `compare_pptx_files` (21 untouched tasks, dev yield 1 of
  4) is the only family that can, and the dev yield makes it unlikely. No
  P4 family can reach the floor. The probe-touched violation and
  extra-change cells are still built, scored and reported as exploratory,
  family by family. Adding the reserve split's 28 targets (18 and 4 tasks
  with untouched violation and extra-change operators) would raise the
  expected P3 and P4 sizes to about 24 and 12 tasks (MDR 15.5% and 26.0%);
  it is not part of this registration.
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
  | 31 | 12.4% / 13.5% / 14.6% / 17.1% | 10.9% / 12.5% / 13.9% |
  | 21 | 14.2% / 15.7% / 17.0% / 20.2% | 12.3% / 14.3% / 16.1% |
  | 17 | 15.4% / 17.0% / 18.6% / 22.2% | 13.2% / 15.5% / 17.6% |
  | 13 | 17.1% / 19.0% / 20.9% / 25.1% | 14.5% / 17.2% / 19.7% |

- Exact one-sided 95% upper bound with zero events: 4.4% at 67 tasks, 4.95%
  at 59, 9.2% at 31, 13.3% at 21, 16.2% at 17, 20.6% at 13, 28.3% at 9,
  45.1% at 5. With one event at 67 tasks the bound exceeds 5%.
- K7's registered test (two-sided 95% task-cluster percentile bootstrap,
  family flagged when its 2.5% limit exceeds 5%) has less power than the
  one-sided normal MDR above. Simulated with beta-binomial tasks, ICC 0.5
  (`integration/prefreeze-counts-v2/sim_k7.py`, `k7-power.json`; 400
  replicates, 2,000 resamples), P(flagged): at 31 tasks × 4 mutants 0.47 /
  0.73 / 0.84 / 0.93 at true rates 14 / 17 / 20 / 22%; at 21 × 4 0.38 / 0.53
  / 0.70 / 0.78 / 0.90 at 14 / 17 / 20 / 22 / 25%; at the 8-task floor (5
  mutants) 0.59 at 30% and 0.72 at 35%. False alarm at a true 5%: at most
  0.5%. 80% power therefore needs about 19% at 31 tasks and 23% at 21.

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
| `infra_failed` | the mutant's or its null mutant's scoring failed for a harness cause: it exceeded 300 s on every attempt (one try and two retries), or its process died without a result, met a live getter or a refused network fetch | no, infrastructure, with the reason |
| `null_not_pass` | the target's saved null mutant does not pass under this venv | no, S7 |
| `error` | `evaluate()` raised | no, counted per checker |
| `nondeterministic` | the mutant's or its null mutant's repeated scorings disagree | no, S5 |
| `ambiguous` | label `ambiguous` | no, counted per witness rule and verdict |
| `evaluable` | all of the above clear | yes: event FN, FN_alt, FP_R or FP_F when the verdict disagrees with the label, otherwise `ok` |

- `should_pass_alt_solution` enters P2 only after audit acceptance; before
  the audit its events are reported as `FN_alt`.
- A passed `should_fail_extra_change` mutant enters P4 only where the audit
  rejects the file (section 4).
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
  `error` (the schema has no other) and its note says `infra_failed` with
  reason `timeout`, which makes the mutant `infra_failed` and keeps the
  control out of K1 and P1. A scoring process that dies without a result
  (`worker_died`, for example an out-of-memory kill), a live getter
  (`live_state_required`) or a refused network fetch (`network_refused`) is
  handled the same way, without a retry (`offline_eval.infra_reason`).
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
  export file name and one through a setup script that writes a file
  (2a729ded, e8172110), both from K1 and P1 (the other affected confirm tasks
  have no gold and enter neither).
- Rerun policy: a Slurm job of the campaign (control, mutation, audit packet
  or rater job) that fails is rerun in full under a versioned run name, at
  most twice; every attempt is reported; the first complete run counts and
  nothing from a failed attempt is merged into it. An open-weight rater job
  that stops early keeps its rated items (one call per item), and a rerun
  rates only the rest, inside the GPU cap of section 9. A failed UNO office
  restart aborts the build job (`CampaignError`) and falls under this rule.

A checker exception is not an infrastructure failure; it is verdict `error`.

## 9. Audit (decisions D9 and D23)

- Raters (D23), labelled "model raters" in every result:
  - Anthropic rater (`model-rater-anthropic`): the Anthropic Messages API,
    model `claude-opus-5-5`. Before the first call the runner records the
    model object the API returns for that id (`GET /v1/models/{id}`) and
    stops if its id differs; every response's `model` field is recorded.
    `max_tokens` 16,000 (it covers the model's adaptive thinking and the
    answer), effort `high` (`output_config.effort`). The request carries no
    sampling parameter: this model rejects `temperature`, `top_p` and
    `top_k` and its thinking cannot be disabled, so its sampling is the API's
    fixed default at that effort. No refusal fallback is enabled, because a
    fallback would answer with another model; a refusal is `unsure`.
    Per-request timeout 600 s, at most 4 requests in flight. The calls run
    where the API key is (not on the H100 host).
  - Open-weight rater (`model-rater-open-weight`, the independent one):
    Qwen3.5-9B at the revision and receipt of section 2, served by
    `vllm serve` on 127.0.0.1 inside the network-less lane container with
    fixed flags (`rater_runner.ENGINE_FLAGS`: bf16, seed 42, tensor parallel
    1, `max_model_len` 131,072, GPU memory utilization 0.90, 16 sequences,
    no prefix caching, `generation_config vllm`, up to 40 images per
    request); greedy decoding (temperature 0, top_p 1, seed 42),
    `max_tokens` 256, thinking off through the chat template, timeout 600 s,
    at most 8 requests in flight. An args doctor checks the engine argv and
    the request payload with vLLM's own parsers before the engine starts.
    It runs as a docker-research lane job (`scripts/submit_docker_research_job.py`,
    `container_profile: vllm`, one H100, the model receipt verified in the
    container, one packet shard mounted read-only as the study artifact;
    manifest from `infra/q2-mutation/run/render_rater_manifest.py`) in the
    cu129 overlay built from the frozen commit.
  - GPU cap: every open-weight rater job of the confirmatory audit together
    (all shards and any rerun) at most 1.0 GPU-h of allocation, plus the
    overlay build at the frozen commit, at most 10 minutes of one H100
    (0.167 GPU-h, as for the serving probes, D8 and D19). The development
    smoke (section 15) was capped at 0.2 GPU-h plus its own overlay build.
    The registration's GPU total is therefore at most 1.17 GPU-h, below the
    8 GPU-h gauntlet threshold.
  - Data sent to the Anthropic API: only the packet text (the task
    instruction, structure listings and differences) and page renders of the
    task's starting files and of the candidate end-state files. These are
    public OSWorld task files (task configs Apache-2.0; file-cache documents
    under the dataset's apache-2.0 card, third-party content) and edits of
    them made by the operators; no credential, private data or other
    material is sent. Volume for the confirmatory audit: at most 587 items
    (450 mutants under the stratum caps, 45 shams, at most 92 P1 flips), one
    request each, with up to 40 page images per request.
- Runner rules (`harness/q2_mutation/rater_runner.py`): one call per rater per
  item (an item with any record in `calls.jsonl` is never sent again, so a
  resumed run skips it); retries only on transport errors (connection
  failure, timeout, HTTP 408, 409, 429, 500, 502, 503, 504, 529), at most 3,
  after 5, 20 and 60 s; the answer is the first word of the reply after
  leading whitespace, markdown emphasis, quotes, list markers and brackets,
  case-folded, and counts only if it is `accept`, `reject` or `unsure`
  (`raters.parse_first_token`); a refusal (`stop_reason` `refusal`), an empty
  or unparseable reply, a timeout that survived its retries, an exhausted
  transport, or a request the provider rejected (HTTP 400 or 413, for
  example a packet over the context window) is `unsure`; an item a job never
  reached is `unsure` (`unrated`); an authentication, permission or
  unknown-model error stops the run and rates nothing (rerun under section 8).
  Every call record holds the SHA-256 of the exact request bytes, of the
  canonical request body (rebuilt from the packet by `request_body`) and of
  the exact response bytes; `receipt.json` records the code, prompt, packet
  file, model identity, parameters, outcome counts and the SHA-256 of
  `calls.jsonl`. Both raters see the same parts in the same order
  (`packet_parts`): `RATER_PROMPT_V1` as the system prompt, then the packet,
  then the answer line; each rater sees the items in its own seeded order.
- Blind packet (`harness/q2_mutation/audit.py`, built in the LO-VM image):
  the task instruction, every starting file of the task and every end-state
  file of the candidate, each with its structure listing; for each end-state
  file its structural difference against the starting file; and 100-dpi page
  renders of office files and PDFs by the VM's own LibreOffice and
  `pdftoppm` (at most 20 pages per file, 40 per packet, end-state pages
  first; a cap is stated in the packet). Never gold, checker verdict, score,
  operator, family, label or witness. The listing and the difference are
  built from the operators' own snapshot model (`packets.py` over
  `operators/_snapshot.py` and `_diff.py`), which records run formatting
  (highlight, colour, font, size, shading), paragraph properties, styles,
  headers, footers, notes, cell styles, shape fills, outlines, text-body
  properties and slide backgrounds, not from python-docx, python-pptx or
  openpyxl, so the raters do not share the checkers' blind spots. Packets are
  written to shards of at most 480 MiB so each fits a lane study artifact.
- Candidate pool (`raters.audit_candidates`): the mutants P2-P5 are computed
  on, evaluable under the lock-exact venv and outside probe-touched cells.
- Sample (`raters.draw_audit_sample`, seed 42), disjoint strata in priority
  order: all `should_pass_alt_solution` mutants (cap 150), all label-verdict
  disagreements (cap 200), 100 random agreements, each with its inclusion
  probability; plus 10% sham items (the target's LibreOffice-saved null
  mutant as the saved gold, and the task's starting files as do-nothing; at
  most two per task); plus every P1 flip of the confirm and reserve control
  runs (stratum `p1_flip`). Mutants labelled `ambiguous` and `error`
  verdicts are outside the sample (`raters.stratum_of`); ambiguous mutants
  are reported as counts per witness rule and verdict, never as rates.
  `submit_audit.sh` builds the sample, the items and the packets in one
  CPU-only job; `sample.jsonl` (labels and verdicts) never reaches a rater.
- Spec author and raters: the blind specs that fix every label were written
  by Claude Opus 5.5 (Anthropic; `blind-spec-provenance.json`), and the
  Anthropic rater is a Claude model, so the open-weight rater is the
  independent one: each rater's answers are reported on their own
  (`per_rater`), and an item on which the raters do not agree is decided by
  Kevin or counted as a label error, never dropped.
- Decision per item (`raters.final_decision`): both raters accept → accept;
  both reject → reject; otherwise unresolved. Kevin adjudicates unresolved
  items on the same packet, blind to the label, the verdict, the operator and
  the raters' answers; his answer (accept or reject) decides it. Label error
  uses Hajek weights; an item still unresolved at analysis counts as a label
  error. The estimate with unresolved items dropped is a sensitivity
  analysis only.
- K3 and K4 groups: `should_pass_equiv` (enters P2 and P5) and
  `should_fail_violation` (enters P3 and P5), the label classes that enter the
  metrics without an audit gate. Alternative-solution and extra-change items
  decide their own entry into P2 and P4, so their acceptance and rejection
  rates are S6 results and never fire K3.
- Human spot check: a stratified sample (max(5, 10%) per stratum plus 5 shams)
  for Kevin. Results state that the human check is pending until it is done.

## 10. Decision rules and kill criteria

Each criterion's sample sizes are checked in section 6; where the
pre-freeze evidence already makes a criterion unlikely to fire, it says so.
`analysis.headline` evaluates every rule below that has data.

- **K1 Harness validity (first step after the freeze, before any mutant is
  scored).** On confirm tasks with a complete gold, raw gold must pass and raw
  do-nothing must fail in at least 90% of tasks under the lock-exact venv;
  otherwise stop, fix, and rerun under a new experiment id. (On the dev split
  this check passed 19/19 before the freeze.) K1 is a harness check, not a
  blind test: the scoping probe already scored the raw gold and do-nothing of
  every confirm task (`controls:gold+do_nothing(raw)`, section 12).
- **K2 VM fidelity gate.**
  - Sample: `campaign k2-sample` draws 80 scoring jobs (admitted mutants and
    null mutants) of the confirm mutation run from `build/scoring-jobs.jsonl`
    alone, in job 3 before scoring (no verdict exists or is read), seed 42:
    each task domain's jobs are shuffled with `random.Random(f"42:k2:{domain}")`
    and taken round-robin over the sorted domains, at most 4 per task, the
    cap relaxed only if the pool runs short. At least 3 domains are required;
    the confirm targets span `libreoffice_calc`, `libreoffice_impress`,
    `libreoffice_writer` and others. `k2-sample.summary.json` records the
    SHA-256 of the job list and of the sample.
  - Executor: the VM runtime of `stage0/q2-action-path` at the commit of its
    own frozen acceptance registration, running the injection plan of
    `harness/q2_mutation/vm_injection.py`; that commit and the VM image
    digest are recorded in the K2 report before any in-VM verdict is compared
    with an offline one. No executor commit is available at this draft (the
    branch is unfinished), so K2 is not a precondition of the freeze or of
    the confirm run.
  - Comparison: for each sampled job, the in-VM `DesktopEnv.evaluate()`
    verdict against the offline lock-exact verdict for the same
    `candidate_sha256`. A difference is explained only by one of: (1) the
    in-VM postconfig save took longer than 0.5 s, so the VM checker read the
    unsaved file; (2) the candidate's offline repeat scorings or in-VM
    repeated evaluations disagree; (3) the in-VM file hash after injection
    differs from the candidate's SHA-256 (infrastructure; the pair is
    excluded); (4) a VM infrastructure failure (boot, reset, injection or
    evaluate error or timeout; excluded). Any other difference is
    unexplained (`analysis.K2_EXPLANATIONS`).
  - Consequence: a checker family with an unexplained difference leaves the
    headline and is reported as exploratory. Fallback: if no K2 report exists
    when the result is written, the headline is labelled "offline harness,
    VM fidelity unverified"; a K2 report added later (on the same fixed
    sample) replaces the label and applies the consequence.
- **K3 Label validity (one rule).** K3 fires for a group when its weighted
  label error's one-sided 95% upper bound exceeds 10% or the group is
  insufficiently audited, and for both groups when Cohen's κ between the two
  model raters on the real (non-sham) items is below 0.6. The bound
  (`stats.label_error_bound`) is the larger of the task-cluster bootstrap's
  95th percentile and the exact Clopper-Pearson bound at the Kish effective
  sample size (rounded down) with the weighted error count rounded up, so it
  cannot collapse to zero when no error is observed (its exact part is 7.2%
  for 40 equally weighted items without an error and 11.3% with one). A group
  with fewer than 30 audited items, fewer than 8 tasks or a Kish effective
  size below 29 (the smallest size whose zero-error bound is under 10%) is
  insufficiently audited. Consequence: when K3 fires for `should_pass_equiv`,
  P2 and P5 leave the headline; for `should_fail_violation`, P3 and P5; when
  κ is below 0.6, P2-P5. A metric that leaves the headline is reported as
  exploratory with the same tables; nothing is relabelled
  (`analysis.headline_exclusions`).
- **K4 Operator design.** If audited label error (the Hajek estimate after
  Kevin's adjudication, with unresolved items counted as errors) exceeds 10%
  in both K3 groups, stop and redesign under a new id.
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
  are 21 `compare_pptx_files` confirm target tasks; the headless scoping round
  trip flipped 7 of 63 gold-passing confirm golds; and the second review
  counted 4 raw-gold failures and 7 headless flips among the 67 confirm
  target golds, which caps P5 at about 56 tasks if they replicate. K6 stays
  as written so the rule is fixed in advance.
- **K6b Adequacy per family and error type (pre-specified, descriptive).**
  A checker family with at least 29 evaluable confirm tasks for one error
  type and no event of that type is reported as having no detected error of
  that type under this operator set, with an exact one-sided 95% upper bound
  below 10%. Only `compare_table` (31 confirm target tasks) can reach 29
  tasks, and only for P2; it needs 29 of its 31 tasks evaluable.
- **K7 Unreliable family.** A family whose P2, P3 or P4 rate is inferential
  (it reaches the family floor of section 6) and whose task-cluster two-sided
  95% interval has a lower limit above 5% is reported as unreliable for that
  error type. The family floor alone decides whether K7 applies. For P2, 80%
  power needs a true rate of about 19% in `compare_table` (31 tasks) and
  about 23% in `compare_pptx_files` (21 tasks) (section 6). For P3 only
  `compare_pptx_files` can reach the floor, and for P4 no family can.
- **K8 Prior art.** Before drafting, rerun `orx` and keyword search including
  citers of AgentRewardBench and ABC. If a mutation audit of desktop CUA
  checkers has appeared, pivot the note to the reachability, gold fixed-point
  and dependency-drift findings.
- **K9 Null-mutant coverage.** If more than 25% of confirm targets end
  `null_not_pass` (at least 18 of 68), the mutation rates are reported as
  covering only the remaining targets, and the excluded checker families are
  named.

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
  disclosed, never pooled. The probe `controls:gold+do_nothing(raw)` scored
  the raw gold and do-nothing of all 120 confirm tasks, so K1 is not blind;
  it stays a harness check (section 10).
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
  `pptx.viol.table_cell_text`, catalog provenance `probe_informed`) are
  probe-touched on every task: `campaign.is_probe_touched` returns true for
  them (`PROBE_INFORMED_OPERATORS`, kept equal to the catalog by a test), so
  `build_report` keeps them out of P2-P5 and the audit pool, and every outcome
  row carries `probe_informed`.
- P1 as a whole: all 92 counted golds were saved by the headless round trip,
  so P1 is a pre-specified replication of that probe under the GUI-faithful
  save, with no confirmatory part (section 4). The golds without an office
  file are not exposed to the save and are listed, not counted.
- Operators added after the freeze.

## 13. Reported regardless of outcome

P1-P5 and S1-S7 with intervals; per-task distributions; the status table of
section 7 per operator and per checker family; every quarantine, error and
infrastructure-failure count with reasons, including every job excluded at
`merge` and every task excluded as `unemulated`; each rater's answers and
disagreement with the labels, every call outcome (refusals, unparseable and
empty replies, timeouts, rejected requests, unrated items) and the number of
items Kevin adjudicated; the audit gate counts of P2 and P4
(`analysis.headline` `audit_gate`) and P4 with unresolved items counted as
events; the family-floor flags, K6b and K7 per family; which metrics left
the headline under K2 or K3, and the K2 label; the excluded-task,
not-exposed-gold and no-target lists; the dependency-flip table; the
save-timing table; the fidelity-gate table; rater κ, sham accuracy and the
pending human check; GPU time and API usage of the raters; the scoping-probe
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
- Human raters are replaced by two model raters (D9). D9 named two API
  providers; D23 replaces the second (no OpenAI key, the Moonshot account is
  suspended) with a self-hosted open-weight model (Qwen3.5-9B), which is the
  independent rater because the spec author and the first rater are both
  Claude models.
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
- K3 is computed on the two label classes that enter the metrics without an
  audit gate, and its consequence is that the affected metrics leave the
  headline; the earlier drafts grouped all should-pass and all should-fail
  labels and allowed relabelling by Kevin.
- P1 has no confirmatory part and counts only golds exposed to the save
  stage (section 4).
- Mutation rates P3 and P4 are inferential mainly as pooled rates; the probe
  exclusion leaves at most one family (`compare_pptx_files`, for P3) able to
  reach the family floor (section 6).

## 15. Integration validation on the development split (exploratory)

Four end-to-end campaigns ran on the 17 dev targets through the three
CPU-only Slurm jobs (no GPU, no network, `/dev/nvidia*` absent in every
receipt). `dev-mutants-v4` ran at commit
`6ad6af6be3d471e8ccebdf99da2732f13c132f8e`, the code tree pinned by the
second draft (after the first review's fixes). The code changed after it in
the second review's fixes (audit, rater runner, analysis, report, K2 sample,
probe-informed cells and the classification of harness-caused scoring
failures); the dev rerun at the pinned tree is recorded below
(`dev-mutants-v5`, `dev-controls-v8`). The exports, with recipes redacted,
are committed under `program/evidence/q2-mutation/integration/` and checked
by `tests/test_q2_mutation_integration_evidence.py`.

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

- Rater smoke on dev packets (`integration/rater-smoke-dev-v1/`, code
  `ba840b4`): `submit_audit.sh` (Slurm 559, CPU only, LO-VM image) drew the
  dev audit from `dev-mutants-v4` and `dev-controls-v7` (pool 120 evaluable
  mutants outside probe cells; 28 alternative, 9 disagreement and 83
  agreement items, 12 shams and the af23762e P1 flip: 133 items) and wrote
  133 blind packets with renders in one 410 MB shard. The cu129 overlay was
  built from a source capsule of `ba840b4` (Slurm 566, 45 s on one H100,
  image `sha256:6bc53f50ee8d556337c07a63df2f3d624fcbfe8becbbe0b95d25e1973eee74a1`);
  a CPU-only Slurm job ran the args doctor (573, pass). The open-weight rater
  ran as a lane job (Slurm 582, 6 min 37 s on one H100, 0.110 GPU-h of its
  0.2 cap; engine ready in 97 s): 133 calls, each sent once, every reply
  parsed by the first-token rule (no retry, no refusal, three replies cut at
  256 tokens after a valid first word), prompts up to 120,678 tokens (median
  46,294) against the 131,072-token window, median 14.7 s per call. Answers
  (exploratory, one rater): do-nothing shams 6 of 6 rejected; gold shams 4
  of 6 accepted; the P1 flip accepted; equivalence 35 accept / 25 reject;
  alternative 25 / 3; violation 8 / 18; extra change 0 / 6. Its rejections of
  equivalence mutants and of two gold shams cite the task result or changes
  the save stage itself makes (for example the VM profile's default font and
  language written into a saved spreadsheet), not the mutation: the packet's
  difference is against the raw starting file. If the two raters split this
  way on confirm, K3 for `should_pass_equiv` fires unless Kevin adjudicates
  the unresolved items (section 10). The Anthropic rater did not run: the
  API key available to the agent is rejected (HTTP 401) on the model
  lookup, before any packet is sent.

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
15). The audit's released evidence is the sample summary, each rater's call
records (answer, status, outcome, request, body and response SHA-256, model
id, usage) and receipt, the decisions and the audit summary. Not released:
mutant documents, base files, full recipes, gold or initial files, audit
packets and renders, and raw rater responses (they may quote document text).

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
- [x] Second adversarial review (2026-10-07): 55/100, not ready to freeze;
      its seven blocking defects are fixed in this draft (see the status
      note), the cheap rule-code inconsistencies too (S1, S4, S6, the P4
      denominator, the audit pool, the family sizes, K7's power, the
      `infra_failed` causes, the rerun policy). Lowest review score so far:
      55.
- [x] Rater runner in the pinned tree; open-weight rater smoke on dev
      packets inside its 0.2 GPU-h cap (section 15).
- [ ] Anthropic rater smoke on dev packets: blocked, the API key in the
      agent's environment is rejected (HTTP 401); needs a working key.
- [ ] Third adversarial review; record its score next to 55 and use the
      lower.
- [ ] Kevin's sign-offs: D2 (upstream defect reports and other outward
      disclosures stay unsent while this runs); D23 rater lineup, including
      sending public OSWorld task files and their renders to the Anthropic
      API (section 9); acceptance that no adequacy claim is expected (K6)
      and that P3 and P4 are pooled, large-effect tests; P1 as a replication
      that uses reserve-split golds; release of the specs, which quote short
      passages of file-cache documents; ownership and size of the human spot
      check (recommendation: every should-fail agreement-stratum item that
      drives K3), whose result stays pending until done.

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
