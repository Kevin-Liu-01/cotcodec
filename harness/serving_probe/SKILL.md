---
name: harness-serving-probe-skill
description: Procedure for the vLLM serving-throughput probe core (serving-throughput-probe-v1) in harness/serving_probe/.
---

# cotcodec / harness / serving_probe

## Purpose
<!-- agent-docs:fill:purpose -->

The CPU-testable core of the serving-throughput probe that prices Stage-1 GPU
time for Q1 (offline n=8 sampling) and Q2 (closed-loop computer-use episodes).
`scripts/run_vllm_throughput_probe.py` owns engines, gates and persistence.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `config.py` loads `experiments/serving/serving-throughput-probe-v1.yaml`, the
  only source of engine flags, points, seeds and thresholds.
- `prompts.py` builds random-token text and the h1 (OSWorld qwen3vl) and h2
  (cua-speedrun, with screenshot folding) message layouts.
- `images.py` renders low-entropy PNG screenshots and random-pixel JPEGs.
- `client.py` is the one streaming client: open loop, episode replay, A/A.
- `metrics.py` parses `/metrics`, `nvidia-smi`, `/proc` and engine logs.
- `budget.py` applies the preregistered X1, stability and Q1/Q2 budget rules.
- `cuda_doctor.py` and `triton_kernels.py` are container-only (torch, Triton).

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Text and image seeds are separate streams, so controls resend identical text.
- Generated text stays in memory; only counts and token-id digests are written.
- Budget fallbacks are fixed in the preregistration and always flagged.
- Only accepted jobs enter a budget: `project` admits a job only when its
  summary.json is accepted (recomputed), exit code 0, and lists the SHA-256 of
  exactly the point files on disk.
- The frozen preregistration names the contract SHA-256 and the digest of every
  `*.py` here plus the driver; G0.0 and `project` refuse any other code. Print
  both with `run_vllm_throughput_probe.py digest`.
- Validity fails closed: no device samples, no reservation or a failed cache
  reset is invalid; only a signal interrupts and only a deadline truncates.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change a point, flag or any probe code | Before freezing: rerun `digest` and update the preregistration's two hash lines. After: a new experiment id. |
| Check flags against vLLM | `python scripts/run_vllm_throughput_probe.py vllm-args-doctor` in the overlay. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- The stock vLLM v0.31.0-cu129 image cannot import `vllm serve` (torchcodec is a
  CUDA 13 build); always run through the overlay, which removes it.
