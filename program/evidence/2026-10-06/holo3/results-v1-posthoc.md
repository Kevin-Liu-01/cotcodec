# Holo3 two-row diff: v1 reproduced (POST-HOC)

**Label: POST-HOC.** These are the v1 analysis's numbers, reproduced with new,
independent code from small range reads of the pinned archives. v1 was
registered after the per-task files were on disk, and its deciding test was
nearly fixed by totals already known
(`program/preregistrations/q2-holo3-rerun-audit-v1-posthoc.md`, decision D10).
Nothing here is confirmatory. The OpenCUA section is EXPLORATORY. Confirmatory
claims can come only from `q2-holo3-rerun-audit-v2`, which is a draft and not
frozen.

## How these numbers were produced

| Item | Value |
|---|---|
| Code | branch `stage0/q2-holo3-diff`, commit `5caf37a8da447ba71053c036734764b537902cc6`, clean checkout (`code_files_dirty: false`) |
| Command | `uv run --locked python scripts/run_holo3_rerun_audit_doctor.py --output receipt-v1.json --matrix-output holo3-per-task-matrix.csv --h-steps` |
| Where | H100 host, CPU only, fresh clone under the Stage 0 scratch root, cold member cache, 2026-10-07T07:21:58Z |
| Network | 189,359,219 bytes in 7,422 range requests, 0 retries, at most 6 concurrent; 501 s |
| Seeds | 42 (v1's registered Monte Carlo seed), 43 and 44 (sensitivity) |
| Receipt | `receipt-v1-posthoc.json`, SHA-256 `b08e102696e40d65f36e3701ecb3dc80a4f7de4dd0ce847bd9ac9eed9f37c605` |
| Per-task matrix | `holo3-per-task-matrix.csv` (361 rows), SHA-256 `2b742b7c2cf7ef191209ee1cf8eff8a7b8850f0d3b95222a595125e6f4960eea` |

The same node also ran through the fixed orx command with
`--node experiments/q2-holo3-rerun-audit/orx-node.yaml` (warm cache, 48 MB,
45 requests). Its `results` and `cases` are identical to the receipt above:

```text
ORX_RECEIPT_SUMMARY {"cases": {"passed": 7, "total": 7}, "doctor": "holo3-rerun-audit", ...}
ORX_RESULT kind=cpu-doctor direction=q2-holo3-rerun-audit exit=0
```

No byte of the 5.75 GB trajectory tarball was read. Benchmark logs were parsed
in memory for the env-prep flag only and never written to disk.

## Positive controls (all PASS)

| Control | Result |
|---|---|
| Leaderboard cells in the code equal the pinned sheet (site `62f8466d`, SHA-256 `cf6b4b67...fc09`) | PASS |
| All 20 Holo3 per-domain cells and both totals rebuilt from per-task files | PASS (296.41/359 and 280.55/359) |
| Every verified-package member matches the package `SHA256SUMS` | PASS (1,448 members) |
| Package run summaries agree with per-task files; every `result.txt` equals its `status.json` score | PASS |
| v1's printed numbers reproduced | PASS: 51 of 51 exact quantities identical; the three Monte Carlo p-values identical as printed |
| 18 OpenCUA turn totals map one-to-one onto leaderboard rows 36-53 | PASS (turn k maps to the k-th row of its archive) |
| Receipt free of IPs, AWS identifiers, home paths, websocket URLs and signed URLs | PASS |

## v1 results (POST-HOC)

Universe: 361 tasks. Both runs scored 359 (`06fe7178` setup CDP timeout and
`da46d875` evaluator date crash in both runs). Infrastructure-flagged: 17 (15
env-prep retries in a run log, 2 repaired tasks). Clean: 342.

| Test (y = 1[s >= 0.5] unless stated) | run1 only | run2 only | Exact p |
|---|---:|---:|---:|
| McNemar, common set (359) | 25 | 9 | 0.0090 |
| McNemar, clean set (342) | 23 | 9 | 0.0201 |
| McNemar, clean, y = 1[s > 0] | 23 | 9 | 0.0201 |
| McNemar, clean, y = 1[s == 1] | 22 | 10 | 0.0501 |
| Sign-flip on scores, common / clean (1e6 draws, seed 42) | | | 0.0087 / 0.0190 |
| Same, seeds 43 and 44 | | | 0.0086, 0.0087 / 0.0191, 0.0193 |

- **Gap decomposition** (4.417 pp): inclusion and denominator 0.000;
  infrastructure-flagged tasks +0.557; clean tasks with a non-local URL
  +1.924; other clean tasks +1.935. **Infrastructure share 12.6%.**
- **Strata** (clean): URL-flagged 48 tasks, 7 vs 0 (p 0.016); others 294
  tasks, 16 vs 9 (p 0.23). No domain is Holm-significant (chrome 5 vs 0, raw
  p 0.063; impress 4 vs 0, raw p 0.125).
- **Elapsed time** (clean): median 97.1 s vs 107.8 s, median ratio 0.997,
  Wilcoxon p 0.51. No shift.
- **H Company reruns** (2026-04-16, unlisted): pairwise discordance 32/356,
  37/356, 37/355 (0.090, 0.104, 0.104; largest 95% upper bound 0.141); nets
  0, +1, +1; McNemar p = 1. Expected two-run gap SD from their mean
  discordance (0.0993): 1.66 pp; the observed gap is 2.65 of those SDs, which
  restates the McNemar result (review E11).
- **Decision as registered:** not R1; **R3** (clean McNemar p < 0.05).
- **Reading fixed in the post-hoc record:** R3 means non-exchangeable reruns
  with a session shift, not an operator contrast. **The Q2 kill criterion
  does not fire.**
- **Foreseeability:** with the net flips fixed by known totals (16 on the
  common set, 14 on the clean set), exact McNemar is below 0.05 for every
  discordant count up to 58 and 44 respectively.

## Corrections from the review, reproduced

| Claim | Value |
|---|---|
| Leaderboard rank (rows grouped by model and max steps, sorted by mean) | #8 of 110, 80.36 ± 2.20 (2 runs) |
| H run rates, nulls excluded / nulls as failures | 79.90 / 79.45, 79.86 / 79.42, 80.03 / 79.58 % |
| Pass rates on the 354 tasks all five runs scored | run1 83.33, run2 78.81, H 80.23, 80.23, 79.94 % |
| run1 vs each H run (z) | +2.12, +1.72, +1.95 |
| run2 vs each H run (z) | -0.73, -0.70, -0.55 |
| Fails a task the other four all pass | run2 15/251, run1 2/238, H 6/242, 8/244, 7/243 |
| Passes a task the other four all fail | run2 1/36, run1 3/38, H 2/37, 2/37, 5/40 |
| MDE of a single two-run contrast (q = 0.0993, 80% power) | 4.66 pp at 359 tasks, 8.06 pp at 120 |

Which run is the outlier cannot be identified from five runs on two harnesses.

## External reference (EXPLORATORY: inspected during review before any registration)

Exact McNemar on y = 1[s >= 0.5] for each pair of maintainer turns, over the
tasks both turns scored; z = (a only - b only) / sqrt(discordant).

| Archive | Turn totals | Pairs (a only - b only, p, z) | Max abs z |
|---|---|---|---:|
| OpenCUA-7B, 15 steps | 93.95/359, 86.08/360, 82.72/360 | 20-12 (0.22, 1.41); 23-12 (0.09, 1.86); 15-12 (0.70, 0.58) | 1.86 |
| OpenCUA-7B, 50 steps | 104.14/361, 99.05/357, 100.25/358 | 26-22 (0.67, 0.58); 19-15 (0.61, 0.69); 17-17 (1.00, 0.00) | 0.69 |
| OpenCUA-7B, 100 steps | 97.57/359, 94.08/361, 95.65/360 | 22-18 (0.64, 0.63); 26-24 (0.89, 0.28); 25-27 (0.89, -0.28) | 0.63 |
| OpenCUA-32B, 15 steps | 100.42/357, 109.80/360, 109.34/360 | 15-23 (0.26, -1.30); 16-23 (0.34, -1.12); 19-18 (1.00, 0.16) | 1.30 |
| OpenCUA-32B, 50 steps | 121.57/360, 120.31/359, 126.49/360 | 29-28 (1.00, 0.13); 25-30 (0.59, -0.67); 23-29 (0.49, -0.83) | 0.83 |
| OpenCUA-32B, 100 steps | 121.83/360, 125.22/360, 127.95/358 | 21-25 (0.66, -0.59); 26-34 (0.37, -1.03); 23-27 (0.67, -0.57) | 1.03 |

- Pooled between-turn / residual mean-square ratio over the six archives:
  **0.663** on (12, 4282) df (upper-tail p 0.79): no sign of a session
  component in these reruns.
- H Company pairs: |z| 0.00, 0.16, 0.16.
- Holo3 run1 vs run2: |z| = 2.74 on 359 tasks, above all 21 reference pairs
  (largest 1.86). Under the v2 draft's descriptive rule this is a
  "pair-specific session shift". Caveats: the OpenCUA turn schedule
  (concurrent or sequential) is unknown, and its success rate (23-36%) differs
  from Holo3's (about 80%).

## Inputs for the v2 draft (already-inspected data only)

`results.v2_design` in the receipt holds the power simulations for v2 rules
(a) and (d) and the calibration of rule (b)'s signatures on the H Company
runs. The v2 draft quotes them in its section 6.
