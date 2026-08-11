# Tinker managed-training profile

Tinker is the managed LoRA backend for the capsule-policy infrastructure study,
not the program's research direction. It does not
replace the capsule runtime and it does not make arbitrary architecture surgery
possible. The fixed external capsule remains the portable object; Qwen and Kimi
receive separate model-specific LoRAs.

The client is pinned to `tinker==0.23.3`. As verified on 2026-08-10, Tinker
advertises `Qwen/Qwen3.5-4B` and `moonshotai/Kimi-K2.6`; the latter has a 32K
training context. Prices and token ceilings are frozen in
`experiments/tinker/capsule-policy-kimi.yaml` rather than read dynamically after
the result is known.

## Local contract checks

```bash
uv sync --extra tinker --extra dev
uv run --extra tinker python scripts/tinker_doctor.py \
  experiments/tinker/capsule-policy-kimi.yaml
uv run --extra tinker python scripts/run_tinker_training.py \
  experiments/tinker/capsule-policy-kimi.yaml \
  --stage qwen-interface-smoke --seed 42 --dry-run
```

An authenticated capability receipt is a separate gate:

```bash
export TINKER_API_KEY=... # obtain through the Tinker console; never commit it
uv run --extra tinker python scripts/tinker_doctor.py \
  experiments/tinker/capsule-policy-kimi.yaml \
  --online --output data/tinker-capabilities.json
```

The doctor records model names and context limits, never the credential. The
contract is still disabled until its dataset, adapter, image, and resume gates
are complete.

## Dataset and training contract

Training records are strict JSONL objects:

```json
{"example_id":"...","prefix":"<fully rendered prefix>","target":"<assistant action>"}
```

The renderer revision and complete JSONL SHA-256 are registered before
execution. The runner rejects extra fields, duplicate IDs, target boundaries
that change prefix tokenization, unregistered seeds, unregistered model stages,
and any token budget overrun.

Each run saves both checkpoint kinds:

- full `weights/...` state for optimizer-preserving resume;
- `sampler_weights/...` for evaluation and final archive download.

The local resume receipt binds the contract, stage, model, seed, epoch, cursor,
token ledger, and remote checkpoint paths. Periodic checkpoints expire after
two hours; interrupted and final checkpoints expire after seven days. A signal
checkpoint writes the Slurm marker only after the remote full state and local
receipt are durable.

## Slurm rule

Tinker owns the remote GPUs; Princeton owns the reproducible CPU client. Build
the same research image with `UV_EXTRA=tinker`, inject `TINKER_API_KEY` through
the cluster's secret mechanism, and submit a CPU-only Pyxis job:

```bash
cp infra/tinker/job-manifest.example.yaml /tmp/cotcodec-tinker.yaml
uv run python scripts/submit_tinker_job.py /tmp/cotcodec-tinker.yaml --dry-run
uv run python scripts/submit_tinker_job.py /tmp/cotcodec-tinker.yaml --test-only
uv run python scripts/submit_tinker_job.py /tmp/cotcodec-tinker.yaml
```

The submitter rejects local GPU requests, embedded credentials, mutable images,
contract traversal, fewer than three seeds, non-finite budgets, and jobs above
the $50 safety ceiling. The registered pilot declares $6 and estimates a
worst-case token-plus-storage charge of $5.2823. This is not a service-side
spending lock: the runner stops local token submission, TTLs bound storage
duration, and delayed Tinker billing usage must be reconciled afterward.

Run Qwen first. Kimi may start only after the Qwen job proves online capability
discovery, one update, full-state checkpoint, process exit, fresh-client
optimizer resume, sampler evaluation, and downloaded adapter hashing.

Primary documentation:

- https://thinkingmachines.ai/tinker/
- https://tinker-docs.thinkingmachines.ai/tinker/quickstart/
- https://tinker-docs.thinkingmachines.ai/tinker/data-model/
- https://tinker-docs.thinkingmachines.ai/tinker/models/
