# Handoff — 2026-10-10 (evening)

## Resume here (2026-10-10 evening)

- S1a is complete and verified (D66): no harness difference detected, DR5
  INCONCLUSIVE, so no S1b. The host is idle.
- Running: a CPU-only design study on S1a's records. It compares successor
  designs within 8 GPU-h and sizes S2's power gate, on branch
  `stage0/q2-design-study`, and its recommendation decides Q2's next step.
  If the session ends, relaunch it from its saved script (archived privately);
  it writes nothing outside its branch.
- Backfill is paused (D65). E4 and C3 ended at honest exits (D63, D65), and
  C5 waits for a D24 ruling.

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 16 rows). Decisions taken
on Kevin's behalf are D1-D66 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`, physical hours): 9.80 in total.

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1`, `-v2` | Real vs dummy weights agree; Q2 Stage 1 as designed projects to 431.5 GPU-h | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate; no verdict | `program/evidence/2026-10-07/q3-k1/` |
| `q3-dense-headroom-precheck-v1` | INCOMPLETE (null job id in receipts; 4B lane CPU-bound) | `program/evidence/2026-10-08/q3-dense-headroom-precheck/` |
| `q3-dense-headroom-precheck-v2` | **NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base** (H1_CX 42.15, 99% 35.8-48.2); 0.6B reproduces v1 exactly and stays NOT_VIABLE; seven requirements for any K1 v3 | `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/` |
| `q2-action-path-v1` (+ addenda) | Invalid on C2: `chord_super_d` failed under raw PyAutoGUI; the cause is the tap's record of key events queued during GNOME Shell's synchronous grab, not delivery (D43) | `program/evidence/2026-10-08/q2-action-path-acceptance/` |
| `q2-action-path-v2` (+ addenda) | **ACCEPTED on attempt 1** (D53): C1-C4, A1-A7 pass, independently verified in two stages; N* = 32 (rung 40 hit the host's inotify limit), so the program kill criterion applies; a whole-boot `/accessibility` failure without restart (1 of 1,245 boots) is outside every criterion | `program/evidence/2026-10-08/q2-action-path-v2-acceptance/` |
| `q2-stage1-rescoped-v1` (S1a) | **DR2 Inconclusive** (pooled δ −3.1 pp, 90% [−8.9, +2.7]); **DR5 INCONCLUSIVE** (π_small 0.055, [0, 0.26] vs M 0.13), so no S1b; P1 falsified (no between-session excess, upper bound 0.78 pp); 1,808 episodes, 0 infrastructure losses; realized cost 0.22-0.24 of the card's high price; not externally anchored; independently verified (D66) | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` |
| `q2-evaluator-mutation-v1` | Descriptive (D35): `compare_pptx_files` fails 35 of 36 equivalent shape-order edits (30 confirmed by both raters; family FN share 40.2%); a GUI-faithful save flips 3 of 92 reference golds (confirmed); false positives few; kappa 0.34; adjudication pending | `program/evidence/2026-10-08/q2-mutation-confirm/` |

Gauntlet records: K1 v2 (45, honest exit), K1 v3 (51, 55, 56; honest exit, D54), Q1 Stage 0 (45, honest exit).
Q1 Stage 0 is closed on the audit-metric study (D46): under TF32 a tolerance
audit certifies "not grossly wrong", not 1% correctness
(`program/evidence/2026-10-08/q1-audit-metric-study/`).

## In progress

- **Q2 next step** (D66): S1a is done (above). A CPU design study calibrated on
  S1a's records compares successor designs within 8 GPU-h (more sessions, more
  tasks, mixed) for decisive DR2/DR5, and sizes S2's power gate with S1a's
  noise floor.
- **Q3**: the dense pre-check v2 result (NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base)
  is Q3's Stage 0 outcome. K1 v3 ended at an honest exit after its third
  gauntlet wave (D54; 45, 51, 55, 56): its chance of any verdict stayed at
  0.03-0.25 and GO is not identified against question-side literal priming.
- **Q1**: Stage 0 closed on the audit-metric study (D46).

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`: the gauntlet trust
store or an admission ruling (D24: blocks anything over 8 GPU-h, including a K1
v3 and Q2 Stage 1), the checker-mutation adjudication (34 items) and spot check
(25 items), the R580 driver and a licensed policy (Q1), the specs published
before their sign-off, review of D1-D66, the host inotify limit behind N* = 32, and the outward actions (disclosures
to Letta and xlang-ai, now including the `compare_pptx_files` finding; licence
requests; a history purge; key rotation; a valid Anthropic API key).

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones or exports under `~/cotcodec-runs/`.
