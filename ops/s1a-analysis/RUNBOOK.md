# S1a analysis runbook (q2-stage1-rescoped-v1, D59)

Operator steps for the S1a analysis on the host. These scripts are operator tooling, not
code of record. They import the frozen modules from the read-only export of the freeze
commit `d5f5798` and never change them. D59 fixed every rule they apply before any A1
outcome was read. This runbook supersedes the dry run's runbook and closes the checker's
gaps. Each step is listed with its exact command. Section 15 items and where they come from
are at the end.

| Script | D59 | What it does |
|---|---|---|
| `provenance.py` | (iii) | Checks the registration SHA-256 (via `lane.frozen_registration`), the frozen plan digest and the section 20 code of record. Also records the environment, the operator script digests and the input digests. |
| `run_report.py` | (i), (ii) | Runs `analysis.main` with the widened outcome check (`report.json`), then the incomplete-data guard (`guard.json`, `report-guarded.json`). |
| `check_identity.py` | (i) | Runs the registered CLI on the same inputs. The wrapper's report must match it byte for byte. With fractional scores, it may differ only in `fractional_score` and `fractional_scores`. |
| `rescore_jobs.py` | (iii) | `submit`: one rescoring job per A1 job, `--time=08:00:00`. `coverage`: coverage, live-score fallbacks and replay mismatches. |
| `first_divergence.py` | (iii) | Base tasks, scored final records, final attempt. Each step log is found in its own job's run directory. |
| `glmm_inputs.py` | (iii) | `write` (`rows_from_records`, `write_csv`), `submit` (the exit code of each fit is captured) and `collect` (convergence as written, R package digest). |
| `assemble_s15.py` | (iii) | Assembles the section 15 items that the CLI lacks. |
| `cpu-step.sbatch` | (iii) | CPU-only Slurm wrapper for one Python step. Its last output line is `exit_status=N`. |

## Rules

- **When.** Start only after the last A1 job that will run has left the queue and its DR0
  has been read: A1-4B-S2, or the job where DR0 fired. No S1a job may be pending or running
  (D58).
- **Jobs that ran.** `VMS` lists only the A1 VM jobs that ran, in the registered order
  (A1-9B-S1 1045, A1-4B-S1 1048, A1-9B-S2 1051, A1-4B-S2 `<vm>`). A job that never ran is
  left out. A job refused before any episode is still listed for DR0 and the guard, but it
  is left out of `COSTRUNS`, because `analysis costs` refuses a job with no episode that
  ran to an end.
- **CPU only.** No GRES. Slurm owns the workload. The steps that take more than a few
  seconds run as Slurm jobs and are polled with `squeue`. These are the rescoring jobs,
  the GLMM, the report, the identity check, first divergence and the assembler. DR0, merge,
  costs, coverage, the GLMM writer and collector, and provenance read files for a few
  seconds and run directly, as `collect-pair.sh` does for DR0. No command blocks for more
  than about a minute.
- **Write once.** Every output is written once, and every script refuses to overwrite one.
  If a step must be redone, move its output aside (for example `mv X X.failed-<slurm id>`)
  and record why. Nothing is deleted.
- **Data handling (section 16).** Step logs, captures, replies and stdout tails stay on the
  host. Only the files listed in step 12 go to `program/evidence/`.
- **Stop conditions.** Stop and record the cause, without patching any frozen file, if any
  of these happens: `provenance.py` exits 3; `run_report.py` exits non-zero;
  `check_identity.py` exits 3; a rescoring or GLMM receipt shows a non-zero
  `exit_status` with no rows written.

## 0. Ship the operator scripts and set the variables

On the Mac, from the verified commit of `ops/s1a-analysis` on `ops/q2-s1a`:

```bash
OPSC=$(git rev-parse <verified ops commit>)
git archive --format=tar "$OPSC" ops/s1a-analysis | ssh -o BatchMode=yes fal-h100-01 \
  "mkdir -p /home/kevin/cotcodec-runs/stage0/q2-stage1/ops/$OPSC && tar -x -C /home/kevin/cotcodec-runs/stage0/q2-stage1/ops/$OPSC"
```

On the host (`ssh -o BatchMode=yes fal-h100-01`, in the operator's tmux, bash), write the
environment once. The chain stops if the analysis directory already exists (write once).
Every later step starts with
`. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh`, so each step also
works from a fresh ssh command:

```bash
R=/home/kevin/cotcodec-runs/stage0/q2-stage1
A=$R/analysis/s1a-v1
mkdir -p $R/analysis && mkdir $A && mkdir $A/logs && cat > $A/env.sh <<EOF
R=$R
X=\$R/src/d5f57988ab94e0c098feddb744b78b73b5ad88ca
PLAN=\$X/program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json
OPSC=<ops commit sha>                    # fill in, as on the Mac
OPS=\$R/ops/\$OPSC/ops/s1a-analysis
A=$A
INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs
VMS="1045 1048 1051 <vm of A1-4B-S2>"   # only the A1 jobs that ran, registered order
COSTVMS="\$VMS"                          # minus a job with no scored or infrastructure attempt
RUNS=(); for VM in \$VMS; do RUNS+=(--run-dir \$R/runs/\$VM); done
COSTRUNS=(); for VM in \$COSTVMS; do COSTRUNS+=(--run-dir \$R/runs/\$VM); done
DR0S=(); for VM in \$VMS; do DR0S+=(--dr0 \$A/dr0-\$VM.json); done
step() { sbatch --parsable --job-name="s1a-\$1" --output="\$A/logs/%x-%j.out" "\$OPS/cpu-step.sbatch" "\$OPS/\$2" "\${@:3}"; }
set -o noclobber                         # a shell redirection never overwrites an output
EOF
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
```

## 1. Preconditions (seconds)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
squeue -h -o '%i %j %T %u'                        # no q2s1a / S1a job pending or running
scontrol show partition research | tr ' ' '\n' | grep -i '^MaxTime='   # must allow 08:00:00
sha256sum $PLAN                                   # a5f0aadce1208d9d9ab31ff572ca93e624dbd87e1b50dd194987ff8cc46e1806
python3 -E -s -B $OPS/provenance.py --export $X --plan $PLAN --ops-commit $OPSC --out $A/provenance-pre.json; echo "exit=$?"
```

`exit=0` means three checks pass:

- registration `f9db7cc38c4954b3144ac5a1afaf7bf5366449081b06c80bf89888bdf653afd8` through
  `lane.frozen_registration`;
- plan `6a3f0219...` recomputed with `plan.digest`, file `a5f0aadc...`, equal to the
  export's copy;
- every section 20 file hashes as the table says.

## 2. DR0 per job (seconds; registered CLI)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
for VM in $VMS; do (cd $X && python3 -E -s -B -m harness.q2_stage1.rules dr0 --run-dir $R/runs/$VM --plan $PLAN > $A/dr0-$VM.json); echo "$VM exit=$?" >> $A/dr0-exits.txt; done
cat $A/dr0-exits.txt                              # exit 3 = DR0 fired: every output is labelled incomplete
```

## 3. Offline rescoring (Slurm, about 3 h per job, in parallel)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
python3 -E -s -B $OPS/rescore_jobs.py submit --export $X --analysis-dir $A --inputs $INPUTS "${RUNS[@]}" --dry-run
python3 -E -s -B $OPS/rescore_jobs.py submit --export $X --analysis-dir $A --inputs $INPUTS "${RUNS[@]}" --out $A/rescore-jobs.json
```

Each job is one `s1a-cpu.sbatch` run in the metric image `2006c1a9...` with
`--time=08:00:00`. The run directory is mounted read-only at `/ro/run`, and the job writes
`$A/rescore-<vm>/rescored.jsonl` and `receipt-<slurm>.json`. The Slurm ids go to
`rescore-jobs.json`. Poll with short commands:

```bash
squeue -h -o '%i %j %T %M' | grep s1a-rescore || echo none-running
grep -h '"exit_status"' $A/rescore-*/receipt-*.json
wc -l $A/rescore-*/rescored.jsonl
```

`rescore capture` is serial and cannot resume. A job that hit its limit leaves a partial
file, and that file is kept and reported through the coverage step (D59 (iii)). If a job
failed before writing any row, for example on a mount error, do the following and record
it:

1. Move its directory to `rescore-<vm>.failed-<slurm>`.
2. Resubmit that run directory alone, with its own record of the submission:
   `rescore_jobs.py submit ... --run-dir $R/runs/<vm> --out $A/rescore-jobs-<vm>-r2.json`.

If a job wrote no `rescored.jsonl` at all, create an empty one with
`: > $A/rescore-<vm>/rescored.jsonl`. `merge` then keeps every record of that job without
a `corrected_score`, so its verdicts fall back to live scores. The coverage step counts and
reports this.

## 4. Merge and one record file (seconds; registered CLI)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
for VM in $VMS; do (cd $X && python3 -E -s -B -m harness.q2_stage1.rescore merge --episodes $R/runs/$VM/episodes.jsonl --rescored $A/rescore-$VM/rescored.jsonl --out $A/merged-$VM.jsonl); done
for VM in $VMS; do cat $A/merged-$VM.jsonl; done > $A/a1.jsonl
python3 -E -s -B $OPS/rescore_jobs.py coverage --export $X --analysis-dir $A "${RUNS[@]}" --records $A/a1.jsonl --plan $PLAN --out $A/rescore-coverage.json
```

For each job, `rescore-coverage.json` lists:

- scored attempts, and those with a capture;
- rows, matched rows, rows with `*_error` (by field), scored attempts with no row;
- the receipt's `exit_status`.

For the primary and secondary sets it adds:

- how many corrected verdicts came from rescoring and how many fell back to the live score;
- the corrected-verdict flips by task, split into `checker_correction` (the corrected
  comparator applies) and `replay_mismatch` (no correction applies, so the flip is a
  live-versus-offline replay mismatch). This split is disclosed beside the flips.

## 5. Cost card input (seconds; registered CLI, on the host)

Receipts name absolute host bridge directories (bug B9), so run this on the host:

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
(cd $X && python3 -E -s -B -m harness.q2_stage1.analysis costs "${COSTRUNS[@]}" --out $A/costs.json)
```

## 6. The report through the wrapper (Slurm CPU, under a minute)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step report run_report.py --export $X --records $A/a1.jsonl --plan $PLAN --costs $A/costs.json "${DR0S[@]}" --out-dir $A/report); echo $J
squeue -h -j $J || true; tail -2 $A/logs/s1a-report-$J.out      # exit_status=0
```

The step writes three files:

- `$A/report/report.json`: `analysis.main` with `estimators._check` widened to [0, 1]
  (D59 (i)). It is absent when the frozen report raises because no size holds two sessions
  (bug B2).
- `$A/report/guard.json`: the inputs' digests, the registered argv, the registered error if
  any, `fractional_base_scores`, completeness (DR0 per job from the files and recomputed
  from the records, the jobs present and absent, the sessions per size) and every reading
  the guard changed.
- `$A/report/report-guarded.json`: the report to read. With complete data it is
  `report.json` plus a `guard` block. With incomplete data the guard changes these
  readings:
  - every output is labelled `incomplete`;
  - a single-session size's session test is `not_estimable`;
  - DR1 is read on the sessions present;
  - DR5 is "not evaluable as registered", and π_9B is shown against both M = 0.13 and
    M = 0.18 as a description only;
  - no p-value is shown from an all-NaN statistic.

  If no size holds two sessions, the file is the delta-only report: δ and the descriptive
  and infrastructure counts. D_b, D_w, X, π, the X test, DR2, DR5, P1, P2, the session test
  and P3 are then not estimable.

## 7. Identity check (Slurm CPU, about one more report)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step identity check_identity.py --export $X --records $A/a1.jsonl --plan $PLAN --costs $A/costs.json --wrapper-report $A/report/report.json --out-dir $A/identity); echo $J
tail -2 $A/logs/s1a-identity-$J.out                              # exit_status=0
```

`$A/identity/identity.json` reports one of three modes:

- `byte identity`: the registered CLI wrote a report, and it equals the wrapper's.
- `fractional`: the registered CLI failed on a fractional base score (bug B1). It was run
  again on the records scored 0, and the reports differ only in `fractional_score` and
  `fractional_scores`.
- Both failed (bug B2).

Exit 3 stops the analysis.

## 8. First divergence (Slurm CPU, reads step logs on the host)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step divergence first_divergence.py --export $X --plan $PLAN --records $A/a1.jsonl "${RUNS[@]}" --out $A/first-divergence.json); echo $J
tail -2 $A/logs/s1a-divergence-$J.out
```

The output gives counts only: within and between pairs, pooled and per size, the kind at
each step, and the number of step logs read and missing. The set is stated in the file.

## 9. GLMM (writer seconds; fits about 20 min in Slurm)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
python3 -E -s -B $OPS/glmm_inputs.py write --export $X --plan $PLAN --records $A/a1.jsonl --out-dir $A/glmm-inputs
python3 -E -s -B $OPS/glmm_inputs.py submit --export $X --inputs-dir $A/glmm-inputs --out-dir $A/glmm-out --out $A/glmm-job.json --dry-run
python3 -E -s -B $OPS/glmm_inputs.py submit --export $X --inputs-dir $A/glmm-inputs --out-dir $A/glmm-out --out $A/glmm-job.json
squeue -h -o '%i %j %T %M' | grep s1a-glmm || echo none-running
cat $A/glmm-out/primary.exit $A/glmm-out/secondary.exit
python3 -E -s -B $OPS/glmm_inputs.py collect --out-dir $A/glmm-out --out $A/glmm-summary.json
```

The job runs the registered image `b15584f3...` with `glmm.R` (200 refits, seed 42). It
fits `primary.csv` (base: the registered reading) and `secondary.csv` (base plus the
completed blocks, reported beside it) in parallel.

- **Exit codes.** Each fit's exit code goes to `<set>.exit`, and the container exits 91 if
  either fit failed.
- **Convergence.** `glmm-summary.json` reports `full`, `reduced`, `lrt_task_harness` and
  the bootstrap counts exactly as `glmm.R` writes them. It adds a note when the bootstrap
  came from a full fit that did not converge, or includes refits that did not converge.
- **Package lock.** It checks the copied `/opt/q2/r-packages.json` against `abb8871d...`.

## 10. Section 15 assembler (Slurm CPU, about one analysis)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step s15 assemble_s15.py --export $X --plan $PLAN --records $A/a1.jsonl "${RUNS[@]}" --costs $A/costs.json --analysis-dir $A --report-guarded $A/report/report-guarded.json --out $A/s15.json); echo $J
tail -2 $A/logs/s1a-s15-$J.out
```

## 11. Final provenance (seconds)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
IN=(); for f in $PLAN $A/dr0-*.json $A/rescore-jobs.json $A/rescore-*/rescored.jsonl $A/rescore-*/receipt-*.json \
  $A/merged-*.jsonl $A/a1.jsonl $A/rescore-coverage.json $A/costs.json $A/report/*.json $A/identity/identity.json \
  $A/first-divergence.json $A/glmm-inputs/* $A/glmm-out/glmm-*.json $A/glmm-out/*.exit $A/glmm-out/r-packages.json \
  $A/glmm-summary.json $A/s15.json; do IN+=(--input $f); done
for VM in $VMS; do for f in manifest.json episodes.jsonl lane-receipt.json; do IN+=(--input $R/runs/$VM/$f); done; done
python3 -E -s -B $OPS/provenance.py --export $X --plan $PLAN --ops-commit $OPSC "${IN[@]}" --out $A/provenance.json; echo "exit=$?"
```

## 12. Evidence (from the Mac)

Copy only metadata, counts, digests, receipts and reports into
`program/evidence/<date>/q2-stage1-analysis/`:

- `env.sh`, `provenance-pre.json`, `provenance.json`;
- `dr0-*.json`, `dr0-exits.txt`;
- `rescore-jobs.json`, `rescore-*/receipt-*.json`, `rescore-*/rescored.jsonl`,
  `rescore-coverage.json`;
- `merged-*.jsonl`, `a1.jsonl` (the committed record fields plus the corrected and offline
  scores);
- `costs.json`;
- `report/`, `identity/identity.json`, `first-divergence.json`;
- `glmm-inputs/`, `glmm-out/{glmm-*.json,*.exit,r-packages.json,receipt-*.json}`,
  `glmm-summary.json`;
- `s15.json`;
- `logs/`.

Never copy step logs, captures, replies or stdout tails. An independent verifier then
re-runs steps 4 to 10 from the copied inputs and compares the SHA-256 of `report.json`,
`report-guarded.json`, `costs.json`, the merged files and `s15.json` with
`provenance.json`.

## Disclosures that go with the outputs

- **Deviation (D59 (i)).** The report runs through `run_report.py`, which widens the
  estimator outcome check to [0, 1] and NaN. `identity.json` shows which case applies:
  byte-identical, or only the fractional outputs changed.
- **Operator rules (D59 (ii)), when the data are incomplete.** These are the guard's
  readings in `guard.json` and `report-guarded.json`.
- **Operator steps (D59 (iii)), each with its command above:**
  - offline rescoring `--time=08:00:00`, with coverage and live-score fallbacks;
  - replay mismatches shown beside the flips;
  - first divergence: base tasks, scored final records, final attempt;
  - the section 15 assembler;
  - the GLMM input writer and the primary-as-registered reading, with exit codes and the
    R package digest;
  - provenance;
  - the truncation label read on all final records, with a base-only share as a
    description;
  - the checker-noise set stated.
- Every output is labelled "not externally anchored" (ANCHOR-UNAVAILABLE).

## Where each section 15 item comes from

| Section 15 item | File and key |
|---|---|
| Every section 9 estimand with intervals, primary and secondary, raw verdicts, per size and pooled | `report-guarded.json`: `primary`, `secondary_base_plus_completed_extension` |
| Corrected verdicts | Primary: `report-guarded.json` `checker_corrected`. Secondary: `s15.json` `secondary_corrected` |
| Per domain | `report-guarded.json` `per_domain` (primary raw). `s15.json` `per_domain` (primary corrected, secondary raw and corrected) |
| DR0 | `dr0-*.json`, `s15.json` `dr0_per_job`, `guard.json` `completeness.jobs` |
| DR1, DR2, DR5 | `report-guarded.json` (`primary`). Guard readings in `guard.json` `readings` |
| DR3 | `s15.json` `dr3` (from `report-guarded.json`) |
| DR4 | `report-guarded.json` `DR4` |
| DR-A | `report-guarded.json` `external_anchor` (ANCHOR-UNAVAILABLE, "not externally anchored") |
| P1-P5 | `report-guarded.json` `predictions` (P5 is not evaluated without `--costs`) |
| Infrastructure losses by type and cell (finals and attempts; per size and harness, size and session, size, harness and session) | `report-guarded.json` `cells`, `cells_by_size_session`, `cells_by_size_harness_session`, `attempts` |
| IRError and metric-exception counts per (size, harness) | `report-guarded.json` `cells` (`ir_errors`, `metric_exceptions`) |
| Restarts per episode | `s15.json` `restarts_per_episode` |
| Observations on retry, slow or undelivered, per episode and per cell | Per cell: `report-guarded.json` `cells*` (`observations_*`). Per episode: `s15.json` `observations_per_episode` |
| Cap truncations | `report-guarded.json` `cells` (`status_cap_truncated`). `s15.json` `losses_by_task` |
| Metric-exception-missing sensitivity | `report-guarded.json` `sensitivity_metric_exception_missing` |
| Per-session counts, postconfig replies, failures and server errors (D56) | `report-guarded.json` `cells_by_size_session`, `cells_by_size_harness_session`, `attempts` |
| Postconfig server-error sensitivity | `report-guarded.json` `sensitivity_postconfig_server_error_missing` |
| Cost card against the central and high prices | `report-guarded.json` `cost_card`. `s15.json` `cost_card_prices`. Output tokens: `s15.json` `output_tokens`. Steps and the termination and success distributions censored at 15: `s15.json` `steps` |
| Truncation rates and label, mediator δ | `report-guarded.json` `truncation`. `s15.json` `truncation` (set stated, base-only description) |
| Uncertified exposure per episode and harness, δ by stratum | `report-guarded.json` `uncertified_exposure`, `delta_by_exposure_stratum`. `s15.json` `uncertified_exposure_per_episode` |
| First divergence | `first-divergence.json` |
| Checker-input-hash discordance, live-versus-offline mismatches | `report-guarded.json` `checker_noise`. Set: `s15.json` `checker_noise_set` |
| Offline rescoring coverage, fallbacks, replay mismatches | `rescore-coverage.json`, `s15.json` `rescoring` |
| Fractional checker scores and their sensitivity | `report-guarded.json` `fractional_score`, `cells*.fractional_scores`. `identity.json` |
| Corrected-verdict flips | `report-guarded.json` `checker_corrected.flips_per_task` (base). `s15.json` `secondary_corrected.flips_per_task`, `rescoring` (split by kind) |
| Flagged-task sensitivity | `report-guarded.json` `sensitivity_flagged_tasks_excluded` |
| Host snapshots and foreign load | `s15.json` `host_snapshots` |
| Anchor | `report-guarded.json` `external_anchor` |
| Offline-setup exclusions with reasons | `s15.json` `offline_setup_exclusions` |
| Failed setup and postconfig replies by type | `s15.json` `setup_and_postconfig_failures` |
| Losses by task (section 10.1) | `s15.json` `losses_by_task` |
| GLMM | `glmm-summary.json`, `glmm-out/glmm-*.json` |
| Provenance | `provenance.json` |
| Every deviation | The disclosures above, `identity.json`, `guard.json` |
