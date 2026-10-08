# K1 v3: compute attestations that do not exist yet

Recorded 2026-10-08 by the wave-1 synthesis owner of the K1 v3 gauntlet.

`q3-k1-localization-screen-v3` is a DRAFT registration. It has no code table, no image A3 or B3,
no 4B throughput probe, no smoke, no filled manifest, no Slurm dry-run or test-only run and no
provenance verification of its own. None can exist before the v3 code is written, the probe runs
under its own id, Kevin rules on admission (projected caps 7.21 GPU-h central, 9.79 high; D24) and
the file is frozen.

What exists is supplementary, listed under `supplementary_attestations` in `bundle.json`: the dense
pre-check v2's Qwen3.5-4B-Base lane (Slurm 862, COMPLETED 0:0 in 9 min 17 s) ran the 4B dense
evaluation path that v3 extends (teacher forward through the hybrid, capture at the eight
softmax-attention layers, dense block targets, selection recall, multiple choice) inside the
digest-pinned image of build 855 (CPU doctor 12/12, Slurm 856), through the Docker Slurm lane, with
provenance verification PASS, a submitter dry-run and test-only exit 0, and ORX_RESULT exit=0. No
4B indexer has been trained by anyone in this repository; the training path is unmeasured.

The two synthesis scripts (`synthesis-cost-model.py`, `synthesis-power-approximations.py`) are the
arithmetic behind the proposal's projections. They are approximations, not the registered
pre-freeze simulation (registration decision 62).
