# Handoff — 2026-10-11

## Resume here (2026-10-11)

- 2026-10-14: public history was rewritten (D99); commit ids from 2026-08-17 on changed.
  Resolve any recorded id with `scripts/verify_history_map.py resolve
  program/history-rewrite-2026-10-14/commit-map.tsv <id>`. Pre-purge clones cannot
  fast-forward: re-clone. S2 v5 merges main and freezes next (D98).

Kevin delegated his pending research decisions on 2026-10-11 ("do it yourself
for whatever gains actual results"; D80). Under that delegation:
- R04 is done (row 18; D89). OSWorld's office checkers are not invariant:
  - LibreOffice 25.8 and 26.2 flip about 20% of the 92 golds (mostly
    `compare_pptx_files`). Builds up to 24.8 flip none.
  - The de_DE, ar_EG and tr_TR locales flip three `compare_table` golds.
  - Every flip reproduced in two confirmation rounds.
  Evidence: `program/evidence/2026-10-12/r04-nuisance-confirm/`.
- The checker-mutation adjudication is complete (D81, D82), adjudicated by an
  isolated model and not human-validated. The first run was void (D81).
  Run 2 passed the registered isolation audit (52 `ok`). The parent analysis,
  rerun with `--adjudications` and `--k2-report`, gives:
  - 33 confirmed false negatives (11.6%; `compare_pptx_files` 37.1%, z-order
    85.4%);
  - 3 gold-defect tasks;
  - P2 at 12.4% on 337;
  - K4 no longer fires.
  R03, the checker-mutation note, can now be finished.
- R03, the checker-mutation note, is drafted and verified, and not published
  (D83; `paper/checker-mutation-note/`). The Q2 report is at revision 6 (successor E included).
- R03 part (b) is done (row 20; D86, D88). On the held-out reserve split,
  zinv's result is PASS, descriptive: it accepts 13 of 13 z-order equivalence
  mutants on 8 tasks and newly accepts none of 15 violation mutants. The
  original `compare_pptx_files` rejects all 13, so the defect replicates on
  held-out tasks. Evidence: `program/evidence/2026-10-12/q2-zinv-reserve-run/`.
- Successor E session E1 is done (jobs 1219/1221 and 1222/1224, ending
  05:46Z on 2026-10-12). E2 starts no earlier than about 17:51Z.
- Successor E is frozen (row 19; sign-off D85; freeze `f6144d6b`). Its four
  sessions (about 42 h, 6.77 cap-GPU-h) are running on `ops/q2-successor-e`.
  Other host work runs only in its gaps.
- S2 is given up (D103): v5 (row 22) was stopped during Phase 0 K1 by Kevin's
  decision, with no result. L1 (D102) was dropped during discovery.
- **New directions (D103):** agent-memory causality, and GPU memory and
  acceleration for inference and RL.
  - The sweep (D104) picked **G2** as the lead: the train-inference mismatch
    of GDN hybrids (Qwen3.5) by token position, vLLM vs HF+FLA, about 3 GPU-h.
    Its exploratory pilot has run (0.44 GPU-h; `stage0/g2-pilot`, corrected
    after an independent check, not merged): at 4B up to 11.5K the raw rise
    follows token entropy, and at fixed entropy the mismatch falls slightly.
    See `program/evidence/2026-10-14/g2-pilot/README.md`.
  - **AM1** is the memory lead: exact credit tables for agent memory on
    LongMemEval.
  - The exploratory inference baseline is done (D105). Dense models are
    KV-starved, and the hybrids' fp32 GDN state caps concurrency.
  - **G2b (D108):** bf16 GDN state gives 1.33-1.38x throughput, but makes
    rollouts about 5x more off-policy, growing with length, and longer.
    **G2c (D109):** the number format drives the drift, not the layout. fp16
    state keeps the 1.3-1.4x throughput at about 2x fp32's off-policy gap.
  - AM1 step 0 (D107): bit-exact reader replay works; exact credit tables are
    cheap.
- The public-history purge ran (D99). Old commit ids resolve through
  `program/history-rewrite-2026-10-14/` (the map plus an 11-row supplement,
  D100). No GitHub Support request (D101).
- Outward items (disclosures, licence, host admin, publication) are shelved
  by Kevin (D101). They do not gate research and are not raised again.
- The R03 note and the Q2 report (revision 5) now include R03 (b) and R04.
Still closed: Q1 (D46) and Q3 (D54). Still Kevin's: the outward actions, Q1's
R570 GPU code and C5 Phase 1 (D80), and an optional human spot check (D9).
See `pending_decisions_for_kevin` in `program/state.json`.

## State

The restarted program is in Stage 0. Everything runs through frozen
preregistrations in `program/preregistrations/ledger.jsonl` (hash-chained;
`uv run python scripts/preregister.py check-chain`, 22 rows). Decisions taken
on Kevin's behalf are D1-D109 in `program/decisions.md`. GPU-hours are in
`program/state.json` (`gpu_hours_ledger`, physical hours): 10.37 in total.

| Registration | Outcome | Evidence |
|---|---|---|
| `q2-holo3-rerun-audit-v2` | Confirmatory: the two same-day Holo3 maintainer runs differ by a session shift not explained by time-dependent checkers, step-count behaviour or visible environment failures | `program/evidence/2026-10-07/holo3-v2/RESULTS.md` |
| `serving-throughput-probe-v1`, `-v2` | Real vs dummy weights agree; Q2 Stage 1 as designed projects to 431.5 GPU-h | `program/evidence/2026-10-07/serving-throughput-probe-v2/` |
| `q3-k1-localization-screen-v1` | Stopped at its smoke gate; no verdict | `program/evidence/2026-10-07/q3-k1/` |
| `q3-dense-headroom-precheck-v1` | INCOMPLETE (null job id in receipts; 4B lane CPU-bound) | `program/evidence/2026-10-08/q3-dense-headroom-precheck/` |
| `q3-dense-headroom-precheck-v2` | **NEGATIVE_CAPABLE_V3 on Qwen3.5-4B-Base** (H1_CX 42.15, 99% 35.8-48.2); 0.6B reproduces v1 exactly and stays NOT_VIABLE; seven requirements for any K1 v3 | `program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/` |
| `q2-action-path-v1` (+ addenda) | Invalid on C2: `chord_super_d` failed under raw PyAutoGUI; the cause is the tap's record of key events queued during GNOME Shell's synchronous grab, not delivery (D43) | `program/evidence/2026-10-08/q2-action-path-acceptance/` |
| `q2-action-path-v2` (+ addenda) | **ACCEPTED on attempt 1** (D53): C1-C4, A1-A7 pass, independently verified in two stages; N* = 32 (rung 40 hit the host's inotify limit), so the program kill criterion applies; a whole-boot `/accessibility` failure without restart (1 of 1,245 boots) is outside every criterion | `program/evidence/2026-10-08/q2-action-path-v2-acceptance/` |
| `q2-stage1-rescoped-v1` (S1a) | **DR2 Inconclusive** (pooled δ, H-GA minus H-OSW-fixed, −3.1 pp, 90% [−8.9, +2.7]); **DR5 INCONCLUSIVE** (π_small 0.055, [0, 0.26] vs M 0.13), so no S1b; P1 falsified (no between-session excess, upper bound 0.78 pp); 1,808 episodes, 0 infrastructure losses; realized cost 0.22-0.24 of the card's high price; not externally anchored; recomputed from the raw records and claims-checked by two fresh lenses (D66, D72) | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` |
| `q2-evaluator-mutation-v1` | Descriptive (D35): the z-order operator fails its checker on equivalent shape-order edits (`compare_pptx_files` 35 of 39); a GUI-faithful save flips 3 of 92 reference golds; kappa 0.34. **Adjudicated (D82), by an isolated model, not human-validated**: 33 confirmed false negatives (11.6%; `compare_pptx_files` 37.1%, z-order 85.4%), 3 gold-defect tasks, P2 12.4% on 337, false positives 2 | `program/evidence/2026-10-08/q2-mutation-confirm/`, `program/evidence/2026-10-11/q2-mutation-adjudication-v2/` |
| `q2-evaluator-mutation-v1-k2` | **VERIFIED** (job 1186, CPU only, from the freeze commit `7d9c881a`): gate 2 of 80 K2 pairs excluded (one task's reopen timed out after LibreOffice did not quit); the 78 compared pairs agree with the offline verdicts in both runs; 41 of 41 candidate events reproduced; no family dropped; the parent analysis now carries "VM fidelity checked (K2)". Its outputs name verdicts per mutant: read after the adjudication | `program/evidence/2026-10-11/q2-mutation-k2/k2-confirm-v1-job1186/` |
| `r04-checker-nuisance-invariance-v1` | **Build arm DRIFT, locale arm DRIFT, route arm MINOR** (D89). LibreOffice 25.8 flips 18 of 92 golds and 26.2 flips 20; builds up to 24.8 flip none. de_DE, ar_EG and tr_TR flip 3 `compare_table` golds; ja_JP flips none. Headless convert flips 1 gold. Every discordance reproduced in two rounds. Not adjudicated | `program/evidence/2026-10-12/r04-nuisance-confirm/` |
| `q2-stage1-successor-e-v1` | **DR2 Near-equivalent** (δ 0.00 pp, 90% [−2.44, +2.44]; each harness 263 of 904; π_small upper bound 0.1187 vs 0.12, about the Monte Carlo error); **DR5 NO-GO** (π_small 0.055, [0.010, 0.119]); 1,808 episodes, 0 losses; not externally anchored; two verifiers (D97) | `program/evidence/2026-10-12/q2-stage1-successor-e-run/RESULTS.md` |
| `q2-zinv-reserve-validation-v1` | **PASS, descriptive** (D88). zinv accepts 13 of 13 held-out z-order equivalence mutants and newly accepts none of 15 violation mutants. The original comparator rejects 13 of 13 | `program/evidence/2026-10-12/q2-zinv-reserve-run/` |

Gauntlet records: K1 v2 (45, honest exit), K1 v3 (51, 55, 56; honest exit, D54), Q1 Stage 0 (45, honest exit).
Q1 Stage 0 is closed on the audit-metric study (D46): under TF32 a tolerance
audit certifies "not grossly wrong", not 1% correctness
(`program/evidence/2026-10-08/q1-audit-metric-study/`).

## In progress (D71-D82)

Since D71:
- The question-renewal dossier is done
  (`program/evidence/2026-10-11/question-renewal/dossier.md`). It recommends
  R01 (rerun-noise sources) as lead, R03 (completing the checker-mutation
  note) as spine and R02 (on-policy checker audit) as backfill. Under D80, R03
  proceeds now that the adjudication is done (D82).
- The Q2 technical report draft is merged (`paper/q2-report/`), unpublished.
  The corrections it found are recorded in D72.
- S2 v3 scored 60, then 65 (the best score; D76). Under D80 it continues as
  S2 v4.
- R01 scored 58, then 57, and ended at an honest exit. Its records-only
  finding stands: serving nondeterminism, not the environment, drives S1a's
  rerun disagreement (D77).
- K2 (`q2-evaluator-mutation-v1-k2`), ledger row 17, ran as job 1186 and was
  VERIFIED and independently reproduced (D79). 78 of 78 compared pairs agree
  with the offline verdicts in both in-VM runs, and 41 of 41 candidate events
  reproduce. The checker-mutation study's label is now "VM fidelity checked
  (K2)". The adjudication and the final rerun are done (D82).
- R04 was verified ready to freeze (D78). Under D80 it is frozen (row 18), and
  it runs standalone with its section 4.4 adaptations and CPU cap accepted.
- The checker-mutation adjudication ran under D80. The first run was void (the
  orchestrator's prompt was not the registered template; D81). Run 2 is the
  record (D82): adjudicated by an isolated model, not human-validated. Its
  Fable and notation sensitivities change no conclusion.

## Waiting on Kevin

See `pending_decisions_for_kevin` in `program/state.json`. Still open:
- the gauntlet trust store, or an admission ruling for anything over 8 GPU-h
  that D80 does not cover (D24);
- the R580 driver, or written risk acceptance (Q1), and a licensed policy;
- review of D1-D82;
- the host inotify limit behind N* = 32;
- an optional human spot check (D9);
- the outward actions: disclosures to Letta and xlang-ai, now including the
  `compare_pptx_files` finding; licence requests; a history purge; key
  rotation; a valid Anthropic API key.

## Host checkouts

`~/cotcodec` on the host still holds Codex's uncommitted edits (archived
privately) and is untouched. `~/cotcodec-main` is a clean clone of `main`.
Experiments run from fresh clones or exports under `~/cotcodec-runs/`.
