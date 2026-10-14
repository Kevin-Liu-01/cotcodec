# q2-stage1-successor-e-v1: the registered analysis (section 18 (iii)), steps and files

The results are in `../RESULTS.md`. This file records what ran, with its commands, so that
every number there can be traced to a file here. **Not externally anchored.**

Everything ran on the host from the read-only export of E's freeze commit
`f6144d6bf745d944cb016cfc2b9894e1dbf7eb66` (`~/cotcodec-runs/stage0/q2-stage1e/src/f6144d6b.../`,
the export every E job ran from; `.git_sha` names the commit), with the registered commands
of `harness/q2_stage1e/analysis.py`, `harness/q2_stage1/rescore.py` and `glmm.R` unchanged.
The operator steps around them are `ops/q2e-analysis/e_ops.py` (shipped read-only to the
host at commit `fb4458a6`) and the analyst's self-check `ops/q2e-analysis/selfcheck.py` (at
`0c36cb32`). Neither is code of record. The host's analysis directory is
`~/cotcodec-runs/stage0/q2-stage1e/analysis/e-v1/` (`A` below); `env.sh` is its environment.
Every output there was written once (`set -o noclobber`; the registered CLIs and `e_ops.py`
refuse to overwrite).

## Steps, in the order they ran

| Step | Section 18 (iii) | Command (host; `. $A/env.sh` first) | Output here |
|---|---|---|---|
| 0 | 8 | `EOP provenance --stage pre`: the export's `.git_sha`, `preregister.py verify` and `check-chain` (uv CPython 3.12), the plan digest, every file of E's section 23 tables and S1a's section 20 table, S1a's `a1.jsonl` | `provenance-pre.json` |
| 1 | 1 | `python3 -E -s -B -m harness.q2_stage1e.analysis dr0 --run-dir $R/runs/$VM --plan $PLAN > $A/dr0-$VM.json`, all eight jobs | `dr0-*.json`, `dr0-exits.txt` |
| 2 | 3 | `python3 -E -s -B -m harness.q2_stage1e.analysis costs --run-dir ... (8) --out $A/costs.json` | `costs.json` |
| 3 | - | `EOP live-records`: each run directory's `episodes.jsonl`, `lane-receipt.json` and `manifest.json` checked against the digests its DR0 file read; the raw records concatenated in the registered job order | `live-records.json` (`e-live.jsonl` stays on the host: it is the eight committed `vm-*/episodes.jsonl` in order) |
| 4 | 6 | `python3 -E -s -B -m harness.q2_stage1e.analysis glmm-input --records $A/e-live.jsonl --plan $PLAN --out $A/glmm-inputs/e-primary.csv` | `glmm-inputs/e-primary.csv` |
| 5 | 2, 6 | `EOP submit-batch --wait-max 32400 --stable 5` (under `nohup setsid`): on an empty queue (five consecutive empty 2-second polls), the GLMM job, then one rescoring job per E job, each through `s1a-cpu.sbatch` | `submit-batch.json` |
| 6 | 2 | `EOP merge`: the registered `python3 -E -s -B -m harness.q2_stage1.rescore merge` per job, then `e.jsonl`, the eight merged files in the registered job order | `e.jsonl`, `merge.txt` |
| 7 | 4 | `EOP step report report --records $A/e.jsonl --plan $PLAN --costs $A/costs.json --dr0 ... (8) --out $A/report.json` (one `cpu-step.sbatch` job) | `report.json`, `step-report.json`, `logs/` |
| 8 | 2 | `EOP coverage`: per job, rows, errors, receipts; per set, corrected verdicts from rescoring, live-score fallbacks and flips split into checker corrections and replay mismatches | `rescore-coverage.json` |
| 9 | 5 | `EOP step s15 section15 --records $A/e.jsonl --plan $PLAN --report $A/report.json --costs $A/costs.json --run-dir ... (8) --out $A/s15.json` | `s15.json` |
| 10 | 7 | `EOP step joint joint --records $A/e.jsonl --s1a-records $X/program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl --plan $PLAN --out $A/joint.json` | `joint.json` |
| 11 | 6 | `EOP glmm-collect`: the fit's exit code, convergence as `glmm.R` wrote it, the R package lock against the registered `abb8871d...` | `glmm-summary.json`, `glmm-out/` |
| 12 | - | the analyst's self-check, `python3 -E -s -B selfcheck.py $A/e.jsonl $PLAN $A/report.json > $A/selfcheck.json` (run directly on the host: 2 s, numpy and scipy only) | `selfcheck.json` |
| 13 | 8 | `EOP provenance --stage post`: as step 0, plus the digest of every input and of every output above but `logs/` | `provenance-post.json` |

## Slurm jobs (all CPU only: no GRES; `s1a-cpu.sbatch` refuses a GPU and its container sees no `/dev/nvidia*`)

| Job | Step | Ran (UTC) | Outcome |
|---:|---|---|---|
| 1279 | GLMM, `glmm.R` (200 refits, seed 42) in the pinned image `b15584f3...`, input `e-primary.csv` (`ab6abee7...`, 1,808 rows) | 2026-10-13 23:40:15 to 2026-10-14 00:03:26 | exit 0 (`glmm.exit` 0, receipt `exit_status` 0); R package lock `abb8871d...` as registered |
| 1280-1287 | `rescore capture` in the metric image `2006c1a9...`, `--time=08:00:00`, one per E job (1219, 1222, 1251, 1254, 1265, 1268, 1272, 1275 in that order) | 23:40:15 to 01:18:32-01:18:47 (about 1 h 38 min each) | `exit_status` 0 each; 226 rows each |
| 1288 | the registered report | 01:20:28-01:21:06 | `exit_status=0` |
| 1289 | section 15 items | 01:21:39-01:21:40 | `exit_status=0` |
| 1290 | the joint reading with S1a | 01:21:39-01:21:50 | `exit_status=0` |

The batch (1279-1287) was submitted at 2026-10-13T23:40:14Z by `submit-batch` after five
consecutive empty polls of the whole queue (2,657 polls from 22:11:24): it waited for job 1278
(S2 v5's development confirmation, CPU only, another workstream's, submitted at 22:00:32 after
E-4B-E4's VM batch job had ended) to leave the queue. Jobs 1288-1290 were submitted with only
this analysis's own jobs in the queue (`step-*.json` `queue_at_submission`). No other
workstream's job was in the queue at any poll this analyst took from 23:43 to 01:22 UTC.

## Checks that ran beside the steps

- **Records.** The eight run directories' `episodes.jsonl`, `lane-receipt.json` and
  `manifest.json` have the SHA-256 their DR0 files read (`live-records.json`), which are the
  digests the committed `../e-*/pair/dr0.json` files and `../e-*/vm-*/episodes.jsonl` carry.
  The re-run `dr0-*.json` are byte-identical to the eight committed `../e-*/pair/dr0.json`.
- **GLMM input.** Written from the raw records before the merge, so that the GLMM could run
  beside the rescoring; written again from the merged `e.jsonl` after the merge
  (`glmm-inputs-check/` on the host): byte-identical (`ab6abee7...`).
- **Merge.** `merge.txt` holds the digests of the eight `merged-<vm>.jsonl` (on the host) and
  of `e.jsonl`, their concatenation in the registered job order.
- **Provenance** (`provenance-pre.json`, `provenance-post.json`): `pass` true at both ends:
  `.git_sha` `f6144d6b...`; `preregister.py verify q2-stage1-successor-e-v1` and `check-chain`
  exit 0 (row 19, file SHA-256 `47e65877...`, 19 rows, PASS); plan `plan_sha256`
  `4e7298a7...` and file `12bded25...`; all 11 E files and 8 infrastructure files of section
  23 and all 75 files of S1a's section 20 at their registered digests; S1a's `a1.jsonl`
  `4af798f5...`; host Python 3.10.12 with numpy 1.21.5 and scipy 1.8.0 (`-E -s -B`).
  `provenance-post.json` lists the digest of every input and output here but `logs/`; every
  committed copy here matches it.
- **Self-check** (`selfcheck.json`; not the fresh verifier): see `../RESULTS.md`, disclosure 4.
- **Fresh verifier** (`verification/`; added on 2026-10-14 after `RESULTS.md` was first
  written, so it is not in `provenance-post.json`). `verifier-record.json` holds the section 18
  verifier's records: the frozen code rerun on the SHA-checked raw records, byte-identical
  outputs, and an independent re-implementation that agrees. `mc-seed-check.py` and its
  outputs are the frozen bootstrap of π_small at 20 other seeds and at 200,000 resamples, run
  read-only on the host by stdin pipe. They are descriptive and not registered (`../RESULTS.md`
  deviation 1, disclosure 6).

## Files here

`env.sh`; `dr0-*.json`, `dr0-exits.txt`; `costs.json`; `live-records.json`;
`glmm-inputs/e-primary.csv`; `submit-batch.json`; `rescore-<vm>/rescored.jsonl` and
`receipt-<slurm>.json`; `merge.txt`; `e.jsonl` (the merged records of all eight jobs, the
report's input; `4e3fc281...`); `report.json` (`step-report.json`); `rescore-coverage.json`;
`s15.json` (`step-s15.json`); `joint.json` (`step-joint.json`); `glmm-out/` and
`glmm-summary.json`; `selfcheck.json`; `provenance-pre.json`, `provenance-post.json`;
`verification/` (the fresh verifier's records and the seed check, added later); `logs/`
(the report, section 15 and joint job outputs, the GLMM job output, which is empty, and
`submit-batch.log`). The eight rescoring job outputs (about 210 KB each of checker warnings
and debug prints) stay on the host, with their SHA-256 in `logs/rescore-logs.sha256`;
`e-live.jsonl` (the eight `../e-*/vm-*/episodes.jsonl` in order, `a863ffc1...`) and the eight
`merged-<vm>.jsonl` stay on the host too. No file here holds a host address.
