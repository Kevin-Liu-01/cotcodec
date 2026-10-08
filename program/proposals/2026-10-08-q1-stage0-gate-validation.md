# Research Direction: Q1 Stage 0 Gate Validation (false accepts, false rejects and cost of a three-gate kernel-correctness ladder against an independent audit)

**Status:** draft; gauntlet wave 1, synthesis by the single synthesis owner; blind closest-prior discrimination, refute-first triad and two provider-distinct reviews not yet run; not pilot-ready: the kill-shot cell found, and synthesis verified on job 713's journal, a fatal confound in the registered primary audit (TF32-admissible thresholds of 1 or more on five of six measured level-2 problems, so an all-zeros output passes the audit's numerical channels there); a score of 100 cannot be certified in this repository (program decision D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-08
**Coverage limits:** orx 0.2.2 only (alphaXiv keyword and embedding search, OpenAlex; 136 discover queries, 3 of them failed), plus arXiv version histories, GitHub and Hugging Face API checks by the frontier cell; the arXiv API, Semantic Scholar and the H100-host relay were not used for retrieval, so there was no forward or backward citation-graph expansion; OpenReview, ACL Anthology full text, ACM, IEEE and Springer full texts, patents, X, Reddit, blogs and Chinese-language sources were not searched; the classic software-engineering and statistics priors were read at OpenAlex abstract level only, three by title only; the PAgE '26 paper (doi 10.1145/3819802.3820580) was read as abstract only; the KernelBench-M witness and suite files were listed by path, not opened; full texts were read by targeted section and grep except Measuring the Checker and The Correctness Illusion, which were read end to end; the alphaXiv index may lag for papers posted on 2026-10-07 and 2026-10-08
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.5
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-08-q1-stage0-gate-validation/bundle.json

## Claim and Research Question

The experiment under review is the draft registration
`program/preregistrations/q1-stage0-gate-validation.md` (not frozen; version card
in its section 2.1: `gate_code_sha256` b5f4fa74..., `audit_code_sha256`
b10a62f7..., `driver_sha256` aa2f365d..., trim rule `q1-stage0-trim/2`, execution
policy `q1-stage0-exec/2`). Decision D31 admits Stage 0 only if its high estimate
through bucket P3 is within 8 GPU-h. It is not (D31, D37), so it runs this
gauntlet (D24; D37 item iv). This proposal argues the case for the design,
prices it with the D37 validation job (Slurm 752), and states its defects. It
edits nothing in the registration. What may change, and who decides, is set by
the registration itself and by D14, D28, D31 and D37.

Registered question (registration section 1): build three kernel correctness
gates of increasing strength and an independent audit that no gate sees, and
measure, on compiler-generated and pre-2025 human-written Triton kernels and
their deterministic mutants, (i) how often each gate accepts a kernel the audit
rejects, (ii) how often each gate rejects a correct kernel, and (iii) what each
gate costs. Stage 0 also builds and validates the corpus it measures on.

Variables and statistics (registration sections 5-8):

- Gates, each a conjunction of the previous one: (a) KernelBench@44130946's five
  native-shape trials at atol = rtol = 1e-2; (b) = a and the KernelGYM launch
  hook (b1) and profiler coverage (b2); (c) = b and KernelBench-Verified's value
  transforms (c1), shape variation (c2) and unaligned remainder shapes (c3) at
  1e-3. Secondaries: a_1e-3, a_head_1e-4, a_head_1e-2, a_static, c_1e-2,
  c_kbv_raw.
- Ground truth: audit tier G (A1 fp64 oracle, A2 held-out values, A3 held-out
  shapes with refusal classification, A4 tolerance-free contracts) under the
  TF32-admissible policy at replicate 42 (D14).
- Primary statistics: MS_g = 1 − FAR_g on witnessed test-split mutants of
  in-scope evaluation parents, on the kernel set a, b and c all referee; paired
  differences MS_c − MS_a, MS_c − MS_b and MS_b − MS_a with cluster-bootstrap
  intervals; FRR_independent(c) over at least 72 independent correct units
  (acceptance criterion 3); GPU-seconds per gate and the pinned c/b statistic.

Claim scope: **systems-pipeline** (instrument validation). Stage 0 makes no RL
claim, and FA-share is computed but not interpreted (registration section 1).

What this proposal claims:

1. The combination Stage 0 measures has no direct prior in the stated coverage:
   a graded three-gate ladder that includes a launch-path anti-hacking rung and
   hack-emulating controls; Triton substrates that are compiler-generated or
   pre-2025 human-written; ground truth from an audit whose inputs are disjoint
   from every gate's and that includes tolerance-free contracts; false
   rejections counted over independent correct units; and per-gate GPU cost.
2. The parts the program's Stage 1 needs (gate (c)'s and the audit's false
   rejections on correct kernels, the control matrix, fidelity to the upstream
   gates, and per-gate cost) are the defensible contribution.

What it does not claim, stated before the evidence:

1. That the registered design is pilot-ready. It is not:
   - F1: its primary audit is vacuous on most measured level-2 matmul and
     convolution problems under the registered TF32 policy;
   - F2: at the primary measured cost, the registered 8 GPU-h stop ends
     inside bucket P1, before any test-quota mutant is scored.
2. That the mutant arm is new. Measuring the Checker (MtC,
   https://arxiv.org/abs/2609.22220) owns mutation analysis of kernel-benchmark
   oracles. Stage 0's mutant miss rates for gate (a) and for c1 would be a small
   Triton replication of its numbers (F3).
3. That mutant miss rates predict on-policy false accepts. The registration says
   so, and https://arxiv.org/abs/2609.09315 reports that traditional fault
   injection does not couple with LLM-generated faults.

Decision this proposal serves: Kevin's admission ruling for Stage 0 (D24, D37),
and before it the D14 TF32-policy decision, which F1 makes the first decision to
take.

## Strategic Fit and Why Now

The case for running Stage 0:

- Q1 is the program's lead question (`program/state.json`). Its Stage 1
  (on-policy false-accept audit, about 12 GPU-h) and Stage 2 (three-arm RL,
  about 1,000-1,400 GPU-h) compare gates by what they let through. Without a
  validated instrument, a Stage 1 difference in FA-share could come from a gate
  implementation bug, an audit hole, or a gate that rejects correct kernels.
  Stage 0 is the check that separates those.
- Kernel-RL systems already gate on correctness with fixed checks
  (https://arxiv.org/abs/2602.05885 ; https://arxiv.org/abs/2609.33074 ;
  https://arxiv.org/abs/2510.17891), and published audits document hacks such
  fixed checks miss (https://arxiv.org/abs/2607.16241 App. H.1;
  https://arxiv.org/abs/2610.05683 section 6.2). None measures graded gate
  strength.
- Why now: D37 asks for a scored, reviewed package before Kevin rules on
  admission. The D37 validation job has now measured the safe execution policy's
  cost. The frontier also moved in the last six weeks: MtC (2026-09-02), RESOLVE
  (2026-10-05), and a preregistered leaky-versus-hardened reward contrast for
  code RL (2026-07-13; https://arxiv.org/abs/2607.11022).

The case against, stated with the same weight:

- Stage 1, the only consumer, is blocked on three Kevin decisions: the R580
  driver or written risk acceptance (D2), a licensed policy (D5; Dr. Kernel-8B
  declares none), and its own gauntlet.
- Registration section 12 requires changes to the worker protocol before any
  Stage 1 scoring: items passed over a pipe, the harness off the candidate's
  import path, and secret per-run audit seeds. So the code Stage 0 freezes is
  not the code Stage 1 will run, and fidelity and controls must be re-run after
  that hardening (kill-shot cell).
- External priors make a small Stage 2 effect plausible. The leaky-suite
  contrast (https://arxiv.org/abs/2607.11022) found a held-out gap of 0.20 pt
  (one-sided 95% upper bound 0.75 pt), and https://arxiv.org/abs/2604.07666
  and https://arxiv.org/abs/2601.04411 point the same way. Stage 0 is far
  cheaper than Stage 2, but its value depends on F1 being fixed.

## Primary-Source Evidence

### In-repository measurements (no new GPU job ran in this wave)

- E1. Pilot pass (Slurm 474, 518 and 548; 0.899 GPU-h; registration sections
  17-18; `program/evidence/2026-10-07/q1-pilot/`).
  - Projection as drafted: about 1,056 GPU-h. Pinned c/b statistic 1.64
    (cluster-bootstrap 95% interval 1.52-2.32), so c-lite is not triggered.
  - Finding 18.3.6: the TF32-policy control (tutorial matmul) fails A3 under
    TF32-admissible at all 5 held-out shapes.
  - Finding 18.3.8: under TF32-admissible, T = 2.67 on L2/3 and 1.19 on L2/74
    (strict-fp32 0.0159 and 0.000586). The registration records this as a
    convolution limitation on two problems.
  - D28 exposure: five evaluation substrates, part of a sixth, eight mutants of
    evaluation parents (three in the test split) and ten controls were scored
    before the freeze. They are listed in `harness/q1/data/pilot_exposed.json`.
- E2. D31 re-pilot (Slurm 713; 0.330 GPU-h; S1-cal kernels only;
  `program/evidence/2026-10-07/q1-engineering-d31/`).
  - At 12 items per GPU, 97 shared attempts on 3 of 8 problems ran out of GPU
    memory, 5 slots were retired, and 93 items never became final.
  - Store versus inline: 698 of 843 twin row pairs identical, 828 with the same
    verdict.
  - The pilot cost model under-predicted the re-pilot's own final inline items
    1.72 times.
- E3. D37 validation job (Slurm 752; 0.1092 GPU-h; branch
  `stage0/q1-exec2-validation` at 13f3180, not merged; evidence
  `program/evidence/2026-10-08/q1-exec2-validation/` on that branch, copied
  into this bundle under `compute/`).
  - Image `cotcodec-q1-gates:23a87683`, from CPU-only build 746 out of a fresh
    clone of 23a8768.
  - 122 of 433 planned items ran and all became final. No GPU resource failure,
    contention retry, failed health check, slot retirement, memory-guard wait
    or A5 `na` occurred at 12 and 2 items per GPU.
  - The largest concurrent sum of measured peak memory was 24.2 GB against the
    68 GB guard budget. Measured peaks reached 1.12 times their estimate.
  - Not reached: L2/87, L2/100 and L2/46, L2/59's consumer gates, and every
    identity control and mutant.
  - Adversarial controls under the store: all 15 consumer-gate aggregates match
    the inline twins. Inline, gate (c) accepted 7 of `result_reuse`'s 16
    configurations with error 0.0, because the freed reference output was
    handed back to the candidate. Through the store, all 16 reject.
  - Cost: R = 2.425 times the exec/2 model (bootstrap over the 5 problems
    reached: 1.14-4.84). It is 6.35 on L2/59, whose 4.3 GB of parameters set
    the per-process cost.
  - Projection through P3 (central / high, GPU-h): A, model without the store,
    10.57 / 12.41; B, model with the store, 10.77 / 12.69; **C, primary
    pre-specified, B scaled by R: 19.99 / 24.66**; C at R's 2.5% point
    11.68 / 13.87; C at R's 97.5% point 35.60 / 44.92; D, per-gate scales,
    18.14 / 22.26; E, store-independent ratio, 26.11 / 32.51. Through P7, C
    gives 31.89 / 40.10.
- E4. Synthesis check of the kill-shot cell's threshold finding (`analysis/tf32_threshold_check.py`
  and `analysis/tf32-threshold-check.json` in the bundle).
  - Input: job 713's re-pilot journal, SHA-256 ddbfbbf6..., which equals the
    record committed in `repilot-713.json`.
  - Rows: inline arm, A1-A3 per-draw rows the audit validity gate admitted,
    every kernel and attempt. Table under F1.
- E5. In-scope composition (`stage0-counts-v2.json`, the host-only counts file
  every cost card used, SHA-256 246e0fb6...). The 69 in-scope evaluation
  substrates (native inputs below 1 GB) are:
  - 45 level-2 S1 substrates: 20 Gemm or Matmul, 25 convolution;
  - 17 level-1 matmul substrates: S1 8, FlagGems 6, Triton tutorials 3;
  - 7 others.
  Under D14 the TF32-admissible threshold applies to all 62 matmul and
  convolution substrates.
- E6. One mutant end to end (L2/95 `plus2minus.L78C14`, job 713; rows in
  `analysis/tf32-threshold-check.json`).
  - Gate (a) and a_1e-3 reject it (`output-mismatch`).
  - Inline A1 under TF32-admissible accepts all 5 draws, each with e = 0.9989
    against T = 1.53-1.69. A2 accepts its one admissible draw (e = 0.9990,
    T = 1.53).
  - A3 rejects at `inner37` (e = 3.8e22), and A4 rejects (in-process and poison
    probes), so tier G rejects it.
  - In the store arm A1 rejects 4 of 5 draws (e about 1,100). This is
    allocator history, since A4 finds the mutant memory-unsafe (registration
    18.8 item 4).
- E7. Where the registered stop falls (`analysis/stop_point_estimate.py`,
  `analysis/stop-point-estimate.json`; a synthesis approximation).
  - The fixed part is 4.294 GPU-h, including the 1.338 spent and the 1.5 GPU-h
    reserve, which leaves 3.706 GPU-h for scoring under the 8.0 stop.
  - Applying the P1/P2/P3 split of the D31 card's exec/1 store-per-job
    scenario (0.49 / 0.38 / 0.13) to the validation job's rows, the stop falls:
    - row C (primary): 48% through P1;
    - row D: 55% through P1;
    - row E: 35% through P1;
    - C at R's 2.5% point: 3% into P2;
    - model rows A and B (unscaled): 22-26% into P2.
  - Under exec/2 the large FRR-core problems that close P1 get more capacity
    units, so the true P1 share is probably larger and the estimate optimistic.

### Findings of this wave

**F1. Fatal confound: under the registered primary policy the audit cannot
reject an all-zeros output on most measured level-2 problems** (kill-shot
cell; verified by synthesis on the job 713 journal).

The audit metric is e(x) = max_i |x_i − r_i| / (|r_i| + 1e-3 ||r||_inf)
(registration 6.1). For any finite reference, e(0) is below 1 and e(−r) is
below 2. The primary threshold is T = max(16 · max(e_r32_device, e_r32_cpu,
e_r32_tf32), 2^-20). A cuBLAS or cuDNN TF32 reference has e_r32_tf32 of about
0.07-0.24 on these problems' A1 draws (up to 0.83 on one A2 draw of L2/46): the
floor 1e-3 ||r||_inf is small next to TF32's absolute error where outputs cross
zero. So T reaches 1 to 13.

Admissible A1-A3 draw rows with TF32-admissible T ≥ 1 in job 713 (inline arm,
S1-cal kernels):

| Problem | Op class | Rows with T ≥ 1 | T range (A1; A2; A3) | Strict-fp32 T max |
|---|---|---|---|---:|
| L2/46 | Conv2d | 13 of 13 (all ≥ 2) | 2.56-3.20; 2.14-13.24; 2.01-3.01 | 0.014 |
| L2/59 | Matmul | 14 of 14 (6 ≥ 2) | 1.81-2.14; 1.05-1.49; 1.78 | 0.026 |
| L2/77 | ConvTranspose3d | 27 of 30 | 1.05-3.84; 0.88-1.97; no admissible draw | 0.150 |
| L2/95 | Matmul | 21 of 25 | 1.53-1.69; 1.53; 0.0009-1.49 | 0.018 |
| L2/100 | ConvTranspose3d | 5 of 6 | 3.45-3.73; 0.0047; none | 0.0067 |
| L2/87 | Conv2d | 0 of 25 | 0.005-0.006; 0.001-0.005; 0.004-0.006 | 0.0063 |
| L1/10 | Matmul | 6 of 49 (A2 only) | 0.0008-0.0009; 0-3.44; 0.0007-0.0009 | 0.011 |
| L1/18 | Matmul | 2 of 35 (A2 only) | 0.0012; 0-2.90; 0-0.012 | 0.014 |

Consequences, each read from the registration's own rules:

1. On these problems "witnessed" (tier G rejects) and "correct substrate"
   (tier G accepts) are set mostly by cuBLAS and cuDNN TF32 error, not by
   faults. Witnessing falls back on A3 crashes and gross errors and on A4.
   A4's memory-fault verdicts follow allocator history and co-scheduling
   (E6; registration 18.2 item 5, 18.8 item 4), which exec/2 changes.
2. The audit-hole replay (registration 6.7) adjudicates a gate rejection that
   the primary audit accepts against fp64 with the frozen T, and books it as a
   false rejection when it is within T. E6 shows the ingredients: gate (a)
   rejects a mutant whose A1 and A2 errors (about 1) sit under T of about 1.5,
   and only A3 and A4 save the verdict. A memory-safe mutant with the same
   numerical error and no held-out-shape crash would be accepted by tier G;
   the replay would find its error within T and book gate (a)'s correct
   rejection as a false rejection. Wherever T ≥ 1 the replay can charge the
   stronger gates with false rejections for catching real faults, which
   inverts the comparison.
3. Criterion 2 (the audit rejects no correct substrate) becomes vacuous on
   those problems. The parent filter admits every mutant whose parent is
   "correct" by a lenient standard.
4. The alternative policy fails the other way. Under strict-fp32 the L2/77
   reference-identity control (ModelNew = Model) is rejected by A1 and A2
   (accepted under TF32-admissible). The strict audit rejects the PyTorch
   reference itself.
5. A fix is data-motivated under D28(iv). It must be designed and validated on
   S1-cal and other non-evaluation kernels only, and it removes from the
   primary analysis every unit whose correctness it would change. For mutants
   that means the ones the fix newly witnesses. So the primary mutant metrics
   on TF32-sensitive problems would still rest on the current audit's
   witnesses. A fix restores the instrument but not the registered primary
   analysis, unless Kevin rules that D28(iv) does not apply. The defect was
   found on non-evaluation kernels (job 713) and on two evaluation substrates
   (L2/3, L2/74 in job 518), so that ruling is his.

Scope of the finding: one job, 8 S1-cal problems (6 level-2), replicate 42,
old exec/1 execution. The extension to the 45 in-scope level-2 substrates is by
op class, not measured. The "all-zeros passes" statement follows from the
registered metric. It has not been run as a control.

**F2. Feasibility: at the primary measured cost, the registered 8 GPU-h stop
ends in P1.** Under rows C, D and E, the 3.706 GPU-h left for scoring end
35-55% of the way through P1 (E7, an estimate). That is before the FRR core
(the large 1.07-2.2 GB problems that close P1) and before any test-quota mutant
(P2). Criterion 3 would then rest on at most the 63 in-scope units, which
registration rule D-1 reports as under-powered. Only the unscaled model rows
(22-26% into P2) and R's 2.5% point (3% into P2) get past P1. Through P3 no
row is within 8 GPU-h: the primary row needs 19.99 central and 24.66 high, and
even R's bootstrap lower point needs 11.68 central (E3).

**F3. Novelty: the mutant arm is occupied; what remains is the
instrument-validation part.** MtC measures the official KernelBench check's
miss rate (16.9% of 7,384 witnessed mutants) and KernelBench-Verified's (KBV)
gain (+4.0 points from hidden inputs, +4.5 from tolerance) on CUDA. It used
about 30 GPU-h on one H100. Stage 0's rules are a Triton port of its rules
(`harness/q1/mutate/README.md`). At trim/2's central plan Stage 0 would score
about 155 pooled witnessed test mutants, about 1/48 of MtC's count, with a
smallest detectable paired difference of 10.1 pp.

The ladder is nested (`harness/q1/analysis.py`: b = a and b1 and b2; c = b and
c1 and c2 and c3), so MS_c ≥ MS_b ≥ MS_a holds by construction. On AST mutants
of kernels that still launch, b1 and b2 accept unless the worker dies, so
MS_b − MS_a is near 0 before any data. Gate (b) is tested only by controls.

### Claim registry

Statuses:

- **VERIFIED_SYNTHESIS**: re-read by the synthesis owner on 2026-10-08 in full
  text (`orx paper --full`; digests in the query log) or computed from the
  hashed input named.
- **VERIFIED_REPO**: read from a committed repository record.
- **VERIFIED_HOST_FILE**: read from a host-only file whose SHA-256 is given.
- **CELL_READ**: read in full text by a discovery cell and not re-read by
  synthesis.
- **ABSTRACT_ONLY**: only the abstract or OpenAlex metadata was read.
- **UNVERIFIABLE_ACCESS**: full text not reachable.
- **ESTIMATE**: a synthesis approximation, as labelled.

Every cited arXiv, GitHub and Hugging Face page has a hashed snapshot (HTTP 200)
in the bundle. Dates are those of the snapshot's version history.

| claim_id | claim | source and locator | date | status |
|---|---|---|---|---|
| C01 | MtC: 10,303 mutants over 188 KernelBench problems, 7,384 with a kill witness; the official check misses 16.9%; family miss rates 8.7 (arithmetic) to 78.6% (precision) | https://arxiv.org/abs/2609.22220 abstract, section 4, Table 2 | 2026-09-02 | VERIFIED_SYNTHESIS |
| C02 | MtC: KBV's +8.5 points split +4.0 hidden inputs and +4.5 tolerance; constant scalings cannot reach remainder-block or index faults; a fuzzing recipe falsely rejects correct kernels 107 times; set cover reaches 98.0% at two inputs per problem (94.8% held out) against 83.1% | 2609.22220 sections 5-6, Table 3 | 2026-09-02 | VERIFIED_SYNTHESIS |
| C03 | MtC: a zeros-output softmax at d = 393,216 passes the official check; two level-3 problems are unrefereeable because their fp32 reference violates the tolerance against fp64 | 2609.22220 sections 2 and 7 | 2026-09-02 | VERIFIED_SYNTHESIS |
| C04 | MtC: substrates are LLM-written CUDA (gpt-5.6-sol through Codex CLI) admitted by a gate; the oracle stays the benchmark's reference; a kill witness is a validity-gated input on which the mutant fails beyond tolerance; an out-of-bounds write into allocator slack is named as invisible to numerical oracles; about 30 GPU-h on one H100 (driver 535, PyTorch 2.7.1, NVRTC 12.6) | 2609.22220 section 3, Reproducibility, LLM-use statement | 2026-09-02 | VERIFIED_SYNTHESIS |
| C05 | MtC is v1 only; its Appendix B carries an unresolved TODO (120 loaded rules against 124 stated); KernelBench-M HEAD d04d6fc7, no licence declared | 2609.22220 App. B; https://huggingface.co/datasets/Elfsong/KernelBench-M | 2026-09-02 | CELL_READ |
| C06 | The Correctness Illusion: 24-26 kernels (15-16 correct controls, 9-10 author-seeded bugs), fp64 CPU reference with per-(op, dtype) absolute tolerances, schema-aware shape fuzzing with boundary values, identical verdicts on five GPU classes including H100 NVL | https://arxiv.org/abs/2606.20128 abstract, sections 3.1-3.3 | 2026-06-18 (v2 2026-07-21) | VERIFIED_SYNTHESIS |
| C07 | Companions: boundary-only shapes 78% recall at 0% control false positives, adversarial values 99% at 94%; per-(op, dtype) calibration raises recall 73.2% to 82.4% and control false positives 0 to 20 of 1,882 | https://arxiv.org/abs/2606.27396 ; https://arxiv.org/abs/2607.16228 | 2026-06-23 (both v2 2026-07-21) | CELL_READ |
| C08 | CGV: of 2,638 accepted drkernel-coldstart-8k kernels, 39.5% fail a tolerance-free gate and 62.1% carry a violation; the standard test accepts 1,487 kernels the verifier rejects against 14 the other way; one uncontrolled gated GRPO arm | https://arxiv.org/abs/2608.12700 abstract, section 1, App. C.4 | 2026-08-13 (v2 2026-08-17) | VERIFIED_SYNTHESIS |
| C09 | KBV: hidden tests vary values, not shapes, by design; a shape-conditional identity shortcut guards the exact test shape; best geomean speedup falls from 1.43x to 0.88x | https://arxiv.org/abs/2607.16241 section 3, related work, App. H.1 | 2026-06-26 | VERIFIED_SYNTHESIS |
| C10 | Dr. Kernel: the hacking check marks a candidate incorrect if no Triton kernel runs; without it RL saturates after about 50 steps; hacking ratio about 20% falling to about 3% with the check | https://arxiv.org/abs/2602.05885 sections 3-4 (ratio figures: App. C) | 2026-02-05 (v2 2026-02-06) | VERIFIED_SYNTHESIS (ratios CELL_READ) |
| C11 | RESOLVE: RKB pairs 100 KernelBench L1 problems with candidates that passed the shipped tolerance tests; two (an ELU and a hardtanh) are empty kernels that still pass; tolerances can hide bugs; 143 synchronization mutants, 92 caught by its determinism tester | https://arxiv.org/abs/2610.05683 sections 2.1 and 6.2, Table 1 | 2026-10-05 | VERIFIED_SYNTHESIS (mutant counts and problem ids CELL_READ) |
| C12 | Leaky-suite contrast: preregistered matched-compute GRPO on MBPP, leaky against hardened tests; held-out gap 0.20 pt, one-sided 95% upper bound 0.75 within a 1.5 pt margin; a static pre-training audit predicts rewarded false-positive mass (Spearman 0.80); false-positive incidence flat | https://arxiv.org/abs/2607.11022 abstract | 2026-07-13 | VERIFIED_SYNTHESIS |
| C13 | In a GRPO bandit model with a noisy verifier, drift on incorrect modes depends on Youden's J = TPR − FPR, with a transition at J = 0 | https://arxiv.org/abs/2601.04411 section 2.2 | 2026-01-07 | CELL_READ |
| C14 | Verifier noise up to 15% keeps peak validation within 2 points of clean (code and science, 4B-9B) | https://arxiv.org/abs/2604.07666 abstract | 2026-04-09 (v2 2026-09-27) | CELL_READ |
| C15 | Systematic verifier false positives cause plateaus or collapse; false negatives act like noise | https://arxiv.org/abs/2605.02909 abstract | 2026-04-06 (v2 2026-08-17) | CELL_READ |
| C16 | Traditional fault injection couples with human faults but not with LLM-generated ones; mutation score is unreliable for LLM faults (6,000+ faulty programs) | https://arxiv.org/abs/2609.09315 introduction, Finding 1 | 2026-09-08 | VERIFIED_SYNTHESIS |
| C17 | A residual normalised by a cancellation-prone denominator gave a max-to-median ratio of 389 (correlation 0.794 with the reciprocal denominator); a nonnegative magnitude normaliser gave 1.0007; threshold fitted as a Generalized Pareto quantile at a stated false-positive rate | https://arxiv.org/abs/2610.02240 sections 2.3-2.5 | 2026-09-29 | VERIFIED_SYNTHESIS |
| C18 | NVIDIA tensor-core TF32 and fp16 semantics reconstructed bit-exactly in Triton; tile shape and split-K fix the reduction order | https://arxiv.org/abs/2609.11356 section 3.2.1 | 2026-09-10 | CELL_READ |
| C19 | An oracle that takes its expectation from the system under test cannot fail ("anchoring") | https://arxiv.org/abs/2608.17214 abstract | 2026-08-17 | CELL_READ |
| C20 | Mixing subsumed mutants causes Type I errors in about 62% of mutation-based comparisons | https://doi.org/10.1145/2931037.2931040 | 2016-07 | ABSTRACT_ONLY |
| C21 | Trivial Compiler Equivalence removes more than 7% equivalent and 21% duplicate mutants and detects about 30% of equivalents | https://doi.org/10.1109/icse.2015.103 | 2015-05 | ABSTRACT_ONLY |
| C22 | Oracle assessment pairs test generation (false positives) with mutation (false negatives) | https://doi.org/10.1145/2931037.2931062 | 2016-07 | ABSTRACT_ONLY |
| C23 | McNemar's test on clustered pairs exceeds its size; Obuchowski's clustered version holds it; cluster-robust inference over-rejects with few clusters | Obuchowski, Stat Med 17(13), 1998; https://doi.org/10.1162/rest.90.3.414 | 1998; 2008 | ABSTRACT_ONLY |
| C24 | Mutant detection correlates with real-fault detection for human faults | https://doi.org/10.1145/2635868.2635929 | 2014-11 | ABSTRACT_ONLY |
| C25 | GateTruth moved its own certified figure from 60/60 to 46/60 after removing unsound equivalence exclusions and blended kill sources | https://arxiv.org/abs/2608.12635 section 4 | 2026-08-12 | CELL_READ |
| C26 | TritonRL multiplies a rule-plus-LLM robust verifier into its reward; input-shape augmentation adds about 12 points of L1 correctness | https://arxiv.org/abs/2510.17891 sections 2.1-2.2 | 2025-10-18 (v2 2026-02-09) | CELL_READ |
| C27 | CATCH labels reward hacking by success under a vulnerable evaluator against correctness under an independent audit | https://arxiv.org/abs/2609.39533 abstract | 2026-09-30 (v3 2026-10-02) | CELL_READ |
| C28 | An all-zeros tensor satisfies KernelBench's allclose on 4 of 60 L1 problems; one kernel scored 283x while writing 0.3% of its output | https://arxiv.org/abs/2609.21058 abstract | 2026-09-17 | CELL_READ |
| C29 | Dirigo finds 600 of 6,988 AI CUDA Engineer kernels marked correct (8.6%) buggy | https://arxiv.org/abs/2609.19611 section 1 | 2026-09-17 | CELL_READ |
| C30 | KernelBench's fixed suite rejects correct kernels and accepts buggy ones; verified Kuiper implementations for all 100 L1 tasks | https://doi.org/10.1145/3819802.3820580 | 2026-06-11 | ABSTRACT_ONLY (UNVERIFIABLE_ACCESS for full text) |
| C31 | KernelZero's checker compares at atol = rtol = 1e-2 with backend constraints; trained on 4xA100; its code repository returns HTTP 404 | https://arxiv.org/abs/2609.33074 App. A | 2026-09-27 | CELL_READ |
| C32 | Upstream pins unchanged at HEAD: KernelGYM 3a84417f, lethe eaff0bb6, kernel_bench_verified 3fdf6fec, KernelBench 423217d9, KernelBench-M d04d6fc7 | GitHub and Hugging Face APIs (frontier cell) | 2026-10-07 | CELL_READ |
| C33 | V-ABFT models the verification difference's variance and reports a threshold-to-error ratio of 7-20x (fp32, fp64) and 48-158x (bf16) at zero false positives | https://arxiv.org/abs/2602.08043 abstract | 2026-02-08 | ABSTRACT_ONLY |
| C40 | Pilot numbers in E1 | registration 17-18; `program/evidence/2026-10-07/q1-pilot/` | 2026-10-07 | VERIFIED_REPO |
| C41 | Re-pilot numbers in E2 | registration 18.8-18.9; `program/evidence/2026-10-07/q1-engineering-d31/` | 2026-10-07 | VERIFIED_REPO |
| C42 | Validation-job numbers in E3 | branch stage0/q1-exec2-validation@13f3180, registration 18.10 and `program/evidence/2026-10-08/q1-exec2-validation/` (copies in bundle compute/) | 2026-10-08 | VERIFIED_REPO (unmerged branch) |
| C43 | TF32-admissible threshold table in F1 | `analysis/tf32-threshold-check.json` from journal SHA-256 ddbfbbf6... | 2026-10-08 | VERIFIED_SYNTHESIS |
| C44 | 69 in-scope substrates: 45 level-2 (20 matmul, 25 convolution), 17 level-1 matmul, 7 other | `stage0-counts-v2.json`, SHA-256 246e0fb68b9f1ba6... | 2026-10-07 | VERIFIED_HOST_FILE |
| C45 | L2/95 plus2minus rows (E6) and L2/77 identity rejection under strict-fp32 (F1 item 4) | `analysis/tf32-threshold-check.json` | 2026-10-08 | VERIFIED_SYNTHESIS |
| C46 | The registered stop ends in P1 under rows C, D and E | `analysis/stop-point-estimate.json` | 2026-10-08 | ESTIMATE |
| C47 | Ladder nesting and fail-open b1/b2 errors | `harness/q1/analysis.py` lines 8-9 | 2026-10-07 | VERIFIED_REPO |
| C48 | Criterion 3 passes with probability 0.70, 0.49 and 0.23 at a true FRR of 0.5%, 1% and 2% with n = 72 and no rejection allowed (0.90, 0.70, 0.35 at n = 110 with one) | binomial computation by synthesis (cross-domain cell's figures reproduced) | 2026-10-08 | VERIFIED_SYNTHESIS |

One cell statement is corrected here. The kill-shot cell wrote that the exec/2
rows were "unvalidated rather than shown to be biased low". That was true when
the cell ran. The D37 validation job has since measured R = 2.425 (E3), so the
exec/2 model is biased low on the evidence now available.

## Closest Prior Work

| Prior | Date | Mechanism | Same as Stage 0 | Differs |
|---|---|---|---|---|
| Measuring the Checker https://arxiv.org/abs/2609.22220 (code and data https://huggingface.co/datasets/Elfsong/KernelBench-M) | 2026-09-02, v1 | Deterministic rule mutants of gate-verified LLM-written CUDA substrates; kill witnesses under the benchmark's own oracle on validity-gated inputs; protocols scored by witnessed miss rate per family; KBV decomposed; set-cover suites checked on held-out mutants; false kills of a fuzzer reported | Mutation analysis of a kernel-benchmark checker, deterministic rules, witnessed denominator, dev/test mutant split, validity gating, family breakdown, gate (a) and KBV-style values as scored protocols | Stage 0: Triton substrates that are compiler-generated or pre-2025 human-written; ground truth from an audit disjoint from gate inputs with tolerance-free contracts (A4 can witness memory faults MtC calls unkillable); a launch-path rung and hack-emulating controls; FRR over independent correct units; per-gate cost; fidelity to upstream gate code |
| The Correctness Illusion https://arxiv.org/abs/2606.20128 , with https://arxiv.org/abs/2606.27396 and https://arxiv.org/abs/2607.16228 | 2026-06-18 | fp64 reference with shape fuzzing on a 26-kernel Triton and CPU corpus; recall on seeded bugs and false positives on correct controls; tolerance calibration | Triton kernels, fp64 oracle, shape variation, both error directions | Hand-seeded (10 bugs, 16 controls) against systematic mutants at scale; no checker ladder, no contracts, no cost |
| Contract-Grade Verifier https://arxiv.org/abs/2608.12700 (code https://github.com/RishiShah99/lethe) | 2026-08-13 | Twelve tolerance-free and contract gates audit 2,638 accepted kernels; one uncontrolled gated GRPO arm | A4/A5-style contracts as an audit of what a standard test accepts | A verifier audit of natural kernels, not a validation of a graded ladder against an independent ground truth on known-correct and known-mutated kernels |
| KernelBench-Verified https://arxiv.org/abs/2607.16241 (code https://github.com/facebookresearch/kernel_bench_verified) | 2026-06-26 | Hidden value transforms and tolerance 1e-3; documents shape-conditional hacks | Gate c1 reimplements it | No mutant-based measurement of its own strength (MtC measured it); shapes not varied by design |
| Dr. Kernel / KernelGYM https://arxiv.org/abs/2602.05885 (code https://github.com/hkust-nlp/KernelGYM) | 2026-02-05 | Launch-path hacking check; RL with and without it | Gate (b) reimplements the released check (D6) | Binary check-versus-none in RL; its false accepts and false rejects are not measured against an audit |
| RESOLVE https://arxiv.org/abs/2610.05683 | 2026-10-05 | Determinism testing, reduction and F*/Pulse proof, without tolerances | A tolerance-free validation of KernelBench L1 candidates | Formal validation of individual kernels at hours per kernel; not a checker-strength measurement |
| When the Reward Suite Is Leaky https://arxiv.org/abs/2607.11022 (code https://github.com/toffee-desuwa/rlvr-leaky-suite) | 2026-07-13 | Preregistered matched-compute leaky-versus-hardened test-suite rewards; static pre-training leakiness audit | The Q1 programme's Stage 1-2 design pattern (gate strength as an RL variable with an audit) | Python unit tests at 1-1.5B, not kernels; bears on Q1 as a whole, not on the Stage 0 instrument |
| GateTruth https://arxiv.org/abs/2608.12635 ; oracle assessment (Jahangirova et al. 2016, https://doi.org/10.1145/2931037.2931062) | 2026-08-12; 2016 | Mutation audits of benchmark testbenches; false positives and false negatives of oracles | The method class: seed faults into trusted code, measure oracle misses and false alarms | Other domains; no graded numerical oracle |

The cells also re-checked the four priors from Codex's list (CUDA-Harness
https://arxiv.org/abs/2609.00058 ; CAKE https://arxiv.org/abs/2608.12629 ; KernelPro
https://arxiv.org/abs/2606.26453 ; AI as a Compiler
https://arxiv.org/abs/2609.36800) and robust-kbench (https://arxiv.org/abs/2509.14279).
None runs a correctness-reward RL comparison or measures a checker ladder.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Mutation analysis of a kernel-benchmark checker with deterministic rule mutants, a witnessed denominator and a dev/test mutant split | MtC https://arxiv.org/abs/2609.22220 ; GateTruth https://arxiv.org/abs/2608.12635 (RTL); MUTGPU and CLTestCheck (developer suites) | yes | none claimed; Stage 0 ports MtC's rules to the Triton AST | 0.9 |
| Gate (a) and KBV-c1 mutant miss rates (FAR per family) | MtC Table 2 and section 5 | yes | Triton substrates and an audit-defined witness only; a small replication (about 155 witnessed test mutants against 7,384) | 0.85 |
| Shape (c2) and unaligned-remainder (c3) families as a gate rung | robust-kbench https://arxiv.org/abs/2509.14279 ; Correctness Illusion https://arxiv.org/abs/2606.20128 (boundary shapes); TritonRL https://arxiv.org/abs/2510.17891 (training-input augmentation) | partly | measured as one rung of a ladder against an independent audit, with a validity gate and refusal handling | 0.5 |
| Launch-path anti-hacking rung (b) with hack-emulating wrapper controls | Dr. Kernel https://arxiv.org/abs/2602.05885 ; AutoTriton https://arxiv.org/abs/2507.05687 ; CUDA Agent https://arxiv.org/abs/2602.24286 | partly | the check's false accepts and false rejects measured against controls and an audit; its interaction with the value and shape rungs | 0.55 |
| Independent audit as ground truth (fp64 oracle, held-out values and shapes with refusal classification, tolerance-free contracts), disjoint from every gate's inputs, in tiers N, G, G-strict and c-disjoint | CGV https://arxiv.org/abs/2608.12700 (contracts); Kernel Contracts https://arxiv.org/abs/2604.22032 ; Correctness Illusion (fp64 and shapes); RESOLVE https://arxiv.org/abs/2610.05683 (tolerance-free); MtC (kill witness under the benchmark's oracle) | partly | the audit serves as the reference standard for validating checkers, not as a verifier; A4 can witness memory faults a numerical oracle cannot. F1 currently defeats this component on TF32-sensitive problems | 0.45 |
| False rejection rate of each gate over independent correct units | Correctness Illusion (16 clean controls); https://arxiv.org/abs/2606.27396 (control false positives); MtC (107 false kills of a fuzzer) | partly | scale (at least 72 independent units) and a graded ladder; MtC's admission gate makes the official check's FRR zero by construction, so it cannot measure it | 0.5 |
| Per-gate GPU cost as a decision variable (c/b rule for Stage 1) | MtC (about 30 GPU-h campaign total); RESOLVE Table 2 (cost per kernel) | partly | marginal and amortized GPU-seconds per rung under a fixed execution policy | 0.5 |
| The combination, run as instrument validation for a matched-budget kernel-RL contrast | none found | no | the bounded statement below | 0.6 |

Merged kill-shot verdict: **NARROWED.** The mutant-metric part (gate (a) and c1
miss rates) is OCCUPIED by MtC. No cell found a direct-prior match for the
combination. By cell:

- frontier: NARROWED. The defensible delta is Triton substrates of trusted
  origin, the ladder with the KernelGYM check, an audit disjoint from gate
  inputs, FRR, and cost. MtC's released witness and set-cover suites are a
  missing comparator gate (licence caveat C05).
- kill-shot: NARROWED, OCCUPIED for the gate (a) and c1 mutant metrics, with
  the fatal identification defect F1 and the feasibility defect F2.
- cross-domain: NARROWED. The instrument belongs to an established method class
  (oracle assessment, GateTruth, verifier fuzzing), so Stage 0 must claim
  instrument validation, not a method.

Novelty wording: No direct prior art found through 2026-10-08 under the
coverage listed here:

- 136 orx discover queries (frontier 55, kill-shot 27, cross-domain 47,
  synthesis 7; 3 failed with no ids), listed below with their returned ids;
- full-text reads of the closest priors by the cells (frontier 42, kill-shot
  22, cross-domain 23) and by synthesis (9: 2609.22220, 2606.20128, 2608.12700,
  2607.16241, 2602.05885, 2610.05683, 2607.11022, 2610.02240 and 2609.09315;
  digests in the query log);
- 30 OpenAlex metadata records (frontier 1, kill-shot 4, cross-domain 25),
  arXiv version histories for 14 ids, GitHub HEAD checks for 5 repositories and
  the Hugging Face dataset API for KernelBench-M.

This is a bounded statement about that coverage, not a global novelty claim.
The blind closest-prior discrimination and the novelty refuter have not run.

Required query types (rule: at least six per candidate). The union of the cells'
and synthesis's queries meets the rule:

- keyword with the mechanism's exact terms: F-k09, F-k15, F-k17, F-k18, K-1,
  K-5, K-21, K-25 and S-3;
- keyword with closest-prior title phrases:
  - Measuring the Checker: F-k01, K-2;
  - The Correctness Illusion: F-k19;
  - Contract-Grade Verifier: F-k05, K-3;
  - KernelBench-Verified: F-k02, K-4;
  - Dr. Kernel: F-k03, K-16;
  - RESOLVE: K-11;
  - When the Reward Suite Is Leaky: S-2;
  - Kernel Contracts: F-k24;
  - Calibrating the Checksum: S-4;
  - Oracles That Cannot Fail: S-6;
- embedding with the mechanism paragraph in plain words: F-e01, F-e12, K-7 and
  S-1 (S-1 is the synthesis mechanism statement);
- openalex for venue and citation context: F-o01 to F-o08, K-9, K-10, K-19,
  K-24, 27 cross-domain queries and S-5;
- published-after bounds where recency matters: F-e06, F-k29, F-k30, F-e15,
  K-6, K-13, K-14, K-21 to K-23, K-27, S-3 and S-7.

Synthesis queries found no new direct prior. S-1 returned the known priors
(RESOLVE, MtC, CGV) and cross-domain verifier audits. S-3 and S-7 (the F1
mechanism) returned no kernel-checker work on TF32 thresholds. S-4 and S-7
returned two threshold-calibration priors for the fix:
https://arxiv.org/abs/2610.02240 and V-ABFT (https://arxiv.org/abs/2602.08043).

Every query and its returned ids (DOIs with angle brackets are percent-encoded):

Frontier cell (55 discover queries, 2 failed):

- F-k01 (orx discover keyword): Measuring the Checker --limit 10 → 2609.22220, 2609.07667, 2609.33160, 2607.01504, 2609.09250, 2608.24320, 2608.01135, 2605.25988, 2603.28794, 2609.36308
- F-k04 (orx discover keyword): KernelZero --limit 12 → 2609.33074, 2504.06151, 0906.2444
- F-k07 (orx discover keyword): KernelGYM --limit 12 → 2602.05885, 2608.12700, 2602.07670
- F-k02 (orx discover keyword): KernelBench-Verified --limit 12 → 2607.16241, 2609.21058, 2502.10517, 2609.22220, 2609.26779, 2609.38384, 2609.17439, 2610.01788, 2609.19352, 2609.12488, 2609.08149, 2610.00760
- F-k05 (orx discover keyword): Contract-Grade Verifier GPU kernels --limit 12 → 2608.12700, 2610.07541, 2609.13585, 2610.02808, 2610.05683, 2606.parallel-kernel-bench, 2608.20711, 2609.36800, 2608.21157, 2608.21227, 2609.13612, 2606.15991
- F-k06 (orx discover keyword): robust-kbench --limit 12 → 2509.14279, 2605.29734, 2603.12440, 2609.31016, 2602.02690, 2608.00848, 2606.22536, 2606.11855, 2606.08063, 2606.11999, 2605.18741, 2602.11437
- F-k03 (orx discover keyword): Dr. Kernel reinforcement learning done right Triton kernel --limit 12 → 2602.05885, 2608.12004, 2608.17641, 2608.hawkeye-hardware-aware-gpu-kernel-optimization, 2609.12471, 2607.23089, 2609.33074, 2606.16497, 2609.36800, 2609.30059, 2603.28342, 2603.21465
- F-k12 (orx discover keyword): KernelPro --limit 10 → 2606.26453, 2608.20532, 2609.12551, 2510.09272
- F-k13 (orx discover keyword): TritonBench --limit 12 → 2502.14752, 2609.12471, 2610.02229, 2609.29626, 2606.20128, 2511.18868, 2511.20100, 2507.05687, 2609.29067, 2609.10226, 2609.36800, 2609.33243
- F-k08 (orx discover keyword): reward hacking GPU kernel generation --limit 15 → 2609.33221, 2609.19101, 2609.28614, 2609.39533, 2609.36245, 2606.04847, 2608.17776, 2610.03055, 2609.14998, 2609.00058, 2608.30724, 2609.33074, 2608.hawkeye-hardware-aware-gpu-kernel-optimization, 2609.00213, 2610.03196
- F-k10 (orx discover keyword): CUDA-Harness --limit 10 → 2609.00058, 2609.24974, 2608.15071, 2609.35738, 2609.40330, 2609.01481, 2608.25593, 2608.23552, 2609.39982, 2609.00196
- F-k09 (orx discover keyword): mutation analysis kernel correctness oracle --limit 15 → 2609.22220, 2609.01775, 2609.33160, 2609.05879, 2609.31596, 2609.23218, 2610.01799, 2609.32996, 2609.01865, 2608.21962, 2609.35841, 2608.05917, 2608.10551, 2608.12635, 2606.20128
- F-k11 (orx discover keyword): CAKE CUDA kernel correctness --limit 10 → 2608.12629, 2609.00058, 2602.24286, 2609.33074, 2607.20908, 2606.16231, 2606.26453, 2608.25124, 2609.12471, 2609.13388
- F-k17 (orx discover keyword): hidden test inputs shape variation kernel correctness --limit 15 → 2608.12629, 2608.30841, 2609.00058, 2608.13882, 2609.22220, 2609.36783, 2608.14375, 2610.05170, 2610.03470, 2610.04512, 2608.11831, 2606.20128, 2609.33074, 2608.22267, 2608.12700
- F-k16 (orx discover keyword): kernel correctness verifier strength reinforcement learning reward --limit 15 → 2609.35677, 2605.12474, 2608.28128, 2609.27572, 2610.07212, 2610.01729, 2610.04469, 2606.28436, 2604.27505, 2610.01207, 2605.vista, 2610.01800, 2610.02545, 2604.16004, 2607.26656
- F-k15 (orx discover keyword): false accept correctness check LLM-generated kernels --limit 15 → 2606.20128, 2608.12700, 2609.21058, 2610.03226, 2609.26550, 2607.16241, 2608.21962, 2609.31540, 2609.39414, 2608.10213, 2609.24895, 2610.00296, 2609.24036, 2605.04956, 2609.25335
- F-k14 (orx discover keyword): KernelBench-M --limit 10 → 2607.16241, 2502.10517, 2609.22220, 2609.26779, 2609.21058, 2608.21157, 2602.24286, 2609.33074, 2610.05683, 2609.30059
- F-k18 (orx discover keyword): mutation testing floating-point numerical software tolerance oracle --limit 15 → 2609.19735, 2608.27100, 2609.22220, 2609.37322, 2609.19352, 2609.11721, 2609.35841, 2610.08808, 2608.14315, 2609.33160, 2608.12635, 2609.07492, 2609.00381, 2608.12970, 2606.31308
- F-k19 (orx discover keyword): Correctness Illusion GPU kernels --limit 10 → 2606.20128, 2609.13585, 2610.03226, 2606.parallel-kernel-bench, 2608.20711, 2607.14541, 2609.11356, 2610.05683, 2609.21058, 2609.33074
- F-e02 (orx discover embedding): LLM reinforcement learning for GPU kernel generation exploits weak correctness checks; reward hacking where generated kernels pass tests without computing the right result --limit 15 → 2609.28614, 2609.39533, 2608.30724, 2608.12700, 2609.22220, 2605.12474, 2608.02712, 2606.04075, 2608.08722, 2607.09492, 2606.04923, 2607.16241, 2605.25189, 2606.15385, 2606.01066
- F-e01 (orx discover embedding): Validate GPU kernel correctness checkers by injecting deterministic mutants into compiler-generated and human-written Triton kernels, then measure each checker's false-accept and false-reject rates against an independent fp64 oracle audit and its cost in GPU-seconds --limit 15 → 2610.05683, 2609.11356, 2610.09142, 2609.29067, 2610.02928, 2609.18123, 2609.33916, 2609.33160, 2609.22220, 2608.12700, 2609.08871, 2608.22331, 2607.17979, 2608.13756, 2608.14527
- F-e04 (orx discover embedding): Robust evaluation of LLM-generated CUDA kernels with hidden inputs, multiple shapes, and tighter tolerances to detect incorrect kernels that pass the benchmark check --limit 15 → 2610.05683, 2608.17379, 2609.00058, 2609.22220, 2609.08871, 2608.12700, 2608.12004, 2608.02712, 2608.09900, 2607.20852, parallel-kernel-bench, 2607.16241, 2605.31464, 2607.04058, 2606.20128
- F-e03 (orx discover embedding): Does training with a stronger verifier reward improve RL for code generation? Matched-budget comparison of strict versus lenient correctness checkers as the reward --limit 15 → 2609.39533, 2610.00890, 2608.24135, 2605.12474, 2607.27271, 2608.02867, 2607.19226, 2607.04332, 2605.28751, 2606.20881, 2606.01066, 2605.30478, 2605.28022, 2604.23488, 2608.12337
- F-e06 (orx discover embedding): Benchmark for LLM generated Triton kernels evaluating correctness and speedup --published-after 2026-01-01 --limit 15 → 2609.36800, 2609.30059, 2609.29067, 2610.03226, 2609.12471, 2608.25061, 2608.17379, 2609.21058, 2606.jax-bench, 2608.12004, 2607.17979, 2607.23089, 2607.04454, 2607.27231, parallel-kernel-bench
- F-e05 (orx discover embedding): Mutation testing to measure the adequacy of test oracles for floating-point numerical code and tolerance-based comparisons --limit 15 → 2609.09315, 2609.33160, 2609.35841, 2609.22220, 2606.26604, 2605.17437, 2605.13279, 2604.19086, 2601.19088, 2512.16741, 2511.14432, 2510.03071, 2506.02954, 2404.09952, 2507.11199
- F-e08 (orx discover embedding): Independent audit of accepted GPU kernels finds many are wrong: tolerance-free contract checks, fp64 reference, unseen shapes and dtypes --limit 15 → 2610.09142, 2609.11356, 2609.37315, 2609.22991, 2609.18123, 2609.33532, 2608.12700, 2609.15015, 2609.19844, 2609.05881, 2609.22220, 2609.09696, 2608.11693, 2608.01715, 2608.13067
- F-k23 (orx discover keyword): test case strength reward code reinforcement learning false positive verifier --limit 15 → 2610.05170, 2608.24135, 2609.35677, 2609.09135, 2609.32172, 2609.03309, 2610.04933, 2605.12474, 2608.28128, 2609.03241, 2609.03955, 2604.16004, 2607.11022, 2609.01354, 2610.01207
- F-k21 (orx discover keyword): AI as a Compiler Triton kernels without the Triton compiler --limit 8 → 2609.36800, 2607.23089, 2608.17641, 2608.12004, 2608.00325, 2609.11356, 2609.37241, 2609.15311
- F-e07 (orx discover embedding): Training a code generation policy with RL using verifiers of different strengths, measuring whether weaker unit tests cause the policy to learn incorrect solutions that pass tests --limit 15 → 2609.39533, 2610.03458, 2609.33220, 2609.09135, 2609.03955, 2608.24135, 2605.12474, 2607.20852, 2607.27271, 2607.11022, 2607.04332, 2605.28751, 2606.16062, 2606.01066, 2603.15611
- F-k22 (orx discover keyword): fuzzing RLVR verifiers --limit 12 → ERROR: error decoding response body
- F-k20 (orx discover keyword): lazy optimization decoy kernel hacking check --limit 15 → 2609.16204, 2609.00058, 2602.05885, 2609.19101, 2609.39533, 2610.03222, 2609.33221, 2609.28614, 2610.08410, 2608.17776, 2610.04581, 2609.19239, 2608.19412, 2609.05372, 2608.29993
- F-k22b (orx discover keyword): Fuzzing RLVR Verifiers --limit 12 → ERROR: error decoding response body
- F-o01 (orx discover openalex): KernelBench GPU kernel LLM correctness --published-after 2025-01-01 --limit 15 → 10.48550/arxiv.2502.10517, 10.48550/arxiv.2607.16241, 10.48550/arxiv.2606.20128, 10.1609/aaai.v40i34.40155, 10.48550/arxiv.2605.26118, 10.48550/arxiv.2602.11000, 10.48550/arxiv.2511.20100, W7106862774, 10.1145/3819802.3820580, 10.48550/arxiv.2606.04847, 10.48550/arxiv.2607.17979, 10.48550/arxiv.2606.16497, 10.48550/arxiv.2609.22220, 10.48550/arxiv.2605.04956, 10.48550/arxiv.2609.30059
- F-o04 (orx discover openalex): mutation testing floating point tolerance test oracle numerical --limit 15 → 10.48550/arxiv.2609.22220, 10.23940/ijpe.18.07.p11.14811486, 10.5753/sast.2025.14183, 10.18653/v1/2026.findings-acl.683, W7161916857, 10.1145/3575693.3575707, 10.48550/arxiv.1906.10742, 10.48550/arxiv.2406.07944, W1583963926, W142920806, 10.4230/lipics.ecoop.2020.22, W2598299391, 10.25675/3.020419, 10.48550/arxiv.2606.06747, W2248259933
- F-o02 (orx discover openalex): mutation analysis GPU kernel benchmark oracle --limit 15 → 10.48550/arxiv.2609.22220, 10.48550/arxiv.2004.08140, 10.1007/s00521-026-11909-3, 10.3390/a18070385, 10.1145/3728950, 10.48550/arxiv.2608.12629, 10.20944/preprints202505.0152.v1, 10.1145/3783992, 10.1002/pro.70334, 10.48550/arxiv.2501.16165, 10.48550/arxiv.2605.23931, 10.65215/ltspreprints.2026.09.30.000357, 10.48550/arxiv.2303.01557, 10.1101/2025.04.29.651183, 10.48550/arxiv.2607.29678
- F-o05 (orx discover openalex): verifier false positives reinforcement learning verifiable rewards code --published-after 2025-06-01 --limit 15 → 10.48550/arxiv.2510.00915, 10.48550/arxiv.2601.04411, 10.48550/arxiv.2602.00513, 10.48550/arxiv.2605.08441, 10.48550/arxiv.2506.14245, 10.48550/arxiv.2605.30244, 10.48550/arxiv.2605.28561, 10.48550/arxiv.2603.16157, 10.54097/mzt6hz16, 10.48550/arxiv.2604.10110, 10.48550/arxiv.2609.23457, 10.48550/arxiv.2609.22347, 10.48550/arxiv.2510.01167, 10.1609/aaai.v40i38.40467, 10.48550/arxiv.2604.05820
- F-o03 (orx discover openalex): reward hacking kernel generation reinforcement learning --published-after 2025-01-01 --limit 15 → 10.48550/arxiv.2602.05885, 10.48550/arxiv.2609.33221, 10.48550/arxiv.2605.13536, 10.48550/arxiv.2603.02637, 10.48550/arxiv.2609.27572, 10.48550/arxiv.2606.04847, 10.1007/978-3-032-36217-9_2, 10.48550/arxiv.2608.08158, 10.1145/3770855.3816468, 10.48550/arxiv.2501.09620, 10.48550/arxiv.2605.21384, 10.48550/arxiv.2607.06175, 10.48550/arxiv.2608.02951, 10.48550/arxiv.2601.03525, 10.48550/arxiv.2602.00424
- F-k26 (orx discover keyword): AutoTriton rule-based reward --limit 10 → 2507.05687, 2610.00729, 2609.33803, 2609.27572, 2609.38862, 2608.06310, 2610.04054, 2609.33221, 2609.31192, 2605.12474
- F-k25 (orx discover keyword): TritonRL robust verification cheating Triton --limit 10 → 2510.17891, 2609.36800, 2608.12004, 2608.17641, 2609.39102, 2609.why-are-ai-agents-lying-cheating-and-coordinating, 2609.04170, 2607.21763, 2609.37280, 2610.00689
- F-e10 (orx discover embedding): mutation testing of GPU kernel test suites CUDA Triton fault injection to evaluate test adequacy --limit 15 → 2609.35841, 2609.25520, 2609.08871, 2609.22220, 2607.04058, 2607.05149, 2607.03223, 2606.20128, 2606.26604, 2605.15638, 2605.00107, 2603.12485, 2602.10478, 2601.19088, 2512.16741
- F-k24 (orx discover keyword): Kernel Contracts specification language ML kernel correctness --limit 10 → 2604.22032, 2610.kernel-autoresearch, 2610.05014, 2609.00058, 2610.10394, 2609.06052, 2608.12629, 2609.38248, 2607.24382, 2609.12471
- F-e09 (orx discover embedding): correctness checker for GPU kernels used as reinforcement learning reward; comparing weak and strong checkers during kernel RL training; false accepts on policy samples --published-after 2026-08-01 --limit 20 → 2609.group-batch-means-sampling-budget, 2610.05683, 2609.33074, 2609.39533, 2609.35677, 2609.35140, 2608.12629, 2610.05014, 2610.02911, 2609.39813, 2610.07043, 2609.09250, 2609.11356, 2609.12471, 2609.33220
- F-k27 (orx discover keyword): Kevin multi-turn RL CUDA kernels reward hacking --limit 10 → 2507.11948, 2609.39533, 2609.00058, 2608.17776, 2609.28614, 2607.20908, 2609.14998, 2609.19101, 2609.33221, 2602.24286
- F-e11 (orx discover embedding): systematic false positives of a verifier, unlike random reward noise, cause reinforcement learning collapse; controlled experiment injecting verifier errors --limit 15 → 2609.35677, 2609.39533, 2609.33220, 2609.17226, 2609.01354, 2609.27883, 2607.11022, 2607.20543, 2607.07436, 2606.01066, 2605.25252, 2605.14220, 2606.05932, 2605.02909, 2603.16140
- F-k28 (orx discover keyword): TorchInductor generated Triton kernels mutation --limit 12 → 2609.36800, 2608.00325, 2608.17641, 2608.12004, 2609.11356, 2609.37241, 2608.03537, 2610.05683, 2607.16241, 2608.20711, 2606.20128, 2607.23089
- F-e13 (orx discover embedding): detecting kernels that do not launch any GPU kernel or branch on training mode; anti-hacking checks for generated kernels; launch hooks and profiler coverage --limit 15 → 2610.09462, 2609.23186, 2608.12700, 2609.00309, 2608.21895, 2607.13640, 2606.28116, 2607.01854, 2606.19262, 2606.20128, 2606.15809, 2606.07968, 2606.11871, 2605.24817, 2609.00351
- F-o07 (orx discover openalex): mutation testing CUDA GPU kernels test suite adequacy --limit 15 → 10.48550/arxiv.2609.22220, 10.1007/978-3-030-16722-6_19, 10.1145/3366428.3380768, 10.1007/s10710-016-9273-9, 10.1016/j.jss.2019.110398, 10.1007/s10664-020-09881-0, 10.1016/j.jss.2019.110398, 10.70675/5747c493z5931z462bz8c5az0f897179fd20, W3006875903, 10.5281/zenodo.5055130, 10.2172/3547206, 10.22541/au.177067589.93635741/v1, W2749431997, 10.1145/3611643.3616337, W592691557
- F-e12 (orx discover embedding): use compiler-generated TorchInductor Triton kernels and human-written library kernels as correct substrates, inject faults, and test benchmark correctness checks --limit 15 → 2610.05683, 2609.29067, 2609.12471, 2609.19611, 2609.18022, 2609.22220, 2608.12700, 2608.02712, 2608.14527, 2608.11886, 2607.04454, 2607.27270, 2607.27231, 2607.20518, 2606.20128
- F-o06 (orx discover openalex): Triton kernel correctness verification large language model --published-after 2025-06-01 --limit 15 → 10.1007/s11704-026-60308-3, 10.48550/arxiv.2609.36800, 10.48550/arxiv.2603.21465, 10.48550/arxiv.2602.11715, 10.48550/arxiv.2604.22032, 10.48550/arxiv.2602.05885, 10.48550/arxiv.2603.21851, 10.48550/arxiv.2510.17891, 10.48550/arxiv.2608.17641, 10.48550/arxiv.2607.04454, 10.48550/arxiv.2607.20475, 10.48550/arxiv.2604.24927, 10.48550/arxiv.2609.30059, 10.48550/arxiv.2603.28342, 10.26153/tsw/64443
- F-o08 (orx discover openalex): KernelBench reward hacking verification --published-after 2026-01-01 --limit 15 → 10.48550/arxiv.2607.16241, 10.48550/arxiv.2606.08960, 10.48550/arxiv.2605.21384, 10.48550/arxiv.2603.02637, 10.48550/arxiv.2604.28182, 10.48550/arxiv.2606.04847, 10.48550/arxiv.2602.05885, 10.48550/arxiv.2609.00058, 10.48550/arxiv.2608.20711, 10.48550/arxiv.2605.12673, 10.48550/arxiv.2607.20518, 10.48550/arxiv.2605.16379, 10.48550/arxiv.2603.19173, 10.48550/arxiv.2609.26457, 10.48550/arxiv.2604.22032
- F-e14 (orx discover embedding): taxonomy of reward hacks in LLM-generated GPU kernels: returning cached output, skipping computation, calling PyTorch fallback, shape-specific shortcuts, timing exploits --limit 15 → 2609.39533, 2609.35587, 2609.18123, 2609.00058, 2607.17979, 2608.02712, 2608.08722, 2608.01804, 2606.04075, parallel-kernel-bench, 2607.16241, 2605.31464, 2605.23215, 2605.25189, 2606.20128
- F-k29 (orx discover keyword): kernel generation verifier RL hidden inputs reward --published-after 2026-09-01 --limit 15 → 2609.35677, 2609.21208, 2610.01066, 2609.39533, 2609.33399, 2609.39436, 2610.04469, 2609.33126, 2609.38847, 2609.37200, 2610.04928, 2609.05028, 2609.32665, 2610.04006, 2609.01354
- F-k30 (orx discover keyword): on-policy false positive rate verifier audit --published-after 2026-06-01 --limit 12 → 2609.03241, 2609.33662, 2608.16003, 2608.00220, 2610.04040, 2610.02808, 2610.06432, 2609.01354, 2609.08798, 2609.15404, 2609.26220, 2609.35677
- F-k31 (orx discover keyword): CUDA-L1 contrastive reinforcement learning reward hacking --limit 8 → 2609.33221, 2609.39533, 2605.12474, 2507.14111, 2609.19101, 2609.00213, 2609.00058, 2607.09492
- F-e15 (orx discover embedding): stronger unit test reward during reinforcement learning for code improves held-out correctness under independent audit; matched compute comparison of reward strictness --published-after 2026-06-01 --limit 15 → 2610.02163, 2610.04011, 2609.32577, 2610.00890, 2610.03984, 2610.03055, 2609.31995, 2609.33875, 2610.04364, 2610.08514, 2609.09133, 2609.32228, 2609.36587, 2609.16604, 2609.32482
- F-P1 (orx paper --full): 2609.22220, 2602.05885, 2609.33074, 2608.12700, 2607.16241, 2509.14279, 2609.00058, 2608.12629, 2606.26453, 2609.36800, 2502.14752, 2606.20128, 2610.05683, 2607.11022, 2606.01066, 2609.35677, 2609.39533, 2606.16062, 2609.01354, 2602.24286, 2608.12635, 2609.21058, 2605.04956, 2607.17979, 2608.24135, 2606.27396, 2607.16228, 2607.04454, 2610.09142, 2608.14527, 2510.17891, 2604.22032, 2507.11948, 2507.05687, 2607.20908, 2604.07666, 2605.02909, 2609.19611, 2607.27231, 2608.01804, 2507.14111
- F-P2 (orx paper (OpenAlex metadata; no full text)): 10.1145/3819802.3820580
- F-V1 (curl export.arxiv.org/abs (submission history)): 2609.22220v1, 2602.05885v2, 2609.33074v1, 2608.12700v2, 2607.16241v1, 2509.14279v1, 2609.00058v1, 2608.12629v1, 2606.26453v2, 2609.36800v1, 2502.14752v1, 2606.20128v2, 2610.05683v1, 2510.17891v2
- F-G1 (GitHub REST commits / HTTP status; Hugging Face datasets API): KernelGYM@3a84417f8c0e (2026-02-06), lethe@eaff0bb6bd6d (2026-08-27), kernel_bench_verified@3fdf6fec7372 (2026-07-13), robust-kbench@078f5bab2993 (2025-11-22), KernelBench@423217d9fda9 (2026-03-05), KernelZero: HTTP 404, gpuemu-corpus: 200, rlvr-leaky-suite: 200, CATCH: 200, KernelBench-M@d04d6fc72504750804c4f4b45b4a8d7dc7c1880d (442 files, 191 witnesses/*.json, no licence)

Kill-shot cell (27 discover queries, 0 failed):

- K-1 (orx discover keyword): kernel correctness checker mutation testing false accept KernelBench → 2609.22220, 2610.05683, 2609.33074, 2609.37322, 2609.33160, 2607.16241, 2608.12635, 2609.30059, 2608.24250, 2610.09142, 2607.01504, 2609.25520, 2608.21157, 2606.26758, 2609.21058
- K-2 (orx discover keyword): Measuring the Checker → 2609.22220, 2609.07667, 2609.33160, 2607.01504, 2609.09250, 2608.24320, 2608.01135, 2605.25988, 2603.28794, 2609.36308
- K-3 (orx discover keyword): Contract-Grade Verifier GPU kernel → 2608.12700, 2610.07541, 2608.21157, 2610.02808, 2608.hawkeye-hardware-aware-gpu-kernel-optimization, 2610.05014, 2608.12629, 2609.33467, 2609.28769, 2606.04847
- K-4 (orx discover keyword): KernelBench-Verified hidden inputs → 2607.16241, 2609.22220, 2609.08149, 2609.21058, 2502.10517, 2610.05683, 2609.17439, 2609.26779, 2609.35475, 2610.01788
- K-5 (orx discover keyword): mutation score Triton kernel mutants verifier → 2609.36800, 2608.12004, 2607.23089, 2609.33160, 2608.26183, 2608.09318, 2607.05149, 2609.22220, 2608.24250, 2610.01799, 2608.12635, 2608.17641, 2609.35841, 2607.18582, 2607.03223
- K-6 (orx discover keyword --published-after 2025-06-01): reward hacking kernel generation correctness check RL → 2609.39533, 2608.17776, 2609.19101, 2609.33221, 2609.28614, 2609.14998, 2609.00058, 2609.35677, 2605.12474, 2608.11669, 2609.00213, 2609.36245, 2610.03055, 2607.09492, 2606.04923
- K-7 (orx discover embedding): Validate GPU kernel correctness checkers of increasing strength (KernelBench allclose check, anti-hacking launch check, hidden-value and shape-variation check) against an independent fp64 oracle audit, measuring each checker's false-accept rate on deterministic mutants of compiler-generated and human-written Triton kernels and its false-reject rate on correct kernels → 2610.05683, 2609.11356, 2610.09142, 2609.29067, 2610.02928, 2609.18123, 2609.33160, 2609.22220, 2608.12700, 2609.08871, 2608.22331, 2607.17979, 2608.16003, 2608.13756, 2608.14527
- K-8 (orx discover embedding): Does training a kernel-generating LLM with RL against a stronger correctness verifier produce more kernels that are correct under independent audit and faster than PyTorch, at matched compute → 2609.33074, 2609.30059, 2609.35140, 2609.12471, 2609.21058, 2608.25061, 2608.25460, 2607.17979, 2602.24286, 2606.29082, 2606.16497, 2606.04847, 2605.31464, 2607.16241, 2607.20501
- K-9 (orx discover openalex): mutation analysis GPU kernel benchmark oracle false negative → 2609.22220, 2608.12629, 10.1002/pro.70334, 10.1145/3783992, 2501.16165, 10.1145/3703920, 2607.12363, 2209.12487, 2606.05570, 2608.11341, 10.1145/3729346, 10.21203/rs.3.rs-10524158/v1, 2605.12673, 10.17877/de290r-7242, 10.3390/books978-3-03936-141-0
- K-10 (orx discover openalex): are mutants a valid substitute for real faults → 10.1145/2635868.2635929, 10.1007/s10664-019-09778-7, 1807.08823, 10.1002/stvr.1509, 2306.02319, 10.5281/zenodo.5053074, 10.1145/2931037.2931039, 1910.11015, 2011.10787, 10.1109/tse.2023.3277564
- K-11 (orx discover keyword): RESOLVE GPU kernels testing reduction proof → 2610.05683, 2609.13585, 2609.28862, 2606.parallel-kernel-bench, 2609.11356, 2610.03226, 2608.21227, parallel-kernel-bench, 2608.17641, 2609.13612
- K-12 (orx discover keyword): cheap verifier good enough erroneous rewards post-training → 2609.33467, 2604.07666, 2610.06432, 2610.02967, 2610.01509, 2607.10474, 2609.29421, 2608.24949, 2609.21208, 2607.05391
- K-13 (orx discover keyword --published-after 2025-01-01): verifier false positive rate RLVR code reward imperfect verifier noise robustness → 2609.35677, 2609.01354, 2607.11022, 2610.02808, 2609.05221, 2609.03241, 2608.20362, 2608.00220, 2609.33662, 2610.06432, 2610.05170, 2607.05391, 2609.06386, 2610.04928, 2609.33467
- K-14 (orx discover keyword --published-after 2025-06-01): KernelBench reward hacking false correctness LLM kernels audit → 2609.19101, 2607.16241, 2609.28614, 2609.39533, 2608.17776, 2609.35677, 2607.05904, 2606.20128, 2609.33221, 2609.11028, 2609.21058, 2608.29460, 2608.30724, 2609.14998, 2605.12474
- K-15 (orx discover keyword): TritonRL training LLMs Triton without cheating robust verification → 2510.17891, 2609.36800, 2609.39102, 2608.12004, 2609.12471, 2608.17641, 2610.00689, 2609.why-are-ai-agents-lying-cheating-and-coordinating, 2608.25061, 2609.33915
- K-16 (orx discover keyword): Dr. Kernel KernelGYM reward hacking lazy optimization → 2602.05885, 2609.33221, 2609.19101, 2609.28614, 2609.39533, 2609.36245, 2608.17776, 2609.14998, 2609.36900, 2608.11669
- K-17 (orx discover keyword): KernelZero correctness-aware GRPO → 2609.33074, 2608.14791, 2608.27351, 2609.21276, 2609.28385, 2609.36932, 2609.21561, 2609.32340, 2608.03467, 2608.22267
- K-18 (orx discover keyword): robust-kbench agentic CUDA kernel benchmarking verification → 2509.14279, 2609.00058, 2602.24286, 2609.34683, 2609.04523, 2608.25124, 2610.00972, 2608.20711, 2603.12440, 2609.12471
- K-19 (orx discover openalex): syntactic versus semantic similarity of artificial and real faults mutation testing → 10.1109/tse.2023.3277564, 2112.14508, 1807.08823, W7161916857, 10.1109/tse.2021.3107634, 10.1016/j.scico.2016.01.003, W7167747163, 10.11591/ijece.v16i4.pp2014-2030, 10.1109/icstw64639.2025.10962508, 10.1109/access.2019.2950171
- K-20 (orx discover embedding): Are artificial program mutants representative of the bugs that large language models make in generated code? Comparing LLM-introduced faults with mutation operators → 2609.10123, 2609.09315, 2609.29410, 2609.35841, 2609.08681, 2607.22880, 2607.05149, 2607.03223, 2606.29088, 2606.05408, 2604.19086, 2603.23443, 2602.15761, 2602.17838, 2601.18949
- K-21 (orx discover keyword --published-after 2025-06-01): TF32 tolerance correctness check matmul kernel benchmark baseline → 2609.22220, 2609.30059, 2607.04454, 2604.22032, 2607.16241, 2610.05014, 2606.jax-bench, 2608.12700, 2608.hawkeye-hardware-aware-gpu-kernel-optimization, 2608.12004
- K-22 (orx discover embedding --published-after 2026-01-01): Measure how often a kernel correctness gate accepts wrong kernels sampled from a language model policy, on-policy false accept rate of verifiers for GPU kernel reinforcement learning → 2610.05458, 2609.35677, 2610.05014, 2609.09250, 2610.02911, 2609.33220, 2609.18123, 2610.00833, 2608.12700, 2609.21058, 2609.10873, 2610.00202, 2609.22220, 2609.05797, 2609.14861
- K-23 (orx discover keyword --published-after 2026-01-01): gate strength matched budget RL kernel correctness hidden-input multi-shape verifier → 2608.12629, 2610.02808, 2605.28751, 2608.12700, 2607.05391, 2609.15404, 2608.13179, 2609.33052, 2610.01069, 2610.04469, 2609.21208, 2610.05014, 2609.02417, 2608.08709, 2610.02828
- K-24 (orx discover openalex): LLM generated GPU kernel correctness verification benchmark → 2605.04956, 2606.20128, 2607.16241, 2608.17379, 2603.02236, 2607.14541, 2609.22220, 2608.05420, 2605.04467, 2608.12700, 2609.21058, 2608.04450, 2605.23215, 10.1609/aaai.v40i34.40155, 10.1145/3839470
- K-25 (orx discover keyword): TF32 tolerance fp64 oracle correctness audit Triton tl.dot → 2608.12700, 2606.20128, 2609.36800, 2609.30059, 2608.12004, 2609.29067, 2609.09702, 2609.37693, 2608.17641, 2609.04663
- K-26 (orx discover embedding): Deterministic mutation operators applied to correct GPU kernels may not represent the errors a language model policy makes; validating a checker on artificial faults may not predict its false-accept rate on model-generated kernels → 2610.10150, 2610.02860, 2609.33220, 2609.33401, 2609.25848, 2609.19844, 2608.12700, 2609.22220, 2609.14861, 2609.09696, 2608.23706, 2608.08709, 2607.12649, 2608.08722, 2608.08266
- K-27 (orx discover keyword --published-after 2026-01-01): hardened tests versus original tests GRPO causal contrast verifier false positives → 2607.11022, 2610.04928, 2609.21208, 2608.27351, 2609.04535, 2610.02808, 2609.28385, 2609.16201, 2610.05170, 2609.03241
- K-P1 (orx paper --full): 2609.22220, 2610.05683, 2606.20128, 2607.11022, 2609.33467, 2604.07666, 2609.35677, 2609.01354, 2608.12700, 2510.17891, 2602.05885, 2607.16241, 2609.08681, 2609.09315, 2609.35841, 2607.04454, 2609.21058, 2609.33074, 2610.03055, 2609.39533
- K-P2 (orx paper (OpenAlex metadata)): 10.1145/2635868.2635929, 10.1109/tse.2023.3277564, 10.1145/3839470, 2607.14541
- K-H1 (read-only host read of job 713's re-pilot journal (S1-cal kernels only; no GPU)): ~/cotcodec-runs/stage0/q1-engineering-d31/runs/713/q1/repilot/journal.jsonl

Cross-domain cell (47 discover queries, 1 failed):

- X-1 (orx discover openalex --limit 8): Is mutation an appropriate tool for testing experiments → 10.1145/1062455.1062530, 10.1109/icse.2005.1553583, 10.1007/s10664-017-9582-5, 10.30630/joiv.6.2-2.1090, 10.1016/j.infsof.2009.04.016, W2243749215, 10.7287/peerj.preprints.2483v1, 10.1002/stvr.1675
- X-2 (orx discover openalex --limit 8): Are mutants a valid substitute for real faults in software testing → 10.1145/2635868.2635929, 10.48550/arxiv.1807.08823, 10.1007/s10664-019-09778-7, 10.48550/arxiv.2306.02319, 10.1145/3383219.3383236, W2468615444, 10.1145/3510003.3510187, 10.1145/3213846.3213875
- X-3 (orx discover openalex --limit 8): trivial compiler equivalence equivalent mutants → 10.5555/2818754.2818867, 10.1109/icse.2015.103, 10.1109/tse.2017.2684805, 10.5281/zenodo.268492, 10.1145/3297280.3297499, 10.1145/3650212.3680310, 10.1109/icstw64639.2025.10962501, 10.1007/978-3-319-68972-2_11
- X-4 (orx discover openalex --limit 8): threats to the validity of mutation-based test assessment subsumed mutants → 10.1145/2931037.2931040, 10.1002/stvr.1667, 10.48550/arxiv.2005.11532, 10.1109/tse.2022.3140510, 10.1016/j.infsof.2009.04.016, 10.5281/zenodo.5750688, 10.1109/ast58925.2023.00008, 10.1145/3368089.3409742
- X-5 (orx discover openalex --limit 8): test oracle assessment and improvement mutation false positives false negatives → 10.1145/2931037.2931062, 10.1145/3213846.3229503, 10.1109/tse.2019.2934409, 10.5281/zenodo.5053420, 10.1145/3449726.3462722, 10.5281/zenodo.5055072, 10.5281/zenodo.5055747, 10.48550/arxiv.2103.02901
- X-6 (orx discover openalex --limit 8): mitigating the effects of flaky tests on mutation testing → 10.1145/3293882.3330568, 10.6084/m9.figshare.8226332, 10.1145/3744916.3773125, 10.1109/icst53961.2022.00034, 10.48550/arxiv.1912.03197, 10.1145/3338906.3338925, 10.48550/arxiv.2504.16777, 10.1145/3468264.3468584
- X-7 (orx discover keyword --limit 12): equivalent mutants mutation score real faults → 2608.09318, 2607.05149, 2609.35841, 2607.03223, 2608.24250, 2605.13279, 2609.37322, 2608.12635, 2609.33160, 2606.26456, 2604.15870, 2606.05499
- X-8 (orx discover embedding --limit 15): Validate correctness checkers for generated code by seeding deterministic single-site mutants into trusted reference programs and measuring how often each checker accepts a mutant that an independent high-precision oracle rejects, and how often it rejects a correct program, with cluster-aware confidence intervals over few independent programs. → 2610.09142, 2610.02928, 2609.33160, 2609.22220, 2608.26746, 2608.19626, 2608.22331, 2607.28271, 2608.17214, 2607.26244, 2607.23002, 2607.05149, 2607.03223, 2606.20128, 2606.26604
- X-9 (orx discover keyword --limit 12 --published-after 2024-06-01): test case quality reinforcement learning code generation false positive rate verifier → 2610.05170, 2609.09135, 2609.03955, 2609.03309, 2608.24135, 2609.34587, 2609.32172, 2607.22471, 2610.04933, 2609.21208, 2607.20852, 2610.05001
- X-10 (orx discover keyword --limit 12): differential testing numerical libraries discrepancies floating-point → 2609.19735, 2609.19352, 2610.04436, 2610.08808, 2609.07492, 2608.11886, 2610.01743, 2608.00085, 2607.12915, 2606.31308, 2605.11546, 2607.27270
- X-11 (orx discover keyword --limit 12): metamorphic testing deep learning compiler → 2610.jevbench-metamorphic-coherence-testing, 2609.19735, 2608.07076, 2609.17007, 2607.25603, 2607.26843, 2610.00255, 2607.04058, 2607.22984, 2606.06056, 2608.07533, 2606.28742
- X-12 (orx discover keyword --limit 12): numerical behavior NVIDIA tensor cores rounding → 2607.06881, 2609.14845, 2609.11356, 2610.rounding-error-in-flashattention-in-pictures, 2610.flashattention-rounding-error-analysis, 2610.09005, 2608.10103, 2609.24519, 2608.06812, 2609.09095, 2608.20725, 2605.17855
- X-13 (orx discover openalex --limit 6): compiler validation via equivalence modulo inputs → 10.1145/2594291.2594334, 10.1145/2666356.2594334, 10.2991/msbda-19.2019.25, W7128648740, 10.1145/2737924.2737986, 10.1145/2813885.2737986
- X-14 (orx discover openalex --limit 6): Finding and understanding bugs in C compilers → 10.1145/1993498.1993532, 10.1145/1993316.1993532, 10.1145/2345156.1993532, 10.1145/2931037.2931074, 10.1109/ase51524.2021.9678776, 10.48550/arxiv.2607.07217
- X-15 (orx discover openalex --limit 6): A new approach to probabilistic rounding error analysis → 10.1137/18m1226312, 10.1137/24m1681458, 10.1137/22m1514817, 10.1137/22m1510819, 10.1093/imanum/draf130, 10.48550/arxiv.2501.14598
- X-16 (orx discover openalex --limit 6): Numerical behavior of NVIDIA tensor cores → 10.7717/peerj-cs.330, 10.7287/peerj-cs.330v0.2/reviews/1, 10.7287/peerj-cs.330v0.2/reviews/2, 10.7287/peerj-cs.330v0.1/reviews/2, 10.7287/peerj-cs.330v0.1/reviews/1, 10.7287/peerj-cs.330v0.1/reviews/3
- X-17 (orx discover openalex --limit 8): diagnostic accuracy imperfect reference standard review of solutions → 10.1016/j.jclinepi.2009.02.005, 10.1016/j.jdent.2018.04.022, 10.3310/hta11500, W2167069878, 10.1371/journal.pone.0012284, 10.1371/journal.pone.0223832, 10.1017/s0950268818001723, 10.1136/bmj.f5605
- X-18 (orx discover openalex --limit 8): comparison of correlated proportions for clustered data → 10.1002/(sici)1097-0258(19980715)17:13%3C1495::aid-sim863%3E3.0.co;2-i, 10.1016/j.jspi.2009.06.005, 10.1371/journal.pone.0007087, 10.1093/bioinformatics/bts595, 10.1197/aemj.9.4.330, 10.1186/1471-2288-13-19, 10.1007/s00357-015-9180-4, 10.1007/s10994-011-5258-3
- X-19 (orx discover openalex --limit 6): Estimating the probability of failure when testing reveals no failures → 10.1109/32.120314, W835915776, 10.1109/12.980013, 10.1155/2015/681232, 10.1016/j.strusafe.2023.102380, 10.1093/humrep/deg488
- X-20 (orx discover openalex --limit 6): How hard does mutation analysis have to be, anyway → 10.1109/issre.2015.7381815, 10.1093/jhered/esac023, 10.48550/arxiv.2212.03075, 10.1109/icse-companion55297.2022.9793738, 10.1111/j.1365-2958.2009.06971.x, 10.1109/tse.2022.3213041
- X-21 (orx discover openalex --limit 6): capture-recapture software inspection defect content estimation → 10.1023/a:1009728205264, 10.1109/issre.1998.730766, W2147925518, 10.1016/s0164-1212(00)00032-7, 10.1109/ccece.2006.277482, 10.1109/tse.2006.1599417
- X-22 (orx discover openalex --limit 6): Evaluating fuzz testing → 10.1145/3243734.3243804, 10.48550/arxiv.1808.09700, 10.48550/arxiv.2607.24577, 10.5281/zenodo.19253442, W2885567964, 10.1109/mines.2012.161
- X-23 (orx discover openalex --limit 5): Bootstrap-based improvements for inference with clustered errors → 10.1162/rest.90.3.414, 10.2139/ssrn.956890, 10.3386/t0344, 10.22004/ag.econ.274640, 10.1016/j.jeconom.2019.04.035
- X-24 (orx discover keyword --limit 8): HardTests synthesizing high-quality test cases LLM coding → 2505.24098, 2605.14445, 2609.30054, 2609.09133, 2609.30233, 2608.18645, 2609.39334, 2610.05001
- X-25 (orx discover keyword --limit 8): CodeContests+ test case generation quality true positive rate true negative rate → 2601.13682, 2506.05817, 2609.29300, 2608.24135, 2610.05001, 2609.12757, 2607.22471, 2609.31795
- X-26 (orx discover openalex --limit 6): a dynamic program analysis to find floating-point accuracy problems shadow → 10.1145/2884781.2884850, 10.4230/dagrep.7.8.74, W2106097038, 10.1109/arith.2016.31, 10.1145/3563322, 10.1145/3151032
- X-27 (orx discover openalex --limit 6): empirical evaluation of mutation operators for deep learning systems statistical killing → 10.5281/zenodo.5053395, 10.5281/zenodo.5082873, 10.5753/reic.2026.8471, 10.48550/arxiv.2301.05651, 10.48550/arxiv.2604.22640, 10.48550/arxiv.2501.09846
- X-28 (orx discover keyword --limit 8): characteristics of code generation errors made by large language models → 2607.13820, 2607.14816, 2406.08731, 2606.19988, 2605.17029, 2606.14113, 2607.05868, 2605.30394
- X-29 (orx discover keyword --limit 10): large language models mutation testing mutants real bugs coupling → 2609.35841, 2607.05149, 2607.03223, 2609.09315, 2608.24250, 2607.21193, 2608.12635, 2609.25520, 2608.09318, 2605.00107
- X-30 (orx discover embedding --limit 12): Choose the floating-point tolerance for checking a GPU kernel's output against a reference from a priori rounding error bounds for dot products and reductions in reduced precision such as TF32, rather than from an empirical multiple of the reference implementation's own error. → 2609.11356, 2610.09089, 2609.39361, 2610.02240, 2609.22220, 2609.00363, 2608.28941, 2608.13756, 2607.18745, 2607.27270, 2606.25453, 2606.06510
- X-31 (orx discover keyword --limit 10 --published-after 2025-01-01): weak test cases reward hacking reinforcement learning code false positives stronger verifier → 2605.12474, 2609.35677, 2609.19101, 2609.39533, 2610.03055, 2609.09135, 2608.24135, 2609.28614, 2607.11022, 2607.09492
- X-32 (orx discover openalex --limit 5): A simple method for the analysis of clustered binary data → 10.2307/2532311, W2186265003, 10.1002/(sici)1097-0258(19990615)18:11%3C1373::aid-sim133%3E3.0.co;2-f, 10.22329/amr.v12i3.658, 10.1371/journal.pone.0151984
- X-33 (orx discover keyword --limit 8): many-core compiler fuzzing OpenCL equivalence modulo inputs GPU → 2609.29311, 2609.11356, 2610.06968, 2607.15762, 2609.36800, 2609.22220, 2609.16389, 2608.11886
- X-34 (orx discover embedding --limit 12): Audit the rigor of benchmark test suites for hardware or code generation by injecting mutations into reference solutions and counting how many mutants pass the official tests. → 2610.09142, 2609.36635, 2610.02928, 2609.35841, 2609.22220, 2608.19626, 2608.12635, 2608.01715, 2608.09318, 2606.26604, 2606.16062, 2604.01518
- X-35 (orx discover keyword --limit 6): flakiness induced by mutation test flimsiness → 2609.24842, 2603.28452, 2610.01891, 2609.35841, 2609.37322, 2609.25528
- X-36 (orx discover keyword --limit 10): floating-point mutation operators numerical programs tolerance oracle equivalent mutants → 2608.09318, 2609.33160, 2609.22220, 2607.05149, 2609.35841, 2605.17437, 2605.13279, 2609.19735, 2609.07492, 2607.03223
- X-37 (orx discover openalex --limit 5): interpreting zero numerators rule of three → 10.1111/anae.12980, 10.6339/jds.2008.06(2).401, 10.1097/ta.0000000000002914, 10.6339/jds.2008.06(3).509, 10.1111/1742-6723.14561
- X-38 (orx discover openalex --limit 5): An empirical comparison of compiler testing techniques → 10.1145/2884781.2884878, 10.1109/issre.2003.1251065, 10.1109/tse.2018.2852744, 10.1145/3133917, 10.1016/j.jss.2021.111174
- X-39 (orx discover keyword --limit 6): NNSmith generating diverse and valid test cases for deep learning compilers → 2207.13066, 2610.06968, 2606.06747, 2511.18918, 2610.04783, 2608.21555
- X-40 (orx discover openalex --limit 4): QUADAS-2 revised tool quality assessment diagnostic accuracy studies → 10.7326/0003-4819-155-8-201110180-00009, 10.3760/cma.j.issn.0254-6450.2018.04.028, 10.3410/f.714797871.790252869, 10.1186/1471-2288-6-9
- X-41 (orx discover embedding --limit 10): Estimate how many faulty program variants every independent checking channel misses by comparing overlaps between several imperfect detectors, as in capture-recapture or latent class models without a gold standard. → 2607.19734, 2607.17061, 2606.01932, 2602.09911, 2511.02977, 2507.17093, 2411.11032, 2307.12365, 2501.15825, 2410.04390
- X-42 (orx discover keyword --limit 10): semantics-preserving transformations kernel equivalence false rejection checker GPU Triton → 2609.11356, 2609.36800, 2608.hawkeye-hardware-aware-gpu-kernel-optimization, 2608.20711, 2608.17641, 2609.33074, 2609.30059, 2609.12471, 2608.12004, 2610.05683
- X-43 (orx discover openalex --limit 5): Investigations of the software testing coupling effect → 10.1145/125489.125473, 10.1145/75308.75324, 10.1145/75309.75324, 10.1016/s0167-6423(03)00022-4, 10.3390/ma14226856
- X-44 (orx discover openalex --limit 5): Is operator-based mutant selection superior to random mutant selection → 10.1145/1806799.1806863, 10.1109/icstw.2019.00037, 10.1007/s10664-019-09778-7, 10.48550/arxiv.2301.12284, 10.48550/arxiv.1803.07901
- X-45 (orx discover openalex --limit 5): theory of composite faults mutation coupling → 10.1109/access.2020.2966582, 10.1155/2019/1564243, 10.3390/s26092914, 10.64972/jaat.2025v3.4, 10.3390/e19110585
- X-46 (orx discover openalex --limit 6): discrepant analysis bias diagnostic test evaluation resolving discordant results → 10.1016/s0140-6736(05)65784-4, 10.3310/hta11500, 10.1016/j.jmoldx.2016.06.008, W7140960881, 10.1016/j.gimo.2026.104171, 10.1097/ede.0b013e31823b5b5b
- X-47 (orx discover openalex --limit 5): If nothing goes wrong, is everything all right? interpreting zero numerators → ERROR: OpenAlex search failed (400 Bad Request)
- X-P1 (orx paper --full (alphaXiv)): 2607.11022, 2609.09315, 2608.12635, 2610.02240, 2609.11356, 2505.24098, 2506.05817, 2406.08731, 2607.23002, 2609.35677, 2609.33160, 2606.01066, 2601.04411, 2604.07666, 2606.16062, 2605.17437, 2606.06747, 2507.17093, 2607.17061, 2607.04058, 2608.17214, 2610.09142, 2610.05683
- X-P2 (orx paper (OpenAlex metadata; 35 calls, 25 records, 10 HTTP 429 retried)): 10.1109/issre.2015.7381815, 10.1145/1062455.1062530, 10.1145/2635868.2635929, 10.1109/icse.2015.103, 10.1145/2931037.2931040, 10.1145/3293882.3330568, 10.1145/2931037.2931062, 10.1002/(sici)1097-0258(19980715)17:13%3C1495::aid-sim863%3E3.0.co;2-i, 10.2307/2532311, 10.1016/j.jclinepi.2009.02.005, 10.1109/32.120314, 10.1162/rest.90.3.414, 10.1137/18m1226312, 10.7717/peerj-cs.330, 10.1145/2594291.2594334, 10.1145/1993498.1993532, 10.1145/2884781.2884878, 10.1145/3744916.3773125, 10.1016/j.infsof.2009.04.016, 10.1145/3243734.3243804, 10.1136/bmj.f5605, 10.1145/125489.125473, 10.1145/1806799.1806863, 10.3310/hta11500, 10.1016/s0140-6736(05)65784-4

Synthesis (7 discover queries, 0 failed):

- S-1 (orx discover embedding --limit 15): Three correctness checkers of increasing strength for GPU kernels (a five-input tolerance comparison against the reference, plus a launch-path check that a compiled kernel actually runs in inference and gradient modes, plus hidden values, shape variation and unaligned remainder shapes at a tighter tolerance) are validated on compiler-generated and human-written Triton kernels and deterministic rule-based mutants of them, against an independent audit no checker sees (float64 oracle with a threshold calibrated from the reference's own float32 error, held-out values and shapes, tolerance-free determinism, aliasing, poisoned-allocation and memory-sanitizer contracts), reporting false accepts on audit-rejected mutants, false rejects on correct kernels and GPU cost per checker before using them as reinforcement-learning rewards → 2610.05683, 2609.11356, 2610.09142, 2609.09250, 2610.07853, 2609.12471, 2610.02928, 2609.33916, 2609.33160, 2608.12700, 2609.22220, 2608.25460, 2609.13311, 2609.02983, 2608.24335
- S-2 (orx discover keyword --limit 10): When the Reward Suite Is Leaky → 2607.11022, 2609.37209, 2609.33136, 2610.01908, 2610.03598, 2609.07211, 2608.30724, 2608.27960, 2608.27109, 2608.09059
- S-3 (orx discover keyword --limit 12 --published-after 2026-01-01): TF32 tolerance fp64 reference relative error near-zero denominator false accept zeros output → 2609.04663, 2609.26550, 2608.12700, 2606.06510, 2608.20607, 2610.01005, 2609.37693, 2609.31291, 2608.25327, 2608.25654, 2609.19758, 2609.09095
- S-4 (orx discover keyword --limit 10): Calibrating the Checksum ABFT bfloat16 false-positive bound → 2610.02240, 2609.16742, 2609.19758, 2609.19743, 2610.02925, 2602.08043, 2608.04035, 2609.19433, 2609.33671, 2609.25581
- S-5 (orx discover openalex --limit 12): mutation testing tolerance-based numerical oracle false acceptance floating point kernels → W7161916857, 10.48550/arxiv.2607.04058, 10.2172/3547206, 10.34726/hss.2016.25320, 10.32657/10356/14803, 10.48550/arxiv.2608.17956, 10.21236/ada610467, 10.48550/arxiv.2608.16409, 10.48550/arxiv.2609.40340, W7131963139
- S-6 (orx discover keyword --limit 10): Oracles That Cannot Fail anchoring expectation moves with the fault → 2608.17214, 2609.24230, 2610.03695, 2607.11342, 2609.08681, 2608.14320, 2608.26272, 2609.01283, 2608.01464, 2610.10490
- S-7 (orx discover embedding --limit 15 --published-after 2026-06-01): Validate a numerical correctness oracle for reduced-precision matrix multiplication and convolution kernels: thresholds derived from the reference's own TF32 error become larger than one, so an all-zeros output passes; choose a cancellation-safe error normalizer → 2610.05683, 2609.14845, 2609.39813, 2609.numerical-representation-invariance-language-models, 2609.39816, 2609.11356, 2610.05488, 2610.06095, 2610.02240, 2610.03321, 2609.38785, 2610.01907, 2610.03228, 2609.33003, 2609.22991
- S-P1 (orx paper --full (read by synthesis before writing the delta rows)): 2602.05885 (sha256 4a2b1e0cf12f48d3), 2606.20128 (sha256 f99a3ed8121d3ddf), 2607.11022 (sha256 2247e419d37cc96d), 2607.16241 (sha256 322c3bc235358ac8), 2608.12700 (sha256 18f9b8f09242a0cf), 2609.09315 (sha256 e2fab7730de5ee10), 2609.22220 (sha256 84c774a9c14e7268), 2610.02240 (sha256 26aa100e26daff85), 2610.05683 (sha256 733ad1d885a39a6d)
- S-H1 (local byte copy of job 713's re-pilot journal (SHA-256 equals the committed record in program/evidence/2026-10-07/q1-engineering-d31/repilot-713.json); no host access by synthesis): ddbfbbf657445d1d7ede759474363a4d8dadc96f86cc3fd0c535830f29796bd2

## Mechanism and Falsifiable Predictions

Mechanism. Why the gates should differ, and why the audit should see what they
miss:

- Gate (a) has four blind spots. Its 1e-2 absolute tolerance hides any error on
  small outputs (tolerance vacuity; C03). Its `torch.rand` inputs lie in
  [0, 1), so sign-dependent faults are invisible. Its shapes are fixed, so
  remainder blocks never execute. It uses only five draws. MtC measured the
  outcome on CUDA: precision faults escape at 78.6%, boundary faults at 22.9%
  (C01).
- Gate (b) adds launch-path evidence: a no-launch decoy, a PyTorch fallback, a
  branch on `self.training` or on the grad mode. AST mutants of kernels that
  still launch are invisible to it by construction.
- Gate (c) adds KBV's magnitude and sign transforms (×3, ×0.01, ×−1), a 1e-3
  tolerance, and shape and remainder configurations. The sign transform
  reaches faults that [0, 1) inputs hide. The shape and remainder
  configurations reach the boundary and index families that constant scalings
  cannot reach by construction (C02).
- The audit adds inputs no gate sees: seven held-out value distributions,
  prime-sized and size-1 held-out shapes, an fp64 oracle with a calibrated
  threshold, and tolerance-free contracts. A4 can witness reads of unwritten or
  out-of-bounds memory, which numerical oracles miss (C04).

Registered predictions (registration section 13; reported, never used to change
a rule):

1. Every S1 substrate refuses `A3/lead1`, so G-strict false-rejects S1 by
   construction.
2. Gate (a) accepts a zeroed or negated L1/23 softmax, while a_1e-3, c and the
   audit reject it. This replicates MtC section 2 on Triton.
3. Liger and tutorial LayerNorm refuse the native L1/40 row.
4. FlagGems relu, gelu, silu and mul read and write out of bounds at
   non-multiple sizes: natural faults.
5. The tutorial matmul fails A1 under strict-fp32 and passes under
   TF32-admissible at native shape.
6. Synchronization is not estimable.
7. G-strict mutant metrics rest on S2 parents only.
8. L1/100's c3 family is vacuous.
9. FlagGems parents of prediction 4 leave every A3-tier filter.

Registered falsifiers (registration 8.2; all required before any Stage 1 work):

1. Criterion 1, fidelity: 100% agreement of a with KernelBench@44130946, of b1
   and b2 with KernelGYM, and of c1 (compatibility mode) with KBV.
2. Criterion 2: the primary audit rejects 0 correct evaluation substrates,
   except adjudicated natural faults.
3. Criterion 3: FRR_independent(c) ≤ 2% with a Clopper-Pearson 95% upper bound
   ≤ 5% on at least 72 units.
4. Criterion 4: no unadjudicated audit hole.
5. Criterion 5: every scheduled control expectation holds in 100% of its cells.
6. Stage 1 rules (registration 12), fixed now: proceed to RL only if
   FA-share(a) − FA-share(c) ≥ 3 pp and FA-share(b) − FA-share(c) ≥ 3 pp with
   non-overlapping intervals and c/b ≤ 2. The decisive negative is FA-share(a)'s
   upper bound below 3 pp, or fewer than 30 audit-rejected kernels among those
   gate (a) accepts.

Kill criteria for the instrument itself (synthesis; not registered; offered to
the owner for any re-registration):

- K-I1, audit non-vacuity. Reject the audit as ground truth on a problem if,
  under the primary policy, T ≥ 1 on any admissible A1-A3 draw. An all-zeros
  output then passes that draw. Observed in job 713 on L2/46, L2/59, L2/77,
  L2/95 and L2/100 (F1). **The registered primary audit is therefore
  falsified as a ground truth on five of the six measured level-2 problems.**
  Stage 0 cannot run as registered without a D14 decision.
- K-I2, independent witnessing. Reject a primary MS difference as a
  gate-strength effect if it vanishes under the c-disjoint tier (A1 and A4,
  which gate (c) does not share). The registration reports c-disjoint, but no
  rule reads it this way.
- K-I3, budget. Reject admission at a given cap if the projection at R's
  bootstrap lower point exceeds that cap through P3. At 8 GPU-h this holds
  already (11.68 central).
- K-I4, ladder informativeness. Report MS_b − MS_a on mutants as uninformative
  by construction (nested ladder, fail-open b1 and b2). Treat gate (b) as
  tested by the control matrix only.

What would change the synthesis verdict: a D14 policy under which T stays
below a stated vacuity bound (for example 0.25) on every admissible draw of the
S1-cal matmul and convolution problems, while the S1-cal TF32 substrates and
identity controls still pass. That is the decisive pilot below.

## Cheapest Decisive Pilot

The decisive test of the registered design has already run at zero additional
GPU cost. It is the synthesis re-analysis of job 713's journal (E4, F1). On
five of six measured level-2 problems the registered primary audit cannot
reject an all-zeros output, so the registered primary mutant metrics are not
interpretable there. No further GPU spend on the registered design is
justified before D14 is revisited.

The cheapest decisive pilot for a repaired design (proposed; it needs the
owner's D14 decision and an allowance, since D31's 0.5 GPU-h holds 0.061):

1. CPU first, no GPU. On the job 713 and 752 journals and on synthetic kernels,
   compute the threshold each candidate policy would give from the stored
   reference errors, where the stored rows suffice. The candidates are:
   - (i) as registered;
   - (ii) strict-fp32 with a TF32 allowance modelled from TF32-rounded inputs:
     an fp64 reference whose matmul and convolution inputs are rounded to a
     10-bit mantissa, as registration finding 18.3.6 proposed, and
     https://arxiv.org/abs/2609.11356 supports;
   - (iii) a cancellation-safe normaliser |x_i − r_i| / (|A||B|-type magnitude
     of position i), after Calibrating the Checksum (https://arxiv.org/abs/2610.02240).
2. One GPU job of at most 0.1 GPU-h on S1-cal kernels only (D28 iv): the 8
   re-pilot problems' substrates, identity controls and mutants, already
   exposed by jobs 713 and 752. It runs A1-A3 under (ii) and (iii) next to the
   registered policy, plus a harness-generated all-zeros wrapper and a negated
   wrapper per problem as new controls.
3. Decision rule, written before the job:
   - Pass if, under the chosen policy, T stays below 0.25 on every admissible
     draw of every matmul and convolution problem.
   - Every S1-cal substrate and identity control must pass A1-A3 under the
     chosen policy; in particular it must accept the PyTorch reference itself
     on L2/77, which strict-fp32 rejects.
   - The all-zeros and negated wrappers must be rejected by A1 on every
     problem.
   - L2/95 `plus2minus` must be rejected by A1 or A2 numerics, not only by A4.
   - Fail: Stage 0's mutant arm is withdrawn on TF32-sensitive problems, and
     Stage 0 reduces to FRR, controls and fidelity on them.

Even with a passing pilot, F2 remains. At the measured cost Stage 0 through P3
needs 11.7-25 GPU-h (central, R's lower point to primary), so admission is a
budget decision only Kevin can make (D24).

## Controls, Baselines, and Ablations

Registered controls (registration 3.4) and their status under trim/2:

- Reference identity (ModelNew = Model) for every in-scope problem: expected
  a accept, b1 and b2 reject, audit_G accept. Scheduled in P1.
- KernelBench adversarial kernels (`result_reuse`, `zero_out`,
  `non_default_stream`, vendored verbatim, D29). Scheduled in P1 and P3. The
  D37 job checked them under the store (E3). Two facts from that job matter
  for any Stage 0 run:
  - The three share `load_inline(name="fast_matmul")` with different sources,
    and trim/2 runs them concurrently in one extension directory. They need
    chaining or a per-item `TORCH_EXTENSIONS_DIR` before their rows can be
    trusted (an owner's execution change).
  - A5 returns `error` on every `load_inline` candidate (PRC-01 and PRC-02
    cannot copy a CUDA extension module).
- Hack-emulating wrappers: decoy, self.training branch, grad-mode split,
  scratch-launch decoy, and the activation-specific kinds. Each kind is
  scheduled on a seeded 15% of in-scope instances. The KBV H.1 controls and
  the five hack-emulating mutants sit on 6.4-8.6 GB problems and are not
  scheduled (registration 18.6 item 2). Gate c1 is therefore never tested
  against an identity shortcut. RESOLVE found natural false accepts of the
  shipped tolerance tests (empty kernels) on two of those same problems,
  L1/31 and L1/32 (C11).

Baselines:

- MtC's published per-family rates (descriptive, registration 8.2 item 6).
- The upstream gates themselves (fidelity, criterion 1).
- Missing comparator, from the frontier cell: an "MtC-suite" gate made of the
  official input plus MtC's released per-problem witness and set-cover inputs.
  Those inputs are problem-level, so they transfer across substrates. MtC
  measured 98.0% detection at two inputs per problem (C02), against gate (c)'s
  roughly 16 configurations per problem (16 on L1/1 in job 752). Its absence is a reviewer-visible gap. Using it
  needs a licence ruling, since KernelBench-M declares none (C05).

Ablations already registered:

- c@1e-3 against c@1e-2 (tolerance against inputs, mirroring MtC's
  decomposition);
- c_kbv_raw (no validity filter);
- the a_head variants and a_static;
- all four audit tiers under both TF32 policies;
- c-disjoint (A1 and A4 only);
- sensitivity analyses without pilot-exposed units.

Additions the cells' evidence supports (each changes the registration, so it
needs a new id or the owner's amendment before the freeze):

1. All-zeros and negated wrapper controls per problem. They test K-I1 directly
   and cost two control kernels per problem.
2. An import-time patch control: a wrapper that replaces a torch op at import.
   Expected a accept and audit reject under the store's clean-process
   reference (cross-domain cell; C19).
3. Same-seed reruns of mutants A4 flags as memory-unsafe. Verdict-unstable
   cells are classed "unknown" and MS is reported with and without them
   (cross-domain cell; Parry et al. 2026, doi 10.1145/3744916.3773125).
4. A real-fault stratum from pre-2025 upstream fix commits (FlagGems, Liger,
   Triton tutorials), to test whether gate rankings on mutants carry over to
   real faults (cross-domain cell; C24, C16). It stays inside D3.

## Evaluation, Statistics, and Leakage Checks

Registered statistics:

- Exact Clopper-Pearson intervals for FRR over kernels and over independent
  units.
- Percentile cluster bootstrap (B = 10,000, seed 0) over problem clusters
  linked by kernel family, for MS, FAR and paired differences.
- Horvitz-Thompson weights (n/k times the frame-to-scored ratio).
- Common kernel set across gates; parent filter; vacuous unrefereeable
  components per problem.
- Replicates 42 (primary), 43 and 44 (robustness).

Defects found by the cells, with the fix each implies:

1. Ground truth (F1): above. Every mutant metric under the primary tier
   inherits it.
2. Nested ladder: MS_b − MS_a is near 0 by construction on mutants (F3).
   Pre-specify it as a check of nesting, not a finding.
3. Degenerate intervals: the paired difference equals hi_only / n ≥ 0. With
   few discordant pairs, the percentile bootstrap collapses to [0, 0] or
   under-covers with fewer than about 30 clusters (C23). Pre-specify an exact
   bound on hi_only at the Rao-Scott effective n, and Obuchowski's clustered
   McNemar for any test. Report the cluster count beside every interval.
4. Criterion 3's operating characteristic at n = 72 with no rejection allowed:
   P(pass) = 0.70, 0.49 and 0.23 at a true FRR of 0.5%, 1% and 2% (C48).
   Registration section 9 states only the n = 110 figures. Under F2 the stop
   leaves at most 63 units (an upper bound of 5.7% at zero rejections), which
   rule D-1 labels under-powered.
5. Discrepant analysis: section 6.7 replays only gate-reject/audit-accept
   disagreements. Precision-only mutants count as witnessed
   (`precision_only_witnessed`). Pre-specify MS without precision-only
   witnessed mutants, and adjudicate a seeded sample of gate-accept/audit-reject
   mutants, so resolution runs in both directions (cross-domain cell).
6. Redundant mutants: report the share killed by every gate, and a sensitivity
   on subsuming mutants from the per-draw kill matrix (C20).
7. Audit and gate (c) dependence: tier G includes A2 and A3, the same kind of
   evidence as c1-c3. That inflates MS_c against MS_a, much like incorporation
   bias in diagnostic-test studies (Rutjes et al. 2007,
   https://doi.org/10.3310/hta11500). Report MS_c − MS_a under c-disjoint
   beside tier G, and read the gap as a dependence estimate (K-I2).
8. Witness-rate ceiling: if Trivial Compiler Equivalence's ratio carried over
   from C and gcc (an untested assumption), about 26% of cubin-distinct mutants
   would be equivalent, capping the witness rate near 0.74 (C21). Unwitnessed
   mutants are reported as surviving the audit, never as equivalent.

Leakage and independence checks:

- D28 exposure. Five evaluation substrates and three test-split mutants were
  scored before the freeze, and gate (c) accepted all five substrates. The
  registered handling: exposed mutants leave every frame, and every primary
  quantity is also reported without exposed units. About 4-5 of criterion 3's
  72 units have known gate-(c) verdicts.
- Audit independence: no gate reads audit inputs or verdicts. The audit is not
  hidden from candidates (registration section 12). That is harmless for
  harness mutants, but Stage 1 needs the hardening first.
- Store semantics: the store's references come from a clean process. For c and
  A1-A5 this is the specification-anchored oracle, which is the stronger audit
  (C19; E3, `result_reuse`). Gate (a) stays inline for fidelity. L2/77's
  nondeterministic cuDNN reference is shared as one realization, which is an
  owner's call.
- Seeds: every draw seed is derived from public constants (registration 4).
  Mutant split and samples are seeded by SHA-256 of fixed strings. There is no
  unseeded randomness.

## Compute and Reproducibility

The gauntlet's own budget (gpu_hours=0.5 in the header) covers reviewer
inference only. The D37 validation job (0.1092 GPU-h) is accounted separately,
under D31's 0.5 GPU-h re-pilot allowance (now 0.439 used). The
research-direction doctor reads the header budget with an integer pattern, so
it parses 0.5 as 0 and reports a non-positive budget. That is a parsing
artifact, not a declared budget of zero. It is recorded and not repaired
(rule 3).

Stage 0 compute ceiling as registered: gpu_hours: 8, the total that
`trim.budget_check` enforces across every Stage 0 job. Spent so far: 1.338
GPU-h (pilot 0.899, re-pilot 0.330, validation 0.109). The projection through
P3 is 19.99 central and 24.66 high (primary row C), and 11.68 / 13.87 at R's
lower bootstrap point (E3). Under the 8 GPU-h stop the run ends inside P1
under rows C, D and E, and only 3% into P2 at R's 2.5% point (F2, an estimate).
Admission at a larger cap is Kevin's ruling (D24).

- Image. The image of record for the current code is the D37 validation image,
  built by CPU-only Slurm 746 from a fresh clean clone of 23a8768, the commit
  whose gate, audit and driver hashes equal registration section 2.1:
  127.0.0.1:5000/cotcodec-q1-gates@sha256:888dbf98cab2ebec4f8f2234727c84f2accb8bb042ec09ead944245be8b7c452
  (image id sha256:28853b9a12fe6bed275155874e4af5e01cffb34ad89f95b8fefd49a4f31f39ff;
  base cotcodec-research@sha256:02965f3d...; torch 2.11.0+cu128, Triton 3.6.0,
  sm_90). A Stage 0 image is built from the frozen revision only, which
  requires a freeze, which requires admission.
- Launch. Every GPU job goes through `scripts/submit_docker_research_job.py`
  (dry-run, test-only, submit) on the H100 host. The validation job's dry-run
  argv, the form a Stage 0 scoring job takes, is
  `sbatch --parsable --partition=research --nodes=1 --ntasks=1 --job-name=q1-exec2-validation --gres=gpu:h100:1 --cpus-per-task=32 --mem=256G --time=00:10:00 --signal=B:USR1@180 --no-requeue infra/slurm/host-single-node/docker-research.sbatch`
  (abridged: the `--output` and `--export` arguments and the clone path of the
  batch script are omitted; the full argv is `compute/validation-752-dry-run.json`
  in the bundle). A
  Stage 0 job uses `experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml`.
  Each refuses to start unless the spent, its own cap and the 1.5 GPU-h
  reserve sum to at most the admitted cap.
- Seeds: seeds: [42, 43, 44] as full-stack scoring replicates (42 primary),
  cap seeds and split seed 42. Every channel seed is derived as in registration
  section 4. The bootstrap uses seed 0.
- Checkpoints and preemption. The journal is append-only. Killed or unstarted
  items rerun in the next job through the lane's resume
  (`resume_from_job_id`). SIGUSR1 180 s before the limit, with a hard deadline
  240 s before the limit. A job that does not end `COMPLETED 0:0` is rerun as a
  new versioned job, and its partial rows are kept and labelled.
- Artifacts. Journals, worker logs and the reference store stay in the host run
  roots. The evidence (summaries, plans, phases, memory records, manifests,
  receipts) is copied to `program/evidence/` with SHA-256 indexes. The corpus
  recipe binds every substrate, mutant and control file.
- Cost ceiling: the admitted cap. No Stage 0 scoring job runs without one.
- Executable evidence:
  - pilot jobs 474, 518 and 548;
  - re-pilot 713;
  - validation 752: COMPLETED 0:0, provenance PASS, GPU prolog exclusive,
    termination `completed`;
  - CPU-only checks in the validation image: plan-only reproduced the
    433-item plan and the card hashes; 38 and 50 Q1 tests passed.

  None of these is an orx experiment node run with the project's single fixed
  run command. They were submitted through the Docker lane's submitter
  directly. Under the gauntlet rule the executable-pilot cap (79) therefore
  still applies.

Known mismatches with the deterministic doctor, recorded and not repaired
(rule 3):

- The doctor validates the compute manifest with
  `scripts/submit_research_job.validate_manifest`, which requires an OCI digest
  in an `image` field. The Docker lane's executed manifest declares `image_id`.
- The doctor's real-model-loop check reads `harness/runner.py`, which does not
  exist. Stage 0 has no model loop at all (`model: {kind: none}`). Its
  executable loop is the gate and audit runner (`harness/q1/runner.py` and
  `harness/q1/worker.py`), which ran in jobs 518, 548, 713 and 752.

## Safety, Data Rights, and Monitorability

- Untrusted code and the R570 driver. Stage 0 runs no model-written kernel on a
  GPU (D3, D7). The corpus is TorchInductor output, pre-2025 human-written
  kernels (FlagGems v1.0, Liger-Kernel v0.3.1, Triton tutorials), and
  deterministic mutants and launcher-level controls derived by reviewed harness
  code. D29 admits as trusted inputs the three KernelBench adversarial kernels
  (vendored verbatim at 423217d9, reviewed) and the unmodified upstream
  fidelity code (KernelBench at both pins, KernelGYM@3a84417f,
  kernel_bench_verified@3fdf6fec), each pinned by hash. Stage 1 scoring of
  policy kernels waits on the R580 upgrade or Kevin's written risk acceptance
  (D2). This proposal changes none of that.
- Isolation. Every GPU step runs in the lane's digest-pinned container through
  Slurm. CPU-only steps run in GPU-less, network-less containers (D12). No new
  Docker network is created (D13). The host is not reconfigured, and no command
  here uses sudo or touches `~/cotcodec`.
- Data rights:
  - KernelBench: MIT, vendored verbatim with SOURCES.json.
  - kernel_bench_verified: MIT, configurations parsed.
  - lethe: MIT, gate semantics reimplemented.
  - FlagGems (Apache-2.0), Liger-Kernel (BSD-2-Clause, with the Unsloth
    Apache-2.0 text) and Triton tutorials (MIT): vendored with licences.
  - KernelGYM: no LICENSE file, so it is reimplemented from a behavioural
    spec (D6). The licence-risk history is in `harness/q1/README.md`, and a
    licence from the authors is Kevin's call (D2).
  - KernelBench-M: no licence; read-only reference, never vendored.
  - Dr. Kernel-8B: no licence (D5; Stage 1 only).
  - drkernel-coldstart-8k: MIT; zero-GPU priors only.
  - The derived image is NGC-based and is never pushed to a public registry.
  - This bundle stores metadata extracts (CC0 for arXiv) and hashes, not full
    texts.
- Public-repository hygiene. The repository is public. No host IP, secret,
  employer material or private dataset is committed. Registry references are
  the loopback 127.0.0.1:5000 private registry, and host run paths are already
  public in the registration.
- Monitorability. Every verdict row carries code hashes. Every job carries
  image, git and source-tree provenance. Exposure ledgers list every kernel
  scored before the freeze. Infrastructure failures and cut items are listed,
  never dropped. F1 itself was found by reading stored per-draw thresholds,
  which is the point of recording them.
- Red lines: none crossed. The `fast_matmul` extension-name collision is an
  integrity hazard (rows could come from another control's library), not a
  safety one. It must be fixed before adversarial rows are trusted.

### Integrity gate (seven AI-research failure modes; ARS ai_research_failure_modes.md not opened, list from the gauntlet rule)

1. Implementation bug passing self-review: possible. The audit metric behaved
   exactly as coded and still produced F1, a design defect that earlier reviews
   recorded only as a convolution limitation on two problems (registration
   18.3.8 and 18.6 item 7; D31). Answered by publishing the threshold table and
   its script.
2. Hallucinated citation: every cited arXiv page has a hashed snapshot.
   Load-bearing priors were re-read by synthesis in full text.
3. Hallucinated result: every in-repo number is traced to a committed record
   or a hashed host file. F1 was recomputed from the hashed journal.
4. Shortcut reliance: the mutant metrics would lean on A4, whose verdicts
   follow allocator history (F1 item 1). Stated, not hidden.
5. Bug reframed as insight: F1 is reported as a defect of the registered
   policy, not as a finding about kernels.
6. Methodology fabrication: no rule is changed here. Proposed changes are
   labelled as proposals, and as data-motivated under D28.
7. Frame-lock: the case against Stage 0 (consumer blocked, mutant arm
   occupied, cost) is argued in "Strategic Fit".

## Negative-Result Value

If Stage 0 ran and its gates barely differed on mutants, that would be
expected (nested ladder, F3) and uninformative about RL. Under F1 a null
mutant difference would be uninterpretable on TF32-sensitive problems. The
negative results that would carry value are:

1. FRR(c) above 2% on correct trusted kernels. A strong gate that rejects
   correct Triton kernels at shape-varied or remainder configurations is a
   reward-noise source in Stage 2, and it is measured nowhere else at this
   scale.
2. A control-matrix failure, for example the launch-path rung missing a decoy
   or c1 accepting an identity shortcut. That would directly inform how the
   field builds kernel rewards (C10, C11).
3. A fidelity disagreement with upstream gates. It would mean published kernel
   RL results rest on a check that differs from its description (D6 already
   records one such difference for KernelGYM).
4. This wave's own negative: under D14's registered TF32-admissible policy, an
   fp64 audit whose threshold scales with the reference's TF32 error cannot
   reject an all-zeros output on most level-2 matmul and convolution problems,
   and strict-fp32 rejects the PyTorch reference. The mechanism is generic to
   an audit whose threshold is a multiple of a TF32 reference's error under a
   relative metric with a small floor. MtC's unrefereeable level-3 problems
   (C03), whose fp32 reference violates the tolerance against fp64, are a
   related phenomenon. It is worth recording whether or not Stage 0 runs.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx (alphaXiv keyword and embedding, OpenAlex) reachable and used by all three cells and by synthesis; cutoff 2026-10-08; degraded coverage recorded in the header (no arXiv API, Semantic Scholar or relay; no OpenReview, publisher full texts, patents or social media); every cited arXiv, GitHub and Hugging Face page snapshotted with HTTP 200 and hashed (bundle snapshots/) | Use the host relay for Semantic Scholar and the arXiv API for forward citations of 2609.22220 and 2606.20128 in any later wave |
| Citation | PASS | Claim registry C01-C48 with locator, date and status. 15 claims verified by synthesis (12 re-read in full text, 3 recomputed from hashed inputs), 5 from committed records or a hashed host file. The rest are CELL_READ, ABSTRACT_ONLY or ESTIMATE and labelled. One cell statement updated (exec/2 bias, after job 752). Structure follows the rule's claim registry; the ARS protocol file was not opened | Independent line-by-line audit; full-text reads of the abstract-only classic priors through library access |
| Novelty | FAIL | No direct prior for the combination (NARROWED), but the mutant arm is OCCUPIED by MtC; no citation-graph expansion; blind discrimination (paragraphs in bundle blind/) and the novelty refuter have not run | Run the blind discrimination on the two paragraphs; expand MtC's and the Correctness Illusion's forward citations; decide whether the MtC-suite comparator belongs on the ladder |
| Design | FAIL | Fatal confound F1: under the registered TF32-admissible policy T ≥ 1 on admissible A1-A3 draws of L2/46, L2/59, L2/77, L2/95 and L2/100 (job 713, hashed journal), so an all-zeros output passes the audit's numerics there, and strict-fp32 rejects the L2/77 reference itself; MS_b − MS_a uninformative by construction; criterion 3 passes with probability 0.49 at 1% FRR | D14 decision first (Kevin), then the decisive S1-cal pilot of "Cheapest Decisive Pilot" (at most 0.1 GPU-h, non-evaluation kernels only, D28 iv), then the statistics additions listed under Evaluation |
| Compute | FAIL | Primary projection through P3 19.99 central / 24.66 high against an 8 GPU-h cap (D37 validation job 752, R = 2.425); the registered stop ends in P1 under the measured scalings (rows C, D, E) and only 3% into P2 at R's 2.5% point (F2, estimate); no frozen Stage 0 image or Stage 0 dry-run exists; executable evidence is from Docker-lane jobs, not orx nodes; the doctor's manifest schema rejects the executed manifest | Kevin's admission ruling at a cap of about 12-25 GPU-h, or an engineering pass that amortises per-process cost (persistent workers per problem) and a re-measurement that reaches the 4-11-unit problems; then freeze, image, dry-run |
| Safety | PASS | D3, D7, D29 and the R570/R580 constraint applied; no model-written kernel on a GPU; licences stated per source; KernelGYM reimplemented (D6); no host address or private data committed; integrity gate answered | Fix the fast_matmul extension collision before adversarial rows are trusted; licence ruling before any use of KernelBench-M suites |

Deterministic doctor (`uv run python scripts/research_direction_doctor.py program/proposals/2026-10-08-q1-stage0-gate-validation.md`),
output verbatim from the run on this file and its bundle:

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
    "repository real model loop is still a stub",
    "compute manifest is invalid: image must contain a full immutable OCI digest",
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 3 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-q1/program/proposals/2026-10-08-q1-stage0-gate-validation.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 43,
    "recognizedPrimaryUrls": 36
  },
  "status": "FAIL"
}
```

## Independent Adversarial Reviews

Reviewer A: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Reviewer B: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Wave 1 has produced only the synthesis. The loop's order is blind
closest-prior discrimination, then the refute-first triad, then two
provider-distinct reviewers. None has run. Even when they do, no review can
count toward a 100:

- That needs Ed25519-signed receipts whose keys come from an external trust
  store pinned by protected CI. That store does not exist, and only Kevin can
  set it up (D24).
- D23 records that no OpenAI key is available and that the Moonshot account is
  suspended. A second provider would therefore be self-hosted open-weight
  inference inside the declared 0.5 GPU-h, as in the K1 v2 gauntlet
  (Qwen3.6-35B-A3B, D26).

**The signed-review requirement fails here, and will keep failing until the
trust store exists.**

The accepted score is capped:

- at 89 by the missing independent review;
- at 79 by the missing executable orx pilot;
- at 74 until novelty coverage and the blind discrimination are complete.

The rule's reject list names direct-prior match, fatal leakage and safety red
lines. F1 is none of these: it is a fatal identification defect of the
registered primary metrics. In the synthesis owner's judgement it should be
treated as reject-class for the registered design until D14 is revisited. The
reviewers decide that.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | Not yet reviewed in wave 1 (0 means unreviewed). Synthesis notes: lead question, but its only consumer is blocked (R580, licence) and needs a hardened worker |
| Primary-source evidence | 0 | 0 | Not yet reviewed. Synthesis notes: 48-claim registry; 9 closest priors re-read in full; F1 recomputed from the hashed journal |
| Defensible novelty delta | 0 | 0 | Not yet reviewed. Synthesis notes: NARROWED; mutant arm occupied by MtC; delta is FRR, controls, ladder, audit, cost |
| Mechanism and falsifiability | 0 | 0 | Not yet reviewed. Synthesis notes: registered falsifiers exist; F1 falsifies the primary audit as ground truth on five of six measured L2 problems |
| Controls and causal identification | 0 | 0 | Not yet reviewed. Synthesis notes: nested ladder; KBV H.1 controls unscheduled; audit and gate (c) dependence |
| Evaluation and statistics | 0 | 0 | Not yet reviewed. Synthesis notes: criterion 3 operating characteristic 0.49 at 1%; degenerate paired intervals; one-directional adjudication |
| Feasibility and information per GPU-hour | 0 | 0 | Not yet reviewed. Synthesis notes: 19.99 / 24.66 GPU-h through P3; stop ends in P1; about 1/48 of MtC's mutants at similar cost |
| Reproducibility and artifact contract | 0 | 0 | Not yet reviewed. Synthesis notes: version card, exposure ledgers and plan hashes are strong; no frozen image; no orx node |
| Safety, data rights, and monitorability | 0 | 0 | Not yet reviewed. Synthesis notes: D3, D7 and D29 respected; fast_matmul collision open |
| Independent adversarial review quality | 0 | 0 | No review exists; no trust store (D24) |
| **Total** | **0** | **0** | Unreviewed. Caps 74, 79 and 89 apply; F1 is a reject-class defect for the registered primary metrics until D14 is revisited |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 (unreviewed) | F1. Under D14's registered TF32-admissible policy the audit's threshold reaches 1-13 on five of six measured level-2 problems. An all-zeros output then passes A1-A3 there, and the audit-hole replay would book real-fault catches as false rejections. Second: F2, cost (stop in P1 at the measured R). Third: F3, mutant arm occupied by MtC | Proposal written from the draft registration, the D37 validation job and three discovery cells merged by mechanism. The kill-shot's F1 was verified by synthesis on the hashed job 713 journal. Its exec/2 statement was updated after job 752. Registration not edited | Pending blind discrimination, refute-first triad and reviewers. 136 of 150 discover queries used. D24 caps the gauntlet at an honest exit below 100. Recommended single fix for wave 2: the D14 decision and the S1-cal threshold pilot |

The evidence bundle `evidence/2026-10-08-q1-stage0-gate-validation/bundle.json`
holds the following, each hashed:

- source snapshots of every cited arXiv, GitHub and Hugging Face page;
- the query log;
- six doctor records;
- the compute record: copies of the D37 validation job's image receipt,
  manifest, dry-run, test-only, provenance, Slurm record, lane files and
  analysis, with the Stage 0 job's own attestations marked not run;
- the synthesis analyses (threshold check, stop-point estimate) with their
  scripts;
- the two anonymized mechanism paragraphs;
- the deterministic doctor's output.

It holds no review receipts and no audit JSONL row. The wave-1 row is appended
to `program/gauntlet/` after the reviewers score, so that the hash-chained score
is a reviewer score and not a placeholder.
