# Research Direction: G2-stream. How local is Kimi K2.x's expert routing on real decode workloads? What cache hit rates does it reach on a 128 GB machine? Does a host-side streaming emulator, checked on held-out ds4 M5 Max measurements, predict Mac speed well enough to price Kimi K2.6 at about 2-2.6 bits? (pilot of at most 8 GPU-h, then a full study)

**Status:** draft; gauntlet wave 1 synthesis by the single owner on 2026-10-15 (branch `gauntlet/g2-kimi-expert-streaming`, not pushed, not frozen); the draft registration for the pilot is `program/preregistrations/g2-kimi-expert-streaming-v1.md` (DRAFT, new experiment id, no ledger row); the blind critic, the refute-first triad and the two reviewers have not run; no host job was submitted by the synthesis (read-only checks and source reads only); the full study is proposed here and registered after the pilot; downloads over 1 GB and the full study's admission are Kevin's (AGENTS.md rule 9; D24, D92)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification, contract and registration by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-15
**Coverage limits:** orx 0.2.2 (reports itself outdated against 0.2.18): 57 orx discover records across three cells (alphaXiv keyword and embedding, OpenAlex), several bounded with `--published-after`, plus 3 OpenAlex DOI lookups; 7 web searches; 8 GitHub repository or issue searches; 7 Hugging Face dataset searches (82 counted searches in all). Full-text reads with `orx paper --full` of every closest paper prior (2608.12103, 2608.07911, 2510.05497, 2609.14864, 2608.16157, 2609.18110, 2609.29032, 2609.18063 by the cells; the first five again by the synthesis owner); the closest non-paper prior (the Anemll Kimi streamer and its modeling workflow) read in full from its repository at `a809594f`; ds4's documents and cache source read at the measurement commit `90aa4b56`. Not reached: the gated Kimi-K2-Thinking trace files themselves (README and file listing only; opening them needs a Hugging Face account and gate acceptance, Kevin's decision); two Research Square preprints with empty abstracts (rs-11268552, rs-10741449); IJCAI 2026 DoMoE; the KTransformers SOSP'25 paper; later sections of the 6-page Zenodo PDF. Not searched: live X, Reddit and r/LocalLLaMA, Hacker News, OpenReview, ACL Anthology, patents, Chinese-language sources beyond one web search, Semantic Scholar and Google Scholar citation graphs, the arXiv API (not reachable from the Mac). PRISMA-style: 549 ids returned by the counted searches (305 unique), screened by title; about 45 read beyond the abstract; 0 direct priors; 7 narrowing priors.
**Budgets:** queries=150; wall_minutes=720; tokens=10000000; dollars=150; waves=3; gpu_hours=0.5
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-16-g2-kimi-expert-streaming/bundle.json

The budgets are this gauntlet's, cumulative; at least 30 queries are reserved for the three
refuters. The GPU budget (0.5 GPU-h) is for the open-weight reviewer's lane job only; the doctor
reads budgets as integers, parses it as 0 and flags it (left as declared). The novelty verdict
field uses the doctor's vocabulary; the merged kill-shot verdict is **NARROWED**, not OCCUPIED
(frontier and kill-shot cells independently). The slug is `g2stream` on the host and in the ledger:
`~/cotcodec-runs/stage0/g2-pilot`, `g2b-*`, `g2c-*` and `program/gauntlet/2026-10-15-g2rl-*.jsonl`
belong to D104's unrelated "G2" and must not be overwritten.

## Budget accounting (read before the refuters run)

| Cell | orx discover | Web search | GitHub search | Hugging Face search | Counted | Reads (uncounted) |
|---|---:|---:|---:|---:|---:|---|
| Frontier | 24 | 5 | 3 | 5 | 37 | 8 full texts, about 30 targeted reads, Hub and GitHub API reads, 1 fetch |
| Kill-shot | 10 | 2 | 5 | 0 | 17 | 13 full texts, ds4 and Anemll documents, 4 fetches |
| Cross-domain | 23 (+3 OpenAlex DOI lookups) | 0 | 0 | 0 | 26 | 3 full texts, 6 PDFs |
| Asset and cost | 0 | 0 | 0 | 2 | 2 | about 30 Hub reads, 6 GGUF header range reads, read-only host listing |
| Synthesis | 0 | 0 | 0 | 0 | 0 | 5 orx full texts, ds4 at `90aa4b56`, Anemll at `a809594f`, Hub metadata, 1 page fetch, snapshots |
| **Total** | **57 (+3)** | **7** | **8** | **7** | **82** | |

82 of 150 are used; 68 remain, 38 above the refuters' reserve of 30. Token, wall-clock and dollar
use are metered by the orchestrator over the whole wave; the synthesis spent no dollars and no
GPU time.

## Scope

- **The pilot** (draft registration v1; Slurm caps 7.45 GPU-h, of which 1.95 is a conditional
  fallback; about 4.1 GPU-h expected; `compute/caps-g2stream.json`). It runs before 2026-10-21 on
  the host's CPU lane and GPUs 1-5. It needs neither GPU 0 nor the INT4 checkpoint's remote code.
  It produces Kimi K2.6 hit-rate curves on four workloads, and it validates the emulator against
  held-out ds4 measurements. Only if the emulator passes does it report Kimi's predicted Mac speed
  and the decision rule that follows from it.
- **The full study** (proposed here, registered after the pilot; 15-41 GPU-h, cap 50). It adds
  INT4 traces at TP8 after GPU 0 frees, the INT4-against-Q2 equivalence, a larger session sample,
  the GLM matched sample at full size, and top-6 and top-4 traces as G5's input. It runs only on the
  decision paths named in the decision rules.

## Merged discovery cells, by mechanism

Four independent cells ran: frontier and novelty, kill-shot, cross-domain, asset and cost. Their
findings are merged below by mechanism, not by cell. The synthesis owner re-opened every source
that a decision rests on (marked in the claim registry). Two of the cells' readings did not survive
that re-reading; both are corrected in place.

**1. Kimi K2-family routing traces already exist; the dossier's G2 status line is wrong.**
"No Kimi K2 trace ... exists" (DOSSIER section 4) is false on three counts:
- *Patterns behind Chaos* (2510.05497, ISCA 2026) profiled "Kimi K2 (1000B)" with SGLang and
  released Kimi-K2-Thinking per-token, per-layer selections: 31,593 request files (about 58 GB) over
  MMLU, MMLU_ZH_CN, Chinese-SimpleQA, LiveCodeBench and H4, with decode capped at 128 tokens. Its only
  K2 locality numbers are conditional-CDF masses: the top 20% of next-layer candidates cover 56% and
  of next-token candidates 53%. It reports no hit rate. The dataset is gated (auto-approve) and
  carries no licence tag.
- `0xSero/kimi-k2.6-reap-observations-v1` (Apache-2.0) holds K2.6 INT4 per-layer
  expert-frequency summaries from REAP's observer over raw-text categories (agentic, coding,
  function calling and others), not chat-templated.
- The Anemll llama.cpp fork captures `--moe-trace` JSONL for Kimi-K2.5 on an M5 Max (item 2).

None of these gives hit-rate curves on chat, agentic or long-document sessions with long decode, or
on the routing of the file a Mac would stream.

**2. One Kimi K2.x residency hit-rate measurement exists, and it is internally consistent.** The
Anemll fork (first-party, MIT, `a809594f`) streams Kimi-K2.5 UD-TQ1_0 on an M5 Max 128 GB through a
per-layer slot bank:
- Setup: one prompt, 100 greedy tokens, `-ngl 0 -ub 1`, cold start.
- Native top-8 with 64 slots per layer (16.7% of each layer's experts): 2.2 tokens/s at a 67.2% hit
  rate.
- Top-4, banks of 16-256 slots: 3.2-3.3 tokens/s, with hit rates of 55.6% rising to 76.4%; the
  rate saturates at 128 slots, where only compulsory first-touch misses remain.
- Reads: about 4.7 GB/s per 3.28 MB `pread`.

The kill-shot cell read its counters as inconsistent: 19,755 preads over about 110 tokens looked
like 75-93% of selections read from SSD. That arithmetic assumed one read per expert. The README's
3.28 MB is one projection tensor: 217 GB ÷ (60 × 384 × 3) ≈ 3.1-3.4 MB. Each miss is therefore three
reads. 19,755 ÷ 3 ≈ 6,600 misses over 6,120 layer calls is 1.08 misses per call, which is the
README's own "Misses/call" and matches its 73.7%. At top-8, 49,266 reads give about 69% hits against
the reported 67.2%. The README's "256 experts/layer" heading is wrong for Kimi (384), as the
kill-shot cell noted.

Neighbouring hit rates, none for K2:
- S82 (2608.12103), Kimi K3 (E = 896, k = 16) and DeepSeek-V3 (E = 256, k = 8): LRU 44% against
  Belady 62% for K3 at 32 experts per layer, and LRU 48% against static 35% for DeepSeek-V3.
- FreeToken (2608.16157): global LRU misses 39% for V4-Flash at 11% cached on agentic workloads.
- LMSYS SSD Expert Pack: unique-key hit rates for V4-Flash and K3.

**3. Measured Kimi-on-Mac speeds exist; none comes from a ds4-class engine.** All first-party:
- Anemll, Kimi-K2.5 on an M5 Max: 2.2 tokens/s at top-8 on the CPU-compute path. Its `-ngl 99`
  path reaches 4.5 tokens/s at top-4, with degraded output on some runs.
- rustane, Kimi-K2 on an M4 Max 128 GB: 1.7 tokens/s. `F_NOCACHE` alone raised it from 1.15 to 1.68,
  because "the OS page cache was absorbing" expert reads and "evicting the shared backbone weights".
- An MLX pread streamer, K2-Instruct on an M3 Max: 0.5 tokens/s.
- Deltafin, Kimi K3 (not K2) on an M5 Max from four SSDs: 1.0 tokens/s.

The dossier's S51 (1.7 tokens/s, "engine not stated") is the rustane report.

**4. ds4's validation targets are richer than the dossier records, and they pin the SSD rate.**
Read by the synthesis at the measurement commit `90aa4b56`, 2026-09-06:
- **Machines and runs.** ds4 used two M5 Max machines, and `QA_BEFORE_RELEASES.md` lists far more
  than the two rows the dossier used:
  - the 16 GiB GLM 5.3 references, with exact inputs: 12.59 tokens/s prefill on a 463-token prompt
    and 6.14 generation on the "apple" prompt, medians of three after a discarded warm-up;
  - the 35.36 GiB 8K/4K condition measured on both machines: generation 3.69/3.62 and 3.96/3.81, a
    cross-machine spread of 1.9-3.8%;
  - per-run minimum available memory: 15.05 GiB at the 61.35 GiB cache, 27.87 GiB at 35.36 GiB;
  - paired runs at 61.35 GiB with identical routing ("All 154,880 logits and complete generated
    text matched in every pair") that differ only by an environment toggle between whole-layer and
    selected-expert append reads.
- **Engine behaviour.**
  - Generation timing includes the first decode step after prefill (`ds4_bench.c`).
  - GLM demand-fills its cache; DeepSeek preloads a shipped hotlist.
  - The Metal policy is decayed route hotness: counts on every selection, halved every 16 decode
    tokens, evicting the lowest count with ties broken by recency. The CUDA path is LRU.
  - Experts are read with `pread` on a descriptor opened without `F_NOCACHE`, so on the Mac an
    expert-cache miss can be served by the macOS file cache.
- **Desk identification of B.** The whole-layer appends took 30.8, 34.4 and 34.9 s for 16, 43 and
  114 tokens. Being nearly flat, they are full passes over the 186.86 GB routed pool. That pins an
  effective whole-layer read rate of about 5.4-6.1 GB/s on the maintainer's machine, independent of
  the prompt.
- **The dossier's null under this B.** With B fixed at 6.08 GB/s and e at 0.61, the dossier's
  model (A6 with A7's cache-share hit rates) under-predicts 10 of 11 generation rows, with a
  geometric-mean error of 41.5% (`compute/identification-g2stream.json`). It also predicts a ratio
  of 1 for every within-run contrast; the observed ratios are 1.25-1.63.
- **The null as written.** With B free in A5's 5.85-10.6 GB/s, its interval contains 9 of the 11
  rows. That is the kill-shot and cross-domain cells' "unfalsifiable as written" point, now
  measured.

**5. The emulator method has priors; validated Mac streaming prediction has none.**
- The Anemll bank-modeling workflow (2026-03-31) prescribes the mechanism closest to this one
  (closest prior, below): traces, then per-layer static, global static and refillable-LRU
  simulation, then calibration against the same engine's runtime anchors. It publishes no outputs
  and no held-out check.
- The Zenodo roofline (10.5281/zenodo.21856981) projects an unexecuted 1T configuration from
  measured host terms and an OLMoE-validated cache model.
- 2609.14864 predicts Apple in-memory decode at 13.1-14.4% held-out MAPE; its prefill model failed.
- Cacheable-by-Design matches bytes ÷ bandwidth within 6% on a PC.
- S82 refuses bandwidth-constant time models and compares simulated misses with block-layer bytes.
- MoE-Lens and ServeTwin validate GPU-server throughput models.
- Cross-domain norms: calibrated simulators reach under 20% only on held-out macro workloads
  (Desikan et al.); report skill against a reference forecast (Murphy); keep a strict
  calibration-holdout split (Lee and Brooks).

**6. Classical cache methodology the K2 priors do not use** (cross-domain cell; searched in S82 and
S123 by term):
- exact miss-ratio curves for stack policies;
- Che's approximation as a simulator unit test;
- an IRM-shuffle split of popularity skew from temporal reuse;
- an explicit model of cold-start bias in short windows (Wood, Hill and Kessler: 0.40 against 0.02);
- Belady defined with the engine's event and bypass semantics;
- timing-in-the-loop multi-stream emulation;
- per-session percentile and win-count reporting;
- cluster bootstrap over sessions.

S123's event-atomic replay, held-out splits and cluster bootstrap are adopted as protocol, not
claimed.

**7. Decision relevance, the kill-shot's strongest argument.** On the Artificial Analysis index
v4.3.2 (first-party, accessed 2026-10-15), Kimi K2.6 scores 27, V4 Flash 0731 34 and GLM-5.3 45.
GLM 5.3 already streams on the target at a measured 3.6-6.1 tokens/s, and the dossier's own Kimi
range (2.5-5.8) sits at or below it. So **no G2 outcome alone makes streamed Kimi the right default
for Kevin's Mac**. The proposal accepts this and re-aims the decision:
1. G2 is the gate on the Kimi-compression lines (G1, G3, G5: 93-759 GPU-h in the dossier, as G1 54-306 on its k-quant route, G3 10-139 and G5 29-314),
   whose only Mac rationale is a Kimi that streams competitively. The pilot's decision statistic is
   therefore the matched speed ratio R of Kimi K2.6 to GLM 5.3 on the same sessions and memory
   scenario, not an absolute Kimi number.
2. A validated emulator (or an honest failure to validate one) settles whether host-side emulation
   can stand in for Mac measurements for any streamed model, which every streaming number in the
   dossier currently rests on.

**8. Assets and feasibility** (asset cell, read-only host check at 22:15Z on 2026-10-15).
- **What exists.**
  - GPUs 1-7 are idle. GPU 0 is held by job 1450, with job 1451 queued.
  - 1.77 TB of RAM, mostly page cache; 19 TB of disk free.
  - Kimi K2.6 INT4 at revision `7eb5002f`.
- **What does not.**
  - No GGUF of any model, and no llama.cpp, SGLang, KTransformers or ds4 image.
  - Stock llama.cpp callbacks cannot dump routing: `llama-eval-callback` prints only three edge
    values per dimension, dropping two of the eight experts. A small reviewed CPU-side `cb_eval` dump
    tool is needed (host code, no GPU kernel).
- **Downloads.** The pilot needs 707.5 GB: GLM 5.3 IQ2_XXS 211.08, V4 Flash Vision-Exp MXFP4 155.98
  and K2.6 UD-Q2_K_XL 340.48. That needs Kevin's go-ahead.
- **Remote code.**
  - The GGUF route needs no Moonshot remote code: the tokenizer and chat template are embedded in
    the file.
  - The INT4 route (vLLM 0.31.0 `--enable-return-routed-experts`, full study) needs the remote
    tokenizer reviewed.
  - SGLang v0.5.21 ships only CUDA 13 images.
- **ds4 itself** is not on the stock-runtime list, and its README discloses heavy agent authorship.
  It is read, never run.

## Claim and Research Question

Claim scope: `systems-pipeline` (a measurement and an instrument; no architecture claim). Three
linked questions, in order of dependence:

- **Q1 (locality, always answered).** Take the routing a 128 GB Mac would execute: Kimi K2.6
  UD-Q2_K_XL, generating its own responses with thinking on, in chat, coding, agentic tool-use
  sessions (replayed from recorded trajectories) and long-document QA (8-16K-token contexts), with
  up to 2,048 decoded tokens per session.
  - Replayed event by event, what hit rates do LRU, LFU, ds4's decayed-hotness policy, a static
    set pinned on a separate calibration split, and Belady reach from 5% to 50% of the expert pool?
    14%, 22% and 32% are named, and both cold-start and warm windows are reported.
  - Does ds4's policy reach h ≥ 0.70 at 22% (the dossier's A7 bracket) in every workload?
- **Q2 (emulator validity).** The emulator is a three-tier model: ds4's expert cache, the macOS file
  cache bounded by ds4's logged available memory, and the SSD. It also models cold start and ds4's
  two prefill paths, and has exactly one constant calibrated on a prompt-independent whole-pool
  read.
  - Fed host-measured routing traces of the exact antirez files, does it reproduce the held-out ds4
    M5 Max measurements: 11 generation levels within ±20% in aggregate, and three within-run
    contrasts within ±15%?
  - Does it beat a frozen null that takes hit rates from cache size alone?
- **Q3 (prediction and decision, only if Q2 passes).** What does the emulator predict for Kimi K2.6
  at about 2.6 bits (the Q2 file) and about 2 bits (byte geometry of a 1.9-2.1-bit file with Q2
  routing borrowed, labelled as such)? It predicts at the dossier's two memory scenarios, and as the
  ratio R to GLM 5.3 IQ2_XXS on the same sessions. Does R's interval lie wholly below 1?

## Strategic Fit and Why Now

- **D122.** Kevin asked whether 700B-1T open models "such as Kimi" can run usefully on a normal
  computer, with all model work on the H100 host.
- **The dossier's state.** Its Kimi streaming numbers rest on a hit rate interpolated from other
  models (A7) and a read rate assumed from a Linux testbed (A5). Its G2 status line and its "no
  streamer read rate measured on a Mac" are both outdated (merged items 1-4).
- **Why now.**
  - The host can run the pilot today, without GPU 0, on stock llama.cpp, plus a dump tool of about
    100 lines.
  - The ds4 maintainer published the most detailed Mac streaming measurement set that exists: paired
    contrasts with identical routing, cross-machine repeats, and memory logs.
  - The decision G2 gates (G1, G3, G5) is the most expensive line in D122.
- **Negative result.** A failed validation is equally useful: it stops the program from quoting
  host-emulated Mac numbers.

## Primary-Source Evidence

Read levels:
- **F**: full text read with `orx paper --full` by a discovery cell;
- **F\***: full text read by a cell and re-read by the synthesis owner;
- **A**: abstract or report only;
- **R**: repository, code, release or dataset record;
- **1P**: first-party page, README or blog, not replicated;
- **M**: this program's committed measurement;
- **D**: this synthesis's desk arithmetic on published numbers, committed in the bundle.

| ID | Claim | Source | Date | Read level |
|---|---|---|---|---|
| C01 | Kimi K2.6 text model: 61 layers (first dense), 384 routed experts, 8 active plus 1 shared, MLA; INT4 group-32 routed experts, other weights BF16; modified MIT, ungated | https://huggingface.co/moonshotai/Kimi-K2.6 | 2026-05-19 (rev 7eb5002f) | R |
| C02 | Unsloth K2.6 GGUF repository at rev 47c7cab1, ungated; UD-Q2_K_XL 340.48 GB, routed pool 331.14 GB, 6.90 GB routed and 8.53 GB non-routed read per token (header range reads) | https://huggingface.co/unsloth/Kimi-K2.6-GGUF | 2026-04-22; headers read 2026-10-15 | R |
| C03 | Kimi-K2-Thinking per-token per-layer expert selections released (MMLU, MMLU_ZH, SimpleQA, LiveCodeBench, H4; decode at most 128); K2 next-layer and next-token top-20% conditional mass 56% and 53%; no hit rates | https://arxiv.org/abs/2510.05497 | 2025-10-07 (v5 2026-05-12) | F* |
| C04 | The trace dataset is gated (auto) and has no licence tag | https://huggingface.co/datasets/core12345/MoE_expert_selection_trace | modified 2026-05-16 | R |
| C05 | K2.6 INT4 REAP observer outputs: per-layer expert-frequency summaries over raw-text categories; Apache-2.0 | https://huggingface.co/datasets/0xSero/kimi-k2.6-reap-observations-v1 | modified 2026-04-28 (rev 88f8625e) | R |
| C06 | Kimi-K2.5 UD-TQ1_0 on an M5 Max 128 GB, one prompt, 100 tokens, cold: top-8 with 64 slots per layer 2.2 tokens/s at 67.2% hits; top-4 3.2-3.3 tokens/s at 55.6-76.4% (banks 16-256); 3.28 MB per pread at about 4.7 GB/s | https://github.com/Anemll/anemll-flash-llama.cpp | README at a809594f, accessed 2026-10-15 | 1P |
| C07 | Anemll's counters are consistent with its hit rates once each miss is three tensor reads (19,755 reads ≈ 6,600 misses ≈ 1.08 per layer call) | https://github.com/Anemll/anemll-flash-llama.cpp | same | D |
| C08 | Anemll bank-modeling workflow: traces, per-layer static, global static and refillable-LRU simulation, runtime-anchor calibration; Kimi-K2.5 geometry 60 routed layers, 384 experts, 232.58 GiB sidecar; no estimator outputs published | https://github.com/Anemll/anemll-flash-llama.cpp/blob/master/docs/moe-bank-modeling-workflow.md | 2026-03-31 | 1P |
| C09 | Decode-only traces: K3 299 accepted tokens per domain, DeepSeek-V3 300 steps by a llama.cpp evaluation callback; K3 reuse after 1 token 32-36% and within 64 tokens 80-82%; fair 60/40 windows; LRU 44% against Belady 62% (K3, 32 per layer); DeepSeek-V3 LRU 48% against static 35%; batch-4 78% falls to 64% at 25% of the pool | https://arxiv.org/abs/2608.12103 | 2026-08-12 (v2 2026-08-30) | F* |
| C10 | The same study measures raw device reads at 27.0 GB/s cold and 61.4 GB/s warm against 29.6 GB/s in replay, and does not model time from bandwidth constants | https://arxiv.org/abs/2608.12103 | 2026-08-30 | F* |
| C11 | Event-atomic replay; sequential replay inflates LRU by 27.4%; one-template probe sets move effects by 19.4-31.9 points; union-to-capacity ratio must be reported | https://arxiv.org/abs/2608.07911 | 2026-08-04 (v4 2026-08-25) | F* |
| C12 | Agentic workloads at RTX 5090 capacity: global LRU misses 16% (Qwen3.6-35B-A3B, 37% cached) and 39% (V4-Flash, 11% cached); no Kimi support | https://arxiv.org/abs/2608.16157 | 2026-08-17 | F* |
| C13 | GGUF-metadata decode prediction: held-out MAPE 13.1% and 14.4% on two Apple M4 Max systems, 36.1% on an RTX 5080; prefill model failed (68-76% at 16K on Apple) | https://arxiv.org/abs/2609.14864 | 2026-09-14 | F* |
| C14 | A 1,045.8B configuration projected at 1.81 tokens/s from measured host terms and a cache model validated on OLMoE; no trillion-parameter model executed | https://doi.org/10.5281/zenodo.21856981 | 2026-08-09 | A |
| C15 | Kimi-K2.7-Code streamed at 0.89-1.03 tokens/s on an RTX 5090; a VRAM hit rate is given only for V4-Flash (80.1% with 22 GiB) | https://arxiv.org/abs/2609.18110 | 2026-09-16 | F |
| C16 | Unique-key VRAM hit rates for V4-Flash (54.2%, 46.4%) and Kimi K3 (17.0%, 22.7%); no K2 | https://www.lmsys.org/blog/2026-08-29-sglang-ssd-expert-pack | 2026-08-29 | 1P |
| C17 | An iPhone flash-backed MoE: LRU 0.00% at 512 MiB against 38.58% at 576 MiB; recorded phone sequences differ from a Python reference in all five cases | https://arxiv.org/abs/2609.29032 | 2026-09-24 | F |
| C18 | Single-shot Mac SSD-streaming benchmarks spread ±40% and up to 2.3x across sessions (16 GB M2) | https://arxiv.org/abs/2609.18063 | 2026-09-16 (v2 2026-09-17) | F |
| C19 | ds4 M5 Max streaming table (V4 Flash Vision-Exp 300/263 prefill and 11.9/19.3 generation, single run, 86.2 GiB cache; GLM-5.3-Flash Q4_K three-run medians); generation includes the first-token wait; "workload references, not a speed guarantee" | https://github.com/antirez/ds4/blob/main/docs/SSD_STREAMING.md | 2026-09-06 (90aa4b56) | 1P |
| C20 | ds4 QA at 90aa4b56: GLM 5.3 16 GiB references 12.59 prefill (463 tokens) and 6.14 generation (apple prompt), medians of three after a warm-up; paired whole-layer and selected-address appends with identical logits; the 35.36 GiB condition on two machines; minimum available memory per run | https://github.com/antirez/ds4/blob/main/QA_BEFORE_RELEASES.md | 2026-09-06 | 1P |
| C21 | ds4 Metal expert cache at 90aa4b56: route hotness counted per selection, halved every 16 decode tokens; lowest-hotness victim with recency tie-break; current selection and in-flight entries protected | https://github.com/antirez/ds4/blob/main/ds4_metal.m | 2026-09-06 | R |
| C22 | ds4 opens the model with plain `open()` and streams experts with `pread` and `F_RDADVISE`; no `F_NOCACHE` anywhere in `ds4.c` or `ds4_metal.m` at 90aa4b56 | https://github.com/antirez/ds4/blob/main/ds4.c | 2026-09-06 | R |
| C23 | ds4-bench generation rate = generated tokens ÷ time from the end of prefill, so it includes the first decode step | https://github.com/antirez/ds4/blob/main/ds4_bench.c | 2026-09-06 | R |
| C24 | ds4's CUDA streaming cache is LRU over slots; its hotness reset is a stub | https://github.com/antirez/ds4/blob/main/ds4_cuda.cu | 2026-10-05 | R |
| C25 | ds4's README discloses strong assistance from AI coding agents | https://github.com/antirez/ds4 | accessed 2026-10-15 | 1P |
| C26 | Kimi-K2 at 1.7 tokens/s on an M4 Max 128 GB (rustane); `F_NOCACHE` raised 1.15 to 1.68 because the page cache evicted backbone weights | https://themenonlab.blog/blog/kimi-k2-1t-macbook-rustane | 2026-03-25 | 1P |
| C27 | Kimi-K2-Instruct 4-bit at 0.5 tokens/s on a 128 GB M3 Max with an MLX pread streamer | https://github.com/rita-aga/mlx-turboquant-moe-streaming | 2026-03-26 | 1P |
| C28 | Kimi K3 at 1.0015 tokens/s steady decode on an M5 Max 128 GB from four SSDs | https://github.com/argonautlabsai/deltafin | 2026-09-08 | 1P |
| C29 | llama.cpp GPU LRU cache for MoE experts kept in host memory; hit rates logged at exit; merged 2026-10-07 | https://github.com/ggml-org/llama.cpp/pull/29887 | 2026-10-07 | R |
| C30 | llama.cpp b11669 supports `deepseek2`, `glm-dsa` and `deepseek4`; every MoE layer emits a tensor named `ffn_moe_topk-` plus the layer index; the stock evaluation callback prints three edge values per dimension | https://github.com/ggml-org/llama.cpp/tree/b11669 | 2026-10-15 | R |
| C31 | vLLM v0.31.0 has `--enable-return-routed-experts` (per-request routed expert ids) | https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/layers/fused_moe/routed_experts_capturer.py | v0.31.0 | R |
| C32 | Intelligence Index v4.3.2: Kimi K2.6 27, DeepSeek V4 Flash 0731 34, GLM-5.3 45 | https://artificialanalysis.ai/models/comparisons/deepseek-v4-flash-vs-kimi-k2-6 | accessed 2026-10-15 | 1P |
| C33 | GLM-5.3 IQ2_XXS (antirez, rev 1434dad1): 211,075,860,864 bytes, SHA-256 059b36ac, no licence tag on the repository (upstream GLM-5.3 Licence) | https://huggingface.co/antirez/glm-5.3-gguf | 2026-08-31 | R |
| C34 | DeepSeek-V4-Flash Vision-Exp MXFP4 (antirez, rev f71f23d5): 155,976,459,136 bytes; MIT | https://huggingface.co/antirez/deepseek-v4-gguf | 2026-08-31 | R |
| C35 | Workload licences by Hub tag: WildChat-1M ODC-BY; oasst2, bigcodebench, BFCL, ToolACE, LongBench-v2 and narrativeqa Apache-2.0; SWE-agent-trajectories CC-BY-4.0; SWE-smith-trajectories and longmemeval-cleaned MIT | https://huggingface.co/datasets/allenai/WildChat-1M | read 2026-10-15 | R |
| C36 | Che's approximation is accurate for LRU under general popularity laws | https://arxiv.org/abs/1202.3974 | 2012-02-17 | A |
| C37 | Cold-start references dominate short trace samples (miss ratio 0.40 against 0.02 overall); DOI 10.1145/107971.107981; cited through its OpenAlex record because the DOI page returns 403 to scripted fetches | https://api.openalex.org/works/doi:10.1145/107971.107981 | 1991 | A |
| C38 | A simulator calibrated on microbenchmarks reached under 20% error only on held-out macro workloads; DOI 10.1145/379240.565338; cited through its OpenAlex record because the DOI page returns 403 to scripted fetches | https://api.openalex.org/works/doi:10.1145/379240.565338 | 2001 | A |
| C39 | Trace-driven simulation misleads when event order depends on timing (multi-stream); DOI 10.1145/166955.167001; cited through its OpenAlex record because the DOI page returns 403 to scripted fetches | https://api.openalex.org/works/doi:10.1145/166955.167001 | 1993 | A |
| C40 | The ECM model states its overlap hypothesis explicitly and validates data volumes separately from time | https://arxiv.org/abs/1509.03118 | 2015-09-10 | F |
| C41 | Kimi-K2.6 INT4 is on the host with a receipt cross-checked against the Hub (96 files, 595,204,999,341 bytes) | program/evidence/2026-10-16/kimi-k26-fetch/README.md | 2026-10-15 | M |
| M1 | The whole-layer appends (30.8, 34.4, 34.9 s for 16, 43, 114 tokens) are full passes over 186.86 GB, so B for whole-layer reads is about 5.4-6.1 GB/s (6.08 with 16-token compute removed) | compute/identification-g2stream.json | 2026-10-15 | D |
| M2 | With that B and e = 0.61, the dossier null (A6 + A7) under-predicts 10 of 11 generation rows (G = 1.415) and predicts a ratio of 1 for every within-run contrast (observed 1.25-1.63); with B free in 5.85-10.6 GB/s its interval contains 9 of 11 | compute/identification-g2stream.json | 2026-10-15 | D |
| M3 | The four simulators pass Che's approximation within 0.01, LRU inclusion, ds4-without-hotness ≡ LRU, and Belady ≥ every online policy, on seeds 42-44 | compute/sim-g2stream.json | 2026-10-15 | D |

## Closest Prior Work

1. **Anemll Flash-MoE llama.cpp fork and its bank-modeling workflow** (C06-C08; read in full at
   `a809594f`). It is the same pipeline shape on the same model family and target machine:
   - Kimi-K2.5 routing traces on an M5 Max;
   - per-layer static, global static and refillable-LRU simulation;
   - throughput calibrated against the same engine's anchors.

   Its measurements are one prompt of 100 tokens, mostly at top-4, from a cold start. Its workflow
   example is one prompt generated to 12,000 tokens with EOS ignored. It publishes no estimator
   outputs, no held-out test against independent measurements, and no workload diversity. **This
   is the closest prior used for blind discrimination.**
2. **S82, "Who Should Own the Expert Cache?"** (2608.12103; C09, C10; F\*). It has locality and
   fair-window LRU, LFU, static and Belady curves for K3 and DeepSeek-V3, which bracket K2, and a
   Darwin page-cache replay of Qwen3-30B. It has no K2, no time model, no Mac speed prediction, and
   only 299-300 decode tokens per domain.
3. **"Quantization as Cache Amplification"** (Zenodo 10.5281/zenodo.21856981; C14; A). It projects
   an unexecuted 1T MoE on a laptop from measured host terms and an OLMoE-validated cache model, with
   no real 1T traces and no check against a real 700B-class streaming measurement.
4. **Others that narrow the delta:**
   - Patterns behind Chaos (C03, K2-Thinking traces, no hit rates);
   - S123 (C11, the replay protocol, adopted);
   - FreeToken (C12, agentic LRU misses for other models);
   - 2609.14864 (C13, Apple in-memory decode prediction);
   - Cacheable-by-Design (bytes ÷ bandwidth on a PC);
   - ds4's own docs (the validation target, C19-C23).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| K2-family per-token, per-layer routing traces | Chaos dataset (C03); REAP observer (C05); Anemll `--moe-trace` (C08) | Per-layer expert ids per token on a K2-architecture model | K2.6 Q2 file a Mac would stream; chat, coding, agentic and long-document sessions with up to 2,048 decoded tokens, the model's own responses, diversified templates; teacher-forced and autoregressive paths compared | high |
| K2 hit-rate curves under several policies | Anemll (C06: one prompt, per-layer LRU, 100 tokens); S82 (C09: K3 and DeepSeek-V3) | LRU on a K2 model (Anemll); policy comparison with Belady (S82) | Event-atomic curves for E = 384, k = 8 from 5% to 50%, with ds4's decayed-hotness policy, LFU, out-of-sample static and Belady, cold-start and warm windows, per-session distributions | high |
| Replay and reporting protocol | S123 (C11) | Event-atomic replay, template diversity, union-to-capacity, cluster bootstrap | None claimed; adopted | n/a |
| Three-tier time model (engine cache, OS file cache, SSD) with the engine's own policy, cold start and two prefill paths | Dossier A6 (two terms, no state); Zenodo roofline (C14); Anemll workflow (C08); S82's page-cache tiering (C10) | Bytes ÷ bandwidth plus a cache model; page cache as a tier (S82, rustane C26) | The file-cache tier bounded by the engine's logged available memory, because the engine reads without `F_NOCACHE` (C22); the engine's exact policy and prefill paths; exactly one fitted constant, fitted on a prompt-independent whole-pool read | medium |
| Held-out validation against third-party measurements on the target machine | 2609.14864 (C13, in-memory Apple); MoE-Lens and ServeTwin (GPU servers); Anemll (in-sample anchors) | Held-out error of a calibrated performance model | Streaming on Apple; cross-model holdout; three within-run contrasts with identical routing in which the shared calibration error cancels; a frozen null that the contrasts falsify by construction (M2) | medium |
| Kimi K2.6 Mac prediction as a matched ratio to a measured incumbent, wired to a program decision | Dossier K2 row (brackets); measured Kimi-on-Mac anchors (C06, C26-C28) | A Kimi Mac speed estimate | A validated prediction (or none) for a ds4-class engine at Kevin's memory scenarios, reported as R against GLM 5.3 on the same sessions, with a pre-registered rule that closes or opens G1, G3 and G5 | medium |

Novelty wording: No direct prior art found through 2026-10-15 under the coverage in the header:
- the 57 orx discover records, 3 OpenAlex lookups, 7 web searches, 8 GitHub searches and 7
  Hugging Face searches listed with their returned ids in `query-log.json`;
- full-text reads of 2608.12103, 2608.07911, 2510.05497, 2609.14864, 2608.16157, 2609.18110,
  2609.29032 and 2609.18063;
- the Anemll repository at `a809594f` and ds4 at `90aa4b56`.

That statement covers the combination of event-atomic Kimi K2 hit-rate curves on chat, coding,
agentic and long-document sessions with long decode, and an engine-faithful three-tier streaming
emulator validated on held-out ds4 M5 Max measurements. The merged verdict is NARROWED. Recombination
risk for the novelty refuter: the emulator half could be called Anemll's workflow plus S82's
policies plus 2609.14864's held-out discipline; the delta then rests on the file-cache tier, the
contrast-based validation and the K2 workload curves.

Blind discrimination packet: `evidence/2026-10-16-g2-kimi-expert-streaming/blind/` (two anonymized
mechanism paragraphs in a seeded order; roles in `compute/blind-roles.json`, recorder only).

## Mechanism and Falsifiable Predictions

**Mechanism.** On a unified-memory Mac that streams experts, the time per decoded token is set by
how many of the token's 60 × 8 routed experts are missing from the engine's cache, where each miss
is served from, and how much serialized work each layer does. All three depend on cache state, not
only cache size:
- **State dependence.** The state follows the routing of the session so far: the prompt, prior
  turns, prefill path and cold start. It is shaped by the engine's policy, here decayed route
  hotness with recency ties.
- **Where a miss is served.** Because ds4 reads through the macOS file cache (C22), a miss that
  was read recently and still sits in the file cache costs a memory copy, not an SSD read. The file
  cache's capacity is whatever memory ds4 leaves available (15.05 GiB and 27.87 GiB in ds4's logs).
- **Consequences.** Speed is not a function of cache size alone (6.14 tokens/s at 16 GiB on a
  repetitive prompt, 5.11 at 61.35 GiB on a code prompt) and differs within a run between cold and warm windows (V4
  Flash 11.9 against 19.3; GLM 3.78 against 5.11). It also depends on whether an append streamed
  the whole pool through the file cache (4.09 against 5.11 with identical routing).
- **What follows.** A model that knows the routing, the engine's policy and the tiers should
  reproduce these effects with one bandwidth constant. A model that knows only cache size (the
  dossier's A6/A7) cannot.

Predictions, falsifiers and kill criteria (registration section 7 has the exact rules):
- **PR1 (locality).** ds4's policy at 22% of the pool reaches h ≥ 0.70 in every workload.
  - Falsified if any workload's 95% cluster-bootstrap upper bound is below 0.70.
  - Expected to hold with margin: M2 suggests A7 is pessimistic for ds4's engine, though part of
    that gap may be the file cache serving misses rather than higher h.
- **PR2 (policy ordering).**
  - At 22% and 32%, ds4's policy ≥ LRU ≥ an out-of-sample static set, in mean and in at least
    three of four workloads.
  - Belady exceeds LRU by at least 0.10 at 14%.
  - Falsified by any reversal whose session-bootstrap CI excludes 0.
- **PR3 (the file-cache tier is needed).** The two-tier ablation (no file cache, everything else
  equal) misses at least one primary contrast K1-K3 by more than 15%. Falsified if the two-tier
  ablation passes all three; the tier is then unnecessary and is dropped from the Kimi predictions.
  - Context from the synthetic simulation (E = 384, reuse calibrated to S82): the expert-cache
    cold-start deficit at 22% is only 0.04 over the first 64 decoded tokens and 0.02 over 128.
  - Decode time is steep in h, though: one point of h moves V4 Flash's time per token by about 7-11%
    (V8, V9) and GLM 5.3's by about 5% at B ≈ 6 GB/s.
  - Whether cold start alone can carry K1 (1.625) therefore depends on the real traces. The cold
    deficit itself is reported with its CI.
  - PR3's reading is conditional on P0 settling ds4's whole-layer prefill path. If P0 cannot, both
    variants are bracket corners.
- **PR4 (emulator, contrasts).** The three primary within-run contrasts are reproduced within ±15%
  with the observed sign:
  - K1 = V9/V8 = 1.625;
  - K2 = V5/V5b = 1.249;
  - K3 = V5/V5i = 1.352.

  The frozen null predicts 1.0 for each and fails by construction. A fail is reportable.
- **PR5 (emulator, levels).** Over the 11 held-out generation levels:
  - the geometric-mean absolute ratio error is at most 1.20;
  - every level lies within ±20% × (1 + ε_i), with ε = 0.10 for medians or repeats and 0.15 for
    single runs;
  - the mean absolute log error is below the frozen null's (0.347, G = 1.415).
- **PR6 (decision).** Q3 runs only if PR4 and PR5 hold (VALIDATED), or PR4 alone holds
  (CONTRASTS_ONLY; then R is reported but absolute speed is not). Its decision rule is fixed in
  advance (Cheapest Decisive Pilot).
- **PR7 (trace equivalence).** On the same token sequences:
  - autoregressive and teacher-forced routing agree at mean top-8 overlap ≥ 0.95 with |Δh| ≤ 0.01
    at 22%;
  - CPU and CUDA llama.cpp agree with |Δh| ≤ 0.02.

**Kill criteria** (registration section 7):
- **KC1.** The simulator disagrees with llama.cpp's own logged LRU hits on the same run beyond
  documented semantics: a bug; stop.
- **KC2.** llama.cpp's teacher-forced top-1 agreement with ds4's published official continuations
  is below 0.60 for a validation model. That model's traces are invalid; if it is GLM 5.3, the
  emulator half stops.
- **KC3.** CPU-against-CUDA |Δh| exceeds 0.03 on the validation conditions. The validation is
  uninformative; stop the emulator half.
- **KC4.** The validation reads FAILED or LEVELS_ONLY. No Kimi speed and no R is reported.

## Cheapest Decisive Pilot

Runs before 2026-10-21 on the CPU lane and GPUs 1-5. It needs no GPU 0 and no Moonshot remote code
(registration sections 4-5). Caps total 7.45 GPU-h; about 4.1 expected.

- **Preconditions:**
  1. Kevin's go-ahead for 707.5 GB of downloads (the three GGUFs, Hub revisions pinned).
  2. A llama.cpp b11669 image built on the program's research base in a CPU-only build job.
  3. The `cb_eval` routing-dump tool written, CPU-tested against `llama-imatrix`'s per-expert counts
     on a small MoE GGUF, reviewed and committed.
  4. ds4's cache policy ported to Python from `ds4_metal.m` at `90aa4b56`, with attribution (MIT),
     and unit-tested.
- **P0 (CPU, 0 GPU-h).**
  - Simulators (LRU, LFU, ds4 policy, static, Belady; event-atomic) with the unit tests already
    passing on synthetic data (M3).
  - The three-tier emulator with its constants fixed in advance (registration section 8).
  - The null's predictions frozen (M2).
  - The REAP observation tables (under 1 GB, JSON only) read for an INT4 popularity reference.
  - Read the ds4 source at `90aa4b56` to settle whether the whole-layer prefill path inserts into,
    bypasses or flushes the expert cache. If the code does not settle it, both variants become
    bracket corners.
- **P1 (CPU lane, 0 GPU-h; 3-GPU fallback cap 1.95).** In llama.cpp CPU, trace GLM 5.3 IQ2_XXS and
  V4 Flash Vision-Exp MXFP4 on ds4's inputs:
  - exact for V1 and V2;
  - `promessi_sposi.txt` with the fixed greedy probe for the ds4-bench rows;
  - the candidate code-audit file for the 61.35 GiB rows.

  Then:
  - check input fidelity: token counts (463 for V1) and the apple string;
  - check runtime correctness: teacher-forced top-1 agreement with ds4's official continuations;
  - trace 32 matched GLM sessions (8 per workload) for R.
- **P2 (GPUs 1-5, cap 5.0 GPU-h).** Trace Kimi K2.6 UD-Q2_K_XL over 64 sessions, 16 per workload,
  with autoregressive decode up to 2,048 tokens with thinking on:
  - greedy for all sessions; seeds 42-44 sampled on 8 of them;
  - a teacher-forced re-pass of 16 sessions (PR7);
  - Anemll's prompt at top-8 and top-4 with a 64-slot per-layer LRU as a cross-check (X1).
- **P3 (1 GPU, cap 0.5 GPU-h).** K2.6 Q2 with experts in host RAM and llama.cpp's GPU expert cache
  (C29), on 4 sessions. The simulator must reproduce the engine's logged hit counts from the same
  run's trace (KC1). This validates h independently of any bandwidth.
- **Readouts.**
  - Q1's curves and PR1-PR3, PR7.
  - The validation verdict: VALIDATED, CONTRASTS_ONLY, LEVELS_ONLY or FAILED, with a FRAGILE flag
    if it changes across bracket corners.
  - If allowed, the K2.6 predictions and R.

**Decision rules (fixed now).** R is Kimi K2.6 Q2 decode over GLM 5.3 IQ2_XXS decode, both
emulated:
- on the 32 matched sessions;
- with ds4's policy;
- at the "all other work stopped" memory scenario (88 GB available) and at the 2026-10-15 reading
  (61.8 GB).

Its 90% interval is the extreme over bracket corners of the session-bootstrap 5th and 95th
percentiles. Kevin's 2 TB drive enters as a B stress corner at 0.5 × B_cal.

| Validation | R | Reading | What happens next |
|---|---|---|---|
| VALIDATED or CONTRASTS_ONLY | upper bound below 1 in both scenarios | KIMI_DOMINATED: on this Mac, streamed Kimi K2.6 is slower than streamed GLM 5.3, and GLM 5.3 also scores higher (C32) | Recommend closing the Mac rationale of G1, G3 and G5; the full study is not run; G2 reports and stops |
| VALIDATED or CONTRASTS_ONLY | lower bound at least 1 in the all-stopped scenario | KIMI_COMPETITIVE | Full study F0-F5 (INT4 equivalence, 256 sessions, top-6 and top-4 for G5) |
| VALIDATED or CONTRASTS_ONLY | otherwise | UNRESOLVED | Full study F0-F4 to narrow R; F5 waits |
| LEVELS_ONLY or FAILED | not computed | EMULATOR_NOT_TRUSTED | Q1 curves only; the dossier keeps its brackets and says host emulation is unvalidated; F1-F3 (INT4 locality) run only if Kevin wants the locality characterization for G5 |

Absolute Kimi tokens/s is reported only under VALIDATED, at both memory scenarios and both file
geometries (Q2, about 2.6 bits; about 2 bits with Q2 routing borrowed).

### The full study the pilot gates (proposed; registered separately)

- **F0.** A vLLM 0.31.0 routed-experts capture smoke test on Qwen3.6-35B-A3B (1 GPU).
- **F1.** INT4 at TP8 with `--enable-return-routed-experts` and prefix caching off, over 256
  sessions (64 per workload), after GPU 0 frees and the remote tokenizer is reviewed.
- **F2.** An INT4 teacher-forced re-pass, comparing decode with prefill routing.
- **F3.** Q2 teacher-forced on the INT4 token sequences. Q2 may stand in for INT4 only if |Δh| ≤ 0.02
  at 14%, 22% and 32% in every workload.
- **F4.** The GLM 5.3 matched sample at 256 sessions.
- **F5.** Q2 at top-6 and top-4 (`--override-kv deepseek2.expert_used_count`) as G5's hit-rate and
  speed input.
- **F6.** An optional Q8_K_XL numerics arm.
- **F7.** One against four streams, with timing in the loop and bracketed interleavings.

Total 15.3-41.0 GPU-h, cap 50 (`compute/caps-g2stream.json`).

## Controls, Baselines, and Ablations

- **Frozen null (the comparator for every validation claim).** The dossier's A6 with h from A7's
  cache-share bracket midpoint, the same calibrated B and e = 0.61. Its predictions were computed
  and committed before any trace exists (M2, `identification-g2stream.json`).
- **Emulator ablations,** each reported on the same holdouts:
  - no file-cache tier (two tiers);
  - no cold start (warm steady-state h only);
  - LRU in place of ds4's policy;
  - one prefill path for both arms of K2;
  - B fitted per target, as an upper bound on what a free constant can absorb.
- **Policy baselines:** LRU, LFU, static pinned out of sample (fit on a disjoint calibration split
  per workload), and Belady (event-atomic; also with bypass) as the offline bound.
- **Cache scope:** global pool and equal per-layer quotas both reported (S82 found them within
  2.7 points at K3).
- **Decomposition:** each session's trace shuffled within the session (an IRM null), so measured
  minus shuffled h is the temporal-reuse share.
- **Trace equivalence** (PR7):
  - autoregressive against teacher-forced on the same tokens;
  - CPU against CUDA llama.cpp (a proxy for the Metal divergence that cannot be measured);
  - INT4 against Q2 in the full study (F3).
- **Fidelity:**
  - the simulator against llama.cpp's own logged LRU hits (P3);
  - the dump tool against `llama-imatrix` counts;
  - input token counts against ds4's (463 for V1).
- **External cross-check X1 (not a gate):** Anemll's prompt at top-8 with 64 per-layer LRU slots
  from a cold start, on K2.6 Q2. Anemll measured 67.2% on K2.5 TQ1_0 (first-party, one run). A gap
  over 0.08 is reported and discussed, not acted on, because the checkpoint and quantization
  differ.
- **Sampling sensitivity:** greedy against seeds 42-44 at the model card's recommended sampling on
  8 sessions; the h spread across seeds is reported per workload.

## Evaluation, Statistics, and Leakage Checks

- **Unit and estimand.** The session is the unit. h is pooled over layers within a session (event
  counts), then averaged over sessions within a workload. Workloads are reported separately and
  pooled only as an equal-weight mean of the four.
- **Intervals.** Cluster bootstrap over sessions (2,000 resamples, seed 42), never over tokens:
  hit indicators are autocorrelated, with 80-85% reuse within 64 tokens (C09).
- **Distributions.** Per-session P10, median and P90, plus per-workload policy win counts (the
  S3-FIFO reporting style).
- **Phases.** Cold-start (first 128 decoded tokens) and warm windows are reported separately;
  reasoning and answer spans are split where the template marks them.

**Validation rule** (registration section 8):
- **Calibration.** Exactly one constant, B for whole-pool reads, is calibrated on CAL-B (the
  16-token whole-layer append, 30.8 s, a three-run median whose cost is prompt-independent). It is
  checked for consistency on the 43- and 114-token whole-layer appends.
- **Constants fixed in advance:**
  - e = 0.61 (ds4's in-memory Metal decode, A2);
  - the file-cache capacity, equal to ds4's logged minimum available memory where published, or
    128 GiB minus ds4's planned memory minus 20 GiB for the OS;
  - a 30 GB/s file-cache copy rate;
  - selected-expert reads at the calibrated B;
  - file-cache state set by each target's protocol (warm for discarded-warm-up medians, cold at
    the start of ds4-bench runs).
- **Brackets.** Corners: e 0.55-0.61; copy rate 15-60 GB/s; capacity × 0.5-1.0; first-step page-in
  of the non-routed weights 0 or a full spine read; both prefill-path variants if P0 cannot settle
  them. A verdict that holds at the central constants but not at every corner is FRAGILE.
- **Holdouts.**
  - Levels: V2, V3, V4, V5, V5i, V5b, V5bi, V6, V7, V8, V9 (`compute/ds4-targets.json`).
  - Primary contrasts: K1, K2, K3.
  - Prefill levels (V1, V3p, V4p, V8p, V9p) and append latencies are secondary, because 2609.14864's
    prefill model failed on Apple.
- **Fidelity strata.** Each target is labelled EXACT, PROBABLE or CANDIDATE by input fidelity. The
  verdict is computed on all holdouts and again on EXACT plus PROBABLE only. Disagreement is
  reported as "input-fidelity-limited".

**Single-run noise.** Each target is an interval, not a point. Per-target allowances:
- ε = 0.10 for three-run medians and for conditions measured on both machines;
- ε = 0.15 for single runs.

Grounds:
- ds4's own regression floors sit about 10% below its three-run reference medians (5.5 against
  6.14, 11.3 against 12.59; C20);
- the same condition on ds4's two machines differed by 1.9-3.8% in generation and 4.5-8.0% in
  prefill (C20).

The ±40% single-shot spread of C18 comes from a 16 GB machine under memory pressure and is not
adopted. Its applicability is stated as a limitation. Within-run contrasts cancel machine-level
noise and the shared calibration error, which is why they are primary.

**Operating characteristics** (`compute/sim-g2stream.json`, seeds 42-44, synthetic; before any
data).

**Simulators.** The unit tests pass on all three seeds:
- Che's approximation holds within 0.0031-0.0053 at 20-192 slots;
- LRU satisfies inclusion;
- ds4's policy with hotness disabled equals LRU event for event;
- Belady upper-bounds every online policy.

**Synthetic routing.** E = 384 and k = 8 with Zipf α 0.9. A reuse knob ρ = 0.25 reproduces S82's K3
reuse: 0.32 after 1 token and 0.80 within 64 tokens.

| Quantity | 14% of pool | 22% of pool |
|---|---:|---:|
| h, ds4 policy | 0.63 | 0.69 |
| h, LRU | 0.61 | 0.68 |
| h, out-of-sample static | 0.43-0.47 | 0.51-0.55 |

ds4's policy beats LRU by about 0.008-0.022.

**Between-session spread.** The synthetic between-session SD of h is 0.005-0.006 for the dynamic
policies and 0.03-0.04 for the static one. That is a floor: synthetic sessions differ only by
hot-set permutation, while real sessions also differ by template and phase (S123: 19-32 points).
The pilot therefore sizes n from an assumed real SD, and measures it:
- the half-width of a 95% CI is 1.96 × SD ÷ √n, so n = 16 per workload gives ±0.025 at SD 0.05 and
  ±0.039 at SD 0.08;
- the full study's 64 per workload gives ±0.012 and ±0.020.

**Cold start.** At 22% of the pool, with ds4's policy, compulsory first touches are a large share
of selections in short windows, but the hit-rate deficit they cause is small:

| Decoded tokens | Compulsory share of selections | Cold h | h after 2,048 tokens of warm-up |
|---:|---:|---:|---:|
| 64 | 31% | 0.648 | 0.687 |
| 128 | 23% | 0.674 | 0.694 |
| 512 | 9% | 0.686 | 0.707 |

**Validation rule.** Monte Carlo with 20,000 replicates per row. It models the 11 levels with
observation noise of 0.035 log for medians and repeats and 0.07 for single runs. The calibration
row's noise propagates into every level with gain 0.6.

The levels test passes:

| Emulator bias | Spread 0.05 | Spread 0.10 | Spread 0.15 | Spread 0.25 |
|---|---:|---:|---:|---:|
| none | 0.999 | 0.90 | 0.47 | 0.04 |
| 10% | 0.96 | 0.61 | 0.25 | 0.02 |
| 20% | 0.40 | 0.15 | 0.05 | 0.01 |
| 28% | 0.006 | 0.007 | 0.005 | 0.001 |
| 42% | 0.000 | 0.000 | 0.000 | 0.000 |

So a systematically biased emulator (28% or more) is falsely validated at most 0.7% of the time. An
unbiased emulator is validated 90% of the time at a 10% spread but only 47% at 15%. The rule is
strict, and a failure does not prove the mechanism wrong.

The primary contrasts pass with probability:

| Mechanism bias | Contrast SD 0.03 | Contrast SD 0.06 | Contrast SD 0.10 |
|---|---:|---:|---:|
| none | 0.79 | 0.67 | 0.42 |
| 10% | 0.22-0.37 (range across SDs) | | |
| 20% or more | 0.03 or less | | |

The ceiling of 0.79 comes from single-run observation noise on K1 (about 0.10 log) against a
±15% band.

The frozen null scores a mean absolute log error of 0.347 on the levels and fails every contrast by
construction. The sensitivity of decode time to h is steep (identification table): at about 6 GB/s,
one point of h moves V4 Flash's time per token by about 7-11% (V8, V9) and GLM 5.3's by about 5%. Passing the
levels test therefore needs h right to within about 0.02-0.04, which is why trace fidelity (PR7,
KC2, KC3) gates the validation.

**Leakage and forking paths.**
- Fixed before any trace is read:
  - the emulator code, constants, brackets and calibration row;
  - the holdout set, the null's predictions and the decision thresholds.
- The traces of calibration and holdout conditions come from the same jobs. The analysis script
  computes B from CAL-B alone and writes it to a hashed file before it reads any holdout trace.
- No constant is refitted after a holdout is seen. Any refit is a new registration id, reported as
  exploratory.
- Kimi sessions are drawn by hash order from disjoint candidate pools. The static policy's
  calibration split is disjoint from its scoring split.
- The REAP observation set and the Chaos traces are used only as external references, never to
  choose sessions.

## Compute and Reproducibility

- **Images.**
  - **llama.cpp.** b11669 (`620d2225`), built offline in a CPU-only build job on the program's
    research base `docker.io/nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed`
    (CUDA 12.8.1 matches the R570 driver; `CMAKE_CUDA_ARCHITECTURES=90`). Its local image id and
    provenance receipt are recorded at P0.
  - **vLLM, full study only.** `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
    (vLLM 0.31.0, commit `db9527a4`).
- **Launch.** Per job: `python3 scripts/submit_docker_research_job.py manifests/g2stream-p2.yaml --dry-run`, then `--test-only`, then submit. That runs
  `sbatch infra/slurm/host-single-node/docker-research.sbatch` with the job's GRES and limit. P1 runs
  on a CPU lane (no GRES), like `fetch-model-cpu.sbatch`. Each pilot job is an orx `slurm-manifest`
  node run with `uv run --locked python scripts/orx_run.py`, never `orx --backend slurm`.
- **Seeds:** seeds: [42, 43, 44]. Session draws use `numpy.random.default_rng(42)` over candidates
  sorted by SHA-256. Seeds 42-44 cover the sampled continuations, synthetic simulations and
  bootstraps (bootstrap seed 42). Greedy decoding is used everywhere else.
- **GPU budget.** gpu_hours: 8 (the pilot ceiling; Slurm caps 7.45, about 4.1 expected). The full
  study's proposed cap is 50 GPU-h (15.3-41.0 by arithmetic), re-derived from P2's measured
  throughput.
- **Checkpoints and preemption.** Traces are written per session as soon as the session completes,
  with an index of completed session ids. A preempted or timed-out job restarts as a fresh job that
  skips completed ids. The resume-equivalence test is that a session's trace from a resumed job is
  byte-identical to one from an uninterrupted job (P2's first two sessions are run twice, the second
  time after a forced kill). No model state needs checkpointing.
- **Artifacts.**
  - On the host: raw traces as int16 expert ids (about 5 GB for the pilot), token ids and
    per-session JSON summaries.
  - In the repository: aggregate curves, per-session h, the emulator's predictions with every
    constant, the trace-equivalence tables, and SHA-256 manifests. Raw traces stay on the host
    because they derive from licensed conversations.
- **This bundle's CPU evidence** (synthesis, Mac CPU only):
  - `compute/sim_g2stream.py`, `sim-g2stream.json`: simulators, unit tests and operating
    characteristics;
  - `compute/identification_g2stream.py`, `identification-g2stream.json`: the B identification,
    the null and the Kimi sensitivity;
  - `compute/caps_g2stream.py`, `caps-g2stream.json`;
  - `compute/ds4-targets.json`: targets, roles, fidelity, sources.

## Safety, Data Rights, and Monitorability

- **Licences.**
  - Kimi K2.6 and its Unsloth GGUF: modified MIT (attribution clause above 100M MAU or US$20M per
    month).
  - GLM-5.3: the upstream GLM-5.3 Licence (MIT-style; review only for model-as-a-service operators
    above US$10B revenue). The antirez repository has no licence tag, which is recorded.
  - V4 Flash Vision-Exp: MIT. ds4 (read and ported, never run): MIT, with attribution in the port.
  - Datasets (C35): WildChat-1M ODC-BY (attribution); oasst2, bigcodebench, BFCL, ToolACE,
    LongBench-v2 and narrativeqa Apache-2.0; SWE-agent-trajectories CC-BY-4.0; SWE-smith and
    longmemeval-cleaned MIT.
  - Excluded: datasets without a clear licence tag (SWE-bench_Verified, livecodebench, quality), and
    unlicensed K2.6 trace sets.
  - The Chaos traces have no licence. They are not redistributed and are used only if Kevin accepts
    their gate.
- **Host rules.**
  - Stock llama.cpp at a pinned tag in a digest-pinned image. The only new code is a reviewed,
    committed CPU-side `cb_eval` dump tool with no GPU kernel. ds4 is never run.
  - GPUs 1-5 only, never GPU 0 or the D110 hosting jobs; no sudo; `~/cotcodec` untouched.
  - The gauntlet itself submits only the open-weight reviewer's lane job.
- **Public repository.** No host addresses, credentials or raw conversation text; aggregates only.
- **Outward actions.** None by this work. The 707.5 GB of downloads await Kevin's go-ahead.
- **Monitorability.** Every job logs its resolved model revision, file SHA-256, token counts, its
  per-layer routing entropy (a degeneracy check) and llama.cpp's logged cache statistics.

## Negative-Result Value

- **FAILED or LEVELS_ONLY.** The program learns that host-side emulation cannot stand in for Mac
  streaming measurements, even with the engine's policy, the file-cache tier and a prompt-independent
  calibration. Every streamed-model speed in the dossier is then labelled an unvalidated estimate.
  That is a correction of record, and the cheapest one available without a Mac run.
- **KIMI_DOMINATED.** Closes the Mac rationale of the dossier's 93-759 GPU-h of Kimi compression work
  (G1, G3, G5) with a matched, validated comparison instead of an index score alone.
- **PR1 falsified** (h below 0.70 at 22% in some workload). The dossier's Kimi range is optimistic
  where it matters, and the workload that breaks it is named.
- **PR2 or PR3 falsified.** Ranks ds4's policy against LRU and static sets on a 384-expert model, a
  design input for any Kimi Mac streamer, Anemll's included.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable; 82 counted searches with returned ids in `query-log.json`; cutoff 2026-10-15; degraded coverage recorded (orx outdated; gated trace files unread; no X, Reddit, OpenReview, Chinese-language sources, patents or citation graphs) (`doctors/source.json`) | A Semantic Scholar citer refresh for 2608.12103 and 2510.05497 through the host relay; a Chinese-language search for Kimi routing locality |
| Citation | PASS | Claim registry C01-C41 and M1-M3 with URLs, dates and read levels; every URL snapshotted with HTTP status and body hash (all HTTP 200; the three ACM papers are cited through their OpenAlex records because their DOI pages return 403 to scripted fetches); first-party numbers labelled 1P; two cell readings corrected after re-reading (Anemll counters; dossier S51) (`doctors/citation.json`) | Replace first-party ds4 and Anemll numbers when replicated |
| Novelty | FAIL | NARROWED by two independent cells; no direct prior under the recorded coverage; the blind critic and the novelty refuter have not run; closest prior (Anemll workflow) read in full (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter within the remaining query budget |
| Design | PASS | Self-assessed; the identification refuter has not run. One calibrated constant on a prompt-independent row; frozen null; primary within-run contrasts; fidelity strata; bracket corners; kill criteria KC1-KC4; falsifiers PR1-PR7; simulated operating characteristics (`doctors/design.json`) | Identification refuter; pre-freeze audit of the registration |
| Compute | FAIL | No llama.cpp image, dump tool, manifest, container smoke, Slurm dry run or test-only run exists; the deterministic doctor's real-model-loop and adapter checks fail; the pilot's caps (7.45 GPU-h) and the full study's arithmetic are in `compute/caps-g2stream.json` (`doctors/compute.json`, `compute/attestations-not-run.md`) | P0 build, dump tool and selftests, manifests, dry runs and test-only runs before a freeze; Kevin's download go-ahead |
| Safety | PASS | Permissive or attributed licences with exclusions; R570 respected (stock llama.cpp, a reviewed CPU-side dump tool, ds4 never run); host and public-repository rules; no outward action (`doctors/safety.json`) | none |

Protocols followed:
- **Citation:** the ARS claim-verification protocol (claim registry, locators, verdicts, first-party
  labels).
- **Design:** the vendored K-Dense `experimental-design` and `statistical-power` skills (design
  before data; one calibration row; sample size and rule operating characteristics by simulation,
  not habit).
- **Evaluation:** K-Dense `statistical-analysis` (cluster bootstrap, intervals, no token-level
  inference).
- **Novelty:** K-Dense `literature-review` (PRISMA counts in the header).

The integrity gate's seven failure modes are answered in the registration's section 14.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only when a GPU among 1-7 is idle and no frozen registration of this program is queued or running; limit 20 minutes)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; the decision-irrelevance kill is answered by re-aiming the decision at G1, G3 and G5 |
| Primary-source evidence | 0 | 0 | not yet reviewed; ds4 and Anemll numbers are first-party |
| Defensible novelty delta | 0 | 0 | not yet reviewed; recombination risk against the Anemll workflow, S82 and 2609.14864 is open |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed |
| Controls and causal identification | 0 | 0 | not yet reviewed; Metal routing divergence is proxied by CPU against CUDA only |
| Evaluation and statistics | 0 | 0 | not yet reviewed; ds4 targets are single runs or medians of three |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; CPU-lane throughput is unmeasured |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no image or manifest exists |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed |
| Independent adversarial review quality | 0 | 0 | not yet reviewed |
| **Total** | **0** | **0** | Lower total is authoritative; caps that bind until fixed: 79 (no executable pilot run), 89 (unsigned reviews, D24) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| wave-1 synthesis (2026-10-15) | not scored | (a) The ±20% check as dossier-written was unfalsifiable: B free, the null's interval covers 9 of 11 targets; (b) G2's Kimi output could not change Kevin's model choice (GLM 5.3 dominates); (c) the dossier and the cells misread three sources (G2 status, S51's engine, Anemll's counters) | (a) One constant calibrated on a prompt-independent whole-pool read; frozen null; within-run contrasts with identical routing as primary tests; file-cache tier added because ds4 reads without `F_NOCACHE`; fidelity strata and bracket corners; (b) decision re-aimed at the Kimi-compression lines through a matched ratio R to GLM 5.3; (c) corrections recorded with sources | awaiting the blind critic, the triad and the reviewers |
