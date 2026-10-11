# Research Direction: R01 first step, where S1a's greedy rerun disagreement starts on the certified desktop stack (Stage A records census, run; Stage B request-level clock-by-serving factorial; Stage C open-loop replay)

**Status:** draft, gauntlet wave 1 synthesis (D73 i), written 2026-10-11 on the development Mac by the gauntlet's single owner from four independent discovery cells (frontier, kill-shot, cross-domain, asset); the blind critic, the refute-first triad and both reviewers have not run; the draft registration is `program/preregistrations/r01-rerun-noise-sources-v1.md` (new experiment id, DRAFT, not frozen, no ledger row); Stage A0 has run as an executable CPU pilot (orx run `83ee815a-426a-4b94-a93f-cc1277972d76`, `ORX_RESULT ... exit=0`); P0 and Stage B have registered caps of 4.22 cap-GPU-h (3.47 without conditional jobs), under the 8 GPU-h line, but under D24 and D70 they run only after Kevin's admission ruling whatever this gauntlet scores; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism, identification, contract and draft registration by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-11
**Coverage limits:** orx 0.2.2 (reports itself outdated against 0.2.18) over alphaXiv keyword and embedding search and OpenAlex, whose newest results are dated 2026-10-09 to 2026-10-10, so papers posted on 2026-10-10 or 2026-10-11 are probably missed; 103 counted orx discover queries by the four cells (frontier 59, kill-shot 19, cross-domain 19, asset 6) with returned ids in `query-log.json`; OpenReview api2 term searches (11, frontier; abstracts only, per-note pages and PDFs behind a browser challenge not bypassed, so cELldjX2oq, qXJ0EkHo2X, ezVIHPgaiG and I0GKaJXdCh are judged from abstracts); 6 web searches and 1 arXiv title search (frontier); ACL Anthology only through the renewal dossier's regex queries 18-22 over the 2026 bibliography and two site-restricted web searches; arXiv API version checks through the host relay (frontier). Not searched: Semantic Scholar or Google Scholar citation graphs (forward citers of 2604.17849, cELldjX2oq and 2609.04748), GitHub code search (harness-side clock masking in OSWorld forks), the vLLM issue tracker, patents, live X, Reddit and Chinese-language venues. PRISMA-style for the cells: 773 ids as the cells reported them (the frontier cell listed at most six per query), 560 unique, screened by title; 33 papers read beyond the title with `orx paper` (full text or report), plus the abstracts or metadata of 13 more (6 OpenReview abstracts, 7 OpenAlex records); 0 direct priors.
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-11-r01-rerun-noise-sources/bundle.json

The budgets are cumulative for this gauntlet. The GPU budget (0.3 GPU-h) is for the
open-weight reviewer's lane job only; the doctor reads budgets as integers, so it parses it as 0
and flags it (left as declared). Queries: counted as orx discover queries (the S2
precedent), the cells used 103 of 150, leaving 47 with the refuters' reserve of 30 intact; the
synthesis ran no new search. If OpenReview, web and arXiv-title searches are counted too, the
cells used 121 (123 with two failed OpenReview calls), leaving 27-29: the reserve of 30 is then
breached by 1-3, and the recorder should account for it before the triad starts. The novelty
verdict field uses the doctor's vocabulary; the merged kill-shot verdict is **NARROWED**, not
OCCUPIED (all three discovery cells agree).

## Scope

R01's first step only: Stage A (A0, the records-only census of S1a, run; A1, a region census
from fresh step-1 captures on the CPU lane), Stage C (open-loop replay of S1a's recorded
actions on the CPU lane, 0 GPU-h, isolating the environment) and Stage B (identical-input
replay through the serving engine, isolating serving numerics, crossed with clock-only
observation swaps). No closed-loop agent episode is part of this step. A closed-loop Stage D
(clock mask x verified-deterministic serving) is sketched in the registration's section 17 and
needs its own registration.

## Changes from the renewal slate's R01, and why

| # | Slate (renewal dossier, R01) | This proposal | Driven by |
|---:|---|---|---|
| 1 | Split D_w into three additive parts | Per-source **sufficiency hazards** at the step where divergence starts, their interaction, and a step-kick model that predicts D_w under each removal; additive shares declared unidentified | Kill-shot cell (overdetermination); cross-domain cell (Owen 2014: a closed index read alone misattributes; competing risks); A0 natural experiment |
| 2 | Closed-loop A0/A1 (clock live against masked, live serving, R = 3, 678 episodes, about 2.2 cap-GPU-h) | Dropped from this step; the request-level factorial measures the same "is the clock sufficient / necessary" question on fixed requests | Simulation CL: under no masking effect (the records' prediction) CLOCK_DOMINANT fires 0.002, the slate's NOT_CLOCK 0.218 by chance |
| 3 | NOT_CLOCK: one-sided upper bound of the D_w reduction below 2 pp | CLOCK_INERT at the request level: h_c upper bound below 0.05 (text) and 0.01 (IR); reachable (0.99 at a true 0.01) | Dossier defect 1; all three judges |
| 4 | Stage A pixel diff of S1a's step-1 screenshots; Stage B replays S1a's recorded requests | A0 on the hashes S1a kept (run); A1 captures fresh images; Stage B rebuilds requests from Stage C's captures and S1a's replies, checked against S1a's prompt-id digests | O1 (S1a kept hashes only) |
| 5 | Gate: at least 80% of step-1 pairs differ only in the clock box | A1's census reads MULTI_REGION / CLOCK_ONLY on Wilson bounds; MULTI_REGION adds a blink-off condition and an other-region swap instead of stopping | A0: 10 of 25 clearly same-minute pairs differ (0.40, 0.23-0.59), all in LibreOffice and GIMP |
| 6 | Stage B: 600 requests x 4 under S1a's flags "with matched filler load"; 300 x 2 at batch 1; 300 clock-swapped; 0.3-0.5 GPU-h | 320 requests in four engine configurations (a 2x2 of batch by cache), in-order streams with randomized load, cache resets, a P0 bitwise self-test with a batch-invariant fallback, and the interaction cell; 4.22 cap-GPU-h with conditional jobs | Kill-shot (identical input is not identical cache state); cross-domain (Vosti's four variation categories, Thinking Machines on batch size); asset (batch-1 decode dominates cost) |
| 7 | Open-loop replay once, verdict only | Twice per episode, two frames per step, masked frame identity, normalized state digests; zero-event rule for ENV_BOUNDED | Cross-domain (lockstep checksums, reproducible-builds timestamps, Playwright two-frame rule); A0: 162 of 227 identical-IR pairs differ in checker-input digests |
| 8 | Motivated by D69's 20-33% and 3-4% | D72 (ii): rerun noise 21-27%, task-by-harness about 4% at 9B and at most 1% at 4B; the power payoff is withdrawn (P-K6) | D72; kill-shot point 5; cross-domain G-theory |
| 9 | Cap 4 under an unstated rule | The design study's realized-cost rule adopted explicitly, with per-job arithmetic | Asset (S1a's c_proj would put the slate's Stage C alone at 7.64) |

## Merged discovery cells, by mechanism

**Serving numerics.** All cells agree that identical-input replay with a replica floor, cache
on/off at batch 1 and a batch-invariant confirmation is published methodology for text models
(2609.04748, 2606.15621, 2605.27763; cELldjX2oq in agent benchmarks). The kill-shot and
cross-domain cells independently found 27 natural identical-request replays in S1a's logs;
this synthesis replicated them from hash-checked copies (A0): reply text differs on 16 of 27
(0.59, 0.41-0.75), IR on 2 of 27. Frontier and cross-domain facts that shaped the design: token
flips under batching occur on 0.3-1.3% of decode steps (2605.30218), so text identity can
saturate and IR identity is registered beside it; vLLM v0.31.0's batch-invariance tested list
names no Qwen3.5 model (first-party docs), and Vosti (2609.38981) shows vLLM's batch-invariant
mode bitwise-exact on Llama3.1-8B but failing on Gemma3-4B under chunked prefill (0 of 90), so
a deterministic reference must be tested (P0) rather than assumed; on Gated DeltaNet hybrids a
prefix-cache hit resumes from a block-aligned recurrent-state checkpoint (2608.30310), a numeric
channel attention-only studies do not cover, hence the batch-by-cache 2x2.

**Observation-time noise (clock and other regions).** Clock control is established practice
(AndroidWorld resets the device clock, 2405.14573; frozen-clock web mirrors, 2607.17136;
Playwright masks regions and hides the caret), so the mask is not a contribution; only the
measured effect is. A0 shows the clock is not the only varying region (10 of 25 clearly
same-minute pairs differ, concentrated in LibreOffice and GIMP), consistent with caret blink
phase; UI-flakiness studies rank rendering and animation timing far above wall-clock time
(2103.02669: async wait 106 of 235, time 1 of 235). The text analog (2609.36931) raises the prior
that a clock perturbs replies.

**Environment.** Record-and-replay of agent runs is published (2609.20625) and open-loop replay
drops closed-loop adaptation (2608.08239), so Stage C measures environment noise given fixed
actions, not the environment's effect through observations. A0's natural replay (0 of 227
identical-IR pairs discordant) bounds it on a selected subset; Stage C covers the unselected
population (long, failing episodes) and the per-step frame identity the frozen-regime
prediction needs.

**Identification.** The kill-shot cell's strongest argument, confirmed by A0 and by the
cross-domain cell's sensitivity-analysis reading: the sources overdetermine divergence, so a
mask under live serving is predicted null and its NOT_CLOCK reading would misattribute. The
repair crosses observation perturbation with serving configuration on fixed requests, which
measures each source's sufficiency directly, and moves the closed-loop consequence to a
pre-stated prediction (P8).

**Payoff.** Kill-shot and cross-domain cells agree that deterministic serving plus a mask
freezes rerun noise rather than removing it; the simulation (K6) confirms a width ratio of
1.002 at one rerun per arm and 2.00 at four. The payoff is attribution, the portability of
floors and evaluation design, not power.

**Cost.** The asset cell's pricing (batch-1 decode dominates; the design study's cap rule) is
adopted; the caps in this proposal are recomputed from S1a's per-step records (`caps-r01.json`).

## Claim and Research Question

**Question.** On S1a's certified desktop stack (Qwen3.5-4B, H-OSW-fixed, greedy decoding,
thinking passed back, 15 steps, V = 20, vLLM v0.31.0 with prefix caching, guest clock live),
which perturbation sources are individually sufficient to change a step's greedy reply, how
large is each per-step hazard, do they interact, and how much does the environment change the
screen or the verdict given fixed actions?

**Variables.** Serving configuration (batch 1 or loaded; prefix cache on or off), observation
perturbation (none, clock-box swap, clock-box mask, other-region swap), and, in replay, the
guest's cursor blink (default or off). Outcomes: reply-text identity and parsed-IR identity per
request; frame identity per step and verdict identity per episode in replay.

**Claim scope:** `systems-pipeline`. The claim is about an evaluation stack's noise sources
on this host and configuration, not about any model's capability and not an architecture
claim. Every number is "not externally anchored".

## Strategic Fit and Why Now

- The program is "checker adequacy and calibrated measurement for verifiable machine work".
  S1a measured the rerun floor (D_w 11-12% at 4B) and the variance split (D72 (ii): rerun noise
  21-27% of outcome variance, task-by-harness at most 1% at 4B), but not where the floor comes
  from. D73 recommends R01 as the renewal slate's lead.
- The answer decides how any OSWorld-style study should treat greedy reruns. If the sources are
  redundant (the records' prediction), a greedy floor is a property of policy and tasks wherever
  any perturbation is active, reruns behave as samples, and deterministic serving would freeze
  one draw per task (P-K6); if one source dominates, removing it freezes trajectories and every
  floor measured with it live is a property of that nuisance.
- The question is active elsewhere in text agents: cELldjX2oq (ICLR 2027 submission, 2026-09-18)
  localizes first divergence in tau2-bench and ALFWorld; TRACE (2610.11678, 2026-10-08) and
  2610.01618 (2026-10-01) report large rerun variance without attribution. No pixel-agent
  attribution was found. The scoop window is open but narrowing.
- S1a's records already exist and Stage A0 is done, so the first step costs at most 4.22
  cap-GPU-h, with Stage C on CPU.

## Primary-Source Evidence

Claim registry (full: `evidence/.../doctors/citation.json`). Read levels: F = full text read
with `orx paper --full` by a cell; A = abstract or report only; R = repository; 1P = first-party.

| id | Claim | Source | Date | Read |
|---|---|---|---|---|
| C01 | Temperature 0 plus batch-invariant inference on OSWorld: Qwen b − c = −20, OpenCUA +20, UI-TARS-1.5 +19; Pass^1 to Pass^3 drops persist; perturbation sets bundle timezone with wallpaper, cursor, dock and icon theme; no clock intervention, identical-input test or open-loop replay | https://arxiv.org/abs/2604.17849 | 2026-04-20 (v1) | F |
| C02 | ARR version decomposes the reliability gap into stochasticity, ambiguity and planning variability | https://openreview.net/forum?id=ezVIHPgaiG | 2026-05-26 | A |
| C03 | First-divergence audit over replicated interactions with identical preceding recorded histories: 100 tau2-bench tasks, five greedy vLLM replicates, transcripts diverge on all, rewards on 20, first discrepancy in the simulated user on 83; cache-off and serving-configuration comparisons; ALFWorld cache resets restore agreement | https://openreview.net/forum?id=cELldjX2oq | 2026-09-18 | A |
| C04 | Batch 1, cache off: 0 of 800 episodes differ; enabling the prefix cache changes 36.2% of trajectories at 16-bit, 75.0% at 4-bit; attention-only models | https://arxiv.org/abs/2609.04748 | 2026-09-04 | F |
| C05 | Replica-floor design; batch-invariant kernels make all passes identical | https://arxiv.org/abs/2606.15621 | 2026-06-14 | F |
| C06 | Paired batch-condition protocol: 22 of 55 flips, 0 of 55 with batch-invariant kernels | https://arxiv.org/abs/2605.27763 | 2026-05-26 | F |
| C07 | Hidden date injection moves scores up to 6% (MCQA), 14% (math), more than batch size or precision | https://arxiv.org/abs/2609.36931 | 2026-09-29 | F |
| C08 | AndroidWorld resets the device clock per task; fixed-seed reruns still vary | https://arxiv.org/abs/2405.14573 | 2024-05-23 | F |
| C09 | Computer-use training and evaluation on snapshot-resettable mirrors with a frozen clock | https://arxiv.org/abs/2607.17136 | 2026-07-19 | F |
| C10 | Vosti: vLLM batch-invariant mode bitwise-exact on Llama3.1-8B, fails on Gemma3-4B (chunked prefill 0 of 90; prefix reuse 11 of 14 with FA3) | https://arxiv.org/abs/2609.38981 | 2026-09-30 | F |
| C11 | Batch-induced token flips on 0.3-1.3% of decode steps; low top-1/top-2 margins predict them | https://arxiv.org/abs/2605.30218 | 2026-05-28 | F |
| C12 | Hybrid prefix caching stores recurrent-state checkpoints; hits resume only at boundaries | https://arxiv.org/abs/2608.30310 | 2026-08-31 | A |
| C13 | Record-and-replay of agent runs at non-deterministic boundaries (Chronicle) | https://arxiv.org/abs/2609.20625 | 2026-09-17 | F |
| C14 | Open-loop replay scores the wrong world: 3% of replayed states stay valid after a swap; 0 flips in 359 same-model control forks | https://arxiv.org/abs/2608.08239 | 2026-08-08 | A |
| C15 | UI flaky tests: async wait 106 of 235, time 1 of 235 | https://arxiv.org/abs/2103.02669 | 2021-03-03 | F |
| C16 | TRACE: identical reruns flip 15-36% of tau2-bench outcomes; cause not located | https://arxiv.org/abs/2610.11678 | 2026-10-08 | F |
| C17 | Noise-floor audit: temperature-0 ever-flip 0.7-2.7%; perturbation SDs 11-58x rerun SDs | https://arxiv.org/abs/2608.22331 | 2026-08-23 | F |
| C18 | About 54% of outcome variance from repeating a configuration (coding agents) | https://arxiv.org/abs/2610.01618 | 2026-10-01 | F |
| C19 | SWE-bench pass@1 SD above 1.5 pp at temperature 0; serving nondeterminism named, not decomposed | https://arxiv.org/abs/2602.07150 | 2026-02-06 (v3 2026-03-25) | F |
| C20 | Prediction noise against data noise by the law of total variance | https://arxiv.org/abs/2512.21326 | 2025-12-24 (v2) | F |
| C21 | Cumulative disagreement = first-mismatch contribution + post-divergence exposure x mismatch rate | https://arxiv.org/abs/2609.16617 | 2026-09-15 | A |
| C22 | Up to 9% accuracy variation under bf16 greedy decoding across GPU count, type and batch size; Div_Index | https://arxiv.org/abs/2506.09501 | 2025-06 (v2) | F |
| C23 | Clinical text agents: twelve greedy noise-floor cells returned twenty identical completions | https://arxiv.org/abs/2609.13582 | 2026-09-11 | F |
| C24 | Request order changes answers under selective KV reuse (69.0% and 26.1%) | https://arxiv.org/abs/2610.05833 | 2026-10-05 | F |
| C25 | Stage-wise fixed widths give byte-identical VLA actions across batch contexts | https://openreview.net/forum?id=qXJ0EkHo2X | 2026-09-10 | A |
| C26 | Single-run leaderboards admit no unbiased estimator of rerun variance | https://openreview.net/forum?id=I0GKaJXdCh | 2026-08-04 | A |
| C27 | Batch size, not concurrency, drives endpoint nondeterminism; 80 unique of 1,000 completions, 1 with batch-invariant kernels | https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ | 2025-09-10 | 1P |
| C28 | vLLM batch-invariance tested list has Qwen3-Next and Qwen3-VL, not Qwen3.5; silent on prefix caching and chunked prefill | https://docs.vllm.ai/en/v0.31.0/features/batch_invariance/ | accessed 2026-10-11 | 1P |
| C29 | Sobol' closed and total indices bracket the Shapley value of a variable | https://doi.org/10.1137/130936233 | 2014 | A |
| C30 | Qwen3.5-4B weights are Apache-2.0 | https://huggingface.co/Qwen/Qwen3.5-4B | accessed 2026-10-11 | 1P |
| R1 | S1a: 1,808 episodes, 0 losses; D_w 4B 11.1% on 113 tasks; first divergence labels; prefix-cache hit share 0.855-0.858; realized cost 0.0025-0.0027 GPU-h per episode | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` | 2026-10-10 | R |
| R2 | D72 (ii) corrected variance shares | `program/decisions.md` D72 | 2026-10-11 | R |
| R3 | A0 census (every number in the registration's section 2.1) | `program/evidence/2026-10-11/r01-stage-a0/census.json`, orx run `83ee815a` | 2026-10-11 | R |
| R4 | S1a engine argv (`--max-num-seqs 256`, `--max-num-batched-tokens 8192`, `--enable-prefix-caching`, `--seed 42`) and sampling (temperature 0, top-p 0.9) | `program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json` | 2026-10-09 | R |

## Closest Prior Work

1. **cELldjX2oq, "The Evaluator Also Varies: Localizing Nondeterminism in Interactive Agent
   Benchmarks"** (ICLR 2027 submission). The closest by mechanism and the highest
   blind-discrimination risk: it asks where replicated greedy runs first diverge (agent,
   simulated user, environment, serving), with identical preceding recorded histories and
   cache-off comparisons. Text environments only (tau2-bench, ALFWorld); judged from its
   abstract (full text behind a browser challenge: UNVERIFIABLE_ACCESS). Delta: R01 works on
   pixel observations with a live rendered clock; it crosses an observation perturbation
   (clock swap, mask, other-region swap) with serving configuration on fixed requests, so each
   source's sufficiency and their interaction are estimated rather than the first discrepancy
   located; it adds open-loop action replay in reset VMs; and its serving channels are those of
   a Gated DeltaNet hybrid VLM.
2. **2604.17849, "On the Reliability of Computer Use Agents"** (and its ARR version
   ezVIHPgaiG). The closest by domain: OSWorld reruns with a deterministic-decoding arm and
   cosmetic perturbation bundles (timezone among them). It has no clock intervention, no
   identical-input serving test, no open-loop replay and no source attribution of rerun
   disagreement; its timezone change is bundled, so a clock effect cannot be isolated from it.
3. **2609.04748, "Same Request, Different Answer"**: the template for B0 and B5 (batch 1, cache
   on/off) on attention-only text models; R01 adds the hybrid VLM, image-heavy requests,
   loaded serving and the observation factor.
4. **2606.15621 and 2605.27763**: replica floors and paired batch-condition tests with
   batch-invariant confirmations; R01 uses the same logic (B0b, P0/P0').
5. **2405.14573, 2607.17136**: clock reset and frozen clocks as reproducibility measures in GUI
   and web benchmarks; neither measures the clock's effect on rerun disagreement.
6. **2609.36931**: the date's effect on text-model scores; R01's clock is rendered pixels in a
   closed loop.
7. **2609.20625 (Chronicle) and 2608.08239 (Replay Gap)**: record-and-replay of agent runs and
   its limits; Stage C applies record-and-replay and inherits the limit (it measures fixed
   actions, not adaptation).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Identical-input replay with a replica floor and cache on/off at batch 1 (B0, B5, P0) | 2609.04748; 2606.15621; 2605.27763 | the method | setting only: a Gated DeltaNet hybrid VLM with up to 8 images per request, at S1a-like load; no method claim | high that the method is occupied |
| Batch-by-cache 2x2 of serving channels (B0, B5, B6, B1) | 2609.04748 (cache); 2609.38981 (four variation categories); Thinking Machines (batch size, first-party) | channel tests exist separately | the crossed 2x2 on one hybrid VLM's agent requests | medium |
| Clock as a controlled factor on fixed requests (B2 swap, B4 mask) | 2405.14573 (clock reset); 2607.17136 (frozen clock); 2604.17849 (timezone in a bundle); Playwright masks | controlling the clock | the per-step sufficiency hazard of the rendered clock on greedy replies and actions, measured; no prior found that measures it | medium |
| Observation perturbation x serving configuration factorial on fixed requests (B2 x B3 against B0 x B1), read as sufficiency hazards with an interaction | cELldjX2oq (first-divergence localization, identical histories, text); Owen 2014 (closed and total indices) | attributing divergence to components | a crossed factorial that identifies each source's sufficiency under redundancy instead of locating the first discrepancy; pixel observations | medium (cELldjX2oq judged from its abstract) |
| Open-loop replay of recorded actions in reset VMs, twice, with two frames per step | 2609.20625; Lam et al. FSE 2017 (Android record and replay); 2608.08239 | record and replay | applied to desktop agent verdicts and per-step frame identity; no method claim | high that the method is occupied |
| Records-only census of natural identical-input replays in an existing study's hashed logs (A0) | 2602.07150 (temperature-0 variance, no decomposition); cELldjX2oq | rerun analysis | a natural experiment from S1a's hashes; descriptive | medium |
| Step-kick model predicting D_w under each removal | 2609.16617 (token-level first-mismatch plus exposure identity) | the decomposition identity | step-level, for agent trajectories, with q measured | medium |

Novelty wording: No direct prior art found through 2026-10-11 under the coverage in the header
(orx discover keyword, embedding and openalex queries listed with returned ids in the bundle's
`query-log.json`, including title-phrase queries for "On the Reliability of Computer Use
Agents", "The Evaluator Also Varies", "Same Request, Different Answer", "Dating the Model",
"Defeating Nondeterminism in LLM Inference", "Greedy Decoding Is Not Precision-Invariant",
"On Randomness in Agentic Evals", "Measuring all the noises of LLM Evals", "Marconi" and
"Engineering record and replay for deployability"; OpenReview api2 term searches; the
dossier's ACL Anthology regex queries) that splits a pixel-observation desktop agent's greedy
rerun disagreement into serving, rendered-clock and environment sources. The serving-replay,
clock-control and record-and-replay methods are each occupied; the residual is their crossed
measurement on this kind of agent. Never "completely novel".

## Mechanism and Falsifiable Predictions

**Mechanism (M).** Each request carries every earlier reply (thinking included) and screenshot,
so a first difference anywhere makes all later requests differ: divergence is absorbing, and
each step adds a kick hazard from serving numerics (batch composition; a hybrid model's
prefix-cache hit resuming from a block-aligned recurrent-state checkpoint), the clock's minute
digits, other time-varying regions (caret blink phase, animation) and the environment given
actions. If each source alone kicks often enough that nearly every pair diverges within a few
steps, the sources are redundant: removing one leaves D_w unchanged, and D_w ≈ (1 − N) q + e,
where N is the share of pairs that never diverge, q the verdict discordance of diverged pairs
and e the environment's verdict noise given actions. A0 supports the premise: identical step-1
inputs did not lower discordance (2 of 19 against 90 of 885), the reply text of identical
requests differed 16 of 27 times, and IR identity survives to step 3 in 34% of pairs.

**Predictions, each with a falsifier** (registration section 3.2):

- P1 SERVING_SUFFICIENT (h_s lower bound above 0.20); falsified by PARTIAL or INERT.
- P2 DET_OK (0 of 320 replica pairs differ at batch 1, cache off); falsified by NEAR or
  UNATTAINABLE.
- P3 CLOCK_SUFFICIENT (h_c lower bound above 0.20 under the deterministic reference);
  falsified by PARTIAL or INERT.
- P4 h_c(IR) ≥ h_s(IR); falsified if the paired upper bound of the difference is below 0.
- P5 MULTI_REGION in A1; falsified by CLOCK_ONLY or UNRESOLVED.
- P6 ENV_BOUNDED in Stage C (below 3%); falsified by ENV_MATERIAL or ENV_UNRESOLVED.
- P7 masked per-step frame identity below 0.95 by default, at least 0.95 with blink off;
  falsified if either half fails.
- P8 (for Stage D) masking alone under live serving moves D_w by less than 2 pp.
- P-K6 a frozen stack does not narrow a K = 113 two-arm contrast at one rerun per arm.

**Kill criteria, restated quantitatively** (the dossier's six; registration section 10):
K1 "not removable" if blink-off plus mask leaves cross-boot step-1 identity with a Wilson upper
bound below 0.90; K2 ENV_MATERIAL if the task-cluster lower bound of e_rr exceeds 2%; K3
DET_UNATTAINABLE if 7 or more of 320 replica pairs differ; K4 MASK_HEAVIER if h_m − h_c has a
paired lower bound above 0.10 (the ±5 pp success check moves to Stage D); K5 CLOCK_INERT if
h_c's upper bound is below 0.05 (text) and 0.01 (IR), which stops the pixel line; K6 registered
as prediction P-K6, not a kill. M is falsified if P1 and P3 both read INERT.

## Cheapest Decisive Pilot

- **Executed (CPU, 0 GPU-h): Stage A0.** The records-only census, as orx cpu-doctor node
  `ff110047` (branch `orx/r01-stage-a0-records-census`, commit `ca3cdbf`), run
  `83ee815a-426a-4b94-a93f-cc1277972d76`: `ORX_RECEIPT_SUMMARY {"cases": {"passed": 8,
  "total": 8}, "doctor": "r01-stage-a0", ... "status": "PASS"}`, `ORX_RESULT kind=cpu-doctor
  direction=r01-rerun-noise-sources exit=0`. Its receipt is byte-identical to the committed
  census (SHA-256 `5568bc7f...`). It replicated both scouts' natural-experiment numbers before
  any rule uses them and fixed the predictions.
- **Next, decisive for identification (GPU, 0.25 cap-GPU-h, after admission): P0.** 40 requests
  x 3 passes on the deterministic reference plus one pass without logprobs. It decides whether a
  bitwise reference exists for Qwen3.5 on vLLM v0.31.0 (with a batch-invariant fallback P0'),
  which is what separates the clock's sufficiency from engine noise, and it prices every Stage B
  job before it is submitted.
- **The single result that would kill the first step's value:** DET_UNATTAINABLE in both P0 and
  P0' (the clock's text-level effect is then not separable), or CLOCK_INERT with SERVING
  SUFFICIENT (the pixel line stops; the floor is serving-driven). Both are cheap to reach and
  both are reportable.

## Controls, Baselines, and Ablations

- **Replica floor** B0b for every request-level estimand, and the engine self-test P0/P0'.
- **Serving baselines:** S1a's exact argv (E-s1a) against the deterministic reference (E-det);
  the 2x2 ablation of batch (1 or loaded) by prefix cache (on or off) isolates the channel.
- **Observation ablations:** clock-box swap from a real later rendering of the same top bar; a
  constant-colour mask (separates "changed" from "blanked"); other-region swap (the frame 0.6 s
  later); blink-off condition in captures and replays.
- **Paired interaction cell:** B3 shares B1 pass 1's schedule.
- **Environment:** replay against replay (pure environment) and replay against the original
  (adds time of day, session and model latency).
- **Negative control:** the rebuilt requests' prompt-id digests must equal S1a's.
- **Positive control:** t0 against t0 + 61 s of one boot must differ inside the clock box for
  every task.
- No architecture claim, so no matched from-scratch arm is needed.

## Evaluation, Statistics, and Leakage Checks

- Request-level readings: episode-cluster percentile bootstrap (40 clusters, 2,000 resamples,
  seed 42); paired differences keep each request's pair. Operating characteristics by
  simulation (`power-r01.json`, seeds 42-44): text SUFFICIENT 0.82-0.94 at a true 0.30, 1.00 at
  0.40; INERT 0.99 at 0.01; IR SUFFICIENT 0.67-0.75 at 0.05, 0.98-0.99 at 0.08.
- DET: exact binomial (P(DET_OK) 0.73 at p = 0.001, 0.04 at 0.01; P(UNATTAINABLE) 0.85 at 0.03);
  a beta-binomial check shows a DET_OK bounds the per-request, not the per-episode, rate.
- Stage C: task-cluster bootstrap and an exact zero-event bound (2.6% at the task level);
  P(ENV_BOUNDED) 0.92 at e = 0.01; P(ENV_MATERIAL) 0.90 at e = 0.05 (0.51 if concentrated in a
  tenth of tasks).
- A1: exact binomial on 113 task pairs; P(MULTI_REGION) 0.76 at a true 0.30 and 0.998 at 0.40.
- The slate's dropped closed loop, simulated (CL), and the K6 prediction are in the same file.
- Missing data: complete case by request; more than 5% missing voids an arm's reading.
- Leakage: A0 was read to design the study and enters no rule (disclosed). The clock box and
  the normalization rules are committed before Stage C's analysis and Stage B's corpus build.
  No new outcome is seen before a freeze.
- Saturation risk: text identity can saturate under batching (C11), so the IR level is
  registered beside it and the first divergent token and its margin are recorded.

## Compute and Reproducibility

- **Image:** the engine base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  (vLLM v0.31.0 at `db9527a4`) with S1a's cu129 overlay (local image ID
  `sha256:10327c706dcf2a9bd06e2449908e37d4fa4e46e7030a85e66f30626a1bafecde`, built by
  `scripts/build_vllm_overlay_on_h100.sh` from source `4a59e87c`); model Qwen3.5-4B at
  `851bf6e8`, receipt `75ebfc53`. CPU lane: S1a's VM image `fe8d9a5e` and metric image
  `2006c1a9`.
- **Launch:** every GPU job is one manifest, `experiments/manifests/r01/p0.yaml`, `p0-bi.yaml`,
  `j1.yaml`, `j1o.yaml`, `j2.yaml`, `j3.yaml` and `j4.yaml` (none rendered yet), submitted only by
  `uv run python scripts/submit_docker_research_job.py experiments/manifests/r01/j1.yaml
  --dry-run`, then `--test-only`, then without a flag, which issues `sbatch --parsable
  --partition=research --gres=gpu:h100:1 ... infra/slurm/host-single-node/docker-research.sbatch`
  with `--signal=B:USR1@180` and the job's cap as `--time`. CPU-lane jobs use S1a's lane
  submitter (`scripts/submit_vm_campaign.py`), never a GRES.
- **Seeds:** seeds: [42, 43, 44] (corpus 42, probe 43, schedules 42-44, bootstraps 42; engine
  `--seed 42`).
- **GPU ceiling:** gpu_hours: 5 (registered caps total 4.22 cap-GPU-h with conditional jobs,
  3.47 without; per-job arithmetic in `caps-r01.json` under the design study's realized-cost
  rule, adopted explicitly; physical estimate 2.2 central, 2.9 high).
- **Checkpoints and resume:** replies are appended per (arm, request) with fsync; a fresh job
  resumes at the first missing item and the analysis is order-free, so a resumed job equals an
  uninterrupted one. Stage C replays are independent episodes with S1a's re-queue rule.
- **Artifacts:** the A0 doctor and test (`scripts/run_r01_stage_a0_doctor.py`,
  `tests/test_r01_stage_a0_doctor.py`), the digests and their derivation
  (`program/evidence/2026-10-11/r01-stage-a0/`), the simulation and caps scripts with outputs
  (bundle `compute/`). Screenshots and request bodies stay on the host run root with SHA-256
  lists committed.
- **Cost ceiling:** at most 4.22 cap-GPU-h plus the reviewer's 0.3; CPU lane about 68 VM-h
  (A1 13.8, C 43.4, C-blink 10.8 conditional).

## Safety, Data Rights, and Monitorability

- No training, no new downloads, no outward action; offline VMs on the certified lane; IR
  actions run only in VMs through the certified executor, as in S1a; no model-generated code
  runs on GPUs (D7).
- Licences: OSWorld tasks Apache-2.0 at `b138d348`; Qwen3.5-4B Apache-2.0 (C30); vLLM
  Apache-2.0. S1a's records are the program's own.
- Screenshots and request bodies render OSWorld task files with their own licences; they stay
  on the host, and the public repository receives hashes, counts and region rectangles only. The
  committed digest table holds 16-hex prefixes of digests, token counts and latencies, with no
  reply text, image or host name.
- The blink-off condition is a guest setting used in measurement captures and replays only; any
  closed-loop use needs a delta certification of D53's scope (decision for the owner).
- Host rule: one node; read-only `squeue` before each submission; no R01 job overlaps another
  workflow's job.
- Monitorability: the study reads replies and actions only; nothing in it trains or rewards the
  model.

## Negative-Result Value

- DET_UNATTAINABLE on Qwen3.5's hybrid layers in vLLM v0.31.0 (with and without the
  batch-invariant mode) is itself a useful engineering fact: the vLLM docs do not list Qwen3.5,
  and Vosti shows model-dependent failures.
- CLOCK_INERT with SERVING_SUFFICIENT says the floor is serving-driven, which makes floors
  depend on serving configuration and load, not on the desktop's nuisances.
- REDUNDANT (the predicted reading) says greedy floors are policy properties wherever any
  perturbation is active, and that deterministic serving would freeze rather than remove rerun
  noise (P-K6): guidance for every OSWorld-style evaluation that reruns at temperature 0.
- ENV_MATERIAL would show that environment noise given actions is a floor no serving or
  observation control can remove.
- Every reading is reported, including PARTIAL ones, with intervals.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 103 counted orx queries by four cells with returned ids, OpenReview api2 searches, arXiv API version checks via the host relay; cutoff 2026-10-11; degraded coverage recorded (orx 0.2.2 outdated; no Semantic Scholar citers, GitHub code search, vLLM issues, social media or Chinese venues) (`doctors/source.json`) | Semantic Scholar citer refresh for 2604.17849 and cELldjX2oq when the relay is free |
| Citation | PASS | Claim registry C01-C30 and R1-R4 with URLs, dates and read levels; every primary URL snapshotted with its HTTP status and body hash; cELldjX2oq, ezVIHPgaiG, qXJ0EkHo2X and I0GKaJXdCh UNVERIFIABLE_ACCESS for full text; first-party sources labelled (`doctors/citation.json`) | Read cELldjX2oq in full if a copy becomes reachable |
| Novelty | FAIL | No direct prior under the recorded coverage, NARROWED by all three cells; the blind critic and the novelty refuter have not run, and the closest prior by mechanism (cELldjX2oq) was read from its abstract only (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter |
| Design | PASS | Interventions, controls, falsifiers P1-P8 and P-K6, the six kill criteria restated with reachable thresholds, operating characteristics for every threshold by exact computation or simulation on S1a's measured inputs (seeds 42-44), A0's natural experiment replicated from hash-checked records; self-assessed, the identification refuter has not run (`doctors/design.json`) | Identification refuter |
| Compute | FAIL | Executable CPU pilot exists (A0, orx run `83ee815a`); but no Stage B manifest, container smoke, Slurm dry run, corpus rebuilder or replay mode exists, and the deterministic doctor's real-model-loop and adapter checks fail (`doctors/compute.json`, `compute/attestations-not-run.md`) | Build the capture and replay driver modes and the request rebuilder with tests; manifests, dry runs and test-only runs before a freeze |
| Safety | PASS | Offline VMs, permissive licences, images kept on the host, no outward action, host rule (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts, UNVERIFIABLE_ACCESS); Design, the vendored K-Dense `experimental-design` and
`statistical-power` skills (design before data; every threshold's operating characteristics by
exact computation or simulation); Evaluation, K-Dense `statistical-analysis`; Novelty, K-Dense
`literature-review` (PRISMA counts in the header). The integrity gate's seven failure modes are
answered in the registration's section 14.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only on an empty queue)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (wave 1 synthesis) |
| Primary-source evidence | 0 | 0 | not yet reviewed |
| Defensible novelty delta | 0 | 0 | not yet reviewed; closest prior read from its abstract |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed |
| Controls and causal identification | 0 | 0 | not yet reviewed |
| Evaluation and statistics | 0 | 0 | not yet reviewed |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed |
| Independent adversarial review quality | 0 | 0 | not yet reviewed |
| **Total** | **0** | **0** | Lower total is authoritative; caps that bind until fixed: 89 (unsigned reviews, D24) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 (synthesis) | not scored | Slate's additive decomposition not identified under redundancy; NOT_CLOCK unreachable; Stage A and B built on images S1a never kept | Sufficiency-hazard factorial on fixed requests; closed loop deferred; A0 run as an orx cpu-doctor; registration v1 drafted | awaiting the blind critic, the refute-first triad and the reviewers |
