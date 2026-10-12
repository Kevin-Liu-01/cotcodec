# Preregistration: q2-stage1-successor-e-v1 (Q2 successor E: S1a's design on all 113 pool tasks with four new serving sessions per size)

**Status: DRAFT. Not frozen, no ledger row; no E episode and no E GPU job may run under it.
Open slots: TBD** (the status paragraph, which the freeze replaces whole with the wording of
section 25; the program's sign-off of section 21; G-E4's, G-E5's and G-E6's slots are filled).

- Drafted 2026-10-11 on branch `stage0/q2-successor-e` from `main` at `c0971a77`, by the
  single owner of successor E under decision D80 (iii) ("registered, audited before the freeze,
  frozen and run, for a decisive DR2 reading"). `main` at `746d60d2` (ledger row 18, D81, D82)
  was merged into the branch before the first pre-freeze audit's items were fixed (section 25).
- Built on D66 (a successor that only adds data needs a registration and a pre-freeze audit,
  not a gauntlet), D69 (E is the design study's best successor; S1b and the harness-scale
  question are closed) and D80 (iii) (Kevin's delegation: E runs).
- The design and its scenarios were chosen after S1a's readings (section 22, disclosure 1).

## 1. Identity

- **Experiment id:** `q2-stage1-successor-e-v1` (successor E of Q2 Stage S1a,
  `q2-stage1-rescoped-v1`).
- **Question:** Q2 (`program/questions/q2-calibrated-cua-instrument.md`), Stage 1.
- **What it measures.** S1a's registered estimands (S1a section 9), unchanged, in a new sample
  with more data: Qwen3.5-4B and Qwen3.5-9B on the two certified harnesses (H-OSW-fixed and
  H-GA), on all 113 tasks of S1a's eligible pool, in **four new serving sessions per size**
  with **one episode per (size, task, harness, session)**. It reads:
  - the harness main effect δ (H-GA minus H-OSW-fixed), pooled and per size;
  - X, the mean squared per-task harness effect, its task-specific part X_c and the harness
    share π per size, with π_small;
  - the between-session rerun floor D_b (six cross-session pairs per cell);
  - DR1, DR2, DR4 and DR5 and the predictions P1-P5, as S1a registered them;
  - the cost card of E's jobs.
- **Why.** S1a's registered outcome was DR2 Inconclusive and DR5 INCONCLUSIVE (D66). The
  design study (D66, D69; `program/evidence/2026-10-10/q2-next-step-design-study/README.md`)
  found that E makes DR2 decisive with probability 0.83-0.87 at S1a's estimates, within
  8 GPU-h by caps. D80 (iii) runs it.
- **Claim level.** Confirmatory for the registered estimands, decision rules and predictions,
  **for E's realized sessions** (four per size): every interval and test resamples or
  randomizes tasks and holds the sessions fixed (S1a section 9). **E is its own sample.** No E
  estimate, test, rule or prediction reads S1a's sessions. A joint reading with S1a is
  reported, as a description only (section 15).
- **Not in scope:** pooling with S1a in any registered reading; the observation factor; step
  caps other than 15; sampled decoding; models other than Qwen3.5-4B and 9B; S1b (closed by
  D69); the OpenCUA-7B anchor (unavailable, as in S1a).
- **Gauntlet.** None. E only adds data to S1a's design (D66, D80 (iii)): its caps total 406
  minutes (6.77 GPU-h), within 8 GPU-h, and it adds no factor, mechanism or estimand.
- **Inputs it builds on**, all frozen or committed:

  | Input | Status | Source |
  |---|---|---|
  | `q2-stage1-rescoped-v1` (S1a) | frozen, ledger row 16; ran complete (D66) | `program/preregistrations/q2-stage1-rescoped-v1.md`; `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md`; `program/evidence/2026-10-10/q2-stage1-analysis/` |
  | `q2-action-path-v2` and its addenda | frozen, ledger rows 13-15; attempt 1 accepted, N* = 32 (D53) | S1a G0 item 1 |
  | The design study | committed (D66, D69); repaired after its attack | `program/evidence/2026-10-10/q2-design-study/`, `program/evidence/2026-10-10/q2-next-step-design-study/` |
  | The D59 tooling | committed (D59, D61, D62) | `ops/s1a-analysis/` |
  | The checker-mutation adjudication (D81 run 2) | committed (D82); adjudicated by an isolated model on the owner's instruction (D80), not human-validated | `program/evidence/2026-10-11/q2-mutation-adjudication-v2/summary.json` |

- **Code revision.** Every E job runs from a read-only export of **E's freeze commit**, the
  commit that adds this file's ledger row and nothing else (S1a section 1's rule); the overlay
  for E's GPU halves is built from that commit (job OE, section 7).

## 2. What E decides, and what it does not

1. **DR2 for E's sessions** on the 113 tasks: Present, Near-equivalent or Inconclusive (S1a
   section 11, unchanged). Decisive with probability 0.83-0.87 at S1a's estimates (section 12).
   A Present reading would come from the X test, not from δ (P(p_δ ≤ 0.025) is 0.03-0.05), and
   would mean "a harness effect is present on some tasks, mostly at 9B, main or task-specific"
   (S1a section 10.1), not a main effect.
2. **DR5 for E's sessions**, against M = 0.13 (π_small) or 0.18 (π_9B when DR1 drops 4B).
   NO-GO with probability 0.23-0.54 at S1a's estimates; GO at most 0.03 for any design within
   8 GPU-h (section 12). Its consequence is section 13's.
3. **The between-session floor D_b** over four sessions (six cross-session pairs per cell), per
   size and pooled, and δ per session.
4. **DR1, DR4 and P1-P5**, as registered; P1 is not estimable in E (section 14).
5. **A cost card** for E's jobs (S1a section 9 item 10).

E does **not** measure: the within-session floor D_w or the session excess D_b − D_w (one
episode per session leaves no within-session pair); the common session share ρ; anything about
scale beyond S1a's screen; the observation factor.

## 3. What E keeps from S1a, and what it changes

E is S1a's design with more data. The table is the whole of the difference.

| Area | S1a (`q2-stage1-rescoped-v1`) | E |
|---|---|---|
| Models, revisions, engine (vLLM v0.31.0), engine flags, one engine per (size, session) job | S1a sections 4, 5.1 | unchanged: the same argv (`plan.engine_argv`, checked by the lane before dispatch) |
| Harnesses H-OSW-fixed and H-GA, prompts, parsers, layouts, upstream differences | S1a section 5.2, `design_diffs.md` | unchanged (`agents.py` unchanged) |
| Prompt date | pinned to Thursday, October 08, 2026 | unchanged: the same pinned date, so every E prompt has S1a's text |
| Screenshot only, 15 steps, thinking on, 2,048 output tokens, greedy decoding (temperature 0, top_p 0.9, top_k −1), settle 60 s and 20 s | S1a section 5.3 | unchanged |
| Action path, executor, IR, adapters | attempt 1 of `q2-action-path-v2` (D53) | unchanged |
| VM image, guest disk, VM settings, episode container (the metric image), OSWorld `b138d348`, file cache | S1a section 4 | unchanged |
| Episode definition, infrastructure losses, agent-caused events, the D53 (iii) observation rule and the postconfig carve-out (D56) | S1a sections 7.1-7.3 | unchanged (`driver.py`, `osworld_live.py` unchanged); counted per E session (section 8) |
| Episode records | schema `q2-stage1a-episode-v1`, sessions S1 and S2, reruns 1 and 2 | the same schema and fields; session labels E1-E4, rerun 1 (section 5.5) |
| Outcomes and checker corrections; flagged tasks | S1a section 8 | unchanged; one sensitivity added for D82's three gold-defect tasks (section 9) |
| Estimators (`estimators.py`), inference, rules (`rules.py`: DR0-DR5, P1-P5, M = 0.13 and 0.18) | S1a sections 9-12 | unchanged; read on E's array (sections 10, 11, 13, 14) |
| Seeds | 42, 43, 44 | 42 for every stream (section 16) |
| **Tasks** | a 32-task base by seeded draw, plus 81 extension tasks by a cost-based fill rule | **all 113 eligible pool tasks**, no draw, no fill rule (section 5.2) |
| **Sessions and reruns** | 2 sessions x 2 within-session reruns per size, 12 h apart | **4 new sessions (E1-E4) x 1 episode** per size, at least 12 h 5 min apart (section 5.3) |
| **Analysis sets** | primary: the 32-task base; secondary: base plus completed extension blocks | **primary: the 113 tasks**; registered secondary: S1a's 32 base tasks (section 5.6) |
| **Caps** | the remainder rule over 478 minutes, K from the card's high price (c_proj) | **per-job caps by arithmetic on S1a's realized cost**: realized price x 1.2 x 1.05 (section 7) |
| **Pre-freeze jobs** | O1, A0a (GPU) | none on a GPU; a CPU-only development smoke and a CPU GLMM run (G-E4, G-E5) |
| **Code** | `harness/q2_stage1/` | S1a's code unchanged, plus a thin layer `harness/q2_stage1e/` (section 23) |

## 4. Gates

### 4.1 Before any E GPU job

- **G-E1. Action-path acceptance.** S1a G0 item 1 holds unchanged: attempt 1 of
  `q2-action-path-v2` accepted (D53), N* = 32, so V = 20 with the sizes one after the other.
- **G-E2. S1a's code of record is unchanged.** Every file of S1a section 20 (both tables, 75
  files) has the SHA-256 S1a states; `tests/test_q2_stage1e_prereg.py` checks each one against
  the tree, so E runs S1a's frozen code.
- **G-E3. E's code is committed and tested on CPU** (section 23): `tests/test_q2_stage1e.py`
  (plan, records, lane, entry point, analysis, section 15 items) and
  `tests/test_q2_stage1e_prereg.py` (this file).
- **G-E4. Development smoke (CPU only, no GPU, pre-freeze).** E's lane and episode entry point
  had not run on the host when this file was drafted. Before the freeze, one CPU-only VM job
  runs `experiments/manifests/q2-stage1e/dev-smoke-v1.json` through
  `python3 -m harness.q2_stage1e.lane submit` from a read-only export of the draft commit: the
  scripted fake engine (S1a's dev-smoke-v1 script: a click, then `terminate(success)`), V = 1,
  the two dev-split tasks of S1a's smoke (job 978) under both harnesses, E's labels. It passes
  if all 4 slots end scored with records that E's `records.validate` accepts, the lane receipt
  holds no error, and offline
  rescoring (`rescore.py capture`) of the captured states matches the live score on every
  episode. A scored record with session `E1` shows that E's entry point ran: S1a's driver
  refuses that label at its final check, so it would leave no record. It touches no confirm
  task and runs no model. It does not reach the `e` purpose's own checks (prior jobs, the
  session gap, the engine argv and the Slurm limit), which CPU tests cover (section 22,
  disclosure 10). Result: **passed** (VM job 1206, 2026-10-11, 7 min 38 s, from the
  read-only export of the draft commit `8a23a483`; CPU only, no GRES; submitted with the Slurm
  queue empty, and the lane's snapshots saw no foreign job): 4 of 4 slots scored, all with
  session `E1`; every record is accepted by E's `records.validate` and refused by S1a's; the
  lane receipt holds no error (lane exit 0, no labelled container left). Each episode ran
  cold boot (18.3 s), setup (11.4 s), the warm-up, both settles, a click and `terminate`,
  `DesktopEnv.evaluate()`, the capture and teardown, in a slot of 113-114 s. Offline rescoring
  (CPU job 1208, the metric image, `rescore.py capture` unchanged) matched the live score on
  4 of 4, on the same state digests. Evidence:
  `program/evidence/2026-10-11/q2-stage1-successor-e/gates/` (`gates-check.json`)
- **G-E5. The registered GLMM on data of E's shape (CPU only, pre-freeze).** S1a's `glmm.R`
  was accepted on two sessions x two reruns (S1a G0 item 12, job 984). Before the freeze it
  runs, unchanged, in the pinned container (`s1a-cpu.sbatch`, image
  `sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed`) on synthetic
  rows of E's shape (`python -m harness.q2_stage1e.analysis glmm-synthetic`, 113 tasks, seed
  42). Its convergence and Hessian are reported. The GLMM is secondary, so its outcome changes
  no registered rule; a fit that fails is disclosed here before the freeze. Result: **passed**
  (CPU job 1210, 2026-10-11, 14 min 41 s, from the export of `8a23a483`; no GRES, no network;
  `glmm.R` and the R package lock are S1a's by SHA-256; input 1,808 rows, SHA-256
  `41d87779...`, which E's code regenerates byte for byte): both fits converged (optimizer
  code 0) with positive-definite Hessians; 200 refits used, none failed, 42 not converged
  (reported). Estimated variances: task 1.33 (generating 2.25), task:harness 0.97 (1.00),
  task:size 0.006 (0.09), task:session and task:harness:session near 0 (0.09 each; the latter
  is not identified at R = 1, section 11), every other component near 0. The task:harness
  likelihood-ratio test gives chi-square 34.1 (p 5.2e-9, boundary-corrected 2.6e-9). Evidence:
  `program/evidence/2026-10-11/q2-stage1-successor-e/gates/` (`gates-check.json`)
- **G-E6. A fresh, independent pre-freeze audit** that finds nothing blocking (earlier rounds
  and their dispositions are in section 25's review log), then the freeze
  (`scripts/preregister.py freeze`, section 25's steps). Audit record: **ready** (audit 2, a
  fresh, independent audit on 2026-10-11/12 of the draft at `d6293900`, with `main` at
  `2b8fadc7` merged; no blocking items; its items and their dispositions are audit 2's rows in
  section 25's review log). Its freeze rehearsal, on a scratch clone with a copy of the ledger:
  `scripts/preregister.py freeze` accepted E as row 19, after R04's row (hash `f7b350a3...`);
  `check-chain` (19 rows) and `verify` passed; on the frozen tree E's suites gave 60 passed and
  2 skipped (the two draft-only tests) and the full suite 2,864 passed and 71 skipped
- **G-E7. The overlay OE** is built from E's freeze commit (S1a section 5.5, "Overlay for the
  A1 GPU halves", with `selected_ref: HEAD`); every E GPU half runs on it and its container
  refuses an overlay whose `git_sha` or `source_sha256` differ from its manifest's.
- **G-E8. Quiet host** (section 6.4) before each E pair is submitted.
- **G-E9. Models.** The same revisions as S1a (`Qwen/Qwen3.5-9B` at
  `c202236235762e1c871ad0ccb60c8ee5ba337b9a`, `Qwen/Qwen3.5-4B` at
  `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`); each GPU half names the model receipt and
  artifact root S1a's A1 GPU halves named for its size and checks the files against that root
  (D57 (i) disclosed that the 4B receipt digest is a host fill whose files equal the CPU-lane
  receipt's).

### 4.2 No A0-type job

S1a's A0a measured c_A0a because S1a's caps were priced from the cost card's synthetic replay.
E's caps are priced from S1a's realized slots on the same tasks, engine, harnesses and VMs
(section 7), so no constant is measured before the freeze, and no GPU job runs before it.

## 5. Design

### 5.1 Models, engine, harnesses, observation, step cap, tokens, sampling, settle

S1a sections 5.1-5.3, unchanged. One fresh engine per (size, session) job, shared by both
harnesses; the GPU job's argv is S1a's `plan.engine_argv` for its size (the lane refuses to
dispatch otherwise, section 6.3). Both harnesses use greedy decoding at 2,048 output tokens and
15 steps, the matched settle, screenshots only, and S1a's pinned prompt date.

### 5.2 Tasks

- **All 113 eligible pool tasks** (S1a section 5.4: the 120-task confirm split minus the four
  K1 raw-gold failures and the three offline-setup exclusions `26150609`, `982d12a5` and
  `e2b5e914`; S1a's `plan.eligible_pool`). There is no draw and no fill rule. The list equals
  S1a's 32 base tasks plus its 81 extension tasks, every one of which S1a ran in all four of
  its jobs. By domain: calc 28, impress 24, multi_apps 23, writer 12, gimp 8, thunderbird 7,
  vlc 6, vs_code 5.
- **Flagged tasks:** S1a's seven (S1a section 8, `plan.FLAGGED_TASKS`), all in the pool.
- The tasks, their domains and S1a's base are in E's plan file (section 5.7).

### 5.3 Sessions, order and gaps

- **Sessions per size:** four new ones, `E1`-`E4`. A session is one GPU job for one size, with
  a fresh engine, paired with one CPU-only VM job holding a fresh pool of VMs (S1a section 5.5).
- **Order:** E1 to E4; in every session 9B then 4B, S1a's seeded size order
  (`plan.size_order()`). The registered job order is `E-9B-E1, E-4B-E1, E-9B-E2, E-4B-E2,
  E-9B-E3, E-4B-E3, E-9B-E4, E-4B-E4`.
- **Gaps:** a job of session E2, E3 or E4 starts **at least 12 hours and 5 minutes after the
  later of the previous session's two jobs ended**, where a job's end is the later of its
  lane's `t_end` and its GPU job's recorded Slurm EndTime (`lane.job_end`; if Slurm reported no
  final state for the GPU job, the latest it could end, its Slurm start plus its time limit,
  stands in). D57 (ii) did not settle one reading for S1a: it moved S1a's session-2 `--begin`
  later so that two readings held, the gap from the lane and GPU ends and the gap from the end
  of the later Slurm job. E's VM batch job ends after its lane, by the lane's wait for the GPU
  job's final state (at most 180 s) and the container cleanup (seconds), so the 5 minutes make
  the 12 hours hold under both readings with a margin.
- **Enforcement by the lane** (section 6.3): each E manifest names every earlier E job's lane
  record file and receipt by SHA-256, and the lane refuses the job if one is missing or changed,
  or if any earlier job fired DR0; a job of E2-E4 is submitted with Slurm `--begin` at its
  earliest start, and the lane refuses to start its engine wait before that time.

### 5.4 Episodes within a job

- **One block per job**, `e1`: every (task, harness) cell of the 113 tasks once, 226 episodes,
  rerun 1.
- **Order:** the sorted cells shuffled by `random.Random(f"q2-stage1e:{session}:{size}:e1:42")`
  (`plan.block_order`), harnesses interleaved; each of the eight jobs has its own order.
- **Continuous dispatch, one re-queue** (S1a sections 5.6 and 7.2): each VM takes the next
  queued slot as soon as its previous VM is gone; a slot lost to infrastructure on its first
  attempt is queued once more; a second loss leaves it missing.
- **No fill rule:** every job's slots are the whole task set, so the number of episodes does
  not depend on any outcome.

### 5.5 Records

The driver writes S1a's record (`q2-stage1a-episode-v1`) unchanged; E's records differ only in
two label values, the session (`E1`-`E4`) and the rerun (always 1). E's `records.validate`
checks those labels and applies S1a's `records.validate` to every other field. S1a's own
`validate` refuses an E record, so no S1a tool can read E's records into S1a's analysis.

### 5.6 Analysis sets

- **Primary:** all 113 tasks, raw verdicts, for every estimand, decision rule and prediction.
- **Registered secondary:** S1a's 32 base tasks (S1a's primary task set), reported with every
  estimand; no rule reads it.
- **Sensitivities** (S1a sections 7.2, 8, 15): metric exceptions treated as missing; the
  postconfig server-error sensitivity (D56); the flagged tasks excluded; the checker-corrected
  verdicts (`compare_pptx_files_zinv`); the fractional checker score (section 18); and one E
  adds, the D82 gold-defect tasks excluded, on raw and on corrected verdicts (section 9).

### 5.7 The plan file

`program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json`, rendered by
`python -m harness.q2_stage1e.plan render` from the committed inputs (the split file, S1a's
frozen plan by its `plan_sha256`, and the design study's cost model by SHA-256). It holds the
tasks, S1a's base, the flagged tasks, D82's gold-defect tasks, the domains, the sessions, the
size and job orders, every job's episode order and its digest, the session gap and its margin,
the engine argv, sampling, prompt date, cost inputs, caps and jobs. It reads no outcome.

E plan SHA-256: `4e7298a77670a1e77d1b7c4435722364799f70ea0b6cb093739fa876b25e474d`.

(That is the file's `plan_sha256` field; the file's own SHA-256 is
`12bded251c08755a6b713e8f34f3f327b46e788d55904f2b7118b97675294de8`.) Every E manifest names
the plan file and this digest, and the lane refuses one whose plan is not named on the line
above.

## 6. The lane, concurrency and the host

### 6.1 Pairing and concurrency (S1a section 5.5, unchanged)

Each VM job is submitted first; its GPU job follows with `--dependency=after:` the VM job's
id, so it cannot start, or spend capped minutes, before its VM job has started. The VM job's
limit is the GPU cap plus 10 minutes. V = 20 concurrent VMs; a VM job takes 4V +
`runner_cpus(V)` = 90 CPUs and a GPU job 32, so a pair takes 122 of the 200 allowed and the
pairs run one at a time (S1a's `lane.check_slurm` and `plan.check_cpus`, unchanged).

### 6.2 Registered parameters are pinned in code

E's lane (`harness/q2_stage1e/lane.py`) refuses an E manifest that does not run V = 20 at its
size's cap, pin S1a's prompt date and the registered episode image, and hold exactly the
plan's slots, or that sets the re-queue rule, the episode timeout or the interpreter, or a
fill rule. The GPU half is rendered from the validated VM manifest
(`scripts/render_q2e_manifest.py gpu`, filling S1a's GPU template with S1a's
`gpu_manifest`): its size and cap come from the manifest, never from the command line. The
filled template passes the docker submitter's checks (one H100, 32 CPUs, `--time` equal to the
cap, USR1 at 180 s, `--dependency=after:` the VM job; a test checks both sizes). Its job name
keeps the template's `q2s1a-` prefix, a label only.

### 6.3 What the lane checks before and while it runs

- before submission and at job start: the registration is the frozen file (its ledger row's
  SHA-256 and the hash chain, as `scripts/preregister.py verify` and `check-chain`), the plan is
  the one named in section 5.7, the slots are the plan's, every earlier job ran and passed DR0
  (by digest), and the session gap has passed;
- before dispatch: the GPU job's `ready.json` argv is S1a's `plan.engine_argv` for the job's
  size and its Slurm limit equals the job's cap; otherwise it refuses, records why and stops
  the engine;
- while it runs: everything S1a's lane does (S1a sections 5.5, 7.2, 14), unchanged, with the
  episode container running `harness.q2_stage1e.driver` (S1a's driver with E's record check).

### 6.4 Quiet host

While an E job (VM or GPU) runs, no other Slurm job runs or is submitted (S1a section 5.5; D80:
host jobs are serialized, at most one VM-lane campaign at a time). The operator submits an E
pair only when no other job is running or pending, and submits nothing else until that pair
has ended. Other work may run in the 12-hour gaps, and must have ended before the next E pair
is submitted. Every block records host snapshots (load, foreign Slurm jobs and their CPUs,
container counts). A foreign job seen running during an E job is a disclosed deviation; it is
not a DR0 criterion.

## 7. Jobs, caps and the 8 GPU-h count

### 7.1 The cap rule

S1a priced its A1 caps from the cost card's high price (c_proj = max(card high, 1.25 x c_A0a)),
which S1a's realized cost came to about 0.24 of. Under that rule 478 minutes buy about 700
episodes and no 113-task design fits (design study section 5). E prices each job from S1a's
**realized** cost on the same tasks, at **realized price x 1.2 (DR4's projection rule) x 1.05
(the re-queues DR0 tolerates)**, the design study's cost model
(`program/evidence/2026-10-10/q2-design-study/cost-model.json`, SHA-256
`36887d3c13b9f4b0809b27ae4f6b825cab80dd824be5f0621bd74156d22346a9`):

    cap = ceil(3 + (L + (N x slot / V + drain) x 1.2 x 1.05) / 60) minutes

with L = 113.18587 s (the longest S1a start-up, Slurm start to first dispatch, used without
inflation: an assumption, section 22, disclosure 6), N = 226
episodes, V = 20, slot the size's mean S1a slot occupancy over the 113 tasks and drain the
size's longest S1a drain (the last wave), and 3 minutes of USR1 lead (`plan.job_cap_minutes`):

| Size | slot (s) | drain (s) | N x slot / V + drain (s) | x 1.26 + L (s) | + 3 min | Cap (min) |
|---|---:|---:|---:|---:|---:|---:|
| 9B | 185.426773 | 104.60958 | 2,199.93 | 2,885.10 | 51.09 | **52** |
| 4B | 173.047879 | 92.870499 | 2,048.31 | 2,694.06 | 47.90 | **48** |

### 7.2 Jobs and the count

Caps follow D22's counting rule: every job's cap counts, whatever its outcome.

| Job | When | What | Cap (min) |
|---|---|---|---:|
| OE | after the freeze, before any E job | the cu129 overlay build from the freeze commit (S1a's O2) | 3 |
| OE retry | only if OE fails | one rebuild | 3 |
| E-9B-E1 ... E-9B-E4 | after OE | 9B, one session each, 226 episodes | 4 x 52 |
| E-4B-E1 ... E-4B-E4 | each after its session's 9B job | 4B, one session each, 226 episodes | 4 x 48 |
| **Total** | | | **406 (6.767 GPU-h)** |

- At most 478 minutes is S1a's maximum (7.967 GPU-h); E's caps leave 72 minutes unallocated and
  no other job may use them. 406 minutes is within 8 GPU-h, so E needs no gauntlet (D24, D66).
- Physical use projected by the cost model: 4.97 GPU-h; 90 VM-h; 1,808 episodes.
- No job is retried except OE (once). A second OE failure stops E before any E job and is
  reported. No E job is rerun to improve an outcome.

### 7.3 Do the caps hold every slot? (CPU check)

An E job whose slots do not all finish before its USR1 point fires DR0 (its slots are its whole
task set) and stops E. `program/evidence/2026-10-11/q2-stage1-successor-e/cap_sufficiency.py`
simulates the lane's continuous dispatch for each E job in its registered order, with slot
occupancies resampled from S1a's realized slots for the same (size, task, harness) (four per
cell), starting at L and ending at the cap minus 180 s (10,000 draws, seed 42;
`cap-sufficiency.json`). The dispatch model replays S1a's four jobs' realized spans to within
0.2 s (4,023.0, 3,958.8, 4,278.7 and 4,281.8 s).

| Scenario | 9B: P(all slots end before USR1) | 9B: p99 span from first dispatch / time to USR1 (s) | 4B: P | 4B: p99 span / time to USR1 (s) |
|---|---:|---|---:|---|
| S1a's slots as measured | 1.000 | 2,306 / 2,827 | 1.000 | 2,191 / 2,587 |
| every slot 10% longer | 1.000 | 2,537 / 2,827 | 1.000 | 2,411 / 2,587 |
| every slot 20% longer | 1.000 | 2,766 / 2,827 | 0.9215 | 2,630 / 2,587 |
| 5% of each cell's first attempts lost at full length and re-queued | 1.000 | 2,503 / 2,827 | 1.000 | 2,347 / 2,587 |

S1a's per-job mean slot moved by about 1% between sessions. A 4B session about 20% slower
than S1a's would cut slots with probability about 0.08 (section 22, disclosure 6).

### 7.4 VM time and calendar

- VM time: 90 VM-h projected (S1a's slots), at most 20 VMs at a time.
- Calendar: three gaps of 12 hours and 5 minutes measured from each session's later end, plus
  four session windows of about 1.3 h each (a 9B job then a 4B job), so **about 41-42 hours at
  the minimum**. (The design study's 37 h counted one session window.)

## 8. Episodes, infrastructure losses and the D53 (iii) observation rule

S1a sections 7.1-7.3 apply unchanged, through the unchanged driver, `osworld_live.py` and lane:

- the episode definition (cold boot, offline setup, the guard warm-up, the 60 s settle, up to
  15 steps, the 20 s settle, `DesktopEnv.evaluate()`, the capture, the restart check, teardown);
- the infrastructure losses (`records.INFRASTRUCTURE_TYPES`), each re-queued once and counted
  toward DR0; agent-caused events (`IRError`, metric exceptions) are not losses;
- **the D53 (iii) observation rule as S1a read it and D56 accepted it:** an observation the
  guest server does not deliver (no HTTP status below 500 on any attempt of a screenshot or a
  checker read) is an infrastructure loss; every attempt is bounded (a screenshot at 10 s per
  attempt, a checker read sent without a timeout at 150 s, then a transport loss); an
  observation delivered slowly (over 30 s) or only on a retry is counted per episode as
  infrastructure and reported per cell beside the losses, and its episode is scored;
- **the postconfig carve-out and D56's two conditions:** a failed postconfig reply is recorded
  (`postconfig_failures`) and is not a loss; the observation counts and the postconfig replies,
  failures and server errors are reported per (size, harness), per (size, session) and per
  (size, harness, session), here over E's four sessions per size; and the postconfig
  server-error sensitivity recomputes every primary estimand with each episode treated as
  missing that has a postconfig reply at HTTP 500 or above or with no HTTP reply. It changes no
  decision rule.

## 9. Outcomes and checker corrections

S1a section 8, unchanged: the primary outcome is y = 1 if the checker score is 1.0, else 0
(raw verdict); the checker-corrected outcome rescored with `compare_pptx_files_zinv` is
secondary; S1a's seven flagged tasks (`plan.FLAGGED_TASKS`) stay in the primary analysis and a
sensitivity excludes them.

**What D82 found.** D80 (ii)'s adjudication of the checker-mutation pool and spot check is
complete (D81 run 2, D82; "adjudicated by an isolated model on the owner's instruction (D80);
not human-validated"; `program/evidence/2026-10-11/q2-mutation-adjudication-v2/summary.json`).
Two of its findings bear on E's outcomes:

- **Three gold-defect tasks.** It rejected the saved gold (the gold sham) of `5c1a6c3d`
  (impress, `compare_pptx_files`), `881deb30` and `8e116af7` (multi_apps, `compare_table`):
  each task's own saved gold is judged not a correct solution (`before_after.after_a.audit
  .gold_defect_tasks`). All three are in E's 113-task primary set. None is in S1a's 32 base
  tasks or in S1a's flagged list, which was fixed before D82 and flagged the same kind of
  defect on `30e3e107` (the P1 raw flip whose saved gold both raters reject).
- **The z-order candidates.** The six unresolved z-order false-negative candidates of
  `compare_pptx_files` became three confirmed and three label-contradicted. The three
  contradicted ones are all on `5c1a6c3d`. `compare_pptx_files_zinv` passes all six (S1a G0
  item 8), so on `5c1a6c3d` the corrected outcome scores as passing states the adjudication
  rejects.

**What E does about it.** No primary set, outcome, decision rule or DR changes:

- E's flagged list stays S1a's seven, and the flagged-task sensitivity is S1a's.
- **The D82 gold-defect sensitivity**, added beside it: every primary estimand, test and rule
  reading (sections 10, 11 and 13: DR1, DR2, DR5) is recomputed on the 110 primary tasks
  without the three gold-defect tasks (the plan's `gold_defect_tasks_d82`), on raw verdicts,
  and the checker-corrected outcome is recomputed on the same 110 tasks, which removes the
  three label-contradicted z-order states. It carries D80's label and changes no reading of
  E's primary set.
- The corrected verdicts stay secondary: the correction was validated on S1a's 29 confirmed
  mutants (S1a G0 item 8), and the adjudication that would confirm more of it is model-made and
  not human-validated (D9's human spot check stays open, D82).

## 10. Estimands and estimators

S1a section 9, unchanged: the same definitions, computed by the frozen
`harness/q2_stage1/estimators.py` on E's outcome array y of shape (Z, K, H, S, R) = (2, 113, 2,
4, 1). Every estimand is conditional on E's realized sessions. The frozen functions are defined
for any S ≥ 2 and R ≥ 1; at S = 4 and R = 1 they read:

- **δ**: the mean over the available (size, session) cells of d_zts, then over tasks; δ_z per
  size; δ per (size, session) is also reported.
- **X_z** = mean_t of the mean over ordered session pairs s ≠ s' of d_zts · d_zts'
  (`estimators.x_task_products`; at S = 2 it is d_zt1 · d_zt2). It is unbiased for
  mean_t Δ_zt² when the sessions are independent given the task, so it carries the main effect
  (S1a section 9 item 3).
- **X_c,z** = X_z − (δ_z² − Var-hat(δ_z)), with Var-hat from the variance of d_zts over the four
  sessions (`estimators.x_centred_by_size`).
- **D_b,z**: the mean over (t, h) of the discordant share among a cell's six cross-session
  pairs. The same-block D_b equals D_b.
- **π_z** = (X_z⁺/4) / (X_z⁺/4 + D_b,z/2); π_small the mean of π_4B and π_9B, or π_9B when DR1
  drops 4B; the scale screens δ_4B − δ_9B and π_4B − π_9B; the Bernoulli X (secondary).
- **Not estimable with one episode per session** (each needs a within-session pair), and
  reported as such: D_w, the session excess D_b − D_w, the cross-block D_b, and the common
  session share ρ.
- **Two-session quantities, by pair.** S1a's session shift (S2 − S1) per size with its
  two-sided sign-flip test, and the harness effect by session (δ_S1 − δ_S2 with its task-paired
  SE), are defined for two sessions. E reports both for each of the six session pairs per size,
  by the frozen two-session functions on that pair's slice, with Holm over a size's six tests
  shown beside them. They are descriptive; no rule or prediction reads them.

The code is `harness/q2_stage1e/analysis.py` (`statistics`, `analyse_array`), which calls the
frozen functions in S1a's order. S1a's `analysis.analyse_array` cannot take S ≠ 2 (its
session-shift statistics raise), so E makes the same calls itself. On S1a's own records E's
`analyse_array` reproduces S1a's committed registered readings exactly, on both of S1a's sets:
18 estimates each, the δ paired t, the X sign-flip and label-permutation p-values, the session
test, the harness effect by session, success, DR1, DR2 and DR5
(`program/evidence/2026-10-11/q2-stage1-successor-e/analysis-identity.json`, at the registered
10,000 resamples and flips).

## 11. Inference

S1a section 10.1, unchanged:

- **Intervals:** task-cluster percentile bootstrap, 10,000 resamples, seed 42; tasks resampled
  jointly across sizes, harnesses and sessions; sessions held fixed; one-sided 95% bounds are
  the 5th and 95th percentiles.
- **δ:** paired t over tasks on d̄_t, two-sided, α = 0.05, with its 90% t interval.
- **X (primary):** the one-sided sign-flip test of the per-task pooled products q_t, 10,000
  flips, seed 42 (`estimators.x_signflip_p`). At S ≥ 3, q_t is a U-statistic over session
  pairs and flipping its sign is not the same as flipping each d_zts, so the test is not exact;
  it is conservative: its null size at α = 0.025 is 0.004-0.017, and DR2's false Present is at
  most 0.049 (design study section 3.4). E registers this frozen statistic, the one the power
  statement was computed with, and not the exact per-cell flip.
- **X (sensitivity):** the label permutation within each (task, session) cell
  (`estimators.x_label_permutation_p`, unchanged). With R = 1 it swaps the two harness
  episodes of each (size, task, session) cell independently, which flips the sign of each d_zts
  on its own: it is the exact per-cell sign flip of X, valid when a cell's two episodes are
  exchangeable under no harness effect. It is reported beside the primary test as a
  sensitivity; no rule reads it.
- **Session tests:** by pair, descriptive (section 10).
- **Secondary model:** S1a's crossed logit GLMM, by the unchanged `glmm.R` and the pinned
  container, on E's rows (`analysis glmm-input`: S1a's columns, sessions nested in size as
  `9B:E1`). With one Bernoulli episode per (task, harness, session), the
  (1|task:harness:session) term has one observation per level and is not identified apart from
  the Bernoulli variance; the fit is reported exactly as `glmm.R` writes it, convergence
  included, and its (1|task:harness) likelihood-ratio test carries that note (G-E5 runs it on
  E's shape before the freeze).
- **Missing data:** missing slots (a second infrastructure loss) are treated as missing at
  random, an assumption; losses are reported by task.
- **Multiplicity:** DR2's family is the δ test and the X sign-flip test, Holm at family-wise 5%.
  P1-P5 are read once each.

## 12. Operating characteristics: the registered power statement

The design study's simulation of E (D66, D69;
`program/evidence/2026-10-10/q2-next-step-design-study/README.md` sections 3-4 and 6,
`designs-P0.json`, `designs-PR.json`, `designs-P4.json`, `designs-P4sf.json`) is E's registered
power statement. Each data set was analysed by `harness.q2_design.analyse.analyse` (equal to
`fast.analyse`): the frozen estimators and rules at 10,000 resamples and flips, Holm DR2, DR5 at
M = 0.13. On simulated E-shaped data E's registered `analyse_array` gives the same p_X, π_small
bounds, δ, DR2 and DR5 as that function (`analysis-identity.json`, seeds 42-44;
`tests/test_q2_stage1e.py`).

**Calibrations.** The generative model is S1a's (S1a section 10.2), fitted by maximum marginal
likelihood to S1a's 113 tasks. Four calibrations pass the extended posterior-predictive check
written after the design study's attack: **P0** (`fit-pool`, coupled across sizes), **PR**
(decoupled), **P4** (4B with no task-specific harness effect) and **P4sf** (P4 with σ_f = 1.0
in both sizes). Base-fitted calibrations failed the check and are not used. Task source: each
calibration's pool posterior. 450 data sets per cell (seeds 42-44 x 150); Monte Carlo SE at most
0.024 per probability; differences below 0.05 are not read.

Truth over the 113 tasks at S1a's estimates (π°_small, π°_9B, δ°): P0 0.098, 0.167, −1.1 pp;
PR 0.093, 0.164, −1.1 pp; P4 0.084, 0.164, −1.1 pp; P4sf 0.067, 0.131, −1.1 pp.

**At S1a's estimates (fitted), the range over the four calibrations:**

| E (K = 113, S = 4, R = 1, both sizes; 406 cap-minutes) | Probability |
|---|---|
| DR2 decisive | 0.83-0.87 |
| of which Present / Near-equivalent | 0.52-0.73 / 0.12-0.34 |
| DR5 NO-GO | 0.23-0.54 |
| DR5 GO | 0.00 |
| Both rules inconclusive (S1a's outcome) | 0.08-0.13 |
| Median width of δ's 90% interval | 4.7-5.4 pp |

**Per calibration:**

| Calibration | Fitted: DR2 decisive (Present / Near-eq.) | Fitted: DR5 decisive (NO-GO / GO) | Fitted: both inconclusive | π = M: DR5 decisive (an error) | Null: Near-eq. / NO-GO / false Present | 2M: DR2 decisive / GO | δ 90% width (pp) |
|---|---|---|---|---|---|---|---|
| P0 | 0.83 (0.71 / 0.12) | 0.23 (0.23 / 0.00) | 0.12 | 0.09 | 0.97 / 0.99 / 0.02 | 1.00 / 0.94 | 5.4 |
| PR | 0.87 (0.73 / 0.14) | 0.24 (0.24 / 0.00) | 0.10 | 0.08 | 0.96 / 0.99 / 0.03 | 1.00 / 0.97 | 4.8 |
| P4 | 0.83 (0.65 / 0.17) | 0.30 (0.30 / 0.00) | 0.13 | 0.09 | 0.95 / 0.99 / 0.03 | 1.00 / 1.00 | 4.7 |
| P4sf | 0.86 (0.52 / 0.34) | 0.54 (0.54 / 0.00) | 0.08 | 0.06 | 0.97 / 1.00 / 0.03 | 1.00 / 1.00 | 4.7 |

Scenarios: **fitted**, S1a's estimates under the calibration; **π = M**, the task-specific part
scaled until π°_small = 0.13, where any decisive DR5 is an error; **null**, no harness effect of
any kind; **2M**, π°_small = 0.26.

What the power statement says:

- **DR2 is decisive with probability 0.83-0.87**, mostly as Present through the X test, from
  9B's task-specific effects: p_X ≤ 0.025 in 49-73% of data sets, p_δ ≤ 0.025 in only 3-5%.
  Near-equivalent is limited by π_small's upper bound, not by δ: δ's 90% interval lies within
  ±7.5 pp in 99-100% of data sets, while π_small's upper bound falls below 0.12 in 14-41%. DR1
  never dropped 4B.
- **DR5 cannot reach GO** at S1a's estimates (the truth is below M); NO-GO has probability
  0.23-0.54, rising as 4B's share falls (P0 lowest, P4sf highest). At the boundary (π = M) the
  error rate is 0.06-0.09.
- With no harness effect, E reads Near-equivalent with probability 0.95-0.97 and NO-GO with
  0.99-1.00; its false Present is 0.02-0.03.
- **Limits of the statement** (design study section 9): the calibrations are plug-in fits with
  no hyperparameter uncertainty, checked in sample on the 113 tasks; 4B's harness differences
  reverse sign across sessions more often than any calibration produces (mid-rank 0.94-0.98;
  P4sf comes closest), and larger true 4B noise would lower P(Present) and raise P(NO-GO); the
  new-session terms rest on two degrees of freedom (σ_g 0 to 0.65; σ_k at most 0.95-1.17
  logits), and a harness x session effect common to a session's tasks (σ_k) was not simulated
  for E (one evaluator ran it at 0.95 on design C under P0: DR2 0.78, DR5 0.38).
- **P3** (the pair is not Present) is forecast to be falsified with the probability of
  Present, 0.52-0.73.

## 13. Decision rules (fixed before any E episode)

S1a section 11, with its thresholds and code (`harness/q2_stage1/rules.py`) unchanged; every
rule reads E's primary set.

- **DR0, validity (each E job).** From infrastructure records only, at the end of every E job
  (`python -m harness.q2_stage1e.analysis dr0`; `records.job_dr0`, which calls S1a's
  `rules.dr0`): it fires if a (size, harness) cell lost more than 5% of its first-attempt
  dispatched episodes to infrastructure, if the job ended without every slot final (scored, or
  lost after its re-queue), or if a gate turned out not to hold (a lane receipt with an error:
  an engine or Slurm check, a visible GPU device). When it fires, no further E job starts (the
  lane refuses it, section 5.3). The cause is investigated without reading outcomes; any code
  change is a new experiment id; the data already collected are reported as incomplete
  (section 18).
- **DR-A, anchor.** ANCHOR-UNAVAILABLE, as in S1a (S1a G0 item 9.6); every E output carries the
  label "not externally anchored".
- **DR1, floor.** If 4B's pooled success is below 10% under both harnesses, π_small = π_9B for
  DR2's bound and DR5's share (M = 0.18).
- **DR2, harness pair (for E's realized sessions).** Present if Holm over the δ paired t and
  the X sign-flip test rejects at family-wise 5% (min p ≤ 0.025); Near-equivalent if not
  present, the 90% t interval of pooled δ lies within ±7.5 pp and the one-sided 95% upper bound
  of π_small is below 0.12; Inconclusive otherwise.
- **DR3, components.** Reported per size: success by harness, D_b, X, X_c, δ per session and the
  pairwise session shifts; D_w and ρ are not estimable (section 10).
- **DR4, cost.** If any E job's realized GPU-h per episode exceeds the card's high price at
  V = 20 (0.011274), it fires; any later projection then uses the realized value x 1.2 and a
  re-probe.
- **DR5.** GO if the one-sided 95% lower bound of the share exceeds M; NO-GO if its one-sided
  95% upper bound is below M; INCONCLUSIVE otherwise (M = 0.13 for π_small, 0.18 for π_9B).
  **Consequences.** Under D47 only GO lets the S1b scale ladder go to the gauntlet. D69 closed
  S1b and the harness-scale question on the design study, which puts GO out of reach at S1a's
  estimates. A GO in E would contradict that forecast: it is reported to the program owner, who
  decides whether to reopen S1b; nothing starts automatically. NO-GO and INCONCLUSIVE start
  nothing; a NO-GO points, as S1a's section 11 says, to an observation-factor study, which
  would be a new proposal with its own gauntlet.

## 14. Predictions (read once on the primary set, for E's realized sessions)

S1a section 12, with the same falsifiers:

| | Prediction | Falsified if | In E |
|---|---|---|---|
| P1 | The session excess D_b − D_w is positive | the one-sided 95% upper bound of pooled D_b − D_w is below 1 pp | **not estimable** (no within-session pair); reported as such, neither falsified nor supported |
| P2 | Pooled D_b lies between 6% and 20% | its 95% bootstrap interval lies wholly outside [6%, 20%] | read as registered |
| P3 | The pair is not Present under DR2 | DR2 classifies the pair as Present | read as registered (forecast falsified with probability 0.52-0.73) |
| P4 | 4B is not at the floor | DR1 fires | read as registered |
| P5 | Realized GPU-h per episode is at most the card's high price | DR4 fires | read as registered |

A falsified prediction is reported as such; none stops E.

## 15. The joint reading with S1a (descriptive)

E's registered readings are E's alone. After E's report is written, one descriptive output,
`joint.json` (`python -m harness.q2_stage1e.analysis joint`, `analysis.joint_reading`), sets
S1a and E side by side on the same 113 tasks, labelled "descriptive joint reading of S1a and E:
not registered inference; no rule, test or prediction reads it":

- S1a's estimates on its 113-task secondary set (its two sessions x two reruns) and E's
  estimates (four sessions x one episode), for δ (pooled and per size), D_b, X and π (per size
  and pooled), each with a task-cluster bootstrap interval;
- their difference, E minus S1a, with an interval from the same bootstrap, which resamples the
  tasks jointly for both samples (seed 42), so it reflects that the two samples share tasks;
- the same quantities over the six sessions together (cell means over the reruns each session
  holds; D_b pools every cross-session pair, S1a's with E's included).

It reports no p-value and enters no rule, DR, prediction or decision. The RESULTS text states
E's registered readings first and quotes the joint reading only as a description.

## 16. Seeds and randomization

Seed 42 for every stream: the episode orders (`random.Random` over a key naming the session and
size), the bootstrap and the randomization tests (numpy PCG64 seeded with 42), the engine seed
(`--seed 42`, S1a's flags) and the GLMM. S1a's 43 and 44 were its session-order seeds; E's
session orders are keyed by session name. Decoding is greedy, so rerun variation comes from the
environment, timing and batched-serving numerics. The design (four sessions, one episode, 113
tasks) is justified by the power statement of section 12, not by habit.

## 17. Stop rules

S1a section 14, unchanged: every GPU job has a Slurm `--time` equal to its cap and
`--signal=B:USR1@180`, and its VM job a limit of the cap plus 10 minutes; on USR1 nothing new is
dispatched and in-flight episodes are recorded `cap_truncated`; a Slurm TIMEOUT keeps the records
and marks the job incomplete; DR0 stops E; no job is rerun to improve an outcome; an aborted
job's records are kept and reported.

## 18. The analysis, through the D59, D61 and D62 rules

S1a's analysis went through operator tooling written under D59 (fixed while blind) and D61 and
D62 (edge cases ratified while blind). E registers those rules up front, in its code of record:

- **D59 (i), fractional scores.** The frozen `estimators._check` accepts only 0, 1 and NaN, and
  three pool tasks use continuous metrics. E's fractional-score sensitivity (δ on checker
  scores in [0, 1]) runs through `analysis.widened_check`, which widens that one check for that
  one call and restores it (a test checks the restoration). Nothing else is widened.
- **D59 (ii), D61, D62, incomplete data.** Every output is labelled `incomplete` when DR0 fired
  for any E job, when a registered job has no records, or when a size holds fewer than four
  sessions of scored records. Estimates are the registered code's on the data collected (D61
  (a)). A size with fewer than two sessions holding scored records, or with no task holding
  both harness cells in two sessions (D62), has no X and no π: DR5 is then "not evaluable as
  registered", with π_9B shown against both M values as a description only; DR2 is kept with a
  note that its X test and π bound come from the other size (D61 (b)), or is not estimable when
  its tests have no finite statistic. No p-value is read from an all-NaN statistic. P1 is
  always not estimable (section 14). The code is `analysis.analyse_array`, `completeness` and
  `report`; tests cover each case.
- **Incomplete readings are E's registered readings, under the label.** When DR0 fires but
  each size still holds at least two sessions with X and π defined (D61 (a)), DR1, DR2, DR5 and
  P2-P5 as the registered code computes them are E's registered readings for the sessions and
  tasks that hold data, reported under the `incomplete` label: their tests and intervals stay
  valid, because they condition on the realized sessions and DR0 reads no outcome. The power
  statement of section 12 covers complete data only (four sessions per size, every slot
  final), and no operating characteristic is claimed for an incomplete reading.
- **D59 (iii), operator steps.** Each is a registered command, with its output kept:
  1. per E job, at its end: `python -m harness.q2_stage1e.analysis dr0 --run-dir RUN --plan
     PLAN` (exit 3 when DR0 fires);
  2. offline rescoring, one CPU job per E job with `--time=08:00:00` in the metric image through
     `s1a-cpu.sbatch`: `python -m harness.q2_stage1.rescore capture` then `rescore merge`
     (unchanged), with coverage, live-score fallbacks and replay mismatches reported beside the
     corrected outputs;
  3. the cost card: `python -m harness.q2_stage1e.analysis costs --run-dir RUN ...`;
  4. the report: `python -m harness.q2_stage1e.analysis report --records E.jsonl --plan PLAN
     --costs costs.json --dr0 ...` (the merged records of all E jobs);
  5. the section 15 items the report does not compute: `analysis section15` (output tokens,
     step distributions censored at 15, restarts and observation events per episode, losses by
     task, the cost card against the central and high prices, setup and postconfig failures by
     type, host snapshots and foreign load, first divergence on E's tasks, scored final records
     and each final attempt's step log; `harness/q2_stage1e/section15.py`);
  6. the GLMM: `analysis glmm-input`, then `glmm.R` in the pinned container through
     `s1a-cpu.sbatch`, each fit's exit code captured, convergence reported as written, the R
     package digest checked;
  7. the joint reading (section 15): `analysis joint`;
  8. provenance: the export's commit, the registration's ledger check
     (`scripts/preregister.py verify` and `check-chain`), the plan digest, the input digests,
     and the interpreter and library versions.

  The analysis CPU jobs run with `ops/s1a-analysis/cpu-step.sbatch` (unchanged) or
  `s1a-cpu.sbatch`; neither requests a GPU. A fresh verifier recomputes the report from the
  SHA-checked raw records before RESULTS is written (the step D72 (v) found missing in S1a).

## 19. Reported regardless of outcome

S1a section 15, for E:

- every estimand of section 10 with its interval, on the primary set and on S1a's 32 base
  tasks: raw on both sets; checker-corrected on the primary set and the D82 110-task set; per
  size and pooled, per domain descriptively; δ per session and the pairwise session shifts;
- DR0-DR5, DR-A and P1-P5 (P1 as not estimable);
- infrastructure losses by type and cell; `IRError` and metric-exception counts; restarts per
  episode; observations delivered on retry, slower than 30 s or undelivered, per episode and per
  cell; cap truncations; the metric-exception-missing sensitivity;
- per session (D56): every count of the cells per (size, harness), per (size, session) and per
  (size, harness, session), over the final records and over every attempt; the postconfig
  server-error sensitivity;
- the cost card against the card's central and high prices; truncation rates per cell and the
  truncation label (S1a section 15's 20% rule); uncertified action-path exposure and δ by
  exposure stratum; first divergence, checker-input-hash discordance and offline rescoring;
  fractional checker scores; corrected-verdict flips; the flagged-task sensitivity; the D82
  gold-defect sensitivity, raw and corrected (section 9);
- host snapshots and any foreign load; the label "not externally anchored"; the offline-setup
  exclusions;
- the joint reading with S1a (section 15), as a description;
- every deviation from this file.

## 20. Data handling

S1a section 16, unchanged: captures, screenshots, raw replies and step logs stay on the host's
persistent run root (or the program's private archive), never in `program/evidence/`; records
keep each guest reply's status, `returncode` and stderr tail, never its stdout tail; evidence
receives metadata, verdicts, counts, hashes, receipts and reports; GPU UUIDs are hashed; no host
address is recorded.

## 21. Design decisions for sign-off

D80 delegates the program owner's pending research decisions on E to the program (D80 (iii)).
The program signs these items in one decision before the freeze:

1. E adds data to S1a's design without a gauntlet (D66, D80 (iii)): 6.77 GPU-h by caps.
2. All 113 eligible pool tasks, no draw and no fill rule; the primary set is the 113 tasks and
   S1a's 32 base tasks are the registered secondary set.
3. Four new sessions per size (E1-E4), at least 12 hours and 5 minutes apart measured from
   the previous session's later end (section 5.3); 9B then 4B in every session; one episode per
   (size, task, harness, session).
4. Caps by arithmetic at realized price x 1.2 x 1.05 (52 minutes at 9B, 48 at 4B, 406 in all,
   with OE and one retry) in place of S1a's card-priced c_proj; no A0-type job.
5. With R = 1, D_w, the session excess, the cross-block D_b, ρ and P1 are not estimable and are
   reported as such.
6. The frozen X statistic at S = 4 (the U-statistic q_t, flipped whole; conservative) as the
   primary X test, not the exact per-cell flip.
7. The two-session quantities (session shift and its test, harness effect by session) reported
   for each session pair, descriptive.
8. The GLMM run unchanged, with the R = 1 identification note (G-E5).
9. E is its own sample; the joint reading with S1a is descriptive (section 15).
10. DR5's consequence under D47 and D69 (section 13).
11. The D59, D61 and D62 rules registered up front, and an incomplete reading with X and π
    defined in both sizes counted as E's registered reading under the `incomplete` label, with
    no power claimed for it (section 18).
12. The quiet-host rule and D80's serialization (section 6.4).
13. E's code: S1a's code of record unchanged, plus `harness/q2_stage1e/`, its lane batch script
    and its manifest renderer (section 23).
14. D82's three gold-defect tasks (`5c1a6c3d`, `881deb30`, `8e116af7`) stay in the primary set;
    one sensitivity excludes them, on raw and corrected verdicts; S1a's seven flagged tasks stay
    the flagged set (section 9).

The sign-off decision is one entry of `program/decisions.md`, on `main`, before the freeze:
its bold heading names `q2-stage1-successor-e-v1`, and its entry signs "items 1-14" of this
section. `tests/test_q2_stage1e_prereg.py` refuses any other id in the slot below.

- Program sign-off of items 1-14 (decision id): TBD

## 22. Disclosures and known limitations

1. **Outcome-aware design.** E's design and its scenarios were chosen after S1a's readings, on
   S1a's records, and E reuses S1a's tasks. E's tests are valid conditional on the task set, and
   E's sessions are new, but the choice of design is not blind to S1a.
2. **Not pooled.** E's readings describe E's four sessions. Pooling S1a with E was not modelled
   by the design study and has no registered rule; the joint reading is descriptive.
3. **P1 is not estimable**, and with it D_w and ρ. S1a falsified P1 already (its upper bound,
   0.78 pp).
4. **Present is not a main effect.** The δ test rejects in 3-5% of simulated data sets at S1a's
   estimates; a Present reading would come from X and mean task-specific (mostly 9B) harness
   effects or a main effect too small for δ to see.
5. **The X test is conservative at S = 4** (section 11), so the power statement may understate
   the X test's power; the statement was computed with this test.
6. **Cap margins.** The caps hold every slot in the cap check under S1a's slots, slots 10% longer
   and 5% loss, but a 4B session about 20% slower than S1a's cuts slots with probability about
   0.08 (section 7.3), which fires DR0 and stops E with incomplete data. Every cap, and the cap
   check, assumes S1a's longest start-up L = 113 s with no inflation. A slower engine start-up
   in an E session comes straight out of the margins: at p99, the time to USR1 minus the span
   is 521 s (9B) and 396 s (4B) under S1a's slots, and 61 s at 9B with slots 20% slower.
7. **The GLMM's (1|task:harness:session) term is not identified** with one episode per cell
   (section 11).
8. **Calendar.** About 41-42 hours at the minimum, longer than the design study's 37 h.
9. **Everything S1a disclosed about its configuration still applies** (S1a section 19): the
   narrow harness contrast, greedy decoding, the 2,048-token thinking budget, 15 steps, offline
   tasks, the agent-caused events counted as infrastructure, partial checker corrections, the
   observation service, uncertified actions, the pinned prompt date, and results that are not
   externally anchored.
10. **New code.** E's lane layer and entry point are new; G-E4 runs them on the host before the
    freeze, and the episode path itself (driver, harness clients, checker path) is S1a's
    unchanged code, which ran 1,808 episodes in S1a without an infrastructure loss. G-E4 runs
    the `development` purpose only, so the `e` purpose's own checks (the prior jobs by digest,
    the session gap, the engine argv and the Slurm limit) first run on the host in E-9B-E1. CPU
    tests cover each, and the engine check copies S1a's `check_registered_engine`, which ran in
    S1a's A0a and A1 jobs.
11. **Gold-defect tasks after the design.** D82, which came after E's design and power
    statement, found three primary tasks whose saved gold is judged not a correct solution
    (section 9). They stay in the primary set, as S1a's flagged tasks did; the D82 gold-defect
    sensitivity reports every primary reading without them. The finding is model-adjudicated
    and not human-validated (D80, D82), and the power statement's calibrations were fitted on
    all 113 tasks.
12. **Incomplete data.** A reading on incomplete data (section 18) keeps its validity but has
    no stated power; the power statement covers complete data only.

## 23. Code of record

Committed and tested on CPU before the freeze. **No file of S1a's code of record changes**:
every file of `q2-stage1-rescoped-v1` section 20 (both tables) keeps the SHA-256 S1a states,
and `tests/test_q2_stage1e_prereg.py` checks each against the tree (G-E2). E runs S1a's episode
path (`driver.py`, `agents.py`, `engine.py`, `bridge.py`, `osworld_live.py`, the executor, IR and
adapters), S1a's lane (`lane.py`), estimators, rules, records, plan constants, rescoring, GLMM
script and GPU template unchanged.

E's own files:

| File | SHA-256 |
|---|---|
| `harness/q2_stage1e/__init__.py` | `c4863fef3110baeecf59e6770eaec1d02a0c4be439aa5ace15cda83578ab958f` |
| `harness/q2_stage1e/plan.py` | `c2c5557efa28e4c87fb41eceb399efd07d7766efabb47635f1439d4d5aa6b597` |
| `harness/q2_stage1e/records.py` | `5f8b6a1a5dfff32c4b12cdbde2a476f02788731b4e4c4e6ccabba288c89822fa` |
| `harness/q2_stage1e/driver.py` | `f5e892c2060ba17173892bfb351263de75ff81783e43f396e7b3edc453d0505e` |
| `harness/q2_stage1e/lane.py` | `6173bc473aec46f04b2f0ead0cce4a42ee887252d6d59264a6770f006b8dd884` |
| `harness/q2_stage1e/analysis.py` | `49d7939f2f0db025135a346750d2cb30acbe70cc7d1cb0e5b096300beff0c6fb` |
| `harness/q2_stage1e/section15.py` | `e1ab8a3e21b008969e8b33d716a78bc73161f6573aee8cdcb80a264922b857bd` |
| `scripts/render_q2e_manifest.py` | `dc61f767e2ea63cbd425d4edc693331b3193cbd708f79674b2ce27d2e4595fde` |
| `infra/slurm/host-single-node/q2e-vm.sbatch` | `2d27bbe50f6ce6aa9df9e4ba9a015ca2d6d489ccc4259f8b8b0a245c94fc6229` |
| `experiments/manifests/q2-stage1e/dev-smoke-v1.json` | `3d215facf9a66f87a7270f359257adda289cf1b1f80c1de33685ccd40a10f2a9` |
| `program/evidence/2026-10-11/q2-stage1-successor-e/plan/plan-e.json` | `12bded251c08755a6b713e8f34f3f327b46e788d55904f2b7118b97675294de8` |

What each adds over S1a's code:

- `plan.py`: the 113 tasks, D82's gold-defect tasks, sessions, orders, job order, gaps and
  their margin, and caps (sections 5, 7, 9).
- `records.py`: E's record labels over S1a's `validate`; the four-session array; DR0 per job
  (S1a's `rules.dr0`); the GLMM rows and the E-shaped synthetic rows.
- `driver.py`: S1a's driver with E's record check (`driver.validate` set to E's `validate`).
- `lane.py`: E's manifest rules, the job order and DR0 by digest, the session gap (`job_end`),
  the engine check and E's entry point, over S1a's `Lane` (subclassed; S1a's dispatch,
  re-queue, stop, snapshots, receipts, `check_slurm` and `check_host` unchanged).
- `analysis.py`, `section15.py`: S1a's estimators and rules on E's array, the D59/D61/D62 rules,
  the D82 gold-defect sensitivity, costs, DR0, the joint reading and the section 15 items.
- `render_q2e_manifest.py`: E's VM manifests, the development smoke's, and the GPU half from S1a's
  template through S1a's `gpu_manifest`.
- `q2e-vm.sbatch`: `s1a-vm.sbatch` with the job name, the header comment and the lane module
  changed; its other lines are S1a's (a test checks).

**Infrastructure E runs that neither table above pins.** The GPU halves run S1a's
`submit_docker_research_job.py` (S1a section 20), which submits `docker-research.sbatch`; its
container runs the provenance, environment and model checks below; OE runs S1a's overlay builder
and extractor (job 464's, by these digests); and the analysis steps run `cpu-step.sbatch`
(section 18). Every file but `cpu-step.sbatch` is unchanged since S1a's freeze commit
(`d5f5798`); `cpu-step.sbatch` was added after it by the D59 tooling. They run from the export
of E's freeze commit with these digests:

| Infrastructure file | SHA-256 |
|---|---|
| `infra/slurm/host-single-node/docker-research.sbatch` | `2a10c9c72c22ab6dd5135061ff1b9b50977a468687180353d8cd7273acbaf1ec` |
| `scripts/verify_compute_provenance.py` | `ca62d62ae5c0e820a08574d5c5b1227c4495a24f3abcf342a1ae3ff1958d54ba` |
| `scripts/check_compute_env.sh` | `76fc5d64f7e84fd1e93340688b6be845d97f01c4791981c31ac8e70d66ff08ff` |
| `scripts/fetch_open_model.py` | `d995b59ece3c809edd70d6c60a78628ae5cb1ccc0ce8350cc455084d3787d29f` |
| `scripts/exec_research_workload.py` | `bb3abd1dd11e8ec9336fc181ac1999b1deea00e08e05d0fff3227111eaa6e4c1` |
| `scripts/build_vllm_overlay_on_h100.sh` | `aa43283e757695384e0548d060a18b98f07a3af06f583efdb2d709f677e1a96d` |
| `scripts/extract_discovery_source_archive.py` | `9b4d21a83beac8913dc06a946cf43ea31d77326e65d04957fad66d7b97d8c3cb` |
| `ops/s1a-analysis/cpu-step.sbatch` | `b826727239a2faf5245b58a6b50bf7e68e068c7357d79833c6c967643663770d` |

Tests: `tests/test_q2_stage1e.py` and `tests/test_q2_stage1e_prereg.py`. The prereg test checks
every digest of the three tables against the tree, and that every in-repo module E's Python
files import, transitively (lazy imports included), is in S1a's section 20 or in E's table.
S1a's suite (`tests/test_q2_stage1_*.py`) and the design study's (`tests/test_q2_design.py`)
pass unchanged.

## 24. Sources and evidence

- S1a: `program/preregistrations/q2-stage1-rescoped-v1.md` (ledger row 16, file SHA-256
  `f9db7cc38c4954b3144ac5a1afaf7bf5366449081b06c80bf89888bdf653afd8`); its frozen plan
  `program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json` (`plan_sha256`
  `6a3f0219448301d95a80d443ed75892eaac093e42349ef98fb985a5d87467d51`); its records
  `program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl` (SHA-256
  `4af798f5908e48aaf84d116682c813311b5ae48096e3b7ed2299c1530c08c6c0`) and its RESULTS.
- The design study: `program/evidence/2026-10-10/q2-design-study/` (the cost model above) and
  `program/evidence/2026-10-10/q2-next-step-design-study/` (README, `designs-*.json`,
  `ppc-*.json`).
- E's evidence: `program/evidence/2026-10-11/q2-stage1-successor-e/` (README; `plan/plan-e.json`;
  `cap_sufficiency.py` and `cap-sufficiency.json`; `analysis_identity.py` and
  `analysis-identity.json`).

## 25. Pre-freeze review log and the freeze

### Pre-freeze review log

Every pre-freeze audit is recorded here, with every item and its disposition. G-E6's slot
names the fresh audit that finds nothing blocking.

**Audit 1** (2026-10-11; a fresh, independent auditor on the draft at `272ea298`, before `main`
was merged; verdict: not ready to freeze, three blocking items). Its own checks included an
independent recomputation of `cap-sufficiency.json`, `analysis-identity.json` and every
section 12 number (all reproduced exactly), a freeze rehearsal on a scratch clone with `main`
merged (accepted as ledger row 19; the rendered E-9B-E1 VM manifest validated with 226 slots;
the GPU half passed the submitter's `--dry-run`; the lane refused every tampered manifest it
tried), and read-only host checks (inputs present; every E module compiles under the host's
Python 3.10.12).

| Item | Finding | Disposition | Sections |
|---|---|---|---|
| B1 | Section 9's sentence on the D80 (ii) adjudication predates D81 and D82, which found three gold-defect tasks in E's primary set (`5c1a6c3d`, `881deb30`, `8e116af7`) and three label-contradicted z-order candidates on `5c1a6c3d` that the corrected outcome scores as passing; no sensitivity covered them | Fixed: `main` at `746d60d2` merged; section 9 states what D82 found; the D82 gold-defect sensitivity (raw and corrected, on the 110 other tasks) is registered (plan field `gold_defect_tasks_d82`, `analysis.report`); S1a's flagged list stays the flagged set; a test checks the three tasks against D82's `summary.json`. No primary set, rule or DR changes | 5.6, 9, 19, 21 (item 14), 22 (disclosure 11) |
| B2 | The freeze steps ignored the current `main` (ledger row 18, R04), so freezing on the branch would fork the hash chain; nothing checked the sign-off decision id (a rehearsal froze with a nonexistent id and every test passed) | Fixed: `main` merged now; step 1 below merges `main` again, after the sign-off decision is on it, and the freeze runs on the merged tree, so E's row follows `main`'s last row (row 19 as of `746d60d2`). The prereg test refuses a sign-off id that is not a decision heading naming `q2-stage1-successor-e-v1` whose entry signs items 1-14, and, once frozen, an E row that does not follow R04's row | 21, 25 |
| B3 | G-E4, G-E5, G-E6 and the sign-off had not run; E's lane and entry point have never run on the host, which held job 1200 (R04) | Open at audit 1: they are step 2 below. Job 1200 (R04) was still running at 20:31 UTC on 2026-10-11, and this round had read-only host access; G-E4 waits for a quiet host (D80). Closed before audit 2: G-E4 passed (VM job 1206, offline rescoring job 1208) and G-E5 passed (CPU job 1210), each on a quiet host from the export of the draft commit `8a23a483`; evidence in `program/evidence/2026-10-11/q2-stage1-successor-e/gates/`. G-E6 is audit 2 below; the sign-off fills section 21's slot at the freeze (step 2) | 4.1, 25 |
| N1 | E only adds data: estimands, thresholds and rules are S1a's; the differences are disclosed and listed for sign-off | No action | 3, 21 |
| N2 | Independent recomputation reproduced the cap check, the analysis identity and section 12 | No action; both outputs were regenerated after this round's plan change (README of E's evidence) | 7.3, 10 |
| N3 | The freeze rehearsal passed on a scratch clone with `main` merged | No action; the rehearsal is step 3 below | 25 |
| N4 | Host inputs present; E's modules compile under Python 3.10.12 | No action | 4.1 |
| N5 | Section 5.3 said the job-end rule was the reading D57 (ii) settled; D57 (ii) made both readings hold instead, and the VM batch job ends seconds after the lane | Fixed: reworded; the gap is 12 h plus a 5-minute margin (`plan.SESSION_GAP_MARGIN_MIN`, in the plan file), so both readings hold by construction; a GPU job with no final Slurm state counts its Slurm start plus its limit as its end (`lane.job_end`); tests | 5.3, 7.4, 21 (item 3) |
| N6 | Draft-only statements outside the slots (G-E4's "have not run on the host", this log's "None yet") would survive the freeze unchecked (the D32 class) | Fixed: G-E4's statement is dated to the draft and this log holds audit 1; a test refuses both draft-only phrasings in any state; the freeze edits only the five slots (below) | 4.1, 25 |
| N7 | Whether an incomplete DR2 or DR5 counts as E's registered decision was unstated, and the power statement covers complete data only | Fixed: section 18 says it does, under the `incomplete` label, with no power claimed | 18, 21 (item 11), 22 (disclosure 12) |
| N8 | Every cap assumes S1a's longest start-up L = 113 s, uninflated; the 9B margin is 61 s with slots 20% slower | Fixed: disclosed as an assumption, with the p99 margins | 7.1, 22 (disclosure 6) |
| N9 | `cpu-step.sbatch`, `docker-research.sbatch` and `verify_compute_provenance.py` were unpinned, and the prereg test did not recompute E's import closure | Fixed: section 23's infrastructure table pins them with the GPU container's other checks and OE's builder and extractor; the prereg test checks their digests and E's import closure | 23 |
| N10 | The owner reported 293 passed and 4 skipped for the S1a and design suites; the same files give 310 passed and 3 skipped | Fixed in the record: this round's counts are stated in `program/log.md` | — |
| N11 | The development smoke never runs the `e` purpose's checks, so E-9B-E1 is their first host run | Disclosed | 4.1 (G-E4), 22 (disclosure 10) |
| N12 | The X test is conservative at S = 4; optionally report the exact per-cell flip | Fixed in the text: the registered label-permutation sensitivity is, at R = 1, the exact per-cell sign flip, and section 11 now says so; no code change | 11 |

**Audit 2** (2026-10-11/12; G-E6: a fresh, independent auditor on the draft at `d6293900`,
with `main` at `2b8fadc7` already merged; verdict: ready to freeze, no blocking items). Its
checks are in its rows: an independent recomputation of the committed evidence and of the X
test's null size, the gate records against their host originals, tampered manifests against
the lane, and a freeze rehearsal on a scratch clone. It read the host without writing to it,
except for item A2-N14, and committed nothing; the real ledger stayed at 18 rows.

| Item | Finding | Disposition | Sections |
|---|---|---|---|
| A2-N1 | Scope: `main` (`2b8fadc7`) is an ancestor of the draft; the ledger has 18 rows and is untouched. Three things remain before the real freeze: audit 2's rows in this log, G-E6's slot naming this audit, and the section 21 sign-off committed on `main` (its heading names `q2-stage1-successor-e-v1` and its entry signs items 1-14), then `main` merged again | The first two are done (this table; G-E6's slot); the sign-off and the merge are steps 1 and 2 below | 4.1, 21, 25 |
| A2-N2 | E only adds data: estimands, thresholds, DR0-DR5, P1-P5, M and the frozen estimators are S1a's; every file of S1a section 20 keeps its SHA-256, and section 23's 11 E files and 8 infrastructure files match the tree; the differences (the 113-task primary set, four sessions at R = 1, caps by arithmetic, the D82 sensitivity) are disclosed and listed for sign-off. Recomputed: `analysis-identity.json` and `cap-sufficiency.json` equal the committed files byte for byte but for provenance; no harness code changed since `acb886c5`. Section 11's conservative X test, checked independently: the frozen `x_signflip_p` at S = 4, R = 1, K = 113 with no harness effect (2,000 data sets x 2,000 flips) had size 0.0175, 0.0145 and 0.010 at α = 0.025 (task success 0.5, U(0.2, 0.8) and Beta(0.3, 0.6)) | No action | 3, 10, 11, 21, 23 |
| A2-N3 | The gate records are genuine and E's lane and entry point ran: every committed file under `gates/ge4`, `gates/ge5` and `gates/scripts` equals its host original by SHA-256; the host export equals `git archive 8a23a483` file for file (7,567 files); the preflight names `q2e-vm.sbatch` (`2d27bbe5`) and no GRES; the manifest's schema is E's, which S1a's lane refuses; the four scored `E1` records could only come from E's driver; 1208 and 1210 ran with no network and no GPU; the GLMM output matches G-E5's slot; `check_gates.py` reproduces `gates-check.json` but for `checked_at_commit`; the lane's snapshots saw no foreign Slurm job, and R04's job 1211 was submitted one second after 1210 ended | No action | 4.1 (G-E4, G-E5) |
| A2-N4 | Caps and session timing are enforced: on the frozen rehearsal tree the rendered E-9B-E1 manifest validates (226 slots, GPU cap 52, VM limit 62 minutes, 90 CPUs) and the development manifest is refused; the lane refused all 12 tampered variants tried (a swapped task or harness, 4B labels at a 9B cap, E2 with no prior jobs, rerun 2, step cap 20, settle 30 s, cap 53, V = 21, setup-only mode, an extension block, a fake engine), and `check_slurm` refused three more; code review confirms the `e` purpose's frozen-registration, prior-job, gap, engine and Slurm-limit checks, and that E's gap check is the only one | No action | 5.3, 6.2, 6.3 |
| A2-N5 | Freeze rehearsal on a scratch clone of `d6293900` (merging `main` was a no-op): the status paragraph replaced by the quoted paragraph below, G-E6 and the sign-off filled (a rehearsal decision D999 appended to `decisions.md`); `freeze` accepted as row 19 after R04's row (hash `f7b350a3...`); `check-chain` (19 rows) and `verify` passed; on the frozen tree E's suites gave 60 passed and 2 skipped, the full suite 2,864 passed and 71 skipped. The same freeze with sign-off id D82 fails the sign-off test. On the draft tree E's suites gave 62 passed, S1a's and the design study's 310 passed and 3 skipped; ruff passes | No action; step 3 below repeats the rehearsal on the tree that holds the sign-off | 21, 25 |
| A2-N6 | Exactly three placeholders remained (the status paragraph, G-E6's record, section 21's id), each one the freeze fills; the guard refuses to freeze while any remains | No action; G-E6's is now filled, so two remain | 4.1, 21, 25 |
| A2-N7 | "At the freeze" said the freeze edits five slots that each hold the placeholder (audit 1's N6 put it so too); since `d6293900` G-E4 and G-E5 hold their results. The sentence survives the freeze (D32 class) | Fixed: it says the freeze fills the three slots that still held the placeholder and that G-E4's and G-E5's results were filled from their records before it (step 2) | 25 |
| A2-N8 | B3 read "Open" and would be frozen so; this audit's items were not in the log | Fixed: B3 is closed above (G-E4: jobs 1206 and 1208; G-E5: job 1210; evidence in `gates/`); this table | 25 |
| A2-N9 | Section 19 promised every estimand on S1a's 32 base tasks raw and corrected, but `analysis.report` computes `secondary_s1a_base` on raw verdicts only and `section15.py` adds nothing for it (the gap S1a covered with an operator step under D59 (iii)); reporting only, no rule reads it | Fixed in the text: section 19 says raw on both sets, checker-corrected on the primary set and the D82 110-task set; `analysis.py` is unchanged (its section 23 digest stands) | 19 |
| A2-N10 | Cosmetic: the draft status paragraph still listed G-E4 and G-E5 as open; the evidence README said no host job ran for its bundle while `gates/` holds jobs 1206, 1208 and 1210 | Fixed: the status paragraph lists only the open slots (the freeze still replaces it whole); the README points to `gates/README.md` | status paragraph; E's evidence README |
| A2-N11 | Optional test hardening: the open-slot test accepted **failed** for G-E4, a gate that must pass (G-E5 may fail and be disclosed) | Fixed: `test_open_slots_and_the_frozen_status_wording` requires G-E4's slot to read **passed** (G-E5's may read passed or failed), and accepts G-E6's slot filled only with the verdict ready and an audit this log holds | 4.1 |
| A2-N12 | Optional wording: section 5.3 said the 5-minute margin makes the 12 hours hold at the VM batch job's end "by construction", but the lane does not observe the batch end; the margin covers the lane's GPU-end wait (up to 180 s plus a 5 s poll) and the cleanup | Fixed: "with a margin" | 5.3 |
| A2-N13 | Optional hardening, as in S1a: nothing in the lane refuses a second run of the same E job (E-9B-E1's prior-job list is empty); "no job is rerun to improve an outcome" (sections 7.2 and 17) rests on operator discipline and the Slurm job ids in the receipts | Reporting only; no code change. As in S1a, it rests on operator discipline, and the receipts' job ids show any rerun | 7.2, 17 |
| A2-N14 | The auditor's own deviation from read-only host access: it copied a 1 KB helper script to the host's `/tmp` to hash the export tree, ran it and deleted it (confirmed gone); nothing in the repository checkout, the run root or Slurm was touched, and later reads piped the script over stdin | Recorded; no action | — |

### At the freeze

The freeze fills the three slots that still held the guard's placeholder once G-E4 and G-E5
had run: G-E6's audit record (filled from audit 2's record in the last pre-freeze edit),
section 21's decision id, and the status paragraph. G-E4's and G-E5's results were filled from
their records before it (step 2). Audit rounds after audit 1 add their rows to the review log
above before the freeze.
The freeze replaces the whole status paragraph at the top of this file, from its first line to
the line before the first bullet, with the paragraph below, word for word (its line breaks may
differ). Nothing else in that paragraph survives.

> **Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the
> freeze time and `git_head_at_freeze`.** The development smoke (G-E4) and the GLMM shape run
> (G-E5) ran on CPU before the freeze, from the draft commit named in their records; no E GPU
> job ran before it. Section 21 records the program's sign-off. OE and every E job run from an
> export of the freeze commit, the commit that adds this file's ledger row, and E's lane admits
> an E job only while this file's SHA-256 equals that row's and refuses the development purpose.
> A material change after the freeze is a new experiment id.

The steps, in order:

1. **Merge `main`.** Before any slot is filled for the freeze, `main` is merged into the
   branch, and again after the program's sign-off decision is committed on `main`, so the
   tree holds that decision and every ledger row frozen on `main`; E's suite and S1a's suite
   pass on the merged tree. The freeze runs on that merged tree, so E's row follows `main`'s
   last row (row 19 as of `746d60d2`), and the freeze commit is merged to `main` before any
   other registration is frozen there.
2. G-E4 and G-E5 run (CPU only, on a quiet host) from an export of the draft commit; their
   results fill their slots; the audit of G-E6 runs and its record fills its slot; the program's
   decision, merged in step 1, fills section 21's slot.
3. On a scratch copy of the tree frozen into a copy of the ledger, `scripts/preregister.py
   freeze` is accepted, `check-chain` and `verify` pass, and E's suite and S1a's suite pass;
   only then is the real freeze run.
4. The filled file is committed; `scripts/preregister.py freeze q2-stage1-successor-e-v1
   program/preregistrations/q2-stage1-successor-e-v1.md` adds the row; `check-chain` and
   `verify` pass; the row is committed alone. That commit is the freeze commit.
5. After the freeze commit: `program/state.json` and `program/log.md` record the freeze; OE runs
   from the freeze commit; then E-9B-E1.
