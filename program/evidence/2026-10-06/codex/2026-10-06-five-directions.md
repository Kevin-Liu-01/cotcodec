# Five research directions for eight H100s

Assessed 2026-10-06. Status: research triage, not pilot admission or a novelty claim.

## Recommendation

Make kernel verification and training the leading candidate. Keep answer selection and compute allocation as the lower-risk alternative. Do not begin five training projects, and do not discard the existing experiment infrastructure.

The strongest opportunity is not simply an open model that writes CUDA. It is a model whose performance reward remains useful when inputs, shapes, and implementation details change. That requires an independently checked reward pipeline before reinforcement learning.

This ranking is a judgment about a tractable first research contribution, not a forecast of eventual commercial impact.

| Rank | Direction | Why it belongs here | Principal limitation |
| --- | --- | --- | --- |
| 1 | Kernel verification and training | H100s provide both model compute and direct measurements of generated programs | Open kernel RL and correctness-aware rewards already exist |
| 2 | Answer selection and shared-budget allocation | Cheap component experiments; direct connection to orchestration research | A hidden-state probe is already prior art; model-specific features limit transfer |
| 3 | Specification robustness | Strong connection to verification and a well-defined failure mode | SpecRL and Spec-Harness already address weak specifications |
| 4 | Numerical-format research | H100s can emulate quantization and test numerical behavior | Emulation cannot establish native FP4 speed, energy, or silicon cost |
| 5 | Switchable attention | Possible checkpoint conversion study | Existing switching does not remove the KV cache; routing alone does not establish memory savings |

## 1. Kernel RL: retain the direction, narrow the contribution

### What the papers actually establish

- KernelPro's 1.23x result is a specific H100 MoE weight-gradient grouped-GEMM case, not a general gain across all MoE kernels. The paper traces the improvement through 18 optimization iterations. See section 5.4 of [KernelPro](https://www.alphaxiv.org/abs/2606.26453), first submitted 2026-06-24.
- CAKE is relevant GPU work, not the unrelated Bayesian-optimization paper with the same acronym. Its clean-start representation comparison uses B200, three runs per representation, and an 80-million-token search budget. It co-designs a typed scheduling IR with localized compiler and verifier feedback. This is important prior art for an agent-facing compiler interface. See abstract and introduction of [CAKE](https://www.alphaxiv.org/abs/2608.12629), 2026-08-12.
- The claim that open kernel training is the missing ingredient is too broad. KernelZero trains a 7B coder with correctness-aware GRPO and a co-evolving proposer. Its reported coder update uses eight A100-80GB GPUs across optimization and validation; its proposer update uses twelve. An eight-H100 machine therefore does not automatically reproduce its entire concurrent setup. See sections 3 and 4 and appendix C of [KernelZero](https://www.alphaxiv.org/abs/2609.33074), 2026-09-27.
- CUDA-Harness already uses isolated, synthesized tests and progressive verification to reduce fixed-input reward hacking. Adding random tests alone is not a new contribution. See sections 1 and 3 of [CUDA-Harness](https://www.alphaxiv.org/abs/2609.00058), 2026-08-30.

### The important correction: testing, formal proof, and speed are different

The proposed reward should not be an additive score in which sufficient speed can compensate for failed correctness. Use hard acceptance conditions followed by a performance objective.

1. Parse and compile an allowed program.
2. Check memory behavior and the supported formal semantics.
3. Run fresh differential tests, including relevant edge cases.
4. Only then measure and reward speed.
5. Keep proof coverage, numerical-test coverage, and unsupported constructs as separate recorded fields.

The formal check is not a universal PTX/SASS equivalence oracle. In *AI as a Compiler*, Volta abstracts floating-point operations as real arithmetic. Unsupported cases include atomics, input-dependent control flow, and bit-level value manipulation. The original verifier also excludes optimizations that improve performance; the paper expands the verifier and its trusted code base. Its 3.34x is the maximum reported improvement, not a typical H100 gain. See sections 3 and 4.5 and appendix B of [AI as a Compiler](https://www.alphaxiv.org/abs/2609.36800), 2026-09-29.

Numerical tolerance is part of the specification. A kernel that passes a real-arithmetic proof can still require floating-point tests. A tested kernel is not thereby formally proven.

### A candidate question worth testing

At a fixed training and evaluation budget, does strengthening the correctness reward improve the fraction of held-out kernels that are both correct and faster than a strong reference?

This is a narrowed question for further novelty review, not an established gap. The next audit must discriminate it from KernelZero, CUDA-Harness, CAKE, and existing kernel-training methods cited by those papers.

Start with a frozen bank of kernels from an existing open coder. Include correct programs, slow programs, and realistic incorrect variants. Compare existing validation against the proposed validation without training a model. If the stronger checker cannot detect additional relevant errors at an acceptable cost, the RL proposal has no demonstrated premise.

If that diagnostic succeeds, compare:

- the unchanged model with matched search and execution budgets;
- supervised learning on accepted examples;
- RL with the baseline correctness reward;
- RL with the stronger correctness reward.

Use held-out operator families, shapes, and input distributions. Keep final evaluation tests unavailable to the learner. Report false acceptance, false rejection, valid-and-fast rate, wall time, total GPU-hours, compilation cost, and verifier cost. Do not report only the fastest survivors.

Time reference and candidate kernels in randomized paired order, with warmup and uncontended hardware. Training or other device workloads must not overlap a measurement window. Separate GPU allocation alone is insufficient if shared host load distorts the timing path.

Start from a pinned 7B checkpoint and a measured memory/throughput smoke test. Do not assume a 14B full-parameter GRPO job fits merely because the total nominal HBM is 640 GB. Weights, optimizer states, rollouts, activations, communication buffers, and serving KV caches all consume memory.

The defensible first outcome is H100 kernel optimization on a declared workload family. Adapting to any new accelerator requires additional hardware and compiler backends; H100-only experiments cannot establish that claim.

## 2. Answer selection: the best lower-risk alternative

The unnamed June paper is [When More Sampling Hurts](https://www.alphaxiv.org/abs/2606.28661), submitted 2026-06-27. Its formal modal ceiling applies to plurality selection from a fixed answer distribution. Section 4.2 explicitly distinguishes learned scorers: a perfect verifier can recover coverage, whereas a frequency-like scorer inherits the modal ceiling. This is not a universal theorem that all best-of-n systems stop improving at a fixed sample count.

[Thinking Hard, Not Smart](https://www.alphaxiv.org/abs/2608.07968), submitted 2026-08-08, studies exam-style shared budgets. Its observed position-driven behavior supports testing an external allocator; it does not itself establish that a particular learned scheduler will improve production serving. The full factorial evaluation is on mathematics, with narrower code-reasoning coverage.

[ReProbe](https://www.alphaxiv.org/abs/2511.06209), first submitted 2025-11-09, already learns small internal-state verifiers. Its limitations explicitly state that a probe cannot be applied directly to a different underlying model. Its appendix also notes that collecting attention-map features disables efficient attention implementations. A small verifier does not guarantee a small end-to-end cost.

The candidate question is whether a calibrated estimate of the value of another generation step improves allocation across tasks, after charging for feature collection and verification.

Separate two effects before combining them:

| | Fixed allocation | Learned allocation |
| --- | --- | --- |
| Existing selector | Baseline | Allocator contribution |
| Hidden-state selector | Selector contribution | Combined system |

First compare selectors on the same frozen candidate pools. Then test allocation online with the same base model and total budget. Use majority voting, a strong existing reward model, and simple early-stopping/allocation heuristics. An oracle selector is a diagnostic upper bound, not a deployable baseline.

Hold out problem families, not just individual sampled answers. Report returned-answer accuracy, available-answer coverage, selection regret, latency, feature overhead, and actual GPU time. No universal deployment claim: closed APIs do not expose the required hidden states.

Stop if a simple allocator matches the proposed one, or if feature extraction erases the savings. This is a practical experiment even without RL-training the base model.

## 3. Specification robustness: combine with verification, not three models immediately

The 2.2% to 58.1% number comes from Max Tan's May 2026 thesis, [Automating Formal Verification with Reinforcement Learning and Recursive Inference](https://www.alphaxiv.org/abs/2605.30914), not from a clean measure of intended-program correctness. The initial verified-reward increase exposed specification hacking. After filtering vulnerable tasks, the thesis reports a separate improvement from 9.7% to 31.1%. These are different experimental conditions, not interchangeable headline results.

[Goedel-Code-Prover](https://www.alphaxiv.org/abs/2603.19329), first submitted 2026-03-18, reports 62.0% proof success over 427 tasks across three Lean code-verification benchmarks. This is proof relative to supplied specifications under its reported hierarchical inference setup. It does not establish that generated specifications capture user intent.

The central gap is already addressed in part by [SpecRL](https://www.alphaxiv.org/abs/2604.05820), first submitted 2026-04-07, which trains against impossible input-output pairs admitted by weak specifications, and [Spec-Harness](https://www.alphaxiv.org/abs/2604.00280), first submitted 2026-03-31, which measures behavioral adequacy beyond verifier pass rate.

A better first question is whether adversarial specifications and counterexamples generalize to unseen semantic defects without excluding legitimate implementations.

Freeze the intended behavior through an independent reference or expert-reviewed contract. Give a challenger the job of finding incorrect programs that satisfy a candidate specification. Check counterexamples with execution or formal tools. Measure both rejected incorrect behavior and retained valid alternatives, including precondition coverage and vacuity. The challenger model is a proposal source, not the source of truth.

Only consider co-training after this evaluator distinguishes genuine improvement from weaker specifications or artificially narrow input domains. Three learning agents can optimize the same defective objective. Call the goal resistance under a stated threat model, not spec-hacking-proof software.

## 4. Four-bit formats: feasible numerics, unproven hardware payoff

[UFP4](https://www.alphaxiv.org/abs/2606.20381), submitted 2026-06-18, studies rounding-bin geometry and its interaction with training recipes. It already evaluates uniform-grid recipes with long-run dense and MoE experiments. Repeating a generic grid sweep at a smaller scale is not sufficient differentiation.

[HiFloat4 pretraining](https://www.alphaxiv.org/abs/2604.08826), first submitted 2026-04-09, revised 2026-09-25, is especially instructive: section 1 states that its experiments simulate quantization around BF16 GEMMs, and do not measure native throughput, latency, or energy. Its NVFP4 failure is conditional on recipe choices, particularly the absence of per-tensor scaling. It is not evidence that native NVFP4 training always diverges.

An H100 is suitable for a numerical emulation study. It cannot establish the throughput or joules of a nonexistent H100 FP4 tensor instruction. Any claim about silicon needs a separate hardware cost model or measurements on appropriate devices. NVIDIA's [H100 specifications](https://www.nvidia.com/en-sg/data-center/h100/) and [HGX component documentation](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) define the actual hardware context.

The useful question is which part of the representation and training recipe controls failure: value grid, block size, scale encoding, rounding, clipping, accumulator precision, or tensor-specific assignment. Do not change all of them at once.

A credible study would compare matched effective storage, including scale metadata, and separately tuned baselines. Use BF16 references, declared forward/backward quantization boundaries, matched tokens, and multiple seeds. Begin with numerical diagnostics and a small training scale, then establish whether the effect persists at larger scale and longer training. If a tuned existing recipe removes the advantage, do not claim a new format contribution.

## 5. Switchable attention: the memory claim needs a different mechanism

[LLaDA-Hybrid](https://www.alphaxiv.org/abs/2608.06628), submitted 2026-08-06, really does replace 6 of 20 layers in a 16B diffusion model. Its abstract says approximately 60 hours; section 4 specifies 24 plus 6 elapsed hours on two L40S GPUs, which is 60 GPU-hours. Serving is measured on an H200. That is not a direct H100 training-time estimate. Quality is also not unchanged on every task; the paper reports an 8.1-point GPQA-Diamond drop.

[Oryx / Multi-Mixer Models](https://www.alphaxiv.org/abs/2605.28769), submitted 2026-05-27, supports sequence-axis switching and reports retrieval using attention on fewer than 10% of tokens. However, section 6 states that switching requires maintaining both the KV cache and recurrent state at every step. The current assignment is static; learned routing is proposed as future work. Fewer attention computations are not equivalent to discarding most stored keys and values.

Converting an autoregressive checkpoint is a plausible adaptation experiment, but it does not inherit the diffusion model's gains. The candidate question must identify how to avoid maintaining full history while retaining the ability to recover information when attention is needed.

Compare fixed hybrids, sliding-window attention with sinks, and the unmodified checkpoint at matched quality and measured memory. Include late retrieval requests and requests that require information skipped by the recurrent representation. Charge for rebuilding a cache or replaying a prefix. Report end-to-end throughput, not just a count of skipped attention operations.

Stop if the router needs both complete states, cache reconstruction eliminates the benefit, or an existing static/windowed design dominates the quality-memory tradeoff. This direction has the greatest risk of spending the cluster budget before the basic mechanism is distinguished from prior work.

## What to do first

1. Choose kernel verification for a bounded candidate audit, not immediate large RL training.
2. Reuse the existing source pinning, containers, run manifests, traces, checkpoints, and cost accounting. Do not rewrite them to make the project look new.
3. Establish where current kernel validators fail on an independently checked, held-out corpus.
4. Measure validator cost and uncontended H100 timing before deciding the training layout.
5. Require a second checkpoint and a fresh-job resume before any long training allocation.

Proposed experiments require their own frozen contracts, budgets, and seeds. Use at least seeds 42, 43, and 44 for pilot interpretation; seed count alone is not a power calculation. Evaluate uncertainty at the workload or problem-family level rather than treating many correlated outputs as independent samples.

The present assessment does not authorize or launch an experiment. It does not promote a direction, assign a Research Gauntlet score, or certify publication isolation. It has no independent signed review or real-model compute attestation. Full novelty admission remains incomplete, including the required query coverage per candidate.

## Execution and coverage

- Read-only SSH inspection confirmed eight H100 80GB HBM3 devices, each idle at inspection, and an empty Slurm queue.
- Nineteen ORX discovery calls ran on the H100 host. Eleven web search queries supplemented exact citation and hardware identification. The 30-query cap is exhausted; no broader coverage claim is made.
- ORX window: 2025-01-01 through 2026-10-06, recency priority. Web fallback did not enforce that window; the hardware sources can be older, and cited paper dates were checked individually.
- The ORX ranked set had fifteen papers, followed by two focused primary-text checks to resolve the exact Dafny percentage and unnamed June paper. Text was inspected in the sections relevant to the claims, not independently replicated.
- Search coverage excludes a full patent search, a full citation-graph audit, exhaustive non-English coverage, and current source-code execution. Recency-weighted retrieval can miss older but decisive baselines.
- Research archive: `/home/kevin/cotcodec-runs/frontier-research/2026-10-06-five-directions-v1`.
- No new model inference, GPU jobs, package upgrades, system changes, or public publication. Existing research data and unrelated work remain untouched.
- The wiki freshness check separately flags overdue system-health reporting, Obsidian and AI-session syncs, lint/index maintenance, and self-heal. These are recorded maintenance items, not blockers for this assessment.

The literature and experimental-design procedures changed this recommendation in concrete ways: correctness is separated from speed, selectors are separated from allocators, and simulated numerical results are separated from hardware performance claims.
