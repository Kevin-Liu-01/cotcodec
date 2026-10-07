# q2-evaluator-mutation-v1: OSWorld-Verified checker mutation audit

**Status: DRAFT, not frozen.** Every `FILL-AT-FREEZE` marker must be replaced
and reviewed before freezing with

```bash
uv run python scripts/preregister.py freeze q2-evaluator-mutation-v1 \
  program/preregistrations/q2-evaluator-mutation-v1.md
uv run python scripts/preregister.py verify q2-evaluator-mutation-v1
```

No confirmatory mutant is scored before the freeze. Development-split runs
(harness validation, gold fixed-point checks, τ and timing calibration) are
allowed and are reported as exploratory.

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
| LibreOffice | the VM's own Ubuntu build, `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, "LibreOffice 7.3.7.2 30(Build:2)" (not TDF's build). The save stage runs the VM's extracted `/usr`, `/etc`, dpkg database, LibreOffice profile and the user's site-packages with PyAutoGUI 0.9.54 (205,028 files, tree SHA-256 `fceee6501ff0d1f1a33500b36663624c220f1598140fa271040b5e97a9de30bf`) plus xvfb `2:21.1.4-2ubuntu1.7~22.04.8` (the VM's X server version, deb SHA-256 `f8c64bc652e3dc1a1041e85025267f574c27f86b00d7965545a8b3ec41a60cd4`) and openbox 3.6.1-10; no VM package changes; one passwd entry for the runtime uid. LO-VM image `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361` (rebuilt image at freeze: FILL-AT-FREEZE) |
| LibreOffice profile | the VM's `registrymodifications.xcu` (SHA-256 `6b5ec88d1570a8ad85932eb53a1a6f8370053d3ac60b30fe759c14135e902ef2`): `WarnAlienFormat=false`, `ShowTipOfTheDay=false`, Writer default filter "MS Word 2007 XML" |
| Metric image | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (ubuntu:22.04 `sha256:5ec03bb3…6401`, Python 3.12.13, uv 0.11.30) |
| Lock-exact venv (primary) | OSWorld `uv.lock` exported for Python 3.12 with hashes, agp-client left out; requirements SHA-256 `3f463d6f3331a80c3054dfd8aced1dabb56adf8ee8b6fa7441e25435f626c2a3`; installed-RECORD fingerprint `f2c9e208d2bdb888668e64143f0603ce92f56cee2fd1002f0211d2c2287db810`; pandas 3.0.1, numpy 1.26.4, python-pptx 1.0.2, python-docx 1.2.0, openpyxl 3.1.5, torch 2.5.1 |
| Scoping venv (sensitivity) | the scoping agent's 129 package versions (pandas 2.3.3, torch 2.5.1+cpu); requirements SHA-256 `5ae07a7a527c22ff580a171692ccbc608f563e6c7264b0819a92ff1c41bd6fb7`; fingerprint `e591c8875c353ecbf6ec38b6c9c467e01b4164cc129744bd51e27c993310417a` |
| Task export | `program/evidence/q2-mutation/sanitized-tasks.manifest.json` (205 tasks) |
| Splits | `program/evidence/q2-mutation/splits.json`, seed 42, stratified by domain × task class: dev 32, confirm 120, reserve 53 |
| Requirement specs | `program/evidence/q2-mutation/specs/`, author `blind-model-author-v1`; set SHA-256 FILL-AT-FREEZE |
| Operator catalog | `harness/q2_mutation/operators/`; catalog SHA-256 and per-operator label class FILL-AT-FREEZE |
| Harness | integration branch `stage0/q2-evaluator-mutation` commit FILL-AT-FREEZE; schema `q2-mutation-schema-v1` |

Licences of runtime packages that are run but never vendored: PyMuPDF 1.27.1
(AGPL-3.0 or commercial), borb 2.1.25 (AGPL-3.0-or-later or commercial),
mutagen 1.47.0 (GPL-2.0+), formulas 1.3.3 (EUPL-1.1+). Mutant documents are
never released; recipes, verdicts and kill matrices are.

## 3. Design

**Candidates.** Each candidate is a set of end-state files for one task. Kinds:
the task's gold (where every metric pairs a `vm_file` result with a
`cloud_file` gold that is not one of the task's own inputs), do-nothing (the
initial state), and operator mutants (`MutationResult`, schema v1).

**Labels.** Fixed a priori from the blind requirement spec, never from a
checker: `should_pass_equiv`, `should_pass_alt_solution`,
`should_fail_violation` (witness names at least one `req_id`),
`should_fail_extra_change`, `ambiguous`.

**Strata.** `document_model` mutants (edits made through an application's
document model) form the headline. `script_writer` mutants (byte-level edits
LibreOffice normalizes on load: split runs, re-packed zips, re-serialized XML)
are reported separately and never pooled.

**Reachability stage (GUI-faithful save).** Every office candidate is placed
at its VM path in a fresh copy of the VM profile, opened by non-headless
LibreOffice under Xvfb before any postconfig step, and the task's postconfig
is replayed step by step: `wmctrl -Fa` activation, keystrokes through the VM's
pyautogui, sleeps, and `libreoffice --convert-to` with its exact filter
string. Tasks without a postconfig save get one agent-equivalent save
(open, activate, Ctrl+S) per OOXML/ODF candidate. File-only postconfig steps
(downloads, `diff`/`ls` captured to the cache directory) run after the saves.
Every save records whether the file changed, its write time and any dialog.

**Scoring.** The unmodified pinned `DesktopEnv.evaluate()` with a stubbed VM:
one non-FAIL action, the offline file-cache shim for `get_cloud_file` (other
URLs refused), live getters refused. Each candidate is scored in fresh
processes twice; a candidate is scored five times when the two disagree or
when it enters the dependency-flip analysis.

**Verdicts.** `pass` iff score == 1.0; `fail` otherwise; `error` iff
`evaluate()` raised (OSWorld's `run.py` logs and skips such a task, so an
error is neither pass nor fail). Credit (raw score) is kept for
leaderboard-impact statements.

**Dependency sets.** Primary: lock-exact venv. Sensitivity: scoping venv.

## 4. Primary metrics (lock-exact venv, document_model stratum, confirm split)

- **P1 Gold fixed-point false negative.** Unit: task. Population: non-dev
  in-scope tasks with a complete gold (confirm and reserve splits). Event:
  LibreOffice-save(gold) through the reachability stage does not pass. Every
  flip goes to the audit; a flip is a confirmed false negative when the audit
  accepts the saved gold as a correct result. Reported: raw flip share and
  audit-confirmed share with exact Clopper-Pearson 95% intervals.
- **P2 FN per checker family.** Share of admitted should-pass mutants
  (`should_pass_equiv` plus audit-accepted `should_pass_alt_solution`) whose
  verdict is not pass.
- **P3 FP_R per checker family.** Share of admitted `should_fail_violation`
  mutants whose verdict is pass.
- **P4 FP_F per checker family.** Share of admitted `should_fail_extra_change`
  mutants whose verdict is pass, counted only where the audit rejects the file.
  Always reported separately from P3.
- **P5 Task-level escape rate.** Share of confirm tasks with at least one
  admitted FN or FP_R.

A checker family is a metric function (`compare_table` rule types and
`compare_pptx_files` facets are descriptive sub-families). Family rates are the
unweighted mean over tasks of per-task rates (tasks weighted equally; at most
three mutants per task and operator, site seeds 42, 43, 44).

## 5. Secondary metrics

- S1 Dependency flips: candidates whose verdict differs between the two venvs,
  counted only when each venv gives the same verdict on five fresh-process
  scorings.
- S2 Script-writer stratum rates (P2-P4 on that stratum).
- S3 Reachability normalization per operator: share of mutants whose targeted
  edit is absent after the save (operator purity checks re-run on the saved
  file).
- S4 Save timing: share of postconfig saves whose write took longer than the
  0.5 s the VM waits before reading the file.
- S5 Nondeterministic checkers: candidates whose repeated scorings disagree.
- S6 Audit agreement with the a-priori labels, per label class.

## 6. Uncertainty, sample size and minimum detectable effects

- Pooled and family rates: task-cluster percentile bootstrap, 10,000
  resamples, seed 42 (`harness/q2_mutation/stats.py`). Wilson or exact
  intervals only for task-level proportions.
- Family floor: a family rate is inferential only with at least 8 tasks and
  20 admitted mutants; otherwise descriptive. In the confirm split only
  `compare_table` (33 tasks) and `compare_pptx_files` (21 tasks) reach 8.
  No inferential claim is made at the operator × checker cell level.
- Planned size: 120 confirm tasks; about 2,000-3,000 raw mutants before
  deduplication and admission.
- Minimum detectable rate (one-sided α = 0.05, power 0.8, 3 mutants per task
  and operator, intra-task correlation 0.5, null rate 5%): 14.3% at 33 tasks,
  17.0% at 21 tasks, 9.5% at 120 tasks (correlation 0.3 / 0.8: 13.2% / 15.8%
  at 33; 9.0% / 10.2% at 120). Recomputed from the dev-split correlation
  before freezing: FILL-AT-FREEZE.
- Exact one-sided 95% upper bound with zero events: 2.5% at 120 tasks, 8.7%
  at 33, 13.3% at 21; with one event at 120 tasks, 3.9%.

## 7. Admission and quarantine

- `should_fail_violation`: witness names a requirement of the task's spec,
  every operator purity check passes on the saved file, and the targeted edit
  survives the reachability stage.
- `should_pass_equiv`: purity checks pass on the saved file.
- `should_pass_alt_solution`: admitted only after audit acceptance.
- `ambiguous`: never in a rate; counted.
- Duplicates: one mutant per canonical content hash (volatile docProps and zip
  timestamps excluded).
- Every quarantine reason is counted and reported.

## 8. Infrastructure failures (excluded and counted, never relabeled)

LibreOffice open, activation or save failure or timeout; a container failure;
a candidate whose repeated scorings disagree (it moves to S5); a setup or
postconfig step the harness cannot emulate that writes a file the checker
reads (the whole task is excluded and listed). A checker exception is not an
infrastructure failure; it is verdict `error`.

## 9. Audit (decision D9)

- Raters: two model raters from different providers (Anthropic
  `claude-opus-5`, OpenAI `gpt-5.6-sol`; `harness/q2_mutation/raters.py`),
  labelled "model raters" in every result. Prompt `RATER_PROMPT_V1`.
- Blind packet: instruction, initial files, candidate (render, structure and
  a structural difference against the initial files). Never gold, checker
  verdict, score, operator, family, label or witness.
- Sample, disjoint strata in priority order: all `should_pass_alt_solution`
  mutants (cap 150), all label-verdict disagreements (cap 200), 100 random
  agreements, each with its inclusion probability; plus 10% sham items
  (LibreOffice-saved gold, do-nothing; at most two per task); every P1 flip.
- Decision per item: both raters accept → accept; both reject → reject;
  otherwise unresolved, sent to Kevin. Label error uses Hajek weights with a
  task-cluster bootstrap; unresolved items are excluded in the primary estimate
  and counted as label errors in a reported sensitivity bound.
- Human spot check: a stratified sample (max(5, 10%) per stratum plus 5 shams)
  for Kevin. Results state that the human check is pending until it is done.

## 10. Decision rules and kill criteria

Each criterion is checked to be able to fire at the planned sizes.

- **K1 Harness validity (first step after the freeze, before any mutant is
  scored).** On confirm tasks with a complete gold, raw gold must pass and raw
  do-nothing must fail in at least 90% of tasks under the lock-exact venv;
  otherwise stop, fix, and rerun under a new experiment id. (On the dev split
  this check is a pre-freeze harness test.)
- **K2 VM fidelity gate.** At least 80 task-candidate pairs across at least
  three domains run through the corrected injection plan
  (`harness/q2_mutation/vm_injection.py`). A checker family with any
  unexplained disagreement between in-VM and offline verdicts is dropped from
  the headline or the harness is fixed and rerun as a new id.
- **K3 Label validity.** If Cohen's κ between the model raters on real items
  is below 0.6, or a label group's weighted label error has a 95% upper bound
  above 10%, that group is relabeled by Kevin or dropped from the headline.
- **K4 Operator design.** If audited label error exceeds 10% in both the
  should-pass and the should-fail group, stop and redesign under a new id.
- **K5 Normalization.** An operator whose edit the reachability stage erases
  in more than 50% of its mutants is reported only as a normalization finding.
- **K6 Adequacy (negative result).** If at least 93 confirm tasks are
  evaluable, the exact one-sided 95% upper bound of P5 is below 5% (zero
  escapes at 59 or more tasks, at most one at 93 or more), and P1 has at most
  one confirmed flip, publish "adequate under this operator set".
- **K7 Unreliable family.** A family whose P2, P3 or P4 task-cluster 95% lower
  bound exceeds 5% is reported as unreliable for that error type (feasible at
  33 tasks for true rates of about 14% or more).
- **K8 Prior art.** Before drafting, rerun `orx` and keyword search including
  citers of AgentRewardBench and ABC. If a mutation audit of desktop CUA
  checkers has appeared, pivot the note to the reachability, gold fixed-point
  and dependency-drift findings.

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

- Dev-split results (harness validation, P1 on dev tasks, timing).
- Scoping-probe numbers (run split 34/38, F-CELL 12/30, headless round trip
  10/106): pre-reachability, Ubuntu `0ubuntu0.22.04.13` build, headless;
  disclosed, never pooled.
- Every (task, operator family) cell touched by a scoping probe
  (`program/evidence/q2-mutation/harness/probe_touched.json`: 207 tasks;
  E-ZIP/E-META 104, run split 65 cells, F-CELL 33, typo probes 106 cells,
  reverts 52 cells) is reported separately; the mapping from probe ops to
  final operator ids is fixed at freeze (FILL-AT-FREEZE).
- P1 stays confirmatory although a headless round trip of 113 golds was
  probed: that probe used a different save path (headless) and build
  (`0ubuntu0.22.04.13`), and nothing in the harness was tuned on it. P1 is
  also reported separately for probe-touched and untouched tasks.
- Operators added after the freeze.

## 13. Reported regardless of outcome

P1-P5 and S1-S6 with intervals; per-task distributions; every quarantine,
error and infrastructure-failure count with reasons; the excluded-task list;
the dependency-flip table; the save-timing table; the fidelity-gate table;
rater κ, sham accuracy and the pending human check; the scoping-probe numbers
labelled pre-reachability; and the deviations below.

## 14. Deviations from the reviewed plan

- The VM runs Ubuntu's LibreOffice build `0ubuntu0.22.04.4`, not TDF's; the
  save stage runs the VM's own userland instead of a TDF tarball.
- Split seed 42 (the program's seed rule and the shared interface), not
  20261006.
- Experiment id `q2-evaluator-mutation-v1` and this path, per the program's
  shared interface.
- Intent predicates on an independent stack are replaced by spec witnesses,
  operator purity checks on the saved file, and the D9 audit.
- Human raters are replaced by provider-distinct model raters (D9).

## 15. Freeze checklist

- [ ] Replace every FILL-AT-FREEZE value.
- [ ] Dev-split harness validation (gold, do-nothing, gold fixed point,
      determinism, timing) recorded as exploratory evidence.
- [ ] Dev-split intra-task correlation measured; MDE table updated.
- [ ] Spec set and operator catalog hashes recorded; no spec author saw
      checker code or probe output (provenance file).
- [ ] Reviewed by a second agent; lower of two review scores recorded.
