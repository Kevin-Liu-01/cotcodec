# Question sweep: agent-memory causality and GPU memory (2026-10-14)

This sweep was run under D103 and produced thirteen candidate questions:

- seven on agent memory and its causal role (AM1-AM7);
- six on hardware memory and GPU acceleration for inference and RL (G1-G6).

A fresh verifier checked every candidate against primary sources. Three
independent judges scored the nine candidates that were not occupied, and
they are ranked with the gates of the 2026-10-11 renewal. This is a dossier
for Kevin, not an adoption. Nothing here starts a run, and no score here is a
gauntlet score.

Companion file: [`ranking.json`](ranking.json). It holds every judge's
scores, the means and minima, the gate results, the rank, the verifier's
verdict and the owner's disposition, machine-readable.

## The short answer

| Role | Key | Question | First real result, and when | Why it matters |
|---|---|---|---|---|
| **Overall lead and GPU-area lead** | G2 | Does the per-token log-prob mismatch between vLLM rollout and the RL trainer grow with token position for Gated DeltaNet (GDN) hybrids (Qwen3.5) while dense models stay flat? If it does, which kernel causes it? | About 3 GPU-h (cap 4), using only stock libraries and models already on the host. The output is mismatch curves against token position up to 16K for Qwen3.5-4B and 9B, set against dense controls. The source is named: chunked vs recurrent GDN, attention backend, LM-head precision. An fp32 reference shows whether the rollout side or the trainer side has drifted. About a day of running once admitted | Training-inference mismatch is a known cause of RL collapse ([VeXact](https://arxiv.org/abs/2605.14220), 2026-05-14). GDN hybrids are what open RL now trains, and every systematic mismatch study found so far used dense or MoE models. If the mismatch grows with position, the result names the kernel to align and argues for position-aware importance-sampling caps in long-CoT RL. If it is flat, the null tells hybrid users that the dense corrections suffice. Either way the result changes what practitioners do |
| **Memory-area lead** | AM1 (AM2 and AM6 folded in) | On LongMemEval, with a reader whose outputs are bit-exact on replay, what is the exact outcome of every subset of an 8-memory pool? How often do the per-memory credit rules that 2026 memory learners train on pick a worse keep set than the exact optimum? | Step 0 runs once one licensed checkpoint (Qwen3-8B) is fetched and costs about 1 GPU-h. It gives the node's first batch-invariant A/A identity rate and its throughput cost. After 2-3 days of harness work, about 4-6 GPU-h give exact 256-subset tables for 200 questions and each credit rule's keep-set regret | [CMP](https://arxiv.org/abs/2610.02070) (2026-10-01) shows that memories act jointly. Yet Hindsight-PRM, MeClear and MGPO train on per-memory credit. Exact potential outcomes are ground truth that no API-based study could afford. A high regret means memory-RL rewards built on per-memory credit are misspecified. A low regret validates the cheap credit on a real benchmark. Step 0 also decides whether exact paired replay works on this node at all, which the legacy memory oracles never achieved |

The GPU alternate is G1, the memory levers for hybrid RL rollouts. Its
fixed-length FP8-KV cells are partly being measured today by the exploratory
inference-baseline-v1 jobs on the host (O2).

## How to read this

- **Rank** is the mechanical order, computed as on 2026-10-11:
  - Gates: a candidate must clear two gates across all three judges, lowest
    correctness at least 5 and lowest citability at least 6.
  - Order: gate passers are ordered by mean significance, then mean novelty
    residual, then mean feasibility.
  - Failures: candidates that fail a gate follow, in the same order. AM3, G4
    and G5 fail the correctness gate.
- **Recommendation** is the owner's, and it is not the rank. The judges gave
  scores and reasons, not verdicts. The owner's disposition on each entry
  (RECOMMEND, ALTERNATE, FOLD, HOLD, DROP) is advisory.
- **Scores** are three-judge means on 0-10 scales:
  - significance (Sig);
  - correctness (Corr);
  - citability (Cite);
  - novelty residual (Nov);
  - feasibility (Feas).

  Per-judge scores appear as J1/J2/J3, each in the order Sig, Corr, Cite,
  Nov, Feas.
- **Corrections govern.** The verifier's corrected question, and every judge
  finding that an owner check confirms (O1-O9 below), governs over the
  scouts' text.
- **GPU-hours** are estimates unless stated.
- **Novelty verdicts** (STILL_OPEN, NARROWED, OCCUPIED) mean present or
  absent in the stated queries through 2026-10-14. They never claim that
  nothing exists.

## Method

### Procedure

| Step | Who | Output | Counts |
|---|---|---|---|
| Brief | Context agent | A read-only brief: D103, the legacy memory work (D17, GAAMA, the transport screens, the lifecycle audits), CMP read in full, host facts, the R570 rules, Q1's kernel results | Host checked read-only on 2026-10-14 |
| Discovery, memory | AGENT-MEMORY scout | AM1-AM7 | 71 listed queries: 66 alphaXiv keyword or embedding, 2 OpenAlex, 3 web lookups. About 60 abstracts or reports read; full-text greps of about 15 papers |
| Discovery, GPU | GPU scout | G1-G6 | 29 alphaXiv keyword or embedding, 3 OpenAlex; 21 full-text reads; 7 report reads. GitHub reads of vLLM v0.31.0 and verl; read-only reads of the host's model configs |
| Verification | Fresh verifier | One verdict per candidate, with corrected questions for the NARROWED ones. 5 STILL_OPEN (AM3, AM4, G1, G2, G5); 4 NARROWED (AM1, AM2, AM6, G4); 4 OCCUPIED (AM5, AM7, G3, G6) | 96 orx queries, 26 OpenReview queries, GitHub issue and PR reads, the HF API, a read-only listing of the host's model directory |
| Judging | Three independent judges | 27 score vectors with reasons (9 candidates x 3) | J1 reported its own keyword and embedding searches after 2026-06-01 (found 2610.15642, 2610.07767 and 2609.20807). J3 reported read-only host checks |
| Dossier | Dossier owner (this file) | Ranking, entries, recommendation | 10 title resolutions; 9 discover queries; 2 report reads; vLLM GitHub reads; 2 read-only host commands; 9 owner checks |

### Differences from the 2026-10-11 method

- **No merge step and no claim registry.** The renewal had a slate owner who
  merged candidates, and a numbered claim registry. This sweep had neither:
  the scouts' candidates went straight to the verifier. The verifier gave one
  verdict per candidate, with evidence and corrected questions. So there is
  no claim-level tally like the renewal's 192 VERIFIED, 4 CORRECTED and 6
  UNVERIFIABLE.
- **Occupied candidates were not scored.** The judges scored only the nine
  candidates that were not OCCUPIED. The four occupied ones are listed after
  the ranking, each with what of it survives.
- **Unchanged.** The gates, the ordering rule and the meaning of the
  dispositions are the renewal's.

### Dossier owner's retrieval (2026-10-14, orx 0.2.2)

Title resolutions with `orx paper <id>`. All ten resolve:

1. 2610.15642, "Recall What Is Missing: Composing Evidence from Long-Term
   Agent Memory" (MemPursuit; raised by J1).
2. 2610.07767, "TRACE: Rollout-Guided Quantization-Aware Training for FP4
   Reinforcement Learning of MoE Language Models", dated 2026-10-12 (raised
   by J1).
3. 2609.20807, "Score Centering Stabilizes Off-Policy Reinforcement Learning"
   (raised by J1).
4. 2507.04480, "Source Attribution in Retrieval-Augmented Generation"
   (Nematov et al.).
5. 2608.17781, "Preference Is Not Intervention: The Structure and Stability
   Boundaries of Reader-Specific Evidence Utility".
6. 2606.12370, "Breaking Entropy Bounds: Accelerating RL Training via MTP
   with Rejection Sampling" (Bebop; Qwen Team).
7. 2609.16648, "GrowMTP: Can RL Grow Its Own Draft Head?".
8. 2609.04748, "Same Request, Different Answer: Quantization Amplifies
   Cache-Induced ...". The title is truncated in the extracted text.
9. 2610.05685, "Spend Bytes on Breadth: Precision-Count Trade-offs for
   Decode-Time KV Compression in Long Chain-of-Thought Reasoning" (BreadthKV).
10. 2609.33759, "Positions Are Not Facts: The Mismatch Between KV Caches and
    Memory".

Scoop checks for the two leads and G1, all with `orx discover`:

1. embedding, after 2026-10-01, recency, limit 10: "training-inference
   mismatch between rollout engine and trainer for Gated DeltaNet hybrid
   models; log-probability discrepancy grows with token position; chunked
   versus recurrent kernels".
2. keyword, after 2026-10-01: "Gated DeltaNet training inference mismatch".
3. keyword, after 2026-09-15: "Qwen3.5 rollout logprob mismatch
   reinforcement learning".
4. keyword, after 2026-09-15: "linear attention recurrent chunked numerical
   mismatch position".
5. embedding, after 2026-10-01: "exhaustive evaluation of all subsets of
   agent memories to obtain exact interaction effects and benchmark
   per-memory credit estimators".
6. keyword, after 2026-09-15: "exact Shapley all subsets retrieved memories
   agent".
7. keyword, after 2026-09-15: "Mobius interaction memory retrieval agent
   credit".
8. embedding, after 2026-10-01: "KV cache quantization versus recurrent state
   precision as levers for RL rollout throughput of hybrid linear attention
   models".
9. embedding, after 2026-10-01: "recurrent state quantization linear
   attention scale feedback low-bit updates" (an id lookup).

Result: no title in these results occupies G2 or AM1. The adjacent papers,
with what each covers:

| Paper | Read at | What it covers |
|---|---|---|
| [2610.05458](https://arxiv.org/abs/2610.05458), cross-vendor mismatch | Report | Two dense and two MoE models; no hybrid model, no position analysis |
| [2610.07043](https://arxiv.org/abs/2610.07043), TRIAGE | Report | NVFP4 RL mismatch stabilization |
| [2610.15755](https://arxiv.org/abs/2610.15755) | Title | vLLM hybrid memory organization for serving |
| [2610.15709](https://arxiv.org/abs/2610.15709) | Title | Low-bit recurrent-state quantization |
| [2610.10179](https://arxiv.org/abs/2610.10179) | Title | Retrieval credit for search agents |

### Owner checks for this dossier

Each check either confirms a judge finding that changes an entry or adds a
fact that no earlier step had.

- **O1. Host model inventory (read-only, 2026-10-14 19:58Z).** Safetensors
  were counted per directory under the persistent HF cache.
  - Weights present: qwen3-0.6b-base, qwen3-1.7b-base, qwen3-32b (17 shards,
    62 GB), qwen3.5-4b, qwen3.5-4b-base, qwen3.5-9b, qwen3.6-35b-a3b (67 GB),
    opencua-7b and the FLA research checkpoints.
  - Metadata only (0 safetensors): qwen3-8b, qwen3.5-27b-fp8 and
    qwen3.5-35b-a3b-fp8.
  - Qwen3-32B was fetched today under D1 for inference-baseline-v1, at
    revision `9216db57`, Apache-2.0. Its registry entry is on branch
    `stage0/inference-baseline`, not on main.
  - This confirms the verifier on Qwen3-8B and on the 27B judge. It confirms
    J3 on Qwen3-32B, which the verifier's listing omitted. It corrects the
    brief, which listed qwen3.5-35b-a3b-fp8 as present.
- **O2. The node is busy now; the brief's "queue empty, all 8 GPUs idle" is
  stale.**
  - At 19:58Z there were six Slurm jobs: 1314 and 1320-1323 running, 1324
    pending (4 GPUs). Seven of eight GPUs held 73,427-76,411 MiB.
  - All six belong to `inference-baseline-v1`
    (`experiments/serving/inference-baseline-v1.yaml` on
    `stage0/inference-baseline` at `f6eaf1b2`). It is an exploratory,
    unregistered vLLM 0.31.0 baseline.
  - It measures fixed-length (ignore_eos) serving and offline cells for six
    models, with prefix caching on and off. It also has FP8-KV arms for
    Qwen3.5-9B and Qwen3-32B.
  - Those cells overlap G1's fixed-length throughput arms, and G1 should read
    them before repeating any.
- **O3. Upstream vLLM state (`gh api`, 2026-10-14).**

  | Issue or PR | What it says | State |
  |---|---|---|
  | [#48613](https://github.com/vllm-project/vllm/issues/48613) | GDN_ATTN has no batch-invariant mode for Qwen3.5/3.6 | Open, since 2026-07-14 |
  | [#45819](https://github.com/vllm-project/vllm/pull/45819) | Fix PR for GDN batch invariance | WIP, open |
  | [#55868](https://github.com/vllm-project/vllm/pull/55868) | Fix PR for GDN batch-invariant prefix caching | WIP, open |
  | [#60033](https://github.com/vllm-project/vllm/pull/60033) | Fix PR sharing recurrent arithmetic for GDN batch invariance | WIP, open |
  | [#53086](https://github.com/vllm-project/vllm/issues/53086) | int4 per-token-head KV writes wrong values | Open, since 2026-08-20 |
  | [#48721](https://github.com/vllm-project/vllm/issues/48721) | int4 per-token-head crashes with SWA models | Open |

  The v0.31.0 tag was also read directly:
  - `vllm/v1/attention/backends/gdn_attn.py` contains no batch-invariance
    hook.
  - `docs/features/batch_invariance.md` calls the feature beta. It lists
    dense Qwen3-1.7B and Qwen3-8B as tested and names Hopper among the
    tuned devices. Qwen3-32B is not on the list; Qwen2.5-32B is.

  Consequences:
  - G2's H2c arm and G6's hybrid half cannot run on the stock image.
  - AM1's Qwen3-8B reader is on the tested list.
  - G1's INT4 arm needs a correctness check before any timing.
- **O4. R01's batch-invariant arm could not have run as drafted.**
  - R01's P0' (`program/preregistrations/r01-rerun-noise-sources-v1.md`,
    section 10.1) adds `VLLM_BATCH_INVARIANT=1` to an engine serving
    Qwen3.5-4B on vLLM v0.31.0 (lines 14 and 344).
  - Per O3, that path is unsupported for GDN models on the stock image.
  - So until a GDN batch-invariance fix is merged and reviewed under D29,
    exact paired replay on this node needs a dense reader. This is why
    AM1, AM2, AM4 and AM6 use Qwen3-8B, and why G6's residue is a dense A/A
    gate.
- **O5. Arithmetic behind AM1's hypotheses. It confirms J2 and sharpens
  J1.**
  - Under the uniform measure on subsets (each memory in or out with
    probability 1/2), the Fourier spectrum of an m-way AND of required
    memories has every coefficient equal to 2^-m. The share of variance at
    order 2 or higher is therefore 1 − m/(2^m − 1): 1/3 at m = 2 and 4/7 at
    m = 3.
  - An m-way OR of redundant memories has the same magnitudes. So H1's 30%
    line is crossed by any question with two jointly needed or two redundant
    memories, and H1 is descriptive.
  - In the 0/1 Möbius basis, an AND of two is entirely order 2. The two bases
    give different "order shares", so the registration must name one.
  - Decisions: under a pure AND, leave-one-out (LOO) credits each required
    memory 1 and keeps the right set. Under a pure OR, LOO credits each
    redundant memory 0. Exact Shapley gives 1/m in both pure forms and keeps
    the right set.
  - So H2's regret can only appear with mixed structures, redundancy against
    LOO, a binding budget or negative interference. Pool construction
    decides whether H2 can fire.
- **O6. Capacity arithmetic behind G1. It confirms J2 and extends the point
  to the hybrid.**
  - Qwen3-8B's KV is 36 layers x 8 KV heads x 128 x 2 (K and V) x 2 bytes =
    144 KiB per token. Qwen3.5-9B's is 8 x 4 x 256 x 2 x 2 bytes = 32 KiB.
    The GDN state is 24 x 32 x 128 x 128 x 4 bytes = 48 MiB per sequence.
    All three match the scout.
  - Dense: at 8K tokens per sequence, about 53 GiB of KV on one H100 (80 GiB
    x 0.9, minus 15.3 GiB of weights and about 3 GiB of activations) holds
    about 47 sequences.
  - Hybrid: at 304 MiB per sequence (48 + 256), its 51.2 GiB pool
    (serving-probe v2) holds about 172.
  - So neither model reaches G1's B = 256 at 8K on one GPU, and the ceilings
    in G1's mechanism paragraph describe a regime the first experiment cannot
    enter. The dense model's gains from quantized KV will be capacity-driven.
- **O7. Lane names and the registry.**
  - `scripts/submit_docker_research_job.py` refuses `run_memory_*`,
    `*memory_model*`, `memory_trials` and the archived entry points. Those
    include `prepare_longmemeval_judge_packet`, so AM1's judge step needs a
    new name. AM1's suggested `run_recall_atlas.py` passes.
  - `models/registry.yaml` (lines 188-191) records qwen3-8b as "config and
    tokenizer only", a D5 stand-in for Dr. Kernel-8B, with "No weight
    download is planned".
  - Fetching its weights is allowed under D1, but that note must change in
    the same commit.
- **O8. Every judge- and verifier-raised arXiv id this dossier cites
  resolves**: retrieval items 1-10 above. OpenReview ids are as reported by
  the verifier and were not re-fetched here.
- **O9. Scoop checks** (queries 1-9 above): nothing occupies G2 or AM1
  through 2026-10-14 under these queries.

## Ranked table

Means of the three judges. The "Min" columns hold the lowest judge score,
which is what the gates read. GPU-h is for the first experiment, with
corrections applied.

| Rank | Key | Title | Sig | Corr | Cite | Nov | Feas | Min Corr | Min Cite | Gates | First exp. GPU-h | Owner's disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | G2 | GDN train-inference mismatch by token position | 6.67 | 7.17 | 7.83 | 6.17 | 8.17 | 7 | 7.5 | pass | about 3 (cap 4) | RECOMMEND: overall lead and GPU lead |
| 2 | G1 | Memory levers for hybrid RL rollouts on H100 | 6.00 | 6.33 | 8.00 | 5.17 | 8.00 | 6 | 8 | pass | about 6 (cap 8) | ALTERNATE (GPU); absorbs G4's quantized-KV arms |
| 3 | AM1 | Exact subset tables for agent-memory credit | 6.00 | 7.17 | 8.00 | 4.67 | 7.33 | 7 | 8 | pass | Step 0 about 1; pilot 4-6 per pool arm | RECOMMEND: memory lead; folds AM2 and AM6 |
| 4 | AM4 | Single-write interventions in self-written memory | 5.83 | 5.00 | 7.17 | 5.33 | 4.83 | 5 | 7 | pass | 4-6 (judges expect more) | ALTERNATE (memory), after repairs |
| 5 | AM2 | Placebo share of per-memory deletion credit | 5.00 | 5.83 | 7.17 | 4.17 | 8.17 | 5.5 | 7 | pass | 2-3 | FOLD into AM1 (placebo arms) |
| 6 | AM6 | One-pass signals of memory use vs exact labels | 4.17 | 6.17 | 7.17 | 3.67 | 7.00 | 6 | 7 | pass | 2-4 | FOLD into AM1 (analysis section) |
| 7 | AM3 | Placebo memory in memory-augmented RL | 6.83 | 5.17 | 7.50 | 6.50 | 5.33 | **4.5** | 7 | **fails correctness** | Stage 1 4-6; Stage 2 60-150 | HOLD: repair identification, then re-judge |
| 8 | G4 | Reasoning KV eviction vs quantized-KV baseline | 5.17 | 5.50 | 7.33 | 4.33 | 5.67 | **4.5** | 7 | **fails correctness** | about 6 (cap 8) | FAILS GATE: quantized arms to G1; eviction dropped |
| 9 | G5 | Single-node GRPO step anatomy and async ceiling | 4.50 | 5.17 | 6.67 | 4.00 | 4.33 | **4.5** | 6 | **fails correctness** | Stage 1 about 7 | FAILS GATE: drop as a line |

Not ranked, because the verifier found them OCCUPIED: AM5, AM7, G3 and G6
(section below).

**Ties.** G1 and AM1 tie on mean significance (6.00). G1 ranks first on mean
novelty residual (5.17 against 4.67).

**Agreement.** The judges agree closely:

- The largest spread on any score is 2 points: G1's feasibility, J2 7
  against J3 9.
- Correctness spreads by 1.5 on AM3, G4 and G5.
- All three gate failures come from one judge. J2 gave correctness 4.5 to
  AM3, G4 and G5, where J1 and J3 gave 5-6. That is the gate as set, applied
  without exception.
- AM3 has the highest mean significance on the slate (6.83) and fails the
  gate.

## Recommendation

| Role | Key | Why this one |
|---|---|---|
| Overall lead, GPU lead | G2 | Rank 1, and best on most measures among gate passers: mean significance 6.67, correctness 7.17 (tied with AM1) and feasibility 8.17; lowest scores 6/7/7.5. Every model a first reading needs is on the host. The dense controls are Qwen3-1.7B-Base and Qwen3-32B now, and Qwen3-8B once fetched. It uses only stock libraries (vLLM, torch, FLA, transformers) and executes no model-written code, so it is R570-clean. It is decisive by construction: teacher-forcing identical tokens removes sampling noise, the fp32 reference names the drifting side, and the kill rule names the null |
| Memory lead | AM1 | The only memory candidate in the top three. Lowest correctness 7 and lowest citability 8, the best floors among the memory candidates. All three judges and the verifier place AM2 and AM6 inside it. Its Step 0 settles the one question every exact-replay memory design depends on (O4) |
| GPU alternate | G1 | Rank 2. The most directly actionable for hybrid RL users, and it fills KV4-RL's stated hybrid limitation. Part of its data is being measured today (O2), and it shares G2's images and its rollout-vs-reference mismatch path |

**Why G2 and not AM1 overall.** Kevin asked for questions whose first
experiment gives a real H100 measurement within days.

- G2's first measurement needs no download and no new harness beyond a
  rollout script and a teacher-forcing script on stock libraries.
- AM1 needs one fetch and 2-3 days of harness work before its main pilot.
- G2 also leads on mean significance (6.67 against 6.00) and on novelty
  (6.17 against 4.67). AM1's novelty was narrowed by Nematov et al.
  ([2507.04480](https://arxiv.org/abs/2507.04480), 2025-07-06), who already
  benchmarked LOO and ContextCite against exact Shapley in RAG.

**Why AM1 leads memory although AM3 scores higher on significance.**

- AM3 asks whether memory-augmented RL gains come from memory content, and
  could deflate a 2026 line as Spurious Rewards did for RLVR. All three
  judges rank it the highest-upside memory question.
- Its first experiment does not identify that claim. Stage 1 measures
  learnable-group fraction at inference (a proxy), its shuffled arm on MATH
  keeps generic strategy content, and its experience library is home-built.
  The decisive test is a 60-150 GPU-h RL stage on an image that does not
  exist yet: weeks, not days.
- AM4 passes at the floor (all three judges gave correctness 5), with
  feasibility 4.83. There is also a live risk that Qwen3-8B learns nothing
  from a cheatsheet.

**What would change this.** Two events would change the recommendation:

1. If the Qwen3-8B A/A gate fails under batch invariance after one repair
   (AM1, kill 1), then AM1, AM2, AM4 and AM6 all lose exact replay.
   - Memory work would then need replica-majority designs.
   - A repaired AM3, which needs no exact replay, would become the memory
     candidate.
2. If G2's pilot shows that HF and vLLM differ in non-kernel semantics for
   Qwen3.5 (G2, kill 4), G2 becomes a bug report until the reference is
   fixed. G1 then leads the GPU area.

### What each lead needs before GPU

| | G2 (overall lead) | AM1 (memory lead) | G1 (GPU alternate) |
|---|---|---|---|
| Route | A new direction under D103, so the research gauntlet. D92 admits below 100. D24's 8 GPU-h line is not engaged (cap 4). Without an executable pilot a package scores at most 79, so a small pilot comes first: 16 rollouts per model through R1 and R5 only, about 0.3-0.5 GPU-h, as an orx `slurm-manifest` node | Gauntlet, as for G2. The Step 0 A/A gate (about 1 GPU-h) is the natural executable pilot. With AM2's and AM6's arms folded in, the full study is about 9-14 GPU-h and over D24's line. Admit Step 0 and the 200-question pilot first, then the folded arms | Gauntlet, as for G2. Under 8 GPU-h (cap 8). The executable pilot is the INT4/INT8 correctness check plus one fixed-length cell, which also reads inference-baseline-v1's cells |
| Models and data | On the host: Qwen3.5-4B, 4B-Base and 9B; Qwen3-1.7B-Base; Qwen3-32B. Qwen3-8B, the size-matched dense control, after the fetch. DAPO-Math-17K: record source, revision, licence and SHA-256 under D1 | Fetch Qwen3-8B under D1 (Apache-2.0; the verifier read revision `b968826d`; about 16 GB) and update the registry note (O7). LongMemEval-S cleaned (MIT, HF sha `98d7416c`). Judge with Qwen3.6-35B-A3B (on the host), or fetch Qwen3.5-27B-FP8 | On the host: Qwen3.5-9B and 4B. Dense control: Qwen3-8B after the fetch, otherwise Qwen3-1.7B-Base |
| Kevin's rulings | Admission only | Admission only. The fetch is within D1 | Admission only |
| Design repairs | (a) Drop H2c's batch-invariant arm on the stock image and record the refusal (O3). (b) Condition the position slope on token entropy (J2, J3). (c) A common-text arm (owner addition, for J2's point): teacher-force one fixed set of reference solutions through every model. (d) Force flash or memory-efficient SDPA in HF (D42, D44). (e) Use vLLM `logprobs_mode` raw | (a) Name the basis. H1 is descriptive, against the AND/OR baseline (O5). (b) Make H2, keep-set regret, the headline. (c) Two pool arms: the retriever's real top-8, and a gold-augmented pool. Report each question's interaction structure. (d) Fold in AM2's placebo arms and AM6's internal-signal analysis. (e) New entry-point names (O7). (f) Cite Nematov, DRSR, MemAttr, MemPO and MemPursuit | (a) Bandwidth comparisons at a concurrency both models fit; capacity reported separately (O6). (b) Fixed-length throughput arms (J2). (c) A decode-path mismatch reference, shared with G2. (d) An INT4 correctness check before timing (#53086). (e) Cite Forgetting to Forget and TRACE |
| Engineering | About a day: a rollout script and a five-path teacher-forcing script, both on stock libraries | 2-3 days: the subset enumerator, the batch-invariant serving client, judge caching and the estimator suite | About a day, reusing `run_vllm_throughput_probe_v2` and inference-baseline-v1's driver |

### Sequencing

D103 says everything runs one agent at a time on Kevin's Mac. Host jobs
follow queue order.

1. Now. inference-baseline-v1 finishes; it is running (O2). Fetch the
   Qwen3-8B weights on the GPU-less fetch lane used today for Qwen3-32B.
2. G2: proposal, gauntlet wave with its executable pilot, then the 3 GPU-h
   run on admission.
3. AM1: harness, then the Step 0 A/A gate as its executable pilot, then the
   gauntlet and the 200-question pilot.
4. G1, if Kevin wants a second GPU line, after inference-baseline-v1's cells
   are read.

The two leads' first experiments total about 3 + 1 + 4-6 GPU-h. None is over
8 GPU-h alone.

## Not ranked: occupied by prior work

The verifier found these four occupied in its queries. The judges did not
score them.

| Key | Question, short | Occupied by | What survives | Disposition |
|---|---|---|---|---|
| AM5 | Do per-memory causal effects transfer across reader models? | [2608.17781](https://arxiv.org/abs/2608.17781), "Preference Is Not Intervention" (2026-08-18). Nine readers, including Qwen3.5-9B, scored closed-book, full and leave-one-out on NQ/HotpotQA. Effect signs disagree in 33% of jointly affected cells. A pre-registered 9x9 transfer test finds that help/harm decisions do not transfer (oracle-distance rho −0.27). Also [2606.32008](https://arxiv.org/abs/2606.32008) (2026-06-30) and [2609.05339](https://arxiv.org/abs/2609.05339) (2026-09-04; writer swaps −13.28 / +9.91 pp) | LongMemEval units under exact replay: at most a second-reader axis inside AM1, with Qwen3-32B. The hybrid readers cannot run batch-invariant on stock v0.31.0 (O3) | DROP |
| AM7 | Append-only vs in-place memory edits: stale answers against prefix-cache savings | [2609.33759](https://arxiv.org/abs/2609.33759), "Positions Are Not Facts" (2026-09-27). It compares keep-all, mask and delete-and-recompute across 8 models, including Qwen3-8B, on MQuAKE, FactConsolidation and LongMemEval-Oracle, with runtime and KV cost on H200 (App. D.7). Also [2608.30647](https://arxiv.org/abs/2608.30647) (2026-08-31; corrections served beside memory are ignored depending on phrasing), [2609.38866](https://arxiv.org/abs/2609.38866) (2026-09-30) and PrefixBench-H100 [2609.19657](https://arxiv.org/abs/2609.19657) (2026-09-17) | Serving-level GPU-time accounting at given update rates, which is a calculation, not a question | DROP |
| G3 | Native MTP speculative decoding in hybrid RL rollouts: batch crossover and frozen-head drift | Bebop [2606.12370](https://arxiv.org/abs/2606.12370) (2026-06-10, Qwen Team): the frozen MTP head of Qwen3.5/3.6/3.7 used during RL; acceptance falls linearly with entropy; mismatch from policy updates is negligible, which answers H3c. GrowMTP [2609.16648](https://arxiv.org/abs/2609.16648) (2026-09-15): Qwen3.5-4B-Base native MTP (K = 3) in GRPO on one 8xH800 node; frozen-head tau 2.65 on math and 2.59 on code; online training 1.36x rollout over frozen. vLLM #60033 says speculative decoding is unsupported under GDN batch invariance | An H100 batch-size crossover (B*): at most one row of G1's lever ledger | DROP |
| G6 | Bit-exact agent trajectories under batch-invariant serving, dense and hybrid | Hybrid half: [#48613](https://github.com/vllm-project/vllm/issues/48613) and WIP PRs #45819, #55868 and [#60033](https://github.com/vllm-project/vllm/pull/60033). Per the verifier, #60033's H100 test shows identical Qwen3.5-0.8B/4B logit hashes with prefix caching on and off. Dense half: Vosti [2609.38981](https://arxiv.org/abs/2609.38981) (2026-09-30; batch-invariant backends match prefix-reuse pairs on Llama3.1-8B, not on Gemma3-4B); [2609.04748](https://arxiv.org/abs/2609.04748) (2026-09-04; prefix caching changes 36.2% of 80 multi-turn agent episodes at 16-bit, 0 of 800 with the cache off); CoRun [2608.14376](https://arxiv.org/abs/2608.14376) (2026-08-14; batch-invariant kernels cost up to 74% of throughput) | The node-specific dense A/A gate, which becomes AM1's Step 0. The hybrid result is the recorded refusal on stock v0.31.0 (O3, O4) | DROP as a question |

---

## Entries

The nine judged candidates, in rank order. Each entry gives the corrected
question, the verifier's verdict, the priors and deltas, the scores, the
first experiment and its GPU-h, the kill criteria, and the corrections that
now apply.

### 1. G2: GDN train-inference mismatch by token position

`G2-gdn-train-inference-mismatch`. GPU area. Verifier: **STILL_OPEN**.
**Owner's disposition: RECOMMEND as overall lead and GPU-area lead.**

Scores: Sig 6.67, Corr 7.17, Cite 7.83, Nov 6.17, Feas 8.17. J1 7/7/8/6/8, J2
6/7.5/7.5/6/7.5, J3 7/7/8/6.5/9. Lowest Corr 7, lowest Cite 7.5. Passes both
gates.

**Question, as corrected.** The verifier left the scout's question open. For
the GDN hybrids Qwen3.5-4B and 9B, compare two forward passes on identical
token sequences:

- vLLM rollout: fused recurrent GDN decode with fp32 state, CUDA graphs and
  FlashInfer or FA attention;
- a verl-style trainer forward: HF transformers plus FLA
  `chunk_gated_delta_rule` over packed `cu_seqlens`.

The questions:

- How large is the per-token log-prob mismatch between the two?
- Does it grow with token position across 16K-token reasoning traces, while
  dense controls measured the same way stay flat?
- Which component causes it: the GDN recurrent vs chunked form, the attention
  backend, or LM-head precision?
- What does removing it cost in throughput?

The hypotheses:

- H2a: hybrid mismatch has a positive slope over 1K-position bins; dense is
  flat.
- H2b: above 4K, swapping the trainer's GDN kernel from chunk to
  `fused_recurrent` removes at least half of the hybrid's excess.
- H2c (the batch-invariant arm) cannot run on the stock image (O3) and is
  dropped from the first experiment.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| VeXact | [2605.14220](https://arxiv.org/abs/2605.14220), 2026-05-14 | A zero-mismatch reference engine for dense Qwen3-1.7B and MoE Qwen3-30B-A3B. No hybrid model, no position-resolved growth, no recurrent-vs-chunk attribution |
| CIS | [2609.32444](https://arxiv.org/abs/2609.32444), 2026-09-26 | Models mismatch as a logit displacement on three MoE attention models and proposes a correction. No hybrid attribution |
| Ring-linear | [2510.19338](https://arxiv.org/abs/2510.19338), 2025-10-22 | The closest hybrid prior: module-by-module alignment with qualitative figures for Ling hybrids on an internal stack. Not Qwen3.5 GDN in vLLM against FLA, and not by position |
| MiniMax-M1 | [2506.13585](https://arxiv.org/abs/2506.13585), 2025-06-16 | An FP32 LM-head fix for lightning attention. A different linear form, one fix, no position analysis |
| FP16 | [2510.26788](https://arxiv.org/abs/2510.26788), 2025-10-30 | Dense models; switching BF16 to FP16 reduces mismatch. G2 can carry an FP16 arm |
| miles PR #3597 | [github.com/radixark/miles/pull/3597](https://github.com/radixark/miles/pull/3597), opened 2026-09-22, open | Qwen3.5-4B GRPO on 4xB200, aggregates only: `train_rollout_logprob_abs_diff` 0.0072-0.0096 and KL about 3.6e-4. Its deterministic kernels are generated CUDA for SM100, excluded here. No position, dense control or attribution |
| Miles v0.1 | [2609.08368](https://arxiv.org/abs/2609.08368), 2026-09-08 | True on-policy (zero difference) only for dense Qwen3 0.6B and 4B |
| verl `qwen3_5.py` | [verl-project/verl](https://github.com/verl-project/verl/blob/main/verl/models/transformers/qwen3_5.py), read 2026-10-14 (verl v0.9.1, 2026-09-20) | Confirms that the standard trainer path calls FLA `chunk_gated_delta_rule` with `cu_seqlens` |
| vLLM PR #60033 | [vllm-project/vllm#60033](https://github.com/vllm-project/vllm/pull/60033), opened 2026-10-05 | States that Qwen GDN's chunked prefill and recurrent decode are not float-identical. A qualitative acknowledgment with no mismatch measurement |
| Score Centering (J1) | [2609.20807](https://arxiv.org/abs/2609.20807) | A correction method for off-policy RL, not an attribution |
| Owner scoop check | [2610.05458](https://arxiv.org/abs/2610.05458); [2610.07043](https://arxiv.org/abs/2610.07043) | Cross-vendor mismatch on dense and MoE models; NVFP4 RL mismatch. Neither is hybrid or position-resolved |

**What the judges agreed on.**

- It is the cleanest GPU design. Teacher-forcing identical tokens through
  five paths, with an fp32 reference, identifies which side drifts. The
  chunk-vs-recurrent swap isolates the kernel. The semantic-bug kill rule is
  right (J2).
- It is cheap, uses stock libraries, and either outcome is reportable (J1,
  J3).

**Defects:**

1. The batch-invariant arm is not runnable for Qwen3.5 on stock v0.31.0 (all
   three; O3).
2. A position trend may track per-position entropy, that is, the reasoning
   phase (J2, J3).
3. Dense and hybrid teacher-force different sequences (J2).
4. Scoop risk from the miles and slime communities' GDN determinism work (J1,
   J3).

**Corrections that apply.**

- Drop H2c on the stock image and record the refusal. A build of PR #60033
  reviewed under D29 is a later option, not part of this experiment.
- Report the slope within entropy bins (reference-distribution entropy) and
  in a regression with entropy as a covariate.
- Add a common-text arm (owner addition): teacher-force one fixed set of
  reference solutions, tokenized by each model, through every model's paths.
  The dense-vs-hybrid contrast then also holds on the same text.
- Dense controls:
  - Qwen3-1.7B-Base, on the host now;
  - Qwen3-8B, size-matched to the 9B, after the fetch;
  - Qwen3-32B, on the host (O1), as an extra dense point.

  Kill criterion 1 names Qwen3-8B. Until it is fetched, say which control a
  reading used.

**First experiment.**

- Images: the vLLM 0.31.0 overlay for rollout; the research image (torch
  2.11, FLA 0.5.2, transformers 5.15) for teacher forcing. Both are stock.
- Rollouts: 256 per model (64 DAPO-Math prompts x 4, T = 1.0, at most 16K
  tokens), recording raw sampled-token logprobs.
- Teacher forcing through five paths:
  - R1: HF+FLA chunk, BF16, packed;
  - R2: the same, unpacked;
  - R3: HF with FLA `fused_recurrent` for GDN;
  - R4: an fp32 torch-native reference, chunked over positions;
  - R5: vLLM prefill recompute via `prompt_logprobs`.
- Rollout-side arms: `mamba_ssm_cache_dtype` bfloat16, and FP16.
- Metrics per 1K-position bin:
  - mean and p99 |Δ log p|;
  - k3-KL;
  - the share of ratios outside [0.8, 1.25];
  - the position slope, with a bootstrap CI over sequences (seeds 42, 43,
    44).
- Diagnostics:
  - per-layer hidden-state relative error on 8 sequences;
  - the throughput cost of each fix at batch 64 and 256.

**GPU-h.** About 3 in all: about 0.5 for generation, about 1.5 for teacher
forcing including the fp32 reference, and about 1 for the remaining arms.
Cap 4.

**Kill criteria** (the scout's, unchanged):

1. If the hybrid's mean and p99 |Δ log p| stay within 1.5x of dense Qwen3-8B
   in every 1K bin, and the slope's 95% CI includes 0: publish a null note.
2. Drop the H2b attribution if R1 against R3 explains less than 25% of the
   hybrid's excess at every position.
3. Reframe, rather than kill, if R4 shows the trainer is the noisy side.
4. Stop and fix the reference first if HF and vLLM differ in non-kernel
   semantics (gated-attention norm, partial RoPE, MTP). A semantic mismatch
   is a bug, not training-inference mismatch.

**What it gives within days, and why it matters.** It gives one figure and
one table:

- the figure: mismatch against position, hybrid against dense;
- the table: which kernel or path accounts for the excess.

That is the input every long-CoT RL run on Qwen3.5-class models needs, and
that no prior found provides.

### 2. G1: memory levers for hybrid RL rollouts on H100

`G1-hybrid-rollout-memory-levers`. GPU area. Verifier: **STILL_OPEN**.
**Owner's disposition: ALTERNATE (GPU area); absorbs G4's quantized-KV
arms.**

Scores: Sig 6.00, Corr 6.33, Cite 8.00, Nov 5.17, Feas 8.00. J1 6/6/8/5/8, J2
5.5/6/8/5/7, J3 6.5/7/8/5.5/9. Lowest Corr 6, lowest Cite 8. Passes both
gates.

**Question.** In GRPO-style rollouts of GDN hybrids (Qwen3.5-9B and 4B) on
H100:

- Where do per-step HBM bytes and resident memory go? The candidates are the
  weights, the 48 MiB fp32 recurrent state per sequence, and KV at 32 KiB per
  token.
- Which stock vLLM 0.31 lever raises rollout throughput? The levers are:
  - `kv_cache_dtype` fp8, `int8_per_token_head` or `int4_per_token_head`;
  - `mamba_ssm_cache_dtype` bfloat16;
  - FP8 weights.
- Under which schedule (synchronous waves, or asynchronous fixed
  concurrency), and at what cost in rollout-vs-reference mismatch?
- Does KV4-RL's ranking of these levers transfer from dense Qwen3 to
  hybrids?

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| KV4-RL | [2610.14448](https://arxiv.org/abs/2610.14448), 2026-10-10 | Dense Qwen3-4B/8B-Base on 4xH200: INT4 KV gives 1.80x cumulative rollout and 1.27x iteration speedup. Lists validation on hybrids as a limitation. No recurrent-state term |
| SketchSSM | [2609.33051](https://arxiv.org/abs/2609.33051), 2026-09-27 | Shows state access bottlenecks large-batch hybrid decode; custom kernels on B300; serving only |
| ReplaySSM | [2610.13778](https://arxiv.org/abs/2610.13778), 2026-10-09 | Halves state traffic, 1.20-1.47x decode at batch 256; custom kernels; serving workloads |
| DeltaLog | [2608.15533](https://arxiv.org/abs/2608.15533), 2026-08-16 | Up to 7.83x less state write traffic for 1.05-1.20x end to end; bounds the state's end-to-end share in serving |
| Ring-linear | [2510.19338](https://arxiv.org/abs/2510.19338), 2025-10-22 | BF16 linear-attention state destabilizes RL (qualitative); no throughput figure |
| STEPQuant, LeapQuant, DAMP | [2609.38169](https://arxiv.org/abs/2609.38169), [2609.38166](https://arxiv.org/abs/2609.38166), [2608.27513](https://arxiv.org/abs/2608.27513) | State quantizers measured on serving accuracy and memory, not RL rollouts |
| Native Dual Pools or Shared Paging? | [2610.15755](https://arxiv.org/abs/2610.15755), 2026-10-11 | vLLM hybrid memory organization for concurrent serving |
| Forgetting to Forget | OpenReview [9LUInzhKZc](https://openreview.net/forum?id=9LUInzhKZc), 2026-09-18 | Partly covers H1c. A bf16 round-to-nearest GDN state on Qwen3.5-0.8B; fp32 on selected heads removes 75.4% of the excess NLL; Qwen3.5-4B generation lengths change |
| TRACE (J1) | [2610.07767](https://arxiv.org/abs/2610.07767), 2026-10-12 | FP4 rollouts for MoE RL; not hybrid |
| verl fully_async | [docs](https://github.com/verl-project/verl/blob/main/docs/advance/fully_async.md), accessed 2026-10-14 | 1.72-2.67x for dense Qwen2.5-Math-7B on 32-128 H20 GPUs; no lever breakdown |

**What the judges agreed on.** It is directly actionable for hybrid RL users
and gives real H100 numbers in a day or two on stock flags. J3 re-derived the
byte arithmetic, and O6 re-derives it again.

**Defects:**

1. The dense B = 256 / 8K ceilings are unreachable on one GPU (J2). O6 shows
   the hybrid does not fit either.
2. Quantized arms change generated length at T = 1, so throughput needs
   fixed-length arms (J2).
3. Mismatch scored through `prompt_logprobs` mixes prefill-vs-decode kernel
   differences with dtype effects (J2).
4. The INT4 bug #53086 is open (all three; O3).
5. Bytes are modeled, not counted, because ncu is blocked.
6. H1c is partly covered by "Forgetting to Forget", and the space is
   crowded.

**Corrections that apply.**

- Run the bandwidth comparison at a concurrency both models fit at the stated
  context (at 8K, at most about 40 on one H100 for the dense control), and
  report capacity, the maximum resident sequences, as a separate result (O6).
- Measure throughput on fixed-length (ignore_eos) arms. Use sampled-length
  arms only for length distributions and mismatch.
- Read inference-baseline-v1's FP8-KV cells first (O2) and do not repeat
  them.
- Score mismatch against a decode-path reference, or subtract G2's
  R5-vs-decode term; G1 and G2 share these runs.
- Check `reshape_and_cache` element by element against BF16 on the host
  image before timing the INT4 and INT8 per-token-head arms. Drop an arm on
  any mismatch.
- Dense control: Qwen3-8B after the fetch, otherwise Qwen3-1.7B-Base.

**First experiment.**

- Setup: the vLLM 0.31.0 overlay, one offline engine per GPU, 8 arms in
  parallel. Prompts: 512 DAPO-Math prompts, n = 8, T = 1.0.
- Schedules:
  - a synchronous wave, logging the active batch per step;
  - quota-based refill at a fixed concurrency both models fit.
- Arms: `kv_cache_dtype` auto, fp8, int8 or int4 per-token-head; for the
  hybrid, `mamba_ssm_cache_dtype` float32 or bfloat16.
- Logs:
  - vLLM engine stats per step;
  - NVML at 1 Hz;
  - torch.profiler over a 200-step slice per arm (attention, GDN, GEMM,
    other).
- Analysis: modeled bytes per second against 3.35 TB/s.
- Mismatch: 64 sequences per arm re-scored against the reference
  configuration, in 1K-position bins.

**GPU-h.** About 6, cap 8.

**Kill criteria** (the scout's):

1. Kill "hybrids reorder the levers" if two things both hold:
   - the hybrid's FP8 or INT4 relative speedup is at least 0.8x the dense
     model's at matched context in both schedules;
   - BF16 state gives under 5% in every context bin.

   Then write a short transfer-confirmation note.
2. Stop and debug if the same-arm repeat spread exceeds 5%.
3. Drop any KV dtype that is unsupported or falls back to a slower backend.
4. Pivot to a "where the gap goes" profile alone if every arm reaches under
   half the modeled roofline.

### 3. AM1: exact subset tables for agent-memory credit

`AM1`. Memory area. Verifier: **NARROWED**. **Owner's disposition:
RECOMMEND as memory-area lead; AM2's and AM6's arms fold in.**

Scores: Sig 6.00, Corr 7.17, Cite 8.00, Nov 4.67, Feas 7.33. J1 6/7/8/5/7, J2
6/7.5/8/4.5/7, J3 6/7/8/4.5/8. Lowest Corr 7, lowest Cite 8. Passes both
gates.

**Question, as corrected (verifier).** The study extends Nematov et al.'s
exact-Shapley RAG benchmark (10 documents, log-prob utility) to agent memory.
On LongMemEval-S, it uses a bit-exact open reader and scores generated
answers over pools of k = 8 memories. It asks two things:

- (a) What share of the exact set function's variance lies in terms of order
  2 or higher?
- (b) How often do the per-memory credits used by 2026 memory learners choose
  a worse B-of-k keep set than the exact optimum? The credits are:
  - one-shot deletion (Hindsight-PRM);
  - permutation Shapley (MeClear);
  - CMP's SNIPW;
  - Shapley over the visible set or over the retrieved set (MemAttr, MemPO).

The owner's correction (O5) adds two requirements. Part (a) must name its
basis and is descriptive against the AND/OR baseline. Part (b) is the
headline.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| CMP | [2610.02070](https://arxiv.org/abs/2610.02070), 2026-10-01 (v3 2026-10-08) | Known-propensity exposure with SNIPW; gemini-3.7-flash at T = 0 ($193.06 over 80,187 calls); an oracle pool; interactions shown descriptively (Sec 4.1: about 0.2 correctness until every required memory is present, then 0.73). AM1 computes exhaustive exact outcomes with an open deterministic reader and scores SNIPW against them |
| Nematov et al., "Source Attribution in RAG" | [2507.04480](https://arxiv.org/abs/2507.04480), 2025-07-06 (ECML-PKDD 2025) | 100 queries x 10 documents with exact Shapley as reference. LOO, TMC-, Beta- and KernelSHAP, and ContextCite compared; the most harmful k-removal set found exhaustively; synthetic redundancy, complementarity and synergy; log-prob utility. AM1 uses agent-memory units, generated-answer utility, an interaction spectrum, SNIPW, and keep/evict decisions |
| UpliftMem | [2609.36805](https://arxiv.org/abs/2609.36805), 2026-09-29 | Learns set-level uplift from EVSI-sampled probes (Qwen3-4B/8B executors; ALFWorld, WebShop, BCB), never from exhaustive truth |
| MeClear | [2609.09115](https://arxiv.org/abs/2609.09115), 2026-09-08 | Permutation Shapley (L = 16) against LOO, ContextCite and ProxySPEX on 745 synthetic cases; Kimi-k2.6 agent |
| Hindsight Memory-PRM | [2608.29605](https://arxiv.org/abs/2608.29605), 2026-08-30 | Per-entry credit from one deletion-and-reanswer (DeepSeek-V4-Flash auxiliary at T = 0; Qwen3-8B LoRA policy) |
| SPEX | [2502.13870](https://arxiv.org/abs/2502.13870), 2025-02-19 | Sparse Fourier interactions over sentences; R^2 on random masks |
| DRSR | [2609.27276](https://arxiv.org/abs/2609.27276), 2026-09-23 | Exact joint-deletion supervision, because singleton scores do not decide set deletions |
| MemAttr | OpenReview [g57t6h0f3Q](https://openreview.net/forum?id=g57t6h0f3Q), 2026-09-14 | Shapley on visible memories against measured leave-one-in utility |
| MemPO | OpenReview [zJgGRuawjw](https://openreview.net/forum?id=zJgGRuawjw), 2026-09-10 | Shapley over the retrieved set as memory-write credit |
| MemPursuit (J1) | [2610.15642](https://arxiv.org/abs/2610.15642) | "Recall What Is Missing": evidence for set-level selection over long-term memory |

**What the judges agreed on.**

- It is the best-identified memory design. Under a batch-invariant greedy
  reader every u(S) in the pool is observed exactly, so there is no IPW and
  no positivity problem inside the pool. The A/A gate and the
  question-clustered CIs are right (J2).
- The exact tables are reusable ground truth (J1, J3).

**Defects:**

1. H1 is near-tautological for multi-gold questions (J1, J2; O5).
2. H2 may not fire: LOO is exact-optimal under a pure AND, and Shapley under
   both pure forms (J2; O5).
3. Nematov et al. narrow the novelty. What remains is agent-memory units,
   generated-answer utility, the interaction spectrum, SNIPW against the
   truth, and keep/evict decisions (all three).
4. Qwen3-8B and the 27B judge have no weights on the host (O1). Batch
   invariance in the host image is untested, though Qwen3-8B is on vLLM's
   tested list (O3).

**Corrections that apply.**

- Basis and hypotheses:
  - Variance shares by order come from the uniform-measure Fourier spectrum.
  - Möbius dividends are reported separately.
  - For each question, register the AND/OR baseline 1 − m/(2^m − 1) given its
    count of required memories.
  - H1 is descriptive. H2, the keep-set regret at B = 4 against the exact
    optimum, is the headline.
- Two pool arms:
  - (a) the retriever's real top-8 (MiniLM), which answers the deployable
    question;
  - (b) a gold-augmented pool (gold turns plus distractors, CMP-style), which
    answers the identification question.

  Report the distribution of required-memory counts and a census of
  interaction structure (AND, OR, mixed, negative). CMP found 54% of required
  memories never retrieved on LongMemEval, so arm (a) will often contain
  none, and that share is itself a result.
- Reader and judge:
  - Reader: Qwen3-8B after the D1 fetch. The fallback is Qwen3-32B (on the
    host). It is dense Qwen3 but not on the tested list, so it gets its own
    A/A gate.
  - Judge: Qwen3.6-35B-A3B (on the host), or Qwen3.5-27B-FP8 after a fetch.
    Verdicts are cached per distinct answer string, and normalized exact
    match is reported alongside.
- Folded arms:
  - AM2's placebo arms: a length- and rank-matched irrelevant swap, a
    paraphrase, a reorder.
  - AM6's internal-signal analysis: retrieval-head mass, AT2-style learned
    head weights and a cross-fitted probe, against rank, lexical-overlap and
    length baselines.
- Engineering: new entry-point names (O7).

**First experiment.**

- Reader: Qwen3-8B, non-thinking, greedy, in the vLLM 0.31.0 overlay with
  `VLLM_BATCH_INVARIANT=1` and prefix caching on.
- Step 0, the A/A gate: 1,000 prompts x 3 replicas with shuffled batch
  composition. Zero differing replies are required. It also measures the
  batch-invariant throughput cost.
- Step 1, exhaustive evaluation:
  - 200 LongMemEval-S cleaned questions, stratified by type;
  - all 256 subsets per question and pool arm, which is 51,200 requests per
    arm;
  - questions with more than 6 gold turns dropped, and the count reported.
- Estimators, each scored at matched call budgets on the same truth tables:
  - LOO (9 calls);
  - Shapley with 16 and 64 permutations;
  - SNIPW with 64 random exposures;
  - RBC-style blocks;
  - attention mass.
- Statistics: seeds 42, 43, 44 for pool sampling and the stochastic
  estimators; question-clustered bootstrap CIs.

**GPU-h.**

- Step 0: about 1.
- Step 1: about 4-6 per pool arm at the scout's assumed 3 requests/s/GPU,
  which comes from 8K-token prompts. These prompts are shorter, so Step 0's
  measured rate decides whether both arms fit in one admitted step. If they
  do not, run 100 questions per arm.
- Folded arms: AM2's add 2-3 and AM6's add 2-4. The whole folded study is
  about 9-14, over D24's line, so it is admitted in two steps.

**Kill criteria** (the scout's):

1. Stop the exact design if the batch-invariant A/A gate still shows any
   differing reply after one configuration repair.
2. Drop if utility is constant over all 256 subsets on more than 60% of
   questions after one pool re-sample.
3. Interactions do not matter for decisions if both of these hold:
   - on at least 90% of non-constant questions, order-1 terms explain at
     least 90% of the variance;
   - LOO and Shapley pick the exact-optimal B = 4 set at least 95% of the
     time.

   Then write a short negative note and stop.

**What it gives within days, and why it matters.**

- Step 0 answers, in about a day of host time after the fetch, whether exact
  paired replay works on this node and at what throughput cost. The legacy
  oracles failed that A/A replay, and R01's batch-invariant arm could not
  have run (O4).
- The first exhaustive tables follow in under a week. No exact
  potential-outcome tables for agent-memory QA were found in the stated
  queries, nor any check of the credit rules memory learners train on
  against such tables.

### 4. AM4: single-write interventions in self-written memory

`AM4`. Memory area. Verifier: **STILL_OPEN**. **Owner's disposition:
ALTERNATE (memory area), after the repairs below and after AM1's Step 0
passes.**

Scores: Sig 5.83, Corr 5.00, Cite 7.17, Nov 5.33, Feas 4.83. J1
6/5/7/5.5/5, J2 5.5/5/7.5/5/4.5, J3 6/5/7/5.5/5. Lowest Corr 5 (at the
floor), lowest Cite 7. Passes both gates.

**Question.** The setting is self-evolving agents that write their own
memory: Dynamic Cheatsheet, and ACE-style playbooks.

- Does one early write change later writes and final success?
- Is the run-to-run instability that RBC and the fragility study report
  caused by memory dynamics amplifying small differences, or by per-call
  sampling noise?

Both are measured with bit-exact replay and single-write interventions.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| RBC | [2610.18427](https://arxiv.org/abs/2610.18427), 2026-10-13 | 27B AppWorld with per-test feedback: three runs score 82.5, 58.9 and 30.0 against 78.4 with no playbook; runs differ only in task order and sampling. Curates around the instability; does not decompose it |
| Fragility of self-improving agents | [2608.18066](https://arxiv.org/abs/2608.18066), 2026-08-18 | Variance rises in 71% of cases; best-to-worst gaps up to 10 pp. No isolation of one write |
| MemForm | [2610.14431](https://arxiv.org/abs/2610.14431), 2026-10-10 | Adversarial poisoning through consolidation order |
| Dynamic Cheatsheet; ACE | [2504.07952](https://arxiv.org/abs/2504.07952), 2025-04-10; [2510.04618](https://arxiv.org/abs/2510.04618), 2025-10-06 | The systems under test; endpoint gains only |
| MemAttr | OpenReview [g57t6h0f3Q](https://openreview.net/forum?id=g57t6h0f3Q), 2026-09-14 | The closest prior (missed by the scout). "Generation influence": a memory acts through later-written memories, attributed with lineage-band Shapley |
| Write-Back Redundancy Breaks LOO Attribution | OpenReview [gSBEPUmVk2](https://openreview.net/forum?id=gSBEPUmVk2), 2026-10-12 | Near-duplicate lineages create deletion thresholds |
| EvoPathBench; Trace Evolution Bench | [2609.24663](https://arxiv.org/abs/2609.24663), 2026-09-21; [2610.15055](https://arxiv.org/abs/2610.15055), 2026-10-10 | Process-level evolution paths; no_evolve seed bands of 5-12.5 pp |

**What the judges agreed on.** Separating write-path amplification from
sampling noise would decide whether single-run evaluations of self-evolving
memory mean anything.

**Defects:**

1. It mixes decode policies: greedy-replay interventions against seed
   variance at T = 0.7 (all three).
2. Divergence that grows after any prompt edit is expected from per-call
   sensitivity alone. Only a non-propagating control separates that from
   loop amplification (J2).
3. Final accuracy on 150 tasks has an SE of about 4 pp with few runs (J2).
4. Qwen3-8B may not learn from a cheatsheet at all (all three; kill 3).
5. GPQA-Diamond is gated, and accepting its terms is Kevin's.
6. Sequential long-reasoning runs will cost more than estimated (J1, J3).

**Corrections that apply.**

- Use common-random-number seeded sampling under batch invariance for both
  the natural-variance arm and the intervention arm.
- Add a non-propagating control: perturb what is read at task t without
  writing it back.
- Use an AIME-only stream (public) unless Kevin accepts GPQA's terms.
- Run a cheatsheet-learning pre-check on Qwen3-8B (base runs against no
  cheatsheet) before any intervention.
- Cite MemAttr and Write-Back Redundancy.

**First experiment.**

- Reader: batch-invariant Qwen3-8B after AM1's A/A gate.
- Memory: a Dynamic-Cheatsheet-style cumulative cheatsheet, with code
  execution disabled (R570).
- Stream: 150 tasks; 3 task orders (seeds 42-44).
- Runs per order:
  - a base run and an A/A rerun;
  - interventions at t ∈ {5, 25, 75}: drop, paraphrase, or an off-domain
    swap;
  - the non-propagating control;
  - CRN-seeded natural-variance runs.
- Metrics:
  - playbook divergence against tasks since the perturbation;
  - final-accuracy differences;
  - intervention-induced variance against seed variance.

**GPU-h.** 4-6 as estimated by the scout; the judges expect more.

**Kill criteria** (the scout's):

1. The A/A gate fails.
2. The dynamics are contractive if both of these hold:
   - divergence falls below 10% of its peak within 10 tasks for every
     intervention type;
   - intervention-induced variance is under 25% of seed variance.

   Then publish the negative.
3. Base cheatsheet runs show no learning (within ±2 pp): switch the stream
   once, then stop.

### 5. AM2: the placebo share of per-memory deletion credit

`AM2`. Memory area. Verifier: **NARROWED**. **Owner's disposition: FOLD into
AM1 as placebo arms.**

Scores: Sig 5.00, Corr 5.83, Cite 7.17, Nov 4.17, Feas 8.17. J1 5/6/7/4/8, J2
5/5.5/7.5/4.5/7.5, J3 5/6/7/4/9. Lowest Corr 5.5, lowest Cite 7. Passes both
gates.

**Question, as corrected (verifier).** Under bit-exact replay on
LongMemEval-S, what fraction of Hindsight-PRM-style per-memory deletion
labels survives subtracting matched content-placebo arms, split by gold and
non-gold memories? The placebo arms are a length- and rank-matched irrelevant
swap, a paraphrase, and a reorder. The study is best run as placebo arms
inside AM1's infrastructure.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| Re-feeding Is Not Replaying | [2606.15621](https://arxiv.org/abs/2606.15621), 2026-06 | Engine replay noise in token-level credit (replica floor 9-23%); `VLLM_BATCH_INVARIANT=1` gave zero disagreement (vLLM 0.22.1, A100). AM2 measures content placebos once engine noise is removed |
| RoutePrism | [2609.34160](https://arxiv.org/abs/2609.34160), 2026-09-28 | An equal-length non-supporting substitute as the control for restoring displaced records |
| Hindsight Memory-PRM | [2608.29605](https://arxiv.org/abs/2608.29605), 2026-08-30 | Correction to the scout: it has a label-level "shuffled-flip placebo" (70.5 vs 70.2), not a prompt-level content placebo |
| Illusion of Robustness | [2607.12963](https://arxiv.org/abs/2607.12963), 2026-07-14 | Irrelevant context flips predictions in general tasks |
| ICRL reward study | [2610.11152](https://arxiv.org/abs/2610.11152), 2026-10-08 | Shuffled or corrupted trajectories work as well as real ones |
| Sham-control neighbours | [2609.27247](https://arxiv.org/abs/2609.27247), 2026-09-23; [2609.34177](https://arxiv.org/abs/2609.34177), 2026-09-28; [2610.02764](https://arxiv.org/abs/2610.02764), 2026-10-02; [2609.01106](https://arxiv.org/abs/2609.01106), 2026-09-01 | Counterfactual memory audit for robot policies; relationship-level interventions with pair-transport controls; within-user permutation placebo; an unrelated hint rescues 19 failures against 36 for a relevant hint |

**What the judges said.**

- A placebo flip under exact replay is still a real effect on that reader,
  so calling it label noise needs an argument (J1).
- A matched swap is not content-free: it adds a new distractor. So
  "deletion minus placebo" rests on an additive assumption, not an
  identified decomposition (J2).
- Count flips on judged correctness, not on answer strings (J2).
- Cheap, and best folded in (all three).

**First experiment and GPU-h.** As arms inside AM1: the full and empty
pools, 6 deletions, 6 paraphrases (filtered by entailment), 6 matched swaps
and 2 reorders per question. About 2-3 GPU-h.

**Kill criteria** (the scout's):

1. The A/A gate fails.
2. Deletion and placebo flip rates are both under 1% for non-gold memories.
3. The labels are robust if both of these hold:
   - the placebo-to-deletion flip ratio is at most 0.1 for both classes;
   - fewer than 2% of labels change after placebo subtraction.

   Then write a short negative note.

### 6. AM6: one-pass signals of memory use against exact labels

`AM6`. Memory area. Verifier: **NARROWED**. **Owner's disposition: FOLD into
AM1 as an analysis section.**

Scores: Sig 4.17, Corr 6.17, Cite 7.17, Nov 3.67, Feas 7.00. J1 4/6/7/4/7, J2
4/6.5/7.5/3.5/7, J3 4.5/6/7/3.5/7. Lowest Corr 6, lowest Cite 7. Passes both
gates.

**Question, as corrected (verifier).** On exact batch-invariant deletion
labels for LongMemEval memory units, does any one-pass internal signal beat
cheap non-internal baselines at predicting causal necessity?

- Internal signals: raw retrieval-head mass, AT2-style learned head weights,
  and a cross-fitted probe.
- Baselines: retrieval rank, lexical answer overlap, and memory length.

It is run as an analysis section of AM1.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| AT2, Learning to Attribute with Attention | [2504.13752](https://arxiv.org/abs/2504.13752), 2025-04-18 | Head weights learned from ablations match many-ablation attribution in one pass |
| Causal Evidence Sets for Global Context Pruning | [2607.21692](https://arxiv.org/abs/2607.21692), 2026-07-23 | Attention and causal masking disagree on retrieval tasks with known evidence |
| CVMA | [2607.25467](https://arxiv.org/abs/2607.25467), 2026-07-28 | Current attention ranks future-useful regions worse than random |
| AGMR | [2607.17621](https://arxiv.org/abs/2607.17621), 2026-07-20; ICLR 2027 version OpenReview [13FlZnpjSN](https://openreview.net/forum?id=13FlZnpjSN), 2026-09-18 | Correction to the scout: the ICLR version reports intervention experiments, so the signal is not unvalidated, though it is not checked against exact potential outcomes |
| Others | [2610.09493](https://arxiv.org/abs/2610.09493), 2026-10-07; [2609.00753](https://arxiv.org/abs/2609.00753), 2026-09-01; [2607.23804](https://arxiv.org/abs/2607.23804), 2026-07-26; ContextCite [2409.00729](https://arxiv.org/abs/2409.00729) | Source reliance in RAG; context-vs-parametric authority; attribution under overlap with the weights; an ablation surrogate |

**What the judges said.**

- The core question is largely answered by AT2, 2607.21692 and CVMA. The
  residual is the comparison against cheap baselines on memory units (all
  three).
- Knockout is not deletion, because positions shift.
- The HF/vLLM agreement filter adds selection bias (J2).

**First experiment and GPU-h.** HF eager-attention re-runs of the
full-memory prompts, retrieval heads chosen on a held-out half, span
knockouts, and a cross-fitted probe (seeds 42-44). About 2-4 GPU-h.

**Kill criteria** (the scout's):

1. A cheap baseline is within 0.03 AUROC of the best internal signal.
2. All signals score below 0.65 AUROC.
3. HF and vLLM greedy answers differ on more than 20% of prompts.

### 7. AM3: placebo memory in memory-augmented RL (fails the correctness gate)

`AM3`. Memory area, bridging to the GPU area. Verifier: **STILL_OPEN**.
**Owner's disposition: HOLD. Repair the identification, then re-judge.**

Scores: Sig 6.83, Corr 5.17, Cite 7.50, Nov 6.50, Feas 5.33. J1 7/5/7/7/5, J2
6.5/4.5/7.5/6/5, J3 7/6/8/6.5/6. **Lowest Corr 4.5 (J2): fails the
correctness gate.** Lowest Cite 7.

**Question.** In memory-augmented RL for LLM agents, is the training gain
caused by the content of the retrieved experience? Or would a content-placebo
memory produce the same gain by diversifying rollouts? The placebo has the
same format and length, with entries shuffled across tasks. The scout's plan
measures it first at inference, as the change in GRPO's learnable-group
fraction, and then in a matched GRPO pilot.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| EMPO² | [2602.23008](https://arxiv.org/abs/2602.23008), 2026-02-26 (ICLR 2026) | +128.6% on ScienceWorld. The number is in the paper's own text (verifier), so it is first-party until replicated. Has with-memory and without-memory modes only |
| Complementary RL | [2603.17621](https://arxiv.org/abs/2603.17621), 2026-03-18 | With and without experience; no content placebo |
| EDGE | [2608.21946](https://arxiv.org/abs/2608.21946), 2026-08-22 | Experience-guided exploration; no placebo arm |
| Training-Free GRPO | [2510.08191](https://arxiv.org/abs/2510.08191), 2025-10-09 | Experience as a token prior in place of weight updates |
| Spurious Rewards | [2506.10947](https://arxiv.org/abs/2506.10947), 2025-06-12 | Placebo logic applied to the reward |
| Nearest placebo neighbours | [2610.11152](https://arxiv.org/abs/2610.11152); [2609.01106](https://arxiv.org/abs/2609.01106); HiLL [2604.00698](https://arxiv.org/abs/2604.00698), 2026-04-01 | All at inference or label level; none during weight-update RL |

The verifier re-ran full-text greps on 2026-10-14 for these terms:
shuffl, placebo, random experience or memory, irrelevant, mismatched, other
task. They found no content-placebo memory arm in EMPO², Complementary RL or
EDGE.

**Why it fails the gate (J2, with J1 and J3 concurring on the substance).**

1. Stage 1 measures a proxy (learnable-group fraction at inference), not RL
   gain. The causal test is Stage 2: 60-150 GPU-h, a new verl or TRL image,
   ALFWorld packaged for `--network none`, and the gauntlet.
2. On MATH the "shuffled" arm keeps transferable generic strategy content, so
   it is not a placebo there.
3. A home-built Training-Free-GRPO library says little about the cited
   systems.
4. Kill 1 (no memory effect for Qwen3-8B on MATH) is likely to fire.

**What a repair needs before re-judging.**

- Make a small matched GRPO run with a placebo arm the decisive test, not the
  inference proxy.
- Use a domain where experience is task-specific, so that shuffling removes
  content; ALFWorld text is one.
- Use a published system's method or experience library where its release
  allows.

It is the slate's highest-significance question and the one that would use
the node for RL. A repaired version deserves a fresh judging. It is not
recommended as it stands.

**GPU-h.** Stage 1 4-6; Stage 2 60-150 (gauntlet, D24).

**Kill criteria** (the scout's):

1. Real memory changes learnable-group fraction and pass@8 by under 3 pp on
   both models.
2. Shuffled and generic arms each recover under 20% of real memory's gain,
   with CIs excluding 50%.
3. In Stage 2, real memory beats no memory by under 2 pp at matched steps.

### 8. G4: reasoning KV eviction against a quantized-KV baseline (fails the correctness gate)

`G4`. GPU area. Verifier: **NARROWED**. **Owner's disposition: fails the
gate. The quantized-KV arms fold into G1; the eviction comparison is
dropped.**

Scores: Sig 5.17, Corr 5.50, Cite 7.33, Nov 4.33, Feas 5.67. J1 5/6/7/4/6, J2
5/4.5/8/4.5/5, J3 5.5/6/7/4.5/6. **Lowest Corr 4.5 (J2): fails the
correctness gate.** Lowest Cite 7.

**Question, as corrected (verifier).** In vLLM 0.31 on H100, does any
reasoning-trace eviction method that ships vLLM-compatible code beat native
fp8 or int8 per-token-head KV in problems per hour, at matched paired
accuracy, on Qwen3-8B? Random Attention is one such method. BreadthKV
already answers the accuracy and length-inflation half.

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| BreadthKV | [2610.05685](https://arxiv.org/abs/2610.05685), 2026-10-05 | Fixed byte budgets on Qwen3-8B and two others. KIVI-4 with no eviction comes within 5.5 pp of FullKV. Eviction sends 91% of AIME samples to the length cap at the tightest budget. "We did not measure serving throughput" |
| Random Attention | [2609.03430](https://arxiv.org/abs/2609.03430), 2026-09-03 | Eviction throughput in vLLM (32-43% over the strongest selector), not against quantized KV |
| R-KV; GrowPage; EpiKV | [2505.24133](https://arxiv.org/abs/2505.24133); [2609.03494](https://arxiv.org/abs/2609.03494), 2026-09-03; [2606.26472](https://arxiv.org/abs/2606.26472), 2026-06-25 | Headline gains against BF16 full-KV baselines |
| Rethinking KV compression | [2503.24000](https://arxiv.org/abs/2503.24000), 2025-03 | Gains vanish in optimized stacks; outputs up to 50% longer |
| Sparse-RL | [2601.10079](https://arxiv.org/abs/2601.10079), 2026-01-15 | Compressed rollouts destabilize RL unless corrected |

**Why it fails the gate (J2).**

1. Equivalence within 1 pp is underpowered on 60 AIME problems x 8 plus a
   MATH subset.
2. Comparing a forked vLLM (Random Attention or EpiKV) with stock 0.31
   confounds engine version with method.
3. BreadthKV covers the accuracy and length half (all three).

J2 judged that it does not breach sweep stop item 15 (2026-10-06), since it
is a dense audit with no new eviction engineering.

**GPU-h.** About 6 (cap 8), about half of it shared with G1's dense
quantized arms.

**Kill criteria** (the scout's):

1. Report a positive replication if eviction beats the best quantized
   baseline by at least 1.3x in problems per hour, with accuracy within 1 pp.
2. Stop after the quantized arms if no eviction code runs in a vLLM-class
   engine within a day.
3. Treat the result as a framework comparison if the BF16 baselines differ
   between harnesses.

### 9. G5: single-node GRPO step anatomy and async ceiling (fails the correctness gate)

`G5`. GPU area. Verifier: **STILL_OPEN**. **Owner's disposition: fails the
gate; drop as a line.**

Scores: Sig 4.50, Corr 5.17, Cite 6.67, Nov 4.00, Feas 4.33. J1 4/5/6/4/4, J2
4.5/4.5/7/4/4, J3 5/6/7/4/5. **Lowest Corr 4.5 (J2): fails the correctness
gate.** Lowest Cite 6, at the floor.

**Question.** On one 8xH100 node, where do wall time and HBM go in a GRPO
step for a 4B reasoning model? The phases are rollout (full batch and tail),
old-logprob recompute, actor update, weight sync, and sleep/wake. The
comparison is hybrid Qwen3.5-4B against a dense control. How much of the
synchronous idle time do verl's one-step-off and fully-async modes recover,
compared with the Amdahl ceiling and with a closed-form staleness
prediction?

**Priors and deltas.**

| Prior | Source, date | Delta |
|---|---|---|
| verl fully_async | [docs](https://github.com/verl-project/verl/blob/main/docs/advance/fully_async.md), accessed 2026-10-14 | Cluster scale (32-128 H20), dense; 1.72-2.67x |
| DORA | [2604.26256](https://arxiv.org/abs/2604.26256), 2026-04-29 | Industrial scale; rollout 50-80% of step time |
| Applied Compute, staleness | [alphaXiv 2607.staleness-in-fully-async-rl](https://www.alphaxiv.org/abs/2607.staleness-in-fully-async-rl), 2026-07-03 | A closed-form staleness prediction. Blog-style source: first-party |
| HARTS | [2608.28158](https://arxiv.org/abs/2608.28158), 2026-08-28 | A hybrid-attention agentic RL system; no step anatomy |
| Hardware-Aware Resource Management for Fully Async Agentic RL | OpenReview [PeJixdAV9G](https://openreview.net/forum?id=PeJixdAV9G), 2026-09-04 | Qwen3-4B on 2xMI350X; no hybrid, no Amdahl comparison |
| Others | [2609.36830](https://arxiv.org/abs/2609.36830); [2609.25463](https://arxiv.org/abs/2609.25463); KV4-RL [2610.14448](https://arxiv.org/abs/2610.14448) | Staleness control; a survey of rollout efficiency; rollout-only traces on a dense model |

**Why it fails the gate (J2).**

1. Six steps per configuration cannot test the staleness prediction.
2. Async modes change the algorithm, so speedup without matched reward is
   half a result.
3. Qwen3.5-4B against Qwen3-1.7B-Base confounds architecture with size.
4. It is the hardest engineering on the slate: a new verl image, Ray under
   `--network none`, and verl issue #7438 (Qwen3.5 fails under
   one_step_off).
5. With G3 occupied, its checkpoints have no downstream use.

**GPU-h.** Stage 1 about 7; Stage 2 over 8 (gauntlet).

**Kill criteria** (the scout's):

1. Report the anatomy alone if the synchronous tail is under 15% of
   generation time.
2. Fall back to TRL if verl cannot run in the lane within a day.
3. Stop if neither runs.

If AM3 Stage 2 is ever admitted, its RL image is the instrument G5 wanted.

---

## Open items for Kevin

1. **Admission.** D103 sends the top candidates through the gauntlet, and
   D92 admits below 100. Each lead's first step is under 8 GPU-h, and each
   has a small executable pilot named above. Admission is the only ruling
   either lead needs.
2. **One licensed fetch.** The Qwen3-8B weights (Apache-2.0, about 16 GB)
   serve as:
   - AM1's reader;
   - G2's and G1's size-matched dense control;
   - the A/A gate.

   D1 allows the fetch. The registry note that calls it a D5 stand-in with
   "No weight download is planned" changes in the same commit (O7).
3. **The node is in use now** by inference-baseline-v1 (O2):
   - it is exploratory and unregistered;
   - its branch is not on main.

   Its fixed-length and FP8-KV cells are the first area-2 numbers and feed
   G1. How it fits D103's gauntlet-first plan is Kevin's to say; this
   dossier does not rule on it.
4. **GPQA-Diamond** is gated on HF. It matters only if AM4 is chosen and
   only if Kevin accepts its terms; AIME alone works otherwise.
5. **R01's record.** R01's P0' arm (Qwen3.5-4B with
   `VLLM_BATCH_INVARIANT=1` on stock v0.31.0) was not runnable as drafted
   (O4). A one-line note in that record would stop later designs from
   assuming it.
6. **The program's GPU-hour counter.** The brief reports `state.json`'s
   `gpu_hours_spent_this_program` (15.63) as stale against about 25 GPU-h
   in 8 days. This dossier does not edit it.

## Coverage limits

- **Cutoff and tools.** Retrieval cutoff 2026-10-14. orx 0.2.2 reports
  itself outdated (latest 0.2.18), which may affect ranking.
- **Novelty.** Everywhere it means "absent in the stated queries". Nothing
  here says a question is new in general.
- **Memory scout.**
  - Queries ran in parallel shells, so the printed per-query hit lists are
    interleaved; the ids are reliable.
  - Absence claims rest on case-insensitive full-text greps, not line-by-line
    reads.
  - The legacy ledger `legacy/research/memory-sources.yaml` (229 sources) was
    not re-screened against these candidates.
- **GPU scout.**
  - Did not search Semantic Scholar, Google Scholar, NVIDIA developer docs,
    or the SGLang and LMCache docs.
  - Did not search the SGLang, slime or miles codebases beyond miles PR
    #3597.
  - GitHub code search is incomplete.
- **Verifier.** Covered OpenReview with 26 queries. Neither the verifier nor
  any other step searched X, Reddit, Chinese-language sources, patents or
  the ACL Anthology.
- **Dossier owner.**
  - This file adds title-level checks of 10 ids, 9 discover queries and 2
    report reads.
  - It did not run the ACL Anthology pass the renewal ran.
  - OpenReview ids are as the verifier reported them.
- **Unverified until a GPU dry run.**
  - Batch invariance for Qwen3-8B in the host's v0.31.0 overlay.
  - Element-level correctness of int4 and int8 per-token-head KV for
    Qwen3.5's head_dim-256 gated attention.
  - HF and vLLM greedy agreement for Qwen3-8B.
  - Whether verl or Ray runs in the lane.
- **Estimates.**
  - Every GPU-h figure is an estimate.
  - G1's byte counts are modeled; ncu and nsys counters are blocked on this
    host.
  - AM1's request rate is assumed from an 8K-prompt measurement on another
    model.
- **First-party numbers.** EMPO²'s +128.6% and Applied Compute's staleness
  formula are first-party until replicated.
