# Research Direction: E5 first step, the per-token decay clock against everything else when English is re-segmented, on two attention-free delta-rule checkpoints (backfill E5, D20)

**Status:** draft for gauntlet wave 1 (program decision D67); synthesis by the single owner on 2026-10-10 from four independent discovery cells (frontier, kill-shot, cross-domain, asset and cost) of workflow gauntlet-e5-wave1; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/e5-gate-fertility-decomposition-v1.md` is a DRAFT, not frozen or admitted, with no ledger row; no executable pilot exists for this step; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design, simulations and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-10
**Coverage limits:** orx 0.2.2 only for literature search (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18; the alphaXiv keyword index leans to recent papers, so classic priors such as MambaExtend and Stuffed Mamba were reached by title, OpenAlex or direct fetch); 120 counted orx discover queries (frontier 47, kill-shot 24, cross-domain 43, asset 6, synthesis 0; one asset raw output was not saved and one OpenAlex query failed with HTTP 429); 57 paper reads by the cells (40 distinct papers; `orx paper --full` or alphaXiv report; full texts read by targeted section, not end to end), including the MambaExtend proceedings PDF, plus 10 OpenAlex metadata records; the OpenReview search API (9 term searches; most ICLR 2027 forum titles hidden or HTTP 403; note pages behind a browser challenge, not bypassed); 7 web searches (4 restricted to aclanthology.org or openreview.net; the Anthology's own index was not queried) and 2 ACL Anthology page fetches; arXiv abstract pages and version histories via arxiv.org and export.arxiv.org; the Hugging Face model, file-tree and dataset APIs; read-only ssh to the host (squeue empty at 21:41 UTC; cached cards, receipts and tokenizer files read by the kill-shot and asset cells); not searched: Semantic Scholar and the arXiv API (the host relay was not used), citation-graph traversal beyond OpenAlex, patents, X, Reddit, GitHub code search, Chinese-language venues; seven background sources added by synthesis were checked by abstract only (arXiv 2004.12265, 2404.03646, 1804.11188, 1609.07843, 2412.06464, 2503.14456, 2305.15425); several psychology sources are OpenAlex metadata or abstracts only; LongMamba, ReMamba and LAMB were not opened
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e5-gate-fertility-decomposition/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED: the frontier and kill-shot cells returned NARROWED, the
cross-domain cell STILL_OPEN with a broken design, and none returned
OCCUPIED. Each component is already partly occupied. The load-against-distance
decomposition in English on pretrained gated linear-attention models belongs to
Lee et al. ([2609.33093](https://arxiv.org/abs/2609.33093)). "Decay has no
measurable cost; interference dominates" is already shown in matched
from-scratch cells ([2609.16183](https://arxiv.org/abs/2609.16183)).
Training-free decay rescaling of frozen recurrent models is established
(MambaExtend, ICLR 2025; DeciMamba,
[2406.14528](https://arxiv.org/abs/2406.14528); Mamba Modulation,
[2509.19633](https://arxiv.org/abs/2509.19633)). Non-canonical re-segmentation
as a perturbation is studied on transformers
([2506.19004](https://arxiv.org/abs/2506.19004),
[2607.26831](https://arxiv.org/abs/2607.26831)). This proposal claims no new
mechanism and no new method family. Its residual is a measurement that none of
these runs: the share of a same-content re-segmentation cost carried by the
per-token decay pathway in attention-free pretrained checkpoints, identified by
holding that pathway at its canonical value.

The gauntlet's GPU budget (0.3 GPU-h) is for reviewer inference only. The
step's own compute (registered caps summing to 4.0 GPU-h, central estimate
1.26 GPU-h) is separate and runs only after a freeze. No host job was run for
this proposal.

## Scope and what changed from the dossier

This proposal covers only E5's first step: the language-free decomposition on
English, on m-a-p/1.3B-100B-GatedDeltaNet-pure at 930ed6ae and
fla-hub/rwkv7-1.5B-world at 004140ba, as the dossier states
(`program/evidence/2026-10-06/question-dossier.md`, section 13). Translation
work of any kind is out of scope.

The four cells were merged by mechanism, not by wording. Fourteen mechanisms
change the step as the dossier wrote it. Each row was re-checked by synthesis,
by simulation (S1 `compute/mech-sim.py`, S2 `compute/power-sim.py`), by a cost
model (S3 `compute/cost-model.py`), by a measurement on the subjects' real
tokenizers (S4 `compute/resegment.py`), by a full-text re-read, or by more
than one of these.

| # | Mechanism (cells that found it) | What it does to the dossier's step | Where handled |
|---:|---|---|---|
| M1 | **Halving every decay rate does not identify the decay share** (kill-shot, cross-domain, frontier). r = 2 keeps distractor writes longer as well as the target (Stuffed Mamba [2410.07145](https://arxiv.org/abs/2410.07145); SpectralShift's fast modes for state clearing, [2609.14320](https://arxiv.org/abs/2609.14320)), and leaves the delta-rule erase untouched ([2605.22791](https://arxiv.org/abs/2605.22791)). Synthesis confirmed it in S1: the r = 2 contrast dG at f = 2.7 is -1.2 to -3.3 points in a world with no decay share, -1.5 to -2.2 in a world where decay carries 22 to 25% of the cost, and -0.7 to +0.8 in one where it carries 15 to 17% | The primary decay arm is a **per-token decay clamp**: in the re-segmented run, each canonical token's pieces get their log-decays rescaled so they sum to the log-decay that token received in the canonical run of the same episode, at every layer and head (or channel). This holds the mediator at its canonical value (an exact mediator manipulation in the sense of Imai, Tingley and Yamamoto, [JRSS-A 2013](https://doi.org/10.1111/j.1467-985x.2012.01032.x)), so clamp minus native is the natural indirect effect through decay. r = 2 stays as a secondary arm | S1; registration "Interventions" |
| M2 | **An exact-match slope of an r x f interaction is scale-dependent** (cross-domain: Loftus, Wagenmakers et al. [2012](https://doi.org/10.3758/s13421-011-0158-0); the legacy simulator's EM slope of 14 with a flat logit slope) | The primary statistic is a paired simple effect at one fertility, clamp minus native, divided by ln f_p (a secant from f = 1, where the clamp is the identity), in the dossier's unit and against its line of 3 points per log-f unit. The log-probability and exact-match versions are reported | `compute/estimator.py`; registration "Primary estimand" |
| M3 | **Base checkpoints mis-generate after non-canonical text** (all three literature cells). Pretrained-only models given character-level context fail to write fluently (spelling at best 0.317) while still recognising the words ([2506.19004](https://arxiv.org/abs/2506.19004), Sec. 4.1); boundary changes cost even at matched length ([2607.26831](https://arxiv.org/abs/2607.26831), Sec. 5.2) | Only the retention passage is re-segmented; facts, query and codes keep canonical tokens; recall is forced choice among four codes scored as string log-likelihood from the cached state, with greedy exact match secondary. A matched-count boundary-only arm and a no-passage read check (ZERO) are added | Registration "Cells", "Readouts" |
| M4 | **Re-segmentation is not a pure token-count lever** (kill-shot: word recovery needs early within-word attention, [2603.10771](https://arxiv.org/abs/2603.10771); segmentation invariance comes mainly from post-training, [2606.15521](https://arxiv.org/abs/2606.15521); the short convolution dominates recall in matched cells, [2609.16183](https://arxiv.org/abs/2609.16183)) | The decomposition is stated as "the per-token decay clock against everything else". The remainder (natural direct effect) holds the extra writes and erasures, the short convolution or token shift, and the unfamiliar segmentation. A write-silenced passage (SIL) and a write-overlap ledger separate interference descriptively; facts-only and facts-plus-passage re-segmentation cells (FACT, BOTH) test the encoding channel | Mechanism section; registration "Reported regardless" |
| M5 | **Decay is visible only at low load, if at all** (cross-domain: the Waugh-Norman replication, [TQMP 2020](https://doi.org/10.20982/tqmp.16.2.r001); Lee et al. Fig. 7) | Primary loads are K = 1 and K = 4 pooled with equal weight; K = 16 is secondary | Registration "Primary estimand" |
| M6 | **The dossier's fund branch has no valid subject** (kill-shot). GDN-1.3B was trained only on English FineWeb-Edu ([2507.06457](https://arxiv.org/abs/2507.06457), Sec. 3); the RWKV World card lists en, zh, ja, ko, fr, ar, es, pt ([card](https://huggingface.co/fla-hub/rwkv7-1.5B-world)) | Consequences restated: KILL kills the phase-1 span-parity loss and closes D20; MATERIAL licenses only a successor gauntlet on a multilingual attention-free subject, and funds nothing by itself | Registration "Consequences" |
| M7 | **The prior predicts the kill** (kill-shot, frontier, cross-domain: Lee et al. Sec. 4.2; Boesch and Wee Sec. 4; Oberauer and Lewandowsky [2008](https://doi.org/10.1037/0033-295x.115.3.544)) | The step's value is a tight upper bound on the decay share. n is set by S2 so that P(KILL) is at least 0.91 when the true share is 0, for discordance up to 0.30, with a false-kill rate of 0.05 to 0.11 at the line. A separate NO_COST exit applies when there is no cost to decompose | S2; registration "Statistics" |
| M8 | **Lee et al.'s elapsed-context panel covers only its 340M models** (frontier, confirmed by synthesis: the Fig. 7 legend lists GLA-340M and GDN-340M; GDN-1.3B appears only in Fig. 8's load curve) | A FILL ladder (the passage lengthened with canonical text to each f's token count) runs Lee's elapsed arm on GDN-1.3B and RWKV-7 and gives an equivalent-distance scale | Registration "Cells" |
| M9 | **Answer codes tokenize differently by subject** (frontier, kill-shot; synthesis measured it in S4: subject G gives "▁" plus four single digits, subject R gives " NN" plus "NN" for all six codes tried) | Codes are never re-segmented in any cell; candidates are scored as string log-likelihood; subjects are compared only through within-subject contrasts | S4; registration "Data" |
| M10 | **Context ceiling** (frontier, asset): the m-a-p config sets max_position_embeddings 2048, while the release paper's Limitations state a 4,096-token window | Every episode is at most 1,900 tokens; the longest registered cell is about 1,736 | S3 |
| M11 | **Gates may already self-normalise** (Tallec and Ollivier, [1804.11188](https://arxiv.org/abs/1804.11188); cross-domain: HiPPO's step-size invariance, [2008.07669](https://arxiv.org/abs/2008.07669)) | The ratio R_F of summed piece log-decay to canonical log-decay is computed in every clamp pass; prediction P1 is registered; R_F near 1 means the clamp is near the identity and the decay share near 0 by construction | Registration "Readouts", "Predictions" |
| M12 | **Subject G has no licence** (asset, frontier): no model card, README, LICENSE or licence tag at 930ed6ae (HF API, 2026-10-10) | Use is conditional on Kevin's ruling (registration decision 1); the apache-2.0 fallback linear-moe-hub/Gated-Deltanet-1.3B (4 heads, no short conv, SlimPajama) is registered | Safety section |
| M13 | **Nothing executable exists** (asset). Subject G is not on the host and not in the registry; no episode builder, splitting rule or distractor corpus exists; the legacy doctor runs only from `legacy/` and has no load, interference or filler case; its orx node fails on main | Prerequisites 1 to 7 in the registration; a new versioned CPU doctor; the legacy doctor is not edited | Compute section |
| M14 | **The splitting rule was unspecified** (all cells; cross-domain: mean fertility hides how splits are allocated, single-token retention rate STRR, [2510.09947](https://arxiv.org/abs/2510.09947)) | A frozen refinement rule R(f, seed) and boundary rule B(seed), implemented and measured on both real tokenizers (S4): f = 2.7 is reached with no shortfall on 11 stand-in passages; 71% of canonical tokens are split; STRR over words falls from 0.72 (G) and 0.79 (R) to 0.10 and 0.11; B re-bounds only 12% (G) and 8% (R) of tokens, so it is descriptive only | S4; registration "Re-segmentation rules" |

Six corrections to the frozen dossier, recorded here because the dossier is
not edited:

1. "The m-a-p GDN-1.3B checkpoint has no model card, so training data
   undocumented": the card is missing, but the data is documented first-party:
   FineWeb-Edu, 100 billion tokens for the 1.3B models, trained with
   flash-linear-attention ([2507.06457](https://arxiv.org/abs/2507.06457),
   Sec. 3, v2 2026-06-24; frontier and asset cells, re-read by synthesis). The
   checkpoint also has no licence.
2. "128 to 1024 tokens costs 'only a modest decline'" is measured on GLA-340M
   and GDN-340M only (Lee et al., Fig. 7(b) legend), not on GDN-1.3B, and its
   filler is natural text that writes to the state, so it is decay plus filler
   interference, not decay alone.
3. "Using a halved decay rate as the intervention": r = 2 cannot identify the
   decay share (M1, S1).
4. "600 episodes per cell": S2 gives P(KILL | no decay share) of only 0.59 at
   discordance 0.30 with 600 episodes per load; 1,500 per load is registered.
5. "Fund the 16-language translation-paired run only if it reaches 3 or more
   on both": neither subject can carry that run (M6).
6. "~3 GPU-h": S3 gives a central 1.26 GPU-h and a high 3.29 GPU-h on assumed
   throughputs; registered caps sum to 4.0 GPU-h.

One correction to a discovery cell: the cross-domain cell argued that the
legacy simulator's duplicated pieces build in a decay-only world because
re-writing an identical key-value pair is nearly idempotent. S1's world W5
(duplicates without write normalisation, as in the legacy code) gives a decay
share of only 0.41 to 0.44: repeated identical writes compound the delta-rule
erase along their keys. A decay-only world needs write-normalised duplicates
(W1, share 1.00).

## Claim and Research Question

**Question.** On two frozen attention-free language models whose only memory
is a fixed-size recurrent state updated by a gated delta rule (subject G:
m-a-p/1.3B-100B-GatedDeltaNet-pure at
`930ed6ae4ac629c86cb9855bb3dcb0a0974a29aa`, scalar decay per head, short
convolution of width 4,
[model page](https://huggingface.co/m-a-p/1.3B-100B-GatedDeltaNet-pure);
subject R: fla-hub/rwkv7-1.5B-world at
`004140baad7a62d49a26d97508ef19cf09672328`, per-channel decay with in-context
removal and token shift,
[model page](https://huggingface.co/fla-hub/rwkv7-1.5B-world)), when the same
English retention passage is re-tokenized into f times as many tokens, how
much of the change in forced-choice recall of facts stored before the passage
is carried by the extra per-token decay mass, and how much by everything else?

The variable is the passage's tokenization (canonical; refined to
f in {1.5, 2.0, 2.7}; boundary-perturbed at f = 1; lengthened with canonical
text) crossed with the decay pathway (native, or clamped to its canonical
value) and the load K in {1, 4, 16}.

**Claim scope.** A frozen-checkpoint mechanism measurement at the Component
level of `docs/evidence-model.md`. It is not `architecture-causal` (hard rule
8: a retrofit on pretrained checkpoints is never an architecture claim) and
carries none of the four claim scopes; at most it is a prerequisite for a later
`portability-protocol` study. The only claims it can license are of the forms
"in these two checkpoints, on re-segmented English, the per-token decay
pathway carries (does not carry) at least 3 points of forced-choice recall per
unit of log fertility", "the re-segmentation cost is (is not) mostly carried
outside the decay pathway", and "the phase-1 span-parity loss is (is not)
killed".

**Hypothesis under test (H_clock).** For each subject s, the secant
beta_s = mean over K in {1, 4} of NIE_s(K, f_p) / ln f_p is at least 3 points,
with NIE_s(K, f) = mean over episodes of Y(clamp, f) - Y(native, f). The
registered reading is KILL when the upper end of the 90% cluster-bootstrap
interval of beta_s is below 3, MATERIAL when beta_s is at least 3 with its
lower end above 0, NO_COST when the total cost per log-f unit has its upper
end below 3, and INCONCLUSIVE otherwise.

## Strategic Fit and Why Now

E5 is item 7 of the backfill queue (`program/backlog.md`). D67 restarted every
remaining line once S1a's result was in, with E5's first step stated as a
3 GPU-h language-free decomposition. Three reasons to run this step before
anything else in D20:

- **It decides the phase-1 loss cheaply.** The same text can take up to 15
  times as many tokens in one language as in another
  ([2305.15425](https://arxiv.org/abs/2305.15425), abstract). The span-parity
  loss of `legacy/directions/20-semantic-clock-gate-parity.md` assumes that
  per-token gates charge such high-fertility text extra forgetting mass and
  that this mass costs recall. If re-segmented English, which holds language, content,
  tokenizer and data share fixed, shows no material cost through the decay
  pathway in the subjects where recall must pass through the state, the loss
  has nothing to fix, and it dies without any translation, Common Crawl or
  probe-QA work.
- **It extends the closest prior where that prior did not measure.** Lee et
  al. measured elapsed context only on 340M models, never intervened on decay,
  never used RWKV-7 in the load or distance arms, and had no tokenization axis
  ([2609.33093](https://arxiv.org/abs/2609.33093), Secs. 2.3 and 4.2, App. A;
  frontier cell, re-read by synthesis).
- **Its scope is honest about reach.** In deployed GDN hybrids recall flows
  through attention, not the recurrent state (Lee et al., Sec. 4.1: 0.2-3.6%
  recovered by recurrent interventions against 96-100% by KV interventions on
  Qwen3.5-4B; split-prefill drops exact retrieval to 0% when only the
  recurrent state is kept, [2609.04434](https://arxiv.org/abs/2609.04434)).
  Only attention-free subjects test the clock where it could matter.

The expected answer is a kill (the dossier, Lee et al., Boesch and Wee and the
psychology literature all point that way). That is why the design is built
for a tight upper bound and a clean NO_COST exit rather than for discovery.

## Primary-Source Evidence

Claim registry (full table with verdicts in `doctors/citation.json`). "Full"
means a cell read the full text with `orx paper --full`; "re-read" means
synthesis re-read the section in that text; "abstract" means only the arXiv
abstract page (snapshotted) or OpenAlex metadata was read.

| id | Claim | Source | Locator | Read |
|---|---|---|---|---|
| C01 | K 1 to 16 lowers recall by about 30-40 pp; 128 to 1024 filler tokens at K = 4 cause "only a modest decline" | [2609.33093](https://arxiv.org/abs/2609.33093) v1 2026-09-27 | Sec. 4.2, Fig. 7(a-b) | full, re-read |
| C02 | Elapsed-context panel legend lists GLA-340M and GDN-340M only; GDN-1.3B at K = 32 reaches 69% | same | Fig. 7 legend; Fig. 8; Sec. 4.2 | full, re-read |
| C03 | Recall scored among four balanced candidates by conditional likelihood; WikiText-103 source-disjoint passages; target logit margin | same | Sec. 2.3 | full, re-read |
| C04 | Exact decomposition of the state into contributions transformed by all later transitions (Eqs. 3-5) | same | Sec. 2.2 | full, re-read |
| C05 | Aligning a later write key with the target lowers the target margin by 0.27-0.44 logits | same | Sec. 4.2, Fig. 7(c) | full, re-read |
| C06 | m-a-p checkpoint commit 930ed6ae; 32,000-token Mistral vocabulary; 1.466B parameters | same | App. A | full, re-read |
| C07 | Hybrid Qwen3.5-4B: recurrent interventions recover 0.2-3.6%, KV interventions 96-100% | same | Sec. 4.1 | full (dossier VERIFIED; frontier) |
| C08 | Convolution dominates matched recall (about +0.5); decay has no measurable cost (0.561 vs 0.518 at K = 32, p = 0.86); distance gives a flat wall attributed to interference | [2609.16183](https://arxiv.org/abs/2609.16183) v1 2026-09-14 | Sec. 4 "Axis 3", Table 1, Sec. 5 | full, re-read |
| C09 | m-a-p models pretrained on FineWeb-Edu; 1.3B models on 100B tokens; 4,096-token window in Limitations | [2507.06457](https://arxiv.org/abs/2507.06457) v2 2026-06-24 | Sec. 3; Limitations | full, re-read |
| C10 | m-a-p config: max_position_embeddings 2048, 8 heads, head dim 256, conv 4; no licence or card | [model page](https://huggingface.co/m-a-p/1.3B-100B-GatedDeltaNet-pure) | config.json and HF API at 930ed6ae, 2026-10-10 | synthesis read |
| C11 | RWKV World card: apache-2.0; languages en, zh, ja, ko, fr, ar, es, pt | [model page](https://huggingface.co/fla-hub/rwkv7-1.5B-world) | card; HF API | frontier, kill-shot |
| C12 | Fallback GDN-1.3B: apache-2.0, SlimPajama, 4 heads, use_short_conv false | [model page](https://huggingface.co/linear-moe-hub/Gated-Deltanet-1.3B) | config.json and HF API at 87107937 | synthesis read |
| C13 | Pretrained-only models given character-level context fail to write fluently (spelling at best 0.317, grammaticality 0.260); Word Repeat 90.8 | [2506.19004](https://arxiv.org/abs/2506.19004) v2 2026-02-02 | Sec. 4.1, Fig. 3; Table 4 | full, re-read |
| C14 | Robustness to non-canonical tokenization does not generalise beyond English; drops of 23.7%, 11.4%, 9.9%; most of the gap survives length matching | [2607.26831](https://arxiv.org/abs/2607.26831) v1 2026-07-29 | Abstract; Sec. 5.2; App. Table 6 | full |
| C15 | Character-level robustness relies on early-layer attention among a word's characters | [2603.10771](https://arxiv.org/abs/2603.10771) | Abstract; Sec. 5 | full |
| C16 | Segmentation invariance arises mainly in post-training (OLMo-2 checkpoints) | [2606.15521](https://arxiv.org/abs/2606.15521) | Sec. 3.2 | full |
| C17 | Mamba-2 and RWKV-6 fail to forget beyond the training length; minimum training length to learn forgetting scales with state size | [2410.07145](https://arxiv.org/abs/2410.07145) v4 2026-01-13 | Abstract; Sec. 3 | full |
| C18 | SpectralShift rescales GDN alpha projections before continual pretraining; two factors, including "preservation of fast-decaying modes for state clearing" | [2609.14320](https://arxiv.org/abs/2609.14320) v1 2026-09-13 | Abstract; App. B.2; Sec. 5.3 | full, re-read |
| C19 | Training-free calibration of per-layer discretization scaling factors extends Mamba context | MambaExtend, [ICLR 2025 proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/file/f1922bd718528ac3eab114eabbbfa7a0-Paper-Conference.pdf) | Abstract; Sec. 3 | full (frontier, pdftotext), re-read abstract |
| C20 | Scaling the transition matrix A, not only the step, improves Mamba length generalisation | [2509.19633](https://arxiv.org/abs/2509.19633) | Abstract; Sec. 6.1 | full |
| C21 | DeciMamba: Mamba's limited length generalisation traced to the training-length receptive field; a context-extension method | [2406.14528](https://arxiv.org/abs/2406.14528) | Abstract | abstract |
| C22 | In Gated DeltaNet and KDA one scalar gate controls both erase and write | [2605.22791](https://arxiv.org/abs/2605.22791) | Abstract | abstract |
| C23 | Hybrids only; OneRULER at fixed token length; Qwen3.5 tokenizer 2.6x longer in Yoruba; deficit initially larger outside English | [2609.35378](https://arxiv.org/abs/2609.35378) v1 2026-09-28 | Sec. 4, Table 2 | full |
| C24 | REC-ONLY split-prefill drops KV retrieval to 0% in Qwen3.5-4B and Falcon-H1-3B; KV-ONLY keeps 64-98% | [2609.04434](https://arxiv.org/abs/2609.04434) | Sec. 4 | report |
| C25 | Length hurts even with whitespace or masked distractors (13.9% to 85%) | [2510.05381](https://arxiv.org/abs/2510.05381) | Secs. 4.1-4.2 | full |
| C26 | Learnable gates give quasi-invariance to time transformations | [1804.11188](https://arxiv.org/abs/1804.11188) | Abstract | abstract |
| C27 | Causal mediation with model components as mediators; natural direct and indirect effects | [2004.12265](https://arxiv.org/abs/2004.12265) | Abstract | abstract (synthesis addition) |
| C28 | Causal tracing and interchange interventions localise factual recall in Mamba | [2404.03646](https://arxiv.org/abs/2404.03646) | Abstract | abstract (synthesis addition) |
| C29 | Experimental designs that identify mechanisms by manipulating the mediator | [Imai et al. 2013](https://doi.org/10.1111/j.1467-985x.2012.01032.x) | Abstract (OpenAlex) | abstract |
| C30 | Filled delays impair; lengthening them adds little; interference model fits best | [Oberauer and Lewandowsky 2008](https://doi.org/10.1037/0033-295x.115.3.544) | Abstract (OpenAlex) | abstract |
| C31 | Noncrossover interactions are removable by monotone transforms | [Wagenmakers et al. 2012](https://doi.org/10.3758/s13421-011-0158-0) | Abstract (OpenAlex) | abstract |
| C32 | Fisher memory curve: a decaying linear memory trades signal for accumulated interference | [Ganguli et al. 2008](https://doi.org/10.1073/pnas.0804451105) | Abstract (OpenAlex) | abstract |
| C33 | WikiText-103 corpus | [1609.07843](https://arxiv.org/abs/1609.07843); [dataset](https://huggingface.co/datasets/Salesforce/wikitext) | CC BY-SA 3.0 and GFDL (HF tags) | abstract; HF API |
| C34 | fla 0.5.2 computes GDN's gate in-kernel from the a_proj output, A_log and dt_bias; RWKV-7's log-decay is -0.6065 sigmoid(w_lora) | [flash-linear-attention](https://github.com/fla-org/flash-linear-attention) | layer sources read by the asset cell; re-read by synthesis | code read |
| C35 | Measured training throughput 73,045 tok/s/GPU (422M GDN hybrid, fla 0.5.2 image) | `docs/h100-node.md` | table | repository |
| C36 | The same text can take up to 15 times as many tokens across languages | [2305.15425](https://arxiv.org/abs/2305.15425) | Abstract | abstract |
| C37 | The gated delta rule combines gating (rapid erasure) with the delta update (targeted modification) | [2412.06464](https://arxiv.org/abs/2412.06464) | Abstract | abstract |
| C38 | RWKV-7: generalised delta rule with vector-valued gating; models, data listing and code released under Apache 2.0 | [2503.14456](https://arxiv.org/abs/2503.14456) v2 | Abstract | abstract |
| C39 | Single-token retention rate as a tokenizer metric beside mean fertility | [2510.09947](https://arxiv.org/abs/2510.09947) | alphaXiv report | report |
| C40 | Tokenizer choice matters more for low-resource languages (transformers, 54 tokenizers) | [2610.12144](https://arxiv.org/abs/2610.12144) v1 2026-10-08 | Sec. 3 (report) | report |
| C41 | Recurrent LLMs overflow; chunked inference mitigates it | [2505.07793](https://arxiv.org/abs/2505.07793) | alphaXiv report | report |
| C42 | Lexical density limits effective context separately from length | [2606.06203](https://arxiv.org/abs/2606.06203) | Abstract | full |

First-party labels: every number from a model card (C11, C12) and the m-a-p
paper's own training description (C09) is first-party; no number in this
proposal comes from a blog or social post.

## Closest Prior Work

1. **Lee, Park, Kim and Ko, How Linear Attention Remembers
   ([2609.33093](https://arxiv.org/abs/2609.33093), v1 2026-09-27; full text
   read by three cells, Secs. 2.2-2.3, 4.1-4.2 and App. A re-read by
   synthesis).** Pretrained GLA-340M, GDN-340M and GDN-1.3B (the same m-a-p
   checkpoint at the same commit) plus hybrids. Controlled associative recall
   in WikiText-103 passages, four-candidate likelihood scoring, an exact
   contribution decomposition, donor-recipient patching of states, writes and
   reads, memory load against elapsed context, and key-overlap interventions.
   This is the closest prior: it owns the load-versus-distance framing in
   English on the same family. What it does not do: intervene on decay or
   gates; measure elapsed context on GDN-1.3B or RWKV-7; use tokenization or
   re-segmentation as the source of extra tokens; separate the decay pathway
   from filler writes (its filler writes to the state).
2. **Boesch and Wee, Anatomy of Associative Recall in Fixed-State
   Recurrences ([2609.16183](https://arxiv.org/abs/2609.16183), v1
   2026-09-14; full text read by the frontier and kill-shot cells; re-read by
   synthesis).** Matched from-scratch cells on synthetic masked recall along
   three single-knob axes (short convolution, rank-1 versus diagonal
   transition, decay). Decay has no measurable cost; distance through a
   haystack is a flat wall attributed to interference under sparse
   supervision. It occupies the "decay versus interference" wording, but in
   trained-from-scratch synthetic cells, by ablating decay in training, not
   by holding a pretrained model's decay mediator fixed, and with no
   tokenization axis.
3. **Training-free decay rescaling of frozen recurrent models.** MambaExtend
   (ICLR 2025: per-layer scaling factors of Mamba's discretization step,
   calibrated by gradient or zeroth-order search, frozen weights), DeciMamba
   ([2406.14528](https://arxiv.org/abs/2406.14528)) and Mamba Modulation
   ([2509.19633](https://arxiv.org/abs/2509.19633): scaling A). SpectralShift
   ([2609.14320](https://arxiv.org/abs/2609.14320)) reparameterises GDN's decay
   spectrum before continual pretraining. All aim at length extension; none
   ties the rescale to re-segmentation or uses it to decompose a cost. The
   dossier's r = 2 is a uniform special case of this family; the per-token
   clamp is a different object (position-specific, matched to another run's
   measured decay).
4. **Causal mediation by component intervention.** Vig et al.
   ([2004.12265](https://arxiv.org/abs/2004.12265)) estimate natural direct
   and indirect effects through neurons and heads; activation patching in
   Mamba localises factual recall
   ([2404.03646](https://arxiv.org/abs/2404.03646)); Lee et al. patch
   recurrent states and writes. The clamp is a mediator intervention of this
   family. Its specific move, patching only the decay channel of a
   re-segmented run with the canonical run's decay summed over each token's
   pieces (positions do not align one to one), was not found.
5. **Re-segmentation robustness on transformers.** Broken Tokens
   ([2506.19004](https://arxiv.org/abs/2506.19004)), Ghosh and Jyothi
   ([2607.26831](https://arxiv.org/abs/2607.26831)), word recovery
   ([2603.10771](https://arxiv.org/abs/2603.10771)) and retokenization
   symmetry ([2606.15521](https://arxiv.org/abs/2606.15521)). All
   transformers, all about whether models cope, none about which state
   pathway carries the cost.
6. **Multilingual hybrids and recurrent capacity.** Bandarkar et al.
   ([2609.35378](https://arxiv.org/abs/2609.35378)) describe hybrid
   multilinguality with OneRULER at fixed token length; no attention-free
   subject, no matched content, no decay surgery. Tokenizer choice matters
   more for low-resource languages in transformers
   ([2610.12144](https://arxiv.org/abs/2610.12144), report). Overflow in
   recurrent LLMs and its mitigation by chunked inference
   ([2505.07793](https://arxiv.org/abs/2505.07793), report) is a capacity and
   interference account with no tokenization axis.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Load against elapsed context in English on pretrained GDN | Lee et al. 2609.33093 | Same family, same GDN-1.3B checkpoint, WikiText passages, four-candidate likelihood | Elapsed arm on GDN-1.3B and RWKV-7 (Lee: 340M only); the extra tokens come from re-segmenting the same content | high |
| Decay versus interference | Boesch and Wee 2609.16183 | Same question in words | Pretrained checkpoints, not from-scratch cells; mediator held fixed at inference, not ablated in training; same-content re-segmentation axis | high |
| Decay rescale at inference | MambaExtend; DeciMamba 2406.14528; Mamba Modulation 2509.19633; SpectralShift 2609.14320 | Rescaling a frozen recurrent model's decay | Position-specific clamp to another run's measured decay, used as an identification instrument, not for length extension; r = 2 itself is not new and is secondary | high |
| Mediation by component intervention | Vig et al. 2004.12265; 2404.03646; Lee et al. patching | Natural direct and indirect effects through a model pathway | Mediator is the decay channel only; alignment across unequal segmentations by summing over each canonical token's pieces | medium |
| Re-segmentation as a perturbation | 2506.19004; 2607.26831; 2603.10771; 2606.15521 | Same-content non-canonical tokenization | Attention-free subjects; decomposed by state pathway; facts and answers kept canonical | high |
| Tokenizer fertility on recurrent or hybrid models | Bandarkar et al. 2609.35378; 2610.12144 | Token inflation as a concern | Matched content, no languages, a decay intervention, attention-free subjects | high |
| Gate self-normalisation ledger (R_F) | Tallec and Ollivier 1804.11188 (theory); legacy D20 direction | Gates as time warps | Measured per canonical token on re-segmented English in pretrained checkpoints | medium |

Novelty wording: No direct prior art found through 2026-10-10 under the
coverage recorded in this proposal's header: 120 counted orx discover queries
(alphaXiv keyword and embedding, OpenAlex; each closest prior's title phrase
and the mechanism in plain words among them, some bounded by
`--published-after`), 57 paper reads by the cells (40 distinct papers), 9
OpenReview term searches, 7 web searches and 2 ACL Anthology page fetches,
listed with every returned id in `query-log.json`. Screening counts (PRISMA
style): 1,244 records returned by the counted queries (frontier 594,
kill-shot 310, cross-domain 321, asset 19), 749 distinct ids; screened at
title or abstract: about 45 by the frontier cell's own count, not reported by
the other cells; 40 distinct papers opened (full text or report); 0 direct
priors. The combination "same-content English re-segmentation x
decay-pathway intervention x load, on attention-free pretrained checkpoints"
was not found; each component is partly occupied (above). The idea is a
recombination and a measurement, not a new mechanism.

Selected queries and the closest-prior ids they returned (full list in the
log): keyword "How Linear Attention Remembers" (frontier, kill-shot,
cross-domain) returned 2609.33093 first; keyword "Multilinguality in Hybrid
Attention" returned 2609.35378; keyword "SpectralShift Gated DeltaNet spectral
reparameterization" returned 2609.14320; keyword "RWKV-7 decay associative
recall" returned 2609.16183; keyword "Broken tokens non-canonical
tokenizations" returned 2607.26831 and 2506.19004; embedding "decomposing
recall loss in linear attention language models into state decay versus write
interference using causal interventions on gate values" (after 2026-06-01)
returned 2609.36322, 2609.33093, 2609.04434, 2609.30634; embedding "halving
the decay rate of a frozen recurrent language model as an intervention to test
whether recall loss on longer token sequences is caused by forgetting rather
than interference" returned 2609.30634, 2609.04434, 2608.18578 (screened, no
overlap); keyword "semantic clock gate parity" returned nothing relevant;
OpenAlex "experimental designs for identifying causal mechanisms mediator
manipulation" returned Imai et al. first.

Not done: the blind closest-prior critic (packets in `blind/`), the novelty
refuter, a full OpenReview sweep of ICLR 2027 submissions, and a search for
"activation patching of gate or decay parameters" as such (synthesis had no
counted queries left above the triad's reserve; see Iteration Log).

## Mechanism and Falsifiable Predictions

The two transitions follow Gated DeltaNet
([2412.06464](https://arxiv.org/abs/2412.06464)) and RWKV-7
([2503.14456](https://arxiv.org/abs/2503.14456)) as implemented in fla 0.5.2
(asset cell's read of the layer sources, re-read by synthesis).

```text
GDN (subject G):   S_t = a_t S_{t-1} (I - b_t k_t k_t^T) + b_t v_t k_t^T
                   g_t = log a_t = -exp(A_log) * softplus(a_proj(x_t) + dt_bias)    per head
RWKV-7 (subject R): S_t = S_{t-1} (diag(exp w_t) - kk_t^T (a_t * kk_t)) + v_t^T k~_t
                   w_t = -0.6065 * sigmoid(w_lora(x_t))                              per channel

Re-segmentation R(f): canonical passage tokens u_1..u_N -> pieces, round(fN) in total,
                      same bytes; facts, query and codes canonical.

Decay mass of token u at layer l, head (or channel) h:
  canonical run:      G_c(u) = g at u's position                     (CAN pass, same episode)
  re-segmented run:   G_r(u) = sum of g over u's pieces              (live, after lower-layer clamps)
  clamp:              g'_piece = g_piece * G_c(u) / G_r(u)          so sum over pieces = G_c(u)
  ledger:             R_F(u) = G_r(u) / G_c(u)

Episode outcome Y in {0, 100} (forced choice among 4 codes):
  TE(f)  = Y(CAN) - Y(NAT f)               total re-segmentation cost
  NIE(f) = Y(CLAMP f) - Y(NAT f)           carried by extra decay mass (natural indirect effect)
  NDE(f) = Y(CAN) - Y(CLAMP f)             carried by everything else (writes, erase, conv or
                                           token shift, unfamiliar segmentation)
  TE = NIE + NDE exactly, per episode.
  beta_s = mean_{K in {1,4}} NIE_s(K, f_p) / ln f_p      line 3 points per log-f unit
```

Why this identifies the decay share where r = 2 does not. Holding each
token's decay mass at its canonical value leaves every other consequence of
re-segmentation in place: the extra pieces still write and erase, the
convolution or token shift still sees shorter spans, the segmentation is
still unfamiliar. The contrast is therefore the effect of the extra decay mass
alone, evaluated at the extra writes the re-segmentation actually produced.
The uniform halving instead changes every decay in the episode, including
the canonical tokens and the facts, and so changes how long every
interfering write survives; its contrast mixes target retention with
crosstalk retention. S1 shows the difference on a gated delta-rule memory:

| S1 world (lambda, rho, write norm) | Decay share (clamp) | Registered reading (3 seeds) | dG from r = 2 at f = 2.7, K = 4 |
|---|---|---|---|
| W1 per-token clock (0, 1, yes) | 1.00 | MATERIAL x3 | +17.5 to +22.5 |
| W2 pure interference (1, 0, no) | 0.00 | KILL x3 | -1.2 to -3.3 |
| W3 clock and interference (0, 0, no) | 0.22 to 0.25 | MATERIAL x3 | -1.5 to -2.2 |
| W4 null (1, 1, yes) | undefined (TE = 0) | NO_COST x3 | 0.0 |
| W5 legacy duplicates (0, 1, no) | 0.41 to 0.44 | MATERIAL x3 | +2.8 to +6.5 |
| W6 partial (0.5, 0.5, no) | 0.15 to 0.17 | MATERIAL x3 | -0.7 to +0.8 |

lambda sets how piece decay scales (0: each piece decays like a whole token;
1: pieces share the token's decay); rho sets how similar piece writes are to
the parent token's write. Effect sizes in S1 are not calibrated to the
checkpoints; only the zeros and signs are evidence.

What the clamp does not identify. It is a mediator intervention on a
pathway, so "decay share" means the effect of the extra decay mass given the
writes that actually occur; if decay and writes interact, NIE and NDE are not
separately additive in a deeper sense, only in the exact per-episode identity
above. RWKV-7's decay is coupled to its in-context removal term, so the
"decay pathway" is a different object on the two subjects (the SPLIT reading
exists for this). The clamp does not touch the short convolution, whose
receptive field in canonical tokens shrinks under re-segmentation; that cost
is in NDE by design.

**Predictions and falsifiers** (each pre-registered in the draft registration):

- **P2, primary (kill criterion).** The upper end of the 90% interval of
  beta_s is below 3 on both subjects (KILL). Falsified by MATERIAL on either
  subject (beta at least 3 with lower end above 0). The dossier's kill line
  is kept in its unit; what changed is the statistic that is compared to it.
- **P1, ledger.** The median R_F over split tokens at f = 2.7 is above 1.5 on
  both subjects (gates do not self-normalise to canonical tokens). Falsified
  by a median at or below 1.5; a median in [0.85, 1.15] means the clamp is
  near the identity and NIE near 0 by construction, a cheap mechanism result
  on its own (Tallec and Ollivier's quasi-invariance realised by pretraining).
- **P3.** TE is at least 10 points per log-f unit on both subjects.
  Falsified by a smaller TE; NO_COST is the extreme case.
- **P4.** Re-segmentation costs more than the same number of extra canonical
  tokens: Y(CAN) - Y(FILL 2.7) is smaller than TE(2.7). Falsified by the
  reverse on either subject.
- **P5.** The r = 2 contrast and NIE at f = 2.7 differ by more than their
  combined intervals on at least one subject (S1's warning reproduced on real
  checkpoints). Falsified by agreement on both.

Reject the step as uninformative before reading P2 if an instrument gate
fails (registration I1 to I7) or no fertility clears the floor.

## Cheapest Decisive Pilot

The step is itself the cheapest decisive experiment: one GPU per subject,
forward passes only, no training. Registered caps: smoke 0.25 GPU-h, subject G
1.25, subject R 2.5, total 4.0 under D22. Central estimate 1.26 GPU-h, high
3.29 (S3, on assumed throughputs). Primary cells are 2.58e7 of the 3.48e7
tokens per subject.

The decisive cell is CLAMP(2.7) against NAT(2.7) at K in {1, 4}, 1,500
episodes per load, paired by episode. A cheaper pre-pilot exists inside the
smoke and is registered as a reported quantity, not a decision: the R_F ledger
on 200 episodes. If R_F is within [0.85, 1.15] on a subject, the clamp is
near the identity there and NIE is near 0 by construction.

No executable pilot exists today. The S1 to S4 scripts are CPU design
evidence, not a pilot, and none is an orx node.

## Controls, Baselines, and Ablations

- **Identity.** At f = 1 the clamp is the identity; gate I1 compares hooked
  and unhooked runs before any analysis.
- **Two implementations of r = 2 (subject G).** Weight edit A_log - ln 2
  against the a_proj hook with c = 0.5 (gate I2): checks that the hook acts on
  the decay the kernel uses. Subject R: chunk kernel against a pure-torch
  recurrence on captured inputs (gate I2b).
- **Uniform halving r = 2.** The dossier's intervention, at f = 1 and 2.7,
  reported beside NIE.
- **Elapsed-context ladder (FILL).** Lee et al.'s arm on both subjects,
  matched in token count to each f; the content-adding counterpart of
  re-segmentation.
- **Boundary only (BND).** Non-canonical boundaries at unchanged token count;
  a descriptive estimate of the boundary step (weak: 8-12% of tokens).
- **No passage (ZERO).** Encoding and fact-competition baseline per load.
- **Write silencing (SIL, SIL-CLAMP).** Decay-only passage: the upper
  reference for what decay alone can cost over the passage at f = 2.7.
- **Encoding channel (FACT, BOTH).** Facts re-segmented (codes never) at
  f = 2.0, alone and with the passage.
- **Mechanism ledgers.** R_F, write-overlap mass, BPB per f.
- **Mandatory 2026 baselines** (gauntlet rule, believability bar item 10)
  apply to architecture claims; this step makes none. SWA plus sinks, tail
  replay, QED and MARCH are not run; MARCH (2608.12435) was found by the
  cross-domain cell and not opened, QED was not found by keyword.

## Evaluation, Statistics, and Leakage Checks

- **Unit and clustering.** The episode is the unit; the retention passage is
  the cluster (4 episodes per passage per load, 375 passages). Intervals are
  90% percentile cluster bootstraps over passages, B = 2,000, seed 42
  (`estimator.cluster_bootstrap_mean`).
- **Power (S2).** At 1,500 episodes per load with a between-passage SD of the
  shift of 2 points: P(KILL | beta = 0) = 1.00, 1.00, 0.98, 0.91 at
  discordance 0.05, 0.10, 0.20, 0.30; P(KILL | beta = 3) = 0.05 to 0.11;
  P(MATERIAL | beta = 5) = 0.98 to 1.00; at 600 per load, P(KILL | beta = 0,
  d = 0.30) is 0.59. The normal-approximation interval used for speed covers
  at 0.86 to 0.92 and the registered bootstrap at 0.85 to 0.93 (nominal 0.90,
  400 replicates per setting), with 99 to 100% agreement of kill decisions.
  The NO_COST rule has P = 0.99 at TE = 0 (d = 0.1) and 0.05 at TE = 3. S1's
  simulated clamp discordance was 0.06 to 0.41 in the worlds with a decay
  share; S2's assumed
  range is 0.05 to 0.30, and a real discordance above 0.30 widens the
  INCONCLUSIVE band.
- **Floors.** Canonical K = 4 accuracy at least 50; the primary f is the
  largest of 2.7, 2.0, 1.5 with native K = 4 accuracy at least 30;
  misclassification under 0.05 at 3 points from a floor (n = 1,000, design
  effect 1.3).
- **Scales.** Primary on forced-choice points; the same contrasts on the
  target log-probability and greedy exact-match scales are reported; only the
  primary is read.
- **Multiplicity.** One primary estimand per subject and a fixed conjunction.
- **Missing data.** Lost episodes are rerun; if not possible they are dropped
  from every cell, and more than 2% dropped caps a subject at INCONCLUSIVE.
- **Leakage.** The answer is a random 4-digit code bound in context, so no
  pretraining knowledge can supply it; candidates are always in-episode codes
  (K at least 4) or fresh codes (K = 1); key strings never occur in any
  passage; passages are cluster-disjoint across seeds. WikiText may be in
  subject R's pretraining data (subject G's FineWeb-Edu could overlap too);
  memorised passage text changes how the passage writes, equally in every arm
  of an episode, and is disclosed. A shortcut risk remains: canonical facts
  among fragmented passage text may cue what to store, more so at higher f;
  the BND and ZERO cells bound it, and it is disclosed. Re-segmentation also
  lowers information per token, and lexical density limits effective context
  in transformers ([2606.06203](https://arxiv.org/abs/2606.06203), kill-shot
  cell, full text), so a density effect may push against a decay penalty; it
  sits in NDE, not NIE, because the clamp holds decay per canonical token.
- **Red flags guarded.** No outcome-dependent exclusion; the estimator is
  code (`compute/estimator.py`) before data; f_p fallback is mechanical.

## Compute and Reproducibility

Image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(build 855 from commit ed5d5a93, image ID
`sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b`;
fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0). Neither checkpoint
has ever been loaded in this image on this host; the smoke does it first.

Launch path (dry run, then test-only, then submit; one GPU per job; none of
these manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v1-smoke.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v1-smoke.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v1-smoke.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the same three steps follow for the two main manifests. Subject G's weights
(5,865,376,000 B of fp32 safetensors) are fetched by
`sbatch infra/slurm/host-single-node/fetch-model-cpu.sbatch` after a registry
entry and Kevin's data-rights ruling, when no S1a job is running. Every
executable pilot also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for the new CPU doctor,
`kind: slurm-manifest` for the GPU jobs).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 4 (registered caps: smoke
0.25, subject G 1.25, subject R 2.5; sum 4.0, at most 8.0 under D22; this is
the step's compute, separate from the gauntlet's 0.3 GPU-h reviewer budget).

Estimate (S3, `compute/cost-model.json`): 3.48e7 tokens per subject. Central
(GDN 40,000 tok/s, RWKV-7 20,000 tok/s, hook overhead 1.2, resume 1.1, fixed
0.15 h per job): 0.47 + 0.79 = 1.26 GPU-h. High (20,000 and 8,000 tok/s, hook
overhead 1.5, fixed 0.25 h): 1.05 + 2.24 = 3.29 GPU-h. The only throughput
anchor on this host is training (73,045 tok/s/GPU for a 422M GDN hybrid, image
0b3ecef0-architecture; about 63,000 tok/s implied for a 1.47B forward pass at
the same achieved FLOP rate); forward inference has never been measured here.
In the first 10 minutes each main job projects its time; ladder tiers are
dropped in a fixed order to fit the cap; if the primary cells alone exceed it
(below about 11,800 tok/s for G or 5,200 for R) the subject is INFEASIBLE, not
cut.

Checkpoints and resume: completed (episode, cell) records every 5 minutes to
the persistent run directory; a fresh job skips completed keys; the smoke runs
a kill-and-resume test requiring identical decisions and log-probabilities
within 1e-4 for every completed key. Artifacts: per-episode records for every
cell (decisions, the four string log-probabilities, greedy strings, ledger
summaries), per-layer ledgers, the decision record. Passage text stays on the
host or in the private archive; the public repository receives ids, hashes and
metrics.

## Safety, Data Rights, and Monitorability

- **Subject R.** apache-2.0 (card; the RWKV-7 paper,
  [2503.14456](https://arxiv.org/abs/2503.14456), states Apache-2.0 for code
  and models); registered with a receipt on the host; frozen, not
  redistributed. Its tokenizer's upstream loader calls `eval()` on each vocab
  line; the harness vendors it with `ast.literal_eval` and pins the vocab
  SHA-256 (S4 reproduces the pinned digest).
- **Subject G.** No licence, card or README at 930ed6ae; training data
  documented first-party in 2507.06457. Its use is a ruling for Kevin
  (registration decision 1). Under either option no weights or derived
  weights are redistributed, and the public repository holds aggregate
  metrics, ids and hashes only. The apache-2.0 fallback is registered.
- **Data.** WikiText-103 (CC BY-SA 3.0 and GFDL) passages stay off the public
  repository; key lists and templates are written by the project.
- **Untrusted code.** None executes. Model outputs are strings scored on CPU.
  Subject R's modeling code is a re-export of fla (asset cell); it loads with
  `import fla` and trust_remote_code false.
- **Host.** No host job of any kind while an S1a VM or GPU job runs; this
  synthesis made one read-only squeue (empty at 21:41 UTC) and no job.
- **Public repository.** No host addresses beyond the documented local
  registry name, no credentials, no passage text.
- **Monitorability.** Nothing is trained or deployed; all interventions are
  inference-time hooks recorded with their parameters.
- **Red lines.** None touched. Safety verdict PASS, conditional on decision 1
  being made before subject G is fetched.

## Negative-Result Value

- **KILL** is the expected result and the useful one: it closes D20's phase-1
  loss without translation work and extends Lee et al.'s English finding to a
  same-content fertility axis and to RWKV-7, with a decay share bounded from
  above by an intervention rather than inferred from a distance curve.
- **NO_COST** says re-segmented English costs these models little recall,
  itself a finding about attention-free robustness to non-canonical
  segmentation, the opposite of the transformer base-model result.
- **P1 falsified with R_F near 1** shows pretrained gates realise
  Tallec-Ollivier time-warp invariance on fragments they never saw.
- **SPLIT** is a GDN-versus-RWKV-7 decay-object difference.
- **P5 confirmed** shows on real checkpoints that the uniform decay rescale
  used across the length-extension literature misreads the decay share.
- **INVALID or INFEASIBLE** still delivers the first inference throughput and
  loader checks for both subjects on this host.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 120 counted discover queries with returned ids and raw-output SHA-256 (one raw output not saved, one 429 failure), uncounted OpenReview, web and Anthology searches logged; cutoff 2026-10-10; degraded coverage recorded (`doctors/source.json`) | Semantic Scholar forward citations for 2609.33093 and 2609.16183 through the host relay |
| Citation | PASS | Claim registry C01 to C42 with locators, dates and read status; every primary URL snapshotted with HTTP 200 and its version history; first-party labels; six dossier corrections and one cell correction (`doctors/citation.json`) | Open the psychology sources cited from metadata only before any write-up |
| Novelty | FAIL | No direct prior under the recorded coverage, but the blind critic and the novelty refuter have not run, and synthesis could not search "activation patching of decay parameters" without breaching the triad's reserve (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter with that query |
| Design | FAIL | Intervention, controls, falsifiers, metrics, leakage and decision rules are specified, coded (`compute/estimator.py`) and simulated (S1, S2), and the splitting rule is measured on the real tokenizers (S4); but discordance is assumed, no harness exists, and the clamp has never run on a checkpoint (`doctors/design.json`) | Build the harness and the new CPU doctor; run the smoke |
| Compute | FAIL | No real model loop, adapter, manifest, container smoke or Slurm dry run; subject G not on the host; inference throughput never measured here (`doctors/compute.json`, `compute/attestations-not-run.md`) | Kevin's ruling, registry entry and fetch; harness; smoke dry run and test-only |
| Safety | PASS | Subject R apache-2.0; subject G gated on Kevin's ruling with a licensed fallback; passages off the public repo; no untrusted code; host rule respected (`doctors/safety.json`) | Decision 1 before any fetch |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts; paywalled psychology sources marked
metadata-only); Design, the vendored K-Dense `experimental-design` and
`statistical-power` skills (design before data; power by simulation for every
threshold); Evaluation, K-Dense `statistical-analysis` (paired, clustered
intervals); Novelty, K-Dense `literature-review` (approximate PRISMA counts).
The integrity gate (seven failure modes) is answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only while no S1a VM or GPU job is running)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; kills or keeps the phase-1 loss |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01 to C42 |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P1 to P5 with registered falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; clamp, identity, r = 2, FILL, BND, SIL, ZERO |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S2 operating characteristics under assumed discordance |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; caps 4.0 GPU-h, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest, subject G not on host |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; subject G licence gap pending decision 1 |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy D20 waves 1-5 (2026-09-01) | 61, 64, 63 (wave 5 not re-judged) | Hybrid readout, headroom, language identity | Prefix-blind readout, rwkv7 co-primary, synthetic-fertility English | Archived in `legacy/directions/20-semantic-clock-gate-parity.md` |
| dossier (2026-10-06) | not scored | Recurrent state does not carry recall in hybrids; load beats distance | Corrected question: English re-segmentation on attention-free subjects, r = 2 | Recorded in the dossier, section 13 |
| new gauntlet, synthesis (2026-10-10) | not scored | r = 2 cannot identify the decay share; the EM slope is scale-dependent; base models mis-generate on fragments; the fund branch has no subject | Per-token decay clamp as the primary arm; paired simple effect against the dossier's line; canonical facts and codes with forced choice; restated consequences; n from S2; rules measured on real tokenizers (S4) | Awaiting blind critic, refuters and reviewers |

Budget note: the cells used 120 of the 150 declared queries, leaving exactly
the triad's reserve of 30; synthesis used none. Paper reads are not counted.

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e5-gate-fertility-decomposition.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-e5-gate-fertility-decomposition/doctors/research-direction-doctor-output.json`.
Three readings the doctor does not make for itself. "All declared budgets must
be positive" comes from parsing the declared `gpu_hours=0.3` as an integer; the
declared budget is honest and is not rounded up to pass. The doctor applies no
79 cap because its executable-pilot check is textual, while by the gauntlet
rule's cap table this proposal is capped at 79 (no executable pilot) and 89 (no
independent provider-distinct review), and cannot reach 100 without D24's
trust store. Its 38 URLs include five doi.org links and one ICLR proceedings
PDF that it does not treat as primary; those claims are labelled
abstract-only or full-text-by-cell in the claim registry.

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
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-e5/program/proposals/2026-10-10-e5-gate-fertility-decomposition.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 38,
    "recognizedPrimaryUrls": 32
  },
  "status": "FAIL"
}
```
