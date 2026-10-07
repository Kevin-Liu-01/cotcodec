# K1 v2 screen: compute attestations that do not exist yet

Recorded 2026-10-07 by the wave-1 synthesis owner.

The registered screen (q3-k1-localization-screen-v2) has no container smoke run, no Slurm dry-run or
test-only run of its own manifests, and no provenance verification of its own image. These cannot exist
while the registration is unfrozen: image B2 is built only from the commit holding the frozen file and
its ledger row, and the manifests are filled from that image and the probe-derived limits. The
registration is not frozen because its caps total 8.05 GPU-hours with the probe, over the 8 GPU-hour
threshold (program decisions D22 and D24).

What does exist is listed under supplementary_probe_attestations in bundle.json: the throughput probe
(job 543, PROBE_COMPLETE) ran the tabled v2 code's training and evaluation loops on the real
Qwen3-0.6B-Base teacher on an H100 inside the digest-pinned probe image, through the Docker Slurm lane,
with provenance verification PASS, a submitter dry-run and test-only exit 0, and ORX_RESULT exit=0.
Both K1 CPU doctors passed in that image (Slurm 534 and 536).
