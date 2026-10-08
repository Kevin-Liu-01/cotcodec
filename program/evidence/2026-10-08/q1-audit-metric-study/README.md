# Q1 audit-metric study (D41 ii): where A1-A3 are vacuous, and a metric that is not

Branch `stage0/q1-audit-metric` (from main `65bc2e2`). CPU only: no GPU job of any
kind. No evaluation unit was read for analysis or recomputed (D28). The draft
registration is not edited. This is a design study for a successor Stage 0, not a
registered result. Every threshold below was fitted on the same S1-cal draws it is
evaluated on, as the registered calibration (section 6.1) also does; the
leave-one-problem-out column is the out-of-sample check.

## Summary

- **F1 is analytic and general.** Under the registered metric
  `e(x) = max_i |x_i - r_i| / (|r_i| + 1e-3 ||r||_inf)`, an all-zeros output scores
  exactly `1/(1+kappa) = 0.999` and a negated one `1.998`, on any finite reference.
  The TF32-admissible threshold `T = 16 max(e_ref)` reaches 1 whenever the TF32
  reference's error at a near-zero output exceeds about `kappa ||r||_inf / 16`.
  That happens for every matmul or convolution with sign-mixed weights, because
  their outputs always include elements near zero. Every nn.Linear and nn.Conv
  initialisation has sign-mixed weights, and so do sign-mixed A2 inputs on the L1
  matmuls. The normaliser is the defect, not M: no threshold separates a correct
  TF32 kernel from zeros on L2/46 A2/uniform8 (0.83 against 0.999).
- **Where (stored rows, inline arm, primary policy).** No admissible draw can
  reject zeros on L2/46, L2/52, L2/59 or L2/60. On L2/77 one draw can (T = 0.88).
  On L2/95 only A3/lead1 and lead5 can, and on L2/100 only A2/constrows, where cuBLAS
  or cuDNN happened not to use TF32. The L1 matmuls (L1/10, L1/18, L1/1) are vacuous
  only on the sign-mixed A2 draws (`randn`, `uniform8`). L2/87 is not vacuous only
  because cuDNN did not use TF32 for its 8-channel convolution; the emulation
  predicts T = 3.5-4.2 there. Strict-fp32 is never vacuous but rejects correct
  kernels: 95 stored rows of S1-cal substrates and identity controls on L2/46,
  L2/52, L2/60, L2/77 and L2/100, which run cuDNN in TF32 by PyTorch default.
- **The emulation is faithful.** A CPU TF32 emulation (operands rounded to TF32,
  exact products, fp32 accumulation) reproduces the stored cuBLAS/cuDNN TF32
  reference error: median ratio 0.996, 64 of 71 draws within 1.5x; inputs are
  bitwise identical on every `torch.rand` draw. The exception is cuBLAS on L1/18 (K = 8192), at 3.6x the RNE emulation and
  still 9x below truncation. cuDNN's TF32 rounds to nearest (truncation would give 0.58
  on L2/46, against the stored 0.176).
- **Candidates.** Seven metrics were evaluated on 139 CPU draws of 12 S1-cal problems
  (1,111 gross destroyed outputs, 376 emulated mutant-family outputs, 278 1%-level
  faults, 408 precision-boundary faults). The registered metric lets 520 of 1,015 gross
  destroyed outputs through on admissible draws. The Higham-style elementwise gauge
  (M3) and a gauge-floored registered metric (M6) fail too. A max-abs noise ratio (M1
  linf) and a blockwise L2 noise ratio (M2) each separate well, and their conjunction
  is clean.
- **Recommendation.** Reject if `rho_inf > 4` or `rho_block > 8` (TF32-admissible; 4
  and 16 under strict fp32). `rho_inf` is the max-abs error over the largest max-abs
  error of a yardstick of correct references, and `rho_block` is the largest
  block-L2 error over the block's yardstick noise. The yardstick is device fp32,
  device TF32, and emulated TF32 RNE, plus emulated TF32 truncation for candidates
  that call `tl.dot`. A draw is determinate only if a decoy battery scores at least 4.
  On the 139 draws this gives 0 false rejects of physical correct realizations, 0 of
  1,111 gross escapes, and 0 indeterminate draws. With the RNE yardstick, 3 of 376
  emulated mutants and 1 of 278 1% faults escape, all within 4x of legitimate TF32
  error. It needs no validity gate.
- **Next.** A successor Stage 0 needs an S1-cal-only GPU pilot of about 0.28 GPU-h
  (0.20 for the 8 re-pilot problems only; 0.57 with a 2x margin) that checks real
  kernels against the rule, with a pass rule written first (section 5).

## Data and the D28 filter

- **Stored journals** (byte copies of the host files; SHA-256 in
  `stored-characterisation.json`): jobs 474 (smoke), 518 (smoke, calibration,
  scoring), 548 (scoring), 713 (re-pilot, `ddbfbbf6...`, the hash the gauntlet
  recorded) and 752 (validation).
- **Kept: 2,570 rows.**
  - Tier 1 (S1-cal problems that host no S2 substrate, so no evaluation unit of any
    tier): all 2,084 rows of 713, 752's 194 re-pilot rows, and 518-calibration's 28
    rows (L1/15, L1/47, L2/52, L2/60).
  - Tier 2 (stored rows only, never recomputed): 752's 264 rows of the three
    KernelBench adversarial controls on L1/1. L1/1 is S1-cal but hosts an S2
    evaluation substrate.
- **Dropped: 1,908 rows.**
  - Every row of 518 and 548 scoring (962 and 886): the evaluation substrates L1/3,
    L2/3 and L2/74 and the Liger, tutorial-matmul and FlagGems units, with their
    mutants; the S1-eval problems; and L1/95's identity control, whose problem hosts
    the Liger unit.
  - 518 smoke (58 rows; L2/12 and L1/25 are S1-eval).
  - 474 smoke (2 rows; L1/19 hosts an S2 unit).
  - Counts by reason are in `stored-characterisation.json`.
- **CPU recomputation** (`cpu_study.py`, run by `run_cpu_study.sh`, 3.4 CPU-hours on
  an Apple M5 Max under torch 2.11.0) covers the 12 tier-1 problems only. The script
  refuses any problem outside S1-cal or hosting an S2 substrate.
  - For each registered A1/A2/A3 draw at replicate 42, the harness's own draw plan
    and reference constructor rebuild the inputs and weights.
  - Inputs drawn by `torch.rand` reproduce job 752's stored input fingerprints
    bitwise (A1, A3, and five of seven A2 distributions). `randn`-based draws differ
    only through the platform's normal sampler.
  - L2/46, L2/60 and L2/87 are evaluated on the first 32 samples of each draw, and
    L2/100 on the first 4. These problems are batch-independent: inputs are drawn at
    full batch and then sliced, so each output is an exact slice of the registered
    draw's output.
  - Draws: all five A1; A2 `randn`, `uniform8`, `spiky`, `ties` and `constrows`; A3
    `lead5`, `inner37` (`inner137` where the manifest has no `inner37`) and
    `allprime`. 139 draws in all.

## 1. F1 characterised (stored data)

**Mechanism.** For a finite reference with `||r||_inf > 0`, `e(0)` is attained at the
largest `|r_i|` and equals `1/(1+kappa) = 0.999001`; `e(-r) = 2/(1+kappa)`. The
primary threshold is `T = max(16 max(e(r32_dev), e(r32_cpu), e(r32_tf32)), 2^-20)`.
A draw therefore admits zeros iff `e_ref >= 0.0624`, and admits negation iff
`e_ref >= 0.125`.

TF32 rounds operands to a 10-bit mantissa, `u = 2^-11`. With sign-mixed weights
(every nn.Linear and nn.Conv init is symmetric about 0) or sign-mixed inputs, an
output is a cancelling sum. Its TF32 error scales with `u` times the magnitude of
the terms, `G_i = (|W||x|)_i`, not with `|r_i|`. Among millions of such outputs,
0.015-1.4% lie below `kappa ||r||_inf`, where the denominator is the floor
`kappa ||r||_inf`.

The registered metric's worst element sits there: at 1.4-27% of the floor on every
TF32 L2 problem in A1 draw 0 (`reg_argmax_rne` in `results.json`), with `G_inf / z_inf` from 1.8
to 29. So `e_tf32` is 0.066-0.24 on the stored A1 draws, and `T = 16 e_tf32` is 1.05
to 3.84. The L1 matmuls with `torch.rand` operands have no cancellation
(`G_inf / z_inf = 1`) and score `e_tf32` of about 5e-5. `kappa = 1e-3` is about 2u, so
the floor cannot absorb TF32 noise. Strict fp32 has `u = 2^-24`, which is why strict
T stays at 1e-3 to 0.15.

**Per problem** (inline arm, admissible A1-A3 rows; each row's own T, because the
cuDNN TF32 reference is nondeterministic across items on L2/100 and L2/77):

| Problem | Op class | Rows | TF32-adm. T | Rows admitting zeros / negation | Draws that can reject zeros | Strict T |
|---|---|---:|---|---|---|---|
| L1/10 | matmul 3D x 2D | 49 | 1e-6 to 3.44 | 6 / 6 (A2 randn, uniform8) | A1, other A2, A3 | 1e-6 to 0.011 |
| L1/18 | matmul, transposed | 35 | 1e-6 to 2.90 | 2 / 2 (A2 uniform8) | A1, other A2, A3 | 1e-6 to 0.014 |
| L1/15 | matmul + tril | 5 | 0.0047-0.0054 | 0 / 0 | A1 | 6e-5 to 7e-5 |
| L1/47 | sum (no matmul) | 5 | 4e-6 | 0 / 0 | A1 | 4e-6 |
| L2/59 | linear + swish | 14 | 1.05-2.14 | 14 / 6 | none | 0.0056-0.026 |
| L2/95 | linear + 5 post-ops | 25 | 0.0009-1.69 | 21 / 0 | A3/lead1, A3/lead5 only | 0.0009-0.018 |
| L2/87 | conv2d (8 ch) + mish | 25 | 0.0014-0.0063 | 0 / 0 (cuDNN did not use TF32) | all | same |
| L2/46 | conv2d + tanh + pool | 13 | 2.01-13.2 | 13 / 13 | none | 0.0046-0.014 |
| L2/52 | conv2d + gate + BN | 5 | 2.71-3.34 | 5 / 5 | none | 0.008-0.010 |
| L2/60 | convT3d + swish + GN | 5 | 1.77-2.26 | 5 / 3 | none | 0.0015-0.0018 |
| L2/77 | convT3d + BN + GAP | 30 | 0.88-3.84 | 27 / 6 | A2/uniform8 only (T = 0.88) | 0.004-0.15 |
| L2/100 | convT3d + clamp | 6 | 0.0047-3.73 | 5 / 5 | A2/constrows only (device used no TF32) | 0.0047-0.0067 |
| L1/1 (tier 2) | matmul | 45 | 1e-6 to 2.85 | 3 / 3 | A1, A2, A3 | 1e-6 to 0.011 |

**Correct against destroyed, on stored rows.**
- The closest registered-metric separation of a correct S1 substrate from zeros is
  1.21x (L2/46 A2/uniform8: e = 0.827 against 0.999), then 3.1x (L2/46 A2/ties) and
  4.2x (L2/77 A1). No threshold can separate these with a margin.
- Real destroyed outputs pass on the GPU. The KernelBench `zero_out` control (an
  all-zeros kernel, tier 2) is accepted by A2/uniform8 under TF32-admissible
  (T = 2.85).
- The L2/95 `plus2minus` mutant writes zeros over part of the output
  (e = 0.9989 on every A1 draw). It passes all 5 A1 draws and its admissible A2
  draw; only A3/inner37 (a crash, e = 3.8e22) and A4 reject it.
- The L1/10 `acc-minus` mutant (a negated output, e = 1.998) passes A2/randn and
  A2/uniform8.
- The L2/77 `const0to1` mutant scores like its parent; it looks equivalent at these
  shapes.
- Under the registered calibration rule, the S1-cal substrates need multipliers of
  at most 1.04 (L2/77). So M = 16 is never raised, and raising it could not help.

**Restriction instead of repair** (the registered metric, three-valued). If a row is
determinate only when zeros fail it with a 4x margin (`4T < 0.999`), then under
TF32-admissible:
- No determinate row remains on L2/46, L2/52, L2/59, L2/60 or L2/77.
- L2/95 and L2/100 keep one row each, both draws where the device did not use TF32.
- The L1 matmuls keep A1, A3 and their same-sign A2 draws, and L2/87 keeps everything.

The restricted registered audit is therefore unauditable on six of the eight L2
problems under the primary policy (`results.json`, `restriction`).

## 2. The CPU emulation and its check against stored GPU values

`tf32emu.TF32Mode` intercepts `mm`, `bmm`, `addmm`, `baddbmm` and `convolution` in an
fp32 forward, rounds the two main operands to TF32 (RNE, truncation, or stochastic)
and runs the op in fp32 with NNPACK off, so products are exact and accumulation is
fp32. The check covers draws where the device used TF32, with full-batch inputs
(`results.json`, `emulation_validation`):

- RNE emulation over the stored device TF32 error: median 0.996, 64 of 71 draws within
  1.5x and 66 within 2x. Examples: L2/46 A1 0.176 against 0.176, L2/60 0.133 against
  0.133, L1/15 0.000304 against 0.000303, L2/95 0.106 against 0.106.
- All seven outliers are L1/18: cuBLAS is 3.5-3.6x the emulation on the five A1
  draws and 1.6x on A3/inner37 (plausibly the tensor core's truncated accumulation at
  K = 8192), and on A2/constrows, whose inputs are not bitwise equal, the emulation is
  1.5x the device.
- Batch-sliced draws: 0.78-1.01 of the full-batch stored value, as expected for a
  maximum over a slice.
- CPU fp32 against device fp32: median 1.00, and often identical to three digits.
- The device did not use TF32 on L2/87 A1 or on the `ties` draws (exact inputs).

## 3. Candidate metrics

Every statistic is computed per draw against the fp64 oracle `r`. A *yardstick* `Y` is
a set of correct references; the rule is calibrated as the smallest power of two at
or above every correct realization's statistic (the registered M rule).

| Policy | Yardstick | Held-out correct realizations (false-reject test) |
|---|---|---|
| strict | fp32 | fp32 NNPACK Winograd (3x3 convolutions) |
| TF32, RNE (candidate does not call `tl.dot`) | fp32, TF32-RNE | TF32 stochastic rounding, fp32 Winograd |
| TF32, extended (candidate calls `tl.dot`) | fp32, TF32-RNE, TF32-RZ | TF32 stochastic rounding, fp32 Winograd |
| registered as is (for comparison) | fp32, TF32-RNE | TF32-RZ (13 of 286 falsely rejected: L1/10, L1/18, finding 18.3.6 reproduced on S1-cal) |

Stochastic rounding on A2/constrows is excluded from calibration. It rounds equal
values differently, which no TF32 unit does, and there it is 10-32x the
yardstick, depending on statistic and policy. Including it would raise
every TF32 threshold to 16-32 (`sr_on_constrows`).

The definitions:
- **REG**: the registered `e`, re-thresholded.
- **M1 l2**: `||x-r||_2 / max_Y ||y-r||_2` (dynamo `same()`'s RMSE ratio).
- **M1 linf**: `||x-r||_inf / max_Y ||y-r||_inf` (KernelOPT's rho).
- **M2**: blockwise, over blocks of 4096 consecutive elements:
  `max_b ||x_b-r_b|| / max(n_b, phi rms_b n_b)`, with `n_b = max_Y ||y_b-r_b||`.
- **M3**: a dblat3/Higham elementwise gauge, `max_i |x_i-r_i| / (u Delta_i + u32 |r_i|)`,
  with `Delta` the linear-stage magnitude `|W||x|+|b|` propagated through the
  post-ops (elementwise ops by interval endpoints, pooling linearly, BN and GN by the
  first-order `|J|` bound).
- **M6**: the registered form with that gauge as its floor, `|x-r| / (|r| + u Delta)`.

Admissible draws (127), TF32 policy with the RNE yardstick. Escapes are counted on
effective decoys, with the number at least 4x the yardstick's own L2 error in
brackets:

| Metric | theta | Worst correct | LOPO FR | Gross esc. /1015 | Mutant-family esc. /332 | 1% esc. /254 | Gross min margin | Indeterminate |
|---|---:|---|---|---|---|---|---:|---|
| REG (registered e) | 1 | 0.15 | none | 520 | 33 (30) | 100 (99) | 0.08 | 90/127 |
| M1 l2 | 2 | 1.50 | none | 12 | 5 (0) | 0 | 0.81 | 63/127 |
| M1 linf | 2 | 1.86 | none | 0 | 4 (1) | 2 (2) | 50 | 0 |
| M2, phi 1 | 4 | 3.95 | none | 0 | 3 (0) | 2 (0) | 7.0 | 0 |
| M2, phi 1/4 | 16 | 9.48 | none | 0 | 17 (14) | 2 (0) | 1.8 | 1 |
| M3 gauge | 65536 | 5.4e4 | L2/100 | 745 | 264 (254) | 218 (216) | 4e-7 | 126 |
| M6 gauge floor | 1 | 0.12 | none | 325 | 39 (36) | 93 (92) | 0.06 | 77 |

With the extended yardstick (RZ admitted, for `tl.dot` candidates), M1 linf has 0
gross escapes (min margin 28), and M2 (phi 1, theta 4) has 0 gross escapes with
L2/60 the only leave-one-problem-out false reject. Every M2 escape there is no
larger than the truncation noise: `drop_last_k` and `acc_fp16` on the positive-data
L1 matmuls, where truncation is biased by -6.5e-4. Under strict fp32, M1 linf, M2
and M1 l2 have 0 escapes in every class. NNPACK Winograd needs theta 4 for M2 on
admissible draws and 16 on all draws (A2/spiky). The registered metric misses 30 of
254 1% gain faults there, on draws where strict T exceeds 0.01: the sign-mixed A2
draws of the L1 matmuls, and L2/46, L2/52, L2/59, L2/77 and L2/95.

What each candidate shows:
- **Registered e, any threshold.** Vacuous: zeros pass on 86 of 127 admissible draws
  under the emulated RNE yardstick. The cap at 1 is in the normaliser.
- **M6, the minimal repair (gauge floor instead of `kappa ||r||_inf`).** Still capped
  at 1 for zeros, so still vacuous (325 gross escapes). Any metric of the form
  `|x-r|/(|r|+...)` saturates at 1.
- **M3, Higham/dblat3 gauge.** Fails in two ways.
  - The worst-case gauge is about sqrt(K) pessimistic and is not cancelled by
    normalisation. On L2/77 (BN, then global average pooling) zeros score 0.125, and
    on L1/18 A3 0.45: vacuous.
  - Scaled by 2^-11, the gauge is not a bound for truncation or stochastic rounding
    (up to 2^-10 per operand). At the clamp kink of L2/100 a correct SR realization
    scores 5.4e4.
  - Fixing the scale would make it looser still. It also needs per-problem
    post-op code, and pointwise gauges break at kinks (the scout's ReLU warning).
- **M1 l2 (normwise RMSE ratio).** Separates zeros by about 1/relF_TF32 (TF32-RNE
  relative L2 error: median 2.6e-4, at most 2.8e-3), but is blind to sparse faults.
  One zeroed element or 0.1% zeroed is below the normwise noise on large outputs.
  Its determinacy gate fails on 63 of 127 draws.
- **M1 linf (max-abs ratio).** Strong margins: its weakest gross decoy scores 50x
  theta under the RNE yardstick and 28x under the extended one. It misses faults
  hidden under spikes: on A2/spiky the yardstick's max
  error sits at the x1000 entries, so `bias_sign` and 1% noise elsewhere escape.
- **M2 (blockwise).** Handles spiky draws and localized faults. Its weakest gross
  decoy is 0.1% sparse zeroing (2.5x theta under the extended yardstick), and its
  threshold must absorb block-to-block noise variation (4 at phi 1).
- **M1 linf or M2 (the conjunction).** On every policy, 0 false rejects and no
  escape of a decoy 4x or more above the yardstick noise. Under the RNE yardstick, 3
  emulated mutants escape (`acc_fp16` at 0.9x and 1.4x, a bias sign flip at 2.1x the
  TF32 noise) and 1 of 254 1% faults (L1/18 constrows, where 1% is 3.6x the noise).
  Under the extended yardstick, 17 mutants and 2 1% faults escape, all at most 3.1x
  the truncation noise. Precision-boundary faults (1e-3 gain, fp16 store, 1e-4
  nudge) are at or below TF32 noise and escape by design under TF32. Under strict
  fp32 every class is caught.
- **Not evaluated here.** Metamorphic power-of-two scaling is bitwise exact for fp32,
  RNE and RZ on L1/10, L1/18 and L1/15 (A1 draw 0), but zeros and negation satisfy
  it, so it can only complement. An ensemble z-score needs per-element sigma from
  many members, and four realizations gave heavy-tailed ratios; M2 is its
  block-pooled form.

**Cost.** M1 and M2 need no per-problem code: on the GPU, two extra forwards per draw
for the emulated references (operands rounded on the device, TF32 off) in the
reference item, and one fused reduction per output (per-block sums of squares and a
max). M3 needs a hand-written post-op chain per problem (12 written here; 69 would be
needed in scope) and an extra linear pass. Stored per-block yardstick vectors are
1/4096 of the output.

## 4. Recommendation (rule `q1-audit-metric/1`, for a successor registration)

For each floating output of each A1-A3 draw:

1. **References.** `r` is the fp64 oracle as registered. The yardstick `Y` is: device
   fp32 with both TF32 switches off; CPU fp32; and under TF32-admissible, also the
   device reference with both switches on, plus an emulated TF32-RNE reference
   (matmul and convolution operands rounded to TF32 on the device, then run with
   TF32 off and deterministic algorithms). If the candidate source calls `tl.dot`
   (the registered static check), an emulated TF32-RZ reference is added, which is
   D14's call: truncation is what Triton's `tl.dot` does to fp32 operands.
2. **Statistics.** `rho_inf = ||x-r||_inf / max_{y in Y} ||y-r||_inf`. And
   `rho_block = max_b ||x_b-r_b||_2 / max(n_b, sqrt(mean_b n_b^2))`, over blocks of
   4096 consecutive elements of the flattened output, with
   `n_b = max_{y in Y} ||y_b-r_b||_2`. Non-finite masks must equal the oracle's, as
   registered.
3. **Verdict.** Reject if `rho_inf > 4` or `rho_block > 8` under TF32-admissible, and
   if `rho_inf > 4` or `rho_block > 16` under strict fp32. Each threshold is the
   in-sample power of two doubled. The precision-only class keeps its form at 64x.
4. **Determinacy gate** (replaces the A2/A3 validity gate; decided from the
   references alone). The draw is scored only if the battery all-zeros, negation,
   last 1/64 of the output zeroed, and largest element zeroed each give
   `max(rho_inf/4, rho_block/8) >= 4`. Otherwise it is indeterminate: reported, and
   dropped like a vacuous channel. A problem with every A1 draw indeterminate is
   unauditable under that policy. On the 139 CPU draws, none was indeterminate.
5. **Reported, not verdict-bearing.** The registered `e` and `T`; M1 l2; gain
   `<x,r>/<r,r>` and `1-cos`; each yardstick member's relative L2 error. A problem
   whose TF32 relative error exceeds 1e-2 is flagged precision-limited.

This change is data-motivated under D28(iv). It was designed on S1-cal only, and it
removes from the primary analysis every unit whose correctness it changes.

## 5. What a successor Stage 0 needs: an S1-cal-only GPU pilot

The CPU cannot show four things: real kernels' errors (Inductor templates, cuDNN
algorithm choice, Triton `tl.dot` on tensor cores); device TF32 on L1/18-like shapes;
nondeterministic cuDNN references (L2/77, L2/100); and the cost of the new reference
items.

- **Units.** The 8 re-pilot problems plus L1/15, L2/52 and L2/60 (all S1-cal, no S2
  substrate; L1/47 dropped: no matmul, 8.6 GB inputs). Per problem:
  - its S1-cal substrate, identity control, and stored mutant (8 problems);
  - a harness decoy bundle scored in one item (zeros, negation, last tile zeroed, max
    element zeroed, 1% gain);
  - on the 5 matmul problems, a Triton `tl.dot` matmul in TF32 (hardware truncation)
    as a correct control.
- **Scope.** A1, A2 (all seven) and A3 at replicate 42 under `q1-stage0-exec/2`.
  Reference items write `r`, the yardstick (with one `cudnn.benchmark=True`
  realization to sample algorithm choice), per-block norms and max-abs errors.
- **Size.** 46 kernels, 138 consumer and 33 reference items. **0.28 GPU-h** from job
  713 and 752 measured item costs (`pilot-cost.json`; L2/59's exec/2 items assumed
  at 21 GPU-s; L1/15, L2/52 and L2/60 at the largest measured item). 0.20 GPU-h for
  the 8 re-pilot problems only; 0.57 with a 2x margin. One H100, one job, time box
  0.3 GPU-h. D31's allowance has 0.061 GPU-h left, so this needs a new allowance.
- **Pass rule, written before the job:**
  - (P1) every substrate, identity control and `tl.dot` control is accepted on every
    determinate draw under its policy;
  - (P2) every battery decoy scores at least 4 on every draw, and the 1% gain is
    rejected wherever the yardstick's relative L2 error is at most 2.5e-3;
  - (P3) at most 10% of a problem's draws are indeterminate, else that problem is
    reported precision-limited;
  - (P4) on draws where the device used TF32, the emulated RNE reference's relative L2
    error is within [1/4, 4] of the device TF32 reference's;
  - the 8 mutants' verdicts are reported.
  - On a fail, the metric is not adopted, and the TF32-admissible audit is reported
    unauditable on the failing problems.
- **Then.** Stage 0 itself recalibrates the two thresholds on all admitted S1-cal
  substrates (section 6.1's procedure) under a new experiment id and gauntlet. F2
  (cost) is untouched by this.

## 6. Limits

- The correct realizations are emulations. Real kernels can differ: cuBLAS on L1/18
  is 3.6x the RNE emulation elementwise, and Winograd/FFT cuDNN algorithms in TF32
  were not emulated. The thresholds carry a 2x margin, which only a GPU check can
  confirm (section 5).
- The mutant families are emulated on the reference computation. They are not the
  registered mutants, which are Triton AST edits that need a GPU. Only 5 stored
  mutants have A1-A3 rows.
- Four problems were evaluated on batch slices, and A2/A3 draws were trimmed
  (two same-sign A2 distributions, A3 lead1 and the largest shape) for CPU time.
- The thresholds were fitted in-sample on 12 problems. The leave-one-problem-out
  check flags L2/60 (M2 at theta 4, extended yardstick), which the doubled threshold
  covers.

## Files

- `stored_characterisation.py` produces `stored-characterisation.json`: the D28
  filter, per-row T and vacuity, mutants and controls, calibration and restriction.
- `tf32emu.py` and `cpu_study.py` (driver `run_cpu_study.sh`) produce `cpu/*.json`:
  one record per draw, with code hashes and input fingerprints; logs in `cpu/logs/`.
- `evaluate.py` produces `results.json`: emulation check, characterisation,
  candidates per policy and subset, the recommended rule per problem, restriction.
- `pilot_cost.py` produces `pilot-cost.json`.

To reproduce:

```bash
python stored_characterisation.py --journals <copies: j474/ j518/ j548/ j713/ j752/>
PY=<python with torch 2.11 CPU> sh run_cpu_study.sh cpu
python evaluate.py --cpu cpu --out results.json
python pilot_cost.py --journals <same>
```
