# q3-dense-headroom-precheck-v1: build evidence (pre-freeze)

Build-time checks of the draft registration
`program/preregistrations/q3-dense-headroom-precheck-v1.md` (program decision
D26). The registration is not frozen; no GPU job of this experiment has run
and no Belebele, FineWeb or K1-bundle content was read. Every number in these
files is synthetic.

| File | What |
|---|---|
| `doctor-cpu-image-e59d9cc1.json` | `scripts/run_dense_headroom_precheck_doctor.py` receipt: DENSE_DOCTOR_PASS, all seven cases (codecs, features, derive, statistics, selectors, multiple choice, end to end on both tiny lanes with an interrupt and its continuation); `code_sha256` gives the digests it ran, the draft's code table at 9f9e735 (before the review fix pass) |
| `doctor-cpu-image-e59d9cc1.log` | its console log |
| `pytest-torch-image-e59d9cc1.log` | the torch-dependent tests of this experiment in the same image |
| `run-in-image.sh` | how both ran: the research image `sha256:e59d9cc18c0db05fa0ae20a0f65492268112d07fef20f00af799323ae02ce6d3` (torch 2.11.0, transformers 5.15.0, flash-linear-attention 0.5.2), a CPU-only Slurm step, `docker run --network none` without GPUs, the branch's worktree mounted read-only; pytest from the lock-pinned overlay built for the K1 v2 equivalence run |

## Review fix pass

The draft was reviewed and nine findings were fixed (`program/log.md`,
2026-10-07, "review fix pass"). The same checks were re-run on the fixed code
in the same image, from the branch's worktree rsynced to its own scratch root
(Slurm CPU steps, `--network none`, no GPU):

| File | What |
|---|---|
| `doctor-cpu-image-e59d9cc1-fix1.json` | the doctor receipt on the fixed code (ops tag `doctor-fix2`): DENSE_DOCTOR_PASS, all seven cases; the end-to-end runs now use the batch environment (`COTCODEC_OUTPUT_DIR` with each job's `manifest.json`), the continuation names its predecessor with a resume receipt, and the same continuation without the resume receipt exits 2; `code_sha256` equals the fixed draft's code table |
| `doctor-cpu-image-e59d9cc1-fix1.log` | its console log |
| `pytest-dense-image-e59d9cc1-fix1.log` | all seven dense test files in the same image (ops tag `pytest-fix2`, with the K1 v2 pytest overlay) |
| `pytest-host-dev-fix1.log` | ruff, the full test suite and both validators in the host's locked dev environment |
| `run-in-image-fix1.sh` | `run-in-image.sh` with the fix pass's own scratch root |

The doctor in the image built for the registration (step 3 of the freeze
procedure) is the binding one; these runs show the code executes before the
freeze.
