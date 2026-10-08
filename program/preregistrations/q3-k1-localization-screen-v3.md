# Q3 K1 localization screen v3 on Qwen3.5-4B-Base (q3-k1-localization-screen-v3)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-08
by the single synthesis owner of the K1 v3 research gauntlet (program decisions
D24 and D26) on branch `gauntlet/k1-v3`. Its design decisions (47 to 73 below)
need the program owner's acceptance, and its projected caps (7.21 GPU-h
central, 9.79 high, before the 4B throughput probe exists) put admission with
Kevin under D24. No GPU job of this experiment may run before a freeze. The
gauntlet proposal that argues and attacks this design is
`program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md`.

## Relation to K1 v1, K1 v2 and the dense pre-check

- `q3-k1-localization-screen-v1` (frozen 2026-10-07) stopped at its smoke
  gate (SMOKE_PASS_OVER_BUDGET, smoke 452). `q3-k1-localization-screen-v2`
  (same science, new engineering; D20) was never frozen: its caps were 8.05
  GPU-h, and its gauntlet ended at an honest exit (score 45, refute-first triad
  3 of 3 refuted; D26).
- D26 required any K1 v3 to add a non-literal adequacy floor, an
  entity-controlled question set and a seen-script cross-script condition,
  take a new id and run the gauntlet.
- `q3-dense-headroom-precheck-v2` (frozen at `ed5d5a9`, Slurm 859 and 862)
  read the development partition with dense models only. Its combined read is
  NEGATIVE_CAPABLE_V3 on qwen3.5-4b-base with seven requirements
  (`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2/summary/combined-read.json`).
  Its independent verification adds three caveats: the lexical confound comes
  from same-language paraphrase, so entity control and anchor masking alone do
  not remove it; the CENTRED and VIABLE flags passed by 0.019 to 0.067 points;
  and needle fertility tracks needle language on both legs (Spearman -0.893
  on CX and MN).

This file is a new experiment. It keeps K1's arms, targets, training
composition, learning-rate grid, seeds, validity-gate thresholds and decision
thresholds where it can, and changes what the requirements and caveats force.
The traceability table at the end maps each requirement and caveat to the
clause that meets it.

## Question

On frozen Qwen3.5-4B-Base, do block-form (compress ratio 4) sparse-attention
indexers fitted on each of its eight softmax-attention layers, distilled by KL
from that layer's own attention, lose more needle-selection recall than the
dense block top-k of their own distillation target when the question is a
human translation in a different script from the needle passage, compared with
a question in the needle's own language?

Recall is counted only on needle blocks that share no content token with
either question (overlap-masked recall), on families whose question carries no
entity anchor (the entity-controlled set), at a matched budget of 1,024 of
8,192 tokens. The primary contrast uses the seven scripts that indexer
training never saw. The comparator stratum uses three scripts that training
did see, in the same bilingual configuration.

Claim scope: attachment-capability. Frozen backbone, KL-only indexers of the
Stage-1 kind (QSA and DSA warm-up). No result is a statement about co-trained
production indexers, and none is an architecture claim.

## Identity

Code: new, not yet written. The v3 harness extends K1 v2's tabled code (the
batched bank, the statistics module and the data module) and the dense
pre-check v2's Qwen3.5 capture and evaluation path
(`harness/dense_headroom_torch_v2.py`, `harness/dense_headroom_v2_lanes.py`).
The code table, its digests, commit A3 and image A3 are filled at the freeze.
Every file the 4B throughput probe runs must equal that table (K1 v2
decision 44, carried).

Image: none exists for v3. The image of record for the 4B evaluation path is
the dense pre-check v2 image
`127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`
(image id `sha256:500f3b027173a2d772b7d6ea00ea667dbe1bc956df51e3c2c4455d9c08a2714b`,
build 855, commit `ed5d5a9`), which ran the 4B lane (Slurm 862). Image B3 is
built from the commit that holds the frozen file and its ledger row.

Model: Qwen/Qwen3.5-4B-Base at `1001bb4d826a52d1f399e183466143f4da7b741b`
(apache-2.0). Host receipt SHA-256
`253a14185bcff0762b8a43944635a550055d3346fe16c416d6bcfe4460793cfe`,
artifact root `c7fbfd6bd1c73b9a0080decf794f5e4333c955f2704591affc61b0a9ac850e42`,
tokenizer SHA-256 `fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927`
(the lane-862 receipt). From the config at that revision: 32 layers, of which
layers 3, 7, 11, 15, 19, 23, 27 and 31 are gated softmax attention and the
rest Gated DeltaNet; 16 query and 4 key-value heads of dimension 256; hidden
size 2,560; interleaved multimodal rotary on a 0.25 fraction (64 of 256
dimensions) at theta 1e7, which reduces to ordinary rotary for text; vocabulary
248,320.

Data sources (revisions as in K1 v2 unless stated):

| Source | Revision | Licence | Use |
|---|---|---|---|
| facebook/belebele | 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2 | CC-BY-SA-4.0 | needles, questions, options; new: ben_Latn and hin_Latn passages for the TR leg |
| HuggingFaceFW/fineweb-2 | af9c13333eb981300149d5ca60a8e9d659b276b9 | ODC-By-1.0 (Common Crawl terms of use apply) | test-split monolingual training text; non-English haystacks; tha, hin and khm split into disjoint training and haystack pools |
| HuggingFaceFW/fineweb | 9bb295ddab0e05d785b879661af7260fed5140fc | ODC-By-1.0 (Common Crawl terms of use apply) | English haystacks |
| jhu-clsp/paradocs | f80095affa44545d18d0d64a574f9b8679017196 | Apache-2.0 packaging; ParaCrawl text not owned by the packager | bilingual training documents |

TED2020 stays excluded (D4). NLLB models and data are not used. Only ids,
digests and aggregates are published. Receipts store entity anchors and
overlap tokens as SHA-256 digests, not strings (decision 70).

Throughput probe: `q3-k1-v3-throughput-probe-v1`, its own id, 1 GPU, cap 0.25
GPU-h, synthetic token ids, no Belebele or partition read (decision 66).

## Arms

Two KL-only block indexers per softmax-attention layer, on all eight such
layers, distilled from:

- hs: head-sum of the 16 heads' exact attention, L1-normalised, summed within
  each 4-token block, renormalised over complete blocks;
- mp: QSA Eq. 17 (head-sum, L1, maximum within each 4-token block, L1 over
  complete blocks).

hm (sum within the block of the per-token head maximum) is a descriptive dense
selector only. A block b is complete for query row i when 4b + 3 is at most i.

Indexer (both targets): four query heads of dimension 128 and one key per
block. q_i^j = RoPE_i(RMSNorm(W_Q^j x_i)); kbar_b = RoPE_4b(RMSNorm(mean of
W_K x_s over the block's 4 tokens)); I_ib = sum over j of w_ij ReLU(q_i^j ·
kbar_b) / sqrt(128); w_ij = b_j + x_i W_w[:, j], with b = 1 and W_w = 0 at
initialisation. x_i is the layer's attention input (post input-RMSNorm hidden
state, detached), of dimension 2,560. Rotary covers 64 of the 128 dimensions
at theta 1e7, the rotary dimension count of the core attention (decision 52).
W_Q and W_K are drawn from N(0, 1/2,560) by a generator seeded with SHA-256 of
(seed, layer, target). 1,648,900 parameters per indexer.

Selection: the top 256 complete blocks by score (1,024 of 8,192 tokens) plus
the incomplete tail block; ties go to the lower block index. The dense target
selector T applies the same rule to the target distribution.

Training grid: targets {hs, mp} x learning rates {3e-4, 1e-3, 3e-3} x seeds
{42, 43, 44} = 18 indexers per layer, 144 in all, trained in one shared
frozen-teacher stream. Adam (0.9, 0.999, eps 1e-8, no weight decay), clipping
at 1.0 per indexer, batch 4 sequences of 8,192 tokens, 610 steps (20.0M
tokens), 20-step linear warm-up then constant learning rate, deterministic
algorithms, TF32 for the indexer's matmuls, no torch.compile and no code
generated at run time. Targets are recomputed exactly in fp32 per 1,024-row
chunk from the teacher's captured post-RoPE bf16 queries and keys. The teacher
runs all 32 layers in bf16 with cuDNN attention off (D42 (i)), and its
Gated DeltaNet layers run flash-linear-attention's pinned Triton kernels.

## Training stream

K1's composition, rebuilt with the Qwen3.5 tokenizer (decision 50): 2,441
training and 64 stream-dev sequences of exactly 8,192 tokens, half bilingual
and half monolingual, items separated by the tokenizer's end-of-text id.

- Bilingual items: ParaDocs, English side then X side or the reverse (SHA-256
  coin), each side truncated at 512 tokens, for en-de, en-fr, en-es, en-pl
  (`strict`) and en-th, en-hi, en-km (`all/paracrawl`), with K1's
  reimplemented filter. Quotas are recomputed for the new tokenizer by K1's
  formula; files are read in name order up to a 9 GB cap; cross-script
  shortfalls are refilled from the same-script pairs; realised shares are
  reported. en-km is expected to stay short, because both files were consumed
  under the Qwen3 tokenizer.
- Monolingual items: FineWeb-2 test splits in deu, fra, spa, pol, tha, hin,
  khm, cmn, arb and rus, truncated at 2,048 tokens. For tha, hin and khm a
  document is training-eligible only if bit 0 of the first byte of SHA-256 of
  its id is 0; the others form the haystack pool (decision 55).
- Exclusions: K1's held-out-script filter (Hiragana, Katakana, Hangul,
  Bengali, Tamil, Greek, Hebrew, Georgian), K1's Latin function-word filter,
  and exact 50-gram and MinHash (Jaccard at least 0.8) dedup against every
  Belebele passage, question and option in every evaluation language and
  variant, now including ben_Latn and hin_Latn.
- Claim boundary: training sees en, de, fr, es, pl, th, hi, km, zh, ar and ru
  text, and the scripts Latin, Thai, Devanagari, Khmer, Han, Arabic and
  Cyrillic. It never sees the seven held-out scripts, apart from Han shared
  with Japanese kanji.
- V1 extension data: epochs 2 and 3 of the same sequences in permutations
  seeded 43 and 44.

## Learning-rate freeze

K1's rule: per target, the learning rate with the lowest mean stream-dev KL
over the three seeds and eight layers; 1e-3 wins if within 1 percent of the
minimum; an exact tie goes to the lower rate. The record and its SHA-256 are
written before any audit prompt is read, and non-selected rates are never
evaluated on the audit partition.

## Evaluation

Partitions: K1's `split_passage_ids(seed=42)` over Belebele links,
development 122 passages and 224 questions, audit 122 and 230, primary 244
and 446. The smoke and the development pre-step read development only; the
H2 gate and the main job read audit only; the primary partition is never read
(decision 64 states the owner option that would change this).

Contexts: exactly 8,192 Qwen3.5 tokens (decision 50), built by K1's rules in
the new tokenizer: the end-of-text id, then needle-language haystack documents
(FineWeb-2 test split for X, from the haystack pool for tha, hin and khm; the
FineWeb shard for English), each followed by "\n\n", the passage (followed by
"\n\n") at the document boundary nearest to depth x (8,191 minus the needle
length), and the haystack tail cut. Depth cycles through {0.15, 0.50, 0.85} in
a SHA-256 order per needle language. Query: "\n\n" + question + "\n"; query
rows are the question tokens.

Legs and families (audit):

| Leg | Pairs | Units | Role |
|---|---|---|---|
| CX and MN, unseen stratum | (X, en) and (en, X) for X in ja, ko, bn, ta, el, he, ka: 14 pairs | 3,220 CX + 1,840 MN | primary decision statistic |
| CX and MN, seen stratum | the same for X in th, hi, km: 6 pairs | 1,380 CX + 690 MN | registered comparator (decision 48) |
| ML literal ceiling | 100 English-needle and 100 X-needle prompts (10 per non-English needle language) | 200 | V1 and V2 use the 100 English ones |
| TR, transliterated needle | for X in bn, hi: the X family's context with the passage replaced by its human Latin transliteration, queried by the X question and by the English question | 920 | descriptive script-only contrast (decision 57) |
| CS, same-script cross-language | K1's five Latin pairs (id, tr, sw, nl, it) both directions, plus their MN legs | 3,450 | descriptive cross-language contrast |
| H2 cells | 2,000 unseen-stratum CX cells (SHA-256 order) with needle present and with needle absent | 4,000 multiple-choice units | H2 gate (decision 61) |

All 230 audit questions appear in every pair (crossed design). MN and CX of a
family share haystack, needle and position. English-needle contexts are
shared by all English-needle pairs. Multiple choice is K1's acc_norm; the
unnormalised and per-character variants are reported beside it.

Development pre-step units (development partition, 20 questions, dense only):
the 20 pairs' CX legs with multiple choice, their MN legs, ML for every needle
language, TR, needle-absent twins and no-haystack references for the CX
cells.

## Masking, the controlled set and the literal check

- Content tokens: LEX's rule from the dense pre-check (not among the 100 most
  frequent token ids of the development haystack of the needle language or the
  query language, and decoding to text with a letter or digit), in the
  Qwen3.5 tokenizer.
- Overlap mask, per family f: O_f is the set of content-token ids that the
  needle shares with the MN question or with the CX question. Every needle
  token in a 4-token block containing a token of O_f is masked. N^M_f is the
  unmasked needle tokens; masked recall is |S ∩ N^M_f| / |N^M_f|. The same mask
  applies to both legs of the family and to every selector. The masked random
  baseline is the analytic expectation over N^M_f. A family with |N^M_f|
  below 32 tokens is excluded and counted (decision 49).
- Entity-controlled set: a question is anchored when its English wording
  contains a capitalised word (not the first word, not "I") or a digit run
  that also occurs in the English passage (the dense pre-check's model-free
  rule). Controlled families are those of unanchored questions. The rule is
  applied to the audit text when the bundle is built, before any model read.
- Literal check: LEX, the dense pre-check's literal selector, is evaluated on
  every leg with and without the mask. It is a reference, not a gate on the
  audit read; its development values gate the pre-step (below).
- Dilated mask (descriptive): also masks the blocks adjacent to masked
  blocks.

## Metrics

Recall of selector A on a prompt: per layer, the mean over query rows of the
recall fraction, then the mean over the eight softmax-attention layers. Both
masked (R^M) and unmasked (R) recall are computed for every selector.

Selectors: the indexer at the frozen learning rate, seed-averaged (R_ind);
the dense top-256 blocks of its own target (R_T); U and U_k; R_rand; hm; LEX;
and the block-score nulls N:T:sigma:seed (natural-log target block scores plus
sigma times standard normal noise, generator seeded by SHA-256 of seed, unit
and layer). The audit read uses sigma in {0.5, 0.59, 0.71, 0.84, 1.0, 1.19};
the development pre-step uses 17 sigmas from 0.25 to 4 at ratio 2^(1/4)
(decision 59).

Primary statistic, per target T: xi^M_T = macro over the 14 unseen-stratum
pairs of the controlled-family mean of
[R^M_ind(MN) − R^M_ind(CX)] − [R^M_T(MN) − R^M_T(CX)], in recall points.

Co-statistic: G^M(c) = (R^M_ind(c) − R^M_rand(c)) / (R^M_T(c) − R^M_rand(c))
on pair-condition means; xi_rel^M_T = macro over pairs of
G^M(MN) − G^M(CX). K1's evaluability rule and 1-point replicate floor apply.

Comparator: xi^M_T,seen and xi_rel^M_T,seen, the same on the seen-stratum
pairs that survive the pre-step. Attribution contrast:
Delta_xi = xi^M_T − xi^M_T,seen.

Interval: K1's combined interval. se_cluster is the SD of a passage-cluster
bootstrap over the audit links that hold at least one controlled question
(B = 10,000, NumPy seed 42, macro inside each replicate, seeds fixed); s_seed
is the SD of the three per-seed values; the 99 percent interval is
point ± t(0.995, df) x sqrt(se_cluster² + s_seed²/3) with Welch-Satterthwaite
df (cluster term df = clusters − 1). The percentile interval, df and the
per-seed values are reported. A CR2 cluster-robust interval with Satterthwaite
df is reported beside it (descriptive).

Floor: G^M(MN) and the unmasked G(MN) on controlled unseen-stratum families,
each with its 99 percent percentile cluster-bootstrap interval.

## Validity gates

- V1 adequacy, per target, at every seed: English ML R_ind at least
  R_T(ML) − 5.
- V2 bug tell (decision 60): for some target, the seed-mean English ML
  difference R_ind − R_T(ML) has a 99 percent passage-cluster lower bound above
  +1 point. HOLD, terminal for this id (D16).
- V3 integrity: K1's (finite values, selection at most 1,027 tokens, every
  unit exactly once, digests verified), plus the mask and controlled-set
  digests.
- V4 null calibration on the audit read, per target: at every audit sigma
  whose null passes V1 at every seed, seed-mean |xi^M| at most 2 points and
  |xi_rel^M| at most 0.10 (the block-score null of the dense pre-check, on the
  masked controlled statistic). A target that fails V4 can be neither GO nor
  NEGATIVE; the verdict is then INCONCLUSIVE with the label NULL_OFF_CENTRE
  (decision 59).
- H1^M: max over T of the macro over unseen-stratum pairs of
  [R^M_T(CX) − R^M_rand(CX)] on controlled families: at least 10 to interpret,
  at least 20 for a NEGATIVE.
- H2a and H2b on the H2 gate's 2,000 cells under K1's bounds: H2a, macro over
  the 14 pairs of CX acc_norm, 99 percent percentile cluster-bootstrap lower
  bound above 30 percent; H2b, needle-present minus needle-absent accuracy
  (plain mean), 99 percent lower bound above 0 and point at least 5 points.

## Development pre-step (dense only, after the smoke)

Decision PROCEED_TO_H2 when all of the following hold on the development
partition, otherwise STOP_INSTRUMENT with the failing items listed. A stop
ends this id; any successor takes a new id.

1. Masked headroom: masked controlled unseen-stratum H1_CX point at least 20
   with 99 percent lower bound at least 10.
2. Literal check, two-sided: on controlled unseen-stratum families, LEX
   masked xi within ±2.5 points and masked xi_rel within ±0.05, for both
   targets.
3. Null calibration on the 17-sigma grid, masked and controlled: at every
   sigma whose null passes V1 at every seed, seed-mean |xi^M| at most 2 and
   |xi_rel^M| at most 0.10, and at least two such sigmas with a seed-mean
   English ML loss between 2.5 and 5 points, for both targets.
4. Floor viability: at two or more of those reaching sigmas, the null's
   controlled G^M(MN) and G(MN) 99 percent lower bounds are at least 0.5; LEX's
   controlled G^M(MN) point is below 0.5.
5. Seen stratum: a seen language whose masked controlled CX headroom point
   (hs) is below 20 is dropped from the stratum (both its pairs) and
   reported; at least two of th, hi and km must remain.
6. Mask coverage: at most 25 percent of controlled unseen-stratum families
   excluded for |N^M| below 32 tokens.
7. TR: a TR language whose masked TR headroom point is below 10 is dropped
   from the descriptive TR contrast (not a stop).

Development H2a and H2b are reported, not gated (the combined read moved the
H2 test to the audit read).

## H2 gate (dense only, audit, before any indexer is trained)

2,000 unseen-stratum CX cells, each scored with the needle present and with
the needle absent (4,000 multiple-choice units). If H2a or H2b fails, the
final verdict is UNINTERPRETABLE and no indexer is trained. Otherwise
PROCEED_TO_K1. The audit read never recomputes H2 (decision 61).

## Decision rules (main read)

- GO: some target T with xi^M_T at least 10, the combined 99 percent lower
  bounds of xi^M_T and xi_rel^M_T above 0, V1 to V4 passing for T, and H1^M at
  least 10. Labels (descriptive, all reported):
  - SEEN_TOO when the seen comparator's point is at least 5 for T;
  - UNSEEN_SPECIFIC when Delta_xi is at least 5 and the seen point is below 5;
  - CROSS_SCRIPT when xi^M_T minus the CS stratum's masked xi is at least 5;
  - SCRIPT_ONLY when the TR contrast's point is at least 5 (decision 57).
- NEGATIVE: for both targets, xi^M_T at most 5 with the combined upper bound
  below 10 and half-width at most 5, and xi_rel^M_T at most 0.1 with its upper
  bound below 0.2; the floor (the 99 percent lower bounds of controlled
  G^M(MN) and of controlled G(MN) both at least 0.5, per target); V1 to V4
  passing for both; H1^M at least 20; and the robustness conditions:
  - the seen comparator's point at most 5;
  - each direction's point (macro over its seven pairs) at most 5;
  - no layer whose xi^M point is at least 10 with a 99 percent lower bound
    above 0 (decision 58).
  If every NEGATIVE-region condition holds except a robustness condition, the
  verdict is INCONCLUSIVE with the label SEEN_EXCESS, DIRECTION_CONCENTRATED
  or LAYER_CONCENTRATED.
- UNINTERPRETABLE: H1^M below 10 on the audit read (H2 is decided by the H2
  gate).
- HOLD: a V2 bug tell (decision 60). Terminal (D16).
- VOID: a V3 integrity failure.
- V1 extension: K1's rule (one registered extension, epochs 2 and 3, only the
  V1-failing targets, mandatory when called, INCONCLUSIVE if not run or void).
  The extension re-reads only the decision legs (CX, MN, ML); the TR and CS
  rows of re-read targets are not reported (decision 65).
- INCONCLUSIVE: everything else, including a disagreement between the xi and
  xi_rel classifications and any half-width above 5.
- Order: VOID, HOLD, UNINTERPRETABLE, V1_EXTENSION_REQUIRED, GO, NEGATIVE,
  INCONCLUSIVE, as in K1; a target failing V4 is treated like a target in
  neither region.
- Multiplicity: two targets at 99 percent each, as in K1. Strata, layers,
  directions, CS, TR, dilated-mask, unmasked and covariate rows are
  descriptive and uncorrected, except where a robustness condition uses them
  as a veto.

## Reported regardless of outcome

- Everything K1 v2 reports, on masked and unmasked recall.
- Per-question overlap distributions on MN and CX, the share of MN families
  whose overlap is at most the largest CX overlap (positivity), and a
  descriptive leg-interacted regression of the family excess on the overlap
  difference with its intercept, slope and cluster interval (decision 63).
- Fertility of every needle and question language in the Qwen3.5 tokenizer;
  pre-fixed fertility-matched seen-unseen contrasts (decision 56); a
  pair-level regression of xi^M on log fertility and a seen indicator;
  randomization inference over the 120 assignments of three of the ten
  cross-script languages to the seen stratum (descriptive).
- Per-layer, per-direction, per-language, per-depth tables; the
  recall-versus-budget curve at 512, 1,024, 2,048 and 4,096 tokens from the
  same scores; the block-0 share of each selector's budget.
- Per-family null recall CDFs on MN and CX and their Kolmogorov-Smirnov
  distance (descriptive check of the scale assumption, decision 59).
- Seed SD per target, before any remedy arm.

## Seeds, sample sizes and sensitivity

- Seeds 42, 43, 44 set indexer initialisation only. Stream order, the passage
  split, prompts, cell samples and the bootstrap use seed 42 or SHA-256
  orders.
- Audit counts: 3,220 unseen-stratum families and 1,380 seen-stratum families
  over 122 links; about half are controlled on the development rate (0.50,
  Wilson 0.30 to 0.70), and the exact audit count is a bundle fact fixed
  before freeze.
- Synthesis approximations (normal approximations and a seeded Monte Carlo of
  the decision rule, not the registered simulation; 70 effective clusters,
  masking inflating se_cluster by 1.12, seed SD 1):
  - cluster-level SD of the family excess 10: median half-width 3.8;
    P(NEGATIVE) 0.95 at a true xi of 0 and 0.48 at 5; P(GO) 0.25 / 0.50 / 0.76
    / 0.91 at 9 / 10 / 11 / 12;
  - cluster SD 13.4: half-width 4.9; P(NEGATIVE) 0.62 at 0;
  - cluster SD 16: half-width 5.8; NEGATIVE unreachable.
  The development LEX excess implies a cluster SD of about 5.9; K1's worked
  case used 10.
- H2b (development ICC 0.138): P(pass) at a true effect of 8.6 points is 0.24
  with K1's 300 cells, 0.69 with this file's 2,000 cells, 0.78 with all 4,600
  CX cells and 0.98 with 2,000 audit plus 2,000 primary cells.
- Per-layer veto: with a layer SE 1.5 times the macro's, it fires with
  probability below 0.001 when every layer's true xi is 0, and above 0.97 when
  one layer's is 15.
- The registered pre-freeze simulation (decision 62) replaces these figures
  before the freeze.

## Compute

Limits: K1 v2's formula, max(5, ceil(1.2 x 1.15 x P + 3)) minutes, cap =
GPUs x limit / 60, with P projected from the 4B probe's rates. The 8 GPU-h
count is the sum of caps of every job, the extension at its worst case and
the probe included (D22). The design is not cut to fit (D20); admission over 8
GPU-h is Kevin's (D24).

Synthesis projection before any probe (rates from K1 v2 probe 543 and lane
862, scaled to 8 layers, hidden size 2,560 and native 8,192-token contexts;
central / high):

| Job (1 GPU each) | Projected minutes | Limit (min) | Cap (GPU-h) |
|---|---|---|---|
| q3-k1-v3-throughput-probe-v1 | | 15 | 0.25 |
| smoke | 7.8 / 9.6 | 14 / 17 | 0.24 / 0.29 |
| development pre-step | 16.7 / 24.1 | 27 / 37 | 0.45 / 0.62 |
| H2 gate | 37.8 / 55.6 | 56 / 80 | 0.94 / 1.34 |
| resume R0, R1, R2 | 9.4, 6.5, 7.0 / 12.1, 7.9, 8.5 | 16, 12, 13 / 20, 14, 15 | 0.69 / 0.83 |
| main | 106.6 / 148.4 | 151 / 208 | 2.52 / 3.47 |
| V1 extension (worst case) | 89.6 / 127.0 | 127 / 179 | 2.12 / 2.99 |
| Total | | | 7.21 / 9.79 |

Expected use: about 0.5 to 0.7 GPU-h if the pre-step stops, 1.1 to 1.6 if the
H2 gate stops, 3.3 to 4.5 without the extension, plus 1.5 to 2.1 with it.

The smoke also re-evaluates 48 units of the dense pre-check v2's 4B
development artifact (`b5210f79...`, 24 selection plus multiple-choice and 24
multiple-choice-only) and must match the host chunk files of job 862 within
1e-4 recall points and 1e-4 in every option score, with the same answers
(decision 51).

Continuation, resume test and failures: K1 v2's rules (one main continuation
inside the main cap; R0 40 steps, R1 held at step 25 and checkpointed on
SIGUSR1, R2 resumed in a fresh job, final indexer state bit-equal to R0's). The
probe must first show that two identical teacher forwards give bit-identical
captured queries, keys and layer inputs (decision 67).

## Bundle

`k1-bundle-v3.json`, built on the host CPU inside the v3 image with
`--network none` from K1's raw directory (raw manifest `808e6c24...`) plus the
new Belebele files (ben_Latn, hin_Latn; one fetch stage with network). Facts
recorded before the freeze, with no model run:

- the Qwen3.5-tokenized stream and its quotas, shortfalls and realised
  shares; the haystack-pool split and its disjointness check (exact hash and
  MinHash) for tha, hin and khm;
- per-language needle and question fertility, needle lengths and the share of
  needles over the budget;
- the anchored share of the audit and development questions and the number
  of links with at least one controlled question;
- per-question overlap on every leg, |N^M| / |N| per language, and the
  exclusion count under the 32-token rule;
- the TR alignment check: for every audit and development (link,
  question_number) of bn and hi, the Latin passage exists, its digit runs and
  sentence count equal the native passage's, and its question is never used
  (decision 57);
- unit counts and query rows per leg.

## Freeze procedure

1. Build the bundle and record its facts (CPU). Fix the fertility-matched
   pairs (decision 56).
2. Run the registered pre-freeze simulations with the v3 statistics code
   (decision 62) and replace the approximations above.
3. Freeze and run the 4B throughput probe under its own id; derive limits;
   record them in `program/decisions.md`.
4. If the caps exceed 8 GPU-h, Kevin rules on admission (D24). Then commit
   A3, image A3, doctors, the frozen file and its ledger row (commit B3),
   image B3, doctors in B3, and the orx nodes in the order smoke, development
   pre-step, H2 gate, R0, R1, R2, main, continuation if needed, and the
   extension when called.

## Requirement and caveat traceability

| Source | Requirement or caveat | Where met |
|---|---|---|
| Combined read 1 (D26) | a seen-script cross-script condition | seen stratum th, hi, km (Evaluation; decision 48); pre-step item 5; NEGATIVE robustness condition; GO labels |
| Combined read 2 (D26) | an entity-controlled question set | controlled set (Masking); decision 53 |
| Combined read 3 (D26) | a new experiment id and the research gauntlet | this id; the K1 v3 gauntlet |
| Combined read 4 (D26) | the non-literal floor, controlled G(MN) 99 percent lower bound at least 0.5 | NEGATIVE floor, on unmasked G(MN) and on masked G^M(MN) |
| Combined read 5 | GO and NEGATIVE computed on the entity-controlled set | primary statistic and floor are controlled-family statistics |
| Combined read 6 | anchor masking or a lexical-overlap covariate | overlap mask (a superset of anchor masking); covariate reported, descriptive only (decision 63) |
| Combined read 7 | H2 re-tested under K1's bounds on the audit read | H2 gate on 2,000 audit cells, K1's bounds (decision 61) |
| Verifier caveat 1 | the lexical confound comes from same-language paraphrase | overlap mask on all shared content tokens, two-sided LEX check at the pre-step, TR leg with zero shared tokens, positivity report |
| Verifier caveat 2 | CENTRED and VIABLE passed by 0.019 to 0.067 points | 17-sigma grid, two reaching sigmas required, re-measured on the masked instrument at the pre-step, audit null as validity gate V4 for both GO and NEGATIVE |
| Verifier caveat 3 | fertility follows needle language on both legs | native 8,192-token contexts remove context-length variation by language; fertility-matched seen-unseen contrasts; TR changes fertility at fixed language and content; claims at language level stay descriptive |

## Design decisions (for the owner's acceptance)

K1 v1 decisions 1 to 17, 19 to 22, 24, 25 and 27 to 29 apply as written, with
"0.6B" read as "Qwen3.5-4B-Base" and "28 layers" as "the eight
softmax-attention layers". v1 decisions 9, 12, 15, 18, 23, 26 and 30 to 31
and v2 decisions 32 to 46 are replaced or restated below. v2 decisions 33 to
36 (batched bank, constants, vectorised evaluation, equivalence evidence)
carry over to the 4B bank with new tolerances fixed by the probe.

47. New id, base Qwen3.5-4B-Base (D26; combined read). Reason: the 0.6B lane
    is NOT_VIABLE; the 4B lane is NEGATIVE_CAPABLE.
48. Primary stratum = the seven unseen scripts; seen stratum th, hi, km as the
    registered comparator, not pooled into the decision statistic. Reason:
    continuity with Q3's question and K1's pairs; pooling would dilute an
    unseen-only effect by 14/20, and three seen languages cannot support a
    pooled claim about seen scripts. The seen stratum enters NEGATIVE as a
    veto and GO as a label.
49. Overlap-masked recall as the decision metric; families with fewer than 32
    unmasked needle tokens excluded. Reason: the MN leg's overlap (0.38 to
    0.68 per pair) has no common support with CX (0 to 0.04), so a covariate
    extrapolates; masking removes shared tokens from the measured evidence on
    both legs at no GPU cost.
50. Native 8,192-token contexts and stream in the Qwen3.5 tokenizer, not
    re-tokenized Qwen3 contexts. Reason: re-tokenizing gave 49 to 10,481
    tokens with matched budgets of 107 to 327 blocks, varying by language, and
    contexts above the indexer's 8,192-token training length. Cost: about 20
    percent per unit; the lane-862 headroom does not carry over exactly and is
    re-measured at the pre-step.
51. The smoke re-evaluates 48 units of the dense pre-check v2's 4B development
    artifact against job 862's chunk files (tolerance 1e-4). Reason: keeps a
    validity gate on the 4B evaluation path that decision 50 would otherwise
    lose.
52. Indexer rotary on 64 of 128 dimensions at theta 1e7. Reason: K1 decision
    12's rule (QSA matches the core attention's rotary dimension); the core
    attention rotates 64 dimensions at theta 1e7.
53. Controlled set by the dense pre-check's English-side anchor rule, applied
    to the audit text at the bundle build. Reason: requirement 2; a
    model-free rule fixed before any read.
54. Floor on both masked and unmasked controlled G(MN). Reason: requirement 4
    is stated on G(MN); the masked version makes a literal-only selector
    (masked G near 0) fail the floor decisively, answering the verifier's
    "permissive floor" note.
55. tha, hin and khm FineWeb-2 test documents split by SHA-256 of their id
    into training and haystack pools. Reason: those splits are both K1's
    training source and the seen languages' only haystack source.
56. Fertility-matched seen-unseen pairs are fixed from the bundle's
    fertilities before freeze (each seen language with its nearest-fertility
    unseen language). Reason: caveat 3; descriptive only, because three
    against seven languages cannot carry an inferential language-level claim.
57. TR leg (bn, hi): human Latin transliterations of the passages, native
    haystack and position unchanged; the Latin questions are not used.
    Reason: Belebele's romanized passages are transliterations, but its
    romanized questions are separately written (cross-domain row check), so
    only the needle side gives a same-language, same-content, other-script
    condition. Descriptive; the Latin needle is a script island in a native
    haystack, which the indexer-minus-target difference only partly cancels.
58. Per-layer and per-direction vetoes on NEGATIVE. Reason: the target's own
    MN-minus-CX gap sits at layers 3 and 31 (4.37 and 5.07 points against
    -0.86 to 0.96 in layers 15 to 23), and macro averaging halves a
    one-direction effect.
59. Null grid at ratio 2^(1/4) on the pre-step, six audit sigmas, two reaching
    sigmas required; both scales (xi and xi_rel) must agree, with a
    distributional check. Reason: caveat 2; the sqrt(2) grid can place at most
    one sigma in the [2.5, 5] window.
60. V2 on the seed mean with a 99 percent cluster lower bound above +1 point.
    Reason: K1's per-seed V2 gave P(HOLD) 0.47 to 0.74 for an indexer exactly
    matching its target; HOLD stays terminal (D16), only its trigger changes.
61. H2 decided once, by a dense-only gate job on 2,000 audit cells before any
    indexer is trained. Reason: requirement 7, and an H2 failure then costs
    about 1.1 to 1.6 GPU-h instead of the whole screen. 2,000 cells give
    P(pass) 0.69 at the development point; 4,600 would give 0.78 for about 1
    GPU-h more of caps.
62. Pre-freeze simulations with the v3 statistics code at cluster SDs 6, 10
    and 13.4 and the measured effective clusters, for GO, NEGATIVE with all
    vetoes, HOLD under decision 60, and H2b; their results replace the
    approximations in "Seeds, sample sizes and sensitivity".
63. The lexical-overlap covariate is descriptive only, with a positivity
    report. Reason: no common support between legs (Miller and Chapman 2001;
    Crump et al. 2009).
64. Owner option, not adopted by default: release 2,000 primary-partition CX
    cells for dense-only H2 (no indexer read). Effect: P(H2b passes | 8.6)
    0.69 to 0.98, caps +0.80 / +1.21 GPU-h. Cost: departs from K1's "primary
    never read" and from the letter of requirement 7.
65. The V1 extension re-reads decision legs only. Reason: saves about 0.6 GPU-h
    of worst-case cap; TR and CS are descriptive.
66. A 4B throughput probe under its own id (cap 0.25) sets every limit, as K1
    v2's did. Reason: the 4B training path has never run; the synthesis
    projection's high and central step times differ by 1.65 times.
67. The probe gates teacher determinism (two identical forwards bit-equal in
    captured queries, keys and layer inputs). If it fails, this file is not
    frozen as drafted.
68. Learning-rate grid kept (D20). Single-rate fallback (caps 6.61 / 8.85) is
    not registered.
69. CS kept as descriptive rows (caps +0.42 / +0.53). Reason: K1's
    "cross-script" label needs a same-script cross-language comparator.
70. Anchors and overlap tokens stored as SHA-256 digests in receipts. Reason:
    the pre-check receipts committed short Belebele strings; the repository is
    public and Belebele is CC-BY-SA.
71. The development pre-step does not gate H2 (combined read 7). Reason: the
    20-question development H2 is POINT_ONLY by precision, not by effect.
72. Strong-alignment haystacks, a monolingually distilled arm, a width arm and
    distance-matched perturbation controls are not registered. Reason: scope
    and cost; each is named in the proposal as a later arm.
73. The v3 filler accepts limits whose caps exceed 8 GPU-h only when
    `program/decisions.md` holds an owner admission decision naming this id
    and the probe receipt's digest. Reason: K1 v2's filler refused above 8
    GPU-h with no admission path (K1 v2 feasibility refuter).
