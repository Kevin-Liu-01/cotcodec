# Open-weight reviewer: GPU validation of the exit fix (2026-10-07)

Tooling evidence for `scripts/run_open_weight_review.py` on `fal-h100-01`. Smoke
job 617 (`open-weight-reviewer-smoke/`) wrote its review, then hung in vLLM
teardown and overran its 0.1 GPU-h cap. The fix (`37f4f2a`) had been validated
on CPU only. Here it runs on a GPU, built from `main` at `00961e5`. The reviewer,
lane and builder code there is identical to `37f4f2a`: `git diff 37f4f2a 00961e5`
touches nothing under `scripts/`, `infra/`, `harness/` or `tests/`. No code was
edited. Both requests are dummies, so nothing here is a scientific result.

## Outcome

| Line | Outcome |
|---|---|
| Overlay build from a fresh clean clone of `main` | **pass**: job 651, COMPLETED 0:0, image `sha256:8c59da42...` |
| Smoke 2 (qwen3.5-9b, TP=1, 6 min, cap 0.1 GPU-h) | **pass**: job 653 meets every acceptance criterion below, using 0.0203 GPU-h |
| Load check (qwen3.6-35b-a3b, TP=1, 9 min, cap 0.15 GPU-h) | **pass**: job 655 exits cleanly, using 0.0433 GPU-h. Verify 52.3 s, engine init 96.5 s, generate 1.2 s |
| GPU time | 0.0747 GPU-h by Slurm (overlay 0.0111). No GPU was held after any job ended |

## Acceptance (fixed before submission)

| Criterion | Job 653 (smoke 2) | Job 655 (35B load check) |
|---|---|---|
| Slurm `JobState`, `ExitCode` | COMPLETED, 0:0 (`ops/scontrol-653.last.txt`) | COMPLETED, 0:0 (`ops/scontrol-655.last.txt`) |
| Lane `termination.env` | `reason=completed`, `exit_code=0` | `reason=completed`, `exit_code=0` |
| Review parses | `PARSED`, extraction `bare`, `finish_reason=stop`; `verify` ok, no problems (`ops/verify-653.json`) | `PARSED`, `bare`, `stop`; `verify` ok (`ops/verify-655.json`) |
| Engine close, signals | `engine_close: closed`, `signals_received: []` | `closed`, `[]` |
| No GPU process within 10 s of the end | first sample 22:08:41.295, at most 1.3 s after Slurm `EndTime` 22:08:40 and 0.5 s after `termination.env` was written: no compute process, 0 MiB on all eight GPUs. All 21 samples to t+20 s are the same (`ops/postjob-653.log`) | first sample 22:12:47.665, at most 0.7 s after `EndTime` 22:12:47: same result, all 21 samples (`ops/postjob-655.log`) |
| No container left | `docker ps -a --filter name=cotcodec-653` was empty at 22:09:16 from a fresh login. The watcher's own Docker query failed (see Operations) | the watcher's Docker query was empty in all 21 samples |

Before each submission, `ops/preflight.log` recorded `squeue` and `nvidia-smi`
(empty queue, all eight GPUs idle, no compute process). It did the same before
the overlay build. Each lane GPU prolog recorded `decision=exclusive`.

## Jobs

| Job | What | Image | Slurm | Start, end (UTC) | Run time | GPU-h | Cap |
|---|---|---|---|---|---:|---:|---:|
| 651 | overlay build (`build_vllm_overlay_on_h100.sh`, cu129) from `checkout-00961e5b2842` | builds `8c59da42` | COMPLETED 0:0 | 22:05:39, 22:06:19 | 40 s | 0.0111 | (5 min allocation) |
| 653 | smoke 2, qwen3.5-9b, eager, thinking off | `8c59da42` | COMPLETED 0:0 | 22:07:27, 22:08:40 | 73 s | 0.0203 | 0.1 |
| 655 | load check, qwen3.6-35b-a3b, CUDA graphs, thinking off | `8c59da42` | COMPLETED 0:0 | 22:10:11, 22:12:47 | 156 s | 0.0433 | 0.15 |
| total | | | | | 269 s | **0.0747** | |

As in D17 and D19, the overlay build is accounted as infrastructure, separately
from the two jobs.

## Job 653: smoke 2

`manifests/smoke2-00961e5b2842.yaml` is the prepared `smoke2.yaml`
(`open-weight-reviewer-smoke/manifests/`) re-rendered by
`run_open_weight_review.py manifest` from overlay 651's build receipt. It has the
same request, model, engine arguments, seeds, 6 minutes and 0.1 GPU-h cap.
`ops/smoke2-vs-smoke2-00961e5b2842.diff` shows that only the provenance changes:
name, image, `git_sha`, `source_sha256`, run root, and the request's revision
and path. The re-packed request is byte-identical to the old one (SHA-256
`54f8a11d...fd7c`). Dry-run and test-only passed with exit 0.

| Time (UTC) | Event | Source |
|---|---|---|
| 22:07:27 | Slurm start | `ops/scontrol-653.last.txt` |
| 22:07:28.50 | container start | `jobs/653/container-state.json` |
| 22:07:29.01 to 22:07:43.06 | lane model verification of 19.33 GB: 14.0 s | host file times of `container-doctor.txt` and `model-verification.txt` |
| 22:07:43 | workload start | `review/receipt.json` `started_at` |
| 22:08:31 | engine ready: init 48.8 s (receipt); weights 16.8 GiB in 7.1 s; KV 52.47 GiB (1,212,416 tokens) | `jobs/653/container.log` |
| about 22:08:38 | review generated: 286 prompt tokens, 3 x 62 output tokens, 6.28 s, seeds 43 and 44 token-identical to 42 | `review/receipt.json` |
| 22:08:38 to 22:08:40 | engine shutdown, `MPClient: complete` | `jobs/653/container.log` |
| 22:08:40.63 | container exits 0 (PID 1 `os._exit`) | `jobs/653/container-state.json` |
| 22:08:40.80 | lane writes `termination.env` (`completed`) and removes the container | file time |
| 22:08:41.29 | watcher sees COMPLETED; GPUs already empty | `ops/postjob-653.log` |

The review is the same as job 617's down to the byte: output SHA-256
`423c3b3f...e2e7` and parsed SHA-256 `dc622312...d25e` in both (greedy, same
prompt, model and settings). Receipt SHA-256 `c522903a...02ab`. Generation took
6.28 s here and 3.6 s in job 617.

## Job 655: qwen3.6-35b-a3b load check

The request (`requests/loadcheck-35b-prompt.txt`, 2 lines, SHA-256
`57aa5a52...1f14`) is packed with `experiments/reviewer/smoke-schema.json`
(bundle `2ed616d3...192d`). Engine settings match the gauntlet review job 640
(`--max-model-len 131072`, `--gpu-memory-utilization 0.95`, CUDA graphs on),
except thinking is off and `--max-tokens` is 512. `--minutes 9` makes the cap
0.15 GPU-h. Dry-run and test-only passed with exit 0.

| Phase | Time | Source |
|---|---:|---|
| Slurm start to container start | 1 to 2 s (22:10:11, whole seconds, to 22:10:12.65) | scontrol, `container-state.json` |
| provenance check and container doctor | 0.5 s | host file times |
| **verify**: lane re-hash of the full 71.93 GB snapshot | **52.3 s** (22:10:13.16 to 22:11:05.46; 1.38 GB/s) | host file times of `container-doctor.txt` and `model-verification.txt` |
| **load**: engine init, as the receipt records it | **96.5 s** | `review/receipt.json` `timings_s` |
| in it: weight load | 19.3 s (64.69 GiB; 15.1 s to read) | `container.log` |
| in it: torch.compile, warmup run, CUDA graph capture | 18.95 s, 8.46 s, 7 s + 2 s | `container.log` |
| in it: vLLM `init engine` (profile, KV cache, warmup) | 46.2 s; KV 7.76 GiB = 385,211 tokens (2.94 x 131,072) | `container.log` |
| **decode**: one batch of 3 seeds, 243 prompt tokens, 40 output tokens each | **1.216 s** | `review/receipt.json` |
| engine close | about 3 s (22:12:43 to 22:12:46), `closed` | `container.log`, receipt |
| container exit, `termination.env`, Slurm end | 22:12:46.85, 22:12:47.01, 22:12:47 | `container-state.json`, file time, scontrol |

Output: `{"falsifiability_score": 0, "has_falsifier": false, "largest_defect":
"no proposal was given"}`. Seeds 43 and 44 were token-identical to 42. Receipt
SHA-256 `99f7e41a...12c2`.

The 1.2 s generate time is not a decode-throughput measurement. It covers 40
tokens and includes a Triton JIT compile of `fused_moe_kernel` that vLLM
flagged during inference (`container.log`, 22:12:42). Throughput needs a long
output; see job 640 below.

From Slurm start to the first generated token, a 35B-A3B review at TP=1 in this
lane takes about 2.5 minutes (verify 52 s plus engine init 97 s), and teardown
adds about 3 s. Slurm sends USR1 180 to 240 s before the limit, so a review
needs `--minutes` of at least (150 s + generation + 240 s) / 60. The page cache
was probably warm, since job 640 read the same snapshot 30 minutes earlier.
Both models hashed at about 1.38 GB/s, which suggests the hash, not I/O, set
the verify rate. A cold read was not measured.

## Earlier observation: job 640

The gauntlet's own 35B-A3B review (`k1v2-w1-r2`, Slurm 640, 21:39 to 21:42 UTC,
image `eda72497` of `37f4f2a`) was in fact the fix's first run on a GPU. It ended
with lane `reason=completed`, exit 0 and `engine_close: closed`, with no signal.
On the host, its run directory shows verify 52.5 s, engine init 96.5 s, and
3 x 5,399 output tokens plus a 103,814-token prompt in one 37.8 s batch. The
37.8 s includes prefill, so 428 tok/s aggregate is a lower bound on decode.
No GPU or Docker sample was taken after that job, so it does not meet the
acceptance above. It is recorded here and was not copied.

## Operations

- The source was shipped as a git bundle of `main` (SHA-256 `749e889b...27b4`)
  and cloned twice on the host. `checkout-00961e5b2842` was used only for the
  capsule and the build. `wt-00961e5b2842` (`uv sync --locked --extra dev`)
  packed the requests, rendered the manifests and submitted the jobs. Both are
  clean at `00961e5b2842f6f38d505dfdba1f074cea985165`, tree `1fe297b9...`.
- Discovery capsule `f5bf819b...e355` has 1,892 files, schema 3 and
  `worktree_clean: true` (`capsule/`). Builder `aa43283e...` and extractor
  `9b4d21a8...` are byte-identical to those of overlays 614 and 629. Base image
  `vllm/vllm-openai@sha256:b18abb2d...` (vLLM 0.31.0); fix-ups remove torchcodec
  0.17.0 (`overlay-651/`).
- Tests ran on the host from an rsync of this worktree (`.venv`, the `.git`
  pointer and caches excluded) after `uv sync --locked --extra dev`: ruff passed,
  and pytest gave 1150 passed and 17 skipped (`ops/host-tests-00961e5b2842.txt`).
- `ops/watch-job.sh` (read-only) followed each job: it kept the last
  `scontrol show job` record (accounting is off) and sampled
  `nvidia-smi --query-compute-apps`, per-GPU memory and
  `docker ps -a --filter name=cotcodec-<job>` once a second for 20 s after the
  terminal state. For job 653 it ran in the host's default tmux server, whose
  `cotcodec` session dates from 2026-08-11. Processes started there lack the
  `docker` group, so every Docker query got `permission denied`; the GPU samples
  were unaffected. Job 655's watcher ran under a new tmux server
  (`-L owr-watch`) whose processes have the group (`id -nG` checked). Job 651's
  watcher ran in the login session.
- Records from the host run directories: `jobs/<id>/` (the lane's files without
  `system.txt`, the batch-script copy and the image and container inspect
  records). `container-state.json` is the `State` block of the final inspect.
  `host-run-dir.sha256` lists every host file.

## Not covered here

- The signal path (USR1 or TERM while generating, exit 3 and the marker) is
  still validated only on CPU (`open-weight-reviewer-smoke/ops/pid1-check-*`).
- The lane gap noted in the smoke bundle remains: a container whose workload
  ignores TERM outlives a job that Slurm kills at its time limit. These jobs
  ended by themselves, so they did not exercise it.

## Files

`SHA256SUMS` covers every file here except itself.
