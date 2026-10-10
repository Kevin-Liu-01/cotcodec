# E4 gate v2: teacher eligibility, oracle interface ceiling and key-span sufficiency (e4-icl-write-rule-gate-v2)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single owner of the E4 repair under program decision D60, on branch
`gauntlet/e4-d19`, as a new versioned attempt (gauntlet rule 3): the wave-1
draft `e4-icl-write-rule-gate-v1.md` (sha256 `4cef1c1c...`) is left as it was
and is superseded by this file. Wave 1 of the E4 gauntlet scored 49 (reviews 55
and 49), and all three refuters refuted
(`program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl`). This draft repairs
the defects that wave named; the section "Repair under D60" at the end lists
every change and the CPU check that sizes it. It registers only the E4 gate
(dossier Steps 1 and 2). Its design decisions (31 to 63 at the end, with 1 to 30
of v1 where not amended) need the program owner's acceptance. Its caps sum to
7.72 GPU-h, below D20's 8 GPU-h line, so admission does not need D24's trust
store; D58 still makes the GPU work wait for a scored, reviewed package and a
freeze, and no host job of any kind runs while a Q2 S1a job is running or
pending. The gauntlet proposal that argues and attacks this design is
`program/proposals/2026-10-10-e4-icl-write-rule-gate.md`; its evidence bundle
is `program/proposals/evidence/2026-10-10-e4-icl-write-rule-gate/` (the repair's
checks are under `compute/repair-d60/`).

## Relation to v1, the legacy D19 contract and the dossier

- Everything v1 said about the legacy contract, its phase-0 doctor and KILL A
  still holds: the legacy rank-8 port makes the span constraint vacuous, so the
  port map is full rank (64-d) and a non-vacuity gate (I1) runs first.
- v2 changes the estimator (family constant, per-episode shift, centred reads,
  key sets, placebo and guard), the family table, the number of fitting probes,
  the instrument gates, the decision rules and the caps. It keeps the teacher,
  the interface sites, the label-free port map, the state ranks, the KL
  objective, the seeds and the claim scope.

## Question

For the frozen teacher `transformer-1.3B-100B`: (1) on how many of 15
synthetic task families (10 whose correct mapping changes from episode to
episode) does it show label-dependent in-context learning; (2) on how many of
those is its eight-shot behaviour episode-specific beyond a per-episode label
prior, that is, carried by an episode's own state better than by another
episode's; (3) can a per-episode rank-8 state at a fixed four-site 64-d
residual interface, fitted to the teacher's own eight-shot predictions, carry
at least half of that episode-specific, probe-dependent divergence on held-out
probes; (4) does confining the read side of that state to the span of the
demonstrations' own interface reads, after one shared linear map, lose at
least 0.10 of it?

Claim scope: a prerequisite measurement on one frozen teacher. No
learning-rule, gradient-descent, portability or architecture claim is licensed
by any outcome. In particular the key-span class contains every write whose
read side is an outer product with a (mapped) demonstration read: first-order,
preconditioned and recursive-least-squares updates, but also Hebbian and
linear-attention memories with free values. STOP_SPAN therefore says that this
interface cannot separate any such write from an unconstrained one, not that
the teacher runs gradient descent.

## Identity

- Experiment id: `e4-icl-write-rule-gate-v2`.
- Teacher: `fla-hub/transformer-1.3B-100B`, revision
  `d6f66f4181fa669e5863327815b44533e3a395e7` (registry id
  `transformer-1.3b-100b`, receipt on the host, MIT card tag). Tokenizer:
  `tokenizer.json` at that revision, sha256
  `fc4f0bd70b3709312d9d1d9e5ba674794b6bc5abc17429897a540f93882f25fc`
  (refetched at the pinned revision and hashed on 2026-10-10; 32,000-token
  BPE, normaliser prepends "▁", no pre-tokenizer, single digits only, "▁" = 28705).
  Secondary: `fla-hub/transformer-2.7B-100B`, revision
  `e29b06c913e05827bfb534844267c8d9f673feda` (receipt to be fetched in Step 0b).
- P-fit corpus: `HuggingFaceFW/fineweb-edu`, `sample-10BT`, revision pinned as
  a 40-hex sha at manifest build, 2,000 documents of at least 512 tokens selected
  by a seeded hash, ODC-By.
- Image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (build 855, commit `ed5d5a93`).
- Code: the Step-0 harness (`harness/e4_gate.py`, `scripts/run_e4_gate_doctor.py`,
  `scripts/run_e4_gate.py`; none written yet) at the commit recorded in the
  freeze. The registered estimator is the one in the bundle's
  `compute/repair-d60/oracle-estimator-v2.py` (`estimate_family`), transcribed to
  KL and Adam; the Step-0 harness test suite checks the transcription on the
  surrogate's planted teachers before any GPU job.
- Seeds: demonstration seeds [42, 43, 44] (seed 45 only under the variance
  rule); oracle initialisation seed 42; restarts 43 and 44.

## Families (generated in the repository; built and checked on 2026-10-10)

Every family is a generator with the template `input: X\noutput: Y\n`
repeated 8 times, then `input: Xq\noutput:`. The answer is the next token, and
it must be exactly one token appended to the prompt's own tokens, checked on the
full string because the tokenizer runs BPE over the whole normalised string:
enc(prompt + answer) = enc(prompt) + [one id], both zero-shot and after an
8-shot block. Word answers follow `output:` as " word". The tokenizer has no
"▁digit" token, so digit answers are tokenized deliberately: for digit
families every `output:` is followed by a space, the prompt's last token is the
bare "▁" (28705), exactly as before any number in pretraining text, and
the answer is the bare digit token. Labels whose answer is not one token are
removed from a family's label set (violet from A2; rocket and tiger from A5);
an input is usable only if its answer passes for every latent value or label it
can take. A family is built only if it has at least 60 usable inputs and enough
labels for an episode (the 8 + 24 + 8 = 40 mutually distinct inputs a Step-2
episode needs, 48 in the 32-probe branch, or for A1 and A2, 8 bound names under
four templates; every built family has at least 67). The build
(`compute/repair-d60/family-table.py`, output `family-table.json`) is part of
the manifest and is rerun and hashed at manifest build.

| Class | Id | Mapping | Varies by episode | Usable inputs |
|---|---|---|---|---:|
| fixed function (FF) | F1 | lowercase word to capitalised word | no | 77 |
| FF | F2 | word to its last letter | no | 108 |
| FF | F3 | two-digit number to its first digit (digit answer) | no | 90 |
| FF | F4 | word to its first letter | no | 108 |
| FF | F5 | regular singular noun to plural | no | 67 |
| latent parameter (LP) | L1 | two-digit number (distinct digits) to its digit at position p, p in {1, 2} (digit answer) | p | 81 |
| LP | L2 | three words (one animal, one colour, one tool, shuffled) to the word of category c | c | 104 |
| LP | L3 | list of three words to the word at position p, p in {1, 2, 3} | p | 347 |
| LP | L4 | word to its i-th letter, i in {1, 2, 3} | i | 108 |
| LP | L5 | three distinct digits to the digit at position p, p in {1, 2, 3} (digit answer) | p | 319 |
| lookup and abstract label (LA) | A1 | nonce name to a single digit, fresh binding of 8 names to 8 distinct digits per episode; Step-2 probes are the 8 bound names under four templates (digit answer) | binding | 400 names |
| LA | A2 | nonce word to colour word (14 colours), fresh binding per episode; probes as A1 | binding | 400 names |
| LA | A3 | animal or tool word to one of two symbols; symbol pair (10 symbols) and assignment drawn per episode | labels | 80 |
| LA | A4 | animal, tool, colour or number word to one of the letters A-D, category-to-letter permuted per episode | labels | 110 |
| LA | A5 | positive or negative adjective to one of two unrelated label words (16) drawn per episode | labels | 91 |

Episode-specific (ES) families are LP and LA (10). Queries are disjoint from
the episode's demonstration inputs except in A1 and A2, where they are the bound
names by construction. A1 and A2 probe templates: `input: X\noutput:`, `the
number (colour) of X is`, `X stands for the number (colour)` for fitting (24
probes) and `X has the number (colour)` for scoring (8 probes), each checked by
the same rule. Zero-shot probe prompts are 7 to 13 tokens with BOS (mean 8.5);
8-shot prompts 71 to 125 (mean 85).

## Conditions and Step 1 (eligibility)

Per family and demonstration seed s, 25 episodes of 8 demonstrations and 16
queries (PCG64 keyed by family, s, episode).

- GOLD: the demonstrations with their correct outputs.
- SHUF: the same inputs in the same order with outputs permuted by a seeded
  derangement (A3, A4, A5: labels re-drawn uniformly from the episode's label
  set). The fraction of SHUF demonstrations still correct by chance is logged.
- ZS: the query template alone.

Score: argmax over the full vocabulary at the answer position equals the gold
answer token. Per family, G_LD = mean over s of (accuracy GOLD minus accuracy
SHUF) on 1,200 query instances per condition; G_ZS = accuracy GOLD minus
accuracy ZS. Cluster-t statistic on episode-level differences (75 clusters,
df 74), one-sided p-value; Holm over the 15 families at one-sided 0.05.

A family is **eligible** if G_LD is at least 0.10, its Holm-adjusted test
rejects, and G_ZS is at least 0.05.

**Format sanity (M1).** If fewer than 2 of the 5 FF families reach GOLD
accuracy 0.50, the template or tokenization is broken: INFRA_FAIL, not
STOP_TEACHER.

Secondary: 2.7B GOLD accuracy and the 1.3B/2.7B argmax disagreement rate.

## Step 2 (oracle interface ceiling and key-span sufficiency)

Runs on every eligible ES family and on one eligible FF family (the first in
F1 to F5 order; a fixed-function family is expected to read EPISODE_CONSTANT and
serves as a positive control for that verdict). Per family: the first 16
Step-1 episodes of each seed (48). Each keeps its 16 Step-1 queries and gets 8
(or, in the 32-probe branch, 16) more fitting queries and 8 scoring queries,
all drawn at manifest build with inputs disjoint from the episode's
demonstrations and from each other (A1 and A2: templates as above, 24 fitting
probes in both branches). Targets: the teacher's GOLD and SHUF next-token
distributions at the answer position of every fitting and scoring probe.

**Fitting-probe rule (fixed now; reads development reads only).** Before any
oracle fit, d90 (the number of principal components holding 90% of the centred
development probe-read energy) is computed per eligible non-lookup ES family
and site, and its median over families of the maximum over sites decides the
number of fitting probes: at most 13, 24 fitting probes and 32 evaluation
episodes per family; 14 or more, 32 fitting probes, 24 evaluation episodes per
family for the decision classes and the full reduction ladder (cost below).
S1v2's grid places the joint I1-I2-I3 window at d90 10-13 for 24 probes and
10-19 for 32 probes; above 19, I2 is expected to fail and the gate is expected
to end at INSTRUMENT_FAIL, which is reported as an identification limit of the
interface at this probe budget. The rule reads no target and no outcome.

**Interface (unchanged from v1).** Sites after blocks 6, 12, 18, 24. At each
site: W_k = ZCA whitening of the site's residuals over 131,072 FineWeb-Edu
positions (ridge 1e-4 times the mean eigenvalue); Δh = h(full prefix) minus
h(the last 16 tokens only) at 64 seeded positions at or after token 128 of each
of the 2,000 documents; V_k = top 64 right singular vectors of W_k Δh;
P_k = V_k^T W_k, Q_k = W_k^-1 V_k. Width-256 reference: the top 256.

**Reads, centring and keys.** Read x = P_k h (64-d). The family's centring
vector mu_k is the mean read over its development episodes' fitting probes
(seed 42; never an evaluation probe). Alone keys k_i^a = P_k h_k(x_i) at the
answer position of template(x_i) encoded alone; in-context keys k_i^c = P_k h_k
at the answer position of demonstration i inside the episode's 8-shot prompt.
Student: the zero-shot probe prompt, each site's residual at every probe
position replaced by h + Q_k M_k [x; 1].

**Classes** (per site k; M_k is 64 x 65, its last column a shift).

- S0: M = 0.
- S_const: C_f, a full-rank 64 x 65 affine state per family, fitted on every
  fitting probe of all 48 episodes with a free nuisance shift per episode (fixed
  effects; the shifts are discarded), 400 Adam steps on minibatches of 256
  probes. The per-episode shifts keep each episode's label prior from leaking
  into the linear part through chance correlation with the reads (S1v2 shows the
  leak without them). No scoring probe enters.
- S_shift: C_f + b_e e_65^T, a free per-episode 64-d shift (a label prior).
- S_span: C_f + b_e e_65^T + U_e Z_e^T (x - mu_k) written as an affine state,
  with U_e 64 x 8 and Z_e an orthonormal basis of the span of the episode's
  mapped keys. Three key sets: alone keys K^a_e; in-context keys K^c_e; and
  S_k B_k [S_k^T K^a_e; S_k^T K^c_e], where S_k (64 x r) spans the family's
  probe-read subspace (the top principal directions holding 99% of the centred
  development probe-read energy at site k, r at least 8) and B_k (r x 2r) is
  shared by all episodes of the family and site. B_k is a family-level
  parameter like C_f: it is fitted jointly with per-episode parts on the
  fitting probes of all 48 episodes (800 minibatch steps of 256 probes, penalty
  1e-3 times the mean curvature toward [I/2, I/2]), never on a scoring probe.
  Only the keys' read-subspace coordinates matter for this family's probes, so
  this parametrisation loses nothing on them and makes B identifiable (S1v2: a
  64 x 128 B fitted on 14 development episodes did not recover a fixed
  preconditioner). The decision-bearing key set is chosen per family among the
  three by development held-out KL and frozen before any evaluation statistic.
- S_span_alone, S_span_ctx: B fixed at [I, 0] and [0, I] (secondaries, 16
  evaluation episodes each).
- S_free: C_f + b_e e_65^T + A_e G_e^T (x - mu_k), A_e and G_e 64 x 8.
- S_resample(e): C_f + the episode's own S_shift shift + the probe-dependent
  part A G^T of the S_free state of episode e+1 of the same family and seed
  (cyclic). Decision-bearing.
- S_rand: C_f + own shift + a random rank-8 probe-dependent part with the
  Frobenius norm of the episode's own (secondary).
- S_ref (conditional): width 256, rank-16 constant plus rank-16 free part.

**Fitting.** Adam, 200 steps, full batch over the 24 fitting probes, loss =
sum of KL(p_T || p_student); learning rate per class from {1e-2, 3e-2, 1e-1},
chosen on 2 seed-42 development episodes per family and then fixed. Every
per-episode class starts at C_f with zero episode part (S_free: A = 0, G a
seeded random orthonormal matrix). Norm cap as v1 (twice the median natural
in-context shift; cap-binding rate reported).

**Quantities** (per family, over its 32 evaluation episodes, seeds 43 and 44;
KL_X(e) is the sum over the episode's 8 scoring probes):

- E_X = 1 - sum_e KL_X(e) / sum_e KL_shift(e): the share of the
  probe-dependent, episode-specific divergence that class X removes.
- D_span(e) = [KL_span(e) - KL_free(e)] / mean_e KL_shift(e).
- Delta_res(e) = [KL_resample(e) - KL_free(e)] / mean_e KL_shift(e).
- KL_LD = sum_e sum_probes KL(p_T^GOLD || p_T^SHUF): the teacher's own
  sensitivity to the labels on the same probes.
- One-sided 95% t bounds over the 32 episodes (df 31) of the episode terms; an
  episode bootstrap (2,000 resamples, seed 42) is the sensitivity.

**Variance rule (fixed now).** If the pooled within-family SD of D_span on the
development episodes exceeds 0.10, 32 more evaluation episodes per ES family
are drawn with demonstration seed 45 before any seed-43/44 statistic is
computed, provided the smoke-derived projection with them stays under the
Step-2 cap; otherwise they are not drawn and this is reported. The rule reads
the SD only.

## Instrument gates (run before any capacity or span statistic is read)

- **I0 constant adequacy (per family).** I0 = 1 - sum_e KL(own shift + the
  leave-one-out mean of the other evaluation episodes' probe-dependent S_free
  parts)(e) / sum_e KL_shift(e) must be at most 0.05. A larger value means C_f
  leaves a family-generic residual that per-episode states would absorb and
  that would read as episode-specific and out of span. On failure C_f is
  refitted once with 800 steps; a second failure excludes the family as
  INSTRUMENT_FAIL_I0 (reported); if half or more of the guarded families fail,
  INSTRUMENT_FAIL.
- **I1 non-vacuity (per family).** The median over evaluation episodes of the
  fraction of centred scoring-read energy |x - mu_k|^2 outside the chosen key
  span must be at least 0.25 at every site. A family below it is SPAN_VACUOUS:
  it counts toward capacity but not toward the span verdict. The lookup
  families (A1, A2) are SPAN_VACUOUS by construction (their scoring probes are
  the demonstrated names; S1v2's lookup teacher reads 0.04-0.06) and serve only
  as the OPEN guard. (v1's pooled
  median at 0.50 is replaced; S1v2 shows I3 is the discriminability check and
  0.50 closed the identification window.)
- **I2 planted recovery.** Per family, 2 development episodes x 2 planted types:
  a rank-8 probe-dependent part whose read directions are drawn from the
  subspace holding 90% of the centred development probe-read energy, plus a
  shift; and a part in the chosen key span. Planted norms: half the norm cap
  (from the natural in-context shift, not from fitted states). Targets are the
  frozen model's outputs under C_f plus the planted part; fitted by the class
  that contains it, best of 3 restarts (seeds 42, 43, 44) by fitting loss.
  Recovery = 1 - KL(planted || fitted) / KL(planted || C_f only) on scoring
  probes. Pass: at least 0.90 in at least 90% of planted episodes.
- **I3 span discrimination.** On 2 more development episodes per type:
  planted parts whose read directions lie in the probe-read subspace and
  orthogonal to the chosen key span must give D_span^pl at least 0.30; planted
  key-span parts at most 0.03; each in at least 90% of planted episodes.
- **I4 code-path checks.** M = 0 reproduces the unmodified model's logits
  exactly; the cached-prefix path (blocks 1-6 computed once per probe) gives
  the uncached logits to 1e-6 in fp32 (the cached path is mandatory: a failure
  is a harness defect, INFRA_FAIL until fixed); no scoring probe enters any fit
  (hash audit); the resample state of an episode never uses that episode's
  targets.
- **I5 preconditioned writer (caps OPEN).** A shared random B* (64 x 64,
  condition number 10, seed 42) and parts U (B* K^a_e)^T are planted on the
  fitting probes of all 48 episodes of the family (synthetic targets: the frozen
  model under C_f plus the planted part); B_k is refitted on them by the
  registered procedure and the chosen-key-set class is scored on 8 further
  planted development episodes. Pass: the planted writer does not meet the
  family GAP rule (not both mean D_span^pl at least 0.10 and its one-sided 95%
  lower bound above 0.02). A failure caps the span verdict at INCONCLUSIVE_SPAN
  instead of OPEN.
- **I6 contextualised-key writer (caps OPEN).** Parts U (K^c'_e)^T, where K^c'
  are in-context keys read from an 8-shot prompt with the demonstrations in a
  seeded permuted order (a gradient-form writer whose keys are contextualised
  differently from the instrument's), planted on 8 development episodes per
  family. Pass: the planted writer does not meet the family GAP rule. A failure
  caps the span verdict at INCONCLUSIVE_SPAN.
- **I7 label-prior writer.** A planted per-episode shift alone, on 8
  development episodes per family; the placebo contrast on them must not pass
  (one-sided 95% lower bound of mean Delta_res at most 0.10). A failure is
  INSTRUMENT_FAIL (the placebo would then call a label prior episode-specific).

Any failure of I2-I4 or I7 as stated is **INSTRUMENT_FAIL**: no capacity or
span verdict; the repair is a new experiment id. d90 is reported per family and
site with the branch it selected.

## Decision rules

Evaluated in this order; the first verdict reached is final.

1. **INFRA_FAIL** if the smoke fails, M1 fails, or a job fails twice for
   infrastructure reasons.
2. **STOP_TEACHER (K2)** if fewer than 4 ES families are eligible. (10 ES
   families are built and checked before freeze, so this needs at least 7 of 10
   to fail on the teacher; v1's absolute "8 of 14 overall" clause is dropped
   because it was set by the manifest, and the overall eligible count is
   reported.)
3. **INSTRUMENT_FAIL** if I2-I4 or I7 fails, or if I0 excludes half or more of
   the eligible ES families.
4. **Episode-specificity (per eligible ES family).** EPISODE_SPECIFIC if the
   one-sided 95% lower bound of mean Delta_res is above 0.10 and KL_shift is at
   least 0.10 KL_LD (the label-prior guard); otherwise EPISODE_CONSTANT (the
   family's label-dependent behaviour is carried by one family state plus a
   per-episode label prior). **STOP_TR** if fewer than 4 eligible ES families
   are EPISODE_SPECIFIC. n_ES below counts EPISODE_SPECIFIC families.
5. **Capacity** on the n_ES families. Per family: CAP_OK if the one-sided 95%
   lower bound of E_free is at least 0.50; CAP_LOW if the upper bound is below
   0.50.
   - CAPACITY_PASS if CAP_OK in at least ceil(0.75 n_ES) families.
   - Otherwise, if CAP_LOW in at least ceil(0.5 n_ES) families, the conditional
     arm runs on the CAP_LOW families: the in-sample ceiling (S_free fitted on
     all 32 probes of 16 evaluation episodes), the supervised-map arm (as v1),
     and S_ref (16 episodes). **INCONCLUSIVE_IDENTIFICATION** if the in-sample
     ceiling's E is at least 0.50 in at least half of them (the state class can
     carry the behaviour but 24 probes cannot identify it); else
     **STOP_LABEL_FREE_MAP** if the supervised map makes at least half of them
     CAP_OK; else **STOP_INTERFACE_SIZE** if S_ref's E has a lower bound of at
     least 0.50 in at least half; else **STOP_INTERFACE_CLASS**.
   - Otherwise **INCONCLUSIVE_CAPACITY**.
6. **Span** on the n_ok CAP_OK families that pass I1 (only after
   CAPACITY_PASS). Per family: TIE if the one-sided 95% upper bound of D_span
   is at most 0.05; GAP if D_span is at least 0.10 and its one-sided 95% lower
   bound exceeds 0.02.
   - **STOP_SPAN** if n_ok is at least 3, no family is GAP, and the one-sided
     95% upper bound of the across-family mean of the family D_span means
     (random effects: t over the n_ok families, df n_ok - 1) is at most 0.05.
     (v1's count rule, TIE in at least ceil(0.75 n_ok) families, is reported
     beside it; S2v2 shows it reaches STOP_SPAN under a true tie only 0.35 of
     the time at the central noise, against 0.61 for the pooled rule, with no
     false STOP_SPAN in any gap scenario.)
   - **OPEN** if GAP holds in at least max(2, ceil(0.5 n_ok)) families, every
     CAP_OK lookup family (A1, A2; never counted in n_ok) has D_span at most
     0.05, and I5 and I6 passed.
   - Otherwise **INCONCLUSIVE_SPAN**.

OPEN licenses only a Step-3 gauntlet. It is pre-registered as not identifying
a non-gradient learning rule: within-family retrieval among stored functions
predicts it.

## Reported regardless of outcome

Per family: G_LD, G_ZS, accuracies in every condition, the SHUF chance-correct
fraction, eligibility; R and E for every class; D_span for the chosen key set,
alone keys and in-context keys; Delta_res, KL_LD and the guard ratio; I0 to I7
values; d90 per site; the chosen key set; placebo floors (S_resample, S_rand);
argmax agreement and Cohen's kappa; permuted-target re-scored R; site-1.0
ablation (S_free without the last site, 8 episodes); cap-binding rate;
injected norm ratios; restart spread; the 2.7B disagreement rate; per-class
summaries. All per-probe tables are released in the bundle.

## Simulations (CPU, 2026-10-10; none is evidence about the teacher)

- **F1 family table** (`family-table.py`/`.json`): the 15 families above, built
  under the teacher's tokenizer with the deliberate digit rule.
- **S1v2 estimator semantics** (`oracle-estimator-v2.py`/`.json`, the
  registered estimator on a linear surrogate, 32-d interface, d_task 12, 24
  fitting probes, 14 development and 32 evaluation episodes, seeds 42/43/44,
  2 families each): constant, family-generic nonlinear and per-episode
  label-prior teachers read EPISODE_CONSTANT in 6 of 6 families; first-order
  (alone keys, plus a label prior, on in-context keys, on differently
  contextualised keys) and RLS teachers TIE 6/6 (D_span -0.04 to 0.00); a
  fixed-preconditioner teacher TIE 5/6 and undecided 1/6 (D_span 0.01-0.06);
  the lookup teacher SPAN_VACUOUS 6/6 with D_span 0.00; retrieval and
  value-directed teachers GAP 6/6 (0.13-0.33); a deliberately under-fitted
  C_f is stopped by I0 (0.20-0.29) 6/6. Planted gates: I2, I3, I6 and I7 12/12,
  I5 11/12. In wave 1's regime the v1 estimator reproduces the wave-1 failure
  (constant teacher GAP 6/6, RLS GAP 6/6) and v2 never reads GAP.
- **S1v2 identifiability grid** (`oracle-estimator-v2-grid.json`, seed 42, 2 families per cell): at 16
  fitting probes I2 fails for every d_task of 12 or more; at 24 probes I1, I2
  and I3 pass together and the verdicts are right for d_task 12-16 (d90
  10-13); at 32 probes for d_task 12-24 (d90 10-19); d_task 6-8 reads
  SPAN_VACUOUS with I3 failing; d_task 32 fails I2 at every count. This sets
  the fitting-probe rule above.
- **G1 guard** (`guard-sim.py`/`.json`, exact categorical model over accuracy
  0.45-0.90 and cardinality 2-8): v1's KL_S0 guard calls 69 of 171
  label-dependent settings EPISODE_CONSTANT; the v2 label-prior guard calls 0
  of 171 (smallest ratio 0.19 against the 0.10 line) and catches all 57
  pure label-prior settings (v1: 23).
- **S2v2 decision path** (`decision-sim-v2.py`/`.json`, 2,000 replicates per cell,
  instrument gates assumed passed): the correct verdict with probability 1.00
  in weak-teacher, task-recognition and low-capacity worlds; 0.61 (central
  noise) and 0.47 (high) under a tie at D_span 0 with family heterogeneity,
  0.84 and 0.70 at D_span -0.02; 0.93 and 0.79 under a gap of 0.20; at most
  0.004 for any wrong decisive verdict. In the 32-probe branch (24 evaluation
  episodes) the tie, tie at -0.02, gap and small-gap rows read 0.60, 0.82, 0.92
  and 0.65 (central) and 0.42, 0.63, 0.74 and 0.26 (high).
- **S3v2 cost** (`cost-model-v2.py`/`.json`): below.

## Smoke (at most 0.17 GPU-h, one GPU)

As v1 (two load paths cross-checked, FineWeb-Edu loss sanity, resume
equivalence), plus: the cached-prefix path (blocks 1-6 computed once per
probe) reproduces the uncached logits to 1e-6 in fp32 on 64 probes (I4; the
cached path is mandatory); measured oracle-step throughput projects every job
under its cap, after the reduction ladder if needed. Otherwise INFRA_FAIL or
not frozen.

## Compute

| Job | Cap (GPU-h) | Central | High (measured prompt lengths) |
|---|---:|---:|---:|
| smoke | 0.17 | 0.17 | 0.17 |
| Step 1 (15 families, 1.3B GOLD, SHUF, ZS; 2.7B GOLD) | 0.55 | 0.08 | 0.21 |
| Step 2 main (at most 11 families) | 5.50 | 1.18 | 5.47 (4.58 after the ladder); 32-probe branch 5.07 |
| Step 2 conditional (after CAP_LOW only) | 1.50 | 0.32 | 1.40 |
| **Sum of caps (D22)** | **7.72** | | |

Method as wave 1 (FLOPs over MFU times the 989 TFLOP/s BF16 peak, a 1.25
factor, launch overhead); central 25% MFU, high 12.5% MFU and 1.5x launch
overhead. Inputs that changed: prompt lengths are measured with the teacher's
tokenizer (zero-shot max 13, 8-shot max 125; central 10/100, high 16/140,
against wave 1's assumed 12/200 and 24/400); oracle steps run blocks 7-24 only
(factor 0.75; the cached path is mandatory and checked by I4); 24 fitting
probes (x1.5 per fit); the design re-counted at 381 episode-fit units per
family (11 families: 4,187), including C_f and B_k fitted by minibatch on all
48 episodes' fitting probes and I5 planted on all 48. Reduction ladder, in
order, if the smoke projects Step 2 over its cap: drop restart sensitivity;
drop the site-1.0 ablation; halve the eval secondaries; drop them (high after
the full ladder 4.58). Conditional ladder: S_ref and the in-sample ceiling to 8
episodes (high 1.07). If any projection still exceeds a cap, the registration
is not frozen and returns to the gauntlet. With wave 1's prompt-length
assumptions the high case would not fit (about 8.2 GPU-h for Step 2); that is
why the lengths were measured. One GPU per job,
Docker lane through `scripts/submit_docker_research_job.py` (dry run,
test-only, submit), checkpoints every 10 minutes, fresh-job resume. The
gauntlet's 0.3 GPU-h (reviewer inference) is separate.

## Infrastructure failures and exclusions

As v1. No family, episode or probe is excluded after Step 1 starts, except a
probe whose teacher target is non-finite (logged and counted) and families
excluded by I0 or marked SPAN_VACUOUS by I1 (reported).

## Data rights

As v1: repository-generated families (MIT), FineWeb-Edu (ODC-By 1.0) for P and
Q only, fla-hub checkpoints MIT by card tag (first-party; no LICENSE file), no
third-party task data. The tokenizer files are fetched at run time, pinned by
revision and hash, and not committed.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the estimator is registered as code
   (S1v2), the harness must reproduce S1v2's planted-teacher verdicts before any
   GPU job, and I0-I7 run on real residuals before any reading. Wave 1's S1 did
   not implement its own registration; S1v2 is the registered estimator.
2. Hallucinated citation: every cited id snapshotted (HTTP 200) and the
   wave-1-uncited priors read in full.
3. Hallucinated result: no teacher result exists; every number is from a
   simulation, the tokenizer, or a source, labelled as such.
4. Shortcut reliance: held-out probes, per-episode shift floor, family
   constant, placebo, norm cap, site-1.0 ablation, permuted-target re-scoring.
5. Bug reframed as insight: a lookup family failing span sufficiency blocks
   OPEN; I0, I2, I3 and I7 failures stop the gate; I5 and I6 failures cap it.
6. Methodology fabrication: thresholds are fixed here with their simulation;
   the variance rule reads only an SD from development episodes.
7. Frame-lock: thirteen verdicts, seven of them scientific stops; OPEN is
   pre-registered as not identifying the mechanism.

## Freeze procedure

After Step 0 (harness, tests including the S1v2 transcription check, CPU doctor
as an orx `cpu-doctor` node), the smoke, a reviewed gauntlet package and the
owner's acceptance of the design decisions:
`uv run python scripts/preregister.py freeze e4-icl-write-rule-gate-v2
program/preregistrations/e4-icl-write-rule-gate-v2.md`, then verify, and record
the freeze commit in every manifest.

## Design decisions (for the owner's acceptance)

Decisions 1-5, 9, 10, 12, 15, 18, 20, 21, 23-26, 28-30 of v1 stand. Amended or
new:

31. New experiment id (v2); v1 is superseded and left unedited.
32. Family table rebuilt under the teacher's tokenizer (15 families, 10 ES),
    with the whole-string single-token rule and deliberate digit tokenization
    (replaces v1 decision 7; F2, F3, L1, L2, L5 and A1 redesigned, A5 added).
33. Floor of 60 usable inputs per family; labels that fail the rule are removed
    from the label set.
34. K2 = fewer than 4 eligible ES families (replaces v1 decisions 6 and 8's "8
    of 14"); Holm over 15.
35. M1 format sanity on FF families (INFRA_FAIL, not STOP_TEACHER).
36. Step 2 on all eligible ES families plus one FF family (replaces part of
    v1 decision 11).
37. 24 fitting and 8 scoring probes per Step-2 episode, or 32 fitting probes
    with 24 evaluation episodes when the development d90 is 14 or more; A1 and
    A2 under four templates with 24 fitting probes.
38. Family constant: full rank, every fitting probe of 48 episodes, per-episode
    nuisance shifts, 400 minibatch steps (replaces v1's rank 8 on 4 probes).
39. Every per-episode class carries a free shift; S_shift is the floor for E
    and D_span (replaces v1 decision 16's KL_const denominator).
40. Probe-dependent parts read centred coordinates x - mu_k, mu_k from
    development fitting probes.
41. Key sets: alone, in-context and a shared read-subspace map over both
    (B_k r x 2r, fitted like C_f on all episodes' fitting probes), chosen per
    family on development episodes (replaces v1 decision 14).
42. Resample placebo with the episode's own shift; decision-bearing through
    the episode-specificity rule.
43. Label-prior guard KL_shift >= 0.10 KL_LD (replaces v1's KL_const/KL_S0 >=
    0.20).
44. STOP_TR when fewer than 4 eligible ES families are EPISODE_SPECIFIC.
45. I0 constant adequacy at 0.05, with one refit.
46. I1 per family at 0.25, failing families SPAN_VACUOUS.
47. I2 planted norms from the natural shift; I3 with out-of-span planted parts.
48. I4 adds the cached-prefix equivalence check.
49. I5 plants on all 48 episodes and refits B_k as registered; I5 and I6 pass
    when the planted writer would not meet the GAP rule.
50. I6 permuted-context-key writer, capping OPEN.
51. I7 planted label prior, INSTRUMENT_FAIL on failure.
52. Conditional in-sample ceiling and INCONCLUSIVE_IDENTIFICATION before any
    interface stop.
53. SHUF-target oracle fits dropped (the guard uses SHUF predictions).
54. Caps 0.17, 0.55, 5.5, 1.5 GPU-h (sum 7.72) and the two ladders.
55. Prefix caching of blocks 1-6, mandatory, checked by I4.
56. Claim scope: STOP_SPAN does not speak to gradient descent specifically.
57. The registered estimator is the bundle's `estimate_family`, transcribed.
58. Variance rule kept, conditional on the projection.
59. The A3, A4 and A5 SHUF re-draw labels from the episode's label set.
60. Teacher SHUF predictions on every Step-2 probe (for KL_LD).
61. Reported secondaries as listed (S_span_alone, S_span_ctx, S_rand).
62. No host job while any Q2 S1a job runs or is pending; no GPU job before a
    freeze.
63. STOP_SPAN by the pooled random-effects bound with no GAP family (replaces
    v1 decision 20 for STOP_SPAN; OPEN keeps the family count).

## Repair under D60

Each row names the wave-1 defect, who found it, the change, the clause, and the CPU check (bundle `compute/repair-d60/`).

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
