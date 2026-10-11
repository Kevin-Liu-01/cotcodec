---
name: harness-s2-locale-skill
description: Procedure for S2 (Arabic interface text against mirrored layout on the certified OSWorld stack) in harness/s2_locale/: the v3 container pilot and the v4 derived images, VM lane, probe and K0 rule.
---

# cotcodec / harness / s2_locale

## Purpose

S2 asks how much mirroring LibreOffice's layout (D) and switching its interface text to Arabic (T)
change Qwen3.5-9B's success on OSWorld's LibreOffice tasks. v3 (`capture.py`, `catalog.py`,
`oracle.py`, `phase0.py`, `goldsave.py`, `score_gold.py`) is the CPU pilot that ran in a container copy
of the VM's userland with a generated pseudo-Arabic catalog (D74, D76). v4
(`program/preregistrations/s2-arabic-cua-locale-v4.md`, DRAFT; D80 (iv)) uses the shipped Arabic
packages inside real VMs.

## Mental model & key files (v4)

- `fetch_langpacks.py`: the D80-approved download, run once on the login host: snapshot.ubuntu.com
  `InRelease` verified by `gpgv`, `Packages.xz` and each `.deb` matched to the signed index and to
  Launchpad. Provenance: `program/evidence/2026-10-11/s2v4-image/fetch/`.
- `image_build.py`: runs in the `cotcodec-q2-vmprobe` container through
  `infra/slurm/host-single-node/s2v4-cpu.sbatch`; copies the certified disk to raw, writes the packages
  (and the postinst's `ucf` copies) into the ext4 root with `debugfs -w`, then each cell's selector
  (and PL's toolbars), checks every changed block, writes standalone qcow2s. `selftest` first.
- `images.json`: the cell images' SHA-256, sizes and selector digests (from the build record);
  `vm_lane.py` refuses any other image.
- `vm_lane.py` + `infra/slurm/host-single-node/s2v4-vm.sbatch`: S1a's lane with a per-slot cell image
  (only `vm.qcow2` changes per slot); `vm_probe.py` runs in the episode container (setup, renders,
  accessibility tree, keyboard, the task's postconfig and checker); `vm_gold.py` runs a gold slot
  (the K2 injection executor, unedited, then the image check); `guest/s2_guest.py` is their
  read-only guest helper; `smoke_summary.py` summarizes a development run (masked pixel
  differences, chrome language and direction, saves, verdicts).
- `k0_v4.py`: the K0 admission rule exactly as the registration's committed section states it
  (`tests/test_s2v4_registration.py` pins that section's hash); `k0_inputs.py` turns lane records
  into its admission inputs (the instrument checks still need the oracle's VM adapter).

## Patterns to follow / invariants

- Never edit `harness/q2/`, `harness/q2_stage1/`, `harness/q2_mutation/` or `harness/q2_mutation_k2/`
  (frozen by other registrations); S2 code imports them.
- Before v4 is frozen only `development` lane jobs on dev-split tasks run; Phase 0 proper runs from the
  freeze commit's export.
- Screenshots, accessibility trees and images stay on the host; commit records and hashes only.
- Host jobs: CPU-only Slurm, one at a time, submitted only on an empty queue.

## Common tasks → first action

| Task | First action |
|---|---|
| Rebuild the images | On the host, export a commit, then `s2v4-cpu.sbatch` run mode with the vmprobe image and argv `python3 -m harness.s2_locale.image_build build --certified /ro/vm/Ubuntu.qcow2 --debs /inputs/debs --out /out` |
| Dev smoke | `python3 -m harness.s2_locale.vm_lane render --base BASE.json --tasks ... --cells S,E,A,ER,AR,PL,AD --out M.json`, check `squeue`, `vm_lane submit M.json --source-dir .` |
| Change K0 | Not allowed after a Phase 0 result has been read: a new experiment id |
