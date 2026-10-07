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
(`gpu_hours_ledger`); about 1.2 so far.

## In progress (branches, not yet merged)

- `stage0/k1-v2`: batched K1 engineering, a synthetic throughput probe and
  draft v2 registrations (D20).
- `stage0/q2-action-path`: VM runtime validated (22 boots, resets pristine);
  remaining suite components being written.
- `stage0/q1-gates`: gates, audit, mutator and substrates integrated; GPU
  smoke and pilot cost card next. Projected Stage 0 total 9-10 GPU-h.
- `stage0/q2-evaluator-mutation`: faithful-save harness, blind specs for 205
  tasks, operator catalog; integration in progress.
- `stage0/q3-dense-precheck`: draft `q3-dense-headroom-precheck-v1` (D26),
  dense only on the K1 bundle's development partition, Qwen3-0.6B-Base and
  Qwen3.5-4B-Base, caps 0.15 + 0.35 GPU-h; code, lane templates and CPU doctor
  (PASS in the image). Waits on Kevin's acceptance of its design decisions,
  then freeze, image, doctor, two lane jobs and the combined read.

## Next actions

1. Freeze and run the K1 throughput probe, then set K1 v2 limits from it.
2. Finish and freeze the action-path suite; run its acceptance trials.
3. Run the Q1 pilot cost card; trim under 8 GPU-h with a registered rule or
   run the gauntlet.
4. Freeze and run the checker-mutation campaign.
5. Rescope Q2 Stage 1 from the measured cost card (more VMs per engine,
   fewer rungs or cells) and take it through the gauntlet.

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`: the R580 driver
upgrade or written risk acceptance (Q1 Stage 1 scoring), outward disclosures
(Letta, OSWorld checker defects and an exposed API key), licences for the Q1
policy, a git-history purge, rotating the Moonshot key, and a human spot check
of the model-rated mutation audit.

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones under `~/cotcodec-runs/stage0/`.
