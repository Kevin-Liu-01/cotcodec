# Handoff — 2026-10-08

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 10 rows). Decisions taken
on Kevin's behalf are D1-D41 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`, physical hours): 3.35 on main, plus
the checker-mutation dev raters' 0.57 on branch `stage0/q2-evaluator-mutation`.

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1` | Q1 sampling within cap; Q2 replay invalid by a probe-design flaw | `program/evidence/2026-10-07/serving-throughput-probe-v1/` |
| `serving-throughput-probe-v2` | Real vs dummy weights agree; Q2 Stage 1 as designed projects to 431.5 GPU-h, so it must be rescoped before the gauntlet | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate; no verdict | `program/evidence/2026-10-07/q3-k1/` |
| `q3-k1-throughput-probe-v1` | K1 v2 limits derived; K1 v2 then ended at an honest gauntlet exit (score 45, D26) | `program/evidence/2026-10-07/q3-k1-v2/` |
| `q3-dense-headroom-precheck-v1` | INCOMPLETE, no combined read: receipts carry a null Slurm job id the summariser rejects, and the 4B lane ran CPU-bound and ignored SIGUSR1. The 0.6B lane is valid (smoke 452 reproduced; NOT_VIABLE, H1_CX 12.25, H2 FAIL) | `program/evidence/2026-10-08/q3-dense-headroom-precheck/` |
| `q2-action-path-v1` (+ `-inputs`, `-executor`) | Invalid on its validity control C2 (job 768): `chord_super_d` failed 5/5 under raw PyAutoGUI, predicted to pass; the press-state loss is real at the X event level, so the miss is in the prediction | `program/evidence/2026-10-08/q2-action-path-acceptance/` |

Gauntlet records: K1 v2 (score 45, honest exit) and Q1 Stage 0
(`program/gauntlet/2026-10-08-q1-stage0-gate-validation.jsonl`, score 45,
honest exit: all three refuters refuted, query budget spent).

## In progress

- **Q3** (D36): `q3-dense-headroom-precheck-v2` on `stage0/q3-dense-v2`, same
  design; receipts bound to their job, SIGUSR1 honoured on the 4B path, the CPU
  bottleneck removed without changing results (gated by reproducing v1 job 727
  to 1e-6), the 4B lane sized from a timing job of at most 0.1 GPU-h; cap 1.5
  GPU-h. Then review, freeze and operate.
- **Q2 action path** (D40): `q2-action-path-v2` (+ `-inputs`, `-executor`)
  is drafted on `stage0/q2-action-path-v2` and freeze-linted in order against
  a scratch ledger; not frozen. It keeps v1 except that the L0-raw prediction
  lists `chord_super_d` as a failure, disclosed as informed by v1's C2, so
  v2's C2 is a reproduction test on its own seed (45); and the renderer takes
  `--host-root`. Seed-42 development (jobs 784-787, 1.0 VM-h; v2 section 26)
  shows v1's C2 failure is in the tap's record, not in delivery: GNOME Shell
  grabs Super_L synchronously, the next key is queued and RECORD reports it
  with state 0, while the shell still shows the desktop. L0-fixed (10 ms
  between presses) passed `chord_super_d` 127/127 with the warm-up. Whether
  the oracle should read such events differently is with Kevin. Then review,
  merge, freeze, and run C2, C1, C3, A1-A6, the ladder on a quiet host (no
  other Slurm job may start during a rung), A4 and A7 (about 98 VM-hours,
  CPU only).
- **Q2 checker mutation** (D34, D35, D38): the study is now a descriptive
  protocol (development kappa 0.066 registered, 0.575 relay-excepted, below
  0.6, so P2-P5 left the confirmatory headline). Ninth draft re-checked at 90;
  a final tidy is running, then merge and freeze. Its confirm campaign needs
  Kevin's adjudication of the pool (about 16 items) and the human spot check
  (about 35 items, D9).
- **Q1** (D41): Stage 0 as drafted is withdrawn. The registered audit metric
  cannot separate a correct TF32 matmul or convolution from a destroyed output
  on most L2 problems, and Stage 0 projects to 20-25 GPU-h at the high point.
  A CPU-only study of the audit metric on stored non-evaluation data is
  running (`stage0/q1-audit-metric`). Stage 1 still needs the R580 driver.
- **Q2 Stage 1**: must be rescoped from the serving cost card and the Stage 0
  results, then go through the gauntlet.

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`: the gauntlet trust
store or an admission ruling (D24: blocks any experiment over 8 GPU-h), the
R580 driver upgrade or written risk acceptance (Q1 Stage 1), the
checker-mutation adjudication and spot check, review of the decisions taken on
his behalf (D1-D41), and the outward actions (disclosures to Letta and
xlang-ai, licence requests, a history purge, key rotation, a valid Anthropic
API key).

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones or exports under `~/cotcodec-runs/`.
