# LM1: compute attestations that do not exist yet

Written by the gauntlet's synthesis owner on 2026-10-16. Nothing below was run for LM1. This file
exists so that the bundle's `compute` record can point at a hashed statement instead of a missing
file.

| Attestation | Status | Why | What produces it |
|---|---|---|---|
| Image digest | EXISTS (D127), not LM1-specific | The stock llama.cpp b11669 image `127.0.0.1:5000/cotcodec-llamacpp@sha256:d445e09f9f0167cbce65be9fecd0f38c539b243ea321ee281ebeea259e904131` (image id `sha256:fb8600d96560412d65ec9c269b555c8db6ed4bcfd86a3556658b1c108073e848`) was built and verified by the LM1 host prep; no overlay has been built from an LM1 commit | The lane's overlay build from the freeze commit |
| Real model loop | NOT_RUN | The request runner (`harness/lm1mmq/runner.py`), grader client and analysis are not written | P0, with unit tests, before the freeze |
| Benchmark adapter | NOT_RUN | The dataset loaders, prompt rendering and graders for AA-Omniscience-Public, SimpleQA-Verified and SuperGPQA are not written | P0 |
| Container smoke | RUN for the image (job 1582, D127); NOT_RUN for LM1 | The smoke test loaded all six GGUFs in this image; no LM1 request has been sent | A test-only job per arm |
| Slurm dry run and test-only run | NOT_RUN | No LM1 manifest is rendered | `scripts/submit_docker_research_job.py manifests/lm1mmq-*.yaml --dry-run` and `--test-only` |
| Provenance verification | PARTLY (D127) | Model receipts and the image's provenance exist; the datasets are not fetched | P0's CPU-lane dataset fetch with receipts |
| Kimi on 3 GPUs | NOT_RUN | The gauntlet's host rule allows no GPU job other than the reviewer's; the fit is arithmetic only (about 15.7 GiB spare at 3 × 79.6 GiB) | P1-K's first placement attempt (K3), logged |
| Executable pilot (orx node) | NOT_RUN | No orx node exists | The pilot after a freeze and admission |

What does exist and is hashed in the bundle:
- the decision-rule simulation with seeds 42-44 (`sim_lm1.py`, `sim-lm1.json`);
- the cap and Mac-time arithmetic (`caps_lm1.py`, `caps-lm1.json`);
- the query log, the source snapshots and the blind packet.

The deterministic doctor's Compute checks therefore fail, and the executable-pilot cap of 79 binds
until the pilot runs.
