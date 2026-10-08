# q3-dense-headroom-precheck-v2: operation (freeze steps 3-5)

Registration `program/preregistrations/q3-dense-headroom-precheck-v2.md`
(SHA-256 `982e66ba...`, ledger row 12 with hash `a68af989...`,
`git_head_at_freeze` `0a068a1`; frozen in commit `ed5d5a9`; decisions 16-21
accepted in D42 and D44, D42 amends D36 (iii) for the 4B lane). Operated on
2026-10-08 (UTC) on `fal-h100-01` from a fresh clean clone of main at
`ed5d5a9`. The full timeline is `operator-log.txt`.

## Result

| Lane | Job | Outcome | Receipt |
|---|---|---|---|
| Qwen3-0.6B-Base | 859 | COMPLETED 0:0 in 4 min 40 s (limit 12) | `d39ca464...`, `PRECHECK_COMPLETE`, bound to 859 from `job.env`; job 727 **REPRODUCED** exactly; smoke 452 **REPRODUCED** |
| Qwen3.5-4B-Base | 862 | COMPLETED 0:0 in 9 min 17 s (limit 32) | `db56b1da...`, `PRECHECK_COMPLETE`, bound to 862 from `job.env` |

**Combined read** (`scripts/summarise_dense_headroom_precheck_v2.py`, exit 0,
`summary/combined-read.json`, SHA-256 `d656d29f...`): design
**NEGATIVE_CAPABLE_V3** on base **qwen3.5-4b-base**. Lane classes: 0.6B
NOT_VIABLE, 4B NEGATIVE_CAPABLE. The summariser's verbatim stdout:

```json
{"design": "NEGATIVE_CAPABLE_V3", "base": "qwen3.5-4b-base", "lane_classes": {"qwen3-0.6b-base": "NOT_VIABLE", "qwen3.5-4b-base": "NEGATIVE_CAPABLE"}, "requirements": ["a seen-script cross-script condition (D26; not measurable here)", "an entity-controlled question set (D26)", "a new experiment id and the research gauntlet (D26)", "the non-literal floor (D26): 99 percent lower bound of G(MN) on entity-controlled families at least 0.5", "the GO and NEGATIVE statistics computed on the entity-controlled set, not only reported beside it (lexical confound PRESENT)", "anchor masking or a lexical-overlap covariate (entity control INSUFFICIENT)", "H2 re-tested under K1's bounds on the v3 audit read (the development read's H2 is POINT_ONLY)"]}
```

Under the registration a K1 v3 with a NEGATIVE region may be designed on
Qwen3.5-4B-Base, with all seven requirements above. A K1 v3 still needs a new
experiment id, the research gauntlet and the program owner's decision (D26).
This is a measurement on the development partition only (20 questions, 20
passage clusters). It is not a K1 result, positive or negative, and it does
not say whether an indexer loses more cross-script recall than its target.

## Validity gate (D36, decision 19)

The registered `harness.dense_headroom_v2.v1_reproduction` compares v2's 0.6B
receipt with v1's job-727 receipt (`bfe4a7c3...`). Result: **REPRODUCED**.
All 3,128 numeric leaves match with a largest gap of exactly 0.0, against the
1e-6 tolerance. All 1,029 other leaves are equal and there are 0 mismatches.
The compared fields are `report`, `decisions`, `coverage`, `artifact_counts`,
`selectors`, `attention_layers` and `hashes.dev_artifact_sha256`, which is
`c1c455d8...`, equal to v1's. K1 smoke 452 was recomputed:
**REPRODUCED** against a tolerance of 0.5 points:

| Selector | v2 job 859 | smoke 452 |
|---|---:|---:|
| T:hs | 26.4506 | 26.4506 |
| T:mp | 26.0806 | 26.0806 |
| T:hm | 26.2663 | 26.2663 |
| rand | 12.4803 | 12.4803 |

The gated gaps are 3e-7 to 7e-7 points; U is 66.5404 and Uk 9.7459.
The filler applied both gates again before filling the 4B lane, and the
summariser applied the job-727 gate a third time (`v1_job_727_reproduction`
in the combined read). The operator's read (`lane-0p6b-859/gate-read-859.json`,
`helpers/read-gate.py`) came first and only calls the registered function.

## Lane statistics (development partition, target hs; 99 percent cluster-bootstrap intervals, 20 clusters)

| Statistic | Qwen3-0.6B-Base (859) | Qwen3.5-4B-Base (862) |
|---|---|---|
| H1 on MN (dense minus random recall, points) | 20.80 (17.40 to 23.99) | 44.39 (38.60 to 49.90) |
| H1 on CX (registered H1_CX, chosen target hs) | 12.25 (8.98 to 15.59) | **42.15 (35.76 to 48.20)** |
| H1 on ML (literal) | 25.81 (23.33 to 28.56) | 52.31 (49.11 to 55.65) |
| Delta_T (MN minus CX) | 8.55 (6.85 to 10.30) | 2.23 (0.44 to 3.87) |
| H2a: CX multiple-choice accuracy (%) | 31.43 (17.14 to 46.43) | 49.64 (34.64 to 65.00) |
| H2b: needle present minus absent (points) | -3.93 (-12.14 to 3.57) | 8.57 (-9.29 to 26.43) |
| MN / needle-absent / no-haystack accuracy (%) | 49.6 / 35.4 / 36.4 | 50.0 / 41.1 / 46.8 |
| `h2_status` | FAIL | POINT_ONLY |
| `lane_class` | NOT_VIABLE | **NEGATIVE_CAPABLE** |
| K1 v1 pre-step (reported unchanged) | ESCALATE_OR_STOP | ESCALATE_OR_STOP (H1 NEGATIVE-ready, H2b bound not above 0) |
| Anchored share (Wilson 95%) | 0.50 (0.30 to 0.70) | 0.50 (0.30 to 0.70) |
| Literal selector xi_rel, all families (hs, mp) | not evaluable | 0.265, 0.274 |
| Literal selector xi_rel, controlled families (hs, mp) | not evaluable, 0.357 | 0.235, 0.245 |
| `lexical_confound` / `entity_control` | NOT_EVALUABLE / NOT_EVALUABLE | **PRESENT / INSUFFICIENT** |
| `null_calibration` (hs, mp) | NOT_EVALUABLE, NOT_EVALUABLE | **CENTRED, CENTRED** |
| Controlled MN headroom | 21.47 (lower 16.92) | 46.10 (lower 37.53) |
| `floor_candidate` | NOT_VIABLE | **VIABLE** |
| Spearman, needle fertility vs CX headroom (7 languages) | -0.82 | -0.89 |
| `fertility_association` | STRONG | STRONG |

The 0.6B column is equal to v1's job-727 receipt, as the gate shows. On the
4B lane:

- **Nulls.** At every sigma that passes V1, the seed-mean |xi| is at most
  0.024 points (hs) and 0.085 points (mp), and |xi_rel| is at most 0.006.
  The reach rule is met at sigma 0.7 for hs (English ML loss 2.57 points) and
  sigma 1 for mp (4.83 points).
- **Floor.** The literal selector's controlled G(MN) point is 0.237. At sigma
  0.7, a V1-adequate null with a 2.57-point English ML loss has a controlled
  G(MN) whose 99 percent lower bound is 0.932.
- **Headroom by pair.** CX headroom ranges from 26.2 (ka>en) to 55.0 (en>ko)
  points. MN headroom on the English-needle pairs is 50.8.

## The 4B lane's attention backend, signals and time

- **Backend (decision 18, D42 (i); descriptive, not gated).** cuDNN's
  attention was off, and flash, memory-efficient and math attention were on.
  `attention_backend_check` ran on unit `c320-q0` and took 47.2 s. The
  largest differences from cuDNN's attention were 1.152 points of recall and
  0.0111 in an option score. Budgets, largest selections, tie counts and the
  answer were the same. These figures match Slurm 810's. The job-727 gate
  does not cover this switch, because the 0.6B lane never makes it.
- **Signals (decision 17).** Signals were blocked in every thread from the
  start. 64.8 s in, the guard found the OS-level SIGUSR1 and SIGTERM handlers
  replaced (Triton's LLVM, as in job 730) and repaired them. The job finished
  before Slurm's SIGUSR1, so no signal was received and the continuation rule
  did not arise.
- **Time.** Measured per-unit times by stage, with D44's largest per-unit
  estimate in brackets:
  - A-main: 231.6 s, 0.53 s per unit [0.90]
  - B-absent: 122.6 s, 0.44 s per unit [0.66]
  - C-literal: 41.9 s, 0.26 s per unit [0.25]
  - D-nohaystack: 82.5 s, 0.29 s per unit [0.34]

  Statistics took 0.9 s. In the process, start-up before the first unit
  took 63.6 s: the start-up checks, derivation (4.5 s), model load (7.0 s)
  and the backend check (47.2 s).
  Evaluation and statistics took 479.5 s, against the registered estimates of
  769 to 824 s. The job ran 555 s of its 29 useful minutes. The 74 chunks took
  2.2 to 16.2 s each (job 730 took about 61 s per chunk). The GPU was at 27-100
  percent when sampled (`lane-4b-862/observe-862.txt`).
- **Determinism.** Warn-only (decision 9). The development artifact is
  `b5210f79...`, equal to job 730's and to both timing jobs'. Contexts run
  from 49 to 10,481 tokens, with 66 tail bytes dropped.

## What ran

| Step | Slurm | What | Outcome |
|---|---|---|---|
| 3 | - | Fresh clone of main at `ed5d5a9` (`~/cotcodec-runs/stage0/q3-dense-v2/lanes-repo`) | clean; `preregister verify` exit 0, `check-chain` 12 rows PASS, 27 tabled files OK |
| 3 | 855 | Image build from the clone (CPU only) | `sha256:500f3b02...`, source tar `53458dd1...`, label `ed5d5a93`; library versions identical to v1's image 723 |
| 3 | 856 | v2 CPU doctor in that image, `--network none`, no GPU | DENSE_V2_DOCTOR_PASS, 12/12; code digests equal the table |
| 4 | 859 | 0.6B lane, orx node `72c5f6c4` (commit `253ad85`), run `391e80aa`, submitted once | receipt `d39ca464...`; both gates REPRODUCED |
| 4 | 862 | 4B lane (`--small-lane-receipt` 859), orx node `e312036d` (commit `98a98a9`), run `a3fae5af`, submitted once | receipt `db56b1da...` |
| 5 | - | `scripts/summarise_dense_headroom_precheck_v2.py` from the clone | exit 0; NEGATIVE_CAPABLE_V3 on qwen3.5-4b-base |

Both lane manifests were filled on the host from the clone by the tabled
filler. Each differs from its template only in the four `FILL-*` values and
has its own exclusive slot-0 claim (`fill-claims/`). Each passed the
submitter's dry run and test-only run before its orx node submitted it
(`orx exp run <node> --backend ssh --host fal-h100-01`, the registered path;
never `orx --backend slurm`). Each orx node commit adds only `node.yaml` and
the byte-identical filled manifest. The node branches and their worktrees
(`cotcodec-wt-orx-q3-dense-v2-0p6b`, `cotcodec-wt-orx-q3-dense-v2-4b`) are
local and not pushed. Each run root holds exactly one job directory, its
claim and its `slurm-N.out`. No re-run or continuation was filled, and no
filled manifest was submitted twice.

## GPU-hours

| Job | Used (`job.env` to `termination.env`) | Charged (registration rule) | Lane cap |
|---|---:|---:|---:|
| 859 (0.6B) | 279 s = 0.0775 | 6 min = 0.1000 | 12 min, 0.20 |
| 862 (4B) | 555 s = 0.1542 | 11 min = 0.1833 | 32 min, 0.5333 |
| Lanes total | 0.2317 | 0.2833 | 0.7333 |
| Timing 766 (before the freeze) | 205 s = 0.0569 | 5 min = 0.0833 | 0.10 |
| Timing 810 (before the freeze) | 162 s = 0.0450 | 4 min = 0.0667 | 0.10 |
| v2 total | 0.3336 | 0.4333 | 0.933 (D36's cap 1.5) |

Slurm reports RunTime 00:04:40 and 00:09:17. Jobs 855 and 856 were CPU only.
The summariser's `gpu_usage` gives the same elapsed and charged minutes and
`claim_problems: []` for both lanes. With v1's 0.4189, the dense pre-check has
used 0.7525 GPU-h, far below 8. Slurm records: `slurm-records.txt`.

## Notes

- **Content.** The lane receipts carry the registered per-question entity
  anchors, as v1's job-727 receipt did. These are isolated capitalised words
  and digit runs shared by a question and its passage, keyed by source URL.
  The bundle copy, development artifacts, chunk files, Triton cache, docker
  inspect records and `system.txt` stay on the host, with their SHA-256
  digests in each lane's `host-files-sha256.txt`. No passage, question or
  answer-option text is committed.
- **Byte-identical copies.** 33 evidence files are byte-identical to the
  host originals by SHA-256: both receipts, every `job.env`,
  `termination.env`, `gpu-prolog.env`, manifest, command, provenance and
  model verification, container logs, development-artifact digests,
  `slurm-N.out`, fill claims, both orx logs, the build and doctor receipts,
  the combined read and both filled manifests. Host files named `*.env` are
  stored here as `*.env.txt`, with content unchanged.
- **Operator differences from v1's procedure** (none breaks a registered rule):
  - The doctor launcher wraps `docker run` in `bash -c` so the Slurm step
    prints its own job id. Its flags are those of the v2 build evidence's
    `run-doctor-in-image.sh`.
  - The operator read both gates with `helpers/read-gate.py` before filling
    the 4B lane. This is an extra read, not a registered step; the filler and
    the summariser applied the gates themselves.
  - A read-only observer sampled job 862 every 30 s.
- **Unverifiable Slurm ids.** Ids 857, 858, 860 and 861 were purged before
  they could be read. The pattern of two ids before each lane job matches
  the two `--test-only` calls per lane, as with v1's 725/726 and 728/729.
- **orx version.** orx 0.2.2 printed an "outdated" notice; it was not
  updated.

## Files

| Path | What |
|---|---|
| `operator-log.txt`, `README.md` | Timeline and summary |
| `clone.txt`, `preregister-verify.txt`, `code-table.sha256`, `inputs-check.txt` | Fresh clone, verify, check-chain, the 27 tabled digests and the inputs |
| `image/` | Build 855: submit record, receipt, versions, Slurm output, provenance checks, scontrol |
| `doctor/` | The launcher, the doctor receipt (`0240cfe3...`) and log, scontrol 856 |
| `states/` | squeue and nvidia-smi before the clone, the build, the doctor, each fill and each submission, and after the run |
| `filler/` | Filler outputs and exit codes, both filled manifests, their diffs against the templates, dry-run and test-only records |
| `fill-claims/<lane>/after-0.json` | The lanes' fill claims (copies of `<run root>/fill-claims`) |
| `lane-0p6b-859/`, `lane-4b-862/` | `job.env`, `termination.env`, `gpu-prolog.env`, `manifest.json`, `command.json`, provenance and model verification, container doctor and log, `slurm-N.out`, `receipt.json`, `dev-artifact.sha256`, the orx run log (`ORX_RESULT ... exit=0`), scontrol, `host-files-sha256.txt`; the gate read (859); observations (862) |
| `summary/` | The summariser's command, stdout, stderr, exit code and `combined-read.json` |
| `helpers/` | Operator scripts: state snapshot, poll, collection, gate read, observer |
| `slurm-records.txt` | Slurm records and the GPU-job list |
