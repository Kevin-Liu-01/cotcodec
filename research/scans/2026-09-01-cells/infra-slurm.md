# infra-slurm cell — publication-grade single-node 8xH100 Slurm/Pyxis/Docker lane (sweep 2026-09-01)

Scope: fal-h100-01 (8x H100 80GB, Ubuntu, unified cgroup v2, Docker 28, Slurm 21.08.5 from the
Ubuntu jammy package, no Pyxis/Enroot). Goal: the exact upgrade path, version pins, commands, and
known failure modes for a receipted publication lane (digest-pinned OCI image, SIGUSR1 checkpoint +
fresh-job resume, vLLM inside Slurm). All claims below were read from the cited primary page today
unless marked **[not verified in official docs]** or **[inference]**. "First-party" = vendor doc,
README, release note, or issue; nothing in this cell is peer-reviewed except where stated.

Honesty header: No direct prior art search is meaningful for an infra cell; the question is what is
*occupied* (already solved upstream — just adopt) versus what Kevin must *prove on his own node*.
Coverage limits are listed at the end and are material (WebSearch quota exhausted at 14 queries;
arXiv API/search and Semantic Scholar returned HTTP 429 all session; SchedMD Bugzilla is login-only;
Princeton RC is Cloudflare-gated and its "checkpointing" KB URL is a 404).

---

## 0. Executive summary (what to do, in order)

1. **Slurm 21.08.5 cannot enforce cgroup v2 at all.** cgroup/v2 support was added in Slurm 22.05
   (RELEASE_NOTES: "Added support for Cgroup Version 2"), and the jammy `slurm-wlm-basic-plugins`
   file list ships only `cgroup_v1.so`. Everything on this host today is env-var (soft) GPU
   isolation. This matches Kevin's own `infra/slurm/host-single-node/README.md`.
2. **Target pin: Slurm 25.11.7 (tag `slurm-25-11-7-1`, 2026-07-14; SchedMD support to May 2027)**
   built from the SchedMD tarball with the in-tree Debian packaging (`debuild -b -uc -us`), with
   `linux-libc-dev` (kernel headers >= 5.7 for `include/linux/bpf.h`), `libdbus-1-dev`
   (>= 1.11.16), and NVML headers present at configure time so `cgroup_v2` and `gpu_nvml` build.
   26.05.3 (2026-08-13) is the current major but changes cgroup/v2 path keys to SLUID (26.05.0rc1;
   job-id path option restored in 26.05.2) — pick it only if nothing parses cgroup paths by job id.
3. **Pyxis v0.24.0 (2026-05-12) + Enroot v4.2.1 (2026-06-09)**, Pyxis compiled against the *exact*
   deployed Slurm headers (`slurm-smd-dev`), or slurmd refuses it with "Incompatible plugin version".
4. `cgroup.conf`: `CgroupPlugin=cgroup/v2`, `ConstrainDevices=yes`, `ConstrainCores=yes`,
   `ConstrainRAMSpace=yes`; `slurm.conf`: `ProctrackType=proctrack/cgroup`,
   `TaskPlugin=task/cgroup,task/affinity`, `JobAcctGatherType=jobacct_gather/cgroup`;
   `gres.conf`: `AutoDetect=nvml` (NVML plugin) with optional `File=/dev/nvidia[0-7]` sanity pins.
5. Validate with `slurmd -G`, `slurmd -C`, `srun --gres=gpu:1 nvidia-smi -L` (exactly one GPU),
   `bpftool cgroup list <job cgroup> effective` (a `Slurm_Cgroup_v2` device program attached),
   and `journalctl -k | grep 'BPF prog-id'` (LOAD/UNLOAD audit lines).
6. Digest-pin everything: `srun --container-image=REGISTRY#IMAGE@sha256:<64hex>` is supported by
   Pyxis/Enroot (Enroot's URI parser accepts `[USER@]REGISTRY/IMAGE[:TAG]@DIGEST`; Enroot 4.2.0
   records `# enroot-provenance: <uri>` in the image's `/etc/rc`). SBOM with `syft` v1.51.1 or
   BuildKit `--sbom=true` (SPDX in-toto attestation, Syft scanner).
7. Checkpoint/resume: `--signal=B:USR1@300 --requeue --open-mode=append`; **set a flag in the
   handler and checkpoint at the next step/episode boundary** (Lightning #21406: checkpointing
   inside the SIGUSR1 handler intermittently never completes); `SLURM_RESTART_COUNT` marks a
   requeue; drill with `scancel --signal=USR1 --batch <jobid>` and `scontrol requeue <jobid>`.
   Keep `ENROOT_DATA_PATH` on local disk (Pyxis #161: requeue fails when it is on a shared FS).
8. vLLM v0.28.0 (2026-08-26) inside one Slurm step: `--ntasks=1`, `vllm serve ... --tensor-parallel-size 8`
   (mp executor is the single-node default); no official vLLM Slurm doc exists (docs tree checked);
   institutional templates (LBL, VT ARC) all use one task and attach with
   `srun --jobid=<id> --overlap --pty bash`.

---

## 1. Findings (title | URL | date | claim | occupies | relevance)

### A. Slurm cgroup v2 device constraints and the upgrade path

**F1. cgroup/v2 support landed in Slurm 22.05; 21.08 has none** — first-party (SchedMD RELEASE_NOTES)
- URL: https://github.com/SchedMD/slurm/blob/slurm-22-05-11-1/RELEASE_NOTES (line: "Added support for Cgroup Version 2"; also "Remove cgroup_allowed_devices_file.conf ... Denying specific devices must be done through gres.conf")
- Date: 22.05 series (2022); tag `slurm-22-05-11-1`.
- Claim: cgroup v2 is a 22.05+ feature. Corroborated by the Ubuntu package file lists: jammy `slurm-wlm-basic-plugins` (21.08.5-2ubuntu1) contains `cgroup_v1.so` but no `cgroup_v2.so`; noble (23.11.4-1.2ubuntu5) has both; resolute (25.11.2-1ubuntu2) has both plus `gpu_nvidia.so`; **none ships `gpu_nvml.so`**.
  https://packages.ubuntu.com/jammy/amd64/slurm-wlm-basic-plugins/filelist ,
  https://packages.ubuntu.com/noble/amd64/slurm-wlm-basic-plugins/filelist ,
  https://packages.ubuntu.com/resolute/amd64/slurm-wlm-basic-plugins/filelist ,
  https://packages.ubuntu.com/jammy/slurm-wlm , https://packages.ubuntu.com/noble/slurm-wlm , https://packages.ubuntu.com/resolute/slurm-wlm
- Occupies: scheduler-side device isolation on unified cgroup v2.
- Relevance: kill-shot for the current host config as a publication lane; explains why Kevin's bootstrap uses `proctrack/linuxproc` + `task/affinity`. Also means: even Ubuntu 26.04's packaged 25.11.2 lacks NVML autodetect (only `AutoDetect=nvidia`), so building from the SchedMD tarball is required for `AutoDetect=nvml`/GPU accounting.

**F2. Slurm cgroup/v2 uses an eBPF device program per job/step/task; only gres.conf devices are managed; build needs kernel headers >= 5.7 and dbus >= 1.11.16** — first-party (SchedMD docs, page marked "Version 26.05")
- URL: https://slurm.schedmd.com/cgroup_v2.html
- Date: page current for 26.05 (fetched 2026-09-01).
- Claim: "In Control Group v2, the devices controller interfaces has been removed. Instead ... create a bpf program of type BPF_PROG_TYPE_CGROUP_DEVICE and attach it to the desired cgroup. This program is created by slurmstepd dynamically ... The only devices that are managed are the ones described in the gres.conf file." Load/unload appears in the kernel audit log (`audit: BPF prog-id=564 op=LOAD`). Requirements table: eBPF `include/linux/bpf.h` from `kernel-headers (>= 5.7)` via `--with-bpf=`; dBus `dbus-devel (>= 1.11.16)`. slurmd must run in a systemd unit with `Delegate=yes`; `IgnoreSystemd`/`IgnoreSystemdOnFailure`/`EnableControllers` are for dev/testing or old systemd (< 244, RHEL8). Conversion: remove `CgroupAutomount=`, `CgroupMountpoint=`, set `CgroupPlugin=autodetect`; a node must be booted with one cgroup version (no hybrid). Limitation: cgroup/v2 reports 0 for VMem metrics (AveVMSize etc.).
- Occupies: mechanism for hard GPU device isolation.
- Relevance: tells the admin exactly which dev packages must be present at `configure` time; explains why `ConstrainDevices` is meaningless without a gres.conf device list.

**F3. cgroup.conf / slurm.conf knobs for the publication lane** — first-party (man pages, generated 2026-08-13)
- URL: https://slurm.schedmd.com/cgroup.conf.html , https://slurm.schedmd.com/slurm.conf.html
- Date: cgroup.conf man2html timestamp "August 13, 2026".
- Claim: `CgroupPlugin=<cgroup/v1|cgroup/v2|autodetect|disabled>`; `ConstrainDevices=<yes|no>` "constrain the job's allowed devices based on GRES allocated resources ... default no"; `SignalChildrenProcesses=<yes|no>` (default no) sends cancel/suspend signals to all children rather than only the step's parent; slurm.conf: "It is recommended to stack task/cgroup,task/affinity together when configuring TaskPlugin, and setting ConstrainCores=yes"; `KillWait` = seconds between SIGTERM and SIGKILL at time limit (default 30); `JobRequeue=1` default requeue eligibility; `RequeueExit=<codes>` auto-requeue on exit codes.
- Occupies: configuration surface.
- Relevance: concrete config block below (section 2).

**F4. Upgrade compatibility windows and stepwise rule** — first-party (SchedMD Upgrade Guide)
- URL: https://slurm.schedmd.com/upgrades.html
- Date: current page (2026-09-01); 6-month cycle since 24.05.
- Claim: "Slurm has long supported in-place upgrades from the previous two major releases. ... Slurm 24.11 introduced compatibility with the previous three major releases." Table: 23.11 <- 23.02, 22.05 (EOL May 2025); 24.05 <- 23.11, 23.02 (EOL Nov 2025); 24.11 <- 24.05, 23.11, 23.02 (EOL May 2026); 25.05 <- 24.11, 24.05, 23.11 (EOL Nov 2026); 25.11 <- 25.05, 24.11, 24.05 (EOL May 2027); 26.05 <- 25.11, 25.05, 24.11 (EOL Nov 2028). "Upgrades from incompatible versions will fail immediately upon startup. It is required to perform upgrades from incompatible prior versions in steps ... Compatibility requirements apply to running jobs and upgrading outside of their compatibility window will result in the jobs being killed and job accounting being lost." Order: slurmdbd, slurmctld, slurmd, commands; back up `StateSaveLocation` first. EPEL/distro Slurm packages are "not provided by or supported by SchedMD".
- Occupies: upgrade procedure.
- Relevance: from 21.08 an in-place path needs >= 3 hops (21.08 -> 23.02 -> 24.11 -> 25.11) **[inference from the pre-24.11 "previous two major releases" rule; the 23.02 row is no longer printed on the page]**. Kevin's node has `AccountingStorageType=none`, `jobcomp/filetxt`, and no jobs worth preserving, so a **clean reinstall** of 25.11.7 with a fresh `StateSaveLocation` avoids the hops **[inference; the guide governs upgrades, not fresh installs]**.

**F5. Slurm release pins and infra-relevant release notes** — first-party (GitHub tags + RELEASE_NOTES.md)
- URLs: https://github.com/SchedMD/slurm/tags ; tarballs verified HTTP 200: https://download.schedmd.com/slurm/slurm-25.11.7.tar.bz2 , https://download.schedmd.com/slurm/slurm-26.05.3.tar.bz2 , https://download.schedmd.com/slurm/slurm-24.11.7.tar.bz2 ; notes: https://github.com/SchedMD/slurm/blob/slurm-25-05-8-1/RELEASE_NOTES.md , https://github.com/SchedMD/slurm/blob/slurm-25-11-7-1/RELEASE_NOTES.md , https://github.com/SchedMD/slurm/blob/slurm-26-05-3-1/RELEASE_NOTES.md , https://slurm.schedmd.com/release_notes.html
- Dates (tag object dates): `slurm-26-05-3-1` 2026-08-13; `slurm-25-11-7-1` 2026-07-14; `slurm-25-05-8-1` 2026-05-14; `slurm-24-11-7-1` 2025-11-11; `slurm-23-11-11-1` 2025-05-07.
- Claims: 25.05 "Marked cgroup/v1 support as deprecated"; `srun --wait-for-children` (cgroup/v2 only). 25.11: "Added support to launching the slurmd in a cgroup slice other than system.slice"; rpm `--with cgroupv2` build option; `NamespaceType` replaces `JobContainerType`. 26.05: `AutoDetect=full` in gres.conf; "cgroup/v2 directory structures are now keyed off of SLUID and not the JobId"; dynamic memory resizing; Prometheus GPU allocation stats.
- Occupies: version selection.
- Relevance: choose 25.11.7 for path stability; 26.05.x if SLUID keying is acceptable.

**F6. CHANGELOG negatives/fixes that touch device constraints (exact maintenance versions)** — first-party
- URLs: https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-25.05.md , https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-25.11.md , https://github.com/SchedMD/slurm/blob/master/CHANGELOG/slurm-26.05.md
- Claims: 25.05.0rc1: "Ensure that a device constrain has been successfully applied to the job/step cgroup, so jobs do not run unconstrained after a failure" (i.e. before 25.05, a failed eBPF attach could silently leave a job unconstrained). 25.05.1: fix slurmstepd killing itself with proctrack/cgroup + cgroup/v2 during core dumps. 25.11.5: "Fix slurmd reconfigure failure with cgroup/v2"; "Fix Insufficient Size error in NVML library call for long gpu names"; BPF-token compile fix for glibc >= 2.36. 25.11.3: `namespace/linux` `disable_bpf_token`. 26.05.0rc1: gpu/nvml "Fix bug that prevented clock frequencies being reset on all GPUs at job completion when cgroups is constraining devices and there are multiple GPUs on the node"; "Add option to use UUID strings with CUDA_VISIBLE_DEVICES".
- Occupies: known-bug landscape for ConstrainDevices.
- Relevance: pins must be >= 25.05 to get fail-closed device constraints; >= 25.11.5 for reconfigure stability; the 26.05 UUID option removes the index-vs-minor ambiguity discussed in F9.

**F7. SchedMD Debian packaging (>= 23.11) and package names** — first-party
- URLs: https://slurm.schedmd.com/quickstart_admin.html ; https://github.com/SchedMD/slurm/blob/slurm-25-11-7-1/debian/control
- Claim: "Beginning with Slurm 23.11.0, Slurm includes the files required to build Debian packages. These packages conflict with the packages shipped with Debian based distributions"; commands `apt-get install build-essential fakeroot devscripts equivs`, `mk-build-deps -i debian/control`, `debuild -b -uc -us`; install with `apt` not `dpkg`. Packages at 25.11.7: `slurm-smd`, `slurm-smd-client`, `slurm-smd-dev`, `slurm-smd-slurmctld`, `slurm-smd-slurmd`, `slurm-smd-slurmdbd`, `slurm-smd-slurmrestd`, `slurm-smd-sackd`, `slurm-smd-libpam-slurm-adopt`, .... Build-time table: `AutoDetect=nvml` requires `libnvidia-ml` ("AutoDetect=nvidia, added in 24.11, does not have any prerequisites"); `auth/slurm` is an alternative to MUNGE ("MUNGE is currently the default and recommended option").
- Occupies: packaging.
- Relevance: exact build commands in section 2; Pyxis must be built against `slurm-smd-dev` from the same build.

### B. GRES / NVML validation and CUDA_VISIBLE_DEVICES vs cgroup

**F8. NVML autodetect semantics and validation commands** — first-party
- URLs: https://slurm.schedmd.com/gres.html , https://slurm.schedmd.com/gres.conf.html , https://slurm.schedmd.com/slurmd.html , https://github.com/SchedMD/slurm/blob/slurm-24-11-7-1/RELEASE_NOTES
- Claims: `AutoDetect=nvml` needs the library "installed on the node and found during Slurm configuration"; `AutoDetect=nvidia` (24.11) needs no NVML "but doesn't detect MIGs or NVlinks"; the `Gres=` line in slurm.conf is still required; when `File`, `Cores`, or `Links` are given alongside AutoDetect they are sanity checks and "If there is a mismatch, then the node's state is set to invalid and the node is drained"; `Type` must match or be a substring of the detected name (`Found gpu:geforce_rtx_2060:1 with Autodetect=nvml`); gpumem/gpuutil accounting only with nvml (or rsmi); `--gpu-freq` and energy accounting hold the library open (set `JobAcctGatherParams=DisableGPUAcct` if jobs share GPUs); `slurmd -G` "Print Generic RESource (GRES) configuration (based upon slurm.conf GRES merged with gres.conf contents for this node)"; `slurmd -C` prints hardware config and (24.11+) autodetected GPUs; `_check_core_range_matches_sock` errors on dual-socket boxes need `l3cache_as_socket` or explicit Cores.
- Occupies: GRES validation.
- Relevance: the 208-CPU dual-socket node is exactly the case the doc warns about; validation recipe in section 2.

**F9. CUDA_VISIBLE_DEVICES under cgroup constraint is renumbered from 0; device minors vs NVML order are nondeterministic** — first-party
- URL: https://slurm.schedmd.com/gres.html (GPU Management section)
- Claims: CUDA_VISIBLE_DEVICES is set per job step; "if a job is allocated the device /dev/nvidia1, then CUDA_VISIBLE_DEVICES will be set to a value of '1' in the Prolog and Epilog while the job's value ... will be set to a value of '0'" when cgroups constrain devices; NVML numbers by PCI bus ID so `CUDA_DEVICE_ORDER=PCI_BUS_ID` is needed for CUDA to agree; "GPU device files (e.g. /dev/nvidia1) are based on the Linux minor number assignment, while NVML's device numbers are assigned via PCI bus ID ... Mapping between these two is nondeterministic and system dependent ... an after-bootup check is required". gres.conf `Flags=nvidia_gpu_env` controls whether CUDA_VISIBLE_DEVICES is exported (implicit default).
- Occupies: env-var GPU visibility semantics.
- Relevance: Kevin's discovery lane maps `CUDA_VISIBLE_DEVICES`/`SLURM_JOB_GPUS` into `docker run --gpus device=...`; with a hand-written `File=/dev/nvidia0..7` gres.conf that mapping is only correct if minor order == PCI order (needs the post-boot check; Kevin's `configure-as-root.sh` only checks the device nodes exist). Under ConstrainDevices the renumbering to 0..k-1 changes what the sbatch must pass to Docker/Enroot.

**F10. Soft vs hard isolation trade-offs (community corroboration)** — secondary (mailing list / ask.CI)
- URLs: https://ask.cyberinfrastructure.org/t/slurm-gpu-cgroups-constraindevices/1745 ; https://groups.google.com/g/slurm-users/c/nFsu33ep9eY ; https://groups.google.com/g/slurm-users/c/Fv2cgq80GmU
- Claim (as summarized in search results; threads not individually opened): without ConstrainDevices users still see all GPUs in nvidia-smi and can unset CUDA_VISIBLE_DEVICES; with it each job sees its GPU as device 0. **[secondary; not verified in official docs, consistent with F9]**
- Occupies: rationale for hard isolation.
- Relevance: publication contract wants hard isolation so "visible devices" in the receipt is a kernel fact, not an env var.

**F11. eBPF device programs need privileges; failure in unprivileged containers** — first-party mailing-list report (negative result)
- URL: https://groups.google.com/g/slurm-users/c/96Pp2b6stA8 (MIG and eBPF issues, Slurm 24.11.6, 2025-11-26..28)
- Claim: slurmd inside an unprivileged LXD container: `load_ebpf_prog: BPF load error (Operation not permitted). Please check your system limits (MEMLOCK)`; `bpftool prog show` also EPERM; no confirmed fix (suggestions: cgroup v1, `lxc.cgroup2.devices.allow`, LXD BPF delegation).
- Occupies: deployment constraint.
- Relevance: keep slurmd on bare metal (as Kevin plans); do not run slurmd in a container/K8s (Slinky) for this lane.

**F12. Inspecting the attached device program** — first-party mailing-list (2024-01-07)
- URL: https://lists.schedmd.com/mailman3/hyperkitty/list/slurm-users@lists.schedmd.com/thread/UX6GRHJDLVHORVA6H6V37HPAKLCDQVLQ/
- Claim: `bpftool cgroup list /sys/fs/cgroup/system.slice/slurmstepd.scope/job_<id>` shows nothing without `effective`; with `effective` it lists program `Slurm_Cgroup_v2`; `bpftool prog dump xlated id <id>` shows the allow/deny bytecode; no map-based dump exists (open question, 1 reply). Note the path form changes in 26.05 (SLUID keys, F5).
- Occupies: validation tooling.
- Relevance: the only documented way to prove the constraint is attached; see gap G3.

### C. Pyxis / Enroot against an exact Slurm release; digest-pinned images

**F13. Pyxis must be compiled against the exact deployed Slurm; install recipe** — first-party
- URLs: https://github.com/NVIDIA/pyxis/blob/main/README.md ; https://github.com/NVIDIA/pyxis/wiki/Installation (wiki last commit 2026-04-29)
- Claims: "Since Slurm 21.08, pyxis must be compiled against the release of Slurm that is going to be deployed on the cluster. Compiling against spank.h from a different Slurm release will cause Slurm to prevent pyxis from loading with error Incompatible plugin version"; requires enroot >= 3.1.0 and Slurm >= 20.02; needs `libslurm-dev`; must be installed on login and compute nodes; `make orig && make deb && dpkg -i ../nvslurm-plugin-pyxis_*_amd64.deb`, then `ln -s /usr/share/pyxis/pyxis.conf /etc/slurm/plugstack.conf.d/pyxis.conf && systemctl restart slurmd`; verify with `srun --help | grep container-image` and `strace -e openat srun --help` showing `plugstack.conf`, `plugstack.conf.d/pyxis.conf`, `spank_pyxis.so`; RPM build not supported by the wiki ("recommended to install without packages"). plugstack defaults: `runtime_path=/run/pyxis execute_entrypoint=0 container_scope=global sbatch_support=1 use_enroot_load=0`; `container_scope=job` auto-cleans named containers in the epilog; `sbatch_support` exists "since it is tricky to get srun to work correctly inside a sbatch script running inside a container image".
- Occupies: container plugin build/install.
- Relevance: Kevin's `research.sbatch` already fails closed on `srun --help | grep -- '--container-image'`.

**F14. Pyxis releases 2026** — first-party
- URL: https://github.com/NVIDIA/pyxis/releases (v0.24.0 2026-05-12; v0.23.0 2026-02-18; v0.20.1 2026-02-12 backport; v0.22.0 2026-02-06; v0.21.0 2025-10-02)
- Claims: v0.24.0: "Add --container-unshare=net,ipc,uts for lightweight isolation", "Start squashfs images from importers with squashfuse", "Forward SIGTERM to child processes instead of ignoring it" (commit 26fa047, 2026-04-15: waitpid EINTR loops "were silently retrying on all interrupted signals, including SIGTERM from scancel"), "Validate source paths for bind mounts", fstab escaping. v0.23.0: robustness of epilog container cleanup. v0.22.0: direct squashfs start via squashfuse.
- Occupies: plugin feature set; signal handling inside Pyxis.
- Relevance: pin v0.24.0; note the SIGTERM fix is 2026 — SIGUSR1 forwarding through pyxis is not documented (gap G1).

**F15. Digest-pinned images with Pyxis/Enroot; provenance line** — first-party (wiki + source)
- URLs: https://github.com/NVIDIA/pyxis/wiki/Usage ("Image URI Formats": `IMAGE@sha256:DIGEST`, example `srun --container-image=ubuntu@sha256:d22e4fb3... hostname`; `REGISTRY#IMAGE:TAG`; `dockerd://`, `podman://`; local `.sqsh` paths; `--container-save=PATH` then reuse) ; https://github.com/NVIDIA/enroot/blob/master/src/docker.sh (`docker::_parse_uri`: `docker://[USER@]REGISTRY/IMAGE[:TAG]@DIGEST` and `...IMAGE@DIGEST`; "Ignore tag, use digest"; manifest list resolved by architecture; every layer verified by `sha256sum` against its digest, "Checksum mismatch" aborts) ; https://github.com/NVIDIA/enroot/commit/8b3a130 (2026-04-28, "Add simple provenance information to images": `/etc/rc` gets `# enroot-provenance: <uri>`) ; https://github.com/NVIDIA/enroot/blob/master/doc/cmd/import.md (digests cached under `$ENROOT_CACHE_PATH`)
- Occupies: immutable image references in the scheduler lane.
- Relevance: `COTCODEC_IMAGE=...@sha256:<64hex>` from `research.sbatch` maps directly onto `--container-image`. Import once to a `.sqsh`, `sha256sum` it, and reference the file for all runs; **[read from source, not executed here]**.

**F16. Enroot 4.2.x requirements and Ubuntu specifics** — first-party
- URLs: https://github.com/NVIDIA/enroot/releases (v4.2.1 2026-06-09: GNU parallel `--xapply`, coreutils 9.2->9.4 workaround; v4.2.0 2026-05-12: PID/IPC/UTS/net namespaces, sysfs isolation in netns, provenance, Docker Hub alias canonicalization, mixed media types) ; https://github.com/NVIDIA/enroot/blob/master/doc/requirements.md ; https://github.com/NVIDIA/enroot/blob/master/doc/installation.md
- Claims: kernel >= 3.10 with `CONFIG_USER_NS`, `CONFIG_SECCOMP_FILTER`, `CONFIG_OVERLAY_FS`; `/proc/sys/user/max_user_namespaces > 1`; Ubuntu: `/proc/sys/kernel/apparmor_restrict_unprivileged_userns` must be 0 "unless {datadir}/enroot/apparmor.profile is installed"; GPU: drivers >= 361.93, `libnvidia-container-tools >= 1.0`; deb install: `curl -fSsL -O https://github.com/NVIDIA/enroot/releases/download/v4.2.0/enroot_4.2.0-1_${arch}.deb` (+ `enroot+caps`), `apt install ./*.deb`, optional `fuse-overlayfs libnvidia-container-tools pigz squashfuse`; self-check `enroot-check_<ver>_$(uname -m).run --verify`.
- Occupies: rootless container runtime.
- Relevance: Ubuntu 24.04+ AppArmor userns restriction is the most likely first failure on this host **[the host's Ubuntu release was not re-audited in this cell]**.

**F17. Enroot GPU exposure is env-driven (`NVIDIA_VISIBLE_DEVICES` -> `nvidia-container-cli --no-cgroups`)** — first-party (source)
- URLs: https://github.com/NVIDIA/enroot/blob/master/conf/hooks/98-nvidia.sh ; https://github.com/NVIDIA/pyxis/wiki/Setup ; https://github.com/NVIDIA/pyxis/wiki/Frequently-asked-questions
- Claims: hook passes `--device=${NVIDIA_VISIBLE_DEVICES}` to `nvidia-container-cli --user ... configure` with `--no-cgroups`; Pyxis wiki recommends `ENROOT_RESTRICT_DEV y` "if you want to allow users to use NVIDIA_VISIBLE_DEVICES to only have a subset of all GPUs"; FAQ: `srun --export ALL,NVIDIA_VISIBLE_DEVICES=0 --container-image nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi -L` (plain `--export` wipes the environment and breaks the import). Recommended `enroot.conf`: `ENROOT_RUNTIME_PATH /run/enroot/user-$(id -u)` (tmpfs), `ENROOT_CACHE_PATH` persistent local, `ENROOT_DATA_PATH /tmp/enroot-data/user-$(id -u)` (local/tmpfs), `ENROOT_SQUASH_OPTIONS -comp zstd -Xcompression-level 3 -b 1M -exit-on-error`, `ENROOT_MOUNT_HOME n`, `ENROOT_ROOTFS_WRITABLE y`. Pyxis namespaces: user, mount, cgroup namespaces; **no** network or PID namespace by default (v0.24 adds opt-in `--container-unshare=net,ipc,uts`).
- Occupies: container-side GPU visibility.
- Relevance: inside Pyxis the kernel-level guarantee still comes from Slurm's eBPF program (F2); the hook only filters what libnvidia-container mounts. Both layers must agree for the receipt's "visible devices" claim.

**F18. Pyxis/Enroot negatives relevant to this lane (2026 issues)** — first-party issue reports
- https://github.com/NVIDIA/pyxis/issues/175 (2026-01-05, open, 0 comments): "Installed Slurm 25.11.1 and enroot with pyxis spank plugin having issues" — Grok container jobs hang at start under Slurm 25.11.1 + PMIx 4.2.9 + pyxis 0.21.0; worked on Slurm 23. Unresolved, uncorroborated.
- https://github.com/NVIDIA/pyxis/issues/176 (2026-02-10; Slurm 25.11.2, Enroot 4.1.0, Pyxis 0.22.0): a `TaskProlog` script breaks container steps (`slurm task_prolog can not be executed ... No such file or directory`); maintainer fix: `echo '/etc/slurm/task_prolog.sh' | sudo tee /etc/enroot/mounts.d/task_prolog.fstab`.
- https://github.com/NVIDIA/pyxis/issues/161 (2025-03-13, comment 2026-02-18): after `scontrol requeue`, `enroot remove -f pyxis_<job>.<step>` fails and the requeued job dies because the directory exists; comment attributes it to `ENROOT_DATA_PATH` on a shared `/home` — put it on local storage.
- https://github.com/NVIDIA/pyxis/issues/180 (2026-06-26): zstd-compressed image layers fail with older enroot ("tar: This does not look like a tar archive"); maintainer: supported "with recent versions of enroot" (4.2.0 "Handle images with mixed media types").
- https://github.com/NVIDIA/enroot/issues/265 (2026-03-27, updated 2026-08-10): `nvidia-persistenced/socket: operation not permitted` when slurmd runs inside Kubernetes (Slinky `slurmd-pyxis:25.11-ubuntu24.04`, CTK 1.19.0) — bare metal unaffected.
- Occupies: known failure modes.
- Relevance: (i) requeue-based resume needs local `ENROOT_DATA_PATH`; (ii) BuildKit zstd layers require Enroot >= 4.2.0; (iii) do not add a TaskProlog without the mounts.d entry; (iv) the 25.11.1 hang report is unresolved — another reason to run a receipted compatibility doctor (gap G2).

**F19. Slurm-native OCI (`--container`, `oci.conf`, `scrun`) and Docker's cgroup placement** — first-party
- URLs: https://slurm.schedmd.com/containers.html ; https://docs.docker.com/engine/containers/runmetrics/
- Claims: Slurm natively runs unprivileged OCI bundles (`sbatch/srun --container $ABS_PATH_TO_BUNDLE`), `oci.conf` examples for runc/crun/nvidia-container-runtime/Enroot 3.3.0; "All containers must run under unprivileged (i.e. rootless) invocation"; rootless Docker via `scrun` needs Slurm >= 23.02 and Docker >= 20.10 with `--security-opt label:disable --security-opt seccomp=unconfined --security-opt apparmor=unconfined --net=none` on every call; `docker exec`/`compose`/`pause` unsupported. Docker docs: on cgroup v2 hosts with the (default) systemd driver a container's cgroup is `/sys/fs/cgroup/system.slice/docker-<longid>.scope/` — i.e. outside any Slurm job cgroup.
- Occupies: alternative container integration; explains the Docker-in-sbatch accounting hole.
- Relevance: `docker run` from an sbatch escapes Slurm's cgroup/proctrack (Kevin's discovery lane compensates with traps and `--gpus device=`), which is why the publication lane is Pyxis, not Docker.

**F20. Sarus Suite (CSCS, arXiv 2604.17064, 2026-04-18)** — arXiv preprint (peer-review status unverified)
- URL: https://arxiv.org/abs/2604.17064
- Claim (abstract): Podman-engine HPC container architecture; "matches the performance and scaling of the production Enroot+Pyxis baseline while delivering consistently faster per-node container startup" on Cray EX GH200 across PyFR, SPH-EXA, Megatron-LM, Pynamic. First-party claim.
- Occupies: container-engine alternative axis.
- Relevance: confirms Enroot+Pyxis is the production baseline; no reason for Kevin to invent a runtime.

### D. Checkpoint / SIGUSR1 / requeue practice

**F21. sbatch `--signal`, `--requeue`, `SLURM_RESTART_COUNT`, scancel semantics** — first-party
- URLs: https://slurm.schedmd.com/sbatch.html ; https://slurm.schedmd.com/scancel.html ; https://slurm.schedmd.com/scontrol.html
- Claims: `--signal=[{R|B}:]<sig_num>[@sig_time]` "When a job is within sig_time seconds of its end time, send it the signal ... the signal may be sent up to 60 seconds earlier than specified ... default time will be 60 seconds. Use the 'B:' option to signal only the batch shell, none of the other processes will be signaled. By default all job steps will be signaled, but not the batch shell itself."; `--requeue`: "the batch script is initiated from its beginning with the same job ID"; `SLURM_RESTART_COUNT` counts restarts/requeues; `--open-mode=append`; `scancel --signal=USR1 --batch <jobid>` signals only the batch step ("Most shells cannot handle signals while a command is running ... so the shell needs to wait until the command ends") and `--full` signals script and children; `scontrol requeue <jobid>` requeues running/suspended/finished batch jobs. `KillWait` (default 30 s) between SIGTERM and SIGKILL at the limit.
- Occupies: scheduler-side checkpoint signalling.
- Relevance: Kevin's templates use `--signal=B:USR1@180` with a `trap ... USR1` forwarder — consistent with the doc; add `--requeue`, `--open-mode=append`, and a `SLURM_RESTART_COUNT` branch.

**F22. Checkpointing inside the SIGUSR1 handler is unsafe; flag-then-checkpoint-at-boundary works** — first-party issue + PR (negative result)
- URLs: https://github.com/Lightning-AI/pytorch-lightning/issues/21406 (2025-12-05, open) ; https://github.com/Lightning-AI/pytorch-lightning/pull/21407 (open, not merged as of 2026-09-01)
- Claims: "sometimes the handler would just stop running after or while saving the HPC checkpoint to disk ... The signal handler just never completes until the program gets killed by SLURM"; handlers can run "in the middle of a backward pass and store a corrupted checkpoint". PR makes SIGTERM/requeue signals only set a flag checked at the next callback hook. Reporter (2026-01-04): 9 runs x ~3 weeks, "~10 successful requeues in a row (one every 2 days)" with the patch, versus "almost always fail" before.
- Occupies: application-side checkpoint protocol.
- Relevance: validates Kevin's "episode-boundary checkpoint marker" design; anecdotal (n=9 runs, one cluster), not peer-reviewed.

**F23. Princeton Research Computing (Della/Tiger) — limits and recommended long-run pattern; no `--signal` guidance found** — first-party institutional docs (Browser-rendered 2026-09-01)
- URLs: https://researchcomputing.princeton.edu/systems/della ; https://researchcomputing.princeton.edu/systems/tiger ; https://researchcomputing.princeton.edu/support/knowledge-base/slurm ; (404) https://researchcomputing.princeton.edu/support/knowledge-base/checkpointing
- Claims: Della GPU QOS: gpu-test 61 min / gpu-short 24 h / gpu-medium 72 h / gpu-long 144 h (6 days, 7 jobs, 16 GPUs per user); PLI members have "exclusive access to 336 H100 SXM GPUs (42 nodes at 8 GPUs per node)", NVLink all-to-all, NDR InfiniBand, 96 cores, 1 TB. Tiger QOS: test 1 h, vshort 5 h, short 24 h, medium 72 h, long 144 h, vlong 360 h (15 days); "H100 GPU access is restricted at this time to only those PIs on the MRI grant from NSF"; `salloc ... --gres=gpu:1 --account=<account>`. Slurm KB: "If your job fails to finish before the specified time limit then it will be killed ... include an extra 20% for safety"; for runs longer than the limit, "your application must have a way of writing a checkpoint file and it must be able to figure out which checkpoint file to read at the start of each job step", chained with `#SBATCH --job-name=LongJob` + `#SBATCH --dependency=singleton` and repeated `sbatch job.slurm`. The site search for "checkpoint" returns only the Slurm KB page and the Apptainer page; **no Princeton page prescribing `--signal`/USR1 was found** (negative finding under this coverage).
- Occupies: institutional walltime/checkpoint conventions.
- Relevance: if Kevin later runs on Della (PLI) the 6-day cap and dependency-chaining pattern apply; on his dedicated node he should still emulate a bounded walltime + requeue to keep the harness portable.

**F24. tmux practice for interactive Slurm sessions** — first-party institutional docs (CÉCI, NeSI)
- URLs: https://support.ceci-hpc.be/doc/_contents/SubmittingJobs/SlurmInteractive.html ; https://docs.nesi.org.nz/Interactive_Computing/Slurm_Interactive_Sessions/
- Claims: `srun --pty bash`/`salloc` "will not survive an SSH disconnection from the login node"; start tmux on the login node first, run srun/salloc inside, detach with Ctrl-b d; alternative: start tmux detached inside an sbatch script (`tmux new-session -d -s <name>`) so the interactive session "survives login node reboots". NeSI: use tmux for any long-running interactive process.
- Occupies: session durability.
- Relevance: matches Kevin's `scripts/tmux-research-session.sh` and `infra/README.md` ("tmux is not a scheduler or checkpoint system").

**F25. DMTCP transparent checkpoint/restart in HPC containers (NERSC, arXiv 2407.19117, 2024-07-26)** — arXiv preprint (venue unverified)
- URL: https://arxiv.org/abs/2407.19117
- Claim: DMTCP C/R evaluated on Perlmutter inside and outside Shifter/Podman-HPC containers.
- Occupies: transparent (non-application) checkpointing alternative.
- Relevance: an alternative to SIGUSR1 application checkpoints for CPU doctors; GPU/CUDA state C/R is not claimed for the LLM case — not a substitute for Kevin's harness.

### E. Docker, CDI, SBOM, digest pinning

**F26. Docker 28.x/29.x facts relevant to the discovery lane** — first-party
- URLs: https://docs.docker.com/engine/release-notes/28/ ; https://docs.docker.com/engine/release-notes/29/ ; https://docs.docker.com/engine/containers/gpu/ ; https://docs.docker.com/reference/cli/docker/container/run/ ; https://docs.docker.com/reference/cli/docker/image/pull/
- Claims: 28.2.0 (2025-05-28) "CDI is now enabled by default" and `docker info` shows CDI devices; 28.3.0 (2025-06-24) AMD `--gpus`; 28.5.2 (2025-11-05) last 28.x; 29.0.0 (2025-11-10) "cgroup v1 is deprecated. Support continues until at least May 2029"; 29.2.0 "Handle --gpus requests for NVIDIA devices using CDI if possible"; 29.7.2 (2026-08-05) latest. GPU syntax: `--gpus all`, `--gpus device=0`, `--gpus device=GPU-<uuid>`, `--gpus '"device=0,2"'` ("exposes the GPUs at index 0 and 2 — the first and third GPUs listed in nvidia-smi output"). `docker run --sig-proxy` default true ("Proxy received signals to the process"); `--init` forwards signals and reaps. `docker pull NAME@DIGEST` pins "exactly which version of an image to pull".
- Occupies: Docker GPU/CDI/digest mechanics.
- Relevance: Kevin's `docker-research.sbatch` uses `--gpus "${docker_gpu_request}"` from `CUDA_VISIBLE_DEVICES` — index-based; prefer UUIDs (`nvidia-smi -L`) to remove the ordering hazard of F9 **[recommendation, not from docs]**.

**F27. NVIDIA Container Toolkit 1.20.0 and CDI refresh** — first-party
- URLs: https://github.com/NVIDIA/nvidia-container-toolkit/releases (v1.20.0 2026-08-13; v1.19.1 2026-05-21) ; https://github.com/NVIDIA/libnvidia-container/releases (v1.20.0 2026-08-13) ; https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html
- Claims: since CTK 1.18.0 `nvidia-cdi-refresh.service` auto-generates `/var/run/cdi/nvidia.yaml` (`nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml`), `nvidia-ctk cdi list` lists devices; 1.20.0 adds CDI hooks limiting EGL/Vulkan visibility to assigned GPUs.
- Occupies: host GPU container plumbing.
- Relevance: `libnvidia-container-tools` 1.20.0 satisfies Enroot's `>= 1.0` requirement; pin it.

**F28. SBOM: syft v1.51.1 and BuildKit attestations** — first-party
- URLs: https://github.com/anchore/syft/releases/tag/v1.51.1 (2026-08-27) ; https://github.com/anchore/syft/blob/main/README.md ; https://oss.anchore.com/docs/guides/sbom/scan-targets/ ; https://docs.docker.com/build/metadata/attestations/sbom/
- Claims: `syft <image> -o spdx-json=./spdx.json -o cyclonedx-json=./cdx.json`; sources include `docker:`, `oci-archive:`, `oci-dir`, `singularity`; `--from registry` "to bypass local daemons and pull directly"; registry-free pinned flow `skopeo copy docker://alpine@sha256:... oci-archive:alpine.tar`; syft can emit in-toto attestations. BuildKit: `docker buildx build --sbom=true` attaches an SPDX in-toto attestation generated with the "BuildKit Syft scanner"; read back with `docker buildx imagetools inspect <ref> --format "{{ json .SBOM.SPDX }}"`; `BUILDKIT_SBOM_SCAN_CONTEXT`/`BUILDKIT_SBOM_SCAN_STAGE` extend coverage.
- Occupies: supply-chain receipts.
- Relevance: Kevin's `mempalace-sbom.sbatch`/`past-vllm-sbom.sbatch` already exist; pin syft 1.51.1 and scan the digest, not the tag.

### F. vLLM inside Slurm

**F29. vLLM v0.28.0; single-node TP via `mp`; no official Slurm page** — first-party
- URLs: https://github.com/vllm-project/vllm/releases (v0.28.0 2026-08-26; v0.27.1 2026-08-11) ; https://docs.vllm.ai/en/latest/serving/parallelism_scaling/ ; https://docs.vllm.ai/en/latest/usage/troubleshooting/ ; https://github.com/vllm-project/vllm/tree/main/docs/deployment/frameworks (22 framework pages, none for Slurm) ; Docker Hub `vllm/vllm-openai:v0.28.0` index digest `sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14` (amd64 `sha256:2286e8533ca8b6bc777594bae30524f1426ba46ca21797524e06df6a94b06635`, 8.63 GB) via https://hub.docker.com/v2/repositories/vllm/vllm-openai/tags/v0.28.0
- Claims: "The default distributed runtimes are Ray for multi-node inference and native Python multiprocessing for single-node inference" (`--distributed-executor-backend mp|ray`); `vllm serve ... --tensor-parallel-size 4` (and `--pipeline-parallel-size`); use TP within an NVLink node. Troubleshooting: `NCCL_DEBUG=TRACE`, `VLLM_HOST_IP` override, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, NCCL init failures from missing `IPC_LOCK` or unmounted `/dev/shm`, `VLLM_ENABLE_V1_MULTIPROCESSING=0` for debugging.
- Occupies: inference engine; documented single-node topology.
- Relevance: 8xH100 -> `--tensor-parallel-size 8` in one `srun --ntasks=1` step; Enroot shares host IPC/net by default so `/dev/shm` is the host's (do not `--container-unshare=ipc` for vLLM without sizing shm) **[inference from F17]**.

**F30. Institutional and community Slurm+vLLM templates** — first-party (institutional docs / READMEs)
- URLs: https://scienceit-docs.lbl.gov/hpc/software/llms/vllm/ (module `ai/vllm/0.19.0`; sbatch with `--nodes=1 --ntasks=1 --cpus-per-task=14 --gres=gpu:1`; `vllm serve openai/gpt-oss-20b --gpu-memory-utilization=0.85`; attach via `srun --jobid=JOBID --overlap --pty bash`; port 8000) ; https://www.docs.arc.vt.edu/ai/030_vllm.html (`--gres gpu:l40s:2`, `--tensor-parallel-size 2`, `--port 8000`, API key, `ssh -N -L 8000:<node>:8000`, serve from a local model path) ; https://github.com/VectorInstitute/vector-inference (106 stars, v0.9.0 2026-04-10, pins vLLM 0.19.0, generates and archives the Slurm script per launch) ; https://github.com/wfrederick7/cluster-llm-server (2026-08-27: gpt-oss-120b TP=8 on one 8xH100 node) ; https://github.com/igeniusai/domyn-swarm (24 stars, 2026-09-01: vLLM replicas + load-balancer jobs, row-level checkpoint every 16 rows) ; https://github.com/NicolasSchuler/hpc-compose (2026-08-30: Compose-like spec -> one Slurm job via Pyxis/Enroot) ; https://github.com/KatherLab/LLM-Scheduler (2026-08-20)
- Occupies: launcher tooling.
- Relevance: nothing here needs inventing; the pattern is one task per node, `vllm serve` in the batch step, health-poll, then the harness talks to `localhost:8000`.

---

## 2. Concrete commands and pins (fal-h100-01)

All version strings verified against tags/releases on 2026-09-01. Commands marked (V) come verbatim
or near-verbatim from the cited doc; (U) are assembled by this cell and **not verified in official docs**.

### 2.1 Pins
| Component | Pin | Source/date |
|---|---|---|
| Slurm | 25.11.7 (`slurm-25.11.7.tar.bz2`) | tag 2026-07-14; support to May 2027 (F4, F5) |
| Slurm (alt) | 26.05.3 | tag 2026-08-13; SLUID cgroup paths (F5) |
| Pyxis | v0.24.0 | 2026-05-12 (F14) |
| Enroot | v4.2.1 (`enroot_4.2.1-1_amd64.deb`, `enroot+caps_4.2.1-1_amd64.deb`) | 2026-06-09 (F16) |
| NVIDIA Container Toolkit / libnvidia-container-tools | 1.20.0 | 2026-08-13 (F27) |
| Docker Engine | keep 28.x (>= 28.2.0 has CDI default); 29.7.2 is current | (F26) |
| syft | v1.51.1 | 2026-08-27 (F28) |
| vLLM | v0.28.0; `vllm/vllm-openai@sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14` | 2026-08-26 (F29) |
| Kernel headers | `linux-libc-dev` providing `include/linux/bpf.h` >= 5.7 | (F2) |
| dbus | `libdbus-1-dev` >= 1.11.16 | (F2) |

### 2.2 Build and install Slurm 25.11.7 (SchedMD Debian packaging) (V + U)
```bash
sudo apt-get install -y build-essential fakeroot devscripts equivs            # (V) quickstart_admin
sudo apt-get install -y libdbus-1-dev linux-libc-dev libmunge-dev             # (U) cgroup/v2 deps; munge stays default auth
# NVML headers for AutoDetect=nvml: from the CUDA repo (e.g. cuda-nvml-dev-12-8) or libnvidia-ml-dev  (U; package name not verified)
curl -fsSLO https://download.schedmd.com/slurm/slurm-25.11.7.tar.bz2            # (V) HTTP 200 verified
tar -xaf slurm-25.11.7.tar.bz2 && cd slurm-25.11.7
sudo mk-build-deps -i debian/control                                          # (V)
debuild -b -uc -us                                                            # (V)
grep -E 'bpf|dbus|nvml' config.log | head                                     # (V) "Look at your config.log ... to see if they were correctly detected"
# Clean reinstall path (single node, no accounting DB, no jobs to preserve):   (U — inference, see F4)
sudo systemctl stop slurmd slurmctld && sudo apt-get remove -y 'slurm-wlm*' 'slurm-client*' 'slurmd' 'slurmctld'
sudo apt install ../slurm-smd_25.11.7-1_amd64.deb ../slurm-smd-client_25.11.7-1_amd64.deb \
  ../slurm-smd-slurmctld_25.11.7-1_amd64.deb ../slurm-smd-slurmd_25.11.7-1_amd64.deb ../slurm-smd-dev_25.11.7-1_amd64.deb   # (V) names; "use apt, not dpkg"
sudo mkdir -p /var/spool/slurmctld-25.11 && sudo chown slurm: /var/spool/slurmctld-25.11        # (U) fresh StateSaveLocation
```
In-place alternative if state must be preserved: 21.08 -> 23.02 -> 24.11 -> 25.11, backing up
`StateSaveLocation` at each hop and starting daemons slurmctld before slurmd (F4).

### 2.3 Configuration (V)
```
# /etc/slurm/cgroup.conf
CgroupPlugin=cgroup/v2
ConstrainCores=yes
ConstrainDevices=yes
ConstrainRAMSpace=yes
ConstrainSwapSpace=yes
# SignalChildrenProcesses=yes   # optional: signals reach all children of the step (F3)

# /etc/slurm/slurm.conf (deltas from infra/slurm/host-single-node/slurm.conf)
ProctrackType=proctrack/cgroup
TaskPlugin=task/cgroup,task/affinity
JobAcctGatherType=jobacct_gather/cgroup
JobRequeue=1
GresTypes=gpu
NodeName=fal-h100-01 CPUs=208 Boards=1 SocketsPerBoard=2 CoresPerSocket=52 ThreadsPerCore=2 RealMemory=1750000 Gres=gpu:h100:8 State=UNKNOWN
# If AutoDetect complains about core affinity vs socket boundaries: NodeName=... Parameters=l3cache_as_socket (gres.html)

# /etc/slurm/gres.conf
AutoDetect=nvml
# Optional pins; a mismatch drains the node (gres.conf.html):
# NodeName=fal-h100-01 Name=gpu Type=h100 File=/dev/nvidia[0-7]
```
systemd: slurmd unit must carry `Delegate=yes` (SchedMD units do) (F2).

### 2.4 Validate GRES and device isolation (V + U)
```bash
sudo slurmd -C                       # (V) hardware + autodetected GPUs (24.11+)
sudo slurmd -G                       # (V) merged GRES view
scontrol show node fal-h100-01 | grep -i -E 'gres|state'
srun --gres=gpu:1 -N1 -n1 nvidia-smi -L                                    # expect exactly 1 line
srun --gres=gpu:1 -N1 -n1 bash -c 'echo CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES; python3 -c "import torch;print(torch.cuda.device_count())"'   # expect 0 and 1
srun --gres=gpu:1 -N1 -n1 bash -c 'for d in /dev/nvidia[0-9]*; do : < $d 2>/dev/null && echo "$d OPEN" || echo "$d denied"; done'   # (U) EPERM on 7 of 8
JOB=<running jobid>; sudo bpftool cgroup list /sys/fs/cgroup/system.slice/slurmstepd.scope/job_$JOB effective   # (V, path form <26.05) shows Slurm_Cgroup_v2
sudo journalctl -k | grep 'BPF prog-id'                                    # (V) LOAD/UNLOAD audit lines
CUDA_DEVICE_ORDER=PCI_BUS_ID nvidia-smi -L                                 # (V) ordering check after every boot (F9)
```

### 2.5 Enroot 4.2.1 + Pyxis 0.24.0 (V + U)
```bash
arch=$(dpkg --print-architecture)
curl -fSsL -O https://github.com/NVIDIA/enroot/releases/download/v4.2.1/enroot_4.2.1-1_${arch}.deb
curl -fSsL -O https://github.com/NVIDIA/enroot/releases/download/v4.2.1/enroot+caps_4.2.1-1_${arch}.deb
sudo apt install -y ./enroot*_4.2.1-1_${arch}.deb fuse-overlayfs libnvidia-container-tools pigz squashfuse   # (V) installation.md pattern (doc example uses 4.2.0)
curl -fSsL -O https://github.com/NVIDIA/enroot/releases/download/v4.2.1/enroot-check_4.2.1_$(uname -m).run
chmod +x enroot-check_*.run && ./enroot-check_*.run --verify && ./enroot-check_*.run              # (V) requirements.md
sysctl kernel.apparmor_restrict_unprivileged_userns    # (V) must be 0 on Ubuntu unless the shipped apparmor profile is installed
sudo tee /etc/enroot/enroot.conf <<'EOF'               # (V) Pyxis wiki Setup example, paths adapted (U)
ENROOT_RUNTIME_PATH /run/enroot/user-$(id -u)
ENROOT_CACHE_PATH /home/kevin/cotcodec-runs/enroot-cache/group-$(id -g)
ENROOT_DATA_PATH /tmp/enroot-data/user-$(id -u)
ENROOT_SQUASH_OPTIONS -comp zstd -Xcompression-level 3 -b 1M -exit-on-error
ENROOT_MOUNT_HOME n
ENROOT_RESTRICT_DEV y
ENROOT_ROOTFS_WRITABLE y
EOF
git clone https://github.com/NVIDIA/pyxis && cd pyxis && git checkout v0.24.0
make orig && make deb                                  # (V) requires slurm-smd-dev from the SAME Slurm build
sudo apt install ../nvslurm-plugin-pyxis_0.24.0*_amd64.deb                   # (V) README uses dpkg -i; apt preferred per SchedMD
sudo mkdir -p /etc/slurm/plugstack.conf.d
sudo ln -s /usr/share/pyxis/pyxis.conf /etc/slurm/plugstack.conf.d/pyxis.conf   # (V)
grep -q plugstack.conf.d /etc/slurm/plugstack.conf 2>/dev/null || echo 'include /etc/slurm/plugstack.conf.d/*' | sudo tee /etc/slurm/plugstack.conf   # (U) not verified against spank.html
sudo systemctl restart slurmd && srun --help | grep container-image           # (V)
strace -e openat srun --help 2>&1 >/dev/null | grep -E 'plugstack|spank_pyxis'   # (V)
srun --container-image=ubuntu@sha256:d22e4fb389065efa4a61bb36416768698ef6d955fe8a7e0cdb3cd6de80fa7eec grep PRETTY /etc/os-release   # (V) wiki digest example
```
Pyxis plugstack line: `required /usr/local/lib/slurm/spank_pyxis.so runtime_path=/run/pyxis execute_entrypoint=0 container_scope=job sbatch_support=1` (wiki; use `container_scope=job` so unnamed/named containers are cleaned in the epilog).

### 2.6 Digest-pinned image + SBOM receipts (V + U)
```bash
IMG="ghcr.io/<org>/cotcodec@sha256:<64hex>"
# once per digest: import to a squashfs and hash it
enroot import -o /home/kevin/cotcodec-runs/images/cotcodec-<digest12>.sqsh "docker://ghcr.io#<org>/cotcodec@sha256:<64hex>"   # (V) URI grammar from src/docker.sh
sha256sum /home/kevin/cotcodec-runs/images/cotcodec-<digest12>.sqsh > .../cotcodec-<digest12>.sqsh.sha256
# provenance line inside the image (Enroot >= 4.2.0): grep enroot-provenance <rootfs>/etc/rc
# SBOM tied to the digest, not the tag
syft "$IMG" --from registry -o spdx-json=sbom.spdx.json -o cyclonedx-json=sbom.cdx.json      # (V) syft docs; pin syft v1.51.1
# or at build time: docker buildx build --sbom=true --provenance=true --push -t ghcr.io/<org>/cotcodec:<tag> .   # (V)
docker buildx imagetools inspect ghcr.io/<org>/cotcodec:<tag> --format '{{ json .SBOM.SPDX }}' > sbom.buildkit.spdx.json   # (V)
```

### 2.7 SIGUSR1 checkpoint + fresh-job resume skeleton (V + U)
```bash
#SBATCH --gres=gpu:h100:1 --cpus-per-task=16 --mem=64G --time=02:00:00
#SBATCH --signal=B:USR1@300        # (V) may arrive up to 60 s early; B: = batch shell only
#SBATCH --requeue                  # (V) script restarts from the top with the same JobID
#SBATCH --open-mode=append         # (V) keep prior attempt logs
echo "restart_count=${SLURM_RESTART_COUNT:-0}"                  # (V) env var
child=""; forward() { [ -n "$child" ] && kill -"$1" "$child" 2>/dev/null; }
trap 'forward USR1' USR1; trap 'forward TERM' TERM               # (U) shell handles traps only between foreground commands -> background + wait
srun --ntasks=1 --container-image=/home/kevin/cotcodec-runs/images/cotcodec-<digest12>.sqsh \
     --container-mounts=/home/kevin/cotcodec-runs:/runs --no-container-entrypoint \
     python -m cotcodec.run --resume-dir /runs/$SLURM_JOB_ID --checkpoint-on USR1 &   # application: set flag on USR1, save at episode boundary (F22)
child=$!; wait "$child"; rc=$?; [ -n "$child" ] && wait "$child" 2>/dev/null; exit $rc
# Drills (V): scancel --signal=USR1 --batch <jobid> ; scontrol requeue <jobid> ; check ENROOT_DATA_PATH is local (pyxis #161)
```
Open question (gap G1): whether `srun --container-image` delivers the forwarded USR1 to the containerized python when the step is signalled directly (no `B:`); Pyxis documents SIGTERM handling only (F14).

### 2.8 vLLM inside one Slurm step (U, assembled from F29/F30)
```bash
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=32 --gres=gpu:h100:8 --time=04:00:00
srun --ntasks=1 --container-image=/home/kevin/cotcodec-runs/images/vllm-openai-v0.28.0-61fc8a89.sqsh \
     --container-mounts=/home/kevin/cotcodec-runs/hf-cache:/root/.cache/huggingface,/home/kevin/cotcodec-runs/models:/models:ro \
     --no-container-entrypoint \
     vllm serve /models/<snapshot-dir> --tensor-parallel-size 8 --distributed-executor-backend mp --port 8000 --gpu-memory-utilization 0.90 &
until curl -sf localhost:8000/v1/models >/dev/null; do sleep 5; done   # then run the harness against http://localhost:8000
# attach for debugging: srun --jobid=$SLURM_JOB_ID --overlap --pty bash     (V, LBL)
# hangs: NCCL_DEBUG=TRACE ; VLLM_HOST_IP=<ip> ; check /dev/shm and IPC_LOCK (V, vLLM troubleshooting)
```
Caveat: Enroot's optional `50-slurm-pytorch.sh` hook injects `RANK/WORLD_SIZE/MASTER_ADDR/MASTER_PORT` into images that define `PYTORCH_VERSION`; interaction with vLLM's mp executor is **not verified** (gap G4) — keep that hook out of `/etc/enroot/hooks.d` for vLLM steps.

---

## 3. Occupied-axes table

| Axis | What is taken (do not build) | Evidence |
|---|---|---|
| Kernel-level GPU device isolation under cgroup v2 in Slurm | Slurm cgroup/v2 + eBPF device programs (since 22.05; fail-closed since 25.05.0rc1); `ConstrainDevices=yes` | F1, F2, F3, F6 |
| Container plugin for Slurm steps | NVIDIA Pyxis (SPANK) + Enroot; Slurm native OCI/`scrun`; CSCS Sarus Suite; institutional Apptainer | F13–F17, F19, F20 |
| Immutable image references and provenance in the scheduler lane | Enroot `@sha256` import with per-layer checksums and `enroot-provenance`; Pyxis `--container-image ...@sha256`; `.sqsh` reuse; Docker digest pulls | F15, F26 |
| SBOM and build attestations | syft (SPDX/CycloneDX/in-toto), BuildKit `--sbom=true` with Syft scanner | F28 |
| Time-limit signalling, requeue, restart detection | `--signal`, `--requeue`, `SLURM_RESTART_COUNT`, `scancel --signal --batch`, `scontrol requeue`, `KillWait` | F21 |
| Safe checkpoint protocol under SIGUSR1 | flag-in-handler + save-at-boundary (Lightning PR 21407); transparent C/R via DMTCP for CPU codes | F22, F25 |
| GPU visibility semantics (env vs cgroup) | `CUDA_VISIBLE_DEVICES` renumbering, `CUDA_DEVICE_ORDER`, `NVIDIA_VISIBLE_DEVICES`/libnvidia-container, UUID option (26.05) | F9, F10, F17, F26 |
| vLLM-on-Slurm launchers | vector-inference, domyn-swarm, LLM-Scheduler, hpc-compose, LBL/VT templates | F29, F30 |
| Interactive session durability | tmux-on-login-node / tmux-in-sbatch patterns | F24 |

## 4. Open gaps (searched, not found)

**G1. Documented SIGUSR1 propagation through Pyxis/Enroot containers.** Searched: Pyxis README, wiki (Usage/Setup/Advanced/FAQ/Error reference), releases, commit 26fa047, Enroot docs. Found only the 2026 SIGTERM-forwarding fix (waitpid EINTR loop). No doc, test, or issue states that `--signal=USR1` (with or without `B:`) reaches the containerized process. Kevin advantage: the Docker/Slurm harness already forwards USR1 and records an episode-boundary checkpoint marker; a receipted 3-way doctor (bare step vs `docker run --sig-proxy` vs `srun --container-image`) on the dedicated node is cheap and directly unblocks the publication contract.

**G2. A public compatibility receipt for Slurm 25.11.x/26.05.x + Pyxis 0.24.0 + Enroot 4.2.x on Ubuntu.** Searched: Pyxis/Enroot releases and issues, Slinky docs, WebSearch (before quota exhaustion). Found one unresolved hang report on 25.11.1 (pyxis 0.21.0, #175) and a TaskProlog incompatibility on 25.11.2 (#176); Slinky publishes `slurmd-pyxis:25.11-ubuntu24.04` images but no version matrix. Kevin advantage: root on a single dedicated 8xH100 node with an existing doctor framework (`scripts/check_compute_env.sh`, `research-image-cuda-doctor.sh`) — he can publish an exact pinned build matrix with receipts, which nobody in the searched corpus has done.

**G3. In-job, unprivileged proof that the eBPF device constraint is attached.** Searched: cgroup_v2.html, slurm-users threads (2024 bpftool thread asked for a map-based dump; none exists), SchedMD Bugzilla (login-only). `bpftool` needs privileges; the 2025 LXD thread shows EPERM. Kevin advantage: his receipts already record "visible devices"; adding an in-job `/dev/nvidia*` open() probe plus `nvidia-smi -L` and a root-side `bpftool cgroup list ... effective` snapshot is feasible on his node and would make the isolation claim a kernel fact in the sealed evidence.

**G4. Official vLLM guidance for Slurm/Pyxis steps (single task vs Enroot's Slurm-PyTorch hook).** Searched: vLLM docs tree (`docs/deployment/frameworks`: 22 pages, no Slurm), parallelism/troubleshooting pages, vLLM issues mentioning Slurm (only multi-node PP hang #26318 surfaced via search; recent issue list has no single-node Slurm item), GitHub code search (failed). Only institutional templates exist. Kevin advantage: 8xH100 + digest-pinned `vllm-openai@sha256:61fc8a...` + Tinker-adjacent local models (Qwen3.5-4B, Kimi-Linear-48B-A3B) let him seal a TP=8 vLLM-in-Pyxis doctor that the harness needs anyway.

**G5. Measured requeue/resume failure rates for containerized LLM jobs.** Searched: arXiv API/HTML (429), Semantic Scholar (429), OpenAlex (no relevant hits), GitHub (Pyxis #161 and Lightning #21406 are single-site anecdotes). Kevin advantage: kill/requeue drills (`scancel --signal=USR1 --batch`, `scontrol requeue`) are free on a dedicated node and can be sealed as negative/positive infrastructure evidence under the existing `research/evidence/harness/` format; this is harness evidence, not architecture novelty.

**G6. Princeton RC prescription for signal-based checkpointing on Della/Tiger.** Searched: Della, Tiger, Slurm KB pages (Browser), site search "checkpoint", the WebSearch-suggested `/support/knowledge-base/checkpointing` URL (404). Princeton documents QOS caps and `--dependency=singleton` chaining with application checkpoint files only. Kevin advantage: none for research; his harness could serve as the group's reference runbook if he runs on PLI H100 nodes later.

## 5. Queries run (57 distinct search queries + ~45 primary-page fetches)

WebSearch (14 executed; quota then exhausted): "Slurm 25.11 cgroup v2 ConstrainDevices eBPF NVIDIA GPU device isolation"; "Pyxis Enroot build against Slurm 25.05 SPANK plugin requirements 2026"; "Slurm upgrade 21.08 to 23.11 24.11 25.05 major version skip path slurmdbd"; "vLLM inside Slurm sbatch job 2026 tensor parallel single node H100 srun"; "Princeton Research Computing checkpointing SIGUSR1 Slurm --signal requeue Della"; "syft SBOM docker image digest pinned reproducible 2026"; "CUDA_VISIBLE_DEVICES vs cgroup ConstrainDevices Slurm GPU isolation trade-offs nvidia-smi"; "Slurm AutoDetect=nvml GRES gpu validation slurmd gres.conf mismatch 2026"; "Slurm 26.05 release notes cgroup GRES changes SchedMD"; "docker run inside Slurm job escapes cgroup accounting daemon root recommended rootless podman scrun"; "vLLM srun ntasks multiple processes hang Slurm vllm serve sbatch workaround issue"; "NVIDIA Container Toolkit CDI Docker 28 enabled by default nvidia-ctk cdi generate"; "tmux salloc srun --pty interactive GPU session best practice research computing 2026"; "enroot 4.2 pyxis 0.24 Slurm 25.11 incompatible OR Incompatible plugin version OR plugstack issue 2026". Refused by quota: site:researchcomputing.princeton.edu checkpointing USR1; Slurm cgroup v2 kernel requirement; Pyxis Enroot Slurm 25.11 Ubuntu install 2026; Slurm preemption SIGUSR1 GraceTime.

arXiv API (8, all empty/HTTP 429): slurm+container; vllm+slurm; checkpoint+preemption+GPU+training; checkpoint+LLM+fault tolerance; reproducib+container+GPU+Slurm; id_list=2407.19117 (x2); Slurm+LLM+inference; checkpointing+LLM+training+failures. arXiv HTML search (3, HTTP 429): "Slurm container Pyxis Enroot"; "checkpoint restart preemption GPU training fault tolerance LLM"; "vLLM Slurm HPC inference cluster". arXiv abs pages fetched OK: 2407.19117, 2604.17064.

Semantic Scholar (6, all HTTP 429 or empty): Slurm Pyxis Enroot containers HPC; checkpoint restart preemptible GPU cluster LLM training; containers HPC Slurm Enroot; checkpoint restart deep learning preemption cluster; Enroot Pyxis Slurm container; DMTCP checkpoint restart containers NERSC. OpenAlex (4): "Slurm containers Enroot Pyxis HPC"; "checkpoint restart GPU cluster preemption deep learning training"; "reproducible containerized GPU experiments Slurm digest"; "Sarus Suite Cloud-native Containers for HPC".

GitHub (11): `gh search repos pyxis enroot`; `gh search repos slurm vllm`; `gh search repos slurm checkpoint requeue`; `gh search repos --owner PrincetonUniversity slurm|checkpoint`; `gh search issues --repo NVIDIA/pyxis`; `gh search issues --repo NVIDIA/enroot`; `gh search issues --repo vllm-project/vllm slurm`; `gh search issues --repo NVIDIA/enroot digest`; code search `slurm repo:vllm-project/vllm` (x3 variants, no results). Plus direct reads of SchedMD tags/RELEASE_NOTES/CHANGELOGs, Pyxis/Enroot READMEs, wiki clone, releases, commits 26fa047 and 8b3a130, issues #175/#176/#161/#180/#265, Lightning #21406/#21407, syft/vector-inference/domyn-swarm/hpc-compose/cluster-llm-server/LLM-Scheduler/slurmise/job_defense_shield READMEs, nvidia-container-toolkit releases.

Hugging Face API (2): search "slurm" (unrelated robotics checkpoints only), "vllm slurm" (none). Kevin's X bookmarks `ft search` (6): slurm; pyxis enroot; vllm slurm; sbatch; cgroup; H100 cluster — all "No results found". SchedMD Bugzilla quicksearch (2): "ConstrainDevices cgroup/v2", "ebpf device" — login required. Princeton site search (Browser, 1): "checkpoint". Docker Hub API (2): vllm-openai tags, v0.28.0.

Primary pages fetched directly (curl/Browser): slurm.schedmd.com {cgroup_v2, cgroup.conf, slurm.conf, gres, gres.conf, slurmd, sbatch, scancel, scontrol, upgrades, containers, quickstart_admin, release_notes}; packages.ubuntu.com {jammy,noble,resolute} slurm-wlm and basic-plugins filelists; docs.docker.com {release-notes/28, release-notes/29, containers/gpu, containers/runmetrics, reference run/pull, build attestations sbom}; docs.nvidia.com container-toolkit {cdi-support, release-notes}; docs.vllm.ai {parallelism_scaling, troubleshooting}; oss.anchore.com syft scan-targets; scienceit-docs.lbl.gov vllm; docs.arc.vt.edu vllm; support.ceci-hpc.be interactive; docs.nesi.org.nz interactive; researchcomputing.princeton.edu {della, tiger, slurm KB} (Browser pane); groups.google.com slurm-users MIG/eBPF thread and lists.schedmd.com eBPF thread (WebFetch); slinky pyxis guide (WebFetch).

## 6. Coverage limits (honest)
- WebSearch: session quota (200) was exhausted after this cell's 14th query; four planned queries never ran.
- Jina reader (`r.jina.ai`) refused anonymous requests from this network (HTTP 401, AS7018); replaced by direct curl + Browser pane.
- arXiv API and arXiv HTML search returned HTTP 429 for every query all session; only individual abstract pages loaded. Semantic Scholar API returned 429 throughout. OpenAlex was used as a partial substitute (4 queries, low relevance). Peer-reviewed coverage of this topic is therefore weak; nearly all findings are first-party vendor/institutional sources.
- SchedMD Bugzilla requires login; no bug-tracker coverage beyond public CHANGELOGs and mailing lists.
- Princeton RC is Cloudflare-gated (curl/WebFetch 403). The Browser pane rendered Della, Tiger, and the Slurm KB, but the `/support/knowledge-base/checkpointing` URL returned "Page not found" and site search found no checkpointing page, so the brief's request to cite Princeton checkpointing docs could only be met via the Slurm KB dependency-chaining section (F23).
- GitHub code search returned nothing (likely token scope); vLLM source was not grepped for Slurm/RANK handling.
- Kevin's X bookmarks contain nothing on Slurm/Pyxis/vLLM-on-Slurm (6 probes).
- Nothing was executed on fal-h100-01 (read-only cell); the host's Ubuntu release, kernel, systemd, and AppArmor settings were not re-audited here. All (U)-marked commands are assembled, not tested.
- Mailing-list threads F10 were summarized from search-result snippets and not opened individually.
- Two community threads (F11, F12) and the Slinky guide were read through WebFetch summaries rather than raw HTML.
