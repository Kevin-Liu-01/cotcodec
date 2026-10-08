# OpenCUA-7B remote code: read and hashed (q2-stage1-rescoped-v1, G0 items 2 and 9.2; D49 iii)

`xlangai/OpenCUA-7B` at revision `a2efb7d2b104d477a4a2666a357e79550a28aafc` (MIT) needs
`--trust-remote-code`. D49 (iii) admits it under D29's conditions: third-party serving code,
not model-generated; revision pinned; files hashed and read before use; run only in the
serving container with no network. This file records the read. Nothing here was executed on
a GPU, and nothing was executed at all before these hashes were recorded.

## Provenance

Fetched by the GPU-less lane (`infra/slurm/host-single-node/fetch-model-cpu.sbatch`, SHA-256
`22685e5e4dc9f88cd9d6ba7aec7189a89500a4f80d2464b8df86e08e76e33c6d`), job 971 on 2026-10-08
(CPU only: TRES `cpu=8,mem=16G`, no GRES; Docker runtime runc; no `/dev/nvidia*` in the
container), source tree `9d4205a`. Receipt `cotcodec-receipts-cpu-lane/opencua-7b.json`
(SHA-256 `8109da82afc90b04b91f40cae4338c0e91dc1215d0a924c48e030e007ea6a2bd`): 40 files,
16,587,131,875 B, artifact root `b3dd62bff3bbd7f3e71f13cf61552d8fd4919febaf1ff34e5c11e4ba5c65a4be`.
The Hub resolved the pinned revision (`fetch_open_model.py` refuses any other).

## The four Python files

| File | Bytes | SHA-256 | What it does |
|---|---:|---|---|
| `configuration_opencua.py` | 1,325 | `12892d04cf561ddf85fbb166088cf6ec2c3edbfed86152461a25ed82f14ef560` | `OpenCUAConfig(PretrainedConfig)`: wraps a `Qwen2_5_VLVisionConfig` and a `Qwen2Config`; sets `media_placeholder_token_id` 151664. Imports transformers only. No I/O. |
| `tokenization_opencua.py` | 14,151 | `7386c9fb5b45a5e5a63fab059dd3c4650c1a229d7e1ce5e14ead276e6be9f3db` | `TikTokenTokenizer` / `TikTokenV3(PreTrainedTokenizer)`: loads `tiktoken.model` from the snapshot directory with `tiktoken.load.load_tiktoken_bpe` (a local path), builds the special-token table from `added_tokens_decoder`, encodes in chunks. File access: reads the vocabulary file; `save_vocabulary` copies it only when called. No network, subprocess, `eval`/`exec` or dynamic import. |
| `processing_opencua.py` | 14,158 | `58198678600fd5a81aab6838321ab56b663f6f2c29918af1bac03ac2378b1b99` | `OpenCUAProcessor(Qwen2_5_VLProcessor)`: expands one image placeholder per image into the processor's token count. Imports torch, numpy, PIL, transformers. One commented-out `IPython.embed()` line. No I/O. |
| `modeling_opencua.py` | 24,850 | `fb8fcf59150cd659d7cb54151f32b49e18bbd2c662fbe93daf78afc33f0a1b53` | `OpenCUAForConditionalGeneration`: a LLaVA-style wrapper of the Qwen2.5-VL vision tower and `Qwen2ForCausalLM` that merges image features into the embedding sequence (ported from transformers v4.53.0 Qwen2.5-VL and LLaVA). Tensor code only; no I/O. vLLM v0.31.0 serves the architecture with its own implementation (registry entry `OpenCUAForConditionalGeneration`, G0 item 9.1), so this file is not what runs in the engine. |

The configuration (`config.json`) names `auto_map` entries for these classes; the
tokenizer (`tokenizer_config.json`) maps `AutoTokenizer` to `tokenization_opencua.TikTokenV3`
and carries the chat template (`<|im_system|>`, `<|im_user|>`, `<|im_assistant|>`,
`<|media_begin|>image<|media_content|><|media_placeholder|><|media_end|>`).
`generation_config.json` is `{"max_length": 32768, "eos_token_id": 151644}`; the S1a anchor
argv keeps the card's `--generation-config vllm`, so the request's sampling applies.
`config.json` declares `max_position_embeddings` 128,000 (text and top level), so vLLM
refuses the card's 131,072 and the anchor argv sets 32,768 (registration section 4).

## Verdict

The remote code is ordinary model-definition, configuration and tokenizer code with no
network access, no subprocess, no dynamic evaluation and no file writes outside an explicit
`save_vocabulary` call. It satisfies D49 (iii)'s "read and hashed before use".
`harness/q2_stage1/anchor.py` (`REMOTE_CODE_SHA256`) refuses to import anything from a
snapshot whose four files differ from these digests.
