# History rewrite, 2026-10-14

On 2026-10-14 (UTC) the public history of this repository was rewritten with git filter-repo
(`--sensitive-data-removal --preserve-commit-hashes`). Three things were removed that should
not have been in public history:
- the GPU host's network address, which was in five documentation files from 2026-08-17 to
  2026-10-06 (28 blobs; no hash of it is recorded, because an address hash can be reversed);
- an employer-internal data inventory, one file (blob `f05bffb4`), from 2026-09-01 to
  2026-10-06;
- an early version of `harness/q1/gates/gate_b.py` (blob `63770654`) that followed KernelGYM's
  source too closely. It was committed and replaced on 2026-10-07, and it reached `main`'s
  history the same day. The current file was rewritten from a specification
  (`harness/q1/gates/KERNELGYM_SPEC.md`).

The first two had already been removed from the working tree in the 2026-10-06 restart
(`program/log.md`). The third was never in `main`'s working tree. No commit or tag message
held any of them. The decision is D99 in `program/decisions.md`.

**What changed:**
- Every commit from 2026-08-17 on has a new id. Of the 944 commits on GitHub at the time
  (`main` at `876f0e86`), 929 were rewritten and the 15 earliest keep their ids.
  `commit-map.tsv` lists each rewritten commit as `old new`. `ref-map.txt` and
  `first-changed-commits.txt` are filter-repo's own records.
- All 7 branches and the annotated tag `legacy-2026-10-06` were rewritten (`ref-map.txt`).
  `main`'s tree did not change (`5d41ef01`), and no commit was dropped.
- 55 commits have a changed tree:
  - 44 from before the restart, which held the address or the inventory;
  - 11 from 2026-10-07, between `b3e16d41` and `acb3bc8f`, which held the early `gate_b.py`
    and now have no `gate_b.py`.
- Every other rewritten commit (874) has byte-identical files, authors, dates and messages,
  and differs only in its parent ids.
- Files in this repository quote 11 of the 55:
  - `0b3ecef0`, `f10a8571`, `2e5d695b`, `999f5583`, `bc05cc49` and `bb1eacd7` held the address
    or the inventory;
  - `acb3bc8f`, `adda2feb`, `66bc7cea`, `1a02d4a5` and `243753f1` held the early `gate_b.py`.

  `resolve` maps them to their new ids. Their files differ from the originals by design, so
  `verify` cannot vouch for them.

**What did not change:**
- The ledger, receipts, evidence, decisions and commit messages keep the ids recorded at the
  time, which are pre-rewrite ids. The ledger is hash-chained, and evidence is never edited.
- To resolve an old id:
  `python scripts/verify_history_map.py resolve program/history-rewrite-2026-10-14/commit-map.tsv <id>`.
- No ledger row's `git_head_at_freeze` or freeze commit is among the 55. For all 21 rows, the
  mapped freeze commit's only parent is the mapped head, and both keep their trees, so every
  freeze diff is unchanged.

**Checks that resolve a recorded id with git.** The K2 report's and S2's
`check_freeze_commit` and the Holo3 doctor's `code_unchanged_since_freeze` compare ids read
from frozen receipts or ledger rows with this repository's history. None of them takes a
mapped id, and frozen code is not edited, so they run unchanged only against the private
pre-rewrite archive. On the public history, check the same structure by hand: map the ids with
`resolve`, then run `git rev-list --parents -n 1 <new freeze>` and
`git diff --name-only <new head> <new freeze>`, or `git diff --quiet <new head> -- <code files>`.
Registrations frozen after the rewrite record post-rewrite ids.

**How to check:**
`python scripts/verify_history_map.py verify program/history-rewrite-2026-10-14/commit-map.tsv --expect-changed 55`
rebuilds each old commit object from its rewritten commit and hashes it. Every row except the
55 must reproduce its old id exactly (874 of 874 at the time of the rewrite).
