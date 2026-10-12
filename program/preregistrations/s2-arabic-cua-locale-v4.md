# S2 v4: Arabic interface text versus mirrored layout on the certified OSWorld stack, with the shipped Arabic language packs, a fixed Phase 0 admission rule and a registered delta certification of the action path (s2-arabic-cua-locale-v4)

**Status: DRAFT, not frozen; no ledger row.** Written on 2026-10-11 by the single owner of the S2
v4 run (decision D80 (iv)) on branch `stage0/s2-v4`, and repaired in one round under D84 (section
"Changes in the repair round (D84): review log" lists every review and audit item and its
disposition). It is a new experiment id: `s2-arabic-cua-locale-v3` and `v3.1` (the package that
scored 60 and 65, D74 and D76) are left unedited, and this file carries v3.1's design with the
changes listed below. D80 (iv) approved, on Kevin's delegation: fetching the official LibreOffice
Arabic language packs that match the guest's LibreOffice 7.3.7; reviewed image-surgery code; a
registered deviation of `q2-action-path-v2` for the P0.6 certification on the derived
configuration; a K0 admission rule committed in this registration before any Phase 0 result is
read; and Phase 1 (6.83 GPU-h) admitted under D24 if Phase 0 passes as registered. The owner also
fetched Ubuntu's `language-pack-ar-base` and `language-pack-gnome-ar-base`, which are not
LibreOffice packs: D84 records them as public research downloads under D1, their use read under D80
(iv) together with D76 (a) ("the applications' real Arabic language packs"); P0.2 states that
reading and the packages' unmet dependencies. Phase 0 is CPU only. Evidence for this draft:
`program/evidence/2026-10-11/s2v4-image/` (the fetch provenance and its offline re-check, the image
builds, the PD file-cache variant, the development smokes and the oracle's development run).

The K0 rule (section "K0: Phase 0 admission rule") and its code (`harness/s2_locale/k0_v4.py`,
`tests/test_s2v4_k0.py`) were committed in the first commit that carries this file, before any
render, save or verdict of the derived images existed. The test `tests/test_s2v4_registration.py`
pins the SHA-256 of that section's text, so any later edit before the freeze is visible; an edit
after any Phase 0 result has been read voids the commitment (a new experiment id is then needed).

## What changed from v3.1, and why

| v3.1 | v4 | Why |
|---|---|---|
| A generated pseudo-Arabic catalog in a container copy of the VM's userland | The official packages, installed into the certified disk offline: `libreoffice-l10n-ar` `1:7.3.7-0ubuntu0.22.04.4` (the guest's exact LibreOffice build), `language-pack-ar-base` and `language-pack-gnome-ar-base` `1:22.04+20230801` (the base system's and GNOME's Arabic catalogs, current in `jammy-updates` beside that build) | `libreoffice-l10n-ar`: D80 (iv). The two Ubuntu packs: D1, read with D80 (iv) and D76 (a) (D84; P0.2). The text factor is now the shipped translation, not a stand-in |
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
| Freeze command named `v3.md` | Names this file; the status line is rewritten to the frozen wording before the freeze, and the ledger row is committed alone (section "Freeze procedure") | Wave 2 secondary defect 5; the D32 defect class (repair round) |
| Images built once, digests of one build's files | Reproducible build: every `debugfs -w` session runs at the certified disk's own last write time (`E2FSPROGS_FAKE_TIME`), one job builds twice and requires identical digests, and the images are re-pinned (section "Images built") | Repair round (review blocking item 1) |
| Phase 0 and K1 code "built before the freeze" | Built and dev-tested: the oracle's VM adapter (`oracle_vm.py`), the PD file-cache variant (`pd_cache.py`), the P0.10 reader, the census renderer and the registered `phase0` purpose of `vm_lane.py`, `ap_delta.py` with its plan and batch file; registered jobs run only from the freeze commit's export | Repair round (audit blocking item 1) |
| Phase 1 rules written, no executor | Phase 1's step-0 mask, keyboard check, image check and infrastructure rule defined here; its runner and analysis code are a Phase 1 executor addendum, dry-run on dev tasks, audited and frozen as its own ledger row before any Phase 1 episode | Repair round (audit blocking item 2) |

## Question

On Q2's certified OSWorld stack, with task instructions, documents, checkers, the system shell,
number formats, Calc's default sheet prefix and the keyboard held fixed, and LibreOffice's interface
text language (English, Arabic as shipped) and layout direction (left-to-right, mirrored) switched
separately in a 2x2, how large are (D) the main effect of mirroring the application layout and (T)
the main effect of Arabic interface text on the screenshot success of Qwen3.5-9B over OSWorld's
LibreOffice tasks?

Claim scope: `portability-protocol`, a measurement on one frozen model, two certified scaffolds and
LibreOffice Calc, Impress and Writer (Ubuntu `1:7.3.7-0ubuntu0.22.04.4`, gtk3) with the shipped
Arabic packs (LibreOffice's `libreoffice-l10n-ar`, and Ubuntu's base and GNOME Arabic catalogs,
installed without their maintainer scripts and possibly inert under the guest's stock locale; P0.2),
in the guest's stock locale (`LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en`) and keyboard. Primary frame: the census of admitted tasks ("on OSWorld's LibreOffice tasks
whose checker accepts their gold, on this stack"). Secondary frames: the runnable census (every task
that passes A1-A3 and A4(i)) and tasks like these (population). Application-level localization over
English documents and an English system shell only; not full operating-system localization,
instruction language, reasoning language, other models or training.

## Identity

- Experiment id: `s2-arabic-cua-locale-v4`. Code of record, in D56's words: every export runs from
  the commit that adds the ledger row (the freeze commit). `vm_lane.py` and `ap_delta.py` admit a
  registered job only from a source tree whose ledger holds this id's row with an unbroken chain,
  whose registration still has the row's SHA-256 and whose `.git_sha` is the manifest's freeze
  commit; their renderers check with git that this commit's only parent is the row's
  `git_head_at_freeze` and that it changes only the ledger. The files of record are pinned by
  SHA-256 in section "Code and inputs of record" (a test keeps the table equal to the tree).
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

Fetched on the login host by `python3 -m harness.s2_locale.fetch_langpacks --launchpad` from an export
of commit `f1cff923` (provenance: `program/evidence/2026-10-11/s2v4-image/fetch/provenance.json`).
Approval: `libreoffice-l10n-ar` is the download D80 (iv) approves (the official LibreOffice Arabic
language pack of the guest's LibreOffice 7.3.7). `language-pack-ar-base` and
`language-pack-gnome-ar-base` are Ubuntu's base-system and GNOME Arabic catalogs, not LibreOffice
packs: they are public research downloads under D1, and D84 reads their use under D80 (iv) together
with D76 (a), which asked Kevin about "the applications' real Arabic language packs" generally. The
owner fetched them for GTK's own dialog strings (v3.1 P0.2's three-package plan); whether they act
at all is open (below).

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
three (`launchpad_matches` true). The fetch code now also pins the signer (a valid signature by any
other key in the host keyring is refused, VALIDSIG fingerprint and primary key both), refuses BADSIG,
ERRSIG, NO_PUBKEY, EXPSIG, EXPKEYSIG and REVKEYSIG status lines, and requires the signed `Suite` and
`Codename` to be `jammy-updates` and `jammy` (unit-tested, with a tampered `Packages.xz`); its
`--verify` mode re-checked every link of the stored files offline with that code (no download),
recorded in `fetch/verify.json`.

Unmet dependencies, disclosed. No maintainer script runs and the package databases are not edited, so
dpkg would leave the packs unconfigured. From the signed stanzas: `language-pack-ar-base` Depends
`language-pack-ar (>= 1:22.04+20230801)` and `language-pack-gnome-ar-base` Depends
`language-pack-gnome-ar (>= 1:22.04+20230801)`, neither installed (both are the per-release update
packages over the `-base` catalogs); `libreoffice-l10n-ar` Depends `libreoffice-common`, `locales |
locales-all` and `ucf`, which the guest has, and Recommends `fonts-hosny-amiri`, `fonts-kacst`,
`fonts-sil-scheherazade` and `libreoffice-core (>> 1:7.3.7)`, of which only `fonts-kacst` and
`libreoffice-core` are installed. Fonts (v3.1's facts, re-read in every v4 slot by the probe's end
facts): no font is added; `fonts-kacst`, `fonts-kacst-one` and DejaVu already cover Arabic, and
`fc-match :lang=ar` gives DejaVu Sans. The maintainer scripts (committed with the build record) would
do three things that are not done: the two language packs' postinst runs
`/usr/share/locales/install-language-pack ar` (which generates the Arabic locales that
`/var/lib/locales/supported.d/ar` lists), and `libreoffice-l10n-ar`'s postinst registers its four
`ucf` copies with `ucfr` and calls `dpkg-maintscript-helper symlink_to_dir` for its doc directory (an
upgrade helper with nothing to do on a fresh install). So no Arabic system locale exists in any
cell, and the guest's
stock locale (`LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en`, as every slot of the development smokes records
for the guest server, S included) is held fixed. LibreOffice's interface language is set by the
selector, not by the locale. Under `LANGUAGE=en_HK:en` GTK's gettext may never select the GNOME pack's
Arabic catalogs, so that pack is possibly inert: the probe records each LibreOffice process's initial
locale variables (`/proc/PID/environ`), and v4 claims nothing about GTK's own strings.

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
- not done, and recorded: every maintainer script (the three packages' control files and maintainer
  scripts are copied into the build directory and committed, `maintainer-scripts/`, so the "not run"
  claims can be audited) and the package databases (`dpkg -l` in the guest does not list the three
  packages; `image-manifest.json` lists every path written with its SHA-256);
- reproducibility: `debugfs -w` stamps the superblock's write time (and new inodes' times, which the
  plan then sets itself) from libext2fs's clock; every write session runs with `E2FSPROGS_FAKE_TIME`
  set to the certified root filesystem's own last write time (`s_wtime`, read from its primary
  superblock), so the images are a function of the code and the inputs; one CPU job builds twice into
  two directories and requires every digest to be identical (`image_build.py build-twice`);
- checks: `e2fsck -fn` reports exactly the certified disk's own finding, before and after, and nothing
  new (the certified root filesystem has one: inode 1214912, a VS Code TypeScript message catalogue,
  whose checksum does not match; read-only `debugfs` runs therefore skip checksum verification); every
  written path read back with its bytes, mode, owner, link target and modification time; a directory
  that two of the packages carry is created once (as dpkg shares it); the system layer's files are
  checked at build time against the selector's dependency list (`check_layer_files`); every 4 KiB block
  of the root filesystem that differs from the reference is classified as data of a written file, a
  directory that gained an entry, an inode-table block in which only the slots of written, removed or
  linked inodes changed (compared slot by slot), a bitmap, or a superblock or group-descriptor copy, and
  an unexplained block fails the build; outside the root partition (GPT, EFI partition, tail) the raw
  disks must be byte-identical; of the superblock fields `dumpe2fs -h` prints only the free counts,
  lifetime writes, the checksum and the write time may differ, and the write time must be the fixed
  build time; the qcow2 equals its raw source (`qemu-img compare`), has no backing file and is
  read-only.

The image digests, the block classification and the reproducibility record are in the pinned build's
record (`program/evidence/2026-10-11/s2v4-image/image-build-1207/`) and in
`harness/s2_locale/images.json`, which `vm_lane.py` and `ap_delta.py` enforce (section "Images built").

## Images built

Built by Slurm job 1207 (CPU only, from the export of commit `c7a2b1d0`; the self-test passed
first), twice in the same job (`image_build.py build-twice`, 466 s and 464 s): every write session
ran at `E2FSPROGS_FAKE_TIME` = 1754395037 (2025-08-05T11:57:17Z, the certified root filesystem's own
last write time), and the two builds gave identical digests for the derived base, every cell image,
the image manifest and the cell manifests (`reproducible` true). Records:
`program/evidence/2026-10-11/s2v4-image/image-build-1207/` (`reproducibility.json`; build a's
`build-record.json`, `image-manifest.json`, `cell-manifests.json`; `maintainer-scripts/`). The pins
are build a's files (host directory `image-build-v5/a`); build b's identical files are kept beside
them. Every image is a standalone, read-only qcow2 (virtual size 53,687,091,200 B, 64 KiB clusters,
no backing file) that `qemu-img compare` finds identical to its raw source; `e2fsck -fn` reports on
every image exactly the certified disk's one finding (inode 1214912); every image is identical to
its reference outside the root partition; of the superblock fields only the checksum and the free
block and inode counts changed against the certified disk; the system layer is `LAYER_FILES` plus
`main`. Against build 1199's derived base (the earlier pins) one 4 KiB block differs, the primary
superblock (its checksum and write time; `only_superblock_copies_differ` true): the file contents
are the same, so development smoke 1201's findings carry over, and smoke 1214 repeated them
on these images. Earlier builds: jobs 1189 and 1192 stopped at their own checks before writing any
image (the certified disk's pre-existing `e2fsck` finding; a directory both language packs carry,
planned twice); job 1195 built images whose selector was read before the pack's `ctl_ar.xcd`
(deleted after this build); job 1199 built the previous pins without a fixed time (kept,
superseded).

| Image | SHA-256 | Bytes | Written | Changed 4 KiB blocks (every one explained) |
|---|---|---:|---|---|
| derived base | `d186f41ef5cec71ef2f961c6eb0151481012388825654a847bd58da6937def1a` | 24,459,214,848 | 404 writes, directories and links (385 files incl. 4 `ucf` copies, 18 directories, 1 symlink) | 2,790 vs the certified disk: 2,675 file data, 14 directory, 83 inode table, 13 bitmap, 5 superblock or descriptor; 411 inode slots |
| E | `51e47abbeed62176aa8d6a60db12c873f4b6c63a90f1e4f3a30514f0d58fdf42` | 24,459,214,848 | selector (selector `62d176fa8135...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| A | `1250098963189effe71fd4e949407f8d8b94543fb192de472ae4572f09c10df2` | 24,459,214,848 | selector (selector `081a34eb90c6...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| ER | `262fe7093d5fbdce466eb9bf15229706a5131d76cb8d7e145f7262eb5096b607` | 24,459,214,848 | selector (selector `d7a7c43f2af3...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| AR | `77cd9a2ab6aa37ef6c7d80ff27486b63e2f2e8a417c46d2768c1d8020cc6311f` | 24,459,214,848 | selector (selector `89b110b48f9e...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |
| PL | `5a4102eefbbaf9e4ad78d499267270c4fdb4671ccff4d6dba777196817aa6ed2` | 24,459,214,848 | selector and 369 toolbar definitions (selector `62d176fa8135...`) | 466 vs the base: 390 file data, 10 directory, 47 inode table, 14 bitmap, 5 superblock or descriptor |
| AD | `d1429751efca0fbbf959f7b2933feab4bc6d36c08e743bb0b4754ed2d562bef1` | 24,459,214,848 | selector (selector `3d2b12f95537...`) | 8 vs the base: 1 file data, 1 directory, 1 inode table, 2 bitmap, 3 superblock or descriptor |

The stock cell S is the certified `Ubuntu.qcow2` (`6bf667a8...`). Images stay read-only on the host
under the run root; `harness/s2_locale/images.json` pins them, and `tests/test_s2v4_image_build.py`
checks that it is the pin set the committed build record gives. The lane's image check (job
1214) re-hashed every cell image and S on the host before dispatching.

### P0.3 Cells and the per-slot image

Each cell image is the derived base plus the selector `/etc/libreoffice/registry/zz-s2v4-cell.xcd`
(the S2 v3 pilot's selector for that cell, byte for byte, after a block of `<dependency .../>`
declarations on every other file of the system layer, `main` required and the rest optional, so that
configmgr reads the selector last in its layer and its finalized values win there; tests check both)
and, for PL only, the
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
pack's `ctl_ar.xcd`, which sets it true), `EnglishFunctionName` true. The dependency block is a
development finding (smoke 1197, dev split): configmgr reads the files of a layer in directory order
unless dependencies order them, and a later file of the same layer overrides an earlier one's
finalized value; without the block `ctl_ar.xcd` was read after the selector, CTL was on in every
derived cell, and E's Formatting toolbar showed the two text-direction buttons that S's does not
(masked E against S: 1,398 and 1,399 px on the Calc and Writer dev tasks). `ctl_ar.xcd` sets only
`CTLFont` (true); the pin overrides it in every derived cell, E included, so the pack's CTL file is a
constant of the derived base, which I2 (E against S) guards. `ooSetupSystemLocale` is not set (the
locale settings follow the guest's stock locale, `en_HK.UTF-8`). No environment variable differs
between cells. Nothing is written to the user profile. E2 and ER2 (A/A replicates) are second boots
of the E and ER images. PD (the planted document) is the ER image with the task's first document
replaced by its planted copy: the lane mounts, for PD slots only, the planted-document file-cache
variant built by `harness/s2_locale/pd_cache.py` (every file the 17 dev tasks' setups download,
copied from the pinned cache, each task's first supported document planted by `capture.py`'s
`plant_document`: its main part's first text run becomes "S2V3 PLANTED CHANGE"). The variant is
pinned by its manifest's `files_sha256` `d51d66fa3d3a890c6a18ad231b926e3932881209ca91e467e8532319c549b46e`
(`program/evidence/2026-10-11/s2v4-image/pd-cache/pd-cache-manifest.json`; 23 files, plants on 15 dev
tasks, every one of K0's 15 named tasks; `2b94c692` and `bf4e9888` have no text run on their first
slide). Rule for a plant the VM view does not show, fixed before the freeze: the variant is
development, decided on the dev tasks only; if the development smoke shows a named task's planted run
off screen (O5 does not flag PD there), that task's plant moves to the first text run its E render
shows, chosen on the dev render, and the variant is rebuilt and re-pinned before the freeze. K0's list
of 15 never changes, and after the freeze nothing about PD changes.

The lane (`vm_lane.py`) is S1a's lane with one change: each slot names a cell, and the VM container
mounts that cell's image read-only at `/System.qcow2` through the action-path v2 runtime's own `docker
run` arguments with only `vm.qcow2` replaced (a test checks that the argument lists of two cells differ
in that one volume argument); a PD slot mounts the ER image and, in its episode container, the PD
variant in place of the pinned file cache. The job hashes every distinct image it will mount before
dispatching any slot (its Slurm minutes include that time: `check_slurm` requires ceil(image GB / 30)
minutes for it, 6 minutes for the seven images), and every probe record names the selector SHA-256
the guest reports, so a slot always runs on the pinned bytes.

### P0.5 Held fixed in every cell

As v3.1, with the guest's own values: task instructions, documents and checker inputs (English, left
to right); the system shell (English, left to right; the GNOME top bar is masked in every pixel
comparison); the guest's stock locale `LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en` (number, date and paper
defaults; as every slot of the development smokes records for the guest server, S included; v3's
container forced `en_US.UTF-8`, which the VM does not use); the document default language; the
SheetPrefix, CTLFont and English-function-name pins; autocorrect and spelling languages; the stock
keyboard: `setxkbmap -query` layout `us,us`, the stock input-method process (`ibus-daemon`, running in
every slot of the smokes, S included) and GNOME's configured input sources, each equal to the stock
cell S's record (Phase 1's keyboard check, below); 1920x1080; the agent, decoding, step cap and
settles. UI digit shaping, translated status-bar fields and localized placeholder prompts are part of
the text treatment; the language pack's `ctl_ar.xcd` is not (it is in every derived cell, and the
CTLFont pin overrides its only key).

### P0.6 Delta certification of the action path (K1)

See section "K1: the registered deviation of q2-action-path-v2".

### P0.7 Capture and the render oracle, in the VM lane

One slot is one fresh VM boot on one cell image, running `vm_probe.py` in the episode container:
S1a's boot wait; the image check (the guest's selector SHA-256 equals the cell's; none in S); the task's
own setup offline from the pinned file cache (the PD variant for PD slots; S1a's unmodified call); the
guard's keyboard warm-up; the 60 s settle; two screenshots 1 s apart; the accessibility tree; window
titles, `setxkbmap -query`, the input-method processes, GNOME's input sources, IBus's engine and each
LibreOffice process's initial locale variables; the 20 s settle; the SHA-256 and mtime of every file
the checker reads; the pinned `DesktopEnv.evaluate()` with `DONE` (the task's own postconfig and its
checker, on the do-nothing state); the guest-server restart check; the files' SHA-256 and mtime again;
P0.10's reader; a last screenshot; the end facts (fonts; `dpkg-query` status of the packs' unmet
dependencies and recommendations). Screenshots and trees stay on the host; records are committed.

Infrastructure, the one rule of section "Infrastructure failures and exclusions": a failed boot, image
check or setup step in the guest, a guest transport failure, an undelivered observation, a guest-server
restart, or a postconfig server error (a postconfig `/setup/*` reply with no HTTP status or a status of
500 or above: the guest server's own failure; a non-zero `returncode` under HTTP 200 is the guest's
state and is scored) is an infrastructure loss: the slot is re-queued once at the end of its block (S1a's
lane rule), and a slot lost twice is unobserved. `vm_probe.py` and `vm_gold.py` implement it (tested).
In Phase 0 no agent acts before the postconfig, so a postconfig server error is not an outcome anyone
influenced; scoring it would let one transient guest-server failure change A3 or A4(i).

Slots (the census): every pool task in S, E, E2, A, ER, AR, PL and AD (848 slots); every dev task also
in ER2 and PD (34); a gold slot (P0.9) per task with a gold in each of E, A, ER, AR and PL (88 tasks,
440 slots); 1,322 in all. Order: the tasks in a seeded order; per task its capture slots and then its
gold slots; the sequence cut into 67 blocks of 20, each block shuffled (one PCG64(42) generator,
`vm_lane.census_slots`); the lane dispatches a block only after the previous one is dispatched, so the
cells of a block run side by side. The census is committed before the freeze
(`experiments/manifests/s2v4/phase0-census.json`, SHA-256
`02bfc97bf8c14f48f2bfd57c26a34b5fac0b57d9aa18981b474a286d38589cf0`, pinned in `vm_lane.CENSUS_SHA256`),
and the registered `phase0` job runs exactly these slots: one CPU job at V = 20 (81 CPUs, 126 GB,
ceil(6 + 1.5 x 1,322 x 3.5 / 20 + 10) = 364 minutes requested, the expected time near 4 hours plus the
image check). A `phase0` job that ends before every slot has a final record is resumed once by a
`phase0` job whose slots are the census from the first block without one (`resume_from_block`, naming
the interrupted job's record file by SHA-256); per slot the earlier job's final record stands
(`k0_inputs.counted`).

Oracle (`harness/s2_locale/oracle_vm.py`: v3's `oracle.py` and `phase0.py` plants on the VM's renders and
OSWorld's accessibility XML; every parameter decided on the 17 dev tasks by a fixed formula; it runs as
one CPU container job in the checker-mutation metric image after the sweep):
- renders: a (task, cell, rep) render is the counted capture attempt when it ended `probed`;
  accessibility nodes are LibreOffice's application subtree with screen boxes, roles from the XML tags;
- masks in every pixel comparison: the GNOME top bar (rows 0-31) and, per render, the caret mask (every
  pixel that differs between the render's two screenshots 1 s apart), applied to both renders compared;
  a pixel differs when a channel differs by more than 20 (v3's `pixel_diff` threshold), counted on the
  first screenshots (the exact count is reported beside it);
- tol5 = tol6 = max(50 px, 2 x the second-largest masked E-vs-E2 differing-pixel count over the dev
  tasks); tol2 and tol3 by v3.1's formulas on the dev tasks' VM renders; the accessibility offset is 0
  (in the VM's GNOME session AT-SPI reports LibreOffice's widgets at their screen position; v3.1's
  container estimate picks 24-27 px on the dev renders, which moves the document box onto the
  sheet-tab and scroll bars, and is reported only);
- O1-O8 as v3.1 (O1 structure on the accessibility tree; O2 text runs; O3 mirror fidelity on
  ink-located boxes; O4 sibling order under text swap; O5 content identity of the document region; O6
  E against S; O7 window title; O8 the RTL-defect inventory). O2, O3, O5 and O8 describe the treatment
  and never exclude a task;
- planted controls (K0's I1-doc and descriptors): the reference for a document plant is the unplanted
  render of the same image, so the check isolates the plant from the layout treatment (on the Calc and
  Writer dev renders O5 of E against ER flags the mirrored layout, which changes the visible part of the
  document region). The synthetic plant is an inverted 48 x 14 block in the document region of each
  task's ER render (ER's own accessibility box), detected when O5 of ER against the planted ER flags it
  (the plant exceeds tol5 through O5's alignment); a task with an ER render and no document region
  counts as not detected. PD is detected when O5 of ER against PD flags it. O5 against E is reported
  beside both. The O3 and O2 descriptor plants (a widget shifted by tol3 + 8 px, a text run with its
  halves swapped) are drawn on each task's ER render with a per-task PCG64 generator seeded by (42, the
  task id's first 32 bits).

### P0.8 Content leaks

An Arabic letter in a saved result file (the A and AR cells' postconfig saves) that E's file lacks is a
content leak; reported with the part and string; it excludes nothing unless A4 shows a verdict change.

### P0.9 Checker invariance

(i) Do-nothing control: the verdict of each capture slot's `evaluate()` (the task's own postconfig and
checker on the post-setup state). (ii) Passing-side control: the task's gold end state (the
checker-mutation study's reference gold for the task) is injected in a gold slot (after setup and the
settle, LibreOffice is closed through its own Quit, the gold uploaded through the pinned
`SetupController` upload step, reopened through the task's own open step) and saved and scored through
the pinned `evaluate()`; the executor is the K2 injection executor (`harness/q2_mutation_k2/executor.py`, reused unedited
through `harness/s2_locale/vm_gold.py`, which adds the image check and the postconfig server-error
rule) with the cell image mounted; the gold files come from the pinned file cache, each checked against
the cache's receipts. The gold rows are `harness/s2_locale/golds.py`'s, the checker-mutation study's own
definition used unedited (`harness.q2_mutation.controls.gold_pairs`: every `vm_file` result paired with
a `cloud_file` expected file of the cache, complete, and not byte-identical to the initial downloads):
88 of the 106 pool tasks (`experiments/manifests/s2v4/golds-v4.jsonl`, SHA-256
`4ac326bd10dbda9ef1e266ffe247cd25f5a2e602e582404a798fadf4908dc71a`; the K2 executor's candidate digest
is the first file's in VM-path order); the other 18 have no passing-side control (K0: runnable at
best), among them the three C1 tasks.

### P0.10 Config invariance (C1 tasks)

For `0f84bef9`, `2cd43775` and `f178a4a9`: after the capture slot's postconfig, the user profile's
`registrymodifications.xcu` is read in E and in each admission cell; P0.10 passes for a task if no key
that its checker reads differs between E and any admission cell, and A4(i) holds. The reader
(`vm_probe.P010_KEYS`, read through the guest helper's `registry` mode after the checker ran) takes,
per key, every `value` of a `prop` with that name under an `item` with that `oor:path`, the way the
checkers at OSWorld `b138d348` read the file: `0f84bef9` `/org.openoffice.Office.Impress/Misc/Start`
`EnablePresenterScreen` (`check_presenter_console_disable`), `2cd43775`
`/org.openoffice.Office.Common/Save/Document` `AutoSaveTimeIntervall` (`check_auto_saving_time`),
`f178a4a9` `/org.openoffice.Office.Writer/DefaultFont` `Standard` (`find_default_font`); every other
slot reads all three, so the reader runs in every slot. `k0_inputs.p010_pass`: True when every
admission cell's values equal E's, False when one differs, unread (the task held) when a cell has no
reading.

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

1. The freeze (section "Freeze procedure"), after the Phase 0 code is built and tested on dev tasks
   (done in the repair round) and a fresh audit.
2. P0.6 (K1), about 46 VM-hours (section "K1"), one `ap_delta` job at a time: 49 jobs (per image C1,
   C2, A1, A2, A5, A6 and C3 in three parts; A3 in three parts; the rung), most at N = 1, so about 45
   hours of wall clock in serial jobs plus queue waits.
3. The capture and gold sweep: 1,322 slots (882 capture, 440 gold), about 80 VM-hours (about 3.5
   minutes per slot); one CPU job at V = 20, about 4 hours plus the image check, on an empty queue.
4. The oracle (one CPU container job, `oracle_vm.py --k0`) and `k0_v4.decide`: K0.

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
on the certified disk. Its suite's executor, catalog, corpus, verdict code
(`harness/q2/action_path/acceptance.py`), trial orders (seeds 42, 43, 44, 45 as attempt 1), sessions,
infrastructure rule (section 6.1 with D30 and D33) and pass lines are unchanged here, and so is its
code: `harness/q2/` is not edited, and every campaign is admitted by harness/q2's own validator
(`harness.q2.vm.manifest.validate_manifest`) with the ledger, whose closed-world rule requires every
file under `harness/q2` to be byte-identical to the file the frozen executor addendum pins. The
deviation: (1) the guest disk is each Phase 1 cell image (E, A, ER, AR, PL; pinned in `images.json`)
instead of the certified `Ubuntu.qcow2`; (2) each campaign's `vm.qcow2` names that image's host path,
SHA-256 and size; its provenance fields (`source_url`, `revision`, `archive_sha256`, `license`),
which harness/q2's validator requires to be a revision-pinned Hugging Face URL, name the certified
disk the image is derived from, and the image itself is identified by its pin and its build record;
(3) only the checks below run; (4) the concurrency rung is N = 20 over the five images interleaved,
which harness/q2 cannot run unedited (its validator admits rungs at N = 8, 16, 24, 32 and 40 only,
and one disk per manifest). All run CPU only from the freeze commit's export, one campaign at a time.

How `harness/s2_locale/ap_delta.py` drives harness/q2 (in one Slurm job per manifest, through
`infra/slurm/host-single-node/s2v4-apdelta.sbatch`):
- a single-image check: the job runs that check's q2 campaigns on one image one after another (C3: its
  44 mutant runs and 3 reference runs), each through `python3 -m harness.q2.vm.driver` unchanged, one
  VM at a time, each into its own run directory in harness/q2's layout (manifest, `preflight.txt` with
  the batch's end line, receipt, cycles), so `acceptance.load` reads them as it read attempt 1's;
- the rung: harness/q2's ladder manifest at N = 20 with `manifest.ladder_reps(20)` = 12 repetitions
  of the seed-43 order (2,400 trials in 40 sessions, 20 per observation setting) and
  `manifest.runner_cpus(20)` = 10 runner CPUs, checked by harness/q2's validator as a shadow at
  N = 24 (every other field, the ledger and the closed world) and its N = 20 fields against
  harness/q2's own functions; `ap_delta.run_rung` is `driver.main`'s concurrent branch with one change:
  20 workers on the CPU slices of `driver.plan_cpusets_multi`, worker k on image k mod 5 (E, A, ER, AR,
  PL), running sessions k and k + 20 of `driver.acceptance_plan`, so session i runs on image i mod 5
  (8 sessions per image, four VMs per image at once), each through the unchanged `driver.run_cycle`
  with that image's `vm.qcow2`; every image is hashed before and after, and the receipt carries
  harness/q2's fields, so `acceptance.rung` reads it.

The registered campaigns are pinned before the freeze: `experiments/manifests/s2v4/k1-plan.json` (284
campaigns: 56 per image and the A3 and rung campaigns; SHA-256
`e1a4ac5b51d22a95f04905b0ebb7018ab521e2b21ca2abe2d62ced4dfd1a83cf`, pinned in `ap_delta.K1_PLAN_SHA256`),
and a `k1` job runs exactly the plan's campaigns for its check and image, or, for a check whose
campaigns' budgets exceed one job's 1,440 minutes (C3, A3), one numbered part of them in the plan's
order, the parts together running each campaign once. Each job's Slurm minutes are the sum of its
campaigns' own harness/q2 budgets plus the image check the driver makes before and after each
campaign (2 x ceil(24.5 GB / 30 GB per minute) = 2 minutes per campaign), plus 10.

| Check | Where | Pass line (D53's) | VM-h |
|---|---|---|---:|
| C1 detection | each of the 5 images | H-GA-buggy fails R01, R02, R05, R06, R07 and H-OSW-up fails R08-R11, each 5 of 5 | 0.12 each |
| C2 L0-raw failing set | each | exactly `l0_raw_prediction_v2.yaml`'s set fails, every other entry passes 5 of 5 (seed 45) | 0.25 each |
| C3 mutation score | each | 100% of scored, non-equivalent mutants killed (seed 42) | 2.82 each |
| C4 R-dev agreement | each, from A1's trials | every projected key, chord and Caps Lock stream equals its reference | (in A1) |
| A1 at N = 1 | each | L0-fixed passes 100% of G at 5 repetitions in the seed-43 and seed-44 shuffles under both observation settings (2,000 trials, 36 sessions); D33's excused-trial rule | 1.53 each |
| A5 reset and hygiene | each | 20 of 20 pristine reset-sentinel checks; every receipt shows the image unchanged and no leaked labelled container | 0.30 each |
| A2 harness layer | each | H-OSW-fixed and H-GA pass 100% of their expressible entries and gating R cells, 5 repetitions, both settings | 1.62 each |
| A6 cross-app canary | each | L0-fixed passes 100% of `canary.yaml` in Writer, Chrome, VS Code and GNOME Terminal, 5 repetitions, screenshot setting | 0.87 each |
| A3 stress | AR only | the 30 stress entries, 60 repetitions, zero failures on L0-fixed and on each harness where expressible | 4.76 |
| V = 20 rung | the 5 images interleaved, 4 VMs each | section 9's qualification rule at N = 20 (below) | about 2 |

A6 runs all four applications, as section 7 defines it: harness/q2's validator admits A6 only with all
four, the 0.87 VM-h above is already the four-application cost, and the derived base adds Ubuntu's and
GNOME's Arabic catalogs that any of the applications could read, not only LibreOffice's files.

The rung qualifies (section 9's rule at N = 20) when: at least 20 cold boots were measured (it has 40);
the boot p95 over its boots is at most 180 s; for each image, the step p95 of its 8 sessions (one
`DesktopEnv.step`, both settings pooled, excused trials included) is at most 2 x the step p95 of that
image's own A1 at N = 1 (both shuffles pooled, excused trials included): the reference is per image,
so a slower image cannot hide behind a faster one; every counted gating trial passes; at most two of its
trials were excused for a guest-server restart (D33); its campaign counts under section 6.1 (completed,
infrastructure gates, every image unchanged, no labelled container left); every session's host
snapshots are present; and no foreign-load abort occurred (a Slurm job started that was not running at
the first snapshot, or foreign jobs held more than 8 CPUs; `acceptance.foreign_abort`, from the
snapshots alone). An aborted rung is rerun once as a new attempt and both are reported; a rung that
aborts twice, or one that ran without aborting and is rerun anyway, does not qualify; the operator
submits no Slurm job while it runs. `acceptance.rung` decides every condition but the step p95 over the
whole rung, and the step condition is read per image as stated.

Total about 46 VM-hours. **K1 passes** if every check passes on every image named and the rung
qualifies. Not rerun, and why: A4 (volume) and A7 (observation service) carry over from D53. The
derived images differ from the certified disk in (i) LibreOffice's Arabic language-pack files, the
four `ucf` registry copies and the selector (and PL's toolbar definitions), (ii) Ubuntu's base and
GNOME Arabic message catalogs, GNOME help files and `/var/lib/locales/supported.d/ar` from the two
Ubuntu packs, and (iii) ext4 metadata (bitmaps, group descriptors, the superblock's free counts,
lifetime writes and checksum); every changed block is classified, and nothing outside the root
partition changes. None of these is the X server, the guard, the XRecord tap, PyAutoGUI or the guest
server, which A4 and A7 measure, and message catalogs are read only by a program running under a
matching language setting (the guest's processes run under `en_HK`). That is an argument, not a
measurement: A1-A3, A5, A6, C1-C4 and the rung test the input path on every image directly. Phase 1
is screenshot only (A7 gates only the accessibility setting), and Phase 0's accessibility calls are not
agent-facing (an undelivered one is an infrastructure loss, re-queued). There is no repair attempt
within v4: a failed check is K1, and a repair is a new image and a new registration.

## What the D53 certification covers for the cells

The runtime, the harness adapters, the lane and V at most 32 carry over (D53). Not covered by D53 and
covered here: the cell images ("another image": P0.6); the keyboard map under an Arabic interface, by
A6 in A and AR (where LibreOffice, one of A6's applications, runs with the Arabic interface; A1-A3 run
in the probe's desktop, so they cover each image's input path, not the Arabic interface) and by Phase
1's per-episode keyboard check; the guest server under localized LibreOffice (the capture slots'
restart checks); the concurrency Phase 1 uses (the V = 20 rung).

## Development smoke (dev split only; not Phase 0, not evidence for K0 or K1)

Before the freeze, the derived images are smoke-tested in the VM lane on dev tasks only (purpose
`development`, which `vm_lane.py` refuses once this id is frozen). Records:
`program/evidence/2026-10-11/s2v4-image/smoke-*/`; they decide nothing registered and change no rule
above, and the screenshots and trees stay on the host.

- Smoke 1197 (images of build 1195) and smoke 1201 (build 1199): three dev tasks (`12382c62`,
  `2b94c692`, `e528b65e`) in S, E, A, ER, AR, PL and AD plus a second E boot, and (1201) gold slots for
  the two tasks with a gold. 1197 found that the language pack's `ctl_ar.xcd` overrode the CTL pin
  (section P0.3); on the rebuilt images 1201 probed 34 of 34 slots, masked E against S 0, 1 and 1 px,
  AD against AR 0 px, E against E2 0-1 px, the Arabic chrome share 0.95-0.98 in A, AR and AD and 0
  elsewhere, the menu bar right to left exactly in ER, AR and AD, and both golds passing in all five
  admission cells.
- Smoke 1214 (repair round; the pinned images of build 1207): the dev part of the census exactly as
  `vm_lane.census_slots` renders it for the 17 dev tasks (`experiments/manifests/s2v4/dev-smoke-v3.json`;
  170 capture slots in S, E, E2, A, ER, AR, PL, AD, ER2 and PD, and 70 gold slots for the 14 dev tasks
  with a gold), one job at V = 20 (81 CPUs, 126 GB), the lane's image check first. All 240 slots ended
  probed; 7 were re-queued once after an infrastructure loss (6 guest-server restarts, found by
  the end-of-slot restart check, and 1 undelivered accessibility tree) and probed on the second attempt.
  Every slot, S included, recorded `setxkbmap` layout `us,us`, `ibus-daemon`, GNOME input sources
  `[('xkb', 'us')]`, IBus engine `xkb:us::eng`, and the guest server's and every LibreOffice process's
  `LANG=en_HK.UTF-8`, `LANGUAGE=en_HK:en` (so GTK cannot select the GNOME pack's Arabic catalogs from
  LibreOffice's initial environment); `fc-match :lang=ar` DejaVu Sans with 20 Arabic-capable families;
  `fonts-kacst` and `fonts-kacst-one` installed, and `fonts-hosny-amiri`, `fonts-sil-scheherazade`,
  `language-pack-ar` and `language-pack-gnome-ar` unknown to dpkg; the P0.10 reader's values equal in
  every slot (`EnablePresenterScreen` `true`, the other two keys absent); no setup failure, no
  postconfig failure, every postconfig save rewrote its file, and the do-nothing verdict `fail` in every
  slot of S and of the derived cells (the checker raises on PD's planted documents). The Arabic chrome share was 0.95-0.98 in A, AR and AD and 0 elsewhere; the
  menu bar ran right to left in ER, AR, AD and PD. Golds: 13 of the 14 pass in all five admission cells;
  `af23762e`'s fails in all five, E included (no passing-side control).
- The oracle's development run on smoke 1214 (`oracle_vm.py --k0`, on copies of the renders;
  `smoke-1214/oracle-dev.json`, `k0-dev.json`): tol6 = tol5 = 50 (the dev tasks' masked E-vs-E2 counts
  are 0 or 1 px); I1-doc's synthetic plant detected on 17 of 17 tasks, and PD detected on all 15 named
  tasks (and, correctly, not on `2b94c692` and `bf4e9888`, which have no plant), so the off-screen rule
  of P0.3 did not fire; I2 17 of 17; I6 17 of 17; I5 16 of 17: on the Impress task `ac9bb6cb` AD
  differs from AR by 513 px, all in the status bar's pointer-position readout (the pointer's position on
  the slide differs between the two boots); I3 and I4 at 100%; the O3 and O2 descriptor plants detected
  on 13 and 15 of 17 tasks (below the 90% descriptor bar on the dev tasks). On the dev tasks K0's
  admission gives 13 admitted and 4 runnable. These are development numbers: K0 reads Phase 0 proper
  over the 106 tasks. They show one risk to I5 that K0's fixed masks cannot remove (a status-bar
  readout that follows the pointer can differ between boots on Impress tasks), recorded here before
  the freeze.
- The `ap_delta` development run (Slurm 1217, repeated as 1218 from the same manifest;
  `experiments/manifests/s2v4/apdelta-dev-v1.json`; records `apdelta-dev/`): a harness/q2 development
  workload (L0-fixed, seed 42, three cells, one repetition) on the pinned images, once as a
  single-image campaign on E through harness/q2's driver unchanged and once as a development rung on E
  and AR at N = 2 through `ap_delta.run_rung` (session i on image i mod 2). Every trial passed (3 of 3
  and 6 of 6 in each job), both images were unchanged before and after, no labelled container was
  left, and harness/q2's `acceptance.load` reads every run directory with no counting problem;
  `acceptance.rung` reads the development rung (which cannot qualify at N = 2). The rung's step p95
  (1.90 s) is its accessibility-setting session's (screenshot-setting steps were 0.52-0.70 s in both
  campaigns); the registered rung gives every image 4 sessions in each setting, as its A1 reference has.

## Phase 1 (admitted under D80 (iv) if K0 and K1 pass)

- P1.1 Tasks: the runnable census (admitted plus runnable, at most 106). Cells: E, A, ER, AR.
- P1.2 Placebo cell PL: the en-LTR interface with the toolbar items in the fixed seeded order, n_pl = 2
  per task (one per harness).
- Episodes: n = 4 per (task, cell) in the 2x2 (2 per harness) and 2 in PL: 18 per task (1,908 at 106).
- Order: one serving session (one GPU job and its CPU VM job). Task blocks in a seeded order (PCG64 seed
  42); within a block the 18 episodes in a seeded interleave; cells assigned to VM slots at random within
  each batch of 20, slot and batch recorded.
- Step-0 check: each episode's first screenshot (after S1a's setup, warm-up and 60 s settle, as the
  Phase 0 capture slot's first screenshot) against the first screenshot of the Phase 0 render of its
  (task, cell) from the same lane and image, counted as P0.7 counts (a channel differing by more than
  20), outside the mask: the GNOME top bar (rows 0-31) and the caret mask of the Phase 0 render (the
  pixels that differ between its two screenshots 1 s apart; the episode has one screenshot, so its own
  caret cannot be masked, and a caret blinking at the reference's place differs by far fewer pixels
  than tol6's 50-pixel floor). The episode is valid if the count is at most tol6 (K0's tolerance, frozen
  with K0's oracle record); a mismatch makes it invalid.
- Step-0 and the A/A gate (I6 lets up to 5% of tasks exceed tol6 between E and E2, while K3 stops Phase
  1 above 2% step-0 failures in a cell; a task whose screen varies between boots would fail step-0 in
  every episode). A task whose Phase 0 E against E2 count exceeds tol6 is A/A-unstable: its episodes
  take no step-0 check (the image check and the keyboard check still run), they are valid, they are
  outside K3's base, and every estimand is also reported without the A/A-unstable tasks. K0 is not
  touched: this reads its I6 per task.
- Keyboard check, at every episode start: the guest's `setxkbmap -query` layout, its set of running
  input-method processes and GNOME's configured input sources (`gsettings get
  org.gnome.desktop.input-sources sources`) each equal the stock cell S's record of the same task in
  Phase 0 (the development smokes record `us,us` and `ibus-daemon` in every slot, S included); a
  difference is an infrastructure loss.
- Image check: the guest's selector SHA-256 equals the cell's at every episode start; a mismatch is an
  infrastructure loss.
- Postconfig server errors: the one rule (section "Infrastructure failures and exclusions"): a
  postconfig `/setup/*` reply with no HTTP status or a status of 500 or above is an infrastructure loss
  of the episode; a non-zero `returncode` under HTTP 200 is the agent's state and is scored. Because an
  agent's end state can make the guest server fail, losses of this kind are reported per cell and per
  session, and a sensitivity recomputes D and T with each such lost attempt entered as a failure
  (score 0) in place of its re-queued replacement (D56's concern turned around: it bounds what dropping
  them could hide); no decision rule depends on it.
- Re-queue: an infrastructure loss or a step-0 failure is re-queued at the end of its task block, at most
  twice per episode. A task enters the analysis if each of its four 2x2 cells has at least 2 valid
  episodes (and PL at least 1 for the placebo contrasts).
- Cap (D22 counting; the cap rule adopted by D80 (iv)): one job, ceil(3 + L/60 + (N x s / V + drain) x
  1.2 x 1.05 / 60) minutes with L = 113.2 s, drain = 104.6 s, V = 20, N = 18 K and s = 197.73 s, plus 6
  minutes for the overlay build and retry; 6.83 GPU-h at K = 106. At the p95 slot price the same 1,908
  episodes would need 7.70 GPU-h; D80 (iv) admits 6.83, so if slots run at that price K8 stops the job at
  the last complete task block (analysed if at least 62 admitted tasks are complete, else INCOMPLETE).

  | K | episodes | physical GPU-h (high slot) | job cap incl. overlay (min) | cap (GPU-h) |
  |---:|---:|---:|---:|---:|
  | 62 | 1,116 | 3.13 | 245 | 4.08 |
  | 89 | 1,602 | 4.46 | 346 | 5.77 |
  | 106 | 1,908 | 5.30 | 410 | 6.83 |

- The Phase 1 executor addendum. Phase 1's runner and analysis code (the agent-episode manifest and
  lane on the per-slot cell images with the GPU serving job, the step-0, keyboard and image checks, the
  postconfig rule, the re-queue at the end of the task block, the K8 cut at the last complete block,
  and the estimands, CR2 moderators and randomization test) are a separate addendum,
  `s2-arabic-cua-locale-v4-executor`, that changes no rule of this file. Before any Phase 1 episode it
  is built, dry-run on dev-split tasks only (a test-only run that decides nothing), audited by a fresh
  agent against this file, and frozen as its own ledger row; the Phase 1 job runs from the export of
  the commit that adds that row (D56's words), after K0 and K1 pass.

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
| K3 | More than 2% of a cell's episodes fail the step-0 check after re-queue (A/A-unstable tasks, whose E-E2 count exceeds tol6, are outside the base; section Phase 1) | INCOMPLETE |
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

Simulation: 42, 43, 44. Phase 0 slot order (the committed census) and Phase 1 episode order, slot
assignment and the sharp-null test: PCG64 seed 42. The oracle's descriptor plants: per task, PCG64 seeded
by (42, the task id's first 32 bits). vLLM request seed 42 (inert under greedy decoding; reruns are not
assumed identical). The P0.6 suite: attempt 1's seeds (42, 43, 44, 45).

## Compute caps (D22 counting)

| Job | Cap (GPU-h) | Arithmetic |
|---|---:|---|
| Phase 0 (P0.6, capture and gold sweep, oracle) | 0 | CPU-only lane and container jobs, no GRES; about 46 + 80 VM-hours |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a |
| Phase 1 (one job, K at most 106, n = 4 in the 2x2, n_pl = 2) | 6.73 | ceil(3 + 113.2/60 + (1,908 x 197.73/20 + 104.6) x 1.2 x 1.05 / 60) = 404 minutes |
| Registered total | 6.83 | below D20's 8 GPU-h line; admitted by D80 (iv) if K0 and K1 pass |

## Infrastructure failures and exclusions

One rule for Phase 0 and Phase 1. As `q2-stage1-rescoped-v1` section 15 and D56, plus the image check,
the keyboard check and one departure: an undelivered observation, a guest-server restart, a guest
transport failure (no reply), a setup step that fails in the guest, a postconfig server error (a
postconfig `/setup/*` reply with no HTTP status or a status of 500 or above), a VM or container failure,
an engine error or timeout, a failed keyboard check and a failed image check are infrastructure losses;
a step-0 mismatch is invalid. Both are re-queued (at most twice in Phase 1, at the end of the task block;
once in Phase 0's lane, at the end of the slot's block). A non-zero `returncode` under HTTP 200 is the
guest's state and is scored. Model behaviour is never infrastructure. The departure: S1a's section 7.2
records a postconfig server-error reply and scores the episode (D56 accepted that carve-out with a
sensitivity); here such a reply is an infrastructure loss, because in Phase 0 no agent acted before the
postconfig, so scoring it would let a transient guest-server failure change A3 or A4(i), and one rule
is kept for both phases. In Phase 1 the agent can influence the guest server, so those losses are
reported per cell and per session and a sensitivity enters each as a failure (section Phase 1).
`vm_probe.py` and `vm_gold.py` implement the rule (tested); the Phase 1 executor addendum implements it
for episodes.

## Data rights

OSWorld task configs and checkers: Apache-2.0. LibreOffice and `libreoffice-l10n-ar`: MPL-2.0. Ubuntu
language packs: translations under their upstream projects' licences (recorded in each package's
`copyright` file, written into the image). The derived and cell images are derived works under those
licences and stay on the host; they are not redistributed. The PD variant's planted documents are
copies of OSWorld file-cache files with one text run changed; only their digests are committed. The
three packages' control files and maintainer scripts committed with the build record are packaging
files under the packages' own licences (their `copyright` files). Public cotcodec artefacts are metrics,
hashes, codings and per-slot records; screenshots, accessibility trees and trajectories stay on the
host. No personal data; the VMs are offline.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the image surgery has a synthetic ext4 self-test (planner
   refusals, readback with modification times, a fixed-time rebuild that must be byte-identical,
   block-level, inode-slot, superblock and outside-partition checks that must flag an unplanned file, a
   changed untouched inode and a byte in the disk's tail) run before the build, the build classifies
   every changed block and is built twice with identical digests; the lane, probe, gold slot, census,
   PD variant, oracle adapter and `ap_delta` have unit tests and development runs on dev tasks; the
   oracle reads screenshots and accessibility trees independently of the switch code; a fresh code
   review and a fresh agent's audit check Phase 0 against this file before the freeze.
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

K1 passes on the five images: 0.85. K0 passes (at least 62 admitted, instrument checks hold): 0.65
(revised from 0.75 in the repair round, before the freeze: the pilot had 83 of 105 tasks with a passing
gold, and on the dev tasks 13 of 17 are admitted, but smoke 1214 showed an Impress status-bar readout
that can make AD differ from AR, a risk to I5's 95% bar). Descriptors valid: 0.6. Phase 1 reached: about 0.6. If it runs: D PRESENT_HARM 0.35, D SMALL 0.45,
EXCESS_OVER_PLACEBO given D PRESENT_HARM 0.5, T PRESENT_HARM 0.45, T SMALL 0.35.

## Freeze procedure

1. Build and test, on dev tasks only, the Phase 0 and K1 code. Done in the repair round (D84): the image
   build (reproducible, re-pinned), the per-slot lane with the `phase0` purpose and the census, the
   capture probe with the P0.10 reader, the gold slot and the gold rows, the PD variant, the oracle's VM
   adapter with the reader of the sweep's records into `k0_v4.decide`'s inputs, and `ap_delta.py` with
   its K1 plan, verdict and batch file (development runs: section "Development smoke").
2. A fresh code review and a fresh agent's pre-freeze audit check this file against the images, the
   code and the K0 commitment.
3. Status fill, one commit: the status paragraph's first line becomes "**Status: frozen in
   `program/preregistrations/ledger.jsonl`; see the ledger row for the freeze time and
   `git_head_at_freeze`.**" (no "DRAFT" remains), and section "Code and inputs of record" is re-filled
   from the tree (`tests/test_s2v4_registration.py` checks both: the frozen wording only with this
   file's ledger row or before it, and the table equal to the tree).
4. `uv run python scripts/preregister.py freeze s2-arabic-cua-locale-v4 program/preregistrations/s2-arabic-cua-locale-v4.md`,
   then `verify` and `check-chain`; the ledger row is committed alone. That commit is the freeze
   commit: its only parent is the status-fill commit (the row's `git_head_at_freeze`), and it changes
   only the ledger.
5. From the freeze commit's export (its `.git_sha` is the freeze commit): P0.6 (K1) through `ap_delta.py
   render` (which checks the freeze commit with git) and `submit`, one job at a time, and `ap_delta.py
   verdict`; then the capture and gold sweep through `vm_lane.py render-census --freeze-commit` and
   `submit`; then the oracle (one CPU container job, `oracle_vm.py --k0`) and `k0_v4.decide` (K0).
6. If K0 and K1 pass as registered: the Phase 1 executor addendum (section "Phase 1": built, dry-run on
   dev tasks only, audited, frozen as its own ledger row), then Phase 1 under D80 (iv) within its cap.

Steps 3 and 4 and the admission of step 5's registered manifests were rehearsed on a scratch clone in the
repair round (section "Changes in the repair round (D84): review log").

## Code and inputs of record

Phase 0 and K1 run from the freeze commit's export (D56's words). The table gives the SHA-256 of every
file they run or read at this file's commit; the status-fill commit re-fills it (`python -m
harness.s2_locale.pins_table`), and `tests/test_s2v4_registration.py` keeps it equal to the tree, so the
frozen text names the K0 code (`k0_v4.py`, `k0_inputs.py`, `oracle_vm.py` and the v3 oracle and plants it
reuses), the lane, probe, gold slot and guest helper, the census, the gold rows, the PD variant, the K1
plan and `ap_delta.py`, the image pins and the batch files.

<!-- PINS:BEGIN -->
| File | SHA-256 |
|---|---|
| `harness/s2_locale/k0_v4.py` | `d76ad39b8bb6da7e96e8afd3a43de2f8b9a90050bc509cb555f192a233712081` |
| `harness/s2_locale/k0_inputs.py` | `7f8f29c6a69ce75cab258892852580b54162faf7ca9053d6a88a4f2abf3cd15f` |
| `harness/s2_locale/oracle.py` | `c43c731daaf2319a3fb3f7a17b3104e5e1c4e73ba0c84802c2a8a3884d139798` |
| `harness/s2_locale/oracle_vm.py` | `9d323b81c1bb0a07adc09a939466fba97236afb2058682dccf61114fe5002162` |
| `harness/s2_locale/phase0.py` | `a15d8caffa16d953c5800e3e251f8d0c8d11d344937110897de0f61b6319c85e` |
| `harness/s2_locale/capture.py` | `6781c860f0ef0e8ff5a21e7f045f36ea47da19f575519be217bca52ca2614f7c` |
| `harness/s2_locale/catalog.py` | `9b95de047690570766e458fccce16ba90a8d0123b13cf3dc99d1f9e37fce57bf` |
| `harness/s2_locale/vm_lane.py` | `6758fee766e16f7423fa3f55eefbc2e7b0feaeead0acc40f617187b6784e0bdf` |
| `harness/s2_locale/vm_probe.py` | `d825f05f7815f8ef690e87fd3f539ed11496149225519a4c44f0bf44e2e11feb` |
| `harness/s2_locale/vm_gold.py` | `20ccb99a03ed311a7db15a81da19d8d6a3e4aa150636b9bb53aa957e6821a27f` |
| `harness/s2_locale/guest/s2_guest.py` | `757fdb1414ab4aeb0230df8d6799352aa720e5778935722c9afd7bf572d46fff` |
| `harness/s2_locale/golds.py` | `0d8fad9fde736ee3fcd80492b5c905d7d6a35e690f9cf66559cf42ff87c25f9e` |
| `harness/s2_locale/pd_cache.py` | `f75c520a6d8fbc7675c12ff1873ec36817eff9efa00ffa4b190fa05e81a10ddd` |
| `harness/s2_locale/ap_delta.py` | `506204e76c79c12da1793b9b1102e5cdbac3e240e28e69f4a09d8feace5176d3` |
| `harness/s2_locale/image_build.py` | `a8f937d856af59b645c10000b028611d4743651f09a23c2d8511084a4bccef66` |
| `harness/s2_locale/fetch_langpacks.py` | `9415e5e82aa92be3d343895e577aebeb67973102681f0a36c6c1536a07b55b24` |
| `harness/s2_locale/images.json` | `a95d4df25957c7301a47d6c8d719b9016a6ac4e9ca51f6377d44b8e28794d767` |
| `infra/slurm/host-single-node/s2v4-vm.sbatch` | `1f831bbbc73b792c9d27809a1ecad41526d0ad79c66ea682457d404200c1a09b` |
| `infra/slurm/host-single-node/s2v4-apdelta.sbatch` | `0423c0257d32a055d6c812cc3d8a287676d604b41b3742012550178e4d0d89cb` |
| `infra/slurm/host-single-node/s2v4-cpu.sbatch` | `47c0900815a81a764af1faf1151a9bac5a18263e1cad0e63cc8584bc6fd675e0` |
| `scripts/render_q2_action_path_manifest.py` | `0d547c7af6c440f108526a4306870091da09e7b99419334d76a4bdd116b90845` |
| `experiments/manifests/s2v4/phase0-census.json` | `02bfc97bf8c14f48f2bfd57c26a34b5fac0b57d9aa18981b474a286d38589cf0` |
| `experiments/manifests/s2v4/golds-v4.jsonl` | `4ac326bd10dbda9ef1e266ffe247cd25f5a2e602e582404a798fadf4908dc71a` |
| `experiments/manifests/s2v4/k1-plan.json` | `e1a4ac5b51d22a95f04905b0ebb7018ab521e2b21ca2abe2d62ced4dfd1a83cf` |
| `program/evidence/2026-10-11/s2v4-image/pd-cache/pd-cache-manifest.json` | `7e9979b4124ccfd6d57535829ac376e2cab57315409ede5ddef2833087223a70` |
| `program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/pool-v3.json` | `f730e464366c03f4d6b12769be96d477609689d9f8ef3db2d7e1ddd2d3237ada` |
| `program/evidence/q2-mutation/splits.json` | `2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9` |
| `program/evidence/q2-mutation/harness/file-cache-receipts.tsv` | `9a3e06a48afe95c2286d0fa26d56edf947e1a5e0f121d414d565b58d30abe5fb` |
<!-- PINS:END -->

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

Added in the repair round (D84):

91. Reproducible images: every `debugfs -w` session at the certified disk's own last write time, built
    twice in one job with identical digests, and re-pinned.
92. The census rendered and pinned before the freeze, run only by the `phase0` purpose from the freeze
    commit's export (the S1a and K2 lanes' gate), with one resume rule.
93. The oracle's VM adapter: accessibility offset 0, K0's masks in O5, document plants judged against the
    unplanted render of the same image.
94. PD as a pinned planted-document file-cache variant on the ER image, with a rule for an off-screen
    plant fixed before the freeze.
95. One infrastructure rule for postconfig server errors in both phases (a loss, re-queued), with Phase
    1's sensitivity entering each lost attempt as a failure (amends 83's inheritance of S1a's rule).
96. The locale and the keyboard held at the guest's stock values, as v4's records show them, and checked
    against the stock cell S at every Phase 1 episode start.
97. Step-0's mask (the top bar and the Phase 0 render's caret mask) and the A/A-unstable tasks taken out
    of step-0 and of K3's base.
98. K1: section 9's full qualification rule at N = 20 with a per-image step reference, harness/q2 driven
    unedited by `ap_delta.py`, the K1 campaigns pinned, and A6 with all four applications.
99. Phase 1's runner and analysis code as an executor addendum, dry-run on dev tasks, audited and frozen as
    its own ledger row before any Phase 1 episode.

## Changes in the repair round (D84): review log

A fresh code review and a fresh pre-freeze audit of `47c169f9` found the package not ready to freeze
(D84). Every item, and what this round did. "Fixed" items are in the code and text above; the
development runs are under `program/evidence/2026-10-11/s2v4-image/`.

Code review, blocking:

| Item | Disposition |
|---|---|
| R1. The image build was not bit-reproducible (each `debugfs -w` stamped the wall clock into the superblock), and nothing said so | Fixed. Every write session runs at the certified disk's `s_wtime` (`E2FSPROGS_FAKE_TIME`); one CPU job (Slurm 1207) built twice and got identical digests for every image, which are the new pins (`images.json`, section "Images built"); the same job found that its derived base differs from build 1199's only in superblock copies (`reproducibility.json`); build 1195's images were deleted after that, build 1199's are kept, superseded |
| R2. Two held-fixed facts contradicted v4's records: `ibus-daemon` runs in every slot, S included, and the guest's locale is `en_HK.UTF-8` / `en_HK:en`, not `en_US.UTF-8`; as written, Phase 1's keyboard check would fail every episode | Fixed. The keyboard check is equality with the stock cell S's record (layout, input-method processes, GNOME input sources; P0.5, Phase 1); the locale is the guest's stock values in P0.2, P0.5, the claim scope and `image_build.py`'s docstrings; the evidence README's two sentences are corrected; the probe records input sources, IBus's engine and LibreOffice's locale variables |
| R3. The download's scope went beyond D80 (iv)'s words and the packages' unmet dependencies were undisclosed | Fixed. P0.2 attributes `libreoffice-l10n-ar` to D80 (iv) and the two Ubuntu packs to D1 under D84's reading of D80 (iv) with D76 (a), lists every unmet Depends and Recommends, restates v3.1's font facts (re-read in the VM by the probe's end facts) and describes the GNOME pack as possibly inert |

Code review, not blocking:

| Item | Disposition |
|---|---|
| The fetch's chain of trust is sound | Confirmed; hardened anyway (below) |
| The image changes only the registered content | Confirmed; the checks are now finer (below) |
| P0.2 cited the superseded build 1195 | Fixed: P0.2 cites the pinned build |
| `LAYER_FILES` is hand-typed and unchecked | Fixed: `check_layer_files` at build time (the system layer's `*.xcd` files must be `LAYER_FILES` plus `main`), tested |
| The block check is coarser than "every block explained" suggests | Fixed: inode-table blocks are compared slot by slot (only touched inodes may change), the superblock fields `dumpe2fs -h` prints are whitelisted (free counts, lifetime writes, checksum, write time), and the raw disks must be identical outside the root partition; superblock and group-descriptor copies and the directories that gained entries are still accepted as classes (disclosed in P0.2) |
| `verify_plan` did not read back modification times; the script digest does not cover staged contents | Fixed: every written path's mtime is read back; reproducibility is judged on the image and manifest digests (`reproducibility.json`) |
| Fetch hardening (signer pin, Suite and Codename, gpgv status tests, a tampered `Packages.xz`) | Fixed: all four, unit-tested; the stored files re-checked offline (`fetch/verify.json`) |
| `ucf_pairs` ignores other postinst actions; commit the maintainer scripts | Fixed: the build copies every control file and maintainer script, committed with the build record (`maintainer-scripts/`) |
| P0.5 called `ctl_ar.xcd`'s default part of the text treatment | Fixed: it sets only `CTLFont`, which the pin overrides in every derived cell; a constant of the derived base, guarded by I2 |
| `verify_images` hashes about 171 GB per lane job | Fixed: `vm_lane.check_slurm` budgets the image check (30 GB per minute) in the job's minutes, and `ap_delta` budgets the driver's two image hashes per campaign |

Pre-freeze audit, blocking:

| Item | Disposition |
|---|---|
| A1. Phase 0 could not run from the freeze commit: five components missing, the lane refusing every job once frozen | Fixed. (a) `oracle_vm.py` (VM renders and OSWorld's XML; I1-doc, I2, I5, I6, tol6; masks in every comparison) run on the development smokes; (b) the PD variant (`pd_cache.py`, pinned) dev-tested on all 17 dev tasks in the VM, the 15 named ones included, with the off-screen rule fixed in P0.3; (c) the P0.10 reader in `vm_probe`; (d) the census renderer and the `phase0` purpose, admitted only with the ledger row and from the freeze commit's export, with V = 20 sizing and one resume rule; (e) `ap_delta.py` with its K1 plan, batch file and verdict, dev-run on the host (Slurm 1217 and 1218: a single-image campaign and a two-image development rung, read by harness/q2's own `acceptance` code; section "Development smoke"). The scratch freeze rehearsal rendered and validated the registered census manifest (1,322 slots), a resumed census, and K1 manifests (C1, C3, the rung) from the freeze export, and refused development manifests |
| A2. Phase 1 had no executor, was not in the freeze procedure, and its step-0 mask was ambiguous | Fixed. The step-0 mask (top bar and the Phase 0 render's caret mask), the keyboard and image checks and the postconfig rule are defined; the Phase 1 executor addendum (code, dev-only dry run, fresh audit, its own ledger row before any episode) is step 6 of the freeze procedure |
| A3. K1's V = 20 rung was under-specified, and harness/q2 cannot run it unedited | Fixed. Section 9's full rule at N = 20 (r = 12, 2,400 trials in 40 sessions, runner CPUs 10, boot and step p95, at most two excused trials, snapshots, foreign abort with one rerun), the step reference per image (its own A1), and how `ap_delta` drives the five images; harness/q2 stays byte-identical (its closed-world ledger check); A6 runs all four applications (harness/q2's validator; already the budgeted cost); the keyboard claim is restricted to A6 in A and AR |
| A4. Held-fixed facts contradicted the records | As R2 |
| A5. The infrastructure rule contradicted S1a's carve-out and the probe | Fixed. One rule: a postconfig server error (no HTTP status, or 500 or above) is an infrastructure loss, stated in P0.7, Phase 1 and the infrastructure section, implemented in `vm_probe.py` and `vm_gold.py` with tests; Phase 1 reports those losses and a sensitivity enters each as a failure |
| A6. The freeze would freeze draft wording; P0.2 cited build 1195 | Fixed: the status-fill step (freeze procedure step 3), the test reads the status against the ledger, and P0.2 cites the pinned build |
| A7. The images were not bit-reproducible | As R1 |
| A8. The approval scope and dependencies were undisclosed | As R3 |

Pre-freeze audit, not blocking:

| Item | Disposition |
|---|---|
| K0 committed before any Phase 0 result; `k0_v4.py` implements it | Confirmed; the K0 section is byte-identical (`ed38b953...`, tested) and `k0_v4.py` is unchanged |
| Wave 2 defect 4: state the K8 consequence at the p95 slot price | Fixed: Phase 1's cap paragraph states it (7.70 GPU-h needed, 6.83 admitted, K8 at the last complete block) |
| K1 takes about 40 hours of serial jobs and image hashing | Budgeted: each `ap_delta` job's minutes include the image checks; one job at a time on an empty queue |
| I6 lets 5% of tasks fail A/A while K3 allows 2% step-0 failures | Fixed without touching K0: A/A-unstable tasks take no step-0 check and are outside K3's base, and every estimand is also reported without them |
| PD rested on container renders | Fixed: dev-tested in the VM on all named tasks, with a rule for an off-screen plant fixed before the freeze |
| Pin `k0_inputs.py` and `k0_v4.py`; `k0_inputs` drops tasks with no records | Fixed: both are in section "Code and inputs of record"; `k0_inputs.admission` lists every pool task (unobserved tasks are excluded, not dropped) |
| "The freeze commit or its successor" is vague | Fixed: D56's words in section "Identity", enforced by the lane and `ap_delta` |
| The carry-over argument for A4 and A7 was inaccurate; a docstring was stale | Fixed: section "K1" lists every class of change (the Ubuntu and GNOME catalogs, help files and `supported.d/ar`, ext4 metadata) and calls the carry-over an argument; `image_build.py`'s docstring gives the dependency block as the reason the selector is read last |
| The review's non-blocking items | As above |
| Program records (decisions, state, handoff) | The orchestrator's; not edited in this round |

Closing the round: `main` was merged in with every ledger row kept (rows 19 and 20 are other
experiments'; this id still has none); the `ap_delta` development jobs' records were committed
(`apdelta-dev/`, section "Development smoke"); the evidence README's statements about the superseded
builds were corrected; and the scratch freeze rehearsal was repeated at the merged head
(`freeze-rehearsal/rehearsal.json`). Found in development and not fixed in this round, recorded for
the next review: the Impress status bar's pointer-position readout made AD differ from AR on
`ac9bb6cb` (section "Development smoke"); parking the pointer before the capture would be a change to
P0.7's capture, not to K0, and would need a development smoke on the host first.

