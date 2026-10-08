# Q1 gate doctor (CPU) execution record

The CPU doctor is a "local container" execution (infra/README.md): pinned
image, no GPU, no network, no Slurm. The Docker GPU lane cannot host it (the
submitter requires at least one GPU, and the doctor refuses to run when a GPU
is visible, because its synthetic Triton fixtures are CPU-only under D3).

Command used on fal-h100-01 (scratch under ~/cotcodec-runs/stage0/q1-core):

    docker run --rm --user "$(id -u):$(id -g)" --network=none --cpus 32 --memory 96g \
      -e NVIDIA_VISIBLE_DEVICES=void -e CUDA_VISIBLE_DEVICES= -e USER=q1 -e HOME=/tmp \
      -e TRITON_CACHE_DIR=/tmp/triton -e TRITON_INTERPRET=1 \
      -e KERNELGYM_SRC=/upstream/KernelGYM -e PYTHONPATH=/work \
      -v "$CHECKOUT:/work:ro" -v "$OUT:/out" -v "$UPSTREAM_CLONES:/upstream:ro" \
      -w /work --entrypoint python cotcodec-research:0b3ecef0-architecture \
      scripts/run_q1_gate_doctor.py --output /out/doctor-RUN_ID (a fresh directory) --slots 12

Image: cotcodec-research:0b3ecef0-architecture,
ID sha256:3804466639c13f132be4b0369de4d3395b9d5ea2d3dc100cd38884c75197fe29.
`$UPSTREAM_CLONES/KernelGYM` is an unmodified clone at
3a84417f8c0efaadb215ef638b37d12e71ed20f3 used only for the b1 differential.
