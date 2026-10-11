# Research Direction: R01 first step, where S1a's greedy rerun disagreement starts on the certified desktop stack (Stage A records census, run; Stage B onset-step factorial of serving x clock region x other screen regions; Stage C open-loop replay)

**Status:** repaired under program decision D75 for a fresh gauntlet run, after gauntlet wave 1 (score 58, the lower of 58 and 62; all three refuters refuted; honest exit on the declared query budget; `program/gauntlet/2026-10-11-r01-rerun-noise-sources.jsonl`, row hash `22639b76...`); repair by the single owner on 2026-10-11 on the development Mac's CPU (no GPU, no host job; read-only ssh only for `squeue` and one fetch attempt through the host relay); the draft registration is now `program/preregistrations/r01-rerun-noise-sources-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted; the blind critic, the refute-first triad and the two reviewers of this run have not run; Stage A0 is the executable CPU pilot (orx run `83ee815a-426a-4b94-a93f-cc1277972d76`, `ORX_RESULT ... exit=0`), and the P0 self-test, the request-replay driver and the open-loop driver are now built and CPU-tested against fakes; P0 and Stage B have registered caps of 4.82 cap-GPU-h (4.08 without conditional jobs), under the 8 GPU-h line, but under D24 and D70 they run only after Kevin's admission ruling whatever this gauntlet scores; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D75 repair (identification, two-stage model, caps, drivers, registration v2, simulations) by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-11
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex: 125 counted orx discover queries by the four cells and the novelty refuter, 16 OpenReview api2 term searches, one arXiv API title search, 6 web searches, the renewal dossier's ACL Anthology regex queries; see wave 1's record) plus this run's repair: 15 counted orx discover queries (10 keyword, including title-phrase queries for "Nondeterminism and Instability in Neural Network Optimization", "Deterministic Implementations for Reproducibility in Deep Reinforcement Learning", "Randomness In Neural Network Training: Characterizing The Impact of Tooling" and "The Evaluator Also Varies"; 3 embedding, one of them the repaired mechanism in plain words; 2 OpenAlex; two bounded with `--published-after`), with returned ids in `query-log-run2.json`; 5 full-text reads (2103.04514, 1809.05676, 2106.11872, 2607.28495, 2601.06118) and 3 report reads (2609.09212, 2607.28802, 2610.00447), uncounted; two uncounted fetch attempts for cELldjX2oq's full text (the OpenReview PDF through the host relay and the OpenReview API attachment route), both HTTP 403 browser challenges, not bypassed, so cELldjX2oq is still judged from its abstract (UNVERIFIABLE_ACCESS). orx reports itself outdated (0.2.2 against 0.2.18); its newest results are dated 2026-10-09 to 2026-10-10. Not searched in either run: Semantic Scholar or Google Scholar citation graphs, GitHub code, the vLLM issue tracker, patents, live X, Reddit, Chinese-language venues; this run ran no OpenReview or ACL Anthology search (wave 1's stand). PRISMA-style for this run: 216 ids identified, 205 unique, screened by title; 8 read beyond the title; 0 direct priors.
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-11-r01-rerun-noise-sources/bundle.json

The budgets are this fresh run's (D75), cumulative over the repair, the triad, the reviewers and
the recorder; at least 30 of the 80 queries are reserved for the three refuters (six orx discover
queries each at minimum). Under the program's counting rule (every retrieval search that reached
a backend counts) the repair used 15, leaving 65. The gauntlet's GPU budget (0.3 GPU-h) is for the
open-weight reviewer's lane job only; the doctor reads budgets as integers, parses it as 0 and
flags it (left as declared). The novelty verdict field uses the doctor's vocabulary; the merged
kill-shot verdict is **NARROWED**, not OCCUPIED.

## Changes after wave 1

Wave 1 (row hash `22639b76...`; proposal sha256 `0eae5ee4...`, registration v1 sha256
`6bc3adf0...`) scored 58: reviewer 1 (claude-opus-5-5) 58, reviewer 2 (qwen3.6-35b-a3b, Slurm
1143) 62. Blind discrimination against cELldjX2oq passed thinly (same mechanism at its core, the
proposal stronger by an incremental step). All three refuters refuted. The largest defect was
identification: Stage B's primary hazards pooled steps 1-8 of 40 episodes, although S1a's first
reply-text divergence falls at step 1 in 205 of 226 within-session pairs; only 40 of 320 requests
measured the hazard the mechanism needs, the text readings were settled by A0 in advance, and the
step-kick model compounded an identical-history IR hazard, contrary to the mechanism. Reviewer 2
put feasibility first (J3 priced at one lane's mean, a timing gate that blocked J3 and J4, P0
waiting on Stage C, four unbuilt tools). Both ranked novelty second (the "sufficiency under
redundancy" delta is published for training nondeterminism, uncited). D75 ordered one CPU repair
by a single owner. This section is that repair. Evidence is in the bundle's `compute/repair-d75/`:
`power_r01_v2.py` and `power-r01-v2.json` (every decision rule's operating characteristics under
the registered estimator, and the two-stage model), `caps_r01_v2.py` and `caps-r01-v2.json`
(caps repriced), `build_query_log_run2.py` and `query-log-run2.json` (this run's retrieval), and
the code under `harness/r01/` with its tests.

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | Stage B's primary estimands pool steps 1-8; 205 of 226 S1a pairs first diverge at step 1; no reading is step-resolved (largest defect: reviewer 1, identification refuter, reviewer 2) | The primary estimands are the per-source sufficiency hazards **at the divergence-onset step**: step 1 on 226 request pairs on 113 tasks, matching S1a's 226 within-session pairs, with step 2 (113 pairs) secondary. Each source is isolated by a 2^3 factorial on fixed first-step requests: serving (verified-deterministic reference against S1a's configuration under S1a-like load) x clock region (same or from a second boot's real screenshot) x every other screen region (same or from the second boot). The cell with every source active must reproduce S1a's own step-1 divergence (205/226 text, 79/226 IR) before any attribution (VAL) | 1, 7.1, 7.4, 10.3-10.5 | `power-r01-v2.json` B_cells, VAL, DECISIVE |
| 2 | Text-level readings settled in advance by A0; M's falsifier unreachable (reviewer 1, feasibility refuter) | Settled only for serving (A0: 12 of 19 natural replays). The clock-alone and other-regions-alone cells under a deterministic engine have no data in S1a and can read INERT (probability «P:INERT_TEXT_001» at a true 0.01). M is falsified in this step by SINGLE_SOURCE, NEITHER or VAL_FAIL. The IR readings are now relative to S1a's natural step-1 action divergence (MAJOR above half of 0.350, MINOR below a third), so they say which source alone reproduces the first-action divergence | 3.2, 10.3-10.5 | B_cells, DECISIVE |
| 3 | The step-kick model compounds an identical-history IR hazard, contradicting the absorbing text onset (reviewer 1) | Replaced by a two-stage model (`harness/r01/stepkick.py`): a text-onset hazard by step (absorbing), then the action-divergence probability at onset and a constant post-onset rate, with joint-end hazards. Validated on S1a before any GPU: it reproduces 4B H-OSW-fixed's IR identity (largest gap 0.020 over 15 steps; 0.650/0.456/0.323/0.204 observed against 0.671/0.454/0.308/0.208), N (0.063 against 0.066) and D_w (0.1199 against 0.1195); leave-one-group-out largest gap 0.069. The D_w prediction under each removal now follows from that arm's measured step-1 and step-2 cells (registered for Stage D, with paired intervals against the live arm) | 2.4, 3.1, 10.9 | PRED |
| 4 | Redundancy evidence "2 of 19 against 90 of 885" is task composition (identification refuter, reviewer 1) | Dropped as evidence (15 of the 19 pairs sit in all-agree units; expected 2.2 discordant) | 2.1 | wave 1's refuter |
| 5 | J3 priced at one lane's mean pass; overrun probability 0.52-0.96 (feasibility refuter, both reviewers, recorder) | Every cap repriced with arithmetic on S1a's realized step-1 and step-2 costs; loaded passes simulated as the slowest of 20 lanes (95th percentile of 20,000 draws, latencies resampled from S1a, x 1.25 for high). J3 is now 5 passes of 339 items, cap 36 min; simulated overrun probability at the cap 0 (largest draw 1,653 s of 1,860 s available). Totals 4.82 cap-GPU-h with conditional jobs, 4.08 without (wave 1: 4.22) | 11 | `caps-r01-v2.json` |
| 6 | The P0 timing gate, read literally, blocks J3 and J4 (feasibility refuter, reviewer 1) | Batch-1 jobs projected from P0's measured 95th-percentile per-request time by step; loaded jobs from the loaded-pass simulation fed P0's own loaded pass (P0 now includes one) | 10.1 | `harness/r01/p0.py`, `tests/test_r01_replay_p0.py` |
| 7 | P0 waits on Stage C's frames and four unbuilt tools (feasibility refuter, reviewer 2) | Every Stage B request, P0's probe items included, is built from A1's frames (one open-loop step in A1 supplies the step-2 frames); Stage C runs independently. Built and CPU-tested: the request rebuilder and composites (`requests.py`, `regions.py`), the request-replay driver with the batch-1, cold/warm and loaded protocols (`replay.py`), the P0 self-test and timing gate (`p0.py`), the A1 capture and Stage C open-loop modes on S1a's runner (`openloop.py`), a fake engine with controllable nondeterminism (`fake_engine.py`), the estimator and the model; 38 tests pass. What remains (an R01 lane adapter, the corpus and report CLIs, manifests, smoke, dry runs, P0 itself) is listed in registration section 16 | 7, 16 | `harness/r01/`, `tests/test_r01_*.py` |
| 8 | Clock box fitted from minute changes only, used on hour-apart comparisons (identification refuter, reviewer 1) | The box is fitted to the full extent of the clock label over every A1 frame (hour digits always inside), with a stop rule; the clock factor's swap source is a second boot at S1a-like spacing (A1 pairs dispatched k positions apart, k from S1a's 171 s median spacing); Stage C's r1 and r2 are also paired at that spacing | 5.3, 6, 7.1 | `regions.py`, tests |
| 9 | Interaction confounded by schedule sharing (identification refuter) | Every live cell compares pass 1's reply to the reference with another pass on a different seeded schedule | 7.3 | registration |
| 10 | Encoder cache never reset; prefix caching flips the Mamba cache mode (identification refuter, reviewer 1) | The encoder cache is reset before every E-det request and wherever the prefix cache is reset; P0 records each configuration's Mamba mode; the serving factor is declared a bundle (batch, cache hits, Mamba mode), with J2 and J4 separating channels as a secondary | 7.2 | `replay.py`, `p0.py` |
| 11 | Resume equivalence false for loaded passes (feasibility refuter, reviewer 1) | A loaded pass is atomic: a cut pass is voided and rerun whole in a fresh job; batch-1 arms resume per item | 7.3, 11 | `tests/test_r01_replay_p0.py` |
| 12 | A1 priced at 110 s per boot (feasibility refuter) | A1 priced from S1a's realized overhead to the first observation (mean 95.6 s, maximum 122.5 s) plus frames and the open-loop step: 678 boots, 20.5 VM-h central, 25.6 high | 11 | `caps-r01-v2.json` cpu_lane |
| 13 | Novelty: "sufficiency under redundancy" published for training nondeterminism, uncited (novelty refuter; both reviewers) | Summers and Dinneen 2021 (2103.04514), Nagarajan et al. 2018 (1809.05676) and Zhuang et al. 2021 (2106.11872) read in full and cited; the one-source-at-a-time protocol and the redundancy-through-instability finding are credited to them. Ledger row 4 is rewritten as a setting-plus-measurement delta: the onset-step factorial on fixed desktop-agent requests with real screen-pixel perturbations, validated against the closed loop, plus open-loop environment replay. The identical-input-replay literature is credited for the serving cells, including 2607.28495 (exact-token replay can repeat itself without reproducing live state), which is why step 2 is secondary | Proposal | `query-log-run2.json` |
| 14 | Blind pass held against the text-agent prior only (reviewer 1) | Fresh anonymized paragraphs: the proposal (`blind/paragraph-3fe4da7c.txt`), cELldjX2oq (`blind/paragraph-69e5c3ef.txt`, abstract-based) and, for a second critic call, Summers and Dinneen 2021 (`blind/paragraph-d8ac91b5.txt`, from full text); roles in `compute/repair-d75/blind-roles-run2.json` | Proposal | `blind/` |
| 15 | Query-counting convention left open; Design PASS self-assessed (process) | This run counts every retrieval search that reached a backend (65 of 80 left, reserve intact). The Design doctor is marked self-assessed with the refuters still to run | Header | `query-log-run2.json` |

Not repaired, and why:

- **cELldjX2oq's full text.** Both reachable routes return a browser challenge; it is not
  bypassed. Its row stays abstract-based (UNVERIFIABLE_ACCESS), and the delta is written so that
  it does not rest on anything the abstract leaves open.
- **Compute attestations.** No manifest, container smoke, Slurm dry run or test-only run exists;
  this run may submit nothing but the reviewer's lane job. The deterministic doctor's Compute
  check stays FAIL. The drivers run against fakes only.
- **An R01 lane adapter.** S1a's lane hard-codes S1a's runner module, experiment id and ledger
  row (`harness/q2_stage1/lane.py`, pinned by S1a's registration). Running A1 and Stage C needs a
  new adapter module; it is the main remaining CPU engineering item (registration section 16).
- **Unsigned reviews (cap 89)** and the trust store (D24).
- **External validity.** One model (4B), one harness, one host and engine build, 113 tasks.

## Scope

R01's first step only: Stage A (A0, run; A1.0, a task audit; A1, 678 fresh boots with frames and
one open-loop step), Stage B (the onset-step factorial, GPU, no VMs) and Stage C (open-loop replay
of S1a's recorded actions on the CPU lane, 0 GPU-h). No closed-loop agent episode is part of this
step. A closed-loop Stage D is sketched in the registration's section 18; it would test the
registered D_w predictions and needs its own registration.

## Changes from the renewal slate's R01, and why

Wave 1's table (rows 1-9: additive shares replaced by sufficiency hazards; closed loop deferred;
NOT_CLOCK restated; A0 on hashes; MULTI_REGION census; a factorial with a self-test; open-loop
replay twice; D72's shares; an explicit cap rule) stands, as amended by "Changes after wave 1":
the sufficiency hazards are now measured at the onset step, the step-kick model is now two-stage,
and the caps are repriced.

## Merged discovery cells, by mechanism

Wave 1's four cells (frontier, kill-shot, cross-domain, asset) are summarized in its record and
the previous version of this section (proposal sha256 `0eae5ee4...`). The repair adds:

**Training nondeterminism (the adjacent field the cells missed).** Summers and Dinneen (2103.04514)
isolate each source of training nondeterminism by holding every other seed fixed, find that every
source has nearly the same effect on run-to-run variability, and explain it by the instability of
training (a one-bit change in one initial parameter suffices); they also delay the onset of
nondeterminism by N identical epochs. Nagarajan, Warnell and Stone (1809.05676) build a
deterministic deep Q-learning implementation and enable sources one by one (environment, GPU,
initialization) on pixel-observation Atari games. Zhuang et al. (2106.11872) separate algorithmic
from tooling randomness and price determinism (up to 746% overhead). R01's mechanism (redundant
sources because the process is unstable) is theirs, moved to closed-loop agent inference; R01's
contribution is the measurement in a setting none of them covers.

**Identical-input replay.** Beyond wave 1's sources (2609.04748, 2606.15621, 2605.27763, the
Thinking Machines note, Vosti), 2607.28495 shows that replaying an exact token prefix by fresh
prefill repeats itself bitwise yet differs from continuing the live decode state (166 of 200
suffixes in BF16; K/V transplants carry the divergence, 24 of 24 and 43 of 43), and 2601.06118
shows nondeterminism moves token probabilities most in the 0.1-0.9 range. For R01 this makes step
1 the clean onset estimand (no earlier reply to re-prefill) and step 2 a disclosed secondary.

**Pixel sensitivity.** AgentHijack (2609.09212) shows multimodal computer-use agents can be
hijacked by adversarial visual patches; R01's pixel factor is the opposite case, natural and
benign time-varying regions rendered by the desktop itself.

## Claim and Research Question

**Question.** On S1a's certified desktop stack (Qwen3.5-4B, H-OSW-fixed, greedy decoding,
thinking passed back, 15 steps, V = 20, vLLM v0.31.0 with prefix caching, guest clock live), at
the step where rerun pairs start to diverge (step 1 in 205 of 226 pairs), how often is each
candidate source alone enough to change the greedy reply and the parsed action: serving numerics
on byte-identical requests, the clock region's pixels, every other screen region? How do they
combine, does the all-sources cell reproduce S1a's own onset, and how much does the environment
change the screen or the verdict given fixed actions?

**Variables.** Serving (E-det, verified-deterministic, against E-s1a under S1a-like load), clock
region (same, or a second boot's), other regions (same, or a second boot's); secondarily the
cache and batch channels and the guest's cursor blink. Outcomes: reply-text and parsed-IR
identity per request pair; frame identity per step and verdict identity per episode in replay.

**Claim scope:** `systems-pipeline`. The claim is about an evaluation stack's noise sources on
this host and configuration, not about any model's capability and not an architecture claim.
Every number is "not externally anchored".

## Strategic Fit and Why Now

- The program is "checker adequacy and calibrated measurement for verifiable machine work". S1a
  measured the rerun floor (D_w 11.9% for 4B H-OSW-fixed) and the variance split (D72 (ii):
  rerun noise 21-27% of outcome variance, task-by-harness at most 1% at 4B), but not where the
  floor comes from. D73 recommends R01 as the renewal slate's lead.
- The two-stage model fitted on S1a already says what matters: D_w barely moves while some
  active source keeps the step-1 onset hazard above about 0.3 (0.120 at 0.907, 0.118 at 0.63,
  0.103 at 0.3) and falls only below it (0.060 at 0.1). The onset hazards decide whether any
  practical control (deterministic serving, a masked clock, a blink-off guest) can make greedy
  reruns repeat, and therefore whether a floor measured with live nuisances is a property of the
  policy and tasks or of the nuisances.
- The question is active in text agents (cELldjX2oq, 2026-09-18; TRACE 2610.11678, 2026-10-08;
  2610.01618, 2026-10-01). No pixel-agent attribution was found. The scoop window is open but
  narrowing.
- A0 is done, so the first step costs at most 4.82 cap-GPU-h (2.66 physical, central), with A1
  and Stage C on CPU.

## Primary-Source Evidence

Claim registry (full: `evidence/.../doctors/citation.json`). Read levels: F = full text read with
`orx paper --full` (by a wave-1 cell, or by the repair owner for C31-C35); A = abstract or report
only; R = repository; 1P = first-party.

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
| C31 | Training-nondeterminism protocol: hold every other source's seed fixed and vary one; every source has nearly the same effect on run-to-run variability; instability (a one-bit change in one initial parameter suffices) is the explanation; delaying the onset of nondeterminism reduces variability only gradually | https://arxiv.org/abs/2103.04514 | 2021-03-08 (v2 2021-06-01) | F |
| C32 | Deterministic deep Q-learning implementation; sources (environment, GPU, initialization and others) enabled one by one on Atari; individual sources substantially change performance variance | https://arxiv.org/abs/1809.05676 | 2018-09-15 | F |
| C33 | Tooling randomness separated from algorithmic randomness (ALGO+IMPL, ALGO-only, IMPL-only); determinism overhead up to 746%, 241% and 196% across GPU architectures | https://arxiv.org/abs/2106.11872 | 2021-06-22 | F |
| C34 | Exact-token replay by fresh prefill against the retained live cache: replicas exact, yet BF16 constructions differ on 166 of 200 suffixes; FP32 shows no decoded disagreement; full K/V transplant makes divergent continuations follow the donor (24 of 24, 43 of 43) | https://arxiv.org/abs/2607.28495 | 2026-07-30 | F |
| C35 | Under GPU nondeterminism, token-probability variations are significant for probabilities between 0.1 and 0.9 and small near 0 or 1, similarly across models | https://arxiv.org/abs/2601.06118 | 2026-01-03 | F |
| C36 | Adversarial visual patches can hijack multimodal computer-use agents | https://arxiv.org/abs/2609.09212 | 2026-09-06 | A |
| R1 | S1a: 1,808 episodes, 0 losses; D_w 4B 11.1% on 113 tasks; first divergence labels; prefix-cache hit share 0.855-0.858; realized cost 0.0025-0.0027 GPU-h per episode | `program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md` | 2026-10-10 | R |
| R2 | D72 (ii) corrected variance shares | `program/decisions.md` D72 | 2026-10-11 | R |
| R3 | A0 census (registration v1 section 2.1) | `program/evidence/2026-10-11/r01-stage-a0/census.json`, orx run `83ee815a` | 2026-10-11 | R |
| R4 | S1a engine argv (`--max-num-seqs 256`, `--max-num-batched-tokens 8192`, `--enable-prefix-caching`, `--seed 42`) and sampling (temperature 0, top-p 0.9) | `program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json` | 2026-10-09 | R |
| R5 | S1a's onset structure (4B H-OSW-fixed): first reply-text difference at step 1 in 205 of 226 pairs, 19 at step 2; first IR difference at step 1 in 79; step-1 latency mean 1.929 s, 95th percentile 2.650 s; step-2 2.401 s, 3.351 s | the A0 digest table, recomputed in `compute/repair-d75/power-r01-v2.json` and `caps-r01-v2.json` | 2026-10-11 | R |
| R6 | Prefix caching sets Qwen3.5's Mamba cache mode to `align`; the encoder cache has a 16,384-token budget | `program/evidence/2026-10-07/serving-throughput-probe-v1/jobs/a-442/probe/engines/real/engine.log` lines 11 and 46 | 2026-10-07 | R |

## Closest Prior Work

1. **cELldjX2oq, "The Evaluator Also Varies: Localizing Nondeterminism in Interactive Agent
   Benchmarks"** (ICLR 2027 submission). The closest in setting and mechanism family: it finds
   where replicated greedy runs first diverge (agent, simulated user, environment, serving), from
   identical preceding recorded histories, with cache-off comparisons. Text environments only;
   judged from its abstract (two full-text routes return a browser challenge). Delta: R01 does not
   locate the first discrepancy of observed runs; it intervenes on fixed first-step requests of a
   pixel desktop agent in a crossed 2^3 design (serving x clock region x other regions, every
   perturbation a real second-boot rendering), checks the all-sources cell against the closed
   loop, replays the environment open loop, and turns the onset hazards into registered
   predictions with a model validated on the original runs.
2. **2103.04514 (Summers and Dinneen), with 1809.05676 and 2106.11872.** The one-source-at-a-time
   protocol and the redundancy-through-instability finding come from training nondeterminism.
   R01 credits both and claims neither: its delta is the setting (closed-loop inference of a
   frozen pixel agent, where a run's own reply is the next input), the onset-step estimand, real
   screen-pixel sources, the closed-loop validation and the environment replay.
3. **2604.17849, "On the Reliability of Computer Use Agents"** (and its ARR version
   ezVIHPgaiG). The closest by domain: OSWorld reruns with a deterministic-decoding arm and
   cosmetic perturbation bundles (timezone among them), never crossed; no clock intervention, no
   identical-input test, no open-loop replay, no source attribution.
4. **Identical-input replay: 2609.04748, 2606.15621, 2605.27763, 2607.28495, 2601.06118,
   2609.38981**: the template for the serving cells (batch 1, cache on and off, replica floors,
   batch-invariant confirmation) and the reason step 2 is secondary; R01 adds the hybrid VLM,
   image-heavy requests, S1a-like load and the observation factors.
5. **2405.14573, 2607.17136**: clock reset and frozen clocks in GUI and web benchmarks; neither
   measures the clock's effect on rerun disagreement.
6. **2609.20625 (Chronicle) and 2608.08239 (Replay Gap)**: record and replay of agent runs and
   its limits; Stage C inherits the limit (it measures fixed actions, not adaptation).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Identical-input replay with a replica floor, batch 1 and cache on/off, batch-invariant fallback (h_floor, h_s, P0, J2, J4) | 2609.04748; 2606.15621; 2605.27763; 2609.38981 | the method | setting only: a Gated DeltaNet hybrid VLM on agent requests with screenshots, at S1a-like load; no method claim | high that the method is occupied |
| Isolating each nondeterminism source by holding the others fixed, and finding the sources redundant because the process is unstable | 2103.04514; 1809.05676; 2106.11872 | the protocol and the explanation | none claimed; R01 applies them to closed-loop agent inference | high that the method is occupied |
| A 2^3 factorial on fixed **onset-step** requests of a pixel desktop agent: serving x clock region x other screen regions, each perturbation a real second-boot rendering, read as per-source sufficiency hazards (text and action) with interactions | cELldjX2oq (first-divergence localization in text agents); 2604.17849 (uncrossed determinism and perturbation arms); 2103.04514 (one source at a time, training) | attributing rerun divergence to components | the crossed, interventional design at the onset step in a pixel agent; no prior found that measures a rendered clock's or other screen regions' sufficiency on byte-fixed requests | medium (cELldjX2oq judged from its abstract) |
| Validating the request-level cell with every source active against the closed loop's own onset counts (VAL) | none found | none | a manipulation check tying request-level replay to closed-loop reruns | medium |
| Two-stage onset model (absorbing text onset, then a post-onset action-divergence rate) validated on the original runs, turning measured onset hazards into registered D_w predictions per removal | 2609.16617 (token-level first-mismatch plus exposure identity); 2103.04514 (delayed-onset experiment) | decomposing cumulative disagreement at a first mismatch | step-level for agent trajectories, with parameters measured on the original runs and predictions registered before the closed-loop test | medium |
| Open-loop replay of recorded actions in reset VMs, twice, two frames per step | 2609.20625; 2608.08239; Lam et al. FSE 2017 | record and replay | applied to desktop-agent verdicts and per-step frame identity; no method claim | high that the method is occupied |
| Records-only census of natural identical-input replays in an existing study's hashed logs (A0) | 2602.07150; cELldjX2oq | rerun analysis | a natural experiment from S1a's hashes; descriptive | medium |

Novelty wording: No direct prior art found through 2026-10-11 under the coverage in the header
(orx discover keyword, embedding and openalex queries listed with returned ids in the bundle's
`query-log.json` (wave 1) and `query-log-run2.json` (this run), including title-phrase queries
for "On the Reliability of Computer Use Agents", "The Evaluator Also Varies", "Same Request,
Different Answer", "Dating the Model", "Defeating Nondeterminism in LLM Inference", "Greedy
Decoding Is Not Precision-Invariant", "On Randomness in Agentic Evals", "Measuring all the noises
of LLM Evals", "Marconi", "Engineering record and replay for deployability", "Nondeterminism and
Instability in Neural Network Optimization", "Deterministic Implementations for Reproducibility
in Deep Reinforcement Learning" and "Randomness In Neural Network Training"; OpenReview api2 term
searches (wave 1); the dossier's ACL Anthology regex queries) that measures, on fixed onset-step
requests of a pixel-observation desktop agent, the sufficiency of serving numerics, the rendered
clock and other screen regions crossed in one factorial, validated against the closed loop, with
an open-loop environment replay. The serving-replay, source-isolation, clock-control and
record-and-replay methods are each occupied; the residual is their crossed, onset-step
measurement on this kind of agent. Never "completely novel".

## Mechanism and Falsifiable Predictions

**Mechanism (M), two stages.** Each request carries every earlier reply (thinking included) and
screenshot. (i) **Onset:** with identical histories, a step's reply text differs with a hazard
from several sources: serving numerics on identical inputs (batch composition; a hybrid model's
prefix-cache hit resuming from a block-aligned recurrent-state checkpoint), the clock's pixels,
every other screen difference between two boots, and, from step 2, the environment given actions.
The first text difference is absorbing. (ii) **Action divergence:** at the onset step the action
differs with probability π; afterwards actions part at a rate ρ set by the policy and the tasks.
If at least two sources each change step-1 text with a high hazard, removing one leaves the onset
at step 1 or 2 and D_w unchanged; only removing every text-level kicker freezes trajectories, and
reruns then repeat one draw. On S1a this model, fitted by event counts, reproduces the IR-identity
curve (largest gap 0.020), N and D_w (0.1199 against 0.1195); D_w falls materially only when the
onset hazard drops below about 0.3.

**Predictions, each with a falsifier** (registration section 3.2): P1 SERVING SUFFICIENT at the
text level (A0: 12 of 19); P2 DET_OK on 226 replica pairs; P3 CLOCK and P3' NON-CLOCK SUFFICIENT
at the text level under the deterministic engine (no data); P4 at the IR level SERVING MINOR,
NON-CLOCK MAJOR, CLOCK not MAJOR; P-VAL VAL_PASS; P5 MULTI_REGION; P6 ENV_BOUNDED; P7 frame
identity below 0.95 by default and at least 0.95 under blink-off; P8 (Stage D) every single
removal within 2 pp of the live arm's predicted D_w («P:P8RANGE» under the records' scenario);
P-K6 a frozen stack does not narrow a K = 113 contrast at one rerun per arm.

**M is falsified in this step** by a joint text reading of SINGLE_SOURCE or NEITHER, or by
VAL_FAIL; each is reachable (INERT at a true 0.01: «P:INERT_TEXT_001»; VAL_FAIL at a true IR rate
of 0.20 instead of 0.35: «P:VALFAIL_IR020»). **Kill criteria, restated** (registration section
10): K1 not removable (blink-off identity outside the box with an upper bound below 0.90); K2
ENV_MATERIAL; K3 DET_UNATTAINABLE (k ≥ 6 of 226); K4 moves to Stage D; K5 CLOCK INERT and MINOR
stops the pixel line; K6 is the prediction P-K6.

## Cheapest Decisive Pilot

- **Executed (CPU, 0 GPU-h): Stage A0**, orx cpu-doctor node `ff110047` (branch
  `orx/r01-stage-a0-records-census`, commit `ca3cdbf`), run
  `83ee815a-426a-4b94-a93f-cc1277972d76`: `ORX_RECEIPT_SUMMARY {"cases": {"passed": 8, "total":
  8}, "doctor": "r01-stage-a0", ... "status": "PASS"}`, `ORX_RESULT kind=cpu-doctor
  direction=r01-rerun-noise-sources exit=0`; receipt byte-identical to the committed census.
- **Built and CPU-tested in this repair (0 GPU-h):** the P0 self-test and timing gate, the
  request-replay driver and the open-loop driver, against `harness/r01/fake_engine.py` and S1a's
  fake guest (38 tests), and the two-stage model's validation on S1a's records.
- **Next, decisive for identification (GPU, 0.45 cap-GPU-h, after admission): P0**, on probe items
  built from A1 frames that no corpus request uses (no longer behind Stage C): is Qwen3.5 on vLLM
  v0.31.0 bitwise deterministic at batch 1 with the prefix cache off (else the batch-invariant
  fallback P0'), do log-probabilities change outputs, what are the Mamba modes, and what does a
  request cost at batch 1 and under load.
- **The single result that would kill the first step's value:** DET_UNATTAINABLE in both P0 and
  P0' (the clock and other-region cells are then "observation or engine, not separated"), or
  VAL_FAIL (the request-level onset is not S1a's). Both are cheap to reach and reportable.

## Controls, Baselines, and Ablations

- Replica floor h_floor for every det cell; the P0/P0' bitwise self-test.
- Serving: S1a's exact argv under S1a-like load (E-s1a) against the deterministic reference
  (E-det); the cache and batch channels separated (E-c1 cold/warm, E-nc), each a secondary.
- Observation: the clock factor and the other-region factor are real second-boot renderings,
  composited on raw PNGs and checked pixel by pixel (C differs from R only inside the box, O only
  outside); the full-label clock box; a blink-off pair (conditional cell).
- VAL: the all-sources live cell against S1a's 205/226 and 79/226.
- Every live comparison is across two different seeded schedules.
- Environment: replay against replay (pure environment) and replay against the original.
- Negative control: every cell's request carries the reference's prompt ids; rebuilt step-2
  requests match S1a's recorded digests.
- Positive control: b3's t0 against t0 + 61 s differs inside the box in every task.
- No architecture claim, so no matched from-scratch arm is needed.

## Evaluation, Statistics, and Leakage Checks

- Cell hazards: pooled share of differing pairs, task-cluster percentile bootstrap (2,000
  resamples, seed 42), at the text and IR levels; 226 step-1 pairs on 113 tasks, 113 step-2 pairs.
  Operating characteristics by simulation with the registered code (`power-r01-v2.json`, seeds
  42-44, 300 replicates per seed, task heterogeneity from S1a: ICC 0.2 text, 0.45 IR):
  «P:CELLS_SUMMARY»
- DET: exact binomial on 226 pairs (k* = 6): P(DET_OK) 0.80 at p = 0.001, 0.32 at 0.005;
  P(DET_UNATTAINABLE) «P:DET_UN_002» at 0.02, «P:DET_UN_003» at 0.03.
- VAL: «P:VAL_SUMMARY»
- Decisiveness of the primary gate (joint text reading not MIXED and VAL not UNRESOLVED):
  «P:DECISIVE_SUMMARY»
- Stage C and A1: v1's rules, re-run (C_env: P(ENV_BOUNDED) «P:CENV_BOUNDED_001» at e = 0.01;
  P(ENV_MATERIAL) «P:CENV_MAT_005» at e = 0.05; A1: «P:A1_SUMMARY»).
- D_w predictions: the two-stage model with each arm's measured cells and S1a's ρ, τ, q; paired
  intervals against the live arm (q's uncertainty cancels).
- Missing data: complete case by pair; more than 5% missing voids a cell.
- Leakage: A0 and S1a's onset counts were read to design the study and enter only as VAL's
  registered comparison values and the model's S1a parameters (disclosed). The clock box and the
  composite checks are committed before the corpus build. No new outcome is seen before a freeze.
- Saturation: text identity can saturate under batching (C11, C35), so IR readings sit beside it,
  and the first differing token's margin is recorded.

## Compute and Reproducibility

- **Image:** the engine base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  (vLLM v0.31.0 at `db9527a4`) with S1a's cu129 overlay (local image ID
  `sha256:10327c706dcf2a9bd06e2449908e37d4fa4e46e7030a85e66f30626a1bafecde`, built by
  `scripts/build_vllm_overlay_on_h100.sh` from source `4a59e87c`); model Qwen3.5-4B at
  `851bf6e8`, receipt `75ebfc53`. CPU lane: S1a's VM image `fe8d9a5e` and metric image `2006c1a9`.
- **Launch:** every GPU job is one manifest, `experiments/manifests/r01/p0.yaml`, `p0-bi.yaml`,
  `j1.yaml`, `j1b.yaml`, `j2.yaml`, `j3.yaml` and `j4.yaml` (none rendered yet), submitted only by
  `uv run python scripts/submit_docker_research_job.py experiments/manifests/r01/j1.yaml
  --dry-run`, then `--test-only`, then without a flag, which issues `sbatch --parsable
  --partition=research --gres=gpu:h100:1 ... infra/slurm/host-single-node/docker-research.sbatch`
  with `--signal=B:USR1@180` and the job's cap as `--time`. The workload inside each job is
  `python -m harness.r01.replay` (or `harness.r01.p0`) over the bridge socket. CPU-lane jobs run
  `harness.r01.openloop` through an R01 lane adapter (to be built; registration section 16),
  never a GRES.
- **Seeds:** seeds: [42, 43, 44] (simulations 42-44; corpus and episode choice 42; probe 43-44;
  J3 schedules 42-46, J4 47-48; bootstraps 42; engine `--seed 42`).
- **GPU ceiling:** gpu_hours: 5 (registered caps total 4.82 cap-GPU-h with conditional jobs, 4.08
  without; per-job arithmetic on S1a's realized step costs in `caps-r01-v2.json`; loaded passes
  simulated as the slowest of 20 lanes; physical estimate 2.66 GPU-h central).
- **Checkpoints and resume:** batch-1 arms append each reply with fsync and resume at the first
  missing item (order-free); loaded passes are atomic and rerun whole when cut; A1 boots and
  Stage C replays are independent episodes with S1a's re-queue rule.
- **Artifacts:** the A0 doctor and test; `harness/r01/` and `tests/test_r01_*.py`; the
  simulation, caps and builders with outputs (bundle `compute/` and `compute/repair-d75/`).
  Screenshots and request bodies stay on the host run root with SHA-256 lists committed.
- **Cost ceiling:** at most 4.82 cap-GPU-h plus the reviewer's 0.3; CPU lane about 91 VM-h high
  (A1 25.6, C 54.7, C-blink 10.8 conditional).

## Safety, Data Rights, and Monitorability

- No training, no new downloads, no outward action; offline VMs on the certified lane; IR actions
  run only in VMs through the certified executor, as in S1a; no model-generated code runs on GPUs
  (D7).
- Licences: OSWorld tasks Apache-2.0 at `b138d348`; Qwen3.5-4B Apache-2.0 (C30); vLLM Apache-2.0.
  S1a's records are the program's own.
- Screenshots and request bodies render OSWorld task files with their own licences; they stay on
  the host, and the public repository receives hashes, counts and region rectangles only.
- The blink-off condition is a guest setting used in measurement captures and replays only; any
  closed-loop use needs a delta certification of D53's scope (owner decision).
- Host rule: one node; read-only `squeue` before each submission; no R01 job overlaps another
  workflow's job.
- Monitorability: the study reads replies and actions only; nothing trains or rewards the model.

## Negative-Result Value

- DET_UNATTAINABLE on Qwen3.5's hybrid layers in vLLM v0.31.0 (with and without the
  batch-invariant mode) is a useful engineering fact: the vLLM docs do not list Qwen3.5.
- SINGLE_SOURCE (serving) says the floor is serving-driven: deterministic serving alone would
  freeze reruns (and P-K6 says what that costs for comparisons).
- REDUNDANT, the predicted reading, says greedy floors are policy properties wherever any one
  sufficient source is active, and the model says by how much each removal would move D_w.
- VAL_FAIL says request-level replay does not reproduce closed-loop onset on this stack, a
  warning for every replay-based attribution, including R01's own.
- ENV_MATERIAL would show an environment floor no serving or observation control can remove.
- Every reading is reported, including PARTIAL and MIXED, with intervals.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; wave 1's 125 counted orx queries plus 16 OpenReview searches, and this run's 15 counted orx queries with returned ids and raw-output digests; 8 reads beyond the title; cutoff 2026-10-11; degraded coverage recorded (orx outdated; no citation graphs, GitHub code, vLLM issues, social media or Chinese venues; cELldjX2oq's full text behind a challenge) (`doctors/source.json`) | Semantic Scholar citer refresh for 2604.17849, cELldjX2oq and 2103.04514 when the relay is free |
| Citation | PASS | Claim registry C01-C36 and R1-R6 with URLs, dates and read levels; every primary URL snapshotted with its HTTP status and body hash; cELldjX2oq, ezVIHPgaiG, qXJ0EkHo2X and I0GKaJXdCh UNVERIFIABLE_ACCESS for full text; first-party sources labelled (`doctors/citation.json`) | Read cELldjX2oq in full if a copy becomes reachable |
| Novelty | FAIL | No direct prior under the recorded coverage, NARROWED; the adjacent training-nondeterminism field now read and credited; this run's blind critic and novelty refuter have not run, and cELldjX2oq is abstract-only (`doctors/novelty.json`) | Run the blind critic on the fresh `blind/` packet (and a second call against `paragraph-d8ac91b5.txt`) and the novelty refuter (65 queries left, above the reserve of 30) |
| Design | PASS | Self-assessed; the identification refuter of this run has not run. Interventions (the onset-step 2^3 factorial; channels; blink-off), controls (replica floor, self-test, VAL, cross-schedule live comparisons, composite checks, fidelity, positive control), falsifiers P1-P8, P-VAL, P-K6 and K1-K6, operating characteristics of every rule under the registered estimator (seeds 42-44), the two-stage model validated on S1a (`doctors/design.json`) | Identification refuter; pre-freeze audit |
| Compute | FAIL | Executable CPU pilot exists (A0, orx run `83ee815a`); P0, the replay driver and the open-loop driver are built and CPU-tested against fakes; but no lane adapter, manifest, container smoke, Slurm dry run or test-only run exists, and the deterministic doctor's real-model-loop and adapter checks fail (`doctors/compute.json`, `compute/attestations-not-run.md`) | Lane adapter, corpus and report CLIs, manifests; dry runs and test-only runs before a freeze |
| Safety | PASS | Offline VMs, permissive licences, images kept on the host, no outward action, host rule (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts, UNVERIFIABLE_ACCESS); Design, the vendored K-Dense `experimental-design` and
`statistical-power` skills (design before data; a crossed factorial blocked by task; every
threshold's operating characteristics by simulation of the registered estimator on S1a-calibrated
inputs); Evaluation, K-Dense `statistical-analysis`; Novelty, K-Dense `literature-review` (PRISMA
counts in the header). The integrity gate's seven failure modes are answered in the
registration's section 14.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviews are in the gauntlet record)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only on an empty queue)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed in this run (wave 1: 7 and 8) |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1: 6 and 8) |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1: 4 and 5) |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1: 5 and 5) |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1: 5 and 5) |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1: 6 and 8) |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1: 4 and 3) |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1: 6 and 3) |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1: 9 and 9) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1: 6 and 8) |
| **Total** | **0** | **0** | Lower total is authoritative (wave 1: 58 and 62, score 58); caps that bind until fixed: 89 (unsigned reviews, D24) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| wave-1 synthesis (2026-10-11) | not scored | Slate's additive decomposition not identified under redundancy; NOT_CLOCK unreachable; Stage A and B built on images S1a never kept | Sufficiency-hazard factorial on fixed requests; closed loop deferred; A0 run as an orx cpu-doctor; registration v1 drafted | reviewed in wave 1 |
| 1 (2026-10-11) | 58 (58, 62) | Stage B's pooled steps 1-8 estimands against step-1 onset (205 of 226); the step-kick model contradicts M; caps underpriced; novelty delta published for training nondeterminism | recorded; triad 3 of 3 refuted; honest exit on the query budget; D75 ordered one repair | row `22639b76...` |
| D75 repair (2026-10-11) | not scored | as wave 1 | Onset-step 2^3 factorial (226 step-1 pairs, step 2 secondary) with VAL against the closed loop; two-stage model validated on S1a; caps repriced from S1a's realized costs with simulated loaded passes; P0, replay and open-loop drivers built and CPU-tested; full-label clock box; adjacent field read and credited | awaiting this run's blind critic, triad and reviewers |

## Deterministic Doctor Output

«P:DOCTOR_OUTPUT»
