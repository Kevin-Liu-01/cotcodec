# S2 v3 wave 1: compute attestations (what ran, what did not)

Written by the single synthesis owner on 2026-10-11. Every host action below was a CPU-only
Slurm job with no GRES, submitted only after `squeue` showed an empty queue, one at a time,
through `infra/slurm/host-single-node/s2v3-pilot-cpu.sbatch` (a path-only copy of the D12 CPU lane
`q2-mutation-cpu.sbatch`: no GPU device nodes visible, `--network=none`, read-only root filesystem,
all capabilities dropped, the host user's uid:gid, tmpfs scratch). Image:
`cotcodec-q2-lo-vm@sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361` (the
certified OSWorld VM's own userland, LibreOffice 1:7.3.7-0ubuntu0.22.04.4, plus Xvfb and openbox;
built for the checker-mutation study). Host run root: `~/cotcodec-runs/stage0/s2v3-phase0-pilot/`
(screenshots stay there). No root, no docker-group escalation, `~/cotcodec` untouched, nothing
downloaded.

## Ran

| Job | Script (exact copy in this bundle) | Wall | Exit | What it established |
|---|---|---|---|---|
| 1096 | `pilot/s2v3_pilot.py` (first version, not kept) | 2 min | cancelled by the owner | headless UNO did not connect; debugged in 1097 |
| 1097 | `pilot/s2v3_debug.py` | about 1.5 min | 0 | cause: `SAL_USE_VCLPLUGIN=gtk3` makes `--headless` open a display (record `pilot/job1097/`) |
| 1098 | `pilot/s2v3_pilot.job1098.py` | 4.6 min | 0 | switch mechanics and content probes (record `pilot/job1098/pilot-record.json`, receipt `run-1098.json`) |
| 1099 | `pilot/s2v3_pilot_b.job1099.py` with `pilot/s2v3_pilot.job1099.py` | 7.6 min | 0 | 106 pool tasks x 3 cells at the post-open state (record and Mac-side analysis `pilot/job1099/`) |
| 1100 | `pilot/s2v3_pilot_b.job1100.py` with `pilot/s2v3_pilot.job1100.py` | 5.7 min | 0 | 106 tasks x 2 cells with AT-SPI dumps; O3 analysis `pilot/job1100/o3-analysis.json` |

The current `pilot/s2v3_pilot_b.py` adds only URL decoding of cache paths (jobs 1099 and 1100 failed to
stage one task whose file name contains `#`, `%23` in its URL; the file is in the cache).

Mac-side analyses: `pilot/s2v3_pilot_b_analysis.py` (job 1099), `pilot/s2v3_o3_analysis.py` (job 1100).
CPU simulations: `power/power-v3.py` (output `power-v3.json`, log `power-v3.log`, tables `tables-v3.py`
and `tables-v3.md`), `pool/pool-v3.py` (output `pool-v3.json`).

## Did not run, and why

- The derived Arabic image (registration P0.2): needs `libreoffice-l10n-ar` 1:7.3.7-0ubuntu0.22.04.4
  (663,804 B), `language-pack-ar-base` 22.04+20230801 (151,600 B) and `language-pack-gnome-ar-base`
  22.04+20230801 (930,704 B) from the Launchpad librarian. The lane has no network, so these are
  downloads on the login host: an outward action this run did not take and that waits on Kevin's
  go-ahead. The offline build script (`dpkg-deb -x` plus `debugfs -w` in the `cotcodec-q2-vmprobe`
  image) and a lane version that accepts a new image digest and the 27 reserve tasks
  (`harness/q2_stage1/lane.py` pins `QCOW2_SHA256`; line 253 accepts only pool and dev tasks) are not
  written.
- The VM-lane render oracle (P0.7), the delta certification of the action path (P0.6), the tagged
  pseudo-catalog cell (P0.8), the functional A/A (P0.9), config invariance (P0.10) and the offline
  setup pass in the VM (P0.11).
- No orx experiment node: the jobs ran through the CPU lane directly, not through
  `uv run --locked python scripts/orx_run.py` over a committed `experiments/orx/node.yaml`.
- Phase 1: no manifest, no Slurm dry run or test-only, no GPU.

## Doctor fields

- `container_smoke`: PASS for the Phase 0 pilot container only (job 1098, exit 0, receipt hashed).
  It is not a smoke of the Phase 1 engine image.
- `slurm_test`: NOT_RUN for Phase 1 (the pilot's CPU jobs were real submissions, not a dry run of a
  Phase 1 manifest).
- `provenance_verification`: NOT_RUN.
- `real_model_loop`: false for S2 (S1a's loop exists; no S2 episode has run).
