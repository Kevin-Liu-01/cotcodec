# Research Direction: E7 G1 floor gate, state-necessary monolingual and cross-lingual recall in a from-scratch 134M Gated DeltaNet plus SWA-512 hybrid without an equivariance loss (backfill E7, direction 22)

**Status:** draft for gauntlet wave 1 (program decision D67). Synthesis was done by the single owner on 2026-10-10 from four independent discovery cells (frontier, kill-shot, cross-domain, asset and cost) of the E7 gauntlet workflow. The blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run. The registration `program/preregistrations/e7-equivariant-writes-g1-v1.md` is a DRAFT: not frozen or admitted, and with no ledger row. No executable pilot exists for this gate. A score of 100 cannot be certified in this repository (D24).
**Owner:** Kevin Liu (program owner). The synthesis, mechanism statement, identification design, simulations and draft registration were written by a Claude agent acting as the gauntlet's single synthesis owner.
**Source cutoff:** 2026-10-10
**Coverage limits:** Literature search used orx 0.2.2 only (alphaXiv keyword and embedding search, and OpenAlex). The build reports itself outdated against 0.2.18, and alphaXiv full texts can lag arXiv versions; versions were resolved through export.arxiv.org by requesting v2 and v3 directly. Other sources: the OpenReview api2 search endpoint (19 searches; per-note pages return a browser challenge and were not bypassed, so every OpenReview item is abstract-only and UNVERIFIABLE_ACCESS for full text); 4 web searches and 1 author page for the ACL Anthology (its own index was not queried and no proceedings were swept); arXiv abstract pages; the GitHub API; the Hugging Face dataset API; and repository evidence. Counts: 97 counted orx discover queries (frontier 46, kill-shot 23, cross-domain 24, synthesis 4) and 70 paper reads (frontier 35, kill-shot 13, cross-domain 19, asset 1, synthesis 2 abstracts). Not searched: Semantic Scholar and the arXiv API (unreachable from the development Mac; the host relay was not used), citation-graph traversal beyond OpenAlex, patents, X, Reddit, Hugging Face papers and Chinese-language venues. Not read: the ICLR 2027 submissions' PDFs (MAPP, CHARTA, the OpenReview version of 2610.06750); ICLR 2027 reviews are not public. The ACL 2026 paper 2026.acl-long.1706 was seen only through an author page. Full texts were read by targeted section, not end to end.
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e7-equivariant-writes-g1/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED: the frontier and kill-shot cells both returned NARROWED,
the cross-domain cell made no novelty claim, and no cell returned OCCUPIED.
No paper trains a translation-pair objective on the recurrent-state write of
a Gated DeltaNet hybrid. The residual left by the dossier, a semantic
objective on the write against generic recurrent-path forcing (2610.06750) in
the regime where attention cannot reach the fact, is narrower still:
- losses and auxiliary supervision on recurrent memory exist monolingually
  (Maglev 2608.02870, CHARTA, 2610.06750);
- aligning a language-agnostic subspace while keeping a language-specific one
  is occupied for dense residual streams (CAROT 2609.06381);
- the closest pretraining analogue of the later loss was null at 360M
  (2609.19291).

This proposal's gate claims no method novelty. It is an instrument floor gate
on a known architecture family (GatedDeltaNet-H1, 2412.06464, with a 512
window). Its only residual is a measurement: whether a from-scratch model at
this scale carries facts, and cross-lingual matches to them, through the
recurrent state where attention cannot reach.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. The
gate's own compute (registered caps summing to 7.733 GPU-h, central 4.87
GPU-h) is separate and runs only after a freeze. No host job was run for this
proposal; the host was read once with `squeue` (empty at 21:25 UTC).

## Scope and what changed from the dossier

This proposal covers only E7's G1 floor gate: the D22 A0 hybrid (no
equivariance loss) with SWA-512 replacing full attention in the measured
134M configuration, read at 200M and 1B tokens. The equivariance arms (A1
write equivariance, A2 projection alignment, A3 placebo, A5 no-bitext, a
2610.06750-style baseline) are out of scope. They need a preregistered subspace
or output-language guardrail design and their own gauntlet, and at about 27
GPU-h their admission is Kevin's under D24. The frozen Qwen3.5-4B
split-prefill confirmation belongs to P-GSM.

The four cells were merged by mechanism, not by wording. Seventeen mechanisms
change the gate as the dossier wrote it
(`program/evidence/2026-10-06/question-dossier.md`, section 16). Each row was
re-checked by synthesis against the full text, by simulation (S1,
`compute/gate-sim.py`), by the cost model (S2, `compute/cost-model.py`), by
the reach check (S3, `compute/reach-doctor.py`), or by more than one of these.

| # | Mechanism (cells that found it) | What it does to the dossier's gate | Where handled |
|---:|---|---|---|
| M1 | **"Beyond-window" is not state-only** (all four cells; derived independently). Information can travel k x W tokens through k stacked window layers ([2310.06825](https://arxiv.org/abs/2310.06825) §2; [2608.28444](https://arxiv.org/abs/2608.28444) Sec. 2.2 "after l layers, the receptive field is l w"). Models trained with SWA do relay information after its tokens leave the cache ([2609.34049](https://arxiv.org/abs/2609.34049): Mistral 7B 89% at offset +10 with the code evicted). Synthesis adds the GDN short convolutions. Without the recurrent state, the A0 graph reaches 3 x 511 + 9 x 3 = 1,560 positions. S3 confirms on a NumPy stand-in of the layer graph that the complex-step derivative with the state cut is nonzero at 1,560 and exactly zero at 1,561 in three seeds, and nonzero at 1,600 with the state | A fact "more than 512 tokens back" can be recalled with no state at all, so the dossier's read does not identify state carriage | Gate bin B3: every fact at least 1,600 tokens back. B1 (direct) and B2 (relay range) reported from the same checkpoint, with an eval-time state cut and a fact-write ablation. Training context 4,096 so that B3 fits |
| M2 | **Chance is 1/8, not 1e-4** (synthesis; the cross-domain cell proposed the forced-choice readout). With eight four-digit codes in context, an answer that copies any in-context code without matching the key scores 12.5% EM, because the target slot is balanced | The dossier's cross line of 15% certifies as little as (0.15 - 0.125) / 0.875 = 2.9% genuine binding. The legacy contract computed chance as 1e-4 | The line is kept verbatim. A binding guard BIND (target hits minus mean distractor hits, lower bound above 0) is added. S1's binding-free null never passes (P(PASS) 0.000 at copy rates 0.5 to 1.0). Forced choice and copy rate are reported |
| M3 | **Recurrent recall lock-in varies by seed** (frontier, kill-shot, cross-domain). Fixed-state recall is a lock-in lottery: 1/10 seeds without a distance curriculum, 7/10 with one; 0/6 under a time ramp, 6/6 when gated on accuracy ([2609.16183](https://arxiv.org/abs/2609.16183), first-party, preliminary, toy cells). Pythia-scale training dynamics are otherwise consistent across seeds, with outliers that show loss spikes ([2503.09543](https://arxiv.org/abs/2503.09543)) | A one-seed read is a lottery draw. The dossier gives no seed count and no curriculum distance distribution | Seeds [42, 43, 44]. Per-seed classification; a line passes on at least two seeds ABOVE and none BELOW; a LOTTERY verdict for splits. The curriculum's distance mixture is fixed (50% of first-query distances in the state-necessary range) |
| M4 | **No reference arm means no attribution** (kill-shot: the legacy dense rescue arm A4 was dropped; frontier and cross-domain: add an SWA plus sinks control or a state cut) | Without a reference, a failure cannot be pinned on the state, and a pass cannot be pinned on it either | A within-model decomposition at no training cost: B1 tests the same model with the fact inside one window; the state cut is 2610.06750's attention-only condition (Sec. 4.1) on the same checkpoint; the fact-write ablation zeroes the queried fact's values. FAIL_CROSS is sub-labelled "state-specific" when B1 cross-lingual EM clears 15% and "representational" when it does not |
| M5 | **The window size decides whether the recurrent path is trained** (frontier, kill-shot). Larger windows hurt the long-context recall of SWA plus xLSTM hybrids ([2509.24552](https://arxiv.org/abs/2509.24552)); "Large-Window Laziness" ([2606.15378](https://arxiv.org/abs/2606.15378)); the "Short-Context Learning Trap" ([2610.10114](https://arxiv.org/abs/2610.10114)) | A failure at SWA-512 does not show a failure at smaller windows | The window stays at the dossier's 512. The curriculum places half of its query distances beyond the attention reach. The limit is stated in every verdict, and an SWA-128 or stochastic-window sibling is named as a successor, not run (budget) |
| M6 | **1B tokens is below the asymptote** (kill-shot, frontier). The first translations without token overlap appear at about 11B tokens in a 1.7B model trained without parallel data ([2604.17633](https://arxiv.org/abs/2604.17633)). In 1B-token hybrid distillation runs "no run has converged" ([2609.35378](https://arxiv.org/abs/2609.35378) Sec. 6.3). Window design changes how fast long-context ability emerges (2606.15378) | A G1 result at 134M and 1B tokens (7.5 tokens per parameter) is a training-speed statement, not a capability statement | Every verdict is stated "at 1B tokens". The 1B read decides; the 200M read is descriptive; an emergence curve (100M, 400M, 800M, 1B) is reported |
| M7 | **Bitext exposure confounds any cross-lingual pass** (kill-shot, frontier, cross-domain). Parallel data mainly speeds early sharing ([2603.29026](https://arxiv.org/abs/2603.29026)). Coherent code-switching raises cross-script bitext retrieval from 5.5% to 61.4% at GPT-2-small shape ([2609.30535](https://arxiv.org/abs/2609.30535)) | A cross-lingual pass at 1B tokens may be bitext exposure, and the no-bitext arm is out of scope | G1 makes no claim about why cross-lingual recall works. CSLS bitext retrieval P@1 on the residual stream and on the pooled GDN write is reported at 200M and 1B. The prefix-sharing presentation is fixed and is the later grid's |
| M8 | **Test languages differ from training languages** (kill-shot, asset). The legacy contract tests En, De and Es, while training has no Spanish | Spanish cells sit at floor by construction | Test languages are En, De, Zh and Th, matching training. Same-script (En-De) and cross-script (En-Zh, En-Th) pairs are reported separately |
| M9 | **The initial decay timescales are short** (cross-domain; synthesis re-ran it in S3). Under fla 0.5.2's initialization, 2.6% of GDN heads start with a timescale above 512 tokens and 0.9% above 1,560. Chrono initialization was designed for exactly this failure ([1804.11188](https://arxiv.org/abs/1804.11188)) | A failure may be retention, not cross-lingual inability | Per-head timescales are logged at initialization and at 1B. The initialization is not changed (that would make A0 differ from the measured config). A chrono-style initialization is named as a successor repair, never applied silently |
| M10 | **EM over four digits is discontinuous** (cross-domain; [2304.15004](https://arxiv.org/abs/2304.15004)). Continuous proxies predict small-scale decisions as well or better ([2504.11393](https://arxiv.org/abs/2504.11393)) | A floor read cannot distinguish "near the line" from "at zero" | EM lines kept. Per-digit accuracy, target log-probability, forced choice among the eight codes and copy rate are reported, and the noise over the last three checkpoints ([2508.13144](https://arxiv.org/abs/2508.13144)) |
| M11 | **An untuned learning rate makes a failure uninterpretable** (cross-domain [2608.11859](https://arxiv.org/abs/2608.11859); frontier [2609.15545](https://arxiv.org/abs/2609.15545), where the learning rate and window change recall formation at 77-79M) | A single-LR failure is INCONCLUSIVE in substance | A three-point LR sweep on held-out LM loss (seed 42, 50M tokens each) with one conditional edge extension. One warmup-stable-decay trunk per seed with the 200M read from a 40M-token decay branch at 160M ([2405.18392](https://arxiv.org/abs/2405.18392): a 20% (1 - sqrt) decay matches cosine) |
| M12 | **The dossier's 2.5 GPU-h is one seed and an eager microbenchmark** (asset). Measured 282,501.4 tokens/s in Slurm 359 with random tokens, eager mode, bf16 parameters, full causal attention and a tied 32K vocabulary. A Qwen-size vocabulary would cost about 2.2x per token | Three seeds and the real pipeline change the price | S2 gives caps summing to 7.733 GPU-h (D22 counting) and 4.87 central. A throughput gate at 179,329 tokens/s; a futility stop after seed 42 (about 1.92 GPU-h if it fires); a 32K tokenizer |
| M13 | **Rights and availability** (asset, frontier) | FLORES+ is gated (`gated=auto`; accepting terms is Kevin's action). ParaDocs has no en-zh. The 2610.06750 code repository has no licence | The instrument comes from NTREX-128 (CC BY-SA 4.0, ungated) unless Kevin accepts FLORES+. En-Zh bitext from the ParaCrawl Bonus release, En-Th from SCB-MT-EN-TH-2020. The auxiliary pass in the probe is reimplemented from the paper |
| M14 | **Neither G1 outcome can confirm or kill the equivariance question** (kill-shot: value of information close to zero as written) | As written, a failure is pre-explained and a pass is confounded | A failure now carries a sub-label that picks a different successor (port, lock-in redesign, or nothing), and a pass is identified by B3. The owner's prior (FAIL_CROSS most likely, PASS about 0.1) is stated. The VoI argument is answered in "Strategic Fit", not dismissed |
| M15 | **SWA-512 nearly empties the later baseline** (kill-shot). An always-on SWA-512 is already the permanent limit of 2610.06750's attention restriction beyond the attention reach | The grid's "generic recurrent-path loss" baseline adds pressure only inside 1,560 tokens | Not G1's to fix. Recorded for the grid's gauntlet. The probe still prices the auxiliary pass |
| M16 | **Novelty narrowed further** (frontier, kill-shot): CAROT 2609.06381; MAPP (OpenReview Nol0BTGPR3); Maglev 2608.02870; CHARTA (OpenReview QvfwNCiyPg); 2609.19291's null activation alignment; Wu and Dredze's null for explicit alignment ([2010.02537](https://arxiv.org/abs/2010.02537)) | The later arms face a narrower residual and a poor prior | Closest Prior Work; Novelty Ledger. G1 reports A0's own write equivariance over the same-prefix floor, which sizes how much room the later loss has |
| M17 | **Pooled cross-lingual numbers hide pairs at floor** (cross-domain: the onset of cross-lingual transfer differs by pair, [2205.11758](https://arxiv.org/abs/2205.11758); subtract language means, [2205.10964](https://arxiv.org/abs/2205.10964)) | A pooled pass can hide a pair at zero | Per-pair and per-layer reporting. CSLS with language means subtracted. Equal cell weights in pooled lines |

Seven corrections to the frozen dossier, recorded here because the dossier
is not edited:

1. "Beyond-window (more than 512 tokens back)" is not state-only. The
   state-free reach of the A0 graph is 1,560 positions (M1).
2. Chance for TP-MQAR exact match at N = 8 is 12.5% for an answer that copies
   any in-context code, not 1e-4 (M2).
3. "~2.5 GPU-h" is one seed. Rule 6 asks for three, which come to 7.733 GPU-h
   in summed caps (M12).
4. The required baseline 2610.06750 was public on OpenReview on 2026-09-18
   (ICLR 2027 submission nIDJ2pPPOB), before its arXiv date of 2026-10-05
   (frontier cell).
5. 2610.01921 is now v2 (2026-10-02); its delta is unchanged.
6. The measured 134M number is for full causal attention with random tokens
   in eager mode. SWA-512 throughput on real data is unmeasured.
7. "A0 (no equivariance loss) on the measured 134M config" describes the
   published GatedDeltaNet-H1 family with a 512 window ([2412.06464](https://arxiv.org/abs/2412.06464)).
   G1 is an instrument gate, not an architecture contribution.

## Claim and Research Question

**Question.** Take a 134M hybrid of nine Gated DeltaNet layers and three
SWA-512 layers (the measured layout), trained from scratch for 1B tokens on
En, De, Zh and Th with 20% prefix-sharing bitext, a 5% same-language recall
curriculum and no equivariance loss. Consider N = 8 facts that all lie at
least 1,600 tokens before the answer position, beyond the 1,560-position
reach of every path that avoids the recurrent state. Does the model reach
exact match of at least 60% when the query repeats the key in its own
language (MONO), and at least 15% when the query is a surface-disjoint
translation of the key (CROSS)? Is recall bound to the queried key (BIND)?
Each must hold in at least two of three seeds, with no seed below the line.

**Claim scope.** This is an admission-gate benchmark outcome on one
from-scratch architecture at one scale (evidence level "benchmark", status
"admission pass", `docs/evidence-model.md`). It is not architecture-causal:
there is no matched control (rule 8). It makes no claim about any
equivariance loss, about production full-attention hybrids, or about other
windows, sizes or token budgets. PASS licenses only a gauntlet for E7's
phase-1 grid.

**Why the dossier asks it.** The corrected question (dossier section 16)
asks whether a loss that matches the recurrent-state write for a fact across
its translations improves cross-lingual recall where attention cannot reach
the fact. That question is only testable if a small from-scratch model
carries facts through the state at all, in-language and across languages.
In frozen full-attention hybrids the state does not carry retrieved facts:
recurrence-only exact retrieval is 0.00 on Qwen3.5-4B ([2609.04434](https://arxiv.org/abs/2609.04434),
Table 1), and recurrent interventions recover 0.2-3.6% against 96-100% for KV
([2609.33093](https://arxiv.org/abs/2609.33093) Sec. 4.1). So the test needs a
model in which attention structurally cannot reach the fact.

## Strategic Fit and Why Now

- **Program position.** E7 is the last item of the backfill queue
  (`program/backlog.md`, order 8; dossier rank 16 of 18, recommendation
  BACKFILL, lowest judge correctness 4). D67 restarted it, with E3, E5, C5 and
  S2, after Q2 S1a's result (D66). It uses idle H100s that no main question
  needs. Its first step is under 8 GPU-h, so a scored, reviewed package is
  actionable within the program without D24.
- **What the gate decides.**
  - Whether E7's from-scratch path is viable at 134M and 1B tokens.
  - If it is not, why: the state does not carry facts (FAIL_MONO); the state
    carries facts but not cross-lingual matches while attention in-window
    does (FAIL_CROSS state-specific); there is no cross-lingual matching even
    in-window (FAIL_CROSS representational); or seeds disagree (LOTTERY).
  - Each answer selects a different successor: the dossier's port to the
    2610.06750 LoRA setting; a lock-in redesign; or nothing. The
    state-specific sub-label is the most interesting outcome for E7, because
    it is the gap a write loss would target, measured in a model where
    in-window matching works.
- **The kill-shot cell's value-of-information argument, answered.** The
  cell argued that no G1 outcome can kill or confirm the equivariance
  question, and that a failure is predictable from the literature. Three
  points answer it, and one concession stands.
  - The literature's calibrations are for other instruments: parametric
    knowledge (2609.19291), word translation without parallel data
    (2604.17633), and a 4-way likelihood choice on pretrained checkpoints
    (2609.33093). The one in-context, small-model, coherent-code-switching
    measurement (2609.30535) points the other way.
  - The B1, B2 and B3 decomposition turns a failure into a diagnosis.
  - The futility rule caps the cost of a monolingual failure at about 1.92
    GPU-h. The most likely failure, FAIL_CROSS, still costs the full 4.87
    GPU-h central.
  - The gate is still a weak lever on E7's main question. The proposal says
    so (owner's prior PASS about 0.1) and does not claim otherwise.
- **Why now.** Hybrid multilinguality, memory-pathway balancing and
  recurrent-write analysis all appeared between 2026-09-03 and 2026-10-07
  (2609.04434, 2609.33093, 2609.35378, 2610.06750, 2610.10114). None of
  these papers, as read, tests state-carried cross-lingual recall with
  attention structurally excluded. A small, cheap instrument result is timely and
  publishable as a short note in either direction.
- **Assets checked, not assumed** (asset cell, synthesis): 8 idle H100s
  (`squeue` empty at 21:25 UTC); the measured image is still on the host; fla
  0.5.2 and tilelang are present, while flash-attn, sentencepiece, datasets
  and datasketch are absent, so SWA uses torch `flex_attention` and the
  tokenizer uses `tokenizers`. Data on host is about 0.25B tokens of K1 slices
  against the 1.04B needed, so new downloads are required under D1. FLORES+
  is gated; NTREX-128 is not. No G1 code exists.

## Primary-Source Evidence

Claim registry (ARS claim-verification protocol). Every row has a URL, a
date, a locator and a read status. "Full" means the full text was read by a
cell and the quoted span re-checked by synthesis in the cell's saved text.
The bundle holds a hashed snapshot of every cited URL.

| ID | Claim | Source and date | Locator | Status |
|---|---|---|---|---|
| C01 | Recurrent-only (attention blocked across segment boundaries, state carried) and attention-only (state reset at boundaries) conditions; an auxiliary loss on a pass with attention to preceding context masked; LoRA rank 16, steps halved to match compute; QA 34.6% to 38.5% and recurrent-only 5.0% to 22.8% on Qwen3.5-4B; no multilingual content | [2610.06750](https://arxiv.org/abs/2610.06750) v1, 2026-10-05 | Sec. 3 "Training"; Sec. 4.1; Sec. 5.1; Sec. 5.2 | Full |
| C02 | Same work as an ICLR 2027 submission, created 2026-09-18; the code repository has no licence | [OpenReview nIDJ2pPPOB](https://openreview.net/forum?id=nIDJ2pPPOB); [code](https://github.com/amy-hyunji/Balancing-Memory-Pathways) | search payload; GitHub API license=null | Abstract-only (UNVERIFIABLE_ACCESS for the PDF) |
| C03 | Qwen3.5-4B: KV retrieve 1.00 / 0.00 / 0.89 and language following 0.97 / 0.70 / 0.01 (full / recurrent-only / KV-only) | [2609.04434](https://arxiv.org/abs/2609.04434) v1, 2026-09-03 | Table 1 | Full |
| C04 | Near-matched hybrid GDN-340M: recurrent replacement recovers under 1% against over 99% for KV; Qwen3.5-4B 0.2-3.6% against 96-100%; scored as a 4-way likelihood choice | [2609.33093](https://arxiv.org/abs/2609.33093) v1, 2026-09-27 | Sec. 2.3; Sec. 4.1 | Full |
| C05 | Qwen3.5 has less cross-lingual alignment in 10/13 languages; SWA hybrids show no recurrent-style reorganization; 1B-token runs have not converged | [2609.35378](https://arxiv.org/abs/2609.35378) v1, 2026-09-28 | Finding 5; Finding 7; Sec. 6.3 | Full |
| C06 | GatedDeltaNet-H1 is GDN plus SWA, trained with a 2K window | [2412.06464](https://arxiv.org/abs/2412.06464) v3, ICLR 2025 | Sec. 3, "Hybrid models" paragraph; Sec. 4 setup ("sliding window size of 2K") | Full |
| C07 | The receptive field after l SWA layers is l w; SWA with 4 sinks matches or beats retrofitted linear attention | [2608.28444](https://arxiv.org/abs/2608.28444) v2, 2026-10-04 | Sec. 2.2; Table 1 | Full |
| C08 | After k attention layers information moves up to k x W tokens | [2310.06825](https://arxiv.org/abs/2310.06825), 2023-10-10 | §2 | Full |
| C09 | Latent information relay in SWA-trained models: Mistral 7B 89% at offset +10 with the code evicted; with a gap of at least 512 filler tokens, Glimmer averages 62.9% and Mistral 39.9% (4-way choice); models not trained with SWA stay near chance | [2609.34049](https://arxiv.org/abs/2609.34049) v1, 2026-09-28 | Sec. 4.3; Sec. 4.4 | Full |
| C10 | Larger sliding windows hurt long-context recall in SWA plus xLSTM hybrids (1.4B, 150B tokens) | [2509.24552](https://arxiv.org/abs/2509.24552) v3, 2026-05-04 | Abstract; Sec. 4.1-4.3 | Full |
| C11 | "Large-Window Laziness": larger windows delay long-range retrieval; design mainly changes emergence speed | [2606.15378](https://arxiv.org/abs/2606.15378) v1, 2026-06-13 | Abstract; Sec. 1 | Full |
| C12 | "Short-Context Learning Trap" and window effects in SWA hybrids | [2610.10114](https://arxiv.org/abs/2610.10114), 2026-10-07 | Abstract; Takeaways T2, T5 | Full |
| C13 | Associative recall in fixed-state cells: a distance curriculum lifts 0.021 to 1.000; lock-in 1/10 to 7/10 seeds; time ramp 0/6, accuracy-gated 6/6 | [2609.16183](https://arxiv.org/abs/2609.16183) v1, 2026-09-14 | Abstract; Sec. 1 | Full; first-party, self-labelled preliminary |
| C14 | 45 runs (9 seeds x 5 sizes) are consistent across seeds; outliers have loss spikes | [2503.09543](https://arxiv.org/abs/2503.09543), ICLR 2025 | Abstract; Sec. 4 | Full |
| C15 | First translations without token overlap at about 11B tokens (1.7B, 9 languages, no parallel data) | [2604.17633](https://arxiv.org/abs/2604.17633) v1, 2026-04-19 | Sec. 5 Phase II | Full |
| C16 | Activation-alignment losses in 360M bilingual pretraining give CLeq 2.5% against 0.9%; word-wise translation 12.6% | [2609.19291](https://arxiv.org/abs/2609.19291) v1, 2026-09-16 | Fig. 1; Sec. 4.2; App. A.4 | Full |
| C17 | Parallel data has minimal effect on cross-lingual alignment | [2603.29026](https://arxiv.org/abs/2603.29026) v1, 2026-03-30 | Abstract | Full |
| C18 | Coherent code-switching curricula at GPT-2-small shape: cross-script bitext retrieval P@1 61.4% against 5.5% on 997 FLORES+ sentences (CSLS) | [2609.30535](https://arxiv.org/abs/2609.30535), 2026-09-24 | Sec. 5; Sec. 6; App. D | Full |
| C19 | Language-specific components (LEACE) separated; language-agnostic part aligned by token-level optimal transport | [2609.06381](https://arxiv.org/abs/2609.06381) v1, 2026-09-06 | Sec. 3.1 | Full |
| C20 | MoE router outputs as a cross-lingual alignment target (v2) | [2610.01921](https://arxiv.org/abs/2610.01921) v2, 2026-10-02 | Abstract | Full |
| C21 | Memory consistency loss aligning an SWA-plus-recurrent decoder's memory to full-attention targets | [2608.02870](https://arxiv.org/abs/2608.02870) v2, 2026-08-05 | Abstract | Full |
| C22 | CHARTA: attention-free delta-rule LM with auxiliary supervision of task-relevant state | [OpenReview QvfwNCiyPg](https://openreview.net/forum?id=QvfwNCiyPg), 2026-09-15 | search payload | Abstract-only |
| C23 | MAPP: complete alignment eliminates language identity | [OpenReview Nol0BTGPR3](https://openreview.net/forum?id=Nol0BTGPR3), 2026-09-19 | search payload | Abstract-only |
| C24 | Writing a different fact into post-attention recurrent memory multiplies the answer's odds by 1.3-2.7 | [2609.32942](https://arxiv.org/abs/2609.32942) v1, 2026-09-26 | Abstract | Full |
| C25 | A 14M DeltaNet variant trained on synthetic episodes reaches 99.95% when choosing among the sequence's values, with filler to 1,798 tokens; parameter-matched Transformer and vector baselines stay near chance | [2610.00232](https://arxiv.org/abs/2610.00232), 2026-09-23 | Abstract; Sec. 1 | Abstract and introduction (synthesis) |
| C26 | Chrono initialization for long dependencies in gated RNNs | [1804.11188](https://arxiv.org/abs/1804.11188), ICLR 2018 | §2 Eq. 16 | Full |
| C27 | Discontinuous metrics create apparent thresholds | [2304.15004](https://arxiv.org/abs/2304.15004), 2023-04-28 | §2-3 | Full |
| C28 | A constant LR with a 20% (1 - sqrt) cooldown matches cosine and can be reused across lengths | [2405.18392](https://arxiv.org/abs/2405.18392), 2024-05-28 | §3 | Full |
| C29 | Tuning is the single most important ingredient of small-scale studies | [2608.11859](https://arxiv.org/abs/2608.11859), 2026-08-12 | Fig. 5 | Full |
| C30 | At 77-79M, the early learning rate and the window change induction formation and recall | [2609.15545](https://arxiv.org/abs/2609.15545) v2, 2026-09-15 | Sec. 2; App. D.3 | Full |
| C31 | Noise as the relative standard deviation over final checkpoints | [2508.13144](https://arxiv.org/abs/2508.13144), 2025-08-18 | §2 | Full |
| C32 | Language-sensitive and language-neutral subspaces after mean centring | [2205.10964](https://arxiv.org/abs/2205.10964), EMNLP 2022 | §3-4 | Full |
| C33 | Samba 1.7B needed passkey fine-tuning before beyond-window retrieval | [2406.07522](https://arxiv.org/abs/2406.07522), ICLR 2025 | §3.3; App. C | Full |
| C34 | LR transfer under μP for hybrid Transformer-SSMs (not GDN) | [2610.01172](https://arxiv.org/abs/2610.01172), 2026-10-01 | Abstract | Full |
| C35 | Pair-dependent onset of cross-lingual transfer during pretraining | [2205.11758](https://arxiv.org/abs/2205.11758), 2022-05-24 | §4-5 | Full |
| C36 | Explicit alignment objectives did not robustly help multilingual encoders | [2010.02537](https://arxiv.org/abs/2010.02537), EMNLP 2020 | Abstract | Full |
| C37 | fla 0.5.2 GatedDeltaNet: short convolution kernel 4 (default on); A ~ U(0, 16), dt log-uniform on [0.001, 0.1] | [fla v0.5.2 gated_deltanet.py](https://github.com/fla-org/flash-linear-attention/blob/v0.5.2/fla/layers/gated_deltanet.py) | L96-99, L151-168 | Source read (cross-domain cell copy) |
| C38 | Measured 134M throughput: 282,501.4 tokens/s, 133.96M parameters, eager, random tokens, full causal attention at 2,048, batch 16, Slurm 359 | repository receipt `legacy/research/evidence/infrastructure/fla-throughput-h100-2026-09-01.json` | runs[1] | Repository |
| C39 | NTREX-128: CC BY-SA 4.0, deu / zho-CN / tha, head 468c6b69 | [NTREX](https://github.com/MicrosoftTranslator/NTREX) | README; LANGUAGES.tsv | Read |
| C40 | FLORES+ gated=auto, CC BY-SA 4.0, sha e707e62e | [flores_plus](https://huggingface.co/datasets/openlanguagedata/flores_plus) | HF API | Read |
| C41 | SCB-MT-EN-TH-2020 CC BY-SA 4.0 (rev 613aad4a); ParaDocs Apache-2.0 (rev f80095af); FineWeb ODC-By (rev 9bb295dd); FineWeb-2 ODC-By (rev af9c1333) | [scb_mt_enth_2020](https://huggingface.co/datasets/airesearch/scb_mt_enth_2020); [paradocs](https://huggingface.co/datasets/jhu-clsp/paradocs); [fineweb](https://huggingface.co/datasets/HuggingFaceFW/fineweb); [fineweb-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | HF API and README | Read |
| C42 | Cross-lingual in-context retrieval forms in post-training; pretraining scale alone does not improve it | [2504.10906](https://arxiv.org/abs/2504.10906), 2025-04-15 | Abstract | Full |
| C43 | The legacy phase-0 object doctor still passes on main: 11/11 gates, payload SHA-256 equal to the registered value | asset cell run, `compute/legacy-phase0-doctor-main.json` | payload_sha256 e94aefff... | Repository rerun |

First-party labels: C13 (self-labelled preliminary) and any number from a
README or blog. No number in this proposal comes from X or Reddit.

## Closest Prior Work

The closest prior for the blind discrimination packet is **2610.06750**
(Balancing Memory Pathways, v1 2026-10-05; ICLR 2027 submission nIDJ2pPPOB,
2026-09-18). It measures how much a hybrid relies on its recurrent state with
exactly the masks this gate borrows (recurrent-only and attention-only
conditions, Sec. 4.1). It then adds the generic recurrent-path auxiliary loss
that E7's later arms must beat (Sec. 5.1). The runner-up for the gate itself
is **2509.24552** (SWAX): SWA plus a recurrent memory trained from scratch,
where long-context recall depends on the window.

| Prior | What it occupies | Delta of this gate |
|---|---|---|
| [2610.06750](https://arxiv.org/abs/2610.06750) Balancing Memory Pathways | Measures recurrent-only against attention-only use of past context in pretrained 4B hybrids with full attention (Qwen3.5-4B, Nemotron-H-4B), by eval-time masks at segment boundaries; a generic auxiliary loss on a masked-attention pass raises recurrent-only QA from 5.0% to 22.8%; monolingual; LoRA fine-tuning | The gate trains from scratch an SWA-only hybrid in which attention structurally cannot reach the fact (no eval-time mask needed beyond 1,560 positions), and asks about cross-lingual keys. It borrows the attention-only mask only as a diagnostic. It trains no auxiliary loss. E7's later contrast is a semantic write objective against exactly this generic loss |
| [2509.24552](https://arxiv.org/abs/2509.24552) SWAX | SWA plus xLSTM trained from scratch (1.4B, 7B; 150B tokens); larger windows under-train the recurrent memory; stochastic windows fix it | Gated DeltaNet, not xLSTM; 134M at 1B tokens; cross-lingual keys; state-necessity defined by the full receptive field, not one window. The window effect is inherited as a stated limit (M5) |
| [2609.04434](https://arxiv.org/abs/2609.04434) What Attention Recalls | Split-prefill on frozen Qwen3.5-4B and Falcon-H1: exact retrieval survives only through KV; output language survives through recurrence | Frozen full-attention hybrids; the gate uses a model whose attention cannot reach the fact. The output-language finding is why later arms need a guardrail (out of scope) |
| [2609.33093](https://arxiv.org/abs/2609.33093) How Linear Attention Remembers | Write-level analysis: facts enter pure GDN states through concentrated writes; in hybrids the state carries under 1% | Released checkpoints, monolingual, 4-way likelihood scoring. The gate measures exact recall of four-digit codes across languages in a hybrid where the state must carry |
| [2609.35378](https://arxiv.org/abs/2609.35378) Multilinguality in Hybrid Attention | Descriptive hybrid cross-lingual deficit; layer-ordering fixes by distillation; SWA hybrids do not reorganize | No state-level recall instrument; the measured layout puts attention at every fourth layer (recurrent-first), the ordering it finds slowest, which is inherited and disclosed |
| [2412.06464](https://arxiv.org/abs/2412.06464) GatedDeltaNet-H1 | The architecture family (GDN plus SWA, 2K window) | A0 is H1 with W = 512 at 134M. No architecture claim |
| [2610.00232](https://arxiv.org/abs/2610.00232) Constant-Memory Recall | A 14M DeltaNet variant on synthetic episodes keeps 32 pairs through 1,798 tokens of filler (forced choice among in-context values) | Natural-language keys, cross-lingual queries, LM pretraining rather than task training, and attention present but out of reach |
| [2609.16183](https://arxiv.org/abs/2609.16183) Anatomy of Associative Recall | Lock-in lottery and distance curricula in fixed-state cells | Motivates the three-seed rule and LOTTERY verdict; not occupying |
| [2609.19291](https://arxiv.org/abs/2609.19291), [2609.30535](https://arxiv.org/abs/2609.30535), [2603.29026](https://arxiv.org/abs/2603.29026) | Cross-lingual transfer in small from-scratch models: activation alignment null for parametric knowledge; code-switching curricula align representations; parallel data has minimal effect | Parametric knowledge or representation similarity, not in-context recall through a recurrent state; they set the priors for CROSS |
| [2609.06381](https://arxiv.org/abs/2609.06381) CAROT; MAPP; [2608.02870](https://arxiv.org/abs/2608.02870) Maglev; CHARTA; [2610.01921](https://arxiv.org/abs/2610.01921) | Subspace alignment in dense residuals; guardrail framing; losses on recurrent memory (monolingual); cross-lingual alignment of a non-residual object (MoE routers) | Priors for E7's later arms, not for this gate |

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| A0: GDN plus SWA hybrid, measured 134M shape, W = 512 | 2412.06464 (H1, 2K window) | Architecture family | Window and scale only; no architecture claim | High (occupied as architecture) |
| State-necessary distance bin (all facts beyond the state-free reach of 1,560) | 2608.28444 Sec. 2.2 and 2310.06825 §2 (receptive field l w); 2610.06750 Sec. 4.1 (eval-time masks) | The receptive-field arithmetic; the use of masks to isolate a pathway | Applied by construction to the evaluation design of a from-scratch SWA hybrid, with the GDN convolutions counted and checked by complex-step perturbation (S3) | Medium (a design detail, not a contribution) |
| Within-model decomposition: B1 direct, B2 relay, B3 state-necessary, state cut and fact-write ablation | 2610.06750 (recurrent-only and attention-only conditions); 2609.04434 (split-prefill) | Pathway isolation by masks or state swaps | Distance bins aligned to the receptive field, plus a fact-specific write ablation, on the same checkpoint | Medium |
| Cross-lingual state-necessary recall instrument (TP-MQAR-v2-G1): natural-sentence keys, surface-disjoint translated queries, four-digit codes, binding margin against the 1/8 copy floor | MLNeedle ([2408.10151](https://arxiv.org/abs/2408.10151)) and OneRuler ([2503.01996](https://arxiv.org/abs/2503.01996)) for cross-lingual needles in dense models (legacy citations, not re-read in this gauntlet); [2609.30634](https://arxiv.org/abs/2609.30634) for in-context binding capacity (abstract read by synthesis) | Cross-lingual retrieval framing | Facts beyond attention's reach, surface-disjoint keys, the copy floor stated and tested | Medium (instrument; collision risk medium) |
| Translation-pair objective on the recurrent write (later arms, not trained here) | 2610.06750 (generic recurrent-path loss); 2608.02870, CHARTA (losses on recurrent memory); 2609.06381 (subspace alignment in residuals); 2610.01921 (non-residual alignment) | Auxiliary losses on recurrent memory; cross-lingual alignment objectives | A semantic, translation-pair objective on the GDN write, in the regime where attention cannot reach the fact | Low to medium (NARROWED, not OCCUPIED) |

Novelty wording: No direct prior art found through 2026-10-10 under the
coverage recorded above: 97 orx discover queries across four cells,
including keyword queries with the mechanism's exact terms and each closest
prior's title phrase, embedding queries with the mechanism in plain words,
and OpenAlex queries; 70 paper reads; 19 OpenReview searches (abstract-only);
4 web searches and 1 author page for the ACL Anthology. The exact queries
and returned ids are in `evidence/2026-10-10-e7-equivariant-writes-g1/query-log.json`.
Screening counts across the cells (PRISMA-style):
- identified: 1,295 records returned by the counted queries, 727 unique ids,
  550 of them dated 2026;
- screened: all titles, by the cells;
- abstracts opened: about 45 in the frontier cell (the other cells did not
  count theirs);
- included: 52 unique papers read in full (67 cell reads with overlap), plus
  2 abstracts read by synthesis. None trains a translation-pair objective on a
recurrent-state write, and none measures cross-lingual recall through a
recurrent state with attention structurally excluded. This is not a claim of
global novelty. The coverage limits in the header apply.

## Mechanism and Falsifiable Predictions

**Mechanism of the measurement.** Each GDN head keeps a matrix state S
updated by the gated delta rule. Per token, S decays by alpha, erases along
the key and writes the value-key outer product (fla convention). The layer
emits S q into the residual stream.

How a fact must reach the answer:
- A fact `key [kv] dddd` that sits at least 1,600 positions before the
  answer can influence the answer only through some GDN head's state crossing
  that gap. The SWA layers reach 511 positions each, the short convolutions
  3 each, and nothing else crosses positions (S3).
- For a correct monolingual answer, the code's digits must be written into a
  state with a key that a later query, computed from the repeated key
  sentence, reads back.
- For a correct cross-lingual answer, the query computed from the
  translation must address the same stored association. The translation
  shares no surface token with any fact key, so the representations feeding
  the GDN keys and queries must be partly language-invariant.

Why it might fail:
- Retention: initial timescales above 1,600 tokens exist in about 1% of heads
  (S3, fla 0.5.2 initialization).
- Interference: 8 facts plus filler in a 64 x 64 state per head.
- Laziness: attention solves half of the curriculum within its reach.
- Undertraining: 7.5 tokens per parameter.
- For CROSS only: missing language-invariant keys at this scale and token
  budget.

The decomposition separates these causes:
- B1 tests whether matching works when attention can reach the fact.
- B2 under the state cut tests how much attention relay carries.
- B3 tests the state.
- The fact-write ablation tests that B3 recall runs through the queried
  fact's own write.
- The decay timescales test retention.
- CSLS retrieval tests whether a shared representation exists.

**Predictions, each with its falsifier** (thresholds as registered; per seed
at 1B tokens; a line passes on at least two seeds ABOVE and none BELOW).

- **P1 (instrument).** I1, monolingual EM with the fact inside one window
  (B1), is at least 0.80. Falsified, giving INSTRUMENT_INVALID and no
  statement about the state, if I1 is BELOW 0.80 in at least two seeds.
- **P2 (state carries facts in-language).** MONO is at least 0.60 on B3.
  Falsified, giving FAIL_MONO, if MONO is BELOW 0.60 in at least two seeds,
  or by the futility rule (seed 42's upper bound under 0.30).
- **P3 (state carries cross-lingual matches).** CROSS is at least 0.15 on
  B3, surface-disjoint, with BIND above 0. Falsified, giving FAIL_CROSS, if
  CROSS is BELOW 0.15 (or BIND BELOW 0) in at least two seeds while MONO
  passes.
- **P4 (reliability).** No line splits across seeds. Falsified, giving
  LOTTERY, if MONO or CROSS has a seed ABOVE and a seed BELOW.
- **P5 (identification checks, registered kill criteria for reading B3 as
  state-carried).** Both use the binding margin (EM_t minus the mean
  distractor EM_j), so the copy floor cancels.
  - CUT: under the state cut, B3's binding margin must have a 90% lower
    bound of at most 0. A positive margin in at least two seeds means the
    reach bound or the cut is wrong, and the verdict is INSTRUMENT_INVALID.
  - ABLATION: under the fact-write ablation, B3's binding margin must fall
    to at most half its unablated value in at least two seeds. If it does
    not, PASS is withheld (INCONCLUSIVE, "identification not established").
- **P6 (descriptive, no decision).** Under FAIL_CROSS, X1 (B1 cross-lingual
  EM) sets the sub-label: "state-specific" if ABOVE 0.15 in at least two
  seeds, "representational" if BELOW in at least two.

## Cheapest Decisive Pilot

There is no executable pilot for this gate. Nothing has run on a GPU, and
the harness does not exist. The cheapest decisive experiment is the
registered gate itself, sized by S2:

| Job | What | Cap |
|---|---|---:|
| J1 | Smoke (300 steps, real mixture, seed 42) with gates: finite and decreasing loss, cached and uncached evaluator equal, state cut equal to a fresh zero-state pass, throughput at least 179,329 tokens/s. Then the step-overhead probe (A0; A0 plus A1 write extraction; A0 plus one 2610.06750-style auxiliary pass; 200 steps each, three repeats), then the three-point LR sweep | 34 min |
| J2 | Fresh-job resume from J1's step-200 checkpoint (rule 7) | 13 min |
| J3 | Conditional LR extension | 18 min |
| T42 | 1B-token trunk with the 200M branch, then all reads | 133 min |
| T43, T44 | Same, only if seed 42 does not meet the futility rule | 133 min each |

The decisive read is the 1B checkpoint of the three trunks, on B3. The
experiment is decisive in the registered sense: every outcome maps to one
verdict and one action (Negative-Result Value). It is not decisive for E7's
main question, which needs the grid.

CPU evidence that exists now, none of it a pilot:
- S1 (`compute/gate-sim.py`, operating characteristics of the decision rule);
- S2 (`compute/cost-model.py`);
- S3 (`compute/reach-doctor.py`, the reach bound on a NumPy stand-in of the
  layer graph, PASS in three seeds);
- the legacy phase-0 object doctor, rerun on main by the asset cell
  (PHASE0_OBJECT_DOCTOR_PASS, 11/11, payload hash equal to the registered
  one). It tests synthetic W, D and P objects, not anything G1 depends on.

The executable-pilot cap (79) applies.

## Controls, Baselines, and Ablations

Within the same checkpoint, at no training cost:
- **B1 direct bin.** The positive control (I1) and the in-window
  cross-lingual reference (X1).
- **B2 relay bin under the state cut.** The share of relay-range recall that
  attention alone carries (the frontier and kill-shot cells' relay concern,
  measured rather than assumed).
- **B3 under the state cut.** The no-information check of the reach bound.
- **Fact-write ablation on B3.** Recall must run through the queried fact's
  write.

On the instrument:
- **Binding-free reference.** The distractor codes' EM in the same prompts
  gives the copy floor per prompt; BIND tests the margin.
- **Surface filter.** No shared token, digit string or four-character
  subword with any of the eight keys.
- **Reserved codes.** 2,000 test codes never seen in training.
- **No digits in keys or filler.**
- **Balanced target slot.**
- **Leakage controls in the cpu-doctor node.** A retrieval-impossible prompt
  (key absent from the facts) and a value-permutation control must give EM at
  the no-information level under an oracle reader.

Training-side controls:
- the LR sweep on held-out LM loss, with the instrument never read;
- three seeds with seed-specific data order;
- a held-out LM loss curve and the beyond-reach in-context loss gap, as
  non-recall checks that the state is used at all.

Baselines not run, and why:
- **A same-depth pure SWA plus sinks model** (rule 10's 2026 baseline,
  2608.28444). It is mandatory for a recall claim, which G1 does not make.
  For state necessity, B3 under the state cut answers the same question on
  the same weights.
- **A dense full-attention model** (the legacy A4 rescue). B1 gives an
  in-model in-window reference. A dense model would answer "is cross-lingual
  matching learnable at this scale with full attention", which X1 answers
  for this model's own attention.
- **An SWA-128 or stochastic-window sibling** (M5). It is a successor, named
  in any FAIL verdict.
- **QED and MARCH.** Mandatory for a recall or interference claim, which G1
  does not make.

Ablations out of scope: every equivariance arm, A5 no-bitext, a curriculum
ramp, chrono initialization.

## Evaluation, Statistics, and Leakage Checks

- **Unit and estimator.** The prompt; per seed, the equal-weight mean of
  cell means. 90% sentence-cluster bootstrap (B = 2,000, seed 42): every
  prompt that queries a resampled sentence, in any cell, moves together.
- **Lines.** I1 0.80, MONO 0.60, CROSS 0.15, BIND 0. Per seed ABOVE,
  BELOW or UNRESOLVED. A line passes on at least two seeds ABOVE and none
  BELOW. Verdicts in order: INSTRUMENT_INVALID, PASS, LOTTERY, FAIL_MONO,
  FAIL_CROSS (with a sub-label), INCONCLUSIVE. A futility stop after seed 42
  applies if MONO's upper bound is under 0.30.
- **Operating characteristics** (S1, 1,000 replicates per scenario, seeds
  42, 43 and 44; every distribution assumed):
  - Half-widths are 0.013 at the CROSS line and 0.020 at the MONO line.
  - Coverage at nominal 0.90 is 0.933 for the bootstrap and 0.940 for CR1;
    the two classify the same in 0.993 of draws.
  - At seed SD 3 points: P(PASS) is 0.717 with every line 5 points above its
    threshold and 0.005 with every line at its threshold.
  - At seed SD 0: P(PASS) on MONO is 0.020 at the line, 0.517 at +2 and 0.997
    at +5.
  - At seed SD 3 points: P(PASS) on CROSS is 0.155 at the line and 0.902 at
    +5; P(FAIL_CROSS) at 0.10 is 0.919.
  - The binding-free null (copying an in-context code) never passes.
  - A lock-in mixture with pi = 0.7 gives PASS 0.368 and LOTTERY 0.613
    without futility. The futility rule never removes a PASS.
  - Halving the prompts barely changes the power: seed variation dominates.
- **Multiplicity.** Four pre-registered lines in one conjunctive rule. The
  200M read and every diagnostic are descriptive. No line is tested twice.
- **Leakage and contamination.**
  - The instrument comes from NTREX-128's test half (documents split by a
    seed-42 hash), deduplicated against every training stream and the
    curriculum key pool by exact match and character 5-gram MinHash (Jaccard
    at least 0.5); matches are removed from training, never from the
    instrument.
  - The English side of NTREX-128 is WMT19 news, which Common Crawl may
    contain; dedup is the control, and the counts are reported.
  - Codes are reserved; digits are excluded from keys and filler.
  - The tokenizer is never trained on instrument text.
  - The curriculum never contains a cross-lingual query.
  - Prompt manifests are sealed before J1. Every read is logged against the
    registered read list; an unlisted read is reported as a leak.
- **Assumption checks.** Per-cell rates and the sentence-cluster design
  effect are reported. A cross cell under 150 eligible sentences is dropped
  before any model exists.
- **Missing data.** A diverged seed counts as BELOW on every line. An
  incomplete trunk counts as UNRESOLVED.
- **Red flags guarded.** No post-hoc bin choice (the bins follow from the
  receptive field). No metric switching (the EM lines are verbatim). No
  optional stopping beyond the registered futility rule.

## Compute and Reproducibility

Image lineage: the measured throughput (Slurm 359) used
`127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`
(`cotcodec-research:0b3ecef0-architecture`, image ID `sha256:38044666...`;
torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention and fla-core
0.5.2, triton 3.6.0, tilelang 0.1.13). The tilelang path is the workaround
for fla #640, the Hopper gated-backward guard under Triton below 3.7.1. The
newest architecture image (build 855, `sha256:500f3b02...`) has the same
library versions. The G1 image is built from the harness commit by the
project's CPU build job and pinned by digest before J1. No new dependency is
needed: `flex_attention` ships with torch 2.11, `tokenizers` 0.22.2 and
pyarrow are present, and MinHash is implemented in NumPy.

Launch path (dry run, then test-only, then submit; one GPU per job; none of
these manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v1-j1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v1-j1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v1-j1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`.
The same three steps follow for J2, J3, T42, T43 and T44. Every executable
step also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml`: `kind: cpu-doctor` for the reach test, the
analysis pipeline and the leakage controls, and `kind: slurm-manifest` for
the GPU jobs.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 8. The gate's caps sum to
7.733 GPU-h under D22 (J1 34 min, J2 13 min, J3 18 min, T42, T43 and T44 133
min each). This is the gate's compute, separate from the gauntlet's 0.3 GPU-h
reviewer budget.

Estimate (S2, `compute/cost-model.json`):
- Base: the measured 282,501.4 tokens/s.
- Assumptions: training time multiplier 1.25 central and 1.5 high; the
  evaluation forward rate 2.0 x and 1.5 x the base; start-up 180 or 300 s;
  compile and autotune 180 or 300 s; cap 1.2 x the high projection.
- Central total 4.87 GPU-h (three trunks at 1.47 each).
- If the futility rule fires after T42: 1.92 GPU-h.
- One seed would cost 1.92 central and 3.30 in caps, against the dossier's
  2.5.
- A trunk fits its cap only if J1 measures at least 179,329 tokens/s (63.5%
  of the eager measurement); otherwise INFEASIBLE_THROUGHPUT and a new
  registration.
- Evaluation is 160.35M forward tokens per seed, with eight candidate codes
  scored from a cached prefix (checked against uncached scoring in J1).

Checkpoints and resume:
- Atomic checkpoints every 15 minutes to persistent storage, and named
  checkpoints at 100M, 160M, 200M (branch), 400M, 800M, 960M, 980M and 1B.
- A SIGUSR1 handler writes a checkpoint. J2 checks that a fresh job resumed
  from step 200 matches the uninterrupted continuation: identical batch hash
  and step counts, and loss within max(2e-3, 3 x the measured run-to-run
  difference).
- At most two resumes per trunk, inside its cap.

Artifacts (public repository):
- configs, the tokenizer's vocabulary hash, the data manifest (ids,
  revisions, hashes);
- prompt manifests (ids, offsets, hashes);
- per-prompt predictions (EM_t, eight log-probabilities, per-digit
  correctness, copy flag);
- per-seed line tables, diagnostics, LR sweep losses, throughput and resume
  reports, realized GPU-hours from `scontrol`, and the read ledger.

Checkpoints stay on the host.

## Safety, Data Rights, and Monitorability

- **Models.** A 134M model trained from scratch on public text. No
  pretrained weights are loaded. Checkpoints are not released without a
  separate decision.
- **Data.**
  - FineWeb and FineWeb-2: ODC-By 1.0 with Common Crawl terms.
  - ParaDocs: Apache-2.0 packaging; the underlying ParaCrawl, News
    Commentary and Europarl texts keep their own terms.
  - ParaCrawl Bonus: CC0 packaging.
  - SCB-MT-EN-TH-2020 and NTREX-128: CC BY-SA 4.0.
  - FLORES+: CC BY-SA 4.0 and gated; accepting its terms is Kevin's action,
    so it is used only if he does.
  - Excluded: TED2020 (D4: NC-ND licence in an employer context) and General
    Translation customer data (ToS §3.1).
  - The public repository holds ids, offsets, hashes, metrics and
    predictions, but no source text. Any prompt text released later goes out
    under CC BY-SA 4.0 with attribution, as a separate artifact.
  - Downloads are recorded under D1 with source, revision, size and SHA-256.
- **Code provenance.** 2610.06750's repository has no licence, so its
  auxiliary pass is reimplemented from the paper, never vendored into this
  MIT repository.
- **Untrusted code.** None. The harness is reviewed project code (D7);
  outputs are digit strings scored by comparison.
- **Host.** No host job while an S1a VM or GPU job runs or is pending. The
  only host action of this gauntlet is the reviewer lane job. No host address
  or credential appears in this repository.
- **Monitorability.** Nothing is deployed and no policy is trained. Every
  read is logged.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Verdict | What it says (at 134M, 1B tokens, W = 512) | What it closes or opens |
|---|---|---|
| PASS | The recurrent state carries facts across at least 1,600 tokens in-language (at least 60%) and across languages (at least 15%, bound to the key), reliably over seeds | Licenses a gauntlet for E7's phase-1 grid. The grid needs a subspace or output-language guardrail, the 2610.06750 baseline, the SWA plus sinks baseline and D24 admission. A short instrument note |
| FAIL_CROSS, state-specific | The state carries facts in-language, and attention matches across languages in-window, but cross-lingual recall through the state fails | The exact gap a translation-equivariant write loss would target, measured cleanly. The dossier's port to the 2610.06750 LoRA setting, or a redesigned grid read on B1 and B2, decided by a new gauntlet. Publishable as "the state stores surface form" |
| FAIL_CROSS, representational | No cross-lingual matching even in-window at this scale and budget | The from-scratch path for E7 at 134M and 1B tokens. Consistent with 2609.19291 and 2604.17633, now for in-context recall. The dossier's port applies |
| FAIL_MONO (including futility) | The state does not carry facts across 1,600 tokens even in-language at this window, scale and budget | The from-scratch path at this configuration. An instrument-scaling fact (with the window caveat of 2509.24552). Under futility, a seed lottery is not excluded |
| LOTTERY | Seeds disagree across a line | Any three-seed arm comparison on this instrument. A successor needs a lock-in design (for example, an accuracy-gated distance curriculum, 2609.16183) under a new id |
| INCONCLUSIVE | One or more lines unresolved | Nothing. The intervals size a successor |
| INSTRUMENT_INVALID | The model cannot recall a fact inside its own window, or the state cut does not abolish B3 recall | A code fix under a new id. No scientific statement |
| INFEASIBLE_THROUGHPUT | J1 measures below 179,329 tokens/s | A re-priced registration |

The most likely outcomes, by the owner's prior, are FAIL_CROSS
(representational more than state-specific) or FAIL_MONO. Each is a cheap,
clean negative that closes E7's from-scratch path at this scale with a
measured reason.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac. 97 counted discover queries with returned ids and raw-output SHA-256, plus 63 uncounted log entries (OpenReview, web, GitHub, Hugging Face, paper reads). Cutoff 2026-10-10. Degraded coverage recorded: no Semantic Scholar, arXiv API, OpenReview full texts, Anthology index, patents or social media; alphaXiv version lag (`doctors/source.json`) | Run Semantic Scholar forward citations for 2610.06750, 2609.04434 and 2509.24552 through the host relay |
| Citation | PASS | Claim registry C01 to C43 with locators, dates and read status. Every cited URL snapshotted with its HTTP status and, for arXiv, its version history. OpenReview rows marked UNVERIFIABLE_ACCESS. C13 labelled first-party and preliminary. Seven dossier corrections (`doctors/citation.json`) | Read the ICLR 2027 PDFs (2610.06750's OpenReview version, CHARTA, MAPP) when accessible |
| Novelty | FAIL | No direct prior under the recorded coverage (NARROWED in the frontier and kill-shot cells). The blind closest-prior critic and the novelty refuter have not run; the ACL Anthology was checked only through web search (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter (53 queries remain; the reserve of 30 is intact) |
| Design | FAIL | Intervention, controls, falsifiers, metrics, leakage controls and decision rules are specified and simulated (S1), and the reach bound is checked (S3). But every distribution is assumed, the CUT and ABLATION identification checks are not simulated, and no harness exists (`doctors/design.json`) | Write the harness; run the cpu-doctor node (reach test on the real module graph, analysis recovery, leakage controls) |
| Compute | FAIL | No real model loop, adapter, manifest, container smoke or Slurm dry run. SWA-512 throughput on real data is unmeasured, and 1.04B tokens of data are not on the host (`doctors/compute.json`, `compute/attestations-not-run.md`) | Fetch data under D1 after S1a is clear; write the harness and the J1 manifest; dry run and test-only |
| Safety | PASS | Public licensed data with text kept out of the repository; NC data, gated data and customer data excluded; the unlicensed code reimplemented, not vendored; no untrusted code; host rule respected (`doctors/safety.json`) | none |

Protocols followed:
- Citation: the ARS claim-verification protocol (claim registry, locators,
  verdicts, UNVERIFIABLE_ACCESS).
- Design: the vendored K-Dense `experimental-design` and `statistical-power`
  skills (design before data, three-way decisions, operating characteristics
  by simulation).
- Evaluation: K-Dense `statistical-analysis` (clustered intervals).
- Novelty: K-Dense `literature-review` (PRISMA counts in the Novelty
  Ledger).
- The integrity gate (seven failure modes) is answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only while no S1a VM or GPU job is running)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; backfill rank 16 of 18, VoI argument answered in Strategic Fit |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01 to C43 in doctors/citation.json |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run; the gate claims no method novelty |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P1 to P6 with registered falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; B1/B2/B3 bins, state cut, fact-write ablation, binding guard |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S1 operating characteristics under assumed distributions |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; caps 7.733 GPU-h, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest, data not on host |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; ids and hashes only, gated and NC data excluded |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy waves 1-5 (2026-09-01) | not comparable | Phase 0 on a frozen hybrid; 57M grid at 200M tokens; doctor executable only on synthetic objects | Contract v5, phase-0 CPU doctor | Archived under legacy/; phase 0 pre-answered by 2609.04434 and 2609.33093 |
| dossier (2026-10-06) | not scored | Phase 0 pre-answered; output language rides the state; G1 at floor unestablished | Corrected question; G1 floor gate at 134M, 1B tokens | Recorded in the dossier, section 16 |
| new gauntlet, synthesis (2026-10-10) | not scored | "Beyond-window" is not state-only (reach 1,560); chance is 1/8; one seed | B3 state-necessary bin; within-model decomposition with registered CUT and ABLATION checks; binding guard; three seeds with LOTTERY and futility; NTREX-128; caps 7.733 GPU-h; S1, S2, S3 | Awaiting blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e7-equivariant-writes-g1.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-e7-equivariant-writes-g1/doctors/research-direction-doctor-output.json`.

Readings the doctor does not make for itself:
- "All declared budgets must be positive" comes from parsing the declared
  `gpu_hours=0.3` as an integer. The declared budget is honest and was not
  rounded up to pass.
- The doctor applies no 79 cap here, because its executable-pilot check is
  textual. By the gauntlet rule's cap table, this proposal is capped at 79
  (no executable pilot) and at 89 (no independent provider-distinct review),
  and it cannot reach 100 without D24's trust store.
- The doctor counts the three OpenReview snapshots as resolved because those
  pages return HTTP 200, but their bodies are a browser challenge.

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
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-e7/program/proposals/2026-10-10-e7-equivariant-writes-g1.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 49,
    "recognizedPrimaryUrls": 49
  },
  "status": "FAIL"
}
```
