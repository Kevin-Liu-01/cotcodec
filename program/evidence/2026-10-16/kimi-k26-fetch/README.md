# Kimi-K2.6 reference checkpoint: fetch record and runtime support

**Status:** infrastructure for a new line (can a ~1T open model be compressed or restructured
to run usefully on a 128 GB machine?). No experiment ran. CPU and network only: no GPU job, 0 GPU-h.

## Summary

- `moonshotai/Kimi-K2.6` at revision `7eb5002f6aadc958aed6a9177b7ed26bb94011bb` is registered in
  `models/registry.yaml` as `kimi-k2.6` (commit `2baacac2`).
- The GPU-less fetch lane downloaded it to the host's model cache,
  `~/cotcodec-runs/hf-cache/cotcodec-models/kimi-k2.6/`, as job 1528. The job was CPU only and
  anonymous, and it ended COMPLETED 0:0 after 55 min 36 s.
  - The receipt holds 96 files and 595,204,999,341 bytes, with artifact root `68f85813...`.
  - It matches the Hub's own listing file for file, including all 67 LFS SHA-256 values.
- Every runtime checked loads Kimi-K2.6 in some form, including the program's pinned vLLM 0.31.0.
  None of them makes it fit in 128 GB as it is. The checkpoint is 595.2 GB at its native INT4.
  Kimi-K3 is supported by vLLM 0.31.0, SGLang, llama.cpp (text only) and MLX, but not by
  KTransformers v0.7.2. At 1,561 GB it cannot sit in this node's 640 GB of GPU memory.

## The checkpoint

Every fact here was read anonymously from the Hub at the pinned revision on 2026-10-15
(`hub/model-info-7eb5002f.min.json`, `hub/tree-7eb5002f.json`). Text files that were read but
not committed are listed by SHA-256 in `hub/text-files-read.sha256`.

| Field | Value |
|---|---|
| Repository | https://huggingface.co/moonshotai/Kimi-K2.6 |
| Revision | `7eb5002f6aadc958aed6a9177b7ed26bb94011bb` (last modified 2026-05-19) |
| Access | `gated: false`, `private: false`. No token, no account and no acceptance |
| Licence | Hub tag `license:other`, card `license_name: modified-mit` (see below) |
| Architecture | `KimiK25ForConditionalGeneration`, `model_type: kimi_k25`; text model `DeepseekV3ForCausalLM` (`kimi_k2`) |
| Text model | 61 layers, hidden 7,168, MLA (q LoRA rank 1,536, kv LoRA rank 512), 384 routed experts with 8 active plus 1 shared, first layer dense, vocabulary 163,840, context 262,144 (YaRN factor 64) |
| Vision | MoonViT, 27 layers, hidden 1,152; README: 400M parameters |
| Parameters | README: 1T total, 32B activated. Hub safetensors metadata: 1,026,879,376,368 (BF16 12,193,329,648) |
| Quantization | `compressed-tensors`, `pack-quantized`: INT4 weights, symmetric, group size 32, on the routed experts only. Attention, shared experts, the dense MLP, `lm_head` and vision stay BF16 |
| Files | 96 files, 595,204,999,341 bytes; 64 safetensors shards (`model-000NN-of-000064`) and a 23.6 MB index |
| Remote code | `configuration_kimi_k25.py`, `modeling_kimi_k25.py`, `configuration_deepseek.py`, `modeling_deepseek.py`, `tokenization_kimi.py`, `kimi_k25_processor.py`, `kimi_k25_vision_processing.py`, `media_utils.py`, `tool_declaration_ts.py` |

- **Licence.** `LICENSE` is a "Modified MIT License" (Moonshot AI, 2026). It is the MIT grant with
  one added clause. A commercial product or service with more than 100 million monthly active users,
  or more than 20 million US dollars in monthly revenue, must prominently display "Kimi K2.6" in its
  user interface. `THIRD_PARTY_NOTICES.md` says `configuration_deepseek.py` and
  `modeling_deepseek.py` are copied from DeepSeek-V3 under MIT. Nothing required accepting any
  terms. Research use is not restricted.
- **Registry.** The entry sets `trust_remote_code: true` because the repository's `auto_map`
  points Transformers at its own code for the config, model, tokenizer and processor. The registry
  contract therefore sets `publication_eligible: false`, as for `kimi-linear-48b-a3b-base` and
  `opencua-7b`. Its `blocker` says the remote code must be read and hashed before it runs, and only
  in a container with no network. Every `.py` file's SHA-256 is in the lane summary and the receipt. Nothing in the
  snapshot was imported or run.
- **Fit on this node.** The weights (595.2 GB) are larger than seven H100s (560 GB). A
  GPU-resident load needs all eight, and GPU 0 is held by another project (`transcreate-lama`, D110)
  until 2026-10-21.

## The fetch

- **The lane** is `infra/slurm/host-single-node/fetch-model-cpu.sbatch` (SHA-256 `22685e5e...`).
  It is the same batch script, image (`sha256:ba360ea1...`) and fetch script (`d995b59e...`) that
  fetched OLMo-2 for AM3 (job 1460) and Qwen3-32B (job 1310).
  - It ran from a `git archive` of commit `2baacac2`, the commit that registers the model, staged at
    `~/cotcodec-runs/stage0/kimi-k26-fetch/src/2baacac2`.
  - The archive's SHA-256, `0a4ac763...`, is the same on the Mac and on the host.
  - The receipt's `registry_sha256`, `6c42c0b2...`, is `models/registry.yaml` at that commit.
- **No GPU.** The job requested no GRES (TRES `cpu=8,mem=16G`). Docker's runtime was `runc`, and the
  container saw no `/dev/nvidia*` node. GPU 0 and the `transcreate-*` jobs were not touched.
- **No credential.** The preflight (`ops/kimi-preflight.sh`, `ops/preflight.log`) found no Hugging
  Face token in the environment or in the four token-file locations, and the container is passed
  none. The download log carries the hub client's warning that the requests are unauthenticated.
  No licence was accepted and no account was created.
- **One departure from AM3.** The Slurm time limit was raised from the script's 4 h to 12 h on the
  `sbatch` command line (`ops/kimi-fetch.sh`). A timeout would have lost the receipt. The batch
  script is unchanged.

| Step | UTC, 2026-10-15 | Duration |
|---|---|---|
| Hub metadata, file listing and six text files read anonymously | 18:30:45-18:31:11 | |
| Job 1528 submitted and started | 18:47:46 | |
| Last file written (snapshot mtimes) | 19:35:43 | 47 min 56 s for 595.2 GB, about 207 MB/s |
| Receipt written (every file hashed) | 19:43:22 | 7 min 39 s, about 1.3 GB/s |
| Job end | 19:43:22 | RunTime 00:55:36, 0 GPU-h |

- **The receipt** is `models/kimi-k2.6.receipt.json`, SHA-256 `f0a95884...`. That equals the
  lane summary's `receipt_sha256`.
  - It is a full-mode receipt of 96 files with each file's path, bytes and SHA-256.
  - Total bytes: 595,204,999,341. Artifact root: `68f8581365f4531c422bf0640c2215d6d85367d24b012a7b574468eeecde3316`.
  - It records `trust_remote_code: true` and `publication_eligible: false`.
- **Cross-check against the Hub** (`ops/kimi-crosscheck.py`, `models/crosscheck.json`): pass.
  - The receipt was compared with the Hub's file listing at the revision, fetched before the
    download (`hub/tree-7eb5002f.json`).
  - It has the same 96 paths and the same size for each.
  - All 67 LFS files' SHA-256 equal the Hub's LFS oids. That covers the 64 shards, the index,
    `tiktoken.model` and a demo video.
  - The 29 small non-LFS files were re-read from disk. Their git blob SHA-1 equal the Hub's oids,
    and their SHA-256 equal the receipt's.
  - The artifact root recomputes.
  - The six text files read before the download (`hub/text-files-read.sha256`) have the same
    SHA-256 as in the receipt.
- **Remote code.** The lane summary (`models/summary.jsonl`) lists the nine `.py` files with their
  SHA-256. None was imported or run.
- **On the host.** The snapshot is at `~/cotcodec-runs/hf-cache/cotcodec-models/kimi-k2.6/`. It is
  595,205,096,931 bytes on disk, including the hub client's `.cache/` metadata, which the receipt
  excludes. The lane's receipt is at `~/cotcodec-runs/hf-cache/cotcodec-receipts-cpu-lane/kimi-k2.6.json`.
  The disk has 19 TB free afterwards.
- **To re-verify** later, run `fetch_open_model.py --model-root ~/cotcodec-runs/hf-cache/cotcodec-models
  --receipt-root ~/cotcodec-runs/hf-cache/cotcodec-receipts-cpu-lane verify kimi-k2.6` in the lane's
  image. It re-hashes all 595 GB, about 8 minutes at the lane's rate. It was not re-run here.

### Reproduce

Host steps, in `ops/` (`jobs.log` has the times):
1. Stage the tree:
   `git archive --format=tar 2baacac2 | ssh <h100-alias> "d=~/cotcodec-runs/stage0/kimi-k26-fetch/src/2baacac2; mkdir -p \$d && tar -x -C \$d && echo 2baacac2d225fa5760f888ac8cfcf211005d7d86 > \$d/.git_sha"`.
2. `kimi-fetch.sh 2baacac2`: runs the preflight, then `sbatch` on the lane.
3. `kimi-capture-end.sh 1528`, in the background: saves `scontrol` before Slurm forgets the job.
   Accounting storage is off on this host. `kimi-progress.sh 1528` polls progress.
4. `kimi-crosscheck.py <receipt> hub/tree.json <snapshot> crosscheck-1528.json`.
5. `kimi-runtime-sources.py runtime-src runtime-sources.json`.
6. `kimi-stage-evidence.sh 1528`.

## Runtime support

Read only. Each cell rests on the source at the version named, not on a run. Nothing was loaded on a
GPU. The SHA-256 of every cited file is in `runtime/runtime-sources.json`.
- The pinned vLLM was read out of the program's base image with `docker create` and `docker cp`.
  Nothing in the image ran.
- The other projects were read from sparse, blobless clones of their latest release tags on
  2026-10-15.

| Runtime, version | Kimi-K2.6 (`KimiK25ForConditionalGeneration`, INT4) | Kimi-K3 (`KimiK3ForConditionalGeneration`, text `kimi_linear`, MXFP4) |
|---|---|---|
| **vLLM 0.31.0+cu129**, the program's pin: base image `vllm/vllm-openai@sha256:b18abb2d...` (image `423783aa`, commit `db9527a4`), under every `cotcodec-vllm` overlay | **Yes, native.** The registry maps it to `kimi_k25.py`, which builds the text model as `DeepseekV2ForCausalLM` with the compressed-tensors INT4 experts, plus the MoonViT tower. The config class is vLLM's own `KimiK25Config`. The tokenizer (`tokenization_kimi.TikTokenTokenizer`) is remote code, so `--trust-remote-code` is needed. The image processor is remote code too unless numba is present. Listed in the docs. | **Yes, native.** The registry maps it to the `vllm.models.kimi_k3` package, with NVIDIA and AMD branches. The NVIDIA branch has SM90 (H100) paths; some fused paths need SM100. Listed in the docs. |
| **SGLang v0.5.21** (`e00930c5`, 2026-09-29) | **Yes.** `kimi_k25.py`, `EntryClass = [KimiK25ForConditionalGeneration]`. The text model is `DeepseekV3ForCausalLM`. Moonshot's deploy guide says v0.5.10.post1 or later. | **Yes.** `kimi_k3.py`, `EntryClass = [KimiK3ForConditionalGeneration, KimiK3LinearForCausalLM]`. Its MXFP4 MoE has an SM90/SM120 CUTLASS path and an SM100 TRT-LLM path. |
| **KTransformers v0.7.2** (`a02efe36`, 2026-10-12), kt-kernel and its SGLang fork | **Yes, documented for K2.5,** whose architecture K2.6 shares (Moonshot's deploy guide uses `--kt-method RAWINT4` for K2.6). Most routed experts run on the CPU from the same native INT4 files (`--kt-num-gpu-experts` keeps some on the GPU), and attention runs on the GPU. `doc/en/Kimi-K2.5.md` asks for an AVX512F x86 CPU, at least 600 GB of system RAM and 48 GB of VRAM. | **Not documented.** v0.7.2 has no Kimi-K3 recipe or model-registry entry. kt-kernel's fine-tuning config knows an `mxfp4` expert format. |
| **llama.cpp b11669** (`620d2225`, 2026-10-15), `convert_hf_to_gguf.py` | **Yes, by conversion.** The text model becomes GGUF arch `deepseek2` (`conversion/deepseek.py`). The vision tower becomes an mmproj (`conversion/kimivl.py`, `PROJECTOR_TYPE_KIMIK25`). The converter dequantizes the INT4 `pack-quantized` experts to float (`dequant_packed`), so a GGUF of usable size needs a separate requantization step. | **Text yes.** `conversion/kimi_k3.py`, arch `kimi-k3`. Its MXFP4 experts are repacked bit for bit into ggml MXFP4 (`repack_mxfp4_blocks`). There is no mmproj mapping for `KimiK3ForConditionalGeneration`, so no vision. |
| **MLX**: mlx-lm v0.32.0 (`a9bd8af5`, 2026-09-30), mlx-vlm v0.7.8 (`97902318`, 2026-10-13) | **Yes.** mlx-lm `models/kimi_k25.py` drops the vision tower and loads the text model through `deepseek_v3.py`. That file remaps the INT4 `weight_packed`/`weight_scale` tensors straight into MLX quantized weights. mlx-vlm has a `kimi_k25` package with vision. | **Yes.** mlx-lm `models/kimi_k3.py` reads the MXFP4 `weight_packed` experts and can pipeline across machines with `mx.distributed`. mlx-vlm has a `kimi_k3` package with vision. |

- **None of these fits a 128 GB machine as it is.**
  - As shipped, the routed experts are 4-bit, so the resident weights stay near 595 GB (K2.6) and
    1,561 GB (K3).
  - KTransformers moves the experts from VRAM to system RAM, but its documented floor is still
    600 GB of RAM.
  - Requantizing below 4 bits (llama.cpp's GGUF types, for example) is the obvious lever. Even at
    1 bit per parameter, the Hub's 1,026,879,376,368 parameters are 128.4 GB.
  - Making it fit is the research question. This table records only what loads.
- **This host as a KTransformers box.** It has an Intel Xeon Platinum 8480+ (2 sockets, 208 vCPUs)
  with AVX512F, AVX512-BF16 and AVX512-VNNI. The VM does not expose AMX (`amx_tile` absent from
  `/proc/cpuinfo`). It has 1.77 TB of RAM, above the 600 GB floor.
- **Only vLLM is pinned by the program.** SGLang, KTransformers, llama.cpp and MLX have no
  digest-pinned image on the host. Using one for a GPU run needs that image first (AGENTS.md hard
  rule 2). MLX targets Apple silicon, and no model work is to run on the Mac.
- **Kimi-K3 facts.** These were read anonymously from the Hub at revision `f831ab66` on
  2026-10-15 (`hub/related-models.min.json`). It is `gated: false`, card `license_name: kimi-k3`.
  - 1,560,998,988,078 bytes in 119 files (1,561 GB), in MXFP4 (`mxfp4-pack-quantized`). The Hub's
    safetensors metadata counts 2.78T parameters.
  - Top-level `model_type: kimi_k3`. The text model is `KimiLinearForCausalLM` with `model_type:
    kimi_linear`.
  - 93 layers: 69 KDA linear-attention layers and 24 full-attention layers. 896 routed experts, 16 active.
  - It needs more than twice this node's 640 GB of GPU memory, so no single-node GPU-resident load
    is possible here.
- **Kimi-K2-Thinking** is the text-only sibling: `a51ccc05`, 594,256,579,602 bytes in 80 files,
  `DeepseekV3ForCausalLM`, `model_type: kimi_k2`, with the same INT4 scheme.
  - vLLM 0.31.0 maps `kimi_k2` to `DeepseekV3Config` and the architecture to `deepseek_v2`.
  - SGLang's `deepseek_v2.py` and llama.cpp's `deepseek2` arch take it as DeepSeek-V3.
  - KTransformers v0.7.2 has a `Kimi-K2-Thinking` registry entry with `RAWINT4`.
  - MLX was not checked for it.

Sources (file paths at the versions above):
- vLLM: `vllm/model_executor/models/registry.py` (SHA-256 `7f1d56e2...`, identical in the image and
  at the v0.31.0 tag: https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py),
  `model_executor/models/kimi_k25.py`, `vllm/models/kimi_k3/`, `transformers_utils/config.py`,
  `tokenizers/registry.py`, and https://github.com/vllm-project/vllm/blob/v0.31.0/docs/models/supported_models.md.
- SGLang: https://github.com/sgl-project/sglang/tree/v0.5.21/python/sglang/srt/models
  (`kimi_k25.py`, `kimi_k3.py`, `kimi_linear.py`).
- llama.cpp: https://github.com/ggml-org/llama.cpp/tree/b11669/conversion (`__init__.py`, `base.py`,
  `deepseek.py`, `kimi_k3.py`, `kimivl.py`), `gguf-py/gguf/constants.py`, `src/llama-arch.cpp`,
  `tools/mtmd/clip.cpp`.
- KTransformers: https://github.com/kvcache-ai/ktransformers/blob/v0.7.2/doc/en/Kimi-K2.5.md,
  `kt-kernel/python/cli/utils/model_registry.py`.
- MLX: https://github.com/ml-explore/mlx-lm/tree/v0.32.0/mlx_lm/models (`kimi_k25.py`, `kimi_k3.py`,
  `deepseek_v3.py`); https://github.com/Blaizzy/mlx-vlm/tree/v0.7.8/mlx_vlm/models.
- Moonshot's deployment guide: `docs/deploy_guidance.md` in the model repository at `7eb5002f`
  (SHA-256 in `hub/text-files-read.sha256`).

## Files

- `models/kimi-k2.6.receipt.json`: the lane's full-snapshot receipt (every file's path, bytes and
  SHA-256; total bytes; artifact root).
- `models/receipt.json`, `models/summary.jsonl`: the lane's job record and per-model summary, with
  the remote-code SHA-256 list.
- `models/crosscheck.json`: the receipt checked against the Hub listing.
- `models/scontrol-1528-start.txt`, `models/scontrol-1528-end.txt`, `models/slurm-1528.out.gz`,
  `models/kimi-k2.6.log.gz`: the Slurm records and the download log.
- `hub/`:
  - the trimmed Hub model info and the Hub file listing at the revision;
  - the SHA-256 of the text files read (LICENSE, notices, README, config, deploy guide), which are
    not committed;
  - `related-models.min.json`: trimmed metadata for Kimi-K3, Kimi-K2-Thinking and Kimi-K2.5.
- `runtime/runtime-sources.json`: the SHA-256 and commit of every runtime source file cited.
- `ops/`: every host script as it ran, `jobs.log`, `preflight.log` and `progress.log`.
  - The scripts keep the host home path, as in earlier ops records. No host address appears.
  - The directory carries the orchestrator's date (2026-10-16). Everything ran on 2026-10-15 UTC.
