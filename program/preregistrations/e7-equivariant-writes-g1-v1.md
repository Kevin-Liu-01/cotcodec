# E7 G1 floor gate v1: state-necessary monolingual and cross-lingual recall in a from-scratch 134M Gated DeltaNet plus SWA-512 hybrid without an equivariance loss (e7-equivariant-writes-g1-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the E7 research gauntlet (D67) on branch
`gauntlet/e7-d22`. It registers only E7's G1 floor gate: the A0 hybrid (no
equivariance loss) trained from scratch, read at 200M and 1B tokens. The
phase-1 grid (A1 write equivariance, A2 projection alignment, A3 placebo, A5
no-bitext, a 2610.06750-style baseline) is not registered here. It needs a
preregistered subspace or output-language guardrail design, its own gauntlet
and, being over 8 GPU-h, Kevin's admission under D24. The frozen Qwen3.5-4B
split-prefill confirmation belongs to P-GSM, not here. The design decisions
at the end (1 to 32) need the program owner's acceptance. The caps below sum
to 7.733 GPU-h under D22's counting rule. No host job of any kind runs while a
Q2 S1a VM or GPU job is running or pending. The proposal that argues and
attacks this design is
`program/proposals/2026-10-10-e7-equivariant-writes-g1.md`; its evidence
bundle is `program/proposals/evidence/2026-10-10-e7-equivariant-writes-g1/`.

## Relation to the dossier and to D67

- Source: dossier entry `E7-d22-translation-equivariant-writes`
  (`program/evidence/2026-10-06/question-dossier.md`, section 16), "First
  experiment" and "Kill criteria". The name "D22" in the dossier key is
  direction 22, not decision D22 of `program/decisions.md`; decision D22's
  counting rule (caps are summed, never expected use) applies to this file.
- Kept: the A0 hybrid without the equivariance loss; SWA-512 replacing full
  attention in the measured 134M configuration; reads at 200M and 1B tokens;
  the 75 / 20 / 5 mixture of monolingual text, prefix-sharing bitext and a
  recall curriculum; TP-MQAR-v2 exact match at N = 8 on facts the attention
  cannot reach; the lines "monolingual at least 60%, cross-lingual at least
  15% at 1B tokens"; the consequence of a failure (defer phase 1 and port the
  comparison to the 2610.06750 LoRA setting rather than scaling the toy
  model); the step-overhead probe that prices the later grid.
- Changed, each for a stated reason (the proposal's merge table gives the
  sources):
  1. "Beyond-window (more than 512 tokens back)" becomes the state-necessary
     bin B3: every fact at least 1,600 tokens before the answer position.
     Without the recurrent state, the A0 layer graph moves information at most
     3 x 511 + 9 x 3 = 1,560 positions (three SWA-512 layers plus the GDN
     short convolutions), and trained SWA models do relay information past one
     window (2609.34049). S3 (`compute/reach-doctor.py`) checks the bound by
     perturbation on a NumPy stand-in of the layer graph.
  2. One seed becomes three, [42, 43, 44] (rule 6), with a per-seed
     classification, a majority rule and a LOTTERY verdict, because recurrent
     recall lock-in varies by seed (2609.16183, first-party, preliminary).
  3. Training context 4,096 tokens at batch 8 (32,768 tokens per step, the
     measured tokens per step), so that B3 fits inside the training length.
     Parameters stay at 133.96M.
  4. Chance is not 1e-4. A model that outputs one of the eight in-context
     codes without matching the key scores 1/8 = 12.5% exact match. The 15%
     cross line certifies as little as (0.15 - 0.125) / 0.875 = 2.9% genuine
     binding. The line is kept as written; a binding guard (BIND) is added.
  5. The test languages match the training languages: En, De, Zh, Th. The
     legacy contract tested En, De and Es while Spanish was absent from
     training.
  6. The legacy dense rescue arm is replaced by a within-model decomposition:
     the same checkpoint read on facts directly inside the window (B1) and in
     the relay range (B2), plus an eval-time state cut.
  7. A three-point learning-rate sweep on held-out LM loss (seed 42, 50M
     tokens each, one conditional edge extension).
  8. One warmup-stable-decay trunk to 1B tokens per seed, with the 200M read
     taken from a 40M-token decay branch at 160M tokens (2405.18392).
  9. A futility stop after seed 42 on monolingual recall.
  10. The dossier's 2.5 GPU-h was one seed. Three seeds cost 4.87 GPU-h
      central and 7.733 GPU-h in summed caps (S2).
  11. Test sentences come from NTREX-128 (CC BY-SA 4.0, ungated) unless the
      program owner accepts the FLORES+ gated terms before freeze (design
      decision 9). FLORES+ is gated on Hugging Face, and accepting its terms is
      Kevin's action.

## Question

For a 134M hybrid of nine Gated DeltaNet layers and three SWA-512 layers
(layout of the measured configuration), trained from scratch for 1B tokens on
En, De, Zh and Th text with 20% prefix-sharing bitext and a 5% same-language
recall curriculum, and with no equivariance loss: at N = 8 facts that all lie
at least 1,600 tokens before the answer position, does the model reach exact
match of at least 60% when the query repeats the key in its own language
(MONO), and at least 15% when the query is a surface-disjoint translation of
the key (CROSS), with recall bound to the queried key (BIND), in at least two
of three seeds and in no seed below the line?

Claim scope: an admission-gate benchmark outcome on one from-scratch
architecture at one scale (evidence level "benchmark", status "admission pass"
in `docs/evidence-model.md`). It is not architecture-causal (no matched
control; rule 8) and claims nothing about any equivariance loss. PASS licenses
only a gauntlet for E7's phase-1 grid.

## Identity

- Experiment id: `e7-equivariant-writes-g1-v1`.
- Proposal: `program/proposals/2026-10-10-e7-equivariant-writes-g1.md`.
- Code revision: the commit that adds the harness, fixed at freeze; the image
  is built from that commit by the project's CPU build job and pinned by
  digest before the smoke.
- Image lineage: the measured throughput used
  `127.0.0.1:5000/cotcodec-research@sha256:02965f3d696d4e516a7cd6d5c03434e9098139738748ae778ed967215db7be6d`
  (`cotcodec-research:0b3ecef0-architecture`, image ID `sha256:38044666...`;
  torch 2.11.0+cu128, flash-linear-attention 0.5.2, triton 3.6.0, tilelang
  0.1.13). The tilelang path works around fla #640 (gated GDN backward on
  Hopper under Triton < 3.7.1).
- Seeds: 42, 43, 44 (initialization, data order, curriculum instances). The
  prompt set and the bootstrap use seed 42 and are shared by all seeds.

## Prerequisites before freeze (no GPU)

1. Harness, reviewed project code under D7, each part unit-tested on CPU:
   - the A0 model: fla `GatedDeltaNet` layers and an SWA-512 attention layer
     through torch `flex_attention` with a sliding-window block mask, plus a
     pure-torch reference recurrence for CPU tests;
   - the training loop: fp32 master weights with bf16 autocast, AdamW,
     warmup-stable-decay, packed rows with document-boundary resets
     (`cu_seqlens` for GDN, block-diagonal masks for SWA), atomic checkpoints
     every 15 minutes to persistent storage, a SIGUSR1 checkpoint and a
     fresh-job resume;
   - the tokenizer trainer and the mixture, bitext and curriculum builders;
   - the TP-MQAR-v2-G1 builder, including the surface filter and the sealed
     manifest;
   - the evaluator: teacher-forced digits for the target and the seven
     distractor codes with prefix caching, the state cut and the fact-write
     ablation;
   - the diagnostics and the analysis (bootstrap, classification, verdict).
2. A `kind: cpu-doctor` orx node that runs (a) a perturbation reach test on a
   small random instance of the real module graph (pure-torch reference
   path), which must show no dependence beyond 1,560 positions with the state
   cut and dependence with it; (b) the analysis pipeline on synthetic
   predictions with known rates, which must recover them within the S1
   standard deviations; (c) the prompt builder's leakage controls.
3. Data fetched with receipts under D1 (source, revision, size, SHA-256):
   FineWeb (rev 9bb295dd), FineWeb-2 deu_Latn, cmn_Hani and tha_Thai
   (rev af9c1333), ParaDocs en-de and en-th (rev f80095af), the ParaCrawl
   Bonus en-zh release, SCB-MT-EN-TH-2020 (rev 613aad4a), and NTREX-128
   (commit 468c6b69). This is a host action and waits until no S1a VM or GPU
   job is running.
4. Deduplication report: every instrument sentence (all four languages)
   against every training stream and the curriculum key pool, by exact match
   and MinHash on character 5-grams at Jaccard at least 0.5. Matches are
   removed from the training streams, never from the instrument; counts are
   reported.
5. The sealed prompt manifests (B1, B2, B3, diagnostics) with SHA-256,
   committed as ids, offsets and hashes without text.
6. Slurm manifests for J1, J2, J3, T42, T43 and T44; `--dry-run` and
   `--test-only` pass for each.
7. A fresh pre-freeze audit of this file against the harness.

## Model (A0)

- 12 blocks, hidden 768, pre-norm RMSNorm, tied embeddings, vocabulary
  32,000. Blocks 3, 7 and 11 (zero-indexed) are attention; the other nine are
  GDN. This is the layout of `scripts/fla_throughput_doctor.py`
  (`i % 4 == 3`), and of the legacy contract's "SWA at 4, 8, 12" (one-indexed).
- GDN: fla 0.5.2 `GatedDeltaNet(hidden_size=768, num_heads=12, head_dim=64,
  expand_v=1, mode="chunk", use_gate=True, use_short_conv=True, conv_size=4,
  allow_neg_eigval=False)` with fla's default initialization (A ~ U(0, 16),
  dt log-uniform on [0.001, 0.1]).
- Attention: causal sliding window, W = 512, so position i attends to
  positions i - 511 to i; 12 heads of 64; q, k, v and output projections
  without bias; RoPE (theta 10,000) on q and k; no attention sinks and no
  global tokens. Position i never sees a token more than 511 positions back
  through one attention layer.
- MLP after every mixer, exactly as in the measured module: Linear 768 to
  4,096, SiLU, Linear 4,096 to 768, no bias. The receipt's "SwiGLU 8/3" label
  describes the widths, not a gated unit.
- Parameter count 133.96M (as measured; the attention projections have the
  same shape as the measured `nn.MultiheadAttention`).
- State-free reach: 3 x 511 + 9 x 3 = 1,560 positions. B3's minimum distance
  of 1,600 leaves a 40-token margin.

## Tokenizer

Hugging Face `tokenizers` Unigram, 32,000 entries including the specials
`[bos]`, `[eos]`, `[pad]` and `[kv]` (the fact separator); NFKC; byte
fallback; digits split into single tokens. It is trained on 100M characters
per language (En, De, Zh, Th) from the training pools, never on instrument
text. Tokens per sentence on the instrument's development half are reported
per language (the fertility confound that E5 studies).

## Training data and schedule

- Pool, per seed one pass over the same pool in a seed-specific order:
  1.04B tokens.
  - Monolingual, 75%: En 30% (FineWeb), De 15%, Zh 15% and Th 15% (FineWeb-2).
  - Prefix-sharing bitext, 20%: En-De, En-Zh and En-Th, 6.67% each (ParaDocs
    en-de; ParaCrawl Bonus en-zh; SCB-MT-EN-TH-2020 plus ParaDocs en-th). A
    record is two sequences, c + a and c + b, packed as separate documents in
    the same row. Here (a, b) is an aligned segment of one to three sentences,
    and c is 64 to 256 tokens of held-out monolingual text in a language drawn
    uniformly from the pair's two languages, bitwise identical in both
    sequences. Each sequence then contains a coherent sentence-level language
    switch for one of the two languages. This is the presentation the later
    write loss needs, so the G1 A0 is the grid's A0.
  - Recall curriculum, 5%: records of up to 4,096 tokens. A record holds
    N_c facts, N_c uniform on {4, 8, 16}, written as `key [kv] dddd` and
    separated by newlines. Keys are training-pool sentences of 8 to 60 tokens
    with no digits. All keys and queries in a record share one language,
    drawn uniformly from the four. Then come filler (training-pool text of
    that language with every digit removed) and four queries `key [kv] dddd`
    about distinct facts.
    - Distance: the first query's distance to the nearest fact is drawn per
      record from 25% U[16, 511], 25% U[512, 1,560] and 50% U[1,600, 3,900].
    - Codes come from the 8,000 four-digit codes outside the reserved test
      set.
    - No cross-lingual query ever appears in the curriculum.
- Packing: rows of 4,096 tokens, document-boundary resets (no state or
  attention crosses a document boundary).
- Optimizer: AdamW (beta1 0.9, beta2 0.95, eps 1e-8); weight decay 0.1 on
  matrices only (not on norms, A_log or dt_bias); gradient clipping 1.0; fp32
  master weights with bf16 autocast; batch 8 x 4,096.
- Schedule: linear warmup over 500 steps, constant peak, then a (1 - sqrt)
  decay to zero over the last 20% of the run.
  - Trunk: stable to 800M tokens, decay from 800M to 1B.
  - 200M read: a branch from the trunk's 160M checkpoint, decayed over 40M
    tokens, inside the trunk job.
  - LR runs: 50M tokens, decay from 40M to 50M.
- Learning rate: peak in {6e-4, 1.2e-3, 2.4e-3}, seed 42, first 50M tokens of
  the seed-42 order. The selected value has the lowest mean held-out LM loss
  (2M held-out tokens per language, languages weighted equally); a tie within
  0.005 nats goes to the smaller value. If the selection is at a grid edge,
  J3 runs one value beyond it (3e-4 or 4.8e-3), and the selection is redone
  over four values. All three seeds use the selected value. The instrument is
  never read during selection.

## Instrument (TP-MQAR-v2-G1)

- Source: NTREX-128 (commit 468c6b69; deu, zho-CN, tha and the English
  source; CC BY-SA 4.0). Documents are split 50/50 by a seed-42 hash of the
  document id into a development half (diagnostics only) and a test half
  (prompts). Key sentences are test-half sentences of 8 to 60 tokens in every
  language with no digit in any language. If the program owner accepts
  FLORES+ before freeze, FLORES+ dev is the development half and devtest the
  test half, with every other rule unchanged (design decision 9).
- Cells: monolingual En, De, Zh, Th (the query repeats the key exactly);
  cross-lingual En->De, De->En, En->Zh, Zh->En, En->Th, Th->En (facts in the
  first language, query in the second).
- Prompt: `[bos]`, eight facts `key [kv] dddd` with keys in the fact
  language, filler, then the query `key [kv]`, after which the four code
  digits are scored.
  - Codes are distinct within a prompt and drawn from a reserved set of 2,000
    codes never used in training.
  - Filler is held-out monolingual text in the fact language, never used in
    training and never taken from the instrument's development half, with
    every digit removed and deduplicated against everything else.
  - The target fact's slot is balanced over the eight positions.
  - Distractor keys are drawn from the eligible pool, excluding the queried
    sentence.
- Surface filter (cross cells): the query shares with none of the eight
  fact keys an NFKC-casefolded whitespace token, a digit string, or a
  32K-tokenizer token of at least four characters. Distractors are resampled
  until the filter holds (at most 50 tries; else the sentence is not
  eligible).
- Distance d: tokens from the last token of a fact record to the position
  that predicts the first code digit.
  - B1 (direct): the queried fact at d ≤ 480.
  - B2 (relay): every fact at 560 ≤ d ≤ 1,520.
  - B3 (state-necessary, the gate): every fact at d ≥ 1,600, the queried fact
    at d ≤ 3,500, total length ≤ 4,096. Within B3 the gap is drawn uniformly
    subject to these limits.
- Sizes: B3 500 prompts per cell, B1 and B2 250 per cell. Each queried
  sentence is used once per cell and bin. A cross cell with fewer eligible
  sentences uses all of them. A cell with fewer than 150 is dropped from the
  pooled statistics, decided and recorded when the prompts are built, before
  any model exists.
- Sealing: manifests hashed and committed before J1 starts. Every read of a
  sealed manifest is logged with checkpoint, job and time; a read not in the
  "Reads" list below is a leak and is reported.

## Jobs

### J1: smoke, probe and LR sweep (cap 34 min, one GPU)

1. Smoke: 300 steps on the real mixture with seed 42; a checkpoint at step
   200 by SIGUSR1; throughput measured over steps 100 to 300 in three repeats
   of 50 steps after warm-up.
2. Gates (all must hold, else the job stops and the registration does not
   proceed):
   - finite loss decreasing over the 300 steps;
   - the cached-candidate evaluator equals the uncached one on 50 prompts
     (maximum absolute log-probability difference ≤ 1e-3);
   - the state cut gives the same logits as a separately started forward
     pass from a zero state at the cut position;
   - measured training throughput r ≥ 179,329 tokens/s (S2: the rate at which
     a trunk fits its 133-minute cap with a 10% margin). Below it the verdict
     is INFEASIBLE_THROUGHPUT and a new registration is needed.
3. Step-overhead probe (non-gating; it prices the later grid): 200 steps each
   of A0, A0 plus A1 write extraction (two `chunk_gated_delta_rule` passes
   from `initial_state` = S(c), the second with v = 0, on 64 bitext pairs per
   step in half the heads), and A0 plus one 2610.06750-style auxiliary pass
   (attention blocked across a segment boundary, recurrent state carried).
   Each is reported as seconds per step and multiple of A0, with three
   repeats.
4. LR sweep as above (three runs of 50M tokens, sequential in the job).

### J2: fresh-job resume test (cap 13 min, one GPU)

A new job loads J1's step-200 checkpoint and runs to step 300. It requires:
- identical batch token-id hashes and optimizer step counts;
- per-step loss within max(2e-3, 3 x the run-to-run difference of two
  uninterrupted segments measured in J1);
- final parameters within the same relative tolerance.

### J3: conditional LR extension (cap 18 min, one GPU)

Runs only if the selected LR is at a grid edge.

### T42, then T43 and T44: trunk, branch and reads (cap 133 min each, one GPU each)

- 1B-token trunk with the 40M-token branch at 160M.
- Named checkpoints at 100M, 160M, 200M (branch), 400M, 800M, 960M, 980M and
  1B, plus the 15-minute atomic checkpoints.
- All reads run in the same job after training.
- T43 and T44 start only after T42's 1B read, and only if the futility rule
  does not stop.

## Reads (every read of the sealed manifests)

- Primary: the 200M branch and the 1B checkpoint. B1, B2 and B3, target and
  seven distractor codes.
- Noise: 960M and 980M. B3, target only.
- Emergence: 100M, 400M and 800M (before decay). B3 and B1, target only.
- Diagnostics at 1B: the state cut on B2 and B3 and the fact-write ablation
  on B3.
- Nothing else reads the sealed manifests.

## Metrics

Per prompt:
- EM_t: the argmax at each of the four digit positions equals the target
  digit under teacher forcing, which is equivalent to greedy decoding
  producing the target.
- EM_j for each of the seven distractor codes, computed the same way.
- Per-digit accuracy, the target's summed log-probability, and forced choice
  (the target has the highest summed log-probability among the eight codes;
  chance 1/8).
- The copy rate: the greedy answer equals any in-context code.

Per seed and checkpoint (equal weights over cells):
- MONO = mean over the four monolingual cells of B3 EM_t.
- CROSS = mean over the six cross cells of B3 EM_t.
- BIND = mean over the six cross cells of B3 (EM_t minus the mean over j of
  EM_j). It is zero in expectation for any answer strategy that ignores the
  query's key, because the target slot is balanced.
- I1 = mean over the four monolingual cells of B1 EM_t (instrument positive
  control).
- X1 = mean over the six cross cells of B1 EM_t (decomposition, descriptive).

Intervals: 90% percentile bootstrap clustered by key sentence. A resample
draws sentence ids with replacement, and every prompt that queries a drawn
sentence, in any cell, moves with it. B = 2,000, seed 42.

## Lines and decision rules

At the 1B checkpoint, separately for each seed, each line is classified:
- ABOVE when the interval's lower bound is at least the threshold (for BIND,
  greater than 0);
- BELOW when the upper bound is under the threshold;
- UNRESOLVED otherwise.

Thresholds: I1 0.80; MONO 0.60 (dossier); CROSS 0.15 (dossier); BIND 0. A
line passes when at least two of the three seeds are ABOVE and none is BELOW.

Two identification checks are run at 1B per seed, on B3 with MONO and
CROSS cells pooled. Both use the binding margin beta = EM_t minus the mean
over j of EM_j, so the copy floor cancels.

- CUT: under the state cut, the binding margin's 90% lower bound is at most
  0. The cut removes every path from the facts to the query, so a positive
  margin means the reach bound or the cut is wrong.
- ABLATION: under the fact-write ablation, the binding margin is at most
  half of the unablated margin (point estimates). Otherwise B3 recall is not
  running through the queried fact's write.

Neither check is simulated in S1. Each has a near-deterministic expectation
if the harness is correct.

Verdict, the first that applies:

1. INSTRUMENT_INVALID: I1 BELOW in at least two seeds, or CUT fails in at
   least two seeds. An engineering failure (the model cannot recall a fact
   inside its own window, or the state cut does not remove state-necessary
   recall); no statement about the state. A fix is a new experiment id.
2. PASS: I1, MONO, CROSS and BIND all pass, and ABLATION holds in at least
   two seeds. If every line passes but ABLATION does not, the verdict is
   INCONCLUSIVE with the reason "identification not established".
3. LOTTERY: MONO or CROSS has at least one seed ABOVE and at least one
   BELOW.
4. FAIL_MONO: MONO BELOW in at least two seeds.
5. FAIL_CROSS: MONO ABOVE in at least two seeds, and CROSS BELOW in at least
   two seeds or BIND BELOW in at least two seeds. It carries a descriptive
   sub-label from X1:
   - "state-specific" when X1 is ABOVE 0.15 in at least two seeds;
   - "representational" when X1 is BELOW 0.15 in at least two seeds;
   - "unresolved" otherwise.
6. INCONCLUSIVE: anything else.

Futility rule: after T42's 1B read, if seed 42's MONO upper bound is under
0.30, T43 and T44 do not run. The verdict is FAIL_MONO (futility; seed
lottery not excluded) and is reported as such.

Consequences:
- PASS: E7's phase-1 grid may be designed (a preregistered subspace or
  output-language guardrail design, the 2610.06750-style baseline, the SWA
  plus sinks baseline) and sent to its own gauntlet. Admission is Kevin's
  under D24 (over 8 GPU-h).
- FAIL_MONO, FAIL_CROSS: phase 1 is deferred. The comparison is ported to the
  2610.06750 LoRA setting rather than scaling the toy model (dossier).
- LOTTERY: no three-seed grid on this instrument. A successor needs a lock-in
  design (for example an accuracy-gated distance curriculum) under a new id.
- INCONCLUSIVE: nothing is licensed; the intervals size any successor.
- INSTRUMENT_INVALID: a code fix under a new id.

No outcome makes an architecture claim or an equivariance claim.

## Reported regardless of outcome

- Every line per seed with its interval and class, at 1B and at the 200M
  branch, and per cell and language pair. Same-script (En-De) and
  cross-script (En-Zh, En-Th) pairs are reported separately.
- B1, B2 and B3 EM_t, forced choice, copy rate, per-digit accuracy and target
  log-probability, by cell and seed.
- The state cut on B2 and B3: the GDN recurrent and convolution states are
  reset to zero at the first token after the facts block (the attention-only
  condition of 2610.06750, Sec. 4.1).
  - B3 under the cut is the CUT check.
  - B2 under the cut measures how much relay-range recall attention alone
    carries.
- The fact-write ablation on B3: GDN values zeroed on the queried fact's
  tokens in all GDN layers. This is the ABLATION check, reported per cell.
- Decay timescale per GDN head at initialization and at 1B (the mean over
  the development half of A_h x softplus(a_proj x + dt_bias_h), inverted).
  Reported: the share of heads with a timescale above 1,600.
- CSLS bitext retrieval P@1 on the development half, En with each of De, Zh
  and Th, both directions, at 200M and 1B. It is computed on the mean-pooled
  residual stream per layer (language means subtracted) and on the pooled GDN
  write W(a|c) per GDN layer (c a fixed neutral prefix), with linear CKA
  beside it.
- Per GDN head on development-half bitext pairs, descriptive inputs for
  sizing the later grid:
  - the translation-pair write cosine cos(W^A, W^B) minus its same-prefix
    floor;
  - the legacy distinctness statistic cos(W, P).
- A linear language-identity probe on the GDN state at sentence end, per
  layer (5-fold).
- The beyond-reach in-context loss gap on held-out documents of 4,096 tokens:
  mean loss at positions 3,000 to 4,000 minus mean loss at positions 400 to
  600.
- The noise of B3 MONO and CROSS over the 960M, 980M and 1B checkpoints
  (relative standard deviation).
- The emergence curve: B3 and B1 at 100M, 400M, 800M, the 200M branch and 1B.
- The step-overhead multiples, the LR sweep losses, the throughput, the
  resume test, and the realized GPU-hours per job from `scontrol`.
- The deduplication counts, tokens per sentence per language, and the token
  count of each language in the realized stream.

## Statistics, sample sizes and simulation

S1 (`compute/gate-sim.py`, `compute/gate-sim.json`; 1,000 replicates per
scenario over generators seeded 42, 43 and 44). The assumed outcome model has
sentence random effects (standard deviation 1 on the logit scale) shared
across cells and seeds, fixed cell offsets, distractor answers on half of the
misses, and seed variation either Gaussian on the probability scale or a
two-point lock-in mixture. Every distribution is an assumption.

Interval width and coverage:
- Mean 90% half-width per seed: 0.013 for CROSS at 0.15 and 0.020 for MONO
  at 0.60.
- At the CROSS line (300 draws, B = 2,000 Poisson bootstrap), coverage was
  0.933 for the sentence-cluster bootstrap and 0.940 for the CR1 normal
  interval, against a nominal 0.90. Their classifications agreed in 0.993 of
  draws.

P(PASS) by the true pooled rate of one line, with the other lines
comfortable (CROSS 0.30 in the MONO rows; MONO 0.85 in the CROSS rows; I1
0.95), by seed standard deviation on the probability scale:

| True rate | sd 0 | sd 0.03 | sd 0.06 | sd 0.10 |
|---|---:|---:|---:|---:|
| MONO 0.55 | 0.000 | 0.000 | 0.008 | 0.024 |
| MONO 0.58 | 0.000 | 0.015 | 0.066 | 0.072 |
| MONO 0.60 (line) | 0.020 | 0.131 | 0.161 | 0.122 |
| MONO 0.62 | 0.517 | 0.442 | 0.311 | 0.179 |
| MONO 0.65 | 0.997 | 0.886 | 0.592 | 0.291 |
| MONO 0.70 | 1.000 | 1.000 | 0.910 | 0.509 |
| CROSS 0.10 | 0.000 | 0.000 | 0.020 | 0.030 |
| CROSS 0.125 | 0.000 | 0.017 | 0.050 | 0.061 |
| CROSS 0.15 (line) | 0.015 | 0.155 | 0.150 | 0.120 |
| CROSS 0.16 | 0.294 | 0.280 | 0.215 | 0.163 |
| CROSS 0.18 | 0.996 | 0.662 | 0.396 | 0.234 |
| CROSS 0.20 | 1.000 | 0.902 | 0.570 | 0.334 |
| CROSS 0.25 | 1.000 | 0.999 | 0.887 | 0.567 |

Failure and lottery rates:
- P(FAIL_CROSS) at a true CROSS of 0.10 is 1.000, 0.919, 0.594 and 0.384 at
  the four seed SDs.
- P(LOTTERY) at the CROSS line is 0.002, 0.427, 0.591 and 0.664.

Joint scenarios:
- All four lines 5 points above their thresholds (I1 0.85, MONO 0.65, CROSS
  0.20) at seed SD 0.03: PASS 0.717. At 10 points above: 0.998. At 5 points
  above with seed SD 0.06: 0.199, with LOTTERY 0.545. All four at their lines
  with seed SD 0.03: 0.005.
- CROSS 3 points below the line with MONO 0.70: PASS 0.010, FAIL_CROSS
  0.679.

I1:
- P(INSTRUMENT_INVALID) is 1.000 at a true I1 of 0.60, 0.895 at 0.75, 0.153
  at 0.80 and 0.002 at 0.85.

Binding-free null:
- Every cross answer copies one of the eight in-context codes uniformly,
  with probability 0.5, 0.8 or 1.0, so the target is hit at most 12.5% of the
  time.
- P(PASS) is 0.000 in all three cases, and P(FAIL_CROSS) is at least 0.999.
  The 15% line is above the copy ceiling, and BIND is zero in expectation.

Seed lock-in mixture on MONO and CROSS:
- Each seed independently locks in with probability pi. Locked seeds have
  MONO 0.85 and CROSS 0.25; unlocked seeds have 0.15 and 0.06.
- P(PASS) is 0.000, 0.031, 0.139, 0.368, 0.728 and 1.000 at pi = 0.1, 0.3,
  0.5, 0.7, 0.9 and 1.0.
- Without the futility rule, P(LOTTERY) is 0.283, 0.634, 0.741, 0.613, 0.271
  and 0.
- With the futility rule, the share stopped after seed 42 is 0.898, 0.687,
  0.482, 0.260, 0.084 and 0.

Futility rule:
- Single seed, P(stop) is 1.000 at a true MONO of 0.25 or below, 0.530 at
  0.28, 0.044 at 0.30 and 0.000 at 0.35 or above.
- It never removes a PASS, because a stopped seed is BELOW, which already
  excludes PASS. When seed 42 is the unlocked seed, it merges LOTTERY into
  FAIL_MONO. That is why the futility verdict is labelled "seed lottery not
  excluded".

Sample size:
- Halving the prompts (250 per B3 cell) changes P(PASS) at CROSS 0.20 and
  seed SD 0.03 from 0.902 to 0.889. Seed variation, not prompt count, sets the
  power. 500 per cell is kept for per-cell reporting at small cost.

Reading:
- With a seed SD of at most 3 points, the rule separates a model 5 points
  above every line from one at the lines (PASS 0.717 against 0.005).
- At a seed SD of 6 points, or a lock-in rate under 0.9, it mostly returns
  LOTTERY. That is the intended reading, because such an instrument cannot
  carry a three-seed arm comparison of about 5 points.

Multiplicity: four lines, each with a pre-registered threshold, combined by
one conjunctive rule. No line is tested twice, and the 200M read is
descriptive.

## Compute caps (D22 counting)

S2 (`compute/cost-model.py`, `compute/cost-model.json`). The base is the
measured 282,501.4 tokens/s (Slurm 359). The training time multiplier is 1.25
central and 1.5 high. The evaluation forward rate is 2.0 x and 1.5 x that
base. Job start-up is 180 or 300 s; compile and autotune 180 or 300 s; a cap
is 1.2 x the high projection, rounded up to a minute.

| Job | Cap (min) | Cap (GPU-h) | Central (GPU-h) |
|---|---:|---:|---:|
| J1 smoke, probe, LR sweep | 34 | 0.567 | 0.345 |
| J2 resume test | 13 | 0.217 | 0.104 |
| J3 conditional LR extension | 18 | 0.300 | 0.161 if run |
| T42 trunk, branch, reads | 133 | 2.217 | 1.474 |
| T43 | 133 | 2.217 | 1.474 |
| T44 | 133 | 2.217 | 1.474 |
| Sum | 464 | 7.733 | 4.871 without J3 |

- Admission: the sum of caps is 7.733 ≤ 8.0 GPU-h. The factors and the
  throughput gate are fixed by this file before J1 runs and are not revisited
  after any measurement (D22).
- If the futility rule stops after T42, the expected use is about 1.92 GPU-h.
- A job that reaches its cap stops. A trunk stopped before 1B tokens gives
  INCOMPLETE for its seed, and that seed counts as UNRESOLVED on every line.
- The gauntlet's own 0.3 GPU-h is reviewer inference and is separate.

## Infrastructure failures and exclusions

- A crash before the first optimizer step is a pre-result: the job is
  resubmitted with the same configuration, and the cap is counted again only
  if a second submission is needed. At most one resubmission per job;
  otherwise INCOMPLETE.
- After a crash during training, a fresh job resumes from the last atomic
  checkpoint (at most two resumes per trunk, inside the same cap).
- Divergence: a non-finite loss, or a loss more than 0.5 nats above its
  1,000-step moving average for more than 1,000 steps. The run restarts once
  from the last checkpoint before the event, with the same data order. A
  second divergence marks the seed DIVERGED, and it counts as BELOW on every
  line. This is conservative and prevents dropping an inconvenient seed. It
  is disclosed.
- A smoke failure stops the registration before any trunk. A fix is a code
  change reviewed under D7; whether it is material is decided before
  re-running (a material change is a new experiment id).
- No job is submitted while a Q2 S1a VM or GPU job runs or is pending.

## Data rights

- Training sources:
  - FineWeb and FineWeb-2: ODC-By 1.0, with Common Crawl terms of use.
  - ParaDocs: Apache-2.0 packaging. The underlying ParaCrawl, News Commentary
    and Europarl texts keep their own terms.
  - The ParaCrawl Bonus release: CC0 for the packaging.
  - SCB-MT-EN-TH-2020: CC BY-SA 4.0.
- Instrument: NTREX-128, CC BY-SA 4.0; FLORES+ is also CC BY-SA 4.0 but
  gated.
- Excluded: TED2020 (D4) and General Translation customer data.
- The public repository receives ids, offsets, hashes, metrics, configs and
  per-example predictions, but no source text. Prompt text, if ever
  released, goes out under CC BY-SA 4.0 with attribution, as a separate
  artifact.
- Model checkpoints stay on the host or in the private archive. Releasing
  them is a separate decision.
- The 2610.06750 code repository has no licence (GitHub API, 2026-10-10), so
  the probe's auxiliary pass is reimplemented from the paper and never
  vendored.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: the cpu-doctor node's reach test
   on the real module graph, the cached-versus-uncached evaluator check, the
   state-cut equivalence check, the B1 positive control (I1), and the CUT and
   ABLATION checks each catch a different class of bug.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot with its
   version history in the bundle; OpenReview items are labelled abstract-only.
3. Hallucinated experimental result: no number in this file is a result. S1,
   S2 and S3 are labelled simulations, estimates and a stand-in check, with
   their scripts and outputs.
4. Shortcut reliance: the copy floor (12.5%) is named, and BIND tests binding
   against it. Surface-disjoint keys block string matching, and B3 blocks
   attention relay by construction.
5. Bug reframed as insight: an I1 failure gives INSTRUMENT_INVALID, not a
   finding about the state.
6. Methodology fabrication: every procedure names its code path and is
   checked against the harness at the pre-freeze audit.
7. Frame-lock: the likely outcomes are stated in advance (below). FAIL_CROSS
   and INCONCLUSIVE are acceptable results.

## Owner's prior forecast (not a decision input)

- P(INSTRUMENT_INVALID) about 0.05.
- P(FAIL_MONO, including futility) about 0.2.
- P(LOTTERY) about 0.15.
- P(FAIL_CROSS) about 0.4, more likely "representational" than
  "state-specific".
- P(INCONCLUSIVE) about 0.1.
- P(PASS) about 0.1.

The most likely verdict is FAIL_CROSS. The literature sets low priors for
cross-lingual transfer at this scale: cross-lingual knowledge transfer under
activation alignment at 360M (2609.19291), and the first translation without
token overlap at about 11B tokens at 1.7B (2604.17633). It also shows that
small models can align across scripts under coherent code-switching
(2609.30535).

## Freeze procedure

After the prerequisites and a fresh pre-freeze audit, and after Kevin accepts
the design decisions:

```bash
uv run python scripts/preregister.py freeze e7-equivariant-writes-g1-v1 program/preregistrations/e7-equivariant-writes-g1-v1.md
uv run python scripts/preregister.py verify e7-equivariant-writes-g1-v1
```

## Design decisions (for the owner's acceptance)

1. Scope: G1 only; phase-1 arms and the P-GSM confirmation are out of scope.
2. The state-necessary bin B3 (d ≥ 1,600) replaces "more than 512 tokens
   back"; B1 and B2 are reported.
3. Seeds [42, 43, 44] with per-seed classification and the majority rule (at
   least two ABOVE, none BELOW).
4. A LOTTERY verdict for seed splits across a line.
5. The futility stop after seed 42 at a MONO upper bound under 0.30.
6. Training context 4,096 at batch 8, the same tokens per step as measured.
7. The A0 layer layout, GDN settings and MLP exactly as in the measured
   module; SWA-512 with RoPE and no sinks.
8. Test languages En, De, Zh and Th; Spanish dropped.
9. NTREX-128 as the instrument source unless Kevin accepts the FLORES+ terms
   before freeze.
10. Key sentences with digits excluded; codes from a reserved set of 2,000.
11. The surface filter at the token, digit-string and four-character-subword
    level, against all eight keys.
12. 500 prompts per cell in B3 and 250 in B1 and B2; a minimum of 150 per
    cell.
13. Equal cell weights in pooled lines.
14. The binding guard BIND (> 0) added to the dossier's CROSS line, which is
    kept at 0.15 EM; the CUT and ABLATION identification checks.
15. The instrument positive control I1 at 0.80 on B1 monolingual.
16. X1 as a descriptive sub-label of FAIL_CROSS only.
17. The 90% sentence-cluster bootstrap with B = 2,000 for every line.
18. The 32K Unigram tokenizer trained on the four languages, digits split.
19. Mixture shares within the 75% monolingual part: En 30, De 15, Zh 15,
    Th 15.
20. The prefix-sharing bitext presentation (c + a and c + b, c in either
    language).
21. The curriculum's fact counts, distance mixture and same-language rule.
22. The LR grid {6e-4, 1.2e-3, 2.4e-3}, selection on held-out LM loss, and
    one conditional edge extension.
23. The warmup-stable-decay trunk with a 20% (1 - sqrt) decay and the 200M
    branch from 160M.
24. The step-overhead probe as non-gating.
25. The throughput gate at 179,329 tokens/s.
26. The cap factor 1.2 and the S2 assumptions.
27. The divergence rule (one restart, then DIVERGED counts as BELOW).
28. The read list as the complete set of sealed-manifest reads.
29. The diagnostics list, all descriptive.
30. The data sources, with the ParaCrawl Bonus en-zh release and SCB-MT for
    Thai.
31. Deduplication by exact match and MinHash on character 5-grams at Jaccard
    0.5, applied to the training streams.
32. The 2610.06750 auxiliary pass reimplemented, never vendored.
