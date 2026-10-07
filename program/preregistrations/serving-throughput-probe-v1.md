# Preregistration: serving-throughput-probe-v1

Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row for
the freeze time. A material change to this file, to the contract or to the probe
code after the freeze is a new experiment id.

## 1. Identity

- **Experiment id:** serving-throughput-probe-v1.
- **Question.** What inference GPU time does the Stage-1 work of Q1 and Q2 need on
  this node, measured rather than assumed? Q2: per-step latency of closed-loop
  computer-use episodes for the Qwen3.5 ladder under two harness layouts and two
  observation types. Q1: GPU-seconds per sampled completion for an 8B dense
  policy with Dr. Kernel's sampling protocol (n=8, up to 8,192 tokens per turn,
  3 turns, 32,768 context).
- **Claim level.** Infrastructure evidence ("admission pass"). Nothing here is a
  scientific result about models, harnesses or checkers.
- **Code revision.** Jobs run from the source capsule of a commit X of `main`
  that contains this file's ledger row (X is pushed, then cloned on the host).
  X is recorded in each job's manifest (`git_sha`), provenance verification and
  the evidence bundle. The overlay image bakes in X's source, so it is built
  from X, after the freeze. X may differ from the freeze commit only outside
  the probe code and the contract: both must be byte-identical to what this
  file names below, and the driver checks this.
- **Contract.** `experiments/serving/serving-throughput-probe-v1.yaml` holds every
  engine flag, point, seed, gate threshold and budget parameter named below. Its
  SHA-256 is
  `8e5ad94e08a17a3eacc049150a14a35ef6ab9509a8c32ca6a6b2ac9711f6e931`.
  Every point file and summary records the contract SHA-256 it ran under.
- **Probe code.** `scripts/run_vllm_throughput_probe.py` and every module of
  `harness/serving_probe/` (budget rules in `budget.py`). Their digest, the
  SHA-256 of the compact JSON list of [path, file SHA-256] pairs sorted by path
  (`run_vllm_throughput_probe.py digest` prints it), is
  `16bde053544ae46b8dba032f9e63056f5ea258ab45ebea417bcd72fcf3a6b8b7`.
  The digest covers these files only (design decision 36).
- **Binding.** Gate G0.0 (in the image) and the `project` step (on the host)
  both verify this file against the ledger and refuse unless its frozen text
  names the contract SHA-256 and the probe code digest they compute from the
  files they run. A changed threshold, rule or line of probe code after freezing
  therefore stops the experiment; it needs a new experiment id. The projection
  records the ledger row, the digest, the per-file hashes and git HEAD.
- **Runtime.** vLLM v0.31.0, commit db9527a46873454610df6dbedf79a36d6bf1a7f6,
  base image `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  (CUDA 12.9.1, torch 2.13.0+cu129, local image ID
  sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b), run
  through the overlay `infra/research/Dockerfile.vllm-overlay` built by
  `scripts/build_vllm_overlay_on_h100.sh`. The overlay image ID is recorded in
  its build receipt and in every manifest. The overlay changes one thing in the
  upstream environment: it removes torchcodec 0.17.0, which the cu129 image ships
  as a CUDA 13 build (`libcudart.so.13`, `libnvrtc.so.13`); importing it raises an
  OSError that vLLM's guard does not catch, so stock `vllm serve` fails at import
  in this image (found on CPU on 2026-10-07). torchcodec only decodes audio and
  video, which the probe never sends. The removal is conditional, recorded in
  `/etc/cotcodec-vllm-overlay-fixups.json` and in the build receipt
  (`infra/research/vllm_overlay_fixups.py`). The builder also runs
  `run_vllm_throughput_probe.py vllm-args-doctor`, which checks every engine flag
  and both request payload variants with vLLM's own parsers on CPU.
- **Lane.** `scripts/submit_docker_research_job.py` with `container_profile: vllm`
  (16 GB /dev/shm, exec /tmp of 32 GB, 8,192 pids), `seed_binding.flag: --seeds`,
  one H100 per job, TP=1. The driver parses its options with abbreviations
  disabled, as the lane's seed binding requires.
- **Data.** Synthetic only: random-token text, rendered PNG screenshots and
  random-pixel JPEG screenshots, all derived from the seeds below. No dataset,
  no model output and no benchmark task is read.

### Models

| Role | Model and revision | Weights | Pin |
|---|---|---|---|
| Q2 9B rung, real weights (jobs A real phase) | Qwen/Qwen3.5-9B @ c202236235762e1c871ad0ccb60c8ee5ba337b9a | real, lane-verified | receipt 0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3, artifact root 9845026dbe255e24b105224eebbb5436d315713b9a5c53c434137896b160c5b1 |
| Dummy-weight control X1 (job A) | same 9B config | `--load-format dummy` | same snapshot |
| Q1 stand-in (job B) | Qwen/Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218 | dummy | metadata receipt pinned in the manifest |
| Q2 27B rung (job C) | Qwen/Qwen3.5-27B-FP8 @ 97f5941bf617e31c5e237364a8602ce3f03a551a | dummy | metadata receipt pinned in the manifest |
| Q2 35B-A3B rung (job C) | Qwen/Qwen3.5-35B-A3B-FP8 @ 9d1823d2dee688a6b25e77009dc727688c44936e | dummy | metadata receipt pinned in the manifest |
| Lane admission token (jobs B, C) | Qwen/Qwen3-0.6B-Base @ da87bfb608c14b7cf20ba1ce41287e8de496c0cd | never served | receipt e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df, artifact root 7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0 |

Qwen3-8B has Dr. Kernel-8B's layer shapes (hidden 4,096, 36 layers, 32 query and
8 KV heads, head dim 128, intermediate 12,288, vocabulary 151,936). Dr. Kernel-8B
itself has no license and stays out of receipted runs (decision D5).

## 2. Claim boundary

- Inference-only GPU cost. VM time is simulated (`t_env`); checker, verification
  and timing costs are excluded.
- Synthetic prompts and fixed output lengths: every request sets
  `ignore_eos=true` and `min_tokens = max_tokens`, so output lengths are a
  harness setting the probe brackets (300 and 2,048 tokens for Q2; 4,096 and
  8,192 per turn for Q1), not a measurement of model behaviour.
- Dummy-weight numbers are admissible only under control X1 (section 7). Dummy
  MoE routing is near uniform, so 35B-A3B numbers carry that caveat whatever X1
  says.
- Generated text is never executed, parsed or written to disk. Replays keep it
  in memory as assistant history, as the real harnesses do. Only token counts
  and, for the A/A check, SHA-256 digests of generated token ids are stored.
- MTP and speculative decoding are off (vLLM issue #53912 is open); the contract
  rejects any speculative flag.
- Server points run greedy (temperature 0). Harness sampling settings
  (cua-speedrun uses 1.0) change no kernel under fixed lengths.
- The VLM engines serve `max_model_len` 131,072 (cua-speedrun's own default);
  the probe measures prompts up to about 47K tokens and extrapolates beyond.
- The overlay cannot decode audio or video (torchcodec removed); the probe sends
  neither, and `limit_mm_per_prompt` sets the video limit to 0.

## 3. Design decisions

Choices the reviewed plan left to the owner, or where this preregistration
departs from it, each with its reason. Decision D17 (`program/decisions.md`)
records the owner's acceptance of design decisions 2 to 27, conditional on job
acceptance gating budget entry (design decision 32 implements it); D17 also
amends D8 (design decision 2) and pre-approves the cu130 retry (section 5).

1. **Experiment id** is `serving-throughput-probe-v1` (the item name), not the
   plan's `vllm-throughput-probe-v1`.
2. **Budget (decisions D8 and D17).** Jobs A and B are capped by Slurm `--time`
   at 40 and 20 minutes, together exactly 1.0 GPU-h (expected about 0.8); the
   manifests' `max_gpu_hours` of 0.67 and 0.34 are those allocations rounded up.
   Job C is the optional 0.5 GPU-h extension and runs only if X1 passes. The
   overlay build and the metadata fetch each hold one idle H100 for at most 10
   minutes; D17 amends D8 so that they are accounted separately from the 1.0
   GPU-h probe cap, as separate lines in `gpu_hours_spent` (cap 0.33 GPU-h
   together). A cu130 retry has its own cap (section 5).
3. **One client for every server point.** The plan used `vllm bench serve` for
   the random-mm brackets and a custom client for replays. Here one asyncio
   client sends every server request. Reasons: identical timing and token
   accounting across open-loop, replay, front-end and A/A points; F1 then
   differs from A1 only in image encoding; G0.7 can demand exact counter
   equality because no hidden warm-up or test request is sent; no generated
   text reaches disk. The random-pixel JPEG generator reproduces vLLM's
   `RandomMultiModalDataset` (iid uniform pixels, PIL JPEG defaults).
4. **Replay sizes fit the allocation.** At V=40 an H1 step carries up to five
   2,040-token screenshots (about 13K prompt tokens with little prefix reuse),
   so an estimated 0.5 s of GPU time per request makes the GPU, not the VMs,
   the bottleneck, and the plan's T=15 replays alone would need about 30 minutes.
   H1 replays therefore run 6 steps (the 4-screenshot window is full from step
   5), and the cost of later steps is extrapolated by the rule in section 8.
5. **H2 runs at V=20 per replica and implements cua-speedrun's folding.**
   cua-speedrun @be17c72c keeps every response and folds the oldest screenshots
   in blocks of 10 once more than 20 are visible, so the prompt grows between
   folds and changes prefix at steps 21, 31, 41 and so on. At V=40 the resident
   context of H2 (about 40 x 45K tokens) exceeds the 9B engine's KV capacity,
   so V=40 would measure preemption churn rather than a deployable point. Two
   replicas of V=20 serve a 40-VM pool. H2 cells are budgeted at their measured
   V; using V=20 per replica cannot understate GPU time relative to V=40.
6. **R3 covers one fold** (steps 1 to 24 from an empty history). **R4 (thinking)
   starts from a prebuilt 17-step history and runs 2 steps**; step 18 is cold
   (no cached prefix) and reported separately, step 19 is used for the thinking
   penalty.
7. **Job B prompt counts are sized to one KV-resident wave** (at most about 80%
   of an estimated 364K-token KV pool for Qwen3-8B at 0.90 memory utilisation):
   B1 8 prompts, B2 4, B6 3, B3 8, each with n=8. Fewer sequences than the KV
   pool could hold give a higher, so conservative, GPU-s per completion.
8. **X1 runs last but its time is reserved.** The real-weight phase may not
   launch or continue points after (85% of the allocation minus 9 minutes);
   the dummy-weight phase then has its 9 minutes. Every point also has its own
   wall cap (contract `max_minutes`).
9. **Dummy-weight jobs bind `qwen3-0.6b-base` as the lane's admission token.**
   The lane mounts the model cache only when a model is bound, and the metadata
   snapshots live there. The driver verifies each pinned metadata receipt
   itself: file SHA-256, mode `metadata`, revision and repository, artifact root,
   and a re-hash of the snapshot (gate G0.1).
10. **Job C measures A1 and R1 per rung**, not R3. The rung multiplier is the
    open-loop A1 throughput ratio to the 9B (same shape, same seed), which is
    the cost ratio of a GPU-bound step; R1 is a cross-check. The 27B rung runs
    first (the most expensive rung), with 7 minutes reserved for the 35B-A3B rung.
11. **G0.3 metric:** the maximum absolute difference between a bf16 4096 x 4096
    GEMM and the fp32 GEMM of the same bf16-rounded inputs (TF32 off), divided
    by the maximum absolute fp32 value.
12. **X1 power.** X1 passes only if both deltas are at most 5%, all three A1
    seed points are valid, and their spread is at most 5%. Fewer valid seeds or
    a larger spread makes X1 "underpowered", treated as not passed. Section 6
    gives the rule's operating characteristics; a false fail only makes the
    budgets more conservative (×1.5) and skips job C. At a run-to-run CV of 2%
    or 3%, X1 passes only 71% or 33% of the time even when dummy and real
    weights cost the same, so the likely outcome is no job C and ×1.5 on Q1,
    which moves Q1's effective single-turn cut from 6 to about 4 GPU-h of true
    cost (section 6). That consequence is conservative and part of the rule.
13. **Offline sampling uses the engine seed (42), not per-request seeds.**
    Per-request seeds force a slower per-request sampler path. Prompt content is
    seeded per point.
14. **Episode starts are staggered** uniformly over `t_env` (2.5 s), so the first
    step is not a synchronised burst.
15. **Q2 primary projection is conservative:** H2 cells use thinking-on costs
    (cua-speedrun's default) and harness step caps (H1 15, H2 100).
16. **F1 correction.** F1's ratio is PNG request throughput (f1) divided by
    random-JPEG request throughput (a1a). If it is below 0.90 (PNG more than 10%
    slower), the open-loop reference request rate (a2, random JPEG) is
    multiplied by it, which raises the open-loop GPU-h. A ratio above 1.10 is
    reported but not applied: the rendered PNGs are simpler than real desktop
    screenshots, so a faster PNG path must not lower the budget.
17. **Resume test.** Resume (skip terminal points, refuse a different contract)
    is tested on CPU with a fake engine; no GPU resume run is made, because a
    probe has no training state to restore (decision D17 requires none).
18. **Metadata fetch** uses a new script (`fetch-model-metadata-in-docker.sh`)
    instead of a mode switch in `fetch-model-in-docker.sh`, so the existing
    full-weight path is unchanged.
19. **Dr. Kernel-8B** gets no registry entry in this item; registering it with
    its blocker is left to the Q1 owner (decision D5). Contacting its authors
    stays a Kevin decision (D2).
20. **Image download.** The reviewed plan asked for Kevin's OK on the 11.02 GB
    cu129 image; decision D1 authorises public research downloads and the image
    is already on the host (image ID above). The 9.04 GB cu130 image is pulled
    only on the failure path in section 5; decision D17 pre-approves that
    download together with the retry's GPU time, and it is recorded like any
    download.
21. **Job C gating.** D8 budgets the 0.5 GPU-h extension; this preregistration
    makes it conditional on X1 passing, because without X1 its dummy-weight
    numbers would carry the 1.5 multiplier anyway and add little over the
    active-parameter rule. The manifest renderer enforces the condition (design
    decision 33).
22. **Excluded arms.** The plan's optional prefix-caching-off arm and TP=2 real
    weight run on the cached Qwen3.6-35B-A3B are not part of this experiment;
    each would need its own approval and a new experiment id.
23. **torchcodec is removed in the overlay** (section 1, Runtime) instead of
    switching the primary image to cu130, because cu129 needs no forward
    compatibility library for most kernels on R570 while cu130 does. The only
    other CUDA-13-linked files in the image are the optional nixl KV connectors,
    which vLLM imports only when KV transfer is configured.
24. **`max_model_len` is 131,072 for the VLM engines** (jobs A and C), the
    default of cua-speedrun's own server launcher (`agents/qwen35/init.py`,
    `VLLM_MAX_MODEL_LEN`). At 65,536 the modelled H2 thinking prompt plus its
    2,048 output tokens passes the limit at step 79 (step 59 with the
    accessibility tree) and peaks at 74,188 (80,332) tokens, so the budget would
    price requests the engine rejects. The projection refuses any primary cell
    whose modelled prompt plus output exceeds the limit.
25. **Seed noise enters the budgets.** The UNSTABLE rule needs a target: every
    budget number comes from one seed per point, so the A1 seeds set a noise
    multiplier on every Q2 cell and the B1 seeds one on both Q1 totals (section
    8). The rung ratio stays seed-matched (a1a against each rung's seed-42 A1).
26. **The open-loop bound prices output length and the accessibility tree.** The
    cell's request rate is the reference rate divided by the larger of the
    cell-to-reference prompt ratio and output ratio, an upper bound on any mix
    of prefill and decode cost. Accessibility cells carry their 6,144 tree tokens
    on every step. If a2 is not valid, the slowest valid A1 seed (concurrency 16,
    so a lower rate and a higher bound) replaces it, flagged.
27. **Acceptance.** A job's points may enter a budget when its summary says
    `acceptance.accepted: true`: status complete or complete-with-cuts and gates
    G0.0 to G0.4 passed. An eager-fallback job is accepted and labelled eager
    (section 5). A non-primary phase whose gate failed contributes no points
    (they are not-run) and is listed, without rejecting the job. The projection
    enforces this (design decision 32).
28. **Checkpoint marker.** The driver follows the lane's signal-checkpoint
    contract (docs/operations.md): `checkpoint.ready` is written only after a
    USR1 or TERM, after progress is saved, as text whose first line is
    `trigger=SIGUSR1` (or `trigger=SIGTERM`). A run that gets no signal never
    writes it.
29. **Offline truncation.** When an offline point is stopped by its wall cap or
    a signal, its requests are aborted in the engine before the next point, and
    each `generate` keeps only outputs with its own request ids; if requests
    remain after the abort, the phase stops (its remaining points are not-run).
30. **Device and cache checks fail closed.** A point needs device samples
    (section 7), a measured engine reservation, and successful prefix,
    multimodal and encoder cache resets. A sampler that yields nothing after the
    smoke stops the phase (G0.8).
31. **No unlicensed text.** cua-speedrun has no LICENSE file, so the probe
    copies none of its text: the folded-screenshot placeholder is neutral text
    of the same length (6 tokens), and the tool-response tags are the Qwen3.5
    chat template's own. The one OSWorld sentence used is quoted with its
    Apache-2.0 attribution.
32. **Acceptance gates budget entry (D17's condition).** `project` admits a
    job's points only if its `summary.json` exists and belongs to this
    experiment, contract and job; records `acceptance.accepted: true`; agrees
    with the acceptance recomputed from its own status and gates (a job-level
    gate that was never recorded counts as failed); records driver exit code 0;
    and lists the SHA-256 of exactly the point files on disk, which the driver
    writes into the summary when it finishes. A later resubmission that dies
    part-way therefore cannot add points under an earlier accepted summary. A
    job that is not admitted is reported with its reasons, and none of its
    points enters a budget (section 8 states the consequence for each job).
33. **Job C gating is enforced.** The manifest renderer
    (`scripts/render_serving_probe_manifest.py`) renders job C only from job A's
    output directory (`--job-a-output`), and only when job A is admitted by the
    rule of design decision 32 and X1 evaluated on its points is "pass". It also
    refuses any manifest whose GPU count is not 1.
34. **Exactly one GPU in G0.2.** The CUDA doctor expects one visible H100
    whatever GPU count the lane's environment carries (the lane sets it from the
    manifest), so a job given more GPUs fails G0.2 instead of passing with them.
35. **Replay dispersion is recorded.** Every latency, TTFT, TPOT and ITL summary
    records the sample standard deviation (n − 1) and the standard error of its
    mean (SD / √n) next to the mean and percentiles, so section 6's standard
    error of each replay step mean is in every replay point file. Raw
    per-request latencies are not stored.
36. **Digest scope.** The probe-code digest covers the probe package and its
    driver only. Shared lane code that G0.0 and G0.1 call
    (`scripts/preregister.py`, `scripts/fetch_open_model.py`),
    `models/registry.yaml` and the manifest renderer are outside it, so an
    unrelated change merged to `main` between the freeze and a job does not stop
    the experiment. They are fixed by the commit X recorded in every manifest,
    and the projection records git HEAD.

## 4. Step-0 gates

All must pass, otherwise the job outcome is "pre-result" (driver exit code 2)
and no number from that job enters a budget.

- **G0.0** This file verifies against the ledger in the image, at the path the
  contract names, and its text names the SHA-256 of the contract the driver
  loaded and the digest of the probe code in the image (section 1, Binding).
- **G0.1** The lane's provenance verification printed status PASS, its container
  doctor printed `STATUS PASS`, and its bound-model verification reports the
  contract's model id, revision, artifact root and mode `full`. For jobs B and C,
  every pinned metadata receipt verifies as described in design decision 9.
- **G0.2** `cuInit` returns 0; exactly one H100 is visible (design decision
  34); the image's vLLM version is 0.31.0 and `VLLM_BUILD_COMMIT` equals the
  commit above. Recorded: `cuDriverGetVersion`, the realpath of the mapped
  `libcuda`, whether it is the image's forward-compatibility library, and
  `ldconfig -p` lines for libcuda.
- **G0.3** The G0.3 metric (design decision 11) is below 0.01 and the product is
  finite.
- **G0.4** A Triton kernel compiles into the cache under the job's output
  directory, returns exactly `x + y` on 2^20 floats, and no file under `/tmp`
  is mapped into the doctor process. Files under `/tmp` mapped by the engine's
  processes are recorded per engine as a diagnostic.
- **G0.5** The engine becomes ready (`/health` 200, or `LLM` constructed) within
  900 s in default mode (torch.compile and CUDA graphs). The compilation config
  line, compile and graph-capture times, weight memory and KV-cache size are
  recorded.
- **G0.6** A 16-request smoke at concurrency 8 completes with 0 failures and every
  output at its requested length. For VLM engines, prompt tokens of one image
  plus text minus the same text alone is within 2,040 ± 2% (1,999.2 to 2,080.8);
  the exact value is recorded. The smoke point must also pass section 7's
  validity checks other than the reservation (cache resets, device samples).
  An invalid smoke point gets section 7's single rerun, so G0.6 and G0.7 have
  at most two attempts per phase; both attempts are kept.
- **G0.7** For the smoke, and for every later point as a validity condition: the
  `/metrics` (or `LLM.get_metrics`) generation-token delta equals the client's
  output-token total exactly, and the prompt-token delta is within 1% of the
  client's prompt-token total. Offline, the prompt check accepts either the
  per-request or the per-sample (n=8 fan-out) total, and records which matched.
- **G0.8** Before every engine start, including the eager retry (after waiting
  up to 90 s for the failed engine's memory to be released), after a 2 s
  settle, every 500 ms sample over 10 s shows device memory.used below
  1,024 MiB and utilisation 0%. After the smoke, the sampler must report at
  least one sample in the 5 s reservation window; otherwise the phase stops.

## 5. Failure path

- **G0.5 fails, eager start succeeds:** the job continues with
  `--enforce-eager`, labelled "eager", and every later engine of the job also
  starts eager. Its points are admissible: the job is accepted with G0.5
  recorded as not passed and `eager_fallback: true` (design decision 27).
  Stage 1 must then also run eager, or wait for the R580 driver.
- **Acceptance of a job.** Slurm `JobState=COMPLETED` with `ExitCode=0:0`
  (checked with `sacct` and the lane's `termination.env` when the outputs are
  collected), and `summary.json` showing `acceptance.accepted: true` (status
  complete or complete-with-cuts, G0.0 to G0.4 passed). Nothing else is
  required, and nothing less is accepted. The projection enforces the summary
  side (design decision 32): it also requires driver exit code 0 and the
  SHA-256 of exactly the point files on disk. Points of a job that is not
  accepted (pre-result, crashed, interrupted, Slurm TIMEOUT, no summary) are
  kept and reported but enter no budget; the projections that need them are
  "incomplete: re-probe" (section 8), and any resubmission needs the owner's
  approval of the extra GPU time.
- **A gate from G0.2 to G0.8 fails on the cu129 image** (G0.5 only when the
  eager start fails too): one retry with the vLLM v0.31.0 default (cu130)
  image, linux/amd64 manifest
  sha256:a4a4c0437bf7240089da5f08aa370c4aee17ae5290f7a3b468825ee26c4c3a6b
  (image ID sha256:c76d0e2225a4b1cb1e2109ace39639f55e714abd1a7a427acc8b0bbd7f6a83b3,
  9,035,211,086 bytes compressed),
  through the same overlay builder with `COTCODEC_VLLM_VARIANT=cu130`, which sets
  `VLLM_ENABLE_CUDA_COMPATIBILITY=1`. Decision D17 pre-approves this retry, its
  download included, with its own cap of 1.0 GPU-h on top of the probe cap:
  the overlay rebuild and one rerun of the job whose gate failed. A job that
  has not run yet when the retry starts runs on cu130 under the probe cap. Each
  job's summary records its image variant. A G0.0 or G0.1 failure (the
  preregistration or the lane's provenance) is not a runtime failure: its job
  is resubmitted on the same image once the cause is fixed, which, like any
  resubmission, needs the owner's approval of the extra GPU time.
- **That fails too:** the probe is classified "pre-result: vLLM runtime blocked on
  R570", no further GPU time is spent, and the R580 upgrade is escalated.
- A gate failure in job A's dummy-weight phase or in one of job C's phases does
  not stop the job; that phase's points are recorded as not run. X1 is then
  not-run; a job C rung whose phase did not run keeps the active-parameter rule
  (section 8).
- No vLLM v0.25.1 number from the earlier program is used.

## 6. Points, seeds and sample sizes

Fixed priority order within each phase. The prefix cache, the multimodal
processor cache and the encoder cache are reset before every point. Seeds set
prompt text (`numpy.random.default_rng([seed, 1, ...])`) and images
(`[seed, 2, ...]`) independently, so F1 and X1 send exactly A1a's and R1's text.
The manifests declare seeds [42, 43, 44] and bind them through `--seeds`; the
driver refuses any other list.

Text shapes are in tokens of the served model's tokenizer. Screenshots are
1920 x 1080 (2,040 visual tokens each after the processor's resize to 1920 x 1088).

**Job A** (Qwen3.5-9B, TP=1, prefix caching on, `max_model_len` 131,072,
`gpu_memory_utilization` 0.90, `max_num_seqs` 256, `max_num_batched_tokens` 8,192,
`limit_mm_per_prompt` 20 images at 1920 x 1080 and no video, `generation_config`
vllm, engine seed 42).

| Point | What | Requests | Seed | Cap (min) |
|---|---|---|---|---|
| a-smoke | gates G0.6 and G0.7 | 16 at C=8, 1 PNG, O=64 | 7 | 3 |
| a1a | S2 open loop: system prefix 1,536 + body 4,608 + 1 random JPEG, O=300, C=16 | 96 | 42 | 4 |
| r1 | H1 replay (OSWorld qwen3vl layout, window 4), screenshot, V=40, steps 1-6, O=300 | 240 | 101 | 6 |
| r3 | H2 replay (cua-speedrun layout, folding), screenshot, V=20, steps 1-24, O=300 | 480 | 103 | 8 |
| r4 | H2 thinking: prebuilt 17 steps, steps 18-19, O=2,048, V=20 | 40 | 104 | 8 |
| a1b | a1a shape | 96 | 43 | 4 |
| r2 | r1 plus 6,144 accessibility-tree tokens on the current step | 240 | 102 | 7 |
| a1c | a1a shape | 96 | 44 | 4 |
| f1 | a1a with rendered PNGs instead of random JPEGs | 96 | 42 | 4 |
| a2 | a1a shape at C=40 | 160 | 45 | 5 |
| d8 | A/A: 16 S2 prompts with PNGs, O=128, at C=1, cache reset, then at C=16 | 32 | 47 | 3 |
| a6 | S4: prefix 1,536 + body 4,608 + 20 random JPEGs, O=300, C=8 | 24 | 46 | 4 |
| x1-smoke | dummy-weight engine, gates G0.5 to G0.7 | 16 | 7 | 3 |
| x1-a1 | a1a, dummy weights | 96 | 42 | 4 |
| x1-r1 | r1, dummy weights | 240 | 101 | 6 |

Replay details: system prompt 1,536 tokens shared within a point, task 64 tokens
per episode, action strings 16 tokens, prebuilt responses 300 tokens, simulated
VM time `t_env` 2.5 s between an episode's steps, starts staggered over 2.5 s.

**Job B** (Qwen3-8B config, dummy weights, offline `LLM.generate`, TP=1,
`max_model_len` 32,768, `gpu_memory_utilization` 0.90, `max_num_batched_tokens`
16,384, `max_num_seqs` 256, prefix caching on; temperature 1.0, top_p 1.0, n=8).

| Point | Shape | Prompts x n | Seed | Cap (min) |
|---|---|---|---|---|
| b-smoke | I=256, O=64, n=1, temperature 0 | 16 x 1 | 7 | 3 |
| b1a | turn 1: I=1,152, O=4,096 | 8 x 8 | 42 | 3 |
| b2 | turn 1 at the per-turn cap: I=1,152, O=8,192 | 4 x 8 | 45 | 4 |
| b6 | turn 3 worst case: I=16,384, O=8,192 | 3 x 8 | 46 | 6 |
| b1b | b1a | 8 x 8 | 43 | 3 |
| b1c | b1a | 8 x 8 | 44 | 3 |
| b3 | turn 2: I=4,096, O=4,096 (lowest priority) | 8 x 8 | 47 | 4 |

I=1,152 (9 × 128) rounds up the scout's measured medians of Dr. Kernel's
first-turn prompt on KernelBench levels 1 and 2 (p50 1,092 and 1,140 tokens).

**Job C** (optional; same engine settings as job A, dummy weights, TP=1): phase
rung-27b runs c27-smoke, c27-a1 (a1a shape, seed 42, cap 6) and c27-r1 (r1,
seed 101, cap 9); phase rung-35b (7 minutes reserved) runs c35-smoke, c35-a1
(seed 42, cap 4) and c35-r1 (seed 101, cap 6).

**Minimum detectable effects.**
- X1 resolves a 5% difference only when A1's three-seed spread is at most 5%
  (design decision 12). Its operating characteristics, from a Monte Carlo of
  the rule as coded (200,000 draws; each throughput or mean latency is the true
  value times 1 + N(0, CV²), independently): with dummy weights exactly like
  real ones, P(pass) is 0.998, 0.71, 0.33 and 0.15 at a run-to-run CV of 1%, 2%,
  3% and 4%. With a true 8% difference in one of the two metrics (throughput
  or latency, either sign), P(pass) is at most 0.02, 0.12, 0.11 and 0.07 at
  these CVs; with 8% in both, at most 0.03. With a true 5% difference in one
  metric, P(pass) is about 0.50 at a CV of 1%. The run-to-run CV on this node
  is unknown before the probe; the A1 seed spread reports it. A non-pass is
  conservative (×1.5 on dummy-weight numbers, no job C), never a loss of
  validity; at a CV of 2% to 3% it is the likely outcome even with identical
  costs (design decision 12). X1 is measured on the hybrid 9B VLM in server
  mode and also governs the dense Qwen3-8B offline numbers of job B: it is the
  probe's only check of dummy weights, and applying a non-pass to job B can
  only raise the Q1 budget.
- Per-step replay latency: V=40 (H1) or V=20 (H2) requests per step; the
  standard error of each step mean (sample SD over the step's requests divided
  by √V) is recorded in the point (design decision 35). With a coefficient of
  variation of 0.3, that is about 5% (V=40) or 7% (V=20) of the mean.
- A1 and B1 throughput: three seeds each. If all three are valid and their
  range is at most 10% of the mean, the noise multiplier is 1. A range above
  10% is flagged UNSTABLE and the multiplier is max/min of the three. With
  fewer than three valid, it is the larger of 1.10 and max/min of the valid
  ones. A1's multiplier applies to every Q2 cell, B1's to both Q1 totals
  (section 8). With three valid seeds and normal noise, P(UNSTABLE) is 0.000,
  0.001, 0.048, 0.33 and 0.65 at a run-to-run CV of 1%, 2%, 3%, 5% and 8%, and
  the mean multiplier is 1.0001 at 2% and 1.048 at 5% (Monte Carlo, 200,000
  draws). The multiplier steps from 1 to about 1.105 as the range crosses 10%,
  and is at least 1.10 whenever a seed is not valid.
- D8 agreement rate: 16 prompts, resolution 1/16 (6.25 points).
- The budget decisions (section 8) change only when a projection crosses 90 or
  15 GPU-h (Q2) or 6 and 12 GPU-h (Q1). The sensitivity table shows how far the
  assumptions, not the measurement noise, move the projection.
- Decision operating characteristics, from a Monte Carlo through the budget code
  on synthetic job A and job B points (within-step CV 0.3 over V requests and a
  per-point run factor at the stated run-to-run CV). Q2 (300 replicates per
  cell): P(rescope) at a true total of 0.85, 0.95, 1.00, 1.05 and 1.15 × 90
  GPU-h is 0.00, 0.19, 0.56, 0.83 and 1.00 at a CV of 2% (0.17, 0.47, 0.72,
  0.88 and 1.00 at 5%); P(over-estimate) at 0.85, 1.00 and 1.15 × 15 GPU-h is
  1.00, 0.43 and 0.00 at 2%. The decision is reliable outside about ±10-15% of
  either threshold. The projection is biased upward (median measured/true
  1.005-1.011 at 2%, 1.04-1.06 at 5%) by the larger-of-two extrapolation and
  the noise multiplier. Q1 (2,000 replicates per cell): with X1 passed, P(cut)
  at a true single-turn cost of 0.9, 1.0 and 1.1 × 6 GPU-h is 0.002, 0.49 and
  1.00 at 2%; without an X1 pass the ×1.5 moves the effective cut to about 4
  GPU-h of true cost (P(cut) 0.51 at 0.667 × 6 and 0.99 at 0.70 × 6 at 2%, and
  already 0.24 at 0.6 × 6 at 5%).

## 7. Metrics, validity and dummy admissibility

**Per point (unit of analysis: one point):** duration; planned, completed and
failed requests; prompt and output tokens (server usage); request, output-token
and total-token throughput; TTFT, TPOT, ITL and end-to-end latency (mean, p50,
p90, p99); for replays, per-step-index latency (mean, p50, p90, p99, max), TTFT,
TPOT and mean prompt tokens, wave wall time and mean episode active time; from
`/metrics` deltas, prefix-cache hit rate, preemptions, multimodal-cache hits and
cached prompt tokens; peak `kv_cache_usage_perc` and peak waiting requests
(polled every 2 s); device peak memory, mean utilisation, mean power, mean and
minimum SM clock (500 ms samples); API-server and client CPU percent; preparation
time (excluded from the measurement). Offline: completions, GPU-seconds per
completion, output tokens per second. Engine facts per phase: weight GiB, KV-cache
GiB and tokens, maximum concurrency, compile and graph-capture seconds, the
compilation config line, eager or not.

**Validity.** A point is valid only if it ran to its end and: failed is 0;
completed equals planned (never more); every completion has exactly its
requested output tokens; the G0.7 counter check holds for the point; every
cache reset before it (and, for d8, between its arms) succeeded: the prefix
cache, plus the multimodal and encoder caches for server points; the device
sampler delivered at least max(1, floor(0.2 × wall seconds / 0.5 s)) samples in
its window; and, except for the smokes, the phase's engine reservation (peak
memory over 5 s after the smoke) was measured and device memory.used never
exceeded it plus 2,048 MiB. API-server CPU of 90% or more (one core saturated)
leaves a point valid but flagged "front-end-bound"; client CPU of 90% or more is
flagged "client-bound".

**Infrastructure failures and exclusions.** A point stopped by USR1 or TERM is
"interrupted". A point stopped by its wall cap or a phase deadline with no
failed request is "truncated". Every other point that ends early, such as a
replay whose episode stopped at a failed request, and every deadline-stopped
point with a failed request, goes through the validity checks and is "invalid".
A failed request (an HTTP error, a transport error or a stream without usage) is
a request error, counted in the point; an exception outside the requests (the
engine died, or its metrics or cache endpoints failed) makes the point
"failed-infra" and ends its phase (the phase's remaining points are not-run).
A point never launched because of a deadline, a gate or an engine failure is
"not-run". An invalid point is rerun once with the same seed
if the phase's launch deadline allows and the engine is alive; both attempts
are kept in full (the first, with all its metrics, under
`superseded_attempts`) and the second stands. Only valid (including flagged)
points enter any budget. Interrupted, failed-infra and not-run points are rerun
on a resumed job; the others are terminal.

**Dummy admissibility (control X1).** X1 passes if |x1-a1 − a1a| / a1a ≤ 5% in
request throughput, |mean latency of x1-r1 − mean latency of r1| / that of r1 ≤
5% (mean over every completed replay request), all three of a1a, a1b and a1c
are valid, and their throughput range is at most 5% of its mean. Outcomes:
pass, fail (a delta above 5%), underpowered (deltas within 5% but fewer than
three valid A1 seeds or a wider range), not-run (a1a, r1, x1-a1 or x1-r1 not
valid). Anything but pass multiplies every dummy-weight number (jobs B and C)
by 1.5 in the budgets. Job C is submitted only after a pass (design decision
33). Reported with the deltas: the mean prompt tokens per request of r1 and
x1-r1, overall and per step, because x1-r1's history carries dummy-weight
outputs, which may re-tokenise to other lengths.

## 8. Budget rules and decisions

**Q2 (per cell = rung x harness x observation; 4 rungs x 2 harnesses x 2
observations = 16 cells, E = 360 episodes each = 120 tasks x 3 reruns, 5,760 in
all).**

GPU-h_closed = g × ceil(E / V) × Σ_{t=1..T} (t_env + m × L(t)) / 3600, and
GPU-h_open = E × T × g × m / r_cell / 3600. The cell value is the larger of the
two, times the A1 noise multiplier n_A1 (section 6).

- g = 1 (TP=1 for every rung). V = the replay's measured V (40 for H1, 20 for
  H2). t_env = 2.5 s. T = the harness step cap: 15 for H1 (OSWorld
  `--max_steps`), 100 for H2 (cua-speedrun `MAX_STEPS`).
- L(t) = mean latency of step t over the episodes, using only steps every
  episode completed. Unmeasured steps after the last measured one use the more
  expensive of the last two measured steps (for H2, the last two measured
  non-fold steps, or the last measured fold step for fold steps 31, 41, ...),
  scaled up by the ratio of modelled prompt tokens at t to those at the
  reference step, never down.
- Profiles: H1 screenshot from r1; H1 accessibility tree from r2; H2 screenshot
  from r3 plus the thinking penalty (r4 step 19 minus r3 step 19, floored at 0);
  H2 accessibility tree adds the accessibility penalty (the larger of r2's last
  two step means minus the larger of r1's last two step means, floored at 0) to
  the H2 thinking profile.
- Fallbacks, each flagged: if r4 is not valid, thinking penalty = (2,048 − 300)
  × the largest p90 TPOT over r3's last six steps × 1.5. If r2 is not valid,
  accessibility penalty = r1's steady latency (the larger of its last two step
  means) × (6,144 / r1's modelled prompt tokens at its last step, step 6) ×
  1.5. If r1 or r3 is not valid, no Q2 budget is frozen and the outcome is
  "incomplete: re-probe".
- Rung multiplier m: 1 for 9B and for 4B (conservative). For 27B and 35B-A3B,
  the a1a throughput divided by the rung's A1 throughput from job C, times 1.5
  unless X1 passed; a measured ratio below 1 is used as measured. Without that
  ratio (job C not run or not accepted, its rung phase not run, or a1a or the
  rung's A1 point not valid), max(1, active parameters / 9B) × 1.5, that is
  4.5 for 27B and 1.5 for 35B-A3B.
- r_cell = r_ref / max(P_cell / P_ref, O_cell / O_ref). r_ref, P_ref and O_ref
  are a2's request throughput and its mean prompt and output tokens per
  completed request. P_cell is the cell's mean modelled prompt tokens over
  t = 1..T; accessibility cells include their 6,144 tree tokens on every step.
  O_cell is the cell's output tokens: 300 for H1 and 2,048 for the H2 (thinking)
  cells. If f1's request throughput divided by a1a's is below 0.90, r_ref is
  multiplied by that ratio (design decision 16); otherwise F1 is reported only.
  If f1 or a1a is not valid, no correction is applied, and the projection
  records why.
- If a2 is not valid, the reference is whichever of a1a, a1b and a1c is valid
  with the lowest request throughput, flagged; if none is valid, no Q2 budget is
  frozen ("incomplete: re-probe").
- Context check: in every primary cell, the largest modelled prompt over
  t = 1..T plus O_cell must not exceed `max_model_len` (131,072); otherwise no
  Q2 budget is frozen ("incomplete: re-probe"). Sensitivity rows report how many
  cells exceed it.
- n_A1 is 1 when a1a, a1b and a1c are valid within a 10% range; otherwise as in
  section 6. It is flagged on every cell when it is not 1.
- Sensitivity table: T in {15, 50, 100}, t_env in {1.5, 2.5, 4.0} s, V in {20, 40}
  per replica (V above the measured value is not extrapolated; such rows reuse
  the measured V).

**Accepted jobs only** (section 5, design decision 32). If job A is not
accepted, none of its points enters a budget: X1 is not-run and no Q2 budget is
frozen ("incomplete: re-probe"). If job B is not accepted, no Q1 budget is
frozen. A job C that is not accepted is treated as not run, so the
active-parameter rule prices both rungs.

**Q2 decision.** If the 16-cell total exceeds 90 GPU-h (the dossier's upper
range), Stage 1 is rescoped before the gauntlet (non-thinking mode, a smaller
history window, lower max_tokens or fewer tasks). Below 15 GPU-h, the dossier is
recorded as an over-estimate. Otherwise the total is within the dossier's range.

**Q1.** GPU-s per completion = g × point duration / (prompts × n). Single turn
uses b2. Three turns sum b2, b3 and b6 (b3 falls back to b6 if not valid), every
completion assumed to continue (conservative). Completions = 2,000. If X1 did not
pass, both totals are multiplied by 1.5. Both totals are multiplied by the B1
noise multiplier n_B1 (b1a, b1b, b1c completions per second; section 6).

**Q1 decision.** If 2,000 single-turn completions exceed 6 GPU-h (half the
dossier's 12 GPU-h central estimate), or the three-turn total exceeds 12 GPU-h,
turns, max_tokens or the task count are cut before the gauntlet. If job B is
not accepted, or b2 or b6 is not valid, no Q1 budget is frozen ("incomplete:
re-probe"). The Q1 policy license (D5) is not resolved by this probe.

Stage 1 must reuse these engine settings or re-probe.

## 9. Stop rules

- No point is launched after 85% of the allocation (from the lane's
  `started_at` in `job.env`; if `job.env` cannot be read, from driver start,
  recorded in the summary); a phase with later reserved phases stops launching
  and truncates its running point at that mark minus the later reserves.
- Every running point is truncated at its wall cap or at the allocation end
  minus 4 minutes; in-flight requests get 30 s, then are cancelled.
- USR1 or TERM (the lane sends USR1 180 s before the end): no new request,
  in-flight requests get 30 s, the point is recorded "interrupted", progress
  is saved, then the lane's checkpoint marker is written (first line
  `trigger=SIGUSR1` or `trigger=SIGTERM`, design decision 28), then engines
  stop. An offline point is stopped at once and its requests aborted.
- Slurm `--time` is the hard cap: job A 40 min (0.67 GPU-h budgeted), job B
  20 min (0.34), job C 30 min (0.5); jobs A and B together hold exactly 1.0
  GPU-h, and their budgeted 0.67 and 0.34 are rounded up. A Slurm TIMEOUT
  classifies the job "incomplete": its points are kept and reported, and enter
  no budget (section 5, Acceptance).
- A prefix-caching-off arm and TP=2 runs are not part of this experiment.

## 10. Reported regardless of outcome

Every gate result with its recorded values; every point with its status,
attempts (superseded attempts in full) and metrics, valid or not, including the
standard error of each replay step mean; each job's acceptance verdict, eager
label, and the reasons a job's points were not admitted to a budget; the X1
deltas, seed spread and outcome, with r1's and x1-r1's prompt tokens per
request; the F1 ratio, applied or not; the D8 agreement rate; A1 and B1
stability and noise multipliers; the open-loop reference used and which bound
binds in each cell; engine facts per phase including eager use and `/tmp`
mappings; all GPU-allocated time, including the overlay build and metadata
fetch allocations and any cu130 retry, each against its own cap;
the Q1 and Q2 projections with every flag and the sensitivity table; the
contract SHA-256, the probe code digest and git HEAD, image IDs, receipt hashes
and this file's ledger row; and every deviation from this document.

## 11. External sources

| Source | Revision | Size | SHA-256 | License |
|---|---|---|---|---|
| vLLM image `vllm/vllm-openai:v0.31.0-cu129`, linux/amd64 | manifest sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f, vLLM commit db9527a46873454610df6dbedf79a36d6bf1a7f6 | 11,015,410,140 B compressed, 26,357,336,842 B unpacked | image ID (config) 423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b | vLLM Apache-2.0; CUDA base layers under NVIDIA's container license (used locally, never redistributed) |
| vLLM source, read for flags and APIs | tag v0.31.0 = db9527a46873454610df6dbedf79a36d6bf1a7f6 | not vendored | LICENSE c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4 | Apache-2.0 |
| Qwen/Qwen3.5-9B weights (cached) | c202236235762e1c871ad0ccb60c8ee5ba337b9a | 19,329,393,661 B | receipt 0a9e052d561b017c505adf5a1c6fcdc048522660a0db134486b84edbf3de5cb3 | Apache-2.0 |
| Qwen/Qwen3-0.6B-Base weights (cached) | da87bfb608c14b7cf20ba1ce41287e8de496c0cd | 1,203,641,805 B | receipt e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df | Apache-2.0 |
| Qwen/Qwen3-8B metadata (8 files, no weights) | b968826d9c46dd6066d109eabc6255188de91218 | 15,910,042 B | per-file SHA-256 in the metadata receipt; tokenizer.json aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 | Apache-2.0 (LICENSE file) |
| Qwen/Qwen3.5-27B-FP8 metadata (11 files) | 97f5941bf617e31c5e237364a8602ce3f03a551a | 23,033,229 B | per-file SHA-256 in the metadata receipt; tokenizer.json 5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42 | Apache-2.0 (LICENSE file) |
| Qwen/Qwen3.5-35B-A3B-FP8 metadata (11 files) | 9d1823d2dee688a6b25e77009dc727688c44936e | 23,034,749 B | per-file SHA-256 in the metadata receipt; tokenizer.json 5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42 | Apache-2.0 (LICENSE file) |
| OSWorld `mm_agents/qwen3vl_agent.py`, read for the H1 layout | b138d348256078fa634fc3b73567a7337c793e6b | 30,053 B | c9bb34d3ad822168c66133cd97c607d4645b7eff08072e1e45c49dbbad8491b4 | Apache-2.0; one instruction sentence quoted in `harness/serving_probe/prompts.py` with attribution |
| cua-speedrun `agents/qwen35/agent.py`, read for the H2 layout | be17c72c5efbb145d06f86028336fdf2743a3d98 | 31,910 B | 287ce1244a787e71aa89bc9c0efd6bf24c2779b6918be7e7b8ae932bcf9c1bfc | unresolved (no LICENSE file); layout and parameters only, no code or text copied |
| cua-speedrun `agents/qwen35/init.py`, read for its server's `max_model_len` default (131,072) | be17c72c5efbb145d06f86028336fdf2743a3d98 | 8,671 B | 798246a4cfd00d79af08a0a8ea7cc7e8838e36d5cdf010e920bed028f92894ce | unresolved (no LICENSE file); one parameter value only |
| KernelBench, read for the scout's prompt-length measurement | 423217d9fda91e0c2d67e4a43bf62f96f6d104f1 | not vendored | LICENSE fb5917dd8e4476fa75e89ef6f03dccf07d4859636bc23c7db50e6c0413887b9e | MIT |
| Dr.Kernel paper (arXiv 2602.05885), sampling protocol | v1 | not stored | not applicable | arXiv |

The metadata receipts' own SHA-256 values are produced by the fetch and pinned
in the job B and C manifests (`--weights-pin`); the driver re-verifies them.
