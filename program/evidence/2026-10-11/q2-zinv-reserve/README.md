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
5. Repeated on a fresh scratch clone at the branch's `81d69a0b` (after the validity change):
   the same results; scratch row 19 with file SHA-256 `4a61a311...` and row hash
   `416898ea...` (fill commit `964ee481`, freeze commit `13e2ae0d`, ledger-only diff);
   reserve refused without the variable, admitted with it, refused at the fill commit; the
   suite 24 passed at the scratch freeze commit. The real ledger stayed at 18 rows.

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
- `317e89c1` staged likewise with plan `dev-zinv-v1` (`--reuse-parent-run dev-mutants-v9`:
  step 4 alone on the parent's stored dev run and `dev-controls-v9`). It was never
  submitted: before the queue emptied, a check of the released confirm verdicts showed that
  the parent's `scored_sha256` hashes the scorer's temporary path (0 of 1,300 lock-exact and
  scoping pairs equal), so the draft's validity rule, which compared it across scorings,
  would have voided every row. The rule now compares a path-independent digest of the job's
  files taken before and after both scorings (`bc14599e`), and `dev-zinv-v1` stays pending,
  superseded by `dev-zinv-v2` at `bc14599e`.

## Dev rehearsal of step 4 (`dev-zinv-v2/`, Slurm 1202; exploratory, dev split)

`zr_host.py next --name dev-zinv-v2`, submitted when `squeue` was empty, from the staged
export of `bc14599e`; the step reads the parent's stored dev mutation run `dev-mutants-v9`
(Slurm 714-716, code `34046e09`) and control run `dev-controls-v9`. One CPU job through the
unchanged lane: exit status 0, 2 min 36 s (21:01:47 to 21:04:23 UTC), `gpus_requested` 0,
network none. In the container both guards passed (this addendum's, then the parent's
`campaign guard`: 447 file-cache files verified, OSWorld tree `4153c686...`, VM baseline
`f3253818...`), then `run rescore` and `run judge`.

- 48 rows: 39 evaluable mutants of the dev split's tasks checked by `compare_pptx_files`
  alone (3 tasks), 4 saved golds, 5 saved do-nothing states. Every row valid: the fresh
  original scoring reproduced the registered verdict on 48 of 48, and every job's files had
  the same digest before and after both scorings.
- The rule's reading (dev, exploratory, not evidence): PASS, descriptive. zinv accepted 6 of
  6 z-order mutants on 2 tasks, all 6 failed by the original; no violation mutant newly
  accepted (6 on 1 task); no other item changed verdict (42 of 42 equal); no zinv error.
  The dev z-order mutants were not part of zinv's validation set (job 1000 read the confirm
  campaign only), but the dev split was read during the operators' development.
- Files: `zinv-rows.json` (SHA-256 `d8c77b28...`), `judgement.json` (`54f56a73...`),
  `receipt-1202.json`, `plan.json`. They hold ids, labels, scores and digests only.

Not rehearsed on the host: steps 1-3 (the parent's frozen mutation jobs, which made
`dev-mutants-v9` and the confirm run) behind this addendum's guard and target filter; their
commands are checked against `submit_mutants.sh` by the tests and rendered by
`next --dry-run` (plan `dev-rehearsal-v1`).
