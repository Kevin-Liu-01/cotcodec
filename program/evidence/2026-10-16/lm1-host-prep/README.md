# LM1 host prep: a stock llama.cpp CUDA image, six GGUF candidates with receipts, and a smoke test

**Status:** infrastructure for LM1 (D125). LM1 asks: at a matched memory cap of about 128 GB,
does a 1T-class open model at about 1.8 bits beat smaller models near native precision on real
tasks? No experiment ran here, and nothing below measures quality. All model work ran on the
H100 host (`fal-h100-01`). Kevin's 128 GB Mac is only the target spec, and nothing ran on it.

**GPU use: 0.3744 physical GPU-h.** That is one smoke-test job (1582): 337 s on 4 H100s (GPUs 3-6),
within its 0.933 GPU-h cap. The image builds (1568, 1578), the fetches (1565-1567) and the receipt
verification (1579) were CPU-only Slurm jobs, at 0 GPU-h. GPU 0 (D110's LaMa job) was not
touched. Every job ran on 2026-10-16 UTC.

## Summary

- **Image.** `cotcodec-llamacpp:b11669-cu128`, image ID
  `sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848`. Its local-registry
  digest is `127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131`.
  - It is stock upstream llama.cpp release b11669 (commit `620d2225`), which is also the stable
    tag v0.7.0, with no patches.
  - Built for sm_90 on NVIDIA's CUDA 12.8.1 Ubuntu 24.04 images, pinned by digest.
  - It holds `llama-server`, `llama-cli`, `llama-bench` and `llama-perplexity`.
  - The lane runs it through a per-commit overlay that adds only the cotcodec source and
    provenance. For this run that was `sha256:db2dcbf1...`.
  - ik_llama.cpp is not included, because no candidate needs it.
- **Models.** All six were fetched anonymously through the CPU lane: 759.9 GB in all, the
  candidates (a)-(d) plus one reference.
  - Every receipt matches the Hub file for file: 19 GGUF LFS SHA-256 values and 6 README blob
    hashes.
  - A separate offline re-hash (job 1579) matched all six receipts.
  - No model was gated. No credential was used and no licence was accepted.
- **Smoke test.** All six loaded, with every layer on the 4 GPUs (`-ngl all --split-mode layer`),
  and answered.
  - Kimi K2.5 UD-TQ1_0 (239.5 GB): load 49 s, prefill 411 tok/s, decode 55.5 tok/s, peak
    51.6-64.5 GiB per GPU.
  - Every greedy output reads as coherent English on the operator's read. Only hashes are
    committed.
  - antirez's ds4 Q2 file runs in stock llama.cpp. It needed no ds4 engine and no tensor
    renaming.
- **Kimi K2.6 at a similar size** exists now. bartowski's mainline IQ1_M build is 232.4 GB and
  IQ1_S is 207.4 GB. Unsloth's smallest K2.6 file is still UD-Q2_K_XL, at 340.5 GB.
- **Main blockers for LM1:**
  - the Kimi reference needs all 8 GPUs;
  - "matched memory" must be defined, because the Kimi file is 1.9 times the cap;
  - reasoning modes and budgets must be pinned per model;
  - batched throughput has not been measured;
  - the study needs its own gauntlet.

  Details are in section 5.

## 1. The image

### Why b11669

- b11669 is the tag the Kimi-K2.6 fetch README read. Its commit, `620d2225cc436ab0b001e3200e590e3b286ef9ab`
  (2026-10-15), is also llama.cpp's stable release v0.7.0. The annotated tag `757cad02` points at
  the same commit. It is the only non-prerelease tag in the GitHub release list
  (`image/upstream-pins.json`).
- The next tag, b11671, only adds an unrelated model (Muse Spark Open). No candidate needs a newer
  build.
- It supports every candidate:
  - Kimi K2.5 loads as arch `deepseek2`;
  - DeepSeek V4 Flash 0731 loads as `deepseek4`;
  - Qwen3-235B loads as `qwen3moe`;
  - gpt-oss loads as `gpt-oss`;
  - every tensor type in the files has a CUDA kernel.
- The smoke test confirms this: all six run on the GPUs.
- **The Kimi file holds no TQ1_0 tensors.** The "UD-TQ1_0" label is Unsloth's name for a mix
  (`hub/gguf-headers.json`, all five shard headers). The ggml CUDA backend at this commit has no
  TQ1_0/TQ2_0 kernels, so this was checked before the choice was made. The shards hold IQ1_S (133
  tensors), IQ2_XXS (92), IQ3_XXS (38), IQ3_S (7), IQ4_NL (108), IQ4_XS (9), Q2_K (3), Q4_K (68),
  Q5_K (54), Q6_K (24), Q8_0 (192), F16 (3) and F32 (365).
- **ik_llama.cpp is not needed.** No candidate uses an ik-only type such as IQ*_KT or IQ*_KS.
  ubergarm's smol-IQ1_KT was not chosen.

### Build

- **Bases**, pinned by their linux/amd64 manifest digests (CUDA 12.8 is the highest the R570
  driver supports):
  - `nvidia/cuda:12.8.1-devel-ubuntu24.04` = `docker.io/nvidia/cuda@sha256:4b9ed5fa...`, local ID
    `154bd2b0...`;
  - `nvidia/cuda:12.8.1-runtime-ubuntu24.04` = `@sha256:828c4d87...`, local ID `011c9490...`.

  Both were pulled anonymously by digest inside the build job.
- **Source:** `git archive --prefix=llama.cpp/ 620d2225` (git tree `6868e0a5...`), SHA-256
  `622f13eb...`. The Dockerfile checks it with `sha256sum -c` before unpacking.
- **Flags:** upstream's own `.devops/cuda.Dockerfile` at this commit uses the same CUDA 12.8.1,
  Ubuntu 24.04 and gcc-14 stack. The build keeps its flags (`GGML_CUDA=ON GGML_NATIVE=OFF
  GGML_BACKEND_DL=ON GGML_CPU_ALL_VARIANTS=ON`) and makes three configuration choices that
  change no code:
  - `CMAKE_CUDA_ARCHITECTURES=90`;
  - no embedded web UI (`LLAMA_BUILD_UI=OFF LLAMA_USE_PREBUILT_UI=OFF`), so nothing is downloaded
    during the build;
  - the build number and commit are passed in, because the archive has no `.git`.

  The binaries report `version: 0.7.0-dev (build 11669, commit 620d2225)`. The `-dev` suffix is
  upstream's default `LLAMA_BUILD_IS_DEV=ON`.
- **Job 1568** (`infra/slurm/host-single-node/build-llamacpp-image.sbatch`): CPU only, 64 cores,
  no GRES. It refuses to start if a GPU is visible. It ran 4 min 19 s.
  - It took the Dockerfile from the `git archive` of `a3e0a495`. The build-receipt fields are
    `dockerfile_sha256 235f7f5a...` and `builder_sha256 ac8a2792...`.
  - It used host networking for apt only, because the bridge network has no DNS.
- **Checks without a GPU or network:**
  - all four tools print build 11669;
  - the binary manifest (`MANIFEST.sha256`, every shipped file) verifies;
  - `ldd` finds every library except the driver's `libcuda.so.1`, which the container toolkit
    supplies at run time;
  - python3 3.12.3 and PyYAML 6.0.1 are present for the lane.

  The receipt is `image/base/build-receipt.json`.
- **Overlay for the lane (job 1578, CPU only, 39 s):** `infra/research/Dockerfile.llamacpp-overlay`
  plus `scripts/build_llamacpp_overlay_on_h100.sh`.
  - It follows the vLLM overlay's pattern: the retained source capsule, `--pull=false
    --network=none`, the base asserted by ID, provenance and a receipt.
  - It does not hold an H100. The vLLM builder does, but nothing in this build touches a GPU.
  - Overlay `sha256:db2dcbf11a004efbe981493a637c87d2250afa3405d19cf1d097cb08ebbf290c`, from capsule
    `4c8e7f36...` of commit `982ee1e6`. Provenance PASS and the plan check PASS
    (`image/overlay/`).
- **Sizes:** the base image is 3.56 GB, the overlay 4.22 GB (it shares the base's layers), and the
  CUDA devel base 9.40 GB.

## 2. The models

All six are registered in `models/registry.yaml` with `runtime: llama.cpp`, no remote code, and
an `allow_patterns` subset of their repository. `scripts/fetch_open_model.py` now honours that
field in a full fetch, and the receipt records it. Without it, a GGUF repository would download
every quantization: 16.85 TB for the Kimi K2.5 repository and 1.54 TB for Unsloth's V4 Flash
0731 repository.

They were fetched by the GPU-less lane (`fetch-model-cpu.sbatch`, unchanged) from the `git
archive` of `a3e0a495`, as three parallel jobs, 02:39-03:23 UTC.
- About 290 MB/s in aggregate.
- Anonymous. The preflight found no Hugging Face token, and the lane passes none.
- The receipts went to the lane's model receipt root (`cotcodec-receipts/`), so any candidate can
  be a lane job's pinned model. The preflight refuses an id that already has a receipt.

| Registry id | Repository @ revision | Files | Bytes | Licence | Receipt SHA-256 | Artifact root | Job |
|---|---|---|---:|---|---|---|---|
| `kimi-k2.5-ud-tq1-0-gguf` (a) | `unsloth/Kimi-K2.5-GGUF` @ `386fed8b` | 5 GGUF + README | 239,537,678,077 | other (modified MIT, "Kimi K2.5" display clause above 100M MAU or $20M/month) | `c198cdd5...` | `03266411...` | 1565 (30 min) |
| `deepseek-v4-flash-0731-ds4-q2-gguf` (b) | `antirez/deepseek-v4-gguf` @ `f71f23d5` | 1 GGUF + README | 86,720,115,016 | MIT | `415e09ea...` | `0d60a7ac...` | 1566 (23 min) |
| `deepseek-v4-flash-0731-ud-iq3-xxs-gguf` (b) | `unsloth/DeepSeek-V4-Flash-0731-GGUF` @ `fbbb5b93` | 4 GGUF + README | 104,207,853,858 | MIT | `22ef4916...` | `c2c4ce4f...` | 1566 (11 min) |
| `qwen3-235b-a22b-instruct-2507-ud-q3-k-xl-gguf` (c) | `unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF` @ `437d6915` | 3 GGUF + README | 104,152,938,929 | Apache-2.0 | `32e64cd0...` | `78fcdc16...` | 1567 (17 min) |
| `gpt-oss-120b-mxfp4-gguf` (d) | `ggml-org/gpt-oss-120b-GGUF` @ `238abdd2` | 1 GGUF + README | 63,387,346,665 | Apache-2.0 | `dc5007aa...` | `329ede2a...` | 1567 (15 min) |
| `deepseek-v4-flash-0731-ud-q8-k-xl-gguf` (reference) | `unsloth/DeepSeek-V4-Flash-0731-GGUF` @ `fbbb5b93` | 5 GGUF + README | 161,869,621,346 | MIT | `a06fc7c2...` | `29ff486f...` | 1566 (10 min) |

Full digests are in `models/receipts/` and the registry. Every repository is `gated: false`
(`hub/hub-listings.json`). Job times include hashing every file for the receipt.

- **Cross-check** (`ops/lm1-crosscheck.py`, `models/crosscheck.json`): pass for all six.
  - Each receipt has the same paths and sizes as the Hub listing of its allowed files at the
    pinned revision.
  - Every GGUF's SHA-256 equals the Hub's LFS oid (19 files).
  - Every README's git blob SHA-1 equals the Hub's blob id (6 files).
  - The artifact roots recompute, and each receipt records its `allow_patterns`.
- **Re-verification** (job 1579, `infra/slurm/host-single-node/verify-models-cpu.sbatch`):
  `fetch_open_model.py verify` re-hashed all 759.9 GB against the receipts. It ran offline, with
  no GPU, one process per model, in 3 min 21 s, and all six matched (`models/verify/`). It also
  warmed the page cache for the smoke test.
- **(b) The ds4 Q2 file in stock llama.cpp.** ds4 is its own engine, so the file's header was
  checked against llama.cpp's `deepseek4` loader before the fetch (`hub/gguf-headers.json`):
  - arch `deepseek4` with 43 trunk blocks;
  - `nextn_predict_layers 1` but no MTP tensors, so the loader sets `n_layer_nextn = 0`;
  - every tensor name the loader requests is present, and no other tensor is (21 blocks with
    compression ratio 4, 20 with ratio 128, 2 with ratio 0, and 3 hash-routed blocks);
  - sqrt-softplus gating;
  - tokenizer pre `joyai-llm`, which llama.cpp knows.

  Unsloth's 0731 files have the same layout. The smoke test loaded the file as it is. The
  dossier's report that commenters had to rename tensors does not apply at b11669. The Unsloth
  UD-Q2_K_XL and UD-IQ2 fallbacks were therefore not fetched.
- **(c) Qwen variant.** This is Instruct-2507 (non-thinking), the variant whose tensor tables
  the dossier read. Thinking-2507 UD-Q3_K_XL (103.8 GB) also exists. LM1 must choose between them
  when it pins reasoning modes.
- **(a) Kimi K2.6 at a similar size.** It exists now (Hub listings and a shard-1 header read on
  2026-10-16):
  - bartowski `moonshotai_Kimi-K2.6-GGUF` @ `ed96b238` has IQ1_M at 232.43 GB (6 files) and IQ1_S
    at 207.40 GB. The IQ1_M shard 1 holds only mainline types (IQ1_M, IQ2_XXS, Q2_K, Q4_K,
    IQ4_NL, Q5_K, Q6_K, Q8_0);
  - Unsloth's smallest K2.6 file is still UD-Q2_K_XL, 340.48 GB;
  - ubergarm's smol-IQ1_KT (235.09 GB) needs ik_llama.cpp;
  - AesSedai's smallest is IQ2_XXS, 282.12 GB.

  None of these was fetched.

### Higher-precision references (proposed; only the first was fetched)

The free GPUs, 1-7, hold about 7 × 79.6 GiB = 557 GiB (598 GB).

| For | Reference | Size | Fits 7 GPUs? | Note |
|---|---|---:|---|---|
| V4 Flash 0731 ds4 Q2, UD-IQ3_XXS | UD-Q8_K_XL (fetched) | 161.9 GB | yes; ran on 4 | Near-lossless repack. The official 0731 safetensors (166.9 GB, vLLM at TP4) are the native check. |
| Qwen3-235B-2507 UD-Q3_K_XL | UD-Q8_K_XL, or Q8_0 | 274.3 / 249.9 GB | yes (4 GPUs) | Or Qwen's official FP8 checkpoint on vLLM. |
| gpt-oss-120b | itself (native MXFP4) | 63.4 GB | yes | No quantization step to measure. |
| Kimi K2.5 UD-TQ1_0 | moonshotai/Kimi-K2.5 native INT4 (vLLM) | about 595 GB | no | Needs all 8 GPUs (after GPU 0 frees, D110: 2026-10-21) or CPU offload of experts (host RAM 1.77 TB). Unsloth's K2.5 IQ4_XS (547.2 GB) would leave about 7 GB per GPU for KV and buffers. That is too tight to plan on, and it is not lossless. |

## 3. Smoke test (job 1582)

- **Lane:** `scripts/submit_docker_research_job.py` (manifest `smoke/smoke-982ee1e6.yaml`, dry run
  and test-only first).
  - Overlay `db2dcbf1...`.
  - Pinned model `gpt-oss-120b-mxfp4-gguf`. The lane re-hashed its whole snapshot in the
    container (`smoke/model-verification.txt`).
  - Provenance PASS. GPU prolog exclusive, with 0 foreign processes. `gpu_devices=3,4,5,6`.
- **Driver:** `scripts/run_lm1_smoke.py` with plan `experiments/lm1/lm1-host-smoke-v1.json`
  (SHA-256 `5e36ae33...`).
  - It checked each model's receipt (digest, revision, artifact root, file sizes).
  - It ran `llama-server -ngl all --split-mode layer -fit off -c 4096 -np 1 -lm none -lzm off`
    with 32 threads.
  - It sent three greedy requests per model (temperature 0, top-k 1, seed 42, no prompt cache):
    - a fixed 6,421-character passage with 1 generated token (prefill);
    - a short fixed question with 128 tokens (decode);
    - one chat turn through the model's own template (128 tokens).
  - It polled `nvidia-smi` every 0.5 s.
  - It refuses to run if physical GPU 0's UUID is visible.
- **Conditions:**
  - Submitted at 03:30:02 with D110's job holding GPU 0, and G3b's two jobs on GPUs 1-2.
  - It shared the host's CPUs and page cache with them. The files were in the page cache from
    job 1579.
  - 337 s of RunTime, 285 s of it in the driver.

| Model | GGUF (GB) | Load to ready (s) | Prefill tok/s (prompt tokens) | Decode tok/s (tokens) | Peak MiB per GPU (3 / 4 / 5 / 6) | Sum of peaks (GB) | Output SHA-256 (16) | Coherent? |
|---|---:|---:|---:|---:|---|---:|---|---|
| gpt-oss-120b MXFP4 | 63.4 | 15.6 | 2,335 (1,306) | 189.0 (128) | 17,369 / 15,665 / 15,671 / 14,603 | 66.4 | `9adaeb20c0fa664c` | yes; repeats its answer paragraph (a raw completion outside its harmony format) |
| Kimi K2.5 UD-TQ1_0 | 239.5 | 49.1 | 411 (1,317) | 55.5 (128) | 66,015 / 58,239 / 52,825 / 55,671 | 244.1 | `e3462b4c360d4553` | yes |
| V4 Flash 0731 ds4 Q2 | 86.7 | 32.6 | 960 (1,289) | 61.8 (128) | 21,741 / 21,943 / 21,987 / 20,605 | 90.5 | `d9aafa6b7d25c613` | yes |
| V4 Flash 0731 UD-IQ3_XXS | 104.2 | 26.6 | 944 (1,289) | 60.0 (128) | 26,145 / 24,803 / 28,027 / 24,567 | 108.6 | `f8ccc56b0599af41` | yes |
| Qwen3-235B-2507 UD-Q3_K_XL | 104.2 | 30.6 | 1,429 (1,326) | 60.0 (65, stopped at EOS) | 26,637 / 25,937 / 26,155 / 24,677 | 108.4 | `3a661adb8bd0e068` | yes |
| V4 Flash 0731 UD-Q8_K_XL | 161.9 | 92.7 | 1,080 (1,289) | 54.6 (128) | 39,963 / 40,165 / 40,209 / 37,645 | 165.7 | `fd1e1adb8e2ac757` | yes |

- **Every layer was on the GPUs.**
  - The driver's check of llama.cpp's "offloaded N/N layers" line came back empty, because
    `llama-server` at its default verbosity does not log the loader's lines. A later run should
    add `-lv 4`.
  - The evidence is the memory instead. Each model's per-GPU peaks sum to more than its file
    size (weights plus KV and compute buffers), with `-ngl all` and `-fit off` set, so nothing
    could be adjusted.
- **Coherence** is the operator's read of the single greedy outputs, which stay on the host. All
  six answer the question correctly in plain English. The driver's text-free statistics are in
  `smoke/lm1smoke/results.jsonl`: distinct-word ratio 0.63-0.71 and a maximum 4-gram repeat of 1,
  except gpt-oss at 0.39 and 3.
- **Chat templates:**
  - All six returned HTTP 200 through their embedded Jinja templates.
  - Kimi K2.5 spent all 128 chat tokens reasoning: empty content, `finish_reason: length`.
  - V4 Flash UD-IQ3_XXS also stopped at the length limit.
  - Qwen3 Instruct-2507 produced no reasoning.
  - gpt-oss, ds4 Q2 and Q8_K_XL reasoned, then answered.
- **Load times** come from the page cache, with `-lm none` (pinned, asynchronous uploads). They
  range from 2.7 to 4.9 GB/s, except Q8_K_XL at 1.7 GB/s, which was last in the order. They are
  single measurements under shared-host conditions.
- **Decode speeds** are one stream with layers pipelined across 4 GPUs, so one GPU is active at a
  time. They are not the host's serving throughput, and they say nothing about the Mac.

## 4. Disk

- **Host model cache:** 759,875,553,891 bytes of model files (759.9 GB). On disk the six
  snapshots take 759,875,909,647 bytes, including the hub client's `.cache` metadata, which the
  receipts exclude.
- **Images:** about 13.6 GB (CUDA devel 9.40 GB, the llama.cpp base 3.56 GB including its runtime
  layers, and the overlay's 0.66 GB on top).
- **Free on the host afterwards:** 19.68 TB of 23.44 TB (16% used).
- **Mac:** nothing downloaded except a 216 MB shallow clone of llama.cpp in the session
  scratchpad, used to read the source and make the source archive.

## 5. What blocks a matched-memory evaluation

1. **"Matched memory" needs a definition before the gauntlet.**
   - Kimi K2.5 UD-TQ1_0 is 239.5 GB, 1.9 times the 128 GB cap. On the Mac it can only stream
     from SSD, at about 2-3 tok/s (D125, Anemll). The in-memory candidates fit the cap: gpt-oss
     63.4, ds4 Q2 86.7, UD-IQ3_XXS 104.2 and Qwen Q3 104.2 GB.
   - On the host, every file sits fully on the GPUs, so the study can measure quality at the
     files' bits regardless of the Mac's memory. It must say whether the cap means "runs on a
     128 GB machine" (streaming allowed) or "file of at most 128 GB".
   - If it means the file, no Kimi build qualifies. The smallest are 207-240 GB, and G1 (a 100 GB
     Kimi) is a negative prior.
2. **The Kimi reference needs all 8 GPUs.**
   - Native INT4 K2.5 is about 595 GB. GPU 0 is held until 2026-10-21 (D110).
   - Until then, LM1 can compare Kimi's 1.9-bit file only with the other candidates, not with its
     own full-precision reference. The alternative is CPU offload of experts through llama.cpp
     or KTransformers (host RAM 1.77 TB), which would need its own image and a throughput pilot.
3. **Reasoning modes and budgets must be pinned per model.**
   - In the smoke test, Kimi K2.5 used a whole 128-token chat budget reasoning. V4 Flash has
     several reasoning-effort modes. gpt-oss has reasoning effort. The Qwen candidate is the
     non-thinking Instruct-2507.
   - Low-bit models write longer chains of thought (dossier S33, D124's G3). Token budgets and
     truncation therefore decide accuracy, and they must be reported separately.
4. **Throughput is unmeasured for evaluation.**
   - The smoke numbers are single-stream: 55-62 tok/s for the large MoEs on 4 GPUs. At that rate,
     the dossier's 6.4-11.2M generated tokens per model setting would take about 30-57 hours per
     stream.
   - A pilot of parallel slots (`-np`, continuous batching) per model is needed before GPU-hours
     can be budgeted. The dossier assumed 150-400 tok/s per instance.
5. **Kernel path.** CUDA on H100 is not Metal on the M5 Max. The dossier records a 4-5% perplexity
   gap between two CUDA GPUs on the same file. LM1 needs its planned CUDA-vs-CPU check on a subset
   (G3/G4).
6. **Gauntlet.** LM1 is a new direction over 8 GPU-hours, so it needs a research-gauntlet wave
   before any study job (D125, `.claude/rules/research-gauntlet-loop.md`).

Not blockers:
- the licences (all ungated; Kimi's modified MIT restricts only very large commercial products);
- disk (19.7 TB free);
- the image (all six candidates run).

## 6. Reproduce

Host scripts are in `ops/`, as they ran; `ops/jobs.log` has the times.
1. Register the models (commit `a3e0a495`). Stage `git archive a3e0a495` under
   `~/cotcodec-runs/stage0/lm1-host-prep/src/a3e0a495`, and the llama.cpp archive under
   `llama.cpp-src/`.
2. `lm1-fetch.sh a3e0a495 <label> <ids...>`, three times (jobs 1565-1567), then
   `lm1-capture-end.sh` for each job.
3. `lm1-build-image.sh a3e0a495` (job 1568).
4. `lm1-crosscheck.py hub/hub-listings.json <receipt root> <model root> crosscheck.json <ids>`.
5. Commit the filled plan (`982ee1e6`). Then:
   - `lm1-checkout.sh 982ee1e6...` (from a git bundle; git archive SHA-256 `57841940...` on both
     machines);
   - `lm1-overlay-build.sh 982ee1e6` (job 1578);
   - `lm1-verify.sh 982ee1e6` (job 1579);
   - `lm1-smoke-submit.sh 982ee1e6 check`, then `submit` (job 1582).
6. `lm1-stage-evidence.sh` collects the text-free records committed here.

## Files

- `image/`:
  - `upstream-pins.json`: the release, tag and commit, the source archive and the CUDA base
    digests;
  - `base/`: the build receipt, versions, binary manifest, ldd check, runtime environment,
    trimmed image config and build log;
  - `overlay/`: the overlay's build records.
- `models/`:
  - `receipts/`: the six lane receipts;
  - `crosscheck.json`;
  - `fetch/<job>/`: the lane's job receipt and summary, and the tail of each download log;
  - `verify/`: job 1579's records.
- `hub/`:
  - `hub-listings.json`: the Hub listing of each model's allowed files at its revision;
  - `gguf-headers.json`: GGUF header summaries and the ds4 loader check.
- `smoke/`:
  - the manifest, dry run and submission;
  - the lane records (`command.json`, `job.env`, `gpu-prolog.env`, `provenance-verification.txt`,
    `model-verification.txt`, `container-doctor.txt`, `termination.env`, `container.log.gz`,
    `scontrol.txt`);
  - `lm1smoke/results.jsonl` and `summary.json`: text-free rows.

  The model outputs (`completion.txt`, `chat.txt`) and the server logs stay in the run directory
  on the host.
- `ops/`: the scripts, `jobs.log`, `preflight.log`, `progress.log` and the `scontrol` records.
- `stage-SHA256SUMS.txt`: the SHA-256 of every staged file as it left the host.
- The directory carries the orchestrator's date (2026-10-16). The work ran on 2026-10-16 UTC
  (2026-10-15 US time).
