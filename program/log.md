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
