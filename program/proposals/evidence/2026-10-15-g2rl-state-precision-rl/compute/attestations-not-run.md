# G2-RL: compute attestations that do not exist yet

Written by the gauntlet's synthesis owner on 2026-10-15. Nothing below was run; this file exists
so that the bundle's `compute` record can point at a hashed statement instead of a missing file.

| Attestation | Status | Why | What produces it |
|---|---|---|---|
| Image digest of the RL overlay | NOT_RUN | No verl image exists on the host or in the repository (asset cell's host listing, about 03:29 UTC 2026-10-15). The bundle records the base image `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` (vLLM v0.31.0) only | P0a fetch, P0b offline build with a provenance receipt |
| Real model loop | NOT_RUN | No GRPO driver, gradient-dump hook or calibration driver is written; the repository's `harness/runner.py` is not the loop this design uses | Drivers and hook written and CPU-tested against fakes before the freeze |
| Benchmark adapter | NOT_RUN | The reward (Math-Verify on DAPO-Math, MATH-500, AIME) and the evaluator are not written | Same |
| Container smoke | NOT_RUN | Needs the image | P0c selftests, then P2a |
| Slurm dry run and test-only run | NOT_RUN | No manifest is rendered (the image id is unknown) | `scripts/submit_docker_research_job.py <manifest> --dry-run` and `--test-only` for P1, P2a, P2b, P3a, P3b |
| Provenance verification | NOT_RUN | Needs the image | P0b's receipt |
| Executable pilot (orx node) | NOT_RUN | The gauntlet's host rule allows no job other than the open-weight reviewer's lane job; no orx node was created | The pilot's P1-P3 after a freeze and admission |

What does exist and is hashed in the bundle: the CPU re-analysis of committed data
(`mismatch_by_cap.py`, `mismatch-by-cap.json`), the operating-characteristics simulation
(`power_g2rl.py`, `power-g2rl.json`), the cap arithmetic (`caps_g2rl.py`, `caps-g2rl.json`), the
query log, the source snapshots and the blind packet. The deterministic doctor's Compute checks
therefore fail, and the pilot cap of 79 binds until the pilot runs.
