# Holo3 rerun audit: evidence bundle

Q2 Stage 0c follow-up. Produced by `scripts/run_holo3_rerun_audit_doctor.py`.

| File | What it is | Label |
|---|---|---|
| `results-v1-posthoc.md` | v1 numbers reproduced, controls, review corrections, OpenCUA reference | POST-HOC; OpenCUA part EXPLORATORY |
| `receipt-v1-posthoc.json` | the doctor's receipt: input hashes, controls, all results (its `results.v2_design` section is superseded by `../../2026-10-07/holo3-v2-design/`) | POST-HOC |
| `holo3-per-task-matrix.csv` | per-task scores, flags, elapsed times and AGP outcome classes for run1, run2 and the H Company rewards | derived numbers only |

## External sources

Every source was read at a pinned revision. Archive members were read by HTTP
range, never downloaded whole.

| Source | Revision | Size | SHA-256 | License | Read |
|---|---|---:|---|---|---|
| HF dataset `xlangai/ubuntu_osworld_verified_trajs` | `5473c39e42a538a187a9b2c2b499db59d560fd8c` | 104 files | per file below | MIT (dataset card) | metadata |
| `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_20260420_verified-run_with-local-rewards.zip` | same | 5,773,773,410 B | `0dea53ac7b04fa7d962c2da48e4c5b4023455c221043378fe1857daf97251ca4` (LFS) | MIT (dataset card) | central directory and 1,449 small members; member manifest `eb5076ba5aa2363c112669cfb25ce3f48335ad99bfb61eb37566455b8f8a93bd` |
| `OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified_hcompany-internal-runs-20260416_complete-with-rewards.zip` | same | 9,127,328,489 B | `9f2c17ae83b605992608386e68c75b284d74217bc3267f2b851b68a2b838ea4c` (LFS) | MIT (dataset card); rights chain for H Company trajectories unverified | 3 nested central directories, 2,156 `task_summary.json`/`actions.json` members (CRC-checked); manifest `de1c0785eb98c46961ec6ab6656010d91d5c461a7cb33f713e6124eaffea6dc5` |
| `opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps.zip` | same | 7,920,092,071 B | `b642e1212d3ebb87e88addc0c55525b12d1ce8b9b253306fa7706908778e9688` | MIT (dataset card) | 1,079 `result.txt`; manifest `55d0337712e38966dbd5a42c0838cfdc4835c8dc589895a912f2919ead930d20` |
| `opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-50steps.zip` | same | 12,012,284,286 B | `ad9e0a1c5b0fbe1df99f5c0e29f5a48990dc9a4e13505161b87dda558c98504b` | MIT (dataset card) | 1,076 `result.txt`; manifest `1da8b03c03fef43a4fe57f072e96909de9ba2311694eeac6df406c89b223e86a` |
| `opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-100steps.zip` | same | 12,983,641,963 B | `3a0abf7be185a7e9d413a33a4407e06da88ecca0a21eb4dc86470966a70d2669` | MIT (dataset card) | 1,080 `result.txt`; manifest `3adef6f07792666c77cfae2d068ebee08228acb3faf24e278c6dd037eab5ca75` |
| `opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-15steps.zip` | same | 7,763,337,166 B | `7ff9a5edd26353c277a21a291d439f3773e9075ab05bdc2f508c17ac5fdf1781` | MIT (dataset card) | 1,077 `result.txt`; manifest `51fa0b315fe88af8cde5318af7e902008880e5d9cdbcb4343deb36d4501b89bb` |
| `opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-50steps.zip` | same | 12,100,856,790 B | `fc657378bedc2c411fdfb5622138cef788b381d4de534a26499511f5c47e1973` | MIT (dataset card) | 1,079 `result.txt`; manifest `52dd1ceb6d34378bf73dbcd830f91c9efefb81ffc83188bdc2f0de6fd6d25fff` |
| `opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-100steps.zip` | same | 13,053,766,042 B | `38a052a86502bdea76bf0383fd16fb3b767f55e781ff48de66959207927ef6e1` | MIT (dataset card) | 1,078 `result.txt`; manifest `aa476950dbce97568fdd6472b879693b7395f398587f5cc6bca0b73c7348b266` |
| Verified-run trajectory tarball (member of the verified zip, not read) | same | 5,748,726,271 B | `3d6d65d1842f827494fb19fa4431bfe77f3b3430f3a7edf7673f928d114ffccd` (package `SHA256SUMS`), CRC-32 `c5d5275e` | MIT (dataset card); contains a personal path prefix | not read; reserved for v2 |
| `xlang-ai/OSWorld` task configs (361 `evaluation_examples/examples/*/*.json`) | `c7e54d24d136d52be0c6d5a7487a1a32f99e7017` (v1); `f723037959a9d70af4a9f39922ec63ae6f078196` for v2, with identical `evaluation_examples/` | 809,470 B in 361 files; tree listing 329,490 B | tree listing `772e02936f2ab1acf269813e7e7b5b923195bd2b8c7ad44a96097bff9936a2dc`; config blob manifest `3d4ae6da235e1d6627e72b389cda9fead93dbe9966ac8a3a3e23a1f39762bbf1`; each file checked against its git blob SHA-1 | Apache-2.0 | configs only |
| OSWorld-Verified leaderboard sheet `static/data/osworld_verified_results.xlsx` (`OS-World/OS-World.github.io`) | `62f8466dbe8b4d67c104b5ead3f8271da01aa09d` | 113,066 B | `cf6b4b67eed566ddcd5a8b7ad2d89013157978dad0eea76ea12d2377471efc09` | none declared: numbers cited, file not stored in this repository | parsed in memory |

"Manifest" is the SHA-256 of the sorted (member name, member SHA-256) list,
as computed by `harness/holo3_rerun_audit.py:_digest_manifest`.

## Public-repository hygiene

- No log text, screenshot, agent text or archive path from the tarball is
  stored. `benchmark.log` files (which hold an AWS account id, an IAM user
  name and VM addresses) are parsed in memory for 8-character task prefixes
  and counts only.
- Runner error strings are reduced to classes (`setup_cdp_timeout`,
  `evaluator_month_out_of_range`); the raw strings contain private VPC
  addresses and a CDP websocket id.
- Every receipt passes `assert_public_safe`, which rejects IPv4 addresses, AWS
  security-group, subnet, VPC, AMI, instance and account ids, access keys,
  home-directory and shared-filesystem paths, websocket and signed URLs.
- No OSWorld agent code is used, quoted or copied. A security-relevant
  observation about it is withheld pending a disclosure decision reserved for
  the program owner (D2).
