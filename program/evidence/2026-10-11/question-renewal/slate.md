# Question-renewal slate (2026-10-11)

Fifteen candidate questions for Kevin, merged from five discovery cells under
D71 (i). This is a slate, not an adoption. Nothing here is a result, a novelty
claim or a gauntlet score. No judge has scored these candidates yet, so the
order below is the slate owner's provisional order, stated with its criteria,
and not a ranking.

Every entry uses the 2026-10-06 dossier format: corrected question, what is
wrong with the naive version, novelty verdict with the closest priors, why it
matters, citable anchors with status, first experiment with GPU-h and the gate
before GPU, kill criteria, and relation to the existing program. Each entry
also has a decisiveness check, because decisiveness or identification was the
largest defect in nearly all of the program's ten gauntlet runs (D54, D63,
D65, D70).

Companion files in this directory:

- [`claim-registry.json`](claim-registry.json): every quantitative or prior
  claim in this file, with its source URL or repository path and how it was
  checked.
- [`queries.md`](queries.md): every retrieval query, by cell, plus the slate
  owner's verification queries.

## How to read this

- **Novelty verdicts.** STILL_OPEN: no prior found that answers the corrected
  question, under the coverage stated in `queries.md`. NARROWED: priors
  answer parts of it; the residual is named. OCCUPIED: the question is
  answered; such candidates were not carried (see "Not carried"). A verdict
  is an absence in the stated queries, never a claim that nothing exists.
- **GPU-hours** are estimates unless stated. GPU-h per desktop episode is
  S1a's realized 0.0025-0.0027 (Qwen3.5-4B and 9B, V = 20). "Cap-GPU-h"
  applies the design study's realized x 1.2 x 1.05 rule. New model sizes,
  new observation arms and kernel timing are unmeasured, and each candidate
  puts a probe or smoke first.
- **Process gates.** A new mechanism, or any run over 8 GPU-h, goes through
  the research gauntlet (`.claude/rules/research-gauntlet-loop.md`). A rerun
  of an existing design under 8 GPU-h needs a registration and a pre-freeze
  audit (D66). No package can score above 79 without an executable pilot or
  above 89 without signed reviews (D24, D68), so every GPU step below needs
  Kevin's admission ruling or the trust store, whatever its score.
- **Standing constraints.** No untrusted model-generated code runs with GPU
  access on the R570 driver (D3, D7). D46 stopped Q1 GPU spend until Q1
  Stage 1 can run, so any kernel-side GPU step, even with trusted code only,
  needs Kevin to lift that stop. Outward actions (disclosures, contacting
  authors, downloads beyond D1) are Kevin's (D2). Host jobs are CPU-only
  unless admitted, and none overlaps another.

## Summary table (provisional order)

Order criteria, in this order: cost to the first decisive reading;
residual novelty and scoop clock; decisiveness by construction; how much of
the path is already built; how many of Kevin's rulings it waits on.

| # | Key | Title | Novelty | First exp. GPU-h | Gate before GPU | Route | Waits on Kevin for |
|---|---|---|---|---|---|---|---|
| 1 | R03 | Finish the OSWorld checker-mutation note | NARROWED | 0 | none (CPU-lane K2) | existing registration | 34-item adjudication, 25-item spot check, disclosure |
| 2 | R02 | On-policy two-sided audit of S1a's 1,808 verdicts | NARROWED | 0.3-1 (rater lane) | instrument validation gate | registration (descriptive) + gauntlet | split-gold adjudication; admission of the rater job |
| 3 | R01 | Where greedy rerun noise comes from on the desktop stack | NARROWED | Stage A 0; B+C about 2.5, cap 4 | Stage A pixel diff and replay | gauntlet | admission |
| 4 | R07 | Task-success cost of known action-path defects | NARROWED | Stage 0 0; Stage 1 about 2.4, cap 4 | Stage 0 census touches at least 10% of episodes | gauntlet | admission |
| 5 | R04 | Checker verdicts under LibreOffice-build and locale changes | STILL_OPEN | 0 (CPU lane) | postconfig replay per build; en_US control | registration | none for CPU; any disclosure |
| 6 | R10 | Input-design oracles for TF32: same-sign and exact-lattice families | NARROWED | 0 (CPU pilot) | CPU pilot is the gate | gauntlet (new mechanism) | D46 stop for any device check |
| 7 | R11 | Can kernel benchmarks referee their own TF32 baseline? | STILL_OPEN (zeros facet OCCUPIED) | 0 (CPU); device pilot 1.2 | CPU census | registration | D14 ruling; D46 stop for the pilot |
| 8 | R05 | Checker-revision drift on fixed end states, then an external anchor | STILL_OPEN | 0 drift test; anchor 0.8-1.1 | agreement at least 98% | registration | remote-code ruling; 7.9 GB download |
| 9 | R12 | Interpreter-executed audit of model-written Triton kernels | NARROWED | 0.3 (trusted fidelity leg) | fidelity agreement at least 95% | registration; Stage 2 gauntlet | D46 stop; policy licence for Stage 2 |
| 10 | R14 | What the cross-lingual long-context penalty is made of | NARROWED | about 1 (Stage A pilot) | overlap audit and scorer mutation gate | gauntlet | admission |
| 11 | R15 | Translated instructions in a desktop agent: language or lost referents? | NARROWED | at most 4.1 | at least 30 referent-bearing informative tasks | gauntlet | admission |
| 12 | R06 | A session-inclusive noise band on published OSWorld-Verified claims | NARROWED | 0 | claim census at least 20 | none (CPU analysis) | none |
| 13 | R08 | Accessibility tree on the certified path vs S1a's floor | NARROWED | about 3.3 cap | harness port and smoke | gauntlet | admission |
| 14 | R13 | The speed premium of a pure precision cut, per gate | STILL_OPEN | about 2.5, cap 4 | gate stack on device outputs | registration | D46 stop |
| 15 | R09 | Does greedy rerun noise shrink with scale within Qwen3.5? | NARROWED | 0.3 probe; then 5-6.5 cap | probe price and keysym certification | gauntlet | admission |

Sum of the first experiments' central estimates if every one ran: about
17 GPU-h (about 20 with R11's device pilot and R05's anchor run), plus R09's
main run. None is above 8 GPU-h alone.

## Merges (cells to candidates)

Cells: 1 checker and benchmark calibration; 2 computer-use instrument
follow-ons; 3 kernel and code correctness after Q1; 4 multilingual and
long-context mechanisms; 5 kill-shot and occupancy. Twenty-six cell
candidates became fifteen.

| Key | Merged from | Shared mechanism |
|---|---|---|
| R01 | cell 1 #1, cell 2 #1, cell 5 #3 | Separating the sources of greedy rerun discordance (clock pixels, serving numerics, environment timing) |
| R02 | cell 1 #2, cell 2 #2, cell 5 #4 | An independent audit of real policy end states, and whether mutant rates transfer to them |
| R03 | cell 2 #4, cell 5 #1 | Completing the checker-mutation study: VM fidelity, held-out repair, adjudication |
| R04 | cell 1 #4, cell 4 #3 | Semantically null environment changes (application build, save path, locale) applied to golds and end states |
| R05 | cell 2 #5 | Checker-code revision drift on fixed end states |
| R06 | cell 1 #3 | Adding a session variance term to published claims |
| R07 | cell 5 #2 | Counterfactual action translation through known-defective harnesses |
| R08 | cell 2 #3 | Observation type as a factor under the measured floor |
| R09 | cell 2 #6 | Rerun noise as a function of scale within one family |
| R10 | cell 1 #5, cell 3 #1 | Choosing inputs so valid-variant noise shrinks below fault size |
| R11 | cell 3 #2, cell 5 #5 | Whether TF32-baseline protocols can decide correctness at all, per problem |
| R12 | cell 3 #3, cell 3 #4 | Executing untrusted Triton only in the CPU interpreter, as an audit path |
| R13 | cell 3 #5 | The speed side of precision cuts that gates miss |
| R14 | cell 4 #1, cell 4 #4, cell 4 #5 | Decomposing the cross-lingual long-context penalty: literal overlap, script tokens, translation mediation, token distance |
| R15 | cell 4 #2 | Literal on-screen referents in translated desktop instructions |

## Corrections made while merging

The slate owner re-checked cell numbers against the repository and primary
sources. Changes from the cells' text:

- A cell wrote that `compare_pptx_files` "fails 35 of 36 equivalent order
  edits". In fact the z-order operator yields 36 false-negative candidates in 40 mutants
  (91.7%), 35 of them under `compare_pptx_files` and 1 under
  `compare_pptx_files_tolerant`.
- A cell wrote that S1a's offline rescoring "matched live scoring in 1,791
  of 1,808". In fact every replayed record matched (0 mismatches); 1,791
  secondary verdicts
  came from rescoring, 16 fell back to live scores (task `53ad5833`, which
  needs live state) and 1 metric-exception episode was scored 0 by the merge
  rule.
- "Qwen3.5-9B solved 52 of the 113 pool tasks" is right for "at least once
  in 8 episodes". Only 32 of them are informative in the sense of being
  neither always nor never solved (4B: 50 and 33).
- 2607.28367's OSWorld figures are both correct but differ in kind: 8 of 57
  OSWorld FAIL verdicts are evaluator false negatives (14.0%), and 17.5% of
  the 57 are wrong once 2 broken tasks are added.
- G0's 110 excluded anchor tasks are not all checker-code changes. 36 have
  a changed task config; 74 differ only in checker definitions they reach.
  Only those 74 (plus the 6 kept) can be re-admitted by a checker-drift test
  (R05).
- The OpenReview id given for CAVEAT (`gfgvdsOX6v`) did not resolve in the
  api2 search; the search returned a different CAVEAT paper. It is not cited.
- A cell's "A7 step p50 2.63 s" was not found in the acceptance record (A4's
  step p50 is 2.124 s). It is not used.
- Measuring the Checker (2609.22220) already uses same-sign magnitudes in its
  targeted suites and explains why in its Fig. 2b. This narrows R10's
  same-sign half more than cell 1 stated.

## Findings for Kevin outside the slate

1. **Scoop clock on the checker-mutation note.** 2610.09142 (2026-10-06)
   mutation-tests AppWorld and WorkArena verifiers, says OSWorld-Verified-class
   desktop checkers "remain untested", and lists an OSWorld rank-consequence
   audit and the mapping from false-accept rate to a policy's silent-wrong
   rate as future work. R03 and R02 are the program's answers to both.
2. **Wording to narrow.** `program/questions/q2-calibrated-cua-instrument.md`
   line 27 and `program/PROGRAM.md` line 77 say checker-mutation testing for
   computer use has "no prior found". After 2610.09142 the accurate line is
   "no prior found for desktop file-state checkers". This slate does not edit
   those files.
3. **The two cross-cutting levers.** Every candidate here is CPU-first, and
   six (R03, R04, R05, R06, R10, R11) have no GPU step in their first
   experiment. CPU first experiments double as executable pilots, which is
   the program's only lever on the 79 cap. The 89 cap needs the D24 trust
   store, which only Kevin can set up.

---

## 1. Finish the OSWorld checker-mutation note

`R03-mutation-note-completion`. Origin: cell 2 #4 and cell 5 #1.
Not a new question: it completes the frozen `q2-evaluator-mutation-v1` study
so it can ship.

**Corrected question.** On the 60 evaluable tasks of the frozen confirm
campaign, after Kevin's blind adjudication and spot check: (a) do mutants
materialized and saved inside the certified VM get the same verdict as the
offline harness, with every difference explained by the four registered
causes (save timing, repeat disagreement, hash mismatch, VM infrastructure)?
(b) Does the order-invariant `compare_pptx_files_zinv` accept at least 95% of
held-out z-order equivalence mutants on the reserve split, while accepting no
violation mutant the original rejects? (c) Optional, as a new registration:
do operator families written blind to the target code exceed a 10%
task-equal false-negative share on the pool's non-office checkers (gimp,
vlc, thunderbird, vs_code, OS settings)?

**What is wrong with the naive version.** "Ship the note now" overstates
three things. The headline carries the registered label "offline harness, VM
fidelity unverified", because K2 had no executor. `zinv` was validated on the
split it was built for (G0 item 8: v1 kept 0 of 29, v2 26 of 29). And the
mutant population is 67 file-target tasks, mostly LibreOffice, so the note
cannot speak for the pool's other checker families.

**Novelty.** NARROWED. The method is published for API and web verifiers
(2610.09142) and kernel oracles (2609.22220); FAIL-verdict hand audits exist
(2607.28367). Desktop file-state checkers are untested in every prior found,
and 2610.09142 says so. Residual: desktop document checkers, false rejects
dominating (z-order), gold round-trip flips, and zero on-policy consequence
at 4B and 9B. Scoop risk is high and rising.

**Why it matters.** It is the program's most finished result and its first
shippable one. It also names the checker families every later Q2, S2 or S3
claim must exclude or correct.

**Closest priors.**

- [Finding Blind Spots in AppWorld and WorkArena Task Verifiers](https://arxiv.org/abs/2610.09142), 2026-10-06: source-informed mutation of task effects on two web/API suites; "OSWorld-Verified-class desktop environments, remain untested"; lists the OSWorld rank-consequence audit as future work.
- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367), 2026-07-30: hand audit of 150 FAIL trajectories; FAIL only.
- [Measuring the Checker](https://arxiv.org/abs/2609.22220), 2026-09: the same method on kernel oracles.
- [Do Agent Benchmarks Do What They Say?](https://arxiv.org/abs/2609.37315) and [Who Guards the Benchmarks? (BenchGuard, COLM 2026)](https://arxiv.org/abs/2604.24955): benchmark audits of tool-using environments, not desktop state checkers.
- [OpenComputer (ICLR 2027 submission)](https://openreview.net/forum?id=CgLTapI6Mr): builds verifiers, does not audit OSWorld's.

**Citable anchors.**

- 2610.09142. Role: closest prior and scoop source. Status: VERIFIED (full text, slate owner): the "remain untested" and future-work lines quoted above.
- 2607.28367. Role: FAIL-side prior. Status: VERIFIED (full text): "the complementary audit of PASS verdicts remains open".
- 2609.22220. Role: method source. Status: VERIFIED (full text).
- Program record: `program/evidence/2026-10-08/q2-mutation-confirm/results/README.md`. Status: VERIFIED (repository).

**First experiment (0 GPU-h).** (1) Kevin adjudicates the 34-item pool blind
and does the 25-item spot check (52 distinct items); rerun `audit summarize
--adjudications` and the registered analysis. (2) K2 as a CPU-only host job
on the certified lane: record the executor commit and image digest, then
run the registered 80-job sample (20 per domain, 41 tasks, drawn before any
verdict) through `harness/q2_mutation/vm_injection.py` at N <= 32, and
classify each difference by the four registered causes. (3) On CPU, the
reserve split's z-order equivalence and pptx violation operators under both
comparators. **Gate before GPU:** none needed; at most 0.5 GPU-h if part (c)
sends new candidates to the open-weight rater.

**Decisiveness check.** Parts (a) and (b) are counts on fixed samples, so
each reaches a verdict whatever the data. The risk is (b)'s sample size: the
reserve split may hold too few evaluable z-order mutants.

**Kill criteria.** Kill the note if, after adjudication, `compare_pptx_files`'
confirmed false-reject share has a 95% lower bound below 5%; if K2 reproduces
fewer than 50% of confirmed verdicts in the VM; or if Kevin's spot check
disagrees with the model-rater consensus on 30% or more of its 25 items. If
more than 10% of K2 pairs are infrastructure exclusions, the executor is not
fit: stop and fix. `zinv` counts as overfit if held-out acceptance is below
95% or it accepts a violation mutant the original rejects; then it is not
shipped as the correction. Below 20 evaluable z-order mutants or 8 tasks,
report (b) descriptively. Part (c) stops if fewer than 3 non-office families
have at least 8 pool tasks with a mutable target. If an OSWorld-class audit
appears first, re-scope to the residual instead of killing.

**Relation to the existing program.** Q2's Stage 0 item 1, frozen as
descriptive under D35. Waits on D9 (Kevin's adjudication) and the K2 label.
The disclosure to xlang-ai is an outward action (D2). Feeds the Q2
technical report (D71 iii).

---

## 2. On-policy two-sided audit of S1a's 1,808 verdicts

`R02-onpolicy-checker-audit`. Origin: cell 1 #2, cell 2 #2, cell 5 #4.

**Corrected question.** On the 1,808 end states S1a captured (Qwen3.5-4B and
9B, two certified harnesses, 113 tasks; 544 checker passes on 57 tasks, 1,264
non-passes including 35 fractional scores), measured against an independent,
three-valued audit (satisfies, violates, ambiguous) frozen before any verdict
is read: (i) what share of PASS verdicts are false accepts, and of FAIL
verdicts false rejects, per checker family; (ii) do the mutation study's
per-family rates predict the on-policy rates (H-transfer), and what share of
on-policy differences from the gold state fall in the frozen operator catalog
(H-coverage); (iii) of the 280 discordant rerun pairs, what share does the
audit judge equivalent in task terms (checker error) rather than different
(agent behaviour)? Falsifiable predictions: the false-accept share among
PASS verdicts has a one-sided 95% upper bound of at most 3%; checker error
explains at most 10% of discordant pairs; catalog coverage is at least 0.5;
and H-transfer fails for `compare_pptx_files` (mutants 40.2%, on-policy flips
0 of 288).

**What is wrong with the naive version.** "Rescore with a better checker"
assumes the audit is independent of the checker and trustworthy. The
program's model raters reached κ = 0.343 on document equivalence despite sham
accuracy of 0.90 and 0.975, so model raters alone cannot be the audit. The
corrected design puts a mechanical instrument first (a structural diff
against the gold state, typed into the operator catalog, and an executable
checker compiled from the blind specs without reading OSWorld's evaluators),
validates it on the mutation campaign's labelled items, and uses raters and
Kevin only for disagreements.

**Novelty.** NARROWED. 2607.28367 audits FAIL verdicts only and states that
the PASS audit "remains open". 2610.09142 disclaims population rates and
names mapping its rate to policy behaviour as future work. Just et al. (FSE
2014) asked the mutant-coupling question for software test suites. No prior
found audits both directions on one policy's reruns of a desktop benchmark or
attributes rerun discordance to the checker. Scoop risk: real (2610.09142's
future-work list).

**Why it matters.** Every noise floor in the program, and every S2, S3 or
leaderboard reading built on it, assumes checker error is small on-policy.
If (iii) fails, D_b and D_w must be corrected before reuse. It also answers
for desktop checkers the realism question Measuring the Checker raised for
kernels.

**Closest priors.**

- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367), 2026-07-30: 150 FAIL trajectories, 57 from OSWorld, 8 of those evaluator false negatives (14.0%); no PASS audit, no reruns.
- [Finding Blind Spots in AppWorld and WorkArena Task Verifiers](https://arxiv.org/abs/2610.09142), 2026-10-06: constructed faults; no population rate.
- [Measuring the Checker](https://arxiv.org/abs/2609.22220): realism probe on 60 LLM-written kernels.
- [Are mutants a valid substitute for real faults in software testing?](https://doi.org/10.1145/2635868.2635929) (Just et al., FSE 2014): the classical transfer question.
- [TRACE](https://arxiv.org/abs/2610.11678): rescoring unchanged trajectories separates evaluator from behaviour on tau2-bench; identical reruns flip 15-36% of outcomes; no checker attribution of rerun discordance.
- [Maintaining Benchmarks Against Increasingly Capable Agents](https://arxiv.org/abs/2609.34262): audits passing coding trajectories for process exploits, not state-checker correctness.
- [KernelAudit (ICLR 2027 submission)](https://openreview.net/forum?id=yTa4gvQUGG): audits 505 generated kernels that passed functional checks, without a mutation catalog.
- [CUAAudit](https://arxiv.org/abs/2603.10577), [The Art of Building Verifiers for CUAs](https://arxiv.org/abs/2604.06240), [AgentRewardBench](https://arxiv.org/abs/2504.08942): judge accuracy, not checker error on one model's reruns.

**Citable anchors.**

- 2607.28367. Role: closest prior. Status: VERIFIED (full text): 57 OSWorld items, 8 evaluator false negatives, 17.5% wrong in all, PASS audit open.
- 2610.09142. Role: scoop source. Status: VERIFIED (full text).
- Just et al. 2014. Role: classical transfer framing. Status: DOI from cells 1 and 5 (OpenAlex query); not opened by the slate owner.
- yTa4gvQUGG. Role: kernel-side on-policy audit. Status: VERIFIED (OpenReview api2 abstract).
- S1a and mutation records. Status: VERIFIED (repository; counts recomputed by the slate owner from `a1.jsonl`).

**First experiment (0.3-1 GPU-h, for the open-weight rater lane job only).**
Packet building and analysis run on the host CPU lane, because the captures
hold third-party documents and stay on the host; only verdicts and recipes
are released. (1) Instruments: the structural diff classifier (the mutation
kit's state readers, diff against the gold state, typed into the frozen
catalog or "uncovered") and the executable spec checker. (2) Population: a
census of the 544 PASS end states, a stratified sample of up to 400 FAIL end
states whose checked file changed from its initial hash (unchanged-file
FAILs classified mechanically and weighted back), and all 280 discordant
pairs. (3) Disagreements between instruments and the OSWorld checker, plus a
random 10% of agreements, go to the two model raters with gold and
do-nothing shams; splits go to Kevin. (4) Readouts with task-cluster
bootstrap (seeds 42-44). **Gate before GPU:** the spec checker passes at
least 95% of golds, accepts no do-nothing sham, and agrees with witness
labels on at least 90% of non-ambiguous mutants; the classifier types at
least 80% of end states and agrees with a 120-item human-adjudicated sample on
at least 80%. Registration (descriptive, D35 style) and a pre-freeze audit
first; a novel direction, so gauntlet-eligible.

**Decisiveness check.** False accepts may be rare: at a true 2% among 544
PASS verdicts the census sees about 11 events. The registration must fix in
advance that fewer than 10 confirmed errors yields counts and examples only.
The upper-bound predictions (at most 3%, at most 10%) are reachable with zero
or few events, so the line can falsify or close either way.

**Kill criteria.** (1) If the spec checker or the classifier fails its
validation gate, stop before reading S1a; report that a blind-spec second
checker cannot serve as an independent audit (this joins the κ 0.343
finding). (2) If confirmed errors in both directions have a pooled upper 95%
bound below 2%, report "OSWorld file checkers are adequate on-policy for these
policies; mutant rates overstate on-policy error" and close. (3) Fewer than 10
confirmed errors: counts only, no per-family rate or H-coverage verdict. (4)
If Kevin's adjudication reclassifies the gold of 2 or more of the 4
split-gold tasks, rebuild the spec checker for those tasks first. (5) If
families needing live state, or end states that cannot be rendered, exceed
30% of PASS verdicts, report coverage and no rate for them. (6) If more than
25% of audited items stay ambiguous after adjudication, report inconclusive.

**Relation to the existing program.** Uses S1a's captures, the blind specs,
packets, shams and rater tooling from the mutation study. Its answer to (iii)
conditions every rerun-noise estimate in Q2, S2 and S3. Shares the split-gold
adjudication with R03.

---

## 3. Where greedy rerun noise comes from on the certified desktop stack

`R01-rerun-noise-sources`. Origin: cell 1 #1, cell 2 #1, cell 5 #3.

**Corrected question.** Hold fixed S1a's stack (H-OSW-fixed, greedy decoding,
15 steps, 2,048 thinking tokens, V = 20, the prompt date pinned and the
guest clock not). For Qwen3.5-4B on the 113-task pool, minus any task whose
config or checker reads the date or time, split within-session rerun
discordance D_w into three measured parts. (i) Environment outcome noise:
how often replaying an episode's recorded IR actions open-loop in a freshly
reset VM changes the verdict. (ii) Serving numerics: how often byte-identical
recorded step requests get a different greedy reply under S1a's serving
configuration (batched, prefix cache on) compared with batch-1 or
batch-invariant serving with the prefix cache off. (iii) Observation-time
noise: how much D_w falls when the top-bar clock region is masked by a fixed
harness-side rectangle (with cursor blink and animations off if Stage A shows
they also vary). Readings: CLOCK_DOMINANT if (iii) removes at least half of
D_w with a lower bound above 0; NOT_CLOCK if the one-sided 95% upper bound of
the reduction is below 2 pp, after which (ii) and (i) assign the floor to
serving or to environment timing; PARTIAL otherwise.

**What is wrong with the naive version.** S1a's first-divergence analysis
labels 512 of 512 between-session and 255 of 256 within-session base pairs as
diverging at step 1 in the "environment". That label does not identify a
cause. The guest clock is on every screenshot, so the inputs already differ
at step 1, and whether identical inputs would get identical replies under
S1a's serving (prefix-cache hit share 0.855-0.858) was never tested. "Make
serving deterministic" is not sufficient either: 2604.17849 found that
temperature 0 plus batch-invariant inference changes CUA reliability in both
directions while every environment nuisance, the clock included, stays live.

**Novelty.** NARROWED. 2604.17849 crosses decoding determinism with cosmetic
desktop perturbations (wallpaper, cursor, dock, icon theme, timezone) on
OSWorld, but has no clock intervention, no open-loop replay and no
identical-input serving test. "The Evaluator Also Varies" localizes first
divergence on tau2-bench and ALFWorld, text environments with a simulated
user. 2609.04748 shows prefix caching alone changes 36.2% of agentic text
trajectories at 16-bit. 2609.36931 shows a hidden date moves text scores by up
to 14%. Residual: a decomposition for pixel-observation desktop agents, with
the clock as a controlled intervention.

**Why it matters.** If the floor is clock-induced, each stack's noise floor
(S1a's about 11%, TRACE's 15-36% flips, the 12-14% web band) measures its
sensitivity to whatever nuisance it happens to inject, so floors are not
portable between stacks, and power sizing for S2, S3 or any successor must
name the perturbation that generates its variance. If the floor is serving
numerics, deterministic serving is a cheap fix. Rerun noise is 20-33% of
S1a's outcome variance against 3-4% for task-by-harness (D69).

**Closest priors.**

- [On the Reliability of Computer Use Agents](https://arxiv.org/abs/2604.17849), 2026-04 (ARR version: [The Reliability Gap](https://openreview.net/forum?id=ezVIHPgaiG)): temperature 0 plus batch-invariant inference regresses Qwen (b − c = −20) and helps OpenCUA (+20); perturbation sets include timezone; clock live in every arm.
- [The Evaluator Also Varies (ICLR 2027 submission)](https://openreview.net/forum?id=cELldjX2oq): first-divergence audit; five greedy vLLM replicates on 100 tau2-bench tasks diverge in transcript on all and in reward on 20; first discrepancy in the simulated user on 83.
- [Same Request, Different Answer](https://arxiv.org/abs/2609.04748), 2026-09: enabling the prefix cache changes the trajectory on 36.2% of episodes at 16-bit and 75.0% at 4-bit.
- [Dating the Model](https://arxiv.org/abs/2609.36931), 2026-09: date deltas up to 6% (MCQA) and 14% (math); text prompts, not rendered pixels.
- [TRACE](https://arxiv.org/abs/2610.11678): identical reruns flip 15-36% of tau2 outcomes; cause not located.
- [Noise Floor Audit for Agent Benchmarks](https://arxiv.org/abs/2608.22331): temperature-0 tool-calling reruns ever-flip 0.7-2.7%; prompt perturbations 11-58x larger.
- [Greedy Decoding Is Not Precision-Invariant (TMLR 2026)](https://arxiv.org/abs/2609.26621), [Vosti](https://arxiv.org/abs/2609.38981), [FlexBI (ICLR 2027 submission)](https://openreview.net/forum?id=rGmv0X20Oj), [Non-Determinism of "Deterministic" LLM Settings](https://arxiv.org/abs/2408.04667): serving determinism, no desktop measurement.

**Citable anchors.**

- 2604.17849. Role: closest prior. Status: VERIFIED (full text, slate owner): the batch-invariant arm, b − c values and the perturbation table.
- cELldjX2oq. Role: method prior. Status: VERIFIED (OpenReview api2 abstract only; PDF behind a challenge).
- 2609.04748, 2609.36931, 2610.11678, 2608.22331. Status: VERIFIED (full text, slate owner): the figures quoted.
- S1a records (`program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md`; `harness/q2_stage1/design_diffs.md` line 35). Status: VERIFIED (repository).

**First experiment (Stage A 0 GPU-h; Stages B and C about 2.5 GPU-h; cap
4).** Stage A (host CPU lane): pixel-diff the step-1 processed screenshots of
all within- and between-session base pairs (if S1a's step logs are retained
on the host) and list every differing region; replay all 512 base episodes'
recorded IR actions open-loop with the 60 s and 20 s settles at N <= 32; hash
step-1 screenshots across 20 idle boots with and without the time-invariance
changes. Stage B (about 0.3-0.5 GPU-h, serving only, no VMs, after a 0.2 GPU-h
timing probe): replay 600 recorded step requests 4 times under S1a's
configuration with matched filler load; 300 of them twice under batch-1 with
the prefix cache off; the same 300 with only the clock region swapped. Stage C
(about 1.7 GPU-h physical, 2.1 cap): one serving session, arms A0 (S1a
default) and A1 (time-invariant observations) interleaved, R = 3 each, 678
episodes. Primary estimand D_w(A0) − D_w(A1) with task-cluster bootstrap;
secondary the success difference (equivalence margin ±5 pp) and the first
divergence step. Optional Stage D, an A2 arm with batch-invariant serving,
only if vLLM's mode passes a bitwise self-test on Qwen3.5's hybrid layers.
**Gate before GPU:** Stage A shows at least 80% of within-session step-1
pairs differ only inside the clock box (otherwise add the other regions to
the mask and repeat Stage A); A1's step-1 screenshots are byte-identical on
at least 90% of idle boots; registration, pre-freeze audit and gauntlet (new
mechanism); Kevin's admission.

**Decisiveness check.** On the 113-task set S1a's 4B D_w is 11.1% (95%
interval 7.5-15.0%), so a reduction from about 11% to near 0 is resolvable
with R = 3, while a reduction of 1-2 pp is not; the PARTIAL band is wide by
construction and must be registered as a reportable outcome, not a failure.
Stage B is decisive regardless of Stage C, because identical-input flip
rates are counts on fixed requests.

**Kill criteria.** (1) Stage A finds step-1 differences outside the clock box
in more than 20% of within-session pairs and they cannot be removed: stop
and report the localization. (2) Open-loop replay changes the verdict on more
than 2% of episodes: report environment outcome noise as a material floor and
read Stage C net of it. (3) Batch-1, prefix-cache-off serving still differs on
more than 1% of identical requests: deterministic serving is not attainable
on this stack, and the serving part is not identified; label residuals
"serving or environment, not separated". (4) A1 moves 4B success outside
±5 pp: masking is not a pure nuisance removal; report and do not read D_w as
attribution. (5) NOT_CLOCK: the pixel line stops. (6) If A1 shrinks the
design study's simulated delta width for a K = 113 two-arm contrast by less
than 10%, record the gain as reproducibility only.

**Relation to the existing program.** Builds on S1a's records, the
first-divergence tool and D53's action path (masking is an observation
transform, so the action path stays inside its certification). The Holo3 v2
audit found 16 clean tasks with time-dependent checkers carrying 4 of 14 net
flips (not attributable, p 0.156), which bears on the date-reading exclusion.
The answer conditions R09 and any S2/S3 power sizing.

---

## 4. Task-success cost of known action-path defects

`R07-action-path-defect-cost`. Origin: cell 5 #2.

**Corrected question.** Fix Qwen3.5-9B on the certified lane with S1a's
settings on the 113-task pool. Does the defective gym-anything harness
H-GA-buggy (`bf965cde0`: middle-click gives no action, Ctrl released before
the click, only the first tool call executed) score lower than its certified
successor H-GA (`aae6f7607`)? Does the upstream OSWorld harness H-OSW-up
(triple-click, scroll-at-coordinate, hscroll and terminate-failure defects)
score lower than H-OSW-fixed? Each by more than the band S1a measured between
the two certified harnesses (δ −1.1 pp, 90% interval [−3.8, +1.6] on 113
tasks)? Define δ_defect = success(certified) − success(defective), paired by
task. PRESENT if its 90% lower bound exceeds 2 pp; NEGLIGIBLE if its 90%
upper bound is below 2 pp.

**What is wrong with the naive version.** "Harness bugs inflate harness
gaps" is not testable from published harness comparisons, because design
and defects change together. A defect only matters where the model emits the
affected action, so the first quantity to measure is exposure, which S1a's
recorded replies give for free.

**Novelty.** NARROWED. cua-speedrun (2609.40284, App. I, Table 20) found and
fixed exactly these Qwen3.5 defects and reports no task-success cost.
2610.05533 separates defect repair from design in text benchmarks; 2610.04433,
2610.00917 and FrogNano measure harness effects without separating defects.
No desktop prior found for the success cost of defects.

**Why it matters.** S1a's exposed episodes (key, chord or hold actions outside
the 33 certified keysyms) showed δ −4.86 pp against −0.89 pp unexposed, a
hint that action-path exposure, not harness design, drives harness gaps. A
measured defect cost turns the action-path certification from hygiene into
an effect size other papers can correct for.

**Closest priors.**

- [cua-speedrun](https://arxiv.org/abs/2609.40284), 2026-09-30: App. I Table 20 lists the Qwen3.5 middle-click, Ctrl-release and first-tool-call-only defects; no success cost.
- [What Does a Harness Repair?](https://arxiv.org/abs/2610.05533): preregistered defect-repair accounting on text benchmarks.
- [What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433): a harness swap and a rerun each flip 13% of SWE-bench tasks.
- [Finding the Right Fit](https://arxiv.org/abs/2610.00917) and [FrogNano](https://arxiv.org/abs/2609.07925): model-harness interactions (Qwen3.5-4B 8.3% vs 37.2% under two coding harnesses).
- [Faster and Better? (ICLR 2027 submission)](https://openreview.net/forum?id=1ivlJ9lC5d): benchmark bug fixes reverse VLA-acceleration rankings.

**Citable anchors.**

- 2609.40284. Role: defect source. Status: VERIFIED (full text, slate owner): Table 20 rows.
- Action-path v2 C1 control: H-OSW-up and H-GA-buggy failed each of their 9 known-defect cells in 5 of 5 repetitions. Status: VERIFIED (repository, `q2-action-path-v2-acceptance/README.md`).
- S1a exposure strata. Status: VERIFIED (repository, RESULTS.md).

**First experiment (Stage 0 0 GPU-h; Stage 1 about 2.4 GPU-h, cap 4).**
Stage 0 (CPU): a counterfactual translation census. Apply the frozen
H-GA-buggy and H-OSW-up translators to every recorded model reply in S1a's
H-GA and H-OSW-fixed episodes and count steps and episodes whose executed IR
sequence would differ. The share of episodes touched bounds the share the
defects can flip. Stage 1, only for a pair that Stage 0 touches on at least
10% of episodes: 9B, 113 tasks, certified against defective harness, one
serving session, 2 interleaved reruns: 452 episodes per pair, about 1.2
GPU-h at 0.0027 per episode. **Gate before GPU:** the Stage 0 threshold;
registration, pre-freeze audit and gauntlet (the defect factor is new);
Kevin's admission. Only reviewed harness code and VMs run.

**Decisiveness check.** Stage 0 is a deterministic count and always decides
whether Stage 1 is worth running. A Stage 1 effect on the order of the
exposure share (10-30% of episodes, each flipping only sometimes) may sit
inside S1a's resolution at 113 tasks; the registration must show by
simulation, with S1a's variance components, that PRESENT or NEGLIGIBLE is
reachable with probability at least 0.8 at the Stage 0 exposure.

**Kill criteria.** Stage 0: fewer than 5% of episodes touched in both pairs:
stop and report the bound. Stage 1: δ_defect's 90% upper bound below 2 pp in
both pairs: publish the negative (known defects do not explain harness gaps
on this lane). More than 5% of defective-arm episodes lost to infrastructure
or unparseable replies: report separately, do not read δ_defect as a task
effect. Rerun discordance differing by more than 2x between arms: descriptive
only.

**Relation to the existing program.** Uses the frozen C1 controls of the
action-path suite (D53) and S1a's per-step records. Complements S1a's harness
answer (D69) by asking what an uncertified harness costs.

---

## 5. Checker verdicts under LibreOffice-build and locale changes

`R04-nuisance-invariance`. Origin: cell 1 #4 and cell 4 #3.

**Corrected question.** Apply semantically null environment changes to the
92 save-exposed OSWorld-Verified golds (confirm 67, reserve 25) and to S1a's
544 successful end states. Arm A, application build: the GUI Ctrl+S "Keep
current format", Save As in the same format and the task's headless convert
step, each under LibreOffice builds other than the VM's (Ubuntu's 7.3.7.2):
for example 7.6, 24.2, 24.8 and 25.x. Arm B, locale: keep the interface
language English and change the desktop and LibreOffice locale from en_US to
de_DE, ar_EG, ja_JP and tr_TR (decimal and list separators, digits, date
formats, case mapping), then re-save. Do verdicts under the pinned checker
and under `zinv` change? Readings: INVARIANT if every build and locale keeps
audit-confirmed flips at or below 5% (build) or below a 3% upper bound
(locale) with the same flip set as the control; DRIFT if some build reaches
10% or changes the set by 3 or more tasks, or any checker family shows 2 or
more audit-confirmed locale flips. A separate, descriptive input arm replays
fixed keystroke scripts (typing decimals, dates and times; saving CSV)
through the certified action path on 10 Calc and Writer tasks per locale.

**What is wrong with the naive version.** P1 measured the gold fixed point at
one build and one locale: a GUI-faithful save flips 4 of 92 golds (3
audit-confirmed). The headless scoping round trip flipped 7 of 63 and 1 of 26,
so the save path already matters. Every queued locale study (S2 v3, S3's
locale arm) and every localized benchmark assumes the checkers are invariant
to locale; S2 v2 avoided the question by keeping the system locale English.
OSWorld 2.0 and third-party re-hosts change images, and no one has reported
whether the gold stays a fixed point.

**Novelty.** STILL_OPEN under the cells' coverage. 2607.28367 found one
OSWorld task unsatisfiable on the released image but ran no round-trip test.
2610.09142 tests web/API verifiers. OSWorld 2.0 uses construction-time QA.
2608.20362 shows language-dependent verifier false negatives for math
exact-match, not GUI state checkers. Metamorphic null transformations are
classical (Chen et al. 2018); applying them to desktop benchmark checkers
across builds and locales has no prior found.

**Why it matters.** It is the precondition for every locale study the
program has queued, and for anyone running OSWorld on a re-hosted image. It
runs at zero GPU on built tooling.

**Closest priors.**

- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367): "include a task that is unsatisfiable on the released VM image"; no gold round trip.
- [Finding Blind Spots in AppWorld and WorkArena Task Verifiers](https://arxiv.org/abs/2610.09142): intent-swap census of reference trajectories; web/API.
- [OSWorld 2.0](https://arxiv.org/abs/2606.29537): new images and construction-time QA; no cross-version invariance test.
- [Introducing OSWorld-Verified](https://xlang.ai/blog/osworld-verified): evaluator fixes.
- [Multilingual Verifier Bias in RLVR](https://arxiv.org/abs/2608.20362): exact-match false negatives depend on language (math).
- [macOSWorld](https://arxiv.org/abs/2506.04135): localized environments in five languages; checkers not audited for locale.
- [Metamorphic Testing: A Review of Challenges and Opportunities](https://doi.org/10.1145/3143561) (ACM CSUR 2018).

**Citable anchors.**

- P1 gold fixed point (`q2-mutation-confirm/results/README.md`). Status: VERIFIED (repository).
- LibreOffice build in the VM: `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, "LibreOffice 7.3.7.2" (`program/preregistrations/q2-evaluator-mutation-v1.md` line 184). Status: VERIFIED (repository).
- S1a checker inputs include `registrymodifications.xcu`, where LibreOffice keeps locale settings. Status: VERIFIED (repository, `a1.jsonl`).
- 2607.28367. Status: VERIFIED (full text). 2608.20362, 2506.04135: titles VERIFIED; figures cell-reported.

**First experiment (0 GPU-h; about 10-20 CPU-h for Arm A, similar for Arm
B).** CPU host jobs on the lane, one at a time. Arm A: build 3-4 derived
LO-VM images that differ only in the LibreOffice package (public MPL-licensed
packages, recorded with source, version and SHA-256 under D1), run the
existing `reach.sh` save stage on the 92 golds x 3 save paths x each build,
and score with the pinned `DesktopEnv.evaluate()` and the lock-exact venv.
Arm B: re-save golds and S1a success end states under each locale through
the kit's GUI save path; the en_US re-save is the control. Every flip goes
to the rater pipeline with gold and do-nothing shams; splits to Kevin.
**Gate before GPU:** no GPU step. Preconditions: postconfig replay
(`wmctrl`, `pyautogui`, convert filters) works on at least 90% of golds in a
build; locale data installs offline on the lane image.

**Decisiveness check.** Both arms are counts on fixed populations with
controls (7.3.7 and en_US), so a verdict is always reached; the flip set
comparison (Jaccard) is decisive even when rates are similar.

**Kill criteria.** Drop a build whose postconfig replay fails on more than
10% of golds for reasons unrelated to the checker; stop Arm A if fewer than
2 non-7.3.7 builds remain. The locale run is invalid if the en_US control
flips more often than the kit's gold-rate upper bound (10.8%). INVARIANT
closes the line as an addendum to the checker note. If every flip falls in
one family, fold it into that family's defect report. If raters split on
more than 30% of flips, hold rate claims until Kevin adjudicates. A locale
whose data cannot be installed offline is dropped, not the study.

**Relation to the existing program.** Extends P1 of the mutation study. Gates
S2 v3 (D71 ii) and S3's locale arm; can reuse S2 v3's derived-image tooling in
the CPU lane.

---

## 6. Input-design oracles for TF32: same-sign and exact-lattice families

`R10-input-design-oracles`. Origin: cell 1 #5 and cell 3 #1.

**Corrected question.** Q1's rule `q1-audit-metric/2` leaves 239 of 272
1%-level faults precision-ambiguous under a TF32-admissible contract, because
valid algorithms (Winograd F(4x4,3x3) up to about 45x the yardstick in
max-abs) sit above the median 1% fault (about 15x) on sign-mixed, cancelling
inputs. On the 12 tier-1 S1-cal problems, do two added input families make
those faults decidable without rejecting any valid algorithm class? Family
S (same-sign, plus an offset family for normalization ops so post-centering
terms stay large): outputs are about the size of their terms and TF32 noise
stays near 2^-11 relative. Family L (exact lattice) under an order-free TF32
contract (operands TF32 or finer, fp32 accumulation, any summation order or
partition, no algebraic transforms): L0 dense small integers in [−3, 3],
exact in TF32, bf16 and fp16; L1 sparse probes in (2^8, 2^11], exact in TF32
and not in bf16; L2 exponent-shifted probes, exact in TF32 and out of fp16
range. On L, a zero-tolerance comparison against the fp64 oracle is a valid
verdict for every order-free class. Second question: on what share of
KernelBench L1/L2 problems does a lattice survive to the output or to the
first transcendental?

**What is wrong with the naive version.** "Test with harsher inputs" is
unsound past a measured boundary (2609.22220, Fig. 2b): sign-mixed inputs at
scale push correct kernels out of tolerance. "Use all-positive inputs"
alone is gamed by identity shortcuts (cell 1 reports this from
KernelBench-Verified), so both families are additions to the registered
draws, never replacements. Winograd F(4x4,3x3) is an algebraic transform, so
under the order-free contract it is out of contract, and the report must say
so rather than count it as a rejected valid kernel.

**Novelty.** NARROWED. The same-sign half is narrowed: Measuring the Checker
already uses same-sign magnitudes in its targeted suites and explains why
(fp32 only, no TF32-admissible three-valued rule; the paper never mentions
TF32). The lattice half has no prior found as an oracle for generated float
kernels: FPRev, Accurate Models of NVIDIA Tensor Cores and Hawkeye craft
inputs to reverse-engineer hardware arithmetic, and 2609.00363 uses
accumulator exactness for INT8 conformance. RESOLVE and Dirigo avoid
tolerances but model floats as reals, so they cannot see precision cuts.

**Why it matters.** D46 closed Q1 Stage 0 on a limiting result. If either
family decides 1% faults under TF32, it is the missing piece of the audit
design D46 names for any revival, and it addresses the precision faults
that escape the official check at 78.6% (2609.22220). Model-written kernels
already live in the TF32 regime: 389 of 390 accepted drkernel kernels that
call `tl.dot` use its TF32 default.

**Closest priors.**

- [Measuring the Checker](https://arxiv.org/abs/2609.22220): Fig. 2b and same-sign targeted suites; 78.6% of precision faults escape; fp32 only.
- [KernelBench-Verified](https://arxiv.org/abs/2607.16241): four value transforms; fp32 τ = 1e-3.
- [RESOLVE](https://arxiv.org/abs/2610.05683) and [The Output-Space Hypothesis (Dirigo)](https://arxiv.org/abs/2609.19611): tolerance-free by proof or enumeration over reals.
- [A Contract-Grade Verifier](https://arxiv.org/abs/2608.12700): tolerance-free gates for non-finite masks, determinism, aliasing; no exact-value channel.
- [Revealing Floating-Point Accumulation Orders (FPRev)](https://arxiv.org/abs/2411.00442), [Accurate Models of NVIDIA Tensor Cores](https://arxiv.org/abs/2512.07004), [Hawkeye](https://arxiv.org/abs/2603.20421): crafted inputs for hardware arithmetic.
- [Deterministic LLM Inference Across GPU Kernels](https://arxiv.org/abs/2609.00363): INT8 exactness preconditions.
- [Bounded, Indeterminate, or a Bug](https://arxiv.org/abs/2609.00381): exact/bounded/indeterminate verdicts for SQL aggregates, the same shape as rule /2.
- [The Correctness Illusion](https://arxiv.org/abs/2606.20128): fp64 reference with seeded fuzzing.

**Citable anchors.**

- Q1 audit-metric study (`program/evidence/2026-10-08/q1-audit-metric-study/README.md`). Status: VERIFIED (repository): 239/272, 45x, median 15x, 276/278 strict, 26/122/218 on 366 mutant-family emulations, 1,087 gross decoys rejected, 139 + 83 draws, emulation median ratio 0.996.
- 2609.22220. Status: VERIFIED (full text, slate owner): Fig. 2b text, same-sign suites, 78.6%, zero occurrences of "TF32".
- drkernel `tl.dot` count. Status: VERIFIED (recomputed by the slate owner from the cell-3 parquet, SHA-256 prefix `4ed72a9f`): 390 accepted kernels call `tl.dot`, 389 without an explicit non-TF32 precision.

**First experiment (0 GPU-h; about 2-3 CPU-days on the Mac).** D28-safe: the
12 tier-1 S1-cal problems only, with D28 refusals kept. Add families S and L
to `cpu_study.py`'s draws (parameters overridden the way gate (c) and A2
already do). Run every `alt_algorithms.py` class plus TF32 Winograd
F(4x4,3x3); record exactness per draw on L. Score the 1,087 gross decoys, the
366 mutant-family emulations, the 272 1% faults and new fp16/bf16
operand-cast, accumulator and store decoys under rule /2 and, on L, zero
tolerance (transcendental epilogues with a stated ulp bound at exact
pre-activations). Run the S1-cal Triton AST mutants under
`TRITON_INTERPRET=1` on L. Then a static op-graph census of all 250
KernelBench problems for lattice survival. **Gate before GPU:** this CPU run
is the gate and the gauntlet's executable pilot (new mechanism). A later
trusted-code device check (cuBLAS/cuDNN TF32 and Inductor templates on L,
0.3-0.5 GPU-h) needs Kevin to lift D46's stop.

**Decisiveness check.** Exactness on L is a deterministic property per
draw and class; the reject rates are counts over fixed fault sets. Every
registered verdict is reachable from the CPU run alone.

**Kill criteria.** KILL if any order-free valid class (K-blocked fp32,
sequential, K-blocked TF32 RNE or RZ, any SR seed, Winograd F(2x2,3x3)) is
non-exact on any L draw, or any valid class or correct realization is
rejected under S. KILL if the families together decide fewer than 80% of
the 361 items rule /2 leaves ambiguous (239 1% faults plus 122 mutant-family
emulations), or miss more than 5% of the faults rule /2 already rejects.
LIMITED if fewer than 50% of ambiguous 1% faults are decided on at least 6
of 12 problems. KILL the census claim if fewer than 40% of L1/L2 problems
keep a lattice to the output or first transcendental. If decidability comes
only from matmul and convolution, write a scoped note in the Q1 record, no
new line. NARROW if the device check finds cuDNN's default TF32 algorithm is
a transform on more than 50% of S1-cal conv draws (the order-free contract
then excludes the PyTorch default).

**Relation to the existing program.** The audit half of a Q1 revival (D46).
Uses `cpu_study.py`, `alt_algorithms.py`, `tf32emu.py` and the decoy battery.
Feeds R11 and R12.

---

## 7. Can kernel benchmarks referee their own TF32 baseline?

`R11-tf32-protocol-consistency`. Origin: cell 3 #2 and cell 5 #5.

**Corrected question.** For each active KernelBench problem and each
published correctness protocol (KernelBench allclose at 1e-2 on
`torch.rand`; KernelBench-Verified's fp32 τ = 1e-3 on four value
distributions with a TF32 timing baseline; Q1's rule /2): does a correct
TF32 implementation pass (RNE and RZ emulations, K-blocked orders, Winograd
where cuDNN could pick it); does a destroyed output pass (zeros, negation,
last tile zeroed, largest element zeroed); does a bf16-operand or fp16-store
variant pass; and what is the smallest relative fault the protocol rejects
without rejecting a valid algorithm class? Classify each (problem,
protocol) as certifies-1%, certifies-gross-only, vacuous, unrefereeable or
bf16-blind. Prediction from Q1's 12 problems: on compute-bound L2 problems
the TF32-baseline protocol is either unrefereeable or bf16-blind. On device,
for the 12 S1-cal problems, does the ambiguity band exist on hardware (the
99th-percentile valid-variant ratio above the median 1%-fault ratio on at
least 6 of 12)?

**What is wrong with the naive version.** KernelBench-Verified made TF32 the
speed baseline (GPT-5.5's speedup falls from 1.43x to 0.88x) but kept a
single fp32 tolerance; its text does not say whether the allclose reference
runs with TF32. Measuring the Checker audited fp32 at 1e-2 and never mentions
TF32. Q1 found strict fp32 rejects 55 correct kernel-draws on cuDNN-TF32
problems, while TF32-admissible tolerance cannot decide 1% faults: the two
choices fail in opposite directions. The zeros-pass defect alone is
published (2609.21058: zeros pass allclose on 4 of 60 L1 problems), so it is
not a contribution here.

**Novelty.** STILL_OPEN for the TF32-contract consistency audit (no prior
found under cell 3's queries); the zeros-normaliser facet is OCCUPIED by
2609.21058. 2607.16228 calibrates per-operator tolerances without an
algorithm-class yardstick or TF32 contract; 2608.12700 names matmul "the
worst case for the TF32 tolerance argument" and strips it rather than
resolving it.

**Why it matters.** It says, problem by problem, which published kernel
benchmark verdicts mean "correct to 1%" and which mean "not grossly wrong".
That is the input every kernel RL reward, including Q1's, needs.

**Closest priors.**

- [KernelBench-Verified](https://arxiv.org/abs/2607.16241): fp32 τ = 1e-3, BF16 τ = 1e-2; TF32 baseline affects compute-bound problems (21.2% of problems); H200.
- [Measuring the Checker](https://arxiv.org/abs/2609.22220): fp32 at 1e-2; unrefereeable L3 problems; no TF32.
- [How Much of a Real Workload Can LLM-Generated GPU Kernels Actually Reach?](https://arxiv.org/abs/2609.21058): zeros pass on 4 of 60 L1 problems; scale-invariant checks proposed.
- [Operator-Aware Mixed-Precision Tolerance Calibration](https://arxiv.org/abs/2607.16228), [A Contract-Grade Verifier](https://arxiv.org/abs/2608.12700), [The Correctness Illusion](https://arxiv.org/abs/2606.20128), [Bounded, Indeterminate, or a Bug](https://arxiv.org/abs/2609.00381).
- [KernelAudit (ICLR 2027 submission)](https://openreview.net/forum?id=yTa4gvQUGG).

**Citable anchors.**

- 2607.16241. Status: VERIFIED (full text, slate owner): τ values, 1.43x to 0.88x, 21.2%, H200.
- 2609.21058. Status: VERIFIED (full text, slate owner): 4 of 60.
- Q1 study: strict rejects 55 correct kernel-draws (95 rows); pilot 0.57 GPU-h, 1.14 with a 2x margin, time box 1.2. Status: VERIFIED (repository).

**First experiment (0 GPU-h; about 3-5 CPU-days on the Mac; optional device
pilot 1.2 GPU-h).** The 197 active L1/L2 problems (KBV's three constant-zero
L2 problems excluded) plus a stratified 15 of the 50 L3 networks; under D28,
exclude problems hosting Q1 evaluation units or record Kevin's release. Per
problem, compute the fp64 oracle, emulated TF32 references (RNE, RZ,
K-blocked), fp32 alternative orders, Winograd variants on 3x3 convolutions,
bf16-operand and fp16-store variants and the decoy battery, under each
protocol's own inputs and tolerances. Read KBV's released harness first to
fix whether its reference runs with TF32; score both readings if it cannot be
settled. Device pilot (only after the CPU audit, trusted code only): the
shelved rule /2 pilot on the 12 S1-cal problems with forced cuDNN algorithm
variants and per-process repeats. **Gate before GPU:** the CPU census;
Kevin's D14 ruling on TF32 truncation; Kevin lifting D46's stop for the
pilot. Registration and pre-freeze audit.

**Decisiveness check.** The classification is deterministic per problem
under the emulation; the device pilot's band test is a per-problem
comparison of quantiles with registered thresholds.

**Kill criteria.** KILL with a short negative note if fewer than 5% of the
problems KBV marks TF32-affected are unrefereeable or bf16-blind under KBV's
protocol, or if more than 80% of L1/L2 problems certify 1% faults under the
TF32-admissible contract. HOLD the emulation classes if the device spot check
is off by more than 2x on more than 10% of sampled problems. Drop the band
claim if, on device, the 99th-percentile valid-variant ratio is below 4x on
at least 10 of 12 problems while 1% faults exceed 8x on at least 90% of
draws. If Kevin rules TF32 truncation inadmissible (D14), reduce the band
claim to a policy remark (strict fp32 decided 276 of 278 faults on CPU).

**Relation to the existing program.** Generalizes Q1's limiting result (D46)
from 12 problems to the benchmark; the device pilot is D46's priced revival
step. Shares emulation tooling with R10.

---

## 8. Checker-revision drift on fixed end states, then an external anchor

`R05-checker-revision-drift`. Origin: cell 2 #5.

**Corrected question.** G0 excluded 110 of 116 tasks from S1a's anchor
because a config or the AST of a reached checker definition differed between
the public runs' revision (`00804f8`, inferred from the run window) and the
pinned one (`b138d34`). On S1a's real file-based end states for the 74
excluded tasks whose config is unchanged (the differences are mostly getters:
`get_vm_file` on 103 tasks, `get_cloud_file` on 84), do the two revisions
agree on at least 98% of episodes, offline (metric code on captures) and in
the VM (getters plus metrics through `DesktopEnv.evaluate`)? Only if they
agree: does a self-hosted 15-step rerun of a public open-weight agent on the
revision-invariant tasks reproduce its public per-task success within the
measured rerun band (at most 2 SE)?

**What is wrong with the naive version.** The exclusion rule was syntactic,
so its effect on verdicts was never measured; most AST differences may be
verdict-preserving. But the 36 excluded tasks whose config changed cannot be
re-admitted by any checker test, because the task itself changed. The
re-admittable ceiling is 6 kept plus 74, which still clears the anchor floor
of 58.

**Novelty.** STILL_OPEN under cell 2's coverage (no direct prior found for
verdict drift across OSWorld checker revisions on fixed end states).
2609.34198 studies version-dependent LLM-judge error, not programmatic
checkers; 2607.28367 names stale tasks as a threat without rescoring.

**Why it matters.** "Not externally anchored" is on every S1a number and is
the largest validity gap in the program's spine result.

**Closest priors.**

- [OSWorld](https://arxiv.org/abs/2404.07972) and the public trajectory archive [xlangai/ubuntu_osworld_verified_trajs](https://huggingface.co/datasets/xlangai/ubuntu_osworld_verified_trajs) (MIT): published runs span checker revisions.
- [Frozen Judges, Moving Agents](https://arxiv.org/abs/2609.34198): judge error depends on version.
- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367): broken and stale tasks.
- [On the Reliability of Computer Use Agents](https://arxiv.org/abs/2604.17849): changes instructions, not checker revisions.

**Citable anchors.**

- G0 evaluator diff (`program/evidence/2026-10-08/q2-stage1-g0/anchor/evaluator-diff.json`). Status: VERIFIED (repository, recounted by the slate owner): 110 excluded, 74 with equal config, 36 with changed config, 6 kept; `get_vm_file` 103, `get_cloud_file` 84.
- OpenCUA-7B 15-step archive member, 7,920,092,071 bytes (`program/evidence/2026-10-06/holo3/README.md`). Status: VERIFIED (repository).

**First experiment (0 GPU-h drift test; about 0.8-1.1 GPU-h anchor).** CPU
on the host lane: take 300 S1a end states stratified over the 74 tasks,
file-based checkers only; rescore offline under both revisions' metric code;
re-materialize in the certified VM and run both revisions' `evaluate()`.
Report agreement by changed function. Only at 98% or more: register an anchor
run (OpenCUA-7B, 15 steps, R = 3 on the revision-invariant tasks, about 300
episodes). **Gate before GPU:** agreement at least 98%; at least 58
revision-invariant tasks; Kevin's ruling on running OpenCUA-7B's remote code
(as D29 ruled for upstream test code) and his OK for the archive download.
Registration and pre-freeze audit.

**Decisiveness check.** The drift test is a count with a fixed threshold.
The anchor reading has a registered stop rule (more than 2 SE beyond the
band), so it decides or stops the instrument.

**Kill criteria.** Agreement below 95%: revisions are not comparable on fixed
states; the drift table is the finding and no cross-revision anchor is
attempted. Between 95% and 98%: anchor only on tasks with zero disagreement,
and only if at least 58 remain. If Kevin declines the remote-code ruling or
the download, stop after the drift test. If the anchor differs from the
public runs by more than 2 SE beyond the rerun band, stop and debug the
instrument before any further Q2 claim (the question file's Holo3 rule).
Live-state checkers stay out of scope.

**Relation to the existing program.** Closes S1a's DR-A label if it works.
Reuses S1a's captures and R03's in-VM executor.

---

## 9. Interpreter-executed audit of model-written Triton kernels

`R12-interpreter-kernel-audit`. Origin: cell 3 #3 and #4.

**Corrected question.** Stage 1, archive: on the accepted best-round kernels
of `hkust-nlp/drkernel-coldstart-8k` (MIT; 8,920 trajectories, 8,462 with
recorded `final_speedup` > 0), executed only in Triton's CPU interpreter
inside a GPU-less, network-less container with `tl` operations instrumented
to log formats used: what fraction are (i) semantically wrong under a
strict-precision audit (fp64 oracle, KBV hidden values, held-out shapes,
R10's lattice draws); (ii) cutting precision at runtime (fp16/bf16 operands,
accumulators or stores at fp32 inputs); (iii) of those, landing in rule /2's
TF32 ambiguous band? Is the recorded speedup higher for (ii)? Stage 2,
on-policy (only if Stage 1's fidelity leg passes): freeze a licensed open
Triton policy (AutoTriton), sample about 2,000 kernels on GPU (generation
only), execute everything in the interpreter, and test Q1's kill line: do
gate (a) official allclose or gate (b) the KernelGYM-style check accept at
least 3 pp more audit-rejected kernels than gate (c) hidden values plus
shapes, with non-overlapping CIs, at matched verification cost?

**What is wrong with the naive version.** Source-level scans cannot answer
(ii): the cell's regex scan found downcast patterns in 321 of 8,462 accepted
kernels, 177 of them beside dtype-conditional branches, and the speedup
association reversed once comments and dispatch code were separated. The
interpreter also changes arithmetic: `tl.dot` runs in fp32 NumPy, so TF32
noise disappears (semantic 1% faults become decidable) while explicit casts
are still honoured, but races are serialized and bf16 handling and
out-of-bounds behaviour may differ. Fidelity must be measured on trusted
kernels before any archive rate means anything.

**Novelty.** NARROWED. The Contract-Grade Verifier audits 2,638 accepted
kernels from the same corpus on B200 (39.5% broken in a way no tolerance
excuses). Dirigo finds bugs in AI CUDA Engineer kernels by symbolic
execution over reals. KernelAudit audits 505 on-policy accepted kernels.
Residual: GPU-free execution as the audit path, runtime format provenance at
fp32 inputs, all 8,462 kernels, placement against the TF32 band, and an
on-policy gate comparison that R570 does not block.

**Why it matters.** Q1 Stage 1 has been blocked by R570 since 2026-10-06
(D2, D7). For Triton, the interpreter path removes that block. Stage 1 also
tests Q1's premise at scale: Measuring the Checker's realism probe found few
incorrect LLM kernels, and a near-empty TF32 band on real kernels would close
Q1's premise rather than revive it.

**Closest priors.**

- [A Contract-Grade Verifier](https://arxiv.org/abs/2608.12700): same corpus, 2,638 kernels, B200.
- [The Output-Space Hypothesis (Dirigo)](https://arxiv.org/abs/2609.19611): enumerative equivalence checking for tensor programs.
- [Measuring the Checker](https://arxiv.org/abs/2609.22220): realism probe.
- [KernelAudit (ICLR 2027 submission)](https://openreview.net/forum?id=yTa4gvQUGG): 505 accepted kernels.
- [Dr. Kernel / KernelGYM](https://arxiv.org/abs/2602.05885), [KernelZero](https://arxiv.org/abs/2609.33074), [AutoTriton](https://arxiv.org/abs/2507.05687), [TritonRL](https://arxiv.org/abs/2510.17891): policies and verifiers.
- [When the Reward Suite Is Leaky](https://arxiv.org/abs/2607.11022): preregistered leaky-vs-hardened test-suite GRPO contrast on MBPP; the hardened suite is non-inferior.
- Corpora: [drkernel-coldstart-8k](https://huggingface.co/datasets/hkust-nlp/drkernel-coldstart-8k) (MIT), [AI-CUDA-Engineer-Archive](https://huggingface.co/datasets/SakanaAI/AI-CUDA-Engineer-Archive) (CC-BY-4.0).

**Citable anchors.**

- drkernel counts. Status: VERIFIED (recomputed by the slate owner): 8,920 rows, 8,462 with `final_speedup` > 0, 390 `tl.dot` users, 389 on the TF32 default. The 321 / 177 / 144 downcast counts and the 1.49 vs 2.06 median speedups are cell-reported regex results, provisional.
- 2608.12700. Status: VERIFIED (title; 39.5% from the 2026-10-06 dossier's full-text check).
- AutoTriton licence (Apache-2.0) and drkernel licence (MIT): cell-reported from Hugging Face tags; verify the model card before Stage 2.

**First experiment (Stage 1: 0.3 GPU-h trusted fidelity leg; archive leg 0
GPU-h, about 70 CPU-h).** (1) Fidelity: run Q1's S1-cal Inductor Triton
substrates and harness-derived AST mutants (D3-compliant) on device and in
the interpreter; measure verdict agreement per fault family. (2) Archive: a
stratified sample of 2,000 accepted kernels by operator class, sandboxed (no
network, no GPU, resource limits) at reduced shapes, under gates a-c, the
strict interpreter audit and lattice draws, logging the dtype of every
`tl.dot`, `tl.store` and accumulator; the first 200 measure CPU cost.
Stage 2 (about 1.5 GPU-h generation, 150-300 CPU-h execution) is a separate
registration with its own gauntlet. **Gate before GPU:** Kevin lifting D46's
stop for the trusted fidelity leg; for Stage 2, a fidelity pass, a verified
policy licence (D5's rule), the gauntlet and Kevin's admission.

**Decisiveness check.** Archive rates are proportions over a fixed sample;
the "near-empty band" outcome is registered as a decisive negative. Stage 2
inherits Q1's 40-kernel floor for a decisive reading.

**Kill criteria.** KILL the archive leg (publish only the fidelity map) if
interpreter-device agreement is below 95% on trusted mutants outside the
race/sync families. KILL as "no new population" if runtime-confirmed
precision cuts are under 2% of accepted kernels and the strict semantic-fault
rate is within 3 pp of CGV's on overlapping classes. Fewer than 30 sampled
kernels in the TF32 band: record that Q1's 1%-fault band is nearly empty on
real model kernels. Stage 2: proceed toward any RL arm (its own gauntlet,
D24) only if FA(a) or FA(b) minus FA(c) is at least 3 pp with non-overlapping
CIs and gate (c) costs at most 2x gate (b); stop as decisive negative if fewer
than 40 kernels are gate-(a)-accepted but audit-rejected among about 2,000.

**Relation to the existing program.** A path to Q1's on-policy audit that
the R570 rule does not block, because untrusted Triton runs only off-GPU
(D3, D7). The licence block (D5) needs a licensed policy such as AutoTriton,
and the TF32 audit block (D46) is what R10 addresses. Uses Q1's admission
check, CPU doctor and interpreter integration test. Depends on R10 for
lattice draws.

---

## 10. What the cross-lingual long-context penalty is made of

`R14-crosslingual-lc-decomposition`. Origin: cell 4 #1, #4 and #5.

**Corrected question.** Qwen3.5-4B and 9B (hybrids), with Qwen3-8B as a
full-attention contrast, at fixed context length and needle depth. When the
question and the needle are in different languages, retrieval accuracy
drops. How much of that drop remains when the comparison is a same-language
question that shares no token with the needle? Design: within-item synthetic
one-hop needles from Wikidata labels (CC0), haystack in the needle's
language, crossing language match {same, different} with literal key
{shared surface form, none}, plus a same-language cross-script leg (question
in Serbian Latin, needle in Serbian Cyrillic: same words, no shared token).
Readings: TOKEN (the cross-language penalty equals the same-language
no-shared-token penalty, and the Serbian cross-script cell pays it), WORD
(the Serbian cell pays nothing while translations pay the no-literal
penalty), LANGUAGE (a cross-language deficit remains beyond the same-language
no-literal cell). Primary statistic: per cell, accuracy at 16K minus at 1K on
the logit scale, with the retained-headroom form as a check. Conditional
follow-ons, each its own registration: (C) forced answer-turn prefixes
(faithful translation with the key, translation with the key replaced,
length-matched restatement) test whether translate-then-answer gains are
carried by recreating the literal key; (D) a digraphic token-distance test
(Serbian Latin vs Cyrillic at token-matched and content-matched depths).

**What is wrong with the naive version.** Q3's K1 v3 ended partly because GO
was not identified against question-side literal priming: question content
overlap was 0.38-0.68 on MN against 0.00-0.04 on CX, with no same-language
zero-overlap leg (D54). The dense pre-check found the lexical confound
PRESENT and entity control INSUFFICIENT, and needle fertility tracked
headroom (Spearman −0.89 over 7 languages). Cross-language comparisons move
script, resource level, fertility and literal overlap together. This design
makes the confound the measured variable and removes K1's decisiveness defect:
no trained component, so no seed SD.

**Novelty.** NARROWED. NoLiMa separates literal from minimal-overlap needles
in English only. MLNeedle and OneRULER measure cross-lingual needles without
overlap control. XHotpotQA treats script as a descriptor. One Language, Two
Scripts uses Serbian digraphia for SAE features, not retrieval. Residual: the
within-item overlap-by-language factorial with a zero-shared-token
same-language leg.

**Why it matters.** It says whether multilingual long-context gaps are about
language or about tokens, which changes what to fix (retrieval heads,
tokenizers or prompting) and what every multilingual long-context benchmark
must control.

**Closest priors.**

- [NoLiMa](https://arxiv.org/abs/2502.05167): English; attention struggles without literal matches.
- [Multilingual Needle in a Haystack (MLNeedle)](https://arxiv.org/abs/2408.10151), [OneRULER](https://arxiv.org/abs/2503.01996), [mLongRR](https://arxiv.org/abs/2409.18006), [CROSS (ICLR 2025 workshop)](https://openreview.net/forum?id=sOXznQZgnM): cross-lingual needles, no overlap control.
- [XHotpotQA](https://arxiv.org/abs/2608.27481), [Measuring the Cross-Lingual Comprehension Gap](https://arxiv.org/abs/2608.06506), [Lost in Compression](https://arxiv.org/abs/2608.26175).
- [One Language, Two Scripts](https://arxiv.org/abs/2603.08869): digraphia as a testbed.
- [Logit-Contribution Scoring Identifies Non-Literal Retrieval Heads (LOCOS)](https://arxiv.org/abs/2607.01002), [Retrieval and Retrieval-Transition Heads](https://arxiv.org/abs/2602.22453).
- For (C): [Do Multilingual Language Models Think Better in English?](https://arxiv.org/abs/2308.01223), [Multilingual Reasoning Cascades Need More Context](https://arxiv.org/abs/2606.27306), [Reasoning-Language Alignment in Monolingual RAG](https://arxiv.org/abs/2610.03136), [Skill Issue](https://arxiv.org/abs/2608.25832).
- For (D): [The African Language Tax](https://arxiv.org/abs/2606.24460), [The Invisible Language Tax](https://arxiv.org/abs/2609.39001), [Beyond Two Bytes per Letter](https://arxiv.org/abs/2608.21384), [Dense Contexts Are Hard Contexts](https://arxiv.org/abs/2606.06203), [How Linear Attention Remembers](https://arxiv.org/abs/2609.33093).

**Citable anchors.**

- Q3 dense pre-check v2 (`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/README.md`). Status: VERIFIED (repository): Delta_T 2.23 (0.44-3.87), PRESENT / INSUFFICIENT, Spearman −0.89, harness reproduction gap exactly 0.0, 0.1542 GPU-h for the 4B lane.
- D54 overlap figures. Status: VERIFIED (repository).
- Tokenizer check (Serbian Latin 1.99x and Cyrillic 2.50x English fertility; 2 shared token ids, both punctuation): cell-reported, on the Qwen3-VL tokenizer as a proxy for Qwen3.5's, one paragraph. Provisional.
- Prior titles: VERIFIED (orx lookup); figures quoted from priors are cell-reported.

**First experiment (Phase 0 0 GPU-h; Stage A about 1 GPU-h).** Phase 0
(CPU): 400 one-hop relations from Wikidata labels in en, zh, ar, ru and sr
(Latin Serbian by deterministic transliteration); haystacks from FineWeb-2
in the needle's language, digests only committed; zero shared token ids
between question and needle in every no-literal and Serbian cell under the
Qwen3.5 tokenizer after NFKC with punctuation dropped from questions (E7's
lesson); a surface-twin decoy needle per item; answers scored against
Wikidata aliases in all five languages, with the scorer mutation-tested on
200 planted correct variants. Stage A (Qwen3.5-9B; zh and sr; 200 relations;
1K and 16K) measures the ceiling, the literal headroom and the paired item
SD, and fixes Stage B's N so that P(decisive) is at least 0.8 before Stage B.
Stage B: 4B and 9B, four languages, 400 relations, two depths, 1K and 16K,
plus a dense-capture attention readout on 4B (4-5.5 GPU-h). **Gate before
GPU:** the overlap audit reaches zero shared tokens; the scorer rejects no
planted correct variant; simulation shows each verdict reachable by a
non-oracle model and the surface-twin decoy reading null; gauntlet (new
mechanism) and Kevin's admission.

**Decisiveness check.** Paired synthetic items, greedy decoding and no
training make N the only lever, and Stage A measures the item SD that sets
N. Stage D is the riskiest: a 1.26x token ratio separates TOKEN from CONTENT
by only a few points unless accuracy falls steeply with distance, so it runs
only if Stage A's curve supports P(decisive) at least 0.8.

**Kill criteria.** Stop at 0 GPU-h if the overlap audit cannot reach zero
shared tokens or the scorer misses any planted variant. Stop after Stage A if
fewer than two cross-script languages pass the 85% ceiling at 1K, or the
same-language literal effect is under 10 pp at 16K and still under 10 pp
after one move to 32K. Verdicts on 90% item-cluster bootstrap intervals:
TOKEN if the cross-language excess over the same-language no-literal cell
lies within ±4 pp and the Serbian cell loses at least half the literal
effect; WORD if the Serbian cell lies within ±4 pp of the literal cell while
translations lose; LANGUAGE if the excess's lower bound is at least 4 pp. A
MIXED reading with an interval wider than 12 pp stops the line. (C) runs
only if the faithful translation gains at least 3 pp over no prefix at 16K in
some language, and is invalid if the restatement differs from no prefix by
more than 3 pp. (D) drops Serbian if its Qwen3.5 token ratio is under 1.15.

**Relation to the existing program.** Repairs the identification defect that
ended Q3's K1 v3 (D54) with a design that needs no trained indexer. Uses the
dense-capture harness and the serving probe's throughput. Shares items with
R15's translation tooling.

---

## 11. Translated instructions in a desktop agent: language or lost referents?

`R15-translated-cua-referents`. Origin: cell 4 #2.

**Corrected question.** On S1a's certified stack (English interfaces and
documents, H-OSW-fixed, Qwen3.5-9B, greedy, 15 steps): when the instruction
is in Arabic, success drops. How much of the drop comes from translating the
on-screen referents the agent must find (UI labels; sheet, column, slide
and folder names quoted from the screen or document), and how much from the
instruction's language? Within-task conditions: E (English original),
T_pres (Arabic with every referent kept verbatim in English), T_full (Arabic
with referents translated). Values the agent must type are byte-identical in
all three. Estimands, paired by task: anchor effect A = T_pres − T_full and
language effect L = E − T_pres.

**What is wrong with the naive version.** "Measure the multilingual gap"
conflates the translation policy with the language. macOSWorld kept proper
nouns and file names verbatim and BabelArena preserves execution-critical
values, so each benchmark's gap depends on its own translation rules. And by
D69, a 5 pp effect spread across tasks needs about 100-115 distinct tasks,
more than this stack's informative set: the question must target an effect
that is large where it applies (tasks with referents) and count those tasks
before spending any GPU (S2's lesson, D70).

**Novelty.** NARROWED. macOSWorld measures task-UI language mismatch (1-10
pp, no significance tests, no referent manipulation). BabelArena preserves
values in tool and planning families without GUIs. OmnilingualGAIA2 names
morphological cue loss by human analysis. Lexical Coupling in GUI Element
Grounding is monolingual. No prior found manipulates the referent
translation policy within task on a desktop stack.

**Why it matters.** It tells localized-benchmark builders which translation
choice they are measuring, and it is the program's cheapest locale question
on the certified stack, separate from S2's interface-direction question.

**Closest priors.**

- [macOSWorld](https://arxiv.org/abs/2506.04135) (NeurIPS 2025): en tasks on an ar UI 33.3% to 22.8% (cell-reported).
- [BabelArena](https://arxiv.org/abs/2609.23490): structure-preserving translation with PRESERVE rules.
- [OmnilingualGAIA2](https://arxiv.org/abs/2608.08775): cross-lingual gap 8.8-18.4 pass@3 (cell-reported).
- [Lexical Coupling in GUI Element Grounding](https://arxiv.org/abs/2608.21794), [Actions Speak Louder than Words (COLM 2026)](https://arxiv.org/abs/2608.11110).
- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367): checker error as a confound.

**Citable anchors.**

- S1a: 9B solved 52 of 113 pool tasks at least once in 8 episodes; 32 are neither always nor never solved. Status: VERIFIED (recomputed by the slate owner from `a1.jsonl`).
- D69's S2 sizing (about 100-115 tasks for a 5 pp gate; LibreOffice's 64 give power 0.60-0.62; all 113 give 0.79-0.83). Status: VERIFIED (repository, `program/decisions.md`).
- Prior titles: VERIFIED (orx); prior figures cell-reported.

**First experiment (Phase 0 0 GPU-h; Phase 1 at most 4.1 GPU-h).** Phase 0
(CPU): span-classify the 52 solved-at-least-once tasks' instructions into
values to type, referents to locate and other text; count a referent as
locatable only if it string-matches the task's initial document or
accessibility text; translate with one frozen model into the two Arabic
variants; gates: values byte-identical, back-translation equivalence at least
0.9, and a referent-recoverability oracle (given screen text and T_full, it
identifies the referent uniquely) at least 95%; re-run S2 v2's beta-binomial
power code on S1a's cells for the surviving K and register P(decisive).
Phase 1: 3 conditions x K (at most 52) x 8 episodes (two sessions x four
reruns), at most 1,248 episodes at V = 20. Scoring uses `zinv` where
`compare_pptx_files` applies. **Gate before GPU:** at least 30 informative
tasks with a locatable referent and P(decisive A) at least 0.8 for a 10 pp
concentrated effect; gauntlet and Kevin's admission.

**Decisiveness check.** Phase 0's count and power gates are designed to stop
at 0 GPU-h if the informative set is too small; with 32 informative tasks at
9B this is a live risk, and the honest expectation is that the gate may
fail.

**Kill criteria.** Stop at 0 GPU-h on either Phase 0 gate. After Phase 1:
E − T_full with a 90% upper bound under 5 pp means nothing to decompose
(publish the null for Arabic instructions on this stack); PRESENT if A's
lower bound exceeds 0 under Holm with L; SMALL if A lies within ±5 pp.
English success on the analysed set outside 15-85% makes the run
uninformative. A second language or the 4B rung is a new registration.

**Relation to the existing program.** Uses S1a's noise floor and records and
the design study's power code. Distinct from S2 (interface direction and
script); overlaps S2's reasoning-language arm (E1's remnant) only in using
Arabic.

---

## 12. A session-inclusive noise band on published OSWorld-Verified claims

`R06-session-band-published-claims`. Origin: cell 1 #3.

**Corrected question.** Build a paired band from components the program
measured: S1a's per-episode rerun variance and task heterogeneity, the 9B
session shift, and session terms estimated from public maintainer reruns
(the Holo3 pair and the OpenCUA turn sets). Apply it to 2025-2026 published
OSWorld or OSWorld-Verified improvement claims of at most 6 pp. What share
stays distinguishable from zero at 95%? H-ROBUST: at least 70% survive with
the session term at its upper estimate. H-FRAGILE: at most 30% survive with a
session term, against at least 60% with task sampling alone.

**What is wrong with the naive version.** "Add error bars" with task
sampling alone misses the one component prior leaderboard audits do not
model: a session term. The program has direct evidence that one exists and
is pair-specific: the Holo3 maintainer pair is not exchangeable (exact
McNemar 25 vs 9, p 0.009; |z| 2.74 against a reference maximum of 1.86) and
no registered mechanism explains it (Holo3 v2), while OpenCUA's turn sets
show none (pooled mean-square ratio 0.663 on (12, 4282) df). S1a's P1 test
found no between-session excess (upper bound 0.78 pp) even as 9B's own
session test rejected (+5.5 pp, p 0.016). A single pooled session SD may
therefore misdescribe the term.

**Novelty.** NARROWED. 2609.17394 separates none of 29 adjacent SWE-bench
Verified pairs by exact McNemar, with no session term. 2610.00651 decomposes
variance over 22 HAL/Harbor benchmarks with few repeated cells; 2608.11323
applies G-theory to other agent benchmarks. Residual: a desktop band with a
session component from same-agent maintainer reruns.

**Why it matters.** It tells readers which published desktop-agent gains
are distinguishable from noise under a realistic variance model, at zero GPU.

**Closest priors.**

- [Coding Agents Have Converged](https://arxiv.org/abs/2609.17394): none of 29 adjacent pairs separated.
- [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651), [Deployment Decision Reliability](https://arxiv.org/abs/2608.11323), [What Does an LLM-Agent Leaderboard Rank Actually Compare?](https://arxiv.org/abs/2609.07785), [Identical Runs, Different Results](https://arxiv.org/abs/2609.33812), [Is This Agent Evaluable? (ICLR 2027 submission)](https://openreview.net/forum?id=3vXI4xEByc): swapping tasks moves scores 6.2x more than rerunning.
- [Signal and Noise](https://arxiv.org/abs/2508.13144), [Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640).

**Citable anchors.**

- Holo3 v1 post-hoc and v2 (`program/evidence/2026-10-06/holo3/results-v1-posthoc.md`, `program/evidence/2026-10-07/holo3-v2/RESULTS.md`). Status: VERIFIED (repository).
- 2609.17394. Status: VERIFIED (full text, slate owner). 3vXI4xEByc: VERIFIED (api2 abstract).

**First experiment (0 GPU-h, CPU on the Mac).** (1) Census: per-task outcome
availability in the public trajectory archive at the pinned revision, from
file metadata only; claims (delta, task count, runs, pairing) extracted from
OSWorld-Verified papers via orx retrieval and frozen before any band is
computed. (2) Fit a session SD from S1a's sessions, the Holo3 pair and the
OpenCUA turns with the design study's model code plus a session random
effect, with a pair-specific alternative. (3) Per claim, the paired 95% band
under session SD in {0, pooled fit, Holo3-type upper}; per-task outcomes
where public, otherwise a conservative bound from the claim's success rates
and S1a's task correlation. Report survival shares and the GPU-h at S1a's
price a claim would need to become decisive. **Gate before GPU:** no GPU
step.

**Decisiveness check.** The survival shares are computed, not sampled; the
risk is the census (too few claims with stated task counts).

**Kill criteria.** Fewer than 20 extractable claims with task counts: report
the census and stop. Session SD upper bound below 1 pp across sources: the
analysis reduces to a desktop copy of 2609.17394; a short methods note at
most. Per-task outcomes public for fewer than 5 agents: bound-based reading
only, labelled conservative, no per-pair claim. Survival shares under the 0
and Holo3-type settings within 10 pp of each other: record the negative and
close.

**Relation to the existing program.** Turns S1a, Holo3 v1/v2 and the design
study into an external calibration; a candidate section of the Q2 technical
report (D71 iii).

---

## 13. Accessibility tree on the certified path vs S1a's floor

`R08-a11y-observation`. Origin: cell 2 #3.

**Corrected question.** On the 113-task pool with the action path unchanged,
does adding the linearized accessibility tree to each screenshot
(H-OSW-fixed+a11y, truncated at a registered token cap) change Qwen3.5-9B
success, on average (δ_obs) and task-specifically (X_obs, π_obs), using S1a's
estimators? H1: π_obs's one-sided 95% lower bound above 0.13, or δ_obs's 90%
interval beyond ±5 pp. Null: δ_obs within ±3 pp and π_obs's upper bound below
0.12.

**What is wrong with the naive version.** OSWorld's original comparison
found accessibility-tree effects that vary and reverse across models, from
single runs of closed models with no noise floor. S1a could not test the
factor because both certified harnesses read screenshots only (D47), and S1b
closed without it (D69). The accessibility service also has a known
whole-boot failure mode (A7 session 193: HTTP 500 on every call) that the
suite reports but does not bound.

**Novelty.** NARROWED. OSWorld (2404.07972) and 2608.06171 (web, rerun band
in 2 of 8 cells) cover the observation factor without a desktop floor;
2607.04334 probes belief, not task success; StateAct and A11y-Compressor
propose formats.

**Why it matters.** It closes, or reopens, Q2's interface question for this
family on the certified stack. A null extends S1a's conclusion that interface
variation is dominated by tasks and reruns.

**Closest priors.** [OSWorld](https://arxiv.org/abs/2404.07972);
[Routing Is Least Learnable Where It Is Most Valuable](https://arxiv.org/abs/2608.06171);
[Do GUI Agents Believe Their Eyes?](https://arxiv.org/abs/2607.04334);
[StateAct](https://arxiv.org/abs/2607.22798);
[A11y-Compressor](https://arxiv.org/abs/2605.00551);
[Agent-Computer Observation Interfaces](https://arxiv.org/abs/2606.29472).

**Citable anchors.**

- A7: 0 restarts in 39,036 calls, exact upper 95% bound 7.67e-5 per call; session 193. Status: VERIFIED (repository).
- S1a secondary π_small 0.084 (one-sided [0.020, 0.162]). Status: VERIFIED (repository).
- Design study J2 (9B, K113, S2 R2): 198 cap-minutes. Status: VERIFIED (repository).

**First experiment (about 2.6-2.7 GPU-h physical, about 3.3 cap-GPU-h).**
Pre-step (CPU): port the linearization from OSWorld `bfd62bdc` into an
H-OSW-fixed+a11y variant as reviewed project code, record every difference
in the `design_diffs` format, unit-test against upstream outputs on recorded
trees, then an A7-style smoke on the CPU lane (delivery, tree length and
truncation on the 113 initial states). Main run: 9B, both arms interleaved
in each of 2 sessions at least 12 h apart, R = 2: 904 episodes (the J2
structure). **Gate before GPU:** the smoke shows truncation on at most 20% of
steps and context overflow on at most 1%; a whole-boot guard for the session-193
pattern; gauntlet (new factor, D66) and Kevin's admission.

**Decisiveness check.** For the harness contrast with the same structure,
the design study puts the probability of a decisive DR2 at 0.50-0.70 for J2
and 0.97-0.99 for J (9B, K113, S4 R2, 390 cap-minutes, 6.5 GPU-h), under
S1a-anchored scenarios. The observation contrast's variance is unmeasured, so
the registration must either accept an inconclusive outcome as reportable or
move to the J structure.

**Kill criteria.** Re-register the cap first if truncation exceeds 20% of
steps or overflow 1%. Count whole-boot accessibility failures as
infrastructure losses; stop if a11y-arm losses exceed 2%. Cut to 9B only if
the a11y arm costs more than 1.5x per episode. Report descriptively if the
informative-task share is below 25%. Falsifier and null as stated.

**Relation to the existing program.** The observation factor S1b would have
carried (D47, D69), now as its own small question.

---

## 14. The speed premium of a pure precision cut, per gate

`R13-precision-premium`. Origin: cell 3 #5.

**Corrected question.** On each compute-bound KernelBench problem, how much
speedup over the TF32 PyTorch baseline does a precision cut alone buy, using
trusted variants only (bf16 and fp16 autocast, cuBLAS reduced-precision
reductions, fp16 accumulation, fp8 `scaled_mm` where shapes allow, Inductor
max-autotune at each precision)? Which variants does each gate accept
(KernelBench 1e-2, KBV 1e-3 on four distributions, the KernelGYM-style check,
rule /2 under TF32 and strict contracts, and R10's lattice oracle if it
survives)? A gate's premium is the geomean speedup of the fastest variant it
accepts. Question: is the premium at least 1.3x under gates used as RL
rewards and about 1.0x under a contract-aware oracle?

**What is wrong with the naive version.** Low prevalence of precision cuts
in archives (cell-reported: about 1.7% unconditional-looking downcasts in
drkernel's accepted kernels; 0.1-0.3% explicit half/bf16 in Sakana's correct
L1/L2 kernels) cannot distinguish "policies do not know the cut" from "the
cut does not pay". The detection side is measured (78.6% of precision faults
escape the official check); the speed side is not.

**Novelty.** STILL_OPEN under cell 3's coverage. KBV has a separate BF16
track at τ = 1e-2 but does not measure what a cut buys inside each gate;
Kernel Contracts names silent precision coercion as a contract class;
Gaming Without an Attacker shows selection pressure exploits what a gate
leaves unmeasured.

**Why it matters.** It prices the latent RL incentive toward precision
hacks per gate, and it can explain the archives' low prevalence.

**Closest priors.** [KernelBench-Verified](https://arxiv.org/abs/2607.16241);
[Measuring the Checker](https://arxiv.org/abs/2609.22220);
[A Contract-Grade Verifier](https://arxiv.org/abs/2608.12700);
[Kernel Contracts](https://arxiv.org/abs/2604.22032);
[Gaming Without an Attacker](https://arxiv.org/abs/2608.08722).

**Citable anchors.** 2607.16241 (BF16 τ = 1e-2) and 2609.22220 (78.6%):
VERIFIED (full text). Archive prevalence figures: cell-reported, provisional.

**First experiment (about 2.5 GPU-h, cap 4; trusted code only).** About 120
compute-bound L1/L2 problems (KBV's TF32-affected set plus S1-cal conv and
matmul problems, D28-filtered) x about 6 trusted variants; timing with Q1's
harness (randomized paired order, L2 flush, CUDA events, 1-2 dedicated
uncontended timing GPUs, seeds 42-44); verdicts from Q1's gate stack and rule
/2 on device outputs, with TF32 and fp32 references in the same process.
**Gate before GPU:** registration and pre-freeze audit; Kevin lifting D46's
stop (R570 does not block trusted code).

**Decisiveness check.** Premiums are deterministic functions of measured
timings and verdicts; uncertainty is the problem-family bootstrap. The
1.15x kill line is far enough from 1.3x to decide.

**Kill criteria.** KILL (the latent incentive is small) if the best variant
accepted by the KernelBench and KBV gates gives a geomean below 1.15x on
compute-bound problems, or if those gates reject bf16 variants on more than
80% of problems. If rule /2 under TF32 accepts bf16 variants on more than 50%
of problems, record the contract finding instead (the TF32-admissible contract
licenses bf16-level cuts), which is D14's question for Kevin.

**Relation to the existing program.** Q1-side; uses Q1's timing harness and
gate stack. Complements R11 (detection side) with the speed side.

---

## 15. Does greedy rerun noise shrink with scale within Qwen3.5?

`R09-noise-scale-ladder`. Origin: cell 2 #6.

**Corrected question.** One certified harness (H-OSW-fixed), screenshot
only, greedy, 15 steps, the 113-task pool. Does within-session rerun
discordance, conditioned on difficulty (discordance among tasks with
0 < p̂ < 1, and the task-by-rerun residual of a logit GLMM), fall from
Qwen3.5-4B to 9B to 27B? Does 35B-A3B (MoE) sit on the dense trend? Does the
informative-task share grow with scale? Prediction: informative-task D_w at
27B below 4B's (one-sided 95%). Null: |D_w(27B) − D_w(9B)| under 2 pp.

**What is wrong with the naive version.** S1a gives two points (secondary
D_w 11.1% at 4B, 9.3% at 9B; base D_b 14.1% and 8.6%), which cannot separate
scale from difficulty. Raw discordance falls mechanically as tasks move to
always-solved, so it must be conditioned. Larger models may lean on keyboard
shortcuts outside the 33 certified keysyms (18 of 32 base tasks already had
an exposed episode), so certification comes first.

**Novelty.** NARROWED. Coding and tool-calling studies report run-to-run
variance across a few models (2609.33812, 2602.07150, 2610.01618) and two
sizes ranking oppositely (2608.22331); no within-family desktop ladder found.

**Why it matters.** Every later design (S2, S3, a successor E, leaderboard
readings) needs the floor per size. If R01 finds the floor is a nuisance
response, this ladder says whether larger models are more or less sensitive
to it.

**Closest priors.** [Identical Runs, Different Results](https://arxiv.org/abs/2609.33812);
[On Randomness in Agentic Evals](https://arxiv.org/abs/2602.07150);
[Agents Are Systems, Not Models](https://arxiv.org/abs/2610.01618);
[Noise Floor Audit for Agent Benchmarks](https://arxiv.org/abs/2608.22331);
[On the Reliability of Computer Use Agents](https://arxiv.org/abs/2604.17849);
[Beyond the Model](https://arxiv.org/abs/2609.32459).

**Citable anchors.** S1a secondary D_w and base D_b per size, and the
exposure count. Status: VERIFIED (repository).

**First experiment (0.3 GPU-h probe; then about 5-6.5 cap-GPU-h).**
Pre-steps: certify the keysyms and chords S1a's agents emitted outside the
certified set (A1/A4-style trials at N* = 32, CPU lane); a replay-only
serving probe (0.3 GPU-h) prices 27B-FP8 and 35B-A3B-FP8. Main run, one
session on 113 tasks: 27B-FP8 and 35B-A3B-FP8 at R = 3, interleaved 4B and 9B
controls at R = 2, a 9B-FP8 quantization control at R = 2: 1,356 episodes.
**Gate before GPU:** keysym certification; the probe's price (27B at most
0.006 GPU-h per episode); gauntlet (new sizes) and Kevin's admission.

**Decisiveness check.** Conditioning on informative tasks shrinks the usable
set (32-33 tasks per size at 4B and 9B), so intervals will be wide; the null
(2 pp) may be unreachable. The registration must simulate P(decisive) from
S1a's components before freeze.

**Kill criteria.** Drop 27B if the probe prices it above 0.006 GPU-h per
episode at V = 20 (keep 35B-A3B). A size below 10% pool success or with fewer
than 20 informative tasks is descriptive only. If 9B-FP8 and 9B-BF16 D_w
differ by more than 3 pp, read large rungs only against FP8 controls.
Exclude episodes exposed to any keysym failing delivery above A4's bound.
Claims stay within one family.

**Relation to the existing program.** The noise-only remainder of S1b's
ladder (D69 closed the harness-scale question, not the noise-scale one).
Should follow R01.

---

## Not carried

| Cell candidate or likely proposal | Reason |
|---|---|
| Kernel timing A/A noise floor (cell 1, dropped) | Largely occupied by [AutoTuneBench](https://arxiv.org/abs/2609.18123) (cross-run CV cap, cross-machine transfer) |
| Desktop collateral side-effect false accepts (cell 1, dropped) | Crowded: [OSGuard](https://arxiv.org/abs/2606.15034), [SCOUT](https://arxiv.org/abs/2609.36201), [SINGED](https://arxiv.org/abs/2609.35889), 2610.09142; S1a captured checker inputs only, so new runs with full-disk diffs would be needed |
| RL on checker-corrected desktop rewards | The corrected comparator changes 0 of S1a's 1,808 verdicts, so the reward contrast is near zero for 4B and 9B; also [When the Reward Suite Is Leaky](https://arxiv.org/abs/2607.11022), [An Imperfect Verifier is Good Enough](https://arxiv.org/abs/2604.07666), [RLVεR](https://arxiv.org/abs/2601.04411) |
| Harness x scale | Closed internally (D69); also [2610.00917](https://arxiv.org/abs/2610.00917), [2610.04433](https://arxiv.org/abs/2610.04433), [2609.07925](https://arxiv.org/abs/2609.07925), [2610.11231](https://arxiv.org/abs/2610.11231) |
| LLM judge vs state checker for desktop agents | Occupied: [OpenComputer](https://openreview.net/forum?id=CgLTapI6Mr), [AgentHorizon](https://arxiv.org/abs/2610.11050), [OSWorld-Pro](https://arxiv.org/abs/2609.24890), [2604.06240](https://arxiv.org/abs/2604.06240) |
| Serving nondeterminism as a general topic | Occupied ([2609.04748](https://arxiv.org/abs/2609.04748), [cELldjX2oq](https://openreview.net/forum?id=cELldjX2oq), [2609.26621](https://arxiv.org/abs/2609.26621), [FlexBI](https://openreview.net/forum?id=rGmv0X20Oj)); the desktop decomposition is R01 |
| Kernel gate strength as an RL variable | Largely occupied ([KernelAudit](https://openreview.net/forum?id=yTa4gvQUGG), [2607.11022](https://arxiv.org/abs/2607.11022), [2609.35677](https://arxiv.org/abs/2609.35677), [Weak-to-Strong Verifier Hardening](https://openreview.net/forum?id=0ad4aBnjoQ)); the remaining on-policy audit is R12 Stage 2 |
| Action-path certification as a methods paper | Occupied by cua-speedrun App. I; the program's scale (64,028 trials, per-class bound about 5e-4) is appendix material for the Q2 report |
| A meta-study of the AI-run research gauntlet | Partly occupied (for example [What Output-Only Review Cannot Verify](https://arxiv.org/abs/2610.11754)); an experience report at most |
| Checker verdict nondeterminism under per-process cuDNN algorithm choice (cell 3) | Already documented by Q1 (determinacy on L2/100 is a per-process cuDNN choice); low significance; folded into R11's device pilot |
| Sakana Max_Diff reanalysis (cell 3) | Max_Diff is recorded at 1e-3 resolution, too coarse to place kernels against TF32 noise |
| SciCode-style numerical-code tolerance audit (cell 3) | Reported by cell 3 as occupied by [SciCode-Verified](https://arxiv.org/abs/2608.04975); the slate owner checked the title, not the content |
| Q3 cross-script sparse indexer (K1) | Closed at its honest exit (D54); its identification defect is what R14 measures |
| Model-rater κ on document equivalence as a finding | Occupied as a general claim by LLM-judge unreliability work; kept as an internal argument for human adjudication (R02, R03) |

## Coverage limits

- Retrieval used orx 0.2.2 in every cell; it reports itself outdated against
  0.2.18, so results may differ under a current client. The alphaXiv
  embedding index favours recent papers and may lag papers posted after
  about 2026-10-08.
- OpenReview: the api2 search endpoint works; every per-note fetch and PDF
  sits behind a bot challenge, which no cell attempted to bypass. ICLR 2027
  submissions are judged from abstracts only.
- ACL Anthology: cell 3 searched a full abstracts export by regex; cells 2
  and 4 used OpenAlex as a proxy; cell 1 ran two domain-restricted web
  searches; cell 5 used OpenAlex only. EMNLP was not covered by the OpenAlex
  source-id filter.
- Not searched by any cell: Semantic Scholar citers, Google Scholar, the
  arXiv API, GitHub code search, X, Reddit, patents, non-English venues.
- Full texts read by the slate owner: 2607.28367, 2604.17849, 2609.22220,
  2609.21058, 2609.04748, 2609.36931, 2610.11678, 2607.16241, 2610.09142,
  2609.40284, 2608.22331, 2609.17394 (targeted searches, not full reads).
  Every other prior is checked at title level by the slate owner (all 102
  arXiv ids resolve to the cited title) and at abstract or full-text level by
  the cell that cited it.
- Not verified, each a stated risk in its candidate: whether S1a's step-1
  screenshots are retained on the host (R01); whether vLLM's batch-invariant
  mode serves Qwen3.5's hybrid layers (R01); whether non-7.3.7 LibreOffice
  builds replay OSWorld postconfig unchanged (R04); the contents of the
  public Qwen3.5 eval archive (R05, R06); whether KBV's reference runs with
  TF32 (R11); Triton interpreter fidelity (R12); AutoTriton's licence beyond
  its Hub tag (R12); the Qwen3.5 tokenizer's fertility for Serbian and Hindi
  (R14).
- GPU-hour figures are estimates from S1a's realized cost model and the
  design study's cap rule. 27B, 35B-A3B, the accessibility arm,
  batch-invariant serving and kernel timing are unmeasured.
- No host job, GPU job or bulk download ran for this slate. The only data
  read outside the repository was the cell-3 drkernel parquet already in the
  session scratchpad.
