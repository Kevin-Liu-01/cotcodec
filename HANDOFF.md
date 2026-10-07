# Handoff — 2026-10-07

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`). Decisions taken on
Kevin's behalf are D1-D21 in `program/decisions.md`. Results so far:

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1` | Q1 sampling within cap; Q2 replay invalid by a probe-design flaw | `program/evidence/2026-10-07/serving-throughput-probe-v1/` |
| `serving-throughput-probe-v2` | Real vs dummy weights agree on identical prompts; Q2 Stage 1 as designed projects to 431.5 GPU-h (4B and 9B rungs alone 110.6), so it must be rescoped before the gauntlet | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate: projected main job 98.8 min vs a 30-min limit. No verdict; the successor keeps the design with batched engineering (D20) | `program/evidence/2026-10-07/q3-k1/` |

GPU-hours spent by the program are in `program/state.json`
(`gpu_hours_ledger`); 2.15 so far, the Q1 pilot pass (0.899, branch `stage0/q1-gates`) included.

## In progress (branches, not yet merged)

- `stage0/k1-v2`: batched K1 engineering, a synthetic throughput probe and
  draft v2 registrations (D20).
- `stage0/q2-action-path`: VM runtime validated (22 boots, resets pristine);
  remaining suite components being written.
- `stage0/q1-gates`: gates, audit, mutator and substrates integrated; GPU
  smoke and pilot cost card next. Projected Stage 0 total 9-10 GPU-h.
- `stage0/q2-evaluator-mutation`: faithful-save harness, blind specs for 205
  tasks, operator catalog; integration in progress.

## Next actions

1. Freeze and run the K1 throughput probe, then set K1 v2 limits from it.
2. Finish and freeze the action-path suite; run its acceptance trials.
3. Run the Q1 pilot cost card; trim under 8 GPU-h with a registered rule or
   run the gauntlet.
4. Freeze and run the checker-mutation campaign.
5. Rescope Q2 Stage 1 from the measured cost card (more VMs per engine,
   fewer rungs or cells) and take it through the gauntlet.

## Q1 Stage 0 (2026-10-07, branch `stage0/q1-gates`)

The Q1 gate stack, mutator and substrate builders are integrated on
`stage0/q1-gates` (not merged, not pushed). The unified draft
preregistration is `program/preregistrations/q1-stage0-gate-validation.md`;
its section 15 lists the integration decisions and section 16 the fixes made
after the adversarial review (evidence:
`program/evidence/2026-10-07/q1-gates-fix-pass.json`). Do not push
`stage0/q1-gates` until Kevin has seen the gate (b) licence note in
`harness/q1/README.md` (NOTICE).

The pilot pass is done (preregistration sections 17-18, evidence
`program/evidence/2026-10-07/q1-pilot/`): three one-GPU lane jobs (474, 518,
548; 0.899 GPU-h) validated every GPU path on trusted code, the corpus reaches
jobs as one hash-bound study artifact, and the cost card is measured. Stage 0
as drafted projects to about 1,056 GPU-h against the 8 GPU-h cap.

A second adversarial review (of `@04c2934`) found that the pilot scored five
evaluation units and three test mutants before the freeze, and that the
proposed `q1-stage0-trim/1` dropped control kinds, had no criterion-3 margin,
existed only as a projection and under-charged fixed phases. The fix pass
(preregistration sections 18.6-18.7, decisions D26 and D27, evidence
`second-review-fix-pass.json`) registers `q1-stage0-trim/2` as code
(`harness/q1/trim.py`, run by `scripts/run_q1_stage0.py`) with the pilot
exposure handled (exposed mutants out of every frame, sensitivity analysis
without exposed units), contention retries alone, a stop enforced by Slurm job
caps, and a corrected projection: 7.60 GPU-h through bucket P3 and 10.99
through P7 centrally (8.70 and 13.09 at the high point), kept under 8 by the
caps. No GPU was used in the fix pass. Next, in order:

1. Kevin decides the budget path: adopt `q1-stage0-trim/2` (section 18.7;
   mutant metrics on problems below 1 GB only, about 155 witnessed test
   mutants, criterion 3 likely "not met (under-powered)" at about 73 admitted
   units, KBV H.1 and hack-emulating mutant controls not scheduled), or an
   engineering pass that computes references once per problem and draw, then
   a new paired pilot, or the gauntlet, which under D24 cannot reach 100 until
   the trust store exists.
2. Kevin decides the D14 findings (section 18.3, items 6-8): the TF32 `tl.dot`
   threshold, A5's dtype refusals, and the TF32 convolution tolerance above 1.
   Any change is data-motivated under D26: design and validate it on S1-cal
   and non-evaluation kernels only, and name the units it affects.
3. Kevin reviews D26 (pilot exposure) and D27 (upstream test code on GPUs).
4. Then fold the chosen rule into sections 3-10, build the Stage 0 corpus
   (admission, specializations, compile filter, cap) and its study artifact,
   record the plan hash with `scripts/run_q1_stage0.py --plan-only`, check
   `python scripts/q1_version_card.py --markdown` against section 2.1 and
   freeze (`scripts/preregister.py freeze ...`).
5. Rebuild `cotcodec-q1-gates` at the frozen revision (CPU-only build job from
   a fresh clone) and run Stage 0 jobs from
   `experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml`, one at a
   time, each with spent + cap + reserve at most 8 GPU-h.

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`: the R580 driver
upgrade or written risk acceptance (Q1 Stage 1 scoring), outward disclosures
(Letta, OSWorld checker defects and an exposed API key), licences for the Q1
policy, a git-history purge, rotating the Moonshot key, and a human spot check
of the model-rated mutation audit.

Also for Q1: the Stage 0 budget decision (`q1-stage0-trim/2`, an engineering
pass, or the gauntlet, blocked under D24), the three open audit findings
(section 18.3, items 6-8), decisions D26 and D27, then review and freeze the
integrated Q1 Stage 0 preregistration (`stage0/q1-gates`); see the gate (b)
licence note before it is pushed.

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones under `~/cotcodec-runs/stage0/`.
