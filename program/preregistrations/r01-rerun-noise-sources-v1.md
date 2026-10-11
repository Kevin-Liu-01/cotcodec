# r01-rerun-noise-sources-v1: where S1a's greedy rerun disagreement starts (first step)

**Status: DRAFT.** Not frozen, no ledger row, not admitted. Written on 2026-10-11 by the R01
gauntlet's single owner (a Claude agent) on branch `gauntlet/r01-noise-sources`. Its GPU stage
(P0 and Stage B, at most 4.22 cap-GPU-h, 3.47 without their conditional jobs) is under the 8 GPU-h line of D20/D22, but under D24 and D70
it runs only after Kevin's admission ruling, whatever the gauntlet scores. The CPU-lane stages
(A1, C) run only after a freeze and a pre-freeze audit. Stage A0 has run (section 5.1).

**Experiment id:** `r01-rerun-noise-sources-v1` (new). **Proposal:**
`program/proposals/2026-10-11-r01-rerun-noise-sources.md`. **Claim scope:** `systems-pipeline`
(a measurement of an evaluation stack's noise sources). There is no architecture claim and no
retrofit claim.

Every number in this file is for Qwen3.5-4B under H-OSW-fixed on S1a's stack (D53's certified
action path, this host, the L0-fixed lane, V = 20), labelled "not externally anchored".

## 0. What this registers, and what it does not

Registered: Stage A (A0, run; A1, region census from fresh captures), Stage C (open-loop
replay of S1a's recorded actions, CPU lane, 0 GPU-h) and Stage B (identical-input replay
through the serving engine: a request-level factorial of observation perturbation by serving
configuration, GPU, no VMs), with their decision rules and caps.

Not registered: any closed-loop agent episode. The slate's closed-loop arms A0/A1 (clock live
against clock masked under S1a's serving, R = 3, 678 episodes, about 2.2 cap-GPU-h) are
dropped from this step (section 3.4, simulation CL). A closed-loop Stage D crossing the clock
mask with deterministic serving is sketched in section 17 and needs its own registration.

## 1. Question

**Corrected question.** On S1a's stack, held fixed (H-OSW-fixed, greedy decoding with
temperature 0, top-p 0.9 and top-k −1 as registered, 15 steps, 2,048 output tokens with
thinking passed back, the 60 s and 20 s settles, the prompt date pinned to 2026-10-08, the
guest clock live, vLLM v0.31.0 with prefix caching, `--max-num-seqs 256`,
`--max-num-batched-tokens 8192`), for Qwen3.5-4B on the 113-task pool:

1. Under S1a's serving configuration, how often does a byte-identical step request get a
   different greedy reply (text, and parsed IR), and how does that compare with a
   deterministic reference configuration (batch 1, prefix cache off)? Which serving channel
   carries it: prefix-cache hit against miss, or batch composition?
2. Under the deterministic reference, how often does a request that differs only in the
   on-screen clock's pixels (or only in the other time-varying regions Stage A1 finds) get a
   different reply? How often under S1a's serving (the interaction cell)?
3. Given fixed actions, how often does the environment alone change the screen at a step, or
   the final verdict?
4. Where do two reruns' step-1 screenshots differ (Stage A1's region census)?

**What was wrong with the slate's version** (the renewal dossier's R01 entry, and the three
discovery cells of this gauntlet):

- It asked for additive "parts" of D_w. The records show the sources are individually
  sufficient to start a divergence that later steps amplify (section 2), so additive shares
  are not identified. This version measures per-source **sufficiency hazards** at the step
  where divergence starts, and their interaction, and predicts D_w under each removal.
- Its NOT_CLOCK reading was unreachable at R = 3 on 113 tasks, and misleading when it fired
  (simulation CL: under no masking effect, the slate's NOT_CLOCK fires with probability 0.218,
  by chance). It is restated at the request level as CLOCK_INERT (section 10.3), which is
  reachable (probability 0.99 at a true hazard of 0.01).
- Stage A's pixel diff and Stage B's replay of "recorded step requests" assumed screenshots
  and request bodies S1a never kept (O1). Stage A0 runs on the hashes S1a kept; Stage A1 and
  Stage C capture fresh images; Stage B rebuilds requests from Stage C's captures and S1a's
  recorded replies.
- It motivated R01 with D69's variance shares; D72 (ii) corrects them (section 2.3).
- It priced Stage B at 0.3-0.5 GPU-h; batch-1 decode dominates, and the registered caps are
  computed in section 11.

## 2. Facts fixed before any new data

### 2.1 S1a's records (Stage A0, run on 2026-10-11)

Stage A0 is the records-only census of all 1,808 S1a episodes. It ran as orx run
`83ee815a-426a-4b94-a93f-cc1277972d76` (node `ff110047`, branch
`orx/r01-stage-a0-records-census`, commit `ca3cdbf`; `ORX_RESULT kind=cpu-doctor
direction=r01-rerun-noise-sources exit=0`). Its receipt is byte-identical to the committed
`program/evidence/2026-10-11/r01-stage-a0/census.json` (SHA-256 `5568bc7f...`). Inputs: the
hashes-only per-step table `s1a-step-digests.jsonl.gz` (SHA-256 `91f84843...`), derived from
the 3,616 host step and reply logs, each checked against the committed per-job host listings.
These are post hoc descriptions of S1a's data and enter no decision rule here; they fix the
predictions in section 3.

| Census item | Count | Share (Wilson 95%) |
|---|---|---|
| Within-session pairs with byte-identical step-1 screenshots (and requests) | 19 of 904 | 2.1% |
| Between-session pairs with identical step-1 screenshots | 0 of 1,808 | 0 |
| Natural replays: identical step requests (19 at step 1, 5 at step 2, 3 at step 3) whose reply text differs | 16 of 27 | 0.59 (0.41-0.75) |
| ... whose parsed IR differs | 2 of 27 | 0.07 (0.02-0.23) |
| Step 1, identical request: reply text differs / IR differs | 12 of 19 / 1 of 19 | 0.63 (0.41-0.81) / 0.05 (0.01-0.25) |
| Step 1, different request: reply text differs / IR differs | 763 of 885 / 269 of 885 | 0.86 (0.84-0.88) / 0.30 (0.27-0.34) |
| Outcome discordance, identical step-1 request / different | 2 of 19 / 90 of 885 | 0.105 (0.03-0.31) / 0.102 (0.08-0.12) |
| Identical-start pairs whose IR sequences never diverge | 2 of 19 | 0.105 |
| Pairs with identical IR sequences (within and between sessions): verdict discordant | 0 of 227 (59 size-task units) | exact one-sided 95% upper bound 1.31% per pair, 4.95% per unit |
| ... whose checker-input digests differ (saved files and registry carry timestamps) | 162 of 227 | 0.71 |
| Clearly same-minute pairs (estimated capture at least 5 s from a minute boundary) whose step-1 screenshots differ | 10 of 25 | 0.40 (0.23-0.59) |
| ... by domain: LibreOffice and GIMP / Thunderbird, VS Code, multi_apps | 10 of 17 / 0 of 8 | |
| Different-minute pairs with identical step-1 screenshots | 0 of 869 | 0 |
| D_w, 4B H-OSW-fixed (113 tasks, binarized raw verdicts) | 27 of 226 | 0.119 (0.083-0.168) |
| Within-session pairs whose IR sequences are identical through step 1 / 2 / 3 / 15 | | 0.70 / 0.48 / 0.34 / 0.086 |

The mean completion of the natural-replay requests is 275 tokens, so a reply-text change rate
of 0.59 implies a constant per-token flip hazard of about 0.0033, at the low end of the
0.3-1.3% batch-induced flip rates of 2605.30218. Where the two replies differ, they share a
common prefix of 4 to 1,046 characters (median share of the shorter reply about 0.45) and then
part (`derive-report.json`).

### 2.2 What the records already answer, and what they cannot

- **Serving numerics are active** on S1a's stack: identical requests get different reply
  text more often than not. But the 27 natural replays are selected (near-simultaneous
  dispatch, so probably whole-prompt prefix-cache hits), n is small, and no deterministic
  reference exists, so the floor is unknown.
- **The clock's own effect is not observable** in the records: every pair whose screenshots
  differ also differs in time of dispatch, load and whatever else varies.
- **Environment outcome noise given actions is small on a selected subset**: 0 of 227, skewed
  to short, successful episodes (mean 7.8 steps, 77% success, 182 of 227 ended by
  `terminate_success`).
- **The clock is not the only varying region**: 10 of 25 clearly same-minute pairs differ,
  all in LibreOffice and GIMP tasks, consistent with a caret's blink phase or an animation.
  Hashes cannot locate the region.
- **Redundancy**: identical step-1 inputs did not lower outcome discordance (2 of 19 against
  90 of 885) and delayed IR divergence by about one step (17 of 19 still diverged).

### 2.3 Variance shares (D72 (ii))

Under the design study's calibrations that pass its extended check (fit-pool, ρ_b = 0 and the
4B-zero refit), rerun noise is 21-27% of S1a's outcome variance on the probability scale;
task-by-harness variance is about 4% at 9B and at most 1% at 4B. D69's 20-33% and 3-4% are
fit-base's shares and are not used. At 4B, the model R01 studies, rerun variance is at least
about 20 times the task-by-harness variance.

## 3. Mechanism and predictions

### 3.1 Mechanism (M)

Each S1a request carries the full history of earlier replies (thinking included) and
screenshots, so the first difference anywhere, a decoded token or a pixel, makes every later
request differ. Rerun disagreement is therefore a divergence process with an absorbing first
divergence and a "kick" hazard per step from several sources: (s) serving numerics on
identical inputs (batch composition; on Qwen3.5's Gated DeltaNet hybrid layers, a prefix-cache
hit that resumes from a block-aligned recurrent-state checkpoint against a full prefill);
(c) the minute digits of the guest's top-bar clock; (o) other time-varying screen regions;
(e) environment execution given actions. If each source alone has a per-step hazard large
enough that almost every pair diverges within a few steps, the sources are redundant: removing
one leaves D_w where it is, and D_w is set by q, the verdict discordance of pairs whose
trajectories diverged, not by which source started the divergence. Only removing every active
source freezes trajectories, and then reruns repeat one draw.

### 3.2 Predictions, each with its falsifier

| # | Prediction (basis) | Falsified if |
|---|---|---|
| P1 | SERVING_SUFFICIENT: under S1a's configuration, h_s (reply text differs between two passes of the same request) has a 95% lower bound above 0.20 (A0: 0.59) | SERVING reads PARTIAL or INERT |
| P2 | DET_OK: under batch 1 with the prefix cache off, 0 of 320 replica pairs differ (2609.04748: 0 of 800 at batch 1, cache off, on dense models) | DET reads NEAR or UNATTAINABLE |
| P3 | CLOCK_SUFFICIENT: under the deterministic reference, h_c (clock-box-only swap) has a 95% lower bound above 0.20 | CLOCK reads PARTIAL or INERT |
| P4 | At the IR level, h_c(IR) ≥ h_s(IR) (A0: step-1 IR differs 0.30 when inputs differ, 0.05 when identical) | the paired 95% upper bound of h_c(IR) − h_s(IR) is below 0 |
| P5 | MULTI_REGION: in A1, the Wilson 95% lower bound of the share of cross-boot step-1 pairs differing outside the clock box is above 0.20 (A0: 0.40) | A1 reads CLOCK_ONLY or UNRESOLVED |
| P6 | ENV_BOUNDED: open-loop replay changes the verdict between two replays on fewer than 3% of episodes (A0: 0 of 227) | C reads ENV_MATERIAL or ENV_UNRESOLVED |
| P7 | Under the default condition, the per-step share of byte-identical clock-masked screenshots between two replays has a 95% upper bound below 0.95 (caret or animation); under blink-off plus the mask its lower bound is at least 0.95 | either half fails |
| P8 | For Stage D (not tested here): with live serving, masking the clock moves closed-loop D_w by less than 2 pp (step-kick model with A0: predicted 10.2% to 10.0%) | Stage D's interval excludes ±2 pp |
| P-K6 | A frozen (deterministic plus masked) stack does not narrow a K = 113 two-arm contrast at one rerun per arm (simulated width ratio 1.002); at four reruns per arm it doubles the width (2.00) | Stage D measures a shrink above 10% at one rerun |

M is falsified if P1 and P3 both fail with INERT readings (neither source kicks at the
request level), or if Stage D later shows that removing one sufficient source alone changes
D_w by more than 2 pp.

### 3.3 Readings and what each licenses

- REDUNDANT (SERVING and CLOCK both SUFFICIENT): attribution is a per-step sufficiency
  statement. No source "owns" a share of D_w; removing either alone is predicted not to move
  it (P8); a stack's greedy floor is a property of the policy and task set (q) wherever at
  least one source is active.
- SINGLE_SOURCE (one SUFFICIENT, the other INERT): the sufficient source is the trigger, and
  removing it is predicted to freeze trajectories up to the environment's and other regions'
  hazards (Stage C and A1).
- NEITHER (both INERT): M is falsified at the request level; divergence comes from other
  regions or the environment (B2o, C).
- PARTIAL cases are reported with their intervals; no attribution is made from them.

### 3.4 Why no closed-loop arm in this step

Simulation CL (`power-r01.json`): the slate's closed-loop design under live serving with no
masking effect, the records' prediction, reads CLOCK_DOMINANT with probability 0.002 and its
NOT_CLOCK with probability 0.218 (chance), and the restated "upper bound below half of D_w"
NOT_CLOCK with 0.78. That last reading would mean "the clock is not necessary given live
serving noise", which the request-level factorial measures directly for about 0.4 GPU-h
instead of 2.2 cap-GPU-h. The identifying closed-loop design crosses the mask with a serving
configuration verified to be deterministic; whether one exists for Qwen3.5 on vLLM v0.31.0 is
Stage B's first gate.

## 4. Design overview and order

| Stage | What | Where | GPU-h (cap) | Gate before it |
|---|---|---|---:|---|
| A0 | Records-only census of S1a | Mac, CPU | 0 | done |
| A1.0 | Audit of the 113 tasks' configs and checker code paths for wall-clock reads | Mac, CPU | 0 | freeze |
| A1 | Fresh step-1 captures, region census, clock box and mask fixed | host CPU lane | 0 | freeze; pre-freeze audit |
| C | Open-loop replay of all 452 4B H-OSW-fixed S1a episodes, twice, two frames per step | host CPU lane | 0 | A1's region file committed |
| B-build | Request corpus rebuilt from C's captures and S1a's replies | Mac or host CPU | 0 | C complete |
| P0 | Timing probe and bitwise self-test | 1 H100 | 0.25 (+0.25 conditional) | Kevin's admission |
| B | J1-J4 | 1 H100, sequential | 3.22 (+0.50 conditional) | P0 within its rule |

All host jobs are Slurm jobs through the project's submitters (CPU-lane jobs as in S1a; GPU
jobs through `scripts/submit_docker_research_job.py`: dry run, test-only, submit). No two R01
jobs overlap, and none overlaps another workflow's job (one host; D71's rule).

## 5. Stage A

### 5.1 A0 (run)

`scripts/run_r01_stage_a0_doctor.py` (standard library, CPU, model-free) with
`tests/test_r01_stage_a0_doctor.py`. Reproduce: `python3 scripts/run_r01_stage_a0_doctor.py
--output OUT.json` (byte-identical to the committed census), or the orx node above. The digest
table is rebuilt from a read-only copy of the host logs with
`program/evidence/2026-10-11/r01-stage-a0/derive_digests.py --logs DIR` (it refuses any file
whose SHA-256 differs from the committed host listings).

### 5.2 A1.0 task audit

Read the config and the checker function(s) of each of the 113 tasks (OSWorld at `b138d348`)
for reads of the wall clock or date (`datetime.now`, `date.today`, `time.time`, `strftime`
without a fixed argument, shell `date`). A task whose checker or postconfig reads the clock is
excluded from Stage C's verdict estimands and reported separately; Stage B is unaffected. The
asset check found no config reading the clock (the one regex hit, `185f29bd`, is a fixed
expected date); checker code paths are unaudited.

### 5.3 A1 captures

For each of the 113 tasks: four fresh boots in the S1a lane (image `fe8d9a5e`, qcow2
`6bf667a8` read-only, V ≤ 20), the task's setup exactly as S1a's driver runs it, keyboard
warm-up, the 60 s settle, then four screenshots at t0, t0 + 0.6 s, t0 + 1.2 s and t0 + 61 s
(t0 + 61 s is always in a different minute). Boots b1 and b2 run under the default condition
(S1a's guest configuration); boots b3 and b4 run with the guest cursor blink disabled
(`gsettings set org.gnome.desktop.interface cursor-blink false`, set before the settle).
Boot order is a seeded permutation (seed 42) of the 452 boots. Every raw PNG and its processed
bytes (`harness/q2_stage1/agents.process_image`, run in S1a's runner environment) stay on the
host run root; the repository receives SHA-256 lists and the census counts only.

**Clock box.** Fixed from b1's t0 against t0 + 61 s pairs before any census statistic is
read: the bounding rectangle, in screen pixels, of the differing pixels inside the top bar's
centre segment, pooled over tasks, padded by 2 px. It is committed as `a1-regions.json` with
the top bar's background colour (the mask fill) before Stage C's analysis or Stage B's corpus
build. If the differing pixels are not confined to one rectangle of at most 2% of the screen,
A1 stops and reports.

**Region census.** Pixel-difference components (8-connected) of each pair, classified as
inside the clock box; caret-like (width at most 3 px, height 10-40 px, present in t0 against
t0 + 0.6 s of one boot); or other.

### 5.4 A1 statistics and readings

- **Primary census statistic** s_nc: over the 113 cross-boot default pairs (b1 t0 against b2
  t0), the share with any differing pixel outside the clock box. MULTI_REGION if its Wilson 95%
  lower bound is above 0.20; CLOCK_ONLY if its Wilson 95% upper bound is below 0.20;
  UNRESOLVED otherwise. Operating characteristics (exact binomial, `power-r01.json` A1_cen):
  P(MULTI_REGION) is 0.31 at a true share of 0.25, 0.76 at 0.30 and 0.998 at 0.40;
  P(CLOCK_ONLY) is 0.84 at 0.10 and 0.024 at 0.20.
- Secondary: same-boot t0 against t0 + 0.6 s and t0 + 1.2 s (blink phase), and the same under
  blink-off; the caret-like share of non-clock components; cross-boot identity after the clock
  mask, default and blink-off (b3 t0 against b4 t0).
- **K1 restated.** "Not removable": if under blink-off plus the clock mask the cross-boot
  step-1 identity share has a Wilson 95% upper bound below 0.90, the available observation
  controls cannot make step-1 inputs identical. Stage D's frozen arm is then predicted
  unattainable and is not proposed; the localization is reported. Stages B and C still run.

## 6. Stage C: open-loop replay (environment)

**Population.** All 452 S1a episodes of 4B under H-OSW-fixed (113 tasks x 4 reruns), minus
any task A1.0 excludes.

**Procedure per replay.** Fresh VM in the S1a lane at V = 20 (the host load S1a ran under);
setup, warm-up and the 60 s settle as S1a; then for each recorded step k: capture frame f0 (the
screenshot S1a's driver takes at step k) and frame f1 0.6 s later; sleep the step's recorded
`latency_s` minus the time spent on f1 (so the interval between actions matches S1a's); execute
the recorded IR through the certified executor; after the last step, the 20 s settle, the live
checker, the final-state capture and offline rescoring in the metric image, all as S1a. A
replay executes exactly S1a's recorded steps, including a terminal action. Each episode is
replayed twice (r1, r2) in the default condition; r1 and r2 of an episode fall in different
halves of a seeded schedule (seed 42), so they are about an hour apart. **Conditional C-blink**
(runs if A1 reads MULTI_REGION and caret-like components are at least half of the non-clock
components): one episode per task (seed 43), replayed twice under blink-off.

**Infrastructure.** S1a's loss rules apply (one re-queue). If more than 2% of replays end as
infrastructure losses, Stage C reports INFRA and its readings do not fire.

**Estimands** (unit: episode or step; cluster: task):

- e_rr (primary): share of episodes whose binarized verdict (y = 1 iff the live score is 1.0,
  S1a's registered outcome) differs between r1 and r2.
- e_ro (secondary): verdict differs between r1 and the original S1a record (adds time of day,
  session and model-in-the-loop timing).
- o (primary for P7): per (episode, step), whether f0's processed screenshot is byte-identical
  between r1 and r2, (i) raw and (ii) after the clock mask applied to both raw PNGs before
  processing; the per-step identity share and the share of episodes identical at every step.
- Secondary: f0 against f1 identity per step (the share of steps captured while something was
  changing); normalized checker-input digests with timestamp fields stripped by rules fixed in
  advance: ODF `meta.xml` (`meta:creation-date`, `dc:date`, `meta:editing-duration`,
  `meta:editing-cycles`), OOXML `docProps/core.xml` (`dcterms:created`, `dcterms:modified`) and
  `docProps/app.xml` (`TotalTime`), and `registrymodifications.xcu` and `prefs.js` items whose
  names contain a time or date token.

**Readings (K2 restated).** With zero discordant episodes: ENV_BOUNDED (the exact one-sided
task-level 95% upper bound, 1 − 0.05^(1/113) = 0.026, is below 0.03). Otherwise, by a
task-cluster percentile bootstrap (2,000 resamples, seed 42): ENV_MATERIAL if the 95% lower
bound is above 0.02 (report a material environment floor and read Stage D net of it);
ENV_BOUNDED if the upper bound is below 0.03; ENV_UNRESOLVED otherwise. Operating
characteristics (`C_env`): P(ENV_BOUNDED) is 1.00 at e = 0, 0.92 (0.85 if concentrated in a
tenth of tasks) at e = 0.01, 0.35 at e = 0.02; P(ENV_MATERIAL) is 0.90 (0.51 concentrated) at
e = 0.05 and 1.00 (0.85) at e = 0.08.

**Observation readings (P7).** OBS_STABLE if the masked per-step identity share has a 95%
lower bound of at least 0.95 (task-cluster bootstrap); OBS_UNSTABLE if its upper bound is
below 0.90; otherwise OBS_PARTIAL. Read separately for default and (if run) blink-off. Under
the step-kick model, a per-step identity of 0.99 over 12.5 steps leaves 88% of trajectories
identical and a predicted frozen-regime D_w of 1.3%; 0.95 leaves 53% and 5.3% (`PRED`).

## 7. Stage B: identical-input replay (serving) with observation swaps

### 7.1 Request corpus

- 40 episodes drawn from the 369 4B H-OSW-fixed S1a episodes with at least 8 steps: at most
  one per task, stratified by domain in proportion to the pool, seed 42. Requests: steps 1-8 of
  each, n = 320 (mean S1a prompt 11,875 tokens, mean completion 376 tokens). The P0 probe uses 5
  further episodes drawn the same way with seed 43 (40 requests), disjoint from the corpus.
- Each step-k request is rebuilt by the frozen H-OSW-fixed client (code of record `d5f5798`,
  prompt date 2026-10-08) driven by a stub engine that returns S1a's recorded reply for steps
  1..k−1, with the screenshots of Stage C replay r1 (frame f0) of that episode. The bodies (JSON
  with base64 images) are stored on the host run root with their SHA-256; the repository
  receives the digests.
- **Fidelity check.** In J1's first pass, the engine's prompt token-id digest of each request
  must equal S1a's recorded `prompt_ids_sha256` for that step (text and image-placeholder
  counts; pixels are not covered). Failing requests are excluded from every arm and counted. If
  more than 10% fail, Stage B stops before any estimand is read and the rebuilder is repaired
  under a registered deviation.
- **Variants** of each request: *clock swap* (every image's clock-box pixels replaced by the
  clock-box pixels of the same step's frame f0 from replay r2, about an hour later, so a
  different minute, then processed); *mask* (every image's clock box filled with A1's
  background colour, then processed); *other-region swap*, conditional on MULTI_REGION (the
  newest image replaced by frame f1, 0.6 s later; requests whose f0 and f1 straddle a minute
  boundary are skipped and counted). Swaps and masks act on raw PNGs before `process_image`.

### 7.2 Engine configurations

All on S1a's engine image (overlay `sha256:10327c70...` over
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`,
vLLM v0.31.0 at `db9527a4`), model Qwen3.5-4B at `851bf6e8` with receipt `75ebfc53`, bf16,
`--seed 42`, `--max-model-len 131072`, `--max-num-batched-tokens 8192`, S1a's
`--limit-mm-per-prompt` and `--generation-config vllm`. Sampling is S1a's registered
H-OSW-fixed sampling plus `"logprobs": true, "top_logprobs": 5` in every Stage B request (identical in every arm; S1a requested no log-probabilities, disclosed).

| Config | Flags beyond the shared ones | Purpose |
|---|---|---|
| E-det | `--max-num-seqs 1 --no-enable-prefix-caching`; one request in flight | deterministic reference |
| E-c1 | `--max-num-seqs 1 --enable-prefix-caching`; `VLLM_SERVER_DEV_MODE=1` for `/reset_prefix_cache` | cache hit against miss at batch 1 |
| E-s1a | S1a's argv exactly (`--max-num-seqs 256 --enable-prefix-caching`) | S1a's serving |
| E-nc | S1a's argv with `--no-enable-prefix-caching` | batch composition without the cache |

### 7.3 Arms and protocol

| Arm | Config | Requests | Protocol |
|---|---|---|---|
| B0a, B0b | E-det | corpus, 2 passes | interleaved with B2, B4 (and B2o) in one seeded order (seed 42); batch 1 |
| B2 | E-det | clock-swapped corpus | as above |
| B4 | E-det | masked corpus | as above |
| B2o (conditional) | E-det | other-region-swapped corpus | as above |
| B5 | E-c1 | corpus | per request (seeded order): reset the prefix cache, send (miss), send again at once (whole-prompt hit to the last block boundary) |
| B1 pass 1-3 | E-s1a | corpus | per pass: reset the cache; 20 streams, 2 episodes each, steps in order; think time per request exponential with mean 11.9 s, so mean in flight is about 3.7 as in S1a (bridge samples 3.5-3.7); stream assignment, start offsets and think times seeded 42, 43, 44 |
| B3 | E-s1a | clock-swapped corpus | one pass with pass 1's schedule (seed 42), paired with B1 pass 1 |
| B6 pass 1-2 | E-nc | corpus | as B1, seeds 42 and 43 |

The engine's running-request count is sampled every second in J3 and J4 and compared with
S1a's (descriptive). In B1, requests carry S1a's recorded earlier replies, so the cache path
differs from S1a's, where the earlier reply's KV came from decode: B1 measures batched,
prefix-cached serving at S1a-like load, not S1a's exact cache history (disclosed).

Replies are parsed by the frozen H-OSW-fixed parser; reply text is the full response field as
S1a logged it (thinking included); IR equality uses S1a's `ir_sha256` definition. For every
differing pair the first differing token index and the reference reply's top-1 minus top-2
log-probability margin at that index are recorded.

### 7.4 Estimands

Unit: request; cluster: episode (40). Each at the text and the IR level.

| Estimand | Comparison |
|---|---|
| h_floor | B0a against B0b |
| h_s (primary serving) | B1 pass 1 against pass 2 (pairs 1-3 and 2-3 secondary) |
| h_c (primary clock) | B2 against B0a |
| h_cs (interaction cell) | B3 against B1 pass 1 |
| h_m | B4 against B0a |
| h_o (conditional) | B2o against B0a |
| h_cache | B5 warm against cold |
| h_batch | B6 pass 1 against pass 2 |
| interaction | h_cs − [1 − (1 − h_s)(1 − h_c)], descriptive |

## 8. Units, clustering and missing data

Stage C clusters by task (113); Stage B by episode (40); A1 by task. A request that errors or
times out after S1a's attempt rule is missing in every arm of that request (complete-case by
request); more than 5% missing in any arm voids that arm's reading. Fractional checker scores
are binarized as registered (y = 1 iff score == 1.0) and reported beside.

## 9. Statistics

- Proportions: Wilson 95% for descriptions; exact one-sided 95% bounds for zero events.
- Stage B readings: episode-cluster percentile bootstrap of the request-level mean
  (2,000 resamples, seed 42); paired differences (P4, interaction) resample episodes and keep
  each request's pair.
- Stage C readings: task-cluster percentile bootstrap (2,000 resamples, seed 42); exact
  task-level bound at zero events.
- Simulations behind every threshold: `power-r01.json` (seeds 42, 43, 44, each block run once
  per seed and averaged).

## 10. Decision rules

### 10.1 P0 gate (before J1-J4)

P0 runs the 40 probe requests three times on E-det and once more on E-det without `logprobs`.
- Any reply-text difference among the 80 replica pairs (pass 2 and 3 against pass 1): rerun P0
  once as P0' with `VLLM_BATCH_INVARIANT=1` added to E-det (conditional cap). J1 uses whichever
  of E-det and E-det-BI shows 0 differences; if neither, J1 runs on E-det and the DET reading
  decides labelling.
- A difference between the `logprobs` and no-`logprobs` passes: Stage B drops `logprobs`
  (margins are then not reported).
- **Timing:** if P0's measured per-request time times any job's request count, plus lead and
  start, exceeds that job's registered cap, that job is not submitted; the registration is
  amended before it runs. Caps are never exceeded.

### 10.2 DET (K3 restated)

On B0a against B0b, k of 320 text pairs differ: DET_OK if k = 0 (exact one-sided 95% upper
bound 0.93%); DET_NEAR if 1 ≤ k ≤ 6; DET_UNATTAINABLE if k ≥ 7 (one-sided 95% Clopper-Pearson
lower bound above 1%). Operating characteristics (exact binomial): P(DET_OK) is 1.00 at
p = 0, 0.73 at 0.001, 0.20 at 0.005, 0.04 at 0.01; P(DET_UNATTAINABLE) is 0.04 at 0.01, 0.46
at 0.02 and 0.85 at 0.03. With differences clustered by episode (beta-binomial, ICC 0.2),
P(DET_OK) at p = 0.005 rises to 0.39, so a DET_OK reading bounds the per-request rate, not the
per-episode rate (episode-level bound at 0 of 40: 7.2%). Under DET_UNATTAINABLE the serving
part is not identified: text-level clock estimands are labelled "clock or engine, not
separated" and are read at the IR level net of h_floor(IR).

Under DET_NEAR, every reading in 10.3 is applied to h − h_floor (paired by request).

### 10.3 SERVING, CLOCK and the restated NOT_CLOCK (K5)

On h_s and on h_c (net of h_floor under DET_NEAR):
- SUFFICIENT if the bootstrap 95% lower bound is above 0.20 (text) / 0.02 (IR);
- INERT if the upper bound is below 0.05 (text) / 0.01 (IR);
- PARTIAL otherwise.

**K5 restated:** CLOCK_INERT at both levels stops the pixel line (no Stage D clock arm).

Operating characteristics (40 episodes x 8 requests, episode logit SD 0.5 and 1.0,
`B_read`): text SUFFICIENT with probability 0.82-0.94 at a true 0.30 and 1.00 at 0.40 or
more, 0.02 at 0.20; text INERT 0.99 at 0.01, 0.44-0.49 at 0.03, 0.05-0.06 at 0.05; IR
SUFFICIENT 0.67-0.75 at 0.05 and 0.98-0.99 at 0.08; IR INERT 0.83-0.84 at 0.002 and 0.17 at
0.01.

Joint readings: REDUNDANT, SINGLE_SOURCE, NEITHER as in section 3.3.

### 10.4 Mask (K4 restated for this step)

MASK_HEAVIER if the paired 95% lower bound of h_m − h_c is above 0.10 (masking perturbs replies
more than a clock tick does). K4's closed-loop check (A1-type masking moves 4B success outside
±5 pp) belongs to Stage D.

### 10.5 Channels (secondary)

h_cache and h_batch are reported with intervals. If h_cache's lower bound exceeds h_batch's
upper bound, the label CACHE_CHANNEL; the reverse, BATCH_CHANNEL; otherwise none. No other rule
reads them.

### 10.6 Stage A1 and Stage C

Sections 5.4 and 6 (K1 and K2 restated).

### 10.7 K6 as a registered prediction

P-K6 (section 3.2). It is computed in `power-r01.json` (K6): at one rerun per arm the width
ratio of a frozen to a live stack is 1.002 (no shrink); at two and four reruns per arm,
1.41 and 2.00. Under a frozen stack, each (task, arm) keeps one draw, so the 21-27% rerun
share (D72 (ii)) would reappear as apparent task-by-arm variance, about 20 times the 4B
task-by-harness share. R01's payoff is attribution and portability of floors, not power.

## 11. Compute and caps

Rule (the design study's realized-cost rule, adopted here explicitly, as D69 left to the
owner): job cap (min) = ceil(3 lead + 2 engine start + W x 1.2 x 1.05), W priced at the high
per-request price (`caps-r01.json`, from S1a's per-step tokens and latencies). Prices: batch 1
without cache 2.55 s central, 3.70 s high per request (prefill at 14,519 tok/s central and half
that high, from S1a's step-1 time to first token; decode 4.6 and 5.5 ms per token); a warm cache
hit 1.78 / 2.17 s; a loaded pass 16 x (latency + 11.9 s).

| Job | Arms | W high (min) | Cap (min) | Cap GPU-h |
|---|---|---:|---:|---:|
| P0 | 40 x 3 on E-det | 7.4 | 15 | 0.25 |
| P0' (conditional) | as P0 with `VLLM_BATCH_INVARIANT=1` | 7.4 | 15 | 0.25 |
| J1 | B0a, B0b, B2, B4: 4 x 320 | 79.0 | 105 | 1.75 |
| J1o (conditional) | B2o: 320 | 19.7 | 30 | 0.50 |
| J2 | B5: 320 cold + 320 warm | 31.3 | 45 | 0.75 |
| J3 | B1 x 3 and B3: 4 loaded passes | 16.2 | 26 | 0.43 |
| J4 | B6 x 2 loaded passes | 9.0 | 17 | 0.28 |
| **Total** | | | **253** | **4.22** (3.47 without the conditional jobs) |

The 8 GPU-h line (D20/D22) is read on the sum of caps: 4.22 < 8. Physical estimate 2.2 GPU-h
central, 2.9 high, plus P0'. CPU lane: A1 13.8 VM-h; C 43.4 VM-h; C-blink 10.8 VM-h
(conditional); about 3.4 h of wall at V = 20. The CPU lane at V = 20 takes about 122 of 208
CPUs, so A1 and C never overlap another workflow's CPU jobs (R03's K2 executor, R04).

Seeds: [42, 43, 44] (corpus 42, probe 43, schedules 42-44, bootstraps 42). Engine `--seed 42`.
No unseeded randomness.

Checkpoints and resume: Stage B jobs write each reply as it completes (JSONL, fsync); a fresh
job resumes at the first missing (arm, request) and the analysis is order-free, so a resumed
job equals an uninterrupted one by construction. Stage C replays are independent episodes with
S1a's re-queue rule.

## 12. Controls

- Replica floor (B0b) for every request-level estimand; P0 and P0' as the engine's bitwise
  self-test.
- The clock swap uses real renderings of the same top bar (from r2), not synthetic digits.
- The mask arm (B4) separates "this region changed" from "this region was blanked".
- B3 against B1 pass 1 shares the schedule, so h_cs is paired with h_s's first pass.
- Stage C's r1 against r2 removes the model and time of day; r1 against the original adds them.
- Negative control: prompt-id fidelity check against S1a's recorded digests.
- Positive control for A1's census: t0 against t0 + 61 s of one boot must differ inside the
  clock box in every task (a task where it does not is flagged and its clock box checked).

## 13. Seeds and randomization

Section 11. The order of variants within J1 is one seeded permutation of all (request,
variant) items, so drift over the session cannot align with an arm.

## 14. Leakage, integrity and failure modes

- No outcome of any new stage is known before the freeze. A0's records were read to design
  the study; that is disclosed, and A0 enters no rule.
- The clock box and the normalization rules are fixed and committed before Stage C's analysis
  and Stage B's corpus build.
- Integrity gate (ARS `ai_research_failure_modes.md`): implementation bugs (the A0 doctor
  reproduces itself byte for byte and has a test; Stage B's rebuilder has the fidelity check);
  hallucinated citations (every quantitative prior claim is in the proposal's claim registry
  with its read level); hallucinated results (only A0 has run; its receipt is hash-matched);
  shortcut reliance (text-level identity can saturate under batching, so IR-level readings
  are registered beside it); bug reframed as insight (a DET failure is labelled, never read
  as a finding about the clock); methodology fabrication (every threshold has its simulation);
  frame lock (the slate's additive frame was dropped after the kill-shot cell's evidence).

## 15. Data rights, safety and repository hygiene

- OSWorld tasks (Apache-2.0) at `b138d348`; Qwen3.5-4B (Apache-2.0) at `851bf6e8`; vLLM
  (Apache-2.0); S1a's records are the program's own.
- Screenshots and request bodies contain renderings of OSWorld task files whose own licences
  vary; they stay on the host run root, as S1a's did, and the repository receives hashes,
  counts and region rectangles only.
- No training, no download beyond what S1a already holds, no outward action, offline VMs, no
  model-generated code executed on GPUs (IR actions run in VMs through the certified executor,
  as in S1a). The blink-off condition is a guest setting used in measurement replays and
  captures only; any closed-loop use needs a delta certification of D53's scope.
- Host: one node; read-only checks before every submission; no job overlaps another workflow's
  job.

## 16. Freeze prerequisites, sign-offs and deviations

Before a freeze: the gauntlet's honest exit or score; a pre-freeze audit of this file; the
A1.0 audit; the corpus and capture code with tests; Slurm dry runs and test-only runs of every
job. Kevin's admission ruling for P0 and Stage B (D24, D70). A material change after the
freeze is a new version with a new id; deviations are disclosed in the results.

## 17. Not registered: Stage D sketch

A closed-loop 2x2 (clock mask x serving: E-s1a against the configuration DET_OK selects),
R = 2 within one session, on the tasks A1 shows can be made observation-identical, with IR
trajectory identity as the primary estimand (observable on every task, unlike verdict
discordance on the 67 tasks 4B never solves) and D_w and the ±5 pp success check (K4)
secondary. It is proposed only if DET reads OK or NEAR, CLOCK is not INERT and K1 is not
triggered. Its cost depends on batch-1 throughput at V = 20 and is sized after Stage B. It
needs its own registration; P8 and P-K6 are its pre-stated predictions.

## 18. Decisions left to the program owner and to Kevin

1. Adopting the realized-cost cap rule (section 11) instead of S1a's c_proj.
2. Whether the blink-off condition may be used in measurement replays (it is a guest setting,
   outside the agent runtime D53 certifies).
3. Admission of P0 and Stage B (D24, D70).
4. Whether Stage D is wanted at all if Stage B reads REDUNDANT.
