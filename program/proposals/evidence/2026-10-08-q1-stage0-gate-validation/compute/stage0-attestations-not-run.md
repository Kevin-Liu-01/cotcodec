# Q1 Stage 0: compute attestations that do not exist yet

Recorded 2026-10-08 by the gauntlet wave-1 synthesis owner.

The registered Stage 0 run (`q1-stage0-gate-validation`, trim rule `q1-stage0-trim/2`, execution
policy `q1-stage0-exec/2`) has no container smoke run, no Slurm dry-run or test-only run of its own
scoring manifest, and no provenance verification of its own image. None can exist while the
registration is unfrozen: the Stage 0 image is built only from the frozen revision, and the scoring
manifest (`experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml`) is filled from that image.
The registration is not frozen because Stage 0 is not admitted under decision D31: through bucket P3
the D37 validation job's primary projection is 19.99 GPU-h central and 24.66 high against an 8 GPU-h
cap (decisions D31, D37; admission is Kevin's ruling under D24).

What does exist is listed under `supplementary_attestations` in `bundle.json`: the D37 validation job
(Slurm 752, branch `stage0/q1-exec2-validation` at 13f3180) ran the registered gate, audit and driver
code (version-card hashes equal to registration section 2.1) under `q1-stage0-exec/2` on one H100,
inside an image built by CPU-only Slurm 746 from a fresh clean clone, through the Docker lane's
submitter (dry-run, test-only exit 0, one submission), with provenance verification PASS, an exclusive
GPU prolog and termination `completed`. It is infrastructure and cost evidence, not a Stage 0 result,
and it is not an orx experiment node.
