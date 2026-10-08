# Q2 Stage 0b: action-path suite and nested-KVM desktop runtime

Status: Stage 0 infrastructure. Nothing here is a result. The preregistration
`program/preregistrations/q2-action-path-v1.md` is a **draft**; acceptance
trials wait for the program owner to freeze it.

The suite checks that what a computer-use harness asks for is what the
desktop receives, before any Stage-1 GPU episode is spent on it. It follows the
reviewed plan's order: a catalog and its expectations first; an independent
device-level reference through the QEMU monitor; mutation testing of the suite;
one canonical action IR through one executor for both harnesses; per-harness
specs from each harness's own tool prompt; a cross-app canary; both observation
settings; and a volume certification split from development runs.

## Layout

| Path | What it is |
|---|---|
| `vm/manifest.py` | VM campaign manifest validator (decisions D12, D13), shared by the submitter and the job |
| `vm/driver.py` | Host-side driver run by `vm-campaign.sbatch`: starts and removes labelled containers |
| `vm/runner.py` | In-namespace runner (GPU-less container): boot timing, sentinel, latency, HMP reachability |
| `vm/hmp.py` | QEMU human-monitor client (the R-dev reference input path) |
| `vm/guest_http.py` | Client for the OSWorld guest server (`/screenshot`, `/execute`, `/setup/launch`, ...) |
| `vm/guest/*.py` | Scripts shipped to the guest as base64 argv: facts, reset sentinel, XRecord tap, tap self-test |
| `action_path/ir.py` | Canonical action IR (Table 21 vocabulary plus explicit holds); `clamp_point`, the IR-boundary coordinate rule |
| `action_path/keysyms.json`, `build_keysyms.py` | Every X keysym name (xorgproto 2024.1 `keysymdef.h`, MIT/X11 notice inside); the IR accepts any of them |
| `action_path/catalog.yaml` | The 100-entry catalog (draft for the owner's freeze; key entries carry the job-393 R-dev streams) |
| `action_path/catalog.py` | Catalog loader, validator and hash |
| `action_path/build_catalog.py` | Author tool that writes `catalog.yaml`; a test checks it reproduces the file byte for byte |
| `action_path/rdev.py`, `rdev_plan.json` | R-dev reference: HMP chords per key entry, projection and stability rules |
| `action_path/rdev_reference.json` | Stable R-dev streams from the reference capture (copied into `catalog.yaml`) |
| `action_path/expressible_entries.json` | Per Stage-1 harness: expressible entries (H-OSW 85, H-GA 79) and reasons for the rest |
| `action_path/vocab.py` | Stage-1 harness vocabularies and the gating set G |
| `action_path/gating_set.json` | G (86 entries) and the 14 non-gating entries with reasons |
| `action_path/mutation_operators.yaml` | 28 suite mutation operators, per-layer kill cells, the R-case table, the kill and equivalence rules |
| `action_path/l0_raw.py`, `l0_raw_prediction.yaml` | The L0-raw control's translator and its predicted failing set, written from code reading |
| `action_path/volume.py`, `volume_plan.json` | A4 volume plan: per-class action counts, sessions and bounds, and the pinned order digest |
| `action_path/canary.yaml` | A6 cross-app canary: app settings, fixtures and expected final text |
| `action_path/build_derived.py` | Regenerates `gating_set.json`, `expressible_entries.json`, `rdev_plan.json` and `volume_plan.json` (tests check them byte for byte) |
| `vm/guest/probe.py` | Guest probe: fullscreen event log, text buffer, marker block, entry delimiters (inputs addendum) |
| `vm/guest/guard.py` | Entry guard: checks (a)-(d), pointer park, side-effect restorations, probe control, the session's keyboard warm-up (inputs addendum) |
| `vm/marker.py` | Stdlib PNG row decoder and marker reader (inputs addendum) |
| `vm/guest/canary.py`, `vm/canary_run.py` | Cross-app canary driver: fixtures, profiles, launch, wait, read-back, close (inputs addendum) |
| `vm/guest/canary_targets.py` | Development tool: the canary's pointer targets from accessibility extents and screenshots |
| `vm/desktop.py` | OSWorld `b138d348` `DesktopEnv.step` and controller calls on the standard library |
| `vm/suite.py`, `vm/validation.py` | Session engine (tap and probe in their own systemd scopes, guards, actions, marker, judging, restart and accessibility-call counts) and the HMP validation of the inputs components |
| `vm/guest/l0_fixed.py`, `action_path/executor.py` | L0-fixed: the XTest executor and its base64 `DesktopEnv.step` transport (executor addendum) |
| `action_path/controls.py`, `action_path/keynames.py` | C1 detection-control translators (H-OSW-up, H-GA-buggy) and upstream key-name resolution (inputs addendum) |
| `action_path/adapters.py` | Stage-1 harness layers to IR: H-OSW-fixed and H-GA (executor addendum) |
| `action_path/upstream/` | Vendored upstream parsers (byte-for-byte line ranges, `vendor.py`, `PROVENANCE.json`) and the marked H-OSW-fixed copy |
| `action_path/corpus.py`, `build_suite.py`, `suite_cells.json`, `qwen35_chat_template.jinja` | Qwen3.5 template corpus and every cell the runner executes (executor addendum) |
| `action_path/verdict.py`, `action_path/order.py` | Trial verdicts (sections 4.3, 5, 6) and seeded run orders and sessions |
| `action_path/mutants.py` | Suite-mutation kit: the 44 scored mutants of `mutation_operators.yaml` as anchored patches |
| `action_path/acceptance.py` | The acceptance analysis: A1-A7 (A4's restart exclusion and A7's observation-service bound, decision D30), C1-C4 and the ladder's N* from campaign receipts (inputs and executor addenda) |
| `action_path/vm_hours.py`, `trial_times.json`, `vm_hours.json` | VM-hour sizing of every scored campaign from measured development trial times (executor addendum) |
| `action_path/harness_design_diffs.md` | Every design difference of each Stage-1 harness |
| `../../infra/slurm/host-single-node/vm-campaign.sbatch` | CPU-only Slurm entry point for VM work |
| `../../infra/q2-vm-runner/Dockerfile`, `image-lock.json` | GPU-less runner image (stdlib Python only); the lock records the saved image tarball and its package versions |
| `../../scripts/submit_vm_campaign.py` | Submitter-side validator and `sbatch` renderer for VM manifests |
| `../../experiments/manifests/q2-action-path/` | Submitted VM campaign manifests |

## Running a VM campaign

On the H100 host, from an exported source tree (`git archive` of a commit into
`~/cotcodec-runs/stage0/q2-action-path/src/<git sha>`, made read-only):

```bash
python3 scripts/submit_vm_campaign.py MANIFEST.yaml --dry-run
python3 scripts/submit_vm_campaign.py MANIFEST.yaml --test-only
python3 scripts/submit_vm_campaign.py MANIFEST.yaml
```

The job requests no GRES and refuses to start if Slurm shows a GPU in its TRES
or GPU variables in its environment. It checks its own SHA-256, the manifest's
SHA-256 and the source tree's SHA-256, starts the VM image by digest with
`--network none` and no published ports, runs the runner with
`--network container:<vm>` (all capabilities dropped, read-only root, host
UID), and on exit removes only containers labelled `cotcodec.slurm_job=<id>`.
CPU sets come from the job's own Slurm allocation. Raw outputs stay on the host
under `~/cotcodec-runs/stage0/q2-action-path/runs/<job>/`.

## What has run (all CPU-only Slurm jobs, 2026-10-07)

| Job | Manifest | Result |
|---|---|---|
| 369 | `boot-reset-smoke-v1.yaml` | lane smoke, 2 cold boots, every infrastructure gate passed |
| 372 | `bridge-exposure-v1.yaml` | the D13 fallback: another container reached the guest server |
| 374 | `boot-reset-v1.yaml` | 22 cold boots (p50 18.3 s, p95 20.8 s), 21/21 pristine resets, HMP reachability |
| 387 | `rdev-capture-v1.yaml` | R-dev capture, superseded (recovery presses leaked into four windows) |
| 393 | `rdev-capture-v2.yaml` | R-dev reference: 35 of 35 entries stable over 5 repetitions |
| 467 | `tap-selftest-v1.yaml` | after the review: the rewritten tap reported every remapped keysym (3 of 3 cycles); its mapping check counted the device-switch keymap re-send as unseen (gate false) |
| 468 | `rdev-capture-v3.yaml` | the R-dev plan re-captured with the rewritten tap: 35 of 35 stable and identical to job 393 |
| 469 | `tap-selftest-v2.yaml` | content check: the re-send differed from the tap's table only at the remapped keycode (gate false) |
| 470 | `tap-selftest-v3.yaml` | diagnostic: the server's row was XKB's four-column core view of the same mapping (gate false) |
| 471 | `tap-selftest-v4.yaml` | rows compared under the core protocol's rules: see the evidence README |
| 482-484 | `inputs-validation-v1/v2.yaml` | HMP input into the probe, guard and marker, and no-input canary read-back: 76 of 76 and 16 of 16 (inputs addendum, section 3) |
| 486-622 | `dev-*.yaml` | development at seed 42 (never evidence): L0-fixed, H-OSW-fixed, H-GA, the canary, 8 concurrent VMs, and the 44 mutants on their predicted kill cells |

Summaries: `program/evidence/2026-10-07/q2-action-path-stage0b/` (development:
`development-runs.json` and the README's development section).

## Isolation facts measured (jobs 369, 372, 374)

* `none-netns` (default): the VM container has no Docker network and no
  address on `docker0`; the image's NAT uses loopback as its uplink
  (`VM_NET_DEV=lo`), so the guest server (NAT address, port 5000) and the
  QEMU monitor (loopback port 7100) are reachable only from inside that
  namespace. The guest has no egress, so the suite is web-free by construction.
* `bridge-unpublished` (the D13 fallback): nothing is published, yet a
  separate container on the default bridge reached the guest's `/platform`
  through the image's DNAT (HTTP 200, job 372). This is the exposure D13
  records; the fallback is not used.
* No container saw `/dev/nvidia*`; the runner ran with no capabilities,
  `NoNewPrivs=1` and seccomp on.

## NOTICE

This directory is an **independent reimplementation**. Its authors read the
sources below; no code or text was copied from any repository without a
licence.

* **cua-speedrun** (no licence) and **sandweave** (no project licence): not
  vendored. From sandweave@99ba1abe we use only the 100 public entry IDs, their
  order and the group sizes, which are facts. Every action, coordinate, string
  and expectation in `catalog.yaml` was written here. Results from this suite
  are never presented as reproducing the paper's 83/11 or 94/94.
* **KernelGYM, KernelBench-M, Dr. Kernel**: not used by this item.
* **gym-anything** (MIT, Copyright (c) 2026 cmu-l3) at bf965cde0 and
  aae6f7607: read for the harness vocabulary and documented deviations; its two
  parsers are vendored as line ranges with the MIT notice (see "Vendored
  parsers" below). The L0-fixed executor does not vendor its
  `_KEYBOARD_XLIB_PREAMBLE`.
* **OSWorld** (Apache-2.0, no NOTICE file) at b138d348 and bfd62bdc: read for
  the provider, controller, guest-server API and the Qwen3.5 agent's prompt;
  the clients here are written from the observed HTTP behaviour. The Qwen3.5
  agent's parser is vendored, and its patched H-OSW-fixed copy keeps the
  header and marks every change under section 4(b) (see "Vendored parsers"
  below); `vm/desktop.py` copies `PYAUTOGUI_PKGS_PREFIX`.
* **QEMU 9.1.0** (GPLv2) and OVMF run inside the pinned image; nothing is
  redistributed.
* **xlangai/ubuntu_osworld** qcow2: run only, never republished; it bundles
  third-party software (Ubuntu, Chrome, VS Code) under their own terms.
* **python-xlib** (LGPL-2.1+) and **pynput** (LGPL-3.0) are used inside the
  guest as installed there; not vendored. The first version of
  `vm/guest/xrecord_tap.py` followed the structure of python-xlib's example
  `examples/record_demo.py` (LGPL-2.1+, Copyright (C) 2006 Alex Badea): two
  display connections, the same RECORD context ranges and an
  `rq.EventField` parsing loop. That pattern is credited here. The current
  tap was rewritten from the X11 core protocol encoding, the RECORD
  extension specification and python-xlib's `Xlib.ext.record` API: it decodes
  events and `ChangeKeyboardMapping` requests with `struct`, keeps its own
  keymap, and copies no example code. The RECORD calls themselves
  (`record_create_context`, `record_enable_context`, `record_disable_context`,
  `record_free_context`) are the library's API.
* **xorgproto 2024.1** `include/X11/keysymdef.h` (MIT/X11: Copyright 1987,
  1994, 1998 The Open Group; Copyright 1987 Digital Equipment Corporation):
  the keysym names and values in `action_path/keysyms.json` are derived from
  it, and the full permission notice is reproduced in that file.
* **PyAutoGUI 0.9.54** (BSD-3-Clause): read for the L0-raw prediction; the
  key and button names in `action_path/l0_raw.py` are PyAutoGUI's public API
  names, and `action_path/keynames.py` lists its `keyboardMapping` names as
  data; no code is copied.
* **Vendored parsers** (`action_path/upstream/`): `osworld_bfd62bdc.py` holds
  line ranges of OSWorld `bfd62bdc` `mm_agents/qwen35vl_agent.py` (Apache-2.0,
  notice in the file, extraction marked as a change under section 4(b));
  `osworld_bfd62bdc_fixed.py` is a modified copy of that extract with every
  change marked; `gym_anything_aae6f7607.py` and `gym_anything_bf965cde0.py`
  hold line ranges of gym-anything `agents/agents/qwen35vl.py` and
  `agents/shared/qwen_computer_use.py` (MIT, Copyright (c) 2026 cmu-l3, notice
  in each file). `vendor.py` writes them from the pinned upstream files and
  `PROVENANCE.json` records every range's SHA-256. `desktop.py` copies
  OSWorld's `PYAUTOGUI_PKGS_PREFIX` string (Apache-2.0).
* **Qwen3.5-9B chat template** (`action_path/qwen35_chat_template.jinja`,
  Apache-2.0, `Qwen/Qwen3.5-9B` at `c202236`, 7,756 B, SHA-256
  `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`): copied
  unchanged so a test can render the corpus through it.
* The L0-fixed executor's spare-keycode typing follows the idea of
  gym-anything's `_KEYBOARD_XLIB_PREAMBLE` (MIT); its code and its
  `_NAME` key table (data, in `keynames.py`) are not copied otherwise.

## External sources

Git sources are pinned by commit; the files that were read are listed with
their size and SHA-256 (computed from `git show REV:PATH` on the H100 host).

| Source | Revision | Files read (size, SHA-256) | Licence | Use |
|---|---|---|---|---|
| [arXiv 2609.40284](https://arxiv.org/abs/2609.40284) (cua-speedrun paper) | v1 | paper | arXiv | App. I.1-I.3, Tables 20 and 21 |
| [cua-speedrun](https://github.com/cua-speedrun/cua-speedrun) | be17c72c5efbb145d06f86028336fdf2743a3d98 | `README.md` (6,495 B, `64a8d21987d04c3f97ca0423c4ff989e71bae9867ac9a7c85cdef16db07ce17c`); `agents/qwen35/agent.py` (31,910 B, `287ce1244a787e71aa89bc9c0efd6bf24c2779b6918be7e7b8ae932bcf9c1bfc`) | none (no licence file at the root) | read only; nothing vendored |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | b138d348256078fa634fc3b73567a7337c793e6b | `desktop_env/controllers/python.py` (28,331 B, `20b00e73704720513aa03b19f33e69280c9e14c92861608f234efc11fed35641`); `desktop_env/desktop_env.py` (24,585 B, `ff73a546074d4cf3b13259f7261a82af5c3f6942bde27101aa74e58da70d84c1`) | Apache-2.0 | runtime reference, L0-raw path |
| [OSWorld `dev_djlu/qwen35vl_agent`](https://github.com/xlang-ai/OSWorld/tree/dev_djlu/qwen35vl_agent) | bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06 | `mm_agents/qwen35vl_agent.py` (28,770 B, `1f39be92cf5461d9671ab9307a69c05691abf0226aa6b53d2af332003a5096fe`) | Apache-2.0 | H-OSW vocabulary and scaling |
| [gym-anything](https://github.com/cmu-l3/gym-anything) | aae6f7607e0f3d9d6306e1fefbad92bda99ca99a | `agents/agents/qwen35vl.py` (32,925 B, `93666f2751d99dfee0034700f65385ca2db1544e3d9a0d194807050d2edea1a5`); `src/gym_anything/runtime/runners/qemu_apptainer.py` (202,812 B, `c22be6bb16f349c40a3b2a549fdfa70208236b647f6b690d0dd418e78b776302`) | MIT | H-GA vocabulary, scroll limit, keyboard remap technique |
| gym-anything | bf965cde02f498bf7d162e6e44da984cff289912 | `agents/agents/qwen35vl.py` (18,236 B, `824ef657345f317bf197b7f6470d82ddbf1779bd556a9a29cd184c5641fa43d8`); `agents/shared/qwen_computer_use.py` (17,087 B, `b74793ea329407d0d27fb536c3db0502f5f0dfeb34f279691ca5f836f0c7b815`) | MIT | H-GA-buggy control |
| [sandweave](https://github.com/Pranjal2041/sandweave) | 99ba1abe442209d99c161e05a50595cea00a3482 | `notes/cua-harness-evidence/fixes/full-cpu/report.json` (19,559 B, `4b579842e87d0ae3b3a957ca30ed78c819762f3ca02fd3021a04c94253d36443`) | none | entry IDs and order (facts) |
| [happysixd/osworld-docker](https://hub.docker.com/r/happysixd/osworld-docker) | sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9 (image ID sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4) | image, 84,258,814 B compressed | none stated (base qemus/qemu MIT; QEMU GPLv2) | VM runtime, run only |
| QEMU (inside that image) | 9.1.0, Debian package 1:9.1.0+ds-8 (HMP `info version`, job 393) | binary in the image | GPL-2.0 | the R-dev reference input path (HMP `sendkey`, `mouse_button`); run only |
| [xlangai/ubuntu_osworld](https://huggingface.co/datasets/xlangai/ubuntu_osworld) `Ubuntu.qcow2.zip` | a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133 | 12,273,896,463 B, `b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712` | apache-2.0 tag (bundled software under own terms) | guest disk, run only |
| `Ubuntu.qcow2` (unzipped member, read-only on the host) | same | 24,460,197,888 B, `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313` | as above | `/System.qcow2` |
| python-xlib (in the guest) | 0.33 as imported by the guest's `python3` (boot facts, job 374); Debian `python3-xlib` 0.29-1 is also installed | `examples/record_demo.py` of the Debian package (3,932 B, `399e02011000b5c5b8878bad207d6262df6312d2fb6e288059b7781f68a5b5ec`) | LGPL-2.1+ | guest library for the tap and fixtures; the example is credited in the NOTICE |
| [xorgproto](https://gitlab.freedesktop.org/xorg/proto/xorgproto) | 2024.1 (conda `xorg-xorgproto` build h5eee18b_1) | `include/X11/keysymdef.h` (186,634 B, `4ba0724695c817a08b4ea3a79c5e8a52e0798cc8d5906281b10f89dc6225208d`) | MIT/X11 | keysym table (`keysyms.json`) |
| [ubuntu:22.04](https://hub.docker.com/_/ubuntu) | sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401 | base image | Ubuntu image terms | runner base |
| [PyAutoGUI 0.9.54](https://pypi.org/project/PyAutoGUI/0.9.54/) sdist | 0.9.54 | sdist 61,236 B, `dd1d29e8fd118941cb193f74df57e5c6ff8e9253b99c7b04f39cfc69f3ae04b2` | BSD-3-Clause | read for the L0-raw translator and prediction |

The runner image built from `infra/q2-vm-runner/Dockerfile` is local image
`sha256:ac2b5815bcc2ed193116aa2d4bdee773b5a457c545453a6c91956768634a6002`
(Dockerfile SHA-256 18abffa24d55eb4fe8a1c5e819d9dabcabb35cca0d8c22690dfbd49c9a8a0cb0).
A rebuild is not bit-reproducible (apt resolves the archive of the build
day), so the image itself is kept: `docker save` tarball
`/home/kevin/cotcodec-runs/stage0/q2-action-path/images/cotcodec-q2-vmrunner-v1.tar`
(111,907,328 B, SHA-256
ec434c04f03b8534e7ef61e1e88a6721b687ad8c3959e24a1dfea10d76d427b3, read-only),
restored with `docker load -i`. `infra/q2-vm-runner/image-lock.json` records
it with all 114 installed package versions (python3.10 3.10.12-1~22.04.18).
