# g2-kimi-expert-streaming-v1: the pilot for "how local is Kimi K2.x's expert routing on real decode workloads, what cache hit rates does it reach on a 128 GB machine, and does a host-side streaming emulator validated on held-out ds4 M5 Max measurements price Kimi K2.6 at about 2-2.6 bits?"

**Status: DRAFT. Not frozen, not admitted, no ledger row.** Drafted on 2026-10-15 by the single
owner of the G2-stream gauntlet's synthesis, on branch `gauntlet/g2-kimi-expert-streaming`, with the
proposal `program/proposals/2026-10-16-g2-kimi-expert-streaming.md`. The blind critic, the
refute-first triad and the two reviewers have not run. Nothing in this file has touched a GPU or the
host. A freeze follows the checklist of section 17, by an operator who did not draft this file. A
material change after the freeze is a new experiment id.

Origin: D122 names G2 as the first research gap of the local frontier-MoE direction. It goes through
the gauntlet because the whole study exceeds 8 GPU-h. This registration covers only the pilot (Slurm
caps 7.45 GPU-h). The full study is described in the proposal and in section 18, and gets its own
registration after this pilot answers. Host slug: `g2stream`. D104's `g2-pilot`, `g2b-*` and
`g2c-*` directories are unrelated and are not touched.

## 1. Question

1. **Locality (Q1).** Take Kimi K2.6 UD-Q2_K_XL, the file a 128 GB Mac would stream, generating its
   own responses with thinking on in chat, coding, agentic tool-use and long-document QA sessions.
   - What are the event-atomic hit-rate curves of LRU, LFU, ds4's decayed-hotness policy,
     out-of-sample static pinning and Belady at 5-50% of the routed pool?
   - Does ds4's policy reach h ≥ 0.70 at 22% in every workload?
2. **Emulator validity (Q2).** Does the three-tier emulator of section 8 reproduce the held-out ds4
   M5 Max measurements of `compute/ds4-targets.json`? It is fixed before data, with one constant
   calibrated on a prompt-independent row, and fed host traces of the exact antirez files. The
   targets are 11 generation levels and three primary within-run contrasts. Does it beat the frozen
   null?
3. **Prediction and decision (Q3; only under section 8.6's verdicts that allow it).** What is the
   matched speed ratio R of Kimi K2.6 to GLM 5.3 on the same sessions at Kevin's two memory
   scenarios? Under VALIDATED only: what are Kimi K2.6's predicted decode rates at about 2.6 and
   about 2 bits?
4. **Trace fidelity.** Do teacher-forced and autoregressive routing agree, and do CPU and CUDA
   llama.cpp agree? Does the simulator reproduce a real engine's logged hits, and do the inputs
   reproduce ds4's token counts?

## 2. What it decides and what it does not

- **It decides,** by section 7.3's table, among: closing the Mac rationale of the Kimi-compression
  lines (G1, G3, G5); running the full study in part or in whole; or reporting only locality
  because the emulator is not trusted.
- **It supplies the full study's inputs:** measured CPU and GPU trace throughput, the real
  between-session SD of h, and the trace-equivalence results.
- **It does not decide:**
  - what Kevin should run on his Mac. GLM 5.3 and V4 Flash already lead on published evidence, and
    this pilot does not test model quality;
  - how fast any model runs on Kevin's own 2 TB drive. B is calibrated on the ds4 maintainer's
    machine; Kevin's drive enters only as a stress corner at 0.5 × B.
- **Reading of the measurements.**
  - The hit-rate readings are confirmatory for the Q2 file's routing, and exploratory for claims
    about the INT4 model (the full study's F3).
  - The emulator verdict is confirmatory for the ds4 conditions listed. It says nothing about
    engines other than ds4.

## 3. Identity and pins

| Item | Pin |
|---|---|
| Kimi file | `unsloth/Kimi-K2.6-GGUF` at `47c7cab1e4...` (Hub sha recorded at download), UD-Q2_K_XL, 8 shards, 340.48 GB; modified MIT; per-shard SHA-256 recorded at download |
| Validation files | `antirez/glm-5.3-gguf` at `1434dad1a2...`: `GLM-5.3-UD-IQ2_XXS_RoutedIQ2XXS_blk78Q2K.gguf`, 211,075,860,864 bytes, SHA-256 `059b36accd4c9acf73099da9f703b574d627869d619b7c4c316aa856e33d472e` (ds4 QA's reference checksum); `antirez/deepseek-v4-gguf` at `f71f23d552...`: the Vision-Exp MXFP4 file, 155,976,459,136 bytes, SHA-256 recorded at download |
| Runtime | llama.cpp tag `b11669` (`620d2225`), built offline in a CPU-only build job on `docker.io/nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`, `CMAKE_CUDA_ARCHITECTURES=90`, CPU and CUDA backends in one image; local image id and provenance receipt recorded at P0 |
| Dump tool | `harness/g2stream/topk_dump.cpp` (to be written): a `cb_eval` callback that asks only for tensors named `ffn_moe_topk-*`, copies them to host, and writes int16 expert ids with (sequence id, position, layer) for each ubatch row; no GPU kernel; reviewed and committed before the freeze; SHA-256 in section 17 |
| ds4 reference | `antirez/ds4` at `90aa4b560a1dec1590f2c60648af404aa40b1188` (2026-09-06), read only, never built or run. Files and SHA-256 of the fetched bytes are in `compute/ds4-targets.json` |
| Policy port | `harness/g2stream/ds4_policy.py` (to be written), ported from `ds4_metal.m` at that commit with MIT attribution. It covers route hotness per selection, halving every 16 decode tokens on the first routed layer's clock, lowest-hotness victim, per-access recency tie-break, protection of the current selection, the global pool, GLM demand-fill, and DeepSeek hotlist preloading from `ds4_streaming_hotlist.inc` (git blob `9f9bf033`) |
| Simulators and emulator | `harness/g2stream/{cache_sim.py, emulator.py}`, grown from the bundle's `compute/sim_g2stream.py`, with its unit tests plus ds4-specific tests (section 9) |
| Validation inputs | ds4 files at `90aa4b56`: `tests/test-vectors/glm-openrouter/prompts/long_memory_archive.txt` (blob `a7355098`), `speed-bench/promessi_sposi.txt` (blob `4655f69d`), `tests/test-vectors/glm-openrouter/prompts/long_code_audit.txt` and `.../continuations/long_code_audit.txt` (candidates), the official-continuation vectors for `glm-openrouter` and `flash-vision-exp` |

## 4. Design: jobs

| Job | Where | Contents | Cap |
|---|---|---|---|
| P0 | Mac or host CPU, no Slurm GPU | Port ds4's policy and pass section 9's tests. Write the three-tier emulator with section 8's constants. Commit the frozen null (done, bundle). Read the REAP observation JSON tables (under 1 GB). Read `ds4_metal.m` and `ds4.c` at `90aa4b56` to settle three questions; any one the code does not settle becomes a bracket corner: (a) whether whole-layer prefill reads insert into, bypass or flush the expert cache; (b) GLM's prefill chunk rule; (c) whether a short append on the selected-address path inserts its experts | 0 |
| P0b | host CPU lane (no GRES) | Build the llama.cpp image. Build the dump tool and test it on the CPU: exact per-expert count equality with `llama-imatrix` on a small MoE GGUF under 1 GB, 512 tokens of fixed text. Download the three GGUFs (Kevin's go-ahead) and verify SHA-256 | 0 |
| P1 | host CPU lane (no GRES) | llama.cpp CPU backend. GLM 5.3 IQ2_XXS and V4 Flash Vision-Exp traces on the inputs of section 8.3. Input-fidelity checks (TE5). Runtime-correctness checks (TE6). 32 matched GLM sessions (section 5.6). The CPU half of TE2: 4 Kimi K2.6 Q2 sessions teacher-forced on the token sequences P2 produced. Wall cap 12 h | 0 |
| P1-gpu | GPUs among 1-7, 3 GPUs | Fallback only if P1 cannot load a validation file on the CPU or exceeds its 12 h wall cap: the same validation traces on CUDA. The 32 matched GLM sessions are not in this fallback; if it runs, R is not computed in the pilot and moves to the full study's F4, and the decision table reads UNRESOLVED | 1.95 (3 × 0.65 h) |
| P2 | GPUs 1-5 | Kimi K2.6 Q2 on CUDA: 64 sessions (section 5) with autoregressive decode; seeded sampled variants (seeds 42-44) on 8 sessions; teacher-forced re-pass of 16 sessions (TE1); Anemll's prompt at top-8 and top-4 (X1); first two sessions repeated after a forced kill (resume test) | 5.0 (5 × 1.0 h) |
| P3 | 1 GPU among 1-7 | K2.6 Q2 with experts in host RAM and llama.cpp's GPU expert cache (PR #29887) at 14% of the pool. 4 sessions × 512 decode tokens, with the routing dump on. The simulator, configured with the engine's semantics read from the b11669 source, must reproduce the logged hits (TE4, KC1) | 0.5 (1 × 0.5 h) |

Order: P0 and P0b first; then P1 and P2 (independent); then P3 and the CPU half of TE2; then the
analysis. P2 starts only when at least five GPUs among 1-7 are idle and no frozen registration of
this program is running. It never uses GPU 0.

## 5. Workload sampling

1. **Sessions.** 64 Kimi sessions, 16 per workload. The session is the unit of analysis.
2. **Sources** (Hub revisions pinned at P0; licences in section 13):
   - **Chat:**
     - `allenai/WildChat-1M` (8): conversations with at least two user turns, English or Chinese,
       not flagged toxic;
     - `OpenAssistant/oasst2` (8): conversation trees, the highest-ranked path, at least two user
       turns.
   - **Coding:**
     - `bigcode/bigcodebench` instruct split (10);
     - WildChat conversations whose first user turn contains a fenced code block (6), drawn from a
       pool disjoint from chat.
   - **Agentic tool use** (decision points per session in parentheses):
     - `nebius/SWE-agent-trajectories` (6; 2 decision points);
     - `SWE-bench/SWE-smith-trajectories` (4; 2 decision points);
     - `gorilla-llm/Berkeley-Function-Calling-Leaderboard` multi-turn categories (3; 1 decision
       point);
     - `Team-ACE/ToolACE` (3; 1 decision point).
   - **Long-document QA:**
     - `zai-org/LongBench-v2` (8; documents of 8K-16K Kimi tokens preferred, longer ones truncated
       from the end of the document to fit 16K with the question kept);
     - `deepmind/narrativeqa` (4; story truncated to 16K);
     - `xiaowu0162/longmemeval-cleaned` (4; history truncated to 16K from the oldest sessions).
3. **Draw.** For each source:
   - rows passing the filters are sorted by SHA-256 of their canonical JSON;
   - the order is permuted with `numpy.random.default_rng(42)`;
   - the first n are taken.

   The session ids and their hashes are committed before any GPU job.
4. **Rendering and decode.**
   - **Template.** Kimi's chat template embedded in the GGUF, rendered by llama.cpp's Jinja engine,
     so no Moonshot remote code runs. If the embedded template cannot render tool declarations,
     tools are rendered as one JSON block in the system message; this fallback is flagged per
     session.
   - **System prompts.** Four variants per workload (none, short neutral, long neutral,
     domain-specific; texts committed at P0), assigned round-robin by draw order, following S123's
     template-diversity warning.
   - **Thinking mode** on. Greedy decoding for all 64 sessions.
   - **Decode caps.** 2,048 tokens per session for chat, coding and long-document QA. For agentic
     sessions, 1,024 per decision point and 2,048 per session.
   - **Context cap** 16,384 tokens; older turns are dropped from the front, with the system prompt
     and the task statement kept.
5. **Agentic replay.**
   - At each decision point (25% and 75% of a trajectory's turns, or its single decision turn), the
     recorded prefix, including recorded tool outputs, is teacher-forced.
   - Kimi then generates its own next turn. That turn is decode-traced and then discarded, and the
     recorded trajectory continues.
   - This approximates a live agent's routing (the recorded tool outputs follow another model's
     actions) and is disclosed as such.
6. **Matched GLM sessions** (for R): the first 8 Kimi sessions per workload in draw order (32),
   rendered with GLM 5.3's template, with GLM generating its own greedy responses. The decode cap is
   1,024 tokens (2,048 for agentic) and the context cap 16,384.
7. **Sampling sensitivity.** The first 2 sessions per workload (8) are re-decoded with sampling at
   the model card's recommended temperature and top-p (recorded at P0), with seeds 42, 43 and 44.

## 6. Estimands

- **Events.**
  - One (token, routed layer) pair is one event: the k = 8 selected experts.
  - Shared experts are always resident and excluded. The dense layer is excluded.
- **Hit rate.** h = (selected experts resident at the event's start) ÷ (all selections), pooled
  over the routed layers and decoded tokens of a window. Replay is event-atomic: hits are counted
  before any insertion, and the event's experts are protected while it is served (S123,
  Definition 2).
- **What counts as decode.** Prefill tokens change cache state according to the engine's prefill
  rule (P0), but are never counted in h. No prefetch hit is counted as a hit; resident means
  resident.
- **Capacity.** Capacity is a byte budget over the actual per-expert bytes of each layer in the
  GGUF tensor table (the K2.6 Q2 file mixes IQ2_XS, IQ3_XXS and Q4_0 projections). Budgets are 5,
  10, 14, 22, 32, 40 and 50% of the routed-pool bytes. 14%, 22% and 32% are the named points.
- **Scope and start state.**
  - **Scope.** Global pool (primary; ds4's GLM default) and equal per-layer budgets (secondary).
  - **Start state.** Each session starts from an empty cache, with its prompt prefill applied by
    the engine's rule (primary). Secondary: warm carry-over from the previous session of the same
    workload in draw order.
- **Windows.**
  - *cold*: the first 128 decoded tokens;
  - *session*: all decoded tokens;
  - *warm*: decoded tokens after the first 512.

  Each is reported with and without compulsory first-touch misses.
- **Policies.**
  - LRU and LFU (persistent counts, recency ties).
  - ds4's policy, with the GLM demand-fill variant for Kimi; the hotlist-preload variant only where
    ds4 has a list.
  - Static pinning, chosen leave-one-session-out within each workload and leave-one-workload-out.
  - Belady with event semantics, without and with bypass.
- **Workload mean** = the mean of per-session h in that workload. **Pooled** = the equal-weight
  mean of the four workloads.
- **Locality descriptors:**
  - reuse after 1 token and within 64 tokens;
  - per-layer Zipf slope;
  - hot-set Jaccard across workloads (top 10% per layer);
  - the union-to-capacity ratio;
  - the IRM-shuffle split (measured h minus h on the session's trace shuffled within session);
  - exact LRU miss-ratio curves by stack distance (Mattson).
- **Emulator outputs:** predicted prefill and generation rates and append latencies for each ds4
  target (section 8), predicted K2.6 decode at the two memory scenarios, and R (section 7.3).

## 7. Hypotheses, gates, kill criteria and decision rules

### 7.1 Gates (must pass before any reading is interpreted)

- **G1 dump fidelity.** On the small MoE, the per-expert counts the dump tool writes must equal
  `llama-imatrix`'s exactly. Fail: fix the tool, then re-run the test. No trace is used until this
  passes.
- **G2 input fidelity (TE5).**
  - V1's prompt must tokenize to 463 input tokens under ds4's chat rendering, reproduced in
    llama.cpp.
  - V2's greedy output must be the word "apple" separated by single spaces for all 64 tokens.
  - If V1 fails, V1 is excluded from the prefill holdouts, which is reported. If V2 fails, V2's
    routing comes from teacher-forcing the apple string.
- **G3 runtime correctness (TE6, also KC2).** On ds4's official-continuation vectors for that
  model, llama.cpp's teacher-forced top-1 agreement must be at least 0.60. Context: ds4's own Q2 of
  V4 Flash 0731 agrees 78.98% with BF16 (dossier S117); a broken attention or indexer path falls far
  below.
- **G4 resume.** A session's trace from a job killed and resumed must be byte-identical to the same
  session's trace from an uninterrupted job.

### 7.2 Predictions (fixed before data)

| ID | Prediction | Test | Falsified if |
|---|---|---|---|
| PR1 | ds4's policy reaches h ≥ 0.70 at 22% (session window, global scope, cold start) in every workload | per-workload 95% cluster-bootstrap CI | any workload's upper bound < 0.70 |
| PR2 | At 22% and 32%: ds4 ≥ LRU ≥ out-of-sample static, in the pooled mean and in at least 3 of 4 workloads; Belady − LRU ≥ 0.10 at 14% | paired session bootstrap of differences | any reversal whose CI excludes 0; or the Belady gap's upper bound < 0.10 |
| PR3 | The two-tier ablation (no file cache) misses at least one of K1-K3 by more than 15% | section 8.5 contrast rule applied to the ablation | the ablation passes all three |
| PR4 | The emulator reproduces K1, K2 and K3 within ±15% with the observed sign | section 8.5 | any primary contrast outside ±15% or of the wrong sign |
| PR5 | The emulator passes section 8.5's levels test | section 8.5 | the levels test fails |
| PR7 | TE1: mean top-8 overlap ≥ 0.95 and |Δh| ≤ 0.01 at 22%; TE2: |Δh| ≤ 0.02 at 22% | section 9 | either bound is missed |

PR6 is the decision rule of section 7.3. Numbering follows the proposal.

### 7.3 Kill criteria and decision rules

- **KC1.** The simulator's hits differ from llama.cpp's logged hits on the same P3 run, beyond what
  the engine's documented semantics explain (TE4). The simulator is wrong; all readings stop until
  it is fixed and P3 re-run under a new id.
- **KC2.** G3 fails for GLM 5.3 or V4 Flash. That model's targets are dropped. If GLM 5.3 fails, the
  emulator half stops, and Q1 is still reported.
- **KC3.** TE2's |Δh| at 22% exceeds 0.03 on the Kimi sessions. Backend numerics alone could move
  the predictions beyond the bands, so the validation is uninformative and the emulator half stops.
- **KC4.** The verdict (section 8.6) is LEVELS_ONLY or FAILED. No R and no Kimi speed is reported.
- **KC5.** More than 10% of sessions are lost to infrastructure after one retry. Stop and report.

R is predicted Kimi K2.6 Q2 decode over predicted GLM 5.3 IQ2_XXS decode on the 32 matched
sessions:
- ds4's policy, session window, cold start;
- emulator central constants, re-calibrated B;
- at each of two memory scenarios:
  - (S-stop) 88 GB available to the engine;
  - (S-today) 61.8 GB, the 2026-10-15 reading;
- each model's expert budget is the dossier's A7 rule: available memory minus resident non-routed
  weights, minus KV at the session's context, minus 3.2 GB;
- the file cache is 8 GiB in both scenarios (bracket 4-16).

The 90% interval takes, across bracket corners and B ∈ {B_cal, 0.5 × B_cal}, the minimum of the
session-bootstrap 5th percentiles and the maximum of the 95th.

| Verdict (8.6) | R | Reading | Next |
|---|---|---|---|
| VALIDATED or CONTRASTS_ONLY | upper bound < 1 in S-stop and S-today | KIMI_DOMINATED | Recommend closing the Mac rationale of G1, G3 and G5; the full study does not run |
| VALIDATED or CONTRASTS_ONLY | lower bound ≥ 1 in S-stop | KIMI_COMPETITIVE | Full study F0-F5 |
| VALIDATED or CONTRASTS_ONLY | otherwise | UNRESOLVED | Full study F0-F4; F5 waits |
| LEVELS_ONLY or FAILED, or KC2/KC3 stopped the emulator | not computed | EMULATOR_NOT_TRUSTED | Q1 only; F1-F3 only on Kevin's request |

Kimi K2.6's absolute predicted decode is reported only under VALIDATED. It is reported at S-stop
and S-today, per workload and pooled, for two geometries:
- the Q2 file (about 2.6 bits);
- the smallest Unsloth K2.6 file in `47c7cab1` (about 1.9-2 bits; byte geometry from its header
  read at P0, with Q2 routing borrowed and labelled as such).

## 8. Emulator specification and validation rule

### 8.1 Structure (fixed)

**Decode step.** For each decoded token, for each routed layer l in order:

  t_l = (non-routed bytes of layer l + bytes of the 8 selected experts) ÷ (e × 614 GB/s)
      + Σ over misses m: bytes_m ÷ B          if m is served from the SSD
                         bytes_m ÷ C_copy     if m is served from the file cache

- Reads and compute do not overlap within a layer, because the layer waits for its experts.
- Misses within a layer are read in parallel at the aggregate rate.
- The token's time is Σ_l t_l, plus the output head and attention reads over the context (KV bytes
  from the model's attention layout).
- After every prefill, the first decode step adds τ_first:
  - central 0;
  - bracket: the non-routed bytes ÷ B (a full page-in, ds4's warning in `docs/SSD_STREAMING.md`).

**Tiers.**
1. The engine's expert cache, under the ported ds4 policy with ds4's budget for the condition.
2. The macOS file cache: an LRU over expert-tensor byte ranges, filled by every SSD read (selected or
   whole-layer). Its capacity C_fc is:
   - ds4's logged minimum available memory for the condition where published (15.05 GiB at the
     61.35 GiB budget, 27.87 GiB at 35.36 GiB);
   - otherwise 128 GiB − ds4's planned memory − 20 GiB for the OS: 68.4 GiB for the 16 GiB QA runs
     (planned 39.63 GiB);
   - for V4 Flash at 86.2 GiB: 128 − 86.2 − 7.74 GB of non-routed weights (7.2 GiB) − 20, so 14.6
     GiB.
3. The SSD.

ds4 opens the model without `F_NOCACHE` (C22), so a miss is served by the file cache when its byte
range is resident there.

**Prefill.** Per the P0 code reading:
- initial prefill and whole-layer appends read each routed layer's whole tensors per chunk;
- selected-address appends read only the selected experts not resident;
- prefill compute runs at P_c tokens/s: 257 for GLM 5.3 and 790 for V4 Flash (ds4's in-memory V4
  Flash Q2 prefill at 2K, scaled by active parameters 13.27B → 40.8B for GLM).

**Start states, by each target's protocol:**
- QA medians after a discarded warm-up: the file cache holds the previous identical run's reads in
  LRU order, and the expert cache starts empty (a new process).
- ds4-bench runs: the file cache is empty at process start (central), with a bracket corner warm
  from one previous identical run.
- Snapshot restores restore KV only, and leave the expert cache and file cache as they were.

### 8.2 Constants

- **Calibrated: B only.** B is the solution of emulated_time(CAL-B; B) = 30.8 s (the 16-token
  whole-layer append at the 61.35 GiB budget, three-run median), by bisection, with the file cache
  state replayed from that run's preceding steps.
  - B is re-solved at every bracket corner. Desk value with no file-cache hits: 6.08 GB/s.
  - Consistency checks, not refits: the 43- and 114-token whole-layer appends (34.4 s, 34.9 s) must
    come out within ±15%.
- **Fixed before data** (central value, with bracket corners):

  | Constant | Central | Bracket |
  |---|---|---|
  | e (fraction of 614 GB/s) | 0.61 | 0.55-0.61 |
  | C_copy (file-cache copy rate) | 30 GB/s | 15-60 GB/s |
  | C_fc (file-cache capacity) | as in 8.1 | × 0.5-1.0 |
  | τ_first | 0 | 0 or a full non-routed page-in |
  | GLM prefill chunk (if P0 cannot settle it) | 2,048 | 1,024-4,096 |
  | Prefill-path variants (if P0 cannot settle them) | — | both |

- **Corners.** A verdict that holds at the central constants and at every corner is ROBUST. One that
  holds at the central constants only is FRAGILE.

### 8.3 Targets

All targets are first-party, from ds4 at `90aa4b56` (`compute/ds4-targets.json`).
- **Generation levels (holdouts):**

  | ID | Condition | Value (t/s) | Noise class |
  |---|---|---:|---|
  | V2 | 16 GiB, apple prompt | 6.14 | median of 3 |
  | V3 | 35.36 GiB, 8K initial | 3.655 | repeated on both machines |
  | V4 | 35.36 GiB, after a 4K append | 3.885 | repeated |
  | V5 | 61.35 GiB, after a 16-token selected-address append | 5.11 | median of 3 |
  | V5i | 61.35 GiB, initial generation | 3.78 | median of 3 |
  | V5b | 61.35 GiB, after a 16-token whole-layer append | 4.09 | median of 3 |
  | V5bi | 61.35 GiB, its initial generation | 4.14 | median of 3 |
  | V6 | 61.35 GiB, 43-token append | 5.34 | single |
  | V7 | 61.35 GiB, 114-token append | 5.39 | single |
  | V8 | V4 Flash Vision-Exp, 86.2 GiB, after the 8K prompt | 11.90 | single |
  | V9 | V4 Flash Vision-Exp, after the 4K append | 19.34 | single |

- **Primary contrasts:**
  - K1 = V9/V8 = 1.625 (within run);
  - K2 = V5/V5b = 1.249 (identical routing, code-path toggle);
  - K3 = V5/V5i = 1.352 (within run).
- **Secondary:**
  - prefill levels V1 (12.59), V3p (92.74), V4p (87.70), V8p (299.87), V9p (263.32);
  - append latencies: 2.9, 5.4 and 8.7 s selected-address; 30.8 (the calibration row), 34.4 and
    34.9 s whole-layer;
  - contrasts K4 (1.335), K5 (1.382), K6 (latency ratios) and K7 (1.05-1.07).
- **Excluded** (named in the targets file): pre-follow-up code rows; GLM-5.3-Flash unless llama.cpp
  loads `glm5-next` at P0, decided before any trace; download-overlapped runs; the prefix-replay run.

### 8.4 Inputs and fidelity strata

| Stratum | Targets | Inputs |
|---|---|---|
| EXACT | V1, V2 | first 2,500 bytes of `long_memory_archive.txt`; the apple prompt; ctx 1024; greedy; 16 and 64 tokens |
| PROBABLE | V3, V4, V8, V9 and their prefill levels | ds4-bench on `promessi_sposi.txt` to the 8K frontier, then a 4K append; a fixed greedy non-EOS probe; 16 tokens (GLM) or 128 tokens (V4 Flash) |
| CANDIDATE | the 61.35 GiB rows | the first 1,024 tokens of `long_code_audit.txt`; 64 greedy tokens; then the appended tokens |

The CANDIDATE appended tokens are the 16-token `continuations/long_code_audit.txt` when it renders
to 16 tokens. Otherwise they are the next 16, 43 or 114 tokens of the code-audit file, wrapped as a
tool-result message.

Generated tokens on the host come from llama.cpp greedy decoding, not ds4's Metal output, which is
unpublished. That divergence is bounded only through TE2's CPU-against-CUDA proxy.

The verdict is computed on all holdouts and again on the EXACT and PROBABLE strata only. If the two
disagree, it is reported as "input-fidelity-limited".

### 8.5 The validation rule

Let err_i = ln(pred_i ÷ obs_i). Per-target allowances: ε_i = 0.10 for medians of three and repeated
conditions, 0.15 for single runs.

- **Levels test.** All three must hold:
  - the aggregate over the 11 holdout generation levels, G = exp(mean |err_i|), is at most 1.20;
  - every |err_i| ≤ ln(1.20 × (1 + ε_i));
  - mean |err_i| is below the frozen null's 0.3469 (G = 1.415).
- **Contrasts test.** For each primary contrast j: |ln(pred_ratio_j ÷ obs_ratio_j)| ≤ ln(1.15), and
  the predicted ratio is on the same side of 1 as the observed one.

**How single-run noise is handled:**
1. Allowances. ds4's own regression floors sit about 10% below its three-run reference medians
   (5.5 against 6.14; 11.3 against 12.59). The same 35.36 GiB condition on ds4's two machines
   differed by 1.9-3.8% in generation and 4.5-8.0% in prefill. Single runs get 1.5 times the median
   allowance.
2. The contrasts are primary. They are within one run or one pair, so machine-level drift and the
   calibration's error cancel.
3. No single target can decide the verdict alone: the aggregate test, the per-target bounds, the
   contrasts and the strata must agree.
4. The ±40% spread of single Mac shots in 2609.18063 (a 16 GB machine under memory pressure) is not
   adopted, and this is disclosed. If the full study ever obtains repeated ds4 runs, ε is
   re-estimated under a new id.

### 8.6 Verdicts

- **VALIDATED:** both tests pass.
- **CONTRASTS_ONLY:** contrasts pass, levels fail. The mechanism reproduces relative effects, but
  absolute speed is untrusted; R is reported, absolute speed is not.
- **LEVELS_ONLY:** levels pass, contrasts fail. The level match is not attributable to the
  mechanism; nothing is predicted.
- **FAILED:** neither test passes.

Each verdict carries ROBUST or FRAGILE (section 8.2) and the stratum caveat (section 8.4).
Ablations (no file cache, no cold start, LRU in place of ds4's policy, one prefill path, B per
target) are scored with the same rule and reported. PR3 reads the two-tier ablation.

## 9. Trace-equivalence and fidelity checks

| Check | What is compared | Metric | Pass |
|---|---|---|---|
| TE1 | Kimi Q2 autoregressive decode against a teacher-forced re-pass of the same tokens (16 sessions, P2) | mean top-8 overlap per (token, layer); exact-set rate; per-layer curve; Δh at 14/22/32% (ds4 policy) | overlap ≥ 0.95 and |Δh| ≤ 0.01 (PR7). If it fails, the full study traces decode autoregressively |
| TE2 | CPU against CUDA llama.cpp, same file, same tokens (4 Kimi sessions); a proxy for the Metal divergence that cannot be measured | same metrics; flip rate against the 8th-9th score margin | |Δh| ≤ 0.02 (PR7); above 0.03 is KC3 |
| TE3 | Dump tool against `llama-imatrix` (G1) | per-expert counts | exact |
| TE4 | Simulator against llama.cpp's GPU expert cache logs (P3), with scope, capacity unit, eviction and hit definition read from the b11669 source and committed before P3 | total hits and misses | exact, or within the log's rounding (KC1) |
| TE5 | Inputs against ds4 (G2) | token counts; apple string | exact |
| TE6 | llama.cpp against ds4's official continuations (G3) | teacher-forced top-1 agreement | ≥ 0.60 |
| X1 (cross-check, not a gate) | Anemll's prompt, top-8, 64 per-layer LRU slots, cold, 100 tokens, on K2.6 Q2 | h | reported against Anemll's 67.2% on K2.5 TQ1_0; a gap over 0.08 is discussed |
| Sim unit tests | Che within 0.01 on IRM traces; LRU inclusion; ds4 without hotness ≡ LRU; Belady ≥ every online policy; ds4 port reproduces hand-worked examples from `ds4_metal.m` (decay at token 16, tie-break, protection) | | all pass before any real trace is replayed |

## 10. Operating characteristics (simulated before any data)

From `program/proposals/evidence/2026-10-16-g2-kimi-expert-streaming/compute/sim-g2stream.json`
(seeds 42-44; synthetic routing with E = 384, k = 8, Zipf α 0.9, and reuse 0.32 after 1 token and
0.80 within 64 tokens, matching S82's K3).

**Hit rates.**
- At 22%: ds4's policy 0.69, LRU 0.68, out-of-sample static 0.51-0.55.
- Synthetic between-session SD: 0.005 for the dynamic policies (a floor), 0.03-0.04 for static.
- Sample size from an assumed real SD: the CI half-width is 1.96 × SD ÷ √n. n = 16 gives ±0.025 at
  SD 0.05 and ±0.039 at SD 0.08; n = 64 (full study) gives ±0.012 and ±0.020.
- PR1's bound is decisive if the true h is at least 0.74 at SD 0.08, or at least 0.73 at SD 0.05.
- The pilot measures the real SD and reports it.

**Cold start.** At 22%, the cold deficit is 0.039 over 64 decoded tokens and 0.020 over 128. The
compulsory share of selections is 31% and 23%.

**Validation rule** (20,000 replicates per row):

| Emulator bias | Spread 0.05 | Spread 0.10 | Spread 0.15 |
|---|---:|---:|---:|
| none | 0.999 | 0.90 | 0.47 |
| 10% | 0.96 | 0.61 | 0.25 |
| 20% | 0.40 | 0.15 | 0.05 |
| 28% or more | at most 0.007 | at most 0.007 | at most 0.007 |

**Primary contrasts:**
- 0.79, 0.67 and 0.42 for an unbiased mechanism at contrast SD 0.03, 0.06 and 0.10;
- 0.22-0.37 at 10% mechanism bias;
- at most 0.03 at 20% or more;
- the 0.79 ceiling comes from single-run noise on K1.

So VALIDATED is hard to reach by luck, and a FAILED reading is plausible even for a useful
emulator. Both facts are reported with the verdict.

**Sensitivity.** At B ≈ 6 GB/s, one point of h moves V4 Flash's decode time by 7-11% and GLM 5.3's by
about 5%. So the levels test needs h within about 0.02-0.04, which TE1 and TE2 bound.

## 11. Seeds

seeds: [42, 43, 44].
- `numpy.random.default_rng(42)` for every session draw.
- Seeds 42, 43 and 44 for the sampled re-decodes (section 5.7) and the synthetic simulations.
- Bootstrap seed 42 (2,000 resamples).
- Greedy decoding everywhere else, so no other randomness exists. llama.cpp's sampler seed is set
  explicitly even for greedy runs.

## 12. Compute plan and caps

Arithmetic in `compute/caps-g2stream.json`. Throughputs are this gauntlet's estimates until P1 and
P2 measure them.

**P2: 5 GPUs × 1.0 h = 5.0 GPU-h.**
- Tokens:
  - prefill: 464,000 tokens (16 sessions each at about 2K for chat, 1K for coding, 12K for agentic,
    14K for long-document), plus a 144,000-token re-pass;
  - decode: 96,000 tokens, plus 24,576 seeded.
- Rates: 600-1,500 tokens/s prefill and 60-150 tokens/s aggregate decode with 8 parallel slots;
  loading takes 5-15 min.
- Wall time: 0.42-1.09 h, central about 0.75 h (3.77 GPU-h expected).
- The 1.0 h limit cuts the slow tail. Sessions unfinished at the limit are reported missing, and
  KC5 applies if more than 10% of any workload is missing. Raising the cap is a new registration
  id.

**P3: 1 GPU × 0.5 h = 0.5 GPU-h.** 4 × 512 decode tokens at 5-10 tokens/s, with CPU-expert prefill
of about 16K tokens and a 340 GB load.

**P1-gpu (conditional): 3 GPUs × 0.65 h = 1.95 GPU-h.** GLM 5.3 takes 0.4 h and V4 Flash 0.25 h, for
about 27K exact-input tokens.

**Totals.** Caps sum to 7.45 GPU-h (5.5 without the conditional fallback), under the 8 GPU-h line.
About 4.1 GPU-h is expected.

**Not GPU.** P0, P0b and P1 run on CPU. P1's wall cap is 12 h; its CPU rates (llama.cpp CPU with no
AMX on this VM) are unmeasured.

**Downloads.** 707.5 GB in all (211.08 + 155.98 + 340.48), about 57 min at the 207 MB/s the CPU fetch
lane reached. They need Kevin's go-ahead.

## 13. Data and licences

- **Models:**
  - Kimi K2.6 and the Unsloth GGUF: modified MIT.
  - GLM-5.3: the upstream GLM-5.3 Licence. The antirez repository carries no licence tag; research
    use is permitted, and model-as-a-service operators above US$10B revenue need a review.
  - V4 Flash Vision-Exp: MIT.
- **ds4** (read and ported): MIT, with attribution kept in the port's header.
- **Datasets** (Hub tags read 2026-10-15):

  | Dataset | Licence |
  |---|---|
  | WildChat-1M | ODC-BY (attribution in results) |
  | oasst2, bigcodebench, BFCL, ToolACE, LongBench-v2, narrativeqa | Apache-2.0 |
  | SWE-agent-trajectories | CC-BY-4.0 |
  | SWE-smith-trajectories, longmemeval-cleaned | MIT |
  | REAP observation tables | Apache-2.0 (JSON tables only; pickles are never opened) |

  The Chaos K2-Thinking traces carry no licence: not used in the pilot; optional later, only if
  Kevin accepts their gate, and never redistributed.
- **Excluded:** SWE-bench_Verified (no tag), livecodebench (tag "cc" only), emozilla/quality (no
  tag), and the unlicensed K2.6 agent-trace sets.
- **Storage.** Raw traces, token ids and generated texts stay on the host under
  `~/cotcodec-runs/stage0/g2stream/`. The repository receives aggregates and hashes only.

## 14. Integrity gate (the seven AI-research failure modes)

1. **An implementation bug passing self-review.**
   - The simulators carry analytic unit tests (Che, inclusion, ds4 ≡ LRU without hotness, the
     Belady bound) and hand-worked ds4 cases.
   - TE4 checks the simulator against a real engine's counters, and TE3 checks the dump against a
     stock tool.
   - A bug found after data is fixed under a new id.
2. **A hallucinated citation.** Every source in the proposal's claim registry was fetched (snapshot
   hashes in the bundle). ds4 and Anemll were read at pinned commits.
3. **A hallucinated result.** Every number reported comes from a hashed output file named in the
   results, with its script's SHA-256.
4. **Shortcut reliance.** The emulator has one calibrated constant on a prompt-independent row.
   Primary tests are contrasts that a constant cannot fit. The null is frozen.
5. **A bug reframed as insight.**
   - A surprising hit rate is first re-checked against TE1-TE4, then against the IRM shuffle.
   - A surprising validation result is first checked across the strata and the corners.
6. **Methodology fabrication.** Every element of the method is in this file and the proposal before
   data. Deviations are listed in the results under "deviations".
7. **Frame-lock.**
   - The decision table includes the outcome that closes the Kimi lines, and the outcome that says
     the emulator cannot be trusted.
   - The proposal records the kill-shot's decision-irrelevance argument and the two cell readings
     that were wrong.

## 15. Infrastructure failures and exclusions

- A session lost to a crash, OOM or timeout is retried once with the same inputs. If the retry also
  fails, the session is reported missing, never replaced by a new draw.
- Exclusions are never made on outcome values.
- If more than 10% of sessions in any workload are missing, KC5 applies.
- A validation target whose inputs fail G2 is reported and dropped from that stratum only.

## 16. Reported regardless of outcome

- **Curves and descriptors.** Every hit-rate curve (all policies, scopes, windows and workloads),
  per-session distributions (P10, median, P90), win counts, and the locality descriptors.
- **Checks.** TE1-TE6 and X1.
- **Emulator.** Every prediction with its constants and corners; the verdict and stratum results;
  every ablation's score; the null's frozen scores.
- **Measured rates.** The throughputs and the between-session SD the full study needs.
- **Process.** Missing sessions, deviations, the GPU-h and wall time used.

## 17. Freeze checklist

1. Kevin's go-ahead for 707.5 GB of downloads; downloads verified by SHA-256.
2. The llama.cpp image built, with its local id and provenance receipt; the dump tool committed;
   G1 passed on the CPU.
3. The ds4 policy port and the emulator committed. Section 9's unit tests pass. The P0 code reading
   of the three prefill questions is committed, with line references at `90aa4b56`.
4. The session ids, hashes, system-prompt texts and sampling parameters committed.
5. The analysis script committed. The order in which it computes B (calibration first, written to a
   hashed file before any holdout is read) is checked by a test.
6. Manifests rendered for P1-gpu, P2 and P3:
   `python3 scripts/submit_docker_research_job.py <manifest> --dry-run`, then `--test-only`, both
   passing. The orx `slurm-manifest` node is committed on `orx/g2stream-pilot`.
7. The SHA-256 of every file above is listed in this section of the frozen copy.
8. A fresh pre-freeze audit by an agent that did not draft this file.

## 18. Consequences for the full study (provisional; registered separately)

The full study's design is in the proposal (F0-F7; 15.3-41.0 GPU-h, cap 50). Its inputs from this
pilot:
- the measured trace throughputs, which re-derive the cap;
- the real between-session SD, which sets n (64 per workload unless the SD exceeds 0.10);
- TE1, which decides between teacher-forced and autoregressive tracing;
- the verdict and R, which decide whether it runs at all (section 7.3).

INT4-against-Q2 equivalence (F3) is pre-specified now: Q2 traces may stand in for INT4 claims only if
|Δh| ≤ 0.02 at 14%, 22% and 32% in every workload. Otherwise both are reported.
