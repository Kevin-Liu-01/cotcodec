# CoTCodec research program (restarted 2026-10-06)

Status: Stage 0. No experiment from this program has run yet. Nothing here is
a result, a novelty claim, or a gauntlet score.

## Thesis

For verifiable machine work, the checker decides what an agent learns and what
a leaderboard says. GPU kernels and desktop computer use are two such kinds of
work. A wrong checker silently rewards wrong programs; an uncalibrated
benchmark reports noise as progress. Before training on a checker or claiming a
difference on a benchmark, measure the checker's false-accept and false-reject
rates against an independent audit, and measure plain rerun noise.

Eight H100s fit this thesis in two ways. They run the policy models. They also
execute the work being checked: kernels are timed and audited on the same
hardware, and desktop tasks run in nested-KVM virtual machines on the same host.

## Why the restart

The previous program studied orchestration variables for tool-using agents,
with Paper 1 on reasoning language, a memory-policy line, and the D17-D22
architecture lines. It built solid infrastructure: digest-pinned Docker images,
Slurm submission with provenance, OpenResearch (`orx`) run ledgers, receipts
and attestation. Its questions did not survive a verification pass on
2026-10-06:

- Paper 1's routing claims failed the correctness gate. The claims in its
  direction doc are withdrawn.
- The memory lifecycle audits fell below the significance bar. The audited
  Letta `memory()` tool was removed upstream in PR #4745.
- D17's causal memory holdout is occupied by CMP (arXiv 2610.02070).
- Across about six weeks, the node logged under 10 recorded GPU-hours, well
  under 1% of its capacity.

The old work is preserved read-only under `legacy/` and at git tag
`legacy-2026-10-06`. See `legacy/INDEX.md`.

## How the questions were chosen

Codex produced a research reset and a five-direction ranking on 2026-10-06.
Those documents and the existing program supplied 15 candidates; a separate
H100 sweep added three. All 18 were verified against primary sources and
ranked by three independent judges.

- 102 distinct cited URLs were audited: 95 OK, 7 fixed, 0 removed.
- Codex's five-direction document had 44 claims checked at the source: 42
  verified, 2 corrected, neither changing a premise.
- Ranking gates: lowest judge correctness at least 5 and lowest citability at
  least 6, then mean significance, novelty residual and feasibility.

Evidence is in [`evidence/2026-10-06/`](evidence/2026-10-06/). The full ranked
dossier with corrected questions, closest priors and kill criteria is
[`question-dossier.md`](evidence/2026-10-06/question-dossier.md).

## The three questions

| # | Question | Role | First experiment | Gate before GPU |
|---|---|---|---|---|
| Q1 | [Kernel correctness-gate strength](questions/q1-kernel-gate-strength.md) | Lead | On-policy false-accept audit, about 12 GPU-h | R580 driver upgrade or Kevin's written risk acceptance; gauntlet |
| Q2 | [Calibrated computer-use instrument](questions/q2-calibrated-cua-instrument.md) | Spine | Stage 0 is CPU-only; Stage 1 about 60 GPU-h | Action-path suite at 100%; gauntlet |
| Q3 | [Cross-script sparse-indexer recall](questions/q3-cross-script-indexer.md) | Backfill | K1 screen, about 1.5 GPU-h | GPU entry point, rebuilt image, checkpoint receipt |

**Q1.** With the policy, RL algorithm, task split and total H100 time fixed,
does training against a stronger hidden-input, multi-shape correctness gate
yield more held-out kernels that are both correct under an independent audit
and faster than a TF32 PyTorch baseline? First measure how often each gate
accepts the frozen policy's own wrong kernels. Offline checker audits already
exist (arXiv 2609.22220, 2608.12700); the open variable is gate strength under
on-policy RL.

**Q2.** On an offline OSWorld-Verified subset, within one open-weight family at
four sizes, how much task-level variation comes from the harness and the
observation type, and how much is rerun noise, after removing infrastructure
failures and correcting the benchmark's own checkers by mutation testing? Does
the harness-plus-interface share shrink with scale? The checker-mutation piece
has no prior found for computer use and ships first.

**Q3.** Do KL-distilled top-k sparse-attention indexers on frozen checkpoints
miss more cross-script evidence than the dense model's own top-k at the same
token budget? Only if they do, test an alignment loss on the indexer. This is
the only live code carried over: the D21 contract and its CPU doctor.

Q1 and Q2 share one method, mutation analysis of a checker, applied to two
objects: kernel oracles and computer-use state checkers.

## Staged plan

**Stage 0: now, no untrusted code on GPUs.**

1. Q2: build the evaluator-mutation kit for the OSWorld-Verified checkers and
   report per-checker false-negative and false-positive rates. Ship it as a
   standalone short note, because scoop risk is high.
2. Q2: port the cua-speedrun action-path suite (arXiv 2609.40284, App. I.1) to
   the nested-KVM runtime and fix the known harness bugs.
3. Q2: diff the two public Holo3-35B-A3B trajectory archives per task. The
   download is about 14.9 GB and needs Kevin's OK.
4. Q1: build gates (a) official allclose, (b) KernelGYM hacking check and (c)
   hidden values plus shapes, and the independent audit. Validate them on
   benchmark reference kernels and deterministic mutants, not model output.
5. Q3: write the GPU entry point, rebuild the image with tilelang and peft,
   fetch a `qwen3-0.6b-base` receipt, then run K1.

**Stage 1: gated, each over 8 GPU-h, so the gauntlet applies.**

- Q1 on-policy false-accept audit, about 12 GPU-h. It runs model-generated
  kernels, so it waits for the R580 upgrade or a written risk acceptance.
- Q2 Qwen3.5 ladder, about 60 GPU-h: 4 sizes, 2 harnesses, 2 observations, 3
  reruns, 120 tasks.

**Stage 2: only past Stage 1 kill criteria.**

- Q1 three-arm, three-seed RL comparison, about 1,000-1,400 GPU-h.
- The Q2 noise floor unlocks the backlog's locale and transfer studies.

All GPU-hour figures are estimates. The only throughput measured on this node
is training: 282,501 tok/s for a 134M GDN hybrid. A 0.5 GPU-h vLLM throughput
probe on one VLM and one LLM comes before any budget is frozen.

## Backlog and dropped lines

[`backlog.md`](backlog.md) holds the ordered backfill queue and every dropped
line with its reason. Dropped lines stay dropped unless new evidence reverses
the reason.

## Where this agrees and differs from Codex

Codex's recommendation is kept where it held up:

- Kernel verification leads, as a bounded audit before any large RL.
- Correctness, formal proof and speed are separate fields; speed is rewarded
  only after correctness.
- Existing source pinning, containers, manifests and cost accounting are
  reused, not rewritten.
- Timing uses randomized paired order on uncontended GPUs; seeds 42, 43, 44 at
  minimum; uncertainty at the problem-family level.

It differs in four places, each from the verification pass:

1. **First step for Q1.** Codex proposed a frozen bank of correct and wrong
   kernels. That offline audit already exists (arXiv 2609.22220, 2608.12700,
   2607.16241). The open first step is the on-policy false-accept rate.
2. **Answer selection** was Codex's second choice. It moves to the backlog:
   each component is covered (arXiv 2607.17531, 2608.03961), and hidden-state
   probes are prior art (ReProbe, arXiv 2511.06209).
3. **Specification robustness** was Codex's third choice. It is dropped:
   SpecRL (arXiv 2604.05820) and Spec-Harness (arXiv 2604.00280) cover weak
   specifications, and the remaining part is a methods note.
4. **Computer use** gets its own question (Q2). Codex's reset covered computer
   work, but its ranking left it out.

FP4 formats (Codex's fourth) are in the backlog. Switchable attention (fifth)
is dropped, because existing switching does not remove the KV cache.

## Hardware track

Hardware work is about making the node safe and measurable, not new silicon.
It needs a host administrator, since the research account has no root. The
list is in [`../docs/h100-node.md`](../docs/h100-node.md). The upgrade that
gates Q1 is the R580 driver with a matching fabric manager. Driver R570 is end
of life.

## Rules that apply

- `.claude/rules/research-gauntlet-loop.md` for any new mechanism or any run
  over 8 GPU-hours.
- Every GPU run uses a digest-pinned image, Slurm, persistent checkpoints and a
  fresh-job resume test. See [`../docs/operations.md`](../docs/operations.md).
- No untrusted model-generated code (sampled kernels, policy rollouts) runs
  with GPU access on the R570 stack. Reviewed, committed harness code is
  project code.
- This repository is public. No secrets, host addresses, employer-internal
  material or private datasets.
