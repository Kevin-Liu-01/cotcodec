# Research Direction: LM1. On a 128 GB unified-memory machine, does a 1T-class open model at about 1.87 bits per weight (Kimi K2.5 UD-TQ1_0, 239.5 GB, streamed from SSD) answer real questions better than the best model that stays resident in memory? The pilot tests the one domain where the 1T model leads at full precision, factual recall, and decides which model Kevin runs locally (pilot of at most 8 GPU-h, then a full study)

**Status:** draft; gauntlet wave 1 synthesis by the single owner on 2026-10-16 (branch `gauntlet/lm1-matched-memory-quality`, not pushed, not frozen); the draft registration for the pilot is `program/preregistrations/lm1-matched-memory-quality-v1.md` (DRAFT, new experiment id, no ledger row); the blind critic, the refute-first triad and the two reviewers have not run; no host job was submitted by the synthesis (one read-only `nvidia-smi` and `squeue` check at 04:29Z); the full study is proposed here and registered after the pilot; downloads over 1 GB and the full study's admission are Kevin's (AGENTS.md rule 9; D24, D92)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification, contract and registration by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-15
**Coverage limits:** orx 0.2.2 (reports itself outdated against 0.2.18). 92 counted searches: 52 orx discover records (alphaXiv keyword and embedding, OpenAlex; several bounded with `--published-after`), 22 web searches (one in Chinese), 2 GitHub repository searches, 3 Hugging Face dataset searches, and 13 searches by the asset cell whose query strings it did not return. Full-text reads with `orx paper --full` of every closest prior (2509.25689, 2504.02010, 2604.18556, 2610.15372 by the cells and again by the synthesis owner) and of the mechanism priors 2404.05405 and 2508.10925 (synthesis). Not searched: live X, Reddit and r/LocalLLaMA directly (one snapshot mirror only), Hacker News, OpenReview, ACL Anthology, patents, Chinese-language sources beyond one web search, Semantic Scholar and Google Scholar forward citations of the closest priors (the arXiv API and Semantic Scholar are not reachable from the Mac). Not opened: AA-Omniscience per-model accuracy values (the leaderboard page renders them client-side; only the comparison page's index values were read), the SimpleQA-Verified Kaggle autorater notebook, the training-token counts of Kimi K2 and Qwen3. PRISMA-style: 641 ids returned by the itemized searches (467 unique), screened by title; about 35 read beyond the abstract; 0 direct priors; 4 closest or narrowing priors; about 14 background priors.
**Budgets:** queries=150; wall_minutes=720; tokens=10000000; dollars=150; waves=3; gpu_hours=0.5
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-16-lm1-matched-memory-quality/bundle.json

The budgets are this gauntlet's, cumulative; at least 30 queries are reserved for the three
refuters. The GPU budget (0.5 GPU-h) is for the open-weight reviewer's lane job only; the doctor
reads budgets as integers, parses it as 0 and flags it (left as declared, as in G2). The novelty
verdict field uses the doctor's vocabulary; the merged kill-shot verdict of two independent cells
is **NARROWED**, not OCCUPIED. Host slug: `lm1mmq`. Experiment id of the pilot:
`lm1-matched-memory-quality-v1`.

## Budget accounting (read before the refuters run)

| Cell | orx discover | Web search | GitHub search | Hugging Face search | Counted | Reads (uncounted) |
|---|---:|---:|---:|---:|---:|---|
| Frontier | 24 | 12 | 2 | 3 | 41 | about 20 full or targeted texts, 7 page fetches |
| Kill-shot | 4 | 4 | 0 | 0 | 8 | 3 full texts, 12 fixed-URL fetches |
| Cross-domain | 18 | 6 | 0 | 0 | 24 | 22 full texts, 8 fetches |
| Asset and cost | not itemized | not itemized | not itemized | not itemized | 13 | Hub API reads, GGUF headers, llama.cpp source at `620d2225`, read-only host check |
| Synthesis | 6 | 0 | 0 | 0 | 6 | 7 `orx paper` full texts, 6 abstracts, Hub API and card reads, 2 llama.cpp docs at `620d2225`, 4 AA pages, 1 read-only host check |
| **Total** | **52 + asset** | **22 + asset** | **2 + asset** | **3 + asset** | **92** | |

92 of 150 are used; 58 remain, 28 above the refuters' reserve of 30. Token, wall-clock and dollar
use are metered by the orchestrator over the whole wave; the synthesis spent no dollars and no
GPU time. The synthesis's six searches added the title-phrase queries the novelty rule asks for
(CC-MoE, 2504.02010, 2610.15372) and three knowledge-under-quantization queries; their ids are in
`query-log.json`.

## Scope

- **The pilot** (draft registration v1; Slurm guards 6.9 GPU-h unconditional plus a 1.1 GPU-h
  reserve for top-ups or the conditional thinking arm, line 8.0; `compute/caps-lm1.json`). It runs
  before 2026-10-20 on at most 3 GPUs at a time, never GPU 0, on the six-file host prep that
  already exists (D127). It needs no download. It answers the knowledge question in instant mode,
  the V4 Flash 0731 file choice for knowledge (Q2 against IQ3_XXS), and, only if Kimi leads, whether
  the lead survives a resident model that thinks for the same Mac wall-clock time.
- **The full study** (proposed here, registered after the pilot; 112-606 GPU-h by branch,
  `compute/caps-lm1.json`). It adds the thinking tier on reasoning, coding and tool use, the V4 Flash
  Q8_K_XL reference, stronger resident comparators (Qwen3.8 27B), the current Kimi (K2.6 IQ1_M, 232.4
  GB) and, in the branch where Kimi leads, Kimi's own INT4 reference and top-4 routing. Its size and
  arm list depend on the pilot's reading.

## Merged discovery cells, by mechanism

Four independent cells ran: frontier and novelty, kill-shot, cross-domain (statistics and protocol),
asset and cost. Their findings are merged below by mechanism, not by cell. The synthesis owner
re-opened every source that a decision rests on (marked F\* in the claim registry). Three cell
readings are corrected in place (item 7).

**1. The cross-family, RAM-matched, task-level comparison at 128 GB is open; three priors narrow it.**
- *CC-MoE* (2509.25689; re-read in full). It fits a pruned, mixed IQ1 DeepSeek-V3 into "a strict
  128GB memory limit" (103 GB, over 5 tokens/s on a Strix Halo laptop) but compares it at that tier
  only with the same model's uniform IQ1_M (140 GB) and Q2_K_L (230 GB), on Winogrande, MMLU, CMMLU,
  HellaSwag and GSM8K. Its one cross-family, size-matched row is at about 220 GB (Table 2: R1 quant
  210 GB against Qwen3-235B at 8 bits, 233 GB; AIME24 86.67 / 86.67, GPQA-D 74.24 / 68.18, GSM8K
  96.51 / 84.99), with no runs, seeds or intervals.
- *When Reasoning Meets Compression* (2504.02010, ICLR 2026; re-read). At about 130-141 GB, Unsloth's
  1.58-bit R1 averages 78.7 on AIME24 / FOLIO / Temporal against 81.8 for R1-Distill-Llama-70B in
  BF16, and leads closed-book MuSiQue by 0.7 EM (14.0 against 13.3, 100 items, single pass for R1).
  Its Finding 1: "weight count has a greater impact on LRMs' knowledge memorization than reasoning".
  It does not frame the comparison as matched memory, and the comparator is distilled from the same
  model.
- *GSQ* (2604.18556; re-read). A same-model comparison on Kimi K2.5 at matched size: GSQ at 2.37 bits
  against Unsloth UD-IQ1_M ("2.4bit") on five AgentBench tasks, mean of 3 runs (Table 14). Base 50 /
  69 / 57 / 53 / 52; UD-IQ1_M 40 / 61 / 39 / 41 / 47; GSQ 43 / 63 / 45 / 42 / 49. The largest drop is
  on the knowledge-graph task (57 to 39). Its authors report that "Templating often failed" for the
  GGUF and that evaluating Kimi-K2.5 "became extremely slow and impractical".
- The nearest community data (Unsloth's Aider Polyglot page) puts DeepSeek-V3.1 at TQ1_0 (170 GB)
  at 50.7 and IQ1_M (206 GB) at 55.7 against full-precision Qwen3-235B at 59.6. These are leaderboard
  numbers, not matched memory.
- *Fewer Bits, More Tries* (2610.15372, Apple; 2026-10-11; re-read). Under a hard memory budget, a
  smaller or one-bit model with verified retries recovers coding accuracy, and the break-even number
  of tries is device-specific (one-bit Qwen3.6-27B at K = 4 is 0.83-0.87x as fast as bf16 on an M3
  Max and 1.58-1.67x on an M5 Pro). It is within-family and coding-only, but it is the closest prior
  for the "same machine, same wall-clock" framing, and LM1 adopts a free version of it (item 5).

**2. The cloud session's three findings.**
- (a) **Verified, with one correction.** GSQ's AgentBench comparison exists (Table 14, above). The
  GSQ model there is 2.37 bits, not Table 3's 2.13. GSQ quantizes only the routed experts while
  Unsloth quantizes every layer. No other model family appears in GSQ, so the open question is the
  cross-family one at matched memory.
- (b) **Consistent by arithmetic (first-party, reproduced, not independently measured).** With the
  dossier's split (1,014.7B routed parameters plus 9.34 GB non-routed, from the K2.6 Q2 file), 1.08
  bits per expert weight gives 146.3 GB and 0.83 gives 114.6 GB. Both leave about 13.5 GB for KV and
  runtime under 160 GB (RTX 5090 plus 128 GB RAM) and 128 GB. Both are below IQ1_S's 1.5625 bpw, the
  smallest stock llama.cpp type, so at IQ1_S they imply pruning about 31% or 47% of the experts. A
  resident Kimi is therefore G1's question; LM1's Kimi arm streams.
- (c) **Partly verifiable.** D125 records only that the cloud session ranked LM1 first. No LM3 or
  "routing traces under quantization" alternate appears anywhere in the repository. Its neighbourhood
  is crowded at title level (EAQuant, ExpertQuant, 2606.05688).

**3. The kill-shot's strongest argument, and how the design answers each part.** The kill-shot cell
judged LM1 as posed NARROWED and "close to predetermined":
- *Stale comparators.* On the Artificial Analysis index v4.3.2 (first-party, re-read 2026-10-16),
  Kimi K2.5 scores 23 ("Estimate (independent evaluation forthcoming)"), Kimi K2.6 27, DeepSeek V4
  Flash 0731 34 and Qwen3.8 27B (Xhigh) 33.7 (not estimated); the kill-shot cell read gpt-oss-120b
  (high) at 12 and Qwen3-235B-2507 Instruct at 12 (an AA estimate) on AA's medium-class page, not
  re-opened here. *Answer:* the design is asymmetric. A negative for Kimi needs one resident arm that
  Kimi does not beat by the practical margin; stronger resident models not on the host can only
  strengthen it. A positive needs Kimi to beat every resident arm (an intersection-union test) and is
  labelled provisional until the full study adds Qwen3.8 27B.
- *Speed and reasoning budget.* Kimi's published quality comes from thinking mode with 96K-token
  budgets; on the Mac it decodes at 2.2 tokens/s (Anemll, first-party, top-8, `-c 256`).
  *Answer:* the pilot runs every arm in instant (non-thinking) mode, which is the only Kimi mode a Mac
  user can afford, and adds, if Kimi leads, the resident arm in thinking mode at a token budget that
  matches Kimi's Mac time per item (registration 6.4).
- *Matched memory undefined.* On the host every file sits on GPUs. *Answer:* "matched memory" is an
  eligibility criterion, not a treatment: the same 128 GB machine and the same resident ceiling
  (tiers R-Y, R-T and S below). The streamed arm uses 2.3-3.8 times the file bytes of the resident
  arms, paid for in speed. A byte-matched Kimi (pruned to about 100 GB) is G1/G3, which LM1 bounds by
  dominance.
- *The residual the kill-shot left open* ("does about-1.8-bit Kimi keep the knowledge lead the 1T
  model has at full precision") is LM1's primary question. On the AA comparison page, AA-Omniscience
  is the one knowledge evaluation in the index where the 1T model leads: Kimi K2.6 5 against V4
  Flash 0731 −14.

**4. Knowledge is the 1T model's full-precision edge, and knowledge is what low-bit quantization
removes first. That is the informative crux, and it is not predetermined.**
- *For the 1T arm:* AA-Omniscience index +19 for K2.6 over V4 Flash 0731 (above); Allen-Zhu and Li
  (2404.05405) find knowledge storage of 2 bits per parameter, unchanged by int8, with MoE costing
  only 1.3x in capacity; Kimi K2.5 has about 1,026B parameters (tensor count of the same-architecture
  K2.6 file, dossier) against 284.3B (V4 Flash), 235B (Qwen3) and 116.8B (gpt-oss); its file holds 1.92 Tbit against 0.51-0.83 Tbit for the resident files (my
  arithmetic); 2504.02010 Finding 1.
- *Against it:* the same paper finds that post-training int4 cuts capacity to 0.7 bits per parameter;
  GSQ's 2.13-bit K2.5 loses 12.7 points of GPQA-Diamond and Unsloth's 2.4-bit K2.5 loses 18 points on
  AgentBench KG; Qwen3-235B-2507's card reports SimpleQA 54.3 against 31.0 for Kimi K2 (vendor
  numbers; the jump from 12.2 for the earlier Qwen3-235B is unexplained); a rate-distortion bound
  ties forced compression to factual hallucination (2609.12111, abstract).
- So the two priors point opposite ways. The synthesis's desk forecast, committed before data
  (registration 7.4), is P(NOT_WORTH) ≈ 0.55, P(UNRESOLVED) ≈ 0.30, P(LEADS) ≈ 0.15.

**5. Statistics and protocol (cross-domain cell, adopted as protocol, not claimed).**
- Paired item-level analysis with clustered intervals (Miller 2411.00640); Var[A−B] ≈ p(1−p) per
  single sample, so K ≥ 3 seeded samples per item raise power (Wang 2512.21326).
- "Beats every resident arm" is an intersection-union test with no multiplicity penalty; "is not
  worth it" is a non-superiority test at a pre-specified practical margin, with a Bonferroni penalty
  because any one resident arm may establish it (2609.13714; Lakens).
- Intercurrent events (truncation, parse or template failure, timeout) are handled by a composite
  strategy as primary (ICH E9(R1)).
- Token budgets reverse rankings (2608.12150); low-bit models inflate chains of thought
  (2606.25519, 2606.00206). The pilot's instant tier caps output at 2,048 tokens and reports
  truncation; the thinking tier's budgets are Mac-time-matched.
- Same-machine, same-wall-clock estimand (2610.15372): the resident arms' three seeded samples per
  item cost far less Mac time than Kimi's one, so "resident majority of three against Kimi's single
  sample" is a free secondary estimand.
- Near-tied cross-family rankings flip under benchmark recomposition (2609.00482), so the suite is
  frozen, readouts are per benchmark, and the practical margin is 5 points.

**6. Assets and feasibility** (asset cell; synthesis's read-only host check at 04:29Z on 2026-10-16).
- GPU 0 holds LaMa (job 1451, successor 1556 pending); GPUs 1-2 hold transcreate jobs; GPUs 3-7
  were idle. Under D127 transcreate may hold up to 4 GPUs through 2026-10-20, so about 3 are
  dependable. RAM 1,771 GB, 1,704 GB of it page cache.
- The six GGUFs, the digest-pinned llama.cpp b11669 image and its overlay exist with receipts; the
  smoke test (job 1582) ran all six on 4 GPUs (Kimi: 55.5 tokens/s single-stream, per-GPU peaks
  64.5 / 56.9 / 51.6 / 54.4 GiB summing to 244.1 GB at `-c 4096`).
- **Kimi on 3 GPUs (not tested; the host rule of this gauntlet allows no GPU job but the reviewer's).**
  3 × 79.6 GiB = 238.8 GiB against about 223.1 GiB of weights leaves about 15.7 GiB for CUDA contexts,
  compute buffers and KV. The knowledge items are short (about 220 prompt tokens, answers under 100),
  so 8 slots × 3,072 tokens need about 1.6-3.0 GiB of KV at the F16 MLA layout (70,272-132,736 bytes
  per token, dossier A9). It is plausible but marginal, because layers are 3.7-3.9 GiB each and the
  split must be tuned. The registration fixes the order of attempts: K3 (3 GPUs, all layers on GPU,
  `-fit on -fitc 24576`), then K3+ (`--n-cpu-moe` 2, 4 or 6, which keeps the first k layers' expert
  weights in host RAM, threads and memory bound to the GPUs' NUMA node), then K4 (4 GPUs, only if transcreate
  holds 3 or fewer), then waiting until after 2026-10-20.
- llama.cpp at `620d2225` (re-read): tensor split is EXPERIMENTAL and "not implemented" for
  DeepSeek2, Kimi's architecture, so layer split is the only multi-GPU mode; `llama-server` defaults
  to temperature 0.80, top-k 40 and min-p 0.05, which every request must override; per-request
  `chat_template_kwargs`, `reasoning_effort`, `id_slot` and `cache_prompt` exist; the README warns
  that prompt caching can make logits nondeterministic; `--reasoning-budget N` and
  `--reasoning-budget-message` are server-wide.
- The judge (Qwen3-32B at `9216db57`, AM1's judge) is on the host with a receipt, in the vLLM image
  AM1 used.

**7. Corrections to cell readings.**
- The kill-shot and frontier cells quote both "1.87 bpw" and the dossier's "1.92 bits" for the Kimi
  file. Both are right for different files: 239,537,678,077 bytes × 8 ÷ 1,026.4B parameters = 1.867
  bpw for K2.5 UD-TQ1_0 (LM1's file); 1.92 is K2-Thinking's 246.8 GB TQ1_0 (dossier row K3).
  Unsloth labels the K2.5 file "1.8-bit".
- The frontier cell says the dossier records CC-MoE at 113 GB against the paper's 103 GB. The
  dossier's 113.38 GB is the size of the released moxin file it measured; the paper's "103GB" may
  be GiB. Neither changes LM1.
- The asset cell's plan put the V4 Flash Q8_K_XL reference in the pilot. It does not inform the
  Kimi decision, and at 3 GPUs it would push the pilot past 8 GPU-h in the pessimistic case, so it
  moves to the full study (G4 decomposition).

## Claim and Research Question

Claim scope: `systems-pipeline` (a measurement of deployable configurations; no architecture
claim, no claim about any model's training).

**Target machine.** A 128 GiB unified-memory MacBook Pro M5 Max (Kevin's; the target spec only, no
model runs on it). Default Metal working-set ceiling 107.52 GiB, measured on that machine (dossier
A10, S1).

**Matched memory, defined.** Each configuration c (model × file × runtime) is assigned a tier from
its resident footprint F(c, L) = resident weights + KV at the evaluated context L + 3 GiB of buffers
(the dossier's A10 convention, other work stopped):

| Tier | Rule | LM1 configurations |
|---|---|---|
| R-Y (resident, fits) | F ≤ 95 GiB at L = 32K | V4 Flash 0731 ds4 Q2 (86.7 GB; ds4 plans 81.62 GiB at 32K for the same-size file); gpt-oss-120b MXFP4 (63.4 GB; 64.9 GB at 32K) |
| R-T (resident, tight) | F above 95 and at most 107.5 GiB at the evaluated L | V4 Flash 0731 UD-IQ3_XXS (104.2 GB); Qwen3-235B-2507 UD-Q3_K_XL (104.2 GB, up to about 41K) |
| S (streamed) | file above 107.5 GiB; runs only by streaming routed experts from SSD with spine, expert cache, KV and buffers ≤ 107.5 GiB; needs a streaming engine | Kimi K2.5 UD-TQ1_0 (239.5 GB; Anemll fork, 2.2 tokens/s at top-8, first-party) |
| not eligible | resident set above 107.5 GiB with no streaming engine, or no Mac runtime | e.g. GSQ checkpoints (CUDA-only); V4 Flash Q8_K_XL is measured as a reference, not as an option |

- **Primary view: RAM-matched.** All eligible arms compete: the same machine, the same resident
  ceiling, different file bytes and very different speeds. "The best model that fits" is the best
  arm in R-Y ∪ R-T; "near native precision" applies within it to gpt-oss-120b (native MXFP4) on the
  host, and to Qwen3.8 27B (BF16) in the full study; the V4 Flash and Qwen3 files are quantized
  resident arms.
- **Secondary view: strict fit.** The same decision recomputed with R-Y arms only (ds4 Q2,
  gpt-oss).
- **Reported for every arm:** tier, file bytes, bits per weight, resident footprint, and Mac speed
  (measured where a first-party measurement exists, otherwise the dossier's estimate, labelled).

**Questions.**
- **Q1 (primary).** In instant (non-thinking) mode, on short-answer factual recall
  (AA-Omniscience-Public, 600 items; SimpleQA-Verified, 1,000 items; equal benchmark weights), is
  Kimi K2.5 UD-TQ1_0's accuracy at least 5 points above every resident arm's? Or is it less than 5
  points above at least one of them?
- **Q2 (V4 Flash file choice, G4's knowledge component).** Is ds4 Q2 (R-Y, 86.7 GB) within 2 points of
  UD-IQ3_XXS (R-T, 104.2 GB) on the primary endpoint?
- **Q3 (domain split, secondary).** Is Kimi's standing relative to the best resident arm better on
  SuperGPQA items that need no calculation than on items that do (200 + 200)?
- **Q4 (time-matched, conditional on Kimi leading).** Does the lead survive the best resident arm in
  thinking mode with a 4,096-token budget, which is at least the tokens a resident V4 Flash decodes on
  the Mac in the time streamed Kimi takes per item?
- **Q5 (reliability, secondary).** Is Kimi's hallucination rate (wrong answers among non-correct
  ones) higher than the best resident arm's?

## Strategic Fit and Why Now

- **D122 and D125.** Kevin asked whether 700B-1T open models such as Kimi can be run usefully on a
  normal computer, with all model work on the H100 host. G2 (speed) closed: streamed Kimi on his
  machine class runs at about 2-3 tokens/s. D125 named quality at matched memory as the question that
  decides whether a 1T model is worth running locally.
- **D127.** The host is prepared: six GGUFs with receipts, a stock digest-pinned image, a passing
  smoke test. The pilot needs no download and fits inside the D127 window on about 3 GPUs.
- **The decision it changes** (registration 7.3): whether Kevin streams a 1T Kimi for anything; which
  V4 Flash file he keeps resident; and whether the program spends the full study's Kimi arms (about
  47-140 GPU-h for the K2.6 IQ1_M thinking tier, 34-251 more for its INT4 reference) and keeps G1/G3 open.
- **Why the pilot is knowledge-first.** On the one AA comparison that pairs a 1T Kimi with V4 Flash
  0731, the 1T model leads only on AA-Omniscience (5 against −14), AA-LCR (81 against 80) and SciCode
  (52 against 50), and trails on AutomationBench (13 against 54), Terminal-Bench 4.0 (1 against 12),
  GDPval (1,038 against 1,434) and CritPt (8 against 17). If the 1.87-bit file cannot hold its edge
  where the full-precision model is strongest, the other domains follow from that prior and are
  checked only cheaply (one K2.6 confirmation run, full study).

## Primary-Source Evidence

Read levels:
- **F**: full text read with `orx paper --full` by a discovery cell;
- **F\***: full text read by a cell and re-read by the synthesis owner;
- **A**: abstract or report only;
- **R**: repository, code, dataset or model record at a pinned revision;
- **1P**: first-party page, README, vendor card or index, not replicated;
- **M**: this program's committed measurement;
- **D**: this synthesis's arithmetic on published numbers, committed in the bundle.

| ID | Claim | Source | Date | Read level |
|---|---|---|---|---|
| C01 | Kimi K2.5: instant and thinking modes; thinking T = 1.0, instant T = 0.6, top-p 0.95; instant via `chat_template_kwargs {"thinking": false}`; HLE, AIME25, HMMT25 and GPQA-D at a 96K completion budget; native INT4 as K2-Thinking; modified MIT; ungated | https://huggingface.co/moonshotai/Kimi-K2.5 | rev 4d01dfe0, read 2026-10-16 | R |
| C02 | Unsloth K2.5 UD-TQ1_0: 239,537,678,077 bytes in 5 shards at rev 386fed8b; no TQ1_0 tensors (a mix of IQ1_S, IQ2_XXS, IQ3_XXS, IQ4_NL, Q4_K, Q8_0 and others); receipt `c198cdd5` | https://huggingface.co/unsloth/Kimi-K2.5-GGUF | 2026-10-16 (host prep) | M |
| C03 | Host smoke test, job 1582: all six GGUFs load on 4 H100s in llama.cpp b11669; Kimi 55.5 tokens/s single-stream, peaks 64.5 / 56.9 / 51.6 / 54.4 GiB at `-c 4096`; Kimi spent its whole 128-token chat budget reasoning | program/evidence/2026-10-16/lm1-host-prep/README.md | 2026-10-16 | M |
| C04 | Anemll fork on an M5 Max 128 GB: Kimi-K2.5 UD-TQ1_0 at 2.2 tokens/s (top-8), 3.3 (top-4), 4.7 (top-2), `-c 256`; no prefill or quality numbers for reduced top-k | https://github.com/Anemll/anemll-flash-llama.cpp | README at a809594f, accessed 2026-10-15 | 1P |
| C05 | GSQ Table 14: Kimi K2.5 AgentBench (OS/DB/KG/ALFWorld/WS), mean of 3 runs: base 50/69/57/53/52; Unsloth UD-IQ1_M (2.4 bit) 40/61/39/41/47; GSQ (2.37 bit) 43/63/45/42/49 | https://arxiv.org/abs/2604.18556 | 2026-04-20 (v2 2026-05-15) | F\* |
| C06 | GSQ Table 3, K2.5 base against GSQ 2.13 bpp: AIME25 95.33 / 93.00; GPQA-D 89.29 / 76.57; LCB 61.37 / 69.37; MATH500 96.68 / 97.32; single quantization run | https://arxiv.org/abs/2604.18556 | 2026-04-20 | F\* |
| C07 | GSQ Appendix K: GGUF "Templating often failed, and evaluating Kimi-K2.5 became extremely slow and impractical" | https://arxiv.org/abs/2604.18556 | 2026-04-20 | F\* |
| C08 | CC-MoE: DeepSeek-V3 to 103 GB under "a strict 128GB memory limit", over 5 tokens/s on a Strix Halo laptop; compared at that tier only with the same model's IQ1_M and Q2_K_L; Table 2: R1 quant 210 GB against Qwen3-235B 8-bit 233 GB, AIME24 86.67/86.67, GPQA-D 74.24/68.18, GSM8K 96.51/84.99 | https://arxiv.org/abs/2509.25689 | 2025-09-30 | F\* |
| C09 | 2504.02010 Table 1: R1 1.58-bit avg 78.7 (AIME24 66.7, FOLIO 75.4, Temporal 94.0), MuSiQue EM/F1 14.0/22.34, single pass; R1-Distill-Llama-70B avg 81.8, MuSiQue 13.3/21.57, three passes; MuSiQue has 100 items; Finding 1 | https://arxiv.org/abs/2504.02010 | 2025-04-02 (ICLR 2026) | F\* |
| C10 | Fewer Bits, More Tries: verified retry recovers coding accuracy under memory budgets; one-bit Qwen3.6-27B at K = 4 runs 0.83-0.87x (M3 Max) and 1.58-1.67x (M5 Pro) the speed of bf16; 10,000 paired task-bootstrap resamples | https://arxiv.org/abs/2610.15372 | 2026-10-11 | F\* |
| C11 | Knowledge capacity is 2 bits per parameter, unchanged by int8; post-training int4 reduces it to 0.7 bits per parameter; MoE with 32 experts costs only 1.3x in capacity (controlled synthetic data, GPT-2-scale models) | https://arxiv.org/abs/2404.05405 | 2024-04-08 | F (synthesis) |
| C12 | AA comparison, index v4.3.2: V4 Flash 0731 / Kimi K2.6: Intelligence Index 34 / 27; AA-Omniscience −14 / 5; AA-LCR 80 / 81; SciCode 50 / 52; AutomationBench 54 / 13; Terminal-Bench 4.0 12 / 1; GDPval 1,434 / 1,038; CritPt 17 / 8; output tokens per task 62k / 47k | https://artificialanalysis.ai/models/comparisons/deepseek-v4-flash-vs-kimi-k2-6 | accessed 2026-10-16 | 1P |
| C13 | AA Kimi K2.5 page: Intelligence Index 23, "Estimate (independent evaluation forthcoming)"; K2.5 and K2.6 listed as deprecated | https://artificialanalysis.ai/models/kimi-k2-5 | accessed 2026-10-16 | 1P |
| C14 | AA Qwen3.8 27B (Xhigh): Intelligence Index 33.68, `intelligenceIndexIsEstimated: false` | https://artificialanalysis.ai/models/qwen3-8-27b | accessed 2026-10-16 | 1P |
| C15 | AA-Omniscience-Public: 600 questions, 100 in each of 6 domains (Finance, Health, Humanities and Social Sciences, Law, Science Engineering and Mathematics, Software Engineering); Apache-2.0; created 2025-11-17; answer prompt asks for "JUST the answer" and allows abstention; grader template with CORRECT / INCORRECT / PARTIAL_ANSWER / NOT_ATTEMPTED; AA's grader is Gemini 2.5 Flash | https://huggingface.co/datasets/ArtificialAnalysis/AA-Omniscience-Public | rev e4883edb, read 2026-10-16 | R |
| C16 | AA-Omniscience paper | https://arxiv.org/abs/2511.13029 | 2025-11 | A |
| C17 | SimpleQA-Verified: 1,000 prompts; MIT; created 2025-09-22; columns include topic, answer_type, multi_step, requires_reasoning; graded by a GPT-4.1 autorater | https://huggingface.co/datasets/google/simpleqa-verified | rev 0dc97e0d, read 2026-10-16 | R |
| C18 | SimpleQA Verified paper | https://arxiv.org/abs/2509.07968 | 2025-09 | A |
| C19 | SuperGPQA: 285 graduate disciplines, 10-option multiple choice; ODC-BY; fields `is_calculation`, `difficulty`, `discipline` | https://huggingface.co/datasets/m-a-p/SuperGPQA | rev 4430d445, read 2026-10-16 | R |
| C20 | SuperGPQA paper | https://arxiv.org/abs/2502.14739 | 2025-02-20 | A |
| C21 | Qwen3-235B-A22B-Instruct-2507 card: non-thinking only; SimpleQA 54.3 against Kimi K2 31.0 and Qwen3-235B-A22B non-thinking 12.2; sampling T 0.7, top-p 0.8, top-k 20, min-p 0; Apache-2.0 | https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507 | rev ac9c66cc, read 2026-10-16 | 1P |
| C22 | DeepSeek-V4-Flash-0731 card: no Jinja template (an `encoding` folder instead); `reasoning_effort` low / high / max; T = 1.0, top-p 1.0 (0.95 agentic); 384K output at high and max; MIT | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 | rev 7872f01b, read 2026-10-16 | R |
| C23 | gpt-oss model card: knowledge cutoff June 2024; AIME25 (no tools) 50.4 / 80.0 / 92.5 at low / medium / high; gpt-oss-120b SimpleQA accuracy 0.168, hallucination rate 0.782 | https://arxiv.org/abs/2508.10925 | 2025-08-05 | F (synthesis) |
| C24 | Qwen3.8-27B: dense 27B vision-language model, thinking on by default and switchable; non-thinking sampling T 0.7, top-p 0.8, top-k 20, presence penalty 1.5; Apache-2.0; created 2026-08-05 | https://huggingface.co/Qwen/Qwen3.8-27B | rev 1d4bf0f2, read 2026-10-16 | R |
| C25 | bartowski Kimi K2.6: IQ1_M 232.43 GB, IQ1_S 207.40 GB, mainline types only | https://huggingface.co/bartowski/moonshotai_Kimi-K2.6-GGUF | rev ed96b238, read 2026-10-16 (host prep) | R |
| C26 | llama.cpp b11669 server: defaults T 0.80, top-k 40, min-p 0.05; `--n-cpu-moe N` keeps the first N layers' expert weights on the CPU; `-fit` on by default with 1,024 MiB margin; per-request `chat_template_kwargs`, `reasoning_effort`, `id_slot`; `cache_prompt` logits "not guaranteed" identical; `--reasoning-budget N` | https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/tools/server/README.md | 2026-10-15 | R |
| C27 | llama.cpp b11669 multi-GPU: `tensor` split EXPERIMENTAL and not implemented for DeepSeek2; `row` deprecated; `layer` default | https://github.com/ggml-org/llama.cpp/blob/620d2225cc436ab0b001e3200e590e3b286ef9ab/docs/multi-gpu.md | 2026-10-15 | R |
| C28 | ds4 Q2 V4 Flash on an M5 Max 128 GB: 39.35 tokens/s decode and 790 prefill at 2K; 34.36 / 557 at 32K | https://github.com/antirez/ds4/blob/main/docs/PERFORMANCE.md | refreshed 2026-08-05 (dossier S95) | 1P |
| C29 | AtomicChat V4 Flash 0731 fidelity ladder against BF16 (WikiText-2, context 5,632): ds4 Q2 KLD 0.408, 78.98% same top token; UD-IQ3_XXS 0.261, 83.46%; no task results | https://huggingface.co/datasets/AtomicChat/dsv4-eval-artifacts | 2026-08-03 | 1P |
| C30 | Unsloth Aider Polyglot: DeepSeek-V3.1 TQ1_0 (170 GB) 50.7, IQ1_M (206 GB) 55.7, full 71.6; full-precision Qwen3-235B 59.6 | https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/unsloth-dynamic-ggufs-on-aider-polyglot | 2025-09-10 | 1P |
| C31 | MoE-XBench: matched-memory comparisons within one model, mostly on perplexity, 30B-235B; IQ1_M raises perplexity sharply against Q4 prune+quant at the same memory | https://arxiv.org/abs/2608.21693 | 2026-08-22 | F |
| C32 | k-bit inference scaling laws: 4 bits almost universally optimal for fixed total model bits (zero-shot, dense, 19M-176B) | https://arxiv.org/abs/2212.09720 | 2022-12-19 | F |
| C33 | Paired evaluation: report the difference, its SE and the correlation; sample size from the paired variance | https://arxiv.org/abs/2411.00640 | 2024-11-01 | F |
| C34 | Paired total variance ≈ E[A](1−E[A]) per single sample; prediction noise usually exceeds data noise | https://arxiv.org/abs/2512.21326 | 2025-12-24 | F |
| C35 | An exact intersection-union non-inferiority gate needs no Bonferroni penalty; a no-detected-harm gate is not non-inferiority | https://arxiv.org/abs/2609.13714 | 2026-08-28 | F |
| C36 | Token budgets reverse rankings; truncation differs sharply by model; three-tier truncation analysis | https://arxiv.org/abs/2608.12150 | 2026-08-12 | F |
| C37 | Low-bit PTQ inflates chain-of-thought length (INT3 +276-292% on one model) | https://arxiv.org/abs/2606.25519 | 2026-06-24 | F |
| C38 | Same model across vendors: 3.1% of MMLU answers differ, aggregate accuracy moves about 0.2 points | https://arxiv.org/abs/2610.05458 | 2026-10-04 | F |
| C39 | For reasoning models, memory spent on KV can beat memory spent on weight precision above an effective 8-bit 4B size | https://arxiv.org/abs/2510.10964 | 2025-10-13 | F |
| C40 | Near-tied cross-family rankings reverse under low-DIF recomposition in 30.9-47.1% of pairs | https://arxiv.org/abs/2609.00482 | 2026-08-31 | F |
| C41 | A rate-distortion lower bound links forced compression of observed facts to closed-book factual error | https://arxiv.org/abs/2609.12111 | 2026-09 | A (synthesis) |
| C42 | Kimi K2.5 file: 1.867 bpw over 1,026.4B parameters; file information 1.92 Tbit against 0.69 (ds4 Q2), 0.83 (IQ3_XXS), 0.83 (Qwen Q3) and 0.51 (gpt-oss) Tbit | compute/caps-lm1.json (arithmetic in this proposal) | 2026-10-16 | D |
| C43 | Kimi's Mac time per short item: 22-68 s to stream the routed pool once for prefill at 3.4-10.6 GB/s plus 13.6 s for 30 tokens at 2.2 tokens/s = 36-82 s; a resident V4 Flash Q2 decodes 1,400-3,227 tokens in that time at 39.35 tokens/s | compute/caps-lm1.json | 2026-10-16 | D |
| C44 | Decision-rule operating characteristics (simulated, seeds 42-44) | compute/sim-lm1.json | 2026-10-16 | D |

## Closest Prior Work

1. **CC-MoE** (C08; re-read in full). It is the only prior that names the exact 128 GB tier and
   deploys a 600B+ MoE inside it, and its Table 2 is an explicit cross-family comparison "at similar
   size" (about 220 GB). At 128 GB it compares only within one model, on easy benchmarks; it has no
   runs or intervals, no streaming option, no 2026 models, no knowledge-recall or reasoning-mode
   control. **This is the closest prior used for blind discrimination.**
2. **When Reasoning Meets Compression** (C09; re-read). The only published point with a 600B+ MoE at
   about 1.6 bits against a smaller model near native precision at about the same bytes (131 against
   141 GB). Not framed as matched memory, single-pass giant, same-lineage comparator, 100 MuSiQue
   items for the knowledge read.
3. **GSQ** (C05-C07; re-read). Same-model, matched-size quantizer comparison on Kimi K2.5 at 2.37-2.4
   bits on AgentBench; no cross-family arm; reports that GGUF evaluation of Kimi broke on templates.
4. **Fewer Bits, More Tries** (C10; re-read). Memory-constrained deployment on Apple Silicon with a
   wall-clock-aware estimand; within-family (Qwen), coding with verifiers, models of 32B or less.
5. **Others that narrow the delta:** MoE-XBench (C31, within-model matched memory, perplexity);
   Unsloth's Aider table (C30); k-bit scaling laws (C32); Allen-Zhu and Li (C11, the mechanism's
   capacity prior); AtomicChat (C29, V4 Flash fidelity only).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Cross-family comparison of a 600B+ MoE at about 1.6-1.9 bpw against smaller models at roughly matched memory | CC-MoE Table 2 (C08); 2504.02010 (C09) | A giant at low bits against a smaller model at higher precision, roughly equal bytes | Matched on the target's resident ceiling (RAM), not bytes, with the giant streamed and its speed cost reported; at the 128 GB tier; four resident arms from three families; seeded, paired, pre-registered | high |
| Task numbers for a mainline-GGUF Kimi below about 290 GB | GSQ (C05, C06: GSQ checkpoints 294 GB and up; Unsloth UD-IQ1_M on AgentBench only) | Low-bit Kimi K2.5 on tasks | The exact 239.5 GB file a Mac user would stream; knowledge recall, domain split and hallucination rate; template-fidelity and mode-conformance gates for the failure GSQ reports | high |
| Knowledge-first decision rule: the giant must keep its full-precision edge where it is strongest | none found; 2504.02010 Finding 1 is the closest observation | Knowledge versus reasoning under compression | An asymmetric rule (non-superiority at a 5-point practical margin, Bonferroni over resident arms, against an intersection-union superiority test) that makes a negative decisive with the comparators at hand and a positive provisional | medium |
| Mac-time-matched comparison of a streamed giant against a resident model | Fewer Bits, More Tries (C10: within-family retries at matched wall-clock) | Spending the resident model's speed on more computation | The resident model thinks for the Mac time the streamed giant needs per item (4,096-token budget from measured speeds), and a free majority-of-three estimand; cross-family, knowledge recall, a 1T streamed arm | medium |
| V4 Flash 0731 knowledge cost at 2 against 3 bits | AtomicChat (C29, KLD only) | The same files | Task-level knowledge recall with paired intervals and a 2-point non-inferiority test (G4's knowledge part) | high |
| Statistics and protocol (paired clustered intervals, IUT, estimands, Mac-time matching) | 2411.00640, 2512.21326, 2609.13714, ICH E9(R1), 2608.12150 | Methods | None claimed; adopted | n/a |

Novelty wording: No direct prior art found through 2026-10-15 under the coverage in the header:
- the 52 orx discover records, 22 web searches, 2 GitHub searches, 3 Hugging Face searches and the
  asset cell's 13 searches, listed with their returned ids (where the cell returned them) in
  `query-log.json`;
- full-text reads of 2509.25689, 2504.02010, 2604.18556, 2610.15372, 2404.05405 and 2508.10925 by the
  synthesis owner, and about 20 more by the cells.

That statement covers the combination of a RAM-matched (not byte-matched) task-level comparison at
the 128 GB tier between a streamed 1T-class model at about 1.87 bpw and resident models from three
families, with a knowledge-first asymmetric decision rule and a Mac-time-matched secondary. The
merged verdict is NARROWED. Recombination risk for the novelty refuter: the design could be called
CC-MoE's Table 2 moved to 128 GB, plus 2504.02010's knowledge observation, plus 2610.15372's
wall-clock framing. The delta then rests on the RAM-matched eligibility definition with a streamed
arm, the asymmetric decision rule wired to a deployment choice, and the first task-level numbers for
the 239.5 GB Kimi file.

Blind discrimination packet: `evidence/2026-10-16-lm1-matched-memory-quality/blind/` (two anonymized
mechanism paragraphs in a seeded order; roles in `compute/blind-roles.json`, recorder only).

## Mechanism and Falsifiable Predictions

**Mechanism.** At a fixed resident memory ceiling, a deployable configuration buys quality with two
resources it cannot both maximize: stored information and speed.
- **Stored information.** Factual recall needs stored bits. Trained models store about 2 bits of
  knowledge per parameter at 8 bits or more, and post-training int4 cuts that to about 0.7 (C11,
  controlled synthetic data). The streamed 1T file holds 1.92 Tbit against 0.51-0.83 Tbit for the
  resident files (C42), and 3.6-8.8 times as many parameters. If recall were bound by stored bits, the
  giant would recall more.
- **Fidelity.** Below 2 bits, post-training quantization stores each association approximately, and
  approximate storage shows up as confident wrong answers rather than abstention (C41; GSQ's KG drop,
  C05). Reasoning and calculation are less capacity-bound (C09 Finding 1) but accumulate per-layer
  noise over long chains (C37).
- **Speed.** Streaming the giant from SSD costs 12-48x in decode speed (2.2 against 27-105 tokens/s;
  C04, C28; the 27-41 values are dossier estimates), so on the target the giant can afford only short instant answers, while a resident model
  can think or sample several times in the same wall-clock (C10).
- **Consequence.** The giant's best case is short factual recall in instant mode. If its parameter
  surplus survives 1.87 bpw, it leads there; if quantization noise erases it, it loses there too, and
  it is dominated everywhere, since it is slower and trails at full precision in the other domains
  (C12).

**Predictions, falsifiers and kill criteria** (registration section 7 has the exact rules; Δ_j is
Kimi's primary accuracy minus resident arm j's, in points):
- **H1 (the giant's recall survives; primary).** For every resident arm j, Δ_j's 95% lower bound is above 0
  and min_j Δ̂_j ≥ +5 (reading LEADS). **Falsified** by reading NOT_WORTH: for some j, Δ_j's upper
  bound at the Bonferroni level (98.75% two-sided) is below +5. The desk forecast favours
  falsification (registration 7.4).
- **H2 (V4 Flash file).** ds4 Q2 is non-inferior to UD-IQ3_XXS within 2 points (lower 95% bound of
  Q2 − IQ3 above −2). Falsified if the lower bound is at or below −2. The fidelity ladder predicts a loss
  (KLD 0.408 against 0.261, C29); whether it reaches 2 points of recall is unknown.
- **H3 (domain split; secondary, underpowered by design).** Kimi's difference to the best resident
  arm is larger on SuperGPQA non-calculation items than on calculation items. Falsified if the 95% CI
  of the interaction lies wholly below 0. The minimum detectable interaction at 200 + 200 items is
  about 12 points (registration 10), so a non-significant result is reported as inconclusive.
- **H4 (reliability).** Kimi's hallucination rate exceeds the best resident arm's (C41). Falsified if
  the 95% CI of the difference lies wholly below 0.
- **H5 (time-matched; only under LEADS).** The best resident arm in thinking mode at a 4,096-token
  budget does not close the gap: Kimi minus that arm has a 95% lower bound above 0 on AA-Omniscience-Public
  (seed 42). Falsified otherwise; the reading then becomes LEADS_INSTANT_ONLY.
- **Assay sensitivity (a gate, not a hypothesis).** Qwen3-235B-2507 minus gpt-oss-120b on
  SimpleQA-Verified is at least +10 points with its 95% CI excluding 0. The vendors report 54.3 and
  16.8 (C21, C23). If the harness cannot see that gap, it cannot see a 5-point one.

**Kill criteria** (registration 7.2):
- **KC1 (assay).** The assay-sensitivity gate fails: the harness is insensitive; no reading; repair
  is a new experiment id.
- **KC2 (judge).** On a blind hand check of 360 graded responses (60 per arm), judge agreement is
  below 0.90 overall, or the judge's error rate differs between any two arms by more than 3 points:
  the judge-based reading is void; the deterministic-grader reading is reported as exploratory.
- **KC3 (mode and template).** An arm fails mode conformance (fewer than 98% of instant responses
  free of reasoning content, or harmony parse success below 98% for gpt-oss) or template fidelity (any
  of 20 fixed conversations renders differently from the reference): that arm is excluded; if it is
  Kimi, the pilot stops with no reading.
- **KC4 (coverage).** A contrast enters the decision only with at least 1,000 paired primary items.
  NOT_WORTH needs one qualifying contrast; LEADS needs all four. Otherwise the reading is
  UNRESOLVED_INCOMPLETE.
- **KC5 (degeneracy, reported, not a stop).** Kimi's share of degenerate responses (a 4-gram repeated
  more than 8 times, or truncation at the 2,048 cap) above 10% is flagged with the reading.

## Cheapest Decisive Pilot

Runs before 2026-10-20 on at most 3 GPUs at a time among GPUs 1-7, never GPU 0, on the host's
existing files; no download. Guards total 6.9 GPU-h, plus a 1.1 GPU-h reserve; line 8.0
(`compute/caps-lm1.json`).

- **Preconditions (CPU only, 0 GPU-h).**
  1. Fetch the three datasets through the CPU lane with receipts (AA-Omniscience-Public, 155 KB;
     SimpleQA-Verified; SuperGPQA, about 30 MB). Item text stays on the host; the repository gets ids
     and hashes only.
  2. Draw the item order: all 1,600 primary items and 400 SuperGPQA items (200 with
     `is_calculation` False, 200 True, stratified by discipline), each sorted by the SHA-256 of its id
     and permuted with `numpy.random.default_rng(42)`; primary items first. Commit the order's hash.
  3. Template fidelity (KC3): render 20 fixed conversations with each file's embedded template
     through llama.cpp's `/apply-template` and compare them with the reference renderer (Moonshot's
     `chat_template.jinja` at 4d01dfe0 through jinja2; DeepSeek's `encoding_dsv4.py` in chat mode;
     Qwen's and OpenAI harmony's own templates). For V4 Flash, one hash-pinned template is passed with
     `--chat-template-file` to all V4 files.
  4. Write the request runner, the grader client and the analysis script, with unit tests, and
     commit them. No GPU code is written.
- **P1 (instant tier; the decision).** One `llama-server` per arm, layer split, F16 KV, a fixed
  per-slot context of 3,072 tokens (`-no-kvu`; 16 slots for resident arms, 8 for Kimi on 3 GPUs),
  `--jinja`, `-lv 4`, every sampler set per request (registration 4-5). Each job
  starts with a 3-minute `llama-batched-bench` preflight (records aggregate throughput) and then
  sends the items in order, the three seeds of an item to one slot (prompt reuse). Arms and guards:
  - Kimi K2.5 UD-TQ1_0, instant, K3 then K3+ then K4 (registration 4): 3 GPUs, guard 3.3 GPU-h;
  - V4 Flash 0731 ds4 Q2, non-thinking: 2 GPUs, 0.9;
  - V4 Flash 0731 UD-IQ3_XXS, non-thinking: 2 GPUs, 0.9;
  - Qwen3-235B-2507 Instruct UD-Q3_K_XL: 2 GPUs, 0.9;
  - gpt-oss-120b, reasoning effort low (its minimum): 1 GPU, 0.6.
- **J (grading).** Qwen3-32B at `9216db57` in vLLM, batch-invariant, greedy, thinking off, with AA's
  grader template verbatim (Apache-2.0) for both primary benchmarks; prefix caching shares the long
  template. 1 GPU, guard 0.3. SuperGPQA is graded by a deterministic parser (last `Answer: [A-J]`).
- **Reserve (1.1 GPU-h), in this order.** (1) A top-up job for any arm below 1,000 primary items,
  resuming from the next item in the order (the fresh-job resume test, below); (2) P2, only if the
  primary reading points to LEADS: the best resident arm by P1 point estimate in thinking mode,
  `--reasoning-budget 4096` with a fixed budget message, on the 600 AA-Omniscience items, seed 42
  (2 GPUs, guard 0.7).
- **Readouts:** the decision table below; per-benchmark and per-domain tables; hallucination rates
  and the Omniscience-style index; truncation, parse-failure and abstention rates; tokens per item;
  measured aggregate throughput per arm (the full study's budget input); Mac seconds per item and per
  correct answer (derived, labelled).

**Decision rules (fixed now).** Δ_j as above, on the primary endpoint, by stratified paired item
bootstrap (10,000 resamples, seed 42):

| Pilot reading | What Kevin runs locally | Program consequence |
|---|---|---|
| NOT_WORTH (some Δ_j's Bonferroni upper bound below +5); sub-reading KIMI_WORSE if that bound is below 0 | A resident model. For knowledge, the best resident arm; for V4 Flash, ds4 Q2 if H2 holds, otherwise UD-IQ3_XXS when other work can stop. Streamed Kimi is not worth its 12-48x speed cost for factual recall, its best case | Kimi arms leave the full study except one confirmation run of K2.6 IQ1_M on the primary endpoint (232.4 GB download, Kevin's go-ahead), because K2.6 is the Kimi a user would stream today. G3 closes by dominance: a 100 GB Kimi is more compressed than this one. G1's coding-specialist framing is a different domain and is not closed |
| LEADS (every Δ_j's 95% lower bound above 0, min Δ̂_j ≥ +5, Kimi's index not below any resident arm's, both benchmarks agreeing in sign) and H5 holds | Stream Kimi for knowledge-heavy questions, at 36-82 s per short answer (C43); a resident model for everything else | Full study, LEADS branch: completes the comparator set (Qwen3.8 27B), K2.6 IQ1_M and its INT4 reference, top-4, the thinking tier |
| LEADS but H5 fails (LEADS_INSTANT_ONLY) | A resident model that thinks; Kimi only where thinking is not wanted | Full study, UNRESOLVED branch |
| UNRESOLVED, SPLIT or UNRESOLVED_INCOMPLETE | Unchanged: a resident model; streamed Kimi optional | Full study, UNRESOLVED branch, with the knowledge block re-sized from the pilot's measured variance for a 3-point minimum effect |

The strict-fit view (R-Y arms only, Bonferroni over 2) is reported next to the primary reading; if
the two disagree, both are stated, and Kevin's choice depends on whether he will stop other work.

### The full study the pilot gates (proposed; registered separately)

- **F1 (thinking tier, Mac-time-matched).** AIME 2026 and HMMT Feb 2026 (63), LiveCodeBench v6
  2025-02 to 2025-05 (150), BFCL AST categories (400), SuperGPQA hard (400); seeds 42-44; budgets
  from measured Mac speeds; three-tier truncation analysis (C36); tokens per solved item.
- **F2 (comparators).** Qwen3.8 27B (Apache-2.0, about 54 GB BF16, R-Y; download, Kevin's go-ahead;
  runtime checked for arch support first); GLM-5.3-Flash only if a stock-llama.cpp file loads.
- **F3 (Kimi).** K2.6 IQ1_M (232.4 GB); in the LEADS branch also K2.6 INT4 (on the host, rev
  7eb5002f, vLLM TP8 after GPU 0 frees) to separate Kimi's quantization cost from model capability,
  and top-4 routing (Anemll's 3.3 tokens/s point).
- **F4 (G4).** V4 Flash 0731 UD-Q8_K_XL as the near-native reference for all blocks.
- **F5 (kernel path).** CUDA against CPU on 200 items per arm, and an optional cuBLAS-dequant build,
  bounding the CUDA-to-Metal numerics (C38).
- **Size by branch:** NOT_WORTH 112-249 GPU-h; UNRESOLVED 138-345; LEADS 174-606, plus 3-8 of setup
  (`compute/caps-lm1.json`). The full study runs after 2026-10-21 on 7 GPUs and gets its own
  registration and admission.

## Controls, Baselines, and Ablations

- **Resident baselines:** four arms from three families, at their best fitting files on the host
  (ds4 Q2, UD-IQ3_XXS, Qwen3 Q3_K_XL, gpt-oss MXFP4). The near-native resident arm on the host is
  gpt-oss; Qwen3.8 27B joins in the full study.
- **Positive control (assay sensitivity):** Qwen3-235B-2507 against gpt-oss-120b on
  SimpleQA-Verified (vendor gap 37.5 points, C21, C23); a gate (KC1).
- **Within-family control:** ds4 Q2 against UD-IQ3_XXS separates quantization cost from model
  identity inside V4 Flash (H2); Q8_K_XL completes the ladder in the full study.
- **Mode control:** every arm in instant mode with the same output cap and prompt; mode conformance
  verified per response (KC3). gpt-oss cannot disable reasoning; its low effort is the closest, and
  its reasoning tokens are reported.
- **Template control:** template fidelity against reference renderers on 20 fixed conversations
  (KC3); one hash-pinned template for all V4 Flash files.
- **Sampling control:** every sampler set explicitly per request at each card's instant setting
  (llama-server's defaults differ from every card, C26); logged per request.
- **Grader controls:** a blind hand check (KC2); a deterministic normalized-match grader as a
  sensitivity; the judge is not a contestant (it shares a family with the Qwen3-235B arm, which the
  per-arm error check addresses).
- **Contamination control:** the two primary benchmarks have opposite exposure (below), so the
  per-benchmark readouts and the SPLIT rule separate a contamination artefact from a model effect.
- **Time-matched control (conditional):** the resident arm in thinking mode at a Mac-time-matched
  budget (H5); majority of three against a single Kimi sample, free from P1.
- **Excluded, with reasons:** Kimi in thinking mode (40-80 minutes per item on the Mac at 5-11K
  tokens; the host's thinking-mode quality would match no usable Mac configuration); retrieval or
  tools (they measure the tool, not stored knowledge); the AA prompt without the abstention line
  (one prompt only, to stay comparable with AA's protocol).

## Evaluation, Statistics, and Leakage Checks

- **Unit and estimand.** The item. Per arm and item, the share of the three seeded samples graded
  CORRECT; intercurrent events (truncation at 2,048, empty or unparseable response, template or
  server error after one retry) count as not correct (composite estimand, primary). Benchmark
  accuracy is the item mean; the primary endpoint is the equal-weight mean of the two benchmarks.
- **Sensitivity estimands:** principal stratum (items no arm truncated); deterministic grader; the
  Omniscience-style index (correct − incorrect) ÷ N; hallucination rate = incorrect ÷ non-correct;
  majority of three (at least 2 of 3 correct) for resident arms against Kimi's seed 42.
- **Intervals.** Stratified paired item bootstrap (strata: benchmark; 10,000 resamples, seed 42);
  for the knowledge-only and calculation-only SuperGPQA strata, the same with discipline strata. The
  decision uses 95% intervals for lower bounds and Bonferroni 98.75% intervals for the NOT_WORTH upper
  bounds.
- **Operating characteristics** (`compute/sim-lm1.json`; seeds 42-44; 1,000 replicates per cell per
  seed; superpopulation item model with arm-item interaction calibrated to single-sample discordance
  of 0.26 and prediction-noise share of 0.27, and a noisier setting at 0.32 and 0.57). The SE of Δ at
  1,600 primary items is about 1.0 point (0.93-1.04 across settings; 1.17-1.31 at the 1,000-item
  minimum), and the normal-approximation 95% interval covers the true Δ in 94.2-95.7% of replicates.
  Seed-averaged, at 1,600 items in the base setting:

  | True Δ_min (points) | P(NOT_WORTH) | P(LEADS) | P(UNRESOLVED) |
  |---:|---:|---:|---:|
  | −5 | 1.000 | 0.000 | 0.000 |
  | 0 | 0.989 | 0.000 | 0.011 |
  | +2 | 0.649 | 0.000 | 0.351 |
  | +5 | 0.007 | 0.495 | 0.497 |
  | +8 | 0.000 | 0.998 | 0.002 |

  The rule calls NOT_WORTH wrongly (true Δ_min = +5) in 0.6-0.9% of replicates across settings and
  sizes, below its nominal 2.5%, and calls LEADS wrongly (true Δ_min ≤ 0) in none. At the 1,000-item
  minimum a true Δ_min of 0 still reads NOT_WORTH in 91-96%. Between +2 and +5 the rule is
  deliberately undecided. The full table (both settings, both sizes, seed ranges, coverage) is in
  registration section 10 and `compute/sim-lm1.json`.
- **Contamination and leakage.**
  - AA-Omniscience-Public (created 2025-11-17) post-dates Qwen3-235B-2507 (2025-07-21) and gpt-oss's
    June 2024 cutoff, and pre-dates Kimi K2.5 (released 2026-01-27 per AA; continual pretraining on
    about 15T tokens) and V4 Flash 0731 (2026-07-31). Exposure would favour Kimi and V4 Flash.
  - SimpleQA (2024-10) and its verified subset (2025-09-22) pre-date every model release; Qwen3-235B's
    SimpleQA jump from 12.2 to 54.3 within one revision is unexplained. Exposure would favour Qwen.
  - So the per-benchmark readings have opposite exposure; a reading that holds on one and reverses on
    the other is SPLIT (UNRESOLVED).
  - SuperGPQA (2025-02-20) pre-dates every release except gpt-oss's cutoff.
  - Item text stays on the host; only ids, hashes and per-item grades enter the repository. No item
    is used to choose prompts, templates or samplers; those are fixed before any model output is read.
- **Multiplicity.** One primary endpoint and decision; H2-H5 are secondary, each at 95% without
  further correction, reported as such.
- **Forking paths.** The prompt, templates, samplers, item order, grader template, judge settings,
  analysis script and every threshold are committed before the first P1 job. Any change after a
  model output is read is a new experiment id.

## Compute and Reproducibility

- **Image.** The digest-pinned llama.cpp b11669 image built from stock upstream code (D127):
  `127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131`
  (image id `sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848`, commit
  `620d2225`, built on `docker.io/nvidia/cuda@sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43`).
  The lane runs it through a per-commit overlay that adds only the cotcodec source and provenance
  (the smoke test's was `sha256:db2dcbf11a004efbe981493a637c87d2250afa3405d19cf1d097cb08ebbf290c`);
  the pilot's overlay is built from its freeze commit. The judge runs in the cotcodec-vllm overlay
  AM1's judge used (vLLM 0.31.0, `db9527a4`; base
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`).
- **Launch.** Per job: `python3 scripts/submit_docker_research_job.py manifests/lm1mmq-p1-ARM.yaml --dry-run`
  (ARM one of kimi, f2, f3, q, o; and `lm1mmq-j.yaml` for the judge),
  then `--test-only`, then submit; that runs `sbatch infra/slurm/host-single-node/docker-research.sbatch`
  with the job's GRES and time limit. Dataset fetches run on the GPU-less CPU lane
  (`fetch-model-cpu.sbatch` pattern). Each pilot job is an orx `slurm-manifest` node run with
  `uv run --locked python scripts/orx_run.py`, never `orx --backend slurm`.
- **Seeds:** seeds: [42, 43, 44]. Sampling seeds per request are 42, 43 and 44; the item order uses
  `numpy.random.default_rng(42)` over ids sorted by SHA-256; bootstrap seed 42; simulation seeds
  42-44. The judge is greedy and batch-invariant.
- **GPU budget.** gpu_hours: 8 (the pilot line; guards 6.9 unconditional, reserve 1.1). Arithmetic
  in `compute/caps-lm1.json`. The full study's caps are re-derived from P1's measured throughput.
- **Checkpoints and preemption.** Each completed (item, seed) response is appended to a JSONL file
  with its request, sampler settings, raw output, token counts and timing, and an index of completed
  keys is updated atomically. A preempted, timed-out or topped-up job restarts as a fresh job that
  skips completed keys. Resume test: the top-up job (or, if none runs, a deliberate 20-item rerun
  after a forced kill in the first resident job) re-runs the last 20 completed items; because CUDA
  kernels depend on batch size and prompt caching is not bit-deterministic (C26), equivalence is
  declared at the grade level (at least 18 of 20 identical grades) and the token-level match rate is
  reported. A 50-item `-np 1` determinism audit measures bit-reproducibility per arm.
- **Artifacts.** On the host: raw responses, server logs, preflight benchmarks. In the repository:
  per-item grades by arm and seed (ids only), token counts, timings, the analysis outputs, receipts
  and SHA-256 manifests.

## Safety, Data Rights, and Monitorability

- **Model licences** (registry and host-prep receipts): Kimi K2.5 and the Unsloth GGUF, modified MIT
  (a display clause above 100M monthly users or US$20M monthly revenue); V4 Flash 0731 and its GGUFs,
  MIT; Qwen3-235B-2507 and Qwen3.8-27B, Apache-2.0; gpt-oss-120b, Apache-2.0; Qwen3-32B (judge),
  Apache-2.0. All ungated; no licence acceptance and no credential needed.
- **Data licences:** AA-Omniscience-Public, Apache-2.0 (AA's prompt and grader template reused
  verbatim with attribution); SimpleQA-Verified, MIT; SuperGPQA, ODC-BY (attribution; underlying
  sources keep their own licences). Item text stays on the host to avoid putting benchmark text into a
  public repository that future models may train on; ids and hashes are committed.
- **Excluded data:** GPQA-Diamond (gated; accepting its terms is Kevin's); ungated mirrors of it.
- **Host rules.** Stock llama.cpp at a pinned tag in a digest-pinned image; the only new code is
  reviewed, committed CPU-side harness code (request runner, grader client, analysis); no GPU
  kernel; model outputs are text that is graded, never executed. GPUs 1-7 only, never GPU 0, at most 3
  at a time before 2026-10-21; no sudo; `~/cotcodec`, `~/tc-speedrun` and transcreate, tcsr and g3b
  jobs untouched. The gauntlet itself submits only the open-weight reviewer's lane job.
- **Public repository.** No host addresses, credentials, raw responses or benchmark text.
- **Outward actions.** None by this work. The full study's downloads (Qwen3.8 27B, K2.6 IQ1_M) await
  Kevin's go-ahead.
- **Monitorability.** Every job logs the model receipt, file SHA-256, template hash, resolved split
  and offload lines (`-lv 4`), per-request samplers, mode-conformance counters, and peak memory per
  GPU.

## Negative-Result Value

- **NOT_WORTH.** The first measured answer to D122's question for the knowledge domain: on a 128 GB
  machine, a 1.87-bit 1T model does not beat a resident model even where it leads at full precision.
  It closes streamed Kimi as a local option, closes G3 by dominance, removes the Kimi arms from the
  full study (saving about 47-140 GPU-h, and 34-251 more for the INT4 reference), and gives Kevin a concrete resident
  default.
- **KIMI_WORSE.** Adds a measured instance of knowledge loss below 2 bits on a 1T MoE trained for
  INT4, the first task-level number for the 239.5 GB file.
- **H2 falsified.** The ds4 Q2 file costs more than 2 points of recall against IQ3_XXS: Kevin should
  prefer IQ3_XXS when he can stop other work (G4's knowledge part).
- **Assay failure (KC1) or judge failure (KC2).** A documented harness limit for GGUF evaluation of
  these families, the failure GSQ reports anecdotally.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable; 92 counted searches with returned ids in `query-log.json` (the asset cell's 13 without query strings); cutoff 2026-10-15; degraded coverage recorded (orx outdated; no X, Reddit, OpenReview, patents, citation graphs; AA per-model Omniscience accuracy not readable) (`doctors/source.json`) | A Semantic Scholar citer pass for 2509.25689, 2504.02010 and 2604.18556 through the host relay |
| Citation | PASS | Claim registry C01-C44 with URLs, dates and read levels; every cited URL snapshotted with HTTP status and body hash; first-party numbers labelled 1P; three cell readings corrected after re-reading (`doctors/citation.json`) | Replace first-party speeds (Anemll, ds4) when replicated |
| Novelty | FAIL | NARROWED by two independent cells; no direct prior under the recorded coverage; every closest prior read in full by the synthesis owner; the blind critic and the novelty refuter have not run (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter within the remaining query budget |
| Design | PASS | Self-assessed; the identification refuter has not run. Matched-memory tiers defined; asymmetric decision rule with simulated operating characteristics; assay-sensitivity, judge, template and mode gates; contamination split; kill criteria KC1-KC5 (`doctors/design.json`) | Identification refuter; pre-freeze audit of the registration |
| Compute | FAIL | The image, models and smoke test exist (D127), but no request runner, grader client, manifest, dry run, test-only run or executable pilot exists for LM1; the deterministic doctor's real-model-loop and adapter checks fail; caps in `compute/caps-lm1.json` (`doctors/compute.json`, `compute/attestations-not-run.md`) | Write and test the harness, render the manifests, dry runs and test-only runs before a freeze |
| Safety | PASS | Permissive licences, all ungated; item text kept off the public repository; R570 respected (stock llama.cpp, no GPU code, outputs never executed); host and public-repository rules; no outward action (`doctors/safety.json`) | none |

Protocols followed:
- **Citation:** the ARS claim-verification protocol (claim registry, locators, verdicts, first-party
  labels).
- **Design:** the vendored K-Dense `experimental-design` and `statistical-power` skills (design before
  data; the minimum effect is the 5-point practical margin; operating characteristics by simulation).
- **Evaluation:** K-Dense `statistical-analysis` (paired, stratified intervals; composite estimand;
  sensitivity estimands).
- **Novelty:** K-Dense `literature-review` (PRISMA counts in the header).

The integrity gate's seven failure modes are answered in the registration's section 14.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only when a GPU among 1-7 is idle; 1 GPU, at most 20 minutes)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; the decision table maps every reading to a local-model choice and a program consequence |
| Primary-source evidence | 0 | 0 | not yet reviewed; speeds (Anemll, ds4) and AA indices are first-party |
| Defensible novelty delta | 0 | 0 | not yet reviewed; recombination risk against CC-MoE, 2504.02010 and 2610.15372 is open |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; H1 has a pre-registered falsifier and a desk forecast |
| Controls and causal identification | 0 | 0 | not yet reviewed; the judge shares a family with one arm; CUDA-to-Metal numerics are bounded only in the full study |
| Evaluation and statistics | 0 | 0 | not yet reviewed; operating characteristics simulated with a normal approximation |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; aggregate throughput is unmeasured and Kimi on 3 GPUs is untested |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no LM1 harness or manifest exists |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed |
| Independent adversarial review quality | 0 | 0 | not yet reviewed |
| **Total** | **0** | **0** | Lower total is authoritative; caps that bind until fixed: 79 (no executable pilot run), 89 (unsigned reviews, D24) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| wave-1 synthesis (2026-10-16) | not scored | (a) As posed, LM1 was close to predetermined: stale comparators (AA 12 for two of four resident arms), an undefined "matched memory", and a Kimi whose published quality needs reasoning budgets the Mac cannot afford; (b) the cells' plan put a 3-GPU reference and long thinking runs in a pilot that has about 3 GPUs and 8 GPU-h | (a) Matched memory defined as RAM-matched eligibility tiers with both views reported; the primary question moved to the 1T model's one full-precision edge (factual recall) in the only Kimi mode a Mac can afford; an asymmetric decision rule that makes a negative decisive with the host's comparators and a positive provisional; Mac-time-matched thinking as a conditional check; (b) the Q8 reference moved to the full study, guards with a reserve and a 1,000-item coverage rule | awaiting the blind critic, the triad and the reviewers |
