# FieldTheory Possibility Runs — 2026-08-10

FieldTheory searched Kevin's local cache of 1,823 X bookmarks across four seeds
and applied each seed to this repository. All four jobs completed with four
independently generated and critiqued ideas. Scores are FieldTheory heuristics,
not experimental evidence.

## Runs

| Seed | Job / run | Frame | Highest-scored useful result |
|---|---|---|---|
| Portable architectures | `job-msnmkmhm-50c287` / `adj-msnmkmll-025b70` | Novelty × feasibility | Failure Mutation Canary Forge, 79 × 69 |
| Research harnesses | `job-msnmkmkz-c6c280` / `adj-msnmkmpe-667fa7` | Leverage × specificity | Executable Agent Loop Spine, 96 × 89 |
| Cloud and bare metal | `job-msnmkmon-58cc5a` / `adj-msnmkmt0-c58f79` | Impact × effort | Portable Agent Loop Spine, 94 × 25 |
| Graphs and memory | `job-msnmkmsf-4439d6` / `adj-msnmkmwt-437b2b` | Novelty × feasibility | Typed Context Portfolio, 66 × 46 |

## Promoted findings

1. **Executable Agent Loop Spine.** Replace `harness/runner.py`'s stub with one
   bounded, injectable model/tool loop that emits complete traces. This is the
   prerequisite for every empirical claim in the repo.
2. **Executable Canary Fixtures.** Give every canary deterministic tool state,
   expected arguments, forbidden actions, and category-specific machine
   oracles. Do not ask the model to grade its own behavior.
3. **Paired Regression Gate.** Join baseline and intervention on experiment,
   benchmark, model, task, and seed; fail closed on missing or duplicate pairs;
   predeclare safety/correctness thresholds.
4. **Crash-safe experiment queue.** Use stable job IDs and atomic pending,
   leased, completed, and dead-letter states so retries cannot duplicate traces
   or spend.
5. **Typed context receipts.** Record provenance, trust, token cost, accepted
   and rejected candidates, then estimate value with matched omission tests.

## Useful negative findings

- The architecture bookmark seed produced harness ideas rather than a new model
  mechanism because FieldTheory grounds possibilities in the active repository.
  It is evidence about project readiness, not evidence that architecture space
  is exhausted.
- Commit-authority memory scored only 14 for novelty because MemTX already
  occupies staged commit, validation, provenance, retraction, and repair.
- Replay-validity and loop-vs-graph experiments are scientifically interesting
  but blocked by the missing executable loop and deterministic environments.
- A local-versus-managed TCO frontier is worth measuring only inside matched
  quality and service-level bands; a raw dollar comparison would be misleading.

## Decision

FieldTheory changes execution order, not the ranked architecture portfolio:
build the loop spine, canary oracles, paired regression gate, and scheduler
contract before expensive architecture runs. Portable Update Dynamics and
Coded Delta Memory still come from the primary-source collision scan and must
pass separate novelty audits.
