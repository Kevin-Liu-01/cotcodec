# q1-stage0-substrate-corpus

**Status: DRAFT for the program owner's review. Not frozen.** No admission data
exists. The only outputs so far are CPU build validation in GPU-less
containers (mock-H100 codegen, conversion, static, compile and interpreter
checks), which this file describes as infrastructure checks, not data.

Experiment id: `q1-stage0-substrate-corpus`. Companion to
`q1-stage0-gate-validation` (core owner), which scores gates and the audit on
the corpus defined here. Question file: `program/questions/q1-kernel-gate-strength.md`.

## Question

Which compiler-generated (S1) and human-written pre-2025 (S2) Triton kernels
enter the Q1 Stage 0 corpus of candidate correct substrates, and does the
evaluation half contain enough independent kernels (at least 72) for the
gate-validation false-reject criterion "FRR(c) at most 2% with a Clopper-Pearson
95% upper bound at most 5%"?

This is instrument construction. It tests no hypothesis about gates. Whether a
candidate is correct or a natural fault is decided by the frozen audit under
`q1-stage0-gate-validation`, not here.

## Pinned inputs

- Problems: KernelBench `423217d9fda91e0c2d67e4a43bf62f96f6d104f1`, levels 1 and
  2 (200 problems). Excluded before any build: L2/23, L2/80, L2/83 (constant-zero
  output, KernelBench-Verified App. I) and L2/66 (training-mode Dropout). 196
  problems remain.
- Code: `harness/q1/substrates/` and `scripts/q1_build_substrates.py` at the
  commit recorded as `git_head_at_freeze` in the ledger row of this file;
  shared schema `q1-schema/1` (`harness/q1/schema.py`).
- Image: `cotcodec-research:0b3ecef0-architecture`, image ID
  `sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29`
  (repo digest `sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`);
  torch 2.11.0+cu128 (git `70d99e998b4955e0049d13a98d77ae1b14db1f45`), Triton
  3.6.0, Python 3.12.3. If the gate-validation run uses a derived image, the
  admission job uses the same image ID and records it.
- S2 sources, vendored verbatim and SHA-256 pinned in `s2_catalog.UPSTREAM_FILES`
  (22 files): FlagGems tag v1.0-manual `18b8e4281610c91e178518271bc756a98fdc84c9`
  (Apache-2.0); Liger-Kernel tag v0.3.1 `1520999e60e34a9e034026d05917082de098be1e`
  (BSD-2-Clause, with Unsloth code under Apache-2.0); Triton tutorials at
  `105cb56487cd8a433b8fbfe9cc63c1f1c04a4b2a` (MIT).

## Construction rules (fixed now)

**S1.** For each of the 196 problems, `torch.compile(model, dynamic=True,
fullgraph=True)` under `torch.no_grad()` with Inductor `deterministic=True`,
`triton.autotune_pointwise=False`, caches disabled, Dynamo
`assume_static_by_default=False`, `specialize_float=True` and duck sizing off.
Canonical codegen runs on one H100 (`mode=cuda`) inside the admission job. A
problem whose default output calls a library GEMM or convolution is recompiled
with `max_autotune=True` and `max_autotune_gemm_backends="TRITON"`; the
template build is kept only if Inductor's deterministic choice is a Triton
template. Each kernel uses the first config its heuristic returns (one config
except some persistent reductions, recorded as `first-of-n`). Conversion follows
`inductor_convert.py` exactly. A problem yields no S1 substrate, with its reason
code recorded, when codegen fails (`graph-break`, `compile-failed`, `crash`) or
the conversion would be unfaithful (`no-triton-kernel`, `aliased-output`,
`runtime-input-mutation`, `aot-runtime-epilogue`, `call-arity`,
`unsupported-grid` and the other codes in `ConversionError`).

**S2.** Exactly the 25 entries of `s2_catalog.CATALOG` (18 kernel families: an
upstream file plus its forward kernels), built with the recorded edits. Each
autotuned kernel is pinned to the first listed config that compiles for sm_90
at fp32; the index is recorded per entry (`tutorial-matmul` uses index 1 because
config 0 needs 294,912 B of shared memory at fp32, above the 232,448 B sm_90
limit; all others use index 0). No entry is added, removed or edited after this
file is frozen; a change is a new experiment id.

## Admission rule (fixed now)

A built substrate is admitted to the corpus if and only if all hold:

1. `check-static` passes (plain `kernel[grid]` launches only, `ModelNew` present,
   no `libentry`, `triton_heuristics` or static launcher).
2. `check-compile-native` passes: every launched kernel compiles for sm_90 at
   native shapes on the meta device. If the substrate's host code cannot run on
   the meta device (it reads a tensor value, such as Liger cross-entropy's
   `.item()`), this check is recorded as not applicable and rule 3 decides.
3. GPU admission at native shapes, seed 42: gate (b)'s `LaunchHook`
   (`harness.q1.gates.gate_b`) records at least one launch under
   `torch.inference_mode()` and under `torch.enable_grad()`, each after one
   unhooked warmup call (b1's protocol). Inputs come from the problem's
   `get_inputs` drawn on the device. `refuse` (the substrate rejects the native
   shape before launch), `reject` (no launch seen) and `error` all mean not
   admitted, with the verdict recorded.
4. For S1 only: `check-interp` does not report `fail` (a numerical mismatch
   with the reference beyond 1e-3 on small CPU inputs under the Triton
   interpreter). A `fail` marks the substrate `conversion-suspect` and excludes
   it. `no-small-shape`, `unsupported` and `error` from interpreter limitations
   do not exclude. For S2, interpreter outcomes are reported only, because the
   interpreter evaluates Python `and` on tensors differently from compiled
   Triton.

Admission says nothing about correctness. Native-shape gate (a) results and
audit verdicts on admitted substrates belong to `q1-stage0-gate-validation`.

## Split (fixed now)

`split.calibration_split` with seed 42 over the 196 admissible problem ids,
per level: sort ids, shuffle with `random.Random("42:L1")` (and `"42:L2"`), the
first `ceil(n/2)` go to calibration. Result: 98 calibration and 98 evaluation
problems (L1 50/50, L2 48/48), split SHA-256
`b773f218f174e3bb8ab4fcde4f4e6318d870ef020e6b86bce807362c5292a0b2`. The split
uses only the problem list and was computed before any substrate was built.
S2 substrates are evaluation-only. A substrate that fails admission leaves its
half; it is never moved to the other half.

## Metrics (unit of analysis: substrate; S2 also by kernel family)

Primary:

- `n_eval_independent` = admitted S1 evaluation-half substrates (one per
  problem) plus admitted S2 kernel families (a family with several admitted
  problems counts once).

Secondary, all reported:

- Built, admitted and excluded counts by tier, level, split half and reason
  code; `triton-only` versus `hybrid-library` S1 substrates.
- Mock-versus-device codegen parity per S1 problem (`identical` or `differs`,
  separately for kernels and guards).
- Interpreter outcomes and maximum absolute and relative error per substrate.
- Registers, stack and shared memory per kernel from the native-shape compile.
- GPU-seconds and wall-seconds per admission row.

## Decision rules

- **D-1, FRR feasibility.** If `n_eval_independent` is at least 72, the
  gate-validation FRR(c) criterion is evaluable as written. If it is between 60
  and 71, report the criterion as under-powered with its actual n (zero
  rejections give a Clopper-Pearson upper bound of 5.1-6.0%) and do not augment
  the evaluation set. If it is below 60, stop before any gate scoring and refer
  the corpus to the program owner.
- **D-2, converter fault.** If more than 5% of converted S1 substrates are
  `conversion-suspect`, the converter is presumed wrong: fix it as a new
  converter version, rebuild every S1 substrate, rerun all checks, and report
  both versions.
- **D-3, mock path.** If more than 10% of S1 problems differ between mock and
  device codegen, the mock path is declared unreliable for future CPU-only
  builds. The corpus always uses the device build, so D-3 changes no corpus
  membership.

## Seeds, sample size and precision

- Admission uses seed 42 only. Launch visibility is a property of the launch
  path, not of input values; seeds 43 and 44 are exercised by every gate in
  `q1-stage0-gate-validation`, which runs seeds 42, 43 and 44.
- The split seed is 42.
- Expected size, from the CPU dry run (mock codegen; infrastructure check, not
  data): 156 of 196 problems convert (81 evaluation, 75 calibration); 35 yield
  no Triton kernel (L1 convolutions, kept on cuDNN by Inductor's deterministic
  choice, and 3D average pooling); 5 fail codegen in mock mode (4 calibration,
  all to be retried on the device). With all 81 evaluation S1 candidates and the
  18 S2 families admitted, `n_eval_independent` would be 99.
- Precision, not power: with zero false rejections, the two-sided 95%
  Clopper-Pearson upper bound on FRR is 1 - 0.025^(1/n): 4.99% at n = 72, 3.7%
  at n = 99. One false rejection at n = 99 gives an upper bound of 5.5%, so the
  FRR(c) criterion tolerates no false rejection below n = 110 (scipy
  `beta.ppf(0.975, x + 1, n - x)`).

## Infrastructure failures and exclusions

- A job that does not end `COMPLETED` with exit `0:0`, exits 75
  (`foreign_gpu_process`), or is preempted, is rerun as a new versioned job; its
  partial rows are kept and labelled, and never mixed into the admitted set.
- A per-substrate admission `timeout` (900 s) or CUDA out-of-memory error is
  retried once in a fresh process. A second identical outcome is recorded as the
  substrate's admission verdict (`timeout` or `error`), not as infrastructure.
- Codegen failures that happen only in mock mode (for example eager CUDA
  constant creation) are dry-run infrastructure; the device build decides.

## Reported regardless of outcome

Every problem with its outcome and reason code; every substrate's
`substrate.json`, `build.json`, `normalization.diff` and admission rows; the
parity table; interpreter and compile results; the image ID and code revision;
and the following predictions, written from code reading before any GPU run:
Liger LayerNorm and the tutorial LayerNorm refuse the native L1/40 row
(4,194,304 elements); FlagGems relu, gelu, silu and mul use block pointers
without a boundary check and write past the end at sizes that are not a
multiple of the block; the tutorial matmul computes `tl.dot` in TF32 and is the
TF32-policy control.

## Design decisions (made where the reviewed plan left a choice)

1. Inductor codegen runs in a GPU-less container against a mocked H100 for the
   dry run; the canonical build runs on the device in the admission job, and
   parity is reported (D-3).
2. Inductor deterministic mode and `autotune_pointwise=False` give one config per
   kernel without on-device benchmarking, which is what Inductor would launch in
   that mode; persistent reductions with several configs take the first.
3. GEMM templates use Inductor's own deterministic template choice, not
   benchmarking, so the build is reproducible. The same rule leaves
   convolutions on cuDNN, which removes L1 convolutions from S1.
4. `specialize_float=True`: Python float inputs and attributes are compiled as
   constants, and a substrate refuses a scalar input that differs from its
   native value.
5. Dynamo and Inductor guards become refusals before launch, so a substrate
   never silently runs outside its compiled specialisation (D14).
6. S2 autotuned kernels are pinned to one config so that every gate and the
   audit execute the same program.
7. The Liger cross-entropy wrapper passes a clone of the logits, because the
   upstream forward writes gradients into its input and the KernelBench
   contract is a pure function.
8. The tutorial softmax launch is normalised from a warmed-up `CompiledKernel`
   launch, which the hook cannot see, to a plain JIT launch with one program
   per row.
9. The reference `Model` embedded in each substrate drops docstrings, because
   KernelBench's static checker matches "pass" in "forward pass". Upstream S2
   docstrings are kept, so `a_static` false rejections of S2 remain measurable.
10. The zero-GPU prior table (lethe per-row verdicts) is delivered by the core
    owner in `scripts/q1_lethe_priors.py`; this corpus does not duplicate it.
