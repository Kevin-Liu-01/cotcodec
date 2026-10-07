# Preregistration: serving-throughput-probe-v2

Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row for the
freeze time. A material change to this file, to the contract or to the probe code
after the freeze is a new experiment id.

## 1. Identity

- **Experiment id:** serving-throughput-probe-v2.
- **Predecessor.** serving-throughput-probe-v1 (ledger row
  `13c72ac3259c8c0a886bad66e5368a37a11f6dd0afb8ad3119a33791bdd47803`, frozen file
  SHA-256 `f0db1a8e939694169e17141a2e9bb61f2d6281d71747f6ef607a0392f9a21784`;
  evidence `program/evidence/2026-10-07/serving-throughput-probe-v1/`). v2 adds
  new files beside v1's. v1's registration, contract, manifests, code and probe
  code digest are unchanged, and no v1 measurement enters any v2 number: v2
  measures every point it registers fresh. v1's values appear here only as
  design inputs (sections 2, 4 and 8), labelled as such.
- **Question.** Q2 only: the per-step latency of closed-loop computer-use
  episodes on Qwen3.5-9B under two harness layouts and two observation types, the
  open-loop bracket and the front-end correction, priced by v1's Q2 budget rules;
  and control X1, whether vLLM dummy weights cost what real weights cost on
  identical prompt token sequences.
- **Claim level.** Infrastructure evidence ("admission pass"). Nothing here is a
  scientific result about models, harnesses or checkers.
- **Code revision.** The job runs from the source capsule of a commit X of `main`
  that contains this file's ledger row (X is pushed, then cloned on the host). X is
  recorded in the manifest (`git_sha`), the lane's provenance verification and
  the evidence bundle. The overlay image bakes in X's source, so it is built from
  X after the freeze. X may differ from the freeze commit only outside the probe
  code and the contract, which must be byte-identical to what this file names
  below; G0.0 checks this.
- **Contract.** `experiments/serving/serving-throughput-probe-v2.yaml` holds every
  engine flag, point, seed, gate threshold, launch-window reservation and budget
  parameter named below. Its SHA-256 is
  `cc7da49083bba1d6c82a30680a63c75b826a6244154ff54afb9d68dc1c2ddd50`.
  Every point file and the summary record the contract SHA-256 they ran under.
- **Probe code.** `scripts/run_vllm_throughput_probe_v2.py`, every module of
  `harness/serving_probe_v2/`, and the frozen v1 code they import:
  `scripts/run_vllm_throughput_probe.py` and every module of
  `harness/serving_probe/`. Their digest, the SHA-256 of the compact JSON list of
  [path, file SHA-256] pairs sorted by path (`run_vllm_throughput_probe_v2.py
  digest` prints it), is
  `db43047b23e04301a7e1bcc0bf419eecb394533883c5b48f3284d7aa7bae6787`.
- **Binding.** Gate G0.0 (in the image) and `project` (on the host) verify this
  file against the ledger and refuse unless its frozen text names the contract
  SHA-256 and the probe code digest they compute from the files they run. A
  changed threshold, rule or line of probe code, v1's included, therefore stops
  the experiment.
- **Runtime.** As v1: vLLM v0.31.0, commit
  db9527a46873454610df6dbedf79a36d6bf1a7f6, base image
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  (CUDA 12.9.1, local image ID
  sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b), run
  through the overlay `infra/research/Dockerfile.vllm-overlay` built by
  `scripts/build_vllm_overlay_on_h100.sh`, which removes the CUDA 13 torchcodec
  build and, for v2, also runs `run_vllm_throughput_probe_v2.py plan` and
  `vllm-args-doctor` on CPU. The overlay image ID is recorded in its build receipt
  and in the manifest. v2 runs on the cu129 image only.
- **Lane.** `scripts/submit_docker_research_job.py` with `container_profile: vllm`,
  `seed_binding.flag: --seeds`, one H100, TP=1; the manifest is rendered by
  `scripts/render_serving_probe_v2_manifest.py` from the overlay build receipt.
  The driver parses its options with abbreviations disabled.
- **Data.** Synthetic only: random-token text, rendered PNG screenshots and
  random-pixel JPEG screenshots, all derived from the seeds below.
- **GPU budget.** Job A: 60 minutes on one H100, 1.0 GPU-h, D8's probe cap. The
  overlay build: one idle H100 for at most 10 minutes, 0.167 GPU-h, accounted
  separately as D17 does for v1. Nothing else uses a GPU. With v1's timings job A
  takes about 27 minutes (design decision 12).

### Model

| Role | Model and revision | Weights | Pin |
|---|---|---|---|
| Q2 9B rung, real-weight phase | Qwen/Qwen3.5-9B @ c202236235762e1c871ad0ccb60c8ee5ba337b9a | real, lane-verified | receipt 0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3, artifact root 9845026dbe255e24b105224eebbb5436d315713b9a5c53c434137896b160c5b1 |
| Control X1, dummy-weight phase | same 9B config | `--load-format dummy` | same snapshot |

## 2. What v1 left open, and the scope of v2

v1's job A (Slurm 442) was accepted with cuts and its job B (Slurm 446) was
accepted complete. Its Q2 projection is "incomplete: re-probe" and its control X1
"fail". The cells, and what v2 does with each:

| v1 cell | v1 outcome | v2 | Why |
|---|---|---|---|
| r3 (H2 replay) | invalid twice, only `no_contamination` | required | the H2 profile; no Q2 budget without it |
| r4 (H2 thinking) | invalid twice, only `no_contamination` | required | the thinking penalty of every H2 cell |
| a1b, a1c (A1 seeds) | truncated, not run | required | the A1 noise multiplier (otherwise at least 1.10 on every cell) and X1's power |
| r2 (H1 accessibility tree) | not run | optional | conservative fallback in the rules (prompt-proportional x1.5) |
| a2 (open loop at C=40) | not run | optional | conservative fallback (the slowest valid A1 seed) |
| f1 (PNG front end) | not run | optional | its correction can only raise the bound; absent, none is applied |
| d8 (A/A batch invariance) | not run | dropped | reported only in v1; no budget rule reads it |
| a6 (20 random JPEGs, open loop) | not run | dropped as a point | no budget rule reads it; its 20-image shape is the warm-up's (design decision 5) |
| a1a, r1 | valid | required, measured fresh | the Q2 rules need a same-id H1 profile and A1 reference; they are also X1's real-weight side |
| X1 (x1-smoke, x1-a1, x1-r1) | fail, comparison not like for like | required, redesigned | design decisions 8 and 9 |
| job B (Q1, 7 points) | all valid, Q1 within cap | dropped | design decision 2 |
| job C (27B and 35B-A3B rungs) | not run (X1 fail) | dropped | design decision 2 |

## 3. Claim boundary

- Inference-only GPU cost of Q2's Stage 1; VM time is simulated (`t_env`);
  checker, verification and timing costs are excluded. Q1 is not projected by v2.
- Synthetic prompts and fixed output lengths: every request sets
  `ignore_eos=true` and `min_tokens = max_tokens` (300 or 2,048 tokens).
- Every replay builds its assistant history from prebuilt responses (300 tokens
  of random text per step), never from generated text, so prompts are a harness
  setting and identical across engines (design decision 7).
- Only the real-weight phase prices Q2. The dummy-weight phase is control X1,
  whose outcome is reported and enters no v2 budget (design decision 10). The
  27B and 35B-A3B rungs keep v1's active-parameter rule.
- MTP and speculative decoding are off; server points run greedy; the engine
  serves `max_model_len` 131,072, as in v1.
- Generated text is never executed, parsed, kept as history or written to disk.
  Only token counts and SHA-256 digests of prompt token ids are stored.

## 4. Design decisions

Freezing this file requires the owner's acceptance of design decisions 1 to 24,
recorded in `program/decisions.md` (as D17 and D18 were for v1). D8's probe cap
of 1.0 GPU-h and D17's separate accounting of the overlay build stand.

1. **New id, new files, no reuse.** v2 is `serving-throughput-probe-v2`, with its
   own contract, registration, manifest template, renderer, driver and package
   (`harness/serving_probe_v2/`). The frozen v1 package and driver are imported,
   not edited, so v1's digest
   (`15b7a73b39dca0bf03959b8943450dc1d862ed6f5a158adcbca8fe763c817277`) still
   matches its files; v2's digest covers them as well. No v1 point enters a v2
   number.
2. **Scope: job A only; jobs B and C are dropped.** *Job B.* v1's Q1 projection is
   "within cap" with the x1.5 unvalidated-dummy penalty already applied and a
   stable B1 noise multiplier of 1.0 (B1 range 1.03%): single turn 2.92 GPU-h
   against the 6 GPU-h cut, three turns 10.21 against 12. A new X1 could only
   remove the penalty and lower both, so no v2 measurement can change the Q1
   decision; Q1's budget remains v1's result. *Job C.* As a design input only, v1's
   points r3 and r4, which failed nothing but the contamination check, were put
   through the frozen Q2 rules (exploratory, post hoc): 529.7 GPU-h in all, 133.9
   from the 4B and 9B rungs, whose multiplier is 1 and needs no dummy weights.
   Even with every other input at its most favourable (A1 noise 1.0, the closed
   loop binding, no accessibility penalty) the total is 396.2 and the 4B and 9B
   rungs alone 101.7, above the 90 GPU-h rescope line. Job C changes only the
   27B and 35B-A3B multipliers, so it could change the decision only if v2's 9B
   cost per rung came out below 45 GPU-h (0.88 of that most favourable value)
   and the measured rung ratios were low enough. Without it, v1's conservative
   stand-in applies (max(1, active parameters / 9B) x 1.5: 4.5 and 1.5, for a
   27B FP8 rung with three times the 9B's parameters and a 3B-active MoE rung),
   so dropping it biases the decision toward rescoping, not toward an
   under-budget, and keeps v2 within one 1.0 GPU-h job.
3. **Which cells are required.** Required: the cells v1 invalidated or did not
   deliver that the Q2 decision depends on (r3, r4, a1b, a1c, X1), and the
   delivered cells the rules need from the same id (a1a, r1). Optional: undelivered
   cells with a conservative fallback already in the rules (r2, a2, f1). Dropped:
   cells no rule reads (d8, a6) and the jobs of design decision 2.
4. **Foreign processes are identified by PID.** A poller lists the compute
   processes on the GPU (`nvidia-smi --query-compute-apps=gpu_uuid,pid,
   process_name,used_memory`) every 2 s, with the device's `memory.used` read
   right after. G0.8 now also requires that the GPU lists no compute process
   before an engine starts. At the reservation (G0.9) the listed PIDs are the
   engine's own when they are in the engine's process tree in this container,
   or, when NVML reports host-namespace PIDs that `/proc` in the container
   cannot resolve, when they are the PIDs that appeared on the GPU (empty at G0.8)
   while the engine started and stayed unchanged through the warm-up. From then
   on a listed PID outside that set and outside the engine's tree is a foreign
   process, and the point is contaminated, however little memory it holds. NVML
   inside a container reporting host PIDs is a user report (section 12), not
   NVIDIA documentation; the rule records which attribution applied and falls
   back to the device rule (design decision 5) when NVML lists nothing.
5. **The engine's own growth is bounded by a largest-shape reservation.** v1
   measured its reservation 5 s after a one-image smoke (74,301 MiB); the engine
   then grew to 75,047 MiB under a1a, 75,807 under r1 and 76,611 under r3's
   20-screenshot prompts, above 74,301 + 2,048 = 76,349, with no other process
   on the GPU. In v2 each phase runs a warm-up after its smoke: 20 cold H2
   requests at step 20 (20 screenshots, 19 prebuilt responses, 48,140 modelled
   prompt tokens each, 300 output tokens, all in flight at once). The contract
   loader refuses any later point of the phase whose largest request has more
   prompt tokens, more images, or more tokens in flight (concurrency times prompt
   plus output) than the warm-up. The reservation is the largest device memory
   over the warm-up and the 5 s after it. With PID attribution ("pid" mode), the
   engine's own memory above its reservation plus 2,048 MiB is flagged
   (`own-footprint-above-reservation`) and is not contamination. Without it
   ("device" mode) the device peak must stay within the largest-shape reservation
   plus 2,048 MiB, as v1's rule did with its smaller reservation.
6. **Memory no process accounts for.** In pid mode, device memory minus the
   engine's listed memory may not exceed what it was at the reservation plus
   1,024 MiB (G0.8's idle threshold), so a process NVML does not list is still
   caught once it holds more than that.
7. **Prebuilt replay history.** v1 fed each step's generated text back as
   history, and the two engines' outputs re-tokenised to different lengths: from
   step 1 to step 2, r1's mean prompt grew by 2,259 tokens and x1-r1's by 2,052,
   of which 2,042 are the new screenshot, so v1's x1-r1 prompts were 6.6%
   shorter than r1's overall. Every v2 replay (r1, r2, r3, r4,
   the warm-ups, x1-r1) builds step t from the same seeded prebuilt responses
   (300 tokens each), so a step's prompt depends only on the point's seed and
   parameters. The prompts match the 300-token responses the extrapolation
   already models, and are longer than v1's real-output histories, which can only
   raise the budget. In r4 the step-18 history is a 300-token prebuilt response,
   not step 18's 2,048-token thinking output, so the thinking penalty prices the
   output length alone.
8. **Prompt token ids are digested.** Every v2 request sets `return_token_ids`;
   vLLM v0.31.0 then streams the prompt's token ids in the first chunk (section
   12). The client stores, per request, the SHA-256 of those ids (as little-endian
   int64) and the prompt token count, and keeps no text. If the server returned no
   ids, the identity check rests on per-request prompt token counts, and says so.
   The extra serialisation applies to every point and both phases alike.
9. **X1 on identical token sequences, with thresholds from v1's noise.** x1-a1
   and x1-r1 repeat a1a and r1 (same seeds and parameters) on dummy weights. X1
   first requires that every request of x1-a1 and x1-r1 sent exactly the prompt
   token sequence of the same request of a1a and r1; otherwise it is
   "not-comparable". Thresholds: open-loop request throughput within 5% (v1's
   identical-prompt delta between a1a and x1-a1 was 0.86%); mean replay latency
   within 8%; the replay delta's standard error at most 5%; a1a, a1b and a1c
   valid with a throughput range of at most 5%. The 8% is about 2.1 standard
   errors of the difference of two r1-shaped replay means as v1 measured them:
   the per-step standard errors recorded in r1 and x1-r1 give 2.84% and 2.70% of
   the mean per point and 3.81% for the difference, and the one step v1 sent
   identically to both engines, step 1, differed by 3.01% with a standard error
   of 2.61%. Section 8 gives the rule's operating characteristics.
10. **What X1 decides in v2.** v2 prices no dummy-weight measurement: the rung
    multipliers use the active-parameter rule and Q1 is not projected. X1's
    outcome is reported, with its identity checks, deltas and standard error, as
    the node's dummy-weight admission record for later registrations, which must
    cite it under their own ids.
11. **Launch-window ledger.** v1 reran an invalid point at once, and the reruns of
    r3 and r4 (about 10 minutes) used up the real phase's launch window, so a1c,
    r2, f1, a2, d8 and a6 never launched. v2 reserves time: each phase reserves
    its start allowance (G0.8 and the engine start: 4 minutes real, 3 dummy) plus
    the wall caps of its required points, and the contract loader refuses a job
    whose preamble (2 minutes, G0.0 to G0.4) and reserved phases do not fit before
    the soft stop (43.5 of 51 minutes, leaving at least 7.5 minutes of slack). A
    phase may launch until its bound, the soft stop minus the reservations of
    later phases. Required points run first; a required point's first attempt
    launches whenever the bound has not passed. Every point gets at most one
    rerun, and a rerun or an optional point launches only from slack: now plus
    its cap plus the caps of the phase's required points still to run must fit
    before the bound. Reruns wait until every required first attempt of the
    phase has run; required reruns go before optional points, and optional
    reruns last. A rerun that does not fit is recorded as not launched and the
    point keeps its invalid attempt. The smoke and the warm-up keep v1's
    immediate single rerun (their gates need it), also from slack.
12. **Allocation and caps.** One job of 60 minutes on one H100 (1.0 GPU-h). Point
    caps are about 1.5 to 2.2 times v1's attempt times (preparation included):
    r3 12 minutes (v1 7.6), r4 3.5 (2.4), r1 and x1-r1 2.5 (1.4 each), a1a,
    a1b, a1c, f1 and x1-a1 1.5 (0.7), smokes 1.5 (under 0.1), warm-ups 2.5 (an
    estimate from v1's cold r4 step 18: 21 s to the first token at 20 concurrent
    43,811-token requests), r2 3.5 and a2 2 (estimates from r1 and a1a). With v1's
    times the job takes about 27 minutes (about 0.45 GPU-h).
13. **Order.** Real phase: smoke, warm-up, a1a, r1, r3, r4, a1b, a1c, then r2,
    a2, f1. Dummy phase: smoke, warm-up, x1-a1, x1-r1. a1a and r1 follow the
    warm-up as x1-a1 and x1-r1 do, so both sides of X1 run in the same position;
    both warm-ups send identical requests (seed 105).
14. **cu129 only.** v1 passed every cu129 gate on this node, so v2 has no
    pre-approved cu130 retry: a gate failure that ends job A as a pre-result ends
    v2 as a pre-result, and another run needs a new id.
15. **Rungs.** The 27B and 35B-A3B rungs keep v1's unmeasured rule, max(1,
    active parameters / 9B) x 1.5 (4.5 and 1.5), flagged on every cell; the 4B
    rung uses the 9B's costs, as in v1.
16. **Q2 rules are v1's.** The projection calls the frozen
    `harness.serving_probe.budget.project_q2` with job A's points and no job C:
    the profiles, extrapolation, open-loop bound, front-end correction, noise
    multiplier, context check, sensitivity table and decision thresholds are v1's
    (section 9).
17. **G0.9 is a phase gate.** Acceptance is v1's rule (section 6) with G0.9
    among the per-phase gates G0.5 to G0.9, so a failed G0.9 in the dummy phase
    leaves the job acceptable and X1 not-run, and a failed G0.9 in the real phase
    ends the job as a pre-result.
18. **Digest scope.** The digest covers the v2 package and driver and the v1
    package and driver they import. The renderer, the overlay builder, the lane
    and `scripts/preregister.py` are fixed by commit X, as in v1.
19. **Overlay and fetch.** v2 needs a new overlay image (it bakes in X's source):
    one idle H100 for at most 10 minutes (0.167 GPU-h), accounted separately as
    D17 does for v1. v2 serves only the cached, receipted Qwen3.5-9B snapshot, so
    there is no metadata fetch.
20. **The compute-process poller is the probe's.** The lane's GPU prolog checks
    exclusivity once, on the host, before the container starts; v2 does not change
    the lane. A host-side poller would see every PID in one namespace, but it is a
    lane change with its own review.
21. **Residual attribution risk.** A foreign process that starts after G0.8 and
    before the end of the warm-up, and stays, is counted as the engine's own in
    pid mode and raises the reservation in device mode. The window is a few
    minutes on a GPU that the lane prolog and G0.8 found idle; the PIDs and their
    memory are recorded at every snapshot, so such a case is visible in the
    evidence.
22. **Resume.** As v1, a resumed job skips terminal points and reruns
    interrupted, failed-infra and not-run points; an invalid point whose rerun
    was still pending when a signal arrived gets that rerun, under the same slack
    rule. No GPU resume run is made (a probe has no training state; D17).
23. **Fail-closed reservation.** G0.9 fails, and the phase stops, when the warm-up
    is not valid, when the device sampler gave no sample, when a process of this
    container outside the engine holds the GPU, or when the listed PIDs change
    inside the reservation window.
24. **What v2 does not change.** Gates G0.0 to G0.7 and G0.8's device
    conditions, the smoke, the counter and cache checks, the signal-checkpoint marker, the acceptance rule, the lane
    termination check, the engine settings, the point shapes and seeds of the
    cells it keeps, and the Q2 rules are v1's.

## 5. Step-0 gates

All must pass, otherwise the job outcome is "pre-result" (driver exit code 2) and
no number enters a budget. Phase gates (G0.5 to G0.9) are recorded per phase.

- **G0.0** This file verifies against the ledger in the image, at the path the
  contract names, and its text names the SHA-256 of the contract the driver loaded
  and the digest of the probe code in the image.
- **G0.1** The lane's provenance verification printed status PASS, its container
  doctor printed `STATUS PASS`, and its bound-model verification reports
  qwen3.5-9b, its revision, its artifact root and mode `full`.
- **G0.2** `cuInit` returns 0; exactly one H100 is visible; vLLM is 0.31.0 and
  `VLLM_BUILD_COMMIT` equals the commit above (v1's CUDA doctor).
- **G0.3** The bf16 4096 x 4096 GEMM's maximum absolute difference from fp32,
  over the maximum fp32 value, is below 0.01 and finite.
- **G0.4** A Triton kernel compiles under the job's output directory, returns
  exactly `x + y`, and no `/tmp` file is mapped into the doctor.
- **G0.5** The engine becomes ready (`/health` 200) within 900 s in default mode
  (torch.compile and CUDA graphs), else one eager start, as in v1.
- **G0.6** The 16-request smoke at concurrency 8 completes with 0 failures and
  every output at its length; one image adds 2,040 ± 2% prompt tokens.
- **G0.7** For the smoke and every later point: the generation-token counter
  delta equals the client's output total and the prompt-token delta is within 1%
  of the client's prompt total.
- **G0.8** Before every engine start (and before an eager retry, after up to
  90 s for the failed engine's memory to be released): after a 2 s settle, every
  500 ms sample over 10 s shows `memory.used` below 1,024 MiB and utilisation
  0%, and the last readable compute-process listing in that window lists no
  process. A listing that cannot be read leaves this condition "unavailable"
  (recorded); the device conditions still apply.
- **G0.9** (new) After the smoke, the phase's warm-up is valid, and over the
  warm-up and the 5 s after it: the device sampler reported at least one sample;
  no process of this container outside the engine is listed; the listed PIDs did
  not change. It records the reservation (largest device memory), the attribution
  mode and its basis, the engine's PIDs and memory, and the unaccounted memory.

## 6. Failure path and acceptance

- **G0.5 fails, eager start succeeds:** as v1; the job continues eager, is
  accepted and labelled eager.
- **Acceptance of the job.** Slurm `JobState=COMPLETED` with `ExitCode=0:0`, the
  lane's `termination.env` recording `reason=completed` and `exit_code=0`, and
  `summary.json` showing `acceptance.accepted: true` (status complete or
  complete-with-cuts, G0.0 to G0.4 passed). `project` admits job A's points only
  if its summary belongs to this experiment, contract and job, records
  `acceptance.accepted: true`, agrees with the acceptance recomputed from its own
  status and gates, records driver exit code 0, and lists the SHA-256 of exactly
  the point files on disk, and the lane's `termination.env` in the run directory
  (the parent of `/outputs/probe`) records `reason=completed` and `exit_code=0`.
  A job that is not admitted is reported with its reasons; none of its points
  enters a budget, X1 is not-run and the Q2 outcome is "incomplete: re-probe".
- **A gate failure ends job A as a pre-result:** G0.2, G0.3 or G0.4, or G0.5 to
  G0.9 in the real-weight phase (G0.5 only when the eager start fails too). v2 is
  then "pre-result"; there is no cu130 retry (design decision 14).
- **A gate failure in the dummy-weight phase** does not end the job: that phase's
  points are not run, the job can still be accepted, and X1 is not-run.
- A G0.0 or G0.1 failure is not a runtime failure; a resubmission once the cause
  is fixed needs the owner's approval of the extra GPU time.

## 7. Points, seeds, launch window and sample sizes

Seeds set prompt text (`numpy.random.default_rng([seed, 1, ...])`) and images
(`[seed, 2, ...]`) independently. The manifest declares seeds [42, 43, 44] and
binds them through `--seeds`; the driver refuses any other list. Screenshots are
1920 x 1080 (2,040 visual tokens each). The prefix, multimodal and encoder caches
are reset before every point.

**Job A** (Qwen3.5-9B, TP=1, prefix caching on, `max_model_len` 131,072,
`gpu_memory_utilization` 0.90, `max_num_seqs` 256, `max_num_batched_tokens`
8,192, `limit_mm_per_prompt` 20 images at 1920 x 1080 and no video,
`generation_config` vllm, engine seed 42); allocation 60 minutes.

| Point | Phase | What | Requests | Seed | Cap (min) | Required |
|---|---|---|---|---|---|---|
| a-smoke | real | gates G0.6, G0.7: 16 at C=8, 1 PNG, O=64 | 16 | 7 | 1.5 | yes |
| a-warmup | real | G0.9: 20 cold H2 requests at step 20, O=300, all at once | 20 | 105 | 2.5 | yes |
| a1a | real | S2 open loop: prefix 1,536 + body 4,608 + 1 random JPEG, O=300, C=16 | 96 | 42 | 1.5 | yes |
| r1 | real | H1 replay (window 4), V=40, steps 1-6, O=300 | 240 | 101 | 2.5 | yes |
| r3 | real | H2 replay (folding), V=20, steps 1-24, O=300 | 480 | 103 | 12 | yes |
| r4 | real | H2 thinking: prebuilt 17 steps, steps 18-19, O=2,048, V=20 | 40 | 104 | 3.5 | yes |
| a1b | real | a1a shape | 96 | 43 | 1.5 | yes |
| a1c | real | a1a shape | 96 | 44 | 1.5 | yes |
| r2 | real | r1 plus 6,144 accessibility-tree tokens per step | 240 | 102 | 3.5 | no |
| a2 | real | a1a shape at C=40 | 160 | 45 | 2 | no |
| f1 | real | a1a with rendered PNGs | 96 | 42 | 1.5 | no |
| x1-smoke | dummy-control | as a-smoke | 16 | 7 | 1.5 | yes |
| x1-warmup | dummy-control | as a-warmup | 20 | 105 | 2.5 | yes |
| x1-a1 | dummy-control | exactly a1a's requests | 96 | 42 | 1.5 | yes |
| x1-r1 | dummy-control | exactly r1's requests | 240 | 101 | 2.5 | yes |

Replay details as v1: system prompt 1,536 tokens shared within a point, task 64
tokens per episode, action strings 16 tokens, prebuilt responses 300 tokens,
`t_env` 2.5 s, starts staggered over 2.5 s (not for the warm-ups).

**Launch window.** Soft stop at 85% of the allocation (51 minutes after the
lane's `started_at`), hard stop 4 minutes before its end (56 minutes). Reserved:
preamble 2, real phase 4 + 26.5, dummy phase 3 + 8 (43.5 minutes). The real
phase's bound is 40 minutes, the dummy phase's 51.

**Minimum detectable effects and power.**
- Per-step replay latency: the standard error of each step mean (sample SD over
  the step's V requests divided by √V) is recorded in every replay point; at a
  coefficient of variation of 0.3 it is about 5% (V=40) or 7% (V=20) of the mean.
- A1 throughput: three seeds; noise multiplier 1 if all are valid within a 10%
  range, max/min if the range is wider (UNSTABLE), and at least 1.10 with fewer
  than three valid seeds. The rule and its code are v1's.
- X1: see section 8.
- The Q2 decision changes only when the total crosses 90 or 15 GPU-h. With v1's
  r3 and r4 values (design decision 2, exploratory) the total sits several times
  above 90; the decision is sensitive mainly to the H2 profile, which v2 measures.

## 8. Metrics, validity, contamination and control X1

**Per point (unit: one point)** as v1: duration; planned, completed and failed
requests; prompt and output tokens; request, output-token and total-token
throughput; TTFT, TPOT, ITL and end-to-end latency (mean, SD, SE, p50, p90, p99);
for replays, per-step latency, TTFT, TPOT and mean prompt tokens, wave wall time
and mean episode active time; counter deltas, prefix-cache hit rate and
preemptions; peak KV-cache use and waiting requests; device peak memory, mean
utilisation, power and SM clock; API-server and client CPU; preparation time. New
in v2: per request, the prompt-token-id SHA-256 and prompt token count
(`request_identity`); per point, the compute-process listings summarised
(`compute_apps`) and the contamination details.

**Validity.** A point is valid only if it ran to its end and: failed is 0;
completed equals planned; every completion has its requested output length; the
G0.7 counter check holds; every cache reset before it succeeded; the device
sampler delivered at least max(1, floor(0.2 × wall seconds / 0.5 s)) samples; and
the contamination checks below hold. API-server or client CPU of 90% or more
flags the point (front-end-bound, client-bound) and leaves it valid.

**Contamination (every point after G0.9).**
- *pid mode:* at least max(1, floor(0.2 × wall seconds / 2 s)) readable listings
  in the point (`attribution_sampled`); every listed PID is the engine's: in its
  process tree, or in the set fixed at G0.9 (`no_foreign_process`); in every
  listing, device memory minus the engine's listed memory is at most the
  reservation's unaccounted memory plus 1,024 MiB (`no_unattributed_memory`). The
  engine's memory above its reservation plus 2,048 MiB, or a device peak above the
  largest-shape reservation plus 2,048 MiB, is a flag, not a failure.
- *device mode:* the device peak is at most the largest-shape reservation plus
  2,048 MiB (`no_contamination`).

**Infrastructure failures and exclusions** as v1: a point stopped by USR1 or TERM
is "interrupted"; one stopped by its cap or a deadline without a failed request
is "truncated"; any other early end, or a failed request, is "invalid"; an
exception outside the requests is "failed-infra" and ends the phase; a point not
launched is "not-run", with the reason (for the launch window: "the phase bound
passed" or "no slack for an optional point"). An invalid point gets one rerun
under the ledger of design decision 11; both attempts are kept in full (the
earlier ones under `superseded_attempts`) and the last stands. Only valid
(including flagged) points enter a budget.

**Control X1.** Inputs a1a, r1 (real) and x1-a1, x1-r1 (dummy).
Outcomes, in order: *not-run* (any of the four not valid); *not-comparable* (for
some request the prompt-token-id digest, or, when the server returned no ids, the
prompt token count, differs between a1a and x1-a1 or between r1 and x1-r1, or the
request sets differ); *fail* (open-loop request-throughput delta above 5% or
mean-replay-latency delta above 8%); *underpowered* (the replay delta's standard
error, sqrt(SE_r1² + SE_x1-r1²) / mean latency of r1 with each SE = sqrt(sum of
squared step SEs) / steps, above 5%, or fewer than three valid A1 seeds, or their
throughput range above 5%); *pass*. Operating characteristics (Monte Carlo through
`harness/serving_probe_v2/x1.py`, replay means with v1's measured standard error,
open-loop throughputs with a run-to-run CV of 1%): P(pass) is 0.95 when dummy and
real weights cost the same, and 0.76, 0.50, 0.33, 0.18 and 0.06 at a true replay
difference of 5, 8, 10, 12 and 15%; at a true open-loop difference of 8% it is at
most 0.04. When they cost the same, P(pass) falls to 0.74 at a CV of 2% and 0.41
at 3%, through both the 5% open-loop threshold and the 5% A1 range condition
(v1's identical-prompt throughput delta was 0.86%). X1 resolves replay differences of about 15%, not 5%;
its outcome enters no v2 budget (design decision 10).

## 9. Budget rules and decisions

**Q2** (per cell = rung x harness x observation; 4 rungs x 2 harnesses x 2
observations = 16 cells, E = 360 episodes each). v1's rules, unchanged:
GPU-h_closed = g × ceil(E / V) × Σ_{t=1..T} (t_env + m × L(t)) / 3600 and
GPU-h_open = E × T × g × m / r_cell / 3600; the cell value is the larger of the
two, times the A1 noise multiplier.

- g = 1; V = the replay's V (40 for H1, 20 for H2); t_env = 2.5 s; T = 15 (H1)
  and 100 (H2).
- L(t) is the mean latency of step t over the episodes, from steps every episode
  completed; later steps use the more expensive of the last two measured steps
  (for H2, the last two non-fold steps, or the last fold step for fold steps),
  scaled up by the ratio of modelled prompt tokens, never down.
- Profiles: H1 screenshot from r1; H1 accessibility tree from r2; H2 screenshot
  from r3 plus the thinking penalty (r4 step 19 minus r3 step 19, floored at 0);
  H2 accessibility tree adds the accessibility penalty (the larger of r2's last
  two step means minus the larger of r1's last two step means, floored at 0).
- Fallbacks, each flagged: without a valid r4, thinking penalty = (2,048 − 300)
  × the largest p90 TPOT over r3's last six steps × 1.5; without a valid r2,
  accessibility penalty = r1's steady latency × (6,144 / r1's modelled prompt at
  step 6) × 1.5. Without a valid r1 or r3, no Q2 budget is frozen ("incomplete:
  re-probe").
- Rung multiplier m: 1 for 9B and 4B; 4.5 for 27B and 1.5 for 35B-A3B
  (active-parameter rule, flagged; design decision 15).
- r_cell = r_ref / max(P_cell / P_ref, O_cell / O_ref), with r_ref, P_ref, O_ref
  from a2 (else the slowest valid of a1a, a1b, a1c, flagged; else no budget);
  r_ref is multiplied by f1's ratio to a1a when PNG is more than 10% slower.
- Context check: every primary cell's largest modelled prompt plus its output
  must fit 131,072 tokens, else no budget.
- Sensitivity table: T in {15, 50, 100}, t_env in {1.5, 2.5, 4.0} s, V in {20, 40}.

**Accepted job only** (section 6). **Q2 decision:** above 90 GPU-h, Stage 1 is
rescoped before the gauntlet (non-thinking mode, a smaller history window, lower
max_tokens or fewer tasks); below 15 GPU-h, the dossier is recorded as an
over-estimate; otherwise the total is within the dossier's range.

**Q1** is not projected by v2; its budget is serving-throughput-probe-v1's.

Stage 1 must reuse these engine settings or re-probe.

## 10. Stop rules

- The launch-window ledger of design decision 11; no point launches after a
  phase's bound, and none after the soft stop (51 minutes).
- Every running point is truncated at its cap or at its phase's hard deadline
  (the bound for the real phase, 56 minutes for the last); in-flight requests get
  30 s, then are cancelled.
- USR1 or TERM (the lane sends USR1 180 s before the end): no new request,
  in-flight requests get 30 s, the point is "interrupted", progress is saved,
  then the lane's checkpoint marker is written (first line `trigger=SIGUSR1` or
  `trigger=SIGTERM`), then the engine stops.
- Slurm `--time` 60 minutes is the hard cap (1.0 GPU-h). A Slurm TIMEOUT
  classifies the job "incomplete": its points are kept and reported and enter no
  budget.

## 11. Reported regardless of outcome

Every gate result with its recorded values, including G0.8's compute-process
listing and G0.9's reservation, attribution mode and basis; every point with its
status, attempts (superseded attempts in full), metrics, request identities and
contamination details, valid or not; every launch decision of the ledger (point,
kind, time, bound, time needed, launched or not) and every rerun not launched;
the job's acceptance verdict, eager label and the reasons its points were not
admitted; X1's identity checks, deltas, standard error and outcome; the A1
stability and noise multiplier; the F1 ratio, applied or not; the open-loop
reference and the binding bound per cell; engine facts per phase; all GPU time
(the overlay build and job A, each against its cap); the Q2 projection with every
flag and the sensitivity table; the contract SHA-256, the probe code digest,
git HEAD, image IDs and this file's ledger row; and every deviation from this
document.

## 12. External sources

| Source | Revision | Size | SHA-256 | License |
|---|---|---|---|---|
| vLLM image `vllm/vllm-openai:v0.31.0-cu129`, linux/amd64 | manifest sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f | 11,015,410,140 B compressed | image ID 423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b | vLLM Apache-2.0; CUDA base layers under NVIDIA's container license (used locally) |
| vLLM `vllm/entrypoints/openai/chat_completion/serving.py`, read 2026-10-07: with `return_token_ids`, the first streamed chunk carries `prompt_token_ids` (lines 553-565); https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/entrypoints/openai/chat_completion/serving.py | tag v0.31.0 | 57,487 B | 532dadea845c77a5a79011027b9989987c3e32467614e993f439f29c924de002 | Apache-2.0 |
| vLLM `vllm/entrypoints/openai/chat_completion/protocol.py`, read 2026-10-07: `return_token_ids` field (lines 416-424); https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/entrypoints/openai/chat_completion/protocol.py | tag v0.31.0 | 47,050 B | 4bdc71f668e4820d8ae5bae2a153fed0296b430cd6353ace8c0c27cfb982ebc1 | Apache-2.0 |
| Qwen/Qwen3.5-9B weights (cached) | c202236235762e1c871ad0ccb60c8ee5ba337b9a | 19,329,393,661 B | receipt 0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3 | Apache-2.0 |
| NVIDIA developer forum, "Nvidia-smi doesnt show running processes inside the container" (user report, 2025-08-28: `--query-compute-apps` inside a pod lists host PIDs with name `[Not Found]`, driver 575.57.08), read 2026-10-07; https://forums.developer.nvidia.com/t/nvidia-smi-doesnt-show-running-processes-inside-the-container/343361 | not applicable | not stored | not applicable | forum post; cited, not copied |
| OSWorld `mm_agents/qwen3vl_agent.py` (H1 layout, as v1) | b138d348256078fa634fc3b73567a7337c793e6b | 30,053 B | c9bb34d3ad822168c66133cd97c607d4645b7eff08072e1e45c49dbbad8491b4 | Apache-2.0; one instruction sentence quoted in `harness/serving_probe/prompts.py` with attribution |
| cua-speedrun `agents/qwen35/agent.py` (H2 layout, as v1) | be17c72c5efbb145d06f86028336fdf2743a3d98 | 31,910 B | 287ce1244a787e71aa89bc9c0efd6bf24c2779b6918be7e7b8ae932bcf9c1bfc | unresolved (no LICENSE file); layout and parameters only |
| serving-throughput-probe-v1 evidence (design inputs only) | `program/evidence/2026-10-07/serving-throughput-probe-v1/` at commit 9154693 | per `SHA256SUMS` there | per `SHA256SUMS` there | this repository (MIT) |
