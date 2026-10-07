# Holo3 rerun audit: v2 design inputs

Q2 Stage 0c follow-up. These are the design numbers that the draft
`program/preregistrations/q2-holo3-rerun-audit-v2.md` quotes in sections 3
and 6. They come from already-inspected data only: v1 totals and URL strata,
and the H Company runs' rewards and `actions.json`. The stage classifies no
evaluator and reads no tarball byte, so nothing here is confirmatory data for
v2. They replace the `results.v2_design` section of
`../../2026-10-06/holo3/receipt-v1-posthoc.json`, which was computed under the
rules the adversarial review rejected.

| File | What it is | Label |
|---|---|---|
| `receipt-v2-design.json` | doctor receipt: input hashes, controls, all design numbers | DESIGN (already-inspected data) |

## Provenance

| Item | Value |
|---|---|
| Command | `uv run --locked python scripts/run_holo3_rerun_audit_doctor.py --stage v2-design --cache-dir CACHE --output receipt-v2-design.json`, with `CACHE` a fresh, empty directory |
| Code | commit `7192c20aff1f318b2f200b8b10ef6235557669f4`, code files clean, fresh clone on the H100 host (CPU only, no GPU, no Slurm) |
| Started | 2026-10-07T08:14:31Z, 117 s |
| Transfer | 134,007,022 B in 968 range requests, 0 retries, cold cache |
| Receipt SHA-256 | `0b48edeeaabcce27edd58d4ba32271b5e10c4613826e5ebc2e449335f954addf` |
| Controls | 6 of 6 PASS: 20 Holo3 domain cells and totals, leaderboard sheet, `SHA256SUMS` (1,449 members), package summaries, registered H reference, receipt public safety |

A dry run of the same stage from an uncommitted copy of the code gave an
identical `results.v2_design`.

## Main numbers

- Clean set 342 tasks. URL stratum 48 tasks (run1-only 7, run2-only 0);
  other 294 (16, 9); net 14. A URL-based L can carry a share of at most 0.5.
- Rule (d) exact power table (stratified exact test at 0.04 plus the 0.5
  share bar): `results.v2_design.rule_d_power_exact`.
- Rule (a) power (Wilcoxon at 0.01 plus |mean ln step ratio| >= ln 1.10),
  uniform and subset shifts, with the superseded median-ratio gate beside it:
  `results.v2_design.rule_a_power`. A 1.5x shift on 30% of tasks: 0.83 (old
  gate 0.00).
- H step baseline: mean ln ratio -0.031, -0.021, +0.009; Wilcoxon p 0.24,
  0.56, 0.69; 153, 167 and 160 tied pairs.
- Rule (b) H reference on clean tasks (registered): 30 unique failures,
  environment 0, step cap 9, premature answer 1, other 20. Run2-unique
  failures 14 (run1-unique 2). Label thresholds: environment >= 7 of 14,
  agent-side >= 10 of 14. Each H run against the other two: no label; the
  superseded share-only rule labelled `072452` "agent-side session
  variation".
- Failing H trajectories with a text signature that also hit the step cap:
  4 of 7, 4 of 10, 1 of 7. Text criterion on passing clean H episodes: 1.1%
  (812 episodes); tool-error keys: 0%.

## External sources

Read at the same pins as the 2026-10-06 bundle, which has the full table
(`../../2026-10-06/holo3/README.md`). This stage read:

| Source | Revision | Size | SHA-256 | License | Read |
|---|---|---:|---|---|---|
| `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_20260420_verified-run_with-local-rewards.zip` (HF `xlangai/ubuntu_osworld_verified_trajs`) | `5473c39e42a538a187a9b2c2b499db59d560fd8c` | 5,773,773,410 B | `0dea53ac7b04fa7d962c2da48e4c5b4023455c221043378fe1857daf97251ca4` (LFS) | MIT (dataset card) | central directory and 1,449 small members; member manifest `eb5076ba5aa2363c112669cfb25ce3f48335ad99bfb61eb37566455b8f8a93bd`; tarball not read |
| `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_hcompany-internal-runs-20260416_complete-with-rewards.zip` (same dataset) | same | 9,127,328,489 B | `9f2c17ae83b605992608386e68c75b284d74217bc3267f2b851b68a2b838ea4c` (LFS) | MIT (dataset card); rights chain for H Company trajectories unverified | 2,156 `task_summary.json`/`actions.json` members, CRC-checked; manifest `de1c0785eb98c46961ec6ab6656010d91d5c461a7cb33f713e6124eaffea6dc5`; no screenshots |
| `xlang-ai/OSWorld` task configs (361 files) | `c7e54d24d136d52be0c6d5a7487a1a32f99e7017` | 809,470 B | config blob manifest `3d4ae6da235e1d6627e72b389cda9fead93dbe9966ac8a3a3e23a1f39762bbf1`; tree listing `772e02936f2ab1acf269813e7e7b5b923195bd2b8c7ad44a96097bff9936a2dc` | Apache-2.0 | v1's URL flag only; no evaluator classified |
| OSWorld-Verified leaderboard sheet (`OS-World/OS-World.github.io`) | `62f8466dbe8b4d67c104b5ead3f8271da01aa09d` | 113,066 B | `cf6b4b67eed566ddcd5a8b7ad2d89013157978dad0eea76ea12d2377471efc09` | none declared: cited, not stored | parsed in memory |

## Public-repository hygiene

The receipt holds input hashes, counts and derived numbers only. It passes
`assert_public_safe`, which now also rejects an IPv4 address before a
sentence period, AWS private DNS names, and 12-digit ids stored as numbers.
The 2026-10-06 receipt and matrix pass the stricter scan too.
