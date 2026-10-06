# MemoryBank Corrected-Decay Control Audit — 2026-08-16

## Verdict

`MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING`

The clean-room corrected MemoryBank decay control repaired the historical
operator-precedence bug in a bounded Qwen3.5-4B H100 screen, but the matched
no-decay control decisively outperformed it. Do not scale this forgetting
mechanism to a larger model or broader panel. This is not an upstream
MemoryBank reproduction or a publication-ready memory-quality result.

## Registered mechanism

- Historical source: arXiv:2305.10250 and repository commit
  `cf61c4196e4cfdb0f2b7a0316249fa40312dc3a9` (MIT).
- Corrected retention: `exp(-elapsed / (5 * strength))`.
- Strength: `1 + prior explicit access count`.
- Ranking: `(1 + query-token overlap) * retention probability`.
- Negative control: the upstream Python-precedence interpretation
  `exp(-(elapsed / 5) * strength)`.
- Upper control: identical ranking without decay.

No upstream runtime code was imported. The implementation consumes only the
task prefix and does not use answer labels or suffix outcomes.

## CPU and frozen-selection evidence

Two clean, byte-identical, network-disabled arm64 container runs passed the
formula, monotonicity, probability-bound, and ranking falsifiers. The runtime
was read-only, capability-free, non-root, and used no model, provider, or GPU.

The three controls were then frozen over the same 200 generated tasks, both
treatment modes, both visibility states, K=4, top-k=4, and 256 injected-token
budget. On all-SERVE storage-and-service requests, the target was selected by:

- corrected decay: 22/200 tasks;
- upstream-precedence negative: 0/200 tasks;
- no-decay upper control: 200/200 tasks.

All holdout requests hid the candidate. This establishes a real deterministic
exposure contrast. It does not establish downstream utility.

## H100 result

The three frozen controls ran against Qwen3.5-4B with identical tasks,
assignment seeds, prompt/schema, model receipt, and decoding. Jobs 328-330 ran
in network-disabled Docker under Slurm on one H100. Preempted corrected and
no-decay cells resumed from their exact persistent checkpoints in fresh jobs
333 and 334; the completed aggregate rehashed all five jobs and their Slurm
outputs.

At the preregistered served executable-success endpoint:

- corrected minus upstream precedence: **+10.97 points**, task-clustered
  bootstrap 95% interval **[+6.15, +16.24]**;
- corrected minus no decay: **-58.39 points**, task-clustered bootstrap 95%
  interval **[-66.77, -50.00]**;
- safety failures: **0**;
- valid action rate: **1.0** in every cell.

The corrected formula therefore repairs the upstream bug on this synthetic
panel, but forgetting itself removed useful evidence. A larger-model rerun of
this exact mechanism is killed. A future forgetting study needs a materially
different, preregistered capacity or staleness tradeoff and must first beat
no decay at matched bytes, reads, actor, assignments, and tuning budget.

The result remains `scientific_result=false` and `publication_ready=false`:
the source archive captured a dirty development tree, the task panel is
synthetic, and summary/personality generation from the original system was not
implemented.

## Evidence

- CPU root: `data/results/memorybank-decay/2026-08-16-local-docker-v1`
- Frozen controls: `data/results/memorybank-decay/frozen-controls-v1`
- H100 root: `data/results/infrastructure/memorybank-h100-source-2026-08-16-v3`
- Aggregate: `data/results/infrastructure/memorybank-h100-source-2026-08-16-v3/aggregate-report.json`
- Aggregate file SHA-256: `8a7e377b4906fa4e58e3929a45c950ee2657a439fe50724e634c55dc981e09aa`
- Aggregate semantic SHA-256: `27044eb244fc35d9c5e2fea3641489633045f0b511ac9463d0d2fcccb72a583f`
- Receipt: `research/evidence/memory/memorybank-h100-actor-v1.json`
- Validator: `scripts/validate_memorybank_h100_evidence.py`
