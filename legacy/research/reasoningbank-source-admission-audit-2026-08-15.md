# ReasoningBank source-admission audit — 2026-08-15

## Verdict

The exact open release is a useful procedural-memory prior, but its released
drivers are not admissible as a frozen held-out comparison. Status:
`BLOCKED_MUTABLE_EVALUATION_AND_UNPINNED_RETRIEVAL`. No provider call, model
inference, GPU, Slurm job, or sudo operation was performed.

This is a source and experimental-contract result, not a reproduction of the
paper's memory-quality claims.

## Immutable source

- Repository: <https://github.com/google-research/reasoning-bank>
- Commit: `ed80611788292ea739f1effd31f16c53823b8a0d`
- Tree: `7cc5e6e08ee8035cde81f1fb9fd871d32423a3e3`
- Deterministic Git archive SHA-256:
  `d85d169c84f82782cefc50044adc192ab1d28956f36e177de0bf213d48298e09`
- License: Apache-2.0, file SHA-256
  `58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd`
- `uv.lock` SHA-256:
  `6835cc5149faf4ddd573cae98851bbd5db6844a1bed567fe8a85525d862d77fa`
- Registered contract:
  `experiments/memory/stage3-reasoningbank-source-admission-doctor.yaml`

## What the release implements

ReasoningBank turns successful and failed trajectories into procedural text
items, retrieves the top item for a later task, and injects it into the agent's
system prompt. It is best classified as an episodic-to-procedural consolidation
and retrieval controller. It is not a persistent CRUD provider, active/inactive
pager, or item-level causal-credit estimator.

## Admission blockers reproduced from the pinned source

1. **Provider and model identity are not offline or immutable.** WebArena
   initializes Vertex AI and a GenAI client at module import
   (`WebArena/memory_management.py:31-38`). Both WebArena and the vendored
   SWE-Bench path load `Qwen/Qwen3-Embedding-8B` without a revision
   (`WebArena/memory_management.py:59-63`) or call mutable
   `gemini-embedding-001` endpoints.

2. **Evaluation changes later evaluation inputs.** WebArena loads the existing
   retrieval cache and then appends the current evaluation query
   (`WebArena/memory_management.py:172-213`). Its main pipeline runs inference,
   evaluates the same trajectory, and immediately appends newly induced memory
   before moving to the next task (`WebArena/pipeline_memory.py:47-86`). That is
   an order-dependent online-learning estimand, not a frozen held-out bank.

3. **The SWE-Bench lane has shared concurrent mutation.** Each worker reads one
   shared model-named bank/cache, appends the query during selection, and appends
   a judged memory item after the task
   (`third_party/src/minisweagent/run/extra/swebench.py:176-245`). Multiple tasks
   execute in a `ThreadPoolExecutor` (`:328-348`), but the append-only bank and
   cache do not have an equivalent transaction or ordering contract.

4. **The scaling driver does not represent its requested trials.** It launches
   `results_0 ... results_n`, but passes only the final loop variable's result
   directory to induction (`WebArena/pipeline_scaling.py:42-78`). The induction
   loop then rereads that same directory for every sample. It also labels
   `reward == 0` as `success` and nonzero reward as `fail`
   (`WebArena/induce_scaling.py:168-196`).

5. **Trajectory and artifact handling is not publication-safe.** WebArena
   induction unpickles trajectory files, silently skips arbitrary extraction
   exceptions, samples procedural items at temperature 1.0 without a seed, and
   appends JSONL directly (`WebArena/induce_memory.py:47-67,145-186`).

The executable source doctor hashes all critical files and requires those
findings to remain true. Any upstream change fails closed and requires a new
review rather than inheriting this verdict.

## Smallest honest patch arm

Create one additive CoTCodec adapter; do not modify or relabel upstream:

1. Build the procedural bank from train workflow families only, then seal it.
2. Build and seal the retrieval index before dev/test; evaluation never writes
   to either artifact.
3. Use a revision-pinned offline embedder with exact tokenizer, weight, pooling,
   and artifact receipts; provider clients cannot initialize at import.
4. Replace pickle trajectories with a strict versioned JSON schema and reject
   malformed or incomplete steps.
5. Compare no memory, raw success trajectory, raw failure trajectory,
   success-only procedural items, failure-only items, shuffled items, and the
   combined ReasoningBank arm under identical actor, reflection, token, call,
   and retrieval budgets.
6. Split by workflow family, not row or task order. Tune on dev and open test
   exactly once.
7. Make bank/index construction atomic and idempotent; bind every item to its
   source trajectory, correctness receipt, generator model, decoding, and cost.

Only after that adapter passes a network-disabled CPU retrieval/restart doctor
may a bounded H100 actor cell be considered.

## Additive frozen-bank contract result

The framework-owned portion of that patch arm now passes a contained CPU
contract. This does not change the release-driver verdict above.

- `harness/memory_trials/procedural_bank.py` owns a content-addressed exact
  train/dev/test task-to-family manifest, TRAIN-only item lineage, immutable
  actor-visible `procedural_text` document vectors, query-only embedding,
  deterministic ranking, injection budgeting, and retrieval receipts. Hidden
  `source_query` lineage is not embedded.
- The real pinned `BAAI/bge-small-en-v1.5` revision
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` ran in image
  `sha256:d3f7858e...`, using the SHA-pinned Torch 2.11 CPU wheel.
- Two fresh named containers were inspected before and after execution. Both
  used network `none`, a read-only root, all capabilities dropped,
  `no-new-privileges`, no device requests, four CPUs, 4 GiB, and read-only model
  and receipt mounts.
- Both runs achieved 6/6 expected fixture top-1 retrievals and produced
  byte-identical bank, manifest, report, and retrieval artifacts. Repeated
  freezes and queries were exact; TRAIN-task and mismatched task/family probes
  failed closed.
- The host now requires that exact image ID, parses strict one-record-per-line
  JSONL, and independently verifies the registered query/oracle roster, bank
  lineage, retrieval digests, top-one hits, source receipts, and token budgets.
- The train/dev/test fixture now uses distinct canonical workflow families,
  rejects split-suffixed family aliases, and retains the exact hand-authored
  trajectory, correctness, and generator artifacts behind every synthetic
  lineage hash. These are explicitly not real ReasoningBank trajectories.
- The portable evidence directory retains the core artifacts, model receipt,
  both execution receipts, and both Docker inspect records; the experiment
  validator recomputes their hashes and receipt chains.
- Evidence:
  `research/evidence/memory/reasoningbank-frozen-bank-cpu-v1.json`, SHA
  `c6f6d6284bcbd9afd8bb0d5e4658b2b892d9679a3614fa4a10169a878c98c994`.

The procedures and tasks are synthetic fixtures. No upstream trajectory was
induced, no actor or matched control ran, no agent success was measured, and no
Slurm/H100 or publication attestation exists. A separate CPU-only compiler now
accepts only canonical TRAIN JSONL, an externally pinned split-manifest digest,
complete task coverage, bound correctness receipts, and two byte-identical
contained generation responses under one dataset/evaluator/generator contract.
It has no registered real input yet. The next gate is to pin a real trajectory
artifact and split, run the contained generator twice, then freeze that bank
before the full control matrix on held-out workflow families.
