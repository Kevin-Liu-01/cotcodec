# Handoff — 2026-10-07 (evening)

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 7 rows). Decisions taken on
Kevin's behalf are D1-D34 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`): 2.44 on main, plus 0.33 (Q1
re-pilot, branch `stage0/q1-engineering-d31`) and 0.13 (checker-mutation
rater, branch `stage0/q2-evaluator-mutation`) not yet merged.

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
  A7 observation-service bound, scoped probe and tap) and the review fixes are
  done; D33 (the exclusion extends to A1-A3 and the ladder, A7 call cap) is
  being applied. Then merge, freeze v1, `-inputs`, `-executor`, and run the
  CPU-only acceptance campaigns (98.4 VM-hours; the ladder needs a quiet host).
- **Q2 checker mutation** (`stage0/q2-evaluator-mutation`): D27's kappa rule
  fired (dev kappa 0.27 with Qwen3.6-35B-A3B, thinking off). Fix 5 under D34:
  gold shams per task, concordant contradictions to adjudication, packet text
  diffs, a registered prompt template and transcript audit tied to items, a
  secret id salt, and one thinking-on rerate. If dev kappa stays below 0.6,
  P2-P5 leave the confirmatory headline and no other rater is tried.
- **Q1 Stage 0** (`stage0/q1-engineering-d31`): the reference store gives the
  same verdicts but saves little; the high projection is 8.56-9.66 GPU-h, so
  under D31 Stage 0 is not admitted and waits on the gauntlet (D24). The
  re-pilot also found out-of-memory failures at 12 items per GPU and a health
  check that retires healthy slots under contention; both need fixing before
  any Stage 0 job. A review and fix pass is running.
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

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones under `~/cotcodec-runs/stage0/`.
