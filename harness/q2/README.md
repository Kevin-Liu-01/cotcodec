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
| `vm/guest/*.py` | Scripts shipped to the guest as base64 argv: facts, reset sentinel, XRecord tap |
| `action_path/ir.py` | Canonical action IR (Table 21 vocabulary plus explicit holds) |
| `action_path/catalog.yaml` | The 100-entry catalog (draft; key entries await R-dev references) |
| `action_path/catalog.py` | Catalog loader, validator and hash |
| `action_path/build_catalog.py` | Author tool that writes `catalog.yaml`; a test checks it reproduces the file byte for byte |
| `action_path/rdev.py`, `rdev_plan.json` | R-dev reference: HMP chords per key entry, projection and stability rules |
| `action_path/rdev_reference.json` | Stable R-dev streams from the reference capture (copied into `catalog.yaml`) |
| `action_path/expressible_entries.json` | Per Stage-1 harness: expressible entries (H-OSW 85, H-GA 80) and reasons for the rest |
| `action_path/vocab.py` | Stage-1 harness vocabularies and the gating set G |
| `action_path/gating_set.json` | G (86 entries) and the 14 non-gating entries with reasons |
| `action_path/mutation_operators.yaml` | 28 suite mutation operators and the equivalence rule |
| `action_path/l0_raw_prediction.yaml` | Predicted L0-raw failing set, written from code reading |
| `../../infra/slurm/host-single-node/vm-campaign.sbatch` | CPU-only Slurm entry point for VM work |
| `../../infra/q2-vm-runner/Dockerfile` | GPU-less runner image (stdlib Python only) |
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
  aae6f7607: read for the harness vocabulary and documented deviations; nothing
  vendored in this change. If the L0-fixed executor later vendors the
  `_KEYBOARD_XLIB_PREAMBLE`, it will carry the MIT notice.
* **OSWorld** (Apache-2.0, no NOTICE file) at b138d348 and bfd62bdc: read for
  the provider, controller, guest-server API and the Qwen3.5 agent's prompt;
  the clients here are written from the observed HTTP behaviour. A patched
  harness copy, when added, will keep the header and mark changes (§4).
* **QEMU 9.1.0** (GPLv2) and OVMF run inside the pinned image; nothing is
  redistributed.
* **xlangai/ubuntu_osworld** qcow2: run only, never republished; it bundles
  third-party software (Ubuntu, Chrome, VS Code) under their own terms.
* **python-xlib** (LGPL-2.1+) and **pynput** (LGPL-3.0) are used inside the
  guest as installed there; not vendored.

## External sources

| Source | Revision | Size | SHA-256 | Licence | Use |
|---|---|---:|---|---|---|
| [arXiv 2609.40284](https://arxiv.org/abs/2609.40284) (cua-speedrun paper) | v1 | n/a | n/a | arXiv | App. I.1-I.3, Table 21 |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | b138d348256078fa634fc3b73567a7337c793e6b | n/a | n/a (git) | Apache-2.0 | runtime reference |
| [OSWorld `dev_djlu/qwen35vl_agent`](https://github.com/xlang-ai/OSWorld/tree/dev_djlu/qwen35vl_agent) | bfd62bdc5a3319809a236dc90ddbbaf3cb4b7e06 | n/a | n/a (git) | Apache-2.0 | H-OSW vocabulary |
| [gym-anything](https://github.com/cmu-l3/gym-anything) | aae6f7607e0f3d9d6306e1fefbad92bda99ca99a; bf965cde02f498bf7d162e6e44da984cff289912 | n/a | n/a (git) | MIT | H-GA vocabulary, controls |
| [sandweave](https://github.com/Pranjal2041/sandweave) | 99ba1abe442209d99c161e05a50595cea00a3482 | n/a | n/a (git) | none | entry IDs (facts) |
| [happysixd/osworld-docker](https://hub.docker.com/r/happysixd/osworld-docker) | sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9 (image ID sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4) | 84,258,814 B compressed | digest as given | none stated (base qemus/qemu MIT; QEMU GPLv2) | VM runtime, run only |
| [xlangai/ubuntu_osworld](https://huggingface.co/datasets/xlangai/ubuntu_osworld) `Ubuntu.qcow2.zip` | a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133 | 12,273,896,463 B | b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712 | apache-2.0 tag (bundled software under own terms) | guest disk, run only |
| `Ubuntu.qcow2` (unzipped member, read-only on the host) | same | 24,460,197,888 B | 6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313 | as above | `/System.qcow2` |
| [ubuntu:22.04](https://hub.docker.com/_/ubuntu) | sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401 | n/a | digest as given | Ubuntu image terms | runner base |
| [PyAutoGUI 0.9.54](https://pypi.org/project/PyAutoGUI/0.9.54/) sdist | 0.9.54 | 61,236 B | dd1d29e8fd118941cb193f74df57e5c6ff8e9253b99c7b04f39cfc69f3ae04b2 | BSD-3-Clause | read for the L0-raw prediction |

The runner image built from `infra/q2-vm-runner/Dockerfile` is local image
`sha256:ac2b5815bcc2ed193116aa2d4bdee773b5a457c545453a6c91956768634a6002`
(Dockerfile SHA-256 18abffa24d55eb4fe8a1c5e819d9dabcabb35cca0d8c22690dfbd49c9a8a0cb0).
