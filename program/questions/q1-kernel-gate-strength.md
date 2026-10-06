# Q1: Kernel correctness-gate strength

Status: Stage 0 (gate building). Role: lead question. Dossier entry:
`C2-kernel-verification-rl`, rank 1, PURSUE-NARROWED.

## Question

With the base kernel policy, RL algorithm, task split and total H100 time
(rollouts plus verification) held fixed, does training against a strong
hidden-input, multi-shape correctness gate produce more held-out kernels that
are both correct under an independent audit and faster than a TF32 PyTorch
baseline? Compare it with the standard KernelBench check and a narrow
anti-hacking check. Before any RL, measure how often each gate accepts the
frozen policy's own wrong kernels.

## Why it is narrowed, not new

- Gating speed on correctness is not new. KernelZero's CA-GRPO and Dr. Kernel's
  KernelGYM already do it. The live variable is gate strength.
- Offline checker audits exist. Measuring the Checker finds the official
  KernelBench check misses 16.9% of witnessed faults. The Contract-Grade
  Verifier finds 39.5% of 2,638 accepted kernels broken.
- Unclaimed: gate strength as a matched-budget RL variable, with on-policy
  false-accept rates and an independent held-out audit.

A negative result is plausible and still useful. Measuring the Checker's
realism probe found only 3 of 60 LLM-written kernels incorrect, and 2 of those
were crashes any gate catches.

## Closest priors

| Paper | Date | Delta |
|---|---|---|
| [Measuring the Checker](https://arxiv.org/abs/2609.22220) | 2026-09-02 | Audits checkers at scale on H100; no policy RL, no on-policy false accepts |
| [Dr. Kernel / KernelGYM](https://arxiv.org/abs/2602.05885) | 2026-02-05 | RL with vs without a narrow hacking check; no graded gate strength |
| [KernelZero](https://arxiv.org/abs/2609.33074) | 2026-09-27 | Correctness-gated GRPO with the standard check, on A100; code repo returns 404 |
| [Contract-Grade Verifier](https://arxiv.org/abs/2608.12700) | 2026-08-13 | 12 adversarial gates, one uncontrolled gated GRPO arm; two-author preprint |
| [KernelBench-Verified](https://arxiv.org/abs/2607.16241) | 2026-06-26 | TF32 baseline moves best geomean from 1.43x to 0.88x; hidden suite has no shape variation |

Also checked from Codex's list: CUDA-Harness (2609.00058), CAKE (2608.12629),
KernelPro (2606.26453) and AI as a Compiler (2609.36800). None runs a
correctness-reward RL comparison.

## Stage 0 deliverables (no model-generated code on GPUs)

1. Gate (a): the official KernelBench five-input allclose check.
2. Gate (b): the KernelGYM hacking check.
3. Gate (c): hidden values (KernelBench-Verified transforms), shape variation
   (robust-kbench style), unaligned remainder shapes.
4. Independent audit no gate sees: contract-grade tolerance-free checks, an
   fp64 oracle, unseen shapes and dtypes.
5. Validate every gate on benchmark reference kernels and deterministic mutants
   of them. These are not model output, so they may run on the current stack
   inside the research container through Slurm.
6. Timing harness: randomized paired order, warmup, one subprocess per GPU,
   one or two dedicated timing GPUs, watchdog timeouts.

## First experiment: on-policy false-accept audit (about 12 GPU-h)

Freeze Dr. Kernel-8B. After a 0.5 GPU-h vLLM throughput calibration, sample 8
completions on about 250 KernelBench L1/L2 and KernelGYM tasks, about 2,000
kernels. Score each with gates (a), (b), (c) and the independent audit. Report
each gate's false-accept rate with bootstrap confidence intervals and per-kernel
GPU-seconds. The estimate ranges from 9 to 25 GPU-h.

**Blocked on:** the R580 driver upgrade or Kevin's written risk acceptance,
because model-generated kernels are untrusted code on R570. The run is over 8
GPU-h, so the research gauntlet applies.

## Kill criteria (pre-registered)

- Proceed to the three-arm, three-seed RL comparison (about 1,000-1,400 GPU-h,
  gauntlet required) only if gates (a) and (b) false-accept at least about 3 pp
  more of the policy's accepted kernels than gate (c), with non-overlapping
  intervals, and gate (c) costs at most about 2x gate (b) per rollout.
- Otherwise publish the negative: gates barely differ on-policy.
- If the frozen policy emits too few audit-rejected kernels to estimate
  false-accept rates, that is itself the decisive negative.

## Stage 2 arms (only past the kill criteria)

Unchanged model at matched search budget; supervised learning on accepted
examples; RL with the baseline reward; RL with the stronger reward. Held-out
operator families, shapes and input distributions. Report false accepts, false
rejects, valid-and-fast rate, wall time, GPU-hours, compile cost and verifier
cost. Never report only the fastest survivors.
