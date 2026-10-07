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

## 2026-10-07 — Q2 evaluator-mutation kit integrated (dev split, exploratory)

- Branch `stage0/q2-evaluator-mutation` merges the harness, the blind specs
  and the operator catalog, and adds `harness/q2_mutation/campaign.py`: blind
  spec -> operator -> mutant -> GUI-faithful LibreOffice save -> pinned
  `evaluate()` -> VerdictRow, as three CPU-only Slurm jobs per run (no GPU, no
  network, D12/D13).
- Three end-to-end runs on the 17 dev targets (Slurm 453-455, 458-460,
  461-463): 275 mutants planned from the blind specs, 271 admitted. Applying
  recipes to the raw gold instead of the LibreOffice-saved base kept
  5cfb9197, whose null mutant failed after three round trips; 215 mutants
  were evaluable in v2 and in v3 (the pinned code), with identical outcomes.
  Unaudited candidate checker errors: a z-order swap of non-overlapping
  shapes fails `compare_pptx_files` (2 tasks), dropped highlight passes
  `compare_docx_files_and_ignore_new_lines`, a deleted unrelated paragraph
  passes `compare_docx_tables`. Exploratory; never pooled with the
  confirmatory run.
- Target counts (no specs or checkers): 67 of 120 confirm tasks have a
  mutable gold file (68 targets). The preregistration draft
  `q2-evaluator-mutation-v1` now pins code tree, catalog, specs, splits and
  images, and K6 is resized to what 67 tasks allow. It awaits a second review
  before freezing. No confirm-split mutant was planned, built or scored.
