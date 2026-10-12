# q2-stage1-successor-e-v1 (successor E): OE and the E jobs, from 2026-10-12

Frozen registration `q2-stage1-successor-e-v1` (ledger row 19, file SHA-256
`47e65877aed069fe919d1a2976345b3d5755e4323a71b47f99ece61c6e2ae98b`, row hash
`0da0a6825c8aad1b0db085f13adef5febb2661bced7e676156c88e009d521ba2`, frozen
2026-10-12T01:02:32Z). Everything here runs from E's freeze commit
`f6144d6bf745d944cb016cfc2b9894e1dbf7eb66` (tree `b8d37e7f4bdb4a54593447b68524b34b309cd4a5`),
the commit that adds the row, never its parent (`7fcf0a4a`, the row's `git_head_at_freeze`).
One operator per session, in the registered order (section 5.3): OE, then E-9B-E1 and
E-4B-E1 (session E1), then the later sessions, each at least 12 h 5 min after the previous
session's later end.

This README is extended per session. It reads infrastructure fields only (statuses, losses,
re-queues, completeness, observation and restart counts, Slurm and engine records): **no
score, success rate or harness comparison is computed here**. The registered analysis
(section 18) runs after the last E job.

## Jobs

| Job | What | Resources | Outcome | Physical GPU-h | Charged (D22) |
|---:|---|---|---|---:|---:|
| 1215 | OE: cu129 overlay build from the freeze commit | 1 H100, 8 CPUs, 32 GB, 3 min | COMPLETED 0:0 in 57 s (02:01:30-02:02:27 UTC, 2026-10-12); overlay `sha256:5d1d4d8f1ff4a92cc607704b5e8e9adaa0269b8fa27757d6fe51616e438584ef` | 0.0158 | 3 min |

Job ids 1213, 1214 and 1216 are other workstreams' (R03 part (b)'s rehearsal 1213, S2 v4's
development smoke 1214, R04's score job 1216); none was in the queue when OE was submitted or
while it ran.

## Source and the frozen registration

- The read-only export `~/cotcodec-runs/stage0/q2-stage1e/src/f6144d6bf745d944cb016cfc2b9894e1dbf7eb66/`
  on the host is `git archive f6144d6b` (tar SHA-256
  `21eaa6b279805b3b000c44c2bb4270c521a2ae1c4c4d0e08c50f1806f41f9339`) plus a `.git_sha` file
  naming the commit (as in the G-E4 export; the VM lane's preflight reads it), made read-only
  (`chmod -R a-w`). Its file list equals the commit's `git ls-files` (7,629 entries), and its
  contents equal a clean clone of the commit file for file (`diff -r`).
- A git bundle of the operations branch at `f6144d6b` (SHA-256 `a041499f...`) was copied to the
  host and cloned; the clone `oe/checkout-f6144d6bf745` is detached at `f6144d6b`, `git status`
  empty, tree `b8d37e7f...`. OE ran from the clone; every E job runs from the export.
- `scripts/preregister.py verify q2-stage1-successor-e-v1` and `check-chain` passed in the
  export and in the clone before OE (`oe/preregister-verify.txt`, 01:07:39 UTC: row 19, file
  SHA-256 `47e65877...`, 19 rows, PASS), and again in the export right before each pair was
  submitted (`*/pair/preregister-verify.txt`). E's lane makes the same check itself at
  `validate`, `submit` and job start (`lane.frozen_registration`).
- Every file of section 23's two tables (E's 11 files and the 8 infrastructure files) has the
  registered SHA-256 in the export, as do S1a's GPU template and docker submitter.
- Interpreters, as in S1a: `scripts/preregister.py` under the host's uv-managed CPython
  3.12.13 (it needs `datetime.UTC`); the renderers, lane, submitter, DR0 and the checks under
  the system Python 3.10 with `-E -s -B`, the interpreter `q2e-vm.sbatch` runs the lane with.

## OE (`oe/`)

- **Source archive**: `scripts/create_source_archive.py --discovery` in the clean clone with
  the default ref `HEAD`: SHA-256
  `6ad9ad67e825dbc99f4c0fbb7fab25d19caee25a8f17ec7ab8495695f63e2a4f`, 7,602 files,
  `selected_ref: HEAD`, `worktree_clean: true`, git tree `b8d37e7f...`
  (`source-receipt-head.json`, SHA-256
  `84e76f95c0469f65dcd5f092da4ba1ebe7e2fea46ba8513c2da13e90d47fec64`).
- **CPU pre-check** (S1a's O2 step, so that OE's one retry could not be spent on a receipt
  error like job 1032's): the pinned extractor (`9b4d21a8...`) validated that archive and
  receipt into an empty scratch directory with the expected commit and tree
  (`precheck-source-validation.json`: `VALIDATED_DISCOVERY_SOURCE`, 7,602 members); the base
  image's ID (`sha256:423783aa...`) and its commit label (`db9527a4...`) were checked. No GPU.
- **Job 1215** (`ops/oe-wait-submit.sh oe`): `sbatch` of the clone's
  `scripts/build_vllm_overlay_on_h100.sh` (builder `aa43283e...`, extractor `9b4d21a8...`:
  section 23's, S1a's O2's), one H100, 8 CPUs, 32 GB, `--time=00:03:00`, `--no-requeue`,
  submitted at 02:01:28 UTC by a loop that polls `squeue` every 2 s and calls `sbatch` only on
  an empty queue (`ops.log`: queue empty, every GPU at 0 MiB). It ran 02:01:30-02:02:27,
  **COMPLETED 0:0 in 57 s** (`slurm-state-1215.txt`); the 5-second queue watcher saw only job
  1215 while it ran (`squeue-watch.log`).
- **Build receipt** (`build-receipt.json`, SHA-256
  `b8f36411bf44cb1975cf2aafef4af6e574fa48da2d3473bf471aa77fcced17c9`): provenance **PASS**
  (`git_sha` `f6144d6b...`, `source_sha256` `6ad9ad67...`), base
  `vllm/vllm-openai@sha256:b18abb2d...` (vLLM 0.31.0, `db9527a4...`), torchcodec removed as
  in O1 and O2, the vLLM argument doctors pass, tag `cotcodec-vllm:6ad9ad67-cu129-overlay`,
  **overlay `sha256:5d1d4d8f1ff4a92cc607704b5e8e9adaa0269b8fa27757d6fe51616e438584ef`**; the
  image's labels carry revision `f6144d6b...` and source-tree digest `6ad9ad67...`.
- The OE retry was not needed; its 3 minutes stay unspent (section 7.2). Every E GPU half
  names this overlay, the freeze commit and this archive (`gpu-values.json`), and its container
  refuses to start unless the overlay's embedded `git_sha` and `source_sha256` equal its
  manifest's (G-E7).

## Session E1

E-9B-E1 waits for a quiet host (section 6.4): R04's job 1216 (32 CPUs, no GRES, a 4 h 41 min
limit) started at 02:02:32 UTC, five seconds after OE ended, and held the queue at every
check since; nothing of E's was submitted while it ran (`e-9b-e1/pair/ops.log`, `wait.log`).

## Operator scripts (`ops/`)

None is code of record; none runs inside a job. Each was copied to the host's
`~/cotcodec-runs/stage0/q2-stage1e/e-ops/` (read-only) and run from there; the SHA-256s there
equal the committed files'.

| Script | What |
|---|---|
| `oe-wait-submit.sh` | OE: checks the clean clone, the builder's and extractor's digests and the archive, waits for an empty queue (2 s polls, at most about 200 s per invocation), submits the build, starts the end-state and queue watchers |
| `submit-pair-e.sh` | one E pair: S1a's `submit-pair.sh` with E's registration, lane, renderer and paths; verify and `check-chain`, `lane validate`, `lane submit --dry-run`, a placeholder GPU half through the submitter's `--dry-run`, an empty-queue wait (at most about 180 s), the VM job, the GPU half rendered from the validated VM manifest with the VM job's id, the submitter's dry run, `--test-only`, a foreign-queue check, the GPU job (`--dependency=after:` the VM job), the watchers |
| `wait-then-submit-pair-e.sh` | polls the queue (2 s, at most about 200 s per invocation) and runs `submit-pair-e.sh` only once it is empty; one line per busy invocation in the pair's `wait.log` |
| `collect-pair-e.sh` | after a pair: the registered DR0 command (section 18 (iii) step 1), raw SHA-256 listings of both run directories, and the evidence subset |
| `job_checks_e.py` | after a pair: the lane's checks re-read from its records (provenance, model verification, engine argv, Slurm limit and USR1 point, receipt, counts, losses, completeness against the plan, restarts, observations, devices, teardown, the session end by `lane.job_end`, physical run times); infrastructure fields only |

## Disclosures

- **The export's `.git_sha`.** The export adds one file to `git archive f6144d6b`: `.git_sha`,
  naming the commit, as the G-E4 export did; `q2e-vm.sbatch`'s preflight prints it. The lane's
  source-tree digest covers `harness/` only.
- **Deviations from the registration:** none so far.
