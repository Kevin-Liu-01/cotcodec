# Q3 K1 localization screen (q3-k1-localization-screen-v1)

Status: DRAFT for the program owner. It is not frozen. The owner reviews it,
logs the design decisions below, rebuilds the bundle with image A and confirms
the bundle digest, then freezes it with
`uv run python scripts/preregister.py freeze q3-k1-localization-screen-v1 program/preregistrations/q3-k1-localization-screen-v1.md`.
No GPU job of this experiment runs before that freeze.

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
`experiments/architectures/translation-supervised-sparse-indexer-k1-screen.yaml`.
A negative here is reported as "K1-screen negative (0.6B, block, hs/mp)" and
never as the D21 contract's two-base, two-form K1.

## Identity

Code. The commit that contains exactly the files below with these SHA-256
digests (commit A), on top of main with the merged discovery lane. It is the
`git_head_at_freeze` of this experiment's ledger row and image A's
`org.opencontainers.image.revision` label. On the review branch it is
`e29570418a813667b636b9e0ed85778c15abe0f8`; if the owner rebases, the file
digests bind, not the commit id.

| File | SHA-256 |
|---|---|
| harness/sparse_indexer_torch.py | f21301a49634af07d5ae0385c34011400c83af15b984a96238dc6fe1d4ee9457 |
| harness/sparse_indexer_k1_stats.py | a14db816ae0b292eed6026e32898c7d02309d39bc42185417418a936ef282bc5 |
| harness/sparse_indexer_k1_runtime.py | e1e1bcde4dc1a94e16cfb4ceabdcc2d89d06211652a861696bc0967c05fb50f2 |
| harness/sparse_indexer_k1_marker.py | 7bc69aa4d27a7d6de92f69a2f7b8e71d98b32101a2f34709fbaef2bdf84c3f1a |
| harness/sparse_indexer_data.py | 8b180e1ca0ba67d29587e3ffc5f5e46720376de6d1a52348f82b8789ab929faa |
| harness/translation_supervised_indexer.py | dee5318d254d962380e2de051eed227a97db10bfaa40eb0c12467e9a289e0cd5 |
| scripts/run_sparse_indexer_phase0a.py | b3f17d90153560333c0019168d27ab227c5a8cebbbd71471a0aec2de97e982a1 |
| scripts/build_sparse_indexer_k1_bundle.py | 6ee842651372ce45827d612539e14e97383493fa162fd29482a99202708502d6 |
| scripts/run_sparse_indexer_k1_doctor.py | 6d98b7b2016ca47131a8a64ccf36e4efe0b18859257a611cc0be2e98a866bb87 |
| scripts/compare_sparse_indexer_resume.py | 75289c34d48e123cb9221c0d980b202c5c8e66750b607a9ae0715375836092bb |
| experiments/architectures/translation-supervised-sparse-indexer-k1-screen.yaml | 25c45ac0a2165f548725749da686b7efeaeb1ee491574a8268179ea61821bfef |

Image. Image B, built by `infra/slurm/host-single-node/build-architecture-image.sbatch`
from a fresh clean clone at commit B (commit A plus this file and its ledger
row, documentation only). Every GPU job uses image B; its image ID, repo
digest, git SHA and source-tar SHA-256 are written into each manifest by
`scripts/fill_sparse_indexer_k1_manifests.py` and verified at job start by
`scripts/verify_compute_provenance.py`. The entry point verifies this file's
digest and its ledger row inside image B before any work.

Bundle. `k1-bundle-v1.json`, schema `cotcodec-k1-bundle-v1`, licence id
`LicenseRef-cotcodec-k1-bundle-v1` with a per-source licence manifest inside.
It is a deterministic function of the raw directory (whose
`raw-manifest.json` records every file's revision, size and SHA-256 and every
streamed ParaDocs file's compressed bytes consumed), the code above and the
receipted tokenizer. The digest is in the section "Bundle digest" below.

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
algorithms, TF32 matmuls (products of bf16 values are exact; accumulation is
fp32), no torch.compile and no code generated at run time.

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
1e-3 is within 1 percent of the minimum it is selected. The record is written
and its SHA-256 taken before any audit prompt is read; the evaluation workers
verify that digest. Indexers at non-selected learning rates are never
evaluated on the audit partition. This is a registered deviation from the D21
contract's "development languages" wording (see Design decisions).

## Evaluation (audit partition only)

The 488 Belebele passages are split by link with
`split_passage_ids(seed=42)`: development 122 passages and 224 questions,
audit 122 and 230, primary 244 and 446. This screen reads only the audit
partition (and, for the pre-check, the development partition); a read outside
the declared partition raises and the job exits 3. The primary partition is
never read.

- Cross-script pairs (14): (needle X, query en) and (needle en, query X) for
  X in {ja, ko, bn, ta, el, he, ka}. Crossed design: all 230 audit questions
  in every pair, 3,220 families.
- Same-script pairs (10, descriptive): the same 230 questions for X in
  {id, tr, sw, nl, it}, 2,300 families.
- Context: exactly 8,192 tokens = [151643] + needle-language haystack
  documents (FineWeb-2 test split for X; the FineWeb shard for English), each
  followed by "\n\n", with the Belebele passage (followed by "\n\n") inserted
  at the haystack document boundary nearest to depth × (8,191 minus the needle
  block length); the haystack tail is cut. Depth cycles through
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
condition means; xi_rel_T = macro over pairs of G(MN) − G(CX). If any pair has
R_T(c) − R_rand(c) of 1 point or less, xi_rel_T is not evaluable.

Interval: se_cluster is the SD of a passage-cluster bootstrap over the 122
audit links (B = 10,000, NumPy seed 42, macro-averaging inside each replicate,
seeds held fixed); s_seed is the SD of the three per-seed values; the decision
interval is point ± 2.576 × sqrt(se_cluster² + s_seed² / 3). The same
construction applies to xi_rel_T. The percentile bootstrap interval and the
per-seed values are reported alongside.

Multiple choice: acc_norm, the option with the highest sum of token
log-probabilities divided by its UTF-8 byte length, each option scored as a
continuation of the full prompt (context + "\n\n" + question + "\n"), four
options, chance 25 percent.

## Validity gates (evaluated before any verdict)

- V1 adequacy, per target, at every seed: English ML R_ind ≥ R_T(ML) − 5.
- V2 bug tell: R_ind(ML) above R_T(ML) + 1 at any seed holds the read for
  investigation (registered tolerance; the harness default is 0).
- V3 integrity: no non-finite value on a selection prompt; every selection at
  most 1,024 + 3 tokens; every evaluation unit present exactly once; bundle,
  preregistration, model receipt, image and LR-freeze digests verified.
- H1 selection headroom: max over T of macro [R_T(CX) − R_rand(CX)] ≥ 10
  points to interpret at all, ≥ 20 points for a NEGATIVE.
- H2a: dense CX acc_norm macro over the 14 pairs, percentile cluster-bootstrap
  99 percent lower bound above 30 percent.
- H2b: needle-present minus needle-absent dense CX accuracy on the 300 paired
  cells (plain mean), 99 percent lower bound above 0 and point at least 5
  points.

Pre-step: H1, H2a and H2b (and the no-haystack reference) are evaluated on the
development pre-check with the dense model only, before any indexer is
trained. If any of the three fails, K1 does not run on 0.6B; the next step is
Qwen3.5-4B-Base under a new contract version and preregistration, or stop.

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
- HOLD: a V2 bug tell. VOID: a V3 integrity failure.
- V1 failure: one registered extension (epochs 2 and 3, the frozen-LR
  indexers only), evaluated once; a target still failing V1 is inconclusive.
- INCONCLUSIVE: everything else, including a disagreement between the xi and
  xi_rel classifications and any half-width above 5 points.
- Order: VOID, HOLD, UNINTERPRETABLE, V1 extension, GO, NEGATIVE,
  INCONCLUSIVE (implemented by `harness.sparse_indexer_k1_stats.k1_verdict`).
- Multiplicity: two targets, each at 99 percent. Same-script rows, Lambda,
  hm, U, U_k and all per-language, per-direction, per-layer and per-position
  tables are descriptive and uncorrected.

## Seeds, sample sizes and sensitivity

- Seeds 42, 43, 44 set indexer initialisation only; stream order, passage
  split, prompts and bootstrap use seed 42 or SHA-256 orders. Seed variance is
  therefore initialisation variance only.
- 3,220 cross-script families in 122 passage clusters (6,440 prompts), 2,300
  same-script families, 200 ML prompts, 300 needle-absent cells.
- SE(xi) is not known in advance. If the cluster-level SD of the family excess
  were 10 points, se_cluster would be about 0.9; with a seed SD of 1 point the
  combined SE is about 1.07, the 99 percent half-width about 2.8 and the
  minimum detectable effect (two-sided 0.01, power 0.8) about 3.7 points,
  under the GO threshold of 10. A NEGATIVE needs a half-width of at most 5
  points (combined SE at most 1.94), which the rule enforces, so an
  underpowered read cannot be called NEGATIVE. The development pre-check
  reports se_cluster of Delta_T and Delta_U as a calibration.

## Compute

| Job | GPUs × minutes | Cap (GPU-h) |
|---|---|---|
| Smoke | 1 × 7 | 0.12 |
| Development headroom pre-check | 1 × 6 | 0.10 |
| Resume R0, R1, R2 (four workers share one GPU) | 1 × 8, 1 × 9, 1 × 8 | 0.43 |
| K1 main | 4 × 30 | 2.00 |
| Total | | 2.65 |
| Conditional V1 extension | 4 × 22 | 1.50 |

The smoke job projects the main job's wall time from measured per-layer
target, indexer and teacher timings. The main job's minutes may be lowered
from that projection but never raised above 30; if the projection exceeds the
2.0 GPU-h cap the main job does not run under this id.

## Resume test

R0 trains to step 40 uninterrupted with a checkpoint every 10 steps. R1 runs
the same command, holds after step 25 until the Slurm signal 180 seconds
before its limit, saves on that signal, writes `checkpoint.ready` (with the
line `trigger=SIGUSR1` that the batch script requires) only after all four
workers acknowledged the save (a stale marker is deleted on receipt of the
signal; periodic saves never write it) and exits 75. R2 is a fresh job resumed from R1's
`phase-0a-k1/checkpoints` and trains to step 40. The resume is valid only if
R2's final state (parameters, Adam moments and step counters of every
indexer) equals R0's bit for bit and R1 terminated with
`signal_USR1_checkpoint_confirmed` (`scripts/compare_sparse_indexer_resume.py`).

## Infrastructure failures and exclusions

A run is void, with no partial read, when: the job does not end COMPLETED
with exit code 0:0 (an exit 75 followed by a valid resume is allowed); the
signal checkpoint times out; any startup digest check fails (exit 2); an
integrity failure occurs (exit 3); provenance verification fails; the smoke
gates fail; or the orx node lacks its ORX_RESULT line. A re-run uses a new run
root and this same id only if no audit number was produced; otherwise it needs
a new id.

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
- Smoke timings, the projection and the main job's measured per-phase timings.

## Bundle digest

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
  met), 7,494,905,291 (en-hi, quota met) and 4,104,691,058 (en-km, all files,
  quota not met); 16 to 60 MB per same-script pair. After filters, en-km
  supplied 1,552,984 of its 1,759,426-token target; the 207,442-token
  shortfall raised each same-script target to 1,811,287. Realised packed
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

## Freeze procedure

1. Merge commit A; build image A from a fresh clean clone with
   `COTCODEC_REPO` pointing at it (never the shared `~/cotcodec`).
2. Rebuild the bundle with `infra/slurm/host-single-node/build-k1-bundle.sbatch`
   in image A, reading the same raw directory (fetch is skipped when
   `raw-manifest.json` exists). The bundle SHA-256 must equal the value above.
   If it differs, this draft is amended with the image-A value and the reason
   before freezing.
3. Freeze this file, commit it with the ledger row (commit B), build image B,
   run the K1 doctor in image B, fill the manifests and run the orx nodes in
   the order smoke, headroom-dev, R0, R1, R2, main.

## Design decisions

Each was left to the program owner by the reviewed plan; the draft takes the
most defensible choice and states why. The owner logs or overrides them before
freezing.

1. Harness code on GPUs. Program decision D7 settles it: reviewed, tested,
   committed harness code is project code. The K1 harness generates no code at
   run time (no torch.compile, no model-written kernels).
2. TED2020 excluded (D4). K1 uses permissively packaged parallel data only.
3. Cross-script bilingual data: stream until the 1.2× quota is met, capped at
   9 GB of compressed input per pair. The yield probe (1 GB per pair,
   2026-10-07) kept 278,595 (en-th), 206,703 (en-hi) and 331,407 (en-km) item
   tokens per GB; the full fetch then consumed 6.34, 7.49 and 4.10 GB, and
   en-km (whose two files hold 4.10 GB) ended 11.5 percent short. The
   shortfall is refilled from the same-script pairs in equal shares and the
   realised shares are reported (en-km 12.6 percent of bilingual tokens).
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
   (review defect D2a), and H2b separates retrieval from parametric answering
   of possibly memorised FLORES passages (D7).
7. NEGATIVE is equivalence-style and needs the scale-free co-statistic:
   xi_rel ≤ 0.1 with upper bound below 0.2. GO needs the xi_rel lower bound
   above 0. Reason: the additive xi penalises a uniformly weaker indexer and
   can mask a cross-script deficit (D2b, D2c).
8. Combined seed-plus-cluster interval (D3), matching the D21 contract's own
   noise model.
9. Base ladder: 0.6B now; if the pre-check or the audit read is
   UNINTERPRETABLE, the fallback is Qwen3.5-4B-Base (named in the D21 contract
   and the dossier; receipt on the host) under a new contract version and
   preregistration. Qwen3-1.7B-Base is not in the contract and is not used
   without one.
10. Crossed evaluation: all 230 audit questions in all 14 pairs (3,220
    families) instead of an 86-question subset per pair. Reason: it removes
    the confound of item difficulty with language (D10) at about +0.1 GPU-h.
11. LR selection per target on mean stream-dev KL (D13). Reason: the
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
14. Same-script descriptive rows included (D6), at about 0.05 to 0.1 GPU-h.
15. V1 at every seed (the contract's doctor gate) and a V2 tolerance of 1
    point (D13).
16. V1 extension data: epochs 2 and 3 of the same stream (D11). Reason: the
    cross-script yield makes fresh data infeasible, and a pre-built 60M-token
    stream would not fit the 512 MiB study-artifact limit with the
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
    image B (CPU, no network) and its receipt is recorded with the node.
