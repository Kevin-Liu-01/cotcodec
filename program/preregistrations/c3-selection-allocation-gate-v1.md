# C3 Stage-0 gate v1: held-out decodability of a linear answer-token selector in thinking mode and the contested-question share (c3-selection-allocation-gate-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the C3 research gauntlet (D64) on branch
`gauntlet/c3-selection`. It registers only C3's Stage-0 precondition gate. The
2x2 factorial (learned selector crossed with adaptive per-question
re-attempts, against a tuned longer single pass, at matched measured
GPU-seconds) is not registered here and needs its own gauntlet and, being over
8 GPU-h, Kevin's admission under D24. The design decisions at the end (1 to 34)
need the program owner's acceptance. Caps are set by a formula fixed here
before the pilot runs; their sum must be at most 8.0 GPU-h under D22, or the
main stage is not run. No host job of any kind runs while a Q2 S1a VM or GPU
job is running or pending. The gauntlet proposal that argues and attacks this
design is `program/proposals/2026-10-10-c3-selection-allocation-gate.md`; its
evidence bundle is
`program/proposals/evidence/2026-10-10-c3-selection-allocation-gate/`.

## Relation to the dossier and to D64

- Source: dossier entry `C3-selection-and-allocation`
  (`program/evidence/2026-10-06/question-dossier.md`, section 9), first
  experiment steps (a) to (e) and kill criteria "held-out decodability AUC
  below 0.60 or spread share below 20%".
- The AUC line is kept: 0.60 on the pooled within-question AUC of held-out
  families, read through a 90% family-cluster bootstrap interval (line D).
- The spread line is kept in purpose and replaced in statistic. The dossier's
  statistic (share of questions whose empirical pass rate over the draws lies in
  [0.1, 0.9]) passes a 20% line with probability 0.39 when every question has
  p = 0.957 (no heterogeneity) at 320 held-out questions (S1). Its corrected
  target, the share of questions whose true pass rate is in [0.1, 0.9]
  (pi_mid), is not identified from six draws (S1, section `identification`).
  Line S uses the identified contested share kappa6 (2 to 4 of 6 correct), with
  its line 0.10 calibrated to pi_mid ≈ 0.18 to 0.21 when in-band mass is
  spread across the band; the raw statistic and the pi_mid identified set are reported.
- Two lines are added, both able only to stop or to withhold GO, never to
  rescue a failed dossier line: F (the gate must beat an output-only floor) and
  H (a gate-weighted vote must not be worse than majority voting).
- Step (a) of the dossier ("measure real decode throughput and whole-job
  GPU-seconds, about 0.5 GPU-h") is P0 here, with a cap of 1.0 GPU-h, and it
  also measures lengths and contestedness by stratum to set the workload and N.
- "Problems split by family (about 600 training, about 400 held-out)" becomes
  a 50/50 family split of N questions, N between 560 and 800 by the cap rule.

## Question

For Qwen3-8B in thinking mode, on the workload chosen by the registered rule
from pre-declared competition-mathematics strata: (D) does a linear gate on
the answer-token residual state, fitted on training families, reach a pooled
within-question AUC of at least 0.60 on held-out families; (F) does it beat an
output-only floor fitted the same way; (S) are at least 10% of held-out
questions contested over six draws; (H) is a gate-weighted vote not worse than
majority voting at six draws? GO requires all four.

Claim scope: a precondition measurement on one frozen model and one
registered workload. No claim about whether selection and allocation stack, or
about a longer single pass, is licensed by any outcome.

## Identity

- Experiment id: `c3-selection-allocation-gate-v1`.
- Model: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`
  (registry id `qwen3-8b`), Apache-2.0; five safetensors shards totalling
  16,381,516,776 B at that revision (HF tree API, read 2026-10-10).
- Generation image: the cu129 overlay of
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  built at the freeze commit by `scripts/build_vllm_overlay_on_h100.sh` (its
  image ID and provenance receipt are recorded; the build is infrastructure
  GPU time, reported separately as in D17 and D19).
- Extraction image:
  `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`.
- Code revision: the freeze commit; the harness files and their SHA-256 are
  listed in the freeze record. Data revisions: the Hugging Face dataset commit
  hashes in the data manifest, fixed at freeze.
- Seeds: generation per-request seed = first 4 bytes (little-endian, an
  unsigned 32-bit integer) of SHA-256 of the JSON list [42, family id,
  question id, draw index]; family
  split seeds 42 (primary), 43 and 44 (sensitivity, CPU only); CV-fold,
  bootstrap and permutation seed 42; draw order for prefix-consumption curves
  permuted by seed 42.

## Prerequisites before freeze (no GPU)

1. Registry amendment for `qwen3-8b`: add the role
   `c3-stage0-model`, replace the "no weight download is planned" blocker, keep
   the revision. Then a full-mode fetch through
   `infra/slurm/host-single-node/fetch-model-cpu.sbatch` (CPU-only Slurm job)
   with a full receipt (`publication_eligible: true`), under D1. This is a host
   action and waits until no S1a VM or GPU job is running.
2. Harness (reviewed project code under D7): generation driver (seeds,
   log-probabilities, step statistics, checkpoint and resume), answer-position
   extractor, graders, family builder with the near-duplicate audit, HF
   extraction job, analysis (gate, floor, selection, spread, accounting), each
   unit-tested on CPU with a random-initialised Qwen3-shaped model.
3. Data manifest (ids, dataset revisions, statement SHA-256, reference
   answers' SHA-256, stratum, family id, exposure flags), committed without
   problem text.
4. Grader audit set: 200 items stratified by stratum, labelled by math-verify,
   by a strict sympy and normalised-string grader, and adjudicated by the
   operator where they disagree; adjudication log committed.
5. Manifests for smoke, P0, G-decode and G-extraction; `--dry-run` and
   `--test-only` pass for each.
6. A `kind: cpu-doctor` orx node that runs the analysis pipeline on S1-style
   synthetic pools with known AUC, floor increment and kappa6, and checks
   recovery within the simulated standard deviations.
7. A fresh pre-freeze audit of this file against the harness.

## Data

**Candidate strata (pre-declared; the workload rule chooses among them):**

| Stratum | Source (card licence) | Selection | Family key |
|---|---|---|---|
| A1 | EleutherAI/hendrycks_math (MIT) | Level 5, all subjects, MATH-500 test ids excluded | near-duplicate component (no provenance field) |
| A2 | KbsdJames/Omni-MATH (Apache-2.0) | difficulty ≤ 4.5, reference answer parseable by math-verify | source competition |
| A3 | KbsdJames/Omni-MATH | difficulty 5.0 to 6.0, parseable | source competition |
| A4 | KbsdJames/Omni-MATH | difficulty ≥ 6.5, parseable | source competition |
| A5 | Hothan/OlympiadBench (Apache-2.0) | OE_TO_maths_en_COMP, numeric or expression answers | near-duplicate component |
| A6 | AI-MO/aimo-validation-aime and -amc (Apache-2.0) | AIME 2022 and 2023, AMC 12 2022 and 2023; AIME 2024 excluded (benchmark-exposed) | exam instance from the AoPS URL |

**Families.** A family is a connected component of the graph whose edges are
(a) the stratum's family key and (b) near-duplicate links across all strata:
MinHash LSH on normalised statement word 5-grams with Jaccard at least 0.5, or
the same normalised final answer together with bge-small-en-v1.5 cosine at
least 0.9 (registry id `bge-small-en-v1.5`, CPU). At most 25 questions per
family enter G, chosen by seed 42. Families are assigned 50/50 to training and
held-out within each stratum by seed 42 (largest families first, alternating
by cumulative question count, then random).

**Exclusions.** MATH-500 test ids; AIME 2024 and later; MathArena sets
(CC-BY-NC-SA-4.0, D4); SynthLabsAI/Big-Math (gated); DeepScaleR's AIME and AMC
(no provenance fields); NuminaMath-1.5 and DAPO-Math-17k; code.

**Contamination.** All permissive sources predate Qwen3-8B's release
(2025-04-27), so no date partition is possible; this is disclosed. Every P0
and G question gets two memorisation probes, run in the same job at
negligible cost: prefix completion (first half of the statement, greedy, 64
tokens, non-thinking; flag if ROUGE-L against the second half is at least 0.6
or any 13-gram matches exactly) and a no-reasoning answer (non-thinking mode,
at most 32 tokens; flag if it is graded correct). Every line is also reported
with flagged questions excluded (sensitivity, not decision-bearing).

**Prompt.** The model's chat template with thinking enabled and the user turn
"{problem}\n\nPlease reason step by step, and put your final answer within
\boxed{}." No system prompt.

**Grading.** math-verify equivalence between the last `\boxed{...}` after the
final end-of-thinking marker and the reference answer; strict grader as a
cross-check; math-verify is primary. Instrument gate I1 (below).

## Stages

### Smoke (cap 0.25 GPU-h, one GPU, generation image then extraction image)

Load the real weights; generate 16 draws (8 training-family questions
excluded from P0 and G, max_tokens 2,048) and check answer extraction; kill the job after 60
seconds of decoding and resume it, requiring the resumed set of completed keys
and their token ids to equal those of an uninterrupted run for requests that
completed before the kill; run the extraction on 4 completed traces of full
length from a second small batch (max_tokens 32,768, 4 draws) and check I7 on
all completed traces (at least 4 here; 32 in P0). No data from the smoke enters
any line.

### P0 pilot (cap 1.0 GPU-h, one GPU)

120 training-family questions, 20 per stratum, chosen by seed 42 from training
families only; 2 draws each (240 traces) at the registered engine settings;
the memorisation probes; extraction on 32 traces (stratified) to measure HF
prefill throughput and check I7; whole-job GPU-seconds. Questions are
processed in seeded random order across strata so a cap-hit truncates strata
evenly. P0 questions never enter G.

Outputs per stratum s: completed traces; mean and second moment of generated
length (with truncation at 32,768 counted at the cap); truncation rate;
discordant-pair rate tau_s (the share of P0 questions whose two draws disagree
in correctness, an unbiased estimate of E[2p(1-p)]); per-trace decode
GPU-seconds from the step log; HF prefill MFU.

### Workload and N rule (CPU, after P0, deterministic)

1. Calibrate: c = (P0 measured decode GPU-seconds) / (S2 model's prediction for
   P0's traces with the central constants). Projected decode GPU-seconds for a
   G trace of length L are c x [t_seq x L + (P x L + L²/2) x (W / (occ x C) +
   kv) / BW] with S2's central constants (t_seq 0.022 ms per sequence-step, BW
   2.805 TB/s, occ 0.92, W 15.27 GiB, C 388,384 tokens, kv 147,456 B) and
   P = 250. A G question's projected cost is three times the summed projection
   of its stratum's P0 questions' two traces, averaged over the stratum. The
   high projection uses the upper end of a 90% bootstrap interval (over P0
   questions, B = 2,000, seed 42) of that mean per-question cost and 1.12
   preemption in place of 1.05.
2. Eligible strata: tau_s ≥ 0.05 and at least 10 completed P0 questions.
3. Equal question counts across eligible strata. N = the largest multiple of 40
   in [560, 800] for which the cap sum (below) is at most 8.0 GPU-h, limited by
   the available training and held-out families of each stratum.
4. If no N is admissible, drop the eligible stratum with the highest projected
   cost per question and repeat while at least 3 strata remain.
5. If no admissible set with at least 3 strata exists, the verdict is
   INFEASIBLE and G is not run.

The rule uses P0 information on contestedness (tau_s) and cost only, from
training families only. The workload it selects is therefore designed, not a
natural benchmark; this is disclosed in every report, and the later 2x2 would
run on the same workload.

### G generation (cap set by the formula)

N questions (N/2 training-family, N/2 held-out-family) x 6 draws at the
registered engine settings, in seeded random family order; memorisation
probes; step statistics logged every 10 seconds (step time, running and
waiting requests, their context lengths, KV usage, preemptions, prefix-cache
hits).

### G extraction (cap set by the formula)

One teacher-forced pass per completed draw with an answer position, on the
stored token ids (never re-tokenised text), bf16, SDPA, batch 1 sorted by
length, `use_cache=False` under inference mode, `lm_head` skipped. Stored per
draw: the primary position's residual outputs at all 37 points (embeddings plus
36 blocks), and at layers 18 to 36 the secondary positions (last answer token,
closing brace, end-of-thinking marker, final token, mean of the last 16
tokens). The prompt-only control state (last prompt token, layers 18 to 36) is
stored once per question.

## Gate fitting (CPU, on the development Mac or a host CPU job)

- Training data: all draws with an answer position from training families.
- Gate: per-feature standardisation then L2-regularised logistic regression
  (scikit-learn, lbfgs, max_iter 2,000). Layer grid {12, 15, 18, 21, 24, 27,
  30, 33, 36}; C grid {0.01, 0.1, 1.0}; the pair minimising mean log loss over
  5-fold family-grouped cross-validation within training families is refitted
  on all training families and scores every held-out draw once.
- Floor: the same procedure on output-only features: log total generated
  tokens, log thinking tokens, log answer-segment tokens, mean and minimum
  sampled-token log-probability over the answer segment, mean sampled-token
  log-probability over the trace, mean top-20 entropy over the answer segment,
  the answer's vote share among the question's six draws.
- Combined: gate features plus floor features, same procedure (reported).
- CASE-faithful secondary: C = 1.0 at the layer maximising out-of-fold pooled
  within-question AUC inside training families (reported).
- Selectors on held-out questions: majority vote (math-verify equivalence
  classes; ties uniformly at random, expected value), CASE argmax (draw with
  the highest gate score), gate-weighted vote (sum of gate probabilities per
  equivalence class).

## Lines and decision rules

All intervals are 90% two-sided percentile intervals from a family-cluster
bootstrap over held-out families (B = 2,000, seed 42). L90 and U90 are their
ends. Split seed 42 governs; seeds 43 and 44 are reported, and a verdict that
differs under either is flagged SPLIT_SENSITIVE without being changed.

**Instrument gates (read first).**

- I1: math-verify agrees with the adjudicated label on at least 98% of the 200
  audit items.
- I2: at least 85% of G's completed draws have an answer position.
- I3: within-question label permutation (200 permutations of correctness within
  each held-out question): mean within-question AUC in [0.48, 0.52].
- I4: the prompt-only control's within-question AUC equals 0.5 exactly.
- I5: zero near-duplicate links between training and held-out families, and
  between held-out families and P0 questions.
- I6: at least 80 mixed held-out questions (at least one correct and one wrong
  draw with an answer position); otherwise INCONCLUSIVE_N.
- I7: on P0's 32 extraction traces, the HF pass's log-probability of the
  sampled first answer token at the answer position matches vLLM's recorded
  log-probability within 0.05 nats for at least 95% (computed with `lm_head`
  for this check only).

Any failure of I1 to I5 or I7 gives INSTRUMENT_FAIL and no line is read.

**Lines.**

- D = pooled within-question AUC of the gate over mixed held-out questions
  (Mann-Whitney per question, ties counted 1/2, averaged with equal question
  weight). PASS_D if L90(D) ≥ 0.60; STOP_DECODE if U90(D) is below 0.60.
- F = D minus the floor's pooled within-question AUC on the same questions
  (paired per question). PASS_F if L90(F) is above 0; STOP_REDUNDANT if U90(F)
  is below 0.02.
- S = kappa6 = share of held-out questions with 2, 3 or 4 of 6 draws correct
  (draws without an answer position count as wrong; a question with fewer than
  6 completed draws is excluded and reported). PASS_S if L90(S) ≥ 0.10;
  STOP_SPREAD if U90(S) is below 0.10.
- H = accuracy of the gate-weighted vote minus accuracy of majority voting over
  all held-out questions at six draws. STOP_HARM if U90(H) is below 0.

**Verdicts.** GO if PASS_D, PASS_F, PASS_S, no STOP_HARM and every instrument
gate passes. Each STOP fires on its own and all that fire are reported.
Otherwise INCONCLUSIVE, naming each line that is neither PASS nor STOP.
INFEASIBLE comes from the workload rule. GO licenses only a gauntlet for the
2x2; no verdict licenses further GPU work inside this registration.

## Reported regardless of outcome

1. Every line's point estimate and interval, under split seeds 42, 43 and 44,
   with and without memorisation-flagged questions.
2. The dossier's raw spread statistic (1 to 5 of 6 correct) with its interval;
   tau2 = E[2p(1-p)] and Var(p) (split-half covariance between draws 1 to 3 and
   4 to 6) with intervals; the pi_mid identified set (sharp linear-programming
   bounds over mixing distributions on a 201-point grid that reproduce the
   six-draw count distribution, bootstrapped outer 90% bounds).
3. CASE's medium-bin within-question AUC (CASE's bin [0.35, 0.6) applied to
   the question's own six draws, which leaves only questions with 3 of 6
   correct; flagged circular as in CASE Sec. 3.5) and the hard-bin (1 or 2 of
   6 correct) selection gain.
4. Pooled AUC under a draw-level random split, a question-grouped split and the
   family-grouped split; the gap.
5. Selection accuracy at k = 1 to 6 by prefix consumption of the stored draws
   in the seeded draw order, for majority vote, argmax and weighted vote, with
   oracle pass@k.
6. Combined-model and length-residualised gate AUCs; secondary positions;
   learning curve at 25, 50 and 75% of training families; the CASE-faithful
   secondary.
7. The prompt-only control's pooled AUC and its question-level AUC for
   predicting a contested pool, and a draw-1 predictor (gate score, length,
   log-probability of the first draw) for the same target: the cross-question
   signal the 2x2's allocator would need.
8. Inputs for the 2x2's power gate: per-question variance of accuracy for each
   selector at k = 1 to 6, between-selector correlations on shared draws, the
   family design effect, and the projected interaction MDE at 1,200 held-out
   questions: 2.80 times the square root of 4 x p(1-p) x (1 - rho) x deff / n
   (80% power, two-sided 5%).
9. GPU-second accounting (below), truncation rates by stratum, length
   distributions, P0 projections against G measurements (prediction P5).
10. The workload rule's inputs and choices, the families, and the split.

## Statistics, sample sizes and simulation

Sample size: N between 560 and 800 questions by the cap rule, half held out
(280 to 400 held-out questions). Simulation S1 (`compute/gate-sim.py` and
`.json` in the bundle; 600 replicates per cell over seeds 42, 43, 44; B =
1,000; assumed distributions) gives at 320 held-out questions: D PASS
probability 0.947 at a true AUC of 0.70 and 0.628 at 0.66, STOP 0.595 at 0.54,
false PASS 0.068 and false STOP 0.047 at 0.60; F PASS 0.66 to 0.77 at a true
increment of 0.08, false PASS 0.07 at 0; S STOP 1.00 with no heterogeneity or
no question in band, PASS 0.94 at kappa6 0.174, INDETERMINATE for most pools
with kappa6 between about 0.08 and 0.14; H false STOP at most 0.043. The
weighted vote's gain has a standard deviation of 0.80 to 0.91 points and an
80%-power MDE of about 2.0 to 2.3 points. With 240 held-out questions D's PASS
probability at 0.70 falls to 0.887. Coverage of the kappa6 interval was 0.83 to
0.91 at nominal 0.90, disclosed as slightly liberal. I6's 80-question minimum
corresponds to a within-question AUC standard deviation of about 0.035.

Seeds for interpretation: the main stage is one generation pass (each question
has six seeded draws); the three split seeds re-fit and re-score on CPU and are
the registered sensitivity analysis. No GPU work is repeated across seeds; the
uncertainty that matters (questions and families) is in the bootstrap.

## GPU-second accounting rule

1. Ground truth per job: (EndTime minus StartTime) x allocated GPUs from
   `scontrol show job`, captured as the job leaves the queue (`sacct` is
   disabled on this host). Every job is counted: smoke, P0, every G-decode
   shard, G-extraction, every retry and every failed attempt. The overlay build
   is reported separately as infrastructure GPU time; the weight fetch is a
   CPU job.
2. One fixed engine configuration for every generation job: bf16, one H100,
   gpu_memory_utilization 0.90, max_model_len 40,960, max_num_seqs 256,
   max_num_batched_tokens 16,384, prefix caching on.
3. The extraction pass is its own job, charged in full and counted once; every
   selector variant shares it. Gate fitting and grading run on CPU and are
   reported as CPU-seconds.
4. Attribution inside a generation job (for the later 2x2, not for any line):
   each engine step's time is split into a weight share (W/BW) divided equally
   among running requests and a KV share proportional to each running
   request's context; prefill chunks are charged by tokens. The attributed sum
   plus fixed overhead (engine start, CUDA graph capture, drain tail) is
   compared with the whole-job total and the residual is reported and charged
   pro rata. The fitted per-trace function τL + β(PL + L²/2) and its error
   against G's measured total are reported (prediction P5).
5. Reported views: GPU-seconds per trace, per question and per thousand
   generated tokens; token counts; prefix-cache hits; batch occupancy over
   time. Utilisation counters are recorded and not used (2609.12923).
6. Timing noise: P0 against G throughput on comparable traffic is reported; the
   host's measured run-to-run noise (probe v2: 0.80 to 2.71%) sets the
   tolerance for equal-cost statements in the later 2x2.

## Compute caps (D22 counting)

- Smoke: 0.25 GPU-h (fixed). P0: 1.0 GPU-h (fixed).
- G-decode cap = 1.2 x the high projection for the chosen workload and N.
- G-extraction cap = 1.2 x [32 traces' measured mean time scaled to all G
  traces by (2 x 6.95e9 x T + 294,912 x T²), at 0.8 times P0's measured MFU] +
  0.05 GPU-h.
- Admission: smoke + P0 + G-decode cap + G-extraction cap ≤ 8.0 GPU-h. The 1.2
  factor and the formula are fixed by this file before P0 runs and are not
  revisited after any measurement (D22).
- Expected use (S2, central, 800 questions at a mean of 6,000 tokens): smoke
  about 0.1, P0 about 0.33, G-decode 3.19, G-extraction 0.38; about 4.0 GPU-h.
  N = 800 is admissible up to a mean thinking length of about 6,300 tokens at
  CV 0.75, and some N of at least 560 up to about 7,700.
- A job that reaches its cap stops; G processes families in seeded random order,
  so the completed held-out set stays random; only complete questions enter;
  I6 still applies.

## Infrastructure failures and exclusions

- A request that fails is retried once with the same seed; a second failure
  marks the draw missing (not wrong); questions with fewer than six completed
  draws are excluded from every line and counted.
- After an engine crash a fresh job resumes from the checkpoint (at most two
  resumes per job, each counted against the same cap); a third crash ends that
  job with INCONCLUSIVE_INFRA.
- A smoke failure stops the registration before P0; a fix is a code change
  reviewed under D7, and whether it is material is decided before re-running
  (a material change is a new experiment id).
- A job that would exceed the host rule (an S1a VM or GPU job appears) is not
  submitted; a running gate job is not preempted for S1a under this file's
  authority (the program decides).

## Data rights

Problem statements and model outputs stay on the host or in the private
archive (`~/repos/cotcodec-private`), never in this public repository, which
receives ids, dataset revisions, statement and answer SHA-256, labels, lengths,
scores and metrics. Compilation licences (MIT, Apache-2.0) do not cover the
underlying problems (MAA, HMMT, AoPS and others). NC-licensed and gated sources
are excluded. Model weights are not redistributed.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the CPU doctor node recovers known
   parameters from synthetic pools; I3, I4 and I7 check the pipeline on real
   data; graders cross-checked on 200 items.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot with its
   version history in the bundle; OpenReview items are labelled abstract-only.
3. Hallucinated experimental result: no number in this file is a result; S1 and
   S2 are labelled simulations and estimates with their scripts and outputs.
4. Shortcut reliance: pooled AUC is never a line; the floor line exists
   because length and vote share predict correctness.
5. Bug reframed as insight: an instrument failure gives INSTRUMENT_FAIL, not a
   finding.
6. Methodology fabrication: every procedure here names its code path and is
   checked at the pre-freeze audit against the harness.
7. Frame-lock: the registration states the likely outcomes in advance
   (below) and treats STOP_REDUNDANT and INCONCLUSIVE as acceptable results.

## Owner's prior forecast (not a decision input)

P(PASS_D) about 0.7, P(PASS_F) about 0.35, P(PASS_S | feasible) about 0.5,
P(STOP_HARM) below 0.05, P(INFEASIBLE) about 0.25, P(GO) about 0.1 to 0.2.
Most likely verdicts: INCONCLUSIVE with F indeterminate, or STOP_REDUNDANT.

## Freeze procedure

After the prerequisites and a fresh pre-freeze audit, and after Kevin accepts
the design decisions:

```bash
uv run python scripts/preregister.py freeze c3-selection-allocation-gate-v1 program/preregistrations/c3-selection-allocation-gate-v1.md
uv run python scripts/preregister.py verify c3-selection-allocation-gate-v1
```

## Design decisions (for the owner's acceptance)

1. Scope is Stage 0 only; the 2x2 needs its own gauntlet and a D24 ruling.
2. Model Qwen3-8B at revision b968826d, thinking mode, recommended sampling, max_tokens 32,768.
3. Registry amendment and full weight fetch under D1, after S1a.
4. Generation in the cu129 vLLM overlay; extraction in the research image.
5. Fixed engine configuration for every generation job (section "GPU-second accounting rule", item 2).
6. Six draws per question for every question.
7. Candidate strata A1 to A6 as listed; code excluded.
8. Family = connected component over provenance keys and near-duplicate links; at most 25 questions per family.
9. 50/50 family split within stratum; seed 42 governs, 43 and 44 are sensitivity.
10. P0: 120 training-family questions, 2 draws, cap 1.0 GPU-h; P0 questions never enter G.
11. Workload rule: eligibility tau_s ≥ 0.05 and at least 10 completed P0 questions; equal allocation; drop the costliest stratum while at least 3 remain.
12. N between 560 and 800 in steps of 40 by the cap rule.
13. Cap formula: 1.2 x high projection; smoke 0.25 and P0 1.0 fixed; sum at most 8.0 GPU-h.
14. INFEASIBLE when no admissible workload exists; no cut below 560 questions.
15. Answer position: the token before the first token inside the last boxed answer after the final end-of-thinking marker.
16. Draws without an answer position count wrong for accuracy and kappa6 and are excluded from AUCs.
17. Gate: standardised L2 logistic; layer grid of 9 and C grid of 3 chosen by grouped CV log loss within training families.
18. Floor features as listed, including the vote share.
19. Line D at 0.60 on the pooled within-question AUC, three-way.
20. Line F: GO needs L90 above 0; STOP below 0.02 upper bound.
21. Line S on kappa6 with line 0.10, replacing the dossier's statistic; raw statistic and pi_mid identified set reported.
22. Line H on the gate-weighted vote; STOP when its upper bound is below 0.
23. CASE argmax reported, not decision-bearing.
24. 90% family-cluster percentile bootstrap, B = 2,000.
25. Instrument gates I1 to I7 with the stated thresholds.
26. Memorisation probes on every question; sensitivity only.
27. Benchmark-exposed exclusions (MATH-500 test ids, AIME 2024 and later).
28. Grader: math-verify primary, strict cross-check, 200-item adjudicated audit.
29. GPU-second accounting rule items 1 to 6.
30. Prefix-consumption curves for k = 1 to 6 in seeded draw order.
31. Retries, crash restarts and cap-hit handling as listed.
32. Data rights: ids and hashes only in the public repository.
33. The CPU doctor orx node as the first executable pilot.
34. Owner's prior forecast recorded before any data.
