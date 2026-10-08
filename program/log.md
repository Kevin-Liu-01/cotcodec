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
