# Do OSWorld's file-state checkers accept equivalent end states? A descriptive mutation audit

Research note, draft of 2026-10-11, revised on 2026-10-12 with the results of R03 part (b) and
of R04. CoTCodec research program, question Q2
(`program/questions/q2-calibrated-cua-instrument.md`), item R03 of the question-renewal dossier
(`program/evidence/2026-10-11/question-renewal/dossier.md`, section 3). Program owner: Kevin Liu.

Repository: <https://github.com/Kevin-Liu-01/cotcodec> (public). Every evidence path below
resolves on `main` at `746d60d2`, the base of this draft's branch `stage0/r03-note`, except
what that branch adds: the note's script, figures and number table
(`paper/checker-mutation-note/scripts/`, `figures/`, `data/`) and the record of the prior-art
check K8 (`program/evidence/2026-10-11/q2-mutation-k8-prior-art/`). The part (b) registration
and run record ([ZR-REG], [ZR]) and decisions D86 and D88 resolve on `main` at `b880275c`, the
base of the revision's branch `stage0/r03-partb-text`. The R04 registration and run record
([NUI-REG], [NUI]) and decision D89 resolve on `main` at `9d320c6e`, the base of the revision's
branch `stage0/r04-text`. The note expands section 6 of the Q2 report draft
(`paper/q2-report/draft.md`), whose first two revisions predate K2 (D79) and the adjudication
(D82); its revision 3 took this note's numbers, its revision 4 adds part (b), and its revision 5
adds R04. Where the two differ, the numbers here are the later ones.

> **Status: DRAFT. Not published, not for circulation.**
>
> - Publishing this note is an outward action reserved to the program owner (D2, D80).
> - It reports candidate defects in OSWorld checkers that have not been disclosed to the OSWorld
>   maintainers (xlang-ai). Whether and how to disclose them is the owner's decision (D2, D80),
>   and it comes before any publication. Any disclosure text uses D72 (iii)'s failure counts
>   (36 of 40 evaluable z-order mutants fail: `compare_pptx_files` 35 of 39 plus
>   `compare_pptx_files_tolerant` 1 of 1) and gives any confirmed count as 30 by both raters,
>   or as 33 after D82's model adjudication, with the D80 label.
> - Every result of the mutation study is **descriptive** (D35). Nothing here is confirmatory.
>   R04's cell and arm readings (section 3.9) come from its own frozen decision rule; they count
>   verdict changes against a paired control and judge none of them.
> - Every audit-dependent number rests on two model raters. The 34 items they split on or both
>   read against the label (the adjudication pool) and the 25-item spot check were answered by
>   an isolated model: **adjudicated by an isolated model on the owner's instruction (D80); not
>   human-validated**. The human spot check that D9 planned is still pending.
> - The registered prior-art check K8 ran on 2026-10-11, after the first draft rather than
>   before drafting as registered, and did not fire (section 6).
> - The offline harness's verdicts were **checked inside real VMs by K2** (D79) on a registered
>   sample of 80 scoring jobs.
> - R03 part (b), the held-out test of the corrected comparator `zinv` on the reserve split,
>   ran on 2026-10-12 under its own frozen addendum (D86, D88). Its outcome is **PASS,
>   descriptive**, on 13 z-order mutants, fewer than the registered 20. It licenses saying that
>   the correction held on reserve documents it was not developed on, at this size; it is not a
>   claim that `zinv` accepts 95% of z-order equivalents (section 3.7).
> - R04, a registered study of whether checker verdicts survive a change of LibreOffice build,
>   locale or save route, ran on 2026-10-11 and 2026-10-12 (D89). Its build and locale arms
>   read DRIFT and its route arm MINOR (section 3.9). **None of its flips is adjudicated.** It
>   scored offline; its K2 label covers the control configuration only.
> - **Blind warning (D9, D82).** The part (b) run's released files name the checker's verdict
>   for every reserve mutant. Whoever does D9's pending human spot check should answer from its
>   blind packets before reading them. No reserve mutant is in the spot check or the
>   adjudication pool, and this note gives only counts for them. R04's analysis files name the
>   checker's verdict per gold task and per S1a end state, and section 3.9 names the golds whose
>   verdict flips; the same order applies to them.
> - The note quotes no OSWorld task document. Task ids are OSWorld's public task identifiers.

## Summary

OSWorld scores many office tasks by comparing the agent's saved file with a reference file. We
asked whether these file-state checkers accept end states that satisfy the instruction and
reject end states that violate it. We edited the reference ("gold") end states of the frozen
confirm split with 64 operators, labelled every edit from a requirement spec written without
seeing any checker, saved each edited file the way the VM's own LibreOffice saves it, and
scored it with OSWorld's unmodified evaluator. Two model raters audited every case where the
checker and the label disagreed, and an isolated model adjudicated the items they split on or
both read against the label.

- **The pptx comparators fail equivalent edits.** Swapping the stacking order of two slide
  shapes that cannot paint the same pixel changes nothing a viewer sees. 36 of 40 evaluable
  mutants of this kind fail their checker (90.0%; task-equal share 91.7%, 81.3-100%):
  `compare_pptx_files` 35 of 39 and `compare_pptx_files_tolerant` 1 of 1. After model
  adjudication (D80) 33 are confirmed and 3 have their label contradicted, all 3 on one task
  whose gold the adjudicator also rejected. Every other should-pass operator gave 0 failures
  (for example 0 of 85 selection changes and 0 of 39 literal-for-formula alternatives in
  spreadsheets).
- **The false negatives sit in `compare_pptx_files` and its tolerant variant.** The
  model-adjudicated (D80) confirmed share is 11.6% (6.4-17.3%) pooled over all 60 evaluable
  tasks, 37.1% (28.3-44.6%) within `compare_pptx_files`, and 85.4% (68.8-97.9%) within the
  z-order operator.
- **Few audited false positives.** 5 of 96 evaluable should-fail mutants pass their checker
  (task-equal 5.9%, 0.8-12.3%). 2 are confirmed violations (2.1%, 0-5.4%); for the other 3 the
  audit says the edit does not violate the task. Probe-touched cells, kept out by registration,
  hold 28 more false-positive events that nobody audited.
- **The gold is not a fixed point of a GUI save.** 4 of the 92 save-exposed golds pass raw but
  fail after a GUI-faithful LibreOffice save (4.35%; exact 95% 1.20-10.76%); 3 of those flips
  are audit-confirmed checker errors (3.26%, 0.68-9.23%).
- **Verdicts are not invariant to the LibreOffice build or the locale (R04, registered; not
  adjudicated).** Re-saved with one factor changed at a time, and with every flip reproduced in
  two confirmation rounds, the 92 golds and S1a's agent end states keep their verdicts under the
  builds up to 24.8, under ja_JP and under a Save As. LibreOffice 25.8 and 26.2 flip 18 and 20
  gold verdicts (19.6%, exact 95% 12.0-29.1%; 21.7%, 13.8-31.6%), mostly `compare_pptx_files`
  passes turning to fails; the de_DE, ar_EG and tr_TR locales flip 3, 4 and 3. The corrected
  comparator reads the same. An image re-hosted with either change cannot keep OSWorld's
  checkers as they are without accepting these flips.
- **The result holds inside the VM.** On the registered K2 sample, 78 of 78 compared pairs give
  the offline verdict in both runs, and all 41 candidate events reproduce.
- **The defect replicates on held-out decks, and the correction held there in a small,
  descriptive test.** On the reserve split's 8 pptx tasks, never used to find the defect or to
  build the fix, `compare_pptx_files` failed 13 of 13 z-order equivalence mutants. The corrected
  comparator `zinv` accepted all 13 (exact one-sided 95% lower bound 0.794) and newly accepted
  none of 15 violation mutants (R03 part (b): PASS, descriptive, below the registered 20
  mutants). The correction held on documents it was not developed on, at this size; this is not
  a 95% acceptance rate.
- **No on-policy consequence is shown.** A corrected comparator changed 0 of 1,808 verdicts of
  two Qwen3.5 policies in the program's S1a run.
- **The audit rests on correlated models.** The two raters agree at Cohen's κ 0.343; the
  adjudicator is the same model as one rater and matched it on all 25 spot-check items. No
  human has validated any label.

## 1. Question

A file-state checker turns an end state into a pass or a fail. On OSWorld that verdict becomes
the benchmark score and, in RL on such tasks, the reward. The study
(`q2-evaluator-mutation-v1`, frozen in ledger row 11 at `65bc2e2`) asks how often
OSWorld-Verified's file-state checkers (a) reject end states that satisfy the task instruction
(false negatives) and (b) accept end states that violate it (false positives), when every
office end state reaches the checker the way it does in the real pipeline, re-saved by the VM's
own LibreOffice [MUT-REG section 1].

Scope: the 205 offline-checkable, web-free tasks of OSWorld-Verified (`test_nogdrive.json`,
361 tasks), split by a seeded draw into dev 32, confirm 120 and reserve 53 tasks [MUT-REG
sections 1-2]. Live-state, web and infeasible tasks are out of scope. Everything below is on the
confirm split unless it says otherwise.

Since D35 the study answers this descriptively: it lists and counts candidate checker errors on
blind-labelled mutants, each with its audit decision, and states no confirmatory rate.

This note completes R03 of the question-renewal dossier, whose corrected question has three
parts [DOSSIER, section 3]. Part (a), whether mutants saved inside the certified VM get the
offline verdict, is answered by K2 (section 3.6). Part (b), whether the corrected comparator
`zinv` holds on the held-out reserve split, ran under its own frozen addendum and passed,
descriptively (section 3.7). Part (c), operator families for the pool's non-office checkers,
would need a new registration and has not been written. The adjudication the dossier left to
the owner was done by an isolated model under D80 (section 2.5). A separate registered item of
the dossier, R04, asks whether the checkers' verdicts survive a change of LibreOffice build,
locale or save route (section 3.9).

## 2. Method

### 2.1 Targets and mutants

A mutation target is one gold file of a task with a complete gold, of a type an operator family
handles. The confirm split has 68 targets on 67 tasks (32 xlsx, 22 pptx, 13 docx, 1 text);
43 confirm tasks have no complete gold and get no mutant [MUT-REG section 6]. The catalog
`q2-mut-operators-v1` has 64 operators in five document families (xlsx, docx, pptx, text,
config), each operator nominally in one of four classes [MUT-REG Appendix A]:

- **Equivalence** edits change nothing the task constrains (document properties, zoom, the
  selected cell, a shape nudged by less than LibreOffice's rounding, the stacking order of
  shapes that cannot overlap).
- **Alternative solutions** reach the requested result another way (a literal in place of a
  formula, absolute references, a named style in place of direct formatting).
- **Violations** break a requirement (a changed value, dropped character formatting, a deleted
  bound shape).
- **Extra changes** alter something the task did not ask for.

Operators work through LibreOffice's document model, or splice characters of text files. They
never read a task config, a checker or a verdict [MUT-REG section 3].

### 2.2 Blind labels

Each mutant's label comes from a requirement spec, never from a checker. The 205 specs (598
requirements) were written by a Claude model (Claude Opus 5.5) from sanitized task exports,
without reading any checker or evaluator code; no spec names any of the 117 checker functions
scanned, and the author model may have seen the public OSWorld repository in pretraining
[MUT-REG sections 2 and 9; `program/evidence/q2-mutation/integration/blind-spec-provenance.json`].
Witness rules map an edit and the spec to one of `should_pass_equiv`,
`should_pass_alt_solution`, `should_fail_violation`, `should_fail_extra_change` or
`ambiguous`; a nominal alternative solution whose aspect the spec pins becomes a violation, for
example [MUT-REG Appendix A]. Ambiguous mutants are counted, never audited or rated.

The z-order operator (`pptx.eq.zorder_nonoverlap`) is restricted so it cannot change what is
drawn: it swaps two shapes only when every shape between them has a known frame and neither
shape comes within 2 mm of the other or of any shape stacked between them [MUT-REG Appendix A;
D27].

### 2.3 Building, saving and scoring

A mutant is the raw gold with one operator recipe applied and one LibreOffice save, so a mutant
and its null mutant (the gold saved once, unedited) are each one round trip from the gold. A
GUI-faithful save stage then opens every office candidate in non-headless LibreOffice under
Xvfb, in a copy of the VM's own profile and build (LibreOffice 7.3.7.2), and replays the
task's postconfig: window activation, keystrokes, sleeps and conversions. The unmodified
pinned `DesktopEnv.evaluate()` scores each saved candidate offline, twice in fresh processes,
under each of two dependency sets [MUT-REG section 3].

A mutant is **evaluable** when it was admitted, saved, scored, kept its edit through the save,
its null mutant passes, its repeated scorings agree and its label is not ambiguous [MUT-REG
section 7]. A **candidate** is an evaluable mutant on which checker and label disagree: a
should-pass mutant that fails (false-negative candidate) or a should-fail mutant that passes
(false-positive candidate).

Table 1. From plan to population [MUT; `build-summary.json`; `audit/sample/sample-summary.redacted.json`].

| Stage | Mutants |
|---|---:|
| Planned | 1,289 |
| Admitted (build-time purity passed, duplicates removed) | 1,232 |
| Evaluable (both dependency sets) | 888 |
| Evaluable outside probe-touched cells, on 60 tasks (the population) | 444 |
| of which `should_pass_equiv` / `should_pass_alt_solution` | 255 / 93 |
| of which `should_fail_violation` / `should_fail_extra_change` | 91 / 5 |

Before the freeze, exploratory scoping probes had shown how some checkers treat some edits.
Every (task, operator) cell a probe touched is outside the population, because its result is
not blind; its events are counted per checker family and never audited [MUT-REG section 12].

The pipeline's own checks were clean. The harness check K1 passed (raw gold passes and raw
do-nothing fails on 70 of 74 confirm tasks, against a 90% line). No dependency-set
disagreement, no nondeterministic checker and no save failure occurred; 23 of 1,232 admitted
mutants lost their edit in the save, and 96 of 1,300 saves took longer than the 0.5 s the VM
waits before reading the file (slowest 1.20 s). 7 of 68 targets have a saved null mutant that
fails its own checker, and their mutants leave the population [MUT, S1-S7].

### 2.4 The audit

Every candidate, every alternative solution the checker passes (the gate for MUT-P2, below),
every gold flip of MUT-P1 and 40 shams were audited: a census of 178 items, not a sample
[MUT-AUD, "Sample"]. The shams are 33 saved golds, one for every audited task, and 7 saved
do-nothing states. Each item became a blind packet: the instruction, every starting and
end-state file with a structure listing, a structural difference against the saved starting
file, and 100-dpi page renders by the VM's own LibreOffice [MUT-REG section 9]. A packet never
shows the gold, the checker, its verdict, the operator or the label. The listings come from
the operators' own snapshot model, not from the libraries the checkers use, so the raters do
not read files through the checkers' parsers. They do share the operators' view: a collateral
change that the snapshot model does not record is missing both from the packet and from the
operators' purity checks, and the page renders are the raters' only independent channel.

Two model raters answered accept, reject or unsure for every item (D9, D23):

- **Claude** (`claude-opus-5-5`), one fresh agent per item through the Claude Code agent
  harness, reading only its own item directory with the Read tool (D25, D27). A registered
  transcript audit voids any rating whose agent read or ran anything else (D34, D35, D38).
  177 ratings passed and 1 was voided.
- **Qwen3.6-35B-A3B**, self-hosted, seeded, thinking on, the independent rater (D23, D34). It
  answered all 178 items; 6 hit the token limit while thinking and count as unsure. It used
  0.365 GPU-h.

A decision is accept or reject when both raters agree, and unresolved otherwise. Items where
the raters split, gold shams they split on, and items where both contradict the label form the
**adjudication pool** of 34 items. A stratified **spot check** of 25 items (7 also in the pool;
52 distinct) was set aside as D9's human validation of the model raters.

### 2.5 The adjudication

The registered adjudicator was the owner. On 2026-10-11 Kevin delegated his pending research
decisions (D80), and the pool and the spot check were answered by fresh, isolated model
adjudicators, one per item, blind to both raters, under the raters' own isolation template.
This is a disclosed deviation from D9: the spot check was meant to be human, and it is not
human here. A first run was void, because its agents were not started with the registered
template and all of them used a forbidden tool; none of its answers is used (D81). The
orchestrating session saw run 1's numbers, and the run-2 collector saw them in a commit
message; D81 and the record disclose both. The record is the second run [ADJ]:

- `claude-opus-5-5`, the same model as the Claude rater; 52 transcripts, 52 passing the
  registered isolation audit and 0 void. The agents used 711 Read calls and 52 structured
  answers, and opened 503 of 506 page images.
- The pool split 17 accept and 17 reject; the spot check 19 accept and 6 reject.
- Two sensitivities fixed before any answer existed (D81): the same items answered by
  `claude-fable-5-1`, a model that is neither rater's (independence), and the 12 items whose
  packets show the differ's added-sheet marker answered with one fixed explanatory sentence
  (notation).

### 2.6 VM fidelity (K2)

Scoring ran offline, in a harness built from the VM's extracted files. The registration's K2
gate compares, for a sample of scoring jobs drawn before any verdict existed, the verdict
inside a freshly booted certified VM with the offline verdict for the same candidate bytes
[MUT-REG section 10]. Its executor did not exist at the freeze, so the first analysis carried
the label "offline harness, VM fidelity unverified". The K2 addendum
(`q2-evaluator-mutation-v1-k2`, ledger row 17) supplied it: the candidate is uploaded into the
VM after the task's own setup, opened and saved by the VM's own LibreOffice, and scored by the
unmodified evaluator [K2-REG section 1]. The sample is 80 jobs, 20 per domain, on 41 tasks, 73
mutants and 7 null mutants. K2-C, a descriptive companion, runs all 41 candidate events of the
campaign. Every pair runs twice.

### 2.7 The frozen analysis and why it is descriptive

The registered rater-agreement rule was κ ≥ 0.6 between the two raters. On the development
audit κ was 0.066 under the registered ingest, and 0.575 with a harness relay turn excepted
(a byte-identical copy of the session request the agent harness placed before resumed raters'
tasks). Both are below 0.6. D34's exit then fired: no other rater was tried, the per-family
and pooled rates (MUT-P2 to MUT-P5) left the confirmatory headline, and D35 froze the study as
a pre-specified descriptive protocol [ADJ-AN, `exclusions.d34_dev_exit`]. The analysis is code
(`harness/q2_mutation/analysis.py`), fixed at the freeze. It ran after the model audit, again
with the K2 report and again with the adjudications, each time from a git archive whose code
equals the frozen pins. Each later run differs from the one before only through its new input,
which a byte-for-byte control run confirms [K2; ADJ, "Controls"].

Every share is task-equal: each task's share of its evaluable mutants with the event, averaged
over tasks with every task weighted equally, because mutants of one task share checker code
paths. Intervals are 95% task-cluster percentile bootstrap intervals (10,000 resamples, seed
42), and exact Clopper-Pearson intervals for task-level proportions [MUT-REG section 4]. No
share is compared with a threshold. A candidate is **confirmed** when the audit agrees with its
label (a false-negative candidate decided accept, a false-positive candidate decided reject)
and **label contradicted** when it decides the opposite.

## 3. Results

### 3.1 The pptx comparators fail equivalent shape reorders

In a PowerPoint file, the order of shapes in a slide's shape tree is their stacking order.
`compare_pptx_files` zips the two decks' top-level shapes in that document order and compares
the pairs [ZINV]. A constructed illustration (not a task): a slide holds a title, a text box on
the left half and a picture on the right half, more than 2 mm apart. Swapping the text box and
the picture leaves the rendered slide unchanged, but the checker now compares the reference's
text box with the agent's picture, and fails.

D72 (iii) fixed the counts for any text: **36 of 40 evaluable z-order equivalence mutants fail
their checker: `compare_pptx_files` 35 of 39, `compare_pptx_files_tolerant` 1 of 1.** Before
adjudication, 29 of the 35 were confirmed by both raters and 6 were unresolved, and the
tolerant one was confirmed: 30 confirmed in all. The raw share is 90.0%; the task-equal share
is 91.7%, because the estimand weights the 16 tasks equally (S11). The 4 evaluable mutants the
checker passes are all on `compare_pptx_files`. Of the 59 z-order mutants planned, 13 sit on
targets whose null mutant fails, 3 have ambiguous labels and 3 were not admitted [DER].

After model adjudication (D80, D82), **33 are confirmed and 3 are label contradicted**. The 3 are all of
task `5c1a6c3d`'s candidates; the adjudicator also rejected that task's saved gold, so it is a
gold-defect task (section 3.3), and the 3 are reported as gold defects. The 3 newly confirmed
candidates are on tasks `57667013`, `70bca0cc` and `eb303e01`. All 6 were rater splits: the
3 newly confirmed had Claude accept and Qwen reject, the 3 contradicted had Claude reject and
Qwen accept, and the adjudicator, the same model as the Claude rater, sided with the Claude
rater on all 6 [ADJ, "Answers"]. The adjudicated z-order reading therefore leans on that model
(section 4).

Table 2. False-negative candidates and confirmed shares, task-equal, in the population [ADJ-AN
`checker_candidates.false_negative`; ADJ, "What changed"]. Before adjudication an unresolved
candidate counts as not confirmed. The "after" column is adjudicated by an isolated model on
the owner's instruction (D80); not human-validated.

| Scope | Evaluable mutants (tasks) | Checker fails | Candidate share | Confirmed share before | Confirmed share after (D82) |
|---|---:|---:|---|---|---|
| z-order operator | 40 (16) | 36 | 91.7% (81.3-100%) | 77.1% (61.5-90.6%) | 85.4% (68.8-97.9%) |
| `compare_pptx_files`, all should-pass | 85 (16) | 35 | 40.2% (32.9-46.3%) | 33.5% (24.8-41.7%) | 37.1% (28.3-44.6%) |
| all families, all should-pass | 348 (60) | 36 | 12.4% (7.2-18.3%) | 10.6% (5.8-16.2%) | 11.6% (6.4-17.3%) |

**Every other should-pass operator gave no failure.** No equivalence operator other than the
z-order swap and no alternative solution (0 of 93) fails its checker. Per operator:
`xlsx.eq.view_selection` 0 of 85 (29 tasks), `pptx.eq.subvisible_nudge` 0 of 46,
`xlsx.alt.literal_for_formula` 0 of 39, `xlsx.eq.view_zoom` 0 of 37, `docx.eq.view_zoom` 0 of
36, `xlsx.alt.absolute_refs` 0 of 34, and smaller cells [ADJ-AN]. Per family, `compare_table`
has 0 of 218 should-pass mutants on 30 tasks. Figure 1 shows every operator with an evaluable
mutant in the population (25 of the catalog's 64).

![Figure 1](figures/fig1-operator-shares.svg)

Figure 1. Per-operator candidate share (filled circle) and adjudicated confirmed share (open
diamond) with 95% task-cluster bootstrap intervals, in the population. Left: should-pass
operators, where a candidate is a failed verdict. Right: should-fail operators, where a
candidate is a pass. Labels give candidates over evaluable mutants and the number of tasks
("t"). Generated by `scripts/figures.py` from the adjudicated analysis. Confirmed shares are
adjudicated by an isolated model on the owner's instruction (D80); not human-validated.

![Figure 2](figures/fig2-zorder-stages.svg)

Figure 2. The z-order mutants through each stage: planning and evaluability [DER], the offline
checker, the two model raters [MUT `summary.json`], the adjudication [ADJ-AN], the in-VM rerun
(K2-C) [K2] and the corrected comparator `zinv` [ZINV-VAL]. Generated by `scripts/figures.py`.
The adjudication stage is adjudicated by an isolated model on the owner's instruction (D80);
not human-validated.

### 3.2 False-positive candidates

5 should-fail mutants pass their checker, out of 96 evaluable on 26 tasks (task-equal candidate
share 5.9%, 0.8-12.3%). All 5 carry a violation label; no extra change passes outside
probe-touched cells (0 of 5).

Table 3. False-positive candidates [ADJ-AN `checker_candidates.false_positive.events`]. The
adjudicator column and the readings are adjudicated by an isolated model on the owner's
instruction (D80); not human-validated.

| Task | Operator | Checker family | Raters | Adjudicator (D82) | Reading |
|---|---|---|---|---|---|
| `358aa0a7` (2 mutants) | `pptx.alt.textbox_for_placeholder` | `compare_pptx_files` | both accept | accept (pool and spot check) | label contradicted |
| `70bca0cc` | `pptx.viol.drop_char_format` | `compare_pptx_files` | both reject | reject (spot check) | confirmed |
| `a434992a` | `pptx.viol.drop_char_format` | `compare_pptx_files_tolerant` | both accept | accept (pool and spot check) | label contradicted |
| `d53ff5ee` | `docx.viol.text_edit` | `compare_docx_files` | both reject | reject (spot check) | confirmed |

The confirmed share is 2.1% (0-5.4%), from 2 events. The textbox-for-placeholder mutants are
nominal alternative solutions that the spec's witness rule turned into violations; both raters
and the adjudicator read them as acceptable, so the label, not the checker, looks wrong there.
Adjudication changed nothing in this table: the 3 label-contradicted items were concordant
contradictions in the pool, and the adjudicator upheld the raters on all 3.

Probe-touched cells hold 28 more false-positive events (`compare_table` 12,
`compare_docx_tables` 7, `compare_docx_images` 6, `compare_docx_files` 3), none audited
[ADJ-AN `checker_candidates.probe_touched_events`]. The registration keeps them out of the
candidates because they are not blind, not because they are few. Some may be label errors, as
3 of the 5 audited candidates were.

### 3.3 Gold-defect tasks

A task whose saved gold sham is decided reject is a gold-defect task (D34): the audit says the
reference itself does not satisfy the instruction. Of the 33 gold shams, the raters split on
4, all rejected by Claude. The adjudicator rejected 3: `5c1a6c3d` (`compare_pptx_files`) and
`881deb30` and `8e116af7` (both `compare_table`); it accepted `035f41ba` [ADJ, "What
changed"]. There were none before adjudication.

Their consequences are the main thing adjudication changed:

- The 3 z-order candidates of `5c1a6c3d` became label contradicted (section 3.1). Mutants of a
  rejected gold are judged against a reference the audit does not accept, so they say little
  about the checker.
- All 10 alternative solutions on `881deb30` (6) and `8e116af7` (4) were rejected. The
  alternative-solution gate went from 72 accepted, 3 rejected and 18 unresolved to 82 accepted,
  11 rejected and 0 unresolved; outside gold-defect tasks, 82 of 83 alternative solutions are
  accepted.
- The equivalence label error (K3) fell from 0.167 to 0.000 (33 items on 15 tasks, exact upper
  bound 0.087), and K4 no longer fires. K3 still fires, through κ alone.

These three calls rest on Claude-family judgment: the adjudicator sided with Claude, not Qwen,
on 3 of the 4 split gold shams. The record cannot separate a gold defect from a shared
Claude-family reading [ADJ, "What the result licenses"].

### 3.4 A GUI-faithful save flips reference golds (MUT-P1)

MUT-P1, a pre-specified replication, asks whether a gold that passes raw still passes after the
GUI-faithful save. The population is the 92 golds that place an office file the save rewrites
(confirm 67, reserve 25) [ADJ-AN `P1`]; 87 of them pass raw (63 confirm, 24 reserve) [DER]:

- 4 pass raw and fail after the save (4.35% of the 92; exact 95% 1.20-10.76%): `30e3e107`,
  `9ec204e4` and `b8adbc24` (confirm) and `3a7c8185` (reserve).
- 3 flips are audit-confirmed checker errors (3.26%; 0.68-9.23%): both raters accept the saved
  gold of `3a7c8185`, `9ec204e4` and `b8adbc24` as still correct.
- Both raters reject the saved gold of `30e3e107`: the save changed its content, so that flip
  is not a checker error.

No P1 flip was in the adjudication pool, so adjudication changes none of this. The measurement
replicates an earlier headless round trip, a different save path, that flipped 7 of 63 confirm
golds and 1 of 26 reserve golds [MUT-REG section 4]. A gold that does not survive the save the
pipeline itself applies means an agent that produces exactly the reference file can still fail.

### 3.5 Exploratory rates (MUT-P2 to MUT-P5)

These left the confirmatory headline under D34 (i) and are reported with the same tables
[ADJ-AN]:

- **MUT-P2** (false negatives per family; equivalence mutants plus the alternative solutions
  the audit accepted): 12.4% (7.2-18.3%) on 337 mutants and 60 tasks. Without the gold-defect
  tasks' equivalence mutants (the registered sensitivity) it is 12.2% (6.7-18.1%; 323 mutants,
  57 tasks). `compare_table` is 0 of 207 on 30 tasks (zero-event bound 9.5%); in the
  sensitivity 0 of 199 on 28 tasks, bound 10.1%. Adjudication moved the population from 327 to
  337, not the rate.
- **MUT-P3** (violations passed): 6.1% (0.8-13.1%) on 91 mutants and 25 tasks.
- **MUT-P4** (extra changes passed and rejected by the audit): 0 of 5 on 2 tasks.
- **MUT-P5** (tasks with any false-negative or violation event): 17 of 60, 28.3% (exact
  17.5-41.4%).

### 3.6 Inside the VM (K2)

The frozen K2 job ran once (Slurm job 1186, CPU only, 65 minutes) from an export of the freeze
commit, with no other Slurm job running. Outcome: **VERIFIED** (D79) [K2]:

- The fitness gate passes: 2 of 80 pairs were excluded (at most 8 allowed), both VM
  infrastructure failures on task `51f5801c`, where a LibreOffice window that the task's setup
  had opened did not quit in time.
- All 78 compared pairs give the offline verdict in both runs (41 pass, 37 fail): no difference,
  so none needed one of the four registered explanations and no family was dropped.
- K2-C: all 41 candidate events reproduce in both runs. The 36 false negatives fail in the VM
  and the 5 false positives pass, as offline.
- `compare_pptx_files_tolerant` has no pair in the K2 sample and is reported as not covered;
  its 2 candidate events reproduce in K2-C.

Table 4. K2 pairs compared per checker family [K2 `k2-summary.json`].

| Family | Pairs | Agree in both runs | Excluded |
|---|---:|---:|---:|
| `compare_table` | 27 | 27 | 0 |
| `compare_pptx_files` | 23 | 23 | 0 |
| `compare_docx_files` | 11 | 9 | 2 |
| `compare_line_spacing` | 6 | 6 | 0 |
| `compare_docx_images` | 6 | 6 | 0 |
| `check_tabstops` | 3 | 3 | 0 |
| `evaluate_strike_through_last_paragraph` | 2 | 2 | 0 |
| `compare_docx_tables` | 1 | 1 | 0 |
| `compare_csv+compare_table` | 1 | 1 | 0 |

With K2's report, the analysis label became "VM fidelity checked (K2)"; nothing else in the
analysis changed.

### 3.7 A corrected comparator, validated where it was built and checked on held-out decks (descriptive)

`compare_pptx_files_zinv` realigns the agent deck's shapes to the reference order only where
the swapped shapes are apart by the operator's own rule, then runs the original comparator with
the task's options, so a visible stacking change still fails [ZINV]. It was validated on CPU on
the stored confirm campaign: 291 items on the 21 tasks whose every metric is
`compare_pptx_files`, namely every evaluable mutant (249, on 16 tasks), 21 golds and 21
do-nothing states [S1A-REG section 3.1, item 8; ZINV-VAL; DER]:

- It passes all 29 then-confirmed z-order false negatives, and all 6 then-unresolved ones.
  After model adjudication (D80) 3 of those 6 are confirmed and 3 are label contradicted, all
  on gold-defect task `5c1a6c3d` (section 3.1), so `zinv` also passes 3 mutants of a gold the
  adjudicator rejected.
- The 256 other items keep the original verdict, including every should-fail mutant (113 that
  the original rejects stay rejected, 3 that it passes stay passed) [DER].
- The first two versions failed the gate (0 of 29, then 26 of 29), and each fix came from the
  confirmed mutants that failed. The 29 are therefore a development set as much as a gate
  [S1A-REG section 3.1, item 8].
- `compare_pptx_files_tolerant` is not corrected.

Those runs validate `zinv` only on the split it was built for. R03 part (b) asks whether it
accepts at least 95% of held-out z-order mutants on the reserve split while accepting no
violation that the original rejects [ZR-REG section 1].

The reserve split has 28 targets, 8 of them pptx; they sit on 8 tasks, and no mutant of the
frozen operators had been built on any of them. A frozen addendum,
`q2-zinv-reserve-validation-v1` (ledger row 20), built, saved and scored their mutants with the
parent's frozen operators and pipeline, then rescored every item with the original comparator
and with `zinv` [ZR-REG section 5]. Condition A asks that `zinv` accept at least 95% of the
evaluable z-order equivalence mutants; condition B, that no violation mutant fail under the
original and pass under `zinv`. The reading is descriptive below 20 mutants or 8 tasks (O4)
[ZR-REG section 6]. The registered run, CPU only, gave **PASS, descriptive** [ZR; D88]:

- **Condition A holds.** `zinv` accepted 13 of 13 evaluable z-order equivalence mutants, on all
  8 tasks. The exact one-sided 95% lower bound on its acceptance is 0.794 per mutant (exact
  two-sided interval 0.753-1.000) and 0.688 per task (8 of 8 tasks with every z-order mutant
  accepted).
- **Condition B holds.** Of 15 violation mutants on 5 of the tasks, `zinv` newly accepted 0. The
  exact one-sided 95% upper bound on the new-accept rate is 0.181 per mutant and 0.451 per task.
  The original failed all 15, and so did `zinv`.
- **Why descriptive.** The 13 z-order mutants are fewer than the registered 20; the 8 tasks meet
  their floor of 8. The registration expected a mean of 19.5 [ZR-REG section 4]. The frozen
  operators planned 13 z-order mutants on these targets, and all 13 were evaluable [ZR].
- **The defect replicates.** The original `compare_pptx_files` failed 13 of 13 of the same
  mutants, on tasks and documents never used to find the defect or to build the fix. This is a
  held-out replication of section 3.1's finding, and it is descriptive.
- **Nothing else moved.** The 93 other items (the other equivalence, extra-change and violation
  mutants, 8 saved golds and 9 saved do-nothing states) kept their registered verdict under
  `zinv`, and `zinv` raised no error. None of the 106 rows was invalid: each fresh original
  scoring reproduced the registered verdict, and no job's files changed during the rescoring.

What this licenses, by the addendum's section 7: the correction held on reserve documents it
was not developed on, at this size. It is not a claim that `zinv` accepts at least 95% of
z-order equivalents in general: a PASS bounds acceptance only from below, here at 0.794 per
mutant. "Held out" means unseen by `zinv`'s development; the reserve decks come from the same
OSWorld pool as the confirm decks. The result is offline (K2 covered the confirm sample only),
and it rests on the operators' labels: no rater, model or person read a reserve mutant.
`compare_pptx_files_tolerant` has no reserve task and is still not corrected
[ZR-REG section 12].

The addendum also states what the test can and cannot show [ZR-REG section 1]. `zinv` moves a
shape only past shapes that are apart by the operator's own rule, the rule that also decides
which swaps the operator builds. On a correct implementation, every operator-built z-order
mutant whose deck is otherwise unchanged therefore passes by construction. What condition A
tests is the implementation's pairing of shapes on documents it was not developed on (its
development fixes were for LibreOffice's save rounding, empty text runs and identical
pictures); condition B tests that the realignment never hides a real violation. A PASS
therefore does not test the idea behind the correction, whether the shared rule picks out
exactly the reorders a viewer cannot see.

**Blind warning (D9, D82).** The run's released files (`release/zinv-rows.json`,
`judgement.json` and the campaign's verdict files) name the checker's verdict for every reserve
mutant. D9's human spot check is still pending; whoever does it should answer from its blind
packets before reading those files. No reserve mutant is in the spot check or the adjudication
pool, and this section gives only counts [ZR].

### 3.8 What the defect did on policy

S1a ran Qwen3.5-4B and Qwen3.5-9B on two certified harnesses (screenshot only, 15 steps) over
113 tasks and scored 1,808 episodes with no infrastructure loss [S1A]. Offline rescoring of
the final states with `zinv` in place of `compare_pptx_files` (72 episodes per job, 288 in
all) changed **0 of 1,808 verdicts**, and 0 of the 512 primary ones [S1A-RESC]. Not every
final state replays offline: 16 secondary verdicts, all of the live-state task `53ad5833`,
kept their live scores, and one metric-exception episode scored 0 by the registered merge
rule; their checkers are `compare_config` and `compare_images`, so no `compare_pptx_files`
episode is among them [S1A; S1A-RESC; MUT `controls/`]. For these two policies at 15 steps,
the reorder defect moved no outcome. A stronger agent that rebuilds or reorders slide shapes
could meet it; S1a does not measure that.

### 3.9 Verdicts under another LibreOffice build, locale or save route (R04, registered)

Everything above holds the environment fixed: the VM's own LibreOffice, the en_US locale and a
GUI Ctrl+S save. R04 (`r04-checker-nuisance-invariance-v1`, ledger row 18) asks whether a
checker gives the same verdict on a fixed end state when that environment changes in ways that
should not matter to the task [NUI-REG section 1]. A changed verdict shows a checker that is not
invariant to the factor on that end state, whatever the cause; R04 does not ask whether the
changed verdict is right. Its readings come from its own frozen decision rule.

**Blind warning (D9).** This section names golds whose verdict flips, and R04's analysis files
name the checker's verdict per gold task and per S1a end state. Whoever does D9's pending human
spot check should answer it from its blind packets before reading either [NUI].

The design [NUI-REG sections 4-9]:

- **End states.** The 92 save-exposed golds of MUT-P1 (section 3.4) and 461 end states that S1a's
  agents saved: all 270 states whose every episode passed, on 32 tasks; 180 sampled failing
  states; and 11 mixed ones.
- **Three arms, one factor at a time.** The control is this study's save stage unchanged (the
  VM's build, en_US, Ctrl+S). The build arm swaps in five TDF builds: 7.3.7.2, 7.6.7.2, 24.8.7.2,
  25.8.7.3 and 26.2.6.2. The locale arm sets de_DE, ar_EG, ja_JP or tr_TR for the desktop and
  LibreOffice, with the interface language kept en-US. The route arm saves with a Save As in the
  document's own format, or with a headless same-format conversion.
- **An adaptation.** Builds from 7.6 on title their windows with an em dash, so the window
  activation in OSWorld's postconfig fails as written. The save stage then retries with the em
  dash, as it did for all 553 items in every Ctrl+S and Save As cell of those builds [NUI-REG
  section 4.4; NUI].
- **Paired verdicts, confirmed twice.** Each item's verdict in a cell is paired with its verdict
  in the control. A discordance counts only if two confirmation rounds, each re-saving and
  re-scoring the item under both, reproduce both verdicts.
- **Gates.** V1: the control's gold verdicts must equal this study's frozen control runs (at most
  one difference). V2: a second run of the control, in its own session, must show no confirmed
  discordance.
- **Rule** [NUI-REG section 9]. A cell reads DRIFT if at least 3 golds or 3 S1a tasks flip,
  INVARIANT if none does and MINOR otherwise; an arm reads DRIFT if any of its cells does. The
  pinned checker is primary, and `zinv` gets the same tables.

The registered run took 24 CPU-only jobs, every one finished on its first attempt, in 10.27
lane-hours and 0 GPU-h [NUI; D89]. Every cell saved all 553 items. **V1 passes** (92 of 92
control gold verdicts equal the frozen ones) and **V2 passes** (0 discordances). Both rounds
reproduced every discordance of the main run (108 items under 11 cells), so none is unstable or
pending.

Table 5. Readings per primary cell, pinned checker [NUI `analysis.json` `pinned.cells`,
`pinned.arms`]. A flip is a confirmed discordance with the paired control; an S1a task counts
if any of its passing states (270 in all) flips. Intervals are exact (Clopper-Pearson) 95%. No
flip is adjudicated.

| Arm (reading) | Level | Cell reading | Golds flipped (of 92) | S1a tasks flipped (of 32); pass states | Families of the flipped golds |
|---|---|---|---|---|---|
| build (DRIFT) | TDF 7.3.7.2, 7.6.7.2, 24.8.7.2 | INVARIANT | 0 | 0; 0 | |
| | TDF 25.8.7.3 | DRIFT | 18 (19.6%, 12.0-29.1%) | 6 (18.8%, 7.2-36.4%); 67 | `compare_pptx_files` 17, `compare_table` 1 |
| | TDF 26.2.6.2 | DRIFT | 20 (21.7%, 13.8-31.6%) | 6 (18.8%, 7.2-36.4%); 67 | `compare_pptx_files` 18, `compare_table` 2 |
| locale (DRIFT) | de_DE | DRIFT | 3 (3.3%, 0.7-9.2%) | 1 (3.1%, 0.1-16.2%); 5 | `compare_table` 3 |
| | ar_EG | DRIFT | 4 (4.3%, 1.2-10.8%) | 2 (6.3%, 0.8-20.8%); 6 | `compare_table` 3, `compare_pptx_files` 1 |
| | ja_JP | INVARIANT | 0 | 0; 0 | |
| | tr_TR | DRIFT | 3 (3.3%, 0.7-9.2%) | 1 (3.1%, 0.1-16.2%); 5 | `compare_table` 3 |
| route (MINOR) | Save As, own format | INVARIANT | 0 | 0; 0 | |
| | headless conversion | MINOR | 1 (1.1%, 0.0-5.9%) | 1 (3.1%, 0.1-16.2%); 7 | `compare_table` 1 |

- **Builds.** The builds up to 24.8 change no verdict. Under 25.8 and 26.2 the flipped golds are
  mostly `compare_pptx_files` golds that go from pass to fail, and all 67 flipped S1a pass states
  are `compare_pptx_files`. The same golds flip in the secondary cells that combine each build
  with the other two routes, so the flips do not come from the save route. One flip goes the
  other way: the reserve gold `3a7c8185`, one of MUT-P1's flips, fails in the control and passes
  again under both builds.
- **Locales.** de_DE and tr_TR flip the same three `compare_table` golds (`21df9241`,
  `4f07fbe9`, `7e287123`) and five pass states of task `4f07fbe9`, and turn one failing state of
  task `a01fbce3` to pass. ar_EG flips those three golds and five states, plus the
  `compare_pptx_files` gold of `5c1a6c3d` and one pass state of that task. ja_JP flips nothing.
  Each of the three `compare_table` golds places a CSV export of its sheet beside the workbook.
  The save leaves that CSV byte for byte as placed under the control and ja_JP, and rewrites it
  with other bytes under de_DE, ar_EG and tr_TR (score rows, `save.outputs`; read for this
  note). A conversion is where the registration expected any locale flip [NUI-REG section 16],
  and its dev smoke traced a de_DE flip to decimal commas in such an export [NUI-REG
  section 15]. R04 keeps digests, not documents, so this locates the change without explaining
  it.
- **Routes.** The Save As changes nothing. The headless conversion flips one gold (`4188d3a4`,
  `compare_table`, pass to fail) and seven pass states of that task, and turns three failing
  states of task `1334ca3e` to pass.
- **`zinv` reads the same.** The corrected comparator gives the same reading, with the same
  counts, in every cell and arm [NUI `zinv`]. None of these flips is a stacking-order change
  that the correction absorbs.
- **The control.** Against the unsaved golds it flips the same 4 of 92 golds as MUT-P1
  (section 3.4); against S1a's captured states, 1 of 270 passing and 3 of 180 failing states.
- **VM fidelity.** Rerun with K2's report, the analysis changes only its label, to "VM fidelity
  checked (K2)". K2 compared the offline save stage with the VM in the control configuration
  only, so on every other cell the label means that the cell's paired control is VM-checked,
  not the cell itself [NUI-REG section 2.1; NUI `analysis-k2.json`].

**The gold-defect task.** ar_EG flips the gold of `5c1a6c3d`, the task whose saved gold the
model adjudicator rejected (section 3.3; adjudicated by an isolated model on the owner's
instruction (D80); not human-validated). Builds 25.8 and 26.2 flip that gold too. A flip of a
gold the audit does not accept says little about the checker; ar_EG's three other flipped golds
alone meet the DRIFT threshold, so its reading does not rest on this task.

**What the readings license** [NUI-REG section 9; D89]. DRIFT names, for 25.8, 26.2, de_DE,
ar_EG and tr_TR, at least three golds or three S1a tasks whose verdict the level changes
reproducibly. An OSWorld image re-hosted with LibreOffice 25.8 or 26.2, or a desktop under one
of those three locales, therefore cannot keep OSWorld's checkers as they are without accepting
these flips; builds after 26.2 were not tested. INVARIANT (the TDF builds up to 24.8, ja_JP and
the Save As) bounds that level's gold discordance rate below 3.20% and its S1a task rate below
8.94% (exact one-sided 95%): a bound at these sizes, not a proof of invariance. MINOR lists the
headless conversion's one gold and one task.

**What they do not license:**

- Whether any flip is a checker defect or a real change in the document. No rater, model or
  person has read a flipped file, and none of the flips is adjudicated.
- Anything about agents in a localized desktop. The interface language stayed en-US, the
  keyboard layout stayed US, and no agent ran.
- Builds, locales or routes other than the registered ones, Windows or macOS LibreOffice, or
  another OSWorld revision.
- Derived files on S1a's end states: R04 re-saved the documents the checker reads directly, so
  a postconfig export such as a CSV is tested on the golds only.
- What a re-hosted VM would do as written. The readings for builds from 7.6 on rest on the
  em-dash retry, without which OSWorld's postconfig fails to activate the window.
- An in-VM reading: the scoring ran offline, and K2 covers the control configuration only.

## 4. How reliable the audit is

Table 6. Agreement [MUT `summary.json`; ADJ `summary.json` `agreement`, `spot_check`]. The
adjudicator rows are adjudicated by an isolated model on the owner's instruction (D80); not
human-validated.

| Comparison | Items | Agree | κ |
|---|---:|---:|---:|
| Claude rater vs Qwen rater, real items of the census | 138 | 114 (82.6%) | 0.343 |
| Adjudicator vs Claude rater, the 52 adjudicated items | 52 | 41 | 0.60 |
| Adjudicator vs Qwen rater, the 52 adjudicated items | 52 | 35 | 0.34 |
| Adjudicator vs Claude rater, the 28 pool splits | 28 | 17 | 0.24 |
| Adjudicator vs Qwen rater, the 28 pool splits | 28 | 11 | 0.00 |
| Fable vs adjudicator, the 52 items, one attachment type excepted (below) | 52 | 51 | 0.96 |

- **The raters.** κ is 0.343 on the 138 real items, below the registered 0.6, and adjudication
  cannot change it. Sham accuracy is 0.90 for Claude (36 of 40) and 0.975 for Qwen (39 of 40).
  24 of the 138 real items were unresolved before adjudication. On the 36 z-order candidates
  the raters agreed on 30.
- **The adjudicator leans to Claude.** On the 28 splits it sided with Claude 17 times,
  including all 6 equivalence splits, and with Qwen 11 times. In the spot check it matched the
  Claude rater on all 25 items and the raters' consensus on all 23 concordant ones, and it got
  all 5 shams right. A model spot check that agrees with one rater on every item cannot
  validate that rater; D9's human spot check stays open as the only independent validation
  (D82).
- **Fable, the independence sensitivity.** `claude-fable-5-1` agreed with the record on 51 of 52
  items and 27 of 28 splits. Its one unsure, `0fd24b93`, is an equivalence split, which leaves
  32 confirmed false negatives and confirmed shares of 11.2% (6.2-17.0%) pooled, 35.8%
  (26.9-43.5%) for `compare_pptx_files` and 82.3% (66.6-95.8%) for the z-order operator. Under
  the strict registered audit all 52 Fable answers are void, because every Fable transcript
  carries a harness attachment type off the registered list (a fixed reminder to batch tool
  calls, 171 entries in 52 transcripts); the reading above excepts that one type. Fable comes
  from the same provider, so this measures stability across two Anthropic models, not
  independence from Anthropic.
- **Notation, the second sensitivity.** The 12 items whose packets show the differ's
  added-sheet marker were all accepted by the record without D81's sentence and all accepted
  with it, so the analysis is byte-identical. In the registered rating the Claude rater had
  rejected 9 of these 12 and Qwen accepted all 12, which is descriptive only.
- **K3 and K4** are reported, not acted on (D35). After adjudication K3 fires through κ alone
  for the equivalence group and fires for the violation group (5 items on 4 tasks,
  insufficiently audited); K4 no longer fires.

## 5. Limitations

These bound every result above, and they are stated as plainly as the results.

- **Descriptive only.** D34's exit fired on the development audit, so the study is a
  pre-specified descriptive protocol (D35). It lists and counts candidates; it makes no
  confirmatory claim, compares no share with a threshold and does not estimate a checker error
  rate for OSWorld as a whole.
- **Offline harness, checked in the VM on a sample.** Scoring ran in an offline replica of the
  VM's files. K2 checked it inside real VMs on 80 registered jobs (78 compared) and on all 41
  candidate events, with no difference. It did not rerun all 1,300 scoring jobs in the VM, and
  `compare_pptx_files_tolerant` has no pair in the K2 sample.
- **Model raters, a correlated model adjudicator, no human.** Both raters are models. The
  labels come from specs written by a Claude model, one rater is Claude, and the adjudicator is
  the same model as that rater (`claude-opus-5-5`). The independence sensitivity used another
  Anthropic model. The adjudicator matched the Claude rater on all 25 spot-check items. Nothing
  here is human-validated; D9's human spot check is pending.
- **κ 0.34.** The raters agree at κ 0.343 on the real items, far below the registered 0.6. The
  z-order finding is the most stable part (30 of 36 concordant before adjudication, 33 confirmed
  after, 32 under Fable); the alternative-solution and gold-sham readings are the least stable.
- **One host, one snapshot.** Every save, scoring and VM job ran on one host (`fal-h100-01`;
  CPU-only jobs, apart from the open-weight rater's 0.365 GPU-h) against one benchmark
  snapshot: OSWorld at `b138d348`, the VM image at Hugging Face revision `a5d9c3ea`,
  LibreOffice 7.3.7.2 in one locale [MUT-REG section 2]. R04 (section 3.9) shows that other
  builds and locales do change some verdicts of golds and agent end states: the two newest
  builds it tested, 25.8 and 26.2, and three of its four other locales. The mutants were not
  rerun under any of them, and no other OSWorld revision was tested.
- **R04's flips are listed, not judged.** Its readings count reproducible verdict changes
  against a paired control. Nobody has read a flipped file or adjudicated a flip, so R04 does not
  say which flips are checker defects and which are real changes in the document. It scored
  offline (K2 covers its control configuration only), tested only the registered levels, kept
  the interface language en-US, and re-saved only the documents the checker reads directly on
  S1a's end states (section 3.9).
- **A narrow population.** The population is 444 synthetic mutants on 60 confirm tasks, mostly
  LibreOffice spreadsheets, documents and decks. Not covered: 43 confirm tasks without a
  complete gold, 10 whose complete gold has no file an operator handles, 7 target tasks whose
  saved null mutant fails its own checker, the reserve split (apart from MUT-P1's golds and
  part (b)'s check of `zinv` on its 8 pptx targets, section 3.7), live-state and web tasks,
  and every non-office checker (GIMP, VLC, Thunderbird, VS Code, OS settings). Probe-touched
  cells were excluded and their 28 false-positive events are unaudited.
- **Ambiguous mutants are out.** 186 of the 1,232 admitted mutants end with an ambiguous
  label, 3 of them z-order swaps. They are counted, kept out of the population and never
  audited, so what the checkers do on them is not described here.
- **Packets share the operators' view of a file.** The packets' listings and differences come
  from the snapshot model the operators also use for their purity checks. A collateral change
  that model does not record is invisible to both, and only the page renders could show it to
  a rater.
- **The catalog shapes the finding.** Operators find only the kinds of edit they make. That
  the z-order swap dominates says that this catalog found one kind of defect, shape-order
  sensitivity in the pptx comparators; it does not say other checkers are sound against edits
  the catalog lacks.
- **The correction's held-out check is small.** `zinv` was developed and validated on the
  confirm campaign's own z-order mutants. On the held-out reserve split (R03 part (b)) it
  accepted 13 of 13 z-order mutants and newly accepted 0 of 15 violation mutants, a descriptive
  PASS below the registered 20 mutants. That bounds its acceptance below at 0.794 per mutant and
  0.688 per task, not at 95%. It checks `zinv`'s implementation on unseen decks, not the rule it
  shares with the operator, under which a correct implementation passes every operator-built
  z-order mutant by construction (section 3.7). The check is offline and rests on the operators' labels, the
  reserve decks come from the same OSWorld pool, and the study has no unseen pptx target left
  for another held-out test.
- **No on-policy consequence shown.** The corrected comparator flipped 0 of 1,808 S1a verdicts
  (two policies, 15 steps). The defect is real on constructed end states; this note does not
  show that it changed any agent's score.
- **Mutants are not agent end states.** A mutant differs from its gold by one controlled edit.
  Real agent end states differ in many ways at once, so these counts are not rates of wrong
  verdicts on agent runs; R02 would measure those.

## 6. Related work

**Closest prior.** Finding Blind Spots in AppWorld and WorkArena Task Verifiers (arXiv
2610.09142, 2026-10-06) mutation-tests task verifiers on two web and API suites. It names
OSWorld-Verified-class desktop checkers as outside its scope (Limitations) and lists an OSWorld
rank-consequence audit as future work, with estimating a false-accept rate and mapping it to a
policy's silent-wrong-action rate [CLAIMS c076; verifier finding S6]. Its Limitations sentence
describes its own scope; it is not evidence that desktop checkers are untested. That absence
claim rests on the program's own searches: the renewal sweep's 272 cell queries and the
dossier owner's 22 queries (among them queries 10, 15 and 19, which target checker mutation and
checker audits on desktop and GUI benchmarks in alphaXiv, OpenReview and the ACL Anthology)
found no prior that mutation-tests desktop file-state checkers [DOSSIER, "Method" and
section 3]. The registered prior-art check K8 [MUT-REG section 10] then ran on 2026-10-11,
after this note's first draft rather than before drafting as registered: 12 `orx` queries
(134 distinct hits) and the Semantic Scholar citers of AgentRewardBench (110) and ABC (114),
216 distinct, found no mutation audit of desktop computer-use-agent checkers, so K8 does not
fire and the note keeps its scope [K8]. The dossier's alphaXiv results reached 2026-10-09 and
K8's newest hit is dated 2026-10-08, so later posts are not covered, and an absence in these
searches is not a claim that none exists.

**Audits of verdicts.** How Benchmarks Mis-Score Computer-Use Agents (arXiv 2607.28367,
2026-07-30) hand-audits 150 FAIL-scored trajectories from five benchmarks; of 57 OSWorld items,
8 are evaluator false negatives (14.0%), and it leaves the complementary audit of PASS verdicts
open [CLAIMS c066]. Our false negatives are on the same side, found by construction rather than
by reading agent failures, with a false-positive side and a GUI-save fixed point added. Auditing
Web Agent Evaluation on WebArena-Lite (arXiv 2610.01491, title resolved 2026-10-11) finds by
human review 5.45-8.49 pp of success the evaluator missed, on the web [DOSSIER, query 2]. A Trust
Layer for Agent Evaluation (arXiv 2610.07274, 2026-10-05) checks earned passes, honesty and
rerun stability on 108 Agents' Last Exam tasks and finds 22.6% of recorded passes clear all
four checks [DOSSIER, query 1].

**Benchmark and checker audits elsewhere.** BenchJack (Do Androids Dream of Breaking the
Game?, arXiv 2605.12673, 2026-05-12), found by K8, drives coding agents to search 10 agent
benchmarks, desktop computing among them, for reward-hacking exploits; per its abstract, its
iterative pipeline fully patched WebArena and OSWorld within three iterations [K8]. It audits
exploitable false accepts of the evaluation pipeline; it does not test checker verdicts on
equivalent or violating end states. Measuring the Checker (arXiv 2609.22220,
2026-09-02) applies mutation analysis to kernel correctness oracles; the official KernelBench
check misses 16.9% of its witnessed faults [CLAIMS c069]. Do Agent Benchmarks Do What They
Say? (arXiv 2609.37315, 2026-09-29) checks the tools of four tool-using agent benchmarks
against their advertised contracts, and Who Guards the Benchmarks? (BenchGuard, arXiv
2604.24955, 2026-04-27, COLM 2026) audits the artifacts of scientific agent benchmarks; neither
touches a desktop state checker. The program verified these two titles [CLAIMS c121, c122;
SLATE section 1], and K8 read their abstracts [K8]. OpenComputer (ICLR 2027 submission,
OpenReview `CgLTapI6Mr`) builds verifiable software worlds with app-specific state verifiers
rather than auditing OSWorld's, per its abstract as the program's verifier read it [CLAIMS
c085]. SSCBench (arXiv 2610.11514) studies the evidential validity of fault-injection tests
for tool-using agents [DOSSIER, "Method"]. The equivalence operators play the role that
metamorphic relations play in testing without a full oracle; Barr et al. survey that oracle
problem (IEEE TSE 41(5), 2015) [CLAIMS c182].

**What is left to this note.** Mutation tests of desktop document checkers; false rejects of
equivalent shape reorders by the pptx comparators, the most frequent candidate error under this
catalog outside probe-touched cells; gold files that are not a fixed point of the pipeline's
own save; a VM fidelity check of the offline harness; a corrected comparator with a held-out
check; a zero on-policy consequence for two small policies; and a registered test of whether
checker verdicts survive a change of LibreOffice build, locale or save route, for which R04's
registration records no prior in the renewal sweep's searches [NUI-REG section 18].

## 7. Reproducing this note

Every number in the text is listed in `data/claims.json` with the committed file and key it
comes from. `scripts/check_claims.py` checks each entry against its source and checks that every
number in the text is covered:

```bash
uv run --locked python paper/checker-mutation-note/scripts/figures.py
uv run --locked python paper/checker-mutation-note/scripts/check_claims.py
```

Both run from the repository root on CPU, without network. `figures.py` writes the two figures
and `data/derived.json`, which holds the few counts no committed file states directly: the
z-order operator's statuses and per-family verdicts, read from `outcomes.jsonl`; the zinv rows
per reading and their tasks; MUT-P1's raw-passing golds, from the controls summaries; the
confirm tasks without a target, from the pre-freeze target counts; and the operators in
Figure 1. The registered analyses themselves are reproduced by the commands in [MUT],
[K2] and [ADJ]. Part (b)'s frozen rule recomputes its judgement from the released rows; for
this revision it gave the committed `judgement.json` again, apart from the last digit of one
float [ZR]:

```bash
uv run --locked python -m harness.q2_zinv_reserve.run judge \
  --rows program/evidence/2026-10-12/q2-zinv-reserve-run/release/zinv-rows.json \
  --out /tmp/zr-judgement.json
```

R04's registered analysis runs on the standard library and reproduces from its evidence copy,
from the repository root at R04's freeze commit or later; it gives the committed `analysis.json`
apart from input paths, which `tests/test_r04_evidence.py` checks [NUI]:

```bash
V=program/evidence/2026-10-12/r04-nuisance-confirm/r04-registered-v1
python -m harness.r04_nuisance.analysis --run $V --src . --out /tmp/r04-analysis.json
```

Not in the repository: the mutant documents, packets, rater transcripts and answer reasons,
because they hold or quote third-party task documents. They are hashed in the committed
receipts.

## 8. Authorship and process

AI agents (Claude models) ran the campaign, the audit, the adjudication and the analyses under
the program's frozen registrations and decisions, and an AI agent wrote this draft as its single
author from committed evidence only; the same agent ran the K8 searches. Decisions D80-D82 delegated the adjudication to an isolated
model. AI agents also ran R03 part (b) under its frozen addendum (D86, D88), and a later agent
session added its result to this draft from the committed run record. AI agents ran R04 under
its frozen registration (D89), and a later agent session added its result from the committed
run record in the same way. No human has reviewed
this note, adjudicated an item or validated a label. Kevin Liu owns the program and every
outward action, including any disclosure and publication.

## Sources

Program evidence (paths from the repository root):

- [MUT-REG] `program/preregistrations/q2-evaluator-mutation-v1.md` (frozen, ledger row 11).
- [K2-REG] `program/preregistrations/q2-evaluator-mutation-v1-k2.md` (frozen, ledger row 17).
- [MUT] `program/evidence/2026-10-08/q2-mutation-confirm/README.md`, `results/README.md`,
  `results/summary.json`, `results/released/confirm-mutants-v1/` and
  `results/released/controls/` (the controls summaries).
- [MUT-AUD] `program/evidence/2026-10-08/q2-mutation-confirm/audit/README.md`.
- [K2] `program/evidence/2026-10-11/q2-mutation-k2/README.md` and
  `k2-confirm-v1-job1186/` (README, `report/k2-summary.json`).
- [ADJ] `program/evidence/2026-10-11/q2-mutation-adjudication-v2/README.md` and
  `summary.json`; [ADJ-AN] its `analysis/analysis.json`.
- [ZINV] `harness/q2_stage1/zinv.py`; [ZINV-VAL]
  `program/evidence/2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json`.
- [ZR-REG] `program/preregistrations/q2-zinv-reserve-validation-v1.md` (frozen, ledger row 20),
  the R03 part (b) addendum; [ZR] `program/evidence/2026-10-12/q2-zinv-reserve-run/README.md`
  and its `release/judgement.json` and `release/zinv-rows.json` (blind warning above).
- [NUI-REG] `program/preregistrations/r04-checker-nuisance-invariance-v1.md` (frozen,
  ledger row 18), R04's registration; [NUI]
  `program/evidence/2026-10-12/r04-nuisance-confirm/README.md` and its
  `r04-registered-v1/analysis.json` and `analysis-k2.json` (the registered analysis without and
  with the K2 report) and score rows `r04-registered-v1/main/scores/` (blind warning above).
- [S1A-REG] `program/preregistrations/q2-stage1-rescoped-v1.md`; [S1A]
  `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md`; [S1A-RESC]
  `program/evidence/2026-10-10/q2-stage1-analysis/rescore-coverage.json`.
- [DER] `paper/checker-mutation-note/data/derived.json` (written by `scripts/figures.py`).
- [K8] `program/evidence/2026-10-11/q2-mutation-k8-prior-art/README.md` and `k8-record.json`
  (added on this draft's branch).
- [DOSSIER] `program/evidence/2026-10-11/question-renewal/dossier.md`; [SLATE] `slate.md`;
  [CLAIMS] `claim-registry.json` and `verification.json` in the same directory.
- Decisions D2, D9, D23, D25, D27, D34, D35, D38, D72, D79, D80, D81, D82, D86, D88 and D89:
  `program/decisions.md`.

External sources (arXiv dates are first-version dates, as the program's verifier or K8's arXiv
API read recorded them; where neither recorded one, the date the title was resolved):

- OSWorld: <https://arxiv.org/abs/2404.07972> (2024-04-11, K8); repository
  <https://github.com/xlang-ai/OSWorld>, pinned at `b138d348`.
- Finding Blind Spots in AppWorld and WorkArena Task Verifiers:
  <https://arxiv.org/abs/2610.09142> (2026-10-06).
- How Benchmarks Mis-Score Computer-Use Agents: <https://arxiv.org/abs/2607.28367>
  (2026-07-30).
- Measuring the Checker: <https://arxiv.org/abs/2609.22220> (2026-09-02).
- Auditing Web Agent Evaluation on WebArena-Lite: <https://arxiv.org/abs/2610.01491> (resolved
  2026-10-11).
- A Trust Layer for Agent Evaluation: <https://arxiv.org/abs/2610.07274> (2026-10-05).
- Do Agent Benchmarks Do What They Say?: <https://arxiv.org/abs/2609.37315> (2026-09-29).
- Who Guards the Benchmarks? (BenchGuard): <https://arxiv.org/abs/2604.24955> (2026-04-27).
- Do Androids Dream of Breaking the Game? Systematically Auditing AI Agent Benchmarks with
  BenchJack: <https://arxiv.org/abs/2605.12673> (2026-05-12, K8).
- SSCBench: <https://arxiv.org/abs/2610.11514> (resolved 2026-10-11).
- OpenComputer: <https://openreview.net/forum?id=CgLTapI6Mr> (resolved 2026-10-11).
- Barr, Harman, McMinn, Shahbaz and Yoo, The Oracle Problem in Software Testing: A Survey,
  IEEE TSE 41(5), 2015: <https://doi.org/10.1109/tse.2014.2372785>.
