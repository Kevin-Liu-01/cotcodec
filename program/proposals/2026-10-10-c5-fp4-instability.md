# Research Direction: C5 Phase 0 and Phase 1 design, what drives emulated FP4 training loss: the element grid crossed with block-scale configurations that separate block size from scale encoding at equal storage (backfill C5)

**Status:** draft for gauntlet wave 1 (program decision D67); synthesis by the single owner on 2026-10-10 from four independent discovery cells (frontier, kill-shot, cross-domain, asset and cost) of gauntlet wave 1; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/c5-fp4-instability-v1.md` is a DRAFT, not frozen or admitted, with no ledger row; no executable pilot exists; a score of 100 cannot be certified in this repository (D24); Phase 1 is above 8 GPU-h, so its admission is Kevin's ruling under D24 whatever this gauntlet scores
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design, CPU computations and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-10
**Coverage limits:** orx 0.2.2 only for literature search (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18; OpenAlex returned HTTP 429 or 400 on 10 of 114 calls, which are logged and not treated as coverage); the OpenReview api2 search (10 searches by the frontier cell; full texts and per-note pages are behind a browser challenge, so every OpenReview item is abstract-only, UNVERIFIABLE_ACCESS for full text); the arXiv API and Semantic Scholar through the read-only host relay (arXiv version records by the frontier cell; Semantic Scholar paper record and forward citations of seven priors by synthesis); arXiv abstract pages; the ACL Anthology only for one PDF (Half-S), not searched; the Hugging Face model and dataset APIs; Zenodo; the PyTorch 2.14 documentation; repository evidence. 114 counted orx discover invocations (frontier 38, kill-shot 26, cross-domain 35, asset 8, synthesis 7; 11 rejected by the backend; 568 unique ids returned), 58 full-text reads by the cells (plus 1 report and 3 metadata records) and 16 synthesis re-reads of cell-fetched texts. Not searched: patents, X, Reddit, Hacker News, Chinese-language venues (Zhihu, CNKI), vendor blogs, GitHub issue trackers. Not readable: the ARITH 2025 microscaling study (IEEE, closed access), the MXFP4-MARS and Agrusa et al. OpenReview PDFs (HTTP 403 challenge), and the full text of Wannamaker et al. 2000 (paywalled); full texts were read by targeted section, not end to end
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-c5-fp4-instability/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED, more severely than the dossier stated (frontier, kill-shot
and cross-domain cells agree; none returned OCCUPIED). Scale format at matched
storage, block size and per-operand rounding were already swept one factor at
a time in training with the grid fixed at E2M1 (2505.19115). The grid was
already varied in training at one scale setting (2603.28765, 2606.20381). One
closed-access study (ARITH 2025) lists the same factor families for MX formats
and could not be read. The residual this proposal claims is narrow: a
seed-replicated crossing of the grid with block-scale configurations chosen so
that block size and scale encoding are separately estimable, under one exact
emulation path, with a tensor-level prediction of the interaction frozen before
the runs.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. Phase 0's
own compute (registered caps 3.05 GPU-h, central about 1.0) is separate and runs
only after a freeze. Phase 1's caps are set by a registered formula from Phase
0's measurement (central projection 45 GPU-h with two runs per GPU, 68 without;
range 18 to 272) and need Kevin's admission under D24. No host job was run for
this proposal; the host was read once (`squeue` empty, all eight GPUs at 0 MiB,
2026-10-10T21:21:22Z).

## Scope and what changed from the dossier

This proposal covers the first step only: Phase 0 (bit-exact tests of the
fake-quant kernels against independent reference quantizers, the GEMM model,
throughput and packing, resume equivalence, and a short BF16 capture run whose
tensors fix a numerics prediction) and the design of Phase 1 (the emulated
grid by scale-configuration factorial). The rounding factor, RHT, UE5M3 and the
125M replication are later steps with their own registration.

The four cells were merged by mechanism, not by wording. Fifteen mechanisms
change C5 as the dossier wrote it
(`program/evidence/2026-10-06/question-dossier.md`, section 8). Each was
re-checked by synthesis against a primary source, by an exact computation (N1,
`compute/numerics.py`), by a tensor-level computation (N2,
`compute/crest_prediction.py`), by the design-matrix check (D1, `compute/doe.py`),
by simulation (S1, `compute/power_sim.py`), by the cost model (S2,
`compute/cost_model.py`), or by more than one.

| # | Mechanism (cells that found it) | What it does to the dossier's design | Where handled |
|---:|---|---|---|
| M1 | **Matched storage makes block size and scale width collinear** (kill-shot, cross-domain). Bits per element = 4 + scale bits / B, so at 4.5 b, B16 pairs only with 8-bit scales and B32 only with 16-bit scales. On the dossier's four scale/block levels the model grid + block + scale type + their grid interactions has rank 8 of 10 (D1); the block step and the E8M0-to-UE4M3 step are aliased | Registered cell set {E8M0/B32 4.25 b, E8M0/B16 4.5 b, UE4M3+FP32/B16 4.5 b, BF16/B32 4.5 b} x {E2M1, INT4}: full rank, every main effect and grid interaction estimable (D1). The MXFP4-to-NVFP4 gap splits into a block step (E8M0 B32 to B16) and a scale step (E8M0 to UE4M3+FP32 at B16); BF16/B32 against UE4M3/B16 is the equal-storage trade. UE5M3/B16 is deferred (adding it gives 10 cells, also full rank). Rounding is not varied in this step | Controls; registration "Cells" |
| M2 | **The residual is narrower than the dossier said** (frontier, kill-shot). 2505.19115 swept seven 8-bit scale encodings at B16 (all 4.5 b), block sizes 8 to 128 under E8M0 and E4M3, and SR per operand, all in training at 350M with E2M1 fixed; 2603.28765 compared NVFP4 with NVINT4 at E4M3/B16 in 340M pretraining; 2606.20381 crossed grid with RHT at an FP32 single-level scale | The claim is restricted to the grid x scale-configuration crossing, seed-replicated, at equal storage where separable, under one exact emulator; "does scale dominate block size" is not claimed as new | Closest Prior Work; Novelty Ledger |
| M3 | **Crest-factor theory predicts a grid x scale interaction** (frontier: INT4 should do relatively better at B16 and after transforms; kill-shot read 2510.25602 as predicting FP4 at least as good as INT4 in both columns; synthesis re-read Table 2: at B16 the median block crest factor 2.16 is below the NV crossover 2.39, NVINT4 wins 64.3% of blocks while the mean QSNR is tied, 20.55 against 20.60) | N2 computes, with the registered quantizer on five synthetic distributions: under power-of-two scales E2M1 beats INT4 by 1.2 to 2.8 dB QSNR in every distribution without RHT (0.4 to 1.8 dB with RHT), while under UE4M3+FP32 or BF16 scales the two grids are within about 0.7 dB for light tails and E2M1 leads by 0.9 to 3.5 dB for heavy tails or outlier channels. Registered predictions P_int_fmt and P_int_blk (INT4's penalty is larger under E8M0), recomputed on captured tensors and frozen before Phase 1 | Mechanism; registration "Numerics prediction" |
| M4 | **The declared GEMM model is not uniform across cells** (cross-domain, asset, kill-shot). N1 (exact): with a BF16 block scale, 28.5% (E2M1) and 42.6% (INT4) of decoded products are not representable in BF16, all are in TF32 within range; with E8M0, UE4M3 and UE5M3 scales every in-range product fits BF16. Folding an FP32 per-tensor scale into the operand is inexact in FP32 for 79.3% of sampled triples. (The asset cell's 37.6% for INT4 counted magnitude 8, a power of two) | One exact path for every cell: decoded operands q x s_block materialised in FP32 and multiplied with TF32 tensor-core GEMMs (exact inputs), FP32 tensor scales applied in the epilogue. A containment unit test asserts exactness per cell. The emulation-path control reruns the NV-like cell on the common BF16 path | Compute; registration "Quantization and GEMM" |
| M5 | **"FP32 accumulate" is not IEEE FP32, and BF16 reduced-precision reduction is on by default** (cross-domain: 2512.07004, the PyTorch 2.14 notes, 2609.11356) | Bit-exact claims are scoped to quantize and dequantize; the GEMM is tested against a deterministic error bound; the reduced-precision flag is set False and TF32 enabled identically in every cell, both asserted and recorded; shapes, library versions and kernels pinned | Evaluation; registration "Phase 0" |
| M6 | **"Bit-exact against a reference" is ill-defined until interpretation choices are pinned** (cross-domain, asset). UE5M3 has two published codebooks (max 61,440 or 114,688, N1); E8M0 scale rounding (floor clips, ceiling does not); true division against multiply-by-reciprocal disagrees on 0.029% of in-domain pairs, all exact ties (N1); overflow and NaN policy; symmetric or two's-complement INT4; SR bit count | Spec pinned: round-up scale rule for every format, true division, ties to even, saturation (never triggered under round-up), symmetric INT4 (15 codes, equal to E2M1's 15), 24 random bits for SR; two independent references per cell where they exist; metamorphic test E1M2 = INT4 / 4 | Registration "Phase 0" |
| M7 | **Confounds outside the four factors move rankings** (frontier, kill-shot): RHT flips the grid ranking (2606.20381, 2603.28765); NVFP4 does not converge without per-tensor scaling (2604.08826); the scale-selection rule changes the scale effect (2605.08565, Half-S); quantizing Wgrad dominates degradation (2605.09825); LayerNorm affine quantization (2506.20752); BF16 final blocks (2509.25149); execution path (2610.00053) | All held fixed and declared: no RHT, per-tensor scale only where the format needs it (S3), round-up absmax, all three GEMMs quantized in blocks 1 to 5, norms and their affine weights in FP32, last block, embeddings and head in BF16, 1D blocks per GEMM's reduction axis, decoded-operand TF32 path. RHT dependence is computed at tensor level (N2, Phase 0), not trained | Controls |
| M8 | **The study may be too small to see anything** (kill-shot, frontier, asset). FP4 effects visible at 12B were not measurable at 1.2B on 1T tokens (2509.25149); Phase 1 has about 29,000 times less compute than those ablations (6ND with 35M parameters; the kill-shot cell's 33,000 assumed 30M); the only published FP4 seed anchor, 2505.19115 Table 4, states SD 0.001 but its printed losses give 0.00195 (N1) | Stage 1a runs only BF16 and the two commercial-format analogues and continues only if the documented MXFP4-vs-NVFP4 gap is resolved (gate G1). S1: false continuation 0.01 to 0.03 under the null; continuation 0.83 to 1.00 when that gap is 2.5 times sigma or more | Cheapest Decisive Pilot; S1 |
| M9 | **Undertuned baselines and the winner's curse** (kill-shot: small models need far more than a 3-point grid, 2608.11859; cross-domain: optimizer's curse) | Five-point LR sweep per Stage-1a configuration, three points plus up to two extensions in Stage 1b, quadratic refinement; fresh seeds never reuse a sweep run. S1: residual tuning bias averages 0.0001 to 0.0008 nats | Controls; S1 |
| M10 | **Instability at the tuned LR is likely rare at 35M** (cross-domain: 2309.14322, 2501.00656) | Loss gap is primary; divergence counts, the LR profile and the OLMo 2 spike score are secondary, spikes analysed as counts with a NOT_ESTIMABLE rule | Evaluation |
| M11 | **Seed structure** (cross-domain: 2002.06305, 2103.04514, common random numbers) | Three RNG streams per seed (init, data order, SR); fresh seeds 42, 43, 44 shared across cells; the analysis always blocks on seed (a fixed choice, not data-dependent) | Evaluation; S1 |
| M12 | **E1M2 is aliased with INT4** (cross-domain, N1): E1M2 with subnormals is the symmetric INT4 grid times 1/4 | No Phase 1 cell; a metamorphic Phase 0 test | Registration "Phase 0" |
| M13 | **Cost is unmeasured and wide** (asset) | Phase 0 probe J1 measures BF16 and emulated throughput, compile time and packing (2 and 4 runs per GPU); Phase 1 caps follow a formula fixed now | Compute; S2 |
| M14 | **The pipeline and data do not exist** (asset) | Harness, tokenizer pin (Mistral-7B-v0.1, Apache-2.0, revision 27d67f1b), FineWeb-Edu sample-10BT files 000 and 001 at revision 87f09149 (ODC-BY, 4.31 GB; download needs Kevin's OK) | Compute; Safety |
| M15 | **Scoop and access risk** (frontier) | Graphcore released three FP4 reports in 13 months, two in September 2026; ARITH 2025 is closed access; MXFP4-MARS and Agrusa et al. are abstract-only. Recorded as coverage limits; the novelty refuter should try IEEE access | Novelty Ledger |

Eight corrections to the frozen dossier, recorded here because the dossier is
not edited:

1. "A Zenodo 2x2 study ... its content was not opened": the frontier cell read
   it ([Zenodo 22554253](https://zenodo.org/records/22554253), 2026-09-06).
   It crosses block size {16, 32} with scale format {E8M0, E4M3} in a GEMM's
   backward error under exact accumulation, E2M1 fixed. Scale format moves
   error more than block size in all 40 cells, and the author states that
   transfer to training loss is untested.
2. The closest priors are 2505.19115, 2509.17791 and 2603.28765, with
   2606.20381 fourth, not 2501.02423 (frontier and kill-shot cells).
3. "Two-way ANOVA ... the 4.5 b iso-storage contrast" on the dossier's four
   levels is rank-deficient (8 of 10, D1); fixed by M1.
4. "Declare the GEMM model (dequantize, BF16 matmul, FP32 accumulate)" is
   inexact for the BF16-scale cell and for a folded per-tensor scale (N1);
   fixed by M4.
5. "E1M2" in Phase 0 is INT4 times 1/4 (N1).
6. "First experiment (47 GPU-h)": unmeasured. The central projection is 45
   GPU-h with two runs per GPU and 68 without, the range is 18 to 272 (S2),
   and caps are set by formula after Phase 0.
7. "3-point LR sweep per cell, then 3 seeds at the tuned LR": too narrow at
   this scale (2608.11859); replaced by M9.
8. The seed-noise anchor quoted from 2505.19115 ("standard deviation of
   0.001") is 0.00195 from the printed values (N1).

## Claim and Research Question

**Question.** In emulated 4-bit training of a 35M-parameter Llama-style model
(d 384, 6 layers, SwiGLU 1024, vocabulary 32,000) on 1.2B FineWeb-Edu tokens,
with the known non-format causes held fixed, how much of the final validation
loss gap is explained by the element grid (E2M1 against symmetric INT4, 15 codes
each), by a block-size step at fixed scale encoding (E8M0, B32 to B16), by a
scale-encoding step at fixed block size and storage (E8M0 to UE4M3 with its
FP32 tensor scale, B16, 4.5 b), and by the equal-storage trade between a wider
scale and a smaller block (BF16/B32 against UE4M3/B16, 4.5 b)? Does the grid
interact with the scale configuration in the direction a tensor-level
signal-to-noise analysis predicts?

The variables are the grid (2 levels) and the scale configuration (4 levels),
crossed (8 cells), plus a BF16 reference and one emulation-path control.

**Claim scope.** `systems-pipeline` (training numerics under one declared
emulator). Not `architecture-causal`: no architecture is proposed. No claim
about native FP4 hardware speed, energy or kernels, about RHT, about rounding
modes, about UE5M3, or about scales above 35M. The claims the design can
license have the forms: "at 35M, under exact decoded-operand TF32 emulation, the
grid effect is (not) at least half the scale-encoding effect"; "the grid does
(not) interact with the scale configuration in the predicted direction"; "the
MXFP4-to-NVFP4 analogue gap divides into a block step of X and a scale step of
Y"; "35M cannot resolve the documented MXFP4-vs-NVFP4 gap". Any GRID or
interaction claim waits for Stage 1c's five seeds and the dossier's 125M
replication.

**Hypotheses under test.** H_sep (the prior, generalised): with the grid
varied, the scale-encoding effect is at least twice the grid effect and the
interactions are smaller than the scale effect (verdict PRIOR_SURVIVES).
H_int (this proposal's mechanism): power-of-two scales penalise the uniform
grid more than the floating-point grid (I_fmt > 0 and I_blk > 0; verdicts
P_int CONFIRMED and GRID_OR_INTERACTION). They make opposite predictions for
the interaction contrasts.

## Strategic Fit and Why Now

C5 is item 4 of the backfill queue (`program/backlog.md`); D67 restarted it with
Kevin's request to continue every line. Its score packages Phase 1 for Kevin's
D24 ruling; it is not an admission. Three facts make the first step worth its
cost now:

- **The scale-versus-grid conclusion has never been tested with the grid
  varied.** Hu et al. ([2509.17791](https://arxiv.org/abs/2509.17791)) conclude
  "Scale Representation is the Primary Bottleneck" with E2M1 fixed, and
  [2505.19115](https://arxiv.org/abs/2505.19115) reaches the same ranking with
  E2M1 fixed. Format designers now argue for uniform grids
  ([2606.20381](https://arxiv.org/abs/2606.20381),
  [2510.25602](https://arxiv.org/abs/2510.25602)) and adaptive grids
  ([2603.28765](https://arxiv.org/abs/2603.28765),
  [2605.31035](https://arxiv.org/abs/2605.31035)), each at one scale setting.
  N2 predicts that the answer depends on the scale configuration: E2M1's
  advantage is robust under power-of-two scales and vanishes or reverses under
  fine scales.
- **The emulation literature has a numerics defect worth publishing in its own
  right.** Decoding a BF16-scaled block to BF16 rounds 28.5% to 42.6% of
  operands (N1); folding an FP32 tensor scale into operands rounds 79% (N1).
  Phase 0's conformance suite and containment tests are reusable by any
  emulation study.
- **Cheap stopping points.** Phase 0 costs at most 3.05 GPU-h of caps. Stage
  1a (15 to 26 GPU-h central) stops Phase 1 if 35M cannot resolve the best
  documented format difference.

The area is crowded. At least six FP4 pretraining submissions to ICLR 2027
appeared in September 2026 (frontier cell), and four sources this design
relies on appeared that month (2609.02846, 2610.00053, Zenodo 22554253,
2609.08135). The scoop risk named in the dossier is concrete (M15).

## Primary-Source Evidence

Every row was opened by a discovery cell or by synthesis. "Full" means the
`orx paper --full` text read by targeted section; "abstract" means abstract or
metadata only. First-party marks a number not independently replicated; single
trajectory marks a number from one run. Claim ids are the Citation doctor's
registry (`doctors/citation.json`). Synthesis re-read C01 to C09, C12, C14,
C17, C20 and C24 to C26 in the cells' saved full texts. N1, N2, D1, S1 and S2 are this
bundle's computations.

| id | Claim used here | Source | Date | Read | Status |
|---|---|---|---|---|---|
| C01 | 350M Llama, E2M1, B16: seven 8-bit scale encodings E1M6 to E8M0 (non-E8M0 encodings leave the sign bit unused, so all are 4.5 b); E1M6 diverges, E3M4 and E4M3 best; block sizes 8, 16, 32, 64, 128 under E8M0 and E4M3: modest effect, diminishing below 16; SR switched per operand (six): helps on gradients in backward and update GEMMs and activations in the update GEMM; a sqrt(3) gradient-noise threshold; App. Table 4: 125M, 30B tokens, five seeds, losses 3.03, 3.027, 3.025, 3.027, 3.029, stated SD 0.001 (sample SD of the printed values 0.00195, N1); reference code public | [2505.19115](https://arxiv.org/abs/2505.19115) Sec. 3.1, Figs. 1-3, 7, Sec. 4, App. Table 4; [code](https://github.com/Anonymous1252022/fp4-all-the-way); NeurIPS 2025 spotlight per [OpenReview kuzye4EPLR](https://openreview.net/forum?id=kuzye4EPLR) | 2025-05-25 (v2 2025-08-10) | full (frontier, kill-shot, synthesis) | verified; single runs per sweep |
| C02 | Thousands of configurations; E2M1 throughout; "Scale Representation is the Primary Bottleneck" (Principle 2); E4M3 "despite applying tensor scaling, did not converge due to its range limitation"; UE5M3 outperforms E8M0 but needs tensor scaling and SR in the backward pass; could not replicate 2505.19115 up to 1B (App. .3); "FP4 training dynamics may not be consistent across model scales" | [2509.17791](https://arxiv.org/abs/2509.17791) Principle 2, App. .3, Conclusion; ICLR 2026 decision rejected per [OpenReview OEXOAMvsc6](https://openreview.net/forum?id=OEXOAMvsc6) | 2025-09-22 (v1 only) | full (frontier, kill-shot, asset, synthesis) | verified; not peer-reviewed |
| C03 | 340M dense pretraining, W4A4G4 except the final four layers, RHT on the weight-gradient GEMM, SR on activation gradients, every format "emulated by de-quantizing to FP32"; NVFP4 "strictly better than NVINT4 when used to quantize all tensors"; part of IF4's gain comes from NVINT4 on Hadamard-transformed weight-gradient inputs; symmetric INT4 (-8 unused); FineWeb-Edu, Llama-2 tokenizer, about 100B tokens | [2603.28765](https://arxiv.org/abs/2603.28765) Sec. 4.1, Fig. 5a, App. A, footnote 3; [code](https://github.com/mit-han-lab/fouroversix) | 2026-03-30 (v1) | full (frontier, kill-shot, synthesis) | verified; no seed replication found |
| C04 | Grid E2M1 against E1M2/INT4 with RHT scope varied, FP32 single-level scale, block 1x16, SR on dY; SQNR: E2M1 leads before rotation (21.90 against 19.94 dB), E1M2 after (23.19 against 20.00); "Scale hierarchy design remains orthogonal" (asserted, not tested) | [2606.20381](https://arxiv.org/abs/2606.20381) Sec. 4 (recipe, Table 1), Sec. 5.2; ICLR 2027 submission [OpenReview bub7HTzeSv](https://openreview.net/forum?id=bub7HTzeSv) | 2026-06-18 (v1) | full (kill-shot, synthesis) | verified |
| C05 | QSNR theorem: MXINT4 beats MXFP4 iff block crest factor below 2.04, NVINT4 beats NVFP4 below 2.39; Llama-3.1-8B tensors: crest factor at B32 median 2.48, Q3 2.96, at B16 median 2.16, Q3 2.39 (no rotation); NVINT4 wins 64.3% of blocks with mean QSNR 20.55 against NVFP4's 20.60, and 21.65 against 20.35 after RHT; direct-cast inference: NVINT4 loses on 12 of 12 models without rotation, wins 12 of 12 with; 4-bit training not run (8-bit only) | [2510.25602](https://arxiv.org/abs/2510.25602) Theorem 1, Fig. 3, Table 2, Sec. 5.1-5.3; [code](https://github.com/ChenMnZ/INT_vs_FP) | 2025-10-29 (v1) | full (kill-shot, frontier, synthesis) | verified |
| C06 | UE5M3 maximum 61,440 (Eq. 3, top exponent reserved), smallest subnormal 2^-17; E4M3 maximum 448, smallest 2^-9; "one seed-42 Nemotron-H 8B trajectory per configuration", differences "descriptive"; the decoded-operand control "reconstructs the FP4 operands as FP32 tensors and applies a standard Torch matrix multiplication"; native outputs are modelled by groups of 64 products, FP32 round-to-nearest partials, round-toward-zero cross-group additions, a 1/1024 lattice; Table 10 window means: B16 probe-matched 2.3090, B16 decoded-operand 2.3157, B32 2.3241 | [2609.02846](https://arxiv.org/abs/2609.02846) Eq. 3, Table 2, Secs. 6.1-6.3, Fig. 2, statistical note, Table 10; [code](https://github.com/MrHuff/ue5m3-fp4) | 2026-09-02 (v1) | full (all cells, synthesis) | verified; single trajectory |
| C07 | MXFP4 = E2M1, UE8M0, block 32; NVFP4 = E2M1, E4M3, block 16 (block and scale change together, 4.25 against 4.5 b); MXFP4 matches NVFP4 loss with 36% more tokens (8B); Hadamard size and sign randomisation show no measurable effect at small scale (1.2B) | [2509.25149](https://arxiv.org/abs/2509.25149) Table 1, Sec. 4, Sec. 5, App. A.3, E.4.1 | 2025-09-29 (v2 2026-03-04) | full (kill-shot, frontier, synthesis) | verified |
| C08 | MXFP4 4.25 b, NVFP4 and HiF4 4.5 b; NVFP4 "does not converge without PTS"; OpenPangu-1B averaged over 4 seeds, larger models single runs; matched-storage margins not separable from seed variance | [2604.08826](https://arxiv.org/abs/2604.08826) Sec. 3, Sec. 5.1, Table 3, Limitations | 2026-04-09 (v2 2026-09-25) | full (kill-shot, synthesis checked locators) | verified |
| C09 | Native MXFP4 on MI355X, Llama 3.1-8B: quantizing Wgrad is "the primary driver of convergence degradation"; randomised Hadamard and SR fail once Wgrad is quantized, deterministic Hadamard restores | [2605.09825](https://arxiv.org/abs/2605.09825) abstract, Sec. 3.2 | 2026-05-11 (v4 2026-08-12) | full (kill-shot, frontier, synthesis abstract) | verified |
| C10 | 366 training runs over exponent bits, mantissa bits and block size, with the block scale stored in high precision | [2501.02423](https://arxiv.org/abs/2501.02423) Sec. 3, Sec. 3.6 | 2025-01-05 (v3 2025-06-04) | full (all cells) | verified; ICML 2025 |
| C11 | Quantizing LayerNorm affine parameters is a key driver of microscaling instability; withdrawn from ICLR 2026 | [2506.20752](https://arxiv.org/abs/2506.20752) abstract; [OpenReview IuigXFBGHI](https://openreview.net/forum?id=IuigXFBGHI) | 2025-06-25 (v1) | full (frontier) | verified; preprint |
| C12 | 8B, 160B tokens: native MXFP4 recipe ends 2.11% above BF16, TE NVFP4 with four final BF16 blocks 0.87%; one trajectory per recipe; outcomes depend jointly on scale contract, operand and execution path | [2610.00053](https://arxiv.org/abs/2610.00053) Abstract, long-run section | 2026-09-04 (v1) | full (frontier, kill-shot, asset; synthesis checked) | verified; single trajectory |
| C13 | Backward-error 2x2 (block {16, 32} x scale {E8M0, E4M3}), E2M1 fixed, exact accumulation; scale moves error more than block size in all 40 cells; E8M0 exponent rounded up; quantizer bit-exact against microxcaling; transfer to training loss untested; decomposition post hoc under an amendment | [Zenodo 22554253](https://zenodo.org/records/22554253) Secs. 3, 4.2, limitation (vii) | 2026-09-06 | full (frontier) | verified; single author |
| C14 | Below a block-size threshold quality degrades with UE4M3 scales (narrow distributions against limited scale range); UE5M3 "obviating the need of global scaling"; PTQ only | [2601.19026](https://arxiv.org/abs/2601.19026) abstract, Sec. 4.3 | 2026-01-26 (v1) | full (frontier, kill-shot; synthesis checked) | verified; ICLR 2026 poster (frontier) |
| C15 | The block-size paradox is partly an artifact of absmax scale selection; hierarchical scales, UE5M3 and four-over-six remove most of it; PTQ only | [2605.08565](https://arxiv.org/abs/2605.08565) abstract | 2026-05-08 (v2 2026-06-08) | full (frontier, asset) | verified |
| C16 | Absmax scaling under-uses the E2M1 grid for heavy-tailed tensors; halving the scale narrows the 4-bit pretraining gap | [Half-S, Findings of ACL 2026](https://aclanthology.org/2026.findings-acl.241.pdf) abstract, Sec. 3 | 2026 | full PDF (frontier) | verified |
| C17 | H100 tensor cores with 16- and 19-bit inputs and FP32 output use exactly 2 extra alignment bits and truncate; FP4 and FP6 MMA kinds not addressed | [2512.07004](https://arxiv.org/abs/2512.07004) Secs. 4.1.6-4.1.7 | 2025-12-07 (v4 2026-06-11) | full (cross-domain, synthesis) | verified |
| C18 | The BF16 reduced-precision-reduction flag "is turned on by default"; `torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction = False` turns it off | PyTorch 2.14 notes, https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html | read 2026-10-10 | full page (cross-domain, synthesis) | verified; the image runs torch 2.11, so Phase 0 asserts the value |
| C19 | Bitwise GEMM results are set mainly by reduction order; cuBLAS reconstructed bit for bit on Blackwell and Hopper | [2609.11356](https://arxiv.org/abs/2609.11356) abstract | 2026-09-10 | full (cross-domain) | verified |
| C20 | Few-bit SR implementations are biased: 2 random bits give bias -0.124 ulp, 3 bits with BF16 inputs -0.047 | [2504.20634](https://arxiv.org/abs/2504.20634) Figs. 1-2 | 2025-04-29 | full (cross-domain, synthesis) | verified |
| C21 | P3109 defines SR modes with an explicit number of random bits, ties-to-even and saturation modes | [2606.04028](https://arxiv.org/abs/2606.04028) Sec. IV | 2026-06-01 | full (cross-domain) | verified |
| C22 | GPU vendors do not document MX bitwise behaviour and the OCP spec does not prescribe precision or rounding; gfloat and the Microsoft MX library as references | [2607.12915](https://arxiv.org/abs/2607.12915) abstract, Sec. II | 2026-07-14 | full (cross-domain, asset) | verified |
| C23 | Conformance packs (MXFP4 element, E8M0, E4M3, E5M2, BF16) cross-validated against ml_dtypes 0.5.4; OCP permits both saturating and NaN E4M3 overflow; single author, unreviewed | [2606.09686](https://arxiv.org/abs/2606.09686) abstract, Sec. 1 | 2026-06-08 (v3 2026-09-04) | full (cross-domain, frontier) | verified; weak source |
| C24 | LR sensitivity summarises final loss over three orders of magnitude of LR; small models reproduce large-scale instabilities at high LR | [2309.14322](https://arxiv.org/abs/2309.14322) Sec. 2.2 | 2023-09-25 (v2 2023-10-16) | full (cross-domain, synthesis) | verified |
| C25 | Spike score: share of values at least 7 standard deviations from a rolling average of the last 1,000, on training loss and gradient L2 norm | [2501.00656](https://arxiv.org/abs/2501.00656) stability section | 2024-12-31 (v3 2025-10-08) | full (cross-domain, synthesis) | verified |
| C26 | Small models are much more sensitive to hyperparameters; revealing the tuned frontier may need hundreds of random-search configurations | [2608.11859](https://arxiv.org/abs/2608.11859) Sec. 1, Sec. 4.1 | 2026-08-12 | full (kill-shot, synthesis checked) | verified |
| C27 | One-bit changes in initial parameters lead to vastly different models (image classifiers) | [2103.04514](https://arxiv.org/abs/2103.04514) abstract | 2021-03-08 (v3 2021-07-10) | full (cross-domain) | verified |
| C28 | Initialisation and data order contribute comparably and largely independently to fine-tuning variance | [2002.06305](https://arxiv.org/abs/2002.06305) | 2020-02-15 | report (cross-domain) | verified |
| C29 | FP and INT formats trained at 30M to 200M on C4 with forward-only QAT; Gaussian-MSE capacity tracks validation loss | [2506.01863](https://arxiv.org/abs/2506.01863) Sec. 2, Fig. 3 | 2025-06-02 | full (kill-shot) | verified; forward-only |
| C30 | Several 4-bit grids trained at 30M to 100M under E4M3/B16 scales, forward-only QAT | [2605.12327](https://arxiv.org/abs/2605.12327) Sec. 5.3 | 2026-05-12 | full (kill-shot) | verified; forward-only |
| C31 | Transposition-inconsistent 1D blocks as an FP4 instability cause; 2D transposition-invariant blocks | [2607.24953](https://arxiv.org/abs/2607.24953) abstract | 2026-07-27 (v1) | dossier, abstract (cells) | verified at abstract level |
| C32 | MXFP4 with Hadamard, SR, overflow-aware scaling and a macro block scale claims to cut MXFP4's extra tokens over NVFP4 from 36% to 0.21% (ICLR 2027 submission) | [OpenReview 18UVn4y0SO](https://openreview.net/forum?id=18UVn4y0SO) | 2026-09-18 | abstract (frontier) | UNVERIFIABLE_ACCESS full text |
| C33 | NVFP4 recipe ingredients compared to 8B dense and 30B-A3B MoE at 1T tokens; selective high-precision layers needed; workshop poster on OpenReview, cited as ICML main track by 2609.02846 | [OpenReview jlkIyaG32w](https://openreview.net/forum?id=jlkIyaG32w) | 2026-05-08 | abstract (frontier) | UNVERIFIABLE_ACCESS full text; venue discrepancy |
| C34 | MX-format pretraining study of Llama3 varying "data types, rounding modes, scaling strategies, granularity, and organization"; Semantic Scholar openAccessPdf CLOSED; second-hand, Hu et al. cite it only for SR stabilising FP4 training (2509.17791 Secs. 1 and 3) | DOI 10.1109/ARITH64983.2025.00011 (Semantic Scholar record via host relay) | 2025-05 | abstract and citing texts (frontier, synthesis) | UNVERIFIABLE_ACCESS full text |
| C35 | Second-order theory of GEMM quantization noise: INT has a constant variance profile, FP a multiplicative one, reducing data dependence to a participation factor; PTQ W4A4 | [2609.08135](https://arxiv.org/abs/2609.08135) abstract | 2026-09-08 (v2 2026-09-27) | abstract (synthesis) | verified at abstract level |
| C36 | FP8 instabilities from SwiGLU outlier amplification appear only in long (trillion-token) training | [2409.12517](https://arxiv.org/abs/2409.12517) abstract | 2024-09-19 (v2 2025-02-10) | abstract (kill-shot) | verified at abstract level |
| C37 | FineWeb-Edu: ODC-BY, ungated, revision 87f09149ef4734204d70ed1d046ddc9ca3f2b8f9; sample/10BT has 14 files, 28,518,193,415 B; files 000 and 001 are 2,152,819,114 and 2,152,222,432 B (LFS oids b1ba7b2c... and 3fcf2dc6...) | [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) HF API | read 2026-10-10 | API (synthesis) | verified |
| C38 | Mistral-7B-v0.1 tokenizer: Apache-2.0, ungated, revision 27d67f1b5f57dc0953326b2601d68371d40ea8da, tokenizer.json 1,795,188 B, vocabulary 32,000 | [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) HF API | read 2026-10-10 | API (synthesis) | verified |
| C39 | Reference implementations and licences: gfloat 0.5.2 (MIT, numpy, E2M1, E8M0, E4M3, P3109, MX blocks, SR), microxcaling (MIT, power-of-two scales only, no SR), TransformerEngine `reference_nvfp4.py` (Apache-2.0, E8, E4M3 and UE5M3 scale casts; UE5M3 maximum code 0xFE), ml_dtypes 0.6.0 (Apache-2.0, in uv.lock and the image) | [gfloat](https://github.com/graphcore-research/gfloat), [microxcaling](https://github.com/microsoft/microxcaling), [TransformerEngine](https://github.com/NVIDIA/TransformerEngine) | read 2026-10-10 | GitHub API and README (asset) | verified |
| C40 | Semantic Scholar forward citations of C01, C02, C03, C04, C05, C06 and C34: 91 citation rows, 74 unique citing works; none crosses the grid with the scale format in training (titles screened; the nearest are C03, C08, C12, 2605.06067 and 2605.31035) | Semantic Scholar Graph API via host relay | 2026-10-10 | titles (synthesis) | screened |
| C41 | Repository anchors: 134M GDN hybrid 282,501 tok/s at 243 TFLOPS achieved (Slurm 359); a GPU unit-test job 0.0044 GPU-h (job 516); startup about 10 s per arm (K1 probe 543); architecture image digest `sha256:13a9de83...` with torch 2.11.0+cu128 and Triton 3.6.0 | `legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json`; asset cell | 2026-09-01 to 2026-10-08 | repository (asset) | measured on a different model |

## Closest Prior Work

Ranked by closeness to the proposed measurement.

1. **FP4 All the Way** ([2505.19115](https://arxiv.org/abs/2505.19115),
   Chmiel, Fishman, Banner and Soudry; NeurIPS 2025 spotlight). Same: training
   (not PTQ), all three GEMMs quantized, a scale-encoding sweep at matched
   storage at B16, a block-size sweep under two scale encodings, per-operand
   rounding ablations. Different: the grid is E2M1 in every run; sweeps are
   single runs; block size and scale encoding
   are swept one at a time, so no crossing with the grid exists; emulation
   numerics are not declared at the GEMM level. It is the stronger
   contribution on rounding and on the scale-encoding sweep. This proposal adds
   the grid crossing, seeds, separable contrasts, an exact uniform emulator, a
   positive-control gate and a pre-registered interaction prediction.
2. **Elucidating the Design Space of FP4 Training**
   ([2509.17791](https://arxiv.org/abs/2509.17791), Hu, Luschi and Balanca).
   Same: the question ("which techniques and formats matter"), many scale
   formats, a cost model. Different: E2M1 fixed; scale format tied to block size
   except UE5M3 against E8M0 at B32; no seeds; not peer-reviewed. Its
   disagreement with C01 on E4M3 (C02) is a further reason to run seeds and a
   per-arm LR sweep.
3. **Adaptive Block-Scaled Data Types (IF4)**
   ([2603.28765](https://arxiv.org/abs/2603.28765), Cook et al.). Same: E2M1
   against symmetric INT4 in W4A4G4 pretraining, emulated through FP32 decode.
   Different: one scale configuration (E4M3 block scales at B16), RHT on, no
   seed replication found. It already gives one column of the 2x4 (NV-like) at 340M on
   about 100B tokens; this proposal's E2M1 and INT4 at S3 replicate that column
   at 35M without RHT.
4. **UFP4** ([2606.20381](https://arxiv.org/abs/2606.20381)). Grid crossed
   with RHT scope at an FP32 single-level scale; asserts that scale hierarchy is
   orthogonal without testing it. This proposal's H_int is a test of that
   assertion in the absence of RHT.

Also relevant, not closest: 2510.25602 (the crest-factor theory behind N2;
tensor-level and inference only at 4 bits), 2609.02846 (UE5M3, emulator
control, single trajectories at 8B), 2509.25149 (the confound), 2604.08826
(matched storage at 1B with 4 seeds), 2501.02423 (grid and block in 366 runs
with high-precision scales), Zenodo 22554253 (numerics-only 2x2), 2601.19026
and 2605.08565 (block-size and scale interaction in PTQ), 2506.01863 and
2605.12327 (grids at 30M to 200M, forward-only QAT), 2609.08135 (a GEMM noise
law for INT and FP grids, PTQ).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Grid (E2M1, INT4) crossed with scale configuration in training | 2505.19115; 2603.28765; 2606.20381 | Grid varied at one scale setting (2603.28765, 2606.20381); scale varied at one grid (2505.19115, 2509.17791) | Both varied in one factorial, with all grid interactions estimable | medium (ARITH 2025 unread) |
| Cell set separating block step, scale step and equal-storage trade | 2505.19115 (scale sweep at B16; block sweep at two scales); Zenodo 22554253 (2x2 numerics) | Separate block and scale sweeps | Separability by design with the grid crossed, in training, with seeds; the MXFP4-to-NVFP4 analogue gap split into two steps | medium |
| Exact uniform emulation (TF32-exact decoded operands, epilogue tensor scales, containment tests) | 2609.02846 decoded-operand control (FP32 operands); 2603.28765 (FP32 decode) | Decode to FP32 | A shown defect in BF16 decode (N1) and per-cell containment as a registered test; an emulation-path control in training | low as novelty (instrumentation) |
| Tensor-level interaction prediction frozen before training | 2510.25602 (crest-factor theorem, inference); 2606.20381 (SQNR, one scale); 2609.08135 (noise law, PTQ) | QSNR as a predictor | Prediction of the grid effect per scale configuration from captured training tensors, tested against seed-replicated training loss | medium |
| Positive-control gate on the documented MXFP4-vs-NVFP4 gap before the factorial | 2509.25149, 2604.08826 (the gap) | The gap | Used as a registered resolution gate for a small-scale study | low as novelty (design) |

Novelty wording: No direct prior art found through 2026-10-10 under the
recorded coverage (114 counted orx discover invocations with returned ids in
`query-log.json`: the frontier cell's FR-01 to FR-38, the kill-shot cell's
KS-01 to KS-26, the cross-domain cell's XD-01 to XD-32 (35 invocations), the
asset cell's AS-01 to AS-08, synthesis SY-01 to SY-07; 568 unique ids; 10
OpenReview searches; Semantic Scholar forward citations of seven priors; 58
cell full-text reads and 16 synthesis re-reads; the gaps in the Coverage limits line) for a
training study that crosses a floating-point and a uniform 4-bit grid with
block-scale configurations that separate block size from scale encoding at
equal storage, with seed replication, one exact emulation path and a
pre-registered tensor-level interaction prediction. Queries aimed at this
mechanism directly include FR-01, FR-05, FR-06, FR-16 and FR-36 (keyword:
scale format, block size, grid comparison, storage matching, uniform grid
against E2M1), FR-07, FR-08, FR-21, FR-34 and SY-02 (embedding: the factorial
and the grid-by-scale interaction in plain words), KS-01 to KS-03 and KS-18
(keyword and embedding: factorial and iso-storage), KS-15 (INT4 against FP4
pretraining), XD-31 (embedding: factorial ablation of format components),
SY-01, SY-03, SY-04 and SY-05 (keyword: grid-by-scale interaction, QSNR
predicting loss, crest factor in training, inexact BF16 decode), and every
closest prior's title phrase (KS-07 for 2505.19115; FR-02, KS-04 and AS-02 for
2509.17791; KS-19 for 2603.28765; SY-07 for 2606.20381; FR-03, KS-05 and AS-03
for 2609.02846; FR-04, KS-06 and AS-04 for 2501.02423; FR-10 and KS-08 for
2510.25602). They returned 2505.19115, 2509.17791, 2603.28765, 2606.20381,
2609.02846, 2610.00053, 2604.08826, 2605.31035, 2609.08135 and others, none of
which runs this combination. The unresolved risk is C34 (ARITH 2025): its
abstract names the same factor families for MX formats, whose shared scale is
power-of-two by the OCP definition, so a crossing with non-power-of-two scale
encodings at matched storage is unlikely there but is unverified. PRISMA counts
across all cells and synthesis: 568 unique ids identified by counted queries
and 74 unique forward citations screened by title; 58 full texts read by the
cells and 16 re-read by synthesis; 0 included as a direct prior. Synthesis
alone: 7 queries returning 110 ids (70 unique). The cells did not report
title-screening counts, so no screened-by-abstract figure is given.

## Mechanism and Falsifiable Predictions

**Mechanism (H_int).** A block's elements are divided by a scale s chosen so
the block maximum maps at or below the grid's top code. With a power-of-two
scale rounded up, the block maximum lands anywhere in (q_max/2, q_max], so on
average about half a bit of the grid's range is unused. A floating-point grid's
relative spacing is roughly constant across its binades, so losing the top of
the range removes codes without coarsening the relative error of what remains.
A uniform grid's absolute spacing is fixed, so every unused fraction of the
range coarsens the relative error of every element. With a fine scale (UE4M3
plus an FP32 tensor scale, or BF16) the block maximum maps close to q_max, and
the comparison reduces to the crest-factor trade of 2510.25602: the uniform grid
wins for light-tailed blocks and loses for heavy-tailed ones. The grid effect
should therefore depend on the scale configuration. INT4's penalty relative to
E2M1 should be largest under E8M0 at B32, smaller under E8M0 at B16, and near
zero (either sign) under fine scales. The prior's "scale dominates" ranking,
measured with E2M1 only, would then understate the scale effect for uniform
grids and the grid effect under power-of-two scales.

N2 (registered quantizer, five synthetic distributions, seeds 42 to 44)
quantifies the operand-level version. E2M1 minus INT4 QSNR is +1.82, +1.27,
-0.69 and -0.34 dB for S1, S2, S3 and S5 on Gaussian blocks (block crest
factor median 2.07 at B16, 2.32 at B32). It is +2.80, +2.01, +2.34 and +3.47 dB
with 2% outlier channels. The S1-minus-S2 difference is positive in all ten
distribution and RHT rows (0.54 to 0.81 dB). The S2-minus-S3 difference is
positive in nine of ten (smallest +0.16 dB, for Student-t(3)) and negative only
with outlier channels without RHT (-0.33 dB). Whether training loss follows
depends on which operands dominate, which is why Phase 0 recomputes the
prediction on captured tensors.

**Predictions and registered falsifiers (kill criteria).** Every interval is a
90% t-interval from the randomized-complete-block analysis (cells x seed
blocks); L90 and U90 are its ends.

| # | Prediction | Statistic | Falsifier (reject if) | Owner's prior |
|---|---|---|---|---|
| P0 | The emulator is exact and conformant | Phase 0 gates PG1 to PG6 (registration) | any mismatch against both references, any non-representable decoded operand, any GEMM bound violation, SR bias above 1e-3 ulp, or a non-identical resume → INSTRUMENT_FAIL, no Phase 1 | likely pass after fixes |
| P1 | 35M resolves the documented MXFP4-vs-NVFP4 analogue gap | C_anchor = L(E2M1/S1) - L(E2M1/S3), Stage 1a | G1 STOP: L90(C_anchor) ≤ 0 or C_anchor below 2.5 sigma_hat → STOP_UNRESOLVED_AT_35M; Phase 1 ends (the dossier's "go to 125M" is Kevin's ruling, not this file's) | uncertain, about 0.5 |
| P2 | H_int: power-of-two scales penalise INT4 more | I_fmt = (INT4: S2 - S3) - (E2M1: S2 - S3); I_blk = (INT4: S1 - S2) - (E2M1: S1 - S2) | REFUTED if U90(I_fmt) is below 0 (and separately I_blk); CONFIRMED needs a Holm-adjusted one-sided 5% rejection | about 0.5 for I_fmt, 0.4 for I_blk |
| P3 | H_sep, the prior generalised | D1 = C_fmt - 2 Delta_G, interactions | PRIOR_SURVIVES requires L90(D1) above 0, every interaction with |I| + half-width below C_fmt, and no interaction verdict; GRID_OR_INTERACTION fires if U90(D1) is below 0 or the 3-df interaction F-test has p below 0.05 with max |I| at least 0.5 |C_fmt| | given G1: about 0.25 PRIOR, 0.35 GRID or interaction, 0.35 neither, 0.05 WITHIN_NOISE |
| P4 | Some format factor moves loss at 35M | omnibus F over the 8 FP4 cells | p > 0.10 → WITHIN_NOISE (the dossier's "every cell within seed noise") | unlikely if G1 passes |
| P5 | The emulator does not drive the factor ranking | C_emu = L(NV-like on the BF16 path) - L(NV-like, primary) | EMULATION_SENSITIVE if the 90% CI of C_emu excludes 0 and |C_emu| is at least half the largest factor contrast: every contrast smaller than 2|C_emu| is labelled emulator-conditional | likely not sensitive (exact operands; only accumulation differs) |
| P6 | Operand QSNR predicts the cell ranking | Spearman rho between the frozen Phase 0 prediction and observed mean loss over 8 cells | rho below 0.619 (exact one-sided 5% critical value for n = 8, S1) → NOT_PREDICTIVE | uncertain |
| P7 | Divergence and spikes are rare at the tuned LR | divergence counts; spike score | none (descriptive); spike analysis NOT_ESTIMABLE if fewer than 10 spikes in all fresh-seed runs | likely NOT_ESTIMABLE |

Precedence for the Stage 1b verdict: WITHIN_NOISE, then GRID_OR_INTERACTION,
then PRIOR_SURVIVES, then SCALE_DOMINATES_INTERACTION_UNRESOLVED (L90(D1) > 0
otherwise), then INDETERMINATE. P2, P5, P6 and P7 are reported beside it. A
GRID_OR_INTERACTION verdict or a CONFIRMED P2 triggers Stage 1c (seeds 45 and
46 on the four cells E2M1/S2, E2M1/S3, INT4/S2, INT4/S3) before any claim, and
the verdict is re-read at five seeds on those cells.

**What the design cannot show.** It cannot say anything about rounding modes,
RHT, UE5M3, scales above 35M, native kernels, or energy. It cannot detect a
grid main effect below about 1.0 sigma or an interaction below about 2.9 sigma
with 80% power at three seeds (D1); at sigma 0.004 that is 0.004 and 0.011
nats.

## Cheapest Decisive Pilot

The cheapest decisive step is Phase 0 (registered caps 3.05 GPU-h, central
about 1.0). It decides whether a valid instrument exists: conformance and
containment on CPU and GPU, the GEMM bound, SR unbiasedness, resume identity,
the fake-quant slowdown F against the dossier's 4x line, and the packing gain
that sets Phase 1's cost. The cheapest decisive science step is Stage 1a (15.5
GPU-h central with two runs per GPU, 23.4 without; 70.8 at the high case's
maximum). It decides whether 35M can see a format difference at all, before the
six other cells are paid for. S1 (assumed distributions, 2,000 replicates per
setting, seeds 42 to 44):

| Truth (sigma 0.004, seed correlation 0.5, LR curvature 0.02) | P(G1 continues) | Stage 1b verdict if run (most likely) |
|---|---:|---|
| null (no format effect) | 0.02 | WITHIN_NOISE 0.88; false GRID_OR_INTERACTION 0.06 |
| prior, additive (C_anchor 0.02) | 1.00 | PRIOR_SURVIVES 0.53, INDETERMINATE 0.35, false GRID 0.04 |
| numerics-predicted interaction (C_anchor 0.012) | 0.94 | GRID_OR_INTERACTION 0.99; P2 (I_fmt) CONFIRMED 0.98 |
| grid additive (C_anchor 0.01) | 0.85 | GRID_OR_INTERACTION 1.00 |
| prior, half size (C_anchor 0.01) | 0.84 | SCALE_DOMINATES_INTERACTION_UNRESOLVED 0.22, INDETERMINATE 0.68 |
| interaction, half size (C_anchor 0.006) | 0.42 | GRID_OR_INTERACTION 0.74 (given G1) |
| grid additive, half size (C_anchor 0.005) | 0.30 | GRID_OR_INTERACTION 0.75 (given G1) |

The gate has a cost. It conditions on one contrast, so when the grid effect is
large and the anchor small (last row), Phase 1 stops 70% of the time with a
real grid effect unmeasured. Gating on any FP4 contrast would need INT4/S1 in
Stage 1a: 8 more runs there (6.2 to 9.3 GPU-h central), 6 of which Stage 1b
would run anyway. That alternative is recorded for the owner's decision
(registration decision 41) and not adopted.

No executable pilot exists today. The first would be a `kind: cpu-doctor` orx
node running a registered `scripts/run_fp4_quantizer_doctor.py`: the reference
quantizer's conformance against gfloat and ml_dtypes, the metamorphic and
containment tests, and N2 recomputed. The second would be the J0 GPU-conformance
manifest through the Docker submitter.

## Controls, Baselines, and Ablations

- **BF16 reference** at its own tuned LR (5-point sweep plus three seeds):
  every loss gap is paired by seed against it.
- **Positive control** (Stage 1a): the MX-like (E2M1/E8M0/B32) and NV-like
  (E2M1/UE4M3+FP32/B16) cells, whose ordering is documented at 1B to 12B
  (C07, C08, C12).
- **Emulation-path control**: the NV-like cell rerun with decoded operands in
  BF16 and a BF16 GEMM with PyTorch's default reduced-precision reduction (3
  fresh seeds at the NV-like tuned LR). Its operands are exactly representable
  in BF16 (N1), so only accumulation differs. The defect itself (inexact BF16
  decode) is characterised at GEMM level in Phase 0, not trained.
- **Held fixed (declared confounds):** no RHT; a per-tensor scale only in S3;
  round-up absmax scale selection for every format; true division; ties to
  even; RTN for weights and activations in every GEMM; SR (24 random bits) for
  output gradients in the Dgrad and Wgrad GEMMs; all three GEMMs of every
  linear layer in blocks 1 to 5 quantized; block 6, embeddings, head,
  attention BMMs, softmax and norms in BF16 or FP32 with norm affine weights in
  FP32; 1D blocks along each GEMM's reduction axis; FP32 master weights and
  AdamW states; one data order per seed; one schedule; no qk-norm and no
  z-loss (so LR-driven instability can appear).
- **Tuning:** five-point sweep for each Stage-1a configuration
  {1e-3, 2e-3, 4e-3, 8e-3, 1.6e-2} plus one extension beyond an edge; three
  points centred on the reference configuration's tuned LR for each Stage-1b
  cell plus up to two extensions; quadratic refinement in log2 LR, clamped to
  half a grid step; three fresh seeds at the tuned LR (S1 tuning bias 0.0001 to
  0.0008 nats).
- **Deferred factors (not ablated here):** rounding mode (RTN against SR per
  operand), RHT, UE5M3, scale-selection rule (four-over-six, Half-S), 2D blocks,
  BF16 final layers, and a larger model. N2 and the Phase 0 numerics report the
  RHT and scale-rule dependence at tensor level only.

## Evaluation, Statistics, and Leakage Checks

**Primary endpoint.** Final validation loss (mean next-token NLL in nats) at
step 18,311 on a 15M-token held-out set, evaluated with the run's own forward
numerics; the BF16-forward evaluation of the same weights is a secondary.
Loss gap = cell minus BF16, paired by seed.

**Analysis.** A randomized complete block design: the 8 FP4 cells x 3 seeds,
with seed as the block (fixed in advance, not chosen from the data), residual
df 14. It gives the omnibus F-test (7 df), the 3-df grid x scale interaction
F-test, and the registered contrasts with 90% t-intervals. Standard errors in
units of the per-run residual SD sigma (D1): Delta_G 0.41; C_blk, C_fmt and C_iso
0.58; each interaction 1.15; D1 1.00. Variance fractions (omega-squared for
grid, scale configuration, interaction, seed and residual) are reported with
parametric-bootstrap intervals. Assumption checks (Shapiro-Wilk on residuals,
Levene across cells) are reported. A within-block permutation test of the
omnibus and interaction F-tests is a reported sensitivity; the verdicts use the
registered parametric rules.

**Operating characteristics (S1).** Rules were revised once before
registration after S1 showed two defects in the first draft: reading three
interaction contrasts without an omnibus gate gave a false GRID_OR_INTERACTION
rate near 0.3 under the null, and requiring interaction intervals inside half
the scale effect could not be met at sigma 0.004 or above. Both are now fixed
(omnibus 3-df gate at 5%; "small" means smaller than the scale effect itself).
Selected rows (seed correlation 0.5, LR curvature 0.02):

| Truth | sigma | P(G1) | Given G1: WITHIN_NOISE / GRID / PRIOR / SDIU / INDET | P2 I_fmt CONFIRMED / REFUTED |
|---|---:|---:|---|---|
| null | 0.002 / 0.004 / 0.008 | 0.01 / 0.02 / 0.02 | if run unconditionally: 0.90 / 0.88 / 0.86 WITHIN_NOISE, GRID 0.06 / 0.06 / 0.07 | 0.04 / 0.04, 0.02 / 0.06, 0.03 / 0.05 |
| prior additive | 0.002 / 0.004 / 0.008 | 1.00 / 1.00 / 0.83 | 0 / 0 / 0.99 / 0 / 0.01; 0 / 0.04 / 0.53 / 0.07 / 0.35; 0 / 0.07 / 0.05 / 0.21 / 0.66 | 0.02 to 0.07 either way |
| numerics interaction | 0.002 / 0.004 / 0.008 | 1.00 / 0.94 / 0.43 | GRID 1.00 / 0.99 / 0.74 | 1.00 / 0.98 / 0.53 CONFIRMED, 0 REFUTED |
| grid additive | 0.002 / 0.004 / 0.008 | 1.00 / 0.85 / 0.32 | GRID 1.00 / 1.00 / 0.75 | 0.02 to 0.06 either way |

Without seed correlation (rho 0) the PRIOR_SURVIVES rate at sigma 0.004 falls
from 0.53 to 0.21, so seed blocking matters. Under the null the overall false
GRID_OR_INTERACTION rate through the gate is about 0.005 (0.02 x 0.25). The
sigma anchors are the 0.00195 recomputed from C01 and the HiF4 statement that
1B margins of 0.01 to 0.14 relative-loss points sit inside seed noise (C08).
The effect sizes (C_anchor 0.006 to 0.04 nats) are assumptions bracketing
C06's single-seed 0.0151 block-size delta at 8B.

**Missing data and divergence.** A fresh-seed run that diverges (NaN, Inf, or
validation loss above 10 at any evaluation) is recorded as divergent. A cell
with a divergent fresh seed is UNSTABLE_AT_TUNED_LR. The factorial is analysed
by OLS on the unbalanced design only if every cell keeps at least 2 finite
seeds; otherwise the verdict is INCONCLUSIVE_UNSTABLE with the instability
table. Sweep divergences count as infinite loss for tuning.

**Leakage checks.** Validation documents are those with
int(SHA-256(document id)[:8], 16) mod 100 = 0, removed from the training
stream before shuffling; the training stream is a single pass with no document
repeated; validation is never used for tuning except through the sweep's final
validation loss, which is the registered selection criterion and is then
re-measured on fresh seeds (no winner's curse in the reported estimates).
There is no benchmark, so no contamination route beyond the split. The
numerics prediction is frozen (hash recorded) before any Phase 1 run. The
analysis code is frozen with the registration and run blind to cell labels
until the verdict script has emitted its table (cell ids are hashed in the
result files and decoded after).

## Compute and Reproducibility

Image: the architecture image
`127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(torch 2.11.0+cu128, Triton 3.6.0, Python 3.12.3, ml_dtypes present; asset
cell). It holds no C5 code; the Dockerfile copies the source tree, so a rebuild
at the freeze commit (`sbatch infra/slurm/host-single-node/build-architecture-image.sbatch`,
CPU only) gives the registered digest. gfloat 0.5.2 (MIT, numpy-only) is the
second CPU reference; it is to be installed, pinned, for the CPU conformance
suite on the development Mac, not in the image (it is not installed yet).

Launch path (dry run, test-only, submit; one GPU per job; none of these
manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v1/j1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v1/j1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py experiments/manifests/c5-fp4-instability-v1/j1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the same three steps apply to J0, J2 and J3 and to every Phase 1 job. The data
fetch (FineWeb-Edu files 000 and 001 at revision 87f09149, 4.31 GB, and the
tokenizer at revision 27d67f1b) and tokenization run as CPU Slurm jobs after
Kevin's OK, and wait until no Q2 S1a VM or GPU job is running.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 4 (Phase 0's registered caps
sum 3.05 GPU-h, rounded up: J0 0.10, J1 2.20, J2 0.45, J3 0.30; Phase 1's caps
are set later by the formula below and are not part of this ceiling; the
gauntlet's 0.3 GPU-h is reviewer inference only).

Phase 0 arithmetic (S2): J1 runs 10 configurations x 200 compiled steps, 2
eager arms x 60 steps, and packing arms (2 and 4 processes per GPU) for BF16
and NV-like; at the central case (BF16 600k tok/s per process, F 2.0, compile
120 s) it takes 2,491 s, and at the high case (400k, F 4.0, compile 300 s, no
packing gain) 6,575 s, so its cap is 1.2 x 6,575 s = 2.20 GPU-h. J2 (300
uninterrupted steps against 150 plus a fresh-job resume of 150) has a high case
of 1,323 s, cap 0.45. J3 (3,000 BF16 steps with capture) has a high case of
862 s, cap 0.30. J0 is fixed at 0.10 (about 7.6 times three job-516 anchors of
0.0044 GPU-h).

Phase 1 cap formula, fixed here before Phase 0: for each run type,
GPU-seconds = [1.2e9 / (0.9 x r) + E / (3 x 0.9 x r) + o] / k, with r the J1
median per-process tok/s at the adopted packing k (k = 2 or 4 is adopted only
if its aggregate gain is at least 1.2), E = 53M evaluation tokens, and o the J1
startup plus compile time. The cap is 1.2 x the sum over the maximum run
counts: Stage 1a 24 runs plus 3 extensions, Stage 1b 36 plus 12, emulation
control 3, Stage 1c 8. S2 projections without the 0.9 factor:

| Case | Stage 1a | Stage 1b | Emulation | Stage 1c | Total (no extensions) | Maximum | Cap value |
|---|---:|---:|---:|---:|---:|---:|---:|
| low, 2 per GPU | 6.6 | 10.5 | 0.8 | 2.3 | 17.9 | 24.5 | 29.4 |
| central, 2 per GPU | 15.5 | 27.7 | 1.9 | 6.2 | 45.0 | 62.4 | 74.8 |
| central, 1 per GPU | 23.4 | 41.9 | 2.8 | 9.3 | 68.1 | 94.3 | 113.2 |
| high, 1 per GPU | 63.0 | 124.9 | 6.6 | 27.7 | 194.4 | 271.7 | 326.0 |

If Kevin admits less than the formula's total, the registered fallback drops
the S5 pair (E2M1/S5, INT4/S5; C_iso and I_iso lost) first; otherwise Phase 1
waits.

Checkpoints and resume: every 1,000 steps and at the end, to
`~/cotcodec-runs/c5-fp4-instability-v1/` (one directory per run id), with model, optimizer, data
cursor, the three Philox generator states (init, data order, SR keyed by step,
layer, GEMM and operand), and the LR schedule position; a fresh job resumes
from the latest checkpoint. J2 requires bit-identical parameters and loss
trajectories between an uninterrupted run and a fresh-job resume, under
`torch.use_deterministic_algorithms(True)` and `CUBLAS_WORKSPACE_CONFIG=:4096:8`.
Artifacts: per-run configs, loss and gradient-norm trajectories, final
validation losses, sweep tables, the frozen numerics prediction, the verdict
table, receipts with image digest and flags; checkpoints stay on the host;
captured tensors (about 3 GB) stay on the host.

## Safety, Data Rights, and Monitorability

- **Data.** FineWeb-Edu (ODC-BY 1.0, ungated, revision 87f09149), derived from
  Common Crawl; attribution kept in every report; only file ids, revisions,
  hashes, token counts and metrics enter the public repository. The download
  (4.31 GB, two files, three if the split leaves fewer than 1.25B training
  tokens) needs Kevin's explicit OK.
- **Tokenizer.** Mistral-7B-v0.1 tokenizer files only (Apache-2.0, ungated,
  revision 27d67f1b); no model weights are downloaded or released.
- **Models.** 35M-parameter models trained from scratch for numerics research;
  checkpoints stay on the host; no release is planned.
- **Untrusted code.** None executes. The quantizers, harness and any fused
  Triton kernel are reviewed project code under D7; third-party kernels
  (ue5m3-fp4, fouroversix) are read as references and not run on the GPU
  unless reviewed and committed as project code. torch.compile output is
  project code.
- **Host.** No host job of any kind while a Q2 S1a VM or GPU job runs; Phase
  0 GPU jobs wait for a freeze; Phase 1 waits for Kevin's D24 ruling.
- **Public repository.** No host addresses beyond the documented local registry
  name, no credentials, no data text.
- **Monitorability.** No policy is trained and nothing is deployed.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Verdict | What it says | What it closes |
|---|---|---|
| INSTRUMENT_FAIL (Phase 0) | The emulator could not be made exact or conformant under the pinned spec | Phase 1 until fixed; the specific interpretation gap is itself a reportable emulation finding |
| TRITON_GATE (F above 4) | Unfused fake quantization is too slow on this host | Phase 1 until a reviewed fused quantizer exists |
| STOP_UNRESOLVED_AT_35M | 35M on 1.2B tokens cannot resolve even the MXFP4-vs-NVFP4 analogue gap | Every format question at this scale; a quantitative reason a 125M step needs its own admission |
| WITHIN_NOISE | No format factor moves loss beyond seed noise | The factorial at 35M |
| PRIOR_SURVIVES | The scale encoding dominates the grid with the grid varied, interactions smaller than the scale effect | The grid question at 35M; points the next step to rounding and block-size factors and a 125M replication |
| GRID_OR_INTERACTION | The grid matters as much as half the scale effect, or interacts with it | The prior's generality; a headline that waits for Stage 1c and 125M |
| P2 REFUTED | Power-of-two scales do not penalise INT4 more | The proposal's mechanism |
| EMULATION_SENSITIVE | Accumulation path alone moves loss comparably to factors | Factor claims below twice the emulation effect, for this and every decoded-operand emulation study |
| INDETERMINATE | Intervals too wide | Nothing; the measured sigma sizes a successor |

Every Phase 1 verdict also yields the block-step and scale-step split of the
MXFP4-to-NVFP4 analogue gap, with intervals, which no prior reports.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac (OpenAlex rate-limited: 10 rejections logged); the arXiv API and Semantic Scholar through the read-only host relay; 114 counted invocations with returned ids and raw-output SHA-256, 11 backend rejections, uncounted searches and reads logged; cutoff 2026-10-10; degraded coverage recorded (`doctors/source.json`) | Retry OpenAlex citation expansion when its budget resets; search patents and Chinese-language venues |
| Citation | PASS | Claim registry C01 to C41 with locators, dates and read status; arXiv ids snapshotted with version histories; OpenReview rows UNVERIFIABLE_ACCESS (HTTP 200 browser challenge); one quoted number corrected (C01 seed SD); first-party and single-trajectory labels (`doctors/citation.json`) | Read ARITH 2025 with IEEE access; read the MXFP4-MARS and Agrusa PDFs when reachable |
| Novelty | FAIL | No direct prior under the recorded coverage, but the blind critic and the novelty refuter have not run, ARITH 2025 (C34) is unread, and the delta is narrow (`doctors/novelty.json`) | Run the blind critic on `blind/`; resolve C34 |
| Design | FAIL | Intervention, controls, falsifiers, decision rules and their operating characteristics (S1) are specified, but every distribution in S1 is assumed, sigma at 35M is unmeasured, and the harness does not exist (`doctors/design.json`) | Phase 0 J3 and Stage 1a measure sigma; build the analysis as a `cpu-doctor` node on S1's synthetic data |
| Compute | FAIL | No real model loop, no fake-quant kernels, no data on the host, no manifest, no container smoke, no Slurm dry run (`doctors/compute.json`, `compute/attestations-not-run.md`) | Write the harness and quantizers; Kevin's OK for the data download; rebuild the image; dry run and test-only |
| Safety | PASS | ODC-BY data and an Apache-2.0 tokenizer, data text kept off the public repository, no untrusted code executed, host rule respected (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts, UNVERIFIABLE_ACCESS); Design, the vendored
K-Dense `experimental-design` and `statistical-power` skills (design before
data, DOE estimability for the multi-factor design, decision rules with
operating characteristics by simulation); Evaluation, K-Dense
`statistical-analysis` (blocked design, contrasts with intervals, assumption
checks, multiplicity control); Novelty, K-Dense `literature-review` (PRISMA
counts). The integrity gate (seven failure modes) is answered in the
registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only while no Q2 S1a VM or GPU job is running)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; wave-1 reviewers have not run |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01 to C41 |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run; ARITH 2025 unread |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P0 to P7 with registered falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; full-rank cell set (D1), positive control, emulation control |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S1 operating characteristics under assumed distributions |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; Phase 0 caps 3.05 GPU-h; Phase 1 by formula, 18 to 272 GPU-h |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest, no data on the host |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; ODC-BY and Apache-2.0, ids and hashes only |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | Factors confounded in prior work; matched storage needs iso-storage contours | Corrected question and kill lines written | Recorded in the dossier, section 8 |
| new gauntlet, synthesis (2026-10-10) | not scored | The dossier's cell set cannot separate block size from scale encoding (rank 8 of 10), its GEMM model is inexact for one cell, and three of four factors are already swept one at a time | Cell set swapped to a full-rank design; exact TF32 emulation path; positive-control gate; numerics-predicted interaction; per-arm sweeps; decision rules simulated and revised once (omnibus gate) | Awaiting blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-c5-fp4-instability.md` (exit 1) on the committed
bundle, also stored as
`evidence/2026-10-10-c5-fp4-instability/doctors/research-direction-doctor-output.json`.
Three readings the doctor does not make for itself. "All declared budgets must
be positive" comes from parsing the declared `gpu_hours=0.3` as an integer; the
declared budget is honest and is not rounded up to pass. The doctor applies no
79 cap here because its executable-pilot check is textual, while by the
gauntlet rule's cap table this proposal is capped at 79 (no executable pilot)
and 89 (no independent provider-distinct review), and cannot reach 100 without
D24's trust store. The doctor also counts the six OpenReview snapshots as
resolved because those pages return HTTP 200; their bodies are a browser
challenge.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "FAIL",
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
    "Design doctor lacks PASS plus concrete evidence",
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
    "doctor artifact 3 did not pass",
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
    "allUrls": 49,
    "recognizedPrimaryUrls": 47
  },
  "status": "FAIL"
}
```
