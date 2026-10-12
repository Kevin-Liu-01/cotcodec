# S2 v4: Arabic interface text versus mirrored layout on the certified OSWorld stack, with the shipped Arabic language packs, a fixed Phase 0 admission rule and a registered delta certification of the action path (s2-arabic-cua-locale-v4)

**Status: DRAFT, not frozen; no ledger row.** Written on 2026-10-11 by the single owner of the S2
v4 run (decision D80 (iv)) on branch `stage0/s2-v4`, and repaired in three rounds, under D84, D87
and D90 (sections "Changes in the repair round (D84): review log", "Changes in the third round
(D87): review log" and "Changes in round 4 (D90): review log" list every review and audit item and
its disposition). It is a new experiment id:
`s2-arabic-cua-locale-v3` and `v3.1` (the package that
scored 60 and 65, D74 and D76) are left unedited, and this file carries v3.1's design with the
changes listed below. D80 (iv) approved, on Kevin's delegation: fetching the official LibreOffice
Arabic language packs that match the guest's LibreOffice 7.3.7; reviewed image-surgery code; a
registered deviation of `q2-action-path-v2` for the P0.6 certification on the derived
configuration; a K0 admission rule committed in this registration before any Phase 0 result is
read; and Phase 1 (6.83 GPU-h) admitted under D24 if Phase 0 passes as registered. The owner also
fetched Ubuntu's `language-pack-ar-base` and `language-pack-gnome-ar-base`, which are not
LibreOffice packs: D84 records them as public research downloads under D1, their use read under D80
(iv) together with D76 (a) ("the applications' real Arabic language packs"); P0.2 states that
reading and the packages' unmet dependencies. Phase 0 is CPU only. Evidence:
`program/evidence/2026-10-11/s2v4-image/` (the fetch provenance and its offline re-check, the image
builds, the PD file-cache variant, the development smokes and the oracle's development runs).

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
| The pointer left where the boot put it | One warp of the pointer to the screen point (995, 540) after the 60 s settle, then a fixed 4 s wait before the first screenshot, in every Phase 0 capture slot and at every Phase 1 episode start (P0.7, Phase 1) | Third round (D87): in smoke 1214 Impress's status-bar pointer readout changed from boot to boot in the mirrored cells. Round 4 (D90): the third round's warp before the settle still left it varying in 2 of 70 Impress boots (smoke 1240) |
| A resumed Phase 0 job's records counted in the order the run directories were named | Counted in job order, by the Slurm job id the batch file writes before the lane starts (a lane receipt is a cross-check only); a first-attempt loss whose re-queue was cut is rerun by the resume; the resume manifest is computed from the interrupted job's records and checked against them; at most one resume; TERM stops the lane like USR1; a census job with zero records uses the one resume (P0.7) | Third round (D87). Round 4 (D90): the third round read the job order from the lane receipt alone, so a job ended by TERM or by a failed image check could be neither read nor resumed |

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

### P0.2 Inputs and the derived image (done before the freeze)

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
for the guest server, S included) is held fixed. That matters for the checkers: R04 (D89) found
OSWorld's office checkers not invariant to the system locale (under `ar_EG` three `compare_table`
golds and the `compare_pptx_files` gold of `5c1a6c3d` flip), so an Arabic system locale would change
verdicts by itself (P0.5). LibreOffice's interface language is set by the selector, not by the
locale. Under `LANGUAGE=en_HK:en` GTK's gettext may never select the GNOME pack's
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
container forced `en_US.UTF-8`, which the VM does not use; R04, D89, found that a `de_DE`, `ar_EG` or
`tr_TR` system locale flips OSWorld checker verdicts, three `compare_table` golds in each and, under
`ar_EG`, also `5c1a6c3d`'s `compare_pptx_files` gold, so v4 switches LibreOffice's interface language
and never the system locale); the document default language; the
SheetPrefix, CTLFont and English-function-name pins; autocorrect and spelling languages; the
pointer's position at the capture and at each episode start (the warp of P0.7); the stock
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
guard's keyboard warm-up; the 60 s settle; the pointer warp and its fixed 4 s wait (below); two
screenshots 1 s apart; the accessibility tree; window titles, `setxkbmap -query`, the input-method
processes, GNOME's input sources, IBus's engine and each
LibreOffice process's initial locale variables; the 20 s settle; the SHA-256 and mtime of every file
the checker reads; the pinned `DesktopEnv.evaluate()` with `DONE` (the task's own postconfig and its
checker, on the do-nothing state); the guest-server restart check; the files' SHA-256 and mtime again;
P0.10's reader; a last screenshot; the end facts (fonts; `dpkg-query` status of the packs' unmet
dependencies and recommendations). Screenshots and trees stay on the host; records are committed.

Pointer warp (third round, D87; after the settle since round 4, D90). After the 60 s settle, the
probe moves the pointer once to the screen point (995, 540) (`vm_probe.POINTER_TARGET`) and then waits
a fixed 4 s (`vm_probe.POINTER_WAIT_S`) before the first screenshot. The warp is the guest helper's
`pointer` mode (`guest/s2_guest.py`, called by `vm_probe.warp_pointer`): one absolute XTest motion to
that point (python-xlib's `xtest.fake_input(MotionNotify, x=995, y=540)` and `XSync`, the call the
certified guard makes to park the pointer, through the input path D53 certified), so the pointer
jumps there with no intermediate position; the mode then reads the position back (the record
keeps it before and after). Why: until then the pointer rests where the boot left it ((1728, 972),
as the warp reads it in smoke 1240; every one of smoke 1214's 177 capture renders shows the cursor
there), and LibreOffice's last motion event is whatever the window received while it was being
laid out. Impress shows that event's position in its status bar, and in the mirrored cells it
changed from boot to boot (smoke 1214). The third round warped before the settle; the warp then landed within about a
second of the guest server's reply to the task's open step, while the window could still be laid
out, and in 2 of smoke 1240's 70 Impress boots the field took another value (section "Development
smoke"). After the 60 s settle the window is expected to have its final layout, so that the warp's
motion event is handled under that layout in every boot (round 4's development smoke tests this). The
4 s wait was chosen before round 4's development smoke:
it is longer than LibreOffice's help-tip delays (VCL shows a quick-help tip 0.5 s and a balloon tip
1.5 s after the pointer comes to rest), so whatever the pointer's arrival shows has shown, and
LibreOffice has handled the motion, before the screenshots. The point was chosen on smoke 1214's dev
renders: it lies inside the document region of Calc, Writer and Impress in every cell (Impress's
slide editing window spans about x 275-1510 left to right and x 480-1720 mirrored, y 250-1045; Calc's
grid x 82-1820, y 281-997; Writer's document x 70-1849, y 246-1034); it lies on the LibreOffice
window's mirror axis (the window spans x 70-1919, and the mirrored layout puts each part of the window
at the mirror image, about x = 994.5, of its left-to-right place: Impress's slide editing window at
x 480-1720 for 275-1510), so the pointer rests over the same part of the window in both directions;
and it is away from the boot's resting point, so the warp always moves the pointer. The
guest server draws the cursor into every screenshot at the pointer, so every render shows the cursor
at that point. Gold slots (P0.9) take no screenshot that K0 reads and do not warp.

Infrastructure, the one rule of section "Infrastructure failures and exclusions": a failed boot, image
check or setup step in the guest, a failed pointer warp (the guest cannot make it, or the pointer reads
back elsewhere), a guest transport failure, an undelivered observation, a guest-server
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
and the registered `phase0` job runs exactly these slots: one CPU job at V = 20 into the registered run
root (81 CPUs requested, which Slurm rounds to 82 as it did for smoke 1214; 126 GB; ceil(6 + 1.5 x 1,322
x 3.5 / 20 + 10) = 364 minutes requested, from a 3.5-minute slot estimate with a 1.5 margin). Smoke
1214's capture slots took 4.3 minutes per attempt at the median (247 attempts, re-queues included, in
53 minutes at V = 20), so the census's about 1,360 attempts need about 4.9 hours and about 95 VM-hours
(round 4's 4 s wait after the warp adds under 2% to a capture attempt);
the request covers that with about 20% to spare, and an overrun is the resume rule's case.

Resume (third round, D87, and round 4, D90; `k0_inputs`, `vm_lane`). A slot's records in one job are
final when an attempt ended `probed` or the slot was lost to infrastructure on its second attempt
(lost twice: unobserved). A first-attempt loss whose re-queue the job did not finish (cut at the stop
signal, never dispatched, or without a record) is not final, nor is a `cap_truncated` record: such a
slot has not had its registered second attempt, so the resumed job runs it afresh (its attempts there
count, with the lane's one re-queue; the interrupted job's loss is reported, not counted). A `phase0`
job that ends before every slot has a final record is resumed once: `vm_lane.py render-census
--freeze-commit ... --resume-from-records RUN_DIR/probes.jsonl` renders the census from the first block
(in census order) holding a slot without a final record (`resume_from_block`), naming the interrupted
job (`resumes`: its Slurm job id, its run directory under the registered run root and the SHA-256 of
its `probes.jsonl`); the lane recomputes all of this from that run directory and admits the resume
manifest only if it is exactly that rendering; the interrupted job must be the census job itself (a
resumed job is never resumed), and `submit` refuses a second census job and a second resume.

Which job a run directory is, and in which order jobs are taken (round 4, D90): by the Slurm job id
the batch file (`s2v4-vm.sbatch`) writes before the lane starts, never by anything the lane writes. On
the host the run directory is named by it (`RUN_ROOT/SLURM_JOB_ID`) and `preflight.txt`'s `job_id`
must be the same id; inside the oracle's container, where the directories are mounted at `/ro/run1`
and `/ro/run2`, `preflight.txt` names the job (`k0_inputs.job_id`). Jobs are taken in ascending job id
(as Slurm assigns them), never in the order the directories are named. A lane receipt is a
cross-check only: when a job wrote one, it must name the same job id, and the receipts' `t_start`
must give the same order. So a job that a TERM ended before its receipt was written (`scancel`, a
node fault, a time-limit kill after USR1's 120 s), or one that failed its image check, is read and
resumed like any other. TERM also reaches the lane as a stop, like USR1 (`vm_lane.stop_on_signals`):
nothing new is dispatched, the slots in flight are cut, every slot never dispatched is recorded, and
the receipt (which carries `t_start`, as the image-check receipt now does) is written, when the job
has the time. A census job with zero records (its image check failed, or it was stopped before any
slot ended; it may have no `probes.jsonl`) is resumed by the same rule: its first block holds a slot
without a final record, so the one resume runs the whole census (and is never resumed itself). A
run directory without `preflight.txt` (the batch file stopped before it could start the lane) holds no
record and is not a job: `submit` does not count it, and the census job is submitted again. Which
record counts: per slot the attempts of the first job (in job order) with a final record, and of
those the last (`k0_inputs.load_runs`, `counted`; `oracle_vm.py` reads its renders the same way).

The oracle's registered route: one CPU container job through `infra/slurm/host-single-node/s2v4-cpu.sbatch`
(run mode, no GRES, `--network=none`, read-only root, no capabilities) in the checker-mutation metric
image `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (the lane's episode
image; `oracle_vm.ORACLE_IMAGE_ID`), the freeze commit's export at `/src`, the census job's run
directory (and its resume's, if any) mounted read-only at `/ro/run1` (`/ro/run2`), and the argv
`oracle_vm.registered_argv`: `/opt/venv-lock/bin/python -m harness.s2_locale.oracle_vm --runs /ro/run1
[/ro/run2] --pool program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/pool-v3.json
--out /out/oracle.json --k0 /out/k0.json --workers 16` (the result does not depend on the number of
workers, nor on which directory is mounted first: the job order comes from `preflight.txt`, above).
Its output records the interpreter and the numpy, scipy and Pillow versions it ran with; the
development run of this route is in section "Development smoke".

Oracle (`harness/s2_locale/oracle_vm.py`: v3's `oracle.py` and `phase0.py` plants on the VM's renders and
OSWorld's accessibility XML; every parameter decided on the 17 dev tasks by a fixed formula; it runs as
the registered container job above, after the sweep):
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
best), among them the three C1 tasks. Why A4(ii) is needed on this stack: R04 (D89) found OSWorld's
office checkers not invariant to the LibreOffice build (25.8 and later) or to the system locale
(`de_DE`, `ar_EG` and `tr_TR` flip three `compare_table` golds, and `ar_EG` also `5c1a6c3d`'s
`compare_pptx_files` gold). R04 did not vary LibreOffice's interface language, v4's treatment; a
cell that changes what a checker reads could flip a gold the same way, and A4(ii) checks in every
admission cell that the gold still passes.

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
2. P0.6 (K1), about 44.3 VM-hours (section "K1"), one `ap_delta` job at a time: 49 jobs (per image C1,
   C2, A1, A2, A5, A6 and C3 in three parts; A3 in three parts; the rung), all but the rung at N = 1,
   so about 42 hours of VM time in serial jobs, plus the driver's two image checks per campaign
   (budgeted at 2 minutes per campaign, at most about 9.5 hours over the 284 campaigns) and queue
   waits: about 42-52 hours of wall clock.
3. The capture and gold sweep: 1,322 slots (882 capture, 440 gold), about 1,360 attempts with
   re-queues, about 95 VM-hours (4.3 minutes per attempt, smoke 1214); one CPU job at V = 20, about 4.9
   hours plus the image check, on an empty queue.
4. The oracle (the registered container job, `oracle_vm.py --k0`) and `k0_v4.decide`: K0.

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
  with that image's `vm.qcow2`. Before any session it makes `driver.main`'s pre-run checks with
  harness/q2's own functions and messages (Docker's server facts, the VM image's ID and digest
  reference agreeing, the runner image present, per image the regular read-only file with the pinned
  size and digest and its `qemu-img info`, and the dangling Docker volumes before and after; third
  round, D87: the repair round's `run_rung` had dropped them, and development jobs 1217 and 1218 ran
  without them); every image is hashed before and after, and the receipt carries harness/q2's fields,
  so `acceptance.rung` reads it.

The registered campaigns are pinned before the freeze: `experiments/manifests/s2v4/k1-plan.json` (284
campaigns: 56 per image and the A3 and rung campaigns; SHA-256
`e1a4ac5b51d22a95f04905b0ebb7018ab521e2b21ca2abe2d62ced4dfd1a83cf`, pinned in `ap_delta.K1_PLAN_SHA256`),
and a `k1` job runs exactly the plan's campaigns for its check and image, or, for a check whose
campaigns' budgets exceed one job's 1,440 minutes (C3, A3), one numbered part of them in the plan's
order, the parts together running each campaign once; every campaign of a `k1` job runs on the same
image (the first campaign's, which names the plan's entries). Each job's Slurm minutes are the sum of its
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

Total about 44.3 VM-hours (7.51 per image on each of the five images, A3's 4.76 and the rung's about
2). **K1 passes** if every check passes on every image named and the rung
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
- The oracle's development run on smoke 1214 (`oracle_vm.py --k0` on the Mac, on copies of the
  renders; `smoke-1214/oracle-dev.json`, `k0-dev.json`), before the pointer warp existed. tol6 = tol5 =
  50 (the dev tasks' masked E-vs-E2 counts are 0 or 1 px). Every boot-to-boot pair the run has (masked
  counts against tol6 = 50):
  - E against E2 (the pair I6 reads), 17 tasks: 0 or 1 px on every task.
  - ER against ER2 (dev tasks only), 17 tasks: 0-2 px on 13 tasks; 13 px on the Writer task
    `936321ce`; 293 px on `2b94c692`, 148 px on `ac9bb6cb` and 139 px on `e4ef0baf`, three of the seven
    Impress dev tasks, all above tol6.
  - AD against AR (the pair I5 reads), 17 tasks: 0 px on 16; 513 px on the Impress task `ac9bb6cb`.
  - Every differing pixel of the four pairs above tol6 lies in Impress's status bar (y 1064-1076, x
    about 820-933 in the mirrored layout), in its pointer-position field. On `ac9bb6cb` it read
    16.46 / 0.90 in ER and 15.62 / 0.90 in ER2, 15.62 / 0.90 in AD and 16.48 / 3.46 in AR. On
    `2b94c692` the counted ER attempt read 18.32 / 1.50 and ER2 20.23 / 2.92, while the uncounted
    first ER attempt differed from ER2 by 0 px: the field takes a fresh value at each boot, not one
    value per task. In the left-to-right cells it read the same value in every boot (-0.39 / -1.40 on
    `ac9bb6cb`). The pointer itself rested at the same point in every capture render (the cursor drawn
    at (1728, 972)); the field shows the position of the last motion event LibreOffice received, and
    with the pointer at rest that event can only have come while the window appeared and was laid out
    under it, at a moment that varies from boot to boot (the explanation the warp tests).

  So 4 of the 7 Impress dev tasks varied between boots in a mirrored cell, and I5 was 16 of 17
  (0.941): on the dev tasks I5 fails its 95% bar. I5 allows at most 5 failures among the 106 pool
  tasks, 40 of which are Impress tasks; the pre-freeze audit put P(I5 holds) at about 0.48 at the
  AD-AR rate (1 in 7 Impress tasks) and about 0.01 at the pooled mirrored boot-pair rate (4 in 14), and
  a failed I5 is an infrastructure exit after about 126 VM-hours. In Phase 1 the step-0 check compares
  each ER and AR episode with one Phase 0 boot, and the A/A-unstable exemption read only E against E2,
  so these tasks would have failed step-0 at random. The third round addressed the cause in the
  capture (a pointer warp before the 60 s settle, in Phase 0 and Phase 1) and masked the status bar in
  step-0 (Phase 1); K0 is unchanged. Smoke 1240 below measured that warp on the dev tasks: these four
  differences were gone, but the field still took another value in 2 of 70 Impress boots, so round 4
  (D90) moved the warp after the settle (P0.7).

  The other development numbers of this run, stated plainly: I1-doc's synthetic plant was detected on
  17 of 17 tasks and PD on all 15 named tasks (correctly not on `2b94c692` and `bf4e9888`, which have no
  plant), so the off-screen rule of P0.3 did not fire; I2 17 of 17; I6 17 of 17; I3 and I4 100%. The O3
  and O2 descriptor plants were detected on 13 and 15 of 17 tasks (76% and 88%), below the 90% bar: if
  that held in the census, every O2, O3 and O8 quantity would be labelled instrument-limited, and O8's
  moderator and P5's O8 route would be dropped (unresolved). K0's admission on the dev tasks: 13
  admitted and 4 runnable; `af23762e`'s gold fails in all five admission cells, E included, so it has
  no passing-side control (runnable). What I1-doc's synthetic plant tests in practice: judged against
  the unplanted render of the same image, it fails only when a task's ER render has no document region
  or O5's alignment fails, and with its 100% bar a single such task fails K0. One PD slot, or one ER
  slot of a named dev task, lost twice (unobserved) also fails I1-doc. These are development numbers:
  K0 reads Phase 0 proper over the 106 tasks.
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
  These jobs ran `run_rung` before the third round restored `driver.main`'s pre-run checks (section
  "K1"). Both were submitted on an empty queue between steps of R04's CPU campaign (1217 about 2 s
  after R04's job 1216 ended; 1218 right after 1217 ended, while R04's driver was waiting for an empty
  queue to submit its next step), so neither overlapped an R04 job, but R04's next step waited for
  1218 (D87; R04's report records any effect on its timing).
- Smoke 1240 (third round; the pointer warp of P0.7): smoke 1214's 240 slots again
  (`experiments/manifests/s2v4/dev-smoke-v4.json`: the same slots under a new name), from the export of
  `688b2880`, one job at V = 20 (81 CPUs requested, 82 allocated), the lane's image check first,
  submitted on an empty queue once R04's campaign had no step pending. All 240 slots ended probed; 4
  were re-queued once after a guest-server restart found by the end-of-slot check and probed on the
  second attempt. The warp ran in all 174 capture attempts: the pointer read (1728, 972) before it and
  (995, 540) after it, in about 0.23 s in the guest. Held fixed in every slot, S included, as in smoke
  1214: `setxkbmap` `us,us`, `ibus-daemon`, input sources `[('xkb', 'us')]`, IBus engine `xkb:us::eng`,
  `LANG=en_HK.UTF-8` and `LANGUAGE=en_HK:en` for the guest server and every LibreOffice process, DejaVu
  Sans with 20 Arabic-capable families, the P0.10 reader's same three values. Every postconfig save
  rewrote its file; the do-nothing verdict was `fail` in every slot but PD's (`error` on the 15 planted
  documents, `fail` on the two tasks without a plant); golds: 13 of the 14 pass in all five admission
  cells, `af23762e`'s fails in all five, E included. Capture slots took 4.0 minutes at the median.
- The oracle's registered route on smoke 1240 (Slurm 1241, `oracle-route-1241/`): the container job of
  P0.7 exactly (the metric image, `registered_argv(1)`, the export of `688b2880` at `/src`, the run
  directory read-only at `/ro/run1`; 34 s), in Python 3.12.13 with numpy 1.26.4, scipy 1.17.1 and
  Pillow 11.0.0. A run of the same code on the Mac, on a copy of the records and renders (Python
  3.13.14, numpy 2.5.2, scipy 1.18.0, Pillow 12.3.0), gave the same metrics, tolerances, instrument
  checks and K0 output; one reported per-task mean displacement differed in its last digit
  (`mac-crosscheck.json`). tol6 = tol5 = 50; tol2 0.0202 and tol3 18 (smoke 1214's renders gave 0.1 and
  20: these are calibrated on the dev renders, which now show the cursor at (995, 540)). Boot-to-boot
  pairs after the warp (masked, against tol6 = 50):
  - E against E2: 0 or 1 px on all 17 tasks (I6 17 of 17).
  - AD against AR: 0 px on all 17 tasks (I5 17 of 17; smoke 1214's 513 px on `ac9bb6cb` is gone).
  - ER against ER2: 0 px on 16 tasks, `2b94c692`, `ac9bb6cb` and `e4ef0baf` among them; 142 px on the
    Impress task `af23762e`.
  - E against S: 0 or 1 px on 16 tasks; 148 px on `ac9bb6cb` (I2 16 of 17, below its 95% bar).

  The two pairs above tol6 differ again only in Impress's pointer-position field, now in both
  directions. On `ac9bb6cb`, E, E2 and PL read 15.14 / 5.44 and S read 15.14 / 4.91; on `af23762e`, ER2
  and PD read 6.95 / 10.44 and ER read 7.57 / 10.44 (the Arabic cells read 15.14 / 5.46 and 6.92 /
  10.41 in their own layout); in every other Impress task each direction's cells read one value. So the
  warp gave the field one value in most boots, but in 2 of the 70 Impress capture boots it took
  another: in those boots the window's layout still changed after the warp (the field keeps the
  position of the warp's motion event, computed under the layout of that moment), which a warp before
  the 60 s settle cannot exclude. The warp before the settle also moved the variation into a
  left-to-right pair: E against S, at most 1 px on the Impress dev tasks in smoke 1214 (at most 19 px on
  any dev task), was 148 px on `ac9bb6cb`. In smoke 1240's probe records the warp's guest time lies
  within about 1.1 s of the guest server's reply to the task's open step in all 170 capture records
  (median 0.06 s; the reading mixes the guest's clock with the episode container's), so the warp
  landed while the window was still being laid out. The other checks: I1-doc held (synthetic plant 17
  of 17, PD on all 15 named tasks); I3 and I4 100%; descriptor plants O3 17 of 17 and O2 15 of 17
  (O2 still below 90%, so the descriptors would be invalid); K0's admission on the dev tasks 13
  admitted and 4 runnable, as in 1214. On smoke 1240's dev tasks K0's instrument checks failed on I2.
  If each Impress boot takes another value
  with probability about 2 in 70, each of I2, I5 and I6 loses an Impress task with probability about
  0.056, and with 40 Impress tasks in the pool (at most 5 failures allowed among 106) each holds with
  probability about 0.98 (about 0.93 for all three); at 0.05 per boot each holds with about 0.81 (0.53
  for all three), and at 0.1 per boot with about 0.2. Two boots in 70 bound that rate only loosely, so
  after the third round the risk to K0 was smaller than before the warp but not removed. The third
  round proposed a warp after the 60 s settle, once the window has stopped changing, followed by a
  fixed wait before the screenshots, so that the motion event is handled under the final layout in
  every boot: a change to P0.7's capture, not to K0, which needed another development smoke beyond
  that round's one. D90 adopted it as round 4 (below). In Phase 1 the field lies inside step-0's
  status-bar mask either way.
- Round 4's development smoke (D90; planned with this text, before it runs). The capture of P0.7 as
  now registered (the warp after the 60 s settle, then the 4 s wait), from the export of round 4's
  head, one job at V = 20 on an empty queue and outside every successor E session:
  `experiments/manifests/s2v4/dev-smoke-v5.json`, smoke 1240's 240 slots plus a second boot of every
  capture slot of the 7 Impress dev tasks (S, A, AR, PL, AD and PD at rep 2; E and ER, which already
  have two boots, at reps 3 and 4), each placed right after the slot it repeats, in the same block: 310 slots
  (240 capture, 70 gold), 140 Impress capture boots, 98 minutes requested
  (`harness/s2_locale/dev_smoke.py render`). Then the oracle's registered route on its run directory.
  D90's acceptance criterion, fixed before the smoke: (a) on all 17 dev tasks every masked boot pair
  E-E2, ER-ER2, AD-AR and E-S is observed and at most tol6 (the route's tolerance on this run), so I2,
  I5 and I6 are 17 of 17; (b) no Impress boot shows a deviating status-bar field. Its reading, fixed
  now (`dev_smoke.py read`, development only): every pair is counted with K0's rule (a channel
  differing by more than 20, outside the top bar and both renders' caret masks), on the whole screen
  and in LibreOffice's status bar (rows 1060-1079); (a) reads the four registered pairs; (b) reads, on
  the Impress dev tasks, the registered pairs and every further boot of a cell against that cell's
  first boot (S-S2, E-E3, E-E4, A-A2, ER-ER3, ER-ER4, AR-AR2, PL-PL2, AD-AD2, PD-PD2), so every Impress
  boot is in at least one pair, and a pair shows a deviating field when more than 10 pixels differ in
  the status-bar rows (a changed digit of the field changes whole glyphs: three changed digits gave
  148 and 142 px in smoke 1240, while its registered boot pairs differed by at most 1 px anywhere
  else). Zero
  deviations in about 140 Impress boots bound the per-boot rate near 2% (95%). D90's stop rule, fixed
  with it: if the smoke misses the criterion, or a fresh audit of round 4 finds a blocking item that
  needs another host smoke, S2 v4 ends at an honest exit, and its instrument findings (the shipped
  catalogs, the reproducible images, the pointer-field instability) are reported as a record; no round
  5 follows. The smoke's result is entered here, in the round-4 review log and in the forecast when it
  has run.

## Phase 1 (admitted under D80 (iv) if K0 and K1 pass)

- P1.1 Tasks: the runnable census (admitted plus runnable, at most 106). Cells: E, A, ER, AR.
- P1.2 Placebo cell PL: the en-LTR interface with the toolbar items in the fixed seeded order, n_pl = 2
  per task (one per harness).
- Episodes: n = 4 per (task, cell) in the 2x2 (2 per harness) and 2 in PL: 18 per task (1,908 at 106).
- Order: one serving session (one GPU job and its CPU VM job). Task blocks in a seeded order (PCG64 seed
  42); within a block the 18 episodes in a seeded interleave; cells assigned to VM slots at random within
  each batch of 20, slot and batch recorded.
- Pointer warp, at every episode start (round 4, D90: after the settle): after the guard's warm-up
  and the 60 s settle, the pointer is moved once to (995, 540) exactly as in P0.7
  (`vm_probe.warp_pointer`: one absolute XTest motion, read back), and the episode waits the same fixed
  4 s (`vm_probe.POINTER_WAIT_S`) before the agent's first screenshot; a failed warp is an
  infrastructure loss. So the agent's first screenshot shows the cursor at (995, 540), over the
  document region, not where the boot leaves it ((1728, 972) in every capture slot of smokes 1214 and
  1240). S1a's episodes started from the boot's resting point, so this is a difference from S1a (and
  the 4 s wait adds 4 s before the first step) that K5's comparison of the en cell with S1a's English
  success carries (disclosed).
- Step-0 check: each episode's first screenshot (after S1a's setup, the warm-up, the 60 s settle, the
  pointer warp and its 4 s wait, as the Phase 0 capture slot's first screenshot) against the first
  screenshot of the
  Phase 0 render of its (task, cell) from the same lane and image, counted as P0.7 counts (a channel
  differing by more than 20), outside the mask: the GNOME top bar (rows 0-31); LibreOffice's status
  bar (rows 1060-1079, below its top border at row 1059 in every dev render of Calc, Writer and Impress
  in both directions; it holds Impress's pointer-position field, the only part of the screen smokes
  1214 and 1240 saw change between boots: every differing pixel of their boot-to-boot pairs above tol6
  lies in rows 1064-1076); and the caret mask of the Phase 0 render (the pixels that differ between
  its two screenshots 1 s apart; the episode has one screenshot, so its own caret cannot be masked,
  and a caret blinking at the reference's place differs by far fewer pixels than tol6's 50-pixel
  floor). The status-bar rows are step-0's own mask, a Phase 1 rule; K0's masks are unchanged. The
  episode is valid if the count is at most tol6 (K0's tolerance, frozen with K0's oracle record); a
  mismatch makes it invalid.
- Step-0 and the A/A gate (I6 lets up to 5% of tasks exceed tol6 between E and E2, while K3 stops Phase
  1 above 2% step-0 failures in a cell; a task whose screen varies between boots would fail step-0 in
  every episode). A task whose Phase 0 E against E2 count exceeds tol6 is A/A-unstable: its episodes
  take no step-0 check (the image check and the keyboard check still run), they are valid, they are
  outside K3's base, and every estimand is also reported without the A/A-unstable tasks. K0 is not
  touched: this reads its I6 per task. The census has a second boot of the mirrored layout (ER2) only
  for the 17 dev tasks, so the A/A reading per task is E against E2 in every cell. The mirrored-layout
  variation smoke 1214 found (Impress's status-bar pointer field: above tol6 between ER and ER2 on 3 of
  the 7 Impress dev tasks and between AD and AR on 1, never between E and E2) was reduced by the third
  round's warp before the settle (smoke 1240: those four pairs at 0 px, but the field took another
  value in 2 of 70 Impress boots, one of them in a left-to-right cell); round 4 warps after the settle
  (P0.7; its development smoke is in section "Development smoke"), and the field lies inside step-0's
  status-bar mask in any case. A variation elsewhere on the screen would still count against K3, and
  is reported per cell.
- Keyboard check, at every episode start: the guest's `setxkbmap -query` layout, its set of running
  input-method processes and GNOME's configured input sources (`gsettings get
  org.gnome.desktop.input-sources sources`) each equal the stock cell S's record of the same task in
  Phase 0 (the development smokes record `us,us` and `ibus-daemon` in every slot, S included); when that
  task's S slot is unobserved (lost twice; S is not an admission cell), they must equal one of the
  census's S records (in smokes 1201, 1214 and 1240 every S slot recorded the same facts); a difference
  is an infrastructure loss.
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
  lane on the per-slot cell images with the GPU serving job, the pointer warp, the step-0 check with its
  mask, the keyboard and image checks, the postconfig rule, the re-queue at the end of the task block, the K8 cut at the last complete block,
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
| Phase 0 (P0.6, capture and gold sweep, oracle) | 0 | CPU-only lane and container jobs, no GRES; about 44 + 95 VM-hours |
| Overlay build and pre-funded retry | 0.10 | 3 + 3 minutes, as S1a |
| Phase 1 (one job, K at most 106, n = 4 in the 2x2, n_pl = 2) | 6.73 | ceil(3 + 113.2/60 + (1,908 x 197.73/20 + 104.6) x 1.2 x 1.05 / 60) = 404 minutes |
| Registered total | 6.83 | below D20's 8 GPU-h line; admitted by D80 (iv) if K0 and K1 pass |

## Infrastructure failures and exclusions

One rule for Phase 0 and Phase 1. As `q2-stage1-rescoped-v1` section 15 and D56, plus the image check,
the keyboard check and one departure: an undelivered observation, a guest-server restart, a guest
transport failure (no reply), a setup step that fails in the guest, a failed pointer warp (the guest
cannot make it, or the pointer reads back elsewhere; P0.7), a postconfig server error (a
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

K1 passes on the five images: 0.85. K0 passes (at least 62 admitted, instrument checks hold): 0.55
(0.75 at the start of the repair round; 0.65 after smoke 1214, which showed only the AD-AR case; 0.55
after the third round, with every number of smokes 1214 and 1240 in hand: the pilot had 83 of 105
tasks with a passing gold and 13 of 17 dev tasks are admitted, but with the third round's warp before
the settle the Impress pointer field still took another value in 2 of 70 boots, which puts I2, I5 and
I6 each at risk (about 0.98 each at that rate, much less if the true rate is a few times higher), and
I1-doc's 100% bar fails on a single task without a document region or a lost ER or PD slot of a named
dev task). Round 4 moves the warp after the settle; this forecast is revised with its development
smoke's result.
Descriptors valid: 0.5 (O3 17 of 17 and O2 15 of 17 on smoke 1240's dev renders, 13 and 15 on 1214's).
Phase 1 reached: about 0.45. If it runs: D PRESENT_HARM 0.35, D SMALL 0.45, EXCESS_OVER_PLACEBO given D
PRESENT_HARM 0.5, T PRESENT_HARM 0.45, T SMALL 0.35.

## Freeze procedure

1. Build and test, on dev tasks only, the Phase 0 and K1 code. Done in the repair round (D84): the image
   build (reproducible, re-pinned), the per-slot lane with the `phase0` purpose and the census, the
   capture probe with the P0.10 reader, the gold slot and the gold rows, the PD variant, the oracle's VM
   adapter with the reader of the sweep's records into `k0_v4.decide`'s inputs, and `ap_delta.py` with
   its K1 plan, verdict and batch file. Third round (D87): the pointer warp in the capture, the resume
   counted in job order with its manifest computed and checked from the interrupted job's records,
   `run_rung`'s pre-run checks, the oracle's registered route (development runs: section "Development
   smoke"). Round 4 (D90): the warp after the 60 s settle with the fixed 4 s wait, the job order from
   the Slurm job id the batch file writes (the lane receipt a cross-check), TERM handled in the lane,
   `t_start` in the image-check receipt and the zero-record census job, and the development smoke of
   D90's acceptance criterion.
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
   `submit` (and, if the census job is interrupted, its one resume through `render-census
   --resume-from-records`); then the oracle (the registered container job of P0.7, `oracle_vm.py
   --k0`) and `k0_v4.decide` (K0).
6. If K0 and K1 pass as registered: the Phase 1 executor addendum (section "Phase 1": built, dry-run on
   dev tasks only, audited, frozen as its own ledger row), then Phase 1 under D80 (iv) within its cap.

Steps 3 and 4 and the admission of step 5's registered manifests were rehearsed on a scratch clone in the
repair round (section "Changes in the repair round (D84): review log"), at `0a1d18e7`, and again by
the third round's auditor at that round's head, with a stand-in resume run directory remapped in
scratch (D90). A resume manifest is admitted only against the interrupted job's run directory, so a
rehearsal of it needs a stand-in run directory, created only in a scratch clone, never under the
host's registered run root (where `submit` would then refuse the real census job); the unit tests
do that (`tests/test_s2v4_vm_lane.py`), and the rehearsal is repeated at the final head before the
freeze.

## Code and inputs of record

Phase 0 and K1 run from the freeze commit's export (D56's words). The table gives the SHA-256 of every
file they run or read at this file's commit: first the S2 v4 code and inputs (the K0 code: `k0_v4.py`,
`k0_inputs.py`, `oracle_vm.py` and the v3 oracle and plants it reuses; the lane, probe, gold slot and
guest helper; the census, the gold rows, the PD variant, the K1 plan and `ap_delta.py`; the image pins
and the batch files), then, sorted, the shared code they import (found by walking the imports of the
lane, the probe, the gold slot, the oracle, the K0 reader, the PD variant's builder, the image build
and `ap_delta`: S1a's lane, driver and OSWorld adapter, harness/q2's VM modules, the K2 injection
executor and the checker-mutation controls), the guest scripts the lanes run in the VM (the guard,
the K2 guest helper), and every file of harness/q2's closed world, which K1 runs through harness/q2's
driver and which its own frozen executor addendum also pins (`pins_table.files`). The status-fill
commit re-fills the table (`python -m harness.s2_locale.pins_table`), and
`tests/test_s2v4_registration.py` keeps it equal to the tree and checks that it holds every file of the
import walk.

<!-- PINS:BEGIN -->
| File | SHA-256 |
|---|---|
| `harness/s2_locale/k0_v4.py` | `d76ad39b8bb6da7e96e8afd3a43de2f8b9a90050bc509cb555f192a233712081` |
| `harness/s2_locale/k0_inputs.py` | `847cf15a7564aba407cfd0afe86d6ed39920a9eef6633f2ae1a9e9223590cb21` |
| `harness/s2_locale/oracle.py` | `c43c731daaf2319a3fb3f7a17b3104e5e1c4e73ba0c84802c2a8a3884d139798` |
| `harness/s2_locale/oracle_vm.py` | `b264df26070dfe3e8687e897dff57ce4a0229ea698580057cae44c5ca5e5056e` |
| `harness/s2_locale/phase0.py` | `a15d8caffa16d953c5800e3e251f8d0c8d11d344937110897de0f61b6319c85e` |
| `harness/s2_locale/capture.py` | `6781c860f0ef0e8ff5a21e7f045f36ea47da19f575519be217bca52ca2614f7c` |
| `harness/s2_locale/catalog.py` | `9b95de047690570766e458fccce16ba90a8d0123b13cf3dc99d1f9e37fce57bf` |
| `harness/s2_locale/vm_lane.py` | `c36ff20025db2f3817e317737cccc6bb6c508f595d8f9223bf4b1f44bd20e588` |
| `harness/s2_locale/vm_probe.py` | `68a4d430e890a3a30206675dff12fde9237403290bc0cb5d66b6e5b3f196ae17` |
| `harness/s2_locale/vm_gold.py` | `20ccb99a03ed311a7db15a81da19d8d6a3e4aa150636b9bb53aa957e6821a27f` |
| `harness/s2_locale/guest/s2_guest.py` | `891170d8265665b0cbccca18bc6f7470ae1fcbc6f0cad5b514bf13e43b5bb94b` |
| `harness/s2_locale/golds.py` | `0d8fad9fde736ee3fcd80492b5c905d7d6a35e690f9cf66559cf42ff87c25f9e` |
| `harness/s2_locale/pd_cache.py` | `f75c520a6d8fbc7675c12ff1873ec36817eff9efa00ffa4b190fa05e81a10ddd` |
| `harness/s2_locale/ap_delta.py` | `481c1e21e22093d5ed3e0f3358cbbfd3305192cfb1a707a283f8fb266a1f1d37` |
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
| `harness/__init__.py` | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/q2/__init__.py` | `0932bda132c1dab03f40e460874a6827c4609424815e65eedcfefd3cd0b943a1` |
| `harness/q2/action_path/__init__.py` | `8ce4d0afdd20f6b09dbb4e9d40d24acead2fc1992fccebd1ddf3891ec402613f` |
| `harness/q2/action_path/acceptance.py` | `ae5470e56e00a4a4a31fb591d41654efe29f7f0a4f45203c9cb03419ec55c573` |
| `harness/q2/action_path/adapters.py` | `3a62eb109d656a717dfe9cbce31fba3bcf02457e9f5690f3e20639e8becbaf40` |
| `harness/q2/action_path/build_catalog.py` | `f7b5b9650c8d416b99507ebaf8522f8075aad928ead7e4c3b702bd2ee63435d8` |
| `harness/q2/action_path/build_derived.py` | `c3e05c8f72c3f49849be7ce59a7b655067c61679e5dbdfa8ac2c130c5299c4e0` |
| `harness/q2/action_path/build_keysyms.py` | `1a977f6c4e8981f3f0ce2040f2ecae28c87f8cf8c730977c9480db900ff91cbf` |
| `harness/q2/action_path/build_suite.py` | `1980d245c8bd4a7175124a74f2131d513facc127abfc5c10ec0db25fd1cfbc3a` |
| `harness/q2/action_path/canary.yaml` | `16e15b6a48a6a560958500b1e6507e1be7368fd0fff2348cb5ed7188e66881ff` |
| `harness/q2/action_path/canary_targets.json` | `a49782274cf7c3dec0b6ceca64564207824220b2dc1572387f98339b0d4805f6` |
| `harness/q2/action_path/catalog.py` | `2223a05b4e88dbc8af52751c9c87b10db99a121cdb93e5289979c657bf92126b` |
| `harness/q2/action_path/catalog.yaml` | `5934c4281cb85a8309be32cb98442b038054a2bba0e7ec3755e20112710b7bba` |
| `harness/q2/action_path/controls.py` | `d96e7b2acdecfef134c08c22f23113c8d78fae9d8a35d0e5ad826a2f0af9cc72` |
| `harness/q2/action_path/corpus.py` | `b4b1f974d481c249fcb22f2b77102579fcb82e504c64375a9183783f63bfbe49` |
| `harness/q2/action_path/executor.py` | `d5c43bbb76926da056c15a39ddcbf05e1c328bd7dddb6a726cde3c46c2f9776a` |
| `harness/q2/action_path/expressible_entries.json` | `380e058e9aced24e30cbfc93ebace901a5cb02b567b42f0cceb7543c87c822ac` |
| `harness/q2/action_path/gating_set.json` | `fe2afcaa5fcb6710f54510555633bcd86bc8d516f01211253cfd46271fdf5a6a` |
| `harness/q2/action_path/ir.py` | `33dc24771b823597eef453a4994faf730d0364bd090488aa13e9de5e3498d305` |
| `harness/q2/action_path/keynames.py` | `ed7afec8fd66e1f1ba1a08e2df6eccd834a24f9f22e6bd4a79604153e3816b72` |
| `harness/q2/action_path/keysyms.json` | `a1ea436d9bd4ae8d9fbc8305772f7dca776858b023092ce1cea059a693924acb` |
| `harness/q2/action_path/l0_raw.py` | `391249f7900dfc327947505526b22710f7dd6bf70f71a230d9865ae7da174f84` |
| `harness/q2/action_path/l0_raw_prediction.yaml` | `8b947acafeae1d2bf4fda5a715888556d9ca672e57d488a4c31dadc420f9302a` |
| `harness/q2/action_path/l0_raw_prediction_v2.yaml` | `5ce6beeb6736560e9a0fc9f84557aa3c9e35d7d30ac423b3541863613e35b489` |
| `harness/q2/action_path/mutants.py` | `1791311503e0b57808b0f378ce2cd4c93167c76a99c80f8b6666f559a1a90beb` |
| `harness/q2/action_path/mutation_operators.yaml` | `429cbc389238404b1b6c345b883db9ada5b470ebad3594a8895187aa377e1259` |
| `harness/q2/action_path/order.py` | `cc709bd455f1899df11e8bf1e780d7efadc0ad374d8e2786bdc6f6e589b65676` |
| `harness/q2/action_path/qwen35_chat_template.jinja` | `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715` |
| `harness/q2/action_path/rdev.py` | `c526f7ed5b8cc560c5419f9f5e25541b46178f2c375b24cbbee84e0093daab83` |
| `harness/q2/action_path/rdev_plan.json` | `5c9b7215c89aadfa6308bdd94c629a716c7c822a8ca626315157e84bd1495d89` |
| `harness/q2/action_path/rdev_reference.json` | `5cc48d5177a7f07baed36b90ab76ce3e10de835b42596fc6a53427add49b518a` |
| `harness/q2/action_path/suite_cells.json` | `a79073a2f5e6e7d7e109b14d50fb4c1e2791f856504c32cd855911e726a95c95` |
| `harness/q2/action_path/trial_times.json` | `a33ca2e024d6f24a31a60ff62053be1fb197af48c996ae99fb75aff4d20217e5` |
| `harness/q2/action_path/upstream/PROVENANCE.json` | `5bef93df835c560b1f8dc6e8cfe7d6c207ba7fbe2e26c861541878563062744d` |
| `harness/q2/action_path/upstream/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `harness/q2/action_path/upstream/gym_anything_aae6f7607.py` | `c624cee586e3b8b8b2ac12102ae1fca91e7de154b494035c4289123f38887aa6` |
| `harness/q2/action_path/upstream/gym_anything_bf965cde0.py` | `f5fb13d2ab6eb024be48f28a439ecb3147308f126217054d4587649f9b1b818f` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc.py` | `9e21622823994721407dc04f606b58c8cbd8848e780e4657e8ee13cb363c77ab` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc_fixed.py` | `9558b956004f6c971e881f073c42792e3d5d437396dbe6c0b407b250df3d8fdf` |
| `harness/q2/action_path/upstream/vendor.py` | `afae1b5d89cf47709727281eab01b1104e6f6b5eabf1c6960e0947c3b23d236f` |
| `harness/q2/action_path/verdict.py` | `29e4501532ab740922645a26a05a365a8aedc95f237efc66be5048df8354c8c4` |
| `harness/q2/action_path/vm_hours.json` | `5fc0617303a2782c02e67888be4584261239e5f90268e4e39d7524aff625636e` |
| `harness/q2/action_path/vm_hours.py` | `58b7379377ae87a72c85076ee87441fbb2da12042a15e9ae4aa62f67365074b1` |
| `harness/q2/action_path/vocab.py` | `f26dd7d34988aebf8e8bbeb3ea118e6da3b9d37505ba8433a6eb6d9f0f186792` |
| `harness/q2/action_path/volume.py` | `91cbbb7f2bf7cd8715ae7c3c88fb8744ff40bd89955283eb680578c24d2a09c7` |
| `harness/q2/action_path/volume_plan.json` | `9567d257b769273788153c4193981f1c7eb1e8664b4d1ef36389b4fbd211802a` |
| `harness/q2/vm/__init__.py` | `43fce1e08200acef9b9b82c914eba0713c0d60716bd2be0feaaade042dee3b19` |
| `harness/q2/vm/canary_run.py` | `295bdd0916869adf79015bc6da6cba4aff2a0ab9f0dab089e4ed3a3565abb119` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/driver.py` | `06f3a29f39ad3a5de55efafd23fdfdfe121914f0f7f5dba281f4aabb68f74f7c` |
| `harness/q2/vm/guest/__init__.py` | `99215662111076fd8ca080805ee2b36156cdec720470d16b612954c50f83362f` |
| `harness/q2/vm/guest/canary.py` | `32742019db56b4f09905c50c71159c2ef3fe024a044d07f4bffb31cd41fcea1e` |
| `harness/q2/vm/guest/canary_targets.py` | `8b7233391b1da78092326c11d394f0385ee42052835a83554c76260e4201aab3` |
| `harness/q2/vm/guest/facts.py` | `4a071a39d4586a58b62419796a57b678568bdbc3bfd77ec6d50e841414dcd255` |
| `harness/q2/vm/guest/guard.py` | `19fe2da1c97c88e07062e9113a8df1b8958b583f6f3bf0e1a763f52eb10a5748` |
| `harness/q2/vm/guest/l0_fixed.py` | `7f8bed98ad22eee662d92d5422ee564d80459645d2e0c58bb6f3df74a94425f1` |
| `harness/q2/vm/guest/probe.py` | `ba5c0f1d364c80d5f8190f3c357b915cd504d754891285c3772ba959a804efeb` |
| `harness/q2/vm/guest/sentinel.py` | `98f46a7faafc58e9c65466b19ae3547288fc8829378ad7aa169b09a17161b18b` |
| `harness/q2/vm/guest/tap_selftest.py` | `7e051c0bcb45ba81c2b1fb855a9dc70115957fafa3ec7f333c8b3be5ab3bf835` |
| `harness/q2/vm/guest/xrecord_tap.py` | `6a6e9453f138776b0717a9087767be0f97460f1ea0d5302f31e21ae1a4a80a74` |
| `harness/q2/vm/guest_http.py` | `13e34f874c89b0b32f7f82ffae658682d2608bc9a0614a569742459d6b796ceb` |
| `harness/q2/vm/hmp.py` | `34b10c2661c6cf40039ca172a704fb5613d0a805e60223acc729f040caf4776a` |
| `harness/q2/vm/manifest.py` | `f238f12bdb8470919c8892eff46fe8b721e1e0c83ad08a60c0293ed8da3b9e2e` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/runner.py` | `bc944df5db3712322e6f01fc54fa6214aa6d9b6ce727282f33ae1043df303f4e` |
| `harness/q2/vm/suite.py` | `6485ddb977d8adaf42ecc8c97f6520d3467633c54aeefba0cec877986805797a` |
| `harness/q2/vm/validation.py` | `2ab5508e5a42269d447312e481b58c9f491d815d73e4977ba9c55d235231116f` |
| `harness/q2_mutation/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `harness/q2_mutation/controls.py` | `0fbc20d1a967e48689937359d7065b53bebd2cea50d7c3f8088fef12c702624f` |
| `harness/q2_mutation/offline_eval.py` | `a598e7fb71c434a7ef135afd250576db1025c4b0e77715413ab78c3e521f877a` |
| `harness/q2_mutation/reachability.py` | `00e106f6003a9f1ef9b9ca4cdbd59fbf1145c5608c6c67e37b57a7a094da0e9b` |
| `harness/q2_mutation/schema.py` | `65d91703754b4026b15f6c53a4a6069da723b58d749730770da2910c1edf427d` |
| `harness/q2_mutation/tasks.py` | `4040d852b18d06eea2fe47155ac642af689dea5477cd4a16a2dd5c71f42d8ecc` |
| `harness/q2_mutation/vm_injection.py` | `43886a101ea7f0dc569454be99bd7bfd1fea051713e0ec886ca25dcf3071f567` |
| `harness/q2_mutation_k2/__init__.py` | `66667a5fcd60b2bfcb72dbe74c94b1443f68dbe75a6ce0cf28816807cccc1ebf` |
| `harness/q2_mutation_k2/executor.py` | `0d104aa6c51dde519d42a33829fdf5f811b524b202463eab5389f1c49d7c48b7` |
| `harness/q2_mutation_k2/guest/k2_guest.py` | `869ebb3811f44ee990f587077756c3bb774392930e6973a54a2225714608dda8` |
| `harness/q2_mutation_k2/rules.py` | `58ea109a1aff6d6b059b6ca841b99a3a8b7ca858fe698c8b5ab33238e6be8c05` |
| `harness/q2_stage1/__init__.py` | `0e2190149cf640fac07dab26332a26f696374ff4400c23aab82e8cf766f3b334` |
| `harness/q2_stage1/agents.py` | `8e72acbd79645b45ccd95cd213d5f8564d7114af538561e28219c12cf0eb0ba1` |
| `harness/q2_stage1/driver.py` | `52f835f6a2f8149ec0b3c14720593c02a42e1d410ab25062845fd3700aeee227` |
| `harness/q2_stage1/engine.py` | `3e0942349a8fc5b2aef5294a28c029ca318acff88f4cd897df274bb6e3b51bf9` |
| `harness/q2_stage1/lane.py` | `d646b144f857d5947ed20d27a5d33107123913321969c89af22729674246eaa5` |
| `harness/q2_stage1/osworld_live.py` | `38b017c04f67b59e08bc1d764702a2ff91c80ebde8054c8e80bc277746334313` |
| `harness/q2_stage1/plan.py` | `1f9c77f758ed590d99597488219cc49fae0e0f3c53567d628d14382346fc2187` |
| `harness/q2_stage1/records.py` | `8c276018b98312dd8aab5a626be55e6421f3d1470aefc6ceae70a471c9082e85` |
| `harness/q2_stage1/rules.py` | `63ed09b0362595e85ac65c9bd29b090dc8b1a3a5e4ab3ace559243a82389d8b0` |
| `harness/s2_locale/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
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

Added in the third round (D87):

100. One warp of the pointer to (995, 540) after the 60 s settle, then a fixed 4 s wait before the
     first screenshot, in every Phase 0 capture slot and at every Phase 1 episode start (P0.7, Phase 1;
     round 4, D90, moved the third round's warp from before the settle to after it and added the
     wait).
101. Phase 0's records counted in job order, by the Slurm job id the batch file writes before the lane
     starts (round 4, D90: the lane receipt is a cross-check only), a cut re-queue rerun by the resume,
     the resume manifest computed from and checked against the interrupted job's records, at most one
     resume, TERM stopping the lane like USR1, and a census job with zero records resumed from its
     first block (P0.7).
102. Step-0's own mask adds LibreOffice's status bar (rows 1060-1079); K0's masks are unchanged (Phase 1).
103. The oracle's registered route: the metric image and the argv pinned, its environment recorded
     (P0.7).

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
| I6 lets 5% of tasks fail A/A while K3 allows 2% step-0 failures | Not fixed in this round (corrected in the third round): A/A-unstable tasks (E against E2 above tol6) take no step-0 check and are outside K3's base, and every estimand is also reported without them, but that rule reads only E against E2, and smoke 1214 had already shown boot-to-boot differences in the mirrored cells that it does not cover (ER against ER2 above tol6 on 3 Impress dev tasks, AD against AR on 1). The third round reduced them (the pointer warp before the settle; smoke 1240 still saw the field vary in 2 of 70 Impress boots) and masked the status bar in step-0, which covers that field for Phase 1 (section "Changes in the third round (D87): review log"); round 4 moves the warp after the settle (D90) |
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
(`freeze-rehearsal/rehearsal.json`). The round left one development finding unresolved: Impress's
status-bar pointer-position field varied between boots in the mirrored cells (smoke 1214, section
"Development smoke"), and this log reported only its AD-against-AR case. The fresh review and audit
found the rest and made it blocking (D87); the third round addressed it, and its development smoke
showed it reduced but not removed (next section); round 4 (D90) moves the warp after the settle.


## Changes in the third round (D87): review log

A fresh code review and a fresh pre-freeze audit of `b3c5537f` found the package not ready to freeze,
with two blocking items (D87). Every item, and what this round did. "Fixed" items are in the code and
text above; the development runs are under `program/evidence/2026-10-11/s2v4-image/` (smoke 1240 and
the oracle-route job 1241).

Blocking (the review and the audit found both):

| Item | Disposition |
|---|---|
| B1. Impress's status-bar pointer-position field changes from boot to boot in the mirrored cells: in smoke 1214, ER against ER2 above tol6 on 3 of the 7 Impress dev tasks (293, 148 and 139 px) and AD against AR on 1 (513 px), E against E2 never. I5 is 16 of 17 on the dev tasks, and P(I5 holds) is about 0.48 to 0.01; Phase 1's A/A exemption read only E against E2; the registration reported only the AD-AR case, called the I6/K3 fix "Fixed" and left an open item "recorded for the next review" | Partly fixed in the third round, as proposed, and not resolved there: the fresh review and audit of the third round's head kept it blocking (D90), and round 4 made the change proposed in (d) (section "Changes in round 4 (D90): review log"). K0 untouched. (a) The pointer warp: one absolute XTest motion to (995, 540) after the warm-up and before the 60 s settle, read back, through the guest helper (`s2_guest.py` mode `pointer`, `vm_probe.warp_pointer`), in every Phase 0 capture slot (P0.7) and at every Phase 1 episode start (Phase 1); P0.7 states the point, the mechanism and the reason; a failed warp is an infrastructure loss. Tests: the probe warps once, after the warm-up and before the settle; a pointer read back elsewhere is a loss; the guest mode sends one MotionNotify at the target (`tests/test_s2v4_vm_lane.py`). (b) Phase 1's A/A rule matched to the layout through step-0's own mask of LibreOffice's status bar (rows 1060-1079; the audit's second option); the A/A-unstable reading stays E against E2, since the census has ER2 only for the dev tasks (stated in Phase 1). (c) Every boot-to-boot pair of smoke 1214 is reported (section "Development smoke"), the repair-round log's I6/K3 disposition is corrected, and its closing note's open item is replaced. (d) Smoke 1240, smoke 1214's shape on the dev tasks with the warp, read by the registered oracle route (Slurm 1241): AD against AR 0 px on all 17 tasks (I5 17 of 17), E against E2 at most 1 px (I6 17 of 17), and the three ER-ER2 tasks of 1214 at 0 px; but the field took another value in 2 of the 70 Impress capture boots, so ER against ER2 is 142 px on `af23762e` and E against S 148 px on `ac9bb6cb` (I2 16 of 17: on the dev tasks K0's instrument checks still fail). The layout still changed after the warp in those boots. The change proposed then (not made in the third round: it needed another development smoke, beyond that round's one): warp after the 60 s settle, once the window has stopped changing, then a short wait before the screenshots, in P0.7 and in Phase 1; a change to the capture, not to K0. Round 4 made it (D90). (e) The forecast is revised |
| B2. Which records count after a resumed Phase 0 job depended on the order of `--runs`; a first-attempt loss whose re-queue the interruption cut counted as final (unobserved after one loss); the resume manifest was checked only loosely (any later block, any 64-hex string, any number of resumes), and nothing rendered it | Fixed as described here, with one gap the fresh review and audit of the third round found (D90): the job order came from the lane receipt alone, so a job ended by TERM (no receipt) or by a failed image check (a receipt without `t_start`) could be neither read nor resumed. Round 4 takes the job order from the Slurm job id the batch file writes (section "Changes in round 4 (D90): review log"). What the third round did: `k0_inputs.run_order` and `load_runs` put the run directories in job order by the lane receipt's job id, which must agree with its `t_start` (refused otherwise; at most two jobs, the second the resume of the first), and `oracle_vm` reads its renders through them. `final_in_job`: probed, or lost on the second attempt; a cut re-queue is not final and the resumed job reruns the slot (chosen over "counts as unobserved"; P0.7). `vm_lane.py render-census --resume-from-records RUN_DIR/probes.jsonl` computes `resume_from_block` and `resumes` (job id, run directory, records SHA-256) from the interrupted job's run directory, and `check_registered` recomputes them and admits only that rendering; a resumed job is not resumed again, `submit` refuses a second census job and a second resume (`check_once`), and `phase0` is pinned to its run root. Tests: the order of the arguments does not matter; directories without a job order are refused; a cut re-queue is rerun; the rendered resume is admitted and every edit of it refused; one census job and one resume (`tests/test_s2v4_k0.py`, `test_s2v4_oracle_vm.py`, `test_s2v4_vm_lane.py`) |

Not blocking:

| Item | Disposition |
|---|---|
| K0 byte-identical and `k0_v4.py` unchanged; the S2 v4 tests pass; the ledger equals main's | Confirmed: the K0 section hashes to `ed38b953...` (tested), `k0_v4.py` is unchanged since `ee0841b3`, and `main` was merged with every ledger row kept (rows 1-20; this id has none) |
| Reproducibility from the double-build records; the K1 checks the owner's rehearsal skipped (C2, A5, A6, A1 and A2 on PL) admitted from a freeze export; no network inside measurement VMs; the postconfig rule implemented; the P0.10 reader matches the checkers | Confirmed by the review and the audit; nothing to change. A1 and A2 on PL fit one job with 46 and 96 minutes of headroom (noted) |
| The code-and-inputs table omitted the shared code the lanes import | Fixed: the table lists the S2 v4 files, the shared code found by walking the imports of the lane, probe, gold slot, oracle, K0 reader, PD builder, image build and `ap_delta` (S1a's lane, driver and OSWorld adapter; harness/q2's VM modules; the K2 executor; the checker-mutation controls and offline evaluator), the guest scripts the lanes run in the VM (the guard, the K2 guest helper) and harness/q2's closed world (`pins_table.files`); a test checks that the table holds the whole import walk. `smoke_summary.py`, which the review listed, is a development summary that no registered job imports or runs, so it is not listed |
| The registered oracle route never ran as registered; its image (the metric image, not v3's oracle image) and argv were not pinned | Fixed: P0.7 pins the image ID and the argv (`oracle_vm.ORACLE_IMAGE_ID`, `registered_argv`), and the output records the interpreter and the numpy, scipy and Pillow versions. The route ran once on the dev records as a CPU container job (Slurm 1241, on smoke 1240's run directory, 34 s; `oracle-route-1241/`), in Python 3.12.13 with numpy 1.26.4, scipy 1.17.1 and Pillow 11.0.0; a run of the same code on the Mac (numpy 2.5.2, scipy 1.18.0, Pillow 12.3.0) on a copy of the records gave the same metrics, tolerances, instrument checks and K0 output (one reported per-task mean displacement differs in its last digit; `mac-crosscheck.json`). It was not run on smoke 1214's records, so the Mac's earlier `oracle-dev.json` is not compared with the container directly; this cross-check on 1240 takes that place |
| Census timing: 4.3 minutes per attempt, so about 4.9 hours and 95 VM-hours, not 3.5 minutes, 4 hours and 80 VM-hours; 81 CPUs against smoke 1214's 82 | Fixed in the text (P0.7, "Order and cost", compute caps). The 364-minute request stays (about 20% above the expected time; an overrun is the resume rule's case); Slurm rounds the 81 CPUs requested to 82, as it did for smoke 1214 |
| K1's table sums to about 44.3 VM-hours, not 46 | Fixed |
| `run_rung` dropped `driver.main`'s pre-run checks | Fixed: restored with harness/q2's own functions (Docker's facts, the VM image's ID and digest, the runner image, per image the file checks and `qemu-img info`, the dangling volumes before and after) and tested, including a missing runner image stopping the rung before any session; development jobs 1217 and 1218 ran without them (disclosed) |
| `check_registered` matched K1 plan entries on the first campaign's cells only | Fixed: every campaign of a `k1` job must name the first campaign's cells and mount its image; tested |
| Development numbers to state plainly (the descriptor plants, I1-doc's practical meaning, K0 on the dev tasks, `af23762e`'s gold) | Fixed (section "Development smoke") |
| Phase 1's keyboard reference when S was unobserved | Fixed: then any of the census's S records (Phase 1) |
| The timing of 1217 and 1218 relative to R04 was not in the evidence README | Fixed: in the README and in section "Development smoke" (D87) |
| Frozen-text wording ("Evidence for this draft", "done in this draft's run") | Fixed: "Evidence", "done before the freeze" |
| Optional hardening: `validate_manifest` comparing the export's files with the frozen table | Not done: the run-time gate stays `check_export` (the export's `.git_sha` is the manifest's freeze commit, which `render-census` and `ap_delta.py render` check with git); the tests check the table against the tree at the freeze commit |
| Program records; superseded images on the host | The orchestrator's; unchanged (build 1199's images and build 1207's copy b are kept, unpinned) |

Tests at this round's head: every S2 v4 test file (`tests/test_s2v4_*.py`) gives 141 passed and 1
skipped (the e2fsprogs round trip, which runs only where e2fsprogs is installed; it ran as build
1207's self-test); ruff is clean on every file this round changed. The K0 section's SHA-256 is
unchanged (`ed38b953...`), and `harness/s2_locale/k0_v4.py` is unchanged since `ee0841b3`.

Closing the third round: `main` was merged in with every ledger row kept (rows 1-20; this id has
none); one development smoke (Slurm 1240) and one run of the oracle's registered route (Slurm 1241)
ran on the dev tasks, each submitted on an empty queue with no other workstream's step pending and no
E session in progress. Every non-blocking item was fixed, and B2 as described (with the gap above).
B1 was reduced, not resolved: with the warp before the 60 s settle, the dev tasks still failed I2
(`ac9bb6cb`, 148 px in Impress's pointer field). The round's owner agent returned no report (its
output was placeholders); the fresh review and audit read the branch head directly. The program
decided one final repair round, with its acceptance criterion and stop rule fixed in advance (D90;
next section).

## Changes in round 4 (D90): review log

A fresh code review and a fresh pre-freeze audit of the third round's head (`c1a56989`) found two
blocking items that round's fixes had not cleared, and the audit a third (D90). D90 made round 4 the
last repair round for S2 v4, adopted the fixes both reviewers proposed, and fixed in advance the
round's acceptance criterion (section "Development smoke", round 4's smoke) and its stop rule: if the
smoke misses the criterion, or a fresh audit of round 4 finds a blocking item that needs another host
smoke, S2 v4 ends at an honest exit, its instrument findings reported as a record, and no round 5
follows. K0 stays byte-identical (`ed38b953...`), and `harness/s2_locale/k0_v4.py` is unchanged.

Blocking:

| Item | Disposition |
|---|---|
| B1 (review and audit). The warp before the 60 s settle did not make Impress's pointer field the same in every boot: it landed within about a second of the task's open step, while the window was still being laid out; in smoke 1240 and on the oracle's registered route (1241) I2 was 16 of 17 (E against S 148 px on `ac9bb6cb`), ER against ER2 142 px on `af23762e`, and the variation moved into the left-to-right pairs | Fixed in the capture, as both proposed; K0 untouched. `vm_probe.Probe.run` now warps once after the 60 s settle and then waits a fixed `POINTER_WAIT_S` = 4 s before the two screenshots (chosen before the smoke: longer than VCL's quick-help and balloon tip delays of 0.5 s and 1.5 s); the same at every Phase 1 episode start. P0.7, Phase 1 and design decision 100 say so, and the ordering test (`test_probe_warps_the_pointer_after_the_settle_and_waits_before_the_screenshots`) requires warm-up, settle, warp, wait, screenshot, 1 s, screenshot, in that order. The pre-settle warp's added left-to-right variation and its timing are reported in section "Development smoke". Round 4's development smoke (`dev-smoke-v5.json`: 310 slots, 140 Impress capture boots) and its reading (`dev_smoke.py`) are fixed before it runs; its result is entered here when it has run |
| B2 (review and audit). The job order came from `lane-receipt.json` alone: a census job ended by TERM wrote no receipt, and the image-check receipt had no `t_start`, so such a job could be neither read by the oracle nor resumed; the zero-record case was undefined | Fixed as both proposed. `k0_inputs.job_id`: the Slurm job id the batch file writes before the lane starts (`preflight.txt`'s `job_id`; on the host the run directory's name, which must equal it; in the oracle's container, `/ro/run1` and `/ro/run2`, `preflight.txt` alone); `run_order` orders by it, and a receipt, when present, must name the same job and its `t_start` must give the same order (a cross-check only). `vm_lane.interrupted_job` reads the job the same way and needs no receipt; a missing `probes.jsonl` is zero records. `vm_lane.main` handles TERM like USR1 (`stop_on_signals`: the lane's stop event), so a terminated lane records the slots never dispatched and writes its receipt when it has the time; the image-check receipt carries `t_start` (and `t_end`, the name and the purpose). The zero-record census job (failed image check, or stopped before any slot ended) is resumed by the general rule, from its first block, so the one resume runs the whole census; a run directory without `preflight.txt` is not a job (`check_once`). P0.7 states all of it. Tests: a census ended by TERM (no receipt) is read by `load_runs` and `render_index` and resumed through `render-census --resume-from-records` and `check_registered`; an image-check-failed census with no records is resumed from its first block and the resume admitted once; the registered route's two mounts (`registered_argv(2)`) are read in job order from `preflight.txt` whatever the mount order; a job id that disagrees between the name, `preflight.txt` and the receipt is refused; TERM sets the stop; a stopped lane records every slot as not final and writes its receipt (`tests/test_s2v4_k0.py`, `test_s2v4_oracle_vm.py`, `test_s2v4_vm_lane.py`) |
| Audit 3. The text read as unfrozen: the review log and closing note said the package was not ready to freeze, the development smoke section said a further smoke was still to run, and the freeze procedure pointed to a rehearsal still to come | The passages that described round 3 are rewritten as its history (sections "Development smoke", "Phase 1", the forecast, the freeze procedure and the third round's review log). Round 4's own result, the scratch freeze rehearsal at the final head and the status fill follow its development smoke |

Not blocking:

| Item | Disposition |
|---|---|
| Merge `main` before the freeze | Done: D88, D89 and D90 and the R03 (b) and R04 merges; the ledger is main's (rows 1-20; this id has none) |
| Cite D89 where the guest locale is held at `en_HK` and where A4(ii) is motivated | Done: P0.2, P0.5 and P0.9 (ii) cite R04's locale arm (under `ar_EG` three `compare_table` golds and `5c1a6c3d`'s `compare_pptx_files` gold flip) |
| Repeat the scratch freeze rehearsal at the final head; a stand-in resume run directory only in scratch, never under the host's registered run root | Planned after round 4's smoke, at the final head, in a scratch clone (freeze procedure) |
| `ap_delta.run_rung`'s restored pre-run checks are only unit-tested | Open: they need one host development rung before the freeze, which this code step did not run (no host job); recorded for the round's host steps |
| `check_once` does not see a census job that is still pending | Unchanged: one job at a time, each submitted on an empty queue, covers it |
| The forecast's K0 risk rested on a loosely bounded per-boot rate (2 of 70) | The forecast is revised with round 4's smoke (about 140 Impress boots) |
| A1 and A2 on PL have 46 and 96 minutes of headroom under 1,440 | Noted, unchanged |
| The third round's owner returned placeholder output; decisions, state and handoff; superseded images on the host | Disclosed (D90); the program records and the host images are the orchestrator's |

Tests at this round's code head: every S2 v4 test file (`tests/test_s2v4_*.py`, with the new
`tests/test_s2v4_dev_smoke.py` for the round-4 manifest and its reading) gives 155 passed and 1
skipped (registration 9, k0 22, oracle_vm 12, vm_lane 52, ap_delta 12, image_build 33 and the skipped
e2fsprogs round trip, which runs only where e2fsprogs is installed, fetch_langpacks 10, dev_smoke 5);
`ruff check` is clean on every file this round changed. The K0 section's SHA-256 is unchanged
(`ed38b953...`), and so are `harness/s2_locale/k0_v4.py` and the batch files.
