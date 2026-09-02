# Direction 20: Semantic-Clock Gate Parity

**Status:** STILL_OPEN on 2026-09-01 — wave-5 repair; the phase-0 objects are executable CPU code with a passing synthetic-case doctor (`scripts/run_semantic_clock_gate_parity_doctor.py`, receipt `data/results/semantic-clock-gate-parity/phase0-doctor.json`); not pilot-ready (no real-checkpoint hooks, no container smoke, no Slurm dry run); phase 0 is a training-free portability screen on released hybrids plus an attention-free co-primary subject, phase 1 (architecture-causal) is gated behind it
**Priority:** real-checkpoint hook path, pass-B window and re-segmentation rule on the registered subjects, then the 16 GPU-h phase-0 ledger and clock-surgery screen before any training
**Experiment contract:** `experiments/architectures/semantic-clock-gate-parity.yaml` (`reference_doctor` bound to `harness/semantic_clock_gate_parity.py`)
**Proposal:** `research/proposals/2026-09-01-semantic-clock-gate-parity.md`
**Phase-0 doctor:** `uv run python scripts/run_semantic_clock_gate_parity_doctor.py --output data/results/semantic-clock-gate-parity/phase0-doctor.json` (NumPy/SciPy, CPU, seconds; every number synthetic; tests in `tests/test_semantic_clock_gate_parity_doctor.py`)

## Research question

In gated delta-rule hybrids the forgetting and write gates tick once per token,
so the same meaning costs a high-fertility language more cumulative gate mass.
Do released Gated DeltaNet (Qwen3.5) and KDA (Kimi-Linear) gates fail to
self-normalize this (C1)? Does a common-dose clock rescale (r = 2 against
r = 1) raise translation-paired recall that is forced through the recurrent
state more for high-fertility languages, after partialling out
training-resource share, on both a GDN hybrid read prefix-blind and an
attention-free RWKV-7 subject (C2)? Can a training-time span-parity loss on
gate statistics, supervised by parallel text, close the gap without changing
inference (C3, phase 1, separate contract)?

## Mechanism

```text
S_t    = alpha_t S_{t-1} (I - beta_t k_t k_t^T) + beta_t v_t k_t^T
g_t    = log alpha_t = -exp(A_log) * softplus(a_t + dt_bias)
beta_t = sigmoid(b_t)
F(s)   = -sum_{t in s} g_t      forgetting mass over span s
W(s)   =  sum_{t in s} beta_t   write mass over span s
Per-token clock: F(s_L) / F(s_en) tracks the fertility ratio |s_L| / |s_en|

Phase-0 surgery on frozen gates (hooks):
  constant decay:  g'_t = g_t / r          r in {0.5, 1, 2, 4} and r = f_L
  span oracle:     g'_t = g_t / r_s        r_s = |s_L| / |s_en| per aligned NTREX sentence
  write:           beta'_t = 1 - (1 - beta_t)^(1/r)
  rwkv7:           log w'_t = log w_t / r  (per-channel decay; same surgery, different gate object)

Readouts (three per cell):
  pass A, as written            secondary (K2b comparator)
  pass A, query-only mask       secondary: at the query the 8 full_attention layers may
                                not attend to fact or distractor positions
  pass B, prefix-blind          PRIMARY: for every token of the episode the 8
                                full_attention layers attend only within the token's
                                own sentence, so no attention hop crosses a sentence
                                boundary and every cross-sentence dependency, including
                                rehearsal of a fact during the distractor span, must
                                pass through the GDN state

Primary estimand (C2), common-dose paired gain at d = 128, prefix-blind:
  G_L = EM_L(r = 2) - EM_L(r = 1)
  G_L = a + beta_f log f_L + beta_c log CCshare_L + e      over 16 languages (en at log f = 0)
  claim (a): beta_f 95% lower bound above 0 and estimate at least 3 EM points per unit log
  fertility on BOTH co-primary subjects (Qwen3.5-4B-Base prefix-blind, rwkv7-1.5B-world);
  pure-clock reference about 7; kill on the pooled slope (upper bound below 3)

Wave-5 headroom-invariant comparator (both wave-4 reviewers' highest-impact fix):
  synthetic-fertility English: the same English episodes re-segmented to f_L x the canonical
  token count (content, language, tokenizer, resource share, translation quality fixed),
  pass B, r in {1, 2}, d = 128, never cut
  G_syn(f) = EM_syn(f; r = 2) - EM_syn(f; r = 1)
  claim (b): slope of G_syn on log f has lower bound above 0 and estimate at least 3
  claim (c): tracking residual D_L = G_L - G_syn(f_L) regressed on log f_L has a point
             estimate inside (-3, 3); an interval entirely outside the band is K11
             (fertility slope is language identity or headroom, not the clock); an estimate
             outside the band whose interval reaches it is the inconclusive second-episode band
  reported sensitivity, never a kill: the same slopes on the smoothed logit scale (the NumPy
  simulator shows a pure per-token clock can have a flat logit gain, so a logit conjunct
  would refuse a true clock); baseline token-count cost = slope of logit EM_syn(f; r = 1) on log f
  descriptive only: quadratic argmax r*(L) with boundary censoring; dEM/dlog r over {0.5, 1, 2}

Phase 1 loss (separate contract), gate parameters only:
  L = L_LM + lambda * sum_(s_a,s_b) sum_(layers,heads) (log(F(s_a)+eps) - log(F(s_b)+eps))^2
           + lambda_W * (same with W) + kappa * (mean_(t in en) g_t - anchor_en)^2
```

Why the within-sentence window rather than masking only fact keys: with fact
keys masked, a distractor token can still read fact content that the GDN state
deposited in an earlier distractor position and re-write it into the state, so
attention would relay state-carried content across long ranges with a hop
count that scales with fertility, against the clock's sign. The window closes
every cross-sentence hop; the cost is a second prefix pass and an operating
regime the checkpoint was not trained for, which the floor hold K7b guards.

The log-ratio form is invariant to a global rescale of g (no "forget less"
shortcut); anchor_en pins the English forgetting budget; the placebo is
length-matched (pairs within 5 percent in token count) so it cannot install a
per-sentence content clock. The loss vanishes at inference.

## Closest work and delta

| Closest work | What it does | Delta here |
|---|---|---|
| Gated DeltaNet [2412.06464](https://arxiv.org/abs/2412.06464); Kimi Linear [2510.26692](https://arxiv.org/abs/2510.26692); GDN-2 [2605.22791](https://arxiv.org/abs/2605.22791) | Per-token gates learned by LM loss; no per-language analysis | Per-language cumulative gate ledger, clock surgery and (phase 1) span-parity supervision of the existing gate statistics |
| Tallec and Ollivier [1804.11188](https://arxiv.org/abs/1804.11188) | Gates give quasi-invariance to time warps (theory) | Fertility is the warp; invariance becomes the explicit null (R_F near 1) that phase 0 tests |
| Hirschi [2604.02474](https://arxiv.org/abs/2604.02474) | Rescales LSTM time constants by a known warp factor | Same operation as the constant surgery, on a language-model gate with a common dose across 16 languages and a fertility partial slope; blind discrimination against it pending |
| DeciMamba [2406.14528](https://arxiv.org/abs/2406.14528) | Inference-time manipulation of the S6 filtering mechanism on a frozen Mamba for length extrapolation | Same frozen-model inference-time family; here the warp factor is fertility, the manipulation a per-language decay rescale, the test a cross-language dose-response |
| Petrov et al. [2305.15425](https://arxiv.org/abs/2305.15425); Ahia et al. [2305.13707](https://arxiv.org/abs/2305.13707) | Tokenizer length disparity up to 15x; token-priced API unfairness across 22 languages | The same fertility ratio is traced into the operator's forgetting and write clock rather than the bill |
| Hybrid localization [2606.15378](https://arxiv.org/abs/2606.15378) | Long-range retrieval in hybrids is carried by attention | Motivates the prefix-blind primary readout, the floor hold and the attention-free co-primary subject |
| RWKV-7 "Goose" [2503.14456](https://arxiv.org/abs/2503.14456) | Generalized delta rule with vector-valued decay; 0.19B to 2.9B models on a 3.1T multilingual corpus (first-party) | Co-primary attention-free subject; surgery on its per-channel decay; fertility re-measured on the World tokenizer |
| MLNeedle [2408.10151](https://arxiv.org/abs/2408.10151); ONERULER [2503.01996](https://arxiv.org/abs/2503.01996) | Cross-lingual needle retrieval on softmax transformers | Recurrent-state readout with n-way matched-content distractors and script-neutral 4-digit answers |
| Parity-aware BPE [2508.04796](https://arxiv.org/abs/2508.04796); MAGNET [2407.08818](https://arxiv.org/abs/2407.08818); Vowel Signs [2608.26449](https://arxiv.org/abs/2608.26449) | Parity at the tokenizer or segmentation level | Tokenizer fixed; parity inside the operator; mark-aware tokenizer verified so the abugida floor does not confound |
| Leino and Tiedemann [2603.29026](https://arxiv.org/abs/2603.29026) | Parallel data barely moves representations | Gate statistics are a different observable; the nil result is pre-registered for phase 1 |

No direct prior art found through 2026-09-01 under the coverage recorded in the
proposal (abstract-level arXiv via the host, HF Papers, OpenReview, Crossref,
WebSearch and WebFetch, pre-pulled feeds, X bookmarks, GitHub; no full-text, ACL
Anthology, patent or Chinese-language sweep). Novelty refuter: not refuted at
0.6; blind discrimination against GDN: different mechanism at 0.9, run against
the substrate only and not transferred to Hirschi or DeciMamba (rerun pending).
The idea is a recombination (new observable plus new supervision target), not a
new gate.

## Cheapest decisive pilot

Phase 0, training-free, public data only, 16 GPU-h ceiling including reserve.

Co-primary subjects: Qwen/Qwen3.5-4B-Base at 1001bb4d826a52d1f399e183466143f4da7b741b
(24 GDN plus 8 full-attention layers, mark-aware tokenizer; registered as
`qwen3.5-4b-base`, artifact receipt reported on fal-h100-01 under
/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/ by Slurm job 356, not
re-opened by this direction's owner) read prefix-blind (pass B), and
fla-hub/rwkv7-1.5B-world at 004140baad7a62d49a26d97508ef19cf09672328
(attention-free; registered as `rwkv7-1.5b-world`, receipt reported the same
way; card license apache-2.0, inheritance unconfirmed; card lists 8 languages,
grid coverage unverified; trust_remote_code, custom code review pending).
Secondary readouts on Qwen
from pass A: as written and query-only mask. Portability base:
moonshotai/Kimi-Linear-48B-A3B-Base (`kimi-linear-48b-a3b-base`, KDA, ledger
plus d = 32 at r in {1, 2} on both passes, two GPUs; scored by P1 replication
and the sign of the prefix-blind slope). Ledger only: Qwen3.5-0.8B-Base and
Qwen3.5-2B-Base.

Languages (16, fertility on the Qwen3.5 tokenizer over NTREX-128): en 1.00;
high-fertility H = pol 1.605, fin 1.627, hun 1.706, ukr 1.792, hin 2.073, ell
2.119, ben 2.164, tam 2.744; resource corners added in wave 3: rus 1.423 (6.9
percent CC share), tur 1.429 (1.4 percent), msa 1.157 (0.086 percent);
low-fertility non-Latin controls tha 1.174, kor 1.284, zho-CN 0.931; stress mya
4.18. Fertility and Common Crawl share are frozen covariates; the measurement
scripts are hashed in the proposal (CR-05) and must be archived. Fertility on
the RWKV World tokenizer is unmeasured.

Steps:

1. CPU doctors. Done as code on 2026-09-01 for the synthetic half:
   `harness/semantic_clock_gate_parity.py` implements the gate
   parametrization, the three surgeries, a batched GDN scan, the F/W ledger
   with R_F and R_W, the prefix-blind window and query-only mask with an
   analytic zero-gradient audit, the anchored log-ratio span-parity loss with
   gradient, the common-dose estimand with the two-regressor partial slope,
   the re-segmented-English tracking residual and every registered decision
   rule (P1, K1, P3, K2, K3, K4, K7, K7b, K8, K9, K10, K10b, K11);
   `scripts/run_semantic_clock_gate_parity_doctor.py --output
   data/results/semantic-clock-gate-parity/phase0-doctor.json` runs 17
   registered cases (identity surgery and causality, token duplication,
   ledger positive and warp-invariant negative controls, prefix-blind window
   zero gradient, query-only mask not prefix-blind, leaky-window tamper,
   span-parity gradient and invariances, mechanistic simulator positive and
   identity-noise negative controls, parametric clock/headroom/identity/null
   worlds, permuted fertility, kill/hold semantics, degenerate inputs) and
   passes on a laptop CPU in seconds; every number is synthetic. Not done:
   the same objects on the real checkpoints (hook path, pass-B window on one
   d = 8 episode, episode builder, re-segmentation rule with BPB, round-trip
   QA pipeline).
2. Ledger: F and W per layer and head per NTREX sentence in 16 languages on the
   Qwen3.5 Base ladder and Kimi-Linear; R_F and R_W against fertility with
   sentence-clustered intervals; per-sentence span-ratio CV.
3. Probe QA: 12 templates x 300 noun phrases per language NLLB-translated and
   back-translated; redraw below chrF 50 or if the code does not survive;
   redraw rate per language reported, above 25 percent translation-limited
   (K10); 180 templates held for human verification (blocker).
4. Probe: K = 8 facts, d in {8, 32, 128} consecutive NTREX sentences (same run
   per episode id in every language), permuted query, greedy 4-token decode,
   exact match; 600 episodes per cell as 3 seeds x 200; pass A (as written,
   query-only mask) and pass B (prefix-blind). Baseline EM(en) curve over d on
   every readout reported before any surgery; K7b floor (prefix-blind EM(en) at
   d = 8 at least 60) and K7 ceiling (at d = 128 at most 95) read here.
5. Surgery at d = 128: r = 2 on both passes (primary cell against r = 1);
   r in {0.5, 4}, r = f_L, span oracle, write, decay plus write on pass B;
   r = f_L on pass A; English at every non-English f_L on pass B (P4);
   two-regressor partial slope of G_L on log f_L and log CC share; BPB under
   every setting; descriptive r*(L) with boundary censoring.
5b. Synthetic-fertility English (wave 5, never cut): the same English episodes
   re-segmented so the token count equals f_L x the canonical count for every
   non-English f_L (forced sub-word or character splitting of a pre-registered
   fraction of words; rule frozen before the first GPU job), pass B, r in
   {1, 2}, d = 128, on Qwen (all 15 f_L) and on rwkv7 at f in {1.5, 2.0, 2.7};
   BPB of the re-segmented text reported; delivers G_syn(f), the baseline
   token-count cost slope and the tracking residual D_L against G_L (P3 b, c;
   K11).
6. Equivalence: span oracle versus constant at r = f_L, pooled TOST margin 3.
7. Co-primary rwkv7: calibration at all three d, r in {0.5, 2, 4, f_L} plus
   span oracle at d = 128, English at every f_L, fertility re-measured on its
   tokenizer, same estimand; per-language 60-point floor (K10).
8. Kimi-Linear: ledger plus d = 32 at r in {1, 2} on both passes.

Budget (owner arithmetic, CR-14 and CR-35): one Qwen prefix pass over 16
languages x 600 episodes is 5.96e7 tokens and 0.78 GPU-h at d = 128 (20 percent
of peak); calibration on both passes 2.12, r = 2 on both passes 1.56, six pass-B
settings 4.69, English at every f_L 0.41, r = f_L on pass A 0.78, synthetic-
fertility English at r in {1, 2} on pass B 1.50 (1200 episode-passes x 3,488
tokens x the sum of the 15 fertilities 27.408 = 1.15e8 tokens), Qwen core
11.06; rwkv7 1.73 plus synthetic English at three fertilities 0.11 = 1.84;
Kimi-Linear 1.08; ledger and BPB 0.5; probe QA 0.3; core 14.78 GPU-h; optional
0.54 (Kimi-Linear r in {0.5, 4}); reserve 0.68; ceiling 16. The wave-5 cell is
funded by dropping the optional pass-A r in {0.5, 4} cells (1.56 GPU-h), as
reviewer 2 proposed. Degradation ladder if first-ten-minute throughput is below
budget: Kimi-Linear r in {0.5, 4}; write settings at d = 128; mya from the
descriptive settings; rwkv7 r in {0.5, 4}; rwkv7 synthetic English. Never cut:
calibration, r in {1, 2} on both passes and both subjects, r = f_L and span
oracle on pass B, English at every f_L, synthetic-fertility English on Qwen
pass B, Kimi-Linear ledger and r in {1, 2}. A second episode block for an
inconclusive primary or an inconclusive tracking band (about 3.6 GPU-h) needs a
contract amendment.

Phase 1 (new architecture-causal contract, owner estimate 55 GPU-h): 60M pure
GDN arms a data-only baseline, b span parity, c learned per-language constant,
d uniform decay regularizer, e length-matched placebo, f full attention, g SWA
plus sinks, h Parity-aware BPE, i synthetic-fertility English, j 3:1 hybrid, k
GDN-2 decoupled erase and write; FLORES+ devtest sealed endpoint. Funded only
if P1, P3 and P4 pass.

## Controls

- r = 1 identity surgery (hook path reproduces the unhooked model).
- Prefix-blind readout (pass B, within-sentence window for the whole episode)
  as primary; query-only mask (pass A) secondary; attention-free rwkv7 as
  co-primary subject carrying the same estimand (claim requires both; K7b
  falls back to rwkv7 alone).
- English under the same r (common dose r = 2 for everyone, plus English at
  every f_L for the r = f_L interaction); BPB under every setting.
- Fertility-resourcedness decorrelated grid (rus, tur, msa) with the partial
  slope as the estimand; tha, kor, zho-CN for script; mya for stress with a
  leave-one-out report.
- Probe-translation round-trip QA: chrF threshold, code survival, redraw log,
  human-verified templates, per-language chrF as a third-covariate sensitivity.
- Span oracle versus per-language constant at matched mean log-decay shift.
- Write-only and decay-plus-write surgery; residual gap pre-registered as the
  write-count or interference share.
- Headroom and language identity (wave 5): synthetic-fertility English at
  matched token count (G_syn slope, baseline token-count cost, tracking residual
  D_L; K11 and the inconclusive band); logit-scale slopes reported as
  sensitivity; r = 0.5 symmetric-harm cells; ceiling hold K7.
- Softmax cross-lingual retrieval baselines MLNeedle and ONERULER; phase-1
  matched arms (data-only, learned constant, uniform decay, length-matched
  placebo, full attention, SWA plus sinks, Parity-aware BPE, LR sweep at 30M).

## Falsifiers

- K1: R_F within 15 percent of 1 for every language with fertility at least
  1.5 — gates already warp-invariant; publish the ledger only.
- K2: pooled partial fertility slope of G_L has an upper bound below 3 EM
  points per log unit and neither subject excludes 0 positively — clock is not
  the bottleneck.
- K2b: as-written slope excludes 0 but prefix-blind pooled upper bound below 3
  — recall is attention-carried; report as hybrid localization.
- K3: G_L minus G_en at r = 2 and the r = f_L interaction both at most 2 points
  everywhere — uniform effect.
- K4: tha, kor, zho-CN and msa gaps within 3 points of the tam and ben gaps —
  script or data, not fertility.
- K5: pooled TOST shows span oracle within 3 EM points of the constant —
  demote the training mechanism to a normalization recipe.
- K6: prefix-invariance audit finds probe, hook, window or mask leakage.
- K7: prefix-blind EM(en) at d = 128 above 95 — on ceiling; extend d first.
- K7b: prefix-blind EM(en) at d = 8 below 60 on Qwen — floor; Qwen cells become
  secondary and rwkv7 is the sole primary; if rwkv7 also fails, redesign the
  probe before any surgery claim.
- K8: marginal slope excludes 0 but partial slope includes 0 — resourcedness.
- K9: the two co-primary subjects' intervals exclude 0 with opposite signs —
  subject-specific; no portable recipe claimed.
- K10: a language with redraw rate above 25 percent or prefix-blind EM at d = 8
  below 60 on a subject is excluded with the count reported; fewer than 12 of
  16 remaining means that subject cannot carry the primary.
- K10b (wave 5, symmetric to K7b): rwkv7 keeps fewer than 12 of 16 languages
  while Qwen clears K7b — Qwen prefix-blind is the sole primary, no GDN-RWKV-7
  portability claim; both subjects failing means redesign the probe.
- K11 (wave 5): the cross-language slope clears but re-segmented English does
  not reproduce it (G_syn slope fails 3 with lower bound above 0, or the D_L
  slope interval lies entirely outside (-3, 3)) — language identity or
  headroom, not the clock; K2-class, no claim.
- Inconclusive tracking band (wave 5): cross-language and synthetic slopes
  clear but the D_L estimate is outside (-3, 3) with an interval reaching the
  band — second episode block (contract amendment), no claim meanwhile.
- Descriptive rule, never a kill: a quadratic r*(L) with non-negative curvature
  or an argmax outside [0.5, 4] is censored at the nearer boundary.

## Compute

Pilot image: `cotcodec-research:999f5583-architecture`, image ID
`sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad`, repo
digest `127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`
(built by Slurm job 353 from commit 999f5583; torch 2.11.0+cu128, transformers
5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2, triton 3.6.0). tilelang is
being added to the architecture extra because fla 0.5.2 guards the gated GDN
backward on Hopper under Triton < 3.7.1 (fla issue 640); the guard binds the
phase-1 training, not the forward-only phase 0. The image predates every hook,
so the run image must be rebuilt from the code that contains them and re-pinned.
Checkpoints: `qwen3.5-4b-base` and `rwkv7-1.5b-world` are registered with
receipts reported under /home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/
(job 356); Kimi-Linear's receipt is pending. The older discovery image
(15d6abc0..., no fla) is no longer cited for the pilot. Launch through
`scripts/submit_docker_research_job.py` (dry run, then submit; it issues the
sbatch), seeds [42, 43, 44], gpu_hours 16, gpus 2, checkpoints every 10 minutes
to /home/kevin/cotcodec-runs with a fresh-job resume test. Executed so far: the
CPU phase-0 object doctor on this Mac (synthetic numbers only). Nothing has run
on the node for this direction; execution.enabled is false with the blockers
listed in the contract (real-checkpoint hooks not written, image predates the
code, rwkv7 custom code unreviewed and fertility unmeasured, covariate scripts
and Common Crawl snapshot unarchived, templates not human-verified, blind
discrimination against Hirschi and DeciMamba not run, job manifest not written,
NLLB license decision unrecorded, Kimi custom code not vendored, re-segmentation
rule unfrozen, second episode block unfunded).

## Kevin advantage

Phase 0 needs only public NTREX and released checkpoints, so any lab could run
it; the advantage is the harness (hooks, attention-window masks, seeded paired
episodes, two-pass triple readout, exact-match generation, checkpoint and
resume) and the compute to run 16 languages x 3 distances x 2 passes x 8
settings in one node-day. General Translation data is an optional upgrade
(human verification of the 180 probe templates, sub-sentence alignments where
span-ratio variance is largest, terminology stress sets, production language
coverage), never a dependency. 8xH100 makes the 55 GPU-h phase 1 a one-day job
if it is ever funded.

## Negative-result value

K1 is the first per-language gate measurement on production hybrids and shows
LM training realizes Tallec-Ollivier invariance. K2 or K8 localize the
cross-lingual recall gap outside the decay clock and hand it to write-count,
interference or data-exposure explanations. K2b is a hybrid-localization result
with prefix-time rehearsal excluded. K7b is itself a finding: the GDN state of
a 3:1 hybrid does not carry 8-fact recall over 8 sentences without attention.
K9 is a GDN-versus-RWKV-7 gate-object difference. K11 (wave 5) is a
headroom-or-identity result: the cross-language dose-response exists but
re-segmented English does not reproduce it, so the cost is not the per-token
clock; the mirror branch (token count reproduces a dose-response that the
languages do not show) says the clock is real but is not what separates
languages. K5 yields a training-free per-language gate normalization recipe
across GDN and KDA plus the ledger.
Every branch delivers the translation-paired recall instrument with
script-neutral answers, n-way matched-content distractors and a
quality-controlled probe set.

## Wave-3 repair (2026-09-01)

One repair, the union of both wave-2 judges' highest-impact identification fix:
(a) rus, tur and msa added and C2 pre-registered as the partial fertility slope
controlling for log Common Crawl share; (b) attention-blind query mask on every
dose-response cell plus the attention-free rwkv7 replication subject, d extended
to 128 with an off-ceiling hold; (c) claim scope relabelled portability-protocol
for phase 0, architecture-causal reserved for the gated phase 1, Hirschi
2604.02474 cited as mechanism ancestor; (d) length-matched placebo; (e) TOST
pooled across languages. Budget re-costed from 4 to 14 GPU-h. Wave-1 kill and
wave-2 score 61 are recorded in the proposal's Iteration Log. Re-judged at 65
and 64 (lower 64).

## Wave-4 repair (2026-09-01)

Union of both wave-3 reviewers' highest-impact fixes (score history 61 to 64):
(a) the primary readout is prefix-blind for the whole episode (within-sentence
attention window in a second prefix pass), because the wave-3 query-only mask
let attention rehearse the fact into the GDN state during the distractor span;
the query-only mask is secondary; (b) floor hold K7b symmetric to K7, with
rwkv7 as the fallback primary; (c) the primary estimand is the common-dose
paired gain G_L = EM(r = 2) minus EM(r = 1) regressed on log fertility with log
CC share partialled out (minimum slope 3 EM points per log unit, pure-clock
reference about 7), the quadratic argmax r*(L) is descriptive with a boundary
rule, and a pooled kill statistic plus disagreement rule K9 are pre-registered;
(d) rwkv7-1.5B-world promoted to co-primary at revision 004140ba with
per-language floors K10; (e) probe-translation QA (round-trip chrF 50, code
survival, 25 percent redraw cap, human-verified templates as a blocker, chrF
covariate sensitivity); (f) fertility and Common Crawl scripts hashed and their
archive listed as a blocker; (g) Petrov, Ahia, DeciMamba and RWKV-7 opened and
cited; blind discrimination against Hirschi and DeciMamba recorded as pending;
(h) re-cost 14 to 16 GPU-h within the lane cap by dropping d = 64 and d = 32
Qwen surgery, not rwkv7. Not yet re-judged.

## Wave-5 repair (2026-09-01)

Single registered repair, the union of both wave-4 reviewers' highest-impact
fix (score history 61, 64, 63): (a) the primary estimand is made
headroom-invariant by a within-tokenizer warp reference in phase 0: the same
English episodes re-segmented to every grid fertility (token count changed;
language, tokenizer, resource share and translation quality fixed), run
prefix-blind at r in {1, 2} and d = 128 as a never-cut cell, with the claim now
requiring the cross-language slope, the synthetic-English slope and a tracking
residual inside (-3, 3) EM points per log unit; (b) K11 disagreement rule and
the inconclusive tracking band pre-registered; (c) the logit-scale slope is
reported as headroom sensitivity rather than the co-primary conjunct the
reviewers proposed, because the executable simulator shows that a pure
per-token clock with an exponential-retention readout has a nearly flat logit
gain across the grid (EM slope 14 points per log unit with the logit interval
covering 0 on the doctor's registered case), so the conjunct would refuse a
true clock; (d) contract drift repaired: arms point at the registered
`qwen3.5-4b-base` and `rwkv7-1.5b-world`, blockers rewritten as receipt-reported,
K10b fallback symmetric to K7b; (e) the phase-0 objects implemented as tested
CPU code (`harness/semantic_clock_gate_parity.py`,
`scripts/run_semantic_clock_gate_parity_doctor.py`,
`tests/test_semantic_clock_gate_parity_doctor.py`) and bound to the contract's
`reference_doctor`; the doctor passes 17 registered synthetic cases, including
the headroom and identity worlds in which the wave-4 EM-only rule would have
claimed; (f) re-cost within the 16 GPU-h cap by dropping the optional pass-A
r in {0.5, 4} cells (core 14.78, optional 0.54, reserve 0.68). Not yet
re-judged; Compute doctor FAIL by construction (no real model loop, no
container smoke, no Slurm dry run).
