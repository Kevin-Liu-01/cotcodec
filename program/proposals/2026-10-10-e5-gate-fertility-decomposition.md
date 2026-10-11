# Research Direction: E5 first step, a decay-by-writes factorial on re-segmented English in two attention-free delta-rule checkpoints (backfill E5, D20)

**Status:** repaired under program decision D68 for a fresh gauntlet run, after gauntlet wave 1 (score 54, the lower of 57 and 54; blind discrimination passed by the letter only; all three refuters refuted; honest exit on the query budget, `program/gauntlet/2026-10-10-e5-gate-fertility-decomposition.jsonl`, row 1); repair by the single owner on 2026-10-10 on the Mac CPU (no GPU, no host job); the draft registration is now `program/preregistrations/e5-gate-fertility-decomposition-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted; the blind critic, the refute-first triad and the two reviewers of this run have not run; no executable pilot exists for this step; a score of 100 cannot be certified in this repository (D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis and the D68 repair (mechanism statement, identification design, estimator, simulations, draft registration) written by a Claude agent acting as the gauntlet's single owner
**Source cutoff:** 2026-10-10
**Coverage limits:** wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex; 135 counted queries by the cells and refuters; 57 cell paper reads; 9 OpenReview term searches, 7 web searches, 2 ACL Anthology fetches; see the wave-1 record) plus this run's repair: 12 counted orx discover queries (alphaXiv keyword and embedding; 2 OpenAlex discover calls failed with HTTP 429 and are logged, not counted), 8 uncounted full-text reads (`orx paper --full`: 2609.33093, 2609.16183, 2606.27510, 1804.11188, 2004.12265, 2404.03646, 2406.14528, 1609.07843) and 6 uncounted OpenAlex API citation-graph lookups (OpenAlex lists 0 citing works for 2609.33093, 2609.16183 and 2606.27510, and 17 for 1804.11188, all screened by title; 94 works citing 2111.00396 match "tokenization", the first 25 screened by title); not searched in this run: Semantic Scholar and the arXiv API (unreachable from the Mac; the host is reserved for the reviewer's lane job), OpenReview and the ACL Anthology (wave 1's searches stand), patents, X, Reddit, GitHub code search, Chinese-language venues; the alphaXiv indices lean to recent papers; full texts read by targeted section
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e5-gate-fertility-decomposition/bundle.json

The budgets are this fresh run's (D68), cumulative over the repair, the
triad, the reviewers and the recorder; at least 30 of the 80 queries are
reserved for the three refuters (six orx discover queries each at minimum).
The repair used 12, leaving 68. The gauntlet's GPU budget (0.3 GPU-h) is for
reviewer inference only; the step's own compute (registered caps 6.25 GPU-h)
runs only after a freeze. The novelty verdict field uses the doctor's
vocabulary; the merged verdict is NARROWED, and the proposal claims no new
mechanism and no new method family (below).

## Changes after wave 1

Wave 1 (row 1 of the gauntlet file, row hash `8b808c0c...`; proposal sha256
`5c12ae3a...`, registration v1 sha256 `f4abf428...`) scored 54: reviewer 1
(claude-opus-5-5) 57, reviewer 2 (qwen3.6-35b-a3b, Slurm 1081) 54. The blind
critic told the designs apart but judged the closest prior the stronger
contribution. All three refuters refuted. The largest defect, for both
reviewers and two refuters, was that the registered kill reading was not
identified and was biased toward the expected KILL: v1 pooled K = 1 (fresh
foils, a presence test at ceiling) with K = 4, and its clamp contrast absorbed
the decay-by-write interaction. D68 ordered one CPU repair by a single owner
of three named defects: (1) the bias toward KILL, (2) pure decay against the
decay-by-write interaction, (3) an honest differentiation from 2609.33093 and
2609.16183. This section is that repair. Each row names who found the
defect, what changed, where it lives in registration v2, and the CPU check
(bundle `compute/repair-d68/`: `estimator_v2.py`, the registered estimator;
S1v2 `mech-sim-v2.py`, identification in a two-layer toy; S2v2
`power-sim-v2.py`, the whole decision path; S3v2 `cost-model-v2.py`, cost).

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | K = 1 with fresh foils is a presence test at ceiling, so the pooled secant is diluted and a true K = 4 decay secant at the line reads KILL with P 0.955 / 0.776 / 0.636 at discordance 0.1 / 0.2 / 0.3 (identification and feasibility refuters; reviewer 1's rerun; both reviewers' largest defect) | K = 1 removed. One primary load K_p, the smallest K in (4, 8, 16) whose canonical accuracy on 200 held-out smoke episodes is at most 90 (ceiling gate) and at least 50; every foil is a code bound in the same episode; the selection never reads an analysis episode | "What changed" 1; Operating point; I4 | S2v2 reproduces v1's dilution with v1's own estimator (P(KILL) 0.954 / 0.792 / 0.655 at a true K = 4 secant of 3; 0.716 / 0.499 / 0.390 at 4). Under v2 a true effect exactly at the line reads KILL with P at most 0.059 at every discordance from 0.10 to 0.46 in profile P1, and at most 0.061 in every other operating-point branch. S1v2's line world W8 (TNIE 3.02 at the selected point): the v1 rule reads KILL with P 1.00 (K = 1 and K = 4 both at ceiling in that toy, NIE 0.0 and 0.17), v2 with P 0.024 |
| 2 | The K = 4 arm was never shown decisive at the line (feasibility refuter; reviewer 1) | n set by S2v2 through the registered path: 2,000 articles (8,000 episodes) at f_p = 2.7, 3,000 at f_p = 2.0 | Data; Operating point | S2v2: P(KILL) for a true null 1.00 / 0.97 / 0.93 / 0.90 at TNIE discordance 0.10 / 0.30 / 0.41 / 0.46 (at 1,000 articles it would be 1.00 / 0.80 / 0.67 / 0.59); P(MATERIAL) at twice the line at least 0.999 |
| 3 | The clamp's natural indirect effect is a noising estimate, NIE = PIE + INT (2606.27510, Prop. 3.1), evaluated at the re-segmented writes, so it absorbs the decay-by-write interaction; in S1 the pure decay cost was 16-45 points against NIE 8-14; the "decay share" was defined by the clamp itself (identification refuter; reviewer 1 partly; reviewer 2's largest defect) | A 2 x 2 factorial: CAN, NAT, CLAMP (noising: canonical decay mass restored at the re-segmented writes, TNIE) and the new DEC arm (denoising: canonical tokens carrying the re-segmented run's per-token decay mass, PNIE). INT = TNIE - PNIE and PNDE are reported; TE = PNIE + PNDE + INT exactly per episode. The "decay share" language is dropped. What TNIE identifies is stated: the oracle benefit of per-canonical-token decay parity at the writes re-segmentation produces, the right estimand for the phase-1 loss | What the primary estimand identifies; Cells; Interventions | S1v2 (two layers, state-dependent writes and decays): the identity holds to floating error in every world; with no extra interference (W1) TNIE 27.7 and PNIE 28.2 (INT -0.5); with self-normalising gates (W2, W4) both are exactly 0; with causally inert decay (W7) 0.34 and 0.0; INT is -0.5 (W3), -6.5 (W5), +6.8 (W6) and -15.6 in the erase-dominated W9 (TNIE 20.8 against PNIE 36.4), so INT's sign and size are world-dependent and must be measured, as v2 does |
| 4 | The kill could be read where decay is irrelevant or cannot act: KILL with R_F near 1 kills the loss without testing whether excess decay costs recall (reviewer 1's transfer defect) | KILL needs TNIE and PNIE below the line and a median R_F of at least 1.5. A material PNIE with TNIE below the line reads MASKED; R_F below 1.5 reads SELF_NORMALIZED; a uniform per-token-clock dose DOSE(f_p) is reported | Decision rules; Consequences | S1v2: W2 and W4 read SELF_NORMALIZED (DOSE would cost 28.4 per log-f unit there), W7 reads KILL; S2v2: P(MASKED) 1.00 / 0.98 / 0.96 / 0.90 and P(SELF_NORMALIZED) 1.00 / 0.98 / 0.93 / 0.91 in their scenarios |
| 5 | The 3-point exact-match line was carried to forced-choice units without calibration (identification refuter; reviewer 1) | Line on the guessing-corrected scale: raw forced-choice differences divided by 0.75 (four-alternative high-threshold correction), 3 points per log-f unit there, i.e. 2.25 raw points; a stricter kill than v1's | What changed 4; estimand | `estimator_v2.py` (GUESS_SCALE) |
| 6 | The f_p fallback was never simulated; f = 1.5 is underpowered; primary_f selected on NAT, the subtrahend of NIE (feasibility and identification refuters; reviewer 1) | f_p from (2.7, 2.0) on held-out episodes only, with a native floor of 30 (chance plus 5); f = 1.5 dropped; n raised to 3,000 articles at f_p = 2.0 | Operating point | S2v2 profile P4 (native accuracy at chance at 2.7, so f_p = 2.0 is selected in 91-94% of replicates): a true null reads KILL 0.995 / 0.824 at discordance 0.10 / 0.42; a true effect at the line reads KILL at most 0.056 |
| 7 | Discordance beyond S2's 0.30 (S1's clamp discordance 0.36-0.45) (feasibility refuter; reviewers) | S2v2 sweeps the latent arm noise so the TNIE discordance spans 0.10 to 0.46, the most the accuracies allow | Statistics | S2v2 grid; operating characteristics above |
| 8 | Passage-level clustering over at most 120 WikiText-103 articles (feasibility refuter; reviewer 1 from 1609.07843 Table 1) | Passages from the train split (28,475 articles, Table 1, read in full in this run), one per article, so the article is the cluster | Data | S2v2 clusters by article with an article share 0.3 of difficulty and effect heterogeneity up to 0.2 latent SD; coverage of the registered interval 0.883 to 0.918 across the grid, the bootstrap's 0.885 to 0.915, decision agreement 0.97 to 1.00 |
| 9 | The simulations did not run the registered estimator: S1 and S2 hard-coded f_p = 2.7; S2 used a normal interval while the bootstrap was registered (feasibility refuter; reviewer 1) | The registered decision interval is the cluster-robust normal interval that S1v2 and S2v2 call; S2v2's vectorised reading is checked against `decide_subject` replicate by replicate (0 mismatches); the operating-point rule runs in every S1v2 and S2v2 replicate | Statistics; Identity (Estimator) | `estimator_v2.py`; S2v2 `vectorised_vs_scalar_mismatches` 0 |
| 10 | S1 was one layer with exogenous writes and no presence channel; no independent ground truth (identification refuter) | S1v2: two layers; layer 2's keys, values, write strengths and decays depend on layer 1's reads, so lower-layer interventions move higher-layer writes; a presence channel makes fresh-foil K = 1 a ceiling test; truth is each world's pool mean, and mechanism truths hold by construction in W1, W2, W4 and W7 | Statistics | S1v2 table below; write drift of layer-2 keys under CLAMP 0.00-0.07 (relative), reported as a ledger in v2 |
| 11 | No write-drift ledger; I1 tested only c = 1; no piece-sum check; the allocation of decay over a token's pieces was an unregistered choice (identification refuter; reviewer 1) | Write-drift ledger (NAT-CLAMP and CAN-DEC, every layer above the first); I2 at c = 0.5 and c = 2 against weight edits; I8 recomputes every clamped and transplanted sum (1e-4); CLAMP-LAST as the allocation sensitivity arm | Readouts; I2, I8; Cells | registration only |
| 12 | Novelty: the clamp is legacy D20's span oracle and Tallec-Ollivier's time-warp condition, uncredited; 2606.27510 uncited; four ledger rows closed on abstracts; no citation-graph traversal (novelty refuter; both reviewers) | All credited and differentiated; 2004.12265, 2404.03646, 2406.14528 and 1804.11188 read in full; 12 counted queries targeting the factorial's components and both closest priors' follow-ups; OpenAlex citation graph checked; fresh blind packets for 2609.33093 and 2609.16183 | Proposal only | `query-log-run2.json`; Closest Prior Work; Novelty Ledger; `blind/` |
| 13 | Subject R's registry entry records trust_remote_code: true and a blocker, against the proposal's text (reviewer 1) | Stated; cleared in prerequisite 2 | Identity; Prerequisites | registration only |
| 14 | No outcome changes a resource decision relative to not running (feasibility refuter; both reviewers' fit scores) | The consequence table now separates KILL (closes the loss with a measured bound), MASKED (redirects any successor to write-side parity, the legacy loss's write-mass term), SELF_NORMALIZED (redirects to a natural-text R_F ledger) and MATERIAL (opens a successor) | Consequences | registration only |
| 15 | Found by the repair itself: the native floor of 40 it first registered refuses exactly the erase-dominated operating points where the factorial reads MASKED (S1v2: two registered-path attempts NOT_ADMISSIBLE; the probe finds every cell with small TNIE and large PNIE under 40) | Native floor 30 (chance plus 5); with PNIE co-primary a low native accuracy no longer biases toward KILL; S2v2 and S1v2 W3, W5 and W9 re-run | Operating point; decision 7 | `int-sign-probe.json`; `superseded-floor40/` kept unedited; W9 now admissible at (4, 2.0) with INT -15.6 |

Not repaired, and why:

- No harness, adapter, manifest, container smoke or Slurm dry run exists
  (Compute FAIL, cap 79); subject G is not on the host and its licence waits
  on Kevin's ruling. These come after a scored package and a freeze; the host
  is reserved for the reviewer's lane job during this run.
- Discordance, the accuracy profile across loads and R_F have not been
  measured on either checkpoint. They are measured in the smoke on held-out
  episodes, and the operating point is chosen from them before any reading;
  S2v2's operating characteristics are conditional on the latent model.
- Signed, provider-distinct reviews cannot exist here (D24, cap 89).
- The deterministic doctor parses `gpu_hours=0.3` as 0 and reports "all
  declared budgets must be positive"; the declared budget is honest and is not
  rounded up to pass (rule 3).

### Decisiveness after the repair

S2v2 (`compute/repair-d68/power-sim-v2.json`): the whole registered path per
replicate (held-out selection, four paired arms, article clustering, the
registered interval and rule), 1,000 replicates per cell, profile P1 (K = 4
admissible, f_p = 2.7), registered n (2,000 articles), article effect
heterogeneity 0.1 latent SD. Probability of the correct reading; for the three
"at the line" scenarios the correct readings are the non-KILL ones (MATERIAL or
INCONCLUSIVE for TNIE at the line; MASKED or PARITY_NULL for PNIE at the line),
and the KILL probability is given in brackets.

| Scenario (b_TNIE, b_PNIE; correct reading) | d = 0.10 | d = 0.30 | d = 0.41 | d = 0.46 |
|---|---:|---:|---:|---:|
| null (0, 0; KILL) | 1.000 | 0.972 | 0.929 | 0.903 |
| one third of the line (1, 1; KILL) | 0.994 | 0.733 | 0.564 | 0.520 |
| both at the line (3, 3; not KILL) | 0.963 [0.000] | 0.955 [0.003] | 0.941 [0.004] | 0.956 [0.002] |
| TNIE at the line (3, 0; not KILL) | 0.949 [0.051] | 0.955 [0.045] | 0.948 [0.052] | 0.949 [0.051] |
| PNIE at the line (0, 3; MASKED or PARITY_NULL) | 0.941 [0.059] | 0.935 [0.046] | 0.889 [0.050] | 0.875 [0.054] |
| material (6, 6; MATERIAL) | 1.000 | 1.000 | 0.999 | 0.999 |
| clock dominant (10, 14; MATERIAL) | 1.000 | 1.000 | 1.000 | 1.000 |
| masked (0, 8; MASKED) | 1.000 | 0.976 | 0.955 | 0.904 |
| masked, partial (1, 12; MASKED) | 0.994 | 0.776 | 0.653 | 0.629 |
| self-normalised (0, 0, R_F 1.1; SELF_NORMALIZED) | 1.000 | 0.975 | 0.931 | 0.912 |

d is the achieved TNIE discordance. Over the seven scenarios away from the
line the mean probability of the correct decisive reading is 0.998, 0.919,
0.862 and 0.838; the weak rows are true effects of one third of the line,
where KILL is correct but harder. A true decay effect at the line is read as
KILL with probability at most 0.059 in every cell (the one-sided 5% of the 90%
interval, by construction). Other operating-point branches at registered n
(`profiles`): K = 4 at ceiling, so K = 8 is selected (P2, 95-97% of
replicates): null 1.00 / 0.92 at d 0.10 / 0.40; K = 4 and 8 at ceiling (P3,
K = 16 in 97-98%): 0.995 / 0.93; native accuracy at chance at 2.7, so f_p =
2.0 (P4, 91-94%): 0.995 / 0.82; canonical accuracy exactly at the ceiling (P5,
K = 4 or 8 about evenly): 1.00 / 0.92; KILL under a true effect at the line at
most 0.061 in every branch; NOT_ADMISSIBLE at most 0.009. Article effect heterogeneity
of 0 or 0.2 changes no probability by more than 0.03.

## Scope and what changed from the dossier

This proposal covers only E5's first step: the language-free decomposition on
English, on m-a-p/1.3B-100B-GatedDeltaNet-pure at 930ed6ae and
fla-hub/rwkv7-1.5B-world at 004140ba, as the dossier states
(`program/evidence/2026-10-06/question-dossier.md`, section 13). Translation
work of any kind is out of scope.

Wave 1 merged four discovery cells by mechanism into fourteen changes to the
dossier's step (M1-M14, kept in the wave-1 proposal at `5c12ae3a...`). Their
status after the repair:

| # | Wave-1 change | Status in v2 |
|---:|---|---|
| M1 | r = 2 cannot identify the decay share; the per-token clamp replaces it | kept, and completed by the transplant arm (the clamp alone is a noising estimate) |
| M2 | Paired simple effect, not an r x f interaction slope | kept; the line is now on the guessing-corrected scale |
| M3 | Only the passage is re-segmented; forced choice; ZERO and BND arms | kept |
| M4 | Re-segmentation is not a pure token-count lever | kept; PNDE now carries it explicitly |
| M5 | Decay visible only at low load, so K = 1 and K = 4 were pooled | replaced: K = 1 was a presence test; the lowest load under the ceiling is selected on held-out data |
| M6 | The fund branch has no valid subject | kept |
| M7 | The prior predicts the kill; n for a tight upper bound | kept; the bound now needs both decay contrasts and R_F at least 1.5 |
| M8 | FILL ladder on GDN-1.3B and RWKV-7 | kept at f_p |
| M9 | Codes tokenize differently by subject | kept |
| M10 | Context ceiling 1,900 tokens | kept (longest cell about 1,736) |
| M11 | Gates may self-normalise (R_F ledger) | promoted: R_F below 1.5 now reads SELF_NORMALIZED |
| M12 | Subject G has no licence | kept (decision 1) |
| M13 | Nothing executable exists | unchanged |
| M14 | Splitting rule R(f, seed) and B(seed) measured on both tokenizers | kept |

The six corrections to the frozen dossier recorded in wave 1 stand (data of
GDN-1.3B documented first-party; the "modest decline" measured on 340M models
only; r = 2 cannot identify; 600 episodes too few; the fund branch has no
subject; the cost estimate). One more: the dossier's kill line is stated on
exact match, and v2 carries it to forced choice by the guessing correction
(2.25 raw points per log-f unit), not unchanged as wave 1 claimed.

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
much forced-choice recall of facts stored before the passage is lost, and how
much of that loss runs through the per-token decay pathway at canonical
writes (PNIE), at the re-segmented writes (TNIE), and through the interaction
of decay with the extra writes (INT)?

The variable is the passage's tokens (canonical or re-segmented at f_p)
crossed with its per-canonical-token decay mass (canonical or re-segmented),
at one load K_p chosen on held-out data.

**Claim scope.** A frozen-checkpoint mechanism measurement at the Component
level of `docs/evidence-model.md`. Not `architecture-causal` (hard rule 8) and
none of the four claim scopes; at most a prerequisite for a later
`portability-protocol` study. The claims it can license are of the forms "in
these two checkpoints, on re-segmented English, restoring per-canonical-token
decay mass recovers (does not recover) at least 3 corrected points of
forced-choice recall per log-f unit", "the extra decay mass costs (does not
cost) at least that much at canonical writes", "the decay-by-write
interaction is negative (positive)", and "the phase-1 forgetting-mass loss is
(is not) killed".

**Hypothesis under test (H_parity).** For each subject s, b_TNIE,s =
mean(CLAMP - NAT) / (0.75 ln f_p) is at least 3. The registered reading is
MATERIAL when b_TNIE is at least 3 with its lower end above 0; with the upper
end of b_TNIE below 3 it is MASKED (b_PNIE material), SELF_NORMALIZED (median
R_F below 1.5), KILL (upper end of b_PNIE also below 3) or PARITY_NULL;
otherwise INCONCLUSIVE.

## Strategic Fit and Why Now

E5 is item 7 of the backfill queue (`program/backlog.md`). D67 restarted every
remaining line; D68 ordered this repair. The step is worth running only if
some outcome changes what the program does, so the consequences are stated
against the dossier's default ("If not run, close D20 by citing 2609.33093"):

| Reading | What it changes against not running |
|---|---|
| KILL | The same closure, now with a measured upper bound from a decay intervention rather than an inference from a distance curve; publishable as the decay-intervention complement of Lee et al. and Boesch and Wee |
| MASKED | Redirects: the forgetting-mass loss is closed, but decay is shown material and the cost runs through the interaction with the extra writes, so any successor targets write-side parity (the legacy loss's write-mass term), not decay |
| SELF_NORMALIZED | Redirects: the gates already charge fragments close to canonical decay; the open question becomes whether natural high-fertility text self-normalises, a cheap forward-only ledger on a multilingual attention-free subject |
| MATERIAL | Opens a successor gauntlet (translation-paired leg on a multilingual attention-free subject); funds nothing by itself |

Three reasons to run it before anything else in D20:

- **It decides the phase-1 loss cheaply.** The same text can take up to 15
  times as many tokens in one language as in another
  ([2305.15425](https://arxiv.org/abs/2305.15425), abstract). The span-parity
  loss of `legacy/directions/20-semantic-clock-gate-parity.md` assumes that
  per-token gates charge such text extra forgetting mass and that this mass
  costs recall. TNIE is exactly the most that parity could recover at the
  writes such text produces, measured with language, content, tokenizer and
  data share held fixed.
- **It measures what the closest priors could not.** Lee et al. never
  intervene on decay and have no tokenization axis; Boesch and Wee ablate
  decay in training in synthetic from-scratch cells. Neither can say what a
  pretrained model's decay costs at inference, nor whether interference
  absorbs it (below).
- **Its scope is honest about reach.** In deployed GDN hybrids recall flows
  through attention, not the recurrent state (Lee et al., Sec. 4.1;
  [2609.04434](https://arxiv.org/abs/2609.04434)). Only attention-free
  subjects test the clock where it could matter.

The expected answer is KILL or MASKED (owner's forecast in the registration);
the design is built for a tight upper bound that a true effect at the line
cannot pass for a kill.

## Primary-Source Evidence

Claim registry (full table with verdicts in `doctors/citation.json`). "Full"
means a cell or the owner read the full text with `orx paper --full`;
"re-read" means synthesis re-read the section in that text; "(repair)" marks a
read made by the D68 repair owner in this run; "abstract" means only the arXiv
abstract page (snapshotted) or OpenAlex metadata was read.

| id | Claim | Source | Locator | Read |
|---|---|---|---|---|
| C01 | K 1 to 16 lowers recall by about 30-40 pp; 128 to 1024 filler tokens at K = 4 cause "only a modest decline" | [2609.33093](https://arxiv.org/abs/2609.33093) v1 2026-09-27 | Sec. 4.2, Fig. 7(a-b) | full, re-read; re-read (repair) |
| C02 | Elapsed-context panel legend lists GLA-340M and GDN-340M only; GDN-1.3B at K = 32 reaches 69% | same | Fig. 7 legend; Fig. 8; Sec. 4.2 | full, re-read; re-read (repair) |
| C03 | Recall scored among four balanced candidates by conditional likelihood; WikiText-103 source-disjoint passages; target logit margin | same | Sec. 2.3 | full, re-read; re-read (repair) |
| C04 | Exact decomposition of the state into contributions transformed by all later transitions (Eqs. 3-5) | same | Sec. 2.2 | full, re-read |
| C05 | Aligning a later write key with the target lowers the target margin by 0.27-0.44 logits | same | Sec. 4.2, Fig. 7(c) | full, re-read; re-read (repair) |
| C06 | m-a-p checkpoint commit 930ed6ae; 32,000-token Mistral vocabulary; 1.466B parameters | same | App. A | full, re-read |
| C07 | Hybrid Qwen3.5-4B: recurrent interventions recover 0.2-3.6%, KV interventions 96-100% | same | Sec. 4.1 | full (dossier VERIFIED; frontier) |
| C08 | Convolution dominates matched recall (about +0.5); decay has no measurable cost (0.561 vs 0.518 at K = 32, p = 0.86); distance gives a flat wall attributed to interference | [2609.16183](https://arxiv.org/abs/2609.16183) v1 2026-09-14 | Sec. 4 "Axis 3", Table 1, Sec. 5 | full, re-read; re-read (repair) |
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
| C21 | DeciMamba: Mamba's limited length generalisation traced to a restricted effective receptive field set by training length; a data-dependent decimation (pooling) method for context extension | [2406.14528](https://arxiv.org/abs/2406.14528) | Abstract; Secs. 1, 4 | full (repair) |
| C22 | In Gated DeltaNet and KDA one scalar gate controls both erase and write | [2605.22791](https://arxiv.org/abs/2605.22791) | Abstract | abstract |
| C23 | Hybrids only; OneRULER at fixed token length; Qwen3.5 tokenizer 2.6x longer in Yoruba; deficit initially larger outside English | [2609.35378](https://arxiv.org/abs/2609.35378) v1 2026-09-28 | Sec. 4, Table 2 | full |
| C24 | REC-ONLY split-prefill drops KV retrieval to 0% in Qwen3.5-4B and Falcon-H1-3B; KV-ONLY keeps 64-98% | [2609.04434](https://arxiv.org/abs/2609.04434) | Sec. 4 | report |
| C25 | Length hurts even with whitespace or masked distractors (13.9% to 85%) | [2510.05381](https://arxiv.org/abs/2510.05381) | Secs. 4.1-4.2 | full |
| C26 | Postulating invariance to time warpings leads to gates: a learnable gate equal to the local time-stretch rate makes a recurrent class quasi-invariant to time warping (continuous time, then discretised) | [1804.11188](https://arxiv.org/abs/1804.11188) | Sec. 1 (time warping to gating); discrete-time translation | full (repair) |
| C27 | Causal mediation analysis with model components (neurons, attention heads) as mediators; natural direct and indirect effects estimated by intervention | [2004.12265](https://arxiv.org/abs/2004.12265) | Abstract; Secs. 2-3 | full (repair) |
| C28 | Activation patching (causal tracing, interchange interventions) adapted to a selective state-space model localises factual recall | [2404.03646](https://arxiv.org/abs/2404.03646) | Abstract; Sec. 2 | full (repair) |
| C29 | Experimental designs that identify mechanisms by manipulating the mediator | [Imai et al. 2013](https://doi.org/10.1111/j.1467-985x.2012.01032.x) | Abstract (OpenAlex) | abstract |
| C30 | Filled delays impair; lengthening them adds little; interference model fits best | [Oberauer and Lewandowsky 2008](https://doi.org/10.1037/0033-295x.115.3.544) | Abstract (OpenAlex) | abstract |
| C31 | Noncrossover interactions are removable by monotone transforms | [Wagenmakers et al. 2012](https://doi.org/10.3758/s13421-011-0158-0) | Abstract (OpenAlex) | abstract |
| C32 | Fisher memory curve: a decaying linear memory trades signal for accumulated interference | [Ganguli et al. 2008](https://doi.org/10.1073/pnas.0804451105) | Abstract (OpenAlex) | abstract |
| C33 | WikiText-103 corpus: train 28,475 articles, validation 60, test 60 | [1609.07843](https://arxiv.org/abs/1609.07843); [dataset](https://huggingface.co/datasets/Salesforce/wikitext) | Table 1; CC BY-SA 3.0 and GFDL (HF tags) | full (repair); HF API |
| C34 | fla 0.5.2 computes GDN's gate in-kernel from the a_proj output, A_log and dt_bias; RWKV-7's log-decay is -0.6065 sigmoid(w_lora); GDN's read passes `o_norm`, an RMSNorm over each head's value dimension | [flash-linear-attention](https://github.com/fla-org/flash-linear-attention) | layer sources read by the asset cell; re-read by synthesis | code read; `layers/gated_deltanet.py` at v0.5.2 re-read (repair) |
| C35 | Measured training throughput 73,045 tok/s/GPU (422M GDN hybrid, fla 0.5.2 image) | `docs/h100-node.md` | table | repository |
| C36 | The same text can take up to 15 times as many tokens across languages | [2305.15425](https://arxiv.org/abs/2305.15425) | Abstract | abstract |
| C37 | The gated delta rule combines gating (rapid erasure) with the delta update (targeted modification) | [2412.06464](https://arxiv.org/abs/2412.06464) | Abstract | abstract |
| C38 | RWKV-7: generalised delta rule with vector-valued gating; models, data listing and code released under Apache 2.0 | [2503.14456](https://arxiv.org/abs/2503.14456) v2 | Abstract | abstract |
| C39 | Single-token retention rate as a tokenizer metric beside mean fertility | [2510.09947](https://arxiv.org/abs/2510.09947) | alphaXiv report | report |
| C40 | Tokenizer choice matters more for low-resource languages (transformers, 54 tokenizers) | [2610.12144](https://arxiv.org/abs/2610.12144) v1 2026-10-08 | Sec. 3 (report) | report |
| C41 | Recurrent LLMs overflow; chunked inference mitigates it | [2505.07793](https://arxiv.org/abs/2505.07793) | alphaXiv report | report |
| C42 | Lexical density limits effective context separately from length | [2606.06203](https://arxiv.org/abs/2606.06203) | Abstract | full |
| C43 | Activation patching by noising estimates NIE = PIE + INT, absorbing the mediator-bypass interaction; denoising estimates the pure indirect effect; INT scales with the distance between clean and patched activations | [2606.27510](https://arxiv.org/abs/2606.27510) v1 2026-06-25 | Prop. 3.1; Thm. 3.2 | full (repair) |
| C44 | Legacy direction 20 registered a span oracle g'_t = g_t / r_s (per aligned sentence) and a forgetting-mass ledger F(s_L) / F(s_en) | `legacy/directions/20-semantic-clock-gate-parity.md` | Mechanism block | repository |
| C45 | Fragmentation, a lossless recoding into smaller units, can strictly increase the optimal finite-context log-loss | [2605.13485](https://arxiv.org/abs/2605.13485) | Abstract | abstract (repair screening) |
| C46 | Delta-rule erase and write share one scalar gate in Gated DeltaNet; an erase-then-write rule decouples where to erase from where to write | [2606.26560](https://arxiv.org/abs/2606.26560) | Abstract | abstract (repair screening) |

First-party labels: every number from a model card (C11, C12) and the m-a-p
paper's own training description (C09) is first-party; no number in this
proposal comes from a blog or social post.

## Closest Prior Work

The differentiation below was rewritten in the repair from full-text re-reads
of both closest priors (2609.33093 Secs. 2.1-2.3, 4.2, 5, 6 and App. B;
2609.16183 abstract, Sec. 4 "Axis 3", Secs. 5-6). It states what each prior
already owns, so the residual is no larger than it is.

1. **Lee, Park, Kim and Ko, How Linear Attention Remembers
   ([2609.33093](https://arxiv.org/abs/2609.33093), v1 2026-09-27).** The
   closest prior. Pretrained GLA-340M, GDN-340M and GDN-1.3B (the same m-a-p
   checkpoint at the same commit as subject G) plus hybrids; controlled
   associative recall in WikiText-103 passages; four balanced candidates
   scored by conditional likelihood, target logit margin, source passages as
   the unit (Sec. 2.3). It owns: the exact decomposition of the state into
   earlier contributions carried through all later transitions (Eqs. 3-5);
   donor-recipient patching of the fact-time write, the pre-query state and
   per-head read outputs; load varied at fixed length against elapsed context
   at fixed load, with "memory load has a substantially larger effect than
   elapsed context alone" (Sec. 4.2); later write keys aligned with or
   orthogonalised against the target (alignment lowers the margin by
   0.27-0.44 logits); recall moving to the attention cache in hybrids. What it
   does not do, checked in the full text: it never intervenes on the decay or
   transition gate (its interventions act on writes, states and reads); its
   elapsed-context arm is shown for the 340M models only (Fig. 7 legend);
   RWKV-7 appears nowhere; there is no tokenization axis; its filler writes
   to the state, so its elapsed arm is decay plus filler interference, not
   decay. **Delta.** This step intervenes on the decay channel itself, in both
   directions (restoring canonical decay mass at the re-segmented writes, and
   adding the re-segmented decay mass at canonical writes), on a
   same-content tokenization axis that changes the number of transitions and
   writes without adding content, and reports the decay-by-write interaction
   that Lee et al.'s filler design cannot separate. **What it does not
   change.** Lee et al.'s load-over-elapsed result already predicts the most
   likely readings here (KILL or MASKED); a KILL would extend it to "decay
   mass at fixed content costs less than the line", not overturn it. Lee et
   al. is the broader contribution (as the wave-1 critic judged); this step is
   a narrow causal test of one sub-question that their tools do not reach.
2. **Boesch and Wee, Anatomy of Associative Recall in Fixed-State
   Recurrences ([2609.16183](https://arxiv.org/abs/2609.16183), v1
   2026-09-14).** Matched from-scratch cells on synthetic masked multi-query
   recall, one knob at a time: short convolution, rank-1 against diagonal
   transition, decay. Decay has no measurable cost (deltanet 0.561 against
   gated deltanet 0.518 at K = 32, p = 0.86, 20 seeds); the haystack wall is
   flat in length and attributed to interference under sparse supervision;
   a distance curriculum lifts it from 0.021 to 1.000. It owns the "decay
   against interference" question in words and the finding that decay is not
   the bottleneck in matched cells. **Delta.** Its decay axis is an ablation
   in training: it asks whether a cell trained without decay recalls as well,
   and the rest of the network can compensate during training. This step
   holds a pretrained model's decay at inference, with every other weight
   fixed, so it asks what the trained model's decay does to recall, and on
   which writes; PNIE is the inference-time analogue of their Axis 3 and INT
   has no counterpart there. Subject R has channel-wise decay, the case
   Boesch and Wee themselves exempt ("any liability measured here is specific
   to the scalar-decay knob at constrained state"). No tokenization axis, no
   pretrained checkpoints. **What it does not change.** If PNIE is below the
   line, the step agrees with Boesch and Wee in a different regime; the
   question is theirs.
3. **Interaction effects in activation patching
   ([2606.27510](https://arxiv.org/abs/2606.27510), v1 2026-06-25; read in
   full in the repair).** Re-derives activation patching from mediation:
   noising estimates NIE = PIE + INT, denoising estimates PIE, and INT scales
   with the distance between clean and patched activations (Prop. 3.1,
   Thm. 3.2). Wave 1's clamp was a noising estimate; v2's factorial is this
   paper's noising and denoising pair applied to one channel (decay), with
   the alignment across unequal segmentations as the only new step. Credited
   as the source of the decomposition; not a prior for the measurement.
4. **The clamp's origins.** Tallec and Ollivier
   ([1804.11188](https://arxiv.org/abs/1804.11188), read in full in the
   repair) derive gates from time-warping invariance: a gate equal to the
   local stretch rate makes a recurrent class quasi-invariant to time
   warping. The clamp imposes that condition by hand, on decay only, per
   canonical token. This project's legacy direction 20 already registered a
   span oracle g'_t = g_t / r_s per aligned sentence and the forgetting-mass
   ledger that became R_F (`legacy/directions/20-semantic-clock-gate-parity.md`);
   the clamp is that oracle at canonical-token granularity, used as a mediator
   intervention rather than as a fix. S4's uniform step-size change for
   resampled input ([2111.00396](https://arxiv.org/abs/2111.00396)) is the
   uniform analogue.
5. **Training-free decay rescaling of frozen recurrent models.** MambaExtend
   (ICLR 2025), DeciMamba ([2406.14528](https://arxiv.org/abs/2406.14528),
   read in full in the repair: limited effective receptive field, decimation),
   Mamba Modulation ([2509.19633](https://arxiv.org/abs/2509.19633)) and
   SpectralShift ([2609.14320](https://arxiv.org/abs/2609.14320)) rescale
   decay for length extension; none ties the rescale to re-segmentation or
   uses it to decompose a cost. The dossier's r = 2 is a uniform member of
   this family and stays as a secondary arm.
6. **Causal mediation by component intervention.** Vig et al.
   ([2004.12265](https://arxiv.org/abs/2004.12265), read in full in the
   repair) estimate natural direct and indirect effects through neurons and
   heads; activation patching localises factual recall in Mamba
   ([2404.03646](https://arxiv.org/abs/2404.03646), read in full in the
   repair). The factorial is a member of this family.
7. **Re-segmentation on transformers and fragmentation theory.** Broken
   Tokens ([2506.19004](https://arxiv.org/abs/2506.19004)), Ghosh and Jyothi
   ([2607.26831](https://arxiv.org/abs/2607.26831)), word recovery
   ([2603.10771](https://arxiv.org/abs/2603.10771)), retokenization symmetry
   ([2606.15521](https://arxiv.org/abs/2606.15521)): all transformers, all
   about whether models cope. Fragmentation into smaller units can strictly
   raise optimal finite-context log-loss
   ([2605.13485](https://arxiv.org/abs/2605.13485), abstract), one reason
   PNDE need not be 0.
8. **Multilingual hybrids and recurrent capacity.** Bandarkar et al.
   ([2609.35378](https://arxiv.org/abs/2609.35378)), 2610.12144 and 2505.07793
   as in wave 1: no attention-free subject, no matched content, no decay
   intervention.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| Load against elapsed context in English on pretrained GDN | Lee et al. 2609.33093 | Same checkpoint G, WikiText passages, four-candidate likelihood, source clustering | FILL on GDN-1.3B and RWKV-7 (Lee: 340M only); the extra tokens come from re-segmenting the same content | high |
| Decay against interference | Boesch and Wee 2609.16183 | The question in words; decay not the bottleneck | Decay held at inference in pretrained checkpoints, not ablated in training; channel-wise decay (subject R), which they exempt; the interaction INT measured | high |
| Noising and denoising with the interaction term | 2606.27510 | The decomposition NIE = PIE + INT and both estimators | Applied to the decay channel across two segmentations of the same text, aligned per canonical token; no new estimator | high (that the estimator is not new) |
| Per-canonical-token decay clamp | Tallec and Ollivier 1804.11188; legacy D20 span oracle | Decay rescaled by the local stretch so that content, not tokens, sets forgetting | Token granularity, decay only, as a mediator patch in both directions; not a fix | medium |
| Decay transplant at canonical writes (DEC) | 2606.27510 (denoising); Lee et al. donor patching | Setting a component to its value under the other input | The component is the per-token decay mass; the donor run has a different number of positions | medium |
| Decay rescale at inference | MambaExtend; DeciMamba 2406.14528; 2509.19633; 2609.14320 | Rescaling a frozen model's decay | Position-specific, matched to another run's measured decay, as an identification instrument; r = 2 secondary | high |
| Re-segmentation as a perturbation | 2506.19004; 2607.26831; 2603.10771; 2606.15521 | Same-content non-canonical tokenization | Attention-free subjects; decomposed by state pathway; facts and answers canonical | high |
| Gate self-normalisation ledger (R_F) and its use as a guard | Tallec and Ollivier (theory); legacy D20 ledger | Gates as time warps; forgetting-mass ratio | Measured per canonical token on fragments in pretrained checkpoints, and a registered guard on the kill | medium |

Novelty wording: No direct prior art found through 2026-10-10 under the
coverage in this proposal's header: wave 1's 135 counted orx discover
queries (listed in `query-log.json` and the wave-1 record) and this run's 12
(`query-log-run2.json`, each with its returned ids and raw-output SHA-256),
8 full-text reads and 6 OpenAlex citation-graph lookups in this run.
Screening for this run (PRISMA style): 177 records returned by the 12 counted
queries, 146 distinct ids; all titles screened, 12 abstracts read
(2610.00232, 2610.05700, 2606.26560, 2605.13485, 2609.24797, 2608.30376,
2609.07681, 2609.06872, 2605.22791, 2609.36322, 2609.34049, 2610.11743); 8
opened in full; 0 direct priors. The combination "same-content English
re-segmentation x per-token decay intervention in both directions x the
decay-by-write interaction, on attention-free pretrained checkpoints" was not
found. Every component is published or is the project's own legacy object,
and the proposal claims no new mechanism or method family: it is a
measurement, and its novelty is the measurement's.

This run's queries and what they returned (full list in the log): keyword
"decay gate intervention recurrent state interference interaction delta
rule" (2609.38169, 2606.26560, 2609.16183, ...; no decay-patching prior);
embedding of the v2 mechanism in plain words after 2026-01-01 (2609.27294,
2610.05700, ...; none); keyword "noising denoising pure indirect effect
recurrent state space model" (diffusion and SSM papers; none); keyword "How
Linear Attention Remembers" after 2026-09-27 (2609.33093 first; no follow-up
with a decay or tokenization axis); keyword "Anatomy of Associative Recall in
Fixed-State Recurrences" after 2026-09-14 (2609.16183 first; 2610.00232 is a
capacity study); keyword "tokenization granularity recurrent state decay
recall subword fragmentation" (2605.13485, 2607.24276, ...; transformers and
tokenizers); embedding on per-token forget gates against extra writes after
2026-06-01 (2609.33093, 2610.05700, 2609.04434, ...; none); keyword "token
fertility multilingual linear attention RWKV Mamba recall gate" (2608.30376,
2609.07681, 2605.22791, ...; none); embedding on patching decay values
between tokenizations in both directions (causal-tracing papers; none);
keyword "discretization step intervention Mamba factual recall delta
patching" (none); keyword "forgetting mass parity tokenization gate
normalization per character recurrent" (none, so the legacy D20 idea has no
direct prior either); embedding on decay against interference by
intervention on a frozen recurrent checkpoint after 2026-03-01 (2609.33093,
2609.16183, 2609.36322, ...; none). Both OpenAlex discover calls (four-way
mediation decomposition) failed with HTTP 429; the OpenAlex API answered the
citation-graph lookups.

## Mechanism and Falsifiable Predictions

The two transitions follow Gated DeltaNet
([2412.06464](https://arxiv.org/abs/2412.06464)) and RWKV-7
([2503.14456](https://arxiv.org/abs/2503.14456)) as implemented in fla 0.5.2.

```text
GDN (subject G):   S_t = a_t S_{t-1} (I - b_t k_t k_t^T) + b_t v_t k_t^T
                   g_t = log a_t = -exp(A_log) * softplus(a_proj(x_t) + dt_bias)    per head
RWKV-7 (subject R): S_t = S_{t-1} (diag(exp w_t) - kk_t^T (a_t * kk_t)) + v_t^T k~_t
                   w_t = -0.6065 * sigmoid(w_lora(x_t))                              per channel

Re-segmentation R(f): canonical passage tokens u_1..u_N -> pieces, round(fN) in total, same bytes;
                      facts, query and codes canonical.

Per-canonical-token decay mass at layer l, head (or channel) h:
  G_c(u) = g at u's position in CAN;   G_r(u) = sum of g over u's pieces in NAT;   R_F(u) = G_r / G_c

Arms (paired by episode), W = passage tokens, D = per-token decay mass:
  CAN   = Y(W0, D0)  canonical tokens, native decay
  DEC   = Y(W0, D1)  canonical tokens, each token's g set to G_r(u)                 (denoising)
  CLAMP = Y(W1, D0)  re-segmented, pieces' g rescaled so their sum is G_c(u)        (noising)
  NAT   = Y(W1, D1)  re-segmented, native decay
  all interventions layer by layer on live values; higher layers respond.

Per episode (raw forced-choice points; b_X = mean / (0.75 ln f_p), line 3):
  TE   = CAN - NAT       total cost
  TNIE = CLAMP - NAT     oracle decay-parity benefit at the re-segmented writes  (primary)
  PNIE = CAN - DEC       pure decay cost at canonical writes                     (co-primary)
  INT  = TNIE - PNIE     decay-by-write interaction
  PNDE = CAN - CLAMP     re-segmentation at canonical decay (writes, erasures, conv or token shift,
                         unfamiliar segmentation)
  TE = PNIE + PNDE + INT exactly.
```

**What the primary estimand identifies.** TNIE is the effect of restoring
every canonical token's summed log-decay to its canonical value while the
passage keeps its re-segmented tokens, with every downstream quantity
(including higher-layer writes and decays) free to respond: the most a
forgetting-mass parity loss could recover on this text if its only effect
were to equalise decay mass. That is the estimand the phase-1 consequence
needs. It is a noising estimate and contains INT (2606.27510), so it is not
"the decay share". PNIE is the cost of the extra decay mass at canonical
writes, the denoising estimate. Neither is a share: with INT not 0 no unique
share exists, so v2 reports the decomposition. What none of them identifies:
the effect of a trained parity loss (training changes the writes too);
transfer to natural high-fertility text (R_F is measured on fragments; the
guard and DOSE bound this, they do not settle it); a pooled "decay pathway"
across subjects (scalar per-head decay against per-channel decay coupled to
in-context removal).

**Why a write-silenced factorial is secondary, not primary.** The other
factorial one could run crosses decay (native or clamped) with the passage's
writes (live or silenced). With the passage silenced, decay's only effect is
to shrink what was stored before the passage relative to the query's own few
writes, and a read that is normalised per head before the output projection
(as in fla's Gated DeltaNet layer) is blind to a uniform shrink except through
that ratio. The zero-write regime is therefore not where a parity loss would
act, and its decay contrast is a lower reference rather than the pure decay
cost.
SIL-NAT and SIL-CLAMP are registered and reported (b_SIL in S1v2 below: 9.65
where TNIE is 27.7, 0.0 where decay is inert).

**S1v2** (`compute/repair-d68/mech-sim-v2.json`): a two-layer gated
delta-rule toy (layer 2's keys, values, write strengths and decays depend on
layer 1's reads), a presence channel, the registered operating-point rule on
200 held-out episodes per cell, pools of 400 articles x 4 episodes as truth,
and the registered estimator and rule resampled at the registered n (2,000
replicates). In eight of the nine worlds held-out canonical accuracy was 96
to 98 at K = 4 and 85 to 90 at K = 16, so the ceiling gate moved them to
K = 16; in W9 (stronger passage writes) it was 82.5 at K = 4, which was
selected.
Effect sizes are not calibrated to the checkpoints; zeros, signs, orderings
and reading semantics are the evidence. b in corrected points per log-f unit.

| World (lambda, rho, write norm) | (K_p, f_p) | b_TE | b_TNIE | b_PNIE | b_INT | b_PNDE | b_SIL | b_DOSE | median R_F | Reading (P at registered n) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| W1 per-token clock, duplicate pieces (0, 1, yes) | (16, 2.7) | 27.6 | 27.7 | 28.2 | -0.5 | -0.1 | 9.7 | 28.4 | 3.00 | MATERIAL (1.00) |
| W2 self-normalising gates, interference (1, 0, no) | (16, 2.7) | 31.8 | 0.0 | 0.0 | 0.0 | 31.8 | 0.1 | 28.4 | 1.00 | SELF_NORMALIZED (1.00) |
| W3 clock and interference (0, 0, no) | (16, 2.7) | 59.3 | 27.5 | 28.0 | -0.5 | 31.8 | 9.7 | 28.4 | 3.00 | MATERIAL (1.00) |
| W4 null (1, 1, yes) | (16, 2.7) | -0.1 | 0.0 | 0.0 | 0.0 | -0.1 | 0.0 | 28.4 | 1.00 | SELF_NORMALIZED (1.00) |
| W5 legacy duplicates (0, 1, no) | (16, 2.7) | 62.8 | 21.7 | 28.3 | -6.5 | 41.1 | 9.7 | 28.4 | 3.00 | MATERIAL (1.00) |
| W6 partial (0.5, 0.5, no) | (16, 2.7) | 44.7 | 12.8 | 6.0 | +6.8 | 32.0 | 1.7 | 28.4 | 1.73 | MATERIAL (1.00) |
| W7 decay causally inert (0, 0, no; decay x 0.02) | (16, 2.7) | 20.1 | 0.3 | 0.0 | +0.3 | 19.7 | 0.0 | 0.0 | 3.00 | KILL (1.00) |
| W8 line, tuned (0, 1, yes; decay x 0.3) | (16, 2.7) | 2.9 | 3.0 | 3.1 | -0.1 | -0.2 | -0.1 | 3.1 | 3.00 | MATERIAL 0.53, INCONCLUSIVE 0.41, PARITY_NULL 0.03, KILL 0.02 |
| W9 erase-dominated (0, 0, no; passage writes 0.15-0.30) | (4, 2.0) | 84.5 | 20.8 | 36.4 | -15.6 | 63.7 | 1.0 | 36.2 | 2.06 | MATERIAL (1.00) |

The identity TE = PNIE + PNDE + INT holds to floating error in every world;
every clamped and transplanted per-token sum equals its target to below
1e-16. Layer-2 key drift under the clamp is 0.00 to 0.07 (relative), so
higher-layer writes do move and the ledger is needed. Three findings matter
for the design. First, mechanism truths are recovered where they hold by
construction: both decay contrasts are exactly 0 when pieces share the
token's decay (W2, W4), TNIE and PNIE agree when the extra pieces add no
interference (W1, INT -0.5), and both are about 0 when decay is causally
inert although R_F is 3 (W7). Second, INT is not small and its sign depends
on the world: near 0 in W1 and W3, positive in W6 (+6.8), negative in W5
(-6.5) and strongly negative in the erase-dominated W9 (-15.6, where
restoring decay at the re-segmented writes recovers 20.8 against a pure
decay cost of 36.4), and in W5 it changes sign between f = 2.0 (+9.9, under
the superseded floor) and f = 2.7. A clamp-only design would misstate the pure
decay cost in either direction, which is why v2 estimates both. The direct
probe (`int-sign-probe.json`, 300 episodes per cell, not the registered path)
finds INT negative in 11 of 12 erase-dominated cells (-1.3 to -20.5). Third, the
wave-1 failure is reproduced and removed: in W8, with TNIE at the line at the
selected point, the v1 rule (pooled K = 1 and K = 4, both at ceiling in this
toy, NIE 0.0 and 0.17 points) reads KILL with probability 1.00 at its own
registered size, and the v2 rule with probability 0.024. The registered
interval covers the pool truth at 0.89 to 0.91 where the contrast is not
degenerate. The repair first registered a native floor of 40. Under it, two
registered-path attempts at an erase-dominated world (passage write strengths
0.4-0.8 and 0.15-0.30) returned NOT_ADMISSIBLE (canonical accuracy 27-35% at
every load in the first; native accuracy 27.5 and 38.5 at K = 4 in the
second), and W3 and W5 fell back to f = 2.0. The probe showed why: in this toy
every cell where restoring decay recovers little while pure decay costs a lot
has native accuracy under 40. With PNIE co-primary a low native accuracy no
longer biases the reading toward KILL, so the floor's only remaining job is to
keep NAT off chance, and v2 registers 30 (chance plus 5). S2v2 and the
affected S1v2 worlds (W3, W5, W9) were re-run under the final value; the
floor-40 outputs are kept unedited in `compute/repair-d68/superseded-floor40/`.
The floor of 30 still refuses the probe's strongest erase setting (writes
0.25-0.45: native accuracy 25 to 31, TNIE 2.6 to 5.8 against PNIE 16.7 to
21.8), where re-segmentation has driven both re-segmented arms to chance; a
MASKED world that extreme would read NOT_ADMISSIBLE, not KILL.

**Predictions and falsifiers** (registration v2; descriptive, they cannot
change the reading):

- **P1, ledger.** Median R_F at f_p above 1.5 on both subjects (gates do not
  self-normalise). Falsified by a median at or below 1.5, which reads
  SELF_NORMALIZED.
- **P2, primary.** No subject reads MATERIAL. Falsified by MATERIAL on
  either.
- **P3.** b_TE at least 10 on both subjects. Falsified by a smaller TE.
- **P4.** CAN - FILL(f_p) is smaller than TE on both subjects
  (re-segmentation costs more than the same number of extra canonical
  tokens). Falsified by the reverse on either.
- **P5.** dG from r = 2 and TNIE differ by more than their combined 90%
  intervals on at least one subject. Falsified by agreement on both.
- **P6.** INT is negative on both subjects (restoring decay at the
  re-segmented writes recovers less than the pure decay cost, as in wave 1's
  one-layer simulation). Falsified by a non-negative INT on either; S1v2 shows
  both signs are possible.

Reject the step as uninformative before reading if an instrument gate fails
(INVALID) or the held-out operating point is not admissible (NOT_ADMISSIBLE).

## Cheapest Decisive Pilot

The step is itself the cheapest decisive experiment: one GPU per subject,
forward passes only, no training. Registered caps: smoke 0.75 GPU-h, subject G
1.75, subject R 3.75, total 6.25 under D22. S3v2 per branch
(`compute/repair-d68/cost-model-v2.json`): at (K_p, f_p) = (4, 2.7), central
0.58 (G) and 1.02 (R) GPU-h with every secondary cell, high 1.33 and 2.96; the
worst branch (16, 2.0) is central 0.77 and 1.39, high 1.80 and 4.13 (the
ladder then drops secondary tiers), and its primary cells alone at the high
scenario need 1.48 and 3.34, inside the caps. The smoke is 0.31 (central) to
0.71 (high) GPU-h for both subjects.

The decisive cells are CAN, DEC, CLAMP(f_p) and NAT(f_p) at K_p on 8,000
(f_p = 2.7) or 12,000 (f_p = 2.0) paired episodes. The smoke's held-out cells
are a cheaper pre-pilot that is registered as a gate, not a reading: they
choose the operating point, and the R_F ledger on them shows whether the
clamp and the transplant are near the identity before the main jobs.

No executable pilot exists today. S1v2 to S3v2 are CPU design evidence, not a
pilot, and none is an orx node.

## Controls, Baselines, and Ablations

- **Identity and exactness.** I1: clamp and transplant hooks at c = 1 against
  unhooked. I2 (G): weight edits A_log -/+ ln 2 against the a_proj hook at
  c = 0.5 and c = 2. I2b (R): chunk kernel against a pure-torch recurrence,
  native, clamped and transplanted. I8: every clamped and transplanted sum
  recomputed.
- **The factorial's fourth cell (DEC).** The denoising counterpart that makes
  INT estimable.
- **Write-silenced pair (SIL-NAT, SIL-CLAMP).** Decay with no passage writes
  (a lower reference, above).
- **Uniform per-token-clock dose (DOSE).** What a pure per-token clock would
  cost at canonical writes; the reference for SELF_NORMALIZED.
- **Allocation (CLAMP-LAST).** Canonical decay mass on each token's last
  piece instead of proportionally.
- **Uniform halving r = 2.** The dossier's intervention, at f = 1 and f_p.
- **Elapsed-context ladder (FILL).** Lee et al.'s arm matched to f_p's token
  count, on both subjects.
- **Boundary only (BND), no passage (ZERO), the other fertility.** As in
  wave 1, descriptive.
- **Ledgers.** R_F per layer and head or channel; write drift; write-overlap
  mass; BPB.
- **Mandatory 2026 baselines** (believability bar item 10) apply to
  architecture claims; this step makes none. SWA plus sinks, tail replay, QED
  and MARCH are not run.

## Evaluation, Statistics, and Leakage Checks

- **Unit and clustering.** The episode is the unit; the article (one passage
  each) is the cluster, four episodes per article. The decision interval is
  the 90% cluster-robust normal interval in `estimator_v2.py`; the percentile
  cluster bootstrap (B = 2,000, seed 42) is reported beside it.
- **Scale.** Raw forced-choice differences divided by 0.75 and by ln f_p
  (corrected points per log-f unit); line 3. The log-probability and
  exact-match versions are reported; only the corrected forced-choice scale
  is read.
- **Operating characteristics (S2v2).** Table in "Decisiveness after the
  repair". Sizing at a true null and TNIE discordance 0.30: P(KILL) 0.80 at
  1,000 articles, 0.94 at 1,500, 0.97 at the registered 2,000. The
  registered interval covers at 0.883 to 0.918 across the grid; at three
  check settings (discordance 0.10, 0.41, 0.46) the cluster-normal interval
  covers at 0.895, 0.900 and 0.920 and the bootstrap at 0.885, 0.895 and
  0.915, with below-line decisions agreeing in 100%, 97% and 99% of
  replicates. Selection near the gates (200 held-out episodes): with true
  canonical K = 4 accuracy 84, 87, 90, 93 and 96, K = 4 is selected with
  probability 0.995, 0.916, 0.54, 0.067 and 0.0003; with true native accuracy
  at (4, 2.7) of 24, 27, 30, 33 and 36, f_p = 2.7 is selected with probability
  0.03, 0.19, 0.50, 0.82 and 0.96 (NOT_ADMISSIBLE 0.11, 0.02, 0.01, 0.003 and
0). A misselection near a gate does not bias
  the reading (the estimand is the effect at the selected point); it changes
  sensitivity only.
- **What S2v2 assumes.** A latent probit model with episode difficulty (article
  share 0.3), a re-segmentation noise shared by NAT and CLAMP, arm noise that
  sets discordance, and article-level effect heterogeneity; accuracies and
  effects per operating point are scenario inputs, not measurements.
- **Multiplicity.** One primary estimand (TNIE) for the consequence; KILL is
  an intersection-union conjunction with PNIE (no inflation); every other
  quantity is descriptive.
- **Missing data.** Lost episodes are rerun; if not possible they are dropped
  from every cell, and more than 2% dropped caps a subject at INCONCLUSIVE.
- **Leakage.** The answer is a random 4-digit code bound in context; every
  candidate is an in-episode code, so the presence shortcut of wave 1 is
  gone; key strings never occur in any passage. WikiText-103 may be in both
  subjects' pretraining data; memorised passage text changes how the passage
  writes equally in every arm of an episode, and is disclosed. Canonical facts
  among fragmented text may cue what to store, more so at higher f; BND and
  ZERO bound it. Lower information per token under re-segmentation (2606.06203,
  2605.13485) sits in PNDE, not in the decay contrasts, because they hold
  decay per canonical token.
- **Red flags guarded.** No outcome-dependent exclusion; the operating point
  is chosen on held-out episodes; the estimator is code before data; the
  vectorised simulation reading equals `decide_subject` on every checked
  replicate.

## Compute and Reproducibility

Image: `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(build 855 from commit ed5d5a93, image ID
`sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b`;
fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0). Neither checkpoint
has ever been loaded in this image on this host; the smoke does it first.

Launch path (dry run, then test-only, then submit; one GPU per job; none of
these manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v2-smoke.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v2-smoke.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e5-gate-fertility-decomposition-v2-smoke.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`;
the same three steps follow for the two main manifests. Subject G's weights
(5,865,376,000 B of fp32 safetensors) are fetched by
`sbatch infra/slurm/host-single-node/fetch-model-cpu.sbatch` after a registry
entry and Kevin's data-rights ruling, when no Q2 job is running. Every
executable pilot also runs as an orx experiment node through
`uv run --locked python scripts/orx_run.py` over a committed
`experiments/orx/node.yaml` (`kind: cpu-doctor` for the new CPU doctor,
`kind: slurm-manifest` for the GPU jobs).

Machine fields: seeds: [42, 43, 44]; gpu_hours: 6.25 (registered caps: smoke
0.75, subject G 1.75, subject R 3.75; at most 8.0 under D22; this is the
step's compute, separate from the gauntlet's 0.3 GPU-h reviewer budget).

Estimate (S3v2): same throughput assumptions as wave 1 (central GDN 40,000
and RWKV-7 20,000 tok/s, hook overhead 1.2, resume 1.1, fixed 0.15 h per job;
high 20,000 and 8,000 tok/s, overhead 1.5, fixed 0.25 h); forward inference
has never been measured on this host. Primary tokens per subject 3.47e7 at
(4, 2.7) to 5.39e7 at (16, 2.0). Below a per-branch throughput floor (10,600
to 16,500 tok/s for G, 4,500 to 7,100 for R) the primary cells alone exceed
the cap and the subject is INFEASIBLE, not cut.

Checkpoints and resume: completed (episode, cell) records every 5 minutes to
the persistent run directory; a fresh job skips completed keys; the smoke runs
a kill-and-resume test requiring identical decisions and log-probabilities
within 1e-4. Artifacts: per-episode records for every cell, per-layer ledgers,
the held-out operating-point table, the decision record. Passage text stays on
the host or in the private archive; the public repository receives ids,
hashes and metrics.

Reproduce the repair's CPU evidence from the worktree root (seeded; the
development Mac was saturated by other work while it ran, so wall times in the
outputs are not representative):

```bash
C=program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/compute/repair-d68
OUT=$(mktemp -d)
for p in misc grid0 grid1 tau prof0 prof1; do .venv/bin/python $C/power-sim-v2.py $OUT/power-$p.json $p; done
python3 $C/merge-power-v2.py $OUT $C/power-sim-v2.json
for w in W1_per_token_clock W2_self_normalised_interference W3_clock_and_interference W4_null W5_legacy_duplicates W6_partial W7_decay_inert W8_line W9_erase_dominated; do .venv/bin/python $C/mech-sim-v2.py $OUT/mech-${w:0:2}.json $w; done
python3 $C/merge-mech-v2.py $OUT $C/mech-sim-v2.json
.venv/bin/python $C/cost-model-v2.py $C/cost-model-v2.json
```

## Safety, Data Rights, and Monitorability

- **Subject R.** apache-2.0 (card; 2503.14456 states Apache-2.0 for code and
  models); registered with a receipt on the host; frozen, not redistributed.
  `models/registry.yaml` still records `trust_remote_code: true` and a
  vendoring blocker for it; prerequisite 2 sets it to false with the
  tokenizer vendored (`ast.literal_eval` instead of the upstream `eval`, vocab
  SHA-256 pinned) before any run. Its modeling code is a re-export of fla.
- **Subject G.** No licence, card or README at 930ed6ae; training data
  documented first-party in 2507.06457. Its use is a ruling for Kevin
  (registration decision 1). Under either option no weights or derived
  weights are redistributed, and the public repository holds aggregate
  metrics, ids and hashes only. The apache-2.0 fallback is registered.
- **Data.** WikiText-103 train split (CC BY-SA 3.0 and GFDL) passages stay off
  the public repository; key lists and templates are written by the project.
- **Untrusted code.** None executes. Model outputs are strings scored on CPU.
- **Host.** No host job of any kind while a Q2 job runs; the repair used no
  host access.
- **Public repository.** No host addresses beyond the documented local
  registry name, no credentials, no passage text.
- **Monitorability.** Nothing is trained or deployed; all interventions are
  inference-time hooks recorded with their parameters.
- **Red lines.** None touched. Safety verdict PASS, conditional on decision 1
  being made before subject G is fetched.

## Negative-Result Value

- **KILL** closes D20's phase-1 loss with an upper bound from a decay
  intervention at both canonical and re-segmented writes, extending Lee et
  al.'s English finding to a same-content fertility axis and to RWKV-7, and
  Boesch and Wee's decay finding from training-time ablation in synthetic
  cells to inference-time intervention in pretrained checkpoints.
- **MASKED** is a positive mechanism finding inside a negative program
  result: decay costs recall on its own, and the extra writes absorb it. It
  points any successor at write-side parity.
- **SELF_NORMALIZED** shows pretrained gates realise Tallec-Ollivier
  quasi-invariance on fragments they never saw, with DOSE reporting what a
  per-token clock would have cost.
- **INT's sign and size** on real checkpoints answers the identification
  refuter's question directly, whatever the reading.
- **SPLIT** is a scalar-against-channel-wise decay difference.
- **INVALID, NOT_ADMISSIBLE or INFEASIBLE** still delivers the first inference
  throughput, loader checks and load-accuracy profile for both subjects on
  this host.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv reachable from the Mac; wave 1's 135 counted queries plus this run's 12 with returned ids and raw-output SHA-256 (2 OpenAlex 429 failures logged); 8 full-text reads and 6 OpenAlex citation-graph lookups logged; cutoff 2026-10-10; degraded coverage recorded (`doctors/source.json`) | Semantic Scholar forward citations through the host relay when the host rule allows |
| Citation | PASS | Claim registry C01 to C46 with locators, dates and read status; the four wave-1 abstract-only ledger rows re-read in full; 2606.27510 and the legacy span oracle credited; every primary URL snapshotted (`doctors/citation.json`) | Open the psychology sources cited from metadata only before any write-up |
| Novelty | FAIL | No direct prior under the recorded coverage; this run's blind critic and novelty refuter have not run; no Semantic Scholar traversal; OpenReview and the Anthology not searched again (`doctors/novelty.json`) | Run the blind critic on each prior packet and the novelty refuter |
| Design | FAIL | Factorial, estimands, operating-point rule, decision rules as code and simulated end to end (S1v2, S2v2); but discordance, accuracy profile and R_F are not measured, and no harness exists (`doctors/design.json`) | Build the harness and the new CPU doctor; measure the operating point, R_F and discordance in the smoke |
| Compute | FAIL | No real model loop, adapter, manifest, container smoke or Slurm dry run; subject G not on the host; inference throughput never measured here (`doctors/compute.json`, `compute/attestations-not-run.md`) | Kevin's ruling, registry entry and fetch; harness; smoke dry run and test-only |
| Safety | PASS | Subject R apache-2.0 with its registry blocker stated; subject G gated on Kevin's ruling with a licensed fallback; passages off the public repo; no untrusted code; no host access (`doctors/safety.json`) | Decision 1 before any fetch |

Protocols followed: Citation, the ARS claim-verification protocol (claim
registry, locators, verdicts); Design, the vendored K-Dense
`experimental-design` and `statistical-power` skills (design before data;
power by simulation of the registered path for every threshold); Evaluation,
K-Dense `statistical-analysis` (paired, clustered intervals, coverage
checked); Novelty, K-Dense `literature-review` (PRISMA counts for this run).
The integrity gate (seven failure modes) is answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after its blind critic and refute-first triad; wave 1's reviewer A scored 57, recorded in the gauntlet file)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's open-weight reviewer lane job has not run; wave 1's reviewer B scored 54, Slurm 1081)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed in this run; consequence table against not running |
| Primary-source evidence | 0 | 0 | not yet reviewed; registry C01 to C46, abstract-only ledger rows closed |
| Defensible novelty delta | 0 | 0 | not yet reviewed; blind packets for 2609.33093 and 2609.16183 |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed; factorial, P1 to P6 |
| Controls and causal identification | 0 | 0 | not yet reviewed; TNIE, PNIE, INT; S1v2 |
| Evaluation and statistics | 0 | 0 | not yet reviewed; S2v2 through the registered path |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; caps 6.25 GPU-h, no executable pilot |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no harness, no manifest, subject G not on host |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed; decision 1 pending |
| Independent adversarial review quality | 0 | 0 | not yet reviewed; no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy D20 waves 1-5 (2026-09-01) | 61, 64, 63 (wave 5 not re-judged) | Hybrid readout, headroom, language identity | Prefix-blind readout, rwkv7 co-primary, synthetic-fertility English | Archived in `legacy/directions/20-semantic-clock-gate-parity.md` |
| dossier (2026-10-06) | not scored | Recurrent state does not carry recall in hybrids; load beats distance | Corrected question: English re-segmentation on attention-free subjects, r = 2 | Recorded in the dossier, section 13 |
| new gauntlet wave 1 (2026-10-10) | 54 (57 / 54) | The kill reading is not identified and is biased toward KILL (K = 1 presence test at ceiling; the clamp absorbs the decay-by-write interaction) | Synthesis: per-token clamp, paired simple effect, canonical facts with forced choice, n from S2, rules measured on the tokenizers | Triad 3 of 3 refuted; honest exit on the query budget; D68 orders one repair |
| D68 repair (2026-10-10) | not yet scored | (wave 1's) | K = 1 removed and a held-out ceiling-gated load; 2 x 2 factorial (TNIE, PNIE, INT); R_F guard; guessing-corrected line; article clustering on the train split; S1v2, S2v2 through the registered path; priors credited and differentiated | Awaiting this run's blind critic, refuters and reviewers |

Budget note: this run declared 80 queries with at least 30 reserved for the
triad; the repair used 12. Paper reads and citation-graph lookups are not
counted.

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e5-gate-fertility-decomposition.md` (exit 1) on the
committed bundle, also stored as
`evidence/2026-10-10-e5-gate-fertility-decomposition/doctors/research-direction-doctor-output.json`.
Three readings the doctor does not make for itself, as in wave 1. "All
declared budgets must be positive" comes from parsing the declared
`gpu_hours=0.3` as an integer; the declared budget is honest and is not
rounded up to pass. The doctor applies no 79 cap because its executable-pilot
check is textual, while by the gauntlet rule's cap table this proposal is
capped at 79 (no executable pilot) and 89 (no independent provider-distinct
review), and cannot reach 100 without D24's trust store. Its 40 URLs include
five doi.org links and one ICLR proceedings PDF that it does not treat as
primary; those claims are labelled by read status in the claim registry. A
first run of this repair flagged "section is empty or contains placeholders:
Compute and Reproducibility" because the reproduce block used `<dir>`; the
block now uses a `mktemp` directory, and the output below is from after that
fix.

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
    "allUrls": 40,
    "recognizedPrimaryUrls": 35
  },
  "status": "FAIL"
}
```
