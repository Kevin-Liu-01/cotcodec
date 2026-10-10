# C5 v1: Phase 0 instrument for emulated FP4 training and the Phase 1 grid x scale-configuration factorial design (c5-fp4-instability-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the C5 research gauntlet (D67) on branch
`gauntlet/c5-fp4`. Part A registers Phase 0 for execution after a freeze;
its caps sum to 3.05 GPU-h, under D20's 8 GPU-h line. Part B registers the
Phase 1 design before any data exists. Its caps follow a formula fixed here and
are computed from Phase 0's measurement; they will exceed 8 GPU-h, so Phase 1
runs only after Kevin's ruling under D24 and a fresh pre-freeze audit of Part B.
The design decisions at the end (1 to 41) need the program owner's acceptance.
No host job of any kind runs while a Q2 S1a VM or GPU job (`s1a-a1-*`,
`q2s1a-*`) is running or pending. The proposal that argues and attacks this
design is `program/proposals/2026-10-10-c5-fp4-instability.md`; its evidence
bundle is `program/proposals/evidence/2026-10-10-c5-fp4-instability/`.

## Relation to the dossier and to D67

- Source: dossier entry `C5-fp4-instability-factors`
  (`program/evidence/2026-10-06/question-dossier.md`, section 8), "First
  experiment" and "Kill criteria".
- Kept: emulated training of a 30M-class Llama on 1.2B FineWeb-Edu tokens; grid
  {E2M1, INT4}; scale/block levels E8M0/B32 (4.25 b), UE4M3+FP32/B16 (4.5 b) and
  BF16/B32 (4.5 b); a BF16 baseline; RTN forward and SR on gradients; LM head,
  embeddings and last block in BF16; 1D blocks; no RHT; per-cell LR tuning then
  3 seeds; an emulation-path control; the kill line "fake-quant overhead above
  4x needs a fused Triton quantizer"; the branches "prior survives", "grid or
  interaction comparable", "every cell within seed noise", "emulation path moves
  loss as much as the factors".
- Changed, with reasons in the proposal's mechanism table: UE5M3/B16 replaced by
  E8M0/B16 (the dossier's set is rank 8 of 10 under the registered model; this
  set is full rank); E1M2 removed from Phase 1 (it is INT4 times 1/4); the GEMM
  model is the exact TF32-operand path with tensor scales in the epilogue (BF16
  decode is inexact for the BF16-scale cell); LR sweeps widened; a
  positive-control gate added before the factorial; a numerics prediction added
  and frozen before Phase 1; a conditional Stage 1c of two more seeds before any
  claim.
- Every dossier kill criterion is made quantitative below with intervals,
  seeds, controls, decision rules and simulated operating characteristics.

## Question

Part A: can an exact, conformant, resumable emulator of the registered FP4
formats run a 35M Llama on this host, at what throughput and packing, and what
does a tensor-level analysis on that model's own tensors predict for the grid
effect in each scale configuration?

Part B: in emulated FP4 training of that model, how much of the final
validation loss gap is explained by the grid, a block-size step at fixed scale
encoding, a scale-encoding step at fixed block size and storage, and the
equal-storage trade between a wider scale and a smaller block, and does the
grid interact with the scale configuration as Part A's prediction says?

Claim scope: `systems-pipeline` (training numerics under one declared
emulator, at 35M). No claim about native FP4 kernels, speed, energy, rounding
modes, RHT, UE5M3 or larger models is licensed by any outcome.

## Identity

- Experiment id: `c5-fp4-instability-v1`.
- Model (all runs): Llama-style decoder, d_model 384, 6 layers, 6 heads (head
  dim 64), SwiGLU FFN 1024, pre-norm RMSNorm (FP32, affine weights FP32 and never
  quantized), RoPE (base 10,000), untied embeddings, vocabulary 32,000, context
  1,024; 35,197,824 parameters, of which the quantized linear weights of blocks
  1 to 5 are 8,847,360. No qk-norm, no z-loss, no dropout.
- Tokenizer: `mistralai/Mistral-7B-v0.1` revision
  `27d67f1b5f57dc0953326b2601d68371d40ea8da`, `tokenizer.json` (1,795,188 B),
  Apache-2.0, ungated. EOS appended between documents.
- Data: `HuggingFaceFW/fineweb-edu` revision
  `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`, `sample/10BT/000_00000.parquet`
  (2,152,819,114 B, LFS oid
  b1ba7b2ce4cb5ea6ef42dca40263eabb85f37700d01693a68e9b30a31d78e871) and
  `001_00000.parquet` (2,152,222,432 B, LFS oid
  3fcf2dc69cd52503986276d3d2d26a8c356d0f2ea28a0de4fdbda8cf87755693); ODC-BY 1.0.
  `002_00000.parquet` (2,151,796,315 B) is added only if files 000 and 001 give
  fewer than 1.25B training tokens after the split.
- Image: the architecture image rebuilt at the freeze commit by
  `infra/slurm/host-single-node/build-architecture-image.sbatch` (CPU job); its
  digest and provenance receipt are recorded in the freeze record. The current
  image `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (torch 2.11.0+cu128, Triton 3.6.0) has no C5 code.
- Code revision: the freeze commit; harness files and their SHA-256 listed in
  the freeze record.
- Seeds: fresh seeds 42, 43, 44 (Stage 1c adds 45, 46); sweep seed 1000; the
  Phase 0 capture run uses seed 1000. Each seed s defines three counter-based
  Philox streams: initialisation (s, 0), data order (s, 1), stochastic rounding
  (s, 2) keyed by (step, layer, GEMM, operand). Simulation and bootstrap seed 42.
  CPU conformance sampling seed 42.

## Prerequisites before freeze (no GPU)

1. Kevin's OK for the data download (two FineWeb-Edu files, 4.31 GB, three if
   needed, 6.46 GB) and the tokenizer files; then a CPU Slurm fetch with SHA-256
   receipts and a CPU tokenization job, both after no S1a job is running.
2. Harness (reviewed project code under D7): the model, AdamW and schedule
   driver, data loader with the split rule and a resumable cursor, the
   quantizers and emulated linear layer (eager and torch.compile paths),
   checkpoint and resume with all generator states, evaluation, the throughput
   probe, tensor capture, the analysis and verdict scripts, each unit-tested on
   CPU.
3. CPU conformance suite (section "Phase 0, CPU") passing on the development
   Mac against gfloat 0.5.2 and ml_dtypes 0.6.0 (pinned).
4. Manifests `experiments/manifests/c5-fp4-instability-v1/j0.yaml` to `j3.yaml` with `--dry-run` and `--test-only` passing through `scripts/submit_docker_research_job.py`.
5. A `kind: cpu-doctor` orx node running `scripts/run_fp4_quantizer_doctor.py`
   (the CPU suite plus N2 recomputed) through `scripts/orx_run.py`.
6. A fresh pre-freeze audit of this file against the harness.

## Model training (fixed for every run)

AdamW (beta1 0.9, beta2 0.95, epsilon 1e-8, weight decay 0.1 on matrices only),
global gradient-norm clipping 1.0, FP32 master weights and optimizer states,
BF16 autocast for non-quantized operations; batch 64 sequences x 1,024 tokens =
65,536 tokens per step; 18,311 steps = 1,200,029,696 tokens; linear warmup over
366 steps (2%), cosine decay to 10% of peak. Evaluation every 1,000 steps on the
first 2M validation tokens and at the end on the full 15M-token validation set;
loss and gradient L2 norm logged every step.

## Data

Validation documents: int(SHA-256(UTF-8 document id)[:8], 16) mod 100 = 0;
the validation set is the first 15,000,000 tokens of those documents in file
order. Training stream: all other documents of files 000 and 001, shuffled once
per data-order seed by a seeded permutation of documents, concatenated and cut
into 1,024-token sequences; a single pass, no document repeated. The data
cursor (document index, token offset) is checkpointed.

## Quantization and GEMM (the pinned specification)

- **Grids.** E2M1: {0, ±0.5, ±1, ±1.5, ±2, ±3, ±4, ±6}, q_max 6 (15 distinct
  values). INT4: symmetric {−7, ..., 7}, q_max 7 (15 values; −8 unused).
- **Scale configurations.** S1: E8M0 block scale, B = 32 (4.25 b/element).
  S2: E8M0, B = 16 (4.5 b). S3: UE4M3 block scale (positive E4M3fn, 2^−9 to 448)
  with an FP32 per-tensor scale, B = 16 (4.5 b plus 32 bits per tensor). S5: BF16
  block scale, B = 32 (4.5 b). Blocks are 1D along each GEMM's reduction axis.
- **Scale rule (every configuration).** Per block, amax = max |x| in FP32.
  S1, S2: s = 2^ceil(log2(amax / q_max)), exponent clamped to [−127, 127].
  S5: s = amax / q_max computed in FP32 and rounded up to the next BF16 value.
  S3: s_t = amax_tensor / (q_max × 448) in FP32, current (not delayed) per GEMM
  operand per step; s_b = (amax / q_max) / s_t rounded up to the next UE4M3
  value, clamped to [2^−9, 448]. An all-zero block gets the smallest scale code
  and zero elements. No element can exceed q_max, so saturation never triggers;
  it is still implemented (clamp) and tested.
- **Element rounding.** y = x / s computed by true division in FP32 (never by
  multiplying with a reciprocal). RTN: round to the nearest grid value, ties to
  the even code (E2M1: the code whose mantissa bit is 0; INT4: the even
  integer). SR: with frac the position of |y| between its two neighbouring grid
  values lo and hi, round to hi iff R < floor(frac × 2^24), R uniform on
  {0, ..., 2^24 − 1} from the SR stream.
- **Which tensors.** All three GEMMs of every linear layer (QKV, output,
  gate, up, down) in blocks 1 to 5: Fprop (X, W: RTN), Dgrad (dY: SR, W: RTN),
  Wgrad (X: RTN, dY: SR). Block 6, embeddings, LM head, attention score and value
  products, softmax, norms and the loss are not quantized.
- **GEMM (primary path, every cell).** Decoded operands q × s_block are
  materialised in FP32 (exact for every cell: N1) and multiplied with
  `torch.matmul` with `torch.backends.cuda.matmul.allow_tf32 = True` (exact TF32
  inputs, FP32 accumulation as the tensor cores implement it); S3's tensor
  scales are applied to the FP32 output (y = s_ta × s_tb × GEMM); the result is
  cast to BF16. `allow_bf16_reduced_precision_reduction = False`. Both flags are
  asserted at start-up and written to every receipt.
- **Emulation-path control.** The NV-like cell (E2M1/S3) with decoded operands
  in BF16 (exact for this cell: N1) and a BF16 GEMM under PyTorch's default
  reduced-precision reduction; tensor scales in the epilogue as above.
- **Evaluation numerics.** Each run is evaluated with its own forward numerics
  (RTN quantization of X and W in blocks 1 to 5); the BF16-forward evaluation of
  the same weights is a secondary.

## Part A: Phase 0

### Phase 0, CPU (development Mac and orx cpu-doctor node; 0 GPU-h)

1. **Conformance.** For each grid, scale configuration and rounding mode
   (RTN; SR with injected R), exhaustive over all positive and negative finite
   BF16 inputs for every scale code that keeps x / s within the grid's range
   (E8M0 codes 2^−30 to 2^30, all UE4M3 codes, BF16 scales with exponents −30 to
   30), the project's reference quantizer must match gfloat 0.5.2 bit for bit;
   element and scale encodes and decodes also match ml_dtypes 0.6.0
   (float4_e2m1fn, float8_e4m3fn, float8_e8m0fnu). Where the two references
   disagree with each other, the disagreement is resolved by this file's pinned
   rule before any GPU run and logged.
2. **Metamorphic.** Q_E1M2(x; s) = Q_INT4(x; 4s) / 4 for every input away from
   the scale-range ends; Q(2^k x; 2^k s) = 2^k Q(x; s) for E8M0 scales.
3. **Containment.** For every cell, every decoded operand (all element × block
   scale products in the code ranges above, and 10^6 random tensors per cell,
   seed 42) is exactly representable in TF32; for the control path, in BF16.
4. **Ties.** Vectors with x / s exactly on a grid midpoint for non-power-of-two
   UE4M3 and BF16 scales (N1 found 602 in 103,047 in-range pairs): RNE result
   checked, and the reciprocal-multiply path shown to differ (30 of 103,047).
5. **SR unbiasedness.** For each grid, 4,096 test values stratified over bins
   and positions, 65,536 SR draws each: every per-value z-test at Bonferroni
   alpha 0.001 / 4,096 must pass and the aggregate mean bias must be below 1e-3
   ulp (aggregate SE at most 3.05e-5 ulp; a bias of 2.0e-4 ulp is detected with
   power 0.999; S1).

### Phase 0, GPU jobs (one H100 each)

- **J0 GPU conformance (cap 0.10 GPU-h).** The CPU suite's vectors through the
  GPU quantizers, eager and compiled: bit-identical to the CPU reference.
  GEMM-level check: for 1,000 random GEMMs per production shape and cell, the
  emulated output minus a float64 matmul of the same decoded operands satisfies
  |error| ≤ gamma_K × sum|a_k b_k| + 2^−133 elementwise, with
  gamma_K = K u / (1 − K u), u = 2^−23 (truncating accumulation), before the
  BF16 cast. Flags asserted.
- **J1 throughput, packing and smoke (cap 2.20 GPU-h).** Ten configurations
  (BF16, the eight FP4 cells, the control path), 200 compiled steps each at LR
  4e-3 (seed 1000), timed over steps 51 to 200; eager arms of 60 steps for BF16
  and NV-like; packing arms with 2 and 4 processes on one GPU for BF16 and
  NV-like. Records tok/s per process, compile time, startup time, peak memory,
  and whether any step produced NaN or Inf.
- **J2 resume (cap 0.45 GPU-h).** NV-like cell (SR on): 300 steps uninterrupted
  against 150 steps, checkpoint, and a fresh job resuming 150 steps, under
  deterministic algorithms; parameters, optimizer states and the per-step loss
  trajectory must be bit-identical.
- **J3 BF16 capture (cap 0.30 GPU-h).** 3,000 BF16 steps at LR 4e-3 (seed
  1000); at steps 500, 1,000, 2,000 and 3,000, for one batch of 8 sequences,
  capture X, W and dY of every quantized linear layer (about 3 GB, kept on the
  host).

### Phase 0 gates

- PG1 conformance (CPU items 1 and 2, J0 bit-identity): zero mismatches.
- PG2 containment (CPU item 3): 100% exact.
- PG3 GEMM bound (J0): zero violations.
- PG4 SR unbiasedness (CPU item 5): passes as stated.
- PG5 overhead: F = BF16 tok/s ÷ emulated tok/s (compiled, one process); if the
  largest F over the eight FP4 cells exceeds 4.0, verdict TRITON_GATE: a fused
  quantizer is written and reviewed under D7, and J1 reruns under a new
  version before Part B.
- PG6 resume (J2): bit-identical.
- PG7 smoke (J1): no NaN or Inf, and loss at step 200 below 8.0 nats for
  every configuration.

Any failure of PG1, PG2, PG3, PG4, PG6 or PG7 gives INSTRUMENT_FAIL: no
Part B. A fix is a reviewed code change; whether it is material is decided
before re-running, and a material change is a new experiment id.

### Numerics prediction (frozen before any Phase 1 run)

On J3's captured tensors, for each operand role (Fprop X and W, Dgrad dY and W,
Wgrad X and dY) and each of the eight cells, compute with the registered
quantizer: QSNR (dB), the relative magnitude bias, and the block crest factor
at B16 and B32, with and without a 32-point randomised Hadamard rotation
(reported only). Predicted cell score = mean over roles and capture steps of
QSNR, weighted equally. The prediction file records: the predicted ranking of
the eight cells; predicted signs of I_fmt, I_blk and I_iso computed from the
cell scores as (INT4: S_a − S_b) − (E2M1: S_a − S_b) with QSNR differences
sign-inverted to loss direction; and the per-role table. Its SHA-256 is
committed before Stage 1a starts. The registered directional predictions P2
(I_fmt > 0, I_blk > 0) stand whatever the captured tensors show; the frozen
file adds the data-calibrated ranking used by P6.

## Part B: Phase 1 design (registered now; runs only after Kevin's D24 ruling)

### Cells

| Cell | Grid | Scale configuration | Storage (b/element) |
|---|---|---|---:|
| E2M1/S1 (MX-like) | E2M1 | E8M0, B32 | 4.25 |
| E2M1/S2 | E2M1 | E8M0, B16 | 4.5 |
| E2M1/S3 (NV-like) | E2M1 | UE4M3 + FP32 tensor scale, B16 | 4.5 |
| E2M1/S5 | E2M1 | BF16, B32 | 4.5 |
| INT4/S1 | INT4 | E8M0, B32 | 4.25 |
| INT4/S2 | INT4 | E8M0, B16 | 4.5 |
| INT4/S3 | INT4 | UE4M3 + FP32 tensor scale, B16 | 4.5 |
| INT4/S5 | INT4 | BF16, B32 | 4.5 |
| BF16 | none | none | 16 |
| Control | E2M1/S3 on the BF16 path | as NV-like | 4.5 |

### Stages

- **Stage 1a.** BF16, MX-like and NV-like. LR sweep at seed 1000 over
  {1e-3, 2e-3, 4e-3, 8e-3, 1.6e-2}; if the lowest final validation loss is at an
  edge, one more point beyond that edge (factor 2). Tuned LR = the vertex of the
  parabola in log2 LR through the best point and its two neighbours, clamped to
  ±0.5 grid steps of the best point (the best point itself if a neighbour is
  missing or divergent). Then fresh seeds 42, 43, 44 at the tuned LR.
- **Gate G1.** On the 9 fresh runs, a randomized complete block analysis
  (configurations x seed blocks, residual df 4): C_anchor = mean L(MX-like) −
  mean L(NV-like); SE = sigma_hat × sqrt(2/3); 90% t-interval (df 4). G1 PASS iff
  L90(C_anchor) > 0 and C_anchor ≥ 2.5 × sigma_hat. Otherwise
  STOP_UNRESOLVED_AT_35M, reported with sigma_hat and C_anchor; Part B ends.
- **Stage 1b.** The six other FP4 cells. LR sweep at seed 1000 over
  {c/2, c, 2c}, with c the tuned LR of the reference configuration (MX-like for
  E2M1/S2, INT4/S1, INT4/S2; NV-like for E2M1/S5, INT4/S3, INT4/S5); up to two
  extension points beyond an edge; tuned LR as in Stage 1a; fresh seeds 42, 43,
  44. The control runs fresh seeds 42, 43, 44 at the NV-like tuned LR.
- **Stage 1c (conditional).** If the Stage 1b verdict is GRID_OR_INTERACTION or
  P2 is CONFIRMED for I_fmt, seeds 45 and 46 run for E2M1/S2, E2M1/S3, INT4/S2
  and INT4/S3 at their tuned LRs, and the verdict and P2 are recomputed with
  those four cells at five seeds (unbalanced RCBD by OLS). No claim is made from
  the three-seed reading alone.

### Endpoints

- Primary: final validation loss L (nats per token, own forward numerics) at
  step 18,311 on the 15M-token validation set.
- Secondary: BF16-forward validation loss of the same weights; divergence
  (NaN, Inf, or validation loss above 10 at any evaluation) for every sweep and
  fresh run; the LR profile and fitted curvature per configuration; the spike
  score on fresh runs (share of logged steps after warmup whose training loss or
  gradient norm is at least 7 standard deviations from the mean of the previous
  1,000 logged steps); loss trajectories.

### Analysis and decision rules

Randomized complete block design on the 8 FP4 cells x 3 fresh seeds (seed as
block, fixed in advance), residual df 14; 90% two-sided t-intervals (L90, U90).
Contrasts (positive means the first-named is worse):

- Delta_G = mean over S of L(INT4/S) − L(E2M1/S) (SE 0.408 sigma).
- C_blk = mean over grids of L(·/S1) − L(·/S2); C_fmt = L(·/S2) − L(·/S3);
  C_iso = L(·/S5) − L(·/S3) (SE 0.577 sigma each).
- I_blk = (INT4: S1 − S2) − (E2M1: S1 − S2); I_fmt = (INT4: S2 − S3) −
  (E2M1: S2 − S3); I_iso = (INT4: S5 − S3) − (E2M1: S5 − S3) (SE 1.155 sigma).
- D1 = C_fmt − 2 Delta_G (SE 1.000 sigma).
- The MXFP4-to-NVFP4 analogue split: C_anchor = C_blk(E2M1) + C_fmt(E2M1),
  with each step and the block share C_blk(E2M1) / C_anchor (Fieller interval)
  reported.

Verdict, in this precedence:

1. WITHIN_NOISE: omnibus F-test of the 8 cell means (7 df) has p > 0.10.
2. GRID_OR_INTERACTION: INTERACTION_PRESENT (the 3-df grid x scale interaction
   F-test has p < 0.05 and max |I| ≥ 0.5 |C_fmt|) or GRID_COMPARABLE
   (U90(D1) < 0).
3. PRIOR_SURVIVES: L90(D1) > 0, and for each of I_blk, I_fmt, I_iso,
   |I| + t(0.95, 14) × SE_I < C_fmt, and not INTERACTION_PRESENT.
4. SCALE_DOMINATES_INTERACTION_UNRESOLVED: L90(D1) > 0 otherwise.
5. INDETERMINATE otherwise.

Reported beside the verdict:

- P2: one-sided tests of I_fmt > 0 and I_blk > 0 with Holm's adjustment at
  alpha 0.05 (the larger z tested at 0.025, the other at 0.05 if the first
  rejects): CONFIRMED on rejection; REFUTED if U90 < 0; else UNRESOLVED.
- P5 EMULATION_SENSITIVE: C_emu = L(control) − L(NV-like), paired by seed, SE =
  sigma_hat × sqrt(2/3) with sigma_hat from the RCBD; sensitive if its 90%
  interval excludes 0 and |C_emu| ≥ 0.5 × max(|Delta_G|, |C_blk|, |C_fmt|,
  |C_iso|). Then every contrast with |C| < 2 |C_emu| is labelled
  emulator-conditional in every report.
- P6 NOT_PREDICTIVE: Spearman rho between the frozen predicted ranking and the
  observed cell means is below 0.619 (exact one-sided 5% critical value for
  n = 8; S1); PREDICTIVE otherwise.
- P7: divergence and spike tables; a Poisson GLM of fresh-run spike counts on
  grid, scale configuration and their interaction if at least 10 spikes occur
  in total, else NOT_ESTIMABLE.
- Variance fractions (omega-squared) for grid, scale configuration,
  interaction, seed and residual, with parametric-bootstrap intervals (B =
  2,000, seed 42); Shapiro-Wilk and Levene checks; within-block permutation
  versions of the omnibus and interaction F-tests (10,000 permutations, seed 42)
  as a sensitivity.

Divergence handling: a cell with a divergent fresh seed is labelled
UNSTABLE_AT_TUNED_LR; the factorial is analysed by OLS on the unbalanced
design only if every cell keeps at least 2 finite seeds, otherwise the verdict
is INCONCLUSIVE_UNSTABLE with the instability table. Sweep divergences count as
infinite loss for tuning.

Blinding: result files carry hashed cell ids; the verdict script runs on the
hashed table and the mapping is applied after it has written the verdict.

## Reported regardless of outcome

1. Phase 0: every gate's result with counts; F per cell (compiled and eager);
   packing gains; compile and startup times; memory; the J2 comparison; the
   numerics prediction file and its hash.
2. Phase 1: every run's configuration, final losses and trajectories; sweep
   tables and tuned LRs; G1's inputs and decision; every contrast, interaction
   and F-test with intervals; the verdict; P2, P5, P6, P7; variance fractions;
   assumption checks; permutation sensitivities; the MXFP4-to-NVFP4 analogue
   split; the BF16-forward secondary; the realised GPU-hours against the caps.
3. Negative and null results with the same prominence as positive ones.

## Statistics, power and simulation

S1 (`compute/power_sim.py` and `.json` in the bundle; 2,000 replicates per
setting; seeds 42 to 44; assumed distributions) simulates the whole sequence:
sweeps with LR-dependent loss (curvature 0.005 or 0.02 nats per squared
factor-of-2 step; configuration optima spread by 0.5 steps), G1, Stage 1b and
the verdicts, for sigma 0.002, 0.004 and 0.008 (0.002 is 2505.19115 Table 4
recomputed), seed correlation 0 or 0.5, and four truths at three effect sizes.
At sigma 0.004, seed correlation 0.5 and curvature 0.02:

- Null: P(G1) 0.02; if Stage 1b ran anyway, WITHIN_NOISE 0.88 and a false
  GRID_OR_INTERACTION 0.06; P2 false confirmation 0.02 (I_fmt), 0.03 (I_blk).
- Prior, additive (C_anchor 0.02, C_fmt 0.012, Delta_G 0.003): P(G1) 1.00;
  PRIOR_SURVIVES 0.53, INDETERMINATE 0.35, SCALE_DOMINATES_INTERACTION_UNRESOLVED
  0.07, false GRID 0.04.
- Numerics-predicted interaction (C_anchor 0.012, I_fmt 0.014): P(G1) 0.94;
  GRID_OR_INTERACTION 0.99; P2 I_fmt CONFIRMED 0.98, I_blk 0.68.
- Grid additive (Delta_G 0.010): P(G1) 0.85; GRID_OR_INTERACTION 1.00.
- With seed correlation 0, PRIOR_SURVIVES falls to 0.21 in the additive prior
  case; at sigma 0.008 most verdicts are INDETERMINATE or the gate stops.
- LR tuning bias averages 0.0001 to 0.0008 nats (95th percentile at most
  0.0032).
- 80%-power minimum detectable effects at 3 seeds (D1, two-sided alpha 0.10):
  Delta_G 1.01 sigma, each of C_blk, C_fmt and C_iso 1.44 sigma, each
  interaction 2.87 sigma, D1 2.49 sigma; at 5 seeds 0.79, 1.11, 2.22 and 1.93
  sigma.

Rules were revised once before registration after S1 showed that reading the
three interaction contrasts without an omnibus gate gave a false
GRID_OR_INTERACTION rate near 0.3 under the null, and that requiring
interaction intervals inside ±0.5 C_fmt could not be met at sigma 0.004 or
above. Both revisions are in the rules above.

## Compute caps (D22 counting)

- Part A: J0 0.10, J1 2.20, J2 0.45, J3 0.30; sum 3.05 GPU-h. Arithmetic in
  S2 (`compute/cost_model.py`): each cap is 1.2 times the high case (BF16 400k
  tok/s per process, F 4.0, compile 300 s, no packing gain), rounded up to 0.05
  GPU-h; J0 is fixed (about 7.6 times three 0.0044 GPU-h job-516 anchors).
  Central use about 1.0 GPU-h. The image build, data fetch and tokenization are
  CPU jobs.
- Part B: for each run type, GPU-seconds = [1.2e9 / (0.9 r) + 53e6 / (3 × 0.9 r)
  + o] / k, with r the J1 median per-process tok/s at the adopted packing k
  (k = 2 or 4 adopted only if its aggregate gain is at least 1.2; otherwise
  k = 1) and o the J1 startup plus compile time. The Part B cap is 1.2 times the
  sum over the maximum run counts: Stage 1a 24 runs plus 3 extensions, Stage 1b
  36 plus 12, control 3, Stage 1c 8. The 1.2 and 0.9 factors are fixed now and
  not revisited after J1 (D22). S2 projections (without the 0.9 factor): low
  with 2 per GPU, 17.9 GPU-h without extensions, cap value 29.4; central with 2
  per GPU, 45.0, cap 74.8; central with 1 per GPU, 68.1, cap 113.2; high, 194.4,
  cap 326.0. Stage 1a alone: 6.6 to 63.0.
- A job that reaches its cap stops; a sweep or fresh run cut by a cap is
  INCONCLUSIVE_INFRA for that run, and Part B's verdict is computed only if the
  rules above can still be applied.
- Fallback if Kevin admits less than the Part B cap: drop the S5 pair (C_iso,
  I_iso and their tests are then not reported); otherwise Part B waits.

## Infrastructure failures and exclusions

- A job that fails before step 1 is rerun once with the same seed; a crash
  after step 1 resumes from the latest checkpoint in a fresh job (at most two
  resumes per run, counted against the same cap); a third crash makes the run
  INCONCLUSIVE_INFRA.
- A run whose receipt shows a flag other than the registered TF32 and
  reduced-precision settings is excluded and rerun once; the exclusion is
  reported.
- No job is submitted while an S1a VM or GPU job is running; a running C5 job
  is not preempted for S1a under this file's authority (the program decides).

## Data rights

FineWeb-Edu is ODC-BY 1.0 (attribution in every report), derived from Common
Crawl. The tokenizer is Apache-2.0. Data text and captured tensors stay on the
host (`~/cotcodec-runs`) or in the private archive, never in this public
repository, which receives file ids, revisions, hashes, token counts, configs,
trajectories and metrics. No model weights are downloaded; trained 35M
checkpoints stay on the host and are not released.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: two independent references
   (gfloat, ml_dtypes), metamorphic and containment tests, a GEMM bound, an SR
   bias test, bit-identical resume, eager-versus-compiled identity.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot with its
   version history; OpenReview items are labelled abstract-only; ARITH 2025 is
   labelled UNVERIFIABLE_ACCESS.
3. Hallucinated experimental result: no number in this file is a result; N1,
   N2, D1, S1 and S2 are labelled computations, simulations and estimates with
   their scripts and outputs.
4. Shortcut reliance: the positive-control gate prevents reading noise as a
   factor effect; the omnibus gates prevent reading one contrast out of many.
5. Bug reframed as insight: an instrument failure gives INSTRUMENT_FAIL, not a
   finding; the emulation control bounds emulator-driven effects.
6. Methodology fabrication: every procedure names its code path and is checked
   at the pre-freeze audit against the harness.
7. Frame-lock: the owner's forecast below gives the null and stop outcomes
   substantial probability; H_sep and H_int are registered as rivals.

## Owner's prior forecast (not a decision input)

P(INSTRUMENT_FAIL after one fix round) about 0.1; P(TRITON_GATE) about 0.25;
P(G1 PASS) about 0.5; given G1, P(GRID_OR_INTERACTION) about 0.35,
P(PRIOR_SURVIVES) about 0.25, P(SCALE_DOMINATES_INTERACTION_UNRESOLVED or
INDETERMINATE) about 0.35, P(WITHIN_NOISE) about 0.05; P(P2 I_fmt CONFIRMED)
about 0.35, P(REFUTED) about 0.1; P(EMULATION_SENSITIVE) about 0.1.

## Freeze procedure

After the prerequisites, a fresh pre-freeze audit and Kevin's acceptance of
the design decisions:

```bash
uv run python scripts/preregister.py freeze c5-fp4-instability-v1 program/preregistrations/c5-fp4-instability-v1.md
uv run python scripts/preregister.py verify c5-fp4-instability-v1
```

Part B is re-audited after Phase 0 and before Kevin's D24 ruling; any change
to Part B after Phase 0 data exist is a new experiment id.

## Design decisions (for the owner's acceptance)

1. Scope: Phase 0 executable after freeze; Phase 1 design registered, admission under D24.
2. Model shape as in "Identity" (35M, 6 layers, d 384, vocabulary 32,000, untied).
3. Mistral-7B-v0.1 tokenizer at revision 27d67f1b.
4. FineWeb-Edu sample-10BT files 000 and 001 at revision 87f09149 (002 only if short); download needs Kevin's OK.
5. Validation split by document-id hash, 15M tokens; single-pass training stream.
6. Training recipe as in "Model training"; 1.2B tokens; no qk-norm, no z-loss.
7. Grids E2M1 and symmetric INT4 (15 codes each).
8. Scale configurations S1, S2, S3, S5; UE5M3 and E1M2 not in Phase 1.
9. Round-up absmax scale rule for every configuration; S3 with a current per-tensor FP32 scale.
10. True division; ties to even; SR with 24 random bits on dY only.
11. All three GEMMs of every linear layer in blocks 1 to 5 quantized; block 6, embeddings, head, attention products and norms not.
12. 1D blocks along each GEMM's reduction axis; no RHT.
13. Exact TF32-operand GEMM path with epilogue tensor scales for every cell; flags asserted.
14. Emulation-path control on the NV-like cell (BF16 decode and GEMM, default reduction).
15. CPU conformance against gfloat 0.5.2 and ml_dtypes 0.6.0.
16. Metamorphic, containment, tie and SR-bias tests as listed.
17. GEMM error bound with u = 2^-23 and gamma_K.
18. J0 to J3 contents and caps (3.05 GPU-h in total).
19. TRITON_GATE at F above 4.0.
20. Bit-identical resume under deterministic algorithms.
21. Numerics prediction from J3 tensors, frozen before Phase 1.
22. Phase 1 cells as tabled.
23. Stage 1a five-point LR grid {1e-3 to 1.6e-2}, one extension, parabolic refinement.
24. Gate G1: L90(C_anchor) > 0 and C_anchor ≥ 2.5 sigma_hat.
25. Stage 1b three-point sweeps centred on the reference tuned LR, two extensions.
26. Fresh seeds 42, 43, 44; sweep seed 1000; three Philox streams per seed.
27. Stage 1c: seeds 45, 46 on four cells when GRID_OR_INTERACTION or P2 CONFIRMED.
28. Primary endpoint and evaluation numerics as stated.
29. RCBD with seed blocks, residual df 14, 90% t-intervals.
30. Registered contrasts and D1.
31. Verdict precedence and thresholds (omnibus p 0.10, interaction F p 0.05, 0.5 |C_fmt|).
32. P2 with Holm at 0.05.
33. P5 emulation sensitivity rule.
34. P6 Spearman threshold 0.619.
35. P7 spike definition and the 10-spike NOT_ESTIMABLE rule.
36. Divergence handling and INCONCLUSIVE_UNSTABLE.
37. Blinding by hashed cell ids.
38. Part B cap formula with factors 1.2 and 0.9, packing adoption at a gain of 1.2.
39. Fallback order: drop the S5 pair first.
40. Data rights: ids, hashes and metrics only in the public repository.
41. G1 conditions on the MX-like vs NV-like anchor only; the alternative of adding INT4/S1 to Stage 1a (8 more Stage-1a runs, 6 of which Stage 1b would run anyway; S1: with a half-size additive grid effect P(G1) is 0.30 at sigma 0.004) is not adopted.
