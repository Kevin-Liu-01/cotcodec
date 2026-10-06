# Architecture Experiment Methodologies

**Date:** 2026-08-10
**Status:** executable research contracts; blocked experiments remain explicitly disabled
**Normative configs:** `experiments/architectures/*.yaml`
**Model inputs:** `models/registry.yaml`

## What changed

The architecture portfolio is no longer a list of mechanisms followed by a GPU
estimate. Every promoted direction now has:

- immutable upstream model identities and a receipt-producing downloader;
- an explicit claim type separating checkpoint attachment from causal
  architecture comparison;
- train/development/sealed-test identities and contamination tests;
- matched controls, one primary endpoint, a minimum worthwhile effect, and
  kill conditions;
- a finite GPU ceiling, persistent checkpoint requirements, and an honest list
  of blockers;
- required per-example predictions, compute ledgers, and restore evidence.

Passing the contract validator means the methodology is internally complete.
It does **not** mean the workload is implemented or pilot-ready. A contract is
runnable only when `execution.enabled: true`, the image is digest-pinned, every
model has a full verified receipt, and the command is fixed as JSON argv.

## Common model-acquisition protocol

Use persistent project or scratch storage; never download the only copy into
node-local `/tmp`.

```bash
export COTCODEC_MODEL_ROOT=/persistent/cotcodec/models
uv sync --extra architecture
uv run python scripts/fetch_open_model.py list
uv run python scripts/validate_architecture_experiments.py
```

Inspect a large or custom-code checkpoint without downloading weights:

```bash
uv run python scripts/fetch_open_model.py fetch kimi-linear-48b-a3b-base --metadata-only
uv run python scripts/fetch_open_model.py fetch llada-8b-base --metadata-only
```

Run the smallest complete loader test:

```bash
uv run python scripts/fetch_open_model.py fetch smollm2-135m
uv run python scripts/fetch_open_model.py verify smollm2-135m
uv run python scripts/smoke_open_model.py smollm2-135m
```

The fetcher resolves the registered 40-character Hub commit, downloads locally,
hashes every artifact, and atomically writes a receipt. The smoke loader is
offline-only, calls `trust_remote_code=False`, checks finite logits and a
deterministic generation, and binds the result to the artifact-root hash.

Ollama aliases remain useful for the Mac Mini agent loop:

```bash
uv run python scripts/fetch_open_model.py fetch ollama-qwen3-0.6b
```

They are deliberately marked non-publication because a tag can move. A positive
Ollama result must be rerun from an immutable Hugging Face snapshot or another
content-addressed artifact before it enters a paper.

### Model ladder

| Stage | Models | Purpose | Scientific status |
|---|---|---|---|
| CPU/local loader | SmolLM2-135M | end-to-end download, hash, load, forward, trace | publication-capable input |
| Cheap Transformer | Qwen3-0.6B Base | multilingual and sidecar base | publication-capable input |
| Cheap recurrence | Mamba-130M HF | recurrent interface and state control | publication-capable input |
| Delta checkpoint | FLA DeltaNet 1.3B | coded-state retrofit screen | blocked on model license resolution |
| Hybrid scale cell | Kimi Linear 48B-A3B Base | KDA/attention/MoE operator diversity | blocked on custom-code review and 8-H100 load proof |
| Byte model | BLT-1B | byte-patch interface and checkpoint continuation | gated, CC-BY-NC research use only |
| Diffusion LM | LLaDA-8B Base | bidirectional plan repair | blocked on custom-code review |
| Image diffusion | SDXL Base 1.0 | Diffusers/container/vision pipeline smoke | not a language-plan baseline |

The official Kimi Linear checkpoint is 48B total parameters, 3B activated, with
20 weight shards and custom modeling/tokenizer code. It is not a laptop model.
Metadata review comes first; only the cluster may download the complete snapshot.

## Interpretation rule: retrofit versus architecture

1. A **retrofit screen** freezes or largely preserves a pretrained model and
   attaches a sidecar, state decoder, objective, or LoRA. It answers whether the
   mechanism can add value to that trained system.
2. A **matched from-scratch arm** trains intervention and control with identical
   bytes/tokens, tokenizer, optimizer, schedule, parameter envelope, seeds, and
   evaluation. Iso-parameter, iso-FLOP, and iso-wall-time views are all reported.
   This is the minimum design for a causal architecture claim.

Pretraining can already encode retrieval or language invariances. Therefore a
retrofit win is never evidence that the architecture would have learned better
from scratch. The contract validator rejects an `architecture-causal` proposal
without a matched from-scratch arm and control.

## Method A: Coded Delta Memory

### Phase A0 — algebra and causality, no language model

Implement the registered fixed `(k=4,r=2)` real-valued systematic code over six
independently projected delta-state blocks. Before training a model, test:

1. exact reconstruction with no corruption;
2. every single-block erasure and corruption location;
3. failure behavior for two-block and correlated errors;
4. causal order by perturbing the first input and verifying no target is read
   before its write;
5. ledger equality for state bytes, projections, parity, six candidate decodes,
   and cache metadata.

The decoder threshold is selected once on development episodes. It may not be
retuned per load ratio or test condition.

### Phase A1 — deterministic MQAR mechanism screen

Generate ordered multi-token values, duplicate and near-duplicate keys, updates,
deletes, contradictions, and early/middle/late targets. Freeze three disjoint
seed ranges. Train three seeds for:

- ordinary multihead DeltaNet;
- wider-head DeltaNet at equal total state bytes;
- six uncoded replicas;
- coded state with correction disabled;
- coded state with syndrome-guided correction;
- a bounded exact-cache control whose metadata and read costs enter the budget.

The single primary endpoint is normalized area under the exact-generation
recall curve over load ratios `{0.5,0.75,1,1.25,1.5,2}`. The go threshold is at
least 5 AUC points over every matched control. State-noise injection is a
diagnostic only; the main claim must hold under natural overload and near-key
collisions.

### Phase A2 — checkpoint retrofit

After A0/A1 pass, transplant the coded read/write attachment into the pinned FLA
DeltaNet checkpoint. Freeze the checkpoint for the first screen and train only
the projections/decoder. Measure language loss drift and exact-memory gain.
This is interface and retained-capability evidence, not the causal result.

Kimi Linear enters only as a diagnostic scale control after the cheap study.
Its KDA plus periodic attention can reveal whether the alarm/correction signal
still adds information in a stronger hybrid. It is not an equal-budget DeltaNet
control and cannot replace the from-scratch matrix.

### Phase A3 — causal 125M comparison

Train coded and ordinary DeltaNet arms from scratch using the same tokenizer,
data order, optimizer, schedule, model width/depth, training tokens, and seeds.
When dimensions prevent exact parameter equality, publish both a narrower
iso-parameter control and a wider iso-state-byte control. Charge compilation and
kernel fallbacks in the wall-time view.

Kill immediately if correction does not beat the same coded state with
correction disabled, if replica/cache controls match it, or if block failures
are too correlated for the single-erasure assumption.

## Method B: Portable Sidecar Update Dynamics

The mechanism and event order in `directions/16-portable-learning-dynamics.md`
are normative. The first executable family uses one typed tool-outcome encoding;
mixing labels, textual critique, and environment reward would change the study.

### Five-role identification

1. Meta-train the rule on `T_meta × B_source` with Qwen and Mamba source bases.
2. Fit anchor-task latents only on `T_anchor × B_source`, then freeze them.
3. Fit the target alignment on `T_anchor × b_target`; it never sees `tau_new`.
4. Select rank, horizon, checkpoint, threshold, and feedback encoding only on
   disjoint `T_dev × B_dev` cells.
5. Fit the new-task latent on `tau_new × b_source`, freeze all components, then
   evaluate sealed `tau_new × b_target`. All dynamic methods receive the same
   causal outcome stream during evaluation and no target-cell training data.

Split generator/template family, tool namespace, argument ontology, and
composition family. Episodes are repeated observations; the generalization unit
is a held-out task-base cell.

The cheap contract uses Qwen3-0.6B and Mamba-130M. Kimi Linear is the third,
scale-only target base after the small-base interface and missing-cell test pass.
Before Kimi execution:

1. fetch metadata and hash the custom Python files;
2. review/vendor them into the image rather than enabling remote execution;
3. build the architecture image from a clean commit;
4. prove an 8-H100 tensor-parallel load, one forward/backward sidecar step,
   checkpoint, process exit, and fresh-job restore;
5. fix measured seconds/episode and HBM before expanding the matrix.

The primary endpoint is prequential regret in sealed missing cells relative to
the no-update base. Common-sidecar, fresh-optimizer, static-delta, and oracle
per-base controls receive matched evidence, state lifetime, update count,
parameters, search budget, and wall time. Latent/rule swaps, alignment-only
recovery, and anchor permutations are mandatory leakage probes.

## Method C: Translation-Equivariant Byte Patches

The 1B BLT checkpoint is an interface/forgetting test. The architecture claim
comes from a matched 125M study.

1. License and hash the parallel English–Chinese, English–Korean, and
   English–Polish corpora. Keep all translations of one semantic item in one
   document-level split.
2. Freeze normalization and monotonic byte-span alignments before training.
3. Compare entropy-only BLT boundaries, translation-equivariant boundaries,
   fixed boundaries plus the same representation loss, and a SentencePiece
   Transformer.
4. Match bytes per language, target patch rate, parameters, training FLOPs, and
   schedule. Report an additional wall-time view because boundary kernels differ.
5. Evaluate bits/byte, patch length by language, exact terminology/tool-schema
   fidelity, and causal transfer after boundary intervention.

The fixed-boundary auxiliary-loss arm is decisive: if it matches the proposed
model, the result is multilingual representation learning rather than a new
patching method. Kill on that result, on any greater-than-five-point language
regression, or if fidelity is purchased by worse bits/byte.

## Method D: Bidirectional Plan Repair

Do not pretrain a diffusion language model. Review and pin LLaDA's custom code,
then use matched LoRA budgets for LLaDA and an autoregressive Qwen planner.

1. Generate typed PDDL/API action DAGs with immutable executed nodes, explicit
   observation slots, deterministic tool replay, and known valid local repairs.
2. Split domain generators, action schemas, and graph motifs—not serialized
   rows—across train, development, and test.
3. On a changed observation, compute the affected-subgraph mask independently
   of either model. LLaDA re-denoises editable nodes only; AR regenerates the
   affected suffix. Both use the same validity verifier.
4. Pair episodes and compare success at equal p95 wall time, total model FLOPs,
   verifier calls, and model evaluations. Charge compilation/warm-up.
5. Replay every success in the environment and assert executed nodes are
   byte-identical before/after repair.

Stable Diffusion/SDXL is useful only to test the Diffusers image, cache, mixed
precision, LoRA, and checkpoint pipeline. It is not evidence for language-plan
repair and is not a scientific baseline here.

## Container, Slurm, tmux, and recovery

The single Dockerfile has locked runtime profiles:

```bash
podman build --build-arg UV_EXTRA=architecture ...
podman build --build-arg UV_EXTRA=diffusion ...
```

Publication jobs use the resulting registry `@sha256:` reference in a validated
Slurm manifest. Models live on a read-only persistent cache mount; outputs and
checkpoints live on a separate writable persistent mount. Every job records the
model receipt, config, git/archive/image hashes, Slurm allocation, seeds,
per-example outputs, compute ledger, and termination reason.

Use `bash scripts/tmux-research-session.sh cotcodec` for the login-host control
session. Submitted `sbatch` work survives SSH disconnects independently of tmux.
Neither tmux nor Slurm replaces recovery: long jobs checkpoint model/adapter,
optimizer, scheduler, scaler, RNG, data cursor, step, config and parent job ID;
retain two validated generations and reproduce uninterrupted continuation in a
fresh allocation before scaling.

## Promotion sequence

1. Registry validation and metadata-only custom-code review.
2. Full SmolLM2 acquisition plus local offline loader smoke.
3. Deterministic algebra/data unit tests with no GPU.
4. One GPU, one cell, one batch, checkpoint/exit/fresh-job resume.
5. Three-seed kill screen within the contract ceiling.
6. Independent Gauntlet novelty and methodology review.
7. Only survivors receive a 125M causal study or Kimi scale cell.

No direction advances because a checkpoint is fashionable or because eight
H100s are available. Each larger run must answer a decision the smaller run
could not answer.

## Primary upstream artifacts

- [SmolLM2-135M](https://huggingface.co/HuggingFaceTB/SmolLM2-135M)
- [Qwen3-0.6B Base](https://huggingface.co/Qwen/Qwen3-0.6B-Base)
- [Mamba-130M HF](https://huggingface.co/state-spaces/mamba-130m-hf)
- [FLA DeltaNet checkpoint](https://huggingface.co/fla-hub/delta_net-1.3B-8K-100B)
- [FLA implementation](https://github.com/fla-org/flash-linear-attention)
- [Kimi Linear checkpoint](https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base)
- [Kimi Linear implementation](https://github.com/MoonshotAI/Kimi-Linear)
- [BLT-1B](https://huggingface.co/facebook/blt-1b)
- [BLT implementation](https://github.com/facebookresearch/blt)
- [LLaDA-8B Base](https://huggingface.co/GSAI-ML/LLaDA-8B-Base)
- [LLaDA implementation](https://github.com/ML-GSAI/LLaDA)
- [SDXL Base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
