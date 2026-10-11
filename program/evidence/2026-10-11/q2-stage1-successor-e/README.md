# Q2 successor E (`q2-stage1-successor-e-v1`, DRAFT): pre-registration evidence

CPU only. No host job of any kind ran for this bundle, and no E episode exists. Everything
here was computed on the development Mac from committed files. Seeds: 42 (plus 43 and 44 for
the simulated identity checks). Branch `stage0/q2-successor-e`, not pushed.

E is S1a's design with more data (D66, D69, D80 (iii)): all 113 eligible pool tasks, Qwen3.5-4B
and 9B, four new serving sessions per size, one episode per (size, task, harness, session),
S1a's estimands, rules, harnesses, engine, prompts, action path, lane and records. The
registration is `program/preregistrations/q2-stage1-successor-e-v1.md`.

## Contents

| File | What it is |
|---|---|
| `plan/plan-e.json` | E's plan file, rendered by `python -m harness.q2_stage1e.plan render --out ...` from the split file, S1a's frozen plan (by its `plan_sha256`) and the design study's cost model (by SHA-256). `plan_sha256` `31270b72091a98289d4baea8aec2bc892bcad8061ab8e3f1d9a69442b6cf9b9c`; file SHA-256 `e37a3d127d67e81c8b55f052c2fbc05eb62884d1b220a5514e86a17a86b4d322`. `tests/test_q2_stage1e.py` re-renders it byte for byte |
| `cap_sufficiency.py`, `cap-sufficiency.json` | Do E's per-job caps (52 minutes at 9B, 48 at 4B) hold every slot before the GPU job's USR1? A replay of the lane's continuous dispatch (V = 20) in each job's registered order with S1a's realized slot occupancies resampled per (size, task, harness), 10,000 draws per scenario |
| `analysis_identity.py`, `analysis-identity.json` | E's registered analysis (`harness.q2_stage1e.analysis.analyse_array`) against S1a's committed registered readings on S1a's records, and against the design study's `harness.q2_design.analyse.analyse` on simulated E-shaped data, at 10,000 resamples and flips |

## Results

**Caps.** The dispatch model replays S1a's four A1 jobs' realized spans from first dispatch
to last teardown to within 0.2 s (4,023.0, 3,958.8, 4,278.7 and 4,281.8 s). For E's jobs, the
probability that every slot ends before USR1:

| Scenario | 9B (cap 52) | 4B (cap 48) |
|---|---:|---:|
| S1a's slots as measured | 1.000 | 1.000 |
| every slot 10% longer | 1.000 | 1.000 |
| every slot 20% longer | 1.000 | 0.9215 |
| 5% of each cell's first attempts lost at full length and re-queued | 1.000 | 1.000 |

**Analysis identity.** On S1a's records, E's `analyse_array` reproduces S1a's committed
`report-guarded.json` exactly on both of S1a's sets: the primary (32 base tasks: p_X 0.4588,
π_small bounds [0.000, 0.260], DR2 Inconclusive, DR5 INCONCLUSIVE) and the registered secondary
(113 tasks: p_X 0.1571, bounds [0.0196, 0.1622], Inconclusive, INCONCLUSIVE). That covers 18
estimates per set, the δ paired t, the X sign-flip and label-permutation p-values, the
session test, the harness effect by session, success, DR1, DR2 and DR5. On three simulated
E-shaped data sets (S = 4, R = 1, 113 tasks), it gives the same p_X, π_small bounds, δ, DR2 and
DR5 as the design study's `analyse.analyse`, the function E's registered power statement was
computed with.

## Reproduction

From the repository root, with the project's Python (numpy 2.5.2, scipy 1.18.0) and
`PYTHONPATH=.`:

    python -m harness.q2_stage1e.plan render --out /tmp/plan-e.json   # equals plan/plan-e.json
    python program/evidence/2026-10-11/q2-stage1-successor-e/cap_sufficiency.py --out OUT.json
    python program/evidence/2026-10-11/q2-stage1-successor-e/analysis_identity.py --out OUT.json

`cap_sufficiency.py` takes about a minute and `analysis_identity.py` about ten. Each output
records its inputs' SHA-256, the commit, whether the tree was dirty, and the versions.

The committed outputs were generated in the worktree at `29a25b5d`, clean (the commit that
added E's code and this bundle; `tree_dirty` false). A first run from the uncommitted tree gave
the same values in every field but the provenance.
