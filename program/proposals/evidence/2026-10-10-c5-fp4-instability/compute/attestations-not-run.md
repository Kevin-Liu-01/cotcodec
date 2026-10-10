# C5 FP4 instability v1: compute attestations that do not exist yet

Written 2026-10-10 by the gauntlet's single synthesis owner. This file is the
honest target of the bundle's `container_smoke`, `slurm_test` and
`provenance_verification` records.

- **Real model loop:** none. The repository has no language-model pretraining
  loop: no Llama-shape model, no AdamW and schedule driver, no checkpoint and
  resume (including the stochastic-rounding generator state), no evaluation.
  `scripts/fla_throughput_doctor.py` measures GDN shapes only.
- **Fake-quant kernels:** none in project code. `compute/crest_prediction.py`
  is a numpy reference quantizer for the registered rules, used only for the
  CPU prediction N2. It is not the GPU path and has not been tested against an
  independent reference (gfloat, ml_dtypes, microxcaling, the TransformerEngine
  NVFP4 reference).
- **Benchmark adapter:** none. FineWeb-Edu sample-10BT files 000 and 001
  (revision 87f09149..., 2,152,819,114 and 2,152,222,432 B) are not on the host,
  and no tokenized shards exist. The download needs Kevin's OK; tokenization is
  a host CPU job and waits for the quiet-host rule.
- **Image:** the architecture image
  `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
  (torch 2.11.0+cu128, Triton 3.6.0, ml_dtypes present; gfloat, torchao and
  TransformerEngine absent; asset cell) holds no C5 code. The Dockerfile copies
  the source tree, so a rebuild at the freeze commit is needed (a CPU Slurm job).
- **Container smoke:** not run.
- **Slurm dry run / test-only:** not run; no manifest exists.
- **Provenance verification:** not run.
- **Executable pilot:** none. N1, N2, D1, S1 and S2 (`compute/*.py`) are CPU
  design evidence on the development Mac, not a pilot, and none is an orx node.
  The first executable pilot would be a `kind: cpu-doctor` orx node running a
  registered `scripts/run_fp4_quantizer_doctor.py` (conformance of the
  reference quantizer against gfloat and ml_dtypes, metamorphic and containment
  tests); the second the J0 GPU-conformance manifest through the Docker
  submitter.

Host state when this was written: `squeue` empty and all eight GPUs at 0 MiB
(read-only ssh, 2026-10-10T21:21:22Z). No host job was submitted by this
gauntlet's synthesis.

The deterministic research-direction doctor therefore reports FAIL, which is
the expected and honest state.
