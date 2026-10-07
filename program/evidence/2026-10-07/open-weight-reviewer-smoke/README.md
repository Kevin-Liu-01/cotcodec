# Open-weight reviewer: lane smoke (2026-10-07)

Tooling evidence for `scripts/run_open_weight_review.py`, the provider-distinct
gauntlet reviewer of D23 and D24, on `fal-h100-01`. No number here is a
scientific result. The smoke request is a dummy (`experiments/reviewer/smoke-*`).

## Outcome

| Line | Outcome |
|---|---|
| Review produced | **yes**: job 617 wrote a `PARSED` review 71 s after its container started; `verify` re-hashes it clean |
| Process exit | **failed**: the process hung in interpreter shutdown after the review; the job ended `TIMEOUT` and its container outlived the job holding GPU 0 until it was stopped by hand |
| Smoke GPU cap (0.1 GPU-h) | **exceeded**: 0.1075 GPU-h by Slurm, 0.1319 GPU-h of physical GPU occupancy |
| Exit fix | commit `37f4f2a`; CPU-validated as PID 1 inside its overlay image; **not yet validated on a GPU** |
| Re-smoke | `manifests/smoke2.yaml` rendered, dry-run and test-only passed; **not submitted** (needs a new GPU allowance) |

## Jobs

| Job | What | Commit | Image | Slurm state | Elapsed | GPU-h |
|---|---|---|---|---|---:|---:|
| 614 | overlay build (`build_vllm_overlay_on_h100.sh`, cu129) | `f74084d` | `sha256:f760b0fe...` | COMPLETED 0:0 | 00:00:46 | 0.0128 |
| 617 | smoke review, qwen3.5-9b, TP=1, 6 min, cap 0.1 | `f74084d` | `sha256:f760b0fe...` | TIMEOUT 0:9 | 00:06:27 | 0.1075 |
| 617, after the job | container `cotcodec-617` still running on GPU 0 (EngineCore, 74,134 MiB) | | | outside Slurm | 00:01:28 | 0.0244 |
| 629 | overlay build of the fix | `37f4f2a` | `sha256:eda72497...` | COMPLETED 0:0 | 00:00:51 | 0.0142 |
| total | | | | | | **0.1589** |

Records: `ops/scontrol-<job>.last.txt` (captured as each job left the queue;
`sacct` accounting is disabled on this host), `ops/jobs.log`,
`ops/preflight.log` (queue and GPU state before each submission: all eight
GPUs idle each time). The overlay builds are infrastructure, accounted as the
serving probes accounted theirs (D17, D19); the smoke itself used 0.1319 GPU-h
of physical occupancy against its 0.1 GPU-h cap.

## Job 617 timeline

| Time (UTC) | Event | Source |
|---|---|---|
| 20:01:27 | Slurm start | `ops/scontrol-617.last.txt` |
| 20:01:28.9 | container start | `State.StartedAt` of `container-inspect.pre-stop.json` (host only, listed in `jobs/617/host-run-dir.sha256`) |
| 20:01:43 | workload start (after provenance, container doctor and the 19.3 GB model verification) | `review/receipt.json` `started_at` |
| 20:02:35 | engine ready: init 52.5 s; weights 16.8 GiB loaded in 7.6 s; KV cache 52.47 GiB (1,212,416 tokens); eager | `jobs/617/container.log` |
| 20:02:39 | review written: 286 prompt tokens, 62 output tokens per seed, generate 3.6 s, `finish_reason=stop`, parsed bare, replicates 43 and 44 token-identical to 42 | `review/receipt.json` |
| 20:02:39 to 20:07:54 | process alive, nothing logged | `jobs/617/container-top.post-timeout.txt` (main `Ssl`, `VLLM::EngineCore`, `resource_tracker`) |
| about 20:04 to 20:05 | Slurm's USR1 due (180 s, up to 240 s, before the limit); no lane record survives, and no marker or receipt change followed | `review/receipt.json` (`signals_received: []`), no `checkpoint.ready` |
| 20:07:54 | Slurm time limit; batch script killed before its exit trap, so no `termination.env` or lane `container.log` | `jobs/617/slurm-617.out` |
| 20:09:22 | operator: logs saved, `docker stop` (TERM ignored, KILL after 15 s, exit 137), `docker rm`; GPU 0 back to 0 MiB | `ops/jobs.log`, `jobs/617/container-state.after-stop.txt` |

The review (`jobs/617/review/`): model `qwen3.5-9b` at
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`, model receipt `0a9e052d...cb3`,
vLLM 0.31.0, torch 2.13.0+cu129, transformers 5.17.0, prompt SHA-256
`25b716c6...a88f`, output SHA-256 `423c3b3f...e2e7`, parsed SHA-256
`dc622312...d25e`, receipt SHA-256 `6dd2d7a9...9e64`. The model scored the
deliberately vacuous proposal's falsifiability 10 and named its triviality as
the largest defect.

## The defect and the fix

After `main` returned, interpreter shutdown waited on vLLM's teardown and never
finished. `command_run` had also restored the default signal dispositions after
the review; the workload is PID 1 in the lane container, where a signal with the
default disposition is ignored, so the lane's USR1 and TERM did nothing. When
Slurm killed the batch script at the limit, its exit trap could not run and the
container was left behind.

Commit `37f4f2a`: the USR1/TERM/INT handlers stay installed until the process
exits; the engine is closed in a daemon thread bounded at 30 s (outcome in the
receipt's `engine_close`; skipped after a signal); the process leaves with
`os._exit` once every output is written. `tests/open_weight_review_exit_driver.py`
reproduces the hang (a non-daemon thread that never ends, a close that never
returns). In image `sha256:eda72497...`, CPU only, the driver as PID 1
(`ops/pid1-check-37f4f2aaf93e.txt`):

- hang scenario: exit 0 in 1.3 s including container start, `PARSED`,
  `engine_close: timeout after 1 s`, no marker;
- `docker kill --signal USR1` while generating: exit 3 0.08 s later,
  `INTERRUPTED`, marker `trigger=SIGUSR1`;
- `docker kill --signal TERM` while generating: exit 3 0.08 s later,
  `INTERRUPTED`, marker `trigger=SIGTERM`.

`doctor` passed in both images (`ops/doctor-cpu-*.json`). The real engine's
`engine_core.shutdown()` call and the exit on a GPU are not yet exercised.

## Lane gap (for the lane owner)

`docker-research.sbatch` removes its container only from its exit trap. When
Slurm kills the batch script at the time limit, a container whose workload
ignores TERM survives the job and keeps its GPU outside Slurm, and the next job
given that GPU is refused by the foreign-process prolog (or, with
`allow_shared_gpu`, shares it). A host-side reaper, or `docker run --init` /
`--stop-timeout` with a kill on the batch script's TERM path, would close it.
Not changed here.

## Model choice

`qwen3.6-35b-a3b` (bf16) is the default reviewer at TP=1: its language-model
weights are 64.56 GiB (vision tower 0.83 GiB and MTP head 1.57 GiB, not loaded
with `language_model_only`), below the 71.27 GiB that 0.9 utilization gives on
this H100 (79.19 GiB, log line in `jobs/617/container.log`); its 10 full-attention
layers with 2 KV heads of 256 need about 20 KiB of KV per token, so a 65,536-token
context fits with room for the three replicates. TP=2 is therefore not needed.
The smoke used `qwen3.5-9b`, the named fallback, because a 35B-A3B job cannot
fit the 0.1 GPU-h cap: 6 minutes on one GPU leaves at most 2 to 3 minutes
before USR1, and the lane first hashes all 72 GB of the snapshot. Nothing in this
bundle ran `qwen3.6-35b-a3b` on a GPU.

## Provenance

- Commits `f74084d3b3fb9877d6c37b08d66ec4b311e71968` (tree `a1dc588c...`) and
  `37f4f2aaf93e2a3035e7f0314b7fcf0ec5f370e9` (tree `03048b1b...`) on branch
  `stage0/open-weight-reviewer`, not pushed; each shipped to the host as a git
  bundle (SHA-256 `37ce6cf9...0e` and `15d4b4c0...56`) and cloned twice, once
  for the archive and the build (never touched otherwise) and once for tests
  (479 and 483 passed: reviewer, overlay, lane and archive tests).
- Discovery capsules `ce9b303c...024e` (1,761 files) and `ef7ce7d4...5b7f`
  (1,762 files), schema 3, `worktree_clean: true`, 27 `.agents/skills` links
  omitted under the reviewed rule (`capsule/`).
- Base image `vllm/vllm-openai@sha256:b18abb2d...` (ID `sha256:423783aa...`,
  vLLM 0.31.0 commit `db9527a4...`); builder `aa43283e...` and extractor
  `9b4d21a8...`, the committed files, as in serving-throughput-probe-v2;
  torchcodec 0.17.0 removed by the fixups (`overlay-*/`).
- Manifests rendered by `run_open_weight_review.py manifest` from the build
  receipts (`manifests/`); dry-run and test-only exit 0 for both (`ops/`).

## Next GPU steps (each needs a GPU allowance; none is spent here)

1. Re-smoke the fix: `manifests/smoke2.yaml` (qwen3.5-9b, image
   `sha256:eda72497...`, 6 min, cap 0.1 GPU-h; dry-run and test-only passed),
   submitted from `~/cotcodec-runs/stage0/open-weight-reviewer/wt-37f4f2aaf93e`.
   Accept it only with `JobState=COMPLETED`, `ExitCode=0:0`, lane
   `reason=completed`, receipt `PARSED` with `engine_close` recorded, and no
   `cotcodec-<job>` container left (`docker ps -a --filter name=cotcodec-<job>`).
2. First 35B-A3B review: render with `--model-id qwen3.6-35b-a3b` (TP=1). Its
   load and decode times in this lane are unmeasured; the lane hashes 72 GB
   before the workload starts. Check the same exit conditions after it.

## Files

`SHA256SUMS` covers every file here. `jobs/617/host-run-dir.sha256` lists every
file of the host run directory, including those not copied (`system.txt`, the
batch script copy and the container and image inspect records).
