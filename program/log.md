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
  transliterated parts of unlicensed KernelGYM code (correction, 2026-10-13, D95: that
  version was pushed and is in public history as blob `63770654`, commit `b3e16d41`). b1 and b2
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

## 2026-10-07 — Q2 evaluator-mutation: first review answered (dev split, exploratory)

- The first adversarial review of `q2-evaluator-mutation-v1` found that an
  office candidate whose GUI-faithful save never ran was still scored on its
  pre-save bytes (and a gold could count for P1 unsaved). The merge now
  excludes such jobs (`save_failed`), and `unemulated` and `infra_timeout`
  are their own statuses. Also fixed: the rater packet is built from the
  operators' snapshot (the checker libraries hid highlight, colour, fills
  and spacing), the K3 bound is exact at the Kish effective size with a
  minimum audited size, unresolved rater disagreements count as label
  errors unless Kevin adjudicates them, the K2 plan opens agent-created
  outputs, the control path has the same freeze, pin and image guards as
  the mutation path, and the pins cover the probe map, file cache, OSWorld
  tree and VM baseline.
- Rerun at the new code (Slurm 475-480): `dev-mutants-v4` reproduces v3 on
  all 275 mutants (admission, status, event, verdict, both venvs);
  `dev-controls-v7` gives K1 19/19 and one P1 flip in 19.
- The draft now states that K6 is very unlikely to fire, reports P1 on the
  93 golds the headless probe saved as a replication, and restates power:
  after the probe exclusion only about 9 (P3) and 5 (P4) confirm tasks are
  expected, so P3 and P4 are pooled-only. The dependency-sensitivity arm is
  disclosed as not leaderboard-era. Still not frozen: second review and
  Kevin's D2/D9 confirmation pending.

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

## 2026-10-07 — Q2 evaluator-mutation: second review answered (third draft, not frozen)

- The second adversarial review of `q2-evaluator-mutation-v1` (55/100) found
  seven blocking defects. Fixed on `stage0/q2-evaluator-mutation` (main's
  six-row ledger and D1-D23 merged first): K3/K4 now use the two label
  classes that enter the metrics without an audit gate, with one
  consequence (the affected metrics leave the headline); a rater runner in
  the pinned tree (`rater_runner.py`: D23 raters, one call per item,
  transport-only retries, first-token rule, `unsure` for every non-answer,
  hashed receipts) plus audit packets (`audit.py`) and the registered
  headline analysis (`analysis.py`); a seeded K2 sample drawn before scoring,
  a closed list of explanations and the "offline harness, VM fidelity
  unverified" fallback; P3 counted at the code's cell-level rule (40 confirm
  tasks, not 11; K7 power corrected by simulation: 80% needs about 19% at 31
  tasks); the probe-informed operators probe-touched in code; P1 a
  replication on 92 save-exposed golds.
- Dev smoke of the open-weight rater (Qwen3.5-9B, vLLM cu129 overlay built
  at `ba840b4`, Slurm 566 and 582): 133 dev packets rated once each, all
  replies parsed, 0.110 GPU-h of its 0.2 cap (0.123 with the overlay
  build). Exploratory answers: do-nothing shams 6/6 rejected, gold shams 4/6
  accepted, equivalence mutants 35 accepted / 25 rejected, mostly over
  save-stage changes visible in the packet difference, so K3 may fire on
  confirm unless Kevin adjudicates. The Anthropic arm did not run: the API
  key in the agent environment returns 401.
- Dev reruns at the new code (`dev-mutants-v5`/`v6`, `dev-controls-v8`/`v9`,
  CPU only) reproduce v4 except 1-2 mutants per run lost to a UNO bridge
  fault (`applied`). v8 showed a spurious venv flip on a nondeterministic
  checker (9219480b), so S1 now confirms candidates at five fresh-process
  scorings per venv (`dependency_flips.py`).
- Not frozen: a third review, a working Anthropic key and Kevin's D2/D23
  sign-offs (prereg section 17) are pending. No confirm or reserve item was
  sampled, packed, rated, built or scored.

## 2026-10-07 — Q2 evaluator-mutation: third review answered (fourth draft, not frozen)

- The re-audit of the third draft (62/100) closed the second review's seven
  defects and found two blocking ones plus eight others. Fixed on
  `stage0/q2-evaluator-mutation` after merging main (D24, D25, the K1 probe
  ledger row): audit packets now compare an end state with the starting
  file saved through the same LibreOffice steps (UNO save then the
  GUI-faithful save stage for mutants and gold shams; the control run's
  saved do-nothing for P1 flips and do-nothing shams); violations are a
  census stratum, and the sampler and K3 rule were simulated at confirm
  scale (`integration/audit-design-v1/`: the violation group at 17 tasks
  fires with P 0.00 / 0.065 / 0.55 at 1 / 2 / 5% label error, against 0.60 /
  0.72 / 0.91 before; raters each right 90% fire the kappa rule in 0.11-0.27
  of replicates); P1/K6 over the confirm and reserve control runs in code,
  K1 confirm-only; the summary merges one calls file per shard and rater;
  a registered token budget fits packets to the 9B rater's window; non-JSON
  200 bodies are `unsure` and hashed, and the Anthropic receipt is written in
  `finally`; a K2-dropped family leaves P2-P5, which are recomputed; S1
  candidates unstable at five scorings are S5 and leave P2-P5; the D25
  agent-harness Claude rater path (`rater_runner export-harness` /
  `ingest-harness`) is registered with its disclosure; adjudication
  workload estimated at about 60-90 confirm items.
- Dev rerun of the audit with saved-start packets (Slurm 644, CPU) and of
  the open-weight rater (overlay 646, args doctor 647, lane job 650; 0.095
  GPU-h of the 0.15 allowed): 90 of 133 items rated before the lane's USR1
  checkpoint signal (180 s before the 8-minute limit). Save noise is gone
  from the packets (difference lines 21,842 to 7,705), but the rater's
  disagreement with labels barely moved (22 vs 24 of the 90 paired items);
  it rejects golds, e.g. 01b269ae's gold carries a zh-CN language and CJK
  default font that the saved start does not (a gold artifact, not the save
  stage as the first smoke read it). If Claude agreed with every label,
  kappa would be 0.48. Dev packets exported for the Claude rater (outside
  the repository); its answers, a fourth review and Kevin's sign-offs are
  pending. Not frozen.

## 2026-10-07 — Open-weight reviewer tooling: smoke reviewed, exit hung, fixed

- Built `scripts/run_open_weight_review.py` on branch
  `stage0/open-weight-reviewer` (not pushed): the D23/D24 provider-distinct
  reviewer, offline vLLM `LLM.generate` in the cu129 overlay, greedy, seed 42
  primary plus same-batch replicates 43 and 44, one retry with the parse error
  appended, a fail-closed JSON Schema subset, a receipt (model id, HF revision,
  model receipt digest, vLLM version, prompt and output SHA-256) and a lane
  manifest renderer. Default reviewer `qwen3.6-35b-a3b` at TP=1 (64.56 GiB of
  language-model weights fit one H100); the smoke used `qwen3.5-9b` because a
  35B-A3B job cannot fit the 0.1 GPU-h smoke cap.
- Overlay 614 (`f74084d`, image `f760b0fe`). Smoke 617 wrote a `PARSED`
  review 71 s after its container started (engine init 52.5 s, replicates
  token-identical), then hung in interpreter shutdown; its reset handlers let
  PID 1 ignore USR1 and TERM, the job ended TIMEOUT and the container held GPU
  0 for 88 s after the job until stopped by hand. Smoke GPU time 0.1075 GPU-h
  by Slurm, 0.1319 physical, over its 0.1 cap.
- Fix `37f4f2a` (handlers kept, bounded engine close, `os._exit`); overlay 629
  (image `eda72497`); CPU-only PID-1 checks in that image pass (hang scenario
  exits 0 in 1.3 s; USR1 and TERM end a generating run with exit 3 and the
  marker). The GPU re-smoke (`smoke2.yaml`, cap 0.1) is rendered and
  test-only passed but not submitted. Lane gap noted: a container whose
  workload ignores TERM outlives a timed-out job.
- GPU time 0.1589 GPU-h in all (two overlay builds 0.027). Evidence:
  `program/evidence/2026-10-07/open-weight-reviewer-smoke/`.

## 2026-10-07 — K1 v2 throughput probe and gauntlet wave 1

- The K1 v2 throughput probe (Slurm 543, PROBE_COMPLETE) put v2's caps plus
  the probe at 8.05 GPU-h under D22, so v2 went to the research gauntlet
  (D24).
- Gauntlet wave 1 (`program/gauntlet/2026-10-07-q3-k1-localization-screen-v2.jsonl`,
  proposal `program/proposals/2026-10-07-q3-k1-localization-screen-v2.md`):
  three discovery cells (about 157 orx queries, 35 full-text reads; novelty
  STILL_OPEN, no direct prior through 2026-10-07; SeerAttention 2410.13276 and
  A.X K2 2608.30181 added as uncited priors), blind discrimination passed,
  refute-first triad 3 of 3 refuted, reviews 45 (Claude) and 59 (Qwen3.6-35B-A3B,
  self-hosted, Slurm 640). Honest exit: triad stop plus query and token
  budgets. Doctor FAIL with the expected trust-store and compute issues.
- Decision D26: Q3 next runs a dense headroom pre-check under a new id.
- The open-weight reviewer tooling is merged; its smoke (Slurm 617) hung at
  vLLM teardown and overran its 0.1 GPU-h cap (0.11 by Slurm); a fix exists
  but is validated on CPU only. The lane leaves a container alive if Slurm
  kills the batch script at the time limit; to be fixed.

## 2026-10-07 — Action-path suite: development complete, one decision before the freeze

- Q2 Stage 0b (branch `stage0/q2-action-path`), development only (seed 42,
  never evidence), every job CPU-only through `vm-campaign.sbatch` with the
  VM in its own network namespace (D12, D13): jobs 482-637, driver exit 0
  for every job after 482, no GPU in any job's TRES, `System.qcow2`
  unchanged, no labelled container or volume left.
- Found and fixed in development: the compositor sometimes never painted the
  probe's last drawing (31 of 941 typing trials, 3.3%; L0-fixed now
  re-damages the top-level windows after each action, and 2,114 typing
  trials since showed none); a session's first XTest key changes the master
  keyboard device and stripped `chord_super_d`'s modifier (runs 549 and 574,
  the same sessions on 8 VMs and on one; every session now warms the
  keyboard up first); Chrome's outdated-build bubble (a launch flag); VS
  Code dropping its first keys while loading on a busy host (the canary waits
  until the app is idle); the boot's first `/accessibility` call answering
  500 (Stage 1's reset observation is reproduced; recovered retries are
  reported, not failures, as section 6.1 says).
- Found while writing the acceptance code: the concurrency ladder could never
  qualify a rung above N = 1 (18 sessions against 20 required boots); rungs
  now repeat the seed-43 order until every VM is busy. Added the acceptance
  analysis as code (`acceptance.py`), a manifest renderer that refuses
  before the freeze, and tests that freeze a scratch ledger to exercise
  admission; the repository ledger still refuses every acceptance campaign
  and seeds 43 and 44.
- Open, for Kevin before the freeze: the OSWorld guest server crashed once in
  7,969 `/accessibility` calls (thread-pool tree walk; systemd then stops
  everything it launched). A4 as registered (zero failures over 36,550
  accessibility calls) would pass with probability about 0.01; options in the
  inputs addendum's section 6. Writer once swapped a space and the emoji
  after it (1 of 336 Writer trials), reported.
- At the final runtime commit every in-spec cell of L0-fixed (one VM and 8
  VMs), H-OSW-fixed, H-GA and the canary passed in every repetition and
  setting (jobs 633-637); the stress and volume samples at `81fd5f3` (jobs
  618-622, 2,600 trials on 8 VMs) failed only in the one session the
  guest-server crash broke.
- The 44 scored mutants on their predicted kill cells (informative): 42
  killed, M12 and M13 on H-OSW-fixed unchanged (predicted equivalent).
- VM time from measured trial times (`vm_hours.json`): A4 44.0 VM-hours,
  all scored campaigns 67.3 VM-hours, CPU only.
- Nothing frozen. Next: Kevin's A4 decision, then the owner freezes
  `q2-action-path-v1`, `-inputs` and `-executor`; C2, then C1 and C3, then
  A1-A6 and the ladder.

## 2026-10-07 — Action-path suite: review of `2b492cd` answered

- An independent review found the branch not ready to freeze: C2's L0-raw
  prediction ignored the timing failures development had found (stale
  screenshots, chord releases losing their modifier state), so C2 would very
  likely have failed v1 for a reason unrelated to the names it tests; and the
  A4 guest-server decision was still open. Fixed at `30d8c7f` (registration
  section 17, design decisions 34-39): C2 is judged on the event and text
  channels (marker reported; key-release state not compared); C3 counts only
  clean kills against a clean reference; admission checks every file the
  frozen tables pin and refuses unpinned files; end states come from the
  batch script's own record or a Slurm watcher
  (`scripts/record_slurm_end_states.sh`), a campaign is rerun at most once and
  never loses its failures; an undelivered reset observation charges the
  session's first trial; ladder runner CPUs are registered; repair attempts
  name their executor addenda; `acceptance.py` is frozen with the inputs
  addendum, before C2 runs. Found while fixing: C2 could not have been
  submitted before the executor freeze, and a restart between two entries
  went untyped; both fixed.
- A guest-server restart now relaunches the tap with the probe. Development
  run 662 SIGKILLed the server after the tenth trial of each session: only
  that next trial failed (27 of 28 per session passed), against 55 trials
  charged in run 622.
- Final development runs at `30d8c7f` (seed 42, CPU only, COMPLETED 0:0,
  no GPU, `System.qcow2` unchanged): L0-fixed on one VM (663, 400 trials) and
  on 8 VMs (664, 800 trials), 200 of 200 cells each; H-OSW-fixed (665, fails
  only R03 and R09, outside spec); H-GA (666, fails only R02, R04, R06 and
  R10, outside spec); canary (667, 60 of 60).
- Recounted from the receipts: the guest server crashed once in 8,114
  `/accessibility` calls (the first count said 7,969); A4 as registered would
  pass with probability about 0.01, with a single-event 95% range of 0.89 to
  0. The A4 decision remains Kevin's (inputs addendum, section 6, options
  1-5). jinja2 is in the dev extra, so the template check runs.
- Nothing frozen, nothing pushed. GPU time 0.

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

## 2026-10-07 — Q1 Stage 0 second review fix pass: trimming rule /2 in code, pilot exposure registered (branch `stage0/q1-gates`, not merged)

- Merged main@36af438 (D22-D25; conflicts in this log and `state.json`, both
  sides kept; ledger 2.150 GPU-h). No GPU was used in this pass; host work ran
  in GPU-less, network-less containers of `cotcodec-q1-gates:5af03757` from a
  fresh clone of the branch.
- Verified all 13 findings of the second adversarial review of `@04c2934`;
  12 fixed, the c-lite one partly rejected (the ratio of medians has been the
  analysis code's statistic since before the pilot; it is now named in
  sections 5.5 and 12 with its interval, 1.64 (1.52-2.32), and the other
  readings, 2.11 and 2.38, reported). Evidence:
  `program/evidence/2026-10-07/q1-pilot/second-review-fix-pass.json`.
- Pilot exposure (D26): the pilot had scored five evaluation substrates, part
  of a sixth, eight mutants (three test) and ten controls. Listed and
  hash-bound (`harness/q1/data/pilot_exposed.json`); exposed mutants leave
  every sampling frame; a pre-specified sensitivity analysis drops every
  exposed unit; data-motivated audit changes drop the units they affect.
- `q1-stage0-trim/2` is code (`harness/q1/trim.py`, run by
  `scripts/run_q1_stage0.py`): seeded frames and samples, FRR set with a
  margin, per-kind control sample, buckets P1-P8, 12 capacity units per GPU,
  shared-item timeouts and CUDA out-of-memory errors retried alone, stop by
  Slurm job caps; `driver_sha256` in the version card. Criterion 5 amended
  for the unscheduled KBV H.1 and hack-emulating mutant controls (at least
  6.2 GPU-h to score at one replicate).
- Corrected projection (fidelity at its measured allocation, timing floor at
  its 8-GPU allocation, anchors for problems of 1 GB or more): 7.60 GPU-h
  through P3 and 10.99 through P7 centrally, 8.70 and 13.09 at the high point;
  the stop keeps the run under 8 (centrally P1-P3 complete, one margin unit).
  The pilot pass's /1 was 7.37 with lower charges.
- Also: TF32 identity timing bias 0.907 (0.886-1.044) reported; TF32
  convolution tolerance above 1 (L2/3 T = 2.67) recorded as finding 18.3.8;
  run records hashed (`run-records.json`), killed items recorded by the
  runner; sanitizer row memcheck-only; Apache-2.0 text with the Liger
  substrates that carry Unsloth code; D27 for upstream test code on GPUs.

## 2026-10-07 — Action-path suite and Q1 gate stack merged (not frozen)

- Merged `stage0/q2-action-path`: the 100-entry action-path suite, its
  device-level references, adapters, acceptance rules and three draft
  registrations. Final development runs (seed 42, CPU only) passed every
  in-spec cell for L0-fixed on 1 and 8 VMs, H-OSW-fixed, H-GA and the canary;
  42 of 44 suite mutants were killed and the two predicted-equivalent ones
  survived. Scored campaigns need about 67 VM-hours, CPU only.
- Merged `stage0/q1-gates`: gates (a)/(b)/(c), the independent audit,
  mutator, substrates, the trimmed Stage 0 driver and the pilot (Slurm 474,
  518, 548; 0.90 GPU-h). The pilot scored a few evaluation units before the
  freeze; D28 (branch D26) hash-pins and fences them. D29 (branch D27) admits
  pinned upstream benchmark test code on GPUs.
- D30: guest-server restarts are bounded separately from A4. D31: Q1 Stage 0
  gets an engineering pass and a non-evaluation re-pilot before admission.
- Full suite on the host after the merges: 1,681 passed, 28 skipped.

## 2026-10-07 — Lane: container lifetime bounded by the job

- Fixed the lane gap found by the open-weight reviewer smoke (Slurm 617) on
  branch `stage0/lane-container-lifetime`: `docker-research.sbatch` removed its
  container only from its exit trap, so a workload that ignored TERM outlived a
  timed-out job (Slurm's KILL, KillWait 30 s after TERM, skips every trap).
- The batch script now reads the time left (`squeue -o %L`, exit 2 if not
  finite or above the manifest minutes), SIGKILLs the container 30 s before the
  limit from a background timer (after USR1's 120 s checkpoint window), and on
  TERM waits at most KillWait minus 20 s (10 s here) for a `trigger=SIGTERM`
  checkpoint before `docker kill` and removal. A TERM before start starts no
  container; `docker create` gets `--stop-timeout`. `termination.env` adds
  `hard_stop_at`, `container_killed_by` and `container_killed_at`.
- Stub-docker tests: a container ignoring USR1 and TERM is killed before the
  job's end (hard stop) and within KillWait (TERM); all 8 new runtime tests
  fail against the previous script. No GPU time used.
- `vm-campaign.sbatch` (branch `stage0/q2-action-path`, not on main) does not
  have this gap: its USR1/TERM handler kills the driver and force-removes every
  job-labelled container without waiting on them.

## 2026-10-07 — Lane: container lifetime review fixes

- An independent review of the lifetime fix found one fail-open path and six
  smaller defects, all reproduced with stub-docker tests before fixing:
  - the hard-stop timer inherited `set -e`, so a failed `hard-stop.env` write
    (full or failing disk) ended it before its kill; it now runs `set +e` and
    the record is best-effort;
  - the timer looped forever after its kill, and outlived a batch shell killed
    alone; it now ends after its kill, and if the shell is gone it SIGKILLs the
    container at once (`cause=batch_script_gone`) and exits;
  - a requeued job reused its run directory and read the earlier attempt's
    records; the submitter passes `--no-requeue` and the batch script refuses
    an existing run directory (exit 2);
  - a TERM that killed the `docker create` client before it printed the ID
    leaked the container dockerd still created; the exit trap watches 5 s;
  - a TERM sent to the whole job reached the container through the attached
    client before the trap's marker record, so a TERM checkpoint never
    confirmed (also on main); the TERM record is now taken at container start;
  - a confirmed TERM checkpoint was SIGKILLed at once; it now gets the grace;
  - `docs/operations.md` overstated the hard stop: a workload must exit within
    150 s of USR1, and the hard stop does not follow `TimeLimit` changes.
- The q2 evaluator-mutation draft preregistration (other branch) sizes its
  rater stop on the 180 s USR1 lead; it needs a note on the 150 s bound before
  it is frozen. No GPU time used.

## 2026-10-07 — Q3 dense headroom pre-check built (D26), not run

- Branch `stage0/q3-dense-precheck`: draft registration
  `program/preregistrations/q3-dense-headroom-precheck-v1.md` (not frozen) and
  its code. Dense only, no indexer; the development partition of the K1
  bundle (`919d016b...`) only; two lanes, Qwen3-0.6B-Base (1 GPU x 9 min, cap
  0.15) and Qwen3.5-4B-Base (1 GPU x 21 min, cap 0.35), caps summing to D26's
  0.5 GPU-h. The 4B lane re-tokenizes the bundle's Qwen3 tokens segment by
  segment (needle spans exact) and reads its 8 full-attention layers.
- Measures H1 on MN, CX and ML (development literal prompts built with the K1
  builder's rule), H2a and H2b, a non-literal floor candidate, English entity
  anchors with the entity-controlled subset, a literal (lexical) selector and
  a block-score null (target log-scores plus noise, seeds 42/43/44) read with
  K1's xi and xi_rel, recall by tokenizer fertility, and a reproduction of K1
  smoke 452's dense numbers on the 0.6B lane. Lane decisions
  (NEGATIVE_CAPABLE needs H1_CX >= 20 with lower bound >= 10) and a combined
  read say which K1 v3 designs are viable.
- New modules beside the frozen K1 files (none edited):
  `harness/dense_headroom_{data,stats,torch}.py`,
  `scripts/run_dense_headroom_precheck{,_doctor}.py`,
  `scripts/fill_dense_headroom_precheck_manifests.py`,
  `scripts/summarise_dense_headroom_precheck.py`, lane templates in
  `experiments/manifests/q3-dense-headroom-precheck-v1/`.
- CPU doctor in the research image (`e59d9cc1`, network none, Slurm CPU
  steps): DENSE_DOCTOR_PASS, including both tiny lanes end to end, a SIGUSR1
  interrupt (exit 75 with the marker) and its continuation. No GPU time used.
- Waiting on Kevin: the draft's design decisions 1-14.

## 2026-10-07 — Q3 dense headroom pre-check: review fix pass (draft, not run)

- An independent review of the draft (`stage0/q3-dense-precheck` at 9f9e735)
  asked for changes before freeze; all nine findings were reproduced and
  fixed, with regression tests. Still a draft, still no GPU time.
- Continuations could never run: the entry point required the lane's full
  minutes. It now checks the job's kind from `manifest.json`: a fresh job (at
  most the lane's minutes, no checkpoints), or a continuation naming its
  predecessor with the batch script's resume receipt and the predecessor's
  pinned artifact (at most the lane's minutes minus two). A time-limit
  interrupt still leaves no room for one (SIGUSR1 comes three minutes early),
  so a lane that overruns ends INCOMPLETE; this is now stated.
- The combined read failed open on an INVALID lane; any INVALID lane now
  makes it INVALID, and the 4B lane is submitted only after the 0.6B smoke
  reproduction is REPRODUCED.
- D26's requirements of a K1 v3 (entity-controlled question set, non-literal
  floor, seen-script cross-script condition, new id and gauntlet) are always
  required; the measured flags only add. `anchor_confound` is renamed
  `lexical_confound` (the literal selector reads all lexical overlap), and the
  literal selector now drops the query language's stop ids as well as the
  needle language's.
- The floor candidate is VIABLE only when a V1-adequate null's 99 percent
  lower bound of G(MN) reaches 0.5. The null is CENTRED only if an adequate
  noise scale loses at least 2.5 points of English ML recall; the sigma grid
  is now 0.25 to 4 in steps of about 1.4 (9 scales, 54 null columns).
- Budget: every job of a lane (re-runs, the one continuation) is charged
  against the lane's minutes from the run root's `job.env` and
  `termination.env` timestamps; the filler claims each later job's slot in the
  run root once; no budget amendment is possible under this id.
- The lane templates and `scripts/preregister.py` are tabled; the filler
  refuses a filled manifest that is not the template with only its `FILL-*`
  values replaced. The summariser applies the void rules from each job's files
  and the saved orx logs and hashes receipts over their bytes.
- Waiting on Kevin: the draft's design decisions 1-15.

## 2026-10-07 — Q2 evaluator-mutation: third review of the fourth draft answered under D27 (fifth draft, not frozen)

- Review 3 of the fourth draft (56/100) found three blocking defects; D27
  answered them without relaxing the κ rule. On `stage0/q2-evaluator-mutation`
  (main's D26/D27 merged first):
  - `pptx.eq.zorder_nonoverlap` swaps a pair only when neither shape comes
    within 2 mm of the other or of any shape stacked between them (rotated
    frames widened, frameless shapes refused); `pptx.viol.delete_bound_shape`
    skips a shape 90% or more under the shapes above it. Synthetic
    revalidation (Slurm 684) as job 431; catalog `07e50a6f`; code tree
    `37ae60f0`. Dev rebuild `dev-mutants-v8` (Slurm 688-690; v7 lost two
    targets to a UNO bridge fault): all 17 targets, 275 / 271, clean save
    stage. The restricted swaps still fail `compare_pptx_files` on 8 of 9
    evaluable mutants (candidate checker false negatives, unaudited).
  - Open-weight rater upgraded to Qwen3.6-35B-A3B (image input confirmed on
    CPU with vLLM's own processor, Slurm 685/687); `rater_runner open` stops
    cleanly on the lane's signals and leaves with `os._exit`. Dev rerate
    (overlay 686, lane job 702): all 133 items of the new dev audit (Slurm 700)
    rated in one 6 min 56 s job that ended on its own; 0.128 GPU-h with the
    overlay. Shams 12/12, equivalence 57/60 accepted, but 19 of 26 violation
    mutants accepted: κ 0.27 if Claude matched every label, 0.34 against the
    earlier non-blind Claude answers. Unless the isolated Claude answers
    differ greatly, κ stays under 0.6 and the design returns to review (D27).
  - Isolated Claude rater: `export-isolated` / `ingest-isolated` (one
    directory per item, manifest outside, re-hash, model id and transcript
    audit from the harness transcript); the 133 dev items are exported
    outside the repository; their answers are pending. The label-bearing
    files of the rerate are held on the host until that ingest.
  - Minor items: K6 needs P5 in the headline and no K4 stop; the answers
    wrapper is accepted; duplicate or anonymous call records are refused; the
    rater GPU cap is read from a ledger; stale text fixed.
- GPU time 0.1284 GPU-h (program total 1.7558). Evidence:
  `program/evidence/q2-mutation/integration/rater-rerate-dev-v3/`. Not frozen.

## 2026-10-07 — Q2 evaluator-mutation: isolated Claude ratings ingested on the D27 dev rerate (κ 0.27, back to review under D27)

- 133 isolated Claude agents, one per dev item (workflow run
  `wf_2301520e-159`), each confined to its own directory under the isolation
  root. A strict transcript audit found 1,711 Read calls, all inside the
  agent's own item directory, and 133 StructuredOutput answers. No other
  tool was called and only claude-opus-5-5 appears: 0 voids. The registered
  `ingest-isolated` gave 133 `ok` and 0 `isolation_void`; every item tree
  re-hashed equal to its export. After the ingest, the held label files were
  released; their digests match the committed `held/SHA256SUMS`.
- Registered dev summary with both raters (121 real items, 12 shams, 1 P1
  flip): κ 0.270, below 0.6, so κ fires. Shams were 12/12 for each rater.
  Label error, with unresolved items counted as errors: equivalence 0.133
  (K3 bound 0.255) and violation 0.731 (5 tasks, too few for the bound).
  Both K3 groups fire, and K4 fires. 29 split items (24%; 26 of them are
  Claude reject / Qwen accept, mostly violation mutants), about 1.5-2.4 h of
  blind adjudication; 51 items with the spot check. Claude agrees with the
  labels on 112 of 121 real items, Qwen on 94. Isolated and earlier
  non-blind Claude answers agree on 93.6% of 109 matched items (κ 0.84).
- Under D27 the design goes back to review; the κ rule is unchanged.
  Evidence: `program/evidence/q2-mutation/integration/rater-isolated-dev-v3/`
  and `dev-mutants-v8/`. No GPU used. Not frozen.

## 2026-10-07 — Q2 evaluator-mutation: D34 retry implemented (sixth draft, thinking-on dev rerate, not frozen)

- Merged main (D28-D34, Q1 gates, action path, Q3 pre-check) into
  `stage0/q2-evaluator-mutation`; log, state, HANDOFF and SKILL conflicts
  kept both sides; GPU total recomputed from the ledger.
- D34 rules in code (`34046e0`): a gold sham for every task with an audited K3
  item and the gold-defect rule (a task whose gold sham is decided reject
  leaves its equivalence items out of the equivalence K3 group; labels stay
  relative to the gold; the analysis reports P2 without them as a
  sensitivity); Kevin's blind adjudication pool now also holds K3 items both
  raters decide against the label and split gold shams; new-file end states
  get a text-level difference against the starting files' text; shape
  position or size changes of at most 0.02 mm are counted, not listed;
  `pptx.viol.delete_bound_shape` skips shapes at least 50% off the slide;
  the registered transcript audit checks the rendered prompt, the answer's
  item id and that the packet was read, and its final-text fallback needs one
  exact answer word; item ids take a secret per-audit salt; the agent prompt
  template is committed (`harness/q2_mutation/templates/isolated_rater_prompt.txt`,
  SHA-256 `0e9d4eb6...`); the open-weight rater thinks (`max_tokens` 8,192,
  the model card's thinking sampling, seed 42, `max_model_len` 139,264).
- Dev rebuild `dev-mutants-v9` (Slurm 714-716) reproduced v8's counts (271
  admitted, 215 evaluable); revalidation Slurm 717 as before. Audit
  `dev-audit-v4` (Slurm 720): 142 items (15 gold shams, 9 added by D34), one
  455 MB shard, 51 new-file text differences, 5,833 drift changes counted.
- Thinking-on rater (overlay 718, doctor 719, lane job 722): all 142 items in
  12 min 57 s, 14.4 items per minute, clean exit, 0.228 GPU-h with the
  overlay. Violations 14 accept / 12 reject (thinking off 19 / 7); extra
  change 0 / 6; shams 20/21. κ 0.578 if Claude matched every label; 0.486
  against the D27 isolated Claude answers on 119 matched items (a
  projection; the packets changed).
- The off-slide rule does not reach the review's item afb440d9: it deleted
  shape 19, which is wholly on the slide; the 78% figure matches shape 20,
  now excluded. Shape 19 is deleted again in v9.
- Confirm rater cap re-registered at 3.0 GPU-h (841-item maximum about 2.2
  GPU-h at a 10 items/min planning rate); the experiment's total stays at
  most 4.52 GPU-h, under 8, so no gauntlet.
- 142 items exported for the isolated Claude rater (`q2m-iso-v5/`, manifest
  outside); answers, ingest and the salt's release are pending. Held on the
  host: sample, items, open-weight calls, v9 export (`held/SHA256SUMS`).
  Evidence: `program/evidence/q2-mutation/integration/rater-rerate-dev-v4/`.
  GPU 0.2281 GPU-h (program total 3.0108). Not frozen.

## 2026-10-07 — Q2 evaluator-mutation: isolated Claude ratings ingested on the D34 dev rerate (κ below 0.6; D34 (i) fires)

- 142 isolated Claude agents, one per dev item (workflow run
  `wf_65ce9899-24a`, labels `rate5:*`), started with the registered prompt
  template (`0e9d4eb6...`). The session ended once mid-run and the workflow
  was resumed: 16 labels have an interrupted agent and a completed rerun; the
  rating is the completed agent's. A strict transcript audit of all 158
  agents found 0 voids: 1,789 Read calls by completed agents and 165 by
  interrupted ones, all inside the agent's own item directory; 142
  StructuredOutput answers, each naming its item; no other tool; only
  claude-opus-5-5; every computed-task turn byte-identical to the rendered
  template in the fixed wrapper; no other item's id in any transcript; every
  item tree unchanged; answers equal to the journal results and the
  handed-over list. 40 of 142 agents were not shown every line of
  `packet.txt` (lowest 56%); all opened every page image.
- The registered `ingest-isolated` (`b29034e`) gave 32 `ok` and 110
  `isolation_void`: after the resume the workflow harness put a relay of the
  session user's request ("continue all work.") before each new agent's task,
  so the first user turn is not the rendered template. The registered rule
  is unchanged; registering the relay turn or requiring unresumed rating runs
  is open for Kevin before the freeze. A sensitivity ingest that does not
  count that one byte-identical turn as a prompt gave 142 `ok`.
- After the ingest the dev-audit-v4 salt was revealed (its SHA-256 matches
  the committed `1660a49d...`; all 142 item ids recompute from it) and the
  held files were released; all 18 match `held/SHA256SUMS`.
- Registered summary with both raters: κ 0.066 (driven by the voids). With
  the relay turn excepted: κ 0.575 (raw agreement 0.843), shams Claude 19/21
  and Qwen 20/21, P1 flip accepted by both; one gold defect (task
  `e528b65e`, 3 equivalence items out of the equivalence group); label error
  equivalence 0.070 (K3 bound 0.179 on 57 items) and violation 0.577 (5
  tasks, too few for the bound), so both K3 groups fire and K4 does not; 20
  of 121 real items unresolved (16.5%; 16 of the splits Claude reject / Qwen
  accept); adjudication pool 24 (20 splits, 3 concordant contradictions, 1
  split gold sham), 48 items with the spot check.
- D34 (i): development κ is below 0.6 either way, so no other rater is
  tried; P2-P5 leave the confirmatory headline before the confirm campaign
  runs, and the campaign reports P1 and the checker false-negative candidates
  descriptively. Evidence:
  `program/evidence/q2-mutation/integration/rater-isolated-dev-v4/` and
  `dev-mutants-v9/`. No GPU used. Not frozen.

## 2026-10-07 — D30 applied to the action-path registrations (not frozen)

- Branch `stage0/q2-action-path-d30` applies decision D30 before the freeze
  (main preregistration section 18). A4 does not count a trial whose only
  failure is a guest-server restart (with the tree it left undelivered); it
  reports every restart and the development rate (1 in 8,114 calls, exact
  95% interval 3.1 x 10^-6 to 6.9 x 10^-4).
- New criterion A7: at most 5 x 10^-4 restarts per accessibility call on the
  exact one-sided 95% Poisson bound, from a dedicated campaign (L0-fixed on
  G, 360 seed-43 repetitions, accessibility setting, 39,036 planned calls;
  pass at 12 restarts or fewer: probability 0.999 at the development rate,
  0.81 at half the bound, at most 0.05 at the bound). 31.1 VM-hours, CPU
  only; scored campaigns now total 98.4 VM-hours. It gates the
  screenshot-plus-accessibility setting and has no repair attempt.
- The probe and the tap start in their own systemd scopes (`systemd-run
  --user --scope`), outside `osworld.service`. Development (seed 42, CPU
  only): runs 694 and 703 killed the server inside and between entries; the
  probe and the tap ran on, only the entries hit failed, and the trial killed
  inside showed the restart alone. Final validation at `7653799` (jobs
  703-708) passed every in-spec cell, no restart in 1,070 calls
  (`program/evidence/2026-10-07/q2-action-path-stage0b/README.md`).
- Stage 1 counts restarts per episode as infrastructure failures.
- Left unchanged on purpose: A1-A3 and the ladder still fail on a restart;
  at the development rate their 16,639 accessibility calls see none with
  probability about 0.13. Kevin's call before the freeze.

## 2026-10-07 — Review fixes on the D30 branch (not frozen)

- An independent review of `stage0/q2-action-path-d30` at `13c6790` found it
  not ready to freeze; dispositions are in main preregistration section 19.
- Fixed in `acceptance.py` (`13ad91e`; the only code changed, and no
  campaign executes it, so the byte-identity check against `7653799` still
  holds): A7 sums the
  restarts of every attempt but divides by the counting attempts' calls only
  (pooling had let a cancel-and-rerun raise the pass probability at the bound
  from 0.048 to about 0.071 in simulation) and refuses an attempt other than
  1; the undelivered reset observation is charged as a reason as well as a
  type, and `restart_only` checks both; a restart across the reset
  observation that left only its tree undelivered is excused on A4's terms;
  the restart report names each hit trial's session and every session whose
  restarts hit no trial.
- Registered: A7 runs at attempt 1's N* after attempt 1's full ladder and is
  not re-judged when a later attempt's N* differs; A4's exclusion covers only
  restarts the observation retries absorb (about 10 s against a measured
  5.6-6.0 s), and the remainder is not sized.
- Corrected: A4 has 36,515 accessibility calls, not 36,550 (an earlier
  2026-10-07 entry and the inputs addendum gave 36,550); the probabilities
  do not change at the precision given. The boot-time restart precedes every
  session's first counter read in all 34 development sessions (the boot's
  facts read named the session's server process); its cause is not recorded.
- Still open for Kevin before the freeze: whether D30's exclusion extends to
  A1-A3 and the ladder.

## 2026-10-07 — Q1 Stage 0 engineering pass and re-pilot (D31)

- Branch `stage0/q1-engineering-d31` (not merged, not pushed). Reference store
  (`harness/q1/refstore.py`, `refschedule.py`): reference items compute the
  fp32 device, TF32, CPU fp32 and fp64 references, gate (c)'s validity gate and
  A5's reference calls once per problem, replicate and channel; consumers read
  the entry or compute inline. No registered quantity changed (plan hash
  untouched). The runner gained item requirements and per-item journals.
- Equivalence: identical rows on the doctor's synthetic corpus (except a kernel
  that reads unwritten memory, whose rows main does not reproduce either) and
  on the committed integration fixtures; a differential against main@47f5fbc
  agrees.
- Re-pilot `q1-repilot/1` (Slurm 713, image `:8e9d2574` from CPU-only build
  710; 0.330 GPU-h of the 0.5 cap): 8 S1-cal problems without evaluation
  units, 24 kernels, inline and store twins of every scoring item. 843 twin
  rows compared, 828 same verdict; every difference explained (inline cuDNN
  nondeterminism on L2/77, mutants A4 finds faulty, A4 probes, memory
  contention), none by the store.
- Cost: the store saves on gate c (42%), A1 (25%), A2 (17%), A3, A5; reference
  items cost about as much at in-scope sizes (store arm plus references 1.19x
  inline at three kernels per problem). Trim/2 high through P3: 8.81-9.85 with
  the store, 9.03 without, 8.56 at the bound of any store design. Stage 0 is
  not admitted under D31; it waits on the gauntlet (D24) or Kevin.
- Finding: at 12 units per GPU, 97 items on 3 of 8 problems (parameters and
  activations, not inputs) ran out of GPU memory in both arms, and failed
  health checks under contention retired 5 of 12 slots. The projections are
  lower bounds for such problems; a memory-aware unit rule is needed first.

## 2026-10-07 — Q3 dense headroom pre-check: D32 applied, design accepted with four amendments (branch `stage0/q3-dense-d32`, not frozen)

- Basis: the second fresh pre-freeze audit
  (`program/evidence/2026-10-07/q3-dense-headroom-precheck/prefreeze-audit-2.json`).
  Its one blocking defect is fixed: the registration's status paragraph now
  has the frozen wording (as K1 v1 and v2 had before their freezes), the
  design-decision lead-in says the decisions were accepted in D32, and freeze
  step 1 includes this rewrite. The registration test accepts either wording
  until the freeze; once frozen it requires `Status: frozen` and a D32 that
  names the experiment id.
- D32 (`program/decisions.md`, on main at `7229df1`): decisions 2-9, 11, 14
  and 15 accepted as drafted (decision 5's H2 relaxation explicitly); 1, 10,
  12 and 13 amended. This branch applies it to the registration and code.
- Decision 1: both lanes run unless the 0.6B smoke reproduction fails. The
  filler now refuses the 4B lane without `--small-lane-receipt`, a completed
  0.6B receipt of this registration whose `smoke_452_reproduction` is
  REPRODUCED. Freeze step 4 now says the read is INCOMPLETE, not INVALID,
  when the 0.6B lane ends without a receipt (as the combined rule computes).
- Decision 10: the floor's condition (c) counts only nulls that meet decision
  8's reach rule (V1-adequate, seed-mean English ML loss at least 2.5 points),
  through one shared `reaching_sigmas` used by the null verdict too.
- Decision 12: every job, the first included, takes an exclusive fill claim;
  each filled manifest is submitted once. A job is matched to its claim by its
  `manifest.json`; a lane with a job without a claim, a job over its claim's
  minutes, or two jobs on one claim is void in the summariser, and the filler
  fills no further job of it. The entry point cannot check claims (its
  container mounts only its own job directory), so the summariser is the
  backstop. The useful window (limit minus the 3-minute SIGUSR1 lead) is 6
  and 18 minutes; `MIN_JOB_MINUTES` is now 5.
- Decision 13: text only; only Triton's cache moves to the run directory.
- Digests changed: `harness/dense_headroom_data.py`,
  `harness/dense_headroom_stats.py`,
  `scripts/fill_dense_headroom_precheck_manifests.py`,
  `scripts/summarise_dense_headroom_precheck.py`. The entry point, torch
  module, doctor, templates and the seven imported rows are unchanged; the
  entry point's import closure still equals its `CODE_FILES`.
- Checks on the Mac, CPU only: the whole suite 1757 passed, 79 skipped
  (host-only and torch tests); all dense test files 107 passed in an offline
  scratch environment with torch 2.11.0 and transformers 5.15.0. The CPU
  doctor reads DENSE_DOCTOR_FAIL in the default environment (no torch: the
  selectors, multiple-choice and end-to-end cases) and DENSE_DOCTOR_PASS, all
  seven cases, in the torch environment. A freeze into a scratch copy of the
  ledger verified, with the status line `Status: frozen`; the real ledger is
  untouched. No GPU time, no host access.
- Next: freeze (steps 2-5). The binding doctor run is still the one in the
  image built from the freeze commit.

## 2026-10-08 — Q2 evaluator-mutation: D35 applied (seventh draft, a descriptive protocol; not frozen)

- Basis: the fifth review (64/100; scores 55, 62, 56, 57, 64) and decision
  D35 on main (`64591fd`). Main merged first (`ba1e24e`): `log.md` kept both
  sides, HANDOFF takes main's refresh with the checker-mutation bullet
  updated, and the branch's `ledger.jsonl` equals main's (7 rows,
  check-chain PASS). GPU total from the ledger rows: 3.0108 (unchanged).
- (i) `analysis.D34_DEV_EXIT` always takes P2-P5 out of the confirmatory
  headline ("D34 (i): development kappa below 0.6"); K6's adequacy claim is
  retired (always blocked), K6b and K7 are descriptive, K4 is reported and
  stops nothing. A test ties the constant to the recorded dev summary
  (κ 0.0663 registered, 0.5752 relay excepted).
- (ii) `analysis.checker_candidates`: false-negative candidates (evaluable
  should_pass_equiv and should_pass_alt_solution mutants outside probe cells
  that the checker fails) and false-positive candidates (evaluable
  should-fail mutants it passes), each with its audit decision and reading
  and its task's gold-defect flag; counts and task-equal shares with the
  task-cluster bootstrap pooled, per label, family and operator; confirmed
  shares when every candidate was audited.
- (iii) `raters.draw_audit_sample` is a census of the candidate events, P2's
  gate, the shams (a gold sham for every audited task) and the P1 flips;
  above the 3.0 GPU-h cap's capacity at the planning rate
  (`raters.audit_capacity`, 1,139 items) a seeded stratified sample over
  candidate type × checker family (`raters.allocate`), disclosed in the
  sample summary (`audit_scope`). Dev-scaled expectation: about 205 items,
  0.62 GPU-h planned; adjudication pool about 16 items (10-40), 0.5-3.5 h.
- (iv) `rater_runner.audit_transcript` checks every user turn: one rendered
  template, and only the harness relay frame (`RELAY_PREAMBLE`, once, before
  the task turn, no item id) besides it; `ingest-isolated` reads every
  transcript of an item (`{item}.jsonl`, `{item}.<agent>.jsonl`, several
  directories), allows one to answer, voids items with a relay frame when
  the run's frames differ (unanswered items' transcripts included) and
  records the relay digests in each call and the receipt. The fifth review's
  probe (a later user turn naming the item's label) now voids. The relay
  frame and its dev content are disclosed in section 9. Dev is not
  re-ingested: the registered κ 0.066 stays as recorded. A scratch-only check
  ran the new audit over the 158 dev transcript copies (format check, nothing
  written): no void reason, one relay digest (`8e7dbd00`) in 110.
- (v) `rater_runner.packet_parts` puts the differences before the listings
  (label-blind, disclosed as postdating the dev results).
- Minor: `render_rater_manifest` takes the lane memory per model (160 GiB for
  Qwen3.6-35B-A3B) and the cap from `raters.AUDIT_GPU_HOURS`; sections 6, 9,
  10, 13, 15 and 17, the status note, state.json (Q2 pending decision and
  next action, D34 ledger outcome) and HANDOFF refreshed; review log added.
- Checks: ruff clean; local Q2 tests 349 passed, 17 skipped; host full suite
  at `1e42036` (fresh scratch copy, `uv sync --locked --extra dev`): ruff
  clean, 2085 passed, 34 skipped; freeze-lint into a scratch copy of the
  ledger (equal to main's): freeze, verify and check-chain (8 rows) pass,
  registration SHA-256 `fe94a301215626c84da4bca0db97c92b404341abcf669a73c679643e018de56b`.
  Records in `program/evidence/q2-mutation/integration/d35-protocol/`. No
  GPU, nothing pushed or frozen.
- Next: a fresh review of the seventh draft, Kevin's sign-offs (section 17),
  re-merge main, freeze.

## 2026-10-08 — Q2 evaluator-mutation: sixth review answered (eighth draft; not frozen)

- Basis: the sixth review of the seventh draft (80/100, not ready to freeze;
  scores 55, 62, 56, 57, 64, 80, lowest 55), one blocking defect. The
  transcript audit read user turns only from entries of type `user`. The
  agent harness also writes attachment entries, and a message sent to a
  running agent (a user prompt, another agent's message, a task
  notification) arrives as a `queued_command` attachment. The review's probe
  (template, Read of `packet.txt`, a queued prompt naming the item's label,
  `StructuredOutput`) returned no void reason, nor did an `edited_text_file`
  attachment or a `system` or `progress` entry carrying a user message.
- Fix (`1242da7`): `rater_runner.audit_transcript` treats any entry whose
  message has the role user as a user turn, whatever its entry type, and
  registers the entry types user, assistant and attachment
  (`TRANSCRIPT_ENTRY_TYPES`) and the fifteen attachment types of the 158
  D34 development transcripts (`HARNESS_ATTACHMENT_TYPES`). Any other entry
  or attachment type (`queued_command`, `edited_text_file`, `nested_memory`,
  `file`, a `queue-operation` entry and so on), a line that is not an entry
  object and a user entry without a message void the item, with a reason
  naming the type. The audit returns the count of every attachment type;
  `ingest-isolated` records it per transcript and for the run, and the
  receipt lists the registered types. Tests cover the probe and the other
  channels, plus an ingest in which a queued prompt voids the answering
  transcript; a prereg test checks that section 9 names every type.
- Rerun over copies of the 158 dev transcripts (scratch only, nothing
  ingested): no void reason, 3,304 attachments, all of the fifteen types,
  none outside the list, one relay digest (`8e7dbd00`) in 110. The
  registered dev result (κ 0.066) stays as recorded.
- Registration (eighth draft): status note (item 4 and a sixth-review
  paragraph), section 9 (the rule, and the fifteen types beside the D34
  injected-context disclosure: checked by type only, fail closed if a
  harness version adds a type), section 17 (the review's minor items listed
  as open, the sign-off, the review log). Code-tree pin `d50be4df`. Harness
  README and SKILL, HANDOFF and state.json updated.
- Not changed (the review's minor items, open for Kevin and a later pass):
  the stratified fallback's budget is not maximal as coded; transcript
  collection from the workflow directory is unregistered; relay identity is
  not checked across several calls files at `audit summarize`, and the
  relayed text is kept only as a hash; concordant contradictions reach the
  pool only for the K3 candidate kinds; a second resume with another
  request voids every relay-frame item; stale K2 wording in section 10.
- Checks: ruff clean; local Q2 tests 351 passed, 17 skipped;
  validate_architecture_experiments, validate_provider_models and
  check-chain pass; host full suite at `1242da7` (fresh scratch copy,
  `uv sync --locked --extra dev`): ruff clean, 2087 passed, 34 skipped;
  freeze-lint into a scratch copy of the ledger (equal to main's, 7 rows):
  freeze, verify and check-chain (8 rows) pass,
  registration SHA-256
  `b8011fc9af23fcf96f6afe1b857154b09a1dd166523b050326275756b3e7de1f`.
  Records in `program/evidence/q2-mutation/integration/d35-protocol/`. No
  GPU, nothing pushed or frozen. Main has moved to `5e9e1f7` (D36, the Q3
  pre-check operated); its ledger still equals the branch's.
- Next: a narrow re-check of the eighth draft, Kevin's sign-offs (section
  17), re-merge main, freeze.

## 2026-10-07 — D33 applied to the action-path registrations (not frozen)

- Decision D33 (`program/decisions.md`, on main at `7229df1`) settles the
  question D30 left open: A1-A3 and the concurrency ladder excuse a trial
  whose only failures are a guest-server restart during an observation call
  and the tree it left undelivered (or the same fault across the reset
  observation), as A4 does; a restart during `/execute` or a guard still
  counts. Applied on `stage0/q2-action-path-d30` (main preregistration
  section 20, design decision 44).
- A1-A3 judge an entry on its counted repetitions; an excused trial alone
  never makes it FLAKY, and a second excused trial in one entry fails it
  (`RESTART_LIMIT`). The limit is counted over both observation settings,
  every attempt and, in A1, both shuffles, because D33 says an entry "needs
  all but at most one of its repetitions counted"; the working brief's
  "per setting, per campaign" reading would let an A1 entry lose 4 of its 20
  repetitions and was not adopted. Flagged for the owner to confirm at the
  freeze (state.json); the pass probabilities differ by under 10^-4.
- A ladder rung reads "every gating trial passes" over its counted gating
  trials and does not qualify with more than two excused trials over its
  attempts (an aborted attempt aside); excused trials' steps stay in the
  step p95; the foreign-load abort is unchanged. Every excused trial is
  listed in its criterion's restart report.
- A7's rules from `13ad91e` match D33; its call count is now capped at the
  plan's 39,036. Found while applying D33: an earlier attempt's failures had
  counted on every cell, so an outside-spec R cell's expected failure in an
  earlier A2 attempt would have failed every rerun; they now count only on
  judged cells, less excused trials.
- Exposure (section 9): no restart is no longer a pass condition for A1-A3
  and the ladder (it had probability about 0.13 at the development rate).
  Some A1-A3 entry reaches its limit with probability 0.004 at the
  development rate (0.015 at half A7's bound, 0.057 at the bound); some rung
  exceeds two excused trials with 0.013 (0.083, 0.37), the N = 40 rung 0.007
  (0.044, 0.21). Restarts outside an observation call or slower than the
  retries stay unsized; D33 accepts them.
- Code: `acceptance.py` only (`3ad255a`, with its tests), which no campaign
  executes, so the byte-identity check against `7653799` still lists only
  `harness/q2/README.md` and `acceptance.py`; both addenda carry its new
  digest. The D33 loader re-read development runs 694 and 703-708: the only
  status change is `chord_ctrl_c` in 694 and 703 (killed inside in both
  sessions of each run), FAIL to `RESTART_LIMIT`, still a failure; read as a
  rung, their gating failures drop to `drag_short` alone (the trial after
  the between-entry kill). 704-708 are unchanged.
- Checks at `4831a87`: the Q2 tests on the Mac, 279 passed; on the host, from
  an rsync of the worktree (`uv sync --locked --extra dev`), ruff clean and
  the whole suite 1,846 passed, 34 skipped. Freezing the three drafts into a
  scratch copy of the ledger verified with the chain intact (SHA-256 v1
  `9d885227`, inputs `5d257de7`, executor `2c26e7b4`); the repository ledger
  is unchanged (7 rows).
- Nothing is frozen and nothing is pushed. No GPU, no VM job.

## 2026-10-07 — Correction to the D33 entry's re-read of runs 694 and 703 (not frozen)

- The entry above says that, read as a ladder rung, the gating failures of
  development runs 694 and 703 drop to `drag_short` alone. They do not. The
  re-read script skipped entries with no counted trial, but the rung rule
  (`acceptance.rung`) does not read a gating entry with no counted trial as
  passing. Both of `chord_ctrl_c`'s trials in each run are excused, so the
  gating entries not PASS stay `chord_ctrl_c` and `drag_short` (recomputed on
  the host with `rung`'s own reading at `acceptance.py` `cb38018d`). Its two
  excused trials are within a rung's limit. A scored rung cannot reach that
  case: each entry runs at least 12 trials and at most two may be excused.
  Main preregistration section 20, item 8, now says this, and lists the
  reset-observation test of `4831a87` among the tests. Every other re-read
  result stands.
- The main draft's SHA-256 is now `683626ec` (it was `9d885227` in the
  entry above); a fresh freeze of all three drafts into a scratch copy of
  the ledger verified with the chain intact, and the repository ledger is
  unchanged (7 rows). No code changed.

## 2026-10-07 — Fixes after the review of the D33 pass (not frozen)

- The review of the D33 pass (head `59bd551`) found two defects in
  `acceptance.py` and one wrong number; fixing them found a third defect.
  All are fixed before the freeze with no scored data (main preregistration
  section 21, design decision 45).
- Validity controls after a rerun: C1-C3 counted every failed trial of an
  earlier attempt, so the by-design failures of C1's known-defect cells,
  C2's predicted set and each mutant's kills made any rerun of a C1-C3
  campaign fail its control (the mechanism D33's pass fixed for A2). Each
  control now reads an earlier attempt by its own rule: C1 counts a
  known-defect cell that passed in any attempt, never its failures; C2
  counts an earlier failure only outside the predicted set, read by
  `c2_trial_pass`; C3 reads kills and equivalence from the counting attempt,
  reports each earlier attempt, and a cell the reference did not pass
  cleanly in any attempt cannot kill (`a3ee335`).
- Rung without host snapshots: `foreign_abort` returned "no host snapshots"
  and `rung` read it as a foreign-load abort, dropping that attempt's gating
  failures and excused trials and allowing a rerun that could qualify.
  Section 9 registers two abort reasons only. Now an attempt missing any
  session's snapshots does not qualify and may be rerun, and its trials
  count (`snapshot_problems`, `a3ee335`).
- Found while fixing: C4 read the counting A1 attempts only, though it
  judges the tap's stream, which A1 does not judge for probe-observed
  entries; it now reads every attempt (`c9b4771`).
- Corrected number: the per-setting, per-shuffle reading of D33's limit was
  said to change the pass probabilities by less than 10^-4 (also in the D33
  entry above). Recomputed independently, it lowers the probability that
  some A1-A3 entry reaches its limit by 8.1 x 10^-5 at the development
  rate, 3.3 x 10^-4 at half A7's bound and 1.25 x 10^-3 at the bound (A1
  only; rungs unchanged). Section 9, design decision 44, section 20 item 2
  and state.json now say this.
- No issue rejected; the two control findings were the same defect.
- Checks at `4619666`: each new test fails on the `acceptance.py` before it;
  the reviewers' probes now give the registered outcomes. Q2 tests on the
  Mac, 284 passed. On the host, from an rsync of the worktree into a fresh
  `~/cotcodec-scratch/` directory (`uv sync --locked --extra dev`), ruff
  check clean and the whole suite 1,851 passed, 34 skipped. The loader read
  development runs 694 and 703-708 read-only: every session has its host
  snapshots, so the snapshot change alters nothing there (each still reads
  as foreign load, as before: the host ran other campaigns and users' jobs).
  `acceptance.py` is still the only code file changed since `7653799`
  besides `harness/q2/README.md`; no lane file imports it. Both addenda pin
  its digest `ced21d32`. Freezing the three drafts into a scratch copy of
  the ledger verified with the chain intact (SHA-256 v1 `4e41abe0`, inputs
  `aaceb3e8`, executor `ef074616`); the repository ledger is unchanged (7
  rows).
- Nothing is frozen and nothing is pushed. No GPU, no VM job.

## 2026-10-07 — The D33 reviews' remaining notes closed before the freeze (not frozen)

- Merged main (D34, D35) into `stage0/q2-action-path-d30` (`6c5915d`), and
  again after main moved on (D36 and the Q3 pre-check's operation,
  `e643aec`, below this entry); the branch's ledger and decision log equal
  main's (7 rows, chain PASS). The Q3 entries of `state.json` are main's:
  this branch changed none of them, and the second merge brought main's
  update of them.
- Wording (main preregistration section 22): the excused reason set shows a
  restart during or after the entry's observation calls, before its post
  guard, and excusing the latter is harmless because every action had
  completed (section 6.1); "every rerun" where sections 6.1, 12, 20 and
  design decision 44 mean reruns, with section 6.1 defining an attempt as a
  run within one repair attempt; A1 at N* is read from the rung under the
  rung's rule (two excused trials per rung), A1 at N = 1 allows one per
  entry (sections 6.1, 7); section 20 item 2 states D33's per-entry reading
  plainly, as D33's author confirmed, and the pending item for it is gone
  from `state.json`; A5 stays judged on the counting attempts' receipts,
  with earlier ones reported (a killed job can leave labelled containers by
  design); a failed `squeue` in a host snapshot reads as no foreign load and
  cannot be detected (the snapshot keeps neither the exit status nor the
  job's own row; checked on runs 694 and 703-708), stated in section 9 as a
  known limitation.
- `acceptance.py` (`2518241`): reports, not judged, per section 12:
  `entries_over_restart_limit` lists every entry with two or more excused
  trials whatever its status, with its excused repetitions; A4's
  `restart_only_trials` counts every rerun; under a repair attempt A4 gives
  its restarts per accessibility call against A7's bound
  (`repair_restart_rate`); A5 lists earlier attempts' receipts. Found while
  closing the A5 note: `load` opened `receipt.json` unconditionally, but
  the driver writes it last, so a killed attempt (runs 695-699 have none)
  could not be read at all. It is now read from its manifest, its batch
  record (`job_id=`) and its finished sessions, and does not count (design
  decision 46).
- Checks at `56b0738`: each new test fails on the `acceptance.py` before
  it. On the Mac, the Q2 tests with the preregistration, VM-campaign and
  Holo3 tests, 349 passed; ruff check and format clean on the changed
  files. On the host, from an rsync of the worktree into a fresh
  `~/cotcodec-scratch/` directory (`uv sync --locked --extra dev`), ruff
  check clean and the whole suite 1,856 passed, 34 skipped, at `56b0738`
  and again at the merge `e643aec` (another fresh directory). The final
  loader re-read runs 694 and 703-708 read-only next to the previous one
  (`ced21d32`): nothing changed but the
  new list's form (`chord_ctrl_c` in 694 and 703 listed with status
  `RESTART_LIMIT` and its two excused repetitions); runs 695-699, which the
  old loader could not read, read as CANCELLED attempts with no finished
  session. `acceptance.py` is still the only code file changed since
  `7653799` besides `harness/q2/README.md`; no lane file imports it. Both
  addenda pin its digest `0f476864`, and all 85 frozen-table digests match.
  Freezing the three drafts into a scratch copy of the ledger, at
  `56b0738` and again at `e643aec`, verified with the chain intact (10
  rows; SHA-256 v1 `1001591d`, inputs `98a4bc53`, executor `05829878`, the
  same at both); the repository ledger is unchanged (7 rows).
- Open for the orchestrator: the three drafts' status lines still read
  "DRAFT. Not frozen." (D32 had the Q3 draft's line rewritten before its
  freeze).
- Nothing is frozen and nothing is pushed. No GPU, no VM job.

## 2026-10-08 — Q3 dense headroom pre-check operated (freeze steps 3-5, branch `ops/q3-dense`): INCOMPLETE, no combined read

- Registration `q3-dense-headroom-precheck-v1` (ledger row `94520a99`,
  freeze commit `a369e6d`). Evidence:
  `program/evidence/2026-10-08/q3-dense-headroom-precheck/` (README, operator
  log, receipts, claims, orx logs, Slurm records, summariser output).
- Step 3: a fresh clone of main at `a369e6d` on the host passed
  `preregister.py verify` and `check-chain`, and all 17 tabled digests. Image
  build Slurm 723 (CPU only): `sha256:60e8d442...`, source tar `fc386fae...`.
  CPU doctor Slurm 724 in that image (`--network none`, no GPU, the image's
  baked source): DENSE_DOCTOR_PASS, 7/7, code digests equal the table.
- Step 4, Qwen3-0.6B-Base: filled on the host (slot-0 claim), dry-run and
  test-only passed, submitted once by orx node `7c344837` (commit `38cf069`,
  ssh backend) as Slurm 727: COMPLETED 0:0 in 278 s, provenance PASS,
  ORX_RESULT exit 0. Receipt `PRECHECK_COMPLETE`; K1 smoke 452 REPRODUCED
  (gaps below 1e-6 points). Lane NOT_VIABLE: H1_CX 12.25 (99% lower bound
  8.98), H2a 31.43, H2b -3.93 (`h2_status` FAIL); lexical confound, entity
  control and null calibration NOT_EVALUABLE; floor NOT_VIABLE; fertility
  STRONG.
- Step 4, Qwen3.5-4B-Base: filled with `--small-lane-receipt` (slot-0
  claim), dry-run and test-only passed, submitted once by orx node
  `51d32d53` (commit `c84c9aa`) as Slurm 730: FAILED 137:0 at its 21-minute
  limit. It evaluated 18 of 74 chunks at about 61 s each (GPU idle when
  sampled, one CPU core busy), did not act on SIGUSR1 (two chunks saved after
  it, no marker) and was killed by the hard stop
  (`signal_USR1_checkpoint_timeout`). The filler refused a re-run (-1 of 21
  minutes left; the job is charged 22) and a continuation (no confirmed
  checkpoint). The lane is void and INCOMPLETE.
- Step 5: the registered summariser exited 2 on the 0.6B receipt ("the
  receipt's Slurm job is not its job directory"): the entry point records
  `SLURM_JOB_ID` from inside the container, the batch script never passes it,
  and the summariser requires the field. Not a registered void rule; no code
  was edited. Under the registration's rule the combined read is INCOMPLETE
  (the 4B lane has no receipt); it was not written, and no base, K1 v3 design
  or stop is read.
- GPU time: 0.4189 GPU-h used (727 0.0772, 730 0.3417), 0.4667 charged under
  the registration's rule; ledger rows use the physical figures, as earlier rows do, with the charged figures noted. Jobs 723 and
  724 CPU only.
- Decision for Kevin (pending in `program/state.json`): whether and how a
  successor id runs. It would need the receipt's Slurm job id bound, the 4B
  lane sized from the measured rate, and SIGUSR1 handled on the 4B path.

## 2026-10-07 — Q1 D31 review fix pass: memory-aware execution, contention-safe health check, store narrowed (branch `stage0/q1-engineering-d31`, not merged, not frozen)

- Main (D32-D35, the Q3 dense pre-check freeze) merged into the branch; the GPU
  total equals the ledger sum (2.7668 GPU-h). No GPU was used in this pass.
- Review of `@f7373aa` (not ready to freeze; D31 verdict computed as
  registered). Every finding was checked against job 713's journals, reference
  journal and the store's use records, and reproduced: 97 shared out-of-memory
  items, 93 never final, 5 slots retired; A5's `na` path dropped the
  reference's out-of-memory text; 10 of 13 failed reference items left
  permanent unusable entries (37 of 189 lookups fell back inline); the pilot
  size model under-predicts the re-pilot's own inline items x1.72 (x0.95
  without L2/59, L2/87, L2/100); 124.6 GB written to the store; the
  references-free bound used the post hoc ratio (9.08 with the pre-specified
  one). One correction to the record: L2/46 was cut after 21 items (10 twin
  pairs), not left unstarted.
- Execution policy `q1-stage0-exec/2` (`harness/q1/memory.py`, meta-device
  `memory_table.json`): units per item from estimated (or measured) peak GPU
  memory with gate profiles, never below the old native-input rule; a
  free-memory guard before an item starts; the runner records each worker's
  peak memory. Health check: a failed check drains the GPU and repeats alone;
  only a failure alone stops the GPU (`gpu-health-fault`, `gpu-memory-held`).
  One resource-failure list (`faults.py`, cuBLAS/cuDNN allocation included).
- Store: gate (a) is no longer a consumer (gate_a.py back to pre-D31); a raised
  reference makes the entry unusable; a resource failure writes no entry and
  is retried alone while consumers wait; input fingerprints per draw (A5 per
  reference call); gate (c) replays skipped reference forwards on a mid-item
  fallback; no tensors for unusable entries; entry cap 50 GB, live cap 400 GB,
  tensors deleted after the last consumer. The documented residual difference:
  a candidate that changes process-global state at import is judged against a
  clean reference by c and A1-A5.
- Projection through P3 (`fixpass/projection-fixpass.json`): the registered
  table reproduces; store without gate (a) 9.15 high (pre-specified), 8.76
  (post hoc); under `q1-stage0-exec/2` (model-based) 10.46 central and 12.31
  high without the store, 11.10 high at the references-free bound. The exec/2
  model predicts the re-pilot's items at x0.81 of measured cost. **D31 verdict
  unchanged: not admitted**; Q1 waits on the gauntlet (D24) or Kevin.
- Exposure ledger entry for job 713 (`repilot-713-exposure.json`): 24 S1-cal
  kernels, no evaluation unit. Registration sections 2.1 (version card), 10,
  18.7 items 6-7, 18.8 and new 18.9 updated.
- Checks: host (rsync of the worktree into a fresh scratch dir, `uv sync
  --locked --extra dev`): full suite 1834 passed, 37 skipped; `ruff check .`
  passes. Every `tests/test_q1_*.py` in a CPU-only, network-less container of
  image `cotcodec-q1-gates:8e9d2574` (CPU-only Slurm steps, no GPU requested;
  KernelGYM and KBV clones mounted read-only): 402 passed. A first container
  run found two test faults, both fixed: the integration test still passed
  0.899 spent hours (now refused by the ledger guard), and the equivalence
  comparison was sensitive to the static checker's set order (a hash-seed
  effect, not the store's). The new tests fail without the fixes (checked by
  disabling the gate (c) replay and A5's per-call check).
- Waiting on Kevin: sign-off of `q1-stage0-exec/2` and the store policy, the
  budget path, D14 findings 18.3 items 6-8, D28/D29.

## 2026-10-08 — Q2 evaluator-mutation: D38 applied (ninth draft; the sixth review's minor items fixed; not frozen)

- Basis: decision D38 on main (`5231846`): the eighth draft's choices
  accepted as implemented, the sixth review's minor items fixed before the
  freeze. Main merged first (`f0e6d35`): `log.md` kept both sides,
  `state.json` keeps main's entries for the other questions (the resolved A4
  pending decision stays removed) and the branch's Q2 entries, and the GPU
  total is recomputed from the 16 ledger rows (3.7597 = main's 3.1857 plus
  the branch's four checker-mutation dev rows, 0.5740); HANDOFF takes main's
  version with the checker-mutation bullet updated; the branch's
  `ledger.jsonl` equals main's byte for byte (7 rows).
- Code (`58435c3`): the stratified fallback searches for the largest mutant
  budget that fits (`raters.stratified_sample`; the review's synthetic pool
  fills 300, 500 and 700 exactly, budgets 227, 417 and 608, where one
  subtraction stopped at 251, 462 and 672); concordant contradictions of
  every stratum join Kevin's pool (the dev census pool stays 4 of 50, the
  D34 audit's pools stay 24 and 113); `rater_runner collect-transcripts`
  maps every `agent-*.jsonl` of the rating run to its item by its rendered
  task turn, refuses one it cannot map, an unstarted agent and a started
  agent without a transcript, copies byte-exact and writes a collection
  manifest that `ingest-isolated --collection` checks (missing, changed or
  unlisted transcripts refused); an attempt without a journal result answers
  only through StructuredOutput; the receipt records each relay frame
  verbatim (digest only if it names an item); `rerate.json` lists items voided
  only for differing frames, `export-isolated --rerate-list` exports them
  for one fresh, unresumed re-rate, and `audit summarize --rerate-list
  --rerate-calls` writes the re-rated summary beside the registered one;
  `audit summarize` refuses calls files with different relay frames. Tests
  for each.
- Registration (`e6cdbd7`, ninth draft): status note items 6-12, sections 4,
  9, 10 (K2 no longer has K6 reading P5), 14, 16 and 17 (D38 checklist item;
  Kevin's remaining items: the pool, the spot check, outward actions and the
  carried-over sign-offs). Code-tree pin `50edcc45`; catalog unchanged.
  `rater-isolated-dev-v4/README.md` no longer calls the relay question open
  (its SHA256SUMS refreshed).
- Checks: locally ruff clean and the Q2 tests 356 passed, 20 skipped
  (module-level torch skips); on the host (fresh
  `~/cotcodec-scratch/q2m-d38-e6cdbd7-20261008065436`, `uv sync --locked
  --extra dev`) ruff clean and the full suite 2124 passed, 37 skipped. The
  collector and audit over copies of the 158 dev transcripts (scratch only):
  all 158 mapped, layout equal to the hand copies file for file, no void, 142
  answering, one relay digest in 110; the whole run (with its non-rater
  agents) is refused. Freeze-lint on a scratch ledger copy: freeze, verify,
  check-chain PASS (8 rows); registration SHA-256
  `0a01f424e9a83357b107c948e915c7b6448848cc9ea55175e1d52f24b34fd27c`.
  Records in `program/evidence/q2-mutation/integration/d38-fixes/`. The older
  host scratch directories `q2m-d35-*` are removed. No GPU, nothing pushed or
  frozen.
- Next: a narrow re-check of the ninth draft, Kevin's remaining items
  (section 17), re-merge main, freeze.

## 2026-10-08 — D39 applied to the action-path registrations (not frozen)

- Merged main (D37-D39, the Q1 D31 engineering pass) into
  `stage0/q2-action-path-d30` (`a367b7a`): `log.md` keeps both sides;
  `state.json` takes main's Q1 and Q3 entries and pending-decision list,
  with the branch's Q2 entry (the action-path freeze item stays resolved by
  D30, D33 and D39); `HANDOFF.md` is main's with the action-path bullet
  brought up to date; the ledger and `decisions.md` equal main's (7 rows,
  `01e0220e`, chain PASS).
- `acceptance.py` (`280ccbf`), decision D39 on the final pre-freeze
  verifier's finding: a C3 mutant is equivalent only if its counting
  attempt's stream signature equals the reference's and every earlier
  attempt's does on each cell it ran without an infrastructure failure;
  kills stay the counting attempt's. Each earlier attempt reports its
  differing cells and the cells left out for an infrastructure failure.
  `load` reads a receipt, cycle or record file that does not parse as
  missing (an empty receipt, a session not run, a session without host
  snapshots), lists it under `unreadable`, and the attempt does not count.
- Text (`e565cb2`, `578131d`; main preregistration section 23): sections
  6.1, 8 and 12 and design decision 45 state both rules; section 12's
  per-rung excused count reads over every rerun that did not abort
  (aborted attempts' counts in `earlier_attempts`); sections 20 and 22 and
  design decision 44 point to D39 for the confirmation of D33's per-entry
  reading, and section 21 points to section 23. The three status lines
  have the frozen wording (the ledger row, the freeze order v1, then
  `-inputs`, then `-executor`, and what may not run before the row), and
  `tests/test_q2_prereg_inputs.py` requires it. Both addenda pin
  `acceptance.py` at `39c59210`; the inputs addendum has a section 5 row
  for `280ccbf`, and the executor addendum's sections 7 and 9 name D39.
- Checks: both new tests fail on the previous `acceptance.py` (the
  verifier's probe reads equivalent; the loader raises on a record cut
  inside a multi-byte character). Mac (worktree `.venv`): the Q2 tests
  with the preregistration, VM-campaign and Holo3 tests, 351 passed; ruff
  check and format clean on the changed Python files. Host, fresh
  `~/cotcodec-scratch/` directories (rsync without `.venv` and `.git`, `uv
  sync --locked --extra dev`): ruff check clean and the whole suite 1,890
  passed, 37 skipped, at `e565cb2` and again at `578131d`. The final loader
  re-read runs 694 and 703-708 and the cancelled 695-699 read-only, next to
  the loader at `ae2a6d7`: nothing changed but the new `unreadable` list,
  empty in every run; all 996 receipt, cycle and record files in the 124
  development run directories parse. All 85 frozen-table digests (20 main,
  34 inputs, 31 executor) match; `git diff --stat 7653799 HEAD` over
  `harness/q2`, the sbatch and the submitter lists only
  `harness/q2/README.md` and `acceptance.py`, and no file imports
  `acceptance.py`. Freezing v1, then `-inputs`, then `-executor` into a
  scratch copy of the ledger at `578131d` verified with the chain intact
  (10 rows; SHA-256 v1 `ab0a5139`, inputs `ca7cadf7`, executor
  `a9f97469`); in a scratch clone frozen step by step, only A5 is admitted
  after v1, C2 after `-inputs`, and every scored campaign after `-executor`
  except A7 under attempt 2. The repository ledger is unchanged (7 rows).
- Nothing is frozen and nothing is pushed. No GPU, no VM job.

## 2026-10-08 — Q2 action-path validity controls operated (branch `ops/q2-action-path`): C2 FAIL, suite invalid for v1

- Scored from a `git archive` export of `a9948ee` (the commit recording
  ledger rows 8-10; tree digest `dec80447`), extracted read-only to
  `~/cotcodec-runs/q2-action-path-v1/src/` on the host. The manifest came
  from the frozen renderer and was then moved to the v1 host root: only
  `source.host_dir` and `run_root` changed, and it was re-validated with the
  ledger. The renderer hard-codes the development root; this is recorded
  as a deviation in the evidence README.
- C2 (job 768): L0-raw, 100 entries x 5, seed 42, screenshot setting,
  N = 1, CPU-only. It ended `COMPLETED` 0:0 by the watcher and the batch
  record alike and counts: gates passed, `System.qcow2` unchanged, nothing
  left, no infrastructure failure, retry or restart. `acceptance.c2`
  (frozen, `39c59210`) gives FAIL: every one of the 8 predicted entries
  failed 5 of 5, and `chord_super_d` failed 5 of 5 unpredicted. Its `d`
  press reached X without Mod4, within 1 ms of the Super_L press sent by
  `pyautogui.hotkey('winleft', 'd')`. C2's rule leaves out the modifier
  state of key releases only, not of presses. Section 5 as written would
  also have failed `chord_alt_f4`, `chord_alt_tab` and
  `chord_ctrl_alt_shift_r` (release state) and marked two typing entries and one sequence entry
  FLAKY (stale markers); C2's rule excuses both, as registered.
- Under sections 8 and 11 the suite is invalid for `q2-action-path-v1`. A
  failed validity control is not repaired within v1, and the campaign
  counted, so it cannot be rerun. C1 and C3 were not run: their 49
  manifests were rendered on the host and never submitted. No acceptance
  campaign ran. A corrected prediction or C2 rule can only enter a new
  preregistration.
- Evidence: `program/evidence/2026-10-08/q2-action-path-acceptance/`
  (manifests as rendered and as submitted, receipt, batch and Slurm
  records, the verdict JSON, the campaign summary, the SHA-256 of the 49
  raw files left on the host, and the operator scripts). 0.17 VM-hours, no
  GPU. Nothing pushed or merged.

## 2026-10-08 — Q1 D37 (iii): the validation job under `q1-stage0-exec/2` (branch `stage0/q1-exec2-validation`, not merged, not pushed)

- Rule `q1-exec2-validation/1` registered before the job (preregistration 18.10,
  commit `23a8768`; `harness/q1/exec2_validation.py`, driver
  `scripts/run_q1_exec2_validation.py`, pre-specified analysis in the evidence
  folder): the re-pilot's 24 S1-cal kernels (job 713's artifact, unchanged), all 15
  gates through the store (gate (a) inline), and the three KernelBench adversarial
  controls on the store's consumer gates with inline twins; adversarial first, then
  the re-pilot kernels in rounds by ascending exec/2 model cost; 10-minute box, items
  started until 330 s, killed at 390 s. Section 2.1 unchanged (the job ran the card's
  gate, audit and driver code).
- Finding before the job: the three adversarial kernels call
  `load_inline(name="fast_matmul")` with different sources and share the container's
  extension directory, so concurrent items can load each other's library; the rule
  chains them. Stage 0's plan runs them concurrently and needs the same fix (owner's
  call).
- Image `cotcodec-q1-gates:23a87683` from CPU-only build 746 (fresh clone); CPU check
  in the image reproduced the plan (433 items, `633b2753...`). Recorded `squeue` and
  `nvidia-smi` (idle node), dry-run, test-only, one submission: Slurm 752
  `COMPLETED 0:0`, 393 s, **0.1092 GPU-h** physical (cap 0.1667; D31's 0.5 now 0.439).
- Safety where it ran (122 items, all final; 1 cut at the hard deadline; 310 never
  started): no GPU resource failure, contention retry, failed health check, slot or
  device retirement, memory-guard wait or A5 `na`; largest concurrent measured peak
  24.2 GB; measured peaks at most 1.12x their estimate (gate c on L1/1 and L1/10).
  Covered 12 and 2 items per GPU only: L2/87, L2/100, L2/46, L2/59's consumers,
  identity controls and mutants not reached. 64 of 65 items also in job 713 kept
  their verdict rows; L2/59 `A4_poison` went from a 713 reject (`CUDA error: invalid
  argument` under the poison allocator, not in the resource-failure list) to accept.
- Adversarial controls: all 15 consumer-gate aggregates equal through the store and
  inline (`result_reuse`, `zero_out` rejected; `non_default_stream` accepted by c,
  A1-A3, A5 `error` in both arms because A5 cannot copy a candidate holding an
  extension module). Rows differ only for `result_reuse` (allocator history): inline,
  gate c accepted 7 of 16 configurations by reusing the freed reference output; the
  store arm rejected all 16.
- Cost: measured GPU-seconds are 2.425x the exec/2 model over the 87 re-pilot items
  (1.96 on one-unit items run during the adversarial CUDA compiles; 6.35 on L2/59 at 2
  per GPU, whose 4.3 GB of parameters the input-sized model misses). Projection with
  this job in the fixed part, central / high: model 10.57 / 12.41 (no store) and
  10.77 / 12.69 (store) through P3; **primary (store model x R) 19.99 / 24.66 through
  P3, 31.89 / 40.10 through P7**; 11.68 central through P3 at R's bootstrap lower
  point. D31 verdict unchanged: Stage 0 not admitted.
- GPU ledger row added (Stage 0 spent 1.3381); two tests that pin the ledger value
  updated. The analysis script's adversarial grouping was fixed after the job (it
  grouped by row gate and missed gate c's `c1`-`c3` rows); post hoc regime split and
  exposure entry written after the data. Evidence:
  `program/evidence/2026-10-08/q1-exec2-validation/`.

## 2026-10-08 — Q1 Stage 0 gauntlet wave 1: score 45, honest exit (branch `gauntlet/q1-stage0`, not merged)

- Wave 1 under D37 (workflow `wf_fcfd5ed9-8a8`) on proposal
  `program/proposals/2026-10-08-q1-stage0-gate-validation.md` (`7f4d080b...`,
  commit `7af2f57`). Audit row 1 appended to
  `program/gauntlet/2026-10-08-q1-stage0-gate-validation.jsonl`, row hash
  `836c7e7d3820736d0d24a48f56271adbced541e4a34757d208cfceef8eaf4d42`.
- Reviews: 47 (claude-opus-5-5) and 45 (qwen3.6-35b-a3b, self-hosted, Slurm
  775). Both totals equal their dimension sums and sit below every cap (74,
  79, 89). Score 45, best 45. Neither review is signed (D24).
- Blind discrimination passed under the rule: same mechanism, proposal judged
  stronger. The pass is weak, because the proposal's paragraph omits the
  registered TF32-admissible policy. Refute-first triad: 3 of 3 refuted
  (novelty: trivial recombination of MtC, CGV and Correctness Illusion;
  identification: execution-arm confound; feasibility: the 8 GPU-h stop falls
  inside P1). The doctor gives FAIL as expected (Novelty, Design and Compute
  FAIL; trust store; known parser quirks, including `gpu_hours=0.5` read as 0).
- Largest defect (F1): the audit metric cannot separate a correct TF32 matmul
  or convolution from a destroyed output. In job 713 the correct L2/46
  Inductor conv substrate scores e = 0.8275 on admissible draw A2/uniform8,
  equal to the reference's own TF32 error, against e = 0.999 for all zeros.
  The recorder checked this against the journal. A threshold-only D14 fix is
  therefore excluded on stored data.
- Honest exit. The query budget is used: 149 of 150 discover calls (the
  recorder recounted from transcripts; the feasibility refuter ran one
  unrecorded duplicate). A compliant wave 2 needs at least 18 more. The triad
  also stopped the candidate. Tokens 5.95M of 8M (conservative counter),
  $87.16 of $150 list-price equivalent, 123 of 600 minutes.
- GPU: reviewer 2 job 775 used 0.0572 GPU-h, added to the ledger as
  "Q1 Stage 0 gauntlet wave 1 open-weight review". The name does not start
  with `q1-stage0`, so the Stage 0 spend in `trim.stage0_spent_gpu_hours`
  stays 1.2289 (ledger test passes). The validation job 752 (0.1092 GPU-h) is
  on `stage0/q1-exec2-validation`. Merging both branches conflicts trivially
  at the ledger end and the total; the resolved total is 3.3521 GPU-h.
- Waiting on Kevin: D14 and the audit metric (normaliser); a GPU allowance for
  an S1-cal repair pilot (at most 0.1 GPU-h, pass rule written first); a
  successor gauntlet with fresh budgets (six queries per refuter and
  reviewer); the Stage 0 cap or a re-scope with the FRR core first. The Q1
  status line in `program/state.json` was left unchanged to avoid a merge
  conflict with the validation branch; update it at merge.

## 2026-10-08 — Q2 evaluator-mutation: the narrow re-check's minor items fixed (ninth draft; not frozen)

- The narrow re-check of the ninth draft scored it 90/100, ready to freeze,
  with no blocking defect (review log, prereg section 17; the lowest score
  stays 55). Its minor items are fixed on `stage0/q2-evaluator-mutation`
  without changing a registered choice.
- Merges of main: `6c4160b` (D39 in `decisions.md` only) as `0c6fe4f`, then,
  because main moved during the pass, `a9948ee` (the action-path branch
  merged and q2-action-path-v1, -inputs and -executor frozen) as `88bd376`.
  `log.md` keeps both sides; `state.json` takes main's action-path
  next_action with the branch's checker-mutation sentence and keeps the
  branch's GPU ledger (16 rows, 3.7597). The ledger equals main's (10 rows,
  SHA-256 `e7d20178`). Nothing under the checker-mutation code-tree roots
  changed on main.
- Code (`de24e23`): `rater_runner.check_rerate_list` recomputes a re-rate
  list's items from the calls file it names (the records whose only void
  reason is the relay mismatch, `relay_rerate_items`, which the ingest uses
  too) and refuses a list that differs; `audit summarize --rerate-list` uses
  the Anthropic calls file the list belongs to, `export-isolated
  --rerate-list` the `calls.jsonl` beside the list. `collect_transcripts`
  copies into a staging directory beside the output and renames it into
  place only when every copy checks, so a refusal leaves nothing behind.
  New tests pin the "only void reason" rule (ingest, summary, export), the
  journal's refusals (an agent started twice among them) and the staged
  collector. The harness README's pool row now says concordant
  contradictions of every label class (D38).
- Registration (`a8ea642`): the status note records the re-check and its
  fixes; section 9 registers the recompute check and says that a resume
  with a different relay frame puts every relay-voided item in the
  registered pool, on top of the normal pool (113 items against 24 on the
  development analogue); section 17 checks the re-check, logs its score and
  carries the same sentence in Kevin's item. Code-tree pin `58bee019`;
  catalog unchanged.
- Checks: ruff clean; the Q2 tests locally 358 passed, 20 skipped. Nine
  targeted mutants of the fixes, each on a `git archive` copy of `88bd376`,
  are all killed, the re-check's survivors M7 and M14 among them. Host,
  fresh `~/cotcodec-scratch/` directories (rsync without `.venv` and
  `.git`, `uv sync --locked --extra dev`): at `a8ea642` 2,126 passed, 37
  skipped; at the merge head `88bd376` 2,181 passed, 37 skipped and 1
  failed, main's own action-path test that still asserts no ledger row for
  the registrations main has now frozen (it fails on main `a9948ee` too).
  Freeze-lint on a scratch copy of main's ledger (10 rows): freeze, verify,
  check-chain PASS (11 rows); registration SHA-256
  `f62362b8f49e20fdca161b55c8b37c861785bdd6711d853713eaabca701f78e5`.
  Records in `program/evidence/q2-mutation/integration/d38-recheck-fixes/`.
  No GPU, nothing pushed or frozen.
- Next: Kevin's remaining items (section 17), re-merge main, freeze.

## 2026-10-08 — Q2 action path v2 drafted under D40 (branch `stage0/q2-action-path-v2`)

- `q2-action-path-v2`, `-inputs` and `-executor` are generated from v1's
  frozen text with D40's three changes and nothing else (main section 24;
  v2's frozen tables equal v1's except the rows it names, and a test checks
  it): `l0_raw_prediction_v2.yaml` lists `chord_super_d` as a failure and
  says it is informed by v1's C2 (job 768); C2 is a reproduction test on its
  own order seed, 45, which no v1 campaign or development run used
  (`order.py` builds it and `manifest.py` admits it for C2 only), and v1's C2
  is reported as the a-priori result (section 25); the manifest renderer
  takes `--host-root`, with no default and the development root refused.
  Every other realized order equals v1's code's, digest for digest. L0-raw
  is admitted in development at seed 42 so the mechanism can be
  characterised. v1's ledger rows and files are unchanged.
- Development (seed 42, CPU-only `vm-campaign.sbatch`, jobs 784-787 at
  `e66bf16`, 1.0 VM-h, all COMPLETED 0:0 with gates passed): L0-raw failed
  `chord_super_d` 10/10, the `d` press 1-2 ms after Super_L recorded with
  state 0. Only the four chords GNOME Shell grabs failed (each event after
  the grab-activating key recorded with state 0, without even NumLock's
  Mod2); the nine others, at the same speed, passed 10/10 with every state
  right. mutter 42.9 grabs synchronously, so the X server queues the next
  key, and RECORD reports a queued event before its state is computed. The
  shell still received Super+d: under L0-raw the desktop was shown and no key
  reached the probe in 15/15 trials, as under L0-fixed in 30/30. So the
  failure D40 records is in the tap's record, not in delivery. L0-fixed
  (10 ms between presses) passed `chord_super_d` 127/127 with the warm-up
  across v1 and v2 development (upper 95% bound 2.3% per trial); its only
  failures were runs 549 and 574 before the warm-up, the same artifact.
  Raised with Kevin as a pending decision (state.json); no rule changed.
- Merged main (112 commits since `124573a`, including ledger row 11,
  `q2-evaluator-mutation-v1`); no file a v2 table pins changed there.
  Freeze-linted v2, then `-inputs`, then `-executor` against a scratch copy
  of the merged ledger: the three rows chain onto row 11, the chain checks at
  14 rows, and every Q2 registration verifies. In a scratch tree frozen step
  by step, A5 is admitted after v2, C2 at seed 45 after `-inputs`, and C1,
  C3, A1, the ladder and A7 after `-executor`; C2 at seed 42 and a repair
  attempt without its addendum never are. The repository ledger is
  unchanged. Q2 tests pass locally (603 passed, 1 skipped) and the full
  suite on the host from a fresh scratch directory (2210 passed, 38
  skipped). Nothing frozen, pushed or merged to main. No GPU.

## 2026-10-08 — Q2 action path v2: D40's stated cause corrected (D43), review fixes

(The branch first numbered its draft decision with the number main then gave to
Q3's dense pre-check; main recorded this correction as D43, which supersedes the draft:
D43 corrects D40's cause the same way but changes the judge instead of accepting the
exposure. The references below read D43; where they describe the draft's own choices
they say so.)

- Review blocker 1: v2's main registration said in section 8 (C2), section
  24 item 2 and section 25 that v1's C2 failure was "verified real at the X
  event level", which its own sections 4.4 and 26 contradict. Those three
  places now say what was recorded (the tap's `d` press at core state 0,
  without Mod4, in every repetition) and that section 26 shows this is how
  RECORD reports a key event queued during the shell's synchronous grab,
  and that the shell received Super+d. Section 24 gains item 9, section 26's
  closing paragraph says what the decision decides and leaves, and section 4.4 says
  why the limit can fail a delivered chord and never makes a trial pass (on
  the four shell-grabbed chords every reference event after the
  grab-activating key has a modifier state that is not empty). No rule,
  number or frozen file changed; every pinned digest is unchanged, and the
  main file's own digest (its ledger row at the freeze) is new.
- Review blocker 2: D40's premise ("a genuine transport defect") is
  contradicted by the branch's evidence. The draft of D43, recorded on this
  branch under a new 2026-10-08 heading, states the corrected cause and decides that
  D40's three changes and L0-raw's development admission stand, that v2
  keeps the oracle's reading of events queued under a grab, and that the
  remaining L0-fixed exposure (127/127, 2.3% bound per trial; A1, A2, A4 and
  the ladder) is accepted, with reasons and a reversal; D40 carries a
  pointer to it. D40's author confirms or overrules the draft at the merge, and v2
  is not frozen before then. HANDOFF's v1 row no longer says the loss is
  real at the X event level; `state.json` and the pending decision for
  Kevin now name D43 and leave him the later-registration question.
- Tests: `tests/test_q2_prereg_inputs.py` checks the corrected wording in
  sections 8, 24 and 25, that no v2 registration or the v2 prediction file
  calls the failure real at the X event level, that D43 exists, keeps D40's
  changes and is cited, and that the four shell-grabbed chords' reference
  states after the grab key are never empty. No VM job, no GPU, nothing
  frozen, pushed or merged to main.
- Checks at `32d083c`: freeze-linted v2, then `-inputs`, then `-executor`
  against a scratch copy of the ledger (main file `a39d1b4d...`, inputs
  `14466f5e...` and executor `b624d20e...` unchanged); the three rows chain
  onto row 11, the chain checks at 14 rows, and v1's and v2's rows verify.
  The step-by-step admission simulation on an export of `32d083c` admits
  the same campaigns at every stage as before (nothing before the freeze;
  A5 after v2; C2 at seed 45 after `-inputs`; 72 of 83 cases after
  `-executor`, with every negative case refused). The repository ledger is
  unchanged (11 rows). Q2 tests 610 passed, 21 skipped; full suite 2167
  passed, 84 skipped; ruff clean.

## 2026-10-08 — Q3 dense pre-check v2 built and timed (D36; branch `stage0/q3-dense-v2`, draft, not frozen)

- Registration `program/preregistrations/q3-dense-headroom-precheck-v2.md`
  (DRAFT): v1's Data, Selectors, Metrics and statistics, Decision rules and
  seeds sections carried verbatim except two named substitutions, v1's
  decisions 1-11 and 13-15 verbatim, decision 12's caps amended; "Changes from
  v1 (D36)", v1's outcome (INCOMPLETE; job 727's receipt `bfe4a7c3...`), a
  26-row code table (v1's and K1's rows equal their frozen registrations'),
  new decisions 16-21 awaiting acceptance. Templates under
  `experiments/manifests/q3-dense-headroom-precheck-v2/`.
- Job binding: receipts take `job_id` from the run directory's `job.env`
  (written by the unchanged batch script before `docker create`); the
  summariser requires source `job.env`. A Linux test runs the real batch
  script against stub host tools, writes v2's and v1's receipts in the
  container environment and feeds them to v1's `check_job` (v2 accepted, v1
  refused as in job 727). Live: Slurm 766's receipt is bound to 766.
- SIGUSR1: Triton's LLVM `RegisterHandlers` replaces CPython's OS-level
  handlers at the first kernel compile and swallows SIGUSR1; `getsignal`
  does not see it. v2 blocks SIGUSR1/SIGTERM from process start (when the
  entry point runs as the program) and consumes them at chunk boundaries.
  Verified: doctor `usr1_displaced`, the entry point as a container's PID 1
  with a real Triton compile (images 770 and 776: v2 exit 75 with marker, v1
  exit 0 without), and Slurm 766 (`signal_USR1_checkpoint_confirmed`).
- CPU bottleneck: not the cache copy (5 ms per unit) or the selectors
  (43 ms). torch 2.11 sends Qwen3.5's head-dim-256 attention to cuDNN, which
  builds a graph per new sequence length (about 0.7 s of CPU per forward,
  GPU idle). Fix on the hybrid lane only: `enable_cudnn_sdp(False)`, the one
  change not bit-equal (reported per receipt by `attention_backend_check`,
  not gated; no v1 4B number exists). Every other evaluation change is
  bit-equal to v1 (unit tests, doctor `equivalence`, `end_to_end` with
  tolerance 0, and two real 4B units in Slurm 766). The 0.6B lane is
  unchanged and must reproduce job 727 to 1e-6 and smoke 452 (gate in the
  filler and summariser).
- Timing job Slurm 766 (image `3f2cc537...` from `71dc954`, CPU-only build
  763): 205 s, 0.0569 GPU-h physical (5 minutes charged); 2 of 8 subset
  chunks, cold units 3.6-4.1 s; ended by Slurm's SIGUSR1 with a confirmed
  checkpoint. It ran before the cause was known, so the fixed 4B path is
  untimed: its limit (45 min) applies D36's rule to twice the warm-unit
  projection (0.52 s x 1,160 + 5 s). 0.6B 12 min from job 727's 278 s.
  Registered caps 1.05 GPU-h of D36's 1.5.
- Checks: CPU doctor 12/12 in images 763, 770 and 776 (`e6e81e7`, Slurm
  778). Host suite at `e6e81e7`: 1,824 passed, 36 skipped, 1 failed (the
  Linux-only binding test's workload program did not start; fixed in
  `50153d0`, then passed). Main merged into the branch (`30f9c7c`; no tabled
  file changed on main). Host suite at `f2510dd` (Slurm 788, fresh scratch):
  2,212 passed, 40 skipped, 0 failed; the torch-dependent dense tests inside
  image 776 (CPU): 43 passed. Freeze simulated on a scratch clone of
  `f2510dd` only: chained onto main's ledger head (`dc39bfa2...`),
  check-chain 12 rows PASS, entry code table no differences, 0.6B fill ok,
  4B fill refused without the small-lane receipt, dry run ok, full suite in
  the frozen clone 2,165 passed, 87 skipped (macOS). The real ledger is
  unchanged.
- State: Q3 `stage-0-precheck-v2-draft`; ledger row 0.0569 GPU-h; program
  total 3.983. Evidence
  `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/`.
- Next: Kevin accepts or amends decisions 16-21 and the limits (and whether
  the fixed 4B path is timed first); then merge and freeze steps 2-5.

## 2026-10-08 — Q3 dense pre-check v2: review fixes (branch `stage0/q3-dense-v2`, draft, not frozen)

- A review found six blocking issues, all real, none needing a GPU job;
  limits, caps and computed quantities unchanged. Fixed at `b8977d9`.
- The 4B lane's cuDNN switch (decision 18) changes computed quantities, so it
  departs from D36 (iii): decision 18 retitled; decisions 18 and 19 say the
  job-727 gate and smoke 452 do not cover the 4B attention backend and the
  descriptive `attention_backend_check` is the only check; v1's carried
  "same code" wording is qualified in decision 18 (kept verbatim).
- The 4B limit is projected, not measured: job 766 ran the path before the
  fix (cuDNN on), and the fixed path has never run on a GPU. Decisions 20
  and 21, Compute, Changes item 6, the lanes module (`LARGE_LANE_PROJECTED`,
  `large_lane_break_even_unit_s`: about 2.1 s per unit) and the 4B template
  say so. No GPU job: the timing allowance has 1 of its 6 minutes left
  (766 charged 5), below the 5 any job needs.
- Freeze step 1 now rewrites the design-decision lead-in as well as the
  status; in frozen mode the prereg test refuses draft wording and requires
  the status and lead-in to name a decision after D36 that names the
  experiment and amends D36 (iii). Simulated on scratch clones: the
  registered procedure passes (check-chain 12 rows PASS, 26 frozen-mode
  tests, fills and dry run as before); the old status-only procedure and a
  wrong decision both fail the test.
- Checks at `b8977d9`: host suite 2,213 passed, 40 skipped, 0 failed; image
  801 (CPU build), doctor 12/12, torch tests in the image 52 passed, PID-1
  SIGUSR1 test passed. Evidence `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/README.md`
  ("Review fixes").
- Next (Kevin): one decision that accepts or amends decisions 16-21 and the
  limits, amends D36 (iii) for the 4B lane (or requires another fix), and
  either amends D36's timing rule for the 4B lane or authorises a second
  timing job of the fixed path (at most 0.1 GPU-h, a fresh timing run root);
  then freeze with that decision named in the status and the lead-in.

## 2026-10-08 — Q2 evaluator-mutation: confirm campaign stage A1 (K1, P1, confirm mutants; CPU only)

- Operator run of the frozen `q2-evaluator-mutation-v1` (ledger row 11,
  frozen on main at `65bc2e2`), branch `ops/q2-mutation-confirm`, evidence
  `program/evidence/2026-10-08/q2-mutation-confirm/`. Source: a `git archive`
  of `65bc2e2` staged under the Q2 run root; every pin of the frozen block
  matches it locally and on the host (code tree `58bee019`, catalog
  `3a5ff949`, the mounted OSWorld tree and VM baseline), and
  `check_frozen.py` and `campaign guard` passed in every run.
- K1 (first step after the freeze; `confirm-controls-v1`, Slurm 781-783):
  70/74 under the lock-exact venv (94.6%, 90% required): PASS. The four
  misses are raw-gold failures (three `compare_pptx_files`, one
  `check_tabstops`). Unemulated tasks with a gold: 2a729ded and e8172110 as
  registered, plus 5df7b33a (a postconfig shell `zip` writes the checked
  archive), which the registered rule excludes but the pre-freeze count did
  not name; its gold is a zip, so only K1's denominator moves (75 to 74).
- P1 (`reserve-controls-v1`, Slurm 791-793, with the confirm run): raw flips
  3/67 confirm and 1/25 reserve, 4/92 together (4.35%, Clopper-Pearson
  1.2-10.8%), on the registered 92 golds; replication only, audit-confirmed
  share pending. The headless scoping round trip had flipped 7/63 and 1/26.
- Confirm mutants (`confirm-mutants-v1`, Slurm 794-796, 16 workers, apply
  to gold): 68 targets on 67 tasks as counted before the freeze; 1,289
  planned, 1,232 admitted (495 equivalence, 93 alternative, 290 violation,
  138 extra change, 216 ambiguous), 1,300 saves all written (96 slower than
  0.5 s, slowest 1.20 s), no save, scoring or infrastructure failure, no
  nondeterministic scoring, no venv disagreement (S1 empty), 23 normalized
  (S3; no K5 finding), 7 of 68 null mutants not passing (S7; K9 not fired).
  Evaluable 888 (444 outside probe-touched cells, 60 tasks). The census
  preview holds 134 real items on 33 tasks (36 equivalence mutants the
  checker fails, 5 violations it passes, 93 alternative solutions it passes)
  plus shams and the 4 P1 flips, far under the 1,139-item capacity. K2
  sample drawn (80 jobs, 4 domains, 41 tasks); no K2 executor yet.
- Held on the host until the isolated ingest (digests committed): the run's
  `campaign export` (labels, outcomes, verdicts), the per-task control
  summaries, the P1 flip list and the K2 sample. Committed: receipts,
  scontrol records, submissions and aggregates only.
- GPU: none (0.0 GPU-h row added to the ledger; total unchanged at 3.9261).
  Nothing pushed or merged.
- Next: stage A2, the audit (fresh salt, `submit_audit.sh` with the reserve
  control run, the overlay and the open-weight rater within the 3.0 GPU-h
  cap, the isolated Claude rating as one workflow session, collector,
  ingest, summary), then the registered analysis and Kevin's pool.

## 2026-10-08 — Q2 action path v2: D43's judge rule implemented and developed (branch `stage0/q2-action-path-v2`)

- Merged main (D41-D43 and the checker-mutation confirm stage A1) at
  `c450d79`. `program/decisions.md` is main's file exactly (D40 unedited;
  D42 is Q3's); the branch's own draft decision, superseded by D43, does not
  survive, and every action-path reference to it on the branch now names
  D43. `state.json` is main's plus the branch's Q2 entries; the GPU total
  stays 3.9261 (a 0.0 GPU-h row for the CPU-only v2 development added).
- The bit: a read-only scan of every run directory of the lane (424
  sessions; `program/evidence/2026-10-08/q2-action-path-v2-d43/`) found the
  Num Lock LED on, Num_Lock on Mod2 and Mod2 set at every session's start
  and in every guard check with no key pressed; of 519,344 tap key events
  172 lacked Mod2, every one after a shell grab key, every one with state 0;
  no probe or QEMU-monitor key event lacked it. The guard checked only the
  LED; condition (f) now requires Mod2.
- The rule (`126ff8b`): `verdict.modifier_state_observable` reads a key
  event the tap recorded without Mod2 on kind, keycode, keysym and order
  only (trial verdict and C4; C2's reading of the tap window too); every
  other event and the probe's channel as before; each verdict reports
  `state_not_observed`. A development-only executor fault
  (`fault_drop_modifier`) gives the negative case. Re-judged real records:
  v1's C2 and job 784's 15 L0-raw `chord_super_d` trials pass, the
  ungrabbed chords and jobs 785-787 are unchanged, run 572 (Super_L
  dropped) still fails. The L0-raw prediction keeps v1's failing set;
  `chord_super_d`'s pass is disclosed as informed by v1's C2 and D43, and
  C2 stays a reproduction test on seed 45.
- Development at `126ff8b` (seed 42, CPU only, jobs 830-839, 2.4 VM-h, all
  COMPLETED 0:0 with gates passed): L0-raw sample 151/180 (the four shell
  chords pass with queued events read without state; only the predicted
  `key_kp_enter` and `type_unicode_bmp` and the marker-only
  `seq_type_chord_type` fail); L0-fixed sample on 8 VMs 180/180; negative
  case (`omit`, `release_first`) 0/140 with nothing read without state; v1's
  final runs 703-708 repeated as 834-839 with the same outcomes (52/56,
  400/400, 800/800, 194/198, 178/186, 60/60). Registrations: sections 4.4,
  5, 6.2, 8, 10, 12 and 24-26 restated, design decisions 47-48, new section
  27; the executor addendum's byte-identity rule now requires every executed
  file to equal `126ff8b` and names each file that differs from `7653799`
  and `e66bf16`, and why.
- Checks at `31942e8`: ruff clean; Q2 tests 625 passed, 1 skipped; full
  suite on the host from a fresh `~/cotcodec-scratch/` copy 2232 passed, 38
  skipped. Freeze-linted v2, then `-inputs`, then `-executor` against a
  scratch copy of the ledger: the rows chain onto row 11, the chain checks
  at 14 rows, v1's, the checker-mutation and v2's rows verify; the
  repository ledger is unchanged (11 rows). Nothing frozen, pushed or merged
  to main. No GPU.
- Next: review of D43's implementation, then freeze v2, `-inputs`,
  `-executor`, and run C2 (seed 45), C1, C3, A1-A6, the ladder on a quiet
  host, A4 and A7.

## 2026-10-08 — Q2 action path v2: review of D43's implementation (branch `stage0/q2-action-path-v2`)

- Reviewers' blocking findings on `65267b7`, fixed at `932c8cb` in the
  registration text before any freeze; no file a campaign executes changed
  (`git diff --stat 126ff8b` over the lane still lists only
  `l0_raw_prediction_v2.yaml`), so the development at `126ff8b` stands.
- Section 26's garbled duplicate sentence (left by `31942e8`) is removed; a
  new test fails any prose paragraph of the three registrations that
  repeats a run of eight words, and catches the old text. Section 15 and the
  header both name sections 24-27; section 24's items 6 and 8 name D43's
  reading of the tap as the exception to "unchanged".
- D43's precondition is stated as observed, not checked (sections 4.4 and
  27, design decision 47, the inputs addendum, the prediction file's
  `d43_judge` note): all 280 development key events without Mod2 (172 in
  the scan, 108 in job 830) have state 0 and follow their grab key's
  processed press, but any client's synchronous grab freezes the keyboard
  and an active grab needs no key press. Section 27's new case 6: a
  synchronous grab already active before an entry would have every event
  read without its state and pass a raw-only shell chord, and the guard
  cannot see a grab (job 833 shows it blind to the overview a lone Super_L
  opened: no key reached the probe in seq 3-21 and 28-34 of both sessions,
  every pre check clean). Section 12 now reports any event read without its
  state that no key press with Mod2 preceded. The narrower rule (read
  without state only after such a press) is not D43's wording and would
  change `verdict.py` and `acceptance.py` and so the final development runs;
  left to Kevin.
- C3's equivalence test still compares the recorded state byte for byte
  (D43 names the judge); disclosed in sections 8, 26 and 27 and design
  decision 47 with its bound (up to 6.7% over the three `chord_super_d`
  trials of C3's H-OSW-fixed reference, M12 and M13 runs at the 2.3% bound;
  it can only fail C3, never pass a criterion; none observed). Whether D43
  covers it is left to Kevin (an `acceptance.py`-only change, no rerun).
- Tests pin each disclosed limit on real records (`tests/test_q2_d43_judge.py`)
  and the text (`tests/test_q2_prereg_inputs.py`). Checks at `932c8cb`
  (`program/evidence/2026-10-08/q2-action-path-v2-d43/checks/checks-932c8cb.json`):
  ruff clean; Q2 tests 635 passed, 1 skipped; full suite on the host from a
  fresh `~/cotcodec-scratch/` export 2242 passed, 38 skipped; validators
  PASS; freeze lint
  of v2, `-inputs`, `-executor` in order on a scratch copy of the ledger:
  14 rows, chain PASS, v1's, the checker-mutation and v2's rows verify; the
  repository ledger is unchanged (11 rows). Nothing frozen, pushed or
  merged. No GPU, no VM job.

## 2026-10-08 — Q2 evaluator-mutation: confirm campaign stage A2 (audit census, open-weight rater, isolated export)

- Operator run of the frozen `q2-evaluator-mutation-v1` (ledger row 11,
  `65bc2e2`), branch `ops/q2-mutation-confirm`, evidence
  `program/evidence/2026-10-08/q2-mutation-confirm/audit/`. Every container
  ran from the staged export or a clean clone of `65bc2e2`.
- Salt (D34): 64 hex characters written on the host (mode 600 in a mode-700
  directory, nothing else in it, never printed); SHA-256 `194ee66c...`
  committed, the salt revealed after the isolated ingest.
- Sample, baselines, packets (`submit_audit.sh` with `reserve-controls-v1`,
  Slurm 815, CPU, 2 min 25 s): the census, 178 items (36 `fn_equiv`, 5
  `fp_violation`, 93 `alt_gate`, all 4 P1 flips of both runs, 33 gold and 7
  do-nothing shams), no fallback (capacity 1,139); 33 baseline saves, none
  failed; two packet shards (133 and 45 items), 16 packets shortened, none
  over budget. The sample summary is held (it names the P1 flip tasks); a
  redacted copy is committed.
- Overlay: capsule `a8559f89...` (3,744 files, clean); job 816 was refused by
  the extractor in 1 s because the first receipt named the commit instead of
  `HEAD`; the same archive with a `HEAD` receipt built as 817 (43 s, image
  `7d4595f9...`, provenance PASS). CPU doctor 819: pass, 918 tokens per page.
- Open-weight rater (Qwen3.6-35B-A3B, thinking on, registered sampling, 160
  GiB, limits 22 and 13 minutes from the GPU ledger, 0.584 of 3.0 GPU-h
  allocated): 823 rated 133/133 in 14 min 49 s, 824 rated 45/45 in 6 min
  21 s; 172 `ok`, 6 `thinking_unfinished` (unsure), 0 unrated, no retry;
  both ended on their own (`reason=completed`, exit 0), no container left.
  Per-item calls held on the host; receipts and aggregates committed.
- Isolated export (`rater_runner export-isolated` at `65bc2e2`): 178 item
  directories under a fresh root in the session scratchpad, manifest
  `f9c91d57...` outside it, template `0e9d4eb6...` as pinned; the exported,
  sampled and rated id sets are equal.
- GPU 0.365 GPU-h physical (rater 0.3528, overlay 0.0122); program total
  4.2911. Nothing pushed or merged.
- Next: the isolated Claude rating as one workflow session of rater agents
  only, then `collect-transcripts`, `ingest-isolated`, `audit summarize`, the
  registered analysis, Kevin's pool and spot check.

## 2026-10-08 — Q3 dense pre-check v2: second timing job of the fixed 4B path (D42; branch `stage0/q3-dense-v2`, draft, not frozen)

- Main (`18fe252`, D42) merged in (`175d35e`); only `program/decisions.md`
  had changed on main. GPU total recomputed from the ledger rows.
- D42 (ii) implemented at `87242fa`: the timing profile starts with the
  lane's own `attention_backend_check` (cuDNN on, then off) before any unit;
  a second timing template with a fresh run root (`timing-2-qwen3.5-4b-base`),
  filler `--timing 2`; the caps count both timing jobs.
- Image 806 (CPU-only build from a fresh clone of `87242fa`); v2 CPU doctor
  12/12 in it. One timing job, filled once, dry run, `--test-only`, submitted
  once: Slurm 810, 162 s, 0.045 GPU-h physical (4 minutes charged), exit 75
  on Slurm's SIGUSR1 at a chunk boundary, receipt bound to job 810.
- The fixed path runs on the GPU. Start-up 78.7 s to the first unit, of which
  the backend check 47.4 s with the first-use compiles; on `c320-q0` cuDNN's
  attention and the lane's differ by at most 1.15 recall points and 0.011 in
  an option score, same answer; memory-efficient attention in the torch
  profiles. First evaluations: medians 0.42 (A-main), 0.39 (B-absent), 0.16
  (C-literal), 0.35 s (D-nohaystack) per unit; re-evaluated units the same
  (no per-shape cost left); two one-off compiles of 7.4 and 7.6 s. The same
  chunks took 6 s against 54-108 s in Slurm 766. One Python thread busy; GPU
  0-95 percent, mean 31 percent. v1's path bit-equal on five units (every
  stage).
- 4B limit by D36's rule: 769 s evaluation and statistics (per-stage means
  scaled up to the lane's context lengths, a compile allowance, 5 s
  statistics) and 79 s start-up give 30 minutes (0.50 GPU-h); 0.6B stays 12.
  Caps with both timing jobs 0.90 of D36's 1.5. A first analysis pass with
  per-stage token fits, whose slopes the two compiles set (measured lengths
  span only 3,600-3,950 tokens in two stages), gave 73 minutes; it was
  discarded for that reason and is kept in the evidence. Lanes module (a measurement
  again, bound by a test to the committed analysis), 4B template,
  registration (status and lead-in name D42; Compute; decisions 12, 18, 20,
  21; Changes; both timing jobs' results) and code table updated (`7ab5b8b`).
- Host suite at `7ab5b8b` hung in the in-process guard test (a
  process-directed signal can be taken by another pytest thread between the
  guard's sigpending and sigwait); the test now sends thread-directed
  signals (`8c3f076`; no tabled file changed). At `8c3f076`: host suite
  2,216 passed, 40 skipped, 0 failed; image 825, doctor 12/12, torch tests in
  the image 55 passed, PID-1 test passed. Freeze simulated on scratch clones
  naming the real D42: check-chain 12 rows PASS, frozen-mode tests pass, 0.6B
  and 4B fills and dry runs (0.2 and 0.5 GPU-h) ok; status-only and a wrong
  decision fail the test; full suite in the frozen clone 2,169 passed, 87
  skipped. Real ledger unchanged. Main (`692b83d`, D43) merged in again
  (`436f038`): host suite 2,216 passed, 40 skipped; full freeze simulation
  check-chain PASS.
- State: ledger row 0.045 GPU-h; program total 4.028; v2 used 0.1019 GPU-h.
  Evidence `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/timing-2/README.md`.
- Next: the narrow re-check of the measured limits (D42 (iii)), then merge
  and freeze naming D42.

## 2026-10-08 — Q2 evaluator-mutation: confirm stage B (isolated Claude rating ingest, audit summary, registered analysis)

- Operator run of the frozen `q2-evaluator-mutation-v1` (ledger row 11,
  `65bc2e2`), branch `ops/q2-mutation-confirm`, evidence
  `program/evidence/2026-10-08/q2-mutation-confirm/audit/` (section Stage B)
  and `.../results/`. Every command ran locally from a fresh `git archive` of
  `65bc2e2` (pins equal the frozen block). No GPU; the host was only read.
- Isolated Claude rating: workflow run `wf_138e30b5-c1a`, one unresumed
  session of 178 rater agents (`rate:0`-`177`), every one answered.
  `collect-transcripts`: 178 transcripts mapped to 178 items, none
  unmappable. `ingest-isolated` (both packet copies, manifest `f9c91d57...`,
  root re-hashed, collection `3a48f6f0...`): 177 `ok`, 1 `isolation_void`
  (`fd455942d783ba01`: one Read of a mistyped, non-existent path outside the
  item directory; the registered rule voids it, and it is in the pool as a
  split); no relay frame, nothing to re-rate; model `claude-opus-5-5` only;
  only the 15 registered attachment types.
- Salt revealed: SHA-256 `194ee66c...` matches, 178/178 item ids recompute.
  Held files released after their digests checked (A1 18/18, A2 7/7).
- `audit summarize`: κ 0.343 on 138 real items (raw agreement 82.6%); sham
  accuracy Claude 0.90, Qwen 0.975; 24 real items unresolved; K3 fires for
  both groups and κ, K4 fires (reported only, D35); no gold defect decided.
- Registered analysis (`--controls-summary`, `--reserve-controls-summary`):
  P1 raw 4/92 (4.35%), audit-confirmed 3/92 (3.26%, 0.68-9.23%). Checker
  false-negative candidates 36, all `pptx.eq.zorder_nonoverlap` on
  `compare_pptx_files`(`_tolerant`): 30 confirmed, 6 unresolved; candidate
  share 12.4% (7.2-18.3%), `compare_pptx_files` 40.2%. False-positive
  candidates 5 violations: 2 confirmed, 3 label-contradicted by both raters
  (pending Kevin); 5.9% (0.8-12.3%). Exploratory (D34 (i)): P2 12.4%, P3
  6.1%, P4 0/5, P5 17/60. K2 "offline harness, VM fidelity unverified".
- Pending for Kevin: the 34-item adjudication pool (24 splits, 6 concordant
  contradictions, 4 split gold shams) and the 25-item human spot check (7
  overlap); then `audit summarize --adjudications` and the analysis rerun.
  Nothing pushed or merged.

## 2026-10-08 — Q1 audit-metric study under D41 (ii): F1 characterised, a replacement metric designed (branch `stage0/q1-audit-metric`, CPU only, not merged)

- Scope: D41 (ii), on stored rows and CPU recomputation only; no GPU job, no
  evaluation unit (D28). Evidence and scripts in
  `program/evidence/2026-10-08/q1-audit-metric-study/` (README is the report). The
  draft registration is not edited.
- Data: journals of jobs 474, 518, 548, 713 (`ddbfbbf6...`) and 752, copied from the
  host. Kept 2,570 rows: S1-cal problems without an S2 substrate, plus 752's
  adversarial controls on L1/1 as stored rows only. Dropped 1,908: all of 518/548
  scoring, 518 and 474 smoke (evaluation units, S1-eval problems, or problems
  hosting S2 units). CPU recomputation of 139 registered A1/A2/A3 draws on the 12
  tier-1 problems (3.4 CPU-h): `torch.rand` inputs match 752's stored fingerprints
  bitwise, and four batch-independent problems were evaluated on leading batch
  slices.
- F1: e(0) = 1/(1+kappa) and e(-r) = 2/(1+kappa) exactly. The TF32-admissible T
  reaches 1 whenever the TF32 reference's error at a near-zero output exceeds about
  kappa ||r||_inf / 16. That holds for every matmul or convolution with sign-mixed
  weights (all L2 problems) and for the sign-mixed A2 draws of the L1 matmuls.
  Stored inline rows: no admissible draw rejects zeros on L2/46, L2/52, L2/59 or
  L2/60. On L2/77, L2/95 and L2/100 only one or two draws do, the latter two where
  the device happened not to use TF32. L2/87 escapes only because cuDNN did not use
  TF32. Strict fp32 is never vacuous but rejects 95 rows of correct cuDNN-TF32
  kernels. Restricting the registered audit to determinate draws (zeros fail by 4x)
  leaves six of eight L2 problems unauditable.
- A CPU TF32 emulation (operands rounded to TF32, fp32 accumulation) reproduces the
  stored device TF32 error: median ratio 0.996, 64 of 71 within 1.5x. The outlier is
  L1/18, where cuBLAS is 3.6x the emulation. cuDNN TF32 rounds to nearest.
- Candidates evaluated: registered e, M1 l2, M1 max-abs, M2 blockwise, M3 Higham
  gauge and M6 gauge-floored e. The registered e, M6 and M3 stay vacuous or fragile:
  520, 325 and 745 of 1,015 gross escapes under the RNE yardstick, and M3 breaks at
  kinks and under BN plus pooling. Recommended: reject if rho_inf > 4 or
  rho_block > 8 (strict: 4 and 16). The yardstick is device fp32, device TF32 and
  emulated TF32-RNE, plus emulated truncation for `tl.dot` candidates, and a decoy
  determinacy gate replaces the validity gate. On the 139 draws: 0 false rejects, 0
  of 1,111 gross escapes, 0 indeterminate; residual escapes are faults within 3.1x
  of TF32 noise.
- Next (Kevin): D14's admissibility of truncation; an allowance for an S1-cal-only
  GPU pilot of the rule (0.28 GPU-h, 0.20 for the 8 re-pilot problems, 0.57 with a
  2x margin; pass rule in README section 5); then a new Stage 0 id and gauntlet.
  F2 (cost) is unchanged. No GPU used; nothing pushed or merged.

## 2026-10-08 — Q1 audit-metric study, revision 2: reconciled with a replication and a critique; rule /1 withdrawn, rule /2 three-valued; recommendation not to fund a successor Stage 0 now (branch `stage0/q1-audit-metric`, CPU only, not merged)

- Scope: D41 (ii), D28, CPU only. An independent replication and an adversarial critique
  (both S1-cal only, no D28 violation found) were reconciled in
  `program/evidence/2026-10-08/q1-audit-metric-study/` (README sections 0 and 8 list each
  item and its answer). Every script was re-run.
- Fixed: the D28 filter now drops 752's L1/1 rows too (L1/1 hosts the FlagGems mm
  evaluation unit; 2,306 kept, 2,172 dropped); determinacy is reported per stored
  reference realization over both arms and all jobs (L2/59 A3/lead1 rejects zeros; L2/100
  has no draw that does in every realization); strict false rejects are 55 kernel-draws,
  not 95 rows; the L2/95 `plus2minus` account covers both arms; L2/59 `mask-bound-minus1`
  added (a zeros-like pass); the emulation check compares TF32 realizations only
  (batch-sliced 0.78-1.09); 12/276, not 13/286; 17 vs 27 conjunction escapes separated;
  the pilot re-priced with `cost_card.charge` (first-pass plan 0.50 GPU-h, not 0.28).
- New: `alt_algorithms.py` (83 registered draws of correct algorithms that are not
  yardstick members) and `scalar_check.py`. Rule /1 (reject above 4x/8x) falsely rejects
  the L1/47 sequential sum (13.7-15.2x), Winograd F(4x4,3x3) (fp32 under strict, TF32 up
  to 50x), truncating TF32 under an RNE-only yardstick, and, in stored GPU rows, fp32
  Inductor substrates at 5.4-7.5x the deployment strict yardstick. Withdrawn.
- Rule /2: noise-relative max-abs and blockwise ratios against a policy-chosen yardstick
  with a 2^-24 floor; accept within 4x/8x (strict 4x/16x), reject above 64x/128x (strict
  256x), otherwise precision-ambiguous; decoy-battery determinacy gate. On 139 CPU and 83
  alternative draws: every gross decoy rejected, no correct algorithm rejected (with RZ
  in the TF32 yardstick); 1% faults decided under strict (276/278) but ambiguous under
  TF32 (239/272). In-sample thresholds, thin margins (1.43x TF32).
- Pilot (if ever run): 13 S1-cal problems, compiler and cuDNN variants as correct
  controls, 0.57 GPU-h measured-cost estimate, 1.14 with a 2x margin, time box 1.2 GPU-h.
- Recommendation for Kevin: do not fund a successor Q1 Stage 0 now (TF32 ground truth
  covers gross faults only; MtC owns the mutant arm; Stage 1 blocked by R580 and D5);
  record this study as Stage 0's outcome; if Q1 is revived, D14 truncation ruling, then
  the pilot, then a reduced Stage 0 with a fresh gauntlet. No GPU used; nothing pushed or
  merged.

## 2026-10-08 — Q3 dense pre-check v2: the 4B limit's estimator sensitivity disclosed (branch `stage0/q3-dense-v2`, draft, not frozen)

- The narrow re-check of the measured limits found that Compute said the
  discarded first analysis pass and the registered one "differ only in how
  the two compiles are treated" (the timing-2 README too). They also scale
  differently: the first pass took the larger of a per-stage least-squares
  line in tokens (at the lane's mean) and the stage mean; the registered
  estimator scales the stage mean in proportion to length, and was chosen
  after the first pass came out over D36's cap (73 minutes).
- Recomputed from Slurm 810's receipt and `analysis.json`
  (`timing-2/limit-recheck/estimator-sensitivity.py`, standard library; it
  reproduces both committed analyses): with the compiles treated as
  registered, the line fit gives 678 s against 658 s for the stages, 27.62
  against 26.95 minutes before rounding, so 31 minutes against 30. The
  increase is all A-main's (+55 s; it has no compile): its measured units
  span only 211 tokens (3,614-3,825), slope 0.16 ms per token, 3.3 times
  B-absent's 0.048 over 3,551-8,313 tokens. The larger of the two in every
  stage gives 32. Proportional scaling over-predicts B-absent's measured
  8,310-token units (0.78 s against 0.60 s). At any of these estimates the
  lane's first job ends in about 14-15 of its 27 useful minutes.
- Fixed in text only (`ddb3d02`; no GPU job, no tabled file changed):
  Compute's parenthetical and decision 20 disclose both differences, the 31
  minutes, the 32-minute bound and why proportional scaling is registered;
  the 4B limit stays 30 minutes (0.50 GPU-h; caps 0.90 of 1.5). A new
  manifests test recomputes both estimators from the receipt and binds the
  disclosure.
- Checks at `ddb3d02`: local dense, preregister and v2 tests 185 passed, 15
  skipped; ruff clean. Freeze simulated on scratch clones naming D42:
  check-chain 12 rows PASS, frozen-mode tests 30 passed, code table matches,
  fills and dry runs (0.2 and 0.5 GPU-h) as before; status-only and a wrong
  decision fail the test; full suite in the frozen clone 2,170 passed, 87
  skipped. Real ledger unchanged.
- Next: close the narrow re-check (D42 (iii)); then merge and freeze naming
  D42.

## 2026-10-08 — Q3 dense pre-check v2: D44 implemented, the 4B limit 32 minutes (branch `stage0/q3-dense-v2`, draft, not frozen)

- Main (`1a45703`, D44; Q2 confirm stage A2) merged in (`cb9fc68`):
  `program/log.md` both sides in time order, `program/state.json` main's
  entries and this branch's Q3 entries; the GPU total recomputed from the 22
  ledger rows is 4.393. Main changed no tabled file and not the ledger.
- D44 implemented at `da31db7` (no GPU job): the lanes module records all
  three estimates of the 4B lane from Slurm 810 (stage-mean scaling 769 s,
  30 minutes; line fit 789 s, 31; the larger of the two per stage 824 s, 32)
  and sets the limit at their maximum, 32 minutes (useful window 29 minutes,
  break-even 1.43 s per unit). A lane's cap is now its minutes / 60 exactly:
  32/60 GPU-h for the 4B lane, because a cap rounded to 0.5333 is below 1 x
  32 / 60 and the submitter and the filler's budget check would refuse it;
  the filler's check is unchanged. Registered caps 0.933 of D36's 1.5 GPU-h.
  4B template 32 minutes, `max_gpu_hours` 32/60. Registration: Changes 6 and
  10, Compute (the three estimates and D44's choice; table 1 x 32, 0.53,
  total 0.93), decisions 12 and 20, freeze step 1 (the status paragraph and
  the lead-in name D42 and D44 at the freeze; the frozen-mode test refuses
  them otherwise); the draft status and lead-in say D44 closed the re-check
  and keep their draft wording until the freeze; code table re-rendered
  (only the lanes module and the 4B template changed). Tests bind the three
  estimates to the receipt, the module and `estimator-sensitivity.json`,
  check the exact cap and the refusal of a rounded one, and require the
  status and the lead-in to name D42 and D44 in draft and frozen mode.
- Checks at `da31db7`: ruff clean; local dense, preregister and v2 tests 186
  passed, 15 skipped; host suite (Slurm 841, fresh scratch clone) 2,218
  passed, 40 skipped, 0 failed; in image 825 with the new head's code
  mounted (CPU, network none) the torch-dependent dense tests 57 passed
  (Slurm 842) and the v2 CPU doctor 12/12 (Slurm 843).
- Freeze simulated on scratch clones of `da31db7` with the frozen wording
  naming D42 and D44: check-chain 12 rows PASS, frozen-mode tests 31 passed,
  code table matches, 0.6B and 4B fills as registered, dry runs 0.2 and
  0.5333 GPU-h (`--time=00:12:00`, `--time=00:32:00`); full suite in the
  frozen clone 2,171 passed, 87 skipped. The lead-in left in draft, D41 in
  place of D42, and the wording naming D42 only each fail the frozen-mode
  test. Real ledger `1052d58b...` before and after.
- Main moved to `1d2cbe0` (D45; Q2 confirm stage B: decisions, log, state
  and evidence only) and was merged in again (`85cf0f5`; this log in time
  order, state merged cleanly, GPU total 4.393 from the 23 ledger rows). At
  `85cf0f5`: host suite (Slurm 844) 2,218 passed, 40 skipped; full-mode
  freeze simulation check-chain PASS, frozen-mode tests 31 passed, the
  frozen file's SHA-256 equal to `da31db7`'s.
- GPU: none. Nothing pushed. Evidence
  `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/timing-2/README.md`
  ("D44") and `timing-2/d44/`.
- Next: freeze with the status paragraph and the design-decision lead-in
  rewritten to the frozen wording naming D42 and D44, image from the frozen
  commit, doctor, the 0.6B lane (job 727 to 1e-6 and smoke 452), then the 4B
  lane (32 minutes), and the combined read.

## 2026-10-08 — Q2 action path v2: D45 implemented, development repeated at `c74eae0` (branch `stage0/q2-action-path-v2`)

- Merged main twice (at `26067a7`: D44, D45 and the checker-mutation confirm
  stages A2 and B; at `e09e362`: D46 and the frozen
  `q3-dense-headroom-precheck-v2`, ledger row 12). `program/decisions.md` is
  main's file exactly; `state.json` is main's plus the branch's Q2 entries,
  the GPU total recomputed (4.393, unchanged by this branch's 0.0 GPU-h
  rows). v1's files are unchanged.
- D45 (i)-(iii) at `c74eae0`: `verdict.py` reads a key event the tap
  recorded without Mod2 without its state only when a key press recorded
  with Mod2 comes before it in the same window (`modifier_state_observable`,
  `state_not_observed`, `rdev_matches`, `match_events`); its docstrings state
  that a grab already active before an entry's first key is now judged on
  the recorded state, and that a grab activating inside an entry after a
  processed press is still taken to be the shell's. `acceptance.py`: C2's
  reading (`c2_projection`, `c2_matches`) and C3's stream signature and
  earlier-attempt comparison (`_stream`, `_events_equal`) read the state by
  the same rule; every criterion returns `state_not_observed_report` (each
  event read without its state with its offset from the preceding processed
  press; each event without Mod2 no processed press preceded). Prediction
  file notes name D45; frozen-table digests refreshed.
- Tests on real records: the 280 development events still read without
  state (and only they); job 785's `chord_super_d` with every key state 0
  (case 6) now fails, with C4 and C2's reading; the C3 slow-answer probe
  leaves M12 and M13 equivalent and C3 passing (counting attempt, earlier
  attempt or reference), a processed `d` press without Mod4 still makes M12
  survive; the dropped-modifier records (832/833, 847/848) still fail.
- Development at `c74eae0` (seed 42, CPU only, `vm-campaign.sbatch`, jobs
  845-854 repeating 830-839 with unchanged workloads, all COMPLETED 0:0,
  gates passed, 2.4 VM-h): every cell as in the D43 job it repeats, except
  one trial of 851 (L0-fixed, 8 VMs) that failed with `guest_server_restart`
  alone: an unprovoked guest-server restart during an `/accessibility` call
  (restart-only, excused in A1-A4 and the ladder; the lane's second after
  run 622; one in the 2,726 non-injected calls of 830-839 and 845-854). 845:
  151/180 with 108 events read without state, each 0-3 ms after a processed
  press; 846: 180/180; 847-848: 0/140, nothing read without state; 849-854:
  52/56, 400/400, 799/800, 194/198, 178/186, 60/60. Section 12's report from
  the analysis over job 768 and every v2 run: no event without Mod2 lacks a
  preceding processed press.
- Registrations: sections 4.4, 5, 8 (C2, C3, C4), 10, 12, 24, 26 and 27
  (now D43's and D45's), design decisions 47 and 48 updated and 49 added;
  inputs addendum rows for `c74eae0`; the executor addendum's byte-identity
  rule names `c74eae0` (`git diff --stat c74eae0` over the lane lists
  nothing). Evidence: `program/evidence/2026-10-08/q2-action-path-v2-d45/`.
- Checks at `e09e362` (`checks/checks-e09e362.json`): ruff clean; Q2 tests
  645 passed, 1 skipped; validators PASS; full suite on the host from a
  fresh `~/cotcodec-scratch/` export 2281 passed, 40 skipped; freeze lint of
  v2, `-inputs`, `-executor` in order on a scratch copy of main's 12-row
  ledger: 15 rows, chain PASS, every row verifies; the repository ledger is
  unchanged. Nothing frozen or pushed. No GPU.
- Next: review of D45's implementation, then freeze v2, `-inputs`,
  `-executor` and run C2 (seed 45), C1, C3, A1-A6, the ladder on a quiet
  host, A4 and A7.

## 2026-10-08 — Q2 action path v2: section 27's claim on D45's repeat corrected (branch `stage0/q2-action-path-v2`)

- Review finding: section 27 (to be frozen) and the D45 bundle's README
  item 3 said every cell's events read without their state equal those of
  the D43 job it repeats. They do not: section 12's report (`by_entry`) has
  job 845 at 29 in `chord_super_d`, 19 in `chord_alt_f4`, 20 in
  `chord_alt_tab` and 40 in `chord_ctrl_alt_shift_r`, job 830 at 30, 18, 20
  and 40 (108 in both). What is equal per cell is the number of trials with
  an event read without its state (10 of 10 in each shell chord), as
  `d45-development-runs.json` counts it. The earlier entry's "every cell as
  in the D43 job it repeats" holds in that sense only.
- Fix at `50f3861` (text and tests): section 27 and the README state the
  trial-level equality and both jobs' per-entry event counts, and why they
  differ (one 845 `chord_super_d` trial queued two events, not three; the
  `chord_alt_f4` Alt_L release was recorded with its state, Mod1 and Mod2,
  in one trial of 845 and two of 830). New tests: the committed
  `section12-report.json` equals the analysis on the records for jobs 830
  and 845, per entry and per event; section 27 and the README state the
  trial-level equality and the report's per-entry counts (the test fails on
  the old wording). No campaign-executed file changed (`git diff --stat
  c74eae0` over the lane lists nothing), so no run was repeated.
- Checks (`checks/checks-50f3861.json`): ruff clean; Q2 tests 647 passed, 1
  skipped; validators PASS; full suite on the host from a fresh
  `~/cotcodec-scratch/` export 2283 passed, 40 skipped; freeze lint of v2,
  `-inputs`, `-executor` in order on a scratch copy of main's 12-row
  ledger: 15 rows, chain PASS, every row verifies; main registration digest
  `6f690bb5...` (was `e2856952...`), the addenda's unchanged. The
  repository ledger is unchanged. Nothing frozen or pushed. No GPU.
- Next: as before (review, then freeze v2, `-inputs`, `-executor`).

## 2026-10-08 — Q3 dense headroom pre-check v2 operated (freeze steps 3-5, branch `ops/q3-dense-v2`): NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base

- Registration `q3-dense-headroom-precheck-v2` (ledger row 12, SHA-256
  `982e66ba...`, row hash `a68af989...`, `git_head_at_freeze` `0a068a1`,
  freeze commit `ed5d5a9`; D36, D42, D44). Evidence:
  `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/` (README,
  operator log, image and doctor receipts, filled manifests, claims,
  receipts, termination and provenance files, orx logs, squeue and
  nvidia-smi snapshots, summariser output).
- Step 3: a fresh clone of main at `ed5d5a9` on the host
  (`~/cotcodec-runs/stage0/q3-dense-v2/lanes-repo`) passed
  `preregister.py verify`, `check-chain` (12 rows) and all 27 tabled
  digests. Image build Slurm 855 (CPU only): `sha256:500f3b02...`, source
  tar `53458dd1...`, library versions identical to v1's image 723. v2 CPU
  doctor Slurm 856 in that image (`--network none`, no GPU, baked source):
  DENSE_V2_DOCTOR_PASS, 12/12, code digests equal the table.
- Step 4, Qwen3-0.6B-Base: filled on the host (slot-0 claim, 12 minutes;
  only the four FILL values differ), dry-run and test-only passed, submitted
  once by orx node `72c5f6c4` (commit `253ad85`, ssh backend) as Slurm 859:
  COMPLETED 0:0 in 279 s, provenance PASS, ORX_RESULT exit 0. Receipt
  `d39ca464...` bound to 859 from `job.env`. The validity gate held: v1's
  job-727 receipt was reproduced exactly (3,128 numeric leaves, largest gap
  0.0, 1,029 other leaves equal, development artifact `c1c455d8...`), and K1
  smoke 452 was reproduced (gaps below 1e-6 points). Decisions equal job
  727's: NOT_VIABLE (H1_CX 12.25, lower 8.98; `h2_status` FAIL).
- Step 4, Qwen3.5-4B-Base: filled with `--small-lane-receipt` 859 (slot-0
  claim, 32 minutes), dry-run and test-only passed, submitted once by orx
  node `e312036d` (commit `98a98a9`) as Slurm 862: COMPLETED 0:0 in 555 s,
  provenance PASS, ORX_RESULT exit 0. Receipt `db56b1da...` bound to 862.
  Run details:
  - 0.26-0.53 s per unit by stage, GPU at 27-100 percent when sampled.
  - cuDNN's attention off; `attention_backend_check` within 1.15 recall
    points and 0.011 in an option score of cuDNN's, same answer.
  - The guard repaired Triton's replaced SIGUSR1 and SIGTERM handlers 64.8 s
    in; no signal arrived.

  Decisions:
  - NEGATIVE_CAPABLE: H1_CX 42.15, 99% interval 35.76 to 48.20.
  - `h2_status` POINT_ONLY: H2a 49.64, H2b 8.57 with lower bound -9.29.
  - Lexical confound PRESENT (literal xi_rel 0.26-0.27; 0.24 on controlled
    families) and entity control INSUFFICIENT.
  - Null calibration CENTRED for hs and mp.
  - Floor VIABLE; fertility STRONG.

  No re-run or continuation arose.
- Step 5: the registered summariser ran from the clone with both receipts
  and both orx logs and exited 0. Combined read: NEGATIVE_CAPABLE_V3 on
  qwen3.5-4b-base. The requirements are D26's (a seen-script cross-script
  condition, an entity-controlled question set, the non-literal floor, a new
  id and the gauntlet) plus three from the flags: statistics computed on the
  entity-controlled set, anchor masking or a lexical-overlap covariate, and
  H2 re-tested on the v3 audit read. The read covers the development
  partition only and is not a K1 result.
- GPU time: 0.2317 GPU-h used (859 0.0775, 862 0.1542), 0.2833 charged
  under the registration's rule (6 and 11 minutes). Ledger rows use the
  physical figures. Program total 4.6247. With both timing jobs, v2 used
  0.3336 (0.4333 charged) of its 0.933 registered caps. Jobs 855 and 856
  were CPU only.
- Decision for Kevin (pending in `program/state.json`): whether to open a K1
  v3 on Qwen3.5-4B-Base under a new id and the gauntlet. Nothing pushed; the
  orx node branches are local.

## 2026-10-08 — K1 v3 gauntlet wave 1 on Qwen3.5-4B-Base: score 51, honest exit (branch `gauntlet/k1-v3`, not merged)

- Wave 1 (workflow `wf_3d0b843a-cdb`) on proposal
  `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md` (`752df4ad...`,
  commit `d911d21`) and the DRAFT registration
  `program/preregistrations/q3-k1-localization-screen-v3.md` (`f4ce9a00...`,
  not frozen, not admitted). Audit row 1 appended to
  `program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl`, row hash
  `fd00353ac209206a96ce0e5bfca5c0bfd08d2c3d9dd1ea29a6379d3b1e3bdb59`.
- Reviews: 51 (claude-opus-5-5) and 55 (qwen3.6-35b-a3b, self-hosted, Slurm
  966). Both totals equal their dimension sums and sit below every cap (74,
  79, 89). Score 51, best 51. Neither review is signed (D24). Reviewer 2 did
  not apply cap 74; its total is below 74, so the number is unaffected.
- Blind discrimination passed under the rule: same mechanism, proposal judged
  stronger (A = Oracle-Guided 2606.07703, B = the proposal). The SpotAttention
  packet and a Lost in Compression packet were not judged. Refute-first triad:
  3 of 3 refuted (novelty: trivial recombination of SpotAttention,
  Oracle-Guided section 9.1 and Lost in Compression's audit form;
  identification: one-sided safeguards; feasibility: decisiveness, not
  hardware). The doctor gives FAIL as expected (Novelty, Design and Compute
  FAIL; trust store; the known parser quirks, including `gpu_hours=0.5` read
  as 0); the re-run at record time is byte-identical to the bundle copy.
- Largest defect: NEGATIVE, the verdict that would stop Q3, is not identified
  as drafted. The overlap mask and LEX share one content-token rule, so LEX
  scores 0 on every unmasked needle block and the "two-sided" literal gate can
  register only haystack displacement and the target's own masked gap. The
  NEGATIVE region has no lower bound, so an MN-only displacement bias and a
  direction-flipping unseen-script deficit can cancel into a kill. The layer
  veto cannot fire at layer 3 (CX headroom 8.68 points against a 10-point
  threshold). With xi_rel and both targets, P(NEGATIVE | xi = 0) falls from
  0.90 at seed SD 1 to 0.34 at seed SD 2 (masked H 36), and no seed SD has
  been measured. The recorder checked the registration lines, the LEX scorer,
  the lane-862 per-layer values and re-ran reviewer 1's sensitivity script.
  Unlike K1 v2, this is repairable in the DRAFT without a new id.
- Honest exit. Queries: 171 counted discover calls against the declared 150
  (148 before the triad; novelty refuter 10, feasibility refuter 7 including
  one that failed to decode, reviewer 1 6), so no compliant wave 2 fits. The
  triad also stopped the candidate. Tokens 4.60M of 8M (conservative
  counter), $71.68 of $150 list-price equivalent, 91 of 600 minutes, 1 of 3
  waves.
- GPU: reviewer 2 job 966 used 0.0569 GPU-h (scontrol RunTime 00:03:25 on 1
  H100, COMPLETED 0:0, no leftover container), added to the ledger as "K1 v3
  gauntlet wave 1 open-weight review (D24)". Program total 4.6816. No screen
  GPU work ran.
- Waiting on Kevin: a successor gauntlet on a repaired v3 DRAFT with fresh
  budgets (six queries per refuter and reviewer, the Novelty doctor's missing
  coverage, a Lost in Compression blind packet); owner-approved CPU reads of
  the lane-862 development chunk files (masked headroom, masked LEX, the count
  of nonzero-LEX MN blocks); decision 64 or the letter of requirement 7;
  admission under D24 if probe-measured caps stay above 8 GPU-h (projected
  7.21 central, 9.79 high). The Q3 pending-decision line in
  `program/state.json` was left unchanged to avoid merge conflicts; update it
  at merge.

## 2026-10-08 — Q2 Stage 1a draft revised after three pre-freeze reviews (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- Three adversarial reviews of `q2-stage1-rescoped-v1` at `392e0ce`
  (identification and statistics; compute and feasibility; protocol) each
  said "not ready to freeze": 21 blocking items, 19 distinct. All are fixed;
  the registration's section 22 maps each to its change. CPU only; no host,
  GPU or VM job.
- Statistics: the X and session tests are now sign-flip tests, which hold
  their size under session excesses of 0-16 pp (the draft's permutations
  reached 0.157 and 0.224); X is named the mean squared per-task harness
  effect, with X_c its task-specific part; every estimand is stated for the
  realized sessions; DR2 uses Holm; P1-P5 are registered; DR5's M is frozen
  at 0.13 (0.18 when DR1 drops 4B) on the estimator's own scale, the largest
  value over six planning cells.
- Compute: sizes run one after the other (two at once need 244 of 208 CPUs);
  each GPU job waits for its VM job (`start_after_job_id` added to the docker
  submitter); the slot now holds VM setup and OSWorld's 80 s of settle, now
  matched for both harnesses; the K-rule counts the USR1 lead, launch and
  re-queues; A1 caps follow a remainder rule (at most 478 minutes in every
  branch). With the anchor running the base is 24 tasks, 32 without it.
- Anchor: its own engine argv (`max_model_len` 32,768 and
  `--trust-remote-code`; vLLM refuses 131,072 for OpenCUA-7B), a CPU
  load-and-validate check after O1, size set from A0b (64 or 96 tasks at
  N* >= 32), read on the longest completed prefix; ANC cap 52 minutes.
- Protocol: unfilled slots read TBD so the freeze guard refuses; G0 item 1
  is action-path v2's own verdict (C1-C4, A1-A6 on one attempt); the guard
  warm-up and uncertified keysym exposure are in; agent-caused `IRError`s and
  metric exceptions are no longer infrastructure loss; H-GA's sampling
  override is disclosed; checker-correction counts fixed and seven tasks
  flagged; DR5 now matches D47 (only GO leads to S1b).
- Code built and tested on CPU: `harness/q2_stage1/` (estimators, records,
  rules, plan, analysis), `scripts/render_q2_stage1_plan.py`, 51 new tests plus one for the submitter;
  the operating characteristics re-run with the registered estimators
  (`analysis/sim_s1a_v2.py`). The package sits outside `harness/q2/` so the
  action-path suite's closed-world admission is untouched.
- Waiting on Kevin: sign-offs on the 24-task floor (amends D47) and on DR1 and
  DR5 replacing the question file's kill lines (pending in
  `program/state.json`). The program must still admit O1, A0a and A0b and
  decide on OpenCUA's remote code; the action-path acceptance must pass first.

## 2026-10-08 — K1 v3 repair under D48, before a fresh gauntlet run (branch `gauntlet/k1-v3`, not merged)

- Single-owner repair of the DRAFT `program/preregistrations/q3-k1-localization-screen-v3.md`
  and the proposal `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md` (new
  section "Changes after wave 1"), with fresh run budgets: queries 60,
  wall_minutes 600, tokens 8,000,000, dollars 150, waves 1, gpu_hours 0.3. The
  repair used 6 counted queries (RP-Q1 to RP-Q6, one Japanese and one Korean)
  and no GPU. Not frozen, not admitted, not pushed.
- Literal check: two literal-free statistics become conditions of both
  verdicts (LF: evidence and candidates exclude every block within two blocks
  of an exact or near-literal match; PRE: passage text before the first
  match, spill-free by causality), with a kernel-literal positive control
  (LEXk) and a literal-leaning null family. Block-level simulation S1 (18
  scenarios, 42 tilts): wave 1's LEX check reads negative in every scenario;
  LF's literal bias stays within −0.26 to +1.11 points and PRE's within
  −0.57 to +0.16 for one-block spill (xi^M: −8.65 to +3.61); with an evenly
  spread excess a NEGATIVE implies an excess of at most 5.3 points (7.9 at
  three-block spill) and a GO at least about 4.7.
- NEGATIVE is two-sided (xi^M, xi_rel with limits scaled to the development
  masked headroom, both literal-free statistics, both directions with the
  English-needle direction gated, the seen comparator, a per-layer
  co-statistic veto on layers with at least 3 points of masked headroom).
  Seed variance: a layer-resolved seed term (df up to 16) and a sealed
  development seed read before the audit read (sigma_star 2.0). CS legs
  dropped; caps 6.94 GPU-h central, 9.46 high (wave 1 7.21 / 9.79).
- Decision simulation S2 (both targets, xi_rel; validated against the K1
  statistics module to 7e-15): given both gates, P(NEGATIVE | no excess) 0.81 to 0.91 at seed SD up to 1,
  0.53 to 0.64 at seed SD 2 and at most 0.08 at 3 (five seeds: 0.45 to 0.60
  at 3); P(GO) 0.31 to 0.61 at an input excess of 12 (realised 9 to 10) and
  0.89 to 0.99 at 15; in the false-kill scenarios 0.00 to 0.12, and 0.34 for a failure
  confined to layer 3, against wave 1's rules' 0.03 to 0.87 on the same draws. With the predictive H2 gate (0.42 to 0.57) and a
  judged pre-step pass of 0.6 to 0.8, unconditional P(GO or NEGATIVE) is about
  0.1 to 0.3.
- Doctor: FAIL as expected (Novelty, Design and Compute FAIL; trust store;
  the integer budget parser reads `gpu_hours=0.3` as 0).
- Next: this run's blind critic (fresh packets including Lost in
  Compression), refute-first triad and two reviewers, then the recorder.
  Admission stays Kevin's under D24.

## 2026-10-08 — K1 v3 gauntlet wave 2 (fresh run under D48): score 55, honest exit (branch `gauntlet/k1-v3`, not merged)

- Fresh run (workflow `wf_2605eba0-3f4`; budgets queries 60, wall_minutes
  600, tokens 8,000,000, dollars 150, waves 1, gpu_hours 0.3) on the repaired
  proposal (`4def0af9...`, commit `fcb303d`) and DRAFT registration
  (`08fa52ca...`, not frozen, not admitted). Audit row 2 appended to
  `program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl` (wave 2 of the
  gauntlet, wave 1 of this run), row hash
  `c56037c94502fbc4e664185124b7befc4c9ec17859fdfd4b01fe1de03c30ee8f`.
- Reviews: 55 (claude-opus-5-5) and 70 (qwen3.6-35b-a3b, self-hosted, Slurm
  1002). Both totals equal their dimension sums and sit below every cap (74,
  79, 89). Score 55, best 55. Trajectory: 45 (K1 v2), 51 (K1 v3 wave 1), 55.
  Neither review is signed (D24).
- Refute-first triad: 3 of 3 refuted again. Novelty: trivial recombination
  only (about 0.6), adding that ledger row 3 compresses XProvence's
  (2601.18886) seen/unseen-training-language split. Identification and
  feasibility: GO is not identified (below). The already-published prong
  fails: no direct prior found through 2026-10-08 under this run's 34 counted
  queries plus wave 1's coverage.
- Blind discrimination: void this run. The critic judged the proposal
  stronger, but its B packet (Oracle-Guided 2606.07703) carried an appended
  note naming that paper and the Lost in Compression packet, and the critic
  used the label against B. The cause was the repair's closest-prior field
  passed verbatim by the workflow script. Only that one comparison ran; the
  Lost in Compression and SpotAttention packets were not judged. Wave 1's
  blind test (passed) remains the only valid one. Cap 74 already applies for
  incomplete coverage, so the score is unchanged.
- Largest defect: GO is not identified as drafted; the NEGATIVE that D48
  targeted is materially repaired. GO's guard against long-range spill is
  PRE, which the registration drops below 40 percent family coverage; two
  independent model-free checks on the development text put coverage at
  0.19-0.22 (only a 400-id stop list clears 40 percent; the registered stop
  lists are not built). Without PRE, the repair's own S2 gives
  P(GO | no excess, spill +10) 0.225, wave 1's figure. GO also lacks a
  direction or floor condition, and a multiplicative query-by-passage loss
  reads as "mismatch" (10.9 points at r 0.2, H 40; P(GO) 0.44 in the
  identification refuter's re-run). S2 assumes 89 passage clusters; the
  development text gives 66, where P(NEGATIVE | no excess) is 0.75 at seed SD
  1 and 0.38 at seed SD 2. All of it is checkable in the DRAFT without GPU.
- Honest exit: wave cap (1 of 1) and token budget overrun. The token counter
  (row-1 convention) reads 8.62M against 8M; the repair owner alone used
  5.71M. Only a reading that also excludes this recorder is under (7.93M).
  Queries 34 of 60, $114.62 of $150 list-price equivalent, 176 of 600
  minutes. The doctor re-run is byte-identical to the bundle copy (FAIL as
  expected). Run against this file, its audit check would also flag the
  run boundary (row 1's hash and counters against the fresh budgets, two rows
  against waves=1); recorded in the row, nothing edited.
- GPU: reviewer 2 job 1002 used 0.0564 GPU-h (scontrol RunTime 00:03:23 on 1
  H100, COMPLETED 0:0, no leftover container), added to the ledger as "K1 v3
  gauntlet wave 2 (fresh run under D48) open-weight review (D24)". Program
  total 4.738. No screen GPU work ran.
- Waiting on Kevin: whether K1 continues at all (three consecutive K1 waves
  stopped 3 of 3 at the triad, each on one decisive verdict's identification
  and on decisiveness), or closes as Q3's attachment screen with the dense
  pre-check and these records as its outcome. If it continues: the stage-0
  facts with the registered stop lists first, a PRE redesign or dense-only
  spill bound, GO direction, floor and log-scale conditions, S2 with
  non-additive generators and 66 clusters, a measured kappa, and a properly
  blinded critic per prior packet. Also pending: the lane-862 CPU reads,
  decision 64, the five-seed option, D24 admission (high cap 9.46 GPU-h), and
  this run's token overrun. The Q3 pending-decision line in
  `program/state.json` was left unchanged to avoid merge conflicts; update it
  at merge.

## 2026-10-08 — Q2 S1a G0 build (branch `stage0/q2-stage1-rescope`, draft, not frozen; D49 iv)

- Built and tested on CPU every G0 item of `q2-stage1-rescoped-v1` the draft listed as TBD,
  in `harness/q2_stage1/` (nothing under `harness/q2/` changed): the episode runner
  (`driver.py`; harness clients in `agents.py`, checked against message lists recorded from
  the unmodified upstream agents), the engine client and the D13 bridge (`engine.py`,
  `bridge.py`), the VM lane (`lane.py`, `infra/slurm/host-single-node/s1a-vm.sbatch`), live
  OSWorld setup and evaluation with final-state capture (`osworld_live.py`), offline
  rescoring and the comparator validation (`rescore.py`), the reworked
  `compare_pptx_files_zinv` (`zinv.py`), the anchor's CPU checks (`anchor.py`) and the
  GLMM input (`glmm.py`). 193 S1a tests (142 new); `design_diffs.md` lists every difference from
  the upstream harnesses.
- Reviewed the stopped attempt's work line by line: kept `fetch-model-cpu.sbatch` (it had
  run as job 971: Qwen3.5-4B re-receipted, OpenCUA-7B fetched, 16.6 GB, D1), the GLMM
  Dockerfile (built as job 972) and the `opencua-7b` registry entry; fixed
  `s1a-cpu.sbatch` (the read-write mount may no longer come from the model cache) and
  `glmm.R` (a binomial `simulate` returns a successes-failures matrix); kept the
  python-pptx dev dependency; reworked `zinv.py`. No job of that attempt was still running.
- Host jobs, all CPU only (no GRES, GPU-less containers), at most one VM job at a time, at
  most 8 CPUs each, next to the running action-path v2 campaigns: 978 (dev smoke with the
  scripted fake engine: 3/3 episodes scored end to end), 982 (G0 item 5: 148/148 setups
  completed offline; the only confirm-task contact), 983 (offline rescoring of the smoke:
  3/3 match live), 980/995/1000 (zinv validation: 0/29, 26/29, then 29/29 confirmed
  mutants with 256/256 other items unchanged; the first two runs are kept and the 29 were
  development set as well as gate), 984 (GLMM acceptance on synthetic data, 200 refits),
  987/998 (anchor dry run in the existing overlay image), several small diagnostic jobs
  (979, 981, 985, 986, 988, 989, 992-994, 999) and the anchor's git reads under srun.
  One 2-second version check (`python3 -c "import vllm"`) ran as a bare `docker run
  --network none` outside Slurm; no GPU was requested.
- Findings that change the plan: the OpenCUA-7B anchor is UNAVAILABLE before any GPU job
  (G0 9.6: the public runs predate `b138d348` by 14 months; 110 of 116 tasks differ in
  config or checker, at most 6 remain readable against the 58 required; also 9.3's dry
  run: vLLM 0.31.0 with transformers 5.17.0 cannot load its remote tokenizer, and 9.5:
  the pinned agent cannot reproduce the public runs' L2 prompt). So A0b and ANC are not
  submitted, T_A1 is 111 minutes and K_base 32 at the card's high price, and D47's floor
  of 32 holds without the item 18 amendment. The episode container is the checker-mutation
  metric image (the stdlib runner image lacks Pillow and OSWorld).
- Registration: G0 items 2-6, 8, 9 and 12 filled; section 4's runner row replaced; section
  5.7's status; section 20 code table filled for the G0 files; section 22 gains a "G0
  build" table for the fresh audit. Still TBD: the status line, G0 item 1, the frozen plan,
  the executor row, the section 6.2 constants and the v2 acceptance evidence.
- Self-review fixes after the evidence commit: a transport loss behind which the guest
  server restarted is recorded as `guest_server_restart` (D30; `faad20f`), and a vLLM stream
  that ends before `[DONE]` is a retried transport error instead of a short completion
  (`9837c54`); code table refreshed.
- Tests on `9837c54`: S1a 192 passed, 1 skipped locally; the full suite on the host in a
  fresh `~/cotcodec-scratch/` export under `srun -c 8` (no GRES): 2,476 passed, 41
  skipped; ruff clean except the two K1 v3 evidence scripts merged from `main`, which fail
  there too (not touched here). The `a869b98` run (2,474 passed) linted `.venv` because its
  `--exclude` replaced ruff's defaults; rerun with `--extend-exclude`.
- Not done: no freeze, no push, no GPU job. Next: the fresh pre-freeze audit (D49 iv), then
  O1 and A0a after the action-path suite passes.

## 2026-10-08 — Q2 S1a G0 build: correctness and readiness review fixed (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- A further review of the G0 build returned eight blocking items; each is fixed with tests
  (registration section 22, "Correctness and readiness review", C1-C8), none rejected:
  - C1 (`61d02d9`): transport failures the pinned OSWorld checker swallows (`get_vm_file`
    returns `None`; postconfig steps log or re-wrap a `ConnectionError`) were scored as the
    agent's outcome. Every guest request that raises is now recorded, and setup,
    `evaluate()` and the capture sweep end in a transport loss when any of theirs failed;
    `is_transport_error` reads the exception chain; the restart check runs again after the
    capture, and an identity check that cannot reach the server is a transport loss.
    Job 1010 (CPU only, no VM, metric image) ran the pinned code on 13 pool tasks against a
    dead and a half-dead guest: the old rule scored 26 of 26 runs, the fix records 26 of
    26 as transport losses.
  - C2 (`483b3c0`): `type` text with a control character L0-fixed cannot type (a CRLF `\r`,
    ESC, C1) is an agent-caused `IRError`, not an `executor_device` loss.
  - C3 (`7929fae`): registered VM jobs take section 5.5's CPUs (90 at V = 20) and a limit
    of the GPU cap plus 10 minutes; the 8-CPU host-load cap is an operator flag for
    development and setup checks only.
  - C4 (`6d20be1`): the GPU-engine template's `seeds: []` (the submitter refused
    `deterministic` with seeds); a filled template passes the submitter for 9B, 4B and the
    anchor.
  - C5 (`2b9100d`): the K floor follows the anchor branch (32 without the anchor whatever
    item 18 says, D49 i); K = 32 needs a mean A0a slot of at most about 728 s at V = 20,
    below the card's high slot of 743 s, so going back to review after A0a is a live
    outcome.
  - C6 (`de4f80f`): A0a's truncation and concurrency gates computed by `plan.a0a_gates`
    and enforced by `freeze_constants`; section 15's label uses the gate's definition.
  - C7 (`e43549d`): every registered VM job's slots rendered from the plan
    (`plan.a0a_slots`, `plan.a1_slots`, `scripts/render_q2_stage1_manifest.py`) and the
    lane refuses any that differ; session 2's blocks recomputed from the session-1 records.
  - C8 (`0e2d192`): the system-prompt date is pinned to 2026-10-08 for every registered
    episode (option a), so the session excess is not confounded with a calendar change.
- Found and left for the audit (`ee531b6`): base task `26150609`'s setup step `pip install
  pygame` cannot succeed offline (OSWorld logs it and goes on, as upstream); scoring is
  unaffected, but the agent's VM lacks pygame. Whether that is a setup failure (which for a
  base task sends the draft back to review) is the audit's and Kevin's call.
- Tests on `e43549d`: S1a 237 passed, 1 skipped locally (45 new); the host full suite in a
  fresh `~/cotcodec-scratch/` export under `srun -c 8` (no GRES): 2,521 passed, 41 skipped;
  ruff clean on the S1a code, scripts and tests. Jobs: 1010 (the transport check) and the
  test run; at most one of mine at a time, beside the action-path acceptance job.
- Not done: no freeze, no push, no GPU job. Next: the fresh pre-freeze audit (D49 iv), then
  O1 and A0a after the action-path suite passes.

## 2026-10-08 — Q2 action-path v2 validity controls operated (branch `ops/q2-action-path-v2`): C2, C1 and C3 PASS

- Ran from a read-only `git archive` export of `bf99a64`, the commit
  recording ledger row 15, extracted to
  `~/cotcodec-runs/q2-action-path-v2/src/` on the host. Its tree digest is
  `abbbfe6c`.
  - A local export of the same commit passed `check-chain` (15 rows),
    `verify` of all three registrations and the pin and admission tests
    (51 passed).
  - The frozen renderer took the host root as a parameter (D40), so no
    manifest field was moved. All 50 manifests reproduce byte for byte
    locally.
  - Every job checked the ledger, the pinned files and the closed world at
    submission and again inside the job.
- C2 (job 864) is a reproduction test on its own seed (45) and is not
  a-priori. It ran L0-raw, 100 entries x 5, screenshot setting, N = 1.
  - End state: `COMPLETED` 0:0 by the watcher and the batch record. The
    campaign counts, with no infrastructure failure, retry or restart.
  - `acceptance.c2` gives PASS: the failing set is exactly the predicted 8.
  - `chord_super_d` passed 5 of 5. Under D45's rule its queued `d` press,
    `d` release and Super_L release were read without their state, each
    0-2 ms after the processed Super_L press.
  - Section 12: 53 events in 20 trials were read without their state, all
    in the four shell chords and all after a processed press of the chord's
    grab key. No event lacked Mod2 without a preceding processed press.
  - Under section 5 as written, 454 of 500 trials passed. The four shell
    chords now pass too. Three entries were FLAKY on stale markers only.
  - v1's a-priori result (job 768, one unpredicted failure) is reported
    beside it.
- C1 (jobs 866 and 868): H-OSW-up failed R08-R11 and H-GA-buggy failed R01,
  R02 and R05-R07, each in 5 of 5. PASS.
- C3 (jobs 870-962, 47 campaigns, 4,617 trials): PASS.
  - 42 of 44 scored mutants were killed. M12 and M13 on H-OSW-fixed came
    out equivalent, as predicted.
  - The reference runs failed only outside-spec R cells.
  - No infrastructure failure, and no event was read without its state.
  - Three predicted killers did not kill, the same three as in development
    (M01 on H-OSW-fixed `scroll_ctrl_down_3`, M21 `mixed_gesture_state`,
    M26 `seq_long_mixed`). Each of those mutants was killed by other cells.
  - C3 repeated development's conditions.
- Every campaign was attempt 1 and counted, so no rerun and no repair.
  - Each manifest is N = 1. C1's two campaigns and up to six C3 campaigns
    ran as concurrent separate jobs, as the development mutant runs did.
  - The verdicts reproduce byte for byte on the host and locally from the
    raw records.
  - 2.95 VM-hours, CPU only (C2 0.17, C1 0.11, C3 2.68), and no GPU.
- Evidence: `program/evidence/2026-10-08/q2-action-path-v2-acceptance/`.
  It holds the manifests, the batch, receipt and Slurm records, the verdicts
  with their section-12 reports, the per-campaign summaries, the
  prediction table, the checks, the raw SHA-256 lists and the operator
  scripts.
- A1-A7, the ladder and A5 did not run. Nothing pushed or merged.

## 2026-10-08 — Q2 action-path v2 acceptance at N = 1 operated (branch `ops/q2-action-path-v2`): A1, C4, A2, A3 and A6 PASS; A5 passes so far

- Ran from the controls' read-only export of `bf99a64` (tree `abbbfe6c`),
  checked again first.
  - A fresh local export passed `check-chain` (15 rows), `verify` of all
    three registrations and the pin and admission tests (51 passed).
  - The frozen renderer, given the host root, wrote 9 manifests. All 9
    reproduce byte for byte locally, and none was edited.
- Ran in the registered order, attempt 1, one campaign at a time, N = 1:
  A5's boot-reset campaign, A1 (seeds 43 and 44), A2 (H-OSW-fixed, H-GA),
  A3 (L0-fixed, H-OSW-fixed, H-GA), then A6 (jobs 964-1015).
  - Every job ended `COMPLETED` 0:0 by the watcher and the batch record, and
    counted.
  - No infrastructure failure, observation retry, guest-server restart or
    excused trial occurred. So there was no rerun and no repair.
- A5: the boot-reset campaign (job 964, 21 cold boots) shows 20 of 20
  pristine reset-sentinel checks. The 8 acceptance receipts are clean.
  `acceptance.a5` passes. It is judged again once A4, A7 and the ladder have
  run.
- A1 at N = 1 (jobs 968 and 970): L0-fixed passed all 100 entries 5 of 5 in
  both seeds' shuffles and both settings, 2,000 of 2,000 trials. PASS.
  - The part at N* > 1 waits for the ladder.
  - N = 1 reference for the ladder: step p95 2.694 s (2,560 steps), boot p95
    17.92 s (36 boots).
- C4: 700 of 700 key, chord and Caps Lock trials agree with the R-dev
  reference. PASS.
- A2 (jobs 974 and 991): every in-spec cell passed 10 of 10. PASS.
  - H-OSW-fixed: 97 of 97 in-spec cells; R03 and R09 failed (outside spec).
  - H-GA: 87 of 87 in-spec cells; R02, R04, R06 and R10 failed (outside
    spec).
  - These are the same outside-spec failures as in development and C3.
- A3 (jobs 1004, 1008 and 1013): 4,980 of 4,980 trials. PASS.
- A6 (job 1015): 300 of 300 trials, with every app at 100%. PASS.
- No restart in 7,172 accessibility calls (A1 1,298, A2 1,452, A3 4,422;
  the registered counts).
- Section 12: no key event was read without its state in any criterion, and
  none lacked Mod2 without a preceding processed press. `chord_super_d` on
  the L0-fixed path passed 40 of 40 (A1 and A2) with every state processed.
- All 18 verdict and summary files reproduce byte for byte locally from the
  raw records (914 files, SHA-256 checked) under Python 3.13 (host 3.10). The
  run checks pass for all 9 jobs.
- 8.65 VM-hours, CPU only (A5 0.29, A1 1.46, A2 1.56, A3 4.51, A6 0.83,
  against 9.1 sized). That brings v2 to 11.60. No GPU.
  - Wall clock: 15:28-00:19 UTC.
  - Other sessions' Slurm jobs (`s1a-*` CPU jobs and an open-weight reviewer
    GPU job) ran during A5, A2 and A3, but not during A1 or A6. They are
    recorded and not judged at N = 1.
- Evidence: the second-stage sections of
  `program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md`, with
  the manifests, run, receipt and Slurm records, verdicts, section-12
  reports, summaries, checks, raw SHA-256 lists and operator scripts.
- Not run: the ladder, A4 and A7. Nothing pushed or merged.

## 2026-10-09 — Q2 action-path v2 concurrency ladder operated (branch `ops/q2-action-path-v2`): N* = 32; rung 40 did not count (host inotify limit), rerun held

- Ran from the earlier stages' read-only export of `bf99a64` (tree
  `abbbfe6c`), checked again first.
  - A fresh local export passed `check-chain` (15 rows), `verify` of all
    three registrations and the pin and admission tests (51 passed).
  - The frozen renderer (`ladder --concurrency N`, given the host root)
    wrote the 5 rung manifests. All 5 reproduce byte for byte locally, and
    none was edited.
  - r_N was 6, 10, 14, 19 and 24, with 20, 34, 48, 64 and 80 sessions.
    Runner CPUs were 4-20, and the VMs used at most 160 vCPUs.
- Ran rungs 8, 16, 24, 32 and 40 in that order, attempt 1, one rung at a
  time (jobs 1017, 1019, 1021, 1023 and 1025), 02:17-03:04 UTC.
  - Each rung was submitted only after an empty whole-queue check
    (`ops/submit_rung.sh`). Nothing else was submitted while a rung ran.
  - No foreign Slurm job appears in any of the 502 host snapshots, so
    `foreign_abort` is empty for every rung.
  - No requeue: every record shows `Requeue=1 Restarts=0`.
- Rungs 8-32 qualify. Each ended `COMPLETED` 0:0 and passed every trial
  (9,800 of 9,800).
  - Boot p95 was 18.3-22.1 s, against a limit of 180.
  - Step p95 was 2.714, 2.885, 3.132 and 3.170 s, against a limit of 5.389
    (2 x A1's 2.694).
  - There were no restarts, so no trial was excused. The rungs'
    `/accessibility` calls were exactly the registered counts.
- Rung 40 (job 1025) did not count: `FAILED` 3:0, `driver_exit=3`,
  infrastructure gates false.
  - 10 of its 80 cold boots served no screenshot within 300 s: 5 in each
    setting, and 600 trials were not run.
  - In each of those VM containers, `dnsmasq` failed with "failed to
    create inotify: Too many open files". The VM fell back to usermode
    networking, and the guest server's port never opened.
  - The host's `fs.inotify.max_user_instances` is 128. About 35 concurrent
    VM containers get `dnsmasq`.
  - The 4,200 trials that did run all passed.
- **N\* = 32** by `acceptance.n_star`, so the program kill criterion
  applies (N\* < 40).
  - A1 at N\* passes: rung 32's first five repetitions passed 1,000 of
    1,000 trials (860 gating).
- Section 6.1 allows rung 40 one rerun, because it did not count. **It was
  not submitted.**
  - Under the same host limit, a rerun would fail the same way and use up
    the rung's last attempt. A7 runs at attempt 1's N\* and is never judged
    again.
  - Raising the limit needs root.
  - Kevin decides: keep N\* = 32, or have an admin raise the limit and then
    rerun rung 40 once, before A4 and A7.
- Reported, not judged:
  - session wall time grows with N, by up to 30%;
  - overlay growth is about 68 MB per screenshot session and 234-259 MB per
    accessibility session;
  - the host was 8-44 CPU-equivalents busy, with steal at most 1e-4
    (operator `/proc/stat` samples);
  - one accessibility retry (rung 40) was delivered on retry;
  - no key event was read without its state, over 14,000 trials.
- A5 over all 13 acceptance campaigns' counting receipts plus the
  boot-reset campaign still passes.
- All ladder and A5 JSON reproduces byte for byte locally from the raw
  records (1,240 files, SHA-256 checked) under Python 3.13 (host 3.10).
  - The run checks pass for 1017-1023, and for 1025 except its end state.
- 12.40 VM-hours occupied, CPU only (17.45 allocated; sized 11.0). That
  brings v2 to 24.00 VM-hours. No GPU.
- Evidence: the third-stage section of
  `program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md`, with
  the manifests, run, receipt and Slurm records, the n_star and A1-at-N\*
  verdicts, the concurrency table, section-12 reports, checks, raw SHA-256
  lists and operator scripts.
- Not run: rung 40's rerun, A4 and A7. Nothing pushed or merged.

## 2026-10-09 — Q2 action-path v2 volume campaigns operated (branch `ops/q2-action-path-v2`): A4, A7 and A5 PASS; A1-A6 hold, Stage 1 may start; A7 holds

- Ran A4 and A7 at attempt 1's N\* = 32 (D51), attempt 1, each as one job
  from the same read-only export of `bf99a64` (tree `abbbfe6c...`).
  - The renderer's worst-case budgets (1,350 and 660 min) fit the lane's
    24 h, so neither campaign was split into session ranges.
  - Each was submitted only on an empty whole-queue check
    (`ops/submit_volume.sh`). No foreign Slurm job appears in any of the
    3,172 host snapshots.
  - A4 (job 1027) ran 03:21:55-04:59:50 UTC; A7 (job 1029) ran
    05:00:32-06:20:52 UTC. Both ended `COMPLETED` 0:0 by the watcher
    and the batch record, and neither was requeued (`Restarts=0`).
  - All 1,584 cold boots got `dnsmasq` and served a screenshot; the
    inotify limit that failed rung 40 was not reached at N = 32.
- **A4 PASS.** 64,028 of 64,028 trials passed, over all 86 G entries in
  1,068 sessions.
  - No trial was excused, and there were 0 restarts in 36,515
    `/accessibility` calls.
  - Each of the seven action classes got 10,148-10,216 executed actions.
    So each class's per-action failure rate is at most 5 x 10^-4 and the
    per-boot rate at most 0.47%, together at family-wise 95%.
- **A7 PASS.** 0 restarts in 39,036 `/accessibility` calls (exactly the
  plan's; the cap does not bind). The exact upper 95% bound is 7.67 x 10^-5
  per call, against 5 x 10^-4.
- **A5 PASS (final).** Over the boot-reset campaign and the counting
  receipts of all 15 acceptance campaigns (A1-A4, A6, A7 and the five
  rungs), `System.qcow2` was unchanged and nothing was left.
- **Overall (section 7): A1-A6 all hold, so Stage 1 may start; A7 holds, so
  Stage-1 episodes may use the screenshot-plus-accessibility setting.**
  N\* = 32 < 40, so the program kill criterion applies: cut the Stage-1
  task count before adding GPUs.
- Reported, not judged: in one A7 session (193), the guest server answered
  every `/accessibility` call with HTTP 500 for the whole boot, without
  restarting.
  - 59 of its 60 trials failed with `infra: accessibility`. A7 counts
    restarts only, so it does not count this.
  - It is 1 of 1,245 accessibility-setting boots across the acceptance
    suite (exact upper 95% bound 3.8 x 10^-3 per boot). No other session
    lost a tree; 17 calls were delivered on retry.
  - Had it struck A4, A4 would have failed. Stage 1 counts restarts per
    episode and would miss it, so the Stage-1 preregistration should count
    undelivered trees per episode too.
- Reported, not judged: one A4 step took 127.7 s, because its
  `/accessibility` call first timed out (the retry delivered it, and the
  trial passed). No key event was read without its state in either
  campaign.
- All A4, A7 and A5 JSON reproduces byte for byte locally under Python 3.13
  (host 3.10), from raw records whose 7,928 files were SHA-256 checked. The
  run checks pass for both jobs.
- 85.12 VM-hours occupied, CPU only (A4 49.21, A7 35.92; sized 44.0 and
  31.1). That brings v2 to 109.12 VM-hours (sized 98.4). No GPU.
- Evidence: the fourth-stage section of
  `program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md`, with
  the manifests, run, receipt and Slurm records, the A4, A7 and final A5
  verdicts, section-12 reports, checks, raw SHA-256 lists and operator
  scripts.
- Not done: `program/state.json` and `HANDOFF.md` are not updated, and
  nothing is pushed or merged.

## 2026-10-09 — Q2 action path v2 accepted on attempt 1 (D53)

- Stage B's volume stage (resumed after the session restart) judged A4 (job
  1027: 64,028 of 64,028 trials over 1,068 sessions; per-class bounds at most
  5.0e-4, per-boot 0.47%, family-wise 95%) and A7 (job 1029: 0 restarts in
  39,036 accessibility calls, upper bound 7.67e-5 per call) at N* = 32, and A5's
  final judgement over all 16 receipts: all PASS. Neither job was resubmitted.
- A fresh verifier recomputed every stage B verdict with the frozen code from
  SHA-256-checked copies of the run directories, re-rendered the 7 manifests
  (byte-identical) and re-judged 107,988 trials (0 mismatches):
  `independent-verification-stage-b.json`, verdicts reproduced. With stage A,
  the registered verdict holds: Stage 1 may start; the screenshot-plus-
  accessibility setting may be used; N* < 40 triggers the program kill criterion.
- Findings recorded in D53: A4 and A7 ran before the rung-40 choice was recorded
  (a disclosed governance deviation); D51's repair-attempt sentence corrected;
  the whole-boot `/accessibility` failure in A7 session 193 and the first-call
  500s and hangs are outside every criterion, so Stage-1 registrations count
  undelivered and very slow observations per episode.
- Merged `ops/q2-action-path-v2` into main. Next: the S1a pre-freeze work.

## 2026-10-09 — K1 v3 repair under D52, before a fresh gauntlet run (branch `gauntlet/k1-v3`, not merged)

- Single-owner, CPU-only repair of the DRAFT
  `program/preregistrations/q3-k1-localization-screen-v3.md` and the proposal
  `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md` (new section "Changes
  after wave 2"), aimed at the defects wave 2 named. Fresh run budgets:
  queries 60, wall 600 min, tokens 8M, dollars 150, waves 1, gpu_hours 0.3.
  No GPU; 2 counted orx queries (RP3-Q1, RP3-Q2), 4 full-text reads.
- Development facts (model-free, real Qwen3.5-4B-Base tokenizer, K1 split,
  proxy stop lists from K1's haystack sources): 110 of 224 questions
  controlled in 66 of 122 links; the D48 per-family PRE rule holds for 0.20
  to 0.22 of controlled unseen families (the wave-2 refuters' figure
  reproduced), the pooled PRE for 0.53 to 0.67 (17 percent of unmasked
  tokens); LF 0.67; mask exclusion 1.5 to 1.6 percent; answer-sentence kappa
  bound LF 0.74 to 0.77, PRE 1.15 to 1.17.
- GO: PRE pooled over every family with a complete pre-literal block (the D48
  40 percent fallback withdrawn; a coverage rule can only make GO
  unavailable); both directions at least 5 with lower bounds above 0; a
  direction floor; a log-retention co-statistic; pre-step item 9 gates the
  literal-free sensitivity.
- Simulation S3 on measured inputs (67 clusters, per-family evidence sizes,
  LF and PRE as statistics, multiplicative and floor-saturating generators;
  validation against K1 6.2e-15): constructed false GOs at most 0.01 (wave-2
  draft as it would freeze: 0.23 under spill +10, 0.99 under +15, 0.71 under
  a multiplicative null); P(NEGATIVE | no excess) 0.60 to 0.71 at seed SD 1
  (S2 said 0.81 to 0.86); the seed top-up in the V1 extension's slot raises
  it to 0.55 to 0.59 at seed SD 2 without new caps.
- Chance of a verdict, stated: about 0.13 to 0.25 at seed SD 1, 0.12 to 0.21
  at 2, 0.07 to 0.14 at 3. Caps 6.96 / 9.46 GPU-h (high over 8; D24).
- XProvence credited in ledger row 3 and as closest prior 4; fresh blind
  packets with no notes (e4578790, 52321202, 9606bfd6). Doctor FAIL as
  expected (Novelty, Design, Compute; trust store; integer budget parser).
- Host CPU (nice 19, temporary directory, removed) ran the stop lists and
  most of S3; no Slurm job, no image. Not frozen, not admitted, not pushed.

## 2026-10-09 — K1 v3 gauntlet wave 3 (fresh run under D52): score 56, honest exit (branch `gauntlet/k1-v3`, not merged)

- Fresh run (workflow `wf_b33e58fd-bfa`; budgets queries 60, wall_minutes
  600, tokens 8,000,000, dollars 150, waves 1, gpu_hours 0.3) on the
  D52-repaired proposal (`ae995bc9...`, commit `1d34eaa`) and DRAFT
  registration (`bdbe5e9a...`, not frozen, not admitted). Audit row 3
  appended to `program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl` (wave 3
  of the gauntlet, wave 1 of this run), row hash
  `7e322aa7e7f70f5cfb8962dad76fafb121b65c99acf0a166017cc1c0d19ca34d`.
- Reviews: 56 (claude-opus-5-5) and 57 (qwen3.6-35b-a3b, self-hosted, Slurm
  1031). Both totals equal their dimension sums and sit below every cap (74,
  79, 89). Score 56, best 56. Trajectory: 45 (K1 v2), 51, 55, 56. Neither
  review is signed (D24).
- Refute-first triad: 3 of 3 refuted, as in every K1 wave. Novelty:
  recombination only (about 0.65); it found two priors the v3 ledger omits,
  Allchin 2607.21692 (KL-distilled block router scored on evidence recall,
  outside the model) and PHSA 2601.02819 (in-model selector with a
  language-coverage deficit). Neither is a direct prior. Identification: GO
  is not identified against question-side literal priming (MN questions share
  0.38-0.68 of content tokens with the needle, CX 0.00-0.04; LF and PRE clean
  only the evidence). NEGATIVE is well identified. Feasibility: decisiveness
  (below). No direct prior found through 2026-10-09 under this run's 35
  counted queries plus waves 1 and 2.
- Blind discrimination: valid this time (the packets match the bundle files
  exactly and name nothing) and passed by the rule's letter. The critic
  judged the prior, Oracle-Guided 2606.07703, the stronger contribution but
  the proposal "more novel and more rigorous, but much narrower", so the prior
  is not strictly dominant. That is weaker than wave 1. Only one critic call
  ran again; the XProvence, Lost in Compression and SpotAttention packets were
  not judged. Reviewer 2 read the result as a failure. Cap 74 applies for
  incomplete coverage either way, so the score is unchanged.
- Largest defect: decisiveness. E19 omits the registered V1-at-every-seed rule
  and V1_AFTER_TOPUP. With them, the unconditional chance of GO or NEGATIVE is
  0.10-0.25, 0.05-0.17 and 0.03-0.11 at seed SD 1, 2 and 3 (E19 states
  0.13-0.25, 0.12-0.21 and 0.07-0.14), and the seed top-up's gain is not
  established. The new direction floor adds no identification in S3's nulls
  but cuts P(GO | excess 15, beta 10) from 0.89 to 0.30. H2 is still the
  likeliest stop. That is about 10-50 GPU-h per decisive verdict. Second: GO's
  question-side literal channel (R10 and decision 91 relabel it rather than
  measure it). Registration lines 341-342 also misstate the pooled-PRE
  per-pair minimum (0.64 is the E-only variant; the registered proxy gives
  0.500).
- Honest exit: wave cap (1 of 1), binding; triad stop. The recorder also
  reads "the same fatal defect survives three waves" as applying in
  substance to decisiveness. It is part of the largest defect in all three
  rows of this gauntlet, and D52's repair aimed at it did not move it. Under
  row 2's stricter reading (identical headline, reject-level) it would not
  formally apply. Not applying: tokens 3.44M of 8M, $56.74 of $150, 89 of
  600 minutes, queries 35 of 60, GPU 0.0564 of 0.3. Under two points of gain
  across three waves: no (+5 over rows 1-3), but this wave gained 1, so a
  fourth wave must reach 57. Doctor re-run byte-identical to the bundle copy
  (FAIL as expected).
- GPU: reviewer 2 job 1031 used 0.0564 GPU-h (scontrol RunTime 00:03:23 on 1
  H100, COMPLETED 0:0, no leftover container; max_model_len 196608 to fit the
  149,570-token prompt). Added to the ledger as "K1 v3 gauntlet wave 3 (fresh
  run under D52) open-weight review (D24)". Program total 4.7944. No screen
  GPU work ran.
- Waiting on Kevin: whether K1 continues. Four K1 waves (45, 51, 55, 56) have
  stopped 3 of 3 at the triad, and decisiveness has not moved across three.
  The levers that could move it are his: decision 64, five seeds at every
  rate, a probe-scale 4B indexer run, and the lane-862 CPU reads. CPU repairs
  in the DRAFT, if it continues: model V1 in S3/E19, drop or relativize the
  direction floor, add a same-language zero-overlap leg or narrow GO's
  reading, restore Allchin and PHSA, correct lines 341-342, and run one
  blinded critic per prior packet. Also pending: the novelty bar for a first
  measurement, and D24 admission (high cap 9.46 GPU-h). The Q3 lines in
  `program/state.json` (pending decision and next_action) still describe
  wave 2; update them at merge.

## 2026-10-09 — Q2 S1a: G0 item 1 filled, D53 (iii) observation rule, O1 and A0a run, A0 constants filled (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- Merged `main` (D53) into the branch. G0 item 1 is filled from action-path v2 attempt 1:
  executor addendum row 15 (`cef0cbc6...`), L0-fixed, executor and adapter digests, H-GA's
  translator (row 14) and the IR (row 13). `preregister.py verify` passes for rows 13-15
  and `check-chain` for 15 rows; every file equals its digest. N* = 32 gives V = 20 with
  the sizes in turn. The concurrency gate's reference is `step_p95_n1_s` = 2.6944 s
  (`acceptance/ladder-n-star.json`). Sections 1, 4, 5.5 and 21 follow.
- D53 (iii). Checked how the runner classifies a guest server that answers HTTP 500 for a
  whole boot:
  - A failed screenshot, `/execute` or `/setup/*` was already an infrastructure loss.
  - A checker's read was not. The pinned controller returns `None` after a 5xx, and the
    metric scored 0 (y = 0). A read with no timeout could hang until the 3,600 s episode
    timeout.
  - Fixed in `bb67aa0`. A checker observation, or a screenshot, that got no HTTP status
    below 500 on any attempt is a `guest_observation` loss. Every observation is counted
    per episode: retried, slower than 30 s, undelivered. A guest request with no timeout
    gets 150 s. A restart check answered with an HTTP error is a transport loss.
  - Found by the new tests: `write_capture` crashed the runner when the checker read no file
    and the task cache was empty. Fixed.
  - The registration (sections 3.1, 7.2, 7.3, 15, 19, 20, 22) and `design_diffs.md` are
    updated.
  - Job 1036 (CPU only, pinned OSWorld, 32 dev tasks) confirms it on the pinned code. Every
    server-error run is a loss (64 of 64; the old rule scored all 64). Every missing-file
    run stays scored (32 of 32). Job 1034 was cancelled as too slow; job 1035 had a
    stand-in artifact.
- O1 (D49 ii) ran from the draft commit `bb67aa0`. Job 1032 failed in 1 s on my error: the
  source receipt named the commit through `--ref`, and the extractor admits only HEAD. Its
  3 minutes count and the retry enters the remainder rule, so T_A1 = 110, not 111. Job 1033
  built overlay `sha256:2c5f9b20...` in 47 s.
- A0a (D49 ii) ran from the read-only export of `bb67aa0`, with both halves rendered from
  the plan: VM job 1037 (90 CPUs, no GRES) and GPU job 1039 (9B, 25-minute cap, after
  1037; job 1038 was the test-only call).
  - The queue was empty before each submission. No foreign job appeared while A0a ran (25
    queue samples, 4 lane snapshots), and job ids 1032-1039 are all mine.
  - 20 of 20 episodes scored in one wave. Slot mean 219.9 s, so c_A0a = 0.003054 GPU-h;
    L_A0a = 1.887 min.
  - Truncation was 0 of 131 and 0 of 125 turns. The step p95 was 1.265 s against 5.389 s.
    There were no losses, restarts or undelivered observations.
- Constants (`render_q2_stage1_plan.py` freeze mode on the host, reproduced locally):
  c_proj 0.011274 (the card's high price binds), T_A1 110, total caps 477 min (7.950
  GPU-h), K_base 32 at the floor of 32, base unchanged, `plan_sha256` `6a3f0219...`.
  Every gate holds, so nothing sends the draft back to review. Section 6.2's table and
  section 22 record them.
- GPU-h: 0.1144 physical (1032 1 s, 1033 47 s, 1039 364 s); 31 minutes charged at caps
  (D22). The program total is 4.852 on this branch (4.9088 once `main`'s reviewer job
  1031, 0.0564 GPU-h, is merged in; corrected 2026-10-09).
- Left open: the status line, the frozen plan digest (both written at the freeze) and the
  three section 18 sign-offs (two Kevin's, one the program's decision id).
- Tests: S1a 282 passed, 1 skipped locally (12 new). On the host, a fresh export of
  `83f4127` ran under `srun -c 8` with no GRES (job 1043): 2,566 passed, 41 skipped, and
  ruff was clean on `harness/q2_stage1`, `tests` and `scripts`.
  - The first host run (job 1041) found 38 driver tests failing. The runner's D12 check reads
    `/dev/nvidia*`, which the host's bare metal has, and the tests did not stub it. That
    check came with the audit fixes, after the last host run (`e43549d`). `83f4127` makes
    the tests stand in for the GPU-less container; the code is unchanged.
  - Jobs 1040 (the sync left out the dev extra) and 1042 (a debugging `srun`) were CPU only.
  - The two evidence copies of `observation_check.py` keep one long line each, byte for
    byte as they ran.
- Evidence: `program/evidence/2026-10-09/q2-stage1-prefreeze/`. Not done: no freeze, no
  push. Next: a fresh pre-freeze audit.

## 2026-10-09 — Q2 S1a: the fresh pre-freeze audit answered, Kevin's sign-offs filled (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- Two fresh auditors read the draft at `82ff505`. Both reproduced every verdict and
  constant from the raw host records. One found the draft ready to freeze except for the
  sign-offs. The other returned two blocking items. I fixed both and every non-blocking
  item that asked for a change, and rejected none. No GPU job ran and no A0 job is owed.
- Merged `main` twice: D54 (K1 v3 wave 3) and D55 (Kevin's S1a rulings). The program total
  is 4.9088 GPU-h: main's reviewer job 1031 (0.0564) plus S1a's 0.1144. Job 1031 ran before
  O1, with the queue empty. The earlier S1a entry's "4.852" was the branch total before the
  merge; it is corrected in place.
- Blocking 1, the frozen-plan slot. `lane.load_frozen_plan` admits an A1 manifest only if
  the registration holds G0 item 10's label followed by the plan file's `plan_sha256` field
  in backticks. The file's SHA-256 (`a5f0aadc...`), printed beside it, or a value without
  backticks would make the lane refuse every A1 job under the frozen id.
  - G0 item 10 now states exactly what the freeze writes: the placeholder, and nothing else
    on its line, becomes the `plan_sha256` of
    `program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json` in backticks
    (`6a3f0219...`).
  - A new prereg test fills the slot on a scratch copy, freezes it into a copy of the
    ledger and has the lane accept an A1-9B-S1 manifest rendered from the plan. It checks
    that the lane refuses the two wrong forms and the frozen copy once edited. After the
    freeze it checks the real slot.
  - I ran the same with the CLIs on a scratch copy of the tree: freeze to row 16,
    `check-chain` (16 rows), `verify`, the A1 renderer and `lane validate` (128 base
    slots, 11 fill blocks, T_A1 110, 120 min, 90 CPUs). With one line appended to the
    frozen copy, `lane validate` and `verify` both refuse. The real ledger is unchanged.
- Blocking 2, D53 (iii)'s "very slow" clause. Section 7.3 now quotes D53 (iii) verbatim and
  states S1a's reading, with no code change:
  - an undelivered observation is a loss;
  - every attempt is bounded: a screenshot at 10 s, a checker read at the pinned 120 s or
    else at 150 s, then a transport loss;
  - an observation delivered slowly or on a retry is counted per episode as
    infrastructure and reported per cell beside the losses, and the episode is scored.
  - The program's sign-off decision must state whether this reading is accepted.
    Otherwise the draft goes back to review: a registered delay limit would change the
    driver after A0 and so repeat A0a.
  - I checked the pinned OSWorld tree on the host (read only): the pool and dev tasks'
    checkers read the guest only through `/file` and `/execute`.
- Lane admission (readiness note 8), now in code. The lane admitted A1 once the ledger had
  any row for the id. `lane.frozen_registration` now makes the checks of `preregister.py
  verify` and `check-chain`: the chain holds, the row names the registration, and the
  file's SHA-256 equals the row's. `validate_manifest` requires this for A1 and ANC at
  validate, submit and job start. The GPU half is rendered only from a validated VM
  manifest, so it is refused too.
  - O2 has no lane manifest. Before O2 the operator runs `verify` and `check-chain`
    (section 5.5).
  - New test: an edited registration refuses A1, ANC and the GPU half's rendering. A row
    moved to the edited digest breaks the chain, and a row naming only the id is refused.
    The frozen-tree fixture now freezes with `preregister.freeze`.
- Code changed after A0a (disclosed in section 22): `lane.py` (post-freeze admission only)
  and the plan renderer's docstring. Neither changes what A0a ran or measured. The VM
  manifest job 1037 ran still validates unchanged, and freeze mode still re-renders
  `plan-a0a.json` byte for byte.
- Sign-offs. Kevin's two slots in section 18 are filled from D55: item 17 accepted,
  including the unanchored read; G0 item 5's offline-setup decisions accepted. The
  program's slot (items 1-16 and 19-27; the lead-in now agrees) stays open for the
  orchestrator's decision id. That decision also states whether section 7.3's reading of
  D53 (iii) is accepted.
- Non-blocking fixes:
  - stale T_A1 numbers (6.3 now 160 VM-h and 110 min; the floor at 110 is about 721 s);
  - D49 (i) quoted exactly;
  - 7.2's transport label follows `driver.observation_loss_kind`;
  - the D11 pointer in section 2;
  - "whose `step_p95_n1_s` equals" in G0 item 1;
  - the three typed renderer inputs named in 3.2 and in the renderer's docstring;
  - the concurrency gate's looseness disclosed;
  - the O2 receipt and overlay rule;
  - evidence README notes (the two manifest digests, the empty test-only file, the host's
    registry container, checked on the host);
  - the section 22 table that a blank line had split.
- `state.json`: the S1a status, next action and audit fields are refreshed. The S1a entry
  leaves Kevin's pending list, since D55 ruled on both of his items. `HANDOFF.md` is left to
  `main`.
- Tests: S1a 284 passed, 1 skipped locally (2 new tests). Full local suite (macOS):
  2,521 passed, 88 skipped. ruff is clean on `harness/q2_stage1`, `tests` and `scripts`;
  whole-repo ruff's 251 findings are all in `main`'s K1 v3 evidence scripts.
- Not done: no freeze, no push. Next: the program's sign-off, then the freeze.

## 2026-10-09 — Q2 S1a: the freeze rehearsal answered (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- A fresh verifier rehearsed the freeze on a scratch clone of `51770da` with its own ledger
  copy (the real ledger unchanged, `cfe46a0b`). The guard refused the unfilled draft on its
  three slots only; filled, the freeze was accepted (row 16, `check-chain` and `verify`
  pass); A1-9B-S1 rendered from `plan-a0a.json` validated (128 base slots, 11 fill blocks,
  V 20, T_A1 110, 90 CPUs, 126 GB, 120 min) and its GPU half passed the docker submitter's
  dry run; a one-byte edit of the frozen copy was refused by `lane validate`, `lane submit
  --dry-run`, the GPU half's rendering and `verify`. It found the D53 (iii) reading
  faithful, sound and implemented as stated, provided the program's decision accepts it.
  Not ready: two blocking items, both fixed (registration section 22, "Freeze rehearsal").
- Blocking 1: three S1a tests failed on the frozen tree (`test_manifest_rules` for A1 and
  ANC, `test_anchor_purposes_are_refused`); they expected the pre-freeze message from the
  repository's tree. Fixed in the tests only: they validate against a tree with the splits
  and no ledger, and require a refusal from the repository's tree in either state.
- Blocking 2: the status slot covered only its bold line, and the rest of the paragraph
  ("This file has no ledger row. No confirm-split episode may run under it.") would have
  been frozen unseen by the guard (D32's defect class). Fixed: the placeholder names the
  whole paragraph; section 22 "At the freeze" states the frozen paragraph word for word,
  the three slots and the freeze steps (scratch freeze and S1a suite first; the row
  committed alone as the freeze commit; `state.json`, this log and `HANDOFF.md` after it).
  New test `test_the_status_paragraph_is_replaced_whole_at_the_freeze`.
- Non-blocking, fixed: two driver tests for delivered-slow observations (a checker `/file`
  read and the agent's screenshots: counted slow, scored); 7.3's delay sentence reworded
  (a late screenshot samples the screen later; same mechanism for both harnesses); item 13
  and the sign-off lead-in put the postconfig carve-out to the program's decision; the
  freeze commit is the commit that adds the ledger row (exports and O2's `FILL_GIT_SHA`),
  not `git_head_at_freeze` (sections 1, 5.5); item 18's missing slot explained (moot
  without the anchor).
- Re-rehearsed here on a scratch clone of `d0a0529`: filled as section 22 states (the
  frozen paragraph, `plan_sha256` `6a3f0219...` in backticks, a stand-in decision id),
  the guard accepted it, row 16 (`check-chain` 16 rows PASS, `verify` PASS); on the frozen
  tree the S1a suite gives 285 passed, 3 skipped (the R container test and the two
  draft-only prereg tests) and the other 16 test files that read the ledger 388 passed, 8
  skipped; an A1-9B-S1 manifest rendered there validated (128 slots) and was refused after
  a one-byte edit, as `verify` was. The real ledger is unchanged (`cfe46a0b`).
- Tests on the draft: S1a 287 passed, 1 skipped (3 new tests). Full local suite (macOS):
  2,524 passed, 88 skipped. ruff clean on the changed tests.
- No file of the code of record changed, no GPU job ran, no freeze, no push. Next: the
  program's sign-off decision (items 1-16 and 19-27, with section 7.3's reading of D53 (iii)
  and the postconfig carve-out), then the freeze steps of section 22.

## 2026-10-09 — Q2 S1a: D56's conditions implemented (branch `stage0/q2-stage1-rescope`, draft, not frozen)

- Merged `main` (D56, `3ee089f`) into the branch (`2beb6d6`). D56 signs items 1-16 and
  19-27 and accepts section 7.3's reading of D53 (iii). It accepts the postconfig carve-out
  on two conditions the registration must state before the freeze.
- Condition 1, per-session reporting. `analysis.infrastructure_counts` now reports every
  count of the cells per (size, harness), per (size, session) and per (size, harness,
  session): losses by type, the agent's and the checker's observations (calls, retried,
  slower than 30 s, undelivered), and the postconfig replies, failures and server errors
  (also by step type). It counts over the final records and over every attempt. Found while
  doing this: section 7.2 promised losses per job, but the report counted final records
  only, so a re-queued loss that later scored appeared nowhere. The attempts view fixes
  that.
- Condition 2, the postconfig server-error sensitivity (`analysis.postconfig_missing`,
  `sensitivity_postconfig_server_error_missing`). It recomputes every primary estimand with
  an episode treated as missing if it has any postconfig reply at HTTP >= 500 or with no
  HTTP reply. An HTTP-200 reply with a non-zero `returncode` keeps the episode, as does a 4xx.
  The sensitivity is reported beside the primary with the count of dropped episodes. No
  decision rule reads it. Sections 7.2 and 15 state it.
- Lane. Once the source tree's ledger has this id's row, `lane.validate_manifest` refuses
  every pre-freeze purpose (development, setup-check, A0a, A0b) at validate, submit and job
  start, which also blocks rendering A0a's GPU half. Job 1037's A0a manifest still validates
  on a draft tree (canonical `051cdd6e...`), and a test checks that. Tests that validated
  pre-freeze manifests against the repository's tree now use a draft tree, so the S1a suite
  holds before and after the freeze.
- Prereg. A frozen-mode test requires the program slot's id to be a `decisions.md` heading
  that names `q2-stage1-rescoped-v1` and S1a's reading of D53 (iii), with an entry that
  accepts the section 7.3 reading. In draft mode, D56 passes and D53, D55, D99 and a list
  are refused. The slot stays TBD. At the freeze it becomes the bare id D56.
- Item 13 and section 7.2's understatement, checked on the pinned OSWorld tree on the host.
  The postconfig calls handlers separate from `/execute`, which nothing earlier in most
  episodes calls. `/setup/activate_window` covers 93 postconfig steps in 92 of the 148 pool
  and dev tasks; only 2 of those tasks call it in setup. The rehearsal's 97 counted the four
  K1 raw-gold failures as well. The other handlers are close_window (6 steps), launch (8),
  upload (4) and open_file (1). On Linux, activate_window and close_window answer 200
  whatever `wmctrl` does. So the carve-out leaves a server fault on a postconfig step, either
  intermittent or lasting a whole boot in one of those handlers. Section 19 discloses it.
  D56 is cited where the draft said the decision "will state" the reading.
- Section 20: `analysis.py` `338139...` -> `eacc5716...`; `lane.py` `83a7dd46...` ->
  `d646b144...`. Section 22's "Code changes after A0a" lists them. Neither changes what A0a
  measured: the lane rules fire only on a frozen tree, and no job runs `analysis.py`.
  `records.py` and the driver are unchanged. Section 22 has a new D56 subsection. "At the
  freeze" names D56 for the slot, and the frozen status paragraph says the lane refuses
  pre-freeze purposes.
- Frozen check on a scratch clone of these changes (filled with D56, frozen into its own
  ledger copy, row 16, `check-chain` and `verify` PASS): S1a suite 289 passed, 3 skipped.
  `lane validate` refuses job 1037's manifest and the committed dev and setup-check
  manifests, and accepts A1-9B-S1 (128 slots). The real ledger is unchanged (`cfe46a0b`).
- Tests on the draft: the S1a suite has 291 passed and 1 skipped (the R container test).
  There are 4 new tests and 11 tests changed to validate pre-freeze manifests on a draft
  tree. The full local suite (macOS) has 2,528 passed and 88 skipped. ruff is clean on
  `harness/q2_stage1`, `tests` and `scripts`. All 251 whole-repo ruff findings are in
  `main`'s K1 v3 evidence scripts.
- No GPU job ran, nothing was frozen and nothing was pushed. Next: the freeze steps of
  section 22 ("At the freeze"; the program slot takes D56), then O2 and the A1 jobs from
  the freeze commit.

## 2026-10-09 — Q2 S1a frozen: `q2-stage1-rescoped-v1`, ledger row 16

- After the D56 conditions (per-session counts, the postconfig server-error
  sensitivity, the lane's refusal of pre-freeze purposes, the decision-id test)
  and a third freeze rehearsal with nothing blocking, the freeze followed section
  22 "At the freeze": the three slots filled (the frozen status paragraph, G0 item
  10's `plan_sha256` 6a3f0219..., the program slot D56), the filled file committed
  (70d57e3); a scratch freeze into a copy of the ledger passed check-chain (16 rows)
  and verify, and the S1a suite passed on the frozen copy (289 passed, 3 skipped);
  then the real freeze: row 16, registration SHA-256 f9db7cc3..., row hash
  bc5e88a0..., previous hash fde44535 (row 15), check-chain PASS, verify PASS;
  the row committed alone as the freeze commit d5f5798.
- Next: O2 and the four A1 jobs (section 5.5), each from an export of d5f5798.

## 2026-10-10 — Q2 S1a: O2 and A1 session 1 ran; session 2 9B queued

- One operator, from the freeze commit d5f5798 (read-only host export for A1; a clean
  clone detached at the commit for O2). `preregister.py verify` and `check-chain` passed
  (row 16, 16 rows) before O2 and again before each pair.
- O2 (job 1044, 47 s): overlay `sha256:10327c70...` from source archive `4a59e87c...`
  (`selected_ref: HEAD`, pre-validated on CPU with the pinned extractor so the retry could
  not be spent on job 1032's receipt error); provenance PASS; no retry.
- A1-9B-S1 (VM 1045, GPU 1047) and A1-4B-S1 (VM 1048, GPU 1050; its manifest names the 9B
  job's records and receipt by SHA-256): each dispatched 452 slots, base and all 11
  extension blocks, with no infrastructure loss, re-queue, cap truncation or USR1. DR0 does
  not fire for either. The lane's provenance, engine-argv and Slurm-limit checks passed.
  Physical GPU-h 1.2203 and 1.1469 (O2 0.0131); program total 7.2891. The queue was empty
  before each submission and no foreign job appeared.
- Session 2 9B (VM 1051, GPU 1053) is submitted and PENDING: `--begin=2026-10-10T12:45:18`
  (job 1050's EndTime plus 12 h) and `--dependency=after:1051`. Session 2 4B is not
  submitted; its manifest needs session 2 9B's records.
- No outcome was read or summarized; the analysis waits for all four jobs. The 4B GPU job
  verified the receipt file the GPU lane reads (`75ebfc53...`), which differs from G0 item
  2's CPU-lane receipt only in its registry digest (disclosed). Evidence:
  `program/evidence/2026-10-10/q2-stage1-a1/`.

## 2026-10-10 — E4 gate gauntlet wave 1 (D58): score 49, honest exit (branch `gauntlet/e4-d19`, not merged)

- Gauntlet `e4-icl-write-rule-gate` (backfill E4 = legacy D19; the gate only:
  teacher eligibility and oracle interface ceiling). Budgets: queries 150,
  wall_minutes 600, tokens 8,000,000, dollars 150, waves 3, gpu_hours 0.3.
  Discovery ran in workflow `wf_9f15e9e8-487`. Its synthesis owner stalled on a
  long recursive grep and committed nothing, so `wf_476629c2-5bc` resumed from
  synthesis. Proposal `22429938...` and DRAFT registration `4cef1c1c...`
  (commit `89ed377`; not frozen, not admitted). Audit row 1 appended to
  `program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl`, row hash
  `b658a26559a35d9d0da1e30c850fbc11d0079d4e87807eed1a87669587d7048f`.
- Reviews: 55 (claude-opus-5-5) and 49 (qwen3.6-35b-a3b, self-hosted, Slurm
  1059). Both totals equal their dimension sums and sit below every cap (74,
  79, 89). Score 49, best 49. Neither review is signed (D24).
- Blind discrimination: valid and passed. The critic judged the gate and
  2608.13385 (task vectors in multimodal ICL) different mechanisms, with the gate
  the stronger contribution. The packets match the bundle files exactly and
  name nothing. Only one prior was judged.
- Refute-first triad: 3 of 3 refuted. Novelty: the method combines published
  parts. The key-span class is the dual form (2212.10559), and the
  confined-versus-free contrast is published for KV compaction (2602.16284,
  2506.06266, 2609.17346). Those, plus 2311.07772 and 2404.11225, are uncited.
  No paper runs this measurement on few-shot ICL, so no direct prior was found.
  Identification and feasibility: below.
- Largest defect: identification. The registration fits the family constant at
  rank 8 on 4 probes per episode, while S1 (the evidence offered) fits it at full
  rank on all 16. Under the registered fit, S1's own code gives these readings:
  - A constant teacher passes the EPISODE_CONSTANT guard (D_span_B 0.63-1.33).
  - First-order and RLS teachers flip from TIE to GAP in 6 of 6 families.
  - The resample placebo that would expose this is report-only. Reviewer 1
    replicated the run byte for byte.
  Alone-encoded keys and a probe-independent per-episode shift are two more
  routes to a false GAP.
  Runner-up (feasibility, tokenizer confirmed by the recorder): the family table
  cannot be built under the registration's own rules. The teacher's tokenizer
  has no single-token digit answers, and the 40-input rule drops five families,
  while K2 stays an absolute 8 of 14. I1 and I2 rarely pass together at 16
  fitting probes, and more probes break the Step-2 cap.
- Honest exit, as in the K1 v2, Q1 and K1 v3 wave-1 rows:
  - Query budget: 159 of 150 counted queries. The cells used 144 and synthesis
    6, then the novelty refuter's 9 overran the budget.
  - Triad stop.
  - Tokens: 2.86M of 8M remain, less than any K1 v3 repair wave used.
  Not exits: tokens 5.14M of 8M, $87.33 of $150, 372.7 of 600 minutes (elapsed,
  including about 144 stalled minutes), GPU 0.0539 of 0.3. The doctor re-run is
  byte-identical to the bundle copy (FAIL, as expected).
- GPU: reviewer 2's job 1059 used 0.0539 GPU-h (scontrol RunTime 00:03:14 on 1
  H100, COMPLETED 0:0, 07:11-07:14 UTC, before the 11:30 S1a reservation; no
  leftover container). Added to the ledger as "E4 gate gauntlet wave 1
  (e4-icl-write-rule-gate, D58) open-weight review (D24)". Program total 7.3430.
  The gate itself used no GPU.
- Waiting on Kevin: whether E4 continues as a fresh run with new budgets and a
  query share reserved for the triad. A v2 DRAFT would need these CPU repairs:
  - Fit C_f on all probes, and make E and D_span count only relative to the
    placebo.
  - Add a constant-column shift to every class, and planted writers for
    contextualised keys and for the probe-independent shift.
  - Build a family table that can actually be built, with K2 counted relative to
    the families that survive.
  - Measure the I1/I2 window on real residuals. This needs approval for the
    2.7 GB teacher download.
  - Normalise the STOP_TR guard by the GOLD-versus-SHUF KL.
  - Write delta rows and blind packets for the dual-form and KV-compaction
    priors.

## 2026-10-10 — Q2 S1a analysis tooling under D59, D61 and D62 (blind)

- A blind dry run of the frozen analysis on synthetic records found eleven
  defects in the code of record. Worst: one fractional base score crashes the
  report. D59 fixes the handling (a wrapper, incomplete-data rules, operator
  steps); D61 and D62 settle three edge cases. Every rule was decided before
  any A1 outcome was read.
- `ops/s1a-analysis/` (wrapper, guard, operator scripts, RUNBOOK.md) and 71
  tests on synthetic records, merged to main (0b55ebd). Three fresh verifiers
  found three blocking items in turn, each fixed; the last was a runbook wait
  before the merge of rescoring output. Evidence:
  `program/evidence/2026-10-10/q2-stage1-d59-tooling/`.

## 2026-10-10 — Q2 S1a session 2: A1-9B-S2 and A1-4B-S2 ran; DR0 does not fire

- One operator, from the read-only export of the freeze commit `d5f5798`
  (`q2-stage1-rescoped-v1`, ledger row 16). Registered per-job checks only; no
  score, success rate or harness comparison was read.
- A1-9B-S2: VM 1051 and GPU 1053, 12:50-14:03 UTC. The VM job began at 12:50:00
  (D57), more than 12 hours after the later session-1 job. 452 of 452 episodes
  scored: the base, then the 11 extension blocks both session-1 jobs completed,
  with no fill. No infrastructure loss, re-queue, cap truncation or USR1.
  DR0 does not fire. Provenance, engine argv and the Slurm limit (110 = T_A1)
  pass. 1.2211 GPU-h physical; 0.002702 GPU-h per episode.
- A1-4B-S2 was rendered after A1-9B-S2's DR0. Its manifest names A1-9B-S1's,
  A1-4B-S1's and A1-9B-S2's records and receipts by SHA-256, and `lane
  validate` accepted it. E4's reviewer job 1061 ran from 14:05:59, after
  A1-9B-S2 ended, so the operator waited for an empty queue and idle GPUs. Then
  `ops/submit-pair.sh` submitted it as in session 1: verify and check-chain
  PASS, VM 1062, test-only 1063, GPU 1064 with the session-1 4B values.
- A1-4B-S2 ran 14:09-15:17 UTC: 452 of 452 scored, 0 losses, DR0 does not
  fire, every check passes. 1.1286 GPU-h physical; 0.002497 GPU-h per episode.
- No job of other work ran while an S1a job ran. While the session-2 9B pair was held, the
  D59 dry run's CPU jobs and E4's reviewer job 1059 ran. Between the two
  session-2 pairs, E4's reviewer job 1061 ran. Deviations: none.
- GPU: S1a post-freeze physical 4.7300 GPU-h (O2 plus four A1 jobs). Charged
  under D22: 474 of 477 minutes. Program total 9.6927 (ledger sum).
- Evidence: `program/evidence/2026-10-10/q2-stage1-a1/` (`a1-9b-s2/`,
  `a1-4b-s2/`, README extended). Next: an independent verification of the
  session-2 checks, then the registered analysis under the D59 runbook.

## 2026-10-10 — E4 gate gauntlet run 2 (D60): score 60, honest exit; E4 ends (branch `gauntlet/e4-d19`, not merged)

- Fresh run under D60 in workflow `wf_65f4f5ac-a69`, with new budgets: queries
  80 (30 reserved for the triad), wall_minutes 600, tokens 8,000,000, dollars
  150, waves 1, gpu_hours 0.3. A single owner did the CPU-only repair: proposal
  `f27ece07...`, DRAFT registration `e4-icl-write-rule-gate-v2` (`8f935cc4...`;
  v1 unedited and superseded), registered estimator as code, family table rebuilt
  under the teacher's tokenizer, I1/I2 window, priors cited after OpenReview and
  ACL Anthology searches (commit `300bb62`; not frozen, not admitted). Audit
  row 2 (gauntlet wave 2, run wave 1) appended to
  `program/gauntlet/2026-10-10-e4-icl-write-rule-gate.jsonl`, row hash
  `8ccad64644134faec52e9e480c72f8aaa13fac89063cc222ccfbd38cf24948db`.
- Reviews: 60 (claude-opus-5-5) and 64 (qwen3.6-35b-a3b, self-hosted, Slurm
  1061). Reviewer 2 returned total 59, but its ten scores sum to 64 and no cap
  binds. Its schema has the consumer re-check the total, so the record uses 64
  and keeps 59 beside it. Score 60 (59 if the produced total were kept), best
  60. Trajectory 49 -> 60. Neither review is signed (D24).
- Blind discrimination: passed by the letter, weakly. The critic told the gate
  and Attention Matching with Cartridges (2602.16284, 2506.06266, 2609.17346)
  apart, and judged the prior the stronger contribution but not strictly
  dominant. The packets match the bundle files exactly. Only one prior was
  judged; the dual-form packet was not.
- Refute-first triad: 3 of 3 refuted (each refuter ran at least six orx
  queries: 10 plus 1 OpenReview, 7, 6). Novelty: a recombination, no direct
  prior. 2605.16591 (an in-span decomposition of the n-shot state with a
  mismatched-dictionary null) was retrieved four times in wave 1 and never
  opened; 2508.17032 and 2305.12766 are uncited (cap 74).
- Largest defect: identification, again (both reviewers). The registered
  S_span key set includes a family-fitted key map B, unconstrained in rank and
  chosen by development fit. When a family's per-episode write reads from a
  fixed subspace of 8 dimensions or fewer, B collapses onto it, and
  key-independent writers read TIE 6/6 through every gate STOP_SPAN needs.
  Retrieval among stored tasks that share a read subspace does the same.
  Swapping in another episode's keys leaves the fit unchanged (0.966 vs 0.966),
  while a first-order writer drops (0.949 to 0.523). Reviewer 1 replicated this
  with its own code. The registration has no key-resample placebo, and I1 reads
  raw read energy.
  Runner-up (decisiveness): the lookup families A1 and A2 are SPAN_VACUOUS by
  construction, yet still pass through I3 and I7, whose failure ends the whole
  gate as INSTRUMENT_FAIL. On lookup-structured planted episodes I7 fails 6/6
  and I3 5/6, so the gate's expected end once K2 passes is INSTRUMENT_FAIL.
- Honest exit: D60's stop line (identification is still the largest defect),
  the wave cap (waves=1) and the triad stop. Under D60, E4 ends here. Not
  exits: queries 57 of 80, tokens 4.96M of 8M, $89.28 of $150, 415.6 of 600
  minutes (about 217 of them a host wait for S1a), GPU 0.0533 of 0.3. The
  doctor re-run is byte-identical to the bundle copy (FAIL, as expected).
- GPU: reviewer 2's job 1061 used 0.0533 GPU-h (scontrol RunTime 00:03:12 on 1
  H100, COMPLETED 0:0, 14:05:59-14:09:11 UTC, no leftover container). It was
  submitted after S1a's session-2 9B jobs 1051 and 1053 completed, with the
  queue empty and re-checked in the submit command. S1a's operator saw it and
  waited, then submitted the 4B session-2 jobs 1062 and 1064 at 14:09:27, at
  most about 3.5 minutes later than otherwise. No S1a job ran during it. Added
  to the ledger as "E4 gate gauntlet wave 2 (fresh run 2 under D60,
  e4-icl-write-rule-gate-v2 draft) open-weight review (D24)". Program total
  7.3963 on this branch (S1a session-2 jobs are not yet in the ledger). The gate
  itself used no GPU.
- Waiting on Kevin: nothing, to stop. Reopening E4 would be a new owner
  decision. It would need a decision-bearing key-resample placebo (or a
  rank-constrained B), I1 on the task-relevant subspace, and per-family
  I2/I3/I7 with the lookup families exempt, all in one new version. It would
  also need d90, noise SDs and planted recovery measured on real residuals
  (the 2.7 GB teacher download), and the 2605.16591, 2508.17032 and 2305.12766
  delta rows.

## 2026-10-10 — C3 Stage-0 gate gauntlet wave 1 (D64): score 54, honest exit (branch `gauntlet/c3-selection`, not merged)

- Wave 1 ran in workflow `wf_c299aa22-d28` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed one
  synthesis owner, who wrote proposal `366b3537...`, DRAFT registration
  `c3-selection-allocation-gate-v1` (`2de3359e...`; not frozen, not admitted)
  and the evidence bundle (evidence root `7b8612b9...`) at `4d29497`. Audit
  row 1 is appended to
  `program/gauntlet/2026-10-10-c3-selection-allocation-gate.jsonl`, row hash
  `e7b2dc726dd3037a8e953f5dcc52efa4621cfd3241c117a72b56e5ac1a57fa8e`.
- Reviews: 56 (claude-opus-5-5) and 54 (qwen3.6-35b-a3b, self-hosted, Slurm
  1070). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 54, best 54. Neither review is signed (D24).
- Blind discrimination is recorded as FAIL. The critic judged the gate and
  CASE (2608.17124) the same mechanism, with CASE the stronger contribution,
  and called the gate "a stricter, narrower pilot" of it. The critic also named
  three CASE weaknesses that the gate fixes, so the prior is stronger but not
  strictly dominant. Reviewer 1 read this as a weak pass by the letter, and
  reviewer 2 read it as failed. The score does not change, because 74 does not
  bind. The packets match the bundle files exactly. Only CASE was judged.
- Refute-first triad: 3 of 3 refuted.
  - Novelty: a recombination plus one model-and-workload cell. PAIR
    2609.36461 already reports pre-answer linear probes in thinking mode at
    within-question AUC 0.79 and 0.87. The cells retrieved it three times
    and never read it.
  - Identification: the registered answer position moves with the answer's
    leading character under Qwen3's BPE, so a gate can learn a tokenizer
    artefact. F's estimand is also mismatched.
  - Feasibility: see the largest defect below.
- Largest defect: feasibility and decisiveness. This is reviewer 1's choice.
  Reviewer 2 named the identification artefact, and the recorder ranks it
  second because it is cheap to repair and does not matter while D, F and H
  are never read.
  - Measured Qwen3-8B thinking data (2609.32035, Tables 8, 9 and 13) cannot
    meet the 8.0 GPU-h cap rule (N >= 560), the S line (kappa6 >= 0.10) and
    I6 (at least 80 mixed held-out questions) at the same time.
  - MATH-500-level workloads are admissible, but there kappa6 <= 0.063 and
    at most about 45 mixed held-out questions are possible.
  - AMC- and AIME-level workloads are INFEASIBLE.
  - So the gate's likely verdicts are INFEASIBLE or INCONCLUSIVE_N with
    STOP_SPREAD. Both are predictable with no GPU, and neither reads D, F
    or H.
- Honest exit applies for two reasons.
  - Query budget: 146 of 150 are used. The cells used 129; the bundle says 127
    because two asset-cell calls whose output was discarded were missed. The
    refuters used 17. The 4 queries left cannot fund a rule-compliant wave
    2, whose triad alone needs at least 18.
  - Triad stop: 0 of 3 refuters failed to refute.
- Exits that do not apply: tokens 4.05M of 8M, $71.08 of $150, 103.5 of 600
  minutes, wave 1 of 3. A second wave at this cost would land near the token
  and dollar caps. The doctor re-run at record time is byte-identical to the
  bundle copy (FAIL, as expected).
- GPU: reviewer 2's job 1070 used 0.0553 GPU-h (scontrol RunTime 00:03:19 on
  1 H100, COMPLETED 0:0, 15:57:23-16:00:42 UTC, no leftover container). It
  was submitted while only S1a's CPU rescore jobs 1065-1068 were running, so
  the host rule held. It is added to the ledger as "C3 Stage-0 gate gauntlet
  wave 1 ... open-weight review (D24)". The program total is 7.4516 on this
  branch. The gate itself used no GPU.
- Waiting on Kevin: whether C3 continues.
  - To stop: nothing further is needed.
  - To continue, a fresh run with new budgets would need a new versioned
    registration with:
    - a decision-bearing zero-GPU feasibility pre-check from measured Qwen3-8B
      anchors;
    - D, F and H separated from S, with N and I6 re-derived from fitted-gate
      simulations;
    - a format-invariant answer position;
    - F redefined as the paired increment, and a floor with answer-string,
      logit-gap and self-certainty features;
    - delta rows for PAIR, 2610.00296 and Xpbbetf285.
  - Alternatively, an admission above 8 GPU-h under D24 (about 13 to 26
    GPU-h of caps for an AMC- or AIME-level workload).

## 2026-10-10 — Q2 S1a registered analysis: DR2 Inconclusive, DR5 INCONCLUSIVE (S1b not admitted); not externally anchored

- One analyst followed `ops/s1a-analysis/RUNBOOK.md` at `6d85529` (D59, D61, D62)
  on the host, from the read-only export of the freeze commit `d5f5798`. The code
  of record was unchanged and provenance passed. Every Slurm job was CPU-only
  with no GRES: rescoring 1065-1068 (`--time=08:00:00`, 3 h 08-3 h 12 each,
  exit 0), report 1071, identity 1072, first divergence 1073, GLMM 1074 and
  assembler 1075, 15:23-18:56 UTC. Labels: data complete, "not externally
  anchored".
- Primary set (base, 32 tasks, 512 episodes): success 4B 28.91% (H-OSW-fixed)
  and 26.56% (H-GA); 9B 32.81% and 28.91%. δ = −3.12 pp (paired t p = 0.367,
  90% t interval [−8.91, 2.66]). X sign flip p = 0.459. D_b = 11.33% [5.86,
  17.19] and D_w = 12.50%. Excess −1.17 pp (one-sided UB 0.78). π_small = 0.055
  (one-sided [0.000, 0.260]).
- Rules: DR0 and DR1 do not fire. DR2 is Inconclusive: not Present, and not
  near-equivalent (the δ interval crosses −7.5 pp and the π bound is above
  0.12). DR4 does not fire (at most 0.002702 GPU-h per episode against
  0.011274). DR5 is INCONCLUSIVE against M = 0.13, so S1b does not go to the
  gauntlet (D47). DR-A: ANCHOR-UNAVAILABLE. Predictions: P1 falsified; P2-P5
  stand.
- Sensitivities: corrected verdicts 0 flips. Metric-exception-missing (1
  episode) and postconfig server-error-missing (0 episodes, D56) are identical
  to the primary. With flagged tasks excluded, δ is −2.50 pp; DR2 and DR5 read
  the same. Secondary set (113 tasks): δ −1.11 pp, π_small 0.084 [0.020, 0.162];
  it enters no rule. GLMM: the primary fit (the registered reading) did not
  converge and its LRT was not computed. The secondary fit converged (task:harness
  LRT p 0.045), which is not a decision input. 9B session shift +5.47 pp
  (p 0.016), which no rule reads.
- Infrastructure over 1,808 episodes: 0 losses, 0 restarts, 0 retried, slow or
  undelivered observations, 0 postconfig server errors. Truncation at most
  0.44% (no label). Rescoring 452/452 rows per job; 16 secondary verdicts fell
  back to live scores (`53ad5833` needs live state).
- Deviation: D59 (i)'s wrapper only. The identity check passed in fractional
  mode (14 fractional base scores). D61 and D62 were not triggered. Merges and
  the report reproduced byte for byte on the Mac. The runbook's independent
  verification (step 12) and a second check of the session-2 per-job lane
  checks are still open.
- GPU: none for the analysis; ledger unchanged at 9.746.
- Evidence: `program/evidence/2026-10-10/q2-stage1-analysis/`; results:
  `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md`. Waiting on Kevin:
  whether to commission the registered follow-up after INCONCLUSIVE (more
  sessions at 4B and 9B, as a new proposal with its own gauntlet).

## 2026-10-10 — Q2 S1a results: review fixes (no estimand, rule or decision changes)

- Two review lenses (a recompute and a claims check) read `RESULTS.md` at
  `23fd973`. The recompute reproduced every output it could re-run off the host
  (not the GLMM fits) and raised four informational items, one a rounding slip.
  The claims check raised four minor and three informational items. All are
  fixed in `RESULTS.md` and the analysis README; none is rejected.
- Added: the D57 disclosures (both 4B GPU jobs' receipt `75ebfc53...`; S2 9B
  begin moved to 12:50:00), the D63 disclosure (reviewer job 1061 in the
  session-2 gap) and D64 for job 1070 during the CPU analysis. Licence scope:
  this host, image and lane (D53), and section 19's harness x session effect
  inside δ. P1's falsification is decided by 4B; 9B's session test rejects
  (p 0.016) for these two sessions.
- GLMM reworded: the registered (primary-set) fit did not converge, so no
  registered GLMM evidence; the secondary-set LRT (p 0.045, boundary 0.023) is
  secondary, non-confirmatory evidence of harness-specific task variance, not
  a decision input. The section 10.1 attribution of "no interaction claim" is
  dropped.
- DR3: C_z (−0.0078 each size) and V_z added; ρ undefined by the frozen code
  (V_z ≤ 0), 0.667 for 4B if section 9 item 8's formula is read literally.
  Corrected-verdict sources split as 511 + 1 (merge rule) on the base and
  1,791 + 1 + 16 live on the secondary set. 9B/H-OSW-fixed mean steps 11.80.
  The CPU-only basis of the analysis jobs restated (receipt fields are
  constants written after the guards).
- New descriptive file `q2-stage1-analysis/post-review/post-review.json`
  (`post_review.py`, committed files only): setup, evaluation and engine queue
  times (section 2 item 5; the engine queued no request), the exact sign-flip
  p-values (X 0.4531, session 4B 0.5625, 9B 0.0156; registered Monte Carlo
  0.4588, 0.5631, 0.0163) and the DR3 inputs.
- The runbook's step-12 verification still has no committed record. GPU: none.

## 2026-10-10 — E5 first-step gauntlet wave 1 (D67): score 54, honest exit (branch `gauntlet/e5-d20`, not merged)

- Wave 1 ran in workflow `wf_a885a6df-60d` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Scope: the language-free
  decomposition only (decay against interference under re-segmentation of
  English episodes on GatedDeltaNet-1.3B and RWKV-7 1.5B World); translation
  work is out of scope. Four discovery cells fed one synthesis owner, who wrote
  proposal `5c12ae3a...`, DRAFT registration
  `e5-gate-fertility-decomposition-v1` (`f4abf428...`; not frozen, not
  admitted) and the evidence bundle (evidence root `dab86d8e...`) at
  `31dd50b`. Audit row 1 is appended to
  `program/gauntlet/2026-10-10-e5-gate-fertility-decomposition.jsonl`, row hash
  `8b808c0c5a91720c6ee9152a71488a64e22cfd740b2bb6275ecb8b86b9d05800`.
- Reviews: 57 (claude-opus-5-5) and 54 (qwen3.6-35b-a3b, self-hosted, Slurm
  1081). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 54, best 54. Neither review is signed (D24).
- Blind discrimination is recorded as PASS by the rule's letter, and weak. The
  critic told the proposal and Lee et al. (2609.33093) apart
  (same_mechanism=false) and judged the prior the stronger contribution, but
  called the proposal "the cleaner causal test of one sub-question", so the
  prior is stronger, not strictly dominant. Reviewer 2 wrote "strictly
  dominant", which the critic did not. Both reviewers apply 74 for incomplete
  coverage anyway. The packets match the bundle files exactly. Only Lee et al.
  was judged.
- Refute-first triad: 3 of 3 refuted.
  - Novelty: a trivial recombination. The per-token clamp is Tallec and
    Ollivier's time-warping condition (1804.11188) applied to the decay term,
    and it is already legacy D20's span oracle; patching NIE as mediation is
    2606.27510. No direct prior was found.
  - Identification: the K = 1 foils are fresh codes, so K = 1 is a presence
    test likely at ceiling, which halves beta; the clamp's NIE absorbs the
    decay-by-write interaction (S1's own worlds: pure decay cost 16-45
    points against NIE 8-14; the audit row's "17-45" is a rounding slip, the
    W6 K = 4 value is 16.2).
  - Feasibility: the registered reading is not decisive at its line; no
    harness, adapter, manifest or measured throughput exists; subject G is
    neither on the host nor licensed.
- Largest defect: the identification and decisiveness of the registered kill
  reading (both reviewers; the identification and feasibility refuters). With
  the registered estimator, a true K = 4 decay secant at the 3-point line reads
  KILL with probability 0.955 / 0.776 / 0.636 at discordance 0.1 / 0.2 / 0.3
  (reviewer 1's rerun), against a stated false-kill rate of 0.05-0.11. S1 and
  S2 never run the f_p fallback, the line is carried from exact match to
  forced choice without calibration, and passages cluster within at most 120
  WikiText-103 articles. All of these push toward KILL, the expected reading,
  which leads to the same action as not running the step.
- Honest exit applies for two reasons.
  - Query budget: 135 of 150 are used (cells 120, novelty refuter 10,
    identification refuter 5, feasibility refuter 0; 8 OpenAlex calls were
    refused with HTTP 429 and are not counted). The 15 left cannot fund a
    rule-compliant wave-2 triad, which needs at least 18.
  - Triad stop: 0 of 3 refuters failed to refute.
- Exits that do not apply: tokens 3.27M of 8M (main-session tokens shared
  with four other gauntlets included), $54.81 of $150, 142.9 of 600 minutes,
  wave 1 of 3. The doctor re-run at record time is byte-identical to the
  bundle copy (FAIL, accepted 0, cap 89, as expected).
- GPU: reviewer 2's job 1081 used 0.0544 GPU-h (scontrol RunTime 00:03:16 on
  1 H100, COMPLETED 0:0, 22:42:29-22:45:45 UTC, no leftover container). It
  was submitted after S2's reviewer job 1079 cleared and no S1a job was
  running or pending, so the host rule held. It is added to the ledger as "E5
  first-step gauntlet wave 1 ... open-weight review (D24)". The program total
  is 9.8557 on this branch. The step itself used no GPU.
- Process defects: the feasibility refuter ran no discover query and the
  identification refuter 5, below six each; one critic call only; seven
  background ledger sources closed on abstracts; reviewer 2's operator wrote
  one scontrol snapshot into the host run root and removed it at once
  (disclosed).
- Waiting on Kevin: whether E5 continues.
  - To stop: close D20 by citing 2609.33093, the dossier's own fallback.
  - To continue, a fresh run with new budgets would need a v2 registration
    that drops the K = 1 presence test from the primary statistic (or uses
    in-episode foils) under a ceiling gate, adds a DECAY-ONLY arm at canonical
    writes and reports PIE, NIE and INT, recalibrates the line in
    forced-choice units, re-runs S1 and S2 through primary_f with
    article-level clustering, conditions KILL on median R_F >= 1.5, and
    credits the span oracle, Tallec and Ollivier, and 2606.27510.
  - Either way, data-rights decision 1: subject G
    (m-a-p/1.3B-100B-GatedDeltaNet-pure@930ed6ae) has no licence; the
    apache-2.0 fallback differs in architecture and data.
## 2026-10-10 — S2 gauntlet wave 1 (D67): score 49, no honest exit; candidate does not proceed as drafted (branch `gauntlet/s2-locale`, not merged)

- Wave 1 ran in workflow `wf_a8edb476-c40` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed one
  synthesis owner, who wrote proposal `e16214cf...`, DRAFT registration
  `s2-arabic-cua-locale-v1` (`866f994d...`; not frozen, not admitted) and the
  evidence bundle (evidence root `39112668...`) at `1ac9837`. The scope is
  Phase 0 (CPU: Relay's chrome strings into catalogs, locale as a fixture
  parameter, oracle gate G1-G12) and the design of Phase 1 (Stage 1a cap 2.0
  GPU-h, Stage 1b cap 15.0 GPU-h; admission is Kevin's under D24). Audit row 1
  is appended to `program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`,
  row hash `1a24cee8e8ec3a9874ed56cd84b35690709ce3d538b93243f0b51e14ac6e6657`.
- Reviews: 58 (claude-opus-5-5) and 49 (qwen3.6-35b-a3b, self-hosted, Slurm
  1079). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 49, best 49. Neither review is signed (D24).
- Blind discrimination: PASS. The critic judged the proposal and macOSWorld
  (2506.04135) different mechanisms and the proposal the stronger
  contribution. The packets match the bundle files exactly. Only macOSWorld
  was judged.
- Refute-first triad: 3 of 3 refuted.
  - Novelty: no direct prior, but a textbook 2x2 on a split macOSWorld
    names. Every cell exists already (Force RTL, en-XB, UIMirroring). G5's
    reflection rule is claimed by an uncited IBM patent family (US9529606B1
    and others, priority 2015). The estimand, chrome localization over an
    English workspace, is narrower than macOSWorld's full localization.
  - Identification: `<html dir>` also sets the bidi direction of chrome
    strings. P0.4 isolates content only and G8 checks content only, so en-RTL
    and ar-LTR each carry their own reordering artefact (a Chromium probe on
    Relay reproduced them). That biases D by (s_arL - s_enR)/2 and T by the
    opposite amount. The gate seeds never render the aurora fixture, K3 has
    no reference hashes for analysed seeds, and G3 contradicts P0.2.
  - Feasibility: the budget fits, but the first GPU step is not decisive (see
    the largest defect).
- Largest defect: decisiveness of the Phase 1 design on Relay. Reviewer 1
  names it alone; reviewer 2, whose 49 is the score, names it together with
  the identification confound, which the recorder ranks second (it is a
  specification repair and matters only if Phase 1 can run).
  - The proposal's own Monte Carlo gives P(gate PASS) 0.000 in three
    scenarios and at most 0.039 in the fourth. The unconditional chance of a
    PRESENT call on a real -5 pp effect is about 0.015.
  - The feasibility refuter's recomputation: a PASS needs at least 15
    informative tasks at S1a's variance and the central price, so at least 9
    of Relay's 12 workflows solved in 2 or more of 8 English pixel episodes.
    Relay's own record shows 0 of 12 frontier-model pixel workflow runs
    completed.
  - The gate's tau2 floor (0.0025) is below the simulated heterogeneity of a
    -5 pp effect (0.006-0.017), so even a PASS would not give 80% power.
  - So Stage 1a's 2.0 GPU-h buys an infrastructure exit that can be
    forecast now at 0 GPU-h. Route R2 (a LibreOffice 2x2 on S1a's harness,
    about 31-37 informative tasks) is recorded but not designed.
- No honest exit applies: wave 1 of 3, tokens 3.35M of 8M, $61.57 of $150
  (list-price equivalent), 141.6 of 600 minutes, no direct prior, no safety
  failure. The triad result means the candidate does not proceed as
  drafted, so the row's termination_reason is null. Queries: 123 of 150
  (cells and synthesis 113, novelty refuter 10; the identification and
  feasibility refuters ran none, below the rule's six each). The 27 left fund
  at most one compliant repair wave. The doctor re-run at record time is
  byte-identical to the bundle copy (FAIL, as expected).
- The design study (`stage0/q2-design-study`, 79096f8) still has no S2 power
  section. The S2 gate was sized independently from S1a's records and must
  be reconciled when that section lands.
- GPU: reviewer 2's job 1079 used 0.0553 GPU-h (scontrol RunTime 00:03:19 on
  1 H100, COMPLETED 0:0, 22:38:48-22:42:07 UTC, no leftover container). It
  was submitted after two read-only squeue checks showed an empty queue, so
  the host rule held. It is added to the ledger as "S2 gauntlet wave 1 ...
  open-weight review (D24)". The program total is 9.8566 on this branch.
  Phase 0 and Phase 1 used no GPU.
- Waiting on Kevin: whether S2 continues to a repair wave, and with which
  repair.
  - (a) Redesign Phase 1 on route R2 and keep Relay Phase 0 as
    infrastructure only, with the bidi, G3, G6, K3 and aurora fixes.
  - (b) Keep Relay. Register Phase 0 as infrastructure only and replace
    Stage 1a with a screen of at most 0.3 GPU-h whose stop rule is the
    gate's real pass condition, with tau2 fixed at 0.006 or more (design
    decision 9). By the registration's own text, this closes Phase 1 on
    Relay now.
  - Design decision 1 (a standalone 2.0 GPU-h Stage 1a) should not be
    accepted on the current design.
## 2026-10-10 — E7 G1 floor gate gauntlet wave 1 (D67): score 51, no honest exit (branch `gauntlet/e7-d22`, not merged)

- Wave 1 ran in workflow `wf_39e89052-5e0` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed one
  synthesis owner, who wrote proposal `7f1179c3...`, DRAFT registration
  `e7-equivariant-writes-g1-v1` (`cce49578...`; not frozen, not admitted)
  and the evidence bundle (evidence root `886240b3...`) at `623abb6`. Audit
  row 1 is appended to
  `program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl`, row hash
  `34901a11f8d9009d52e525d54bf440b6a2ba4419b24dd78ac4e1596dff430388`.
- Reviews: 51 (claude-opus-5-5) and 51 re-checked (qwen3.6-35b-a3b,
  self-hosted, Slurm 1077). Reviewer 2 returned 46, but its ten scores sum to
  51 and no cap binds: an arithmetic error, as in E4's job 1061. As in E4
  row 2, the re-checked totals are used. Score 51, best 51 (46 if the
  produced total were kept; nothing depends on it). Neither review is signed
  (D24).
- Blind discrimination: a weak pass by the letter. The critic judged the
  gate and 2610.06750 (Balancing Memory Pathways) not the same mechanism, and
  the prior the stronger contribution, while crediting the gate's controls
  and cross-lingual angle, so not strictly dominant. The packets match the
  bundle files exactly. Only 2610.06750 was judged.
- Refute-first triad: 3 of 3 refuted.
  - Novelty: a recombination, not a direct prior. 2609.33093, SWAX
    (2509.24552) and Griffin (2402.19427) already measure state-carried recall
    and its window dependence, and the translated key is the cross-lingual
    needle protocol of MLNeedle and OneRuler. Griffin was never cited or
    retrieved, and MLNeedle and OneRuler were not re-read.
  - Identification: see the largest defect. CROSS and BIND also reward
    surface cues, and the FAIL_CROSS sub-label confounds pathway with
    distance.
  - Feasibility: the caps fit (7.733 GPU-h), but the step is not decisive
    for the same CUT reason. The measured NTREX test pool (median 676) is
    smaller than S1 assumes (900).
- Largest defect (both reviewers): the CUT check rests on a false premise and
  is evaluated first. The registration says the state cut "removes every
  path from the facts to the query" (L365-367), but the registered cut resets
  the GDN states once after the facts block and leaves SWA untouched
  (L420-422). SWA relays the facts into post-cut GDN writes, so a model that
  really carries facts in its state can be labelled INSTRUMENT_INVALID. Two
  refuters and reviewer 1 showed the leak by complex step on S3's model; the
  recorder re-ran reviewer 1's script and reproduced it exactly (single cut
  0.94-1.01 of uncut; state zeroed across the gap exactly 0). The fact-write
  ablation (v = 0) leaks the same way. Next in line: the CROSS/BIND
  surface-cue confound (a length-plus-punctuation oracle picks the target
  among 8 NTREX keys 52-66% of the time).
- No honest exit applies. Queries 113 of 150 (the cells and synthesis used
  98, one more than the bundle's 97 because the frontier's first call was a
  byte-identical duplicate; the novelty refuter used 15, three of them
  OpenAlex 429s; the identification and feasibility refuters used none,
  below the six-per-refuter rule). Tokens 3,762,329 of 8M, $64.07 of $150,
  151.0 of 600 minutes, wave 1 of 3. The triad stop blocks freezing v1. The
  doctor re-run at record time is byte-identical to the bundle copy (FAIL,
  as expected).
- GPU: reviewer 2's job 1077 used 0.0583 GPU-h (scontrol RunTime 00:03:30 on
  1 H100, COMPLETED 0:0, 22:30:55-22:34:25 UTC, no leftover container). The
  queue was empty before submission, so the host rule held. It is added to
  the ledger as "E7 G1 floor gate gauntlet wave 1 ... open-weight review
  (D24)". The program total is 9.8596 on this branch. The gate itself
  used no GPU.
- Waiting on Kevin: whether E7 continues to wave 2.
  - The repair is CPU-only: a v2 draft with a path-complete cut (state zeroed
    from the facts to the answer, verified on the real module graph) or CUT
    demoted to a descriptive read; ABLATION with beta = 0, gated separately
    for MONO and CROSS; surface-matched distractors and controls for CROSS;
    a B1 attention-only read; S1 re-run on the measured pool; delta rows for
    Griffin, 2609.33093 and SWAX.
  - Stopping is also reasonable: even a repaired gate is a weak lever on
    E7's main question (owner's prior P(PASS) about 0.1).
## 2026-10-10 — C5 FP4 instability gauntlet wave 1 (D67): score 54, no honest exit (branch `gauntlet/c5-fp4`, not merged)

- Wave 1 ran in workflow `wf_32e68e61-0d6` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed one
  synthesis owner, who wrote proposal `3195b9a2...`, DRAFT registration
  `c5-fp4-instability-v1` (`6d1a786a...`; not frozen, not admitted) and the
  evidence bundle (evidence root `5c254eda...`) at `341e314`. Scope: Phase 0
  (registered caps 3.05 GPU-h) and the design of Phase 1 (central 45.0 GPU-h
  with two runs per GPU, 68.1 without). Audit row 1 is appended to
  `program/gauntlet/2026-10-10-c5-fp4-instability.jsonl`, row hash
  `65266173a930eeb1dcda24d4825e8dc9482afa36fd33bdc5da47e89e21cb621c`.
- Reviews: 54 (claude-opus-5-5) and 65 (qwen3.6-35b-a3b, self-hosted, Slurm
  1083). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 54, best 54. Neither review is signed (D24).
- Blind discrimination passed by the letter, weakly. The critic judged the
  proposal and 2505.19115 ("FP4 All the Way") different mechanisms, with the
  prior the stronger contribution, and called the proposal "methodologically
  cleaner" and a gap-filler, so the prior is stronger but not strictly
  dominant. The packets match the bundle files exactly. Reviewer 1 notes the
  packet tests the wrong prior for the mechanism claim: 2510.25602 had no
  packet.
- Refute-first triad: 3 of 3 refuted.
  - Novelty: NARROWED, not OCCUPIED. No paper trains E2M1 and INT4 crossed
    with power-of-two and non-power-of-two scales. But H_int ("power-of-two
    scales penalise INT4 more"), which the proposal calls its own mechanism,
    is 2510.25602 Theorems 1-2. ARITH 2025 (labelled closed access, but open
    on NSF PAR) has the block-size leg at tensor level. 2302.08007 (returned
    by KS-20, never cited) already ties a tensor metric to training loss.
  - Identification: G1's runs are reused as two Stage 1b cells, which biases
    P2 toward REFUTED given G1 (0.086-0.178 against about 0.05 with fresh
    seeds). I_blk measures crest factor, not power-of-two waste. I_fmt also
    changes UE4M3 range. The endpoint carries forward-pass quantization noise.
  - Feasibility: Phase 0 only certifies the instrument. The kill result (G1,
    P about 0.5) first appears in Stage 1a above 8 GPU-h, and sigma is never
    measured below 8 GPU-h. Within-budget defects: the J0 cap is copied from
    another job, Inductor's FP32 division rounding is unpinned, and
    determinism is stated for J2 only.
- Largest defect: identification of the central registered test (P2/H_int),
  framed by uncredited published theory. This is reviewer 1's choice;
  reviewer 2 named the gate-reuse part together with the sigma point. Neither
  a CONFIRMED nor a REFUTED P2 could be attributed to the stated mechanism.
  Second: decisiveness (no step under 8 GPU-h measures sigma or the anchor
  gap).
- No honest exit applies at wave 1. Exits checked: wave 1 of 3; tokens
  3.66M of 8M; $67.63 of $150 (list-price equivalent); 158.2 of 600 minutes;
  GPU 0.0583 of 0.3; no novelty invalidation (narrowed, no reject); Safety
  PASS. The query budget binds. On the bundle's rule (every orx discover
  invocation counts, including rejections), 132 of 150 are used and 18 remain.
  That is exactly a compliant wave-2 triad, with nothing left over for the
  synthesis owner. On the narrower reading (results only), 115 are used. No
  wave 3 is fundable. The candidate does not proceed as drafted (triad 3/3).
  Whether wave 2 runs is the orchestrator's and Kevin's call.
- The doctor re-run at record time is byte-identical to the bundle copy
  (FAIL: Novelty, Design and Compute). Process defects:
  - The feasibility refuter ran no orx query.
  - The synthesis note gives a stale registration hash ("fc3b29cc...").
  - OpenAlex rejected 17 of 132 invocations.
- GPU: reviewer 2's job 1083 used 0.0583 GPU-h (scontrol RunTime 00:03:30 on
  1 H100, COMPLETED 0:0, 23:12:37-23:16:07 UTC, no leftover container). It
  was submitted after three empty read-only squeue checks (no S1a job), so
  the host rule held. It is added to the ledger as "C5 FP4 instability
  gauntlet wave 1 ... open-weight review (D24)". The program total is 9.8596
  on this branch. Phase 0 and Phase 1 used no GPU.
- Waiting on Kevin or the orchestrator:
  - whether C5 runs wave 2, repairing the largest defect in a new versioned
    attempt: credit 2510.25602 and ARITH; restrict P2 to I_fmt or add a
    UE4M3+FP32/B32 pair; register a range-confound rule; use fresh seeds for
    the gate cells; pin autocast off; rerun the blind critic against the
    mechanism prior;
  - whether to register a sigma-and-anchor probe under 8 GPU-h after J1;
  - the FineWeb-Edu and tokenizer downloads (possibly already covered by D1);
  - Phase 1 admission (D24), whatever the score.
## 2026-10-10 — E3 Stage-0 headroom probe gauntlet wave 1 (D67): score 52, honest exit (branch `gauntlet/e3-d18`, not merged)

- Wave 1 ran in workflow `wf_5b779bc0-dee` (one of the five D67 gauntlets)
  with declared cumulative budgets: queries 150 (at least 30 reserved for the
  triad), wall_minutes 600, tokens 8,000,000, dollars 150, waves 3, gpu_hours
  0.3. Four discovery cells fed one synthesis owner, who wrote proposal
  `782cbf31...`, DRAFT registration `e3-byte-boundary-headroom-v1`
  (`30f1fe76...`; not frozen, not admitted) and the evidence bundle (evidence
  root `60e5e933...`) at `9d79644`. Audit row 1 is appended to
  `program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl`, row hash
  `13d97526e18462751b8234676a118bed333d313458b93615cb50f62e60762d59`.
- Reviews: 52 (claude-opus-5-5) and 57 (qwen3.6-35b-a3b, self-hosted, Slurm
  1085). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 52, best 52. Neither review is signed (D24).
- Blind discrimination is recorded as a weak PASS by the rule's letter. The
  critic told the probe and token alignability (2502.06468) apart and judged
  the prior the stronger contribution as a finding, but the probe the better
  methodology, so the prior is not strictly dominant. Reviewer 2 read it as
  "strictly dominant", which the critic did not say. The score does not
  change, because 74 does not bind. The packets match the bundle files
  exactly. Only token alignability was judged (no SOMBRERO packet).
- Refute-first triad: 3 of 3 refuted.
  - Novelty: a recombination of published parts (token alignability's
    question, boundary Dice, SOMBRERO's circular-shift null, kappa_M-form
    normalization, SMT phrase-consistency cuts); kappa_M and the SMT
    bilingual-segmentation lineage are missing from the ledger.
  - Identification: see the largest defect below.
  - Feasibility: at published EN-ZH aligner error (AER about 0.18-0.27) the
    rule never returns NO_HEADROOM under correlated errors, and the registered
    compute fails on the pinned stack (fp32 against hnet's bf16 flash-attention
    asserts; mamba_ssm@a6a1dae cannot import under transformers 5.15.0).
- Largest defect: the decision statistic does not read translation-specific
  placement at the registered operating point. Both reviewers name it.
  - At EN-ZH stage 1, with Chinese calibrated to the English count, the
    Chinese side covers about 0.85-1.0 of its canonical gaps (one chunk per
    character; H-Net paper Chinese 2-stage BPIC 5.81).
  - The floor shifts only side b, so it collapses onto the system, and S is
    driven by Chinese density and the English word-end miss rate. With perfect
    Chinese placement, a 3% English miss gives S about 0.8 (a HEADROOM call)
    at density about 0.9 but 0.947 at density 0.54, against a 0.03 gap between
    the decision lines.
  - Every threshold was tuned on simulations in another regime (budget near
    the cut count; independent aligner errors at AER 0.03-0.13), and no
    registered gate catches the collapse.
- Honest exit applies for two reasons.
  - Query budget: 137 of 150 are used. The cells used 122; the bundle says
    118 because four asset-cell calls whose output the wrapper truncated were
    rerun and only the reruns were counted. The refuters used 15 (novelty 8,
    identification 0, feasibility 7; six calls overall were OpenAlex 429s).
    The 13 left cannot fund a rule-compliant wave 2, whose triad alone needs
    at least 18.
  - Triad stop: 0 of 3 refuters failed to refute.
- Exits that do not apply: tokens 3.84M of 8M, $66.43 of $150, 163.2 of 600
  minutes, wave 1 of 3. The doctor re-run at record time is byte-identical to
  the bundle copy (FAIL, as expected).
- GPU: reviewer 2's job 1085 used 0.055 GPU-h (scontrol RunTime 00:03:18 on
  1 H100, COMPLETED 0:0, 23:14:17-23:17:35 UTC, no leftover container). It
  was submitted while only the C5 gauntlet's reviewer-2 job 1083 was running
  on another GPU, so the host rule held. It is added to the ledger as "E3
  Stage-0 headroom probe gauntlet wave 1 ... open-weight review (D24)". The
  program total is 9.8563 on this branch. The probe itself used no GPU.
- Waiting on Kevin: whether E3 continues.
  - To stop: nothing further is needed.
  - To continue, a fresh run with new budgets would need a new versioned
    registration with:
    - the decision at a common budget no larger than the consistent-cut count
      (or a density and ceiling-minus-floor validity gate), a symmetric
      floor, and calibration on canonical boundaries;
    - thresholds re-derived from simulations at that budget with AER-matched,
      correlated aligner errors, or aligner error measured on XL-WA en-zh gold
      (R5);
    - a cut-count-preserving alignment control in place of I1, and line M at
      the treatment's budget;
    - bf16 (or fp32 encoder-only extraction) and a working overlay proven by a
      container smoke;
    - a reason why headroom in monolingual checkpoints may stop Stage 1;
    - delta rows for kappa_M and the SMT segmentation lineage, and a SOMBRERO
      blind packet.
  - Sign-offs R1-R5 (registration sec. 16) also remain open.

## 2026-10-10 — C5 FP4 instability gauntlet run 2 (D68): score 58, honest exit; C5 stops (branch `gauntlet/c5-fp4`, not merged)

- Fresh run under D68 in workflow `wf_9e0ea822-f4e`, with new budgets: queries
  80 (30 reserved for the triad), wall_minutes 600, tokens 8,000,000, dollars
  150, waves 1, gpu_hours 0.3. A single owner did the CPU-only repair (commit
  `aafa69d`): proposal `2b9d768a...` and DRAFT registration
  `c5-fp4-instability-v2` (`4db20a54...`; v1 unedited and superseded; not
  frozen, not admitted). It credits the power-of-two-scale penalty to
  2510.25602 Theorems 1-2 and ARITH 2025, and narrows P2 to I_prec32 (E8M0
  against BF16 scales at B32). The gate moves into Phase 0 as J4 on its own
  probe seeds, which also measure sigma and the anchor. Caps are recomputed.
  Audit row 2 (gauntlet wave 2, run wave 1) is appended to
  `program/gauntlet/2026-10-10-c5-fp4-instability.jsonl`, row hash
  `875e04dd427c4ee2bcbe2583ebada40416a19ba5f860db8b669e8d0e55675afa`.
- Reviews: 58 (claude-opus-5-5) and 71 (qwen3.6-35b-a3b, self-hosted, Slurm
  1087). Each total equals the sum of its ten scores. No cap binds (reviewer 1
  applies 74, 79 and 89; reviewer 2 applies 79 and 89). Score 58, best 58.
  Trajectory 54 -> 58 (reviewer 1 54 -> 58, reviewer 2 65 -> 71). Neither
  review is signed (D24).
- Blind discrimination passed by the letter, weakly. The packet now pairs the
  proposal with the mechanism prior (2510.25602 with ARITH 2025). The critic
  judged them the same mechanism, which is true by construction because the
  proposal now tests a published prediction. It judged the prior the stronger
  contribution but not strictly dominant: it credits the proposal with the
  first training test of the 4-bit INT claim and sharper identification. The
  packets match the bundle files exactly. Only one prior packet was judged.
- Refute-first triad: 3 of 3 refuted. Each refuter ran at least six orx
  queries (11 plus 1 OpenReview, 7, 7).
  - Novelty: a trivial recombination, no direct prior (NARROWED). Two
    training precedents are uncredited. 2510.25602 App. D.2 Table 10 already
    trains the BF16-against-UE8M0 scale contrast at INT8 (0.0018 nats at
    B32, 0.0267 at B256; 145M, 20B tokens, single runs). 2505.14302 Fig. 2
    trains INT4 against E2M1 by group size with full-precision scales.
  - Identification: J4's C0 drives the verdicts (below).
  - Feasibility: J4 fits inside 8.0 GPU-h only at about 277k tok/s or more
    per process, and Phase 0 reruns are not counted against the line.
- Largest defect (reviewer 1, authoritative; the identification refuter
  agrees): J4's probe statistic C0 sets G1, Phase 1's seed count n and P2's
  ABSENT band. C0 is measured at one untuned LR on three probe seeds (df 2)
  and selected by G1. Its LR artefact (SD about 0.010 nats at curvature 0.02)
  is the size of the credited anchor (0.011).
  - In the bundle's own power-sim-v2.json, end-to-end wrong-decisive reaches
    0.131 at half the registered effect size. The registration says "at or
    below 0.08 in every reported cell"; that holds only at the registered
    size (at most 0.072).
  - G1 says GO 0.14-0.29 under a tuned-LR null with LR spread, against a
    nominal 0.05.
  Reviewer 2 named the missing executable pilot instead. That defect is
  structural (cap 79) and binds every candidate here.
- Relation to wave 1's largest defect: what wave 1 named is repaired. P2 is
  identified by design, the mechanism is credited, and no gate run enters a
  Phase 1 estimate. The new defect descends from wave 1's gate-reuse part:
  the selected probe statistic now enters the decision rule instead of the
  estimates. That is the same defect class by another route, as with E4
  under D63; on a strict reading it is not the same defect.
- Honest exit: D68's stop line (D60's rule) applies on its score prong
  (58 < 60), whichever reading of the largest-defect prong is taken. The wave
  cap (waves=1) and the triad stop also apply. C5 stops here: v2 is not
  frozen and not admitted.
  - Not exits: queries 42 of 80; tokens 3.21M of 8M; $53.85 of $150
    (list-price equivalent); 115.0 of 600 minutes; GPU 0.0553 of 0.3.
  - Gauntlet cumulative over both rows: 174 queries, 6.87M tokens, $121.48,
    273.2 minutes, 0.1136 GPU-h.
  - The doctor re-run is byte-identical to the bundle copy (FAIL: Novelty
    and Compute).
- Process defects:
  - Only one blind critic call ran; the design-prior packet was not judged.
  - Reviewer 2 misread the blind result ("distinct mechanism") and the
    novelty refuter's verdict. It also said the uncredited priors "are now
    credited" and that the design has "fallbacks and explicit D22 counting".
    Its scores are recorded as produced.
  - The repaired package still says "costs GPU time, not a false claim"
    (proposal L88-89) and "wrong decisive at most 0.08" (registration
    L556-559), and presents N3's tautological toggles as identification
    evidence. None of these was edited (rule 3).
- GPU: reviewer 2's job 1087 used 0.0553 GPU-h (scontrol RunTime 00:03:19 on
  1 H100, COMPLETED 0:0, 01:10:48-01:14:07 UTC on 2026-10-11, no leftover
  container). It was submitted after read-only squeue checks at 01:09:59 and
  01:10:39 and an in-command re-check showed an empty queue (no S1a or other
  job), so the host rule held. Added to the ledger as "C5 FP4 instability
  gauntlet wave 2 (fresh run 2 under D68, c5-fp4-instability-v2 draft, Phase
  0 and Phase 1 design) open-weight review (D24)". Program total 10.1379 on
  this branch. Phase 0 and Phase 1 used no GPU; the repair, the refuters and
  reviewer 1 made no host contact.
- Waiting on Kevin: nothing, to stop. Reopening C5 would be a new owner
  decision. One new version would need all of the following:
  - the ABSENT margin taken from Phase 1's own tuned-LR anchor, with its
    uncertainty;
  - G1 computed on LR-matched probe configurations;
  - Phase 0 reruns counted under D22, with a fallback J4 that always fits;
  - delta rows for 2510.25602 Table 10 and 2505.14302;
  - a cpu-doctor orx node as the first executable evidence.
  Phase 1 admission and any 100 still need D24.
## 2026-10-10 — E5 first-step gauntlet run 2 (D68): score 51, honest exit; E5 ends (branch `gauntlet/e5-d20`, not merged)

- Fresh run under D68 in workflow `wf_7f7725c7-157`, with new budgets: queries
  80 (30 reserved for the triad), wall_minutes 600, tokens 8,000,000, dollars
  150, waves 1, gpu_hours 0.3. A single owner did the CPU-only repair (commit
  `fff98da`): proposal `22b43bcf...`, DRAFT registration
  `e5-gate-fertility-decomposition-v2` (`a0bbd08b...`; v1 unedited and
  superseded; not frozen, not admitted). The repair removed K = 1, chose one
  primary load on held-out episodes under a ceiling gate, put the line on a
  guessing-corrected scale, made the design a 2 x 2 factorial (CAN, DEC,
  CLAMP, NAT) with TE = PNIE + PNDE + INT exact, gated KILL on median
  R_F >= 1.5, and credited 2606.27510, legacy D20's span oracle and Tallec and
  Ollivier. Audit row 2 (gauntlet wave 2, run wave 1) is appended to
  `program/gauntlet/2026-10-10-e5-gate-fertility-decomposition.jsonl`, row
  hash `18e2060ef99f0a8bae988f29bdd19bb3b8bdaac84e3e28a437c449737f58bbe7`.
- Reviews: 61 (claude-opus-5-5) and 51 (qwen3.6-35b-a3b, self-hosted, Slurm
  1089). Each total equals the sum of its ten scores, and no cap binds (74, 79
  and 89 all apply). Score 51, best 54. Trajectory 54 -> 51, a dip of 3:
  reviewer 1 rose 57 -> 61 (wave 1's named identification mechanisms are
  repaired), reviewer 2 fell 54 -> 51. Neither review is signed (D24).
- Blind discrimination: passed by the letter, weakly, for the second time. The
  critic told the proposal and Lee et al. (2609.33093) apart and judged the
  prior the stronger contribution, but called the proposal "crisper and more
  falsifiable", so the prior is stronger, not strictly dominant. Reviewer 2
  again wrote "strictly dominant", which the critic did not. The packets match
  the bundle files exactly. Only one prior was judged; the Boesch and Wee
  packet the repair prepared was not.
- Refute-first triad: 3 of 3 refuted again (orx discover queries 9, 8, 8).
  - Novelty: a trivial recombination, no direct prior (NARROWED). The 2 x 2 is
    VanderWeele's three-way decomposition (2013), and LongMamba (2504.16053),
    Zhan et al. (2409.18962) and 2204.05192 are published decay-mass alignments
    at inference; none is cited. The repair's two OpenAlex mediation queries
    had failed with HTTP 429.
  - Identification: KILL comes from the new R_F guard, not from decay. R_F is
    an unweighted median pooled over every layer-head (G) or layer-channel (R),
    most of which retain nothing across the passage. With the bundle's own
    toy and estimator, KILL reads with probability 1.00 when decay is inert,
    when the fact-carrying unit fully self-normalises while a per-token clock
    would cost 42.4 points per log-f (once two fast units per slow unit are
    pooled), and under partial self-normalisation with DOSE up to 4.6 times
    the line. DOSE, the only arm that separates these worlds, is descriptive.
  - Feasibility: S2v2 draws arm noise per episode (within-article contrast ICC
    0.001-0.039) although four episodes share a passage. At an ICC of
    0.11-0.32 a true null reads KILL per subject 0.63-0.92 (f_p 2.7) and
    0.49-0.81 (f_p 2.0); two-subject power is unreported, and decide_overall
    has no INFEASIBLE branch. Reviewer 1 shows one episode per article at the
    same episode count removes most of the loss at no GPU cost.
- Largest defect: the identification of the decision-bearing KILL reading,
  through the pooled R_F guard and the fertility-scaled line (both reviewers;
  the identification refuter). With identical contrasts, decide_subject reads
  SELF_NORMALIZED at a pooled R_F of 1.49 and KILL at 1.51. Runner-up: the
  article-clustering decisiveness gap above.
- Honest exit: D68's stop line. The score is 51, below 60. The same-defect
  prong also holds by category: wave 1's specific mechanisms (K = 1 at ceiling;
  the clamp NIE absorbing INT) are repaired, but identification of the KILL
  reading is again the largest defect, as D63 read E4's. The wave cap
  (waves=1) and the triad stop also apply. Under D68, E5 ends here. Not exits:
  queries 37 of 80, tokens 2.95M of 8M, $53.92 of $150, 121.1 of 600 minutes,
  GPU 0.0553 of 0.3. The doctor re-run is byte-identical to the bundle copy
  (FAIL, accepted 0, cap 89, as expected). Gauntlet-cumulative: 172 queries,
  6.22M tokens, $108.73, 264.0 minutes, 0.1097 GPU-h over two rows.
- GPU: reviewer 2's job 1089 used 0.0553 GPU-h (scontrol RunTime 00:03:19 on 1
  H100, COMPLETED 0:0, 01:21:17-01:24:36 UTC on 2026-10-11, no leftover
  container). It was submitted after read-only squeues at 01:19:31 and
  01:20:42 showed an empty queue, re-checked in the submit command, so the
  host rule held. Added to the ledger as "E5 first-step gauntlet wave 2 (fresh
  run 2 under D68, e5-gate-fertility-decomposition-v2 draft) open-weight review
  (D24)". The program total is 10.1379 on this branch. The step itself used no
  GPU.
- Process defects: one critic call only (Boesch and Wee packet not judged);
  the repair's OpenAlex mediation queries failed and LongMamba, named in wave
  1, is still uncredited; reviewer 2 reversed the identification refuter's
  inert-decay point and glossed the ICC (operator observations); the
  identification refuter misreported one file hash suffix (part.json, contents
  as reported).
- Waiting on Kevin: nothing, to stop. Closing D20 by citing 2609.33093 is the
  dossier's own fallback. Reopening E5 would be a new attempt with its own id
  and gauntlet. It would need, in one version: the R_F guard on retaining
  units (weighted), KILL gated also on DOSE, dose-normalised contrasts and
  S1v2 worlds with a minority of retaining units; one episode per article (or
  an ICC-sized n) with two-subject power and an INFEASIBLE branch; a
  registered precision and measured throughput; credit for VanderWeele,
  LongMamba, Zhan et al. and 2204.05192 with one blind critic call per prior
  packet; and a harness (cap 79). Data-rights decision 1 for subject G is moot
  while E5 stays closed.
## 2026-10-10 — E3 Stage-0 headroom probe gauntlet wave 2 (fresh run under D68): score 49, honest exit, E3 ends (branch `gauntlet/e3-d18`, not merged)

- The one repair run D68 allowed ran in workflow `wf_f6d515f0-29f` with newly
  declared cumulative budgets: queries 80 (at least 30 reserved for the
  triad), wall_minutes 600, tokens 8,000,000, dollars 150, waves 1, gpu_hours
  0.3. A single owner repaired wave 1's defects on the Mac CPU (common
  word-gap budget, two-sided floor, two-family consensus ITG target, error
  model at published aligner rates, band and gold attenuation paths, working
  stack on paper) and wrote proposal `cfacf766...`, DRAFT registration
  `e3-byte-boundary-headroom-v2` (`8dc19cb8...`; v1 `30f1fe76...` unedited;
  not frozen, not admitted) and the bundle (evidence root `7f4562d6...`) at
  `39f2b35`. Audit row 2 (gauntlet wave 2, wave 1 of the fresh run) is
  appended to `program/gauntlet/2026-10-10-e3-byte-boundary-headroom.jsonl`,
  row hash `81dc7ba66213b7f07d16c009726128d1e5002954331c09bc21df265d183dc06f`.
- Reviews: 55 (claude-opus-5-5) and 49 (qwen3.6-35b-a3b, self-hosted, Slurm
  1091). Each total equals the sum of its ten scores, and no cap binds (74,
  79 and 89 all apply). Score 49, best 52. Trajectory 52 -> 49: a dip of 3,
  recorded as is. Reviewer 1 rose 52 -> 55 (controls +2 after the density
  collapse was repaired); reviewer 2 fell 57 -> 49 (mechanism 7 -> 3,
  evaluation 7 -> 4, feasibility 5 -> 3). Neither review is signed (D24).
- Blind discrimination: a weak PASS by the rule's letter, as in wave 1. The
  critic told the probe and token alignability (2502.06468) apart and judged
  the prior the stronger contribution, while rating the probe ahead on rigor;
  the prior is not strictly dominant. Reviewer 2 again read "strictly
  dominant", which the critic did not say. Only one critic call ran: the
  SOMBRERO packet was not judged, and the newly raised prior has no packet.
- Refute-first triad: 3 of 3 refuted (queries: novelty 12, identification 7,
  feasibility 7; the repair used 20; 46 of 80 in all).
  - Novelty: the recombination prong. Yarmohammadi et al. 2013 (I13-1141)
    already scores a segmenter's boundaries against alignment-consistent
    split points (P/R/F1); permutation trees, Kuhn 2004 and Artstein and
    Poesio 2008 are also uncited. No direct prior was found for the object
    (learned byte boundaries across translations).
  - Identification: the kill and the monolingual guard are reachable only by
    oracle systems (`M_high` is the truth oracle); one oracle attenuation is
    applied to every system although real aligner errors are concentrated;
    line M's tie convention moves it by 0.03-0.04.
  - Feasibility: see the largest defect below.
- Largest defect (both reviewers; recorder reproduced): the registered rule
  cannot reach a verdict on its default path, and the proposal reports
  decisiveness for a rule the registration does not use.
  - `final_verdict()` needs the primary system AND line M at H for HEADROOM.
    Without R5 (XL-WA EN-ZH, which needs contacting Babelscape) the band path
    divides line M by alpha_min 0.52-0.58, so any monolingual reference with
    true S above about 0.5 is never H.
  - At the published aligner rates, band-path final P(decisive) is 0.136
    (0.125 over random-displacement systems), against the 0.51 the proposal
    reports from primary-only verdicts, and P(HEADROOM) is 0.00 for every
    primary true S of 0.42 or less. NO_HEADROOM fires only near true S 1.00.
    The recorder re-ran reviewer 1's recomputation on the committed
    `oc-decisions.json` (byte-identical output).
  - Only the gold path is decisive (0.78), and its asset is not in hand.
- Wave 1's largest defect (density collapse at the stage-1 EN-ZH point) is
  repaired and not reproduced. The new defect is a different mechanism but
  repeats wave 1's secondary theme (verdicts unreachable at the realistic
  operating point).
- Honest exit: D68's stop line applies on its score prong (49 is below 60),
  so E3 ends here. The wave cap (waves=1) and the triad stop also apply.
  Exits that do not apply: tokens 3.04M of 8M, $59.82 of $150, 125.4 of 600
  minutes, 46 of 80 queries. The doctor re-run at record time is
  byte-identical to the bundle copy (FAIL, as expected).
- GPU: reviewer 2's job 1091 used 0.0572 GPU-h (scontrol RunTime 00:03:26 on
  1 H100, COMPLETED 0:0, 01:30:01-01:33:27 UTC 2026-10-11, no leftover
  container). The queue was empty before and at submission, so the host rule
  held. It is added to the ledger as "E3 Stage-0 headroom probe gauntlet wave
  2 ... open-weight review (D24)". The program total is 10.1398 on this
  branch. The probe itself used no GPU.
- Waiting on Kevin: nothing to stop E3. Reopening it would be a new decision
  and a new proposal, needing line M as a relative comparison rather than a
  conjunct (or R5 as a prerequisite), operating characteristics under the
  final rule with non-oracle references, per-system attenuation, XL-WA EN-ZH
  in hand, a BinaryAlign inference path, and delta rows plus blind packets
  for Yarmohammadi 2013 and SOMBRERO.
## 2026-10-10 — S2 gauntlet wave 2 (fresh run under D68): score 59, honest exit, S2 ends (branch `gauntlet/s2-locale`, not merged)

- The one repair run D68 allowed ran in workflow `wf_cd7039f6-9e8` with newly
  declared cumulative budgets: queries 80 (at least 30 reserved for the
  triad), wall_minutes 600, tokens 8,000,000, dollars 150, waves 1, gpu_hours
  0.3. A single owner repaired wave 1's defects on the Mac CPU and wrote
  proposal `c13c8464...`, DRAFT registration `s2-arabic-cua-locale-v2`
  (`a2aaaed9...`; v1 `866f994d...` unedited; not frozen, not admitted) and the
  bundle (evidence root `d92056da...`) at `2a362a6`. S2 moved off Relay onto
  Q2's certified OSWorld stack: Qwen3.5-9B, both harnesses, S1a's lane and
  cost card, and 26-43 S1a tasks the agent solved at least once in English
  (LibreOffice; Thunderbird and GIMP conditional). Every catalog string is
  wrapped in FSI...PDI in all four cells, a factorial render oracle (O1-O6)
  certifies the cells, and the Phase 1 caps are 5.98-7.98 GPU-h. Audit row 2
  (gauntlet wave 2, wave 1 of the fresh run) is appended to
  `program/gauntlet/2026-10-10-s2-arabic-cua-locale.jsonl`, row hash
  `89ebed59c3b079f7b73a67e1c1c74515e03db20498b6400067e905dd29fad128`.
- Reviews: 61 (claude-opus-5-5) and 59 (qwen3.6-35b-a3b, self-hosted, Slurm
  1095). Each total equals the sum of its ten scores, and no cap binds
  (reviewer 1 applied 74, 79 and 89; reviewer 2 applied 79 and 89). Score
  59, best 59. Trajectory 49 -> 59. Reviewer 2 rose 49 -> 59 (evaluation
  +2, safety +2, six dimensions +1); reviewer 1 rose 58 -> 61 (feasibility
  +2 and review quality +2, but mechanism 6 -> 4). Neither review is signed
  (D24).
- Blind discrimination: PASS. The critic judged the proposal and macOSWorld
  (2506.04135) different mechanisms and the proposal the stronger
  contribution, citing the verified 2x2 that splits the drop into text and
  direction effects. The packets match the bundle files exactly. Only
  macOSWorld was judged.
- Refute-first triad: 3 of 3 refuted (queries: novelty 12, identification 7,
  feasibility 7; the repair used 22; 48 of 80 in all).
  - Novelty: the recombination prong only. No paper crosses interface text
    with layout direction for any agent, but every component is prior art
    by the proposal's own ledger, the decomposition move is published
    (macOSWorld App. D.1, PuMVR), and application-level localization does not
    decompose macOSWorld's full-system drop.
  - Identification: the null is reachable only through a degraded English
    cell; selection on English success pushes D towards PRESENT_HARM for any
    decorrelating perturbation, with no placebo cell; P6's screen-half share
    is about 1 for every task; the isolation misses LibreOffice's
    configuration-registry labels, and the gettext sheet prefix renames
    Sheet2, which task 42e0a640's checker reads.
  - Feasibility: see the largest defect below.
- Largest defect (both reviewers; recorder re-ran reviewer 1's check
  byte-identical): at K = 26, the task count Phase 0 is most likely to admit
  and also K_min, Phase 1 can confirm that mirroring hurts but cannot
  falsify it.
  - P3 and P4's only falsifier, an unqualified SMALL, is impossible at K =
    26-31 by the registration's own text. At K = 26 it needs the en cell
    below 0.459 against S1a's 0.625.
  - The 0.89-0.97 headline power is a uniform logit shift. Under the
    task-specific perturbation the proposal calls plausible (simulated by
    the repair only at D = 0), PRESENT at -5 pp is 0.45 at K = 26 and 0.70 at
    K = 43, and INCONCLUSIVE is 0.67-0.70 under the matching null.
  - No slack at K_min: step-0-invalid episodes are not re-queued (one task
    drops with probability 0.68 at a 1% mismatch rate), and no outcome is
    registered below 26.
  - Wave 1's specific defect (Relay's 18 tasks; P(PRESENT | -5 pp) about
    0.015) is repaired. This is the same category, decisiveness of the
    first GPU step, in a narrower form.
- Honest exit: D68's stop line on its score prong (59 < 60), so S2 ends. The
  defect prong also fires under the category reading D63 applied to E4; the
  wave cap and the triad stop apply too. Counters: queries 48 of 80, tokens
  3.72M of 8M, $74.91 of $150 (list-price equivalent), 168.6 of 600
  minutes, GPU 0.0606 of 0.3. The doctor re-run at record time is
  byte-identical to the bundle copy (FAIL, as expected; only Design changed,
  FAIL to PASS).
- The design study's S2 section (`926c63e`) and D69 landed after this
  repair was committed. They put a 5 pp gate at about 100-115 distinct tasks
  at S1a-like heterogeneity (0.60-0.62 on 64 LibreOffice pool tasks), which
  corroborates the largest defect. D69's sentence that the repair "uses
  these figures" does not describe this repair, which sized Phase 1 with
  its own simulation. Reviewer 2 saw both records; reviewer 1 did not.
- GPU: reviewer 2's job 1095 used 0.0606 GPU-h (scontrol RunTime 00:03:38 on
  1 H100, COMPLETED 0:0, 02:14:12-02:17:50 UTC, no leftover container). It
  was submitted after read-only squeue checks and an in-command re-check
  showed an empty queue, so the host rule held. It is added to the ledger as
  "S2 gauntlet wave 2 ... open-weight review (D24)". The program total is
  10.1432 on this branch. Phase 0 and Phase 1 used no GPU. The recorder's
  one read-only ssh (02:23:52 UTC) found the queue empty and all GPUs at
  0 MiB.
- Waiting on Kevin: nothing to stop. Reopening S2 would be a new owner
  decision with a new registration id. A v3 would need a P3/P4 falsifier
  reachable at the admitted K, decisiveness shown under the perturbation
  structure (or about 100 tasks), step-0 re-queue, a placebo layout cell, a
  complete wrap set and a task-specific P6. Any 100 still needs the trust
  store (D24).
## 2026-10-11 — E7 G1 floor gate gauntlet fresh run 2 (D68): score 51, honest exit; E7 ends (branch `gauntlet/e7-d22`, not merged)

- The fresh run ran in workflow `wf_75d16c52-9a6` with newly declared
  cumulative budgets: queries 80 (at least 30 reserved for the triad),
  wall_minutes 600, tokens 8,000,000, dollars 150, waves 1, gpu_hours 0.3. One
  repair owner wrote proposal `67d0a4fe...`, DRAFT registration
  `e7-equivariant-writes-g1-v2` (`b8830fa6...`; not frozen, not admitted; v1
  `cce49578...` unedited) and the bundle update (evidence root `0d975c11...`)
  at `86258d4` and `728aeef`. Audit row 2 (gauntlet wave 2, wave 1 of the
  fresh run) is appended to
  `program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl`, row hash
  `779bbc0b98ff72b300879a212ab8ea0da6b6cf219f96c6a023b182610f46e160`.
- The repair fixed wave 1's largest defect. CUT is replaced by REACH under a
  path-complete SPAN_CUT (exactly zero at d_f >= 1,561; S3v2's complex step
  equals the symbolic count on 504 rows) and ISO. Only deterministic harness
  checks now come before PASS. It also added cross-script cells with
  surface-twin decoys and a SEM line, re-ran S1v2 on the measured design, and
  reframed the gate as a no-novelty precondition.
- Reviews: 59 (claude-opus-5-5) and 51 re-checked (qwen3.6-35b-a3b,
  self-hosted, Slurm 1093). Reviewer 2 returned 47, but its ten scores sum to
  51 and no cap binds: the same arithmetic error as row 1's job 1077. As in
  row 1 and E4 row 2, the re-checked totals are used. Score 51, best 51 (47
  if the produced total were kept). Trajectory 51 -> 51. Neither review is
  signed (D24).
- Blind discrimination: a weak pass by the letter. The critic judged the gate
  and 2610.06750 not the same mechanism and the prior the stronger
  contribution, while calling the gate the more rigorous, narrower design.
  The packets match the bundle files exactly. The SWAX packet was prepared
  but not judged (one critic call per run).
- Refute-first triad: 3 of 3 refuted (26 counted queries: 12, 7 and 7).
  - Novelty: a recombination the proposal concedes, about 0.55; no direct
    prior. Coverage residuals: no Semantic Scholar or citation-graph pass,
    2610.00232 in a ledger row from its abstract, 2609.32102 unscreened.
  - Identification: see the largest defect. RELAY_BLOCK also keeps the
    convolution, so the "state-only" reads X1_state and I1_state include an
    attention route; and the single-seed futility stop returns FAIL_MONO in
    0.524 of runs in the registration's own lottery world.
  - Feasibility: the caps fit (7.767 GPU-h, host idle), but X1_attn is read
    under SPAN_CUT at B1, which also zeroes the state while the query is
    encoded, so the FAIL_CROSS sub-label is biased towards "representational".
    Without LOTTERY, P(decisive) is 0.77 (SD 0.03) and 0.62 (SD 0.06), not
    0.89 and 0.91.
- Largest defect (both reviewers): PASS's semantic claim is not identified.
  SEM's surface-twin decoy and the sliding block match punctuation counts,
  length and named-entity count, not punctuation positions. NFKC maps the
  Chinese full-width ，：；（）？！ to ASCII, and the filter only excludes
  shared tokens of four characters or more, so key and translation share
  these marks at preserved positions. On the bundle's own builder, a
  position-only rule picks the target 0.187 of the time with the real query
  and 0.131 with the decoy (SEM about 0.063, twice the line), and the
  registered S1v2 then reads PASS 0.767 for a surface-only model (the
  registration claims 0.000). The refuter's position-plus-length rule reads
  0.977. The recorder re-ran reviewer 1's three scripts unchanged: every value
  is equal. This is wave 1's second-ranked defect (the surface-cue confound)
  in narrower form.
- Honest exit: D68's stop line applies on its score prong (51 < 60; 47 as
  produced; reviewer 1's 59 alone is also below 60). Under the specific
  reading of the defect prong it does not fire (the CUT premise is repaired);
  under D60's category reading it does (identification is again the largest
  defect). The run's wave cap and the triad stop also apply. E7 ends here;
  v2 is not frozen or admitted. Queries 63 of 80, tokens 3,308,377 of 8M,
  $70.26 of $150, 153.7 of 600 minutes, GPU 0.0547 of 0.3. Gauntlet totals:
  176 queries, 304.7 minutes, 7.07M tokens, $134.33, 0.113 GPU-h over two
  rows. The doctor re-run at record time is byte-identical to the bundle copy
  (FAIL, as expected; it parses gpu_hours 0.3 as 0, left as declared).
- GPU: reviewer 2's job 1093 used 0.0547 GPU-h (scontrol RunTime 00:03:17 on
  1 H100, COMPLETED 0:0, 01:55:24-01:58:41 UTC, no leftover container). The
  queue was empty before submission and at the in-command re-check, so the
  host rule held; the recorder's read-only check at 02:09:46 UTC found the
  queue empty and all GPUs at 0 MiB. It is added to the ledger as "E7 G1
  floor gate gauntlet fresh run 2 under D68 ... open-weight review (D24)".
  The program total is 10.1373 on this branch. The gate used no GPU.
- Waiting on Kevin: nothing to stop. Reopening E7 would be a new owner
  decision with new budgets and a v3 registration id: decoys matched on
  punctuation order and position (or shared punctuation dropped) with a
  position-aware B-SURF oracle, a state-only RELAY_BLOCK, a single-boundary
  attention-only read at B1 with positive controls, a non-decisive futility
  stop, and a Semantic Scholar pass. Wave 1's value-of-information doubt
  (owner's prior P(PASS) about 0.1) stands.

## 2026-10-11 — S2 v3 gauntlet wave 1 (D71 ii): score 60, no honest exit; candidate does not proceed as drafted (branch `gauntlet/s2v3-locale`, not merged)

- Wave 1 ran in workflow `wf_59308530-d56` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed one
  synthesis owner. The owner wrote proposal `d4e1f765...`, DRAFT registration
  `s2-arabic-cua-locale-v3` (`74f969e1...`; not frozen, not admitted; v2
  unedited) and the evidence bundle (`685da276...`, evidence root
  `5820c999...`) at `4d8e17e`. Scope: Phase 0 as an executable CPU pilot,
  plus the Phase 1 design (a 2x2 census of 106 OSWorld LibreOffice tasks,
  n = 4, cap 6.10 GPU-h). The audit row starts the new file
  `program/gauntlet/2026-10-11-s2v3-arabic-cua-locale-pilot.jsonl`, row hash
  `8b0c6ef5297b123c98d5b6bc24089f8807dc744e5e7a71c71c778409827d25f5`.
- Pilot: four CPU-only Slurm jobs (1097-1100; 1096 cancelled), no GRES,
  `--network=none`, each on an empty queue, in the LO-VM container
  (`f5b4c40e...`), about 20 minutes in all.
  - UIMirroring is pixel-identical to SAL_RTL_ENABLED.
  - A pinned SheetPrefix fixes the translated default sheet name.
  - Window titles are identical across cells for the 104 of 106 tasks that
    opened.
  - AT-SPI extents cannot certify mirroring (a median 53% of matched
    accessibles keep their unmirrored extents).
  - Not built or run: the derived Arabic image, the VM-lane oracle and P0.6.
    The three Launchpad packages wait on a go-ahead.
- Reviews: 61 (claude-opus-5-5) and 60 (qwen3.6-35b-a3b, self-hosted, Slurm
  1102). Each total equals the sum of its ten scores. No cap binds (reviewer 1
  applied 74, 79 and 89; reviewer 2 applied 79 and 89). Score 60, best 60.
  Neither review is signed (D24).
- Blind discrimination: PASS. The critic judged the proposal (A) and
  macOSWorld (2506.04135) to be different mechanisms, and the proposal the
  stronger contribution. The packets match the bundle files, and the prompt
  names nothing. Reviewer 1's caveat: paragraph A presents checks that were not
  run, or did not discriminate, as done. Only macOSWorld was judged.
- Refute-first triad: 3 of 3 refuted (35 counted queries: 21, 7 and 7).
  - Novelty: no direct prior. It is a recombination: OSWorld's own LibreOffice
    domains, the census variance of 2411.00640, a bioequivalence ratio margin
    and shipped LibreOffice keys. The measured object is narrower than
    macOSWorld's open split.
  - Identification: census D also includes generic screen-change fragility.
    Under direction-free reshuffles the realized D has an SD of 1.59-2.67 pp,
    PRESENT_HARM comes out at 0.12-0.22, and there is no placebo. The
    sharp-null guard is miscomputed, and admission depends on how the
    treatment renders.
  - Feasibility: see the largest defect. Phase 1's fit also depends on an
    unadopted cap rule (19.1 GPU-h under S1a's c_proj).
- Largest defect (both reviewers and the feasibility refuter): the pilot
  decides neither K0 nor K1 of Phase 0, and the run that could decide them
  cannot start with the assets that exist.
  - No real or full pseudo-Arabic catalog was rendered: L4 fell back to
    English strings.
  - ar-LTR ran only on blank documents.
  - The registered oracle (O2, ink-located O3, O6, positive controls) is not
    implemented.
  - O5 did not discriminate. The recorder's recompute: Calc 13 unflipped
    against 26 flipped, Impress 0 of 40 unflipped, Writer 2 of 20. Yet the
    proposal and the blind packet say documents stay unmirrored.
  - The selector sat in an extra configuration layer, in a container, outside
    an orx node, so the 79 cap binds.
  - The decisive run needs three downloads, image-surgery code nobody has
    reviewed, a lane version that accepts a new qcow2 digest and the reserve
    tasks, a per-VM cell mechanism (P0.3 also sets LANGUAGE=ar) and a P0.6
    deviation.
  - Neither earlier S2 largest defect is open. Relay was moved in v2. The
    106-task census makes SMALL reachable (0.92-0.97 at the null).
- Secondary, all checked by the recorder: the sharp-null test uses variance v
  instead of 4v. It rejects in 0.32 at the exact null (power-v3.json). Reruns
  gave 0.34075 against 0.053 and 0.324 against 0.044, equal to the agents'
  outputs. This disables PRESENT_FRAGILE.
- No honest exit applies. Usage: wave 1 of 3; 4,586,573 of 8M tokens; $91.11 of
  $150 (list-price equivalent; $81.70 at the reported cache TTLs); 159.4 of
  600 minutes; GPU 0.0553 of 0.3. No direct prior, no safety failure.
  Queries are 127 of 150 (126 backed by logged records), with 23 left: enough
  for one wave-2 triad (18) plus at most 5 repair queries, and no wave 3. A
  repair wave at this wave's cost without cells would reach about 7.5M tokens
  and $150. The row's termination_reason is null (CONTINUE_PENDING).
- Doctor checks: the re-run at record time is byte-identical to the bundle
  copy (FAIL, as expected; gpu_hours 0.3 is parsed as 0 and left as
  declared). On a scratch copy the doctor's audit validator finds the chain
  intact. With gpu_hours parsed as 0 it flags only 'invalid cumulative
  gpu_hours' and the missing success state; with 0.3, only the success state.
- GPU: reviewer 2's job 1102 used 0.0553 GPU-h (scontrol RunTime 00:03:19 on
  1 H100, COMPLETED 0:0, 09:00:14-09:03:33 UTC). The queue was empty before
  submission and at the in-command re-check. The recorder's read-only check
  at 09:13:52 UTC found the queue empty, all GPUs at 0 MiB and no leftover
  container. It is added to the ledger as "S2 v3 gauntlet wave 1 ...
  open-weight review (D24)", and the program total on this branch is 10.4210.
  The pilot used no GPU.
- Waiting on the orchestrator or Kevin:
  - Whether wave 2 runs. Without Kevin it could implement the oracle with
    positive controls on the existing captures, sweep an offline pseudo-Arabic
    catalog in all four cells, move the selector to /etc/libreoffice/registry,
    run as an orx node, and fix the variance and the admission rule.
  - The three packages. The owner held them for Kevin. D1 may cover public
    research downloads; the recorder takes no position.
  - Review of the image and lane code.
  - The cap rule and Phase 1 admission (Kevin's).
  - R04: D73's dossier folds it into S2 v3's Phase 0, while D73 (iii) drafts
    it separately. Neither the triad nor the reviewers saw D73.
## 2026-10-11 — R01 gauntlet wave 1 (D73 i): score 58, honest exit on the query budget with the triad stop (branch `gauntlet/r01-noise-sources`, not merged)

- Wave 1 ran in workflow `wf_4e942e9b-9fc` with declared cumulative budgets:
  queries 150 (at least 30 reserved for the triad), wall_minutes 600, tokens
  8,000,000, dollars 150, waves 3, gpu_hours 0.3. Four discovery cells fed
  one synthesis owner. The owner wrote proposal `0eae5ee4...`, DRAFT
  registration `r01-rerun-noise-sources-v1` (`6bc3adf0...`; not frozen, not
  admitted) and the evidence bundle (`e7c1a714...`, evidence root
  `a09c5a34...`) at `2bbc08d` and `a9c30dd`. Scope: R01's first step only.
  Stage A0 (a records-only census of S1a) ran as an executable CPU pilot.
  Stage A1, Stage B (a request-level factorial of observation perturbation
  by serving configuration) and Stage C (open-loop replay) are designed.
  Registered caps are 4.22 cap-GPU-h. The audit row starts the new file
  `program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl`, row hash
  `22639b7682469a9241dbfd6542104bfda6b38ec5edcfd349e94b66540f0204fc`.
- Pilot: A0 is orx cpu-doctor node `ff110047`, run `83ee815a`
  (`ORX_RESULT exit=0`, 8 of 8 cases). The recorder re-ran it: the census is
  byte-identical (`5568bc7f...`) and its test passes. Its main numbers: 27
  natural identical-request replays, with reply text differing in 16 and the
  IR in 2; 0 of 227 identical-IR pairs verdict-discordant.
- Reviews: 58 (claude-opus-5-5) and 62 (qwen3.6-35b-a3b, self-hosted, Slurm
  1143). Each total equals the sum of its ten scores, and no cap binds. Both
  applied 74 and 89. Reviewer 2 also applied 79, but reviewer 1 did not,
  because A0 is a recorded orx run. Score 58, best 58. Neither review is
  signed (D24).
- Blind discrimination: PASS by the rule's letter, and thin. The critic
  judged the proposal (A) and cELldjX2oq the same mechanism at the core, with
  the proposal stronger by an incremental step in measurement design. The
  packets match the bundle files, and the prompt names nothing. The critic
  saw only cELldjX2oq's abstract-based paragraph.
- Refute-first triad: 3 of 3 refuted (27 counted queries, all by the novelty
  refuter).
  - Novelty: no direct prior, but the claimed delta (per-source sufficiency
    under redundancy) is published for training nondeterminism and uncited:
    Summers and Dinneen 2021, Nagarajan et al. 2018, Zhuang et al. 2021. The
    residual is a setting delta plus the clock hazard as a number.
  - Identification: see the largest defect. Also, the clock box is fitted
    on minute changes but used on hour-apart comparisons; h_cs shares a
    schedule that h_s does not; the encoder cache is never reset; and
    prefix caching flips the Mamba cache mode.
  - Feasibility: J3 is priced at one stream's mean pass. The recorder's
    recompute puts the chance of overrunning its 26-minute cap at 0.52-0.96.
    The P0 timing gate as written blocks J3 and J4. P0 needs Stage C frames
    and four unbuilt tools.
- Largest defect (reviewer 1, authoritative; reviewer 2 names the same
  estimand defect beside the feasibility defects): Stage B's primary h_s,
  h_c and h_cs pool steps 1-8 equally. But S1a's records put the first
  reply-text divergence at step 1 in 205 of 226 4B within-session pairs
  (recomputed by the recorder).
  - The text-level readings are settled in advance by A0.
  - The step-kick model compounds h_c(IR) per step, contrary to M.
  - The 2 of 19 against 90 of 885 redundancy evidence is task composition.
  So the GPU stage could not deliver the D_w attribution that is R01's
  payoff.
- Exit. The triad stop applies (0 of 3 failed to refute). Under the program
  convention (S2 run 2 and S2 v3: orx discover, OpenReview API searches and
  the arXiv title search), queries are 142 of 150. The 8 left cannot fund a
  compliant wave-2 triad (at least 18). That is the declared-budget exit, as
  for E4, C3, E3 and E5.
  - Under the bundle's own orx-only rule (125 used, 25 left), no exit would
    apply. The synthesis left this for the recorder, and the recorder
    applied the program convention.
  - termination_reason is `honest_exit_query_budget_and_triad_stop`.
  - Other usage: 4,056,469 of 8M tokens; $71.85 of $150 (list-price
    equivalent); 186.7 of 600 minutes; GPU 0.0581 of 0.3.
- Doctor checks: the re-run at record time is byte-identical to the bundle
  copy (FAIL, as expected; gpu_hours 0.3 is parsed as 0). On a scratch copy
  the audit validator finds the chain intact. With gpu_hours parsed as 0 it
  flags 'invalid cumulative gpu_hours' and the missing success state; with
  0.3, only the success state. Process note: the recorder ran
  `compute/build_bundle.py` by mistake. It rewrote `bundle.json`
  byte-identically, so git stayed clean.
- GPU: reviewer 2's job 1143 used 0.0581 GPU-h (scontrol RunTime 00:03:29 on
  1 H100, COMPLETED 0:0, 11:29:02-11:32:31 UTC). It was submitted on an
  empty queue after the operator waited 10:07-11:29 UTC through other
  workflows' CPU-only jobs. The recorder's read-only check at 11:46:00 UTC
  found all GPUs at 0 MiB, no compute apps and no leftover container; one
  other workflow's CPU job (R04) was running. The job is added to the ledger
  as "R01 gauntlet wave 1 ... open-weight review (D24)". The program total
  on this branch is 10.4238; main is at 10.4210 after S2 v3, so 10.4791
  after a merge.
- Waiting on the orchestrator or Kevin:
  - Whether R01 gets a fresh repair run with new budgets (the D60 and D68
    pattern). Without Kevin, a CPU-only repair could: rewrite the
    step-kick model as a two-stage process validated on S1a's records; make
    the step-1 hazards primary; build the step-1 corpus from A1 captures so
    that P0 no longer waits on Stage C; fix the clock box, placebo,
    replicate and cache resets; price loaded passes at the maximum over 20
    streams; and read the three adjacent-field papers in full.
  - The realized-cost cap rule, blink-off outside D53's scope, and P0 and
    Stage B admission (Kevin's, D24 and D70).
  - Merging this branch with main (state.json and log.md).

## 2026-10-11 — S2 v3 gauntlet wave 2 (fresh run under D74): score 65, honest exit on D74's stop line; S2 v3 ends (branch `gauntlet/s2v3-locale`, not merged)

- The run (gauntlet wave 2, wave 1 of the fresh run) ran in workflow
  `wf_d2bce6a2-2bf` with newly declared cumulative budgets: queries 80 (at
  least 30 reserved for the triad), wall_minutes 600, tokens 8,000,000,
  dollars 150, waves 1, gpu_hours 0.3. A single owner repaired wave 1's
  largest defect on CPU only (commits `c8669d2`, `f7df23c`, `da45543`,
  `aba30a7`, `6d4621d`, `5fc5e46`): proposal `e5f53151...`, new DRAFT
  registration `s2-arabic-cua-locale-v3.1` (`f2a8478f...`; not frozen, not
  admitted; v3 unedited), bundle `7ba7fcae...` (evidence root `2a758e90...`).
  Row hash
  `0d557a759bc80a467062cfdb703a076b276e8489f0f765e256d0f1b686dc7616`.
- Repair, all CPU-only Slurm jobs with no GRES (1116, 1120, 1123, 1124, 1129
  cancelled, 1131, 1132, 1139, 1140 failed, 1141, 1142; 0 GPU-h):
  - A generated pseudo-Arabic catalog built from the strings LibreOffice
    7.3.7.2 already ships (no download) renders the text factor at all 106
    task states in every cell, ar-LTR included (1,022 renders, 0 errors).
  - Instrument fixes: both language keys are needed (ooLocale alone leaves
    registry labels English); the ooSetupSystemLocale pin and LANGUAGE=ar are
    dropped; the selector sits in the system layer; the placebo shuffles
    toolbar items.
  - The registered oracle runs with planted controls as orx cpu-doctor node
    `c7bcde07` (run `9e78b49f`, ORX_RESULT exit=0); host replicate 1132 gives
    identical verdicts.
  - K0 under the rules committed before the sweep: FAIL (53 admitted; I1
    synthetic plants 101/106 for O3, 95/106 for O2, against a 100% bar).
    Under a checker-invariance rule chosen afterwards, 105 of 106 are
    admitted, and no cell changed any of 1,110 checker verdicts. K1 did not
    run.
  - A fifth Phase 1 cell (PL, toolbar items in a seeded order) carries the
    new MIRROR_SPECIFIC reading. The sharp-null variance is fixed (0.048 at
    the null). Phase 1 cap 6.83 GPU-h at K = 106 under the unadopted
    realized-price rule.
- Blind discrimination: PASS. The critic called the mechanism the same as
  macOSWorld's (2506.04135) but judged the proposal (B) the stronger
  contribution, with a specific delta. The packets match the bundle files,
  and the prompt names nothing. Only macOSWorld was judged.
- Refute-first triad: 3 of 3 refuted (36 counted queries: 10, 18 and 8).
  - Novelty: already-published fails (conceded); trivial recombination
    stands, as the proposal's own ledger calls the residual a measurement
    built from prior-art parts.
  - Identification: P3's total effect is identified, but MIRROR_SPECIFIC is
    a displacement-dose contrast at the measured placebo dose (0.34-0.44
    under dose-scaled direction-free harm; the recorder re-ran the refuter's
    simulation with identical output), the moderators are application
    indicators (R^2 0.848 for O8), and K0's passing count comes from a
    post-hoc estimator.
  - Feasibility: see the largest defect.
- Reviews: 65 (claude-opus-5-5) and 72 (qwen3.6-35b-a3b, self-hosted, Slurm
  1162). Each total equals the sum of its ten scores. No cap binds (reviewer 1
  applied 89 only; reviewer 2 applied 79 and 89). Score 65, best 65;
  trajectory 60 -> 65. Neither review is signed (D24).
- Largest defect (both reviewers and the feasibility refuter): Phase 0 still
  cannot decide its own gates with the assets that exist, the narrowed
  residue of wave 1's largest defect.
  - The only K0 verdict under rules fixed before data is FAIL. The 105-task
    pass has no passing-side control on 22 admitted tasks (recorder recount:
    12 none/fail, 5 fail/fail, 5 none/none) and admits the C1 tasks
    0f84bef9 and f178a4a9 without P0.10.
  - v3.1 leaves I1's bar 'fixed before Phase 0 proper', so K0 as registered
    has a free parameter.
  - K1 (P0.6, about 44 VM-h) and Phase 0 on the shipped catalogs wait on
    Kevin's three downloads, unwritten image-surgery and lane code (one
    pinned qcow2 digest; driver.py mounts one /System.qcow2) and a P0.6
    deviation.
- Stop line (D74: D60's rule at 65). Score prong: does not fire (65 is not
  below 65). Defect prong: fires. The wave-1 largest defect is still the
  largest under the category reading D63 applied to D60's rule; reviewer 1
  calls it the narrowed residue and left the ruling to the recorder and
  Kevin. The run's wave cap is reached and the triad stopped the candidate.
  Honest exit: S2 v3 ends; v3.1 is not frozen and not admitted.
- Usage (this run): 45 of 80 queries (repair 9, refuters 36); 4,231,312 of 8M
  tokens; $92.75 of $150 (list-price equivalent); 236.4 of 600 minutes; GPU
  0.0558 of 0.3. Gauntlet totals over both rows: 172 queries, 8.82M tokens,
  $183.86, 395.8 minutes, 0.1111 GPU-h. No direct prior, no safety failure.
- Doctor checks: the re-run at record time is byte-identical to the bundle
  copy (FAIL: Compute FAIL, unsigned reviews, cap 89; gpu_hours 0.3 parsed as
  0). On the appended file the doctor's audit validator finds the chain
  intact and flags row 1's older candidate hash and 127 queries, this row's
  token counter restarting below row 1's, two rows against waves=1 and no
  success state.
- GPU: reviewer 2's job 1162 used 0.0558 GPU-h (scontrol RunTime 00:03:21 on
  1 H100, COMPLETED 0:0, 12:58:07-13:01:28 UTC). The queue was empty before
  submission and at both in-command re-checks. The recorder's read-only check
  at 13:14:24 UTC found the queue empty, all GPUs at 0 MiB and no leftover
  container. It is added to the ledger as "S2 v3 gauntlet wave 2 ...
  open-weight review (D24)", and the program total on this branch is 10.4768
  (main also carries R01's job 1143, 0.0581, so the merged total is 10.5349).
- Waiting on Kevin: the package (the program's highest-scoring so far) can
  advance only by his admission ruling (D24, D70) or the trust store, the
  three language-pack downloads, the cap rule, review of the image and lane
  code, and a P0.6 deviation. Reopening S2 v3 as a v3.2 (reviewer 1's list:
  an I1 bar and one K0 rule, passing-side controls, C1 held until P0.10, a
  renamed or dose-matched placebo contrast, application fixed effects, the
  freeze path) would be a new owner decision.
## 2026-10-11 — R01 gauntlet wave 2 (fresh run under D75): score 57, honest exit on D75's stop line; R01 ends (branch `gauntlet/r01-noise-sources`, not merged)

- The fresh run used workflow `wf_2b705b28-469`, with budgets newly
  declared and cumulative for the run: queries 80 (30 reserved for the
  triad), wall_minutes 600, tokens 8,000,000, dollars 150, waves 1,
  gpu_hours 0.3. A single owner repaired the candidate on the Mac CPU. Then
  came one blind critic call, the refute-first triad, reviewer 1 and this
  record.
- The run is incomplete.
  - The repair owner returned at the harness's demand at 13:14 UTC. It had
    not filled its «P:» placeholders (12 distinct in the proposal, 13 in
    registration v2), merged its four simulation parts, rebuilt
    `bundle.json`, run the doctor or committed.
  - The recorder committed the owner's 38 files unedited as `3a2b771`,
    exactly as they were reviewed: proposal `f33658bd...`, DRAFT
    registration `r01-rerun-noise-sources-v2` `4a63be26...` (not frozen,
    not admitted), v1 unedited. This way the row binds to a commit.
  - Reviewer 2 (open-weight) never ran. Another workflow's CPU job (1175)
    held the host queue at every check from 13:45 to 13:53 UTC, and the
    host rule allows the lane job only on an empty queue.
  - The audit row is row 2 of
    `program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl`, with row
    hash `44604d3906c550e4e155f0a4f60bfa498134f51107395219a3318747a7e15929`.
- What the repair fixed (reviewer 1 confirms):
  - the primary estimands are now step-1 hazards (226 pairs, step 2
    secondary) in an onset-step 2^3 factorial (serving x clock region x
    other screen regions);
  - a VAL gate against S1a's own step-1 divergence;
  - a two-stage onset model that agrees with the mechanism;
  - caps repriced at 4.82 cap-GPU-h, with J3's overrun chance near 0;
  - P0, replay and open-loop drivers built and tested against fakes. The
    recorder reran the tests at `3a2b771`: 36 passed. The proposal claims
    38.
- Review: reviewer 1 (claude-opus-5-5) scored 57; its ten scores sum to 57.
  It applied 74 and 89, and neither binds. The score is 57 because the
  procedure takes the lower of two totals, and only one exists, so 57 is an
  upper bound. Best 58. Trajectory 58 -> 57, a dip that stays recorded.
- Blind discrimination: PASS. The critic judged the proposal (B) stronger
  than cELldjX2oq's abstract-based paragraph. The Summers and Dinneen
  packet was never judged.
- Triad: all three refuted (28 counted queries: 14, 7, 7).
  - Novelty: a recombination with a setting-only residual. The primary
    cells are single-turn requests, and 2609.16617, 2608.08239, 2606.08998
    and 2609.28851 are uncited or read only at abstract level. No direct
    prior was found.
  - Identification: the largest defect. Also, J3 sends R together with R2,
    whose prompt begins with R's screenshot turn, and caches reset only at
    the start of a pass. There is no placebo arm.
  - Feasibility: VAL is UNRESOLVED 0.247 of the time even at a perfect
    match, because it bootstraps S1a independently. The timing gate
    recomputes think time and refuses J3 at a latency ratio of about 1.04.
    P0 waits on A1 and on a lane adapter that does not exist yet.
- Largest defect: the step's mechanism test and its payoff are settled
  outside the GPU measurement.
  - S1a's step-1 text divergence is 202/221 when the step-1 requests
    differ, against 3/5 when they are identical. Given that, and VAL, the
    joint reading is REDUNDANT with probability 1.000 in every
    S1a-consistent scenario that passes VAL. So M's falsifier reduces to
    VAL_FAIL, which is a fidelity check, not a test of M.
  - P8's D_w predictions follow from a rho imported from S1a and held fixed
    across removal arms. The D_w "validation" is the in-sample identity
    (1 - N) x q.
  - The recorder recomputed the S1a counts and read the identity in
    `stepkick.py`.
  - This is wave 1's largest defect, narrowed. The step pooling and the
    model contradiction are fixed, but the predetermined text reading and
    the undelivered D_w attribution survive.
- Exit: D75's stop line fires on both prongs. The score is below 60 (and
  could only fall with a second review), and the wave-1 largest defect is
  still the largest. The run's wave cap is reached and the triad stopped
  the candidate. termination_reason is
  `honest_exit_d75_stop_line_triad_stop_and_wave_cap`. Under D75, R01
  ends: v2 is neither frozen nor admitted. Stage A0's descriptive finding
  (D75) stands.
- Usage: 43 of 80 queries; 2,679,536 of 8M tokens; $54.77 of $150
  (list-price equivalent); 123.7 of 600 minutes; GPU 0.0 of 0.3.
- Doctor: the recorder ran it on the reviewed candidate (exit 1, FAIL).
  Novelty and Compute are FAIL, and gpu_hours 0.3 parses as 0. The stale
  bundle also causes a proposal_sha256 mismatch, three unsnapshotted URLs
  and attestation hash mismatches. On a scratch copy the audit validator
  finds the hash chain intact. It flags the counter restarts at the run
  boundary, row 1's earlier exit, the wave count and the missing success
  state.
- GPU: no job ran. The ledger gains a 0.0 GPU-h row, "R01 gauntlet wave 2
  ... open-weight review (D24): NOT RUN". The program total on this branch
  stays 10.4791. Main is ahead by S2 v3's reviewer job 1162 (0.0558).
- Waiting on the main session:
  - a decision entry recording R01's end under D75;
  - whether to keep `3a2b771` (the unfinished candidate) when merging;
  - merging this branch with main (da95281), where `program/state.json`
    and `program/log.md` conflict.
  - If R01 is ever reopened, reviewer 1's list applies, as a new draft v3.
    P0 and Stage B admission stays Kevin's (D24, D70).
## 2026-10-11 — R03's K2 VM-fidelity executor built and tested on the dev split; addendum `q2-evaluator-mutation-v1-k2` drafted (DRAFT, not frozen; branch `stage0/q2-mutation-k2`, not merged)

- D73 (ii): the checker-mutation study's K2 gate had no executor (dossier O3),
  so its headline carries "offline harness, VM fidelity unverified". New code
  in `harness/q2_mutation_k2/` (no file under `harness/q2_mutation/`,
  `infra/q2-mutation/`, `harness/q2/` or `harness/q2_stage1/` changed; the
  parent's code tree `58bee019...`, action-path v2's 86 pinned files and S1a's
  section 20 files are byte-identical): an executor that runs the frozen plan
  of `vm_injection.py` in a fresh certified VM through S1a's OSWorld session
  code (setup, warm-up, the 60 s and 20 s settles, the pinned `evaluate()`
  with `DONE`), the K2 lane (S1a's lane with K2 slots,
  `infra/slurm/host-single-node/q2m-k2-vm.sbatch`), the run and pair rules
  for the parent's four explanations, a fitness gate (at most 8 of 80 pairs
  excluded) and the report that writes the parent analysis's `--k2-report`
  only for the registered job.
- Addendum `program/preregistrations/q2-evaluator-mutation-v1-k2.md` (DRAFT,
  own experiment id): the comparison (in-VM verdict against the offline
  lock-exact verdict for the same `candidate_sha256`), the items (the frozen
  80-job K2 sample; K2-C, the 41 candidate events, descriptive only), two
  independent runs per pair, the outcomes VERIFIED / FAMILIES_DROPPED (the
  parent's consequence verbatim) / INCOMPLETE (label kept; one repair under a
  new id), and the adjudication interplay (K2 reads no audit or adjudication
  file; its outputs are unblinding and carry the warning; neither waits for
  the other). Pre-freeze audit pending; the freeze is the owner's step.
- Dev-split jobs (CPU-only, no GRES, each submitted on an empty queue): 1113
  (void: SIGTERM left LibreOffice's recovery list, so reopened candidates sat
  behind a Document Recovery dialog; one run contaminated by a manual probe;
  fixed by a Ctrl+Q quit before any signal), 1122 (6 pairs, 12 of 12 runs
  scored, all agree) and 1130, the dress rehearsal at the registered shape
  (80 dev sample pairs and 11 dev candidate events, two runs each, V = 8):
  182 of 182 runs scored, 0 excluded, 80 of 80 pairs and 11 of 11 candidate
  events agree with the offline verdicts in both runs, 45.5 minutes.
  Exploratory; nothing here is a confirm result. No GPU used.
- Waiting on: the pre-freeze audit, then the owner's freeze, then the `k2` job
  (about 1 hour on the CPU lane). Kevin's adjudication (34 items) and spot
  check (25 items) are independent of K2 and stay his.

## 2026-10-11 — K2 addendum `q2-evaluator-mutation-v1-k2`: first pre-freeze audit's items fixed (DRAFT, not frozen; branch `stage0/q2-mutation-k2`, not merged)

- Audit verdict: not ready to freeze, two blocking items. (1) The text named
  the executor commit as the ledger row's `git_head_at_freeze`, but the lane
  accepts purpose `k2` only from a tree holding the row, and that commit's
  tree has none (reproduced by the auditor on a scratch copy of the ledger).
  Sections 7, 12 and 14 and the `k2-confirm-v1` base manifest note now adopt
  S1a's convention: the job runs from an export of the freeze commit (the
  commit that adds only the row), never its parent. The lane records the
  export's row in the receipt, and the `k2` report checks in a git checkout
  that the executor commit's only parent is `git_head_at_freeze` and that the
  trees differ only by the ledger. Section 14 asks for the branch to be merged
  to `main` before the freeze. (2) Section 8's per-set quantities (agreement
  by save path, run statistics, checker observations) were not produced by
  `report.py`; they are now, with tests.
- Cheaper items: a second `k2` job is refused by `lane submit` and `lane run`;
  the `k2` report reads one run directory and takes the K2-C digest from the
  frozen registration; `lane render` checks the job list against the sample
  summary (the pinned `9c2426b7...` for `k2`); the executor's upload is bounded
  at 180 s; scores are coerced with `float()` as offline; text fixes (section
  9.4's adjudication route, section 6's repair, section 11's table, section 7's
  `.git_sha`, the executor docstring); the confirm-only shapes and the dev jobs'
  host overlap are recorded in section 11. The dev reports of jobs 1122 and
  1130 were regenerated (pair rows unchanged except a new `save_path`).
- Checks: 88 K2 tests pass; ruff clean; code table refreshed. On a scratch
  git copy frozen into a copy of the ledger (the real ledger still has 16
  rows), the host's fresh render of the `k2` manifest (242 slots, job list
  `9c2426b7...` checked at render) validates on the freeze commit's tree
  (40 CPUs, 64 GB, 360 minutes) and is refused on its parent's; the report
  CLI with synthetic agreeing records accepts the freeze commit and refuses
  its parent. Dev job 1163 (CPU-only, no GRES, submitted on an empty queue,
  executor `2307253`): 12 of 12 runs scored and job 1122's six readings
  reproduced. No GPU used.
- Waiting on: a re-check of the fixes if the owner wants one, the merge to
  `main` (`program/log.md` conflicts only by both sides appending), then the
  owner's freeze and the `k2` job.

## 2026-10-11 — K2 addendum `q2-evaluator-mutation-v1-k2` frozen (ledger row 17) and run: job 1186, VERIFIED; parent analysis rerun with `--k2-report` (branch `ops/q2-mutation-k2`, not merged)

- Blind warning (D77, D78): the K2 outputs name checker verdicts per mutant
  and which mutants are candidate events; Kevin answers his adjudication (34
  items) and spot check (25 items) before reading
  `program/evidence/2026-10-11/q2-mutation-k2/`. This entry gives aggregates
  only.
- Freeze (D78, section 14 steps 1-2, done on `main` before this branch):
  status-paragraph commit `0a864682` (the row's `git_head_at_freeze`), row 17
  committed alone in the freeze commit `7d9c881a` (row hash `7d03d928...`,
  registration SHA-256 `564f8c5c...`); `check-chain` (17 rows) and `verify`
  pass; the K2 suite passes at the freeze commit (92).
- Section 14 step 3: `git archive` of the freeze commit (never its parent) to
  the host as `src/7d9c881a.../` with `.git_sha`, read-only; its `harness/`
  digest `1e087a0e...` equals the commit's. `lane render` from the pinned job
  list (`9c2426b7...`, sample summary checked) gave the 242 registered slots;
  `lane validate` passed (manifest `00830fde...`); `prior_k2_runs` empty (the
  run root held only development jobs), `check_one_job`, `check_slurm` and
  `check_host` (130 files hashed) passed. Submitted on an empty queue at
  15:56:19 UTC as job 1186 (CPU only, 40 CPUs, no GRES, V = 8); it ran 65.0
  minutes, the lane exited 0 and wrote its receipt, no labelled container was
  left, and no host snapshot saw another Slurm job.
- Outcome **VERIFIED**: gate 2 of 80 K2 pairs excluded (cause (4), both on
  task `51f5801c`: in all 8 attempts LibreOffice did not quit on Ctrl+Q within
  15 s, SIGTERM ended it, and the reopen of the Writer target got no reply
  within 180 s; a shape no development job had); 78 compared K2 pairs agree
  with the offline verdicts in both runs, none differs, no family dropped;
  K2-C 41 of 41 events reproduced in both runs (descriptive). 246 attempts,
  238 scored; no target unsaved at the checker's read; two save-time readings
  above 0.5 s (one pair, reported only). The report's freeze check passed.
- Parent analysis rerun (section 9.4) with `--k2-report` and the audit inputs
  as they stand: only `exclusions.k2` changes, to "VM fidelity checked (K2)"
  with no family dropped. Control: the same archive and interpreter without
  `--k2-report` reproduce the committed `analysis.json` byte for byte.
- Records, report, rerun analysis and blind READMEs:
  `program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/`. 0 GPU-h.
- Waiting on: Kevin's adjudication and spot check; after his answers the
  analysis is rerun once with `--k2-report` and the post-answer audit inputs.
  Adopting R03's kill line stays his (D73).

## 2026-10-11 — Checker-mutation pool and spot check adjudicated (D81 run 2, the record); parent analysis rerun with `--adjudications` and `--k2-report` (branch `ops/q2-mutation-adjudication-v2`, not merged)

- Label: adjudicated by an isolated model on the owner's instruction (D80);
  not human-validated. This is a disclosed deviation from D9. The human spot
  check stays pending as a human validation. Run 1 (`wf_cdd11126-1a7`, branch
  `ops/q2-mutation-adjudication`) is void under D81, and none of its answers
  or numbers is used.
- Run 2's rules were committed in D81 (`9890d11b`, 19:04:07Z) before any
  answer existed. Three workflow sessions, each holding adjudicator agents
  only:
  - (a), the record: `wf_843930b8-5af`, `claude-opus-5-5`, 52 items, the
    registered template;
  - (b): `wf_4d1fa210-001`, `claude-fable-5-1`, the same prompts;
  - (c): `wf_d750e081-ae1`, `claude-opus-5-5`, the 12 marker items plus D81's
    sentence.
  Every agent ran once, and no run was resumed.
- Isolation audit.
  - (a): the frozen `collect-transcripts` and `ingest-isolated`, from a git
    archive of `65bc2e2` with pins checked, gave **52 `ok`, 0 void**. Read and
    StructuredOutput only, all inside the item directories, one task turn
    each, registered attachments only, every tree equal to the export.
  - (b): the frozen ingest refuses the model pin, and (c): the frozen
    collector refuses the added sentence. Neither is an isolation failure.
    Both were audited by `audit_runs.py`, which calls the frozen functions
    unmodified and reproduces the frozen ingest on (a) and on the 2026-10-08
    rating, every item equal.
  - (c): 12 `ok`.
  - (b): every check passes except the attachment allow-list. The harness
    added `batching_reminder_sent`, a fixed tool-batching sentence (171
    entries), to every Fable transcript, so under the strict rules all 52 are
    void. The (b) sensitivity uses them with that type excepted, as a
    disclosed departure.
- Answers. Pool: 17 accept and 17 reject, all 34 decided, in
  `adjudications.jsonl`. Spot check: 19 accept and 6 reject. Run from
  `65bc2e2`: `audit summarize --adjudications`, then the analysis with
  `--k2-report`. Controls, all byte for byte: the 2026-10-08 summary, the K2
  rerun analysis, and the 2026-10-08 analysis.
- What changed against the K2 rerun:
  - Gold-defect tasks: 3 split gold shams were rejected (`5c1a6c3d`,
    `881deb30`, `8e116af7`).
  - FN: 33 confirmed and 3 label-contradicted, where before it was 30 and 6
    unresolved. The 3 are all on gold-defect task `5c1a6c3d`. Confirmed
    shares: pooled 11.6%, `compare_pptx_files` 37.1%, z-order 85.4%.
  - Alternative-solution gate: 82 accepted, 11 rejected, 0 unresolved. 10 of
    the rejects are on the two `compare_table` gold-defect tasks.
  - P2: the population is 337 and the rate is unchanged at 12.4%. P2 without
    the gold-defect equivalence mutants is 12.2% on 57 tasks.
  - The equivalence K3 label error is 0 (upper 0.087). K3 still fires through
    κ.
  - K4 no longer fires.
- Unchanged: κ 0.343, P1, P3-P5, the FP table, the candidate shares, and
  every other K.
- Sensitivities. (b) differs from (a) only on one equivalence split, which
  Fable answered unsure: FN 32 confirmed and 1 unresolved, equivalence K3
  0.030. (c) is byte-identical to (a), because all 12 marker items are
  accept with and without the sentence.
- Agreement and the correlated-judge caveat:
  - (a) vs (b): 51 of 52 items, (b) with `batching_reminder_sent` excepted
    (void under the strict audit).
  - (a) vs the Claude rater: 41 of 52. (a) vs Qwen: 35 of 52.
  - On the 28 splits, (a) sides with Claude 17 times and with Qwen 11 times.
  - On the spot check, (a) matches the raters' consensus on 23 of 23 and
    the Claude rater on 25 of 25.
  - The adjudicator shares a model, and with (b) a provider, with the
    Anthropic rater.
- Image coverage: (a) opened 503 of 506 images, and the registered rating
  opened 502 of 506 on the same items (1,453 of 1,457 overall).
- Records: `program/evidence/2026-10-11/q2-mutation-adjudication-v2/`.
  Transcripts and answer files with reasons stay outside the repository,
  hashed. 0 GPU-h.
- Verification. Two independent audits (isolation and mapping; recompute
  and claims) reproduced every answer mapping, frozen output and table byte
  for byte. They found one wrong README sentence, now corrected: of the 6
  spot-check items where the adjudicator contradicts the label, 5 are items
  both raters already contradicted, and the sixth (`aa3331db`, `alt_gate`) is
  a split on which it sided with the Claude rater. The README also now says
  that the model pin refuses the whole ingest rather than voiding an item,
  that the injected git status every agent saw named D81's commit title (no
  item, label or answer), that the frozen K3 reason string still reads "label
  error" although the cause is κ, and that (b)'s agreement figures except
  `batching_reminder_sent`. No answer, number or frozen output changed.

## 2026-10-11 — Q2 successor E `q2-stage1-successor-e-v1` drafted (D80 iii; DRAFT, not frozen; branch `stage0/q2-successor-e`, not merged)

- Single owner, CPU only, no host job. Registration
  `program/preregistrations/q2-stage1-successor-e-v1.md`: S1a's design with more data, no
  change to its estimands or rules. All 113 eligible pool tasks (no draw, no fill rule), 9B then
  4B in every session, four new sessions per size (E1-E4) at least 12 h apart from the previous
  session's later end, one episode per (size, task, harness, session); S1a's harnesses, engine,
  prompts and pinned date, action path (D53), lane, records schema, D53 (iii) observation rule
  and D56 carve-out; S1a's estimators, DR0-DR5 and P1-P5 (P1, D_w and rho not estimable at
  R = 1). Primary set the 113 tasks; S1a's 32 base tasks a registered secondary. E is its own
  sample; the joint reading with S1a is descriptive.
- Caps by arithmetic at realized price x 1.2 x 1.05 on the design study's cost model: 52 min
  per 9B job, 48 per 4B job, 3 + 3 for the overlay OE and its retry, 406 in all (6.77 GPU-h).
  Cap check (`cap-sufficiency.json`): every slot ends before USR1 with probability 1.000 under
  S1a's slots, 10% longer slots and 5% loss; 0.9215 for a 4B session 20% slower. Calendar about
  41-42 h minimum (the design study's 37 h counted one session window).
- Code: no S1a code-of-record file changes (the prereg test checks all 75 digests). New thin
  layer `harness/q2_stage1e/` (plan, records, entry point, lane over S1a's `Lane`, analysis with
  the D59/D61/D62 rules built in, section 15 items), `scripts/render_q2e_manifest.py`,
  `infra/slurm/host-single-node/q2e-vm.sbatch` (S1a's with the lane module changed), the plan
  file and the development smoke manifest. E's analysis reproduces S1a's committed readings on
  S1a's records exactly and the design study's analysis on E-shaped data
  (`analysis-identity.json`). The design study's E numbers are the registered power statement.
- Tests: `tests/test_q2_stage1e.py`, `tests/test_q2_stage1e_prereg.py`; S1a's and the design
  study's suites pass unchanged.
- Open before the freeze: G-E4 (CPU development smoke of E's lane on the host), G-E5 (the GLMM
  on E's shape in the pinned container), G-E6 (fresh pre-freeze audit) and the program's
  sign-off decision.

## 2026-10-11 — Q2 successor E `q2-stage1-successor-e-v1`: first pre-freeze audit's items fixed (DRAFT, not frozen; branch `stage0/q2-successor-e`, not merged)

- Single owner, CPU only; host read-only (job 1200, R04, was running). `main` at `746d60d2`
  (ledger row 18, D81, D82) merged into the branch first (`23f00f4c`; only `program/log.md`
  conflicted). Fixes in `acb886c5`; evidence regenerated from it, clean.
- B1: section 9 now states what D82 found: three gold-defect tasks in E's primary set
  (`5c1a6c3d`, `881deb30`, `8e116af7`; none in S1a's base or flagged list) and three
  label-contradicted z-order candidates, all on `5c1a6c3d`, that the corrected outcome scores
  as passing. New D82 gold-defect sensitivity: every primary reading on the 110 other tasks,
  raw and corrected (plan field `gold_defect_tasks_d82`; `analysis.report`). S1a's seven
  flagged tasks stay the flagged set. No primary set, rule or DR changes. Section 21 item 14,
  disclosure 11.
- B2: section 25 step 1 merges `main` again after the sign-off decision and freezes on the
  merged tree (E's row after `main`'s last, row 19 as of `746d60d2`). New prereg tests: the
  section 21 id must be a decision heading naming the registration whose entry signs items
  1-14; the ledger must hold R04's row and a frozen E row must follow it. Rehearsed on a
  scratch export: the freeze is accepted as row 19 and passes with a valid id; a nonexistent id
  (D83) and a freeze on the pre-merge 17-row ledger each fail their test. Real ledger untouched
  (18 rows).
- B3 open: G-E4 (CPU development smoke), G-E5 (GLMM on E's shape), G-E6 (a fresh audit that
  finds nothing blocking) and the program's sign-off decision. G-E4 needs a quiet host (D80).
- Non-blocking: the session gap is 12 h plus a 5-minute margin, and a GPU job with no final
  Slurm state counts its start plus its limit as its end (`lane.job_end`), so both D57 (ii)
  readings hold; G-E4's draft-only sentence dated, with a test refusing draft-only wording;
  section 18 says incomplete readings are registered readings under the label, with no power
  claimed; L = 113 s disclosed as an assumption, with the p99 margins; section 23 pins the GPU
  container, overlay and analysis infrastructure, and a test checks E's import closure; the
  `e` purpose's first host run (E-9B-E1) disclosed; section 11 states that the R = 1 label
  permutation is the exact per-cell sign flip. The review log (section 25) records audit 1
  with every item's disposition.
- Plan re-rendered: `plan_sha256` `4e7298a7...`, file `12bded25...`; tasks, orders, caps and
  engine unchanged. `cap-sufficiency.json` and `analysis-identity.json` regenerated at
  `acb886c5`: identical to the first outputs but for provenance (and the plan digest input).
- Tests: E 62 passed on the draft (`test_q2_stage1e.py` 46, `test_q2_stage1e_prereg.py` 16);
  60 passed and 2 skipped on the frozen rehearsal tree. S1a's and the design study's suites
  (15 files): 310 passed, 3 skipped. (The earlier report of 293 passed and 4 skipped for these
  files was wrong; audit 1 found the same 310/3.)

## 2026-10-11 — Q2 successor E `q2-stage1-successor-e-v1`: pre-freeze gates G-E4 and G-E5 passed (DRAFT, not frozen; branch `stage0/q2-successor-e`, not merged)

- Single operator. CPU only: three Slurm jobs with no GRES, run from a read-only `git archive`
  export of the draft commit `8a23a483` under `~/cotcodec-runs/stage0/q2-stage1e/` on the host
  (its `harness/` tree digest equals the Mac's). Each job was submitted only when the whole
  queue was empty, one at a time (polling `squeue` every 2 s in commands of at most about four
  minutes). Other workstreams held the queue for about two hours first: S2 v4 1201 and 1207,
  1202, 1209, and R04 1203 and 1204. No GPU, no model, no confirm task.
- G-E4 **passed**. VM job 1206 ran the registered development smoke
  (`lane submit experiments/manifests/q2-stage1e/dev-smoke-v1.json`) in 7 min 38 s. All 4
  slots scored with session `E1`. E's `records.validate` accepts every record and S1a's
  refuses every one. The lane receipt holds no error (lane exit 0, no container left), and the
  lane's snapshots saw no foreign Slurm job. Offline rescoring (job 1208, `rescore.py capture`
  in the metric image) matched the live score on 4 of 4, with the same state digests.
- G-E5 **passed**. CPU job 1210 ran the unchanged `glmm.R` (200 refits, seed 42) in the
  pinned image, in 14 min 41 s, on E-shaped synthetic rows: 1,808 rows, `glmm-synthetic`,
  113 tasks, seed 42, the same bytes on the host's numpy 1.21.5 and the Mac's 2.5.2. Both fits
  converged with positive-definite Hessians. Bootstrap: 200 refits used, 0 failed, 42 not
  converged. Estimated variances: task 1.33 (generating 2.25), task:harness 0.97 (1.00),
  task:session and task:harness:session about 0 (the latter is not identified at R = 1). LRT
  of `(1|task:harness)`: chi-square 34.1.
- Evidence: `program/evidence/2026-10-11/q2-stage1-successor-e/gates/` (README, the records
  and receipts, the operator scripts, `check_gates.py` and its `gates-check.json`, which checks
  every record with E's code). The registration's G-E4 and G-E5 result slots are filled;
  nothing else in it changed. Its status paragraph, replaced whole at the freeze, still lists
  them among the open slots.
- `main` at `2b8fadc7` (D83, D84, the Q2 report revision; no ledger change) was merged into
  the branch first (`2f278e81`). E's code equals the exported commit's. The real ledger is
  untouched (18 rows).
- `tests/test_q2_stage1e_prereg.py`: the open-slot test accepts a G-E4 or G-E5 slot that is
  either `TBD` or holds a `**passed**`/`**failed**` verdict naming the gates' evidence. It
  refuses a filled slot without either. Tests: E 62 passed (`test_q2_stage1e.py` 46,
  `test_q2_stage1e_prereg.py` 16); S1a's and the design study's suites (15 files) 310 passed,
  3 skipped.
- Still open before the freeze: G-E6 (a fresh pre-freeze audit that finds nothing blocking)
  and the program's sign-off decision (section 21), then section 25's steps.

## 2026-10-12 — Q2 successor E `q2-stage1-successor-e-v1` (frozen, ledger row 19): OE built the overlay from the freeze commit (branch `ops/q2-successor-e`, not merged)

- E was frozen as ledger row 19 at `f6144d6b` (2026-10-12T01:02:32Z; file SHA-256
  `47e65877...`). Everything below runs from that commit, never its parent `7fcf0a4a`.
- The host export `~/cotcodec-runs/stage0/q2-stage1e/src/f6144d6b.../` is `git archive
  f6144d6b` plus `.git_sha`, read-only; its file list and contents equal a clean clone of the
  commit. `preregister.py verify` and `check-chain` pass in both (row 19, 19 rows). Section
  23's 19 digests match in the export.
- OE: the discovery source archive `6ad9ad67...` (7,602 files, `selected_ref: HEAD`, clean
  clone at `f6144d6b`) was validated on CPU with the pinned extractor first. Job 1215 (one
  H100, 3-minute cap) was submitted on an empty queue at 02:01:28 UTC and **COMPLETED 0:0 in
  57 s**: provenance PASS, overlay
  `sha256:5d1d4d8f1ff4a92cc607704b5e8e9adaa0269b8fa27757d6fe51616e438584ef`. No retry. Physical
  0.0158 GPU-h (`program/state.json`); charged 3 minutes under D22.
- Before OE the queue held other workstreams' jobs (R03 part (b)'s 1213, S2 v4's 1214, about
  55 minutes). R04's job 1216 started five seconds after OE ended, so E-9B-E1 waits for a quiet
  host (section 6.4); its VM manifest is rendered and validated (226 slots, cap 52, VM limit
  62 minutes, 90 CPUs).
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/` (README, `oe/`, `ops/`).

## 2026-10-12 — Q2 successor E `q2-stage1-successor-e-v1`: session E1 ran (E-9B-E1, E-4B-E1); DR0 does not fire (branch `ops/q2-successor-e`, not merged)

- R04's job 1216 held the queue until after 03:18 UTC; the OE operator stopped polling then
  with nothing submitted. The next operator resumed at 04:25, found an empty queue and no
  leftover operator process, re-checked the export against `git archive f6144d6b` (7,602
  files and 27 symlinks equal, `.git_sha` present, nothing writable) and the operator scripts
  against the committed ones, and submitted on the first check.
- **E-9B-E1**: VM job 1219 and GPU job 1221 (`--dependency=after:1219`), submitted 04:28:39 UTC
  on an empty queue (verify and `check-chain` PASS in the export; `lane validate` 226 slots;
  `--test-only` exit 0, id 1220). Both COMPLETED 0:0; GPU 04:28:39-05:08:31 (00:39:52, 0.6644
  GPU-h physical, 52 minutes charged). 226 of 226 slots scored, no infrastructure loss, no
  re-queue, no cap truncation, no restart, no slow or undelivered observation; DR0 exit 0, does
  not fire. Provenance PASS (`f6144d6b`, overlay `5d1d4d8f...`), engine argv equal to S1a's
  for 9B, Slurm limit 52 equal to the cap, first dispatch 113.2 s after the Slurm start.
- **E-4B-E1**: its manifest was rendered after E-9B-E1's DR0 and names E-9B-E1's records
  (`278e8112...`) and receipt (`32a4a1f7...`). VM job 1222 and GPU job 1224, submitted 05:09:55
  on an empty queue (`--test-only` id 1223). Both COMPLETED 0:0; GPU 05:09:56-05:46:33
  (00:36:37, 0.6103 GPU-h physical, 48 minutes charged). 226 of 226 scored, no loss, no
  re-queue, no truncation; one postconfig reply at HTTP 200 with a non-zero return code
  (recorded, not a loss, not a server error under D56); DR0 exit 0, does not fire. Provenance,
  engine argv (4B) and Slurm limit 48 checks pass; first dispatch 105.6 s after the start.
- Quiet host: no foreign Slurm job in any lane snapshot or 15-second queue sample while either
  job ran; nothing else was submitted between the pairs.
- **Session E1's later end: 2026-10-12T05:46:33Z** (E-4B-E1 by `lane.job_end`; VM batch end
  05:46:36). **E2 may not start before 17:51:33 UTC.** Other workstreams may use the host until
  then and must have ended before E-9B-E2 is submitted.
- GPU-h: physical 1.2747 for the session (ledger rows in `program/state.json`; program total
  11.8254); charged under D22 103 of E's 406 cap-minutes so far (OE 3, E1 100). No outcome was
  read; the registered analysis runs after the last E job.
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/` (README section "Session
  E1", `e-9b-e1/`, `e-4b-e1/`).

## 2026-10-12 — R03 (b) `q2-zinv-reserve-validation-v1` run (`reserve-v1`): PASS, descriptive (branch `ops/r03-zinv-reserve`, not merged)

- Single operator, under D80 and D86. Run from an export of the freeze commit `ff802ca5`
  (ledger row 20), staged with `git archive | ssh tar -x`; its 7,640 regular files equal the
  commit's blobs, with no AppleDouble file. The plan `reserve-v1` was created at 01:35Z by an
  earlier session of this operator, which was restarted before submitting anything; this
  session verified it and continued it with `next`. Nothing was planned twice and no step
  was rerun.
- Scheduling: the session waited, submitting nothing, through successor E's whole session E1
  (9B pair 1219/1221 from 04:28Z, 4B pair 1222/1224 to 05:46:36Z) and R04 job 1225. It then
  submitted the four steps one at a time, each on an empty queue, in E's gap (E2 not before
  about 17:51Z): Slurm 1226 `targets`, 1227 `build`, 1228 `score`, 1229 `zinv`, 07:15-07:28Z.
  All four exited 0, network none, no GPU; 0.221 of the 4.0 lane-hours; 0 GPU-h.
- **Outcome as `rules.judge` gives it: PASS, status descriptive.** zinv accepted 13 of 13
  held-out z-order equivalence mutants on 8 of 8 tasks (`n_Z` 13, `t_Z` 8). It newly accepted
  none of 15 violation mutants (`n_V` 15, 5 tasks). All 106 rows are valid. The status is
  descriptive because `n_Z` < 20: the operators planned 13 z-order mutants on these targets,
  against an expected 19.5.
- Bounds:
  - acceptance, exact one-sided 95% lower bound 0.794 (two-sided 0.753-1.000);
  - task level 0.688;
  - new-accept rate, upper bound 0.181 per mutant and 0.451 per task.
- Licensed (section 7): the correction held on reserve documents it was not developed on, at
  this size, with that lower bound. Not licensed: a population claim that zinv accepts 95% of
  z-order equivalents.
- The result is offline and rests on the operators' labels.
- The original `compare_pptx_files` failed 13 of 13 of the z-order mutants (a held-out
  replication of the defect, descriptive). zinv changed no other verdict (93 of 93 equal). It
  raised no error and turned no pass into a fail.
- Step 3's checker-error tables for these 8 targets are exploratory.
- Evidence: `program/evidence/2026-10-12/q2-zinv-reserve-run/`, with its README and
  `release/`, exactly as `zr_host.py export` wrote it (23 files, digests in its manifest). The
  blind warning (D9, D82) applies to every per-mutant verdict file. Mutant documents and step
  logs stay on the host. No outward action.
## 2026-10-12 — R04 `r04-checker-nuisance-invariance-v1` frozen (ledger row 18) and run: build DRIFT, locale DRIFT, route MINOR; gates pass (branch `ops/r04`, not merged)

- Blind warning: the R04 outputs name checker verdicts per gold task and S1a state. The
  checker-mutation pool and spot check were adjudicated by an isolated model (D81, D82); if
  Kevin does his optional human spot check (D9) blind, he does it before reading
  `program/evidence/2026-10-12/r04-nuisance-confirm/`.
- Freeze (D80; section 17), by an operator who did not draft the file, on `main`: fill
  commit `c908b978` on `c0971a77` (status paragraph, `code_tree_sha256` `1ffe2d19...`,
  code-of-record row); scratch freeze first (R04 suite 62 passed at the scratch freeze
  commit; the ledger-touching suites 574 passed, 11 skipped); then `freeze`, `check-chain`,
  `verify` and the freeze commit `e312e996` with row 18 alone (row hash `f7b350a3...`,
  registration SHA-256 `1191a4a0...`, 2026-10-11T18:27:01Z; R04 suite 62 passed), pushed.
  At the fill commit itself one R04 test failed by construction (the frozen status line needs
  the ledger row of the next commit).
- Run (section 6) from a `git archive` export of `e312e996` on the host, CPU only: plan
  `r04-registered-v1 --registered`, 14 main jobs (1187-1225), `analysis --run` (108 items,
  24 of them golds, pending under 11 cells), `confirm`, 10 round jobs (1230-1239), `analysis
  --run`, then the same with `--k2-report`. Every job was submitted by the host tool on an
  empty queue and finished on its first attempt; the last main job waited for successor E's
  first session (1219-1224) to end. 24 jobs, 10.27 lane-hours of the 20 h cap (main 8.04,
  rounds 2.23), 328.6 allocated CPU-h, 0 GPU-h. The workflow's first operator instance
  stopped polling at 03:33 UTC; a second instance resumed from the same plan at 04:28 UTC.
- Items: 553 (92 golds, equal to P1's counted golds; S1a 270 pass, 180 fail, 11 mixed
  states). Every cell saved every item (556 saves per cell, no failure, no dialog), every pair
  is valid, no scoring failure; the em-dash title fallback was used on 553 items in each
  `ctrl_s` and `store_as` cell of B2-B5 and nowhere else.
- Gates: control retained, V1 pass (92 of 92, 0 differences), V2 pass (replicate: 0
  discordances). Both rounds reproduced every discordance: 0 unstable, no `harness_noise`.
- **Readings (pinned checker; `zinv` identical):** build arm **DRIFT** (B1-B3 INVARIANT; B4
  TDF 25.8.7.3 DRIFT, `k_gold` 18 of 92, `t_s1a` 6 of 32; B5 TDF 26.2.6.2 DRIFT, 20 and 6;
  `compare_pptx_files` 17-18 golds and 67 pass states, identical across all three routes);
  locale arm **DRIFT** (de_DE 3 and 1, ar_EG 4 and 2, tr_TR 3 and 1, all three on the same
  `compare_table` golds; ja_JP INVARIANT); route arm **MINOR** (`store_as` INVARIANT;
  `headless_convert` 1 gold and 1 task, `compare_table`). Secondary cells follow their
  build. P1 replication: the control flips 4 of 92 golds (as P1).
- K2: with the K2 report (job 1186, VERIFIED, no family dropped) only the label changes, to
  "VM fidelity checked (K2)"; both analyses are committed.
- Disclosed: the first operator instance ran an exploratory explicit-form peek at the
  partial main run (about 02:04 UTC; scratch only, nothing chosen after it); the registered
  analyses ran on the host from the freeze export (Python 3.10.12) because the Mac was
  overloaded; the committed `analysis.json` and `analysis-k2.json` are the Mac
  reproductions from the evidence copy (repository venv), which differ from the host's
  (kept in `host-analysis/`) only in the last bits of Clopper-Pearson bounds (max absolute
  difference 8.2e-16) and input paths; `tests/test_r04_evidence.py`'s glob widened to
  `r04-nuisance*/` (outside the code tree).
- Evidence: `program/evidence/2026-10-12/r04-nuisance-confirm/` (README, the run copy
  without documents, analyses, operator scripts).

## 2026-10-12 — Q2 successor E `q2-stage1-successor-e-v1`: session E2 ran (E-9B-E2, E-4B-E2); DR0 does not fire (branch `ops/q2-successor-e`, not merged)

- The E2 operator started at 05:55 UTC and submitted nothing before the gap had passed
  (17:51:33 UTC, session E1's later end plus 12 h 5 min). It prepared E-9B-E2 without touching
  Slurm (pair directory; VM manifest rendered from the export with E1's two run directories,
  validated, `--begin=2026-10-12T17:51:33` from the lane's dry run), queued nothing ahead, and
  polled the queue about every 4 minutes while R04 (1225, 1230, 1234, 1235, 1239), R03 part (b)
  (1227-1229) and S2 v4 (1240, 1242, 1244-1250) used the gap. `main` was merged into the branch
  three times (D87-D91, R03 part (b), R04, S2 v4's freeze, ledger rows 20 and 21; every row
  kept, `check-chain` 21 rows PASS). At 17:42 it re-checked the export against `git archive
  f6144d6b` (7,602 files, 27 symlinks, `.git_sha`, nothing writable) and the operator scripts.
- **E-9B-E2**: VM job 1251 and GPU job 1253 (`--dependency=after:1251`), submitted 17:53:07 UTC
  on an empty queue (verify and `check-chain` PASS in the export; `lane validate` 226 slots;
  `--test-only` exit 0, id 1252). Both COMPLETED 0:0; GPU 17:53:08-18:33:49 (00:40:41, 0.6781
  GPU-h physical, 52 minutes charged). 226 of 226 slots scored, no infrastructure loss, no
  re-queue, no cap truncation, no restart, no slow or undelivered observation, no postconfig
  failure; DR0 exit 0, does not fire. The manifest named E1's two jobs by records and receipt;
  the session gap held; provenance PASS (`f6144d6b`, overlay `5d1d4d8f...`), engine argv equal
  to S1a's for 9B, Slurm limit 52 equal to the cap; first dispatch 114.3 s after the Slurm
  start (the caps assume L = 113.19 s); lane end 8.4 minutes before the USR1 point.
- **E-4B-E2**: its manifest was rendered after E-9B-E2's DR0 and names the three earlier jobs
  (E-9B-E2's records `e8755336...`, receipt `e1664285...`). VM job 1254 and GPU job 1256,
  submitted 18:36:41 on an empty queue (`--test-only` id 1255). Both COMPLETED 0:0; GPU
  18:36:44-19:12:47 (00:36:03, 0.6008 GPU-h physical, 48 minutes charged). 226 of 226 scored,
  no loss, no re-queue, no truncation; one postconfig reply at HTTP 200 with a non-zero return
  code (recorded, not a loss, not a server error under D56; every postconfig reply of both E2
  jobs was HTTP 200); DR0 exit 0, does not fire. Provenance, engine argv (4B) and Slurm limit
  48 checks pass; first dispatch 104.5 s after the start; lane end 9.0 minutes before USR1.
- Quiet host: no foreign Slurm job in any lane snapshot or 15-second queue sample while either
  job ran; nothing else was submitted between the pairs. S2 v4's job 1257 was submitted at
  19:13:59, after E-4B-E2's VM batch job had ended (19:12:50).
- **Session E2's later end: 2026-10-12T19:12:47Z** (E-4B-E2 by `lane.job_end`; VM batch end
  19:12:50). **E3 may not start before 2026-10-13T07:17:47Z.** Other workstreams may use the
  host until then and must have ended before E-9B-E3 is submitted.
- GPU-h: physical 1.2789 for the session (ledger rows in `program/state.json`; program total
  13.1043); charged under D22 203 of E's 406 cap-minutes so far (OE 3, E1 100, E2 100). No
  outcome was read; the registered analysis runs after the last E job.
- Disclosure: the operator's own network to the host was down from about 16:24 to 16:49 UTC
  while it waited (nothing of E's pending or running). No deviation from the registration.
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/` (README section "Session
  E2", `e-9b-e2/`, `e-4b-e2/`).

## 2026-10-12 — S2 v4 `s2-arabic-cua-locale-v4` Phase 0 run: K1 fails as registered (A6 on ER), the operator stops (branch `ops/s2-v4`, not merged)

- Frozen in ledger row 21 (status fill `d27331d4`, freeze commit `cf174050`). Every job ran
  from the host's `git archive` export of `cf174050` (`.git_sha` `cf174050...`; file digest
  `bd289bb8...`, equal to a Mac export), CPU only, no GRES, one job at a time, each on an empty
  queue and only when its Slurm limit ended before successor E's next earliest session start
  (D85, D87, D90, D91); no S2 v4 job ran during an E session (E2 17:53-19:12:50Z; E3 not before
  2026-10-13T07:17:50Z).
- K1 (P0.6), 14 of its 49 `ap_delta` jobs, Slurm 1245-1250 and 1257-1264, every one COMPLETED 0:0
  with every campaign counting (driver exit 0, `infra_gates_pass`, image unchanged, no labelled
  container): C1 pass on E, A, ER, AR and PL; the V = 20 rung not aborted, 2,400 of 2,400 trials
  (its per-image step condition waits for each image's A1); C2 pass on all five; A6 pass on E
  (1262) and A (1263), 300 of 300 each.
- **A6 on ER (Slurm 1264) fails:** 295 of 300 trials, 59 of 60 canary entries PASS;
  `writer:drag_select_word` failed in all 5 sessions with the same read-back (`Ykeep word keep`
  for `keep Y keep`). `ap_delta.verdict` on the job: A6 on ER `pass` false. The campaign counts,
  so no registered rerun applies. Operator's untested reading: the canary's frozen drag
  coordinates were measured on the left-to-right layout, and ER mirrors LibreOffice's layout.
- By the registration's pass line (every check on every image) and kill criterion K1, **K1
  fails**: no Phase 1 on these images; a repair is a new image and a new registration. The
  registered `ap_delta.py verdict` over all 49 jobs has not run (35 jobs not run); none of them
  can make K1 pass.
- The operator stopped at 22:45Z, as its brief requires when a registered stop rule fires:
  nothing submitted after 1264, the queue empty and no labelled container at 22:59:49Z. Not run:
  A6 on AR and PL, A5 on all five, the 28 long K1 jobs, the census, the oracle and K0. Whether to
  run any of them as a record is the program owner's decision.
- The orchestrating session restarted once (21:46Z) while 1263 ran; the new operator collected
  it without resubmitting and kept the previous instance's `watch_job.sh` fix (a failed `ssh` is
  retried, not read as the job gone).
- Evidence: `program/evidence/2026-10-12/s2v4-phase0-run/` (README with per-job records and the
  stop record; per job its submission snapshot, `scontrol`, batch output, receipts, manifests
  and `check-JOB.json`). Cycle records and VM logs stay on the host.

## 2026-10-13 — Q2 successor E `q2-stage1-successor-e-v1`: session E3 ran (E-9B-E3, E-4B-E3); DR0 does not fire (branch `ops/q2-successor-e`, not merged)

- The orchestrating session restarted twice after session E2 (the operator's Mac crashed). The
  E3 operator started at 00:06 UTC and checked the host first: queue empty, no E3 run
  directory, no submission file in either E3 pair directory and no operator process, so
  nothing of E3 had been submitted. An earlier E3 instance had prepared both pair directories
  and E-9B-E3's VM manifest at 19:23 UTC on 2026-10-12; this operator re-rendered the manifest
  from the export (byte-identical) and found the operator scripts on the host equal to the
  committed ones. `main` (D93, S2 v4's K1 jobs 1245-1264) was merged into the branch, every
  ledger row kept (21 rows). The queue was empty at every poll from 00:07 to 07:15 UTC (about
  every 4 minutes); at 06:39 the export was re-checked against `git archive f6144d6b` (7,602
  files, 27 symlinks, `.git_sha`, nothing writable).
- **E-9B-E3**: VM job 1265 and GPU job 1267 (`--dependency=after:1265`), submitted 07:18:02 UTC
  on an empty queue, after both readings of the gap (07:17:47 by `lane.job_end`, 07:17:50 by
  E-4B-E2's VM batch end); verify and `check-chain` PASS in the export; `lane validate` 226
  slots; `--test-only` exit 0, id 1266. Both COMPLETED 0:0; GPU 07:18:02-07:56:53 (00:38:51,
  0.6475 GPU-h physical, 52 minutes charged). 226 of 226 slots scored, no infrastructure loss,
  no re-queue, no cap truncation, no restart, no slow or undelivered observation, no
  postconfig failure; DR0 exit 0, does not fire. The manifest named E1's and E2's four jobs by
  records and receipt; the session gap held; provenance PASS (`f6144d6b`, overlay
  `5d1d4d8f...`), engine argv equal to S1a's for 9B, Slurm limit 52 equal to the cap; first
  dispatch 113.7 s after the Slurm start (the caps assume L = 113.19 s); lane end 10.2 minutes
  before the USR1 point.
- **E-4B-E3**: its manifest was rendered after E-9B-E3's DR0 and names the five earlier jobs
  (E-9B-E3's records `d2fb985b...`, receipt `bc30d8e2...`). VM job 1268 and GPU job 1270,
  submitted 07:58:41-07:58:42 on an empty queue (`--test-only` id 1269). Both COMPLETED 0:0;
  GPU 07:58:45-08:36:07 (00:37:22, 0.6228 GPU-h physical, 48 minutes charged). 226 of 226
  scored, no loss, no re-queue, no truncation; two postconfig replies at HTTP 200 with a
  non-zero return code, in two episodes (recorded, not losses, not server errors under D56;
  every postconfig reply of both E3 jobs was HTTP 200); DR0 exit 0, does not fire.
  Provenance, engine argv (4B) and Slurm limit 48 checks pass; first dispatch 105.4 s after
  the start; lane end 7.7 minutes before USR1.
- Quiet host: no foreign Slurm job in any lane snapshot or 15-second queue sample while either
  job ran; nothing else was submitted between the pairs. S2 v5's job 1271 was submitted at
  08:37:17, after E-4B-E3's VM batch job had ended (08:36:10).
- **Session E3's later end: 2026-10-13T08:36:07Z** (E-4B-E3 by `lane.job_end`; VM batch end
  08:36:10). **E4 may not start before 2026-10-13T20:41:07Z** (20:41:10Z by the VM batch
  end). Other workstreams may use the host until then and must have ended before E-9B-E4 is
  submitted.
- GPU-h: physical 1.2703 for the session (ledger rows in `program/state.json`; program total
  14.3746); charged under D22 303 of E's 406 cap-minutes so far (OE 3, E1 100, E2 100, E3
  100). No outcome was read; the registered analysis runs after the last E job.
- Disclosures: the operator handover across the restarts (above); E-9B-E3's `--test-only`
  printed a start estimate of 08:20:02 while the GPU job started at 07:18:02. No deviation
  from the registration.
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/` (README section "Session
  E3", `e-9b-e3/`, `e-4b-e3/`).

## 2026-10-13 — Q2 successor E `q2-stage1-successor-e-v1`: session E4 ran (E-9B-E4, E-4B-E4); DR0 does not fire; all eight E jobs have run (branch `ops/q2-successor-e`, not merged)

- The E4 operator started at 08:41 UTC from the E3 operator's report and checked the host
  first: S2 v5's step-0 job 1271 (CPU only) running, no E4 pair or run directory, no E4 job
  and no operator process; the operator scripts on the host equal to the committed ones; the
  six earlier E jobs' records and receipts at their DR0 digests. At 08:43 it prepared both E4
  pair directories and rendered E-9B-E4's VM manifest from the export (`c181d0aa...`,
  canonical `72a0f39a...`; `lane validate` 226 slots; `--begin=2026-10-13T20:41:07`), without
  touching Slurm. It polled the queue about every 4 minutes from 08:47 to 20:41 (189 polls;
  one more failed on an ssh connection timeout at about 09:15); job 1271 had left the queue by
  09:21 and the queue was empty at every later poll. `main` (D96) was merged into the branch
  at 17:43, every ledger row kept (21 rows). At 19:33 the export was re-checked against `git
  archive f6144d6b` (7,602 files, 27 symlinks, `.git_sha`, nothing writable).
- **E-9B-E4**: VM job 1272 and GPU job 1274 (`--dependency=after:1272`), submitted
  20:41:27-20:41:28 UTC on an empty queue, after both readings of the gap (20:41:07 by
  `lane.job_end`, 20:41:10 by E-4B-E3's VM batch end); verify and `check-chain` PASS in the
  export; `lane validate` 226 slots; `--test-only` exit 0, id 1273. Both COMPLETED 0:0; GPU
  20:41:28-21:20:14 (00:38:46, 0.6461 GPU-h physical, 52 minutes charged). 226 of 226 slots
  scored, no infrastructure loss, no re-queue, no cap truncation, no restart, no slow or
  undelivered observation, no postconfig failure (376 replies, all HTTP 200); DR0 exit 0,
  does not fire. The manifest named the six E1-E3 jobs by records and receipt; the session gap
  held; provenance PASS (`f6144d6b`, overlay `5d1d4d8f...`), engine argv equal to S1a's for
  9B, Slurm limit 52 equal to the cap; first dispatch 113.0 s after the Slurm start; lane end
  10.3 minutes before the USR1 point.
- **E-4B-E4**: its manifest was rendered after E-9B-E4's DR0 and names the seven earlier jobs
  (E-9B-E4's records `014b4689...`, receipt `79a11458...`). VM job 1275 and GPU job 1277,
  submitted 21:21:45 on an empty queue (`--test-only` id 1276). Both COMPLETED 0:0; GPU
  21:21:45-21:58:03 (00:36:18, 0.6050 GPU-h physical, 48 minutes charged). 226 of 226 scored,
  no loss, no re-queue, no truncation; two postconfig replies at HTTP 200 with a non-zero
  return code, in two episodes (recorded, not losses, not server errors under D56; all 376
  postconfig replies HTTP 200); DR0 exit 0, does not fire. Provenance, engine argv (4B) and
  Slurm limit 48 checks pass; first dispatch 105.9 s after the start; lane end 8.7 minutes
  before USR1.
- Quiet host: no foreign Slurm job in any lane snapshot or 15-second queue sample while either
  job ran; nothing else was submitted between or after the pairs.
- **Session E4's later end: 2026-10-13T21:58:03Z** (E-4B-E4 by `lane.job_end`; VM batch end
  21:58:06). Session E4 was E's last: all eight registered E jobs have run and none fired
  DR0. The registered analysis (section 18 (iii)) is next; other workstreams may use the host.
- GPU-h: physical 1.2511 for the session (ledger rows in `program/state.json`; program total
  15.6257); E's physical total 5.0908 with OE. Charged under D22: 403 of E's 406 cap-minutes
  (OE 3, E1-E4 100 each). No outcome was read.
- Disclosures: one failed queue poll (ssh timeout) during the wait; E-9B-E4's `--test-only`
  printed a start estimate of 21:43:28 (the VM job's limit) while the GPU job started at
  20:41:28, as for E-9B-E3. No deviation from the registration.
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/` (README section "Session
  E4", `e-9b-e4/`, `e-4b-e4/`).

## 2026-10-14 — Q2 successor E `q2-stage1-successor-e-v1`: the registered analysis ran; DR2 Near-equivalent, DR5 NO-GO (branch `ops/q2-successor-e`, not merged)

- Started 22:03 UTC on 2026-10-13 after the orchestrator's restarts, from the host's state: no
  analysis directory or analysis job existed. Every step ran on the host from the read-only
  export of the freeze commit `f6144d6b`, with the registered commands of section 18 (iii)
  unchanged and `ops/q2e-analysis/e_ops.py` (`fb4458a6`) around them. Provenance passed at
  both ends (ledger row 19 `verify` and `check-chain`; plan `4e7298a7...`; every file of E's
  section 23 and S1a's section 20 at its digest). The eight run directories' records matched
  their DR0 digests; the re-run DR0 files are byte-identical to the per-job ones.
- CPU-only Slurm jobs, all exit 0: GLMM 1279 and rescoring 1280-1287, submitted together at
  23:40:14 on an empty queue (after S2 v5's development job 1278 left it); report 1288,
  section 15 items 1289, joint reading 1290 (01:20-01:22 on 2026-10-14). No GPU.
- Complete data, not externally anchored: 1,808 episodes, 0 infrastructure losses. Success:
  4B 27.21% (H-OSW-fixed) / 26.33% (H-GA), 9B 30.97% / 31.86%.
- **DR2 Near-equivalent**: δ (H-GA − H-OSW-fixed) 0.00 pp, 90% t [−2.44, +2.44] (p 1.000);
  X sign flip p 0.093; π_small one-sided upper bound 0.1187 < 0.12. **DR5 NO-GO**: π_small
  0.055, one-sided [0.010, 0.119] < M 0.13; S1b stays closed (D69), nothing starts. DR1 does
  not fire; DR4 does not fire (0.0027-0.0030 GPU-h per episode, 24-27% of the high price). P1
  not estimable; P2 (D_b 10.69% [8.00, 13.53]), P3, P4, P5 not falsified. No session pair's
  shift test rejects after Holm.
- Sensitivities change no rule: corrected verdicts 0 flips (16 live fallbacks on `53ad5833`),
  no metric exception, 0 postconfig server errors, flagged tasks excluded and the D82 110-task
  set both Near-equivalent / NO-GO. Registered secondary (S1a's 32 base tasks): Inconclusive /
  NO-GO as a description (π_small upper bound 0.121). GLMM: the full fit did not converge (no
  positive-definite Hessian); the task:harness test is not computed. The descriptive joint
  reading with S1a: every E − S1a interval covers 0.
- Deviation: the fresh verifier of section 18 had not run when RESULTS was written; the
  analyst's self-check (`ops/q2e-analysis/selfcheck.py`, independent code) reproduced every
  primary point estimate, the t test, DR2 and DR5. RESULTS is provisional until a fresh
  verifier's record is committed.
- Evidence: `program/evidence/2026-10-12/q2-stage1-successor-e-run/RESULTS.md` and
  `analysis/`.

## 2026-10-14 — Public history rewritten (D99)

- Public history rewritten (D99). The host address, the internal inventory and the early
  `gate_b.py` are gone from every public ref. Commit ids from 2026-08-17 on changed; see
  `program/history-rewrite-2026-10-14/`. No result, ledger row or evidence file changed.
- Counts: 929 of 944 commits rewritten; 874 old ids rebuilt exactly by
  `scripts/verify_history_map.py`; 55 tree-changed (44 address or inventory, 11 early
  `gate_b.py`); `main`'s tree unchanged; all 21 ledger rows map as the plan predicted.
- The early `gate_b.py` was in public history from 2026-10-07 (D95) until this rewrite; GitHub
  may serve cached views of old commits until Support removes them.

## 2026-10-14 — S2 v5 `s2-arabic-cua-locale-v5` Phase 0 run, stint 1: staging, the registered census dry-run, and K1 on E (branch `ops/s2-v5`, not merged)

- Frozen in ledger row 22 (status fill `cecd06d8`, freeze commit `7c963f51`). Worktree
  `cotcodec-wt-ops-s2v5`, branch `ops/s2-v5` from `7c963f51`; `main` (`bddf4b38`, a handoff
  update) merged with all 22 ledger rows.
- Staging: `git archive 7c963f51 | ssh fal-h100-01 tar -x` (GNU tar) into
  `~/cotcodec-runs/stage0/s2v5/k1/src/7c963f51.../`, `.git_sha` written, made read-only; 9,308
  files, per-file digest `9a8d7141...`, equal to a Mac export.
- The registered pre-census check ran first: `lane_v5.py submit CENSUS --source-dir EXPORT
  --dry-run` on the host from the freeze export passed (`vm_lane.check_host`'s image, Docker,
  OSWorld, file-cache and PD-cache checks; `check_once`), writing only the stored manifest
  (`efdb8832...`) under `phase0-runs/manifests/`. The census manifest (1,322 slots, rendered by
  `lane_v5.py render-census --freeze-commit`) is committed with it. No census job was submitted.
- K1: 49 manifests rendered by `ap_delta_v5.py render` from the freeze export, equal to v4's
  apart from id fields and A6's cells file on ER and AR. Run in the K1 plan's order, one CPU-only
  job at a time, each on an empty queue through the guarded helper (`--no-e-deadline`; successor
  E is finished). Every job COMPLETED 0:0, every campaign counts (driver exit 0,
  `infra_gates_pass`, image unchanged, no labelled container, no foreign-abort or snapshot
  problem), and every check read so far passes (interim, job by job):
  - 1292 C1 on E: pass.
  - 1293 C2 on E: pass (exactly the predicted 8 L0-raw entries fail).
  - 1294, 1295, 1296 C3 on E (parts 1-3): pass over the three parts, 42 mutants killed and 2
    equivalent (M12 and M13 on H-OSW-fixed), as q2-action-path-v2's attempt 1.
  - 1297 A1 on E: pass, 2,000 of 2,000, 0 restarts; C4 on E pass; pooled step p95 2.69 s.
  - 1298 A2 on E: pass (failures only on cells outside each layer's spec, 0 restarts).
- No K1 check has failed, and nothing was rerun or resubmitted. The stint stopped at 10:44Z at a
  clean point: no job of this workstream running, the queue empty, no labelled container. 42 K1
  jobs remain (A5 and A6 on E, then A, ER, AR and PL, A3 on AR, the rung; about 33 hours of
  serial wall clock at E's pace), then the K1 verdict, the census, the oracle and K0.
- Evidence: `program/evidence/2026-10-14/s2v5-phase0-run/` (README with per-job records; per job
  its submission snapshot, `scontrol`, batch output, receipts, manifests and `check-JOB.json`;
  the census dry-run; the 49 K1 manifests). Cycle records and VM logs stay on the host.

## 2026-10-14 — S2 v5 `s2-arabic-cua-locale-v5` Phase 0 run, stint 2: K1 on E completed, image A through A1 (branch `ops/s2-v5`, not merged)

- Checked the host before submitting: queue empty, `ops.log` and the K1 run directory held jobs
  1292-1298 only, no labelled container. No job was resubmitted.
- K1, in the plan's order, one CPU-only job at a time, each on an empty queue through the
  guarded helper (`--no-e-deadline`). Every job COMPLETED 0:0 and every campaign counts; every
  check read so far passes (interim, job by job):
  - 1299 A5 on E: pass (20 of 20 reset sentinels pristine; HMP `sendkey menu` 0 of 21, reported
    and not judged, as in q2's jobs 374 and 964).
  - 1300 A6 on E: pass (300 of 300, every entry 5 of 5, q2's cells file).
  - 1301 C1 on A: pass. 1302 C2 on A: pass.
  - 1303, 1304, 1305 C3 on A (parts 1-3): pass over the three parts, 42 killed and 2 equivalent
    (M12 and M13 on H-OSW-fixed), as on E.
  - 1306 A1 on A: pass, 2,000 of 2,000, 0 restarts; C4 on A pass; pooled step p95 2.68 s.
- All eight checks on E have now run and pass. No K1 check has failed, and nothing was rerun.
- The stint stopped at about 16:25Z with job 1307 (A2 on A, submitted 16:20:55Z) running; its
  collection is the next stint's. 27 K1 jobs follow it, then the K1 verdict, the census, the
  oracle and K0.
- Evidence: `program/evidence/2026-10-14/s2v5-phase0-run/` (README rows and notes for 1299-1307,
  `k1-jobs/1299`-`1306`, `k1-jobs/1307/submit-1307.txt`, `k1-jobs/c3-a-interim-1303-1305.json`,
  operator aids `campaign_summary.py` and `c3_parts.py`).

## 2026-10-14 — Exploratory inference baseline `inference-baseline-v1`: where time and HBM go when vLLM serves on H100 (branch `stage0/inference-baseline`, not merged)

- Kevin asked to "just straight up run inference" (D103 area 2). This is an exploratory baseline:
  no registration, hypothesis or decision rule, and no confirmatory claim. It grounds the
  question sweep running in parallel.
- Ran vLLM 0.31.0's own `bench serve` and `bench throughput` code in the digest-pinned
  `cotcodec-vllm` overlay, through the docker-research lane, with NVML and Prometheus sampling.
  - Models: Qwen3-0.6B-Base, Qwen3-1.7B-Base, Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-35B-A3B (MoE,
    TP 1 and 2), and Qwen3-32B (dense, TP 1, 2 and 4).
  - Qwen3-32B was downloaded under D1 by the GPU-less fetch lane (job 1310, receipt
    `06e4a7e9...`) and registered in `models/registry.yaml`.
  - Grid: chat, 8k-in, 32k-in and long-output shapes at concurrency 1-128. The ablations were
    prefix caching on and off (1.7B, 9B) and FP8 KV (9B, 32B TP 1).
  - Seed 42, two repeats per cell, prefix cache reset before every run.
  - 258 of 258 serving runs ok, 36 offline runs.
- Jobs: overlay builds 1311 and 1325, then jobs a-h (1314, 1320-1324, 1329, 1330). All COMPLETED
  0:0. Physical total 4.7806 GPU-h, against a budget of 6. Fetch 1310 and selftests 1312 and
  1326 were CPU-only.
- Deviations:
  - Job e's one-GPU MoE engine was refused, because `max_num_seqs` 256 exceeds the 181 GDN-state
    blocks that fit. Job h reran it with 128. (Corrected 2026-10-14: vLLM's check counts one
    block per sequence, but each running sequence took four, so job h ran at most 51 chat
    sequences.)
  - Job f's limit cut two TP 4 second repeats. Job g reran both cells twice on a fresh engine.
- Exploratory reading (details and caveats in the README):
  - Single-stream decode on the 9B and 32B streams weights at about 73-83% of 3.35 TB/s (an
    analytical estimate) at TP 1-2. The small models and the 3B-active MoE are overhead-bound,
    at 26-62% (corrected 2026-10-14 from 25-61% for the float32 GDN state).
  - KV capacity ranges from 28k tokens (32B TP 1) to 3.1M tokens (MoE TP 2). It bound the dense
    models, and the GDN state bound the one-GPU MoE (corrected 2026-10-14; first written as
    "binds only for the dense models"). FP8 KV doubles it and gives 1.3-1.5x where it binds.
  - Prefix sharing gives about 2x throughput.
  - Heavy cells often run at the 700 W power cap.
  - Run-to-run spread: a median of about 1% (p90 4-5%) for throughput and TPOT.
- Evidence: `program/evidence/2026-10-14/inference-baseline/` (README; raw JSON and CSV per job;
  lane receipts; manifests; overlay, fetch and selftest records; `analysis/`). Code:
  `scripts/run_inference_baseline.py`, `scripts/analyze_inference_baseline.py`,
  `experiments/serving/inference-baseline-v1.yaml`, `tests/test_inference_baseline.py`.

## 2026-10-14 — `inference-baseline-v1` corrected after an independent check (branch `stage0/inference-baseline`, not merged; exploratory)

- An independent checker reproduced the analysis byte for byte from the committed records and
  found two medium and three low problems. All are fixed in the README, `analysis/` and the
  entry above. Raw records are unchanged and no GPU job ran. The analysis reran on the host from
  the committed job records (`corrections/analysis-rerun.txt`).
- GDN state dtype (medium). vLLM 0.31.0 keeps the hybrids' gated-DeltaNet recurrent state in
  float32, as the checkpoints' `mamba_ssm_dtype` asks, not in bf16 as the analysis assumed.
  - Three CPU-only, read-only source checks (1346, 1348 failed on a `grep`, 1350) printed the
    lines from both overlay images: `model_executor/models/config.py:829-832` and
    `:1060-1062`, `layers/mamba/mamba_utils.py:104-110`. Every hybrid engine's
    `cache_config_info` also records `mamba_ssm_cache_dtype` float32.
  - Per-sequence state is 49.1 MiB for Qwen3.5-4B and 9B and 61.4 MiB for the MoE (first
    25.1 and 31.4). At long-output-128 the 9B's state is 12.7 GB of 38.8 GB per step (first
    6.5 GB, 20%), and its estimated bandwidth use 76% (first 64%). Batch-1 estimates moved by
    at most 0.4 points.
- One-GPU MoE (medium). Job h ran at most 51 sequences at chat-128, because each held one
  attention block and three GDN-state blocks of its 207. 77-79 requests waited and the median
  TTFT was 5.7 s. The state, not KV, was its binding limit.
- Low items:
  - `gpu_memory_utilization` 0.90 sets Qwen3-32B TP 1's KV. vLLM's log says 13.44 GiB (55,067
    tokens) would fit instead of 6.89 GiB: the cheapest untried lever.
  - TP 4 32k-32 differs between engine instances: median ITL 129.5 against 29.4 and 35.9 ms,
    p99 1.41 against 0.48 and 0.49 s, with equal throughput.
  - Block alignment does not fully explain the 9B's prefix hit rates (predicted 74.3% and
    79.6%, measured 63.7% and 74.3%).
  - Smaller mismatches fixed: the spread cells, c=1 power, 130 cells, peak GiB and start-up
    overlap. The thin records are stated: empty `scontrol` files, the in-image pytest that
    never ran, `selftest.json` with vLLM's stdout notices, and 56 host files not committed.
- The README now opens with "Main takeaways (corrected)". The analysis script takes the GDN
  dtype from the engine record, and a new test checks it against vLLM's logged page padding
  (`tests/test_inference_baseline.py`: 10 passed).
- Evidence: `program/evidence/2026-10-14/inference-baseline/` (`gdn-state-dtype/`,
  `corrections/`, regenerated `analysis/`, README).

## 2026-10-14 — G2 exploratory pilot: GDN-hybrid train-inference mismatch by position (branch `stage0/g2-pilot`, not merged)

- EXPLORATORY executable pilot of G2 (D104), the gauntlet's pilot; no preregistration, no
  confirmatory claim. Config `experiments/g2/g2-pilot-v1.yaml`; new entry points
  `scripts/run_g2_rollouts.py` (cotcodec-vllm cu129 overlay, vLLM 0.31.0),
  `scripts/run_g2_teacher_force.py` (research source overlay: torch 2.11, transformers 5.15,
  FLA 0.5.2) and `scripts/analyze_g2_pilot.py` (CPU), with `harness/g2_pilot.py` and
  `tests/test_g2_pilot.py`.
- Dense control: Qwen3-8B (`b968826d`, Apache-2.0) fetched in full under D1 by the GPU-less
  lane (job 1333, 16.4 GB, artifact root `325ab760...`), its receipt in the lane's own
  receipt root so the earlier metadata receipt stands. Prompts: 64 MATH-500 level-5 problems
  (MIT, `6e4ed1a2`), seeded selection.
- GPU jobs, each on a queue with no inference-baseline job: builds 1334, 1335, 1339, 1340;
  rollouts 1337 (attempt 1, no data: `LLM.enqueue` returns internal request ids, outputs carry
  external ones, so all 192 finished rollouts were dropped; the worker then hung at exit;
  cancelled after 00:12:52 by the lane's records) and 1342 (attempt 2, fixed: own ids via
  `LLMEngine.add_request`, DELTA streaming, bounded exit); teacher forcing 1352. **0.4402
  physical GPU-h of the 0.5 cap** (corrected 2026-10-14 from 0.4372, which took attempt 1
  from an uncommitted RunTime of 00:12:41). CPU: selftests 1331, 1332, 1338, 1343; fetch 1333
  (the CPU jobs 1331-1333 ran beside the baseline's GPU jobs g and h).
- Scope run, cut by attempt 1's cost: 24 prompts; Qwen3.5-4B x seeds 42/43/44 (72 rollouts),
  Qwen3-8B x seed 42 (24); 120 s of generation per model (41 of 72 hybrid rollouts cut at
  about 11.5K tokens); r1 (HF+FLA chunk bf16, unpacked, batch 1: the dossier's R2) on all,
  R3 (FLA fused_recurrent) and R4 (fp32 reference) on seed 42; the dossier's packed R1, R5
  (vLLM prefill) and the common-text arm not run. Prompts are MATH-500 level 5, not the
  dossier's DAPO-Math.
- Readings (exploratory; corrected 2026-10-14, see the next entry): Qwen3.5-4B rollout vs
  trainer mean |dlogp| 0.0076, p99 0.11, k3 2.7e-4, 0.03% of ratios outside [0.8, 1.25]; up
  about 12% over the first 3K positions as token entropy rises, then flat to 11.5K. Position
  slope with entropy-bin fixed effects -5.2e-5 per 1K [-6.8e-5, -3.5e-5] (first written
  +1.3e-5 [-2.3e-5, +4.9e-5] from string-binned entropies); within sequences +2.4e-5
  [-2.8e-5, +7.5e-5]. vLLM decode and the trainer sit about equally far from fp32 (0.0073,
  0.0076; the fp32 reference has no second implementation); swapping chunk for
  fused_recurrent GDN changes the mismatch by under 1%, but every bf16 pair sits at the same
  floor (about 0.0075), so the swap does not show the kernel has no effect. Qwen3-8B (not
  size-matched, different text, one seed): 0.0123, p99 0.19, falling with position; it cannot
  carry a hybrid-vs-dense comparison, and the pilot does not evaluate kill criterion 1 (first
  written "reads as the null"; withdrawn). The p99 tail is nearly constant across bins (an
  untested bf16-logit explanation; an fp32 LM-head arm would test it).
- Evidence: `program/evidence/2026-10-14/g2-pilot/` (README with tables, figure and a "what
  it says and does not" section; per-token data, lane records, build and fetch receipts,
  manifests, operator log). Raw outputs stay on the host under
  `~/cotcodec-runs/stage0/g2-pilot/` with SHA-256 in the README.

## 2026-10-14 — G2 pilot corrected after an independent check (branch `stage0/g2-pilot`, not merged; exploratory)

- An independent checker reproduced the analysis byte for byte, recomputed it from the raw job
  outputs on the host, and found one high, one medium and several low problems. All are fixed
  in the README, `analysis/`, the figure, `program/state.json` and the entry above. Raw
  records and `data/per-token.npz` are unchanged and no GPU job ran; the analysis reran on
  the host from the committed `per-token.npz` and reproduces byte for byte
  (`corrections/analysis-rerun.txt`).
- Entropy binning (high). The config's top entropy edge `1.0e9` loads through PyYAML (YAML
  1.1) as a string, so numpy binned entropies as text: 24.1% of the hybrid's and 24.9% of the
  dense model's tokens were misbinned. Corrected, the hybrid's slope within entropy bins is
  -5.16e-5 per 1K [-6.85e-5, -3.47e-5] (all seeds, dec vs r1; per seed -6.2e-5, -5.8e-5,
  -3.5e-5, each CI excluding 0), not the null first reported; the dense model's is -2.4e-4
  (first -3.3e-4). With 6, 20 and 50 entropy quantile bins it is -4.7e-5 to -5.4e-5. So the
  raw early rise follows the entropy profile, and at fixed entropy the mismatch falls
  slightly with position. The edge is now `1.0e+9`, `harness.g2_pilot.numeric_edges` refuses
  non-numeric edges in `load_config` and in the analysis, and new tests fail on string edges
  (`tests/test_g2_pilot.py`: 15 passed, locally and on the host).
- Kill criterion 1 (medium). The "reads as the null" reading is withdrawn. Slopes per 1K
  (hybrid, all seeds): pooled +7.6e-5 [+2.2e-5, +1.3e-4]; entropy fixed effects -5.16e-5
  [-6.85e-5, -3.47e-5]; sequence fixed effects (new) +2.4e-5 [-2.8e-5, +7.5e-5];
  sequence-by-entropy-bin -4.95e-5 [-6.76e-5, -3.01e-5]. The dense control (Qwen3-8B against
  the 4B, different text, one seed) cannot carry a hybrid-vs-dense comparison.
- Low items, now stated in the README: composition vs position (41 of 72 hybrid rollouts cut
  at about 11.5K); the bf16-vs-bf16 noise floor under the chunk-vs-recurrent attribution; the
  fp32 reference has no second implementation; dense-control comparability; the deviations
  from the dossier (MATH-500 level 5, not DAPO-Math; r1 is the unpacked batch-1 HF forward,
  the dossier's R2); attempt 1's GPU-h from the lane's records (0.2144; pilot total 0.4402);
  the CPU jobs 1331-1333 beside the baseline's jobs g and h (also noted in the baseline
  README); the miles PR #3597 aggregate is "consistent with", not "matched"; and the
  `models/registry.yaml` qwen3-8b note now that its full weights are fetched.
- Main merged into the branch first; `program/state.json`'s GPU-h ledger keeps every row from
  both (77 rows) and `gpu_hours_spent_this_program` is the ledger sum, 20.8466.
- The README opens with "Main takeaways (corrected)". Code: `scripts/analyze_g2_pilot.py`
  (numeric bins, within-sequence slopes, entropy-standardized curve, by-entropy tables),
  `harness/g2_pilot.py`, `experiments/g2/g2-pilot-v1.yaml`, `tests/test_g2_pilot.py`,
  `program/evidence/2026-10-14/g2-pilot/corrections/robustness_checks.py`.

## 2026-10-15 — AM1 Step 0 (exploratory): exact replay of the Qwen3-8B reader and the cost of exact subset tables (branch `stage0/am1-step0`, not merged)

- What ran. EXPLORATORY Step 0 of AM1 (D104; dossier entry 3), 0.1978 physical GPU-h of the 1.5
  cap: one cotcodec-vllm overlay build (job 1393, `b95ac22c`, image `sha256:51540dd5`) and one main
  job (1397, 00:10:48 on 1 H100, 2026-10-14 23:01-23:12Z) with five vLLM 0.31.0 engine sessions
  (batch-invariant `bi-a`, `bi-b` restart, `bi-c` reconfigured; default `default-a`, `default-b`
  restart), 24 passes and 37,136 requests. CPU-only: LongMemEval-S fetch 1362, selftests 1383
  and 1394. Both GPU jobs were submitted with no G2b job in the queue; two CPU jobs ran beside
  G2b GPU jobs and G2b's CPU job 1398 ran beside the main job (README, Problems).
- How batch invariance is enabled in v0.31.0 (read-only at `db9527a4`, line-pinned in the README):
  `VLLM_BATCH_INVARIANT=1`, applied by the worker at start-up; on an H100 it routes every bf16
  linear layer and the LM head through a Triton persistent matmul, sets FlashAttention
  `num_splits=1`, overrides softmax/log-softmax/bmm/mean, keeps prefix caching with FLASH_ATTN,
  and (no tuned Qwen3-8B tiles on Hopper) stays on torch.compile with CUDA graphs. The nine cited
  files hash the same in the image as at the tag.
- LongMemEval-S under D1: `xiaowu0162/longmemeval-cleaned` @ `98d7416c`,
  `longmemeval_s_cleaned.json`, 277,383,467 bytes, SHA-256 `d6f21ea9...` (equal to the Hub's LFS
  oid), MIT; on the host only.
- Readings (exploratory): in batch-invariant mode every A/A comparison was identical in tokens
  and log-prob bits (4,096 of 4,096 greedy requests under a shuffled order, a restart and a
  reconfigured engine, each 95% CP [0.9991, 1]; 512 at concurrency 8, 96 one at a time, 512 from
  a warm prefix cache; 1,024 of 1,024 seeded samples shuffled and restarted). The default mode
  repeated all 4,096 replies on a same-schedule restart but changed 3 of 4,096 under a shuffled
  order, 14 of 512 at concurrency 8 and 3 of 96 one at a time. Batch invariance cost 1.32-1.38x
  wall time on batched passes and 2.5-3.1x at concurrency 8 or 1 (both modes power-capped at
  700 W when batched). The 256-subset tables cost 2.8 GPU-s per question for both arms
  (4,096 requests in 22.6 s; 405-token prompts, 64.5% prefix-cache hits): about 0.16 GPU-h per
  pass for 200 questions, against the dossier's 4-6 GPU-h per arm. The demo's crude containment
  utility cannot score the tables (a judge is required); a CPU census finds 416 of 500 questions
  usable with user-turn memories, 84% of them with one or two required memories, and BM25 top-8
  recall of gold turns 0.74.
- Feasibility: AM1's full study is feasible on this node and GPU is not its constraint (about
  1-2 GPU-h for the folded reader work at these memory units); the open work is the judge, the
  estimators, the placebo arms, a cross-GPU A/A, and pools that produce mixed interaction
  structures so that H2 can fire.
- Evidence: `program/evidence/2026-10-15/am1-step0/` (README with "Main takeaways", identity,
  throughput, cost, demo and census tables; fetch receipt; pools summary; lane records; every
  pass's tokens and log-probs; host analysis rerun byte-identical to the in-job analysis). Raw
  outputs, the study artifact and the dataset stay on the host under
  `~/cotcodec-runs/stage0/am1-step0/`.

## 2026-10-15 — G2b exploratory: a bf16 GDN recurrent state in vLLM 0.31.0, concurrency and train-inference mismatch (branch `stage0/g2b-state-dtype`, not merged)

- EXPLORATORY measurement (no preregistration, no decision rule, no confirmatory claim) that
  follows D105's float32-state finding and the G2 pilot (D104). Config
  `experiments/g2/g2b-state-dtype-v1.yaml`; new entry points `scripts/run_g2b_rollouts.py`
  (vLLM overlay: long rollouts, saturation waves, paired prefill), `scripts/run_g2b_teacher_force.py`
  (research overlay: HF+FLA unpacked, a verl-style packed varlen path, fp32 reference) and
  `scripts/analyze_g2b_state_dtype.py` (CPU), with `harness/g2b_state_dtype.py` and
  `tests/test_g2b_state_dtype.py` (15 pass). The G2 pilot's scripts came in by merging
  `stage0/g2-pilot` (with its request-id and float entropy-edge fixes).
- The setting, read from the image (CPU jobs 1354, 1355): `--mamba-ssm-cache-dtype`
  (`MambaDType` allows auto, float32, float16, bfloat16; `config/cache.py:61`); "auto" copies the
  checkpoint's float32. The trainer (FLA 0.5.2) accumulates the running state in fp32 and stores
  bf16 per-chunk snapshots.
- GPU jobs (jobs ran 2026-10-14 22:21-23:00 UTC; the directory follows the requested date):
  builds 1357, 1358, 1379; smokes 1361, 1364, 1366 (failed after r1: a list-unpacking bug in the
  packed check, fixed in `4555c647`) and 1382; per model and state dtype, phase R (72 long
  reasoning rollouts, 24 MATH-500 L5 prompts x seeds 42/43/44, up to 32K tokens) and phase S
  (one fixed-length wave per seed): 1368/1370 (4B), 1372/1374 (9B), 1376/1378 (35B-A3B on one
  GPU); paired prefill 1385, 1389; teacher forcing 1387, 1391. **1.8386 physical GPU-h of the 3.0
  cap.** Lane-job run times come from the lane's started_at to finished_at, not scontrol
  RunTime: every scontrol record but 1391's (RunTime 1 s above its lane interval) had expired
  by collection and Slurm accounting is off. The lane intervals sum 0.002 GPU-h under the
  total, which is left as entered. CPU: source checks, selftests 1356, 1359,
  1380, analyses 1392, 1398, 1399, a reproduction check 1400, checks 1401.
- No fresh-job resume test (AGENTS.md hard rule 2): like the G2 pilot and the inference
  baseline, these short exploratory jobs ran without one; as in the pilot, a stop signal saves
  finished work and writes a "no resume" checkpoint marker (no job was signalled). Recorded as a
  disclosed exemption for short exploratory measurements.
- Readings (exploratory, one stack, 72 rollouts per arm and model):
  - (a) bf16 halves the state (49.1 to 25.1 MiB; 61.4 to 31.4 on the MoE) and the hybrid block
    (528 to 272 tokens), doubling the block pool. Saturation waves: 1.33x (4B), 1.38x (9B; 114
    preemptions per wave to 0) and 1.37x (one-GPU MoE; peak running 51 to 99). The gain shrinks
    with length; the 4B/9B pools never filled in the long rollouts.
  - (b) Rollout vs trainer mean |dlogp| rises from 0.0077 to 0.0357 (4B) and 0.0074 to 0.0365
    (9B), k3 18-21x, and grows +1.3e-3 / +1.5e-3 per 1K within sequences (fp32 flat): 1.25x at
    0-1K, about 7-8x at 28-32K, in every entropy bin. vLLM prefill in the bf16 state stays at
    1.05x of fp32 against the trainer, and the bf16 decode is 0.034-0.037 from the fp32
    reference while the trainer is 0.008 from it. So the data place the drift in vLLM's
    bf16-state decode path, consistent with per-step state rounding; precision is not
    separated from the changed block layout (528 to 272 tokens; 1,056 to 544 on the MoE) and
    kernel instance. No RL training ran, so nothing about RL outcomes is measured.
  - The bf16 rollouts reason longer: 9B 35 of 72 hit the 32K cap vs 7; paired over (prompt,
    seed) bf16 ran longer 47-10 (4B) and 56-9 (9B), sign test p 7.5e-7 and 2.0e-9; tails are not
    loops; accuracy among ended rollouts is similar by string match.
  - Packed varlen teacher forcing equals unpacked (4B exactly on 942,608 tokens). The 9B mean
    of 1.7e-5 is one whole sequence differing at noise level (mean 0.0054; its pack neighbours
    exactly 0); with the smoke's single-sequence 0.0027 it points to shape-dependent trainer
    numerics of about 0.003-0.005 per sequence, uncharacterised. The fp32-state arm reproduces
    the pilot (0.0077, k3 2.7e-4) and stays flat to 32K.
  - Saturation-wave scheduling is deterministic (identical preemptions in every wave), so the
    three waves replicate timing only. The metric sampler's first sample per phase repeats the
    previous phase's gauges (it sets no reported peak and moves means by about 1 in 76).
- Evidence: `program/evidence/2026-10-15/g2b-state-dtype/` (README with tables, figure, spread,
  "what it says and does not", problems; seed-42 per-token subsets, rollout texts, lane records,
  manifests, build and source-check records). Full per-token files, rollout token arrays and the
  prefill and teacher-forcing arrays stay on the host under `~/cotcodec-runs/stage0/g2b-state-dtype/`
  with SHA-256. Next: a float16-state arm and a forced-block control.
- An independent check passed it with one medium and four low items. All five are fixed in
  text and records only (README, this entry, the `program/state.json` bases); no GPU job ran
  and no result changed: the mechanism wording and a prescriptive RL line, the GPU-h basis,
  the 9B packed residual, the sampler's first sample and wave determinism, and the resume
  exemption.

## 2026-10-15 — G2c exploratory: GDN state precision vs block layout in vLLM 0.31.0 (branch `stage0/g2c-precision-layout`, not merged)

- EXPLORATORY follow-up to G2b (no preregistration, no decision rule, no confirmatory claim).
  G2b's bf16 GDN state also halved the hybrid block (528 to 272 tokens), so its drift could not
  be pinned on precision. Two new arms on G2b's prompts, seeds and engine settings (inherited by
  hash from G2b's config): `fp16` (float16 state, vLLM's own 272-token block: bf16's layout and
  memory) and `bf16_b528` (bf16 state with `block_size=528`: fp32's layout and block pool).
  G2b's fp32 and bf16 arms were reused from their committed, hash-bound outputs, not rerun; the
  same code recomputes G2b's committed numbers exactly. Config
  `experiments/g2/g2c-precision-layout-v1.yaml`; `harness/g2c_precision_layout.py`,
  `scripts/run_g2c_rollouts.py`, `scripts/run_g2c_teacher_force.py`,
  `scripts/analyze_g2c_precision_layout.py`, `tests/test_g2c_precision_layout.py`. G2b's
  scripts came in by merging `stage0/g2b-state-dtype` at `a213572e` (read-only on that branch).
- The other off-diagonal cell, fp32 at 272-token blocks, cannot be run in vLLM 0.31.0 without
  code changes. Read-only source (CPU jobs 1403, 1409): `platforms/interface.py`
  `_align_hybrid_block_size` (lines 835-1018) aligns to max(16, user block), raises a block whose
  attention page cannot hold the GDN page, and asserts attention page >= GDN page. The smoke's
  dummy-weight probe confirmed it: fp32 with `block_size=272` resolved to 544. bf16 with 528 is
  kept, its GDN page padded 97.01%.
- GPU jobs (2026-10-15 00:10-00:54 UTC): builds 1406, 1407; smokes 1414 (probe and both arms)
  and 1422 (teacher forcing); per model one H100 running both arms in turn (phase R, one wave,
  prefill in each arm's own engine): 1418 (4B), 1420 (9B); teacher forcing r1 (all 144) and r4
  (32): 1428, 1431. **1.2158 physical GPU-h of the 1.5 cap.** CPU: source checks 1403 and 1409
  (with selftests), analysis dry runs 1423-1425 (two early failures, fixed), analyses 1433,
  1437, 1438, checks 1442 (ruff clean; 3,291 tests pass; the 2 failures, both r04 tests, fail
  the same way at `a213572e`). No fresh-job resume test (AGENTS.md hard rule 2): the
  disclosed exemption G2b used.
- Readings (exploratory, one stack, 72 rollouts per arm and model):
  - The state's number format, not the block layout, drives the ~4.7x drift. bf16_b528's
    rollout-vs-trainer mean |dlogp| is 4.64x (4B) and 4.74x (9B) fp32's, with bf16's
    within-sequence growth (+1.31e-3 vs +1.33e-3; +1.46e-3 vs +1.46e-3 per 1,000 tokens).
    - On the 4B it equals bf16's: 0.0357 vs 0.0357, ratio 1.00. Its rollouts repeat G2b's bf16
      rollouts token for token: 66 of 72 are identical up to the shorter, and 99.96% of decode
      log-probs are bit-equal.
    - On the 9B it is 4% below bf16's (0.0352 vs 0.0365, 0.96 [0.94, 0.99]). Standardizing by
      position removes only about a quarter of that gap. About 3% remains at matched positions
      (0.97 [0.95, 0.99], independent check). One engine instance per arm cannot split it
      between the layout and the instance. The 9B rollouts diverge after a median 220 tokens.
    - bf16_b528's rollouts run as long as bf16's.
  - fp16 at bf16's layout keeps 26% (4B) and 17% (9B) of bf16's excess mean |dlogp| over fp32,
    pooled (0.0151 and 0.0124). At matched positions it keeps somewhat more, 28-29% and
    20-21%, because fp16 rollouts are shorter. So it keeps a fifth to under a third of the
    excess. It keeps 14% and 7% of the excess k3 and 43% and 31% of the excess slope.
  - fp16 is not fp32: 2.0x and 1.7x fp32's mean, growing +5.8e-4 and +4.5e-4 per 1,000 tokens.
    Near 30K it is about 3x fp32 on the 4B and 2-2.5x on the 9B. The 9B value rests on 7 fp32
    sequences: 2.54 in the 1,024-token bin from 30,720, and 2.05 over positions
    30,000-30,999. fp16 rollouts end like fp32's (54 vs 57 and 65 vs 65 EOS; paired 37-24 and
    38-29, p 0.12 and 0.33).
  - The drift stays in vLLM's decode path: prefill in each arm's own engine is at fp32 level.
  - One wave per arm, in different jobs on a shared host: fp16 keeps bf16's throughput (1.34x
    and 1.38x over G2b's fp32 wave). bf16_b528, the bf16 state dtype at fp32's block pool,
    gives 1.33x on the 4B and 1.23x on the 9B, with fp32's preemptions.
    - So the state dtype at fp32's pool carries the whole 4B gain and about 58% of the 9B gain
      (roughly ±10 points from wave noise).
    - Bytes moved and the dtype-specialized kernel are not separated.
  - Not separated: the dtype-specialized kernel instance from precision; within fp16, mantissa
    from exponent range; the 9B's ~3% layout-arm residual, between layout and engine instance.
    No RL training ran.
- An independent check passed it with one medium and three low wording items. All four are
  fixed in text and records only (README, this entry); no GPU job ran and no committed number
  changed.
  - The 9B layout gap is about 3% at matched positions, not length composition.
  - fp16's excess fraction is a fifth to under a third.
  - The position bins are 1,024 tokens wide, and the 30K tails depend on the bin edges.
  - The throughput split is the state dtype at fp32's pool, from single waves.
  - The standardized and 1,000-token-bin values are the check's (CPU jobs 1443-1445; its code
    is not committed).
- Evidence: `program/evidence/2026-10-15/g2c-precision-vs-layout/` (README with the four arms side
  by side, figure, problems; seed-42 per-token subsets, rollout texts, lane records, manifests,
  build, selftest and source-check records). Full per-token files and raw arrays stay on the
  host under `~/cotcodec-runs/stage0/g2c-precision-layout/` with SHA-256.

## 2026-10-15 — AM1 development-set pilot (exploratory) and the draft registration am1-memory-credit-v1 (branch `stage0/am1-study`, not merged)

- What ran. EXPLORATORY, 1.4862 physical GPU-h of the 2.0 cap: three overlay builds (1405,
  1432, 1439) and three jobs on 2 H100 each: the pilot 1411 (00:26:45), the cross-GPU A/A
  diagnostic 1435 (00:11:04) and the eager replay check 1441 (00:05:07). LongMemEval-S's 416
  usable questions were split with seed 42 by type into 63 development and 353 held-out
  questions (`experiments/am1/memcredit-split-v1.json`); only the development split was used.
- Findings (exploratory; `program/evidence/2026-10-15/am1-dev-pilot/README.md`):
  - Judge: Qwen3-32B in batch-invariant mode with LongMemEval's official answer-check prompt
    agrees with a blind hand check (by the agent, not a human) on 117 of 120 replies (kappa
    0.95); Qwen3-8B 109 (0.82); Step 0's containment rule 87 (0.45).
  - Tables: 37 of 126 exact 256-subset tables are constant (all 0); of the 89 others, 53 are
    non-monotone, 22 single-memory, 8 AND, 2 OR. H1: order >= 2 share 0.374, above the
    gold-count AND/OR baseline by 0.121 [0.046, 0.198].
  - H2 (B = 4 of 8, retrieved arm): keep-set regret against the exact optimum is 0.214 [0.121,
    0.316] for leave-one-out, 0.097 for permutation Shapley-16, 0.070 for SNIPW-64, 0.132 for
    retrieval rank, 0.263 for raw attention, 0.079 for exact Shapley, 0.576 for a random set;
    the gold arm agrees.
  - AM2: 70.8% of gold deletion labels survive length- and rank-matched swaps and reorders,
    16.7% of non-gold ones; a content-free reorder flips 13.1% of pools.
  - AM6: necessity AUROC 0.868 for raw attention, 0.935 for cross-fitted heads, 0.888 for the
    reply-overlap baseline.
  - Replay: compiled batch-invariant replay is exact only for the same compiled kernels. One of
    four fresh reader compiles (job 1411, GPU 0, which made the pilot's tables) autotuned a
    different inductor reduction block and changed 3.1% of replies (0.25% of judged cells);
    copied compile caches and enforce_eager replay bit-exactly across GPUs, processes, orders
    and jobs, eager at 1.06x the compiled pass's wall time.
- Draft registration: `program/preregistrations/am1-memory-credit-v1.md` (DRAFT, not frozen, no
  ledger row) with `experiments/am1/am1-memory-credit-v1.yaml`: the held-out run in eager mode,
  H1 descriptive, H2 decisions per primary rule (MISSPECIFIED if the 99% lower bound of the B = 4
  regret exceeds 0.05, ADEQUATE if the upper bound is below 0.02), gates (replay, judge with a
  fresh hand check, constant tables, interactions), power simulated from the pilot, about 1.1
  GPU-h expected under a 2.1 cap. The prepare script and the driver refuse held-out data unless
  the registration is frozen.
- Problems: a quadratic pass read idled both GPUs for about 15 of job 1411's 26.75 minutes (fixed
  in `9c3d0db8`); G2c GPU jobs started beside job 1411; a transposition in the hand labels was
  corrected against the agent's item notes (both files kept).

## 2026-10-15 — `am1-memory-credit-v1` (CONFIRMATORY, frozen, ledger row 23): artifact, image, selftest and the registered GPU job ran; hand-check sample drawn, unlabelled (branch `ops/am1`, not merged)

- Operator (did not draft the registration), from the freeze commit `9ad36b10` only: a clean
  clone on the host from a git bundle (`git archive` of `9ad36b10` byte-identical on the Mac and
  the host, `8806cd7b...`), section 17's 19 pins re-hashed and matching; the source capsule
  `a46be5ed...` (12,492 files, carries the ledger row); 80 tests pass on the host clone.
- Held-out artifact by the registered `memcredit_study_prepare.py artifact --split heldout`
  command: 347 questions (the confirmatory set), `f23bca04...`, 12,669,196 bytes, rebuilt
  byte-identically; host only.
- Image: overlay build 1454 (1 H100, 00:01:02) from the capsule, `sha256:abcd2b56...`; the
  post-build CPU selftest 1455 with the held-out artifact mounted passes (190,156 reader prompts
  fit, 694 of 694 pools' memory spans, judge prompts fit, attention code ok).
- The registered GPU job 1458 (2 H100, limit 90 minutes; GPUs 2-3, D110's jobs on 0-1
  untouched), submitted once with no other GPU job of this program queued or running:
  COMPLETED 0:0 in 00:45:49. Every phase and worker complete; both reader passes 190,156 of
  190,156 (1,281 s canonical, 2,297 s shuffled, neither stopped by the 3,600 s budget, so the
  reader-cap contingency does not arise); 10,230 judge items finished by both Qwen3-32B passes
  and the Qwen3-8B judge; attention 694 of 694 pools. Nothing rerun.
- Hand-check sample by the registered `hand-sample` command: 120 items, SHA-256 `cebfe191...`,
  no label field; on the host, not labelled. No analysis ran (`analyze`, `aa`), no outcome was
  read; G2 is PENDING. Next: blind labels (an agent unless Kevin labels, D9/D111), their
  SHA-256 committed, then `analyze` and `aa` as registered.
- GPU-h: 1.5444 physical (build 0.0172, job 1.5272) of the 3.1 cap; program total 27.1294.
  D111's disclosure stands: no gauntlet score; blind discrimination and the two
  provider-distinct reviews did not run.
- Evidence: `program/evidence/2026-10-16/am1-confirmatory/README.md` (ops scripts, logs,
  manifests, build and selftest records, lane and worker records, text-free judge items).

## 2026-10-15 — `am1-memory-credit-v1` (CONFIRMATORY, frozen, ledger row 23): hand labels receipted, registered analysis run; every gate passes; leave-one-out and the other four primary rules MISSPECIFIED (branch `ops/am1`, not merged)

- Blind G2 labels by an isolated agent (Kevin did not label; D9/D111): 120 rows, SHA-256
  `70a5f2ec...`, kept on the host (the rows carry free-text notes). The digest was committed
  before the join (`9e641945`, 04:22:22Z).
- The registered `analyze` (with `--hand-labels-sha256` and `--expected-evidence-sha256`) and
  `aa` ran once (04:24:06-04:24:39Z, host CPU) from a fresh `git archive` export of `9ad36b10`
  (`8806cd7b...`, 19 pins checked). Both exited 0.
- Gates: void no (0 incomplete tables); G1 PASS (190,156 of 190,156 reader requests and 10,230
  of 10,230 judge items identical in tokens and log-prob bits); K2 no (12.4%); K3 no; K4 251
  tables; G2 PASS (322/322, 347/347, hand-check kappa 0.867 [0.767, 0.950] on exactly the
  seeded sample). H2 read; program decision follows.
- H2, retrieved, B = 4, 99%: leave-one-out 0.277 [0.223, 0.333], permutation Shapley-16 0.138
  [0.096, 0.187], SNIPW-64 0.094 [0.058, 0.133], retrieval rank 0.343 [0.271, 0.418], raw
  attention 0.311 [0.235, 0.382]: all MISSPECIFIED. Leave-one-out minus exact Shapley +0.233
  [0.194, 0.273] (LOO_LOSES_MORE_THAN_EXACT_SHAPLEY); exact Shapley 0.044 (95% [0.020, 0.072]; 99% [0.012, 0.080]).
  Program reading: per-memory deletion credit is misspecified for keep/evict decisions on this
  benchmark (this reader, this judge, BM25 user-turn pools, 4 of 8). The second judge gives the
  same five verdicts.
- Secondary: E1 +0.156 [0.119, 0.194] retrieved, +0.094 [0.058, 0.129] gold; AM2 non-gold ABOVE
  THE SWAP FLOOR (+0.0099 [0.0026, 0.0170], driven by the gold arm; not evidence of content
  effects); AM6 cross-fitted heads 0.890 vs best cheap baseline 0.830 (neither AM6 reading
  holds); reorders change 17.1% of answers.
- Disclosures: no gauntlet score (D111); agent hand labels (7 of 8 disagreements on preference
  items); no GPU used by the analysis (GPU-h unchanged, 1.5444 of the 3.1 cap).
- Verified afterwards by a fresh verifier: a new export's `analyze` gave 11 of 11 outputs
  byte-identical, and its own implementation reproduced every H2 verdict, AM2 and the hand-check
  join. Its three low-severity wording corrections are applied in RESULTS.md: claim 2 no longer
  treats E3 paired differences as licensed; no claim about exact Shapley's adequacy; item 8942
  was not among the flagged items, so 6 of 8 disagreements were.
- Evidence: `program/evidence/2026-10-16/am1-confirmatory/RESULTS.md` and `analysis/`.

## 2026-10-15 — G2-RL gauntlet wave 1: score 63 (one review), honest exit on the query budget with the triad stop (branch `gauntlet/g2rl-state-precision`, not merged)

- Candidate: does the GDN recurrent-state precision of RL rollouts (fp32, fp16, bf16) change
  GRPO training of Qwen3.5-4B, and does token-level truncated importance sampling recover it?
  Proposal `program/proposals/2026-10-15-g2rl-state-precision-rl.md` (`10beca2a...`) and DRAFT
  registration `g2rl-state-precision-rl-v1` (`f9a7c9b1...`, not frozen, no ledger row) at
  `6483df8a`: a pilot at learning rate 0 (7.92 cap-GPU-h) that reads the policy-gradient bias of
  bf16-state rollouts against an fp32 A/A floor and the share token-TIS removes, gating a staged
  training comparison of about 640 GPU-h (null path) to 1,150 GPU-h (central estimates).
- Run: workflow `wf_f7b403ad-d82`, budgets queries 150 (30 reserved for the triad),
  wall_minutes 720, tokens 10,000,000, dollars 150, waves 3, gpu_hours 0.5. The orchestrating
  session paused it at 02:06 UTC to free a slot for D110 hosting and resumed it at 02:34 UTC; the
  frontier cell re-ran its retrieval from scratch.
- Review: reviewer 1 (claude-opus-5-5) scored 63; its ten scores sum to 63 and no cap binds
  (74, 79, 89 applied). Reviewer 2 (open-weight) never ran: the host rule allows its lane job only
  on an empty queue, and the D110 hosting jobs (1450-1453) hold the queue until about
  2026-10-17. The score is 63 as an upper bound on the lower of two totals; best 63.
- Blind discrimination: PASS against Ring-linear (2510.19338); the critic judged the proposal
  stronger. KV4-RL (2610.14448), whose Sec. 3 states the proposal's TIS-prefix split, was not in
  the packet.
- Triad: all three refuted. Novelty: a recombination (Ring-linear's lever, KV4-RL's split and
  design template, the FP16 paper's dose-and-length profile), not OCCUPIED. Identification: PR5
  cannot attribute a low TIS recovery to state visitation (continuation advantages, truncation
  scored 0, token-mean normalization and fixed prompts predict the same). Feasibility: the pilot
  decides runnability only, and is over 8 GPU-h under D22 with its own conditional repeats.
- Largest defect: no pilot readout can stop or re-size the full study (G4 cannot fail; kappa and
  r are never gates), the pilot never measures the seed-to-seed SD that decides whether Stage 1
  reads more than INCONCLUSIVE (0.62 under the null at an SD of 2), PR5 cannot attribute what it
  finds, and both P3 jobs exceed their limits at the registration's own high step estimate.
- Doctor at record time: FAIL (Compute and Novelty FAIL), byte-identical to the bundle copy.
- Budgets, recounted from the transcripts: queries 298 of 150 under the program convention
  (orx discover plus GitHub searches, the paused attempt included; 191 without it; 123 counting
  only orx discover and web searches). The bundle under-records the GitHub searches (80, not
  about 51) and omits the asset cell's and the paused attempt's. Tokens 4,249,241 of 10M; $93.75
  of $150 (list-price equivalent); 234.3 of 720 minutes; 0 GPU-h (ledger row added, NOT RUN).
- Exit: the declared query budget under the program convention, with the triad stop (3/3
  refuted). Under the narrowest reading no exit would apply, but a repair wave would take dollars
  to about $155. A fresh repair run needs a decision; admission of the full study is Kevin's
  (D24, D92) whatever any wave scores.
- Audit row 1 of `program/gauntlet/2026-10-15-g2rl-state-precision-rl.jsonl`, row hash
  `dc36ee2497e3023f104d6d3ac8d936456cae444274a50f1d40a4297dcb25dcc9`.

## 2026-10-15 — `am1-keepset-search-v1` (CONFIRMATORY, frozen, ledger row 24; CPU only): H-A INCONCLUSIVE (6 of 7 SEARCH_BETTER), H-C NONABSTAIN_HELPS (+0.112, 39 vs 0); verified

- Drafted from D115, with two independent pre-freeze checks (round 1: one blocker and three
  majors fixed; round 2: the measured bootstrap size was added). H-B was made descriptive (D116).
  Fill `4b89e8eb`, freeze `72d50162`.
- The registered run took 71 s on the host CPU from an export of `72d50162`. All validity checks
  passed: `values_hex` 694 of 694, joins 190,156 of 190,156.
- H-A (retrieved, B = 4, 251 tables): A1-A6 SEARCH_BETTER. Greedy backward at 26 calls is
  NOT_SEPARATED, with upper bound +0.0014, so the verdict is INCONCLUSIVE.
- H-C: nonabstain-BM25 0.571 against BM25 top 4 0.458, +0.112 [0.081, 0.147], 39 against 0,
  p 3.6e-12; median 1 read.
- Descriptive: BM25 top 4 is 0.066 behind all 8, as D116 expected. Nonabstain-BM25 is 0.046
  ahead of all 8 (p 0.033), which is not a test.
- A fresh verifier reproduced the features and outputs byte for byte and recomputed every
  headline number independently.
- Evidence: `program/evidence/2026-10-16/am1-keepset-search/RESULTS.md`.

## 2026-10-15 — `am3-nonabstain-generality-v1` (CONFIRMATORY, frozen, ledger row 25; GPU 0.67 h): H1 NONABSTAIN_HELPS for OLMo-2 and Qwen3.5-9B (hand-confirmed); H2 cost on unanswerable questions 1-8 of 30 (descriptive, judge-qualified); verified

- Process. Drafted from D118, checked three times by independent checkers, filled at
  `78e9c00f` and frozen at `6384f294`.
- Run. Section 16 ran once: build 1475, selftests 1476 and 1477, held-out job 1480, abstention
  job 1482. No rerun was needed.
- Hand labels. Blind, 278 items in 5 chunks, one subagent per chunk with audited transcripts.
  The receipt `417d1149` came before analyze.
- H1 (Qwen3-32B, retrieved arm):
  - OLMo-2: 0.329 to 0.429, 35 against 0;
  - Qwen3.5-9B: 0.464 to 0.553, 31 against 0;
  - the hand labels confirm both (agreement 274 of 278, kappa 0.967);
  - the anchor replays job 1458 token for token and reproduces 39 against 0.
- H2 (30 abstention questions, descriptive, JUDGE_QUALIFIED because G-J2 passed only 26 of 30):
  - cost 5, 8 and 1 of 30 for Qwen3-8B, OLMo-2 and Qwen3.5-9B (hand counts 5, 8 and 0);
  - the net effect at LongMemEval-S's mix stays positive (+0.08 to +0.10);
  - the break-even unanswerable share is 0.27-0.73.
- Verification. A fresh verifier reran analyze, byte-identical; extract digests reproduced;
  its own recomputation was exact.
- Evidence: `program/evidence/2026-10-15/am3-nonabstain-generality-v1/RESULTS.md`.

## 2026-10-15 — AM4 (EXPLORATORY, POST HOC, CPU only): read caps on the non-abstention keep rule

- What it is. A read cap K on the stop rule, with a fallback to BM25 top 4 after K subsets that
  all abstain. It was computed from `am3-nonabstain-generality-v1`'s registered features.
- Reproduction. K = 70 reproduces the registered analysis (243 figures, 0 differences). The
  orchestrator recomputed K = 8 and K = 70 independently from the committed `per-table.json.gz`,
  and both match exactly.
- Shape (retrieved arm, Qwen3-32B judge):
  - At K = 8 the rule keeps 77-84% of the K = 70 gains: 31, 27 and 26 questions against 0, for
    Qwen3-8B, OLMo-2 and Qwen3.5-9B.
  - At K = 8 the cost on unanswerable questions is 3, 3 and 0 of 30 (against 5, 8 and 1 at
    K = 70).
  - Mean reads at K = 8 are 2.7-3.1 on answerable and 6.6-7.5 on unanswerable questions (against
    11-14 and 43-59 at K = 70).
- Status. The caps were examined on the same questions the rule was confirmed on. AM4 is post
  hoc and licenses nothing, and any chosen K needs new questions.
- Evidence: `program/evidence/2026-10-16/am4-read-caps/README.md`.
