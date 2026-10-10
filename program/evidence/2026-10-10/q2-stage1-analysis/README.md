# q2-stage1-rescoped-v1 (S1a): the registered analysis, 2026-10-10

**Labels (`report/guard.json` `labels`): complete data (`incomplete`: null, no reason);
"not externally anchored" (ANCHOR-UNAVAILABLE, DR-A).** Every file in this directory falls
under these labels. Some files are written by the registered CLIs: `dr0-*.json`,
`merged-*.jsonl`, `a1.jsonl`, `costs.json`, `report/report.json`, `rescore-*/rescored.jsonl`
and the GLMM fits. Two operator records are written before the completeness test exists:
`provenance-pre.json` (a check of the frozen inputs before any record was read) and
`rescore-jobs.json` (the rescoring submissions). None of these can carry the label in its own
body, so they fall under it here. `provenance.json` carries the label and binds each of them
by SHA-256. Neither operator record holds an estimate or a count of records.

The results and what they license are written up in
[`../q2-stage1-a1/RESULTS.md`](../q2-stage1-a1/RESULTS.md). This directory holds the
evidence, as listed in step 12 of the runbook (`ops/s1a-analysis/RUNBOOK.md`).

## What ran

One analyst ran it on the host, following the runbook step by step. The code is the
read-only export of the freeze commit `d5f57988ab94e0c098feddb744b78b73b5ad88ca` (the code
of record, unchanged). The operator scripts are `ops/s1a-analysis/` at
`6d85529b1f84e1c9bd6a01b693c0eab76d0054c6`, shipped by `git archive` to
`~/cotcodec-runs/stage0/q2-stage1/ops/<commit>/`; their digests are in `provenance.json`
`ops_files`. Interpreter: the host's system CPython 3.10.12, numpy 1.21.5, scipy 1.8.0,
`python3 -E -s -B`. Every Slurm job was CPU-only, with no GRES. Each container receipt shows
`gpus_requested` 0, no `/dev/nvidia*` and network `none`.

| Step | What | Command or job | Outcome |
|---|---|---|---|
| 0 | environment | `env.sh` (VMS 1045 1048 1051 1062, COSTVMS the same) | written once |
| 1 | preconditions | `provenance.py` -> `provenance-pre.json` | registration `f9db7cc3...`, plan `6a3f0219...` (file `a5f0aadc...`), 75 code-of-record files: PASS; queue empty; partition MaxTime 1 day |
| 2 | DR0 per job | `python -m harness.q2_stage1.rules dr0` | exit 0 for all four; `dr0-*.json` byte-identical to the session evidence's `pair/dr0.json` |
| 3 | offline rescoring | `rescore_jobs.py submit`, `--time=08:00:00`: Slurm 1065-1068 (metric image `2006c1a9...`, 8 CPUs each) | 15:25:10-18:36:47 UTC, `exit_status` 0 for all four; 452 rows per job |
| 4 | merge, `a1.jsonl`, coverage | `python -m harness.q2_stage1.rescore merge`; `rescore_jobs.py coverage` | 1,808 records; coverage in `rescore-coverage.json` |
| 5 | cost card input | `python -m harness.q2_stage1.analysis costs` | `costs.json` (GPU elapsed from `scontrol` EndTime, all four) |
| 6 | report (D59 (i), (ii)) | `run_report.py`, Slurm 1071 | `exit_status` 0; `report.json`, `guard.json`, `report-guarded.json`; no guard reading changed |
| 7 | identity check | `check_identity.py`, Slurm 1072 | PASS, mode `fractional` (see below) |
| 8 | first divergence | `first_divergence.py`, Slurm 1073 | 512 step logs read, 0 missing |
| 9 | GLMM | `glmm_inputs.py write/submit/collect`, Slurm 1074 (image `b15584f3...`, 8 CPUs) | 18:37:56-18:54:36 UTC; both fits exit 0; R package lock `abb8871d...` matches |
| 10 | section 15 assembler | `assemble_s15.py`, Slurm 1075 | `s15.json` |
| 11 | provenance | `provenance.py` -> `provenance.json` | PASS; 53 inputs, none missing |

**Identity check (D59 (i)).** The base holds 14 episodes with a fractional checker score. As
the D59 dry run found (bug B1), the registered CLI raised `ValueError: outcomes must be 0, 1
or NaN` on them. It was then run on the same records with those scores set to 0. That report
differs from the wrapper's `report.json` only in `fractional_score` and the `fractional_scores`
counts, the outputs that D59 (i) allows to differ (`identity/identity.json`).

**Self-check from the committed files (not the runbook's independent verification).** On the
Mac, from this directory's `rescore-*/rescored.jsonl` and each job's committed
`episodes.jsonl`, the registered `rescore merge` reproduced all four `merged-*.jsonl` and
`a1.jsonl` byte for byte. `run_report.py` then reproduced `report.json` and
`report-guarded.json` byte for byte (numpy 2.5.2). `guard.json` differs there only in the
absolute paths it records.

## Files

- `env.sh`, `provenance-pre.json`, `provenance.json` (the digest of every input, the
  environment and the label)
- `dr0-*.json`, `dr0-exits.txt`
- `rescore-jobs.json`, `rescore-<vm>/receipt-<slurm>.json`, `rescore-<vm>/rescored.jsonl`
  (verdicts and state digests only), `rescore-coverage.json`
- `merged-*.jsonl`, `a1.jsonl`: the committed record fields plus `corrected_score`,
  `offline_raw_score`, `offline_state_score` and `live_offline_match`. The records keep no
  stdout tail (`driver.strip_stdout`).
- `costs.json`
- `report/` (`report-guarded.json` is the file to read), `identity/identity.json`,
  `first-divergence.json`
- `glmm-inputs/`, `glmm-job.json`, `glmm-out/{glmm-*.json,*.exit,r-packages.json,receipt-1074.json}`,
  `glmm-summary.json`
- `s15.json`
- `logs/` (the four `cpu-step.sbatch` outputs)

Step logs, screenshots, captures, model replies and setup or postconfig stdout tails stay on
the host (section 16). This directory holds no host address and no credential. The only
dotted-quad string is a package version in `r-packages.json`.

## Key digests

| File | SHA-256 |
|---|---|
| `report/report-guarded.json` | `6bda751e55c049b9edbd3613d9004f8ab2285a43b2ca890274991c74de7ee655` |
| `report/report.json` | `9c4d483aec6dfc9316f1d3a2d1798aaf1c8ed5c57ba5365cecc0015bad3e8d5b` |
| `report/guard.json` | `6b43dee9fae1ae5ac28457f7a0eb062dc4abfb62c37e09b4f1e298a4efdaa4a2` |
| `a1.jsonl` | `4af798f5908e48aaf84d116682c813311b5ae48096e3b7ed2299c1530c08c6c0` |
| `costs.json` | `8a03f13c6fdb795032f7245e159cac6f7f2d12aa6e68a72f95384bd2358a08d5` |
| `s15.json` | `f09a8031988133e2d4d4eb3e392d6fc66fa10cc102fa5a3d121436fefdffbcfa` |
| `identity/identity.json` | `b24902ac14f53852e05ab775f4a685284876978fb8d0a64e560e65b879c7bb3e` |
| `first-divergence.json` | `dcd6744ee2b68f444ddd8909a9a42933838ec05498cfd4a160963467ee1439fa` |
| `rescore-coverage.json` | `61213f197ce7a6f6dd4a40cbf67cddb4e3fea6f9a194f5d41406fc3550533a41` |
| `glmm-summary.json` | `9691c846f3fb34f7e9936f8f461becdae6b3c7cae8f064579dd3d7dc0d080be3` |
| `glmm-out/glmm-primary.json` | `c753afdf731b71c84945be13bf4a8c4a7794954409ce87ed0eb4711d71107752` |
| `glmm-out/glmm-secondary.json` | `69faad13e6a23148bcd0caf6bfd9367ce258e6c1c524adf6aeaaa12453861303` |
| `provenance.json` | `c365ae0f4e6972c632566848bc6bcda574b51645f0aa6940d9bcd5a0cc441b72` |

The other files' digests are in `provenance.json` `inputs`. All 40 inputs from the host's
analysis directory were checked against the copies here, and every one matches.

## Still open

The runbook's independent verifier still has to run (step 12). It would re-run steps 4, 6, 7
and 9's writer from these files and check the outputs that read host-only files against
`provenance.json`.
