# Q3 dense headroom pre-check (q3-dense-headroom-precheck-v1)

Status: DRAFT, not frozen. Built under program decision D26 on branch
`stage0/q3-dense-precheck`. No GPU job of this experiment runs before this file
is frozen in `program/preregistrations/ledger.jsonl`; every job verifies this
file's digest against its ledger row at start-up and refuses code whose
SHA-256 differs from the table below. The design decisions at the end are
left to the program owner.

## Purpose and claim level

Program decision D26 ended `q3-k1-localization-screen-v2` at an honest
gauntlet exit (wave 1 score 45, refute-first triad 3 of 3 refuted;
`program/gauntlet/2026-10-07-q3-k1-localization-screen-v2.jsonl`). The
defects are in the design inherited from `q3-k1-localization-screen-v1`, not in
its engineering:

- NEGATIVE needs 20 points of dense headroom over random (H1 at least 20), and
  K1 v1's smoke (Slurm 452) measured dense block top-k recall of 26.45 (hs) and
  26.08 (mp) against 12.48 for random on 20 development units, about 14 points
  pooled over the MN and CX legs
  (`program/evidence/2026-10-07/q3-k1/smoke-452/phase-0a-k1-receipt.json`).
  The MN and CX split of those units was never computed.
- A selector flat on both non-literal legs falls inside NEGATIVE
  (xi = −Delta_T, xi_rel = 0): there is no non-literal adequacy floor.
- GO is confounded: Belebele's translation rules make a translated question
  follow the passage's proper nouns, dates and units of measure (Belebele,
  arXiv 2308.16884, Appendix A.5.2, https://arxiv.org/abs/2308.16884, read
  2026-10-07), so a same-language (MN) question carries literal anchors into
  its passage that a cross-script (CX) question cannot.
- Top-256 recall is a thresholded function of block scores, so equal,
  language-agnostic selector noise can give xi above 0 when the MN and CX
  needle-score shapes differ (identification refuter, seeded illustration);
  K1's pre-freeze simulations assumed the null instead of measuring it.
- "Cross-script" is collinear with scripts unseen in indexer training and with
  tokenizer fertility.

This experiment measures, densely (no indexer is trained or read), what any K1
v3 needs to know first, on the development partition of the existing K1 bundle
only, on Qwen3-0.6B-Base and the registered fallback Qwen3.5-4B-Base:

1. dense block top-k recall headroom over random (H1) on the MN, CX and ML
   (literal) legs, and the MN minus CX gap of the dense target;
2. dense multiple-choice accuracy (H2a) and needle-present minus needle-absent
   accuracy (H2b);
3. a candidate non-literal adequacy floor;
4. the share of development questions whose wording shares proper nouns,
   dates or numbers with the passage (entity anchors), the H1 and H2 numbers on
   the entity-controlled subset, and what a purely literal selector would read
   under K1's statistics;
5. what a language-agnostic noisy copy of the dense target would read under
   K1's statistics (a block-score null on the measured score shapes);
6. recall headroom by tokenizer fertility.

It is measurement-only. Its decisions say which K1 v3 designs the measured
headroom supports and on which base; they never say whether an indexer loses
more cross-script recall than its target. Nothing here is a K1 result,
positive or negative.

## Identity

Code. The jobs run from the source baked into an image built by
`infra/slurm/host-single-node/build-architecture-image.sbatch` from a fresh
clean clone of the commit that holds this file's ledger row. The entry point
refuses to start unless every file it runs has the SHA-256 tabled here; the
manifest filler refuses unless every tabled file has this digest in the
checkout and at the image's commit. The last seven rows are files tabled by
frozen registrations, imported unchanged: `harness/sparse_indexer_bank.py` by
`q3-k1-throughput-probe-v1`, the others by `q3-k1-localization-screen-v1`
(same SHA-256 as in those registrations).

| File | SHA-256 |
|---|---|
| scripts/run_dense_headroom_precheck.py | cb1eb03eeae6b86a4e4ae16abe570285ce4ca6b1f887a56108a4e958c026317a |
| harness/dense_headroom_data.py | 614f4b4cbfcce88f1b29513987ce3526a5a452f80048723210b8c1558d745ae8 |
| harness/dense_headroom_stats.py | 5b036b99c1edde01fb4bf0826e3656c1071887a34b20bcc80fc410fcfff1cf8d |
| harness/dense_headroom_torch.py | 6dd8ff1f9cbcbd7d3faaecd1c94ab7908c12e2aea16b480bc56735e4b27547be |
| scripts/run_dense_headroom_precheck_doctor.py | 57096736b09c36306f032317d46fb44f48a16d741ce674dc340cefcafd1eee30 |
| scripts/fill_dense_headroom_precheck_manifests.py | 35ea7d9ff969eb2ea942786adef789b219f058fa781bc6b18de7dc19f2016bdd |
| scripts/summarise_dense_headroom_precheck.py | 2f6210158c586d94a2ea1ccc480f8d42ce957d511a74b248f08883a96fd1d364 |
| harness/sparse_indexer_torch.py | f21301a49634af07d5ae0385c34011400c83af15b984a96238dc6fe1d4ee9457 |
| harness/sparse_indexer_bank.py | e96653eb3eb5b9876201347c2fa8d452efc3ebb1043a516ac03c366ff8b89f88 |
| harness/sparse_indexer_k1_runtime.py | 6fbddc91b6f7224f909901edb82278a68f68a208b558526c1a778ec9da6812fd |
| harness/sparse_indexer_k1_marker.py | 7bc69aa4d27a7d6de92f69a2f7b8e71d98b32101a2f34709fbaef2bdf84c3f1a |
| harness/sparse_indexer_k1_stats.py | b9949b4b24502ad30d576938e88cd39d0fdcfc2be90eeedf52a68c76430f36b8 |
| harness/sparse_indexer_data.py | 8b180e1ca0ba67d29587e3ffc5f5e46720376de6d1a52348f82b8789ab929faa |
| harness/translation_supervised_indexer.py | dee5318d254d962380e2de051eed227a97db10bfaa40eb0c12467e9a289e0cd5 |

Bundle. `k1-bundle-v1.json`, schema `cotcodec-k1-bundle-v1`, SHA-256
`919d016b87ad862f8f156e9537c9a39e2864dab0e6c605307d100d25a199dd2d`,
278,818,734 bytes, built and registered by `q3-k1-localization-screen-v1`
(section "Bundle digest"), mounted read-only as the study artifact. Its
tokens were produced by the Qwen3-0.6B-Base tokenizer
(`tokenizer.json` SHA-256
`c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`); the entry
point refuses any other bundle or source tokenizer.

Models (receipts on the host, read 2026-10-07):

| Lane | Model, revision | Receipt SHA-256 | Artifact root | tokenizer.json | Layers with softmax attention |
|---|---|---|---|---|---|
| qwen3-0.6b-base | Qwen/Qwen3-0.6B-Base `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` (apache-2.0, https://huggingface.co/Qwen/Qwen3-0.6B-Base) | e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df | 7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0 | c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539 | all 28 (16 query, 8 key-value heads, head dimension 128) |
| qwen3.5-4b-base | Qwen/Qwen3.5-4B-Base `1001bb4d826a52d1f399e183466143f4da7b741b` (apache-2.0, https://huggingface.co/Qwen/Qwen3.5-4B-Base) | 253a14185bcff0762b8a43944635a550055d3346fe16c416d6bcfe4460793cfe | c7fbfd6bd1c73b9a0080decf794f5e4333c955f2704591affc61b0a9ac850e42 | fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927 | the 8 full-attention layers 3, 7, ..., 31 of 32 (16 query, 4 key-value heads, head dimension 256, rotary on 64 dimensions); the other 24 are gated-delta layers |

The Qwen3.5-4B-Base checkpoint is stored as `Qwen3_5ForConditionalGeneration`;
the text model is loaded with `AutoModelForCausalLM` (`Qwen3_5ForCausalLM`,
vision and multi-token-prediction weights ignored). On a tiny checkpoint saved
the same way, the loaded text model gives logits identical to the full model's
(checked while building this design). Its gated-delta layers run
flash-linear-attention 0.5.2's Triton kernels from the pinned image (library
code, compiled by Triton at first use; https://github.com/fla-org/flash-linear-attention).

## Data (development partition only)

The 488 Belebele passages are split by link with `split_passage_ids(seed=42)`
(development 122, audit 122, primary 244 links; K1 v1 registration). This
experiment reads only the development partition: every prompt, context and
query it uses must carry a development link, or the job exits 3
(`harness.dense_headroom_data.derive_dev_artifact`, the K1 partition guard
`assert_reads_within`). The audit and primary partitions are never read. The
job decodes the bundle's arrays once and keeps only development rows.

The K1 bundle holds development prompts for the 20 development questions that
K1 v1 selected for its pre-check (about 19 passage clusters), crossed with the
14 cross-script pairs (needle X with an English question and the reverse, X in
ja, ko, bn, ta, el, he, ka):

| Role | Prompts | Use |
|---|---|---|
| dev (MN and CX) | 560 (280 families) | selection (H1) and multiple choice (H2a; MN accuracy descriptive) |
| dev-absent | 280 | multiple choice, needle-absent twin of each CX prompt (H2b) |
| dev-nohaystack | 280 | multiple choice, passage plus question without haystack (reference) |
| dev-literal (ML), built here | 160 (20 questions x 8 needle languages) | selection (H1 on ML, the null's V1 adequacy) |

Development literal prompts are built from the development needles with the K1
builder's rule: the needle passage is split with `split_sentences` and the
sentence at index SHA-256("ml-sentence|L|link|q") modulo the sentence count
becomes the query ("\n\n" + sentence + "\n"), in the same context as the MN
prompt of that needle language. The sentence must occur verbatim in the
needle.

Re-tokenization (Qwen3.5-4B-Base only; its vocabulary differs). Every context
is decoded to bytes with the bundle's tokenizer segment by segment (haystack
before the needle, the needle, the rest) through the byte-level table, and
re-encoded with the 4B tokenizer; the needle span is the re-encoded needle
segment exactly, the sink is the 4B tokenizer's `<|endoftext|>`, and queries
and options are re-encoded the same way. Only the end of the haystack, where
the K1 builder cut it, may end inside a character; at most three trailing
bytes of an incomplete sequence are dropped there (counted). Contexts are then
shorter than 8,192 tokens, so the budget is matched by fraction (Selectors).
The development artifact (all inputs, both tokenizations' indices, the text
features) is written to the run directory and its SHA-256 goes in the
receipt; deriving it twice gives the same bytes.

Unique evaluation units (context, query) are 1,160 per lane, in four stages
run in this order: A main (440 units: 280 CX, 160 MN, MN shared across the
seven English-needle pairs), B needle absent (280), C literal (160), D no
haystack (280). Selection is read on 600 units, multiple choice on 1,000.

## Selectors

At every softmax-attention layer the question rows' post-norm, post-RoPE
queries and all keys are captured from the bf16 SDPA forward (K1 v1's
`CaptureSession`) and exact probabilities are recomputed in fp32 per row. A
block is complete for row i when 4b + 3 is at most i. Recall of a selector on
a prompt is K1 v1's: per layer, the mean over question rows of the selected
needle tokens over the needle tokens; then the mean over the lane's attention
layers.

Matched budget: k = floor(floor(L x 1,024 / 8,192) / 4) blocks for a context
of L tokens, which is K1's 256 blocks (1,024 tokens, 12.5 percent) at 8,192
tokens and keeps 12.5 percent for a re-tokenized context.

- T:hs, T:mp: top-k complete blocks of K1 v1's targets (hs head-sum block mass,
  mp QSA Eq. 17), lower block index first on ties; T:hm descriptive.
- U, Uk: union over heads of each head's top 4k and top max(1, 4k/16) tokens
  (1,024 and 64 at 8,192 tokens); descriptive references.
- rand: the analytic expectation of a uniformly random choice of k complete
  blocks.
- LEX, the literal selector: a block's score is the number of its context
  tokens (sink excluded) that are content tokens of the question; content
  tokens are those that are not among the 100 most frequent token ids of the
  needle language's development haystack (ties to the lower id) and do not
  decode on their own to text without a letter or digit. Recall is the exact
  expectation under uniformly random tie-breaking at the k-th score.
  Layer-independent.
- N:T:sigma:seed, the block-score null: natural-log block scores of target T
  (hs, mp; floored at 1e-30) plus sigma times standard normal noise, sigma in
  {0.25, 0.5, 1, 2}, seeds 42, 43, 44; the noise of a (seed, unit, layer) comes
  from a generator seeded with SHA-256 of those three, so its law is identical
  on every leg. It is the identification refuter's null on the measured score
  shapes: a copy of the target with language-agnostic error.
- T:hs@fixed, T:mp@fixed, rand@fixed: the K1 budget of 256 blocks whatever L
  (equal to the matched budget at 8,192 tokens); descriptive.

Multiple choice is K1 v1's acc_norm: each of the four options scored as a
continuation of the full prompt by its summed token log-probability over its
UTF-8 byte length, an exact tie to the lowest option index. The prompt's cache
is cropped back between options for Qwen3 (K1 v1's code) and deep-copied per
option for Qwen3.5, whose recurrent state cannot be cropped; on tiny models
both equal a no-cache forward to 1.5e-6.

## Metrics and statistics

Intervals are 99 percent percentile passage-cluster bootstraps (B = 10,000,
NumPy seed 42, macro over pairs inside each replicate;
`harness.sparse_indexer_k1_stats.macro_mean_interval`), K1 v1's construction
for its dense gates. A subset with fewer than 3 passage clusters gets a point
estimate only, marked not evaluable.

- H1 on leg c (MN, CX, ML) for target T: macro over pairs (the 14 cross-script
  pairs; the 8 needle languages for ML) of the mean of R_T(c) − R_rand(c). The
  registered H1 statistic is K1 v1's: H1_CX = the larger of the hs and mp
  points, with that target's interval (the chosen target).
- Delta_T: macro over pairs of the family mean of R_T(MN) − R_T(CX).
- H2a: CX accuracy, macro over the 14 pairs. H2b: needle-present minus
  needle-absent CX accuracy on the 280 paired cells, plain mean with a cluster
  bootstrap. MN, needle-absent and no-haystack accuracy are descriptive.
- K1 v1's development pre-step rule (PROCEED_TO_K1 when H1_CX is at least 10,
  the H2a lower bound is above 30, and the H2b lower bound is above 0 with a
  point of at least 5) is reported unchanged, for continuity.
- Entity anchors (model-free, before any GPU work): a development question is
  anchored when its English wording contains a word that starts with an
  uppercase letter (not the first word, not "I"), or a digit run, that also
  occurs in the English passage (possessive "'s" removed). Belebele's
  translation rules keep these strings with the passage in every language, so
  the English flag marks the question in all languages. Reported: the anchored
  share with a Wilson 95 percent interval; H1 (MN, CX, ML), Delta_T, H2a and
  H2b on the entity-controlled (unanchored) and the anchored subsets; per
  language the digit anchors; per pair and leg the share of the query's
  content tokens that occur in the needle.
- The literal selector under K1's statistics: xi and xi_rel (K1 v1's
  definitions and combined interval, with LEX in the indexer's place and one
  "seed") against each target, on all families, the controlled and the
  anchored subsets. A LEX xi_rel above 0 is what a selector that matches only
  shared tokens reads with no cross-lingual matching error at all.
- The block-score null under K1's statistics: for each target and sigma, xi
  and xi_rel with the seed-plus-cluster interval (three seeds), the English ML
  adequacy of K1 v1's V1 rule (null recall at least the target's minus 5
  points at every seed), and its G(MN) on controlled families.
- Retention G of selector X against target T: macro over pairs of
  (R_X − R_rand) / (R_T − R_rand) on pair means, not evaluable when a pair's
  point target headroom is 1 point or less; replicates floor the denominator
  at 1 point (K1 v1's xi_rel rule).
- Fertility: per language and question, tokens of the passage (and question)
  over tokens of the parallel English one, in the lane's tokenizer; per
  language the share of needles longer than the matched budget; Spearman
  correlations over the seven held-out languages between fertility and the
  chosen target's CX headroom (needle side and query side) and MN headroom.
- K1 smoke reproduction (Qwen3-0.6B-Base lane only): the 20 development units
  smoke 452 read (K1 v1's unit order) recomputed; T:hs, T:mp, T:hm and rand
  must each be within 0.5 points of the smoke receipt (26.45, 26.08, 26.27,
  12.48), U and Uk are reported.
- Integrity: every planned unit evaluated exactly once, every selection score
  finite, no selection above 4 max(k, 256) + 3 tokens; otherwise exit 3 and no
  read.

## Decision rules

Per lane (`harness.dense_headroom_stats.classify_lane`):

- h2_status: PASS when K1 v1's H2a and H2b rules hold; POINT_ONLY when both
  points meet the thresholds (H2a above 30, H2b at least 5) but a bound does
  not; FAIL otherwise.
- lane_class:
  - INVALID: the K1 smoke reproduction failed (0.6B lane); the lane is not
    read further.
  - NEGATIVE_CAPABLE: H1_CX at least 20 with its 99 percent lower bound at
    least 10, and h2_status not FAIL. A K1 v3 with a NEGATIVE region may be
    designed on this base.
  - GO_ONLY_CAPABLE: H1_CX at least 10, h2_status not FAIL, and not
    NEGATIVE_CAPABLE. A K1 v3 on this base may register GO only; it cannot
    register a NEGATIVE (the inherited H1 at least 20 rule).
  - NOT_VIABLE: otherwise. No K1 v3 on this base.
- anchor_confound: PRESENT when the literal selector's xi_rel point on all
  families is at least 0.10 (K1 v1's NEGATIVE limit) for either target;
  ABSENT otherwise; NOT_EVALUABLE when xi_rel is not evaluable.
- entity_control: SUFFICIENT when at least 30 percent of the questions are
  unanchored and on them the literal selector's xi_rel point is below 0.10 for
  both targets; INSUFFICIENT otherwise; NOT_EVALUABLE when not evaluable.
- null_calibration per target: CENTRED when, at every sigma whose null passes
  V1 at every seed, the seed-mean |xi| is at most 2 points and |xi_rel| at most
  0.10; NOT_CENTRED otherwise; NOT_EVALUABLE when no sigma passes V1 or xi_rel
  is not evaluable at one that does.
- floor_candidate (an indexer's 99 percent lower bound of G(MN) on
  entity-controlled families at least 0.5, for the chosen target): VIABLE when
  the target's controlled MN headroom is at least 10 points, the literal
  selector's controlled G(MN) is below 0.5, and some sigma whose null passes V1
  has a controlled G(MN) of at least 0.5; NOT_VIABLE otherwise (reasons
  listed); NOT_EVALUABLE when the controlled MN headroom is not evaluable.
- fertility_association: STRONG when |Spearman| between needle fertility and
  CX headroom over the seven held-out languages is at least 0.75, WEAK
  otherwise (descriptive; with seven languages it cannot separate fertility
  from script or from being unseen in indexer training).

Combined read of the two lanes
(`scripts/summarise_dense_headroom_precheck.py`,
`harness.dense_headroom_stats.combined_recommendation`), applied once both lane
receipts exist:

- Base: the first lane in the order Qwen3-0.6B-Base, Qwen3.5-4B-Base that is
  NEGATIVE_CAPABLE (design NEGATIVE_CAPABLE_V3); otherwise the first that is
  GO_ONLY_CAPABLE (design GO_ONLY_V3); otherwise NO_K1_V3: no K1 v3 is
  designed on these bases and Q3's K1 line is reported as stopped for
  insufficient dense headroom (a pre-result, not a negative). A lane without a
  completed receipt makes the read INCOMPLETE.
- Requirements of any K1 v3, always: a seen-script cross-script condition
  (D26; the bundle's development partition has none, so it is not measured
  here), a new experiment id and the research gauntlet (D26). From the chosen
  base's flags: an entity-controlled MN leg unless anchor_confound is ABSENT;
  anchor masking or an overlap covariate unless entity_control is SUFFICIENT;
  a null-calibrated statistic unless null_calibration is CENTRED for both
  targets; the floor as registered here when floor_candidate is VIABLE,
  otherwise a redesigned floor.

## Seeds, sample sizes and sensitivity

- Seeds 42, 43, 44 seed the block-score null only (the only randomness in the
  jobs). The bootstrap uses NumPy seed 42 (K1 v1). Dense recall, accuracy and
  the literal selector are deterministic functions of the inputs (the 0.6B
  lane runs with deterministic torch kernels; the 4B lane warns instead of
  raising for an op without a deterministic kernel, decision 9).
- About 19 passage clusters carry every statistic; the subsets fewer. The
  pre-check's precision is therefore limited and is reported, never inferred
  from its decisions: K1 v1's simulations found that its development pre-step
  passes H2a with probability 0.46 to 0.76 at a true CX accuracy of 45 percent
  and H2b with probability 0.37 to 0.43 at a true difference of 10 points (K1
  v1 registration, "Seeds, sample sizes and sensitivity"). That is why H2 here
  has the POINT_ONLY status and gates only on FAIL.
- The NEGATIVE_CAPABLE rule asks for the lower bound at least 10 so that a
  development point at or just above 20 that is mostly cluster noise does not
  open a NEGATIVE design; the audit-partition read of any K1 v3 re-applies its
  own H1 rule.
- The controlled subset's size is unknown before the run; its statistics are
  descriptive, and entity_control asks for at least 30 percent of questions
  (about 69 of K1's 230 audit questions) before an entity-controlled design is
  called sufficient.

## Compute

| Job | GPUs x minutes | Cap (GPU-h) |
|---|---|---|
| Qwen3-0.6B-Base lane | 1 x 9 | 0.15 |
| Qwen3.5-4B-Base lane | 1 x 21 | 0.35 |
| Total | | 0.50 |

The total is the sum of the registered caps, D22's counting rule, and equals
D26's ceiling of 0.5 GPU-h. Expected use, from K1 v1's smoke timings and the
model sizes, is about 4 minutes for the 0.6B lane and about 11 for the 4B lane
(both include start-up: bundle read and artifact derivation, model load, and
on 4B the first-use Triton compilation); these are estimates, not
measurements. A lane interrupted by its time-limit signal saves its completed
chunks and exits 75; one continuation in the same run root
(`resume_subpath` `dense-precheck/checkpoints`) may use the lane's remaining
minutes (its limit minus the minutes used, rounded up, minus one) if at least
3 remain; the filler fills it at most once. A lane that still has no receipt
is INCOMPLETE; any budget amendment would be recorded in
`program/decisions.md` before the other lane's read is opened and could
change only minutes and GPU-hours. A CPU doctor run in the image and the
artifact derivation inside each job cost no separate GPU time.

## Infrastructure failures and exclusions

A lane is void, with no read, when its job does not end COMPLETED with exit
code 0:0 (except an exit 75 completed by its one continuation), when a
start-up check fails (exit 2), on an integrity failure (exit 3), when
provenance verification fails, or when the orx node lacks its ORX_RESULT line.
A void lane may be re-run under this id only if no lane receipt was produced
by it (chunk files no statistic has read do not count), in a new run root.

## Reported regardless of outcome

- Both lanes' receipts: every statistic above with points, intervals and the
  per-seed null values; per pair, per leg, per layer and per depth tables;
  tie counts; the matched budgets used; the fixed-budget rows; the development
  artifact's digest, counts, context lengths and dropped tail bytes; timings
  per stage; the determinism mode; torch and transformers versions.
- The entity anchors of every development question.
- The K1 smoke reproduction, whatever its outcome.
- The combined read with its requirements, and the GPU-hours used per lane.

## Freeze procedure

1. The program owner accepts or amends the design decisions below (a
   decision in `program/decisions.md`). The code table above is recomputed
   from the final code; `tests/test_dense_headroom_prereg.py` binds it to the
   working tree.
2. This file is frozen with
   `uv run python scripts/preregister.py freeze q3-dense-headroom-precheck-v1 program/preregistrations/q3-dense-headroom-precheck-v1.md`
   and committed with its ledger row.
3. An image is built from that commit; the CPU doctor
   (`scripts/run_dense_headroom_precheck_doctor.py`) runs in the image
   (network none, no GPU) and its receipt is kept with this experiment's
   evidence.
4. The two lane manifests are filled by
   `scripts/fill_dense_headroom_precheck_manifests.py` and pass the
   submitter's dry run and test-only run; the 0.6B lane is submitted first,
   then the 4B lane.
5. The combined read is written by
   `scripts/summarise_dense_headroom_precheck.py`; `program/state.json` and the
   Q3 question file are updated.

## Design decisions

Each states the choice and why; all are open for the program owner.

1. Two lanes, both always run. D26 names both bases. The 4B lane is not
   conditional on the 0.6B result because a NEGATIVE-capable v3 may exist on
   one and not the other, and the combined rule needs both.
2. Development partition only, from the K1 bundle only (D26). The bundle's
   development prompts are K1 v1's 20 development questions; no new Belebele
   question, haystack or language is read. Consequence: no seen-script
   cross-script pair can be measured (the bundle has development prompts only
   for the seven held-out scripts), and the anchored share is estimated on 20
   questions.
3. Development literal (ML) prompts are constructed from development needles
   with the K1 builder's sentence rule. K1's ML prompts are all in the audit
   partition, and H1 on ML and the null's V1 adequacy need them.
4. Re-tokenization for Qwen3.5-4B-Base, segment by segment, with the matched
   budget kept at 12.5 percent of the context. Feeding Qwen3 ids to a model
   with another vocabulary is wrong, and re-building 8,192-token contexts would
   need the raw haystack (outside D26's scope). The fixed 256-block rows are
   reported beside it.
5. NEGATIVE_CAPABLE needs H1_CX at least 20 (K1's inherited rule, named in
   D26) and its development lower bound at least 10; GO_ONLY_CAPABLE needs at
   least 10. H2 gates only on FAIL (points below K1's thresholds) because the
   development read cannot reach K1's H2 bounds with useful power.
6. The entity-anchor rule is a deterministic English-side rule (capitalised
   words after the first, digit runs, both shared with the passage). Proper
   nouns cannot be detected by case in six of the eight languages; Belebele's
   translation rules carry the English anchors into every translation. It
   misses lower-case entities and counts capitalised common words after the
   first; both are visible in the per-question anchor list.
7. The literal selector (LEX) measures the anchor confound in K1's own units:
   its xi_rel on all families against 0.10 (K1's NEGATIVE limit) decides
   anchor_confound. Stop ids come from the development haystack per language,
   not from a stop-word list, so the rule is the same for every script.
8. The block-score null uses noise on natural-log block scores, because a
   KL-distilled indexer's scores approximate the log of its target up to a
   constant; sigma spans 0.25 to 2 and only scales whose null passes K1's V1
   rule decide null_calibration. The 2-point and 0.10 limits are a fifth of
   K1's GO threshold and K1's NEGATIVE xi_rel limit.
9. On Qwen3.5-4B-Base, deterministic torch kernels are requested with
   warn-only, because the gated-delta layers run Triton kernels outside
   torch's deterministic registry and an op without a deterministic kernel
   would otherwise end the job; the receipt records the mode. Nothing read
   here depends on bitwise reproducibility.
10. The floor candidate is the gauntlet's example (lower bound of G(MN) at
    least 0.5), defined on entity-controlled families so that it measures
    non-literal adequacy, and judged by whether it separates a literal-only
    selector from a V1-adequate noisy copy of the target.
11. The K1 smoke reproduction is a validity gate for the 0.6B lane: same
    tokens, same capture path, K1 v2's equivalence-tested batched selection.
    A failure means the new code path does not reproduce K1 v1's measurement.
12. Caps 0.15 and 0.35 GPU-h (9 and 21 minutes on one GPU), about twice the
    estimated use, summing to D26's 0.5 GPU-h; one continuation per lane
    inside the lane's own minutes.
13. Container profile `default` for the 0.6B lane and `large-cpu-mem` (an exec
    /tmp) for the 4B lane, whose Triton kernels compile and load at first use;
    the entry point also points Triton's and TorchInductor's caches at the run
    directory.
14. The CPU doctor runs tiny random Qwen3 and Qwen3.5-style models with
    stand-in byte and pair tokenizers on a synthetic bundle built by the real
    K1 builder; on CPU it blocks flash-linear-attention so the gated-delta
    layers use transformers' torch implementation. It proves executability
    and gate semantics only, never anything about the real models or data.
