# S2 v4: Arabic interface text versus mirrored layout on the certified OSWorld stack, with the shipped Arabic language packs, a fixed Phase 0 admission rule and a registered delta certification of the action path (s2-arabic-cua-locale-v4)

Status: DRAFT. Not frozen, no ledger row. Written on 2026-10-11 by the single owner of the S2 v4
run (decision D80 (iv)) on branch `stage0/s2-v4`. It is a new experiment id: `s2-arabic-cua-locale-v3`
and `v3.1` (the package that scored 60 and 65, D74 and D76) are left unedited, and this file carries
v3.1's design with the changes listed below. D80 (iv) approved, on Kevin's delegation: fetching the
official LibreOffice Arabic language packs that match the guest's LibreOffice 7.3.7; reviewed
image-surgery code; a registered deviation of `q2-action-path-v2` for the P0.6 certification on the
derived configuration; a K0 admission rule committed in this registration before any Phase 0 result
is read; and Phase 1 (6.83 GPU-h) admitted under D24 if Phase 0 passes as registered. Phase 0 is CPU
only. Evidence for this draft: `program/evidence/2026-10-11/s2v4-image/` (the fetch provenance, the
image build record, the development smoke).

The K0 rule (section "K0: Phase 0 admission rule") and its code (`harness/s2_locale/k0_v4.py`,
`tests/test_s2v4_k0.py`) were committed in the first commit that carries this file, before any
render, save or verdict of the derived images existed. The test `tests/test_s2v4_registration.py`
pins the SHA-256 of that section's text, so any later edit before the freeze is visible; an edit
after any Phase 0 result has been read voids the commitment (a new experiment id is then needed).

## What changed from v3.1, and why

| v3.1 | v4 | Why |
|---|---|---|
| A generated pseudo-Arabic catalog in a container copy of the VM's userland | The official packages, installed into the certified disk offline: `libreoffice-l10n-ar` `1:7.3.7-0ubuntu0.22.04.4` (the guest's exact LibreOffice build), `language-pack-ar-base` and `language-pack-gnome-ar-base` `1:22.04+20230801` (GTK's and the base system's Arabic catalogs, current in `jammy-updates` beside that build) | D80 (iv); the text factor is now the shipped translation, not a stand-in |
| Packages "fetched from Launchpad" (not done) | Fetched from Ubuntu's snapshot archive at `20240110T000000Z`, `jammy-updates`; the `InRelease` file verified with `gpgv` against the Ubuntu archive keyring (Ubuntu Archive Automatic Signing Key (2018), fingerprint `F6ECB3762474EDA9D21B7022871920D1991BC93C`), `Packages.xz` matched to the signed hash, each `.deb` matched to the signed index and to Launchpad's published SHA-256 | Every link of the chain is checked (`harness/s2_locale/fetch_langpacks.py`; provenance below) |
| Image surgery and lane change unwritten | Written, unit-tested and run: `harness/s2_locale/image_build.py` (offline `debugfs -w` on a raw copy, no host root, every changed filesystem block classified), `harness/s2_locale/vm_lane.py` (S1a's lane with a per-slot cell image), `harness/s2_locale/vm_probe.py` | D76 (b) |
| Per-cell overlays, mechanism unchosen (flattened images or a backing chain) | Six standalone qcow2 images (E, A, ER, AR, PL, AD), each the derived base plus its cell's files and nothing else (checked block by block), pinned by SHA-256 in `harness/s2_locale/images.json`; the stock cell S is the certified disk itself | The lane's VM arguments stay the certified ones; only the mounted disk differs per slot |
| Phase 0 renders in a container; "every step in the lane" for Phase 0 proper | Phase 0 proper runs entirely in the VM lane on the cell images: setup, post-setup renders, accessibility trees, the task's own postconfig, checker verdicts and gold saves | Phase 1's step-0 references must come from the same lane and image; the container is no longer needed |
| Coupling remedy (FSI ... PDI wrapping of leaking strings, rewritten catalogs) | No remedy: O2's coupling-leak candidates are part of the layout treatment and are reported | A remedy would rewrite the shipped catalogs; v4 measures LibreOffice as it ships |
| Tagged cell Q (KeyID `qtz`, generated registry tags) and planted coupled-string cells PCL, PCR (generated `en_US` catalogs) | Dropped. Coverage is measured directly (the Arabic chrome share of the shipped catalogs, P0.13); content leaks directly (Arabic letters in saved files of A and AR against E) | Both cells needed generated catalogs inside the image |
| K0: a committed admission proxy (FAIL, 53 tasks), a post-hoc checker-invariance rule (105) and an I1 bar left "to be fixed before Phase 0 proper" | One K0 rule, committed now, with code: admission A1-A4 in the five admission cells, a passing-side control required for the primary census, C1 tasks held until P0.10; instrument checks with fixed bars (the document plants, invisibility, P7 and A/A gate; O1 and O4 structure are reported, since a shipped translation can itself change structure); the O3 and O2 synthetic plants gate only the oracle's descriptors | Wave 2's largest defect (K0 had a free parameter and its only pre-committed verdict was FAIL) and secondary defect 3 (22 admitted tasks had no passing-side control; two C1 tasks were admitted without P0.10) |
| `E_dir` and `MIRROR_SPECIFIC` | Renamed `X_PL` (mirror excess over the toolbar-shuffle placebo) and `EXCESS_OVER_PLACEBO`; no row names "left-to-right priors" | Wave 2 secondary defect 1: at the measured dose (the placebo moves 53% of chrome by a median 271 px, mirroring all of it by 991 px) the contrast is not a direction test |
| Moderator regressions without an application term | Application fixed effects (Calc, Impress, Writer) in every moderator regression; O8's count and the Arabic chrome share enter as deviations from their application mean | Wave 2 secondary defect 2 (application R^2 0.848 for O8) |
| P0.6 "a deviation ... is written before it runs" | The deviation of `q2-action-path-v2` is registered here (section "K1") | D76 (c), D80 (iv) |
| The cap rule "a decision the program owner has to adopt" | Adopted: D80 (iv) admits Phase 1 at 6.83 GPU-h if Phase 0 passes as registered | D80 |
| Freeze command named `v3.md` | Names this file | Wave 2 secondary defect 5 |

## Question

On Q2's certified OSWorld stack, with task instructions, documents, checkers, the system shell,
number formats, Calc's default sheet prefix and the keyboard held fixed, and LibreOffice's interface
text language (English, Arabic as shipped) and layout direction (left-to-right, mirrored) switched
separately in a 2x2, how large are (D) the main effect of mirroring the application layout and (T)
the main effect of Arabic interface text on the screenshot success of Qwen3.5-9B over OSWorld's
LibreOffice tasks?

Claim scope: `portability-protocol`, a measurement on one frozen model, two certified scaffolds and
LibreOffice Calc, Impress and Writer (Ubuntu `1:7.3.7-0ubuntu0.22.04.4`, gtk3) with Ubuntu's shipped
Arabic language pack. Primary frame: the census of admitted tasks ("on OSWorld's LibreOffice tasks
whose checker accepts their gold, on this stack"). Secondary frames: the runnable census (every task
that passes A1-A3 and A4(i)) and tasks like these (population). Application-level localization over
English documents and an English system shell only; not full operating-system localization,
instruction language, reasoning language, other models or training.

## Identity

- Experiment id: `s2-arabic-cua-locale-v4`. Code of record: the freeze commit on `stage0/s2-v4` or its
  successor.
- Model: Qwen3.5-9B, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` (receipt `0a9e052d`). Greedy
  decoding, thinking on, 2,048 output tokens per step, 15 steps, screenshot only, the matched 60 s and
  20 s settles (S1a's configuration).
- Harnesses: H-OSW-fixed (OSWorld `bfd62bdc` qwen35vl with its own-spec fixes) and H-GA (gym-anything
  `aae6f7607` qwen35vl), unchanged from `q2-stage1-rescoped-v1`; their prompts do not mention the
  interface language.
- Engine: vLLM v0.31.0 (commit `db9527a4`) on
  `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  with the cu129 overlay rebuilt from the freeze commit.
- VM lane: S1a's L0-fixed lane with the per-slot cell image (`harness/s2_locale/vm_lane.py`), V = 20
  concurrent VMs in Phase 1, offline VMs, OSWorld task configs and checkers at
  `b138d348256078fa634fc3b73567a7337c793e6b`, the pinned file cache `file_cache_1e112283`. Every VM
  setting except the mounted disk is the action-path v2 runtime (`happysixd/osworld-docker@sha256:0e6497a9...`,
  4 GiB RAM, 4 cores, `none-netns`).
- Images: the certified disk (HF `xlangai/ubuntu_osworld` `a5d9c3ea`, `Ubuntu.qcow2` sha256
  `6bf667a8...`) for S; the derived base and the six cell images built by `image_build.py` (section
  "P0.2"), pinned in `harness/s2_locale/images.json`.

## Tasks (P0.1, unchanged from v3.1)

`compute/pool/pool-v3.py` of the S2 v3 evidence bundle applied to OSWorld `test_all.json` at
`b138d348`: 117 LibreOffice single-application tasks, minus E1 infeasible (2), E2 outside the file-checker
scope (1), E3 setup clicks at screen coordinates (3), E4 checker fails its own raw gold (5): **106
tasks** (confirm 62, dev 17, reserve 27; Calc 46, Impress 40, Writer 20). C1, conditional: `0f84bef9`,
`2cd43775`, `f178a4a9` (the checker reads `registrymodifications.xcu`) enter only if P0.10 passes for
them. F1: 12 tasks read a sheet the agent creates by Calc's default name; held fixed by the SheetPrefix
pin and checked by A4. Split rules as v3.1: the 17 dev tasks are Phase 0's development set (the
oracle's tolerances, the mirror specification and every development decision are taken on them); confirm
and reserve tasks meet Phase 0 only through frozen checks; nothing about the agent is tuned on any task,
and no task is selected on an agent outcome.

## Phase 0 (CPU only; host CPU lane jobs; no GPU)

### P0.2 Inputs and the derived image (done in this draft's run)

Fetched on the login host under D80 (iv) by `python3 -m harness.s2_locale.fetch_langpacks --launchpad`
from an export of commit `f1cff923` (provenance:
`program/evidence/2026-10-11/s2v4-image/fetch/provenance.json`):

| File | URL (snapshot.ubuntu.com, `20240110T000000Z`) | Bytes | SHA-256 |
|---|---|---:|---|
| `InRelease` (jammy-updates; signed 2024-01-09T23:45:44Z) | `.../dists/jammy-updates/InRelease` | 118,761 | `764c270330bdcc948bcb1216853e901be03bcdcb57175cb07407c33245137400` |
| `Packages.xz` (main, amd64; matches the signed SHA256 entry) | `.../dists/jammy-updates/main/binary-amd64/Packages.xz` | 1,277,024 | `7a20811ae8371893345c1c5a1fe2ae58d6d2eb4ee6657a2033b5bc846f1f47f7` |
| `libreoffice-l10n-ar_7.3.7-0ubuntu0.22.04.4_all.deb` | `.../pool/main/libr/libreoffice/` | 663,804 | `765339432f140aede4af39c8cb2b2ab87077abccba768a14cb9da387a2b6a9cd` |
| `language-pack-ar-base_22.04+20230801_all.deb` | `.../pool/main/l/language-pack-ar-base/` | 151,600 | `d6503a116a4a73d7a6fecac635f50efce962b3a05ec1f2312db6c28bab9cf057` |
| `language-pack-gnome-ar-base_22.04+20230801_all.deb` | `.../pool/main/l/language-pack-gnome-ar-base/` | 930,704 | `13e8cd8a3dbd3bd3069b76f5f245c7d9f536c9011b58af099cb4966ac0c45f15` |

`gpgv` reported GOODSIG and VALIDSIG for key `F6ECB3762474EDA9D21B7022871920D1991BC93C` (keyring
`/usr/share/keyrings/ubuntu-archive-keyring.gpg`, SHA-256 `1a4dd63e...`); the same signed index lists
the guest's `libreoffice-core` `1:7.3.7-0ubuntu0.22.04.4`, so the packages are the archive's own
companions of the guest's build. Launchpad's `binaryFileUrls` reports the same SHA-256 and size for all
three (`launchpad_matches` true).

The derived base image is built offline by `image_build.py` in the `cotcodec-q2-vmprobe` container
(qemu-utils 6.2, e2fsprogs 1.46.5; `--network=none`, host uid, read-only root, no capabilities) through
`infra/slurm/host-single-node/s2v4-cpu.sbatch`:
- the certified disk is converted to a sparse raw file; its GPT root partition (start sector
  1,054,720, 61,857,792 sectors, ext4, state clean) is edited in place with `debugfs -w` at its byte
  offset, never through a mount or a device;
- every entry of the three packages' data archives is written with the archive's mode, owner and
  modification time; an existing directory is left as it is; a path that exists as a file, or whose
  parent chain holds a symlink, is refused;
- `libreoffice-l10n-ar`'s postinst copies four registry files into the system configuration layer
  with `ucf`; the same four copies are made (`Langpack-ar.xcd`, `ctl_ar.xcd`, `res/registry_ar.xcd`,
  `res/fcfg_langpack_ar.xcd` from `/usr/lib/libreoffice/share/.registry/` to
  `/etc/libreoffice/registry/`; the pairs are read from the package's postinst and must equal the
  registered list);
- not done, and recorded: the language packs' postinst (`locale-gen --keep-existing ar`: no Arabic
  system locale is generated; the system locale stays `en_US.UTF-8` in every cell) and the package
  databases (`dpkg -l` in the guest does not list the three packages; `image-manifest.json` lists every
  path written with its SHA-256);
- checks: `e2fsck -fn` reports exactly the certified disk's own finding, before and after, and nothing
  new (the certified root filesystem has one: inode 1214912, a VS Code TypeScript message catalogue,
  whose checksum does not match; read-only `debugfs` runs therefore skip checksum verification); every
  written path read back with its bytes, mode, owner and link target; a directory that two of the
  packages carry is created once (as dpkg shares it); every 4 KiB block of the root filesystem that differs from the certified disk is
  classified as data of a written file, a directory that gained an entry, the inode-table block of a
  written inode, a bitmap or a superblock or group-descriptor copy; an unexplained block fails the
  build; the qcow2 equals its raw source (`qemu-img compare`) and has no backing file.

The image digests and the block classification are in the build record
(`program/evidence/2026-10-11/s2v4-image/build/`) and in `harness/s2_locale/images.json`, which
`vm_lane.py` enforces (section "Images built", added with the pins).

## Images built

Built by Slurm job 1195 (CPU only, 455 s, from the export of commit `9c450da0`; the self-test passed
first); record `program/evidence/2026-10-11/s2v4-image/build/build-record.json`, per-path manifests
`image-manifest.json` and `cell-manifests.json`. Every image is a standalone qcow2 (virtual size
53,687,091,200 B, 64 KiB clusters, no backing file) that `qemu-img compare` finds identical to its raw
source, and `e2fsck -fn` reports on every image exactly the certified disk's one finding (inode 1214912).
Two earlier attempts stopped at their own checks before writing any image (job 1189: the certified
disk's pre-existing `e2fsck` finding; job 1192: a directory both language packs carry, created twice).

| Image | SHA-256 | Bytes | Written | Changed 4 KiB blocks (every one explained) |
|---|---|---:|---|---|
| derived base | `894528792a7c59488a6d30680b1ed39b82e68e47c8b5a7bc90585d371d895ff4` | 24,459,214,848 | 404 writes, directories and links (385 files incl. 4 `ucf` copies, 18 directories, 1 symlink) | 2,790 vs the certified disk: 2,675 file data, 14 directory, 83 inode table, 13 bitmap, 5 superblock or descriptor |
| E | `19792fbcc7b3b9bbc18b45f95cb0b09c7064b5bd8e841f144d381e5c063ea856` | 24,459,214,848 | selector (selector `f486e44f3f8f...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| A | `1d2bb7ad14148e40c4298dab04fe3cee5d53f65330da0d8e0fe82e1fcfa6eb3e` | 24,459,214,848 | selector (selector `2500c24400f4...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| ER | `f4db3bba67e4a4fd0e941385799c5569c6c49524bb44b7ce6e2a9724685df18c` | 24,459,214,848 | selector (selector `5a53083e0773...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| AR | `1cf32571aa5c0fa98fa5c5387af2d56a155566467a36c70048844d54c00517d9` | 24,459,214,848 | selector (selector `d69e21004ecc...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| PL | `d7402b1db5ff9072cc4e36fa4900bcba9966b593590fc0c3cd759f340e36a9e0` | 24,459,214,848 | selector and 369 toolbar definitions (selector `f486e44f3f8f...`) | 466 vs the base: 390 file data, 10 directory, 47 inode table, 14 bitmap, 5 superblock or descriptor |
| AD | `3d5141b647afc42cd4819f3058cd929cfff0391f423035c77fad50afef11fed7` | 24,459,214,848 | selector (selector `235f348b05a4...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |

The stock cell S is the certified `Ubuntu.qcow2` (`6bf667a8...`). Images stay read-only on the host
under the run root; `harness/s2_locale/images.json` pins them, and `tests/test_s2v4_image_build.py`
checks that it is the pin set the committed build record gives.

### P0.3 Cells and the per-slot image

Each cell image is the derived base plus the selector `/etc/libreoffice/registry/zz-s2v4-cell.xcd`
(byte-identical to the S2 v3 pilot's selector for that cell; a test checks this) and, for PL only, the
toolbar definitions whose items the seeded shuffle reorders; nothing else (checked block by block
against the base: the changed blocks of each cell are the selector's data block, the registry
directory's block, the inode-table blocks of the written and removed inodes, the bitmaps and the
superblock and group-descriptor copies).

| Cell | Interface language (`ooLocale`, `UILocale`) | `UIMirroring` | Other |
|---|---|---|---|
| S | stock (certified disk: no language pack, no selector) | stock | the O6 reference |
| E | en-US | false | pins |
| A | ar | false | pins |
| ER | en-US | true | pins |
| AR | ar | true | pins |
| PL | en-US | false | pins; every toolbar's items in the seeded order of v3.1 (369 of 386 definitions change) |
| AD | ar | key absent (the layout follows the language) | pins; P7 only |

Pins in every derived cell, finalized: `SheetPrefix` "Sheet", `CTLFont` false (overrides the language
pack's `ctl_ar.xcd`, which sets it true), `EnglishFunctionName` true. `ooSetupSystemLocale` is not set
(the system locale). No environment variable differs between cells. Nothing is written to the user
profile. E2 and ER2 (A/A replicates) are second boots of the E and ER images; PD (the planted document)
is the ER image with the task's first document replaced by its planted copy in a file-cache variant
(`capture.py`'s `plant_document`, applied to the dev tasks' cached files, hashed).

The lane (`vm_lane.py`) is S1a's lane with one change: each slot names a cell, and the VM container
mounts that cell's image read-only at `/System.qcow2` through the action-path v2 runtime's own `docker
run` arguments with only `vm.qcow2` replaced (a test checks that the argument lists of two cells differ
in that one volume argument). The job hashes every image it will mount before dispatching any slot,
and every probe record names the selector SHA-256 the guest reports, so a slot always runs on the
pinned bytes.

### P0.5 Held fixed in every cell

As v3.1: task instructions, documents and checker inputs (English, left to right); the system shell
(English, left to right; the GNOME top bar is masked in every pixel comparison); the system locale
`en_US.UTF-8` (number, date and paper defaults); the document default language; the SheetPrefix,
CTLFont and English-function-name pins; autocorrect and spelling languages; the X keyboard map `us` and
no input method; 1920x1080; the agent, decoding, step cap and settles. UI digit shaping, translated
status-bar fields, localized placeholder prompts and the language pack's own CTL default (overridden
by the pin) are part of the text treatment.

### P0.6 Delta certification of the action path (K1)

See section "K1: the registered deviation of q2-action-path-v2".

### P0.7 Capture and the render oracle, in the VM lane

One slot is one fresh VM boot on one cell image, running `vm_probe.py` in the episode container:
S1a's boot wait; the image check (the guest's selector SHA-256 equals the cell's; none in S); the task's
own setup offline from the pinned file cache (S1a's unmodified call); the guard's keyboard warm-up; the
60 s settle; two screenshots 1 s apart; the accessibility tree; window titles, `setxkbmap -query` and
input methods; the 20 s settle; the SHA-256 and mtime of every file the checker reads; the pinned
`DesktopEnv.evaluate()` with `DONE` (the task's own postconfig and its checker, on the do-nothing state);
the guest-server restart check; the files' SHA-256 and mtime again; a last screenshot. Screenshots and
trees stay on the host; records are committed. An infrastructure loss (boot, image check, transport,
undelivered observation, guest-server restart, a setup step that fails in the guest) is re-queued once
(S1a's lane rule); a slot lost twice is unobserved.

Slots: every pool task in S, E, E2, A, ER, AR, PL and AD (848 slots); every dev task also in ER2 and PD
(34). Gold slots (P0.9): every task with a gold, in E, A, ER, AR and PL. Concurrency V = 20; cells
interleaved at random within each block of 20 (PCG64 seed 42).

Oracle (`harness/s2_locale/oracle.py`, adapted to the VM's renders and OSWorld's accessibility XML
before the freeze, with every parameter decided on the 17 dev tasks by a fixed formula):
- masks in every pixel comparison: the GNOME top bar (rows 0-31) and, per render, the caret mask (the
  pixels that differ between the render's two screenshots 1 s apart), applied to both renders compared;
- tol5 = tol6 = max(50 px, 2 x the second-largest masked E-vs-E2 differing-pixel count over the dev
  tasks);
- tol2, tol3 and the accessibility offset `dy` by v3.1's formulas, on the dev tasks' VM renders;
- O1-O8 as v3.1 (O1 structure on the accessibility tree; O2 text runs; O3 mirror fidelity on
  ink-located boxes; O4 sibling order under text swap; O5 content identity of the document region; O6
  E against S; O7 window title; O8 the RTL-defect inventory). O2, O3, O5 and O8 describe the treatment
  and never exclude a task;
- planted controls: the in-application document plant PD on the dev tasks; synthetic plants on every
  task's ER screenshot (a widget shifted by tol3 + 8 px for O3, a text run with its halves swapped for
  O2, an inverted 48 x 14 block in the document region for O5).

### P0.8 Content leaks

An Arabic letter in a saved result file (the A and AR cells' postconfig saves) that E's file lacks is a
content leak; reported with the part and string; it excludes nothing unless A4 shows a verdict change.

### P0.9 Checker invariance

(i) Do-nothing control: the verdict of each capture slot's `evaluate()` (the task's own postconfig and
checker on the post-setup state). (ii) Passing-side control: the task's gold end state (the
checker-mutation study's reference gold for the task) is injected in a gold slot (after setup and the
settle, LibreOffice is closed through its own Quit, the gold uploaded through the pinned
`SetupController` upload step, reopened through the task's own open step) and saved and scored through
the pinned `evaluate()`; the executor is the K2 injection executor's code path
(`harness/q2_mutation_k2/executor.py`, reused unedited through an S2 wrapper) with the cell image
mounted.

### P0.10 Config invariance (C1 tasks)

For `0f84bef9`, `2cd43775` and `f178a4a9`: after the capture slot's postconfig, the user profile's
`registrymodifications.xcu` is read in E and in each admission cell; P0.10 passes for a task if no key
that its checker reads differs between E and any admission cell, and A4(i) holds.

### P0.11 Setup validation

The capture slots are the setup validation: A1 below.

### P0.12 Moderators, frozen before any GPU job

As v3.1 (positional exposure from S1a's English click coordinates, chrome and document clicks
separately; lexical overlap; O8's per-task count; baseline success), with application fixed effects in
every regression and O8's count and the Arabic chrome share entered as deviations from their
application mean. If the oracle's descriptors are not valid (K0 section), O8's moderator and P5's O8
route are dropped and reported as unresolved.

### P0.13 Arabic chrome share

Per task, in A and AR: the share of named, showing accessibility nodes of LibreOffice's application
subtree, outside any document subtree and other than the application and its window frames, whose name
is in Arabic script, among those with Arabic or Latin letters (`vm_probe.a11y_summary`).

### Order and cost of Phase 0

1. The freeze (section "Freeze procedure"), after the remaining pre-freeze code is built and tested on
   dev tasks and a fresh audit.
2. P0.6 (K1), about 44 VM-hours (section "K1").
3. The capture and gold sweep: 882 capture slots and about 440 gold slots, about 80 VM-hours (about 3.5
   minutes per slot); about 4 hours at V = 20; CPU only, one job at a time on an empty queue.
4. The oracle (one CPU container job) and `k0_v4.decide`: K0.

<!-- K0:BEGIN -->
## K0: Phase 0 admission rule (committed before any Phase 0 result)

This rule and its code `harness/s2_locale/k0_v4.py` are fixed. Tasks: the 106-task pool. Admission
cells: E, A, ER, AR, PL; E is the reference. Each criterion is read from the VM-lane slots of P0.7 and
P0.9 (after the lane's one re-queue of an infrastructure loss).

- A1 setup: in every admission cell the task was observed (a probed capture slot). A cell whose every
  attempt failed in the task's own setup fails A1; a cell lost to infrastructure on every attempt leaves
  the task unobserved; both exclude it.
- A2 window title: every strict `activate_window` target of the task's postconfig that E's post-setup
  window list contains is in every admission cell's list.
- A3 save: every file the checker reads that E's postconfig rewrote (its SHA-256 or mtime moved), every
  admission cell's postconfig rewrote.
- A4(i) do-nothing control: in every admission cell the checker's verdict on the post-setup state equals
  E's (pass, fail or error); E must have a verdict.
- A4(ii) passing-side control: the task's gold, saved through its own postconfig in a gold slot, passes
  in E and in every admission cell. A gold that passes in E and fails, errs or is unobserved in an
  admission cell excludes the task.
- C1: `0f84bef9`, `2cd43775` and `f178a4a9` enter only if P0.10 passes for them.

Status: a task meeting A1-A4 and C1 is **admitted** (the primary census). A task meeting A1-A3, A4(i)
and C1 whose gold does not exist or does not pass in E has no passing-side control: it is **runnable**
(Phase 1 runs it; the runnable-census frame analyses it), not admitted. Every other task is
**excluded**. O2, O3, O5, O8 and content leaks never exclude a task.

Instrument checks, each required:
- I1-doc: O5 detects the synthetic document plant (an inverted 48 x 14 block in the document region of
  the task's ER render) on 100% of tasks with an ER render; and O5 detects the in-application document
  plant PD on each of the 15 dev tasks where the S2 v3 pilot showed it on screen (`01b269ae`,
  `0e47de2a`, `12382c62`, `347ef137`, `4172ea6e`, `4ed5abd0`, `5cfb9197`, `6a33f9b9`, `6e99a1ad`,
  `936321ce`, `ac9bb6cb`, `af23762e`, `d681960f`, `e4ef0baf`, `e528b65e`).
- I2 (invisibility): masked E against S differs by at most tol6 pixels on at least 95% of tasks with both
  renders.
- I5 (P7, one layout treatment): masked AD against AR differs by at most tol6 pixels on at least 95% of
  tasks with both renders.
- I6 (A/A, the step-0 check's feasibility): masked E against E2 differs by at most tol6 pixels on at
  least 95% of tasks with both renders.

Masks and tolerance: the GNOME top bar (rows 0-31) and the per-render caret mask (pixels that differ
between the render's two screenshots 1 s apart), applied to both renders compared; tol5 = tol6 = max(50
px, 2 x the second-largest masked E-vs-E2 count over the 17 dev tasks), so one dev task with a transient
event does not set the tolerance.

**K0 passes** if at least 62 tasks are admitted and I1-doc, I2, I5 and I6 hold. Otherwise: infrastructure
exit (no Phase 1), with the images, the oracle record and the leak and defect inventories published.

Reported with K0, not part of it:
- I3 (O1's structure of showing accessibles identical for E-A and ER-AR) and I4 (O4's sibling order equal
  between E and A), each as a share of (task, pair) and of compared parents. With the shipped catalogs a
  translation can itself change structure (a longer label pushing toolbar items into an overflow menu);
  such a change belongs to the text treatment as shipped, so it does not stop Phase 1. If either share is
  below 95%, T is reported as the effect of the text treatment with its structural side effects, listed
  per task. The primary estimand D does not rest on I3 or I4.
- Descriptor validity: the oracle's O3 and O2 descriptors are valid if O3 detects the shifted-widget plant
  on at least 90% of tasks and O2 detects the halves-swapped text-run plant on at least 90%. If not, every
  O2, O3 and O8 quantity is labelled instrument-limited, and O8's moderator and P5's O8 route are dropped
  (unresolved).
<!-- K0:END -->

## K1: the registered deviation of q2-action-path-v2

`q2-action-path-v2` (frozen in ledger rows 13-15, accepted on attempt 1, D53) certified the input path
on the certified disk. Its suite's executor, catalog, corpus, verdict code, trial orders (seeds 42, 43,
44, 45 as attempt 1), sessions, infrastructure rule (section 6.1 with D30 and D33) and pass lines are
unchanged here. The deviation: (1) the guest disk is each Phase 1 cell image (E, A, ER, AR, PL; pinned
in `images.json`) instead of the certified `Ubuntu.qcow2`; (2) the suite's manifests name that image by
SHA-256 and its build record instead of the Hugging Face URL, rendered and validated by an S2 wrapper
(`harness/s2_locale/ap_delta.py`, built before the freeze; `harness/q2/` is not edited); (3) only the
checks below run. All run CPU only from the freeze commit's export, one campaign at a time.

| Check | Where | Pass line (D53's) | VM-h |
|---|---|---|---:|
| C1 detection | each of the 5 images | H-GA-buggy fails R01, R02, R05, R06, R07 and H-OSW-up fails R08-R11, each 5 of 5 | 0.12 each |
| C2 L0-raw failing set | each | exactly `l0_raw_prediction_v2.yaml`'s set fails, every other entry passes 5 of 5 (seed 45) | 0.25 each |
| C3 mutation score | each | 100% of scored, non-equivalent mutants killed (seed 42) | 2.82 each |
| C4 R-dev agreement | each, from A1's trials | every projected key, chord and Caps Lock stream equals its reference | (in A1) |
| A1 at N = 1 | each | L0-fixed passes 100% of G at 5 repetitions in the seed-43 and seed-44 shuffles under both observation settings (2,000 trials, 36 sessions); D33's excused-trial rule | 1.53 each |
| A5 reset and hygiene | each | 20 of 20 pristine reset-sentinel checks; every receipt shows the image unchanged and no leaked labelled container | 0.30 each |
| A2 harness layer | each | H-OSW-fixed and H-GA pass 100% of their expressible entries and gating R cells, 5 repetitions, both settings | 1.62 each |
| A6 Writer canary | each | L0-fixed passes 100% of `canary.yaml`'s Writer entries, 5 repetitions, screenshot setting, read back from the accessibility tree | 0.87 each |
| A3 stress | AR only | the 30 stress entries, 60 repetitions, zero failures on L0-fixed and on each harness where expressible | 4.76 |
| V = 20 rung | the 5 images interleaved, 4 VMs each | the ladder rung's rule (section 9): the seed-43 shuffle under both settings passes with at most two excused trials in the rung | about 2 |

Total about 44 VM-hours. **K1 passes** if every check passes on every image named. Not rerun, and why:
A4 (volume) and A7 (observation service) carry over from D53 because the block-level build check shows
that every byte outside LibreOffice's language files and the selector (and PL's toolbar definitions) is
the certified disk's, so the X server, the guard, the tap, PyAutoGUI and the guest server are
unchanged; Phase 1 is screenshot only (A7 gates only the accessibility setting), and Phase 0's
accessibility calls are not agent-facing (an undelivered one is an infrastructure loss, re-queued).
There is no repair attempt within v4: a failed check is K1, and a repair is a new image and a new
registration.

## What the D53 certification covers for the cells

The runtime, the harness adapters, the lane and V at most 32 carry over (D53). Not covered by D53 and
covered here: the cell images ("another image": P0.6), the keyboard map under an Arabic interface (A1,
A6, the per-episode keyboard check), the guest server under localized LibreOffice (the capture slots'
restart checks), the concurrency Phase 1 uses (the V = 20 rung).

## Development smoke (dev split only; not Phase 0, not evidence for K0 or K1)

Before the freeze, the derived images are smoke-tested in the VM lane on dev tasks only (purpose
`development`, which `vm_lane.py` refuses once this id is frozen): one Calc, one Impress and one Writer
task (`12382c62`, `2b94c692`, `e528b65e`) in S, E, A, ER, AR, PL and AD, plus a second E boot, through
`vm_probe.py` with `evaluate` on. It checks that every image boots in the certified runtime, carries its
selector, sets the task up, renders the cell as specified (Arabic chrome share near 1 in A, AR and AD and
0 in the English cells; the menu bar's order right to left in ER, AR and AD), keeps the `us` keyboard
map, and saves through the task's own postconfig. Its records are under
`program/evidence/2026-10-11/s2v4-image/smoke/`; it decides nothing registered and changes no rule above.

## Phase 1 (admitted under D80 (iv) if K0 and K1 pass)

- P1.1 Tasks: the runnable census (admitted plus runnable, at most 106). Cells: E, A, ER, AR.
- P1.2 Placebo cell PL: the en-LTR interface with the toolbar items in the fixed seeded order, n_pl = 2
  per task (one per harness).
- Episodes: n = 4 per (task, cell) in the 2x2 (2 per harness) and 2 in PL: 18 per task (1,908 at 106).
- Order: one serving session (one GPU job and its CPU VM job). Task blocks in a seeded order (PCG64 seed
  42); within a block the 18 episodes in a seeded interleave; cells assigned to VM slots at random within
  each batch of 20, slot and batch recorded.
- Step-0 check: each episode's first screenshot, masked as in K0, against the Phase 0 E/A/ER/AR/PL
  render of its (task, cell) from the same lane and image, within tol6; a mismatch makes the episode
  invalid.
- Keyboard check: `setxkbmap -query` reports `us` and no input method runs at every episode start; a
  failure is an infrastructure loss.
- Image check: the guest's selector SHA-256 equals the cell's at every episode start; a mismatch is an
  infrastructure loss.
- Re-queue: an infrastructure loss or a step-0 failure is re-queued at the end of its task block, at most
  twice per episode. A task enters the analysis if each of its four 2x2 cells has at least 2 valid
  episodes (and PL at least 1 for the placebo contrasts).
- Cap (D22 counting; the cap rule adopted by D80 (iv)): one job, ceil(3 + L/60 + (N x s / V + drain) x
  1.2 x 1.05 / 60) minutes with L = 113.2 s, drain = 104.6 s, V = 20, N = 18 K and s = 197.73 s, plus 6
  minutes for the overlay build and retry; 6.83 GPU-h at K = 106 (7.70 at the p95 slot). Beyond the cap
  K8 stops the job at the last complete task block.

  | K | episodes | physical GPU-h (high slot) | job cap incl. overlay (min) | cap (GPU-h) |
  |---:|---:|---:|---:|---:|
  | 62 | 1,116 | 3.13 | 245 | 4.08 |
  | 89 | 1,602 | 4.46 | 346 | 5.77 |
  | 106 | 1,908 | 5.30 | 410 | 6.83 |

## Estimands

Per task t, cell means y_en, y_arL, y_enR, y_arR (harnesses equally weighted).

- **Primary, D (layout main effect)**, on the admitted census: D = mean_t D_t, D_t = ((y_arR - y_arL) +
  (y_enR - y_en)) / 2; R_D = S_RTL / S_LTR with S_RTL = mean_t (y_enR + y_arR) / 2 and S_LTR = mean_t
  (y_en + y_arL) / 2.
- **Secondary, T (Arabic interface text main effect)**: T = mean_t ((y_arL - y_en) + (y_arR - y_enR)) /
  2, with R_T likewise. T changes language, script, UI digits and the word overlap between English
  instructions and interface labels together.
- **Placebo contrasts (en level):** P = mean_t (y_PL - y_en), the effect of the toolbar shuffle; X_PL =
  mean_t (y_enR - y_PL), the mirror's excess over the toolbar shuffle. X_PL is not a direction test: the
  shuffle moves fewer elements by less (53% of located chrome by a median per-task mean of 271 px;
  mirroring all of it by 991 px; S2 v3 pilot), so an excess can come from displacement magnitude alone.
- **Secondary:** Delta = T + D; the interaction I; M_ar = ar-RTL - ar-LTR and G = ar-LTR - en; D and T by
  harness and application (descriptive); fractional checker scores; D and T without the 7 S1a-flagged
  tasks and without the `compare_pptx_files` tasks; D and T on the runnable census (secondary frame);
  process metrics by cell.
- **Moderators** (task-level regressions, CR2 standard errors, application fixed effects, baseline
  success as a covariate): D_t on positional exposure (chrome and document clicks separately) and on O8's
  count (within application); T_t on lexical overlap and on the Arabic chrome share (within
  application). A mechanism is named only if the 95% CR2 interval excludes 0 in the predicted direction
  (negative); otherwise "unresolved".
- **Reference:** the en cell against S1a's 9B English success on the S1a-overlap tasks of the admitted
  census (K5).

## Decision rules (primary D; the same labels are reported for T)

Census frame (primary; the admitted census). Var(D) = (1/K^2) sum_t v_t, where v_t sums, over the four
cells, (1/4) x the unbiased variance of the cell mean, per (task, cell, harness) from its m valid
episodes, m/(m-1) p(1-p)/m. log R_D has delta-method variance Var(S_RTL)/S_RTL^2 + Var(S_LTR)/S_LTR^2.

- **PRESENT:** the 95% normal interval of D excludes 0 (PRESENT_HARM or PRESENT_BENEFIT). The stratified
  randomization test of the sharp null (strata task x harness x text level, successes fixed; S = sum
  (k_RTL - k_LTR) with variance 4v) is reported beside it; disagreement at 0.05 gives PRESENT_FRAGILE.
- **SMALL:** the 90% interval of D lies inside (-5, +5) pp and the 90% interval of log R_D lies inside
  (log 0.85, -log 0.85). PRESENT and SMALL can hold together (PRESENT_AND_SMALL).
- **INCONCLUSIVE:** neither. **SMALL is suppressed** (SMALL_DEGRADED_INSTRUMENT) if K5 fires.
- **Governing labels for P3 (total effect, no mechanism):** CONFIRMED if PRESENT_HARM; FALSIFIED if SMALL
  without PRESENT, or PRESENT_BENEFIT; OPEN otherwise.
- **Placebo reading (decides only whether a relocation mechanism may be named):** X_PL in the population
  frame (t interval over tasks, df K - 1): EXCESS_OVER_PLACEBO if its 95% interval lies below 0; NO_EXCESS
  if its 90% interval lies inside (-5, +5) pp; otherwise UNRESOLVED. A Negative-Result row that names
  relocation requires EXCESS_OVER_PLACEBO and P5's slope; no row names left-to-right priors; otherwise D
  is reported as a net change of the mirrored interface.

Population frame and runnable-census frame (secondary, reported, not decision-bearing): as v3.1 (t
interval over task-level D_t; the concentration guard for SMALL_POP).

Margins: 5 pp absolute and a ratio inside (0.85, 1/0.85), fixed before data (v3.1's reasons).

## Kill criteria

| Id | Trigger | Consequence |
|---|---|---|
| K0 | Fewer than 62 tasks admitted, or I1-doc, I2, I5 or I6 fails (section "K0") | Infrastructure exit: images, oracle record, leak and defect inventories published; no Phase 1 |
| K1 | Any P0.6 check fails on any of the five images | No Phase 1 on these images; a repair is a new image and a new registration |
| K2 | More than 5% of a cell's episodes are infrastructure losses after re-queue | INCOMPLETE |
| K3 | More than 2% of a cell's episodes fail the step-0 check after re-queue | INCOMPLETE |
| K4 | The en cell's census mean success lies outside [0.15, 0.85] | UNINFORMATIVE: D and T claims dropped |
| K5 | On the S1a-overlap tasks, the 90% interval of (en cell - S1a 9B English success) lies entirely below -5 pp | INSTRUMENT_DEGRADED: no SMALL claim |
| K6 | D and T both SMALL and neither PRESENT | Publish the robustness null for application-level localization of these tasks; drop the locale arm from S3's plan |
| K7 | Neither D nor T PRESENT | No reasoning-language arm |
| K8 | The Phase 1 cap is reached | Stop at the last complete task block; analyse if at least 62 admitted tasks are complete, else INCOMPLETE |
| K9 | D PRESENT_HARM and X_PL not EXCESS_OVER_PLACEBO | D is reported as a net change; no relocation row is claimed |

## Predictions and falsifiers

| | Prediction | Falsifier |
|---|---|---|
| P1 | Phase 0 admits at least 62 tasks and the gating instrument checks hold | K0 (reachable: the pilot's stand-in catalog admitted 83 tasks with a passing gold; the shipped catalogs can localize window titles and placeholder text, and VM renders vary between boots) |
| P2 | P0.6 passes on the five images | K1 |
| P3 | D < 0 (a total effect, no mechanism attached) | D is SMALL (census) or PRESENT_BENEFIT. Simulated P(SMALL) under the null: 0.975 at K = 106, 0.962 at K = 105, 0.879 at K = 62 (v3.1's power-v4 tables, n = 4) |
| P4 | T < 0 | T is SMALL (census) or PRESENT_BENEFIT |
| P5 | The D_t slope on positional exposure is negative | its 95% CR2 interval lies above 0 |
| P6 | The T_t slope on lexical overlap is negative | its 95% CR2 interval lies above 0 |
| P7 | The layout switch is one treatment whether set by the key or by the language | I5 fails |
| P8 | The mirror cost exceeds the toolbar shuffle's (X_PL < 0) | X_PL NO_EXCESS (population frame) |

## Statistics, sample sizes and simulation

Unchanged from v3.1 (`compute/power-v4/power-v4.py`, Slurm 1142; seeds 42, 43, 44; tables in v3.1's
section "Statistics, sample sizes and simulation" for K = 106, 105 and 62). The admitted census is
expected near 83 tasks (the pilot's count of tasks whose gold passes after the GUI-faithful save), where
the operating characteristics lie between the K = 62 and K = 105 tables (null SMALL between 0.88 and
0.96; PRESENT_HARM at a 15% uniform relative harm between 0.85 and 0.95). Before Phase 1 the simulation
is rerun on the realized admitted task list (CPU, reported; no rule depends on it).

## Seeds

Simulation: 42, 43, 44. Phase 0 slot order and Phase 1 episode order, slot assignment and the sharp-null
test: PCG64 seed 42. vLLM request seed 42 (inert under greedy decoding; reruns are not assumed identical).
The P0.6 suite: attempt 1's seeds (42, 43, 44, 45).

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0 (P0.6, capture and gold sweep, oracle) | 0 | CPU-only lane and container jobs, no GRES; about 44 + 80 VM-hours |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a |
| Phase 1 (one job, K at most 106, n = 4 in the 2x2, n_pl = 2) | 6.73 | ceil(3 + 113.2/60 + (1,908 x 197.73/20 + 104.6) x 1.2 x 1.05 / 60) = 404 minutes |
| Registered total | 6.83 | below D20's 8 GPU-h line; admitted by D80 (iv) if K0 and K1 pass |

## Infrastructure failures and exclusions

As `q2-stage1-rescoped-v1` section 15 and D56, plus the image check: an undelivered observation, a
guest-server restart, a setup or postconfig server error (HTTP 500 or above, or no reply), a VM or
container failure, an engine error or timeout, a failed keyboard check and a failed image check are
infrastructure losses; a step-0 mismatch is invalid. Both are re-queued (at most twice in Phase 1; once
in Phase 0's lane). Model behaviour is never infrastructure.

## Data rights

OSWorld task configs and checkers: Apache-2.0. LibreOffice and `libreoffice-l10n-ar`: MPL-2.0. Ubuntu
language packs: translations under their upstream projects' licences (recorded in each package's
`copyright` file, written into the image). The derived and cell images are derived works under those
licences and stay on the host; they are not redistributed. Public cotcodec artefacts are metrics,
hashes, codings and per-slot records; screenshots, accessibility trees and trajectories stay on the
host. No personal data; the VMs are offline.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the image surgery has a synthetic ext4 self-test (planner
   refusals, readback, a block-level diff that must flag an unplanned file) run before the build, and the
   build itself classifies every changed block; the lane and probe have unit tests; the oracle reads
   screenshots and accessibility trees independently of the switch code; a fresh agent audits Phase 0
   against this file before the freeze.
2. Hallucinated citation: the packages' provenance is a signed chain recorded with URLs and hashes.
3. Hallucinated result: no localized-agent measurement exists; every number is from a job record.
4. Shortcut reliance: the agent may succeed from English document content; that is the estimand.
5. Bug reframed as insight: a half-mirrored layout, a clipped status bar or a localized title could look
   like a treatment effect; O3, O5, O7 and O8 exist for that, A2 excludes title failures, and O8's
   defects are reported as part of the treatment.
6. Methodology fabrication: the K0 rule is committed with code before any Phase 0 result; the dev smoke
   decides nothing registered.
7. Frame-lock: the census frame is declared before data; the runnable-census and population frames are
   reported beside it; the infrastructure exits K0 and K1 are first-class results.

## Owner's prior forecast (not a decision input)

K1 passes on the five images: 0.85. K0 passes (at least 62 admitted, instrument checks hold): 0.75 (the
pilot had 83 of 105 tasks with a passing gold; VM renders add boot-to-boot variation the container did not
have). Descriptors valid: 0.6. Phase 1 reached: about 0.6. If it runs: D PRESENT_HARM 0.35, D SMALL 0.45,
EXCESS_OVER_PLACEBO given D PRESENT_HARM 0.5, T PRESENT_HARM 0.45, T SMALL 0.35.

## Freeze procedure

1. Build and test, on dev tasks only, the remaining Phase 0 code: the oracle's adapter to VM renders and
   OSWorld's accessibility XML, the gold-slot wrapper of the K2 injection executor, the PD file-cache
   variant, the P0.10 reader, the capture and gold sweep renderer, and `ap_delta.py` for P0.6.
2. A fresh agent's pre-freeze audit checks this file against the images, the code and the K0 commitment.
3. `uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v4 program/preregistrations/s2-arabic-cua-locale-v4.md`,
   then `verify` and `check-chain`.
4. From the freeze commit's export: P0.6 (K1), then the capture and gold sweep, the oracle and
   `k0_v4.decide` (K0).
5. If K0 and K1 pass as registered, Phase 1 is admitted under D80 (iv) and runs within its cap.

## Design decisions (for the owner's acceptance)

v4 adds 80-90 (v3.1's 54-79 carry over except 60, 64, 69, 75 and 79, which v4 replaces):

80. The official Arabic packages from Ubuntu's signed snapshot archive (replaces 69's source).
81. Offline image surgery with `debugfs -w` on a raw copy, the `ucf` copies made, no maintainer scripts,
    and a block-level check of every changed block (replaces 69's route).
82. Standalone, digest-pinned cell images and a per-slot image in S1a's lane (replaces 76's open choice).
83. Phase 0 entirely in the VM lane.
84. No coupling remedy (replaces 60).
85. Q, PCL and PCR dropped (replaces 64 and 75).
86. The K0 rule above, with the passing-side control and the C1 hold (replaces 73's operationalization
    and 79's open bar).
87. The instrument checks split: the document plants, I2, I5 and I6 gate K0; I3 and I4 are reported; the O3
    and O2 plants gate only the descriptors (replaces 79 and amends 73's instrument list).
88. X_PL and EXCESS_OVER_PLACEBO (renames 71's labels).
89. Application fixed effects in the moderator regressions (amends 77).
90. The P0.6 deviation of `q2-action-path-v2` as registered in section "K1" (amends 62).
