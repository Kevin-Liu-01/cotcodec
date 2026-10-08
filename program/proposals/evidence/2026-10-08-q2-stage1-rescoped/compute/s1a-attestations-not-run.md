# S1a compute attestations: not run

No S1a job has run. The S1a image (cu129 overlay rebuilt from the S1a commit),
its manifests, the submitter dry-run and test-only records, a container smoke
and an orx `slurm-manifest` node do not exist yet. They are produced by O1 and
A0a after the G0 items (preregistration section 3) and a decision admitting
the pre-freeze development jobs.

The cost basis is `serving-throughput-probe-v2` job 466, whose attestations
are committed under `program/evidence/2026-10-07/serving-throughput-probe-v2/`
(manifest `manifests/a.yaml`, dry-run `manifests/a.dry-run.json`, provenance
`jobs/a-466/provenance-verification.txt`, image receipt
`overlay/build-receipt.json`). They attest the engine and lane S1a reuses, not
an S1a run.
