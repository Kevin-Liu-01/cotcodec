# Q1 audit-metric study (D41 ii), revision 2: where A1-A3 are vacuous, and what a successor audit can certify

Branch `stage0/q1-audit-metric` (from main `65bc2e2`). CPU only: no GPU job of any
kind. No evaluation unit was read for analysis or recomputed (D28). The draft
registration is not edited. This is a design study for a successor Stage 0, not a
registered result. Every threshold below was fitted on the same S1-cal draws it is
evaluated on, as the registered calibration (section 6.1) also does.

Revision 2 reconciles the first pass (commit `5f295cd`) with an independent
replication and an adversarial critique, both run on 2026-10-08 on S1-cal data only.
It fixes the errors they found, re-runs every script, adds a CPU check of correct
algorithms that are not yardstick members (section 4), withdraws the first pass's
rule `q1-audit-metric/1`, and replaces it with a three-valued rule (section 5).
Section 8 answers each objection. Section 9 is the recommendation.

## Summary

- **F1 stands, and both reviews replicated it.** Under the registered metric
  `e(x) = max_i |x_i - r_i| / (|r_i| + 1e-3 ||r||_inf)`, an all-zeros output scores
  exactly `1/(1+kappa) = 0.999` and a negated one `1.998`, on any finite reference.
  The TF32-admissible threshold `T = 16 max(e_ref)` reaches 1 whenever the TF32
  reference's error at a near-zero output exceeds about `kappa ||r||_inf / 16`, which
  happens for every matmul or convolution with sign-mixed weights. The normaliser is
  the defect, not M: no threshold separates a correct TF32 kernel from zeros on L2/46
  A2/uniform8 (0.83 against 0.999).
- **Where (stored rows, every arm and job, per stored reference realization).** No
  admissible draw rejects zeros in any stored realization on L2/46, L2/52 or L2/60.
  L2/59 has one such draw (A3/lead1), L2/77 one (A2/uniform8), L2/95 two (A3/lead1,
  lead5). On L2/100 no draw rejects zeros in every realization, and five A2 draws do so
  only in the realization where cuDNN happened not to use TF32: determinacy there is a
  per-process cuDNN choice, not a property of the draw. Real zeros-like mutant outputs
  pass on 9 admissible stored rows (L2/95 `plus2minus`, L2/59 `mask-bound-minus1`).
  Strict fp32 is never vacuous but rejects 55 correct kernel-draws (95 rows) on the
  cuDNN-TF32 problems.
- **The emulation is faithful where the device used TF32.** A CPU TF32 emulation
  reproduces the stored device TF32 error: median ratio 0.996, 64 of 71 draws within
  1.5x. The outlier is cuBLAS on L1/18 (3.6x the emulation).
- **The first pass's false-reject evidence was mostly by construction.** Its "0 false
  rejects" held because the TF32 RNE and RZ realizations are yardstick members, NNPACK
  is more accurate than the yardstick, and on L1/47 every realization is the yardstick.
  Correct algorithms that are not yardstick members break rule `/1`: Winograd
  F(4x4,3x3) (fp32 under strict, TF32 under TF32-admissible), sequential and two-stage
  reductions, truncating TF32 under the RNE yardstick, and real fp32 Inductor kernels
  against the deployment strict yardstick (5.4-7.5x in stored GPU rows). Rule `/1` is
  withdrawn.
- **Rule `q1-audit-metric/2`** keeps the noise-relative statistics (max-abs and
  blockwise L2 error over the largest error of a policy-chosen yardstick of correct
  references, with an absolute floor) and adds a third verdict. Accept within 4x/8x of
  the yardstick (strict 4x/16x), reject above 64x/128x (strict 256x/256x), otherwise
  precision-ambiguous. On the 139 CPU draws and 83 alternative-algorithm draws it rejects
  every gross destroyed output on determinate draws and rejects no correct algorithm
  tested (with truncation in the TF32 yardstick). The price, stated plainly: under TF32-admissible it cannot decide 1%-level
  faults (239 of 272 land in the ambiguous band), because valid TF32 algorithms differ
  from the yardstick by up to 45x (Winograd F(4x4,3x3), max-abs) while a 1% fault
  scores a median 15x. Under strict fp32 it decides them (276 of 278 rejected).
- **Pilot, re-priced with the harness's `cost_card.charge`.** The first pass's plan
  costs 0.50 GPU-h (0.32 for the 8 re-pilot problems), not 0.28 (0.20). The revised
  plan (section 6) is 0.57 GPU-h measured-cost estimate, 1.14 with a 2x margin.
- **Recommendation (section 9).** Do not fund a successor Q1 Stage 0 now. Record this
  study as Stage 0's outcome. Keep rule `/2` and the priced pilot on the shelf for the
  day Stage 1 becomes runnable (R580 or written risk acceptance), and run them first
  then.

## 0. What revision 2 changed

| Item | First pass | Revision 2 | Source |
|---|---|---|---|
| D28 filter | Kept 752's adversarial controls on L1/1 as tier 2 | Dropped: L1/1 hosts the FlagGems mm evaluation substrate, its draw thresholds would judge that unit, and L1/95's identity control was already dropped on the same ground. Kept 2,306 rows, dropped 2,172 | replication D28 note |
| Determinacy table | Inline arm only, one label per draw | Every arm and job, per stored reference realization | replication D1 |
| L2/59 | "no draw can reject zeros" | A3/lead1 does (T = 0.0047) | replication D1 |
| L2/100 | "A2/constrows only" | No draw in every realization; five A2 draws in the non-TF32 realization only | replication D1 |
| Strict false rejects | 95 rows | 55 distinct kernel-draws (48 in the inline arm) | replication D2 |
| L2/95 `plus2minus` | "passes all 5 A1 draws; A3/inner37 a crash" | Inline arm passes all 5 A1 draws; the store arm passes 1 and rejects 4 (e 1084-1177); inline A3/inner37 is silent-wrong (e = 3.8e22, no exception) | replication D3 |
| Stored mutants with A1-A3 rows | 5 | 6 (adds L2/59 `mask-bound-minus1`, which passes A1 seed 6042 at e = 0.9988, T = 2.14) | replication D4 |
| Closest separations | 1.21x, 3.1x, 4.2x (inline substrates) | 1.21x, 3.13x, 3.90x (L2/100 A2/spiky identity), 4.17x | replication D5 |
| `zero_out` control | Cited as a real destroyed output passing A2/uniform8 | Withdrawn with the L1/1 rows | D28 |
| Emulation, batch-sliced draws | "0.78-1.01" | 0.78-1.09 over 27 draws: three L2/100 draws had been compared with a non-TF32 realization (ratios 1264-1545) | replication D9 |
| Registered rule on truncation | "13 of 286 falsely rejected" | 12 of 276 admissible (12 of 300 all draws) | critique |
| Conjunction mutant escapes | "17" (in-sample thetas) beside the recommended thetas | 17 at in-sample thetas (2, 4); 27 at the recommended (4, 8) | critique |
| Floor | None | 2^-24 of the oracle's max-abs and rms block norm | both |
| Pilot cost | 0.28 GPU-h, `wall x units / 12` on L2/59's failed shared attempt | `cost_card.charge`, every attempt: first-pass plan 0.50 GPU-h | replication D10 |
| Recommended rule | `/1`: reject above 4x/8x | Withdrawn; `/2` three-valued | both |

## Data and the D28 filter

- **Stored journals** (byte copies of the host files; SHA-256 in
  `stored-characterisation.json`, unchanged): jobs 474 (smoke), 518 (smoke,
  calibration, scoring), 548 (scoring), 713 (re-pilot, `ddbfbbf6...`) and 752
  (validation).
- **Kept: 2,306 rows**, all on S1-cal problems that host no S2 substrate, so no
  evaluation unit of any tier: all 2,084 rows of 713, 752's 194 re-pilot rows, and
  518-calibration's 28 rows (L1/15, L1/47, L2/52, L2/60).
- **Dropped: 2,172 rows.** Every row of 518 and 548 scoring (962 and 886: the
  evaluation substrates and their mutants, the S1-eval problems, and L1/95's rows,
  whose problem hosts the Liger unit); 518 smoke (58; S1-eval problems); 474 smoke (2;
  L1/19 hosts an S2 unit); and, new in revision 2, 752's 264 rows on L1/1 (the three
  KernelBench adversarial controls, inline and store). Counts by reason are in
  `stored-characterisation.json`.
- **CPU recomputation** (`cpu_study.py`, unchanged; 139 registered A1/A2/A3 draws on
  the 12 tier-1 problems) and **the alternative-algorithm check** (`alt_algorithms.py`,
  new; 83 draws on the same problems) refuse any problem outside S1-cal or hosting an S2
  substrate. Inputs drawn by `torch.rand` reproduce job 752's stored input fingerprints
  bitwise. L2/46, L2/60 and L2/87 are evaluated on the first 32 samples of each draw,
  L2/100 on the first 4 and (alternative check only) L1/47 on the first 8; each output is
  then an exact slice of the registered draw's output.

## 1. F1 characterised (stored data)

**Mechanism.** For a finite reference with `||r||_inf > 0`, `e(0)` is attained at the
largest `|r_i|` and equals `1/(1+kappa) = 0.999001`; `e(-r) = 2/(1+kappa)`. The
primary threshold is `T = max(16 max(e(r32_dev), e(r32_cpu), e(r32_tf32)), 2^-20)`.
A draw therefore admits zeros iff `e_ref >= 0.0624`, and admits negation iff
`e_ref >= 0.125`.

TF32 rounds operands to a 10-bit mantissa, `u = 2^-11`. With sign-mixed weights or
inputs, an output is a cancelling sum whose TF32 error scales with the term magnitudes
`G_i = (|W||x|)_i`, not with `|r_i|`. Among millions of such outputs, 0.015-1.4% lie
below `kappa ||r||_inf`, where the denominator is the floor. The registered metric's
worst element sits there (`reg_argmax_rne` in `results.json`; `G_inf / z_inf` 1.8-29),
so `e_tf32` is 0.066-0.24 on the stored A1 draws and `T` is 1.05-3.84. `kappa = 1e-3` is
about 2u, so the floor cannot absorb TF32 noise. Strict fp32 has `u = 2^-24`, which is
why strict T stays at 1e-3 to 0.15.

**Per problem**, TF32-admissible, every admissible stored row of both arms and every
job. A draw "rejects zeros" in a realization if that realization's `T < 0.999`. A
realization is one stored set of reference errors (`e_dev`, `e_cpu`, `e_tf32`); cuDNN
picks its algorithm, and whether it uses TF32, per process.

| Problem | Op class | Rows | TF32-adm. T | Rows admitting zeros / negation | Admissible draws | Draws rejecting zeros in every realization | Strict T |
|---|---|---:|---|---|---:|---|---|
| L1/10 | matmul 3D x 2D | 114 | 1e-6 to 3.44 | 14 / 14 | 17 | 15 (all but A2 randn, uniform8) | 1e-6 to 0.011 |
| L1/18 | matmul, transposed | 70 | 1e-6 to 2.90 | 4 / 4 | 16 | 15 (all but A2 uniform8) | 1e-6 to 0.014 |
| L1/15 | matmul + tril | 5 | 0.0047-0.0054 | 0 / 0 | 5 | 5 (A1) | 6e-5 to 7e-5 |
| L1/47 | sum (no matmul) | 5 | 4e-6 | 0 / 0 | 5 | 5 (A1) | 4e-6 |
| L2/59 | linear + swish | 32 | 0.0047-2.14 | 31 / 15 | 10 | 1 (A3/lead1) | 0.0047-0.026 |
| L2/95 | linear + 5 post-ops | 58 | 0.0009-1.69 | 49 / 0 | 9 | 2 (A3/lead1, lead5) | 0.0009-0.018 |
| L2/87 | conv2d (8 ch) + mish | 52 | 0.0014-0.0063 | 0 / 0 | 16 | 16 (cuDNN used no TF32 in any stored realization) | same |
| L2/46 | conv2d + tanh + pool | 23 | 2.0-13.2 | 23 / 23 | 13 | none | 0.0046-0.014 |
| L2/52 | conv2d + gate + BN | 5 | 2.7-3.3 | 5 / 5 | 5 | none | 0.008-0.010 |
| L2/60 | convT3d + swish + GN | 5 | 1.8-2.3 | 5 / 3 | 5 | none | 0.0015-0.0018 |
| L2/77 | convT3d + BN + GAP | 70 | 0.88-3.84 | 63 / 14 | 10 | 1 (A2/uniform8, T = 0.88) | 0.004-0.15 |
| L2/100 | convT3d + clamp | 18 | 0.0034-4.1 | 12 / 12 | 12 | none; 5 A2 draws in some realizations | 0.0034-0.0067 |

L2/100's A2 draws allneg, constrows, samesign100, spiky and ties each have a stored
realization with `T` of 0.003-0.006 (cuDNN without TF32) and another with `T` of 2.2-4.1
(with TF32). The first pass's "A2/constrows only" rested on one inline row from an item
that shared the GPU with an out-of-memory failure; the same draw's store-arm row has
`T = 3.21`. The emulation predicts `T` of 3.5-4.2 on L2/87 if cuDNN used TF32 there.

**Correct against destroyed, on stored rows.**
- The closest registered-metric separations of a correct kernel (substrate or identity
  control, any arm) from zeros are 1.21x (L2/46 A2/uniform8: e = 0.827 against 0.999),
  3.13x (L2/46 A2/ties), 3.90x (L2/100 A2/spiky, identity control, store arm) and 4.17x
  (L2/77 A1; L2/100 A2/randn). No threshold separates these with a margin.
- Real destroyed outputs pass. Six stored mutants have admissible numeric A1-A3 rows
  (L1/10 `acc-minus`, L1/18 `load-offset-off1`, L2/59 `mask-bound-minus1`, L2/77
  `const0to1`, L2/87 `mul2plus`, L2/95 `plus2minus`).
  - L2/95 `plus2minus` writes zeros over part of the output in some runs and garbage
    in others. Zeros-like (e = 0.9989) and accepted on 8 admissible rows: the five
    inline A1 draws, inline A2/allneg, store A1 seed 6042 and store A3/inner37. The
    store arm rejects it on the other four A1 draws (e = 1084-1177) and on A2/allneg
    (e = 4152); inline A3/inner37 rejects it as silent-wrong (e = 3.8e22, no exception).
  - L2/59 `mask-bound-minus1` (store arm) scores e = 0.9988 on A1 seed 6042 and is
    accepted at T = 2.14; its other four A1 rows are rejected (e = 325-362).
  - L1/10 `acc-minus` (a negated output, e = 1.998) passes A2/randn and A2/uniform8 in
    both arms.
  - L2/77 `const0to1` scores like its parent; it looks equivalent at these shapes.
- Under the registered calibration rule the S1-cal substrates need multipliers of at
  most 1.04 (L2/77, every arm). So M = 16 is never raised, and raising it could not help.
- Strict fp32 rejects 55 correct kernel-draws (95 rows; 48 in the inline arm): L2/46
  13, L2/52 5, L2/60 5, L2/77 20, L2/100 12. cuDNN runs these convolutions in TF32 by
  PyTorch default.

**Restriction instead of repair** (the registered metric, three-valued). If a row is
determinate only when zeros fail it with a 4x margin (`4T < 0.999`), then under
TF32-admissible, over every arm (`results.json`, `restriction`): no determinate row
remains on L2/46, L2/52, L2/60 or L2/77; L2/59 keeps 1 row (A3), L2/95 2 (A3) and L2/100
6 (A2 rows from realizations where cuDNN did not use TF32); the L1 matmuls keep A1, A3
and their same-sign A2 draws; L2/87 keeps everything. The restricted
registered audit is unauditable on most of the L2 problems under the primary policy.

## 2. The CPU emulation and its check against stored GPU values

`tf32emu.TF32Mode` intercepts `mm`, `bmm`, `addmm`, `baddbmm` and `convolution` in an
fp32 forward, rounds the two main operands to TF32 (RNE, truncation, or stochastic)
and runs the op in fp32 with NNPACK off, so products are exact and accumulation is
fp32. The check compares each CPU draw with the stored realizations in which the
device used TF32 (a TF32-policy reference error at least twice both fp32 errors;
median over realizations), over every arm and job (`results.json`,
`emulation_validation`):

- Full-batch draws: RNE emulation over stored device TF32 error, median 0.996, 64 of
  71 within 1.5x and 66 within 2x. Examples: L2/46 A1 0.176 against 0.176, L2/60 0.133
  against 0.133, L1/15 0.000304 against 0.000303, L2/95 0.106 against 0.106.
- All seven outliers are L1/18: cuBLAS is 3.5-3.6x the emulation on the five A1 draws
  and 1.6x on A3/inner37 (plausibly the tensor core's accumulation at K = 8192), and on
  A2/constrows, whose inputs are not bitwise equal, the emulation is 1.5x the device.
- Batch-sliced draws: 0.78-1.09 of the full-batch stored value, all 27 within 1.5x. (A
  maximum over a slice is usually but not always below the full batch's: the
  emulation is not the device.)
- CPU fp32 (Apple Accelerate) against device fp32: median 1.00 over 77 draws, but not
  uniform. At the A3 shapes of L1/10, L1/18, L2/59 and L2/95 the Mac's error is 3.7-12.7x
  the device's, and there it equals the stored fp32 Inductor substrates' error (section
  4); on L2/77 it is 0.25-0.46x (cuDNN's fp32 algorithm is the less accurate one).
- The device used no TF32 on L2/87 (every stored realization), on the exact `ties`
  draws of L1/10 and L1/18, on L1/47 (no matmul), and in one of L2/100's realizations.

## 3. Candidate metrics (first pass, corrected)

Every statistic is computed per draw against the fp64 oracle `r`. A *yardstick* `Y` is
a set of correct references; a threshold is the smallest power of two at or above every
correct realization's statistic (the registered M rule).

| Policy | Yardstick | Held-out correct realizations | Informative held-out cases (admissible draws) |
|---|---|---|---|
| strict | CPU fp32 | fp32 NNPACK Winograd (3x3 convolutions) | 32, on three conv2d problems; more accurate than the yardstick in max-abs (`rho_inf` at most 0.75), blockwise up to 9.4 (L2/46 A2/spiky, inadmissible) |
| TF32, RNE | fp32, TF32-RNE | TF32 stochastic rounding, fp32 NNPACK | SR: 117, of which 8 are the yardstick itself (L1/47, exact `ties` draws) |
| TF32, extended | fp32, TF32-RNE, TF32-RZ | same | same |
| registered as is | fp32, TF32-RNE | TF32-RZ | 12 of 276 falsely rejected (L1/10 5, L1/18 7; finding 18.3.6 reproduced on S1-cal) |

So the first pass's false-reject test was nearly empty: the TF32 realizations it
called correct were yardstick members, and the only strict held-out realization was
more accurate than the yardstick in max-abs. Section 4 supplies the missing test.

Stochastic rounding on A2/constrows is excluded from calibration: it rounds equal
values differently, which no TF32 unit does, and there it is 10-32x the yardstick.

Definitions: **REG** the registered `e`, re-thresholded; **M1 l2**
`||x-r||_2 / max_Y ||y-r||_2`; **M1 linf** `||x-r||_inf / max_Y ||y-r||_inf`; **M2**
`max_b ||x_b-r_b|| / max(n_b, phi rms_b n_b)` over blocks of 4096 with
`n_b = max_Y ||y_b-r_b||`; **M3** a dblat3/Higham elementwise gauge; **M6** the
registered form with that gauge as its floor.

Admissible draws (127), TF32 policy with the RNE yardstick; escapes on effective decoys,
with the number at least 4x the yardstick's L2 error in brackets:

| Metric | theta | Worst correct | LOPO FR | Gross esc. /1015 | Mutant-family esc. /332 | 1% esc. /254 | Gross min margin | Indeterminate |
|---|---:|---|---|---|---|---|---:|---|
| REG (registered e) | 1 | 0.15 | none | 520 | 33 (30) | 100 (99) | 0.08 | 90/127 |
| M1 l2 | 2 | 1.50 | none | 12 | 5 (0) | 0 | 0.81 | 63/127 |
| M1 linf | 2 | 1.86 | none | 0 | 4 (1) | 2 (2) | 50 | 0 |
| M2, phi 1 | 4 | 3.95 | none | 0 | 3 (0) | 2 (0) | 7.0 | 0 |
| M2, phi 1/4 | 16 | 9.48 | none | 0 | 17 (14) | 2 (0) | 1.8 | 1 |
| M3 gauge | 65536 | 5.4e4 | L2/100 | 745 | 264 (254) | 218 (216) | 4e-7 | 126 |
| M6 gauge floor | 1 | 0.12 | none | 325 | 39 (36) | 93 (92) | 0.06 | 77 |

The in-sample thetas move with the stochastic-rounding seed: the replication's SR
realization gives M2 4.44 (L1/15 A2/spiky) against theta 4 and M1 linf 1.985 against
2; four more seeds here give at most 2.26 (M1 linf) and 4.18 (M2) under the RNE yardstick
on admissible draws (section 4), so both in-sample thetas are exceeded and rule `/1`'s
doubled values (4, 8) are not. The conjunction "M1 linf or M2" at the in-sample thetas
(2, 4) lets 17 mutant-family emulations escape under the extended yardstick; at rule
`/1`'s doubled thresholds (4, 8), 27 (all within 3.1x of the truncation noise).

What each candidate shows (unchanged): the registered `e`, M6 and every metric of the
form `|x-r|/(|r|+...)` saturate at 1 for zeros; M3's worst-case gauge is about
`sqrt(K)` pessimistic, breaks at kinks and needs per-problem code; M1 l2 is blind to
sparse faults; M1 linf misses faults hidden under spikes; M2 handles spiky draws and
localized faults. Max-abs and blockwise noise ratios together separate every gross
decoy with margins of 25-970x on the battery, and both reviews reproduced those margins.

## 4. Correct algorithms that are not yardstick members (new in revision 2)

`alt_algorithms.py` rebuilds 83 registered draws (75 admissible) on the 12 tier-1
problems and computes correct outputs that a real kernel may produce:

- `kblock_fp32`: a Triton or Inductor template K-loop, fp32 operands, blocks of 32
  accumulated sequentially (convolutions: 8 input-channel blocks; L1/47: `seq1`, one
  accumulator over the 4096 rows, and `kblock32`);
- `kblock_tf32_rne`, `kblock_tf32_rz`: the same with TF32-rounded operands
  (truncation is `tl.dot`'s TF32 on fp32 operands);
- `wino23`, `wino43`: Winograd F(2x2,3x3) and F(4x4,3x3), fp32 or with the transformed
  GEMM operands rounded to TF32 (L2/46, L2/87, L2/52; checked exact in fp64);
- `tf32_sr_s101`-`s104`: four more stochastic-rounding seeds.

Largest ratio to the yardstick over the draws (`rho_inf / rho_block`, with the floor;
`results.json`, `alt_algorithms`):

| Algorithm | Correct under | Problems | Draws (adm.) | strict | TF32, RNE yardstick | TF32, extended | Above rule `/1` (adm. draws) |
|---|---|---|---|---|---|---|---|
| `kblock_fp32` | all policies | L1/10, L1/15, L1/18, L2/100, L2/46, L2/52, L2/59, L2/60, L2/77, L2/87, L2/95 | 80 (72) | 1 / 2.72 | 0.056 / 0.0561 | 0.0134 / 0.016 | strict 0/72, RNE 0/72, ext 0/72 |
| `seq1_fp32` | all policies | L1/47 | 3 (3) | 15.2 / 14.3 | 15.2 / 14.3 | 15.2 / 14.3 | strict 3/3, RNE 3/3, ext 3/3 |
| `kblock32_fp32` | all policies | L1/47 | 3 (3) | 2.58 / 2.55 | 2.58 / 2.55 | 2.58 / 2.55 | strict 0/3, RNE 0/3, ext 0/3 |
| `wino23_fp32` | all policies | L2/46, L2/52, L2/87 | 22 (21) | 1.07 / 2.74 | 0.00207 / 0.002 | 0.00163 / 0.00143 | strict 0/21, RNE 0/21, ext 0/21 |
| `wino43_fp32` | all policies | L2/46, L2/52, L2/87 | 22 (21) | 13.7 / 18.1 | 0.0263 / 0.0115 | 0.0248 / 0.0106 | strict 10/21, RNE 0/21, ext 0/21 |
| `kblock_tf32_rne` | TF32 | L1/10, L1/15, L1/18, L2/100, L2/46, L2/52, L2/59, L2/60, L2/77, L2/87, L2/95 | 80 (72) | (TF32 not admissible) | 1.02 / 1.03 | 1 / 1 | RNE 0/72, ext 0/72 |
| `wino23_tf32` | TF32 | L2/46, L2/52, L2/87 | 22 (21) | (TF32 not admissible) | 2.13 / 4.76 | 2.04 / 1.94 | RNE 0/21, ext 0/21 |
| `wino43_tf32` | TF32 | L2/46, L2/52, L2/87 | 22 (21) | (TF32 not admissible) | 50.2 / 34.9 | 44.8 / 18.3 | RNE 21/21, ext 15/21 |
| `tf32_sr (4 seeds; not on constrows)` | TF32 | L1/10, L1/15, L1/18, L2/46, L2/60, L2/87, L2/95 | 232 (208) | (TF32 not admissible) | 2.26 / 4.18 | 1.98 / 2.94 | RNE 0/208, ext 0/208 |
| `kblock_tf32_rz` | TF32 (if truncation admitted) | L1/10, L1/15, L1/18, L2/100, L2/46, L2/52, L2/59, L2/60, L2/77, L2/87, L2/95 | 80 (72) | (TF32 not admissible) | 33.1 / 167 | 1 / 1.01 | ext 0/72, RNE 19/72 |

`rho_inf / rho_block`, largest over admissible draws. Under strict, TF32 outputs are not
correct and are not listed. Stochastic rounding on A2/constrows is excluded, as in
section 3 (it reaches 30/25 there). "Above rule `/1`" counts draws above 4 (max-abs) or
8 (blockwise; strict 16).

What this shows:

- **Rule `/1` rejects correct kernels outside the TF32-RNE cell.** Under strict, a single
  sequential accumulator per output on L1/47 (a common Triton reduction) is 13.7-15.2x
  the yardstick on all three draws, while the registered e/T is 0.87-0.96; fp32 Winograd
  F(4x4,3x3) exceeds rule `/1` on 10 of 21 admissible draws (up to 13.7/18.1, and 23/73 on
  the inadmissible L2/46 A2/spiky). Under TF32-admissible, TF32 Winograd F(4x4,3x3) exceeds it
  on 21 of 21 draws against the RNE yardstick (up to 50 on L2/87 A2/ties) and 15 of 21
  against the extended one; truncating TF32 exceeds the RNE-only yardstick on 19 of 72
  (up to 33/167 on L1/18). K-blocked orders, Winograd F(2x2,3x3) and the four SR seeds stay
  inside it.
- **Platform transfer under strict (critique).** On the five matmul problems the
  K-blocked fp32 matmul has 0.06-0.44 of the Mac's max-abs error (median about 0.2), and
  registered e tracks `rho_inf` there (L1/18: 0.16 against 0.16, 0.19 against 0.19). The
  Mac's Accelerate kernel accumulates in a less accurate order, like the fp32 Inductor
  kernels (their stored errors agree to three digits at A3 shapes). On the GPU the
  deployment yardstick (device fp32, x86 CPU fp32) is accurate, and the stored fp32
  Inductor substrates sit at 7.48x (L1/18 A3/inner37), 6.10x (L1/18 A3/allprime) and
  5.41x (L2/95 A3/lead5) of it in registered e, which tracks `rho_inf` on these
  positive-data matmuls. Rule `/1`'s strict accept band
  (4x) would reject them; the registered strict T accepts them (e/T 0.34-0.47).
- **Scalar outputs** (`scalar_check.py`, 200 synthetic 2^24-element means). With two
  yardstick members, a correct two-stage reduction with a sequential second stage
  exceeds `rho_inf` 4 on 63-83% of draws and 16 on 10-34%, and never 64 (largest 54).
  Adding an emulated worst-order member (4096-element blocks, then sequential) cuts
  "above 4" to 10-20% and the largest to 44. A tree of the same accuracy as the
  yardstick never exceeds 1.8.
- **Gross decoys stay far above every valid algorithm.** On the same draws the battery
  (zeros, negation, last 1/64 zeroed, largest element zeroed) scores at least 57 in
  max-abs under the TF32 yardsticks and 3,609 under strict. A 1% gain scores a median 15
  (max-abs) and 22 (blockwise) under TF32, as low as 0.7 on A2/constrows, and at least 36
  under strict: under TF32 it overlaps the valid algorithms.

## 5. Rule `q1-audit-metric/1` withdrawn; rule `q1-audit-metric/2`

Rule `/1` (reject above 4x/8x) assumed that every correct kernel sits within a few
times the yardstick's error. Section 4 shows that valid algorithms spread over two
orders of magnitude, so a two-valued rule must either reject correct kernels or accept
1% faults. Rule `/2` says which draws and faults it can decide.

For each floating output of each A1-A3 draw:

1. **References.** `r` is the fp64 oracle as registered. The yardstick `Y` is chosen by
   policy, the same for every candidate (not by the candidate's source text):
   - strict fp32: device fp32 with both TF32 switches off, and x86 CPU fp32;
   - TF32-admissible: those, the device reference with TF32 on, and emulated TF32-RNE and
     TF32-RZ references (operands rounded on the device, then run with TF32 off and
     deterministic algorithms). Whether truncation belongs here is D14's call (Kevin);
     `tf32_rne_only` in `results.json` shows the rule without RZ;
   - optional, for reductions of length 2^12 or more: an emulated worst-order member
     (blocks, then one sequential accumulator), which narrows the ambiguous band.
2. **Statistics, with an absolute floor.**
   `rho_inf = ||x-r||_inf / max(max_Y ||y-r||_inf, 2^-24 ||r||_inf)`;
   `rho_block = max_b ||x_b-r_b||_2 / max(n_b, sqrt(mean_b n_b^2), 2^-24 rms_b ||r_b||_2)`,
   blocks of 4096 consecutive elements, `n_b = max_Y ||y_b-r_b||_2`. Without the floor, a
   draw on which every yardstick member is exact (A2/ties on L1/10, L1/15, L1/18) gives
   0/0 for an exact candidate and infinity for any inexact correct one.
3. **Three-valued verdict per draw.** Accept if `rho_inf <= 4` and `rho_block <= 8`
   (strict: 16). Reject if `rho_inf > 64` or `rho_block > 128` (strict: 256 and 256).
   Otherwise precision-ambiguous.
4. **Determinacy gate** (replaces the A2/A3 validity gate). A draw is scored only if every
   battery decoy (all zeros, negation, last 1/64 zeroed, largest element zeroed) scores
   at least twice the reject threshold (`max(rho_inf/64, rho_block/128) >= 2`). Otherwise
   it is reported as indeterminate.
5. **Kernel verdict over determinate draws.** Silently wrong if any draw rejects; correct
   if every draw accepts; precision-ambiguous otherwise. Ambiguous kernels are reported
   and left out of ground truth, with a sensitivity analysis that counts them both ways.
6. **Reported, not verdict-bearing.** The registered `e` and `T`; M1 l2; gain and
   `1-cos`; each yardstick member's relative L2 error; non-finite masks as registered.

The thresholds are in-sample: the accept band is rule `/1`'s, and the reject thresholds
were chosen after the critique's Winograd numbers and the first alternative records were
seen. Results (`results.json`, `rule2`):

All 139 CPU draws and 83 alternative-algorithm draws (rule `/2` has no validity gate);
counts are accept / ambiguous / reject on determinate draws:

| Policy (yardstick) | Indeterminate draws (CPU, alt) | Correct realizations (CPU) | Alternative algorithms | Gross decoys | Mutant-family emulations | 1% faults | Precision boundary |
|---|---|---|---|---|---|---|---|
| strict (fp32) | 0, 0 | 172 / 0 / 0 | 116 / 14 / 0 | 0 / 0 / 1111 | 0 / 7 / 369 | 0 / 2 / 276 | 0 / 111 / 297 |
| TF32 (fp32, RNE, RZ) | 3, 3 | 565 / 0 / 0 | 523 / 18 / 0 | 0 / 0 / 1087 | 26 / 122 / 218 | 2 / 239 / 31 | 371 / 1 / 27 |
| TF32 without RZ (D14 alternative) | 3, 3 | 429 / 0 / 0 | 498 / 40 / 3 | 0 / 0 / 1087 | 2 / 93 / 271 | 1 / 186 / 85 | 277 / 76 / 46 |
| TF32, reject at 128/256 (sensitivity) | 4, 4 | 562 / 0 / 0 | 520 / 18 / 0 | 0 / 14 / 1066 | 26 / 146 / 191 | 0 / 254 / 16 | 371 / 1 / 27 |

- The ambiguous alternatives are the L1/47 sequential sum (3) and Winograd F(4x4,3x3) (11
  in fp32 under strict, 15 in TF32 under TF32-admissible).
- Without RZ in the yardstick, truncating TF32 is rejected on three L1/18 draws
  (`rho_block` 163-167): if Kevin rules truncation admissible (D14), RZ must be a
  yardstick member for every candidate.
- The indeterminate TF32 draws are L1/15 A3/lead5, L2/46 A2/spiky and L2/95 A2/spiky
  (the last two inadmissible under the registered gate); the battery's weakest member
  there is the last tile or the largest element, at 0.9-2.0x the reject threshold.
- Doubling the TF32 reject thresholds would leave 14 gross decoys ambiguous (constant-mean
  and shuffled outputs on L1/18, 13; 0.1% sparse zeroing on L2/77, 1) and gain no correct
  verdict, so 64/128 is kept.
- Admissible draws only (`results.json`, `rule2.admissible_draws`) give the same pattern:
  no correct realization or alternative rejected under strict or TF32 with RZ, every gross
  decoy rejected, 219 of 252 1% faults ambiguous under TF32.

Rule `/1` with the floor added changes no count on the 139 CPU draws (the floor binds
on 5 strict draws and 3 TF32 draws, all exact or near-exact).

What rule `/2` can certify, and what it cannot:

- **Strict fp32:** gross destruction and 1%-level faults (rejected), with every valid fp32
  algorithm tested accepted or ambiguous. But strict rejects the PyTorch default itself on
  the cuDNN-TF32 problems, so it can only be the secondary policy (D14).
- **TF32-admissible:** gross destruction only. A 1% fault scores a median 15x (max-abs)
  and 22x (blockwise) the TF32 yardstick, inside the band where valid TF32 algorithms
  also sit (Winograd F(4x4,3x3) in TF32 reaches 45x against the extended yardstick, 50x
  against RNE). Stage 0's ground truth under the primary policy would be "never grossly
  wrong", not "never wrong at 1%".

## 6. The S1-cal-only GPU pilot (revised)

The CPU cannot show: real kernels' errors (Inductor Triton templates, cuDNN algorithm
choice, `tl.dot` on tensor cores, and whether Triton's TF32 conversion truncates or
rounds); the deployment yardstick's own size; nondeterministic cuDNN references (L2/77,
L2/100); and the cost of the new reference items.

- **Problems** (all S1-cal, no S2 substrate): the 8 re-pilot problems; L1/15, L2/52 and
  L2/60; and two small L2 problems with reduction epilogues, L2/56 (matmul, sigmoid,
  row sum) and L2/18 (matmul, sum, max, avg-pool, logsumexp x2), whose S1 substrates must
  be compiled first. L1/47 and the other S1-cal reduction problems (L1/24, L1/33, L1/37,
  L1/94, L1/100) have 4.3-8.6 GB inputs and run alone: L1/47 alone would cost 0.81 GPU-h,
  so the reduction class is covered on the CPU (section 4) and by L2/56 and L2/18.
- **Kernels per problem, chosen so that correct controls differ from the yardstick**
  (181 of 252 stored substrate rows and all 171 identity rows equal a yardstick member
  bitwise, so they test nothing):
  - the S1-cal substrate and the identity control (sanity);
  - matmul problems: an Inductor variant forced to its Triton matmul template
    (`max_autotune_gemm_backends="TRITON"`), compiler-generated and so within D3;
  - convolution problems: the reference module with `cudnn.benchmark = True` (algorithm
    sampling, Winograd and FFT included), TF32 on;
  - reduction problems: an Inductor variant with the other `split_reductions` setting;
  - a harness decoy bundle in one item (zeros, negation, last tile zeroed, largest element
    zeroed, 1% gain);
  - the stored mutant (8 problems).
  No kernel is written for the pilot by a model (D3, D7).
- **Scope.** A1, A2 (all seven) and A3 at replicate 42 under `q1-stage0-exec/2`.
  Reference items write `r`, the yardstick members (device fp32, x86 CPU fp32, device
  TF32, emulated RNE and RZ; the worst-order member on the reduction problems), per-block
  norms and max-abs errors.
- **Size and cost** (`pilot-cost.json`, `cost_card.charge` on jobs 713, 752 and 518's
  calibration phase; every consumer item at the problem's largest measured item):
  60 kernels, 180 consumer and 39 reference items, **0.57 GPU-h**, **1.14 GPU-h with a 2x
  margin**. The 8 re-pilot problems alone are 0.34 GPU-h. L2/59 dominates (0.17 GPU-h;
  its A2/A3 items ran alone at 26.8-35.5 GPU-s). Assumptions: L1/15, L2/52 and L2/60
  have only A1 items measured, so their A2/A3 items are A1 x 2.09 and their reference
  items consumer x 2.03 (the largest ratios measured on the re-pilot problems);
  L2/56 and L2/18 take L2/95's costs. Time box: 1.2 GPU-h, one H100, one job. D31's
  allowance has 0.061 GPU-h left, so this needs a new allowance.
- **Pass rule, written before the job:**
  - (P1) every substrate, identity control and compiler or cuDNN variant is accepted or
    precision-ambiguous on every determinate draw, never rejected; the number of
    ambiguous verdicts among them is reported;
  - (P2) every battery decoy is rejected on every determinate draw, and at most 10% of a
    problem's draws are indeterminate (else that problem is reported unauditable under
    that policy);
  - (P3) the 1% gain is rejected on every determinate strict-fp32 draw; under
    TF32-admissible its verdicts are reported, not tested;
  - (P4, on every draw) the emulated RNE reference's relative L2 error is within
    [1/4, 4] of the device TF32 reference's where the device used TF32, and the device
    and x86 fp32 members are within 8x of each other; a draw failing P4 is reported and
    its verdicts are not used;
  - the 8 mutants' verdicts and the variants' ratios are reported.
  - On a fail, rule `/2` is not adopted, and the failing problems are reported unauditable
    under that policy.
- **Then**, only if Stage 0 goes ahead: Stage 0 recalibrates the thresholds on all
  admitted S1-cal kernels under a new experiment id and a fresh gauntlet (D24, D41 i).

## 7. Limits

- The correct alternatives are CPU emulations of algorithm classes, not the GPU kernels
  themselves. FFT convolutions, split-K with atomics, cuDNN's own Winograd variants and
  fused epilogues are not covered; the pilot samples some of them, not all.
- Every threshold is in-sample, fitted on 12 S1-cal problems. The reject thresholds
  have margins of 1.43x (TF32, Winograd F(4x4,3x3) at 44.8; 1.27x without RZ in the
  yardstick) and 3.5x (strict, fp32 Winograd at 73.5 blockwise) over the worst valid
  algorithm seen, and the scalar check reached 54 against 64 with a two-member yardstick.
- The mutant families are emulated on the reference computation, not the registered
  Triton AST mutants; six stored mutants have A1-A3 rows.
- Four problems were evaluated on batch slices, and A2/A3 draws were trimmed for CPU time.
- fp16 operand casts score about 0.25 and pass every draw: no registered draw leaves the
  fp16 range (the registered rule shares this gap). A successor's A2 would need a draw
  with values above 65504 to see it.
- Under the extended yardstick a bf16 output store passes on L2/95 (kernel maximum 0.99):
  inside a TF32-admissible numeric contract, errors within TF32-truncation noise are
  admissible by construction.

## 8. Objections and answers

### Replication (all accepted unless stated)

| Item | Answer |
|---|---|
| Core replicated (own code; filter, per-problem table, restriction, calibration, separations, emulation, mechanism, candidate counts, battery minima) | Noted. No change needed beyond the items below. |
| D1. Inline-arm selection: L2/59 A3/lead1 admissible with T = 0.0047; L2/100 "A2/constrows only" rests on one non-final row; determinacy is a per-process cuDNN choice | **Accepted, fixed.** Section 1's table now counts every arm and job per stored realization. Rule `/2` decides determinacy per draw from the realized references (step 4). |
| D2. 95 strict false-reject rows are 55 kernel-draws | **Accepted, fixed** (48 in the inline arm). |
| D3. L2/95 `plus2minus` account holds for the inline arm only; inline A3/inner37 is silent-wrong, not a crash | **Accepted, fixed** (section 1). The conclusion stands: a zeros-like output passes 8 admissible rows. |
| D4. L2/59 `mask-bound-minus1` zeros-like pass omitted; six mutants, not five | **Accepted, fixed.** |
| D5. With store rows, next separations are 3.90x and 4.17x | **Accepted, fixed** (correct kernels of every kind and arm). |
| D6. In-sample thresholds move with the SR seed (M2 4.44 > 4; M1 linf 1.985 < 2) | **Accepted.** Four more seeds: at most 2.26 (M1 linf) and 4.18 (M2) under the RNE yardstick on admissible draws, so both in-sample thetas are exceeded, as the replication found. The doubled accept band (4, 8) still accepts every SR realization; rule `/2` keeps it. |
| D7. Decoy definitions differ (M2 gross min margin 5.5 vs 7.0; M1 l2 13 vs 12 escapes) | **Accepted as definitional.** Neither set lets a gross decoy through M1 linf or M2. No change. |
| D8. No floor; exact A2/ties draws give 0/0 | **Accepted, fixed** (rule `/2` step 2; evaluated in `results.json`). |
| D9. "Batch-sliced 0.78-1.01" wrong; three L2/100 draws mislabelled | **Accepted, fixed.** The label now requires TF32 error at least twice the fp32 error and compares with TF32 realizations only: 0.78-1.09 over 27 draws. |
| D10. Pilot underpriced; L2/59 alone-run items 26.6-35.5 GPU-s; stated fallback rule not applied | **Accepted, fixed.** With `cost_card.charge` and every attempt, the first pass's plan is 0.50 GPU-h (0.32 for the 8 re-pilot problems; replication 0.30) and 1.03 GPU-h under its own stated fallback. The fallback is replaced by measured ratios (section 6). |
| M3, M6 not replicated | Noted. M6 fails analytically (`x = 0` gives `|r|/(|r|+D) < 1`). |
| D28 note: L1/1 kept, L1/95 identity dropped on the same ground | **Accepted, fixed** by dropping L1/1 (264 rows). The `zero_out` witness is withdrawn; the tier-1 mutants carry the point. No D28 violation was found by either review. |
| Strongest objection: "0 false rejects" holds by construction; held-out realizations are only SR and NNPACK; thresholds move with the seed; cuBLAS is 3.6x the emulation on L1/18 | **Accepted.** Section 4 adds the missing test and rule `/1` fails it; rule `/2` replaces it. Whether rule `/2` admits real kernels is the pilot's P1 (open). |
| Conditions (1)-(5) on the verdict | (1) floor: done. (2) "by construction" stated (section 3) and P1 made decisive with controls that differ from the yardstick. (3) per-realization determinacy: done. (4) re-priced: 0.57 GPU-h, 1.14 with 2x margin, time box 1.2. (5) D14 truncation call and new allowance and gauntlet: open, Kevin's. |

### Critique (all accepted unless stated)

| Item | Answer |
|---|---|
| Strongest objection: rule `/1` rejects correct kernels wherever error is fp32 rounding (reductions, strict, scalar outputs); L1/47 sequential sum at `rho_inf` 13-16; Inductor substrates 5.4-7.5x the deployment strict yardstick; the study's test is empty there | **Accepted.** Reproduced with independent code: L1/47 `seq1` at `rho_inf` 13.7-15.2 and `rho_block` 14.0-14.3 with registered e/T 0.87-0.96, scalar check (section 4), stored GPU rows (5.41-7.48x). Rule `/1` withdrawn. Rule `/2` does not reject any of these; it makes them ambiguous where they exceed the accept band. |
| Candidate text picks the yardstick (`tl.dot` regex adds RZ) | **Accepted.** Rule `/2` picks the yardstick by policy. |
| bf16 output store passes on L2/95 under the extended yardstick; 0.1% gain passes on 7 of 8 L2 problems | **Accepted as a limit** (section 7): within a TF32 contract these are inside the noise. |
| TF32 Winograd F(4x4,3x3) rejected on 9/9 draws of L2/87 and L2/46; F(2x2,3x3) passes | **Accepted, reproduced** (section 4: F(4x4,3x3) in TF32 up to 50 against the RNE yardstick on L2/87 A2/ties; F(2x2,3x3) at most 2.1). Ambiguous under rule `/2`. |
| fp16 operand casts pass every draw | **Accepted; open** for a successor's A2 design (section 7). |
| "13 of 286" should be 12 of 276 | **Accepted, fixed.** |
| "17 mutants" mixes the in-sample and recommended thresholds | **Accepted, fixed** (17 at (2, 4), 27 at (4, 8)). |
| L1/47's four realizations are bitwise the yardstick; strict's only held-out realization is NNPACK on three conv problems | **Accepted** (section 3, informative cases column). |
| NNPACK is more accurate than the yardstick; explicit F(4x4,3x3) fp32 is rejected on 4/9 draws under strict | **Accepted, reproduced** (section 4). Ambiguous under rule `/2`. |
| Platform transfer: the Mac CPU member equals the Inductor substrate's error; the deployment yardstick is 6-7.5x smaller | **Accepted.** Section 4; the strict reject threshold (256) is set with this gap in view; the accept band is not, and the pilot measures it. |
| No floor | **Accepted, fixed.** |
| P1 tests almost nothing: substrate and identity rows equal yardstick members | **Accepted.** 181 of 252 substrate rows and 171 of 171 identity rows bitwise, 29 more within 0.1%. The pilot's correct controls are now variants that differ. |
| Emulation not uniformly faithful (0.276 on L1/18) | **Accepted** (already disclosed). P4 is now a per-draw guard. |
| Verdict items (1)-(6) | (1) floor: done (2^-24 relative; a reduction-length-aware floor is an option the pilot can test). (2) per-op-class validation: done on the CPU per class (section 4); per-class thresholds are **rejected** for now: one global reject threshold with an ambiguous band avoids fitting 12 problems twice. (3) strict calibration against the deployment yardstick: **open**, the pilot measures it. (4) yardstick by policy: done. (5) P4 on every draw: done. (6) pilot controls that differ from the yardstick, including non-matmul problems: done for L2/56, L2/18 and the CPU L1/47 check; **rejected** for L1/24, L1/33, L1/37, L1/94 and L1/100 on cost (4.3-8.6 GB inputs run alone; L1/47, the measured one, would cost 0.81 GPU-h). |

## 9. Recommendation for the program owner

**Whether Q1 Stage 0 is worth a successor: not now.** Record this study as Stage 0's
outcome and stop Q1's GPU spend until Stage 1 can run.

- **What a successor could still measure.** Stage 0 exists to give gate false-accept and
  false-reject rates against an audit that serves as ground truth. Under the primary
  TF32-admissible policy, the audit that works (rule `/2`) certifies gross destruction
  only; 1%-level faults land in the ambiguous band. A successor would measure how often
  gates let grossly wrong kernels through, the coarse end of what the gates already
  catch, and its false-reject side rests on a P1 that is still untested on real kernels.
- **Novelty.** Measuring the Checker (arXiv:2609.22220) already owns mutation analysis of
  kernel-benchmark oracles. Stage 0's mutant arm would be a small Triton replication of
  it; what is left (gate false rejects on independent correct kernels, per-gate cost)
  does not justify spending above the 8 GPU-h cap, and Stage 0 as drafted projects to
  20-25 GPU-h at the high point (D41).
- **Consumer.** Stage 0's only consumer, Stage 1, cannot score policy kernels until the
  R580 driver lands or Kevin accepts the risk in writing, and it also needs a licensed
  policy (D5). Stage 1 must change the worker protocol anyway (registration section 12),
  so a Stage 0 frozen now would be re-run after that hardening.

**If Q1 is revived (R580 or written risk acceptance first), in this order:**

1. **D14 ruling (Kevin).** Whether TF32 truncation is admissible (it decides whether RZ is
   a yardstick member), and acceptance that the primary audit's contract becomes "never
   grossly wrong at held-out values and shapes", with 1%-level faults decided only under
   strict fp32.
2. **Audit design: rule `q1-audit-metric/2`** (section 5). Max-abs and blockwise L2 errors
   over the largest error of a policy-chosen yardstick of correct references (device
   fp32, x86 fp32; under TF32 also device TF32 and emulated TF32-RNE, and RZ if
   admitted), with an absolute floor of 2^-24 of the output scale. Accept within 4x/8x
   (strict 4x/16x), reject above 64x/128x (strict 256x/256x), otherwise
   precision-ambiguous; a draw counts only if the decoy battery scores at least twice
   the reject threshold; ambiguous kernels are left out of ground truth and reported both
   ways. No validity gate, no per-problem code.
3. **GPU validation pilot, S1-cal only** (section 6): 13 problems (the 8 re-pilot problems,
   L1/15, L2/52, L2/60, and the small reduction problems L2/56 and L2/18), 60 kernels,
   180 consumer and 39 reference items, A1-A3 at replicate 42 under exec/2. Cost from
   `cost_card.charge` on measured items: **0.57 GPU-h, 1.14 GPU-h with a 2x margin; time
   box 1.2 GPU-h** on one H100, as a new allowance (D31 has 0.061 GPU-h left). Its
   correct controls are compiler and cuDNN variants that differ from the yardstick (no
   model-written kernel, D3/D7). The pass rule (P1-P4) is fixed before the job.
4. **Then a reduced Stage 0** under a new id and a fresh gauntlet (D24, D41 i): gate false
   rejects on independent correct kernels and gate false accepts on gross faults, with the
   thresholds recalibrated on all admitted S1-cal kernels, and only the parts MtC does not
   cover.

**What the audit and its pilot cannot do:**

- decide 1%-level faults under TF32-admissible (a median 15-22x the TF32 yardstick,
  where valid TF32 algorithms also sit);
- prove that no correct kernel is ever rejected: the pilot samples Inductor templates and
  cuDNN's algorithm choice, not every algorithm (FFT, split-K with atomics, fused
  epilogues); the reject thresholds' margins over the worst valid algorithm seen are
  small (section 7);
- see faults that no registered draw exposes (fp16 range, section 7);
- use any evaluation unit (D28): everything is designed and validated on S1-cal only, and
  units whose correctness the rule changes leave the primary analysis (D28 iv);
- unblock Stage 1, which still needs R580 or written risk acceptance, and a licensed
  policy.

**Kevin's calls:** close Q1 Stage 0 with this study as its outcome (recommended), or keep
it alive behind R580; if kept, the D14 truncation ruling and a 1.2 GPU-h allowance for the
pilot, then a fresh gauntlet.

## Files

- `stored_characterisation.py` produces `stored-characterisation.json`: the D28 filter,
  per-row T and vacuity, per-realization determinacy, mutants and controls, distinct
  strict false rejects, yardstick equality of correct-kernel rows, the deployment strict
  ratio, calibration and restriction inputs.
- `tf32emu.py` and `cpu_study.py` (driver `run_cpu_study.sh`) produce `cpu/*.json` (first
  pass, unchanged).
- `alt_algorithms.py` (driver `run_alt.sh`) produces `alt/*.json`: correct algorithms
  that are not yardstick members, with the decoy battery on the same draws.
- `scalar_check.py` produces `scalar-check.json` (synthetic, no problem module).
- `evaluate.py` produces `results.json`: emulation check, characterisation, candidates,
  rule `/1` with and without the floor, held-out informativeness, the alternative
  algorithms, rule `/2`, restriction.
- `pilot_cost.py` produces `pilot-cost.json`.

To reproduce:

```bash
python stored_characterisation.py --journals <copies: j474/ j518/ j548/ j713/ j752/>
PY=<python with torch 2.11 CPU> sh run_cpu_study.sh cpu
PY=<same> sh run_alt.sh alt
python scalar_check.py --trials 200
python evaluate.py --cpu cpu --alt alt --out results.json
python pilot_cost.py --journals <same>
```
