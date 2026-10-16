# lm1-matched-memory-quality-v1: the pilot for "on a 128 GB unified-memory machine, does a 1T-class open model at about 1.87 bits per weight (Kimi K2.5 UD-TQ1_0, streamed) recall facts better than the best model resident in memory, and which model should Kevin run locally?"

**Status: DRAFT. Not frozen, not admitted, no ledger row.** Drafted on 2026-10-16 by the single
owner of the LM1 gauntlet's synthesis, on branch `gauntlet/lm1-matched-memory-quality`, with the
proposal `program/proposals/2026-10-16-lm1-matched-memory-quality.md`. The blind critic, the
refute-first triad and the two reviewers have not run. Nothing in this file has touched a GPU. A
freeze follows the checklist of section 17, by an operator who did not draft this file. A material
change after the freeze is a new experiment id.

Origin: D125 named quality at matched memory (LM1) as the question that decides whether a 700B-1T
model is worth running locally; D127 prepared the host. It goes through the gauntlet because the
whole study exceeds 8 GPU-h and is a new direction. This registration covers only the pilot (guards
6.9 GPU-h plus a 1.1 GPU-h reserve, line 8.0). The full study is described in the proposal and in
section 18, and gets its own registration after this pilot answers. Host slug: `lm1mmq`, under
`~/cotcodec-runs/stage0/lm1mmq/`; the host-prep directory `~/cotcodec-runs/stage0/lm1-host-prep/` is
read, never written.

## 1. Question

1. **Primary (Q1).** In instant (non-thinking) mode, on short-answer factual recall, is Kimi K2.5
   UD-TQ1_0's accuracy at least 5 points above that of every resident arm? Or less than 5 points
   above at least one of them? The endpoint is the equal-weight mean of accuracy on
   AA-Omniscience-Public (600 items) and SimpleQA-Verified (1,000 items).
2. **V4 Flash file choice (Q2).** Is V4 Flash 0731 ds4 Q2 within 2 points of UD-IQ3_XXS on the primary
   endpoint?
3. **Domain split (Q3, secondary).** Is Kimi's difference to the best resident arm larger on SuperGPQA
   items that need no calculation than on items that do?
4. **Time-matched (Q4, conditional).** Under the LEADS reading only: does Kimi's lead survive the
   best thinking-capable resident arm in thinking mode at a 4,096-token budget?
5. **Reliability (Q5, secondary).** Is Kimi's hallucination rate higher than the best resident arm's?

## 2. What it decides and what it does not

- **It decides,** by section 7.3's table: whether streaming a 1T Kimi at about 1.87 bpw is worth its
  speed cost for factual recall on Kevin's 128 GB machine; which V4 Flash 0731 file to keep resident
  for knowledge use; whether the full study keeps Kimi arms; and whether G3 closes by dominance.
- **It supplies the full study's inputs:** measured aggregate throughput per arm on the H100 host,
  tokens per item, the measured paired variance, the grader's error rates, and whether Kimi fits on 3
  GPUs.
- **It does not decide:**
  - quality on reasoning, coding or tool use (the full study's thinking tier);
  - quality of Kimi K2.6, of Kimi at its native INT4, or at top-4 routing;
  - whether stronger resident models (Qwen3.8 27B, GLM-5.3-Flash) beat the host's resident arms;
  - Mac speed. Speeds are taken from first-party measurements or the dossier's estimates and are
    labelled; nothing runs on the Mac;
  - CUDA-to-Metal numerical transfer, which is bounded only in the full study (F5).
- **Reading.** Q1 and Q2 are confirmatory for the registered files, runtime, prompt and modes. Q3-Q5
  are secondary. Anything about the domains or models above is exploratory.

## 3. Identity and pins

| Item | Pin |
|---|---|
| Experiment id | `lm1-matched-memory-quality-v1` (this file; the config `experiments/lm1/lm1mmq-v1.yaml`, to be written) |
| Kimi (arm K) | `kimi-k2.5-ud-tq1-0-gguf`: `unsloth/Kimi-K2.5-GGUF` @ `386fed8b054275941d6a495a9a7010fbf31b560d`, 5 shards, 239,537,678,077 bytes, receipt SHA-256 `c198cdd577ebc20da713cebdd76066a9677597512fb6f24e25a287579bb32460`; modified MIT |
| V4 Flash ds4 Q2 (arm F2) | `deepseek-v4-flash-0731-ds4-q2-gguf`: `antirez/deepseek-v4-gguf` @ `f71f23d552d664e523b422157b2befbf74040380`, 86,720,115,016 bytes, receipt `415e09ea35bbbfa60c75586e91fec5299855dcfe6dcd62b5faddf46f3124a3fc`; MIT |
| V4 Flash UD-IQ3_XXS (arm F3) | `deepseek-v4-flash-0731-ud-iq3-xxs-gguf`: `unsloth/DeepSeek-V4-Flash-0731-GGUF` @ `fbbb5b93fb787c21338159b0af3318bb3f4d9768`, 104,207,853,858 bytes, receipt `22ef49169d1eaa02a438235e440a34727cfc5ff4e6fb66238ab9bec9cb04f9b3`; MIT |
| Qwen3-235B-2507 Instruct (arm Q) | `qwen3-235b-a22b-instruct-2507-ud-q3-k-xl-gguf`: `unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF` @ `437d6915c5c512869e4cf8b16b840bbe3fb172bc`, 104,152,938,929 bytes, receipt `32e64cd077c3d5c07b408fffbd67aaea93673b1d853b2c33f162b7d83f3f1357`; Apache-2.0 |
| gpt-oss-120b (arm O) | `gpt-oss-120b-mxfp4-gguf`: `ggml-org/gpt-oss-120b-GGUF` @ `238abdd290bb874b90a5da1b4549881b7d05c091`, 63,387,346,665 bytes, receipt `dc5007aa56057007c80e8a364584d41dc24980d9f9a87770614245d2e1c38f8c`; Apache-2.0 |
| Judge | `Qwen/Qwen3-32B` @ `9216db5781bf21249d130ec9da846c4624c16137` (Apache-2.0), receipt in `cotcodec-receipts` (AM1's judge) |
| Runtime (arms) | llama.cpp b11669 (`620d2225`, stock, v0.7.0) in `127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131` (image id `sha256:fb8600d9...`), through the lane's per-commit overlay built from the freeze commit |
| Runtime (judge) | vLLM 0.31.0 (`db9527a4`) in the cotcodec-vllm overlay AM1 used, `VLLM_BATCH_INVARIANT=1`, `enforce_eager=True`, bf16, engine seed 42, prefix caching on |
| Data | `ArtificialAnalysis/AA-Omniscience-Public` @ `e4883edbb9f5ccf2b2a8fdc6fb65e01a58e99849` (`AA-Omniscience_dataset_public.csv`, 600 rows), Apache-2.0; `google/simpleqa-verified` @ `0dc97e0d28d8233463e005cdc4475cc2a13ba2dc` (`simpleqa_verified.csv`, 1,000 rows), MIT; `m-a-p/SuperGPQA` @ `4430d4458112c7d4497fdcf94d7cc223313d6acf` (`SuperGPQA-all.jsonl`), ODC-BY. Fetched through the CPU lane with receipts; file SHA-256 recorded at fetch |
| Templates | Each GGUF's embedded template, except V4 Flash: one template file passed with `--chat-template-file` to F2 and F3 (Unsloth's 0731 template, SHA-256 recorded at P0), checked against DeepSeek's `encoding/encoding_dsv4.py` at `7872f01b` in `thinking_mode="chat"`. If Kimi's embedded template has no `thinking` switch (the smoke test showed it thinking by default), Moonshot's `chat_template.jinja` at `4d01dfe0` is passed with `--chat-template-file` instead (SHA-256 recorded); this choice is made at P0, before any graded output |
| Reference renderers | Moonshot `chat_template.jinja` at `4d01dfe0`; Qwen3-235B-2507 `tokenizer_config.json` template at `ac9c66cc`; `openai/gpt-oss-120b` `chat_template.jinja` at the revision recorded at P0; DeepSeek `encoding_dsv4.py` at `7872f01b`. Rendered with jinja2 or the Python encoder on the CPU |
| Harness | `harness/lm1mmq/{runner.py, grade.py, analyze.py, templates_check.py}` (to be written), with tests; SHA-256 in section 17. CPU-side code only: it sends HTTP requests to `llama-server` and vLLM on 127.0.0.1 and writes JSONL |
| Prompts | Section 5.3, committed verbatim in `experiments/lm1/lm1mmq-v1.yaml`; SHA-256 of each prompt template recorded at freeze |

## 4. Design: jobs

| Job | Where | Contents | Guard (GPU-h) |
|---|---|---|---|
| P0 | Mac or host CPU lane, no GRES | Fetch the three datasets with receipts. Draw the item order (5.2). Template fidelity on 20 fixed conversations (7.1 G3). Write and test the runner, grader client, analysis script and deterministic grader. Render the manifests; dry runs and test-only runs | 0 |
| P1-K | 3 GPUs among 1-7 (4 only under K4) | Kimi, instant mode, items in order. Placement attempts in this fixed order, each logged: **K3**: 3 GPUs, `-ngl all -sm layer -fit on -fitt 1024 -fitc 24576 -np 8 -c 24576 -no-kvu`; **K3+**: the same with `--n-cpu-moe k` for k = 2, then 4, then 6, threads and memory bound to the GPUs' NUMA node, `-np 16 -c 49152`; **K4**: 4 GPUs as K3 with `-np 16`, only if transcreate holds 3 GPUs or fewer at that moment; otherwise **Kw**: wait until after 2026-10-20 and run K4. The first attempt that loads and passes the preflight is used for the whole arm | 3.3 (3 × 66 min) |
| P1-F2 | 2 GPUs | V4 Flash ds4 Q2, non-thinking | 0.9 (2 × 27 min) |
| P1-F3 | 2 GPUs | V4 Flash UD-IQ3_XXS, non-thinking | 0.9 |
| P1-Q | 2 GPUs | Qwen3-235B-2507 Instruct UD-Q3_K_XL | 0.9 |
| P1-O | 1 GPU | gpt-oss-120b, reasoning effort low | 0.6 (1 × 36 min) |
| J | 1 GPU | Grade P1's primary responses (and P2's) with the judge (section 8) | 0.3 |
| T (reserve) | as the arm | Top-up for any arm with fewer than 1,000 primary items completed: a fresh job resuming at the next item; it first re-runs the last 20 completed items (resume test, 9.4) | from the reserve |
| P2 (reserve, conditional) | 2 GPUs | Only if section 7.3's LEADS conditions hold on P1: the best thinking-capable resident arm (6.4) in thinking mode, 600 AA-Omniscience items, seed 42, `--reasoning-budget 4096` with the budget message "Time is up. Give your final answer now." | 0.7 (2 × 21 min) |

- **Every P1 server:** `llama-server --jinja -sm layer -ngl all -fa on -ctk f16 -ctv f16 -b 4096 -ub 512
  --host 127.0.0.1 --metrics -lv 4 -no-kvu`, per-slot context 3,072 tokens; resident arms `-np 16 -c
  49152`. Before items, a 3-minute `llama-batched-bench -npp 256 -ntg 64 -npl 1,8,16` preflight
  records aggregate throughput.
- **Requests.** The three seeds of an item are sent consecutively to one slot (`id_slot`) with
  `cache_prompt: true`, so the prompt is prefilled once.
- **Order and concurrency.** At most 3 GPUs at once, never GPU 0, never while a frozen registration of
  this program is queued or running. Suggested schedule: P1-O with P1-F2; P1-F3 with J (once enough
  responses exist); P1-Q; P1-K alone; then the reserve. Any job is cut so that the pilot's total stays
  at or below 8.0 GPU-h.
- **No downloads.** Every model is on the host with receipts (D127). The datasets total under 40 MB.

## 5. Items, prompts, modes and sampling

### 5.1 Task suite

| Block | Source | Items | Scoring | Licence | Contamination exposure |
|---|---|---:|---|---|---|
| Primary A | AA-Omniscience-Public | 600 (100 per domain, all) | judge, AA's 4-grade template | Apache-2.0 | created 2025-11-17: after Qwen3-235B-2507 (2025-07-21) and gpt-oss's cutoff (2024-06); before Kimi K2.5 (2026-01-27) and V4 Flash 0731 (2026-07-31). Exposure would favour K, F2, F3 |
| Primary B | SimpleQA-Verified | 1,000 (all) | judge, the same template | MIT | a subset of SimpleQA (2024-10); before every release; Qwen3-235B's vendor SimpleQA rose from 12.2 to 54.3 in one revision, unexplained. Exposure would favour Q |
| Secondary | SuperGPQA | 400: 200 `is_calculation` False, 200 True | deterministic parse of the last `Answer: [A-J]` | ODC-BY | released 2025-02-20: before every release except gpt-oss's cutoff |

### 5.2 Item order

- For each block, rows are keyed by `question_id` (AA-Omniscience), `original_index` (SimpleQA-Verified)
  or `uuid` (SuperGPQA), sorted by the SHA-256 of the key, and permuted with
  `numpy.random.default_rng(42)`.
- SuperGPQA's 400: within each `is_calculation` value, a draw stratified by `discipline`
  (proportional, largest remainder), then permuted as above.
- The run order is the 1,600 primary items interleaved by benchmark in the ratio 3:5 (so any prefix
  is a near-proportional random subset), then the 400 secondary items. The order file and its
  SHA-256 are committed at P0, before any model output.

### 5.3 Prompts (one user turn; no system message; each template's default system text applies)

- **Primary (both benchmarks).** AA's answer prompt, verbatim, then the question:

  ```
  You are answering questions about {domain}, and in particular {subtopic}.
  You will be given a question, answer with JUST the answer (no explanation).
  If you do not know the answer, or you need more context or tools to answer the question,
  be clear about this - it is better that you say this than get the wrong answer.

  Question: {question}
  ```

  AA-Omniscience fills `{domain}` and `{subtopic}` from its columns. SimpleQA-Verified uses
  `domain = "general knowledge"` and `subtopic = {topic}` (its `topic` column).
- **Secondary (SuperGPQA).**

  ```
  Answer the following multiple choice question. There is only one correct answer. The last line of
  your response should be in the format 'Answer: $LETTER' (without quotes), where LETTER is one of
  A, B, C, D, E, F, G, H, I or J.

  {question}

  A) {option_1}
  ...
  J) {option_10}
  ```

### 5.4 Reasoning modes, sampling and budgets (fixed per arm)

Every request sets every sampler; llama-server's defaults (temperature 0.80, top-k 40, min-p 0.05)
are never used. Presence and repetition penalties are off for every arm. `max_tokens` is 2,048 in P1.

| Arm | Mode (how it is set) | Temperature | top-p | top-k | min-p | Source |
|---|---|---:|---:|---:|---:|---|
| K | instant: `chat_template_kwargs {"thinking": false}` | 0.6 | 0.95 | 0 (off) | 0 | Kimi K2.5 card |
| F2, F3 | non-thinking: the pinned template's switch for `thinking_mode="chat"` (name recorded at P0) | 1.0 | 1.0 | 0 | 0 | V4 Flash 0731 card |
| Q | non-thinking (the only mode) | 0.7 | 0.8 | 20 | 0 | Qwen3-235B-2507 card |
| O | `reasoning_effort: "low"` (gpt-oss cannot disable reasoning) | 1.0 | 1.0 | 0 | 0 | gpt-oss card |
| P2 arm | thinking: V4 Flash `thinking_mode="thinking"`, `reasoning_effort: "high"`; or gpt-oss `reasoning_effort: "high"`; budget 4,096 reasoning tokens, then the answer, `max_tokens` 4,608 | as the arm | as the arm | as the arm | 0 | 6.4 |

## 6. Estimands

### 6.1 Units and events

- **Response.** One (arm, item, seed). Graded CORRECT, INCORRECT, PARTIAL_ANSWER or NOT_ATTEMPTED by
  the judge on the model's final content (reasoning content stripped; for gpt-oss the final channel).
- **Intercurrent events,** each counted and reported per arm: truncation at `max_tokens`; empty final
  content; reasoning content present in an instant-mode response; template or server error after one
  retry; judge output unparseable after one re-ask.
- **Composite strategy (primary).** Every intercurrent event counts as not CORRECT.

### 6.2 Primary endpoint and contrasts

- Item score y_ai = share of the three seeds graded CORRECT. Benchmark accuracy = mean over items.
- Primary endpoint A_a = 0.5 × accuracy on AA-Omniscience-Public + 0.5 × accuracy on
  SimpleQA-Verified.
- Contrast Δ_j = A_K − A_j for resident arm j ∈ {F2, F3, Q, O}, computed on I_j, the primary items
  with all three seeds completed and graded for both K and j (pairwise intersection; a guard-cut run is
  a prefix of the random order, so I_j is a random subset).
- Strict-fit view: the same with j ∈ {F2, O} (tier R-Y).
- H2 contrast: A_F2 − A_F3 on their intersection.

### 6.3 Secondary and sensitivity estimands

- **Per benchmark:** Δ_j on each benchmark alone (for the SPLIT rule and the contamination reading).
- **Omniscience-style index:** (CORRECT − INCORRECT) ÷ N per arm, PARTIAL and NOT_ATTEMPTED counting 0.
- **Hallucination rate:** INCORRECT ÷ (INCORRECT + PARTIAL_ANSWER + NOT_ATTEMPTED).
- **Majority of three:** for resident arms, an item is correct if at least 2 of 3 seeds are CORRECT;
  compared with Kimi's seed-42 response alone (a same-machine, same-wall-clock estimand: three resident
  answers cost less Mac time than one streamed Kimi answer).
- **Principal stratum:** items on which no arm had an intercurrent event.
- **Deterministic grader:** the primary contrasts recomputed with the grader of 8.4.
- **Domain split (H3):** D_nc − D_c, where D_s = (K's SuperGPQA accuracy minus R*'s) on stratum s;
  R* is the resident arm with the highest primary point estimate (a data-dependent choice, disclosed).
- **Mac seconds per item and per correct answer (derived, labelled):** prompt tokens ÷ prefill rate +
  output tokens ÷ decode rate, with the rates of 6.5.

### 6.4 The time-matched budget (P2)

- Kimi's Mac time per short item: prefill of a 220-token prompt touches nearly every routed expert
  (1 − (1 − 8/384)^220 ≈ 0.99 per layer), so it streams about the routed pool once: 232.5 GB at
  10.6-3.4 GB/s = 22-68 s (the dossier's read-rate range); decode of 30 tokens at 2.2 tokens/s = 13.6
  s; total 36-82 s (`program/proposals/evidence/2026-10-16-lm1-matched-memory-quality/compute/caps-lm1.json`; an expert cache would shorten it).
- A resident V4 Flash Q2 decodes 1,400-3,227 tokens in that time at 39.35 tokens/s. The registered
  budget, 4,096 reasoning tokens, is above the upper end, so the comparison errs in the resident arm's
  favour, which is conservative for a claim that Kimi leads.
- The P2 arm is the thinking-capable resident arm (F2, F3 or O) with the highest primary point
  estimate. If Q is the best resident arm overall, its instant result stands as final (it has no
  thinking mode) and H5 is evaluated against the best thinking-capable arm.

### 6.5 Mac speeds used for the derived columns (not measured here)

| Arm | Decode tokens/s | Prefill tokens/s | Source |
|---|---:|---:|---|
| K (streamed) | 2.2 (top-8) | 3.2-10.6 (one pass of the routed pool per short prompt, 6.4) | Anemll fork README, first-party; prefill is this registration's arithmetic |
| F2 | 39.35 | 790 | ds4 maintainer, first-party (2K context) |
| F3 | 31-41 | not estimated | dossier estimate |
| Q | 27-35 | not estimated | dossier estimate |
| O | 105 | 1,833 | community report, first-party |

## 7. Hypotheses, gates, kill criteria and decision rules

### 7.1 Gates (before any reading is interpreted)

- **G1 assay sensitivity.** A_Q − A_O on SimpleQA-Verified ≥ +10 points with its 95% interval excluding
  0 (vendors: 54.3 and 16.8).
- **G2 judge.** Section 8.3: binary agreement with the blind hand check ≥ 0.90; the reading corrected
  for per-arm misclassification equals the uncorrected reading.
- **G3 template fidelity.** For each arm, all 20 fixed conversations render identically through
  llama.cpp's `/apply-template` and the reference renderer (section 3). For V4 Flash, the pinned
  template equals `encoding_dsv4.py` in chat mode.
- **G4 mode conformance.** At least 98% of an instant arm's responses have empty reasoning content and
  no thinking delimiters in the final content; for O, at least 98% have a parsed final channel.
- **G5 placement.** Kimi's arm records which of K3, K3+ (with k) or K4 ran, the logged layer split, and
  the "offloaded" lines; under K3+, the number of CPU-resident expert layers is part of the arm's
  identity and is reported with every Kimi number.

### 7.2 Kill criteria

- **KC1.** G1 fails: no reading; the harness is insensitive; a repair is a new experiment id.
- **KC2.** G2 fails: the judge-based reading is void; the deterministic-grader reading is reported as
  exploratory, and the full study must replace the judge.
- **KC3.** G3 or G4 fails for an arm: that arm is excluded and reported; if it is K, the pilot stops
  with no reading.
- **KC4.** Coverage: a contrast enters the decision only if |I_j| ≥ 1,000 with at least 300 items from
  each benchmark. NOT_WORTH needs one qualifying contrast; LEADS needs all four. Otherwise the
  reading is UNRESOLVED_INCOMPLETE.
- **KC5 (reported, not a stop).** K's share of degenerate responses (a 4-gram repeated more than 8
  times, or truncation at 2,048) above 10% is flagged with the reading.

### 7.3 Predictions and decision rules (fixed before data)

Intervals are stratified paired item-bootstrap percentile intervals (section 9). In points:

- **NOT_WORTH** if for at least one qualifying j, the upper end of Δ_j's 98.75% interval (Bonferroni
  over four arms) is below +5. Sub-reading **KIMI_WORSE** if that upper end is below 0.
- **LEADS** if all of:
  - for every j ∈ {F2, F3, Q, O}, the lower end of Δ_j's 95% interval is above 0 (an
    intersection-union test, no multiplicity penalty);
  - min_j Δ̂_j ≥ +5;
  - every per-benchmark point estimate Δ̂_jb > 0;
  - K's Omniscience-style index is at or above every resident arm's (no lead bought by guessing);
  - not SPLIT.
- **SPLIT** if, applying the two rules above within each benchmark alone (with that benchmark's own
  intervals), one benchmark reads NOT_WORTH and the other LEADS. SPLIT is reported as UNRESOLVED.
- **UNRESOLVED** otherwise; **UNRESOLVED_INCOMPLETE** under KC4.
- **Under LEADS, H5** decides between **LEADS** (the 95% lower end of K's seed-42 accuracy minus the P2
  arm's on AA-Omniscience-Public is above 0) and **LEADS_INSTANT_ONLY**. If P2 cannot run within the
  reserve, the reading is LEADS_PROVISIONAL and H5 moves to the full study.
- **H2 (V4 Flash file):** **Q2_SUFFICES** if the lower end of (A_F2 − A_F3)'s 95% interval is above
  −2; **Q2_WORSE** if that lower end is at or below −2 and the upper end is below 0; **INCONCLUSIVE**
  otherwise.
- **H3 (domain split):** reported as an estimate with its 95% interval; **SUPPORTED** if the interval
  lies above 0, **CONTRADICTED** if below 0, otherwise **INCONCLUSIVE** (expected; section 10).
- **H4 (reliability):** **SUPPORTED** if the 95% interval of K's hallucination rate minus R*'s lies
  above 0, **CONTRADICTED** if below 0, else **INCONCLUSIVE**.
- **The strict-fit view** (j ∈ {F2, O}, Bonferroni over two, 97.5% upper ends) is computed and
  reported next to the primary reading. If the two disagree, both are stated.

| Reading | Kevin's local model | Program consequence |
|---|---|---|
| NOT_WORTH (or KIMI_WORSE) | A resident model; for knowledge, the best resident arm; for V4 Flash, F2 under Q2_SUFFICES, otherwise F3 when other work can stop | Kimi arms leave the full study except one confirmation of K2.6 IQ1_M on the primary endpoint (232.4 GB download, Kevin's go-ahead). G3 closes by dominance (a 100 GB Kimi is more compressed than this one). G1's coding framing stays open |
| LEADS | Stream Kimi for knowledge-heavy questions (36-82 s per short answer); a resident model otherwise | Full study, LEADS branch |
| LEADS_INSTANT_ONLY or LEADS_PROVISIONAL | A resident model that thinks; Kimi optional | Full study, UNRESOLVED branch (with H5 first) |
| UNRESOLVED, SPLIT, UNRESOLVED_INCOMPLETE | Unchanged | Full study, UNRESOLVED branch; knowledge block re-sized from the measured variance for a 3-point minimum effect |

### 7.4 Desk forecast (committed before data)

P(NOT_WORTH) ≈ 0.55 (KIMI_WORSE ≈ 0.40 of the total), P(UNRESOLVED, SPLIT or incomplete) ≈ 0.30,
P(LEADS) ≈ 0.15; P(Q2_SUFFICES) ≈ 0.5. Grounds: the 1T model leads at full precision on
AA-Omniscience (K2.6 5 against V4 Flash 0731 −14); Kimi K2's vendor SimpleQA (31.0) trails
Qwen3-235B-2507's (54.3); post-training int4 cuts knowledge capacity (2404.05405); 2-2.4-bit Kimi
loses 12.7 GPQA-D points (GSQ) and 18 AgentBench KG points (UD-IQ1_M). The forecast is recorded so the
reading can be scored against it; it does not enter any rule.

## 8. Grading

### 8.1 Judge

- Qwen3-32B at `9216db57`, vLLM as in section 3, temperature 0, `max_tokens` 4, thinking off
  (`enable_thinking: false`).
- Template: AA's `OMNISCIENCE_GRADER_TEMPLATE`, verbatim from the dataset card at `e4883edb`
  (Apache-2.0), with `{question}`, `{target}` (gold answer) and `{predicted_answer}`. The letter A, B,
  C or D maps to CORRECT, INCORRECT, PARTIAL_ANSWER or NOT_ATTEMPTED. An unparseable output is
  re-asked once with `max_tokens` 16; still unparseable is INCORRECT and counted.
- The judge sees no arm identity. Requests are sent in a hash-shuffled order across arms (rng 44).
- The judge shares a family with arm Q; section 8.3's per-arm correction addresses family bias.
- SimpleQA-Verified's own autorater (GPT-4.1, Kaggle notebook) is not used; its numbers are therefore
  not comparable with published SimpleQA-Verified scores, which is disclosed.

### 8.2 Hand check

- 360 primary responses, 72 per arm, stratified by the judge's label (minimum 10 per label per arm
  where available, the rest proportional), drawn with `numpy.random.default_rng(43)`.
- Labelled by an agent blind to arm and to the judge's label (D9: agent labels unless Kevin labels),
  from a packet with only the question, the gold answer and the response.
- Agreement is computed on the binary CORRECT / not CORRECT, with Cohen's κ reported.

### 8.3 Judge gate and correction

- G2 passes if binary agreement ≥ 0.90 overall and the misclassification-corrected reading equals the
  uncorrected one.
- Correction: per arm, sensitivity and specificity of the judge against the hand labels; corrected
  accuracy by the Rogan-Gladen estimator; the decision rule re-applied to corrected accuracies with
  intervals that bootstrap the hand-check sample as well.

### 8.4 Deterministic grader (sensitivity only)

NFKC, casefold, strip punctuation, articles and whitespace. CORRECT if the normalized gold equals the
normalized prediction, or the gold is contained in a prediction of at most 3 times its length, or both
parse as numbers that agree to the gold's last significant figure. NOT_ATTEMPTED if the prediction
matches the committed abstention patterns. Otherwise INCORRECT.

### 8.5 SuperGPQA

The last line matching `Answer:\s*\(?([A-J])\)?` decides; no match is INCORRECT and counted as a parse
failure.

## 9. Analysis

1. **Bootstrap.** For each contrast, 10,000 resamples of items with replacement within each benchmark
   (strata), seed 42; the statistic is the equal-weight mean of the two benchmark mean differences;
   percentile intervals at 95% (2.5, 97.5) and 98.75% (0.625, 99.375). Seeds stay nested in items.
2. **Pairing.** Pairwise intersections I_j (6.2). The intersection sizes and the per-arm completed
   counts are reported.
3. **Assumption check.** The bootstrap interval is reported next to the normal interval from the
   paired SE; a disagreement above 0.5 points at a decision boundary is flagged.
4. **Resume equivalence.** The resume test's 20 re-run items must give at least 18 identical grades;
   the token-level match rate is reported. A 50-item `-np 1` determinism audit per arm (seed 42, two
   runs) reports bit-reproducibility. Item-level bit equality is not claimed, because CUDA kernels
   depend on batch size and prompt caching is not guaranteed to be deterministic (llama.cpp server
   README).
5. **Reporting.** Every reading with its intervals, the per-benchmark and per-domain tables,
   intercurrent-event rates by arm, tokens per item, the measured throughput, and the derived Mac
   columns.

## 10. Power and operating characteristics (simulated before any data)

`program/proposals/evidence/2026-10-16-lm1-matched-memory-quality/compute/sim_lm1.py`, output `program/proposals/evidence/2026-10-16-lm1-matched-memory-quality/compute/sim-lm1.json`; seeds 42, 43, 44; 1,000 replicates per cell per
seed. Superpopulation model: new items each replicate; item difficulty, arm-item interaction and
three Binomial seeds per item; two settings calibrated to single-sample discordance 0.26 with
prediction-noise share 0.27 ("base") and 0.33 with 0.56 ("noisy"); resident arms at the best
resident's accuracy and 3, 6 and 15 points below it; Kimi at the best resident + Δ_min on both
benchmarks; base accuracies 0.30 (AA-Omniscience) and 0.40 (SimpleQA-Verified). The simulation applies
the registered rule with the analytic paired SE instead of the bootstrap.

**base setting, 1600 primary items** (single-sample discordance 0.26, prediction-noise share 0.27; mean SE of Δ 1.04 points):

| True Δ_min (points) | P(NOT_WORTH) | P(LEADS) | P(UNRESOLVED) | of which SPLIT | 95% coverage | seed range of P(NOT_WORTH) |
|---:|---:|---:|---:|---:|---:|---|
| -15 | 1.000 | 0.000 | 0.000 | 0.000 | 0.947 | 1.000-1.000 |
| -10 | 1.000 | 0.000 | 0.000 | 0.000 | 0.949 | 1.000-1.000 |
| -5 | 1.000 | 0.000 | 0.000 | 0.000 | 0.950 | 1.000-1.000 |
| -2 | 1.000 | 0.000 | 0.000 | 0.000 | 0.951 | 1.000-1.000 |
| +0 | 0.989 | 0.000 | 0.011 | 0.000 | 0.954 | 0.986-0.992 |
| +2 | 0.649 | 0.000 | 0.351 | 0.017 | 0.955 | 0.646-0.652 |
| +5 | 0.007 | 0.495 | 0.497 | 0.005 | 0.957 | 0.006-0.009 |
| +8 | 0.000 | 0.998 | 0.002 | 0.000 | 0.956 | 0.000-0.000 |
| +12 | 0.000 | 1.000 | 0.000 | 0.000 | 0.951 | 0.000-0.000 |

**base setting, 1000 primary items** (single-sample discordance 0.26, prediction-noise share 0.27; mean SE of Δ 1.31 points):

| True Δ_min (points) | P(NOT_WORTH) | P(LEADS) | P(UNRESOLVED) | of which SPLIT | 95% coverage | seed range of P(NOT_WORTH) |
|---:|---:|---:|---:|---:|---:|---|
| -15 | 1.000 | 0.000 | 0.000 | 0.000 | 0.948 | 1.000-1.000 |
| -10 | 1.000 | 0.000 | 0.000 | 0.000 | 0.946 | 1.000-1.000 |
| -5 | 1.000 | 0.000 | 0.000 | 0.000 | 0.942 | 1.000-1.000 |
| -2 | 0.998 | 0.000 | 0.002 | 0.001 | 0.950 | 0.997-0.999 |
| +0 | 0.910 | 0.000 | 0.090 | 0.004 | 0.952 | 0.895-0.927 |
| +2 | 0.412 | 0.011 | 0.577 | 0.015 | 0.949 | 0.391-0.438 |
| +5 | 0.006 | 0.485 | 0.508 | 0.008 | 0.952 | 0.003-0.010 |
| +8 | 0.000 | 0.986 | 0.014 | 0.000 | 0.948 | 0.000-0.000 |
| +12 | 0.000 | 1.000 | 0.000 | 0.000 | 0.948 | 0.000-0.000 |

**noisy setting, 1600 primary items** (single-sample discordance 0.32, prediction-noise share 0.57; mean SE of Δ 0.93 points):

| True Δ_min (points) | P(NOT_WORTH) | P(LEADS) | P(UNRESOLVED) | of which SPLIT | 95% coverage | seed range of P(NOT_WORTH) |
|---:|---:|---:|---:|---:|---:|---|
| -15 | 1.000 | 0.000 | 0.000 | 0.000 | 0.956 | 1.000-1.000 |
| -10 | 1.000 | 0.000 | 0.000 | 0.000 | 0.953 | 1.000-1.000 |
| -5 | 1.000 | 0.000 | 0.000 | 0.000 | 0.949 | 1.000-1.000 |
| -2 | 1.000 | 0.000 | 0.000 | 0.000 | 0.955 | 1.000-1.000 |
| +0 | 0.999 | 0.000 | 0.001 | 0.000 | 0.949 | 0.999-1.000 |
| +2 | 0.762 | 0.001 | 0.237 | 0.011 | 0.950 | 0.751-0.777 |
| +5 | 0.009 | 0.496 | 0.494 | 0.010 | 0.948 | 0.005-0.015 |
| +8 | 0.000 | 0.999 | 0.001 | 0.000 | 0.956 | 0.000-0.000 |
| +12 | 0.000 | 1.000 | 0.000 | 0.000 | 0.955 | 0.000-0.000 |

**noisy setting, 1000 primary items** (single-sample discordance 0.32, prediction-noise share 0.57; mean SE of Δ 1.17 points):

| True Δ_min (points) | P(NOT_WORTH) | P(LEADS) | P(UNRESOLVED) | of which SPLIT | 95% coverage | seed range of P(NOT_WORTH) |
|---:|---:|---:|---:|---:|---:|---|
| -15 | 1.000 | 0.000 | 0.000 | 0.000 | 0.954 | 1.000-1.000 |
| -10 | 1.000 | 0.000 | 0.000 | 0.000 | 0.946 | 1.000-1.000 |
| -5 | 1.000 | 0.000 | 0.000 | 0.000 | 0.948 | 1.000-1.000 |
| -2 | 0.999 | 0.000 | 0.001 | 0.000 | 0.952 | 0.998-1.000 |
| +0 | 0.962 | 0.000 | 0.038 | 0.002 | 0.945 | 0.959-0.964 |
| +2 | 0.510 | 0.003 | 0.487 | 0.017 | 0.954 | 0.496-0.523 |
| +5 | 0.008 | 0.511 | 0.481 | 0.007 | 0.945 | 0.006-0.010 |
| +8 | 0.000 | 0.993 | 0.007 | 0.000 | 0.954 | 0.000-0.000 |
| +12 | 0.000 | 1.000 | 0.000 | 0.000 | 0.950 | 0.000-0.000 |

Reading of the tables:
- Wrong NOT_WORTH (true Δ_min = +5, at the margin): 0.6-0.9% (seed range up to 1.5%), below the
  nominal 2.5%. Wrong LEADS (true Δ_min ≤ 0): 0 in every cell; at +2 points, at most 1.1%.
- A true Δ_min of 0 or below reads NOT_WORTH in 99-100% of replicates at 1,600 items and 91-96% at
  the 1,000-item minimum; the rest are UNRESOLVED.
- At +8 points or more, LEADS in 98.6-100%.
- Between +2 and +5 the rule is deliberately undecided: a lead under the 5-point margin does not
  justify a 12-48x speed cost, so NOT_WORTH or UNRESOLVED are both acceptable outcomes there.
- The normal-approximation 95% interval covered the true Δ in 94.2-95.7% of replicates per cell; the
  registered analysis uses the bootstrap and reports both (section 9.3).
- Limits: the item model is synthetic; the real discordance, noise share and benchmark accuracies are
  measured in P1 and reported against these settings.

Analytic minimum detectable effects (80% power, two-sided 0.05) for the secondary hypotheses, at
the base setting's variance structure:
- H2 (within family, single-sample discordance about 0.12): SE about 0.8 points at 1,600 items. The
  probability of Q2_SUFFICES is about 0.69 if the true difference is 0 and about 0.23 if it is −1
  point; H2 is informative only for differences near 0 or below −3.
- H3 (interaction over 200 + 200 items): SE about 4.6 points; minimum detectable interaction about 13
  points. An INCONCLUSIVE reading is expected unless the domain effect is large.

## 11. Seeds

`[42, 43, 44]`: the three sampling seeds per request in P1 (and 42 alone in P2), the simulation seeds,
and the item order (42), the bootstrap (42), the hand-check draw (43) and the judge order (44). The
judge is greedy and batch-invariant. No unseeded randomness.

## 12. Compute plan and caps

Arithmetic in `program/proposals/evidence/2026-10-16-lm1-matched-memory-quality/compute/caps-lm1.json` (throughputs are estimates with about 3x uncertainty; the
preflight measures them):

| Job | GPUs | Guard (GPU-h) | Wall limit | Estimate (GPU-h, low-high) | Primary items done in the pessimistic case (no prompt reuse / reuse) |
|---|---:|---:|---:|---|---|
| P1-K | 3 | 3.3 | 66 min | 0.90-11.19 | 894 / 1,131 |
| P1-F2 | 2 | 0.9 | 27 min | 0.42-2.62 | 920 / 1,221 |
| P1-F3 | 2 | 0.9 | 27 min | 0.42-2.62 | 920 / 1,221 |
| P1-Q | 2 | 0.9 | 27 min | 0.39-2.45 | 1,014 / 1,274 |
| P1-O | 1 | 0.6 | 36 min | 0.30-2.06 | 575 / 608 |
| J | 1 | 0.3 | 18 min | 0.15-0.35 | n/a |
| **Unconditional** | | **6.9** | | **2.6-6.9** (capped) | |
| Reserve: T top-ups, then P2 (0.7 cap) | ≤ 3 | 1.1 | | 0.46-2.65 for P2 | |
| **Line** | | **8.0** | | | |

- The pessimistic column combines the low end of every throughput with long outputs; the expected
  case completes every arm. If an arm stops short of 1,000 primary items, the reserve tops it up
  (Kimi first); KC4 covers the rest.
- GPU-h is counted as allocated GPUs × wall time. The reviewer's lane job (0.5 GPU-h) is counted in the
  gauntlet's budget, not here.

## 13. Data and licences

- **Models** (section 3): Kimi K2.5 (modified MIT: a display clause above 100M monthly users or US$20M
  monthly revenue); V4 Flash 0731 and its GGUFs (MIT); Qwen3-235B-2507 (Apache-2.0); gpt-oss-120b
  (Apache-2.0); Qwen3-32B (Apache-2.0). All ungated.
- **Data:** AA-Omniscience-Public (Apache-2.0; AA's prompt and grader template reused verbatim with
  attribution); SimpleQA-Verified (MIT); SuperGPQA (ODC-BY; attribution; underlying sources keep their
  licences).
- **Excluded:** GPQA-Diamond (gated; accepting its terms is Kevin's) and ungated mirrors of it.
- **Repository:** item ids, hashes, grades and aggregates only. Item text, raw responses and server
  logs stay on the host.

## 14. Integrity gate (the seven AI-research failure modes)

1. **Implementation bug passing self-review.** The runner, grader client and analysis have unit tests
   on synthetic responses with known grades; the analysis is re-run by a fresh verifier from the raw
   JSONL before any reading is reported; the assay-sensitivity gate (G1) catches a harness that cannot
   see a known gap.
2. **Hallucinated citation.** Every number in the proposal has a URL and a read level; the closest
   priors were re-read in full; the bundle snapshots every URL with its HTTP status and hash.
3. **Hallucinated experimental result.** No result exists yet. The only numbers presented as computed
   are the simulation and the cap arithmetic, both committed with their scripts and seeds.
4. **Shortcut reliance.** Judge shortcuts are checked by the hand check and the per-arm correction; a
   model that guesses more cannot win LEADS on accuracy alone (the index condition); contamination is
   read through two benchmarks with opposite exposure.
5. **Bug reframed as insight.** A template or mode failure is a kill criterion (KC3), not a finding
   about the model; GSQ's GGUF template failures are the named precedent.
6. **Methodology fabrication.** Prompts, samplers, templates, item order, grader and thresholds are
   fixed and hashed before the first P1 job; any change after a model output is read is a new id.
7. **Frame-lock at an early stage.** The desk forecast is recorded; the decision rule has a branch for
   each reading, including the one the forecast disfavours; the full study's arms depend on the
   reading.

## 15. Infrastructure failures and exclusions

- A job killed by the host, a node fault or preemption is resumed by a fresh job that skips completed
  keys; its GPU time counts against the line.
- A model that fails to load under every registered placement is an exclusion (KC3 for K).
- Server errors are retried once; persistent errors are intercurrent events (6.1).
- No item is excluded after any output is read. Items whose gold answer the hand check finds wrong
  are reported and kept (the error affects every arm equally).

## 16. Reported regardless of outcome

The reading and every interval; H2-H5; the strict-fit view; per-benchmark and per-domain tables;
intercurrent-event rates; mode-conformance and template-fidelity results; the judge's agreement and
per-arm error rates; Kimi's placement (K3, K3+ with k, or K4); measured throughput per arm; tokens per
item; the derived Mac columns; the desk forecast against the reading; GPU-h per job.

## 17. Freeze checklist

- [ ] The proposal's blind critic, the triad and both reviewers have run, and their defects are
      resolved or recorded.
- [ ] `experiments/lm1/lm1mmq-v1.yaml` committed with prompts, samplers, templates and thresholds;
      SHA-256 of each prompt template recorded here.
- [ ] `harness/lm1mmq/` committed with tests; `uv run pytest -q tests/test_lm1mmq*.py` run unpiped and
      its exit code checked directly (D123).
- [ ] The three dataset receipts; the item-order file and its SHA-256.
- [ ] Template-fidelity results (G3) committed.
- [ ] Manifests rendered; dry runs and test-only runs pass for every job.
- [ ] Section 3's pins re-checked against `models/registry.yaml` and the receipts after any merge
      (D123).
- [ ] An operator who did not draft this file performs the freeze and the ledger row.

## 18. Consequences for the full study (provisional; registered separately)

- **NOT_WORTH:** the full study runs the thinking tier on resident arms only (V4 Flash Q2, IQ3_XXS,
  Q8_K_XL, gpt-oss high, Qwen3.8 27B, Qwen3-235B Thinking-2507 after a CPU-lane fetch), plus one K2.6
  IQ1_M confirmation on the primary endpoint and the CUDA-against-CPU kernel-path check: 112-249 GPU-h.
- **UNRESOLVED:** the same with K2.6 IQ1_M in the thinking tier and a re-sized knowledge block:
  138-345 GPU-h.
- **LEADS:** adds K2.6 INT4 (vLLM TP8 after GPU 0 frees), top-4 routing and H5 at full size: 174-606
  GPU-h.
- In every branch: 3-8 GPU-h of setup; the full study's caps are re-derived from P1's measured
  throughput before its registration.
