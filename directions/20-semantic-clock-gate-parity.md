# Direction 20: Semantic-Clock Gate Parity

**Status:** STILL_OPEN on 2026-09-01 — wave-3 spec; not pilot-ready; phase 0 is a training-free portability screen on released hybrids, phase 1 (architecture-causal) is gated behind it
**Priority:** CPU hook and mask doctors, then the 14 GPU-h phase-0 ledger and clock-surgery screen before any training
**Experiment contract:** `experiments/architectures/semantic-clock-gate-parity.yaml`
**Proposal:** `research/proposals/2026-09-01-semantic-clock-gate-parity.md`

## Research question

In gated delta-rule hybrids the forgetting and write gates tick once per token,
so the same meaning costs a high-fertility language more cumulative gate mass.
Do released Gated DeltaNet (Qwen3.5) and KDA (Kimi-Linear) gates fail to
self-normalize this (C1)? Does rescaling the clock by the fertility ratio move
translation-paired recall through the recurrent state, with a fertility-specific
dose-response that survives partialling out training-resource share (C2)? Can a
training-time span-parity loss on gate statistics, supervised by parallel text,
close the gap without changing inference (C3, phase 1, separate contract)?

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
  attention-blind readout: at query time the 8 full_attention layers cannot attend to
  any fact or distractor position; GDN state and KV cache are shared with the
  as-written readout from one prefix pass

Primary estimand (C2):
  log r*(L) - log r*(en) = a + beta_f log f_L + beta_c log CCshare_L + e
  over 15 non-English languages; claim requires the beta_f 95% interval to exclude 0.2
  on both readouts and the sign to replicate on an attention-free subject (rwkv7)

Phase 1 loss (separate contract), gate parameters only:
  L = L_LM + lambda * sum_(s_a,s_b) sum_(layers,heads) (log(F(s_a)+eps) - log(F(s_b)+eps))^2
           + lambda_W * (same with W) + kappa * (mean_(t in en) g_t - anchor_en)^2
```

The log-ratio form is invariant to a global rescale of g (no "forget less"
shortcut); anchor_en pins the English forgetting budget; the placebo is
length-matched (pairs within 5 percent in token count) so it cannot install a
per-sentence content clock. The loss vanishes at inference.

## Closest work and delta

| Closest work | What it does | Delta here |
|---|---|---|
| Gated DeltaNet [2412.06464](https://arxiv.org/abs/2412.06464); Kimi Linear [2510.26692](https://arxiv.org/abs/2510.26692); GDN-2 [2605.22791](https://arxiv.org/abs/2605.22791) | Per-token gates learned by LM loss; no per-language analysis | Per-language cumulative gate ledger, clock surgery and (phase 1) span-parity supervision of the existing gate statistics |
| Tallec and Ollivier [1804.11188](https://arxiv.org/abs/1804.11188) | Gates give quasi-invariance to time warps (theory) | Fertility is the warp; invariance becomes the explicit null (R_F near 1) that phase 0 tests |
| Hirschi [2604.02474](https://arxiv.org/abs/2604.02474) | Rescales LSTM time constants by a known warp factor | Same operation as the constant surgery on a language-model gate with a fertility-predicted dose-response over 15 languages |
| Hybrid localization [2606.15378](https://arxiv.org/abs/2606.15378) | Long-range retrieval in hybrids is carried by attention | Motivates the attention-blind query mask and the attention-free replication subject |
| MLNeedle [2408.10151](https://arxiv.org/abs/2408.10151); ONERULER [2503.01996](https://arxiv.org/abs/2503.01996) | Cross-lingual needle retrieval on softmax transformers | Recurrent-state readout with n-way matched-content distractors and script-neutral 4-digit answers |
| Parity-aware BPE [2508.04796](https://arxiv.org/abs/2508.04796); MAGNET [2407.08818](https://arxiv.org/abs/2407.08818); Vowel Signs [2608.26449](https://arxiv.org/abs/2608.26449) | Parity at the tokenizer or segmentation level | Tokenizer fixed; parity inside the operator; mark-aware tokenizer verified so the abugida floor does not confound |
| Leino and Tiedemann [2603.29026](https://arxiv.org/abs/2603.29026) | Parallel data barely moves representations | Gate statistics are a different observable; the nil result is pre-registered for phase 1 |

No direct prior art found through 2026-09-01 under the coverage recorded in the
proposal (abstract-level arXiv via the host, HF Papers, OpenReview, Crossref,
WebSearch and WebFetch, pre-pulled feeds, X bookmarks, GitHub; no full-text, ACL
Anthology, patent or Chinese-language sweep). Novelty refuter: not refuted at
0.6; blind discrimination against GDN: different mechanism at 0.9. The idea is a
recombination (new observable plus new supervision target), not a new gate.

## Cheapest decisive pilot

Phase 0, training-free, public data only, 14 GPU-h ceiling including reserve.

Subjects: Qwen/Qwen3.5-4B-Base at 1001bb4d826a52d1f399e183466143f4da7b741b
(24 GDN plus 8 full-attention layers, mark-aware tokenizer; unregistered, the
registry's `qwen3.5-4b` is the post-trained placeholder); the same checkpoint
under the attention-blind mask; fla-hub/rwkv7-1.5B-world (attention-free
multilingual replication; unregistered, license unconfirmed);
moonshotai/Kimi-Linear-48B-A3B-Base (`kimi-linear-48b-a3b-base`, KDA
portability, ledger plus r grid at d = 32, two GPUs). Ledger only:
Qwen3.5-0.8B-Base and Qwen3.5-2B-Base.

Languages (16, fertility on the Qwen3.5 tokenizer over NTREX-128): en 1.00;
high-fertility H = pol 1.605, fin 1.627, hun 1.706, ukr 1.792, hin 2.073, ell
2.119, ben 2.164, tam 2.744; resource corners added in wave 3: rus 1.423 (6.9
percent CC share), tur 1.429 (1.4 percent), msa 1.157 (0.086 percent);
low-fertility non-Latin controls tha 1.174, kor 1.284, zho-CN 0.931; stress mya
4.18. Fertility and Common Crawl share are frozen covariates.

Steps:

1. CPU doctors: NumPy GDN simulator (r = 1 identity; token duplication x k
   scales F x k), zero-gradient attention-blind mask doctor, log-ratio loss
   gradient and invariance checks, causality doctor.
2. Ledger: F and W per layer and head per NTREX sentence in 16 languages on the
   Qwen3.5 Base ladder and Kimi-Linear; R_F and R_W against fertility with
   sentence-clustered intervals; per-sentence span-ratio CV.
3. Probe: K = 8 facts ("the password of [NP] is [CODE]", NLLB-translated), d in
   {8, 32, 64, 128} consecutive NTREX sentences (same run per episode id in every
   language), permuted query, greedy 4-token decode, exact match; 600 episodes
   per cell as 3 seeds x 200; two readouts (as written, attention-blind) per
   prefix pass. Baseline EM(en) curve over d reported before any surgery.
4. Surgery at d in {32, 128}: constant r in {0.5, 2, 4} and r = f_L, span
   oracle, write, decay plus write; quadratic fit gives r*(L); two-regressor
   partial slope on log f_L and log CC share; BPB under every setting.
5. Equivalence: span oracle versus constant at r = f_L, pooled TOST margin 3.
6. Attention-free replication on rwkv7 with fertility re-measured on its
   tokenizer.

Budget (owner arithmetic): 6.42e8 GDN prefix tokens, 5.98e18 FLOPs, 8.4 GPU-h
at 20 percent of peak; rwkv7 1.45 GPU-h; KDA 1.0 GPU-h; ledger and BPB 0.5
GPU-h; core 11.35 GPU-h; ceiling 14. Pre-registered degradation ladder if the
first-ten-minute throughput is below budget: drop the d = 64 calibration, then
write settings at d = 128, then r = 4 at d = 128, then rwkv7 d = 32 cells.

Phase 1 (new architecture-causal contract, owner estimate 55 GPU-h): 60M pure
GDN arms a data-only baseline, b span parity, c learned per-language constant,
d uniform decay regularizer, e length-matched placebo, f full attention, g SWA
plus sinks, h Parity-aware BPE, i synthetic-fertility English, j 3:1 hybrid, k
GDN-2 decoupled erase and write; FLORES+ devtest sealed endpoint. Funded only if
P1, P3 and P4 pass.

## Controls

- r = 1 identity surgery (hook path reproduces the unhooked model).
- Attention-blind query mask on the shared prefix state; attention-free
  multilingual subject (kills must replicate in sign).
- English under the same r (uniform "forget less" interaction control); BPB
  under every setting.
- Fertility-resourcedness decorrelated grid (rus, tur, msa) with the partial
  slope as the estimand; tha, kor, zho-CN for script; mya for stress.
- Span oracle versus per-language constant at matched mean log-decay shift.
- Write-only and decay-plus-write surgery; residual gap pre-registered as the
  write-count or interference share.
- Softmax cross-lingual retrieval baselines MLNeedle and ONERULER; phase-1
  matched arms (data-only, learned constant, uniform decay, length-matched
  placebo, full attention, SWA plus sinks, Parity-aware BPE, LR sweep at 30M).

## Falsifiers

- K1: R_F within 15 percent of 1 for every language with fertility at least
  1.5 — gates already warp-invariant; publish the ledger only.
- K2: partial fertility slope interval upper bound below 0.5 on both readouts,
  replicated on the attention-free subject — clock is not the bottleneck.
- K2b: dose-response present as written but absent attention-blind — recall is
  attention-carried; report as hybrid localization.
- K3: English interaction at most 2 points everywhere — uniform effect.
- K4: tha, kor, zho-CN and msa gaps within 3 points of the tam and ben gaps —
  script or data, not fertility.
- K5: pooled TOST shows span oracle within 3 EM points of the constant —
  demote the training mechanism to a normalization recipe.
- K6: prefix-invariance audit finds probe, hook or mask leakage.
- K7: attention-blind EM(en) at d = 128 above 95 — on ceiling; extend d first.
- K8: marginal slope excludes 0.2 but partial slope includes 0 — resourcedness.

## Compute

Discovery image `127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
(torch 2.11.0+cu128, transformers 5.15.0, no fla) runs the CPU doctors only;
the pilot needs a rebuilt image with fla 0.5.2 or newer re-pinned by digest.
Launch through `scripts/submit_docker_research_job.py` (dry run, then submit;
it issues the sbatch), seeds [42, 43, 44], gpu_hours 14, gpus 2, checkpoints
every 10 minutes to /home/kevin/cotcodec-runs with a fresh-job resume test.
Nothing has been executed; execution.enabled is false with the blockers listed
in the contract (no implementation, no fla image, unregistered Base and rwkv7
checkpoints, covariates not frozen, job manifest not written, licenses
unresolved for NLLB outputs and rwkv7, Kimi custom code not vendored).

## Kevin advantage

Phase 0 needs only public NTREX and released checkpoints, so any lab could run
it; the advantage is the harness (hooks, seeded paired episodes, shared-prefix
double readout, exact-match generation, checkpoint and resume) and the compute
to run 16 languages x 4 distances x 8 settings x 2 readouts in one node-day.
General Translation data is an optional upgrade (sub-sentence alignments where
span-ratio variance is largest, terminology stress sets, human-verified
templates, production language coverage), never a dependency. 8xH100 makes the
55 GPU-h phase 1 a one-day job if it is ever funded.

## Negative-result value

K1 is the first per-language gate measurement on production hybrids and shows
LM training realizes Tallec-Ollivier invariance. K2 or K8 localize the
cross-lingual recall gap outside the decay clock and hand it to write-count,
interference or data-exposure explanations. K2b is a hybrid-localization result
for these distances. K5 yields a training-free per-language gate normalization
recipe across GDN and KDA plus the ledger. Every branch delivers the
translation-paired recall instrument with script-neutral answers and n-way
matched-content distractors.

## Wave-3 repair (2026-09-01)

One repair, the union of both wave-2 judges' highest-impact identification fix:
(a) rus, tur and msa added and C2 pre-registered as the partial fertility slope
controlling for log Common Crawl share; (b) attention-blind query mask on every
dose-response cell plus the attention-free rwkv7 replication subject, d extended
to 128 with an off-ceiling hold; (c) claim scope relabelled portability-protocol
for phase 0, architecture-causal reserved for the gated phase 1, Hirschi
2604.02474 cited as mechanism ancestor; (d) length-matched placebo; (e) TOST
pooled across languages. Budget re-costed from 4 to 14 GPU-h. Wave-1 kill and
wave-2 score 61 are recorded in the proposal's Iteration Log.
