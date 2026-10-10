# Research Direction: E4 gate, oracle interface ceiling and key-span sufficiency for a distilled in-context write rule (D19 backfill)

**Status:** repaired under program decision D60 for a fresh gauntlet run, after gauntlet wave 1 (score 49, the lower of 55 and 49; all three refuters refuted; honest exit on the query budget, `program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl`); repair by the single owner on 2026-10-10 on the Mac CPU (no GPU, no host job); the draft registration is now `program/preregistrations/e4-icl-write-rule-gate-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted; the blind critic, the refute-first triad and the two reviewers of this run have not run; no executable pilot exists for this gate; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D60 repair (estimator, family table, identification design, draft registration, simulations) written by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-10
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex, 159 counted queries, 73 paper reads; see wave 1's limits in the record) plus this run's repair: 33 counted retrieval queries (13 orx discover; 10 OpenReview API searches over forum notes, including ICLR 2027 submissions; 10 ACL Anthology searches over the full `anthology+abstracts.bib`, 131,473 entries of which 82,295 have abstracts; the first 3 ACL searches read titles only because of a parser bug, are counted and were rerun) and 10 uncounted full-text reads (`orx paper --full`) of the six priors wave 1 left uncited and four found here; OpenReview's per-note endpoint returned a bot challenge, which was not bypassed, so OpenReview-only submissions were read through the search API's abstracts; not searched: Semantic Scholar and the arXiv API (unreachable from the Mac; the host relay was not used because the host is reserved for Q2 S1a), patents, X, Reddit, Hacker News, Chinese-language venues; the citation graph is degraded (OpenAlex citation counts unreliable); the alphaXiv embedding index favours recent papers; full texts read by targeted section.
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e4-icl-write-rule-gate/bundle.json

The budgets are this fresh run's (D60), cumulative over the repair, the triad,
the reviewers and the recorder; at least 30 of the 80 queries are reserved for
the three refuters (six orx discover queries each at minimum). The repair used
33, leaving 47. The novelty verdict field uses the doctor's vocabulary; the
merged verdict is NARROWED (below), not STILL_OPEN.

## Changes after wave 1

Wave 1 (the first row of the gauntlet file, row hash `b658a265...`;
proposal sha256 `22429938...`, registration v1 sha256 `4cef1c1c...`) scored 49:
reviewer 1 (claude-opus-5-5) 55, reviewer 2 (qwen3.6-35b-a3b, Slurm 1059) 49.
Blind discrimination against 2608.13385 passed. All three refuters refuted.
Its largest defect was identification: S1, the evidence offered for the
episode-specificity and span verdicts, did not implement the registered
estimator, and under the registered one a constant teacher passed the guard and
gradient-form teachers read GAP; a per-episode label prior and contextualised
keys gave further false GAPs. The runner-up was feasibility (the family table
could not be built under the teacher's tokenizer, K2 was set by the manifest,
and I1 and I2 could rarely pass together at 16 fitting probes); novelty
coverage was incomplete (the dual-form and KV-compaction lines uncited;
OpenReview and the ACL Anthology unsearched). D60 ordered one CPU-only repair by
a single owner and a fresh run. This section is that repair. Each row names who
found the defect, what changed, where it lives in registration v2, and the CPU
check that sizes it (bundle `compute/repair-d60/`: S1v2 = the registered
estimator on the linear surrogate, `oracle-estimator-v2.py`; G1 = guard,
`guard-sim.py`; F1 = family table under the real tokenizer, `family-table.py`;
S2v2 = decision path, `decision-sim-v2.py`; S3v2 = cost, `cost-model-v2.py`).

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | S1 did not implement the registered estimator: it fitted a full-rank constant on all 16 probes while the registration fitted rank 8 on 4 probes per episode; under the registered one a constant teacher passed the guard and first-order and RLS teachers read GAP in 6 of 6 families (identification refuter, replicated byte for byte by reviewer 1; both reviewers' largest defect) | The registered estimator is now code: `estimate_family` in S1v2 is the decision code, and the harness must reproduce its planted-teacher verdicts before any GPU job. In the identifiable regime (d_task 12, 24 fitting probes) every synthetic teacher reads as intended in 6 of 6 families: constant, family-generic nonlinear and per-episode label-prior teachers EPISODE_CONSTANT; first-order, first-order plus prior, contextualised-key, mismatched-contextualisation and RLS teachers TIE (the fixed-preconditioner teacher TIE 5/6 and undecided 1/6, never GAP); the lookup teacher SPAN_VACUOUS with D_span 0.00; retrieval and value-directed teachers GAP. In wave 1's regime (isotropic 32-d reads, 16 probes) the v1 estimator reproduces the failure (constant GAP 6/6, RLS GAP 6/6) and v2 reads EPISODE_CONSTANT and CAP_LOW, never GAP | Identity ("Code"); Classes; Decision rules | S1v2 `oracle-estimator-v2.json` |
| 2 | Constant misfit: a rank-8, 4-probe C_f leaves family-generic residual that per-episode states absorb as "episode-specific" and "out of span" (identification refuter, reviewer 1) | C_f full rank on every fitting probe of all 48 episodes with per-episode nuisance shifts (S1v2 showed label priors leaking into an ordinary C_f's linear part through chance correlation); I0 constant adequacy (leave-one-out mean episode part may remove at most 0.05 of KL_shift; one refit) | Classes (S_const); I0 | S1v2: a deliberately under-fitted C_f (half its linear part, a 5x larger true constant) inflates the per-episode fit and is stopped by I0 (0.20-0.29) in 6 of 6 families before any reading; I0 for every intended teacher -0.11 to -0.01 |
| 3 | The resample placebo was report-only (identification refuter, reviewer 1) | Decision-bearing: EPISODE_SPECIFIC needs the one-sided lower bound of Delta_res (own state against another episode's probe-dependent part on the episode's own shift) above 0.10 | Decision rule 4 | S1v2: lower bound -0.46 to 0.01 for constant-type teachers, 1.09 to 3.17 for episode-specific ones; I7 (planted label prior) passes in every instance |
| 4 | A probe-independent per-episode shift (label-prior calibration) lies outside span(B K) and reads GAP (identification refuter; reviewer 1 by algebra) | Every per-episode class carries a free shift; S_shift is the floor for E and D_span; probe-dependent parts act on centred reads; label-prior guard KL_shift >= 0.10 KL_LD on teacher SHUF predictions; I7 | Classes; Quantities; Decision rule 4; I7 | S1v2: label-prior teacher EPISODE_CONSTANT 6/6; first-order plus prior TIE 6/6 (D_span -0.04 to -0.01) |
| 5 | Keys were alone-encoded; a gradient-form teacher with contextualised keys reads GAP (identification refuter; reviewer 1: plausible and unaddressed) | In-context keys added; the decision-bearing key set is chosen among alone, in-context and a shared map over both (B_k on the keys' read-subspace coordinates, fitted like C_f on all fitting probes); I6 plants a writer on keys from a permuted-order context and caps OPEN if it would read GAP | Reads, centring and keys; Classes (S_span); I6 | S1v2: contextualised-key and mismatched-contextualisation teachers TIE 6/6 each; I6 passes in 12 of 12 planted instances |
| 6 | STOP_TR's KL_S0 guard fires on families Step 1 certified as label-dependent (identification refuter; reviewer 1: plausible) | Replaced by the placebo rule and the label-prior guard | Decision rule 4 | G1: the old guard misreads 69 of 171 label-dependent settings, the new 0 of 171, and the new one catches 57 of 57 label-prior settings |
| 7 | The family table could not be built: no "▁"+digit token, the 40-input and disjointness rules drop F2, F3, L1, L2, L5; K2 an absolute 8 of 14, so STOP_TEACHER was set by the manifest (feasibility refuter; recorder confirmed) | Family table rebuilt and checked under the teacher's tokenizer (refetched at the pinned revision, sha256 matches): whole-string single-token rule, deliberate digit tokenization (the prompt ends in the bare "▁" token, as before any number in pretraining text), 15 families (10 episode-specific), floor of 60 usable inputs, every family built (67-400 inputs); K2 = fewer than 4 eligible ES families; M1 format sanity on fixed-function families | Families; Step 1; Decision rules 1-2 | F1 `family-table.json`; S2v2: STOP_TEACHER only when the teacher fails (weak-teacher scenario 1.00; never in the other scenarios) |
| 8 | I1 and I2 pass together in 1 of 42 settings at 16 fitting probes; S1's E_free 0.29-0.40 (feasibility refuter; reviewer 1 confirmed in logic) | 24 fitting probes; I1 per family on centred reads at 0.25 (I3's planted out-of-span check carries discriminability); I2 planted norms from the natural shift, best of 3 restarts | Step 2; I1-I3 | S1v2 grid (seed 42, 2 families per cell): at 16 probes I2 fails at every d_task of 12 or more (wave 1's window problem reproduced); at 24 probes I1 (0.39-0.56), I2, I3, I6 and I7 pass together and the first-order teacher reads TIE and the value-directed teacher GAP in every cell for d_task 12-16 (d90 10-13); at 32 probes the same holds for d_task 12-24 (d90 10-19). Hence the registered rule: 24 fitting probes, or 32 with 24 evaluation episodes per family when the development d90 is 14 or more (high cost 5.07 GPU-h, inside the 5.5 cap). d_task 6-8 reads SPAN_VACUOUS with I3 failing (the gate correctly refuses a span reading) and d_task 32 fails I2 at every probe count |
| 9 | More probes push the high case to 7.5 GPU-h and over D20's line (feasibility refuter) | Prompt lengths measured with the teacher's tokenizer (zero-shot max 13, 8-shot max 125 tokens, against assumed 24 and 400); blocks 1-6 cached (exact reuse, checked by I4); design re-counted; SHUF-target fits dropped | Compute | S3v2: caps 0.17 + 0.55 + 5.5 + 1.5 = 7.72 GPU-h; Step 2 high 5.47 (4.58 after the ladder); with wave 1's assumed lengths it would be 8.21 |
| 10 | The tie decision was underpowered, so INCONCLUSIVE_SPAN was the likely end (reviewer 1; wave-1 design doctor) | STOP_SPAN by a pooled random-effects bound across capable families with no GAP family | Decision rule 6 | S2v2: P(STOP_SPAN) under a true tie 0.61 (central) and 0.47 (high noise), against 0.35 and 0.09 under v1's count rule, and 0.84 and 0.70 when the true shortfall is -0.02 as in S1v2; no false STOP_SPAN in any gap scenario |
| 11 | STOP_INTERFACE_CLASS was the default sink for identification limits; no ceiling for E_free (identification refuter) | Conditional in-sample ceiling: INCONCLUSIVE_IDENTIFICATION before any interface stop | Decision rule 5 | registration only |
| 12 | I5 likely to fail (S1: B* not recovered), capping OPEN (reviewer 1) | B_k parametrised on the keys' read-subspace coordinates and fitted on all episodes' fitting probes; I5 plants on all 48 episodes and passes when the planted writer would not read GAP | Classes (S_span); I5 | S1v2: fixed-preconditioner teacher now TIE 5/6 and undecided 1/6, never GAP (D_span 0.01-0.06; wave 1's S1: GAP 0.68-0.82); I5 passes in 11 of 12 (wave 1's B: 0 of 12) |
| 13 | I1 pooled across families; I2 planted norms circular; I2/I3 never test S_ref (identification refuter) | I1 per family (SPAN_VACUOUS); planted norms from the natural shift; S_ref only in the conditional arm, behind the in-sample ceiling | I1, I2; Decision rule 5 | registration only |
| 14 | Novelty coverage: 2212.10559, 2311.07772, 2404.11225, 2506.06266, 2602.16284, 2609.17346 uncited; OpenReview and the ACL Anthology unsearched; key-span confidence overstated (novelty refuter; both reviewers) | All six read in full and cited (C31-C36) with four more found (C37-C40, 2507.04221, 2507.16003, 2310.19698, 2610.05885) and OpenReview-only and ACL items (C41-C43); OpenReview searched through its API (10 queries, ICLR 2027 submissions included) and the full ACL Anthology bibliography with abstracts (10 queries); the key-span component lowered to medium-low; the closest prior is now Attention Matching with Cartridges; blind packets for it, the dual form and 2608.13385 | Proposal only | `query-log-run2.json`; Closest Prior Work; Novelty Ledger; `blind/` |
| 15 | STOP_SPAN was sold as ICL-as-GD evidence while the registration licensed no GD claim (novelty refuter; reviewer 1) | Claim scope rewritten: the class also holds Hebbian and linear-attention memories, so STOP_SPAN says nothing about GD specifically | Question (claim scope) | registration only |
| 16 | Query budget overrun (159/150); two refuters ran no queries (process defect) | This run declares 80 queries with at least 30 reserved for the triad; the repair used 33 | Proposal header | `query-log-run2.json` |

Not repaired, and why:

- No harness, adapter, manifest, container smoke or Slurm dry run exists
  (Compute FAIL, cap 79). They come after a scored package and a freeze, and no
  host job may run while a Q2 S1a job runs or is pending.
- No noise SD, read spectrum or throughput has been measured on the teacher.
  Measuring the probe-read spectrum on CPU needs the 2.7 GB checkpoint on the
  Mac, which wave 1 left as an owner decision; it was not downloaded. The
  window in which I1 and I2 can pass together (S1v2 grid) is therefore a
  surrogate statement, and d90 is reported at the start of Step 2 before any
  reading.
- The fixed-preconditioner check I5 now passes in 11 of 12 surrogate instances
  (after B was moved to the read-subspace coordinates and fitted on all
  episodes' fitting probes; with wave 1's B it passed 0 of 12). On the teacher
  it is unmeasured; a failure caps OPEN at INCONCLUSIVE_SPAN, so a true gap
  would then also read INCONCLUSIVE_SPAN.
- Signed, provider-distinct reviews cannot exist here (D24, cap 89).
- The deterministic doctor parses `gpu_hours=0.3` as 0 and reports "all
  declared budgets must be positive"; the declared budget is honest and is not
  rounded up to pass (rule 3).

Decisiveness after the repair (S2v2, `compute/repair-d60/decision-sim-v2.json`;
the whole v2 decision path per replicate, 2,000 replicates per cell, 10
episode-specific and 5 fixed-function families, Holm over 15, 32 evaluation
episodes; instrument gates assumed passed, their surrogate pass rates below;
every noise SD assumed): probability of the correct verdict.

| Scenario (correct verdict) | central noise (sd_D 0.10, sd_E 0.15) | high noise (sd_D 0.20, sd_E 0.30) | wave-1 count rule for STOP_SPAN, central / high |
|---|---:|---:|---:|
| weak teacher, 2 of 10 families label-dependent (STOP_TEACHER) | 1.00 | 1.00 | |
| task recognition, no episode-specific part (STOP_TR) | 1.00 | 1.00 | |
| low capacity, E_free 0.30 (STOP_INTERFACE) | 1.00 | 1.00 | |
| tie, D_span 0 with family SD 0.05 (STOP_SPAN) | 0.61 | 0.47 | 0.35 / 0.09 |
| tie, D_span -0.02 as S1v2's key-span teachers (STOP_SPAN) | 0.84 | 0.70 | 0.61 / 0.23 |
| gap, D_span 0.20 (OPEN) | 0.93 | 0.79 | |
| small gap, D_span 0.12 with E_free 0.65 (OPEN) | 0.69 | 0.38 | |

Mean over the seven scenarios: 0.87 at central noise and 0.76 at high noise;
the largest probability of a wrong decisive verdict in any cell is 0.004 (a
false OPEN under a true tie at high noise). The lookup families are excluded
from the span counts (they read SPAN_VACUOUS by construction), so the span
verdict rests on the 6 non-lookup eligible families in these scenarios. The
variance rule's 64 episodes raise the high-noise tie rows to 0.60 and 0.81. In the 32-probe branch (24 evaluation episodes per family) the four span rows read 0.60, 0.82, 0.92 and 0.65 at central noise and 0.42, 0.63, 0.74 and 0.26 at high noise, with a wrong decisive verdict at most 0.004. The
OPEN rows also need I5 and I6 to pass on the teacher (S1v2: I5 11 of 12, I6 12 of 12 planted instances).
Every number is conditional on the instrument gates passing; in the S1v2
surrogate they pass together only inside an identifiable window (d90 10-13 at 24 fitting probes and 10-19 at 32, the two registered branches),
so the probability that the gate reaches any scientific verdict also depends
on the teacher's probe-read dimension, which is measured at the start of Step
2 before any reading.

## Scope and what changed from the dossier

This proposal covers only the E4 gate: Step 1 (teacher eligibility) and Step 2
(an oracle interface ceiling). Step 3 (training a free write rule against a
gradient-form rule), the port to recurrent bases, the cross-lingual stage and the
independent-ladder replication are out of scope. Each would need its own
gauntlet. The gate is what the dossier
(`program/evidence/2026-10-06/question-dossier.md`, entry
`E4-d19-icl-rule-distillation-port`) asked to run first, and D58 scopes wave 1
to it.

This section is wave 1's synthesis, kept as written; the D60 repair amends
rows 2 and 4 (the key sets now include in-context keys, and the controls are
re-specified) as listed under "Changes after wave 1".

Four discovery findings change the gate as the dossier wrote it. Each one is
re-checked in this proposal, by a CPU check, a full-text read, or both.

| # | Finding (cell) | Consequence for the gate | Where handled |
|---:|---|---|---|
| 1 | KILL A (kill-shot cell): the legacy interface reuses D16's rank-8 factorised port maps P (64 x d_b, rank 8). Every key and every probe read then lies in one 8-d subspace, and 8 demonstrations span it, so a state restricted to the span of the keys gives the same reads as a free state. The dossier's Step-2 tie rule ("if the free and key-span oracles tie ... stop") fires by construction. Cell receipt: gap 0.0 at seeds 42/43/44 and a read difference of 1.8e-14 at pilot shape | The port map becomes a full-rank 64-d map (rank 64), so 8 keys span 8 of 64 readable dimensions. A pre-registered non-vacuity check on real residuals must pass before the span contrast is read. This breaks the deliberate identity with D16's interface; a result here no longer tests D16's premise directly | S1 (this bundle) replicates KILL A and shows the repair; registration I1 |
| 2 | The gradient-form class w_i = k_i excludes the literature's own GD-like solutions: a preconditioned step whose preconditioner approximates the inverse data covariance ([2306.00297](https://arxiv.org/abs/2306.00297), Sec. 4.1, 2023-06-01) and recursive least squares in the mesa-layer ([2309.05858](https://arxiv.org/abs/2309.05858), Sherman-Morrison derivation, 2023-09-11) (kill-shot and cross-domain cells) | The restricted class is redefined as the span of the demonstration keys after one linear map B shared by all episodes. It contains first-order updates with any fixed preconditioner, recursive least squares, and preconditioned recursive least squares. B = I (the exact dual form of plain first-order updates, [2202.05798](https://arxiv.org/abs/2202.05798), Sec. 2, 2022-02-11) is reported as a secondary | Mechanism; registration Step 2 classes |
| 3 | A free-over-key-span gap can be produced by retrieval among latent tasks a pretrained model already knows, not by a non-gradient learning rule. The legacy doctor's positive control is prior memorisation (wave-5 reviewer: 0.94 falls to -0.72 on a held-out prior) and a learned amortizer on GPT-2 shows zero leave-one-task-out transfer ([2610.00526](https://arxiv.org/abs/2610.00526), Table 2, 2026-09-30) (kill-shot and frontier cells) | A family-constant state absorbs task identity before the span contrast. The gate's positive outcome is renamed OPEN: it says a later rule-versus-rule study has room to separate, and it is pre-registered as uninformative about whether that room comes from retrieval or from a non-gradient rule | Mechanism; Negative-Result Value; registration decision rules |
| 4 | Step 2 as written could not be read as a capacity result: no optimiser-adequacy check, no control for a variance-driven label-free map discarding label-bearing directions, no floor stronger than M = 0, no guard against off-manifold edits (cross-domain cell: [2106.05945](https://arxiv.org/abs/2106.05945), [2110.14633](https://arxiv.org/abs/2110.14633), [2412.11299](https://arxiv.org/abs/2412.11299), [2404.03592](https://arxiv.org/abs/2404.03592)) | Planted-state recovery, a width-256 reference, a conditional supervised-map arm, placebo and family-constant floors, a norm cap at twice the natural in-context residual shift, and context-change principal directions instead of variance principal directions | Controls; registration I2 to I4 |

Two more corrections to the dossier, recorded here because a frozen dossier is
not edited: Jeong's "universal write rule"
([2603.22329](https://arxiv.org/abs/2603.22329), Sec. 8.3, v1 2026-03-20) is an
attention-coupled aggregation with temporal decay and fixed random write
projections, not a Hebbian rule (Hebbian is only its method M.4; frontier cell,
re-checked in the cell's full-text read); and the dossier's requirement of "at
least 4 function-induction families" admits families that pass the
gold-versus-shuffled test through task recognition, because pairs identify a
stored function ([2310.15916](https://arxiv.org/abs/2310.15916), 2023-10-24;
[2310.15213](https://arxiv.org/abs/2310.15213), 2023-10-23). The gate instead
requires at least 4 eligible families whose mapping changes from episode to
episode.

## Claim and Research Question

**Question.** For the frozen fla-hub `transformer-1.3B-100B` teacher
(revision `d6f66f4181fa669e5863327815b44533e3a395e7`, MIT card tag,
[model page](https://huggingface.co/fla-hub/transformer-1.3B-100B)), four
quantities decide whether any later study of a distilled in-context write rule
at a 64-d residual interface can be informative:

1. **Eligibility.** On how many of 15 synthetic task families (10 whose correct
   mapping changes from episode to episode) does the teacher show
   label-dependent in-context learning (accuracy with gold demonstrations minus
   accuracy with deranged labels, over three demonstration seeds)?
2. **Episode-specificity.** On how many eligible episode-specific families is
   the teacher's eight-shot behaviour carried by each episode's own state better
   than by another episode's (the resample placebo), beyond what one family
   state plus a per-episode label prior carries?
3. **Interface ceiling.** Can a per-episode rank-8 state at the interface (a
   64 x 65 affine matrix at each of four residual depths, read from and written
   into a fixed label-free 64-d subspace), fitted directly to the teacher's own
   eight-shot predictions, remove at least half of the probe-dependent
   divergence the family constant and the per-episode shift leave, on held-out
   probes?
4. **Key-span sufficiency.** Does confining the read side of the episode's
   probe-dependent part to the span of the eight demonstrations' own interface
   reads (encoded alone and in context, after one linear map shared by all
   episodes) lose anything measurable?

The variable is the state class (none, family constant, per-episode shift,
key-span with the chosen key set, key-span with alone keys, key-span with
in-context keys, free rank 8, free rank 16 at width 256, and the resample and
random placebos), fitted per episode by the same optimiser to the same targets.

**Claim scope.** `portability-protocol` prerequisite. The gate measures one
frozen teacher. It makes no architecture, portability, learning-rule or
gradient-descent claim (registration v2, "Claim scope"). The key-span class
contains every write whose read side is an outer product with a mapped
demonstration read: first-order, preconditioned and recursive-least-squares
updates, and also Hebbian and linear-attention memories with free values. The
only claims the gate can license are of the form "at this interface, the
teacher's episode-specific, probe-dependent in-context behaviour on these
families is (not) carried by any rank-8 state, and is (not) carried by states
whose read side lies in the span of the demonstrations' own reads".

**Hypothesis under test (H_gate).** At least 4 episode-specific families are
eligible; at least 4 of them are EPISODE_SPECIFIC by the placebo rule; the free
state carries at least half of the remaining divergence on at least 75% of
those; and the key-span class falls short of the free class by at least 0.10
of that divergence on at least half of the capable families. H_gate is what a
later rule-versus-rule study needs. Each clause has a pre-registered failure.

## Strategic Fit and Why Now

E4 is item 3 of the backfill queue (`program/backlog.md`). D58 chose it
because its prerequisites are CPU work and the host is reserved for Q2 S1a; D60
continued it for one repair and a fresh run. The gate's GPU work is small (sum
of registered caps 7.72 GPU-h, central estimate about 1.6 GPU-h;
`compute/repair-d60/cost-model-v2.json`) and runs only when no S1a job is
running or pending, after a scored and reviewed package and a freeze.

The gate's value does not depend on the later stages surviving. Each of its
stopping outcomes is informative on its own:

- **STOP_TEACHER** says label-dependent, episode-specific in-context learning at
  1.3B/100B tokens is confined to few families. That is a measured floor for
  every 1.3B write-rule and fast-weight study in the program, including D16.
- **STOP_TR** says that on the families where the correct mapping changes
  between episodes, one state per family plus a per-episode label prior
  already reproduces the teacher's eight-shot behaviour at this interface, and
  no episode's own state beats another episode's: task recognition and label
  calibration, with nothing episode-specific and probe-dependent for a write
  rule to carry.
- **STOP_INTERFACE** (or its size and label-free-map variants) says the 64-d,
  rank-8, four-site interface cannot carry the teacher's episode-specific
  behaviour, whatever rule writes it. That closes D19 and constrains D16 for a
  few GPU-hours, before any rule is trained.
- **STOP_SPAN** says every episode-specific behaviour the interface can carry is
  expressible by writes whose read side lies in the span of the demonstrations'
  own reads. Then no rule-versus-outer-product-write contrast can separate at
  this interface, and Step 3 is closed without being run. It says nothing about
  gradient descent specifically (the class also holds Hebbian and
  linear-attention memories).

Wave 1 of this gauntlet scored 49 (all three refuters refuted); D60 allowed one
fresh run and set its exit: below 60, or identification still the largest
defect, ends E4. The legacy D19 direction ran five gauntlet waves (62, 57, 65, 65 by the lower
reviewer; `legacy/directions/19-icl-rule-distillation-port.md`) and exited at
"under two points of gain across three waves". Both wave-5 reviewers named
identification defects that the gate now removes rather than repairs (KILL A,
the clamp co-condition passing under the null, prior memorisation). The
competing frontier is moving fast: four of the priors closest to E4 appeared
since August 2026 (One Adapter Pair 2026-08-10, When Is a Task Vector Enough?
2026-08-13, Task Operators 2026-10-01, Internalizer 2026-10-08).

## Primary-Source Evidence

Every row was opened by a discovery cell or by synthesis. "Full" means `orx
paper --full` text read by targeted section; "abstract" means the abstract page
only. First-party marks a number not independently replicated. Claim ids C01 to
C30 are wave 1's registry; C31 to C44 were added by the D60 repair (read by the
repair owner on 2026-10-10). The Citation doctor's registry is
`doctors/citation.json`.

| id | Claim used here | Source | Date | Read | Status |
|---|---|---|---|---|---|
| C01 | Each head's ICL output is an affine transform of its context-masked counterpart, replayed training-free as a per-input W_O update; evaluated on Qwen3-4B/8B and Llama-3.2-3B/3.1-8B instruct, K = 8, 8 tasks; unstable at large K | [2610.01054](https://arxiv.org/abs/2610.01054) Sec. 3 Eq. 3, Sec. 4.1, App. A | 2026-10-01 (v1) | full (frontier, kill-shot, synthesis) | verified |
| C02 | Implicit multimodal ICL: nested static, query-conditioned, multi-site and routing interventions, matched in rank and injected norm, scored by recovery of the explicit-ICL gain on held-out queries; static recovery tracks the share of the demonstration-induced change common to all queries; 16 shots; OpenFlamingo-v2-9B, Idefics2-8B, LLaVA-NeXT-7B | [2608.13385](https://arxiv.org/abs/2608.13385) Sec. 2 Eqs. 1-6, Sec. 4.3, Sec. 5.1, Table 3 | 2026-08-13 (v1) | full (synthesis) | verified; single author, first-party numbers |
| C03 | Context distilled into fast weights (MLP down-projection) with a fixed gradient-form update, same model as teacher and student; nothing learned about the rule, nothing ported | [2608.01672](https://arxiv.org/abs/2608.01672) Sec. 3, Proposition 1 | 2026-08-03 (v1) | full | verified |
| C04 | A 2.6M-parameter network reads support-set geometry and writes an input-conditioned mid-depth residual update into frozen GPT-2-large/XL; leave-one-task-out transfer 0.00 to 0.03; wrong-task manifolds collapse accuracy to 0.06 or below | [2610.00526](https://arxiv.org/abs/2610.00526) Sec. 2, Tables 1-2 | 2026-09-30 (v1) | full | verified; single-author workshop paper, first-party |
| C05 | Label-free per-model linear adapter pairs into a shared 3072-d space; round-trip self-FVE 0.591 to 0.980; five softmax transformers, no recurrent model | [2608.09521](https://arxiv.org/abs/2608.09521) Sec. 4, App. E.1-E.2 | 2026-08-10 (v1) | full | verified |
| C06 | Shared model-agnostic context-to-LoRA trunk with thin per-base entry and exit layers, warm-started on five 1-3B bases and ported to a frozen 284B model; frozen trunk with cold-started maps above 90% top-1 in the 64-token setting | [2610.11715](https://arxiv.org/abs/2610.11715) Sec. 3.7, 4.5-4.6, 6.3 | 2026-10-08 (v1) | full (frontier, synthesis) | verified; first-party |
| C07 | PorTAL: frozen task latent and decoder core learned on Qwen3-1.7B and 4B, refitting a thin per-base alignment recovers about 98% of LoRA's lift on Qwen3-8B and about 94% on Gemma-3-4B | [PorTAL blog](https://labs.ramp.com/research/portal-portable-task-adaptation/) headline results | 2026-07-01 | opened by synthesis 2026-10-10 | first-party blog, not peer reviewed |
| C08 | Jeong's shared write rule is a fixed attention-coupled aggregation with decay and random write projections; GPT-2 only, one benchmark, one seed | [2603.22329](https://arxiv.org/abs/2603.22329) Sec. 4.1, 8.3, 8.4 | 2026-03-20 (v1) | full | verified; corrects the dossier |
| C09 | Task learning (abstract labels) is acquired with scale; small models (GPT-3 babbage 1.3B, OPT-350M/2.7B) are flat with the number of demonstrations | [2305.09731](https://arxiv.org/abs/2305.09731) Sec. 4.1 | 2023-05-16 (v1 only) | full | verified |
| C10 | ICL and GD differ in order sensitivity and output-distribution shift in LLaMa-7B and GPT-J; the equivalence remains "an open hypothesis" | [2310.08540](https://arxiv.org/abs/2310.08540) abstract, Sec. 4-5 | 2023-10-12 (v1) to 2024-06-03 (v5) | full | verified |
| C11 | A single linear self-attention layer's global optimum implements one step of preconditioned GD; for large n the preconditioner approximates the inverse data covariance | [2306.00297](https://arxiv.org/abs/2306.00297) Sec. 4.1 | 2023-06-01 | full (kill-shot, synthesis) | verified |
| C12 | The mesa-layer solves in-context least squares; Sherman-Morrison gives recursive least squares | [2309.05858](https://arxiv.org/abs/2309.05858) mesa-layer section | 2023-09-11 | full | verified |
| C13 | A linear layer trained by GD equals its initial weights plus a sum of outer products of errors with inputs (dual form) | [2202.05798](https://arxiv.org/abs/2202.05798) Sec. 2 | 2022-02-11 | full | verified |
| C14 | Kalman-gain associative memory treats a covariance-weighted write direction as part of the delta-rule family | [2609.07816](https://arxiv.org/abs/2609.07816) abstract | 2026-09-07 | abstract (kill-shot) | abstract only |
| C15 | Flipped-label override rate is zero across eight open 1-12B models | [2511.21038](https://arxiv.org/abs/2511.21038) abstract, Table 1 | 2025-11-26 | full (kill-shot) | verified |
| C16 | Function-induction ICL is strong at small scale and mostly removed by shuffled labels | [2310.15916](https://arxiv.org/abs/2310.15916) results table; [2310.15213](https://arxiv.org/abs/2310.15213) Table 2 | 2023-10-24; 2023-10-23 | full (kill-shot) | verified |
| C17 | At fixed stitching rank, task-loss maps beat variance-based (SVD) maps; principal-component magnitude does not track information | [2110.14633](https://arxiv.org/abs/2110.14633) Sec. 7 | 2021-10-27 | full (cross-domain) | verified |
| C18 | Transformer residual streams are dominated by one principal direction; ZCA whitening before alignment | [2609.08692](https://arxiv.org/abs/2609.08692) Fig. 3, Sec. 5.1 | 2026-09-08 | full (cross-domain) | verified; first-party |
| C19 | Task-loss stitching layers produce out-of-distribution representations | [2412.11299](https://arxiv.org/abs/2412.11299) Sec. 4 | 2024-12-15 | full (cross-domain) | verified |
| C20 | A stitching result must show the stitcher is not doing the work | [2106.07682](https://arxiv.org/abs/2106.07682) Sec. 3 | 2021-06-14 | full (cross-domain) | verified |
| C21 | Students can fail to match a teacher they have the capacity to match; optimisation is the main cause | [2106.05945](https://arxiv.org/abs/2106.05945) Sec. 6 | 2021-06-10 | full (cross-domain) | verified |
| C22 | Low-rank interventions on a frozen model's hidden representations, rank 1 to 64 swept | [2404.03592](https://arxiv.org/abs/2404.03592) Sec. 3.2 | 2024-04-04 | full (cross-domain) | verified |
| C23 | Linearising attention costs few-shot ability first: Llama 3 8B 5-shot MMLU 66.6 to 52.8 under LoLCATs | [2410.10254](https://arxiv.org/abs/2410.10254) main LM-Eval table | 2024-10-14 | full (cross-domain) | verified |
| C24 | Error consistency (chance-corrected agreement) between decision makers | [2006.16736](https://arxiv.org/abs/2006.16736) Sec. 2.2 | 2020-06-30 | full (cross-domain) | verified |
| C25 | Learning rules can be recovered from behaviour with ground-truth recovery simulations first | [2509.04661](https://arxiv.org/abs/2509.04661) Sec. 3 | 2025-09-04 | full (cross-domain) | verified |
| C26 | Finite task diversity gives Bayes-optimal retrieval (dMMSE); high diversity gives ridge regression | [2306.15063](https://arxiv.org/abs/2306.15063) abstract | 2023-06-26 | report (kill-shot) | abstract-level |
| C27 | Steering outside a feature's natural range need not reflect the model's computation; tests should use values observed on natural inputs | [2610.07270](https://arxiv.org/abs/2610.07270) abstract | 2026-10-05 | abstract (synthesis query) | abstract only |
| C28 | Shuffled labels in demonstrations; contextual calibration with content-free inputs | [2202.12837](https://arxiv.org/abs/2202.12837); [2102.09690](https://arxiv.org/abs/2102.09690) | 2022-02-25; 2021-02-19 | metadata (asset cell, OpenAlex) | method citations only |
| C29 | fla-hub 1.3B/100B checkpoints: transformer and GLA receipts exist on the host; 2.7B registered without receipt; fla 0.5.2's Attention raises ImportError without flash_attn, which no image contains | [transformer-1.3B-100B](https://huggingface.co/fla-hub/transformer-1.3B-100B), [transformer-2.7B-100B](https://huggingface.co/fla-hub/transformer-2.7B-100B) (HF API, 2026-10-10); fla 0.5.2 `fla/layers/attn.py` in the host uv cache | 2026-10-10 | asset cell (read-only ssh before 11:30 UTC; uv.lock and Dockerfile) | verified by reading, not by running a container |
| C30 | FineWeb-Edu is ODC-By | [dataset page](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) | 2026-10-10 | asset cell | verified (card) |
| C31 | Relaxed linear attention splits the attention output into a zero-shot term and a demonstration term equal to a weight update, a sum of outer products of demonstration value and key vectors (the dual form of gradient descent); ICL compared empirically with one-step key/value fine-tuning on GPT 1.3B and 2.7B by recall of correct predictions and attention-output and attention-weight similarity | [2212.10559](https://arxiv.org/abs/2212.10559) Sec. 2.2, 3.1 Eq. 11-12, 3.2, 4.1 | 2022-12-20 (ACL Findings 2023) | full (repair) | verified |
| C32 | The ICL-GD similarity metrics are problematic and untrained models reach comparable scores; a layer-causal GD variant improves similarity; GPT 1.3B | [2311.07772](https://arxiv.org/abs/2311.07772) abstract, Sec. 3.3, 4.1-4.5, 6 | 2023-11-13 (NAACL 2024) | full (repair) | verified |
| C33 | Cartridges: a free trainable KV prefix per corpus, initialised from the corpus's first p tokens' cache and trained by KL context distillation on self-generated conversations, frozen model | [2506.06266](https://arxiv.org/abs/2506.06266) Sec. 3.2, 4.2 Eq. 3 | 2025-06-06 (v3 2025-06-13) | full (repair) | verified |
| C34 | Attention Matching restricts compact keys to a subset of the original keys, fits values by least squares and biases by NNLS to match attention outputs and mass; the authors attribute Cartridges' advantage at 100x compaction to its not being restricted to selecting keys from the original cache | [2602.16284](https://arxiv.org/abs/2602.16284) Sec. 3.2-3.3, Discussion | 2026-02-18 (ICML 2026) | full (repair) | verified |
| C35 | Controlled, storage-matched comparison on five knowledge benchmarks (Qwen3-8B): at 2x, Compaction 73.4 average, Cartridges 70.6, LoRA 64.5; Compaction degrades steeply at high compression while Cartridges stay nearly flat | [2609.17346](https://arxiv.org/abs/2609.17346) Sec. 3, 4, 5.1, Table 2 | 2026-09-15 | full (repair) | verified; first-party |
| C36 | ICL compressed vectors analysed as GD-trained parameters ("state vector"); inner and momentum optimisation refine them | [2404.11225](https://arxiv.org/abs/2404.11225) abstract, Sec. 1 | 2024-04-17 | full by outline (repair) | verified |
| C37 | Context Tuning initialises a trainable prompt or KV prefix (CT-KV) from the demonstrations and refines it by gradient descent for few-shot adaptation | [2507.04221](https://arxiv.org/abs/2507.04221) abstract, Sec. 1 | 2025-07-06 (ICML 2026) | full by section (repair) | verified |
| C38 | A self-attention layer stacked with an MLP is equivalent, for a given query, to the MLP with a context-dependent rank-1 weight patch whose read side is the query's own context-free attention output (unique minimal-norm patch) | [2507.16003](https://arxiv.org/abs/2507.16003) Theorem 2.3 | 2025-07-21 | full by section (repair) | verified |
| C39 | Prefix-tuning cannot change the relative attention over content tokens and can only bias an attention layer's output in a fixed direction (from a subspace of rank at most the prefix length) | [2310.19698](https://arxiv.org/abs/2310.19698) abstract, Sec. 4 | 2023-10-30 (ICLR 2024) | full by section (repair) | verified |
| C40 | Optimising a compact KV state through a frozen model has a brittle, flat loss landscape | [2610.05885](https://arxiv.org/abs/2610.05885) abstract, Sec. 1 | 2026-10-05 | full by section (repair) | verified; first-party |
| C41 | ICLR 2027 submissions (OpenReview, abstracts through the search API): Attention-Patching fits layer-wise affine maps from non-contextual attention representations to demonstration-induced output changes per demonstration set; ICL-R reconstructs routing and value shifts of multimodal demonstrations; an empirical study finds inference-time fast-weight updates contribute little in In-Place TTT | OpenReview submission ids JHUthhdVQu, vdDNOvVZxW, x7actWdqhZ (read through `api2.openreview.net/notes/search`, queries R06, R07, R09; forum pages not fetched because they return a bot challenge) | 2026-09 (submissions) | abstract (repair) | abstract only; anonymous submissions |
| C42 | Label biases in ICL (vanilla-, context- and domain-label bias) and calibration by an estimated label prior | [2023.acl-long.783](https://aclanthology.org/2023.acl-long.783/) abstract | 2023 (ACL 2023) | abstract (repair, ACL bib) | abstract only; method citation for the label-prior control |
| C43 | A learnable task vector as a weighted sum of attention heads, optimised by gradient descent | [2025.findings-acl.345](https://aclanthology.org/2025.findings-acl.345/) abstract | 2025 (Findings ACL 2025) | abstract (repair, ACL bib) | abstract only |
| C44 | The teacher's tokenizer (revision d6f66f41) is a 32,000-token BPE with a normaliser that prepends "▁" and no pre-tokenizer; "▁" = 28705; digits exist only as bare "0"-"9"; enc("input: 47\noutput: 4") ends [28747, 28705, 28781] | [tokenizer.json at the pinned revision](https://huggingface.co/fla-hub/transformer-1.3B-100B/blob/d6f66f4181fa669e5863327815b44533e3a395e7/tokenizer.json), sha256 fc4f0bd7... | 2026-10-10 | run (repair: `family-table.py` with tokenizers 0.22.2) | verified by running |

## Closest Prior Work

Ranked by how close the mechanism is to the gate's measurement. The D60 repair
adds the two lines wave 1 left uncited (KV compaction, the empirical dual-form
line) after reading each in full, and moves the structural closest prior to the
top.

1. **Fast KV Compaction via Attention Matching**
   ([2602.16284](https://arxiv.org/abs/2602.16284), Zweiger, Fu, Guo, Kim, ICML
   2026; v1 2026-02-18; full text read), with its free comparator **Cartridges**
   ([2506.06266](https://arxiv.org/abs/2506.06266), Eyuboglu et al., 2025) and
   the controlled comparison **Where Should a Document Live**
   ([2609.17346](https://arxiv.org/abs/2609.17346), 2026-09-15). The structural
   closest prior. A state confined to the context's own keys (a subset of the
   original cached keys, values by least squares, biases by NNLS) is compared at
   matched size with a free state (a trainable KV prefix fitted by KL to the
   model's own context-conditioned predictions), and the free state's advantage
   at extreme compaction is attributed to its not being confined to the original
   keys (C34). Same: a confined-to-own-keys class against a free class, both
   fitted to the frozen model's own behaviour with the context present, scored
   on held-out queries; the free state initialised from real keys. Different,
   and why it matters for the question: (a) the classes do not nest with the
   gate's. A subset of original keys inside softmax attention expresses
   query-dependent, nonlinear reads that no linear-read residual state
   expresses, and the gate's class is a linear span of mapped demonstration
   reads at a residual write, not a subset; so neither result predicts the
   other. (b) Compaction compresses one long document for question answering;
   there is no task family, no family-constant or per-episode label-prior floor,
   no placebo, and no notion of an episode-specific part. (c) Their contrast
   compares two methods that differ in objective (attention matching against
   end-to-end KL) as well as class; the gate's classes share the objective,
   optimiser, rank and budget and differ only in the read-side constraint. (d)
   Their contrast is about compression rate; the gate's is about whether the
   outer-product write family is expressive enough for a teacher's in-context
   behaviour, which is what a distilled write rule (Step 3) would need.
2. **Why Can GPT Learn In-Context?**
   ([2212.10559](https://arxiv.org/abs/2212.10559), Dai et al., ACL Findings
   2023; full text read), continued by **In-context Learning and Gradient
   Descent Revisited** ([2311.07772](https://arxiv.org/abs/2311.07772), Deutch
   et al., NAACL 2024) and the state-vector paper
   ([2404.11225](https://arxiv.org/abs/2404.11225)). The source of the key-span
   class: under relaxed linear attention, the demonstrations' effect is a sum of
   outer products of their value and key vectors (C31). Dai compares ICL with
   one-step key/value fine-tuning on GPT 1.3B and 2.7B by similarity metrics;
   Deutch shows those metrics are matched by untrained models (C32). Same: the
   outer-product row space, pretrained models at the teacher's scale, an
   empirical ICL-versus-gradient-form question. Different: the gate assumes no
   linear attention and measures no similarity to fine-tuning. It asks whether
   any state whose read side lies in the demonstrations' span can carry the
   episode-specific behaviour at a fixed external interface, against a
   rank-matched unconstrained state, with planted recovery and placebo floors
   that answer Deutch's baseline objection; and its tie is not evidence for GD
   (the class is larger than GD).
3. **When Is a Task Vector Enough? An Empirical Theory of Implicit Multimodal
   ICL** ([2608.13385](https://arxiv.org/abs/2608.13385), Li, v1 2026-08-13;
   full text read in wave 1). The closest measurement prior and wave 1's blind
   packet (passed). Nested interventions replacing demonstrations, matched in
   rank and norm, recovery on held-out queries; its shared/variable split runs
   across queries within one demonstration set, never across episodes of a
   family, and it has no key-span class.
4. **Capturing In-Context Learning Dynamics with Task Operators**
   ([2610.01054](https://arxiv.org/abs/2610.01054)) and **Learning without
   training** ([2507.16003](https://arxiv.org/abs/2507.16003), Dherin et al.).
   Exact per-input identities that replay ICL as a weight update (per-head
   affine W_O update; a rank-1 MLP patch whose read side is the query's own
   context-free attention output, C38). Same: ICL's effect as a weight update
   inside a frozen model. Different: per-query and exact, so no single
   per-episode state, no constrained class and no fitted oracle; Dherin's patch
   reads along the query, not the demonstrations, which is a reason to expect
   that exact effects need not lie in the demonstrations' span (the gate
   measures whether a fitted per-episode state needs to leave it).
5. **Context Tuning** ([2507.04221](https://arxiv.org/abs/2507.04221), CT-KV)
   initialises a trainable KV prefix from the demonstrations and refines it for
   accuracy (C37); **Attention-Patching** (ICLR 2027 submission, C41) fits
   per-demonstration-set affine maps; **Rules Amortize, Pairings Don't**
   ([2610.00526](https://arxiv.org/abs/2610.00526)) learns an amortizer; **TTCD**
   ([2608.01672](https://arxiv.org/abs/2608.01672)) distils context into fast
   weights with a fixed gradient-form update that lies inside the key-span class.
   None compares a confined with an unconstrained per-episode state.

Adjacent and cited, not closest: Petrov et al. on prefix-tuning's
fixed-direction bias (C39; the gate's S_shift class is its residual-site
analogue, and E measures what exceeds it); the compacted-context optimisation
landscape (C40; motivates I2); label-bias calibration (C28, C42; the label-prior
floor and guard); One Adapter Pair (C05), Internalizer (C06) and PorTAL (C07)
for the later port; Jeong (C08); SADA (ACL 2026) for state-aligned context
distillation; learned update rules moved across architectures before D19
(1703.04813, 1907.09720, 2012.14905), so no later stage may claim "the first
transferable write rule".

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Per-episode oracle states fitted by KL to a frozen LM's own few-shot predictions, scored on held-out probes | 2506.06266 (Cartridges: free KV prefix by KL context distillation); 2608.13385 (oracle conditional coefficients); 2507.04221 (CT-KV) | A state fitted to the model's own context-conditioned behaviour, held-out queries | Few-shot episodes of task families; states at a fixed label-free residual interface; a nested class ladder with matched rank, objective and optimiser | low (the fitting recipe is published) |
| Confined-to-own-representations class against a free class | 2602.16284 with 2506.06266 and 2609.17346 (original-key subset against a free KV prefix); 2212.10559 (dual-form row space) | A state confined to the context's own keys compared with a free state | A linear span of the demonstrations' interface reads (alone and in context, after one shared map), which contains every outer-product write, rather than a softmax key subset; objective, rank and budget matched, so only the read-side constraint differs; applied to few-shot ICL, where the classes do not nest with KV compaction's | medium-low (lowered from wave 1's medium-high: the contrast exists in KV compaction and the class in the dual-form line) |
| Family-constant floor plus a per-episode label-prior shift, with a decision-bearing resample placebo | 2310.15213, 2310.15916 (averaged task/function vectors); 2608.13385 (static shift across queries); 2310.19698 (prefix-tuning as a fixed-direction bias); 2102.09690, 2023.acl-long.783 (label-prior calibration) | A shared state as a floor; a label prior as a confound | The episode-specific, probe-dependent part is defined against both floors and must beat another episode's state; a label-prior guard on the teacher's own GOLD-versus-SHUF divergence | medium |
| Identification controls before any reading: constant adequacy (I0), planted recovery and discrimination (I2, I3), planted preconditioned (I5), contextualised-key (I6) and label-prior (I7) writers | 2509.04661 (ground-truth recovery before interpretation); 2106.05945 (optimisation, not capacity); 2311.07772 (untrained baselines for ICL-GD claims) | Recovery and baseline checks before interpretation | Applied to oracle state classes at an LM interface, with planted writers chosen to fail each false-GAP route the wave-1 refuters found | medium; low weight as novelty |
| Episode-specific family classes as built-in predictions (lookup families span-sufficient) | 2306.15063; 2608.13385 | Controlled task structure | Synthetic families built under the teacher's tokenizer, generated in the repository | medium |

**Merged verdict: NARROWED.** Every component is published; the delta is
their combination applied to few-shot ICL with identification controls, at an
interface a later write rule would use.
No direct prior art found through 2026-10-10 under the recorded coverage below
for an oracle comparison, at a fixed
residual interface of a frozen pretrained language model and fitted to the
model's own few-shot predictions, of per-episode states whose read side is
confined to the span of the demonstrations' own interface reads (alone-encoded
and in-context, after one shared map) against rank-matched unconstrained
states, with a family-constant floor, a per-episode label-prior floor and a
decision-bearing resample placebo. The gate does not claim the first
confined-versus-free comparison (KV compaction has one), the first empirical
dual-form test (Dai, Deutch), or the first oracle replacement of
demonstrations (2608.13385, Task Operators, Attention-Patching).

**Coverage of this claim.** Wave 1's 159 counted queries (listed in
`query-log.json` and the wave-1 record) plus this run's repair queries
(`query-log-run2.json`, 33 counted, raw-output digests recorded):

- orx keyword: N01 "When do prompting and prefix-tuning work theory of
  capabilities and limitations" (2310.19698); N02 "Learning without training
  implicit dynamics of in-context learning low-rank weight update MLP"
  (2507.16003); N04 "context tuning in-context optimization trainable prefix
  initialized from demonstrations KV"; N06 "optimization landscape of learning
  compacted context models" (2610.05885); N07 "key-value memory restricted to
  span of context keys versus free keys expressivity fitted by distillation";
  N08 "Context Tuning for In-Context Optimization"; N09 "oracle intervention
  replacing demonstrations fitted to the model's own few-shot predictions
  held-out queries upper bound in-context learning"; N11 label-bias
  calibration; N12 "in-context learning versus test-time training fast weights
  equivalence pretrained language model gradient-form update few-shot".
- orx embedding: N03 (the v2 mechanism in plain words, published after
  2025-06-01); N10 (outer-product writes along the demonstrations versus other
  directions, fitted to the model's own outputs, published after 2024-01-01).
- orx openalex: N05 "in-context learning implicit weight update outer product
  of demonstration keys empirical test pretrained language model"; N13
  "expressivity comparison constrained versus unconstrained per-context state
  reproduce in-context learning frozen language model".
- OpenReview (api2 search over forum notes, including ICLR 2027 submissions):
  R00/R01 "in-context learning gradient descent dual form"; R02 "key span"
  in-context learning oracle state; R03 "task vector" oracle intervention
  demonstrations episode-specific; R04 "in-context learning" "low-rank" update
  span demonstrations; R05 Cartridges KV cache compaction attention matching
  keys; R06 implicit in-context learning residual stream intervention replace
  demonstrations; R07 in-context learning implicit weight update fast weights
  outer product pretrained language model; R08 prefix tuning expressivity
  limitations in-context attention; R09 three ICLR 2027 titles.
- ACL Anthology (all-of regular expressions over title and abstract of the
  full bib): A04 in-context && gradient descent; A05 dual form && (attention or
  in-context); A06 in-context && (task/function/in-context/state vector) &&
  (oracle, optimised, upper bound or span); A07 context distillation &&
  (in-context, demonstration or few-shot); A08 (KV cache, key-value cache or
  prefix) && (in-context or demonstration) && (trainable, optimised, learned or
  distilled); A09 in-context && implicit && (weight update, meta-optimisation,
  fast weight or low-rank update); A10 in-context && (label bias or
  calibration) && (prior, shift or majority); A01-A03 (title-only, flawed,
  rerun as A04-A06).

They returned the priors above and, among ICLR 2027 submissions,
Attention-Patching, ICL-R, an In-Place TTT study, KV-compaction variants
(ARC-KV, KV-Surgeon, Still, LowRAM, Cartridges++), and "Learned Structure in
Cartridges: Keys as Shareable Routers"; none runs the comparison.
PRISMA-style counts for the repair: 33 queries, 701 ids identified, 590 unique
screened by title, about 25 abstracts read, 10 full texts read, 0 included as
direct prior.

## Mechanism and Falsifiable Predictions

**Setting.** Frozen teacher T = `transformer-1.3B-100B` (24 layers, width 2048,
32 heads, vocabulary 32k, context 2048). An episode is 8 demonstrations
(x_i, y_i) of one task family followed by probe queries (16 in Step 1; 32 in
Step 2, of which 24 fit and 8 score); the teacher's target for probe q is its
next-token distribution p_T(. | demos, q) at the answer position, under GOLD and
under SHUF (deranged labels).

**Interface (unchanged).** Four sites, after decoder blocks 6, 12, 18 and 24.
At each site k a fixed map P_k (64 x 2048, rank 64) and its write-back Q_k =
W_k^-1 V_k, P_k = V_k^T W_k, where W_k whitens the site's residuals on
FineWeb-Edu and V_k holds the top 64 principal directions of the whitened
context-induced change on FineWeb-Edu text. No task text enters P or Q. The
student is the same frozen model reading the zero-shot prompt, with h replaced
by h + Q_k M_k [x; 1] at every probe position, x = P_k h.

**Reads, centring and keys (new).** The family's centring vector mu_k is the
mean development read; every probe-dependent part acts on x - mu_k, and every
per-episode class carries a free shift, so a constant component of the reads
cannot be split arbitrarily between the shift and the probe-dependent part (S1v2
showed that split inflating both the placebo contrast and the span gap before
centring). Alone keys k_i^a are the reads at the answer position of
demonstration input i encoded alone; in-context keys k_i^c are the reads at the
answer position of demonstration i inside the 8-shot prompt.

**State classes (nested), per episode e of family f.**

```text
S0        M = 0
S_const   M = C_f            full rank (64 x 65), every fitting probe of 48 episodes, per-episode nuisance shifts
S_shift   M = C_f + b_e 1^T  (free per-episode shift: a label prior)
S_span    M = C_f + b_e 1^T + U_e Z_e^T (x - mu)   Z_e = orth(span of the episode's mapped keys): K^a, K^c, or
                                                   S B [S^T K^a; S^T K^c] with S the family's probe-read subspace and
                                                   B (r x 2r) fitted on all episodes' fitting probes; key set chosen
                                                   per family on development held-out KL
S_free    M = C_f + b_e 1^T + A_e G_e^T (x - mu)   A_e, G_e 64 x 8
S_resample(e)  C_f + b_e 1^T + (A G^T) of episode e+1     (placebo, decision-bearing)
S_rand, S_span_alone, S_span_ctx, S_ref                    (secondaries; S_ref conditional)
```

S_span contains every write whose read side is an outer product with a mapped
demonstration read: first-order updates (B = I), first-order updates with a
fixed preconditioner (any B), recursive least squares (its write direction
(B K K^T B^T + lambda I)^-1 B k_i stays in span(B K) by the push-through
identity), and Hebbian and linear-attention memories with free values. S_free
is the ceiling for any rank-8 per-episode probe-dependent write at this
interface.

**Fitting.** Adam on the KL from the teacher to the student over 24 (or 32)
fitting probes, 200 steps (C_f: 400 and B: 800 minibatch steps of 256 probes),
learning rate per class from {1e-2, 3e-2, 1e-1} on development episodes, initialised from C_f, norm cap at twice the
median natural in-context shift. Scores use the 8 other probes only. The span
classes are parametrised in an orthonormal basis of their row space; S_free
starts LoRA-style with no knowledge of the keys.

**Quantities.** With KL_X summed over held-out probes of a family's 32
evaluation episodes: E_X = 1 - KL_X / KL_shift (the share of the remaining,
probe-dependent divergence removed); D_span = E_free - E_span (paired within
episode); Delta_res = (KL_resample - KL_free) / mean KL_shift (the placebo
contrast); KL_LD = sum KL(p_T^GOLD || p_T^SHUF) (the teacher's own label
sensitivity); I0 = the share of KL_shift that the leave-one-out mean of other
episodes' probe-dependent parts removes (constant adequacy).

**Falsifiable predictions and the kill criterion for each.**

| id | Prediction | Falsifier (decision rule in registration v2) |
|---|---|---|
| P1 | At least 4 of the 10 built episode-specific families are eligible (gold-minus-shuffled gap at least 0.10, Holm over 15, gold at least 0.05 above zero-shot) | K2 (STOP_TEACHER): fewer than 4; INFRA_FAIL instead if fewer than 2 fixed-function families reach 0.50 GOLD accuracy (M1) |
| P1b | At least 4 eligible ES families are EPISODE_SPECIFIC: each episode's own state beats another episode's (lower bound of Delta_res above 0.10) and the per-episode shift does not explain the label sensitivity (KL_shift at least 0.10 KL_LD) | STOP_TR: fewer than 4 |
| P2 | On the EPISODE_SPECIFIC families, E_free has a one-sided 95% lower bound of at least 0.50 in at least 75% of them | Capacity stops when CAP_LOW holds in at least half: INCONCLUSIVE_IDENTIFICATION if the in-sample ceiling reaches 0.50, else STOP_LABEL_FREE_MAP, STOP_INTERFACE_SIZE or STOP_INTERFACE_CLASS |
| P3 | On capable families that pass I1, D_span is at least 0.10 with a lower bound above 0.02 in at least max(2, half) of them | STOP_SPAN: at least 3 capable families, no GAP family, and the one-sided 95% upper bound of the across-family mean of D_span at most 0.05; INCONCLUSIVE_SPAN otherwise |
| P4 | Built-in structure: lookup families (A1, A2) are span-sufficient; the fixed-function control family reads EPISODE_CONSTANT | A lookup family with D_span above 0.05 blocks OPEN |
| P5 | Instrument validity on real residuals: I0 at most 0.05; planted recovery at least 0.90 (I2); planted out-of-span parts give D_span at least 0.30 and planted key-span parts at most 0.03 (I3); a planted label prior does not pass the placebo (I7) | INSTRUMENT_FAIL (I0 per family with one refit) |
| P6 | Planted gradient-form writers with a fixed preconditioner (I5) or with keys from a permuted-order context (I6) read as ties | Either failure caps the span verdict at INCONCLUSIVE_SPAN |

**What the surrogate says about the registered estimator (S1v2,
`compute/repair-d60/oracle-estimator-v2.json`; linear surrogate, 32-d
interface, squared error for KL, d_task 12, 24 fitting probes, 14 development
and 32 evaluation episodes, seeds 42/43/44, 2 families each).**

| Synthetic teacher (truth) | v2 verdict, 6 families | D_span | E_free | lower bound of Delta_res |
|---|---|---:|---:|---:|
| family constant, no episode part | EPISODE_CONSTANT 6/6 | -0.40 to -0.31 | -0.69 to -0.57 | -0.19 to -0.05 |
| family constant plus family-generic nonlinear behaviour | EPISODE_CONSTANT 6/6 | -1.03 to -0.74 | -1.65 to -1.27 | -0.46 to 0.01 |
| per-episode label prior only (probe-independent shift) | EPISODE_CONSTANT 6/6 | -0.44 to -0.29 | -0.72 to -0.55 | -0.23 to -0.06 |
| first-order write on alone keys | TIE 6/6 | -0.04 to -0.02 | 0.92 to 0.94 | 1.63 to 1.80 |
| first-order write plus a label prior | TIE 6/6 | -0.04 to -0.01 | 0.91 to 0.94 | 1.64 to 1.73 |
| first-order write on the site's in-context keys | TIE 6/6 | -0.03 to -0.01 | 0.92 to 0.95 | 1.40 to 1.66 |
| first-order write on keys contextualised differently from the site's reads | TIE 6/6 | -0.04 to -0.02 | 0.91 to 0.95 | 1.63 to 1.74 |
| recursive least squares | TIE 6/6 | -0.04 to -0.01 | 0.89 to 0.93 | 1.63 to 1.79 |
| fixed preconditioner (condition number 10) | TIE 5/6, undecided 1/6 | 0.01 to 0.06 | 0.93 to 0.95 | 1.61 to 1.83 |
| lookup (probes are the demonstrated names) | SPAN_VACUOUS 6/6 (I1 0.04-0.06), D_span 0.00 | 0.00 | 0.98 | 2.91 to 3.17 |
| retrieval among four stored family tasks | GAP 6/6 | 0.13 to 0.23 | 0.78 to 0.81 | 1.09 to 1.60 |
| value-directed write (unconstrained) | GAP 6/6 | 0.28 to 0.33 | 0.90 to 0.93 | 1.64 to 1.81 |
| first-order write, C_f deliberately under-fitted | INSTRUMENT_FAIL_I0 6/6 (I0 0.20-0.29) | -0.01 to 0.04 | 0.87 to 0.89 | 1.08 to 1.27 |

I0 is -0.11 to -0.01 for every intended teacher. Planted gates on the constant
and first-order runs (12 instances, d90 = 10): I2 12/12, I3 12/12, I5 11/12
(mean planted D_span 0.02-0.12; the failing instance's mean is 0.123), I6
12/12, I7 12/12. In wave 1's regime (isotropic reads over the whole 32-d
interface, no template mean, 16 fitting probes), the v1 estimator reproduces
the wave-1 failure (constant teacher GAP 6/6 with D_span 0.84-0.96 and a
passing guard 0.29-0.38; RLS GAP 6/6, 0.35-0.57), while v2 reads the constant
EPISODE_CONSTANT 6/6 and first-order and RLS CAP_LOW 6/6 (D_span -0.62 to
-0.52), never GAP. Two estimator defects were found and fixed while building
S1v2, before any final run, and are recorded here: without the per-episode
nuisance shifts in C_f's fit, label priors leaked into C_f's linear part and I0
read 0.55 for the label-prior teacher; without centred reads, a constant
component split arbitrarily between the shift and the probe-dependent part
inflated the placebo contrast (Delta_res above 300 for a planted label prior).
A 64 x 128 B fitted on 14 development episodes did not recover the fixed
preconditioner (D_span 0.16-0.31, I5 0/12), which is why B now acts on the
read-subspace coordinates and is fitted on all episodes' fitting probes.

**Strongest counter-argument.** A positive P3 (OPEN) is predicted by
within-family task retrieval alone (dMMSE-like behaviour,
[2306.15063](https://arxiv.org/abs/2306.15063)), and S1v2's retrieval teacher
reads GAP. The gate therefore pre-registers that OPEN does not identify a
non-gradient learning rule. Its only consequence is that a Step-3 study would
not be closed by expressivity, and that study must separate retrieval from rule
structure with its own design.

## Cheapest Decisive Pilot

The gate is itself the cheapest decisive experiment the dossier names. Its
cheapest decisive part comes first:

- **Step 0 (CPU, Mac; 0 GPU-h):** the family table is built and checked under
  the teacher's tokenizer (done in this repair: F1); generators and manifest
  hashing; the harness for the four-site read path, the state classes and the
  instrument gates, tested on a tiny random-init Llama-shaped model; the
  harness must reproduce S1v2's planted-teacher verdicts (the registered
  estimator is S1v2's `estimate_family`, transcribed to KL and Adam).
- **Step 0b (host CPU job, only with no S1a job running or pending):** fetch and
  receipt of `transformer-2.7B-100B` (secondary only).
- **Smoke (GPU, at most 0.17 GPU-h):** load the 1.3B teacher two ways (Llama
  remap with SDPA, and fla 0.5.2 with a harness-side SDPA shim), cross-check
  logits, FineWeb-Edu loss sanity, the cached-prefix equivalence check, and
  oracle-step throughput with and without the cached prefix; sets the caps'
  projection before freeze.
- **Step 1 (GPU, cap 0.55 GPU-h):** eligibility on 15 families. If
  STOP_TEACHER, nothing else runs.
- **Step 2 (GPU, cap 5.5 GPU-h, plus a conditional 1.5 GPU-h arm):** P fits,
  instrument gates, oracle classes, decisions.

The first decisive reading is Step 1, at a central estimate of 0.08 GPU-h. The
teacher-strength risk (weak label-dependent in-context learning at 1.3B,
[2305.09731](https://arxiv.org/abs/2305.09731),
[2511.21038](https://arxiv.org/abs/2511.21038)) is tested first, and K2 now
needs 7 of 10 built episode-specific families to fail on the teacher, so it
cannot be set by the manifest. The families are synthetic and generated in the
repository, so a pass cannot come from contamination.

## Controls, Baselines, and Ablations

| Control | Kind | What it rules out |
|---|---|---|
| Shuffled labels (seeded derangement; A3-A5 re-drawn from the episode's label set) | Step 1, decision-bearing; Step 2 targets for KL_LD | Format and input-distribution effects counted as in-context learning |
| Zero-shot (template only) and S0 | Step 1 and Step 2 floor | Gains the base model has without demonstrations |
| Fixed-function format sanity (M1) | Step 1, decision-bearing (INFRA_FAIL) | A broken template or tokenization read as STOP_TEACHER |
| Family-constant state C_f, full rank, per-episode nuisance shifts | Step 2, every class builds on it | Task recognition read as episode-specific writing; label priors leaking into the constant's linear part |
| Per-episode shift S_shift (floor for E and D_span) | Step 2, decision-bearing | A label-prior or calibration shift (C28, C42) read as episode-specific, probe-dependent writing or as out of span |
| Resample placebo (own shift + another episode's probe-dependent part) | Step 2, decision-bearing (EPISODE_SPECIFIC) | A state that helps by absorbing family-generic structure, not by carrying the episode |
| Label-prior guard KL_shift >= 0.10 KL_LD | Step 2, decision-bearing | Label dependence that a per-episode prior explains |
| Constant adequacy I0 | Step 2 instrument gate | Constant misfit absorbed by per-episode states and read as episode-specific and out of span (the wave-1 false-GAP route) |
| Key-span constraint with key set chosen among alone, in-context and fitted B | Step 2, decision-bearing | Room for a non-outer-product write where none exists; a key-definition artefact |
| Planted free and key-span states, best of 3 restarts (I2); out-of-span and in-span plants (I3) | Step 2 instrument gates | Optimiser failure read as capacity; a span class that cannot discriminate |
| Planted fixed-preconditioner writer (I5) and permuted-context-key writer (I6) | Step 2, cap OPEN | A gap that is really a preconditioned or differently contextualised gradient-form writer |
| Planted label-prior writer (I7) | Step 2 instrument gate | A placebo that calls a label prior episode-specific |
| Non-vacuity per family (I1) | Step 2, SPAN_VACUOUS per family | KILL A recurring through the interface geometry |
| In-sample ceiling (conditional) | Step 2 capacity disambiguation | An identification limit (24 probes) read as an interface limit |
| Width-256 rank-16 reference; supervised P and Q (conditional) | Step 2 capacity disambiguation | "64-d too small" or a label-free map discarding label-bearing directions read as a class limit |
| Norm cap at twice the natural in-context shift | Step 2 | Off-manifold edits inflating the ceiling ([2412.11299](https://arxiv.org/abs/2412.11299), [2610.07270](https://arxiv.org/abs/2610.07270)) |
| Site-1.0 ablation; permuted-target re-scoring; random-state placebo | Step 2 secondaries | A logit-level shortcut; recovery regardless of the probe; help from being a state at all |
| Lookup families span-sufficient by construction | built-in prediction, blocks OPEN | Span gaps that are artifacts of template or key definition |
| 2.7B disagreement rate | Step 1 secondary | Whether a later cross-teacher sibling control would be live |

There is no "baseline method" to beat: the gate compares state classes fitted
by the same optimiser with the same objective, per-class learning-rate grid
and budget, so no class is undertuned relative to another.

## Evaluation, Statistics, and Leakage Checks

**Units and seeds.** Demonstration seeds [42, 43, 44]: seed 42 episodes fix
mu_k, the read subspace and d90, select learning rates and key sets, and carry
the planted gates except I5, which is planted on all episodes (development);
seeds 43 and 44 give the 32 (or, in the 32-probe branch, 24) evaluation
episodes per family. C_f and B are fitted on the fitting probes of every
episode. Oracle initialisation seed 42; restarts 43 and 44. All episode
generation uses PCG64 keyed by (family, seed, episode); manifests (including
`family-table.json`) are hashed before any GPU run.

**Step 1 statistics.** Per family, G_LD = mean over seeds of (accuracy with gold
minus accuracy with shuffled labels), 1,200 query instances per condition.
One-sided cluster-t bound with episodes as clusters (75), Holm over the 15
families at one-sided alpha 0.05.

**Step 2 statistics.** Per family, one-sided 95% t bounds over the 32
evaluation episodes (df 31) on Delta_res, E_free and D_span (paired within
episode), with an episode bootstrap (2,000 resamples, seed 42) as sensitivity.
STOP_SPAN pools across capable families with a random-effects bound (t over
families, df n_ok - 1) and requires no GAP family; OPEN counts GAP families as
in wave 1.

**Guard (G1, `compute/repair-d60/guard-sim.json`, exact categorical model).**
Wave 1's KL_S0 guard reads 69 of 171 label-dependent settings (accuracy
0.45-0.90, cardinality 2-8, three SHUF behaviours, zero-shot candidate mass
0.05-0.4) as EPISODE_CONSTANT; the label-prior guard reads 0 of 171 (smallest
ratio 0.19 against its 0.10 line) and catches all 57 pure label-prior settings
(wave 1: 23).

**Decision path (S2v2, `compute/repair-d60/decision-sim-v2.json`; 2,000
replicates per cell; 10 ES and 5 FF families; Holm over 15; assumed noise).**
The probability of the correct verdict under six scenarios whose truth is
known (instrument gates assumed passed; their surrogate pass rates are in
S1v2):

| Scenario (truth) | sd_D 0.05, sd_E 0.15 | sd_D 0.10, sd_E 0.15 (central) | sd_D 0.20, sd_E 0.30 (high) | wrong decisive verdict, max over cells |
|---|---:|---:|---:|---:|
| weak teacher: 2 of 10 ES families label-dependent (STOP_TEACHER) | 1.00 | 1.00 | 1.00 | 0.000 |
| task recognition: 8 eligible, no episode-specific part (STOP_TR) | 1.00 | 1.00 | 1.00 | 0.000 |
| low capacity: E_free 0.30 (STOP_INTERFACE) | 1.00 | 1.00 | 1.00 | 0.000 |
| tie, D_span 0 with family SD 0.05 (STOP_SPAN) | 0.64 | 0.61 | 0.47 | 0.004 |
| tie, D_span -0.02 as S1v2's key-span teachers (STOP_SPAN) | 0.87 | 0.84 | 0.70 | 0.001 |
| gap, D_span 0.20 (OPEN) | 0.98 | 0.93 | 0.79 | 0.000 |
| small gap, D_span 0.12, E_free 0.65 (OPEN) | 0.74 | 0.69 | 0.38 | 0.0005 |

Lookup families are excluded from the span counts (SPAN_VACUOUS by
construction) and act only as the OPEN guard. Wave 1's count rule for
STOP_SPAN would give 0.35 (central) and 0.09 (high) in the first tie row; the
pooled rule gives 0.61 and 0.47. The variance rule's 64 episodes raise the
high-noise tie rows to 0.60 and 0.81. In the 32-probe branch (24 evaluation episodes per family) the four span rows read 0.60, 0.82, 0.92 and 0.65 at central noise and 0.42, 0.63, 0.74 and 0.26 at high noise, with a wrong decisive verdict at most 0.004. The OPEN rows assume I5 and I6 pass; in
S1v2 I5 passed in 11 of 12 planted instances and I6 in 12 of 12.

**What the surrogate says about the instrument (S1v2).** The registered estimator on the linear surrogate (full table under
Mechanism): in the identifiable regime every synthetic teacher reads as
intended in 6 of 6 families (constant-type teachers EPISODE_CONSTANT; first-order,
contextualised-key, RLS and fixed-preconditioner teachers TIE, except one
preconditioner family undecided; retrieval and value-directed teachers GAP; a
deliberately under-fitted C_f stopped by I0), and in wave 1's regime v1
reproduces the wave-1 failure while v2 never reads GAP. The identifiability
grid (seed 42, 2 families per cell, planted gates on the first-order cells):

| d_task (d90) | 16 fitting probes | 24 fitting probes | 32 fitting probes |
|---|---|---|---|
| 6 (5-6) | SPAN_VACUOUS, I3 fails | SPAN_VACUOUS, I3 fails | SPAN_VACUOUS, I3 fails |
| 8 (7) | SPAN_VACUOUS, I3 fails | SPAN_VACUOUS, I3 fails | SPAN_VACUOUS, I3 fails |
| 12 (10-11) | TIE / GAP but I2 fails | TIE / GAP, all gates pass | TIE / GAP, all gates pass |
| 16 (13-14) | capacity low or undecided, I2 fails | TIE / GAP, I2, I3, I6, I7 pass (I5 1/2) | TIE / GAP, I2, I3, I6, I7 pass (I5 0/2) |
| 24 (17-19) | capacity undecided, I2 fails | capacity undecided, I2 1/2 | TIE / GAP, I2, I3, I6, I7 pass (I5 1/2) |
| 32 (22-25) | capacity low, I2 fails | capacity undecided, I2 fails | capacity undecided, I2 fails |

"TIE / GAP" means the first-order teacher read TIE and the value-directed
teacher GAP in both families. I5 passes in every cell at d_task 12 and is
unreliable above it; it caps OPEN only. The window is a surrogate statement:
the real interface is 64-d, the read path is a 24-layer network and the loss is
KL, so d90 is measured on development reads before any oracle fit and selects
the branch.

**Multiplicity.** One decision path in a fixed order; secondaries (S_span_alone,
S_span_ctx, S_rand, site-1.0 ablation, argmax agreement and kappa,
permuted-target re-scoring, 2.7B disagreement) are reported with Holm
adjustment and change no decision.

**Leakage.** Fitting and scoring probes are disjoint within every episode
(lookup families: same names, different template). C_f and B use fitting probes
only; mu_k, the read subspace, learning rates, key sets and the planted gates
use only seed-42 episodes, which never enter a decision statistic. P and Q see
no task text. The resample state of an episode never uses that episode's
targets. The families are generated in the repository with per-episode random
mappings, so the teacher cannot have memorised an episode's answers.

**Missing data and infrastructure failures.** A job that fails for
infrastructure reasons is retried once from its checkpoint; the family table is
fixed before Step 1 (15 families built); nothing is dropped after Step 1 starts
except by the registered I0 and I1 rules, which are reported.

## Compute and Reproducibility

Pinned image (exists in the host's local registry; build 855, commit
`ed5d5a93`; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention
0.5.2, tilelang 0.1.13): `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`.
It contains no flash-attn, so the teacher is loaded through the Llama remap
with SDPA and cross-checked against fla 0.5.2 with a harness-side SDPA shim in
the smoke job; both paths are harness code, not model-generated code (D7).

Launch path (dry run, then test-only, then submit; each job one GPU):

```bash
# one manifest per job: smoke, step1, step2, step2-conditional (none written yet)
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v2-smoke.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v2-smoke.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v2-smoke.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`.
Every executable pilot also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for Step 0, `kind:
slurm-manifest` for the GPU jobs).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 8 (integer ceiling of the
summed caps, 7.72 GPU-h: smoke 0.17, Step 1 0.55, Step 2 5.5, conditional arm
1.5; D22 counts caps, not expected use, and the sum is below D20's 8 GPU-h line,
so D24 is not triggered).

**Arithmetic (S3v2, `compute/repair-d60/cost-model-v2.json`).** Method as wave 1:
FLOPs over MFU times the 989 TFLOP/s dense BF16 peak, a 1.25 factor, launch
overhead; central 25% MFU, high 12.5% MFU with 1.5x launch overhead; no
throughput has been measured for this workload. What changed:

- Prompt lengths are measured with the teacher's tokenizer on the built
  families (F1): zero-shot probes 7-13 tokens with BOS (mean 8.5), 8-shot
  prompts 71-125 (mean 85). Central 10/100 and high 16/140, against wave 1's
  assumed 12/200 and 24/400.
- Oracle steps run blocks 7-24 only: the first site is after block 6, so blocks
  1-6 are computed once per probe and cached (factor 0.75); I4 checks the
  cached path against the uncached one before the factor is used.
- 24 fitting probes per episode (x1.5 per fit) for the I1/I2 window.
- The design is re-counted at 347 episode-fit units per family (one unit =
  200 Adam steps over 24 probes of one episode): 3 decision classes x 32
  evaluation episodes, 2 secondary key sets x 16, the full-rank constant (400
  minibatch steps of 256 probes, 21.3 units), the B fit and key-set choice on
  14 development episodes (56), learning rates (18), I2/I3 plants (36), I5
  (32), I6 (8), I7 (16), restart sensitivity (24) and the site-1.0 ablation
  (8); 11 families (at most 10 ES plus 1 FF): 3,821 units.

| Job | Cap | Central | High | High, no prefix cache |
|---|---:|---:|---:|---:|
| Step 1 (15 families) | 0.55 | 0.08 | 0.21 | 0.21 |
| Step 2 main | 5.50 | 1.08 | 5.01 (4.12 after the ladder) | 6.61 (5.43 after the ladder) |
| Step 2 conditional | 1.50 | 0.32 | 1.40 | 1.84 (1.39 after its ladder) |

Reduction ladder for Step 2, in order: drop restart sensitivity; drop the
site-1.0 ablation; halve the evaluation secondaries; drop them. Conditional
ladder: S_ref and the in-sample ceiling to 8 episodes. With wave 1's
prompt-length assumptions the high case would not fit (Step 2 7.51 GPU-h with
the cache), which is why the lengths were measured rather than assumed. The
variance rule's 32 extra episodes per ES family fit at the central projection
(about +0.3 GPU-h) but not at the high one; they are drawn only if the
smoke-derived projection with them stays under the cap. If any projection
still exceeds a cap, the registration is not frozen and returns to the
gauntlet.

Checkpoints: per-episode state tensors and optimiser states every 10 minutes to
the persistent run directory, keyed by (family, seed, episode, class, restart),
so a fresh job resumes to identical outputs; a resume-equivalence test runs in
the smoke job. Artifacts: per-probe teacher (GOLD and SHUF) and student top-64
log-probabilities and KL, per-episode states, P/Q matrices, B, mu_k and the read
subspace with hashes, the decision record. Third-party data and the tokenizer
are fetched at run time pinned by revision and never committed.

**Repair reproduction (CPU).** From the worktree root:

```bash
cd program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/compute/repair-d60
# tokenizer.json: fetched from the teacher repository at revision d6f66f41 (sha256 fc4f0bd7...)
uv run --no-project --offline --with tokenizers==0.22.2 --with numpy python family-table.py tokenizer.json family-table.json
OMP_NUM_THREADS=1 ../../../../../../.venv/bin/python oracle-estimator-v2.py oracle-estimator-v2.json 7
OMP_NUM_THREADS=1 ../../../../../../.venv/bin/python oracle-estimator-v2.py oracle-estimator-v2-grid.json 5 --grid
python3 guard-sim.py guard-sim.json
../../../../../../.venv/bin/python decision-sim-v2.py decision-sim-v2.json
python3 cost-model-v2.py > cost-model-v2.json
```

All randomness is seeded from scenario keys; process count does not change
results.

## Safety, Data Rights, and Monitorability

- **Models.** fla-hub transformer 1.3B and 2.7B, MIT by card tag (first-party;
  no LICENSE file). Frozen; no weights are released.
- **Data.** All decision-bearing families are generated by repository code from
  hand-written word lists and seeded synthetic strings (MIT). FineWeb-Edu
  (ODC-By) is used only to fit P and Q and is never committed. No Function
  Vectors word lists (several ChatGPT-made), no MUSE (CC-BY-NC-4.0), no
  Super-NaturalInstructions, no CoNLL-2003 (asset cell).
- **Public repository.** No host addresses beyond the documented local registry
  name, no credentials, no private data; host paths in run artifacts are
  rewritten relative to the run root.
- **Host.** No host job of any kind while a Q2 S1a job (names s1a-* or
  q2s1a-*) is running or pending; the GPU work waits for a freeze (D58, D60).
  The D60 repair used no host access and no GPU.
- **Downloads in this repair.** The teacher's tokenizer files (about 1.8 MB,
  pinned revision, hash recorded) and the ACL Anthology bibliography with
  abstracts (42.5 MB, CC BY 4.0 metadata) were fetched to the scratch
  directory under D1 and are not committed; the 2.7 GB teacher checkpoint was
  not downloaded (an owner decision wave 1 left open). OpenReview's bot
  challenge was not bypassed.
- **Monitorability.** The gate trains no policy and produces no deployable
  system. States are tiny, inspectable tensors; every fit is logged with its
  KL trajectory.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| STOP_TEACHER | At 1.3B/100B tokens, label-dependent in-context learning is present on fewer than 4 of 10 built episode-specific families | D19 at this scale; a measured floor for D16 and any 1.3B fast-weight study (not set by the manifest: the table is built and checked first) |
| STOP_TR | On the families whose correct mapping changes between episodes, one state per family plus a per-episode label prior reproduces the teacher at this interface, and no episode's own state beats another's | Any write-rule question at this interface; says the 1.3B teacher's in-context behaviour on these families is task recognition and label calibration |
| INCONCLUSIVE_IDENTIFICATION | The state class can carry the behaviour in-sample but 24 probes cannot identify it | Nothing; sizes a successor's probe budget |
| STOP_INTERFACE_SIZE / _CLASS / STOP_LABEL_FREE_MAP | The 64-d rank-8 four-site interface (or residual-site states in general, or a label-free map) cannot carry the teacher's episode-specific behaviour | D19 as designed; D16's interface premise; tells a future port design which of size, site or map to change |
| STOP_SPAN | Everything episode-specific and probe-dependent the interface carries is expressible by writes whose read side lies in the span of the demonstrations' own reads | Step 3's free-versus-outer-product contrast, without training a rule; it does not say the teacher runs gradient descent (the class also holds Hebbian and linear-attention memories) |
| INCONCLUSIVE_SPAN | The paired noise, the number of capable families, or an I5/I6 failure leaves the span question open | Nothing; the per-family table and noise estimates size any successor |
| OPEN | Some episode-specific behaviour needs read directions outside the demonstrations' span, against preconditioned and differently contextualised gradient-form plants that read as ties | Licenses only a Step-3 gauntlet; pre-registered as not identifying a non-gradient rule (within-family retrieval predicts it) |

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex, the OpenReview search API and the ACL Anthology bibliography reachable from the Mac; wave 1's 159 and this run's 33 counted queries logged with returned ids and raw-output digests (`query-log.json`, `query-log-run2.json`); cutoff 2026-10-10; degraded coverage recorded (no Semantic Scholar, arXiv API, patents, social media, Chinese-language venues; OpenReview note pages behind a bot challenge; citation graph degraded) (`doctors/source.json`) | Semantic Scholar forward citations for the closest priors through the host relay when no S1a job runs |
| Citation | PASS | Claim registry C01 to C44 with locators, dates and read depth; every arXiv id snapshotted with HTTP 200 and version history; first-party, abstract-only and OpenReview-only claims labelled; the six priors wave 1 left uncited read in full and cited (`doctors/citation.json`) | Open the bodies of the ICLR 2027 submissions (C41) once the OpenReview challenge can be passed by a person |
| Novelty | FAIL | NARROWED: no direct prior under the recorded coverage; the confined-versus-free contrast exists in KV compaction (C34, C35) and the class in the dual-form line (C31, C32), so the key-span component's confidence is lowered to medium-low; blind packets prepared for Attention Matching with Cartridges, the dual form and 2608.13385 (`doctors/novelty.json`) | Run one blind critic per packet and the novelty refuter of this run |
| Design | FAIL | The registered estimator is code (S1v2) and gives the intended verdicts for all twelve synthetic teachers in the identifiable window, I0 catches a deliberate constant misfit, the wave-1 regime is reproduced and repaired, G1 and S2v2 size the guard and the decision path; but every noise SD is assumed, I5 fails in the surrogate, the window for I1 and I2 is a surrogate statement, and nothing has run on the teacher's residuals (`doctors/design.json`) | Build the Step-0 harness; measure d90, the paired SDs and I5 on real residuals before the freeze |
| Compute | FAIL | No real model loop for this gate, no benchmark adapter, no container smoke, no Slurm dry run, no manifest; the pinned image cannot instantiate the fla teacher without a shim (`doctors/compute.json`, `compute/attestations-not-run.md`); caps re-derived (7.72 GPU-h, under 8) from measured prompt lengths | Write the harness and the smoke manifest; dry run and test-only when no S1a job runs |
| Safety | PASS | Synthetic in-repository data, FineWeb-Edu ODC-By for P only, MIT checkpoints, no deployable system, host rule respected, public-repository hygiene, no bot challenge bypassed (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts); Design, the vendored K-Dense
`experimental-design` and `statistical-power` skills (design before data, seed
blocking, decisiveness by simulation); Evaluation, K-Dense
`statistical-analysis`; Novelty, K-Dense `literature-review` (PRISMA counts).
Integrity gate (the seven failure modes) is answered in the registration's
integrity section.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviewer 1, claude-opus-5-5, scored 55 and is recorded in the gauntlet file)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only while no Q2 S1a job is running or pending; wave 1's reviewer 2, qwen3.6-35b-a3b, scored 49)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

This run's reviewers have not scored. Wave 1's scores (reviewer 1 / reviewer 2)
are in the gauntlet record and in the iteration log below; they scored the
wave-1 package, not this one.

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (wave 1: 7 / 8) |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1: 6 / 6); registry now C01 to C44 |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1: 5 / 4); uncited priors read and differentiated |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1: 5 / 4); P1 to P6 with falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1: 4 / 4); registered estimator now code, S1v2 |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1: 5 / 5); G1 and S2v2 |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1: 4 / 3); family table built, caps 7.72 GPU-h |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1: 5 / 2); no harness, no manifest |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1: 9 / 9) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1: 5 / 4); no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy 1-5 (D19, 2026-09-01) | 62, 57, 65, 65 (lower reviewer; wave 1 killed before judging) | Wave 5: the w-clamp co-condition passes under the gradient-form null; positive control is prior memorisation; nothing executable on a model | Exit 5 (under two points of gain across three waves) | Recorded in `legacy/research/gauntlet/2026-09-01-frontier/` |
| new gauntlet, synthesis (2026-10-10) | not scored | KILL A makes the dossier's Step-2 tie rule fire by construction | Gate rescoped to Steps 1-2; full-rank port map; key-span class with shared map B; family-constant floor; planted recovery and non-vacuity gates; S1, S2, S3 | Went to wave 1 |
| 1 (2026-10-10) | 49 (55 / 49) | Identification: S1 did not implement the registered estimator; under it a constant teacher passed the guard and gradient-form teachers read GAP; label-prior and contextualised-key false GAPs; runner-up feasibility (family table not buildable, K2 set by the manifest, I1/I2 window) | Honest exit (query budget 159 of 150; triad 3 of 3 refuted); D60: one repair and a fresh run | Recorded, row hash `b658a265...` |
| D60 repair (2026-10-10) | not scored | as wave 1 | Registration v2: the estimator as code (S1v2), full-rank constant with per-episode nuisance shifts, per-episode shift floor, centred reads, alone and in-context keys, decision-bearing placebo, label-prior guard, I0 and I5-I7, family table under the real tokenizer, K2 relative, 24 fitting probes, pooled STOP_SPAN, caps 7.72; novelty coverage of OpenReview and the ACL Anthology | Awaiting this run's blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e4-icl-write-rule-gate.md` (exit 1) on the bundle
as committed, also stored as
`evidence/2026-10-10-e4-icl-write-rule-gate/doctors/research-direction-doctor-output.json`.
Readings the doctor does not make for itself: "all declared budgets must be
positive" comes from parsing the declared `gpu_hours=0.3` as 0 (the declared
budget is honest and not rounded up to pass); and the doctor applies only the
89 cap, while by the gauntlet rule's cap table this proposal is also capped at
74 until this run's blind critic and novelty refuter have run (Novelty doctor
FAIL) and at 79 (no executable pilot), and it cannot reach 100 without D24's
trust store.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "FAIL",
    "Novelty": "FAIL",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "all declared budgets must be positive",
    "Novelty doctor lacks PASS plus concrete evidence",
    "Design doctor lacks PASS plus concrete evidence",
    "Compute doctor lacks PASS plus concrete evidence",
    "Reviewer A lacks structured PASS attestation",
    "Reviewer B lacks structured PASS attestation",
    "evidence bundle requires exactly two review artifacts",
    "protected external trust store is not configured; set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI",
    "reviewers must use different providers; degraded review cannot score 100",
    "reviewers must have distinct nonempty run IDs",
    "two distinct trusted reviewer signatures are required for 100",
    "compute attestation says the real model loop is not executable",
    "compute attestation lacks a non-stub benchmark adapter",
    "compute benchmark_adapter path does not exist",
    "repository real model loop is still a stub",
    "compute lacks a hashed Slurm manifest",
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 3 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-e4/program/proposals/2026-10-10-e4-icl-write-rule-gate.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 46,
    "recognizedPrimaryUrls": 46
  },
  "status": "FAIL"
}
```
