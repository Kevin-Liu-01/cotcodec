# Q3 K1 localization screen, successor (q3-k1-localization-screen-v2)

Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row
for the freeze time and `git_head_at_freeze`. The registered design is that of
`q3-k1-localization-screen-v1`, carried unchanged under program decision D20,
which accepts a change of code efficiency, limits and caps only; the limits
below are the registered formula applied to the `q3-k1-throughput-probe-v1`
receipt, and `program/decisions.md` records that receipt and those limits
before the freeze. No GPU job of this experiment runs before the freeze, and
every job verifies this file's digest against its ledger row at start-up.

## Relation to v1

`q3-k1-localization-screen-v1` was frozen on 2026-10-07 (ledger row
`c50540e9757289f152874dbd3833433539332df71004e87e80d9246dad3f3c4e`, file
SHA-256 `a0077d31dd250f621c82c2cdef2e80dfd8d3f7f4c356addfc0cbc241db51f79c`).
Its only GPU job, smoke job 452 (0.0403 GPU-h), passed every smoke gate and
reported SMOKE_PASS_OVER_BUDGET: it projected the main job at 98.8 minutes
(6.59 GPU-h), so 1.2 x 98.8 + 3 = 121.6 minutes against the fixed 30-minute
limit, and the main job could not run under that id
(`program/evidence/2026-10-07/q3-k1/`). No headroom pre-check, resume test, LR
freeze, audit statistic or verdict exists. Two causes: the per-indexer
training loop (5.69 ms per indexer, sequence and layer in the smoke, about
half of it kernel-launch and host-synchronisation overhead) and a projection
that counted the evaluation worker's 15.7 s start-up in its per-unit rate
(1.361 s instead of 0.533 s per unit). The design analysis and its adversarial
review (2026-10-07) chose this successor: the same registered design,
engineering only, measured first.

This file copies v1's registered science verbatim: the question, the arms,
the model and data sources, the training stream, the learning-rate freeze,
the evaluation, the metrics, the validity gates, the decision rules, the
seeds and sensitivity statements, the bundle and v1's design decisions. What
changes: the code (see "Engineering"), the job limits and caps and how they
are set ("Compute"), the smoke's measurement and its gate, which now also
covers the V1 extension, the resume legs' limits, the code table, the image
and the experiment id. v1's design decisions 18 and 23 (its 2.65 GPU-h budget
and its fixed 30-minute main limit), 30 (an extension projection that gated
nothing) and 31 (the bundle rebuild in image A) are replaced by this file's
decisions 32 to 46; the rest of v1's decisions apply as written. v1's
registration, contract, manifests and code are unchanged and v1 stays in the
ledger. In the copied text, "this experiment id", "this file", "image B" and
"the tabled code" mean this experiment's.

## Question

On frozen Qwen3-0.6B-Base, do block-form (compress ratio 4) sparse-attention
indexers distilled by KL from the model's own attention, and trained without
the evaluation languages, lose more needle-selection recall than the dense
block top-k of their own distillation target when the question is a human
translation in a different script from the needle passage, compared with a
same-language non-literal question, at a matched achieved budget of 1,024
tokens in an 8,192-token context?

This is a material narrowing of Phase 0a of the D21 contract
(`experiments/architectures/translation-supervised-sparse-indexer.yaml`): one
base, block form only, two targets (hs, mp), 20M distillation tokens, 8K only,
new headroom gates, an equivalence-style negative and a scale-free
co-statistic. Statistic definitions are inherited from that contract; scope
comes from `program/PROGRAM.md`, `program/questions/q3-cross-script-indexer.md`
and dossier entry E6. The versioned contract for this screen is
`experiments/architectures/translation-supervised-sparse-indexer-k1-screen-v2.yaml`
(v1's, `translation-supervised-sparse-indexer-k1-screen.yaml`, is unchanged).
A negative here is reported as "K1-screen negative (0.6B, block, hs/mp)" and
never as the D21 contract's two-base, two-form K1.

## Identity

Code. Commit A2 contains exactly the files below with these SHA-256 digests,
on top of main. It is the v2 image A's `org.opencontainers.image.revision`
label and the `git_head_at_freeze` of this experiment's ledger row: the file
is frozen from a clean checkout of commit A2 in which it is the only file that
may differ from commit A2. The file digests bind; a rebase or merge changes
the commit id, not the digests. The manifest filler
(`scripts/fill_sparse_indexer_k1_v2_manifests.py`) refuses to run unless its
own digest and the resume comparison's equal the table, holds back the main
job unless every gate receipt carries the tabled code and contract digests,
and refuses limits from a throughput probe that measured code other than the
table's.

| File | SHA-256 |
|---|---|
| harness/sparse_indexer_bank.py | e96653eb3eb5b9876201347c2fa8d452efc3ebb1043a516ac03c366ff8b89f88 |
| harness/sparse_indexer_k1_budget_v2.py | c86568a62fe12cbcb5ad91eed25fc0afd9e9a09078a43345b18277e6922ea4fe |
| harness/sparse_indexer_k1_equivalence_v2.py | 8117734933c10ff5027b5b1d3a15289d1bd45452c6bac2a2214a89daccd33d78 |
| harness/sparse_indexer_k1_runtime_v2.py | 5bd8cb0a5e05fa49c82da1154d7ae7bb335741a0da84d78953ac36377f2a8547 |
| scripts/run_sparse_indexer_phase0a_v2.py | 0848c071f517ec1eb3b16a948b20e05d16221ccd046a88b36cdfbf697f3ec721 |
| scripts/run_sparse_indexer_k1_v2_doctor.py | 78b9644faa542e8b44453e21e5fed433b8dd88fc83461ab83e5157f31aa6502e |
| scripts/probe_sparse_indexer_k1_throughput.py | a3207e10ea1662a3111c43d1378eb4d58cd166c96644bc7f4bd4af66a756115f |
| scripts/derive_sparse_indexer_k1_v2_limits.py | d3df879c98e5f7d3899508e95dd0a8f5acc65ac202f610e44823ddc8dd8b13f3 |
| scripts/fill_sparse_indexer_k1_v2_manifests.py | 7df1d609f4cfb7c04c1c34ab857d76ea023b3af3b0f0b782011f408b65af0efb |
| harness/sparse_indexer_torch.py | f21301a49634af07d5ae0385c34011400c83af15b984a96238dc6fe1d4ee9457 |
| harness/sparse_indexer_k1_stats.py | b9949b4b24502ad30d576938e88cd39d0fdcfc2be90eeedf52a68c76430f36b8 |
| harness/sparse_indexer_k1_runtime.py | 6fbddc91b6f7224f909901edb82278a68f68a208b558526c1a778ec9da6812fd |
| harness/sparse_indexer_k1_marker.py | 7bc69aa4d27a7d6de92f69a2f7b8e71d98b32101a2f34709fbaef2bdf84c3f1a |
| harness/sparse_indexer_data.py | 8b180e1ca0ba67d29587e3ffc5f5e46720376de6d1a52348f82b8789ab929faa |
| harness/translation_supervised_indexer.py | dee5318d254d962380e2de051eed227a97db10bfaa40eb0c12467e9a289e0cd5 |
| scripts/run_sparse_indexer_phase0a.py | ee11c38c3d84e691133b9563a3945331831ceb84ad7207d4c4f7a72e0906aef8 |
| scripts/run_sparse_indexer_k1_doctor.py | 1444b0635289a477d265b82f90e7b43d4fb913aff6639c3160d887f6ec25fcb7 |
| scripts/build_sparse_indexer_k1_bundle.py | 6ee842651372ce45827d612539e14e97383493fa162fd29482a99202708502d6 |
| scripts/compare_sparse_indexer_resume.py | 75289c34d48e123cb9221c0d980b202c5c8e66750b607a9ae0715375836092bb |
| experiments/architectures/translation-supervised-sparse-indexer-k1-screen-v2.yaml | e60cd1fe7b5285e584807640d5a12bc5ba4385ee422bf2b394869566aa6b5777 |

The v1 files in the table (`harness/sparse_indexer_torch.py` to
`scripts/compare_sparse_indexer_resume.py`) are
`q3-k1-localization-screen-v1`'s tabled files, byte-identical: v2 imports
v1's capture path, targets, statistics, verdict rules, data objects,
checkpoint store, signal protocol, LR freeze, chunk files, capture check and
resume comparison, and runs v1's K1 doctor beside its own. The files the
throughput probe ran (its receipt records their digests) must equal this
table.

Image. Image B2, built by `infra/slurm/host-single-node/build-architecture-image.sbatch`
from a fresh clean clone at commit B2 (commit A2 plus this file and its ledger
row, documentation only). Every GPU job uses image B2; its image ID, git SHA
and source-tar SHA-256 are written into each manifest by the filler and
verified at job start by `scripts/verify_compute_provenance.py`. The entry
point (`scripts/run_sparse_indexer_phase0a_v2.py`) verifies this file's digest
and its ledger row inside image B2 before any work. v1's K1 doctor and the v2
doctor (`scripts/run_sparse_indexer_k1_v2_doctor.py`) run in image A2 and in
image B2; all four receipts are kept with this experiment's evidence.

Bundle. v1's `k1-bundle-v1.json`, reused without a rebuild (see "Bundle").
The entry point verifies its SHA-256 at start-up, and the filler refuses any
other bundle and any building commit other than the one stated there.

Model. Qwen/Qwen3-0.6B-Base at `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`
(apache-2.0, 596,049,920 BF16 parameters, 28 full-attention layers, 16 query
and 8 key-value heads, head dimension 128, full rotary position at theta 1e6).
Receipt `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-0.6b-base.json`,
SHA-256 `e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df`,
artifact root `7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0`,
tokenizer.json SHA-256 `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`
(the entry point refuses a bundle built with any other tokenizer). The
receipt's `registry_sha256` is the registry baked into an earlier image
(`140d4418...`), not the current `models/registry.yaml`; `verify_receipt` does
not read that field.

Data sources (all opened 2026-10-06 or 2026-10-07):

| Source | Revision | Licence | Use |
|---|---|---|---|
| facebook/belebele | 7899cdfa4e1e0d733fd77c848e2c273cb1d32be2 | CC-BY-SA-4.0 | needles, questions, options (18 languages) |
| HuggingFaceFW/fineweb-2 | af9c13333eb981300149d5ca60a8e9d659b276b9 | ODC-By-1.0 (Common Crawl terms of use apply; not opened) | test-split monolingual training text (10 languages) and non-English haystacks (12 languages) |
| HuggingFaceFW/fineweb | 9bb295ddab0e05d785b879661af7260fed5140fc | ODC-By-1.0 (Common Crawl terms of use apply; not opened) | English haystacks, `data/CC-MAIN-2025-26/004_00046.parquet` |
| jhu-clsp/paradocs | f80095affa44545d18d0d64a574f9b8679017196 | Apache-2.0 packaging (README); the ParaCrawl text is not owned by the packager | bilingual training documents |
| rewicks/ParaDocs (filter tool) | 88f4ed95dadc577605e775ad447eefde5229d611 | none (no LICENSE file) | semantics reimplemented, not vendored |

TED2020 is excluded (program decision D4). Only identifiers and digests of web
text are published.

Throughput probe. The limits in "Compute" are the registered formula applied
to the rates of this receipt:

| Item | Value |
|---|---|
| q3-k1-throughput-probe-v1 receipt SHA-256 | <probe receipt digest> |
| Probe job | <probe slurm job> |

## Arms

Two KL-only block-form indexers per layer on all 28 layers, distilled from:

- hs: head-sum of the 16 heads' exact attention, L1-normalised, summed within
  each 4-token block, renormalised over complete blocks.
- mp: QSA Eq. 17: head-sum, L1, maximum within each 4-token block, L1 over
  complete blocks.

The harness's head-max aggregation is used only as a descriptive dense
selector row hm (sum within the block of the per-token head maximum); no
indexer is trained on it. A block b is complete for query row i when
4b + 3 ≤ i; rows with no complete block are excluded from the loss.

Indexer (identical for both targets): four query heads of dimension 128 and one
key per block. Query q_i^j = RoPE_i(RMSNorm(W_Q^j x_i)); block key
kbar_b = RoPE_{4b}(RMSNorm(mean of W_K x_s over the 4 tokens of block b));
score I_ib = sum over j of w_ij ReLU(q_i^j · kbar_b) / sqrt(128) on complete
blocks; gate w_ij = b_j + x_i W_w[:, j] with b = 1 and W_w = 0 at
initialisation (equal to QSA's unweighted head sum at init). x_i is the
layer's attention input (post input-RMSNorm hidden state, detached). Rotary
position covers all 128 dimensions at theta 1e6. RMSNorm is plain RMSNorm with
a learnable gain (initialised to 1, eps 1e-6). W_Q and W_K are drawn from
N(0, 1/1024) with a generator seeded by SHA-256 of (seed, layer, target), so
the three learning rates share an initialisation. 659,716 parameters per
indexer.

Selection: the top 256 complete blocks by score (1,024 tokens, 12.5 percent of
the context) plus the incomplete tail block; ties go to the lower block index.
The dense target selector T uses the same rule on the target distribution.

Training grid: targets {hs, mp} × learning rates {3e-4, 1e-3, 3e-3} × seeds
{42, 43, 44} = 18 indexers per layer, trained in one shared frozen-teacher
stream. Adam (beta 0.9, 0.999; eps 1e-8; no weight decay), gradient clipping
at 1.0 per indexer, batch 4 sequences of 8,192 tokens, 610 steps (20.0M
tokens), 20-step linear warm-up then constant learning rate, deterministic
algorithms, TF32 matmuls allowed, no torch.compile and no code generated at run
time. TF32 is exact only where both factors are bf16-valued: the target
recomputation from captured bf16 queries and keys (products exact, fp32
accumulation). The indexer's own matmuls (fp32 weights W_Q, W_K, W_w and the
fp32 q · kbar logits) are rounded to TF32's 10-bit mantissa on CUDA; the
indexer is therefore trained and evaluated at TF32 precision.

Targets come from the teacher's SDPA forward in bf16: post-norm, post-RoPE
queries and keys are captured and exact probabilities are recomputed in fp32
per 1,024-row chunk.

## Training stream

2,441 training sequences and 64 stream-dev sequences of 8,192 tokens. Every
sequence starts with token 151643 and items are separated by 151643. Each
sequence is homogeneous: 1,221 training and 32 stream-dev sequences are
bilingual, 1,220 and 32 are monolingual; the training order interleaves them
by a seeded permutation (seed 42). An item that overflows a sequence is cut
and its remainder discarded, so a bilingual item is never split across
sequences.

- Bilingual items: one ParaDocs document per item, laid out as English side,
  "\n\n", X side or the reverse (a SHA-256 coin per document), each side
  truncated at 512 tokens. Pairs en-th, en-hi, en-km come from `all/paracrawl`
  (the only split released for them); en-de, en-fr, en-es, en-pl come from the
  authors' `strict` split. One reimplemented filter runs on all seven pairs:
  minimum_size 2, frequency_cutoff 100, lid_cutoff 0.5, min_avg_score 0.0,
  including the upstream target-side consecutiveness quirk; a malformed line
  ends a document instead of stopping the run.
- Quota: each pair's target is 1.2 × floor(1,253 × 8,191 / 7) = 1,759,426
  item tokens, rounded down, counted with each side capped at 512 tokens (the
  1.2 covers the cut remainders). Files are read in name order
  until the target is met or 9 GB of compressed input is consumed or the files
  end. A cross-script shortfall is refilled in equal shares from the
  same-script pairs; the realised packed token share per pair is reported.
- Monolingual items: FineWeb-2 test splits in deu, fra, spa, pol, tha, hin,
  khm, cmn, arb, rus, in a SHA-256 order per language, each item truncated at
  2,048 tokens, 1.2 × the per-language share.
- Exclusions, counted in the bundle: no held-out evaluation language (ja, ko,
  bn, ta, el, he, ka, id, tr, sw, nl, it) is a training source; documents with
  more than 0.5 percent characters in the Hiragana, Katakana, Hangul, Bengali,
  Tamil, Greek, Hebrew or Georgian blocks; Latin-script training text whose
  function words read as it, nl, tr, id or sw (at least 3 hits and more than
  the expected language); any training or haystack document with an exact
  50-gram match, or a MinHash (128 permutations, token 5-gram shingles)
  Jaccard of at least 0.8, against any Belebele passage, question or option in
  the 18 downloaded languages. Evaluation texts shorter than 50 tokens are
  covered by the MinHash check only.
- Claim boundary: the indexers never see the evaluation languages. Japanese
  kanji overlap the Mandarin training text.
- V1 extension data: epochs 2 and 3 of the same 2,441 training sequences, each
  epoch in a permutation seeded 43 and 44.

## Learning-rate freeze

Per target, the learning rate with the lowest mean KL on the 64 stream-dev
sequences, averaged over the three seeds and the 28 layers, is selected; if
1e-3 is within 1 percent of the minimum it is selected, and an exact tie
between the other learning rates goes to the lower one. The record is written
and its SHA-256 taken before any audit prompt is read; the evaluation workers
verify that digest. Indexers at non-selected learning rates are never
evaluated on the audit partition. This is a registered deviation from the D21
contract's "development languages" wording (see Design decisions).

## Evaluation (audit partition only)

The 488 Belebele passages are split by link with
`split_passage_ids(seed=42)`: development 122 passages and 224 questions,
audit 122 and 230, primary 244 and 446. This screen reads only the audit
partition (and, for the smoke and the pre-check, the development partition);
a read outside the declared partition raises and the job exits 3. The primary
partition is never read.

- Cross-script pairs (14): (needle X, query en) and (needle en, query X) for
  X in {ja, ko, bn, ta, el, he, ka}. Crossed design: all 230 audit questions
  in every pair, 3,220 families.
- Same-script pairs (10, descriptive): the same 230 questions for X in
  {id, tr, sw, nl, it}, 2,300 families.
- Context: exactly 8,192 tokens = [151643] + needle-language haystack
  documents (FineWeb-2 test split for X; the FineWeb shard for English), each
  followed by "\n\n", with the Belebele passage (followed by "\n\n") inserted
  at the haystack document boundary nearest to depth × (8,191 minus the needle
  block length), an equidistant tie going to the earlier boundary; the
  haystack tail is cut. Depth cycles through
  {0.15, 0.50, 0.85} in a SHA-256 order of the questions, per needle language.
  Haystack documents have 32 to 1,536 tokens and are drawn per context by a
  seeded permutation.
- Query: "\n\n" + question + "\n". Query rows are the question tokens.
  MN = the question in the needle language; CX (or CS) = the human-translated
  question in the other language. A family's MN and CX prompts share
  haystack, needle and position; English-needle contexts are shared by all 12
  English-needle pairs.
- ML literal ceiling: 200 prompts (100 English-needle, 100 X-needle across the
  seven scripts); the query is one verbatim sentence of the needle passage.
- Needle-absent CX twins: 300 cross-script cells (SHA-256 order) whose context
  is haystack only.
- Development pre-check: 20 development questions × 14 pairs = 280 families,
  their 280 needle-absent twins and a no-haystack passage-plus-question
  reference for the same cells.

## Metrics

Recall of selector A on one prompt: for each layer, the mean over query rows
of |S ∩ N| / |N| × 100 (N = the needle passage tokens, S = the selected
tokens), then the mean over the 28 layers.

Selectors: the indexer at the frozen LR, seed-averaged (R_ind); the dense
block top-256 of its own target (R_T); the union over the 16 heads of each
head's top 1,024 tokens (U); the union of each head's top 64 tokens (U_k);
the analytic expectation of a uniformly random choice of 256 complete blocks
(R_rand); and the descriptive dense hm row.

Primary statistic, per target T: xi_T = macro over the 14 cross-script pairs
of the family mean of [R_ind(MN) − R_ind(CX)] − [R_T(MN) − R_T(CX)], in
recall points.

Co-statistic: G(c) = (R_ind(c) − R_rand(c)) / (R_T(c) − R_rand(c)) on pair
condition means; xi_rel_T = macro over pairs of G(MN) − G(CX). Evaluability is
decided once, on the point pair means: if any pair has R_T(c) − R_rand(c) of 1
point or less (MN or CX), xi_rel_T is not evaluable. Inside each bootstrap
replicate the denominator is max(R_T(c) − R_rand(c), 1 point), so a replicate
never divides by a vanishing or negative headroom; the number of replicates in
which this floor was active is reported. Per-seed values share the target and
random denominators, so they are evaluable exactly when the point is.

Interval: se_cluster is the SD of a passage-cluster bootstrap over the 122
audit links (B = 10,000, NumPy seed 42, macro-averaging inside each replicate,
seeds held fixed); s_seed is the SD of the three per-seed values; the decision
interval is point ± t(0.995, df) × sqrt(se_cluster² + s_seed² / 3), where df
is the Welch–Satterthwaite degrees of freedom of the two terms:
df = (se_cluster² + s_seed²/3)² / (se_cluster⁴ / 121 + (s_seed²/3)² / 2)
(a zero term drops out; df is infinite, and t the normal quantile 2.576, only
if both are zero). With three seeds a seed-dominated interval uses df near 2
(t up to 9.925); a normal quantile there would cover only about 88 percent.
The interval is not a full 99 percent interval in every regime. In the
pre-freeze simulations its coverage was 97.9 to 98.9 percent in four of five
regimes (cluster-dominated, seed-dominated or with a small seed SD), but 96.3
to 96.7 percent (each tail 1.5 to 1.9 percent against a nominal 0.5) where the
two terms were comparable (seed SD of xi about 2, df about 2.5), because a
small s_seed by chance raises df toward 121 and narrows the interval. The point
thresholds still keep P(GO) at a true xi of 5 or below, and P(NEGATIVE) at 9 or
above, near zero in every simulated regime (see "Seeds, sample sizes and
sensitivity"). The same construction applies to xi_rel_T. The percentile
bootstrap interval, df, the quantile and the per-seed values are reported
alongside.

Multiple choice: acc_norm, the option with the highest sum of token
log-probabilities divided by its UTF-8 byte length, each option scored as a
continuation of the full prompt (context + "\n\n" + question + "\n"), four
options, chance 25 percent; an exact score tie goes to the lowest option
index.

## Validity gates (evaluated before any verdict)

- V1 adequacy, per target, at every seed: English ML R_ind ≥ R_T(ML) − 5.
- V2 bug tell: English ML R_ind above R_T(ML) + 1 at any seed (the same 100
  English ML prompts as V1; registered tolerance, the harness default is 0)
  is a HOLD, terminal for this experiment id (see Decision rules).
- V3 integrity: no non-finite value on a selection prompt; every selection at
  most 1,024 + 3 tokens; every evaluation unit present exactly once; bundle,
  preregistration, model receipt, image and LR-freeze digests verified.
- H1 selection headroom: max over T of macro [R_T(CX) − R_rand(CX)] ≥ 10
  points to interpret at all, ≥ 20 points for a NEGATIVE.
- H2a: dense CX acc_norm macro over the 14 pairs, percentile passage-cluster
  bootstrap (B = 10,000, NumPy seed 42) 99 percent lower bound above 30
  percent.
- H2b: needle-present minus needle-absent dense CX accuracy on the 300 paired
  cells (plain mean), percentile passage-cluster bootstrap (B = 10,000, NumPy
  seed 42) 99 percent lower bound above 0 and point at least 5 points.

Pre-step: H1, H2a and H2b (and the no-haystack reference) are evaluated on the
development pre-check with the dense model only, before any registered indexer
is trained (the smoke's 4-step training and 20-unit development recall check
run first; they are plumbing and timing checks whose indexers are never used
again). If any of the three fails, the pre-check decision is ESCALATE_OR_STOP
and K1 does not run on 0.6B; the next step is Qwen3.5-4B-Base under a new
contract version and preregistration, or stop. If the resume test is not valid,
the main job does not run under this id either. The manifest filler enforces
both, and the smoke gate (see Compute): it fills the main job, its continuation
and the extension only after exactly one completed smoke job reports
SMOKE_PASS, exactly one completed development pre-check reports PROCEED_TO_K1
under the registered H1, H2a and H2b rules, and the resume test is valid, each
run under image B, the registered bundle, this file and the tabled code
(program decision D16).

## Decision rules

- GO: some target T has xi_T ≥ 10 with the combined 99 percent lower bound of
  xi_T above 0 and the combined 99 percent lower bound of xi_rel_T above 0,
  with V1 to V3 passing for that T and H1 ≥ 10, H2a and H2b passing. Next step:
  label-free remedy arms (rh/LOCOS target, multilingual KL data). Attribution
  is "cross-script" only if xi_CX − xi_CS ≥ 5 points (descriptive); otherwise
  the claim is "cross-lingual excess on cross-script pairs".
- K1-screen NEGATIVE: for both targets, xi_T ≤ 5 with the combined upper bound
  below 10 and the half-width at most 5, and xi_rel_T ≤ 0.1 with its upper
  bound below 0.2, with V1 to V3 passing for both, H1 ≥ 20, H2a and H2b
  passing. Reported as a localization negative for 0.6B block form and an
  indexer trained without the evaluation languages.
- UNINTERPRETABLE: H1 below 10, or H2a or H2b fails on the audit partition.
- HOLD: a V2 bug tell. HOLD is terminal for this experiment id (program
  decision D16): no GO or NEGATIVE is reported, the extension does not run,
  and the investigation of the bug tell is reported with the receipts. If the
  investigation finds a defect, the run is VOID and any re-run needs a new
  experiment id and preregistration; if it finds none, the verdict stays
  HOLD.
- VOID: a V3 integrity failure.
- V1 failure: one registered extension (epochs 2 and 3), called for by a main
  read whose verdict is V1_EXTENSION_REQUIRED, or INCONCLUSIVE with at least
  one target failing V1 (never after GO, NEGATIVE, UNINTERPRETABLE, HOLD or
  VOID). When the main read calls for it, the extension is submitted; it is not
  discretionary (program decision D16). If it is not run, or ends void
  (including a signal checkpoint, since it has no continuation, and a VOID
  read), the final verdict is INCONCLUSIVE and no second extension runs; the
  manifest filler fills the extension only while the main run root holds no
  extension job. It retrains the frozen-LR indexers of the V1-failing targets
  only and re-reads only those targets, once. A target that passed V1 in the
  main read keeps its main read and is never re-read; the dense-only gates (H1,
  H2a, H2b) are not re-read either (the main read's values decide; the
  extension's dense recomputation is reported as a determinism check). The
  extension's combined read applies the same rules to the main reads of the
  V1-passing targets and the extension reads of the others; a target still
  failing V1 is inconclusive, so a read in which no target passes V1 after the
  extension is INCONCLUSIVE, not a second extension. The main job persists its
  read in `checkpoints/main-read.json` (SHA-256 in its receipt); the extension
  recomputes that read's verdict and extension targets with the registered
  rules and refuses to run on any disagreement.
- INCONCLUSIVE: everything else, including a disagreement between the xi and
  xi_rel classifications and any half-width above 5 points.
- Final verdict (implemented by `harness.sparse_indexer_k1_stats.final_verdict`):
  one of GO, NEGATIVE, UNINTERPRETABLE, HOLD, VOID or INCONCLUSIVE.
  V1_EXTENSION_REQUIRED is never final. A main read that does not call for
  the extension is final, and its receipt says so (`verdict_is_final`). When
  the main read calls for the extension, the extension receipt's
  `final_verdict` is final; it equals the combined verdict except that a VOID
  extension read is INCONCLUSIVE, and an extension that wrote no receipt
  leaves the final verdict INCONCLUSIVE.
- Order (implemented by `harness.sparse_indexer_k1_stats.k1_verdict`): VOID
  (any target fails V3); HOLD (any V2 bug tell); UNINTERPRETABLE (H1 below 10,
  or H2a or H2b fails); V1_EXTENSION_REQUIRED when no target passes V1
  (INCONCLUSIVE after the extension); GO when any target that passes V1 is in
  the GO region (a GO is not delayed by the other target failing V1); NEGATIVE
  when both targets pass V1, both are in the NEGATIVE region and H1 is at
  least 20; otherwise INCONCLUSIVE (with the extension called for when a
  target failed V1).
- Multiplicity: two targets, each at 99 percent. Same-script rows, Lambda,
  hm, U, U_k and all per-language, per-direction, per-layer and per-position
  tables are descriptive and uncorrected.

## Seeds, sample sizes and sensitivity

- Seeds 42, 43, 44 set indexer initialisation only; stream order, passage
  split, prompts and bootstrap use seed 42 or SHA-256 orders. Seed variance is
  therefore initialisation variance only.
- 3,220 cross-script families in 122 passage clusters (6,440 prompts), 2,300
  same-script families, 200 ML prompts, 300 needle-absent cells.
- SE(xi) is not known in advance. Worked case: if the cluster-level SD of the
  family excess were 10 points, se_cluster would be about 0.9; with a seed SD
  of 1 point the combined SE is about 1.07 and df about 21 (t = 2.83), so the
  99 percent half-width is about 3.0 points.
- GO requires the point estimate itself to reach 10, so its power at a true
  xi of exactly 10 is about 0.5 whatever the SE. With SE 1.07, P(GO) is about
  0.83 at a true xi of 11, 0.97 at 12 and above 0.99 at 13 (the xi
  lower-bound condition is then met with near certainty because t × SE ≈ 3 is
  far below 10; these figures assume the xi_rel lower bound is also above 0);
  GO detects a true xi of about 10.9 points with power 0.8. If the
  seed term dominates (se_cluster near 0, df near 2, t up to 9.925), a GO at
  a point of 10 additionally needs SE below about 1.0, that is a seed SD of
  xi below about 1.7 points.
- A NEGATIVE needs a half-width of at most 5 points, which the rule enforces,
  so an underpowered read cannot be called NEGATIVE. In the worked case the
  half-width is about 3.0. In a seed-dominated read the half-width is about
  t(2) × s_seed / sqrt(3) = 5.7 × s_seed, so a NEGATIVE then needs a seed SD of
  xi of at most about 0.87 points; seeds vary initialisation only.
- The development pre-check reports se_cluster of Delta_T and Delta_U as a
  calibration.

Pre-freeze simulations with the registered statistics code (scripts and
results in `program/evidence/2026-10-07/q3-k1-prefreeze-simulations/`;
synthetic reads, two targets with independent noise, B = 10,000) give these
operating characteristics:

- Worked case (cluster-level SD of the excess about 9.3, seed SD 1, df about
  33, half-width 3.0; 4,000 reads per cell): GO per target 0.50 / 0.82 / 0.97
  at a true xi of 10 / 11 / 12; NEGATIVE for both targets 0.92 at a true xi of
  0 and 0.20 at a true xi of 5 (xi_rel 0.10). Across all five simulated
  regimes, P(GO verdict) is 0 at a true xi of 2.5 or below and at most 0.002
  at 5, and P(NEGATIVE verdict) is 0 at a true xi of 9 or above.
- GO from either of two targets inflates GO near the threshold: with both
  targets at a true xi of 9, P(GO verdict) is 0.16 to 0.32 in four of the
  five regimes (0.02 when the seed SD of xi is 0.5), against 0.09 to 0.17
  (0.01) for one target.
- When the seed SD of xi is about 2 and the two variance terms are comparable
  (df about 2.5, half-width about 8), NEGATIVE for both targets has
  probability 0.11 at a true xi of 0 and GO per target 0.35 at 10; with a
  seed SD of 3 (seed-dominated, half-width about 15) NEGATIVE is below 0.012
  at any true xi.
- HOLD is likely when the indexers match their targets on English ML: with the
  true indexer-minus-target English ML gap at 0 / −0.5 / −1 / −2 points,
  P(HOLD) is 0.47 / 0.20 / 0.06 / 0.002 when the per-prompt SD of the
  difference is 6 points (seed-by-prompt SD 4, seed SD 0.5), 0.74 / 0.57 / 0.39
  / 0.13 when it is 10 (6 and 1.0), and 0.09 at a gap of 0 when it is 3 (2 and
  0.3); 100 prompts, two targets × three seeds, 200,000 draws. Because HOLD is
  terminal, a well-trained indexer can end this id without a GO or NEGATIVE;
  that cost is accepted with the V2 tolerance (decisions 15 and 26). Some
  target fails V1 at a gap of −4 points with probability 0.09 / 0.47 / 0.74
  when the per-prompt SD is 3 / 6 / 10.
- H2a passes the 20-question development pre-check (19 passage clusters in
  the simulation) with probability 0.05 to 0.07 / 0.17 to 0.39 / 0.46 to 0.76
  / 0.72 to 0.95 at a true dense macro CX accuracy of 35 / 40 / 45 / 50
  percent, and the audit read with 0.58 to 0.91 / at least 0.998 / 1 / 1
  (logit item-difficulty SD 0.8 or 1.5; 2,000 replicates per cell).
- H2b (needle-present accuracy 45 percent) passes with probability 0.11 /
  0.24 to 0.25 / 0.37 to 0.43 / 0.75 to 0.80 on the development pre-check and
  0.11 to 0.13 / 0.29 to 0.34 / 0.50 to 0.54 / 0.90 to 0.91 on the audit read
  at a true present-minus-absent difference of 5 / 8 / 10 / 15 points, so it
  needs a real retrieval effect of about 14 to 15 points to pass with
  probability 0.8 to 0.9. At an accuracy of 45 percent and a difference of 10
  points the development pre-step passes with probability only about 0.17 to
  0.33. A pre-step stop can therefore reflect the pre-check's precision
  rather than an absence of headroom, and it is reported that way; the
  thresholds are accepted as registered (decision 6).

The pre-freeze simulations quoted above were run for v1 with the registered
statistics code, which v2 runs unchanged (`harness/sparse_indexer_k1_stats.py`
is in both tables); they apply to v2 as written.

## Engineering

The function computed is v1's; only how it is computed changes (decisions 33
to 36).

- Training. One batched bank per layer holds that layer's trainable indexers
  (`harness/sparse_indexer_bank.py`), stacked in cells of one target and one
  learning rate (the three seeds). Every slot is initialised by v1's
  `BlockIndexer.initialised`, bit for bit; each cell has its own
  `torch.optim.Adam` with v1's settings and `foreach=False`; the gradient norm
  is clipped at 1.0 per indexer over that indexer's six parameter tensors.
  The KL is computed per 1,024-row chunk (v1's target chunk) over keys and
  blocks up to the chunk's end, rows 0 to 2 (no complete block) are sliced
  off, block keys are computed once per sequence and their gradient is pushed
  through once, and the 1/sqrt(128) score scale multiplies the head gates
  instead of the logits plane. Losses stay on the device until one copy per
  step and layer. In the V1 extension the indexers that are not trained are
  in no bank: their parameters and Adam moments are carried through every
  checkpoint bit for bit.
- Stream-dev KL. The same chunked KL without gradients, 18 indexers at once.
- Evaluation. One teacher forward per unit as in v1. Per layer the dense
  probabilities and the hs, mp and hm targets are v1's own functions (the
  probabilities without v1's host-synchronising range check, same operations
  in the same order). The 9 block selectors (3 dense, 6 indexers) of 4 layers
  at a time are ranked by one `torch.topk` over a composite integer key (the
  score's order-preserving integer image, then the lower block index); U and
  U_k come from one top-k (the top 64 is a prefix of the same order); the
  random baseline is computed once per unit (it does not depend on the layer);
  the per-row recall values are v1's and their mean over query rows is taken
  in float64; recall is accumulated on the device and copied once per unit.
  The multiple-choice scores are v1's `_option_scores`, unchanged.
- Equivalence. In float64 on the CPU the bank equals v1's per-indexer path
  within 1e-12 relative (loss, clip norm) and 1e-11 (every gradient tensor,
  the parameters after an Adam step), the Adam step is bit for bit, changing
  one indexer leaves every other indexer's loss and gradients bit-identical,
  the selection and union functions equal v1's exactly (exact ties and signed
  zeros included), and one evaluation unit on a tiny random model matches
  v1's evaluation loop within 4e-6 recall points
  (`tests/test_sparse_indexer_bank.py`, the v2 doctor). On the H100 the
  throughput probe gates the same comparisons at the registered shapes under
  TF32 (`q3-k1-throughput-probe-v1`, "Arms"). Floating-point summation order
  differs, so a near-tie selection can differ from what v1's code would have
  produced; no v1 result exists to compare with.

## Compute

Every limit is a registered function of measured rates
(`harness/sparse_indexer_k1_budget_v2.py`, tabled). For a job whose projected
wall time is P minutes, the limit is max(5, ceil(1.2 x 1.15 x P + 3)) minutes
and the cap is GPUs x limit / 60 GPU-hours, rounded up to 0.01: v1's 1.2
margin, a 15 percent headroom for the smoke's re-measurement, and the
3-minute lead of Slurm's USR1. The projections use the probe's rates and v1's
registered counts (the registered layer shards [0-7], [8-14], [15-21],
[22-27]; a step of a shard is 4 x prefix layers x the teacher rate + layers x
the layer-step rate + the step overhead):

- main (4 GPUs): a 300 s allowance (v1's) + two training start-ups (training,
  stream-dev KL) + one evaluation start-up + the slowest shard's 610 steps
  and 7 checkpoint saves + the slowest shard's 64 stream-dev sequences + the
  audit evaluation / 4. The audit evaluation is 3,650 selection-only, 5,060
  selection plus multiple-choice and 300 multiple-choice-only units (bundle
  metadata, 289,330 selection query rows), the selection part scaled up by
  max(1, 33.2 / the measured mean rows).
- extension (4 GPUs; worst case: both targets fail V1, so 6 trainable
  indexers per layer): 300 s + one training and one evaluation start-up + the
  slowest shard's 1,220 steps, 13 saves and one load + the audit
  evaluation / 4.
- smoke (1 GPU): 120 s + the capture check + three training start-ups and one
  evaluation start-up + 12 steps of all 28 layers (18 indexers) + 6 steps of
  all 28 layers (6 trainable indexers) + two saves of 28 layers + 4 stream-dev
  sequences of 28 layers + 24 units of each kind (selection part scaled by
  38.6 / the measured rows, the development mean).
- headroom-dev (1 GPU): 120 s + one evaluation start-up + the development
  partition (160 selection-only, 280 selection plus multiple-choice, 560
  multiple-choice-only units, priced at the with-indexer rates; 16,968
  selection rows).
- resume-r0, resume-r1, resume-r2 (1 GPU, four workers): 120 s + the probe's
  four-worker start-up + steps x its four-worker step time + saves x 4 x 8
  layers x the save rate (the four workers write at once): R0 40 steps and 4
  saves, so that it finishes before its USR1; R1 25 steps and 2 saves, so that
  all four workers hold at step 25 before its USR1; R2 15 steps, 2 saves and
  one load.

| Job | GPUs | Projected minutes | Limit (minutes) | Cap (GPU-h) |
|---|---|---|---|---|
| smoke | 1 | <from the probe> | <from the probe> | <from the probe> |
| headroom-dev | 1 | <from the probe> | <from the probe> | <from the probe> |
| resume-r0 | 1 | <from the probe> | <from the probe> | <from the probe> |
| resume-r1 | 1 | <from the probe> | <from the probe> | <from the probe> |
| resume-r2 | 1 | <from the probe> | <from the probe> | <from the probe> |
| main (and its continuation, if any) | 4 | <from the probe> | <from the probe> | <from the probe> |
| extension (only when the main read calls for it, then mandatory) | 4 | <from the probe> | <from the probe> | <from the probe> |
| q3-k1-throughput-probe-v1 | 1 | | 9 | 0.15 |
| Total with the probe | | | | <from the probe> |

The contract (`execution.job_limits`) holds the same limits, written by
`scripts/derive_sparse_indexer_k1_v2_limits.py --apply` from the probe
receipt; the filler re-derives them from the receipt's rates and refuses any
difference.

Smoke gate. The smoke measures the same rates on the registered data: its
12-step training of all 28 layers (18 indexers per layer; steps 0 and 1
excluded) gives the teacher, layer-step and overhead rates; a 6-step timing
run with the extension's 6 trainable indexers (steps 0 and 1 excluded) the
extension's layer step; 4 stream-dev sequences (the first excluded) the
stream-dev rates; 24 development units of each kind (the first of each
excluded) the per-unit times; start-up and the save are measured apart. It
computes the main and extension projections with the same functions and
reports SMOKE_PASS only if every smoke gate passes and 1.2 x the projected
wall minutes + 3 is at most the registered limit for the main job and for the
extension; otherwise SMOKE_PASS_OVER_BUDGET, and the main job does not run
under this id. Its gates also check that the audit and development unit
counts and query rows in the staged bundle metadata equal the registered
ones above. Budget amendments are declined by default (program decision
D16); any amendment would be recorded in `program/decisions.md` before any
audit statistic exists and could change only minutes and GPU-hours, never
rules. The manifest filler recomputes both projections from the smoke
receipt's rates and fills the main job only after SMOKE_PASS, so no amendment
takes effect silently.

Continuation. If the main job nevertheless ends with a confirmed signal
checkpoint (exit 75, `signal_USR1_checkpoint_confirmed`), the continuation job
`q3-k1-v2-main-resume` runs once in the main job's run root from its
`phase-0a-k1/checkpoints`, with a limit of the registered main limit minus
the minutes the interrupted job used (rounded up, plus one), so the two
together stay within the main cap. It runs only if at least 5 minutes remain;
otherwise the screen stops without a read, reported as over budget. A second
continuation is declined by default (program decision D16), and the manifest
filler fills `q3-k1-v2-main-resume` only while the main run root holds no
continuation job. Training and evaluation are deterministic, so a
continuation changes the cost, never the outcome.

Gauntlet. If the caps with the probe total more than 8 GPU-hours, this file is
not frozen: the research gauntlet applies (program decision D20), and the
design is not cut to fit (the learning-rate grid stays; the review's
single-learning-rate fallback is not registered). The derivation script and
the filler both refuse such limits. Sensitivity, from the design analysis's
scenarios (estimates, not measurements; `scripts/derive_sparse_indexer_k1_v2_limits.py --scenario`;
indexer milliseconds per indexer, layer and sequence, target milliseconds per
layer and sequence, and seconds per selection unit; v1's smoke for the
teacher, saves and start-ups):

| Scenario | Inputs | Main projected / limit (min) | Extension projected / limit (min) | Caps with the probe (GPU-h) |
|---|---|---|---|---|
| central | 1.3 ms, 10 ms, 0.16 s | 25.4 / 39 | 28.9 / 43 | 6.50 |
| conservative | 2.8 ms, 16 ms, 0.30 s | 41.1 / 60 | 42.5 / 62 | 9.35 |
| batching-only | 3.2 ms, 20 ms, 0.30 s | 44.8 / 65 | 46.2 / 67 | 10.06 |

In the conservative scenario the caps exceed 8 GPU-hours, so the gauntlet
would apply before any v2 freeze. Interpolating the inputs between the central
and the conservative scenario, the caps cross 8 GPU-hours when the probe
projects the main job at about 33 minutes and the extension at about 36.

## Resume test

R0 trains to step 40 uninterrupted with a checkpoint every 10 steps. R1 runs
the same command, holds after step 25 until the Slurm signal 180 seconds
before its limit, saves on that signal, writes `checkpoint.ready` (with the
line `trigger=SIGUSR1` that the batch script requires) only after all four
workers acknowledged the save (a stale marker is deleted on receipt of the
signal; periodic saves never write it) and exits 75. Workers start with
SIGUSR1 and SIGTERM blocked and unblock them only after installing their
handler, so a signal that arrives while a worker is starting is held, not
fatal. R2 is a fresh job in R1's run root (the lane's resume copy reads the
predecessor's job directory, named by its Slurm job id, inside the resuming
job's own run root), resumed from R1's
`phase-0a-k1/checkpoints`, and trains to step 40. The resume is valid only if
R2's final state (parameters, Adam moments and step counters of every
indexer) equals R0's bit for bit and R1 terminated with
`signal_USR1_checkpoint_confirmed` and exit code 75
(`scripts/compare_sparse_indexer_resume.py`). R1's exit 75 is its expected
end: Slurm records it as FAILED 75:0 and its orx node prints ORX_RESULT
exit=5; the manifest filler selects R1 as R2's predecessor only from its
`termination.env`.

Evaluation reads exactly the generation each training worker completed at
the registered final step (610, or 1,830 after the extension), verified
against the worker's completion record; a missing or corrupt final generation
is an integrity failure (exit 3), never a fallback to an older generation.

The legs' limits are the registered probe-derived limits above: R0 and R2 are
sized to finish before their USR1, and R1 so that all four workers hold at
step 25 before its USR1, from the probe's measurement of the four shards
sharing one GPU (v1's 8- and 9-minute legs would not have: R0 needed about 10
minutes against a USR1 at minute 5).

## Infrastructure failures and exclusions

A run is void, with no partial read, when: the job does not end COMPLETED
with exit code 0:0, except R1 (whose registered end is exit 75) and a main job
that ends with a confirmed signal checkpoint (exit 75) and is completed by its
one registered continuation (see Compute); the signal checkpoint times out,
or is missing in a job that did not complete with exit code 0 (a signal that
arrives after the last checkpointable step, while the receipt is written, lets
the job finish); any startup digest check fails (exit 2); an integrity failure
occurs (exit 3); provenance verification fails; the smoke gates fail; or the
orx node lacks its ORX_RESULT line. A continuation is not a re-run: it reuses
the interrupted job's completed training, stream-dev KL, LR freeze and
evaluation chunks and computes the statistics once, at the end. A re-run uses
a new run root and this same id only if no audit statistic was produced
(written evaluation chunks that no statistic has read do not count; a main
receipt or `main-read.json` does); otherwise it needs a new id. The extension
is never continued or re-run: it must share the main run root, so an
extension that ends void for any of these reasons leaves the final verdict
INCONCLUSIVE (Decision rules).

The smoke gates include the gate of the main job and of the worst-case
extension against their registered limits. An evaluation unit with a
non-finite score on a complete block, or a non-finite attention probability,
is an integrity failure (exit 3, V3).

## Reported regardless of outcome

- Seed SD per target; pooled sigma-hat of macro CX recall with df 4 (two
  targets × two) and its 80 percent chi-square upper bound, stated as
  initialisation-only variance, before any parallel-loss arm.
- Delta_ind, Delta_T, the single difference R_T(CX) − R_ind(CX), xi_T, xi_rel_T
  (point, combined interval, percentile interval, per-seed values), S_T against
  U and U_k, and Lambda = R(ML) − R(MN).
- Per-language, per-direction, per-layer and per-position tables; same-script
  rows and xi_CS; the attribution label.
- Boundary tie counts per selector; needle-absent and no-haystack accuracy;
  the achieved-budget check.
- Stream-dev KL for all 18 indexers per layer and the LR-freeze record with
  its digest.
- Bundle reports: dedup and filter counts, quota, shortfall and realised
  packed share per pair.
- Smoke timings, the main and extension projections, and the measured
  per-phase timings of the main job (and of the extension, if it runs).
- The final verdict and whether the main read was final; for a HOLD, the
  investigation of the bug tell and its finding.
- The throughput probe's receipt, its rates and the limits derived from them;
  the smoke's measured rates, its projections of the main job and the
  extension against their limits; the per-step and per-unit times of every
  job and their start-up times.

## Bundle

v1's bundle is reused without a rebuild. v1's record of it, verbatim, with
the commit that built it added (v1's commit A, its ledger row's
`git_head_at_freeze`):

Fetch stage: the H100 host's CPU on 2026-10-07 (Python 3.12.13, tokenizers
0.22.2, pyarrow 25.0.1), with network, writing only the raw directory; the
fetch code is identical to commit A's. Build stage: inside
`cotcodec-research:f10a8571-architecture` (Python 3.12, numpy 2.5.2,
tokenizers 0.22.2) with pyarrow 25.0.1 on the path, `--network none`, the raw
directory and the model snapshot mounted read-only. The build ran from the
review branch before it was rebased onto main (sidecar `built_from_git_sha`
668673dc6162103969d266a3d12dab6ed853dc7c); the bundle embeds the SHA-256 of
the builder and the data module, which are byte-identical to commit A's
(table above), and carries no commit id, so the rebase does not change it.
The build was run twice and produced the same bytes. The full source ledger
(every file's revision, licence, size and SHA-256, and the ParaDocs streaming
record) is `program/evidence/2026-10-07/q3-k1-bundle-sources.json`.

| Item | Value |
|---|---|
| raw-manifest.json SHA-256 | 808e6c2477cafbe672273f004f0dafad4b1cb83780bb83114f971f6a34819189 |
| k1-bundle-v1.json SHA-256 | 919d016b87ad862f8f156e9537c9a39e2864dab0e6c605307d100d25a199dd2d |
| k1-bundle-v1.json size (bytes) | 278,818,734 |
| Licence id | LicenseRef-cotcodec-k1-bundle-v1 |
| k1-bundle-v1.json built at commit | ec81fe3292d8559251adb273cb4e6ec5b070c162 |

Input facts measured while building (no model was run):

- Split 122 / 122 / 244 links; 230 audit questions; every cross-script pair
  holds all 230 audit questions; 3,744 contexts, all needle and needle-absent
  contexts exactly 8,192 tokens; 12,660 prompts (main 6,440, same-script
  4,600, literal 200, needle-absent 300, development 560 plus 280 absent and
  280 no-haystack).
- Audit needle length in tokens, mean (max): en 95 (209), ja 138 (269), ko 155
  (337), he 142 (289), bn 482 (1,002), el 467 (1,035), ka 501 (1,124), ta 587
  (1,164). Needles longer than 1,024 tokens cap block-budget recall below 100
  for those prompts; MN and CX share the needle, so the cap enters both legs.
- Training stream: 2,441 × 8,192 and 64 × 8,192 tokens, every row starting
  with 151643. ParaDocs streaming consumed 6,340,670,165 bytes (en-th, quota
  met at the fetch stage with 1,765,090 tokens), 7,494,905,291 (en-hi, quota
  met with 1,779,230) and 4,104,691,058 (en-km, all files, 1,557,005 tokens,
  11.5 percent short); 16 to 60 MB per same-script pair. After the build's
  filters the cross-script pairs supplied en-th 1,758,426 (1,000 short of the
  1,759,426-token target), en-hi 1,759,460 and en-km 1,552,984 (206,442 short,
  11.7 percent); the combined 207,442-token shortfall raised each same-script
  target to 1,811,287. Realised packed
  shares: en-de 14.6, en-es 14.7, en-fr 14.7, en-pl 14.6, en-th 14.3, en-hi
  14.3, en-km 12.6 percent of bilingual tokens.
- Removals: no exact-50-gram or MinHash match in any training or haystack
  pool; held-out-script removals 79 (en-th), 17 (en-hi), 38 (en-km), 16
  (en-pl), 1 (en-de) bilingual documents and 2, 2, 1, 1, 0, 1, 1, 0, 3, 17
  monolingual documents (ar, de, es, fr, hi, km, pl, ru, th, zh);
  Latin function-word removals 1 (en-fr), 2 (en-pl) bilingual and 1 (pl)
  monolingual. A sanity check with the real tokenizer flagged a Belebele
  passage embedded in other text (exact 50-gram) and gave Jaccard 0.898 for a
  one-token edit.
- The reimplemented ParaDocs filter reproduces the upstream tool's output
  line for line (same documents, same lines, same order) on the three head
  samples the plan review filtered with the upstream tool: en-th (36
  documents, 107 lines), en-hi (20, 44) and en-km (17, 35).

## Freeze procedure

1. `q3-k1-throughput-probe-v1` is frozen, its image is built from the commit
   holding its ledger row, and the probe job runs
   (`scripts/fill_sparse_indexer_k1_probe_manifest.py`). Its receipt and
   evidence are committed. If it does not end `PROBE_COMPLETE`, no limit
   exists and this file is not frozen.
2. `scripts/derive_sparse_indexer_k1_v2_limits.py --probe-receipt RECEIPT
   --apply` writes the limits and the receipt's SHA-256 into the contract; it
   refuses if the caps with the probe exceed 8 GPU-hours, and then the
   gauntlet applies (program decision D20). The limits table, the probe rows
   in "Identity" and the code table (the contract's digest changes) are filled
   in this file, and `program/decisions.md` records the receipt and the
   limits.
3. Commit A2 is that state. The v2 image A is built from a fresh clean clone
   of commit A2, and v1's K1 doctor and the v2 doctor run in it. No bundle is
   rebuilt.
4. This file is frozen from a clean checkout of commit A2 and committed with
   its ledger row (commit B2). Image B2 is built from commit B2, both doctors
   run in image B2, the manifests are filled, and the orx nodes run in the
   order smoke, headroom-dev, R0, R1, R2, main, then the main-job continuation
   only if the main job ended with a confirmed signal checkpoint, and the
   extension whenever the main read calls for it.

## Design decisions carried from v1

v1's design decisions follow verbatim. Decisions 18 and 23 (v1's budget and
its fixed 30-minute main limit), 30 (the extension projection that gated
nothing) and 31 (the bundle rebuild in image A) are replaced by decisions 32
to 46 below; every other decision applies to this experiment as written.

Decisions 1 to 25 were left to the program owner by the reviewed plan; each
states the choice and why. The owner accepted them as program decision D16
(`program/decisions.md`) with conditions: decisions 26 to 29 apply those
conditions, and decisions 30 and 31 apply the pre-freeze audit's
recommendations.
"Program decision Dn" refers to `program/decisions.md`; "review Dn" refers to
a defect in the plan review's list.

1. Harness code on GPUs. Program decision D7 settles it: reviewed, tested,
   committed harness code is project code. The K1 harness generates no code at
   run time (no torch.compile, no model-written kernels).
2. TED2020 excluded (program decision D4). K1 uses permissively packaged
   parallel data only.
3. Cross-script bilingual data: stream until the 1.2× quota is met, capped at
   9 GB of compressed input per pair. The yield probe (1 GB per pair,
   2026-10-07) kept 278,595 (en-th), 206,703 (en-hi) and 331,407 (en-km) item
   tokens per GB; the full fetch then consumed 6.34, 7.49 and 4.10 GB, and
   en-km (whose two files hold 4.10 GB) ended 11.5 percent short at the fetch
   stage (11.7 percent, 206,442 tokens, after the build's filters, which also
   left en-th 1,000 tokens short). The 207,442-token shortfall is refilled
   from the same-script pairs in equal shares and the realised shares are
   reported (en-km 12.6 percent of bilingual tokens).
   Reason: this keeps the registered 50/50 bilingual/monolingual design and
   the largest feasible cross-script share; dropping cross-script bilingual
   data would change the recipe more than a recorded shortfall.
4. Same-script pairs read the authors' `strict` split. Their `all/paracrawl`
   files open with millions of lines without document positions (the en-de
   head is a 2016 crawl with every position field "None"), so the
   reimplemented filter keeps nothing there. One filter runs on all seven
   pairs; the input regimes differ and this is registered. The `strict` heads
   are Europarl-dominated.
5. A Latin-script function-word filter was added after an en-pl `strict` line
   was found to carry Italian and Greek text. It is a heuristic and is
   reported with counts.
6. Headroom thresholds: H1 ≥ 10 to interpret and ≥ 20 for a NEGATIVE; H2a
   99 percent lower bound above 30 percent; H2b lower bound above 0 and point
   at least 5. Reason: a NEGATIVE needs the target to have recall to lose
   (review D2a), and H2b separates retrieval from parametric answering of
   possibly memorised FLORES passages (review D7). The pre-freeze simulations
   show that H2b needs a retrieval effect of about 14 to 15 points to pass
   with probability 0.8 to 0.9 and that the development pre-step can stop
   0.6B for precision reasons (see "Seeds, sample sizes and sensitivity");
   the thresholds are accepted with that operating characteristic stated.
7. NEGATIVE is equivalence-style and needs the scale-free co-statistic:
   xi_rel ≤ 0.1 with upper bound below 0.2. GO needs the xi_rel lower bound
   above 0. Reason: the additive xi penalises a uniformly weaker indexer and
   can mask a cross-script deficit (review D2b, D2c).
8. Combined seed-plus-cluster interval (review D3), the D21 contract's own
   noise model, read with a Welch–Satterthwaite t quantile instead of the D21
   contract's normal quantile (decision 20).
9. Base ladder: 0.6B now; if the pre-check or the audit read is
   UNINTERPRETABLE, the fallback is Qwen3.5-4B-Base (named in the D21 contract
   and the dossier; receipt on the host) under a new contract version and
   preregistration. Qwen3-1.7B-Base is not in the contract and is not used
   without one.
10. Crossed evaluation: all 230 audit questions in all 14 pairs (3,220
    families) instead of an 86-question subset per pair. Reason: it removes
    the confound of item difficulty with language (review D10) at about +0.1
    GPU-h.
11. LR selection per target on mean stream-dev KL (review D13). Reason: the
    contract's "development languages" metric is unspecified, and all 18
    indexers are trained anyway; held-out KL is the distillation objective
    itself and never touches Belebele.
12. Indexer rotary width 128. Reason: QSA applies partial rotary "matching the
    rotary dimension used in the core attention module"; Qwen3-0.6B rotates
    all 128 dimensions. At theta 1e6, 30 of the 64 frequency pairs have
    wavelengths beyond 8,192 tokens, so near-position-free channels remain.
13. Plain RMSNorm (learnable gain) and a fixed 1/sqrt(128) score scale. QSA
    says only RMSNorm; the scale is a reparametrisation (ReLU is positively
    homogeneous).
14. Same-script descriptive rows included (review D6), at about 0.05 to 0.1
    GPU-h.
15. V1 at every seed (the contract's doctor gate) and a V2 tolerance of 1
    point (review D13), read on the 100 English ML prompts; a V2 bug tell is a
    terminal HOLD (decision 26).
16. V1 extension data: epochs 2 and 3 of the same stream (review D11). Reason:
    the cross-script yield makes fresh data infeasible, and a pre-built
    60M-token stream would not fit the 512 MiB study-artifact limit with the
    evaluation set.
17. Context sharing and depth: English-needle contexts are shared by the 12
    English-needle pairs and depth is assigned per needle language and
    question, so the English MN prompt is one prompt for every X.
18. Budget: 2.65 GPU-h cap plus a conditional 1.5 GPU-h extension, above the
    program document's 1.5 GPU-h estimate and below the 8 GPU-h gauntlet
    threshold. `program/state.json` and the Q3 question file are updated when
    this is frozen.
19. The orx `cpu-doctor` node runs `uv run --locked` without the architecture
    extra, so it cannot import torch; the K1 doctor is run in image A and in
    image B (CPU, no network), and both receipts are kept with this
    experiment's evidence.
20. Decision-interval quantile: t(0.995, df) with Welch–Satterthwaite df (121
    for the cluster term, 2 for the seed term) instead of 2.576. Reason: with
    three seeds the seed SD has 2 degrees of freedom; MN and CX share needle
    and context, so cluster effects largely cancel in xi and the seed term can
    dominate, where a normal quantile covers only about 88 percent. Simulated
    with the module's own code (true xi = 0, 300 to 400 tables per scenario,
    including the plan review's two), 2.576 missed 13 to 15 percent and the t
    quantile 0.5 to 2 percent (`tests/test_sparse_indexer_k1_stats.py` keeps
    one scenario as a regression test). That figure holds when one term
    dominates; the pre-freeze simulations found the t interval missing 3.3 to
    3.7 percent (coverage 96.3 to 96.7) when the two terms are comparable, so
    the decision interval is not a full 99 percent interval in that regime,
    while the point thresholds still keep P(GO) at a true xi of 5 or below, and
    P(NEGATIVE) at 9 or above, near zero (see "Interval" and "Seeds, sample
    sizes and sensitivity"). More seeds would cost GPU time the budget does not
    have; the cost of the honest quantile is that a seed-dominated NEGATIVE
    needs a seed SD of xi of at most about 0.87 points.
21. xi_rel evaluability is decided on the point pair means only, and
    bootstrap replicates use max(R_T(c) − R_rand(c), 1) as the denominator.
    Reason: the registered rule names the pair means; a replicate-level rule
    let a single pair with 1.3 to 4 points of target headroom block both GO and
    NEGATIVE although the point statistic is defined. The floor keeps a
    replicate from dividing by a vanishing or negative headroom; dropping such
    replicates instead would condition the bootstrap on the data. The number
    of replicates where the floor was active is reported.
22. V1 extension scope: only after V1_EXTENSION_REQUIRED, or INCONCLUSIVE with
    a V1-failing target; only the V1-failing targets are retrained and
    re-read; a V1-passing target keeps its main read; H1, H2a and H2b are not
    re-read. Reason: re-reading a target that already passed V1 (or the
    dense gates) would be an unregistered second look.
23. The main job's limit is fixed at 30 minutes, gated by 1.2 × the smoke
    projection + 3 minutes ≤ 30, instead of "lowered from the projection".
    Reason: a lower limit buys nothing but scheduling and raises the chance
    of an interruption; the 1.2 factor covers the single-GPU-to-four-worker
    scaling of the projection and the 3 minutes are Slurm's USR1 lead. A
    confirmed-signal interruption is continued once within the remaining
    minutes (at least 5), so the main read never exceeds its 2.0 GPU-h cap; a
    second continuation is declined (decision 28).
24. Resumed legs share their predecessor's run root (R1 and R2 in
    `k1-screen-v1/resume-r1-r2`; main, its continuation and the extension in
    `k1-screen-v1/main`). Reason: the merged lane copies the resume subpath
    from the predecessor's job directory (named by its Slurm job id) inside
    the resuming job's own run root; separate run roots fail before the
    container starts.
25. TF32 stays enabled for the indexer's fp32 matmuls; the precision
    statement is narrowed to the target recomputation. Reason: TF32 is
    deterministic, the screen reads selection recall rather than exact fp32
    logits, and indexer training and evaluation use the same precision.
26. HOLD is terminal for this experiment id (program decision D16). After a
    V2 bug tell no GO or NEGATIVE is reported and the extension does not run;
    the investigation is reported; a defect it finds makes the run VOID, with
    any re-run under a new id and preregistration, and otherwise the verdict
    stays HOLD. Reason: the main receipt shows every target's xi and xi_rel
    before anyone investigates, so releasing or discarding a held read later
    would be decided with the results in view (pre-freeze audit, blocking
    defect 1). The cost is stated under "Seeds, sample sizes and
    sensitivity": HOLD fires with probability 0.06 to 0.74 when the indexers
    are within a point of their targets on English ML.
27. The V1 extension is mandatory when the main read calls for it (program
    decision D16). If it is not run, or ends void (including a signal
    checkpoint and a VOID read), the final verdict is INCONCLUSIVE and no
    second extension runs; `harness.sparse_indexer_k1_stats.final_verdict`
    implements this and the extension receipt carries the result. Reason:
    `main-read.json` and the main receipt hold the V1-failing target's xi
    before the extension, so an optional extension could be spent only when
    that target looks like a GO (pre-freeze audit, blocking defect 2); the
    extension shares the main run root, so the re-run rule cannot apply to
    it.
28. Budget amendments after SMOKE_PASS_OVER_BUDGET, and a second main-job
    continuation, are declined by default (program decision D16). Any
    amendment would be recorded in `program/decisions.md` before any audit
    statistic exists and could change only minutes and GPU-hours, never
    rules. Reason: training and evaluation are deterministic, so only the cost
    is at stake, and a resource-only amendment is bounded in advance.
29. The manifest filler enforces the pre-main gates (program decision D16).
    It fills the main job, its continuation and the extension only after
    exactly one completed smoke job reports SMOKE_PASS (re-checking 1.2 × the
    projection + 3 minutes ≤ 30), exactly one completed development pre-check
    reports PROCEED_TO_K1 (re-checking the registered H1, H2a and H2b rules),
    and the resume test is valid (R2 resumed from the signal-checkpointed R1
    and equals R0 bit for bit under `scripts/compare_sparse_indexer_resume.py`).
    Each gate job must have run under image B and the bundle, and its receipt
    must carry this experiment id, the registered profile, this file's digest
    and the tabled code and contract digests. The filler also refuses a
    bundle whose SHA-256 differs from the one stated here, refuses to run
    unless its own digest and the comparison script's equal the table, and
    fills the continuation and the extension at most once. Nothing overrides a
    failed gate. Reason: the pre-freeze audit found these gates computed but
    not enforced, so the registered order was operator discipline only; the
    filler is tabled, so the enforcement is part of commit A.
30. The smoke reports a projection of the extension's wall time (worst case:
    both targets fail V1) against its 22-minute limit, descriptively. Reason:
    the 22 minutes and 1.5 GPU-h for 1,220 extra training steps per indexer
    and a full audit evaluation were unverified, and the extension has no
    continuation. The projection gates nothing: the extension is mandatory
    when called for, and one that does not finish leaves the verdict
    INCONCLUSIVE.
31. The bundle rebuild in image A refuses to fetch when a registered
    raw-manifest digest is supplied, and checks the rebuilt bundle against
    the registered digest (`infra/slurm/host-single-node/build-k1-bundle.sbatch`).
    Reason: the batch script's raw path did not exist on the host, so it would
    have re-fetched; a fetch records wall-clock streaming times that end up in
    the raw manifest the bundle embeds, which would change the digest and lose
    the bit-identical check.

## Design decisions of v2

32. Successor, engineering only (program decision D20). No registered
    scientific quantity changes: the question, arms, data, stream, learning-rate
    grid and freeze, evaluation, metrics, gates, decision rules, seeds,
    statistics and bundle are v1's. Operational changes, all listed here:
    the experiment id; the code and its table (decisions 33 to 36); the job
    limits and caps (main 30 minutes and 2.0 GPU-h, extension 22 minutes and
    1.5 GPU-h and gate legs of 7, 6, 8, 9 and 8 minutes in v1, probe-derived
    here, decision 37); the smoke's measurement (decision 39) and its gate,
    which now covers the extension (decision 38); the image; and the evidence
    of equivalence (decision 36). Disclosure: these changes were designed
    after v1's smoke gate failed (SMOKE_PASS_OVER_BUDGET, 121.6 against 30
    minutes); v1's failure is reported, v1 stays in the ledger, and this is a
    new id, not an amendment of v1 (D16 declined amendments under v1).
33. The batched bank (see "Engineering"). Reason: v1's 5.69 ms per indexer,
    sequence and layer was about half launch and host-synchronisation overhead
    over a memory-traffic floor of about 2.6 to 3.0 ms; one bank per layer
    removes the per-indexer launches and synchronisations, and the chunked
    causal truncation removes 44 percent of the logits plane. The review's
    traps are closed by construction and tested: every slot's initialisation
    is v1's (seeded by seed, layer and target, so the three learning rates
    still share one); clipping and Adam are per indexer (per slot, per cell),
    never shared; indexers that are not trained are in no bank, so no
    optimizer moves them; the target path keeps the scale as the fp32
    multiplier after the bf16-valued product, so TF32 stays exact there.
34. Fixed constants: the 1,024-row chunk (v1's target chunk, for the targets
    and the indexer alike) and the evaluation group of 4 layers never depend
    on available memory; the engine and the chunk enter the checkpoint
    configuration digest, so a checkpoint written by another engine (v1's
    included) is refused, never resumed.
35. Vectorised evaluation (see "Engineering"). The selection rule is v1's,
    implemented with a composite-key top-k whose selected sets, boundary tie
    counts, needle hits and selected-token counts equal v1's functions
    exactly. -0.0 is canonicalised to +0.0 before ranking, so zero scores of
    either sign tie and go to the lower block index on any device, as the
    rule registers, whatever sort a device uses (one that compares raw float
    bits orders -0.0 below +0.0). A non-finite score on a complete block, or a non-finite attention
    probability, is an integrity failure (V3: "no non-finite value on a
    selection prompt"); v1 checked only the recall values.
36. Equivalence evidence: float64 tolerances 1e-12 (loss, clip norm) and 1e-11
    (gradients, post-step parameters), Adam bit for bit, slot independence
    bit for bit, selection exactly equal, and the device gates of the probe
    under TF32. Equivalence means the same function: summation order differs,
    so near-tie selections can differ from what v1's code would have
    produced; there is no v1 result to reproduce.
37. Limits from the probe by the explicit formula in "Compute". Reason: v1's
    limits were estimates about 3.3 times low. The 1.15 headroom follows the
    review: a limit set at exactly 1.2 x the probe projection + 3 would leave
    the smoke, which re-measures the same quantity, about an even chance of
    failing. The 300 s allowance of the main job and the extension is v1's
    (staging, statistics, receipt); the gate legs get 120 s (v1's smoke spent
    30 s from container start to its first worker, the capture check
    included).
38. The smoke gates the extension as well as the main job. Reason: the
    extension is mandatory when called for and has no continuation, so an
    extension that cannot finish makes the verdict INCONCLUSIVE; v1 projected
    it (96.1 minutes against 22) but gated nothing.
39. The smoke's measurement protocol (see "Compute"): steady state after
    steps 0 and 1, the first unit of each kind excluded, start-up apart,
    multiple-choice units measured (v1's smoke had none), the extension's
    6-indexer step measured, not scaled. The registered unit counts and rows
    are checked against the staged metadata, so the projection cannot use
    another unit mix.
40. Resume legs and the pre-check are sized by the same formula from the
    probe: the four-shards-on-one-GPU step time (measured, not summed), the
    saves of four workers counted as serialised, R1 sized to its hold, and
    the pre-check's 560 multiple-choice-only units counted.
41. The main job's one continuation gets the registered main limit minus the
    minutes used (v1's rule with the probe-derived limit).
42. Gauntlet, not a cut (program decision D20): if the caps with the probe
    exceed 8 GPU-hours this file is not frozen and the research gauntlet
    applies. The review's fallback of a single learning rate is not
    registered: it would give up decision 11's guard against an undertrained
    indexer that matches English literal prompts (passes V1) and loses more
    recall on cross-script queries, a bias toward GO.
43. The bundle is v1's, reused without a rebuild (D20); its digest and the
    commit that built it are checked by the entry point and the filler.
44. The probe binds the code: the files the probe ran must have this table's
    digests, and any change to them after the probe needs a new probe id.
45. Considered and not adopted: CUDA graphs (the bank already removes the
    per-indexer launches and synchronisations; graph capture of the backward
    pass adds a memory-pool and determinism path of its own), one teacher
    forward shared by the four workers (cross-process tensors for about 2
    minutes of the central main projection), context-prefix reuse in the
    evaluation (a key-value-cache capture path that would need its own
    capture gate, about 0.13 GPU-h), several prompts per forward (at most
    about 5 percent) and target or teacher caching (reading cached targets
    back is slower than recomputing them).
46. Owner record before the freeze: program decision D20 sets the method; the
    numbers (the probe receipt's SHA-256 and the limits table) are recorded in
    `program/decisions.md` with the owner's acceptance of decisions 32 to 46
    before this file is frozen.
