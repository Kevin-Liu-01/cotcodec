# Q1 substrates

The correct-kernel corpus for the Q1 Stage 0 gate validation
(`program/preregistrations/q1-stage0-substrate-corpus.md`, draft). Two tiers,
both outside the R570 rule's scope by decision D3:

- **S1**: TorchInductor-generated Triton for every admissible KernelBench@423217d9
  L1/L2 problem, compiled with dynamic shapes and converted to plain
  `@triton.jit` kernels launched as `kernel[grid](...)`.
- **S2**: human-written pre-2025 Triton (FlagGems v1.0-manual, Liger-Kernel v0.3.1,
  Triton tutorials), each mapped to one KernelBench problem by a short `ModelNew`.

Every substrate follows `harness/q1/schema.py`: a directory named after its
`substrate_id` with `kernel.py` (defining `ModelNew` with `Model`'s constructor
and forward arguments) and `substrate.json`, plus `build.json`,
`normalization.diff` and the upstream text it came from.

## Why the conversion

Gate (b) (KernelGYM's hacking check) counts a kernel only if its launch passes
through `JITFunction`/`Autotuner`/`KernelInterface`. Torch 2.11 Inductor launches
through `CachingAutotuner` and a static CUDA launcher, and FlagGems' `libentry`
caches the compiled kernel and relaunches it directly, so both are invisible to
the hook and would be false-rejected by gate (b) for their packaging. Static-shape
Inductor code also fails at every held-out shape. Hence: dynamic shapes, then
plain JIT launches, and admission only after the hook sees the launch.

## S1 pipeline

1. `inductor_codegen.py` (torch + triton; runs in the research image).
   `torch.compile(model, dynamic=True, fullgraph=True)` under `no_grad`, with
   Inductor `deterministic=True` and `triton.autotune_pointwise=False` (so each
   kernel has the single config Inductor would launch, without benchmarking),
   caches off, duck sizing off and `specialize_float=True`. It stops after the
   wrapper module is written; nothing is compiled for or launched on a device,
   and inputs are fake tensors (no 17 GB allocations). The record keeps the
   wrapper, each kernel's heuristic configs (via an intercepted
   `cached_autotune`), Inductor's own `GridExpr` strings, the Dynamo
   placeholders with their guard sources, the shape-environment guards and
   ranges, and the AOT view/mutation metadata.
   - `mode="cuda"` uses the real device (the canonical build, in the GPU job).
   - `mode="mock-h100"` runs in a GPU-less, network-less container: a handful of
     torch/Dynamo/Triton device queries are patched to report an H100 SXM
     (`MOCK_PATCHES`, `MOCK_H100_PROPERTIES`), and a codegen-only Triton driver
     targets `GPUTarget("cuda", 90, 32)`. It refuses to run if a CUDA device is
     visible. This is the CPU dry run; `parity` compares it with the device build.
   - Problems whose default output calls a library GEMM or convolution are
     recompiled with `max_autotune` and Triton templates; the template build is
     kept only if Inductor's own deterministic choice
     (`AlgorithmSelectorCache.pick_deterministic_choice`) is a Triton template.
     For convolutions it never is, so L1 convolution problems have no Triton
     kernel and are excluded.
2. `inductor_convert.py` (pure Python). Kernel text is copied verbatim minus the
   `@triton_heuristics` decorator; `kernel.run(..., stream=s)` becomes
   `kernel[grid](..., config, num_warps, num_stages, debug, sanitize_overflow=False)`
   with Inductor's compile options; grids come from `GridExpr` (ceil division as
   `triton.cdiv`; template kernels keep their fixed grid); device index 0 becomes
   the inputs' device. Dynamo tensor guards (dtype, rank, device type), shape
   guards, symbol ranges (sizes 0 and 1 were specialised away) and pinned scalar
   inputs become `SubstrateRefusal` checks before any launch, so an input outside
   the compiled specialisation is refused instead of computed wrongly (D14's
   "refusal is not silently wrong"). `ModelNew(Model)` inherits the embedded
   reference `Model` (docstrings dropped: KernelBench's static checker matches
   `pass` in "forward pass") and binds the graph inputs from their guard sources.
   Records that cannot be converted faithfully are refused with a reason code
   (`aliased-output`, `runtime-input-mutation`, `aot-runtime-epilogue`,
   `no-triton-kernel`, `call-arity`, `unsupported-grid`, ...).

## S2 catalog

`s2_catalog.py` lists 25 substrates in 18 kernel families. Upstream files are
vendored verbatim under `third_party/` and checked against size and SHA-256
pins. Normalisations are text edits, each recorded:

| Edit | Why |
|---|---|
| `strip-libentry` | `libentry` relaunches a cached kernel directly; invisible to the hook |
| `drop-debug-prints` | `if __debug__: print("GEMS ...")` on every call |
| `pin-autotune` | `configs=(X)[i:i+1]`: one config, the first listed that compiles for sm_90 at fp32, so every gate and the audit run the same program |
| `tl-math-to-libdevice` | `tl.math.tanh`/`tl.math.pow` do not exist in Triton 3.6 |
| `liger-inline-utils` | inline `ensure_contiguous`/`calculate_settings`; resolve the Triton-version `rsqrt` import to its Triton >= 3 branch |
| `tutorial-*` | fp32 output for the fp16 tutorial matmul; CUDA config list; plain JIT launch for the softmax tutorial's warmed-up `CompiledKernel` |

Predicted from code reading, before any GPU run: Liger LayerNorm and the
tutorial LayerNorm refuse the native L1/40 row (4,194,304 elements); FlagGems
block-pointer kernels (relu, gelu, silu, mul) have no boundary check and write
past the end at sizes that are not a multiple of the block (a natural fault at
held-out shapes); Liger cross-entropy writes gradients into its logits, so the
wrapper passes a clone; the tutorial matmul is the TF32-policy control.

## Admission

| Check | Needs | Decides |
|---|---|---|
| `check-static` | Python | launch path: `ModelNew` present, plain `kernel[grid]` launches, no `libentry`/`triton_heuristics`/static launcher |
| `check-compile`, `check-compile-native` | torch + triton, no GPU | every launched kernel compiles for sm_90 (small CPU inputs; native shapes on the meta device); registers, stack, shared memory from `cuobjdump` |
| `check-interp` | torch + triton, `TRITON_INTERPRET=1`, no GPU | conversion validation: `ModelNew` vs `Model` on small CPU inputs (loose 1e-3); libdevice calls are evaluated with NumPy, a check shim only |
| `admit-gpu` | one GPU, Slurm job | gate (b)'s `LaunchHook` records a launch under `inference_mode` and `enable_grad` at native shapes (b1 protocol: warmup 1 unhooked, step 1 hooked); writes `admission_hook` rows |

Small inputs come from the problem's own `get_inputs` after greedily halving
module-level sizes that neither `get_init_inputs` nor `Model` reads, keeping
every shape guard satisfied.

`split.py` fixes the S1 calibration/evaluation split from the problem list
alone (seed 42, per level), before any admission; S2 is evaluation-only.

## Commands

```bash
# CPU (GPU-less container with the research image):
python scripts/q1_build_substrates.py s1-codegen --kernelbench-root K --records-dir R --mode mock-h100
python scripts/q1_build_substrates.py s1-convert --records-dir R --out-root S
python scripts/q1_build_substrates.py s2-build --kernelbench-root K --out-root S
python scripts/q1_build_substrates.py check-static --root S
python scripts/q1_build_substrates.py check-compile-native --root S --kernelbench-root K
TRITON_INTERPRET=1 python scripts/q1_build_substrates.py check-interp --root S --kernelbench-root K
python scripts/q1_build_substrates.py split --kernelbench-root K --out S/split.json
python scripts/q1_build_substrates.py manifest --root S --split S/split.json --out S/corpus_manifest.json
# GPU (after the preregistration is frozen): experiments/manifests/q1-substrate-admission.yaml
```

`K` is a KernelBench checkout or the vendored problem tree
(`harness/q1/third_party/kernelbench/problems`); both layouts are accepted.

## NOTICE

Third-party material used by this directory, all read at the pinned revisions:

- **KernelBench** (https://github.com/ScalingIntelligence/KernelBench,
  `423217d9fda91e0c2d67e4a43bf62f96f6d104f1`, MIT, copyright 2023 Anne Ouyang,
  Simon Guo, Azalia Mirhoseini): problem files are read at build time; each
  substrate embeds its problem's `Model` class (docstrings dropped). Five
  codegen records in `tests/fixtures/q1_substrates/` contain problem sources.
- **FlagGems** (https://github.com/flagos-ai/FlagGems, tag `v1.0-manual`,
  `18b8e4281610c91e178518271bc756a98fdc84c9`, Apache-2.0, copyright 2024 BAAI;
  no NOTICE file at the tag): 10 files vendored verbatim in
  `third_party/FlagGems/` with the LICENSE; built substrates are modified copies,
  changes listed in each `substrate.json` and `normalization.diff`.
- **Liger-Kernel** (https://github.com/linkedin/Liger-Kernel, tag `v0.3.1`,
  `1520999e60e34a9e034026d05917082de098be1e`, BSD-2-Clause, copyright 2024
  LinkedIn Corporation): 5 files vendored verbatim with LICENSE and NOTICE.
  `utils.py` and `rms_norm.py` state that they incorporate code from Unsloth
  (https://github.com/unslothai/unsloth) under Apache-2.0.
- **Triton tutorials** (https://github.com/triton-lang/triton,
  `105cb56487cd8a433b8fbfe9cc63c1f1c04a4b2a`, MIT, copyright 2018-2020 Philippe
  Tillet, 2020-2022 OpenAI): 3 tutorial scripts vendored verbatim with the
  LICENSE; only their kernels and the matmul host function are used.
- **PyTorch / TorchInductor** (https://github.com/pytorch/pytorch, v2.11.0,
  `70d99e998b4955e0049d13a98d77ae1b14db1f45`, BSD-3-Clause): S1 kernels are
  Inductor output and import `torch._inductor.runtime.triton_helpers`; the
  converter reuses Inductor's `GridExpr` strings. No PyTorch source is vendored.
- **KernelGYM** (https://github.com/hkust-nlp/KernelGYM, `3a84417f`, no LICENSE
  file): not vendored and not copied. The fallback `LaunchRecorder` patches the
  two entry points the reviewed plan documents for KernelGYM's released hook
  (`JITFunction.run`, `Autotuner.run`); it was written from that description.
  Admission uses the core owner's spec-first `harness.q1.gates.gate_b.LaunchHook`
  when present.
- **KernelBench-M**, **cua-speedrun**, **sandweave** and **Dr. Kernel**: not used
  here; nothing read from them is reproduced.

Sizes and SHA-256 of every vendored file: `s2_catalog.UPSTREAM_FILES`.
