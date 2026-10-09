# Q2: Calibrated computer-use instrument

Status: Stage 0 (CPU only). Role: spine; its noise floor is the prerequisite
for every later computer-use claim. Dossier entry:
`S1-calibrated-cua-instrument`, rank 2, PURSUE-NARROWED.

## Question

On desktop computer-use tasks from an offline OSWorld-Verified subset, within
one open-weight family at four sizes (Qwen3.5-4B, 9B, 27B, 35B-A3B), how much of
the task-level variation in success comes from the agent harness and from the
observation type, and how much is plain rerun noise? Measure it after removing
infrastructure failures and correcting the benchmark's own state checkers by
mutation testing. Does the harness-plus-interface share shrink as the model
grows?

## Why it matters

- 15.3% of audited FAIL verdicts on computer-use benchmarks are wrong
  (2607.28367).
- Harness choice moves a 4B coding model from 8.3% to 37.2% while a large model
  is unchanged (FrogNano, 2609.07925). The scale question has only coding
  evidence today.
- Rerunning the same observation mode flips 12-14% of web outcomes
  (2608.06171).

Mutation testing of computer-use state checkers has no prior found. The nearest
are a hand audit of false negatives (2607.28367) and kernel-oracle mutation
(2609.22220). This piece is cheap and ships first as a short note.

## Closest priors

| Paper | Date | Delta |
|---|---|---|
| [cua-speedrun](https://arxiv.org/abs/2609.40284) | 2026-09-30 | Harness x model x five seeds on OSWorld; screenshots only, no scale ladder, no noise floor, no checker testing |
| [Routing Is Least Learnable...](https://arxiv.org/abs/2608.06171) | 2026-08-06 | Observation modes x scale with a rerun band; web only, band measured in 2 of 8 cells |
| [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651) | 2026-09-30 | Variance decomposition method; repeated cells rare, no desktop or interface factor |
| [How Benchmarks Mis-Score CUAs](https://arxiv.org/abs/2607.28367) | 2026-07-30 | Hand audit of FAIL verdicts; false negatives only |
| [What Does a Harness Buy?](https://arxiv.org/abs/2610.04433) | 2026-10-03 | Coding analogue; harness swap and rerun each flip 13% of tasks |

## Stage 0 (CPU only, 0 GPU-h, about 2-3 days)

1. **Evaluator mutation kit.** Apply about 40 state-mutation operators to the
   pinned OSWorld evaluators on a 120-task, web-free, domain-stratified subset.
   Report per-evaluator false-negative and false-positive rates.
2. **Action-path suite.** Port cua-speedrun's App. I.1 suite to the nested-KVM
   runtime and the Qwen3.5 reference harness. Fix the Table 20 bugs: modifier
   release, dropped multi-tool calls, middle-click.
3. **Holo3 archive diff.** Diff the two public Holo3-35B-A3B trajectory
   archives in `xlangai/ubuntu_osworld_verified_trajs` per task, to decide
   whether their 4.4 pp gap is rerun noise or an operator contrast. The
   download is about 14.9 GB and needs Kevin's OK.

## Stage 1 (rescoped 2026-10-08; drafts, not frozen)

Drafts on branch `stage0/q2-stage1-rescope`:

- Gauntlet proposal: [`program/proposals/2026-10-08-q2-stage1-rescoped.md`](../proposals/2026-10-08-q2-stage1-rescoped.md)
- Draft preregistration of the first stage: [`program/preregistrations/q2-stage1-rescoped-v1.md`](../preregistrations/q2-stage1-rescoped-v1.md)

Status: DRAFT; gauntlet wave 0 (synthesis only), revised after three
adversarial pre-freeze reviews of the S1a draft (2026-10-08; every blocking
item fixed, preregistration section 22).

Why the original design was rescoped:

- `serving-throughput-probe-v2` priced it at 431.5 GPU-h (job 466).
- The pinned upstream sources show that both certified harnesses fold their
  history, think by default and read screenshots only. The cheap profile the
  earlier budgets used therefore prices neither harness, and the
  accessibility-tree arm cannot run on them.

**S1a: runs without the gauntlet; registered caps at most 7.967 GPU-h in
every branch.**

- Qwen3.5-4B and 9B x H-OSW-fixed and H-GA. Screenshot only, thinking on with
  2,048 output tokens, T = 15, greedy decoding.
- A base of 24 or 32 of the 116 usable confirm tasks (an A0-derived rule; 24
  when the anchor runs), plus a cost-based fill rule whose extension blocks
  enter only a secondary analysis set.
- Two serving sessions per size, at least 12 h apart, with 2 reruns each;
  every estimand is stated for the realized sessions.
- An OpenCUA-7B 15-step anchor against its three public runs (D11), read
  before the factorial, sized from its smoke run (64-96 tasks at N* >= 32).
- Outputs: the between- and within-session noise floor, the harness main
  effect, the mean squared per-task harness effect and harness share, the
  first real per-episode cost card, P1-P5, and a GO/NO-GO for the scale ladder
  (DR5, with the ladder's detectable share frozen at 0.13).
- Gated on:
  - the action-path v2 acceptance (C1-C4, A1-A6 on one attempt) and an N*
    of at least 16;
  - the CPU-only G0 items;
  - a decision admitting the pre-freeze development jobs;
  - a D29-style decision on OpenCUA's `--trust-remote-code`;
  - Kevin's sign-off on three items: D47's task floor (24 when the anchor
    runs), DR1 in place of the 122B-A10B swap, and DR5 in place of the 7-8 pp
    line.

**S1b: over 8 GPU-h; only on S1a's DR5 GO (D47); gauntlet and D24.** A
replay-only serving probe v3 comes first, then the harness scale ladder with
27B-FP8 and 35B-A3B-FP8 added (32 GPU-h central, 41 high, at the card's
unmeasured multipliers). After NO-GO or INCONCLUSIVE no S1b runs; an
observation study on a certified harness variant that reads the accessibility
tree, or more sessions at 4B and 9B, would each be a new proposal.

The proposal also asks to restate the "paired MDE about 7-8 pp" kill line
below in share units, as DR5 does. Kevin ruled on 2026-10-09 (D55): for S1a,
DR1 replaces the 122B-A10B swap and DR5 replaces the paired-MDE line, and S1a
is read unanchored (every output labelled "not externally anchored"; nothing
replaces the Holo3 2-SE line, because no anchor runs). The lines below are
kept as written for the record and for any design outside S1a.

The original design is kept for the record: four sizes x 2 harnesses x 2
observations x 3 reruns x 120 tasks (5,760 episodes), plus a Holo3 rerun on
359 tasks, estimated at 15-90 GPU-h.

## Kill criteria

- No GPU episodes until the action-path suite passes 100%.
- If the Holo3 diff traces the 4.4 pp gap mostly to infrastructure or operator
  differences, do not use the pair as a noise anchor.
- If the Holo3 rerun lands more than 2 SE outside the range of the two official
  rows, stop and debug the harness before reading the factorial.
- If Qwen3.5-4B is below 10% success on more than 80% of cells, swap it for
  122B-A10B.
- If the harness-plus-interface share at 4B vs 27B/35B-A3B differs by less than
  the paired MDE (about 7-8 pp, estimate), report no detectable shrinkage.
- If nested KVM cannot host about 40 VMs or the qcow2 reset path fails, cut the
  task count before adding GPUs.

## Modules folded in

- Timing census (dossier `C1`): per-episode cost card with settle time, queue
  wait and stale-dispatch counts.
- Interface main effects from the dropped Relay lab (`E9`).
