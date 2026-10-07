# serving-throughput-probe-v2: operations evidence (2026-10-07)

Run of the frozen registration
`program/preregistrations/serving-throughput-probe-v2.md` (ledger row in
`ledger-row.json`, sign-offs D19 and D21) on `fal-h100-01`. Infrastructure
evidence only ("admission pass"); no number here is a scientific result.

## Outcome (as `project` labelled it)

`ops/project.stdout.txt`: `{"attribution": {"dummy-control": "pid", "real": "pid"}, "q2": "rescope-before-gauntlet", "x1": "pass"}`, exit 0.

| Line | Outcome | Key numbers |
|---|---|---|
| Job A (Slurm 466) | accepted, `complete`, not eager | G0.0-G0.4 pass; G0.5-G0.9 pass in both phases; all 16 points valid on their first attempt (r3 `valid-flagged`, `front-end-bound`, API server 107% CPU); no rerun, no cut, no signal |
| Control X1 | `pass` | identity: a1a/x1-a1 96 of 96 and r1/x1-r1 240 of 240 requests sent identical prompt token ids; open-loop delta 2.66% (threshold 5%); replay mean-latency delta 2.71% (8%); replay delta SE 4.00% (5%); A1 seeds 3 of 3 valid, range 1.82% (5%); same-engine replicate r1b used, delta to r1 0.80% (within 8%) |
| Q2 projection | `rescope-before-gauntlet` | total 431.51 GPU-h (rescope line 90): 4B 55.28, 9B 55.28, 27B 239.36 (x4.5, unmeasured rule), 35B-A3B 81.58 (x1.5, unmeasured rule); every cell binds on the closed loop; no cell over `max_model_len` |
| Q1 projection | `not-projected` | "v2 registers Q2 cells only; Q1 stays with serving-throughput-probe-v1" (v1: `within-cap`, 2.92 and 10.21 GPU-h with its x1.5 penalty) |
| A1 noise | multiplier 1.0, `stable` | a1a 2.523, a1b 2.560, a1c 2.569 req/s; range 1.82% (limit 10%) |
| Front-end (F1) | not applied | f1/a1a ratio 1.031 (PNG faster; correction only when PNG is more than 10% slower); no `front-end-uncorrected` flag |
| Attribution | pid mode, both phases | basis "container-namespace PIDs in the engine's process tree"; all 822 compute-process listings were readable; 777 listed one process, always the engine's own EngineCore (PID 481 real, 3764 dummy), and 45 listed none |

## Q2 cells (9B rung; the 4B rung is identical)

| Harness | Observation | Closed loop | Open loop | Binding | Largest context |
|---|---|---:|---:|---|---:|
| H1 (T=15, V=40) | screenshot | 0.752 | 0.667 | closed loop | 13,470 |
| H1 | accessibility tree | 1.129 | 1.023 | closed loop | 19,614 |
| H2 (T=100, V=20) | screenshot, thinking | 24.105 | 21.648 | closed loop | 74,188 |
| H2 | accessibility tree, thinking | 29.295 | 21.648 | closed loop | 80,332 |

Profiles: H1 from r1 and r2; H2 from r3 plus the thinking penalty
16.81 s (r4 step 19 at 47.58 s minus r3 step 19 at 30.77 s) and, for the
accessibility-tree cell, an accessibility penalty of 10.38 s. Open-loop
reference: a2 at 3.153 req/s (8,205 prompt tokens, 300 output). The 4B and 9B
rungs alone total 110.56 GPU-h, above the 90 GPU-h line, so the decision does
not rest on the unmeasured 27B and 35B-A3B multipliers. Sensitivity table
(`projection-v2.json`): 65.95 GPU-h (T 15, t_env 1.5 s, V 40) to 656.86 GPU-h
(T 100, t_env 4.0 s, V 20); every row with T of 50 or 100 is above 90.

## Reservation and memory (design decisions 4 to 6)

| Phase | G0.8 | G0.9 reservation | Engine (own) | Unattributed | Later device peak |
|---|---|---:|---:|---:|---:|
| real | empty listing, 1 MiB, 0% | 75,653 MiB | 75,642 MiB | 11 MiB | 76,457 MiB (from r1 on) |
| dummy-control | empty listing, 0 MiB, 0% | 75,325 MiB | 75,314 MiB | 11 MiB | 75,327 MiB |

The warm-up reached 75,653 MiB, above the 74,563 MiB the registration names for
device mode, but not the engine's later plateau: the real engine grew 804 MiB
more under r1 and stayed at 76,457 MiB (v1's plateau was 76,611). That is below
the pid-mode flag line (own reservation plus 2,048 MiB, 77,690 MiB) and the
device line (77,701 MiB), so no point carries `own-footprint-above-reservation`
and every contamination check passed. The lane prolog recorded the GPU as
exclusive (`gpu-prolog.env`, empty `gpu-compute-apps-prolog.csv`).

Design decision 25 left open which PIDs NVML lists inside the lane container.
This run observed the container-namespace case: the engine's PID resolved in its
process tree, and no host-namespace PID appeared. The detection guarantee is
therefore "a listed foreign process at any size; one NVML does not list only
through unattributed memory above the reservation's plus 1,024 MiB". One run on
an otherwise idle GPU cannot show whether NVML would list another container's
process.

## GPU time (Slurm `scontrol`; `sacct` accounting is disabled on this host)

| Line | Job | Elapsed | GPU-h | Cap |
|---|---|---:|---:|---:|
| Overlay build (cu129) | 464 | 00:00:44 | 0.0122 | 10 min / 0.167 (D19) |
| Job A | 466 | 00:28:23 | 0.4731 | 60 min / 1.0 (D19) |
| v2 total | | | 0.4853 | 1.167 (D19) |
| v1 total (v1 README) | | | 0.6661 | |
| Serving probe, v1 + v2 | | | 1.1514 | registration bound 1.833 |

Both records were captured live as each job left the queue
(`ops/slurm-records.txt`). Both jobs: `JobState=COMPLETED`, `ExitCode=0:0`. Job
A's lane `termination.env`: `reason=completed`, `exit_code=0`,
`checkpoint_ready=false` (no signal).

## Provenance

- Code revision X = freeze commit `1141d9442b9c78233176f558fe8870046ab2fb8f`
  (origin/main at clone time), fresh clone at
  `~/cotcodec-runs/stage0/serving-throughput-probe-v2/checkout`. Before the
  build, on the host: contract SHA-256 `9224ccdc...257a` and probe code digest
  `64493671...12af6` equal the registration, and `preregister.py verify`
  returned the ledger row (hash `52cd6a84...df44`, file SHA-256
  `19a9f5b5...d4d9`). G0.0 verified the same in the image. The 162 v2-probe,
  manifest, overlay and archive tests passed in the clone.
- Source capsule `0e9c210c92b3e5b1cc363588f23e6532d08344b2203ac76ba2b27f6e77844516`
  (`capsule/source-receipt.json`): schema 3, 1,593 files, `worktree_clean:
  true`, git tree `dfc1f7b6...`. The 27 `.agents/skills` links are recorded as
  omitted under the reviewed rule (`omitted_symlinks_sha256 083d40f1...`); the
  clone was not modified (v1's `git rm` workaround was not needed).
- Base image `vllm/vllm-openai@sha256:b18abb2d...` (image ID `sha256:423783aa...`,
  label commit `db9527a4...`), already on the host. Overlay image
  `sha256:a59d7782755ac7db3e5ffdeaa1dd023af169b0ed6a5e04213ebbecbc7d5c30fc`
  (`overlay/build-receipt.json`, SHA-256 `8ac3846f...ab87d`): torchcodec 0.17.0
  removed, provenance PASS, `plan-job-a-v2.json` made from contract
  `9224ccdc...`, `vllm-args-doctor-v2.json` `pass: true` with both v2 payload
  checks.
- Manifest rendered by `render_serving_probe_v2_manifest.py` outside the clone
  (`manifests/a.yaml`); dry-run 1.0 GPU-h, `--time=01:00:00`,
  `--signal=B:USR1@180`; test-only exit 0.
- Runtime: the image's forward-compatibility `libcuda.so.575.57.08` on the R570
  host driver (`cuDriverGetVersion` 12090); G0.3 normalized error 0.00281;
  G0.5 ready in 104 s (real) and 62 s (dummy); G0.6 image tokens 2,042
  (expected 2,040). Engine facts, both phases: weights 17.66 GiB, KV cache
  51.2 GiB (1,634,030 tokens), CUDA graphs on, no eager fallback, no `/tmp`
  mappings.
- `project` admitted job A with no reasons; its recorded summary SHA-256
  `665b952c...4bb4` equals `jobs/a-466/probe/summary.json`, and the 16 point
  files match the summary's `point_sha256`.

## Operational notes and deviations

1. The overlay build (job 464) was submitted with `sbatch` running
   `scripts/build_vllm_overlay_on_h100.sh` on one idle H100, as the registration
   (sections 1 and 4, design decision 19) and v1's job 439 do; the Docker
   submitter runs containers and cannot build an image. The probe job went
   through `submit_docker_research_job.py` (`--dry-run`, `--test-only`, submit).
   `squeue` and `nvidia-smi` were recorded before each submission
   (`ops/preflight.log`); another agent's CPU-only job
   (`cotcodec-q2-mutation-cpu`, 462 and 463) was on the host, and no other GPU
   job ran.
2. The builder's run steps quote contract `14f25482...`; the registration and
   the contract file give `9224ccdc...` (rebound before the freeze in
   `64f4328`). The registration governs, and the host computed `9224ccdc...`.
3. No orx node was created; the registration does not require one.
4. `jobs/a-466/probe/samples/compute-apps.csv` holds the allocated H100's
   NVML UUID, as the probe recorded it. It is a device identifier, not a
   network address, and the file is unmodified.

## Files

`SHA256SUMS` covers every file here. `jobs/a-466/host-run-dir.sha256` lists
every lane and probe file in the host run directory except the runtime cache
(`probe/cache`, 57 MB), including the files not copied (`system.txt`,
`docker-research.sbatch`, the container ID and the container and image inspect
records). `projection-v2.json` is the `project` output; `ops/` holds the
pre-submission node records, the job log, the Slurm records and `project`'s
stdout and exit status.
