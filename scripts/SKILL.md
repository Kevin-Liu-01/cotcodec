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
  Archives hold regular files only. `--discovery` leaves out a symlink only
  under a reviewed rule (link under `.agents/skills/`, target under
  `.claude/skills/`: the agent-skill mirror), when it is tracked as a link, its
  target is canonical (a run of `..`, then named parts with no empty, `.` or
  `..` part), stays inside the repository, passes through no other symlink,
  lands on disk where its text says, and names a tracked regular file the
  archive holds or a directory holding one. Any other symlink is refused,
  including dangling links and links that leave the repository. The schema 3
  receipt records the rules and each omitted `{path, target}` with a digest;
  for a clean worktree the creator checks the record equals HEAD's committed
  links (`committed_symlinks`), so anyone with the repository can recompute it
  from `git_tree`. `archive_sha256` and `file_manifest_sha256` cover archived
  files only, so omitting a link gives the same archive as deleting it, and
  nothing the lane pins binds the record: an edited receipt can empty it.
  `extract_discovery_source_archive.py` holds an identical rule (a test checks
  the source matches), accepts schema 3, accepts schema 2 only for capsules
  retained before schema 3 (so a stripped record cannot pass as schema 2),
  checks each omitted target is archived, and never recreates links.
  Publication archives still refuse every symlink.
- `run_vllm_throughput_probe.py` is the serving-throughput probe
  (serving-throughput-probe-v1): `plan`, `run`, `vllm-args-doctor`, `project`,
  `digest`.
  `build_vllm_overlay_on_h100.sh` builds its vLLM overlay image and
  `render_serving_probe_manifest.py` fills its manifest templates from receipts
  (job C only from an accepted job A whose control X1 passed). `project` reads
  only accepted jobs whose summary lists the point files on disk and whose lane
  `termination.env` (in the output directory's parent) shows a clean exit.
- `run_vllm_throughput_probe_v2.py` is serving-throughput-probe-v2 (`plan`,
  `run`, `vllm-args-doctor`, `project`, `digest`): it subclasses the frozen v1
  runner and adds the warm-up reservation (G0.9), PID-based contamination, the
  launch-window ledger and X1 on identical prompts. Never edit the v1 driver:
  both digests cover it. `render_serving_probe_v2_manifest.py` renders its one
  job's manifest.

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
