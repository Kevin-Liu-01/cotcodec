# C5 v2: Phase 0 instrument and sigma-and-anchor probe for emulated FP4 training, and the Phase 1 training-time measurement of the grid x scale crossing at matched storage (c5-fp4-instability-v2)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single owner of the C5 repair run under program decision D68, on branch
`gauntlet/c5-fp4`. It supersedes `c5-fp4-instability-v1.md`, which is left
unedited; v2 is a new experiment id because the cell set, the token budget,
the gate, the registered test and the caps all change. Part A registers
Phase 0 for execution after a freeze. Its fixed caps (J0 to J3) sum to 2.80
GPU-h; its probe J4 has a formula cap set from J1's measurement and runs only
if Part A's caps then sum to at most 8.0 GPU-h (D20, D22), so Part A never
crosses the 8 GPU-h line. Part B registers the Phase 1 design before any data
exists. Its caps follow a formula fixed here and are computed from Phase 0's
measurement; they exceed 8 GPU-h, so Phase 1 runs only after Kevin's ruling
under D24 and a fresh pre-freeze audit of Part B. The design decisions at the
end (1 to 48) need the program owner's acceptance. No host job of any kind
runs while a Q2 job that the program protects is running or pending. The
proposal that argues and attacks this design is
`program/proposals/2026-10-10-c5-fp4-instability.md`; its evidence bundle is
`program/proposals/evidence/2026-10-10-c5-fp4-instability/` (v2 computations
under `compute/repair-d68/`).

## Relation to v1, to gauntlet wave 1 and to D68

Wave 1 (`program/gauntlet/2026-10-10-c5-fp4-instability.jsonl`, row 1) scored
54 and named four defects that D68 orders repaired. Each is repaired here:

1. **The mechanism was published and the registered test did not identify
   it.** The power-of-two-scale penalty on the uniform grid is Theorem 1 of
   arXiv 2510.25602 (the UE8M0 term 20 log10(rho), rho in [1, 2)), with the
   tensor-level grid-by-block interaction under E8M0 in the ARITH 2025 study
   (Insight 5, Fig. 9; Insight 3 for the scale-rounding rule). v2 claims none
   of that. Its contribution is the training-time measurement of the
   grid-by-scale crossing at matched storage, with one registered test that
   the design identifies: P2 on I_prec32, which compares an E8M0 block scale
   with a BF16 block scale at the same block size (32) and the same exponent
   range, so the two cells differ only in the scale's mantissa width. N3
   (`compute/repair-d68/numerics_v2.py`) shows that this contrast vanishes
   exactly when scale rounding is removed and is unchanged when UE4M3's range
   limit is removed, while v1's I_blk keeps 0.32 to 0.67 dB with exact scales
   and the matched-storage I_fmt moves by up to 1.5 dB with UE4M3's range.
   One cell pair is added (UE4M3+FP32/B32 for both grids) so the matched-storage
   crossing is measured at both block sizes and UE4M3's range is diagnosed by
   I_range32.
2. **Gate reuse biased the factorial.** The gate now runs on its own runs
   in Phase 0 (J4, probe seeds 2001 to 2003, never used in Phase 1), and every
   Phase 1 cell, including E2M1/S1 and E2M1/S3, runs on fresh seeds. No gate
   run enters any Phase 1 estimate. S1v2 replays v1's reuse on the same data
   and shows the bias there and its absence here.
3. **Phase 0 did not measure what Phase 1 needs.** J4 measures the seed-to-
   seed residual SD and the MX-like versus NV-like anchor gap at Phase 1's
   token budget, and Phase 1's seed count n is computed from them by a
   registered power rule.
4. **Phase 1's caps were miscomputed.** Wave 1's cap table omitted the 0.9
   factor of its own formula (its central single-process cap was 125.3 GPU-h,
   not 113.2) and its J0 cap was copied from another job. Every cap here is
   derived from its workload with the arithmetic shown in
   `compute/repair-d68/cost-model-v2.json`.

Also changed, from wave 1's other findings: Phase 1's token budget is 0.6B
(9,155 steps), so J4 can measure at Phase 1's budget inside 8 GPU-h; every FP4
cell gets the same LR protocol (a 3-point sweep centred on the BF16 tuned LR),
so tuning depth is no longer confounded with the grid; the emulation-path
control moves to INT4/S5, whose BF16 decode is inexact for 42.6% of products;
autocast is disabled around every quantized GEMM with a runtime dtype
assertion; TorchInductor's division is pinned to correctly rounded division;
E8M0's exponent floor is 2^-126 (2^-127 is an FP32 subnormal that a flush-to-
zero kernel turns into 0/0); deterministic mode is the same in J1, J2, J4 and
Phase 1; the SR rule is mapped to a named gfloat mode; PG5 separates
quantization overhead from the TF32-path cost; the BF16-forward loss of the
same weights is a registered attribution endpoint; P2 is decided on 95%
intervals because LR tuning adds cell-level variance (S1v2).

Kept from v1 and the dossier: the 35M Llama, FineWeb-Edu, the Mistral
tokenizer, RTN forward and SR on output gradients, the last block, embeddings
and head in BF16, 1D blocks along the reduction axis, no RHT, per-cell LR
tuning then fresh seeds, the exact decoded-operand TF32 GEMM path, the Phase 0
conformance and containment design, the kill line "fake-quant overhead above
4x needs a fused quantizer" (now applied to quantization overhead only), and
the verdict family "prior survives / grid or interaction / within noise" as a
secondary reading.

## Question

Part A: can an exact, conformant, resumable emulator of the registered FP4
formats run a 35M Llama on this host; at what throughput; what are the
seed-to-seed residual SD and the MX-like versus NV-like gap at Phase 1's token
budget; and what does a tensor-level analysis of the model's own tensors
predict for each grid-by-scale contrast?

Part B: in emulated FP4 training of that model, how does the element grid
(E2M1 against symmetric INT4) cross with the block-scale configuration at
matched storage, and does replacing a power-of-two block scale by a BF16 block
scale at the same block size and range help INT4 more than E2M1 in final
validation loss, as Theorem 1 of arXiv 2510.25602 predicts at tensor level?

Claim scope: `systems-pipeline` (training numerics under one declared
emulator, at 35M on 0.6B tokens). No claim about native FP4 kernels, speed,
energy, rounding modes, RHT, UE5M3 or larger models is licensed by any
outcome. No claim to the mechanism itself: it is published theory, and Part B
measures whether it reaches training loss.

## Identity

- Experiment id: `c5-fp4-instability-v2`.
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
  3fcf2dc69cd52503986276d3d2d26a8c356d0f2ea28a0de4fdbda8cf87755693); ODC-BY
  1.0. Both files are kept although a run reads only 0.6B training tokens,
  because the 1% validation split of one file would hold fewer than the
  registered 15M validation tokens.
- Image: the architecture image rebuilt at the freeze commit by
  `infra/slurm/host-single-node/build-architecture-image.sbatch` (CPU job); its
  digest and provenance receipt are recorded in the freeze record. The current
  image `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (torch 2.11.0+cu128, Triton 3.6.0) has no C5 code.
- Code revision: the freeze commit; harness files and their SHA-256 listed in
  the freeze record.
- Seeds: Phase 1 fresh seeds 42 to 41 + n, with n in {3, 4, 5, 6} set by the
  J4 rule (so at least 42, 43, 44); J4 probe seeds 2001, 2002, 2003 (used
  nowhere else); sweep seed 1000; J1, J2 and J3 seed 1000. Each seed s defines
  three counter-based Philox streams: initialisation (s, 0), data order (s, 1),
  stochastic rounding (s, 2) keyed by (step, layer, GEMM, operand). Simulation,
  bootstrap and CPU conformance sampling seed 42.

## Prerequisites before freeze (no GPU)

1. The data fetch (files 000 and 001, 4.31 GB) and the tokenizer files, as
   public licensed research downloads under D1, each
   recorded with source, revision, size and SHA-256, through a CPU Slurm job;
   then a CPU tokenization job. Both obey the host rule.
2. Harness (reviewed project code under D7): the model, AdamW and schedule
   driver, data loader with the split rule and a resumable cursor, the
   quantizers and emulated linear layer (eager and torch.compile paths),
   checkpoint and resume with all generator states, evaluation (own forward
   and BF16 forward), the throughput probe, tensor capture, the analysis and
   verdict scripts. The analysis script must reproduce `power_sim_v2.py`'s
   decisions on its synthetic replicates before any GPU job.
3. CPU conformance suite (section "Phase 0, CPU") passing on the development
   Mac against gfloat 0.5.2 and ml_dtypes 0.6.0 (pinned).
4. Manifests `experiments/manifests/c5-fp4-instability-v2/j0.yaml` to `j4.yaml` with `--dry-run` and `--test-only` passing through `scripts/submit_docker_research_job.py`.
5. A `kind: cpu-doctor` orx node running `scripts/run_fp4_quantizer_doctor.py`
   (the CPU suite plus N2v2 and N3 recomputed) through `scripts/orx_run.py`.
6. A fresh pre-freeze audit of this file against the harness.

## Model training (fixed for every run, Phase 1 and J4)

AdamW (beta1 0.9, beta2 0.95, epsilon 1e-8, weight decay 0.1 on matrices only),
global gradient-norm clipping 1.0, FP32 master weights and optimizer states,
BF16 autocast for non-quantized operations only (see "GEMM"); batch 64
sequences x 1,024 tokens = 65,536 tokens per step; 9,155 steps = 599,982,080
tokens; linear warmup over 183 steps (2%), cosine decay to 10% of peak.
Evaluation every 1,000 steps on the first 2M validation tokens and at the end
on the full 15M-token validation set, twice: with the run's own forward
numerics and with a BF16 forward of the same weights. Loss and gradient L2
norm logged every step. `torch.use_deterministic_algorithms(True)` and
`CUBLAS_WORKSPACE_CONFIG=:4096:8` in J1, J2, J4 and every Phase 1 run.

## Data

Validation documents: int(SHA-256(UTF-8 document id)[:8], 16) mod 100 = 0;
the validation set is the first 15,000,000 tokens of those documents in file
order. Training stream: all other documents of files 000 and 001, shuffled
once per data-order seed by a seeded permutation of documents, concatenated
and cut into 1,024-token sequences; a run reads the first 599,982,080 tokens of
its stream, a single pass with no document repeated. The data cursor
(document index, token offset) is checkpointed.

## Quantization and GEMM (the pinned specification)

- **Grids.** E2M1: {0, ±0.5, ±1, ±1.5, ±2, ±3, ±4, ±6}, q_max 6 (15 distinct
  values). INT4: symmetric {−7, ..., 7}, q_max 7 (15 values; −8 unused).
- **Scale configurations.** S1: E8M0 block scale, B = 32 (4.25 b/element).
  S2: E8M0, B = 16 (4.5 b). S3: UE4M3 block scale (positive E4M3fn, 2^−9 to
  448) with an FP32 per-tensor scale, B = 16 (4.5 b plus 32 bits per tensor).
  S4: UE4M3 with an FP32 per-tensor scale, B = 32 (4.25 b plus 32 bits per
  tensor). S5: BF16 block scale, B = 32 (4.5 b). Blocks are 1D along each
  GEMM's reduction axis.
- **Scale rule (every configuration).** Per block, amax = max |x| in FP32.
  S1, S2: s = 2^ceil(log2(amax / q_max)), exponent clamped to [−126, 127].
  S5: s = amax / q_max computed in FP32, rounded up to the next BF16 value and
  clamped below at 2^−126. S3, S4: s_t = amax_tensor / (q_max × 448) in FP32,
  current (not delayed) per GEMM operand per step; s_b = (amax / q_max) / s_t
  rounded up to the next UE4M3 value, clamped to [2^−9, 448]. An all-zero block
  gets the smallest scale code of its format (2^−126 for E8M0 and BF16) and
  zero elements. No element can exceed q_max, so saturation never triggers; it
  is still implemented (clamp) and tested.
- **Element rounding.** y = x / s by correctly rounded FP32 division (never a
  reciprocal multiply); on the compiled path `TORCHINDUCTOR_EMULATE_DIVISION_ROUNDING=1`
  (torch 2.11 `config.eager_numerics.division_rounding`, which emits `div_rn`)
  is set and asserted, because Inductor otherwise lowers FP32 division to the
  approximate `div.full`. RTN: round to the nearest grid value, ties to the
  even code (E2M1: the code whose mantissa bit is 0; INT4: the even integer).
  SR: with frac the position of |y| between its two neighbouring grid values lo
  and hi, round to hi iff R < floor(frac × 2^24), R uniform on {0, ..., 2^24 −
  1} from the SR stream. The gfloat reference is `RoundMode.StochasticFastest`
  with 24 random bits and srbits = 2^24 − 1 − R, which is the same rule.
- **Which tensors.** All three GEMMs of every linear layer (QKV, output,
  gate, up, down) in blocks 1 to 5: Fprop (X, W: RTN), Dgrad (dY: SR, W: RTN),
  Wgrad (X: RTN, dY: SR). Block 6, embeddings, LM head, attention score and value
  products, softmax, norms and the loss are not quantized.
- **GEMM (primary path, every cell).** Decoded operands q × s_block are
  materialised in FP32 (exact for every cell: N1; block size does not change
  the decoded set, so S4 inherits S3's result) and multiplied with
  `torch.matmul` inside `torch.autocast(device_type="cuda", enabled=False)`
  with `torch.backends.cuda.matmul.allow_tf32 = True` (exact TF32 inputs, FP32
  accumulation as the tensor cores implement it); S3 and S4's tensor scales are
  applied to the FP32 output (y = s_ta × s_tb × GEMM); the result is cast to
  BF16. `allow_bf16_reduced_precision_reduction = False`. The input dtypes of
  all three quantized GEMMs are asserted FP32 at step 1 and every 1,000 steps;
  the flags and the assertion results are written to every receipt.
- **Emulation-path control.** INT4/S5 with decoded operands cast to BF16
  (inexact for 42.6% of decoded products: N1) and a BF16 GEMM under PyTorch's
  default reduced-precision reduction; input dtypes asserted BF16.
- **Evaluation numerics.** Own forward (RTN quantization of X and W in blocks
  1 to 5) for the primary endpoint; BF16 forward of the same weights for the
  attribution endpoint.

## Part A: Phase 0

### Phase 0, CPU (development Mac and orx cpu-doctor node; 0 GPU-h)

1. **Conformance.** For each grid, scale configuration and rounding mode
   (RTN; SR with injected R), over all positive and negative finite BF16
   inputs and: every E8M0 code (2^−126 to 2^127); every UE4M3 code; BF16
   scales with all 128 significands at exponents −126, −100, −30, −1, 0, 1, 30,
   100 and 127 (scale exponents in between are covered by the metamorphic test
   below), the project's reference quantizer must match gfloat 0.5.2 bit for
   bit; element and scale encodes and decodes also match ml_dtypes 0.6.0
   (float4_e2m1fn, float8_e4m3fn, float8_e8m0fnu). Where the two references
   disagree, the disagreement is resolved by this file's pinned rule before any
   GPU run and logged.
2. **Metamorphic.** Q_E1M2(x; s) = Q_INT4(x; 4s) / 4 for every input away from
   the scale-range ends; Q(2^k x; 2^k s) = 2^k Q(x; s) for E8M0 and BF16 scales
   over every exponent k that keeps both in range (10^5 random inputs per k,
   seed 42).
3. **Containment.** For every cell, every decoded operand (all element × block
   scale products in the code ranges above, and 10^6 random tensors per cell,
   seed 42) is exactly representable in TF32; for the control path, the
   BF16-rounded operand is what the control registers.
4. **Ties.** Vectors with x / s exactly on a grid midpoint for non-power-of-two
   UE4M3 and BF16 scales (N1 found 602 in 103,047 in-range pairs): RNE result
   checked, and the reciprocal-multiply path shown to differ (30 of 103,047).
5. **SR unbiasedness.** For each grid, 4,096 test values stratified over bins
   and positions, 65,536 SR draws each: every per-value z-test at Bonferroni
   alpha 0.001 / 4,096 must pass and the aggregate mean bias must be below 1e-3
   ulp (aggregate SE at most 3.05e-5 ulp; a bias of 2.0e-4 ulp is detected with
   power 0.999).

### Phase 0, GPU jobs (one H100 each)

- **J0 GPU conformance (cap 0.25 GPU-h).** The CPU suite's vectors through
  the GPU quantizers, eager and compiled (division flag set): output hashes per
  (cell, mode, scale code) identical to the CPU reference's. GEMM-level check:
  for 50 random GEMMs per distinct production shape (9 shapes at 65,536 tokens)
  and cell, the emulated output minus an FP64 matmul of the same decoded
  operands satisfies |error| ≤ gamma_K × sum|a_k b_k| + 2^−133 elementwise,
  with gamma_K = K u / (1 − K u), u = 2^−23 (truncating accumulation), before
  the BF16 cast. A zero-block test (all-zero blocks in every operand role)
  checks that no NaN appears on the compiled path. Flags asserted. Workload
  arithmetic in S2v2: high case 712 s.
- **J1 throughput and smoke (cap 1.85 GPU-h).** Thirteen compiled
  configurations (BF16; a TF32-operand baseline with no quantization; the ten
  FP4 cells; the control path), 120 steps each at LR 4e-3 (seed 1000), timed
  over steps 21 to 120, deterministic mode as in Phase 1; eager arms of 60
  steps for BF16 and NV-like; one packing arm with 2 processes of NV-like on
  one GPU. Records tok/s per process, compile and startup time, peak memory,
  and any NaN or Inf.
- **J2 resume (cap 0.40 GPU-h).** NV-like cell (SR on): 200 steps
  uninterrupted against 100 steps, checkpoint, and a fresh job resuming 100
  steps, deterministic mode; parameters, optimizer states and the per-step loss
  trajectory must be bit-identical.
- **J3 BF16 capture (cap 0.30 GPU-h).** 3,000 BF16 steps at LR 4e-3 (seed
  1000); at steps 500, 1,000, 2,000 and 3,000, for one batch of 8 sequences,
  capture X, W and dY of every quantized linear layer (about 3 GB, kept on the
  host).
- **J4 sigma-and-anchor probe (formula cap, at most 5.20 GPU-h).** Only after
  PG1 to PG7 pass and the numerics prediction is frozen. MX-like (E2M1/S1) and
  NV-like (E2M1/S3), each on probe seeds 2001, 2002 and 2003 (6 runs), the full
  Phase 1 recipe (9,155 steps) at the fixed LR 4e-3. Cap = 1.2 × Σ over the six
  runs of [599,982,080 / (0.9 r) + 48,000,000 / (3 × 0.9 r) + o] / k GPU-
  seconds, with r the J1 median per-process tok/s of that configuration at the
  adopted packing k and o its J1 startup plus compile time. J4 runs only if
  2.80 + its cap ≤ 8.0 GPU-h; otherwise PROBE_OVER_LINE: J4 is not run and goes
  to Kevin with Part B as its first step. At the cost model's central case the
  cap is 4.82 GPU-h (Part A total 7.62); J4 fits whenever the emulated
  per-process throughput is at least about 277,000 tok/s (o = 130 s).

### Phase 0 gates

- PG1 conformance (CPU items 1 and 2, J0 hash identity): zero mismatches.
- PG2 containment (CPU item 3): 100% exact.
- PG3 GEMM bound and zero blocks (J0): zero violations, no NaN.
- PG4 SR unbiasedness (CPU item 5): passes as stated.
- PG5 overhead: F_total = BF16 tok/s ÷ emulated tok/s and F_quant = TF32-
  baseline tok/s ÷ emulated tok/s (compiled, one process), per FP4 cell. If the
  largest F_total exceeds 4.0 and the largest F_quant exceeds 2.0, verdict
  TRITON_GATE: a fused quantizer is written and reviewed under D7 and J1 reruns
  under a new version before J4. If F_total exceeds 4.0 with F_quant at most
  2.0, verdict TF32_PATH_COST: the cost is the exact path itself, no fused
  quantizer is written, and the formulas carry it (J4 may then not fit).
- PG6 resume (J2): bit-identical.
- PG7 smoke (J1): no NaN or Inf, loss at step 120 below 8.0 nats for every
  configuration, and every dtype assertion true.

Any failure of PG1, PG2, PG3, PG4, PG6 or PG7 gives INSTRUMENT_FAIL: no J4 and
no Part B. A fix is a reviewed code change; whether it is material is decided
before re-running, and a material change is a new experiment id.

### Numerics prediction (frozen before J4)

On J3's captured tensors, for each operand role (Fprop X and W, Dgrad dY and W,
Wgrad X and dY) and each of the ten cells, compute with the registered
quantizer: whole-tensor QSNR (dB), per-row QSNR averaged over rows (rows are
tokens for activations and gradients, output channels for weights), the
relative magnitude bias, the block crest factor at B16 and B32, and for S3 and
S4 the share of blocks whose UE4M3 scale is subnormal (below 2^−6) or clamped
at 2^−9; with and without a 32-point randomised Hadamard rotation (reported
only). Predicted cell score = mean over roles and capture steps of whole-tensor
QSNR, weighted equally (the per-row version is reported). The prediction file
records: the predicted ranking of the ten cells; every registered contrast in
QSNR units (loss direction) and as noise-power ratios to the anchor; the
per-role table; the UE4M3 shares. Its SHA-256 is committed before J4 starts.
P2's direction (I_prec32 > 0, Theorem 1's prediction) stands whatever the
tensors show; the frozen file adds the data-calibrated sign and size reported
beside P2, taken from the noise-power version (dB and noise-power contrasts
can disagree in sign for heavy-tailed blocks, N2v2, and a first-order loss
response is linear in noise power), and the ranking used by P6.

### Probe decision (after J4; gate G1 and the Phase 1 seed count)

On J4's six runs, a randomized complete block analysis (2 configurations ×
3 probe-seed blocks, residual df 2): C0 = mean over seeds of L(MX-like) −
L(NV-like); sigma0 = SD of the three paired differences ÷ sqrt(2) (the
residual SD after seed blocks, the same quantity Phase 1's analysis
estimates); SE0 = sigma0 × sqrt(2/3).

- **G1.** PASS iff L90(C0) > 0, that is C0 / SE0 > t(0.95, 2) = 2.920
  (equivalently C0 ≥ 2.384 sigma0). Otherwise STOP_UNRESOLVED_AT_35M: Part B
  is not requested; the report gives C0, sigma0 and their intervals.
- **Seed count.** n = the smallest value in {3, 4, 5, 6} whose 80%-power
  minimum detectable effect for an interaction contrast (sum of squared
  coefficients 4, one-sided 2.5%, df 9(n − 1)) is at most C0: n = 3 if
  C0 ≥ 3.421 sigma0, 4 if ≥ 2.907, 5 if ≥ 2.576, 6 if ≥ 2.338 (D1v2). Because
  G1 needs C0 ≥ 2.384 sigma0, every G1 pass gets n ≤ 6; STOP_UNDERPOWERED is
  kept as a guard.
- **Calibration of the prediction.** kappa = C0 ÷ (the frozen anchor's
  noise-power difference); every registered contrast's predicted size in nats
  is kappa × its frozen noise-power difference. Reported beside the Part B
  estimates (observed ÷ predicted); not decision-bearing.
- **Instability.** If any J4 run diverges (NaN, Inf, or validation loss above
  10), G1 is not evaluable: PROBE_UNSTABLE, reported to Kevin with Part B and
  the divergence table.
- **Disclosure.** J4 compares the two configurations at one LR, so C0
  includes any difference in their optimal LRs. That is a real difference at a
  common LR; S1v2 models it. Phase 1 re-tunes every cell and never uses J4's
  runs.

## Part B: Phase 1 design (registered now; runs only after Kevin's D24 ruling)

### Cells

| Cell | Grid | Scale configuration | Storage (b/element) |
|---|---|---|---:|
| E2M1/S1 (MX-like) | E2M1 | E8M0, B32 | 4.25 |
| E2M1/S2 | E2M1 | E8M0, B16 | 4.5 |
| E2M1/S3 (NV-like) | E2M1 | UE4M3 + FP32 tensor scale, B16 | 4.5 |
| E2M1/S4 | E2M1 | UE4M3 + FP32 tensor scale, B32 | 4.25 |
| E2M1/S5 | E2M1 | BF16, B32 | 4.5 |
| INT4/S1 | INT4 | E8M0, B32 | 4.25 |
| INT4/S2 | INT4 | E8M0, B16 | 4.5 |
| INT4/S3 | INT4 | UE4M3 + FP32 tensor scale, B16 | 4.5 |
| INT4/S4 | INT4 | UE4M3 + FP32 tensor scale, B32 | 4.25 |
| INT4/S5 | INT4 | BF16, B32 | 4.5 |
| BF16 | none | none | 16 |
| Control | INT4/S5 on the BF16 path | as INT4/S5 | 4.5 |

Matched storage holds within each block size: S1 and S4 at 4.25 b, S2 and S3
at 4.5 b. S5 differs from S1 only in the scale's mantissa (0 against 7 bits)
and in storage; it shares S1's block size and exponent range. The model with
grid, block, scale family and all their identifiable interactions has rank 10
of 10 (D1v2).

### Steps

- **B1.** BF16 LR sweep at seed 1000 over {1e-3, 2e-3, 4e-3, 8e-3, 1.6e-2};
  if the lowest final validation loss is at an edge, one more point beyond that
  edge (factor 2). Tuned LR c = the vertex of the parabola in log2 LR through
  the best point and its two neighbours, clamped to ±0.5 grid steps of the
  best point (the best point itself if a neighbour is missing or divergent).
- **B2.** Every FP4 cell: LR sweep at seed 1000 over {c/2, c, 2c}; up to two
  extension points beyond an edge; tuned LR as in B1. The same protocol for
  both grids. The control runs at INT4/S5's tuned LR.
- **B3.** Fresh seeds 42 to 41 + n (n from J4) for every FP4 cell, BF16 and
  the control, at their tuned LRs.

### Endpoints

- Primary: final validation loss L (nats per token, own forward numerics) at
  step 9,155 on the 15M-token validation set.
- Attribution: BF16-forward validation loss of the same final weights.
- Secondary: divergence (NaN, Inf, or validation loss above 10 at any
  evaluation) for every sweep and fresh run; the LR profile and fitted
  curvature per cell; the spike score on fresh runs (share of logged steps after
  warmup whose training loss or gradient norm is at least 7 standard deviations
  from the mean of the previous 1,000 logged steps); loss trajectories.

### Analysis and decision rules

Randomized complete block design on the 10 FP4 cells × n fresh seeds (seed as
block, fixed in advance), residual df 9(n − 1). Contrasts (positive means the
first-named is worse; SE in units of the residual SD sigma at n seeds):

- I_prec32 = (INT4: S1 − S5) − (E2M1: S1 − S5), SE 2 sigma / sqrt(n). The
  registered test P2.
- I_fmt16 = (INT4: S2 − S3) − (E2M1: S2 − S3) and I_fmt32 = (INT4: S1 − S4) −
  (E2M1: S1 − S4), the matched-storage crossings (SE 2 sigma / sqrt(n) each);
  I_fmt_bar their mean.
- I_blk_E8 = (INT4: S1 − S2) − (E2M1: S1 − S2) and I_blk_UE = (INT4: S4 − S3) −
  (E2M1: S4 − S3), the grid-by-block (crest-factor) interactions under each
  scale family; I3 = I_fmt32 − I_fmt16 = I_blk_E8 − I_blk_UE.
- I_range32 = (INT4: S4 − S5) − (E2M1: S4 − S5), the UE4M3-against-BF16 scale
  interaction at B32.
- Delta_G = mean over the five configurations of L(INT4/S) − L(E2M1/S);
  C_fmt_bar = mean over grids of [(S2 − S3) + (S1 − S4)] / 2; C_prec32 = mean
  over grids of (S1 − S5); D1 = C_fmt_bar − 2 Delta_G.
- The anchor's split: C_anchor = L(E2M1/S1) − L(E2M1/S3) = [S1 − S4] + [S4 − S3]
  (scale step at B32, then block step under UE4M3) = [S1 − S2] + [S2 − S3]
  (block step under E8M0, then scale step at B16), each with intervals.

**P2 (the registered identified test).** Decided on the 95% interval of
I_prec32 (t at 0.975, df 9(n − 1)):

- CONFIRMED if L95 > 0 (one-sided 2.5%);
- REFUTED if U95 < 0;
- ABSENT if neither, and −C0 < L95 and U95 < C0 (the interaction is smaller
  than the anchor gap J4 measured, in both directions);
- UNRESOLVED otherwise.

The 95% level, not 90%, is registered because per-cell LR tuning adds
cell-level variance the seed residual cannot see: S1v2 shows 90% intervals of
I_prec32 covering 0.84 to 0.86 in the flatter LR regime (curvature 0.005),
with false confirmation up to 0.09 given GO, against 95% coverage of 0.88 to
0.95 and false confirmation of at most 0.05 at 95%. The 90% reading is
reported beside it.

Beside P2: the frozen calibrated prediction for I_prec32 (sign and size) and
the attribution label. **Attribution.** For a CONFIRMED or REFUTED P2, the same
test is run on the BF16-forward endpoint: IN_WEIGHTS if it reaches the same
verdict there; FORWARD_SHARE_NOT_EXCLUDED otherwise (a small-model FP4 gap can
sit mostly in forward-pass rounding: OpenReview eEicXkAWDk, abstract).

**Range rule (matched-storage readings).** I_fmt16, I_fmt32 and I_fmt_bar are
labelled RANGE_EXPOSED, and are reported as the matched-storage crossing
including UE4M3 range effects rather than as scale-precision effects, if (a)
in any operand role the frozen prediction's share of UE4M3 blocks with
subnormal or clamped scales exceeds 1% (N2v2: 0.25% at a per-token log-SD of
1.5, 33% at 2.5), or (b) the 95% interval of I_range32 excludes 0. P2 does
not involve UE4M3 and is not affected by this rule.

**Secondary verdict (the prior generalised; 90% intervals), in this
precedence:**

1. WITHIN_NOISE: the omnibus F-test of the 10 cell means (9 df) has p > 0.10.
2. GRID_OR_INTERACTION: INTERACTION_PRESENT (the 4-df grid × configuration
   F-test has p < 0.05 and max |I| over {I_prec32, I_fmt16, I_fmt32, I_blk_E8,
   I_blk_UE} ≥ 0.5 |C_fmt_bar|) or GRID_COMPARABLE (U90(D1) < 0).
3. PRIOR_SURVIVES: L90(D1) > 0, and for each of those five interactions
   |I| + t(0.95, df) × SE_I < C_fmt_bar, and not INTERACTION_PRESENT.
4. SCALE_DOMINATES_INTERACTION_UNRESOLVED: L90(D1) > 0 otherwise.
5. INDETERMINATE otherwise.

**Reported beside the verdicts:**

- P5 EMULATION_SENSITIVE: C_emu = L(control) − L(INT4/S5), paired by seed,
  SE = sigma_hat × sqrt(2/n); sensitive if its 95% interval excludes 0 and
  |C_emu| ≥ 0.5 × max(|Delta_G|, |C_fmt_bar|, |C_prec32|). Then every contrast
  with |C| < 2 |C_emu| is labelled emulator-conditional in every report.
- P6 NOT_PREDICTIVE: Spearman rho between the frozen predicted ranking and the
  observed cell means is below 0.564 (exact one-sided 5% critical value
  for n = 10, S1v2); PREDICTIVE otherwise.
- P7: divergence and spike tables; a Poisson GLM of fresh-run spike counts on
  grid, configuration and their interaction if at least 10 spikes occur in
  total, else NOT_ESTIMABLE.
- Every contrast above with 90% and 95% intervals, observed ÷ calibrated
  prediction, and the anchor's two splits.
- Variance fractions (omega-squared) for grid, configuration, interaction,
  seed and residual, with parametric-bootstrap intervals (B = 2,000, seed 42);
  Shapiro-Wilk and Levene checks; within-block permutation versions of the
  omnibus and interaction F-tests (10,000 permutations, seed 42) as a
  sensitivity.

Divergence handling: a cell with a divergent fresh seed is labelled
UNSTABLE_AT_TUNED_LR; the factorial is analysed by OLS on the unbalanced
design only if every cell keeps at least 2 finite seeds, otherwise every
verdict is INCONCLUSIVE_UNSTABLE with the instability table. Sweep divergences
count as infinite loss for tuning.

Blinding: result files carry hashed cell ids; the verdict script runs on the
hashed table and the mapping is applied after it has written the verdicts.

## Reported regardless of outcome

1. Phase 0: every gate's result with counts; F_total and F_quant per cell
   (compiled and eager); the packing gain; compile and startup times; memory;
   the J2 comparison; the numerics prediction file and its hash; J4's C0,
   sigma0, intervals, G1, n and kappa, or PROBE_OVER_LINE with the computed cap.
2. Phase 1: every run's configuration, final losses (both endpoints) and
   trajectories; sweep tables and tuned LRs; every contrast, interaction and
   F-test with intervals; P2 with its attribution and calibrated prediction;
   the range rule's inputs and label; the secondary verdict; P5, P6, P7;
   variance fractions; assumption checks; permutation sensitivities; the
   realised GPU-hours against the caps.
3. Negative and null results with the same prominence as positive ones.

## Statistics, power and simulation

S1v2 (`compute/repair-d68/power_sim_v2.py` and `power-sim-v2.json`; 4,000
replicates per setting; seeds [42, 43, 44, j]; assumed distributions)
implements this file's rules end to end: J4 with LR offsets at the common LR,
G1 and the seed-count rule, the B1 and B2 sweeps with LR-dependent loss
(curvature 0.005 or 0.02 nats per squared factor-of-2 step; BF16 optimum and
FP4 family offset each SD 0.5 steps, per-cell spread SD 0.25), B3, the RCBD,
P2, the range flag and the secondary verdicts; for sigma 0.002, 0.004 and
0.008 (per-run SD; 0.002 is 2505.19115 Table 4 recomputed), seed correlation 0
or 0.5, and nine truths at three effect sizes.

Operating characteristics at sigma 0.004 and seed correlation 0.5 (cells
"LR curvature 0.005 / 0.02"; full grid in the json):

- Gate: correct decision (GO under a format effect, STOP under a null) 0.73
  to 0.99 across the seven non-null truths at their registered size, 0.77 to
  0.96 under the two nulls; under a tuned-LR null with LR spread, GO 0.08 to
  0.23 because J4 compares at one LR. Mean n given GO 3.0 to 3.9.
- P2 given GO, credited mechanism (anchor 0.011, I_prec32 0.012 nats):
  CONFIRMED 0.93 / 0.94; the whole path ends in a correct CONFIRMED 0.81 /
  0.69. Reversed (I_prec32 −0.008): REFUTED 0.66 / 0.67. With I_prec32 = 0
  and a crest-factor, UE4M3-range or additive grid effect present: falsely
  CONFIRMED 0.02 to 0.05, ABSENT 0.70 to 0.77; additive prior (anchor 0.020):
  ABSENT 0.92.
- Range flag given GO: 0.82 to 0.84 under the range truths, 0.05 to 0.13
  otherwise.
- 95% coverage of I_prec32 given GO: 0.91 to 0.95 (0.88 at worst across the
  grid); 90% coverage would be about 0.84 to 0.90 and false confirmation at 90% up to 0.09, the reason P2
  uses 95%.
- At sigma 0.002 the mechanism's path ends correct 0.86 to 0.99; at sigma
  0.008 GO falls to about 0.5 and CONFIRMED given GO to about 0.5 (J4's C0 is
  inflated in passing replicates, so n is set too small); wrong decisive
  verdicts stay at or below 0.08 in every reported cell.
- Gate reuse: replaying v1's reuse on the same data, the anchor is biased
  upward by up to 0.010 nats and covered 0.20 to 0.28 of the time under a
  null, and P2 is falsely REFUTED in 0.07 to 0.34 of gated replicates; with
  the independent probe, coverage 0.84 to 0.90 and false REFUTED 0.05 to 0.09
  at 90% (0.02 to 0.05 at the registered 95%).
- Secondary verdict: GRID_OR_INTERACTION 0.80 to 1.00 under every interaction
  truth whatever its source, 0.05 to 0.17 under a null; PRIOR_SURVIVES 0.52 /
  0.61 under the additive prior. It identifies nothing and is reported, not
  interpreted causally.
- Exact Spearman critical value for 10 cells: rho ≥ 0.564 (one-sided p
  0.048).

D1v2 (`compute/repair-d68/doe_v2.py`): standard errors at n seeds in sigma
units are 2/sqrt(n) for every interaction (1.155 at n = 3), 0.82 for I_fmt_bar
and C_anchor, 0.84 for D1, 0.37 for Delta_G; 80%-power minimum detectable
effects for a one-sided 2.5% test of an interaction are 3.42, 2.91, 2.58 and
2.34 sigma at n = 3, 4, 5 and 6.

## Compute caps (D22 counting)

- Part A fixed caps: J0 0.25, J1 1.85, J2 0.40, J3 0.30; sum 2.80 GPU-h. Each
  is 1.2 times its high-case workload (BF16 400k tok/s per process, F_total
  4.0, F_quant 2.0, compile 300 s, no packing gain), rounded up to 0.05 GPU-h:
  J0 712 s (start-up, ten quantizer compiles of 60 s, the vectors, the 12.5 s
  FP64 GEMM check, copies), J1 5,481 s, J2 1,192 s, J3 862 s (S2v2).
- J4: the formula cap above, at most 5.20 GPU-h; 2.07 at the low case, 4.82 at
  the central case, 14.31 at the high case (where it does not fit and
  PROBE_OVER_LINE applies). Part A never exceeds 8.0 GPU-h.
- Part B: for each run type (BF16, each FP4 cell, the control), GPU-seconds =
  [599,982,080 / (0.9 r) + 48,000,000 / (3 × 0.9 r) + o] / k, with r the J1
  median per-process tok/s at the adopted packing k (k = 2 adopted only if its
  measured aggregate gain is at least 1.2; otherwise k = 1) and o the J1
  startup plus compile time. Maximum run counts at seed count n: BF16 6 + n,
  FP4 10 × 5 + 10 n, control n. Part B cap = 1.2 × the sum. The 1.2 and 0.9
  factors are fixed now and not revisited after J1 (D22). S2v2 values (k = 1):
  low 31.2, 35.3, 39.3 and 43.4 GPU-h at n = 3 to 6; central 70.1, 79.2, 88.3
  and 97.4; high 201.4, 227.5, 253.5 and 279.6. Central with k = 2 (if J1
  measures the gain): 46.1 to 64.0. Expected use without extensions at the
  central case, n = 3, k = 1: 44.6 GPU-h. Worked example (central, k = 1): an
  FP4 run is 599,982,080 / (0.9 × 300,000) + 48,000,000 / (3 × 0.9 × 300,000)
  + 130 = 2,222 + 59 + 130 = 2,411 s = 0.670 GPU-h; a BF16 run 0.353; a
  control run 0.543; the n = 3 maximum is 9 × 0.353 + 80 × 0.670 + 3 × 0.543 =
  58.4 GPU-h, cap 70.1.
- A job that reaches its cap stops; a sweep or fresh run cut by a cap is
  INCONCLUSIVE_INFRA for that run, and Part B's verdicts are computed only if
  the rules above can still be applied.
- Fallback if Kevin admits less than the Part B cap: first drop the BF16
  fresh seeds and the control (P5 not reported; saves n × 0.896 GPU-h at the
  central case before the 1.2 factor), then the S2 pair (I_fmt16, I_blk_E8 and
  I3 lost; P2, I_fmt32, I_blk_UE and I_range32 kept; saves 2 × (5 + n) × 0.670);
  otherwise Part B waits.

## Infrastructure failures and exclusions

- A job that fails before step 1 is rerun once with the same seed; a crash
  after step 1 resumes from the latest checkpoint in a fresh job (at most two
  resumes per run, counted against the same cap); a third crash makes the run
  INCONCLUSIVE_INFRA.
- A run whose receipt shows a flag, division setting, deterministic setting
  or dtype assertion other than the registered ones is excluded and rerun once;
  the exclusion is reported.
- No job is submitted while a protected Q2 job is running or pending; a
  running C5 job is not preempted under this file's authority (the program
  decides).

## Data rights

FineWeb-Edu is ODC-BY 1.0 (attribution in every report), derived from Common
Crawl. The tokenizer is Apache-2.0. Data text and captured tensors stay on the
host (`~/cotcodec-runs`) or in the private archive, never in this public
repository, which receives file ids, revisions, hashes, token counts, configs,
trajectories and metrics. No model weights are downloaded; trained 35M
checkpoints stay on the host and are not released.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: two independent references
   (gfloat, ml_dtypes), metamorphic and containment tests, a GEMM bound, a
   zero-block test, an SR bias test, bit-identical resume, eager-against-
   compiled identity with the division flag, runtime dtype assertions; the
   analysis script must reproduce S1v2's decisions on synthetic replicates.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot with its
   version history; OpenReview items are labelled abstract-only; the ARITH 2025
   study was read in full from its open copy (NSF PAR, sha256 d1d5b8e3...).
3. Hallucinated experimental result: no number in this file is a result; N1,
   N2v2, N3, D1v2, S1v2 and S2v2 are labelled computations, simulations and
   estimates with their scripts and outputs.
4. Shortcut reliance: the probe gate prevents reading noise as a factor
   effect; P2 is a single pre-specified contrast; the omnibus gates prevent
   reading one secondary contrast out of many.
5. Bug reframed as insight: an instrument failure gives INSTRUMENT_FAIL, not a
   finding; the emulation control bounds emulator-driven effects on the cell
   where the common BF16 path is most inexact.
6. Methodology fabrication: every procedure names its code path and is checked
   at the pre-freeze audit against the harness.
7. Frame-lock: the mechanism is credited to its authors; the forecast below
   gives the stop, absent and unresolved outcomes substantial probability; the
   reversed and range-only alternatives are simulated.

## Owner's prior forecast (not a decision input)

P(INSTRUMENT_FAIL after one fix round) about 0.1; P(TRITON_GATE or
TF32_PATH_COST) about 0.2; P(PROBE_OVER_LINE) about 0.3; given J4 runs,
P(G1 PASS) about 0.55; given GO, P2 CONFIRMED about 0.4, ABSENT about 0.25,
REFUTED about 0.05, UNRESOLVED about 0.3; P(RANGE_EXPOSED) about 0.3;
P(EMULATION_SENSITIVE) about 0.1.

## Freeze procedure

After the prerequisites, a fresh pre-freeze audit and Kevin's acceptance of
the design decisions:

```bash
uv run python scripts/preregister.py freeze c5-fp4-instability-v2 program/preregistrations/c5-fp4-instability-v2.md
uv run python scripts/preregister.py verify c5-fp4-instability-v2
```

Part B is re-audited after Phase 0 and before Kevin's D24 ruling; any change
to Part B after Phase 0 data exist is a new experiment id.

## Design decisions (for the owner's acceptance)

1. Scope: Phase 0 (J0 to J4) executable after freeze; Phase 1 design registered, admission under D24.
2. Model shape as in "Identity" (35M, 6 layers, d 384, vocabulary 32,000, untied).
3. Mistral-7B-v0.1 tokenizer at revision 27d67f1b.
4. FineWeb-Edu sample-10BT files 000 and 001 at revision 87f09149, downloaded under D1.
5. Validation split by document-id hash, 15M tokens; single-pass training stream.
6. Training recipe as in "Model training"; 9,155 steps, 0.6B tokens (v1: 1.2B); no qk-norm, no z-loss.
7. Grids E2M1 and symmetric INT4 (15 codes each).
8. Scale configurations S1 to S5 (S4 new); UE5M3 and E1M2 not in Phase 1.
9. Round-up absmax scale rule for every configuration; S3 and S4 with a current per-tensor FP32 scale.
10. E8M0 and BF16-scale floor 2^-126; zero blocks get the smallest code.
11. Correctly rounded division with `TORCHINDUCTOR_EMULATE_DIVISION_ROUNDING=1`; ties to even; SR with 24 random bits on dY only, mapped to gfloat StochasticFastest with srbits = 2^24 - 1 - R.
12. All three GEMMs of every linear layer in blocks 1 to 5 quantized; block 6, embeddings, head, attention products and norms not.
13. 1D blocks along each GEMM's reduction axis; no RHT.
14. Exact TF32-operand GEMM path with epilogue tensor scales; autocast disabled around quantized GEMMs; dtype assertions; flags asserted.
15. Deterministic mode in J1, J2, J4 and Phase 1.
16. Emulation-path control on INT4/S5 (BF16 decode and GEMM, default reduction).
17. CPU conformance against gfloat 0.5.2 and ml_dtypes 0.6.0 over the stated code ranges.
18. Metamorphic, containment, tie and SR-bias tests as listed.
19. GEMM error bound with u = 2^-23 and gamma_K; 50 GEMMs per shape and cell; zero-block test.
20. J0 to J3 contents and caps (2.80 GPU-h in total), each derived from its workload.
21. PG5 with F_total and F_quant; TRITON_GATE at F_total above 4.0 with F_quant above 2.0; TF32_PATH_COST otherwise.
22. Bit-identical resume under deterministic algorithms.
23. Numerics prediction from J3 tensors (whole-tensor and per-row QSNR, UE4M3 shares), frozen before J4.
24. J4: MX-like and NV-like, probe seeds 2001 to 2003, fixed LR 4e-3, Phase 1 recipe.
25. J4 formula cap; J4 runs only if Part A stays at or below 8.0 GPU-h, else PROBE_OVER_LINE.
26. G1: L90(C0) > 0 at df 2.
27. Seed-count rule n in {3, 4, 5, 6} from C0 / sigma0 (thresholds 3.421, 2.907, 2.576, 2.338).
28. Calibration kappa reported, not decision-bearing.
29. PROBE_UNSTABLE on any divergent J4 run.
30. Phase 1 cells as tabled (10 FP4 cells, BF16, control).
31. B1 five-point BF16 sweep, one extension, parabolic refinement.
32. B2 three-point sweep centred on the BF16 tuned LR for every FP4 cell, two extensions.
33. Fresh seeds 42 to 41 + n; no Phase 1 run reuses a J4 or sweep run.
34. Primary endpoint own-forward loss; BF16-forward loss as the attribution endpoint.
35. RCBD with seed blocks, residual df 9(n - 1).
36. Registered contrasts as listed.
37. P2 on I_prec32, decided on 95% intervals: CONFIRMED, REFUTED, ABSENT (inside +-C0), UNRESOLVED.
38. Attribution labels IN_WEIGHTS and FORWARD_SHARE_NOT_EXCLUDED.
39. Range rule: 1% subnormal-or-clamped share in any role, or I_range32's 95% interval excluding 0.
40. Secondary verdict precedence and thresholds (omnibus p 0.10, interaction F p 0.05, 0.5 |C_fmt_bar|, 90% intervals).
41. P5 on the INT4/S5 control with the stated rule.
42. P6 Spearman threshold 0.564 for n = 10.
43. P7 spike definition and the 10-spike NOT_ESTIMABLE rule.
44. Divergence handling and INCONCLUSIVE_UNSTABLE.
45. Blinding by hashed cell ids.
46. Part B cap formula with factors 1.2 and 0.9, packing adoption at a gain of 1.2.
47. Fallback order: BF16 fresh seeds and control, then the S2 pair.
48. Data rights: ids, hashes and metrics only in the public repository.
