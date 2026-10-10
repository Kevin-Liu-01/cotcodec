# Research Direction: C3 Stage-0 gate, held-out decodability of a linear answer-token selector in thinking mode and the contested-question share on disjoint draws (backfill C3)

**Status:** draft for gauntlet wave 1 (program decision D64); synthesis by the single owner on 2026-10-10 from four independent discovery cells (frontier, kill-shot, cross-domain, asset and cost) of workflow gauntlet-c3-wave1; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/c3-selection-allocation-gate-v1.md` is a DRAFT, not frozen or admitted, with no ledger row; no executable pilot exists for this gate; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design, simulations and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-10
**Coverage limits:** orx 0.2.2 only for literature search (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18; alphaXiv indexing lags by 2 to 3 days, newest ids seen 2610.12xxx dated 2026-10-08), the OpenReview search API until it began returning a browser challenge (12 searches; full texts and per-note pages are behind a bot-check page and were not bypassed, so every OpenReview item is abstract-only, UNVERIFIABLE_ACCESS for full text), 10 web searches (5 restricted to aclanthology.org or openreview.net; the Anthology's own index was not queried), the OpenAlex API with an ACL venue filter (2 searches), arXiv abstract pages and version histories via arxiv.org and export.arxiv.org, the Hugging Face model, dataset and datasets-server APIs, and repository evidence; 127 counted orx discover queries (frontier 45, kill-shot 39, cross-domain 31, asset 12, synthesis 0) and 94 paper reads by the cells (frontier 47, kill-shot 17, cross-domain 20 including 4 OpenAlex metadata records, asset 10 including 2 skims; `orx paper --full` by targeted section), plus 7 synthesis re-reads of texts the cells had fetched; not searched: Semantic Scholar and the arXiv API (unreachable from the development Mac; the host relay was not used while Q2 S1a jobs 1062 and 1064 were running), citation-graph traversal beyond OpenAlex, patents, X, Reddit, Hacker News, Chinese-language venues; classical statistics sources (Efron 2016, Obuchowski 1997, Andrews et al., Cawley and Talbot 2010, Roberts et al. 2016, Kapoor and Narayanan 2023, Hadad et al. 2021, Howard et al. 2021, Hoefler and Belli 2015) were read as OpenAlex abstracts only; Gelman's interaction-sample-size post is first-party and its page returned HTTP 403; full texts were read by targeted section, not end to end.
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-c3-selection-allocation-gate/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED (all three novelty-bearing cells; none returned OCCUPIED).
It is narrower than the dossier stated. The selector arm (a learned
hidden-state selector on Qwen3-8B in thinking mode) and the "one shared
internal signal for ranking and for compute control" recipe are already
published under token or latency accounting (TrajSelector, HSRM, DeepConf,
STEP, ZIP-RC, MARS; below). This proposal claims no method novelty for the
gate. Its residual is a measurement: whether a linear answer-token gate
transfers to a thinking model under family-grouped holdout, and what it adds
over free output signals, read as a go/no-go precondition for a later 2x2
study that needs its own gauntlet.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. The
gate's own compute (registered caps summing to at most 8.0 GPU-h, central
about 4 GPU-h) is separate and runs only after a freeze. No host job was run
for this proposal.

## Scope and what changed from the dossier

This proposal covers only C3's Stage-0 precondition gate: held-out,
family-grouped decodability of a CASE-style linear selector on a thinking-mode
model, and the difficulty spread measured on draws disjoint from any fit.
The 2x2 factorial (learned selector crossed with an adaptive per-question
re-attempt policy, scored at matched measured GPU-seconds against a tuned
longer single pass) is out of scope and needs its own gauntlet; it is over
8 GPU-h, so its admission is Kevin's under D24 whatever its score.

The four cells were merged by mechanism, not by wording. Thirteen mechanisms
change the gate as the dossier wrote it (`program/evidence/2026-10-06/question-dossier.md`, section 9).
Each row was re-checked by synthesis, by simulation (S1, `compute/gate-sim.py`),
by a cost model calibrated on repository measurements (S2,
`compute/cost-model.py`), by a full-text re-read, or by more than one of these.

| # | Mechanism (cells that found it) | What it does to the dossier's gate | Where handled |
|---:|---|---|---|
| M1 | **The spread statistic measures binomial noise.** With k draws, "share of questions with empirical pass rate in [0.1, 0.9]" is non-monotone in true heterogeneity: a pool where every question has p = 0.957 passes the 20% line, and a pool where allocation helps most fails (kill-shot and cross-domain cells, derived independently). Synthesis adds an identification result: the corrected target, the share of questions whose TRUE pass rate is in [0.1, 0.9] (pi_mid), is not identified from six draws. Its sharp population bounds are [0.105, 0.501] for a pool with pi_mid = 0.233 and [0.165, 0.611] for pi_mid = 0.328, and the EM path to the binomial-mixture NPMLE moves pi_mid from 0.387 to 0.287 between 100 and 10,000 iterations (S1, section `identification`) | The dossier's literal statistic and its corrected target both fail as decision quantities. The registered spread line is an identified replacement with the same purpose: the contested share kappa6, the share of held-out questions whose six draws have 2 to 4 correct (an unbiased estimator of the probability that six fresh draws are contested). Its line 0.10 corresponds to pi_mid ≈ 0.18 to 0.21 whenever in-band mass is spread across the band (ratio kappa6 / pi_mid 0.48 to 0.56 in every simulated shape of that kind). The raw dossier statistic and the pi_mid identified set are reported beside it | S1; registration "Lines and decision rules" |
| M2 | **Pooled decodability is trivially high, and AUC is not selection gain.** Trace length alone gives pooled AUROC 0.838 to 0.929 on Qwen3 thinking traces; question-only forecasts come within 0.041 AUROC of answer-time confidence; on Qwen3-8B thinking at k = 8, none of 280 confidence-weighted combinations beat majority voting; a calibrated post-CoT probe ties voting as a selector (kill-shot, frontier, cross-domain cells) | Primary decodability is CASE's within-question AUC, leakage-free by construction. A new floor line requires the hidden-state gate to beat a pre-declared output-only floor (lengths, token log-probabilities, entropy, the answer's vote share). Selection gain over voting is measured, with a HARM stop. S1 shows why: under thinking-mode error concentration, CASE's argmax rule loses 2.0 to 5.3 points to voting at within-question AUC 0.60 and breaks even only near 0.66 to 0.76, while a gate-weighted vote gains 0.3 to 0.8 points there | S1 sections D, F, G; registration lines D, F, H |
| M3 | **Choosing the probe layer by held-out AUC is a winner's curse** aimed at the 0.60 line (cross-domain cell: Cawley and Talbot 2010; exact-null routing probes, 2609.38956; self-improvement loops, 2610.09239) | Layer (grid of 9) and regularisation (3 values) are chosen by family-grouped cross-validated log loss inside training families only; held-out AUC is computed once for the chosen pair. CASE's own rule (C = 1.0 at the layer maximising out-of-fold within-question AUC) is a secondary, restricted to training families | Registration "Gate fitting" |
| M4 | **Every interval must be family-clustered** (cross-domain cell: Obuchowski 1997; exceedance design effect 2608.21262) | 90% percentile intervals from a family-cluster bootstrap (B = 2,000) for every line; S1 measured 0.83 to 0.91 coverage for the contested share at nominal 0.90 with about 50 families, disclosed as slightly liberal | S1; registration "Statistics, sample sizes and simulation" |
| M5 | **Leakage routes** (dossier; CASE Sec. 6.1; cross-domain cell: blocked CV, leakage taxonomy) | Families are connected components over provenance links (contest instance or source competition) and near-duplicate links across all sources; split 50/50 by family, stratified by stratum; question- versus family-grouped pooled-AUC gap reported; within-question label-permutation null and a prompt-only probe as instrument gates; a near-duplicate audit with zero cross-split links required | Registration "Data" and "Lines and decision rules" (I3 to I5) |
| M6 | **Cost scales with the second moment of trace length, and the dossier's 6 GPU-h is unmeasured** (all four cells). Probe v2 measured Qwen3.5-9B (hybrid, about 4.4x less KV per token) in a prefill-heavy regime; real-weight Qwen3-8B has never run on this host; Qwen3-8B's AIME sequences average about 17.2k tokens (mean peak KV, prompt included; 2610.05685 Table 13) | Cost model S2 calibrated on probe v1 job B (dummy-weight Qwen3-8B on this host): N = 800 questions x 6 draws is admissible under 8 GPU-h of caps only up to a mean thinking length of about 6,300 tokens, and any N of at least 560 only up to about 7,700 (CV 0.75). A 1.0 GPU-h pilot P0 on training families measures lengths, contestedness and throughput first; a registered rule then sets the workload and N; if no admissible workload exists the gate is INFEASIBLE, not cut | S2; registration "P0 pilot" and "Workload and N rule" |
| M7 | **GPU-seconds under batching are not token counts** (kill-shot and cross-domain cells: serial versus batched N = 8 differs 4.6x to 4.9x in energy, 2609.19499; token attribution is off by 0.44 to 0.46 normalized L1 from measured Shapley shares, 2608.00026; cost follows the largest KV footprint, 2608.02244; STEP: about 40% of latency is KV-saturation waiting) | Ground truth is whole-job GPU-seconds from `scontrol` for every job, failed or not; one fixed engine configuration; the extraction (HF prefill) job charged once; engine step statistics logged to fit a per-trace cost function for the later 2x2, with its residual against whole-job totals reported | Registration "GPU-second accounting rule" |
| M8 | **Novelty narrowed further** (frontier and kill-shot cells) | The gate claims no method novelty; the 2x2's residual is the interaction under measured GPU-seconds, out of scope here | Closest Prior Work; Novelty Ledger |
| M9 | **Stored i.i.d. draws are a valid accuracy instrument when decide and evaluate are disjoint** (cross-domain cell: Li et al. replay theorem, Holdout Best-of-N, Bae's own split estimand d_split) | Corrects the dossier's correction (6): replay is biased only when the same draws decide and evaluate. The gate's k = 1 to 6 accuracy curves use prefix consumption of the stored draws in random draw order; the later 2x2 can use stored per-question streams for accuracy and needs live runs only for GPU-seconds | Registration "Reported regardless of outcome" |
| M10 | **Data rights and contamination** (asset cell) | Public repository holds problem ids, revisions, statement hashes, labels and metrics only; NC-licensed and gated sets excluded; memorisation probes on every question, reported as a sensitivity; no clean date window exists among permissive sources (all predate Qwen3-8B's 2025-04-27 release), disclosed | Safety section; registration "Data" |
| M11 | **Qwen3-8B weights are not on the host** (asset cell: metadata receipt only; the registry says no weight download is planned) | A registry amendment, a 16.38 GB safetensors fetch with a full receipt under D1, and a smoke job are prerequisites; the fetch is a host action and waits for S1a | Compute section |
| M12 | **"A tuned longer single pass dominates" is not supported for thinking models** (kill-shot: parallel beats sequential for large reasoning models, 2604.05868; SEVRA's longer pass matched selective verification in tokens) | Out of scope (2x2). Recorded for the 2x2 gauntlet: the longer-pass arm's budget is a selection subject to the winner's curse (2608.12150) | Negative-Result Value |
| M13 | **The 2x2's interaction needs about 16x the sample of a main effect** (cross-domain cell: at 1,200 held-out questions the 80%-power MDE is 5.6, 4.3 and 3.1 points at between-arm correlation 0.5, 0.7 and 0.85, before family clustering; reproduced in S1) | The gate reports the inputs (per-arm variances, between-arm correlations on shared draws, family design effect) for the 2x2's power gate; GO does not certify that power | Registration "Reported regardless of outcome" |

Five corrections to the frozen dossier, recorded here because the dossier is
not edited:

1. "Either is publishable as a negative transfer of CASE or Bae": a spread
   failure is not a negative transfer of Bae. Bae's spread is the standard
   deviation of instance shift severity, built by composing the workload
   ([2609.27917](https://arxiv.org/abs/2609.27917), Sec. 3, 2026-08-21), a
   different statistic for a different problem class (kill-shot cell,
   confirmed in the full text).
2. "Replaying stored pools to decide and evaluate allocation is biased": true
   only when the same draws decide and evaluate. Bae's own split estimand
   gives 0.457, 0.015 and -0.512 percent with intervals covering zero
   ([2608.13087](https://arxiv.org/abs/2608.13087), Sec. II-E and Table I,
   2026-08-13; cross-domain cell).
3. "AUC 0.60": CASE's threshold is fitted on the medium-difficulty bin of
   non-thinking models generating up to 512 new tokens; its cluster-bootstrap
   interval is [0.562, 0.596], and CASE itself treats AUC 0.55 to 0.65 as
   indeterminate and says the value "is measured, not derived"
   ([2608.17124](https://arxiv.org/abs/2608.17124), Prop. 2, Sec. 5 and
   Sec. 6.4, 2026-08-17; re-read by synthesis).
4. "First experiment (6 GPU-h)": unmeasured. It corresponds to MATH-level
   traces (about 5k tokens), where Qwen3-8B scores 97.4 on MATH-500
   ([2505.09388](https://arxiv.org/abs/2505.09388), Table 17, 2025-05-14) and
   the spread line would likely fail by construction; at a mean of 12,000 to
   17,000 tokens a trace costs about 5 to 8.4 times one at 5,000 (S2's
   per-trace cost P·L + L²/2 at CV 0.75 with the 32,768-token cap).
5. "Problems split by family (~600 training, ~400 held-out)" left family
   undefined. For the sources available under permissive licences, family is
   registered as a connected component over provenance and near-duplicate
   links (registration "Data").

## Claim and Research Question

**Question.** For Qwen3-8B (revision
`b968826d9c46dd6066d109eabc6255188de91218`, Apache-2.0,
[model page](https://huggingface.co/Qwen/Qwen3-8B)) in thinking mode at its
recommended sampling (T 0.6, top-p 0.95, top-k 20, up to 32,768 generated
tokens), on a registered competition-mathematics workload, four quantities
decide whether C3's 2x2 study can be informative:

1. **D, decodability.** Does a linear gate on the answer-token residual state,
   fitted only on training families, rank each held-out question's own six
   draws by correctness with a within-question AUC of at least 0.60 (the
   dossier's line)?
2. **F, increment over free signals.** Does that gate beat an output-only
   floor (lengths, token log-probabilities and entropy, the answer's vote
   share), fitted by the same protocol, on the same held-out draws?
3. **S, contested share.** Do at least 10% of held-out questions have
   contested six-draw pools (2 to 4 correct), the identified image of the
   dossier's "20% with pass rate in [0.1, 0.9]"?
4. **H, harm.** Is a gate-weighted vote not worse than plain majority voting on
   held-out questions at six draws?

The variable is the answer-fusion signal (hidden-state gate, output-only
floor, the two combined, prompt-only control), fitted and scored under one
family-grouped protocol on one set of draws.

**Claim scope.** A precondition measurement on one frozen model and one
registered workload. Not `architecture-causal`, not a method claim, and no
claim about whether selection and allocation stack. The only claims it can
license are of the forms "on this workload, a linear answer-token gate does
(not) rank Qwen3-8B's thinking-mode answers within question above the line on
held-out families", "(does not) add over free output signals", "the workload
has (no) affordable room for re-attempts", and "the C3 2x2 may (may not)
enter its own gauntlet".

**Hypothesis under test (H_gate).** L90(D) ≥ 0.60, L90(F) above 0,
L90(S) ≥ 0.10, and U90(H) ≥ 0, where L90 and U90 are the lower and upper
ends of 90% family-cluster bootstrap intervals. Each clause has a registered
failure (Mechanism section).

## Strategic Fit and Why Now

C3 is item 5 of the backfill queue (`program/backlog.md`). D64 put it ahead of
C5 because C5's first experiment (about 47 GPU-h) is over 8 GPU-h and needs a
D24 ruling, while C3's Stage-0 gate is meant to fit under 8 GPU-h and so is
actionable within the program. Two discovery results sharpen why the gate is
worth running before anything larger:

- **Conflicting priors on the selector.** Trained hidden-state selectors beat
  majority voting on Qwen3 thinking models (TrajSelector +4.61 points at
  Best-of-32 on Qwen3-8B, 2510.16449; HSRM within-problem AUROC 0.736 and
  0.884 on Qwen3-1.7B and 4B, 2608.30841), while confidence-weighted voting,
  a prompted Yes/No probe and a learned six-signal combination do not
  (2609.32035, Qwen3-8B thinking at k = 8 and 32,768 tokens), and a calibrated
  post-CoT probe only ties voting (2609.33290). The linear CASE gate sits
  between these. Which side it falls on decides whether a 2x2 with a learned
  selector is worth 30 to 40 GPU-h.
- **Feasibility is the binding constraint.** Contested questions are the long,
  expensive ones. S2 shows the gate fits under D20's 8 GPU-h line only on a
  workload whose mean thinking length is at most about 7,700 tokens. Whether
  such a workload with enough contested questions exists is itself the answer
  the 2x2 needs, and the gate measures it for at most 1.25 GPU-h of pilot
  before committing the rest.

Every stopping outcome is informative on its own (Negative-Result Value), so
the gate's value does not depend on the 2x2 ever running. The competing
frontier is moving fast: eleven of the priors named under Closest Prior Work
appeared since June 2026, and five sources this design relies on appeared in
the ten days before the cutoff (2610.02808, 2610.05685, 2610.08544,
2610.08719, 2610.09239).

## Primary-Source Evidence

Every row was opened by a discovery cell or by synthesis. "Full" means `orx
paper --full` text read by targeted section; "abstract" means abstract only.
First-party marks a number not independently replicated. Claim ids are the
Citation doctor's registry (`doctors/citation.json`). Synthesis re-read rows
C01 to C05, C11 and C22 in the cells' saved full texts.

| id | Claim used here | Source | Date | Read | Status |
|---|---|---|---|---|---|
| C01 | Linear gate (per-feature standardisation, L2 logistic, C = 1.0) on the answer-token residual state; 5-fold GroupKFold by question; decodability = mean within-question AUC over mixed questions, leakage-free by construction; threshold near 0.60 on the medium bin, zero-crossing 0.58, cluster-bootstrap interval [0.562, 0.596], band 0.55 to 0.65 indeterminate; "no useful threshold" in the hard regime; models Qwen2.5 1.5B to 14B, Llama-3-8B and medical models, up to 512 new tokens; MATH-500 medium-bin AUC 0.763 and 0.789 | [2608.17124](https://arxiv.org/abs/2608.17124) Secs. 3.2-3.4, Prop. 2, Secs. 5, 6.4, 6.7, Table 6 | 2026-08-17 (v1) | full (frontier, kill-shot, asset, cross-domain, synthesis) | verified |
| C02 | Hidden-state reward model (2-layer encoder, about 2M parameters) on frozen Qwen3; thinking mode, answer-only extraction after the end-of-thinking boundary: within-problem AUROC 0.736 (1.7B) and 0.884 (4B) on MATH-500, against 0.669 and 0.672 with full-trace extraction; best-of-8 on a problem-disjoint split | [2608.30841](https://arxiv.org/abs/2608.30841) Secs. 4.1-4.4, 6.6, Table 2 | 2026-08-31 (v1) | full (frontier, synthesis) | verified; first-party |
| C03 | Qwen3-8B and 32B, k = 8, T 0.6, top-p 0.95, 32,768 tokens; across 280 method-dataset-model combinations none beats majority voting after Holm correction; weighted voting agrees with voting on 98.5% of problem-method pairs; a learned six-signal selector gains -0.0003 out of domain; the probe is a prompted Yes/No probe, not a trained hidden-state gate; in-domain length AUROC 0.838 to 0.929; Qwen3-8B thinking MATH-500 accuracy 0.957, truncation 0.0055; single author, under review, one seed | [2609.32035](https://arxiv.org/abs/2609.32035) abstract, Sec. 3, Table 1, Table 13, Sec. 8, Table 20 | 2026-09-25 (v1) | full (kill-shot, synthesis) | verified; first-party |
| C04 | Post-CoT hidden-state probe on Qwen3-14B and Ministral-3-8B-Reasoning is well calibrated but as a selector nearly ties voting (TriviaQA, N = 32: Max-Probe 0.778, majority vote 0.771, oracle 0.879) | [2609.33290](https://arxiv.org/abs/2609.33290) Sec. 3.3, Fig. 2b | 2026-09-27 (v1) | full (frontier, kill-shot; synthesis checked the locator) | verified; factual QA only |
| C05 | Qwen3-8B thinking trajectories scored by a 0.6B step scorer on hidden states; trained on OpenR1-Math-220k and DeepMath-103K; +4.61 over majority voting at Best-of-32 on six competition sets | [2510.16449](https://arxiv.org/abs/2510.16449) abstract, Sec. 4, main table | 2025-10-18 (v1) | full (frontier; synthesis checked) | verified; first-party |
| C06 | One model-internal confidence signal filters and weights traces and drives consensus-based adaptive sampling; Qwen3-8B among models; Qwen3-32B at Cons@512 on AIME25 used 2.43e8 tokens for 30 problems | [2508.15260](https://arxiv.org/abs/2508.15260) Secs. 3.2-3.3, Table 2 | 2025-08-21 (v1) | full (frontier, kill-shot) | verified |
| C07 | Hidden-state step scorer prunes traces during generation and weights the vote; thinking models; measured end-to-end latency 45 to 70% below self-consistency on one GH200; about 40% of parallel-scaling latency is waiting from KV saturation and preemption | [2601.09093](https://arxiv.org/abs/2601.09093) Secs. 3, 4, 5.1, Table 1 | 2026-01-14 (v2 2026-04-28) | full (kill-shot) | verified |
| C08 | Reserved logits predict final reward and remaining length; one signal drives selection and adaptive spawning and pruning; Qwen3-1.7B reasoning; normalized FLOPs and a best-case latency proxy | [2512.01457](https://arxiv.org/abs/2512.01457) Sec. 6.1, Table 2 | 2025-12-01 (v4 2025-12-23) | full (frontier, kill-shot) | verified |
| C09 | Margin-adversarial stopping saves 25 to 47% of self-consistency tokens, and 14 to 29% on top of DeepConf Online, at matched accuracy | [2606.12935](https://arxiv.org/abs/2606.12935) abstract, Fig. 1 | 2026-06-11 (v1) | full (frontier, kill-shot) | verified; tokens, not GPU time |
| C10 | A latent probe predicts per-sample budgets, crossed with majority voting, a reward model and an oracle, with wall-clock latency and memory measured in vLLM | [2601.21619](https://arxiv.org/abs/2601.21619) Secs. 2.1, 5.1 | 2026-01-29 (v2 2026-05-09) | full (kill-shot) | verified |
| C11 | Fuzzy per-query sample-budget controller with a fixed self-certainty plus Borda selector and a selector-matched fixed N = 8 control; Phi-3-mini and Qwen2.5-1.5B, 256 output tokens; cost in samples | [2608.03961](https://arxiv.org/abs/2608.03961) Sec. 5, App. E.1 Table 5 | 2026-08-04 (v1) | full (frontier, kill-shot, asset; synthesis checked Sec. 5) | verified |
| C12 | Fixed-pool decomposition of selector net gain into recoverable mass, signal coverage, conditional selection quality and harm | [2607.17531](https://arxiv.org/abs/2607.17531) abstract | 2026-07-20 (v1) | full (frontier, kill-shot) | verified |
| C13 | Full generation-plus-verification entry fee; none of 12 adaptive-depth policies beats uniform compute (video world models) | [2609.13257](https://arxiv.org/abs/2609.13257) abstract | 2026-09-06 (v1) | full (frontier, kill-shot, asset) | verified |
| C14 | Allocation decided and scored on the same stored samples: 2.2 to 2.6% gain; decided and scored on disjoint halves: 0.457, 0.015, -0.512% with intervals covering zero (TSP solvers) | [2608.13087](https://arxiv.org/abs/2608.13087) Secs. II-D, II-E, Tables I-III | 2026-08-13 (v1) | full (all three novelty cells) | verified |
| C15 | Spread is the standard deviation of shift severity over a reference group, set by workload composition (TSP) | [2609.27917](https://arxiv.org/abs/2609.27917) Secs. 1.2, 3, 4 | 2026-08-21 (v1) | full (frontier, kill-shot, asset) | verified |
| C16 | On Qwen3-4B, an 8,192-token initial solve matches selective verification with fewer realized tokens; latency not measured | [2606.19808](https://arxiv.org/abs/2606.19808) Sec. 6.1 | 2026-06-18 (v1) | full (frontier) | verified; tokens only |
| C17 | Large reasoning models do better with parallel than with sequential sampling, attributed to less exploration under sequential conditioning | [2604.05868](https://arxiv.org/abs/2604.05868) abstract | 2026-04-07 (v1) | full (frontier) | verified |
| C18 | Hidden-state MLP probe predicts marginal reward per budget and drives adaptive best-of-k with an offline binned allocation | [2410.04707](https://arxiv.org/abs/2410.04707) Sec. 3.1 | 2024-10-07 (v1) | full (frontier, kill-shot) | verified |
| C19 | Constrained per-query allocation (Lagrangian oracle then classifier) with majority voting only | [2604.14853](https://arxiv.org/abs/2604.14853) abstract, Sec. 5 | 2026-04-16 (v1) | full (frontier) | verified |
| C20 | Eight serial calls versus one batched call at N = 8: 4.64 to 4.86x GPU energy, 5.77 to 6.12x P95 latency (A100, HF generation, small models) | [2609.19499](https://arxiv.org/abs/2609.19499) abstract | 2026-09-16 (v2 2026-09-19) | full (frontier, kill-shot) | verified; magnitude under vLLM continuous batching unknown |
| C21 | Attention and memory access, not parameter FLOPs, dominate test-time scaling cost | [2506.05333](https://arxiv.org/abs/2506.05333) abstract | 2025-06-05 (v3 2025-06-20) | abstract (kill-shot) | verified at abstract level |
| C22 | Qwen3-8B on AIME24+25 at full KV: mean peak KV 2.53 GB per sequence including the prompt (about 17.2k tokens at 147,456 B per token), pass@1 69.8%, 10.2% of samples capped at 32K; on MATH500 5% hit a 16K cap | [2610.05685](https://arxiv.org/abs/2610.05685) Tables 10, 11, 13 | 2026-10-05 (v2 2026-10-07; the version alphaXiv served to the asset cell is not recorded) | full (asset; synthesis checked) | verified; first-party |
| C23 | Qwen3 thinking-mode evaluation settings; Qwen3-8B MATH-500 97.4, AIME'24 76.0, AIME'25 67.3 | [2505.09388](https://arxiv.org/abs/2505.09388) Sec. 4, Table 17 | 2025-05-14 | full (asset) | verified; first-party |
| C24 | A question-only forecast comes within 0.041 AUROC of answer-time confidence | [2609.34864](https://arxiv.org/abs/2609.34864) abstract | 2026-09-28 (v1) | full (kill-shot) | verified |
| C25 | A token-margin signal separates correct from incorrect pooled across questions (+0.0604) but not paired within problems (-0.0168, interval crossing 0), preregistered | [2608.11403](https://arxiv.org/abs/2608.11403) abstract, Sec. 1 | 2026-08-11 (v2 2026-08-15) | full (kill-shot) | verified |
| C26 | A probe score should be read against a floor of simple inputs and a ceiling; the headroom is the evidential range | [2610.08544](https://arxiv.org/abs/2610.08544) abstract, Sec. 4.1 | 2026-10-06 (v1) | full (cross-domain) | verified |
| C27 | Under an exact label null, a width-matched MLP routing probe reported gains in 308 of 600 evaluations; a linear comparison reported none; selecting by validation log loss removed false detections | [2609.38956](https://arxiv.org/abs/2609.38956) abstract | 2026-09-30 (v1) | full (cross-domain) | verified; first-party |
| C28 | Selection-set score beat held-out accuracy by 13 to 20 points with 16 items and by 1 to 5 points with 256 | [2610.09239](https://arxiv.org/abs/2610.09239) abstract | 2026-10-07 (v1) | full (cross-domain) | verified; first-party |
| C29 | For exchangeable candidates a uniform subset of a stored pool has the law of the first N generated; selection by a noisy score is unbiasedly evaluable iff selection and evaluation use disjoint score columns | [2610.08719](https://arxiv.org/abs/2610.08719) Sec. 2, abstract | 2026-10-06 (v1) | full (cross-domain, frontier) | verified |
| C30 | Replay evaluation is unbiased for i.i.d. events under uniform logging (Theorem 1) | [1003.5956](https://arxiv.org/abs/1003.5956) Sec. 3.1 | 2010-03-31 (v2 2012-03-01) | full (cross-domain) | verified |
| C31 | Token-proportional energy attribution differs from measured Shapley attribution by 0.440 (static) and 0.458 (continuous batching) normalized L1 | [2608.00026](https://arxiv.org/abs/2608.00026) abstract | 2026-07-11 (v1) | full (cross-domain) | verified; first-party |
| C32 | In batched decoding a step's wall-clock cost is governed largely by the largest active KV footprint | [2608.02244](https://arxiv.org/abs/2608.02244) abstract, Sec. 1 | 2026-08-03 (v1) | full (cross-domain) | verified |
| C33 | Qwen3-14B dense decode at batch 32 on H100: about 72% SM busy while only half of each m64 fragment holds real rows | [2609.12923](https://arxiv.org/abs/2609.12923) abstract | 2026-09-11 (v1) | full (cross-domain) | verified; first-party |
| C34 | Variance of a below-threshold fraction over clustered data is inflated by 1+(m-1)rho_I | [2608.21262](https://arxiv.org/abs/2608.21262) abstract, Sec. 1.2 | 2026-08-21 (v2 2026-10-01) | full (cross-domain) | verified; single author |
| C35 | Varying the generation budget gives 3 to 19% non-monotone items and reverses model rankings | [2608.12150](https://arxiv.org/abs/2608.12150) abstract | 2026-08-12 (v1) | full (cross-domain) | verified |
| C36 | Probes on reasoning-model hidden states verify intermediate answers; pooled ROC-AUC above 0.9 on AIME for R1-Distill-Qwen-32B; early exit cuts 24% of tokens | [2504.05419](https://arxiv.org/abs/2504.05419) abstract, Sec. 4 | 2025-04-07 (v1) | full (frontier, asset) | verified; pooled AUC |
| C37 | Latent-trajectory signals predict correctness on reasoning models and drive sequential early acceptance, up to 70% fewer tokens than voting | [2510.10494](https://arxiv.org/abs/2510.10494) abstract, Sec. 5 | 2025-10-12 (v1) | full (frontier) | verified |
| C38 | Interaction-aware identification of adaptive verifier routing: apparent adaptive gains belong to the verifier-set coordinate | [2610.02808](https://arxiv.org/abs/2610.02808) abstract, Table 6 | 2026-10-02 (v1) | full (frontier) | verified |
| C39 | Realized-maximum gap of verifier-triggered resampling falls inside an exact exchangeable-action null | [2607.08665](https://arxiv.org/abs/2607.08665) abstract | 2026-07-09 (v3 2026-09-02) | full (frontier) | verified |
| C40 | 1,403,520 released sampled attempts, including Qwen3-30B-A3B-Thinking banks with 80 responses per question for some sets | [2608.04001](https://arxiv.org/abs/2608.04001) abstract | 2026-08-04 (v2 2026-08-31) | full (frontier) | verified; banks' licence not checked |
| C41 | Comparisons along realized cost and at the same cap disagree; a log-probability selector loses accuracy while coverage rises (19,200 public traces) | [2609.38699](https://arxiv.org/abs/2609.38699) abstract | 2026-09-30 (v1) | full (frontier) | verified |
| C42 | A budget read off a best-of-k curve after looking needs a simultaneous band | [2609.40190](https://arxiv.org/abs/2609.40190) abstract | 2026-09-30 (v1) | full (frontier) | verified |
| C43 | Within-query ranking metrics average over pairs while selection depends on the maximum; exact decomposition of selection loss (ICLR 2027 submission) | [OpenReview RJtxGvLeYP](https://openreview.net/forum?id=RJtxGvLeYP) | 2026-09-17 | abstract (OpenReview API search) | UNVERIFIABLE_ACCESS full text |
| C44 | Selector-agnostic nonparametric early stopping matches fixed-budget accuracy with 42 to 73% fewer samples across selectors (ICLR 2027 submission) | [OpenReview X7X1K0xfZe](https://openreview.net/forum?id=X7X1K0xfZe) | 2026-09-19 | abstract | UNVERIFIABLE_ACCESS full text |
| C45 | With answer identity fixed, two correctness probes order 93 and 95% of pairs, yet incorrect answers outrank correct answers from other problems in about a third of cross-problem comparisons (ICLR 2027 submission) | [OpenReview ND39qPOQ0h](https://openreview.net/forum?id=ND39qPOQ0h) | 2026-09-14 | abstract | UNVERIFIABLE_ACCESS full text |
| C46 | Continuation and answer selection over trajectories benefit from different evidence (ICLR 2027 submission) | [OpenReview BLOx9TYfgl](https://openreview.net/forum?id=BLOx9TYfgl) | 2026-08-26 | abstract | UNVERIFIABLE_ACCESS full text |
| C47 | Failure-aware routing on GPQA with Qwen3-32B: 54.5% to 58.7% with 51 verifier calls; advantage over runner-up-share allocation not established (ICLR 2027 submission) | [OpenReview SId4cvKz6D](https://openreview.net/forum?id=SId4cvKz6D) | 2026-09-11 | abstract | UNVERIFIABLE_ACCESS full text |
| C48 | Confidence-based evidence sufficiency replaces count-based stopping in adaptive self-consistency (Findings of ACL 2026) | [2026.findings-acl.1085](https://aclanthology.org/2026.findings-acl.1085/) | 2026 | abstract via web search | not read in full |
| C49 | Qwen3-8B revision b968826d: Apache-2.0, created 2025-04-27, 36 layers, 8 KV heads, head_dim 128, max_position_embeddings 40,960, untied embeddings; five safetensors shards totalling 16,381,516,776 B; card recommends T 0.6, top-p 0.95, top-k 20, min-p 0 for thinking and warns against greedy decoding | [model page](https://huggingface.co/Qwen/Qwen3-8B), config, generation_config and tree at the revision | 2026-10-10 (read) | HF API (synthesis) | verified |
| C50 | Dataset licences and fields: Omni-MATH Apache-2.0 card, 4,428 problems, fields domain, difficulty (1.0 to 9.5), source (67 values; HMMT_2 1,385 and HMMT_11 896); OlympiadBench Apache-2.0 card, OE_TO_maths_en_COMP 674 problems; EleutherAI/hendrycks_math MIT card; AI-MO validation AIME (90) and AMC (83) Apache-2.0 cards with AoPS URLs; DeepScaleR MIT card without source or year fields; MathArena sets CC-BY-NC-SA-4.0; Big-Math gated | [Omni-MATH](https://huggingface.co/datasets/KbsdJames/Omni-MATH), [OlympiadBench](https://huggingface.co/datasets/Hothan/OlympiadBench), [hendrycks_math](https://huggingface.co/datasets/EleutherAI/hendrycks_math), [aimo-validation-aime](https://huggingface.co/datasets/AI-MO/aimo-validation-aime), [aimo-validation-amc](https://huggingface.co/datasets/AI-MO/aimo-validation-amc) | 2026-10-10 (read) | HF API and datasets-server (asset, synthesis) | verified; compilation licences only |
| C51 | Serving probe v1 job B (Slurm 446) on this host: Qwen3-8B config, DUMMY weights, 0.9 memory utilisation, max_model_len 32,768: weights 15.27 GiB, KV 53.34 GiB = 388,384 tokens; 4,346 to 4,391 tok/s at 64 sequences (1,152 in, 4,096 out), 2,339 tok/s at 32 (8,192 out), 3,438 at 64 (4,096 in), 1,083 at 24 (16,384 in, 8,192 out) | `program/evidence/2026-10-07/serving-throughput-probe-v1/` (README, jobs/b-446/probe/points) | 2026-10-07 | repository evidence | measured; dummy weights |
| C52 | Serving probe v2 job A (Slurm 466): Qwen3.5-9B real weights, multimodal prefill-heavy, output 756.9 tok/s at concurrency 16 and 946.0 at 40, thinking replay 581.3 tok/s; KV 1,634,030 tokens; engine ready 104 s; 0.4731 GPU-h | `program/evidence/2026-10-07/serving-throughput-probe-v2/` | 2026-10-07 | repository evidence | measured; different model and regime |

## Closest Prior Work

Ranked by closeness to the gate's measurement, not to the later 2x2.

1. **CASE: a decodability criterion predicts when hidden-state selection beats
   majority voting** ([2608.17124](https://arxiv.org/abs/2608.17124), Wang,
   Hong and Bagci, v1 2026-08-17; full text re-read by synthesis). The gate's
   mechanism is CASE's, transported. Same: a linear gate on the answer-token
   residual state, within-question AUC over mixed questions as the leakage-free
   decodability, comparison of hidden-state selection with majority voting,
   grouped evaluation. Different: CASE tests non-thinking models with outputs up
   to 512 tokens, groups by question (not by provenance family), selects the
   operating layer by maximising pooled within-question AUC on the evaluated
   data, has no output-only floor in its decision (it compares output-space
   selectors separately, Sec. 6.8), and uses argmax selection. The gate adds a
   thinking model with traces up to 32,768 tokens, family-grouped holdout,
   layer selection by grouped log loss inside training families, a floor
   increment line, a gate-weighted vote, and a measured cost. CASE is the
   stronger contribution; the gate is a transfer test with controls.
2. **HSRM: hidden-state reward models** ([2608.30841](https://arxiv.org/abs/2608.30841),
   Li and Zhu, v1 2026-08-31). Same: frozen Qwen3 in thinking mode,
   post-reasoning hidden states, within-problem AUROC on a problem-disjoint
   split. Different: a nonlinear encoder over step-boundary states (about 2M
   parameters) trained on 64 candidates per training problem; no family
   grouping; Qwen3-1.7B and 4B only; no floor or voting comparison in the
   thinking ablation. It makes the D line likely to pass, which is why the gate
   adds F and H.
3. **Reasoning concentrates errors, and self-consistency never notices**
   ([2609.32035](https://arxiv.org/abs/2609.32035), Althoubi, v1 2026-09-25).
   Same: Qwen3-8B thinking, k = 8, T 0.6, 32,768 tokens, signals fitted on
   MATH-500, decisions against voting. Different: output signals and a
   prompted Yes/No probe, not a trained hidden-state gate; pooled AUROCs; no
   family holdout. It is the strongest prior for a null selector arm.
4. **TrajSelector** ([2510.16449](https://arxiv.org/abs/2510.16449), v1
   2025-10-18) and **Calibration, not answer selection**
   ([2609.33290](https://arxiv.org/abs/2609.33290), v1 2026-09-27): a learned
   hidden-state selector on Qwen3-8B thinking that beats voting, and a
   calibrated post-CoT probe that does not. They bracket the gate's outcome.

Closest priors for the later 2x2, which this gate does not test: DeepConf
(C06), STEP (C07), ZIP-RC (C08), MARS (C09), LanBo (C10) and SANE (C44) already
combine an internal signal with adaptive sampling or stopping under token,
FLOP or latency accounting; 2608.03961 (C11) isolates allocation from a fixed
selector; Bae (C14, C15) motivates disjoint draws and spread; the dossier's
2607.17531 and 2609.13257 (C12, C13) frame selection headroom and the entry
fee. None of these runs a selector-by-allocator interaction contrast at matched
measured whole-job GPU-seconds on family-grouped held-out problems (frontier and
kill-shot cells).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Linear answer-token gate, within-question AUC on held-out problems | 2608.17124 (CASE) | Gate, position, metric, grouped evaluation | Thinking model with traces up to 32,768 tokens; provenance-family grouping; layer and C chosen by grouped log loss inside training families | high that the delta is real; low as novelty (a transfer test) |
| Thinking-mode within-problem decodability | 2608.30841 (HSRM) | Qwen3 thinking, post-reasoning states, within-problem AUROC, disjoint problems | Linear gate on Qwen3-8B; family holdout; floor and voting decisions | medium |
| Floor-increment line (hidden states versus free output signals, same protocol) | 2610.08544 (floors), 2609.32035 (output signals), CASE Sec. 6.8 (output selectors compared separately) | Idea of a floor; output signals as competitors | A registered go/no-go line on the paired within-question increment, with output features including the vote share | medium |
| Selection decision against voting with a HARM stop | 2608.17124, 2609.32035, 2609.33290 | Accuracy against voting | Argmax and gate-weighted vote on family-held-out questions at six draws; S1 shows argmax loses to voting near AUC 0.60 under error concentration | medium |
| Contested share kappa6 as an identified spread estimand, with the pi_mid identified set | 2609.27917 (spread by composition); cross-domain and kill-shot derivations | Spread decides whether reallocation pays | Shows the dossier's target is not identified from six draws (sharp bounds, NPMLE path dependence) and registers an unbiased replacement with a calibrated line | medium |
| Whole-job GPU-second accounting of generation plus the charged prefill, and a per-trace cost function τL + β(PL + L²/2) | 2609.19499, 2608.00026, 2601.09093 (STEP), 2506.05333 (Kinetics) | Systems cost differs from tokens | Measured on this host for Qwen3-8B thinking traffic, to calibrate the later 2x2's cost model | low as novelty (instrumentation) |

Novelty wording: No direct prior art found through 2026-10-10 under the
recorded coverage (127 counted orx discover queries listed with returned ids
in `query-log.json`: the frontier cell's FR-01 to FR-45, the kill-shot cell's
39 KS rows, the cross-domain cell's XD-00 to XD-30, the asset cell's AS-01 to
AS-12; 24 uncounted OpenReview, web and OpenAlex API searches; 94 paper
reads; the gaps in the Coverage limits line above) for a family-grouped,
held-out test of a linear answer-token correctness gate on a thinking-mode
model that is read against an output-only floor and against majority voting,
paired with an identified contested-share estimand, as a precondition for a
selector-by-allocator factorial. Queries targeting this mechanism directly
include FR-01 and KS-K6 (keyword, CASE's title phrase), FR-12 (keyword
"hidden-state probe answer correctness reasoning model best-of-N selection
held-out", after 2026-03-01), FR-16 (keyword "question-grouped split probe
leakage correctness prediction"), FR-20 (embedding "hidden-state linear probe
selects correct answer among sampled reasoning traces of thinking models,
evaluated with question-grouped splits", after 2026-01-01), FR-23 (openalex
"hidden state probe answer selection majority voting language models"),
FR-36 (keyword "hidden-state reward model within-problem AUROC thinking mode"),
KS-K23 (keyword "probe selection majority voting thinking mode Qwen3
within-question AUROC"), KS-E4 and KS-E6 (embedding: probes leaking question
identity; pooled AUROC conflating difficulty with within-question
discrimination), XD-16 (embedding, between- versus within-group
discrimination), AS-08 (embedding, linear probe on long chain-of-thought
hidden states evaluated on held-out questions) and each closest prior's title
phrase (FR-02 to FR-10, FR-27 to FR-31, FR-42 to FR-45, KS-K2 to KS-K4,
KS-K11, KS-K13, KS-K15 to KS-K17, KS-K20). They returned 2608.17124,
2608.30841, 2609.33290, 2609.37700, 2610.04512, 2609.32035, 2504.05419,
2510.16449 and others, none of which runs this combination. Synthesis made no
counted query (the cells had spent 127 of the 150, breaching the refuters'
reserve of 30 by 7) and re-read seven full texts the cells had fetched. PRISMA
counts for synthesis: 0 identified, 7 full texts re-read, 0 included as direct
prior; the frontier cell reports about 640 unique ids identified, about 110
screened by title or abstract, 47 full texts and 33 cited.

## Mechanism and Falsifiable Predictions

**Setting.** Qwen3-8B, thinking mode, chat template with the Qwen-recommended
math instruction ("Please reason step by step, and put your final answer
within \boxed{}."), six independent draws per question with per-request seeds.
For each completed draw, one teacher-forced HF forward pass over the stored
prompt and generated token ids records the residual-stream output of every
layer (embeddings plus 36 blocks) at the answer position: the token
immediately before the first token inside the last `\boxed{...}` that follows
the final end-of-thinking marker, the state from which the first answer token
is predicted (CASE Sec. 3.2). A draw with no end-of-thinking marker or no
boxed answer after it has no answer position; it counts as wrong for accuracy,
is excluded from decodability, and is reported.

**Why the gate's quantities are the right preconditions.** In CASE's model
(Prop. 1-2), the gain of hidden-state selection over voting rises with
within-question decodability and crosses zero at a threshold set by how much
better voting is than a random pick of the pool. Thinking-mode errors are more
concentrated than non-thinking ones (2609.32035 Table 1: wrong-answer collision
0.25 to 0.51 for Qwen3-8B with reasoning on), which moves the threshold for
argmax selection upward. S1 reproduces this: with a mixed-difficulty pool and
collision c² = 0.36, argmax breaks even near AUC 0.66, and near 0.76 when
errors are scattered (c² = 0.09), while a gate-weighted vote never loses more
than 0.4 points and gains up to 2.7 points over AUC 0.55 to 0.80. So
decodability above 0.60 is necessary for a useful selector arm but not
sufficient, which is why F and H join D. For allocation, re-attempts can change
the outcome only on questions whose pools are contested; kappa6 measures that
share directly and is identified, unlike pi_mid.

**Predictions and their registered falsifiers (kill criteria).**

| # | Prediction | Statistic | Falsifier (reject if) | Owner's prior |
|---|---|---|---|---|
| P1 | CASE's decodability transfers to thinking mode | D = pooled within-question AUC of the gate, held-out families | U90(D) below 0.60 → STOP_DECODE | likely pass (C01 MATH-500 0.76 to 0.79 non-thinking; C02 0.74 to 0.88 thinking with a nonlinear encoder) |
| P2 | Hidden states add over free output signals | F = D minus the floor's within-question AUC, paired | U90(F) below 0.02 → STOP_REDUNDANT; GO needs L90(F) above 0 | uncertain; length and vote share are strong within-question signals (C03) |
| P3 | The affordable workload has room for re-attempts | S = kappa6 on held-out families | U90(S) below 0.10 → STOP_SPREAD; GO needs L90(S) ≥ 0.10 | uncertain; depends on the P0 workload rule |
| P4 | The selector does not harm | H = acc(gate-weighted vote) minus acc(majority vote), k = 6 | U90(H) below 0 → STOP_HARM | unlikely to fire |
| P5 | GPU time per trace follows τL + β(PL + L²/2) | P0-calibrated model against G's whole-job GPU-seconds | absolute error above 20% of G's measured decode GPU-seconds → the 2x2 may not use a length-based cost model (reported, not a gate verdict) | likely within 20% |
| P6 | Family grouping matters little for within-question AUC and somewhat for pooled AUC | pooled AUC, question-grouped minus family-grouped | none (diagnostic); a gap above 0.05 is reported as evidence of family-level leakage in question-grouped studies | small gap |

GO = L90(D) ≥ 0.60 and L90(F) above 0 and L90(S) ≥ 0.10 and U90(H) ≥ 0,
with every instrument gate passed. GO licenses only a gauntlet for the 2x2.
Every STOP is reported with its interval; several may fire together. Anything
else is INCONCLUSIVE, with the indeterminate lines named; no further GPU work
follows inside this registration.

**What the gate cannot show.** It cannot show that selection and allocation
stack, that a longer single pass is worse, or that a selection gain of 2
points is absent (the weighted-vote gain's 80%-power MDE is about 2.0 to 2.3
points at 320 held-out questions; S1). A GO is necessary, not sufficient, for
an informative 2x2.

## Cheapest Decisive Pilot

The cheapest decisive experiment for C3's precondition is the gate itself:
smoke (cap 0.25 GPU-h), P0 (cap 1.0), and G (decode and extraction caps set by
a registered formula after P0; total caps at most 8.0 GPU-h; central about 3.6
GPU-h for 800 questions at a mean thinking length of 6,000 tokens). It is
decisive in the registered sense: S1 shows that at 320 held-out questions
(about 117 mixed) D reaches PASS with probability 0.95 at a true AUC of 0.70
and STOP with probability 0.60 at 0.54 (false PASS 0.068 and false STOP 0.047
at exactly 0.60); S reaches STOP with probability 1.00 when no question is
heterogeneous or none is in band, and PASS with probability 0.94 at
kappa6 = 0.174. The cheapest decisive experiment for feasibility is P0 alone
(at most 1.25 GPU-h with the smoke): if no admissible workload exists, the gate
ends INFEASIBLE before G spends anything.

An optional zero-GPU pre-check is available and not decision-bearing: the
released Qwen3-30B-A3B-Thinking banks (C40, 80 responses per question for some
sets) give kappa6 and the pi_mid identified set for a related thinking model
on CPU, once their licence is checked.

No executable pilot exists today. The first one would be a `kind: cpu-doctor`
orx node that runs the analysis pipeline on synthetic pools with known AUC,
floor increment and kappa6 (S1's generator) and checks that the registered
estimators recover them; the second, the smoke manifest through the Docker
submitter.

## Controls, Baselines, and Ablations

- **Output-only floor (the F line's baseline).** Per draw: log total generated
  tokens, log thinking tokens, log answer-segment tokens, mean and minimum
  sampled-token log-probability over the answer segment, mean log-probability
  over the whole trace, mean top-20 entropy over the answer segment, and the
  answer's vote share among the question's six draws. Same standardisation,
  L2 logistic and C selection as the gate. The combined model (gate features
  plus floor features) is reported.
- **Majority voting** over math-verify equivalence classes, ties broken
  uniformly at random (expected value), the H line's baseline; single draw and
  oracle pass@6 reported.
- **CASE-faithful secondary.** C = 1.0 at the layer that maximises
  out-of-fold within-question AUC inside training families, argmax selection;
  reported, not decision-bearing.
- **Length-residualised gate.** The gate score residualised on log total
  length (OLS on training families); within-question AUC reported.
- **Prompt-only control.** A probe on the last prompt-token state (identical
  across a question's draws), so its within-question AUC is exactly 0.5 by
  construction: a pipeline check (instrument gate I4); its pooled AUC and its
  question-level prediction of contestedness are reported as the
  question-identity and difficulty component.
- **Label-permutation null.** Within-question permutation of correctness labels
  (200 permutations, seed 42); mean AUC must lie in [0.48, 0.52] (I3).
- **Grouping audit.** Pooled AUC under a draw-level random split, a
  question-grouped split and the family-grouped split (CASE Sec. 6.1
  replicated).
- **Ablations (reported):** secondary answer positions (last answer token,
  closing brace, end-of-thinking marker, final token, mean of the last 16
  tokens) at layers 18 to 36; training-set learning curve at 25, 50 and 75% of
  training families; split seeds 43 and 44; memorisation-flagged questions
  excluded; benchmark-exposed sources excluded.

## Evaluation, Statistics, and Leakage Checks

**Units.** Within-question AUCs are averaged over mixed held-out questions
(at least one correct and one wrong draw with an answer position). Accuracy and kappa6 are
over all held-out questions. The resampling unit is the family.

**Intervals.** 90% two-sided percentile intervals from a family-cluster
bootstrap (B = 2,000, seed 42); each line reads one end, so each STOP is a
one-sided 5% test. GO is an intersection of four one-sided tests and needs no
multiplicity adjustment; the four STOP lines together can fire falsely with
probability at most about 0.20 (union bound), disclosed. S1 measured 0.83 to 0.91 coverage
for kappa6 at nominal 0.90 with about 50 families: slightly liberal, disclosed,
not corrected.

**Operating characteristics (S1, assumed distributions, 600 replicates per
cell, B = 1,000).**

| Line | Held-out questions | Truth | P(PASS) | P(STOP) |
|---|---:|---|---:|---:|
| D | 320 (about 117 mixed) | AUC 0.54 / 0.57 / 0.60 / 0.63 / 0.66 / 0.70 / 0.75 | 0.000 / 0.008 / 0.068 / 0.297 / 0.628 / 0.947 / 1.000 | 0.595 / 0.278 / 0.047 / 0.003 / 0 / 0 / 0 |
| D | 240 (about 88 mixed) | AUC 0.54 / 0.60 / 0.70 | 0.002 / 0.063 / 0.887 | 0.522 / 0.057 / 0 |
| F | 320 | increment 0 / 0.04 / 0.08 | 0.07 / 0.29 to 0.36 / 0.66 to 0.77 | REDUNDANT 0.14 / 0.02 / 0 |
| S (kappa6) | 320 | no heterogeneity (p = 0.957 for all) | 0 | 1.000 (the raw dossier statistic PASSES 0.39) |
| S | 320 | 60% p = 0.98, 40% p = 0.04 | 0 | 1.000 (raw STOP 0.71) |
| S | 320 | pi_mid 0.233, in-band mass at the band's top edge (kappa6 0.064) | 0 | 0.763 (raw PASS 0.70) |
| S | 320 | pi_mid 0.138 / 0.185 / 0.233 / 0.25 / 0.328 (kappa6 0.074 / 0.098 / 0.124 / 0.141 / 0.174) | 0 / 0.037 / 0.25 / 0.52 / 0.94 | 0.455 / 0.08 / 0.005 / 0.002 / 0 |
| H (weighted vote) | 320 | AUC 0.55 to 0.80, collision 0.09 or 0.36 | gain SD 0.80 to 0.91 pp, MDE80 2.0 to 2.3 pp | false STOP at most 0.043 where the true gain is non-negative |

The S line is decisive at the extremes and INDETERMINATE for kappa6 between
about 0.08 and 0.14 at 320 held-out questions; that is the honest resolution of
six draws on about 50 families. The edge-heavy row is a deliberate property:
questions just inside the band (p 0.8 to 0.9) are rarely contested in six draws,
and re-attempts change a six-draw majority vote on them little.

**Leakage checks.** (1) Families are connected components over provenance
(Omni-MATH source competition; AIME or AMC exam instance from the AoPS URL)
and near-duplicate links across all sources (MinHash on normalised word
5-grams with Jaccard at least 0.5, or the same normalised final answer with
bge-small cosine at least 0.9); at most 25 questions per family enter G.
(2) Families split 50/50 within stratum by seed 42 (43 and 44 for
sensitivity). (3) Zero near-duplicate links across split sides, and none to P0
questions (I5). (4) Standardisation, layer and C are fitted on training
families only; the held-out AUC is computed once. (5) Within-question AUC is
leakage-free by construction; the question-grouped versus family-grouped
pooled-AUC gap is reported. (6) Label-permutation and prompt-only controls as
instrument gates. (7) Benchmark-exposed items (MATH-500 test ids, AIME 2024
and later) are excluded; memorisation probes (prefix completion and a
32-token non-thinking answer) flag questions, and every line is reported with
flagged questions excluded as a sensitivity.

**Instrument gates (before any line is read).** I1 grader audit: math-verify
labels agree with adjudicated labels on 200 stratified items in at least 98%.
I2 at least 85% of G's draws have an answer position. I3 permutation null in
[0.48, 0.52]. I4 prompt-only within-question AUC exactly 0.5. I5 near-duplicate
audit clean. I6 at least 80 mixed held-out questions, else INCONCLUSIVE_N.
I7 alignment: on P0's 32 extraction traces (checked first on the smoke's
full-length traces), the HF pass's log-probability of the sampled first answer
token at the answer position matches vLLM's recorded value within 0.05 nats for
at least 95%. Any failure except I6 gives INSTRUMENT_FAIL and no
science verdict.

**Missing data and caps.** If G's decode job reaches its cap, generation stops;
questions processed in a seeded random family order keep the held-out sample
random; only questions with all six draws enter, and the shortfall is reported
(I6 still applies). Failed requests are retried once with the same seed; a
second failure counts the draw as missing, not wrong, and is reported.

## Compute and Reproducibility

Generation image: the cu129 overlay of
`docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
(image ID `sha256:423783aa...`, vLLM commit `db9527a4`, torch 2.13.0+cu129),
built per source commit by `scripts/build_vllm_overlay_on_h100.sh` with a
provenance receipt, as in probe v2 (overlay image ID
`sha256:a59d7782755ac7db3e5ffdeaa1dd023af169b0ed6a5e04213ebbecbc7d5c30fc`).
The overlay served the Qwen3-8B architecture with dummy weights in probe v1
job B (CUDA graphs on, no eager fallback). Extraction (HF prefill) image:
`127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(build 855; transformers 5.15.0, torch 2.11.0+cu128), with SDPA attention and
`lm_head` skipped except for the I7 check.

Engine configuration (fixed for every generation job): bf16, one H100,
gpu_memory_utilization 0.90, max_model_len 40,960, max_num_seqs 256,
max_num_batched_tokens 16,384, prefix caching on, T 0.6, top-p 0.95, top-k 20,
min-p 0, max_tokens 32,768, logprobs 20; per-request seed = first 4 bytes
(unsigned 32-bit) of SHA-256 of [42, family id, question id, draw index]; stored prompt and generated
token ids with their SHA-256 are the record, because vLLM sampling is not
batch-invariant.

Launch path (dry run, then test-only, then submit; one GPU per job; none of
these manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/c3-selection-allocation-gate-v1-smoke.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/c3-selection-allocation-gate-v1-smoke.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/c3-selection-allocation-gate-v1-smoke.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the same three steps follow for the P0, G-decode and G-extraction manifests. The
weight fetch uses `sbatch infra/slurm/host-single-node/fetch-model-cpu.sbatch`
(CPU only) after a registry amendment for `qwen3-8b` (new role, blocker text
replaced) under D1; it is a host action and waits until no S1a VM or GPU job is
running. Every executable pilot also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for the analysis-pipeline
doctor, `kind: slurm-manifest` for the GPU jobs).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 8 (the gate's admission
ceiling: smoke 0.25 and P0 1.0 fixed caps, G-decode and G-extraction caps each
1.2 times the P0-calibrated high projection, sum at most 8.0 under D22; this is
the gate's compute, separate from the gauntlet's 0.3 GPU-h reviewer budget).

Estimate (S2, `compute/cost-model.json`; HBM-bound decode model calibrated on
job B's dummy-weight points, which it reproduces within 0.7% for the four
short-prompt points and underpredicts for the long-prompt points b3 and b6,
whose rate the high case uses). For 800 questions x 6 draws at CV 0.75, G decode
central / high: 3.19 / 4.44 GPU-h at a mean of 6,000 tokens, 4.21 / 5.86 at
7,000, 7.90 / 11.0 at 10,000; G extraction (HF prefill) 0.38 / 0.61 at 6,000. P0 (120
questions x 2 draws plus 32 prefill traces): 0.33 / 0.51 at 6,000 and 0.71 /
1.04 at 12,000. The registered N rule admits 800 questions up to a mean of
about 6,300 tokens and some N of at least 560 up to about 7,700 (7,300 to
8,200 over CV 0.6 to 0.9).

Checkpoints and resume: generation writes completed draws (token ids,
log-probabilities, step statistics) to the persistent run directory every 5
minutes keyed by (family, question, draw); a fresh job skips completed keys and
continues the seeded family order; the smoke job runs a kill-and-resume test
and requires the resumed output set to equal an uninterrupted run's set of
keys and per-key token ids for requests that completed before the kill. The
extraction job checkpoints per 256 traces. Artifacts: per-draw answer, label,
lengths, log-probability features, gate and floor scores, the selected-layer
states (late layers only in the archive), per-question verdict tables, and the
decision record. Problem text and raw traces stay on the host or in the
private archive; the public repository receives ids, hashes, labels and
metrics.

## Safety, Data Rights, and Monitorability

- **Model.** Qwen3-8B, Apache-2.0 (card and LICENSE at the revision). Frozen;
  no weights are trained or released. The registry entry currently says no
  weight download is planned; amending it is part of the registration's
  prerequisites, under D1 (public research downloads authorized, recorded with
  SHA-256).
- **Data.** Compilations with permissive cards: EleutherAI/hendrycks_math (MIT),
  KbsdJames/Omni-MATH (Apache-2.0), Hothan/OlympiadBench (Apache-2.0),
  AI-MO/aimo-validation-aime and -amc (Apache-2.0). A compilation licence does
  not cover the underlying competition problems (MAA, HMMT, AoPS and others),
  so the public repository holds ids, source revisions, statement hashes,
  labels and metrics only. Excluded: MathArena sets (CC-BY-NC-SA-4.0; D4's
  precedent for NC data in Kevin's commercial context), SynthLabsAI/Big-Math
  (gated; accepting terms needs explicit permission), DeepScaleR's AIME and AMC
  (no provenance fields for families), NuminaMath and DAPO fillers, and code
  (grading runs untrusted model code; D7 forbids it GPU access and no
  CPU-sandbox ruling exists).
- **Untrusted code.** None executes: model outputs are strings graded by
  math-verify or sympy on CPU; the harness is reviewed project code (D7).
- **Public repository.** No host addresses beyond the documented local
  registry name, no credentials, no problem text, no raw traces.
- **Host.** No host job of any kind while an S1a VM or GPU job runs; the GPU
  work waits for a scored, reviewed package and a freeze (D64).
- **Monitorability.** No policy is trained and nothing is deployed; the gate
  is a 4,096-dimensional linear probe whose weights and scores are archived.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Verdict | What it says | What it closes |
|---|---|---|
| STOP_DECODE | A linear answer-token gate does not rank Qwen3-8B's thinking-mode answers within question at 0.60 on family-held-out problems of this workload | The learned-selector arm of C3 for this model and workload; a publishable negative transfer of CASE's criterion to long reasoning, bounded to a linear gate |
| STOP_REDUNDANT | The hidden-state gate adds less than 0.02 within-question AUC over free output signals | C3's "learned hidden-state selector" framing; any selector arm reduces to confidence-weighted voting, which 2609.32035 already finds does not beat voting on this model |
| STOP_HARM | A gate-weighted vote is worse than voting on held-out questions | The selector arm, and a warning against deploying hidden-state fusion on thinking models without a held-out check |
| STOP_SPREAD | The affordable workload has fewer than 10% contested questions | Allocation's room on the workload the registered rule could afford with this model; a quantitative reason a re-attempt study on this model needs a larger compute admission (D24) or a smaller-KV model |
| INFEASIBLE | No registered workload with at least 3 strata admits N of at least 560 under 8 GPU-h of caps | The gate on Qwen3-8B within the program; a measured statement that contested competition questions cost too much for this model on one H100; options are a Qwen3.5-9B variant (about 3.4x cheaper per generated token by the asset cell's bandwidth estimate, unmeasured, and an architecture change with no clean date window) under a new registration, or Kevin's admission under D24 |
| INCONCLUSIVE | One or more lines indeterminate | Nothing; the per-line intervals size a successor |
| GO | All four lines pass | Licenses only a gauntlet for the 2x2, with the gate's variance and correlation inputs for its power gate |

The likely outcomes, by the owner's prior, are INCONCLUSIVE (F indeterminate)
or STOP_REDUNDANT, either of which is a clean, cheap negative for a crowded
area.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 127 counted discover queries with returned ids and raw-output SHA-256, 24 uncounted searches and the fetch failures logged; cutoff 2026-10-10; degraded coverage recorded (no Semantic Scholar, arXiv API, OpenReview full texts, Anthology index, patents, social media; alphaXiv lag) (`doctors/source.json`) | Run Semantic Scholar forward citations for CASE, HSRM and 2609.32035 through the host relay after S1a |
| Citation | PASS | Claim registry C01 to C52 with locators, dates and read status; every arXiv id snapshotted with HTTP 200 and its version history; OpenReview rows marked UNVERIFIABLE_ACCESS (their HTTP 200 pages are a browser challenge); first-party labels; five dossier corrections (`doctors/citation.json`) | Read SANE's and the other ICLR 2027 submissions' full texts when accessible |
| Novelty | FAIL | No direct prior under the recorded coverage, but the blind closest-prior critic and the novelty refuter have not run; the query budget left 23 queries for a triad that needs at least 30; ACL Anthology checked only through web search (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter |
| Design | FAIL | Intervention, controls, falsifiers, metrics, leakage controls and decision rules are specified and simulated (S1), but every distribution is assumed, the workload rule and family builder are unexecuted, and no harness exists (`doctors/design.json`) | Build the analysis pipeline and run it as a `cpu-doctor` orx node on S1's synthetic pools |
| Compute | FAIL | No real model loop for this gate, no adapter, no manifest, no container smoke, no Slurm dry run; Qwen3-8B weights not on the host; real-weight Qwen3-8B throughput never measured (`doctors/compute.json`, `compute/attestations-not-run.md`) | Registry amendment and fetch after S1a; write the harness and the smoke manifest; dry run and test-only |
| Safety | PASS | Apache-2.0 model, permissive compilations with problem text kept off the public repository, NC and gated sets excluded, no untrusted code executed, host rule respected (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts, UNVERIFIABLE_ACCESS); Design, the vendored
K-Dense `experimental-design` and `statistical-power` skills (design before
data, three-way decisions with operating characteristics by simulation);
Evaluation, K-Dense `statistical-analysis` (clustered intervals, paired
increments); Novelty, K-Dense `literature-review` (PRISMA counts). The
integrity gate (seven failure modes) is answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only while no S1a VM or GPU job is running)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; wave-1 reviewers have not run |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01 to C52 in doctors/citation.json |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P1 to P6 with registered falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; floor, permutation, prompt-only and grouping controls |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S1 operating characteristics under assumed distributions |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; caps at most 8.0 GPU-h by formula, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest, weights not on host |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; ids and hashes only, NC excluded |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| dossier (2026-10-06) | not scored | Spread statistic measures noise; pooled decodability trivially high; 6 GPU-h unmeasured | Corrected question and kill lines written | Recorded in the dossier, section 9 |
| new gauntlet, synthesis (2026-10-10) | not scored | The dossier's spread target is not identified from six draws, and AUC 0.60 does not imply selection gain in thinking mode | Gate rescoped to Stage 0; identified contested-share line; floor and harm lines; family construction; P0 with a registered workload and N rule; S1 and S2 | Awaiting blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-c3-selection-allocation-gate.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-c3-selection-allocation-gate/doctors/research-direction-doctor-output.json`.
Two readings the doctor does not make for itself: "all declared budgets must be
positive" comes from parsing the declared `gpu_hours=0.3` as an integer (the
declared budget is honest and not rounded up to pass); and the doctor applies no
79 cap here because its executable-pilot check is textual, while by the
gauntlet rule's cap table this proposal is capped at 79 (no executable pilot)
and 89 (no independent provider-distinct review), and cannot reach 100 without
D24's trust store. The doctor also counts the OpenReview snapshots as resolved
because those pages return HTTP 200; their bodies are a browser challenge.

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "FAIL",
    "Novelty": "FAIL",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "all declared budgets must be positive",
    "Novelty doctor lacks PASS plus concrete evidence",
    "Design doctor lacks PASS plus concrete evidence",
    "Compute doctor lacks PASS plus concrete evidence",
    "Reviewer A lacks structured PASS attestation",
    "Reviewer B lacks structured PASS attestation",
    "evidence bundle requires exactly two review artifacts",
    "protected external trust store is not configured; set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI",
    "reviewers must use different providers; degraded review cannot score 100",
    "reviewers must have distinct nonempty run IDs",
    "two distinct trusted reviewer signatures are required for 100",
    "compute attestation says the real model loop is not executable",
    "compute attestation lacks a non-stub benchmark adapter",
    "compute benchmark_adapter path does not exist",
    "repository real model loop is still a stub",
    "compute lacks a hashed Slurm manifest",
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 3 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-c3/program/proposals/2026-10-10-c3-selection-allocation-gate.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 54,
    "recognizedPrimaryUrls": 54
  },
  "status": "FAIL"
}
```
