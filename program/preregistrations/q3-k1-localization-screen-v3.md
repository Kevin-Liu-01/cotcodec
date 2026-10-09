# Q3 K1 localization screen v3 on Qwen3.5-4B-Base (q3-k1-localization-screen-v3)

Status: DRAFT, repaired under program decision D48 and again under D52. Not
frozen, not admitted, no ledger row. Written on 2026-10-08 by the single
synthesis owner of the K1 v3 research gauntlet (D24, D26) on branch
`gauntlet/k1-v3`. Wave 1 scored 51 (reviews 51 and 55); wave 2, a fresh run
on the D48 repair, scored 55 (reviews 55 and 70); both stopped at the
refute-first triad, 3 of 3 refuted
(`program/gauntlet/2026-10-08-q3-k1-v3-qwen35-4b.jsonl`). The D48 repair
changed the literal check, the NEGATIVE region, the vetoes and the seed term,
and dropped the CS legs. The D52 repair (2026-10-09, the same single owner,
no GPU) changes GO's identification: the pre-literal statistic is pooled so
that it can be evaluated where GO reads, GO needs both translation
directions, a floor in each direction and a log-retention co-statistic, the
literal-free sensitivities are gated at the pre-step, and a seed top-up
reuses the V1 extension's reserved slot. The sections "Repair under D48" and
"Repair under D52" at the end list every change (wave-1 draft sha256
`f4ce9a00...`, wave-2 draft sha256 `08fa52ca...`). Its design decisions (47
to 91 below) need the program owner's acceptance, and its projected caps
(6.96 GPU-h central, 9.46 high, before the 4B throughput probe exists) put
admission with Kevin under D24 at the high projection. No GPU job of this
experiment may run before a freeze. The gauntlet proposal that argues and
attacks this design is `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md`.

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

Sealed development seed read (decision 80), inside the main job, after the
learning-rate freeze and before any audit prompt is read: the frozen-rate
indexers (three seeds, both targets) select on the development partition's
controlled families of the 14 unseen pairs (CX and MN legs, 440 selection
units). The job computes, per target, the layer-resolved seed SD of xi^M
(the SD of the eight-layer-average per-seed xi implied by V_seed), its df
and its one-sided 80 percent upper bound, and writes them with a digest to
the receipt. The development xi point is neither computed into the receipt
nor logged. If, after the seed top-up below when it runs, the upper bound
exceeds the stated bound sigma_star = 2.2 points (five seeds; the seed SD at
which simulation S3 puts P(NEGATIVE | no excess) near 0.5 at masked
headrooms of 20 to 40), the receipt declares NEGATIVE_REACHABILITY_LOW before
the audit read; the rules do not change, but an INCONCLUSIVE cannot
afterwards be read as a near-negative.

Seed top-up (decision 81 as revised under D52; registered). If the sealed
read's 80 percent upper bound exceeds sigma_top = 1.5 points, the main job
writes the sealed record, checkpoints and stops before any audit prompt is
read. A top-up job then trains seeds 45 and 46 at the frozen rate for both
targets and all eight layers (the same stream and steps; generators by
SHA-256 of seed, layer and target), repeats the sealed read with five seeds,
and runs the audit read with five seeds. The top-up runs in the slot whose
cap the V1 extension reserves, and the two are exclusive: after a top-up a V1
failure is INCONCLUSIVE with the label V1_AFTER_TOPUP and no extension runs,
so the total of caps does not change. Without a top-up the upper bound is at
most 1.5 and no declaration can arise. In S3 the top-up moves P(NEGATIVE | no
excess) from 0.30 to 0.43 up to 0.55 to 0.59 at a seed SD of 2, and from 0.01
to 0.03 up to 0.20 to 0.34 at 3.

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
| CS, same-script cross-language | not run (owner option, decision 69 as revised): K1's five Latin pairs both directions | (3,450) | none; the CROSS_SCRIPT label is dropped |
| H2 cells | 2,000 unseen-stratum CX cells (SHA-256 order) with needle present and with needle absent | 4,000 multiple-choice units | H2 gate (decision 61) |

All 230 audit questions appear in every pair (crossed design). MN and CX of a
family share haystack, needle and position. English-needle contexts are
shared by all English-needle pairs. Multiple choice is K1's acc_norm; the
unnormalised and per-character variants are reported beside it. The
literal-free and pre-literal statistics (next section) reuse the captured
block scores of the same units; they add no prompt.

Directions. The seven English-needle pairs (needle and haystack English,
question English on MN and in the unseen script on CX) and the seven X-needle
pairs (needle and haystack in the unseen script, question in that script on
MN and English on CX) are read separately as well as together (decision 77).

Development pre-step units (development partition, 20 questions, dense only):
the 20 pairs' CX legs with multiple choice, their MN legs, ML for every needle
language, TR, needle-absent twins and no-haystack references for the CX
cells.

## Masking, the controlled set and the literal checks

Literal rules (model-free, computed when the bundle is built):

- Exact rule E (content tokens): LEX's rule from the dense pre-check (not
  among the 100 most frequent token ids of the development haystack of the
  needle language or the query language, and decoding to text with a letter
  or digit), in the Qwen3.5 tokenizer.
- Near rule F (decision 75): a token is a near-literal match to a question
  when the word holding it shares a character n-gram with a content word of
  the question but no content-token id: n is 4 code points in scripts written
  with spaces between words and 2 in ja, ko, th, km and zh; n-grams made only
  of digits or punctuation, and the 200 most frequent n-grams of the
  development haystack of that language, do not count. It catches inflection,
  different subword splits and close paraphrase that rule E misses (the
  verifier's paraphrase caveat).
- A block is a literal block of a leg when it holds an E or F match to that
  leg's question. On CX legs there are almost none (E2: overlap 0.00 to 0.04).

Evidence sets and the primary mask:

- Overlap mask M (unchanged), per family f: O_f is the set of content-token
  ids that the needle shares with the MN question or with the CX question.
  Every needle token in a 4-token block containing a token of O_f is masked.
  N^M_f is the unmasked needle tokens; masked recall is |S ∩ N^M_f| / |N^M_f|.
  The same mask applies to both legs of the family and to every selector. The
  masked random baseline is the analytic expectation over N^M_f. A family
  with |N^M_f| below 32 tokens is excluded and counted (decision 49).
- Literal-free instrument LF (decision 74), radius r = 2 blocks. Evidence
  N^LF_f: needle tokens farther than r blocks from every needle block holding
  an E or F match to either question. Candidates on each leg: every block
  except the sink, the needle blocks within r of such a match, and every
  context block within r of a literal block of that leg's question. Both
  selectors (indexer and target) and every reference choose their top 256
  blocks among the same candidates, so the competition for the budget by
  literal blocks and their neighbours (displacement) and the literal identity
  carried into the next blocks (local spill) are both outside xi^LF by
  construction. The random baseline is the analytic expectation over the
  candidates.
- Pre-literal evidence PRE (decision 76 as revised under D52). Evidence
  N^PRE_f: the needle tokens in the complete blocks before the first needle
  block holding an E or F match to either question; candidates as for LF.
  The question comes after the needle and the model is causal, so no needle
  token's key can carry a needle literal match that comes later in the
  passage; PRE is free of spill from the needle's own literal matches at any
  range, which LF is not beyond r. PRE is pooled: within each pair, every
  family with at least one complete pre-literal block enters, weighted by
  |N^PRE_f| (a token-weighted mean with no per-family minimum), and xi^PRE is
  the macro over pairs of the pooled pair means.
- Evaluability. A family enters xi^LF when |N^LF_f| is at least 32 tokens;
  if fewer than 60 percent of controlled unseen-stratum families qualify, r
  is set to 1 at the freeze. A family enters xi^PRE when it has at least one
  complete pre-literal block. The D48 rule that removed the PRE conditions
  when fewer than 40 percent of families had 32 pre-literal tokens is
  withdrawn (decision 76 as revised): on the development text it would have
  removed them, and with them GO's only guard against long-range spill. In
  its place a fixed rule can only take GO away: if the audit bundle's
  pre-literal tokens are fewer than 8 percent of its unmasked controlled
  unseen-stratum tokens, or any unseen pair has fewer than 20 families with a
  complete pre-literal block, GO is unavailable for this id (stated in the
  bundle before any model read; NEGATIVE, INCONCLUSIVE and the gates are
  unchanged).
- Development facts (decision 90; model-free, on the development partition,
  with the real Qwen3.5-4B-Base tokenizer, sha256 `fe000e3e...`, K1's split
  and the dense pre-check's anchor rule; stop lists proxied by the 100 most
  frequent ids and the 200 most frequent n-grams of the first 1,000
  documents of K1's haystack source of each language, the registered lists
  being built with the bundle; `compute/repair3-stage0-dev-facts.py` in the
  gauntlet bundle). 110 of the 224 development questions are controlled, in
  66 of the 122 links. Over the four block alignments of the 1,540
  controlled unseen-stratum families: 1.5 to 1.6 percent fall under the
  mask's 32-token rule; LF (r = 2) is evaluable for 0.67 (r = 1: 0.84 to
  0.85); the D48 per-family PRE rule (32 tokens) for 0.20 to 0.22 (0.29 to
  0.32 with exact matches only; median pre-literal evidence 5 to 8 tokens);
  the pooled PRE for 0.53 to 0.67 of families, holding 17 percent of the
  unmasked tokens, and at alignment 0 every unseen pair has a complete
  pre-literal block in at least 0.64 of its families (ja>en the lowest).
  With 200 or 400 stop ids the per-family share rises to 0.29 to 0.31 and
  0.40 to 0.41 (E and F), which shows how much the stop list matters; the
  registered list is the bundle's.
- Entity-controlled set: a question is anchored when its English wording
  contains a capitalised word (not the first word, not "I") or a digit run
  that also occurs in the English passage (the dense pre-check's model-free
  rule). Controlled families are those of unanchored questions. The rule is
  applied to the audit text when the bundle is built, before any model read.

Literal references (selectors evaluated on every leg, masked and unmasked):

- LEX, the dense pre-check's literal selector (exact-rule count per block).
  Because the mask uses the same rule, LEX scores zero on every block of N^M,
  so its masked statistic can show only displacement and the target's own
  gap (wave-1 identification refuter). It is descriptive: it reports the
  displacement density d (the share of LEX's MN budget outside the needle).
- LEXk, the kernel-literal selector, whose rule differs from the mask: a
  block's E count plus 0.5 times that of the block before it and 0.25 times
  that of the block two before. It scores unmasked needle blocks that follow
  a literal match, so it carries a positive literal channel by construction.
  It is the positive control of the literal check (pre-step item 3) and the
  literal selector of the floor check (item 5).
- The literal-leaning null family N_lambda: the top 256 blocks of the
  target's natural-log block score plus lambda x s_row x LEXk, where s_row is
  the SD of the target's natural-log block scores over the blocks of that
  query row, for lambda in {0.25, 0.5, 1, 2, 4}; no noise, no seed. It is the target tilted toward
  literal matches and the blocks after them, at increasing strength.
- Spill profile (descriptive): masked recall of indexer, target, LEXk and
  N_lambda on unmasked needle blocks binned by forward distance from the
  nearest preceding literal block (PRE, 1 to 2, 3 to 5, 6 or more blocks), on
  both legs. The wave-1 dilated mask is superseded by LF.

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

Directions and components (decision 77): xi^M_T,E and xi^M_T,X are the same
statistic over the seven English-needle and the seven X-needle pairs, so
xi^M_T = (xi_E + xi_X) / 2, and alpha_T = (xi_E − xi_X) / 2. Under an additive
model of the indexer's excess loss, with gamma for a question in a different
script from the passage, alpha for a question in an unseen script and beta
for a passage in an unseen script, the English-needle direction reads
alpha + gamma, the X-needle direction gamma − alpha, and beta cancels within
every family. xi^M_T therefore estimates gamma (the H_loc estimand) and
alpha_T the query-script component, which opposite-signed directions would
otherwise cancel in the macro. The needle-script component beta is reported
through G^M(MN) by direction (descriptive). The additive reading is an
assumption (decision 86). If question-side and passage-side deficits combine
multiplicatively (the indexer keeps a factor r_q of its target's headroom on
a question in an unseen script and r_p on a passage in one), the macro is
about 0.85 H (1 − r_q)(1 − r_p) / 2 with no mismatch component, the X-needle
direction is negative and the log-retention co-statistic below is zero; a
loss that saturates at the random floor behaves the same way. GO therefore
needs the excess in both directions and on both scales; NEGATIVE's
two-sided bands on both directions hold without the additive assumption.

Literal-free and pre-literal statistics (decisions 74 and 76): xi^LF_T is
xi^M_T recomputed on the LF evidence and candidates over families with
|N^LF| of at least 32 tokens; xi^PRE_T is the pooled statistic (Masking).
Each has its own combined interval: the passage-cluster bootstrap of its
weighted pair-cluster sums and the layer-resolved seed term of its own
per-layer, per-seed contributions.

Direction floor (decision 87): G^M(MN) on the controlled unseen-stratum
families of each direction (the seven English-needle and the seven X-needle
pairs), with its 99 percent percentile cluster-bootstrap lower bound.

Log-retention co-statistic (decision 86): xi_log^M_T = macro over the 14
unseen pairs of log G^M(MN) − log G^M(CX), with G^M on pair-condition means
floored at 0.05. Its interval is the combined interval, with the bootstrap of
the replicate statistic (replicate headroom floored as for xi_rel) and the
layer-resolved seed term of the delta-method contributions (each layer's and
seed's contribution to G divided by the point G). Under multiplicative
question-side and passage-side deficits with no mismatch component it is
zero while xi^M is positive; under an additive mismatch excess it is
positive.

Per-layer co-statistic (decision 58 as revised): xi_rel^M_T,l = macro over
unseen pairs of G_l(MN) − G_l(CX), where G_l uses layer l's recall and layer
l's own target and random means. A layer is testable when its masked target
headroom (macro over unseen pairs) is at least 3 points on both legs and
every pair's is above 1 point; other layers are listed as UNTESTABLE.

Interval: K1's combined interval with a layer-resolved seed term (decision
78). se_cluster is the SD of a passage-cluster bootstrap over the audit links
that hold at least one controlled question (B = 10,000, NumPy seed 42, macro
inside each replicate, seeds fixed). Every registered statistic is linear in
the per-layer recalls of each seed's indexer (xi_rel with its point
denominators fixed), so it is the sum over the eight layers of per-layer,
per-seed contributions c_l,s. Each layer's indexer starts from its own
generator (SHA-256 of seed, layer and target) and is trained only on its own
layer's KL against a frozen backbone, so seed deviations are independent
across layers. The seed variance of the seed mean is
V_seed = sum over l of var_s(c_l,s) / 3, with Satterthwaite degrees of freedom
(sum of v_l)² / sum of (v_l² / 2), v_l = var_s(c_l,s) / 3: up to 16 instead of
K1's 2. The 99 percent interval is point ± t(0.995, df) x
sqrt(se_cluster² + V_seed) with Welch-Satterthwaite df (cluster term df =
clusters − 1). K1's estimator (the SD of the three per-seed values, df 2), the
percentile interval, df and the per-seed and per-layer values are reported
beside it. For a per-layer statistic the seed variance is pooled over the
eight layers (df 16) and scaled by that layer's headroom; this is the safe
direction for a veto (a layer noisier than the pool fires more often, not
less). A CR2 cluster-robust interval with Satterthwaite df is reported beside
the decision interval (descriptive).

Floor: G^M(MN) and the unmasked G(MN) on controlled unseen-stratum families,
each with its 99 percent percentile cluster-bootstrap interval.

## Validity gates

- V1 adequacy, per target, at every seed: English ML R_ind at least
  R_T(ML) − 5.
- V2 bug tell (decision 60): for some target, the seed-mean English ML
  difference R_ind − R_T(ML) has a 99 percent passage-cluster lower bound above
  +1 point. HOLD, terminal for this id (D16).
- V3 integrity: K1's (finite values, selection at most 1,027 tokens, every
  unit exactly once, digests verified), plus the mask, LF, PRE and
  controlled-set digests, and the 24 initialisation generator digests per
  target (8 layers x 3 seeds) all distinct (decision 78's independence
  premise).
- V4 null calibration on the audit read, per target: at every audit sigma
  whose null passes V1 at every seed, seed-mean |xi^M| and |xi^LF| at most 2
  points and |xi_rel^M| at most 0.10 (the block-score null of the dense
  pre-check, on the masked controlled statistic). A target that fails V4 can
  be neither GO nor NEGATIVE; the verdict is then INCONCLUSIVE with the label
  NULL_OFF_CENTRE (decision 59).
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
2. Literal check, specificity (replaces wave 1's LEX gate, decision 74): at
   every reaching sigma of item 4, the block-score null's seed-mean
   |xi^M − xi^LF| is at most 1.5 points and |xi^LF| at most 2, for both
   targets. A noise-only selector must not look literal.
3. Literal check, sensitivity (positive controls), on controlled
   unseen-stratum families: (a) LEXk's MN recall of unmasked needle blocks one
   or two blocks after a literal block exceeds its MN recall of PRE blocks by
   at least 10 points (the spill profile sees a selector with a positive
   literal channel); (b) LEXk's LF recall equals the LF random baseline within
   1 point on both legs (LF holds no literal neighbourhood); (c) for both
   targets, at every lambda at which the literal-leaning null N_lambda has
   |xi^M| of at least 5, its |xi^M − xi^LF| is above 2.5 (the check sees a
   literal channel large enough to matter). The largest |xi^M| of N_lambda
   over lambda is reported as the development size of the literal channel. A
   failure is an implementation fault or an instrument that cannot see the
   channel; either stops the id.
4. Null calibration on the 17-sigma grid, masked and controlled: at every
   sigma whose null passes V1 at every seed, seed-mean |xi^M| at most 2 and
   |xi_rel^M| at most 0.10, and at least two such sigmas (the reaching sigmas)
   with a seed-mean English ML loss between 2.5 and 5 points, for both
   targets.
5. Floor viability: at two or more reaching sigmas, the null's controlled
   G^M(MN) and G(MN) 99 percent lower bounds are at least 0.5; LEXk's
   controlled G^M(MN) point is below 0.5 (wave 1 used LEX, whose masked G is
   at most 0 by construction, so the check was vacuous).
6. Seen stratum: a seen language whose masked controlled CX headroom point
   (hs) is below 20 is dropped from the stratum (both its pairs) and
   reported; at least two of th, hi and km must remain.
7. Mask coverage: at most 25 percent of controlled unseen-stratum families
   excluded for |N^M| below 32 tokens.
8. TR: a TR language whose masked TR headroom point is below 10 is dropped
   from the descriptive TR contrast (not a stop).
9. Literal-free sensitivity (decision 89), for both targets on controlled
   unseen-stratum families: a CX-only, non-literal degradation is injected
   into the dense target (its natural-log block scores on CX legs plus
   Gaussian noise, three seeds, MN legs untouched, at the smallest sigma of
   the 17-sigma grid at which the degraded target's seed-mean xi^M is at
   least 5 points); its xi^LF and pooled xi^PRE are each at least 0.5 of its
   xi^M; and the masked target headroom on the LF and on the PRE evidence (CX
   leg; H1^LF and H1^PRE) is at least 10 points. The ratios are recorded as
   kappa_LF and kappa_PRE. The development text bounds them model-free at
   0.74 to 0.77 (LF) and 1.15 to 1.17 (pooled PRE) when a loss sits only on
   the question's answer sentence, and at 1 when it is spread evenly. A
   failure means that the literal-free evidence cannot see a cross-script
   loss of the kind GO claims, and stops the id.

Recorded at the pre-step, not gated:

- H_ref,T, the masked controlled unseen-stratum H1_CX point of target T, which
  sets that target's xi_rel NEGATIVE limits (decision 79);
- per-layer masked target headroom on both legs, and the list of UNTESTABLE
  layers for the per-layer veto (decision 58 as revised);
- the evaluable shares of LF and PRE and the pooled PRE token share on the
  development partition (H1^LF and H1^PRE are gated, item 9);
- development H2a and H2b (the combined read moved the H2 test to the audit
  read).

## H2 gate (dense only, audit, before any indexer is trained)

2,000 unseen-stratum CX cells, each scored with the needle present and with
the needle absent (4,000 multiple-choice units). If H2a or H2b fails, the
final verdict is UNINTERPRETABLE and no indexer is trained. Otherwise
PROCEED_TO_K1. The audit read never recomputes H2 (decision 61). The pass
probability is about 0.42 to 0.57 when the uncertainty of the development
point is integrated (skeptical and flat priors), not the 0.69 plugged in at
the development point in wave 1 (repair simulation `repair-h2-predictive`).

## Decision rules (main read)

- GO: some target T with xi^M_T at least 10; the combined 99 percent lower
  bounds of xi^M_T, xi_rel^M_T and xi_log^M_T above 0 (decision 86); the
  literal-free and pooled pre-literal points xi^LF_T and xi^PRE_T both at
  least 5 (decisions 74 and 76); both directions, xi^M_T,E and xi^M_T,X each
  at least 5 with each 99 percent lower bound above 0 (decision 77 as
  revised); the direction floor, the 99 percent lower bounds of G^M(MN) in
  each direction at least 0.5 (decision 87); V1 to V4 passing for T; and H1^M
  at least 10. A target that meets the xi^M_T, xi_rel^M_T, V and H1^M
  conditions but fails another is INCONCLUSIVE with the label
  LITERAL_CHANNEL (LF or PRE), DIRECTION_SPLIT (a direction), DIRECTION_FLOOR
  (the floor) or SCALE (the log-retention co-statistic); if the bundle's PRE
  coverage rule made GO unavailable (Masking), the label is GO_UNAVAILABLE.
  Labels (descriptive, all reported):
  - SEEN_TOO when the seen comparator's point is at least 5 for T;
  - UNSEEN_SPECIFIC when Delta_xi is at least 5 and the seen point is below 5;
    secondary test, read only after a GO: Delta_xi's 99 percent lower bound
    above 0, for the three seen languages as fixed (decision 82);
  - QUERY_SCRIPT when |alpha_T| is at least 5 (the excess depends on the
    question's script more than on the mismatch);
  - SCRIPT_ONLY when the TR contrast's point is at least 5 (decision 57).
- NEGATIVE (two-sided; decisions 58, 77 and 79): for both targets, all of
  - xi^M_T inside the band: |point| at most 5, the combined 99 percent
    interval inside (−10, 10) and half-width at most 5;
  - xi_rel^M_T inside its band: |point| at most tau1_T and the 99 percent
    interval inside (−tau2_T, tau2_T), with tau1_T = 5 / H_ref,T and
    tau2_T = 10 / H_ref,T (decision 79);
  - the floor: the 99 percent lower bounds of controlled G^M(MN) and of
    controlled G(MN) both at least 0.5;
  - the literal checks: |xi^LF_T| and |xi^PRE_T| each at most 5 (points);
  - V1 to V4 passing; H1^M at least 20;
  and the robustness conditions, all two-sided:
  - directions: |xi_E| and |xi_X| each at most 5 (points), and the
    English-needle direction (its MN leg wholly in seen text) with its own 99
    percent interval inside (−10, 10);
  - the seen comparator's |point| at most 5;
  - no testable layer whose |xi_rel^M_T,l| is at least 0.2 with its 99
    percent interval excluding 0 (UNTESTABLE layers are named in the
    NEGATIVE's scope; a 95 percent veto was simulated and rejected, see
    decision 58).
  If every NEGATIVE-region condition holds except a robustness or literal
  condition, the verdict is INCONCLUSIVE with the label QUERY_SCRIPT,
  DIRECTION_OPPOSED, SEEN_EXCESS, LAYER_CONCENTRATED or LITERAL_CHANNEL; an
  xi^M_T below −5 is labelled REVERSED.
- UNINTERPRETABLE: H1^M below 10 on the audit read (H2 is decided by the H2
  gate).
- HOLD: a V2 bug tell (decision 60). Terminal (D16).
- VOID: a V3 integrity failure.
- V1 extension: K1's rule (one registered extension, epochs 2 and 3, only the
  V1-failing targets, mandatory when called, INCONCLUSIVE if not run or void).
  The extension re-reads only the decision legs (CX, MN, ML, with the M, LF
  and PRE evidence); the TR rows of re-read targets are not reported
  (decision 65).
- INCONCLUSIVE: everything else, including a disagreement between the xi and
  xi_rel classifications and any half-width above 5.
- Order: VOID, HOLD, UNINTERPRETABLE, V1_EXTENSION_REQUIRED, GO, NEGATIVE,
  INCONCLUSIVE, as in K1; a target failing V4 is treated like a target in
  neither region.
- Multiplicity: two targets at 99 percent each, as in K1. Strata, layers,
  directions, alpha, TR, LF, PRE, unmasked and covariate rows are descriptive
  and uncorrected, except where a GO or NEGATIVE condition uses them; a
  condition that can only block a verdict adds no false-positive risk to it.
  The one secondary test (decision 82) is read only after a GO.
- Scope of a NEGATIVE, stated in the verdict: weak alignment (haystack in the
  needle's language, R5), Stage-1 KL-only indexers with bilingual exposure,
  the testable layers only, and the needle-script component beta outside the
  claim (reported).

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
- Seed SD per target, before any remedy arm: the sealed development seed read
  (decision 80), and on the audit read the layer-resolved and K1 estimators
  with their df, the per-layer per-seed contributions and the correlation of
  seed deviations across layers (a check of decision 78's premise).
- The literal block: LEX, LEXk and N_lambda on every leg (M, LF, PRE), the
  displacement density d, the spill profile, xi^M − xi^LF and xi^M − xi^PRE
  with intervals.
- Directions: xi_E, xi_X and alpha_T with intervals; G^M(MN) by direction
  (the needle-script component beta).
- Per-layer xi^M and xi_rel^M with intervals, testable or not.

## Seeds, sample sizes and sensitivity

- Seeds 42, 43, 44 set indexer initialisation only. Stream order, the passage
  split, prompts, cell samples and the bootstrap use seed 42 or SHA-256
  orders.
- Audit counts: 3,220 unseen-stratum families and 1,380 seen-stratum families
  over 122 links; about half are controlled on the development rate (0.50,
  Wilson 0.30 to 0.70), and the exact audit count is a bundle fact fixed
  before freeze.
- Repair simulation S3 (`compute/repair3-decision-sim.py` in the gauntlet
  bundle; it imports S2, `compute/repair-decision-sim.py`, whose statistics
  agree with the registered K1 module to 6e-15, and its own weighted pair
  statistics agree with S2's to 3e-14). S3 replaces S2's assumed inputs with
  measured or bounded ones: controlled questions clustered by passage as on
  the development text (113 controlled audit questions in 67 links, against
  S2's 115 in 89); every family's |N^M|, |N^LF| and |N^PRE| taken from a
  development family of the same pair; xi^LF and the pooled xi^PRE computed
  as statistics with nested-sampling noise (S2 used xi^M plus N(0, 0.4) and
  N(0, 0.8)); the sensitivity kappa at the measured answer-sentence bound
  (LF 0.74, PRE 1.0) unless stated; and multiplicative and floor-saturating
  generators beside the additive one. 400 reads per cell (800 for the
  identification rows), bootstrap B = 1,000, cluster se of xi about 1.4.
  P(verdict) over both targets with every condition of this file:
  - no excess, three seeds: P(NEGATIVE) 0.65 / 0.60 / 0.71 at masked headroom 20 / 30 / 40 and seed SD 1; 0.43 / 0.30 / 0.31 at seed SD 2; 0.03 / 0.01 / 0.02 at seed SD 3; with the seed top-up (five seeds) 0.71 / 0.66 / 0.73, 0.59 / 0.56 / 0.55 and 0.34 / 0.21 / 0.20;
  - an input excess of 12 (realised mean xi 9.1 / 9.7 / 9.9): P(GO) 0.32 / 0.51 / 0.58 at seed SD 1; of 15: 0.85 / 0.94 / 0.95; of 10: 0.04 / 0.15 / 0.18; P(GO) is at most 0.01 at 7.5 and 0 at 5;
  - false GO (P(GO), this file against the D48 draft as it would freeze, PRE removed by its 40 percent rule): long-range spill of +10 with no excess 0.00 against 0.23 (0.01 against 0.23 at H 40); spill of +15, 0.01 against 0.99; a true excess of 5 plus spill of +6, 0.12 against 0.46; multiplicative question-side and passage-side deficits with no mismatch, r 0.2 at H 40, 0.00 against 0.71, r 0.35, 0.00 against 0.05; a floor-saturating additive deficit (25 and 25 points at H 40), 0.00 against 0.06;
  - what GO's new conditions cost (P(GO), against the D48 draft with PRE removed): input excess 12 at the measured kappa bound 0.52 against 0.54; at S1's concentrated kappa (0.68, 0.53) 0.31 against 0.51; an excess of 12 plus a question-script deficit of 6, 0.37 against 0.50 (DIRECTION_SPLIT); a multiplicative mismatch alternative (r_m 0.5) 0.69 against 0.72;
  - false kills (P(NEGATIVE), H 30, seed SD 1): question-script excess 6, 0.09; a total failure at layer 3 only, 0.26; a true excess of 10 hidden by displacement −8, 0.00; 7.5 with displacement −4, 0.04; 8 with displacement −4 at S1's concentrated kappa, 0.05; 7.5 under long-range anti-spill, 0.01; a seen-stratum excess of 8, 0.04. A needle-script deficit (beta 10, or a multiplicative r_p of 0.3) reaches NEGATIVE in 0.66 of reads by design: it lies outside the claim and is reported;
  - cluster noise: at a cluster se of xi of 0.89, P(NEGATIVE | no excess) 0.93 and P(GO | input 12) 0.96; at 1.90, 0.04 and 0.08;
  - sigma_star: P(NEGATIVE | no excess) is near 0.5 at a seed SD of about 1.5 with three seeds and about 2.2 with five, which sets sigma_top = 1.5 and sigma_star = 2.2 (decisions 80 and 81 as revised).
- Repair simulation S2's figures (wave 2) are superseded: they assumed 89
  clusters, xi^LF and xi^PRE nearly deterministic given xi^M, kappa 1.0 and
  0.87, and an additive generator.
- H2b (development ICC 0.138): plugged in at the development point of 8.6,
  P(pass) is 0.24 with K1's 300 cells, 0.68 with this file's 2,000, 0.74 with
  all 3,220 unseen CX cells and 0.98 with 2,000 audit plus 2,000 primary
  cells; integrated over the development uncertainty it is 0.42 to 0.57,
  0.45 to 0.59 and 0.61 to 0.69 (skeptical to flat prior;
  `compute/repair-h2-predictive.py`).
- The literal bound (simulation S1, `compute/repair-literal-channel-sim.py`):
  across 18 scenarios and 42 literal tilts, xi^LF's literal bias lies within
  −0.26 to +1.11 points and xi^PRE's within −0.57 to +0.16 when spill reaches
  one block, and within −2.86 to +10.01 and −4.42 to +0.92 when it reaches
  three; xi^M's within −8.65 to +11.52. Because PRE is now always a GO
  condition, a GO needs a pooled pre-literal excess of at least 5 points,
  which no simulated literal tilt reaches (PRE's upward bias is at most
  0.92); the bound is on the pre-literal evidence, which kappa_PRE (pre-step
  item 9) relates to the excess on the masked evidence.
- The registered pre-freeze simulation (decision 62 as revised) replaces
  these figures before the freeze.

## Compute

Limits: K1 v2's formula, max(5, ceil(1.2 x 1.15 x P + 3)) minutes, cap =
GPUs x limit / 60, with P projected from the 4B probe's rates. The 8 GPU-h
count is the sum of caps of every job, the extension at its worst case and
the probe included (D22). The design is not cut to fit (D20); admission over 8
GPU-h is Kevin's (D24).

Synthesis projection before any probe (rates from K1 v2 probe 543 and lane
862, scaled to 8 layers, hidden size 2,560 and native 8,192-token contexts;
repair additions: +5 percent on every selection unit for LF and PRE, +3
percent on the pre-step's selection units for LEXk and N_lambda, the sealed
development seed read inside the main job, CS legs not run; central / high;
`compute/repair-cost-model.py`, which reproduces the wave-1 7.21 / 9.79):

| Job (1 GPU each) | Projected minutes | Limit (min) | Cap (GPU-h) |
|---|---|---|---|
| q3-k1-v3-throughput-probe-v1 | | 15 | 0.25 |
| smoke | 7.8 / 9.6 | 14 / 17 | 0.24 / 0.29 |
| development pre-step | 17.4 / 25.2 | 28 / 38 | 0.47 / 0.64 |
| H2 gate | 37.8 / 55.6 | 56 / 80 | 0.94 / 1.34 |
| resume R0, R1, R2 | 9.4, 6.5, 7.0 / 12.1, 7.9, 8.5 | 16, 12, 13 / 20, 14, 15 | 0.69 / 0.83 |
| main (with the sealed seed read) | 93.1 / 130.8 | 132 / 184 | 2.20 / 3.07 |
| V1 extension or seed top-up (exclusive slot, worst case: the extension) | extension 91.5 / 129.5; top-up 72.1 / 97.8 | 130 / 182 (top-up 103 / 138) | 2.17 / 3.04 (top-up 1.72 / 2.30) |
| Total | | | 6.96 / 9.46 |

Third-repair changes (`compute/repair3-cost-model.py`): pre-step item 9
reuses the captured scores (+2 percent on the pre-step's selection units);
the pooled PRE, the log-retention co-statistic and the direction floor add
nothing; the seed top-up shares the extension's slot (exclusive), so the total
of caps rises only by the pre-step's 0.02 GPU-h.

Expected use: about 0.5 to 0.7 GPU-h if the pre-step stops, 1.2 to 1.6 if the
H2 gate stops, 3.1 to 4.3 without the extension or a top-up, plus 1.5 to 2.2
with the extension or 0.45 to 0.65 with a top-up. The central projection is
under 8 GPU-h and the high one is not; the V1 extension's worst case (2.17 /
3.04) is what crosses the line. Owner options and their caps: CS restored
+0.44 / +0.57; five seeds at every learning rate +0.91 / +1.34 (the top-up
gives five seeds at the frozen rate without new caps); all 3,220 unseen CX
cells in the H2 gate +0.48 / +0.75; decision 64 (primary H2 cells) about
+0.8 / +1.2.

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
- the near rule's n-gram stop lists, and per family the E and F literal
  blocks of each leg, |N^LF| and |N^PRE|, the LF evaluable share that fixes
  r, the pooled PRE coverage (families with a complete pre-literal block and
  the PRE token share, per pair) that decides whether GO is available
  (decisions 74 to 76), and the MN haystack's literal block count by
  language (the displacement exposure);
- the answer-sentence proxy's share of the M, LF and PRE evidence (the
  model-free kappa bound of decision 89), and the controlled links per
  partition;
- the TR alignment check: for every audit and development (link,
  question_number) of bn and hi, the Latin passage exists, its digit runs and
  sentence count equal the native passage's, and its question is never used
  (decision 57);
- unit counts and query rows per leg.

## Freeze procedure

1. Build the bundle and record its facts (CPU). Fix the fertility-matched
   pairs (decision 56), r and GO's availability (decisions 74 to 76).
2. Run the registered pre-freeze simulations with the v3 statistics code
   (decision 62 as revised) and replace the repair-pass figures above; the
   repair simulation's generator and K1-code validation are the template.
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
| Combined read 1 (D26) | a seen-script cross-script condition | seen stratum th, hi, km (Evaluation; decision 48); pre-step item 6; two-sided NEGATIVE robustness condition; GO labels and the secondary UNSEEN_SPECIFIC test |
| Combined read 2 (D26) | an entity-controlled question set | controlled set (Masking); decision 53 |
| Combined read 3 (D26) | a new experiment id and the research gauntlet | this id; the K1 v3 gauntlet |
| Combined read 4 (D26) | the non-literal floor, controlled G(MN) 99 percent lower bound at least 0.5 | NEGATIVE floor, on unmasked G(MN) and on masked G^M(MN) |
| Combined read 5 | GO and NEGATIVE computed on the entity-controlled set | primary statistic and floor are controlled-family statistics |
| Combined read 6 | anchor masking or a lexical-overlap covariate | overlap mask (a superset of anchor masking); covariate reported, descriptive only (decision 63) |
| Combined read 7 | H2 re-tested under K1's bounds on the audit read | H2 gate on 2,000 audit cells, K1's bounds (decision 61) |
| Verifier caveat 1 | the lexical confound comes from same-language paraphrase | overlap mask on all shared content tokens; near rule F for inflection and paraphrase; LF and PRE literal-free statistics as conditions of both verdicts; TR leg with zero shared tokens; positivity report (wave 1's two-sided LEX check is replaced, decision 74) |
| Verifier caveat 2 | CENTRED and VIABLE passed by 0.019 to 0.067 points | 17-sigma grid, two reaching sigmas required, re-measured on the masked instrument at the pre-step, audit null as validity gate V4 for both GO and NEGATIVE |
| Verifier caveat 3 | fertility follows needle language on both legs | native 8,192-token contexts remove context-length variation by language; fertility-matched seen-unseen contrasts; TR changes fertility at fixed language and content; claims at language level stay descriptive |
| D48 (1) | a literal check that can see a positive literal channel, with its bound derived and simulated | LF and PRE statistics as GO and NEGATIVE conditions (decisions 74, 76); near rule (75); LEXk positive control, N_lambda family and the spill profile (Masking section; pre-step items 2 and 3); bound in the proposal's Mechanism section from simulation S1 |
| D48 (2) | a two-sided NEGATIVE region; vetoes meaningful where headroom is small | NEGATIVE band on xi^M, xi_rel, xi^LF and xi^PRE; two-sided directions with the English-needle direction gated; seen comparator two-sided; per-layer co-statistic veto on testable layers (decisions 58 as revised, 77, 79) |
| D48 (3) | seed variance handled | layer-resolved seed term (decision 78), sealed development seed read with sigma_star (decision 80), owner option of five seeds (81); simulated over seed SD 0.5 to 4 (S2) |
| D48 (4) | the other wave-1 defects | CS dropped (69 revised), H2 stated predictively (85), mechanism statement corrected (84), xi_rel limits scaled to headroom (79), UNSEEN_SPECIFIC secondary test (82), LEXk in the floor check (54 revised), decision 62 widened |
| D52 (1) | GO's guard against long-range spill evaluable where GO reads, or GO gated on a measured spill bound; evaluability computed on the development text | pooled PRE in every family with a complete pre-literal block (decision 76 revised), the D48 40 percent fallback withdrawn and replaced by a rule that can only remove GO; development facts with the real tokenizer and proxy stop lists (decision 90; Masking); sensitivity of LF and PRE gated at the pre-step (item 9, decision 89) |
| D52 (2) | GO's agreement across the two directions and a floor | both directions at least 5 with lower bounds above 0 (decision 77 revised); direction floor (decision 87) |
| D52 (3) | the additivity the decision simulation assumes | log-retention co-statistic as a GO condition (decision 86); S3 simulates multiplicative and floor-saturating generators (decision 88) |
| D52 (4) | the simulation's hard-coded literal sensitivities and noise, and its cluster count | S3: measured evidence sizes, LF and PRE as statistics, kappa at the measured bound, 67 clusters from the development link profile (decision 88) |
| D52 (5) | the screen's low chance of a verdict | seed top-up in the extension's slot at no new caps (decision 81 revised); the chance stated from S3 and the gates (proposal) |

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
    "permissive floor" note. As revised under D48: the pre-step's literal
    check of the floor uses LEXk, whose masked G can be positive; wave 1 used
    LEX, whose masked G is at most 0 by construction (reviewer 1).
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
58. Per-layer and per-direction vetoes on NEGATIVE, two-sided (revised under
    D48). Reason: the target's own MN-minus-CX gap sits at layers 3 and 31
    (4.37 and 5.07 points against -0.86 to 0.96 in layers 15 to 23), and
    macro averaging halves a one-direction effect. Wave 1's layer veto (xi^M
    of at least 10 with a lower bound above 0) could not fire at layer 3,
    whose CX headroom is 8.68 points; the revised veto reads the per-layer
    co-statistic with the layer's own denominators, on layers with at least
    3 points of masked headroom on both legs, at |point| 0.2 with a 99
    percent interval excluding 0. In the repair simulation (S2, H 30, seed
    SD 1) a total cross-script failure confined to layer 3 leaves
    P(NEGATIVE) at 0.34 with this veto, against 0.73 under wave 1's rule; a
    95 percent veto would cut it to 0.06 but costs P(NEGATIVE | no excess)
    0.32 at H 20 and 0.20 at seed SD 2, so it was not chosen. Wave 1's
    direction veto was one-sided;
    the revised one bounds both directions' points and gates the
    English-needle direction on its own interval (decision 77).
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
62. Pre-freeze simulations with the v3 statistics code (revised under D48):
    cluster SDs 6, 10 and 13.4 and the measured effective clusters; seed SD
    of xi 0.5, 1, 2, 3 and 4; masked headroom 20, 30 and 40 and the measured
    H_ref; both targets with xi_rel; the direction components; the seen
    comparator; per-layer vetoes on the measured per-layer headroom; the
    literal channels at S1's tilts; HOLD under decision 60; H2b with the
    predictive integration. They must reproduce the repair simulation's
    validation against the K1 statistics module, and their results replace
    the repair-pass figures in "Seeds, sample sizes and sensitivity".
63. The lexical-overlap covariate is descriptive only, with a positivity
    report. Reason: no common support between legs (Miller and Chapman 2001;
    Crump et al. 2009).
64. Owner option, not adopted by default: release 2,000 primary-partition CX
    cells for dense-only H2 (no indexer read). Effect: P(H2b passes | 8.6)
    0.69 to 0.98, caps +0.80 / +1.21 GPU-h. Cost: departs from K1's "primary
    never read" and from the letter of requirement 7.
65. The V1 extension re-reads decision legs only. Reason: saves about 0.6 GPU-h
    of worst-case cap; TR is descriptive (CS is not run, decision 69).
66. A 4B throughput probe under its own id (cap 0.25) sets every limit, as K1
    v2's did. Reason: the 4B training path has never run; the synthesis
    projection's high and central step times differ by 1.65 times.
67. The probe gates teacher determinism (two identical forwards bit-equal in
    captured queries, keys and layer inputs). If it fails, this file is not
    frozen as drafted.
68. Learning-rate grid kept (D20). Single-rate fallback (caps 6.61 / 8.85) is
    not registered.
69. CS not run (revised under D48; wave 1 kept them as descriptive rows).
    Reason: the CROSS_SCRIPT label subtracted a stratum of five Latin-script,
    low-fertility languages, so it mixed script with fertility and
    familiarity (wave-1 reviewer 1 and identification refuter); the seen
    stratum and TR carry the script attribution; dropping the legs saves
    0.44 / 0.57 GPU-h of caps, which pays for the repair's additions. Owner
    option to restore them at that cost.
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

Decisions added by the repair under D48 (same day, single owner; each answers
a named wave-1 defect):

74. Literal-free instrument LF (r = 2 blocks) as a condition of both
    verdicts: GO needs xi^LF of at least 5, NEGATIVE |xi^LF| at most 5, with
    the pre-step's specificity and positive-control items in place of wave
    1's LEX gate. Reason: the mask and LEX share one token rule, so the wave-1
    gate saw only displacement and the target's own gap, could not see a
    positive channel, and could stop the id for reasons unrelated to the
    indexer (identification refuter, reviewer 1, feasibility refuter). In the
    block-level repair simulation (S1) LEX's masked xi is negative in all
    eighteen scenarios (−0.85 to −5.65), while the literal bias of xi^LF stays
    within −0.26 to +1.11 points for spill ranges up to one block, against
    −8.65 to +3.61 for xi^M.
75. Near rule F (character n-grams) beside the exact token rule. Reason: the
    verifier's caveat 1 (same-language paraphrase); exact ids miss
    inflection and different subword splits.
76. Pre-literal evidence PRE as a condition of both verdicts (GO needs
    xi^PRE of at least 5, NEGATIVE |xi^PRE| at most 5), with a coverage
    fallback fixed at the bundle build. Reason: spill beyond r (S1, range 3
    blocks) moves xi^M and xi^LF together by up to +10 points; causality
    keeps PRE within −4.42 to +0.92 in every S1 scenario.
77. Directions read separately; alpha = (xi_E − xi_X) / 2 reported; NEGATIVE
    bounds both directions' points and the English-needle direction's
    interval. Reason: a question-script deficit enters the two directions
    with opposite signs and cancels in the macro (identification refuter);
    under an additive model the macro is the mismatch component and alpha
    the question-script component.
78. Layer-resolved seed term in every interval (df up to 16), K1's estimator
    reported beside it; V3 checks the generator digests. Reason: K1's df-2
    seed term made NEGATIVE unreachable at a seed SD of xi of 2 (feasibility
    refuter, reviewer 1); per-layer indexers are independently initialised
    and trained on independent losses against a frozen backbone.
79. xi_rel NEGATIVE limits tau1 = 5 / H_ref and tau2 = 10 / H_ref per target,
    H_ref the development masked controlled H1_CX point recorded at the
    pre-step. Reason: K1's 0.1 and 0.2 match its 5 and 10 points at a
    headroom of 50; at masked headrooms of 20 to 40 they bind before xi
    (feasibility refuter); the repair simulation (S2) puts P(NEGATIVE | no
    excess) at H 20 at 0.07 to 0.11 with the fixed limits.
80. Sealed development seed read inside the main job, before the audit read,
    with the stated bound sigma_star (2.0 points under D48; 2.2 with five
    seeds under D52, decision 81 as revised) and the
    NEGATIVE_REACHABILITY_LOW declaration. Reason: D48 (3); a measurement
    before any verdict, at about 2 GPU-minutes.
81. Owner option, not adopted: five seeds at every learning rate (+0.91 /
    +1.34 GPU-h of caps), or a conditional two-seed extension at the frozen
    rate triggered by the sealed seed read.
82. UNSEEN_SPECIFIC becomes a secondary test after a GO (Delta_xi's 99
    percent lower bound above 0, the three seen languages treated as fixed).
    Reason: the wave-1 novelty refuter asked for a decision-bearing
    identification device; it is read only after GO, so it adds no risk to
    the primary verdicts.
83. CS legs dropped (decision 69 as revised).
84. The mechanism statement no longer says that literal matching cannot
    favour either side; it says how the literal channels are measured.
    Reason: reviewer 1 and the identification refuter.
85. The H2 gate's pass probability is stated as a predictive range (0.42 to
    0.57), not the plug-in 0.69. Reason: the development point was selected
    (feasibility refuter, reviewers 1 and 2).

Decisions revised or added under D52 (each answers a named wave-2 defect):

62 (revised again). The pre-freeze simulations use simulation S3's inputs:
    controlled questions clustered by passage as in the bundle's link
    profile, per-family evidence sizes from the bundle, xi^LF and xi^PRE as
    statistics, kappa at the bundle's answer-sentence bound and at the
    pre-step's measured values, and additive, multiplicative and
    floor-saturating generators. Reason: S2 assumed 89 clusters (the
    development text gives 66), nearly deterministic LF and PRE, and an
    additive model (wave-2 reviewer 1 and the feasibility and identification
    refuters).
76 (revised). PRE is pooled over every family with a complete pre-literal
    block, token-weighted within pairs; the D48 40 percent fallback is
    withdrawn; a fixed coverage rule can only make GO unavailable. Reason: on
    the development text the per-family rule is met by 0.20 to 0.22 of
    families, so the fallback would have removed GO's guard against
    long-range spill and returned P(GO | spill +10, no excess) to 0.23 (wave-2
    feasibility refuter; S3).
77 (revised). GO also needs both directions: xi_E and xi_X each at least 5
    with each 99 percent lower bound above 0. Reason: question-side and
    passage-side deficits that combine multiplicatively, or saturate at the
    floor, make the macro positive with a negative X-needle direction
    (identification refuter; S3: P(GO) 0.71 to 0.00 at r 0.2, H 40).
81 (revised). The seed top-up (Learning-rate freeze) replaces the owner
    option: seeds 45 and 46 at the frozen rate when the sealed read's upper
    bound exceeds 1.5, in the V1 extension's slot, the two exclusive. Reason:
    D52's decisiveness item, without new caps.
86. Log-retention co-statistic xi_log as a GO condition (lower bound above
    0). Reason: it is zero under multiplicative question-side and
    passage-side deficits with no mismatch, where xi^M and xi_rel (both
    linear) are positive; GO then needs the excess on an additive and a
    multiplicative scale (C30, C51).
87. Direction floor as a GO condition (G^M(MN) 99 percent lower bound at
    least 0.5 in each direction). Reason: a selector collapsing towards
    random in one direction produces large differences without a mismatch
    deficit (wave-2 reviewer 1); the NEGATIVE's floor already required it on
    both directions pooled.
88. Simulation S3 (measured inputs) replaces S2 in "Seeds, sample sizes and
    sensitivity" until decision 62 runs with the v3 code.
89. Pre-step item 9: an injected CX-only, non-literal degradation of the
    dense target must show at least half of its masked excess on the LF and
    PRE evidence, and H1^LF and H1^PRE must be at least 10. Reason: the
    sensitivity kappa of the literal-free statistics was assumed (S2: 1.0
    and 0.87) and nothing measured it (identification refuter, reviewer 1).
90. The development facts (Masking) are recorded in the bundle of the
    gauntlet; the registered facts come from the v3 bundle build with the
    registered stop lists. Reason: wave 2 found that the zero-GPU facts the
    proposal listed had not been computed.
91. Residual R10 (query-side literal content) is part of the estimand, not a
    confound of it: the indexer and its target read the same query rows, so
    a selector that leans on literal-derived question content more than its
    target is the H_loc failure (wave-2 reviewer 1); the claim states it.

## Repair under D48 (changes against the wave-1 draft)

Wave-1 draft: sha256 `f4ce9a00f501f712247dd5ebb5964043c5f40d721c21db19c411475d3cce3b2c`
(commit d911d21). Every change below is in this file; the proposal's section
"Changes after wave 1" maps each to the reviewer or refuter who named the
defect and to the simulation that sizes it.

1. Masking section: near rule F; literal-free instrument LF; pre-literal
   evidence PRE; evaluability rules; LEX demoted to descriptive; LEXk,
   N_lambda and the spill profile added; dilated mask superseded.
2. Metrics: direction components and alpha; LF and PRE statistics;
   per-layer co-statistic; layer-resolved seed term.
3. Validity gates: V3 checks LF, PRE and generator digests; V4 also bounds
   the null's xi^LF.
4. Pre-step: wave 1's two-sided LEX gate (item 2) replaced by the
   specificity and positive-control items 2 and 3; the floor check uses
   LEXk; H_ref, per-layer headroom and LF and PRE coverage recorded.
5. Learning-rate freeze: the sealed development seed read.
6. Decision rules: GO adds xi^LF and xi^PRE of at least 5; NEGATIVE is a
   two-sided band on xi^M, xi_rel (limits scaled to H_ref), xi^LF and
   xi^PRE, with two-sided direction, seen and per-layer conditions; labels
   QUERY_SCRIPT, DIRECTION_OPPOSED, LITERAL_CHANNEL and REVERSED added;
   CROSS_SCRIPT removed; UNSEEN_SPECIFIC secondary test after a GO.
7. Legs: CS not run.
8. Compute: caps 6.94 / 9.46 GPU-h (wave 1 7.21 / 9.79).
9. Seeds, sample sizes and sensitivity: the repair simulation replaces the
   wave-1 approximations until decision 62 runs with the v3 code.
10. Decisions 54, 58, 62 and 69 revised; 74 to 85 added.

## Repair under D52 (changes against the wave-2 draft)

Wave-2 draft: sha256 `08fa52ca28898b8c99752d5e914d63a2068a276d5fb1da57ed4d1407916abdeb`
(commit fcb303d). Every change below is in this file; the proposal's section
"Changes after wave 2" maps each to the reviewer or refuter who named the
defect and to the evidence that sizes it.

1. Status: wave-2 outcome and the D52 repair.
2. Masking section: PRE pooled over every family with a complete
   pre-literal block (token-weighted within pairs); the D48 40 percent PRE
   fallback withdrawn and replaced by a coverage rule that can only make GO
   unavailable; the development facts recorded.
3. Metrics: the additive reading of the macro stated as an assumption; LF
   and PRE intervals computed on their own families and weights; the
   direction floor; the log-retention co-statistic.
4. Pre-step: item 9 (literal-free sensitivity, H1^LF and H1^PRE gated).
5. Decision rules: GO adds the log-retention lower bound, both directions
   (points at least 5, lower bounds above 0), the direction floor and the
   pooled PRE; labels DIRECTION_SPLIT, DIRECTION_FLOOR, SCALE and
   GO_UNAVAILABLE.
6. Learning-rate freeze: the seed top-up in the V1 extension's slot; sigma_top
   1.5 and sigma_star 2.2 with five seeds.
7. Seeds, sample sizes and sensitivity: simulation S3 replaces S2.
8. Compute: caps 6.96 / 9.46 GPU-h (wave 2 6.94 / 9.46); the extension and
   the top-up share one slot.
9. Bundle and freeze procedure: the pooled PRE coverage fixes GO's
   availability; the answer-sentence kappa bound and controlled links are
   bundle facts.
10. Decisions 62, 76, 77 and 81 revised; 86 to 91 added; traceability rows
    for D52.
