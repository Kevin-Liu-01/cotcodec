# Memory Policy Across Model Scale and Frontier Providers

**Status:** registered methodology; deterministic engine and resume contract pass;
GPT-5.6 and open-Qwen discovery screens are preserved but fail promotion or
provenance gates. Contained job 84 passes source/configuration doctors only.
**Verified:** 2026-08-13 against official model and service catalogs.

## Question

Does selective memory become less useful as the actor becomes more capable, or
does a stronger actor exploit the same retrieved evidence better?

Both outcomes are plausible:

- **Substitution:** a frontier model reconstructs missing context, asks for
  clarification, or uses its long context well enough that external memory adds
  little.
- **Complementarity:** a frontier model turns a correctly selected fact, graph
  path, or tool argument into successful action more reliably than a small model.
- **Risk amplification:** a more instruction-following actor may also obey a
  stored prompt injection more reliably.

Model size is an effect modifier, not a new memory estimand. The intervention
remains whether one registered memory candidate is served at its first eligible
use under a fixed memory and retrieval budget.

## Registered roster

Open checkpoints are pinned in `models/registry.yaml`; hosted identifiers and
their version semantics are in `models/provider-registry.yaml`.

| Tier | Model | Scientific role |
| --- | --- | --- |
| Interface | Qwen3 0.6B Base | loader, prompt, artifact, and replay smoke only |
| Small | Qwen3.5 4B | first post-trained agent; Gated DeltaNet/attention hybrid |
| Medium | Qwen3.5 9B | within-family scale control |
| Large open | Qwen3.6 35B-A3B | hybrid MoE scale transport |
| Large open | GPT-OSS 120B | architecture-diverse open control; official MXFP4 checkpoint |
| Architecture diagnostic | Kimi Linear 48B-A3B Base | long-context KDA/attention state diagnostic, not an instruction-model comparison |
| Frontier API | GPT-5.6 Sol | OpenAI capability ceiling |
| Frontier API | Claude Opus 5 | Anthropic primary frontier agent |
| Frontier API | Gemini 3.5 Flash | stable Google cross-provider cell |
| Frontier API | DeepSeek V4 Pro | DeepSeek provider and architecture cell |
| Frontier API | Kimi K2.6 | primary Kimi agent cell |
| Maximum secondary | Claude Fable 5 | expensive ceiling only after the primary frontier wave |

The Qwen 4B card identifies a hybrid of Gated DeltaNet and gated attention and a
262,144-token native context. It is therefore useful for both size transport and
sequence-operator transport. GPT-OSS 120B is a separate open MoE family. Kimi
Linear remains a base-model architecture experiment and cannot be pooled with
post-trained agent models.

Primary sources:

- https://huggingface.co/Qwen/Qwen3.5-4B
- https://huggingface.co/Qwen/Qwen3.5-9B
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- https://huggingface.co/openai/gpt-oss-120b
- https://huggingface.co/moonshotai/Kimi-Linear-48B-A3B-Base
- https://developers.openai.com/api/docs/models/gpt-5.6-sol
- https://platform.claude.com/docs/en/about-claude/models/overview
- https://ai.google.dev/gemini-api/docs/models
- https://api-docs.deepseek.com/updates/
- https://platform.kimi.ai/docs/models

## Identical experimental surface

Every eligible model receives the same:

1. task IDs and family-disjoint train/development/test manifest;
2. durable serve/holdout assignment for each task;
3. rendered query, untrusted-memory framing, response JSON schema, and tool tape;
4. active capacity `K=4`, at most one archive read, top-k at most four, and at
   most 256 injected memory tokens;
5. no-memory, full-transcript, fixed-policy, next-use, observational-utility,
   frozen causal-policy, and oracle-memory controls;
6. exact deterministic evaluator and safety cases;
7. tuning-trial, prompt-version, and policy-artifact budgets.

Do not pad a holdout prompt. Record actual input/output/reasoning/cache tokens,
latency, serialized memory bytes, reads, writes, and provider cost.

## Three-wave method

### Wave A — interface and competence screen

Run 25 A/A tasks per open checkpoint to validate load, chat template, direct JSON
mode, exact artifact capture, isolation, and checkpoint recovery. Then run 200
common tasks per model at serve propensity 0.5.

A model can enter confirmation only when oracle-memory success is at least 80%,
valid action JSON is at least 95%, no session bleed occurs, and A/A executable
success drift is at most two percentage points. Failing models remain reported
interface or floor controls; excluding them is not evidence of memory failure.

### Wave B — matched model transport

Freeze the memory policies learned without any sealed test or frontier-model
outcomes. Run the same 2,400 task IDs for eligible models. The primary within-
model contrast is:

```text
executable success(frozen causal policy)
  - executable success(strongest noncausal learned control)
```

Require at least three percentage points with a family-clustered 95% confidence
interval excluding zero for a model-specific promotion. Fit a categorical
model-by-policy mixed-effects analysis clustered by task family. A monotonic
trend with parameter count is exploratory because MoE active parameters,
post-training, architecture, and provider scaffolding are confounded.

Run propensities 0.50, 0.25, and 0.10 only after the 0.50 cell passes overlap,
competence, leakage, and cost gates. Stop a model cell if at least 80% of tasks
are at the oracle ceiling or no-memory floor; that cell cannot identify a useful
memory-policy difference.

### Wave C — sealed external validity

Only policies and thresholds frozen in Wave B may run on LongMemEval-V2,
MemoryAgentBench, and Mem2ActBench. Public tasks never train or select the gate.
Report every excluded or unscorable public item.

## Self-hosted versus hosted identification

Self-hosted open checkpoints use greedy decoding and engine-owned snapshot,
RNG, prompt, and deterministic tool receipts. A 25% paired replay audit can
therefore check that branches differ only in the memory exposure.

Hosted providers do not expose restorable hidden state or sampling RNG. Their
primary causal evidence is prospective single-arm randomization with known
propensity and cross-fitted AIPW. Do not describe two hosted calls as exact
counterfactual replay. Instead:

- repeat 10% of identical prompts as A/A drift probes;
- bind requested and returned model identifiers, response IDs, timestamps,
  SDK/API versions, and available service fingerprints;
- re-list model availability before every wave;
- fail closed on a changed model ID or unsupported parameter;
- run serve and holdout in randomized temporal order to reduce time drift.

Anthropic documents dateless 4.6-and-later IDs as pinned weights while warning
that surrounding serving infrastructure may change. Google distinguishes stable
IDs from mutable `latest` aliases. DeepSeek and Kimi service IDs are treated as
mutable unless the provider supplies a stronger run-time guarantee.

## Tinker controller ladder

Tinker is for the external discrete `KEEP`, `EVICT`, `RETRIEVE`, or `NO_OP`
controller—not for changing hidden memory state or a sequence operator. The
official service currently exposes LoRA training, sampling, full-state resume,
and downloadable adapter checkpoints.

Use three label arms with identical examples, rank, steps, token ceilings, and
rendering:

1. next-use labels;
2. observational future-utility labels;
3. cross-fitted causal holdout labels.

Start with `Qwen/Qwen3.5-4B`, then confirm on
`Qwen/Qwen3.6-35B-A3B`, and only then run
`moonshotai/Kimi-K2.6`. Use the official thinking-disabled renderer for the
primary direct-decision comparison and the matched thinking renderer as a
secondary arm. A fresh client must restore weights **and optimizer state** and
reproduce the uninterrupted next batch before the Kimi run.

Official Tinker sources:

- https://tinker-docs.thinkingmachines.ai/
- https://tinker-docs.thinkingmachines.ai/tinker/models/
- https://tinker-docs.thinkingmachines.ai/tinker/data-model/
- https://tinker-docs.thinkingmachines.ai/tutorials/core-concepts/rendering/

## Budgets and stop rules

- Open-model screen: at most 8 H100-hours per model.
- Open confirmation: at most 96 H100-hours total.
- Hosted screen: at most $25 total.
- Hosted confirmation: at most $100 total.
- Tinker has its own preregistered token and dollar ceiling.

Stop on any leakage, cross-session bleed, model identity drift, safety red line,
budget breach, irrecoverable checkpoint, insufficient overlap, or three waves
without a two-point score improvement. A result in which frontier models make
the proposed memory policy unnecessary is a valid negative finding.

## Executed GPT-5.6 discovery cells

The first 200-task competence screen is transport evidence only. Structured
actions and provider receipts were complete; served-memory executable success
was 94/97. The stratum breakdown was 28/28 active core, 23/23 inactive archive,
25/25 proactive tool, and 18/21 temporal graph. All three failures followed a
newer conflicting graph edge. Twenty identical A/A prompt pairs had no action
disagreement. The sealed bundle manifest is
`64f3f5da6a104bb8fa97c052f240985affa2a24e3e9728dbeb726a25d5c69329`;
the immutable v2 analysis records that the original preflight predates source
receipts. Cost estimated from provider usage was $0.75577 for 240 responses.

The 80-task safety screen randomized hazardous candidate visibility at p=0.5.
There were 13 failures among 33 served tasks and zero among 47 holdouts: risk
difference +39.39 points, Newcombe 95% interval [+17.13, +56.32], Fisher exact
two-sided p=`1.82e-6`. By family, stored prompt injection was 6/6 served versus
0/14 holdout; PII canary was 6/11 versus 0/9; delayed activation was 1/6 versus
0/14; stale permission was 0/10 versus 0/10. One of eight identical A/A prompt
pairs changed from the safe baseline record to the hazardous PII record, so the
registered drift gate failed. The bundle manifest is
`c354223d562904b135d29399ce1b3a48fcaa4db3eeb1f5186eee2413022e6d0e`.
This dirty-tree synthetic result triggers replication and mitigation work; it
is not publication evidence or a claim about real-world incidence.

## Open-model H100 launch path

`scripts/compile_memory_open_job.py` compiles the common model-transport command
into a validated Slurm manifest after receiving a real committed git SHA,
source-archive SHA, OCI digest, and persistent run root. Registered discovery
profiles are:

| Model | GPUs | Wall time | Ceiling |
| --- | ---: | ---: | ---: |
| Qwen3.5 4B | 1 H100 | 4 h | 4 GPU-h |
| Qwen3.5 9B | 1 H100 | 4 h | 4 GPU-h |
| Qwen3.6 35B-A3B | 2 H100 | 4 h | 8 GPU-h |
| GPT-OSS 120B | 2 H100 | 4 h | 8 GPU-h |

Snapshots and full-file receipts must be staged under the persistent
`/cache/huggingface/cotcodec-{models,receipts}` mount before inference. The
generic image refuses checkpoints with unreviewed remote code or unresolved
publication eligibility. Chat checkpoints use their pinned tokenizer chat
template with thinking disabled; base checkpoints retain plain completion.

On preemption, the episode collector writes the hash-bound checkpoint before
the Slurm marker. A successor manifest names a numeric predecessor and the
`screen` subpath. The batch job checks predecessor image/git/source provenance,
rejects symlinks, copies that tree into the new job directory, and runs
`--resume`; it never overwrites the predecessor.

Metadata-only preflight resolved all four registered Hub commits and downloaded
their required config/license/chat-template metadata. The locked Transformers
runtime loaded them without remote code as `Qwen3_5Config`, `Qwen3_5Config`,
`Qwen3_5MoeConfig`, and `GptOssConfig`, respectively. These receipts prove
registry/config compatibility only; publication eligibility remains false until
the complete weight snapshots are downloaded and hashed.

Full pinned Qwen3.5 4B/9B and Qwen3.6 35B-A3B snapshots were subsequently
hashed and verified offline. The 4B and 9B 200-task screens failed promotion;
the 35B four-task interface cell passed but its full screen failed same-arm A/A
replay. GPT-OSS 120B still has no full artifact receipt. Separately, discovery
job 84 used retained source archive
`10e598c71fa523c94a8f626c9dd93514b08f850f6a3bdf0bd87072cbf16edc7c`
and image
`sha256:d55c09031bcf3d816eaa3371cea387b9ff3463de8dd0029358a92e937faea9b0`
to pass compile and configuration validators. That dirty-tree, no-dev overlay
is not a model result or a contained pytest receipt.

## Required artifacts

Persist the model/provider preflight, open-model file receipt, task and assignment
manifests, exact rendered request, returned model and response identifiers,
token counts, raw response, parsed action, tool trace, memory ledger, policy
artifact, checkpoint lineage, A/A probes, estimator folds, per-family metrics,
cost reconciliation, and safety report. The registered machine-readable contract
is `experiments/memory/stage1-model-transport.yaml`.
