# q2-zinv-reserve-validation-v1: development record (DRAFT; nothing here is evidence)

Pre-freeze record of the draft addendum
`program/preregistrations/q2-zinv-reserve-validation-v1.md` (R03 (b): does the corrected
z-order comparator `zinv` accept at least 95% of held-out z-order equivalence mutants on the
reserve split while accepting no violation mutant the original rejects?). Branch
`stage0/r03-zinv-reserve`. No reserve mutant exists and none was built; the real ledger was
not written.

| File | What |
|---|---|
| `known-answer-confirm-devset.json` | The registered rule (`rules.judge`) read on S1a job 1000's committed rows (`program/evidence/2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json`): PASS at `registered_rule` status, 39 of 39 z-order mutants on 15 tasks accepted, 0 of 67 violation mutants newly accepted, 35 of 39 failed by the original. This is zinv's development set, so it checks the rule's code, not zinv |
| `design-table.json` | `rules.design_table()`: the detection probabilities, lower bounds and expected-size simulation quoted in section 4 |

## What the frozen parent says (summary of section 2)

The parent registers the reserve split's golds for P1 only (lines 375-402) and says adding
its 28 targets "is not part of this registration" (lines 576-579); its pins name
`"mutation_split": "confirm"` (line 230), which its code does not enforce. zinv is registered
by S1a (lines 321-351), validated on the confirm split, which was also its development set.
R04 promises not to change zinv from its reserve-gold verdicts before R03 (b) runs. So the
reserve-split zinv test was not registered; the draft registers it.

## Scratch-ledger rehearsal (2026-10-11)

On a scratch clone of the branch at `9b364be1` (in the session scratchpad), with the clone's
own copy of `program/preregistrations/ledger.jsonl` (18 rows); the worktree's and main's
ledgers stayed at 18 rows, unmodified:

1. `scripts/preregister.py freeze` on the draft: refused ("preregistration still contains
   TBD or <placeholder> text").
2. The status paragraph replaced by section 13's stated paragraph (scratch fill commit
   `6d23cd3b`), then frozen into the copy: row 19, file SHA-256 `0a3c6943...`, row hash
   `cc28137d...`, `git_head_at_freeze` `6d23cd3b`; `check-chain` PASS (19 rows), `verify`
   PASS; the row committed alone (scratch freeze commit `e33b313f`, which differs from its
   parent only by the ledger).
3. At the scratch freeze commit: `guard check --split reserve` refused without
   `Q2ZR_PREREG_FROZEN`, admitted with it (row hash `cc28137d...`); `--split dev` admitted;
   `uv run pytest -q tests/test_q2_zinv_reserve.py` 21 passed (the suite holds in both the
   draft and the frozen state).
4. At the fill commit (the row's `git_head_at_freeze`, whose tree has no row) the reserve
   split is refused: the registered run must be exported from the freeze commit itself.

## Host rehearsal (2026-10-11, no reserve job)

- The draft tree `9b364be1` staged at
  `/home/kevin/cotcodec-runs/stage0/q2-zinv-reserve/src/9b364be1...` (`git archive`,
  `.git_sha`). On the host's Python 3.10.12: `guard check --split dev` admitted;
  `zr_host.py plan --split reserve` refused ("runs only after q2-zinv-reserve-validation-v1
  is frozen"), with nothing written; `plan --split dev --controls-run dev-controls-v9`
  (plan `dev-rehearsal-v1`) and `next --dry-run` rendered step 1 (the parent's job 1 behind
  this addendum's guard, then `select-targets --family pptx`) with a busy queue reported and
  nothing submitted.
- The scratch freeze commit `e33b313f` was unpacked into a host temp directory (outside the
  run root, so the lane would refuse it) and `make_plan(..., "reserve")` called with
  `Q2ZR_PREREG_FROZEN` set: the guard admitted it, the two pinned control files of
  `reserve-controls-v1` matched their digests on the host, the images came from the parent's
  pins, step 1 rendered with both frozen-environment variables, and nothing was written; the
  temp directory was removed.
- `317e89c1` staged likewise; plan `dev-zinv-v1` (`--reuse-parent-run dev-mutants-v9`)
  rehearses step 4 alone on the parent's stored dev run and `dev-controls-v9`.
