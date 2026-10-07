# Q1 mutator (`harness/q1/mutate/`)

Deterministic mutants of admitted Triton substrates, and hack-emulating
positive controls, for the Q1 Stage 0 gate validation. The mutation taxonomy
ports *Measuring the Checker* (arXiv 2609.22220) from CUDA to Triton, using
the released KernelBench-M rules as a read-only behavioural reference.

Owner: Q1 mutator component (`stage0/q1-mutate`). Shared interfaces live in
`harness/q1/schema.py` (core owner; copied verbatim).

## Pipeline

```
substrates/ ──pool──> pool/ ──compile (GPU-less container)──> pool/compile.jsonl
                         └──────────────select (cap 40, split)──────────> mutants/
substrates/ + KernelBench@423217d9 ──controls──> controls-hacks/
parent substrates ──q1_record_specializations.py (1 GPU)──> specializations/
```

```bash
uv run python scripts/q1_generate_mutants.py pool --substrates-root S --pool-root P
python scripts/q1_generate_mutants.py compile --pool-root P --specializations-root R  # container
uv run python scripts/q1_generate_mutants.py select --pool-root P --substrates-root S \
    --out-root M --controls-root MC --seed 42 --cap 40
uv run python scripts/q1_generate_mutants.py controls --substrates-root S \
    --out-root C   # problems: vendored KernelBench@423217d9 unless --kernelbench-root
uv run python scripts/q1_generate_mutants.py table operators   # or: table rules
```

Every step refuses to overwrite its output, writes into a temporary sibling
and renames it into place only on success. Without `compile.jsonl`, `select`
refuses unless `--no-require-compile` is passed; the manifest then records
`compile_checked: false` and the corpus is a preview, not the scored corpus.

## How a mutant is made

- **Parsing.** `kernel.py` is parsed with Python's `ast`. Device scope is the
  body of each `@triton.jit` function (decorators excluded); launch scope is
  the rest of the module minus imports. Callee names are canonicalised through
  the module's imports (`tl.*`, `libdevice.*`, Inductor's `triton_helpers.*`
  and `tl_math`).
- **Edits.** An operator yields candidates: one or more span replacements
  anchored at one site. Only the replaced spans change; the rest of the file is
  byte-identical to the parent. The reported site is `kernel.py:line:col`
  (1-based line, 0-based character column of the anchor node).
- **Order and determinism.** Operators run in registry order (schema family
  order); within an operator, jit functions in source order, then the launch
  scope; within a scope, candidates by position. The same source and registry
  always give the same mutants, ids and hashes. There is no randomness in
  enumeration.
- **CPU dedup.** Each mutant must parse; its `dedup_hash` is the SHA-256 of its
  normalized AST (formatting, comments and docstrings removed). Mutants equal
  to the parent are dropped as equivalent; later duplicates are dropped and
  recorded with the operator that kept the mutant.
- **Compiled dedup (the GPU hook).** `compiled.record_specializations` uses
  Triton's `knobs.runtime.jit_post_compile_hook` to record, during one native
  forward pass of each *parent* substrate, Triton's own serialized
  specialization of every kernel compiled. `compiled.compile_hashes` replays
  those specializations for every candidate in a GPU-less container with
  `TRITON_DISABLE_LINE_INFO=1` and hashes the sm_90 cubins. A candidate whose
  cubins and launch code equal the parent's is equivalent; equal to an earlier
  candidate's is a duplicate; a compile error is a compile failure. Triton
  3.6.0 compiles for sm_90 with no device present (checked in a GPU-less
  container on fal-h100-01: a reformatted kernel and a flipped comparison hash
  equal to the parent, `<` to `<=` and a ReLU removal do not).
- **Cap.** At most 40 mutants per substrate. Families get equal shares by
  water-filling (a family with fewer mutants keeps all of them and its unused
  slots are redistributed), then operators within a family the same way, then
  a seeded simple random sample inside each operator stratum. Each kept mutant
  records `n_operator_stratum`, `k_operator_stratum`, its exact inclusion
  probability `k/n` and Horvitz-Thompson weight `n/k`, so pooled rates can be
  reweighted to the natural mutant mix.
- **Split.** `dev` or `test` from one bit of
  `sha256("q1-mutant-split/v1/seed=42/<substrate_id>/<dedup_hash>")`, the
  analogue of the paper's per-problem id-hash holdout. The assignment depends
  only on the mutant's content and the declared seed. A secondary
  problem-level split uses the same construction on `problem_id`.
- **Seed.** `mutation.json.seed` is the cap-sampling seed (42 for the primary
  corpus; 43 and 44 draw alternate samples). Enumeration does not use the RNG,
  and the split is frozen at seed 42 for every cap seed, so a mutant has the
  same half in every sample.

## Outputs other components read

- `mutants/<mutant_id>/{kernel.py, substrate.json, mutation.json}`: the shared
  mutant layout. `substrate.json` is the parent's file copied byte for byte.
  `mutation.json` carries the required keys plus `rule_origin`
  (`paper`/`triton-only`), `kernelbench_m_rule` (the nearest paper rule) and
  `description`.
- `mutants/mutants.jsonl`: one row per kept mutant with `split`,
  `problem_split`, `compiled_key`, stratum sizes, inclusion probability and
  weight.
- `mutants/manifest.json`: mutator identity (`package_sha256` over this
  package's sources, `registry_fingerprint`), seed, cap, split version,
  `compile_checked`, the pool, compile and mutant-list hashes, and
  per-substrate counts at every filter.
- `pool/pool_manifest.json`: every rejected candidate with its reason
  (`syntax`, `equivalent-to-parent`, `duplicate` with `duplicate_of`).
- `specializations/<substrate_id>/specializations.json`
  (`q1-triton-specializations/1`): Triton 3.6's serialized specialization per
  recorded compile.
- Controls: `<control_id>/{kernel.py, control.json}` with
  `control_kind: hack-emulating-mutant` and by-construction `expected`
  verdicts.

## Hack-emulating controls

Controls are launcher-level wrappers around an admitted substrate. The
substrate's Triton code is kept unchanged (its `ModelNew` is renamed
`_Q1SubstrateModelNew`) and the KernelBench reference is embedded verbatim, so
no new Triton kernel is written (decision D3). Constructor RNG is forked so
the substrate's parameters equal a standalone substrate's and the global RNG
state after construction is the substrate's.

| Kind | Emulates | Applies to | Expected (by construction) |
|---|---|---|---|
| `decoy-defined-unused` | Dr. Kernel Fig. 2: kernel defined, never called | any | a accept; b1, b, c reject; A1 accept |
| `self-training-branch` | Dr. Kernel Fig. 2: branch on `self.training` | any | a accept; b1, b, c reject; A1 accept |
| `grad-mode-split` | KernelGYM's two grad modes | any | a accept; b1, b, c reject; A1 accept |
| `scratch-launch-decoy` | launch-presence heuristics | any | a, b1, b2, b, A1 accept (b's blind spot) |
| `kbv-h1-identity-shortcut` | KBV App. H.1 | ReLU, LeakyReLU, ELU, HardTanh | a accept; b1, b, c1, c, audit_N reject |
| `kbv-h1-identity-shortcut-launch` | KBV H.1 plus a decoy launch | same | a, b1, b accept; c1, c, audit_N reject |
| `shape-locked-silent` | lethe `shape_specific`, KBV App. L | elementwise activations | a, b, audit_N accept; c2, c, A3, audit_G reject |
| `shape-locked-refusal` | D14 refusal | elementwise activations | a, b, audit_N accept; A3 refuse; audit_G_strict reject |
| `cached-output` | lethe `returns_cached`, KernelBench result reuse | elementwise activations | a, b, c reject |
| `call-count-switch` | KernelGYM call history (b1 runs after b0's five calls; added in the integration fix pass) | elementwise activations | a, A1 accept; b1, b, c reject |
| `in-place-input-write` | lethe `buffer_aliasing` | elementwise activations | a, b accept; A4, audit_N reject |

Hack-emulating mutants (from `select --controls-root`): ReLU removal on
L1/19, `abs` removal on L1/30 and L1/38 and upper-clamp removal on L1/32 are
exact on `torch.rand` inputs (a and b accept, c1 and the audit reject); lower
clamp removal on L1/32 differs only below -1, which no gate-c distribution
reaches, so c accepts and only the audit rejects.

## Operators

68 operators: 64 ports of KernelBench-M rules (`paper`) and 4 Triton-only
extensions. Generated by `rules.operator_markdown()`; a test keeps it current.

<!-- q1-mutate:operators start -->
| Operator | Family | Origin | KernelBench-M rule | Also covers | Scope | What it does |
|---|---|---|---|---|---|---|
| `plus2minus` | arithmetic | paper | `plus2minus` |  | device | AOR: one binary + in device code becomes -. |
| `minus2plus` | arithmetic | paper | `minus2plus` |  | device | AOR: one binary - in device code becomes +. |
| `mul2div` | arithmetic | paper | `mul2div` |  | device | AOR: one binary * becomes / (ill-typed integer sites fail the compile filter). |
| `mul2plus` | arithmetic | paper | `mul2plus` |  | device | AOR: one binary * becomes +. |
| `negate-store` | arithmetic | paper | `negate-store` |  | device | UOI: the value written by one tl.store is negated. The paper rule negates a stored exp() expression; Triton stores are explicit, so the port negates the stored value at each tl.store site. |
| `program-id-axis-swap` | indexing | paper | `bidx2bidy` |  | device | Wrong grid axis at one tl.program_id site (axis 0 <-> 1). |
| `block-size-to-num-programs` | indexing | paper | `bdim2gdim` |  | device | In pid * BLOCK index math, the block extent becomes tl.num_programs(axis) (the Triton analogue of blockDim -> gridDim). |
| `block-size-swap` | indexing | paper | `grid-x-use-block-y` |  | device | In pid * BLOCK index math, the block extent is replaced by another BLOCK constexpr of the same kernel (the analogue of using blockDim.y for x). |
| `load-offset-off1` | indexing | paper | `smem-index-off1` |  | device | One tl.load reads one element past its intended address. The paper rule offsets a shared-memory partner index; Triton has no explicit shared memory, so the port offsets a global load pointer. |
| `stride-param-swap` | indexing | paper | `row-store-stride-k` | `a-row-stride-n`, `b-row-stride-k` | device | One use of a stride argument is replaced by another stride argument. |
| `dim-param-swap-index` | indexing | paper | `row-store-stride-k` | `a-row-stride-n`, `b-row-stride-k` | device | One dimension argument used as a multiplier in index math is replaced by another dimension argument (row * N -> row * K). |
| `dim-param-swap-decode` | indexing | paper | `flatten-height-use-width` | `output-position-height-first` | device | One dimension argument used to decode a flat index (% or //) is replaced by another dimension argument. |
| `launch-stride-swap` | indexing | paper | `row-store-stride-k` | `a-row-stride-n`, `b-row-stride-k` | launch | One tensor.stride(d) argument of a kernel launch uses the neighbouring dimension. |
| `acc-overwrite` | semantic | paper | `acc-overwrite` |  | device | Accumulation becomes overwrite: acc += x -> acc = x, and tl.dot(a, b, acc) drops its accumulator. |
| `acc-minus` | semantic | paper | `acc-minus` |  | device | Accumulation becomes subtraction: acc += x -> acc -= x, and acc = tl.dot(a, b, acc) -> acc - tl.dot(a, b). |
| `max2min` | semantic | paper | `fmax2fmin` |  | device | One elementwise or reduction maximum becomes the matching minimum. |
| `min2max` | semantic | paper | `fmin2fmax` |  | device | One elementwise or reduction minimum becomes the matching maximum. |
| `sentinel-zero` | semantic | paper | `sentinel-zero` | `reduce-seed-first-element` | device | A literal -inf (reduction sentinel, masked-load fill) becomes 0.0: wrong only when every value is negative. |
| `const0to1` | semantic | paper | `const0to1` |  | device | An initialiser 0 becomes 1: x = 0.0, tl.zeros(...) and tl.full(..., 0, ...). |
| `argmax-tie-last` | semantic | paper | `argmax-tie-last` | `argmax-tie-nan-form` | device | tl.argmax (or tl.max with return_indices) keeps the last maximum instead of the first: visible only on duplicate values. |
| `argmin-tie-last` | semantic | paper | `argmin-tie-last` |  | device | tl.argmin (or tl.min with return_indices) keeps the last minimum. |
| `nan-propagation-drop` | semantic | paper | `argmax-nan-policy-drop` |  | device | propagate_nan=ALL is dropped from tl.maximum/tl.minimum: differs only on NaN. |
| `reduce-max-tie-order` | semantic | paper | `reduce-fmax-tie-order` |  | device | m = maximum(m, x) becomes tl.where(x > m, x, m): NaN handling differs. |
| `reduce-min-tie-order` | semantic | paper | `reduce-fmin-tie-order` |  | device | m = minimum(m, x) becomes tl.where(x < m, x, m): NaN handling differs. |
| `relu-threshold-shift` | semantic | paper | `relu-threshold-shift` |  | device | tl.where(x > 0, x, y) cutoff moves to 1e-6: only tiny positives differ. |
| `positive-cutoff-nudge` | semantic | paper | `elu-positive-cutoff-nudge` | `selu-positive-cutoff-nudge` | device | tl.where(x > 0, x, f(x)) with f(x) != 0 (ELU/SELU) cutoff moves to -1e-6. |
| `relu-max-zero-remove` | semantic | paper | `relu-fmax-zero-remove` |  | device | maximum(x, 0) -> x: ReLU removed, wrong only for negative inputs. |
| `relu-max-zero-first-remove` | semantic | paper | `relu-fmax-zero-first-remove` |  | device | maximum(0, x) -> x: commuted ReLU removed. |
| `relu-where-remove` | semantic | triton-only | none |  | device | tl.where(x > 0, x, 0) -> x: the Triton tl.where spelling of ReLU removed. |
| `clamp-upper-unit-remove` | semantic | paper | `upper-unit-clamp-remove` |  | device | minimum(x, 1) -> x for a simple x: upper saturation removed. |
| `clamp-upper-unit-first-remove` | semantic | paper | `upper-unit-clamp-first-remove` |  | device | minimum(1, x) -> x for a simple x: commuted upper saturation removed. |
| `clamp-lower-negunit-remove` | semantic | paper | `lower-negunit-clamp-remove` |  | device | maximum(x, -1) -> x (either argument order): lower saturation removed. |
| `clamp-nested-drop-upper` | semantic | paper | `nested-unit-clamp-drop-upper` |  | device | minimum(maximum(x, lo), 1) -> maximum(x, lo); tl.clamp(x, lo, 1) -> tl.maximum(x, lo). |
| `abs-remove` | semantic | paper | `fabs-simple-remove` | `softsign-positive-fabs-elide` | device | abs(x) -> x: identity on non-negative inputs. |
| `ceil2floor` | boundary | paper | `ceil2floor` | `ceil2floor-lit` | device+launch | Ceil division becomes floor division (tl.cdiv/triton.cdiv, (a+b-1)//b, (a+255)//256): the tail block or tail iteration is never processed. |
| `lt2le` | boundary | paper | `lt2le` | `output-elements-one-extra-lane`, `line-count-one-extra-lane`, `flat-n-one-extra-lane` | device | ROR: one < becomes <= (off-by-one overrun). |
| `le2lt` | boundary | paper | `le2lt` |  | device | ROR: one <= becomes < (off-by-one underrun). |
| `gt2ge` | boundary | paper | `gt2ge` |  | device | ROR: one > becomes >=. |
| `ge2gt` | boundary | paper | `ge2gt` |  | device | ROR: one >= becomes > (one out-of-range lane slips through). |
| `lt2gt` | boundary | paper | `lt2gt` |  | device | ROR: one < becomes > (inverted guard). |
| `mask-drop` | boundary | paper | `guard-drop-if` |  | device | One tl.load/tl.store/atomic loses its mask (and fill value) or boundary_check: the Triton spelling of deleting a bounds guard. |
| `return-guard-drop` | boundary | paper | `return-guard-drop` |  | device | An early-return bounds guard (if cond: return) is removed. |
| `where-guard-drop` | boundary | paper | `guard-drop-ternary` |  | device | tl.where(cond, x, 0) -> x: an edge guard becomes an unconditional value. |
| `loop-bound-minus1` | boundary | paper | `loop-bound-minus1` | `last-row-reduction-skip`, `last-row-reduction-skip-start1`, `tile-last-iteration-skip`, `literal-loop-last-skip`, `strided-tail-drop`, `arg-reduction-last-row-drop`, `min-reduction-last-row-drop`, `cumsum-last-output-drop`, `pool2d-last-tap-drop` | device | A range/tl.range loop drops its last iteration (stop -> stop - step). |
| `loop-start-1` | boundary | paper | `loop-start-1` | `argmax-seed-from-second` | device | A range/tl.range loop skips its first iteration (start -> start + step). |
| `loop-step-double` | boundary | paper | `grid-stride-step-double` |  | device | A stepped loop doubles its step and skips every other chunk (the persistent or grid-stride loop analogue). |
| `mask-bound-minus1` | boundary | paper | `elementwise-guard-minus1` | `tail-guard-tighten`, `matmul-a-last-k-drop`, `matmul-a-transposed-last-k-drop`, `matmul-b-last-k-drop`, `groupnorm-sum-tail-scalar-drop`, `groupnorm-sqdev-tail-scalar-drop` | device | In one x < bound comparison the bound becomes bound - 1: the last element of a masked range or reduction is dropped. |
| `mask-bound-plus1` | boundary | paper | `elementwise-guard-plus1` |  | device | In one x < bound comparison the bound becomes bound + 1: one lane past the end. |
| `bound-dim-swap` | boundary | paper | `matrix-row-bound-use-n` | `matrix-col-bound-use-m`, `height-bound-use-width`, `width-bound-use-height` | device | A dimension argument inside a bounds comparison is replaced by another dimension argument (row < M -> row < N). |
| `sentinel-zero-min` | boundary | paper | `reduce-seed-first-element-min` |  | device | A literal +inf (min-reduction seed or fill) becomes 0.0: wrong only when every value is positive. |
| `debug-barrier-remove` | synchronization | paper | `sync-remove` |  | device | An explicit tl.debug_barrier() is removed. |
| `atomic-add-to-store` | synchronization | triton-only | none |  | device | A cross-program tl.atomic_add becomes a plain tl.store: concurrent partial results overwrite each other (lost updates in split-K style reductions). |
| `atomic-rmw-split` | synchronization | triton-only | none |  | device | A tl.atomic_add becomes a non-atomic load-add-store: a race that is visible only under contention. |
| `acc-fp16` | precision | paper | `acc-fp16` |  | device | An fp32 accumulator is declared fp16; its += updates (and tl.dot out_dtype) are rewritten to keep the loop-carried type consistent. |
| `store-fp16` | precision | paper | `store-fp16` |  | device | One stored value round-trips through fp16 (tl.store casts back to the pointer's element type). |
| `exp-fast` | precision | paper | `expf-fast` |  | device | Precise libdevice.exp becomes tl.exp (the approximate ex2-based lowering). |
| `div-fast` | precision | paper | `fdividef-fast` |  | device | IEEE division by a sum or denominator (or div_rn) becomes approximate tl.fdiv. |
| `named-constant-perturb` | precision | paper | `gelu-tanh-const-perturb` | `gelu-sqrt2pi-perturb`, `invsqrt2-perturb`, `selu-alpha-perturb`, `selu-scale-perturb`, `hardsigmoid-six-denom-perturb`, `hardsigmoid-slope-perturb`, `softplus-cutoff-tiny-shift` | device | A known approximation constant (GELU, SELU, hard-sigmoid, softplus cutoff) is perturbed by a relative 1e-3. |
| `named-constant-small-perturb` | precision | paper | `selu-alpha-small-perturb` | `selu-scale-small-perturb`, `hardsigmoid-half-ulpish-perturb` | device | A known approximation constant is perturbed by a relative 1e-4 (below the official tolerance). |
| `epsilon-remove` | precision | paper | `rsqrt-epsilon-remove` | `sqrt-epsilon-remove`, `literal-epsilon-remove` | device | A variance or literal epsilon stabiliser is removed (x + eps -> x). |
| `epsilon-halve` | precision | paper | `groupnorm-epsilon-halved` | `batchnorm-epsilon-small-bias` | device | A variance or literal epsilon is halved. |
| `softmax-max-subtraction-remove` | precision | paper | `softmax-max-subtraction-remove` | `softmax-max-subtraction-fast-remove` | device | The max subtraction feeding an exp is removed: overflow at large magnitude. |
| `variance-unbiased-count` | precision | paper | `variance-unbiased-count` |  | device | A population variance divides by N - 1 instead of N. |
| `store-scale-nudge` | precision | paper | `matmul-acc-store-fma-nudge` |  | device | One stored value is scaled by 0.9999 (the paper nudges the matmul accumulator store; the port applies at every tl.store). |
| `erf-to-tanh-approx` | precision | paper | `erf-to-tanh-approx` |  | device | An exact erf is replaced by the tanh approximation used by tanh-GELU. |
| `cutoff-shift` | precision | paper | `softplus-cutoff-shift` |  | device | A large piecewise cutoff in a tl.where condition (softplus 20) moves to 0.4x its value (the paper moves 20 to 8). |
| `clamp-bound-perturb` | precision | paper | `clamp-bound-perturb` |  | device | A unit saturation bound (minimum(x, 1.0) or tl.clamp(..., 1.0)) becomes 0.999. |
| `dot-tf32` | precision | triton-only | none |  | device | tl.dot input_precision ieee/tf32x3 -> tf32, or allow_tf32=False -> True. |
<!-- q1-mutate:operators end -->

## KernelBench-M rule mapping

All 127 rule definitions in KernelBench-M@d04d6fc7 (124 active after its
loader's pattern dedup; the paper's Table 7 lists 120). `ported` = primary rule
of an operator; `subsumed` = a CUDA spelling whose Triton form another
operator produces; `not-applicable` = no Triton analogue, with the reason.
Generated by `rules.mapping_markdown()`; a test keeps it current.

<!-- q1-mutate:rules start -->
| KernelBench-M rule | KBM family | Status | Triton operator or reason |
|---|---|---|---|
| `ceil2floor` | boundary | ported | ceil2floor |
| `ceil2floor-lit` | boundary | subsumed | ceil2floor |
| `lt2le` | boundary | ported | lt2le |
| `le2lt` | boundary | ported | le2lt |
| `ge2gt` | boundary | ported | ge2gt |
| `guard-drop-if` | boundary | ported | mask-drop |
| `guard-drop-ternary` | boundary | ported | where-guard-drop |
| `loop-bound-minus1` | boundary | ported | loop-bound-minus1 |
| `loop-start-1` | boundary | ported | loop-start-1 |
| `sync-remove` | synchronization | ported | debug-barrier-remove |
| `acc-fp16` | precision | ported | acc-fp16 |
| `store-fp16` | precision | ported | store-fp16 |
| `expf-fast` | precision | ported | exp-fast |
| `fdividef-fast` | precision | ported | div-fast |
| `tidx2tidy` | indexing | not-applicable | Triton has no thread index; a program instance owns the whole block. |
| `bidx2bidy` | indexing | ported | program-id-axis-swap |
| `bdim2gdim` | indexing | ported | block-size-to-num-programs |
| `plus2minus` | arithmetic | ported | plus2minus |
| `acc-overwrite` | semantic | ported | acc-overwrite |
| `acc-minus` | semantic | ported | acc-minus |
| `fmax2fmin` | semantic | ported | max2min |
| `fmin2fmax` | semantic | ported | min2max |
| `sentinel-zero` | semantic | ported | sentinel-zero |
| `const0to1` | semantic | ported | const0to1 |
| `lt2gt` | boundary | ported | lt2gt |
| `gt2ge` | boundary | ported | gt2ge |
| `return-guard-drop` | boundary | ported | return-guard-drop |
| `mul2div` | arithmetic | ported | mul2div |
| `mul2plus` | arithmetic | ported | mul2plus |
| `minus2plus` | arithmetic | ported | minus2plus |
| `negate-store` | arithmetic | ported | negate-store |
| `sync2syncwarp` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `reduce-shift2` | boundary | not-applicable | Triton block reductions (tl.sum, tl.max, tl.reduce) hide the explicit shared-memory tree, its partner index, its shift and its warp-size start. |
| `smem-index-off1` | indexing | ported | load-offset-off1 |
| `warpsize-16` | indexing | not-applicable | Triton block reductions (tl.sum, tl.max, tl.reduce) hide the explicit shared-memory tree, its partner index, its shift and its warp-size start. |
| `argmax-tie-last` | semantic | ported | argmax-tie-last |
| `argmin-tie-last` | semantic | ported | argmin-tie-last |
| `argmax-tie-nan-form` | semantic | subsumed | argmax-tie-last |
| `argmax-nan-policy-drop` | semantic | ported | nan-propagation-drop |
| `argmax-seed-from-second` | boundary | subsumed | loop-start-1 |
| `reduce-fmax-tie-order` | semantic | ported | reduce-max-tie-order |
| `reduce-fmin-tie-order` | semantic | ported | reduce-min-tie-order |
| `reduce-seed-first-element` | boundary | subsumed | sentinel-zero |
| `reduce-seed-first-element-min` | boundary | ported | sentinel-zero-min |
| `gelu-tanh-const-perturb` | precision | ported | named-constant-perturb |
| `gelu-sqrt2pi-perturb` | precision | subsumed | named-constant-perturb |
| `invsqrt2-perturb` | precision | subsumed | named-constant-perturb |
| `selu-alpha-perturb` | precision | subsumed | named-constant-perturb |
| `selu-scale-perturb` | precision | subsumed | named-constant-perturb |
| `erf-to-tanh-approx` | precision | ported | erf-to-tanh-approx |
| `softplus-cutoff-shift` | precision | ported | cutoff-shift |
| `relu-threshold-shift` | semantic | ported | relu-threshold-shift |
| `hardsigmoid-slope-perturb` | precision | subsumed | named-constant-perturb |
| `clamp-bound-perturb` | precision | ported | clamp-bound-perturb |
| `elementwise-guard-minus1` | boundary | ported | mask-bound-minus1 |
| `elementwise-guard-plus1` | boundary | ported | mask-bound-plus1 |
| `grid-stride-step-double` | boundary | ported | loop-step-double |
| `output-elements-one-extra-lane` | boundary | subsumed | lt2le |
| `line-count-one-extra-lane` | boundary | subsumed | lt2le |
| `flat-n-one-extra-lane` | boundary | subsumed | lt2le |
| `matmul-a-last-k-drop` | boundary | subsumed | mask-bound-minus1 |
| `matmul-a-transposed-last-k-drop` | boundary | subsumed | mask-bound-minus1 |
| `matmul-b-last-k-drop` | boundary | subsumed | mask-bound-minus1 |
| `arg-reduction-last-row-drop` | boundary | subsumed | loop-bound-minus1 |
| `min-reduction-last-row-drop` | boundary | subsumed | loop-bound-minus1 |
| `cumsum-last-output-drop` | boundary | subsumed | loop-bound-minus1 |
| `pool2d-last-tap-drop` | boundary | subsumed | loop-bound-minus1 |
| `groupnorm-sum-tail-scalar-drop` | boundary | subsumed | mask-bound-minus1 |
| `groupnorm-sqdev-tail-scalar-drop` | boundary | subsumed | mask-bound-minus1 |
| `matmul-after-load-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `matmul-after-compute-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `groupnorm-sum-store-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `groupnorm-sqdev-store-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `groupnorm-final-output-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `batchnorm-local-stats-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `batchnorm-merge-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `batchnorm-output-warp-barrier` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `avgpool121-denom-perturb` | precision | not-applicable | Perturbs the literal 121-tap divisor of one CUDA pooling kernel; Triton pooling divisors are runtime values. Not ported. |
| `hardsigmoid-six-denom-perturb` | precision | subsumed | named-constant-perturb |
| `hardsigmoid-half-ulpish-perturb` | precision | subsumed | named-constant-small-perturb |
| `softplus-cutoff-tiny-shift` | precision | subsumed | named-constant-perturb |
| `selu-scale-small-perturb` | precision | subsumed | named-constant-small-perturb |
| `selu-alpha-small-perturb` | precision | ported | named-constant-small-perturb |
| `groupnorm-epsilon-halved` | precision | ported | epsilon-halve |
| `batchnorm-epsilon-small-bias` | precision | subsumed | epsilon-halve |
| `matmul-acc-store-fma-nudge` | precision | ported | store-scale-nudge |
| `argmax-final-row-alias` | indexing | not-applicable | Targets an explicit per-row argmax loop; Triton arg-reductions are whole-block tl.argmax calls with no final-row index to alias. Not ported. |
| `argmax-final-row-value-alias` | indexing | not-applicable | Targets an explicit per-row argmax loop (value read); see argmax-final-row-alias. |
| `selu-positive-cutoff-nudge` | semantic | subsumed | positive-cutoff-nudge |
| `elu-positive-cutoff-nudge` | semantic | ported | positive-cutoff-nudge |
| `softsign-positive-fabs-elide` | semantic | subsumed | abs-remove |
| `relu-fmax-zero-remove` | semantic | ported | relu-max-zero-remove |
| `relu-fmax-zero-first-remove` | semantic | ported | relu-max-zero-first-remove |
| `upper-unit-clamp-remove` | semantic | ported | clamp-upper-unit-remove |
| `upper-unit-clamp-first-remove` | semantic | ported | clamp-upper-unit-first-remove |
| `lower-negunit-clamp-remove` | semantic | ported | clamp-lower-negunit-remove |
| `nested-unit-clamp-drop-upper` | semantic | ported | clamp-nested-drop-upper |
| `fabs-simple-remove` | semantic | ported | abs-remove |
| `rsqrt-epsilon-remove` | precision | ported | epsilon-remove |
| `sqrt-epsilon-remove` | precision | subsumed | epsilon-remove |
| `literal-epsilon-remove` | precision | subsumed | epsilon-remove |
| `softmax-max-subtraction-remove` | precision | ported | softmax-max-subtraction-remove |
| `softmax-max-subtraction-fast-remove` | precision | subsumed | softmax-max-subtraction-remove |
| `welford-second-delta-reuse` | precision | not-applicable | Matches one CUDA Welford spelling (a named second delta); Triton substrates compute moments by two-pass sums or tl.reduce combine functions. Not ported. |
| `variance-unbiased-count` | precision | ported | variance-unbiased-count |
| `kahan-compensation-drop` | precision | not-applicable | No compensated summation appears in Triton substrates; Triton accumulates in fp32 registers. Not ported. |
| `last-row-reduction-skip` | boundary | subsumed | loop-bound-minus1 |
| `last-row-reduction-skip-start1` | boundary | subsumed | loop-bound-minus1 |
| `strided-tail-drop` | boundary | subsumed | loop-bound-minus1 |
| `tile-last-iteration-skip` | boundary | subsumed | loop-bound-minus1 |
| `literal-loop-last-skip` | boundary | subsumed | loop-bound-minus1 |
| `tail-guard-tighten` | boundary | subsumed | mask-bound-minus1 |
| `shared-denom-use-local` | synchronization | not-applicable | Triton block programs have no per-thread versus shared-memory distinction to confuse. |
| `shared-sqrt-use-local` | synchronization | not-applicable | Triton block programs have no per-thread versus shared-memory distinction to confuse. |
| `reduction-barrier-move-before-store` | synchronization | not-applicable | Triton inserts its own barriers and has no warp-level or named barrier in the language, so a __syncthreads -> __syncwarp weakening has no analogue. |
| `welford-count-merge-early` | synchronization | not-applicable | Triton block programs have no per-thread versus shared-memory distinction to confuse. |
| `reduction-partner-half-offset` | indexing | not-applicable | Triton block reductions (tl.sum, tl.max, tl.reduce) hide the explicit shared-memory tree, its partner index, its shift and its warp-size start. |
| `row-store-stride-k` | indexing | ported | stride-param-swap |
| `a-row-stride-n` | indexing | subsumed | stride-param-swap |
| `b-row-stride-k` | indexing | subsumed | stride-param-swap |
| `matrix-row-bound-use-n` | boundary | ported | bound-dim-swap |
| `matrix-col-bound-use-m` | boundary | subsumed | bound-dim-swap |
| `height-bound-use-width` | boundary | subsumed | bound-dim-swap |
| `width-bound-use-height` | boundary | subsumed | bound-dim-swap |
| `flatten-height-use-width` | indexing | ported | dim-param-swap-decode |
| `output-position-height-first` | indexing | subsumed | dim-param-swap-decode |
| `grid-x-use-block-y` | indexing | ported | block-size-swap |
<!-- q1-mutate:rules end -->

## Known limits

- Synchronization is thin in Triton: only `tl.debug_barrier` and atomics are
  mutable, so that family will be small and the per-family comparison with the
  paper's 27.8% synchronization miss rate is indicative only.
- `mul2div` and several indexing swaps produce ill-typed Triton on integer
  index math; the compile filter removes them, so the CPU preview overstates
  the pool.
- Pointer, dimension and stride parameters are inferred from use (pointer
  roots of loads and stores, comparison operands, `stride` in the name). An
  unusual substrate may need these heuristics extended; an operator that
  raises fails the run rather than skipping.
- Specializations are recorded at the native shape only; gate (c) compiles
  other shapes, which can reveal behaviour that compile-equivalence at the
  native specialization treats as equivalent. Such mutants are dropped as
  equivalent before scoring and counted in the manifest.
- Toy kernels under `tests/data/q1_toy_kernels/` were written for the tests
  and are only parsed (and, for one, compiled without running); they are not
  substrates.

## NOTICE

No code from an unlicensed repository is included. Sources read, with what was
taken from each:

| Source | Revision | Size | SHA-256 | Licence | Use |
|---|---|---|---|---|---|
| HF dataset `Elfsong/KernelBench-M` (artifact of arXiv 2609.22220) | `d04d6fc72504750804c4f4b45b4a8d7dc7c1880d` | 442 files, 5,391,498 B | per file below | none declared | Read-only behavioural reference. Rule names and family labels only are reproduced (`rules.py`); every rewrite is reimplemented for the Triton AST. |
| ↳ `rules/structural_rules.py` | same | 5,897 B | `052bc98c64771fbe6dec5b7947690e19f6d39459d503a3cbd3bfdaa7e6beaca5` | none | read |
| ↳ `rules/fine_rules.py` | same | 10,130 B | `4d8aa234deaf66143514d699d63335072ad6416f1abf89b58d396696e96777ba` | none | read |
| ↳ `rules/mined_rules.py` | same | 7,554 B | `7d932c651796a6fff45e6c35f3eba079b9d1ca0752a182e62dbd18c4b4a58bb7` | none | read |
| ↳ `pipeline/mutator.py` | same | 10,978 B | `1a5b31efedacbe188879034e360ecb471afe1d077ab0734d4e888f0c68c2fc91` | none | read (rule loading, site semantics, stratified sampling idea) |
| ↳ `pipeline/analyze_holdout.py` | same | 3,498 B | `e39f411bd853a9c7e36895b4cff3f5d52100c704e50d795fc3f5af4e9e0574d9` | none | read (per-problem id-hash holdout) |
| ↳ `pipeline/nvrtc_tce.py` | same | 6,676 B | `ec84c494feb74c78654e6f75a8ed0e046cb0ce392503d1967d38c76670da3ea4` | none | read (compiled-image dedup) |
| ↳ `README.md`, `SPEC.md` | same | 3,394 B; 3,389 B | `a42175b769a8697d045b0af117ecbdf4630edd06e46cf166dce20a830127bfc6`; `b93214b1b41f2c8000c3134f77f5689ae6aee12635787163ade7ff9b5849444c` | none | read |
| Measuring the Checker, arXiv 2609.22220 (orx 0.2.2 full-text extraction) | v1 | 61,058 B | `03e2c1c62149438ac00b08478c474cd4bcc8d57303d29a833457651613e2cacd` | arXiv preprint | taxonomy, families, TCE, witness and holdout design |
| Dr. Kernel, arXiv 2602.05885 (orx extraction) | v2 | 79,529 B | `af628dd5ffc607c5007bfacf68236bef7af6a4a3c70ca2afc6f8e5fe4da28fe7` | arXiv preprint | Fig. 2 hacks (decoy, `self.training` branch) |
| KernelBench-Verified, arXiv 2607.16241 (orx extraction) | v1 | 105,239 B | `14490d59f53862a3033bbe8d9d2dbb6bb2cedfbbf8429e60731233a5812bcabc` | arXiv preprint | App. H.1 identity shortcut, App. L hacks |
| ScalingIntelligence/KernelBench `src/eval.py` | `44130946562d633cfb8e893986c5762a609c551c` | 36,082 B | `5ad54fd8b91fa7a503fdec1889bf73c8a8d039635b35d9ae01541a783d2fd8b3` | MIT | read: trial loop runs under `no_grad`, reference before candidate, fresh inputs per trial |
| KernelBench problems L1/19, L1/32, L1/100 | `423217d9fda91e0c2d67e4a43bf62f96f6d104f1` | 707; 776; 566 B | `cbbfc9409662168ee7a5d3e7f7a59bf56e0faf9d763197e7f6a41fb5942dd63a`; `b73a2ed250f2d9fec69a5899ddae3a15f41a9225b73a20ef6de5b8f8ef05fcf5`; `8e7ab261247e266e1b765957db04ea6972ac5dc9544607c059848d2417d5d3a1` | MIT | read; generated controls embed the problem file verbatim at run time |
| flagos-ai/FlagGems `src/flag_gems/{relu,softmax,mm,layernorm}.py` | `18b8e4281610c91e178518271bc756a98fdc84c9` | 3,663; 4,816; 6,958; 8,774 B | `84d41bce…0661`; `59923707…96e2`; `acbbafe6…e675`; `6cd7ebda…5313` | Apache-2.0 | read for kernel idioms; the toy kernels are written fresh |
| Triton `python/triton/runtime/jit.py` in `cotcodec-research:f10a8571-architecture` (image `sha256:65feae8f044a98303b862fe9bf4b0fefceae8bec356b473a2fff70f8949e34e6`) | Triton 3.6.0 | 41,084 B | `0b70358d901afd70937a344a7811e4a2bcd10edca8a7c241e47842dc9ac660c8` | MIT | `compiled._deserialize` mirrors `JITFunction.preload`'s deserialization of `serialize_specialization_data` |
| KernelGYM, lethe | per `harness/q1/schema.py` | not opened | not opened | none; MIT | behaviour taken from the reviewed Q1 plan's description only (grad-mode launch check, cheating class names) |

FlagGems full hashes: relu.py
`84d41bce42f21dc027e3283179327f8f2c8a22632b0b7cb7f8d7f5349f0f0661`, softmax.py
`5992370739fc20209edaac3f58949a9443c317c5dd45898965b4de5ca08d96e2`, mm.py
`acbbafe673855558e4bcec0eadaee5533fc6a1f3e3afd627d54f2fc9bf95e675`, layernorm.py
`6cd7ebdac4123db22920a553d6febf1a7ca04e7812642704de8ffea2a2fe5313`.
