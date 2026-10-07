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

## 2026-10-07 — Q3 K1 frozen

- Merged the K1 code as commit A (`ec81fe3`). Image A
  (`sha256:6de9c900...`, Slurm job 434) was built from a clean clone of it.
- The K1 CPU doctor passed all seven cases in image A (receipt in
  `program/evidence/2026-10-07/q3-k1/`). The data bundle was rebuilt in image A
  from the recorded raw directory (Slurm job 436) and reproduced the
  registered SHA-256 `919d016b...` byte for byte.
- Froze `q3-k1-localization-screen-v1` (ledger row `c50540e9...`,
  `git_head_at_freeze` = commit A). Sign-offs are decision D16.

## 2026-10-07 — Holo3 audit registered

- Merged the Holo3 rerun audit (branch `stage0/q2-holo3-diff`). Froze
  `q2-holo3-rerun-audit-v1-posthoc` (the original v1 registration, recorded
  verbatim and labelled post-hoc per D10) and `q2-holo3-rerun-audit-v2`
  (confirmatory rules on data nobody has read; sign-offs in D15). The v2
  rules run within 14 days of the freeze, under Python 3.14 with scipy 1.18.0.
- Merged the serving-throughput probe and froze `serving-throughput-probe-v1`
  (sign-offs D17, D18). Full suite on the host: 848 passed.

## 2026-10-07 — Serving-throughput probe run (serving-throughput-probe-v1)

- Ran the frozen registration from a fresh host clone of `80a87ee` (contract
  and probe digest verified). Overlay image `sha256:fa1906ad...` built under
  Slurm 439 (cu129; torchcodec removed, args doctor pass); metadata for
  Qwen3-8B, Qwen3.5-27B-FP8 and Qwen3.5-35B-A3B-FP8 fetched under Slurm 444.
- Job A (Slurm 442, 28 min 32 s) and job B (Slurm 446, 10 min 51 s) both
  COMPLETED 0:0, lane `reason=completed`, and accepted; all gates passed,
  no eager fallback. X1 failed (replay latency delta 5.89% > 5%; 1 of 3 A1
  seeds valid), so job C was not rendered and no cu130 retry applied.
- Projection: Q1 within cap (2.92 GPU-h single turn, 10.21 three turns,
  x1.5 for X1); Q2 incomplete, re-probe: r3 and r4 failed only the
  contamination check, because the engine's own footprint under 20-screenshot
  prompts (76,611 MiB) exceeded the post-smoke reservation plus 2 GiB
  (76,349 MiB). Fixing that rule needs a new experiment id.
- GPU time 0.666 GPU-h: probe 0.656 (cap 1.0), build and fetch 0.010
  (cap 0.333). The capsule omitted the 27 tracked `.agents/skills` symlinks,
  which the discovery archiver refuses. Evidence:
  `program/evidence/2026-10-07/serving-throughput-probe-v1/`.

## 2026-10-07 — Q3 K1 screen stops at the smoke gate

- Image B (`sha256:5dc3025b...`, Slurm job 437, CPU only) was built from a
  clean clone at commit B (`d36cbbe`). Its revision label and source-tar
  SHA-256 match the clone.
- The K1 CPU doctor passed all seven cases in image B (Slurm job 443, `srun`,
  network none, no GPU). Its receipt's code digests equal the registration's
  table.
- The manifest filler (run from the clean clone) filled smoke, headroom-dev,
  R0 and R1. The smoke ran as orx node `66f7d302` (run `01692785`, branch
  `orx/q3-k1-smoke-q3-k1-localization-screen-v1` on commit B) as Slurm job 452.
  Terminal state COMPLETED, exit 0:0, `ORX_RESULT ... exit=0`, 2 min 25 s on
  one GPU.
- Smoke receipt: **SMOKE_PASS_OVER_BUDGET**. All four smoke gates passed, but
  the projected main wall time is 98.8 minutes (training about 43 minutes
  per worker, audit evaluation 51 minutes, 5 minutes start-up). That makes
  1.2 x 98.8 + 3 = 121.6 minutes against the fixed 30-minute limit (about
  6.6 GPU-h against the 2.0 GPU-h cap). The filler, re-run with the smoke run
  root, holds back the main job, its continuation and the extension for this
  reason.
- Under the registration and D16 the main job does not run under this id.
  Headroom-dev, the resume test and the main read were not run. No audit
  statistic exists and there is no K1 verdict. The tabled filler hard-codes
  the 30-minute rule, so any rescoping needs a new experiment id and
  preregistration. At the projected cost (about 6.6 GPU-h for the main job
  plus up to about 6.4 GPU-h for the extension) it would cross the 8 GPU-h
  gauntlet threshold. That is Kevin's decision.
- GPU-hours spent by this experiment: 0.04. Evidence:
  `program/evidence/2026-10-07/q3-k1/`.

## 2026-10-07 — Holo3 v2: first confirmatory result

- Ran `q2-holo3-rerun-audit-v2` (Slurm job 438, CPU only). All receipts are
  `v2 CONFIRMATORY`. Rule (d): not attributable to checker time-dependence
  (p = 0.156). Rule (a): no agent-behaviour shift (Wilcoxon p = 0.94).
  Rule (b): the 14 run2-unique failures are unexplained (1 environment,
  1 agent-side). Coverage 96.8%. The 5.75 GB tarball was deleted after the
  run. Results: `program/evidence/2026-10-07/holo3-v2/RESULTS.md`.
- Implication for Q2 Stage 1: same-day, same-operator reruns can shift by
  4.4 points with no visible cause, so the variance model needs a session
  random effect and more than one session per cell.

## 2026-10-07 — Serving probe v2 frozen

- Merged and froze `serving-throughput-probe-v2` (sign-offs D19, D21). It
  attributes GPU memory by process, compares real and dummy weights on
  identical prompt token sequences, reserves launch time for required points,
  and reruns only job A's points that v1 lost. Full suite on the host: 1,029
  passed.

## 2026-10-07 — Action-path runtime and Q1 gate stack built (not frozen)

- Q2 Stage 0b (branch `stage0/q2-action-path`): CPU-only VM lane
  (`vm-campaign.sbatch`), VM in its own network namespace with the runner
  sharing it (D13: a bridge-unpublished guest was still reachable from other
  containers through the image's DNAT, job 372). 22 cold boots: first
  screenshot p50 18.3 s, p95 20.8 s; 21 of 21 resets pristine; only
  `/dev/kvm` exposed. The 100-entry action-path catalog and its device-level
  reference were frozen-ready before any executor code. Review findings
  (11) fixed; remaining components are being written.
- Q1 Stage 0 (branch `stage0/q1-gates`): gates (a), (b), (c), the
  independent audit, mutator and substrate builders integrated; 280 tests
  pass in a GPU-less container. The review found a critical defect (gate (c)
  rejected every kernel on 10 problems because of a config-id format) and
  seven others, all fixed. Not yet run on a GPU; the projected Stage 0 total
  (9-10 GPU-h) is above the gauntlet threshold, so a measured pilot decides
  between a registered trimming rule and the gauntlet.

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

## 2026-10-07 — Serving probe v2 run: X1 pass, Q2 rescope before the gauntlet

- Ran the frozen `serving-throughput-probe-v2` from a fresh host clone of the
  freeze commit `1141d94` (contract `9224ccdc...` and probe digest
  `64493671...` verified; ledger row verified). The schema-3 capsule
  (`0e9c210c...`, worktree clean) omitted the 27 `.agents/skills` links under
  the reviewed rule. Overlay image `sha256:a59d7782...` built under Slurm 464
  (cu129; v2 plan and args doctor pass).
- Job A (Slurm 466, 28 min 23 s) COMPLETED 0:0, lane `reason=completed`,
  summary `complete` and accepted. Every gate passed (G0.9 in pid mode in
  both phases, container-namespace PIDs; reservation 75,653 MiB real,
  75,325 MiB dummy). All 16 points valid on their first attempt; r3 flagged
  front-end-bound.
- X1 `pass`: identical prompt token ids on all 336 paired requests; open-loop
  delta 2.66% (5%), replay delta 2.71% (8%), SE 4.00% (5%), A1 range 1.82%,
  r1b replicate 0.80%. It enters no v2 budget; later registrations cite it.
- Q2 `rescope-before-gauntlet`: 431.5 GPU-h (4B and 9B rungs 55.3 each, 27B
  239.4 and 35B-A3B 81.6 on the unmeasured active-parameter rule). The 4B and
  9B rungs alone (110.6) exceed the 90 GPU-h line. A1 noise 1.0; no F1
  correction (PNG 3.1% faster). Q1 not projected; v1's result stands.
- GPU time 0.485 GPU-h: job A 0.473 (cap 1.0), overlay build 0.012 (cap
  0.167). Serving probe total with v1: 1.151 GPU-h. Evidence:
  `program/evidence/2026-10-07/serving-throughput-probe-v2/`.

## 2026-10-07 — K1 v2 throughput probe frozen

- The K1 v2 batched-bank GPU equivalence pre-check passed on the H100 (Slurm
  516, 0.004 GPU-h): every gated deviation more than 100 times inside its
  TF32 tolerance; Adam steps bitwise.
- A pre-freeze audit found the probe's manifest filler did not enforce the
  probe's GPU count, limit and 0.15 GPU-h cap or the image commit; fixed with
  tests. Froze `q3-k1-throughput-probe-v1` (D20, D22). Projected v2 totals
  under D22's counting rule: about 6.6 GPU-h central, 9.5 conservative; the
  probe's measurement decides between freezing v2 and the gauntlet.

## 2026-10-07 — K1 v2 throughput probe run: complete, caps 8.05 GPU-h, gauntlet

- Ran the frozen `q3-k1-throughput-probe-v1` from a fresh clean host clone of
  `4b9d6c4` (holds ledger row `c9b45f00...`). Probe image `sha256:e59d9cc1...`
  (Slurm 533, CPU). v1's K1 doctor (Slurm 534, 7/7) and the v2 doctor (Slurm
  536, 5/5) passed in that image, CPU only and `--network none`. The filler,
  dry-run and test-only passed. orx node `1c4cb641` (commit `8415ee7`) ran as
  orx run `b6fb997c`.
- Job 543 COMPLETED 0:0 in 3 min 18 s (limit 9). Lane `reason=completed`,
  provenance and model verification passed, `ORX_RESULT ... exit=0`. Receipt
  `cae4e949...`: `PROBE_COMPLETE`. Every TF32 device gate passed: largest
  gradient deviation 1.7e-4 against 1e-2, Adam bitwise, selection exact. The
  composition check passed (max ratio 1.001 against 1.15). The concurrent arm
  was measured, not bounded: 7.41 s per step, 1.035 times the sum of the solo
  steps.
- `derive_sparse_indexer_k1_v2_limits.py` without `--apply` (exit 1). Main
  projects 33.6 min (limit 50, cap 3.34 GPU-h); the worst-case extension 35.7
  (53, 3.54); smoke, headroom-dev and R2 each get 11 min, R0 15 and R1 12. The
  total with the probe is **8.05 GPU-h**, over the 8 GPU-h threshold, so
  `gauntlet_required` is true. Under D20 and D22, v2 is not frozen and goes
  through the research gauntlet; the design is not cut. Neither the contract
  nor the v2 registration was edited.
- GPU time: 0.055 GPU-h (D22 counts the probe at its 0.15 cap). Evidence:
  `program/evidence/2026-10-07/q3-k1-v2/probe/`.

## 2026-10-07 — Q1 Stage 0 pilot pass: GPU paths validated, cost card measured (branch `stage0/q1-gates`, not merged)

- Three one-GPU lane jobs on trusted code only (KernelBench references,
  TorchInductor output, pre-2025 human-written kernels and harness-derived
  mutants and controls; model kind none): 474 smoke and admission, 518 pilot
  cost, 548 paired concurrency re-measurement. 0.899 GPU-h of the pass's 1.0;
  image builds 472, 487, 507 and 544 CPU-only from fresh clones.
- Corpus hand-off: S2 sources vendored with their licences (22 files
  re-verified against the pinned commits), the corpus recipe committed, and one
  hash-bound study artifact per job (28 MB, host-only; it carries the
  unmodified KernelGYM and KBV clones for fidelity).
- Validated on the GPU: admission and device codegen, specializations, the
  identity control through all 15 gates and channels, fidelity against
  unmodified KernelBench (a 11/11; a_head_1e-4 9/11 plus 2 listed in
  advance), KernelGYM (decoy 5/5 comparable) and KBV (c1 11/11), calibration
  on S1-cal (M stays 16), the poison allocator, compute-sanitizer, b2 and the
  timing harness.
- Found and fixed: compute-sanitizer never ran on S1 kernels (they refuse
  `A3/lead1`), so A4 and every tier were `error` for all S1 kernels; the probe
  now skips refused shapes (job 548: 6/6 S1 kernels accepted at `A3/lead5`).
  b2 rows record profile attempts (the retry is unreachable on a working
  GPU); timing now runs before scoring.
- Open (owner): the TF32-admissible threshold rejects the TF32 tutorial
  matmul at every held-out shape; A5 counts S1 dtype refusals as failures.
- Cost card: c/b = 1.64 (no c-lite). Stage 0 as drafted projects to about
  1,056 GPU-h (scoring 95% interval 671-1,359), far above the 8 GPU-h cap and
  a lower bound (gate (c) on a 4.3 GB problem ran over 676 s). 12 items per
  GPU halve small-problem cost with identical verdicts (ratio 0.493 on 240
  paired items). Proposed rule `q1-stage0-trim/1` (preregistration section
  18.5): 7.37 GPU-h through its last fixed bucket, a hard stop at 8, every gate,
  family, tier and policy kept, mutant metrics narrowed to problems under 1 GB
  with about 2.5 times wider intervals; or the gauntlet. Evidence:
  `program/evidence/2026-10-07/q1-pilot/`.
