# S2 v4: shipped Arabic language packs, derived images and the development smoke

Registration: `program/preregistrations/s2-arabic-cua-locale-v4.md` (DRAFT, not frozen; decision
D80 (iv)). Nothing here is a Phase 0 result: the fetch and the image build construct the instrument,
and the smoke (dev split only) decides nothing registered. The K0 rule was committed (commit
`ee0841b3`) before any image existed.

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

## image-build-1195/

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

Pins: `harness/s2_locale/images.json` (a test checks it equals the pin set this record gives).

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
- Keyboard `us,us` (`setxkbmap -query`, the stock image's own value) and no input method in every slot;
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

## image-build-1199/ (the pinned images)

Slurm 1199 (CPU only, 481 s, export of `4c516761`, the self-test first): the same install (404
operations, 2,790 changed blocks against the certified disk, 0 unexplained) and six cell images whose
selector declares a dependency on every other file of the system layer (configmgr reads it last). Each
selector-only cell changes 8 blocks against the base and PL 466 (369 toolbar definitions); `e2fsck -fn`
reports only the certified disk's finding on every image; `qemu-img compare` finds each qcow2 identical
to its raw source. Digests: the registration's section "Images built" and
`harness/s2_locale/images.json`. The images of build 1195 stay on the host, superseded and unpinned.

## smoke-1201/ (development, dev split only; the pinned images)

Slurm 1201 (CPU only; export of `513a5aa5`; manifest `experiments/manifests/s2v4/dev-smoke-v2.json`):
the same 24 capture slots as smoke 1197 on the images of build 1199, plus 10 gold slots
(`vm_gold.py`, the K2 injection executor unedited, then the image check) for the two tasks with a gold
(`12382c62`, `e528b65e`) in E, A, ER, AR and PL. The lane hashed all seven images before dispatching
(the pinned digests).

- 34 of 34 slots probed, no infrastructure loss; every guest reported its cell's selector.
- Interface as specified: Arabic chrome share 0.953 (Calc), 0.959 (Impress), 0.979 (Writer) in A, AR
  and AD and 0 elsewhere; the menu bar right to left exactly in ER, AR and AD; keyboard `us,us` and no
  input method everywhere; every postconfig save rewrote the checked file; the do-nothing verdict
  `fail` in every cell of every task.
- Masked pixel differences: **E against S 0, 1 and 1 px** (the CTL buttons are gone); AD against AR 0
  px; E against E2 0-1 px; PL against E 26,513-48,905 px.
- Gold slots: the gold saved through the task's own postconfig and scored by the pinned checker
  **passes in all five admission cells for both tasks** (10 of 10; for `12382c62`, a task whose checker
  reads Calc's default sheet name, so the SheetPrefix pin holds in the Arabic cells).
- `k0_inputs.admission` over these records (development, three dev tasks, no instrument metrics):
  `12382c62` and `e528b65e` admitted, `2b94c692` runnable (it has no gold, so no passing-side control).
