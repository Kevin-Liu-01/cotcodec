# harness/q1: kernel correctness-gate stack (Q1 Stage 0)

Three gates of increasing strength, an independent audit that no gate sees,
a runner with a watchdog and an append-only journal, a timing harness, and a
CPU doctor. The preregistration draft is
`program/preregistrations/q1-stage0-gate-validation.md`.

## Layout

| Path | Owner | Contents |
|---|---|---|
| `schema.py` | core (binding, copied verbatim by all owners) | substrate / mutant / control layouts, verdict rows, pinned revisions |
| `problems.py`, `shapes.py` | core | pinned KernelBench problems, constant scope analysis, c2/c3/A3 shape rules |
| `gates/gate_a.py` | core | KernelBench@44130946 check and HEAD/tolerance variants, upstream fidelity entry points |
| `gates/gate_b.py`, `gates/KERNELGYM_SPEC.md` | core (rewritten in the fix pass) | b1 launch hook and b2 profiler coverage, from the behavioral spec; b1/b2 replay b0's five calls first |
| `gates/b_native.py` | core | runs an unmodified KernelGYM clone (fidelity only) |
| `gates/gate_c.py` | core | KBV values (c1), shapes (c2), unaligned remainders (c3), validity gate |
| `audit/` | core | A1 fp64 oracle (D14 dual TF32 policy, calibration), A2 values, A3 shapes with refusal classification, A4 contracts and dual-poison allocator, A5 lethe-style checks, tiers |
| `runner.py`, `worker.py`, `journal.py` | core | one subprocess per item, phase watchdog, kill-and-resume journal, signal checkpoint; item requirements and per-item journals (reference items) |
| `refstore.py` | engineering pass (decision D31) | reference store: reference items compute gate (c)'s references and validity gate and the audit's fp64, device, TF32 and CPU fp32 references and A5's reference calls once per problem, replicate and channel; consumers read the entry or compute inline (gate (a) always inline since the D31 review; in `gate_code_sha256` and `audit_code_sha256`) |
| `faults.py` | D31 review fix pass | the one list of GPU resource-failure text the runner's contention rule, its health check and the reference store share |
| `memory.py`, `memory_table.json` | D31 review fix pass | execution policy `q1-stage0-exec/2`: per-item capacity units from estimated (or measured) peak GPU memory; the meta-device table is built by `scripts/q1_memory_table.py` (in `driver_sha256`) |
| `refschedule.py` | engineering pass (D31) | which items share an entry (groups of at least two kernels), where reference items go, what each consumer requires (driver) |
| `repilot.py` | engineering pass (D31) | the re-pilot rule `q1-repilot/1` (S1-cal problems with no evaluation unit, paired inline and store arms) and the twin-row comparison (driver) |
| `exec2_validation.py` | D37 validation job | the rule `q1-exec2-validation/1` of the one validation job under `q1-stage0-exec/2` (re-pilot kernels and the KernelBench adversarial controls under the store, adversarial controls chained because they share an extension name); run by `scripts/run_q1_exec2_validation.py`; outside the version card |
| `timing.py` | core | randomized paired timing with L2 flush and CUDA events |
| `analysis.py` | core, integration | ladder composition with vacuous unrefereeable components, tiers, splits, parent filter and mutant scope, MS (weighted and unweighted)/FAR/FRR/FRR_independent/FA-share on one kernel set, paired differences, breakdowns, precision-only class, audit-hole candidates and summary, c-lite set cover, marginal and amortized cost |
| `audit/calibration.py`, `audit/replay.py` | integration | M calibration driver (members, fault ceiling, exact references) and the audit-hole replay (`scripts/q1_calibrate_audit.py`, `scripts/q1_audit_hole_replay.py`) |
| `doctor_fixtures.py` | core | CPU-only synthetic fixtures for the doctor and tests |
| `data/` | core | problem hashes, KBV configuration table, shape manifest |
| `third_party/kernelbench/` | core | verbatim KernelBench files (MIT), see NOTICE |
| `controls.py` | core | reference-identity and KernelBench adversarial controls (`python -m harness.q1.controls --out-root R`) |
| `versions.py` | integration | version card named in the preregistration (`scripts/q1_version_card.py`) |
| `pilot.py`, `cost_card.py` | pilot pass | pilot selection, schedule and size rules (watchdog limits, exclusive class); the cost card and the trimmed projection |
| `trim.py`, `data/pilot_exposed.json` | second review fix pass | the trimming rule `q1-stage0-trim/2` as code (plan, seeded samples, FRR set, control schedule, buckets, units, budget check) and the hash-pinned list of kernels the pilot exposed (decision D26); run by `scripts/run_q1_stage0.py` |
| `mutate/` | mutator owner (`stage0/q1-mutate`) | Triton AST mutants, compiled dedup, cap and split, hack controls; see `mutate/README.md` |
| `substrates/` | substrate owner (`stage0/q1-substrates`) | S1 Inductor and S2 human-written substrates, admission, S1 split; see `substrates/README.md` |

## Interfaces other components depend on

- Kernel directories and verdict rows: `schema.py` (`q1-schema/1`).
- Problem access: `problems.load_problem_source(problem_id)` (hash-checked),
  `problems.analyze_problem`, `problems.override_constants`.
- Work items: `runner.WorkItem(kernel_id, kernel_path, problem_id, gate, seed,
  problem_source_path, options, exclusive, timeouts, units, requires, journal,
  memory_bytes)`;
  gates and channels in `worker.WORK_GATES` (reference items: `ref_*`).
- Phase reporting for the watchdog: `gates.outcome.report_phase`.
- Seeds: `gates.outcome.channel_seed(base, replicate, index)`.

## Running

```bash
# pure-Python tests (laptop)
uv run pytest -q tests/test_q1_schema.py tests/test_q1_problems.py \
  tests/test_q1_journal.py tests/test_q1_provenance.py tests/test_q1_lethe_priors.py
# torch tests and the CPU doctor: GPU-less container on the host
# (see experiments/manifests/q1-core/q1-gate-doctor-cpu.md for the exact command)
python -m pytest -q tests/test_q1_gates.py tests/test_q1_audit.py tests/test_q1_runner.py
TRITON_INTERPRET=1 python scripts/run_q1_gate_doctor.py --output /out/doctor-RUN_ID
# regenerate or check committed data
python scripts/build_q1_shape_manifest.py --check
python scripts/build_q1_kbv_configs.py /path/to/kernel_bench_verified --output harness/q1/data/kbv_hidden_configs.json
```

GPU work (smoke, admission, specializations, pilot, Stage 0) runs only as
Slurm jobs through the Docker lane, with the templates in
`experiments/manifests/`, after the preregistration is frozen.

## Integration (stage0/q1-gates)

The three components are merged on `stage0/q1-gates`. The pipeline is

```
substrates (S1 convert, S2 build, admission) -> mutate (pool, compile, select, controls)
  + controls.py (identity, adversarial) -> trim.plan (q1-stage0-trim/2)
  -> run_q1_stage0.py -> runner/worker (gates a-c, audit A1-A5)
  -> journal -> analysis.py / report_q1_stage0.py --plan
```

- `tests/test_q1_integration.py` (pure Python) builds real substrates, runs
  the mutator on them, and checks every hand-off, the splits, the control
  gate ids, the job manifests and the preregistration's version table.
- `tests/test_q1_integration_cpu.py` (torch, Triton interpreter, no GPU) runs
  an S1 and an S2 substrate, five mutants and 16 controls through the real
  runner and checks verdict rows, ladder, tiers, metrics and every control
  expectation that does not need `b2`.
- `scripts/q1_version_card.py --markdown` prints the table the
  preregistration must name; rerun it after any change to Q1 code or data.

### Fix pass after the adversarial review

- Config ids are schema-safe where they are made (`shapes.root_label`:
  `input_shape[0]` is written `input_shape.0`; overrides keep the real name),
  `gate_c.c_configs` refuses an invalid id before any candidate loads, and the
  worker writes one `error` row (`infra_failure-harness-row`) when building or
  serialising rows fails, so a harness fault is never a candidate rejection.
  The runner retries an infrastructure-failed item once.
- `analysis.py`: unrefereeable gate (c) families and A2/A3 channels are
  vacuous per problem; mutants are scored only when the same audit tier
  accepts their parent; primary mutant metrics use evaluation-set parents
  (S1-cal parents are a labelled secondary); every gate is compared on the
  kernels a, b and c all referee; FRR for criterion 3 is over independent
  units; bootstrap clusters link problems that share a kernel family.
- `gates/gate_b.py` was rewritten from `KERNELGYM_SPEC.md` (see NOTICE) and
  now replays b0's five candidate calls before b1/b2, plus b2's empty-profile
  retry; `relu_call_count_switch` (doctor) and `call-count-switch` (hack
  control) check it.

## Reference store (decision D31)

Gate (c) and audit channels A1, A2, A3 and A5 compare a candidate with
references computed on its own inputs, and none of those references depends on
the candidate. `refstore.py` computes them once per problem, replicate and
channel in a **reference item** (gates `ref_c`, `ref_A1`, `ref_A2`, `ref_A3`,
`ref_A5`; no candidate loads) with the same functions the inline path calls
(`gate_c.reference_configs`, `audit.run.reference_draws`,
`lethe_contracts.reference_results`) and writes an entry; a **consumer** item
draws its inputs as before, reads the entry and runs the candidate. Gate (a) is
not a consumer (D31 review): upstream KernelBench computes the reference in the
candidate's process. The store is an optimisation only:

- an entry is usable only if no reference call raised, changed an input it
  received or the CPU/CUDA RNG state, no stored output aliases an input, and
  every output is a tensor or tuple/list of tensors; a resource failure writes
  no entry (the reference row carries the text, so the runner retries a shared
  reference item alone while its consumers wait); an unusable entry keeps no
  tensors;
- the TF32/cuDNN switches and a fingerprint of each draw's inputs are checked
  before every draw (A5: before every stored reference call), and a consumer
  computes inline from the first draw it cannot use; gate (c) first replays the
  reference forwards the store skipped;
- disk: groups over `refschedule.ENTRY_CAP_BYTES` compute inline, entries are
  written only within `refstore.STORE_CAP_BYTES`, and the Stage 0 driver
  deletes an entry's tensors after its last consumer;
- consumers add nothing to verdict rows; what they used is in
  `<store>/uses/`, and reference rows go to `references.jsonl`, never to the
  scoring journal;
- `tests/test_q1_refstore_equivalence.py` (doctor corpus) and
  `tests/test_q1_integration_cpu.py::test_reference_store_rows_equal_inline_rows`
  (committed fixtures) prove identical verdict rows except timing and run
  fields, for kernels with defined behaviour that leave process-global state
  alone; `tests/test_q1_refstore_semantics.py` covers a stateful reference with
  a switch flip, A5 integer inputs written in place and raising references. The
  exceptions are a kernel that reads memory it never wrote (its rows depend on
  allocator history; the inline path does not reproduce them either, and A4
  rejects such a kernel either way) and a candidate that changes process-global
  state at import (the store's reference comes from a clean process);
  `program/evidence/2026-10-07/q1-engineering-d31/` holds the differential
  against main's code.

`scripts/run_q1_stage0.py` uses the store unless `--reference-store off`;
`refschedule.with_references` gives every (problem, replicate, channel) read by
at least two pending kernels one reference item, placed before its first
consumer. The store lives beside the output, so a resumed job recomputes what
its pending items need.

## NOTICE

### Vendored verbatim (MIT)

ScalingIntelligence/KernelBench, Copyright (c) 2023 Anne Ouyang, Simon Guo,
Azalia Mirhoseini, Scaling Intelligence Lab, Stanford University. MIT License,
`third_party/kernelbench/LICENSE` (SHA-256
`fb5917dd8e4476fa75e89ef6f03dccf07d4859636bc23c7db50e6c0413887b9e`, identical
at both revisions). Every vendored file, its upstream path, revision, size and
SHA-256 is listed in `third_party/kernelbench/SOURCES.json` and checked by
`tests/test_q1_provenance.py`:

- `src/eval.py` @44130946562d633cfb8e893986c5762a609c551c (36,082 B);
- `src/kernelbench/{eval,timing,kernel_static_checker,dataset}.py` and the three
  adversarial test kernels @423217d9fda91e0c2d67e4a43bf62f96f6d104f1;
- `KernelBench/level1/*.py` and `KernelBench/level2/*.py` @423217d9
  (200 files; per-file SHA-256 in `data/kernelbench_423217d9_problems.json`).

The two `utils.py` files are minimal stand-ins (not verbatim): upstream
`utils.py` imports dotenv, openai, litellm and tqdm for inference helpers that
evaluation never calls; the stand-ins contain only `read_file` and
`get_gpu_vendor`, whose bodies are copied verbatim.

### Reimplemented from behavior, not vendored

- **hkust-nlp/KernelGYM @3a84417f8c0efaadb215ef638b37d12e71ed20f3**: no LICENSE
  file (the README claims Apache-2.0), so its code may not be copied here
  (decision D6). Its released hacking check was read on the host from a
  scratch clone (pack size 1.85 MiB) and described in `gates/KERNELGYM_SPEC.md`.
  **Licence-risk history.** The adversarial review of `stage0/q1-gates@acb3bc8`
  found that the first `gates/gate_b.py`, although it said "No KernelGYM code
  is copied", transliterated parts of `triton_detect.py` statement by
  statement (kernel-name resolution, the capture record, the `__getitem__`
  wrapper, the grid-attribute and resolver lists): token similarity of
  `kernel_name` to `_get_kernel_name` was 0.84 raw and 0.96 with identifiers
  normalised, with 7 shared string literals. That version was never pushed.
  In the fix pass `gates/gate_b.py` was rewritten from `KERNELGYM_SPEC.md` by
  an agent that had read neither the KernelGYM source nor the earlier hook
  code. Where the spec was silent (which object a capture names; the
  `unknown` fall-through), behavior was measured black-box against the
  unmodified clone on 40 controlled objects and 5 interpreter kernels (all
  equal) and is pinned by
  `tests/test_q1_gates.py::test_capture_names_match_kernelgym`. After the
  rewrite the largest similarities are 0.49 raw / 0.58 normalised
  (`_resolve_name` vs `_get_kernel_name`, longest common run 7 tokens; the 6
  shared literals are the attribute names the spec requires) and 0.45 / 0.57
  (`capture_text` vs `_append_capture`). This is weaker separation than a
  two-person clean room (one agent wrote the spec, another implemented it
  only for this rewrite); a licence from the authors (an outward action, D2)
  would remove the residual risk. Files read for the spec (bytes, SHA-256):
  `kernelgym/toolkit/kernelbench/triton_detect.py` (31,846,
  `426c415e8518f001b15acad7acb5e2d601fb9dcb09c9098e54969bd6b4b16502`),
  `pipeline.py` (25,633, `80298b9ea21ce45ca2346ba60c12e417780cee6b0778e4abe59ad4b606d77bf2`),
  `profiling.py` (10,075, `f6c3c707c885bda140be9cdaa67776b13eccd69b9bed85c29cc808aff3d3924e`),
  `timing.py` (4,142, `486310e086a18cf1dae1b900bdd87bc0d629ead9d5dc2e03fb07e65d93fa5b5c`),
  `correctness.py` (4,463, `361b316a3adc4251fd8cac561d39d150dfd251d63693532fc3fa85587755e506`),
  `loading.py` (2,446, `bd30ef06116aacbc5775c50f97a4435b084274f281726168658d4ed4e6ea49f4`),
  `exec_types.py` (583, `8c209627ec288679520dec4c1f8232512cd927051a17c11ec15d5768a56d9907`),
  `kernelgym/config/settings.py` (15,022, `086b70b777d8278588b928a28505de08f243da47fd1265b7b7b6fbdae51f36ca`).
  `gates/b_native.py` imports the unmodified clone at run time from a path
  outside this repository for fidelity measurement only.
- **RishiShah99/lethe @eaff0bb6bd6d3a1c510fa7b4708ceb0f07a5ac9e** (MIT, Copyright
  (c) 2026 Rishi Shah and Rishav Shrestha; LICENSE SHA-256
  `97c4d23b3255b0a22a6073c9cc7851b4d3f55e554ba2091d91f7f68beb2ce501`): the
  EXC-01, EXC-02, PRC-01 and PRC-02 gate semantics and the ORD-02 contract idea
  are reimplemented in `audit/lethe_contracts.py` and `audit/contracts.py`, with
  the adapter fixes listed there (training mode instead of `.eval()`, every
  floating input perturbed). Files read: `src/lethe/verifier/contracts.py`
  (28,258, `398611e33b3551f5c2a8cba8ddf745056f4d03e5302ebe95c03a3605bafb6c4f`),
  `src/lethe/verifier/audit_harness.py` (13,648,
  `5d79e6deca76abf7d0e26c88d53b413b9753c82da50ce290a90066ebf4331281`).

### Data extracted (MIT)

- **facebookresearch/kernel_bench_verified @3fdf6fec7372a4d0cb682635f00e7bdcbc55d50e**
  (MIT, Copyright (c) Meta Platforms, Inc. and affiliates; LICENSE SHA-256
  `da6d3703ed11cbe42bd212c725957c98da23cbff1998c05fa4b3d976d1a58e93`): the
  per-problem hidden configuration lists were parsed (not executed) into
  `data/kbv_hidden_configs.json`, which records each `hidden_tests` file's
  SHA-256. The D1-D4 scale factors and the L1/100 D5 targets are reimplemented
  in `gates/gate_c.py`. Also read: `scripts/generate_hidden_inputs.py` (17,909,
  `5497916313cc7bbca5347711476c84c6282d46a5b055c0d259c2ff9795a57ca4`),
  `src/eval.py` (41,061, `30d694d24434e0c8032d5ff491a88442f30d94aca2893ec12b9faa67ec41153e`).
- **lethe `results/audit_rows.jsonl.gz`** (217,947 B,
  `e20a65ede302f531bbc81170a2dd3f0e42185fd4d12c883f71b5448a00dcde40`) and
  **hkust-nlp/drkernel-coldstart-8k @cba0ef06a5b1e3c307b7acfa8b6acb7a46578105**
  (`drkernel-coldstart-8k.parquet`, 163,236,950 B,
  `4ed72a9f85c069aaec2daf65229c35d1b888762a455e115fe23f8eae2541097b`, MIT):
  inputs to the zero-GPU priors reanalysis (`scripts/q1_lethe_priors.py`); only
  the derived summary is committed
  (`program/evidence/2026-10-07/q1-lethe-priors.json`). The parquet was
  downloaded to the host's persistent storage under D1.

### Read-only reference, never vendored

- **Elfsong/KernelBench-M @d04d6fc72504750804c4f4b45b4a8d7dc7c1880d** (no
  licence declared): used by the mutator owner as a read-only reference; the
  core does not read or include it.

### Base image and packages

- `cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`
  is NGC-derived (NVIDIA Deep Learning Container License); the derived
  `cotcodec-q1-gates` image (`infra/q1-gates/Dockerfile`) must not be pushed
  to a public registry.
- Packages added by the derived image (PyPI, versions pinned in the
  Dockerfile): python-dotenv 1.1.1 (BSD-3-Clause), tomli 2.2.1 (MIT), pyarrow
  21.0.0 (Apache-2.0), ninja 1.13.0 (PyPI classifiers: Apache-2.0 and BSD; the ninja binary is Apache-2.0), pydantic-settings 2.10.1
  (MIT, test-only), pytest 8.4.2 (MIT).
