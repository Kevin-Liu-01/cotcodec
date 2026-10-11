# Research Direction: C5 Phase 0 and Phase 1 design, a training-time measurement of how the FP4 element grid crosses with the block-scale configuration at matched storage, with an identified test of the published power-of-two-scale penalty on INT4 (backfill C5)

**Status:** repaired under program decision D68 for a fresh gauntlet run, after gauntlet wave 1 (score 54, the lower of 54 and 65; all three refuters refuted; no honest exit; `program/gauntlet/2026-10-10-c5-fp4-instability.jsonl`, row 1); repair by the single owner on 2026-10-10 on the Mac CPU (no GPU, no host contact); the draft registration is now `program/preregistrations/c5-fp4-instability-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted, with no ledger row; the blind critic, the refute-first triad and the two reviewers of this run have not run; no executable pilot exists; a score of 100 cannot be certified in this repository (D24); Phase 1 is above 8 GPU-h, so its admission is Kevin's ruling under D24 whatever this gauntlet scores
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D68 repair (reframing, identification design, probe, cost arithmetic, draft registration v2, simulations) written by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-10
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex, 114 counted invocations of which 11 were backend rejections, 568 unique ids; 10 OpenReview api2 searches; Semantic Scholar forward citations of seven priors through the read-only host relay; arXiv version records; 58 cell full-text reads and 16 synthesis re-reads) plus run 2's: 16 counted retrieval queries (orx keyword 10, embedding 2, OpenAlex 2 that both failed with HTTP 429, OpenReview api2 notes/search 2; 275 ids returned, 209 unique) and 3 uncounted full-text reads (2510.25602 and 2302.08007 by `orx paper --full`; the ARITH 2025 study from its open copy on NSF PAR, which wave 1 had wrongly recorded as closed access); OpenReview items are abstract-only (per-note pages behind a browser challenge), including the ICML 2026 record of 2510.25602, whose abstract differs from arXiv v1; the citation graph of 2510.25602 was not expanded (OpenAlex rate-limited); not searched: patents, X, Reddit, Hacker News, Chinese-language venues (Zhihu, CNKI), vendor blogs, GitHub issue trackers; full texts read by targeted section except the ARITH 2025 study, read end to end
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-c5-fp4-instability/bundle.json

The budgets are this fresh run's (D68), cumulative over the repair, the triad,
the reviewers and the recorder; at least 30 of the 80 queries are reserved for
the three refuters (six orx discover queries each at minimum). The repair used
16, leaving 64. The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference
only. Phase 0's own compute is separate and runs only after a freeze: fixed
caps of 2.80 GPU-h plus a probe whose cap is set from Phase 0's throughput
measurement and which runs only if Phase 0 stays at or below 8.0 GPU-h.
Phase 1's caps are set by a registered formula after Phase 0 (central case,
single process: 70.1 to 97.4 GPU-h) and need Kevin's admission under D24.

The novelty verdict field uses the doctor's vocabulary. The merged verdict is
NARROWED, and more narrowly than wave 1 stated. The mechanism this study
tests is published: Theorem 1 of 2510.25602 gives the power-of-two (UE8M0)
block scale an overhead rho in [1, 2) that costs a uniform integer grid
20 log10(rho) dB of signal-to-noise ratio (at most 6.02 dB), while Theorem 2 leaves a
floating-point grid's signal-to-noise ratio set by its mantissa width; the
ARITH 2025 study measured on weight tensors that, under E8M0 scales, INT4
gains about 6.47 times E2M1's error reduction when blocks shrink from 32 to 16
(Insight 5). Neither trains a 4-bit integer grid; 2510.25602 trains at 8 bits
only and ARITH 2025 trains E2M1 only. The residual this proposal claims is a
training-time measurement: the grid-by-scale crossing at matched storage at
two block sizes, with one registered test (P2) that the design identifies,
because the two cells it compares differ only in the block scale's mantissa.

## Changes after wave 1

Wave 1 (row hash `65266173...`; proposal sha256 `3195b9a2...`, registration v1
sha256 `6d1a786a...`) scored 54: reviewer 1 (claude-opus-5-5) 54, reviewer 2
(qwen3.6-35b-a3b, Slurm 1083) 65. Blind discrimination against 2505.19115
passed by the letter (distinct mechanism; the prior judged the stronger
contribution, not strictly dominant), but it tested the design prior, not the
mechanism prior. All three refuters refuted. The largest defect, for reviewer
1, was that the central registered test (P2, through I_fmt and I_blk) tested
published theory and was not identified by the design; reviewer 2 named gate
reuse and Phase 0's failure to measure sigma and the anchor. D68 ordered one
CPU-only repair by a single owner and a fresh run. This section is that
repair. Each row names who found the defect, what changed, where it lives in
registration v2, and the CPU check that sizes it (bundle
`compute/repair-d68/`: N2v2 and N3 = tensor-level prediction and
identification table, `numerics_v2.py`; D1v2 = estimability, `doe_v2.py`;
S1v2 = the registered decision path end to end, `power_sim_v2.py`; S2v2 =
caps, `cost_model_v2.py`).

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | The mechanism (power-of-two scales penalise INT4) is 2510.25602's Theorems 1-2, with ARITH 2025 Insights 3 and 5 at tensor level, and was uncredited; H_int was called "this proposal's mechanism" (novelty refuter; both reviewers) | Credited throughout. 2510.25602, ARITH 2025 (open copy on NSF PAR, read end to end) and 2302.08007 read in full with delta rows; the contribution is reframed as the training-time measurement of the grid-by-scale crossing at matched storage, with one identified test of the published prediction; the closest prior is now the mechanism prior, and run 2's blind packet pairs the proposal with it | Relation to v1; Question; Claim scope | Closest Prior Work; Novelty Ledger; `blind/paragraph-ad76d839.txt` |
| 2 | P2 was not identified: I_blk is a block-size (crest-factor) effect, growing 58% to 94% as much under exact or BF16 scales; I_fmt changes UE4M3's range together with its precision (identification refuter; reviewer 1, both reproduced) | P2 now reads only I_prec32 = (INT4: S1 − S5) − (E2M1: S1 − S5): E8M0 against BF16 block scales at the same block size (32) and the same exponent range, so the cells differ only in the scale's mantissa (0 against 7 bits). N3 with the registered quantizer: I_prec32 is +2.17 dB (Gaussian blocks) and 0.00 dB in every one of seven distributions once scale rounding is removed, and unchanged when UE4M3's range limit is removed; I_blk keeps 0.32 to 0.67 dB with exact scales (not identified, now labelled a crest-factor interaction); per-row I_fmt16 falls from 1.84 to 1.41 and 0.38 dB under per-token log-SDs of 2.5 and 3.5 while I_range32 rises from 0.19 to 0.64 and 1.45 dB. A UE4M3+FP32/B32 pair (S4) is added so the matched-storage crossing is measured at both block sizes (4.25 b and 4.5 b) and the range is diagnosed by I_range32 | Cells; Analysis (P2; range rule) | N3 `numerics-v2.json` identification table; D1v2 rank 10 of 10 |
| 3 | G1's runs were reused as Stage 1b cells, so passing G1 biased I_fmt and I_blk toward REFUTED (false REFUTED 0.09 to 0.18 against about 0.05) and C_anchor upward (identification refuter; reviewer 1; reviewer 2's largest defect) | The gate runs on its own runs in Phase 0 (J4, probe seeds 2001 to 2003); every Phase 1 cell, E2M1/S1 and E2M1/S3 included, runs on fresh seeds; no gate or sweep run enters any Phase 1 estimate. The "no winner's curse" sentence is now true and is checked: S1v2 replays v1's reuse on the same Phase 1 data | Probe decision; Steps B1-B3 | S1v2 gate-reuse table below |
| 4 | Phase 0 only certified the instrument: J3 is one seed and cannot give sigma, the anchor gap was first measured above 8 GPU-h, and Kevin would rule with both assumed (feasibility refuter; reviewer 1's runner-up; reviewer 2) | J4, the sigma-and-anchor probe: MX-like and NV-like on 3 probe seeds at Phase 1's full recipe, after J1. It measures the residual SD and the anchor gap; G1 (L90 > 0 at df 2) stops the line if the gap is unresolved; otherwise the Phase 1 seed count n (3 to 6) is set from C0 / sigma0 by a power rule, and a calibration kappa turns the frozen tensor prediction into nats. J4 runs only if Phase 0 stays at or below 8.0 GPU-h | Part A J4; Probe decision | S2v2: J4 cap 4.82 GPU-h at the central case (Phase 0 total 7.62); S1v2 decisiveness table |
| 5 | Phase 1's caps were miscomputed: the projections omitted the 0.9 factor of the registered formula, the 1.5x two-process packing headline is unlikely without MPS, and J0's cap was copied from another job (feasibility refuter; reviewer 1) | Every cap derived with its arithmetic shown; central single-process is the headline; J0 derived from its workload (ten quantizer compiles, conformance vectors, a 12.5 s FP64 GEMM check at 50 GEMMs per shape and cell) | Compute caps | S2v2: wave 1's central single-process cap was 125.3 GPU-h, not the 113.2 printed (with two processes 82.9, not 74.8); v2 Part B 70.1 to 97.4 at n = 3 to 6 |
| 6 | The probe cannot fit at wave 1's 1.2B tokens (6 FP4 runs at the central case need a 9.3 GPU-h cap) | Phase 1's budget is 0.6B tokens (9,155 steps, about 17 tokens per parameter, near compute-optimal for 35M) so J4 measures at Phase 1's own budget inside 8 GPU-h; Phase 1 roughly halves in cost | Model training | S2v2 |
| 7 | Tuning depth was confounded with the grid (both 5-point reference sweeps were E2M1; INT4 cells got 3-point sweeps centred on E2M1 LRs) (identification refuter (e); reviewer 1) | Every FP4 cell gets the same 3-point sweep centred on the BF16 tuned LR, with up to two extensions | Step B2 | S1v2 tuning bias reported |
| 8 | New in the repair: S1v2 under the registered estimator shows per-cell LR tuning error adds cell-level variance that seed blocks cannot see: 90% intervals of I_prec32 cover 0.84 to 0.86 and false confirmation reaches 0.08 to 0.09 in the flatter LR regime (curvature 0.005) | P2 is decided on 95% intervals (one-sided 2.5%); the seed-count rule uses the matching MDE; the 90% reading is reported beside it | Analysis (P2) | S1v2 operating characteristics below |
| 9 | Autocast is never disabled around the FP32 decoded-operand matmul, so S5 operands could silently be cast to BF16 (identification refuter (b); reviewer 1's top implementation catch) | Autocast disabled around all three quantized GEMMs; input dtypes asserted at step 1 and every 1,000 steps and written to every receipt; a receipt with the wrong dtype excludes the run | GEMM; Exclusions | registration only |
| 10 | The emulation control sat on E2M1/S3, whose BF16 decode is exact, so it could only see accumulation (identification refuter (a)) | The control moves to INT4/S5, whose BF16 decode is inexact for 42.6% of products (N1) | Emulation-path control; P5 | N1 |
| 11 | TorchInductor lowers FP32 division to approximate `div.full`, so eager and compiled paths will disagree on N1's 602 exact ties; E8M0's 2^-127 floor is an FP32 subnormal that flush-to-zero turns into 0/0; determinism was stated for J2 only; the SR rule's gfloat mapping was mirrored and unstated (feasibility refuter; reviewer 1, verified in the torch 2.11 source) | `TORCHINDUCTOR_EMULATE_DIVISION_ROUNDING=1` set and asserted; E8M0 and BF16-scale floors 2^-126 and a zero-block test; deterministic mode in J1, J2, J4 and Phase 1; SR mapped to gfloat StochasticFastest with srbits = 2^24 − 1 − R | Quantization and GEMM; J0 | registration only |
| 12 | PG5's F included the TF32-against-BF16 GEMM gap, which a fused quantizer cannot remove (identification refuter (c)) | J1 adds a TF32-operand baseline; F_quant isolates quantization overhead; TRITON_GATE needs F_total > 4 and F_quant > 2, else TF32_PATH_COST | PG5 | registration only |
| 13 | The endpoint uses each run's own quantized forward pass, so forward-pass noise enters every contrast (identification refuter (4); reviewer 1) | The BF16-forward loss of the same weights is a registered attribution endpoint: a decisive P2 is labelled IN_WEIGHTS only if it reaches the same verdict there; a small-model FP4 gap can sit mostly in forward rounding (OpenReview eEicXkAWDk, abstract) | Endpoints; Attribution | registration only |
| 14 | Novelty coverage: ARITH 2025 labelled closed though open on NSF PAR; 2302.08007 retrieved (KS-20) and never read; novelty row 4 overstated; "which no prior reports" about the block/scale split (novelty refuter; reviewer 1) | All three read in full and cited (C34 rewritten, C42 added); row 4 downgraded to low; the sentence now says "with intervals" (2505.19115 Fig. 2 trains the three E2M1 cells, single runs); 16 run-2 queries including OpenReview searches; two new items cited at abstract level (C43, C44) | Proposal only | `query-log-run2.json` |
| 15 | The data download was said to need Kevin's OK (feasibility refuter: D1 already authorizes public research downloads) | Recorded as a D1 download, logged with source, revision, size and SHA-256, through a CPU job under the host rule | Prerequisites | registration only |
| 16 | Process: the feasibility refuter ran no orx query; the query budget left exactly a minimal triad | This run declares 80 queries with 30 reserved for the triad; the repair used 16 | Header | `query-log-run2.json` |

Not repaired, and why:

- No harness, quantizer kernels, tokenized data, manifest, container smoke,
  Slurm dry run or orx node exists (Compute FAIL, cap 79). They come after a
  scored package and a freeze, and run 2 had no host mandate beyond the
  reviewer's lane job.
- Sigma, the anchor gap, the LR curvature and the dY spread are still
  unmeasured. J4 and J3 measure them in Phase 0; every operating
  characteristic below is a simulation under assumed distributions.
- G1 rests on residual df 2 (three paired probe seeds); more probe seeds do
  not fit under 8 GPU-h at the central cost case. Because J4 runs both
  configurations at one LR, its gap includes any difference in their optimal
  LRs; under a tuned-LR null with LR spread P(GO) is 0.06 to 0.29 across the
  simulated sigmas and curvatures (S1v2). That
  costs GPU time, not a false claim: Phase 1 re-tunes every cell and its tests
  stay calibrated.
- The secondary verdict family (prior generalised) keeps v1's 90% intervals
  and F-tests, which do not see LR tuning error; its realised false rates are
  reported, not corrected.
- Signed, provider-distinct reviews cannot exist here (D24, cap 89).
- The deterministic doctor parses `gpu_hours=0.3` as 0 and reports "all
  declared budgets must be positive"; the declared budget is honest and is not
  rounded up to pass.

Decisiveness after the repair (S1v2, `compute/repair-d68/power-sim-v2.json`;
the whole v2 decision path per replicate, 4,000 replicates per setting; sigma
is the per-run SD, with seed correlation 0.5; instrument gates assumed
passed; every distribution assumed). The gate is Phase 0's decision (G1 and
the seed count); "correct" is GO when the truth has a format effect and STOP
under the nulls; P2's correct verdict is CONFIRMED under the credited
mechanism, REFUTED under the reversed one, and anything but CONFIRMED (ABSENT
being the decisive reading) when I_prec32 is zero.

| Truth (registered effect size) | anchor, I_prec32 (nats) | gate correct | P2 given GO: CONFIRMED / REFUTED / ABSENT / UNRESOLVED (a = 0.02) | path ends correct and decisive | path ends wrong and decisive |
|---|---|---:|---|---:|---:|
| null, LR spread 0.25 | 0.000, +0.000 | 0.92 / 0.77 | 0.04 / 0.03 / 0.58 / 0.35 | 0.93 / 0.90 | 0.01 / 0.02 |
| null, no LR spread | 0.000, +0.000 | 0.96 / 0.94 | 0.03 / 0.03 / 0.04 / 0.89 | 0.96 / 0.94 | 0.00 / 0.00 |
| prior additive | 0.020, +0.000 | 0.99 / 0.92 | 0.03 / 0.02 / 0.92 / 0.03 | 0.91 / 0.85 | 0.08 / 0.05 |
| credited mechanism | 0.011, +0.012 | 0.88 / 0.73 | 0.94 / 0.00 / 0.03 / 0.03 | 0.81 / 0.69 | 0.03 / 0.02 |
| crest-factor only | 0.011, +0.000 | 0.86 / 0.74 | 0.03 / 0.03 / 0.77 / 0.17 | 0.62 / 0.57 | 0.08 / 0.04 |
| UE4M3 range only | 0.011, +0.000 | 0.86 / 0.74 | 0.03 / 0.03 / 0.77 / 0.17 | 0.61 / 0.57 | 0.08 / 0.04 |
| mechanism + range | 0.011, +0.012 | 0.86 / 0.74 | 0.94 / 0.00 / 0.03 / 0.03 | 0.79 / 0.70 | 0.03 / 0.02 |
| grid additive | 0.011, +0.000 | 0.87 / 0.73 | 0.03 / 0.03 / 0.77 / 0.17 | 0.61 / 0.56 | 0.08 / 0.04 |
| reversed | 0.011, -0.008 | 0.86 / 0.75 | 0.00 / 0.67 / 0.21 / 0.12 | 0.73 / 0.66 | 0.00 / 0.00 |

Each cell gives the LR-curvature regimes a = 0.005 and a = 0.02 (nats per
squared factor-of-2 step), "a = 0.005 / a = 0.02"; the P2 column is a = 0.02.
"Path ends correct and decisive" is P(STOP) + P(GO and ABSENT) under a null,
P(GO and CONFIRMED) under a positive I_prec32, P(GO and REFUTED, or ABSENT
when the true interaction is smaller than the anchor) under the reversed
truth, and P(GO and ABSENT) when I_prec32 is zero but an anchor exists.
"Wrong and decisive" is a CONFIRMED or REFUTED P2 against the truth's sign,
or an ABSENT when the true interaction exceeds the anchor. At sigma 0.002 the
mechanism's path ends correct 0.86 to 0.99; at sigma 0.008 the gate says GO
only about half the time and the path ends correct about 0.23 under the
mechanism, because J4's C0 is inflated in the replicates that pass and the
seed count it sets is then too small (wrong and decisive stays at or below
0.08). Under a tuned-LR null with LR spread the probe says GO 0.08 to 0.23 of
the time, from the configurations' different optimal LRs at the common probe
LR (real differences at that LR; Phase 1 then reads ABSENT or UNRESOLVED).

## Scope and what changed from the dossier

This proposal covers the first step only: Phase 0 (bit-exact tests of the
fake-quant kernels against independent reference quantizers, the GEMM model,
throughput, resume equivalence, a BF16 capture run whose tensors fix a
numerics prediction, and the sigma-and-anchor probe J4) and the design of
Phase 1 (the emulated grid by scale-configuration factorial). The rounding
factor, RHT, UE5M3 and a 125M replication are later steps with their own
registration.

Wave 1 merged four discovery cells by mechanism into fifteen design changes
to the dossier (`program/evidence/2026-10-06/question-dossier.md`, section 8);
the table is kept with each row's v2 status.

| # | Mechanism (cells that found it) | What it does to the dossier's design | v2 status |
|---:|---|---|---|
| M1 | Matched storage makes block size and scale width collinear (kill-shot, cross-domain); the dossier's four levels give rank 8 of 10 | Full-rank cell set | v2 adds S4 (UE4M3+FP32/B32): rank 10 of 10, matched storage within each block size (D1v2) |
| M2 | The residual is narrower than the dossier said (frontier, kill-shot) | Claim restricted to the grid x scale crossing | narrowed further: the mechanism is credited to 2510.25602 and ARITH 2025 |
| M3 | Crest-factor theory predicts a grid x scale interaction (frontier, kill-shot, synthesis) | Wave 1 owned it as H_int and tested it through I_fmt and I_blk | credited; P2 reads only the identified I_prec32; I_blk relabelled a crest-factor interaction |
| M4 | The declared GEMM model is not uniform across cells (N1) | One exact decoded-operand TF32 path | kept; S4 inherits S3's exactness (block size does not change the decoded set) |
| M5 | FP32 accumulation is not IEEE FP32; BF16 reduced-precision reduction on by default | Flags pinned and asserted | kept; autocast disabled around quantized GEMMs, dtypes asserted |
| M6 | Bit-exact needs pinned interpretation choices | Spec pinned | kept; division flag, 2^-126 floors, gfloat SR mapping added |
| M7 | Confounds outside the four factors (RHT, per-tensor scaling, scale rule, Wgrad, norms, final blocks, execution path) | Held fixed and declared | kept |
| M8 | The study may be too small to see anything | Stage 1a gate above 8 GPU-h | replaced by J4 inside Phase 0, under 8 GPU-h, on its own seeds |
| M9 | Undertuned baselines and the winner's curse | Five-point sweeps for references, three for others | one 3-point protocol for every FP4 cell around the BF16 tuned LR; tuning error handled by 95% decision intervals |
| M10 | Instability at the tuned LR is likely rare at 35M | Loss gap primary; spikes secondary | kept |
| M11 | Seed structure | Three RNG streams per seed, seed blocks | kept; probe seeds disjoint from Phase 1 seeds |
| M12 | E1M2 is aliased with INT4 | Metamorphic test only | kept |
| M13 | Cost is unmeasured and wide | J1 and a cap formula | kept; formula arithmetic corrected (the 0.9 factor), J0 derived, J4 formula |
| M14 | The pipeline and data do not exist | Harness, tokenizer and data pins | kept; data under D1 |
| M15 | Scoop and access risk | Coverage limits | ARITH 2025 now read; an ICLR 2027 submission (gap location) and the ICML 2026 record of 2510.25602 added at abstract level |

The eight corrections to the frozen dossier recorded by wave 1 stand
(Zenodo 22554253 was read; the closest priors were 2505.19115, 2509.17791 and
2603.28765; the dossier's two-way ANOVA was rank-deficient; its GEMM model was
inexact for the BF16-scale cell; E1M2 is INT4 times 1/4; its 47 GPU-h was
unmeasured; its three-point LR sweep was too narrow; its seed anchor 0.001 is
0.00195 from the printed values). Run 2 adds two: the dossier's first
experiment (1.2B tokens) is now 0.6B tokens so that Phase 0 can measure sigma
at Phase 1's budget; and the dossier's framing of the grid-by-scale question
as open understated the published theory (2510.25602, ARITH 2025).

## Claim and Research Question

**Question.** In emulated 4-bit training of a 35M-parameter Llama-style model
(d 384, 6 layers, SwiGLU 1024, vocabulary 32,000) on 0.6B FineWeb-Edu tokens,
with the known non-format causes held fixed, how does the element grid (E2M1
against symmetric INT4, 15 codes each) cross with the block-scale
configuration at matched storage (E8M0 against UE4M3 with an FP32 tensor
scale, at 32-element blocks with 4.25 bits per element and at 16-element
blocks with 4.5), and does replacing a power-of-two block scale by a BF16
block scale at the same block size and exponent range help INT4 more than
E2M1 in final validation loss, as Theorem 1 of 2510.25602 predicts at tensor
level?

The variables are the grid (2 levels) and the scale configuration (5 levels:
S1 E8M0/B32, S2 E8M0/B16, S3 UE4M3+FP32/B16, S4 UE4M3+FP32/B32, S5 BF16/B32),
crossed (10 cells), plus a BF16 reference and one emulation-path control
(INT4/S5 on the common BF16 path).

**Claim scope.** `systems-pipeline` (training numerics under one declared
emulator). Not `architecture-causal`: no architecture is proposed. No claim to
the mechanism, which is published theory. No claim about native FP4 hardware
speed, energy or kernels, about RHT, about rounding modes, about UE5M3, or
about scales above 35M and 0.6B tokens. The claims the design can license
have the forms: "at 35M under exact decoded-operand TF32 emulation, replacing
E8M0 by BF16 block scales at B32 helped INT4 more than E2M1 by X nats (95%
interval), or the difference was smaller than the MX-like versus NV-like gap
in both directions"; "the grid crossed with E8M0 against UE4M3 scales at
matched storage by Y at B32 and Z at B16, with or without UE4M3 range
exposure"; "the MXFP4-to-NVFP4 analogue gap splits into a scale step and a
block step of these sizes, in either order"; "35M on 0.6B tokens cannot
resolve the MX-like versus NV-like gap".

**Hypotheses under test.** H_pow2 (published, 2510.25602 Theorem 1, the
claim P2 tests): with block size and exponent range fixed, a power-of-two
block scale costs the uniform grid more than the floating-point grid, so
I_prec32 > 0 in training loss. H_sep (the design prior's ranking,
2505.19115 and 2509.17791 with E2M1 fixed): with the grid varied, the scale
encoding still dominates the grid and the interactions are smaller than the
scale effect (secondary verdict PRIOR_SURVIVES).

## Strategic Fit and Why Now

C5 is item 4 of the backfill queue (`program/backlog.md`); D67 restarted it and
D68 ordered this repair. Its score packages Phase 1 for Kevin's D24 ruling; it
is not an admission. Why the measurement is worth its cost now:

- **The theory exists and its training-time test does not.**
  2510.25602 ([arXiv](https://arxiv.org/abs/2510.25602)) derives the
  power-of-two penalty on INT and the INT-against-FP crossovers, and tests
  them on tensors and in direct-cast inference; it trains only at 8 bits. The
  ARITH 2025 study (open copy, NSF PAR 10628832) measures the INT4 penalty
  under E8M0 on weight tensors and trains E2M1 only. 2603.28765
  ([arXiv](https://arxiv.org/abs/2603.28765)) trains NVINT4 against NVFP4 at
  one scale setting. Format designers draw opposite conclusions from the same
  theory: 2606.20381 argues for a uniform grid after rotation, and the
  ICML 2026 record of 2510.25602 ([OpenReview](https://openreview.net/forum?id=1GIYHWO9S5),
  abstract) now states that MXINT4 is superior to MXFP4, against arXiv v1's
  finding that MXINT4 lags without rotation. A seed-replicated training
  measurement of the crossing at matched storage tests whether the
  tensor-level ranking survives training.
- **The emulation literature has a numerics defect worth reporting.**
  Decoding a BF16-scaled block to BF16 rounds 28.5% to 42.6% of operands (N1;
  reviewer 1 re-derived 28.5% analytically: 3 of 7 nonzero E2M1 magnitudes
  times 85 of 128 significands); folding an FP32 tensor scale into operands
  rounds 79%. Phase 0's conformance and containment suite is reusable; the
  emulation-path control now sits on the cell where the common path is most
  inexact.
- **Cheap, decision-bearing stopping points.** Phase 0 stays at or below 8.0
  GPU-h by construction and now ends in a decision (STOP_UNRESOLVED_AT_35M,
  or GO with a seed count), measured at Phase 1's own budget.

The area is crowded. At least six FP4 pretraining submissions to ICLR 2027
appeared in September 2026 (wave 1's frontier cell); run 2 read the
abstracts of three ICLR 2027 submissions that bear on the design (eEicXkAWDk, gap location; 6xNJZSLSjl,
mean bias; CzwnhuTaBw, scale search), none of which crosses the grid with
the scale. The scoop risk is concrete (M15).

## Primary-Source Evidence

Every row was opened by a discovery cell, by synthesis or by the repair
owner. "Full" means the full text read by targeted section; "abstract" means
abstract or metadata only. First-party marks a number not independently
replicated; single trajectory marks a number from one run. Claim ids are the
Citation doctor's registry (`doctors/citation.json`). Run 2 rewrote C05 and
C34 after full reads and added C42 to C44. N1, N2, D1, S1 and S2 are wave 1's
computations (they reproduce byte for byte); N2v2, N3, D1v2, S1v2 and S2v2 are
run 2's.

| id | Claim used here | Source | Date | Read | Status |
|---|---|---|---|---|---|
| C01 | 350M Llama, E2M1, B16: seven 8-bit scale encodings E1M6 to E8M0 (all 4.5 b); E1M6 diverges, E3M4 and E4M3 best; block sizes 8 to 128 under E8M0 and E4M3 (Fig. 2, so E8M0/B32, E8M0/B16 and E4M3/B16 are trained with E2M1, single runs); SR per operand; a sqrt(3) gradient-noise threshold; App. Table 4: 125M, 30B tokens, five seeds, stated SD 0.001 (sample SD of the printed values 0.00195, N1); code public | [2505.19115](https://arxiv.org/abs/2505.19115) Sec. 3.1, Figs. 1-3, 7, Sec. 4, App. Table 4; [code](https://github.com/Anonymous1252022/fp4-all-the-way); NeurIPS 2025 spotlight per [OpenReview kuzye4EPLR](https://openreview.net/forum?id=kuzye4EPLR) | 2025-05-25 (v2 2025-08-10) | full (frontier, kill-shot, synthesis, novelty refuter) | verified; single runs per sweep |
| C02 | Thousands of configurations; E2M1 throughout; "Scale Representation is the Primary Bottleneck"; E4M3 with tensor scaling did not converge; UE5M3 outperforms E8M0 with tensor scaling and SR; could not replicate 2505.19115 up to 1B | [2509.17791](https://arxiv.org/abs/2509.17791) Principle 2, App. .3, Conclusion; ICLR 2026 rejected per [OpenReview OEXOAMvsc6](https://openreview.net/forum?id=OEXOAMvsc6) | 2025-09-22 | full (frontier, kill-shot, asset, synthesis) | verified; not peer-reviewed |
| C03 | 340M W4A4G4 pretraining (final four layers excepted), RHT on Wgrad, SR on activation gradients, FP32 decode; NVFP4 "strictly better than NVINT4 when used to quantize all tensors"; symmetric INT4 | [2603.28765](https://arxiv.org/abs/2603.28765) Sec. 4.1, Fig. 5a, App. A, footnote 3; [code](https://github.com/mit-han-lab/fouroversix) | 2026-03-30 | full (frontier, kill-shot, synthesis, novelty refuter) | verified; no seed replication found |
| C04 | Grid E2M1 against E1M2/INT4 with RHT scope varied, FP32 single-level scale; SQNR: E2M1 leads before rotation, E1M2 after; "Scale hierarchy design remains orthogonal" (asserted, not tested) | [2606.20381](https://arxiv.org/abs/2606.20381) Sec. 4, Table 1, Sec. 5.2; ICLR 2027 submission [OpenReview bub7HTzeSv](https://openreview.net/forum?id=bub7HTzeSv) | 2026-06-18 | full (kill-shot, synthesis) | verified |
| C05 | Theorem 1: INT QSNR ≈ 4.78 + 6.02 b − 20 log10(rho) − 20 log10(kappa) under a UE8M0 scale, rho in [1, 2) ("UE8M0 scaling incurs up to 20 log10(rho) ≤ 6.02 dB loss"); an E4M3 scale is treated as rho = 1 "since it is close to BFloat16 scales", with a 10 log10(g/(g−1)) gain. Theorem 2: FP QSNR ≈ 13.80 + 6.02 M with ample range, "independent of block granularity". Crossovers: MXINT4 beats MXFP4 iff kappa < 2.04, NVINT4 beats NVFP4 iff kappa < 2.39. Llama-3.1-8B tensors: B32 median crest 2.48, Q3 2.96; B16 median 2.16, Q3 2.39; NVINT4 wins 64.3% of blocks, mean QSNR 20.55 against 20.60. Direct-cast inference: MXINT4 and NVINT4 lose on 12 of 12 models without rotation, NVINT4 wins 12 of 12 with it. Training at 8 bits only (Llama-1B, 100B tokens) | [2510.25602](https://arxiv.org/abs/2510.25602) Eq. 12-14, Theorems 1-2 and interpretations, Fig. 3, Table 2, Secs. 5.1-5.3; [code](https://github.com/ChenMnZ/INT_vs_FP) | 2025-10-29 (v1) | full (run 2 owner, text sha256 5c3301ee...; cells and reviewer 1 earlier) | verified |
| C06 | UE5M3 maximum 61,440, smallest subnormal 2^-17; E4M3 maximum 448; one seed-42 8B trajectory per configuration; decoded-operand control in FP32; B16 probe-matched 2.3090, decoded-operand 2.3157, B32 2.3241 | [2609.02846](https://arxiv.org/abs/2609.02846) Eq. 3, Table 2, Secs. 6.1-6.3, Table 10; [code](https://github.com/MrHuff/ue5m3-fp4) | 2026-09-02 | full (all cells, synthesis) | verified; single trajectory |
| C07 | MXFP4 = E2M1/UE8M0/B32, NVFP4 = E2M1/E4M3/B16 (block and scale change together); MXFP4 matches NVFP4 loss with 36% more tokens (8B); Hadamard choices show no measurable effect at 1.2B | [2509.25149](https://arxiv.org/abs/2509.25149) Table 1, Secs. 4-5, App. A.3, E.4.1 | 2025-09-29 (v2 2026-03-04) | full (kill-shot, frontier, synthesis) | verified |
| C08 | MXFP4 4.25 b, NVFP4 and HiF4 4.5 b; NVFP4 does not converge without per-tensor scaling; 1B margins inside seed noise | [2604.08826](https://arxiv.org/abs/2604.08826) Secs. 3, 5.1, Table 3, Limitations | 2026-04-09 (v2 2026-09-25) | full (kill-shot, synthesis) | verified |
| C09 | Native MXFP4 on MI355X: quantizing Wgrad is "the primary driver of convergence degradation" | [2605.09825](https://arxiv.org/abs/2605.09825) abstract, Sec. 3.2 | 2026-05-11 (v4 2026-08-12) | full (kill-shot, frontier) | verified |
| C10 | 366 training runs over exponent bits, mantissa bits and block size with high-precision block scales | [2501.02423](https://arxiv.org/abs/2501.02423) Secs. 3, 3.6 | 2025-01-05 (v3 2025-06-04) | full (all cells) | verified; ICML 2025 |
| C11 | Quantizing LayerNorm affine parameters drives microscaling instability | [2506.20752](https://arxiv.org/abs/2506.20752) abstract; [OpenReview IuigXFBGHI](https://openreview.net/forum?id=IuigXFBGHI) | 2025-06-25 | full (frontier) | verified; preprint |
| C12 | 8B, 160B tokens: native MXFP4 recipe 2.11% above BF16, TE NVFP4 with four final BF16 blocks 0.87%; outcomes depend jointly on scale contract, operand and execution path | [2610.00053](https://arxiv.org/abs/2610.00053) | 2026-09-04 | full (frontier, kill-shot, asset) | verified; single trajectory |
| C13 | Backward-error 2x2 (block {16, 32} x scale {E8M0, E4M3}), E2M1 fixed; scale moves error more than block size in all 40 cells; transfer to training untested | [Zenodo 22554253](https://zenodo.org/records/22554253) | 2026-09-06 | full (frontier) | verified; single author |
| C14 | Below a block-size threshold, quality degrades with UE4M3 scales (narrow distributions against limited scale range); UE5M3 obviates global scaling; PTQ | [2601.19026](https://arxiv.org/abs/2601.19026) abstract, Sec. 4.3 | 2026-01-26 | full (frontier, kill-shot) | verified |
| C15 | The block-size paradox is partly an artifact of absmax scale selection; in the subnormal range the E4M3 scaling grid is extremely coarse; PTQ | [2605.08565](https://arxiv.org/abs/2605.08565) abstract, Secs. II, III.A | 2026-05-08 (v2 2026-06-08) | full (frontier, asset, identification refuter) | verified |
| C16 | Absmax scaling under-uses the E2M1 grid for heavy-tailed tensors | [Half-S, Findings of ACL 2026](https://aclanthology.org/2026.findings-acl.241.pdf) | 2026 | full PDF (frontier) | verified |
| C17 | H100 tensor cores with 16- and 19-bit inputs and FP32 output use 2 extra alignment bits and truncate | [2512.07004](https://arxiv.org/abs/2512.07004) Secs. 4.1.6-4.1.7 | 2025-12-07 (v4 2026-06-11) | full (cross-domain, synthesis) | verified |
| C18 | The BF16 reduced-precision-reduction flag is on by default and can be set False | PyTorch 2.14 notes, https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html | read 2026-10-10 | full page | verified; the image runs torch 2.11, so Phase 0 asserts the value |
| C19 | Bitwise GEMM results are set mainly by reduction order | [2609.11356](https://arxiv.org/abs/2609.11356) | 2026-09-10 | full (cross-domain) | verified |
| C20 | Few-bit SR implementations are biased (2 bits: −0.124 ulp) | [2504.20634](https://arxiv.org/abs/2504.20634) Figs. 1-2 | 2025-04-29 | full | verified |
| C21 | P3109 SR modes with explicit random-bit counts | [2606.04028](https://arxiv.org/abs/2606.04028) Sec. IV | 2026-06-01 | full (cross-domain) | verified |
| C22 | Vendors do not document MX bitwise behaviour; gfloat and the MX library as references | [2607.12915](https://arxiv.org/abs/2607.12915) | 2026-07-14 | full | verified |
| C23 | Conformance packs cross-validated against ml_dtypes; OCP permits saturating and NaN E4M3 overflow | [2606.09686](https://arxiv.org/abs/2606.09686) | 2026-06-08 (v3 2026-09-04) | full | verified; weak source |
| C24 | LR sensitivity over three orders of magnitude; small models reproduce large-scale instabilities at high LR | [2309.14322](https://arxiv.org/abs/2309.14322) Sec. 2.2 | 2023-09-25 | full | verified |
| C25 | Spike score: values at least 7 SD from a rolling mean of 1,000 | [2501.00656](https://arxiv.org/abs/2501.00656) | 2024-12-31 (v3 2025-10-08) | full | verified |
| C26 | Small models are much more hyperparameter-sensitive | [2608.11859](https://arxiv.org/abs/2608.11859) Secs. 1, 4.1 | 2026-08-12 | full | verified |
| C27 | One-bit changes in initial parameters give vastly different models | [2103.04514](https://arxiv.org/abs/2103.04514) | 2021-03-08 | full | verified |
| C28 | Initialisation and data order contribute comparably to fine-tuning variance | [2002.06305](https://arxiv.org/abs/2002.06305) | 2020-02-15 | report | verified |
| C29 | FP and INT formats at 30M to 200M, forward-only QAT; Gaussian-MSE capacity tracks loss | [2506.01863](https://arxiv.org/abs/2506.01863) | 2025-06-02 | full | verified; forward-only |
| C30 | Several 4-bit grids at 30M to 100M under E4M3/B16, forward-only QAT | [2605.12327](https://arxiv.org/abs/2605.12327) Sec. 5.3 | 2026-05-12 | full | verified; forward-only |
| C31 | Transposition-inconsistent 1D blocks as an FP4 instability cause | [2607.24953](https://arxiv.org/abs/2607.24953) | 2026-07-27 | abstract | verified at abstract level |
| C32 | MXFP4 with Hadamard, SR, overflow-aware scaling and a macro block scale claims to cut MXFP4's extra tokens from 36% to 0.21% | [OpenReview 18UVn4y0SO](https://openreview.net/forum?id=18UVn4y0SO) | 2026-09-18 | abstract | UNVERIFIABLE_ACCESS full text |
| C33 | NVFP4 recipe ingredients at 8B and 30B-A3B | [OpenReview jlkIyaG32w](https://openreview.net/forum?id=jlkIyaG32w) | 2026-05-08 | abstract | UNVERIFIABLE_ACCESS full text; venue discrepancy |
| C34 | Yang et al., MX formats in Llama3 pretraining: training runs E2M1 (E3M0 for gradients) under E8M0 with Floor, Ceil and Even scale rounding (Figs. 4, 5, 12; 7B, up to 100M tokens); INT4 only in R-MSE on weight tensors; Insight 3: with E8M0, E2M1 is best with Even, INT4 with Ceil, and E2M1 beats INT4 under default MX; Insight 5 and Fig. 9: B32 to B16 under symmetric scaling lowers INT4's R-MSE about 6.47 times as much as E2M1's; Fig. 6: normalized R-MSE correlates with the training-loss gap when weight quantization is varied; no non-power-of-two scale anywhere | ARITH 2025, DOI 10.1109/ARITH64983.2025.00011; open copy https://par.nsf.gov/servlets/purl/10628832 (PDF sha256 d1d5b8e3...) | 2025 | full, end to end (run 2 owner; novelty refuter and reviewer 1 earlier) | verified (wave 1's UNVERIFIABLE_ACCESS was wrong) |
| C35 | Second-order theory of GEMM quantization noise: INT constant, FP multiplicative variance profile; PTQ W4A4 | [2609.08135](https://arxiv.org/abs/2609.08135) | 2026-09-08 (v2 2026-09-27) | abstract | verified at abstract level |
| C36 | FP8 SwiGLU outlier instabilities appear only in trillion-token training | [2409.12517](https://arxiv.org/abs/2409.12517) | 2024-09-19 | abstract | verified at abstract level |
| C37 | FineWeb-Edu: ODC-BY, ungated, revision 87f09149; files 000 and 001 are 2,152,819,114 and 2,152,222,432 B | [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) HF API | read 2026-10-10 | API | verified |
| C38 | Mistral-7B-v0.1 tokenizer: Apache-2.0, revision 27d67f1b, vocabulary 32,000 | [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) HF API | read 2026-10-10 | API | verified |
| C39 | Reference implementations: gfloat 0.5.2 (MIT, SR modes), microxcaling (MIT, power-of-two only), TransformerEngine NVFP4 reference (Apache-2.0), ml_dtypes 0.6.0 | [gfloat](https://github.com/graphcore-research/gfloat), [microxcaling](https://github.com/microsoft/microxcaling), [TransformerEngine](https://github.com/NVIDIA/TransformerEngine) | read 2026-10-10 | GitHub API and README | verified |
| C40 | Semantic Scholar forward citations of seven priors: 74 unique citing works, none crossing grid with scale format in training | Semantic Scholar Graph API via host relay | 2026-10-10 | titles | screened |
| C41 | Repository anchors: 134M GDN hybrid 282,501 tok/s (Slurm 359); a GPU unit-test job 0.0044 GPU-h (job 516); start-up about 10 s per arm (K1 probe 543); image digest `sha256:13a9de83...` | `legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json` | 2026-09-01 to 2026-10-08 | repository | measured on a different model |
| C42 | Over 800 block-format configurations analysed by QSNR; a "strong Pearson correlation" between the QSNR analysis and language-model loss in end-to-end training in the narrow bit-width regime (coefficient not given); Fig. 7 includes FP4 E2M1, E1M2, E3M0 and scaled INT4 | [2302.08007](https://arxiv.org/abs/2302.08007) Sec. IV-A, Fig. 7 (ISCA 2023) | 2023-02-16 (v2 2023-04-13) | full (run 2 owner, text sha256 ab339035...) | verified |
| C43 | The ICML 2026 record of 2510.25602 states that INT "consistently surpasses" FP as blocks shrink and that MXINT8 and MXINT4 are superior to their FP counterparts; arXiv v1 (C05) finds MXINT4 behind MXFP4 without rotation; an ICLR 2026 submission of the same paper was withdrawn (OpenReview gMUZ8GKRFf) | [OpenReview 1GIYHWO9S5](https://openreview.net/forum?id=1GIYHWO9S5) | 2026 | abstract (run 2 owner, OpenReview search API) | UNVERIFIABLE_ACCESS full text; version discrepancy |
| C44 | In one FP4 recipe at three sizes, nearly all of a small model's gap to BF16 comes from forward-pass rounding; a switch to BF16 removes the share from rounding still in progress at once | [OpenReview eEicXkAWDk](https://openreview.net/forum?id=eEicXkAWDk) (ICLR 2027 submission) | 2026 | abstract (run 2 owner) | UNVERIFIABLE_ACCESS full text |

## Closest Prior Work

Ranked by closeness to what this proposal tests and measures.

1. **The mechanism prior: INT v.s. FP** ([2510.25602](https://arxiv.org/abs/2510.25602),
   Chen et al.; ICML 2026 per its OpenReview record), **with the ARITH 2025
   microscaling study** (Yang et al., open copy on NSF PAR). Same: the
   mechanism. Theorem 1 is the power-of-two penalty on the uniform grid that
   P2 tests; the crossovers are a tensor-level grid-by-scale interaction; the
   ARITH study adds the grid-by-block interaction under E8M0 on weight
   tensors (Insight 5) and an error proxy that correlates with training-loss
   gaps (Fig. 6). Different: neither trains a 4-bit integer grid
   (2510.25602 trains at 8 bits; ARITH trains E2M1 and E3M0 only, under E8M0
   only), neither crosses grids with non-power-of-two scales in training, and
   neither has seeds for any 4-bit comparison. The theory treats an E4M3
   scale as overhead-free, so it does not separate UE4M3's precision from its
   range; v2 does (S4 against S5). This proposal adds no mechanism. It adds a
   seed-replicated training measurement of the crossing at matched storage, a
   test of Theorem 1's prediction that block size and range cannot produce,
   and a frozen per-cell prediction calibrated by a probe. The prior is the
   stronger contribution on theory and breadth (twelve models, many formats).
2. **FP4 All the Way** ([2505.19115](https://arxiv.org/abs/2505.19115)).
   The closest design: training with all three GEMMs quantized, scale-encoding
   and block-size sweeps with E2M1 (Fig. 2 trains E8M0/B32, E8M0/B16 and
   E4M3/B16, single runs), per-operand rounding ablations, a sqrt(3)
   threshold and a trillion-token recipe. The grid is E2M1 in every run. It
   is the stronger contribution on rounding, scale-encoding breadth and scale.
3. **Adaptive Block-Scaled Data Types (IF4)** ([2603.28765](https://arxiv.org/abs/2603.28765)).
   E2M1 against symmetric INT4 in W4A4G4 pretraining at one scale setting
   (E4M3/B16) with RHT on; no seed replication found. One column of the
   crossing (S3), at 340M with rotation.
4. **UFP4** ([2606.20381](https://arxiv.org/abs/2606.20381)). Grid crossed
   with RHT scope at one FP32 single-level scale; asserts that the scale
   hierarchy is orthogonal without testing it.
5. **Shared microexponents** ([2302.08007](https://arxiv.org/abs/2302.08007)).
   QSNR over 800 block formats, strongly correlated with training loss; the
   reason P6 and the calibrated prediction are not claimed as new.
6. **Elucidating the Design Space of FP4 Training** ([2509.17791](https://arxiv.org/abs/2509.17791)).
   E2M1 fixed; "scale representation is the primary bottleneck"; the ranking
   H_sep generalises.

Also relevant, not closest: 2609.02846 (UE5M3, emulator control, single 8B
trajectories), 2509.25149 and 2604.08826 (the MXFP4-NVFP4 gap), 2501.02423
(grid and block in 366 runs with high-precision scales), Zenodo 22554253
(numerics-only 2x2), 2601.19026 and 2605.08565 (UE4M3 range and block size in
PTQ, the basis of the range rule), 2506.01863 and 2605.12327 (grids at 30M to
200M, forward-only QAT), 2609.08135 (a GEMM noise law, PTQ), OpenReview
eEicXkAWDk (where a small model's FP4 gap sits, the basis of the attribution
endpoint).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Grid (E2M1, INT4) crossed in training with power-of-two and 8-bit floating-point block scales at matched storage, at two block sizes | 2510.25602 (tensor and inference; trains at 8 bits); ARITH 2025 (INT4 at tensor level; trains E2M1 under E8M0 only); 2603.28765 (training at the NV setting only); 2505.19115 (E2M1 only) | The crossing as a tensor-level prediction; single columns in training | The crossing measured in training, seed-replicated, with all grid interactions estimable (rank 10 of 10) | medium-low (the direction is predictable from theory; ARITH full text now read) |
| Identified test of the power-of-two penalty: E8M0 against BF16 block scales at the same block size and exponent range (P2, I_prec32) | 2510.25602 Theorem 1 (the prediction); ARITH 2025 Insights 3 and 5 | The mechanism and its tensor-level evidence | A training-loss test that crest factor and UE4M3 range cannot produce (N3), decided with seeds, an equivalence band and an attribution endpoint | low-medium (it tests published theory) |
| Matched-storage crossing with a UE4M3 range rule (S4, I_range32, subnormal shares) | 2601.19026, 2605.08565 (UE4M3 range, PTQ); 2510.25602 (treats E4M3 scales as overhead-free) | UE4M3 range as a quality limit | Range separated from scale precision in training (S4 against S5) | medium |
| Decision-bearing probe of sigma and the anchor at Phase 1's budget, on its own seeds, setting the seed count | 2509.25149, 2604.08826 (the gap) | The gap | Used as a registered, non-reused gate with a power rule | low as novelty (design) |
| Exact uniform emulation (TF32-exact decoded operands, epilogue tensor scales, containment, dtype assertions) | 2609.02846 (FP32 decoded-operand control); 2603.28765 (FP32 decode) | Decode to FP32 | A shown defect of BF16 decode (N1), per-cell containment, the control on the most inexact cell | low as novelty (instrumentation) |
| Frozen tensor-level prediction, calibrated by the probe and tested on seed-replicated training (P6, kappa) | 2302.08007 (QSNR correlates with LM loss); ARITH 2025 Fig. 6; 2510.25602 | QSNR or R-MSE as a predictor of training loss | Per-cell, per-role prediction frozen before the probe and tested against seeded training | low (downgraded from wave 1's medium) |

Novelty wording: No direct prior art found through 2026-10-10 under the
recorded coverage (wave 1: 114 counted orx discover invocations in
`query-log.json`, FR-01 to FR-38, KS-01 to KS-26, XD-01 to XD-32 (35
invocations), AS-01 to AS-08, SY-01 to SY-07, 568 unique ids, 10 OpenReview
searches, Semantic Scholar forward citations of seven priors, 58 full-text
reads and 16 re-reads; run 2: 16 counted queries R2-01 to R2-16 in
`query-log-run2.json`, 209 unique ids, and full reads of 2510.25602,
2302.08007 and the ARITH 2025 study; the gaps in the Coverage limits line) for
a training study that crosses a floating-point and a uniform 4-bit grid with
power-of-two, 8-bit floating-point and 16-bit block scales at matched storage,
with seed replication, one exact emulation path, and a test of the
power-of-two penalty that block size and scale range cannot produce. Run 2's
queries aimed at the reframed claim: R2-01 (keyword: power-of-two scale, INT4
penalty, E8M0, BF16 block scale, training loss), R2-02 (keyword: 2510.25602's
title), R2-03 (keyword: the ARITH 2025 title; it is not on arXiv), R2-04
(embedding: the v2 design in plain words), R2-05 (keyword: UE4M3 subnormal
range, gradients, INT4, NVINT4), R2-06 (keyword: NVINT4 MXINT4 pretraining,
published after 2026-08-15; returned only generic pretraining work), R2-07 and
R2-15 (OpenAlex; HTTP 429), R2-08 (keyword: scale mantissa bits, INT4, FP4,
training ablation, BF16 scale), R2-09 (keyword: QSNR predicts training loss),
R2-10 (embedding: the mechanism prior's prediction tested in training),
R2-11 (keyword: crest factor, INT and FP 4-bit training), R2-12 (keyword:
seed variance of final loss in small LMs), R2-13 and R2-14 (OpenReview:
MXINT4 NVINT4 training; INT4 FP4 block scale pretraining), R2-16 (keyword:
the gap-location submission's terms; no arXiv copy). They returned
2510.25602, 2603.28765, 2605.31035, 2609.02846, 2606.20381, 2607.04422,
2608.01847, 2605.12464 and others, and on OpenReview eEicXkAWDk, 6xNJZSLSjl,
CzwnhuTaBw and the two records of 2510.25602; none trains the two grids under
both power-of-two and non-power-of-two block scales. PRISMA across both runs:
568 + 209 unique ids identified and screened by title (overlapping), 74
forward citations screened by title, 61 full texts read (58 by wave 1's cells,
3 by the repair owner), 0 included as a direct prior.

## Mechanism and Falsifiable Predictions

**Mechanism (published; credited).** A block's elements are divided by a
scale s chosen so the block maximum maps at or below the grid's top code.
2510.25602 models the low-precision scale as s' = rho s. A power-of-two scale
rounded up has rho in [1, 2): the block maximum lands anywhere in
(q_max/2, q_max], and Theorem 1 charges the uniform grid 20 log10(rho) dB,
because its absolute step is fixed and every element's error scales with s'.
A floating-point grid's relative spacing is roughly constant across its
binades, so with ample range its QSNR is set by its mantissa width (Theorem 2)
and the overshoot costs it little. With a fine scale (BF16: rho below 1.008;
UE4M3: rho below 1.125 in its normal range) the comparison reduces to the
crest-factor trade: the uniform grid wins for light-tailed blocks and loses
for heavy-tailed ones (crossovers 2.04 and 2.39). The ARITH 2025 study's
Insight 5 is the block-size face of the same arithmetic under E8M0.

**What v2 tests.** Whether that tensor-level mechanism reaches training loss.
P2 reads I_prec32, which isolates rho: S1 and S5 share block size (32) and
exponent range (an 8-bit exponent), and differ only in the scale's mantissa
(0 bits against 7). N3 with the registered quantizer
(`compute/repair-d68/numerics-v2.json`, seven synthetic distributions, seeds
42 to 44):

- I_prec32 (loss direction) is +2.17 dB for Gaussian blocks, +1.23 Laplace,
  +0.05 Student-t(3), −0.68 with 2% outlier channels, and +2.15 to +2.44 for
  gradient-like rows with per-token log-SDs 1.5 to 3.5; +2.15 to +2.80 after
  rotation. It is 0.00 dB in every distribution once scale rounding is
  removed, and unchanged when UE4M3's range limit is removed. In noise-power
  units it is positive in every distribution, 0.58 to 3.96 times the
  anchor's noise-power gap; dB and noise power disagree in sign for the
  outlier-channel distribution (−0.68 dB against +0.58) and nearly so for
  Student-t(3) (+0.05 dB against +0.82), so the frozen sign and size beside P2
  are registered in noise-power units, the units in which a first-order loss
  response is linear.
- The block-size interactions I_blk_E8 and I_blk_UE keep 0.32 to 0.67 dB
  with exact scales: they are crest-factor effects (as wave 1's refuter
  showed) and are reported as such, not as tests of the power-of-two
  mechanism.
- The matched-storage crossings I_fmt16 and I_fmt32 equal I_prec32 to within
  about 0.4 dB when UE4M3's range is not binding, but with wide per-token
  spreads the per-row version of I_fmt16 falls from 1.84 to 1.41 dB (log-SD
  2.5; 33% of UE4M3 block scales subnormal, 13% clamped) and to 0.38 dB
  (log-SD 3.5; 73% and 54%), while I_range32 rises from 0.19 to 0.64 and
  1.45 dB. Whole-tensor QSNR cannot see this (wave 1's refuter); the range
  rule uses the per-row shares.

Whether training loss follows depends on which operands dominate, which is
why Phase 0 recomputes the prediction on captured tensors and freezes it
before the probe.

**Predictions and registered falsifiers (kill criteria).** P2 is decided on
95% intervals; the secondary reading on 90% intervals; L and U are interval
ends from the randomized-complete-block analysis (cells x seed blocks).

| # | Prediction | Statistic | Falsifier (reject if) | Owner's prior |
|---|---|---|---|---|
| P0 | The emulator is exact and conformant | PG1 to PG7 | any mismatch against both references, a non-representable decoded operand, a GEMM bound violation or a NaN on zero blocks, SR bias above 1e-3 ulp, a non-identical resume, or a failed dtype assertion → INSTRUMENT_FAIL; no J4, no Phase 1 | likely pass after fixes |
| P1 | 35M on 0.6B tokens resolves the MX-like versus NV-like gap | C0 on J4 (probe seeds, fixed LR) | L90(C0) ≤ 0 (df 2) → STOP_UNRESOLVED_AT_35M; Phase 1 is not requested | about 0.55 |
| P2 | Theorem 1 reaches training loss: power-of-two block scales penalise INT4 more than E2M1 at fixed block size and range | I_prec32 = (INT4: S1 − S5) − (E2M1: S1 − S5) | REFUTED if U95 is below 0; ABSENT (the effect is smaller than the anchor gap in both directions) if the 95% interval lies inside (−C0, C0); CONFIRMED needs L95 above 0 | CONFIRMED about 0.4, ABSENT 0.25, REFUTED 0.05 |
| P3 | H_sep, the design prior's ranking generalised to both grids | D1 = C_fmt_bar − 2 Delta_G, interactions | PRIOR_SURVIVES needs L90(D1) above 0, every registered |I| + t SE below C_fmt_bar, no interaction verdict; GRID_OR_INTERACTION fires if U90(D1) is below 0 or the 4-df interaction F has p below 0.05 with max |I| ≥ 0.5 |C_fmt_bar| | GRID_OR_INTERACTION about 0.45 given GO |
| P4 | Some format factor moves loss at 35M | omnibus F over the 10 FP4 cells | p above 0.10 → WITHIN_NOISE | unlikely given GO |
| P5 | The emulator does not drive the factor ranking on the cell where the common path is most inexact | C_emu = L(INT4/S5 on the BF16 path) − L(INT4/S5) | EMULATION_SENSITIVE if the 95% interval excludes 0 and |C_emu| ≥ 0.5 max(|Delta_G|, |C_fmt_bar|, |C_prec32|); every smaller contrast is then emulator-conditional | not sensitive, about 0.9 |
| P6 | Operand QSNR predicts the cell ranking | Spearman rho between the frozen ranking and observed means over 10 cells | rho below 0.564 (the exact one-sided 5% critical value for 10 cells, p 0.048; S1v2) → NOT_PREDICTIVE | uncertain |
| P7 | Divergence and spikes are rare at the tuned LR | divergence counts; spike score | none (descriptive); NOT_ESTIMABLE below 10 spikes | likely NOT_ESTIMABLE |
| P8 | The matched-storage crossing is a scale-precision effect | the range rule | RANGE_EXPOSED if any role's UE4M3 subnormal-or-clamped share exceeds 1% or the 95% interval of I_range32 excludes 0 | exposed about 0.3 |

Precedence for the secondary verdict: WITHIN_NOISE, then GRID_OR_INTERACTION,
then PRIOR_SURVIVES, then SCALE_DOMINATES_INTERACTION_UNRESOLVED, then
INDETERMINATE. P2, P5, P6, P7 and P8 are reported beside it, with every
contrast's observed size against its calibrated prediction (kappa from J4)
and the anchor's split into a scale step and a block step in both orders.

**What the design cannot show.** Anything about rounding modes, RHT, UE5M3,
scales above 35M and 0.6B tokens, native kernels or energy. Whether the
mechanism, if confirmed, is the only one acting (P2 identifies a
scale-precision effect, not its theoretical form). At n = 3 seeds it cannot
detect an interaction below about 3.4 sigma with 80% power (2.3 sigma at
n = 6; D1v2).

## Cheapest Decisive Pilot

The cheapest decisive step is Phase 0, now decision-bearing and at most 8.0
GPU-h by construction: fixed caps of 2.80 GPU-h (J0 to J3) and the probe J4
(central-case cap 4.82 GPU-h; Phase 0 total 7.62). It decides whether a valid
instrument exists (PG1 to PG7), measures throughput and the quantization
overhead that set Phase 1's cost, freezes the tensor-level prediction, and
then decides the science question that gates Phase 1: whether 35M on 0.6B
tokens resolves the MX-like versus NV-like gap at all (G1), and if so how many
seeds Phase 1 needs. If the probe's formula cap would push Phase 0 over 8.0
GPU-h (the high cost case, emulated throughput below about 277,000 tok/s per
process), J4 is not run and goes to Kevin as Phase 1's first step
(PROBE_OVER_LINE).

The decisiveness table in "Changes after wave 1" gives the gate's and P2's
operating characteristics. At sigma 0.004 with the credited mechanism at the
registered effect size, Phase 0 says GO in about three quarters of
replicates, and given GO P2 is CONFIRMED in about 0.93; under crest-only and
range-only truths (the alternatives wave 1's design could not exclude), P2 is
falsely CONFIRMED in at most 0.05 of GO replicates and reads ABSENT in
most of them.

No executable pilot exists today. The first would be a `kind: cpu-doctor` orx
node running a registered `scripts/run_fp4_quantizer_doctor.py`: the
reference quantizer's conformance against gfloat and ml_dtypes, the
metamorphic and containment tests, N2v2 and N3 recomputed, and the analysis
script reproducing S1v2's decisions on synthetic replicates. The second would
be the J0 GPU-conformance manifest through the Docker submitter.

## Controls, Baselines, and Ablations

- **BF16 reference** at its own tuned LR (5-point sweep plus n fresh seeds);
  every loss gap is reported against it, paired by seed.
- **Positive control and gate** (J4, Phase 0): the MX-like (E2M1/E8M0/B32)
  and NV-like (E2M1/UE4M3+FP32/B16) configurations, whose ordering is
  documented at 1B to 12B (C07, C08, C12), on probe seeds never used in
  Phase 1.
- **Identification controls for P2**: S5 (BF16 scale) shares S1's block size
  and exponent range, so I_prec32 excludes crest-factor and range effects by
  construction (N3); S4 separates UE4M3's range from its precision (S4 against
  S5, I_range32), and the range rule labels the matched-storage readings.
- **Emulation-path control**: INT4/S5 rerun with decoded operands cast to
  BF16 and a BF16 GEMM with PyTorch's default reduced-precision reduction (n
  fresh seeds at INT4/S5's tuned LR); 42.6% of its decoded products are
  inexact in BF16 (N1), so it bounds what the common emulation path would have
  done to the cells P2 reads.
- **Attribution endpoint**: the BF16-forward loss of the same weights.
- **Held fixed (declared confounds):** no RHT; a per-tensor scale only in S3
  and S4; round-up absmax scale selection for every format; correctly rounded
  division; ties to even; RTN for weights and activations; SR (24 random bits)
  for output gradients in the Dgrad and Wgrad GEMMs; all three GEMMs of every
  linear layer in blocks 1 to 5 quantized; block 6, embeddings, head,
  attention BMMs, softmax and norms in BF16 or FP32, norm affine weights in
  FP32; 1D blocks along each GEMM's reduction axis; FP32 master weights and
  AdamW states; one data order per seed; one schedule; no qk-norm and no
  z-loss.
- **Tuning:** five-point BF16 sweep {1e-3, 2e-3, 4e-3, 8e-3, 1.6e-2} plus one
  extension; every FP4 cell a 3-point sweep centred on the BF16 tuned LR plus
  up to two extensions (one protocol for both grids); quadratic refinement in
  log2 LR, clamped to half a grid step; n fresh seeds at the tuned LR.
- **Deferred factors (not ablated here):** rounding mode, RHT, UE5M3, the
  scale-selection rule (four-over-six, Half-S), 2D blocks, BF16 final layers,
  a larger model. N2v2 reports RHT dependence at tensor level only.

## Evaluation, Statistics, and Leakage Checks

**Primary endpoint.** Final validation loss (mean next-token NLL in nats) at
step 9,155 on a 15M-token held-out set, with the run's own forward numerics.
**Attribution endpoint:** the BF16-forward loss of the same weights.

**Analysis.** A randomized complete block design: the 10 FP4 cells x n seeds,
seed as the block (fixed in advance), residual df 9(n − 1). Standard errors in
units of the per-run residual SD sigma at n seeds (D1v2): every interaction
2/sqrt(n) (1.155 at n = 3), I_fmt_bar and C_anchor 0.82, D1 0.84, Delta_G 0.37
at n = 3. P2 on the 95% interval of I_prec32; secondary verdicts as
registered; omega-squared variance fractions with parametric-bootstrap
intervals; Shapiro-Wilk and Levene checks; within-block permutation versions
of the omnibus and interaction F-tests as a sensitivity.

**Operating characteristics (S1v2).** S1v2 simulates exactly the registered v2
rules, including the probe's LR offsets at a common LR, the BF16 and FP4
sweeps with LR-dependent loss, the seed-count rule, the RCBD and every
verdict. Selected rows, given GO (sigma 0.004, seed correlation 0.5; cells
"LR curvature a = 0.005 / a = 0.02"; the full grid is in `power-sim-v2.json`):

| Truth (m = 1) | P2 CONFIRMED at 90% (reported) | RANGE flag | WITHIN_NOISE | GRID_OR_INTERACTION | PRIOR_SURVIVES | SDIU | INDETERMINATE | cover95 I_prec32 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| null (LR spread 0.25) | 0.09 / 0.06 | 0.10 / 0.05 | 0.75 / 0.88 | 0.17 / 0.05 | 0.00 / 0.00 | 0.01 / 0.02 | 0.07 / 0.05 | 0.92 / 0.93 |
| prior additive | 0.07 / 0.05 | 0.09 / 0.06 | 0.00 / 0.00 | 0.10 / 0.05 | 0.52 / 0.61 | 0.16 / 0.14 | 0.22 / 0.20 | 0.92 / 0.95 |
| credited mechanism (pow2) | 0.96 / 0.97 | 0.13 / 0.10 | 0.00 / 0.00 | 0.96 / 0.97 | 0.00 / 0.00 | 0.00 / 0.00 | 0.03 / 0.03 | 0.91 / 0.94 |
| crest-factor only | 0.08 / 0.06 | 0.09 / 0.06 | 0.00 / 0.00 | 0.97 / 0.97 | 0.00 / 0.00 | 0.00 / 0.00 | 0.03 / 0.03 | 0.91 / 0.95 |
| UE4M3 range only | 0.07 / 0.05 | 0.84 / 0.82 | 0.00 / 0.00 | 0.98 / 0.98 | 0.00 / 0.00 | 0.00 / 0.00 | 0.02 / 0.02 | 0.91 / 0.94 |
| pow2 + range | 0.96 / 0.98 | 0.82 / 0.84 | 0.00 / 0.00 | 0.99 / 0.99 | 0.00 / 0.00 | 0.00 / 0.00 | 0.01 / 0.01 | 0.91 / 0.94 |
| grid additive | 0.08 / 0.05 | 0.09 / 0.05 | 0.00 / 0.00 | 1.00 / 1.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.91 / 0.94 |
| reversed | 0.00 / 0.00 | 0.09 / 0.05 | 0.01 / 0.01 | 0.81 / 0.80 | 0.00 / 0.00 | 0.18 / 0.19 | 0.01 / 0.00 | 0.91 / 0.95 |

Effect size and sigma (P2 given GO; cells "a = 0.005 / a = 0.02"):

| Truth | m | sigma | P(GO) | P2 CONFIRMED given GO | P2 REFUTED given GO | P2 ABSENT given GO | cover95 I_prec32 given GO |
|---|---:|---:|---:|---:|---:|---:|---:|
| credited mechanism (pow2) | 0.5 | 0.004 | 0.48 / 0.51 | 0.47 / 0.48 | 0.00 / 0.00 | 0.11 / 0.26 | 0.91 / 0.94 |
| credited mechanism (pow2) | 1.0 | 0.002 | 0.99 / 0.86 | 1.00 / 1.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.95 / 0.94 |
| credited mechanism (pow2) | 1.0 | 0.004 | 0.88 / 0.73 | 0.93 / 0.94 | 0.00 / 0.00 | 0.03 / 0.03 | 0.91 / 0.94 |
| credited mechanism (pow2) | 1.0 | 0.008 | 0.47 / 0.49 | 0.48 / 0.47 | 0.00 / 0.00 | 0.09 / 0.16 | 0.89 / 0.93 |
| credited mechanism (pow2) | 2.0 | 0.004 | 1.00 / 0.94 | 1.00 / 1.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.92 / 0.94 |
| crest-factor only | 0.5 | 0.004 | 0.48 / 0.49 | 0.05 / 0.03 | 0.04 / 0.03 | 0.33 / 0.58 | 0.91 / 0.94 |
| crest-factor only | 1.0 | 0.002 | 0.99 / 0.86 | 0.03 / 0.02 | 0.03 / 0.03 | 0.93 / 0.91 | 0.94 / 0.95 |
| crest-factor only | 1.0 | 0.004 | 0.86 / 0.74 | 0.05 / 0.03 | 0.04 / 0.03 | 0.72 / 0.77 | 0.91 / 0.95 |
| crest-factor only | 1.0 | 0.008 | 0.47 / 0.48 | 0.05 / 0.04 | 0.06 / 0.04 | 0.25 / 0.46 | 0.89 / 0.93 |
| crest-factor only | 2.0 | 0.004 | 1.00 / 0.94 | 0.04 / 0.02 | 0.04 / 0.03 | 0.91 / 0.93 | 0.92 / 0.95 |
| null (LR spread 0.25) | 1.0 | 0.002 | 0.14 / 0.29 | 0.03 / 0.02 | 0.04 / 0.03 | 0.35 / 0.72 | 0.93 / 0.95 |
| null (LR spread 0.25) | 1.0 | 0.004 | 0.08 / 0.23 | 0.03 / 0.04 | 0.05 / 0.03 | 0.14 / 0.58 | 0.92 / 0.93 |
| null (LR spread 0.25) | 1.0 | 0.008 | 0.06 / 0.14 | 0.06 / 0.03 | 0.06 / 0.04 | 0.05 / 0.35 | 0.88 / 0.93 |

Two readings. First, the identification holds in training under the
registered estimator: with I_prec32 = 0 but a crest-factor or a UE4M3-range
interaction present, P2 is falsely CONFIRMED in 0.02 to 0.05 of GO
replicates, and the range flag fires in 0.82 to 0.84 of them under the range
truths (0.05 to 0.13 otherwise). Second, the secondary verdict family does
not identify anything: GRID_OR_INTERACTION fires at 0.80 to 1.00 under every
interaction truth whatever its source, and at 0.05 to 0.17 under a null, so it
is reported, not interpreted causally. 90% intervals of I_prec32 would give
false confirmation up to 0.09 (first column), which is why P2 uses 95%.

**Gate reuse removed (S1v2).** The same Phase 1 data read two ways: with v2's
independent probe as the gate, and with v1's gate computed on Phase 1's own
E2M1/S1, E2M1/S3 and BF16 fresh runs (wave 1's rule). Both read P2 on the
90% interval at n = 3, wave 1's rule, so they compare like with like.

| Truth | sigma | v2: P2 REFUTED given GO | v2: anchor 90% coverage given GO | v1 reuse: P(gate) | v1: P2 REFUTED given gate | v1: anchor 90% coverage given gate | v1: anchor bias given gate (nats) |
|---|---:|---:|---:|---:|---:|---:|---:|
| null, no LR spread | 0.004 | 0.08 / 0.08 | 0.87 / 0.88 | 0.03 / 0.02 | 0.28 / 0.28 | 0.21 / 0.26 | 0.0051 / 0.0048 |
| null, no LR spread | 0.008 | 0.06 / 0.05 | 0.85 / 0.90 | 0.04 / 0.02 | 0.34 / 0.19 | 0.20 / 0.28 | 0.0104 / 0.0097 |
| grid additive, half size | 0.004 | 0.07 / 0.05 | 0.86 / 0.89 | 0.37 / 0.38 | 0.12 / 0.09 | 0.82 / 0.88 | 0.0019 / 0.0017 |
| grid additive, half size | 0.008 | 0.09 / 0.07 | 0.85 / 0.88 | 0.15 / 0.13 | 0.22 / 0.15 | 0.55 / 0.68 | 0.0073 / 0.0061 |
| crest-factor only, half size | 0.004 | 0.08 / 0.06 | 0.85 / 0.90 | 0.39 / 0.36 | 0.12 / 0.11 | 0.80 / 0.87 | 0.0021 / 0.0016 |
| crest-factor only, half size | 0.008 | 0.09 / 0.06 | 0.85 / 0.88 | 0.15 / 0.13 | 0.19 / 0.16 | 0.58 / 0.63 | 0.0069 / 0.0064 |
| prior additive, half size | 0.004 | 0.08 / 0.06 | 0.85 / 0.90 | 0.82 / 0.84 | 0.09 / 0.07 | 0.88 / 0.91 | 0.0006 / 0.0004 |
| prior additive, half size | 0.008 | 0.08 / 0.06 | 0.84 / 0.89 | 0.32 / 0.32 | 0.13 / 0.10 | 0.79 / 0.82 | 0.0045 / 0.0040 |

Cells "a = 0.005 / a = 0.02", sigma as listed, seed correlation 0.5. With
v1's reuse the gate selects Phase 1 noise, so the anchor estimate is biased
upward by up to 0.010 nats, its 90% interval covers 0.20 to 0.28 of the time
under a null, and P2 is falsely REFUTED in 0.07 to 0.34 of gated replicates;
with v2's independent probe the anchor's coverage is 0.84 to 0.90 and false
REFUTED 0.05 to 0.09 at the 90% reading (0.02 to 0.05 at the registered 95%
reading), the residual excess being LR tuning error, not selection.

**Missing data and divergence.** A fresh-seed run that diverges (NaN, Inf, or
validation loss above 10 at any evaluation) is divergent. A cell with a
divergent fresh seed is UNSTABLE_AT_TUNED_LR; the factorial is analysed by
OLS on the unbalanced design only if every cell keeps at least 2 finite seeds,
otherwise INCONCLUSIVE_UNSTABLE. Sweep divergences count as infinite loss for
tuning. A divergent probe run gives PROBE_UNSTABLE.

**Leakage checks.** Validation documents are those with int(SHA-256(document
id)[:8], 16) mod 100 = 0, removed from the training stream before shuffling;
each run reads a single pass with no document repeated. Near-duplicates across
crawl dumps can still sit on both sides of the split (reviewer 1); this
affects every cell identically and so cannot bias a between-cell contrast, and
it is reported, not repaired. Validation is used for tuning only through the
sweep's final loss, which is then re-measured on fresh seeds; probe runs and
sweep runs never enter the factorial's estimates. The numerics prediction is
frozen (hash recorded) before J4. The analysis code is frozen with the
registration and runs on hashed cell ids until the verdict table is written.

## Compute and Reproducibility

Image: the architecture image
`127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(torch 2.11.0+cu128, Triton 3.6.0, Python 3.12.3, ml_dtypes present). It holds
no C5 code; the Dockerfile copies the source tree, so a rebuild at the freeze
commit (`sbatch infra/slurm/host-single-node/build-architecture-image.sbatch`,
CPU only) gives the registered digest. gfloat 0.5.2 (MIT, numpy-only) is the
second CPU reference, installed and pinned for the CPU conformance suite on
the development Mac.

Launch path (dry run, test-only, submit; one GPU per job; none of these
manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v2/j1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v2/j1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v2/j1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the same three steps apply to J0, J2, J3, J4 and every Phase 1 job. The data
fetch (FineWeb-Edu files 000 and 001 at revision 87f09149, 4.31 GB, and the
tokenizer at revision 27d67f1b) and tokenization are CPU Slurm jobs, public
research downloads under D1, and obey the host rule.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 8 (Phase 0's ceiling: fixed
caps J0 0.25, J1 1.85, J2 0.40 and J3 0.30 = 2.80 GPU-h, plus J4 by formula
only if the sum stays at or below 8.0; Phase 1's caps are set later by the
formula below and are not part of this ceiling; the gauntlet's 0.3 GPU-h is
reviewer inference only). Phase 1 adds seeds 45 to 47 when J4 sets n above 3;
probe seeds 2001 to 2003 and sweep seed 1000 are used nowhere in the
factorial.

Phase 0 arithmetic (S2v2, each cap 1.2 times the high case: BF16 400,000
tok/s per process, F_total 4.0, F_quant 2.0, model compile 300 s, quantizer
compile 60 s, no packing gain; rounded up to 0.05 GPU-h):

| Job | High-case workload | High case (s) | Cap (GPU-h) | Central (s) |
|---|---|---:|---:|---:|
| J0 | start-up 10 s; ten quantizer compiles of 60 s; conformance vectors 60 s; FP64 GEMM check 12.5 s (50 GEMMs x 9 distinct shapes x 10 cells, 418.8 GFLOP per shape set, value and abs-product bound, 50% of the 67 TFLOPS FP64 peak); copies 30 s | 712 | 0.25 | 383 |
| J1 | 13 compiled configurations x (10 + 300 + 120 steps); eager BF16 and NV-like, 60 steps; NV-like packed 2 per GPU, 120 steps | 5,481 | 1.85 | 2,216 |
| J2 | 3 processes x (10 + 300); 400 NV-like steps | 1,192 | 0.40 | 477 |
| J3 | 10 + 300 + 3,000 BF16 steps + 60 s capture | 862 | 0.30 | 518 |
| J4 | formula: 1.2 x 6 x [599,982,080 / (0.9 r) + 48,000,000 / (3 x 0.9 r) + o] / k | 14.31 GPU-h at the high case (does not fit) | at most 5.20 | 4.82 GPU-h (Phase 0 total 7.62); low 2.07 |

Phase 1 cap formula, fixed here before Phase 0 (D22): for each run type,
GPU-seconds = [599,982,080 / (0.9 r) + 48,000,000 / (3 x 0.9 r) + o] / k, with
r the J1 median per-process tok/s of that run type at the adopted packing k (k
= 2 only if J1 measures an aggregate gain of at least 1.2), E = 48M
evaluation tokens (nine periodic 2M-token evaluations, the final 15M on the
run's own forward and 15M on the BF16 forward, at three times training
throughput) and o the J1 startup plus compile time. The cap is 1.2 x the sum
over the maximum run counts at the probe's seed count n: BF16 6 + n, FP4
10 x 5 + 10 n, control n. Worked example (central, k = 1): an FP4 run is
599,982,080 / (0.9 x 300,000) + 48,000,000 / (3 x 0.9 x 300,000) + 130 =
2,222 + 59 + 130 = 2,411 s = 0.670 GPU-h; a BF16 run 0.353 GPU-h; a control
run 0.543 GPU-h; at n = 3 the maximum is 9 x 0.353 + 80 x 0.670 + 3 x 0.543 =
58.4 GPU-h and the cap 1.2 x 58.4 = 70.1 GPU-h. S2v2:

| Case (k = 1 unless stated) | n = 3 | n = 4 | n = 5 | n = 6 | Expected at n = 3 (no extensions) |
|---|---:|---:|---:|---:|---:|
| low (BF16 850k tok/s, F 1.2) | 31.2 | 35.3 | 39.3 | 43.4 | 20.0 |
| central (600k, F 2.0) | 70.1 | 79.2 | 88.3 | 97.4 | 44.6 |
| central, k = 2 if measured (gain 1.5) | 46.1 | 52.0 | 58.0 | 64.0 | 29.3 |
| high (400k, F 4.0) | 201.4 | 227.5 | 253.5 | 279.6 | 127.6 |

For the record, wave 1's own formula with its 0.9 factor applied gives a
central single-process cap of 125.3 GPU-h (its table printed 113.2) and 82.9
with two processes (printed 74.8). If Kevin admits less than the formula's
value, the registered fallback drops the BF16 fresh seeds and the control
first, then the S2 pair (I_fmt16, I_blk_E8 and I3 lost; P2, I_fmt32, I_blk_UE
and I_range32 kept); otherwise Phase 1 waits.

Checkpoints and resume: every 1,000 steps and at the end, to
`~/cotcodec-runs/c5-fp4-instability-v2/` (one directory per run id), with
model, optimizer, data cursor, the three Philox generator states and the LR
schedule position; a fresh job resumes from the latest checkpoint. J2
requires bit-identical parameters and loss trajectories between an
uninterrupted run and a fresh-job resume under the deterministic mode every
Phase 1 run uses. Artifacts: per-run configs, loss and gradient-norm
trajectories, both final validation losses, sweep tables, the frozen numerics
prediction, J4's probe table, the verdict table, receipts with image digest,
flags, division setting and dtype assertions; checkpoints and captured
tensors (about 3 GB) stay on the host.

## Safety, Data Rights, and Monitorability

- **Data.** FineWeb-Edu (ODC-BY 1.0, ungated, revision 87f09149), derived from
  Common Crawl; attribution kept in every report; only file ids, revisions,
  hashes, token counts and metrics enter the public repository. The download
  (4.31 GB, two files) is a public licensed research download under D1,
  recorded with source, revision, size and SHA-256.
- **Tokenizer.** Mistral-7B-v0.1 tokenizer files only (Apache-2.0, ungated,
  revision 27d67f1b); no model weights are downloaded or released.
- **Models.** 35M-parameter models trained from scratch for numerics research;
  checkpoints stay on the host; no release is planned.
- **Untrusted code.** None executes. The quantizers, harness and any fused
  Triton kernel are reviewed project code under D7; third-party kernels are
  read as references only. torch.compile output is project code.
- **Host.** Run 2 made no host contact. Phase 0 GPU jobs wait for a freeze and
  obey the host rule; Phase 1 waits for Kevin's D24 ruling.
- **Sources.** The ARITH 2025 PDF and the paper texts read in run 2 stay in
  the session scratchpad; only hashes, locators and short paraphrases enter
  the repository.
- **Public repository.** No host addresses beyond the documented local registry
  name, no credentials, no data text.
- **Monitorability.** No policy is trained and nothing is deployed.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Verdict | What it says | What it closes |
|---|---|---|
| INSTRUMENT_FAIL (Phase 0) | The emulator could not be made exact or conformant under the pinned spec | Phase 1 until fixed; the interpretation gap is itself a reportable emulation finding |
| TRITON_GATE / TF32_PATH_COST | Quantization overhead, or the exact path itself, is too slow on this host | Phase 1 until a fused quantizer exists, or until Kevin accepts the formula's larger cap |
| PROBE_OVER_LINE | Measuring sigma and the anchor at Phase 1's budget costs more than Phase 0's 8 GPU-h | Moves the probe into Kevin's Phase 1 ruling with its measured cost |
| STOP_UNRESOLVED_AT_35M | 35M on 0.6B tokens cannot resolve even the MX-like versus NV-like gap, with sigma measured | Every format question at this scale; a quantitative reason a larger step needs its own admission |
| P2 ABSENT | The power-of-two penalty on INT4, if present in training at 35M, is smaller than the MX-like versus NV-like gap in both directions | The claim that the tensor-level penalty is a first-order training effect at this scale |
| P2 REFUTED | Power-of-two scales penalised E2M1 more than INT4 in training | Theorem 1's ranking as the dominant training-time effect here |
| P2 CONFIRMED, FORWARD_SHARE_NOT_EXCLUDED | The penalty appears in own-forward loss but not shown in the weights | Separates a deployment effect from a training effect |
| RANGE_EXPOSED | The matched-storage crossing includes UE4M3 range effects | Attributing the commercial-format crossing to scale precision |
| WITHIN_NOISE / PRIOR_SURVIVES / GRID_OR_INTERACTION | The design prior's ranking with the grid varied | The prior's generality at 35M |
| EMULATION_SENSITIVE | The common BF16 emulation path alone moves loss comparably to the factors | Factor claims below twice the emulation effect, for this and every BF16-decode emulation study |
| INDETERMINATE / UNRESOLVED | Intervals too wide | Nothing; the measured sigma sizes a successor |

Every Phase 1 outcome also yields the MXFP4-to-NVFP4 analogue gap split into
a scale step and a block step in both orders, with intervals; 2505.19115
Fig. 2 trains the E2M1 cells of one order as single runs, so only the
intervals, the second order and the INT4 column are new.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv reachable; OpenAlex rate-limited (2 of 2 run-2 calls rejected, logged and counted); OpenReview search reachable; 16 run-2 queries and 3 full reads logged with hashes; the ARITH 2025 open copy found and read; cutoff 2026-10-10; degraded coverage recorded (`doctors/source.json`) | Retry OpenAlex expansion of 2510.25602; search patents and Chinese-language venues |
| Citation | PASS | Claim registry C01 to C44; C05 and C34 rewritten after full reads, C42 to C44 added; wave 1's closed-access label for C34 and its "no prior reports" sentence corrected; OpenReview items labelled abstract-only (`doctors/citation.json`) | Read C32, C33, C43 and C44 in full when accessible |
| Novelty | FAIL | NARROWED, no direct prior under the recorded coverage; the mechanism credited; but the blind critic has not been rerun against the mechanism prior and run 2's novelty refuter has not run (`doctors/novelty.json`) | Run the blind critic on `blind/paragraph-65332d00.txt` against `paragraph-ad76d839.txt` (and `paragraph-201f330b.txt`); run the refuter |
| Design | PASS | Identified P2 (N3), rank 10 of 10 (D1v2), no gate reuse, J4 measuring sigma and the anchor with a power rule, 95% decision intervals justified by S1v2, range rule, attribution endpoint, equal LR protocol, S1v2 over nine truths; residual risks listed (`doctors/design.json`) | Build the analysis script and reproduce S1v2's decisions as a cpu-doctor node |
| Compute | FAIL | No real model loop, quantizer kernels, data on the host, manifest, container smoke or Slurm dry run (`doctors/compute.json`, `compute/attestations-not-run.md`) | Write the harness and quantizers; fetch the data under D1; rebuild the image; dry run and test-only |
| Safety | PASS | ODC-BY data and an Apache-2.0 tokenizer under D1, data text off the public repository, no untrusted code, no host contact in run 2 (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol; Design, the
vendored K-Dense `experimental-design` and `statistical-power` skills (design
before data, DOE estimability, decision rules with operating characteristics
by simulation of the registered estimator); Evaluation, K-Dense
`statistical-analysis`; Novelty, K-Dense `literature-review` (PRISMA counts).
The integrity gate (seven failure modes) is answered in registration v2.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviewer 1, claude-opus-5-5, scored 54 and is recorded in the gauntlet file)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job is the only host job this run may submit; wave 1's reviewer 2, qwen3.6-35b-a3b, Slurm 1083, scored 65)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

This run's reviewers have not scored. Wave 1's scores (reviewer 1 / reviewer
2) are in the gauntlet record and in the iteration log below; they scored the
wave-1 package, not this one.

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (wave 1: 5 / 8); reframed as a training-time measurement of published theory |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1: 6 / 8); registry C01 to C44, ARITH 2025 read in full |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1: 3 / 5); mechanism credited, narrow residual |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1: 6 / 8); P2 identified (N3), P0 to P8 with falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1: 5 / 5); no gate reuse, S4 and S5 controls, attribution endpoint |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1: 6 / 8); S1v2 under the registered estimator, 95% decision intervals |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1: 3 / 5); J4 decision-bearing inside 8 GPU-h, caps recomputed |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1: 6 / 5); no harness, no manifest |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1: 9 / 8) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1: 5 / 5); no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | Factors confounded in prior work; matched storage needs iso-storage contours | Corrected question and kill lines written | Recorded in the dossier, section 8 |
| new gauntlet, synthesis (2026-10-10) | not scored | The dossier's cell set cannot separate block size from scale encoding (rank 8 of 10), its GEMM model is inexact for one cell, and three of four factors are already swept one at a time | Full-rank cell set; exact TF32 emulation path; positive-control gate; numerics-predicted interaction; per-arm sweeps; decision rules simulated and revised once | Went to wave 1 |
| 1 (2026-10-10) | 54 (54 / 65) | The central registered test (P2 through I_fmt and I_blk) is published theory (2510.25602 Theorems 1-2, ARITH 2025) and not identified (I_blk is crest factor, I_fmt mixes UE4M3 range); gate reuse biases the factorial; Phase 0 does not measure sigma or the anchor; caps miscomputed | No honest exit; triad 3 of 3 refuted; D68: one repair and a fresh run | Recorded, row hash `65266173...` |
| D68 repair (2026-10-10) | not scored | as wave 1 | Registration v2: mechanism credited and claim reframed; P2 on the identified I_prec32 (N3); S4 added (rank 10 of 10) with a range rule; J4 probe on its own seeds inside 8 GPU-h with G1 and a power rule for n; no reuse (S1v2 replay); 0.6B tokens; equal LR protocol; 95% decision intervals; control on INT4/S5; autocast, division, FTZ, determinism and SR pins; F_quant; attribution endpoint; caps derived and recomputed; novelty coverage (ARITH 2025, 2302.08007, OpenReview) | Awaiting this run's blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-c5-fp4-instability.md` (exit 1) on the committed
bundle, also stored as
`evidence/2026-10-10-c5-fp4-instability/doctors/research-direction-doctor-output.json`.
Three readings the doctor does not make for itself. "All declared budgets must
be positive" comes from parsing the declared `gpu_hours=0.3` as an integer;
the declared budget is honest and is not rounded up to pass. The doctor
applies no 79 cap here because its executable-pilot check is textual, while by
the gauntlet rule's cap table this proposal is capped at 79 (no executable
pilot) and 89 (no independent provider-distinct review), and cannot reach 100
without D24's trust store. The doctor also counts the eight OpenReview
snapshots as resolved because those pages return HTTP 200; their bodies are a
browser challenge.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "PASS",
    "Novelty": "FAIL",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "all declared budgets must be positive",
    "Novelty doctor lacks PASS plus concrete evidence",
    "Compute doctor lacks PASS plus concrete evidence",
    "Reviewer A lacks structured PASS attestation",
    "Reviewer B lacks structured PASS attestation",
    "evidence bundle requires exactly two review artifacts",
    "protected external trust store is not configured; set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI",
    "reviewers must use different providers; degraded review cannot score 100",
    "reviewers must have distinct nonempty run IDs",
    "two distinct trusted reviewer signatures are required for 100",
    "compute attestation says the real model loop is not executable",
    "compute attestation lacks a non-stub benchmark adapter",
    "compute benchmark_adapter path does not exist",
    "repository real model loop is still a stub",
    "compute lacks a hashed Slurm manifest",
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-c5/program/proposals/2026-10-10-c5-fp4-instability.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 52,
    "recognizedPrimaryUrls": 49
  },
  "status": "FAIL"
}
```
