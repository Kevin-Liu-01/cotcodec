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

- `fetch_langpacks.py`: the download, run once on the login host: snapshot.ubuntu.com `InRelease`
  verified by `gpgv` with the pinned signer and the signed Suite/Codename, `Packages.xz` and each
  `.deb` matched to the signed index and to Launchpad; `--verify DIR` re-checks a fetched directory
  offline. Provenance: `program/evidence/2026-10-11/s2v4-image/fetch/`.
- `image_build.py`: runs in the `cotcodec-q2-vmprobe` container through
  `infra/slurm/host-single-node/s2v4-cpu.sbatch`; copies the certified disk to raw, writes the packages
  (and the postinst's `ucf` copies) into the ext4 root with `debugfs -w` at the certified disk's own
  `s_wtime` (`E2FSPROGS_FAKE_TIME`, reproducible), then each cell's selector (and PL's toolbars),
  checks every changed block (inode slots, superblock fields, outside the partition), writes
  read-only standalone qcow2s. `selftest` first; `build-twice` requires identical digests.
- `images.json`: the cell images' SHA-256, sizes and selector digests (from the build record);
  `vm_lane.py` and `ap_delta.py` refuse any other image.
- `vm_lane.py` + `infra/slurm/host-single-node/s2v4-vm.sbatch`: S1a's lane with a per-slot cell image
  (only `vm.qcow2` changes per slot; PD slots mount the ER image and the PD file-cache variant).
  Purposes: `development` (dev tasks, before the freeze) and `phase0` (after it, from the freeze
  commit's export, exactly the pinned census `experiments/manifests/s2v4/phase0-census.json`,
  `render-census`). `vm_probe.py` runs in the episode container (setup, renders, accessibility tree,
  keyboard and locale facts, the task's postconfig and checker, P0.10's reader, end facts;
  postconfig server errors are infrastructure); `vm_gold.py` runs a gold slot (the K2 injection
  executor, unedited, then the image check and the same postconfig rule); `guest/s2_guest.py` is
  their read-only guest helper; `smoke_summary.py` summarizes a development run.
- `golds.py`: the gold rows (the checker-mutation study's `controls.gold_pairs`, unedited) ->
  `experiments/manifests/s2v4/golds-v4.jsonl`. `pd_cache.py`: the planted-document variant (built
  once on the host, pinned by `vm_lane.PD_CACHE_FILES_SHA256`).
- `oracle_vm.py`: the v3 oracle on the VM renders and OSWorld's XML: K0's masked counts, tol6,
  I1-doc's plants, O1-O5 and the descriptor plants; `--k0` also runs `k0_inputs` + `k0_v4.decide`.
- `k0_v4.py`: the K0 admission rule exactly as the registration's committed section states it
  (`tests/test_s2v4_registration.py` pins that section's hash); `k0_inputs.py` turns lane records into
  its admission inputs for every pool task (P0.10 from the reader).
- `ap_delta.py` + `infra/slurm/host-single-node/s2v4-apdelta.sbatch`: K1, the registered deviation of
  `q2-action-path-v2` on the cell images: q2 campaigns run by harness/q2's unedited driver, the N = 20
  rung over five images by `run_rung`, the pinned plan `experiments/manifests/s2v4/k1-plan.json`,
  `verdict` (acceptance's own functions, the rung's step p95 per image).
- `pins_table.py`: the registration's "Code and inputs of record" table (re-filled at the status fill).

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
| Dev smoke | `python3 -m harness.s2_locale.vm_lane render-census --pool POOL --golds GOLDS --dev-only --purpose development --name NAME --run-root ROOT --out M.json`, check `squeue`, `vm_lane submit M.json --source-dir .` from the export |
| Phase 0 sweep (after the freeze) | From the freeze commit's export: `vm_lane render-census --freeze-commit SHA --repo REPO --source-dir .`, then `submit` on an empty queue |
| K1 (after the freeze) | `ap_delta render CHECK --cell CELL --source-dir EXPORT --git-sha SHA --images-root DIR --out M.json` (or `rung`), then `ap_delta submit` from the export, one job at a time; `ap_delta verdict JOBS... --freeze-commit SHA` |
| Oracle | `python -m harness.s2_locale.oracle_vm --runs RUN... --pool POOL --out oracle.json --k0 k0.json --workers N` (numpy, scipy, Pillow: the metric image) |
| Change K0 | Not allowed after a Phase 0 result has been read: a new experiment id |
