# Q3 dense headroom pre-check v2 (q3-dense-headroom-precheck-v2)

Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row
for the freeze time and `git_head_at_freeze`. The design is v1's
(`q3-dense-headroom-precheck-v1`, frozen 2026-10-08 after D32), kept unchanged
by program decision D36 (`program/decisions.md`). The repairs and limits
listed under "Changes from v1 (D36)" and design decisions 16-21 were accepted
in D42 and D44, as amended by them, after a narrow re-check of the measured
limits; D42 amends D36 (iii) for the Qwen3.5-4B-Base lane (decision 18) and
authorised the second development timing job, whose measurement of the fixed
path (Slurm 810) sets the 4B limit by D36's rule (decisions 20 and 21); D44
closed the re-check and set that limit at 32 minutes, the largest of the
estimates computed from the measurement. No lane job of this experiment ran
before the freeze; every lane job verifies this file's digest against its
ledger row at start-up and refuses code whose SHA-256 differs from the table
below. Both development timing jobs ran before the freeze (Compute): Slurm 766
on the 4B path as it was before the fix (cuDNN's attention on) and Slurm 810
on the fixed path (cuDNN's attention off).

## Purpose and claim level

v1 asked, densely and on the development partition of the K1 bundle only,
what any K1 v3 needs to know first (its Purpose section, carried here
unchanged): the dense block top-k recall headroom over random on the MN, CX
and ML legs, dense multiple-choice accuracy and the needle effect, a
candidate non-literal adequacy floor, the entity-anchored share and the
entity-controlled reads, what a purely literal selector and a
language-agnostic noisy copy of the target read under K1's statistics, and
headroom by tokenizer fertility, on Qwen3-0.6B-Base and the registered
fallback Qwen3.5-4B-Base. It is measurement-only. Its decisions say which K1
v3 designs the measured headroom supports and on which base; they never say
whether an indexer loses more cross-script recall than its target. Nothing
here is a K1 result, positive or negative.

v1 ended INCOMPLETE (D36; evidence
`program/evidence/2026-10-08/q3-dense-headroom-precheck/README.md`, with the
operator log, the independent verification and both lanes' files). Jobs 727
and 730 used 0.4189 GPU-h. Its Qwen3-0.6B-Base receipt (Slurm 727, 278 s,
receipt SHA-256 `bfe4a7c3...`) is valid under every v1 void rule: K1 smoke 452
reproduced to within 1e-6 points (T:hs 26.4506, T:mp 26.0806, T:hm 26.2663,
rand 12.4803); lane NOT_VIABLE (H1_CX 12.25 points on target hs, 99 percent
interval 8.98 to 15.59; H2a 31.43; H2b -3.93, so `h2_status` FAIL); lexical
confound, entity control and null calibration NOT_EVALUABLE; floor
NOT_VIABLE; fertility association STRONG; 20 development passage clusters,
half the questions entity-anchored. Two code defects left no combined read:
every receipt the frozen code can write records `slurm_job_id: null`, which
the frozen summariser refuses; and the Qwen3.5-4B-Base lane (Slurm 730) ran
CPU-bound (GPU idle when sampled, one core busy, about 61 s per 16-unit chunk
against an 11-minute estimate for the lane), ignored SIGUSR1 and was killed at
its 21-minute limit with 18 of 74 chunks done and no receipt. Neither is a
design question; the 4B lane is the informative one, since on 0.6B a
NEGATIVE-capable K1 v3 already looks excluded descriptively (H1_CX 99 percent
upper bound 15.6) and H2 fails because the model barely answers cross-script
questions.

v2 runs both lanes again with v1's data, statistics, decision rules,
thresholds and D32's amendments unchanged, repairs the two defects, and adds a
validity gate that ties v2's 0.6B lane to v1's job-727 receipt. v1's 0.6B
receipt is reported beside v2's; it is not v2's read.

## Changes from v1 (D36)

Every difference from `q3-dense-headroom-precheck-v1`, and why. Nothing else
differs: the sections Data, Selectors, Metrics and statistics, Decision rules
and "Seeds, sample sizes and sensitivity" below are v1's text, except the two
substitutions in item 4 (`tests/test_dense_headroom_v2_prereg.py` checks it),
and v1's design decisions 1-11 and 13-15 are carried with only decision 12's
caps changed.

1. Identity. New experiment id `q3-dense-headroom-precheck-v2` everywhere; run
   roots `/home/kevin/cotcodec-runs/q3-dense-headroom-precheck-v2/` plus the lane id;
   templates under `experiments/manifests/q3-dense-headroom-precheck-v2/` (the
   two lanes, same inputs, models, argv shape, CPUs, memory and container
   profiles as v1's, and the two timing jobs); v2's entry point, doctor, filler and
   summariser (`scripts/*_v2*.py`). v1's frozen registration, code table and
   files are unchanged; v2 imports v1's data, statistics and torch modules and
   v1's filler and summariser rules byte for byte (the imported rows of the
   code table).
2. Job binding (D36 (i), decision 16). Receipts record their Slurm job from
   `job.env`; the summariser also requires that it was read there. Why: every
   v1 receipt had `slurm_job_id: null` and v1's summariser refused it (job
   727).
3. Signals (D36 (ii), decision 17). SIGUSR1/SIGTERM blocked from process start
   and consumed at safe points by `SignalGuard`, which also repairs a replaced
   handler. Why: job 730 never saw Slurm's SIGUSR1 (Triton's LLVM had replaced
   CPython's handler).
4. Evaluation (D36 (iii), decision 18). The evaluation module `harness/dense_headroom_torch_v2.py`
   (literal blocks on the device before the layer loop, the hybrid cache
   cloned instead of deep-copied, the first option token from the host array;
   all bit-equal to v1, tested) and, on the hybrid lane only, torch's cuDNN
   attention turned off, which removes the CPU bottleneck (a cuDNN graph built
   for every new sequence length). That switch is not bit-equal to cuDNN, so
   on the 4B lane it departs from D36 (iii), which allows no change to a
   computed quantity; D42 (i) amends D36 (iii) for that lane (decision 18 says
   why and what is reported). Why: job 730 ran CPU-bound at about 3.8 s per
   unit; the first timing job located the cost and the second timed the fix.
   The carried Selectors text says "copied per option for Qwen3.5 (v2's `clone_cache`, the
   values v1's deep copy held)" where v1's said "deep-copied per option", and
   the Decision rules text names `scripts/summarise_dense_headroom_precheck_v2.py`
   where v1's named its own summariser (which v2's calls for the void rules).
5. Validity gate (D36, decision 19). v2's 0.6B lane must reproduce v1's job-727
   receipt statistics to 1e-6 as well as smoke 452 (0.5 points); otherwise
   the read is INVALID and the 4B lane does not run (filler and summariser).
   Why: D36 ties the repaired code path to the one valid v1 measurement.
6. Limits and caps (D36, D42, D44, decision 20). Both measured: 0.6B lane 12
   minutes (0.20 GPU-h, from job 727's measured 278 s); 4B lane 32 minutes
   (32/60 GPU-h, 0.5333, from the second timing job's measurement of the
   fixed path, Slurm 810, by D36's rule at the largest of the three estimates
   computed from it, D44; it replaces the 45 minutes, 0.75 GPU-h, that an
   earlier draft had projected from the first timing job's warm-shape units);
   two timing jobs of 6 minutes (0.10 GPU-h each); total 0.933 GPU-h within
   D36's 1.5. v1 had 9 and 21 minutes (0.15 and 0.35 GPU-h, D26's 0.5) from
   estimates; the 4B lane needed several times its 21 minutes.
7. The development timing jobs (D36, D42 (ii), decision 21; Compute). New in
   v2; both ran before the freeze: Slurm 766 on the 4B path as it was before
   the fix (cuDNN's attention on), Slurm 810 on the fixed path at the code
   head, starting with the lane's start-up and its `attention_backend_check`.
8. Reporting. Receipts add per-chunk times, the signal guard's record and the
   job binding; the summariser reports the job-727 reproduction and v1's
   0.6B receipt beside v2's.
9. Corrections of v1's text that change no rule: re-tokenized Qwen3.5-4B-Base
   contexts range from 49 to 10,481 tokens (job 730's development artifact),
   so not every one is shorter than 8,192 tokens as v1's Data section says
   (the matched budget is a fraction of each context's length, unchanged); the
   development read has 20 passage clusters (job 727), not "about 19"; the
   lane has 74 chunks of at most 16 units (28, 18, 10 and 18 by stage).
10. Files changed after the first timing job (Slurm 766, the image built
    from `71dc954`): `scripts/run_dense_headroom_precheck_v2.py` (cuDNN's
    attention off on the hybrid lane, the `attention_backend_check`, the
    signal block limited to runs of the file as the program, so that
    importing it in tests does not block the signals of their child
    processes, and, for D42 (ii), the timing profile starting with the lane's
    `attention_backend_check`), `harness/dense_headroom_v2_lanes.py` and the
    4B template (the 4B limit and cap; both timing jobs in the caps),
    `scripts/run_dense_headroom_precheck_v2_doctor.py` (checks of the backend
    record and of the timing profile's check),
    `scripts/fill_dense_headroom_precheck_v2_manifests.py` and the second
    timing template (D42 (ii): a fresh run root), and this file. Files changed
    after the second timing job (Slurm 810, the image built from `87242fa`):
    only `harness/dense_headroom_v2_lanes.py` and the 4B template (the
    measured 4B limit and cap, first 30 minutes and 0.50 GPU-h from the
    stage-mean scaling, then 32 minutes and 32/60 GPU-h from the largest of
    the three estimates, D44, and their comments) and this file; every other
    tabled file it ran has the digest tabled here. Each timing job's code
    digests are in its receipt.

## Identity

Code. The lanes run from the source baked into an image built by
`infra/slurm/host-single-node/build-architecture-image.sbatch` from a fresh
clean clone of the commit that holds this file's ledger row. The entry point
refuses to start unless every file it runs (the ledger verifier
`scripts/preregister.py` among them) has the SHA-256 tabled here; the manifest
filler refuses unless every tabled file has this digest in the checkout and at
the image's commit. The four manifest templates are tabled (the two lanes and
the two development timing jobs), so their argv, run roots, CPUs, memory, mounts
and host paths are bound: the filler refuses a template with another digest
and a filled manifest that is not the template with only its `FILL-*` values
replaced. The rows from `harness/dense_headroom_data.py` down are files tabled
by frozen registrations and imported unchanged: v1's data, statistics, torch
selectors, entry point (whose receipt-writing code the doctor runs beside
v2's), doctor, filler and summariser by `q3-dense-headroom-precheck-v1`,
`harness/sparse_indexer_bank.py` by `q3-k1-throughput-probe-v1`, the others by
`q3-k1-localization-screen-v1` (the same SHA-256 as in those registrations).
`infra/slurm/host-single-node/docker-research.sbatch` is unchanged (SHA-256
`2a10c9c7...`, recorded in every job's `job.env`).

| File | SHA-256 |
|---|---|
| scripts/run_dense_headroom_precheck_v2.py | e36e021b70834a2ede73ab7542ab8f5e45ace2c5c554d7e489d2a3a7bf8ae2ba |
| harness/dense_headroom_v2.py | 49f340ac46c80fa312d10e29bb3eaa45d95e574b9a598f47379b0e1effa5b5e1 |
| harness/dense_headroom_v2_lanes.py | 7b75d305489e36386d1a11b654764954a08d1dbb6158ec4ba4b38202cccc8881 |
| harness/dense_headroom_torch_v2.py | 34963c32746c9d6b4384cb32b9ab37b1a4966b4586923ba43da036bdc6da0cbe |
| scripts/run_dense_headroom_precheck_v2_doctor.py | 52011a26dd2b318465a5aaddb9fcaad2bd8ea8b98599377fa7584d52f547d697 |
| scripts/dense_headroom_v2_signal_shim.py | 40be0760437253ca7290b358245d8ce61ff5c9886e930a833a3768765c620fa1 |
| scripts/fill_dense_headroom_precheck_v2_manifests.py | 56c28491988c5a2422e4fb8127d74d62ef557f9cb1b622ab6d50c151001ad6e2 |
| scripts/summarise_dense_headroom_precheck_v2.py | cd5b6af45a93cf1b04faaffe1dfd72b82d9a7cb3ffcfed2e512de04a8ce2deae |
| scripts/preregister.py | 21fc3ef0ed0958b1600ce742c3b4f8d557d0a298635acb20342710eb814b2c0d |
| experiments/manifests/q3-dense-headroom-precheck-v2/q3-dense-headroom-v2-0p6b.yaml | bf28d0b75d13d4b0ea825b481f3c9f8d17026dae8ce0d24b910c4d7f178c4cc1 |
| experiments/manifests/q3-dense-headroom-precheck-v2/q3-dense-headroom-v2-4b.yaml | c34f4fdc5748edbb0c6b43e2eb4d1744d79ac074f6531fe193c2ad858cef267a |
| experiments/manifests/q3-dense-headroom-precheck-v2/q3-dense-headroom-v2-timing-4b.yaml | 007b64f91a53eefcbadeaf0971a46701769210d7d1b34383a7f78f70af353c6c |
| experiments/manifests/q3-dense-headroom-precheck-v2/q3-dense-headroom-v2-timing-2-4b.yaml | 3fc8874d0cdee6992aa937a00e8308d4d1b451c9625079314aaf6dca6b323093 |
| harness/dense_headroom_data.py | ee78549e257631035aef0d52c5243f6bae969fd2c4f4a1e43bb8779bdf524003 |
| harness/dense_headroom_stats.py | a94d1ceee80fe3e95f2f36af0cbda51644846594d5fc9ccf69fcb90c8215d195 |
| harness/dense_headroom_torch.py | 6dd8ff1f9cbcbd7d3faaecd1c94ab7908c12e2aea16b480bc56735e4b27547be |
| scripts/run_dense_headroom_precheck.py | 85a22c63be3336121e451d224ea6dae68dc1078f289c0f440bef98eb53669577 |
| scripts/run_dense_headroom_precheck_doctor.py | 1a02188fefae40d2522840a26662478ed13fd2164f60b40b4b628dc38619cf7c |
| scripts/fill_dense_headroom_precheck_manifests.py | 0c5505cce47c972b0631011d5c9c069341e1830b84ab6838be9a37b693cb9266 |
| scripts/summarise_dense_headroom_precheck.py | 0a4663a19877ed13bf06ffda09ac810ad66d31cb7e56471aa73a5a6001b8daaf |
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

Models (receipts on the host, read 2026-10-07; unchanged from v1):

| Lane | Model, revision | Receipt SHA-256 | Artifact root | tokenizer.json | Layers with softmax attention |
|---|---|---|---|---|---|
| qwen3-0.6b-base | Qwen/Qwen3-0.6B-Base `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` (apache-2.0, https://huggingface.co/Qwen/Qwen3-0.6B-Base) | e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df | 7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0 | c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539 | all 28 (16 query, 8 key-value heads, head dimension 128) |
| qwen3.5-4b-base | Qwen/Qwen3.5-4B-Base `1001bb4d826a52d1f399e183466143f4da7b741b` (apache-2.0, https://huggingface.co/Qwen/Qwen3.5-4B-Base) | 253a14185bcff0762b8a43944635a550055d3346fe16c416d6bcfe4460793cfe | c7fbfd6bd1c73b9a0080decf794f5e4333c955f2704591affc61b0a9ac850e42 | fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927 | the 8 full-attention layers 3, 7, ..., 31 of 32 (16 query, 4 key-value heads, head dimension 256, rotary on 64 dimensions); the other 24 are gated-delta layers |

The Qwen3.5-4B-Base checkpoint is stored as `Qwen3_5ForConditionalGeneration`;
the text model is loaded with `AutoModelForCausalLM` (`Qwen3_5ForCausalLM`,
vision and multi-token-prediction weights ignored). Its gated-delta layers run
flash-linear-attention 0.5.2's Triton kernels from the pinned image (library
code, compiled by Triton at first use; https://github.com/fla-org/flash-linear-attention).
In transformers 5.15.0 only the chunked kernel resolves to flash-linear-attention;
the one-token recurrent step and the short convolution use transformers'
torch implementations (checked in the image, 2026-10-08), as they did in v1.

Development artifacts. Derived by v1's unchanged
`harness.dense_headroom_data.derive_dev_artifact`, so they are byte for byte
v1's: SHA-256 `c1c455d8...` for Qwen3-0.6B-Base (job 727's) and `b5210f79...`
for Qwen3.5-4B-Base (job 730's, re-derived by both timing jobs: `b5210f79...`, equal to job 730's).
Their internal `experiment_id` field names v1, whose derivation they are.

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
  development haystack of the needle language or of the query's language
  (ties to the lower id; on a cross-script prompt both lists are removed, so
  the query's own function words are not content) and do not decode on their
  own to text without a letter or digit. Recall is the exact expectation under
  uniformly random tie-breaking at the k-th score. Layer-independent. LEX
  matches every shared token, entities among them: it measures lexical
  overlap, not entities.
- N:T:sigma:seed, the block-score null: natural-log block scores of target T
  (hs, mp; floored at 1e-30) plus sigma times standard normal noise, sigma in
  {0.25, 0.35, 0.5, 0.7, 1, 1.4, 2, 2.8, 4} (a geometric grid of ratio about
  the square root of 2), seeds 42, 43, 44; the noise of a (seed, unit, layer) comes
  from a generator seeded with SHA-256 of those three, so its law is identical
  on every leg. It is the identification refuter's null on the measured score
  shapes: a copy of the target with language-agnostic error.
- T:hs@fixed, T:mp@fixed, rand@fixed: the K1 budget of 256 blocks whatever L
  (equal to the matched budget at 8,192 tokens); descriptive.

Multiple choice is K1 v1's acc_norm: each of the four options scored as a
continuation of the full prompt by its summed token log-probability over its
UTF-8 byte length, an exact tie to the lowest option index. The prompt's cache
is cropped back between options for Qwen3 (K1 v1's code) and copied per
option for Qwen3.5 (v2's `clone_cache`, the values v1's deep copy held), whose recurrent state cannot be cropped; on tiny models
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
  shared tokens reads with no cross-lingual matching error at all. It is a
  lexical-overlap reading (entity anchors are one source of overlap,
  paraphrase overlap of a same-language question another); only the
  comparison of the controlled and anchored subsets bears on entities.
- The block-score null under K1's statistics: for each target and sigma, xi
  and xi_rel with the seed-plus-cluster interval (three seeds), the English ML
  adequacy of K1 v1's V1 rule (null recall at least the target's minus 5
  points at every seed), the English ML loss (target minus null) per seed and
  its seed mean, and its G(MN) on controlled families with its 99 percent
  interval.
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
    read further and the combined read is INVALID.
  - NEGATIVE_CAPABLE: H1_CX at least 20 with its 99 percent lower bound at
    least 10, and h2_status not FAIL. A K1 v3 with a NEGATIVE region may be
    designed on this base.
  - GO_ONLY_CAPABLE: H1_CX at least 10, h2_status not FAIL, and not
    NEGATIVE_CAPABLE. A K1 v3 on this base may register GO only; it cannot
    register a NEGATIVE (the inherited H1 at least 20 rule).
  - NOT_VIABLE: otherwise. No K1 v3 on this base.
- lexical_confound: PRESENT when the literal selector's xi_rel point on all
  families is at least 0.10 (K1 v1's NEGATIVE limit) for either target;
  ABSENT otherwise; NOT_EVALUABLE when xi_rel is not evaluable. It is a
  lexical-overlap confound and is not attributed to entities; ABSENT comes
  from one heuristic selector and is weak evidence that no confound exists.
- entity_control: SUFFICIENT when at least 30 percent of the questions are
  unanchored and on them the literal selector's xi_rel point is below 0.10 for
  both targets (removing the anchored questions removes the lexical confound
  in K1's units); INSUFFICIENT otherwise; NOT_EVALUABLE when not evaluable.
- null_calibration per target: CENTRED when, at every sigma whose null passes
  V1 at every seed, the seed-mean |xi| is at most 2 points and |xi_rel| at most
  0.10, and at least one such sigma has a seed-mean English ML loss of at least
  2.5 points (half of V1's 5-point tolerance), so that the null was tested
  near the V1 boundary and not only on near-exact copies of the target;
  NOT_CENTRED when a V1-adequate sigma breaks either limit; NOT_EVALUABLE when
  no sigma passes V1, xi_rel is not evaluable at one that does, or every
  V1-adequate sigma is within the limits but none reaches 2.5 points.
- floor_candidate (an indexer's 99 percent lower bound of G(MN) on
  entity-controlled families at least 0.5, for the chosen target): VIABLE when
  the target's controlled MN headroom is at least 10 points, the literal
  selector's controlled G(MN) point is below 0.5, and some sigma whose null
  passes V1 and whose seed-mean English ML loss is at least 2.5 points (the
  reach rule of null_calibration) has a controlled G(MN) whose 99 percent
  lower bound is at least 0.5 (a realistically imperfect, V1-adequate noisy
  copy of the target passes the floor as an indexer would be judged, not only
  the near-exact copy at sigma 0.25); NOT_VIABLE otherwise (reasons listed);
  NOT_EVALUABLE when the controlled MN headroom is not evaluable. The points
  and both bounds of the literal selector's and every null's G(MN) are
  reported, with each null's English ML loss.
- fertility_association: STRONG when |Spearman| between needle fertility and
  CX headroom over the seven held-out languages is at least 0.75, WEAK
  otherwise (descriptive; with seven languages it cannot separate fertility
  from script or from being unseen in indexer training).

Combined read of the two lanes
(`scripts/summarise_dense_headroom_precheck_v2.py`,
`harness.dense_headroom_stats.combined_recommendation`), applied once both lane
receipts exist, or once the 0.6B lane's receipt is INVALID:

- INVALID first: if any lane is INVALID (the 0.6B lane's K1 smoke
  reproduction failed), the combined design is INVALID. The failure means the
  shared selection code path does not reproduce K1 v1's measurement, and the
  4B lane runs the same code, so neither lane's read is a result: no base, no
  design and no stop is read, and a repair is a new experiment id. The 4B lane
  is not submitted unless the 0.6B lane's receipt reports the smoke
  reproduction REPRODUCED (Freeze procedure, step 4); the filler refuses to
  fill the 4B lane without that receipt.
- Then INCOMPLETE: a lane without a completed, non-void receipt makes the
  read INCOMPLETE.
- Base: the first lane in the order Qwen3-0.6B-Base, Qwen3.5-4B-Base that is
  NEGATIVE_CAPABLE (design NEGATIVE_CAPABLE_V3); otherwise the first that is
  GO_ONLY_CAPABLE (design GO_ONLY_V3); otherwise NO_K1_V3: no K1 v3 is
  designed on these bases and Q3's K1 line is reported as stopped for
  insufficient dense headroom (a pre-result, not a negative).
- Requirements of any K1 v3, always, as D26 states them: a seen-script
  cross-script condition (the bundle's development partition has none, so it
  is not measured here), an entity-controlled question set, a non-literal
  adequacy floor (the floor registered here when floor_candidate is VIABLE,
  otherwise a redesigned one), a new experiment id and the research gauntlet.
  No measurement here removes any of them; a change to D26 is the program
  owner's decision in `program/decisions.md`. The chosen base's flags only
  add: the GO and NEGATIVE statistics computed on the entity-controlled set
  (not only reported beside it) unless lexical_confound is ABSENT; anchor
  masking or a lexical-overlap covariate unless entity_control is SUFFICIENT;
  a null-calibrated statistic unless null_calibration is CENTRED for both
  targets; H2 re-tested under K1's bounds on the v3 audit read unless the
  chosen base's h2_status is PASS (a POINT_ONLY lane met only the points).

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

## Validity gate: v1's job-727 receipt (D36)

v2's Qwen3-0.6B-Base lane must reproduce v1's job-727 receipt
(`program/evidence/2026-10-08/q3-dense-headroom-precheck/lane-0p6b-727/receipt.json`,
SHA-256 `bfe4a7c33cca3cf106370876f2843239c7c88a4f3c4fb70798f8a8d6404508ba`)
as well as K1 smoke 452 (within 0.5 points, as in v1). The comparison
(`harness.dense_headroom_v2.v1_reproduction`) covers these fields of the
receipt, leaf by leaf:

- `report`: every registered statistic and its intervals, the per-pair,
  per-leg, per-layer and per-depth tables, tie counts, the matched budgets, the
  fixed-budget rows, the entity, fertility, floor and null sections with every
  per-seed value, the K1 v1 pre-step and the smoke-452 recomputation;
- `decisions`, `coverage`, `artifact_counts`, `selectors` and
  `attention_layers`;
- `hashes.dev_artifact_sha256` (the development artifact, byte for byte).

Every numeric leaf must be within 1e-6 (absolute, in the field's own unit:
points, fractions, counts) of v1's and every other leaf must be equal, with
the same keys and list lengths everywhere. Timings, versions, code digests and
job fields are not statistics and are not compared. Exact equality is
expected: the 0.6B lane runs with strict deterministic torch kernels on the
same hardware and the same pinned libraries (`uv.lock` unchanged), and v2's
evaluation equals v1's bit for bit on every field (tested); the 1e-6 tolerance
is D36's. If the gate fails, the 0.6B lane is INVALID and so is the combined
read, under v1's rule for a failed K1 smoke reproduction (decision 11): the
shared code path no longer reproduces the measurement, and the 4B lane is not
run (the filler refuses it). No exact gate exists for the 4B lane (v1 has no
4B receipt); its lane runs with deterministic torch kernels in warn-only mode
(decision 9), flash-linear-attention's Triton kernels and, in v2, PyTorch's
flash or memory-efficient attention in place of cuDNN's (decision 18), so its
numbers are compared with nothing, as in v1; its receipt reports how far
cuDNN's attention would move its first unit. The timing jobs compared v1's and
v2's evaluation on real 4B units on the GPU: Slurm 766 two units with cuDNN's
attention, Slurm 810 five units (one or two in every stage) with the lane's
backend, cuDNN's attention off; every field was bit for bit equal. Neither
this gate nor the smoke reproduction covers the 4B lane's attention backend,
which the 0.6B lane never switches; `attention_backend_check` is the only
check of the switch, and it is descriptive (D42 (i)). In Slurm 810 it ran on
the GPU as the lane runs it: on the lane's first combined unit, cuDNN's
attention and the lane's differed by at most 1.15 points of recall and 0.011
in an option score, with the same budgets, largest selections, tie counts and
answer.

## Compute

| Job | GPUs x minutes | Cap (GPU-h) |
|---|---|---|
| Development timing job (D36; before the freeze; done, Slurm 766) | 1 x 6 | 0.10 |
| Second development timing job (D42 (ii); before the freeze; done, Slurm 810) | 1 x 6 | 0.10 |
| Qwen3-0.6B-Base lane | 1 x 12 | 0.20 |
| Qwen3.5-4B-Base lane | 1 x 32 | 0.53 |
| Total | | 0.93 |

The 4B lane's cap is 32/60 GPU-h (0.5333) and the total 0.933 GPU-h; the
table rounds them to two decimals. The total is the sum of the registered
caps, D22's counting rule, within D36's v2 cap of 1.5 GPU-h (both timing jobs
included, D42); with v1's 0.4189 GPU-h the dense pre-check stays far below 8
GPU-h. The limits use D36's arithmetic: twice the measured full-lane
evaluation (evaluation and statistics), plus start-up, plus the 3-minute
SIGUSR1 lead, rounded up. Every input is measured: for the 0.6B lane by v1's
job 727, for the 4B lane by the second timing job (Slurm 810), which ran the
fixed 4B path at the code head on the GPU (D42 (ii); below). The 4B limit is
the largest of the three estimates computed from that measurement (D44).

- Qwen3-0.6B-Base: job 727 used 278 s from `job.env` to `termination.env`,
  of which 262 s were evaluation and statistics (stage walls 132.5, 52.6,
  37.0 and 38.7 s, statistics 1.2 s) and 16 s start-up (container checks,
  bundle read, derivation 1.9 s, model load 3.0 s). 2 x 262 + 16 s is 9 minutes
  rounded up; with the 3-minute lead, 12 minutes. v2 runs the same
  computation (the validity gate above).
- Qwen3.5-4B-Base: measured by Slurm 810 on the fixed path (cuDNN's attention
  off; PyTorch's memory-efficient kernel ran,
  `aten::_efficient_attention_forward` in its torch profiles). It evaluated
  159 units for the first time, in all four stages (the registered subset and
  one more chunk of A-main and of B-absent, the latter two under cProfile,
  which only slows them). Per stage, the mean of those units, leaving out
  one-off first-use compiles (a unit over five times its stage's median: the
  first selection-only prefill, 7.4 s, and the first prefill above 8,192
  tokens, 7.6 s), is 0.43, 0.42, 0.16 and 0.34 s for A-main, B-absent,
  C-literal and D-nohaystack. The subset's contexts are shorter than the
  lane's (3,723 against 6,607 tokens on average in A-main), so each stage's
  mean is carried to the lane's mean length in that stage. Three estimates
  were computed (D44; `LARGE_LANE_ESTIMATES` in
  `harness/dense_headroom_v2_lanes.py`), each over the stages' 440, 280, 160
  and 280 units, with the one-off compiles added at their observed rate (2 in
  159 units) over all 1,160 units at the larger one's extra cost, 106 s, and a
  5 s statistics bound (job 727's took 1.2 s). Stage-mean scaling: each
  stage's mean scaled up by the ratio of the lane's mean token length in that
  stage to the measured units' (1.77, 1.58, 1.59 and 1, never below 1), 0.77,
  0.66, 0.25 and 0.34 s per unit, 658 s over the stages and 769 s of
  evaluation and statistics: 30 minutes by D36's rule. Line fit: per stage, a
  least-squares line in tokens through the same units, at the lane's mean
  length and never below the stage's mean, 0.90, 0.54, 0.24 and 0.34 s per
  unit, 678 s and 789 s: 31 minutes. The larger of the two in every stage:
  0.90, 0.66, 0.25 and 0.34 s per unit, 713 s and 824 s: 32 minutes. The 4B
  limit is the largest, 32 minutes (D44), so D36's "at least twice the
  measured time plus start-up" holds under each of the three. (The stage-mean
  scaling was chosen after a first analysis pass, kept in the evidence, came
  out over D36's cap. That pass differed from it in two ways: it fitted the
  two compiles into the per-stage figures, and it scaled to the lane's lengths
  by the line (the larger of the line at the lane's mean length and the
  stage's mean) instead of in proportion to length. The measured units of
  A-main and C-literal span only 3,600 to 3,950 tokens, so C-literal's compile
  set that stage's slope, which extrapolated 7.7 s per unit against 0.16 s
  measured: 73 minutes for the lane, over D36's cap. With the compiles treated
  as above (left out of the fits and added back as the same 106 s), the line
  gives 678 s instead of 658 s for the stages and 27.62 instead of 26.95
  minutes before rounding up, so 31 minutes, not 30. The increase is all
  A-main's, which has no compile (55 s more; the line gives B-absent and
  C-literal 35 s less): its measured units span only 211 tokens (3,614 to
  3,825), over which the line's slope is 0.16 ms per token, 3.3 times
  B-absent's 0.048 ms per token over 3,551 to 8,313 tokens, and it gives 0.90
  s per A-main unit against proportional scaling's 0.77 s. On B-absent, the
  only stage with measured units at the lane's long contexts, proportional
  scaling over-predicts them: 0.78 s against 0.60 s measured at 8,310 tokens
  (under cProfile, which only slows them), where prefill went from 0.116 to
  0.247 s and the whole unit from 0.38 to 0.60 s for 2.2 times the tokens. At
  each of the three estimates the lane's first job, run at that speed, ends in
  about 14 to 15 of its 29 useful minutes.) Start-up is everything before the
  first unit, 79 s: 2 s from Slurm's start to `job.env`, 9.7 s of the job
  outside the workload process (container creation and the epilogue, so this
  over-counts) and 67.0 s in the process: 19.6 s to the loaded model (start-up
  checks, imports, derivation 4.6 s, model load 7.1 s) and the lane's
  `attention_backend_check`, 47.4 s, which carries the first-use compiles. 2 x
  824 + 79 s is 29 minutes rounded up; with the 3-minute lead, 32 minutes (2 x
  769 + 79 s and 2 x 789 + 79 s give 27 and 28 minutes, so 30 and 31). The
  lane's first job finishes its 1,160 units inside its 29 useful minutes if it
  averages at most about 1.4 s per unit (after the 79 s start-up and the 5 s
  statistics bound), against the 0.16 to 0.43 s measured. The first timing job
  (Slurm 766) had timed the path before the fix at 3.6 to 4.1 s per cold unit,
  at which the lane would need about 75 minutes; an earlier draft set 45
  minutes from a doubled projection of its warm-shape units, which D42 (ii)
  replaced with this measurement.

Slurm sends SIGUSR1 three minutes before a job's limit. In v2 the signal is
honoured at the next chunk boundary whatever the libraries did to the
process's signal handlers (decision 17); the job then saves its completed
chunks, writes `receipt-interrupted.json` and the marker, and exits 75. In the
statistics phase it is not checked (as in v1). A job's useful time is its
limit minus three minutes: 9 and 29 minutes for the two lanes' first
jobs, each covering twice the measured evaluation time plus start-up.

Every job of a lane counts against that lane's own minutes: its first job, a
re-run of a void job and its one continuation. All of a lane's jobs run in the
lane's registered run root (the template's `run_root`). Before filling any
job, the filler reads that run root: every job directory must have ended
(`job.env` and `termination.env`), none may hold a lane receipt, and each is
charged its elapsed minutes from `job.env` `started_at` to `termination.env`
`finished_at`, rounded up, plus one (Slurm accounting is off on this host; the
extra minute covers the prolog before `job.env` and the epilogue). A later job
gets the lane's minutes minus everything charged, at least 5 (the three-minute
SIGUSR1 lead plus two useful minutes), or is refused and the lane is
INCOMPLETE. A job interrupted by a signal saves its completed chunks and exits
75; its continuation resumes `dense-precheck/checkpoints` of the lane's latest
job, which must have ended with a confirmed signal checkpoint (exit 75), has
at most the lane's minutes minus two, and is filled at most once per lane (no
job in the run root may name a predecessor). The one continuation is kept
(D36): it fits only after an earlier interruption (a SIGTERM from the operator
or the node, or a SIGUSR1 sent by hand), because a job interrupted at its time
limit has used at least its limit minus three minutes and leaves at most two.

The filler claims every job's slot in the run root exclusively, the first
job's included (slot 0), so a second manifest for a slot is refused whatever
the output directory. Each filled manifest is submitted once. A job is matched
to its claim by its `manifest.json` (name, minutes, image and predecessor). A
lane with a job that has no claim, a job whose elapsed minutes exceed its
claim's minutes, or two jobs on one claim (a filled manifest submitted again)
is void and cannot be read under this id: the filler fills no further job of
it, and the lane is INCOMPLETE. The entry point cannot refuse a manifest whose
claim is missing or already used, because its container sees only its own job
directory, not the lane's run root; the summariser's void rule is the
backstop, applied after the GPU time is spent. The filler and the summariser
run on the host against the lane's run root, whose `fill-claims` directory
holds the claims; an evidence copy keeps that directory. A claim is never
removed, so an image rebuilt after a manifest was filled means a new
experiment id.

The filler, which reads the run root, is the budget authority; the entry point
refuses a registered-profile job outside the batch script, a job whose
`job.env` is missing or names no Slurm job (or another job than
`SLURM_JOB_ID`, when that is set), a continuation manifest without the batch
script's resume receipt for its predecessor or without the predecessor's
pinned development artifact, a fresh job that finds checkpoints, and any
manifest whose GPUs differ from the lane's or whose minutes exceed the lane's
(the lane's minus two for a continuation) or fall below 5.

No budget amendment is possible under this id, whatever either lane read: a
lane without a receipt within its own minutes is INCOMPLETE, and so is the
combined read. More GPU time is a new experiment id, decided by the program
owner in `program/decisions.md`. A CPU doctor run in the image and the
artifact derivation inside each job cost no separate GPU time.

### The development timing jobs (D36 and D42 (ii), before the freeze)

Two jobs, each of at most 0.1 GPU-h (1 GPU x 6 minutes) on the 4B lane's
model, inputs, container profile, CPUs and memory, through the discovery lane
(`scripts/submit_docker_research_job.py`, the batch script, a digest-pinned
image built from the branch by the CPU-only build path), running v2's entry
point with `--profile timing`, each from its own template and in its own run
root, filled with one claim and submitted once
(`experiments/manifests/q3-dense-headroom-precheck-v2/q3-dense-headroom-v2-timing-4b.yaml`,
run root `timing-qwen3.5-4b-base`, D36's job;
`q3-dense-headroom-v2-timing-2-4b.yaml`, run root `timing-2-qwen3.5-4b-base`,
D42's; `--timing 1` and `--timing 2` of the filler). Since the second job the
profile starts with the lane's start-up as the lane runs it, including its one
`attention_backend_check` (cuDNN's attention on, then off, on the lane's first
combined unit), so that the fixed path's start-up runs on the GPU (D42 (ii));
a failing check writes the timing receipt and ends the job as it would end
the lane. The registered subset of development units is the first two
16-unit chunks of every stage, in the lane's own chunking, taken round robin
(A1 B1 C1 D1 A2 B2 C2 D2; 128 units; `harness.dense_headroom_v2.timing_order`). For every unit it
records the wall and process CPU seconds of each component (inputs, prefill
forward, selection, each option's cache copy and forward), synchronising the
device at component boundaries; per chunk, the wall and CPU seconds and the
busiest threads. After the first chunk it profiles one warm unit through v1's
and v2's evaluation with `torch.profiler` and runs v1's evaluation on that
chunk's first two units and on the first unit of every other stage, timed,
under cProfile and compared bit for bit with v2's output. It then evaluates
the lane's other chunks in the same order (the first of each stage under
cProfile) until Slurm's SIGUSR1, three minutes before its limit, which it
answers as a lane does (exit 75 and the marker): the live test of decision 17.
It reads no preregistration, writes `timing-receipt.json` and never a lane
receipt or chunk file, and is not evidence of any statistic.

Result of the first job (2026-10-08; evidence
`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/`). Image
`sha256:3f2cc537...` built by Slurm 763 (CPU only) from a fresh clone of
`71dc954`; the v2 CPU doctor passed in it (12 of 12 cases). The timing job,
Slurm 766, ran 205 s (07:32:07 to 07:35:32 UTC, 0.0569 GPU-h): start-up 19.4 s
to the first unit; the first unit 47.7 s (first-use compiles); A-main chunk 0
in 108 s (median unit 4.08 s), B-absent chunk 0 in 54 s (median 3.62 s),
with the GPU at 0 to 13 percent when sampled after the first unit and one
thread of the workload busy (`busiest_threads`), as in job 730. Per unit, the cache copy took 5 ms and
the selectors with the fp32 recompute 43 ms; each forward with new lengths
took about 0.7 s more than one with lengths seen before (decision 18). The two
v1-path reference units were bit for bit equal to v2's output; the development
artifact equals job 730's. The guard found Triton's LLVM handlers 65.6 s in
(SIGUSR1 and SIGTERM replaced, repaired). Slurm's SIGUSR1 arrived during
B-absent chunk 0 and was answered at the chunk boundary: marker
`trigger=SIGUSR1`, exit 75, termination reason
`signal_USR1_checkpoint_confirmed`, the timing receipt bound to job 766 from
`job.env`. The subset did not complete (2 of its 8 chunks); the remaining
stages were not timed.

Result of the second job (2026-10-08; evidence
`program/evidence/2026-10-08/q3-dense-headroom-precheck-v2-build/timing-2/`).
Image `sha256:15514bd1...` built by Slurm 806 (CPU only) from a fresh clean
clone of `87242fa`, the code head (source tar `b8bee28b...`); the v2 CPU
doctor passed in it (12 of 12 cases). The timing job, Slurm 810, ran 162 s
(10:12:46 to 10:15:28 UTC from `job.env` to `termination.env`, 0.045 GPU-h;
Slurm's run time 164 s) on the fixed path. Its start-up ran as the lane's:
the model was loaded 19.6 s in, the `attention_backend_check` took 47.4 s
with the first-use compiles and left cuDNN's attention off, and the first
unit started 67.0 s in. On the lane's first combined unit (`c320-q0`)
cuDNN's attention and the lane's differed by at most 1.15 points of recall
and 0.011 in an option score; budgets, largest selections, tie counts and the
answer were the same. The registered subset completed (8 chunks, 128 units,
128 s in), then one further chunk of A-main and of B-absent under cProfile.
First evaluations took a median 0.42 s (A-main), 0.39 s (B-absent), 0.16 s
(C-literal) and 0.35 s (D-nohaystack) per unit; units re-evaluated with
every kernel compiled took the same (0.37 s for `c320-q0` after the check;
0.16 to 0.52 s through v1's path under cProfile), so no per-shape cost is
left. Two one-off compiles (7.4 and 7.6 s) are the only slow units. The
same A-main and B-absent chunks that took 108 s and 54 s in Slurm 766 took
6.3 s and 6.0 s. One Python thread still does the work (`busiest_threads`;
CPU seconds equal wall seconds per chunk), with the GPU at 0 to 95 percent,
mean 31 percent, when sampled every 2 s during the evaluation. v1's path on
five units (two of A-main, one of every other stage) was bit for bit equal to
v2's output with the lane's backend; the torch profiles of both show
`aten::_efficient_attention_forward` and no cuDNN attention; the development
artifact equals job 730's. The guard found Triton's LLVM handlers 65.4 s in
(after the check's compiles) and repaired them; Slurm's SIGUSR1 arrived
150.6 s in (about 162 s after Slurm's start, 18 s before the nominal
three-minute lead; in Slurm 766 it came 8 s early) and was answered at the
next chunk boundary: marker
`trigger=SIGUSR1`, exit 75, `signal_USR1_checkpoint_confirmed`, the timing
receipt bound to job 810 from `job.env`. The 4B limit above is set from this
job, at the largest of the estimates computed from it (D44).

## Infrastructure failures and exclusions

A lane is void, with no read, when its job does not end COMPLETED with exit
code 0:0 (except an exit 75 completed by its one continuation), when a
start-up check fails (exit 2), on an integrity failure (exit 3), when
provenance verification fails, or when the orx node lacks its ORX_RESULT line.
A void lane may be re-run under this id only if no lane receipt was produced
by any of its jobs (chunk files no statistic has read do not count) and each
of its jobs ran on its own fill claim, in the lane's registered run root and
within the lane's remaining minutes (Compute).
The combined read (`scripts/summarise_dense_headroom_precheck_v2.py`) applies
these rules to the job that wrote each receipt, from the files beside it,
through v1's own functions (`scripts/summarise_dense_headroom_precheck.py`,
imported unchanged): `termination.env` reason completed with exit code 0;
`provenance-verification.txt` PASS for the job's git SHA and source SHA-256,
which must be the receipt's; the job's `ORX_RESULT ... job=N exit=0` line (N
its Slurm job id) in a saved orx log; the receipt's `slurm_job_id` is its job
directory, bound from `job.env` (`slurm_job_id_source` is `job.env`); every
job in the lane's run root ended and exactly one holding a receipt; a
continuation's predecessor ended with a confirmed signal checkpoint and is
recorded in the receipt; the lane's jobs together ran within its minutes; and
every job of the lane, the first included, ran on its own fill claim and
within the claim's minutes, with no claim carrying two jobs (Compute). It
records each receipt's SHA-256 over the file's bytes. It also applies the
validity gate: a 0.6B receipt that does not reproduce v1's job 727 is read as
INVALID.

## Reported regardless of outcome

- Both lanes' receipts: every statistic above with points, intervals and the
  per-seed null values; per pair, per leg, per layer and per depth tables;
  tie counts; the matched budgets used; the fixed-budget rows; the development
  artifact's digest, counts, context lengths and dropped tail bytes; timings
  per stage and per chunk; the determinism mode; torch and transformers
  versions; the attention backends enabled and, on the 4B lane,
  `attention_backend_check` (decision 18, D42 (i)); the signal guard's record
  (signals received, handler replacements found and repaired); the Slurm job
  and where it was read.
- The entity anchors of every development question.
- The K1 smoke reproduction and the job-727 reproduction (every differing
  leaf, the largest numeric gap), whatever their outcome.
- v1's job-727 receipt and decisions beside v2's.
- The combined read with its requirements, and the GPU-hours used per lane:
  every job in the lane's run root with its elapsed and charged minutes; both
  timing jobs' GPU-hours.

## Freeze procedure

1. The program owner accepts or amends design decisions 16-21 below and the
   limits (a decision in `program/decisions.md`). That decision also rules on
   the two departures from D36 on the 4B lane: it amends D36 (iii) for that
   lane (decision 18: cuDNN's attention off, not bit-equal, checked only by
   the descriptive `attention_backend_check`), and on D36's timing rule
   (decisions 20 and 21) it either accepts a limit that no measurement of the
   fixed path set or authorises a timing job of the fixed path, after which
   this file is revised and reviewed again before step 2. D42 is that
   decision: it amends D36 (iii) for the 4B lane, authorises a timing job of
   the fixed path (Slurm 810, whose measurement set the 4B limit by D36's rule,
   so D36's rule for the limit stands), and accepts decisions 16-21 as amended by it
   after a narrow re-check of the measured limits. D44 closed that re-check:
   it sets the 4B limit at 32 minutes, the largest of the estimates computed
   from Slurm 810's measurement (decision 20), and accepts decisions 16-21 as
   amended by D42 and D44. Before step 2 the status paragraph at the top of
   this file is rewritten to the frozen wording (frozen in the ledger;
   decisions accepted in D42 and D44; D42 amends D36 (iii) for the 4B lane;
   the 4B limit measured by the second timing job and set at the largest
   estimate in D44), and so is the lead-in of the design decisions (decisions
   16-21 accepted in D42 and D44, as amended by them), because a frozen file
   cannot be edited: both name D42 and D44. In frozen mode
   `tests/test_dense_headroom_v2_prereg.py` refuses a file that still holds
   draft wording, or whose status paragraph and lead-in do not both name D42
   and D44, decisions in `program/decisions.md` that name this experiment
   (D42 amends D36 (iii); D44 sets the 4B limit at 32 minutes). The code
   table above is recomputed from the final code;
   `tests/test_dense_headroom_v2_prereg.py` binds it to the working tree.
2. This file is frozen with
   `uv run python scripts/preregister.py freeze q3-dense-headroom-precheck-v2 program/preregistrations/q3-dense-headroom-precheck-v2.md`
   and committed with its ledger row.
3. An image is built from that commit; the CPU doctor
   (`scripts/run_dense_headroom_precheck_v2_doctor.py`) runs in the image
   (network none, no GPU) and its receipt is kept with this experiment's
   evidence.
4. The two lane manifests are filled by
   `scripts/fill_dense_headroom_precheck_v2_manifests.py` and pass the
   submitter's dry run and test-only run; each filled manifest is submitted
   once, by its orx node, and the 0.6B lane is submitted first. The 4B lane is
   filled (`--small-lane-receipt`) and submitted only after the 0.6B lane has a
   completed receipt bound to its Slurm job whose `smoke_452_reproduction`
   status is REPRODUCED and which reproduces v1's job-727 receipt (the validity
   gate); the filler refuses it otherwise. If either reproduction fails, the
   pre-check ends INVALID and the 4B lane does not run; if the 0.6B lane ends
   without a receipt, the 4B lane does not run either and the read is
   INCOMPLETE.
5. The combined read is written by
   `scripts/summarise_dense_headroom_precheck_v2.py` from the lane receipts
   and the saved orx logs of their nodes (`--orx-log`; `--run-root` for a lane
   without a receipt); `program/state.json` and the Q3 question file are
   updated.

## Design decisions

Each states the choice and why. Decisions 1-15 are v1's, accepted in D32
(`program/decisions.md`; 1, 10, 12 and 13 were amended there and are
stated as amended), carried unchanged except decision 12's caps (D36, D44).
Decisions 16-21 are v2's (D36), accepted in D42 and D44 as amended by them,
after a narrow re-check of the measured limits: decision 18's switch departs
from D36 (iii) on the 4B lane, which D42 (i) amends, and decisions 20 and 21
set the 4B limit from the second timing job that D42 (ii) authorised, at the
largest of the estimates computed from it (D44).

1. Two lanes, both run unless the 0.6B smoke reproduction fails or the 0.6B
   lane ends without a receipt (amended in D32). The 4B lane is filled and
   submitted after the 0.6B lane's receipt reports the K1 smoke reproduction
   REPRODUCED (the filler checks it; Freeze procedure, step 4). If the
   reproduction fails, the 4B lane is not submitted and the combined read is
   INVALID (decision 11); if the 0.6B lane ends without a receipt, the 4B lane
   is not submitted and the read is INCOMPLETE. The 4B lane never depends on
   the 0.6B lane's headroom result: D26 names both bases, a NEGATIVE-capable
   v3 may exist on one and not the other, and the combined rule needs both.
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
   development read cannot reach K1's H2 bounds with useful power. This
   relaxes K1 v1's development pre-step (reported beside it, unchanged): a lane
   can be NEGATIVE_CAPABLE or GO_ONLY_CAPABLE while that pre-step reads
   ESCALATE_OR_STOP. The relaxation is not silent: a chosen base whose
   h2_status is POINT_ONLY adds the requirement that the v3 re-test H2 under
   K1's bounds on its audit read. D32 accepts this explicitly.
6. The entity-anchor rule is a deterministic English-side rule (capitalised
   words after the first, digit runs, both shared with the passage). Proper
   nouns cannot be detected by case in six of the eight languages; Belebele's
   translation rules carry the English anchors into every translation. It
   misses lower-case entities and counts capitalised common words after the
   first; both are visible in the per-question anchor list.
7. The literal selector (LEX) measures the lexical-overlap confound in K1's
   own units: its xi_rel on all families against 0.10 (K1's NEGATIVE limit)
   decides lexical_confound. It matches every shared token, so the flag is
   named for lexical overlap and never attributed to entities; an entity-only
   literal selector would need each language's form of the English anchors,
   which the bundle does not give. Stop ids come from the development haystack
   per language, not from a stop-word list, so the rule is the same for every
   script; the needle's and the query's languages are both removed.
8. The block-score null uses noise on natural-log block scores, because a
   KL-distilled indexer's scores approximate the log of its target up to a
   constant; sigma spans 0.25 to 4 on a grid of ratio about 1.4, so that for a
   loss that grows smoothly with sigma some scale lands between half of V1's
   tolerance and V1's tolerance. Only scales whose null passes K1's V1 rule
   decide null_calibration, and one of them must lose at least 2.5 points of
   English ML recall; otherwise only near-exact copies of the target were
   tested, their xi is near 0 by construction, and the verdict is
   NOT_EVALUABLE. The 2-point and 0.10 limits are a fifth of K1's GO threshold
   and K1's NEGATIVE xi_rel limit.
9. On Qwen3.5-4B-Base, deterministic torch kernels are requested with
   warn-only, because the gated-delta layers run Triton kernels outside
   torch's deterministic registry and an op without a deterministic kernel
   would otherwise end the job; the receipt records the mode. Nothing read
   here depends on bitwise reproducibility.
10. The floor candidate (amended in D32) is the gauntlet's example (lower
    bound of G(MN) at least 0.5), defined on entity-controlled families so
    that it measures non-literal adequacy, and judged by whether it separates
    a literal-only selector (point below 0.5) from a V1-adequate noisy copy of
    the target whose 99 percent lower bound is at least 0.5, the bound an
    indexer would be judged by. The noisy copy must meet decision 8's reach
    rule: its seed-mean English ML loss is at least 2.5 points. The near-exact
    copy at sigma 0.25 passes whenever the other two conditions hold, so
    without the reach rule VIABLE would not show that the floor admits a
    realistically imperfect selector. With about 19 development clusters, and
    fewer controlled ones, wide intervals make NOT_VIABLE (a redesigned floor)
    the likely outcome.
11. The K1 smoke reproduction is a validity gate for the 0.6B lane: same
    tokens, same capture path, K1 v2's equivalence-tested batched selection.
    A failure means the new code path does not reproduce K1 v1's measurement;
    the 4B lane runs the same path, so the combined read is INVALID and the 4B
    lane is not submitted.
12. Caps 0.20 and 0.5333 GPU-h (12 and 32 minutes on one GPU; the 4B cap is
    32/60 GPU-h, D44), with the two timing jobs' 0.10 each summing to 0.933
    GPU-h within D36's 1.5
    (caps amended in D36; v1's 0.15 and 0.35 GPU-h summed to D26's 0.5, as
    amended in D32). SIGUSR1
    arrives three minutes before the limit and ends the job at the next chunk
    boundary, so the useful window is the limit minus three minutes: 9 and
    29 minutes, each covering twice the measured evaluation time plus
    start-up (decision 20). Every job of a lane
    (re-runs and its one continuation included) is charged against the lane's
    own minutes from the run root's timestamps, gets at least 5 minutes (2
    useful after the signal's lead) or is refused, and no budget amendment is
    possible under this id. Every job, the first included, takes an exclusive
    filler claim, and each filled manifest is submitted once; a lane with a
    job without a claim, a job that ran longer than its claim's minutes, or
    two jobs on one claim is void. The entry point cannot check claims (its
    container sees only its own job directory), so the summariser's void is
    the backstop. A time-limit interrupt leaves no room for a continuation, so
    a lane that overruns ends INCOMPLETE.
13. Container profiles `default` and `large-cpu-mem` (amended in D32):
    `default` for the 0.6B lane, `large-cpu-mem` (an exec /tmp) for the 4B
    lane, whose Triton kernels compile and load at first use. Only Triton's
    cache moves to the run directory; the entry point sets the cache
    variables with `setdefault`, so TorchInductor's cache stays at the batch
    script's `/tmp/torchinductor`, and nothing here calls `torch.compile`.
14. The CPU doctor runs tiny random Qwen3 and Qwen3.5-style models with
    stand-in byte and pair tokenizers on a synthetic bundle built by the real
    K1 builder; on CPU it blocks flash-linear-attention so the gated-delta
    layers use transformers' torch implementation. Its end-to-end runs use the
    batch environment (`COTCODEC_OUTPUT_DIR` and the job's `manifest.json`),
    so a continuation runs with its predecessor and resume receipt. It proves
    executability and gate semantics only, never anything about the real
    models or data.
15. D26's four requirements of a K1 v3 are always required. No flag here
    removes one: an ABSENT lexical confound comes from one heuristic selector
    and does not show that entity anchors are absent. Changing D26 is the
    program owner's decision.
16. Job binding through `job.env` (D36 (i)). Every receipt records
    `slurm_job_id` read from `job_id` in the job's `job.env`, which
    `infra/slurm/host-single-node/docker-research.sbatch` writes into the
    job's run directory before it creates the container; that directory is
    the container's `/outputs` (`COTCODEC_OUTPUT_DIR`). Under the batch script
    a job without `job.env`, or whose `job.env` names no job or another job
    than a `SLURM_JOB_ID` in its environment, exits 2 before any work, so no
    receipt can carry a null job; the receipt also records where the id came
    from (`slurm_job_id_source`). This is the least invasive repair that is
    correct for every lane: the batch script is not changed, so its digest
    (`2a10c9c7...`, recorded in every `job.env`), the lane runtime tests and
    every frozen registration that ran on it stay as they are, and no other
    entry point's container environment changes. Passing `SLURM_JOB_ID` into
    every container instead would have changed the batch script and the
    container contract of all lanes. Tested end to end: the real batch script,
    run against stub host tools (`tests/test_dense_headroom_v2_job_binding.py`,
    Linux), writes `job.env`; the entry point's receipt-writing code, in the
    environment the batch script passed to `docker create`, binds the receipt
    to job 4242; v1's summariser rule accepts it and refuses v1's null-job
    receipt; the doctor runs the full tiny lanes the same way
    (`end_to_end`, `job_binding`).
17. Signals (D36 (ii)). In job 730 SIGUSR1 never reached the workload:
    flash-linear-attention's Triton kernels compile inside the first forward,
    and LLVM (inside Triton) then installs process-wide signal handlers. It
    replaced CPython's OS-level handler for SIGUSR1 (LLVM's "info" signal,
    which its handler swallows) and SIGTERM, while `signal.getsignal` still
    reported CPython's (shown in the image on 2026-10-08: the OS-level
    handler address changed at `triton.compile` and a self-sent SIGUSR1 never
    reached Python). The container's PID 1 status was not the cause: a
    process-directed signal with an installed handler is delivered to PID 1.
    v2's entry point blocks SIGUSR1 and SIGTERM in its first lines, before any
    import can start a thread, so every thread inherits the block and the
    signals stay pending whatever handler a library installs (a blocked signal
    is never discarded, PID 1 included); `SignalGuard` consumes them with
    `sigpending`/`sigwait` at every unit and chunk boundary, keeps CPython's
    handler installed as a second path, re-installs it whenever the OS-level
    handler has been replaced, and records each replacement. The answer is
    v1's: at the next chunk boundary, `receipt-interrupted.json`, the marker,
    exit 75. Tested with the dependencies of the 4B path: the doctor's
    `usr1_displaced` case and `tests/test_dense_headroom_v2_usr1_pid1.py` run
    the entry point (as a child, and as a container's PID 1 through the batch
    script's exec chain with `docker kill --signal USR1`) under a shim that
    compiles a real Triton kernel inside the first forward; v2 answers, v1
    does not. Both timing jobs tested the live path on the GPU (Compute).
18. Evaluation: v1's on every computed quantity except the 4B lane's attention
    backend, a departure from D36 (iii) that D42 (i) accepts. v2's `harness/dense_headroom_torch_v2.py` runs v1's
    selectors (`select_unit`, imported) and v1's multiple choice with three
    changes that leave every value as it was: the literal blocks are moved to
    the device before the layer loop, a hybrid prompt cache is cloned per
    option (`clone_cache`, the same tensors, strides and attributes) instead of
    deep-copied, and an option's first token is read from its host array.
    Tested bit for bit against v1 on tiny Qwen3 and Qwen3.5-style models for
    every receipt field of a unit (selection-only, multiple-choice-only and
    combined units; `tests/test_dense_headroom_v2_torch.py`, doctor
    `equivalence`), and end to end on both tiny lanes, where every statistic
    and receipt field of v2's entry point equals v1's with tolerance 0 (doctor
    `end_to_end`). None of v1's operator hypotheses was the cost: in the first
    timing job the cache copy took 5 ms per unit and the selectors with the fp32
    recompute 43 ms. The cost was torch 2.11's scaled-dot-product attention on
    Qwen3.5 (head dimension 256), which goes to cuDNN (`torch.profiler`: every
    attention call `aten::_cudnn_attention_forward`) and builds a new cuDNN
    graph for every new query and key length: about 0.7 s of CPU per forward,
    with the GPU idle, and every unit has five new shapes (the prefill and four
    options). In Slurm 766 a unit whose prefill length had been seen before
    took 0.11 s for its prefill against about 0.8 s for new lengths, and the
    units re-evaluated with every graph cached took 0.51 s whole against 3.6 to
    4.1 s cold. So on the hybrid lane the entry point turns cuDNN's attention
    off (`torch.backends.cuda.enable_cudnn_sdp(False)`); PyTorch's flash and
    memory-efficient kernels (its math kernel where neither applies) compute
    the same softmax attention without a per-shape build. This is the one
    change that is not bit-equal: on the 4B lane attention outputs differ from
    cuDNN's at bf16 rounding (another accumulation order), and through near
    ties in top-k selection a recall can move by a block. There is no v1 4B
    number to compare with (job 730 left no receipt), the lane already runs
    warn-only determinism and nothing read there depends on bitwise
    reproducibility (decision 9), so no tolerance is registered and nothing is
    gated on it; the lane's receipt reports, for its first unit with selection
    and multiple choice, the largest difference of every recall and option
    score between cuDNN's attention and the lane's (`attention_backend_check`,
    descriptive). The 0.6B lane is untouched, so the job-727 gate binds it
    exactly; on CPU the equality holds bitwise (no cuDNN there). D36 (iii)
    asks that the bottleneck be removed without changing any computed
    quantity, so on the 4B lane this switch departs from it; D42 (i) amends
    D36 (iii) for that lane only (Freeze procedure, step 1). The job-727 gate (decision 19) and the smoke-452
    reproduction do not cover the switch, because the 0.6B lane never makes
    it. Where the carried text says that the 4B lane runs the same code or
    path as the 0.6B lane (decision 11, and the INVALID rule under Decision
    rules; v1's words, kept verbatim), that holds in v2 for everything except
    this backend: a 0.6B failure still makes the combined read INVALID, but a
    0.6B pass says nothing about the 4B lane's attention. `attention_backend_check`
    is the only check of the switch, and it is descriptive. The fixed path ran
    on the GPU in the second timing job (Slurm 810; decision 21): torch chose
    its memory-efficient kernel (`aten::_efficient_attention_forward`), v1's
    and v2's evaluation were bit for bit equal on five units with it, units
    took 0.16 to 0.43 s on average by stage against 3.6 to 4.1 s with cuDNN's
    attention, and on the lane's first combined unit cuDNN's attention and the
    lane's differed by at most 1.15 points of recall and 0.011 in an option
    score, with the same answer.
19. The validity gate against job 727 (D36), with the fields and the 1e-6
    tolerance stated in its section. Exact equality is expected on the 0.6B
    lane (strict deterministic kernels, same hardware and libraries); the
    tolerance is D36's and is not widened. A failure means the shared code
    path no longer reproduces v1's measurement, so the combined read is
    INVALID, as for a failed smoke reproduction (decision 11). The gate does
    not cover the 4B lane's attention backend (decision 18): the 0.6B lane
    never switches it, and there `attention_backend_check`, which is
    descriptive, is the only check.
20. Limits with D36's arithmetic, both lanes' measured; the 4B lane's at the
    largest of the estimates computed from its measurement (D44). The 0.6B
    lane's minutes come from job 727's measured 278 s (262 s of evaluation and
    statistics, 16 s of start-up), the 4B lane's from the second timing job's
    measurement of the fixed path (Slurm 810, D42 (ii)): per-stage means of
    159 measured units carried to the lane's context lengths, with an
    allowance for one-off compiles and a 5 s statistics bound, and 79 s of
    start-up with the lane's `attention_backend_check` (Compute). Each limit
    is twice the measured evaluation plus start-up plus the 3-minute SIGUSR1
    lead, so a lane that runs at its measured speed ends well inside its
    useful window and the one continuation stays possible after an early
    interruption: 12 and 32 minutes. Three estimates of the 4B lane's
    evaluation and statistics were computed from the measurement: the stage
    means scaled in proportion to length, 769 s (30 minutes); a per-stage line
    in tokens, 789 s (31 minutes); and the larger of the two in every stage,
    824 s (32 minutes). The proportional scaling was chosen after a first
    analysis pass came out over D36's cap; the line fit gives 31 minutes, all
    of the increase from A-main, whose measured units span only 211 tokens,
    while on B-absent, the one stage measured at the lane's long contexts,
    proportional scaling over-predicts (Compute). D44 sets the limit at the
    largest, 32 minutes, so that it is at least twice the measured time plus
    start-up (D36) under each of the three. The 4B lane completes its first
    job if it averages at most about 1.4 s per unit against the 0.16 to 0.43 s
    measured by stage. An earlier draft set 45 minutes from a doubled
    projection of the first timing job's warm-shape units because the fixed
    path had not been timed; D42 (ii) replaced it with this measurement, so
    D36's rule for the 4B limit holds unamended (D42 (ii) adds only the second
    timing job, and D44 chooses among estimates of the same measurement). The
    caps, 0.20 and 32/60 GPU-h, sum with both timing jobs' to 0.933 GPU-h,
    within D36's 1.5.
21. Two development timing jobs before the freeze (D36, D42 (ii)), each in
    its own run root with its own template and claim, with component timings
    and profiles so that they show where the time goes, a bit-for-bit
    comparison of v1's and v2's evaluation on real 4B units, and a live
    SIGUSR1 at the limit. The first (Slurm 766, the image built from
    `71dc954`) ran the 4B path as it was before the fix (cuDNN's attention
    on): it located the per-shape cost (decision 18) and compared two units
    with cuDNN's attention, but did not time the fixed path. D42 (ii)
    authorised the second (Slurm 810, the image built from `87242fa`, the code
    head), which ran the fixed path from the lane's own start-up, its
    `attention_backend_check` included, through the registered subset and two
    more chunks, compared five units with the lane's backend, and answered
    SIGUSR1 at a chunk boundary; its measurement sets the 4B limit (decision
    20). The files changed after each are listed in "Changes from v1" (item
    10); after the second, only the 4B limit and cap and their text. Their
    numbers are not evidence of any statistic.
