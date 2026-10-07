# serving-throughput-probe-v1: operations evidence (2026-10-07)

Run of the frozen registration
`program/preregistrations/serving-throughput-probe-v1.md` (ledger row in
`ledger-row.json`, sign-offs D8, D17, D18) on `fal-h100-01`. Infrastructure
evidence only ("admission pass"); no number here is a scientific result.

## Outcome (as `project` labelled it)

| Line | Outcome | Key numbers |
|---|---|---|
| Job A (Slurm 442) | accepted, `complete-with-cuts`, not eager | G0.0-G0.8 pass in both phases; points valid: a-smoke, a1a, r1, x1-smoke, x1-a1, x1-r1; invalid: r3, r4; truncated: a1b; not-run: a1c, r2, f1, a2, d8, a6 |
| Job B (Slurm 446) | accepted, `complete`, not eager | G0.0-G0.8 pass; all 7 points valid |
| Control X1 | `fail` | a1 delta 0.86%, r1 mean-latency delta 5.89% (threshold 5%); 1 of 3 A1 seeds valid; mean prompt tokens per request r1 9,077 vs x1-r1 8,475 (6.6%) |
| Job C | not run | renderer refused: "job C needs control X1 to pass; job A has X1 fail" (`manifests/c.render.txt`) |
| cu130 retry | not triggered | no cu129 gate failure ended a job as a pre-result |
| Q1 projection | `within-cap` | single turn 2.92 GPU-h (cut 6), three turns 10.21 GPU-h (cut 12); x1.5 applied (X1 fail), n_B1 1.0 (B1 range 1.03%); GPU-s per completion b2 3.50, b3 1.19, b6 7.56 |
| Q2 projection | `incomplete-re-probe` | "required replay point r3 is missing or invalid" |
| A1 noise | multiplier 1.10 | 1 of 3 valid (a1b truncated, a1c not run) |

## Why r3 and r4 are invalid

Every attempt of r3 (2) and r4 (2) completed all requests with no failures,
exact output lengths and matching counters, and failed only `no_contamination`.
The real-phase reservation measured over 5 s after the 1-PNG smoke was
74,301 MiB, so the limit was 76,349 MiB; the engine's own footprint reached
76,611 MiB under the 20-screenshot H2 replay and stayed there (a1b, the next
point, also failed the check before it was truncated). `nvidia-smi
--query-compute-apps` showed only the job's EngineCore process on the GPU, and
the lane prolog recorded the GPU as exclusive. r3 was also flagged
`front-end-bound` (API server 103% CPU). Under the frozen rules r3 and r4 stay
invalid; the two reruns consumed the real phase's launch window, which cut the
remaining points. Any change to the reservation rule is a new experiment id.

## GPU time (Slurm `scontrol`; `sacct` accounting is disabled on this host)

| Line | Job | Elapsed | GPU-h | Cap |
|---|---|---:|---:|---:|
| Overlay build (cu129) | 439 | 00:00:30 | 0.0083 | 10 min |
| Metadata fetch | 444 | 00:00:05 | 0.0014 | 10 min |
| Overlay build + fetch | | | 0.0097 | 0.333 (D17) |
| Job A | 442 | 00:28:32 | 0.4756 | 40 min / 0.67 |
| Job B | 446 | 00:10:51 | 0.1808 | 20 min / 0.34 |
| Probe (A + B) | | | 0.6564 | 1.0 (D8) |
| Job C | not run | | 0 | 0.5 |
| cu130 retry | not run | | 0 | 1.0 (D17) |
| Total | | | 0.6661 | |

Jobs 439, 444 and 446 had aged out of `scontrol` when the records were
collected; their lines were captured live when each job left the queue
(`ops/slurm-records.txt`). Every job: `JobState=COMPLETED`, `ExitCode=0:0`;
jobs A and B: lane `termination.env` `reason=completed`, `exit_code=0`,
`checkpoint_ready=false` (no signal).

## Provenance

- Code revision X = `80a87ee4f91e104d73948b756e5acda3ee7863c6` (origin/main at
  clone time; differs from the freeze commit `6b7967f` only in
  `program/state.json`). Contract SHA-256 `8e5ad94e...e931` and probe code
  digest `15b7a73b...7277` verified on the host before the build and by G0.0 in
  both jobs; `project` recorded `probe_files_modified: false`.
- Source capsule `2c607c86d83c0b023bddb28ac22ed7fa2541c816ac8b6b16370d83bc3fb4d5b9`
  (`capsule/source-receipt.json`, 1,445 files).
- Base image `vllm/vllm-openai@sha256:b18abb2d...` (image ID
  `sha256:423783aa...`, vLLM label commit `db9527a4...`) was already on the host.
  Overlay image `sha256:fa1906ad5c53ec9bdb92551d8b81b78ae22e9bf26871c03c3128437236846dea`
  (`overlay/build-receipt.json`, SHA-256 `31f11632...0622`): torchcodec 0.17.0
  removed, `vllm-args-doctor` pass, provenance PASS.
- Runtime: torch 2.13.0+cu129, Triton 3.7.1, the image's forward-compatibility
  `libcuda.so.575.57.08` active on the R570 host driver (`cuDriverGetVersion`
  12090); G0.3 normalized error 0.00281.
- Metadata receipts (`metadata/`): qwen3-8b `8c206de0...9a48` (15,910,042 B),
  qwen3.5-27b-fp8 `7f5b4659...51e1` (23,033,229 B), qwen3.5-35b-a3b-fp8
  `2b6f0100...a2b` (23,034,749 B); byte totals and tokenizer.json hashes match
  section 11. Both rung configs have `max_position_embeddings` 262,144.
- Engine facts: 9B real and dummy, weights 17.66 GiB, KV 51.2 GiB (1,634,030
  tokens); Qwen3-8B dummy, weights 15.27 GiB, KV 53.34 GiB (388,384 tokens);
  CUDA graphs on, no eager fallback, no `/tmp` mappings.

## Operational deviations

1. **Capsule without the `.agents/skills` symlinks.** `create_source_archive.py
   --discovery` refuses symlinks, and main tracks 27 (`.agents/skills/*`, links
   to `.claude/skills/*`); the discovery extractor admits regular files only, so
   no capsule of this repository can carry them. In the dedicated host clone the
   operator ran `git rm -r .agents/skills` for the archive step only, then
   `git reset --hard X` (clone clean again). The capsule receipt therefore
   records `worktree_clean: false`; the excluded entries are in
   `capsule/capsule-symlink-exclusion.txt`. No probe, contract or runtime file
   is affected. A lane fix is a code change and was not made.
2. The metadata fetch ran after job A was submitted, and jobs A and B ran at the
   same time on separate H100s (GPU 0 and 1, overlapping 11:49-11:59 UTC).
   The registration fixes neither order. Other agents' CPU-only jobs ran on the
   host during the probe (`ops/preflight.log`).
3. Rendered manifests were written outside the host clone (copies in
   `manifests/`). No orx node was created; the registration does not require
   one.

## Files

`SHA256SUMS` covers every file here. `jobs/<job>-<id>/host-run-dir.sha256`
lists every lane and probe file left on the host run directory (Triton cache
excluded), including the files not copied (`system.txt`, container inspect
records). `projection-v1.json` is the `project` output; `ops/` holds the
pre-submission node records, job log, Slurm records and the `project` exit
status.
