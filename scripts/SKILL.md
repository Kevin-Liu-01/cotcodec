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
- `create_source_archive.py`, `verify_compute_provenance.py` and
  `verify_publication_attestation.py` bind source, image and claims.
- `run_vllm_throughput_probe.py` is the serving-throughput probe
  (serving-throughput-probe-v1): `plan`, `run`, `vllm-args-doctor`, `project`,
  `digest`.
  `build_vllm_overlay_on_h100.sh` builds its vLLM overlay image and
  `render_serving_probe_manifest.py` fills its manifest templates from receipts
  (job C only from an accepted job A whose control X1 passed). `project` reads
  only accepted jobs whose summary lists the point files on disk and whose lane
  `termination.env` (in the output directory's parent) shows a clean exit.

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

- The seed-binding check in the submitters only knows the archived memory
  scripts. A new seeded workload must add its own binding before it runs.
