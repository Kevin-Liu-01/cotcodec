# q1-stage0-mutant-corpus (DRAFT, not frozen)

Status: draft for the program owner's review, 2026-10-07. Not frozen. No
mutant or control has been scored, and no confirmatory data exists. The only
executions so far are infrastructure validation: CPU unit tests, and
sm_90 compiles of toy kernels in a GPU-less container (no launch).

## Experiment

- **Id:** `q1-stage0-mutant-corpus`.
- **Question:** Q1 Stage 0, component of the gate validation. Build the
  deterministic mutant corpus and the hack-emulating positive controls on which
  `q1-stage0-gate-validation` measures gate strength. Fix every rule that
  decides which mutants exist, which are scored and how they are weighted
  before any mutant is scored, and state how the corpus itself is validated.
- **Division of authority:** `q1-stage0-gate-validation` (core owner) defines
  the gates, the audit, the witness rule, MS, FAR, FRR and the Stage 1 rules.
  This document defines corpus construction, corpus-level metrics and control
  acceptance. Where both speak (the witness rule), the gate-validation
  document governs.
- **References:** `program/questions/q1-kernel-gate-strength.md`; the reviewed
  Q1 plan (q1-gate-stack, sections 7(iii) and 7(iv)); decisions D3, D5-D7,
  D12-D14 in `program/decisions.md`.

## Code, data and environment

- **Code:** `harness/q1/mutate/` and `scripts/q1_generate_mutants.py`,
  `scripts/q1_record_specializations.py` on branch `stage0/q1-mutate`. Every
  corpus manifest records `package_sha256` (SHA-256 over the package's
  sources) and the operator `registry_fingerprint`; a corpus whose values
  differ from the frozen commit's is not admissible. At this draft:
  68 operators, registry fingerprint
  `43a1f0a234ad1c4a4421626d740989e01890b878c5ce7f2dec5739e3d43922a6`.
- **Shared schema:** `harness/q1/schema.py`, `q1-schema/1`, SHA-256
  `c9bae9d502f7b9c83332f95e24fd9934d91bfe6cede47de527f6d584838b3256`.
- **Substrates:** exactly the substrates the substrate owner admits: S1
  (TorchInductor, dynamic shapes, normalized to plain JIT launches) and S2
  (FlagGems v1.0-manual `18b8e428`, Liger-Kernel v0.3.1 `1520999e`, Triton
  tutorials `105cb564`). S3 (agent-written) is excluded (D3). Problems come
  from KernelBench `423217d9fda91e0c2d67e4a43bf62f96f6d104f1`.
- **Environment:** research image `cotcodec-research:f10a8571-architecture`
  (`sha256:65feae8f044a98303b862fe9bf4b0fefceae8bec356b473a2fff70f8949e34e6`),
  Triton 3.6.0, torch 2.11.0+cu128, compile target sm_90. Enumeration, the
  compile filter and selection run without a GPU; the compile filter runs in a
  GPU-less container (no `/dev/nvidia*`).
- **Reference only:** KernelBench-M `d04d6fc72504750804c4f4b45b4a8d7dc7c1880d`
  (no licence; read, never vendored).

## Corpus construction (frozen rules)

1. **Enumeration.** Each of the 68 operators is applied to every scope of
   each substrate's `kernel.py`: the body of every `@triton.jit` function and
   the launch code. Each candidate changes one site (the paper rule
   `acc-fp16` changes an accumulator's declaration and its updates together).
   Order is fixed: registry (schema family) order, then jit functions in source
   order and the launch scope, then position. Enumeration uses no randomness.
2. **CPU dedup.** A candidate must parse. Its `dedup_hash` is the SHA-256 of
   its normalized AST (formatting, comments, docstrings removed). Candidates
   equal to the parent are dropped as equivalent; a later candidate equal to an
   earlier one is dropped as a duplicate and recorded with the operator that
   kept it.
3. **Specialization record.** One native forward pass of each *parent*
   substrate (KernelBench `get_init_inputs`/`get_inputs`, seed 42, tensors
   created on the GPU with the problem's dtypes) runs under Triton's
   `knobs.runtime.jit_post_compile_hook`, which records Triton's serialized
   specialization of every kernel compiled, including every autotune
   configuration. Input values do not enter a specialization. No mutant runs
   in this step.
4. **Compile filter.** Each parent and candidate is compiled at every recorded
   specialization with `TRITON_DISABLE_LINE_INFO=1`, target sm_90, in a
   GPU-less container. A candidate is `compile-fail` (Triton error, more than
   600 s for one kernel, or no result after two isolated retries following a
   crashed batch), `equivalent-to-parent` (same cubin SHA-256 at every recorded
   specialization and the same launch-scope AST), `duplicate` (same as an
   earlier candidate) or `distinct`. Mutations confined to a kernel the parent
   never launches are therefore equivalent. If any parent fails to compile, the
   corpus is not built.
5. **Cap.** At most 40 distinct mutants per substrate. Slots go to families
   by water-filling (equal shares, capped by availability, unused slots
   redistributed equally, leftovers to the largest remaining availability,
   ties by schema family order), then to operators within a family the same
   way (ties by operator name), then
   to a simple random sample inside each operator stratum drawn with
   `random.Random` seeded from
   `sha256("q1-mutant-cap/42/{substrate_id}/{family}/{operator}")` over the
   stratum sorted by `dedup_hash`. Each kept mutant records its stratum sizes,
   inclusion probability `k/n` and weight `n/k`.
6. **Split.** A kept mutant is `dev` if the first byte of
   `sha256("q1-mutant-split/v1/seed=42/{substrate_id}/{dedup_hash}")` is even,
   else `test`. This mirrors the paper's per-problem id-hash holdout. A
   secondary problem-level split applies the same rule to
   `sha256("q1-problem-split/v1/seed=42/{problem_id}")`. Both splits use seed
   42 whatever cap seed drew the sample. The c-lite set cover
   (gate-validation) selects on `dev` only; every primary metric below is on
   `test`.
7. **Controls.** For every admitted substrate, the applicable wrapper controls
   below are generated; hack-emulating mutant controls are copies of kept
   mutants matching the listed (problem, operator) pairs. Controls never enter
   mutant or FRR denominators.

### Controls and their by-construction expectations

Expectations assume the parent passed admission (gates a, b, c and the
audit). Gate identifiers are `harness/q1/schema.py` `KNOWN_GATES`.

| Control | Emulates | Applies to | Expected verdicts |
|---|---|---|---|
| decoy-defined-unused | Dr. Kernel (2602.05885) Fig. 2 decoy | every substrate | a accept; b1, b, c reject; A1 accept |
| self-training-branch | Dr. Kernel Fig. 2, branch on self.training | every substrate | a accept; b1, b, c reject; A1 accept |
| grad-mode-split | KernelGYM's two grad modes | every substrate | a accept; b1, b, c reject; A1 accept |
| scratch-launch-decoy | launch-presence heuristics | every substrate | a, b1, b2, b, A1 accept |
| kbv-h1-identity-shortcut | KBV (2607.16241) App. H.1 | L1/19, 20, 31, 32 | a accept; b1, b, c1, c, audit_N reject |
| kbv-h1-identity-shortcut-launch | KBV H.1 plus a decoy launch | L1/19, 20, 31, 32 | a, b1, b accept; c1, c, audit_N reject |
| shape-locked-silent | lethe shape_specific; KBV App. L | 13 L1 elementwise activations | a, b, audit_N accept; c2, c, A3, audit_G reject |
| shape-locked-refusal | D14 refusal | same 13 | a, b, audit_N accept; A3 refuse; audit_G_strict reject |
| cached-output | lethe returns_cached | same 13 | a, b, c reject |
| in-place-input-write | lethe buffer_aliasing | same 13 | a, b accept; A4, audit_N reject |
| ReLU removal mutant | KBV H.1 analogue | L1/19 | a, b accept; c1, c, audit_N reject |
| abs removal mutant | invisible on rand inputs | L1/30, L1/38 | a, b accept; c1, c, audit_N reject |
| upper-clamp removal mutant | invisible on rand inputs | L1/32 | a, b accept; c1, c, audit_N reject |
| lower-clamp removal mutant | below -1 only | L1/32 | a, b, c accept; audit_N reject |

The 13 activations are L1/19, 20, 21, 22, 25, 26, 27, 28, 29, 30, 31, 32
and 88, each with a single `torch.rand` input (checked statically).

## Metrics

Corpus metrics (no GPU; unit = candidate mutant):

- **C1 yield:** CPU-distinct candidates per substrate, family and operator;
  rejections by reason (syntax, equivalent, duplicate).
- **C2 compile filter:** fractions compile-fail (by error kind),
  equivalent-to-parent and duplicate, per family and operator.
- **C3 selection:** kept mutants per family; the share of substrates on which
  every family present in the pool is kept; the distribution of weights.
- **C4 split balance:** `dev` share overall and per family.

Scored metrics (from the gate-validation verdict rows; unit = kept mutant;
`test` half unless stated):

- **W1 witness rate** per family: the share of kept mutants the primary audit
  (tier G, TF32-admissible) rejects on at least one validity-gated input.
  Unwitnessed mutants are quarantined: counted, excluded from W2-W4.
- **W2 miss rate** `FAR_g` per family for gates a, b and c (definition from
  gate-validation), unweighted and weighted by `n/k` (the uncapped natural
  mix), with 95% problem-cluster bootstrap intervals (B = 10,000, seed 0).
- **W3 paper comparison:** `FAR_a` per family beside 2609.22220 Table 2
  (arithmetic 8.7%, indexing 14.4%, semantic 14.9%, boundary 22.9%,
  synchronization 27.8%, precision 78.6%, all 16.9%). Descriptive only; no
  threshold, because the language, substrates and rule port differ.
- **W4 origin split:** W2 separately for `paper` operators and for the 4
  `triton-only` operators.
- **K controls:** the verdict of every control for every gate in its
  `expected` map, at each scoring replicate (input seeds 42, 43, 44).

## Acceptance rules (all required before the corpus is used for Stage 0 results)

1. **Determinism.** Two independent runs of pool, compile and select from the
   same substrates, records and code produce byte-identical `mutants.jsonl` and
   `manifest.json`, and the same set of `compile.jsonl` rows.
2. **Compile-filter sanity, on the production image.** Every parent compiles;
   compiling each parent twice gives identical cubin hashes; on the toy probe,
   a reformatted kernel and a flipped comparison hash equal to the parent while
   `<` to `<=` and ReLU removal do not.
3. **Controls.** Every expectation holds in 100% of control x gate x seed
   cells. A mismatch blocks Stage 0 results until it is classified as a gate or
   audit bug (fixed in a new gate version and rerun), a control bug (fixed in a
   new control version and rerun) or a false premise (the expectation is
   withdrawn in a new preregistration id, never by editing this file).
4. **Coverage.** At least 5 of the 6 families have at least 30 witnessed
   `test` mutants. A family below 30 is reported with its counts and
   intervals and marked "not estimable"; it does not fail the corpus.
   Synchronization is expected to be small, since Triton exposes only
   `tl.debug_barrier` and atomics.
5. **Power label.** If fewer than 300 witnessed `test` mutants exist in total,
   every W metric is labelled under-powered.

## Seeds, sample size and detectable effects

- **Seeds.** The cap seed is 42 for the primary corpus. Seeds 43 and 44 draw
  alternate cap samples on the CPU only; their family composition and overlap
  with seed 42 (Jaccard index per substrate) are always reported. The
  mutants that only seed 43 or 44 select are scored on the GPU only if the
  gate-validation pilot cost card projects the Stage 0 total, including them,
  at or below 8 GPU-h; otherwise they are reported as not scored. Scoring
  replicates use input seeds 42, 43 and 44 per gate-validation.
- **Size.** At most 40 kept mutants per admitted substrate (at most about
  8,400 for about 210 substrates), about half in `test`. The paper witnessed
  89.5% of its distinct mutants (7,384 of 8,253); our witness rate is unknown
  until scoring.
- **Precision.** For a family with `n` witnessed `test` mutants, a miss rate
  near 0.2 and a problem-cluster design effect of 2, the 95% half-width is
  about 11.1 points at `n = 100`, 6.4 at 300 and 3.5 at 1,000. The design
  effect is estimated from the data and reported.
- **Detectable difference.** Gates are nested, so `MS_c - MS_a` is a
  one-directional paired difference with variance about `d / n`. With 80%
  power at two-sided alpha 0.05 and design effect 2, the smallest detectable
  difference is about `7.84 x 2 / n`: 5.2 points at `n = 300` and 1.6 points
  at `n = 1,000`.

## Infrastructure failures and exclusions

- **Compile filter.** Compile errors, per-kernel timeouts and crashes that
  persist through two isolated retries are properties of the mutant
  (`compile-fail`), reported per operator, never infrastructure failures. A
  parent that fails to compile stops the build; the substrate owner fixes or
  withdraws the substrate in their own manifest.
- **Specialization record.** A recording job that does not end `COMPLETED`
  with exit 0, or logs an Xid, is rerun as a whole; partial records are never
  used.
- **Scoring.** Infrastructure failures during scoring follow
  gate-validation. A kept mutant whose every attempt fails for infrastructure
  reasons is excluded from all denominators and counted per family.
- No other exclusion exists. A kept mutant is never removed after selection
  for any other reason.

## Always reported

Counts at every filter per substrate, family and operator; every rejected
candidate with its reason; the KernelBench-M mapping (127 rules: 62 ported,
43 subsumed, 22 not applicable) and the 4 Triton-only operators; selection and
split tables; the seed 43 and 44 sensitivity; every control cell; W1-W4 with
intervals, weighted and unweighted; under-powered and not-estimable labels;
every deviation from this document with its reason. A family where gate a
misses nothing, a control that fails, or a corpus that fails acceptance is
reported as such.

## Design decisions

Made by the mutator owner where the reviewed plan left a choice open. Each is
flagged for the program owner's review before the freeze.

1. **Mutant-level split as primary.** It matches the paper's holdout, so the
   held-out c-lite number is comparable. The problem-level split is reported as
   a stricter secondary, because mutants of one substrate share code.
2. **Equal family shares with exact weights**, not proportional allocation.
   Per-family miss rates are the paper's central result and the rare families
   (precision, synchronization) would otherwise get almost no slots; the
   `n/k` weights recover the natural mix for pooled rates.
3. **Cap after the compile filter**, so 40 means 40 compilable,
   compile-distinct mutants per substrate.
4. **Compiled dedup by CPU replay** of parent specializations instead of
   launching mutants: no mutant runs on a GPU before scoring, and the check
   works in a GPU-less container. It covers the native specialization only.
5. **Controls as launcher-level wrappers** of admitted substrates, with no new
   Triton code, to stay inside D3. Authored Triton fixtures (lethe classes,
   KBV L.3.x) wait for a ruling.
6. **Paper-faithful AOR on pointer arithmetic.** The paper's arithmetic rules
   apply to every binary operator in device code; the port does the same, and
   the compile filter and witness rule remove the invalid or equivalent ones.
7. **Three loader-inactive KernelBench-M rules are ported** (`argmin-tie-last`,
   `argmax-seed-from-second` via `loop-start-1`, `elementwise-guard-plus1`);
   they are shadowed in KernelBench-M only because their CUDA regex equals an
   earlier rule's.
8. **`kernelbench_m_rule` names the nearest paper rule** for generalised ports
   (for example a `0.5` literal in GELU is perturbed under
   `hardsigmoid-slope-perturb`); `rule_origin` stays `paper` because the
   paper's family B (approximation constants) covers it.
9. **Seeds 43 and 44 are cap-sampling seeds**, scored only within the 8 GPU-h
   Stage 0 cap, so the seed requirement does not inflate GPU cost.
