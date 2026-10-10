# Handoff — 2026-10-10 (saved 01:50 UTC)

## Resume here (saved 2026-10-10 01:50 UTC)

- **On the host, unattended:** S1a's session-2 9B pair, VM job 1051 (Slurm
  begin 12:50 UTC 2026-10-10, D57) and GPU job 1053 (`after:1051`), about 75
  minutes. Session-2 4B is not submitted: its manifest must name 9B's records.
  Next, in order: collect 1051/1053 and check DR0, submit S2 4B, collect it,
  then the registered analysis with two independent verifiers (recompute;
  claims). Submit nothing else while an S1a job runs (quiet host).
- **Interrupted if the session ends:** a blind dry run of the frozen S1a
  analysis on synthetic records (writes nothing to the repository), and E4's
  gauntlet wave 1 (four discovery cells finished; the synthesis owner works on
  branch `gauntlet/e4-d19`, nothing committed yet). Relaunch both from their
  saved scripts with a resume note; the E4 reviewer's lane job must not overlap
  an S1a job.
- The operator's workflow scripts and a runbook with local paths are archived
  privately (outside this repository).

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 16 rows). Decisions taken
on Kevin's behalf are D1-D60 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`, physical hours): 7.34 in total.

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1`, `-v2` | Real vs dummy weights agree; Q2 Stage 1 as designed projects to 431.5 GPU-h | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate; no verdict | `program/evidence/2026-10-07/q3-k1/` |
| `q3-dense-headroom-precheck-v1` | INCOMPLETE (null job id in receipts; 4B lane CPU-bound) | `program/evidence/2026-10-08/q3-dense-headroom-precheck/` |
| `q3-dense-headroom-precheck-v2` | **NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base** (H1_CX 42.15, 99% 35.8-48.2); 0.6B reproduces v1 exactly and stays NOT_VIABLE; seven requirements for any K1 v3 | `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/` |
| `q2-action-path-v1` (+ addenda) | Invalid on C2: `chord_super_d` failed under raw PyAutoGUI; the cause is the tap's record of key events queued during GNOME Shell's synchronous grab, not delivery (D43) | `program/evidence/2026-10-08/q2-action-path-acceptance/` |
| `q2-action-path-v2` (+ addenda) | **ACCEPTED on attempt 1** (D53): C1-C4, A1-A7 pass, independently verified in two stages; N* = 32 (rung 40 hit the host's inotify limit), so the program kill criterion applies; a whole-boot `/accessibility` failure without restart (1 of 1,245 boots) is outside every criterion | `program/evidence/2026-10-08/q2-action-path-v2-acceptance/` |
| `q2-evaluator-mutation-v1` | Descriptive (D35): `compare_pptx_files` fails 35 of 36 equivalent shape-order edits (30 confirmed by both raters; family FN share 40.2%); a GUI-faithful save flips 3 of 92 reference golds (confirmed); false positives few; kappa 0.34; adjudication pending | `program/evidence/2026-10-08/q2-mutation-confirm/` |

Gauntlet records: K1 v2 (45, honest exit), K1 v3 (51, 55, 56; honest exit, D54), Q1 Stage 0 (45, honest exit).
Q1 Stage 0 is closed on the audit-metric study (D46): under TF32 a tolerance
audit certifies "not grossly wrong", not 1% correctness
(`program/evidence/2026-10-08/q1-audit-metric-study/`).

## In progress

- **Q2 S1a** (`q2-stage1-rescoped-v1`, D47, D49, D53, D55, D56): **frozen**
  2026-10-09 as ledger row 16 (freeze commit `d5f5798`). Pre-freeze O1 and A0a
  ran (A0a: 20 of 20 dev episodes, mean slot 220 s against the card's 743 s;
  K_base 32, T_A1 110 min, caps 477 min = 7.95 GPU-h). Kevin signed item 17 (DR1
  and DR5 replace the kill lines; S1a read unanchored) and the offline-setup
  exclusions (D55); D56 signed the rest and accepted S1a's reading of D53 (iii).
  O2 (job 1044) and A1 session 1 ran on 2026-10-09/10: 9B (1045/1047) and 4B
  (1048/1050), 452 of 452 episodes scored each, no infrastructure loss, DR0 did
  not fire, independently verified (D57 records two disclosures). Session 2's
  9B pair (1051/1053) is held by Slurm until 12:50 UTC 2026-10-10; 4B follows
  once 9B's records exist; then the registered analysis (a blind dry run on
  synthetic records checks the frozen analysis code meanwhile).
- **Backfill E4** (D19, distilled in-context write rule; D58, D60): gauntlet
  wave 1 scored 49 (honest exit: triad 3/3 refuted, query budget overrun;
  identification is the largest defect). D60 allows one fresh repair run;
  below 60, or identification still the largest defect, ends E4.
- **S1a analysis** (D59): a blind dry run found 11 defects in the frozen
  analysis code (a fractional base score crashes the report; incomplete data
  crash or mislead; serial rescoring; missing section 15 items). D59 fixes
  their handling before any outcome is read: a wrapper, incomplete-data rules
  and operator steps, built under `ops/s1a-analysis/`.
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
before their sign-off, review of D1-D60, the host inotify limit behind N* = 32, and the outward actions (disclosures
to Letta and xlang-ai, now including the `compare_pptx_files` finding; licence
requests; a history purge; key rotation; a valid Anthropic API key).

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones or exports under `~/cotcodec-runs/`.
