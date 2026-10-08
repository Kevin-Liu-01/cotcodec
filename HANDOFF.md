# Handoff — 2026-10-07 (evening)

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 7 rows). Decisions taken on
Kevin's behalf are D1-D34 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`): 2.44 on main; 2.77 on branch
`stage0/q1-engineering-d31` (main merged in, plus the Q1 re-pilot's 0.33);
the checker-mutation rater's 0.13 (branch `stage0/q2-evaluator-mutation`) and
the Q3 dense pre-check lanes (`ops/q3-dense`) are not yet merged.

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1` | Q1 sampling within cap; Q2 replay invalid by a probe-design flaw | `program/evidence/2026-10-07/serving-throughput-probe-v1/` |
| `serving-throughput-probe-v2` | Real vs dummy weights agree; Q2 Stage 1 as designed projects to 431.5 GPU-h, so it must be rescoped before the gauntlet | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate (projected 98.8 min vs a 30-min limit); no verdict | `program/evidence/2026-10-07/q3-k1/` |
| `q3-k1-throughput-probe-v1` | K1 v2 limits derived; K1 v2 then ended at an honest gauntlet exit (score 45, D26) | `program/evidence/2026-10-07/q3-k1-v2/` |
| `q3-dense-headroom-precheck-v1` | Frozen 2026-10-08 03:29 UTC (D32); being operated | `program/evidence/2026-10-08/q3-dense-headroom-precheck/` (branch `ops/q3-dense`) |

## In progress

- **Q3 dense pre-check** (`ops/q3-dense`): image from `a369e6d`, CPU doctor
  in the image, the 0.6B lane (cap 0.15 GPU-h), the 4B lane only if the 0.6B
  receipt reproduces K1 smoke 452 (cap 0.35), then the combined read, which
  says whether a K1 v3 can register a NEGATIVE, on which base, and with which
  controls. Any K1 v3 takes a new id and the gauntlet.
- **Q2 action path** (`stage0/q2-action-path-d30`): D30 (A4 restart exclusion,
  A7 observation-service bound, scoped probe and tap), D33 (the exclusion
  extends to A1-A3 and the ladder within per-entry and per-rung limits, A7
  call cap) and the fixes after their reviews are done in `acceptance.py` and
  the text (main preregistration sections 18-22). D39 (C3 equivalence fails
  closed over earlier attempts, an unparseable record file reads as missing,
  frozen status lines) is being applied. Then merge, freeze v1, `-inputs`,
  `-executor`, and run the CPU-only acceptance campaigns (98.4 VM-hours; the
  ladder needs a quiet host).
- **Q2 checker mutation** (`stage0/q2-evaluator-mutation`): D27's kappa rule
  fired (dev kappa 0.27 with Qwen3.6-35B-A3B, thinking off). Fix 5 under D34:
  gold shams per task, concordant contradictions to adjudication, packet text
  diffs, a registered prompt template and transcript audit tied to items, a
  secret id salt, and one thinking-on rerate. If dev kappa stays below 0.6,
  P2-P5 leave the confirmatory headline and no other rater is tried.
- **Q1 Stage 0** (`stage0/q1-engineering-d31`): not admitted under D31; waits
  on the gauntlet (D24) or Kevin. The D31 review's fix pass is done (section
  18.9, no GPU): memory-aware execution `q1-stage0-exec/2`, a health check that
  never retires a slot on contention, gate (a) out of the reference store, a
  tighter store. Under the safe execution the projection through P3 is 10.46
  GPU-h central and 12.31 high without the store (model-based). Not merged,
  not pushed, not frozen.
- **Q2 Stage 1**: must be rescoped from the serving cost card and the Stage 0
  results, then go through the gauntlet.

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`. The ones that
block work: the gauntlet trust store or an admission ruling (D24: blocks Q1
Stage 0, Q2 Stage 1 and any K1 v3), the R580 driver upgrade or written risk
acceptance (Q1 Stage 1 scoring), adjudication of the checker-mutation pool
and the human spot check (D9), and review of D28-D34. Outward actions
(disclosures to Letta and xlang-ai, licence requests, a history purge, key
rotation) stay his.

## Q1 Stage 0 (2026-10-07, branches `stage0/q1-gates` and `stage0/q1-engineering-d31`)

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
(preregistration sections 18.6-18.7, decisions D28 and D29, evidence
`second-review-fix-pass.json`) registers `q1-stage0-trim/2` as code
(`harness/q1/trim.py`, run by `scripts/run_q1_stage0.py`) with the pilot
exposure handled (exposed mutants out of every frame, sensitivity analysis
without exposed units), contention retries alone, a stop enforced by Slurm job
caps, and a corrected projection: 7.60 GPU-h through bucket P3 and 10.99
through P7 centrally (8.70 and 13.09 at the high point), kept under 8 by the
caps. No GPU was used in the fix pass. Next, in order:

1. Kevin decides the budget path. The engineering pass of D31 is done
   (branch `stage0/q1-engineering-d31`, preregistration section 18.8, evidence
   `program/evidence/2026-10-07/q1-engineering-d31/`): a reference store
   computes references once per problem, replicate and draw with identical
   verdict rows (CPU tests; a differential against main; on the GPU every twin
   difference is explained and none is the store's), and the non-evaluation
   re-pilot (Slurm 713, 0.330 GPU-h) measured it. The store saves where
   references are expensive (gate c 42%, A1 25%, A2 17%) but its reference
   items cost about as much at in-scope sizes, so `q1-stage0-trim/2`'s high
   estimate through P3 is 8.81-9.85 GPU-h with it, 9.03 without, and 8.56 at
   the references-free bound (post hoc ratio): **Stage 0 is not admitted under
   D31.** The D31 review then found the 12-per-GPU execution unsafe (97 items
   out of GPU memory, 93 never final, 5 of 12 slots retired; A5 dropped the
   out-of-memory text; failed reference items left permanent unusable
   entries), the projection built on a size model the re-pilot contradicts
   (x1.72), and the store's equivalence overstated. Its fix pass (section 18.9,
   evidence `.../q1-engineering-d31/fixpass/`, no GPU) registers
   `q1-stage0-exec/2` (units from each item's estimated or measured peak GPU
   memory, a free-memory guard, a health check that drains the GPU and repeats
   alone before anything is retired), one resource-failure list, gate (a) out
   of the store, raised references unusable, no entry after a resource
   failure, input fingerprints, a replay of skipped reference forwards, and
   disk caps. Under `q1-stage0-exec/2` the model-based projection through P3 is
   10.46 GPU-h central and 12.31 high without the store (11.10 high at the
   references-free bound): still not admitted. The remaining paths are the
   gauntlet (D24), a scope reduction that acts on P1-P3 (a 30-per-family test
   quota still projects 9.10 central, 10.51 high), or a new engineering pass
   beyond D31. Before any Stage 0 job, Kevin signs off `q1-stage0-exec/2` and
   the store policy, and a re-measurement under it replaces the model.
2. Kevin decides the D14 findings (section 18.3, items 6-8): the TF32 `tl.dot`
   threshold, A5's dtype refusals, and the TF32 convolution tolerance above 1.
   Any change is data-motivated under D28: design and validate it on S1-cal
   and non-evaluation kernels only, and name the units it affects.
3. Kevin reviews D28 (pilot exposure) and D29 (upstream test code on GPUs).
4. Then fold the chosen rule into sections 3-10, build the Stage 0 corpus
   (admission, specializations, compile filter, cap) and its study artifact,
   record the plan hash with `scripts/run_q1_stage0.py --plan-only`, check
   `python scripts/q1_version_card.py --markdown` against section 2.1 and
   freeze (`scripts/preregister.py freeze ...`).
5. Rebuild `cotcodec-q1-gates` at the frozen revision (CPU-only build job from
   a fresh clone) and run Stage 0 jobs from
   `experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml`, one at a
   time, each with spent + cap + reserve at most 8 GPU-h.

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones under `~/cotcodec-runs/stage0/`.
