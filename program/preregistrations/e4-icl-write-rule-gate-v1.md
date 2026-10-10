# E4 gate v1: teacher eligibility, oracle interface ceiling and key-span sufficiency (e4-icl-write-rule-gate-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the E4 research gauntlet (D58) on branch
`gauntlet/e4-d19`. It registers only the E4 gate (dossier Steps 1 and 2).
Step 3 (rule against rule), the port, the cross-lingual stage and the
replication are not registered here and need their own gauntlet. Its design
decisions (1 to 30 at the end) need the program owner's acceptance. Its caps
sum to 6.42 GPU-h, below D20's 8 GPU-h line, so admission does not need D24's
trust store, but D58 makes the GPU work wait for a scored, reviewed package
and a freeze, and no host job of any kind runs before Q2 S1a's session 2 has
ended. The gauntlet proposal that argues and attacks this design is
`program/proposals/2026-10-10-e4-icl-write-rule-gate.md`; its evidence bundle
is `program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/`.

## Relation to the legacy D19 contract and the dossier

- The legacy contract `legacy/experiments/architectures/icl-rule-distillation-port.yaml`
  and its phase-0 CPU doctor (orx node on
  `orx/d19-icl-rule-distillation-port-phase-0-cpu-docto`, commit `bc05cc4`,
  run `e20eeccb-8c51-42de-891b-007e52282bf4`, PHASE0_DOCTOR_PASS 66/66 on a
  synthetic regime) are not reused. The doctor tests none of the gate's
  quantities, and its positive control is prior memorisation (legacy wave-5
  reviewers). It is not edited (hard rule 3); this is a new experiment id.
- The dossier's Step 2 compared a free per-episode state with a state limited
  to the span of the 8 keys at D16's interface, whose port maps are rank-8
  factorised. There the two classes give identical reads for any teacher
  (KILL A; replicated in the bundle's `compute/oracle-class-semantics.json`).
  This registration uses a full-rank 64-d port map and a pre-registered
  non-vacuity gate (I1).
- The dossier's kill criteria are kept and made quantitative: "fewer than 8
  families whose gold-minus-shuffled gap clears its CI (including at least 4
  function-induction families)" is K2 with "function-induction" replaced by
  "episode-specific" (decision 6); "the free oracle cannot reach meaningful
  fidelity" is the capacity rule with E_free at least 0.50; "the free and
  key-span oracles tie" is STOP_SPAN with a 0.05 equivalence margin.

## Question

For the frozen teacher `transformer-1.3B-100B`: (1) on how many of 14
synthetic task families does it show label-dependent in-context learning, and
on how many of those does the correct mapping change across episodes; (2) can a
per-episode rank-8 state at a fixed four-site 64-d residual interface, fitted
to the teacher's own eight-shot predictions, carry at least half of the
episode-specific divergence a family-constant state leaves, on held-out probes;
(3) does restricting the episode-specific part of that state to the span of the
demonstrations' keys after one shared linear map lose at least 0.10 of that
divergence?

Claim scope: a prerequisite measurement on one frozen teacher. No learning-rule,
gradient-descent, portability or architecture claim is licensed by any outcome.

## Identity

- Experiment id: `e4-icl-write-rule-gate-v1`.
- Teacher: `fla-hub/transformer-1.3B-100B`, revision
  `d6f66f4181fa669e5863327815b44533e3a395e7` (registry id
  `transformer-1.3b-100b`, receipt on the host, MIT card tag). Secondary:
  `fla-hub/transformer-2.7B-100B`, revision
  `e29b06c913e05827bfb534844267c8d9f673feda` (registry id
  `transformer-2.7b-100b`, receipt to be fetched in Step 0b).
- P-fit corpus: `HuggingFaceFW/fineweb-edu`, `sample-10BT`, revision pinned as
  a 40-hex sha at manifest build (the asset cell read `87f09149...`), 2,000
  documents of at least 512 tokens selected by a seeded hash, ODC-By.
- Image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (build 855, commit `ed5d5a93`).
- Code: the Step-0 harness (`harness/e4_gate.py`, `scripts/run_e4_gate_doctor.py`,
  `scripts/run_e4_gate.py`; none written yet) at the commit recorded in the
  freeze.
- Seeds: demonstration seeds [42, 43, 44] (seed 45 only under the
  variance rule); oracle initialisation seed 42; restarts 43 and 44.

## Families (generated in the repository)

Every family is a generator with a fixed template `input: X\noutput: Y\n`
repeated 8 times, then `input: Xq\noutput:`; the answer is the next token.
Word lists are written by hand in the repository; nonce names and symbols come
from seeded syllable generators. Answers must be single tokens under the
teacher's tokenizer; items that are not are filtered at manifest build, and a
family left with fewer than 40 usable inputs is dropped before Step 1 and
listed.

| Class | Id | Mapping | Varies by episode |
|---|---|---|---|
| fixed function (FF) | F1 | lowercase word to capitalised word | no |
| FF | F2 | letter to next letter | no |
| FF | F3 | digit 1-9 to digit minus one | no |
| FF | F4 | word to its first letter | no |
| FF | F5 | regular singular noun to plural | no |
| latent parameter (LP) | L1 | letter to letter shifted by k, k in {1,2,3,4} | k |
| LP | L2 | digit to (digit + k) mod 10, k in {1,2,3,4,6,7,8,9} | k |
| LP | L3 | list of three words to the word at position p, p in {1,2,3} | p |
| LP | L4 | word to its i-th letter, i in {1,2,3} | i |
| LP | L5 | weekday to the weekday k days later, k in {1,2,3} | k |
| lookup and abstract label (LA) | A1 | nonce name to two-digit number, a fresh binding per episode; probes are the 8 bound names under the demonstration template and, in Step 2, also under `the number of Xq is` and `Xq has the number` | binding |
| LA | A2 | nonce word to colour word, fresh binding per episode, probe templates as A1 (with `colour`) | binding |
| LA | A3 | animal or tool word to one of two symbols, symbol pair and assignment drawn per episode | labels |
| LA | A4 | animal, tool, colour or number word to one of the letters A-D, permuted per episode | labels |

Episode-specific (ES) families are LP and LA (9). Queries are disjoint from the
episode's demonstration inputs except in A1 and A2, where they are the bound
names by construction.

## Conditions and Step 1 (eligibility)

Per family and demonstration seed s, 25 episodes of 8 demonstrations and 16
queries (PCG64 keyed by family, s, episode).

- GOLD: the demonstrations with their correct outputs.
- SHUF: the same inputs in the same order with outputs permuted by a seeded
  derangement (for A3 and A4: the labels re-drawn uniformly, as in Min et al.).
  The fraction of SHUF demonstrations still correct by chance is logged.
- ZS: the query template alone.

Score: argmax over the full vocabulary at the answer position equals the gold
answer token. Per family, G_LD = mean over s of (accuracy GOLD minus accuracy
SHUF) on 1,200 query instances per condition; G_ZS = accuracy GOLD minus
accuracy ZS. Cluster-t statistic on episode-level differences (75 clusters,
df 74), one-sided p-value; Holm over the 14 families at one-sided 0.05.

A family is **eligible** if G_LD is at least 0.10, its Holm-adjusted test
rejects, and G_ZS is at least 0.05.

Secondary: 2.7B GOLD accuracy and the fraction of queries where the 1.3B and
2.7B argmax differ, per family (relevant only to a later sibling control).

## Step 2 (oracle interface ceiling and key-span sufficiency)

Runs on every eligible ES family and on at most 2 eligible FF families (in the
order F1 to F5). Per family: the first 16 Step-1 episodes of each seed (48).
Each keeps its 16 Step-1 queries as fitting probes and gets 8 new scoring
queries, drawn at manifest build with inputs disjoint from the episode's
demonstrations and fitting queries (A1 and A2: the 8 bound names under
templates one and two for fitting and template three, `Xq has the number`, for
scoring). Targets: the teacher's GOLD next-token distributions at the answer
position, recomputed in Step 2.

**Interface.** Sites after blocks 6, 12, 18, 24. At each site: W_k = ZCA
whitening of the site's residuals over 131,072 FineWeb-Edu positions (ridge
1e-4 times the mean eigenvalue); Δh = h(full prefix) minus h(the last 16
tokens only) at 64 seeded positions at or after token 128 of each of the 2,000
documents; V_k = top 64 right singular vectors of W_k Δh; P_k = V_k^T W_k,
Q_k = W_k^-1 V_k. Width-256 reference: the top 256. The read is affine:
x = [P_k h; 1]. Keys k_i = [P_k h_k(x_i); 1] at the answer position of
template(x_i) encoded alone; K_e = [k_1 ... k_8] (65 x 8). Student: zero-shot
probe prompt, each site's residual at every probe position replaced by
h + Q_k M_k x, with M_k 64 x 65.

**Classes.** S0 (M = 0); S_rand (random state with the rank and Frobenius norm
of the episode's S_free state, seed 42); S_resample (the S_free state of
episode e+1 of the same family and seed, cyclic); S_const (C_f, rank 8,
fitted on the first 4 fitting probes of each of the family's 48 episodes);
S_spanB (C_f frozen plus U_e (B_k K_e)^T, U_e 64 x 8, B_k = diag(B_64, 1) so
the constant coordinate is not preconditioned); S_spanI (B = I); S_free (C_f
frozen plus A_e G_e^T, A_e 64 x 8 and G_e 65 x 8); S_ref (width 256: rank-16
constant plus rank-16 free episode part; 16 evaluation episodes per family).

**Fitting.** Adam, 200 steps, full-batch over the 16 fitting probes (batched
across episodes), loss = sum of KL(p_T || p_student) over fitting probes;
learning rate per class from {1e-2, 3e-2, 1e-1}, chosen on 2 seed-42
development episodes per family by held-out KL and then fixed. S_spanB and
S_spanI are parametrised as U'_e O_e^T with O_e an orthonormal basis of
span(B_k K_e) (QR), so their conditioning does not depend on the keys' Gram
matrix; U'_e starts at zero. S_free starts with A_e = 0 and G_e a seeded random
orthonormal matrix (LoRA-style), so it has no knowledge of the keys. Every
class therefore starts at C_f;
B_64 initialised at I and fitted jointly with the U_e of the 14 other seed-42
development episodes per family (all but the 2 learning-rate episodes) over 400
steps with an L2 penalty on B_64 - I (weight 1e-2
times the mean diagonal curvature), then frozen. Per family, the
decision-bearing span class uses B_64 or I, whichever gives the lower held-out
KL on that family's development episodes; the choice is frozen before any
evaluation statistic. A poorly estimated B can otherwise make the span class
worse than B = I and manufacture a gap (simulation S1). Norm cap: after each step, if
the largest ratio over fitting probes of |Q_k M_k x| to the site's median
natural shift |h_8shot - h_0shot| (median over the family's fitting probes)
exceeds 2, M_k's episode part is rescaled to bring it to 2. The cap-binding
rate is reported.

**Quantities** (per family, over its 32 evaluation episodes = seeds 43 and 44):

- KL_X(e) = sum over the episode's 8 scoring probes of KL(p_T || p_X).
- R_X = 1 - sum_e KL_X(e) / sum_e KL_S0(e).
- E_X = 1 - sum_e KL_X(e) / sum_e KL_const(e).
- D_span(e) = [KL_spanB(e) - KL_free(e)] / mean_e KL_const(e); D_span is its
  episode mean (equal to E_free - E_spanB).
- Guard: E and D_span are computed only for a family with sum_e KL_const(e) /
  sum_e KL_S0(e) at least 0.20; a family below it is EPISODE_CONSTANT and is
  excluded from the capacity and span counts (reported).
- Per-family one-sided 95% bounds: t over the 32 episodes (df 31) of the
  episode-level terms; an episode bootstrap (2,000 resamples, seed 42) is the
  sensitivity.
- D_span can be negative: scored on held-out probes, the key-span class has the
  demonstrations' keys as a prior that the free class lacks, so it can
  generalise better from 16 fitting probes. A negative D_span counts toward
  TIE. The opposite error (an out-of-span behaviour the free class cannot
  identify from 16 probes, read as TIE) is what gate I3 guards against.

**Variance rule (fixed now).** If the pooled within-family SD of the
episode-level D_span terms on the learning-rate development episodes (2 per
family, at the selected rates) exceeds 0.10,
32 more evaluation episodes per ES family are drawn with demonstration seed 45
before any seed-43/44 statistic is computed, provided the smoke-derived
projection with them stays under the Step-2 cap after the reduction ladder;
otherwise they are not drawn and this is reported. The rule uses the SD only.

## Instrument gates (run before any capacity or span statistic is read)

- **I1 non-vacuity.** Over the evaluation episodes of the eligible ES families
  other than A1 and A2 (whose probes are the demonstrated names by
  construction), the median of the fraction of the
  energy of the 64-d part of the scoring-probe read, |P_k h(q)|^2, that lies
  outside the span of the keys' 64-d parts, and outside the span of B_64 times
  them, is at least 0.50 at every site.
- **I2 planted recovery.** Per family, 2 development episodes x 2 planted
  types (a rank-8 free episode part whose read directions G are drawn uniformly
  from the subspace holding 90% of the energy of the family's development
  probe reads, and whose write directions A are random; a random episode part
  in the span of B_k K_e, drawn after B is frozen), each added to C_f with
  Frobenius norm
  set to the median fitted S_free episode-part norm on development episodes;
  targets are the frozen model's outputs under C_f plus the planted part;
  fitted from C_f by the class that contains the planted part, best of 3
  restarts (seeds 42, 43, 44) by fitting loss. Recovery = 1 - KL(planted ||
  fitted) / KL(planted || C_f only), summed over scoring probes. Pass: recovery
  at least 0.90 in at least 90% of planted episodes.
- **I3 span discrimination.** On the same planted episodes, with D_span^pl =
  [KL(planted || S_spanB fit) - KL(planted || S_free fit)] / KL(planted || C_f
  only): planted free parts give D_span^pl at least 0.30, planted key-span parts
  give at most 0.03, each in at least 90% of planted episodes.
- **I5 preconditioned writer.** A shared random B* (64 x 64, condition number
  10, seed 42) and episode parts U (B* K_e)^T are planted on 4 development
  episodes per family; B is refitted on them by the registered procedure and
  scored on 2 further planted development episodes per family. Pass: D_span^pl
  at most 0.05 in at least 90% of the scored episodes. A failure does not stop
  the gate; it caps the span verdict at INCONCLUSIVE_SPAN instead of OPEN,
  because a gap could then be a fixed-preconditioner writer the B fit did not
  recover (simulation S1 shows exactly this failure in the surrogate).
- **I4 code-path checks.** M = 0 reproduces the unmodified model's logits
  exactly; the scoring probes never enter any fit (hash audit); the
  resample state of an episode never uses that episode's targets.

Any failure of I1 to I4 is **INSTRUMENT_FAIL**: no capacity or span verdict;
the repair is a new experiment id. The effective dimension of the probe reads
(components holding 90% of their energy) is reported per family and site; if
it exceeds 16, 16 fitting probes cannot identify a free per-episode state, and
I2 is expected to fail.

## Decision rules

Evaluated in this order; the first verdict reached is final.

1. **INFRA_FAIL** if the smoke fails (below) or a job fails twice for
   infrastructure reasons.
2. **STOP_TEACHER (K2)** if fewer than 8 families are eligible or fewer than 4
   ES families are eligible.
3. **INSTRUMENT_FAIL** if any of I1 to I4 fails.
3b. **STOP_TR** if fewer than 4 eligible ES families pass the guard (are not
   EPISODE_CONSTANT): the teacher's in-context behaviour at this interface is
   one state per family. n_ES below counts only families that pass the guard.
4. **Capacity** on the n_ES eligible, guarded ES families. Per family: CAP_OK if the
   one-sided 95% lower bound of E_free is at least 0.50; CAP_LOW if the upper
   bound is below 0.50.
   - CAPACITY_PASS if CAP_OK in at least ceil(0.75 n_ES) families.
   - Otherwise, if CAP_LOW in at least ceil(0.5 n_ES) families, the
     conditional supervised-map arm runs on the CAP_LOW families (P_k, Q_k
     initialised at the label-free maps and trained by teacher KL jointly with
     episode states on 8 seed-42 episodes of each of up to 8 other eligible
     families for 400 steps, then frozen; S_const and S_free refitted on the
     CAP_LOW families' evaluation episodes).
     **STOP_LABEL_FREE_MAP** if it makes at least half of those families
     CAP_OK; else **STOP_INTERFACE_SIZE** if S_ref's E (episode-specific, on
     its 16 episodes) has a lower bound of at least 0.50 in at least half of
     them; else **STOP_INTERFACE_CLASS**.
   - Otherwise **INCONCLUSIVE_CAPACITY**.
5. **Span** on the n_ok CAP_OK ES families (only after CAPACITY_PASS). Per
   family: TIE if the one-sided 95% upper bound of D_span is at most 0.05; GAP
   if D_span is at least 0.10 and its one-sided 95% lower bound exceeds 0.02.
   - **STOP_SPAN** if n_ok is at least 3 and TIE holds in at least
     ceil(0.75 n_ok) families.
   - **OPEN** if GAP holds in at least max(2, ceil(0.5 n_ok)) families,
     every lookup family (A1, A2) among the n_ok families has D_span at most
     0.05 (a lookup family's probes are its demonstrated names, so key-span
     states can read them; a gap there would point at the instrument), and I5
     passed.
   - Otherwise **INCONCLUSIVE_SPAN**.

OPEN licenses only a Step-3 gauntlet. It is pre-registered as not identifying
a non-gradient learning rule: within-family retrieval among stored functions
predicts it.

## Reported regardless of outcome

Per family: G_LD, G_ZS, accuracies in every condition, the SHUF chance-correct
fraction, eligibility; R and E for every class; D_span(B), D_span(I); placebo
floors; argmax agreement with the teacher overall and on teacher-wrong queries;
chance-corrected agreement (Cohen's kappa over argmax tokens); permuted-target
re-scored R (eval targets permuted across the episode's scoring probes, no
refit); site-1.0 ablation (S_free without the last site, 8 episodes); S_free on
SHUF targets (16 episodes) with its own constant; cap-binding rate; injected
norm ratios; restart spread (4 episodes x restarts 43, 44); I1 to I5 values;
the probe reads' effective dimension per family and site; which B (fitted or
I) each family uses;
the 2.7B disagreement rate; per-class summaries (FF, LP, LA). All per-probe
tables are released in the bundle.

## Seeds, sample sizes and simulation

Simulation S2 (`compute/decision-sim.py` and `.json` in the proposal bundle,
4,000 replicates per scenario, design seed 42; every noise SD assumed):

- eligibility: P(eligible) is 0 at a true gap of 0, 0.98 to 1.00 at 0.15, and
  0.25 to 0.50 at 0.10;
- capacity (family SD 0.10): P(CAPACITY_PASS) at least 0.99 at a true mean
  E_free of 0.75, 0.43 to 0.66 at 0.60, at most 0.02 at 0.45;
- span: false OPEN under a true tie at most 0.012; false STOP_SPAN under a
  true shortfall of 0.10 at most 0.004; P(OPEN) 0.52 to 0.68 at a true
  shortfall of 0.10 and at least 0.99 at 0.20; P(STOP_SPAN | true tie) 0.997,
  0.88, 0.17 at paired episode SD 0.05, 0.10, 0.20 with homogeneous families
  (4 families), lower with family heterogeneity, which is why the variance
  rule exists.

Simulation S1 (`compute/oracle-class-semantics.py` and `.json`, linear
surrogate, 32-d interface, seeds 42/43/44): at the legacy rank-8 port, probe
reads have no energy outside the key span and D_span is 0.0000 for all seven
synthetic teachers, including retrieval and value-directed writers (KILL A).
At a full-rank port, D_span(B) is -0.29 to -0.16 for first-order and
recursive-least-squares writers (TIE), 0.001 for lookup, 0.57 to 0.65 for
retrieval and 0.78 to 1.21 for value-directed writers (GAP); a
family-constant teacher is EPISODE_CONSTANT. A fixed-preconditioner writer
reads as a gap (0.68 to 0.82) because the B fit did not recover B* from 6
development episodes (I5 exists for this). Neither simulation is evidence
about the teacher.

## Smoke (at most 0.17 GPU-h, one GPU)

Load the teacher two ways: weights remapped to transformers'
`LlamaForCausalLM` with SDPA, and fla 0.5.2's `TransformerForCausalLM` with a
harness-side SDPA replacement for its flash-attention call. Pass: top-1
agreement at least 0.999 and largest absolute logit difference at most 0.05
(bf16) on 64 FineWeb-Edu sequences of 512 tokens not used for P; mean
FineWeb-Edu loss at most 3.5 nats per token (a broken load gives about
ln 32000 = 10.4); a 4-episode oracle fit is resumed from a mid-run checkpoint in
a fresh process and matches the uninterrupted run to 1e-6 in fp32 states;
measured throughput projects every step under its cap, after the reduction
ladder if needed. Otherwise INFRA_FAIL or not frozen.

## Compute

| Job | Cap (GPU-h) | Central estimate |
|---|---:|---:|
| smoke | 0.17 | 0.17 |
| Step 1 (14 families, 1.3B GOLD, SHUF, ZS; 2.7B GOLD) | 0.75 | 0.10 |
| Step 2 main (at most 11 families) | 4.00 | 0.91 |
| Step 2 supervised-map arm (conditional) | 1.50 | 0.20 |
| **Sum of caps (D22)** | **6.42** | |

Reduction ladder if the smoke projects Step 2 over its cap, in order: drop SHUF
targets; drop restart sensitivity; drop the site-1.0 ablation; halve S_ref to 8
episodes. If still over, not frozen. One GPU per job, Docker lane through
`scripts/submit_docker_research_job.py` (dry run, test-only, submit),
checkpoints every 10 minutes to the persistent run directory, fresh-job resume.
The gauntlet's 0.3 GPU-h (reviewer inference) is separate.

## Infrastructure failures and exclusions

A job that fails for infrastructure reasons (node, container, OOM, preemption)
is resumed once from its checkpoint; a second failure is INFRA_FAIL. No
family, episode or probe is excluded after Step 1 starts, except a probe whose
teacher target is non-finite, which is logged and counted.

## Data rights

Repository-generated families (MIT). FineWeb-Edu (ODC-By 1.0) fetched at run
time, pinned by revision, used only for P and Q, never committed. fla-hub
checkpoints MIT by card tag (first-party; no LICENSE file). No third-party task
data. Per-probe tables contain only repository-generated strings and model
outputs on them.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: I2 to I4 run on real residuals
   before any reading; the Step-0 harness is tested on a random-init model
   with planted states; M = 0 identity check.
2. Hallucinated citation: every cited id is snapshotted with HTTP 200 in the
   bundle; claims C01 to C30 carry locators.
3. Hallucinated result: the gate has no result yet; every number in the
   proposal is from a simulation or a source and is labelled as such.
4. Shortcut reliance: held-out probes, family-constant floor, norm cap,
   site-1.0 ablation, permuted-target re-scoring.
5. Bug reframed as insight: a lookup family failing span sufficiency blocks
   OPEN instead of being read as a finding; I1 to I3 failures stop the gate.
6. Methodology fabrication: thresholds are fixed here with their simulation;
   the variance rule reads only an SD from development episodes.
7. Frame-lock: the gate can end at eleven verdicts; six are scientific stops
   that close the line (STOP_TEACHER, STOP_TR, STOP_LABEL_FREE_MAP,
   STOP_INTERFACE_SIZE, STOP_INTERFACE_CLASS, STOP_SPAN), and OPEN is
   pre-registered as not identifying the mechanism.

## Freeze procedure

After Step 0 (harness, tests, CPU doctor as an orx `cpu-doctor` node), the
smoke, a reviewed gauntlet package and the owner's acceptance of decisions 1
to 30: `uv run python scripts/preregister.py freeze e4-icl-write-rule-gate-v1
program/preregistrations/e4-icl-write-rule-gate-v1.md`, then verify, and
record the freeze commit in every manifest.

## Design decisions (for the owner's acceptance)

1. Only Steps 1 and 2 are registered; Step 3 and the port need new gauntlets.
2. New experiment id; the legacy contract and doctor are not edited.
3. Full-rank 64-d port map instead of D16's rank-8 factorised map (KILL A);
   the result no longer tests D16's interface directly.
4. Label-free P from context-change principal directions of whitened residuals
   on FineWeb-Edu, not variance principal directions.
5. Sites after blocks 6, 12, 18, 24 (legacy depths), with a site-1.0
   ablation as a secondary.
6. K2's "at least 4 function-induction families" becomes "at least 4
   episode-specific families" (fixed-function families pass through task
   recognition).
7. 14 repository-generated families in three classes; no third-party task
   data.
8. Eligibility threshold G_LD at least 0.10 with Holm over 14 and G_ZS at least
   0.05.
9. 3 demonstration seeds x 25 episodes x 16 queries per family in Step 1.
10. 2.7B disagreement is secondary and needs a fetch; never decision-bearing.
11. Step 2 on all eligible ES families plus at most 2 FF families; 24 queries
    per Step-2 episode (16 fitting, 8 scoring); affine read with a constant
    coordinate.
12. Seed 42 episodes are development (B, learning rates, variance rule);
    seeds 43 and 44 are evaluation.
13. Oracle classes S0, S_rand, S_resample, S_const, S_spanB, S_spanI, S_free,
    S_ref as defined.
14. The decision-bearing restricted class is span(B K_e) with B shared,
    fitted with a penalty toward I, and chosen per family between the fitted B
    and I on development episodes; D_span(I) is also reported.
15. KL over the full vocabulary as the fitting and scoring loss; recovered
    fractions as ratios of sums.
16. Episode-specific recovered fraction E relative to the family constant as
    the capacity metric, defined only above the 0.20 guard; STOP_TR when fewer
    than 4 eligible ES families pass the guard.
17. Capacity threshold E_free at least 0.50 (one-sided 95% lower bound per
    family) and the 75% count rule.
18. Capacity disambiguation by S_ref and a conditional supervised-map arm.
19. Span TIE margin 0.05 and GAP threshold 0.10 with lower bound above 0.02.
20. Family-count aggregation, not pooled intervals.
21. Variance rule with demonstration seed 45.
22. Instrument gates I1 to I4 with the thresholds above; I5 as a cap on OPEN;
    planted free states drawn in the probe-read subspace.
23. Lookup families as a guard on OPEN.
24. Norm cap at twice the median natural in-context shift.
25. 200 Adam steps, per-class learning-rate grid on development episodes.
26. Smoke criteria and the teacher loading by Llama remap cross-checked with
    an fla shim.
27. Caps 0.17, 0.75, 4.0, 1.5 GPU-h and the reduction ladder.
28. OPEN pre-registered as not identifying a non-gradient rule.
29. All per-probe tables released.
30. No host job before S1a's session 2 ends; no GPU job before a freeze.
