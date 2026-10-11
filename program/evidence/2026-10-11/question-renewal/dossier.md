# Question-renewal dossier: judged and ranked (2026-10-11)

Fifteen candidate questions from the D71 (i) renewal sweep, scored by three
independent judges and ranked with the 2026-10-06 gates. This is a dossier
for Kevin, not an adoption. Nothing here starts a run, and no score here is a
gauntlet score. `slate.md` holds each candidate's full entry (corrected
question, priors, first experiment, kill criteria). This file holds the
judging, the ranking, the corrections that now apply to each entry, the
owner's recommendation, and the program results that are reportable on their
own.

Companion files in this directory:

- [`slate.md`](slate.md): the fifteen entries, the merge table and the
  not-carried table.
- [`claim-registry.json`](claim-registry.json): the slate's 202 claims with
  sources.
- [`verification.json`](verification.json): the fresh verifier's verdicts
  (`d4f8339`).
- [`queries.md`](queries.md): the cells' and the slate owner's queries.
- [`ranking.json`](ranking.json): every judge's scores, the means, the gate
  results, the rank and the owner's disposition, machine-readable.

## How to read this

- **Rank** is the mechanical aggregate order, computed as in the 2026-10-06
  dossier. A candidate must clear two gates across all three judges: lowest
  correctness at least 5 and lowest citability at least 6. Gate passers are
  ordered by mean significance, then mean novelty residual, then mean
  feasibility. Candidates failing a gate follow in the same order. R09 and R06
  fail the correctness gate.
- **Recommendation** is the owner's, and it is not the rank. The judges gave
  scores and reasons, not verdicts. The recommendation reads their reasons,
  the verifier's findings and the owner's own checks (O1-O8 below).
- **Owner's disposition** on each entry (RECOMMEND, ALTERNATE, FOLD, HOLD,
  DROP) is advisory. It is not a judge verdict.
- **Scores** are three-judge means on 0-10 scales: significance (Sig),
  correctness (Corr), citability (Cite), novelty residual (Nov) and
  feasibility (Feas). Each judge scored the corrected question in `slate.md`
  with `verification.json` in hand. Per-judge scores are in each entry as
  J1/J2/J3, in the order Sig, Corr, Cite, Nov, Feas.
- **Corrections govern.** Where the verifier (c-ids and S1-S14), a judge
  finding the owner confirmed, or an owner check (O1-O8) differs from
  `slate.md`, the correction governs. D72 (on main, `0848d1e`) governs over
  D66 and D69 figures: rerun noise is 21-27% of S1a's outcome variance and
  task-by-harness about 4% at 9B and at most 1% at 4B; δ is H-GA minus
  H-OSW-fixed.
- **GPU-hours** are estimates unless stated. S1a's realized price is
  0.0025-0.0027 GPU-h per desktop episode at V = 20; "cap" applies the design
  study's realized x 1.2 x 1.05 rule.
- **Novelty verdicts** are absences in the stated queries, never a claim that
  nothing exists.

## Method

### Procedure

D71 (i) asked for a replay of the 2026-10-06 selection procedure on what the
program has measured since: S1a's noise floor and variance split, the
certified action path and its limits, the `compare_pptx_files` order defect
and the GUI-save gold flips, Q1's limiting result on TF32 tolerance audits,
Q3's NEGATIVE_CAPABLE_V3, and the honest-exit pattern of the gauntlets. Each
step below was done by a different agent.

| Step | Who | Output | Counts |
|---|---|---|---|
| Discovery | Five cells: (1) checker and benchmark calibration; (2) computer-use instrument follow-ons; (3) kernel and code correctness after Q1; (4) multilingual and long-context mechanisms; (5) kill-shot and occupancy | 26 cell candidates | 272 retrieval queries (53, 47, 48, 39 and 85 per cell), all in `queries.md` |
| Slate | Slate owner | 15 merged candidates, 14 not carried, a 202-claim registry (`f033b13`) | 102 arXiv title resolutions plus 1 added; 12 targeted full-text reads; OpenReview api2 searches on 11 topics; 1 data recount |
| Verification | Fresh verifier, independent of the slate owner and the cells | `verification.json` (`d4f8339`) | 202 claims: 192 VERIFIED, 4 CORRECTED (c047, c088, c095, c197), 6 UNVERIFIABLE (c188, c191, c199-c202), 0 REMOVED. 30 cell-reported claims upgraded at the primary source. 14 slate-text findings (S1-S14). 2 slate-only sources verified. All 101 distinct cited arXiv ids resolve to their titles (abs page and PDF text); all 10 OpenReview forum ids found by api2 search |
| Judging | Three independent judges | 45 score vectors with reasons | 20 retrieval actions reported in the reasons (J1 10, J2 7, J3 3) |
| Dossier | Dossier owner (this file) | Ranking, entries, recommendation | 22 retrieval queries (below); 8 owner checks (O1-O8) |

### Judges' retrieval, as reported in their reasons

The judges reported their queries in paraphrase; the exact strings were not
passed to the dossier owner.

- J1 (orx embedding unless stated): on-policy PASS audits on desktops (after
  2026-06-01; found 2610.07274); clock pixels and greedy rerun divergence in
  GUI agents (no clock-intervention prior); the cost of harness action bugs
  and counterfactual replay (found 2609.26693, not occupying); desktop
  evaluator verdicts under application-version or locale change (nothing on
  desktop checkers); exact integer inputs as a zero-tolerance kernel oracle
  (found 2609.11356, adjacent); KernelBench's TF32 protocol and unrefereeable
  problems (none); cross-lingual needles with controlled overlap and Serbian
  transliteration (none); translated instructions that keep UI labels
  verbatim (none); significance of OSWorld claims (found 2610.05830 and
  2609.33012); keyword "OSWorld rerun variance model size" after 2026-06-01
  (none).
- J2: an orx query finding 2610.07274; an orx clock and screenshot query
  (none); two orx queries on LibreOffice version or locale and on metamorphic
  null changes for checkers (none); two orx queries on overlap control and on
  digraphia (none); `orx paper --full` on 2609.12307.
- J3: an orx keyword query after 2026-09-01 (found 2610.01491); an orx
  embedding query after 2026-09-15 on rerun noise (none); an orx keyword
  query on exact-input kernel testing (Ozaki-scheme papers only).

### Dossier owner's retrieval (22 queries, 2026-10-11, orx 0.2.2)

Title checks of the judge-raised priors, `orx paper <id>`:

1. 2610.07274: "A Trust Layer for Agent Evaluation". Resolves. Earned-pass,
   honesty and rerun-stability checks on 108 Agents' Last Exam tasks; 22.6%
   of recorded passes clear all four checks.
2. 2610.01491: "Auditing Web Agent Evaluation on WebArena-Lite: Human Review
   of Outcomes and Trajectories". Resolves. Human review recovers 5.45-8.49 pp
   of success the evaluator missed (the false-negative side), web only.
3. 2609.12307: "How to grade the accuracy of the BLAS" (Demmel et al.).
   Resolves. Proposes "ungameable" test matrices that grade which accuracy
   class a matrix multiply satisfies, separating classical from Strassen-like
   algorithms.
4. 2610.05830: "Measurement-First Auditing of Agentic Leaderboards". Resolves.
5. 2609.33012: "When Pair Count Is Not the Sample Size: What All-Pairs Agent
   Comparisons Estimate". Resolves.
6. 2609.26693: "Measuring the Serving Stack Instead of the Model: Hidden
   Confounds in Local Tool-Use Evaluation". Resolves.
7. 2609.11356: "Taming Bitwise Behavior in GPU Kernels with Tensor Core:
   Black-Box Reconstruction, Compiler Enforcement, and Static Verification".
   Resolves.

Scoop check for the recommended and alternate candidates, alphaXiv:

8. embedding, after 2026-10-01, recency, limit 12: "sources of rerun
   nondeterminism in desktop computer-use agents: on-screen clock pixels,
   serving numerics, environment timing".
9. keyword, after 2026-10-01, limit 10: "computer-use agent rerun clock
   screenshot nondeterminism".
10. embedding, after 2026-10-01: "mutation testing of desktop benchmark state
    checkers OSWorld false negatives false positives".
11. embedding, after 2026-10-01: "audit of passing verdicts of computer-use
    benchmark checkers on real agent end states; do mutant error rates
    transfer to on-policy errors".
12. embedding, after 2026-10-01: "KernelBench correctness tolerance under a
    TF32 reference: which problems can the protocol referee".
13. embedding, after 2026-10-01: "cross-lingual needle in a haystack with
    controlled literal token overlap and same-language zero-overlap control".

OpenAlex:

14. after 2026-09-01, limit 12: "computer-use agent benchmark evaluator
    audit".

OpenReview api2 `notes/search` (source=forum, limit 10):

15. "OSWorld checker audit".
16. "rerun noise computer-use agents".
17. "desktop agent evaluator false accept".

ACL Anthology, regex AND-queries over the full abstracts export
(`anthology+abstracts.bib.gz`, SHA-256 prefix `85a53292`, 131,654 entries,
through 2026), lower-cased title and abstract:

18. `(rerun|run-to-run|nondetermini|non-determini)` AND `agent` AND
    `(screenshot|gui|desktop|computer[- ]use)`: 6 hits.
19. `(evaluator|checker|verifier)` AND `(false negative|false
    positive|false accept|false reject|mutation)` AND
    `(gui|desktop|computer[- ]use|osworld|web agent)`: 4 hits.
20. `osworld`: 9 hits.
21. `needle` AND `(cross-lingual|multilingual)` AND
    `(overlap|lexical|literal)`: 0 hits.
22. `(kernelbench|gpu kernel|cuda kernel|triton kernel)` AND
    `(toleran|correctness)`: 3 hits.

Result: no prior found that occupies R01, R02, R03, R11 or R14. Adjacent
papers posted 2026-10-01 to 2026-10-09: 2610.11514 (SSCBench, the evidential
validity of fault-injection tests for tool-using agents), 2610.11464
(co-evolving inspectable graders), 2610.09778 (a sequential isolation
protocol for inference-timing benchmarks on vLLM; timing, not outputs),
2610.03818 (Control OSWorld) and 2610.02320 (DeskForge). OpenReview returned
OSWorld-Pro (already in the slate's not-carried table) and two titles judged
at title level only: tn4eslVXEK ("When the Evaluator Changes", self-improving
language models) and Uiv5hUFlkv (evaluator disagreement in agent RL). The ACL
hits are GUI-agent benchmarks and training methods; none measures checker
error or the sources of rerun noise. The latest publication date in the
alphaXiv results is 2026-10-09, so papers posted on 2026-10-10 or 2026-10-11
are not covered.

### Owner checks for this dossier

Each check either confirms a judge finding that changes an entry or adds a
fact no earlier step had.

- **O1. S1a kept screenshot hashes, not screenshots.** The driver logs each
  step's raw and processed screenshot SHA-256 (`harness/q2_stage1/driver.py`
  lines 609-610, from `agents.process_image`) and writes no screenshot file.
  The per-job lists of every host run file
  (`program/evidence/2026-10-10/q2-stage1-a1/*/vm-*/raw-sha256sums.txt`,
  4,679-4,693 files per job) hold `steps.jsonl`, `replies.jsonl`,
  `episode.json`, `config.json`, `container.log` and final-state captures,
  and no agent screenshot. The README sentence and registration section 16
  that list screenshots among the host files do not match these listings. So
  R01's Stage A pixel diff and Stage B's "recorded step requests" cannot be
  built from S1a. The recorded IR actions (needed for open-loop replay) and
  the model replies are kept. This corrects J3's R01 feasibility premise and
  settles the slate's coverage-limit item, unless images were kept outside
  the run root.
- **O2. R07's premise.** The header of
  `harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py` (lines 15-34)
  and `harness/q2/action_path/harness_design_diffs.md` show that H-OSW-fixed
  keeps triple-click-as-double-click, hscroll-as-vertical-scroll and the
  ignored scroll coordinate as declared design differences of its prompt. Its
  four fixes are `terminate(failure)`, the explicit key-name map, exact text
  whitespace and `wait`. The C1 control judged H-OSW-up against cua-speedrun's
  Table 21, not against H-OSW-fixed's spec. This confirms J2.
- **O3. R03's K2 executor does not exist.**
  `harness/q2_mutation/vm_injection.py` is the corrected protocol and a plan
  builder (`build_injection_plan`, `check_plan`). Its ops (`upload`,
  `open_file`, `agent_save`, `hash` with `expect_changed`) are a contract for
  a VM runtime that does not implement them. The confirm analysis ran without
  `--k2-report` because "no K2 executor exists" (results README line 33). This
  confirms all three judges.
- **O4. R03 part (b) is small by construction.** The reserve split has 28
  targets, 8 of them pptx (`program/preregistrations/q2-evaluator-mutation-v1.md`,
  target table line 514). This confirms J3; (b) will probably be descriptive.
- **O5. R05's waits on Kevin are stale.** D49 (iii) admitted OpenCUA-7B's
  `--trust-remote-code` under D29's conditions, D1 authorizes public downloads
  (source, revision, size and SHA-256 recorded), and
  `harness/q2_stage1/anchor.py` exists with tests. This confirms J3.
- **O6. R04's build arm needs no root.** `infra/q2-mutation/lo-vm/Dockerfile`
  builds LO-VM from the OSWorld VM's own rootfs (LibreOffice
  1:7.3.7-0ubuntu0.22.04.4) and fails the build if any other package changes.
  A derived image with another LibreOffice build needs a changed check, not
  root. Postconfig replay under other builds is still untested. This confirms
  J3's feasibility point.
- **O7. The judge-raised priors resolve** (queries 1-7 above). gfgvdsOX6v
  (CAVEAT) was resolved by the verifier (c088).
- **O8. Arithmetic behind three judge findings.** R02: zero confirmed false
  accepts among 544 PASS verdicts gives an exact one-sided 95% upper bound of
  0.55% if the verdicts were independent, but 5.1% at the level of the 57
  PASS tasks (1 − 0.05^(1/57)). The slate's "at most 3%" prediction is
  reachable only under the first reading (J2). R04: zero flips on 92 golds
  gives 3.2% (1 − 0.05^(1/92)), above the slate's 3% locale line (J2). R09:
  with p̂ taken from the same R reruns, every task with 0 < p̂ < 1 has
  pairwise discordance exactly 2/3 at R = 3 and exactly 1 at R = 2, so the
  conditioned D_w is fixed by construction (J2).

## Ranked table

Means of the three judges. "Min" columns are the lowest judge score, which
the gates read. GPU-h is the first experiment's, with corrections applied.

| Rank | Key | Title | Sig | Corr | Cite | Nov | Feas | Min Corr | Min Cite | Gates | First exp. GPU-h | Owner's disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | R02 | On-policy two-sided audit of S1a's 1,808 verdicts | 5.67 | 5.67 | 8.00 | 5.17 | 5.00 | 5 | 8 | pass | 0.3-1 (rater lane) | RECOMMEND: backfill, after R03's adjudication |
| 2 | R01 | Where greedy rerun noise comes from on the desktop stack | 5.67 | 6.33 | 8.00 | 5.00 | 7.00 | 6 | 8 | pass | Stage A 0; B 0.3-0.5 plus a 0.2 probe; C about 1.7 (2.1 cap); a recording pass of about 0.3 if the prefix-cache arm stays (O1) | RECOMMEND: lead |
| 3 | R03 | Finish the OSWorld checker-mutation note | 5.33 | 6.67 | 8.67 | 4.50 | 6.67 | 6 | 8 | pass | 0 (at most 0.5 if part (c) runs) | RECOMMEND: spine |
| 4 | R14 | What the cross-lingual long-context penalty is made of | 5.00 | 6.00 | 7.00 | 5.00 | 6.00 | 6 | 7 | pass | Stage A about 1 (unverifiable, c200) | ALTERNATE |
| 5 | R11 | Can kernel benchmarks referee their own TF32 baseline? | 5.00 | 6.00 | 8.00 | 4.67 | 7.00 | 6 | 8 | pass | 0 (device pilot 1.2 behind D46) | ALTERNATE |
| 6 | R12 | Interpreter-executed audit of model-written Triton kernels | 4.67 | 5.00 | 6.33 | 4.17 | 4.33 | 5 | 6 | pass | 0.3 (trusted fidelity leg, behind D46) | HOLD |
| 7 | R04 | Checker verdicts under LibreOffice-build and locale changes | 4.50 | 6.00 | 7.00 | 6.00 | 6.33 | 6 | 7 | pass | 0 | FOLD into S2 v3's Phase 0 |
| 8 | R05 | Checker-revision drift on fixed end states, then an external anchor | 4.50 | 6.00 | 7.00 | 5.17 | 6.33 | 5 | 7 | pass | 0 drift test; anchor at most 240 episodes, about 0.65 (0.8 cap) (c197) | HOLD until R03's executor |
| 9 | R10 | Input-design oracles for TF32 | 4.33 | 5.67 | 7.67 | 4.00 | 8.33 | 5 | 7 | pass | 0 (device check 0.3-0.5 behind D46) | FOLD into R11's census |
| 10 | R07 | Task-success cost of known action-path defects | 4.00 | 5.67 | 7.33 | 4.83 | 7.33 | 5 | 7 | pass | Stage 0 0; Stage 1 about 2.4 (4 cap) | FOLD Stage 0 into the Q2 report; drop Stage 1 |
| 11 | R15 | Translated instructions in a desktop agent | 3.83 | 5.33 | 7.00 | 5.00 | 3.67 | 5 | 7 | pass | Phase 0 0; Phase 1 at most 4.1 | HOLD for a larger informative pool |
| 12 | R08 | Accessibility tree on the certified path vs S1a's floor | 3.83 | 5.50 | 7.00 | 3.00 | 5.33 | 5 | 7 | pass | about 3.3 cap | DROP as a line |
| 13 | R13 | The speed premium of a pure precision cut, per gate | 3.67 | 5.83 | 6.00 | 4.33 | 5.00 | 5.5 | 6 | pass | about 2.5 (unverifiable, c199), behind D46 | DROP as a line |
| 14 | R09 | Does greedy rerun noise shrink with scale within Qwen3.5? | 4.00 | 4.33 | 7.00 | 4.00 | 4.33 | **3** | 7 | **fails correctness** | 0.3 probe; then 5-6.5 cap | FAILS GATE |
| 15 | R06 | A session-inclusive noise band on published OSWorld-Verified claims | 4.00 | 4.67 | 7.33 | 3.50 | 7.67 | **4** | 7 | **fails correctness** | 0 | FAILS GATE |

Ties broken as the rule states. R02 and R01 tie on mean significance
(5.67); R02 ranks first on mean novelty residual (5.17 against 5.00). R14 and
R11 tie at 5.00 and split on novelty (5.00 against 4.67). R04 and R05 tie at
4.50 and split on novelty (6.00 against 5.17). R15 and R08 tie at 3.83 and
split on novelty (5.00 against 3.00).

Agreement. The judges agree closely: the largest spread on any score is 3
points (R05 feasibility: J2 5, J3 8, because J3 found the slate's waits on
Kevin stale, O5). Correctness splits by 2 on R05 (5 to 7), R07 (J3 7 against
5 and 5) and R09 (J2 3 against 5 and 5); feasibility by 2 on R01 (6 to 8,
J3 on a premise O1 corrects); novelty by 2 on R10 (J2 3, after finding
2609.12307). J1 placed R06 and R09 at the correctness gate (5); J2 put both
below it (4 and 3).

## Recommendation

Three questions for Kevin to consider. None is adopted by this file.

| Role | Key | Question | Why this one |
|---|---|---|---|
| Lead | R01 | Where greedy rerun noise comes from on the certified desktop stack | Ties for the highest mean significance and is the best identified of the top three: it leads R02 by 0.67 on correctness and 2.0 on feasibility. Its Stage B is decisive by construction (counts on fixed requests). Rerun noise is the largest variance component S1a measured (21-27%, D72 (ii)), so the answer conditions every later power calculation, here and on any OSWorld-style stack |
| Spine | R03 | Finish the OSWorld checker-mutation note | The highest mean correctness (6.67) and citability (8.67) on the slate, zero GPU, and the program's most finished result, with a live scoop clock (2610.09142, 2026-10-06). It produces the adjudicated labels and the in-VM executor that R02 and R05 need |
| Backfill | R02 | On-policy two-sided audit of S1a's verdicts | First in mechanical rank and the most thesis-central question: does checker error matter on real policy end states, and do mutant rates transfer? Its CPU instruments can be built in the gaps now; its decisive readout waits on R03's adjudication and a repaired prediction |

**Why R01 leads although R02 ranks first.** The two tie on significance, and
the tie is broken by 0.17 of novelty. R01 is ahead on correctness and
feasibility. R02's largest judged defect is decisiveness: its headline
prediction cannot be reached under task clustering (O8). Decisiveness or
identification was the largest defect in all 18 gauntlet runs on record
(below), so the program should not lead with a design whose largest defect
is that one while a better-identified candidate of equal significance
exists. R02 also cannot read its first decisive result before Kevin
adjudicates R03's items.

**Why R02 is the backfill and not an alternate.** "Backfill" here means
preemptible CPU work that runs around the lead and the spine, with a small
GPU tail (0.3-1 GPU-h). That fits R02's shape: weeks of instrument building
on the CPU lane, a validation gate before any S1a verdict is read, and a
dependency on R03.

**Concentration risk.** All three sit on the OSWorld stack and S1a's
records, so one stack problem hits all three. If Kevin wants a second
domain, or if his adjudication time is the binding constraint, swap R11 in
for R02. It needs no GPU and no adjudication, and keeps the kernel half of
the thesis alive while Q1 stays closed.

**Alternates.**

- R11 (rank 5), the zero-GPU swap for R02 described above. It needs Kevin's
  D14 ruling to interpret its TF32 classes and D46 lifted for its device
  pilot. R10's lattice-survival census folds into it.
- R14 (rank 4), if Kevin wants one line off the desktop stack. It repairs
  D54's identification defect with no trained component, but sits off the
  checker thesis, has a heavy Phase 0 data pipeline, and needs a gauntlet and
  admission for about 1 GPU-h at Stage A (unmeasured) and about 6 GPU-h for a
  decisive reading.
- R04 (rank 7) is not a standalone question. It is a precondition for S2 v3
  (D71 (ii)) and for any re-hosted OSWorld image, so it belongs in S2 v3's
  Phase 0.

**Sequencing.** These are host jobs on one lane, CPU only and never
overlapping (D71).

1. R03: Kevin's blind adjudication (52 items) and the K2 executor build, in
   parallel.
2. R02's CPU instruments (spec checker, diff classifier), which do not need
   the adjudication, in parallel on the Mac.
3. R01's rebuilt Stage A on the CPU lane, after R03's K2 job.
4. GPU, only after admission: R01's Stages B and C; R02's rater-lane job
   after its validation gate.

Total GPU if all three run: about 4.5 cap-GPU-h for R01 (with the recording
pass), 0-0.5 for R03 and 0.3-1 for R02. None is above 8 GPU-h alone.

### What each needs before any GPU

| | R01 (lead) | R03 (spine) | R02 (backfill) |
|---|---|---|---|
| Route | New mechanism (an observation mask and an identical-request serving replay): registration, pre-freeze audit and the research gauntlet | Existing frozen registration `q2-evaluator-mutation-v1`, descriptive under D35. No gauntlet. The K2 executor is new project code: an amendment with a pre-freeze audit, recording executor commit and image digest. Part (c), if wanted, is a new registration | Novel direction: a descriptive registration (D35 style), a pre-freeze audit and the gauntlet |
| D24 position | Under 8 GPU-h (about 4.5 cap), but gauntleted. Under D24 and D68 a package scores at most 79 without an executable pilot and at most 89 without signed reviews, so admission is Kevin's ruling whatever the score. A CPU Stage A run first is the executable pilot, the only lever on the 79 cap | Not engaged: no GPU step (at most 0.5 GPU-h if part (c) sends items to the open-weight rater, which needs its own registration) | As R01: the rater-lane job (0.3-1 GPU-h) needs Kevin's admission. The CPU validation gate run first is the executable pilot |
| Kevin's rulings | Admission only | Blind adjudication of the 34-item pool and the 25-item spot check (52 distinct items, D9); the xlang-ai disclosure is an outward action (D2) and uses D72 (iii)'s counts | The split-gold adjudication it shares with R03; a budget for a 120-item human-adjudicated sample (or a smaller sample with a registered precision); admission of the rater job |
| Design repairs | (a) NOT_CLOCK (upper bound of the reduction below 2 pp) is unreachable at R = 3 on 113 tasks (all three judges; SE of the paired reduction about 2-3 pp). Make the Stage A and B counts the decisive readings, keep Stage C as an estimate with its interval and CLOCK_DOMINANT as its only decision, or show by simulation from S1a's components that a larger R or K within 8 GPU-h makes NOT_CLOCK reachable with probability at least 0.8. Register PARTIAL as a reportable outcome. (b) Rebuild Stage A and Stage B's request source (O1): CPU-lane captures of the 113 initial states, kept on the host, localize the differing regions; Stage B serves step-1 requests built from them; the prefix-cache arm needs multi-step requests, so either add a recording pass (113 episodes with full requests kept on the host, about 0.3 GPU-h physical at 0.0027 per episode) or drop that arm. (c) Use D72 (ii)'s 21-27%. (d) Fix the date- and time-reading exclusion list before any run (the Holo3 v2 audit's 16 time-dependent tasks are a seed). (e) Keep the masking check (A1 success within ±5 pp) | (a) Build K2: `upload`, `open_file`, `agent_save` and `hash` with `expect_changed` in the VM runtime (O3); then the registered 80-job sample on the CPU lane at N ≤ 32. (b) Register in advance that the reserve split's z-order test is descriptive below 20 mutants or 8 tasks; the reserve split has 8 pptx targets (O4). (c) Text: S6's wording for 2610.09142; "36 of 40 (90.0%; task-equal 91.7%)" (S11); D72 (iii)'s counts | (a) Restate the predictions at the task-cluster level: 544 PASS verdicts sit on 57 tasks, so even zero events bounds the false-accept share near 5.1% (O8); state the unit and the design effect. (b) Drop "H-transfer fails for `compare_pptx_files`" as a test: 0 of 288 flips is already known; keep it as a consistency check. (c) Argue the spec checker's independence: compiled from the blind specs without reading OSWorld's evaluators, validated on witness labels. (d) Note that none of the 280 discordant rerun pairs has identical checker-input hashes and no checker was nondeterministic (S1a RESULTS, mutation S5), so (iii) measures over-strict or over-lenient verdicts on different end states, not checker noise. (e) Cite 2610.07274, gfgvdsOX6v and 2610.01491 |
| CPU work first | Stage A as rebuilt: about 20 idle boots per initial state with and without the time-invariance changes, the differing-region map, and open-loop replay of the 512 base episodes' recorded IR at N ≤ 32 | The K2 run; the reserve-split zinv check | The spec checker over the 113 blind specs and the structural diff classifier; validation on the mutation campaign's witness labels. Packet building runs on the host CPU lane, because S1a's captures hold third-party documents; only verdicts and recipes are released |

## Program results that are reportable findings

These are results the program has already measured. Each is reportable on
its own, with the caveat shown. Most already sit in the Q2 report draft
(`paper/q2-report/draft.md` on main, D71 (iii); unpublished; publishing is
Kevin's).

| # | Finding | Numbers | Caveat | Where it stands |
|---|---|---|---|---|
| 1 | `compare_pptx_files` rejects equivalent z-order edits | 36 of 40 evaluable z-order equivalence mutants fail their checker: `compare_pptx_files` 35 of 39 (29 confirmed by both raters, 6 split), `compare_pptx_files_tolerant` 1 of 1; 30 confirmed in all (D72 (iii)). Family task-equal share 40.2% (32.9-46.3%), audit-confirmed 33.5% (24.8-41.7%). Every other should-pass family 0 (for example `compare_table` 0 of 218 on 30 tasks) | Descriptive (D35); offline harness, VM fidelity unverified (K2); Kevin's adjudication pending; the corrected comparator (`zinv`) was validated on the split it was built for | Q2 report draft; R03 completes it; disclosure to xlang-ai is Kevin's |
| 2 | The gold is not a fixed point of a GUI save | 4 of 92 golds flip under a GUI-faithful save (exact 95% 1.20-10.76%); 3 audit-confirmed (3.26%, 0.68-9.23%); the headless round trip flipped 7 of 63 and 1 of 26 | One LibreOffice build (7.3.7.2), one locale | Q2 report draft; R04 would extend it |
| 3 | The checker defect has no on-policy consequence for Qwen3.5-4B and 9B | The corrected comparator changes 0 of the 288 `compare_pptx_files` episodes and 0 of 1,808 verdicts | Two policies, 15 steps; the defect may matter for stronger agents that reorder shapes | Q2 report draft (S1a) |
| 4 | S1a's rerun discordance is not checker noise | All 280 discordant rerun pairs have different checker-input hashes; no checker was nondeterministic on repeated scoring (mutation S5) | Says nothing about over-strict verdicts on different end states (that is R02 (iii)) | S1a RESULTS; not yet a stated finding in the report |
| 5 | Two certified harnesses do not differ detectably on this stack | δ (H-GA − H-OSW-fixed) −3.1 pp, 90% interval [−8.9, +2.7], on 32 base tasks; −1.1 pp, [−3.8, +1.6], on 113 tasks. Rerun disagreement about 11-12% of cells. No between-session excess (P1 falsified; upper bound 0.78 pp). 0 infrastructure losses in 1,808 episodes. Realized cost 0.0025-0.0027 GPU-h per episode, 0.22-0.24 of the card's high price | Not externally anchored; two realized sessions per size; two sizes; one host | Q2 report draft |
| 6 | Rerun noise dwarfs harness-specific variance | Rerun noise 21-27% of outcome variance; task-by-harness about 4% at 9B and at most 1% at 4B (D72 (ii)). No successor design within 8 GPU-h can admit S1b (P(GO) at most 0.03). A 5 pp locale gate needs about 100-115 distinct tasks; reruns do not help | Model-based, from S1a's records; calibrations that passed the extended check | Q2 report draft (design study) |
| 7 | A certified desktop action path at volume | A4: 64,028 of 64,028 trials pass at N* = 32. A7: 0 restarts in 39,036 accessibility calls (exact upper bound 7.67e-5 per call). C1: both defective harnesses fail each of their 9 known-defect cells in 5 of 5 repetitions. One whole-boot accessibility HTTP-500 session (193) is reported and not bounded | As a methods paper it is occupied by cua-speedrun (App. I); the scale is appendix material | Q2 report draft (appendix) |
| 8 | A first-step divergence census | Between-session pairs: 512 of 512 part at step 1 as "environment"; within-session: 255 of 256 at step 1, 1 at step 2 as "serving" | Descriptive: the guest clock is on every screenshot, so "environment" does not identify a cause (R01's question) | S1a RESULTS |
| 9 | Under a TF32-admissible policy, a tolerance audit certifies only gross destruction | The registered metric scores an all-zeros output at 1/(1+κ) = 0.999 for any reference. Under TF32, valid algorithms sit up to about 45-50x the yardstick while a 1% fault scores a median of about 15x, so 239 of 272 1% faults are ambiguous; strict fp32 decides them (276 of 278) but rejects 55 correct kernel-draws | CPU emulation (median ratio to device 0.996; cuBLAS on L1/18 3.5-3.6x off); 12 tier-1 problems | Q1 record (D46); a short note at most; narrowed by 2609.22220 (no TF32) and 2609.12307 |
| 10 | Cross-script retrieval measurements carry a lexical confound | Dense pre-check v2 on Qwen3.5-4B-Base: NEGATIVE_CAPABLE_V3; lexical confound PRESENT, entity control INSUFFICIENT; needle fertility tracks headroom (Spearman −0.89 over 7 languages); v1 reproduced with a largest gap of exactly 0.0 | Development partition only (20 questions); not a K1 result | Q3 record (D54); R14 builds on it |
| 11 | Two leaderboard rows for one agent can be an operator contrast | The two public Holo3-35B-A3B runs are not exchangeable reruns (exact McNemar 25 vs 9, p 0.009); OpenCUA's turn sets show no such term (mean-square ratio 0.663) | Post hoc (v1) and a registered audit (v2) that found no registered mechanism | Q2 report draft (Holo3 v2) |
| 12 | Model raters disagree on document equivalence despite passing shams | Cohen's κ 0.343 (raw agreement 82.6%) on 138 real items, with sham accuracy 0.90 and 0.975 | Occupied as a general claim (LLM-judge unreliability); an internal argument for human adjudication | Mutation results README |
| 13 | AI-run gauntlets end on identification or decisiveness | 18 gauntlet runs over 10 packages; the largest defect named in every run is identification, decisiveness or instrument validity; the highest score is 60; under D24 and D68 no package can exceed 79 without an executable pilot | Partly occupied (for example 2610.11754); an experience report at most | `program/gauntlet/`; D54, D63, D65, D70 |

## Open items for Kevin outside the ranking

1. **Scoop clock.** 2610.09142 (2026-10-06) mutation-tests AppWorld and
   WorkArena verifiers and lists an OSWorld rank-consequence audit as future
   work. R03 ships the program's desktop result; R02 answers the
   rank-consequence question for two policies.
2. **Wording to narrow.** `program/PROGRAM.md` line 77 and
   `program/questions/q2-calibrated-cua-instrument.md` line 27 say
   checker-mutation testing for computer use has "no prior found". After
   2610.09142 the accurate line is "no prior found for desktop file-state
   checkers", and per S6 that absence rests on the program's searches, not on
   2610.09142's own Limitations sentence. This dossier does not edit those
   files.
3. **S1a's data-handling text.** O1 shows that the S1a README sentence and
   registration section 16 name screenshots among the host files, but the
   driver kept only their hashes. A one-line correction in the S1a record
   (like D72) would stop later designs from assuming the images exist.
4. **The levers on the caps are unchanged.** Every recommended GPU step is
   gauntleted or needs admission, so the 79 cap binds without an executable
   pilot and the 89 cap without the D24 trust store, which only Kevin can set
   up. Each recommended candidate puts a CPU step first that can serve as its
   executable pilot.

---

## Entries

In rank order. Each entry gives the scores, what the judges agreed on, the
corrections that now apply and the owner's disposition. The full entry is the
matching section of `slate.md`.

### 1. On-policy two-sided audit of S1a's 1,808 verdicts

`R02-onpolicy-checker-audit`. Slate section 2. **Owner's disposition:
RECOMMEND as backfill, after R03's adjudication.**

Scores: Sig 5.67, Corr 5.67, Cite 8.00, Nov 5.17, Feas 5.00. J1 6/6/8/5.5/5,
J2 5/5/8/5/5, J3 6/6/8/5/5. Passes both gates; correctness at the floor (J2
5).

**Question, as corrected.** On S1a's 1,808 captured end states (544 checker
passes on 57 tasks; 1,264 non-passes, 35 of them fractional), measured
against an independent three-valued audit frozen before any verdict is read:
(i) the false-accept share among PASS verdicts and the false-reject share
among FAIL verdicts, per checker family; (ii) whether the mutation study's
per-family rates predict the on-policy rates (H-transfer) and what share of
on-policy differences from the gold fall in the frozen operator catalog
(H-coverage); (iii) what share of the 280 discordant rerun pairs the audit
judges task-equivalent.

**What the judges agreed on.** It is the most thesis-central candidate (J1)
and answers the PASS-side audit 2607.28367 left open and 2610.09142's future
work (J1, J2). The GPU cost is small, but the engineering and Kevin's time
are not (J3): executable spec checkers for 113 tasks (all 113 have blind
specs), a 120-item human sample and the split-gold adjudication.

**Defects.** (1) The headline prediction (false-accept upper bound at most
3%) cannot be reached under task clustering (J2; O8). (2) H-transfer for
`compare_pptx_files` is already known (0 of 288 flips under `zinv`), so it is
not a test (J1, J2). (3) Independence: the program's model raters reached κ
0.343 with an equivalence label error of 0.167, the spec checker is built by
the program, and S1a captured only checker inputs, so the audit inherits
OSWorld's getter scope (J1, J2, J3).

**Corrections and new priors.** gfgvdsOX6v (CAVEAT, a GUI-agent trajectory
verifier) resolves and is a judge-side prior (S1, c088). 2610.07274 (Trust
Layer; earned passes and rerun stability on Agents' Last Exam) and
2610.01491 (human outcome audit of WebArena-Lite, the false-negative side)
are adjacent and uncited (O7). Owner note: none of the 280 discordant pairs
has identical checker-input hashes, and no checker was nondeterministic
(mutation S5), so (iii) can only find over-strict or over-lenient verdicts on
different end states.

**Novelty after judging.** NARROWED, slightly more than the slate said. No
prior found audits both directions on one policy's reruns of a desktop
benchmark.

**First experiment.** 0.3-1 GPU-h for the open-weight rater-lane job; the
rest is CPU on the host lane. Before GPU: see the recommendation table.

### 2. Where greedy rerun noise comes from on the certified desktop stack

`R01-rerun-noise-sources`. Slate section 3. **Owner's disposition:
RECOMMEND as lead.**

Scores: Sig 5.67, Corr 6.33, Cite 8.00, Nov 5.00, Feas 7.00. J1 6/6/8/5/6,
J2 5/6/8/5/7, J3 6/7/8/5/8. Passes both gates.

**Question, as corrected.** Hold S1a's stack fixed (H-OSW-fixed, greedy, 15
steps, 2,048 thinking tokens, V = 20, prompt date pinned, guest clock live).
For Qwen3.5-4B on the 113-task pool minus tasks whose config or checker reads
the date or time, split within-session discordance D_w into environment
outcome noise (open-loop replay of recorded IR actions), serving numerics
(identical requests under S1a's batched, prefix-cached serving against
batch-1 with the cache off) and observation-time noise (a harness-side mask
over the top-bar clock).

**What the judges agreed on.** The best-identified candidate on the slate
(J2), with high practical significance: a clock- or serving-dominant reading
gives every OSWorld-style stack a cheap fix and explains why floors do not
transfer between stacks (J1). The best information per GPU-hour (J3). The S1a
figures check: 4B secondary D_w 11.1% (7.5-15.0%); 512 of 512 and 255 of 256
step-1 "environment" divergences; prefix-cache hit share 0.855-0.858.

**Defects.** (1) NOT_CLOCK is close to unreachable at R = 3 on 113 tasks
(all three; SE of the paired reduction about 2-3 pp), so PARTIAL is the
likely reading. (2) The motivating 20-33% is superseded by D72 (ii): 21-27%,
with task-by-harness at most 1% at 4B (J1, J2). (3) Masking may change
behaviour (J1; the registered ±5 pp check covers it).

**Corrections.** O1: S1a kept screenshot hashes, not images. Stage A's pixel
diff and Stage B's replay of "recorded step requests" must be rebuilt from
fresh CPU-lane captures, and the prefix-cache arm needs a recording pass or
must be dropped. The recorded IR and replies are kept, so open-loop replay
works as planned. J3's feasibility 8 rested on the opposite premise.

**Novelty after judging.** NARROWED. 2604.17849 crosses decoding determinism
with cosmetic perturbations but has no clock intervention, no open-loop
replay and no identical-input serving test. No clock-intervention prior was
found in any judge's query or in queries 8-9 above.

**First experiment.** Stage A 0 GPU-h (rebuilt); Stage B 0.3-0.5 GPU-h plus a
0.2 GPU-h probe; Stage C about 1.7 GPU-h physical (2.1 cap); a recording pass
of about 0.3 GPU-h physical if the prefix-cache arm stays. About 4.5 cap in
all. Before GPU: see the recommendation table.

### 3. Finish the OSWorld checker-mutation note

`R03-mutation-note-completion`. Slate section 1. **Owner's disposition:
RECOMMEND as spine.**

Scores: Sig 5.33, Corr 6.67, Cite 8.67, Nov 4.50, Feas 6.67. J1 5/7/9/4.5/6,
J2 5/6/8/5/7, J3 6/7/9/4/7. Passes both gates.

**Question, as corrected.** On the 60 evaluable tasks of the frozen confirm
campaign, after Kevin's adjudication: (a) do mutants materialized and saved
inside the certified VM get the offline harness's verdict, with every
difference explained by the four registered causes? (b) Does `zinv` accept at
least 95% of held-out z-order equivalence mutants on the reserve split while
accepting no violation mutant the original rejects? (c) Optional, a new
registration: blind operator families on the pool's non-office checkers.

**What the judges agreed on.** The cheapest shippable result, with a real
scoop clock, and the highest correctness and citability on the slate. But it
completes a study rather than asking a new question, and its field
significance is bounded: the headline is one comparator defect (36 of 40
z-order mutants) with no on-policy consequence (0 of 1,808 flips) (J1).

**Defects.** (1) K2 has no executor (all three; O3). (2) Part (b) is probably
undersized: the reserve split has 8 pptx targets (J3; O4). (3) The kill
lines barely bind: the audit-confirmed `compare_pptx_files` share is already
33.5% (24.8-41.7%), far above the 5% kill line (J2). (4) The note cannot ship
before Kevin's 52-item adjudication.

**Corrections.** S6: 2610.09142's "remain untested" sentence is in its
Limitations and describes its own scope. Write "2610.09142 names
OSWorld-Verified-class desktop checkers as outside its scope and lists an
OSWorld rank-consequence audit as future work"; the absence claim rests on
the program's searches. S11: 36 of 40 is 90.0%; 91.7% is the task-equal
share. D72 (iii): use 35 of 39 plus 1 of 1, 30 confirmed, in any text.

**Novelty after judging.** NARROWED. No prior found mutation-tests desktop
file-state checkers (queries 10, 15 and 19 above found none either).

**First experiment.** 0 GPU-h (at most 0.5 GPU-h if part (c) runs). Before
GPU: see the recommendation table.

### 4. What the cross-lingual long-context penalty is made of

`R14-crosslingual-lc-decomposition`. Slate section 10. **Owner's
disposition: ALTERNATE (the off-desktop option).**

Scores: Sig 5.00, Corr 6.00, Cite 7.00, Nov 5.00, Feas 6.00. All three judges
gave 5/6/7/5/6. Passes both gates.

**Question.** Qwen3.5-4B and 9B (with Qwen3-8B as a full-attention contrast):
how much of the cross-language retrieval drop remains against a
same-language question that shares no token with the needle, with a Serbian
Latin/Cyrillic leg (same words, no shared tokens)?

**What the judges agreed on.** A broadly interesting decomposition that
repairs the identification defect that ended K1 v3 (D54), with no trained
component (J1, J2). The Serbian leg is a strong control (J2).

**Defects.** (1) The same-language zero-overlap cell needs paraphrase, which
changes semantic difficulty, so "cross-language minus same-language
no-literal" mixes translation with paraphrase (J1, J2). (2) Serbian as the
only digraphic leg confounds script with resource level (J1). (3) The
tokenizer figures (c191) and GPU estimates (c200) are unverifiable. (4) Phase
0 is a heavy data pipeline: Wikidata, FineWeb-2 and an alias scorer in five
languages (J3). (5) Off the checker thesis (J1).

**Novelty after judging.** NARROWED. No prior found with the within-item
overlap-by-language factorial (J1 and J2 queries; queries 13 and 21 above).

**First experiment.** Phase 0 on CPU; Stage A about 1 GPU-h (unverified);
about 6 GPU-h for a decisive reading. Before GPU: a fix for the paraphrase
confound (for example a paraphrase control inside the same language with a
literal key), the gauntlet and Kevin's admission.

### 5. Can kernel benchmarks referee their own TF32 baseline?

`R11-tf32-protocol-consistency`. Slate section 7. **Owner's disposition:
ALTERNATE (the zero-GPU swap for R02).**

Scores: Sig 5.00, Corr 6.00, Cite 8.00, Nov 4.67, Feas 7.00. J1 5/6/8/5/7,
J2 5/6/8/4/7, J3 5/6/8/5/7. Passes both gates.

**Question.** For each active KernelBench problem and each published
correctness protocol, does a correct TF32 implementation pass, does a
destroyed output pass, does a bf16-operand or fp16-store variant pass, and
what is the smallest relative fault the protocol rejects without rejecting a
valid algorithm class?

**What the judges agreed on.** A per-problem map of which verdicts certify
1% faults helps kernel-RL reward builders and generalizes D46 beyond 12
problems (J1). The census is deterministic under emulation and needs no GPU
(J2, J3).

**Defects.** (1) It rests on CPU TF32 emulation (median ratio 0.996, but
cuBLAS on L1/18 is 3.5-3.6x off). (2) Whether KBV's correctness reference
runs TF32 is unsettled (S10). (3) The zeros facet is occupied (2609.21058,
4 of 60 at 1e-2 only, S8). (4) The output is a methods note (J1). (5) The
3-5 CPU-day estimate is unverified (c201). (6) 2609.12307 grades
matrix-multiply accuracy by algorithm class, which narrows it (J2; O7).

**Novelty after judging.** STILL_OPEN for the TF32-contract consistency
audit (no prior found by J1's query or query 12); the zeros facet stays
OCCUPIED.

**First experiment.** 0 GPU-h, CPU on the Mac. Before any device step:
Kevin's D14 ruling and D46 lifted. Registration and pre-freeze audit. R10's
lattice census folds in here.

### 6. Interpreter-executed audit of model-written Triton kernels

`R12-interpreter-kernel-audit`. Slate section 9. **Owner's disposition: HOLD
until D46 is lifted and the fidelity leg passes.**

Scores: Sig 4.67, Corr 5.00, Cite 6.33, Nov 4.17, Feas 4.33. J1 5/5/7/4.5/4,
J2 4/5/6/4/4, J3 5/5/6/4/5. Passes both gates, at both floors.

**What the judges agreed on.** It removes the R570 block for Triton by
executing untrusted kernels only in the CPU interpreter, and it would test
Q1's premise at scale (J1).

**Defects.** (1) The interpreter changes the arithmetic: `tl.dot` runs in
fp32 NumPy, so the TF32 band must be emulated rather than observed, races
are serialized, and reduced shapes miss boundary bugs (all three). (2) The
archive leg means nothing without the fidelity leg, which needs D46 lifted
(J2, J3). (3) The Contract-Grade Verifier already audits 2,638 kernels from
the same corpus (all three). (4) The downcast regex counts cannot be checked
(c188: an independent scan finds 413 of 8,462 where the cell found 321).
(5) Stage 2 needs a verified policy licence (D5).

**First experiment.** 0.3 GPU-h trusted fidelity leg (behind D46); archive
leg about 70 CPU-h.

### 7. Checker verdicts under LibreOffice-build and locale changes

`R04-nuisance-invariance`. Slate section 5. **Owner's disposition: FOLD into
S2 v3's Phase 0 as its checker-invariance precondition.**

Scores: Sig 4.50, Corr 6.00, Cite 7.00, Nov 6.00, Feas 6.33. J1
4.5/6/7/6/6, J2 4/6/7/6/6, J3 5/6/7/6/7. Passes both gates. The highest
novelty residual on the slate.

**What the judges agreed on.** Clean metamorphic design with controls (7.3.7
and en_US), at zero GPU, and a real precondition for S2 v3 and for any
re-hosted OSWorld image (all three). STILL_OPEN under J1's and J2's queries.

**Defects.** (1) OOXML formats store locale-neutral values, so INVARIANT is
near-certain for re-saves, while the informative keystroke arm is
descriptive only; flips will likely sit in CSV, convert and date paths (J1,
J3). (2) The locale line ("below a 3% upper bound") cannot be reached on the
92 golds alone (J2; O8). (3) The build and locale thresholds are
inconsistent (J1). (4) Postconfig replay under other builds is untested; the
CPU-h estimate is unverifiable (c202).

**Correction.** O6: alternative LibreOffice builds can be installed in
derived LO-VM Docker images without root.

**First experiment.** 0 GPU-h on the CPU lane.

### 8. Checker-revision drift on fixed end states, then an external anchor

`R05-checker-revision-drift`. Slate section 8. **Owner's disposition: HOLD
until R03's executor exists; the offline leg can run any time.**

Scores: Sig 4.50, Corr 6.00, Cite 7.00, Nov 5.17, Feas 6.33. J1
4.5/6/7/5.5/6, J2 4/5/7/5/5, J3 5/7/7/5/8. Passes both gates.

**What the judges agreed on.** Lifting S1a's "not externally anchored" label
matters inside the program; outside it, it is a hygiene table (J1).

**Defects.** (1) Weak identification in the gate that licenses the anchor:
S1a's end states are mostly failures with unchanged files, so 98% agreement
is near-guaranteed and says little about drift on PASS-like states (J2).
(2) Captures hold only what the pinned getters fetched, so getters of the
old revision that read other paths cannot be exercised (J2). (3) The public
runs' revision is inferred (J1). (4) The in-VM leg needs the executor R03
builds (J3).

**Corrections.** S4: among the 74 re-admittable tasks, `get_vm_file` covers
71 and `get_cloud_file` 57 (103 and 84 are over all 116). S5 and c197: the
anchor run is at most 240 episodes, about 0.65 GPU-h physical (0.8 cap). O5:
the remote-code ruling (D49 (iii)) and the download authority (D1) already
exist. An AWS-against-nested-KVM mismatch would make a failed anchor hard to
read (J3).

**First experiment.** 0 GPU-h drift test; the anchor is an existing design
(S1a's A0b and ANC), so a registration and pre-freeze audit, no gauntlet.
Restrict the agreement gate to changed-file or PASS-like states before
freeze.

### 9. Input-design oracles for TF32: same-sign and exact-lattice families

`R10-input-design-oracles`. Slate section 6. **Owner's disposition: FOLD the
lattice-survival census into R11; hold the oracle with Q1.**

Scores: Sig 4.33, Corr 5.67, Cite 7.67, Nov 4.00, Feas 8.33. J1 5/6/8/5/8,
J2 4/5/7/3/8, J3 4/6/8/4/9. Passes both gates. The highest feasibility on the
slate.

**What the judges agreed on.** An elegant, CPU-decisive answer to D46's
limiting result: exact-lattice inputs make order-free TF32 realizations
bit-exact, so zero tolerance becomes valid (J1, J3).

**Defects.** (1) Integer-input exact GEMM testing is long-standing practice
(all three), and 2609.12307 grades algorithm class with "ungameable" test
matrices (J2; O7). (2) The kill list names Winograd F(2x2,3x3) as an
order-free valid class right after ruling algebraic transforms out of
contract (J2). (3) "Every verdict reachable from the CPU run alone"
overstates it: the emulation is not uniformly faithful (L1/18) and
tensor-core accumulation is not IEEE (J2). (4) Lattices die at
normalizations and transcendentals, which bounds the scope (J1). (5) S9: the
389 of 390 kernels pass no explicit non-TF32 precision; operand dtype was not
checked.

**First experiment.** 0 GPU-h, 2-3 CPU-days (unverified, c201).

### 10. Task-success cost of known action-path defects

`R07-action-path-defect-cost`. Slate section 4. **Owner's disposition: FOLD
Stage 0 (the counterfactual census) into the Q2 report's action-path
appendix; drop Stage 1.**

Scores: Sig 4.00, Corr 5.67, Cite 7.33, Nov 4.83, Feas 7.33. J1
4/5/7/4.5/7, J2 4/5/8/5/7, J3 4/7/7/5/8. Passes both gates.

**What the judges agreed on.** Stage 0 is cheap, deterministic and a valid
bound, because untouched episodes translate identically (J1, J3). The
quantity is incremental: cua-speedrun found and fixed these defects (J1).

**Defects.** (1) Premise error: three of the four H-OSW-up defects the slate
lists are design choices H-OSW-fixed keeps (J2; O2). The OSW pair contrasts
`terminate(failure)`, the key-name map, text whitespace and `wait`. (2) The
motivating −4.86 against −0.89 pp comes from task strata with uncertified
keysym exposure, not known-defect exposure (S3, J2). (3) Stage 1 at one size
and R = 2 gives a δ half-width of about 3.5-4 pp, so PRESENT needs about 6 pp
and NEGLIGIBLE is nearly unreachable (J1, J3).

**Corrections.** S7: 2610.04433's 13% is the median on a 45-task hard subset.
S2 and c047: A7's step p50 2.628 s is in the record.

**First experiment.** Stage 0 0 GPU-h, with the OSW pair's translators
restricted to the four real fixes.

### 11. Translated instructions in a desktop agent: language or lost referents?

`R15-translated-cua-referents`. Slate section 11. **Owner's disposition:
HOLD; revisit only with a larger informative pool (for example S2 v3's
LibreOffice pool).**

Scores: Sig 3.83, Corr 5.33, Cite 7.00, Nov 5.00, Feas 3.67. J1
3.5/5/7/5/3, J2 4/5/7/5/4, J3 4/6/7/5/4. Passes both gates.

**What the judges agreed on.** The within-task estimands are clean, but the
Phase 0 gate (at least 30 informative tasks with locatable referents) meets a
9B set of only 32 informative tasks in all, so the expected outcome is a stop
at 0 GPU-h, as the slate concedes (all three).

**Defects.** T_pres is code-switched Arabic, so L mixes language with code
switching (J2). Narrow: Arabic instructions on English interfaces, one model
(J1).

**First experiment.** Phase 0 0 GPU-h; Phase 1 at most 4.1 GPU-h.

### 12. Accessibility tree on the certified path vs S1a's floor

`R08-a11y-observation`. Slate section 13. **Owner's disposition: DROP as a
line.**

Scores: Sig 3.83, Corr 5.50, Cite 7.00, Nov 3.00, Feas 5.33. J1
3.5/5.5/7/3/5, J2 4/5/7/3/5, J3 4/6/7/3/6. Passes both gates. The lowest
novelty residual of the gate passers.

**Why.** About 3.3 cap-GPU-h for a 0.50-0.70 chance of a decisive reading
(design study J2), with the observation contrast's variance unmeasured; the
factor is covered by OSWorld and 2608.06171; S1b, which would have carried
it, is closed (D69). S14: the a11y cost factor is an assumption. Context
growth on top of history folding and 2,048 thinking tokens is a further risk
(J2).

### 13. The speed premium of a pure precision cut, per gate

`R13-precision-premium`. Slate section 14. **Owner's disposition: DROP as a
line.**

Scores: Sig 3.67, Corr 5.83, Cite 6.00, Nov 4.33, Feas 5.00. J1
4/5.5/6/5/5, J2 3/6/6/4/5, J3 4/6/6/4/5. Passes both gates; citability at
the floor.

**Why.** The answer is largely predictable from first principles: H100 bf16
dense tensor throughput is about twice TF32, and 1e-2 allclose on
`torch.rand` admits bf16-level error (all three). The GPU estimate (c199)
and the prevalence figures (c188) are unverifiable, it needs D46 lifted and
dedicated timing GPUs, and once R11 shows which gates accept bf16 most of
the premium follows (J3).

### 14. Does greedy rerun noise shrink with scale within Qwen3.5?

`R09-noise-scale-ladder`. Slate section 15. **Fails the correctness gate**
(J2 3).

Scores: Sig 4.00, Corr 4.33, Cite 7.00, Nov 4.00, Feas 4.33. J1 4/5/7/4/4,
J2 4/3/7/4/5, J3 4/5/7/4/4.

**Why it fails.** The primary estimand is degenerate (J2; O8): with p̂ from
the same reruns, discordance among tasks with 0 < p̂ < 1 is exactly 2/3 at R
= 3 and 1 at R = 2, so the 27B-against-4B prediction is fixed by construction
and differs by design between rungs. A task-by-rerun residual in a logit GLMM
with one binary outcome per cell is not identified (J2). FP8 large rungs
confound scale with quantization; 27B and 35B-A3B prices are unmeasured; it
should follow R01 (all three). A redesign would need an external difficulty
measure or p̂ from held-out reruns.

### 15. A session-inclusive noise band on published OSWorld-Verified claims

`R06-session-band-published-claims`. Slate section 12. **Fails the
correctness gate** (J2 4).

Scores: Sig 4.00, Corr 4.67, Cite 7.33, Nov 3.50, Feas 7.67. J1 4/5/8/3.5/8,
J2 4/4/7/4/7, J3 4/5/7/3/8.

**Why it fails.** The session SD has no sound source: S1a's two sessions per
size falsified P1 (upper bound 0.78 pp), the Holo3 pair is an operator
contrast by the 2026-10-06 dossier's own reading, and OpenCUA's turns show
none (J2). Moving a Qwen3.5-4B/9B, 15-step band onto frontier agents at
50-100 steps assumes the portability R01 says may not hold, and the
cross-agent band borrows S1a's task correlation (J1, J2). The framing is
crowded: 2609.17394, 2610.00651, 2608.11323, 3vXI4xEByc, and J1's 2610.05830
and 2609.33012 (O7). At most a labelled section of the Q2 report.

---

## Coverage limits

- Every retrieval used orx 0.2.2, which reports itself outdated against
  0.2.18. The alphaXiv results reached publication dates up to 2026-10-09,
  so papers posted on 2026-10-10 or 2026-10-11 are not covered.
- OpenReview: api2 search only; per-note fetches and PDFs sit behind a bot
  challenge, which no step bypassed. ICLR 2027 submissions are judged from
  abstracts or titles.
- ACL Anthology: the dossier owner searched the full abstracts export by
  regex (5 queries). EMNLP 2026 is likely not in that export yet.
- The judges' queries are known only from their reasons; their exact strings
  and result lists were not passed on.
- Owner checks O1-O6 read the repository at `d4f8339` (this branch before
  this commit); D72 is read from main (`0848d1e`), which this branch does not
  yet contain. O1 rests on the committed listings of host run files. No host
  was read for this dossier.
- No host job, GPU job or download ran for this dossier. The only data read
  outside the repository was the ACL Anthology export already in the session
  scratchpad (SHA-256 prefix `85a53292`).
