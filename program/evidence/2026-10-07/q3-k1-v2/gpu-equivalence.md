# K1 v2 batched-bank GPU equivalence check (D22)

The one-GPU job that D22 pre-approves (at most 0.1 GPU-h, no evaluation data)
ran `tests/test_sparse_indexer_bank_gpu.py` on an H100 under TF32. This was
done before any probe freeze. Nothing was frozen, the throughput probe did not
run, no code was edited, and no Belebele, bundle or partition file was read.
This check comes before the registered gates and does not replace them: the
probe's tolerance arm still gates the same quantities on the real teacher.

## Identity

- Source: a fresh clean clone of `main` at `7863f3ed43c5965fdb41395212aa0f0db96e6aa3`
  on the host (`~/cotcodec-runs/stage0/k1-v2/repo-eq`). Tree `6c9fc4ba`,
  `git archive` SHA-256 `b8417b24dffa8ba106b06dd749f7aa3bef28d572eabcad6cc1db01a43737fd25`.
- Image: built by Slurm job **502** with
  `infra/slurm/host-single-node/build-architecture-image.sbatch` and
  `COTCODEC_REPO` set to that clone. The job was CPU only (16 CPUs, 64G, no GPU)
  and ended COMPLETED with ExitCode 0:0 after 00:10:20.
  - Tag: `cotcodec-research:7863f3ed-architecture`
  - Image ID: `sha256:9664eff3ac3207c5f6a6bb2bb78e4f598b3453ce34c8de3340e362ee4fd07679`
  - Digest in the local loopback registry: `sha256:5889a4f37c833b27abdee98c4eb74b6fc87634ab435e5eb3990e126df2af44e6`
  - The revision label and `/etc/cotcodec-provenance.json` match the commit
    and the source SHA-256.
  - Versions: torch 2.11.0+cu128, transformers 5.15.0, numpy 2.5.2, Python 3.12.3.
- Test job: Slurm job **516**, `--gres=gpu:h100:1`, `--time=00:06:00`, 8 CPUs,
  64G. It ended COMPLETED with ExitCode 0:0 after 00:00:16
  (17:06:47Z to 17:07:03Z UTC), on GPU index 0.
  - GPU use: 0.0044 GPU-h, under the 0.1 GPU-h cap that `--time` enforces.
  - Before submission, `squeue` showed only CPU jobs and `nvidia-smi` showed
    all 8 GPUs at 0% and 0 MiB with no compute processes. The in-job check
    found 0 foreign processes on the allocated GPU before the run and 0 after.
- Container: `docker run --gpus device=$CUDA_VISIBLE_DEVICES --network none --read-only`
  with these settings:
  - `--tmpfs /tmp:rw,exec,nosuid,nodev,size=16g`, which holds HOME, the
    Triton, Inductor and HF caches, and pytest's basetemp
  - `--cap-drop ALL`, `no-new-privileges`, `--user 1004:1004` (non-root)
  - the clone mounted read-only at `/repo`, with `legacy/` masked by an empty
    read-only tmpfs
  - `HF_HUB_OFFLINE=1`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `COTCODEC_GPU_TESTS=1`
- Code under test: the tests imported from `/repo`. Nine files have the same
  SHA-256 in `/repo` and in the image's baked `/workspace/cotcodec`: the test,
  the five harness modules, the doctor, `pyproject.toml` and `uv.lock`. The five
  harness modules match the table in `q3-k1-throughput-probe-v1`:
  - `sparse_indexer_bank` `e96653eb...`
  - `k1_equivalence_v2` `3c8b6caf...`
  - `k1_runtime` `6fbddc91...`
  - `k1_runtime_v2` `2c77c4bd...`
  - `sparse_indexer_torch` `f21301a4...`

  This is the only GPU-gated test file in `tests/`.

## Result: 3 passed, 0 failed (pytest 12.59 s)

| Test | Outcome |
|---|---|
| `test_registered_shape_bank_matches_v1_under_tf32` | PASSED (4.75 s) |
| `test_device_gates_on_a_tiny_model` | PASSED (2.03 s; `device_check` passed=True, all 8 gates True) |
| `test_selection_on_the_device_is_the_registered_rule` | PASSED (0.58 s) |

## Observed deviations against the registered TF32 tolerances (D22, v2 decision 36)

The first column is the registered-shape check: layer 15, 18 indexers, 8,192
tokens, random bf16-valued activations. The second is `device_check` on a tiny
random Qwen3: layer 2, 256 tokens, 18 slots.

| Quantity | Tolerance | Registered shape | Tiny-model `device_check` |
|---|---:|---:|---:|
| KL loss, max relative | 1e-3 | 1.28e-7 | 9.42e-8 |
| Clip norm, max relative | 1e-2 | 4.16e-7 | 1.66e-6 |
| Gradients, max relative Frobenius | 1e-2 | 6.86e-5 (wk) | 7.91e-5 (wk) |
| Adam step on identical inputs, max relative (3 steps) | 1e-6 | 0.0 (bitwise) | 0.0 (bitwise) |
| Adam step on v1's clipped gradients | bitwise reported | bitwise | bitwise |
| Chunked targets, max relative / dropped mass | 1e-4 / 0 | not run | 0.0 / 0.0 |
| Slot independence | exact | not run | bit-identical (losses and gradients), perturbed loss moves |
| Selection and U/U_k unions vs v1 on CPU | exact | not run | exact (also exact in test 3, 0 mismatches) |
| Dense recall of one unit, max abs points | 1e-3 | not run | 1.9e-6 (5 rows; indexer columns 0.0) |
| Parameters after one full step, max relative Frobenius | reported only | 2.98e-5 (gate_w) | 1.11e-5 (wq) |

Per-tensor gradient deviations at the registered shape: wk 6.86e-5, wq 1.06e-5,
gate_w 9.61e-6, k_norm 4.07e-6, q_norm 2.17e-7, gate_b 1.75e-7. The largest
ratio of observed deviation to tolerance is 7.9e-3 (gradients), so every gated
quantity is more than 100 times inside its tolerance.

## Deviations from the plain procedure (disclosed)

1. The architecture image has no pytest: the `dev` extra is not installed. The
   run used pytest 9.1.1, pluggy 1.6.0, iniconfig 2.3.0 and pygments 2.20.0 at
   the `uv.lock` versions. They were installed offline from the host's uv
   cache with `--require-hashes` against the `uv.lock` wheel hashes into
   `eq-run/pytest-overlay`, then mounted read-only and put on `PYTHONPATH`.
   The image already has pygments 2.20.0 and packaging 26.3. pytest-asyncio
   was absent, so pytest warned about the unknown `asyncio_mode` option. This
   file has no async tests.
2. The tests assert but print nothing when they pass. To report the numbers,
   pytest loaded a read-only observer plugin (`eq_observer.py`, SHA-256
   `edf11719004cbb6acba8b11121b33c5ce4d51da29038b2148db03a3ea5a252aa`). It
   registers `sys.monitoring` PY_RETURN events on six code objects only and
   wraps or replaces no function: `compare_with_v1`, `adam_check`,
   `independence_check`, `selection_check`, `device_check` and
   `eval_unit_check`. The numbers above are the return values the assertions
   saw, taken from that same single run.
3. The job ran through a one-off sbatch script (`k1v2-gpu-eq.sbatch`, SHA-256
   `427edbcc...`, container script `d2a4365d...`) as the operator task
   specified, not through `submit_docker_research_job.py`. It keeps the
   lane's isolation flags:
   - `--network none` and a read-only root
   - `--cap-drop ALL` and `no-new-privileges`
   - a non-root user
   - `--pids-limit 4096`, the Slurm cpuset, and memory equal to the Slurm
     allocation
   - the foreign GPU process check

   It differs in two ways: `/tmp` is mounted exec so the caches can live
   there, and the inner and outer deadlines are 250 s and 300 s.

Host artifacts (not committed) are in `~/cotcodec-runs/stage0/k1-v2/eq-run/`:
`pre-submit-20261007T170640Z.txt`, `slurm-k1v2-gpu-eq-516.out`, `tools/`,
`pytest-overlay/`, and `job-516/` with `observed.json`, `pytest.log`,
`junit.xml`, `job.env`, `container-preflight.txt`, `nvidia-smi-allocated.txt`
and the GPU process lists from before and after the run. The build receipt is
in `~/cotcodec-runs/builds/7863f3ed-architecture-502/`.
