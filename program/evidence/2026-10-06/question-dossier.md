# Research-question dossier: verified and ranked (2026-10-06)

Eighteen candidate questions: 15 from the Codex research reset and the existing program (C1-C6, E1-E9) and 3 from the October H100 sweep (S1-S3). Every entry states the corrected question, not the original one.

## How to read this

- **Rank** is the mechanical aggregate order. A candidate must clear two gates across all three judges (lowest correctness at least 5, lowest citability at least 6). Ties are then broken by mean significance, then novelty residual, then feasibility. E1, E7, C6 and E9 fail the correctness gate, so they sit at the bottom.
- **Recommendation** is the judges' majority verdict. It is not the rank. Two examples: C2 ranks first but is gated behind a security upgrade, and S3 ranks fourth but cannot start until its prerequisites exist.
- **Scores** are three-judge means on a 0-10 scale. Each score judges the corrected question.
- **GPU-hours** are estimates unless stated otherwise. The only throughput measured on this node is training: 282,501 tok/s for the 134M GDN hybrid. Before any budget is frozen, run a 0.5 GPU-h vLLM throughput probe on one VLM and one LLM.
- **URLs** come only from sources opened in the review files. Items that could not be confirmed are marked UNVERIFIABLE in the anchor status.

## Merges

None. No two candidates ask the same question, so the provisional order is kept unchanged. Four pairs overlap closely enough to be worth naming:

- **E9 and S1/S2.** S1 absorbs E9's interface main effects, and Relay becomes the shared fixture. E9's leftover question (how the site guide and history interact with the interface) appears in neither S1 nor S2.
- **E1 and S2.** E1's reasoning-language question survives as S2's arm (d), so E1 is dropped as a standalone line.
- **C1 and S1.** C1's timing census belongs in WS1's per-episode cost card. Its readiness gate is a separate question and is likely to lose.
- **C2 and S1.** Both use the same checker-mutation method (2609.22220), but on different objects: kernel oracles in C2, computer-use state checkers in S1.

## Summary table

| # | Key | Title | Rec. | Sig | Corr | Cite | Nov | Feas | First exp. GPU-h |
|---|---|---|---|---|---|---|---|---|---|
| 1 | C2-kernel-verification-rl | Correctness-gate strength in kernel RL | PURSUE-NARROWED | 6 | 6.33 | 8 | 4.67 | 5 | 12 |
| 2 | S1-calibrated-cua-instrument | Harness, interface and scale effects on open-weight computer-use agents vs rerun noise | PURSUE-NARROWED | 6 | 6 | 9 | 4.33 | 6.33 | 60 |
| 3 | E6-d21-translation-supervised-indexer | Do learned sparse-attention indexers drop cross-script evidence? | BACKFILL | 5 | 6.67 | 8 | 5.33 | 6 | 1.5 |
| 4 | S3-interface-locale-rl-transfer | Does RL on one GUI interface or UI language transfer to the others? | PURSUE-NARROWED | 5 | 5 | 7 | 5 | 3 | 150 |
| 5 | S2-aligned-locale-language | Arabic in computer-use agents: script vs mirrored layout | PURSUE-NARROWED | 4.67 | 6 | 8.67 | 5.33 | 5.67 | 15 |
| 6 | C1-timing-resource-control | Wait, queue or act: timing in self-hosted computer-use agents | BACKFILL | 4.67 | 5.67 | 8 | 5 | 6 | 2.5 |
| 7 | E4-d19-icl-rule-distillation-port | Distilling in-context learning into a portable write rule | BACKFILL | 4.67 | 5 | 8 | 5 | 6 | 2 |
| 8 | C5-fp4-instability-factors | What drives FP4 training instability: grid, scale format, block size or rounding? | BACKFILL | 4.67 | 6.67 | 8.67 | 4 | 6.33 | 47 |
| 9 | C3-selection-and-allocation | Do answer selection and per-question re-attempts stack? | BACKFILL | 4.33 | 6.67 | 7.67 | 3.67 | 7 | 6 |
| 10 | C4-specification-robustness | Is adversarial spec weakness a property of the spec or of the attacker? | DROP | 4 | 6 | 8 | 4 | 5 | 10 |
| 11 | E3-d18-translation-byte-boundaries | Translation-supervised boundaries in byte-level models | BACKFILL | 4 | 5.33 | 8.33 | 4 | 3.67 | 0.5 |
| 12 | E2-d17-causal-memory-holdout | Randomized first use of a stored memory to measure its value | DROP | 4 | 5.67 | 8.33 | 3 | 5.67 | 6 |
| 13 | E5-d20-semantic-clock-gate-parity | Do recurrent-state gates penalize languages that need more tokens? | BACKFILL | 3 | 5.67 | 8 | 4 | 6 | 3 |
| 14 | E8-memory-lifecycle-audits | Storage-level lifecycle audit of agent memory libraries | DROP | 2.67 | 5 | 6.33 | 3.67 | 8.33 | 0 |
| 15 | E1-paper1-language-routing | Reasoning-language routing for tool-using agents (Paper 1) | DROP | 4 | 5 | 8.33 | 3.33 | 4.33 | 20 |
| 16 | E7-d22-translation-equivariant-writes | Translation-equivariant recurrent-state writes | BACKFILL | 3 | 4.67 | 8.33 | 3.33 | 5.33 | 2.5 |
| 17 | C6-switchable-attention-recovery | Discard-and-rebuild attention for bounded GPU memory | DROP | 3 | 3.33 | 7.67 | 3 | 6.67 | 8 |
| 18 | E9-relay-interface-context-lab | Relay interface, guide and history lab | DROP | 3 | 4.67 | 8.33 | 2 | 4.67 | 6 |

## What to do now

1. **S1 Stage 0** (0 GPU-h). Run the computer-use evaluator-mutation kit first and ship it as a standalone short note, because scoop risk is high. In parallel, diff the two Holo3 archives per task; that download is about 14.9 GB and needs Kevin's OK. Run the ~60 GPU-h Qwen3.5 ladder only after both are done.
2. **S2 Phase 0** (0 GPU-h). Build the localized Relay and its oracle gate. The ~15 GPU-h RTL split runs only if a power gate shows the MDE is about 5 pp or less.
3. **Gated work.**
   - C2's ~12 GPU-h on-policy false-accept audit waits for the R580 security upgrade or Kevin's written risk acceptance.
   - S3's ~150 GPU-h pilot waits for four things: the template factory (at least 100 templates), a working pixel harness, a shared action space, and a read of the Cobra PDF.
4. **Preemptible backfill, in order:** E6 K1 (1.5 GPU-h), C1 census inside WS1, the E4 gate, C5 Phase 1, C3 Stage 0, the E3 headroom probe, the E5 decomposition and the E7 G1 gate.
5. **Drop as lines:** C4, E2, E8, E1, C6 and E9. Two of these still leave follow-up work:
   - E8: disclose two security-relevant Letta observations to the maintainers regardless [details withheld pending coordinated disclosure to the maintainers].
   - E1: withdraw the claims in directions/01.

## Source verification summary

**arXiv IDs.** The three judges each checked every arXiv ID they could find in the candidates, covering 87, 89 and 111 IDs respectively. Every ID exists with a matching title.

**Date skews.** Two IDs imply a different month from the published date. Neither changes a premise:
- 2609.27917 was published 2026-08-21.
- 2608.26175 was published 2026-07-27.

**OpenReview.** The ICLR 2027 submissions exist according to the api2 search, but only their abstracts were readable.

**Unverifiable or weak:**
- Cobra: whether it cross-evaluates its fixed-observation controls. The PDF sits behind the OpenReview challenge.
- The KernelBench-M artifact URL.
- The KernelZero GitHub repo, which returns 404. The paper itself exists.
- E8's alphaXiv-slug "Beyond Recall Accuracy" and the SSRN "Deletion Is Not Forgetting". Neither is used as an anchor here.
- The Zenodo FP4 2x2 study. It exists, but no reviewer opened its contents, so it is named in the text only.

**Relay.** Facts about Relay were re-checked read-only in ~/repos/Relay:
- `locale: 'en-US'` is set at environment.mjs:64.
- The a11y observation is `ariaSnapshot()` plus a role/name element list with no coordinates.

## Citation audit (final edit)

A final citation audit checked all 102 distinct cited URLs. It returned 95 OK, 7 FIX and 0 REMOVE verdicts. No new URLs were added. Because nothing was removed, every entry keeps at least 5 anchors, all entries still pass the gates, and the rank order is unchanged. The fixes applied:

- **KernelZero (2609.33074):** the alphaXiv URL was swapped for the canonical arXiv URL and the full title restored. CA-GRPO is a contribution named in the abstract, not part of the title.
- **Contract-Grade Verifier (2608.12700):** the full title was restored (", and a Native Blackwell Backward for the Gated-Linear-Recurrence Family"). It is a two-author industry preprint without peer review.
- **FrogNano (2609.07925):** the paraphrased "title" was replaced with "FrogNano: Training a 4B Coding Agent via Online Task Synthesis". The 8.3% to 37.2% harness-sensitivity finding is in the body text.
- **HEAR (2610.06597):** the real title was restored ("Can Agent Harnesses and Inference Engines Hear Each Other? The HEAR Protocol for Agentic LLM Serving").
- **MAGNET (2407.08818):** the real title was restored ("MAGNET: Improving the Multilingual Fairness of Language Models with Adaptive Gradient-Based Tokenization").
- **NVFP4 pretraining (2509.25149):** the v2 revision date was corrected from 2026-03-06 to 2026-03-04.
- **ASIL (2608.26991):** the date was corrected from 2026-08-26 to 2026-08-27.

Caveats on OK verdicts. Three OpenReview ICLR 2027 submissions (Cobra, HINT, One Policy Many Harnesses) were confirmed from the abstract only, because the PDFs sit behind a bot check. The Relay citation is a private local path. 2610.03136 is an EMNLP 2026 workshop paper, not a main-conference paper.

---

## 1. Correctness-gate strength in kernel RL

`C2-kernel-verification-rl`. Origin: Codex ranking doc #1. **Recommendation: PURSUE-NARROWED.**

Scores (3-judge means): significance 6, correctness 6.33, citability 8, novelty residual 4.67, feasibility 5.

**Corrected question.** With the base kernel policy, RL algorithm, task split and total H100 time (rollouts plus verification) held fixed, does training against a strong hidden-input, multi-shape correctness gate produce more held-out kernels that are both correct under an independent audit and faster than a TF32 PyTorch baseline, compared with the standard KernelBench check or a narrow anti-hacking check? Before any RL, measure how often each gate accepts the frozen policy's own wrong kernels.

**What was wrong with the original.** Four premises failed. (1) Using correctness as a hard gate before the speed reward is not new: KernelZero's CA-GRPO and Dr. Kernel's KernelGYM already gate speed on correctness, so the live variable is gate strength, not gating. (2) The proposed first step, auditing validators on a frozen corpus of correct and subtly wrong kernels, is already done: Measuring the Checker injects 10,303 faults into 188 KernelBench problems and finds the official check misses 16.9% of witnessed faults; the Contract-Grade Verifier finds 39.5% of 2,638 accepted kernels broken; the Correctness Illusion audits seeded bugs. (3) The cited sources were the wrong ones: KernelPro, CAKE, KernelAgent and AI-as-a-Compiler do no correctness-reward RL, and the closest work was missing. (4) 'Matched compute' and 'faster' were undefined: verifier cost differs by arm, and the baseline choice moves KernelBench-Verified's best geomean from 1.43x to 0.88x. Further corrections: KernelBench-Verified has no hidden shapes (only four value transforms), the KernelBench-M artifact URL could not be found, the KernelZero GitHub repo returns 404, and KernelZero's numbers are on A100, not H100. No merge: this shares a method prior with S1's evaluator mutation but is a different object (kernel oracles vs computer-use state checkers).

**Novelty.** NARROWED. Measuring the Checker (2609.22220) audits kernel checkers and frames them as RL rewards but runs no RL. Dr. Kernel (2602.05885) ablates only 'hacking check vs none'. KernelZero CA-GRPO gates speed on the standard (weak) check. The Contract-Grade Verifier (2608.12700) ran one uncontrolled contract-gated GRPO arm. Unclaimed: gate strength as a matched-budget RL variable, with on-policy false-accept rates and an independent held-out audit.

**Why it matters.** Kernel-generation RL is reward-hacking-prone, and four 2026 preprints show the standard checker is too weak. A matched-budget comparison of gate strength would be cited by the KernelGYM, TritonRL, CUDA Agent and KernelZero lines and by RLVR-verifier work. A negative is plausible and still useful: Measuring the Checker's realism probe found only 3 of 60 LLM-written kernels incorrect (2 were crashes any gate catches), so policies may rarely emit the subtle faults a strong gate exists to catch. Significance is capped at 6 because the area is crowded and moving fast (RESOLVE 2610.05683, Contract-Grade Verifier, Measuring the Checker could scoop the RL arm).

**Closest priors.**

- [Measuring the Checker: Mutation Analysis for GPU-Kernel Benchmark Oracles](https://arxiv.org/abs/2609.22220), 2026-09-02: Does the validator audit at scale on H100 and treats checkers as RL rewards, but runs no policy RL and measures no on-policy false accepts.
- [Dr. Kernel: Reinforcement Learning Done Right for Triton Kernel Generations (KernelGYM)](https://arxiv.org/abs/2602.05885), 2026-02-05: RL with vs without a narrow hacking check (saturates at ~50 steps without it); no hidden shapes, no graded gate strength.
- [KernelZero: Co-Evolving Proposer and Coder for Continuously Improved GPU Kernel Generation](https://arxiv.org/abs/2609.33074), 2026-09-27: Correctness-gated GRPO already exists, but with the standard check and on A100; code repo returns 404.
- [A Contract-Grade Verifier for LLM-Generated GPU Kernels, and a Native Blackwell Backward for the Gated-Linear-Recurrence Family](https://arxiv.org/abs/2608.12700), 2026-08-13: Audits 2,638 generated kernels with 12 adversarial gates and runs one uncontrolled contract-gated GRPO arm; no matched comparison of gates.

**Citable anchors.**

- [Measuring the Checker: Mutation Analysis for GPU-Kernel Benchmark Oracles](https://arxiv.org/abs/2609.22220), 2026-09.
  - Role: closest prior; method and audit instrument.
  - Status: VERIFIED: exists (all three judges' arXiv checks); reviewer full text: 'The official KernelBench check misses 16.9% of witnessed faults'. KernelBench-M artifact claimed released but no public URL located.
- [KernelBench-Verified: Do LLM-Generated Kernels Actually Beat PyTorch?](https://arxiv.org/abs/2607.16241), 2026-06-26 (arXiv published date; ID month 2607).
  - Role: evaluation instrument (TF32 baseline, hidden value distributions).
  - Status: VERIFIED: exists; speedup falls from 1.43x to 0.88x under TF32 baseline plus hidden inputs. CORRECTED: hidden suite is four value transforms, no shape variation.
- [A Contract-Grade Verifier for LLM-Generated GPU Kernels, and a Native Blackwell Backward for the Gated-Linear-Recurrence Family](https://arxiv.org/abs/2608.12700), 2026-08-13 (v1; v2 2026-08-17).
  - Role: closest prior and independent-audit instrument.
  - Status: VERIFIED: exists; '39.5% are broken in a way no tolerance can excuse'; repo github.com/RishiShah99/lethe exists. CITATION AUDIT (FIX): title restored to the full arXiv title. Two-author industry preprint (E3A Healthcare), not peer-reviewed; weigh accordingly.
- [Dr. Kernel: Reinforcement Learning Done Right for Triton Kernel Generations](https://arxiv.org/abs/2602.05885), 2026-02.
  - Role: baseline policy and gate (b).
  - Status: VERIFIED: exists; KernelGYM repo exists with env, code, models and data; Dr. Kernel-8B is the only open 8B policy with confirmed released env and weights.
- [TritonRL: Training LLMs to Think and Code Triton Without Cheating](https://arxiv.org/abs/2510.17891), 2025-10.
  - Role: baseline.
  - Status: VERIFIED: exists; robust verifier includes a Qwen3-235B LLM judge, which makes it a poor frozen base.

**First experiment (12 GPU-h).** On-policy false-accept audit, no training. Freeze Dr. Kernel-8B. Sample 8 completions on ~250 KernelBench L1/L2 and KernelGYM training tasks (~2,000 kernels) after a 0.5 GPU-h vLLM throughput calibration. Score each kernel with gate (a) official 5-input allclose, (b) the KernelGYM hacking check, and (c) a hidden gate (KernelBench-Verified value transforms, robust-kbench shape variation, unaligned remainder shapes, plus KernelBench-M suites if obtainable). Score every kernel with an independent audit no gate sees: contract-grade tolerance-free gates (lethe), an fp64 oracle, and unseen shapes and dtypes. One subprocess per GPU, pinned with CUDA_VISIBLE_DEVICES, watchdog timeouts, 1-2 dedicated timing GPUs. Report each gate's false-accept rate with bootstrap CIs and per-kernel GPU-seconds. ~12 GPU-h (range 9-25, estimate). Runs only after the R580 security upgrade or Kevin's written risk acceptance, because model-generated kernels are untrusted code on R570 (sweep stop item 8). Over 8 GPU-h, so the research gauntlet applies.

**Kill criteria.** Pre-registered. Go to the 3-arm x 3-seed RL comparison (~1,000-1,400 H100 GPU-h, gauntlet required) only if gates (a) and (b) false-accept at least ~3 pp more of the policy's accepted kernels than gate (c), with non-overlapping CIs, and gate (c) costs at most ~2x gate (b) per rollout. Otherwise publish the negative ('gates barely differ on-policy'). Also stop if the frozen policy emits too few audit-rejected kernels to estimate false-accept rates (the 3-of-60 realism-probe risk); that is itself the decisive negative.

**Relation to the existing program.** Better-specified form of WS4(d), the gated oracle-strength kernel RL lane; stays behind WS4(d)'s security-upgrade and opt-in gate. Shares the checker-mutation method prior (2609.22220) with S1's evaluator-mutation leg, so one 'measuring the checker for agents' line could cover both kernel oracles and computer-use state checkers.

---

## 2. Harness, interface and scale effects on open-weight computer-use agents vs rerun noise

`S1-calibrated-cua-instrument`. Origin: H100 sweep WS1. **Recommendation: PURSUE-NARROWED.**

Scores (3-judge means): significance 6, correctness 6, citability 9, novelty residual 4.33, feasibility 6.33.

**Corrected question.** On desktop computer-use tasks (an offline OSWorld-Verified subset), within one open-weight family at four sizes (Qwen3.5-4B, 9B, 27B, 35B-A3B), how much of the task-level variation in success comes from the agent harness and from the observation type (screenshot vs screenshot plus accessibility tree), and how much is plain rerun noise, once infrastructure failures are removed and the benchmark's own state checkers are corrected by mutation testing? Does the harness-plus-interface share shrink as the model grows?

**What was wrong with the original.** (1) 2610.04433 does not use 'only 2 local Qwen models': it runs 5 models on hard45 (2 local plus 3 API) with Opus 5 in Claude Code, and it already excludes infrastructure-lost trials. (2) Holo3-35B-A3B = 82.56 is not a single reproduction anchor: the official board has a second identically flagged row at 78.15, and the two rows map to two different public trajectory archives (a verified run vs H Company internal runs), so the 4.4 pp gap is more likely an operator contrast than rerun noise. (3) Relay's interface study is not single-pass; a 48/48 repeated follow-up exists, though the first pass was confounded by 14 connection failures. (4) Separating infrastructure from task failures is required hygiene, already practiced (cua-speedrun App. I.1; 2610.04433; ICLR 2027 Ri0rU3rPOS), not a contribution. Design corrections: the ladder mixed generations (use all Qwen3.5; Holo3's HF base_model is Qwen/Qwen3.5-35B-A3B); variance shares on pass/fail outcomes depend on the base rate, so a logit-scale mixed model with a preregistered floor rule is needed; the API/CLI level exists only on Relay, so harness and interface must be separate factors; Relay at 18 tasks has an MDE near 20 pp. No merge, but this entry absorbs E9's interface main effects and C1's timing census as modules.

**Novelty.** NARROWED. cua-speedrun (2609.40284) already runs harness x model x seeds on OSWorld with runtime/harness/model error separation, screenshots only. 2608.06171 crosses observation mode x a 2-point scale ladder x rerun band, web only, rerun band measured in 2 of 8 cells. 2610.00651 does a G-theory model x scaffold decomposition but has almost no repeated cells. Open: the harness-plus-interface share vs scale within one family on desktop with measured rerun cells, and mutation analysis of computer-use state checkers (no prior found; nearest are a hand audit of false negatives, 2607.28367, and kernel-oracle mutation, 2609.22220).

**Why it matters.** Open-weight and closed systems are 3.4 pp apart on the OSWorld-Verified board, 15.3% of audited FAIL verdicts are wrong, and harness choice moves small models by about 30 pp, so leaderboard differences may be noise. A calibrated instrument says which differences are real, and it is the noise floor every later Relay or RL claim needs. The scale question has only coding evidence today (FrogNano: 'a substantially larger model shows little sensitivity to the same harness change'). The evaluator-mutation result is the most novel and cheapest piece and should ship first as a standalone short paper: scoop risk is high, with four adjacent papers between 2026-08-06 and 2026-10-03.

**Closest priors.**

- [cua-speedrun: Standardized Benchmarking of the Speed of Computer-Use Agents](https://arxiv.org/abs/2609.40284), 2026-09-30: Harness x model x five-seed checks on OSWorld with an action-path error suite, but screenshot-only, no scale ladder, no per-cell noise floor, no variance decomposition, no evaluator testing.
- [Routing Is Least Learnable Where It Is Most Valuable: Bounds on Representation Routing for Web Agents](https://arxiv.org/abs/2608.06171), 2026-08-06: Six observation modes x backbones of different scale with a 12-14% rerun band, but web-only, fixed scaffold, band measured in 2 cells and imported into 6.
- [Agent Evaluation Reliability: More Tasks Won't (Always) Fix An Agent Leaderboard](https://arxiv.org/abs/2610.00651), 2026-09-30: Method prior for the variance decomposition (model x scaffold x task over 22 benchmarks); repeated cells are 'rare', so rerun variance is not identified; no desktop or interface factor.
- [How Benchmarks Mis-Score Computer-Use Agents](https://arxiv.org/abs/2607.28367), 2026-07-30: Hand audit of 150 FAIL verdicts (17.5% wrong on the 57 OSWorld-Verified items); false negatives only, no mutation testing of the checkers.

**Citable anchors.**

- [cua-speedrun: Standardized Benchmarking of the Speed of Computer-Use Agents](https://arxiv.org/abs/2609.40284), 2026-09.
  - Role: closest prior; source of the action-path suite.
  - Status: VERIFIED (full text): 56 OSWorld configurations, harness comparisons for selected models, five-seed stability, App. I.1 action-path tests (94 cases x 5, 83 pass and 11 fail), Table 20 Qwen3.5 harness errors; screenshots only.
- [Agent Evaluation Reliability: More Tasks Won't (Always) Fix an Agent Leaderboard](https://arxiv.org/abs/2610.00651), 2026-10.
  - Role: decomposition-method prior.
  - Status: VERIFIED: Bayesian G-theory over 22 HAL/Harbor benchmarks; repeated (i,m,a) cells 'rare'.
- [Routing Is Least Learnable Where It Is Most Valuable (observation modes on (V)WebArena)](https://arxiv.org/abs/2608.06171), 2026-08-06.
  - Role: interface x scale x rerun-band prior (web).
  - Status: VERIFIED (abstract confirmed by judge 1): 'rerunning the same mode on the same tasks changes 12-14% of outcomes'.
- [What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433), 2026-10-03.
  - Role: coding analogue and methodological template (McNemar/TOST, MDE).
  - Status: VERIFIED: SWE-bench Verified only; harness swap and rerun each flip 13% of tasks; infrastructure-lost trials excluded.
- [FrogNano: Training a 4B Coding Agent via Online Task Synthesis](https://arxiv.org/abs/2609.07925), 2026-09-07 (v1; current v4 2026-09-16).
  - Role: motivation for the scale hypothesis.
  - Status: VERIFIED (exists; harness-sensitivity quote is in the full text, not the abstract, accepted on the reviewer's full-text read). CITATION AUDIT (FIX): the previous "title" was a paraphrase of a finding; replaced with the real title. The harness-sensitivity finding (Qwen3.5-4B SWE-bench Verified 8.3% under R2E-Gym vs 37.2% under Leaf; MiniMax-M2.5 66.5% on both) is in Sec. 1-2 of the full text, not the title.
- [Measuring the Checker: Mutation Analysis for GPU-Kernel Benchmark Oracles](https://arxiv.org/abs/2609.22220), 2026-09.
  - Role: method prior for evaluator mutation.
  - Status: VERIFIED: kernel oracles only; no computer-use mutation-analysis prior found.

**First experiment (60 GPU-h).** Stage 0 (CPU only, 0 GPU-h, 2-3 days): (i) per-task diff of the two public Holo3-35B-A3B trajectory archives in xlangai/ubuntu_osworld_verified_trajs (~14.9 GB; the download needs Kevin's OK) to settle rerun vs operator contrast; (ii) port cua-speedrun's action-path suite to the osworld-kvm runtime and the Qwen3.5 reference harness, fixing the Table 20 bugs (modifier release, dropped multi-tool calls, middle-click); (iii) apply ~40 state-mutation operators to the pinned OSWorld evaluators on a 120-task, web-free, domain-stratified subset and report per-evaluator false-negative and false-positive rates. Stage 1 (~60 GPU-h, range 15-90, estimate): Qwen3.5-{4B, 9B, 27B FP8, 35B-A3B} x 2 harnesses x 2 observations x 3 reruns x the same 120 tasks = 5,760 episodes, plus one Holo3-35B-A3B rerun on all 359 tasks; logit-scale crossed mixed model with infrastructure-lost runs removed and evaluator-corrected verdicts; the first 10 GPU-h must log real per-episode costs.

**Kill criteria.** Stage 0: no GPU episodes until the action-path suite passes 100%. If the Holo3 per-task diff traces the 4.4 pp gap mostly to infrastructure or operator differences, do not use the pair as a noise anchor. Stage 1: if the Holo3 rerun lands more than 2 SE outside the range spanned by the two official rows, stop and debug the harness before reading the factorial. If Qwen3.5-4B is below 10% success on more than 80% of cells, swap it for 122B-A10B. If the harness-plus-interface share at 4B vs 27B/35B-A3B differs by less than the paired MDE (~7-8 pp, estimate), report 'no detectable shrinkage with scale' rather than extend the ladder. If nested-KVM cannot host ~40 VMs or the qcow2 reset path fails, cut the task count before adding GPUs.

**Relation to the existing program.** This is WS1, the program spine. It absorbs E9's interface main effects and C1's timing census (fold into WS1's per-episode cost card), and it is the noise-floor prerequisite for S2 and S3. Shares the checker-mutation method with C2.

---

## 3. Do learned sparse-attention indexers drop cross-script evidence?

`E6-d21-translation-supervised-indexer`. Origin: existing: directions/21 + proposal. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 5, correctness 6.67, citability 8, novelty residual 5.33, feasibility 6.

**Corrected question.** In frozen open models fitted with KL-distilled top-k sparse-attention indexers (the selector family used by DeepSeek's DSA and Qwen's QSA), does the indexer miss more of the relevant passage than the dense model's own top-k attention when the question is in a different script from the passage, at the same token budget? Only if such a cross-script shortfall survives label-free fixes, test whether a parallel-document alignment loss on the indexer improves recall on languages it never saw.

**What was wrong with the original.** No premise failed; this is the only D-series item whose premises all held. The core premise (production sparse attention uses a small learned top-k indexer KL-distilled toward dense attention) was confirmed in DSA 2512.02556. The corrections are scope and design: the method half is narrowed by 2610.01921 (auxiliary KL on parallel data for MoE routers); claims are limited to frozen retrofits because production indexers were co-trained with their backbones; Belebele has no evidence spans, so the needle must be the whole passage, which dilutes differences; Qwen3-0.6B may lack cross-lingual retrieval headroom; and directions/21 omits 2602.22453 (retrieval-transition heads), LOCOS 2607.01002 and 2609.35378.

**Novelty.** NARROWED. 2610.01921 already supervises a discrete selection component (MoE routers) with parallel data. 2608.26175 audits learned token-selection compressors cross-lingually and finds the gap 'tracks compression supervision data, not architecture'. 2609.35378 shows efficient-attention hybrids lose more non-English NIAH but studies recurrent hybrids, not indexers. Unmeasured: indexer-specific cross-script selection recall against the dense teacher's own top-k.

**Why it matters.** Learned top-k indexers are now standard in production sparse attention, and nobody has measured whether that selection step drops cross-script evidence. The first stage localizes the cross-lingual long-context gap to selection or to attention mass, the first component-level answer (MLNeedle and OneRULER only describe the gap), and leaves a reusable selection-recall instrument. A null is a publishable localization negative. Capped at 5: the remedy is narrowed, results cover frozen retrofits only, and the likely effect is modest; best case is EMNLP/ACL Findings or an efficient-attention workshop.

**Closest priors.**

- [Cross-Lingual Alignment for Decoder-Only Models using MoE Routers](https://arxiv.org/abs/2610.01921), 2026-10-01: Same remedy (parallel-data KL on a selection component) applied to expert choice, not to in-context token selection by an attention indexer.
- [Lost in Compression: A Controlled Cross-Lingual Audit of Extractive Prompt Compressors](https://arxiv.org/abs/2608.26175), 2026-08-28: Cross-lingual audit of learned token selectors outside the model; predicts multilingual KL data alone may close any gap.
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28: Efficient-attention hybrids lose more non-English NIAH (Granite-H 52.1 vs 71.2 non-English), but recurrent hybrids and monolingual query-needle pairs only.
- [How Much Dense Attention is Necessary? Oracle-Guided Sparse Prefill for Full/GQA Layers in Hybrid Long-Context Models](https://arxiv.org/abs/2606.07703), 2026-06: Separates budget feasibility from indexer error with frozen KL indexers, but monolingual.

**Citable anchors.**

- [DeepSeek-V3.2 (DSA lightning indexer; frozen-backbone KL warm-up to head-summed attention)](https://arxiv.org/abs/2512.02556), 2025-12.
  - Role: baseline recipe.
  - Status: VERIFIED (reviewer opened): 'freeze[s] all model parameters except for the lightning indexer'; target aggregated 'by summing across all attention heads'.
- [On the Design of Qwen3.8-Next Architecture (QSA compressed-block indexer, max-pooled KL target)](https://arxiv.org/abs/2608.30320), 2026-08.
  - Role: baseline recipe (block form).
  - Status: VERIFIED: exists (judges' arXiv checks).
- [How Much Dense Attention is Necessary? Oracle-Guided Sparse Prefill](https://arxiv.org/abs/2606.07703), 2026-06.
  - Role: closest prior (frozen KL indexers on Qwen3.5).
  - Status: VERIFIED: exists.
- [Cross-Lingual Alignment for Decoder-Only Models using MoE Routers](https://arxiv.org/abs/2610.01921), 2026-10-01.
  - Role: closest prior for the remedy.
  - Status: VERIFIED: exists.
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28.
  - Role: motivation.
  - Status: VERIFIED (full text): OneRULER NIAH Table 2, Granite-4.0-H-Micro 52.1 non-English vs Granite-4.0-Micro 71.2.
- [Lost in Compression: A Controlled Cross-Lingual Audit of Extractive Prompt Compressors](https://arxiv.org/abs/2608.26175), 2026-08-28 (arXiv published 2026-07-27 per judges 2 and 3).
  - Role: evaluation protocol (achieved-budget reading).
  - Status: VERIFIED: exists; ID-month vs published-date skew noted, does not change the premise.

**First experiment (1.5 GPU-h).** K1 localization screen on frozen Qwen3-0.6B-Base (~1.5 GPU-h). Fit block-form indexers (compress ratio 4) on all 28 layers with two target aggregations (head-sum, max-pool) x 3 seeds, all six trained in one shared frozen-teacher stream of 20M tokens at 8K (half ParaDocs/TED2020 bilingual concatenations, half FineWeb-2). Evaluate 1,200 Belebele prompts at 8K: question in the passage's language vs human-translated cross-script question, for 7 held-out scripts {ja, ko, bn, ta, el, he, ka} x both directions with English, plus a 200-prompt literal ceiling; read recall at a matched achieved budget of 12.5% and record dense answer accuracy as the headroom gate. No sparse kernel is needed: the indexer is scored offline against captured dense attention. Under 8 GPU-h, so no gauntlet for K1; blocked first on a GPU entry point, a rebuilt image and a qwen3-0.6b-base checkpoint receipt.

**Kill criteria.** Pre-registered. If the cross-script shortfall is at least 10 points for some target with a 99% passage-cluster bootstrap interval excluding 0, go to the label-free remedy arms (retrieval-head or LOCOS-weighted target, multilingual KL data alone). If it is at most 5 points for both targets, publish the localization negative and stop. If the dense cross-script baseline is near floor (headroom gate fails), the shortfall is uninterpretable: move to Qwen3.5-4B-Base at 3-5x cost or stop. Report seed SD before any parallel-loss arm runs.

**Relation to the existing program.** D21 architecture backfill, independent of the CUA spine; first in the backfill queue. Complements WS2's language thread at the architecture level.

---

## 4. Does RL on one GUI interface or UI language transfer to the others?

`S3-interface-locale-rl-transfer`. Origin: H100 sweep WS3. **Recommendation: PURSUE-NARROWED.**

Scores (3-judge means): significance 5, correctness 5, citability 7, novelty residual 5, feasibility 3.

**Corrected question.** On one state-graded workplace app (Relay, once it has at least 100 task templates and a screenshot harness that rarely fails), with tasks, reward, rollouts and optimizer updates held fixed, does RL training of an open 4B policy under one observation type (screenshots vs accessibility tree, sharing one action space) or one UI language (English vs Japanese vs Arabic right-to-left, string-table swap only) improve success in the other interface and language cells, measured against each cell's own pre-RL baseline and a rerun-noise floor?

**What was wrong with the original.** (1) The proposed policy, Fara1.5-4B, is screenshot-only at perception time ('it sees the browser through screenshots, not the DOM or accessibility tree'), so every non-pixel cell starts off-distribution and confounds starting competence with transfer; the API interface also changes the action space. (2) Relay has no locale factor: runner/environment.mjs:64 hard-codes locale 'en-US'. (3) Train-interface x eval-interface transfer under RL is already occupied for coding harnesses: ICLR 2027 4KSNZln9nS (10 Qwen3.5-27B checkpoints x 4 harnesses, 'transfer is direction-dependent') and 2609.04518 (the eval harness moves solve rate by a factor of 4.3). (4) 'Matched compute' was undefined across interfaces with very different per-step token costs, and the funded design is 2 x 2, not a 4 x 4 matrix. Open risk: Cobra (dmf4jsd81g) trains three fixed-observation online-RL controls at equal budget; whether it cross-evaluates them is UNVERIFIABLE (PDF behind the OpenReview challenge).

**Novelty.** NARROWED. 'Training binds the interface' is established (HINT for SFT; 4KSNZln9nS and 2609.04518 for RL on coding harnesses). The pixels-vs-a11y arm may be occupied by Cobra. Locale as an RL training factor looks genuinely open: macOSWorld and MPR-GUI are evaluation or inference-time only.

**Why it matters.** A clean answer on locale transfer, positive or negative, would be the first RL result treating UI language as a training factor, and it matches Kevin's research identity (language as a controlled variable) and day job (localization). The pixels-vs-a11y arm, read against a 3-seed x 5-rerun noise floor, would firm up interface claims that 2608.06171's 12-14% rerun flips make weak. Limits: one synthetic Slack-like app at 4B, and a null on interface transfer is workshop-level unless replicated on desktops.

**Closest priors.**

- [One Policy, Many Harnesses: Reinforcement Learning for Transferable Harness Adaptation (ICLR 2027 submission 4KSNZln9nS)](https://openreview.net/forum?id=4KSNZln9nS), 2026-09-19: Full RL train x eval matrix over 4 coding harnesses; no perceptual GUI interfaces, no locale.
- [What Does Multi-Harness RL Learn? Credit Assignment and Portability in Coding Agents](https://arxiv.org/abs/2609.04518), 2026-09-03: Design template (SFT warm start, held-out harness, seed-noise reading) for coding, not GUI perception.
- [Cobra: Co-Training Bi-Level Observation Routing and Action Policies for GUI Agents (ICLR 2027 submission dmf4jsd81g)](https://openreview.net/forum?id=dmf4jsd81g), 2026-08-20: Fixed-observation online-RL controls at matched budget on OSWorld-Verified; cross-evaluation of the controls unverified; no locale.
- [HINT: Learning the Harness Protocol Interface-Invariant Training for SWE Agents (ICLR 2027 submission EPtfpNXW58)](https://openreview.net/forum?id=EPtfpNXW58), 2026-09-07: Establishes interface binding under SFT on SWE harnesses; its multi-surface re-rendering is the mixed-interface baseline arm.

**Citable anchors.**

- [One Policy, Many Harnesses (ICLR 2027 submission 4KSNZln9nS)](https://openreview.net/forum?id=4KSNZln9nS), 2026-09-19.
  - Role: closest prior.
  - Status: VERIFIED (abstract via api2 search): 'ten Qwen3.5-27B checkpoints evaluated in 40 checkpoint--harness combinations'; PDF not readable (403).
- [What Does Multi-Harness RL Learn? Credit Assignment and Portability in Coding Agents](https://arxiv.org/abs/2609.04518), 2026-09-03.
  - Role: design and matching-rule template.
  - Status: VERIFIED (arXiv abstract): 'The evaluation harness is the dominant variable ... a factor of 4.3'.
- [Cobra (ICLR 2027 submission dmf4jsd81g)](https://openreview.net/forum?id=dmf4jsd81g), 2026-08-20.
  - Role: occupancy risk for the interface arm; routing baseline.
  - Status: VERIFIED abstract (outperforms 'the strongest of three fixed-observation online-RL controls by 5.5 percentage points'); UNVERIFIABLE whether controls were cross-evaluated (PDF behind challenge).
- [HINT (ICLR 2027 submission EPtfpNXW58)](https://openreview.net/forum?id=EPtfpNXW58), 2026-09-07.
  - Role: phenomenon prior; mixed-interface baseline.
  - Status: VERIFIED (abstract): fine-tuning on one harness 'teaches the interface along with the task'.
- [macOSWorld: A Multilingual Interactive Benchmark for GUI Agents](https://arxiv.org/abs/2506.04135), 2025-06-04.
  - Role: occupies the locale evaluation main effect.
  - Status: VERIFIED (full text): Arabic 28.8% average degradation vs English; evaluation only.
- [Routing Is Least Learnable Where It Is Most Valuable](https://arxiv.org/abs/2608.06171), 2026-08-06.
  - Role: justifies the rerun noise floor.
  - Status: VERIFIED (abstract): rerunning the same mode changes 12-14% of outcomes.

**First experiment (150 GPU-h).** CPU prerequisites first (0 GPU-h): a shared element-or-coordinate action space in Relay's runner/interfaces.mjs (pixels click coordinates at line 207; a11y and JSON accept only element refs at line 219); a pixel harness with blocked rate under 5% (now 19 of 24 pixel runs blocked, 14 by connection failures); locale as a fixture parameter with an en/ja string-table swap; at least 100 templates with a held-out split; and a read of Cobra's PDF. Then a single-train-cell pilot (~150 GPU-h, range 125-185, all estimates): Step 0 (~25 GPU-h) ~2,000 multi-interface teacher trajectories on training templates plus an SFT warm start of Qwen3.5-4B/Fara1.5-4B on pixels and a11y, plus a 2.5 GPU-h rollout/trainer parity gate; Step 1 (~12 GPU-h) pre-RL baselines in {pixels, a11y} x {en, ja} on 100 held-out instances x 5 reruns; Step 2 (~75-135 GPU-h) GRPO in a11y-en only, 50 updates x 3 seeds x 128 trajectories per update, re-evaluating every checkpoint in all 4 cells x 5 reruns. Per-update cost may be 1.5-2x the sweep's estimate.

**Kill criteria.** Every pre-RL cell must sit in the 10-90% success band, or fix tasks before RL. Kill if the a11y-en diagonal gain is below max(5 pp, 2x rerun SE): nothing to transfer. If Cobra's PDF shows its fixed-observation controls were cross-evaluated, demote the interface arm and lead with locale. Locale transfer below the noise floor while the diagonal gains is itself the publishable 'RL binds the locale' result. Fund the 8-cell factorial with mixing and routing baselines (480-720 GPU-h) only past this pilot and the Cobra read, and through the research gauntlet.

**Relation to the existing program.** This is WS3-R, the gated flagship. Depends on S1's noise floor and S2's localized Relay (the locale fixture). The interface arm is the GUI analogue of 4KSNZln9nS, 2609.04518 and HINT; the locale arm is the headline.

---

## 5. Arabic in computer-use agents: script vs mirrored layout

`S2-aligned-locale-language`. Origin: H100 sweep WS2. **Recommendation: PURSUE-NARROWED.**

Scores (3-judge means): significance 4.67, correctness 6, citability 8.67, novelty residual 5.33, feasibility 5.67.

**Corrected question.** In one web app (Relay, after real i18n extraction) whose page structure, element IDs, task steps and state grader are identical in every UI language, how much of an open-weight agent's Arabic drop comes from the Arabic text itself (Arabic strings in a left-to-right layout) and how much from right-to-left mirroring of the layout, measured on screenshots against a per-cell rerun-noise floor? Run the measurement only if the design can detect effects of about 5 pp, since macOSWorld's entire English-to-Arabic drop is 5.6 pp.

**What was wrong with the original.** (1) A string-table swap cannot hold layout fixed while including Arabic RTL and a +30% pseudo-locale: text expansion changes wrapping and real Arabic needs mirroring, so mirroring must be its own factor. (2) Relay is not internationalized: runner/environment.mjs:64 hard-codes locale 'en-US', strings are inline JSX, no i18n library. (3) Comparing an effect on Relay with macOSWorld's mixes platform, task and model differences; the defensible estimand is a within-environment decomposition. (4) 18 tasks with cosmetic seeds cannot detect macOSWorld-sized non-RTL effects (1.6-3.5 pp); the paired MDE is about 8-12 pp (estimate). (5) Skill Issue (2608.25832) already crosses an aligned interface with reasoning language with the state space fixed, in text games. Judge 3 found two further problems, both confirmed against Relay's code: the planned a11y 'negative control' is identical by construction (Relay's a11y observation is a Playwright ariaSnapshot plus a role/name element list in DOM order with no coordinates, and dir=rtl does not change DOM order), so it can only show rerun noise and is a pipeline sanity check, not a finding; and the planned ~10 pp MDE exceeds macOSWorld's total English-to-Arabic absolute drop of 5.6 pp (19.3 to 13.7), which is split between glyph and mirror, so Phase 1 as designed is likely underpowered. Also, chrome-only localization of a chat app leaves most visible text (fixture content) in English, so the treatment is weak and its size must be reported.

**Novelty.** NARROWED. macOSWorld (2506.04135) owns the UI-locale main effect on an executable desktop benchmark and explicitly leaves the Arabic split open ('Arabic glyphs or the mirrored UI layout, or both'). MPR-GUI (2512.00756) owns strictly aligned cross-lingual GUI evaluation, but static and without Arabic or RTL. Skill Issue (2608.25832) owns the reasoning-language crossing with fixed state in text games. 2608.11110 owns rerun-normalized instruction-language effects in tool agents. Open: the glyph-vs-mirror split in an executable GUI.

**Why it matters.** The glyph-vs-mirror question bears on every RTL deployment of a computer-use agent and is the one clean, cheap estimand left after macOSWorld. Building the localized, oracle-gated Relay is also the prerequisite for S3's locale arm, where most downstream value sits. Capped: evaluation-only on one synthetic 18-task app, a weak chrome-only treatment, and no power for non-RTL locales.

**Closest priors.**

- [macOSWorld: A Multilingual Interactive Benchmark for GUI Agents (NeurIPS 2025)](https://arxiv.org/abs/2506.04135), 2025-06 (v4 2025-10-18): Locale x instruction-language main effect on 202 desktop tasks; does not separate Arabic glyphs from mirrored layout; no significance testing.
- [MPR-GUI: Benchmarking and Enhancing Multilingual Perception and Reasoning in GUI Agents (ACL 2026)](https://arxiv.org/abs/2512.00756), 2025-11-30 (ACL 2026): Near-aligned static screenshots in 6 languages with an inference-time fix; not interactive, no Arabic or RTL.
- [Skill Issue: Are Skills Language-Invariant in LLMs?](https://arxiv.org/abs/2608.25832), 2026-08-26: Isolates language with fixed state and actions and shows reasoning-language changes recover performance; text games, no GUI perception or layout.
- [Actions Speak Louder than Words: Measuring Cross-Lingual Policy Retention in Tool-Using Agents (COLM 2026)](https://arxiv.org/abs/2608.11110), 2026-08-11: Instruction-language effects normalized by rerun reproducibility; tool agents, not GUIs.

**Citable anchors.**

- [macOSWorld: A Multilingual Interactive Benchmark for GUI Agents](https://arxiv.org/abs/2506.04135), 2025-06 (NeurIPS 2025).
  - Role: closest prior; source of the open split.
  - Status: VERIFIED (full text): Table 4 en 19.3 / ru 17.7 / zh 17.2 / ja 15.8 / ar 13.7; Sec 5.2 attributes the Arabic drop to 'Arabic glyphs or the mirrored UI layout, or both'; checklist item 7 (statistical significance) answered No.
- [MPR-GUI: Benchmarking and Enhancing Multilingual Perception and Reasoning in GUI Agents](https://arxiv.org/abs/2512.00756), 2025-11-30 (ACL 2026 long).
  - Role: motivation; static aligned prior.
  - Status: VERIFIED (full text): interactive benchmarks 'inevitably introduce language-irrelevant variations (e.g., UI layouts and interaction trajectories)'.
- [Skill Issue: Are Skills Language-Invariant in LLMs?](https://arxiv.org/abs/2608.25832), 2026-08.
  - Role: closer prior for the reasoning-language arm.
  - Status: VERIFIED (full text): 'changing only the intermediate reasoning language recovers much of the lost performance'.
- [Actions Speak Louder than Words: Measuring Cross-Lingual Policy Retention in Tool-Using Agents](https://arxiv.org/abs/2608.11110), 2026-08.
  - Role: noise-floor and compliance prior.
  - Status: VERIFIED: 'Published as a conference paper at COLM 2026'; reasoning-language prompting compliance 0.79% (Gemma) and 0.08% (Sarvam).
- [Investigating the Role of Reasoning-Language Alignment in Monolingual Retrieval-Augmented Generation](https://arxiv.org/abs/2610.03136), 2026-10-02.
  - Role: preregistered H1 for the reasoning-language arm.
  - Status: VERIFIED (full text): alignment helps but does not surpass native English reasoning; German text RAG only.
- [Relay repo docs (local, read-only): README.md, runner/environment.mjs, runner/interfaces.mjs](file:///Users/kevinliu/repos/Relay/README.md), 2026-10-05 (HEAD e6c815e).
  - Role: environment feasibility and power constraint.
  - Status: VERIFIED locally: locale 'en-US' hard-coded at environment.mjs:64; a11y observation is ariaSnapshot (environment.mjs:96, interfaces.mjs:190) with a role/name element list and no coordinates; 18 tasks; 'Cosmetic seeds are not held-out task families'.

**First experiment (15 GPU-h).** Phase 0 (CPU, 0 GPU-h): extract Relay's inline chrome strings into i18next catalogs for en, ar-LTR (Arabic strings, dir=ltr) and ar-RTL (Arabic strings plus dir=rtl and logical CSS); make the locale a fixture parameter; keep fixture content and grader target strings in English. Gate in every locale: scripted reference solutions pass 18/18 on at least 3 seeds, the DOM role/ID tree hash is identical, graders are unchanged. Record the chrome-vs-content visible-text ratio per screen and get a native-speaker check of the Arabic catalog. Power gate: compute the paired MDE from the WS1 Relay noise-floor run. Phase 1 (~15 GPU-h, range 4-34, estimate; only past the power gate): 18 tasks x 4 cosmetic seeds x {en, ar-LTR, ar-RTL} x {pixels, a11y} x 1 open VLM x 2 reruns = 864 episodes, English instructions; glyph effect = ar-LTR minus en, mirror effect = ar-RTL minus ar-LTR, task-clustered paired bootstrap; the a11y mirror contrast is reported as a pipeline check only.

**Kill criteria.** Phase 0: if the oracle gate fails in any locale, fix the alignment before any GPU work. Power gate: if the paired MDE is above ~5 pp and there is no route to more structurally distinct templates (or an OSWorld/LibreOffice subset), publish localized Relay plus the oracle gate as infrastructure and stop. Phase 1: if English pixel success is outside 15-85%, the pixel arm is uninformative and the mirror claim is dropped. A nonzero a11y mirror contrast beyond noise means the alignment is broken. If both Arabic effects fall under the MDE, publish the robustness null and drop the locale arm from WS3-R. Run the instruction x reasoning-language arm only if Phase 1 survives; defer zh/ja/pseudo-locale until Relay has at least 100 templates.

**Relation to the existing program.** This is WS2, the Paper 1 sequel. Supersedes E1, whose reasoning-language question survives as this entry's arm (d). Its locale fixture is the prerequisite for S3's locale arm; it needs S1's local serving path and Relay noise floor.

---

## 6. Wait, queue or act: timing in self-hosted computer-use agents

`C1-timing-resource-control`. Origin: Codex research reset. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 4.67, correctness 5.67, citability 8, novelty residual 5, feasibility 6.

**Corrected question.** With one open vision-language agent served on one H100 and N concurrent desktop VMs under a fixed arrival stream, what share of step time goes to fixed post-action waits versus inference queueing, and how often do agents capture a screen before the UI has settled or act on a screen that has since changed? Only if stale actions are common, does a readiness-and-revalidation gate that also tells the inference server when to hold or release cache beat a tuned fixed wait plus always-revalidate plus an existing cache-aware scheduler?

**What was wrong with the original.** Six premises failed. Queueing contention is unestablished for computer-use agents (HEAR and ThunderAgent measure text and tool agents; cua-speedrun used a closed API on Modal). Stale-observation dispatch frequency is plausible but unmeasured. 'Simple refresh rules' are not weak: default runtimes already sleep 2 s after every action (2,000 of 2,524 ms per OSWorld click), so the default problem is wasted time, not correctness. No off-the-shelf cache-aware scheduler has been tested on screenshot-heavy prompts (HEAR is a one-day-old v1; ThunderAgent's Dynamo plugin is experimental). Completions per GPU-hour rise trivially with less waiting unless concurrency and arrivals are fixed. VLMs judge UI transitions poorly (65.1% best exact match on Desktop-Delta Bench), so 'visible-input-only readiness' is unproven. The proposed 18-episode diagnostic fixes no concurrency, so it cannot test GPU competition.

**Novelty.** NARROWED. cua-speedrun (2609.40284) owns the wasted-settle-time story. Serving-side environment signals exist for tool agents (Ask the Tool 2609.18849, HEAR 2610.06597); stale-observation handling exists outside GUIs and GPUs (ATR, Concord, Desktop-Delta Bench). Unclaimed: a gate coupling GUI readiness with KV hold/release, and any measurement of queue-vs-settle share and stale-dispatch frequency for self-hosted VLM agents under controlled concurrency.

**Why it matters.** Parts (1) and (2) would be the first timing census for self-hosted VLM computer-use agents under controlled load, and CUA-serving and benchmark groups would cite it whatever the result. The likeliest clean answer for the gate is negative (a tuned wait plus revalidation plus an existing scheduler matches it), which is an engineering note. A positive result changes practice only if stale dispatch is frequent under natural dynamics, which no source measures today.

**Closest priors.**

- [cua-speedrun: Standardized Benchmarking of the Speed of Computer-Use Agents](https://arxiv.org/abs/2609.40284), 2026-09-30: Shows fixed waits dominate default runtime latency and that removing them causes premature capture; no shared inference queue, no concurrency control.
- [Ask the Tool, Don't Guess: Agent Tool Calls Hold Their Progress, and the Serving System Should Read It](https://arxiv.org/abs/2609.18849), 2026-09-16: Environment-side progress drives KV retain/evict in a production engine; text tool agents, not GUI readiness.
- [Desktop-Delta Bench: Do Computer-Use Models Understand Desktop GUI Transitions?](https://arxiv.org/abs/2607.26041), 2026-07-28: States the asynchronous-capture mechanism and measures weak VLM transition judgment; offline, no runtime policy, no GPU side.
- [Can Agent Harnesses and Inference Engines Hear Each Other? The HEAR Protocol for Agentic LLM Serving](https://arxiv.org/abs/2610.06597), 2026-10-05: Harness-engine protocol with cache-aware scheduling; text/tool workloads only.

**Citable anchors.**

- [cua-speedrun (Table 2: fixed 2 s post-action waits dominate runtime latency)](https://arxiv.org/abs/2609.40284), 2026-09-30.
  - Role: motivates; sets the tuned-wait baseline.
  - Status: VERIFIED (full text; v1 2026-09-30): 'Fixed waits account for most baseline latency'.
- [Can Agent Harnesses and Inference Engines Hear Each Other? The HEAR Protocol for Agentic LLM Serving](https://arxiv.org/abs/2610.06597), 2026-10-05 (v1 only).
  - Role: closest serving-side prior and baseline.
  - Status: VERIFIED: v1 posted 2026-10-05; anonymous code mirror; not peer-reviewed. CITATION AUDIT (FIX): title was a paraphrase; replaced with the real arXiv title.
- [ThunderAgent: A Simple, Fast and Program-Aware Agentic Inference System](https://arxiv.org/abs/2602.13692), 2026-02-14 (v2 2026-03-10).
  - Role: baseline scheduler.
  - Status: VERIFIED: pause/restore scheduling; Dynamo plugin labelled 'Experimental'.
- [Ask the Tool, Don't Guess](https://arxiv.org/abs/2609.18849), 2026-09-16.
  - Role: closest prior for the KV half.
  - Status: VERIFIED: exists; 20.7% p90 post-tool TTFT cut vs LRU.
- [Benchmarking and Improving GUI Agents in High-Dynamic Environments (DynamicGUIBench)](https://arxiv.org/abs/2604.25380), 2026-04 (v2 2026-05-08).
  - Role: source of natural (non-injected) dynamics.
  - Status: VERIFIED: exists; code/env release not stated in text read.
- [Desktop-Delta Bench](https://arxiv.org/abs/2607.26041), 2026-07-28 (v2 2026-07-29).
  - Role: motivates a deterministic settle detector.
  - Status: VERIFIED: best temporal-ordering exact match 65.1%.

**First experiment (2.5 GPU-h).** Timing census only, no gate. Phase 0 (CPU, 0 GPU-h): boot one nested-KVM Ubuntu guest under userspace QEMU (no root needed), run scripted actors over ~10 actions on each of 3 apps, capture 30-60 fps, and measure the settle-time distribution (frames to pixel-diff quiescence) and the premature-capture rate at 0/100/500/2000 ms. Phase 1 (~2.5 GPU-h, hard cap 3, estimate): serve Qwen3-VL-8B on vLLM with prefix caching; drive N in {1, 4, 8, 16} concurrent guests from a fixed Poisson arrival stream over a frozen 24-task batch with the default 2 s wait; timestamp capture, quiescence, queue admission, prefill, decode, dispatch and effect; count stale dispatches with a hidden frame observer under natural dynamics plus one injected late modal in half the batch.

**Kill criteria.** Phase 0: if 2000 ms default waits never capture prematurely and p99 settle is under 300 ms, natural premature capture is answered and the work reduces to a wait-tuning note. Phase 1: kill if queue wait is under 10% of step time at N=16 and stale dispatch is under 2% of steps under natural dynamics. Drop the gate (part 3) if a per-app tuned wait plus always-revalidate plus a cache-aware scheduler matches it.

**Relation to the existing program.** Complements WS1: parts (1) and (2) belong in WS1's per-episode cost card and readiness-probe work and reuse its nested-KVM runtime, serving path and action-path suite. Competes with no workstream.

---

## 7. Distilling in-context learning into a portable write rule

`E4-d19-icl-rule-distillation-port`. Origin: existing: directions/19 + proposal. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 4.67, correctness 5, citability 8, novelty residual 5, feasibility 6.

**Corrected question.** Can a small fast-weight write rule, distilled from a frozen 1.3B transformer's 8-shot in-context behaviour through a fixed 64-dimensional interface, reproduce the teacher's held-out predictions better than a capacity-matched gradient-descent-form rule, and does the same frozen rule, attached to recurrent models (GLA, RetNet, HGRN2, GSA) through label-free linear maps, add few-shot ability beyond their own in-context learning and a placebo rule? First check that the interface can carry the behaviour at all and that the teacher shows real label-dependent in-context learning.

**What was wrong with the original.** (1) Whether a 64-d, rank-8 external interface can capture the transformer's content-dependent update is not established; the only evidence is a synthetic CPU doctor. (2) Whether the 1.3B/100B-token teacher shows enough label-dependent in-context learning is unverified, and Pan et al. (2305.09731) find task learning grows with scale. (3) 'Ports' had no success criterion: it needs a target-native ceiling (a rule distilled directly on each target), a native-ICL baseline and a placebo rule. Also, requiring the external rule to beat Task Operators is close to unattainable (TO edits every head's W_O inside the model), so TO should be an upper reference; and the native-ICL control must say whether targets see the demonstrations in their window.

**Novelty.** NARROWED. Task Operators (2610.01054) already captures ICL's effect as an explicit per-head affine transform inside the model. TTCD (2608.01672) distils context into fast weights with a gradient-form update within one model. One Adapter Pair (2608.09521) occupies label-free per-model linear interfaces. Jeong (2603.22329) fixes a Hebbian 'universal write rule'. Unclaimed: a distilled, external write rule ported across operator families, with a gradient-form attribution.

**Why it matters.** A positive result would give capacity-matched behavioural evidence on whether pretrained in-context learning is gradient-descent-like (Shen et al. 2310.08540 call the equivalence 'an open hypothesis') and the first transfer of a write rule, rather than state or weights, across operator families. A negative is confounded by interface capacity unless the oracle-ceiling gate runs first.

**Closest priors.**

- [Capturing In-Context Learning Dynamics with Task Operators](https://arxiv.org/abs/2610.01054), 2026-10-01: Explicit within-model replacement of ICL; no cross-model or cross-operator port, no learned write rule, no gradient-form comparison.
- [Learning What to Remember: Test-Time Training via Context Distillation (TTCD)](https://arxiv.org/abs/2608.01672), 2026-08-03: Context distillation into fast weights with a gradient-form update; same teacher and student, nothing ported.
- [One Adapter Pair per Model: A Universal Activation Interface for Language Models](https://arxiv.org/abs/2608.09521), 2026-08-10: The porting mechanism (per-model linear adapters fitted label-free) without any distilled rule.

**Citable anchors.**

- [Capturing In-Context Learning Dynamics with Task Operators](https://arxiv.org/abs/2610.01054), 2026-10-01.
  - Role: closest prior; upper reference.
  - Status: VERIFIED (abstract): each head's ICL output 'is an affine transformation of its context-masked counterpart'; Qwen3 and Llama3 only.
- [Do pretrained Transformers Learn In-Context by Gradient Descent?](https://arxiv.org/abs/2310.08540), 2023-10-12.
  - Role: motivates.
  - Status: VERIFIED (abstract): 'the equivalence between ICL and GD remains an open hypothesis'.
- [What In-Context Learning 'Learns' In-Context: Disentangling Task Recognition and Task Learning](https://arxiv.org/abs/2305.09731), 2023-05-16.
  - Role: eligibility-gate instrument; source of the 1.3B risk.
  - Status: VERIFIED (abstract): 'LLMs acquire TL as the model scales'.
- [Trained Persistent Memory for Frozen Decoder-Only LLMs (Jeong)](https://arxiv.org/abs/2603.22329), 2026-03.
  - Role: closest framing prior.
  - Status: VERIFIED: Sec 8.3 'universal write rule' is fixed-form Hebbian, GPT-2/Flan-T5 only.
- [One Adapter Pair per Model](https://arxiv.org/abs/2608.09521), 2026-08.
  - Role: porting-mechanism precedent.
  - Status: VERIFIED (abstract): 'a new model joins by fitting only its adapter pair on unlabeled matched text'.
- [fla-hub 1.3B-100B iso-corpus ladder (transformer, gla, retnet, hgrn2, gsa; MIT)](https://huggingface.co/fla-hub/transformer-1.3B-100B), 2025-02-09 (lastModified).
  - Role: teacher and target checkpoints.
  - Status: VERIFIED: repo exists, re-read from the HF API on 2026-10-06; only transformer and gla have local receipts.

**First experiment (2 GPU-h).** Source-only eligibility plus interface-capacity gate before any rule training or port (~2 GPU-h with 25% reserve, estimate). Step 1, eligibility (~0.1 GPU-h): run transformer-1.3B-100B on 14 candidate families under gold, shuffled-label and zero-shot conditions, 400 queries each, plus disagreement with transformer-2.7B-100B. Step 2, oracle interface ceiling (~0.8 GPU-h): with label-free maps fitted on FineWeb-Edu, directly optimize a per-episode free rank-8 64x64 state at the 4 sites to match the teacher's 8-shot predictions, then repeat constrained to the span of the 8 keys. Step 3, only if both pass (~0.6 GPU-h): train the free rule and the gradient-form rule (1 seed each), add a Task Operators replay as an upper reference, and report the write-direction clamp ablation. Blocked first on a model loop, the Stage-A doctors and a re-pinned fla image.

**Kill criteria.** Step 1: fewer than 8 held-out families whose gold-minus-shuffled gap clears its CI (including at least 4 function-induction families) means the teacher is too weak; stop. Step 2: if the free oracle cannot reach meaningful fidelity, the 64-d interface is too small; report that and stop. If the free and key-span oracles tie, the free rule and the gradient-form rule cannot separate; stop. If Step 3 ties, report 'fits a gradient-form description at this interface', not a porting result. Full Stage B (~11 GPU-h) and the port need the gauntlet (direction score 65 < 100).

**Relation to the existing program.** D19 architecture backfill, as the sweep ranks it; uses the fla/GDN asset; no tie to the CUA spine.

---

## 8. What drives FP4 training instability: grid, scale format, block size or rounding?

`C5-fp4-instability-factors`. Origin: Codex ranking doc #4. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 4.67, correctness 6.67, citability 8.67, novelty residual 4, feasibility 6.33.

**Corrected question.** In emulated FP4 training of small LLMs (30M-350M parameters, at least 3 seeds per cell, tuned learning rates), with other known instability causes held fixed, how much of the loss gap and spike rate is explained by the element grid, the block-scale format, the block size and the rounding mode, and do they interact? Compare formats at equal storage including scale bits, which ties block size to scale width, and test whether the prior finding that scale representation dominates survives once the grid also varies. Claims stop at emulated numerics, not FP4 hardware speed or energy.

**What was wrong with the original.** (1) The four named factors leave out causes with existing evidence: 1D-vs-2D block geometry and transposition scale inconsistency (2607.24953), LayerNorm affine-parameter quantization (2506.20752), per-tensor scaling (HiF4 v2), and BF16-exempt last blocks and RHT (2509.25149, 2609.02846); these must be fixed or included. (2) The factors are already partly separated: Hu et al. (2509.17791) ran thousands of combinations and conclude 'Scale Representation is the Primary Bottleneck' (grid fixed at E2M1); a Zenodo 2x2 study (Gomez Garcia, 2026-09-06; exists but its content was not opened by any reviewer) crosses block size and scale format in numerics only; Sun et al. (2501.02423) trained 366 models over grid and block size. (3) A full factorial at matched storage is impossible: bits per element = element bits + scale bits / block size, so iso-storage contours (4.25 and 4.5 b) are required. (4) UFP4 (2606.20381) covers only a grid x RHT x stochastic-rounding slice.

**Novelty.** NARROWED. Hu et al. hold the grid fixed; UFP4 holds the scale fixed; 2609.02846 compares whole recipes with one seed. Residual: grid x scale crossed at matched storage with seed replication and a variance decomposition.

**Why it matters.** Format designers currently argue from confounded data: NVIDIA's MXFP4-vs-NVFP4 comparison changes block size and scale format together and is not storage-matched (4.25 vs 4.5 b/elem). A clean crossing either strengthens the case for wider scales or shows the grid matters. Capped at 5: crowded (Graphcore could publish this crossing first), and 30M-350M emulated runs are far from the 8B native-Blackwell scale where decisions are made; in 2609.02846 Table 10 the emulation-path delta (0.0067 loss) is comparable to the block-size delta (0.0151).

**Closest priors.**

- [Elucidating the Design Space of FP4 Training (Hu, Luschi, Balanca)](https://arxiv.org/abs/2509.17791), 2025-09: Thousands of configurations up to 1B, but grid fixed at E2M1, block size varied only in reconstruction plots, storage not matched, no seeds.
- [UE5M3 FP4 Block Scaling for Stable Language Model Pretraining](https://arxiv.org/abs/2609.02846), 2026-09-02: Scale format at 8B with a matched block-32 control and an emulator control; single seed, whole recipes.
- [Scaling Laws for Floating-Point Quantization Training](https://arxiv.org/abs/2501.02423), 2025-01: Grid x block size in 366 training runs; no scale-format width, rounding or iso-storage.

**Citable anchors.**

- [Elucidating the Design Space of FP4 Training](https://arxiv.org/abs/2509.17791), 2025-09.
  - Role: closest prior.
  - Status: VERIFIED: exists; 'Scale Representation is the Primary Bottleneck'.
- [UE5M3 FP4 Block Scaling for Stable Language Model Pretraining](https://arxiv.org/abs/2609.02846), 2026-09-02.
  - Role: closest prior; emulation-error bound.
  - Status: VERIFIED: Table 10 B=16 2.3090 vs decoded-operand 2.3157 vs B=32 2.3241; one seed-42 trajectory per configuration.
- [Pretraining Large Language Models with NVFP4](https://arxiv.org/abs/2509.25149), 2025-09 (v1 2025-09-29; revised v2 2026-03-04).
  - Role: motivates (the confound).
  - Status: VERIFIED: Table 1 MXFP4 'E2M1 UE8M0 32' vs NVFP4 'E2M1 E4M3 16'; 'MXFP4 matches NVFP4 loss when trained on 36% more tokens'. CITATION AUDIT (FIX): revision date corrected from 2026-03-06 (announcement) to 2026-03-04 (v2 submission).
- [Rethinking Shrinkage Bias in LLM FP4 Pretraining (UFP4)](https://arxiv.org/abs/2606.20381), 2026-06-18.
  - Role: baseline slice.
  - Status: VERIFIED: fixes 'FP32 single-level' scale and block 16; 'Scale hierarchy design remains orthogonal'.
- [Scaling Laws for Floating-Point Quantization Training](https://arxiv.org/abs/2501.02423), 2025-01 (v3 2025-06-04).
  - Role: closest prior.
  - Status: VERIFIED: peer-reviewed (ICML 2025).
- [Characterization and Mitigation of Training Instabilities in Microscaling Formats](https://arxiv.org/abs/2506.20752), 2025-06-25.
  - Role: confound to hold fixed.
  - Status: VERIFIED: 'a key driver of this bias is the quantization of the layer normalization affine parameters'.

**First experiment (47 GPU-h).** Gate on part (b) only (~47 GPU-h, estimate; gauntlet applies). Phase 0 (~2 GPU-h): bit-exact unit tests of fake-quant kernels (E2M1, INT4, E1M2 grids; E8M0, UE4M3 plus FP32 tensor scale, UE5M3, BF16 scales; B16/B32) against a reference quantizer; declare the GEMM model (dequantize, BF16 matmul, FP32 accumulate); measure emulated throughput of a 30M Llama. Phase 1 (~45 GPU-h): 30M Llama on 1.2B FineWeb-Edu tokens; grid {E2M1, INT4} x scale/block {E8M0/B32 = 4.25 b, UE4M3+FP32/B16 = 4.5 b, UE5M3/B16 = 4.5 b, BF16/B32 = 4.5 b} plus a BF16 baseline; RTN forward, SR on gradients, LM head/embeddings/last block in BF16, 1D blocks, no RHT; 3-point LR sweep per cell, then 3 seeds at the tuned LR; one emulation-path control cell. Two-way ANOVA on loss gap with seed variance as error, the 4.5 b iso-storage contrast, and spike counts.

**Kill criteria.** Phase 0: if fake-quant overhead exceeds 4x, write a fused Triton quantizer before continuing. Phase 1: scale effect size at least 2x the grid's with a small interaction means the prior survives at 30M; then add rounding and block-size factors and replicate at 125M. Grid or interaction comparable to scale is the headline; replicate at 125M first. If every cell is within seed noise, 30M is too small to show instability; go straight to 125M with fewer cells. If the emulation-path control moves loss as much as the factors, restrict claims accordingly.

**Relation to the existing program.** Outside the CUA program; WS4-adjacent preemptible GPU filler with weak asset fit. Duplicates no existing direction.

---

## 9. Do answer selection and per-question re-attempts stack?

`C3-selection-and-allocation`. Origin: Codex ranking doc #2. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 4.33, correctness 6.67, citability 7.67, novelty residual 3.67, feasibility 7.

**Corrected question.** For one open long-reasoning model on H100s, does combining a learned answer selector with an adaptive per-question re-attempt policy raise accuracy at equal total measured GPU-seconds more than either part alone and more than one longer single pass, when evaluated on held-out problem families with allocation decided and scored on separate samples?

**What was wrong with the original.** (1) Separating selection from allocation is already done (2608.03961 uses selector-matched fixed-N controls; 2607.17531 studies fixed-pool selection; 2609.13257 charges the full generation-plus-verification fee). (2) ReProbe is a white-box, model-specific step verifier whose runtime numbers exclude generation, and CASE (2608.17124) shows hidden-state probes look accurate only through question-identity leakage, so splits must be grouped by question family. (3) 'Thinking Hard, Not Smart' studies allocation inside one trace, not external scheduling; external per-question allocators are well studied (2410.04707, 2604.14853, 2512.01457 and others). (4) 'Does the combination beat each component' is ill-posed: allocation always needs some selector, so the test is a 2x2 factorial with an interaction contrast and a rule for charging shared signals once. (5) Accuracy per GPU-second is maximized by spending almost nothing; the endpoint must be accuracy at matched GPU-seconds against a tuned single longer pass (SEVRA 2606.19808). (6) Replaying stored pools to decide and evaluate allocation is biased: Bae (2608.13087) found 2.2-2.6% in-sample gains that vanish out of sample.

**Novelty.** NARROWED. Each component is covered (2607.17531 for selection, 2608.03961 for allocation with matched selectors, 2609.13257 for cost framing). Residual: the selector x allocator interaction under wall-clock GPU-second accounting on held-out families, and whether Bae's out-of-sample result and CASE's decodability criterion transfer to long-reasoning LLMs.

**Why it matters.** A clean answer is useful but incremental in a crowded area (8+ adjacent preprints Jun-Sep 2026). The likely result is a sobering baseline ('they do not stack; a tuned longer pass matches them'); a positive interaction would give a concrete recipe (one shared probe signal for ranking and re-attempt triggering). Neither outcome changes the field's direction.

**Closest priors.**

- [Interpretable Adaptive Sampling for LLM Test-Time Scaling](https://arxiv.org/abs/2608.03961), 2026-08-04: Isolates allocation from the final selector with selector-matched controls; no learned selector crossing, token rather than GPU-second accounting.
- [Oracle Gap and Signal Fidelity: A Fixed-Pool Diagnostic for Test-Time Collaboration](https://arxiv.org/abs/2607.17531), 2026-07-20: Covers fixed-pool selection and its decomposition; no allocation.
- [Sampling Headroom Is Not Selection Gain: A Compute-Value Audit of Test-Time Scaling for Video World Models](https://arxiv.org/abs/2609.13257), 2026-09-06: Charges the full entry fee against matched uniform compute; mostly video, NFE accounting.
- [Sampling Luck Masquerades as Allocation Gain](https://arxiv.org/abs/2608.13087), 2026-08-13: Shows the in-sample allocation bias on TSP solvers only; no LLM replication.

**Citable anchors.**

- [Sampling Luck Masquerades as Allocation Gain: Auditing Test-Time Budget Allocation for Neural Combinatorial Optimization (Bae)](https://arxiv.org/abs/2608.13087), 2026-08-13.
  - Role: motivates disjoint decide/evaluate draws.
  - Status: VERIFIED: exists; single-author, NCO/TSP only.
- [Spread and Scale: What Determines Whether Test-Time Budget Allocation Pays (Bae)](https://arxiv.org/abs/2609.27917), 2026-08-21 (published date; ID month 2609).
  - Role: motivates the difficulty-spread predictor.
  - Status: VERIFIED: exists; ID-month vs date skew confirmed by judges 2 and 3, harmless.
- [A decodability criterion predicts when hidden-state selection beats majority voting in large language models (CASE)](https://arxiv.org/abs/2608.17124), 2026-08-17.
  - Role: selector arm and decodability predictor.
  - Status: VERIFIED: exists; tested only on non-thinking Qwen2.5/Llama-3.
- [Interpretable Adaptive Sampling for LLM Test-Time Scaling](https://arxiv.org/abs/2608.03961), 2026-08-04.
  - Role: closest prior (allocation with matched selector).
  - Status: VERIFIED: exists.
- [Oracle Gap and Signal Fidelity](https://arxiv.org/abs/2607.17531), 2026-07-20.
  - Role: baseline (fixed-pool selection).
  - Status: VERIFIED: exists.
- [Sampling Headroom Is Not Selection Gain (CVA)](https://arxiv.org/abs/2609.13257), 2026-09-06.
  - Role: cost-accounting instrument.
  - Status: VERIFIED: exists; cs.CV with one small LLM pass.

**First experiment (6 GPU-h).** Stage-0 precondition gate (~6 GPU-h, estimate): Qwen3-8B in thinking mode on a pinned vLLM image; problems split by family (~600 training, ~400 held-out); (a) measure real decode throughput and whole-job GPU-seconds (~0.5 GPU-h); (b) 8 samples per question (~40M tokens); (c) one charged HF prefill pass to extract answer-token hidden states; (d) train a CASE-style linear gate on training families and report family-grouped decodability AUC on held-out families; (e) measure difficulty spread (share of questions with pass@1 in [0.1, 0.9]) on draws disjoint from those used to fit the gate.

**Kill criteria.** Stop if held-out decodability AUC is below 0.60 or the spread share is below 20%; either is publishable as a negative transfer of CASE or Bae to long-reasoning models. Run the full 2x2 plus a tuned single-pass baseline (~30-40 GPU-h, ~1,200 held-out questions, live fresh draws, gauntlet required) only past the gate; drop the line if the interaction is not positive beyond both single arms and the longer single pass.

**Relation to the existing program.** Orthogonal to the program, with no CUA, language or GDN asset fit; duplicates no existing direction.

---

## 10. Is adversarial spec weakness a property of the spec or of the attacker?

`C4-specification-robustness`. Origin: Codex ranking doc #3. **Recommendation: DROP.**

Scores (3-judge means): significance 4, correctness 6, citability 8, novelty residual 4, feasibility 5.

**Corrected question.** For a frozen set of Dafny/Verus specifications with an independent hidden correctness oracle, does the rate at which a budgeted adversary finds programs that formally verify against the spec yet are wrong (a) scale predictably with adversary compute and (b) rank specs the same way across independent attacker models? Only if so, does that score predict how often RL on those specs rewards spec-hacking programs better than mutation- or test-based adequacy metrics?

**What was wrong with the original.** (1) 'Fixed intended behaviour' was undefined: without a named oracle (reference implementation, hidden tests, independent correct solutions), 'incorrect' is circular. (2) The cited sources (an MIT thesis, SpecRL, Spec-Harness) do not search over programs; SpecRL mutates input-output pairs. (3) The adversarial counter-implementation evaluator is occupied: VeriScale (2605.22368) uses an LLM red team to write wrong Lean implementations the spec accepts; PROBE (ACL Findings 2026) uses counter-implementations to tighten properties (+9.79% mutation score, 45 bugs); POSTCONDBENCH and nl2postcond define the two-sided reject-wrong/accept-right metric. (4) A fixed adversary over fixed specs would replicate VeriScale unless it adds budget scaling, attacker transfer or predictive validity for RL.

**Novelty.** NARROWED. Parts (a)-(b) are a methods note on the VeriScale/PROBE line. Part (c), predicting RL spec-hacking, is open only for formal specs; for test suites it is close to 2606.16062, 2607.11022 and CATCH (2609.39533).

**Why it matters.** A validated predictor would replace LLM-judge filtering in Dafny/Verus RL corpora (the MIT thesis found much of a 2.2% to 58.1% reward gain was spec hacking, from inspecting 5 prompts per checkpoint). But part (c) needs 150-400 GPU-h of RLVR, the no-paid-API rule removes frontier attackers, and the work uses none of the program's assets.

**Closest priors.**

- [VeriScale: Adversarial Test-Suite Scaling for Verifiable Code Generation](https://arxiv.org/abs/2605.22368), 2026-05-21: Owns the 'measure' half on Lean/Verina with one fixed attacker; no budget scaling, attacker transfer or RL link.
- [Beyond Superficial Tests: Adversarial Refinement for Reliable Property-Based Testing (PROBE)](https://aclanthology.org/2026.findings-acl.683/), 2026 (Findings of ACL): Owns the 'improve' half by execution on Python properties, not formal specs.
- [POSTCONDBENCH: Benchmarking Correctness and Completeness in Formal Postcondition Inference](https://arxiv.org/abs/2605.03356), 2026-05-05: Defines the two-sided mutant-based adequacy metric; non-adversarial.
- [When the Reward Suite Is Leaky: A Preregistered Causal Contrast of Natural Verifier False Positives in RLVR](https://arxiv.org/abs/2607.11022), 2026-07-13: A pre-training leakiness audit predicts rewarded false positives (Spearman 0.80) for test suites; the formal-spec version is the open residual.

**Citable anchors.**

- [VeriScale: Adversarial Test-Suite Scaling for Verifiable Code Generation](https://arxiv.org/abs/2605.22368), 2026-05.
  - Role: closest prior.
  - Status: VERIFIED (full text): 'a more capable model acts as a red team ... crafting adversarial implementations'.
- [Beyond Superficial Tests: Adversarial Refinement for Reliable Property-Based Testing (PROBE)](https://aclanthology.org/2026.findings-acl.683/), 2026 (Findings of ACL 2026).
  - Role: closest prior.
  - Status: VERIFIED: ACL Anthology page resolves (HTTP 200, judges 2 and 3).
- [Automating Formal Verification with Reinforcement Learning and Recursive Inference (MIT MEng thesis)](https://arxiv.org/abs/2605.30914), 2026-05-29.
  - Role: motivates part (c).
  - Status: VERIFIED (full text): 'much of this progress was specification hacking'; diagnosis over five logged prompts.
- [POSTCONDBENCH](https://arxiv.org/abs/2605.03356), 2026-05.
  - Role: baseline metric.
  - Status: VERIFIED (full text).
- [Spec-Harness: Measuring and Improving Behavioral Adequacy of LLM-Synthesized Formal Specifications](https://arxiv.org/abs/2604.00280), 2026-04 (v1 2026-03-31).
  - Role: baseline metric.
  - Status: VERIFIED: v2 title; v1 titled VeriAct.
- [A Benchmark for Vericoding: Formally Verified Program Synthesis](https://arxiv.org/abs/2509.22908), 2025-09.
  - Role: evaluation instrument and oracle source.
  - Status: VERIFIED (full text): 3,029 Dafny specs; APPS(test) subset has hidden tests and multiple human solutions.

**First experiment (10 GPU-h).** Attacker-invariance test, parts (a) and (b) only, no RL (~10 GPU-h, estimate; gauntlet applies). Freeze 200 Vericoding APPS(test) Dafny tasks with stdin-to-argument adapters where the reference verifies and agrees with APPS hidden tests; oracle = hidden tests plus at least 2 cross-validated independent human solutions, never shown to the adversary. Three open-weight coder adversaries x 2 strategies (direct, weaken-then-implement) x k in {1, 4, 16, 64}. Success = verifies with no assume, verify-false or edited contract AND diverges from the oracle on a hidden input. Fit success against log k and compute cross-attacker Kendall tau of per-spec weakness; compare with mutant discrimination on the same specs.

**Kill criteria.** Tau below 0.4 between attackers means the score is attacker-specific: stop and publish the negative. Tau at least 0.6 for every attacker pair at k=64 with monotone saturating curves is required before any part (c) RLVR (150-400 GPU-h). Never report a spec with no counterexample found as robust; scores are budget-relative lower bounds.

**Relation to the existing program.** Orthogonal to the CoTCodec/CUA program, with no asset fit; no existing direction covers it.

---

## 11. Translation-supervised boundaries in byte-level models

`E3-d18-translation-byte-boundaries`. Origin: existing: directions/18. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 4, correctness 5.33, citability 8.33, novelty residual 4, feasibility 3.67.

**Corrected question.** In a byte-level language model with a learned, differentiable boundary predictor (H-Net style), does a loss that pushes boundaries onto corresponding spans of translation pairs improve terminology and tool-schema exactness across languages, without worse bits per byte, beyond per-language rate calibration, monolingual boundary supervision and fixed-boundary cross-lingual state alignment? First check on released checkpoints whether rate calibration already reaches most of the achievable boundary correspondence.

**What was wrong with the original.** (1) BLT's boundaries come from a separately trained entropy model and receive no gradient, so BLT is a non-learned control, not a supervisable substrate; the treatment needs an H-Net- or Bolmo-style learned head. (2) Cross-lingual compute parity is reachable by rate calibration alone (MAGNET's per-script priors give 'equitable segmentation across languages'; UBE 2610.01984), so parity is not the delta. (3) Token-level unbalanced optimal-transport alignment of parallel hidden states is CAROT's (2609.06381), so only boundary-mass transport remains. (4) The question's endpoint (parity) did not match the direction's registered endpoint (terminology and tool-schema fidelity). (5) No licence-cleared parallel corpus exists in the repo. Also, Bolmo's boundary predictor is non-causal (one byte of lookahead), which conflicts with the contract's causal-head requirement.

**Novelty.** NARROWED. MAGNET takes parity, CAROT takes state alignment, 2608.27658 defines monolingual boundary supervision. Residual: one auxiliary boundary-transport loss.

**Why it matters.** Would tell byte-LM builders whether parallel-span supervision does anything beyond rate priors and monolingual distillation, and would test 2608.03599's claim that boundary placement can be changed independently of next-byte capability. Capped at 5: one loss term at ~40M on a mostly cross-script language set, with no corpus, evaluation set or substrate code yet.

**Closest priors.**

- [MAGNET: Improving the Multilingual Fairness of Language Models with Adaptive Gradient-Based Tokenization](https://arxiv.org/abs/2407.08818), 2024-07-11: Parity from per-script rate priors with no translation supervision; the mandatory control.
- [Cross-Lingual Representation Alignment by Token-Level Optimal Transport in a Language-Agnostic Space (CAROT)](https://arxiv.org/abs/2609.06381), 2026-09-06: Owns unbalanced-OT state alignment over parallel sentences, with fixed boundaries.
- [When Tokenizers Fail: Byte-Level Chunking for Zero-Shot Transfer to Low-Resource Languages](https://arxiv.org/abs/2608.27658), 2026-08-27: Monolingual boundary supervision (ratio loss, POS) on byte chunking; no parallel data.
- [Disentangling Language Modeling and Boundaries](https://arxiv.org/abs/2608.03599), 2026-08-04: Position paper proposing boundaries can be retrained with the LM held fixed; untested.

**Citable anchors.**

- [Dynamic Chunking for End-to-End Hierarchical Sequence Modeling (H-Net)](https://arxiv.org/abs/2507.07955), 2025-07.
  - Role: treatment substrate.
  - Status: VERIFIED (full text): learned differentiable routing with a ratio loss.
- [Bolmo: Byteifying the Next Generation of Language Models](https://arxiv.org/abs/2512.15586), 2025-12.
  - Role: control (subword-distilled boundaries).
  - Status: VERIFIED (full text): boundary predictor 'is non-causal: it has access to one byte of future context'.
- [MAGNET: Improving the Multilingual Fairness of Language Models with Adaptive Gradient-Based Tokenization](https://arxiv.org/abs/2407.08818), 2024-07-11 (v1; v2 2024-11-17).
  - Role: closest prior; rate-calibration control.
  - Status: VERIFIED (full text): 'infer boundaries leading to equitable segmentation across languages'. CITATION AUDIT (FIX): previous title was a shortened, invented form; replaced with the real arXiv title.
- [CAROT](https://arxiv.org/abs/2609.06381), 2026-09-06.
  - Role: closest prior; state-alignment control.
  - Status: VERIFIED (full text): token-level unbalanced Sinkhorn OT over parallel hidden states.
- [When Tokenizers Fail: Byte-Level Chunking for Zero-Shot Transfer to Low-Resource Languages](https://arxiv.org/abs/2608.27658), 2026-08.
  - Role: monolingual-supervision control.
  - Status: VERIFIED; EMNLP 2026 acceptance self-reported, not verified.
- [Byte Latent Transformer: Patches Scale Better Than Tokens](https://arxiv.org/abs/2412.09871), 2024-12.
  - Role: non-learned control.
  - Status: VERIFIED (full text): separately trained entropy model; boundaries get no gradient.

**First experiment (0.5 GPU-h).** Stage 0 headroom probe only (~0.5 GPU-h, no training): on FLORES+ dev/devtest for EN-ZH, EN-KO and EN-PL with frozen aligner spans, compute aligned-span boundary correspondence (the existing NumPy UOT cost as an evaluator) for released H-Net checkpoints, Bolmo-1B boundaries, and a rate-calibrated reference with per-language thresholds matched on patches per sentence, against a permuted-alignment floor and aligner-derived oracle boundaries.

**Kill criteria.** If rate-calibrated boundaries already reach at least 90% of the correspondence ceiling, there is no room for a boundary-transport delta: stop and record the negative. The Stage 1 screen (~16 GPU-h, 4 arms x 3 seeds at ~40M, gauntlet) runs only after a licensed parallel corpus, a terminology/tool-schema evaluation set, a differentiable torch loss and H-Net-style training code exist; it passes only if boundary transport beats both monolingual supervision and state alignment by at least 3 points macro with no language down more than 5.

**Relation to the existing program.** D18 language-thread architecture backfill. CAROT takes the state term and MAGNET takes parity; only the Stage 0 probe is justified now.

---

## 12. Randomized first use of a stored memory to measure its value

`E2-d17-causal-memory-holdout`. Origin: existing: directions/17. **Recommendation: DROP.**

Scores (3-judge means): significance 4, correctness 5.67, citability 8.33, novelty residual 3, feasibility 5.67.

**Corrected question.** In multi-step tool-agent tasks where one stored memory per episode is randomly served or withheld at its first eligible use with known probability, does that randomization identify an average and covariate-conditional effect of serving the memory that (a) a doubly-robust estimator recovers against a deterministic paired-replay oracle and (b) can be predicted from information available when the memory was written, despite CMP's finding that query-independent predictors reach r <= 0.10?

**What was wrong with the original.** (1) One random assignment per item identifies a population or covariate-conditional effect, never 'per-item memory value' (the direction's own estimand section says so). (2) Known-propensity randomized memory exposure is occupied by Causal Memory Policy (CMP, 2610.02070), uncited in the repo. (3) Write-time covariates predicting the effect is untested on non-engineered data, and CMP Sec 4.3 reports no query-independent aggregation above r = 0.10 and calls the limit 'structural'; the repo's Spearman 0.88/0.90 partly recovers generator-encoded labels. (4) Memory effects are often joint: CMP Sec 4.1 shows correctness near 0.2 until every required memory is retrieved, then 0.73, so a one-candidate effect is likely erased. (5) The status 'real-model pilot blocked' is stale: Qwen 4B and 9B runs happened and failed promotion gates. (6) Learning a memory gate from executable paired uplift with a frozen executor is UpliftMem (2609.36805).

**Novelty.** NARROWED. CMP owns known-propensity identification; UpliftMem owns the execution-uplift gate. Residual: first-service timing, executable agent outcomes, a paired-replay oracle, and a write-time conditional effect, with a strong null prior.

**Why it matters.** A positive result would qualify CMP's 'structural' no-retention claim for agentic tool settings; a negative extends CMP's null to learned write-time predictors with an oracle-audited estimator. Either is a narrow methodological contribution, workshop-level if negative.

**Closest priors.**

- [Causal Memory Policy: Making Memory Utility Identifiable by Intervening on Retrieval](https://arxiv.org/abs/2610.02070), 2026-10-01 (v2 2026-10-02): Randomizes retrieval exposure with known propensities and estimates utility by SNIPW; QA outcomes, no oracle, no first-service timing, no write-time predictor.
- [UpliftMem: Learning Set-Level Uplift for Agent Memory Retrieval](https://arxiv.org/abs/2609.36805), 2026-09-29: Learns retrieval from executable paired uplift with a frozen executor; set-level, query-time, adaptively chosen probes.
- [Learning What to Remember: Long-Horizon Counterfactual Memory Optimization (MGPO)](https://arxiv.org/abs/2609.37930), 2026-09-29: Per-write counterfactual credit on the write/retain side, which D17 excludes.
- [What Should an Agent Remember? Disentangling Retention from Retrieval in Bounded-Memory Evaluation](https://arxiv.org/abs/2610.00366), 2026-09-30: Argues retention is necessarily query-independent; supports separating first-service from write claims.

**Citable anchors.**

- [Causal Memory Policy (Behnam, Wang)](https://arxiv.org/abs/2610.02070), 2026-10-02 (v2).
  - Role: closest prior; source of both falsifier priors.
  - Status: VERIFIED (abstract confirmed by judge 1: 'known propensities'); Sec 4.3 r <= 0.10 and Sec 4.1 0.2-to-0.73 jump read by the reviewer.
- [UpliftMem: Learning Set-Level Uplift for Agent Memory Retrieval](https://arxiv.org/abs/2609.36805), 2026-09-29.
  - Role: baseline.
  - Status: VERIFIED: exists; ICLR 2027 submission.
- [Hindsight Memory-PRM: Supervising Memory Management with Auditable Hindsight Credit](https://arxiv.org/abs/2608.29605), 2026-08-30.
  - Role: baseline.
  - Status: VERIFIED: exists.
- [What Should an Agent Remember? (Huang)](https://arxiv.org/abs/2610.00366), 2026-09-30.
  - Role: motivates the reporting control.
  - Status: VERIFIED: exists.
- [MGPO: Long-Horizon Counterfactual Memory Optimization](https://arxiv.org/abs/2609.37930), 2026-09-29.
  - Role: write-side counterfactual-credit prior.
  - Status: VERIFIED: exists.
- [RAISE: Diagnosing Acquisition Collapse in Costly LLM Signals](https://arxiv.org/abs/2608.10441), 2026-08.
  - Role: learnability pre-check (reward-SNR floor).
  - Status: VERIFIED: exists.

**First experiment (6 GPU-h).** Stage-1a transfer and interference kill screen (~6 GPU-h, estimate): frozen Qwen3.5-4B (9B excluded after failed calibration), greedy vLLM with batch-invariant decoding for paired audits after the A/A replay receipt passes; one non-engineered executable source family (ALFWorld cross-episode notes preferred, Mem2ActBench alternative); one retained candidate per episode randomized at first eligible retrieval with p = 0.25, journaled before continuation; 1,600 randomized episodes, 400 sealed paired audits, and 300 two-candidate 2x2 interference episodes. CPU prerequisite: rerun the symbolic doctor with an injected joint-requirement world.

**Kill criteria.** Kill the direction if the write-time conditional-effect predictor reaches sealed Spearman below 0.10 against the paired oracle (reproducing CMP's null in agents) or if the interaction |tau11 - tau10 - tau01| is at least the mean main effect. Run the gate-vs-CMP/UpliftMem/Hindsight-PRM comparison only if |AIPW - oracle| <= 0.03 with arm ESS >= 400, Spearman >= 0.20, and the interaction check passes.

**Relation to the existing program.** D17. Largely duplicated by CMP (2610.02070) and narrowed by UpliftMem; the memory program is demoted to WS3's memory-vs-weights baseline arm. Freeze it and cite CMP in that arm's design.

---

## 13. Do recurrent-state gates penalize languages that need more tokens?

`E5-d20-semantic-clock-gate-parity`. Origin: existing: directions/20 + proposal. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 3, correctness 5.67, citability 8, novelty residual 4, feasibility 6.

**Corrected question.** In attention-free delta-rule models (RWKV-7 and a pure Gated DeltaNet checkpoint), does exact-match recall carried by the recurrent state fall as the same content takes more tokens, and is the drop due to per-token decay or to interference from more writes? Test it first in English artificially re-segmented into more tokens, using a halved decay rate as the intervention; the answer does not transfer to deployed Qwen3.5 hybrids, whose recall flows through full attention.

**What was wrong with the original.** (1) In Qwen3.5-4B hybrids the recurrent state does not carry recall: 0.2-3.6% is recovered by recurrent interventions vs 96-100% by KV interventions (2609.33093), so the hybrid readout is an artificial stress test. (2) Passive decay over distance is minor next to memory-load interference: 128 to 1024 tokens costs 'only a modest decline' while 1 to 16 facts costs ~30-40 pp (2609.33093). (3) 'Released gates fail to self-normalize per-language token rate' is untested, and Tallec and Ollivier predict quasi-invariance. (4) The question merged phase 0 (a training-free decay rescale) with phase 1 (a parity loss). (5) Closer priors appeared after the sweep (2609.35378, 2609.33093, SpectralShift 2609.14320). Subject coverage is also weak: the rwkv7-1.5B-world card lists 8 languages, none high-fertility, and the m-a-p GDN-1.3B checkpoint has no model card.

**Novelty.** NARROWED. Bandarkar et al. (2609.35378) claim the first study of hybrid-attention multilinguality; Lee et al. (2609.33093) own the load-vs-distance decomposition in English; SpectralShift reshapes the GDN decay spectrum for distance. Residual: the fertility axis on attention-free models.

**Why it matters.** The most likely answer is 'interference dominates', which cheaply kills the phase-1 parity loss and extends Lee et al.'s English finding to a fertility axis. A positive decay share would surprise. Practical reach is limited to attention-free models.

**Closest priors.**

- [How Linear Attention Remembers](https://arxiv.org/abs/2609.33093), 2026-09-27: Load-vs-distance decomposition and recall localization in English; no fertility axis.
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28: Descriptive multilingual NIAH on hybrids motivated by token inflation; no gate ledger, matched content or decay surgery.
- [SpectralShift: Effective Context Window Extension of Gated DeltaNet via Spectral Reparameterization](https://arxiv.org/abs/2609.14320), 2026-09-13: GDN decay-spectrum manipulation tied to retrieval distance, via continued pretraining, not fertility.

**Citable anchors.**

- [How Linear Attention Remembers (Lee, Park, Kim, Ko)](https://arxiv.org/abs/2609.33093), 2026-09.
  - Role: closest prior; scopes the claim.
  - Status: VERIFIED (full text): Sec 4.1 recurrent 0.2-3.6% vs KV 96-100% on Qwen3.5-4B; Sec 4.2 'Memory load has a substantially larger effect than elapsed context alone' (abstract claim confirmed by judge 1).
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28.
  - Role: closest prior.
  - Status: VERIFIED (full text): Qwen3.5 tokenizer 2.6x longer in Yoruba; hybrid deficit 'initially larger outside English'.
- [SpectralShift](https://arxiv.org/abs/2609.14320), 2026-09-13.
  - Role: decay-manipulation prior.
  - Status: VERIFIED (full text): High-Retrieval 'scales the alpha projections'; applied before continual pretraining.
- [fla-hub/rwkv7-1.5B-world model card](https://huggingface.co/fla-hub/rwkv7-1.5B-world), accessed 2026-10-06.
  - Role: attention-free subject.
  - Status: VERIFIED: card lists 8 languages, none in the high-fertility set; apache-2.0.
- [m-a-p/1.3B-100B-GatedDeltaNet-pure checkpoint](https://huggingface.co/m-a-p/1.3B-100B-GatedDeltaNet-pure), accessed 2026-10-06.
  - Role: pure-GDN subject (the one Lee et al. used).
  - Status: VERIFIED exists; 'No model card', so training data undocumented.

**First experiment (3 GPU-h).** Language-free decomposition before any translation work (~3 GPU-h, estimate): m-a-p/1.3B-100B-GatedDeltaNet-pure at commit 930ed6ae and fla-hub/rwkv7-1.5B-world; English episodes (K facts with script-neutral 4-digit answers, distractors, query) re-segmented to f in {1.0, 1.5, 2.0, 2.7} times the canonical token count with a frozen splitting rule, crossed with decay rescale r in {1, 2} and load K in {1, 4, 8, 16}; 600 episodes per cell; an elapsed-only filler control at f = 1; an identity hook check first; BPB reported per f.

**Kill criteria.** If the decay-slope point estimate is below 3 exact-match points per log-fertility unit on both subjects, kill the phase-1 span-parity loss without any translation, Common Crawl partialling or template QA. Fund the 16-language translation-paired run only if it reaches 3 or more on both. If not run, close D20 by citing 2609.33093.

**Relation to the existing program.** D20. The sweep already stops its Qwen leg (stop item 3) and folds the translated split-prefill check into P-GSM; only this synthetic-English decomposition survives as backfill.

---

## 14. Storage-level lifecycle audit of agent memory libraries

`E8-memory-lifecycle-audits`. Origin: existing: memory program (docs/memory-handoff.md). **Recommendation: DROP.**

Scores (3-judge means): significance 2.67, correctness 5, citability 6.33, novelty residual 3.67, feasibility 8.33.

**Corrected question.** Across the program's ~21 lifecycle receipts, plus a repaired Letta Code audit at both the pinned historical revision and the current release, do agent-memory systems leave deleted content physically recoverable on disk (database heap and WAL, Git objects, orphaned folders) and fail to keep writes atomic when a commit fails? One revision's doctor is a bug report; only the cross-system matrix is a research result.

**What was wrong with the original.** (1) The pinned revision is not 'current Letta Code': a575e11 (0.30.20) is 605 commits behind main, and the public memory() tool it audits was removed upstream (PR #4745, merged 2026-09-25); writer leases (#4626) and the root MemFS layout (#3842) also changed. (2) Lifecycle correctness is not unoccupied: 2609.08258 audits revocation in Graphiti/Zep, mem0, langmem and cognee; the 2604.16548 survey defines a forget-and-rollback phase; MemLeak (2610.04195), 2609.04875 and MemTxn (2607.27834) cover isolation, behavioural deletion leakage and transactions. Storage-forensic residue plus commit atomicity on exact revisions was not found. (3) It does not use the H100 node (zero GPUs). Reviewer findings: the v3 atomicity, retry and restart verdicts are void because the fault injection never fired (the commit succeeded); two security-relevant observations [details withheld pending coordinated disclosure to the maintainers] look real and need disclosure to the maintainers.

**Novelty.** NARROWED. Adjacent work stays at the behavioural or retrieval level (2609.08258, 2609.04875) or proposes remedies without auditing shipped systems (MemTxn). Residual: a cross-system storage-level residue and atomicity matrix. Workshop-tier.

**Why it matters.** Useful to memory-library maintainers and right-to-erasure researchers; not field-changing, and only the cross-system synthesis is publishable. The disclosure obligation stands regardless of the research verdict.

**Closest priors.**

- [Revoked but Still Authoritative: An Empirical Study of Revocation Enforcement in Agent-Memory Systems](https://arxiv.org/abs/2609.08258), 2026-09-08: System-by-system audit of revocation in retrieval behaviour, not on-disk residue or atomicity.
- [A Survey on Long-Term Memory Security in LLM Agents (Lin et al.)](https://arxiv.org/abs/2604.16548), 2026-04: Defines the lifecycle framing including forget and rollback; no audit of pinned revisions.
- [MemTxn: A Transaction Boundary for Source-Supported Updates and Complete-State Recovery in Agent Memory](https://arxiv.org/abs/2607.27834), 2026-07-30: Remedy side of commit atomicity; does not audit shipped systems.
- [Forgetting Without Restarting: Execution-State Unlearning for Stateful LLM Agents](https://arxiv.org/abs/2609.04875), 2026-09-04: Deletion leakage at the behavioural level, not storage level.

**Citable anchors.**

- [Revoked but Still Authoritative (Shen, Toyoda, Leung)](https://arxiv.org/abs/2609.08258), 2026-09.
  - Role: closest prior.
  - Status: VERIFIED: exists.
- [A Survey on Long-Term Memory Security in LLM Agents (Lin et al.)](https://arxiv.org/abs/2604.16548), 2026-04.
  - Role: motivates.
  - Status: VERIFIED: exists.
- [Forgetting Without Restarting (Yao et al.)](https://arxiv.org/abs/2609.04875), 2026-09.
  - Role: motivates.
  - Status: VERIFIED: exists; 'memory deletion leaves leakage unchanged'.
- [MemTxn (Cui et al.)](https://arxiv.org/abs/2607.27834), 2026-07.
  - Role: closest prior (remedy).
  - Status: VERIFIED: exists.
- [MemLeak: Cross-User Semantic Leakage in Multi-Tenant AI Agent Memory](https://arxiv.org/abs/2610.04195), 2026-10.
  - Role: closest prior (isolation axis).
  - Status: VERIFIED: exists.
- [letta-ai/letta-code PR #4745 'refactor(tools): remove memory and memory_apply_patch'](https://github.com/letta-ai/letta-code/pull/4745), 2026-09-25.
  - Role: evidence that the audited surface no longer exists upstream.
  - Status: VERIFIED (gh): merged 2026-09-25; release v0.34.4 = f898fda6 (2026-10-04).

**First experiment (0 GPU-h).** Zero GPUs, ~2-3 engineering days, under 1 CPU-hour. (1) Rerun the frozen a575e11 doctor as v4 with a process-independent fault (a pre-commit hook exiting 75, after checking runGit does not pass --no-verify) and a precondition that the injection fired at least once; seal it as a historical receipt and relabel v3 a pre-result diagnostic. (2) Write doctor v2 against v0.34.4 (f898fda6), driving the generic file tools and post-turn commit sync with no model calls, and rerun the same falsifiers. (3) Normalize all 21 lifecycle receipts into one storage-level matrix (logical delete, physical residue location, scoped purge, rejected-write atomicity, retry idempotency).

**Kill criteria.** Any atomicity, retry or restart verdict without proof that the fault injection fired is void. If the matrix does not show residue or non-atomicity as the modal outcome across at least 5 independent systems, close the direction. Disclose the security-relevant observations to the maintainers before any write-up [details withheld pending coordinated disclosure to the maintainers].

**Relation to the existing program.** Item 2 on the sweep's stop list (the memory lifecycle-doctor line as a main output). Freeze the line, reuse its gates inside WS3, and do the responsible disclosure as housekeeping. Uses no GPU.

---

## 15. Reasoning-language routing for tool-using agents (Paper 1)

`E1-paper1-language-routing`. Origin: existing: directions/01-language.md, Paper 1. **Recommendation: DROP.**

Scores (3-judge means): significance 4, correctness 5, citability 8.33, novelty residual 3.33, feasibility 4.33.

**Corrected question.** For English-input, tool-using agent tasks with fixed tool schemas and English final answers, does choosing the style of the agent's intermediate messages per task (unconstrained, English, compressed English, structured English or Chinese) beat the best single fixed style on success, cost and latency on held-out tasks, with measured language compliance treated as a mediator and tool-argument language errors counted separately? It is only worth asking for models where prompting actually changes the reasoning language.

**What was wrong with the original.** (1) A system-prompt addendum does not reliably set the reasoning language: 2608.11110 (COLM 2026) reports 0.79% (Gemma) and 0.08% (Sarvam) compliance and calls it 'a failed manipulation, not a null'. (2) The '20-40% savings' prior has no agent evidence: EfficientXLang is math-only and loses up to 12.52% relative on AIME25; BabelArena finds non-English agent runs use up to ~2x the input tokens; 2609.32961 shows fewer tokens need not mean lower cost or latency. (3) Fixed schemas do not fix argument contents: reasoning language leaks into tool arguments (2610.03136; 2608.11715). (4) Inference-time routing over reasoning languages already exists (CLSR 2606.29354, UL-XCoT 2604.20090, RAAI 2609.04653). Fails the correctness gate (lowest judge correctness 4).

**Novelty.** NARROWED. CLSR owns test-time routing over reasoning 'languages'; 2608.11110 owns cross-lingual policy measurement in tool agents. Residual: the agent success/cost/latency frontier with intention-to-treat analysis, a compliance mediator and a tokenizer-vs-trajectory split.

**Why it matters.** Mainly a correction to the stale '20-40% savings' and 'best inference-time-only approach' framing in directions/01. The probable finding is negative or narrow (compressed or structured English captures most of any saving).

**Closest priors.**

- [Actions Speak Louder than Words: Measuring Cross-Lingual Policy Retention in Tool-Using Agents](https://arxiv.org/abs/2608.11110), 2026-08-11: Shows the English pivot is causally load-bearing in tool agents and prompt control of reasoning language fails; no routing or cost frontier.
- [When LLMs Develop Languages: Symbolic Communication for Efficient Multi-Agent Reasoning (CLSR)](https://arxiv.org/abs/2606.29354), 2026-06-28: Test-time router over reasoning languages for accuracy-token trade-off; QA and math, not tool agents.
- [Less Languages, Less Tokens: UL-XCoT](https://arxiv.org/abs/2604.20090), 2026-04-22: Inference-time per-query reasoning-language selection; non-agent.
- [Investigating the Role of Reasoning-Language Alignment in Monolingual RAG](https://arxiv.org/abs/2610.03136), 2026-10-02: Reasoning-language control in an agentic RAG loop, with leakage into queries; one model, no token accounting.

**Citable anchors.**

- [Actions Speak Louder than Words (Mukherjee, Bali, Sitaram)](https://arxiv.org/abs/2608.11110), 2026-08.
  - Role: closest prior.
  - Status: VERIFIED: 'Published as a conference paper at COLM 2026'; compliance 0.79% and 0.08%.
- [CLSR: Symbolic Communication for Efficient Multi-Agent Reasoning](https://arxiv.org/abs/2606.29354), 2026-06.
  - Role: closest prior and baseline.
  - Status: VERIFIED (full text): 'a test-time framework'; router 'adaptively selects and composes these languages'.
- [EfficientXLang: Towards Improving Token Efficiency Through Cross-Lingual Reasoning](https://arxiv.org/abs/2507.00246), 2025-06-30.
  - Role: the repo's main prior; motivates.
  - Status: VERIFIED (full text): fewer tokens on easy math; up to 12.52% relative drop on AIME25.
- [Investigating the Role of Reasoning-Language Alignment in Monolingual RAG (Hauck et al.)](https://arxiv.org/abs/2610.03136), 2026-10.
  - Role: motivates the tool-argument leakage outcome.
  - Status: VERIFIED (full text): retrieval queries issued 'in French rather than German'.
- [Beyond Token Savings: A Systematic Study of Context Compression in LLM Agents](https://arxiv.org/abs/2609.32961), 2026-09.
  - Role: motivates the joint frontier.
  - Status: VERIFIED (full text): 'fewer tokens need not mean faster or cheaper execution'.
- [tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045), 2024-06.
  - Role: evaluation instrument.
  - Status: VERIFIED: exists; venue not verified; LLM user simulator is a confound.

**First experiment (20 GPU-h).** If run at all, a go/no-go gate on oracle headroom and compliance before any router (~20 GPU-h, estimate; gauntlet applies): Qwen3-30B-A3B and Qwen3.5-4B on local vLLM after a 0.5 GPU-h throughput probe; 5 fixed register conditions; tau-bench retail (115 tasks) x k = 3, i.e. 3,450 rollouts, with a fixed local user simulator at T = 0. Record intention-to-treat pass^1 and pass^3, per-message register compliance, tool-argument language mismatch, tokens split into tokenizer and trajectory terms, and latency on an exclusively allocated GPU. Blocked until a tau-bench adapter completes a live run (every live agent run so far failed protocol checks) and vLLM is in a runnable image.

**Kill criteria.** Build a router only if (1) the per-task oracle headroom on success at matched cost exceeds the 95% bootstrap interval of trial-to-trial noise on the 60% split and (2) at least one non-default condition reaches 80% or higher compliance. Otherwise publish the negative with the mediator analysis and withdraw the '20-40% savings' and 'best inference-time-only approach' claims from directions/01.

**Relation to the existing program.** The existing Paper 1. Superseded by S2/WS2 as the program's language paper; its reasoning-language question survives as S2's arm (d), with the preregistered H1 from 2610.03136.

---

## 16. Translation-equivariant recurrent-state writes

`E7-d22-translation-equivariant-writes`. Origin: existing: directions/22 + proposal. **Recommendation: BACKFILL.**

Scores (3-judge means): significance 3, correctness 4.67, citability 8.33, novelty residual 3.33, feasibility 5.33.

**Corrected question.** In Gated DeltaNet hybrids where attention cannot reach the fact (sliding-window-only attention, facts beyond the window), does a loss that makes the recurrent-state write for a fact match across its translations improve cross-lingual recall beyond the same loss on projections and a generic recurrent-path auxiliary loss (2610.06750), while keeping output-language fidelity? First check that a small from-scratch model can do state-carried cross-lingual recall at all.

**What was wrong with the original.** (1) In frozen full-attention hybrids (Qwen3.5-4B) the recurrent state does not carry recalled facts: recurrence-only retrieval is 0.00 (2609.04434) and recurrent interventions recover 0.2-3.6% (2609.33093), so D22's phase 0 is pre-answered. (2) The state does carry output language ('Lang. follow 0.97 0.70 0.01'; the answer 'takes ... its language from the recurrent side'), so a full equivariance loss on writes would fight a needed function; it needs a language-invariant subspace or an output-language guardrail. (3) Above-floor cross-lingual recall in a 57M/200M-token from-scratch hybrid is not established (gate G1). Fails the correctness gate (lowest judge correctness 4).

**Novelty.** NARROWED. 2610.06750 occupies 'add an auxiliary loss so hybrids use the recurrent path' (no multilingual content); 2610.01921 aligns a non-residual object cross-lingually; 2609.35378 owns the descriptive hybrid cross-lingual framing. Residual: a semantic objective on the recurrent write vs generic recurrent-path forcing, in the regime where attention cannot reach the fact.

**Why it matters.** Narrow: production hybrids keep full attention, which already does the recall, so reach is limited to sliding-window, KV-evicted or pure-recurrent settings; at 57M-134M the instrument may sit at floor; and the required subspace restriction adds a free design choice that weakens a negative.

**Closest priors.**

- [What Attention Recalls and Recurrence Controls in Hybrid Language Models](https://arxiv.org/abs/2609.04434), 2026-09-03: Pre-answers phase 0 on Qwen3.5-4B and shows the state carries output language.
- [How Linear Attention Remembers](https://arxiv.org/abs/2609.33093), 2026-09-27: Write-level causal analysis; in pure GDN the state does carry the fact, monolingually.
- [Balancing Memory Pathways: Analyzing and Improving Memory Utilization in Hybrid LMs](https://arxiv.org/abs/2610.06750), 2026-10-05: Recurrent-path auxiliary loss (QA 34.6 to 38.5) with no multilingual content; the required baseline.
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28: Hybrid cross-lingual deficit and a layer-ordering fix; no state supervision.

**Citable anchors.**

- [What Attention Recalls and Recurrence Controls in Hybrid Language Models (Afendulev et al.)](https://arxiv.org/abs/2609.04434), 2026-09-03.
  - Role: motivates; pre-answers phase 0.
  - Status: VERIFIED (full text): Table 1 KV retrieve '1.00 0.00 0.89'; 'Lang. follow 0.97 0.70 0.01'.
- [How Linear Attention Remembers](https://arxiv.org/abs/2609.33093), 2026-09-27.
  - Role: closest prior.
  - Status: VERIFIED (full text): recurrent 0.2-3.6% vs KV 96-100% on Qwen/Qwen3.5-4B-Base @adebbbc0 (D22 receipts @1001bb4d).
- [Balancing Memory Pathways](https://arxiv.org/abs/2610.06750), 2026-10-05.
  - Role: baseline.
  - Status: VERIFIED: exists; code repo created 2026-10-04.
- [Multilinguality in Hybrid Attention LLMs](https://arxiv.org/abs/2609.35378), 2026-09-28.
  - Role: motivates.
  - Status: VERIFIED (full text): 'Qwen3.5 has less cross-lingual alignment in 10/13 languages'.
- [kirillTerra/split-prefill (MIT)](https://github.com/kirillTerra/split-prefill), 2026-08-31.
  - Role: confirmatory instrument (folded into P-GSM).
  - Status: VERIFIED: repo exists.

**First experiment (2.5 GPU-h).** G1 floor gate only (~2.5 GPU-h including a step-overhead probe and reserve; estimate): train the D22 A0 GDN hybrid (no equivariance loss) with SWA-512 replacing full attention on the measured 134M config at 200M and 1B tokens (75% mono, 20% prefix-sharing bitext, 5% recall curriculum), and read beyond-window (more than 512 tokens back) TP-MQAR-v2 exact match at N = 8; in the same job, time ~200 steps of the A1 write extraction and one 2610.06750-style restricted-attention auxiliary pass to price the full grid. The ~1 GPU-h translated split-prefill confirmation on frozen Qwen3.5-4B (predicted ~0) belongs to P-GSM, not here. Prerequisites: the SWA-512 model definition, TP-MQAR-v2 built from FLORES+, and a rewritten contract.

**Kill criteria.** G1 passes only with monolingual beyond-window exact match of at least 60% and cross-lingual at least 15% at 1B tokens; if the A0 model fails, defer phase 1 and port the comparison to the 2610.06750 LoRA setting rather than scaling the toy model. If the P-GSM confirmation unexpectedly shows the frozen state recovering more than 10 points on cross-lingual keys, write that up instead. The full grid (~27 GPU-h, 18 runs) needs a preregistered subspace or guardrail design and the gauntlet.

**Relation to the existing program.** D22 backfill. Phase 0 is pre-answered and absorbed by P-GSM; sweep stop item 3 already halts its Qwen frozen screen; only the small-model G1 gate survives.

---

## 17. Discard-and-rebuild attention for bounded GPU memory

`C6-switchable-attention-recovery`. Origin: Codex ranking doc #5. **Recommendation: DROP.**

Scores (3-judge means): significance 3, correctness 3.33, citability 7.67, novelty residual 3, feasibility 6.67.

**Corrected question.** If only a sliding window and a recurrent state stay on the GPU and the rest of the history is kept off-GPU, up to what rate of 'full attention needed' calls does rebuilding the past KV on demand (host fetch, re-prefill or hidden-state restore) still beat keeping the full KV cache resident, in decode speed and throughput per GB, at 32K-128K context? Exact rebuild matches full-cache quality by construction, so only the cost side is open.

**What was wrong with the original.** (1) History that is truly discarded cannot be recovered; recovery requires an off-GPU copy (exact retrieval 'collapses to zero through recurrence', 2609.04434). (2) Oryx keeps both the KV cache and the state, uses static switching and runs at 2K. (3) LLaDA-Hybrid has no recovery or switching. (4) Learned local/global switching methods reduce compute, not memory (ODA keeps 'the complete historical KV cache'; Switch Attention shares one KV cache). (5) Rebuild cost is already charged in systems work (HCache, ArkVale, ShadowKV, QEvict, WakeKV, 2608.30647). (6) A short-context study cannot show a benefit (ODA is 13.1% slower at 4K and gains 2.65x only at 512K). Fails the correctness gate (lowest judge correctness 3): with exact rebuild, quality equals ODA by construction, and ODA's realized Full-call rates on RULER at 32K are 33-69%, so a full-history PCIe rebuild (roughly 60x slower than an HBM read, reviewer estimate, unmeasured on this node) makes the cost result derivable on paper.

**Novelty.** NARROWED. The bounded-memory regime is unclaimed by the learned-switching papers, but its cost side duplicates HCache, ArkVale, ShadowKV, QEvict and WakeKV, and a positive version (sparse rebuild) is their territory.

**Why it matters.** At most a systems note. Reframed as 'what call rate and rebuild sparsity make bounded-resident on-demand attention Pareto-positive', it would need a training contribution (call-rate-aware or page-selective recall), which is not the question posed.

**Closest priors.**

- [On-Demand Attention: Language Models Know When to Recall (ODA)](https://arxiv.org/abs/2609.20734), 2026-09-17: Learned recall trigger with cost accounting, but keeps the full KV cache.
- [Learning When to Attend: Conditional Memory Access for Long-Context LLMs (L2A)](https://arxiv.org/abs/2603.17484), 2026-03-18: Skips global attention for ~80% of tokens within 3% quality; full KV retained.
- [Fast State Restoration in LLM Serving with HCache](https://arxiv.org/abs/2410.05004), 2024-10: Already compares recompute, KV offload and hidden-state restore on cost.
- [WakeKV: Reactive, Reversible KV Residency for Heads That Change Their Minds](https://arxiv.org/abs/2610.02713), 2026-10-02: Recoverable CPU reservoir for KV without a learned trigger.

**Citable anchors.**

- [On-Demand Attention (ODA)](https://arxiv.org/abs/2609.20734), 2026-09.
  - Role: closest prior; quality ceiling.
  - Status: VERIFIED (full text): 'retaining the complete historical KV cache'; Table 1 Full-call rates 32.6-68.9% at 32K; 'At 4K, however, ODA remains 13.1% slower'; code not released.
- [Learning When to Attend (L2A)](https://arxiv.org/abs/2603.17484), 2026-03.
  - Role: baseline.
  - Status: VERIFIED: 'within 3% while skipping Global Attention for ~80% of tokens'.
- [Fast State Restoration in LLM Serving with HCache](https://arxiv.org/abs/2410.05004), 2024-10.
  - Role: closest prior for rebuild cost.
  - Status: VERIFIED: compares recomputation, KV offload and hidden-state restore.
- [WakeKV](https://arxiv.org/abs/2610.02713), 2026-10.
  - Role: baseline (recoverable eviction).
  - Status: VERIFIED: 'recoverable CPU reservoir'; single author.
- [QEvict: Recoverable Quantized KV Eviction for Attention-Drift-Robust Long-Context Decoding](https://arxiv.org/abs/2608.05326), 2026-08.
  - Role: baseline.
  - Status: VERIFIED: 'replaces binary retain-or-delete eviction with recoverable eviction'.
- [Sliding-Window Beats Linear Attention](https://arxiv.org/abs/2608.28444), 2026-08.
  - Role: baseline and instrument.
  - Status: VERIFIED: SWA '2 to 10 times higher' on NIAH/BABILong than retrofitted linear attention.

**First experiment (8 GPU-h).** Cost-only break-even test, no training (~8 GPU-h, estimate): measure pinned host-to-device bandwidth, the memlock limit without root and 8-GPU copy contention; on Qwen3-1.7B at 32K and 128K implement three layer-streamed rebuild paths (host-KV fetch, re-prefill, HCache-style restore); sweep a prescribed Full-call rate over {1, 5, 12.5, 33, 50, 65%} x batch {1, 8, 32}; record decode tok/s, peak resident memory, rebuild FLOPs and host-to-device bytes against full-resident decode and SWA(2,048) plus 4 sinks; run RULER 32K for Full vs SWA plus sinks as the two quality endpoints.

**Kill criteria.** If the break-even call rate is below 5% at 32K, the exact-rebuild version is dead for retrieval-heavy RULER (ODA's realized rate is 33-69%); redirect to page-selective rebuild or call-rate-aware recall training, or drop. Only if break-even exceeds ~30% at 128K under batching is the question live.

**Relation to the existing program.** Orthogonal to the program and conflicts with sweep stop item 15 (no mid-sequence KV-eviction engineering for hybrid CUAs). Adjacent to the D19-D22 architecture backfill; its cost side duplicates existing KV-serving systems work.

---

## 18. Relay interface, guide and history lab

`E9-relay-interface-context-lab`. Origin: existing: cua-slack Relay Lab. **Recommendation: DROP.**

Scores (3-judge means): significance 3, correctness 4.67, citability 8.33, novelty residual 2, feasibility 4.67.

**Corrected question.** In one instrumented Slack-like app with a fixed non-LLM state grader and a pinned local model, does supplying a site guide (llms.txt plus an interaction guide) or full history change the gap between screenshot, accessibility-tree and API interfaces, on held-out tasks long enough (10+ steps, with a fact revealed early and needed late) for history to matter? The interface main effects are already published and are not claimed.

**What was wrong with the original.** Eight premises failed. Hosted model aliases are not immutable, so 'same model' cannot be held fixed. The API condition changes action granularity and the a11y tree is not information-matched to pixels, so the interface factor is not a pure observation ablation. Four-step tasks cannot show history effects, and only recent-4 history was run. Cost is a local estimate and latency is confounded by harness overhead. Evidence is thin: the live matrices stopped at 3/9 and 4/9 cells, $0.031 total on one task, one seed. Fixture seeds vary identifiers, not reasoning structure (six templates, one app). The lab describes itself as an engineering harness, not a research mechanism. It uses no H100. Fails the correctness gate (lowest judge correctness 3).

**Novelty.** NARROWED. Affora (2609.19125), ASIL (2608.26991), Tool Illusion (2604.03465), MCPWorld (2506.07672), Beyond Browsing (2410.16464), WebPageBench (2609.35026) and OSWorld's observation ablation own the main effects. Residual: interface x guide and interface x history interactions in the messaging domain under matched information scope, underpowered with today's templates.

**Why it matters.** A workshop or HCI short paper at best; the likely result is a null interaction ('the guide is a constant offset, so build the API'). Effective sample size is task families, not seeds.

**Closest priors.**

- [Affora: A Design System for Agent-Friendly Interfaces](https://arxiv.org/abs/2609.19125), 2026-09-16: Same-model Vision vs DOM/AX channels plus an instruction-file condition (+23 pp); no history factor or latency.
- [ASIL: Replacing Screenshot-and-Click with Structured State and Semantic Actions](https://arxiv.org/abs/2608.26991), 2026-08-27: Owns the pixels vs structured vs API main effect on desktop apps.
- [WebPageBench: Event-Level Verification and Controlled UI-Variant Generation for Web Agents](https://arxiv.org/abs/2609.35026), 2026-09-28: Nearly identical methodology: self-hosted mock sites, judge-free event grading, many harness configurations.
- [MCPWorld: A Unified Benchmarking Testbed for API, GUI, and Hybrid Computer Use Agents](https://arxiv.org/abs/2506.07672), 2025-06-09: API vs GUI vs hybrid on the same white-box-verified tasks.

**Citable anchors.**

- [Affora: A Design System for Agent-Friendly Interfaces](https://arxiv.org/abs/2609.19125), 2026-09-16.
  - Role: closest prior.
  - Status: VERIFIED (full text): 'Instruction file (agent.md) 60/60 (100%)' vs 'Baseline 46/60 (77%)'.
- [ASIL: Replacing Screenshot-and-Click with Structured State and Semantic Actions](https://arxiv.org/abs/2608.26991), 2026-08-27.
  - Role: closest prior on the interface main effect.
  - Status: VERIFIED (abstract): above 80 strict success vs '6.6 and 26.6' under screenshot-and-click. CITATION AUDIT (FIX): date corrected from 2026-08-26 to 2026-08-27 (v1 submission).
- [The Tool Illusion: Rethinking Tool Use in Web Agents](https://arxiv.org/abs/2604.03465), 2026-04 (COLM 2026).
  - Role: motivates cost accounting.
  - Status: VERIFIED: 'Published as a conference paper at COLM 2026'; 'Tool entails hidden tax'.
- [MCPWorld](https://arxiv.org/abs/2506.07672), 2025-06-09.
  - Role: baseline.
  - Status: VERIFIED: exists.
- [Beyond Browsing: API-Based Web Agents](https://arxiv.org/abs/2410.16464), 2024-10 (v3 2025-06-16).
  - Role: baseline.
  - Status: VERIFIED: hybrid agents '24.0% absolute improvement over web browsing alone'.
- [WebPageBench](https://arxiv.org/abs/2609.35026), 2026-09-28.
  - Role: methodology prior.
  - Status: VERIFIED: exists.

**First experiment (6 GPU-h).** Stage 0 (no GPU, no paid API): write 3-4 held-out long task families (10+ required steps, a fact revealed in steps 1-3 and needed after step 8), have the guide written by someone blind to them, add an oracle check that a scripted last-4-history policy fails unless it re-retrieves the fact, and build a viewport-scoped a11y gateway and a matched-retrieval API. Stage 1 (~6 GPU-h, estimate): one pinned local VLM on vLLM; {pixels, a11y-viewport, matched API} x {full, last-4 history} x guide = none on 4 families x 10 seeds x 2 repeats = 480 episodes, graded by state-contract-v1, with a family-first bootstrap.

**Kill criteria.** Stop if the paired full-minus-last-4 completion difference in a11y-viewport has a family-clustered bootstrap CI inside +/-10 pp: history does not matter for these tasks and the interaction is meaningless. Add the guide factor only on the interface pair with the largest history gap. Detecting a ~15 pp interaction needs at least 8 held-out families.

**Relation to the existing program.** Subsumed as a fixture: its interface main effects and Relay noise floor belong to S1 (WS1-A), and its Relay cells feed S2 and S3. Not merged with S1 or S2 because its residual (guide and history interactions) is not in either; Relay itself stays as the shared fixture.
