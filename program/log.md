# Program log

Append-only. Newest entries at the bottom.

## 2026-10-06 — Program restart

- Verified all 18 candidate questions from Codex's research reset, Codex's
  five-direction ranking, the existing program and an H100 sweep. Three
  independent judges ranked them. 102 cited URLs audited: 95 OK, 7 fixed, 0
  removed. Codex's five-direction claims: 42 verified, 2 corrected.
- Chose three questions: Q1 kernel correctness-gate strength, Q2 calibrated
  computer-use instrument, Q3 cross-script sparse-indexer recall (carried over
  from D21). Ordered the backfill queue and dropped six lines with reasons.
- Moved the previous program to `legacy/` with history preserved (`git mv`),
  tagged `legacy-2026-10-06`. Kept live: the Docker and Slurm submitters,
  provenance and attestation tools, `orx` dispatcher, D21 contract and doctor,
  model registries, research-gauntlet rules and vendored skills.
- The Docker submitter now rejects archived memory workloads before any other
  memory-specific check. The `orx` default node now points to the D21 doctor.
- Restored the gauntlet procedure and evidence model to `docs/`, and the
  proposal template, evidence schema and D21 proposal to `program/proposals/`.
- Path references in the D21 contract and proposal were updated to the new
  layout. No gate, threshold or result in them changed.
- Removed from the public tree: an employer-internal corpus inventory and the
  host address. Kept out of the commit: a local Slack bot directory and an
  unfinished Letta doctor that demonstrates an undisclosed issue. All are in a
  private archive outside the repository. Old copies of the first two remain
  in public git history.
- No GPU job ran. GPU-hours spent by this program: 0.

## 2026-10-06 — Stage 0 begins

- Created a clean host clone of `main` at `~/cotcodec-main` for program work;
  the older host checkout with Codex's uncommitted edits is left untouched.
- Fetched `qwen3-0.6b-base` (Qwen/Qwen3-0.6B-Base at revision
  `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`) with a receipt through Slurm job
  365 in image `cotcodec-research:0b3ecef0-architecture`. Terminal state
  COMPLETED, exit 0:0. Receipt artifact-root SHA-256
  `7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0`.
- Scoping workflow launched for six Stage-0 items: evaluator mutation kit,
  Holo3 archive diff, Q3 K1, Q1 gate stack, action-path suite and VM runtime,
  and the serving throughput probe.
- Clarified the R570 rule: "untrusted model-generated code" means code a model
  produces as the object of study (sampled kernels, rollouts), not reviewed,
  committed harness code (decision D7). Decisions D1-D11 are in
  `program/decisions.md`.
- A private recheck confirmed two security-relevant observations about a
  third-party agent-memory library on its current main branch. Details are
  kept privately pending coordinated disclosure, which needs Kevin's go-ahead.
  Mentions that named the issue class were redacted from the public dossier,
  backlog and handoff; earlier commits still contain the short mention.
- Scoping of all six Stage-0 items finished with adversarial review. The job
  lane upgrade and builds for the Holo3 follow-up, serving probe and Q3 K1
  are running on separate branches.

## 2026-10-07 — Lane upgrade merged

- Merged the hardened Docker discovery lane (branch `stage0/lane`): opt-in
  `seed_binding`, `container_profile` (`default`, `vllm`, `large-cpu-mem`),
  `model: {kind: none}`, explicit memory limits, a foreign-GPU-process prolog,
  signal checkpoints confirmed only by a fresh `trigger=` marker, and a precise
  archived-memory rule with `legacy/` masked inside containers. An adversarial
  review found five bypasses; all were fixed with regression tests.
- The lane work found a pre-existing bug: Bash deferred the SIGUSR1 trap while
  `docker start --attach` ran in the foreground, so signal checkpoints never
  reached a live workload. Earlier signal-checkpoint evidence from the old
  lane should be treated as untested.
- `legacy/` is excluded from future images. The D21 doctor test now bounds
  child CPU time instead of wall time. Full suite on the host: 458 passed.

## 2026-10-07 — Q1 gate stack integrated (branch `stage0/q1-gates`, not merged)

- Merged the Q1 core (gates, audit, runner, analysis), mutator and substrate
  branches. The shared schema was byte-identical on all three
  (`c9bae9d5...3256`). No GPU job ran.
- Reconciled what the components disagreed on: the analysis now uses the
  substrate corpus's S1 split (`b773f218...`) and the mutator's content-hash
  dev/test split; one exclusion list serves every component; every control's
  `expected` map is checked by `analysis.control_checks`.
- Gate (c) no longer sets a free root below 2. The S1 converter refuses sizes
  below 2 (Dynamo's 0/1 specialisation), so 19 size-1 configurations would have
  made gate (c) reject correct S1 substrates; two of them (L1/9, L1/11) are in
  the evaluation half. Audit A3 keeps size 1, where a refusal is classified.
  The shape manifest was regenerated.
- The integration tests found three more defects: the mutant compile filter
  broke when `TRITON_INTERPRET=1` was set in the process (fixed), and the
  specialization manifest lacked `seeds: []` and asked for 1.0 GPU-h against a
  0.5 GPU-h budget (fixed).
- A CPU end-to-end test runs an Inductor ReLU and a Triton-tutorial softmax,
  five mutants and 15 controls through the real runner. It also showed that
  gate (a)'s 1e-2 absolute tolerance accepts a negated softmax over 1,024
  columns; this is recorded as a prediction in the draft.
- The two component preregistration drafts were merged into
  `program/preregistrations/q1-stage0-gate-validation.md`, which now names the
  version card it will freeze. It is a draft; freezing is the program owner's
  step. Evidence: `program/evidence/2026-10-07/q1-integration-validation.json`
  (253 Q1 tests in a GPU-less container, 651 passed and 8 skipped on the host,
  CPU doctor PASS).

## 2026-10-07 — Q1 gate stack fix pass after adversarial review (branch `stage0/q1-gates`, not merged)

- An adversarial review of `stage0/q1-gates@acb3bc8` reported 8 findings. All
  were verified; 7 are fixed in `c6ef3a9` and 1 (candidates can see the gate
  id and seeds) is recorded as a Stage 1 threat-model limit.
- Critical: c3 config ids built from `input_shape[0]` failed the verdict schema
  inside the worker after the candidate ran, so gate (c) rejected every kernel
  on 10 L1 problems. Ids now use `input_shape.0`; gate (c) checks ids before a
  candidate loads; row-building failures are infrastructure errors, retried
  once.
- Analysis: parent filter for mutants; unrefereeable components vacuous per
  problem; one kernel set across gates; S1 calibration parents' mutants out of
  the primary metrics; and code for every preregistered quantity that had none
  (audit-hole replay, calibration driver, weighting, breakdowns, c-lite, cost,
  FRR over independent units).
- `gate_b.py` was rewritten from the spec after the review found it
  transliterated parts of unlicensed KernelGYM code (never pushed). b1 and b2
  now replay b0's five calls first, as released.
- Infrastructure validation only: 280 Q1 tests in a GPU-less container, 669
  passed and 8 skipped on the host, CPU doctor PASS (195 items). Evidence:
  `program/evidence/2026-10-07/q1-gates-fix-pass.json`. The draft is not
  frozen.

