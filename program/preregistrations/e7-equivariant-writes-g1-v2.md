# E7 G1 floor gate v2: state-carried monolingual and cross-script recall beyond attention's reach in a from-scratch 134M Gated DeltaNet plus SWA-512 hybrid, the precondition for the equivariance study (e7-equivariant-writes-g1-v2)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single owner of the D68 repair on branch `gauntlet/e7-d22`. It
supersedes `e7-equivariant-writes-g1-v1` (wave 1's draft, left unedited as the
record of what wave 1 reviewed). It registers only E7's G1 floor gate: the A0
hybrid (no equivariance loss) trained from scratch, read at 200M and 1B tokens.
The phase-1 grid (A1 write equivariance, A2 projection alignment, A3 placebo,
A5 no-bitext, a 2610.06750-style baseline) is not registered here; it needs its
own design, its own gauntlet and, being over 8 GPU-h, Kevin's admission under
D24. The frozen Qwen3.5-4B split-prefill confirmation belongs to P-GSM. The
design decisions at the end (1 to 36) need the program owner's acceptance. The
caps sum to 7.767 GPU-h under D22's counting rule (S2v2). No host job of any
kind runs while a Q2 job is running or pending. The proposal that argues and
attacks this design is `program/proposals/2026-10-10-e7-equivariant-writes-g1.md`
(its "Changes after wave 1" section maps every wave-1 defect to a clause here);
its evidence bundle is `program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/`,
with the repair's CPU checks under `compute/repair-d68/`.

## What changed from v1, in one list

1. CUT is replaced by REACH, a path-complete check. v1's cut reset the
   recurrent and convolution states once after the facts block and left SWA
   untouched; SWA layers 3 and 7 then relay the facts into fresh post-cut
   states, so a model that carries facts could fail it (wave 1's largest
   defect). REACH replaces the GDN recurrence by its zero-state form at every
   position after the facts block. By an exact symbolic reachability count and
   by complex step on a NumPy reference of this module graph (S3v2, 504 rows,
   all agreeing), no path is then left from the facts block to an answer
   1,561 or more positions away, and REACH is checked on every trained
   checkpoint as a deterministic logit-invariance test, not a statistical one.
2. ABLATION is replaced by two interventions. ISO isolates the queried fact (no
   write, no erase, no input-dependent decay on its span in any GDN layer, no
   conv spill out of it, no attention into it). It is a deterministic check
   with an exact-zero guarantee. D1, the fact-span write ablation (ISO without
   the attention mask), erases every write made on the fact's own tokens and is
   a descriptive pathway read. S3v2 found that beta = 0 alone leaves a path
   through the input-dependent decay gate, so alpha is fixed too.
3. The verdict order is changed so that only deterministic harness checks
   precede PASS, and in-window recall can turn only a failing MONO into
   INSTRUMENT_INVALID, and only when it is under one half (the I1F floor,
   0.50); the 0.80 I1 line is reported, not decision-bearing.
   A state-carrying model cannot be labelled INSTRUMENT_INVALID or
   HARNESS_INVALID by any check in this file.
4. CROSS is identified against surface form. The surface filter regains the
   legacy letter-4-gram clause; distractor keys are the target's neighbours in
   a punctuation-and-length order (sliding block, random offset); every
   cross-lingual query is paired with a surface-twin decoy; a new line SEM
   (binding margin with the real query minus that with the decoy) must have a
   lower bound of at least 0.03;
   a builder gate B-SURF checks the realized manifest before any model exists.
   On NTREX-128 (P1), the learned surface oracle that picks the target 66% of
   the time under v1's design picks it 19% under v2's, and decoys reproduce it
   (20%).
5. CROSS, BIND and SEM are computed on the four cross-script cells only (En-Zh and
   En-Th, both directions). Under the 4-gram clause only 97 test-half En-De sentences are
   eligible, so the En-De cells fall below the 150 floor (P1: 32 and 51
   prompts) and are dropped before any model exists.
6. The FAIL_CROSS sub-label compares attention-only and state-only
   cross-lingual matching at the same distance (B1 under the span cut and under
   the relay block), instead of B1 against B3, which confounded pathway with
   distance. A "surface" sub-label is added.
7. Half of the bitext (10% of tokens) is presented as co-present translation
   pairs in one sequence; the other half keeps the prefix-sharing presentation
   the later write loss needs. Under v1 no translation pair was ever in one
   context, which made FAIL_CROSS "representational" close to a design
   consequence (wave-1 reviewer 1).
8. The probe's three repeats are priced (100 steps per configuration per
   repeat), the v2 diagnostics are priced, and resubmissions are bounded so
   that the D22 sum stays at or under 8.0 GPU-h with the arithmetic shown.
9. S1v2 re-runs every simulation the decision rules rest on under the
   registered estimator (sentence-cluster percentile bootstrap, B = 2,000), on
   the measured pool (699 test-half key sentences; cross-script cells 474, 366,
   314, 235), with a surface-only null, a decoy-quality sensitivity family and
   the v1 failure modes.

## Relation to the dossier and to D67 and D68

- Source: dossier entry `E7-d22-translation-equivariant-writes`
  (`program/evidence/2026-10-06/question-dossier.md`, section 16). "D22" in the
  dossier key is direction 22, not decision D22 of `program/decisions.md`;
  decision D22's counting rule (caps summed, never expected use) applies here.
- D67 restarted E7; wave 1 scored 51 (D68). D68 ordered one repair by a single
  owner and a fresh run; the run ends at an honest exit if it scores below 60 or
  if wave 1's largest defect (the CUT premise) is still the largest.
- Kept from the dossier: the A0 hybrid without the equivariance loss; SWA-512
  replacing full attention in the measured 134M configuration; reads at 200M
  and 1B tokens; the 75 / 20 / 5 mixture of monolingual text, bitext and a
  recall curriculum; TP-MQAR-v2 exact match at N = 8 on facts the attention
  cannot reach; the lines "monolingual at least 60%, cross-lingual at least 15%
  at 1B tokens" (the cross-lingual line now read on cross-script pairs); the
  consequence of a failure (port the comparison to the 2610.06750 LoRA setting
  rather than scale the toy model); the step-overhead probe that prices the
  later grid.
- The changes v1 already made (state-necessary bin, three seeds and LOTTERY,
  4,096 context, the 1/8 copy floor and BIND, matched test languages, the
  within-model decomposition, the LR sweep, the WSD trunk, futility, NTREX-128)
  are kept unless the list above says otherwise.

## Question

For a 134M hybrid of nine Gated DeltaNet layers and three SWA-512 layers
(layout of the measured configuration), trained from scratch for 1B tokens on
En, De, Zh and Th text with 20% bitext (half prefix-sharing, half co-present)
and a 5% same-language recall curriculum, and with no equivariance loss: when
the whole block of N = 8 facts ends at least 1,600 positions before the answer
position (beyond the 1,560-position reach of every path that avoids the
recurrent state), does the model reach

- exact match of at least 60% when the query repeats the key in its own language
  (MONO), and
- exact match of at least 15% when the query is a translation of the key into a
  language with another script that shares no word, letter 4-gram or digit with
  any of the eight keys (CROSS, on En->Zh, Zh->En, En->Th, Th->En), with recall
  bound to the queried key (BIND > 0) and not explained by surface form (SEM at
  least 0.03: the binding margin with the real translation exceeds the binding
  margin with a surface-twin decoy query by at least 3 points),

in at least two of three seeds and in no seed below a line?

Claim scope: an admission-gate benchmark outcome on one from-scratch
architecture at one scale (evidence level "benchmark", status "admission pass"
in `docs/evidence-model.md`). It is not architecture-causal (no matched
control; rule 8) and claims nothing about any equivariance loss. It is the
precondition for the equivariance study and makes no novelty claim: its MONO
line and its pathway reads replicate, in this configuration, measurements
published for other configurations (2610.06750's recurrent-only and
attention-only conditions, SWAX 2509.24552's window and receptive-field
analysis, Griffin 2402.19427's beyond-window retrieval, 2609.33093's fact-time
write blocking). PASS licenses only a gauntlet for E7's phase-1 grid.

## Identity

- Experiment id: `e7-equivariant-writes-g1-v2` (supersedes
  `e7-equivariant-writes-g1-v1`, never frozen).
- Proposal: `program/proposals/2026-10-10-e7-equivariant-writes-g1.md`.
- Code revision: the commit that adds the harness, fixed at freeze; the image is
  built from it by the project's CPU build job and pinned by digest before J1.
- Image lineage (the measured throughput):
  `127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`
  (`cotcodec-research:0b3ecef0-architecture`; torch 2.11.0+cu128,
  flash-linear-attention 0.5.2, triton 3.6.0, tilelang 0.1.13; the tilelang path
  works around fla #640).
- Seeds: 42, 43, 44 (initialization, data order, curriculum instances). The
  prompt set, the builder draws and the bootstrap use seed 42 and are shared by
  all seeds.

## Prerequisites before freeze (no GPU)

1. Harness, reviewed project code under D7, each part unit-tested on CPU:
   - the A0 model (fla `GatedDeltaNet` layers; SWA-512 through torch
     `flex_attention` with a sliding-window block mask), plus a pure-torch
     reference recurrence for CPU tests;
   - the four eval-time interventions as named code paths (Interventions,
     below): SPAN_CUT, RELAY_BLOCK, D1 and ISO;
   - the training loop (fp32 master weights with bf16 autocast, AdamW,
     warmup-stable-decay, packed rows with document-boundary resets, atomic
     checkpoints every 15 minutes, a SIGUSR1 checkpoint, a fresh-job resume);
   - the tokenizer trainer and the mixture, bitext and curriculum builders;
   - the TP-MQAR-v2-G1 builder v2 (surface filter, sliding-block distractors,
     surface-twin decoys, B-SURF, manifest assertions, sealed manifests);
   - the evaluator (teacher-forced digits for the target and seven distractor
     codes with prefix caching; decoy queries from the cached prefix);
   - the diagnostics and the analysis (bootstrap, classification, verdict).
2. A `kind: cpu-doctor` orx node that runs:
   a. the intervention table of S3v2 (`compute/repair-d68/reach-cut-v2.py`) on a
      small random instance of the harness's own module graph (pure-torch
      reference path, float64, complex step or autograd): for every mode and
      distance in S3v2, the exact-zero pattern must equal the symbolic
      reachability `reachable(mode, set, d)` of S3v2. In particular SPAN_CUT
      gives exactly zero from the facts block at d >= 1,561 and nonzero at
      d <= 1,560; ISO gives exactly zero from the queried fact at every
      distance; v1's single cut gives nonzero (the documented wave-1 failure);
   b. the analysis pipeline on synthetic predictions with known rates, which
      must recover them within the S1v2 half-widths and reproduce the S1v2
      verdicts for the planted world scenarios;
   c. the builder checks: B-SURF and the manifest assertions on the sealed
      manifest.
3. Data fetched with receipts under D1 (source, revision, size, SHA-256):
   FineWeb (rev 9bb295dd), FineWeb-2 deu_Latn, cmn_Hani and tha_Thai (rev
   af9c1333), ParaDocs en-de and en-th (rev f80095af), the ParaCrawl Bonus en-zh
   release, SCB-MT-EN-TH-2020 (rev 613aad4a) and NTREX-128 (commit 468c6b69).
   A host action; it waits until no Q2 job is running or pending.
4. Deduplication report: every instrument sentence (all four languages, both
   NTREX halves, since decoys come from both) against every training stream and
   the curriculum key pool, by exact match and MinHash on character 5-grams at
   Jaccard at least 0.5; matches are removed from training, never from the
   instrument; counts reported.
5. The sealed prompt manifests (B1, B2, B3, decoys, check pairs, diagnostics)
   with SHA-256, committed as ids, offsets and hashes without text, with the
   B-SURF record.
6. Slurm manifests for J1, J2, J3, T42, T43 and T44; `--dry-run` and
   `--test-only` pass for each.
7. A fresh pre-freeze audit of this file against the harness.

## Model (A0)

- 12 blocks, hidden 768, pre-norm RMSNorm, tied embeddings, vocabulary 32,000.
  Blocks 3, 7 and 11 (zero-indexed) are attention; the other nine are GDN (the
  layout of `scripts/fla_throughput_doctor.py`, `i % 4 == 3`).
- GDN: fla 0.5.2 `GatedDeltaNet(hidden_size=768, num_heads=12, head_dim=64,
  expand_v=1, mode="chunk", use_gate=True, use_short_conv=True, conv_size=4,
  allow_neg_eigval=False)` with fla's default initialization (A ~ U(0, 16), dt
  log-uniform on [0.001, 0.1]).
- Attention: causal sliding window W = 512 (position i attends to i - 511 to
  i); 12 heads of 64; projections without bias; RoPE (theta 10,000); no sinks,
  no global tokens.
- MLP after every mixer as in the measured module (768 to 4,096, SiLU, 4,096 to
  768, no bias). Parameters 133.96M.
- Reach without the recurrent state: 3 x 511 + 9 x 3 = 1,560 positions from the
  facts block's last token (S3v2: exact symbolic count and complex step agree;
  1,557 from any earlier token, whose information reaches the block's end
  through a state no earlier than layer 0's output).

## Tokenizer

Hugging Face `tokenizers` Unigram, 32,000 entries including `[bos]`, `[eos]`,
`[pad]` and `[kv]`; NFKC; byte fallback; digits split into single tokens.
Trained on 100M characters per language from the training pools, never on
instrument text. Tokens per sentence on the development half are reported per
language.

## Training data and schedule

- Pool, per seed one pass over the same pool in a seed-specific order: 1.04B
  tokens.
  - Monolingual, 75%: En 30% (FineWeb), De 15%, Zh 15% and Th 15% (FineWeb-2).
  - Bitext, 20%: En-De, En-Zh and En-Th, 6.67% each (ParaDocs en-de; ParaCrawl
    Bonus en-zh; SCB-MT-EN-TH-2020 plus ParaDocs en-th). For each pair:
    - half (10% of tokens overall) prefix-sharing, as in v1: a record is two
      sequences c + a and c + b packed as separate documents, (a, b) an
      aligned segment of one to three sentences, c 64 to 256 tokens of
      held-out monolingual text in a language drawn uniformly from the pair's
      two, bitwise identical in both sequences. This is the presentation the
      later write loss needs;
    - half (10%) co-present: one document holding a, a newline and b, with the
      order (a first or b first) drawn uniformly per record. Translation pairs
      are then in one context, as in coherent code-switching curricula
      (2609.30535).
  - Recall curriculum, 5%: as v1 (N_c uniform on {4, 8, 16}; keys of 8 to 60
    tokens with no digits; one language per record; four queries; first-query
    distance 25% U[16, 511], 25% U[512, 1,560], 50% U[1,600, 3,900]; codes from
    the 8,000 outside the reserved set; no cross-lingual query, ever).
- Packing: rows of 4,096 tokens, document-boundary resets.
- Optimizer, schedule, LR grid, LR selection, J3 extension: as v1 (AdamW 0.9 /
  0.95 / 1e-8, weight decay 0.1 on matrices, clipping 1.0, fp32 master weights
  with bf16 autocast, batch 8 x 4,096; warmup 500 steps, constant, (1 - sqrt)
  decay over the last 20%; trunk stable to 800M, decay to 1B; the 200M read from
  a branch at 160M decayed over 40M; LR in {6e-4, 1.2e-3, 2.4e-3} on held-out LM
  loss, seed 42, 50M tokens; one conditional edge extension; the instrument is
  never read during selection).

## Instrument (TP-MQAR-v2-G1, builder v2)

- Source: NTREX-128 (commit 468c6b69; deu, zho-CN, tha and the English source;
  CC BY-SA 4.0). Test half: the documents with int(sha256("42:" + doc_id), 16)
  mod 2 == 0 (63 of 123 documents). The other half is the development half
  (diagnostics, and fitting the B-SURF oracle). If the program owner accepts
  FLORES+ before freeze, FLORES+ dev is the development half and devtest the
  test half, every other rule unchanged (design decision 9).
- Key eligibility: digit-free in all four languages, 8 to 60 tokens in every
  language. Under P1's CPU proxy (6 to 40 English words) 1,360 sentences are
  eligible, 699 in the test half.
- Cells:
  - MONO: En, De, Zh, Th (the query repeats the key exactly);
  - CROSS (decision-bearing): En->Zh, Zh->En, En->Th, Th->En (facts in the first
    language, query in the second);
  - En->De and De->En are built and reported if they reach 150 prompts, and
    never enter a line (P1: 32 and 51 under the 4-gram clause, so they are
    expected to be dropped).
- Surface filter (cross cells, real and decoy queries): the query shares with
  none of the eight keys an NFKC-casefolded whitespace token (raw or with
  leading and trailing punctuation stripped), a letter 4-gram inside any word
  (Unicode letters, casefolded), a 32K-tokenizer token of at least four
  characters, or a digit string.
- Distractor keys (sliding surface block): the fact-language keys of the test
  half are put in one order by (the exact count vector of the punctuation
  classes ", ?, !, :, ;, ( and ",", then length in 32K tokens, then row id). A
  prompt's eight keys are the block of eight consecutive keys that contains the
  target at an offset drawn uniformly from 0 to 7 (clipped at the ends). A
  distractor that fails the filter is replaced by the nearest unused key beyond
  either end of the block, alternating, at most 20 steps; otherwise the target
  is not used in that cell. The target's rank in its block is uniform, so no
  statistic of the keys alone singles it out.
- Decoy query (each cross prompt): a sentence in the query language from the
  whole eligible NTREX pool (both halves) that is not the row of any of the
  eight keys (so it translates none of them), passes the filter against all
  eight keys, has the real query's punctuation count vector and named-entity
  shape count (capitalised words after the first in Latin script; runs of Latin
  letters inside Chinese or Thai) and a length within 5% of the real query's;
  the nearest in length, ties at random. A prompt with no twin is not used in
  that cell.
- Prompt: `[bos]`, the facts block (eight facts `key [kv] dddd` separated by
  newlines), filler, then the query `key [kv]`, after which the four digits
  are scored. A decoy prompt is the same facts block and filler with the decoy
  sentence as the query, scored from the same cached prefix.
  - Codes are distinct within a prompt, from a reserved set of 2,000 never used
    in training.
  - Filler: held-out monolingual text in the fact language, never in training,
    never from the instrument, digits removed, deduplicated.
  - The target's slot is balanced over the eight positions.
- Distance: d is measured from the last token of a fact record to the position
  that predicts the first code digit; d_f is d for the facts block's last token.
  - B1 (direct): every fact at d <= 480.
  - B2 (relay): every fact at 560 <= d <= 1,520.
  - B3 (state-necessary, the gate): d_f >= 1,600, the queried fact at d <= 3,500,
    total length <= 4,096; the gap uniform within these limits.
- Sizes: B3 MONO 4 x 500. B3 CROSS: every eligible queried sentence up to 500 per
  cell (P1, CPU proxy: 474, 366, 314 and 235). B1 and B2: 250 per MONO and CROSS
  cell (fewer if a cross cell has fewer). Each queried sentence is used once per
  cell and bin. A cell under 150 is dropped from every line, decided at build
  time before any model exists.
- Builder gate B-SURF, on the sealed manifest before any model exists (P1 values
  under the CPU proxy in brackets):
  1. the query-free central-key oracle (the key whose length is nearest the
     median of the eight) picks the target in at most 0.155 of prompts, pooled
     over the four cross cells [0.123];
  2. a conditional-logit surface oracle over ten features (log length ratio and
     its square, seven punctuation count differences, the named-entity shape
     difference), fitted on development-half prompts built the same way, picks
     the target with the real query in at most 0.25 of test prompts, pooled
     [0.19];
  3. the same oracle's pooled top-1 with decoy queries is within 0.03 of its
     top-1 with real queries [0.198 against 0.190], and within 0.06 in every
     cell [largest gap 0.030].
  If B-SURF fails, the builder redraws the block offsets and decoy ties with seed
  43, then 44; if all three fail, the registration stops (a new id).
- Manifest assertions: each target code string occurs only in its queried fact;
  no digit occurs outside codes; the filter holds for every real and decoy
  query; no decoy is the row of any key; the eight keys are distinct; slots are
  balanced.
- Sealing: manifests hashed and committed before J1. Every read of a sealed
  manifest is logged with checkpoint, job and time; a read not in "Reads" is a
  leak and is reported.

## Interventions (evaluation only)

Let c be the first position after the facts block and F the queried fact's span
(its key tokens, `[kv]`, its four digits and its newline).

- SPAN_CUT: in every GDN layer, at every position t >= c, the recurrence uses a
  zero previous state, o_t = beta_t (k_t . q_t) v_t (the zero-state form), with
  the output gate as usual. SWA and the convolutions are unchanged.
- RELAY_BLOCK: SWA queries at t >= c cannot attend to keys at positions < c (the
  recurrent-only condition of 2610.06750 Sec. 4.1, at the facts/filler
  boundary). States and convolutions are unchanged, so information crosses the
  boundary only through the recurrent state (and three tokens of convolution).
- D1 (fact-span write ablation): on F, in every GDN layer, beta = 0 and alpha = 1,
  so the state passes F unchanged (no write, no erase, no input-dependent decay);
  convolution inputs from F are dropped for every output position outside F.
  Only attention can carry the fact out of F.
- ISO (isolation): D1 plus no SWA query outside F attends to a key inside F.

What each removes (S3v2, `reach-cut-v2.py`, where the complex step agrees with the
symbolic reachability on all 504 rows): SPAN_CUT leaves no path from the facts
block to an answer at d_f >= 1,561 (and none from F at d_f >= 1,558); ISO leaves
no path from F at any distance; D1 leaves attention relay out of F (the derivative
keeps 6% to 94% of its uncut size in the random reference); RELAY_BLOCK leaves the
state. v1's single reset, v1's v = 0 ablation, a reset over only part of the
post-facts span, and beta = 0 without alpha = 1 all leave paths.

## Reads (every read of the sealed manifests)

- Primary, at the 200M branch and at 1B: B1, B2 and B3, target and seven
  distractor codes; the decoy query of every cross prompt.
- Noise, at 960M and 980M: B3, target only.
- Emergence, at 100M, 400M and 800M (before decay): B3 and B1, target only.
- Checks, at 1B for every trunk (also on T42 when futility stops):
  - REACH: 64 B3 prompts (16 per cross cell), each run twice under SPAN_CUT,
    the second time with every token of the facts block replaced by a token
    drawn uniformly from the vocabulary (seed 42; same length, so every later
    position is unchanged); the answer-position logits of the two runs are
    compared. The same 64 pairs are also run uncut (reported).
  - ISO: 64 B3 prompts, each run twice under ISO, the second time with only the
    queried fact's code changed; answer-position logits compared.
- Pathway reads, at 1B: RELAY_BLOCK on B3 and B1; D1 on B3; SPAN_CUT on B2 and
  B1. All prompts of the named bins.
- Nothing else reads the sealed manifests.

## Metrics

Per prompt: EM_t (greedy equals the target, read by teacher forcing); EM_j for
each distractor code; per-digit accuracy; the target's summed log-probability;
forced choice among the eight codes (chance 1/8); the copy flag; for each cross
prompt, the same for its decoy query.

Per seed and checkpoint, equal weights over cells:
- MONO = mean over the four MONO cells of B3 EM_t.
- CROSS = mean over the four cross cells of B3 EM_t.
- BIND = mean over the cross cells of B3 (EM_t minus the mean over j of EM_j),
  the binding margin. It is zero in expectation for any answer strategy that
  ignores the query, because the target slot is balanced.
- SEM = mean over the cross cells of B3 (binding margin with the real query minus
  binding margin with its decoy), paired by prompt. It is zero in expectation
  for any strategy that uses only what the decoy matches: the key set and the
  query's punctuation, length and name pattern.
- DEC = mean over the cross cells of the decoy's binding margin (for the surface
  sub-label).
- I1 = mean over the four MONO cells of B1 EM_t (the positive control; read
  against 0.80 for the report and against the in-window floor I1F = 0.50 for
  INSTRUMENT_INVALID).
- Descriptive pathway reads: X1 (B1 cross EM_t), X1_attn (B1 cross under
  SPAN_CUT), X1_state (B1 cross under RELAY_BLOCK), I1_attn and I1_state (the
  same for MONO), R3 (B3 under RELAY_BLOCK, MONO and CROSS), A3 (B3 binding
  margin under D1 over the unablated margin, MONO and CROSS separately), B2_attn
  (B2 under SPAN_CUT: what attention and the convolutions alone carry over the
  relay range).

Intervals: 90% percentile bootstrap clustered by key sentence. A resample draws
sentence ids with replacement, and every prompt that queries a drawn sentence,
in any cell, moves with it (with its decoy). B = 2,000, seed 42.

## Structural checks (deterministic, not statistical)

- REACH passes when the largest absolute difference between the two runs'
  answer-position logits, over the 64 pairs and the vocabulary, is at most
  1e-5 in the fp32 evaluation path (exactly 0 is expected).
- ISO passes under the same rule.
- B-SURF and the manifest assertions pass at build time.
- A failure of any is HARNESS_INVALID. These checks test the harness, not the
  model: S3v2 and the cpu-doctor node show that a correct implementation passes
  them for any weights, so no model behaviour can trigger HARNESS_INVALID.
- Why REACH is enough to attribute B3 recall to the state: with REACH passing on
  the trained weights, the harness's SWA window, convolutions and cut are as
  registered, and the reach bound then leaves the recurrent state as the only
  carrier of any information from the facts block to a B3 answer.

## Lines and decision rules

At the 1B checkpoint, separately for each seed, each line is classified ABOVE
when the interval's lower bound is at least the threshold (greater than 0 for
BIND and DEC), BELOW when the upper bound is under it, and UNRESOLVED
otherwise. Thresholds: MONO 0.60 (dossier), CROSS 0.15 (dossier, cross-script),
BIND 0, SEM 0.03, DEC 0; I1 0.80 (reported) and I1F 0.50 (the same I1 estimate
against the in-window floor). A line passes when at least two of the three seeds
are ABOVE and none is BELOW.

Why SEM's threshold is 0.03 and not 0: the decoy reproduces a surface-only
model's binding margin only as well as it matches the surface features that
model uses. P1 measures the surface excess the v2 builder leaves at about 0.065
(the learned oracle's 0.19 against the 1/8 floor), so a surface-only model's
binding margin is about 0.074, and with a decoy that reproduces a share phi of
it, SEM is about (1 - phi) x 0.074. B-SURF's pooled tolerance of 0.03 bounds phi
from below at about 1 - 0.03 / 0.065 = 0.54. S1v2 evaluates both thresholds on
the same replicates: with a threshold of 0 a surface-only model would pass in
0.147 of replicates at phi = 0.8 and 0.600 at phi = 0.6; with 0.03 it passes
in 0.000 and 0.012 (0.052 at phi = 0.5). A semantic model at the CROSS line has SEM about 0.09, so the threshold
costs no detectable power there (S1v2: P(PASS) at a true CROSS of 0.16 is 0.272 with the 0.03 threshold against 0.272 with 0, and at 0.18 0.657 against 0.657, at seed SD 0.03).

Verdict, the first that applies:

0. HARNESS_INVALID: a structural check fails. A code fix under a new id.
1. PASS: MONO, CROSS, BIND and SEM all pass.
2. LOTTERY: MONO or CROSS has at least one seed ABOVE and at least one BELOW.
3. FAIL_CROSS: MONO passes, and either
   a. CROSS is BELOW in at least two seeds or BIND is BELOW in at least two
      seeds (sub-label from the B1 pathway reads, below); or
   b. CROSS and BIND are ABOVE in at least two seeds, SEM does not pass, and DEC
      is ABOVE in at least two seeds (sub-label "surface").
4. INSTRUMENT_INVALID: I1F BELOW (in-window recall under 0.50) in at least two
   seeds and MONO BELOW in at least two seeds. The model cannot recall even half
   of the facts inside its own window, so its B3 failure says nothing about the
   state. Above the floor, a B3 failure is informative even if I1 misses 0.80,
   and it reads FAIL_MONO with I1 reported.
5. FAIL_MONO: MONO BELOW in at least two seeds (sub-label from I1_state).
6. INCONCLUSIVE: anything else.

Futility: after T42's 1B read, if seed 42's MONO upper bound is under 0.30, T43
and T44 do not run. The verdict is FAIL_MONO (futility; seed lottery not
excluded), or INSTRUMENT_INVALID (futility) if seed 42's I1F is BELOW. T42's
REACH and ISO checks run in either case.

Why this order: the only checks before PASS are deterministic properties of the
harness. In-window recall can turn only a MONO that fails in two seeds into
INSTRUMENT_INVALID, never a passing, split or unresolved MONO, and only when it
is under one half. A model that carries facts through its state at or above the
MONO line therefore reaches PASS, LOTTERY, FAIL_CROSS or INCONCLUSIVE; one that
carries them below the line reads FAIL_MONO. Neither can read an invalidity
verdict unless it fails to recall half of the facts in its own window (S1v2
checks this: an in-window anomaly with MONO passing, and MONO just under the line
with I1 at 0.70). Wave 1's draft would have labelled the second case
INSTRUMENT_INVALID in 0.999 of replicates under its 0.80
trigger.

Sub-labels (descriptive; each maps to a successor):
- FAIL_CROSS:
  - "surface" (rule 3b): cross recall is explained by surface form; the state
    stores surface features of keys. An instrument note; the dossier's port.
  - "state-specific": X1_attn ABOVE 0.15 in at least two seeds and X1_state
    BELOW 0.15 in at least two seeds. At the same distance (at most 480),
    attention matches across scripts and the state does not: the gap a
    translation-equivariant write loss would target, measured cleanly.
  - "decay": X1_state ABOVE 0.15 in at least two seeds. The state matches across
    scripts at short range but not at 1,600 or more: a retention or curriculum
    successor, not a write-alignment one.
  - "representational": X1_attn BELOW 0.15 in at least two seeds. No
    cross-script matching even through attention in-window: the dossier's port
    to the 2610.06750 LoRA setting.
  - "unresolved": otherwise.
- FAIL_MONO: "retention" (I1_state ABOVE 0.60 in at least two seeds: the state
  stores facts at short range and loses them by 1,600; a chrono-style
  initialization or curriculum successor), "no short-range state recall"
  (I1_state BELOW 0.60 in at least two seeds), "unresolved" otherwise.
- PASS carries a flag "relay-dominated" if A3 is above 0.5 in at least two seeds
  for MONO or for CROSS (reported separately): the facts reach the state mostly
  through attention-relayed writes, so the grid's write loss must target those
  writes, not only the fact's own span. Recorded for the grid's gauntlet.

Consequences:
- PASS: E7's phase-1 grid may be designed (a preregistered subspace or
  output-language guardrail design, the 2610.06750-style baseline, the SWA plus
  sinks baseline) and sent to its own gauntlet; admission is Kevin's under D24.
- FAIL_CROSS and FAIL_MONO: phase 1 is deferred; the successor is the one the
  sub-label names.
- LOTTERY: no three-seed grid on this instrument; a lock-in design (for example
  an accuracy-gated distance curriculum, 2609.16183) under a new id.
- INCONCLUSIVE: nothing is licensed; the intervals size any successor.
- INSTRUMENT_INVALID, HARNESS_INVALID: a fix under a new id.

No outcome makes an architecture claim or an equivariance claim.

## Reported regardless of outcome

- Every line per seed with its interval and class, at 1B and at the 200M branch,
  and per cell; the En-De cells if built.
- B1, B2 and B3 EM_t, forced choice, copy rate, per-digit accuracy and target
  log-probability by cell and seed, for real and decoy queries.
- REACH and ISO: the largest logit difference per seed; the uncut REACH pairs'
  differences (non-vacuity).
- The pathway reads X1_attn, X1_state, I1_attn, I1_state, R3, A3 (MONO and CROSS
  separately) and B2_attn, per seed.
- B-SURF's three values on the sealed manifest, and the oracle top-1 per cell.
- Decay timescale per GDN head at initialization and at 1B; the share above
  1,600.
- CSLS bitext retrieval P@1 on the development half (En with De, Zh and Th, both
  directions) at 200M and 1B on the mean-pooled residual stream per layer
  (language means subtracted) and on the pooled GDN write per GDN layer, with
  linear CKA.
- Per GDN head on development-half bitext pairs: the translation-pair write
  cosine minus its same-prefix floor; the legacy cos(W, P).
- A linear language-identity probe on the GDN state at sentence end, per layer.
- The beyond-reach in-context loss gap (positions 3,000 to 4,000 minus 400 to
  600) on held-out 4,096-token documents.
- The noise of B3 MONO and CROSS over 960M, 980M and 1B; the emergence curve.
- The step-overhead multiples, LR sweep losses, throughput, resume test and
  realized GPU-hours per job from `scontrol`.
- Deduplication counts, tokens per sentence per language, realized token counts.

## Statistics, sample sizes and simulation

S1v2 (`compute/repair-d68/gate-sim-v2.py`, `gate-sim-v2.json`; 1,000 replicates
per scenario over generators seeded 42, 43 and 44). Every classification uses
the registered estimator (sentence-cluster percentile bootstrap, B = 2,000,
bootstrap seed 42, so the resampling matrix is fixed as it will be in the
analysis). The design is the measured one: 699 test-half key sentences; MONO
cells 4 x 500; B1 cells 4 x 250; cross cells 474, 366, 314 and 235. The outcome
model is wave 1's (sentence random effects, standard deviation 1 on the logit
scale, shared across cells and seeds; distractor answers on half of the misses;
seed variation Gaussian on the probability scale or a two-point lock-in
mixture). Every distribution is an assumption.

Interval width and coverage:
- Mean 90% half-width per seed: MONO 0.0209 at 0.60, CROSS 0.0173 at 0.15, BIND 0.0188 and SEM 0.0229 at a CROSS of 0.15 (smaller cross cells than wave 1 assumed, so wider).
- Coverage of the registered bootstrap against the superpopulation rate (300 draws, nominal 0.90): MONO 0.917, CROSS 0.88.

P(PASS) by the true pooled rate of one line, the other lines comfortable (CROSS 0.30 in the MONO rows; MONO 0.85 in the CROSS rows; I1 0.95), by seed standard deviation on the probability scale:

| True rate | sd 0 | sd 0.03 | sd 0.06 |
|---|---:|---:|---:|
| MONO 0.3 | 0.000 | 0.000 | 0.000 |
| MONO 0.45 | 0.000 | 0.000 | 0.000 |
| MONO 0.55 | 0.000 | 0.000 | 0.010 |
| MONO 0.58 | 0.000 | 0.014 | 0.075 |
| MONO 0.6 (line) | 0.023 | 0.130 | 0.176 |
| MONO 0.62 | 0.459 | 0.415 | 0.329 |
| MONO 0.65 | 0.995 | 0.867 | 0.583 |
| MONO 0.7 | 1.000 | 0.999 | 0.891 |
| MONO 0.8 | 1.000 | 1.000 | 0.986 |
| CROSS 0.05 | 0.000 | 0.000 | 0.000 |
| CROSS 0.1 | 0.000 | 0.000 | 0.010 |
| CROSS 0.125 | 0.000 | 0.009 | 0.052 |
| CROSS 0.14 | 0.000 | 0.055 | 0.105 |
| CROSS 0.15 (line) | 0.011 | 0.150 | 0.161 |
| CROSS 0.16 | 0.156 | 0.272 | 0.236 |
| CROSS 0.18 | 0.909 | 0.657 | 0.416 |
| CROSS 0.2 | 1.000 | 0.906 | 0.617 |
| CROSS 0.25 | 1.000 | 1.000 | 0.920 |

Failure and lottery rates:
- P(FAIL_CROSS) at a true CROSS of 0.10: 1.000, 0.905 and 0.594 at seed SD 0, 0.03 and 0.06.
- P(FAIL_MONO) at a true MONO of 0.55: 0.998, 0.869 and 0.582.
- P(LOTTERY) at the CROSS line: 0.003, 0.351 and 0.567.

Surface form (seed SD 0.03 unless stated; MONO 0.85):
- A surface-only model (it always outputs an in-context code and picks the target as often as P1's learned surface oracle does, per cell, with real and with decoy queries): PASS 0.000 and FAIL_CROSS "surface" 1.000 under v2 (at seed SD 0: 0.000 and 1.000). Under v1's rule and v1's uniform distractors (P1's v1 oracle rates), the same kind of model reads PASS 1.000.
- Decoy-quality sensitivity: the decoy reproduces only a share phi of the surface-only model's excess over 1/8. P(PASS) with SEM's threshold 0.03 (and, on the same replicates, with a threshold of 0): phi 1.0: 0.000 (0.011); phi 0.8: 0.000 (0.147); phi 0.7: 0.002 (0.335); phi 0.6: 0.012 (0.600); phi 0.5: 0.052 (0.809); phi 0.4: 0.142 (0.932); phi 0.0: 0.949 (1.000).
- A mixed model that retrieves semantically on a share lambda of prompts and otherwise by surface form: PASS 0.080 at lambda 0.05 (FAIL_CROSS "surface" 0.920), 0.998 at 0.10 and 1.000 at 0.20.

Binding-free null (cross answers copy an in-context code uniformly with probability c): P(PASS) 0.000, 0.000 and 0.000 at c = 0.5, 0.8 and 1.0 (FAIL_CROSS 1.000, 1.000, 0.937).

Seed lock-in mixture on MONO and CROSS (locked seeds MONO 0.85 and CROSS 0.25, unlocked 0.15 and 0.06):
- P(PASS) 0.000, 0.023, 0.119, 0.353, 0.742, 1.000 at pi = 0.1, 0.3, 0.5, 0.7, 0.9 and 1.0;
- P(LOTTERY) 0.112, 0.261, 0.357, 0.335, 0.169, 0.000;
- share stopped by futility after seed 42 0.888, 0.716, 0.524, 0.312, 0.089, 0.000.

Invalidity verdicts:
- In-window anomaly with MONO passing (I1 0.70, MONO 0.80, CROSS 0.25): v2 PASS 0.999, LOTTERY 0.001; v1 INCONCLUSIVE 0.001, INSTRUMENT_INVALID 0.999.
- MONO just under its line with I1 0.70 (MONO 0.58): v2 PASS 0.012, LOTTERY 0.225, FAIL_MONO 0.401, INCONCLUSIVE 0.362; v1 FAIL_MONO 0.001, INSTRUMENT_INVALID 0.999.
- Weak in-window recall with MONO failing (I1 0.60, MONO 0.20): v2 FAIL_MONO 1.000; v1 INSTRUMENT_INVALID 1.000.
- Broken recall (I1 0.40, MONO 0.10): v2 FAIL_MONO 0.018, INSTRUMENT_INVALID 0.982.
- v1's single-reset cut on a PASS-level model (MONO 0.80, CROSS 0.25), the cut leaving a share of each prompt's above-floor target probability: P(INSTRUMENT_INVALID) under v1 0.004 at 0.0, 0.629 at 0.02, 1.000 at 0.05, 1.000 at 0.1, 1.000 at 0.25, 1.000 at 1.0. v2's REACH does not depend on recall (S3v2), and v2 reads PASS 1.000, 1.000, 1.000, 1.000, 1.000, 1.000 in the same scenarios.

Futility rule, single seed: P(stop) 1.000 at MONO 0.1, 1.000 at MONO 0.2, 0.995 at MONO 0.25, 0.548 at MONO 0.28, 0.047 at MONO 0.3, 0.000 at MONO 0.35, 0.000 at MONO 0.4. A stopped seed is BELOW, which already excludes PASS, so the rule never removes a PASS.

Decisiveness (decisive = PASS, FAIL_MONO including futility, FAIL_CROSS with any sub-label, or LOTTERY):
  - FAIL_MONO world (I1 0.90, MONO 0.25, CROSS 0.08): LOTTERY 0.004, FAIL_MONO 0.996 at seed SD 0.03 (decisive 1.000); decisive 1.000 at SD 0.06.
  - FAIL_CROSS world (MONO 0.80, CROSS 0.10): LOTTERY 0.048, FAIL_CROSS 0.905, INCONCLUSIVE 0.047 at seed SD 0.03 (decisive 0.953); decisive 0.927 at SD 0.06.
  - PASS world (MONO 0.80, CROSS 0.22): PASS 0.979, LOTTERY 0.013, INCONCLUSIVE 0.008 at seed SD 0.03 (decisive 0.992); decisive 0.964 at SD 0.06.
  - near-line world (MONO 0.62, CROSS 0.16): PASS 0.122, LOTTERY 0.454, FAIL_MONO 0.014, FAIL_CROSS 0.017, INCONCLUSIVE 0.393 at seed SD 0.03 (decisive 0.607); decisive 0.881 at SD 0.06.
  - lottery world (lock-in pi = 0.5): PASS 0.119, LOTTERY 0.357, FAIL_MONO 0.524 at seed SD 0.03 (decisive 1.000); decisive 1.000 at SD 0.06.
  - surface world (MONO 0.80, cross recall surface-only): FAIL_CROSS surface 1.000 at seed SD 0.03 (decisive 1.000); decisive 1.000 at SD 0.06.
  - broken-recall world (I1 0.40, MONO 0.10): FAIL_MONO 0.012, INSTRUMENT_INVALID 0.988 at seed SD 0.03 (decisive 0.012); decisive 0.129 at SD 0.06.
- Weighted by the owner's prior over worlds (FAIL_MONO 0.20, FAIL_CROSS 0.40, PASS 0.10, near-line 0.10, lottery 0.15, broken recall 0.05): P(decisive) 0.8917 at seed SD 0.03 and 0.9118 at SD 0.06.

Reading:
- With a seed SD of at most 3 points, the rule separates a model 5 points above the MONO line (P(PASS) 0.867) and 3 to 5 points above the CROSS line (0.657 at 0.18, 0.906 at 0.20) from models at the lines.
- At a seed SD of 6 points, or a lock-in rate under 0.9, it mostly returns LOTTERY or INCONCLUSIVE near the lines. That is the intended reading. In the lottery world most FAIL_MONO verdicts are futility stops with seed 42 the unlocked seed, which the verdict labels "seed lottery not excluded".
- Decisiveness counts LOTTERY as decisive because it is a registered verdict with its own consequence; that is why P(decisive) rises from SD 0.03 to SD 0.06.
- A surface-only model cannot PASS unless the decoy reproduces less than about half of its surface signal; B-SURF bounds that share on the sealed manifest.

Multiplicity: four decision lines (MONO, CROSS, BIND, SEM), each with a pre-registered threshold, in one conjunctive rule; I1F and DEC only route failures to labels. No line is tested twice, and the 200M read is descriptive. Runtime of S1v2: 1100.0 s on the development Mac.

## Compute caps (D22 counting)

S2v2 (`compute/repair-d68/cost-model-v2.py`, `cost-model-v2.json`). Base: the
measured 282,501.4 tokens/s (Slurm 359). Training time multiplier 1.25 central,
1.5 high; evaluation forward rate 2.0 x and 1.5 x the base; start-up 180 or
300 s; compile and autotune 180 or 300 s; checkpoint saves 60 or 110 s per
trunk; a cap is 1.2 x the high projection, rounded up to a minute.

| Job | Work | High projection | Cap (min) | Cap (GPU-h) | Central (GPU-h) |
|---|---|---:|---:|---:|---:|
| J1 | smoke 300 steps; probe 3 configurations x 100 steps x 3 repeats at 1 + 3 + 2 step-equivalents (1,800); LR sweep 3 x 50M tokens | 218.8M token-equivalents x 1.5 / 282,501.4 + 600 s = 1,761.8 s | 36 | 0.600 | 0.369 |
| J2 | resume test, 100 steps | 3.28M x 1.5 / 282,501.4 + 600 s = 617.4 s | 13 | 0.217 | 0.104 |
| J3 | conditional LR extension, 50M tokens | 50M x 1.5 / 282,501.4 + 600 s = 865.5 s | 18 | 0.300 | 0.161 if run |
| T42 | 1.04B training tokens; 165.15M evaluation tokens | 1.04B x 1.5 / 282,501.4 + 165.15M / (1.5 x 282,501.4) + 710 s = 6,621.8 s | 133 | 2.217 | 1.476 |
| T43 | same | 6,621.8 s | 133 | 2.217 | 1.476 |
| T44 | same | 6,621.8 s | 133 | 2.217 | 1.476 |
| Sum | | | 466 | 7.767 | 4.901 without J3 |

- Each cap is ceil(1.2 x high / 60) minutes: J1 ceil(35.24) = 36; J2 ceil(12.35)
  = 13; J3 ceil(17.31) = 18; each trunk ceil(132.44) = 133.
- Evaluation tokens per seed, 165.15M: primary reads 2 x 22.71M (B3 5,000 x
  2,950, B1 2,500 x 700, B2 2,500 x 1,180, decoys 3,000 x 60); noise 29.5M;
  emergence 49.5M; REACH 0.57M; ISO 0.38M; RELAY_BLOCK on B3 14.75M; D1 on B3
  14.75M; SPAN_CUT on B2 2.95M; B1 pathway reads 3.5M; CSLS, writes and probes
  10M.
- Admission: 466 minutes = 7.767 GPU-h <= 8.0. The factors and the throughput
  gate are fixed before J1 and not revisited after any measurement (D22).
- Throughput gate: J1 must measure at least 179,940 tokens/s (63.7% of the eager
  base), the rate at which a trunk fits its 133-minute cap with a 10% margin;
  below it the verdict is INFEASIBLE_THROUGHPUT and a new registration is needed.
- Expected use: 4.90 GPU-h central for three seeds; 1.95 if futility stops after
  T42.
- Resubmissions: the D22 sum counts every submitted job at its cap. The margin
  is 0.233 GPU-h, so at most one resubmission is allowed in the whole
  registration, and only of J2 (cap 0.217; sum then 7.984 <= 8.0). A crash of
  any other job before its first optimizer step stops the registration
  (INCOMPLETE; a fix is a new id). A crash during training resumes from the last
  atomic checkpoint in a fresh job whose run time counts against the same cap
  (at most two resumes per trunk).
- A job that reaches its cap stops. A trunk stopped before 1B gives INCOMPLETE for
  its seed, which counts as UNRESOLVED on every line.
- The gauntlet's own 0.3 GPU-h is reviewer inference and is separate.

## Infrastructure failures and exclusions

- Divergence: a non-finite loss, or a loss more than 0.5 nats above its
  1,000-step moving average for more than 1,000 steps. One restart from the last
  checkpoint before the event with the same data order, inside the same cap; a
  second divergence marks the seed DIVERGED, which counts as BELOW on every line
  (conservative; disclosed).
- A smoke failure stops the registration before any trunk. A fix is a code
  change reviewed under D7; whether it is material is decided before re-running
  (a material change is a new experiment id).
- No job is submitted while a Q2 job runs or is pending.

## Data rights

- Training: FineWeb and FineWeb-2 (ODC-By 1.0, with Common Crawl terms);
  ParaDocs (Apache-2.0 packaging; the underlying ParaCrawl, News Commentary and
  Europarl texts keep their terms); the ParaCrawl Bonus release (CC0
  packaging); SCB-MT-EN-TH-2020 (CC BY-SA 4.0). The co-present presentation uses
  the same sources.
- Instrument: NTREX-128 (CC BY-SA 4.0); FLORES+ is CC BY-SA 4.0 but gated.
- Excluded: TED2020 (D4) and General Translation customer data.
- The public repository receives ids, offsets, hashes, metrics, configs and
  per-example predictions, never source text. The repair's CPU checks read
  NTREX from a local copy and write counts and rates only.
- Checkpoints stay on the host or in the private archive.
- The 2610.06750 code repository has no licence, so the probe's auxiliary pass is
  reimplemented from the paper and never vendored.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the cpu-doctor node's intervention
   table on the harness's own module graph (it must match the symbolic
   reachability row by row), REACH and ISO on every trained checkpoint, the
   cached-versus-uncached evaluator check, the manifest assertions, B-SURF and
   the I1 positive control each catch a different class of bug. S3v2 already
   caught one: beta = 0 alone leaves a path through the decay gate.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot with its
   version history; OpenReview items are labelled abstract-only.
3. Hallucinated experimental result: no number here is a model result. S1v2,
   S2v2, S3v2 and P1 are labelled simulations, estimates, a reference-graph check
   and a CPU measurement on NTREX text, with scripts and outputs.
4. Shortcut reliance: the copy floor is cancelled by BIND; surface form by the
   4-gram filter, the sliding-block distractors, the decoy contrast SEM and
   B-SURF; attention relay by the reach bound, verified by REACH.
5. Bug reframed as insight: a REACH or ISO failure is HARNESS_INVALID, never a
   finding about the state; in-window recall under one half with MONO failing
   is INSTRUMENT_INVALID.
6. Methodology fabrication: every procedure names its code path and is checked
   against the harness at the pre-freeze audit.
7. Frame-lock: likely outcomes are stated below; FAIL_CROSS and INCONCLUSIVE are
   acceptable results; wave 1's design was abandoned where it failed, and the
   first repair of the distractor design (stratified sampling, P1 "v2a") is
   reported as insufficient rather than registered.

## Owner's prior forecast (not a decision input)

- P(HARNESS_INVALID or INSTRUMENT_INVALID) about 0.05.
- P(FAIL_MONO, including futility) about 0.2.
- P(LOTTERY) about 0.15.
- P(FAIL_CROSS) about 0.4: "representational" and "state-specific" about
  equally likely now that half the bitext is co-present; "surface" and "decay"
  about 0.05 each.
- P(INCONCLUSIVE) about 0.1.
- P(PASS) about 0.1.

The literature sets low priors for cross-lingual transfer at this scale
(2609.19291 at 360M; the first translations without token overlap at about 11B
tokens in a 1.7B model, 2604.17633) and shows that small models align across
scripts under coherent code-switching (2609.30535).

## Freeze procedure

After the prerequisites and a fresh pre-freeze audit, and after Kevin accepts the
design decisions:

```bash
uv run python scripts/preregister.py freeze e7-equivariant-writes-g1-v2 program/preregistrations/e7-equivariant-writes-g1-v2.md
uv run python scripts/preregister.py verify e7-equivariant-writes-g1-v2
```

## Design decisions (for the owner's acceptance)

Unchanged from v1 unless marked (v2).

1. Scope: G1 only; phase-1 arms and the P-GSM confirmation are out of scope.
2. (v2) B3 defined by the facts block: d_f >= 1,600; B1 every fact at d <= 480;
   B2 every fact in [560, 1,520].
3. Seeds [42, 43, 44], per-seed classification, at least two ABOVE and none
   BELOW.
4. LOTTERY for seed splits across MONO or CROSS.
5. Futility after seed 42 at a MONO upper bound under 0.30 (v2: INSTRUMENT_INVALID
   instead of FAIL_MONO if seed 42's I1F is BELOW).
6. Training context 4,096 at batch 8.
7. The A0 layout, GDN settings and MLP as measured; SWA-512 with RoPE and no
   sinks.
8. Test languages En, De, Zh and Th; Spanish dropped.
9. NTREX-128 as the instrument source unless Kevin accepts the FLORES+ terms.
10. Keys with digits excluded; codes from a reserved set of 2,000.
11. (v2) The surface filter with the legacy letter-4-gram clause, against all
    eight keys, for real and decoy queries.
12. (v2) B3 MONO 500 per cell; B3 CROSS every eligible queried sentence up to 500;
    B1 and B2 250; a floor of 150 per cell.
13. Equal cell weights in pooled lines.
14. (v2) BIND (> 0) and SEM (lower bound at least 0.03) required for PASS; DEC
    for the surface sub-label.
15. (v2) I1 reported against 0.80; INSTRUMENT_INVALID only when in-window recall
    is under the floor I1F = 0.50 in two seeds and MONO fails.
16. (v2) Sub-labels from distance-matched pathway reads (X1_attn, X1_state,
    I1_state) and the surface sub-label.
17. The 90% sentence-cluster bootstrap, B = 2,000, for every line.
18. The 32K Unigram tokenizer.
19. Monolingual shares En 30, De 15, Zh 15, Th 15.
20. (v2) Bitext half prefix-sharing (c + a and c + b) and half co-present (a then
    b, or b then a, in one document).
21. The curriculum's fact counts, distance mixture and same-language rule.
22. The LR grid, selection on held-out LM loss, one conditional extension.
23. The WSD trunk with a 20% (1 - sqrt) decay and the 200M branch from 160M.
24. (v2) The step-overhead probe as non-gating, 100 steps per configuration per
    repeat, three repeats.
25. (v2) The throughput gate at 179,940 tokens/s.
26. The cap factor 1.2 and the S2 assumptions.
27. The divergence rule.
28. (v2) The read list, including the check pairs and pathway reads, as the
    complete set of sealed-manifest reads.
29. The diagnostics list, all descriptive.
30. The data sources.
31. (v2) Deduplication of both NTREX halves against training (decoys use both).
32. The 2610.06750 auxiliary pass reimplemented, never vendored.
33. (v2) REACH and ISO as deterministic harness checks at tolerance 1e-5, with
    HARNESS_INVALID first in the verdict order.
34. (v2) Cross-script cells only in CROSS, BIND and SEM; En-De descriptive.
35. (v2) Sliding-block distractors and surface-twin decoys, with B-SURF's
    thresholds (0.155, 0.25, 0.03 pooled and 0.06 per cell) and up to two
    redraws.
36. (v2) Resubmissions limited to one J2 resubmission so that the D22 sum stays
    at or under 8.0 GPU-h.
