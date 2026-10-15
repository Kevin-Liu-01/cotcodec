# Running 700B-1T open MoE models on a 128 GB Mac: evidence dossier

- **Date:** 2026-10-15, third draft (after two rounds of verification). The file lives under the 2026-10-16 evidence folder.
- **Status:** a reading synthesis plus header-only file measurements. No model was run, on the Mac or on the host.
- **Verification.**
  - Round 1: three independent verifiers (claims, arithmetic, novelty) filed 54 findings (1 blocker, 26 major, 24 minor, 3 info). The second draft applied them.
  - Round 2: two verifiers (claims, arithmetic) checked the second draft and filed 23 findings (4 major, 16 minor, 3 info). This draft applies them.
  - Before adopting any fact a verifier introduced, I re-opened its source. The corrections log at the end (section 7) lists every finding, what changed, and what I rejected.
- **Inputs:**
  - the five round-1 research sweeps (extreme quantization; offloading and streaming; structural compression; routing locality and bandwidth; practical Apple Silicon recipes);
  - the verifier findings of both rounds;
  - my own checks on 2026-10-15:
    - the GGUF tensor tables of 15 files, read with HTTP range requests (headers only, no weights) [S128]; the two antirez V4 Flash headers were re-parsed for this draft;
    - Hugging Face API listings and metadata;
    - the papers and repository documents marked as re-read in section 6;
    - read-only status commands on Kevin's Mac (`headroom status`, `df -H`, `sysctl`) [S129].
- **Where experiments run.** Every experiment proposed here runs on the 8×H100 host. The Mac is only the target spec. Its numbers come from Apple, reviewers, the ds4 maintainer, and the status commands above.
- **Citations:** `[Sn]` points to section 6. Sources S1-S108 keep the read level the round-1 sweep agent recorded, unless section 6 says a later draft re-read them ("round 2" is the second draft, "round 3" this one).

**Conventions**
- **Units.** GB = 10^9 bytes and GiB = 2^30 bytes. "bits" means bits per weight (bpw). The Mac has 128 GiB = 137.4 GB of memory.
- **measured:** someone ran the model and reported the number. The label says who:
  - "maintainer": the engine's author;
  - "maker": the person who made the quant;
  - "community report": not a controlled measurement.
- **estimate:** my arithmetic, using the model in section 2.

---

## 1. The short answer

Kevin asked whether a 700B-1T open model such as Kimi can be made to run usefully on his Mac. The Mac is an M5 Max with 128 GiB of unified memory and a 2 TB SSD.

**A 700B-class model already runs on a 128 GB M5 Max like this one by streaming its experts from the SSD, at about 4-5 tokens/s (measured by the ds4 maintainer on their machine; this Mac's 2 TB drive is untested and does not have room for the 211 GB file today, section 5). Kimi has no maintained streaming engine on the Mac. Community reports on 128 GB Macs give about 1.7 tokens/s on an M4 Max (engine and quant not stated) and 0.5 tokens/s with an experimental streamer on a 128 GB M3 Max. My estimate for Kimi, with other work stopped, is 2.5-5.8 tokens/s if a streamer reads the SSD at 5.85-10.6 GB/s, a rate assumed from a Linux testbed, and 1.5-2.2 tokens/s at 3.4 GB/s, the rate the one quantified macOS streamer implies. Long prompts take minutes. For interactive use, a smaller model that fits in memory is still the better choice.**

### What runs on this Mac today

**In memory (fastest).**
- **DeepSeek V4 Flash 0731 at about 2 bits.** The model has 284B total and 13B active parameters (April card [S12]; 284.3B / 13.27B by tensor count of the 0731 file [S128]) and an MIT licence. The file is antirez's ds4 Q2, 86.7 GB.
  - On a 128 GB M5 Max the ds4 maintainer measured [S95]:
    - 39.4 tokens/s decode and 790 tokens/s prompt processing (prefill) at 2K context;
    - 34.4 and 557 at 32K;
    - 27.6 and 399 at 64K.
  - These numbers were refreshed on 2026-08-05 and do not name the checkpoint [S136]. ds4's current Q2 download is the 0731 checkpoint [S110].
  - Artificial Analysis scores the full-precision 0731 model 34 at its "max" reasoning setting. Kimi K2.6 scores 27 [S105].
  - The 2-bit cost is known only as fidelity to the full model: KL divergence 0.41 and 78.98% top-token agreement [S117]. Its cost on real tasks is not measured (gap G4).
- **gpt-oss-120b.** 63.4 GB, Apache-2.0, natively 4-bit.
  - A community report measured 105 tokens/s decode and 1,833 tokens/s prefill on this chip with upstream llama.cpp [S97].
  - It is weaker: it scores 12 on the same index.
- **Qwen3-235B-A22B-2507 at 2-3 bits.** 88.8-104.2 GB, Apache-2.0.
  - Estimate: 27-38 tokens/s at short context and 17-23 at 32K.
  - The 3-bit file fits only up to about 41K tokens of context.
- **GLM-5.3-Flash at 2 bits: worth testing, estimate only.**
  - The model has 320B total and 18B active parameters and an MIT licence. It scores 42 on the same index [S116].
  - ds4 lists its 96.5 GB Q2 file for a 128 GB Mac "with modest initial context" [S110].
  - Estimate: 28-37 tokens/s. No speed or quality has been published for this file.

**By streaming experts from the SSD.** The ds4 maintainer measured these on a 128 GB M5 Max on 2026-09-06 [S109]:
- **Full GLM 5.3** at IQ2_XXS, a 211 GB file. The model has 753B total and 40B active parameters. It scores 45 on the index, the highest of the models here [S116].
  - Generation: **4.1-5.1 tokens/s**, at 8K context with a 61 GiB expert cache (three-run medians).
- **DeepSeek V4 Flash Vision Experimental** with its native MXFP4 experts, a 156 GB file (ds4 target `ds4f-vision-mxfp4`). This is a different checkpoint from 0731 [S110].
  - Generation: **12-19 tokens/s**. Prefill: **263-300 tokens/s**. One run, with an 86 GiB expert cache.
- **GLM-5.3-Flash Q4_K**, a 191 GB file.
  - Generation: 12-15 tokens/s. Prefill: 104-121 tokens/s.
- ds4 calls these "workload references, not a speed guarantee". The generation numbers include the wait for the first token.
- None of these streamed files has a measured quality cost at the bits used.

**What these need from the Mac.**
- **Memory.** When I checked on 2026-10-15, Headroom showed 57.6 GiB (61.8 GB) free [S129]. Two later readings that day gave 46.1 and 70.4 GiB, so treat any single reading as a snapshot that moves by about ±15 GB. V4 Flash Q2 needs about 88 GB at 32K (ds4 plans 81.62 GiB for the same-size Vision-Exp Q2 file [S108]), so other sessions, Chrome and the dev servers must stop first.
- **Disk.** 203 GB was free [S129]. The streamed files need 156-211 GB plus headroom (section 5).

### What Kimi specifically needs

- **Size.**
  - K2-Thinking, K2.5, K2.6 and K2.7-Code ship natively at INT4, about 595 GB [S6, S9].
  - K2-Instruct and K2-Instruct-0905 shipped in FP8, 1,029 GB [S9].
  - The smallest published files in the K2 family are:
    - 235.1 GB: ubergarm smol-IQ1_KT, 1.84 bits, ik_llama.cpp only;
    - 239.5 GB: Unsloth K2.5 UD-TQ1_0, mainline llama.cpp [S134].
  - That is 1.7 times the Mac's memory, so running Kimi on this Mac means streaming.
- **An engine.**
  - ds4 does not list Kimi [S110].
  - Stock llama.cpp reads files larger than memory through mmap. flash-moe measured mmap as 5 times slower than pread on macOS [S135].
  - No maintained or supported Metal streamer for Kimi K2 exists. One experimental MLX streamer that reads experts with pread ran K2-Instruct at 4 bits (578 GB) on a 128 GB M3 Max at 0.5 tokens/s, using 7.1 GB of RAM [S139].
- **Speed (estimate)** for Kimi K2.6 at about 2.6 bits (the 340.5 GB file), at short context:
  - with a purpose-built streamer like ds4 and all other work stopped (about 75 GB of expert cache, 23% of the pool):
    - **2.5-5.8 tokens/s** if it reads the SSD at 5.85-10.6 GB/s;
    - **1.5-2.2 tokens/s** at 3.4 GB/s;
  - at the free memory of the first reading today (about 45-47 GB of cache, 14% of the pool): **1.4-3.0 tokens/s**, or 0.9-1.0 at 3.4 GB/s;
  - with stock llama.cpp mmap: about **0.5-1.4 tokens/s**.
- **Read rates behind these estimates.** 5.85-10.6 GB/s is an assumption carried over from a Linux testbed: 43% (the SSD-LLaMA paper's best baseline) to 78% (SSD-LLaMA itself) of peak [S36], applied to the reviewers' 13.6 GB/s. No streamer has measured it on a Mac. 3.4 GB/s is the low case: it is what flash-moe's measured read time on macOS implies [S135].
- **Long prompts (estimate).** With 4,096-token chunks, ds4's documented default for DeepSeek [S95], a 30,000-token prompt takes about 6-12.5 minutes. About 3-6 minutes is a lower bound, reached only if the whole prompt went through each layer in one batch (section 3b).
- **Measured comparisons.**
  - Two community reports on a 128 GB Mac: about 1.7 tokens/s for Kimi K2.5 on an M4 Max, with the engine and quant not stated [S51]; and 0.5 tokens/s for K2-Instruct 4-bit with the experimental streamer above, on an M3 Max [S139].
  - GLM 5.3 is the nearest measured case. It reads about 5.8 GB of experts per token, against 6.9 GB for the Kimi file, from a smaller expert pool (187 GB against 331 GB). It measures 4.1-5.1 tokens/s.
- **Quality at about 2 bits.**
  - Most GGUF files have only fidelity data: K2.6 UD-Q2_K_XL raises perplexity by 31% [S15]. The exception is the GSQ paper's AgentBench comparison, which includes Unsloth's K2.5 UD-IQ1_M GGUF at 2.4 bits (row K2b).
  - Task results at about 2 bits come from GSQ at 2.13 bits (294 GB) [S111, S112], and from REAP-50 plus INT4 (row K4):
    - K2.6 GPQA-Diamond: 87.21 → 83.16;
    - K2.6 AIME25: 90.00 → 87.78.
  - The published K2.6 GSQ checkpoint is CUDA-only: it needs vLLM with humming kernels on Hopper or Ampere GPUs [S112].
  - GSQ can also refine an existing GGUF K-quant file and write it back in the same format, which runs unchanged on llama.cpp, so that route is Metal-compatible. It has been tested only on dense Qwen3-8B and Qwen3-4B, not on Kimi [S111, S138].
- **Disk.** The 340.5 GB file fits only if the space Kevin is freeing comes on top of the 203 GB free now (section 5).
- **Shrinking Kimi to about 100 GB.**
  - That needs 0.78 bits per parameter (100 × 8 / 1,026.4). Only removing experts gets there: with experts at 2-2.7 bits, 64-74% of them must go (gap G1).
  - What pruning did to Kimi K3 [S113]:
    - **50% removed** (Nota's evaluation, which includes a REAP baseline): GPQA-Diamond falls 17-20 points (86.36 → 66.67-69.19), while HumanEval+ holds (82.32 → 82.32 and 81.71);
    - **50% and 75% removed without calibration:** GSM8K falls from 95.5% to 68.2% and 34.4%;
    - **80% removed, experts kept at native MXFP4:** single greedy prompts drift into lists and loop in Chinese, but "The capital of France is" is answered "Paris";
    - **82% removed plus 2-bit experts:** the same factual probe fails (it loops);
    - above 50%, the coding evidence is one greedy prompt per build.
  - So a 100 GB Kimi would at best be a coding specialist, and even that is untested. Nobody has measured one (gap G1).
- **Full-quality interactive Kimi** needs about 600 GB of fast memory. Two 512 GB M3 Ultra Mac Studios ran native INT4 at 15 tokens/s [S47].

### Why

- Decode speed is roughly the bytes read per token divided by the bandwidth.
- **Memory.** The M5 Max has 614 GB/s. Decoders on this chip use 47-61% of it at short context (measured; section 2, A2), and less at long context.
- **SSD.**
  - Apple quotes up to 14.5 GB/s, measured on an 8 TB unit [S126]. Reviewers measured 12.6-13.6 GB/s on 4 TB units [S3, S4].
  - No 2 TB M5 Max has been tested, and Kevin's drive is 90% full [S129].
  - No streamer's read rate has been measured on this Mac. I assume 5.85-10.6 GB/s for a purpose-built streamer (94-171 ms per GB that misses the cache), carried over from SSD-LLaMA's Linux results [S36]. flash-moe's measured read time on macOS implies only 3.4 GB/s (about 290 ms per GB) [S135], so I also give that low case. For stock mmap I assume about 2 GB/s (about 500 ms per GB). That is an assumption, not a measurement: flash-moe's "5x slower than pread" against its implied 3.4 GB/s points lower, so the mmap estimates may be optimistic.
- **So:**
  - a model that fits in memory runs several times faster than a bigger model that has to stream;
  - streaming works best when each token reads few expert bytes and the cache holds a large share of the expert pool. V4 Flash Vision-Exp MXFP4 reads 3.45 GB of experts per token, and its cache held 63% of the pool.

---

## 2. Feasibility table

### Assumptions used by every estimate

- **A1. Memory bandwidth.**
  - 614 GB/s: Apple's figure for the 40-core-GPU M5 Max, the only M5 Max sold with 128 GB [S2].
  - Some third-party sites list 540-546 GB/s. Apple's figure is used.

- **A2. Decode efficiency e**, the share of 614 GB/s that a runtime actually achieves. Recalibrated with bytes per token measured from the files (A3):
  - **DeepSeek V4 Flash ds4 Q2 on the M5 Max** [S95]:
    - at 2K context: 39.35 tokens/s × 9.57 GB = 377 GB/s, so e = 0.61;
    - adding KV reads of about 8.6 KB per token of context (ds4's 8.39 GiB at 1M tokens [S108]): e = 0.57 at 16K, 0.55 at 32K and 0.46 at 64K.
  - **gpt-oss-120b on the M5 Max**:
    - llama.cpp: 105 × 3.59 GB = 377 GB/s, so e = 0.61 [S97];
    - MLX (oMLX, 1K context): 79.7 × 3.59 = 286 GB/s, so e = 0.47 [S89].
  - **Kimi K2.6 on an M3 Ultra** (819 GB/s), community report [S46]:
    - an MLX build named "Kimi-K2.6DQ3_K_M-q8" (oMLX label "4bit"), not a GGUF; four oMLX runs give 20.3-22.0 tokens/s at 1K context (20.3, 20.8, 21.7 and 22.0), with 439.6 GB peak memory;
    - I did not read its tensor table. If the "q8" means 8-bit non-expert weights (10.55B at about 8.5 bits with group scales = 11.2 GB read per token) and the rest of the peak is the expert pool, it reads about 20 GB per token, so e ≈ 0.49-0.54. This layout is inferred from the name.
  - **I use e = 0.47-0.61 (288-377 GB/s) at short context.**
    - At 32K and beyond I add the KV read explicitly (A4). Expect the low end of the range there.
    - Round 1 used 0.35-0.46, because it undercounted bytes per token (A3).

- **A3. Bytes per token** = routed-pool bytes × k/E + non-routed bytes.
  - k/E is the share of experts each token uses.
  - The non-routed bytes (the "spine") are attention, shared experts, dense layers, routers and the output head.
  - The token embedding and any MTP (multi-token prediction) block are excluded: decode reads one embedding row, and MTP runs only with speculative decoding.
  - Both terms come from the GGUF tensor table [S128], not from average bits.
  - Every file keeps its spine at 4-14 bits, so round 1's rule (active parameters × average bits) undercounted.

  | File | File size (GB) | Routed pool (GB) | Routed per token (GB) | Spine (GB) | Total per token (GB) | Spine bits |
  |---|---|---|---|---|---|---|
  | Kimi K2.6 UD-Q2_K_XL | 340.48 | 331.14 | 6.90 | 8.53 | **15.42** | 6.47 |
  | Kimi K2-Thinking UD-TQ1_0 | 246.85 | 239.18 | 4.98 | 7.00 | **11.98** | 5.31 |
  | DeepSeek R1 UD-Q2_K_XL | 226.60 | 215.71 | 6.74 | 10.37 | **17.11** | 5.12 |
  | DeepSeek R1 UD-IQ1_S | 140.23 | 129.13 | 4.04 | 10.58 | **14.61** | 5.23 |
  | V4 Flash 0731, ds4 Q2 (antirez IQ2XXS) | 86.72 | 77.91 | 1.83 | 7.74 | **9.57** | 9.14 |
  | V4 Flash 0731, Unsloth UD-IQ3_XXS | 104.21 | 96.82 | 2.27 | 6.95 | **9.22** | 8.20 |
  | V4 Flash Vision-Exp, MXFP4 experts (ds4) | 155.98 | 147.17 | 3.45 | 7.74 | **11.19** | 9.14 |
  | Qwen3-235B-2507 UD-Q2_K_XL | 88.77 | 83.81 | 5.24 | 4.60 | **9.84** | 4.99 |
  | Qwen3-235B-2507 UD-Q3_K_XL | 104.15 | 99.18 | 6.20 | 4.61 | **10.81** | 5.00 |
  | GLM-4.6 UD-TQ1_0 | 84.14 | 74.18 | 3.71 | 8.18 | **11.89** | 4.08 |
  | GLM-5.3-Flash, ds4 Q2 | 96.51 | 85.61 | 2.38 | 7.93 | **10.31** | 7.66 |
  | GLM-5.3-Flash, ds4 Q4_K | 190.88 | 171.23 | 4.76 | 14.05 | **18.81** | 13.57 |
  | GLM 5.3, ds4 IQ2_XXS | 211.08 | 186.86 | 5.84 | 19.72 | **25.56** | 8.67 |
  | gpt-oss-120b MXFP4 (ggml-org) | 63.39 | 61.07 | 1.91 | 1.69 | **3.59** | 8.71 |

  - Parameter counts from the same tables, excluding MTP blocks:
    - Kimi K2: 1,026.4B total; per token 21.14B routed + 10.55B spine (matches A8);
    - DeepSeek R1: 671.0B; 20.43B routed + 16.19B spine, so routed is 56% of active parameters and 39% of the bytes;
    - GLM-4.6: 352.8B total, 32.9B active;
    - GLM 5.3: 743.9B total, 40.8B active;
    - GLM-5.3-Flash: 313.3B total, 16.7B active;
    - V4 Flash: 284.3B total, 13.27B active. All 43 blocks in the antirez files are trunk layers (the config has 43 hidden layers); ds4 ships the MTP layer as a separate 3.81 GB file [S133].
  - GLM-5.3-Flash keeps its linear-attention (KDA) layers in BF16, hence the 13.57-bit spine in the Q4_K file.

- **A4. Decode for a model held in memory.**
  - tokens/s = (e × 614 GB/s) ÷ (bytes per token + KV bytes read per token).
  - The KV read per token is the context length × KV bytes per token (A9). Models with GQA or MLA attention read their whole cache for every token.

- **A5. SSD bandwidth.**
  - **Apple** quotes "up to 14.5GB/s", measured on a preproduction 8 TB unit with FIO, 1 MB requests and queue depth 8 [S126].
  - **Reviewers** measured 13.6 GB/s (The Verge, via S4), 12.7 GB/s (PetaPixel, via S4) and 12.6 GB/s (Computerworld, Blackmagic Disk Speed Test, 12,587.3 MBps) on 4 TB units [S3, S4].
  - **No 2 TB M5 Max test exists.**
    - A video review says larger drives are faster because they have more NAND chips. I saw this only as a search summary and did not verify it [S127].
    - Kevin's drive is 2 TB and 90% full [S129]. It stays unmeasured, because experiments do not run on the Mac.
  - **SSD-LLaMA** [S36], on a Linux PC with a 9 GiB/s NVMe:
    - it reaches 77.7% of sequential bandwidth;
    - its best baseline reaches 43.2%. The paper does not name it; the read-bandwidth ratios suggest KTransformers;
    - its read bandwidth is up to 2.82 times llama.cpp's and 1.93 times KTransformers'. These are ratios of SSD read bandwidth. Its decode speedups are 1.35-3.44 times over llama.cpp and 1.57-15.61 times over KTransformers.
  - **flash-moe on macOS** [S135]:
    - mmap was 5 times slower than pread;
    - its decode reads take 2.41 ms per layer for 4 experts at about a 71% page-cache hit rate. That implies only 3.4 GB/s, against the 17.5 GB/s sequential speed it reports for the drive.
  - **Assumption: 5.85-10.6 GB/s for purpose-built pread or O_DIRECT streamers** (SSD-LLaMA's 43-78% on Linux, applied to 13.6 GB/s), so each GB missed costs 94-171 ms. It is carried over from a Linux testbed and not measured on any Mac.
  - **Low case: 3.4 GB/s**, from flash-moe's measured decode reads, the only macOS streamer whose read rate can be quantified. Section 1 and row K2 give the Kimi estimate at both.
  - **I use about 2 GB/s for stock llama.cpp mmap on macOS**, about 500 ms per GB missed.
  - Small reads per layer can fall below 5.85 GB/s, as flash-moe shows, so the low end is the more likely one for decode.

- **A6. Decode when streaming.**
  - Time per token = (1 − h) × R ÷ B + (A + KV read) ÷ (e × 614 GB/s), where:
    - R = routed bytes per token and A = total bytes per token (A3);
    - h = the expert-cache hit rate (A7);
    - B = the SSD bandwidth (A5).
  - SSD reads and compute are assumed not to overlap.
  - **Two costs are left out:**
    - if the cache is the OS page cache read through pread, each hit is also a CPU copy (hit bytes ÷ copy bandwidth, which is unmeasured). An engine that keeps its own cache, as ds4 does [S109], avoids this;
    - about 60 serialized I/O and GPU round trips per token, because routing is resolved layer by layer.
  - **Back-tests:**
    - **flash-moe** (Qwen3.5-397B, M3 Max) [S135]: with B set to its measured 3.4 GB/s, A6 predicts 5.5-5.7 tokens/s. It measured 4.36, so the real time per token is 25-32% longer than A6.
      - Because 3.4 GB/s is derived from flash-moe's own measured read time, the SSD term (145 ms) is exact by construction. The whole gap is in the memory and compute term: the remaining 84.5 ms is 2.2-2.9 times A6's memory term (7.2 GB ÷ 188-244 GB/s = 29.5-38.3 ms).
    - **ds4, full GLM 5.3** (M5 Max; 65.9 GB cache = 35% of the 186.9 GB pool) [S109]:
      - the memory term is 70-91 ms of the measured 196-245 ms per token;
      - the rest fits A6 with a miss rate of 0.19-0.32 at 10.6 GB/s, or 0.10-0.18 at 5.85 GB/s. That is h = 0.68-0.90.
    - **ds4, V4 Flash Vision MXFP4** (92.6 GB cache = 63% of the 147.2 GB pool), at 19.3 tokens/s: fits A6 only with h = 0.93-0.98, or if ds4 overlaps reads with compute.
  - **Conclusion.** A6 agrees with ds4's measurements for plausible hit rates, but it cannot separate h from B. Gap G2 measures h. The flash-moe overhead is a downside risk; I did not apply it, because the ds4 back-tests fit without it. If Kimi's memory term carried the same 2.2-2.9 times overhead, row K2's stopped case would be 2.0-4.5 tokens/s instead of 2.5-5.8.

- **A7. Cache size and hit rate.**
  - **Cache** = available memory − resident non-routed weights (spine + embedding) − KV at the stated context − 3 GiB (3.2 GB) of buffers. The same rule applies to every case. For the Kimi K2.6 Q2 file:
    - **all other work stopped:** I assume 88 GB available. That is about what ds4 plans for V4 Flash Q2 at 32K (81.62 GiB = 87.6 GB), a load that runs on a 128 GB Mac once other work stops [S108]. It is my choice, not a measurement. 88 − 9.3 − 0.3 (KV at 2K) − 3.2 = 75.2 GB, 22.7% of the 331.1 GB pool; at 32K (KV 2.3-4.4 GB), 71.1-73.1 GB, 21.5-22.1%;
    - **free memory at the first reading today:** 57.6 GiB = 61.8 GB [S129] − 9.3 − 2.3 to 4.4 (KV at 32K) − 3.2 = 45-47 GB, 13.6-14.2% of the pool. This is a snapshot: free memory read between 46.1 and 70.4 GiB the same day.
  - **Kimi K2's hit rate has not been measured.** The brackets come from S82:
    - DeepSeek-V3 (256 experts, top-8): LRU 48% with 12.5% of experts cached;
    - Kimi K3 (896 experts, top-16): 44% with 3.6% cached and 78% with 25%.
    - S82 does not say whether it replays a token's experts at a layer as one event. Replaying them one at a time inflates LRU misses (by 27.4% in S123's Qwen3-30B-A3B test with 8 concurrent requests). If S82 did that, these brackets lean pessimistic.
  - **Brackets used:**
    - h = 0.45-0.55 at about 10-15% cached (lowered from round 1);
    - 0.70-0.80 at 22-26%;
    - 0.75-0.85 at 32-38%, extrapolated past the measured points;
    - 0.85-0.90 at 55-60%.
    - K3's measured curve gives about +0.17 in h per e-fold of cache share (from S82's two K3 points). For every share used in this dossier (10.7% to 14%, 22.7%, 32-36%, 56.8%), that moves h by 0.03 or less from the bracket's anchor, inside the bracket's width. Most of these shares sit below their anchor, so read the low end of each h range as the more likely one.
  - **Batching lowers hit rates.** For K3 at 25% cached, the hit rate fell from 78% with one stream to 64% with four [S82].
  - **Pruned models.** The hit rate must come from the original model's routing, not from the share of the pruned pool that is cached.
    - Pruning removes the coldest experts.
    - So a cache holding X% of a 50%-pruned pool holds the same hottest experts as a cache of X/2% of the full pool, plus any redirected traffic that lands on them.

- **A8. Kimi K2 shape**, from the K2 config [S5]; the tensor table confirms it.
  - Each expert has 3 × 7,168 × 2,048 = 44.04M parameters.
  - Per token, 60 MoE layers × 8 experts = 21.14B routed parameters are read.
  - Another 10.55B parameters (the spine) are read for every token: attention 6.17B, shared expert 2.64B, dense layer 0.40B, routers 0.17B and output head 1.17B.
  - Total 1,026.4B parameters, of which the expert pool is 1,014.7B.
  - The K2.6 config: sigmoid router scores, `norm_topk_prob` true, routed scaling factor 2.827, no MTP layer.

- **A9. KV bytes per token**, from the configs and the GGUF metadata.
  - **Kimi K2.x and DeepSeek V3/R1** (MLA attention, 61 layers, latent 512 + rope 64):
    - vLLM and SGLang store 576 values per layer: 576 × 61 × 2 bytes = **70,272 bytes per token** (35,136 with an FP8 KV cache);
    - llama.cpp's 2025 layout stored K (576 values) and V (512) separately: 132,736 bytes per token. That matched a measured 8,296 MiB at 64K for R1 [S45]. Current builds may differ, so check the log;
    - range at 32K: 2.1-4.0 GiB.
  - **Qwen3-235B:** 94 layers × 4 KV heads × 128 × 2 × 2 bytes = 192,512 bytes per token. That is 5.9 GiB at 32K, 11.75 GiB at 64K and 23.5 GiB at 128K.
  - **GLM-4.6:** 92 layers × 8 KV heads × 128 × 2 × 2 bytes = 376,832 bytes per token. That is 11.5 GiB at 32K and 23 GiB at 64K.
  - **gpt-oss-120b:** 0.3 GB per 8,192 tokens [S98]. Half its layers use a 128-token sliding window.
  - **DeepSeek V4 Flash in ds4** [S108]:
    - 8.39 GiB of KV at 1M tokens;
    - but ds4's plan budgets 16.4 GiB of context-dependent memory at 1M (97.15 − 80.76 GiB). Use 16.4 GiB for long-context fits;
    - the compressed cache is why V4 Flash slows down least as context grows.
  - **On the H100 host,** MLA's single latent KV head is copied to every GPU under tensor parallelism (section 4).

- **A10. Memory budget.**
  - **Physical memory:** 128 GiB (137.4 GB).
  - **Default Metal working-set ceiling:** 107.52 GiB (115.4 GB), with `iogpu.wired_limit_mb = 0` [S1]; re-checked on 2026-10-15 [S129]. It can be raised with sudo; the setting resets on reboot.
  - **Running at the first check (2026-10-15)** [S129]. Headroom reports binary GiB labelled "GB": its machine total of "128 GB" is `hw.memsize` = 137.4 × 10^9 bytes. So:
    - 57.6 GiB (61.8 GB) free (45%);
    - swap 11.3 GiB used and 57.0 GiB compressed, with a memory-pressure warning;
    - Claude sessions held 81.1 GiB, Chrome 24.4 GiB, and two dev servers 17.4 GiB and 7.2 GiB.
    - This is a snapshot. Later readings the same day: 46.1 GiB free (the round-2 verifier) and 70.4 GiB (this draft).
  - **Fit labels assume other work is stopped.** Each counts weights + KV at the stated context + 3 GiB of buffers:
    - **Yes:** 95 GiB or less;
    - **Tight:** 95-107.5 GiB;
    - **No:** more than 107.5 GiB.
  - At the first reading, any model that needs more than about 62 GB (57.6 GiB) means stopping other work.

### Table

Estimates use A2-A7. "Short" means 2K context or less.

**Held in memory**

| # | Model × approach | File size | Fits in 128 GB with KV + OS? (other work stopped) | Decode tokens/s from bandwidth math | Measured tokens/s (source) | Known quality cost (source) |
|---|---|---|---|---|---|---|
| O1 | **gpt-oss-120b** (116.8B / 5.1B active, Apache-2.0), native MXFP4 | 63.4 GB [S128]. Every GGUF is 62.6-63.0 GB [S10]. | **Yes.** 64.0 GB at 8K, 64.9 at 32K, 68.5 at 131K with llama.cpp [S98]. That is still more than the 61.8 GB (57.6 GiB) free at the first reading. | **estimate**: 3.59 GB per token → **80-105**. | **community report** on an M5 Max 128 GB: llama-bench decode (tg128) 105, prefill (pp2048) 1,833 with the Metal 4 tensor API on, using upstream llama.cpp (the issue cites release b9592). With the tensor API off, prefill is 877; the poster says this approximates LM Studio's runtime [S97]. **community report**: oMLX decode 79.7 at 1K, 41.4 at 32K, 14.0 at 128K; prefill 1,023-1,658 [S89]. | No quantization cost (natively 4-bit). Index 12 [S105]. |
| F1 | **DeepSeek V4 Flash 0731** (284B / 13B active per the April card [S12]; 284.3B / 13.27B by tensor count [S128]; MIT), ds4 Q2: routed experts IQ2_XXS (gate/up) + Q2_K (down); attention, shared expert and output at Q8 | 86.72 GB (80.8 GiB) [S128] | **Yes.** For the Vision-Exp Q2 file (same size, a different checkpoint), ds4 plans 81.62 GiB at 32K and 97.15 GiB at 1M tokens, and a 128 GB M4 Max ran that file at 1M context with about 103 GB wired and flat swap [S108]. Needs about 88 GB at 32K. | **estimate**: 9.57 GB per token → **30-39**. | **measured** (maintainer) on an M5 Max 128 GB, decode / prefill: 39.35 / 790.18 at 2K; 36.14 / 572.53 at 16K; 34.36 / 557.04 at 32K; 27.64 / 398.50 at 64K [S95]. **community report**, April checkpoint (run dated 2026-06-14, before 0731 existed): a ds4 "q2–q4" mix (91 GB file, 103 GB in use), 33 / 28 decode at 128 / 8K context, with reasoning tokens counted [S96]. | 0731 file, context 5,632, against BF16: KLD 0.408, 78.98% same top token, perplexity 5.60 vs 4.53 [S117]. Unsloth's table (+34% perplexity, 78.15%, context 512) is for an unconfirmed checkpoint [S23]. Task cost unmeasured. A community card that returns HTTP 401 reportedly gives about −8 points (78.09 → 69.85, thinking off) for a 90.9 GiB file; that size matches ds4's q2–q4 mix (97.6 GB), not ds4 Q2, and its checkpoint is not stated. Search summaries only [S131]. |
| F2 | V4 Flash 0731, Unsloth UD-IQ3_XXS | 104.21 GB (97.1 GiB) [S128] | **Tight.** 97.1 GiB of weights plus context memory. Unsloth says about 110 GB of RAM [S23]. | **estimate**: 9.22 GB per token → **31-41**. | None. | KLD 0.261, 83.46% same top token [S117]. |
| F3 | **GLM-5.3-Flash** (320B / 18B active per Artificial Analysis; MIT; index 42), ds4 Q2 | 96.51 GB (89.9 GiB) [S128] | **Yes by A10's rule**, if the KV cache holds the F16 MLA latent: 89.9 GiB of weights + 0.43 GiB of KV at 32K (11 trunk MLA layers × (512 latent + 128 indexer-key values) × 2 bytes = about 14 KB per token) + 0.13 GiB of linear-attention state + 3 GiB = 93.4 GiB, under 95 GiB up to about 150K. ds4 still says it fits a 128 GB Mac only "with modest initial context", and to stop other memory-heavy work [S110]; its own buffer sizes are not documented. | **estimate**: 10.31 GB per token → **28-37**. | None published for the Mac. | No quality data for this file. Index 42 at full precision [S116]. |
| F4 | Qwen3.8-Flash-Next (180B / 6B active per Artificial Analysis; Qwen Community License 1.0; index 40), ds4 Q2 | 147.2 GB file: 41.73 GiB of weights held in memory + 95.37 GiB of n-gram tables read from disk [S110] | **Yes.** About 42 GiB resident; ds4 targets 64 GB Macs. | Not estimated: the per-token n-gram reads from disk are not modelled. | DGX Spark only: 22.6 decode at 8K, 745 prefill [S110]. | None for this file. |
| Q1 | **Qwen3-235B-A22B-2507** (235B / 22B active, Apache-2.0), UD-Q2_K_XL | 88.77 GB (82.7 GiB) [S128] | **Yes** up to about 51K context; **Tight** up to about 119K. 91.5 GiB at 32K, 97.4 at 64K, 109.2 at 128K (No). | **estimate**: 9.84 GB per token → **29-38** short; **18-23** at 32K (+6.3 GB of KV read per token). | None in the sweeps. | Not measured for this model. On 671B models, dynamic 2-bit costs 1-6 points [S19, S20]. |
| Q2 | Qwen3-235B-2507, UD-Q3_K_XL / MLX 3-bit DWQ | 104.15 / 102.9 GB [S128, S24] | **Tight** up to about 41K (105.9 GiB at 32K). **No** beyond. | **estimate**: 10.81 GB per token → **27-35** short; **17-22** at 32K. | **community report** via the SiliconScore aggregator: about 30 at 1K, about 100 GB, 3-bit MLX, 128 GB M4 Max (546 GB/s), which implies e ≈ 0.6. The Reddit original was not fetched [S102]. | Not measured for this model. MLX DWQ model cards publish no metrics [S25]. |
| Q3 | Qwen3-235B-A22B, 4-bit | Q4_K_XL 134.3 GB; MLX 4-bit 132.2 GB; GPTQ-Int4 124.5 GB [S24, S26] | **No.** | Not estimated. | **community report**: 24 with MLX and 16 with GGUF, 4-bit, 512 GB M3 Ultra [S102]. | 4 bits is usually within 1% [S29]. |
| G1 | **GLM-4.6** (352.8B / 32.9B active by tensor count, MIT), UD-TQ1_0 | 84.14 GB (78.4 GiB) [S134] | **Yes** up to about 38K; **Tight** up to about 73K (92.9 GiB at 32K, 104.4 at 64K). The same-size GLM-4.7's UD-IQ1_S (97.2 GB) is Tight up to about 39K [S24]. | **estimate**: 11.89 GB per token → **24-32** short; **12-16** at 32K (+12.35 GB of KV read). | None in the sweeps. | Not measured for GLM. 1 bit costs 16-21 Aider points on DeepSeek-V3.1 [S19] and collapses a dense 27B model [S104]. |
| G2 | GLM-4.6 REAP-pruned (Cerebras 218B / 252B / 268B) + quantization | BF16 and FP8 checkpoints only [S61]. Arithmetic at 3.5 bits: 218B → about 95 GB (88.8 GiB). | 218B at 3.5 bits: **Tight** up to about 44K (103.3 GiB at 32K); **No** at 64K. | Not computed. | None. | Cerebras reports coding retention only, e.g. 94.1% on LiveCodeBench for GLM-4.5-Air at 50% [S60]. REAP loses general knowledge outside the calibration domain [S59]. |
| G3 | GLM-4.6 at BF16 or 4 bits | 713.6 GB stored [S134]. 4-bit by arithmetic: about 201 GB. | **No.** | Not estimated. | None. | Not measured. |
| D4 | DeepSeek V3-0324 with expert pruning (192 of 256 experts kept, 6 active instead of 8) + 1-2-bit mixed precision (2509.25689; published as moxin V3-Mini-Exp) | **113.38 GB (105.6 GiB, 1.79 bpw)** [S130]. The paper says "103GB", probably meaning GiB. | **No** under the default ceiling: 108.6 GiB with no context at all. It needs a raised wired limit (sudo) and a short context. | **estimate**: 13-14.4 GB per token → **20-29**. | **measured** (paper): "over 5 tokens/s" on an AMD Strix Halo laptop with 128 GB in total [S22]. | The pruned model is compared only in a figure: it beats uniform IQ1_M (140 GB) on six benchmarks. The paper's "130GB" table row is the full-size, unpruned DeepSeek-V3 with mixed precision: Winogrande 77.63, MMLU 84.55, CMMLU 86.08, HellaSwag 84.58, GSM8K 93.56 [S22]. No coding or agentic evaluation. |

**Streamed from the SSD, measured on an M5 Max 128 GB by the ds4 maintainer** (automatic cache sizing, no speculative decoding) [S109]

| # | Model × approach | File size | Fits? | Decode from bandwidth math | Measured tokens/s (source) | Known quality cost (source) |
|---|---|---|---|---|---|---|
| S1 | **GLM 5.3** (753B / 40B active; licence "glm-5.3"; index 45 [S116]), ds4 IQ2_XXS | 211.08 GB (196.6 GiB) [S128] | **No** in memory; streamed. Needs 211 GB of disk. | A6 back-test only (A6). | **measured**: 8K context, 61.35 GiB effective expert cache. Generation after a 16-token tool-result append rose from 4.09 to 5.11 when ds4 began caching short appends (three-run medians, 64 tokens). The append itself fell from 30.8 s to 2.9 s [S109]. | Not measured at IQ2_XXS. |
| S2 | **DeepSeek V4 Flash Vision Experimental**, native MXFP4 routed experts (ds4) | 155.98 GB (145.3 GiB) [S128] | Streamed. | A6 back-test only. | **measured**: prefill 300 (8K prompt) and 263 (4K append); generation 11.9 and 19.3 after each, including the first-token wait. Single run, 86.2 GiB expert cache [S109]. | The same-layout MXFP4 file of the 0731 checkpoint has KLD 0.155 and 87.4% same top token [S117]. Vision-Exp is a different checkpoint [S110]. |
| S3 | **GLM-5.3-Flash** Q4_K (ds4) | 190.88 GB (177.8 GiB) [S128] | Streamed. | Not estimated. | **measured**: prefill 121 (2K prompt) and 104 (1K append); generation 11.9 and 14.9. Three-run median [S109]. | Not measured. |

**Streamed from the SSD, estimated** (no measurement on a Mac)

| # | Model × approach | File size | Fits? | Decode tokens/s from bandwidth math | Measured tokens/s (source) | Known quality cost (source) |
|---|---|---|---|---|---|---|
| K1 | **Kimi K2.x** native INT4 (K2-Thinking, K2.5, K2.6, K2.7-Code; modified MIT) | 594.3-595.3 GB [S9]. K2-Instruct and K2-0905 are FP8, 1,029 GB [S9]. | **No.** 4.3 times the Mac's memory, and larger than any free-disk scenario in section 5. | Moot. Streamed with the shipped BF16 spine, it reads 33.0 GB per token (11.89 GB routed + 21.1 GB spine; embedding excluded, as in A3). A 61 GB cache (A7 rule) holds 10.7% of the 571 GB pool, so h 0.45-0.55 → about 0.8-1.7. | **measured**: 15 on 2× M3 Ultra 512 GB, MLX pipeline-parallel [S47, maintainer]. **measured**: 0.89 (16 GB RAM) to 1.03 (32 GB RAM) streamed, Kimi-K2.7-Code Q4_0 on an RTX 5090 with a 9 GiB/s NVMe [S36, paper]. | Reference. Moonshot publishes no INT4-vs-BF16 comparison [S6]. |
| K2 | **Kimi K2.6 UD-Q2_K_XL** (Unsloth, about 2.6 bits). Also: K2-0905 UD-Q2_K_XL 383.6 GB; ubergarm K2 IQ2_KL 349.4 GiB (ik_llama.cpp only) [S16, S18] | 340.48 GB [S128] | **No** in memory (2.5 times). On disk only if enough space is freed (section 5). | **estimate**, 15.42 GB per token (6.90 routed). **All other work stopped** (75.2 GB cache = 22.7%; 71-73 GB at 32K; h 0.70-0.80): **2.5-5.8** short and 2.4-5.5 at 32K with B = 5.85-10.6 GB/s (assumed, A5); **1.5-2.2** at B = 3.4 GB/s (flash-moe-derived low case); 2.0-4.5 if the memory term carries flash-moe's 2.2-2.9 times overhead (A6). **Free memory at the first reading today** (45-47 GB cache = 14%, h 0.45-0.55): **1.4-3.0**; 0.9-1.0 at 3.4 GB/s. **Stock mmap** at 2 GB/s: 0.9-1.4 with other work stopped, 0.5-0.6 today. **Prefill of a 30K prompt:** 40-73 with 4,096-token chunks (ds4's default for DeepSeek [S95]) and no cache hits, 45-82 if a managed cache serves hits after the first pass; 84-185 is a bound, for the whole prompt in one batch per layer (no overlap to full overlap of reads and compute); 8-15 with 512-token chunks (section 3b). | **community report**: about 1.7, Kimi K2.5 on a 128 GB M4 Max; engine, quant and context not stated [S51]. **community report**: 0.5, K2-Instruct MLX 4-bit (578 GB) with an experimental pread streamer, 128 GB M3 Max, 7.1 GB of RAM [S139]. | K2.6 UD-Q2_K_XL: perplexity 2.4131 vs 1.8420 at Q4, **+31%** [S15, maker]. K2-Instruct IQ2_KL (2.92 bits, from an FP8 base without INT4 training): **+7.8%** [S18, maker]. No GGUF task benchmarks. |
| K2b | **Kimi K2.5 / K2.6 GSQ** 2-bit (routed experts at 2.13 bits; humming format; modified MIT) | 293.97 GB [S112] | **No**, and this checkpoint has no GGUF or MLX build: it needs vLLM + humming-kernels on Hopper or Ampere GPUs [S112]. GSQ's GGUF K-quant route would give a Metal-compatible file, but it has not been applied to Kimi (section 3a). | Not estimated: no Mac engine for this checkpoint. | Quantization took 24 h on 8×H200 for K2.5 [S111]. | **Task results** [S111, maker]. K2.5: AIME25 95.33 → 93.00, GPQA-D 89.29 → 76.57, LiveCodeBench 61.37 → 69.37, MATH500 96.68 → 97.32. K2.6 with a broader calibration mix: AIME25 90.00 → 87.78, GPQA-D 87.21 → 83.16, MATH500 92.67 → 93.67. AgentBench, K2.5 at 2.37 bits (OS / DB / KG / ALFWorld / WebShop): 43 / 63 / 45 / 42 / 49, vs base 50 / 69 / 57 / 53 / 52 and Unsloth UD-IQ1_M (an i-quant mix, 2.4 bits) 40 / 61 / 39 / 41 / 47. GSQ quantizes only the experts; Unsloth quantizes every layer. |
| K3 | **Kimi K2 at about 1.8-1.9 bits**: ubergarm smol-IQ1_KT (1.84 bits, ik_llama.cpp only); Unsloth UD-TQ1_0 (1.92 bits, mainline llama.cpp) | 235.1 GB (K2-0905, K2.5, K2.6) [S134]. Unsloth: K2.5 239.5, K2-Thinking 246.8, K2-0905 248.6 [S16, S134]. | **No** in memory (1.7-1.8 times). | **estimate**, K2-Thinking TQ1_0, 11.98 GB per token (4.98 routed). A 76.8 GB cache (A7 rule) = 32.1% of the 239.2 GB pool, h 0.75-0.85 → **3.9-9.8**. | Not measured. Unsloth's guidance: "under 1 token" per second through mmap [S17]. | K2-Instruct IQ1_KT (1.96 bits) **+34.7%** perplexity; smol-IQ1_KT (1.84 bits) **+43.0%** [S18, maker]. No task benchmarks for these files. |
| K4 | Kimi K2.5 with REAP removing 50% of experts, native INT4 kept (kwanhee checkpoint, 519B parameters) | 288.4 GB [S64] | **No.** Its runtime is a private vLLM fork (HTTP 404 on 2026-10-15) [S132], and stock vLLM fails to load it [S64]. It cannot run anywhere without the author. | Moot. If a Mac streamer existed, with the spine requantized to about 6.5 bits (19.5 GB per token) and a 75 GB cache (A7 rule) holding about 14% of the original experts (h 0.55-0.65, A7 plus some redirected traffic): 1.1-2.4. | Only on 4×B200 (model card). | Model card [S64]: OpenLLM v1 80.77 vs 82.43 (97.99%); AIME25 95.1%; GPQA-D 88.0%; MATH500 101.5%. The MoESQ paper [S63] reports only the OpenLLM figure, and its first author uploaded the checkpoint, so the two are not independent. MoESQ is independent of REAP's authors. REAP's own 50% run on K2-Instruct: knowledge multiple-choice 0.780 → 0.643, BFCL multi-turn tool use 0.355 → 0.164, coding held [S59]. |
| K5 | Kimi K2.6 "JANGTQ" build (routed experts at about 2 bits with a Hadamard rotation and codebook; non-stock JANG runtime) | Peak memory 167.5-185.6 GB; file size not stated [S46] | **No** (1.22-1.35 times the Mac's memory). | Not estimated: the file layout is unknown. | **community report**: 19.4 decode and 90.2 prefill at 1K; 14.7 and 73.5 at 32K; 512 GB M3 Ultra [S46]. | Not independently evaluated [S46]. |
| K6 | **Hypothetical** Kimi K2 at about 100 GB: (i) 75% of experts pruned, experts at 2.7 bits, spine as in the Q2 file; (ii) 50% pruned, experts at IQ1_S (1.5625 bits, the smallest stock llama.cpp type) | Arithmetic. (i) 253.7B × 2.7/8 + 9.3 = **95.0 GB** (88.4 GiB). (ii) 507.3B × 1.5625/8 + 9.3 = **108.4 GB** (101.0 GiB). | (i) **Yes to Tight**: 93.6-95.5 GiB at 32K. (ii) **Tight to No**: 106.1-108.0 GiB at 32K. | **estimate**, held in memory: (i) 15.66 GB per token → **18-24**; (ii) 12.65 GB → **23-30**. | None. No such model exists. | **Unknown, with a negative prior** [S113]. K3 pruned 50% by REAP or Nota loses 17-20 points of GPQA-D (86.36 → 66.67-69.19) while HumanEval+ holds. K3 pruned 75% without calibration scores 34.4% on GSM8K against 95.5% for the source. At 80% with native MXFP4 experts, single prompts drift but the factual probe is answered; at 82% plus 2-bit, it fails. Coding above 50% rests on one prompt per build. This is gap G1. |
| K7 | **Kimi K3** (2.8T / 104B active, "Kimi K3 License") | Smallest full files: Unsloth UD-Q1_0, 466.4 GB [S14]; antirez IQ2_XXS / Q2_K, 858.8 GB (no README; not a listed ds4 target) [S133]. Native MXFP4 about 1.51-1.56 TB [S8]. Community REAP builds: 181.2 GB (82% pruned, MLX 2-bit), 342.5 GB (55%, GGUF), 349.7 GB (80%, MLX) [S113]. | **No** in memory or on disk (full model). The 181.2 GB pruned build targets a 192 GB machine per its card [S113]. | Not estimated. | **measured**: 0.465 decode and 1.217 prefill, streamed, RTX 5090 + 16 GB RAM [S36]. **measured**: Colibri about 9.4 s per token [S52]. **community report**: the 82%-pruned MLX build, 3.93 on a CUDA node [S113]. | UD-IQ1_S (594 GB): 78.9% top-1 agreement, perplexity +77%. UD-Q2_K_XL (861 GB): 90.4%, +19% [S14, maker]. Pruned builds, one greedy prompt each: at 82% pruned plus 2-bit, code correct and the factual probe failing; at 80% with MXFP4 experts, the factual probe answered, with drift and Chinese repetition loops [S113]. |
| D1 | **DeepSeek V3.x / R1** (671B / 37B active, MIT), official FP8 or 4-bit | FP8 about 689 GB [S9]. R1 Q4_K_M 404.4 GB (376.7 GiB) [S134]. V3.1 Q4_K_XL 387 (Unsloth's figure) [S19]. | **No.** | Not estimated. | **community report**: R1 Q4_K_M on a 512 GB M3 Ultra, llama-bench decode (tg128) 20.21, prefill (pp512) 168.90. V3.1 Q4_K_M: 14.82 and 86.09 [S43]. **community report**: R1-0528 MLX 4-bit with an 11k-token prompt, 189 prefill and 11 decode [S45]. | Q4_K_M **−0.68%** on R1's 9-benchmark average, 0% on V3 [S20, independent]. Red Hat INT4 R1-0528 keeps **99.82%** [S26, maker]. Aider (V3.1) Q4_K_XL 69.7 vs 71.6 [S19]. |
| D2 | DeepSeek R1 / V3.1, dynamic 2-3 bit | R1 UD-Q2_K_XL **226.6 GB (211.0 GiB, 2.70 bits)**; R1 Q2_K_L 244.3 GB [S134]. V3.1 Q2_K_XL 255 and Q3_K_XL 300 (Unsloth's figures, which for R1 turned out to be GiB) [S19]. | **No** in memory. | **estimate**, R1 UD-Q2_K_XL, 17.11 GB per token (6.74 routed). A 73.6 GB cache (A7 rule) = 34.1% of the 215.7 GB pool, h 0.75-0.85 → **2.9-7.1**. | **community report**: R1 UD-Q2_K_XL on 96 GB RAM + 24 GB VRAM, Linux, stock llama.cpp mmap: 1.29 decode, 2-3 prefill [S103]. **community report**: the same file fully in RAM (256 GB DDR5 + 48 GB GPU): 13.1-13.7 decode, 111-115 prefill [S39]. | R1 UD-Q2_K_XL **−0.94%**; DQ3_K_M −0.34% [S20, independent]. Aider (V3.1, non-thinking): Q2_K_XL 65.8, Q3_K_XL 68.4, full 71.6; thinking mode, 3-bit 75.6 vs 76.1 [S19]. Uniform Q2_K_L: **−8.9%** (V3), **−14.7%** (V3-0324) [S20]. |
| D3 | DeepSeek R1 / V3 at 1-1.6 bits | R1 UD-IQ1_S **140.2 GB (130.6 GiB)** [S134]. V3.2 UD-TQ1_0 161.3 GB [S24]. V3.1 TQ1_0 170 and IQ1_M 206 (Unsloth's figures) [S19]. | **No.** | **estimate**, R1 IQ1_S, 14.61 GB per token (4.04 routed). A 73.4 GB cache (A7 rule) = 56.8% of the 129.1 GB pool, h 0.85-0.90 → **6.5-13**. | None on a Mac in the sweeps. | R1 IQ1_S rated "Fair", a qualitative rating [S21, maker]. Aider (V3.1) at 1 bit: 50.7-55.7 vs 71.6 [S19]. Uniform IQ1_S V3: "entirely non-functional" [S22]. |
| Q5 | **Qwen3.5-397B-A17B** (403B / 17B active, Apache-2.0), 4-bit, streamed with flash-moe | About 224 GB. flash-moe's "209GB" is GiB: 512 × 60 experts of 6.75 MiB + 5.5 GB of other weights [S135]. | **No** in memory. | **estimate** at the model's own top-10 routing: 4.25 GB routed + 5.5 GB other = 9.75 GB per token. A 79.2 GB cache (A7 rule) = 36% of the 217.5 GB pool, h 0.75-0.85 → **4.6-11.6**. | **community report**: 4.36 on a 48 GB M3 Max, with only 4 of 10 experts used per token. That model change was not evaluated [S135]. | At 4 bits "full tool calling" works. The 2-bit build breaks JSON output [S50]. |
| V1 | **DeepSeek V4.1 Flash** (552B / 16B active per Artificial Analysis; MIT; index 39 [S116]), ds4 Q2 | 365.71 GB (340.6 GiB): 152 GiB of main weights + 189 GiB of Engram tables read from disk as needed [S110, S134] | **No** in memory. ds4 says to stream it on one 128 GB Mac [S110]. Needs 366 GB of disk plus headroom. | Not estimated: the Engram reads are not modelled. | None published [S109]. | None. |

Other models in the sweeps that do not fit 128 GB in memory at any published size:
- MiniMax-M3: smallest file 129.3 GB.
- Qwen3-Coder-480B: UD-IQ1_M 149.7 GB.
- Mistral Large 3 (675B / 41B active, Apache-2.0): UD-TQ1_0 168.6 GB. An official NVFP4 build exists for H100 nodes [S11].
- DeepSeek-V4-Pro: 865 GB native [S24, S9]. ds4 calls its 464.6 GB PRO Q2 file "usable for inspection, but slow" when streamed on a 128 GB Mac [S109, S128].
- GLM 5.3: Unsloth's smallest file is UD-IQ1_S, 216.7 GB [S24]. ds4's IQ2_XXS file streams (row S1).

Qwen3.5-397B UD-IQ1_M (106.8 GB) is Tight to No [S24].

### Where sources disagree, or a source contradicts itself

1. **M5 Max SSD speed.**
   - Apple: up to 14.5 GB/s, on an 8 TB unit [S126].
   - Reviewers: 12.6-13.6 GB/s, on 4 TB units [S3, S4].
   - No 2 TB unit has been tested, and Kevin's drive is unmeasured.
2. **M5 Max memory bandwidth.** Apple says 614 GB/s; some comparison sites list 540-546 GB/s [S2].
3. **Metal memory ceiling.** Community guides, and the mlx Kimi K3 card, repeat "about 75%" of RAM [S113]. This Mac measures 107.52 GiB, about 84% [S1].
4. **DeepSeek V4 Flash expert-cache hit rate with a cache of about 21 GiB.**
   - SSD-LLaMA reports 80.1% [S36].
   - LMSYS reports 54.2% (Alpaca) and 46.4% (MMLU) [S87].
   - LMSYS counts unique (layer, expert) keys per update, not per-token accesses, so the two metrics differ.
5. **flash-moe's SSD figure.**
   - It reports 17.5 GB/s sequential on an M3 Max [S135].
   - Reviewer data imply about 7.3 GB/s for an M4 Max [S4].
   - Its own decode reads run at about 3.4 GB/s (A5).
6. **Bytes per token for 1T Kimi.**
   - SSD-LLaMA reports 19.7 GiB activated per token for Kimi-K2.7-Code Q4_0 [S36].
   - Round 1 estimated 16.6 GiB, assuming a uniform 4.5 bits.
   - Spine precision explains the gap. With Q4_0 experts (11.9 GB per token), 19.7 GiB (21.2 GB) implies a spine of about 9.3 GB, or about 7 bits. The K2.6 Q2 file's spine measures 6.5 bits, and the file reads 15.42 GB per token.
7. **Kimi K2 at about 2-3 bits.**
   - Unsloth: K2.6 at 2.65 bits, **+31%** perplexity [S15].
   - ubergarm: K2-Instruct at 2.92 bits, **+7.8%** [S18].
   - They differ in model version, bit width and evaluation corpus (neither page names its corpus). K2.6 starts from INT4-trained weights, which leaves less headroom; K2-Instruct started from FP8 [S9].
   - The difference is unresolved.
8. **DeepSeek at about 2 bits.**
   - China Unicom: R1 UD-Q2_K_XL **−0.94%**, averaged over 9 reasoning and knowledge benchmarks [S20].
   - Unsloth: V3.1 Q2_K_XL **−5.8 Aider points** on coding [S19].
   - Different models and tasks. Both agree that uniform 2-bit is much worse.
9. **MLX vs llama.cpp on Macs.**
   - On an M5 Max running Qwen3.6-35B-A3B, llama.cpp is about 9% faster without MTP (93 vs 85) and 24% faster with MTP (105 vs 85). On the dense 27B it is 6% faster at 128 tokens and equal at 8K [S96].
   - On an M3 Ultra running Qwen3-235B, MLX gave 24 vs 16 tokens/s [S102].
   - A vendor blog says MLX is about 50% faster for K2.6 [S101].
   - No controlled comparison exists at 200B+ on the M5 Max.
10. **Prefill under SSD streaming.**
    - Earlier measured rates were 0.25-4.1 tokens/s [S36, S86, S87].
    - ds4 measured 104-300 tokens/s on an M5 Max [S109].
    - The difference is batching. ds4 prefills in large chunks: 4,096 tokens by default for DeepSeek, while GLM picks its own chunks [S95]. For V4.1 Flash only, ds4's docs add that large SSD prefills go through each layer in wide batches and that Metal overlaps compute with the next layer's reads [S110]; the docs do not say this for the files ds4 measured. Each chunk then costs about one pass over the uncached expert pool, plus compute (section 3b).
11. **Internal inconsistencies within single sources.**
    - The Aider page says "671GB → 192GB" for 1-bit, but its table lists 170 GB and 206 GB [S19].
    - Cacheable-by-Design says its measured 0.44 tokens/s warm decode agrees exactly with bytes ÷ bandwidth. But 12 GB per token × 0.44 = 5.3 GB/s, while it states the SSD as about 2.4 GB/s; and cold decode measured 0.128 against a modelled 0.20 [S86].
    - Kimi K3 size: 1,508.7 GB (Unsloth Q4_K_XL), 1,561 GB (Hugging Face storage) and "about 1.4 TB" (SSD-LLaMA).
    - Kimi K3 active parameters: 104B on the card, against about 50B in a DeepLearning.AI write-up.
    - Kimi K3 licence: reports conflict [S107].
12. **Parameter counts.**
    - Qwen3.8-Flash-Next: 125B in S106, against 180B total / 6B active on Artificial Analysis [S116].
    - DeepSeek V4 Flash: 284B / 13B on the April card [S12] and on Artificial Analysis, and 284.3B / 13.27B by tensor count of the 0731 GGUF [S128], against "165B / 11.5B" in the table of 2609.25809 [S119]. The 0731 card states no parameter count [S115].
    - GLM-5.3-Flash: 320B / 18B on Artificial Analysis, against 313.3B / 16.7B counted from the GGUF without the MTP block.

---

## 3. The routes

### (a) Very low-bit quantization

**Best evidence: quality vs bits for 600B-1T MoEs.** The curve is consistent across sources:

| Bits per weight | Typical cost | Evidence |
|---|---|---|
| About 4 | Near-lossless | K2 IQ4_KS +0.26% perplexity [S18]; R1 INT4 keeps 99.82% [S26]; R1 Q4_K_M −0.68% [S20] |
| About 3 | 0.3-3% | R1 DQ3_K_M −0.34%, Q3_K_M −1.80% [S20]; V3.1 Aider −3.2 points without thinking, −0.5 with thinking [S19]; K2 IQ3_KS +2.4% perplexity [S18] |
| About 2 | Depends on how the bits are allocated and on calibration | Dynamic R1 −0.94% vs uniform Q2_K_L −8.9% to −14.7% [S20]; V3.1 Q2_K_XL −5.8 Aider points [S19]; K2 +7.8% perplexity at 2.9 bits and +24.8% at 2.4 bits [S18]; K2.6 +31% at 2.65 bits [S15]; GSQ at 2.13 bits on K2.5/K2.6: GPQA-D −4.05 (K2.6, broad calibration) to −12.72 (K2.5, maths-and-code calibration), AIME25 −2.2 to −2.3, MATH500 +0.6 to +1.0 [S111] |
| Under 2 | Large losses | K2 +35-43% perplexity [S18]; K3 1-bit keeps 78.9% top-1 agreement [S14]; V3.1 1-bit −16 to −21 Aider points [S19]; uniform IQ1_S V3 non-functional [S22] |

**Best evidence: bigger model at fewer bits vs smaller model at more bits.**

For the bigger model:
- Dettmers (2022; round-to-nearest quantization; models up to 176B): 4 bits is almost always optimal for a fixed total number of model bits [S28].
- QTIP: 2-bit Llama-2-70B (perplexity 3.87-3.90) beats FP16 Llama-2-13B (4.57) [S27].
- COLM 2025: larger quantized models beat smaller BF16 models at 4 bits; 3 bits is risky on hard tasks [S29].
- A compressed R1 at 210 GB matched or beat Qwen3-235B 8-bit (233 GB):
  - AIME24: 86.67 vs 86.67;
  - GPQA-Diamond: 74.24 vs 68.18;
  - GSM8K: 96.51 vs 84.99.

  Only three benchmarks, with no variance reported [S22].

Against, at about 1 bit:
- DeepSeek-V3.1 at 1 bit (206 GB) scored 55.7 on Aider, below unquantized Qwen3-235B at 59.6 [S19].
- Qwen3-235B's 3-bit file is 104 GB, but its 3-bit score is not in the sweeps.

Open: full GLM 5.3 (index 45) streams on this Mac at IQ2_XXS (row S1), but its cost at that size is unmeasured.

**Natively low-bit models leave nothing easy to cut.** Kimi K2-Thinking and later (INT4), Kimi K3 (MXFP4), DeepSeek V4 (FP4 experts) and gpt-oss (MXFP4) ship already quantized, so their "Q4" GGUF is the full model:
- the K2.6 Q8_K_XL repack is lossless at 594.5 GB [S15];
- every gpt-oss-120b GGUF is about 63 GB [S10];
- for V4 Flash 0731, the MXFP4 GGUF repacks still show a KLD of about 0.155 against the BF16 expansion when run in llama.cpp on an RTX 5090 [S117]. The kernel path matters: the BF16 reference's perplexity differs by 4-5% between RTX 5090 and H100, with the same file, corpus and commit [S117].

A scaling-law paper predicts that heavily trained models suffer more from low-bit quantization [S31]. This has not been tested on these MoEs.

**Model and serving matter too.**
- MiniMax-M2.5 lost 6 points even at its best 4-bit quant. MiniMax-M3, which has a shared expert, held up better [S30].
- Low-bit reasoning models write longer chains of thought [S33]. A Q2 dense 27B wrote about 25% more output tokens on Terminal-Bench [S104].
- Kimi's tool-call schema accuracy ranges across serving providers: 83-100% for K2-Thinking and 72-100% for K2-0905. The verifier names wrong versions, malformed tool-call IDs and the lack of schema enforcement as causes; it does not rule out quantization [S35].
- GSQ beat Unsloth's files at about equal size [S111]:
  - Kimi K2.5 AgentBench: GSQ at 2.37 bits against UD-IQ1_M (an i-quant mix at 2.4 bits), KG 45 vs 39;
  - Qwen3-4B Q2_K, refined in place in GGUF: 48.34 vs 35.01 average.

  A stock k-quant or i-quant result is therefore a lower bound on what 2 bits can reach.

**Limits**
- Most curves come from the quant makers (Unsloth, ubergarm, AtomicChat).
- Most perplexity tables do not name the evaluation corpus.
- Task benchmarks below 4 bits exist for one 1T format only: GSQ at 2.13 bits on K2.5 and K2.6 [S111]. The published checkpoints are CUDA-only (Humming format) [S112]. None exist for the GGUF or MLX files a Mac would run.
- The quants that fit 128 GB have only fidelity metrics.
- The best 2-bit methods (QTIP, AQLM, EXL3, ik_llama.cpp trellis quants, GSQ's Humming checkpoints) are CUDA-first, not Metal-first [S27, S112].
- The exception is GSQ's GGUF K-quant route. It starts from an existing K-quant GGUF, improves the discrete assignments and writes the same format, which "runs unchanged on llama.cpp / Ollama" [S111, S138]. The output uses standard K-quant types, so it is Metal-compatible. It is tested only on dense Qwen3-8B and Qwen3-4B (Q2_K and Q3_K_M), not on an MoE or on Kimi.

**Practical recipe today, on the Mac**
1. Choose a model whose mixed-precision quant fits (table rows O1, F1, F2, F3, Q1, Q2). Prefer recipes that push only the routed experts to low bits:
   - ds4 Q2 keeps attention, the shared expert and the output head at Q8;
   - Unsloth's "UD" quants protect sensitive tensors.
2. Avoid uniform Q2_K and IQ1_S.
3. Use upstream llama.cpp, MLX, or ds4 for DeepSeek V4 Flash and GLM-5.3-Flash.
   - With llama.cpp, check the log for `has tensor = true`. With the Metal tensor API off, gpt-oss prefill falls from 1,833 to 877 tokens/s; the S97 poster says LM Studio's runtime behaves like the "off" case [S97].
4. Before trusting a quant, compare it with a reference on your own prompts. Do this on the host (llama.cpp CUDA), not the Mac. MLX DWQ cards publish no metrics [S25].

### (b) SSD or unified-memory expert streaming with caching

**Best evidence**

- **Measured on this Mac model.** The ds4 maintainer streamed three models on a 128 GB M5 Max on 2026-09-06 [S109]:

  | Model (file) | Expert cache | Prefill (tokens/s) | Generation (tokens/s) | Runs |
  |---|---|---|---|---|
  | GLM-5.3-Flash Q4_K (191 GB) | automatic | 121 (2K prompt), 104 (1K append) | 11.9, 14.9 | three-run median |
  | V4 Flash Vision-Exp MXFP4 (156 GB) | 86.2 GiB | 300 (8K prompt), 263 (4K append) | 11.9, 19.3 | single run |
  | GLM 5.3 IQ2_XXS (211 GB), 8K context | 61.35 GiB | 16-token append: 30.8 s → 2.9 s | 4.09 → 5.11 | three-run medians |

  - Generation includes the first-token wait.
  - The GLM 5.3 row compares runs before and after ds4 began caching short tool-result prompts.
  - ds4 also reports DeepSeek V4 PRO Q2 streaming on a 128 GB Mac as "usable for inspection, but slow".
  - Its guidance [S109]:
    - "Generation is usually more sensitive to cache misses than prefill";
    - an oversized expert cache can push the non-routed weights out of memory and slow decoding;
    - leave memory for the OS and other applications.
- **The bandwidth model** (A6) agrees with the ds4 GLM 5.3 measurement for h = 0.68-0.90. It agrees with the V4 Flash measurement only if h ≥ 0.93, or if reads overlap compute. It is 25-32% optimistic against flash-moe, and the gap sits in the memory and compute term (2.2-2.9 times A6's; section 2, A6).
  - Cacheable-by-Design says its warm decode agrees exactly with bytes ÷ bandwidth, but its own numbers are inconsistent (section 2, item 11), so it is weak support [S86].
  - That paper's pre-registration covers a router-training experiment, not the bandwidth measurement [S86].
- **SSD-LLaMA** [S36], built on llama.cpp, Linux and CUDA:
  - packs each expert into one aligned block read with O_DIRECT through io_uring;
  - compresses experts losslessly;
  - caches by frequency and recency in VRAM and RAM.

  Results:
  - 1T Kimi-K2.7-Code at Q4_0: 0.89 tokens/s with 16 GB of RAM and 1.03 with 32 GB, on an RTX 5090 with a 9 GiB/s NVMe;
  - up to 77.7% of the SSD's sequential read bandwidth, against 43.2% for the best baseline (unnamed);
  - read bandwidth up to 2.82 times llama.cpp's and 1.93 times KTransformers' (ratios of read bandwidth, not of speed);
  - decode 1.35-3.44 times faster than llama.cpp and 1.57-15.61 times faster than KTransformers;
  - Colibri reached slightly higher read bandwidth on some models;
  - the expert-pack layout alone gave 4.1 times;
  - prefetching hid only about 5% of transfer latency.
- **flash-moe on a Mac** [S135] streams experts with pread and the OS page cache:
  - Qwen3.5-397B (about 224 GB) ran at 4.36 tokens/s on a 48 GB M3 Max, but with only 4 of 10 experts used per token;
  - the page cache (about 35 GB) hit about 71%;
  - mmap was 5 times slower than pread;
  - prefetching gained nothing, because SSD DMA slowed the GPU by 73% (both share the memory controller);
  - a temporal expert predictor hit only 25%.
- **Routing locality** [S82]:
  - 26-36% of a token's experts repeat from the previous token, and 80-85% within the previous 64 tokens (DeepSeek-V3, Kimi K3);
  - LRU hit rates at small caches are 44-48% for DeepSeek-V3 and Kimi K3;
  - Kimi K3 reaches 78% with 25% of its experts cached, and 64% with four streams sharing the cache;
  - the hot experts change between domains: Jaccard overlap 0.03-0.19 for DeepSeek-V3 and K3, and 0.07-0.45 for Qwen3-30B;
  - the OS page cache comes within 1.09-1.11 times of an oracle-pinned cache;
  - a replay on an M-series Mac found that macOS compresses memory before giving up file cache, and that Metal-wired pages cannot be evicted.
- **llama.cpp's GPU LRU expert cache** [S41]:
  - 72-89% hits and 1.57-2.20 times faster decode on RTX 4090 and 5090 (CUDA);
  - only for batches of 32 tokens or fewer, on a single device;
  - a later comment found it slower than no cache for GLM-5.3-Flash over PCIe 4;
  - not shown on Metal.
- **On macOS, a bigger cache can slow things down.** On a 24 GB M5 Pro, decode was fastest with 35% of experts cached for Gemma 4 26B Q8, and with 15% for Qwen Q8. Larger caches lost speed to memory pressure, even though the hit rate kept rising [S88].
- **Other streamers:**
  - Colibri: GLM-5.2 (744B) at 1.83 tokens/s on a 128 GB Ryzen AI Max+ 395 [S52];
  - ssd-moe: DeepSeek V4 Flash at 4.5-5 tokens/s on a 48 GB M5 Pro [S53];
  - mlx-turboquant-moe-streaming, an experimental MLX streamer that reads experts with parallel pread: Kimi-K2-Instruct 4-bit (578 GB) at 0.5 tokens/s on a 128 GB M3 Max, using 7.1 GB of RAM [S139].
- **Speculative decoding under offload** has to load the union of the experts that all draft tokens need:
  - EAGLE-3 without an expert cache ran at 0.90 times plain decoding (Qwen3-30B-A3B) [S91];
  - MTP on a Mac ran at 0.87 times, and expert bytes rose from 48 to 117 GiB [S88];
  - offload-aware drafters recover gains:
    - SpecFit: 1.77-2.29 times faster than plain decoding, on Qwen3-30B-A3B [S91];
    - AcceptMoE: 2.06 times faster than standard speculative decoding (EAGLE-3), on one RTX 5090 [S92].

  Kimi K2 ships no MTP head. Third-party EAGLE-3 drafts exist for K2.5 to K2.7 [S5, S92].
- **Energy:** a simulation estimates that SSD offload costs up to about 12 times the energy per token of HBM [S58].

**Prefill arithmetic** (estimate, corrected)

- **Experts touched per micro-batch.** With uniform routing (conservative; real routing is skewed), a micro-batch of n tokens touches 1 − (1 − 8/384)^n of each layer's experts:
  - 49% at n = 32;
  - 93% at n = 128;
  - about 100% at n = 512 or more.

  So each micro-batch reads about the whole expert pool. A partial last batch counts as a full pass: 1,328 tokens still touch about all experts. A 30K prompt is therefore 8 passes at 4,096 tokens and 59 at 512.
- **The cache helps only if the engine manages it.** A micro-batch scans layers 1-60 in a fixed cycle. An LRU-like page cache smaller than the pool gets almost no hits on such a scan. A pinned or engine-managed cache can save its share of the pool on every pass after the first: about 72 of 331 GB (22%) for the Kimi Q2 file at 30K context (A7). ds4's docs say short appends keep using the expert cache [S110], and its warm appends run faster than any no-hit pass (check below).
- **One pass over the Kimi K2.6 Q2 pool (331.1 GB):**
  - 31 s at 10.6 GB/s;
  - 57 s at 5.85 GB/s;
  - 166 s with mmap at 2 GB/s.
- **Compute.** For a 30K-token prompt I use 100-185 tokens/s (the arithmetic verifier's estimate):
  - gpt-oss-120b's measured 1,833 tokens/s at 2K, scaled from 5.1B to 31.7B active parameters, gives 295 tokens/s;
  - Kimi's MLA attention at a mean context of 15K adds 0.6-2 times the weight FLOPs, which lowers this to 100-185 tokens/s.
- **Prefill rate for a 30K prompt** = tokens ÷ (read time + tokens ÷ compute rate) with no overlap of reads and compute, or tokens ÷ max(read time, tokens ÷ compute rate) with full overlap. Read time = passes × pass time, less the cached share on every pass after the first when the cache is managed:

  | Batching | Prefill (tokens/s) | Time for 30K tokens |
  |---|---|---|
  | Whole prompt through each layer in one batch: a bound, not a documented ds4 mode for these files (no overlap to full overlap) | 84-185 | 2.7-5.9 min |
  | 4,096-token micro-batches (ds4's default chunk for DeepSeek [S95]), no cache hits | 40-73 | 6.9-12.5 min |
  | 4,096-token micro-batches, managed 72 GB cache hit after the first pass | 45-82 | 6.1-11.1 min |
  | 512-token micro-batches, no cache hits (managed cache: 10-19) | 8.2-15 | 33-61 min |
  | mmap at 2 GB/s, 4,096-token micro-batches | about 18-20 | about 25-27 min |

  With 4,096-token micro-batches on short prompts (compute 295 tokens/s), the upper end rises to 91 tokens/s (one pass for a 4,096-token prompt).
- **Check against ds4's measurements** [S109]:
  - **GLM-5.3-Flash Q4_K** (171.2 GB pool): one no-hit pass takes 16.2-29.3 s. The measured 2K prompt took 16.9 s, and the 1K append 9.8 s. Compute for 2K tokens is about 2.6-3.3 s: ds4's in-memory V4 Flash prefill rate, unscaled and scaled up for 16.7B active parameters. So even the 2K prompt beats one no-hit pass plus compute, unless its compute took under 0.8 s.
  - **V4 Flash Vision-Exp MXFP4** (147.2 GB pool, 92.6 GB cache): a full pass takes 13.9-25.2 s, and the uncached part alone 5.2-9.3 s. Compute for 8K tokens is about 10.4-14.7 s, scaled from ds4's in-memory prefill. The measured 8K prompt took 27.3 s, which fits one full pass plus compute. The 4K append took 15.6 s, below the 19.1 s minimum for a no-hit pass plus compute; it fits only with hits on the cached part.
  - So only the V4 Flash 8K cold prompt fits "one no-hit pass plus compute". The appends and the GLM-5.3-Flash prompt run faster: ds4's cache serves prefill hits, or its reads overlap compute, or it reads faster than 10.6 GB/s.
  - The earlier SSD-bound rates of 0.25-4.1 tokens/s [S36, S86, S87] fit small micro-batches.

**Limits**
- Decode time is set by bytes per token, the cache hit rate and SSD bandwidth.
- Kimi K2's hit rate is not measured.
- Stock tools waste bandwidth:
  - GGUF interleaving touches 6,912 pages per expert, against 192 after re-layout [S103];
  - on Linux, SSD-LLaMA reads up to 2.82 times faster than stock llama.cpp and decodes 1.35-3.44 times faster [S36]; on macOS, mmap is 5 times slower than pread [S135].
- On unified memory, SSD reads and GPU compute contend for the same memory controller.
- Disk space limits which Kimi file can be stored at all.

**Practical recipe today**
1. **Stock route:** llama.cpp mmap of a file larger than memory. It works, but expect about 1 token/s or less for Kimi, and about 20 tokens/s of prefill even with large micro-batches [S17, S103].
2. **Measured ds4 targets** (Mac, Metal). These are the files to try first, in order of size [S109, S110]:
   - DeepSeek V4 Flash Vision-Exp MXFP4, 156 GB: ds4 target `ds4f-vision-mxfp4`, the file ds4 measured. `ds4f-mxfp4` is the 0731 MXFP4 file of the same size, which has no published streaming measurement;
   - GLM-5.3-Flash Q4_K, 191 GB;
   - full GLM 5.3 IQ2_XXS, 211 GB.

   Start with ds4's automatic cache budget, and stop other memory-heavy work first.
3. **V4.1 Flash Q2** needs 366 GB of disk and has no published Mac speed [S109, S110].
4. **Other streamers:** flash-moe (Qwen3.5-397B, Mac); ssd-moe (V4 Flash, MLX); SSD-LLaMA and SGLang SSD Expert Pack (Linux and CUDA) [S36, S87]. None of these supports Kimi K2 on Metal. The only documented Kimi K2 streamer on a Mac is the experimental MLX one above, at 0.5 tokens/s [S139]; the 1.7 tokens/s K2.5 report names no engine [S51].
5. **For Kevin:** Kimi streaming is a research question (gap G2), worked on the host.

### (c) Expert pruning or merging

**Best evidence**

- **REAP** (router-weighted pruning) [S59] is the only peer-reviewed expert-pruning method tested on 1T Kimi. On K2-Instruct at INT4, calibrated on code and tool data, removing 50% of experts gave:
  - coding average 0.631 → 0.624;
  - SWE-Bench Verified 0.554 → 0.576;
  - BFCL multi-turn tool use 0.355 → 0.164;
  - knowledge multiple-choice average 0.780 → 0.643.
- **Calibration data must match the use.** Calibrating on general text (C4) made code generation collapse [S59, S67].
- **MoESQ** [S63], independent of REAP's authors, measured Kimi-K2.5 with REAP 50% plus INT4 (2.25 bits per original expert weight, 288 GB):
  - 97.99% on the OpenLLM v1 average, against 94.22% for dense 2.13-bit GSQ at about the same size.
  - MoESQ's first author uploaded the checkpoint. Its GPQA-Diamond (88.0%), AIME25 and MATH500 recoveries appear only on the model card [S64].
- **GSQ** [S111]: dense 2.13-bit Kimi K2.5 and K2.6, 294 GB, with task results (table row K2b). The checkpoints are public and run on Hopper or Ampere [S112]. GSQ's GGUF K-quant route (section 3a) has not been applied to Kimi.
- **Pruning vs very low bits.**
  - One preliminary test on Qwen3-30B, at 12.5% of BF16 size: 4-bit weights + 50% pruning scored 77.6 on EvalPlus, against 28.6 for uniform AWQ 2-bit.
  - Dynamic and trellis 2-bit were not tested.
  - The paper also states that weight quantization is more accurate than pruning down to 4 bits [S59].
- **DeepSeek-V3 pruned plus mixed precision**: the published file is 113.4 GB (105.6 GiB) [S130]; table row D4 [S22].
- **MoE-XBench** [S67], independent, stacked pruning with GGUF and KV-cache quantization:
  - pruning is the main source of quality loss;
  - losses do not add up simply;
  - 1-bit plus pruning breaks down.
- **Merging** (HC-SMoE, M-SMoE) fails on generative tasks at 50% [S59]. Router-aware merging (REAM) is close to REAP at 25% [S68].
- **Low-rank / shared-basis compression (MoBE)** kept 98% on Kimi-K2 but removed only 24% of parameters. It is BF16-only and has no released checkpoint [S66].
- **Newer pruning criteria** (HOPE, task-agnostic criteria, coverage-based selection) beat REAP, but are tested only up to 122B [S69, S70].
- **Recovery and specialization.**
  - A short fine-tune recovers 37.3% of the lost quality [S71].
  - 70-90% pruning works only for single-task specialists such as translation [S72].
- **Kimi K3, pruned by the community and by Nota** [S113]:

  | Build | Kept experts | Size | Reported result |
  |---|---|---|---|
  | REAP 50% / Nota global 50% (maker evaluation) | about 448 per layer (Nota: 350-717, varying by layer) | — | Base / REAP / Nota: IFEval 93.72 / 87.80 / 90.02; GPQA-D 86.36 / 66.67 / 69.19; HumanEval+ 82.32 / 82.32 / 81.71 |
  | prometheusAIR REAP55, IQ1_M GGUF | 400 of 896 | 342.5 GB | No standard benchmarks. Needle test 15/15 exact through 64K; 0.48 tokens/s warm, streamed from NVMe on a PC (maker) |
  | mgoin pruned75 (no calibration; experts ranked by router weights) | 224 of 896 | 475 GB | GSM8K 34.42%, against 68.23% for the 50% sibling and 95.53% for the source K3; same harness, hardware and seed, 5-shot, 256-token limit |
  | pipenetwork REAP80, MLX | 179 of 896 | 349.7 GB | Experts kept at native MXFP4, bit-exact. 5.54 tokens/s on a 512 GiB M3 Ultra. One greedy prompt each: code structurally correct; "The capital of France is" → "Paris.", then drift into a list; Chinese loops. Calibration 40% code, 30% English web, 15% Chinese, 15% other languages |
  | mlx-community reap160, MLX 2-bit | 160 of 896 | 181.2 GB | Experts at 2-bit affine. One 40-token greedy prompt each: code correct; "The capital of France is" loops; Chinese degrades. Perplexity and benchmarks "not done". REAP keeps 51.7% of router demand at 160 experts; about 376 experts (77.5%) would be needed. Lowering top-k from 16 to 6 did not help. |

- **Kimi K2.5 REAP 50% (Ex0bit)**, 309.7 GB [S114]:
  - built on an abliterated K2.5 variant ("PRISM");
  - calibrated on 512 samples of tulu-3 using 8×H200;
  - it ships saliency scores and a Kimi observer script.
- **Instability.** A community 50% prune of K2.6 in NVFP4 shows repetition loops and thinking blocks that never close [S65, community report].

**Limits**
- Pruning makes domain specialists, not smaller generalists. The Kimi K3 numbers point this way: at 50%, knowledge (GPQA-D, GSM8K) falls while HumanEval+ holds. Beyond 50%, the evidence is single prompts and one calibration-free GSM8K run.
- No Kimi K2.x result goes past 50% pruning, and none combines 50% pruning with 2 bits or fewer.
- No general-purpose pruned Kimi K2.x exists in GGUF or MLX. A Hugging Face search on 2026-10-15 found [S137]:
  - one MLX build: a Solidity-coding specialist with 256 of 384 experts kept (33% pruned), Q4, about 401 GB, needing about 440 GB of memory; about 10-13 tokens/s decode and 300 prefill on an M3 Ultra 512 GB, on a small workload snapshot;
  - GGUFs of a 2-layer truncation of K2.5 (mradermacher, from ubicloud's BF16-Pruned-20B, which keeps the first 2 of 61 layers), "intended for pipeline testing and performance research". ubicloud's 20-layer truncation (Pruned-340B) is safetensors only.
- Kimi K3 builds pruned 50-82% exist in MLX, GGUF and safetensors. Benchmarks are few and come from the makers: Nota's table at 50%, mgoin's GSM8K at 50% and 75%, and prometheusAIR's needle test. The rest are single greedy prompts [S113].
- The other pruned K2.x checkpoints need a private vLLM fork (kwanhee) [S132], are unstable (0xSero) [S65], or derive from an abliterated variant (Ex0bit) [S114].

**Practical recipe today**
- **On the H100 host:** Cerebras's REAP repository [S61] includes:
  - a layer-wise calibration observer that runs on a single GPU;
  - its published calibration mix (24,576 samples × 16,384 tokens of code, math, science, tool calls and SWE).

  The host's 1.77 TB of RAM can hold the INT4 model while layers stream to one GPU (untested). For general use, add a general-domain mix and test outside the calibration domain.
- **Ready-made pruned files:**
  - Cerebras REAP checkpoints for Qwen3-Coder-480B, GLM-4.6/4.7 (BF16 and FP8), MiniMax-M2.x and DeepSeek-V3.2 (345B, 508B). None for Kimi K2; Cerebras's only Kimi prune is Kimi-Linear-REAP-35B-A3B [S61].
  - Unsloth's Qwen3-Coder-REAP-363B GGUF, 101-116 GB at 1 bit, with its evaluation section marked "TBD" [S81].
  - The pruned DeepSeek-V3-0324 GGUF from 2509.25689 (moxin V3-Mini-Exp, 113.4 GB) [S130].

### (d) Distillation or smaller siblings

**Best evidence**

- **DeepSeek's R1 distills**, trained by supervised fine-tuning on 800K R1 samples, keep most of R1's reasoning [S77]:

  | Model | AIME24 | GPQA-Diamond | LiveCodeBench |
  |---|---|---|---|
  | R1 | 79.8 | 71.5 | 65.9 |
  | R1-Distill-Llama-70B | 70.0 | 65.2 | 57.5 |

  They were tested only on reasoning benchmarks.
- **Converting an MoE into a dense model** and then distilling beats dense-to-dense pruning by 6.3 points. Tested only at 30B or below [S79].
- **There is no official small Kimi.**
  - Kimi-Linear-48B-A3B was trained separately (MMLU-Pro 51.0).
  - Kimi-Dev-72B is a Qwen2.5-72B fine-tune (SWE-bench Verified 60.4%) [S78].
- **Vendor-trained smaller siblings are the practical form of this route.** Artificial Analysis index v4.3.2, full precision [S105, S116]:

  | Model | Total / active | Index | Runs on this Mac as |
  |---|---|---|---|
  | GLM 5.3 | 753B / 40B | 45 | ds4 IQ2_XXS, streamed (row S1) |
  | GLM-5.3-Flash | 320B / 18B | 42 | ds4 Q2 in memory (F3), or Q4_K streamed (S3) |
  | Qwen3.8-Flash-Next | 180B / 6B | 40 | ds4 Q2 in memory (F4) |
  | DeepSeek V4.1 Flash | 552B / 16B | 39 | ds4 Q2, streamed only (V1) |
  | DeepSeek V4 Flash 0731 | 284B / 13B | 34 | ds4 Q2 in memory (F1) |
  | Kimi K2.6 | 1T / 32B | 27 | streamed only, no Mac engine (K2) |
  | gpt-oss-120b | 117B / 5.1B | 12 | in memory (O1) |

**Limits**
- Distills copy narrow skills, not the large model's knowledge.
- Making one from a 1T teacher costs billions of generated tokens.
- The index is measured at full precision. The Mac runs these models at about 2-4 bits, and their cost at those sizes is unmeasured.

**Practical recipe today:** use a vendor sibling that fits.
- DeepSeek V4 Flash 0731 on ds4 is the strongest option with a measured Mac speed (row F1).
- GLM-5.3-Flash Q2 scores higher at full precision, but its Mac speed is only an estimate and its Q2 cost is unknown (row F3).

### (e) Combinations

| Combination | Evidence or estimate |
|---|---|
| Pruning + quantization | MoESQ (288 GB Kimi) [S63]; GSQ dense 2.13-bit (294 GB) [S111]; the pruned DeepSeek-V3 (113 GB) [S22, S130]; REAP's appendix [S59]. The best-supported combinations. |
| Pruning + streaming | **estimate**: Kimi K2.6 with 50% of experts pruned at the Q2 file's bits is about 175 GB on disk. The hit rate must come from the original model's routing (A7): with a 75 GB cache (A7 rule), h 0.75-0.85 → **2.9-7.2 tokens/s**; at h 0.70-0.80 it is 2.5-5.8, the same as the unpruned file. Pruning mainly saves disk, not decode time. Quality not measured (gap G1). |
| Fewer active experts (top-k) + streaming | **estimate** for the K2.6 Q2 file, with the hit rate held at 0.75: top-6 is **28-30%** faster and top-4 **76-87%** faster than top-8, across the A2/A5 parameter range (e × 614 = 288-377 GB/s, B = 5.85-10.6 GB/s). Quality evidence: keeping about 2/3 of the chosen experts preserves 98.8% of unpruned performance, averaged over the nine models of the study's budget sweeps (it covers 12 checkpoints in all; V4 Flash 0731, k 6 → 4: 75.69 → 74.53) [S119]; normalizing the weights by the trained top-k's mass instead of the reduced set's cuts Qwen3.5-397B's MMLU loss (10 → 5 experts) from 2.10 to 0.55 points [S120]. Not measured on Kimi K2 (gap G5). |
| Quantization + speculative decoding | ds4 with the DSpark draft for DeepSeek V4 Flash: 1.5-1.9 times (measured on a B200: 120 vs 60 tokens/s); needs about 10 GB more memory [S23]. Under expert offload on a Mac, MTP ran at 0.87 times [S88]. |
| Several Macs | Two M5 Max laptops over Thunderbolt 5 ran DeepSeek V4 Flash Q4 with ds4 [S100]. Prefill was 1.38, 1.66 and 1.85 times faster at 9,421, 28,684 and 63,819 tokens. The page's link-quality line reads "Thunderbolt 5 25.1 t/s · WiFi 10.7 t/s · Internet / VPN 3.6 t/s", and generation "pays roughly a 19% penalty over a single machine". exo with RDMA claims 1.8 times on 2 devices and needs macOS 26.2+, Thunderbolt 5 cables between every pair of machines, and identical OS builds [S99]. Four M3 Ultras (1.5 TB in total) ran K2 Thinking at about 30 tokens/s [S49]. |
| CPU-GPU hybrid server (not Kevin's Mac) | KTransformers runs K2 Q4_K_M at about 10-14 tokens/s with about 600 GB of DRAM [S37]. An OSDI'26 engine runs K2 FP8 at 22.4 tokens/s on 1.15 TB of DDR5 plus 2× RTX 5090 [S38]. The H100 host (1.77 TB of RAM) is this kind of machine (section 5). |

---

## 4. Research gaps

These are gaps where a small, rigorous program could produce a new measured result. Each gap is labelled with the novelty verifier's status, re-checked here:
- **OPEN:** nobody has published the result;
- **PARTLY_DONE:** published work answers part of it, and the gap is narrowed to the rest.

All five gaps need more than 8 GPU-hours, so the project's research-gauntlet rule applies.

**Where the work runs.**
- **Everything runs on the 8×H100 host.** The Mac is only the target spec.
- **Mac numbers come from host-side emulation:**
  - replay measured routing traces through cache simulators on the host CPUs;
  - feed the misses into the A6 model, using Apple's and the reviewers' SSD and memory numbers (A1, A5) and the measured decode efficiency (A2);
  - validate the emulator against ds4's published M5 Max streaming measurements [S109] before trusting its Kimi prediction.
- **GPU 0 is held by another project's job until 2026-10-21.**
  - This blocks Kimi K2.6 INT4 at TP8 (8-way tensor parallelism). The 595 GB checkpoint needs all 8 GPUs: 69.3 GiB of each GPU's 79.6 GiB.
  - It also cannot run on 7 GPUs: 7 × 79.6 = 557 GiB leaves under 3 GiB in total, and 7 does not divide the 64 attention heads.
  - Until then the host can run:
    - GGUF files on up to 7 GPUs;
    - inference on the published GSQ 2-bit checkpoint at TP4 (if humming-kernels is accepted as stock; section 5);
    - CPU-side work with experts in the host's 1.77 TB of RAM;
    - all cache simulation.
  - Running GSQ quantization on Kimi also waits: its repository lists a full 8-GPU H100/H200 node as the minimum [S138].
  - K2.6 INT4 is already on the host: job 1528 fetched 595.2 GB, and its receipt matches the Hub listing file for file [S140].

**Shared assumptions behind the GPU-hour figures.** A one-hour pilot per runtime should replace them.

- **Evaluation suite: about 800 items.**
  - Items: GPQA-Diamond 198; MMLU-Pro subset 300; LiveCodeBench subset 200; a 100-item tool-call schema set.
  - Pin one reasoning mode per model and tier. For example, V4 Flash 0731 has low, high and max reasoning effort and recommends up to 384K output tokens at high and max [S115]; its index score of 34 is at max [S105].
  - **Tier A**, all items, no thinking: 800 × 2 seeds × 1,000-2,000 generated tokens (my assumption) = 1.6-3.2M tokens.
  - **Tier B**, a 200-item subset, one thinking mode: 200 × 2 seeds × 12,000-20,000 tokens = 4.8-8.0M tokens.
    - Basis: compressed Kimi K2.5 answers that finish have a median length of about 43,800 characters on GPQA-Diamond and 42,600 on AIME25, under a 65,536-token cap [S63]. At an assumed 4 characters per token, that is about 11K tokens.
    - Low-bit models write longer chains of thought [S33].
  - **Total: 6.4-11.2M generated tokens per model setting.**
  - Report truncation and non-termination separately. Measure tokens per item in the pilot.
- **Throughput, until the pilot measures it:**
  - **vLLM running Kimi K2.6 INT4 at TP8: 0.075-0.55M tokens per GPU-hour.**
    - Round 1 assumed 0.45-1.1M (1,000-2,500 tokens/s in aggregate).
    - The KV limit below makes that figure uncertain by 2-6 times, so I divide it by 2-6.
  - **Why the KV cache limits concurrency under TP8:**
    - MLA keeps one latent KV head, so vLLM and SGLang copy the whole cache to every GPU. vLLM's documentation says TP8 causes "8x KV cache duplication" for DeepSeek-R1 [S124, S125].
    - K2.6 INT4 uses 69.3 GiB of each GPU, leaving 10.3 GiB raw.
    - At vLLM's default `gpu_memory_utilization` of 0.90 only 2.3 GiB remain; at 0.95, 6.3 GiB. Activations come out of that too.
    - With 3-6 GiB per GPU for KV, the tokens in flight are 46-92K in BF16 (70,272 bytes per token) or 92-183K in FP8.
    - That is 4-8 (BF16) or 8-17 (FP8) concurrent 11K-token sequences, and 0-2 sequences of 64K.
  - **Mitigations:**
    - an FP8 KV cache;
    - vLLM's decode context parallelism (`-dcp`), which splits the KV cache across GPUs [S124].
    - SGLang's DP attention does not fit: each GPU would hold the full BF16 attention weights (12.3 GB, from A8) instead of 1/8 of them. That adds about 10.8 GB per GPU against about 11 GB free, which leaves no room for KV.
  - **llama.cpp CUDA serving a GGUF on 2 GPUs: 0.27-0.72M tokens per GPU-hour** (150-400 tokens/s per instance).
    - Two GPUs hold 171 GB, which limits this to files of about 150 GB or less.
    - Larger files need more GPUs, which lowers throughput per GPU-hour: the 161.9 GB V4 Flash reference needs 3 GPUs; the 340.5 GB K2.6 Q2 needs 5.
  - **Models with 13-18B active parameters** (V4 Flash, GLM-5.3-Flash): 0.5-3M tokens per GPU-hour.
  - **Prefill-only passes** (KLD measurement, routing traces): 0.9-4.5M tokens per GPU-hour.

### G2 (OPEN). Kimi K2 routing locality, cache hit rates, and whether they predict streaming speed on the Mac

- **Status: OPEN, confirmed.**
  - No Kimi K2 trace (384 experts, top-8) or hit-rate measurement exists.
  - Published traces cover DeepSeek-V3, Kimi K3, V4 Flash and Qwen [S82, S36, S87].
  - SSD-LLaMA streams K2.7-Code but reports hit rates only for V4 Flash [S36].
  - LMSYS's SSD Expert Pack tests V4 Flash and K3, and does not mention K2 [S87].
  - An alphaXiv keyword and semantic search on 2026-10-15 found nothing more.
- **Questions (falsifiable):**
  1. On teacher-forced traces of Kimi K2.6 INT4 (chat, coding, agentic tool use, long-document QA), replayed event by event, does an LRU cache holding 22% of the expert pool reach h ≥ 0.70 in every workload? 22% is the Mac's budget for the Q2 file with other work stopped (A7). Also report hit-rate curves from 5% to 50% cached, including 14% (the first reading of today's free memory).
  2. **Emulator validation.** Feed host traces of DeepSeek V4 Flash and GLM 5.3 through the same simulator and A6, using only Apple's numbers and the A2 calibration. Does the emulator reproduce ds4's published M5 Max generation and prefill numbers [S109] within ±20%?
     - If yes, its Kimi prediction becomes the dossier's Mac number.
     - If not, report the gap.
- **Why it matters:** every Kimi streaming number in this dossier rests on hit rates interpolated from other models (A7).
- **What to measure:**
  - **Per-layer expert IDs for every token**, with stock SGLang's expert-distribution recorder in `per_token` mode (`expert_distribution_recorder_mode`), which stores `topk_ids` per layer [S122]. No patch is needed. Run it:
    - with EPLB off, so physical expert IDs equal logical IDs;
    - with two-batch overlap off (the recorder asserts this);
    - with shared-expert fusion off (the code notes the data are wrong otherwise).

    Its buffer is sized for top-8, which matches K2. For GGUF files, use llama.cpp's evaluation callback (host code).
  - **Teacher-forced prefill** of the model's own transcripts. The routing of token t depends only on tokens up to t, so a prefill pass reproduces decode routing at a fraction of the cost. Check on a small decode sample how often routing differs; numerics can flip near-ties.
  - **Locality:** reuse after 1 and after 64 tokens, Zipf slope, cross-domain overlap.
  - **Cache policies:** LRU, LFU, LFRU and Belady (the offline optimum), following 2608.07911's protocol [S123]:
    - replay event by event ("event-atomic"). Sequential replay inflated the LRU miss fraction by 27.4% (19.30% → 24.59%; Qwen3-30B-A3B, 40% of experts resident, 8 concurrent requests), so it understates hit rates. S82 does not state its replay semantics; check this before treating A7's brackets as pessimistic or optimistic;
    - use diverse prompt templates: template contamination moved a measured effect by 19.4-31.9 points;
    - follow its reporting checklist.
  - **Batching:** one stream vs four sharing the cache [S82].
  - **Routing agreement** (top-8 overlap) between INT4 and K2.6 UD-Q2_K_XL, since the Q2 file is what a Mac would stream.
  - **Prefill:** passes over the pool per prompt, for micro-batches of 32-4,096 tokens and for whole-prompt batches, computed from the traces.
  - **Host-side emulation of the Mac:**
    - simulate the cache on the host CPUs;
    - feed miss bytes per token into A6, with SSD at 5.85-10.6 GB/s (assumed), 3.4 GB/s (the flash-moe-derived low case) and 2 GB/s for mmap, and e = 0.47-0.61 of 614 GB/s;
    - output: predicted Mac decode and prefill for the K2.6 Q2 and K2-Thinking TQ1_0 files, with 14%, 22% and 32% of the pool cached.
- **GPU-hours: about 13-51.**

  | Step | Arithmetic | GPU-hours | Needs GPU 0? |
  |---|---|---|---|
  | Pilot and setup | — | 5-15 | partly |
  | Generate transcripts (INT4) | 1.6M tokens at 0.075-0.55M per GPU-hour | 2.9-21 | yes, after 2026-10-21 |
  | Trace by prefill (INT4, SGLang) | 4M tokens at 0.9-4.5M per GPU-hour | 0.9-4.4 | yes |
  | Trace the Q2 GGUF | 1M tokens of prefill on 5 GPUs, or with experts in host RAM | 1-3 (or 0 on CPU) | no |
  | Decode-routing check | small decode sample | 2-4 | yes |
  | Emulator-validation traces (V4 Flash, GLM 5.3) | about 0.5M tokens each, GGUF on 2-3 GPUs | 1-3 | no |
  | Cache simulation and emulation | host CPUs | 0 | no |

  Before 2026-10-21, the setup, the GGUF traces, the emulator validation and the simulator can all run on GPUs 1-7 and the CPUs. Transcripts could also be generated from the Q2 GGUF, at the cost of measuring INT4-vs-Q2 routing agreement first.
- **Risks:**
  - Tracing V4 Flash and GLM 5.3 depends on runtime support on the host:
    - mainline llama.cpp supports DeepSeek V4 (PR #24162, merged 2026-06-29) [S118];
    - ds4 runs GLM 5.3 and has a CUDA path [S110];
    - whether mainline llama.cpp or SGLang supports GLM 5.3 on H100 is unchecked.
  - Emulation cannot capture macOS memory pressure [S88], or how a 90%-full 2 TB SSD behaves. Both stay stated assumptions.
  - The ds4 numbers used for validation are single runs or three-run medians on particular prompts.

### G4 (PARTLY_DONE). What does 2-bit cost DeepSeek V4 Flash 0731 on real tasks?

- **Status: PARTLY_DONE.**
  - A fidelity ladder for about 48 quants of the 0731 checkpoint exists, measured on 8× RTX 5090 hardware against one BF16 reference (AtomicChat, 2026-08-03) [S117]. The other publishers' files are split into three result files "by the machine that produced them"; the ds4 Q2 row is in RIVALS-B3:

    | File | Size (GB) | KLD | Same top token |
    |---|---|---|---|
    | antirez IQ2XXS-0731 (ds4 Q2) | 86.7 | 0.408 | 78.98% |
    | Unsloth UD-IQ3_XXS-0731 | 104.2 | 0.261 | 83.46% |
    | Unsloth UD-Q2_K_XL-0731 | 96.8 | 0.322 | 80.92% |
    | Unsloth UD-IQ1_S-0731 | 82.5 | 0.486 | 76.15% |

  - Task results exist only in a community model card, which returns HTTP 401 [S131, unverified]. Search summaries describe an average of 78.09 for the full model against 69.85 for a 90.9 GiB GGUF, with thinking off (about −8 points). 90.9 GiB matches ds4's q2–q4 mix (97.6 GB), not ds4 Q2, and the checkpoint (April or 0731) is not stated. The summaries disagree on how many benchmarks were averaged.
  - The task-level cost is still open.
- **Question (falsifiable).** With every setting taken from the 0731 checkpoint, and one reasoning mode pinned per tier:
  - does ds4 Q2 (86.7 GB) lose at most 3 points (absolute, suite average) against Unsloth's 0731 UD-Q8_K_XL, while using at most 10% more reasoning tokens per solved item?
  - does UD-IQ3_XXS-0731 lose at most 1 point?
- **Pre-registered expectation:** the unverified card is only a weak prior, and it points toward the 2-bit hypothesis failing. If it does, the Mac recommendation moves to UD-IQ3_XXS (Tight) or to another model (GLM-5.3-Flash, row F3).
- **What to measure:**
  - suite accuracy by domain, with paired bootstrap CIs;
  - reasoning tokens per solved item;
  - tool-call schema accuracy;
  - reproduce 2-3 AtomicChat KLD rows as a check instead of re-measuring all of them;
  - a non-thinking MMLU-style tier, so the result can be compared with the community card;
  - **a 100-item kernel-path check on the host:** the same GGUF on llama.cpp's CUDA and CPU backends. The BF16 reference's perplexity differs by 4-5% between the RTX 5090 and H100 kernel paths, with the same file, corpus and commit [S117], and the Mac uses a third path (Metal).
- **GPU-hours: about 18-137.** It does not need GPU 0.
  - 4 quantized settings × 6.4-11.2M tokens at 0.5-3M per GPU-hour, 2 GPUs each: 8.5-90.
  - Reference UD-Q8_K_XL (161.9 GB, 3 GPUs): 6.4-11.2M tokens at 0.33-2M per GPU-hour: 3.2-34.
  - Kernel-path check: 1-3. Setup: 5-10.
- **Risks:**
  - llama.cpp's CUDA backend supports V4 since PR #24162 [S118]. The novelty verifier reported that commenters needed to rename tensors to load the antirez files (not re-checked), so load-test them in the pilot.
  - On H100 (compute capability 9.0), llama.cpp unpacks MXFP4 to BF16 [S117].
  - The card recommends temperature 1.0 [S115], which raises variance and may need more seeds.

### G5 (PARTLY_DONE). Can Kimi K2 run with fewer active experts?

- **Status: PARTLY_DONE.**
  - Reducing top-k is characterized on 12 fine-grained checkpoints in 9 families up to 295B, including V4 Flash 0731 and Qwen3-235B [S119]:
    - keeping ⌈2k/3⌉ of the chosen experts preserves 98.8% of unpruned performance, averaged over the nine models of its budget sweeps;
    - V4 Flash 0731, k 6 → 4: 75.69 → 74.53 average.
  - On Qwen3.5-397B (10 → 5 experts), normalizing the gate weights by the top-10 mass instead of the top-5 cuts the MMLU loss from 2.10 to 0.55 points. The authors find standard renormalization over the reduced set, every implementation's default, "the worst choice in that grid" [S120].
  - ik_llama.cpp's SER already uses fewer experts at run time in a llama.cpp-style engine [S121].
  - **It has not been measured on Kimi K2.** What is new: the first Kimi K2 measurement, and how fewer experts change the streaming hit rate (from G2's traces).
- **Question (falsifiable).** K2.6's router uses sigmoid scores, `norm_topk_prob` true and a routed scaling factor of 2.827 (A8). With two renormalization variants:
  - standard: normalize over the k experts used;
  - anchored: normalize over the trained top-8,

  does top-6 lose at most 1 point and top-4 at most 3 points on the suite?
- **Why it matters:** at a fixed hit rate, my estimate is 28-30% (top-6) and 76-87% (top-4) faster streamed decode for the K2.6 Q2 file (section 3e).
- **What to measure:**
  - KLD against top-8;
  - suite accuracy;
  - routed bytes per token;
  - the change in hit rate, replayed on the G2 traces;
  - predicted Mac decode from the G2 emulator.
- **GPU-hours: about 29-314 with INT4 evaluation.**
  - **Screen** (KLD, 4 variants): 1-5. Runs before 2026-10-21, on either:
    - the K2.6 Q2 GGUF, where the standard variant is a stock override (`--override-kv deepseek2.expert_used_count=int:K`) [S121]; or
    - the GSQ checkpoint.
  - **Task evaluation of 2 finalists on INT4 at TP8:** 2 × 6.4-11.2M tokens at 0.075-0.55M per GPU-hour = 23-299. This needs all 8 GPUs, so it runs after 2026-10-21. The INT4 reference is shared with G1.
  - **Setup:** 5-10.
  - Running the evaluation on the GSQ 2-bit checkpoint instead (TP4: 68.4 GiB per GPU, about 11 GiB free) would cost less, but the result may not transfer to INT4.
- **Risks:**
  - vLLM can change `num_experts_per_tok` by a config override. The anchored variant needs a router change. vLLM's routing uses fused kernels; a torch reference path should allow a Python-only patch, with no new GPU kernel. Confirm this in the pilot.
  - Results may not transfer to the low-bit files a Mac would run.

### G1 (PARTLY_DONE). How much can a Kimi K2.x keep at about 100 GB?

- **Status: PARTLY_DONE.**
  - The measured Kimi K2.x points are at about 288-294 GB:
    - GSQ dense 2.13-bit, 294 GB, with task results [S111];
    - REAP 50% + INT4, 288 GB [S63, S64].
  - What pruning did to Kimi K3 [S113]:
    - at 50% (REAP or Nota, maker evaluations), GPQA-D falls 17-20 points (86.36 → 66.67-69.19), while HumanEval+ holds (82.32 → 82.32 and 81.71);
    - without calibration (experts ranked by router weights), 5-shot GSM8K falls from 95.53% to 68.23% at 50% and 34.42% at 75%, on one harness;
    - at 80% with native MXFP4 experts, single greedy prompts drift and loop in Chinese, but the factual probe is answered;
    - at 82% plus 2-bit experts, the factual probe fails; lowering top-k did not help;
    - above 50%, the coding evidence is one greedy prompt per build; no coding benchmark exists there.
  - On Kimi K2, REAP at 50% already drops knowledge multiple-choice from 0.780 to 0.643 [S59], below 90%.
  - So round 1's hypothesis, that a general-purpose 100 GB Kimi keeps 90% or more, is very likely false. No K2.x model at 100 GB or less has been measured.
- **Reframed question (falsifiable).** Does a Kimi K2.6 of 100 GB or less keep at least 90% of the INT4 reference on the coding and tool-use parts of the suite? Knowledge is reported as collateral.
  - **The build** (size = 1,014.7B × (1 − pruned share) × expert bits ÷ 8 + 9.34 GB of non-routed weights from the Q2 file):
    - 75% of experts pruned with a code-and-tool calibration, experts at 1.6-2.7 bits: 60-95 GB; or
    - 62.5% pruned, experts at 1.9 bits or fewer: 85 GB at 1.6 bits. At 2 bits it is 104.5 GB, over the bound.
  - In the screen grid below, every configuration of 100 GB or less at 2 bits or more is a 75% prune. The nearest K3 analogue, 82% pruned at 2 bits, fails the factual probe, and calibration-free 75% pruning cut K3's GSM8K from 95.5% to 34.4%. That lowers the prior further.
  - The alternative outcome is an honest desk exit for general use, recorded with the K3 evidence.
- **Prior:** put the K3 numbers into the pre-registration, and expect the Stage-1 stop rule to trigger.
- **Building configurations:**
  - **(a) GGUF imatrix route.** Cheap: the quantization is CPU-heavy, from the INT4 weights or a lossless Q8 repack.
    - It gives only a lower bound on what 2 bits can reach. GSQ beat Unsloth's files at about equal size: AgentBench KG 45 vs 39 on K2.5, GSQ at 2.37 bits against UD-IQ1_M (an i-quant mix at 2.4 bits); Qwen3-4B Q2_K 48.34 vs 35.01 [S111].
    - So a negative stock-quant result does not falsify the hypothesis.
  - **(b) GSQ route (Humming checkpoint, CUDA-only).** GSQ took 24 hours on 8×H200 for K2.5, i.e. 192 H200 GPU-hours per configuration [S111]. I assume 190-250 H100 GPU-hours. Screen at most 1-2 configurations.
    - The GSQ repository lists Kimi K2/K2.5 as needing a full node of 8× H100/H200 at minimum, typically 1-2 nodes [S138]. With GPU 0 held, it runs after 2026-10-21.
    - GSQ checkpoints need humming-kernels, a published, prebuilt package. Decide whether it counts as "stock" before using it (section 5).
    - The output runs only on CUDA, so it measures what GSQ can do, not a file the Mac can run.
  - **(c) GSQ refinement of a Kimi GGUF K-quant (Metal-compatible output).** GSQ starts from an existing K-quant GGUF and writes the same format, which runs on stock llama.cpp [S111, S138].
    - Tested only on dense Qwen3-8B and Qwen3-4B. First check whether the repository's K-quant path handles Kimi's MoE expert tensors and every tensor type in the starting file.
    - Not costed; assume at least the full-node requirement of (b), so after 2026-10-21.
    - If it works, it is the only route here that applies GSQ's optimizer to a file the Mac could run. Its quality on Kimi is unknown.
- **Calibration:**
  - Use Cerebras REAP's layer-wise observer [S61]. The INT4 model can stay in the host's 1.77 TB of RAM while layers stream to one GPU, so calibration need not wait for GPU 0 (untested).
  - Ex0bit published K2.5 REAP saliency scores and a Kimi observer [S114]. They come from an abliterated K2.5 variant and are pickle files (load with `weights_only=True`), so use them only as a cross-check.
- **What to measure:**
  - bytes on disk and peak memory;
  - KLD and top-1 agreement against the INT4 reference on fixed text;
  - suite accuracy by domain, with paired bootstrap CIs;
  - reasoning tokens per solved item [S33];
  - tool-call schema accuracy, with the chat template and parser fixed [S35];
  - repetition and non-termination rate [S65];
  - predicted Mac decode and prefill: A4 for files that fit in memory, the G2 emulator otherwise.
- **GPU-hours: about 54-306 on the k-quant route.** Add 190-250 for each GSQ configuration (route b); route (c) is not costed.

  | Step | Arithmetic | GPU-hours |
  |---|---|---|
  | Calibration | 12k samples × 4k tokens = 49M tokens at 0.9-4.5M per GPU-hour | 11-54 |
  | KLD screen | 12 configurations (pruning {0, 50, 62.5, 75%} × expert bits {1.6, 2.2, 2.7}), 0.5M tokens each, plus load time. Four are 100 GB or less (62.5% at 1.6 bits; 75% at all three); the rest are reference points on the curve | 14-19 |
  | Task evaluation of 2 finalists | 2 × 6.4-11.2M tokens at 0.27-0.72M per GPU-hour | 18-83 |
  | INT4 reference | 6.4-11.2M tokens at 0.075-0.55M per GPU-hour (shared with G3 and G5) | 12-149 |

  Stage 1 (calibration + screen) costs 25-73 GPU-hours, with a stop rule: stop if no configuration of 100 GB or less reaches 80% top-1 agreement.
- **Risks:**
  - Requantizing weights that were trained for INT4 may compound error.
  - A pruned Kimi GGUF may not load in stock llama.cpp. Nota's non-uniform K3 prune needed a patched vLLM model file [S113].
  - The INT4 reference and both GSQ routes need all 8 GPUs.

### G3 (OPEN, conditional on G1). At equal memory, does a compressed Kimi beat the best model that fits?

- **Status: OPEN, but the prior is low.**
  - V4 Flash 0731 (34), V4.1 Flash (39), Qwen3.8-Flash-Next (40) and GLM-5.3-Flash (42) all score above full-precision Kimi K2.6 (27) [S105, S116].
  - V3.1 at 1 bit scored below unquantized Qwen3-235B on Aider [S19].
  - The K3 pruning evidence (G1) points the same way.
- **Run only if G1 Stage 1 passes.** Otherwise, replace G3 with a desk comparison of published numbers (GSQ AgentBench, Artificial Analysis).
- **Question (falsifiable).** At 105 GB or less, does the best compressed Kimi from G1 score at least 2 points higher than each of the following, with the 95% paired bootstrap CI excluding 0?
  - V4 Flash 0731 ds4 Q2 (86.7 GB) and UD-IQ3_XXS-0731 (104.2 GB);
  - GLM-5.3-Flash ds4 Q2 (96.5 GB);
  - Qwen3.8-Flash-Next ds4 Q2 (41.7 GiB in memory);
  - Qwen3-235B-2507 UD-Q3_K_XL (104.2 GB);
  - gpt-oss-120b (63.4 GB).
- **What to measure:**
  - suite accuracy with paired CIs;
  - tokens per solved item;
  - tool-call schema accuracy;
  - a host kernel-path check (CUDA vs CPU) on a 100-item subset per model, standing in for Metal;
  - predicted Mac speed and memory, from A4 or the G2 emulator.
- **GPU-hours: about 10-139**, not counting the G1 Kimi run or G4's V4 Flash runs, which are reused.
  - 3 new configurations (GLM-5.3-Flash ds4 Q2, Qwen3.8-Flash-Next ds4 Q2, Qwen3-235B UD-Q3_K_XL) × 6.4-11.2M tokens at 0.27-3M per GPU-hour: 6.4-124.
  - gpt-oss-120b on single-GPU vLLM: 2-11.
  - Kernel-path check: 2-4.
- **Risks:**
  - A confirmatory negative is the most likely outcome.
  - Chat templates and tool parsers confound comparisons between model families [S35].
  - ds4 is the runtime for the GLM-5.3-Flash and Qwen3.8 files, and it "is not a general GGUF runner" [S110]. The host would need a ds4 CUDA build; check its CUDA requirements against R570.

**Suggested order**
1. **G2 (OPEN):** the host-side traces and the emulator. Most of it can run before 2026-10-21.
2. **G4**, with every setting pinned to 0731. It runs on GPUs 1-7.
3. **G5**, with both renormalization variants: screen now, INT4 evaluation after 2026-10-21.
4. **G1**, only in its reframed (coding-specialist) form, and Stage 1 first.
5. **G3**, only if G1 Stage 1 passes.

---

## 5. What it would take to try it

### Mac disk

- **Measured on 2026-10-15:** 203 GB free; the data volume is 90% used [S129].
- **Space being freed.** The task brief says about 238 GB more is being freed. It is not known whether that comes on top of today's 203 GB. So free space after the cleanup is somewhere between 203 GB and about 441 GB. Re-measure with `df -H /` before any download.
- **Floor.** I assume a free-space floor of 50 GB for swap and APFS (my assumption). The Mac was swapping 11.3 GiB under a memory-pressure warning when checked [S129]. Usable space = free space − 50 GB.

| File or set | Size (GB) | Fits in 153 GB usable (today) | Fits in 391 GB usable (if the 238 GB is extra) |
|---|---|---|---|
| gpt-oss-120b | 63.4 | yes | yes |
| V4 Flash 0731 ds4 Q2 | 86.7 | yes | yes |
| Qwen3-235B UD-Q2_K_XL / UD-Q3_K_XL | 88.8 / 104.2 | yes | yes |
| GLM-5.3-Flash ds4 Q2 | 96.5 | yes | yes |
| Qwen3.8-Flash-Next ds4 Q2 | 147.2 | yes, just | yes |
| V4 Flash Q2 + gpt-oss-120b | 150.1 | yes, just | yes |
| DeepSeek Flash MXFP4 (streamed, measured) | 156.0 | no | yes |
| GLM-5.3-Flash Q4_K (streamed, measured) | 190.9 | no | yes |
| Full GLM 5.3 IQ2_XXS (streamed, measured) | 211.1 | no | yes |
| GLM 5.3 IQ2_XXS + V4 Flash Q2 + gpt-oss-120b | 361.2 | no | yes |
| Smallest Kimi: smol-IQ1_KT / K2.5 UD-TQ1_0 | 235.1 / 239.5 | no | yes |
| Kimi K2.6 UD-Q2_K_XL | 340.5 | no | yes (about 100 GB left) |
| V4.1 Flash Q2 | 365.7 | no | yes, just (75 GB left) |
| Kimi K2.6 INT4 / smallest Kimi K3 | 595.2 / 466.4 | no | no |

- An external Thunderbolt 5 NVMe is untested. On a PC, Colibri gained 37.5% from a second NVMe [S52]. ds4 asks for a fast local SSD [S109, S110].
- Whether a nearly full drive reads more slowly is not measured.

### Downloads

Download time in hours = GB × 8 ÷ (link speed in Gb/s × 3,600). At an assumed 1 Gb/s:

| File | Time |
|---|---|
| V4 Flash Q2 (86.7 GB) | about 0.19 h (11 min) |
| GLM 5.3 IQ2_XXS (211.1 GB) | about 0.47 h |
| Kimi K2.6 Q2 (340.5 GB) | about 0.76 h |
| Kimi K2.6 INT4 (595.2 GB; already on the host) | about 1.3 h |
| Whole host set (about 3.0 TB, below) | about 6.8 h |

Neither machine's link speed was measured.

### Licences, as recorded by the sweeps and re-checked where marked

| Model | Licence |
|---|---|
| Kimi K2.x | Modified MIT. Products with more than 100M monthly active users or more than US$20M monthly revenue must display "Kimi K2.6" in the UI [S7]. The GSQ, kwanhee and Ex0bit derivatives carry the same licence [S112, S64, S114]. |
| Kimi K3 | "Kimi K3 License". Text not read; reports conflict [S8, S107]. The pruned K3 builds inherit it [S113]. |
| DeepSeek V3.x, R1, V4 Flash (April and 0731), V4.1 Flash, V4 Pro | MIT [S9, S12, S115] |
| Qwen3-235B-2507, Qwen3-Coder-480B, Qwen3.5-397B | Apache-2.0 per Hugging Face metadata [S9] |
| Qwen3.8-2.4T | "qwen3.8-max" [S9] |
| Qwen3.8-Flash-Next | Qwen Community License 1.0 [S116] |
| GLM-4.5, 4.6, 4.7, GLM-5, GLM-5.2, GLM-5.3-Flash | MIT [S9, S116] |
| GLM 5.3 | "glm-5.3" (Hugging Face); "GLM-5.3 License" (Artificial Analysis) [S9, S116] |
| gpt-oss-120b, Mistral Large 3, MiniMax-M1 | Apache-2.0 |
| MiniMax-M3 | "minimax-community" |
| Llama-4-Maverick | Gated [S9] |

### H100 host

**Hardware and state**
- **GPUs:** 8 × H100 80 GB. About 79.6 GiB (85.5 GB) is usable per GPU, 637 GiB (684 GB) in total. This is the host figure from the task brief; it matches the standard nvidia-smi total of 81,559 MiB.
- **GPU 0** is held by another project's job until 2026-10-21. Anything that needs all 8 GPUs waits until then. In this program that means Kimi K2.6 INT4 at TP8.
- **Other:** 1.77 TB of RAM; 208 CPU cores; about 20 TB of disk; R570 driver; Slurm; stock runtimes only.
- **Kimi K2.6 INT4 is on the host.** Job 1528 fetched it with the CPU lane (0 GPU-hours): 96 files, 595,204,999,341 bytes, matching the Hub listing file for file, including all 67 LFS SHA-256 values [S140].

**What fits on the GPUs**
- **Kimi K2.6 INT4** (595.2 GB = 554.3 GiB):
  - at TP8 it takes 69.3 GiB per GPU, leaving 10.3 GiB raw per GPU;
  - the KV cache is copied to every GPU (section 4), so concurrency is limited;
  - it needs all 8 GPUs, so it waits until 2026-10-21.
- **GSQ 2-bit K2.6** (294.0 GB = 273.8 GiB):
  - 34.2 GiB per GPU at TP8;
  - 68.4 GiB per GPU at TP4, about 11 GiB free;
  - so it can run on GPUs 1-4 before 2026-10-21, if humming-kernels is accepted as stock.
- **K2.6 UD-Q2_K_XL** (340.5 GB) in llama.cpp CUDA: on 5 GPUs (427 GB), or with the experts in host RAM.
- **DeepSeek V4 Flash 0731:** the official weights (166.9 GB stored [S115]) at TP4; the GGUFs on 2-3 GPUs. Mistral Large 3 NVFP4 also fits.
- **DeepSeek V3.x FP8 (689 GB)** does not fit. Use Red Hat's INT4 build (371 GB, vLLM) or Q4_K_XL (387 GB) instead.
- **Do not fit:** K2-Instruct FP8 (1,029 GB), BF16 K2 (2 TB), DeepSeek-V4-Pro (865 GB), GLM 5.3 FP8 (about 756 GB stored [S134]) and Kimi K3.

**Host RAM (1.77 TB): an option for CPU-side routing analysis.** None of this has been tried on the host.
- It can hold K2.6 INT4 (595 GB), the Q2 GGUF, or even K2-Instruct FP8 (1,029 GB).
- llama.cpp or ik_llama.cpp can keep the experts on the CPU (`-ot exps=CPU`, as in S40) and attention on 1-2 GPUs. That would produce routing traces from GGUF files while GPU 0 is busy.
- KTransformers-style hybrid runs [S37] and REAP's layer-wise calibration, with layers streamed from RAM to one GPU.
- Cache simulation and trace replay for G2 on the 208 cores.

**Files for G1-G5 on the host: about 3.0 TB** of the 20 TB:
- Kimi:
  - K2.6 INT4: 595.2 (on the host [S140]);
  - K2.6 UD-Q2_K_XL: 340.5;
  - K2.6 GSQ: 294.0;
  - K2-Thinking UD-TQ1_0: 246.8.
- V4 Flash:
  - 0731 official: 166.9;
  - 0731 UD-Q8_K_XL: 161.9;
  - UD-IQ3_XXS: 104.2;
  - UD-Q2_K_XL: 96.8;
  - UD-IQ1_S: 82.5;
  - ds4 Q2: 86.7;
  - Vision-Exp MXFP4 (the file ds4 measured): 156.0.
- GLM:
  - GLM 5.3 IQ2_XXS (the file ds4 measured): 211.1;
  - GLM-5.3-Flash ds4 Q2: 96.5.
- Others:
  - Qwen3.8-Flash-Next ds4 Q2: 147.2;
  - Qwen3-235B Q2 and Q3: 88.8 + 104.2;
  - gpt-oss-120b: 63.4.

Pruned intermediate files, and a 2 TB BF16 Kimi if requantization from BF16 is needed, could add 1-4 TB. That still fits.

**Runtimes**
- **"Stock only" and no generated kernels** allow:
  - vLLM and SGLang. vLLM's CUDA 13 images run on R535 and R570 host drivers in compatibility mode on datacenter GPUs, with `VLLM_ENABLE_CUDA_COMPATIBILITY=1` [S124]. So R570 need not pin the host to an old vLLM. Test a pinned image in the pilot;
  - SGLang's `per_token` expert recorder (stock) [S122];
  - llama.cpp built with CUDA, which supports DeepSeek V4 since PR #24162 [S118];
  - ik_llama.cpp, needed for ubergarm's IQ*_KS / IQ*_KT quants; it also has SER [S18, S121];
  - EXL3 (CUDA 12.4 or later). It lists DeepSeek V3/V4, GLM, Qwen3 MoE, MiniMax-M2 and gpt-oss, but not Kimi K2 [S27];
  - KTransformers [S37];
  - a ds4 CUDA build, for the GLM 5.3, V4 and Qwen3.8 ds4 files [S110]. Its CUDA requirements are not checked.

  Each needs a pinned image.
- **Decisions needed on "stock only":**
  - humming-kernels for the GSQ checkpoints: a published, prebuilt package, not model-generated code [S112];
  - Nota's patched vLLM model file for its non-uniform K3 prune [S113].
- **Not runnable:** the kwanhee REAP-50 INT4 Kimi. Its vLLM fork is private (HTTP 404) [S132].
- **Other constraints:**
  - REAP calibration is PyTorch.
  - Router tracing uses SGLang's recorder or a llama.cpp evaluation callback. Both are host code; no custom GPU kernels are needed.
  - Speeds measured on Blackwell (B200, RTX PRO 6000, RTX 5090) do not carry over to H100. On H100, llama.cpp unpacks MXFP4 to BF16 [S117].

### Mac memory headroom (shared with other sessions)

This is for Kevin's own use of the models; no experiments run on the Mac.
- **Measured on 2026-10-15** [S129]: 57.6 GiB (61.8 GB) free (45%); swap 11.3 GiB used and 57.0 GiB compressed; memory-pressure warning. Headroom's "GB" are GiB. This is a snapshot: later readings the same day were 46.1 and 70.4 GiB free.
- **Default ceiling.** The default Metal working-set ceiling is 107.52 GiB [S1]. Raising it (`sudo sysctl iogpu.wired_limit_mb=N`, which resets on reboot) takes memory from macOS and the other sessions.
  - One idle oMLX server held 19.8 GB on a 128 GB M4 Max [S108].
  - Base macOS used 27-30 GB on a 512 GB Mac Studio (vendor blog) [S101].
- **Gate every model run with Headroom** (`headroom can-start`) and pause other heavy sessions. Two crashes under heavy concurrency are on record for this Mac.
- **For streaming:**
  - ds4 warns that an oversized expert cache can push the non-routed weights out of memory and slow decoding. Start with its automatic budget [S109].
  - With page-cache streamers, macOS compresses memory before giving up file cache, and Metal-wired pages cannot be evicted [S82].
  - A cache that is too large lowers speed through memory pressure [S88].
  - Tune the cache size on measured tokens/s, not on hit rate.
- **Stay on ds4's Metal path.** Its CONTRIBUTING.md warns that running the CPU path on Metal can crash the system, because of a kernel bug in macOS [S95].
- **Energy.** A simulation estimates SSD streaming at up to about 12 times the energy per token of HBM [S58]. Run streaming on mains power.

---

## 6. Sources

Read levels for S1-S108 are those recorded by the round-1 sweep agents; "round 2" notes what the second draft re-opened and "round 3" what this draft re-opened. S109-S137 were read by the second draft and S138-S140 by this one. Dates are publication dates where known, otherwise the access date.

| ID | Source | URL | Date | Kind | Read level |
|---|---|---|---|---|---|
| S1 | Local measurement on Kevin's Mac: `sysctl iogpu.wired_limit_mb hw.memsize` and Metal `recommendedMaxWorkingSetSize` (sweep 5) | local (scratchpad/wset.swift) | 2026-10-15 | measurement | full; re-checked in round 2 [S129] |
| S2 | Apple MacBook Pro tech specs (M5 Max bandwidth, configurations) | https://www.apple.com/macbook-pro/specs/ | accessed 2026-10-15 (product 2026-03-03) | official | skim |
| S3 | Computerworld, M5 Max MacBook Pro (Blackmagic SSD test) | https://www.computerworld.com/article/4148742/heres-what-5849-gets-you-in-an-m5-max-macbook-pro.html | 2026-03-23 | other | skim; round 3: article text read (12,587.3 MBps read; 128 GB, 4 TB unit) |
| S4 | MacDailyNews on M5 Max SSD speed (The Verge and PetaPixel figures) | https://macdailynews.com/2026/03/10/apples-new-m5-max-macbook-pro-delivers-a-huge-ssd-read-write-speed-boost/ | 2026-03-10 | other | skim |
| S5 | Kimi K2-Instruct model card and config.json | https://huggingface.co/moonshotai/Kimi-K2-Instruct ; https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/config.json | 2025-07 | model card / official | card skim, config full |
| S6 | Kimi K2-Thinking model card | https://huggingface.co/moonshotai/Kimi-K2-Thinking | 2025-11-04 | model card | skim |
| S7 | Kimi K2.6 model card and licence | https://huggingface.co/moonshotai/Kimi-K2.6 | 2026 (about 2026-04-20 per secondary coverage) | model card | skim |
| S8 | Kimi K3 model card; K3 paper (QAT section); MoonshotAI/Kimi-K3 repository | https://huggingface.co/moonshotai/Kimi-K3 ; https://www.alphaxiv.org/abs/2607.24653 ; https://github.com/MoonshotAI/Kimi-K3 | 2026-06-13 (repo), 2026-07-27 (paper) | model card / paper | skim |
| S9 | Hugging Face API metadata for the model inventory (DeepSeek, Qwen, GLM, MiniMax, Llama, gpt-oss, Kimi) | https://huggingface.co/api/models/deepseek-ai/DeepSeek-V4-Pro (and sibling endpoints) | queried 2026-10-15 | official | full |
| S10 | gpt-oss-120b model card and Unsloth GGUF sizes | https://huggingface.co/openai/gpt-oss-120b | 2025-08-05 | model card | skim |
| S11 | Mistral Large 3 675B model card | https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512 | 2025-11-28 | model card | skim |
| S12 | DeepSeek-V4-Flash model card (April checkpoint) | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash | 2026-04 | model card | skim; round 3: README read (284B parameters, 13B activated) |
| S13 | DeepSeek-V4.1-Flash paper | https://www.alphaxiv.org/abs/2609.19969 | 2026-09-17 | paper | abstract only |
| S14 | Unsloth Kimi K3 docs (GGUF sizes, KLD, top-1) | https://unsloth.ai/docs/models/kimi-k3 | 2026-07-27 to 2026-08-07 | maintainer benchmark | skim |
| S15 | Unsloth Kimi K2.6 docs (sizes, perplexity) | https://unsloth.ai/docs/models/kimi-k2.6 | 2026-04-20 (repo) | maintainer benchmark | skim |
| S16 | Unsloth Kimi-K2-Instruct-0905 GGUF listing (plus K2-Thinking and K2.7-Code listings) | https://huggingface.co/unsloth/Kimi-K2-Instruct-0905-GGUF | queried 2026-10-15 | official repo | full |
| S17 | Unsloth Kimi K2 / K2-Thinking / K2.5 run guides | https://unsloth.ai/docs/basics/kimi-k2-how-to-run-locally ; https://unsloth.ai/docs/models/tutorials/kimi-k2-thinking-how-to-run-locally ; https://unsloth.ai/docs/models/tutorials/kimi-k2.5 | undated (notes 2025-07 to 2026) | official docs | skim |
| S18 | ubergarm Kimi-K2-Instruct GGUF perplexity ladder | https://huggingface.co/ubergarm/Kimi-K2-Instruct-GGUF | 2025-07-14 (modified 2025-07-22) | maintainer benchmark | skim |
| S19 | Unsloth dynamic GGUFs on Aider Polyglot (DeepSeek-V3.1) | https://unsloth.ai/docs/basics/dynamic-3.0-ggufs/unsloth-dynamic-ggufs-on-aider-polyglot | 2025-09-10 | maintainer benchmark (community-run) | skim (sweep 1), full .md (sweep 5) |
| S20 | China Unicom, quantized DeepSeek-R1/V3 evaluation, arXiv 2505.02390 | https://arxiv.org/abs/2505.02390 | 2025-05-05 (v2 2025-06-13) | paper | full |
| S21 | Unsloth DeepSeek-R1 run guide (1.58-bit dynamic) | https://unsloth.ai/docs/models/tutorials/deepseek-r1-how-to-run-locally | 2025-01-27 | maintainer benchmark | skim |
| S22 | Pruning plus mixed-precision DeepSeek-V3 / R1, arXiv 2509.25689 | https://arxiv.org/abs/2509.25689 | 2025-09-30 | paper | skim; round 2: sections via orx full text (Table 1 caption, deployment section) |
| S23 | Unsloth DeepSeek V4 docs (V4-Flash perplexity and KLD table, memory table, DSpark) | https://unsloth.ai/docs/models/deepseek-v4 | 2026-07 to 2026-08 | maintainer benchmark | skim |
| S24 | Unsloth DeepSeek-V4-Flash GGUF listing, plus Unsloth and mlx-community listings for Qwen3.5-397B, GLM-4.7, GLM-5.3-Flash, Qwen3-235B-2507, MiniMax-M2.7 and others | https://huggingface.co/unsloth/DeepSeek-V4-Flash-GGUF | queried 2026-10-15 | official repo | full |
| S25 | mlx-lm LEARNED_QUANTS.md (DWQ, AWQ, GPTQ) | https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LEARNED_QUANTS.md | undated (2026 HEAD) | official docs | skim |
| S26 | RedHatAI DeepSeek-R1-0528 w4a16; Qwen3-235B GPTQ-Int4 size | https://huggingface.co/RedHatAI/DeepSeek-R1-0528-quantized.w4a16 | 2025-05-30 | maintainer benchmark | skim |
| S27 | QTIP, arXiv 2406.11235 (with AQLM 2401.06118, EXL3 README, ik_llama.cpp README) | https://arxiv.org/abs/2406.11235 | 2025-06-18 (v4) | paper | skim |
| S28 | Dettmers and Zettlemoyer, 4-bit precision scaling laws, arXiv 2212.09720 | https://arxiv.org/abs/2212.09720 | 2022-12-19 | paper | abstract only |
| S29 | Quantized reasoning models study (COLM 2025), arXiv 2504.04823 | https://arxiv.org/abs/2504.04823 | 2025-08-18 (v2) | paper | skim |
| S30 | Unsloth MiniMax-M2.5 guide (Benjamin Marie's evaluation); Kaitchup MiniMax-M3 GGUF article | https://unsloth.ai/docs/models/tutorials/minimax-m25 ; https://kaitchup.substack.com/p/minimax-m3-gguf-quantization-from | 2026-02; 2026-06-30 | maintainer benchmark | skim (M3 numbers paywalled) |
| S31 | Low-bit quantization favours undertrained LLMs, arXiv 2411.17691 | https://arxiv.org/abs/2411.17691 | 2024-11-26 | paper | abstract only |
| S32 | Cross-family weight-only PTQ study, alphaXiv 2608.08188 | https://www.alphaxiv.org/abs/2608.08188 | 2026-08-08 | paper | abstract only |
| S33 | CoT token inflation under quantization, alphaXiv 2606.25519 | https://www.alphaxiv.org/abs/2606.25519 | 2026-06-24 | paper | abstract only |
| S34 | llama.cpp quantize README (bits per weight by format) | https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md | undated (2026 HEAD) | official docs | skim |
| S35 | MoonshotAI K2-Vendor-Verifier | https://github.com/MoonshotAI/K2-Vendor-Verifier | 2025-11-15 | official repo | skim; round 2: README read |
| S36 | SSD-LLaMA, arXiv 2609.18110 | https://arxiv.org/abs/2609.18110 | 2026-09-16 | paper | full (sweep 2); skim (sweeps 1, 3, 4); round 2: sections (5.1, 5.2, 5.4) via orx full text; round 3: section 5.2 read-bandwidth and decode-speedup passages |
| S37 | KTransformers: SOSP'25 paper, DeepSeek-R1/V3 tutorial, Kimi-K2 doc | https://madsys.cs.tsinghua.edu.cn/publication/ktransformers-unleashing-the-full-potential-of-cpu/gpu-hybrid-inference-for-moe-models/SOSP25-chen.pdf ; https://raw.githubusercontent.com/kvcache-ai/ktransformers/main/doc/en/DeepseekR1_V3_tutorial.md ; https://github.com/kvcache-ai/ktransformers/blob/main/doc/en/Kimi-K2.md | 2025-10; 2025-02; 2025-07 | paper / official docs | paper full; docs skim |
| S38 | OSDI'26 CPU-GPU hybrid engine, arXiv 2606.10493 | https://arxiv.org/abs/2606.10493 | 2026-06-09 | paper | skim |
| S39 | ik_llama.cpp discussion #258 (DeepSeek-R1 on 256 GB DDR5 + one GPU) | https://github.com/ikawrakow/ik_llama.cpp/discussions/258 | 2025-03 | community report | skim |
| S40 | llama.cpp MoE offload guide (Doctor-Shotgun) | https://huggingface.co/blog/Doctor-Shotgun/llamacpp-moe-offload-guide | 2026-01-30 | community report | skim |
| S41 | llama.cpp PR #29887, GPU LRU expert cache | https://github.com/ggml-org/llama.cpp/pull/29887 | about 2026-10-07 | official repo | skim; round 2: PR body and comments read |
| S42 | vLLM engine arguments; MoE CPU-offload RFC #33869; SGLang issue #11425 | https://docs.vllm.ai/en/latest/configuration/engine_args.html ; https://github.com/vllm-project/vllm/issues/33869 | accessed 2026-10-15; RFC 2026-02-05 | official docs | skim |
| S43 | Geerling beowulf-ai-cluster issue #17 (M3 Ultra llama-bench) | https://github.com/geerlingguy/beowulf-ai-cluster/issues/17 | 2025-12-10 to 2025-12-15 | community report | skim |
| S44 | Simon Willison on DeepSeek-V3-0324 at more than 20 tokens/s (Awni Hannun) | https://simonwillison.net/b/8588 | 2025-03-24 | maintainer benchmark | skim |
| S45 | someoddcodeguy, DeepSeek R1-0528 Q4_K_M and MLX 4-bit on M3 Ultra (includes the MLA KV size) | https://dev.to/someoddcodeguy/running-deepseek-r1-0528-q4km-and-mlx-4-bit-on-a-mac-studio-m3-le4 | 2025-05-29 | community report | skim |
| S46 | oMLX community benchmarks, Kimi K2.6 on M3 Ultra (runs 8y9ori5i, qsgif005, jw1099pr, 93kgjkbc, ez6mnyny) | https://omlx.ai/benchmarks/8y9ori5i ; https://omlx.ai/benchmarks/qsgif005 ; https://omlx.ai/benchmarks/jw1099pr ; https://omlx.ai/benchmarks/93kgjkbc ; https://omlx.ai/benchmarks/ez6mnyny | 2026-04-21 to 2026-06-06 | community report | full; round 3: the four Kimi-K2.6DQ3_K_M-q8 runs re-read (20.3-22.0 at 1K; 439.6 GB peak) |
| S47 | Simon Willison on Kimi K2 Thinking on 2× M3 Ultra (Awni Hannun) | https://simonwillison.net/b/9138 | 2025-11-06 | maintainer benchmark | full |
| S48 | MLX distributed docs (JACCL / RDMA); SiliconBench, arXiv 2609.19169 | https://ml-explore.github.io/mlx/build/html/usage/distributed.html | accessed 2026-10-15; 2026-09-12 | official docs / paper | skim |
| S49 | Jeff Geerling, 1.5 TB of VRAM on Mac Studio (RDMA over Thunderbolt 5) | https://jeffgeerling.com/blog/2025/15-tb-vram-on-mac-studio-rdma-over-thunderbolt-5 | 2025-12-18 | community report | full / skim |
| S50 | flash-moe repository (Dan Woods) | https://github.com/danveloper/flash-moe | about 2026-03 | official repo / community | skim; round 2: see S135 |
| S51 | Simon Willison, streaming experts (Kimi K2.5 on a 128 GB M4 Max) | https://simonwillison.net/2026/Mar/24/streaming-experts/ | 2026-03-24 | community report | full; round 3: re-read (no engine or quant named for the 1.7 tokens/s report) |
| S52 | Colibri repository | https://github.com/JustVugg/colibri | 2026-07-12 (benchmark log) | official repo | skim |
| S53 | ssd-moe deepseek-v4-flash-mlx | https://github.com/ssd-moe/deepseek-v4-flash-mlx | 2026 (undated) | official repo | skim |
| S54 | ik_llama.cpp PR #1634 (--defer-experts) | https://github.com/ikawrakow/ik_llama.cpp/pull/1634 | 2026-04-16 | official repo | skim |
| S55 | LLM in a flash, arXiv 2312.11514 | https://arxiv.org/abs/2312.11514 | 2023-12-12 | paper | skim |
| S56 | PowerInfer-2, arXiv 2406.06282 (and PowerInfer, 2312.12456) | https://arxiv.org/abs/2406.06282 | 2024-06 (v3 2024-12) | paper | skim |
| S57 | Apple ML Research, LLMs with MLX on M5 | https://machinelearning.apple.com/research/exploring-llms-mlx-m5 | 2025-11-19 | official | skim |
| S58 | SSD offload energy study, arXiv 2508.06978 | https://arxiv.org/abs/2508.06978 | 2025-08 | paper | abstract only; round 2: text searched (simulation method) |
| S59 | REAP, arXiv 2510.13999 | https://arxiv.org/abs/2510.13999 | 2025-10-15 | paper | full; round 2: appendix E read |
| S60 | Cerebras REAP blog | https://www.cerebras.ai/blog/reap | 2025-10-16 | maintainer benchmark | skim |
| S61 | Cerebras REAP collection and repository README; HF API listing of author=cerebras | https://huggingface.co/collections/cerebras/cerebras-reap ; https://huggingface.co/api/models?author=cerebras | 2025-10-14 to 2026-03-30 | official repo | full; round 3: API listing (Kimi-Linear-REAP-35B-A3B; GLM-4.6/4.7 REAP in BF16 and FP8) |
| S62 | DeepSeek-V3.2-REAP-345B-A37B model card | https://huggingface.co/cerebras/DeepSeek-V3.2-REAP-345B-A37B | 2025-12-09 | model card | skim |
| S63 | MoESQ, arXiv 2610.02241 | https://arxiv.org/abs/2610.02241 | 2026-09-29 | paper | full; round 2: author list, Tables 3, 6 and 7 read |
| S64 | kwanhee/Kimi-K2.5-REAP50-INT4-W4A16 | https://huggingface.co/kwanhee/Kimi-K2.5-REAP50-INT4-W4A16 | not stated (2026) | model card | full; round 2: card re-read in full |
| S65 | 0xSero/Kimi-K2.6-519B-NVFP4 | https://huggingface.co/0xSero/Kimi-K2.6-519B-NVFP4 | not stated (2026) | community report | full |
| S66 | MoBE, arXiv 2508.05257 | https://arxiv.org/abs/2508.05257 | 2025-08-07 | paper | skim |
| S67 | MoE-XBench, arXiv 2608.21693 | https://arxiv.org/abs/2608.21693 | 2026-08-22 | paper | skim |
| S68 | REAM, arXiv 2604.04356 | https://arxiv.org/abs/2604.04356 | 2026-04-06 | paper | abstract only |
| S69 | HOPE, arXiv 2609.18916 | https://arxiv.org/abs/2609.18916 | 2026-09-16 | paper | abstract only |
| S70 | Expert-scoring criteria papers: arXiv 2606.15716, 2607.01710, 2609.04453, 2603.18492 | https://arxiv.org/abs/2606.15716 | 2026-03-19 to 2026-09-03 | paper | abstract only |
| S71 | Post-compression fine-tuning, arXiv 2609.06076 | https://arxiv.org/abs/2609.06076 | 2026-09-05 | paper | abstract only |
| S72 | Translation-specialist expert extraction, arXiv 2605.28042 | https://arxiv.org/abs/2605.28042 | 2026-05-27 | paper | abstract only |
| S73 | EEP 2407.00945; NAEE 2402.14800; MoE-Pruner 2410.12013 | https://arxiv.org/abs/2407.00945 | 2024-02 to 2024-10 | paper | abstract only |
| S74 | Sub-MoE 2506.23266; MC-SMoE 2310.01334; HC-SMoE 2410.08589 | https://arxiv.org/abs/2506.23266 | 2023-10 to 2025-06 | paper | abstract only |
| S75 | D2-MoE 2502.17298; MoE-SVD (ICML 2025); LorExperts 2608.07814 | https://arxiv.org/abs/2502.17298 ; https://proceedings.mlr.press/v267/li25az.html ; https://arxiv.org/abs/2608.07814 | 2025-02 to 2026-08 | paper | abstract only |
| S76 | CD-MoE, arXiv 2412.00069 | https://arxiv.org/abs/2412.00069 | 2024-11-26 | paper | abstract only |
| S77 | DeepSeek-R1, arXiv 2501.12948 | https://arxiv.org/abs/2501.12948 | 2025-01-22 | paper | skim |
| S78 | Kimi-Linear-48B-A3B card; Kimi-Dev-72B card | https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Instruct ; https://huggingface.co/moonshotai/Kimi-Dev-72B | 2025-10-30; 2025-06 | model card | skim |
| S79 | MoE-to-dense conversion, arXiv 2605.28207 | https://arxiv.org/abs/2605.28207 | 2026-05-27 | paper | abstract only |
| S80 | Simon Willison on DeepSeek V4 | https://simonwillison.net/2026/apr/24/deepseek-v4 | 2026-04-24 | other | skim |
| S81 | Unsloth Qwen3-Coder-REAP-363B-A35B GGUF | https://huggingface.co/unsloth/Qwen3-Coder-REAP-363B-A35B-GGUF | not stated (source checkpoint 2025-10-30) | model card | full |
| S82 | Kernel-tiering MoE trace study, arXiv 2608.12103 | https://arxiv.org/abs/2608.12103 | 2026-08-12 (v2 2026-08-30) | paper | skim; round 2: Table 1 and LRU sections read |
| S83 | Mixtral of Experts, arXiv 2401.04088 | https://arxiv.org/abs/2401.04088 | 2024-01-08 | paper | skim |
| S84 | Eliseev and Mazur, MoE offloading, arXiv 2312.17238 | https://arxiv.org/abs/2312.17238 | 2023-12-28 | paper | skim |
| S85 | MoE-Infinity, arXiv 2401.14361 | https://arxiv.org/abs/2401.14361 | 2024-01-25 (v3) | paper | skim |
| S86 | Cacheable-by-Design, arXiv 2608.18261 | https://arxiv.org/abs/2608.18261 | 2026-08-18 | paper | skim; round 2: abstract and Table 2 text read |
| S87 | LMSYS, SGLang SSD Expert Pack | https://www.lmsys.org/blog/2026-08-29-sglang-ssd-expert-pack | 2026-08-29 | maintainer benchmark | skim; round 2: WebFetch (models, hit-rate definition) |
| S88 | MawForge, arXiv 2607.09686 | https://arxiv.org/abs/2607.09686 | 2026-06-17 | paper | skim; round 2: abstract read |
| S89 | oMLX benchmark, gpt-oss-120b on M5 Max 128 GB | https://omlx.ai/benchmarks/d8dnhh1k | 2026-04-05 | community report | full (sweep 5) |
| S90 | DeepSeek-V3 technical report, arXiv 2412.19437 (MTP acceptance) | https://arxiv.org/abs/2412.19437 | 2024-12-27 | paper | skim |
| S91 | SpecFit, arXiv 2610.15417 | https://arxiv.org/abs/2610.15417 | 2026-10-11 | paper | skim; round 2: results text read |
| S92 | AcceptMoE, arXiv 2608.02989; DraftExpert; BigMoMo; Kimi EAGLE-3 drafts (NVIDIA, AQ-MedAI); vLLM K3 blog | https://arxiv.org/abs/2608.02989 ; https://huggingface.co/nvidia/Kimi-K2.5-Thinking-Eagle3 ; https://huggingface.co/AQ-MedAI/Kimi-K2.7-Code-eagle3 ; https://vllm.ai/blog/2026-07-27-k3 | 2026-07 to 2026-08 | paper / model cards | abstract only / search summaries; round 2: AcceptMoE abstract and results text read |
| S93 | 2023-2024 offloading systems: Pre-gated MoE, Fiddler, AdapMoE, ProMoE, HOBBIT, MoE-Lightning, SwapMoE, ExpertFlow, DAOP, MoE deployment (2410.22134, 2308.12066, 2402.07033, 2408.10284, 2411.01433, 2411.11217, 2308.15030, 2410.17954, 2501.10375, 2303.06182) | https://arxiv.org/abs/2410.22134 | 2023-2024 | paper | abstract only |
| S94 | 2025-2026 offloading follow-ups: SeqMoE, FineMoE, HybriMoE, Klotski, MoEpic, ReMoE, MoE-CORE, OD-MoE (2609.12978, 2502.05370, 2504.05897, 2502.06888, 2509.08342, 2605.27081, 2609.04895, 2412.00099, 2610.01950, 2512.03927) | https://arxiv.org/abs/2609.12978 | 2025-2026 | paper | abstract only |
| S95 | antirez/ds4: PERFORMANCE.md, README, CONTRIBUTING.md, easel fork README | https://github.com/antirez/ds4/blob/main/docs/PERFORMANCE.md ; https://github.com/antirez/ds4 ; https://github.com/antirez/ds4/blob/main/CONTRIBUTING.md ; https://github.com/easel/ds4 | 2026 (around 2026-04 to 2026-09) | maintainer benchmark / official repo | PERFORMANCE full; READMEs skim; round 2: PERFORMANCE.md re-read in full; round 3: PERFORMANCE.md (prefill chunk defaults), CONTRIBUTING.md and README read |
| S96 | stared, benching local LLMs on Apple Silicon (M5 Max 128 GB) | https://github.com/stared/benching-local-llms-on-apple-silicon | 2026-06-14 | community report | skim; round 2: README read in full |
| S97 | LM Studio bug tracker #2040 (M5 Metal 4 tensor API, gpt-oss-120b llama-bench) | https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/2040 | 2026-06-11 to 2026-08-11 | community report | full; round 2: issue body read in full |
| S98 | llama.cpp gpt-oss guide, discussion #15396 | https://github.com/ggml-org/llama.cpp/discussions/15396 | 2025-08-18 | maintainer benchmark | skim |
| S99 | exo repository | https://github.com/exo-explore/exo | undated (2026) | official repo | skim |
| S100 | dwarfstar.sh benchmarks (ds4 on 2× M5 Max over Thunderbolt 5; M3 Ultra V4 Pro) | https://dwarfstar.sh/benchmarks/ | 2026-09-17 (site build) | community report | full; round 2: WebFetch |
| S101 | rentamac, run Kimi K2 on Mac | https://rentamac.io/run-kimi-k2-on-mac/ | 2026-07-03 | other (vendor blog) | skim |
| S102 | MacStories, early Mac Studio AI benchmarks; SiliconScore M4 Max 128 GB aggregator (Reddit-sourced) | https://www.macstories.net/notes/notes-on-early-mac-studio-ai-benchmarks-with-qwen3-235b-a22b-and-qwen2-5-vl-72b/ ; https://siliconscore.com/chips/m4-max-128-gb/ | about 2025-05-20; up to 2026-04-27 | community report | full |
| S103 | Unsloth DeepSeek-R1 GGUF discussion #13 (mmap larger than RAM); llama.cpp discussion #27149 (expert re-layout) | https://huggingface.co/unsloth/DeepSeek-R1-GGUF/discussions/13 ; https://github.com/ggml-org/llama.cpp/discussions/27149 | 2025-01-29 to 01-31; 2026-08-15 to 08-19 | community report | full |
| S104 | Quesma, Qwen3.8 27B quantizations benchmarked | https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/ | 2026-08-26 | other | full |
| S105 | Artificial Analysis comparisons (V4 Flash vs Kimi K2.6; Kimi K2.6 vs gpt-oss-120b), index v4.3.2 | https://artificialanalysis.ai/models/comparisons/deepseek-v4-flash-vs-kimi-k2-6 ; https://artificialanalysis.ai/models/comparisons/kimi-k2-6-vs-gpt-oss-120b | accessed 2026-10-15 | other | skim; round 2: WebFetch (checkpoint and reasoning-setting labels) |
| S106 | Unsloth Qwen3.8-Next docs; GLM-5.3-Flash model card | https://unsloth.ai/docs/de/modelle/qwen3.8-next.md ; https://huggingface.co/zai-org/GLM-5.3-Flash | about 2026-08-26; undated | official docs / model card | skim |
| S107 | Kimi K3 secondary coverage (NYU Shanghai RITS; Pinggy) | https://rits.shanghai.nyu.edu/ai/kimi-k3-open-weights-ship-2-8t-parameters-1-4-tb-to-run/ ; https://pinggy.io/blog/self_hosting_llms_on_512gb_m5_ultra_mac_studio/ | 2026-07 to 2026-09-01 | other | abstract only |
| S108 | Weschera, DeepSeek V4 Flash Vision-Exp (ds4 Q2 file) on a 128 GB M4 Max Mac Studio with ds4 (memory accounting) | https://github.com/Weschera/DeepSeek-V4-Flash-Vision-Exp-ds4-Mac-Studio | 2026-09-02 | community report | full |
| S109 | antirez/ds4, docs/SSD_STREAMING.md ("Models Larger Than RAM", including "M5 Max measurements") | https://github.com/antirez/ds4/blob/main/docs/SSD_STREAMING.md | 2026-09-06 (commits) | maintainer benchmark | full (round 2) |
| S110 | antirez/ds4 docs: MODELS.md, METAL.md, QWEN38_FLASH_NEXT.md; download_model.sh; QA_BEFORE_RELEASES.md | https://github.com/antirez/ds4/blob/main/docs/MODELS.md ; https://github.com/antirez/ds4/blob/main/docs/METAL.md ; https://github.com/antirez/ds4/blob/main/docs/QWEN38_FLASH_NEXT.md ; https://github.com/antirez/ds4/blob/main/download_model.sh | 2026-09 (MODELS.md last changed 2026-09-15) | official repo | MODELS and METAL full; QWEN38 sections; round 3: download_model.sh file names and the QA prefill note read |
| S111 | GSQ (Gumbel-Softmax quantization), arXiv 2604.18556 | https://arxiv.org/abs/2604.18556 | 2026-04-20 | paper | sections: Kimi results (Table 3), appendices D (Table 6) and K (Table 14), runtime (Table 10), Table 13; via orx full text |
| S112 | ISTA-DASLab/Kimi-K2.6-2Bit-GSQ model card (K2.5 sibling by HF API) | https://huggingface.co/ISTA-DASLab/Kimi-K2.6-2Bit-GSQ | created 2026-05-18 | model card | full |
| S113 | Kimi K3 pruned builds: mlx-community/Kimi-K3-mlx-reap160-2bit; pipenetwork/Kimi-K3-REAP80-MLX-mxfp4-q8; prometheusAIR/Kimi-K3-REAP55-GGUF; mmnga-o/Kimi-K3-REAP50-UD-gguf; nota-ai/Kimi-K3-Nota-Global-Pruned-50; mgoin/Kimi-K3-pruned75 | https://huggingface.co/mlx-community/Kimi-K3-mlx-reap160-2bit ; https://huggingface.co/pipenetwork/Kimi-K3-REAP80-MLX-mxfp4-q8 ; https://huggingface.co/prometheusAIR/Kimi-K3-REAP55-GGUF ; https://huggingface.co/nota-ai/Kimi-K3-Nota-Global-Pruned-50 ; https://huggingface.co/mgoin/Kimi-K3-pruned75 | 2026-07-27 to 2026-08-05 | community report / maker benchmark (Nota) | mlx, Nota and mgoin cards full; pipenetwork and prometheusAIR skim; mmnga-o metadata only; round 3: mlx, Nota, mgoin, pipenetwork and prometheusAIR cards read in full |
| S114 | Ex0bit/Kimi-K2.5-PRISM-REAP-530B-A32B model card | https://huggingface.co/Ex0bit/Kimi-K2.5-PRISM-REAP-530B-A32B | 2026-02-18 | community report | skim |
| S115 | DeepSeek-V4-Flash-0731 model card and config.json; HF API metadata for DeepSeek-V4-Flash (April), -0731 and V4.1-Flash | https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731 | 2026-07-31 (card); queried 2026-10-15 | model card / official | card full; metadata full; round 3: card re-read (no parameter count) and config read (43 hidden layers, 1 MTP layer) |
| S116 | Artificial Analysis model pages: DeepSeek V4.1 Flash, GLM-5.3, GLM-5.3-Flash, Qwen3.8-Flash-Next (index v4.3.2) | https://artificialanalysis.ai/models/deepseek-v4-1-flash ; https://artificialanalysis.ai/models/glm-5-3 ; https://artificialanalysis.ai/models/glm-5-3-flash ; https://artificialanalysis.ai/models/qwen3-8-flash-next | accessed 2026-10-15 | other | skim |
| S117 | AtomicChat/dsv4-eval-artifacts: DeepSeek-V4-Flash-0731 quantization measurements (README, RESULTS and RIVALS JSONL) | https://huggingface.co/datasets/AtomicChat/dsv4-eval-artifacts | 2026-08-03 | maker benchmark | full; round 3: README and all four JSONL files re-read (48 quant rows) |
| S118 | llama.cpp PR #24162, "DeepSeek V4" | https://github.com/ggml-org/llama.cpp/pull/24162 | merged 2026-06-29 | official repo | metadata only |
| S119 | Dynamic expert pruning in fine-grained MoE LLMs ("you only need 2/3 of the chosen experts"), arXiv 2609.25809 | https://arxiv.org/abs/2609.25809 | 2026-09 | paper | sections (abstract, Table 1, section 4.1, V4 Flash table) via orx; round 3: full text (nine models in the budget sweeps) |
| S120 | Training-free halving of activated experts, arXiv 2609.04575 | https://arxiv.org/abs/2609.04575 | 2026-09-04 | paper | sections (abstract, introduction, related work) via orx; round 3: full text, including the discussion |
| S121 | ik_llama.cpp PR #239, SER (smart expert reduction) | https://github.com/ikawrakow/ik_llama.cpp/pull/239 | merged 2025-03-02 | official repo | skim |
| S122 | SGLang source on main: python/sglang/srt/eplb/expert_distribution.py; python/sglang/srt/arg_groups/fields/exec_.py | https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/eplb/expert_distribution.py | accessed 2026-10-15 | official repo | partial (recorder classes; option definition) |
| S123 | Reproducible evaluation of MoE expert caching (replay semantics, workload contamination), arXiv 2608.07911 | https://arxiv.org/abs/2608.07911 | 2026-08-04 | paper | abstract and introduction; round 3: full text via orx (Table 2) |
| S124 | vLLM docs: Docker deployment (CUDA compatibility); context parallel deployment (`-dcp`) | https://docs.vllm.ai/en/latest/deployment/docker.html ; https://docs.vllm.ai/en/latest/serving/context_parallel_deployment.html | accessed 2026-10-15 | official docs | skim |
| S125 | SGLang docs, DeepSeek V3/V3.1/R1 usage (DP attention "reduces KV-cache duplication across TP ranks") | https://docs.sglang.io/basic_usage/deepseek_v3.html | accessed 2026-10-15 | official docs | skim |
| S126 | Apple newsroom, MacBook Pro with M5 Pro and M5 Max (footnote 5, SSD test conditions) | https://www.apple.com/newsroom/2026/03/apple-introduces-macbook-pro-with-all-new-m5-pro-and-m5-max/ | 2026-03-03 | official | skim |
| S127 | Web search on 2 TB M5 Max SSD speed (PetaPixel review; a video review on capacity and NAND parallelism) | https://petapixel.com/2026/03/13/macbook-pro-with-m5-max-review-this-is-better-than-your-desktop/ | 2026-03-13 | other | search summary only |
| S128 | GGUF tensor tables read by this revision with HTTP range requests (headers only, no weights): unsloth Kimi-K2.6 UD-Q2_K_XL, Kimi-K2-Thinking UD-TQ1_0, DeepSeek-R1 UD-Q2_K_XL and UD-IQ1_S, DeepSeek-V4-Flash-0731 UD-IQ3_XXS, Qwen3-235B-A22B-Instruct-2507 UD-Q2_K_XL and UD-Q3_K_XL, GLM-4.6 UD-TQ1_0; antirez DeepSeek-V4-Flash IQ2XXS-0731, MXFP4-0731 and Vision-Exp MXFP4, GLM-5.3 IQ2_XXS, GLM-5.3-Flash Q2 and Q4_K; ggml-org gpt-oss-120b MXFP4 | https://huggingface.co (file resolve URLs) | 2026-10-15 | measurement | full; round 3: antirez V4 Flash IQ2XXS-0731 and Vision-Exp MXFP4 headers re-parsed (43 trunk blocks, no MTP tensors) |
| S129 | Local status on Kevin's Mac: `headroom status`, `df -H /`, `sysctl hw.memsize iogpu.wired_limit_mb` | local | 2026-10-15 | measurement | full |
| S130 | moxin-org/DeepSeek-V3-0324-Moxin-GGUF model card and file tree (V3-Mini-Exp) | https://huggingface.co/moxin-org/DeepSeek-V3-0324-Moxin-GGUF | 2025-10-10 to 2025-11-30 | model card | full |
| S131 | Jundot/DeepSeek-V4-Flash-oQ2.5e-mtp model card | https://huggingface.co/Jundot/DeepSeek-V4-Flash-oQ2.5e-mtp | undated | community report | not readable (HTTP 401 on 2026-10-15, re-checked in round 3); numbers come from search summaries, which disagree on the benchmark count; unverified |
| S132 | kwanhee-lee/vllm-private, the runtime named on the kwanhee checkpoint's card | https://github.com/kwanhee-lee/vllm-private | checked 2026-10-15 | official repo | HTTP 404 |
| S133 | antirez Hugging Face listings: kimi-k3-gguf, glm-5.3-gguf, glm-5.3-flash-gguf, deepseek-v4-gguf, deepseek-v4.1-flash-gguf | https://huggingface.co/antirez | 2026-07-29 to 2026-09 | official repo | full (listings) |
| S134 | Hugging Face API file sizes and metadata queried by this revision: ubergarm smol-IQ1_KT (K2-0905, K2.5, K2.6); unsloth Kimi-K2.5 UD-TQ1_0; unsloth GLM-4.6 UD-TQ1_0; unsloth DeepSeek-R1 files; antirez V4.1 Flash Q2; zai-org GLM-5.3 and GLM-4.6; moonshotai Kimi-K2-Instruct and Kimi-K2.6 | https://huggingface.co/api/models/ (per repository) | queried 2026-10-15 | official | full |
| S135 | flash-moe README (CLAUDE.md) | https://github.com/danveloper/flash-moe | about 2026-03 | official repo / community | full (round 2) |
| S136 | ds4 commit history of speed-bench/m5_max.csv ("refresh M5 Max and DGX Spark benchmarks") | https://github.com/antirez/ds4/commits/main/speed-bench/m5_max.csv | 2026-08-05 | official repo | metadata |
| S137 | Hugging Face search for pruned Kimi K2.x (2026-10-15): sombra-x/Kimi-K2.6-REAP-Solidity (MLX, 256 of 384 experts); ubicloud/Kimi-K2.5-Pruned-20B, -BF16-Pruned-20B (first 2 of 61 layers) and -Pruned-340B (first 20 layers, safetensors only), and Kimi-K2.6-Pruned-60B (layer-truncated, "intended for pipeline testing"); mradermacher/Kimi-K2.5-BF16-Pruned-20B-GGUF (static quants of the 2-layer BF16-Pruned-20B) | https://huggingface.co/sombra-x/Kimi-K2.6-REAP-Solidity ; https://huggingface.co/ubicloud/Kimi-K2.5-BF16-Pruned-20B ; https://huggingface.co/ubicloud/Kimi-K2.5-Pruned-340B ; https://huggingface.co/mradermacher/Kimi-K2.5-BF16-Pruned-20B-GGUF | 2026-03-20 to 2026-07-21 | community report | sombra-x card skim; ubicloud cards skim; mradermacher metadata only; round 3: ubicloud BF16-Pruned-20B, Pruned-20B and Pruned-340B cards and file lists, and the mradermacher card, read |
| S138 | GSQ repository README (IST-DASLab/GSQ): GGUF K-quant refinement, supported models, hardware per model | https://github.com/IST-DASLab/GSQ | accessed 2026-10-15 | official repo | full (round 3) |
| S139 | rita-aga/mlx-turboquant-moe-streaming README (Kimi-K2 4-bit, pread SSD streaming with MLX, 128 GB M3 Max) | https://github.com/rita-aga/mlx-turboquant-moe-streaming | 2026-03-26 (created) | community report | full (round 3) |
| S140 | This repository's Kimi K2.6 fetch evidence: program/evidence/2026-10-16/kimi-k26-fetch/README.md (job 1528 receipt, Hub cross-check, GPU 0 hold) | commit 90c337f5 in this repository | 2026-10-15 | measurement | full (round 3) |

---

## 7. Corrections log

Two rounds of findings, both in this folder. Round 1 is below as the second draft recorded it, with notes where round 2 superseded an entry. Round 2 follows.

### Round 1 (`verifier-findings-round1.json`; applied in the second draft)

IDs number each verifier's problems in file order:
- **CL:** claims and sources (23 findings);
- **AR:** feasibility arithmetic (20 findings);
- **NV:** novelty and feasibility of the gaps (11 findings).

Before adopting a fact a verifier introduced, I opened its source. The exceptions are marked "unverified" in the text: S127 (search summary only) and S131 (HTTP 401).

#### Claims and sources (CL)

| ID | Severity | Finding | What changed |
|---|---|---|---|
| CL-01 | blocker | ds4's M5 Max streaming measurements (2026-09-06) were missed; the dossier said none existed | Read SSD_STREAMING.md in full [S109]. Added rows S1-S3, a measured block in sections 1 and 3b, and GLM 5.3 as a streamed 700B-class model. Rewrote the short answer. Recalibrated A6 and the prefill model against these numbers (back-tests in A6 and 3b). |
| CL-02 | major | D4's size, fit and "130 GB variant" were wrong | D4 is now 113.4 GB (105.6 GiB), "No" under the default ceiling. The 130 GB scores are attributed to the unpruned mixed-precision model [S22, S130]. |
| CL-03 | major | The kwanhee vLLM fork is private, not published | Confirmed HTTP 404 [S132]. K4 and section 5 now say it is not runnable without the author. G1 no longer relies on that checkpoint. |
| CL-04 | major | "No GGUF/MLX pruned Kimi" was false for the Kimi family | Reworded. Kimi K3 builds pruned 50-82% are cited [S113] and used as prior negative evidence in G1. My own Hugging Face search found that it is also false for K2.x: there is a 33%-pruned K2.6 MLX Solidity specialist, and test-only GGUFs of a layer-truncated K2.5 [S137]. Section 3c now says no *general-purpose* pruned K2.x exists in GGUF or MLX. **Round 2 (R2-CL-11):** the GGUF is a 2-layer truncation, not 20 layers. |
| CL-05 | major | The smallest Kimi K2 file is 235 GB, not 247-249 GB | Section 1 and row K3 now give 235.1 GB (smol-IQ1_KT, ik_llama.cpp) and 239.5 GB (K2.5 UD-TQ1_0, mainline) [S134]. |
| CL-06 | major | V4 Flash checkpoints were mixed up; V4.1 Flash was missing | "0731" is named throughout. The index score of 34 is labelled "max". F2 and the host list now use the 0731 files. The Unsloth fidelity table is marked "checkpoint unconfirmed". G4 is pinned to 0731. Added row V1 (V4.1 Flash, index 39) [S115, S116]. **Round 2 (R2-CL-08):** the remaining April and Vision-Exp rows in F1 are now labelled. |
| CL-07 | major | Recommending V4.1 Flash Q2 streaming was infeasible on the dossier's own disk numbers | Replaced with the three ds4-measured files. V4.1 Flash Q2 is listed as "366 GB, no published Mac speed". |
| CL-08 | minor | SSD-LLaMA's 43% was misattributed to llama.cpp mmap | A5 and section 3b reworded. 5.85 GB/s is labelled the purpose-built floor; mmap is about 2 GB/s. **Round 2 (R2-CL-02):** 5.85-10.6 GB/s is now labelled an assumption, with a 3.4 GB/s low case; 2.82 and 1.93 are read-bandwidth ratios. |
| CL-09 | minor | H100 HBM units and KV layout | **Adopted** the unit fix (79.6 GiB per GPU, 684 GB in total) and the KV-per-runtime figures. **Rejected** its conclusion that round 1's KV risk was "about 2x too pessimistic": MLA's KV cache is copied to every GPU under TP (AR-11; vLLM docs [S124]), so the limit is per-GPU headroom and the risk is larger. |
| CL-10 | minor | S96's quant is stated, and the MLX gap was overstated | F1 now says "q2–q4 mix, 91 GB file, 103 GB in use, reasoning tokens counted". Conflict 9 gives +9% without MTP, +24% with MTP, and 0-6% on the dense model [S96]. |
| CL-11 | minor | The 25.1 t/s two-Mac figure is a link-quality line | Quoted as written, with the 19% generation penalty [S100]. |
| CL-12 | minor | 877 t/s is llama-bench with the tensor API off, not LM Studio's measured prefill | O1 and section 3a reworded [S97]. |
| CL-13 | minor | The tool-call schema accuracy cause was unsupported | Dropped "not bit width". Gives 83-100% (K2-Thinking) and 72-100% (K2-0905), and the causes the verifier names [S35]. |
| CL-14 | minor | SSD-LLaMA's 0.89 and 1.03 come from different RAM sizes | K1 and section 3b corrected [S36]. |
| CL-15 | minor | The llama.cpp LRU cache range was truncated and its scope omitted | Now 72-89%, 1.57-2.20 times, CUDA only, batches of 32 tokens or fewer, single device, not shown on Metal [S41]. |
| CL-16 | minor | MoESQ and the kwanhee checkpoint share an author | K4 and section 3c fixed: GPQA, AIME and MATH500 recoveries are from the card only [S63, S64]. |
| CL-17 | minor | GLM-4.6 active parameters and files were resolvable | GLM-4.6 TQ1_0 (84.1 GB) is listed, with 32.9B active counted from the tensor table. **Adopted with a change:** decode uses the measured 11.89 GB per token, giving 24-32 tokens/s, not the verifier's 28-37. That figure (32B × 1.89 bits) omits the spine. |
| CL-18 | minor | S86 was cited as pre-registered proof of the bandwidth model | Now cited as weak, internally inconsistent support. Its pre-registration covers a different experiment. ds4 is the calibration [S86, S109]. |
| CL-19 | minor | The REAP Qwen3-30B result was over-generalized | Section 3c narrowed: one preliminary test, uniform AWQ 2-bit, dynamic 2-bit untested [S59]. |
| CL-20 | minor | "Kimi ships at 4 bits" over-generalized | Section 1, K1 and conflict 7 now separate K2-Thinking and later (INT4) from K2-Instruct and K2-0905 (FP8, 1,029 GB). |
| CL-21 | minor | Baselines and evidence types were mixed | SpecFit (against plain decoding, Qwen3-30B-A3B), AcceptMoE (against EAGLE-3, one RTX 5090), S58 labelled "simulation", and the MawForge model named (Gemma Q8 35%, Qwen Q8 15%). Checked in each source. |
| CL-22 | info | The low end of the hit-rate bracket looked optimistic | A7 now uses 0.45-0.55 at 12-13% cached, and notes the batching penalty (78% → 64%) [S82]. **Round 2 (R2-AR-05, R2-AR-06):** today's cache share is 14%, and the bands were restated. |
| CL-23 | info | Free disk had changed | Re-measured: 203 GB free [S129]. Section 5 gives a formula with a 50 GB floor, for 203 GB and for about 441 GB. |

#### Feasibility arithmetic (AR)

| ID | Severity | Finding | What changed |
|---|---|---|---|
| AR-01 | major | Bytes per token were undercounted (spine ignored) | A3 rebuilt from tensor tables I read myself (15 files [S128]); every row recomputed. For the same files my numbers match the verifier's to within 0.01 GB, with one refinement: V4 Flash ds4 Q2 reads 9.34 GB per token, not 9.57, because its 1.99 GB MTP block is not used in ordinary decode. **Reversed in round 2 (R2-AR-01):** that block is trunk layer 42, so the verifier's 9.57 GB was right. |
| AR-02 | major | Decode efficiency e was mis-calibrated | A2: e = 0.47-0.61 at short context, falling to 0.54 at 32K and 0.45 at 64K (V4 Flash). Rows recomputed. Section 1 says 47-61%. |
| AR-03 | major | The SSD upper bound (13.6 GB/s) was optimistic | A5: 5.85-10.6 GB/s for purpose-built streamers and about 2 GB/s for mmap. Apple's 14.5 GB/s is for an 8 TB unit [S126]. 94-171 ms per GB missed. |
| AR-04 | major | The streamed decode estimates were too high | K1, K2, K3, D2, D3 and Q5 recomputed. Cache share is now net of the non-routed weights. D2 inputs: routed is 56% of active parameters and 39% of bytes; pool 215.7 GB. Q5: 7.08 MB per expert, 4.25 GB routed. Section 1: 2.5-5.8 with other work stopped, 1.4-3.0 at today's free memory. |
| AR-05 | major | The memory budget ignored running work | A7 and A10 use the 57.6 GB free measured at revision time [S129] (the verifier saw 55.0 GB). Each fit label says it assumes other work is stopped, and section 1 says what must stop. **Round 2 (R2-AR-06):** Headroom's figures are GiB; 57.6 GiB = 61.8 GB. |
| AR-06 | major | The prefill model assumed cache hits and ignored attention | Section 3b rebuilt: no hits on a cyclic scan, and attention-aware compute. A 30K prompt runs at 42-77 tokens/s with 4,096-token micro-batches (up to 91 at short context) and 8-15 with 512. **Adopted with a refinement:** the verifier's 91 holds only where compute reaches 295 tokens/s (2K context). Added the whole-prompt batch case (84-155), checked against ds4's measured prefill. **Round 2 (R2-AR-04, R2-CL-09):** 8 whole passes give 40-73; the whole-prompt case is a bound (84-185), not a documented ds4 mode; the ds4 check now shows that its cache serves prefill hits. |
| AR-07 | major | The KV allowance was too small, and A4 ignored KV reads | A9 now computes KV per token from the configs, and A4 adds the KV read. Q1, Q2, G1 and G2 give context limits and 32K speeds. |
| AR-08 | major | V4.1 Flash Q2 (365.7 GB) does not fit the disk | Same fix as CL-07. Section 5 notes it fits only if the 238 GB being freed comes on top of today's 203 GB. **Not adopted:** the verifier's alternative, V4 Flash Q4K streaming (164.6 GB), has no Mac measurement. The recommendation lists the three ds4-measured files instead. |
| AR-09 | major | D4's "103 GB" is GiB, and it does not fit | Published file 113.4 GB (105.6 GiB); "No" under the default ceiling (108.6 GiB with no context); 20-29 tokens/s. |
| AR-10 | major | The pruned-plus-streaming hit rate was overstated | A7 rule: take the hit rate from the original model's routing. Section 3e gives 2.9-7.2; K4 gives 1.1-2.4 (the verifier's 1.2-2.8 used h 0.60-0.70, above the lowered A7 bracket). |
| AR-11 | major | H100 KV arithmetic was wrong (units, layout, pooling) | Section 4 shared assumptions and section 5: 79.6 GiB per GPU, KV copied to every GPU, FP8 KV, `-dcp`. vLLM budgets carry the 2-6 times uncertainty. |
| AR-12 | major | No free-disk headroom was budgeted | 50 GB floor in section 5. With today's 203 GB no Kimi file fits; K2.6 Q2 fits only if the 238 GB is extra. |
| AR-13 | minor | A6 omitted hit-copy and per-layer sync costs | Both terms described in A6, and the flash-moe back-test reported (A6 is 25-32% optimistic there). **Partly rejected:** I did not add a fixed ~20% overhead to every estimate, because the ds4 back-tests fit without one. It is stated as a downside risk. |
| AR-14 | minor | The top-k gains were overstated | Now 26-30% (top-6) and 69-84% (top-4) across the A2/A5 parameter range. The verifier got +26% and +69% at its parameters. **Corrected in round 2 (R2-AR-03):** 28-30% and 76-87%; the lower ends came from superseded inputs. |
| AR-15 | minor | Maker sizes were GiB, not GB | D1, D2, D3 and Q5 converted using HF API sizes [S134, S135]. |
| AR-16 | minor | 128 GiB = 137.4 GB; the ratios were overstated | Conventions updated; K1 4.3 times, section 1 1.7 times, K5 1.22-1.35 times. |
| AR-17 | minor | Smaller Kimi files exist; Unsloth's "1.8-bit" is 1.92 bits | Same as CL-05. Row K3 says 1.92 bits. |
| AR-18 | minor | K6(ii) assumed 1.4 bits, which no stock format reaches | K6(ii) now uses IQ1_S (1.5625 bits): 108.4 GB, Tight to No. K6(i) now uses the measured spine. |
| AR-19 | minor | The 2-GPU llama.cpp assumption covered files up to 300 GB | Section 4 limits it to about 150 GB; the 161.9 GB reference uses 3 GPUs and the 340.5 GB Q2 uses 5. |
| AR-20 | info | ds4's 1M-context memory is 16.4 GiB, not 8.39 | A9 and F1 now say to use 16.4 GiB for long-context fits [S108]. |

#### Novelty and feasibility of the gaps (NV)

| ID | Severity | Finding | What changed |
|---|---|---|---|
| NV-01 | major | GSQ task results for Kimi K2.5 and K2.6 at about 2 bits already exist | Read the Kimi sections and the card [S111, S112]. Added row K2b, plus updates in section 3a (curve and limits), section 3c and G1's status. |
| NV-02 | major | Kimi K3 pruning evidence makes G1's general hypothesis very likely false | G1 reframed as a coding-specialist question, or a desk exit for general use. The K3 numbers go into the pre-registration as the prior [S113]. |
| NV-03 | major | G1 omitted the cost of competitive 2-bit quantizers | G1 now lists the GGUF route (a lower bound on quality) and the GSQ route (190-250 GPU-hours per configuration, from 192 H200 GPU-hours [S111]). **Partly adopted:** the Ex0bit K2.5 saliency scores are only a cross-check, not the starting point, because they come from an abliterated variant and are pickle files [S114]. |
| NV-04 | major | The vLLM K2.6 INT4 throughput was likely too high | 0.075-0.55M tokens per GPU-hour (round 1 divided by 2-6) until the pilot. FP8 KV. The G5 screen moves to GGUF or GSQ. |
| NV-05 | major | 6,000 tokens per item was too low, and the reasoning mode was not fixed | Two-tier suite with the reasoning mode pinned; 6.4-11.2M tokens per setting, based on MoESQ's measured lengths [S63]. **Not adopted:** the V4 Flash per-mode GPQA figures (71.2 / 87.4 / 88.1), which came only from a search summary. The 0731 card I read lists the reasoning levels but not those numbers [S115]. |
| NV-06 | major | G4 is partly done; the checkpoint and kernel path were not controlled | G4 is PARTLY_DONE and cites the AtomicChat ladder [S117]. Pinned to 0731. A host kernel-path check (CUDA vs CPU) replaces the Mac check. Load test in the pilot. Confirmed that PR #24162 merged on 2026-06-29 [S118]. |
| NV-07 | minor | An unverified community card reports about −8 points for V4 Flash mixed Q2 | Cited as an unverified prior (HTTP 401 confirmed) [S131], with a pre-registered consequence if the 2-bit hypothesis fails. |
| NV-08 | major | Top-k reduction is already characterized, and standard renormalization is the worst variant | G5 is PARTLY_DONE, citing S119-S121, both checked at source. Both renormalization variants are pre-registered, with the Python-patch caveat. |
| NV-09 | major | G2 is OPEN; stock SGLang has a per-token recorder; replay method matters | G2 is first and OPEN. The recorder settings were checked in SGLang's source [S122]. Event-atomic replay and diverse templates are required [S123]. Budget 13-51 GPU-hours. |
| NV-10 | minor | G3 should be conditional, and its comparators were stale | G3 runs only if G1 Stage 1 passes. Comparators updated (GLM-5.3-Flash, Qwen3.8-Flash-Next, the 0731 pin), with a desk alternative. |
| NV-11 | minor | vLLM CUDA 13 compatibility on R570; the humming-kernels decision | Both recorded in section 5 [S124, S112]. |

#### Other changes required by the revision brief

- **Section 1** was rewritten in plain words: what runs in memory, what runs by streaming (with measured speeds), and what Kimi needs.
- **The Mac is now only the target spec.** Every "on the Mac" measurement in section 4 is replaced with host-side emulation: traces replayed through cache simulators and A6, using Apple's, reviewers' and ds4's numbers, and validated against ds4's published M5 Max measurements (G2, question 2).
- **GPU 0 is held until 2026-10-21.** Sections 4 and 5 say what that blocks: K2.6 INT4 at TP8, which needs all 8 GPUs. They also say what runs before then.
- **Section 5** uses the host figures: K2.6 is downloading (595 GB; it has since arrived, R2-CL-07); 8 × 80 GB HBM with about 79.6 GiB usable per GPU; and the 1.77 TB of RAM as an option for CPU-side routing analysis.
- **Added from my own checks of the sources:**
  - GLM-5.3-Flash (index 42) has a ds4 Q2 file that fits in memory (row F3);
  - Qwen3.8-Flash-Next (index 40) has a ds4 Q2 file with 41.7 GiB resident (row F4);
  - GLM 5.3 scores 45 (row S1) [S116];
  - antirez publishes an 858.8 GB Kimi K3 GGUF, but it is not a listed ds4 target [S133].

### Round 2 (`verifier-findings-round2.json`; applied in this draft)

Two verifiers checked the second draft and filed 23 findings:
- **R2-CL:** claims and sources, 14 findings (3 major, 11 minor);
- **R2-AR:** feasibility arithmetic, 9 findings (1 major, 5 minor, 3 info).

IDs number each verifier's problems in file order. The verifiers confirmed 19 of the 23 round-1 claims fixes and 17 of the 20 round-1 arithmetic fixes; the rest reappear below (CL-04, CL-06 and CL-08 as R2-CL-11, R2-CL-08 and R2-CL-02; AR-01 and AR-14 as R2-AR-01 and R2-AR-03). Before adopting any correction I opened its source myself; the "Checked" column says what I read or recomputed.

#### Claims and sources (R2-CL)

| ID | Severity | Finding | Checked | What changed |
|---|---|---|---|---|
| R2-CL-01 | major | The K3 pruning summary ("more than 50% pruned keeps coding, loses facts") was wrong for the 80% build and rested on single prompts | pipenetwork REAP80, mlx-community reap160, Nota and mgoin cards, read in full [S113] | Section 1, K6, K7, section 3c and G1 restated: at 50%, GPQA-D falls 17-20 points while HumanEval+ holds; at 80% with native MXFP4 experts, prompts drift but the factual probe is answered; at 82% plus 2-bit it fails; coding above 50% is one prompt per build. "Keep their coding ability" removed. |
| R2-CL-02 | major | The 5.85-10.6 GB/s streamer bandwidth behind every Kimi estimate was stated as fact; 2.82× and 1.93× were called speedups | SSD-LLaMA §5.2 [S36]; flash-moe [S135] | Labelled an assumption carried over from Linux in section 1, A5 and row K2. Added the flash-moe-derived 3.4 GB/s low case: Kimi K2.6 Q2 at 1.5-2.2 tokens/s with other work stopped, 0.9-1.0 today. 2.82× and 1.93× are now read-bandwidth ratios; decode speedups (1.35-3.44× and 1.57-15.61×) are quoted separately. G2's emulator uses both bandwidths. |
| R2-CL-03 | major | GSQ was called CUDA-only, but its GGUF K-quant route runs on llama.cpp; Kimi GSQ needs a full node | GSQ §4.4, Appendix E and Tables 13-14 [S111]; GSQ README [S138] | Section 1, K2b, 3a and 3c: the published K2.6 checkpoint is CUDA-only; GSQ-in-GGUF is Metal-compatible but tested only on dense Qwen3-8B and Qwen3-4B. G1 gains route (c). The full-node requirement is stated in section 4 and G1 (after 2026-10-21). UD-IQ1_M is named as an i-quant mix at 2.4 bits, against GSQ at 2.37. |
| R2-CL-04 | minor | mgoin's base scores were omitted; "no benchmarks" contradicted other rows | mgoin and prometheusAIR cards [S113] | 95.53 → 68.23 (50%) → 34.42 (75%), calibration-free, added to section 1, 3c, K6 and G1. The limits line says benchmarks are few and come from the makers. prometheusAIR's needle test and NVMe speed added. |
| R2-CL-05 | minor | The event-atomic replay figure was inverted | 2608.07911 Table 2 and §1 [S123]; S82 full text | G2 now says sequential replay inflated the LRU miss fraction by 27.4% (Qwen3-30B-A3B, 40% resident, 8 concurrent requests), so it understates hit rates. S82 does not state its replay semantics; noted in A7 and G2. |
| R2-CL-06 | minor | A documented MLX pread streamer has run Kimi-K2 on a 128 GB Mac | rita-aga README [S139]; Simon Willison's post [S51] | Added the 0.5 tokens/s report (K2-Instruct 4-bit, 128 GB M3 Max, 7.1 GB of RAM, experimental) to section 1, K2 and 3b. Wording is now "no maintained or supported Metal streamer". S51 now says its engine and quant are not stated. |
| R2-CL-07 | minor | "Being downloaded" was stale | kimi-k26-fetch README at commit 90c337f5 [S140] | Sections 4 and 5 say K2.6 INT4 is on the host: job 1528, 595.2 GB, matched to the Hub listing file for file. |
| R2-CL-08 | minor | F1 still mixed April and Vision-Exp runs; "284B / 13B on its card" cited a card that does not state it; the recipe named no file | stared README (2026-06-14); Weschera README; April and 0731 cards; 0731 HF metadata; ds4 `download_model.sh` [S96, S108, S12, S115, S110] | S96 labelled as the April checkpoint; S108 labelled as the Vision-Exp Q2 file at 1M context; 284B / 13B cited to the April card, with my tensor count beside it; the streaming recipe names `ds4f-vision-mxfp4` and warns that `ds4f-mxfp4` is a different file of the same size. |
| R2-CL-09 | minor | ds4 does not document whole-prompt batching for the files it measured | ds4 PERFORMANCE.md, MODELS.md and QA_BEFORE_RELEASES.md [S95, S110] | The whole-prompt case is now a bound, not "ds4 style". Section 1 uses the documented 4,096-token default (about 6-12.5 minutes for 30K tokens). Conflict 10 scopes the overlap sentence to V4.1 Flash. |
| R2-CL-10 | minor | AtomicChat, S119 and S120 were misstated | AtomicChat README and all four JSONL files [S117]; 2609.25809 and 2609.04575 full text | About 48 quants, measured on 8× RTX 5090 hardware, rival files split by machine, ds4 Q2 in RIVALS-B3; the 4-5% perplexity gap is the BF16 reference's; 98.8% averages nine models. The S120 quotation was kept (see below). |
| R2-CL-11 | minor | S137's GGUF is a 2-layer truncation, not 20 layers | ubicloud and mradermacher cards and file lists [S137] | Section 3c corrected; the 20-layer variant is safetensors only. |
| R2-CL-12 | minor | The 21.7 tokens/s in A2 was uncited and treated as a GGUF | oMLX runs qsgif005, 8y9ori5i, 93kgjkbc and ez6mnyny [S46] | A2 cites S46, names the MLX build, gives 20.3-22.0 across four runs, and derives about 20 GB per token from the 439.6 GB peak and an 8-bit spine: e ≈ 0.49-0.54. The range used (0.47-0.61) is unchanged. |
| R2-CL-13 | minor | S131's numbers are unverifiable and the search summaries disagree | Card still HTTP 401; a fresh search summary | Benchmark count and the MMLU pair dropped. The 90.9 GiB file is identified as ds4's q2–q4 mix (97.6 GB), checkpoint unknown. G4's expectation is a weak prior. |
| R2-CL-14 | minor | Small citation errors | ds4 CONTRIBUTING.md; the Computerworld article; HF API listing for author=cerebras [S95, S3, S61] | The macOS kernel-bug warning cites CONTRIBUTING.md; reviewers are 12.6 (Computerworld), 12.7 (PetaPixel) and 13.6 GB/s (The Verge); "none for Kimi K2" (Cerebras has Kimi-Linear-REAP-35B); row G2 says BF16 and FP8 checkpoints. |

#### Feasibility arithmetic (R2-AR)

| ID | Severity | Finding | Checked | What changed |
|---|---|---|---|---|
| R2-AR-01 | minor | The two antirez V4 Flash rows dropped trunk layer 42, reversing a correct round-1 number | Re-parsed both headers [S128]: block_count 43, blocks 0-42, blk.42 has the same 34 tensors as blk.40 and no MTP tensors. The 0731 config has 43 hidden layers plus 1 MTP layer [S115]; MTP ships as a separate 3.81 GB file [S133] | Restored ds4 Q2 to 9.57 GB per token (pool 77.91, routed 1.83, spine 7.74) and Vision-Exp to 11.19 (147.17, 3.45, 7.74); 284.3B / 13.27B. Downstream: A2 e = 0.61 / 0.57 / 0.55 / 0.46; F1 30-39; S2 cache 63% of 147.2 GB; ds4 prefill check 13.9-25.2 s and 5.2-9.3 s; conflict 12. The back-test h stays 0.93-0.98. |
| R2-AR-02 | major | G1's build range (62.5-75% pruned, 2-2.7 bits) mostly broke its own 100 GB bound | Recomputed: size = 1,014.7B × (1 − pruned) × bits ÷ 8 + 9.34 GB | G1's build is now 75% pruned at 1.6-2.7 bits (60-95 GB), or 62.5% at 1.9 bits or fewer (85 GB at 1.6). Section 1: with experts at 2-2.7 bits, 64-74% must go. The screen-grid row notes that 4 of 12 configurations are at or under 100 GB. |
| R2-AR-03 | minor | The top-k gains mixed old and new parameters | Recomputed at e × 614 = 288-377 GB/s and B = 5.85-10.6 GB/s | +28-30% (top-6) and +76-87% (top-4) in 3e, G5 and the AR-14 note. |
| R2-AR-04 | minor | "Both fit" was false for ds4's warm appends; the whole-prompt row added times that ds4 overlaps; micro-batch passes were fractional | Recomputed | ds4 check rewritten: only the V4 Flash 8K cold prompt fits one no-hit pass plus compute, so ds4's cache serves prefill hits (or reads overlap, or run faster than 10.6 GB/s). Whole-prompt bound 84-185 (2.7-5.9 min); 4,096-token chunks, 8 passes: 40-73 (6.9-12.5 min), 45-82 with a managed cache; 512-token chunks, 59 passes: 8.2-15 (10-19 with a managed cache); mmap 18-20. Section 1 and row K2 updated. |
| R2-AR-05 | minor | The stopped-case cache omitted the KV and buffers that A7's own rule subtracts | Recomputed every stopped-case cache | One rule in A7. Stopped-case caches at short context: K2 75.2 GB (22.7%), K3 76.8 (32.1%), D2 73.6 (34.1%), D3 73.4 (56.8%), Q5 79.2 (36%), K1 61 (10.7%); K2 at 32K 71-73 GB. The 88 GB budget is explained (about ds4's plan for V4 Flash Q2 at 32K) and marked as my choice. The h bands are restated; the tokens/s ranges are unchanged (see below). |
| R2-AR-06 | minor | Headroom's "GB" are GiB | `headroom status --json` (total "128" for `hw.memsize` 137,438,953,472 bytes; a later reading of 70.4 at 55% free) | 57.6 GiB = 61.8 GB in sections 1, 2 and 5; process figures labelled GiB; today's cache 45-47 GB (14%); every reading marked as a snapshot (46.1-70.4 GiB the same day). |
| R2-AR-07 | info | G3 has 3 new configurations, not 4 | Recomputed | G3 is now about 10-139 GPU-hours and names the three. |
| R2-AR-08 | info | The flash-moe back-test hid where the error is | Recomputed | A6 reports the residual as 2.2-2.9 times A6's memory term, and gives the K2 downside case, 2.0-4.5 tokens/s. |
| R2-AR-09 | info | K1's bytes per token, the DP-attention comparison and F3's label did not follow the dossier's own rules | GLM-5.3-Flash Q2 header (11 trunk MLA layers, kv_lora_rank 512, rope dimension 0, 128-value indexer key; 34 KDA layers) | K1 reads 33.0 GB per token (range unchanged, 0.8-1.7). DP attention adds about 10.8 GB per GPU against about 11 GB free. F3 is "Yes by A10's rule" (93.4 GiB at 32K, if the cache holds the latent), with ds4's caution kept. |

#### Rejected or adjusted
- **R2-CL-10, the S120 quotation (rejected in part).** The verifier said the paper's wording is "precisely the setting we find worst on both models", not "the worst choice", and asked for a paraphrase. The full text also says the default "is the worst choice in that grid", in its discussion. I kept the quotation and made it exact.
- **R2-AR-04, managed-cache prefill (adjusted).** The verifier's 46-83 tokens/s used the second draft's 78.7 GB cache. With the corrected A7 rule at 30K context (about 72 GB) it is 45-82.
- **R2-AR-05, hit-rate brackets (adjusted).** I applied the single rule and restated every cache share, but kept the h brackets and widened their bands (10-15%, 22-26%, 32-38%, 55-60%). On K3's measured curve [S82] the corrected shares move h by 0.03 or less, inside each bracket's width, so the tokens/s ranges are unchanged. The verifier also expected the h ranges to barely move.
- **R2-AR-06, today's estimate (adjusted).** The verifier offered 1.5-3.2 tokens/s with h interpolated to 0.48-0.58. I kept 0.45-0.55 and 1.4-3.0, since the 10-15% band covers the corrected 14%.
- **R2-CL-12, Kimi's decode efficiency (adjusted as asked, with a caveat).** The 439.6 GB peak and an 8-bit spine give about 20 GB per token and e ≈ 0.49-0.54. The layout is inferred from the build's name, not read from its tensors, and A2 says so.

### Round 3 (orchestrator, after the confirmation pass)

- The confirmation pass found 22 of the 23 round-2 findings fixed and 1 partly fixed (R2-CL-14: A5's PetaPixel citation runs through S4). It also listed seven wording problems in section 1.
- I applied these:
  - "runs on this Mac" became "on a 128 GB M5 Max like this one", with the disk caveat;
  - the task data for GGUF files and for REAP-50 plus INT4 is now acknowledged;
  - the attribution of the 50% REAP row is corrected;
  - the 43-78% read-rate attribution is corrected;
  - the mmap rate is labelled an assumption;
  - an S51 report (K2.5 on a 96 GB M2 Max, no speed) is noted in the confirmation file.
- The full confirmation is in `confirmation-round3.json`.
