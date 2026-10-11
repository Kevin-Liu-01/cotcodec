# Research Direction: E7 G1 floor gate, the precondition for translation-equivariant recurrent-state writes: state-carried monolingual and cross-script recall beyond attention's reach in a from-scratch 134M Gated DeltaNet plus SWA-512 hybrid without an equivariance loss (backfill E7, direction 22)

**Status:** repaired under program decision D68 for a fresh gauntlet run, after gauntlet wave 1 (score 51, the lower of 51 and 51 re-checked; all three refuters refuted; no honest exit; `program/gauntlet/2026-10-10-e7-equivariant-writes-g1.jsonl`, row 1). The repair was done by the single owner on 2026-10-10 on the Mac CPU (no GPU, no host contact). The draft registration is now `program/preregistrations/e7-equivariant-writes-g1-v2.md` (new experiment id; v1 superseded and left unedited), a DRAFT, not frozen or admitted, with no ledger row. This run's blind critic, refute-first triad and two reviewers have not run. No executable pilot exists for this gate. A score of 100 cannot be certified in this repository (D24).
**Owner:** Kevin Liu (program owner). Wave-1 synthesis and the D68 repair (identification design, instrument builder, simulations, draft registration) were written by a Claude agent acting as the gauntlet's single owner.
**Source cutoff:** 2026-10-10
**Coverage limits:** Wave 1's coverage (orx 0.2.2 alphaXiv keyword and embedding search and OpenAlex; 97 counted cell queries and 15 by the novelty refuter; 70 paper reads; 19 OpenReview searches; 4 web searches; see the wave-1 record). This run's repair added 37 counted retrieval queries: 16 orx keyword, 6 orx embedding, 5 orx OpenAlex (4 returned HTTP 429, counted), 4 OpenReview API searches over forum notes including ICLR 2027 submissions, 4 ACL Anthology searches over the cached full `anthology+abstracts.bib` (131,473 entries, fetched by the E4 repair and reused, no new download), and 2 OpenAlex citing-works lookups. It also made 7 uncounted full-text reads (`orx paper --full`) of Griffin, MLNeedle, OneRuler, 2609.33093, SWAX, 2610.06750 and 2504.10906. OpenReview per-note pages return a browser challenge, which was not bypassed, so OpenReview-only items are abstract-only. The citation graph is degraded: OpenAlex indexes 0 citations of SWAX and 8 of Griffin, so full-text search on each prior's title phrase is the citation proxy. Not searched: Semantic Scholar and the arXiv API (unreachable from the Mac; the host relay was not used), patents, X, Reddit, Hugging Face papers, Chinese-language venues. Full texts were read by targeted section, not end to end.
**Budgets:** queries=80; wall_minutes=600; tokens=8000000; dollars=150; waves=1; gpu_hours=0.3
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-10-e7-equivariant-writes-g1/bundle.json

The budgets are this fresh run's (D68), cumulative over the repair, the triad,
the reviewers and the recorder. At least 30 of the 80 queries are reserved for
the three refuters (six orx discover queries each at minimum). The repair used
37, leaving 43. The GPU budget (0.3 GPU-h) is for reviewer inference only; the
gate's own compute (registered caps summing to 7.767 GPU-h, central 4.90 GPU-h)
is separate and runs only after a freeze.

The novelty verdict field uses the doctor's vocabulary. The gate makes no
novelty claim. It is the precondition for the equivariance study: that study
can only be informative if a from-scratch model's recurrent state carries facts,
and cross-script matches to them, where attention cannot reach. The gate's
measurements replicate published pathway measurements in this configuration
(2610.06750's recurrent-only and attention-only conditions; SWAX 2509.24552's
window and receptive-field analysis; Griffin 2402.19427's beyond-window
retrieval; 2609.33093's fact-time write blocking). Its one element not found in
prior work, a surface-disjoint cross-script key read through a state that
attention structurally cannot reach, is a protocol transfer of the cross-lingual
needle tests of MLNeedle and OneRuler and is not claimed as a contribution. The
novelty that matters is the later objective's: a translation-pair objective on
the recurrent-state write, NARROWED and not OCCUPIED (Novelty Ledger).

## Changes after wave 1

Wave 1 (row 1 of the gauntlet file, row hash `34901a11...`; proposal sha256
`7f1179c3...`, registration v1 sha256 `cce49578...`) scored 51: reviewer 1
(claude-opus-5-5) 51, reviewer 2 (qwen3.6-35b-a3b, Slurm 1077) 51 re-checked (46
as produced, an arithmetic error). Blind discrimination against 2610.06750 was a
weak pass. All three refuters refuted. The largest defect was identification:
the registered CUT reset the recurrent and convolution states once after the
facts block while SWA kept reading the facts, so SWA relayed them into fresh
states, a model that carries facts could fail CUT, and CUT came first in the
verdict order as INSTRUMENT_INVALID. The same section had three more defects:
the ABLATION did not erase the fact's writes, CROSS and BIND could be passed on
surface form, and the FAIL_CROSS sub-label confounded pathway with distance.
Novelty coverage was incomplete (Griffin uncited; MLNeedle and OneRuler not read)
and the delta table claimed more than the gate measures. S1 did not use the
registered estimator and assumed a larger pool. D68 ordered one CPU repair by a
single owner:
- identification: make the CUT path-complete, prove it by perturbation, fix the
  ablation, and re-order the verdicts;
- novelty: credit 2610.06750 and SWAX and state that G1 is a precondition;
- compute: keep the caps within 8 GPU-h, with the arithmetic.
This section is that repair. Each row names who found the defect, what changed,
where it lives in registration v2, and the CPU check that sizes it. The checks
are in the bundle's `compute/repair-d68/`:
- S3v2 `reach-cut-v2.py`: which intervention removes which path, by complex step
  on a NumPy reference of the registered module graph, checked row by row
  against an exact symbolic reachability count;
- P1 `instrument-pool-v2.py`: the measured NTREX-128 pool and the surface-cue
  controls, counts and rates only;
- S1v2 `gate-sim-v2.py`: the decision rule under the registered estimator;
- S2v2 `cost-model-v2.py`: the caps, with every job's arithmetic written out.

| # | Wave-1 defect (named by) | Repair | Registration v2 clause | Evidence |
|---:|---|---|---|---|
| 1 | The CUT premise is false: one reset of the GDN recurrent and conv states after the facts block leaves SWA layers 3 and 7 reading the facts from post-cut positions and GDN layers 4-6 and 8-10 carrying that relay to the answer; S3 had validated a different intervention (identification and feasibility refuters, reviewer 1 by complex step, reviewer 2; both reviewers' largest defect) | CUT is replaced by REACH. SPAN_CUT replaces the GDN recurrence by its zero-state form o_t = beta_t (k_t . q_t) v_t at every position after the facts block (2610.06750's attention-only condition made path-complete for an SWA hybrid). REACH is run on every trained checkpoint as a deterministic test: answer-position logits must be unchanged (at most 1e-5) when every facts-block token is replaced. A failure is HARNESS_INVALID, a code fix | Interventions; Reads ("Checks"); Structural checks | S3v2, 504 rows over 3 seeds, 7 distances, 12 modes and 2 perturbation sets: the exact-zero pattern of the complex step equals the symbolic reachability on every row. SPAN_CUT is exactly 0 from the facts block at d_f >= 1,561 and nonzero at d_f <= 1,560 (from the queried fact alone: 0 at >= 1,558). v1's single reset is nonzero at every distance; at B3 distances it keeps 15% to 97% of the uncut derivative (facts block). A reset over only part of the post-facts span (one refuter's suggestion) is also nonzero; full disconnection is exactly 0 everywhere |
| 2 | INSTRUMENT_INVALID was checked first, so a leaky check could label the most informative outcome (real state carriage) an engineering failure (reviewer 1, why largest; D68) | Verdict order: HARNESS_INVALID (deterministic harness checks only), PASS, LOTTERY, FAIL_CROSS, INSTRUMENT_INVALID (only when MONO is BELOW in two seeds and in-window recall is under a floor of 0.50 in two seeds), FAIL_MONO, INCONCLUSIVE. No check that a state-carrying model can fail precedes PASS; in-window recall can only turn a failing MONO into INSTRUMENT_INVALID, and only below one half (the 0.80 I1 line is reported, not decision-bearing) | Lines and decision rules | S1v2: a model whose MONO passes with an in-window anomaly (I1 0.70) reads PASS 0.999 under v2 and INSTRUMENT_INVALID 0.999 under v1; a model with MONO just under its line (0.58) and I1 0.70 reads PASS 0.012, LOTTERY 0.225, FAIL_MONO 0.401, INCONCLUSIVE 0.362 (INSTRUMENT_INVALID 0.000) under v2 and INSTRUMENT_INVALID in 0.999 under v1. A PASS-level model under v1's single cut leaking 5% of its margin reads INSTRUMENT_INVALID in 1.000 of replicates under v1. Under v2, REACH does not depend on recall (S3v2), so the probability is 0 by construction |
| 3 | ABLATION was not path-complete or specific: v = 0 still erases along k, the conv carries the fact into the next three tokens, SWA relays feed unablated writes, and MONO and CROSS were pooled (identification refuter, reviewer 1, reviewer 2) | Two interventions. ISO isolates the queried fact: on its span in every GDN layer, beta = 0 and alpha = 1, so the state passes the span unchanged; conv inputs from the span are dropped outside it; no attention enters it. ISO is a deterministic check (logits unchanged when the queried code changes). D1 is ISO without the attention mask: it erases every write made on the fact's own tokens and is a descriptive read, reported for MONO and CROSS separately. PASS no longer depends on it; it sets a "relay-dominated" flag for the grid | Interventions; Structural checks; sub-labels | S3v2: v1's v = 0 is nonzero (queried fact, 59% to 335% of uncut). beta = 0 alone is nonzero (92% to 198%): the input-dependent decay gate is itself a path out of the span, which is why alpha is fixed too. ISO is exactly 0 at every distance. D1 leaves only attention relay (6.5% to 94% of uncut in the random reference) |
| 4 | CROSS and BIND did not identify semantic matching: on NTREX, a length-plus-punctuation oracle picked the target 52% to 66% of the time, while the 15% line needs about 4 points beyond the 1/8 floor; the legacy 4-gram clause, the surface-shared contrast and hard negatives had been dropped (identification refuter, reviewer 1's oracle) | The legacy letter-4-gram clause is restored. Distractor keys are the target's neighbours in a punctuation-and-length order, with a random offset (sliding block). Every cross query is paired with a surface-twin decoy (same punctuation vector, name pattern and length within 5%, no translation of any key). A new line, SEM = binding margin with the real query minus binding margin with the decoy, must have a lower bound of at least 0.03 (with 0, a surface-only model would pass in 0.147 of replicates if the decoy reproduced only 80% of its surface signal; with 0.03, in 0.000). A builder gate B-SURF checks the sealed manifest before any model exists | Instrument (filter, distractors, decoy, B-SURF); Metrics (SEM, DEC); rule 3b | P1 on NTREX (test half, character-level proxies), a learned conditional-logit surface oracle pooled over the four cross-script cells: v1's design 0.66 (length plus punctuation 0.59; reviewer 1's 0.52 to 0.66 reproduced). A first repair attempt, stratified sampling ("v2a"), gave 0.29 and is not registered. v2 gives 0.19 (length plus punctuation 0.18; the query-free central-key oracle 0.12). Decoys reproduce it: 0.20 (0.17). S1v2: a surface-only model reads PASS in 0.000 of replicates under v2 (FAIL_CROSS "surface" 1.000) and in 1.000 under v1 |
| 5 | CROSS was pooled with a same-script pair (En-De), where sub-token cues survive any string filter (identification refuter: require the cross-script pool) | CROSS, BIND and SEM use the four cross-script cells only; En-De is descriptive | Question; Instrument (cells) | P1: under the 4-gram clause only 97 test-half En-De sentences are eligible; the En-De cells reach 32 and 51 prompts, under the 150 floor, so they are dropped before any model exists |
| 6 | The FAIL_CROSS sub-label compared B1 (d at most 480, attention and state) with B3 (d at least 1,600, state only), confounding pathway with distance, and yet picked the successor (identification refuter, reviewer 1) | The sub-label compares X1_attn (B1 under SPAN_CUT: attention only) with X1_state (B1 under RELAY_BLOCK, 2610.06750's recurrent-only condition at the facts boundary: state only) at the same distance. New sub-labels: "decay" (the state matches across scripts at short range only) and "surface" (rule 3b). FAIL_MONO gets "retention" against "no short-range state recall" from I1_state | Lines and decision rules (sub-labels) | S3v2: RELAY_BLOCK leaves the state path (nonzero everywhere); SPAN_CUT at B1 distances leaves attention (nonzero at 300) |
| 7 | Under the separate-document bitext presentation no translation pair is ever in one context, so "representational" is close to a design consequence (reviewer 1) | Half of the bitext (10% of tokens) is co-present (a and b in one document, order random). The other half keeps the prefix-sharing presentation the later write loss needs | Training data (design decision 20) | Motivated by coherent code-switching at GPT-2-small shape (2609.30535: cross-script retrieval P@1 61.4% against 5.5%); no CPU check. Disclosed as a change of A0's data |
| 8 | S1 was optimistic and incomplete: CR1 intervals instead of the registered bootstrap, 900 key sentences against a measured median of 676, larger En-De cells, no surface-cue null, CUT and ABLATION unsimulated (feasibility refuter, reviewer 1) | S1v2 uses the registered estimator throughout (sentence-cluster percentile bootstrap, B = 2,000, seed 42). It runs on the measured design (699 test-half key sentences under the registered salt; cross cells 474, 366, 314, 235) and adds a surface-only null, a decoy-quality sensitivity family, the binding-free null, lock-in, futility, the in-window anomaly, v1's cut leak and decisiveness by world | Statistics | S1v2 (below): prior-weighted P(decisive) 0.8917 at seed SD 0.03 and 0.9118 at 0.06; PASS 0.979 in a PASS world, FAIL_CROSS 0.905 in a FAIL_CROSS world, FAIL_MONO 0.996 in a FAIL_MONO world; a surface-only model PASS 0.000 (v1: 1.000) |
| 9 | The step-overhead probe's three repeats were priced once; priced as three runs, J1 needs 42 minutes and the cap sum 7.87 GPU-h (feasibility refuter) | The probe now runs 100 steps per configuration per repeat, three repeats, 1,800 step-equivalents, priced explicitly. The v2 diagnostics are priced. Resubmissions are bounded so that the D22 sum stays at or under 8.0 GPU-h | Compute caps | S2v2: J1 36 min, J2 13, J3 18, three trunks 133 each, 466 min = 7.767 GPU-h; with the one allowed J2 resubmission, 7.984. Every job's arithmetic is written out |
| 10 | The proposal described itself as an instrument residual and a "within-model decomposition" while the pathway devices are published; the novelty refuter's condition for withdrawing was that G1 be scored as a floor gate that claims no novelty, with the MONO line and the checks recast as replications (novelty refuter, D68) | The gate claims no novelty. It is stated as the precondition for the equivariance study. 2610.06750 is credited for the pathway conditions (SPAN_CUT is its attention-only condition made path-complete; RELAY_BLOCK is its recurrent-only condition). SWAX is credited for the receptive-field reasoning, beyond-receptive-field recall from scratch and the window decomposition (Fig. 6); Griffin for beyond-window retrieval; 2609.33093 for fact-time write blocking and the paraphrased-query pilot. The MONO line and the pathway reads are recast as replications and positive controls in this configuration | Question (claim scope); Closest Prior Work; Novelty Ledger | Full texts read in this run (orx paper --full) |
| 11 | Novelty coverage: Griffin 2402.19427 uncited and never retrieved; MLNeedle and OneRuler not read before their row; no citation-graph, OpenReview or ACL Anthology pass by the refuters; one blind packet only (novelty refuter, both reviewers) | Griffin, MLNeedle, OneRuler, 2609.33093 (Sec. 3, App. F.2), SWAX (Secs. 3, 4.1-4.3, Figs. 5-6), 2610.06750 (Sec. 4.1) and 2504.10906 were read in full. 37 counted queries were run (OpenReview, the ACL Anthology bibliography, OpenAlex citing works, and title-phrase full-text search as the citation proxy). New items were screened: four ICLR 2027 submissions and a WMT 2024 SSM translation study, none a direct prior. A second blind packet (SWAX) was written | Primary-Source Evidence (C44 to C54); Novelty Ledger; `blind/` | `query-log-run2.json`; no direct prior found |
| 12 | Two refuters ran no orx queries (process defect) | This run declares 80 queries with at least 30 reserved for the triad; the repair used 37, leaving 43 | Proposal header | `query-log-run2.json` |

Not repaired, and why:

- No harness, adapter, manifest, container smoke or Slurm dry run exists
  (Compute FAIL, cap 79). They come after a scored package and a freeze, and the
  only host job this run may submit is the open-weight reviewer's lane job.
- P1's surface statistics use character-level proxies (non-whitespace length,
  English word counts), because the 32K tokenizer does not exist yet. B-SURF
  re-measures them on the sealed manifest with the real tokenizer before any
  model exists, and the registration stops if they fail after two redraws.
- S3v2 is a NumPy reference of the module graph at width 16, not the harness.
  The cpu-doctor node must reproduce its table on the harness's own module, and
  REACH and ISO re-check the property on every trained checkpoint.
- SWA-512 throughput on real data is unmeasured; the J1 throughput gate
  (179,940 tokens/s) decides it before any trunk.
- Value of information: even the repaired gate is a weak lever on E7's main
  question (owner's prior P(PASS) about 0.1), and a failure closes only this
  configuration (134M, 1B tokens, W = 512). The sub-labels now pick distinct
  successors, but stopping E7 remains a legitimate owner call.
- Signed, provider-distinct reviews cannot exist here (D24, cap 89).
- The deterministic doctor parses `gpu_hours=0.3` as 0 and reports "all declared
  budgets must be positive". The declared budget is honest and is not rounded up
  to pass (rule 3).

## Scope and what changed from the dossier

This proposal covers only E7's G1 floor gate: the D22 A0 hybrid (no
equivariance loss) with SWA-512 replacing full attention in the measured
134M configuration, read at 200M and 1B tokens. The equivariance arms (A1
write equivariance, A2 projection alignment, A3 placebo, A5 no-bitext, a
2610.06750-style baseline) are out of scope. They need a preregistered subspace
or output-language guardrail design and their own gauntlet, and at about 27
GPU-h their admission is Kevin's under D24. The frozen Qwen3.5-4B
split-prefill confirmation belongs to P-GSM.

The four wave-1 cells were merged by mechanism, not by wording. Seventeen
mechanisms change the gate as the dossier wrote it
(`program/evidence/2026-10-06/question-dossier.md`, section 16). Wave 1
re-checked each against the full text, by simulation (S1), by the cost model
(S2) or by the reach check (S3). The "Where handled" column below is updated to
registration v2. Where wave 1's handling failed (M1's state cut, M2's binding
guard alone, M4's decomposition, M8's pooled pairs, M12's probe pricing, M16's
framing), "Changes after wave 1" gives the defect and the repair.

| # | Mechanism (cells that found it) | What it does to the dossier's gate | Where handled |
|---:|---|---|---|
| M1 | **"Beyond-window" is not state-only** (all four cells; derived independently). Information can travel k x W tokens through k stacked window layers ([2310.06825](https://arxiv.org/abs/2310.06825) §2; [2608.28444](https://arxiv.org/abs/2608.28444) Sec. 2.2 "after l layers, the receptive field is l w"). Models trained with SWA do relay information after its tokens leave the cache ([2609.34049](https://arxiv.org/abs/2609.34049): Mistral 7B 89% at offset +10 with the code evicted). Synthesis adds the GDN short convolutions. Without the recurrent state, the A0 graph reaches 3 x 511 + 9 x 3 = 1,560 positions. S3 confirms on a NumPy stand-in of the layer graph that the complex-step derivative with the state zeroed at every step is nonzero at 1,560 and exactly zero at 1,561 in three seeds, and nonzero at 1,600 with the state | A fact "more than 512 tokens back" can be recalled with no state at all, so the dossier's read does not identify state carriage | Gate bin B3: the facts block ends at least 1,600 tokens back (d_f >= 1,600). B1 (direct) and B2 (relay range) reported from the same checkpoint. v2: REACH (the span cut, exact by S3v2) verifies the bound on every trained checkpoint; wave 1's single-reset cut leaked (Changes, row 1). Training context 4,096 so that B3 fits |
| M2 | **Chance is 1/8, not 1e-4** (synthesis; the cross-domain cell proposed the forced-choice readout). With eight four-digit codes in context, an answer that copies any in-context code without matching the key scores 12.5% EM, because the target slot is balanced | The dossier's cross line of 15% certifies as little as (0.15 - 0.125) / 0.875 = 2.9% genuine binding. The legacy contract computed chance as 1e-4 | The line is kept verbatim (on cross-script cells). BIND (binding margin above 0) and, in v2, SEM (binding margin with the real query minus with a surface-twin decoy, above 0) are required; BIND alone admitted surface cues (Changes, row 4). S1v2's binding-free null never passes. Forced choice and copy rate are reported |
| M3 | **Recurrent recall lock-in varies by seed** (frontier, kill-shot, cross-domain). Fixed-state recall is a lock-in lottery: 1/10 seeds without a distance curriculum, 7/10 with one; 0/6 under a time ramp, 6/6 when gated on accuracy ([2609.16183](https://arxiv.org/abs/2609.16183), first-party, preliminary, toy cells). Pythia-scale training dynamics are otherwise consistent across seeds, with outliers that show loss spikes ([2503.09543](https://arxiv.org/abs/2503.09543)) | A one-seed read is a lottery draw. The dossier gives no seed count and no curriculum distance distribution | Seeds [42, 43, 44]. Per-seed classification; a line passes on at least two seeds ABOVE and none BELOW; a LOTTERY verdict for splits. The curriculum's distance mixture is fixed (50% of first-query distances in the state-necessary range) |
| M4 | **No reference arm means no attribution** (kill-shot: the legacy dense rescue arm A4 was dropped; frontier and cross-domain: add an SWA plus sinks control or a state cut) | Without a reference, a failure cannot be pinned on the state, and a pass cannot be pinned on it either | v2: pathway reads at no training cost, borrowed from 2610.06750 (Sec. 4.1) and made path-complete where needed: SPAN_CUT (attention only after the facts), RELAY_BLOCK (state only across the facts boundary), D1 (the fact's own writes removed), ISO (the fact isolated). FAIL_CROSS sub-labels compare attention-only and state-only cross-script matching at the same distance (B1); wave 1's B1-against-B3 comparison confounded pathway with distance (Changes, row 6) |
| M5 | **The window size decides whether the recurrent path is trained** (frontier, kill-shot). Larger windows hurt the long-context recall of SWA plus xLSTM hybrids ([2509.24552](https://arxiv.org/abs/2509.24552)); "Large-Window Laziness" ([2606.15378](https://arxiv.org/abs/2606.15378)); the "Short-Context Learning Trap" ([2610.10114](https://arxiv.org/abs/2610.10114)) | A failure at SWA-512 does not show a failure at smaller windows | The window stays at the dossier's 512. The curriculum places half of its query distances beyond the attention reach. The limit is stated in every verdict, and an SWA-128 or stochastic-window sibling is named as a successor, not run (budget) |
| M6 | **1B tokens is below the asymptote** (kill-shot, frontier). The first translations without token overlap appear at about 11B tokens in a 1.7B model trained without parallel data ([2604.17633](https://arxiv.org/abs/2604.17633)). In 1B-token hybrid distillation runs "no run has converged" ([2609.35378](https://arxiv.org/abs/2609.35378) Sec. 6.3). Window design changes how fast long-context ability emerges (2606.15378) | A G1 result at 134M and 1B tokens (7.5 tokens per parameter) is a training-speed statement, not a capability statement | Every verdict is stated "at 1B tokens". The 1B read decides; the 200M read is descriptive; an emergence curve (100M, 400M, 800M, 1B) is reported |
| M7 | **Bitext exposure confounds any cross-lingual pass** (kill-shot, frontier, cross-domain). Parallel data mainly speeds early sharing ([2603.29026](https://arxiv.org/abs/2603.29026)). Coherent code-switching raises cross-script bitext retrieval from 5.5% to 61.4% at GPT-2-small shape ([2609.30535](https://arxiv.org/abs/2609.30535)) | A cross-lingual pass at 1B tokens may be bitext exposure, and the no-bitext arm is out of scope | G1 makes no claim about why cross-lingual recall works. CSLS bitext retrieval P@1 on the residual stream and on the pooled GDN write is reported at 200M and 1B. The prefix-sharing presentation is fixed and is the later grid's |
| M8 | **Test languages differ from training languages** (kill-shot, asset). The legacy contract tests En, De and Es, while training has no Spanish | Spanish cells sit at floor by construction | Test languages are En, De, Zh and Th, matching training. v2: CROSS uses the cross-script pairs (En-Zh, En-Th) only; under the 4-gram clause the En-De cells fall under the 150 floor (P1: 32 and 51) and are dropped before any model exists |
| M9 | **The initial decay timescales are short** (cross-domain; synthesis re-ran it in S3). Under fla 0.5.2's initialization, 2.6% of GDN heads start with a timescale above 512 tokens and 0.9% above 1,560. Chrono initialization was designed for exactly this failure ([1804.11188](https://arxiv.org/abs/1804.11188)) | A failure may be retention, not cross-lingual inability | Per-head timescales are logged at initialization and at 1B. The initialization is not changed (that would make A0 differ from the measured config). A chrono-style initialization is named as a successor repair, never applied silently |
| M10 | **EM over four digits is discontinuous** (cross-domain; [2304.15004](https://arxiv.org/abs/2304.15004)). Continuous proxies predict small-scale decisions as well or better ([2504.11393](https://arxiv.org/abs/2504.11393)) | A floor read cannot distinguish "near the line" from "at zero" | EM lines kept. Per-digit accuracy, target log-probability, forced choice among the eight codes and copy rate are reported, and the noise over the last three checkpoints ([2508.13144](https://arxiv.org/abs/2508.13144)) |
| M11 | **An untuned learning rate makes a failure uninterpretable** (cross-domain [2608.11859](https://arxiv.org/abs/2608.11859); frontier [2609.15545](https://arxiv.org/abs/2609.15545), where the learning rate and window change recall formation at 77-79M) | A single-LR failure is INCONCLUSIVE in substance | A three-point LR sweep on held-out LM loss (seed 42, 50M tokens each) with one conditional edge extension. One warmup-stable-decay trunk per seed with the 200M read from a 40M-token decay branch at 160M ([2405.18392](https://arxiv.org/abs/2405.18392): a 20% (1 - sqrt) decay matches cosine) |
| M12 | **The dossier's 2.5 GPU-h is one seed and an eager microbenchmark** (asset). Measured 282,501.4 tokens/s in Slurm 359 with random tokens, eager mode, bf16 parameters, full causal attention and a tied 32K vocabulary. A Qwen-size vocabulary would cost about 2.2x per token | Three seeds and the real pipeline change the price | S2v2 gives caps summing to 7.767 GPU-h (D22 counting; the probe's repeats now priced) and 4.90 central. A throughput gate at 179,940 tokens/s; a futility stop after seed 42 (about 1.95 GPU-h if it fires); a 32K tokenizer; one J2 resubmission at most (sum 7.984) |
| M13 | **Rights and availability** (asset, frontier) | FLORES+ is gated (`gated=auto`; accepting terms is Kevin's action). ParaDocs has no en-zh. The 2610.06750 code repository has no licence | The instrument comes from NTREX-128 (CC BY-SA 4.0, ungated) unless Kevin accepts FLORES+. En-Zh bitext from the ParaCrawl Bonus release, En-Th from SCB-MT-EN-TH-2020. The auxiliary pass in the probe is reimplemented from the paper |
| M14 | **Neither G1 outcome can confirm or kill the equivariance question** (kill-shot: value of information close to zero as written) | As written, a failure is pre-explained and a pass is confounded | A failure carries a sub-label that picks a different successor (port, retention or curriculum redesign, write-loss target, instrument note), and a pass is identified by REACH, BIND and SEM. The owner's prior (FAIL_CROSS most likely, PASS about 0.1) is stated. The VoI argument is answered in "Strategic Fit", not dismissed |
| M15 | **SWA-512 nearly empties the later baseline** (kill-shot). An always-on SWA-512 is already the permanent limit of 2610.06750's attention restriction beyond the attention reach | The grid's "generic recurrent-path loss" baseline adds pressure only inside 1,560 tokens | Not G1's to fix. Recorded for the grid's gauntlet. The probe still prices the auxiliary pass |
| M16 | **Novelty narrowed further** (frontier, kill-shot): CAROT 2609.06381; MAPP (OpenReview Nol0BTGPR3); Maglev 2608.02870; CHARTA (OpenReview QvfwNCiyPg); 2609.19291's null activation alignment; Wu and Dredze's null for explicit alignment ([2010.02537](https://arxiv.org/abs/2010.02537)) | The later arms face a narrower residual and a poor prior | Closest Prior Work; Novelty Ledger, rewritten in v2: the gate claims no novelty and is the precondition for the equivariance study (Changes, rows 10 and 11). G1 reports A0's own write equivariance over the same-prefix floor, which sizes how much room the later loss has |
| M17 | **Pooled cross-lingual numbers hide pairs at floor** (cross-domain: the onset of cross-lingual transfer differs by pair, [2205.11758](https://arxiv.org/abs/2205.11758); subtract language means, [2205.10964](https://arxiv.org/abs/2205.10964)) | A pooled pass can hide a pair at zero | Per-pair and per-layer reporting. CSLS with language means subtracted. Equal cell weights in pooled lines |

Seven corrections to the frozen dossier, recorded here because the dossier
is not edited:

1. "Beyond-window (more than 512 tokens back)" is not state-only. The
   state-free reach of the A0 graph is 1,560 positions (M1; S3v2).
2. Chance for TP-MQAR exact match at N = 8 is 12.5% for an answer that copies
   any in-context code, not 1e-4 (M2).
3. "~2.5 GPU-h" is one seed. Rule 6 asks for three, which come to 7.767 GPU-h
   in summed caps (M12; S2v2).
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
SWA-512 layers (the measured layout), trained from scratch for 1B tokens on En,
De, Zh and Th with 20% bitext (half prefix-sharing, half co-present), a 5%
same-language recall curriculum and no equivariance loss. Consider N = 8 facts
in a block that ends at least 1,600 tokens before the answer position, beyond
the 1,560-position reach of every path that avoids the recurrent state. Does the
model reach exact match of at least 60% when the query repeats the key in its
own language (MONO)? Does it reach at least 15% when the query is a translation
into another script that shares no word, letter 4-gram or digit with any key
(CROSS, on En-Zh and En-Th, both directions), with recall bound to the queried key (BIND) and
not explained by surface form (SEM, the binding margin with the real
translation minus that with a surface-twin decoy, at least 0.03)? Each must hold in at least
two of three seeds, with no seed below the line.

**Claim scope.** This is an admission-gate benchmark outcome on one
from-scratch architecture at one scale (evidence level "benchmark", status
"admission pass", `docs/evidence-model.md`). It is not architecture-causal:
there is no matched control (rule 8). It makes no claim about any equivariance
loss, about production full-attention hybrids, or about other windows, sizes or
token budgets. It makes no novelty claim: it is the precondition for the
equivariance study, and its MONO line and pathway reads replicate published
measurements in this configuration (Closest Prior Work). PASS licenses only a
gauntlet for E7's phase-1 grid.

**Why the dossier asks it.** The corrected question (dossier section 16) asks
whether a loss that matches the recurrent-state write for a fact across its
translations improves cross-lingual recall where attention cannot reach the
fact. That question is only testable if a small from-scratch model carries
facts through the state at all, in-language and across languages. In frozen
full-attention hybrids the state does not carry retrieved facts:
recurrence-only exact retrieval is 0.00 on Qwen3.5-4B
([2609.04434](https://arxiv.org/abs/2609.04434), Table 1), and recurrent
interventions recover 0.2-3.6% against 96-100% for KV
([2609.33093](https://arxiv.org/abs/2609.33093) Sec. 4.1). So the test needs a
model in which attention structurally cannot reach the fact.

## Strategic Fit and Why Now

- **Program position.** E7 is the last item of the backfill queue
  (`program/backlog.md`, order 8; dossier rank 16 of 18, recommendation
  BACKFILL). D67 restarted it; wave 1 scored 51; D68 allows one repair and a
  fresh run, which ends at an honest exit below 60 or if the CUT premise is
  still the largest defect. Its first step is under 8 GPU-h, so a scored,
  reviewed package is actionable within the program without D24.
- **What the gate decides.** Whether E7's from-scratch path is viable at 134M
  and 1B tokens, and if not, why. Each answer selects a different successor:
  - FAIL_MONO "retention" (the state stores facts at short range and loses them
    by 1,600): a chrono-style initialization or curriculum successor;
  - FAIL_MONO "no short-range state recall": the dossier's port to the
    2610.06750 LoRA setting;
  - FAIL_CROSS "state-specific" (attention matches across scripts in-window,
    the state does not, at the same distance): exactly the gap a write loss
    would target, measured cleanly;
  - FAIL_CROSS "decay" (the state matches across scripts at short range only):
    a retention successor, not a write-alignment one;
  - FAIL_CROSS "representational" (no cross-script matching even through
    attention): the port;
  - FAIL_CROSS "surface" (cross-script recall explained by surface form): an
    instrument note, the port;
  - LOTTERY: a lock-in design;
  - PASS: a gauntlet for the grid, with a "relay-dominated" flag that tells the
    grid whether the write loss must target relayed writes.
- **The value-of-information argument (kill-shot cell, novelty refuter,
  reviewer 1), answered.** A failure is not pre-explained any more: each
  sub-label is read from a distance-matched pathway comparison, and half the
  bitext is now co-present, so "representational" is no longer a design
  consequence. A pass is identified by REACH (verified state necessity), BIND
  and SEM. The futility rule caps a monolingual failure at about 1.95 GPU-h. The
  concession stands: the gate is a weak lever on E7's main question (owner's
  prior PASS about 0.1). It is a precondition, not an answer.
- **Why now.** Hybrid multilinguality, memory-pathway balancing and
  recurrent-write analysis all appeared between 2026-09-03 and 2026-10-07
  (2609.04434, 2609.33093, 2609.35378, 2610.06750, 2610.10114). None of these
  papers, as read, tests state-carried cross-lingual recall with attention
  structurally excluded.
- **Assets checked, not assumed** (wave-1 asset cell): 8 H100s idle when last
  read; the measured image is on the host; fla 0.5.2 and tilelang present,
  flash-attn, sentencepiece, datasets and datasketch absent (SWA uses torch
  `flex_attention`, the tokenizer `tokenizers`); about 0.25B tokens on the host
  against the 1.04B needed, so downloads under D1 are required; FLORES+ gated,
  NTREX-128 not; no G1 code exists. This repair made no host contact.

## Primary-Source Evidence

Claim registry (ARS claim-verification protocol). Every row has a URL, a
date, a locator and a read status. "Full" means the full text was read by a
cell or by the repair owner and the quoted span re-checked in the saved text.
The bundle holds a hashed snapshot of every cited URL.

| ID | Claim | Source and date | Locator | Status |
|---|---|---|---|---|
| C01 | Recurrent-only (attention from the current portion to the past portion masked, state carried) and attention-only (state reset at the boundary, attention unchanged) conditions; Qwen3.5-4B and Nemotron-H-4B-Instruct; 8.2k test examples, average context 84k tokens; an auxiliary loss on a pass with attention to preceding context masked; LoRA rank 16, steps halved to match compute; QA 34.6% to 38.5% and recurrent-only 5.0% to 22.8% on Qwen3.5-4B; no multilingual content | [2610.06750](https://arxiv.org/abs/2610.06750) v1, 2026-10-05 | Sec. 3 "Training"; Sec. 4.1 (re-read by the D68 repair); Sec. 4.2 setup; Sec. 5.1; Sec. 5.2 | Full |
| C02 | Same work as an ICLR 2027 submission, created 2026-09-18; the code repository has no licence | [OpenReview nIDJ2pPPOB](https://openreview.net/forum?id=nIDJ2pPPOB); [code](https://github.com/amy-hyunji/Balancing-Memory-Pathways) | search payload; GitHub API license=null | Abstract-only (UNVERIFIABLE_ACCESS for the PDF) |
| C03 | Qwen3.5-4B: KV retrieve 1.00 / 0.00 / 0.89 and language following 0.97 / 0.70 / 0.01 (full / recurrent-only / KV-only) | [2609.04434](https://arxiv.org/abs/2609.04434) v1, 2026-09-03 | Table 1 | Full |
| C04 | Pretrained pure GLA-340M, GDN-340M and GDN-1.3B: blocking the selected head's fact-time write reduces recall by 36-79 pp (Sec. 3.1); near-matched hybrid GDN-340M: recurrent replacement recovers under 1% against over 99% for KV; Qwen3.5-4B 0.2-3.6% against 96-100% (Sec. 4.1); scored as a 4-way likelihood choice; a prose-retrieval competence check with two fixed query paraphrases reaches 56.3% at 512 filler tokens, below its 80% prerequisite (App. F.2) | [2609.33093](https://arxiv.org/abs/2609.33093) v1, 2026-09-27 | Sec. 2.3; Sec. 3.1; Sec. 4.1; App. F.2 | Full (re-read by the D68 repair) |
| C05 | Qwen3.5 has less cross-lingual alignment in 10/13 languages; SWA hybrids show no recurrent-style reorganization; 1B-token runs have not converged | [2609.35378](https://arxiv.org/abs/2609.35378) v1, 2026-09-28 | Finding 5; Finding 7; Sec. 6.3 | Full |
| C06 | GatedDeltaNet-H1 is GDN plus SWA, trained with a 2K window | [2412.06464](https://arxiv.org/abs/2412.06464) v3, ICLR 2025 | Sec. 3, "Hybrid models" paragraph; Sec. 4 setup ("sliding window size of 2K") | Full |
| C07 | The receptive field after l SWA layers is l w; SWA with 4 sinks matches or beats retrofitted linear attention | [2608.28444](https://arxiv.org/abs/2608.28444) v2, 2026-10-04 | Sec. 2.2; Table 1 | Full |
| C08 | After k attention layers information moves up to k x W tokens | [2310.06825](https://arxiv.org/abs/2310.06825), 2023-10-10 | §2 | Full |
| C09 | Latent information relay in SWA-trained models: Mistral 7B 89% at offset +10 with the code evicted; with a gap of at least 512 filler tokens, Glimmer averages 62.9% and Mistral 39.9% (4-way choice); models not trained with SWA stay near chance | [2609.34049](https://arxiv.org/abs/2609.34049) v1, 2026-09-28 | Sec. 4.3; Sec. 4.4 | Full |
| C10 | SWAX: SWA plus xLSTM hybrids trained from scratch (1.4B and 7B, 150B tokens, 16K sequences); the receptive field of stacked windows is O(lw) (pure SWA 128 x 24 = 3,072); NIAH evaluated far beyond it (to 131K); shorter training windows give better long-range recall; a training-time against test-time window grid separates the effects (train and test 512: average NIAH 0.33); monolingual; ICLR 2026 poster ([OpenReview btgVfhudI1](https://openreview.net/forum?id=btgVfhudI1)) | [2509.24552](https://arxiv.org/abs/2509.24552) v3, 2026-05-04 | Sec. 3; Sec. 4.1-4.3; Figs. 5-6 | Full (re-read by the D68 repair) |
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
| C42 | Cross-lingual in-context retrieval (xMRC) over 40+ dense LLMs and 12 languages forms in post-training; pretraining scale alone does not improve it | [2504.10906](https://arxiv.org/abs/2504.10906), 2025-04-15 | Abstract | Full |
| C43 | The legacy phase-0 object doctor still passes on main: 11/11 gates, payload SHA-256 equal to the registered value | asset cell run, `compute/legacy-phase0-doctor-main.json` | payload_sha256 e94aefff... | Repository rerun |
| C44 | Griffin (gated linear recurrence plus local attention, trained from scratch; 7B, 300B tokens) solves phonebook lookup up to a context matching its 1,024 local window and degrades beyond it | [2402.19427](https://arxiv.org/abs/2402.19427), 2024-02-29 | Sec. 6.2; Fig. 6(c) | Full (D68 repair) |
| C45 | MLNeedle: needles from MLQA in one language, questions in the same or another language, on four dense instruction LLMs (Llama2-7B-Chat, Llama3-8B-Instruct, Mistral-7B-Instruct-v0.2, Aya-23-8B); lowest when the needle is outside the English family or mid-context | [2408.10151](https://arxiv.org/abs/2408.10151) (NAACL 2025, [2025.naacl-long.267](https://aclanthology.org/2025.naacl-long.267/)) | Abstract; Sec. 2; Sec. 3 | Full (D68 repair) |
| C46 | OneRuler: 26 languages, NIAH variants, a cross-lingual setting with instructions and context in different languages, on Qwen 2.5 (7B, 72B), Llama 3.1 8B, Llama 3.3 70B, o3-mini-high and Gemini 1.5 Flash; accuracy changes by up to 20% with the instruction language | [2503.01996](https://arxiv.org/abs/2503.01996), 2025-03-03 | Sec. 1; Sec. 2; Sec. 4 | Full (D68 repair) |
| C47 | Information propagation through stacked SWA layers predicts an effective reach of W x H_l (harmonic number), within 20% of measured limits | [OpenReview 5MKfXl078n](https://openreview.net/forum?id=5MKfXl078n) (ICLR 2027 submission, 2026-09-10) | search abstract | Abstract-only (UNVERIFIABLE_ACCESS for the PDF) |
| C48 | Linear-attention recall gaps at long distance are attributed to insufficient supervision in pretraining, not capacity; in-context repetition narrows them | [OpenReview UUldzWxIL4](https://openreview.net/forum?id=UUldzWxIL4) (ICLR 2027 submission, 2026-09-19) | search abstract | Abstract-only |
| C49 | RetNet, Mamba and Mamba-attention hybrids for machine translation: attention improves robustness to length and the recall of named entities | [2024.wmt-1.111](https://aclanthology.org/2024.wmt-1.111/) (WMT 2024) | abstract | Abstract (ACL Anthology) |
| C50 | PreAlign: multilingual alignment established before pretraining (similar representations of aligned words) and kept with code-switching, in dense models | [2407.16222](https://arxiv.org/abs/2407.16222) v1 2024-07-23 (v3 2024-11-16) | abstract | Abstract (orx) |
| C51 | The measured NTREX-128 pool and surface-cue controls: 1,360 eligible sentences, 699 in the registered test half; cross-script cells 474, 366, 314, 235 under builder v2; surface oracle 0.66 (v1 design), 0.29 (stratified), 0.19 (v2), decoys 0.20; En-De 97 eligible, cells 32 and 51 | this bundle, `compute/repair-d68/instrument-pool-v2.json` (NTREX files hashed inside) | cells; cross_script_pooled_equal_weight | Repository CPU measurement (character-level proxies) |
| C52 | Which eval-time intervention removes which path from the facts to the answer in the registered module graph (504 rows; complex step equal to symbolic reachability on every row) | this bundle, `compute/repair-d68/reach-cut-v2.json` | summary_exact_zero_by_distance; symbolic_reach_boundaries | Repository CPU check (NumPy reference, width 16) |
| C53 | Decision-rule operating characteristics under the registered estimator on the measured design | this bundle, `compute/repair-d68/gate-sim-v2.json` | scenarios | Repository simulation (assumed distributions) |
| C54 | Caps and arithmetic (466 min = 7.767 GPU-h) | this bundle, `compute/repair-d68/cost-model-v2.json` | arithmetic; jobs | Repository estimate (measured base, Slurm 359) |

First-party labels: C13 (self-labelled preliminary) and any number from a
README or blog. No number in this proposal comes from X or Reddit.

## Closest Prior Work

G1 is a precondition, and its measurements are borrowed. This section credits
them before it states any delta.

- **2610.06750 (Balancing Memory Pathways)** defines the two pathway conditions
  this gate uses. Its recurrent-only condition masks attention from the current
  portion to the past while the state propagates; its attention-only condition
  resets the state at the boundary while attention is unchanged (Sec. 4.1). G1's
  RELAY_BLOCK is the recurrent-only condition applied at the facts boundary.
  G1's SPAN_CUT is the attention-only condition made path-complete for a
  sliding-window hybrid. In a full-attention model, one reset leaves attention
  as the only boundary crossing. With SWA, attention-relayed information
  re-enters fresh states after the reset and is carried beyond the window, which
  is wave 1's defect (S3v2). So the state is held at zero at every position
  after the boundary. 2610.06750 is also the generic recurrent-path loss that
  E7's later arms must beat. It remains the closest prior for the blind
  packet.
- **SWAX (2509.24552)** trains SWA-plus-recurrent hybrids from scratch, argues
  from the O(lw) receptive field that retrieval far beyond it must use the
  recurrent memory, measures needle retrieval there, and separates training-time
  from test-time windows (Fig. 6). G1's state-necessary bin is that argument,
  with the exact count (convolutions included) verified by perturbation on the
  trained weights. Its window caveat (a 512 window is not the best for recurrent
  recall) is inherited. SWAX is the second blind packet.
- **Griffin (2402.19427)** mixes gated linear recurrence with local attention
  from scratch and shows phonebook retrieval succeeding up to the local window
  and degrading beyond it (Sec. 6.2). It was uncited in wave 1.
- **2609.33093 (How Linear Attention Remembers)** measures in-context recall
  through pure recurrent states of released 340M and 1.3B models, blocks the
  fact-time write (Sec. 3.1, -36 to -79 pp), shows the hybrid's state carrying
  under 1% (Sec. 4.1), and pilots paraphrased prose queries (App. F.2, 56.3%, an
  unmet competence prerequisite). G1's D1 is a stronger form of its write block
  (every GDN layer, decay fixed, convolution spill removed).
- **MLNeedle (2408.10151), OneRuler (2503.01996) and 2504.10906** test
  cross-lingual needles and in-context retrieval on dense LLMs only; grep of the
  three full texts finds no recurrent or hybrid model evaluated (OneRuler names
  Jamba once, in its references).

| Prior | What it occupies | What G1 adds, and whether it is a contribution |
|---|---|---|
| [2610.06750](https://arxiv.org/abs/2610.06750) | Pathway conditions (recurrent-only, attention-only) on pretrained 4B full-attention hybrids; a generic recurrent-path auxiliary loss; monolingual | The same conditions on a from-scratch SWA hybrid, the attention-only one made path-complete and verified exact. A replication device, not a contribution |
| [2509.24552](https://arxiv.org/abs/2509.24552) SWAX | From-scratch SWA hybrids; receptive-field reasoning; retrieval beyond the receptive field; the window decomposition; monolingual | The same reasoning at 134M and 1B tokens with Gated DeltaNet; a cross-script read. MONO is a replication of this kind of measurement |
| [2402.19427](https://arxiv.org/abs/2402.19427) Griffin | Beyond-window retrieval with local attention plus recurrence, from scratch | As above; Griffin counts one window, G1 counts the full receptive field |
| [2609.33093](https://arxiv.org/abs/2609.33093) | Fact-time write blocking; state recall in pure recurrent models; the hybrid's state carrying under 1%; a paraphrased-query pilot | D1 and ISO as stronger write ablations; descriptive reads, not findings |
| [2408.10151](https://arxiv.org/abs/2408.10151) MLNeedle, [2503.01996](https://arxiv.org/abs/2503.01996) OneRuler, [2504.10906](https://arxiv.org/abs/2504.10906) | Cross-lingual needles and context retrieval in dense LLMs | The cross-lingual key read moved to a state that attention cannot reach, with a surface-twin decoy contrast. A protocol transfer; NARROWED; not claimed |
| [2609.04434](https://arxiv.org/abs/2609.04434) | Split-prefill on frozen full-attention hybrids: exact retrieval survives only through KV; output language rides the state | Motivates using a model whose attention cannot reach the fact; the output-language finding is why later arms need a guardrail |
| [2412.06464](https://arxiv.org/abs/2412.06464) GatedDeltaNet-H1 | The architecture family (GDN plus SWA, 2K window) | A0 is H1 with W = 512 at 134M; no architecture claim |
| [2610.00232](https://arxiv.org/abs/2610.00232), [2609.16183](https://arxiv.org/abs/2609.16183) | Fixed-state recall over long filler from task training; lock-in lottery and distance curricula | Natural-language keys and LM pretraining; motivates the three-seed rule and LOTTERY |
| [2609.19291](https://arxiv.org/abs/2609.19291), [2609.30535](https://arxiv.org/abs/2609.30535), [2603.29026](https://arxiv.org/abs/2603.29026), [2604.17633](https://arxiv.org/abs/2604.17633) | Cross-lingual transfer in small from-scratch models (alignment null for parametric knowledge; code-switching aligns representations; parallel data has little effect; translation emerges late) | Set the priors for CROSS; 2609.30535 motivates the co-present half of the bitext |
| [2609.06381](https://arxiv.org/abs/2609.06381) CAROT; MAPP; [2608.02870](https://arxiv.org/abs/2608.02870) Maglev; CHARTA; [2610.01921](https://arxiv.org/abs/2610.01921); [2407.16222](https://arxiv.org/abs/2407.16222) PreAlign | Subspace alignment in dense residuals; guardrail framing; losses on recurrent memory (monolingual); non-residual alignment (MoE routers); alignment injected before pretraining (dense) | Priors for E7's later objective, not for this gate (Novelty Ledger, last row) |

## Novelty Ledger

The gate is scored as a floor gate that makes no novelty claim. Each component
is recorded with the prior that occupies it.

| Component | Closest prior | Same | Delta | Status |
|---|---|---|---|---|
| A0: GDN plus SWA hybrid, measured 134M shape, W = 512 | 2412.06464 (H1) | Architecture family | Window and scale only | Occupied (no claim) |
| State necessity by receptive field (B3 at d_f >= 1,600) | SWAX Sec. 3; 2310.06825; 2608.28444 Sec. 2.2; OpenReview 5MKfXl078n (effective reach W x H_l) | The l x w argument | The exact structural count with convolutions (1,560), checked on the trained weights by REACH | Occupied as reasoning; the check is a design detail (no claim) |
| MONO: in-language recall beyond attention's reach, from scratch | SWAX Figs. 5-6; Griffin Sec. 6.2; 2609.33093 Sec. 3; 2610.00232 | Recall beyond the attention window through a recurrent memory | 134M, 1B tokens, natural-sentence keys, four-digit codes, the 1/8 copy floor | Replication and positive control (no claim) |
| Pathway reads (SPAN_CUT, RELAY_BLOCK, D1, ISO) | 2610.06750 Sec. 4.1; 2609.33093 Sec. 3.1 | Masking attention across a boundary; resetting the state; blocking fact-time writes | The attention-only condition made path-complete for SWA hybrids; the write block extended to every layer with the decay fixed; verified by exact reachability (S3v2) | Borrowed devices (no claim) |
| CROSS: a surface-disjoint cross-script key read through a state attention cannot reach, with a surface-twin decoy contrast | MLNeedle; OneRuler; 2504.10906 (dense models); 2609.33093 App. F.2 (paraphrase pilot, pure recurrent); 2609.04434 ("False Familiars": the state accepts related words) | Cross-lingual needles; paraphrased queries | The read moved into a state-only regime, with decoys that match surface form | NARROWED; a protocol transfer, not claimed as a contribution |
| The later objective: a translation-pair objective on the recurrent-state write (not trained in G1) | 2610.06750 (generic recurrent-path loss); 2608.02870 Maglev and CHARTA (losses on recurrent memory, monolingual); 2609.06381 CAROT (subspace alignment in dense residuals); 2609.19291 (activation alignment null at 360M); 2407.16222 PreAlign and 2610.01921 (alignment outside the recurrent state) | Auxiliary losses on recurrent memory; cross-lingual alignment objectives | A semantic, translation-pair objective on the GDN write, in the regime where attention cannot reach the fact | NARROWED, not OCCUPIED: the novelty that matters, tested only by the grid |

Novelty wording: No direct prior art found through 2026-10-10 under the
coverage recorded in the header, for the later objective or for a cross-script
key read through a recurrent state with attention structurally excluded. The
coverage is:
- wave 1's 97 counted cell queries and 15 novelty-refuter queries;
- this run's 37 counted queries (16 keyword with the mechanism's exact terms and
  each closest prior's title phrase, 6 embedding in plain words, 5 OpenAlex, 4
  OpenReview, 4 ACL Anthology over the full bibliography, 2 citing-works
  lookups);
- 7 full-text reads in this run and 70 in wave 1.
The exact queries and returned ids are in `query-log.json` (wave 1) and
`query-log-run2.json` (this run). Screening counts for this run (PRISMA-style):
- identified: 554 records, 453 unique;
- screened: all titles;
- abstracts read: the top hits of every keyword and embedding query, five
  OpenReview abstracts and two ACL abstracts;
- included as direct prior: 0.

Items newly screened in this run and judged adjacent, not occupying:
- two ICLR 2027 submissions on SWA reach and SWA note-taking (5MKfXl078n,
  HdZogiR5K1);
- two on recall incentives in linear attention (UUldzWxIL4, usnA2Fiw5e);
- a WMT 2024 study of state space models for translation (2024.wmt-1.111);
- MLRBench (2026.eacl-long.290);
- PreAlign (2407.16222).
This is not a claim of global novelty.

## Mechanism and Falsifiable Predictions

**Mechanism of the measurement.** Each GDN head keeps a matrix state S updated
by the gated delta rule. Per token, S decays by alpha, erases along the key and
writes the value-key outer product (fla convention). The layer emits S q into
the residual stream.

How a fact must reach the answer:
- In B3 the facts block ends at least 1,600 positions before the answer. Without
  the recurrent state, the SWA layers move information at most 511 positions
  each and the short convolutions 3 each, 1,560 in all from the block's last
  token. S3v2 confirms this on a NumPy reference of the module graph: the complex
  step and an exact symbolic reachability count agree on every one of 504 rows.
  REACH re-checks it on each trained checkpoint. Every B3 answer that depends on
  the facts therefore depends on them through some GDN state.
- That state may hold the fact because it was written on the fact's own tokens,
  or because SWA read the fact from a later position and a GDN layer wrote it
  there (a relayed write). Both are state carriage. D1 removes the first kind
  and RELAY_BLOCK the second's attention reads across the facts boundary, so the
  two are reported separately.
- For a correct monolingual answer, the code's digits must be written into a
  state with a key that a later query, computed from the repeated key sentence,
  reads back.
- For a correct cross-script answer, the query computed from the translation
  must address the same stored association. The translation shares no word,
  letter 4-gram or digit with any key, the distractor keys share its surface
  shape, and a surface-twin decoy measures what surface form alone retrieves.
  So an SEM of at least 0.03 requires the representations feeding the GDN keys and queries
  to be partly language-invariant beyond surface form.

Why it might fail:
- Retention: initial timescales above 1,600 tokens exist in about 1% of heads
  (wave-1 S3, fla 0.5.2 initialization).
- Interference: 8 facts plus filler in a 64 x 64 state per head.
- Laziness: attention solves half of the curriculum within its reach (SWAX's
  window effect; an ICLR 2027 submission attributes long-distance recall gaps in
  linear attention to missing supervision, OpenReview UUldzWxIL4).
- Undertraining: 7.5 tokens per parameter.
- For CROSS only: missing language-invariant keys at this scale and budget.

**Predictions, each with its falsifier** (thresholds as registered; per seed at
1B tokens; a line passes on at least two seeds ABOVE and none BELOW).

- **P0 (harness).** REACH and ISO hold exactly (largest logit difference at most
  1e-5) on every trained checkpoint, and B-SURF and the manifest assertions hold
  at build time. Falsified, giving HARNESS_INVALID and no statement about the
  state, if any fails. No model behaviour can falsify it when the harness is
  correct (S3v2).
- **P1 (in-window positive control).** I1, B1 monolingual EM, is at least 0.80
  (reported). It is consulted only when MONO fails: I1 under the in-window floor
  of 0.50 in two seeds, together with MONO BELOW in two seeds, gives
  INSTRUMENT_INVALID.
- **P2 (the state carries facts in-language).** MONO is at least 0.60 on B3.
  Falsified, giving FAIL_MONO, if MONO is BELOW in at least two seeds (with I1
  not under its floor in two), or by the futility rule. The sub-label reads I1_state:
  "retention" or "no short-range state recall".
- **P3 (the state carries cross-script matches).** CROSS is at least 0.15 on B3
  cross-script cells, with BIND above 0 and SEM at least 0.03. Falsified, giving
  FAIL_CROSS, if MONO passes and CROSS or BIND is BELOW in at least two seeds
  (sub-label from X1_attn and X1_state), or if CROSS and BIND pass while SEM
  does not and DEC is ABOVE (sub-label "surface").
- **P4 (reliability).** No line splits across seeds. Falsified, giving LOTTERY,
  if MONO or CROSS has a seed ABOVE and a seed BELOW.
- **P5 (descriptive pathway reads, no decision).** A3 (the share of B3's binding
  margin left after D1, MONO and CROSS separately), R3 (B3 under RELAY_BLOCK)
  and B2_attn (B2 under SPAN_CUT). PASS carries the flag "relay-dominated" if A3
  is above 0.5 in two seeds.

## Cheapest Decisive Pilot

There is no executable pilot for this gate. Nothing has run on a GPU and the
harness does not exist. The cheapest decisive experiment is the registered gate
itself, sized by S2v2:

| Job | What | Cap |
|---|---|---:|
| J1 | Smoke (300 steps, real mixture, seed 42) with gates: finite and decreasing loss, cached and uncached evaluator equal, SPAN_CUT and ISO invariance on smoke prompts, throughput at least 179,940 tokens/s. Then the step-overhead probe (A0; A0 plus A1 write extraction; A0 plus one 2610.06750-style auxiliary pass; 100 steps each, three repeats), then the three-point LR sweep | 36 min |
| J2 | Fresh-job resume from J1's step-200 checkpoint (rule 7) | 13 min |
| J3 | Conditional LR extension | 18 min |
| T42 | 1B-token trunk with the 200M branch, then all reads and checks | 133 min |
| T43, T44 | Same, only if seed 42 does not meet the futility rule | 133 min each |

The decisive read is the 1B checkpoint of the three trunks, on B3. The
experiment is decisive in the registered sense (every outcome maps to one verdict
and one action); S1v2 gives the probability of a decisive verdict by world. It
is not decisive for E7's main question, which needs the grid.

CPU evidence that exists now, none of it a pilot:
- S3v2 (`compute/repair-d68/reach-cut-v2.py`): which intervention removes which
  path, 504 rows, complex step equal to exact symbolic reachability on every
  row;
- P1 (`compute/repair-d68/instrument-pool-v2.py`): the measured NTREX-128 pool,
  the v2 builder's cell sizes and its surface-oracle levels;
- S1v2 (`compute/repair-d68/gate-sim-v2.py`): the decision rule under the
  registered estimator on the measured design;
- S2v2 (`compute/repair-d68/cost-model-v2.py`): caps with every job's
  arithmetic;
- wave 1's S1, S2 and S3 and the legacy phase-0 object doctor's rerun, kept
  unedited.

The executable-pilot cap (79) applies.

## Controls, Baselines, and Ablations

Structural checks (deterministic; HARNESS_INVALID on failure):
- **REACH**: SPAN_CUT on 64 B3 prompts with the facts block replaced by random
  tokens; the answer logits must not move.
- **ISO**: the queried fact isolated on 64 B3 prompts with its code changed; the
  answer logits must not move.
- **B-SURF and the manifest assertions** at build time.

Within the same checkpoint, at no training cost (descriptive):
- **B1 direct bin**: I1 (reported against 0.80; consulted against the 0.50
  floor only for INSTRUMENT_INVALID) and X1.
- **Pathway reads at the same distance**: X1_attn and I1_attn (B1 under
  SPAN_CUT) against X1_state and I1_state (B1 under RELAY_BLOCK), for the
  sub-labels.
- **B2 under SPAN_CUT**: what attention and the convolutions alone carry over the
  relay range (the relay concern, measured correctly this time).
- **B3 under RELAY_BLOCK and under D1**: how B3 recall splits between states
  written inside the facts block and relayed writes, and between the fact's own
  writes and others.

On the instrument:
- **Copy floor**: BIND cancels it per prompt.
- **Surface form**: the letter-4-gram filter, the sliding-block distractors, the
  surface-twin decoy and SEM, and B-SURF.
- **Cross-script only** in the decision lines; En-De descriptive.
- **Reserved codes**, **no digits in keys or filler**, **balanced target slot**.
- **Leakage controls in the cpu-doctor node**: a retrieval-impossible prompt and
  a value-permutation control must give EM at the no-information level under an
  oracle reader.

Training-side controls: the LR sweep on held-out LM loss with the instrument
never read; three seeds with seed-specific data order; a held-out LM loss curve
and the beyond-reach in-context loss gap.

Baselines not run, and why:
- **A same-depth pure SWA plus sinks model** (rule 10's 2026 baseline,
  2608.28444). It is mandatory for a recall claim, which G1 does not make. For
  state necessity, REACH answers the same question on the same weights.
- **A dense full-attention model** (the legacy A4 rescue). X1_attn gives an
  in-model reference for in-window cross-script matching.
- **An SWA-128 or stochastic-window sibling** (SWAX). It is a successor, named in
  any FAIL verdict.
- **QED and MARCH.** Mandatory for a recall or interference claim, which G1 does
  not make.

Ablations out of scope: every equivariance arm, A5 no-bitext, a curriculum
ramp, chrono initialization.

## Evaluation, Statistics, and Leakage Checks

- **Unit and estimator.** The prompt; per seed, the equal-weight mean of cell
  means. 90% sentence-cluster percentile bootstrap (B = 2,000, seed 42): every
  prompt that queries a resampled sentence, in any cell, moves together with its
  decoy.
- **Lines.** MONO 0.60, CROSS 0.15 (cross-script), BIND 0, SEM 0.03; DEC 0 for the
  surface sub-label; I1 0.80 reported, and the in-window floor 0.50 for
  INSTRUMENT_INVALID only. Per seed ABOVE, BELOW
  or UNRESOLVED; a line passes on at least two seeds ABOVE and none BELOW.
  Verdicts in order: HARNESS_INVALID, PASS, LOTTERY, FAIL_CROSS,
  INSTRUMENT_INVALID, FAIL_MONO, INCONCLUSIVE. A futility stop after seed 42
  applies if MONO's upper bound is under 0.30.
- **Operating characteristics** (S1v2; 1,000 replicates per scenario over
  generator seeds 42, 43 and 44; the registered estimator in every replicate;
  the measured design; every distribution assumed):

  - Half-widths per seed: MONO 0.0209, CROSS 0.0173, BIND 0.0188, SEM 0.0229; coverage of the registered bootstrap 0.917 (MONO) and 0.88 (CROSS) at nominal 0.90.
  - At seed SD 0.03: P(PASS) on MONO is 0.130 at the line, 0.415 at +2 and 0.867 at +5; on CROSS 0.150 at the line, 0.657 at +3 and 0.906 at +5; P(FAIL_CROSS) at 0.10 is 0.905.
  - A surface-only model reads PASS 0.000 (FAIL_CROSS "surface" 1.000) under v2 and 1.000 under v1. If the decoy reproduced only 80%, 60% or 50% of its surface signal, PASS would be 0.000, 0.012 and 0.052 (with SEM's threshold at 0: 0.147, 0.600, 0.809).
  - The binding-free null never passes (P(PASS) 0.000 at copy probability 1.0).
  - Invalidity: an in-window anomaly with MONO passing reads PASS 0.999 under v2 (INSTRUMENT_INVALID 0.999 under v1); MONO at 0.58 with I1 0.70 reads INSTRUMENT_INVALID 0.000 under v2 (0.999 under v1); v1's single cut leaking 5% of the margin reads INSTRUMENT_INVALID 1.000 under v1, while v2 reads PASS 1.000.
  - Lock-in mixture: P(PASS) 0.353 and LOTTERY 0.335 at pi = 0.7; futility stops after seed 42 in 0.888 of replicates at pi = 0.1 and never removes a PASS.
  - Decisiveness at seed SD 0.03: FAIL_MONO world 0.996 FAIL_MONO, FAIL_CROSS world 0.905 FAIL_CROSS, PASS world 0.979 PASS, surface world 1.000 FAIL_CROSS "surface", near-line world decisive 0.607; prior-weighted P(decisive) 0.8917 (SD 0.03) and 0.9118 (SD 0.06).
  - Halving the prompts is not simulated in v2; the cross cells are already at the measured pool's size.

- **Multiplicity.** Four decision lines (MONO, CROSS, BIND, SEM) in one
  conjunctive rule; I1 and DEC only route failures to labels. The 200M read and
  every pathway read are descriptive. No line is tested twice.
- **Leakage and contamination.**
  - The instrument comes from NTREX-128's test half (documents split by the
    registered hash); decoys come from both halves; every instrument sentence is
    deduplicated against every training stream and the curriculum key pool by
    exact match and character 5-gram MinHash (Jaccard at least 0.5); matches are
    removed from training, never from the instrument.
  - The English side of NTREX-128 is WMT19 news, which Common Crawl may contain;
    dedup is the control, and the counts are reported.
  - Codes are reserved; digits are excluded from keys and filler; each target
    code occurs only in its queried fact (manifest assertion).
  - The tokenizer is never trained on instrument text; the curriculum never
    contains a cross-lingual query.
  - Prompt manifests are sealed before J1; every read is logged against the
    registered read list; an unlisted read is reported as a leak.
- **Assumption checks.** Per-cell rates, the sentence-cluster design effect and
  B-SURF's values are reported. A cell under 150 eligible prompts is dropped
  before any model exists.
- **Missing data.** A diverged seed counts as BELOW on every line; an incomplete
  trunk counts as UNRESOLVED.
- **Red flags guarded.** No post-hoc bin choice (the bins follow from the
  receptive field). No metric switching (the EM lines are verbatim). No optional
  stopping beyond the registered futility rule. B-SURF's thresholds were set
  after P1's CPU measurement on NTREX and before any model exists; the
  disclosure is in the registration.

## Compute and Reproducibility

Image lineage: the measured throughput (Slurm 359) used
`127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`
(`cotcodec-research:0b3ecef0-architecture`, image ID `sha256:38044666...`;
torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention and fla-core
0.5.2, triton 3.6.0, tilelang 0.1.13; the tilelang path is the workaround for fla
#640). The G1 image is built from the harness commit by the project's CPU build
job and pinned by digest before J1. No new dependency is needed.

Launch path (dry run, then test-only, then submit; one GPU per job; none of
these manifests exists yet):

```bash
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v2-j1.yaml --dry-run
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v2-j1.yaml --test-only
uv run --locked python scripts/submit_docker_research_job.py infra/slurm/host-single-node/e7-equivariant-writes-g1-v2-j1.yaml
```

The submitter wraps `sbatch infra/slurm/host-single-node/docker-research.sbatch`.
The same three steps follow for J2, J3, T42, T43 and T44. Every executable step
also runs as an orx experiment node through `uv run --locked python
scripts/orx_run.py` over a committed `experiments/orx/node.yaml`: `kind:
cpu-doctor` for the intervention table, the analysis pipeline and the builder
checks, and `kind: slurm-manifest` for the GPU jobs.

Machine fields: seeds: [42, 43, 44]; gpu_hours: 8. The caps sum to 7.767 GPU-h
under D22. This is the gate's compute, separate from the gauntlet's 0.3 GPU-h
reviewer budget.

Caps and arithmetic (S2v2, `compute/repair-d68/cost-model-v2.json`; base 282,501.4
tokens/s; high case: training x 1.5, evaluation at 1.5 x the base, start-up 300
s, compile 300 s, trunk checkpoints 110 s; cap = ceil(1.2 x high / 60) minutes):
- J1: 300 smoke steps and 1,800 probe step-equivalents (3 repeats x 100 steps x
  (1 + 3 + 2)) at 32,768 tokens per step, plus 150M sweep tokens: 218.8M
  token-equivalents x 1.5 / 282,501.4 + 600 = 1,761.8 s; cap ceil(35.24) = 36 min
  (0.600 GPU-h).
- J2: 3.28M x 1.5 / 282,501.4 + 600 = 617.4 s; cap 13 min (0.217).
- J3: 50M x 1.5 / 282,501.4 + 600 = 865.5 s; cap 18 min (0.300).
- Each trunk: 1.04B x 1.5 / 282,501.4 + 165.15M / (1.5 x 282,501.4) + 710 =
  6,621.8 s; cap ceil(132.44) = 133 min (2.217).
- Sum: 36 + 13 + 18 + 3 x 133 = 466 min = 7.767 GPU-h <= 8.0. The one allowed
  resubmission (J2) would make it 7.984. No other resubmission is allowed; a
  training crash resumes inside the same cap.
- Evaluation tokens per seed, 165.15M: primary reads 45.42M (B1, B2, B3 and
  decoys at 200M and 1B); noise 29.5M; emergence 49.5M; REACH 0.57M; ISO 0.38M;
  RELAY_BLOCK on B3 14.75M; D1 on B3 14.75M; SPAN_CUT on B2 2.95M; B1 pathway
  reads 3.5M; CSLS, writes and probes 10M.
- Central total 4.90 GPU-h (three trunks at 1.48 each); 1.95 GPU-h if futility
  fires after T42; one seed would cost 1.95 central and 3.33 in caps, against the
  dossier's 2.5.
- A trunk fits its cap only if J1 measures at least 179,940 tokens/s (63.7% of
  the eager measurement); otherwise INFEASIBLE_THROUGHPUT and a new registration.

Checkpoints and resume:
- Atomic checkpoints every 15 minutes to persistent storage, and named
  checkpoints at 100M, 160M, 200M (branch), 400M, 800M, 960M, 980M and 1B.
- A SIGUSR1 handler writes a checkpoint. J2 checks that a fresh job resumed from
  step 200 matches the uninterrupted continuation (identical batch hash and step
  counts; loss within max(2e-3, 3 x the measured run-to-run difference)).
- At most two resumes per trunk, inside its cap.

Artifacts (public repository): configs, the tokenizer's vocabulary hash, the
data manifest (ids, revisions, hashes); prompt manifests (ids, offsets, hashes,
B-SURF record); per-prompt predictions (EM_t, eight log-probabilities, per-digit
correctness, copy flag, decoy outcomes); per-seed line tables, REACH and ISO
logit differences, pathway reads, diagnostics, LR sweep losses, throughput and
resume reports, realized GPU-hours from `scontrol`, and the read ledger.
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
    under CC BY-SA 4.0 with attribution, as a separate artifact. The repair's
    CPU check P1 read NTREX-128 from a local copy in the session scratchpad
    (fetched by a wave-1 refuter at commit 468c6b69; file hashes recorded in
    `instrument-pool-v2.json`) and wrote counts and rates only.
  - Downloads are recorded under D1 with source, revision, size and SHA-256.
- **Code provenance.** 2610.06750's repository has no licence, so its
  auxiliary pass is reimplemented from the paper, never vendored into this
  MIT repository.
- **Untrusted code.** None. The harness is reviewed project code (D7);
  outputs are digit strings scored by comparison.
- **Host.** No host job while a Q2 job runs or is pending. The only host
  action of this gauntlet run is the open-weight reviewer's lane job; the
  repair made no host contact. No host address or credential appears in this
  repository.
- **Monitorability.** Nothing is deployed and no policy is trained. Every
  read is logged.
- **Red lines.** None touched. Safety verdict PASS.

## Negative-Result Value

| Verdict | What it says (at 134M, 1B tokens, W = 512) | What it closes or opens |
|---|---|---|
| PASS | The recurrent state carries facts across at least 1,600 tokens in-language (at least 60%) and across scripts (at least 15%, bound to the key and beyond surface form), reliably over seeds | A gauntlet for E7's phase-1 grid (a guardrail design, the 2610.06750 baseline, the SWA plus sinks baseline, D24 admission). The "relay-dominated" flag tells the grid which writes its loss must target |
| FAIL_CROSS, state-specific | At the same distance, attention matches across scripts and the state does not | The gap a translation-equivariant write loss would target, measured cleanly; a new gauntlet decides between the 2610.06750 LoRA port and a grid read on B1 and B2. Publishable as "the state stores surface form" |
| FAIL_CROSS, decay | The state matches across scripts at short range but loses it by 1,600 | A retention or curriculum successor, not a write-alignment one |
| FAIL_CROSS, representational | No cross-script matching even through attention in-window, with half the bitext co-present | Closes the from-scratch path at this scale; the dossier's port applies |
| FAIL_CROSS, surface | Cross-script recall is explained by what a surface-twin decoy also retrieves | An instrument result: the state keys on surface form; the port |
| FAIL_MONO (retention, no short-range state recall, futility) | The state does not carry facts across 1,600 tokens even in-language | Closes the from-scratch path at this configuration; retention points to a chrono-style initialization or curriculum successor (with SWAX's window caveat) |
| LOTTERY | Seeds disagree across a line | Any three-seed arm comparison on this instrument; a lock-in design (2609.16183) under a new id |
| INCONCLUSIVE | A line unresolved | Nothing; the intervals size a successor |
| INSTRUMENT_INVALID | MONO fails and the model recalls under half of the facts inside its own window | A fix under a new id; no statement about the state |
| HARNESS_INVALID | REACH, ISO, B-SURF or a manifest assertion fails | A code fix under a new id; no statement about the model |
| INFEASIBLE_THROUGHPUT | J1 measures below 179,940 tokens/s | A re-priced registration |

The most likely outcomes, by the owner's prior, are FAIL_CROSS (about 0.4;
representational and state-specific about equally likely now) and FAIL_MONO
(about 0.2). Each is a cheap negative with a measured reason and a named
successor.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex (4 of 5 OpenAlex calls returned HTTP 429), the OpenReview search API, the cached ACL Anthology bibliography and the OpenAlex works API reachable from the Mac; wave 1's 97 + 15 and this run's 37 counted queries logged with returned ids and raw-output digests (`query-log.json`, `query-log-run2.json`); cutoff 2026-10-10; degraded coverage recorded (no Semantic Scholar, arXiv API, patents, social media, Chinese-language venues; OpenReview note pages behind a challenge; citation graph degraded) (`doctors/source.json`) | Semantic Scholar forward citations for 2610.06750, 2509.24552 and 2402.19427 through the host relay when the host is free |
| Citation | PASS | Claim registry C01 to C54 with locators, dates and read status; every cited URL snapshotted with its HTTP status and, for arXiv, its version history; OpenReview rows abstract-only (UNVERIFIABLE_ACCESS for PDFs); C13 first-party and preliminary; the closest priors re-read in full in this run (`doctors/citation.json`) | Read the ICLR 2027 PDFs (2610.06750's OpenReview version, CHARTA, MAPP, 5MKfXl078n, UUldzWxIL4) when a person can pass the challenge |
| Novelty | FAIL | No direct prior under the recorded coverage; the gate claims no novelty and is scored as a precondition; Griffin, MLNeedle, OneRuler and the other priors read and credited; this run's blind critic and novelty refuter have not run (`doctors/novelty.json`) | Run one blind critic per packet (2610.06750; SWAX) and the novelty refuter; 43 queries remain, at least 30 reserved |
| Design | FAIL | Interventions, structural checks, lines, verdict order, surface controls and pathway reads specified; S3v2 proves the checks' exactness on a reference of the module graph; P1 measures the pool and the surface controls; S1v2 gives operating characteristics under the registered estimator. But every outcome distribution is assumed, the surface controls use character proxies, and no harness exists (`doctors/design.json`) | Write the harness; run the cpu-doctor node (intervention table on the harness's own module graph, analysis recovery, builder checks with the real tokenizer) |
| Compute | FAIL | No real model loop, adapter, manifest, container smoke or Slurm dry run; SWA-512 throughput on real data unmeasured; 1.04B tokens of data not on the host; caps 7.767 GPU-h with every job's arithmetic (`doctors/compute.json`, `compute/attestations-not-run.md`) | Fetch data under D1 when the host is free; write the harness and the J1 manifest; dry run and test-only |
| Safety | PASS | Public licensed data with text kept out of the repository (P1 writes counts only); NC, gated and customer data excluded; the unlicensed code reimplemented, not vendored; no untrusted code; no host contact by the repair (`doctors/safety.json`) | none |

Protocols followed:
- Citation: the ARS claim-verification protocol (claim registry, locators,
  verdicts, UNVERIFIABLE_ACCESS).
- Design: the vendored K-Dense `experimental-design` and `statistical-power`
  skills (design before data, decisiveness by simulation under the registered
  estimator).
- Evaluation: K-Dense `statistical-analysis` (clustered intervals).
- Novelty: K-Dense `literature-review` (PRISMA counts in the Novelty Ledger).
- The integrity gate (seven failure modes) is answered in the registration.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (this run's reviewers run after the blind critic and the refute-first triad; wave 1's reviewer 1, claude-opus-5-5, scored 51 and is recorded in the gauntlet file)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only while no Q2 job is running or pending; wave 1's reviewer 2, qwen3.6-35b-a3b, scored 51 re-checked)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

This run's reviewers have not scored. Wave 1's scores (reviewer 1 / reviewer 2)
are in the gauntlet record and below; they scored the wave-1 package, not this
one.

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed (wave 1: 5 / 7); precondition framing, sub-labels pick successors |
| Primary-source evidence | 0 | 0 | not yet reviewed (wave 1: 6 / 5); registry C01 to C54, priors re-read in full |
| Defensible novelty delta | 0 | 0 | not yet reviewed (wave 1: 4 / 5); no novelty claimed; priors credited |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed (wave 1: 5 / 5); P0 to P5 with falsifiers |
| Controls and causal identification | 0 | 0 | not yet reviewed (wave 1: 3 / 5); REACH and ISO exact (S3v2), SEM and B-SURF (P1), distance-matched sub-labels |
| Evaluation and statistics | 0 | 0 | not yet reviewed (wave 1: 5 / 5); S1v2 under the registered estimator |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed (wave 1: 4 / 5); caps 7.767 GPU-h with arithmetic |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed (wave 1: 5 / 2); no harness, no manifest |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed (wave 1: 9 / 7) |
| Independent adversarial review quality | 0 | 0 | not yet reviewed (wave 1: 5 / 5); no signed reviews possible (D24) |
| **Total** | **0** | **0** | Lower total is authoritative |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| legacy waves 1-5 (2026-09-01) | not comparable | Phase 0 on a frozen hybrid; 57M grid at 200M tokens; doctor executable only on synthetic objects | Contract v5, phase-0 CPU doctor | Archived under legacy/; phase 0 pre-answered by 2609.04434 and 2609.33093 |
| dossier (2026-10-06) | not scored | Phase 0 pre-answered; output language rides the state; G1 at floor unestablished | Corrected question; G1 floor gate at 134M, 1B tokens | Recorded in the dossier, section 16 |
| new gauntlet, synthesis (2026-10-10) | not scored | "Beyond-window" is not state-only (reach 1,560); chance is 1/8; one seed | B3 bin; within-model decomposition with CUT and ABLATION; BIND; three seeds with LOTTERY and futility; NTREX-128; caps 7.733 GPU-h; S1, S2, S3 | Went to wave 1 |
| 1 (2026-10-10) | 51 (51 / 51 re-checked) | Identification: the CUT premise (a single reset leaves SWA relay paths, so a state-carrying model can read INSTRUMENT_INVALID); then the CROSS/BIND surface confound, a non-erasing ablation, a distance-confounded sub-label; novelty coverage (Griffin; MLNeedle and OneRuler unread) | No honest exit; triad 3 of 3 refuted; D68: one repair and a fresh run | Recorded, row hash `34901a11...` |
| D68 repair (2026-10-10) | not scored | as wave 1 | Registration v2: REACH and ISO as exact deterministic checks (S3v2), the verdict re-ordered, D1 and RELAY_BLOCK as pathway reads, the 4-gram filter, sliding-block distractors, surface-twin decoys, SEM and B-SURF (P1), cross-script CROSS, distance-matched sub-labels, half the bitext co-present, S1v2 under the registered estimator, caps 7.767 GPU-h with arithmetic; novelty reframed as a precondition, priors credited and read | Awaiting this run's blind critic, refuters and reviewers |

## Deterministic Doctor Output

Verbatim output of `uv run python scripts/research_direction_doctor.py
program/proposals/2026-10-10-e7-equivariant-writes-g1.md` (exit 1) on the bundle
as committed, also stored as
`evidence/2026-10-10-e7-equivariant-writes-g1/doctors/research-direction-doctor-output.json`.

Readings the doctor does not make for itself:
- "All declared budgets must be positive" comes from parsing the declared
  `gpu_hours=0.3` as an integer. The declared budget is honest and was not
  rounded up to pass.
- The doctor applies no 79 cap here, because its executable-pilot check is
  textual. By the gauntlet rule's cap table this proposal is capped at 79 (no
  executable pilot) and at 89 (no independent provider-distinct signed review),
  and at 74 until this run's blind critic and novelty refuter have run (Novelty
  doctor FAIL). It cannot reach 100 without D24's trust store.
- The doctor counts OpenReview snapshots as resolved because those pages return
  HTTP 200, but their bodies are a browser challenge.

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
    "allUrls": 55,
    "recognizedPrimaryUrls": 55
  },
  "status": "FAIL"
}
```
