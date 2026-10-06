# Research reset: useful computer work on eight H100s

Research date: 2026-10-06. Status: literature-backed design assessment, not an admitted experiment or a reproduced result.

## Recommendation

Keep the evidence infrastructure. Broaden the research question from agent memory to reliable computer work under a fixed compute budget. Build a small integration layer around existing desktop environments and inference engines before considering a new framework or model architecture.

The primary question should be:

> How much correctly completed computer work can this machine deliver, at a specified latency and safety level?

This is different from maximizing tokens per second, keeping every GPU busy, or making an agent remember more. A faster model call can still produce a slower or incorrect workflow. A cached observation can be cheap and wrong. A short trajectory can be an early failure.

There is a plausible systems research direction at the boundary between inference scheduling and changing application state. There is not yet evidence that our proposed mechanism is novel. Several broad versions of this idea are already occupied. The next step is a small falsification study, not a full rewrite or a large training run.

## 1. What I checked

The literature search used OpenResearch on `fal-h100-01`, with the publication window 2026-01-01 through 2026-10-06 and recency priority. Fourteen archived keyword, embedding and OpenAlex queries returned 84 records, or 70 unique identifiers after normalizing arXiv DOI forms. An initial eight-result discovery call is recorded in the conversation but not in the raw archive and is excluded from those counts.

Five central papers received targeted main-text method/result inspection. Three additional closest-prior papers received targeted method/result/limitation inspection. Full extracted text and hash receipts for all eight are on the H100 host. This does not mean every appendix was read. The companion source ledger records the inspected sections.

Official documentation and repositories were checked for NVIDIA Hopper, Dynamo/ThunderAgent, vLLM AgentX, SGLang System One, FlashAttention, Slurm and KernelAgent. Lab-oriented searches covered OpenAI, Anthropic, Google, DeepSeek, Qwen, Meta, Mistral, xAI and Cohere. Search coverage is not equivalent to a complete review of each lab. An inaccessible Mistral announcement was not used to select a checkpoint.

This is a broad, bounded review, not “all research.” Missing coverage includes a systematic OpenReview/ACL sweep, patents, Chinese-language sources, complete citation chasing and a live X/HN/Reddit account sweep. Recent preprints and development-branch documentation can change. No paper result was independently reproduced.

The review was bounded to 90 minutes, zero paid model calls and zero GPU jobs. No complete query/token/wave budget was recorded before the initial retrieval. That is a process defect, so this report is not a compliant completed Research Gauntlet wave. Further retrieval stopped after the closest-prior pass. No candidate is promoted or assigned a score.

## 2. What changed in the research landscape

These are the strongest findings for our decision. Numbers below are the authors' results, not our measurements. Dates are publication dates reported by the retrieved source.

| Work | Relevant finding | Consequence for us |
|---|---|---|
| [HEAR, October 5](https://www.alphaxiv.org/abs/2610.06597) | A protocol already connects harness intent, engine state, execution constraints and outcomes. Its experiments include cache-aware scheduling and role-specific inference configurations. Policy benefits change with load. | “Connect the harness to the GPU engine” is not a new contribution. Use this as a baseline or integration reference. |
| [ThunderAgent, February 14](https://www.alphaxiv.org/abs/2602.13692), plus [current Dynamo implementation](https://docs.dynamo.nvidia.com/dynamo/dev/agents/thunder-agent-program-scheduler) | Program-aware admission and worker placement already account for reasoning/tool phases and cache pressure. The native plugin is experimental; its logical token budget is not exact physical KV occupancy, and state is per frontend. | Do not reinvent generic agent-aware scheduling. Benchmark the actual selected implementation, not a mixture of paper and plugin features. |
| [CUA-Sandbox, September 26](https://www.alphaxiv.org/abs/2609.32750) | Shares initialized runtimes while keeping mutable environment state private. The OSWorld rollout comparison reports 3.08× throughput at eight concurrent environments. Hardware was Blackwell, not H100. | Environment startup and state copying deserve measurement. Sharing requires complete resource bindings; it is not automatically an adversarial security boundary. |
| [cua-speedrun, September 30](https://www.alphaxiv.org/abs/2609.40284) | In one five-seed comparison, faster I/O reduced environment processing from 12.68 to 0.34 seconds per task, but total task time rose from 89.5 to 99.0 seconds. Screenshots could precede UI updates. | Optimize complete tasks. Distinguish an old observation from a new observation of an application that has not finished updating. |
| [AsyncLLM, September 28](https://www.alphaxiv.org/abs/2609.35427) | Concurrent inference coroutines share model memory views. It supports changing input, video and monitoring without task-specific training. Some efficiency gains accompany lower monitoring accuracy. Its reported inference-speed hardware is H200. | “Think while observing” and shared inference memory already have direct prior work. Neither their throughput nor their quality transfers automatically to this H100 host. |
| [HybridCUA, September 29](https://www.alphaxiv.org/abs/2609.38008) | Training teaches GUI/CLI selection. Merely adding CLI access reduced the base model's OSWorld accuracy from 38.8% to 18.4%; the trained hybrid reached 53.6%. The matched trained GUI-only arm reached 50.4%. | Interface access and learned competence are different treatments. Do not attribute the full improvement to the interface. Shell access also needs a stronger safety boundary. |
| [Before Agents Act, September 28](https://www.alphaxiv.org/abs/2609.34376) | Explicitly schedules evidence under freshness, deadline and resource constraints. Evaluation uses generated infrastructure scenarios, not a deployed desktop/GPU system. | Generic “freshness-aware scheduling” is already occupied. Any remaining claim must be narrower and experimentally distinct. |
| [Tracking State Footprints, October 2](https://www.alphaxiv.org/abs/2610.03140) | Relates agent coordination to read/write conflicts and transactions. Includes a small four-task coding study and a broader research vision. | Durable execution, dependency tracking and selective recovery are not new merely because we apply them to agents. |
| [ReSync, September 28](https://www.alphaxiv.org/abs/2609.33944) | Studies the timing gap between action commitment and useful world evidence in asynchronous robot world-action models, with equal-compute controls. | Timing of evidence is a broader existing idea. Desktop application readiness and GPU scheduling must add more than a renamed “two clocks” story. |

Two further leads were retrieved at abstract level only: [Desktop-Delta Bench](https://www.alphaxiv.org/abs/2607.26041), which diagnoses GUI transitions, and [TRACE](https://www.alphaxiv.org/abs/2609.33517), which governs whether old memory remains usable after shared state changes. These belong in the next closest-prior review, not in a claim of verified superiority.

### What this means for memory research

Memory remains relevant, but it is only one part of the system:

| State | Example | Correctness question |
|---|---|---|
| Application state | A saved spreadsheet or sent message | Did the requested change actually happen? |
| Agent memory | A remembered fact or plan | Is it still true and relevant? |
| Model cache | Cached attention keys/values | Does reuse match the intended model computation? |
| Runtime state | Processes, queues, files and checkpoints | Can the run continue without contamination or duplicate effects? |

Optimizing one does not prove improvement in the others. Keep the exact-source memory lifecycle doctors and the negative evidence. The earlier [October 6 memory/architecture scan](2026-10-06.md) remains separate. Its frozen experiments do not become runnable because this review changes our priorities.

## 3. What our H100 machine actually provides

Read-only SSH inspection on October 6 confirmed:

- Eight H100 80GB HBM3 devices, each reporting 81,559 MiB. All were idle at inspection. This is an instantaneous observation, not a utilization history.
- `NV18` connectivity between every GPU pair. This supports investigation of multi-GPU serving, but link labels are not a measured bandwidth result.
- About 1.7 TiB host RAM and 208 logical CPUs presented to a KVM virtual machine. The CPU/NUMA presentation is not proof of the physical host's full topology.
- A roughly 22 TB virtual block device. Its backing storage and sustained I/O performance are unknown; calling it NVMe would be unjustified.
- `/dev/kvm` exists and is readable/writable by the research user. Nested desktop virtualization remains untested until an actual guest boots and passes interaction checks.
- NVIDIA driver 570.148.08, Docker 28.3.1 and Slurm 21.08.5. The existing project gate still classifies this as discovery-only: cgroup-v2 device isolation and the required Pyxis path are not admitted.

The nominal eight-device memory total is not one transparent allocation pool. Model weights, KV state, activations and runtime overhead must fit the chosen sharding layout. A mixture-of-experts model's active parameter count is not its total resident weight size.

Use these GPUs where they provide experimental control: pinned open checkpoints, reproducible inference settings, concurrent workloads and small adaptation studies. We cannot infer how a closed frontier model schedules its internal compute, and an eight-H100 node is not a sensible reason to pretrain a frontier foundation model.

## 4. Modernize the software stack before considering new hardware

### First: make execution trustworthy

The [operator runbook](../../docs/h100-operator-runbook.md) separates bounded single-user discovery from publication-grade execution. It also records an exhausted, frozen two-attempt node. Neither that node nor its accounting should be reset.

An administrator should review an aligned Slurm/container/cgroup upgrade, with a maintenance window and rollback plan. Prove GPU visibility, CPU/RAM limits, cancellation and cleanup. Current [Slurm cgroup-v2 documentation](https://slurm.schedmd.com/cgroup_v2.html) explains why this is a coordinated configuration task, not a package-version substitution. Do not copy old proposed version pins without a fresh compatibility check.

A job must use an immutable source/image/model tuple, persistent output, bounded resources and tested recovery. Shared filesystem state, a browser context, a container and a VM are different isolation boundaries. Browser agents must not receive the host Docker socket, real credentials, broad host mounts or a path to their grader.

### Second: establish a strong H100 baseline

Start with one GPU and one small, image-capable open checkpoint. An 8–9B model is a reasonable candidate class, not a guaranteed memory-fit statement. Validate exact weights, visual token sizes, context lengths and concurrency before admission. Use a larger second checkpoint only after the measurement loop works.

Compare a pinned vLLM or SGLang build against the existing baseline. Use BF16 as the numerical reference. Evaluate supported lower precision only with task-level checks and a declared numerical tolerance. Do not confuse quantized storage with native arithmetic support.

[Hopper's documented features](https://docs.nvidia.com/cuda/archive/12.8.1/hopper-tuning-guide/index.html) include asynchronous memory movement and architecture-specific execution mechanisms. The current [FlashAttention repository](https://github.com/Dao-AILab/flash-attention) includes Hopper support in both the FA3 path and the newer FA4 work. Kernel availability, selected shapes, driver compatibility and actual dispatch still need validation. Installing a package is not evidence that the fast kernel ran.

Sweep replicas versus tensor parallelism only after one-GPU measurement. Several small independent workers can outperform putting a small model across all eight devices. Conversely, a larger checkpoint may require sharding. Measure CPU/browser saturation, NUMA placement, screenshot encoding, GPU queues, cache reuse and storage alongside inference.

The [vLLM AgentX report](https://vllm-project.github.io/2026/09/08/vllm-agentx.html) is a useful configuration reference, but its headline hardware is B300/GB300. Its throughput figures cannot be advertised as H100 results. Cached-token throughput is also not completed computer work.

### Third: only optimize a measured bottleneck

Use a whole-run timeline before a kernel profiler. If GPU work occupies 20% of a sequential critical path, making that part infinitely fast gives at most 1.25× end-to-end speedup under that simplified model. Overlapping pipelines require their actual critical path, not a sum of component times.

An agent that writes GPU kernels is not a novel project by itself. [Meta's KernelAgent](https://github.com/meta-pytorch/KernelAgent) already integrates generation, profiling, verification and optimization. Adopt or compare with it. A useful narrower experiment would optimize operators that dominate our measured H100 workload, under hidden shape/input tests, numerical checks, and an unchanged end-to-end task suite.

Do not buy networking, storage, DPUs or replacement GPUs before measurement identifies a bottleneck. Software can improve how H100s are used; it cannot increase their physical HBM capacity or turn them into a newer GPU architecture.

## 5. The system I would build

Build a thin, versioned computer-work harness, not another all-purpose agent framework.

```text
Frozen task + initial application state
                 |
                 v
     Private real application session
                 |
       timestamped observation
                 v
        Agent / bounded policy
                 |
        inference-engine adapter <--> H100 queue and cache telemetry
                 |
       authorized action boundary
                 v
     Application changes and acknowledgments
                 |
                 v
     Independent final-state evaluator

Observer: records timing, actions, state versions and resource use.
The actor cannot read evaluator answers or future application state.
```

### Reuse

- Existing provenance, task/version contracts, immutable traces, cost limits and lifecycle tests from CoTCodec.
- Relay's experience with live observations, understandable results and replay. Reuse patterns, not unexamined claims that every historical task is valid.
- Existing real-application environments from OSWorld/cua-speedrun or another admitted backend. Do not build another Slack clone to establish general computer-work capability.
- Existing inference servers and their scheduling APIs. Keep engine-specific code in adapters.

### Add

- One event schema linking task, session, observation, model request, action and acknowledged application change.
- Separate timestamps for capture, UI readiness, queue admission, prefill, decode, action dispatch and effect acknowledgment. Specify clock domains and uncertainty.
- A deterministic state-change injector for controlled tests: for example, a modal opens late, another authorized editor changes a value, or a file changes while the agent reads it.
- A visible-input-only policy that can wait, refresh, execute or stop. Hidden evaluators may measure staleness but must not supply the policy with privileged state.
- A read-only observer that records failures without turning unknown outcomes into successes.
- Full-run accounting: GPU allocation time, useful kernel time, CPU time, energy where reliable counters exist, memory and evidence storage. Record unsuccessful and interrupted work too.

### Application coverage

Start with three different state/verification patterns: browser form editing, spreadsheet/file editing, and a terminal-plus-document workflow. Later hold out whole applications, not merely alternate wording of the same task. A GUI-only arm, a GUI/CLI arm and an API arm have different available capabilities. Label them separately instead of presenting API tool use as pixel-based computer use.

### System One fits as an optional component

SGLang has a merged [System One-compatible route](https://github.com/sgl-project/sglang/pull/41208) for typed decisions over state. It may be useful for a small “wait / refresh / act” choice. It is not a new trained computer-use model. The implementation documents uncalibrated confidence and sensitivity to batching/cache behavior; we must test those, pin the route and prompts, and avoid importing thresholds from another provider. No endpoint was deployed in this review.

## 6. Candidate research question and rejection tests

### Leading candidate: joint timing and resource control for computer work

Claim scope, if it survives: `systems-pipeline`, not a new model architecture.

Question: Can a policy that accounts for application readiness and observation validity improve correct task completions per allocated GPU-hour over a strong cache-aware scheduler plus simple refresh rules?

Example: a model chooses a menu action from a screenshot. While its request waits in the inference queue, the application opens a dialog. Executing the old coordinate can hit a different control. Conversely, capturing immediately after a valid click may show a UI that has not finished updating. These are two different failure modes. A useful policy must distinguish them without reading hidden truth.

The proposed intervention would choose among bounded waiting, obtaining a fresh observation, yielding inference capacity, or dispatching an already authorized action. Cache reuse is a cost signal, not permission to use stale evidence. Consequential writes require an observed precondition or a safe refusal; a screenshot recheck alone cannot guarantee atomicity in arbitrary software.

Closest-prior verdict: `NARROWED`. HEAR/ThunderAgent cover cross-layer efficiency, AAS covers freshness-aware evidence scheduling, AsyncLLM covers concurrent observations, and State Footprints covers conflicts. A contribution might remain in a demonstrated interaction between real desktop state validity and inference scheduling. Mere integration or renaming does not establish it.

### Smallest diagnostic, proposed but not authorized to launch

- One pinned open VLM, three workflow fixtures and seeds `[42, 43, 44]`.
- Pair unchanged-state and controlled-changing-state conditions: 18 agent episodes maximum.
- Freeze instruction, initial state, model, precision, observation budget, action budget and injected event schedule. Preserve every failure.
- First use scripted actors and CPU checks on the H100 host to verify that the injected events and state graders work.
- A future diagnostic allocation would be capped at one H100 for two hours, not a promise that all episodes fit. Stop at the cap and report incomplete coverage.
- Purpose: determine whether the failure exists and can be measured. This is not enough to declare an improvement or estimate general safety.

If this passes, prepare a separate matched study. Its controls must include the original runtime, a fixed wait/refresh rule, always-refresh before relevant writes, and the strongest feasible prior scheduler plus the same safety rules. Compare the proposed joint policy against that composition, not only against an intentionally weak sequential loop.

The scheduling treatment affects shared queues, so the randomized experimental unit for a load test is a complete workload batch. Individual requests in one queue are not independent trials. Match arrival streams, task mixture, state-change draws and seeds across arms; randomize arm order and isolate serving state. Include both low load and overload, and report per-task harm alongside throughput. The experimental-design skill informed these controls.

Primary measure: correct completions meeting a prespecified deadline, divided by allocated GPU-hours. Report completion rate, unsafe/unrequested changes, full wall time, p50/p95 latency, per-task cost and storage separately. Queue waiting, startup and verification must be visible even if a secondary benchmark clock excludes them. Success-only latency must not hide failures. System load and task distributions define the scope of the result.

Kill the candidate if:

1. A fixed readiness wait or always-refresh control removes the problem at the same effective cost.
2. The apparent gain comes from dropping hard tasks, using privileged state, allowing more attempts or changing the grader.
3. Existing scheduling plus an independent freshness check matches the joint policy.
4. Results depend on hand-designed disturbances and disappear on held-out real applications.
5. More completed work requires unacceptable side effects or starvation of slower tasks.

### Other directions

| Direction | Recommendation | Reason |
|---|---|---|
| Shared runtime and fast task reset | Adopt and validate first | CUA-Sandbox is close prior; the hard part is proving state isolation for our apps. |
| Learning GUI/CLI/API selection | Secondary study after a sound harness | Existing hybrid training work is strong. A new policy needs matched training and permission controls. |
| H100-specific operator optimization | Engineering track unless a distinct method emerges | Measure actual operator shapes and end-to-end effect; compare existing kernel optimizers. |
| Memory-only product comparison | Retain as a component-level control | Lifecycle correctness does not by itself establish better computer work. |
| New foundation architecture from scratch | Do not start now | Existing architecture candidates have unresolved admission gates. Available GPUs do not remove identification, data or kernel-maturity problems. |

## 7. What changes now, and what does not

Change the research priorities and measurement plan. Do not discard the repository or erase negative results. Update outdated “unexplored” and “nobody has studied this” language where the new sources directly contradict it.

No GPU run is admitted by this report. The remaining gates are: exact implementation/license review; full closest-prior discrimination; independent refute-first and provider-distinct reviews; a clean source capsule; image/model provenance; executable CPU tests; Slurm dry-run and test-only receipts; and a tested persistent recovery contract. No scores or independent reviews have been invented.

Suggested order:

1. Resolve the host's execution/isolation plan with its administrator.
2. Admit one real desktop fixture and one frozen checkpoint on the H100 host.
3. Produce a single complete timing/verification trace before optimizing anything.
4. Run the bounded diagnostic only under a new admitted manifest.
5. If simple controls already solve it, retain the engineering improvement and reject the research claim.
6. Scale to more GPUs, training or kernel work only after the evidence identifies the useful next expense.

There is no need to keep all eight GPUs occupied while deciding what to measure. The scarce resource is not just GPU capacity. It is a trustworthy experiment that answers a question the current literature has not already answered.

## Evidence and preservation

- Remote source archive: `/home/kevin/cotcodec-runs/frontier-research/2026-10-06-reset-v1`.
- Companion ledger: `2026-10-06-research-reset.sources.json`.
- Verification receipt: `2026-10-06-research-reset.verification.json`.
- Research execution and document validation took place on `fal-h100-01`; the laptop served as editing/transport and viewing surface.
- Existing local Letta Code work, frozen experiment limits, prior study evidence, deployed Relay and GPU configuration were not changed.
- Zero new agent inference calls, GPU jobs, administrator changes or hardware purchases in this review.
