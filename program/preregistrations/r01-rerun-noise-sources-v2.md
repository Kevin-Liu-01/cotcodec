# r01-rerun-noise-sources-v2: where S1a's greedy rerun disagreement starts (first step, onset-step factorial)

**Status: DRAFT.** Not frozen, no ledger row, not admitted. Written on 2026-10-11 by the R01
gauntlet's single owner (a Claude agent) on branch `gauntlet/r01-noise-sources`, as the D75
repair of `r01-rerun-noise-sources-v1` (wave 1, score 58). v1 is superseded and left unedited.
Its GPU stage (P0 and Stage B, at most 4.82 cap-GPU-h with conditional jobs, 4.08 without) is
under the 8 GPU-h line of D20/D22, but under D24 and D70 it runs only after Kevin's admission
ruling, whatever the gauntlet scores. The CPU-lane stages (A1, C) run only after a freeze and a
pre-freeze audit. Stage A0 has run (section 5.1).

**Experiment id:** `r01-rerun-noise-sources-v2` (new). **Proposal:**
`program/proposals/2026-10-11-r01-rerun-noise-sources.md`. **Claim scope:** `systems-pipeline`
(a measurement of an evaluation stack's noise sources). No architecture or retrofit claim.

Every number is for Qwen3.5-4B under H-OSW-fixed on S1a's stack (D53's certified action path,
this host, the L0-fixed lane, V = 20), labelled "not externally anchored".

## 0. What this registers, and what it does not

Registered: Stage A (A0, run; A1.0, a task audit; A1, fresh captures with one open-loop step),
Stage B (an onset-step factorial of serving configuration by clock region by non-clock regions on
fixed first-step requests, primary, and the same at step 2, secondary; GPU, no VMs), Stage C
(open-loop replay of S1a's recorded actions, CPU lane, 0 GPU-h), their decision rules and caps,
and the two-stage model's D_w predictions for a later closed-loop Stage D.

Not registered: any closed-loop agent episode (section 18 sketches Stage D).

What changed from v1, and why, is the proposal's "Changes after wave 1" table. In short:
Stage B's primary estimands are now the per-source sufficiency hazards **at the divergence-onset
step**, sized on S1a's 226 within-session pairs; the step-kick model is replaced by a two-stage
model validated on S1a before any GPU; every cap is repriced from S1a's realized step costs, with
loaded passes simulated as the slowest of 20 lanes; P0 no longer waits on Stage C; the drivers
are built and CPU-tested against a fake engine.

## 1. Question

**Corrected question.** On S1a's stack, held fixed (H-OSW-fixed, temperature 0, top-p 0.9,
top-k −1, 15 steps, 2,048 output tokens with thinking passed back, the 60 s and 20 s settles, the
prompt date 2026-10-08, the guest clock live, vLLM v0.31.0, `--max-num-seqs 256`,
`--max-num-batched-tokens 8192`, prefix caching on), for Qwen3.5-4B on the 113-task pool:

1. At the step where S1a's rerun pairs start to diverge (step 1 in 205 of 226 within-session
   pairs), how often is each candidate source **alone** enough to change the greedy reply text,
   and the parsed action: serving numerics on byte-identical requests (S1a's configuration under
   S1a-like load against a verified-deterministic reference), the on-screen clock's pixels alone,
   and every other screen difference between two boots alone? How do the sources combine?
2. Does the request-level replay reproduce S1a's own closed-loop step-1 divergence when every
   source is active?
3. The same at step 2 (secondary; 19 of the remaining 21 pairs start there).
4. Given fixed actions, how often does the environment alone change the screen at a step, or the
   final verdict (Stage C)?
5. Where do two boots' step-1 screenshots differ (Stage A1's region census)?

What the answer is for: D_w is set by whether some source changes the reply text at the onset
step, and then by the post-onset rate at which actions part and by how often diverged pairs end
with different verdicts (section 3). The onset hazards decide which sources must be removed for
reruns to stop diverging, and the two-stage model turns them into predicted D_w for each removal.

## 2. Facts fixed before any new data

### 2.1 S1a's records (Stage A0, run on 2026-10-11)

A0 is the records-only census of all 1,808 S1a episodes: orx run
`83ee815a-426a-4b94-a93f-cc1277972d76` (node `ff110047`, branch
`orx/r01-stage-a0-records-census`, commit `ca3cdbf`; `ORX_RESULT kind=cpu-doctor
direction=r01-rerun-noise-sources exit=0`), receipt byte-identical to
`program/evidence/2026-10-11/r01-stage-a0/census.json` (SHA-256 `5568bc7f...`), inputs the
hashes-only table `s1a-step-digests.jsonl.gz` (SHA-256 `91f84843...`). These are post hoc
descriptions; they enter no decision rule. v1's section 2.1 table stands, with one correction:
the comparison "2 of 19 identical-start pairs discordant against 90 of 885" is **not evidence**
of redundancy. 15 of the 19 pairs sit in size-harness-task units whose four episodes all agree,
and the task-composition expectation is 2.2 discordant (wave 1's identification refuter and
reviewer 1). It is dropped as evidence.

### 2.2 Where S1a's divergence starts (4B, H-OSW-fixed, 226 within-session pairs)

Recomputed from the A0 table (`compute/repair-d75/power-r01-v2.json`, block PRED):

| Quantity | Value |
|---|---|
| Step-1 screenshots differ | 221 of 226 |
| First reply-text difference at step 1 / 2 / 3 / 4 / later | 205 / 19 / 1 / 1 / 0 |
| First IR difference at step 1 / 2 / 3 / 4 / 5 / 6+ / never | 79 / 44 / 30 / 27 / 15 / 16 / 15 |
| IR identical through step 1 / 2 / 3 / 4 / 15 | 0.650 / 0.456 / 0.323 / 0.204 / 0.066 |
| D_w (binarized verdicts) | 27 of 226 = 0.1195 |
| q, verdict discordance of IR-diverged pairs | 27 of 211 = 0.128 (IR-identical pairs: 0 of 15) |
| q by IR-onset step 1 / 2 / 3 / 4+ | 8 of 79 / 4 of 44 / 7 of 30 / 8 of 58 |
| Intraclass correlation of a task's two step-1 pairs (all four size-harness groups) | text 0.06-0.42; IR 0.34-0.48 |

### 2.3 Variance shares (D72 (ii))

Under the design study's passing calibrations, rerun noise is 21-27% of S1a's outcome variance;
task-by-harness variance about 4% at 9B and at most 1% at 4B. D69's 20-33% and 3-4% are not used.

### 2.4 The two-stage model on S1a (`harness/r01/stepkick.py`)

Fitted by event counts on the 226 pairs: text-onset hazards κ1 = 0.907, κ2 = 0.905 (19 of 21),
κ3+ = 0.667 (2 of 3); IR at the onset step π = 0.363; post-onset IR rate ρ = 0.323 per step
(constant); joint-end hazards τ_k of IR-identical pairs as observed. The model's IR-identity
curve is 0.671, 0.454, 0.308, 0.208 for steps 1-4 against the observed 0.650, 0.456, 0.323,
0.204 (largest gap over 15 steps 0.020), N = 0.063 against 0.066, and D_w = (1 − N) q = 0.1199
against 0.1195. With ρ and π taken from the other three size-harness groups instead (leave one
group out), the largest gap is 0.069 and D_w 0.116. The same in-sample fit gives gaps of 0.045-
0.067 on the other three groups. D_w's sensitivity to the onset hazard (κ_k = κ for every k,
π = 0.363): κ = 0.907 → 0.120; 0.63 → 0.118; 0.50 → 0.115; 0.30 → 0.103; 0.20 → 0.088; 0.10 →
0.060; 0.05 → 0.036; 0 → 0. D_w moves materially only when no active source keeps the onset
hazard above about 0.3.

## 3. Mechanism and predictions

### 3.1 Mechanism (M), two stages

Each S1a request carries every earlier reply (thinking included) and screenshot. (i) **Onset.**
With identical histories, a step's reply text differs with a hazard from several sources: (s)
serving numerics on identical inputs (batch composition; on Qwen3.5's Gated DeltaNet hybrid
layers, a prefix-cache hit that resumes from a block-aligned recurrent-state checkpoint); (c) the
pixels of the guest's top-bar clock; (o) every other screen difference between two boots (caret
blink phase, animation, loading or layout state); (e) environment execution given actions, which
acts from step 2 on. The first text difference is absorbing, because the reply is passed back.
(ii) **Action divergence.** At the onset step the parsed action differs with probability π; after
it, while actions still agree, they part at a rate ρ set by the policy and the tasks, not by the
source that started the onset. Redundancy: if at least two sources are each sufficient to change
step-1 text with a high hazard, removing one leaves the onset at step 1 or 2 and D_w unchanged;
only removing every text-level kicker freezes trajectories, and then reruns repeat one draw
(P-K6).

### 3.2 Predictions, each with its falsifier

Readings are those of section 10; "step 1" cells are on 226 pairs, task-clustered.

| # | Prediction (basis) | Falsified if |
|---|---|---|
| P1 | SERVING (identical step-1 requests, S1a's configuration under S1a-like load) reads SUFFICIENT at the text level (A0: 12 of 19 natural replays) | SERVING text reads PARTIAL or INERT |
| P2 | DET_OK: 0 of 226 step-1 replica pairs differ on E-det (2609.04748: 0 of 800 at batch 1, cache off, dense models) | DET reads NEAR or UNATTAINABLE |
| P3 | CLOCK (clock region alone, E-det) reads SUFFICIENT at the text level (no data; a few hundred changed pixels in a 1920 x 1088 image) | CLOCK text reads PARTIAL or INERT |
| P3' | NON-CLOCK (other regions alone, E-det) reads SUFFICIENT at the text level (A0: 10 of 25 same-minute pairs differ outside the clock) | NON-CLOCK text reads PARTIAL or INERT |
| P4 | At the IR level, SERVING reads MINOR (A0: 1 of 19) and NON-CLOCK reads MAJOR; CLOCK does not read MAJOR | any of the three readings is the opposite extreme (SERVING MAJOR, NON-CLOCK MINOR, CLOCK MAJOR) |
| P-VAL | VAL_PASS: the all-sources live cell reproduces S1a's step-1 divergence (205/226 text, 79/226 IR) within ±0.15 | VAL_FAIL |
| P5 | MULTI_REGION in A1 (A0: 10 of 25) | CLOCK_ONLY or UNRESOLVED |
| P6 | ENV_BOUNDED in Stage C (A0: 0 of 227 identical-IR pairs discordant) | ENV_MATERIAL or ENV_UNRESOLVED |
| P7 | Masked per-step frame identity between replays: upper bound below 0.95 by default, lower bound at least 0.95 under blink-off | either half fails |
| P8 | For Stage D (not tested here): each single removal's predicted D_w (section 10.9, from that arm's measured cells) is within 2 pp of the live arm's; under the records' redundancy scenario the model gives «P:P8RANGE» | Stage D's paired interval for any single removal excludes the predicted Δ by more than 2 pp |
| P-K6 | A frozen stack does not narrow a K = 113 two-arm contrast at one rerun per arm (width ratio 1.002) | Stage D measures a shrink above 10% at one rerun |

**M is falsified in this step** if the joint text reading is SINGLE_SOURCE or NEITHER (no
redundancy at the onset step), or if VAL_FAIL shows the request-level onset is not S1a's. Both
are reachable: INERT has probability «P:INERT_TEXT_001» at a true text hazard of 0.01 and
SUFFICIENT «P:SUFF_TEXT_030» at 0.30 (section 10.3); VAL_FAIL has probability «P:VALFAIL_IR020»
when the true IR rate is 0.20 instead of 0.35.

### 3.3 Readings and what each licenses

- REDUNDANT: at least two sources alone change step-1 text with a lower bound above 0.20. D_w is
  predicted not to move under any single removal (P8); a greedy floor is a property of the policy
  and tasks wherever one such source is active.
- SINGLE_SOURCE: one source is the onset trigger; removing it is predicted to freeze trajectories
  up to the environment (Stage C) and the remaining hazards.
- NEITHER: no measured source starts the onset at the request level; M is falsified, and the
  environment (Stage C) or an unmeasured channel carries it.
- MIXED: reported with intervals; no attribution.
- The IR readings (MAJOR, MINOR) say which source alone reproduces S1a's first-action
  divergence; they feed π in the predictions.

### 3.4 Why no closed-loop arm in this step

Simulation CL (wave 1, re-run in `power-r01-v2.json`): under live serving with no masking
effect, the slate's closed-loop design reads CLOCK_DOMINANT with probability 0.002 and its
NOT_CLOCK with 0.218 (chance). The request-level factorial measures each source's sufficiency
directly; Stage D's closed loop needs a verified-deterministic configuration, which P0 and J1
establish or rule out.

## 4. Design overview and order

| Stage | What | Where | GPU-h (cap) | Gate before it |
|---|---|---|---:|---|
| A0 | Records-only census of S1a | Mac, CPU | 0 | done |
| A1.0 | Audit of the 113 tasks' configs and checker code paths for wall-clock reads | Mac, CPU | 0 | freeze |
| A1 | 678 fresh boots: frames, one open-loop step, clock box, census | host CPU lane | 0 | freeze; pre-freeze audit |
| B-build | Corpus and probe items from A1's frames and S1a's step-1 replies | Mac or host CPU | 0 | A1's region file committed |
| P0 | Bitwise self-test, logprob check, Mamba mode, prices, one loaded pass | 1 H100 | 0.45 (+0.38 conditional) | Kevin's admission |
| B | J1, J2, J3, J4 (+ J1b conditional) | 1 H100, sequential | 3.63 (+0.35 conditional) | P0's gates |
| C | Open-loop replay of the 452 4B H-OSW-fixed episodes, twice | host CPU lane | 0 | A1's region file committed |

Stage B no longer waits on Stage C: every Stage B request is built from A1's frames. Host jobs
are Slurm jobs through the project's submitters; no two R01 jobs overlap, and none overlaps
another workflow's job (one host; D71).

## 5. Stage A

### 5.1 A0 (run)

`scripts/run_r01_stage_a0_doctor.py` with `tests/test_r01_stage_a0_doctor.py`; reproduce with
`python3 scripts/run_r01_stage_a0_doctor.py --output OUT.json` (byte-identical), or the orx node.

### 5.2 A1.0 task audit

As v1 section 5.2: each task's config and checker code paths (OSWorld at `b138d348`) read for
wall-clock or date reads; a task whose checker or postconfig reads the clock leaves Stage C's
verdict estimands (reported separately); Stage B is unaffected.

### 5.3 A1 captures (`harness/r01/openloop.py`, mode `a1`)

For each of the 113 tasks, six fresh boots in the S1a lane (image `fe8d9a5e`, qcow2 `6bf667a8`
read-only, V ≤ 20), each with the task's setup exactly as S1a's runner runs it, the guard's
keyboard warm-up and the 60 s settle, on S1a's runner code (subclassed, unmodified):

| Boots | Condition | Frames | Use |
|---|---|---|---|
| b1, b2 (pair 1) | default | t0, t0 + 0.6 s, t0 + 1.2 s; then one open-loop step: S1a's recorded step-1 IR of the task's chosen episode, executed after its recorded latency from t0, and the step-2 frame f0 with f1 0.6 s later | step-1 and step-2 cells |
| b3, b4 (pair 2) | default | t0, t0 + 0.6 s, t0 + 1.2 s; b3 also t0 + 61 s | step-1 cells; b3's late frame is the positive control |
| b5, b6 (pair 3) | blink-off (`gsettings set org.gnome.desktop.interface cursor-blink false`, read back, before the settle) | t0, t0 + 0.6 s, t0 + 1.2 s | conditional J1b; blink-phase census |

The chosen episode (`requests.choose_episode`, seed 42) is, among the task's four 4B
H-OSW-fixed episodes with at least two steps and a non-empty, non-terminal, parse-clean step-1
IR, the one with the smallest SHA-256 of (seed, task, session, rerun). **Pair spacing:** the
lane's dispatch order is a seeded sequence (seed 42) in which each pair's second boot follows its
first by k positions, k drawn from S1a's within-session spacing distribution (A0_8: median
171 s, 90th percentile 695 s) divided by the lane's mean dispatch interval at V = 20, with k at
least the equivalent of 65 s, so that the clock label differs as in 869 of S1a's 904 pairs. The
realized gaps are recorded and reported against S1a's. A boot that ends as an infrastructure
loss is re-queued once under S1a's rule; a pair without both boots leaves the corpus (counted).

Every raw PNG stays on the host run root; the repository receives SHA-256 lists and counts.

**Clock box (wave 1 defect repaired).** Fitted to the **full extent of the clock label**, not to
the pixels a one-minute change moves: over every A1 frame, the bounding rectangle of the pixels
in the top bar's rows 0-31 and centre third whose colour differs from the bar's background
colour, padded by 4 px (`regions.fit_clock_box`). The hour digits are inside it whether or not
any pair crossed an hour. A1 stops and reports if the label touches the centre segment's edge in
any frame or the box exceeds 2% of the screen. The box and the background colour are committed
as `a1-regions.json` before the corpus is built or Stage C is analysed.

**Composite checks (per pair, before its requests enter the corpus;
`requests.check_composites`).** C (pair's first frame with the second's clock box) differs from
R only inside the box; O (second frame with the first's clock box) differs from R only outside
it; the two clock boxes differ (a pair whose boxes are pixel-identical leaves the clock cells,
counted); whether any pixel outside the box differs is recorded (a pair without one contributes
O = R, a true zero of the non-clock factor).

**Region census.** 8-connected pixel-difference components classified as inside the box,
caret-like (at most 3 px wide, 10-40 px tall) or other (`regions.census`).

### 5.4 A1 statistics and readings

- **Primary census statistic** s_nc: over the 226 default pairs (b1 t0 against b2 t0, b3 t0
  against b4 t0), the share with any differing pixel outside the clock box; task-cluster
  bootstrap (section 9). MULTI_REGION if the lower bound is above 0.20; CLOCK_ONLY if the upper
  bound is below 0.20; UNRESOLVED otherwise. Operating characteristics (`A1_cen`, ICC 0.45):
  «P:A1_TABLE».
- Secondary: same-boot t0 against t0 + 0.6 s and t0 + 1.2 s (blink phase), default and
  blink-off; the caret-like share of non-clock components; the positive control (b3's t0 against
  t0 + 61 s must differ inside the box in every task; a task where it does not is flagged).
- **K1 restated.** If under blink-off the cross-boot step-1 identity share outside the box has an
  upper bound below 0.90, observation controls cannot make step-1 inputs identical; Stage D's
  frozen arm is then not proposed. Stages B and C still run.

## 6. Stage C: open-loop replay (environment) (`harness/r01/openloop.py`, mode `stage-c`)

As v1 section 6, with two changes. (i) The replays r1 and r2 of an episode are dispatched as a
pair at S1a-like spacing (the A1 pair rule), not "about an hour apart". (ii) The masked frame
identity uses the full-label clock box. Per recorded step: frame f0 (the observation S1a's agent
saw), f1 0.6 s later, a sleep for the rest of the step's recorded latency, then the step's IR
through the certified executor; a step whose IR is empty captures no new observation; after
`terminate` (or the last step), the 20 s settle, the restart check, the live checker and the
capture, all S1a's code paths. Estimands and readings (e_rr, e_ro, o, the normalized
checker-input digests; ENV_BOUNDED, ENV_MATERIAL, ENV_UNRESOLVED; OBS_STABLE, OBS_PARTIAL,
OBS_UNSTABLE; K2) are v1's, with operating characteristics re-run (`power-r01-v2.json`, V1.C_env):
P(ENV_BOUNDED) is 1.00 at e = 0, «P:CENV_BOUNDED_001» at e = 0.01; P(ENV_MATERIAL) «P:CENV_MAT_005»
at e = 0.05. Stage C runs on the CPU lane independently of Stage B.

## 7. Stage B: the onset-step factorial (serving x clock x non-clock)

### 7.1 Request corpus (`harness/r01/requests.py`)

- **Step 1 (primary): 226 pairs on 113 tasks**, A1's boot pairs 1 and 2 of every task, matching
  S1a's 226 within-session pairs (113 tasks x 2), so the all-sources live cell is directly
  comparable with S1a's 205/226 and 79/226. For a pair (a, b) and the clock box, four requests:
  R = a, C = a with b's clock box, O = b with a's clock box, X = b.
- **Step 2 (secondary): 113 pairs**, pair 1 of every task: R2, C2, O2, X2 carry a's step-1 frame
  and the chosen episode's recorded step-1 reply, with the newest frame from the same 2 x 2 of
  a's and b's step-2 frames. Step 2's earlier reply is prefilled from text, whereas S1a's engine
  reached it by decode; exact-token replay can repeat itself without reproducing the live state
  (2607.28495), so step 2 is secondary and its cache path is disclosed. Step 1 carries no
  earlier reply and is free of this gap.
- **Probe items for P0 (40 step-1, 20 step-2)** use frames no corpus request uses: b4's t0 +
  1.2 s frame of 40 tasks (seed 43), and b1's t0 + 0.6 s frame, the recorded step-1 reply and b1's
  step-2 f1 frame for 20 tasks (seed 44).
- Each request is rebuilt by the frozen H-OSW-fixed client (code of record `d5f5798`, prompt date
  2026-10-08) driven by a stub engine returning the recorded reply; the body is
  `engine.EngineClient.body` plus `logprobs: true, top_logprobs: 5` in every arm (dropped
  everywhere if P0 shows they change outputs). Bodies stay on the host run root with SHA-256.
- **Fidelity (negative control).** vLLM's prompt token ids cover text and image-placeholder
  counts, not pixels: every cell's request must carry the reference's ids, and every rebuilt
  step-2 request's ids must equal S1a's recorded `prompt_ids_sha256` for that episode's step 2. P0
  checks the probe items first; in J1's first E-det pass a failing request leaves every cell
  (counted); more than 10% failing stops Stage B before any estimand is read.

### 7.2 Engine configurations

S1a's engine image (overlay `sha256:10327c70...` over
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`,
vLLM v0.31.0 at `db9527a4`), Qwen3.5-4B at `851bf6e8` (receipt `75ebfc53`), bf16, `--seed 42`,
`--max-model-len 131072`, `--max-num-batched-tokens 8192`, S1a's `--limit-mm-per-prompt` and
`--generation-config vllm`, `VLLM_SERVER_DEV_MODE=1` (for the cache-reset routes) in every
configuration.

| Config | Flags beyond the shared ones | Caches | Purpose |
|---|---|---|---|
| E-det | `--max-num-seqs 1 --no-enable-prefix-caching` | encoder cache reset before every request | deterministic reference |
| E-det-BI | E-det plus `VLLM_BATCH_INVARIANT=1` | as E-det | P0' fallback |
| E-c1 | `--max-num-seqs 1 --enable-prefix-caching` | prefix and encoder reset before each item's cold request | cache hit against miss |
| E-s1a | S1a's argv | prefix and encoder reset at every pass start | S1a's serving |
| E-nc | S1a's argv with `--no-enable-prefix-caching` | encoder reset at every pass start | batch composition without the cache |

Prefix caching switches Qwen3.5's Mamba cache mode to `align` (the program's own engine log,
`program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/a-442/probe/engines/real/engine.log`
line 11); P0 records each configuration's mode from its log. The serving factor (E-det against
E-s1a) is S1a's serving as a bundle (batch, cache hits, Mamba mode); J2 and J4 separate its
channels as a secondary.

### 7.3 Arms and protocols (`harness/r01/replay.py`)

| Job | Config | Protocol | Requests |
|---|---|---|---|
| J1 | E-det | `batch1`, one seeded order of every item (seed 42), encoder reset per request | step 1: R, R' (a replica of R), C, O, X on 226 pairs; step 2: R2, R2', C2, O2, X2 on 113 |
| J1b (conditional) | E-det | as J1 | blink-off pair 3: R'' = b5, O'' = b6 with b5's clock box, on 113 pairs |
| J2 | E-c1 | `coldwarm`: reset, send (cold), send again (warm) | R on 226 step-1 pairs |
| J3 | E-s1a | `loaded`, 20 lanes, think time exponential with mean 9.19 s (3.7 in flight at S1a's step-1/2 latency mix), schedules seeded 42-46 | pass 1: R + R2; pass 2: R + R2; pass 3: C + C2; pass 4: O + O2; pass 5: X + X2 |
| J4 | E-nc | as J3, seeds 47-48 | passes 1-2: R + R2 |

Every live cell compares pass 1's reply to R with another pass's reply, so every live comparison
is across two different seeded schedules (wave 1's schedule-sharing confound is gone). A loaded
pass is atomic: a cut pass is discarded and rerun whole from its start in a fresh job (a resumed
pass would run under different concurrency). Batch-1 arms resume at the first missing item. The
client-side in-flight count is sampled each second and reported against S1a's bridge samples
(3.5-3.7 mean, 15-17 maximum). Replies are parsed by the frozen H-OSW-fixed parser; reply text is
the full response (thinking included); IR equality uses S1a's `ir_sha256`; for every differing
pair the first differing token index and the reference's top-1 minus top-2 log-probability margin
there are recorded.

### 7.4 Estimands

Unit: a request pair; cluster: task. Each at the text and the IR level. Step 1 on 226 pairs; step
2 on 113 (the same cells with suffix 2).

| Cell | Serving | Clock | Non-clock | Comparison | Role |
|---|---|---|---|---|---|
| h_floor | det | same | same | J1 R against R' | DET |
| **h_s** | live | same | same | J3 R (pass 1) against R (pass 2) | **primary: serving alone** |
| **h_c** | det | differs | same | J1 R against C | **primary: clock alone** |
| **h_o** | det | same | differs | J1 R against O | **primary: non-clock alone** |
| h_x | det | differs | differs | J1 R against X | remove serving |
| h_cs | live | differs | same | J3 R (1) against C (3) | remove non-clock |
| h_os | live | same | differs | J3 R (1) against O (4) | remove clock |
| **h_X** | live | differs | differs | J3 R (1) against X (5) | **primary: VAL (all sources)** |
| h_cache | batch 1 | same | same | J2 cold against warm | channel (secondary) |
| h_batch | loaded, no cache | same | same | J4 pass 1 against pass 2 | channel (secondary) |

Descriptive: interactions (each two-source cell minus the independence prediction
1 − (1 − h_a)(1 − h_b)), and Owen's closed and total indices from the 2^3 table.

## 8. Units, clustering and missing data

Stage B clusters by task (113); Stage C by task; A1 by task. A request that errors or times out
after S1a's attempt rule is missing in every cell of its pair (complete case by pair); more than
5% missing in a cell voids that cell's reading (`estimators.compare`). Fractional checker scores
are binarized (y = 1 iff score == 1.0) and reported beside.

## 9. Statistics (`harness/r01/estimators.py`)

- Cell hazards: pooled share of differing pairs; 95% interval by task-cluster percentile
  bootstrap, 2,000 resamples, `numpy.random.default_rng(42)`. Under DET_NEAR, differences
  h − h_floor paired by request, same bootstrap.
- VAL: Stage B's X cell against S1a's own 226 pairs (per-task step-1 indicators from the A0
  table), the difference's interval from independent task bootstraps of both.
- Stage C and A1: task-cluster bootstrap; exact zero-event bounds where stated.
- Every threshold's operating characteristics are simulated with this code
  (`power-r01-v2.json`, seeds 42, 43, 44, 300 replicates per seed, task heterogeneity from S1a:
  ICC 0.2 for text, 0.45 for IR, sensitivity at 0.6).

## 10. Decision rules

### 10.1 P0 (`harness/r01/p0.py`)

E-det session: the 60 probe items three times with log-probabilities and once without, batch 1,
encoder reset per request. Then E-s1a: one loaded pass of the probe items.
- Any reply-text or completion-token-id difference among the 120 replica comparisons: P0' runs
  (E-det-BI, conditional cap). J1 uses whichever reference shows none; if neither, J1 runs on
  E-det and its DET reading labels every det cell.
- Any difference between the log-probability passes and the pass without: Stage B drops
  log-probabilities in every arm (margins not reported).
- The Mamba cache mode of each configuration (engine log) and the encoder-cache route's answer
  are recorded; a configuration whose cache-reset route does not answer 200 is not used.
- **Timing gate.** For each J job: batch-1 work projected as P0's measured 95th-percentile time
  per request by step times the job's request count; loaded work as the 95th percentile of the
  loaded-pass simulation with latencies resampled from P0's loaded pass; a job whose projection
  (lead, engine starts, x 1.2 x 1.05) exceeds its registered cap is not submitted and the
  registration is amended first. Caps are never exceeded.

### 10.2 DET (K3 restated)

On J1's step-1 R against R' (226 pairs): DET_OK if 0 differ (exact one-sided 95% upper bound
1.32%); DET_UNATTAINABLE if the one-sided 95% Clopper-Pearson lower bound exceeds 1% (k ≥ 6);
DET_NEAR otherwise. Exact operating characteristics: P(DET_OK) is 1.00 at p = 0, 0.80 at 0.001,
0.32 at 0.005; P(DET_UNATTAINABLE) «P:DET_UN_002» at 0.02 and «P:DET_UN_003» at 0.03. Step 2's
113 replica pairs are reported beside. Under DET_NEAR, det cells are read net of h_floor; under
DET_UNATTAINABLE, det cells are labelled "observation or engine, not separated" and read at the
IR level net of h_floor.

### 10.3 Source readings at the onset step (K5 restated)

On h_s, h_c, h_o (and every other cell, reported):
- text: SUFFICIENT if the lower bound is above 0.20; INERT if the upper bound is below 0.05;
  PARTIAL otherwise;
- IR: MAJOR if the lower bound is above 0.175 (half of S1a's natural 0.350); MINOR if the upper
  bound is below 0.117 (a third of it); PARTIAL otherwise.

Operating characteristics at step 1 (226 pairs, ICC 0.2 text, 0.45 IR; `B_cells`):
«P:CELLS_TABLE»

**K5 restated:** CLOCK INERT at the text level and MINOR at the IR level stops the pixel line
(no Stage D clock arm).

### 10.4 Joint reading

Over the text readings of h_s, h_c, h_o: REDUNDANT if at least two are SUFFICIENT; SINGLE_SOURCE
if exactly one is SUFFICIENT and the other two INERT; NEITHER if all three are INERT; MIXED
otherwise.

### 10.5 VAL (request-level replay against the closed loop)

h_X against S1a's 205/226 (text) and 79/226 (IR): VAL_PASS if both differences' 95% intervals
lie inside ±0.15; VAL_FAIL if either excludes 0 with a point difference above 0.10 in magnitude;
VAL_UNRESOLVED otherwise. Under VAL_FAIL, every attribution is labelled "request level only, not
transported to S1a's closed loop" and the D_w predictions of 10.9 are not registered for Stage D.
Operating characteristics (`VAL`): «P:VAL_TABLE»

### 10.6 Channels (secondary)

h_cache and h_batch with intervals; CACHE_CHANNEL if h_cache's lower bound exceeds h_batch's
upper bound, BATCH_CHANNEL for the reverse, otherwise none. No other rule reads them.

### 10.7 Stage A1 and Stage C

Sections 5.4 and 6 (K1 and K2 restated).

### 10.8 K6 as a registered prediction

P-K6 (section 3.2), from `power-r01-v2.json` (V1.K6): width ratio frozen/live 1.002 at one rerun
per arm, 1.41 and 2.00 at two and four.

### 10.9 The D_w predictions registered for Stage D (two-stage model)

For each removal arm A (live; remove serving: h_x; remove clock: h_os; remove non-clock: h_cs;
remove observation: h_s; remove serving and clock: h_o; remove serving and non-clock: h_c;
frozen: h_floor), the prediction is `stepkick.predict` with κ1 = A's step-1 text hazard, π = A's
step-1 IR hazard over its text hazard, κ_k = A's step-2 text hazard for k ≥ 2 (stationarity,
with the bracket κ_k≥3 over A's step-2 interval reported), and ρ, τ, q from S1a's 226 pairs.
Interval: 2,000 draws pairing Stage B task-bootstrap draws (tasks resampled jointly across
cells) with independent S1a task-bootstrap refits; the difference from the live arm uses the same
S1a refit in both arms, so q's uncertainty cancels. Under the scenarios of `power-r01-v2.json`
(PRED), the predicted Δ D_w of each arm is «P:PRED_TABLE»

These are predictions for Stage D, not readings of this step. D_w moves by more than a point only
when every remaining source's step-1 text hazard is low (section 2.4).

## 11. Compute and caps (`compute/repair-d75/caps-r01-v2.json`, `harness/r01/caps.py`)

Rule (the design study's realized-cost rule, adopted explicitly): cap (min) = ceil(3 lead + 2 x
engine starts + W x 1.2 x 1.05), W at the high price. Prices are arithmetic on S1a's realized
per-step records (4B H-OSW-fixed): step-1 latency mean 1.929 s, 95th percentile 2.650 s, prompt
3,427 tokens; step 2 2.401 s, 3.351 s, 5,766 tokens. Batch-1 request: latency plus a full
uncached prefill (14,519 tok/s central, 7,260 high) plus 0.05 s of reset: step 1 2.21 s central,
3.17 s high; step 2 2.85 s, 4.20 s. Warm hit: the latency (mean, 95th percentile). **Loaded
passes are simulated**: per pass a seeded deal of items to 20 lanes, latencies resampled from
S1a's step-1 and step-2 latencies (x 1.25 for high), exponential think times (mean 9.19 s) after
every item but a lane's last, a uniform start offset, and the pass ending at its slowest lane;
W is the 95th percentile of 20,000 draws (seed 42) plus 0.2 s of resets per pass. Wave 1 priced
J3 as one lane's mean and under-capped it (overrun probability 0.52-0.96).

| Job | Work central / high (min) | Cap (min) | Cap GPU-h | Arithmetic |
|---|---:|---:|---:|---|
| P0 | 10.72 / 15.52 | 27 | 0.450 | ceil(3 + 2 x 2 + 15.52 x 1.2 x 1.05) |
| P0' (conditional) | 9.70 / 14.05 | 23 | 0.383 | ceil(3 + 2 + 14.05 x 1.26) |
| J1 | 68.53 / 99.24 | 131 | 2.183 | ceil(3 + 2 + 99.24 x 1.26) |
| J1b (conditional) | 8.34 / 11.95 | 21 | 0.350 | ceil(3 + 2 + 11.95 x 1.26) |
| J2 | 15.61 / 21.93 | 33 | 0.550 | ceil(3 + 2 + 21.93 x 1.26) |
| J3 | 21.99 / 24.46 | 36 | 0.600 | ceil(3 + 2 + 24.46 x 1.26); 5 passes simulated: mean 1,320 s, 95th percentile 1,422 s (central), 1,468 s (high) |
| J4 | 8.79 / 10.18 | 18 | 0.300 | ceil(3 + 2 + 10.18 x 1.26) |
| **Total** | | **289** | **4.817** (4.083 without conditional jobs) | |

«P:OVERRUN» The 8 GPU-h line (D20/D22) is read on the sum of caps: 4.82 < 8. Physical estimate
2.66 GPU-h central. CPU lane: A1 678 boots, 20.5 VM-h central (S1a's 95.6 s mean overhead to the
first observation plus frames and the open-loop step), 25.6 high (its maximum, 122.5 s); Stage C
43.4 VM-h central, 54.7 high; C-blink 10.8 (conditional); about 4.6 h of wall at V = 20 (high).

Seeds: [42, 43, 44] for the simulations; corpus and episode choice 42; probe 43-44; J3 schedules
42-46, J4 47-48; bootstraps 42; engine `--seed 42`. No unseeded randomness.

Checkpoints and resume: batch-1 arms append each reply with fsync and a fresh job resumes at the
first missing item (order-free: encoder reset per request, prefix caching off); a loaded pass is
atomic (section 7.3); Stage C replays and A1 boots are independent episodes with S1a's re-queue.

## 12. Controls

- Replica floor (h_floor) for every det cell; P0 and P0' as the engine's bitwise self-test.
- The clock factor uses a second boot's real rendering of the same top bar; the non-clock
  factor uses the same boot pair's real other regions; composites are checked pixel by pixel.
- VAL ties the request level to S1a's closed loop.
- Stage C's r1 against r2 removes the model; r1 against the original adds time of day and the
  model loop.
- Negative control: prompt-id fidelity (all cells share ids; step 2 matches S1a's digests).
- Positive control: b3's t0 against t0 + 61 s differs inside the box in every task.

## 13. Seeds and randomization

Section 11. J1's order is one seeded permutation of every (pair, cell) item, so drift over the
session cannot align with a cell; J3's passes have distinct seeded schedules.

## 14. Leakage, integrity and failure modes

- No outcome of any new stage is known before the freeze. A0's records and S1a's onset counts
  were read to design the study; that is disclosed, and they enter only VAL (as the registered
  comparison values 205/226 and 79/226) and the two-stage model's S1a parameters.
- The clock box and the composite checks are fixed and committed before the corpus build and
  Stage C's analysis.
- Integrity gate (ARS `ai_research_failure_modes.md`): implementation bugs (every driver has CPU
  tests against fakes; the A0 doctor reproduces byte for byte; the rebuilder has the fidelity
  check); hallucinated citations (claim registry with read levels); hallucinated results (only A0
  has run); shortcut reliance (IR readings beside text; VAL against the closed loop); bug
  reframed as insight (a DET failure is labelled, never read as a clock finding); methodology
  fabrication (every threshold simulated with the registered code); frame lock (v1's pooled-step
  estimands and step-kick model dropped after review).

## 15. Data rights, safety and repository hygiene

As v1 section 15: OSWorld tasks Apache-2.0 at `b138d348`, Qwen3.5-4B Apache-2.0 at `851bf6e8`,
vLLM Apache-2.0; screenshots and request bodies stay on the host run root (hashes, counts and
region rectangles in the repository); no training, no new download, no outward action, offline
VMs, no model-generated code on GPUs. The blink-off condition is a measurement setting outside
the agent runtime D53 certifies (owner decision, section 19).

## 16. Code: what is built, and what remains

Built and tested on the development Mac's CPU (no model, no host contact):
`harness/r01/regions.py`, `requests.py`, `replay.py`, `p0.py`, `openloop.py`, `fake_engine.py`,
`caps.py`, `estimators.py`, `stepkick.py`, with `tests/test_r01_regions_requests.py`,
`tests/test_r01_replay_p0.py`, `tests/test_r01_openloop.py` and
`tests/test_r01_estimators_stepkick_caps.py` (the replay and P0 tests run against
`harness/r01/fake_engine.py`; the open-loop tests against S1a's fake guest and session).

Remaining before a freeze, CPU (Mac):
1. An R01 lane adapter: S1a's lane (`harness/q2_stage1/lane.py`, pinned by S1a's registration)
   hard-codes the S1a runner module, experiment id and ledger row. R01 needs a new module that
   runs `harness.r01.openloop` in the episode container, admits R01's own frozen registration,
   writes per-boot configs (mode, recorded steps, frame offsets, blink-off) and the A1 dispatch
   order with pair spacing; tested against the lane's fakes.
2. The corpus builder CLI (A1 frames and S1a's step-1 replies to the corpus JSONL and bodies,
   with the composite checks) and the Stage B report CLI (cells, readings, VAL, predictions)
   over the built functions.
3. The A1.0 audit.
4. Manifests: P0, P0', J1, J1b, J2, J3, J4 (`scripts/submit_docker_research_job.py`) and the A1
   and Stage C lane jobs.

Remaining, host side:
5. A container smoke of the engine image with the replay client over the bridge socket; Slurm dry
   runs and test-only runs of every manifest; provenance verification.
6. P0 itself: the real engine's bitwise self-test, log-probability check, Mamba modes,
   cache-reset routes and measured prices.
7. The blink-off setting's effect in the guest image (A1's read-back and blink-phase frames).
8. Kevin's admission for P0 and Stage B (D24, D70).

## 17. Freeze prerequisites, sign-offs and deviations

Before a freeze: the gauntlet's honest exit or score; a pre-freeze audit of this file; items 1-5
of section 16. A material change after the freeze is a new version with a new id; deviations are
disclosed in the results.

## 18. Not registered: Stage D sketch

A closed-loop 2 x 2 (clock mask x serving: E-s1a against the configuration DET_OK selects), R = 2
within one session, on the tasks A1 shows can be made observation-identical, with IR trajectory
identity as the primary estimand and D_w and the ±5 pp success check (K4) secondary; it tests
P8 and P-K6. It is proposed only if DET reads OK or NEAR, VAL passes, CLOCK is not INERT and
MINOR, and K1 is not triggered; sized after Stage B; its own registration.

## 19. Decisions left to the program owner and to Kevin

1. Adopting the realized-cost cap rule (section 11) instead of S1a's c_proj.
2. Whether the blink-off condition may be used in measurement captures and replays.
3. Admission of P0 and Stage B (D24, D70).
4. Whether Stage D is wanted if Stage B reads REDUNDANT.
