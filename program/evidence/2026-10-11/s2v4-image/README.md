# S2 v4: shipped Arabic language packs, derived images and the development smoke

Registration: `program/preregistrations/s2-arabic-cua-locale-v4.md` (DRAFT, not frozen; decision
D80 (iv); repaired under D84 and D87). Nothing here is a Phase 0 result: the fetch and the image builds
construct the instrument, and the smokes and the oracle's development run (dev split only) decide
nothing registered. The K0 rule was committed (commit `ee0841b3`) before any image existed, and its
section is unchanged.

The download's scope (D84): `libreoffice-l10n-ar` is the download D80 (iv) approves; the two Ubuntu
language packs are public research downloads under D1, their use read under D80 (iv) with D76 (a).

## fetch/

`provenance.json`: the D80-approved download, run on the login host by
`python3 -m harness.s2_locale.fetch_langpacks --launchpad` from an export of `f1cff923`, from
`https://snapshot.ubuntu.com/ubuntu/20240110T000000Z/` (`jammy-updates`):

- `InRelease` (118,761 B, `764c2703...`) verified by `gpgv` with the Ubuntu archive keyring: GOODSIG and
  VALIDSIG, Ubuntu Archive Automatic Signing Key (2018), `F6ECB3762474EDA9D21B7022871920D1991BC93C`;
- `main/binary-amd64/Packages.xz` (1,277,024 B, `7a20811a...`) equal to the signed SHA256 entry; the
  signed index lists the guest's `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`;
- `libreoffice-l10n-ar_7.3.7-0ubuntu0.22.04.4_all.deb` (663,804 B, `76533943...`),
  `language-pack-ar-base_22.04+20230801_all.deb` (151,600 B, `d6503a11...`) and
  `language-pack-gnome-ar-base_22.04+20230801_all.deb` (930,704 B, `13e8cd8a...`), each equal to its
  signed index stanza and to Launchpad's published SHA-256 and size.

The archives stay on the host (`~/cotcodec-runs/stage0/s2v4/inputs/`).

`verify.json` (repair round): the stored files re-checked offline on the login host with the hardened
code (`fetch_langpacks.py --verify`, export of `d2f733e4`; no download): gpgv GOODSIG and VALIDSIG by the
pinned signer `F6ECB3762474EDA9D21B7022871920D1991BC93C` (fingerprint and primary key), the signed
`Suite: jammy-updates` and `Codename: jammy`, the stored signed text equal to gpgv's output,
`Packages.xz` equal to its signed hash, each `.deb` equal to its signed stanza.

## image-build-1195/ (superseded; its images deleted after build 1207 ran)

Slurm 1195 (CPU only, no GRES, `s2v4-cpu.sbatch` run mode, `cotcodec-q2-vmprobe` image
`sha256:0cde2db1...`, `--network=none`, host uid, read-only root, no capabilities; 455 s), from an
export of `9c450da0`:

- `selftest.json`: the synthetic ext4 round trip (planner refusals, readback, a planted checksum
  finding kept as baseline, a block diff that flags an unplanned file) passed before the build;
- `build-record.json`: inputs and tools, the root partition, the certified disk's `e2fsck -fn` baseline
  (one finding: inode 1214912, a VS Code TypeScript message catalogue whose checksum does not match),
  the install (404 operations: 385 files including the 4 `ucf` copies, 18 directories, 1 symlink; 26
  existing directories left as they were; 2 directories the two language packs share), its readback,
  its block-level diff against the certified disk (2,790 changed blocks, 0 unexplained), and per cell
  the selector, readback, `e2fsck` (the baseline finding only), the block diff against the base (8
  blocks for each selector-only cell, 466 for PL with its 369 rewritten toolbar definitions; 0
  unexplained) and the qcow2 (`qemu-img compare`: identical to its raw source; no backing file);
- `image-manifest.json`, `cell-manifests.json`: every path written, with mode, owner, inode and SHA-256;
- `receipt-1195.json`: the batch receipt (no GPU, network none).

Its digests were the first pins; builds 1199 and then 1207 replaced them (below).

Two earlier attempts stopped at their own checks before writing an image: Slurm 1189 (the certified
disk's pre-existing `e2fsck` finding failed a precondition that required a clean check; the build now
requires exactly the baseline's findings) and Slurm 1192 (a directory both language packs carry was
planned twice; it is now created once, as dpkg shares it).

## smoke-1197/ (development, dev split only; superseded images)

Slurm 1197 (CPU only; `s2v4-vm.sbatch`; export of `dd7ce25c`; manifest
`experiments/manifests/s2v4/dev-smoke-v1.json`): three dev tasks (`12382c62` Calc, `2b94c692`
Impress, `e528b65e` Writer) in S, E, A, ER, AR, PL and AD plus a second E boot, through `vm_probe.py`,
on the images of build 1195. The lane hashed all seven images before dispatching (every digest the
pinned one). `probes.jsonl` (the per-slot records; screenshots and accessibility trees stay on the
host), `smoke-summary.json` (`smoke_summary.py`), `preflight.txt`.

- 24 of 24 slots probed, no infrastructure loss; every guest reported its cell's selector; the 33
  Arabic catalogs present in every derived image and absent in S; PL's toolbar digest differs from
  every other image's.
- Interface as specified: Arabic chrome share 0.954 (Calc), 0.959 (Impress) and 0.979 (Writer) in A,
  AR and AD, 0 in S, E, ER and PL; the menu bar right to left in ER, AR and AD (first item "ملف" in the
  Arabic cells, "File" otherwise) and left to right elsewhere.
- Keyboard `us,us` (`setxkbmap -query`, the stock image's own value) and the stock input-method process
  `ibus-daemon` running in every slot, S included (corrected in the repair round: an earlier version of
  this file said "no input method"); the guest server's locale `LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en`;
  the postconfig's strict activation target present and its save rewrote the checked file in every slot;
  the checker's verdict on the do-nothing state `fail` in every cell of every task.
- Masked pixel differences: AD against AR 0 px on all three tasks (P7); E against E2 0-1 px (A/A); PL
  against E 26,513-50,635 px (the toolbars only).
- **Finding:** E against S 1,398 px (Calc) and 1,399 px (Writer), 1 px (Impress): E's Formatting
  toolbar shows the two text-direction buttons (left-to-right, right-to-left) that S's does not. The
  language pack's `ctl_ar.xcd` (`CTLFont` true), read after the selector in the same configuration
  layer, had overridden the selector's finalized `CTLFont` false, so CTL was on in every derived cell.
  Under the committed K0 rule this would fail I2 on the Calc and Writer tasks. The selector now declares
  a dependency on every other file of the layer (configmgr then reads it last), and the images were
  rebuilt (below). This changed the instrument on the development set, not a rule.

## image-build-1199/ (superseded by build 1207)

Slurm 1199 (CPU only, 481 s, export of `4c516761`, the self-test first): the same install (404
operations, 2,790 changed blocks against the certified disk, 0 unexplained) and six cell images whose
selector declares a dependency on every other file of the system layer (configmgr reads it last). Each
selector-only cell changes 8 blocks against the base and PL 466 (369 toolbar definitions); `e2fsck -fn`
reports only the certified disk's finding on every image; `qemu-img compare` finds each qcow2 identical
to its raw source. Superseded in the repair round: this build stamped the wall clock into each superblock, so it could not be
regenerated bit for bit. Its images stay on the host, unpinned; build 1195's images were deleted after
build 1207 ran (their records stay here).

## smoke-1201/ (development, dev split only; the images of build 1199, then pinned)

Slurm 1201 (CPU only; export of `513a5aa5`; manifest `experiments/manifests/s2v4/dev-smoke-v2.json`):
the same 24 capture slots as smoke 1197 on the images of build 1199, plus 10 gold slots
(`vm_gold.py`, the K2 injection executor unedited, then the image check) for the two tasks with a gold
(`12382c62`, `e528b65e`) in E, A, ER, AR and PL. The lane hashed all seven images before dispatching
(the pinned digests).

- 34 of 34 slots probed, no infrastructure loss; every guest reported its cell's selector.
- Interface as specified: Arabic chrome share 0.953 (Calc), 0.959 (Impress), 0.979 (Writer) in A, AR
  and AD and 0 elsewhere; the menu bar right to left exactly in ER, AR and AD; keyboard `us,us` with the
  stock `ibus-daemon` running everywhere, S included (corrected: an earlier version said "no input
  method"); every postconfig save rewrote the checked file; the do-nothing verdict
  `fail` in every cell of every task.
- Masked pixel differences: **E against S 0, 1 and 1 px** (the CTL buttons are gone); AD against AR 0
  px; E against E2 0-1 px; PL against E 26,513-48,905 px.
- Gold slots: the gold saved through the task's own postconfig and scored by the pinned checker
  **passes in all five admission cells for both tasks** (10 of 10; for `12382c62`, a task whose checker
  reads Calc's default sheet name, so the SheetPrefix pin holds in the Arabic cells).
- `k0_inputs.admission` over these records (development, three dev tasks, no instrument metrics):
  `12382c62` and `e528b65e` admitted, `2b94c692` runnable (it has no gold, so no passing-side control).

## image-build-1207/ (the pinned images; repair round, D84)

Slurm 1207 (CPU only, 16.5 minutes, `s2v4-cpu.sbatch` run mode in the `cotcodec-q2-vmprobe` image,
`--network=none`, export of `c7a2b1d0`): the self-test first (`selftest.json`: planner refusals,
readback with modification times, a second application of the plan one second later byte-identical
under the fixed time and `s_wtime` equal to it, the inode-slot, superblock-field and outside-partition
checks, and tampers that each must be flagged: an unplanned file, a changed untouched inode, a byte in
the disk's tail), then `image_build.py build-twice`: two full builds from the same inputs into `a/` and
`b/`, every `debugfs -w` session at `E2FSPROGS_FAKE_TIME` = 1754395037 (the certified root filesystem's
own `s_wtime`).

- `reproducibility.json`: both builds' digests (derived base, six cells, image manifest, cell
  manifests) identical, `reproducible` true; against build 1199's derived base one 4 KiB block differs,
  the primary superblock (its checksum and write time).
- `a/build-record.json` (the pinned build; `b/build-record.json` beside it): per image the block
  classification (the base 2,790 blocks against the certified disk, 411 changed inode slots, every one
  a touched inode; each selector-only cell 8 blocks against the base, PL 466), the whole-image checks
  (identical outside the root partition; superblock fields changed: checksum and free counts only;
  `s_wtime` the fixed time), `e2fsck -fn` (the certified disk's one finding only), the readback (404
  paths with their mtimes), `layer_files` (the system layer is `LAYER_FILES` plus `main`), and the
  qcow2 (read-only, standalone, identical to its raw source).
- `a/image-manifest.json`, `a/cell-manifests.json`: every path written, with mode, owner, mtime, inode
  and SHA-256.
- `a/maintainer-scripts/`: the three packages' control files and maintainer scripts, none of which ran
  (the language packs' `install-language-pack ar`; `libreoffice-l10n-ar`'s `ucf`/`ucfr` registration and
  `dpkg-maintscript-helper` upgrade helper; the `ucf` copies themselves are made by the build).
- `receipt-1207.json`: the batch receipt (no GPU, network none, exit 0).

Pins: `harness/s2_locale/images.json` (build a's files, host directory `image-build-v5/a`; build b's
identical files are kept as a second copy). `tests/test_s2v4_image_build.py` checks the pins against
this record and the reproducibility record.

## pd-cache/ (the PD file-cache variant; repair round)

`pd-cache-manifest.json`: built once on the login host by `python3 -m harness.s2_locale.pd_cache` from an
export of `e958a22e` (no download; copies from the pinned file cache): every file the 17 dev tasks'
setups download (23 files), each task's first supported document planted by `capture.py`'s
`plant_document` (15 tasks, every one of K0's named PD tasks; `2b94c692` and `bf4e9888` have no text run
on their first slide), with each file's SHA-256 and the plants. `files_sha256`
`d51d66fa3d3a890c6a18ad231b926e3932881209ca91e467e8532319c549b46e` is pinned in
`vm_lane.PD_CACHE_FILES_SHA256`; the lane re-checks the host directory against the manifest at submit.

## smoke-1214/ (development, dev split only; the pinned images of build 1207; repair round)

Slurm 1214 (CPU only, `s2v4-vm.sbatch`, export of `4a4ae0c5`, manifest
`experiments/manifests/s2v4/dev-smoke-v3.json`, 81 CPUs and 126 GB at V = 20): the dev part of the
census as `vm_lane.census_slots` renders it for the 17 dev tasks: 170 capture slots (S, E, E2, A, ER,
AR, PL, AD, ER2, PD) and 70 gold slots (the 14 dev tasks with a gold, in E, A, ER, AR and PL). The lane
hashed all seven images (and the PD variant at submit) before dispatching. `probes.jsonl` (every
attempt), `smoke-summary.json`, `lane-receipt.json` (host snapshots removed), `preflight.txt`,
`oracle-dev.json` and `k0-dev.json`.

- 240 of 240 slots probed; 7 re-queued once after an infrastructure loss (6 guest-server restarts found
  by the end-of-slot check, 1 undelivered accessibility tree) and probed on the second attempt.
- Held fixed, in every slot, S included: `setxkbmap` `us,us`; `ibus-daemon`; GNOME input sources
  `[('xkb', 'us')]`; IBus engine `xkb:us::eng`; `LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en` for the guest
  server and for every LibreOffice process (initial environment). Fonts and packages (end facts):
  `fc-match :lang=ar` DejaVu Sans, 20 Arabic-capable families; `fonts-kacst`, `fonts-kacst-one`,
  `locales`, `ucf`, `libreoffice-common` installed; `fonts-hosny-amiri`, `fonts-sil-scheherazade`,
  `language-pack-ar`, `language-pack-gnome-ar` unknown to dpkg.
- P0.10's reader: the same three values in every slot (`EnablePresenterScreen` `true`; the auto-save
  interval and Writer's default font absent).
- Interface: Arabic chrome share 0.952-0.979 in A, AR and AD, 0 elsewhere; menu bar right to left in
  ER, AR, AD and PD. Every postconfig save rewrote its file; the do-nothing verdict is `fail` in every
  slot of S and of every derived cell; on PD's 15 planted documents the checker raises (`error`).
- Golds: 13 of 14 pass in all five admission cells; `af23762e`'s fails in all five.
- Oracle (development run on the Mac, on copies of the renders, `oracle_vm.py --k0 --workers 6`): tol6 =
  50; synthetic document plant detected 17/17; PD detected on all 15 named tasks (not on the two without
  a plant); E-S 17/17 and E-E2 17/17 within tol6; AD-AR 16/17 (`ac9bb6cb`: 513 px in Impress's status-bar
  pointer-position readout); O1 text pairs and O4 order 100%; descriptor plants O3 13/17, O2 15/17.
  `k0-dev.json` (development; 89 pool tasks have no record here): 13 dev tasks admitted, 4 runnable.
- Boot-to-boot pairs (masked, tol6 = 50; corrected in the third round, which found that this file and
  the registration reported only the AD-AR case): E-E2 0 or 1 px on all 17 tasks; ER-ER2 0-2 px on 13
  tasks, 13 px on `936321ce` (Writer), and 293, 148 and 139 px on the Impress tasks `2b94c692`,
  `ac9bb6cb` and `e4ef0baf`; AD-AR 0 px on 16 tasks and 513 px on `ac9bb6cb`. Every differing pixel of
  the four pairs above tol6 is in Impress's status-bar pointer-position field (y 1064-1076), which takes
  a fresh value at each boot in the mirrored layout (`2b94c692`'s uncounted first ER attempt matched
  ER2 to 0 px). The cursor is drawn at the same point in all 177 capture renders (the boot's resting point, (1728, 972) as the third round's warp reads it). The third round adds a
  pointer warp to the capture (smoke 1240 below).

## apdelta-dev/ (development, dev split only; repair round)

Slurm 1217 and 1218 (CPU only, `s2v4-apdelta.sbatch`, batch SHA-256 `0423c025...`, export of
`4a4ae0c5`, 10 CPUs and 16 GB; manifest `experiments/manifests/s2v4/apdelta-dev-v1.json`, stored on the
host in canonical form as `aabbbebd...`, the same content): `ap_delta.py`'s development purpose, a
harness/q2 development workload (L0-fixed, seed 42, the three cells `click_left_center`, `type_plain`,
`key_enter`, one repetition) on the pinned images of build 1207. Each job ran two campaigns:

- a single-image campaign on E through `python3 -m harness.q2.vm.driver` unchanged (one VM, one
  screenshot-setting session): 3 of 3 trials pass in each job;
- a development rung on E and AR at N = 2 through `ap_delta.run_rung` (session i on image i mod 2:
  session 0 on E in the screenshot setting, session 1 on AR with accessibility): 6 of 6 pass in each job;
  both images hashed before and after the campaign and unchanged; no labelled container left; host
  snapshots present; no foreign job.

`summary.json` (`summarize.py`, which reads the run directories with harness/q2's own
`acceptance.load`, `counting_problems`, `foreign_abort`, `snapshot_problems` and `acceptance.rung`):
every campaign counts (no counting problem); cold boots 17.2-19.1 s; screenshot-setting steps 0.52-0.70 s
in both campaigns and the AR session's accessibility-setting steps 1.74-1.90 s (each step also fetches
the accessibility tree). `acceptance.rung` reads the development rung and, as it must, does not qualify
it (2 boots of the 20 required, and a 6-trial workload instead of the 1,200-trial order). In the
registered rung each image runs 4 sessions in each setting (sessions 0-19 screenshot, 20-39
accessibility, session i on image i mod 5), as each image's A1 reference does, so the per-image step
comparison of section "K1" is between like workloads. The job directories (receipts, preflights,
manifests, session plans) are copied here; the per-trial cycles and VM logs stay on the host. 1218
repeats 1217 from the same manifest, and its records agree with 1217's.

Timing relative to R04 (disclosed under D87): both jobs were submitted on an empty queue between steps
of R04's CPU campaign. 1217 went in about 2 s after R04's job 1216 ended; 1218 went in right after
1217 ended, while R04's driver was waiting for an empty queue to submit its next step. Neither
overlapped an R04 job, but R04's next step waited for 1218; R04's report records any effect on its
timing. These jobs also ran `ap_delta.run_rung` before the third round restored `driver.main`'s
pre-run checks in it (Docker facts, the VM and runner images, `qemu-img info`, dangling volumes).
Round 4's development rung (Slurm 1244, `program/evidence/2026-10-12/s2v4-apdelta-rung/`) ran
the same workload with those checks, and every one passed.

## smoke-1240/ (development, dev split only; third round, D87: the pointer warp)

Slurm 1240 (CPU only, `s2v4-vm.sbatch`, export of `688b2880`, manifest
`experiments/manifests/s2v4/dev-smoke-v4.json`: smoke 1214's 240 slots under a new name; 81 CPUs
requested, 82 allocated, 126 GB, V = 20; 49 minutes). Submitted at 09:51 UTC on an empty queue, once
R04's campaign had no step pending (its round-2 score had ended at 09:49 and its plan had no open step
for three checks a minute apart); no E session was in progress. `probes.jsonl` (every attempt),
`lane-receipt.json` (host snapshots removed), `preflight.txt`, `smoke-summary.json`
(`smoke_summary.py` on a copy of the capture records and renders).

- 240 of 240 slots probed; 4 re-queued once after a guest-server restart (end-of-slot check) and
  probed on the second attempt; `lane_exit=0`, no labelled container left.
- The pointer warp ran in all 174 capture attempts: before (1728, 972), after (995, 540), about
  0.23 s in the guest. Gold slots do not warp.
- Held fixed in every slot, S included, as in smoke 1214 (keyboard, input method, input sources, IBus
  engine, the guest server's and LibreOffice's `en_HK` locale variables, fonts, P0.10's values).
- Every postconfig save rewrote its file; do-nothing verdict `fail` everywhere but PD (`error` on the
  15 planted documents); golds 13 of 14 pass in all five admission cells, `af23762e`'s fails in all
  five.

## oracle-route-1241/ (development; the oracle's registered route, third round)

Slurm 1241 (CPU only, `s2v4-cpu.sbatch` run mode, `--network=none`, submitted right after 1240 ended,
on an empty queue): the metric image `sha256:2006c1a9...` running `oracle_vm.registered_argv(1)` on
smoke 1240's run directory (read-only at `/ro/run1`), the export of `688b2880` at `/src`; 34 s.
`oracle.json` and `k0.json` (development only), `receipt-1241.json`, `slurm-1241.out`, and
`mac-crosscheck.json`: the same code on the Mac, on a copy of the records and renders, gave the same
metrics, tolerances, instrument checks and K0 output in a different environment (Python 3.13, numpy
2.5, scipy 1.18, Pillow 12.3, against the container's Python 3.12.13, numpy 1.26.4, scipy 1.17.1,
Pillow 11.0.0); one reported per-task mean displacement differs in its last digit.

- tol6 = 50; tol2 0.0202, tol3 18; I1-doc holds (17/17, PD 15/15); I3, I4 100%.
- I5 AD-AR 17/17 (0 px everywhere); I6 E-E2 17/17 (at most 1 px); the three ER-ER2 tasks of 1214 at
  0 px.
- Not resolved: Impress's pointer-position field took another value in 2 of the 70 Impress capture
  boots (the window's layout still changed after the warp): ER-ER2 142 px on `af23762e` and E-S 148 px
  on `ac9bb6cb` (I2 16/17), every differing pixel in rows 1066-1074 of the status bar.
- Descriptor plants O3 17/17, O2 15/17; K0's admission on the dev tasks 13 admitted, 4 runnable.

## freeze-rehearsal/ (repair round)

`rehearsal.json`: a scratch freeze of a local clone of the branch at `0a1d18e7` (after the merge of
`main`, whose ledger has rows 1-20; origin removed, its own ledger; the real ledger was not touched):
the status fill, `scripts/preregister.py freeze` (row 21 in the clone), `verify` and `check-chain`, the
ledger row committed alone (the freeze commit changes only the ledger); every S2 v4 test file at the
freeze commit (129 passed, 1 skipped; the status test reading the frozen wording against the row);
from an export of the freeze commit, the registered census manifest (1,322 slots; `render-census
--freeze-commit`, the commit checked with git) and a census resumed from block `b010` validated, K1
manifests rendered and validated (C1 on E; C3 on AR in three parts; A3 on AR in three parts; the rung,
90 CPUs, 142 GB), and development manifests of both the lane and `ap_delta` refused. The first
rehearsal of the round (at `5d61a63a`, four test files, 78 passed) is kept under `earlier`.
