# S1a analysis runbook (q2-stage1-rescoped-v1, D59)

Operator steps for the S1a analysis on the host. These scripts are operator tooling, not
code of record. They import the frozen modules from the read-only export of the freeze
commit `d5f5798` and never change them. D59, with D61 and D62 for the edge cases
D59 leaves open, fixed every rule they apply before any A1 outcome was read. This runbook
supersedes the dry run's runbook and closes the checker's gaps. Each step is listed with its
exact command. Section 15 items and where they come from are at the end.

| Script | D59 | What it does |
|---|---|---|
| `provenance.py` | (iii) | Checks the registration SHA-256 (via `lane.frozen_registration`), the frozen plan digest and the section 20 code of record. Also records the environment, the operator script digests and the input digests. |
| `run_report.py` | (i), (ii), D61 | Runs `analysis.main` with the widened outcome check (`report.json`), then the incomplete-data guard (`guard.json`, `report-guarded.json`). |
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
  The registered `rescore merge` does not check, so step 4 checks before each merge.
  If a step must be redone, move its output aside (for example `mv X X.failed-<slurm id>`)
  and record why. Nothing is deleted.
- **Data handling (section 16).** Step logs, captures, replies and stdout tails stay on the
  host. Only the files listed in step 12 go to `program/evidence/`.
- **Stop conditions.** Stop and record the cause, without patching any frozen file, if any
  of these happens: `provenance.py` exits 3; `run_report.py` exits non-zero;
  `check_identity.py` exits 3; `glmm_inputs.py collect` exits 3 (the image's R package
  lock does not hash to the registered `abb8871d...`); a rescoring or GLMM receipt shows a
  non-zero `exit_status` with no rows written. Any other operator script that exits non-zero
  has written nothing; fix the input it names and run it again.
- **Labels.** `guard.json` `labels` (step 6) is the label of every file of this analysis:
  incomplete or not (D59 (ii), D61), and "not externally anchored" (ANCHOR-UNAVAILABLE).
  `report-guarded.json`, `rescore-coverage.json`, `identity.json`, `first-divergence.json`,
  `glmm-inputs/inputs.json`, `glmm-job.json`, `glmm-summary.json`, `s15.json` and
  `provenance.json` carry it. The registered CLIs' outputs (`dr0-*.json`, `merged-*.jsonl`,
  `a1.jsonl`, `costs.json`, `report.json`, `rescored.jsonl`, the GLMM fits) cannot carry it.
  Two operator records are written before the completeness test exists: `provenance-pre.json`
  (step 1, a check of the frozen inputs before any record is read) and `rescore-jobs.json`
  (step 3, the rescoring jobs' submission). Neither holds an estimate or a count of records.
  These files fall under `guard.json`'s label, and `provenance.json`, which carries it,
  binds each of them by digest (step 11). The evidence README states this (step 12).
- **Order.** Steps 7 to 11 start only after step 6's job has ended with `exit_status=0`.
  Steps 7, 8, 9 and 11 read `guard.json` and refuse, writing nothing, while it is missing
  (the report job still running) or names no guarded report (the report step failed: a stop
  condition). Step 10 reads `report-guarded.json`, which step 6 writes only when it
  succeeds.

## 0. Ship the operator scripts and set the variables

On the Mac, from the verified commit of `ops/s1a-analysis` on `ops/q2-s1a` (replace
`FILL-IN` with that commit; as written the line fails and nothing is shipped):

```bash
OPSC=$(git rev-parse --verify 'FILL-IN^{commit}') &&
git archive --format=tar "$OPSC" ops/s1a-analysis | ssh -o BatchMode=yes fal-h100-01 \
  "mkdir -p /home/kevin/cotcodec-runs/stage0/q2-stage1/ops/$OPSC && tar -x -C /home/kevin/cotcodec-runs/stage0/q2-stage1/ops/$OPSC" &&
echo "$OPSC"
```

On the host (`ssh -o BatchMode=yes fal-h100-01`, in the operator's tmux, bash), write the
environment once. Replace the two `FILL-IN` placeholders first, and edit `COSTVMS` if a job
was refused before any episode ran. `s1a_env_ok` refuses a placeholder left in place, a
commit whose scripts were not shipped, a VM job without a run directory and a `COSTVMS`
entry outside `VMS`; the chain then stops before it creates anything. It also stops if the
analysis directory already exists (write once). Every later step starts with
`. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh`, so each step also
works from a fresh ssh command:

```bash
OPSC=FILL-IN                             # the verified ops commit: its full 40-hex sha, as on the Mac
VMS="1045 1048 1051 FILL-IN"             # the A1 VM jobs that ran, registered order; FILL-IN: A1-4B-S2's
COSTVMS="$VMS"                           # VMS minus a job refused before any episode ran to an end
R=/home/kevin/cotcodec-runs/stage0/q2-stage1
A=$R/analysis/s1a-v1
s1a_env_ok() {
  [[ $OPSC =~ ^[0-9a-f]{40}$ && -d $R/ops/$OPSC/ops/s1a-analysis ]] || { echo "OPSC: not a shipped full sha: $OPSC" >&2; return 1; }
  [[ -n $VMS ]] || { echo "VMS is empty" >&2; return 1; }
  for VM in $VMS; do [[ $VM =~ ^[0-9]+$ && -f $R/runs/$VM/manifest.json ]] || { echo "VMS: no run directory for $VM" >&2; return 1; }; done
  for VM in $COSTVMS; do [[ " $VMS " == *" $VM "* ]] || { echo "COSTVMS: $VM is not in VMS" >&2; return 1; }; done
}
s1a_env_ok && mkdir -p $R/analysis && mkdir $A && mkdir $A/logs && cat > $A/env.sh <<EOF
R=$R
X=\$R/src/d5f57988ab94e0c098feddb744b78b73b5ad88ca
PLAN=\$X/program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json
OPSC=$OPSC
OPS=\$R/ops/\$OPSC/ops/s1a-analysis
A=$A
INPUTS=/home/kevin/cotcodec-runs/stage0/q2-evaluator-mutation/inputs
VMS="$VMS"
COSTVMS="$COSTVMS"
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
python3 -E -s -B $OPS/rescore_jobs.py submit --export $X --analysis-dir $A --inputs $INPUTS "${RUNS[@]}" --out $A/rescore-jobs.json --dry-run
python3 -E -s -B $OPS/rescore_jobs.py submit --export $X --analysis-dir $A --inputs $INPUTS "${RUNS[@]}" --out $A/rescore-jobs.json
```

The first line prints one `sbatch` line per job and writes nothing (`--out` is optional with
`--dry-run`, and it must not exist yet). The second line submits the same commands and
writes `rescore-jobs.json`.

Each job is one `s1a-cpu.sbatch` run in the metric image `2006c1a9...` with
`--time=08:00:00`. The run directory is mounted read-only at `/ro/run`, and the job writes
`$A/rescore-<vm>/rescored.jsonl` and `receipt-<slurm>.json`. The Slurm ids go to
`rescore-jobs.json`. Poll with short commands:

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
squeue -h -o '%i %j %T %M' | grep s1a-rescore || echo none-running
grep -h '"exit_status"' $A/rescore-*/receipt-*.json
wc -l $A/rescore-*/rescored.jsonl
```

**Go on to step 4 only after `none-running` and one `receipt-*.json` in every
`rescore-<vm>/`.** `rescore capture` writes `rescored.jsonl` row by row for the whole job, so
a file exists long before the job ends, and `merge` does not check that the job has ended.
A job that hit its limit or wrote no rows still leaves a receipt.

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
for VM in $VMS; do ls $A/rescore-$VM/receipt-*.json >/dev/null 2>&1 || { echo "rescoring of $VM has not ended (no receipt)" >&2; break; }; test ! -e $A/merged-$VM.jsonl || { echo "exists: $A/merged-$VM.jsonl" >&2; break; }; (cd $X && python3 -E -s -B -m harness.q2_stage1.rescore merge --episodes $R/runs/$VM/episodes.jsonl --rescored $A/rescore-$VM/rescored.jsonl --out $A/merged-$VM.jsonl); done
for VM in $VMS; do cat $A/merged-$VM.jsonl; done > $A/a1.jsonl
python3 -E -s -B $OPS/rescore_jobs.py coverage --export $X --analysis-dir $A "${RUNS[@]}" --records $A/a1.jsonl --plan $PLAN "${DR0S[@]}" --out $A/rescore-coverage.json
```

`rescore-coverage.json` carries the labels (from the same completeness test as the guard
in step 6). For each job it lists:

- scored attempts, and those with a capture;
- rows, matched rows, rows with `*_error` (by field), scored attempts with no row;
- the receipt's `exit_status`.

For the primary and secondary sets it adds:

- how many corrected verdicts came from rescoring and how many fell back to the live score;
- the corrected-verdict flips by task, split into `checker_correction` (the corrected
  comparator applies) and `replay_mismatch` (no correction applies, so the flip is a
  live-versus-offline replay mismatch). This split is disclosed beside the flips. A
  checker-correction flip whose raw replay already differed from the live score is also
  counted under `checker_correction_raw_replay_also_differs` (a subset of
  `checker_correction`).

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
```

Wait for the job to end before step 7. Poll (each line returns at once):

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
squeue -h -o '%i %j %T %M' | grep s1a-report || echo none-running
tail -2 $A/logs/s1a-report-*.out                                 # exit_status=0
```

Go on only after `none-running` and `exit_status=0`. A non-zero exit is a stop condition.

The step writes three files:

- `$A/report/report.json`: `analysis.main` with `estimators._check` widened to [0, 1]
  (D59 (i)). It is absent when the frozen report raises (bug B2): no size holds two
  sessions, or a DR5 share has no finite bound.
- `$A/report/guard.json`: the inputs' digests, the registered argv, the registered error if
  any, `fractional_base_scores`, completeness (DR0 per job from the files and recomputed
  from the records, the jobs present and absent, the sessions per size), every reading
  the guard changed, the `labels` every later output copies, the `read` note and the
  `interpretation` (below).
- `$A/report/report-guarded.json`: the report to read. With complete data it is
  `report.json` plus a `guard` block. With incomplete data the guard changes these
  readings:
  - every output is labelled `incomplete`;
  - a single-session size's session test is `not_estimable`;
  - DR1 is read on the sessions present;
  - DR5 is "not evaluable as registered", and π_9B is shown against both M = 0.13 and
    M = 0.18 as a description only;
  - a size that holds both sessions but has no task with both harness cells scored in both
    (a session-2 job cut after a few episodes) has no π: it is read for π as a one-session
    size, so DR5 is "not evaluable as registered" there too (D62);
  - no p-value is shown from an all-NaN statistic.

  If a size holds two sessions but the registered report raises because a DR5 share has no
  finite bound (`rules.dr5` compares None: for example DR0 at A1-9B-S2 after a few
  episodes, so A1-4B-S2 never runs), `report.json` is absent. `report-guarded.json` is then
  `analysis.report` recomputed with those `rules.dr5` calls returning "not evaluable as
  registered", every other value as the registered code computes it, with the readings
  above. `guard.json` `tolerant_report` counts the calls (D62).

  If no size holds two sessions, the file is the delta-only report: δ and the descriptive
  and infrastructure counts. D_b, D_w, X, π, the X test, DR2, DR5, P1, P2, the session test
  and P3 are then not estimable.

**Read `report-guarded.json`, never `report.json` directly.** On incomplete data
`report.json` still holds every value the guard changed: for example a single-session
size's session p-value of 1/(n+1), or DR5 read against M = 0.13. It is kept for the
identity check (step 7). `guard.json` says so in `read`.

**The guard's readings of D59 (ii)** are fixed in `run_report.py` before any A1 outcome is
read, ratified in D61 and D62, and written to `guard.json` `interpretation`:

| Case | Reading |
|---|---|
| DR0 fired for any A1 job, a registered job has no records, or a size lacks two sessions of scored base records | Every output is labelled `incomplete` |
| A size's session-2 job fired DR0, but the size still holds scored base records in both sessions (cut or failed after its first block) | D61 (a). Labelled `incomplete`; the DR0 masks nothing else: that size's session test (and DR1, for 4B) are read as registered on the data collected, and a `guard.json` reading says so. D59's "that size" is read as the size left with one session: section 11 reports the data already collected as incomplete, and the dry-run checker's B3 handling, from which D59 (ii) was written, names the single-session size |
| A size holds both sessions, but in a set no task has both harness cells scored in both (its X and π are all-NaN) | D62. For π it is read as a one-session size in that set: DR5 is "not evaluable as registered" (π_9B against both M as a description), DR2 carries an `incomplete_note`, `pi_undefined_sizes`, `registered_pi_small_defined` and `pooled_from_sizes` are written, and the DR0 reading says DR5 is not kept. Its session test and DR1 stay as registered |
| A size holds two sessions, but the registered report raises on a DR5 share with no finite bound | D62. `report.json` is absent; `report-guarded.json` is the registered computation with those `rules.dr5` calls returning "not evaluable as registered", then the readings above |
| One size holds one session, the other two | D61 (b). That size's session test (and its harness-by-session and common-share entries) is `not_estimable`; DR1 is read on the sessions it holds; DR5 is "not evaluable as registered", with π_9B against both M as a description; DR2 is kept as the registered code computes it, with an `incomplete_note` (its X test and π_small bound then come from the size with two sessions; π_9B is the registered π_small only when DR1 drops 4B); P1 and P2 read the size with two sessions; `pooled_from_sizes` lists the sizes each pooled estimate averages (pooled D_w, δ and the Bernoulli X average the single-session size's session with the other size's two) |
| No size holds two sessions | The delta-only report above |
| Any statistic with no finite entry | No p-value is read from it |

Rows two to five answer questions D59 leaves open. D61 (a) and (b) ratify rows two and
five, and D62's rows three and four, all fixed before any A1 outcome was read.

## 7. Identity check (Slurm CPU, about one more report)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step identity check_identity.py --export $X --records $A/a1.jsonl --plan $PLAN --costs $A/costs.json --wrapper-report $A/report/report.json --guard $A/report/guard.json --out-dir $A/identity); echo $J
tail -2 $A/logs/s1a-identity-$J.out                              # exit_status=0
```

`$A/identity/identity.json` reports one of three modes:

- `byte identity`: the registered CLI wrote a report, and it equals the wrapper's.
- `fractional`: the registered CLI failed on a fractional base score (bug B1). It was run
  again on the records scored 0, and the reports differ only in `fractional_score` and
  `fractional_scores`.
- Both failed (bug B2): no size holds two sessions, or a DR5 share has no finite bound (step
  6's tolerant recomputation).

`identity.json` carries `guard.json`'s labels. The check refuses, writing nothing, until step
6 has written a complete `guard.json`. Exit 3 stops the analysis.

## 8. First divergence (Slurm CPU, reads step logs on the host)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step divergence first_divergence.py --export $X --plan $PLAN --records $A/a1.jsonl "${RUNS[@]}" --guard $A/report/guard.json --out $A/first-divergence.json); echo $J
tail -2 $A/logs/s1a-divergence-$J.out
```

The output gives counts only: within and between pairs, pooled and per size, the kind at
each step, and the number of step logs read and missing. The set is stated in the file.

## 9. GLMM (writer seconds; fits about 20 min in Slurm)

Write the inputs and submit the fits (`sbatch` returns at once):

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
python3 -E -s -B $OPS/glmm_inputs.py write --export $X --plan $PLAN --records $A/a1.jsonl --guard $A/report/guard.json --out-dir $A/glmm-inputs
python3 -E -s -B $OPS/glmm_inputs.py submit --export $X --inputs-dir $A/glmm-inputs --out-dir $A/glmm-out --guard $A/report/guard.json --out $A/glmm-job.json --dry-run
python3 -E -s -B $OPS/glmm_inputs.py submit --export $X --inputs-dir $A/glmm-inputs --out-dir $A/glmm-out --guard $A/report/guard.json --out $A/glmm-job.json
```

Poll until the job has ended (about 20 minutes; each line returns at once):

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
squeue -h -o '%i %j %T %M' | grep s1a-glmm || echo none-running
ls $A/glmm-out/receipt-*.json && cat $A/glmm-out/primary.exit $A/glmm-out/secondary.exit
```

Only after `none-running` and a receipt in `glmm-out/`, collect:

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
python3 -E -s -B $OPS/glmm_inputs.py collect --out-dir $A/glmm-out --guard $A/report/guard.json --out $A/glmm-summary.json; echo "exit=$?"
```

`collect` refuses, writing nothing, while `glmm-out/` holds no `receipt-*.json`:
`s1a-cpu.sbatch` writes the receipt when the job ends, after both `.exit` files.

The job runs the registered image `b15584f3...` with `glmm.R` (200 refits, seed 42). It
fits `primary.csv` (base: the registered reading) and `secondary.csv` (base plus the
completed blocks, reported beside it) in parallel.

- **Exit codes.** Each fit's exit code goes to `<set>.exit`, and the container exits 91 if
  either fit failed.
- **Convergence.** `glmm-summary.json` reports `full`, `reduced`, `lrt_task_harness` and
  the bootstrap counts exactly as `glmm.R` writes them. It adds a note when the bootstrap
  came from a full fit that did not converge, or includes refits that did not converge.
- **Package lock.** It checks the copied `/opt/q2/r-packages.json` against `abb8871d...`.
  A mismatch is written to `glmm-summary.json` and the collector exits 3: stop (see Rules).

## 10. Section 15 assembler (Slurm CPU, about one analysis)

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
J=$(step s15 assemble_s15.py --export $X --plan $PLAN --records $A/a1.jsonl "${RUNS[@]}" --costs $A/costs.json --analysis-dir $A --report-guarded $A/report/report-guarded.json --out $A/s15.json); echo $J
tail -2 $A/logs/s1a-s15-$J.out
```

## 11. Final provenance (seconds)

Run this only after the Slurm jobs of steps 7, 8 and 10 have ended with `exit_status` 0
(`squeue` shows none of them, and their receipts exist), so that no input is recorded as
missing because it has not been written yet.

```bash
. /home/kevin/cotcodec-runs/stage0/q2-stage1/analysis/s1a-v1/env.sh
IN=(); for f in $PLAN $A/provenance-pre.json $A/dr0-*.json $A/rescore-jobs*.json $A/rescore-*/rescored.jsonl $A/rescore-*/receipt-*.json \
  $A/merged-*.jsonl $A/a1.jsonl $A/rescore-coverage.json $A/costs.json $A/report/*.json $A/identity/identity.json \
  $A/first-divergence.json $A/glmm-inputs/* $A/glmm-job.json $A/glmm-out/glmm-*.json $A/glmm-out/*.exit $A/glmm-out/r-packages.json \
  $A/glmm-summary.json $A/s15.json $A/glmm-out/receipt-*.json $A/dr0-exits.txt $A/env.sh; do IN+=(--input $f); done
for VM in $VMS; do for f in manifest.json episodes.jsonl lane-receipt.json; do IN+=(--input $R/runs/$VM/$f); done; done
python3 -E -s -B $OPS/provenance.py --export $X --plan $PLAN --ops-commit $OPSC --guard $A/report/guard.json "${IN[@]}" --out $A/provenance.json; echo "exit=$?"
```

A pattern that matches nothing (for example a GLMM output that was never written) reaches
`provenance.py` as written. It is recorded under `inputs_missing` and fails no check, so
read that list.

## 12. Evidence (from the Mac)

Copy only metadata, counts, digests, receipts and reports into
`program/evidence/<date>/q2-stage1-analysis/`:

- `env.sh`, `provenance-pre.json`, `provenance.json`;
- a `README.md` that states the labels (`guard.json` `labels`) and that `provenance-pre.json`,
  `rescore-jobs*.json` and the registered CLIs' outputs fall under them (see Rules);
- `dr0-*.json`, `dr0-exits.txt`;
- `rescore-jobs*.json`, `rescore-*/receipt-*.json`, `rescore-*/rescored.jsonl`,
  `rescore-coverage.json`;
- `merged-*.jsonl`, `a1.jsonl` (the committed record fields plus the corrected and offline
  scores);
- `costs.json`;
- `report/`, `identity/identity.json`, `first-divergence.json`;
- `glmm-inputs/`, `glmm-job.json`, `glmm-out/{glmm-*.json,*.exit,r-packages.json,receipt-*.json}`,
  `glmm-summary.json`;
- `s15.json`;
- `logs/`.

Never copy step logs, captures, replies or stdout tails. An independent verifier then
re-runs, from the copied files and each job's committed `episodes.jsonl`, the steps that
read only them: the merges and `a1.jsonl` (step 4), the report (6), the identity check (7)
and the GLMM writer (9). The verifier compares the SHA-256 of the merged files, `a1.jsonl`,
`report.json`, `report-guarded.json`, `guard.json`, `identity.json` and
`glmm-inputs/*.csv` with `provenance.json`. Some steps read files that stay on the host
(section 16): coverage (step 4) and first divergence (step 8) read captures and step logs,
costs (step 5) and the assembler (step 10) read lane run directories and receipts, and the
GLMM fits (step 9) need the registered container. For those steps the verifier checks the
copied outputs (`rescore-coverage.json`, `first-divergence.json`, `costs.json`, `s15.json`,
`glmm-out/glmm-*.json`) against `provenance.json`'s digests, or re-runs them read-only on
the host.

## Disclosures that go with the outputs

- **Deviation (D59 (i)).** The report runs through `run_report.py`, which widens the
  estimator outcome check to [0, 1] and NaN. `identity.json` shows which case applies:
  byte-identical, or only the fractional outputs changed.
- **Operator rules (D59 (ii)), when the data are incomplete.** These are the guard's
  readings in `guard.json` and `report-guarded.json`, and its reading of the cases D59
  leaves open, ratified in D61 and D62 (`guard.json` `interpretation`; the table
  in step 6).
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
