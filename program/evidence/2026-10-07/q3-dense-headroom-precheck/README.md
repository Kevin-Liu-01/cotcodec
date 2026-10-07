# q3-dense-headroom-precheck-v1: build evidence (pre-freeze)

Build-time checks of the draft registration
`program/preregistrations/q3-dense-headroom-precheck-v1.md` (program decision
D26). The registration is not frozen; no GPU job of this experiment has run
and no Belebele, FineWeb or K1-bundle content was read. Every number in these
files is synthetic.

| File | What |
|---|---|
| `doctor-cpu-image-e59d9cc1.json` | `scripts/run_dense_headroom_precheck_doctor.py` receipt: DENSE_DOCTOR_PASS, all seven cases (codecs, features, derive, statistics, selectors, multiple choice, end to end on both tiny lanes with an interrupt and its continuation); `code_sha256` gives the digests it ran, equal to the draft's code table |
| `doctor-cpu-image-e59d9cc1.log` | its console log |
| `pytest-torch-image-e59d9cc1.log` | the torch-dependent tests of this experiment in the same image |
| `run-in-image.sh` | how both ran: the research image `sha256:e59d9cc18c0db05fa0ae20a0f65492268112d07fef20f00af799323ae02ce6d3` (torch 2.11.0, transformers 5.15.0, flash-linear-attention 0.5.2), a CPU-only Slurm step, `docker run --network none` without GPUs, the branch's worktree mounted read-only; pytest from the lock-pinned overlay built for the K1 v2 equivalence run |

The doctor in the image built for the registration (step 3 of the freeze
procedure) is the binding one; these runs show the code executes before the
freeze.
