# G2-stream: compute attestations that do not exist yet

Written by the gauntlet's synthesis owner on 2026-10-15. Nothing below was run. This file exists so
that the bundle's `compute` record can point at a hashed statement instead of a missing file.

| Attestation | Status | Why | What produces it |
|---|---|---|---|
| Image digest of the llama.cpp b11669 image | NOT_RUN | No llama.cpp image exists on the host (asset cell's read-only listing, 22:15Z on 2026-10-15). The bundle records the research base `docker.io/nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04@sha256:24c8e3581ea6330038b0d374920721983312627f8adbfcf390bdb4b399d280ed` and, for the full study, `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` | P0b: an offline CPU-only build job with a provenance receipt |
| Real model loop | NOT_RUN | The routing-dump tool (`harness/g2stream/topk_dump.cpp`), the trace driver and the session renderer are not written | P0 and P0b, CPU-tested before the freeze |
| Benchmark adapter | NOT_RUN | The ds4-policy port, the cache simulators as harness code and the three-tier emulator are not written as harness modules; the bundle's `compute/sim_g2stream.py` is a synthetic-data prototype with unit tests | P0 |
| Container smoke | NOT_RUN | Needs the image | P0b, then a test-only job |
| Slurm dry run and test-only run | NOT_RUN | No manifest is rendered: the image id is unknown | `scripts/submit_docker_research_job.py <manifest> --dry-run` and `--test-only` for P1-gpu, P2 and P3 |
| Provenance verification | NOT_RUN | Needs the image and the downloads, which await Kevin's go-ahead (707.5 GB) | P0b's receipt and the downloads' SHA-256 checks |
| Executable pilot (orx node) | NOT_RUN | The gauntlet's host rule allows no job other than the open-weight reviewer's lane job; no orx node was created | The pilot after a freeze and admission |

What does exist and is hashed in the bundle:
- the simulators and their unit tests on synthetic data, with operating characteristics
  (`sim_g2stream.py`, `sim-g2stream.json`);
- the identification arithmetic and the frozen null (`identification_g2stream.py`,
  `identification-g2stream.json`);
- the pre-registered targets (`ds4-targets.json`);
- the cap arithmetic (`caps_g2stream.py`, `caps-g2stream.json`);
- the query log, the source snapshots and the blind packet.

The deterministic doctor's Compute checks therefore fail, and the pilot cap of 79 binds until the
pilot runs.
