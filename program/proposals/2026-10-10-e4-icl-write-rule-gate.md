# Research Direction: E4 gate, oracle interface ceiling and key-span sufficiency for a distilled in-context write rule (D19 backfill)

**Status:** draft for gauntlet wave 1 (program decision D58); synthesis by the single owner on 2026-10-10 from four independent discovery cells; the blind closest-prior critic, the refute-first triad and the two provider-distinct reviewers have not run; the registration `program/preregistrations/e4-icl-write-rule-gate-v1.md` is a DRAFT, not frozen or admitted; no executable pilot exists for this gate; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification design and draft registration written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-09
**Coverage limits:** orx 0.2.2 only (alphaXiv keyword and embedding search, OpenAlex; the build reports itself outdated against 0.2.18), arXiv abstract pages and version histories through export.arxiv.org and arxiv.org, the Hugging Face model API, the GitHub API for commit dates, and one first-party blog (PorTAL); 150 counted orx discover queries (144 by the four discovery cells, 6 by synthesis) and 73 paper reads (mostly `orx paper --full` texts; 2 alphaXiv reports and 2 OpenAlex metadata records); not searched: Semantic Scholar and the arXiv API (unreachable from the development Mac; the host relay was not used because the host is reserved for Q2 S1a), OpenReview bodies including ICLR 2027 submissions, ACL Anthology full text (one ACL 2026 abstract read through OpenAlex), patents, X, Reddit, Hacker News, Chinese-language venues; the citation graph is degraded (OpenAlex reports zero citations for every prior, including a 2023 paper); the alphaXiv index lags (newest item seen 2026-10-08); full texts were read by targeted section, not end to end; neuroscience and modeling-practice sources (Wilson and Collins 2019, Nili et al. 2014) were read as abstracts only.
**Budgets:** queries=150; wall_minutes=600; tokens=8000000; dollars=150; waves=3; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e4-icl-write-rule-gate/bundle.json

The novelty verdict field uses the doctor's vocabulary. The merged discovery
verdict is NARROWED (frontier, kill-shot and cross-domain cells; the asset cell
gave no novelty verdict): no direct prior was found for the gate's
measurement, and the later distillation and port stages, which are out of scope
here, are narrowed further by Internalizer and PorTAL (below).

## Scope and what changed from the dossier

This proposal covers only the E4 gate: Step 1 (teacher eligibility) and Step 2
(an oracle interface ceiling). Step 3 (training a free write rule against a
gradient-form rule), the port to recurrent bases, the cross-lingual stage and the
independent-ladder replication are out of scope. Each would need its own
gauntlet. The gate is what the dossier
(`program/evidence/2026-10-06/question-dossier.md`, entry
`E4-d19-icl-rule-distillation-port`) asked to run first, and D58 scopes wave 1
to it.

Four discovery findings change the gate as the dossier wrote it. Each one is
re-checked in this proposal, by a CPU check, a full-text read, or both.

| # | Finding (cell) | Consequence for the gate | Where handled |
|---:|---|---|---|
| 1 | KILL A (kill-shot cell): the legacy interface reuses D16's rank-8 factorised port maps P (64 x d_b, rank 8). Every key and every probe read then lies in one 8-d subspace, and 8 demonstrations span it, so a state restricted to the span of the keys gives the same reads as a free state. The dossier's Step-2 tie rule ("if the free and key-span oracles tie ... stop") fires by construction. Cell receipt: gap 0.0 at seeds 42/43/44 and a read difference of 1.8e-14 at pilot shape | The port map becomes a full-rank 64-d map (rank 64), so 8 keys span 8 of 64 readable dimensions. A pre-registered non-vacuity check on real residuals must pass before the span contrast is read. This breaks the deliberate identity with D16's interface; a result here no longer tests D16's premise directly | S1 (this bundle) replicates KILL A and shows the repair; registration I1 |
| 2 | The gradient-form class w_i = k_i excludes the literature's own GD-like solutions: a preconditioned step whose preconditioner approximates the inverse data covariance ([2306.00297](https://arxiv.org/abs/2306.00297), Sec. 4.1, 2023-06-01) and recursive least squares in the mesa-layer ([2309.05858](https://arxiv.org/abs/2309.05858), Sherman-Morrison derivation, 2023-09-11) (kill-shot and cross-domain cells) | The restricted class is redefined as the span of the demonstration keys after one linear map B shared by all episodes. It contains first-order updates with any fixed preconditioner, recursive least squares, and preconditioned recursive least squares. B = I (the exact dual form of plain first-order updates, [2202.05798](https://arxiv.org/abs/2202.05798), Sec. 2, 2022-02-11) is reported as a secondary | Mechanism; registration Step 2 classes |
| 3 | A free-over-key-span gap can be produced by retrieval among latent tasks a pretrained model already knows, not by a non-gradient learning rule. The legacy doctor's positive control is prior memorisation (wave-5 reviewer: 0.94 falls to -0.72 on a held-out prior) and a learned amortizer on GPT-2 shows zero leave-one-task-out transfer ([2610.00526](https://arxiv.org/abs/2610.00526), Table 2, 2026-09-30) (kill-shot and frontier cells) | A family-constant state absorbs task identity before the span contrast. The gate's positive outcome is renamed OPEN: it says a later rule-versus-rule study has room to separate, and it is pre-registered as uninformative about whether that room comes from retrieval or from a non-gradient rule | Mechanism; Negative-Result Value; registration decision rules |
| 4 | Step 2 as written could not be read as a capacity result: no optimiser-adequacy check, no control for a variance-driven label-free map discarding label-bearing directions, no floor stronger than M = 0, no guard against off-manifold edits (cross-domain cell: [2106.05945](https://arxiv.org/abs/2106.05945), [2110.14633](https://arxiv.org/abs/2110.14633), [2412.11299](https://arxiv.org/abs/2412.11299), [2404.03592](https://arxiv.org/abs/2404.03592)) | Planted-state recovery, a width-256 reference, a conditional supervised-map arm, placebo and family-constant floors, a norm cap at twice the natural in-context residual shift, and context-change principal directions instead of variance principal directions | Controls; registration I2 to I4 |

Two more corrections to the dossier, recorded here because a frozen dossier is
not edited: Jeong's "universal write rule"
([2603.22329](https://arxiv.org/abs/2603.22329), Sec. 8.3, v1 2026-03-20) is an
attention-coupled aggregation with temporal decay and fixed random write
projections, not a Hebbian rule (Hebbian is only its method M.4; frontier cell,
re-checked in the cell's full-text read); and the dossier's requirement of "at
least 4 function-induction families" admits families that pass the
gold-versus-shuffled test through task recognition, because pairs identify a
stored function ([2310.15916](https://arxiv.org/abs/2310.15916), 2023-10-24;
[2310.15213](https://arxiv.org/abs/2310.15213), 2023-10-23). The gate instead
requires at least 4 eligible families whose mapping changes from episode to
episode.

## Claim and Research Question

**Question.** For the frozen fla-hub `transformer-1.3B-100B` teacher
(revision `d6f66f4181fa669e5863327815b44533e3a395e7`, MIT card tag,
[model page](https://huggingface.co/fla-hub/transformer-1.3B-100B)), three
quantities decide whether any later study of a distilled in-context write rule
at a 64-d residual interface can be informative:

1. **Eligibility.** On how many synthetic task families does the teacher show
   label-dependent in-context learning (accuracy with gold demonstrations minus
   accuracy with deranged labels, over three demonstration seeds), and on how
   many of those does the correct mapping change from episode to episode?
2. **Interface ceiling.** Can a per-episode state at the interface (a rank-8
   64 x 65 matrix at each of four residual depths, read affinely from and
   written into a fixed label-free 64-d subspace), fitted directly to the
   teacher's own
   eight-shot predictions, remove at least half of the episode-specific
   divergence that a single family-constant state leaves, on held-out probes?
3. **Key-span sufficiency.** Does restricting the episode-specific part of
   that state to the span of the eight demonstrations' own key representations,
   after one linear map shared by all episodes, lose anything measurable?

The variable is the state class (none, placebo, family constant, key-span
with shared map B, key-span with B = I, free rank 8, free rank 16 at width
256), fitted per episode by the same optimiser to the same targets.

**Claim scope.** `portability-protocol` prerequisite. The gate measures one
frozen teacher. It makes no architecture, portability, learning-rule or
gradient-descent claim. The only claims it can license are of the form "at this
interface, the teacher's episode-specific in-context behaviour on these
families is (not) carried by any state, and is (not) carried by key-span
states".

**Hypothesis under test (H_gate).** At least 8 families are eligible, including
at least 4 episode-specific ones on which a family-constant state leaves at
least 0.20 of the zero-shot divergence; the free state carries at least half of the
episode-specific divergence; and the key-span class falls short of the free
class by at least 0.10 of that divergence on at least half of the
interface-capable episode-specific families. H_gate is what a later
rule-versus-rule study needs. Each clause has a pre-registered failure.

## Strategic Fit and Why Now

E4 is item 3 of the backfill queue (`program/backlog.md`). D58 chose it
because its prerequisites are CPU work and the host is reserved for Q2 S1a. The
gate's GPU work is small (sum of registered caps 6.42 GPU-h, central estimate
about 1 GPU-h; `compute/cost-model.json`) and runs only after S1a's session 2,
a scored and reviewed package, and a freeze.

The gate's value does not depend on the later stages surviving. Each of its
stopping outcomes is informative on its own:

- **STOP_TEACHER** says label-dependent, episode-specific in-context learning at
  1.3B/100B tokens is confined to few families. That is a measured floor for
  every 1.3B write-rule and fast-weight study in the program, including D16.
- **STOP_TR** says that on the families where the correct mapping changes
  between episodes, one state per family already reproduces the teacher's
  eight-shot behaviour at this interface: task recognition, with nothing
  episode-specific for a write rule to carry.
- **STOP_INTERFACE** (or its size and label-free-map variants) says the 64-d,
  rank-8, four-site interface cannot carry the teacher's episode-specific
  behaviour, whatever rule writes it. That closes D19 and constrains D16 for a
  few GPU-hours, before any rule is trained.
- **STOP_SPAN** says every episode-specific behaviour the interface can carry is
  expressible by key-span writes. Then no rule-versus-gradient-form contrast can
  separate at this interface, and Step 3 is closed without being run.

The legacy D19 direction ran five gauntlet waves (62, 57, 65, 65 by the lower
reviewer; `legacy/directions/19-icl-rule-distillation-port.md`) and exited at
"under two points of gain across three waves". Both wave-5 reviewers named
identification defects that the gate now removes rather than repairs (KILL A,
the clamp co-condition passing under the null, prior memorisation). The
competing frontier is moving fast: four of the priors closest to E4 appeared
since August 2026 (One Adapter Pair 2026-08-10, When Is a Task Vector Enough?
2026-08-13, Task Operators 2026-10-01, Internalizer 2026-10-08).

## Primary-Source Evidence

Every row was opened by a discovery cell or by synthesis. "Full" means `orx
paper --full` text read by targeted section; "abstract" means the abstract page
only. First-party marks a number not independently replicated. Claim ids C01 to
C30 are the Citation doctor's registry (`doctors/citation.json`).

| id | Claim used here | Source | Date | Read | Status |
|---|---|---|---|---|---|
| C01 | Each head's ICL output is an affine transform of its context-masked counterpart, replayed training-free as a per-input W_O update; evaluated on Qwen3-4B/8B and Llama-3.2-3B/3.1-8B instruct, K = 8, 8 tasks; unstable at large K | [2610.01054](https://arxiv.org/abs/2610.01054) Sec. 3 Eq. 3, Sec. 4.1, App. A | 2026-10-01 (v1) | full (frontier, kill-shot, synthesis) | verified |
| C02 | Implicit multimodal ICL: nested static, query-conditioned, multi-site and routing interventions, matched in rank and injected norm, scored by recovery of the explicit-ICL gain on held-out queries; static recovery tracks the share of the demonstration-induced change common to all queries; 16 shots; OpenFlamingo-v2-9B, Idefics2-8B, LLaVA-NeXT-7B | [2608.13385](https://arxiv.org/abs/2608.13385) Sec. 2 Eqs. 1-6, Sec. 4.3, Sec. 5.1, Table 3 | 2026-08-13 (v1) | full (synthesis) | verified; single author, first-party numbers |
| C03 | Context distilled into fast weights (MLP down-projection) with a fixed gradient-form update, same model as teacher and student; nothing learned about the rule, nothing ported | [2608.01672](https://arxiv.org/abs/2608.01672) Sec. 3, Proposition 1 | 2026-08-03 (v1) | full | verified |
| C04 | A 2.6M-parameter network reads support-set geometry and writes an input-conditioned mid-depth residual update into frozen GPT-2-large/XL; leave-one-task-out transfer 0.00 to 0.03; wrong-task manifolds collapse accuracy to 0.06 or below | [2610.00526](https://arxiv.org/abs/2610.00526) Sec. 2, Tables 1-2 | 2026-09-30 (v1) | full | verified; single-author workshop paper, first-party |
| C05 | Label-free per-model linear adapter pairs into a shared 3072-d space; round-trip self-FVE 0.591 to 0.980; five softmax transformers, no recurrent model | [2608.09521](https://arxiv.org/abs/2608.09521) Sec. 4, App. E.1-E.2 | 2026-08-10 (v1) | full | verified |
| C06 | Shared model-agnostic context-to-LoRA trunk with thin per-base entry and exit layers, warm-started on five 1-3B bases and ported to a frozen 284B model; frozen trunk with cold-started maps above 90% top-1 in the 64-token setting | [2610.11715](https://arxiv.org/abs/2610.11715) Sec. 3.7, 4.5-4.6, 6.3 | 2026-10-08 (v1) | full (frontier, synthesis) | verified; first-party |
| C07 | PorTAL: frozen task latent and decoder core learned on Qwen3-1.7B and 4B, refitting a thin per-base alignment recovers about 98% of LoRA's lift on Qwen3-8B and about 94% on Gemma-3-4B | [PorTAL blog](https://labs.ramp.com/research/portal-portable-task-adaptation/) headline results | 2026-07-01 | opened by synthesis 2026-10-10 | first-party blog, not peer reviewed |
| C08 | Jeong's shared write rule is a fixed attention-coupled aggregation with decay and random write projections; GPT-2 only, one benchmark, one seed | [2603.22329](https://arxiv.org/abs/2603.22329) Sec. 4.1, 8.3, 8.4 | 2026-03-20 (v1) | full | verified; corrects the dossier |
| C09 | Task learning (abstract labels) is acquired with scale; small models (GPT-3 babbage 1.3B, OPT-350M/2.7B) are flat with the number of demonstrations | [2305.09731](https://arxiv.org/abs/2305.09731) Sec. 4.1 | 2023-05-16 (v1 only) | full | verified |
| C10 | ICL and GD differ in order sensitivity and output-distribution shift in LLaMa-7B and GPT-J; the equivalence remains "an open hypothesis" | [2310.08540](https://arxiv.org/abs/2310.08540) abstract, Sec. 4-5 | 2023-10-12 (v1) to 2024-06-03 (v5) | full | verified |
| C11 | A single linear self-attention layer's global optimum implements one step of preconditioned GD; for large n the preconditioner approximates the inverse data covariance | [2306.00297](https://arxiv.org/abs/2306.00297) Sec. 4.1 | 2023-06-01 | full (kill-shot, synthesis) | verified |
| C12 | The mesa-layer solves in-context least squares; Sherman-Morrison gives recursive least squares | [2309.05858](https://arxiv.org/abs/2309.05858) mesa-layer section | 2023-09-11 | full | verified |
| C13 | A linear layer trained by GD equals its initial weights plus a sum of outer products of errors with inputs (dual form) | [2202.05798](https://arxiv.org/abs/2202.05798) Sec. 2 | 2022-02-11 | full | verified |
| C14 | Kalman-gain associative memory treats a covariance-weighted write direction as part of the delta-rule family | [2609.07816](https://arxiv.org/abs/2609.07816) abstract | 2026-09-07 | abstract (kill-shot) | abstract only |
| C15 | Flipped-label override rate is zero across eight open 1-12B models | [2511.21038](https://arxiv.org/abs/2511.21038) abstract, Table 1 | 2025-11-26 | full (kill-shot) | verified |
| C16 | Function-induction ICL is strong at small scale and mostly removed by shuffled labels | [2310.15916](https://arxiv.org/abs/2310.15916) results table; [2310.15213](https://arxiv.org/abs/2310.15213) Table 2 | 2023-10-24; 2023-10-23 | full (kill-shot) | verified |
| C17 | At fixed stitching rank, task-loss maps beat variance-based (SVD) maps; principal-component magnitude does not track information | [2110.14633](https://arxiv.org/abs/2110.14633) Sec. 7 | 2021-10-27 | full (cross-domain) | verified |
| C18 | Transformer residual streams are dominated by one principal direction; ZCA whitening before alignment | [2609.08692](https://arxiv.org/abs/2609.08692) Fig. 3, Sec. 5.1 | 2026-09-08 | full (cross-domain) | verified; first-party |
| C19 | Task-loss stitching layers produce out-of-distribution representations | [2412.11299](https://arxiv.org/abs/2412.11299) Sec. 4 | 2024-12-15 | full (cross-domain) | verified |
| C20 | A stitching result must show the stitcher is not doing the work | [2106.07682](https://arxiv.org/abs/2106.07682) Sec. 3 | 2021-06-14 | full (cross-domain) | verified |
| C21 | Students can fail to match a teacher they have the capacity to match; optimisation is the main cause | [2106.05945](https://arxiv.org/abs/2106.05945) Sec. 6 | 2021-06-10 | full (cross-domain) | verified |
| C22 | Low-rank interventions on a frozen model's hidden representations, rank 1 to 64 swept | [2404.03592](https://arxiv.org/abs/2404.03592) Sec. 3.2 | 2024-04-04 | full (cross-domain) | verified |
| C23 | Linearising attention costs few-shot ability first: Llama 3 8B 5-shot MMLU 66.6 to 52.8 under LoLCATs | [2410.10254](https://arxiv.org/abs/2410.10254) main LM-Eval table | 2024-10-14 | full (cross-domain) | verified |
| C24 | Error consistency (chance-corrected agreement) between decision makers | [2006.16736](https://arxiv.org/abs/2006.16736) Sec. 2.2 | 2020-06-30 | full (cross-domain) | verified |
| C25 | Learning rules can be recovered from behaviour with ground-truth recovery simulations first | [2509.04661](https://arxiv.org/abs/2509.04661) Sec. 3 | 2025-09-04 | full (cross-domain) | verified |
| C26 | Finite task diversity gives Bayes-optimal retrieval (dMMSE); high diversity gives ridge regression | [2306.15063](https://arxiv.org/abs/2306.15063) abstract | 2023-06-26 | report (kill-shot) | abstract-level |
| C27 | Steering outside a feature's natural range need not reflect the model's computation; tests should use values observed on natural inputs | [2610.07270](https://arxiv.org/abs/2610.07270) abstract | 2026-10-05 | abstract (synthesis query) | abstract only |
| C28 | Shuffled labels in demonstrations; contextual calibration with content-free inputs | [2202.12837](https://arxiv.org/abs/2202.12837); [2102.09690](https://arxiv.org/abs/2102.09690) | 2022-02-25; 2021-02-19 | metadata (asset cell, OpenAlex) | method citations only |
| C29 | fla-hub 1.3B/100B checkpoints: transformer and GLA receipts exist on the host; 2.7B registered without receipt; fla 0.5.2's Attention raises ImportError without flash_attn, which no image contains | [transformer-1.3B-100B](https://huggingface.co/fla-hub/transformer-1.3B-100B), [transformer-2.7B-100B](https://huggingface.co/fla-hub/transformer-2.7B-100B) (HF API, 2026-10-10); fla 0.5.2 `fla/layers/attn.py` in the host uv cache | 2026-10-10 | asset cell (read-only ssh before 11:30 UTC; uv.lock and Dockerfile) | verified by reading, not by running a container |
| C30 | FineWeb-Edu is ODC-By | [dataset page](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) | 2026-10-10 | asset cell | verified (card) |

## Closest Prior Work

Ranked by how close the mechanism is to the gate's measurement, not to the
legacy direction's later stages.

1. **When Is a Task Vector Enough? An Empirical Theory of Implicit Multimodal
   ICL** ([2608.13385](https://arxiv.org/abs/2608.13385), Li, v1 2026-08-13;
   full text read by synthesis). The closest measurement prior. It fits a nested
   family of interventions that replace demonstrations (static shift, oracle
   and predicted query-conditioned shifts, multi-site, attention routing),
   matched in rank and injected norm, scores each by recovery of the explicit
   gain on held-out queries, and predicts the cheapest sufficient family from
   properties of the demonstration-induced change. Same: oracle-level nested
   interventions, held-out queries, matched counterfactuals with deranged
   labels. Different: its axes are query-selection and realization site within
   one demonstration set; it never restricts an intervention to the span of the
   demonstrations' own representations, never compares a per-episode state with
   one shared by all episodes of a task family, and never asks what a write rule
   could express. It is multimodal (VLMs, 16 shots).
2. **Capturing In-Context Learning Dynamics with Task Operators**
   ([2610.01054](https://arxiv.org/abs/2610.01054), Xiong et al., v1
   2026-10-01). An exact per-head affine identity for ICL inside softmax
   attention, replayed as a per-input W_O update. Same: replaces demonstrations
   inside a frozen model, per input. Different: exact and within-model; no fixed
   external interface, no state classes, no gradient-form boundary, 3-8B
   instruction-tuned models only. The kill-shot cell adds that its per-prompt
   parameters are stable within a task (80.7% of sites with a coefficient of variation of w below 0.1), which
   is the family-constant reading the gate measures.
3. **Rules Amortize, Pairings Don't** ([2610.00526](https://arxiv.org/abs/2610.00526),
   Jhingran, v1 2026-09-30). A learned amortizer of ICL into an input-conditioned
   mid-depth residual update on frozen GPT-2-large/XL, with wrong-task and
   leave-one-task-out controls. Same: residual-site update reproducing ICL on a
   frozen model, held-out controls. Different: a learned network (closer to the
   out-of-scope Step 3), not an oracle; no key-span class; no family-constant
   floor; leave-one-task-out zero.
4. **Learning What to Remember: TTCD** ([2608.01672](https://arxiv.org/abs/2608.01672),
   v1 2026-08-03). Context distilled into fast weights with a fixed
   gradient-form update in one model. It is the natural gradient-form reference
   for Step 3, and its update lies inside the gate's key-span class.

Adjacent, cited and not closest for the gate: One Adapter Pair (C05) and
Internalizer (C06) and PorTAL (C07) for the later port; Jeong (C08) for the
"universal write rule" framing; SADA (ACL 2026, `10.18653/v1/2026.acl-long.1046`,
OpenAlex abstract) for state-aligned context distillation inside one model;
learned update rules moved across architectures well before D19 (Wichrowska et
al. [1703.04813](https://arxiv.org/abs/1703.04813), 2017-03-14; MNM
[1907.09720](https://arxiv.org/abs/1907.09720), 2019-07-23; VSML
[2012.14905](https://arxiv.org/abs/2012.14905), 2020-12-29), so no later stage
may claim "the first transferable write rule".

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Per-episode oracle states fitted to a frozen LM's own few-shot predictions and scored on held-out probes | 2608.13385 (oracle conditional coefficients; recovery on held-out queries) | Oracle-level replacement of demonstrations, held-out evaluation | States live in a fixed label-free 64-d subspace at four depths and are fitted by KL to the teacher's distribution, not by reconstructing activations; text LM | medium |
| Family-constant state as the task-recognition ceiling | 2608.13385 (static shift shared across queries); 2610.01054 (stable per-task parameters) | A shared intervention as the floor | Shared across all episodes of a task family, not across queries of one demonstration set, so it measures episode-specificity, the quantity a write rule must carry | medium |
| Key-span class with a shared linear map B, as the boundary of first-order, preconditioned and recursive-least-squares writes | 2202.05798 (dual form), 2306.00297, 2309.05858 (theory); no empirical prior found | The algebra of gradient-form writes | Used as an empirical oracle class on a pretrained LM's behaviour, with B fitted on other episodes; no prior compares key-span and unconstrained states on a pretrained model's in-context behaviour | medium-high |
| Planted-state recovery and span discrimination on real residuals before any reading | 2509.04661 (ground-truth rule recovery in behavioural modelling); 2106.05945 (optimisation, not capacity) | Recovery simulations before interpretation | Applied to oracle state classes at an LM interface; planted states of known class pass through the same read path | medium |
| Non-vacuity check of the span constraint | none found; KILL A shows the need | n/a | A registered instrument gate | high (that it is needed); low weight as novelty |
| Episode-specific family classes as built-in predictions (lookup families predicted span-sufficient, latent-parameter families predicted not) | 2306.15063 (dMMSE vs ridge, synthetic); 2608.13385 (controlled conditionality alpha) | Controlled task structure to calibrate the instrument | On a pretrained text LM with synthetic families generated in the repository | medium |

Novelty wording: No direct prior art found through 2026-10-09 under the
recorded coverage (150 orx discover queries listed in `query-log.json`: the
frontier cell's 61, the kill-shot cell's 30, the cross-domain cell's 43, the
asset cell's 10, and synthesis queries SQ1 to SQ6; 73 paper reads; the
gaps in the Coverage limits line above) for an oracle comparison of
key-span-constrained against unconstrained per-episode states, with a
family-constant floor, at a fixed residual interface of a frozen pretrained
language model, fitted to the model's own few-shot predictions. The six
synthesis queries targeting this mechanism are: SQ1 keyword "optimized
activation intervention reproduces in-context learning predictions upper
bound"; SQ2 embedding (per-demonstration-set low-rank residual intervention
compared with one constant intervention per task and with interventions
restricted to the span of the demonstrations' representations,
`--published-after 2025-06-01`); SQ3 keyword "span of demonstration
representations in-context learning low-rank update subspace task vector";
SQ4 openalex "in-context learning task recognition versus task learning
low-rank activation steering capacity"; SQ5 keyword "key span oracle
in-context learning gradient descent fast weight state"; SQ6 embedding (the
mechanism paragraph in plain words, `--published-after 2026-06-01`). They
returned 2608.13385, 2610.01054, 2610.00526, 2609.40063 (LARC, a gradient-form
fast state learning from feedback in a frozen 1B model, not an oracle and no
span class), 2610.07572 (STAVE), 2610.07270 and others, none of which runs the
comparison. PRISMA-style counts for synthesis: 6 queries, 90 ids identified,
84 unique titles screened, 9 abstracts read, 10 full texts read (8 by this
owner, 2 by an earlier synthesis owner that stalled before committing), 0
included as direct prior. The cells' counts are in `query-log.json`.

## Mechanism and Falsifiable Predictions

**Setting.** Frozen teacher T = `transformer-1.3B-100B` (24 layers, width 2048,
32 heads, vocabulary 32k, context 2048; asset cell from the HF config). An
episode is 8 demonstrations (x_i, y_i) of one task family followed by probe
queries (16 in Step 1; 24 in Step 2, of which 16 fit and 8 score); the
teacher's target for probe q is its next-token distribution p_T(. | demos, q)
at the answer position.

**Interface.** Four sites, after decoder blocks 6, 12, 18 and 24 (depth
0.25/0.5/0.75/1.0, as in the legacy design). At each site k a fixed map P_k
(64 x 2048, rank 64) and its write-back Q_k = W_k^-1 V_k, P_k = V_k^T W_k, where
W_k whitens the site's residuals on FineWeb-Edu and V_k holds the top 64
principal directions of the whitened context-induced change Δh = h(full
prefix) - h(last 16 tokens only) on FineWeb-Edu text. No task text enters P or
Q. The read is affine: with x = [P_k h; 1] (65 coordinates) and a state M_k
(64 x 65), the student is the same frozen model reading the zero-shot prompt,
with h replaced by h + Q_k M_k x at every probe position. The constant
coordinate lets a state write a probe-independent shift (a task-vector-like
write); it is also what makes the span class below the exact dual form of
gradient steps on an affine map. Keys are k_i = [P_k h_k(x_i); 1], taken at the
answer position of the demonstration input encoded alone in the probe
template, so a key and a probe read live in the same coordinates.

**State classes (nested), per episode e of family f.**

```text
S0      M = 0                                   (zero-shot floor)
S_plac  norm- and rank-matched random state; and the S_free state of another
        episode of the same family (resample placebo)
S_const M = C_f                                 (rank 8; one state for all episodes of f)
S_spanB M = C_f + U_e (B K_e)^T                 (U_e 64x8 free; B = diag(B_64, 1) shared
                                                 by all episodes, fitted on seed-42 episodes)
S_spanI M = C_f + U_e K_e^T                     (B = I: exact dual form of first-order writes)
S_free  M = C_f + A_e G_e^T                     (A_e 64x8, G_e 65x8 free; rank 8)
S_ref   width-256 interface, C_f rank 16 + free rank-16 episode part (reference)
```

B is fitted on development episodes with a penalty toward I, and per family
the span class uses the fitted B or I, whichever predicts the development
episodes' held-out probes better; S1 shows why: an estimated B can be worse than
I and would then manufacture a gap.

S_spanB contains every rule whose writes are sums of outer products of an error
vector with a demonstration's key after a fixed linear map: plain first-order
updates (B = I), first-order updates with a fixed preconditioner (any B), and
recursive least squares with or without a fixed preconditioner (its write
direction (B K K^T B^T + λ I)^-1 B k_i stays in span(B K)). S_free is the
ceiling for any rank-8 per-episode write at this interface.

**Fitting.** Each class is fitted by Adam on the KL divergence from the teacher
to the student over 16 fitting probes, 200 steps, learning rate chosen per
class from {1e-2, 3e-2, 1e-1} on development episodes, initialised from C_f,
with the injected norm |Q M x| capped at twice the median natural in-context
shift |h_8shot - h_0shot| at that site. Scores use the other 8 probes only.
Sixteen fitting probes, not eight, because a per-episode state is identified
only on the read directions its fitting probes visit. The span classes are
parametrised in an orthonormal basis of span(B K_e), so their conditioning does
not depend on how similar the demonstrations' keys are; S_free starts LoRA-style
(A = 0, G random), with no knowledge of the keys. Because scoring is on
held-out probes, the key-span class can beat the free class (the keys are a
prior the free class lacks), so D_span can be negative and counts toward a tie;
the converse error, an out-of-span behaviour that 16 probes cannot identify, is
what the planted-state gate P5 guards against. For the lookup families the 24 probes are the 8 bound names
under three query templates (fit on two, score on the third).

**Quantities.** With KL_X the summed KL on held-out probes of a family's 32
evaluation episodes: R_X = 1 - KL_X / KL_S0 (recovered fraction) and, for the
episode-specific part, E_X = 1 - KL_X / KL_const. The shortfall of the span
class is D_span = E_free - E_spanB (paired within episode). E and D_span are
defined only for a family whose constant leaves at least 0.20 of the zero-shot
divergence (KL_const / KL_S0 at least 0.20); a family below that line is
EPISODE_CONSTANT: its in-context behaviour is carried by one state for every
episode, which is task recognition at this interface.

**Falsifiable predictions and the kill criterion for each.**

| id | Prediction | Falsifier (decision rule in the registration) |
|---|---|---|
| P1 | At least 8 of 14 families are eligible (gold-minus-shuffled accuracy gap at least 0.10 with a Holm-corrected one-sided cluster bound above 0, and gold at least 0.05 above zero-shot), at least 4 of them episode-specific | Kill criterion K2 (STOP_TEACHER): fewer than 8 eligible or fewer than 4 eligible episode-specific families |
| P1b | On at least 4 eligible episode-specific families the family constant leaves at least 0.20 of the zero-shot divergence | STOP_TR (task recognition): fewer than 4 such families; the teacher's in-context behaviour at this interface is one state per family |
| P2 | On eligible episode-specific families, E_free has a one-sided 95% lower bound of at least 0.50 in at least 75% of them | Reject if CAP_LOW (upper bound below 0.50) holds in at least half: STOP_INTERFACE_SIZE if the width-256 reference passes, STOP_LABEL_FREE_MAP if the conditional supervised-map arm passes, STOP_INTERFACE_CLASS otherwise |
| P3 | On interface-capable episode-specific families, D_span is at least 0.10 with a one-sided 95% lower bound above 0.02 in at least max(2, half) of them | STOP_SPAN when the one-sided 95% upper bound of D_span is at most 0.05 in at least 75% of them (n at least 3); INCONCLUSIVE_SPAN otherwise |
| P4 | Built-in structure: lookup families are span-sufficient (D_span upper bound at most 0.05); fixed-function families are EPISODE_CONSTANT (KL_const / KL_S0 below 0.20); latent-parameter families carry the gap if any family does | A lookup family with D_span above 0.05 downgrades OPEN to INCONCLUSIVE_SPAN (the span class would be missing template-dependent information) |
| P5 | Instrument validity on real residuals: probe reads keep at least half their energy outside the key span (median over episodes of the non-lookup episode-specific families, every site); planted states are recovered to 0.90 of their KL; planted out-of-span states give D_span at least 0.30 and planted key-span states at most 0.03, each in at least 90% of planted episodes; a planted fixed-preconditioner writer gives D_span at most 0.05 after the B fit (I5) | Any failure of the first three is INSTRUMENT_FAIL (no capacity or span reading; the repair is a new versioned attempt); an I5 failure caps the span verdict at INCONCLUSIVE_SPAN |

**Strongest counter-argument.** A positive P3 (OPEN) is predicted by within-family
task retrieval alone (dMMSE-like behaviour, [2306.15063](https://arxiv.org/abs/2306.15063)):
the 8 demonstrations select one of several stored functions, and applying it to
a new query reads directions orthogonal to the demonstrations' keys. The gate
therefore pre-registers that OPEN does not identify a non-gradient learning
rule. Its only consequence is that a Step-3 study would not be closed by
expressivity, and that study must then separate retrieval from rule structure
with its own design (model-recovery confusion matrix on real residuals, held-out
latent parameters), as the cross-domain cell recommends.

## Cheapest Decisive Pilot

The gate is itself the cheapest decisive experiment the dossier names. Its
cheapest decisive part comes first:

- **Step 0 (CPU, Mac, now; 0 GPU-h):** generators for the 14 families, manifest
  build and hashing; harness for the four-site read path, the state classes,
  the planted-recovery and non-vacuity checks, tested on a tiny random-init
  Llama-shaped model; simulations S1 and S2 (this bundle) re-run under the
  harness.
- **Step 0b (host CPU job, after S1a session 2):** fetch and receipt of
  `transformer-2.7B-100B` (secondary only); tokenizer single-token filter for
  every family's answers.
- **Smoke (GPU, at most 0.17 GPU-h):** load the 1.3B teacher two ways (weights
  remapped to Llama with SDPA, and fla 0.5.2 with a harness-side SDPA shim for
  its flash-attention call), cross-check logits, FineWeb-Edu loss sanity,
  throughput for the oracle step; sets the caps' projection before freeze.
- **Step 1 (GPU, cap 0.75 GPU-h):** eligibility. If STOP_TEACHER, nothing else
  runs.
- **Step 2 (GPU, cap 4.0 GPU-h, plus a conditional 1.5 GPU-h supervised-map
  arm):** P fits, instrument checks, oracle classes, decisions.

The first decisive reading is Step 1, at central estimate 0.10 GPU-h. The
teacher-strength risk that the dossier and the kill-shot cell flag (weak
label-dependent in-context learning at 1.3B, most of all on abstract-label
families; [2305.09731](https://arxiv.org/abs/2305.09731), [2511.21038](https://arxiv.org/abs/2511.21038))
is tested first. The episode-specific families
are synthetic and generated in the repository, so a pass cannot come from
contamination.

## Controls, Baselines, and Ablations

| Control | Kind | What it rules out |
|---|---|---|
| Shuffled labels (seeded derangement of the 8 outputs, same inputs and order) | Step 1, decision-bearing | Format and input-distribution effects counted as in-context learning |
| Zero-shot (template only) and S0 | Step 1 and Step 2 floor | Gains the base model has without demonstrations |
| Placebo states: norm- and rank-matched random state; resample state (another episode's fitted S_free) | Step 2 floors, reported | A state that helps by being a state, not by carrying the episode |
| Family-constant state C_f | Step 2, every class builds on it | Task recognition read as episode-specific writing |
| Key-span constraint, S_spanB primary, S_spanI secondary | Step 2, decision-bearing | Room for a non-gradient-form rule where none exists |
| Planted free and planted key-span states, 3 restarts | Step 2 instrument gate | Optimiser failure read as capacity; a span class that cannot discriminate |
| Non-vacuity of the span constraint on real residuals | Step 2 instrument gate | KILL A recurring through the interface geometry |
| Planted fixed-preconditioner writer with a shared random B* (I5) | Step 2, caps OPEN | A gap that is really a preconditioned gradient writer the B fit missed |
| B penalised toward I and chosen against I on development episodes | Step 2 | A poorly estimated B manufacturing a gap for plain first-order writers |
| Width-256 rank-16 reference (16 episodes per family) | Step 2 capacity disambiguation | "64-d too small" confused with "residual-site states cannot do it" |
| Supervised P and Q fitted by teacher KL on a disjoint family split (conditional) | Step 2 capacity disambiguation | A variance-driven label-free map discarding label-bearing directions read as interface size |
| Norm cap at twice the natural in-context shift, cap-binding rate reported | Step 2 | Off-manifold edits inflating the ceiling ([2412.11299](https://arxiv.org/abs/2412.11299), [2610.07270](https://arxiv.org/abs/2610.07270)) |
| Site-1.0 ablation (8 episodes per family, S_free without the last site) | Step 2 secondary | A logit-level shortcut at the final residual carrying the ceiling |
| Permuted-target re-scoring (no refit) | Step 2 secondary | Recovery that comes from shifting the answer distribution regardless of the probe |
| Shuffled-label targets for the oracle (16 episodes per family) | Step 2 secondary | Episode-specific structure that is not label-driven |
| Lookup families as span-sufficient by construction | built-in prediction P4 | Span gaps that are artifacts of template or key definition |
| 2.7B teacher disagreement rate | Step 1 secondary | Whether a later cross-teacher sibling control would be live (needs at least 0.10 disagreement) |

There is no "baseline method" to beat: the gate compares state classes, all
fitted by the same optimiser with the same per-class learning-rate grid and the
same budget, so no class is undertuned relative to another.

## Evaluation, Statistics, and Leakage Checks

**Units and seeds.** Demonstration seeds [42, 43, 44]: seed 42 episodes fit B
and select learning rates (development); seeds 43 and 44 give the 32
evaluation episodes per family. Oracle initialisation seed 42; restarts with
seeds 43 and 44 on planted and sensitivity episodes. All episode generation uses
PCG64 keyed by (family, seed, episode); manifests are hashed before any GPU run.

**Step 1 statistics.** Per family, G_LD = mean over seeds of (accuracy with gold
minus accuracy with shuffled labels), 1,200 query instances per condition
(3 seeds x 25 episodes x 16 queries). One-sided cluster-t bound with episodes as
clusters (75 clusters), Holm over the 14 families at one-sided alpha 0.05.
Simulation S2 (`compute/decision-sim.json`): a family with no true gap is never
declared eligible (0 of 1,000 at every setting); a true gap of 0.15 is declared
eligible with probability 0.98 to 1.00; a true gap of exactly 0.10 with 0.25 to
0.50 (the point-estimate rule makes the threshold effectively about 0.12).

**Step 2 statistics.** Per family, the one-sided 95% bounds on E_free and on
D_span are t bounds over the 32 evaluation episodes (paired within episode for
D_span), with an episode bootstrap (2,000 resamples, seed 42) as sensitivity.
The gate aggregates by counting families, not by pooling, because the number of
eligible episode-specific families may be as small as 4. S2 under assumed
noise (family SD of E_free 0.10, episode SD 0.15 or 0.30):

- capacity: P(CAPACITY_PASS) is 0.99 or more at a true mean E_free of 0.75,
  0.43 to 0.66 at 0.60, and 0.02 or less at 0.45, where STOP fires with
  probability 0.57 to 0.72; at 0.30, STOP fires with probability 0.998 or more;
- span, with capacity passing: false OPEN under a true tie is at most 0.012
  at every setting; false STOP_SPAN under a true shortfall of 0.10 is at most
  0.004; P(OPEN) at a true shortfall of 0.10 is 0.52 to 0.68 and at 0.20 is
  0.99 or more;
- the tie decision depends on the paired noise: with homogeneous families and
  4 families, P(STOP_SPAN | true tie) is 0.997, 0.88 and 0.17 at paired episode
  SD 0.05, 0.10 and 0.20; with family heterogeneity (half-normal, SD 0.05) it is
  0.71, 0.44 and 0.06. The registration therefore adds a variance-only sample
  size rule: if the pooled within-family SD of D_span on the seed-42
  development episodes exceeds 0.10, 32 more evaluation episodes per
  episode-specific family are drawn (demonstration seed 45) inside the Step-2
  cap. The rule reads the SD, never the mean, and is fixed now.

**What the surrogate says about the instrument (S1,
`compute/oracle-class-semantics.json`).** A linear surrogate of the read path
(32-d interface, 128-d residuals with one outlier direction, 16 fitting and 8
scoring probes, squared error for KL, seeds 42/43/44) with seven synthetic
teachers:

- At the legacy rank-8 port, probe reads keep 0.0 of their energy outside the
  key span and D_span is 0.0000 for every teacher, including retrieval and
  value-directed writers. KILL A is replicated: the dossier's tie rule would
  fire whatever the teacher does.
- At a full-rank port, probe reads keep 0.73 to 0.78 of their energy outside
  the key span (lookup: 0.007, by construction). D_span(B) is -0.29 to -0.16
  for first-order and recursive-least-squares writers (the key-span class
  generalises better than the free class from 16 probes, so these read as
  TIE), 0.001 for lookup, 0.57 to 0.65 for retrieval and 0.78 to 1.21 for
  value-directed writers (GAP). A family-constant teacher is EPISODE_CONSTANT
  in every run (R_const 0.995).
- Two failures the registration now guards against. (i) In an earlier run of
  the same script, with B shrunk toward zero and no selection against I, the
  fitted-B class gave first-order and RLS writers false gaps of 0.20 to 0.41
  (an earlier run still had a transposed-B bug, found and fixed during
  synthesis; neither superseded output is kept, and the numbers are recorded
  here). The registered B is penalised toward I and chosen against I on
  development episodes, which removed the false gaps. (ii) A fixed-preconditioner writer (condition
  number 10) still reads as a gap (0.68 to 0.82): the B fit did not recover B*
  from 6 development episodes. Gate I5 plants such a writer on real residuals,
  and if it fails, OPEN is capped at INCONCLUSIVE_SPAN.
- E_free for non-lookup teachers is only 0.29 to 0.40, because 16 random probes
  in a 32-d read space cannot identify a free per-episode state. The real
  gate's probe reads share one template, so their effective dimension may be
  lower; the registration reports it, plants free states inside the probe-read
  subspace (I2), and treats an identification failure as INSTRUMENT_FAIL, not
  as a capacity verdict.

**Multiplicity.** One decision path (eligibility, instrument, capacity, span) in
a fixed order; secondaries (S_spanI, site-1.0 ablation, placebo floors,
argmax agreement and chance-corrected agreement, permuted-target re-scoring,
shuffled-label targets, 2.7B disagreement) are reported with Holm adjustment
and change no decision.

**Leakage.** Fitting and scoring probes are disjoint within every episode (for
lookup families: same names, different query template). C_f uses only fitting
probes. B and the learning rates use only seed-42 episodes, which never enter a
decision statistic. P and Q see no task text. The task families are generated
in the repository with per-episode random mappings, so the teacher cannot have
memorised an episode's answers; fixed-function families use generic skills
whose pretraining exposure is the point, and they carry no decision.

**Missing data and infrastructure failures.** A job that fails for
infrastructure reasons is retried once from its checkpoint; a family whose
answers are not single tokens under the teacher's tokenizer is dropped before
Step 1 and listed; nothing is dropped after Step 1 starts.

## Compute and Reproducibility

Pinned image (exists in the host's local registry; build 855, commit
`ed5d5a93`; torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention
0.5.2, tilelang 0.1.13): `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`.
It contains no flash-attn, so the teacher is loaded through the Llama remap
with SDPA and cross-checked against fla 0.5.2 with a harness-side SDPA shim in
the smoke job; both paths are harness code, not model-generated code (D7). The
legacy contract's image `@sha256:bde90daa...` lacks tilelang and is not used.

Launch path (dry run, then test-only, then submit; each job one GPU):

```bash
# one manifest per job: smoke, step1, step2, step2-oracle-p (none written yet)
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v1-smoke.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v1-smoke.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e4-icl-write-rule-gate-v1-smoke.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`.
The 2.7B fetch uses `sbatch infra/slurm/host-single-node/fetch-model-cpu.sbatch`
(CPU only). Every executable pilot also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for Step 0, `kind:
slurm-manifest` for the GPU jobs).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 7 (integer ceiling of the
summed caps, 6.42 GPU-h: smoke 0.17, Step 1 0.75, Step 2 4.0, conditional
supervised-map arm 1.5; D22 counts caps, not expected use, and the sum is below
D20's 8 GPU-h line, so D24 is not triggered).

Estimate (`compute/cost-model.json`; FLOPs over MFU times the 989 TFLOP/s
dense BF16 peak; no throughput has been measured for this workload): central
(25% MFU) Step 1 0.10 GPU-h, Step 2 0.91 GPU-h and the conditional
supervised-map arm 0.20 GPU-h; high (12.5% MFU, prompts twice as long, 1.5x
launch overhead) 0.40, 5.16 and 0.98 GPU-h. The high Step 2 exceeds its cap. If
the smoke-derived projection exceeds a cap, a fixed reduction ladder applies in
order (drop shuffled-label targets, drop restart sensitivity, drop the
site-1.0 ablation, halve the width-256 reference); after it the high case is
3.83 GPU-h. The variance rule's 32 extra episodes per episode-specific family
fit inside the cap at the central projection (about 0.95 GPU-h after the
ladder) but not at the high one (about 5.4 GPU-h); they are drawn only if the
smoke-derived projection with them stays under the cap, and otherwise the span
reading is likely to be INCONCLUSIVE_SPAN, which the registration reports as
such. If any projection still exceeds a cap, the registration is not frozen
and returns to the gauntlet.

Checkpoints: per-episode state tensors and optimiser states every 10 minutes to
the persistent run directory, keyed by (family, seed, episode, class, restart),
so a fresh job resumes to identical outputs; a resume-equivalence test runs in
the smoke job. Artifacts: per-probe teacher and student top-64 log-probabilities
and KL, per-episode states, P/Q matrices with hashes, decision record. Third-party
data is fetched at run time pinned by revision and never committed.

## Safety, Data Rights, and Monitorability

- **Models.** fla-hub transformer 1.3B and 2.7B, MIT by card tag (first-party;
  no LICENSE file). Frozen; no weights are released.
- **Data.** All decision-bearing families are generated by repository code from
  hand-written word lists and seeded synthetic strings (MIT). FineWeb-Edu
  (ODC-By) is used only to fit P and Q and is never committed. No Function
  Vectors word lists (several ChatGPT-made), no MUSE (CC-BY-NC-4.0), no
  Super-NaturalInstructions, no CoNLL-2003 (asset cell).
- **Public repository.** No host addresses beyond the documented local registry
  name, no credentials, no private data; host paths in run artifacts are
  rewritten relative to the run root.
- **Host.** No host job of any kind until Q2 S1a's session 2 ends; the GPU work
  waits for a freeze (D58).
- **Monitorability.** The gate trains no policy and produces no deployable
  system. States are tiny, inspectable tensors; every fit is logged with its
  KL trajectory.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Outcome | What it says | What it closes |
|---|---|---|
| STOP_TEACHER | At 1.3B/100B tokens, label-dependent episode-specific in-context learning is present on fewer than 4 of 9 episode-specific families (or fewer than 8 of 14 overall) | D19 at this scale; a measured floor for D16 and any 1.3B fast-weight study |
| STOP_TR | On the families whose correct mapping changes between episodes, one state per family already reproduces the teacher at this interface | Any write-rule question at this interface; says the 1.3B teacher's in-context behaviour on these families is task recognition |
| STOP_INTERFACE_SIZE / _CLASS / STOP_LABEL_FREE_MAP | The 64-d rank-8 four-site interface (or residual-site states in general, or a label-free map) cannot carry the teacher's episode-specific behaviour | D19 as designed; D16's interface premise; tells a future port design which of size, site or map to change |
| STOP_SPAN | Everything episode-specific the interface carries is expressible by key-span writes with a shared map: at this interface the teacher's update is behaviourally inside the class of first-order, preconditioned and recursive-least-squares writes | Step 3's free-versus-gradient-form contrast, without training a rule; a quantitative data point for the open ICL-as-GD question (C10) on a pretrained model, bounded to this interface |
| INCONCLUSIVE_SPAN | The paired noise or the number of capable families is too small | Nothing; the per-family table and noise estimates size any successor |
| OPEN | Some episode-specific behaviour needs write directions outside the key span | Licenses only a Step-3 gauntlet; pre-registered as not identifying a non-gradient rule (within-family retrieval predicts it) |

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable from the Mac; 150 counted discover queries and 73 paper reads logged with returned ids; cutoff 2026-10-09; degraded coverage recorded (no Semantic Scholar, arXiv API, OpenReview, ACL full text, patents, social media; citation graph degraded; index lag) (`doctors/source.json`) | Run Semantic Scholar forward citations for the four closest priors through the host relay after S1a |
| Citation | PASS | Claim registry C01 to C30 with locators, dates and status; every arXiv id snapshotted with HTTP 200 and version history; first-party and abstract-only claims labelled; dossier errors corrected (Jeong, function-induction criterion) (`doctors/citation.json`) | Open the bodies of Wilson and Collins 2019 and Nili et al. 2014 if they are ever cited for a number |
| Novelty | FAIL | No direct prior under the recorded coverage; blind closest-prior discrimination and the novelty refuter have not run; OpenReview, ACL Anthology and Chinese-language venues unsearched (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter; search OpenReview and ACL Anthology |
| Design | FAIL | Intervention, classes, controls, falsifiers, metrics, leakage and decision rules are specified and simulated (S1, S2), but every noise SD is assumed, the oracle optimiser and planted recovery have never run on a real model, and the harness does not exist (`doctors/design.json`) | Build the Step-0 harness and run it as a `cpu-doctor` orx node on a random-init Llama-shaped model |
| Compute | FAIL | No real model loop for this gate, no benchmark adapter, no container smoke, no Slurm dry run, no manifest; the pinned image cannot instantiate the fla teacher without a shim (`doctors/compute.json`, `compute/attestations-not-run.md`) | Write the harness, the smoke manifest, run the dry run and test-only after S1a |
| Safety | PASS | Synthetic in-repository data, FineWeb-Edu ODC-By for P only, MIT checkpoints, no deployable system, host rule respected, public-repository hygiene (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts); Design, the vendored K-Dense
`experimental-design` and `statistical-power` skills (design before data, seed
blocking, power by simulation); Evaluation, K-Dense `statistical-analysis`;
Novelty, K-Dense `literature-review` (PRISMA counts). Integrity gate (the seven
failure modes) is answered in the registration's integrity section.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (wave-1 reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job may run only before 11:30 UTC on 2026-10-10 or after S1a's session 2 has ended)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed; wave-1 reviewers have not run |
| Primary-source evidence | 0 | 0 | not yet reviewed; claim registry C01 to C30 in doctors/citation.json |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind discrimination not run |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; P1 to P5 with falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed; KILL A repaired, S1 semantics check |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S2 operating characteristics under assumed noise |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; caps 6.42 GPU-h, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; synthetic data, MIT checkpoints |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy 1-5 (D19, 2026-09-01) | 62, 57, 65, 65 (lower reviewer; wave 1 killed before judging) | Wave 5: the w-clamp co-condition passes under the gradient-form null (clamp cost 40 to 53 points); positive control is prior memorisation; nothing executable on a model | Exit 5 (under two points of gain across three waves) | Recorded in `legacy/research/gauntlet/2026-09-01-frontier/` |
| new gauntlet, synthesis (2026-10-10) | not scored | KILL A makes the dossier's Step-2 tie rule fire by construction | Gate rescoped to Steps 1-2; full-rank port map; key-span class with shared map B; family-constant floor; planted recovery and non-vacuity gates; decisions by family counts; S1, S2, S3 simulations | Awaiting blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e4-icl-write-rule-gate.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-e4-icl-write-rule-gate/doctors/research-direction-doctor-output.json`.
Two readings the doctor does not make for itself: "all declared budgets must be
positive" comes from parsing the declared `gpu_hours=0.3` as an integer (the
declared budget is honest and not rounded up to pass); and the doctor applies
no 79 cap here because its executable-pilot check is textual, while by the
gauntlet rule's cap table this proposal is capped at 79 (no executable pilot)
and 89 (no independent provider-distinct review), and cannot reach 100 without
D24's trust store.

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
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-e4/program/proposals/2026-10-10-e4-icl-write-rule-gate.md",
  "remediation": [
    "all declared budgets must be positive"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 36,
    "recognizedPrimaryUrls": 36
  },
  "status": "FAIL"
}
```
