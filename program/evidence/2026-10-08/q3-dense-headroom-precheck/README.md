# q3-dense-headroom-precheck-v1: operation (freeze steps 3-5)

Registration `program/preregistrations/q3-dense-headroom-precheck-v1.md`
(SHA-256 `94520a99...`, ledger row hash `0533bf7f...`, `git_head_at_freeze`
`c2768e1`, frozen in commit `a369e6d`; design decisions accepted and four
amended in D32). Operated on 2026-10-08 (UTC) on `fal-h100-01`. The full
timeline is `operator-log.txt`.

## Result

| Lane | Job | Outcome | Receipt |
|---|---|---|---|
| Qwen3-0.6B-Base | 727 | COMPLETED 0:0 in 4 min 38 s (limit 9) | `PRECHECK_COMPLETE`; K1 smoke 452 **REPRODUCED** |
| Qwen3.5-4B-Base | 730 | FAILED 137:0 at its 21-minute limit (hard stop); no signal checkpoint | none; the lane is void and **INCOMPLETE** |

**Combined read: not written.** The registered summariser exited 2 on the
0.6B receipt (`summary/`): `the receipt's Slurm job is not its job
directory`. Under the registration's combined rule (INVALID first, then
INCOMPLETE when a lane lacks a completed, non-void receipt) the read is
INCOMPLETE: the 0.6B lane reproduced smoke 452, and the 4B lane has no
receipt and no minutes left under this id. No base, no K1 v3 design and no
stop is read. More GPU time, or a repaired summariser, is a new experiment
id decided by the program owner.

The 0.6B lane's registered per-lane decisions (from its receipt, not a
combined read): `lane_class` NOT_VIABLE, `h2_status` FAIL,
`lexical_confound` NOT_EVALUABLE, `entity_control` NOT_EVALUABLE,
`null_calibration` NOT_EVALUABLE for hs and mp, `floor_candidate`
NOT_VIABLE, `fertility_association` STRONG. On 20 development passage
clusters (99 percent cluster-bootstrap intervals):

| Statistic (0.6B, target hs) | Point | 99% interval |
|---|---:|---|
| H1 on MN (dense minus random recall, points) | 20.80 | 17.40 to 23.99 |
| H1 on CX (registered H1_CX, chosen target hs) | 12.25 | 8.98 to 15.59 |
| H1 on ML (literal) | 25.81 | 23.33 to 28.56 |
| Delta_T (MN minus CX) | 8.55 | 6.85 to 10.30 |
| H2a: CX multiple-choice accuracy (%) | 31.43 | 17.14 to 46.43 |
| H2b: needle present minus absent (points) | -3.93 | -12.14 to 3.57 |

H1_CX is at least 10 but H2b's point is below 5, so `h2_status` is FAIL and
the lane is NOT_VIABLE. K1 v1's development pre-step reads ESCALATE_OR_STOP.
Half of the 20 questions are entity-anchored (Wilson 95 percent 0.30 to
0.70). The null verdicts are NOT_EVALUABLE because xi_rel is not evaluable
at sigma 0.25; English ML loss reaches 2.5 points at sigma 0.7 (3.53 hs,
3.21 mp). Spearman of needle fertility against CX headroom over the seven
held-out languages is -0.82. These are development-partition descriptions on
one base; they are not a K1 result and not the experiment's read.

## What ran

| Step | Slurm | What | Outcome |
|---|---|---|---|
| 3 | 723 | Image build from a fresh clone of main at `a369e6d` (CPU only) | `sha256:60e8d442...`, source tar `fc386fae...` |
| 3 | 724 | Dense CPU doctor in that image, `--network none`, no GPU | DENSE_DOCTOR_PASS, 7/7; code digests equal the table |
| 4 | 727 | 0.6B lane, orx node `7c344837` (commit `38cf069`), submitted once | receipt `bfe4a7c3...` |
| 4 | 730 | 4B lane, orx node `51d32d53` (commit `c84c9aa`), submitted once | no receipt |
| 5 | - | `scripts/summarise_dense_headroom_precheck.py` from the clone | exit 2 |

Both lane manifests were filled by the tabled filler on the host from the
clone (only the four `FILL-*` values differ from the templates), each with
its exclusive slot-0 fill claim (`fill-claims/`), and passed the submitter's
dry run and test-only run before their orx nodes submitted them. The 4B lane
was filled with `--small-lane-receipt` pointing at the 0.6B receipt. After job
730 the filler refused both a re-run ("-1 of 21 minutes remain") and a
continuation ("did not end with a confirmed signal checkpoint"), writing
nothing.

## Findings for the program owner

1. **The summariser cannot accept any receipt these jobs produce.** The entry
   point records `slurm_job_id` from `SLURM_JOB_ID` inside the container, and
   `infra/slurm/host-single-node/docker-research.sbatch` does not pass that
   variable into the container, so the receipt's `slurm_job_id` is null (the
   K1 v2 probe receipt was null the same way). The summariser's `check_job`
   requires it to equal the job directory's name. This check is not among the
   registration's void rules; job 727 meets every one of them (COMPLETED 0:0,
   provenance PASS, ORX_RESULT exit 0, its claim and minutes). The
   summariser's tests build receipts with the field already set to the job
   directory's name, and the doctor never passes an entry-point receipt to the
   summariser, so neither caught it.
2. **The 4B lane needs several times its registered minutes.** Stage A chunks
   (16 units) took about 61 s each after a 2-minute start-up: 18 of 74 chunks
   in 20 minutes, against an estimate of 11 minutes for the whole lane. During
   sampling the GPU was idle (0 percent in 10 samples) and the job's python
   process held one CPU core at 94-98 percent
   (`lane-4b-730/progress-observations.txt`). The cause was not investigated.
3. **The 4B workload did not act on SIGUSR1.** Two chunks were saved after
   the signal was due and no interrupted receipt or marker was written; the
   batch script's hard stop killed the container
   (`reason=signal_USR1_checkpoint_timeout`). The CPU doctor's interrupt test
   runs the tiny hybrid on CPU with flash-linear-attention blocked, as a child
   process rather than a container's PID 1, so it does not cover this path. The cause was not
   investigated.
4. **Charging.** Job 730 used 1,230 s of GPU time, inside its 21-minute Slurm
   limit and 0.35 GPU-h cap; the registration's charge rule (minutes rounded
   up, plus one) charges it 22 minutes (0.367 GPU-h).

## GPU-hours

| Job | Used (job.env to termination.env) | Charged (registration rule) | Cap |
|---|---:|---:|---:|
| 727 (0.6B) | 278 s = 0.0772 | 6 min = 0.1000 | 0.15 |
| 730 (4B) | 1,230 s = 0.3417 | 22 min = 0.3667 | 0.35 |
| Total | 0.4189 | 0.4667 | 0.50 |

Jobs 723 and 724 were CPU only. Slurm records: `slurm-records.txt`.

## Notes

- **Deviation.** The binding CPU doctor ran the source baked into the image
  (`/workspace/cotcodec` at `a369e6d`) with the flags of the earlier
  `run-in-image.sh`, but without mounting a worktree, so it exercised the
  image itself (`doctor/run-doctor-in-image.sh`).
- **Content.** The lane receipt contains the registered per-question entity
  anchors: isolated capitalised words and digit runs shared by a question and
  its passage, keyed by the question's FLORES source URL. No passage,
  question or answer-option text is committed. The development artifacts
  (token ids derived from Belebele), evaluation chunks, the bundle copy, the
  Triton cache, docker inspect records and `system.txt` stay on the host;
  their SHA-256 digests are in each lane's `host-files-sha256.txt`.
- Lane files named `*.env` on the host are stored here as `*.env.txt`,
  content unchanged. The orx logs are the host's
  `~/.orx/runs/<run>/log` files. The orx node branches
  (`orx/q3-dense-pre-check-0-6b-lane-q3-dense-headroom-p`,
  `orx/q3-dense-pre-check-4b-lane-q3-dense-headroom-pre`) are local and not
  pushed.
