# S2 v4 round 4: the `ap_delta` development rung (Slurm 1244)

Registration: `program/preregistrations/s2-arabic-cua-locale-v4.md` (DRAFT, not frozen; D80 (iv);
repaired under D84, D87 and D90). Development only: nothing here is a K1 result, and nothing here
decides anything registered. The K0 section is unchanged (`ed38b953...`), and so are
`harness/s2_locale/k0_v4.py`, `harness/s2_locale/ap_delta.py` and the batch files.

Why it ran. The third round restored `driver.main`'s pre-run checks in `ap_delta.run_rung`
(registration section "K1"), and until now they were only unit-tested: the repair round's
development jobs 1217 and 1218 ran `run_rung` without them, and round 4's smoke (1242, 1243) did not
exercise `run_rung`. Round 4's code review and audit both classed one host development rung as
cheap insurance before the freeze, not a D90 repair smoke (registration, section "Changes in round 4
(D90): review log").

## Result: every pre-run check ran and passed; both campaigns exit 0

In the development rung (`01-s2v4-apd-dev-rung/receipt.json`), before any session, `run_rung` made
`driver.main`'s checks with harness/q2's own functions:
- Docker's server facts: server 28.3.1, default runtime `runc`, runtimes `io.containerd.runc.v2` and
  `runc`, cgroup version 2.
- The VM image `sha256:fe8d9a5e...` and its digest reference
  `happysixd/osworld-docker@sha256:0e6497a9...` agree.
- The runner image `sha256:ac2b5815...` is present.
- Per image (E and AR): a regular, read-only file of the pinned size (24,459,214,848 bytes) whose
  SHA-256 equals its pin (E `51e47abb...`, AR `77cd9a2a...`), and `qemu-img info` through harness/q2's
  `qemu_img_info_argv`: format qcow2, virtual size 53,687,091,200 bytes.
- Dangling Docker volumes: 0 before and 0 after.

After the sessions both images hashed to their pins again (`qcow2_unchanged` true), no container
labelled with the job's id was left, and `infra_gates_pass` was true. The single-image campaign
(`00-s2v4-apd-dev-single/receipt.json`), which runs harness/q2's driver unchanged, recorded the same
Docker facts and image checks for E.

Trials (`summary.json`):
- Single-image campaign on E, one VM, screenshot setting: 3 of 3 trials pass. Cold boot 17.2 s;
  step p95 0.67 s.
- Development rung on E and AR at N = 2 (session 0 on E in the screenshot setting, session 1 on AR
  with accessibility): 6 of 6 pass. Cold boots 17.2 s each; step p95 1.90 s, from the
  accessibility-setting session, as in 1217 and 1218.
- harness/q2's `acceptance.load` reads both run directories with no counting problem, no foreign
  abort and no snapshot problem. `acceptance.rung` reads the development rung and, as it must, does
  not qualify it (2 boots of the 20 required, and a 6-trial workload instead of the 1,200-trial
  order).

These numbers agree with 1217 and 1218 (`program/evidence/2026-10-11/s2v4-image/apdelta-dev/`):
3 of 3 and 6 of 6 there too, cold boots 17.2-19.1 s, and step p95 0.63-0.68 s and 1.90 s.

## The job

- CPU only: `s2v4-apdelta.sbatch` (batch SHA-256 `0423c025...`, unchanged), purpose `development`,
  no GRES; 9 CPUs requested and 10 allocated, 16 GB, an 86-minute limit.
- Source: a `git archive` export of `3065d198d726a5eadb52b89e40d3974e1434fe98`, the text-only commit
  that resolved round 4's audit item (code identical to round 4's code head `b8c815c8`; source tree
  digest `6c1037c9...`, the same as smoke 1242's). The gzipped archive (SHA-256 `abeac91b...`) went
  to the host in 4 MB parts and was checked against its SHA-256 there before GNU tar extracted it.
  `.git_sha` names the commit.
- Manifest: `ap_delta.py render-dev` on the Mac from a local copy of the same export
  (`manifest-rendered.json`; the stored canonical form on the host is `8aec88bf...`, and the job's
  `manifest.json` equals it). It is `experiments/manifests/s2v4/apdelta-dev-v1.json` with only the
  commit, the source directory and the source tree digest changed (its `name` field is
  `render-dev`'s fixed `apd-dev-v1`). It passed `ap_delta.py validate` and `submit --dry-run` on the
  host before submission.
- Timing: submitted at 14:06:57 UTC on an empty queue and started at once; `ap_delta` ran from
  14:06:58 to 14:09:34 UTC (2.6 minutes; the rung campaign 97 s); `lane_exit=0`,
  `labelled_containers_left=0`. No other workstream had a step pending. Successor E session 1's 4B
  pair had ended at about 05:47 UTC, and E2's 9B pair may start no earlier than about 17:51 UTC (its
  pair directory held only its staged configuration, no job). The rung's host snapshots saw no
  foreign Slurm job.

## Files

- `1244/`: the job's `preflight.txt`, `apdelta-receipt.json` and `manifest.json`, and per campaign
  its `apdelta.json`, `preflight.txt` (with the batch's end line), `manifest.json`, `receipt.json`
  and `session_plan.json`. The per-trial cycle records and VM logs stay on the host
  (`~/cotcodec-runs/stage0/s2v4/apdelta-dev/runs/1244/`), as for 1217 and 1218.
- `summary.json`: `program/evidence/2026-10-11/s2v4-image/apdelta-dev/summarize.py` on a Mac copy of
  the whole job directory (cycles included), reading it with harness/q2's `acceptance` code.
- `slurm-1244.out`: the job's Slurm output.
- `manifest-rendered.json`: the manifest as rendered on the Mac.

Housekeeping: the host staging directory (the archive parts) and the local scratch copies were
deleted after the records were copied. The source export stays on the host, made read-only, beside
1217's (`~/cotcodec-runs/stage0/s2v4/apdelta-dev/src/`). Nothing was created under the Phase 0 run
root.
