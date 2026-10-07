---
name: scripts-skill
description: Procedure for CoTCodec validators, submitters, doctors, provenance and orx entry points.
---

# cotcodec / scripts

## Purpose
<!-- agent-docs:fill:purpose -->

Scripts make every repeated research operation executable: validate contracts,
build source archives, submit receipted Slurm jobs, run doctors and verify
provenance.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `submit_docker_research_job.py` is the discovery-lane submitter (Docker on
  Slurm 21.08.5). `submit_research_job.py` is the Pyxis lane, blocked until the
  host has Pyxis. Both reject archived memory workloads.
- `orx_run.py` is the single fixed run command for OpenResearch nodes.
- `validate_architecture_experiments.py`, `validate_provider_models.py` and
  `research_direction_doctor.py` fail closed on contract drift.
- `run_translation_supervised_indexer_doctor.py` is Q3's CPU doctor;
  `fla_throughput_doctor.py` measures training throughput on the node.
- Q3 K1: `run_sparse_indexer_phase0a.py` is the GPU entry point (phases smoke,
  headroom-dev, resume-test, 0a-k1, 0a-k1-extend; PID-1 signal protocol; exit
  codes 0/2/3/75), `run_sparse_indexer_k1_doctor.py` its CPU doctor on a tiny
  model (needs the architecture extra), `build_sparse_indexer_k1_bundle.py` the
  two-stage bundle builder, `compare_sparse_indexer_resume.py` the R0/R2 check
  and `fill_sparse_indexer_k1_manifests.py` fills `experiments/manifests/` from
  measured artifacts (a resumed leg's predecessor is chosen from its
  `termination.env`, and it shares the predecessor's run root); it fills the
  main job, its continuation and the extension only after SMOKE_PASS,
  PROCEED_TO_K1 and an equivalent resume test bound to image B, the bundle,
  the frozen preregistration and its tabled code digests (program decision
  D16).
- `run_holo3_rerun_audit_doctor.py` is Q2's Holo3 rerun audit; its v2 stages
  refuse to run until `q2-holo3-rerun-audit-v2` is frozen in the repository
  ledger (a scratch `--ledger` alone does not open the gate), and a v2 receipt
  is CONFIRMATORY only on the committed ledger with the code unchanged since
  the freeze and, with trajectories, a feature file from a CONFIRMATORY
  `v2-tarball` receipt (`--tarball-receipt`). `v2-design` reads
  already-inspected data only.
- `create_source_archive.py`, `verify_compute_provenance.py` and
  `verify_publication_attestation.py` bind source, image and claims.

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- Runnable as modules and by file path; insert the project root before repo
  imports when launched as `python path/to/script.py`.
- Validate inputs before creating output, refuse overwrite, write a temporary
  file, then atomically replace.
- Return distinct exit codes for expected falsification versus infrastructure crash.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Submit a GPU job | `--dry-run`, then `--test-only`, then submit. See `docs/operations.md`. |
| Add a doctor | Name it `run_<name>_doctor.py` so `orx_run.py` admits it. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- A seeded workload declares `seed_binding` in its manifest, parses with
  `allow_abbrev=False`, and gives its seed option no short alias; see the
  lane section of `docs/operations.md`.
