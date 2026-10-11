# Draft registration: E3 Stage-0 headroom probe, v2 (`e3-byte-boundary-headroom-v2`)

**Status:** DRAFT. Not frozen, not admitted, no ledger row. Written 2026-10-10
by the E3 gauntlet's single owner (a Claude agent) under D68, as the repair of
gauntlet wave 1 (score 52). It supersedes `e3-byte-boundary-headroom-v1`, which
is left unedited. It may be frozen only after the fresh gauntlet run, a
pre-freeze audit, the prerequisites in section 18 and Kevin's reserved sign-offs.
Any material change after a freeze is a new id with a new output path.

**Experiment id:** `e3-byte-boundary-headroom-v2` (new; no E3 id exists in
`program/preregistrations/ledger.jsonl`).

**Scope:** E3's Stage 0 only. It measures whether the strongest learned
boundaries of released byte-level models already fall at corresponding,
alignment-consistent places in a sentence and its translation, once word
segmentation and boundary rate are taken out. Nothing is trained.

**Code is the specification.** The estimator in section 7 to 11 is
`program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute/repair-run2/e3_estimator_v2.py`
(SHA-256 in the bundle). Simulation S1v2 (`instrument_sim_v2.py` beside it)
imports that file unchanged, so every simulated number below comes from the
decision code. The production harness must reproduce S1v2's planted-system
verdicts before any GPU job (gate I7).

**What changed from v1, in one paragraph.** v1 decided on stage-1 boundaries
of EN-ZH, where the Chinese side covers most of its character gaps; its floor
shifted only that side and collapsed, so its statistic read Chinese density and
English word-end misses. v1's operating characteristics assumed aligner errors
three to six times smaller than the published Chinese-English rates and
independent between aligners, so its kill verdict could not fire. v2 decides at
one common per-sentence budget of at most half of either side's word gaps,
selects the model's strongest word gaps by score, counts disjoint alignment-
consistent split pairs (straight and inverted), corrects against random word
gaps on both sides, builds the target from the links two aligner families agree
on, and handles the remaining aligner attenuation on a registered band or with a
gold-measured factor. Its pinned stack is changed so it can import and run.

## 1. Question and verdicts

On FLORES+ devtest, EN-ZH, with an in-distribution H-Net reading each side: at a
common per-sentence budget k (section 7), do the model's k strongest word gaps on
each side already form alignment-consistent split pairs at, or near, the rate an
oracle on the aligners' consensus target reaches?

Verdicts (section 11): NO_HEADROOM, HEADROOM_MONOLINGUAL, HEADROOM,
INDETERMINATE, INSTRUMENT_INVALID, INCOMPLETE.

Consequences, fixed now:

- **NO_HEADROOM:** E3 as the dossier scopes it stops, and the negative is
  recorded. The released checkpoints are monolingual and Stage 1 would train a
  multilingual model from scratch, so the record states the scope: "independently
  trained learned-boundary predictors already correspond across EN-ZH
  translations at the decision budget". Reopening E3 needs a new proposal with
  evidence specific to multilingual learned-boundary models (for example a
  released multilingual checkpoint measured with this instrument).
- **HEADROOM_MONOLINGUAL:** a monolingual syntactic reference already reaches
  the NO_HEADROOM criterion, so the correspondence is reachable without
  translations. E3's translation-specific delta is not supported; boundary work
  moves to monolingual supervision, outside E3.
- **HEADROOM:** E3 may propose building Stage 1's prerequisites (licensed
  parallel corpus, terminology and tool-schema evaluation set, differentiable
  loss, training code) as a new gauntlet. Nothing else is licensed. The measured
  shortfall and the monolingual reference's share of it are reported as the effect
  prior for Stage 1's power analysis.
- **INDETERMINATE, INSTRUMENT_INVALID, INCOMPLETE:** no verdict; recorded; no
  repair inside this id.

## 2. Data

- **Decision data:** FLORES+ (`openlanguagedata/flores_plus`), revision
  `e707e62e...` (full hash pinned at freeze; modified 2026-10-01),
  CC-BY-SA-4.0, gated with automatic approval. Files
  `dev/{eng_Latn,cmn_Hans,kor_Hang,pol_Latn}.jsonl` (997 each) and
  `devtest/...` (1,012 each), each SHA-256 recorded at fetch. dev for gates
  only; devtest for the decision only, read once by the frozen script.
- **Gold calibration data (optional, reserved sign-off R5):** XL-WA en-zh dev
  (90) and test (210) manually aligned sentence pairs (Wikipedia-derived,
  CC BY-NC-SA 4.0, obtainable on request; an outward action). Used only to
  measure attenuation on the gold path (section 9). If R5 is not granted, the
  band path applies and NO_HEADROOM can fire only when attenuation is small
  (section 9, S1v2 table).
- **Rights and hygiene:** no FLORES+ or XL-WA text, per-sentence boundary,
  alignment or score file enters this public repository; only aggregates,
  revisions and hashes. Logs never contain sentence text. Belebele is not used
  as a substitute for the gated files.
- **Q3 overlap:** FLORES sentences overlap Belebele passages that Q3 never reads
  (366 of 488). Reserved sign-off R1.

## 3. Word segmentation (shared by aligners, selection and line M)

- English: spaCy 3.8 tokenizer of `en_core_web_sm` 3.8.0 (MIT), punctuation split.
- Chinese: the tokenizer of `zh_core_web_sm` 3.8.0 (MIT; spacy-pkuseg
  segmentation, OntoNotes model).
- Korean and Polish (descriptive pairs only): whitespace words with Unicode
  punctuation split.
- The segmentation defines the words the aligners link, the word gaps the
  systems select from, and the parse line M uses, so the target and the
  candidates share one unit. A second Chinese segmentation (jieba, MIT, pinned
  release, default accurate mode) is a registered sensitivity analysis, reported
  without a verdict.
- Pinning: wheel and model-package SHA-256 recorded at freeze.

## 4. Boundary systems

Checkpoints (Hugging Face `cartesia-ai`, licence undeclared, not
publication-eligible; R4), code `goombalab/hnet` at 3673fe12 (MIT):

| Checkpoint | Revision | Role |
|---|---|---|
| `hnet_2stage_XL` | c56e23e0 | English side of EN-ZH (decision); both sides of EN-KO and EN-PL (descriptive) |
| `hnet_2stage_XL_chinese` | 01db28db | Chinese side of EN-ZH (decision) |
| `hnet_1stage_XL` | 68f11d72 | descriptive: English 1-stage scores |

**Scores.** For byte t of at least 1, the stage-1 router gives p1(t), the
probability that a chunk starts at byte t; it belongs to raw byte gap t - 1.
The stage-2 router gives p2 over stage-1 chunks; p2 of chunk j belongs to the
byte gap before chunk j's first byte. The driver reads the encoder outputs and
recomputes p = (1 - cos(W_q h_{t-1}, W_k h_t)) / 2 in fp32 with the routing
module's own weights (the model itself runs in bf16); the native boundary mask
that feeds stage 2 is the module's own argmax output, so stage 2 sees the
model's real chunking. Every raw gap maps to a canonical gap (section 5); a
canonical gap's score is the maximum over the raw gaps that map to it.

1. **Primary system, H-Net hierarchical stage-2 score:** s2(g) = p2(g) if g
   carries a native stage-1 boundary, otherwise p1(g) - 1, so every gap without
   a stage-1 boundary ranks below every gap with one. English side from
   `hnet_2stage_XL`, Chinese side from `hnet_2stage_XL_chinese`.
2. **H-Net stage-1 score** p1(g) (secondary, reported without a verdict).
3. **H-Net native boundary sets** (descriptive): the argmax boundaries at each
   stage, scored by the native-set form of section 13.
4. **Same-model variants** (descriptive): each EN-ZH model on both sides.
5. **Line M reference (section 10):** monolingual dependency parses by the
   same spaCy pipelines; word gap strength is ranked by (minus the depth of the
   lowest common ancestor of the two adjacent words, minus the number of
   dependency arcs that span the gap, punctuation-adjacent first), ties broken by
   the registered seed.
6. **Punctuation-only reference** (descriptive): punctuation-adjacent gaps
   first, others random.
7. **Random word gaps** (gate I2).
8. **Tokenizer references** (descriptive, unrestricted form only): OLMo-2
   (`allenai/OLMo-2-0425-1B`, a1847dff) and Qwen3 (`Qwen/Qwen3-8B-Base`,
   49e3418f) tokenizers, Bolmo-1B's and Bwen-8B's sources. They give hard
   boundaries at every word gap, so the word-gap statistic cannot rank them.

**Rate calibration** is the common per-sentence budget k with top-k selection
(section 7). It equalizes the number of boundaries per sentence exactly, which
the dossier's per-language thresholds did only on average. The native boundary
sets (system 3) keep the uncalibrated comparison.

## 5. Canonicalization

As v1 section 5 (unchanged): canonical gaps lie between consecutive
non-whitespace characters of the NFC string; a boundary adjacent to whitespace
maps to the gap after the last non-whitespace character before it; a boundary
after a character's last byte maps to the gap after that character; a boundary
inside a multi-byte character maps to the gap before that character. A word gap
is the canonical gap between a word's last character and the next word's first
character. S1v2 re-checked this under the v2 estimator: mapping every canonical
score through either byte convention and back leaves the word-gap score vector
identical in 600 of 600 synthetic sentences per seed (seeds 42, 43, 44).

## 6. Aligners and the consensus target

- **Aligner A:** OmniAlign (`WPS-Qingqiu/OmniAlign`, revision eaeeb279,
  Apache-2.0; code `MilkDargon/OmniAlign`, Apache-2.0, commit pinned at freeze):
  an mGTE encoder that induces word alignments from token similarity matrices,
  fine-tuned on human Chinese-English alignments. Published zh-en AER 8.5
  (2608.18474, Table 4). The model card loads custom modelling code (R3).
- **Aligner B:** BinaryAlign (`ubisoft/ubisoft-laforge-binaryalign`, commit
  5acb6e7f, checkpoint `models/zhen`, LFS SHA-256 615c9001...,
  CC BY-NC-ND 4.0): mDeBERTa-v3 binary sequence labelling, one pass per source
  word. Published zh-en AER 4.8 supervised and 9.0 zero-shot from its
  six-pair model (2407.12881, Tables 1-2). The two families differ in encoder,
  extraction (similarity matrix against per-word classifier) and training-set
  size; both were supervised on Tsinghua Chinese-English alignments, a shared
  annotation convention and a source of correlated errors that the error model
  covers (section 9).
- **Inputs and settings:** the word segmentation of section 3; each aligner's
  documented default inference settings at the pinned commit, recorded in the
  run manifest. Settings are not tuned.
- **Consensus links:** the links both aligners produce. A spurious link destroys
  every phrase pair it crosses (S1v2: a single aligner at link AER 0.085 keeps
  S of a perfect selection at about 0.69); a spurious link reaches the consensus
  only when both families make it.
- **Allowed pairs (the target):** English gap t and Chinese gap u are an allowed
  pair when some alignment-consistent phrase pair (every link from its English
  span lands in its Chinese span and back) contains both gaps strictly inside,
  and splitting it at t and u leaves two consistent sub-pairs, in straight order
  or in inverted order. Unlinked words between the two halves' images make a
  range of Chinese gaps, all allowed. The whole sentence is a consistent pair, so
  its straight splits are v1's monotone cuts; S1v2 finds that 52-55% of true
  allowed pairs are nested or inverted, which v1 ignored (a selection on true
  pairs scored against monotone cuts alone reads S 0.37 to 0.40).
- **Per-aligner targets** (allowed pairs from A's or B's links alone) are
  secondaries, reported without a verdict.

## 7. Instrument

All per sentence pair i, then pooled.

- **Budget:** k_i = min(floor(0.5 x min(word gaps EN, word gaps ZH)), nu_A,
  nu_B, nu_C), where nu_X is the maximum number of disjoint allowed pairs of
  target X over all gaps. Neither side selects more than half of its word gaps,
  and every target's oracle can place all k_i pairs, so the ceiling is exactly
  1. Pairs with k_i = 0 are dropped (gate I6).
- **Selection:** on each side, the system's k_i highest-scoring word gaps
  (ties by a seeded random key, seed 42).
- **Hits:** the maximum number of disjoint allowed pairs between the selected
  English gaps and the selected Chinese gaps (bipartite matching).
- **Floor:** expected hits of k_i word gaps drawn uniformly at random on each
  side independently, 64 draws per sentence, seed 42 (43 and 44 repeat it).
- **Statistic:** S_X = (sum hits - sum floor) / (sum k - sum floor) under target
  X. This is chance-corrected agreement scaled by its maximum at fixed marginals,
  the form of Cohen's kappa_M (Cohen 1960). Restricting selection to word gaps
  removes word-end detection (S1v2: a system that knows only where words end
  reads S 0.00); the budget rule removes saturation (S1v2: a binary Chinese side
  at density 0.54 to 0.99 and an English word-end miss rate of 0 to 10% leave S
  unchanged within 0.02; graded scores read 0.38 to 0.41 at every density).

## 8. Instrument gates (FLORES+ dev, before any devtest read)

A failed gate makes the pair INSTRUMENT_INVALID; nothing is tuned to pass.

| Gate | Requirement | S1v2 basis |
|---|---|---|
| I1 alignment sensitivity (cut-count preserving) | each sentence's consensus-oracle selection, scored against a same-shape donor sentence's consensus pairs, gives S at most 0.15 | 0.048 to 0.061 (seeds 42-44), against 1.000 on its own pairs |
| I2 random | random word-gap selections at the same budgets give absolute S at most 0.02 under every target (seeds 42, 43, 44) | at most 0.0101 (consensus target at most 0.0031) |
| I3 convention | word-gap score vectors identical under both byte conventions | 600 of 600 per seed |
| I4 aligner agreement | pooled Dice of the two aligners' allowed pairs at least 0.448 and below 0.85 for the band path (section 9) | 0.46-0.82 inside the band with c at most 0.5; 0.91-1.00 with identical errors |
| I5 budget | share of pairs with k_i at least 1 at least 0.98; pooled 1 - floor/k at least 0.5 | k_i at least 1 in every synthetic pair; 1 - floor/k 0.68 (consensus) to 0.74 (per aligner) |
| I6 completeness | at most 2% of pairs dropped (no links, no allowed pair, segmentation failure); zero in-character boundaries after canonicalization | not simulated |
| I7 estimator reproduction | the harness, on S1v2's planted synthetic systems (seed 42 pool), reproduces S1v2's S values to 1e-9 and its verdicts exactly | S1v2 outputs |

## 9. Attenuation: band path and gold path

Aligner error lowers S multiplicatively (S1v2: S under the consensus target is
about alpha_C x S under the truth, where alpha_C is the S of a selection made
exactly on true allowed pairs; adjacent-gap and random-gap errors behave alike).
Two registered paths; every constant below is in `e3_estimator_v2.py` and was
derived from S1v2 before any data (`band_envelope.py`, `band-registered.json`).

- **Band path (default; no outward action).** The registered error band is each
  aligner's link AER at most 0.15 on FLORES+ (the published supervised zh-en
  rates are 0.048 to 0.090; 0.15 allows for the shift from news to Wikipedia
  text), with any error correlation between the families and any
  spurious:missed split.
  - NO_HEADROOM is judged on S_lo = S_C / ALPHA_MAX with ALPHA_MAX = 0.97, the
    largest consensus alpha in the band (so S_lo never overstates S inside it).
  - HEADROOM is judged on S_hi = S_C / alpha_min(a), where a is the devtest pair
    agreement (pooled Dice of the two aligners' allowed pairs) and alpha_min(a) is
    the smallest band alpha among conditions whose agreement is below the next
    edge: a below 0.55, 0.754; below 0.65, 0.651; below 0.75, 0.576; below 0.85,
    0.521. Along each simulated curve alpha falls and agreement rises with the
    error correlation, so a low agreement rules out strongly shared errors.
  - Valid only while 0.448 is at most a and a is below 0.85 (gate I4). Below,
    the aligners are worse than the band; at or above, errors are presumed shared
    and only the gold path can decide.
- **Gold path (if R5 is granted).** On the 300 XL-WA en-zh pairs, re-segmented by
  section 3 (a word pair is gold-linked when any of their XL-WA tokens are
  linked), both aligners and the consensus target are run, the budget rule is
  applied, and alpha_hat_C is the pooled S of the gold-truth oracle (64 random
  maximum matchings per sentence), post-stratified to FLORES+ devtest over the
  smaller side's word count (bins 0-15, 16-20, 21-25, 26-30, 31-40, over 40).
  S* = S_C / alpha_hat_C, with its 90% interval from a joint bootstrap (devtest
  documents and gold pairs resampled independently, B = 2,000, seed 42).
  - A transfer margin of 0.03 on alpha covers a difference in aligner error
    between XL-WA and FLORES+: NO_HEADROOM is judged on S* x alpha_hat /
    (alpha_hat + 0.03) (point and lower bound), HEADROOM on S* x alpha_hat /
    (alpha_hat - 0.03) (upper bound). S1v2: without the margin, a gold sample
    whose aligner AER is 0.03 worse than the test set's produced false
    NO_HEADROOM calls with probability up to 0.64 at true S 0.84; with it, at most
    0.02.
  - Valid only if alpha_hat_C is at least 0.70 (the correction at most 1.43x)
    and at least 280 gold pairs are usable; otherwise the band path applies.

## 10. Line M (translation-specificity)

The line M reference (system 5) is scored exactly like the primary system, on
the same path. If it meets the NO_HEADROOM criterion, the correspondence at this
budget is reachable from monolingual syntax alone, and a HEADROOM verdict on the
primary becomes HEADROOM_MONOLINGUAL. The reference selects among word gaps at
the treatment's own budget, so it cannot saturate (v1's line M scored at its own
budget and reached 0.99 trivially).

## 11. Decision rule (EN-ZH devtest, consensus target, primary system)

1. Any gate fails: INSTRUMENT_INVALID.
2. Path: gold if R5 is granted and its conditions hold; else band if I4 holds;
   else INSTRUMENT_INVALID.
3. Per system (primary P, reference M), with point estimate and 90% interval
   [L, U] of the path's corrected statistic (band path: S_lo for NO_HEADROOM,
   S_hi for HEADROOM; gold path: S* scaled by alpha_hat / (alpha_hat + 0.03) for
   NO_HEADROOM and by alpha_hat / (alpha_hat - 0.03) for HEADROOM):
   - NH: point at least 0.90 and L at least 0.88;
   - H: U below 0.85;
   - otherwise I.
4. Final: P = NH gives NO_HEADROOM; else M = NH gives HEADROOM_MONOLINGUAL; else
   P = H and M = H gives HEADROOM; else INDETERMINATE.
5. Either GPU job reaching its cap or failing: INCOMPLETE.

**Why these numbers.** The dossier's line is 90% of the correspondence ceiling;
the 0.02 margin on the lower bound and the 0.85 headroom line leave a tolerance
zone of 0.85 to 0.90 in which the rule may return INDETERMINATE. S1v2's operating
characteristics under the registered rule (proposal, Evaluation section;
`oc-summary.md`): with the gold sample at the published error rates, a verdict
for 77-81% of 16 scenario systems, NO_HEADROOM probability 1.00 at true S 1.00
and 0.16-0.23 at 0.91-0.92, HEADROOM 0.99-1.00 at true S 0.75 or less, and no
wrong decisive verdict anywhere inside the band (at most 0.02 with a gold sample
whose aligner error is 0.03 worse); on the band path, no wrong decisive verdict
inside the band, NO_HEADROOM only near true S 1.00, HEADROOM at true S of about
0.45 or less, and refusal when the aligners' errors look shared. Outside the band
(AER 0.20, c 0.5) the band path returned a false HEADROOM with probability 0.09
at true S 0.92, which the band assumption cannot detect without the gold path.

## 12. Statistics

- Pooled ratio estimators from per-sentence counts (hits, floor, k).
- 90% percentile intervals from a cluster bootstrap over FLORES+ source documents
  (the `url` field) if the pinned files carry it, otherwise over sentences
  (disclosed); B = 2,000, seed 42.
- Seeds: [42, 43, 44]; floor draws, tie keys and oracle draws use 42 for the
  decision; 43 and 44 repeat them and the range is reported.
- One primary quantity (S of the primary system on the consensus target);
  everything in section 13 is reported without a verdict.

## 13. Reported regardless of outcome

- S under the consensus target and under each aligner's own target, for every
  system, pair and stage, on dev and devtest; S_lo, S_hi and (gold path) S*.
- The native-set form for H-Net native boundaries: Dice of native sets on word
  gaps, against a floor of random word-gap sets of the same sizes and the
  matching ceiling min(n_a, n_b, nu)/((n_a + n_b)/2), with per-side densities;
  and S_native against S_calibrated.
- The unrestricted form (top-k over all canonical gaps, floor of random
  canonical gaps), which keeps word-end detection in, for every system including
  the tokenizer references.
- A budget profile with rho in {0.25, 0.5, 0.75}; the monotone-only target.
- Aligner statistics: links per word, unlinked share, consensus share, pair
  agreement, nu per target; on the gold path, each aligner's AER, precision and
  recall against XL-WA en-zh and the estimated error correlation.
- The token-alignability form (raw one-to-one share per direction) and the
  legacy UOT cost on 300 devtest pairs, as in v1 (I7 of v1 still governs the UOT
  secondary).

## 14. Compute

**Overlay stack (fixes v1's two breaks).** v1 registered fp32 with TF32 off,
which hnet's attention asserts against (fp16 or bf16 only, `hnet/modules/mha.py`
lines 55 and 123), and the pinned image's transformers 5.15.0, which no longer
exports the `GreedySearchDecoderOnlyOutput` and `SampleDecoderOnlyOutput`
names that mamba_ssm at a6a1dae imports (`mamba_ssm/utils/generation.py` line
14). v2 registers a separate overlay virtual environment on the pinned CUDA
12.8.1 devel base, statically checked on 2026-10-10:

| Package | Pin | Why |
|---|---|---|
| Python | 3.12 (base image system Python) | matches the flash-attn wheel tag cp312 |
| torch | 2.7.1+cu128 | flash-attn 2.8.0.post2 ships wheels for torch 2.4 to 2.7 only; driver 570.148.08 supports CUDA 12.8 |
| flash_attn | 2.8.0.post2, wheel `cu12torch2.7cxx11abi{TRUE,FALSE}-cp312`, the ABI matching torch's `_GLIBCXX_USE_CXX11_ABI` (asserted at build) | hnet's pin |
| mamba_ssm | git a6a1dae (2.2.4), built from source with nvcc 12.8 | hnet's pin, kept exactly |
| causal_conv1d | git e940ead, built from source | hnet's pin |
| triton | as torch 2.7.1 requires (3.3.x; hnet asks for at least 3.2.0) | |
| transformers | 4.57.1 | still exports both names mamba_ssm imports (4 and 8 matches in `generation/__init__.py`; 0 in 5.15.0); OmniAlign's config was written with 4.56.1; BinaryAlign was written for 4.43 |
| hnet | git 3673fe12 | |
| einops, optree, regex, omegaconf, sentencepiece, protobuf | pinned in the overlay lock | |

The build is a host CPU job; its digest is pinned before freeze. The smoke job
proves the stack (section 14 table).

**Precision.** bf16, the checkpoints' native dtype (upstream `generate.py` builds
the model in bf16); router probabilities recomputed in fp32 by the driver
(section 4). Determinism: two smoke runs must agree bit for bit.

**Encoder-only extraction.** Stage-1 scores need the outer encoder and the
stage-1 router; stage-2 scores need the stage-1 chunking, the inner encoder and
the stage-2 router. The driver composes these upstream modules
(`HNet.encoder`, `routing_module`, `chunk_layer`, the inner `HNet`'s encoder and
router) and never runs the main network or decoders. The smoke checks that the
boundary masks equal those of a full upstream forward on its synthetic strings.

**Jobs (one GPU each, network off, `scripts/submit_docker_research_job.py` dry
run, test-only, then submit; never while a Q2 job runs):**

| Job | Cap (GPU-h) | Content |
|---|---:|---|
| smoke | 0.20 | overlay imports; `torch.load(weights_only=True)` of the three checkpoints (fail closed); encoder-only stage-1 and stage-2 extraction of `hnet_2stage_XL` on 64 synthetic byte strings, equal to a full forward's masks; two runs bit-identical; kill and resume; both aligners on 8 synthetic sentence pairs |
| probe | 0.70 | scores of the three checkpoints on dev and devtest in four languages; OmniAlign on the three pairs and BinaryAlign (`zhen`) on EN-ZH, dev and devtest, and on the gold pairs if R5 is granted; per-file SHA-256 |
| **Sum of caps (D22)** | **0.90** | under the 8 GPU-h threshold |

S2v2 (`compute/repair-run2/cost_model_v2.py`): central 0.26 GPU-h, high 0.63
(full forward FLOPs at every byte, as if the split failed, at 20 TFLOPS); the
probe cap is 1.11 times the high estimate. Nothing is measured on the host.

**CPU (0 GPU-h):** segmentation and parsing with spaCy, scoring, gates and
bootstrap on the Mac (minutes).

## 15. Outputs

- Private run directory and private archive: per-checkpoint score files, aligner
  link files, the FLORES+ and XL-WA files, receipts.
- Public repository: analysis code and tests, frozen script digests, aggregate
  result JSON (no per-sentence rows), the verdict, every hash.

## 16. Deviations

Any change to a number, rule, system, aligner, segmenter, revision or script
after freeze is a new id. A bug found after freeze is fixed only under a new id,
with the original output kept.

## 17. Reserved sign-offs (Kevin)

- **R1:** E3 may read FLORES+ sentences that overlap Q3's sealed Belebele
  passages, programmatically and without logging text.
- **R2:** accept the FLORES+ gate and provide a read token on the host.
- **R3:** the pinned upstream code is a trusted input under D7 and D29: hnet,
  mamba-ssm, causal-conv1d, flash-attn, OmniAlign's model-card modelling code
  (`modeling.py`, `configuration.py` at revision eaeeb279) and BinaryAlign's
  repository code (human-written library code, not code produced during an
  experiment).
- **R4:** H-Net weights with an undeclared licence may be fetched and used for an
  aggregate-only measurement, recorded as not publication-eligible.
- **R5 (optional):** request XL-WA's en-zh gold sets (an outward action;
  CC BY-NC-SA 4.0). It enables the gold path; without it the band path applies.
- **R6:** BinaryAlign's checkpoint and code are CC BY-NC-ND 4.0: non-commercial
  research inference only, no redistribution of the model, aggregates only.

## 18. Prerequisites before freeze

1. The estimator (`e3_estimator_v2.py`), canonicalization, word-gap mapping and
   byte mappings in `harness/` with unit tests (the brute-force cross-check of
   allowed pairs included), run as an orx `cpu-doctor` node that passes I7.
2. The overlay built on the host (CPU job), its digest pinned, and the smoke run
   passing (as an orx `slurm-manifest` node).
3. Aligner, segmenter and tokenizer revisions pinned, licences re-checked.
4. The three checkpoints fetched with receipts and `models/registry.yaml`
   entries.
5. Manifests for the smoke and probe jobs, dry run and test-only passed.
6. A pre-freeze audit by a fresh reviewer.
7. R1 to R4 and R6 signed off; R5 decided (granted or declined).
