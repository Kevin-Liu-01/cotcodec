# q2-zinv-reserve-validation-v1: development record (DRAFT; nothing here is evidence)

Pre-freeze record of the draft addendum
`program/preregistrations/q2-zinv-reserve-validation-v1.md` (R03 (b): does the corrected
z-order comparator `zinv` accept at least 95% of held-out z-order equivalence mutants on the
reserve split while accepting no violation mutant the original rejects?). Branch
`stage0/r03-zinv-reserve`. No mutant of the frozen operators exists on the reserve split and
none was built; the real ledger was not written.

> Blind warning (D9, D82): `dev-zinv-v2/` and `dev-rehearsal-v2/` name checker verdicts per
> mutant (dev split). The parent's human spot check (D9) is still pending: if you are doing
> it, answer from its blind packets before reading them. No dev or reserve mutant of these
> files is in the spot check or the adjudication pool.

| File | What |
|---|---|
| `known-answer-confirm-devset.json` | The registered rule (`rules.judge`) read on S1a job 1000's committed rows (`program/evidence/2026-10-08/q2-stage1-g0/zinv/zinv-validation-v3.json`): PASS at `registered_rule` status, 39 of 39 z-order mutants on 15 tasks accepted, 0 of 67 violation mutants newly accepted, 35 of 39 failed by the original. This is zinv's development set, so it checks the rule's code, not zinv |
| `design-table.json` | `rules.design_table()`: the detection probabilities, lower bounds and expected-size simulation quoted in section 4 |
| `dev-zinv-v2/` | Step 4 alone on the parent's stored dev run (Slurm 1202; below) |
| `dev-rehearsal-v2/` | The full dev rehearsal of steps 1-4 and its release view, exactly as `zr_host.py export` wrote it (Slurm 1205, 1209, 1212, 1213; below) |

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

Steps 1-3 were not rehearsed then; `dev-rehearsal-v2` below does.

## Pre-freeze audit 1 fixes (`046f82e7`)

The audit's blocking item (two tests failed at the fill commit) and its cheap non-blocking
items were fixed before any further host job; the dispositions are in the registration's
section 13. New behaviour that the rehearsal below exercises: `zr_host.py export` (the
release view in the parent's layout), the reserve plan name (`reserve-v1` only), and the
blind warning in the rows, the judgement and the release.

## Full dev rehearsal of steps 1-4 (`dev-rehearsal-v2/`; exploratory, dev split)

From the staged export of `046f82e7` (`git archive`, `.git_sha`; its code equals the
registration's code table), on the host's Python 3.10.12: `plan --split reserve --name
reserve-v1` refused ("runs only after q2-zinv-reserve-validation-v1 is frozen"), then
`plan --split dev --controls-run dev-controls-v9 --name dev-rehearsal-v2` and `next` until
`complete`, each step submitted by `next` only when `squeue` showed no job (R04, Successor
E and S2 v4 ran between them). Four CPU jobs through the unchanged lane, GPU-less
(`gpus_requested` 0, no `/dev/nvidia*`), network none, every receipt exit status 0:

| Step | Slurm | Image | Wall time (UTC) | What it did |
|---|---|---|---|---|
| `targets` | 1205 | metric | 23:06:57-23:06:59 | both guards (dev), the parent's job 1 (51 control jobs, 17 targets), `select-targets`: 5 pptx targets kept (dropped 4 docx, 1 text, 7 xlsx) |
| `build` | 1209 | LO-VM | 23:33:24-23:35:10 | the parent's job 2: 5 targets planned, 97 mutants planned, applied and admitted (42 equivalence, 19 violation, 15 extra change, 21 ambiguous), 0 duplicates, 102 scoring jobs saved |
| `score` | 1212 | metric | 00:59:37-01:04:46 | both guards, the parent's job 3: K2 sample "not drawn: K2 needs at least 3 domains, found 1"; 102 jobs merged, 0 excluded; both venvs scored 102 jobs; 0 S1 candidates; recheck 97 (96 admitted after the save); lock-exact status 57 evaluable, 11 ambiguous, 1 normalized, 28 null-not-pass (scoping identical) |
| `zinv` | 1213 | metric | 01:04:47-01:07:25 | both guards, `campaign guard` (447 file-cache files, OSWorld `4153c686...`, VM baseline `f3253818...`), `run rescore` (48 rows), `run judge` |

Lane time 0.16 h of the 4.0 cap (the time between steps was other programs' jobs).

Checks of the outputs:

- The 97 outcomes have exactly the same multiset of (task, operator, label, lock-exact and
  scoping status and verdict, probe flag) as the parent's stored `dev-mutants-v9` (Slurm
  714-716) on the same 5 tasks. The mutant ids differ: each carries a digest of the
  recipe, whose `input_sha256` is the LibreOffice-saved base, and those bytes differ
  between runs. So the target filter changed no plan, as section 3 states.
- Step 4's 48 rows (39 evaluable mutants on the 3 tasks checked by `compare_pptx_files`
  alone; 4 saved golds and 5 saved do-nothing states from `dev-controls-v9`) form the same
  multiset of (task, kind, operator, label, registered, fresh original and zinv verdict,
  file check) as `dev-zinv-v2`, and the 9 control rows are identical, digests included.
  Every row valid (fresh original verdict equal to the registered one on 48 of 48, files
  unchanged on 48 of 48, no timeout, no scoring error). The 28 null-not-pass mutants are
  all on the fourth `compare_pptx_files` task, so none is evaluable.
- The rule's reading (dev, exploratory, not evidence): PASS, descriptive; zinv accepted 6 of
  6 z-order mutants on 2 tasks (all 6 failed by the original); none of 6 violation mutants
  newly accepted; 42 of 42 other items unchanged. Same as `dev-zinv-v2`.
- `zr_host.py export --name dev-rehearsal-v2` (host, Python 3.10.12) wrote `release/`
  (23 files): `view/` linked `prep`, `build`, `score` and `zinv` to the finished attempts and
  its `submitted.json` named jobs 1205, 1209, 1212 and 1213; the parent's `campaign export`
  read it unmodified (12 files and its manifest under `campaign/`, `slurm_jobs` the four
  jobs, `receipts.json` the four receipts, all exit 0). The released `zinv-rows.json` is
  byte-identical to the host's (no checker message over 80 characters). The directory
  `dev-rehearsal-v2/` here is that `release/` copied unchanged (568 KB; the only
  dotted-quad strings in it are the LibreOffice version `7.3.7.2`).

No defect was found, so no fix and no second rehearsal were needed. Left on the host:
staged sources `9b364be1`, `317e89c1`, `bc14599e`, `046f82e7`; plans `dev-rehearsal-v1` and
`dev-zinv-v1` (never submitted), `dev-zinv-v2` and `dev-rehearsal-v2` (complete). No
reserve plan exists.

## Scratch freeze rehearsal at the final draft (`06ee7280`)

On a fresh scratch clone (session scratchpad) of the branch at `06ee7280`: a scratch `main`
from `f6144d6b` (successor E frozen, 19 ledger rows), the branch merged into it (`20e59c22`),
then section 13's steps on the clone's own copy of the ledger. The worktree's and the main
checkout's ledgers stayed at 19 rows, unmodified.

| Commit | What | `tests/test_q2_zinv_reserve.py` |
|---|---|---|
| merge `20e59c22` (draft) | `preregister.py freeze` refused ("still contains TBD or placeholder text") | 31 passed |
| fill `2fd80080` | the status paragraph replaced by section 13's, nothing else | 31 passed |
| freeze `fbb34000` | scratch row 20 (file SHA-256 `c3a621dc...`, row hash `aa3057f8...`, `git_head_at_freeze` `2fd80080`); `check-chain` PASS (20 rows), `verify` PASS; the diff from the fill commit is `program/preregistrations/ledger.jsonl` alone | 31 passed |

On `git archive` exports of the two commits: the freeze export refuses the reserve split
without `Q2ZR_PREREG_FROZEN`, admits it with the variable (row hash `aa3057f8...`), refuses
confirm and admits dev; the fill export refuses the reserve split ("runs only after ... is
frozen"); the parent's `require_split_allowed('reserve')` passes on the freeze export. The
ledger-reading suites at the scratch freeze commit (ledger, parent, K2, S1a and successor E
preregistrations, R04, the parent's campaign) pass with the extra row: 144 passed, 5
skipped.

On the host (Python 3.10.12), the guard's inputs from the scratch freeze export, unpacked
in a temp directory outside the run root and removed afterwards: `make_plan` for the
reserve split refused `reserve-v1` without the variable, refused `reserve-v2` with it ("the
reserve split's one registered plan is reserve-v1"), and admitted `reserve-v1` with it (the
pinned `reserve-controls-v1` files matched on the host); nothing was written and the run
root's plans were unchanged.

An earlier pass of the same rehearsal at `046f82e7` (main at `2b8fadc7`, scratch row 19)
gave the same results (31, 31 and 31 passed; 130 passed and 3 skipped in the ledger-reading
suites without successor E's).
