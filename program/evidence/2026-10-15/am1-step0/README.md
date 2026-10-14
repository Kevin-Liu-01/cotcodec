# AM1 Step 0 (exploratory): exact replay of the Qwen3-8B reader and the cost of exact subset tables

**EXPLORATORY.** This is Step 0 of AM1, the memory lead of the D103 sweep (D104; dossier entry 3,
`program/evidence/2026-10-14/question-sweep-memory-gpu/dossier.md`). It is not a registered
experiment: there is no preregistration, no decision rule and no confirmatory claim. Every number
below describes these requests, on one H100 of this node, with this software stack, in one
11-minute job.

- Config: `experiments/am1/memcredit-step0-v1.yaml`. Code: `harness/memcredit.py`,
  `scripts/memcredit_fetch_dataset.py`, `scripts/memcredit_prepare.py`,
  `scripts/memcredit_census.py`, `scripts/memcredit_step0.py`; tests in
  `tests/test_memcredit.py` (30 pass locally and on the host). The entry points use
  `memcredit_*` names because the lane refuses the archived memory names (dossier O7).
- GPU use: **0.1978 physical GPU-h** of the 1.5 cap: one image build (job 1393, 00:01:04) and one
  main job (1397, 00:10:48), each on 1 H100. CPU-only jobs (no GRES): fetch 1362, selftests
  1383 and 1394.

## Main takeaways (exploratory)

1. **Exact replay works on this node for the dense reader.** In vLLM 0.31.0's batch-invariant
   mode (`VLLM_BATCH_INVARIANT=1`), Qwen3-8B returned the same reply, token for token and with
   bit-identical sampled-token log-probs, in every A/A comparison: 4,096 greedy requests replayed
   in a shuffled order, after an engine restart, and on an engine configured differently (no
   prefix cache, 2,048-token prefill chunks, at most 64 sequences), each 4,096 of 4,096
   (95% Clopper-Pearson [0.9991, 1]); subsets at concurrency 8 (512 of 512), one at a time
   (96 of 96) and from a warm prefix cache (512 of 512); and 1,024 sampled requests (T 1, a
   fixed per-request seed) in a shuffled order and after a restart (1,024 of 1,024 each, [0.9964,
   1]). The dossier's Step 0 gate (zero differing replies) would pass on this sample, and its kill
   criterion 1 does not fire. Not tested: a second GPU, longer prompts, other models.
2. **The default mode is close to, but not, batch-invariant.** Replayed with the same schedule
   after a restart it repeated all 4,096 greedy replies (4,095 with identical log-prob bits). A
   shuffled order changed 3 of 4,096 replies (0.07%, [0.015%, 0.21%]); concurrency 8 changed 14 of
   512 (2.7%, [1.5%, 4.5%]); one request at a time changed 3 of 96 (3.1%, [0.6%, 8.9%]). Log-prob
   bits changed far more often (in 432 of 512 requests at concurrency 8). In the same batched pass
   the two modes gave identical tokens for all 4,096 requests (4,094 with identical bits).
3. **Throughput cost.** Batch invariance took 1.32-1.38x the default's wall time on the six
   matched batched passes (about 25% less throughput), 2.5x at concurrency 8 and 3.1x one request
   at a time. Batched passes of both modes ran at the 700 W power cap (mean 668-688 W, SM clock
   about 1.55-1.69 GHz). Engine start: 92 s cold and 38 s with a warm compile cache in
   batch-invariant mode, against 63 s and 26 s.
4. **Exact 256-subset tables are cheap.** 8 questions x 2 pool arms x 256 subsets (4,096 requests,
   mean prompt 405 tokens, 64.5% of prompt tokens served from the prefix cache, mean reply 12
   tokens) took 22.6 s in batch-invariant mode in both sessions: **2.8 GPU-s per question with
   both arms**, 1.4 GPU-s per table. At that rate a 200-question study is about **0.16 GPU-h per
   pass** of the reader, and all 416 questions a full study could take about 0.33 GPU-h. The
   dossier's 4-6 GPU-h per arm assumed 8K-token prompts at 3 requests/s; with user-turn memories
   the reader served 181 requests/s.
5. **LongMemEval-S is on the host under D1**: `xiaowu0162/longmemeval-cleaned` @
   `98d7416c24c778c2fee6e6f3006e7a073259d48f`, `longmemeval_s_cleaned.json`, 277,383,467 bytes,
   SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` (equal to the Hub's
   Git LFS oid), MIT. It stays out of the repository; only ids, counts, ranks and hashes are here.
6. **The demo exercises the pipeline but says nothing about credit-rule regret.** The crude
   containment utility used here is not usable (it scores "UCLA" wrong against "University of
   California, Los Angeles (UCLA)", and it scores "I don't know" replies that mention "fixing the
   fence" as right); the reader got the temporal-reasoning questions wrong on full pools; and the
   scorable tables have the pure
   structures under which, by the dossier's O5, LOO and Shapley already pick the optimal keep set
   (a knowledge-update gold arm determined by one memory, a multi-session gold arm that is exactly
   the AND of its two gold turns, single-memory single-session-user tables). A CPU census of all
   500 questions says 84% of the 416 that fit the design need one or two memories.
7. **Feasibility.** AM1's full study is feasible on this node, and GPU is not its constraint: at
   these memory units the folded study (both arms, a full A/A replicate of every table, AM2's
   three placebo variants) is about 1-2 GPU-h of reader time for 200 questions, well under the
   dossier's 9-14 GPU-h and D24's 8 GPU-h line (AM6's internal signals need HF forwards and were
   not costed; nor was the judge). The cost is harness work (the judge, the credit
   estimators, the placebo arms, AM6's HF-side signals) and the identification design: H2 can only
   fire if the pools produce mixed structures (redundancy against LOO, a binding budget,
   interference), which the demo's pools mostly did not.

## What ran

| Job | What | GPUs | Run time | GPU-h | Outcome |
|---|---|---:|---:|---:|---|
| 1362 | LongMemEval-S fetch (`ops/fetch-longmemeval-s-cpu.sbatch`) | 0 | about 5 s | 0 | downloaded in 3.1 s, size and SHA-256 equal to the Hub listing |
| 1383 | pre-image CPU selftest: source `a18fa56b` mounted into the G2 overlay `sha256:fabad633` | 0 | about 1 min | 0 | pass: 4,096 prompts rendered (108-940 tokens), thinking off, parsers and analysis ok |
| 1393 | cotcodec-vllm cu129 overlay build, commit `b95ac22c` | 1 | 00:01:04 | 0.0178 | COMPLETED, `sha256:51540dd50e0ec28c2cb4a77b51a70ba4767d58edf0fc6673ff1c81678210c2a3` |
| 1394 | post-build CPU selftest of the baked `b95ac22c` code | 0 | about 1 min | 0 | pass |
| 1397 | main job: five engine sessions, 24 passes, 37,136 requests, analysis | 1 | 00:10:48 | 0.1800 | COMPLETED 0:0, `reason=completed`, every session and pass complete |
| | **total** | | | **0.1978** | |

Run times are `scontrol` RunTime; for job 1397 the lane's records agree (`job.env` started_at
23:01:40Z, `termination.env` finished_at 23:12:27Z). `b95ac22c` differs from `a18fa56b` only in
the driver's signal forwarding and the nvidia-smi query; the post-build selftest checked the
baked code.

### Images, code, model, data

| Item | Identity |
|---|---|
| Image | `cotcodec-vllm` cu129 overlay `sha256:51540dd5...` (build receipt `builds/vllm-overlay-b95ac22c-job1393-build-receipt.json`): vLLM 0.31.0 (`db9527a4`), torch 2.13.0+cu129, transformers 5.17.0, Python 3.12.3; base `vllm/vllm-openai@sha256:b18abb2d...` |
| Code | git `b95ac22c64b68c1724b3669c3445d32fba0a2478`, source capsule `ddfb8533...` (`builds/source-capsule-b95ac22c.json`); the analysis was rerun on the host CPU at `e87a6c1a` (adds `analysis/tables.md`) and every JSON output is byte-identical to the in-job analysis (`jobs/1397-main/am1/in-job-analysis-sha256.txt`; the gzip of the demo rows differs only in its header timestamp) |
| Reader | `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218`, Apache-2.0, full weights fetched by G2's job 1333 (receipt `b9e3a74d...` in `cotcodec-receipts-cpu-lane`), re-verified file by file by the driver before any engine started (`fetch_open_model.py verify`, 12.1 s, exit 0) |
| Lane model | `qwen3-0.6b-base` @ `da87bfb6`, a verification placeholder: the lane requires a full receipt in `cotcodec-receipts`, where Qwen3-8B has only its metadata receipt, so the lane verified the smallest full model and the driver verified the reader. No engine loaded the placeholder |
| Pools | study artifact `3b70f56ff8191cfb54f84f6a4ed8a37405160961a9d414894c77583a8620db06` (91,434 bytes, host only: it holds LongMemEval text), built twice with the same digest by `scripts/memcredit_prepare.py` (`prepare/`); text-free summary `prepare/pools-summary.json` |
| Hardware | one NVIDIA H100 80GB HBM3, driver 570.148.08, power limit 700 W; every session ran on the same GPU |

No `--trust-remote-code`. The GPU ran vLLM, torch and transformers only; the reader's replies are
text that nothing executes (D7).

## How batch invariance is enabled in vLLM 0.31.0 (read-only, 2026-10-14)

Read at the `v0.31.0` tag, commit
[`db9527a4`](https://github.com/vllm-project/vllm/tree/db9527a46873454610df6dbedf79a36d6bf1a7f6),
the commit the image was built from. The nine source files cited below have the same SHA-256 in
the image as at the tag (`selftests/*/step0-selftest.json`, `vllm_cited_files_sha256`).

- **The switch is one environment variable**, `VLLM_BATCH_INVARIANT=1`
  ([docs/features/batch_invariance.md L44-L50](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/docs/features/batch_invariance.md#L44-L50);
  [vllm/envs.py L629-L631](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/envs.py#L629-L631)).
  The worker applies it at start-up
  ([v1/worker/gpu_worker.py L1585-L1587](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/v1/worker/gpu_worker.py#L1585-L1587)).
  The docs call the feature beta (L4) and list `Qwen/Qwen3-8B` among the tested models (L126).
  The driver set the variable only in the batch-invariant sessions' environment, and each worker
  checked `vllm.envs.VLLM_BATCH_INVARIANT` against its session before starting the engine.
- **What it changes on an H100 for a bf16 dense model**
  ([determinism/batch_invariant.py L1166-L1176](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/model_executor/determinism/batch_invariant.py#L1166-L1176)):
  - environment overrides (NCCL settings, `CUBLAS_WORKSPACE_CONFIG`, `VLLM_USE_AOT_COMPILE=0`;
    L1140-L1163), and on SM90 a 1-byte cuBLASLt workspace "the only source of batch variance is
    split-k" (L1073-L1077);
  - aten overrides for `mean.dim`, `_log_softmax`, `softmax` and `bmm` with Triton kernels
    (L1106-L1127), and TF32 off (L1173-L1176);
  - every unquantized linear layer and the LM head go through `linear_batch_invariant`, a Triton
    persistent matmul with a fixed reduction order
    ([layers/linear.py L234-L237](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/model_executor/layers/linear.py#L234-L237),
    [layers/vocab_parallel_embedding.py L78-L81](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/model_executor/layers/vocab_parallel_embedding.py#L78-L81),
    batch_invariant.py L281-L300 and L1036-L1040). The engine log confirms it: torch.compile
    traced `matmul_persistent` in every batch-invariant session;
  - FlashAttention runs with `num_splits=1` and no AOT schedule
    ([v1/attention/backends/flash_attn.py L834-L838, L868-L869, L1785](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/v1/attention/backends/flash_attn.py#L868-L869));
    both modes selected FLASH_ATTN, FlashAttention 3 (engine log);
  - prefix caching stays on with FLASH_ATTN; it is switched off only for FLASHINFER and
    TRITON_MLA
    ([layers/attention/attention.py L373-L387](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/model_executor/layers/attention/attention.py#L373-L387));
  - cascade attention is forced off (config/vllm.py L2171-L2179); it is already off by default
    in v0.31.0 (config/model.py L284), so both modes ran without it;
  - tuned matmul tiles and the "breakable CUDA graph" path apply only to shapes in the tuned
    table; on Hopper the table holds Qwen3-1.7B's shapes, and Qwen3-8B's are listed under
    `sm120` only
    ([determinism/batch_invariant_configs.py L103-L179, L408-L468](https://github.com/vllm-project/vllm/blob/db9527a46873454610df6dbedf79a36d6bf1a7f6/vllm/model_executor/determinism/batch_invariant_configs.py#L103-L179);
    config/vllm.py L798-L857). So on this node Qwen3-8B ran default tiles under torch.compile with
    piecewise and full CUDA graphs, which the engine log shows.
- **Sampling**: vLLM warns that sampling at T > 0 without a per-request seed "may not be batch
  invariant" (sampling_params.py L538-L546). Every sampled request here carried seed 44; the one
  such warning in each batch-invariant session's log came from the engine's own warm-up, before
  the engine was ready and before any request.

## Design

**Requests.** 8 LongMemEval-S questions (seed 42, two per stratum: temporal-reasoning,
multi-session, knowledge-update, single-session-user; abstention, single-session-assistant and
single-session-preference questions are left out of the demo), two pool arms each, all 256 subsets
of each 8-memory pool: 4,096 requests (`prepare/pools-summary.json`).

- Memory unit: one user turn with its session date (842 of LongMemEval-S's 896 gold turns, 94%,
  are user turns); 1,500 characters at most (one memory of 128 truncated).
- Arm `retrieved`: the BM25 top 8 user turns for the question (Okapi, k1 1.5, b 0.75; it stands in
  for the dossier's MiniLM retriever). It held every gold turn for 7 of the 8 questions and none
  for one.
- Arm `gold`: every gold user turn plus distractors drawn uniformly (seed 42, per question) from
  the question's other user turns. The two arms share only the retrieved gold turns.
- Pools are in chronological order; bit i of a mask keeps memory i. The prompt lists the kept
  memories with their dates, the question date and the question, and asks for one short sentence
  or "I don't know" (`experiments/am1/memcredit-step0-v1.yaml`, `prompt`). Qwen3-8B's own chat
  template, thinking off. Prompts are 108-940 tokens (mean 405).

**Reader.** Greedy (T 0) or sampled (T 1, top-p 1, top-k off, per-request seed 44), at most 64
new tokens, stop at `<|im_end|>`, sampled-token log-prob returned (`raw_logprobs`). Engine: bf16,
seed 42, `max_model_len` 4,096, `gpu_memory_utilization` 0.85, prefix caching on, at most 256
sequences, 8,192-token prefill chunks (except `bi-c`). Requests go through `LLMEngine.add_request`
under our own ids with streamed deltas (the G2 fix), and every pass resets the prefix cache first
except the warm-cache pass.

**Sessions** (one fresh engine each, in this order on one GPU):

| Session | Mode | Engine | Passes |
|---|---|---|---|
| `bi-a` | batch-invariant | as above | smoke (16); all 4,096 canonical; all shuffled (seed 43); 1,024 sampled canonical and shuffled; 512 at concurrency 8; 96 one at a time; 512 cold, then the same 512 from the warm prefix cache |
| `default-a` | default | as above | smoke; all canonical; all shuffled; sampled canonical and shuffled; concurrency 8; one at a time |
| `bi-b` | batch-invariant | restart of `bi-a` | smoke; all canonical; sampled canonical |
| `default-b` | default | restart of `default-a` | smoke; all canonical; sampled canonical |
| `bi-c` | batch-invariant | no prefix cache, 2,048-token chunks, at most 64 sequences | smoke; all canonical |

A reply is "identical" when its token ids and finish reason match; "identical bits" adds the
float32 bytes of every sampled-token log-prob. Each pass is compared with its mode's reference
pass for the same sampling (`bi-a` or `default-a`, all canonical or sampled canonical). Intervals
are exact 95% Clopper-Pearson over requests; requests of one question and arm share a prefix and a
pool, so they are not independent, and the cluster columns count (question, arm) tables in which
every request matched.

## Results

### A/A identity

| Mode | Sampling | Replayed as | Compared | Identical replies | Rate [95% CP] | Identical log-prob bits | Tables all identical |
|---|---|---|---:|---:|---|---:|---:|
| batch-invariant | greedy | shuffled order | 4,096 | 4,096 | 1 [0.99910, 1] | 4,096 | 16 of 16 |
| batch-invariant | greedy | engine restart | 4,096 | 4,096 | 1 [0.99910, 1] | 4,096 | 16 of 16 |
| batch-invariant | greedy | other engine (`bi-c`) | 4,096 | 4,096 | 1 [0.99910, 1] | 4,096 | 16 of 16 |
| batch-invariant | greedy | concurrency 8 | 512 | 512 | 1 [0.99282, 1] | 512 | 16 of 16 |
| batch-invariant | greedy | one at a time | 96 | 96 | 1 [0.96230, 1] | 96 | 15 of 15 |
| batch-invariant | greedy | cold then warm prefix cache | 512, 512 | 512, 512 | 1 [0.99282, 1] | 512, 512 | 16 of 16 |
| batch-invariant | greedy | three 16-request smoke passes | 48 | 48 | | 48 | |
| batch-invariant | sampled | shuffled order | 1,024 | 1,024 | 1 [0.99640, 1] | 1,024 | 16 of 16 |
| batch-invariant | sampled | engine restart | 1,024 | 1,024 | 1 [0.99640, 1] | 1,024 | 16 of 16 |
| default | greedy | shuffled order | 4,096 | 4,093 | 0.99927 [0.99786, 0.99985] | 4,045 | 13 of 16 |
| default | greedy | engine restart | 4,096 | 4,096 | 1 [0.99910, 1] | 4,095 | 16 of 16 |
| default | greedy | concurrency 8 | 512 | 498 | 0.97266 [0.95455, 0.98497] | 80 | 9 of 16 |
| default | greedy | one at a time | 96 | 93 | 0.96875 [0.91138, 0.99351] | 24 | 13 of 15 |
| default | greedy | 16-request smoke passes (each) | 16 | 14 | 0.875 [0.617, 0.984] | 4 | 7 of 9 |
| default | sampled | shuffled order | 1,024 | 1,022 | 0.99805 [0.99296, 0.99976] | 898 | 15 of 16 |
| default | sampled | engine restart | 1,024 | 1,024 | 1 [0.99640, 1] | 987 | 16 of 16 |
| cross-mode | greedy | `bi-a` vs `default-a`, all canonical | 4,096 | 4,096 | 1 [0.99910, 1] | 4,094 | 16 of 16 |
| cross-mode | sampled | `bi-a` vs `default-a`, sampled canonical | 1,024 | 1,024 | 1 [0.99640, 1] | 985 | 16 of 16 |

Every one of the 4,096 requests ran in four full batch-invariant passes (two orders, a restart,
another engine) and in subsets; no request differed in any of them, so the per-request rate of any
difference is at most 0.09% (95% upper bound, 0 of 4,096). The default mode's differing greedy
replies diverge at token 0-21 and the two sampled ones at tokens 33 and 45
(`analysis/identity.json`, `differing_examples`); every differing reply also changed its text.
One greedy reply of the 4,096 ran to the 64-token cap in the canonical pass of each mode.

Two readings, untested here: (i) the default mode's changes concentrate at small batch sizes,
which fits vLLM's own statement that split-K is the source of batch variance on Hopper
(batch_invariant.py L1073-L1075) and FlashAttention's split heuristics; (ii) at a large batch the
default kernels appear to reduce in the same order as the batch-invariant ones, since the two
modes agreed on all 4,096 replies and on the log-prob bits of 4,094. Log-prob bits are a coarse
test for confident tokens (an fp32 log-softmax of large logits is quantized near 0), so bit
identity says less than it seems where the reader is sure.

### Throughput cost

Wall time per pass (`analysis/tables.md` has every pass, with tokens/s and cache shares):

| Pass | Batch-invariant s | Default s | Ratio |
|---|---:|---:|---:|
| all 4,096, canonical (`bi-a` / `default-a`) | 22.58 | 17.05 | 1.324 |
| all 4,096, canonical (`bi-b` / `default-b`) | 22.57 | 17.16 | 1.315 |
| all 4,096, shuffled | 24.16 | 17.91 | 1.349 |
| 1,024 sampled, canonical (a) | 7.70 | 5.67 | 1.358 |
| 1,024 sampled, canonical (b) | 7.60 | 5.71 | 1.332 |
| 1,024 sampled, shuffled | 8.05 | 5.85 | 1.376 |
| 512 at concurrency 8 | 18.46 | 7.30 | 2.529 |
| 96 one at a time | 26.94 | 8.72 | 3.088 |

- Batched passes: batch-invariant 181 requests/s and about 26,000 computed prompt tokens/s
  against 240 and 34,500 (median ratio 1.34 over the six matched batched pairs). The two
  sessions of each mode agree within 1.3% on the same pass.
- The no-prefix-cache engine (`bi-c`) took 57.8 s for the same 4,096 requests (2.56x `bi-a`):
  prefix caching served 64.5% of the prompt tokens in the canonical order (63% shuffled).
- GPU power (`jobs/1397-main/am1/gpu-samples.csv`, 1 s samples): batched passes averaged
  668-688 W of the 700 W limit in both modes, SM clocks 1.55-1.69 GHz; concurrency 8 and one at a
  time ran at 1.94-1.98 GHz, 355-626 W. Both modes were power-capped where the cost is 1.3x.
- Engine start: batch-invariant 92.4 s (torch.compile 56 s) cold and 37.9 s with the compile cache
  (`bi-c`, a different shape set, 61.5 s); default 62.8 s and 26.2 s (it can load an AOT compile,
  which batch-invariant mode turns off).

### Cost of exact subset tables

| | Batch-invariant | Default |
|---|---:|---:|
| 4,096 requests (8 questions x 2 arms x 256), canonical | 22.6 s (both sessions) | 17.1 s |
| GPU-s per question, both arms (512 requests) | 2.82 | 2.13 |
| GPU-s per 256-subset table | 1.41 | 1.07 |
| 200 questions x 2 arms, one pass | 0.157 GPU-h | 0.118 GPU-h |
| all 416 questions a full study could take, one pass | 0.33 GPU-h | 0.25 GPU-h |

Engine starts add about a minute each. These numbers hold for short prompts (user-turn memories,
mean 405 tokens) and 12-token replies. Prompt tokens drive the cost: at the measured 26,000
computed prompt tokens/s, pools of 8K-token prompts without cache hits would cost about
8.8 GPU-h per 102,400 requests, roughly the dossier's 4-6 GPU-h per arm.

### Demo tables

Utility here is a crude containment check (the normalized gold answer occurs in the normalized
reply). It is not the study's utility, and it misreads several tables, so the set-function numbers
below illustrate the pipeline only (`analysis/demo-tables.json`, `analysis/tables.md`; replies in
`analysis/demo-table-rows.jsonl.gz`).

| Question | Type | Arm | Gold in pool | Distinct replies | Mean u | u(all 8) | Order >= 2 share | AND/OR baseline |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 6e984301 | temporal-reasoning | retrieved / gold | 2 / 2 | 15 / 9 | 0.012 / 0.004 | 0 / 0 | 0.94 / 0.97 | 0.33 |
| gpt4_70e84552 | temporal-reasoning | retrieved / gold | 2 / 2 | 27 / 26 | 0.055 / 0.074 | 0 / 0 | 0.84 / 0.88 | 0.33 |
| 09ba9854 | multi-session | retrieved / gold | 2 / 2 | 38 / 40 | 0.438 / 0.250 | 1 / 1 | 0.18 / 0.33 | 0.33 |
| e6041065 | multi-session | retrieved / gold | 2 / 2 | 13 / 13 | 0.449 / 0.438 | 1 / 1 | 0.17 / 0.19 | 0.33 |
| 618f13b2 | knowledge-update | retrieved / gold | 2 / 2 | 8 / 5 | 0.457 / 0.500 | 1 / 1 | 0.14 / 0.00 | 0.33 |
| 6aeb4375 | knowledge-update | retrieved / gold | 2 / 2 | 7 / 7 | 0.496 / 0.477 | 1 / 1 | 0.02 / 0.08 | 0.33 |
| 25e5aa4f | single-session-user | retrieved / gold | 0 / 1 | 1 / 2 | 0 / 0 | 0 / 0 | constant | n/a / 0 |
| 3d86fd0a | single-session-user | retrieved / gold | 1 / 1 | 3 / 2 | 0.5 / 0.5 | 1 / 1 | 0.00 / 0.00 | 0 |

- The reader answers from the memories when they hold the answer: "You met Sophia at a coffee
  shop in the city" in exactly the 128 subsets that keep the gold turn, "I don't know" in the other
  128 (3d86fd0a, gold arm). The multi-session gold arm 09ba9854 is exactly the AND of its two gold
  turns (mean 0.25, order >= 2 share 1/3, the O5 value); the knowledge-update gold arm 618f13b2 is
  exactly the indicator of one of its two gold turns (the one that gives "six"); with only the
  other gold turn the reader answers "four times", which by the session timestamps is the later
  statement.
- 25e5aa4f's gold arm answers "You completed your Bachelor's degree in Computer Science from UCLA"
  whenever the gold turn is kept, and the containment check scores it 0 against "University of
  California, Los Angeles (UCLA)". The temporal-reasoning tables are near 0 because the reader
  answers them wrongly on almost every subset, the full pools included: 6, 10 or 2 weeks where
  the answer is 3 weeks (it says "3 weeks" in 4 of 512 subsets), and "the goats' hooves first"
  where it is the fence. gpt4_70e84552's ones are replies that mention "fixing the fence" while
  answering otherwise or not at all. So these tables' high order >= 2 shares and nonzero LOO
  regrets describe a few scattered ones, not memory interactions. A judge is required.
- 216 distinct replies over the 16 tables (1-40 per table): at that rate the judge sees about 5,400
  distinct answers for 200 questions and both arms.

### Census of LongMemEval-S for the full study (CPU)

`census/census-e87a6c1a.json` (`scripts/memcredit_census.py`): every question, with the demo's
memory unit and retriever. "Eligible" means no abstention, every gold turn a user turn and at most
6 gold turns.

| Type | Questions | Eligible | Required memories (count: questions) | BM25 top-8 recall of gold turns | All / some / none in the top 8 |
|---|---:|---:|---|---:|---|
| all | 500 | 416 | 1: 123, 2: 226, 3: 37, 4: 14, 5: 10, 6: 6 | 0.739 | 294 / 74 / 48 |
| temporal-reasoning | 133 | 127 | 1: 35, 2: 73, 3: 13, 5: 3, 6: 3 | 0.763 | 92 / 16 / 19 |
| multi-session | 133 | 120 | 2: 77, 3: 19, 4: 14, 5: 7, 6: 3 | 0.609 | 60 / 46 / 14 |
| knowledge-update | 78 | 72 | 1: 2, 2: 68, 3: 2 | 0.944 | 64 / 8 / 0 |
| single-session-user | 70 | 62 | 1: 62 | 0.968 | 60 / 0 / 2 |
| single-session-preference | 30 | 30 | 1: 19, 2: 8, 3: 3 | 0.545 | 14 / 4 / 12 |
| single-session-assistant | 56 | 5 | 1: 5 | 0.8 | 4 / 0 / 1 |

With this retriever and these units the retrieved arm holds every gold turn for 71% of eligible
questions and none for 12%. That differs from the 54% of required memories never retrieved that
the dossier cites from CMP, whose memory units and retriever differ; this was not compared further.

## What Step 0 says and does not say

It says, for this node and stack:

1. Exact paired replay of a dense bf16 reader works in vLLM 0.31.0's batch-invariant mode on an
   H100 across order, batch composition, concurrency, prefix-cache state, engine restarts and an
   engine reconfiguration, greedy and seeded sampling, at a cost of about 1.3x wall time in
   batched work. The legacy memory oracles failed their same-arm A/A replay on nondeterministic
   decoding (`legacy/directions/03-memory-policy.md`, the transport results), which the dossier
   names as the gate exact-replay memory designs depend on.
2. Without batch invariance, replay under the same schedule mostly holds on this stack, but
   changing the batch composition changes 0.07%-3.1% of greedy replies. Credit estimators that call
   the reader at different concurrency than the reference table (online LOO, sampled Shapley,
   SNIPW exposures) would see spurious differences of that order in default mode.
3. Exhaustive 256-subset tables for a few hundred questions are a fraction of a GPU-hour.

It does not say:

- Anything confirmatory: 8 questions, 4,096 distinct requests, one job, one GPU, one
  10-minute window, no preregistration.
- That replay holds across GPUs. Every session ran on the same physical H100; a cross-GPU A/A is
  untested and the full study must include one if it spreads tables over GPUs.
- Anything for longer prompts (at most 940 tokens here), longer replies (at most 64 tokens),
  tensor parallelism, other models, the Qwen3-32B fallback or the GDN hybrids (which have no
  batch-invariant path in v0.31.0; dossier O3).
- Anything about credit rules, interaction spectra or regret: the utility is crude and the demo
  tiny.
- That the throughput ratio transfers: both modes were power-capped in batched passes, and the
  low-concurrency ratios (2.5-3.1x) rest on 96-512 requests.

## Problems and deviations

- The lane's model is a placeholder (`qwen3-0.6b-base`), as explained above; G2 used a model the
  job also ran.
- BM25 stands in for the dossier's MiniLM retriever, and memory units are user turns; the demo
  leaves out single-session-assistant and single-session-preference questions.
- No judge; the containment utility is crude (above).
- CPU jobs beside G2b measurements. The fetch (1362, 22:26Z, a 3 s download) ran while G2b's GPU
  job 1361 was running, and the pre-image selftest (1383, 22:42-22:43Z, 8 CPUs, about a minute of
  tokenization) ran while G2b's GPU jobs 1368, 1370, 1372 and 1374 were running. Neither used a
  GPU; their CPU, memory and network load on those measurements was not measured. The build
  (1393) and the main job (1397) were submitted with no G2b job in the queue
  (`ops/preflight.log`); G2b's CPU analysis job 1398 (no GRES) was submitted at 23:02:37Z and ran
  beside the main job.
- The in-job analysis predates `analysis/tables.md`; the committed `analysis/` is the host rerun
  at `e87a6c1a`, identical in every JSON file.

## Files

- `fetch/`: the LongMemEval-S receipt (source URL, revision, Hub listing, size, SHA-256, licence)
  and the job log.
- `prepare/`: the pools summary (no text), prepare log and digests.
- `census/`: the census of all 500 questions (ids, counts, BM25 ranks; no text).
- `builds/`: the overlay build receipt and log, the source capsule records (`file_manifest`
  omitted).
- `selftests/`: pre-image (`a18fa56b` mounted) and post-build (baked `b95ac22c`) CPU selftests.
- `manifests/`: the main job's manifest, dry run and submission.
- `jobs/1397-main/`: lane records; `am1/` with the driver summary, environment, nvidia-smi
  samples, worker logs and every pass (`sessions/<session>/<pass>.npz` token ids and log-probs,
  `.json` metadata, `.texts.jsonl.gz` replies; SHA-256 in `sessions-sha256.txt`).
- `analysis/`: identity, throughput, cost, demo tables and rows, engine log lines, `tables.md`.
- `ops/`: the scripts and sbatch files run on the host, the job log and the preflight log.

Raw outputs stay on the host under `~/cotcodec-runs/stage0/am1-step0/` (run directory
`runs/main/1397/`); the study artifact and the dataset file never leave it.
