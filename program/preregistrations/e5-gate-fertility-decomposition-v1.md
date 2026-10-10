# E5 first step v1: is the cost of re-segmented English carried by the per-token decay clock in attention-free delta-rule models? (e5-gate-fertility-decomposition-v1)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single synthesis owner of the E5 research gauntlet (D67) on branch
`gauntlet/e5-d20`. It registers only E5's first step, the language-free
decomposition on English. Translation work of any kind (the dossier's
16-language run, Common Crawl partialling, probe QA) is out of scope and needs
its own gauntlet. The design decisions at the end (1 to 27) need the program
owner's acceptance; decision 1 (the GDN subject's data rights) is a ruling only
Kevin can make. Registered caps sum to 4.0 GPU-h (D22 counting), under the
8 GPU-h line. No host job of any kind runs while a Q2 S1a VM or GPU job is
running or pending. The gauntlet proposal that argues and attacks this design
is `program/proposals/2026-10-10-e5-gate-fertility-decomposition.md`; its
evidence bundle is
`program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/`.

## Relation to the dossier and to D67

- Source: dossier entry `E5-d20-semantic-clock-gate-parity`
  (`program/evidence/2026-10-06/question-dossier.md`, section 13), first
  experiment and kill criteria.
- Kept: the two subjects (pure GDN-1.3B at 930ed6ae, RWKV-7 1.5B World at
  004140ba, subject to design decision 1), English episodes of K facts with
  4-digit codes, distractor text and a query, fertility f in {1.0, 1.5, 2.0, 2.7}
  by a frozen splitting rule, loads K in {1, 4, 16}, an elapsed-only filler
  control, an identity hook check first, BPB per f, and the line of
  3 points per unit of log fertility.
- Changed, with the reason in the proposal's mechanism table (M1 to M14):
  1. The primary decay intervention is a per-token decay clamp that holds the
     decay mediator at its canonical value, not the uniform halving r = 2. The
     halving rescales the decay of every write, so it moves interference too;
     in simulation S1 it reads the wrong sign in a world where the decay clock
     carries a quarter of the cost (`compute/mech-sim.json`, world W3). r = 2
     stays as a secondary arm.
  2. The primary statistic is a paired simple effect at one fertility
     (clamp minus native), not a slope of an r x f interaction on the
     exact-match scale, which a monotone rescaling of the outcome can remove.
  3. Only the retention passage is re-segmented. Facts, query and codes keep
     their canonical tokens, and recall is scored by forced choice among four
     codes; greedy exact match is secondary. Base checkpoints given
     non-canonical text tend to copy the odd surface form instead of
     answering (arXiv 2506.19004).
  4. The kill and fund branches are restated: a positive result cannot fund
     the 16-language run on these subjects (GDN-1.3B was trained on English
     FineWeb-Edu only; the RWKV World card lists no high-fertility language).
  5. 600 episodes per cell becomes 1,500 per primary load, set by S2.

## Question

On two frozen attention-free language models whose only memory is a
fixed-size recurrent state updated by a gated delta rule, when the same English
retention passage is re-tokenized into f times as many tokens, how much of the
resulting change in forced-choice recall of facts stored before the passage is
carried by the extra per-token decay mass (the per-token decay clock), and how
much by everything else (the extra writes and erasures, the short convolution
or token shift, and the unfamiliar segmentation)?

The variable is the retention passage's tokenization (canonical, re-segmented
at f, boundary-perturbed at f = 1, or lengthened with canonical text), crossed
with the decay pathway (native or clamped to canonical) and the load K.

## Identity

| Item | Value |
|---|---|
| Experiment id | `e5-gate-fertility-decomposition-v1` |
| Code revision | the commit that adds the harness and the CPU doctor (recorded at freeze) |
| Subject G (GDN) | `m-a-p/1.3B-100B-GatedDeltaNet-pure` at `930ed6ae4ac629c86cb9855bb3dcb0a0974a29aa` (24 layers, 8 heads, head dim 256, short conv 4, fp32 shards 5,865,376,000 B, shard SHA-256 `9c0e888e...562c` and `b89b26e2...0bef`); fallback under decision 1: `linear-moe-hub/Gated-Deltanet-1.3B` at `871079371adab842ea82efc56d9c303c45460eee` (apache-2.0, 4 heads, no short conv, SlimPajama) |
| Subject R (RWKV-7) | `fla-hub/rwkv7-1.5B-world` at `004140baad7a62d49a26d97508ef19cf09672328` (apache-2.0; registered `rwkv7-1.5b-world`, receipt on the host) |
| Tokenizers | G: `tokenizer.json` SHA-256 `1d5b9634c23bdd4540f633d327120e1fa4b57a2a723a56d7a92debfc4d15c061` (git blob `b667161b...`, equal to the HF tree oid); R: `rwkv_vocab_v20230424.txt` SHA-256 `e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89`, parsed with `ast.literal_eval` (the upstream loader's `eval` is not used) |
| Image | `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9` (build 855 from ed5d5a93; fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0) |
| Estimator | `compute/estimator.py` of the evidence bundle, copied unchanged into the harness; its SHA-256 recorded at freeze |
| Seeds | `[42, 43, 44]`: each seed builds a disjoint block of 125 passages and 500 episodes per primary load; derived seeds for every random choice are the first 8 bytes of SHA-256 of `[seed, block, episode id, cell, purpose]`; bootstrap seed 42 |

## Prerequisites before freeze (no GPU)

1. Kevin's ruling on subject G's data rights (decision 1).
2. A registry entry for subject G and a CPU-lane fetch with a full receipt
   (`scripts/fetch_open_model.py`, `fetch-model-cpu.sbatch`), under D1, when no
   S1a job is running. The rwkv7 registry blocker text is updated (the receipt
   exists; the custom tokenizer is vendored).
3. The RWKV World tokenizer vendored into the harness with
   `ast.literal_eval` and the vocab SHA-256 pinned.
4. The episode builder (CPU): WikiText-103 raw download under D1 with SHA-256,
   the frozen normalizer, passages, noun-phrase lists, codes, templates, and
   the rules R(f, seed), B(seed) and FILL as code, with decode-identity tests.
   The S4 prototype (`compute/resegment.py`) is the reference implementation.
5. The harness: model loop on fla 0.5.2, hooks (clamp, r = 2, write
   silencing), forced-choice scoring from the cached recurrent state, greedy
   decode, BPB, gate ledger, write-overlap mass, checkpoint and resume keyed by
   (episode, cell).
6. A new versioned CPU doctor, run as an orx `cpu-doctor` node: unit cases for
   `estimator.py`, S1's six worlds re-run through the harness's estimator and
   decision code, decision semantics, decode identity of R and B on the frozen
   passages. The legacy doctor is not edited.
7. Manifests for the smoke and the two main jobs, a dry run and a test-only
   submission (host actions, after the host rule allows).

## Data

- **Retention passages.** WikiText-103 raw v1 (Salesforce/wikitext at
  `b08601e04326c79dfdd32d625aee71d232d685c3`, CC BY-SA 3.0 and GFDL),
  validation and test splits, heading lines removed, normalizer frozen
  (" @-@ " to "-", " @,@ " to ",", " @.@ " to ".", no space before
  , . ; : ? ! ' or ) and none after (). 375 passages from distinct articles
  where possible, each cut at a word boundary to exactly 512 canonical tokens
  of subject G's tokenizer (the same text has about 465 tokens on subject R's;
  f is always measured on the subject's own tokenizer). A passage is the
  cluster for every statistic. Passage text stays off the public repository
  (ids, offsets and SHA-256 only).
- **Lead-in.** 24 canonical tokens from a different article, never
  re-segmented.
- **Facts.** "the {adjective} {noun}" keys from project-written lists (60
  adjectives, 120 nouns; no key string occurs in any passage), three templates
  assigned per episode ("The code for the X is NNNN." / "The X has the code
  NNNN." / "Remember that the code of the X is NNNN."), each with its matched
  query ending in "is" or "code". Codes are uniform in 1000-9999, distinct
  within an episode, pairwise Hamming distance at least 2. The K facts appear
  in random order after the lead-in; the target is uniform over them.
- **Candidates.** The target code plus three foils: for K of at least 4,
  three other codes bound in the same episode; for K = 1, three fresh codes
  absent from the episode. Each candidate is the canonical tokenization of
  " NNNN" in context (subject G: "▁" then four digits, 5 tokens; subject R:
  " NN" then "NN", 2 tokens; checked in S4 for six codes).
- **Episode layout.** lead-in, facts, retention passage (in the cell's
  tokenization), query. Longest registered episode about 1,736 tokens (K = 16
  at f = 2.7), under the 1,900 limit kept below subject G's configured 2,048
  (its release paper states a 4,096-token training window; the smaller is
  assumed).

## Re-segmentation rules (frozen as code)

- **R(f, seed), refinement.** Every canonical token of the retention passage
  is split into one or more in-vocabulary pieces (byte-fallback pieces
  excluded on subject G), adding one internal boundary at a time, chosen
  uniformly among all (token, boundary) moves that keep every piece in the
  vocabulary, until the passage has round(f x N) pieces. Splits occur only at
  character boundaries. The output must decode to the canonical bytes. S4 on
  11 stand-in passages: f = 2.7 reached with no shortfall on both tokenizers;
  share of canonical tokens split 0.71 (G) and 0.71 (R); single-token
  retention over words 0.10 (G) and 0.11 (R); maximum reachable f 4.3 to 5.8.
- **B(seed), boundary only.** Adjacent canonical tokens inside one
  whitespace word are re-bounded at a different split point where both new
  pieces are in the vocabulary; token count unchanged (f = 1 exactly). S4: 12%
  (G) and 8% (R) of tokens re-bounded. This arm is weak by construction and is
  read only as a boundary-step estimate, never as a decision input.
- **FILL(f).** The canonical passage is extended with the next canonical
  tokens of the same article until its length equals the token count of
  R(f) on that subject (Lee et al.'s elapsed-context arm, matched to f).

## Cells

Paired design: every cell of an episode reuses the same facts, codes, target,
passage and lead-in. n is per load.

| Cell | Passage tokenization | Decay pathway | Loads (n) | Tier |
|---|---|---|---|---|
| CAN | canonical | native | 1, 4 (1,500); 16 (500) | primary |
| NAT(f), f in {1.5, 2.0, 2.7} | R(f) | native | 1, 4 (1,500); 16 at 2.7 (500) | primary |
| CLAMP(f), f in {1.5, 2.0, 2.7} | R(f) | clamped to CAN | 1, 4 (1,500); 16 at 2.7 (500) | primary |
| BND | B | native | 1, 4 (1,500) | primary (descriptive) |
| ZERO | none (query right after the facts) | native | 1, 4 (1,500); 16 (500) | primary (read check) |
| FILL(f), f in {1.5, 2.0, 2.7} | canonical, lengthened | native | 4 (500) | ladder 2 |
| SIL(1), SIL(2.7), SIL-CLAMP(2.7) | canonical / R(2.7) with writes silenced on the passage | native / clamped | 4 (500) | ladder 5 |
| R2(1), R2(2.7) | canonical / R(2.7) | every log-decay halved (r = 2) | 4 (500) | ladder 6 |
| FACT(2.0), BOTH(2.0) | facts re-segmented by R(2.0) (codes never) / facts and passage | native | 4 (500) | ladder 4 |
| BPB subset | CAN, NAT(f), BND with full logits on the passage | native | 4 (200) | ladder 1 |

The 500-episode cells use the first 500 episodes of the corresponding load
(seed 42's block, then seed 43's), so they pair with CAN and NAT.

## Interventions

- **Decay clamp (both subjects).** For each canonical token u of the passage,
  each layer l and each head h (subject G) or channel (subject R): the target
  is the log-decay that u received in the CAN run of the same episode, G_c;
  the native value is the sum of the live log-decays of u's pieces in the
  re-segmented run, G_r; each piece's log-decay is multiplied by
  c = G_c / G_r. The clamp is applied layer by layer during the forward pass,
  so the live values at layer l already include the clamp at lower layers.
  Subject G: g = -exp(A_log) softplus(a + dt_bias) is computed inside the
  fla 0.5.2 kernel from the a_proj output, so a forward hook on a_proj
  replaces a with softplus^-1(c softplus(a + dt_bias)) - dt_bias (exact).
  Subject R: w = -0.6065306597 sigmoid(z), z the w_lora output; the hook sets
  z' = logit(c sigmoid(z)). Where c sigmoid(z) would reach 1, the piece is
  saturated at 1 - 1e-6 and the unmatched mass is moved to the token's other
  pieces (two passes); the remainder is reported (gate I5). At f = 1 the
  clamp is the identity.
- **r = 2.** Subject G: A_log replaced by A_log - ln 2 (exact). Subject R:
  hook z' = logit(sigmoid(z) / 2). Every position, every layer.
- **Write silencing (SIL).** Subject G: b_proj output set to -30 on passage
  positions (beta about 1e-13: no write and no delta-rule erase). Subject R:
  on passage positions the value write and the in-context removal term are
  zeroed (v_proj output 0, v_lora and a_lora pre-activations -30). Decay
  stays native, or clamped in SIL-CLAMP.

## Readouts

- **Primary.** Forced-choice correctness Y in {0, 100}: the candidate whose
  canonical token string has the largest summed log-probability given the
  episode, scored from the recurrent state cached at the end of the query
  (four continuations from one prefix pass).
- **Secondary.** Target forced-choice log-probability l (log-softmax of the
  four string log-probabilities); greedy exact match (6 greedy tokens on
  subject G, 3 on subject R; correct if the first 4-digit run equals the
  target); target logit margin.
- **Mechanism ledgers (from the CLAMP passes).** R_F(u, l, h) = G_r / G_c per
  split token; write-overlap mass sum over passage positions of
  beta_t (k_t . k*)^2, with k* the target fact's write key (subject G; the
  analogous removal-weighted overlap on subject R); BPB of the passage per f
  on the 200-episode subset.

## Stages

### Smoke (cap 0.25 GPU-h, one GPU, both subjects in sequence)

Load each model in the image with `output_loading_info`: missing keys empty;
unexpected keys only subject G's 24 `attn.D` tensors, each verified all zero
(the asset cell range-read all 192 values as 0.0). Gates I1, I2 or I2b, I3,
I7 on 200 K = 4 episodes of seed 42 (not reused in analysis), a kill-and-resume
test on 40 episodes, a throughput measurement per subject on 64 full episodes
of every cell type, and a Slurm dry run of both main manifests.

### Main jobs (one GPU each; caps 1.25 GPU-h for subject G, 2.5 for subject R)

Batches of episodes run every cell for those episodes (CAN first, so CLAMP
has its targets). Results are written every 5 minutes keyed by
(episode, cell). In the first 10 minutes each job projects its total time from
measured throughput; if the projection exceeds the cap, ladder tiers are
dropped in order 1, 2, 3 (K = 16), 4, 5, 6 until it fits; if the primary cells
and gates alone exceed the cap, the job stops and the subject is INFEASIBLE
(throughput floors: about 11,800 tok/s for subject G and 5,200 for subject R,
`compute/cost-model.json`). Primary cells are never cut.

## Instrument gates

| Gate | Pass condition | On failure |
|---|---|---|
| I1 hook identity | clamp hooks active with c = 1 versus unhooked, 200 episodes: decisions identical on at least 199, median abs difference in l at most 0.01 | subject INVALID |
| I2 r = 2 two ways (G) | weight edit versus a_proj hook with c = 0.5: decisions agree on at least 199 of 200, max abs difference in l at most 0.02 | subject INVALID |
| I2b reference recurrence (R) | 4 episodes x 64 tokens: chunk kernel versus a pure-torch recurrence on captured r, w, k, v, a, kk; max relative error at most 1e-2 | subject INVALID |
| I3 padding | padded versus unpadded batches: decisions identical on at least 199 of 200, median abs difference in l at most 0.01 | subject INVALID |
| I4 floors | canonical K = 4 accuracy at least 50; primary f is the largest of 2.7, 2.0, 1.5 whose native K = 4 accuracy is at least 30 | no admissible f: subject INVALID |
| I5 clamp completeness (R) | unmatched log-decay mass at most 1% of the passage's total | 1 to 5%: reading stands, flagged; above 5%: subject INVALID |
| I6 decode identity | every re-segmented sequence decodes to the canonical bytes | episode regenerated with the next derived seed (logged) |
| I7 loader sanity | canonical WikiText-103 test perplexity at most 40 on 100 passages | subject INVALID |

## Primary estimand and decision rules

Per subject s, with f_p from I4 and Y in points:

- beta_s = mean over K in {1, 4} of NIE_s(K, f_p) / ln f_p, where
  NIE_s(K, f) = mean over episodes of Y(CLAMP f) - Y(NAT f). NIE(K, 1) = 0 by
  construction, so beta_s is the secant from f = 1 in the dossier's unit.
- TE_s = mean over K in {1, 4} of [Y(CAN) - Y(NAT f_p)] / ln f_p.
- Intervals: 90% percentile cluster bootstrap over passages, B = 2,000,
  seed 42 (`estimator.cluster_bootstrap_mean`).

Reading per subject, in order:

1. Any of I1, I2 or I2b, I3, I5 (above 5%), I7 fails, or I4 admits no f: INVALID.
2. Upper end of TE_s below 3: NO_COST (there is no fertility cost to decompose).
3. Upper end of beta_s below 3: KILL.
4. beta_s at least 3 and its lower end above 0: MATERIAL.
5. Otherwise INCONCLUSIVE.

Overall (`estimator.decide_overall`): INVALID if either subject is INVALID;
KILL if both are KILL or NO_COST (KILL_NO_COST if both NO_COST); MATERIAL if
both MATERIAL; SPLIT if one is MATERIAL and the other KILL or NO_COST;
otherwise INCONCLUSIVE.

Consequences, fixed now:

- **KILL or KILL_NO_COST.** The phase-1 span-parity loss is killed without
  any translation work, and D20 is closed citing this result with
  arXiv 2609.33093 and 2609.16183.
- **MATERIAL.** A successor gauntlet may design a translation-paired leg on
  an attention-free subject pretrained on the target languages; neither
  registered subject qualifies, so this result funds nothing by itself.
- **SPLIT.** A subject-specific result (scalar per-head decay against
  per-channel decay with in-context removal); no portable claim.
- **INCONCLUSIVE.** Reported with intervals; no second block without a new
  registration.
- **INVALID.** No claim; the probe or the hooks need repair under a new id.

## Reported regardless of outcome

1. NIE and TE per load (1, 4, 16) at every f, with intervals; the
   through-origin slope over f; the same on the l and exact-match scales.
2. The decay share NIE / TE with a ratio-bootstrap interval, undefined when
   the TE interval includes 0.
3. The boundary step Y(CAN) - Y(BND).
4. FILL: Y(CAN) - Y(FILL f) on both subjects (the elapsed-context arm of
   arXiv 2609.33093, which measured only its 340M models), and the canonical
   extra-token count whose cost equals NAT(f)'s, by interpolation.
5. SIL: the decay-only reference Y(SIL 1) - Y(SIL 2.7) and SIL-CLAMP.
6. r = 2: G(1), G(2.7) and dG = G(2.7) - G(1), set beside NIE.
7. FACT and BOTH at f = 2.0 against NAT(2.0) and CAN.
8. ZERO per load (encoding baseline).
9. R_F per layer and head (G) or channel group (R), at every f; write-overlap
   mass per f; BPB per f; STRR and share of tokens split per f.
10. Per-seed estimates of beta and TE.
11. All infrastructure events, regenerated episodes and dropped ladder tiers.

## Predictions (falsifiable, stated before data)

- P1 (ledger): the median R_F over split tokens, pooled over layers and
  heads, at f = 2.7 is above 1.5 on both subjects (the gates do not
  self-normalize to canonical tokens). Falsified by a median at or below 1.5;
  a median within 0.85 to 1.15 means NIE is about 0 by construction.
- P2 (primary): KILL on both subjects.
- P3: TE_s is at least 10 points per log-f unit on both subjects.
- P4: Y(CAN) - Y(FILL 2.7) is smaller than Y(CAN) - Y(NAT 2.7) on both
  subjects (re-segmentation costs more than the same number of extra
  canonical tokens).
- P5: dG from r = 2 and NIE at f = 2.7 differ by more than their combined
  90% intervals on at least one subject.

## Statistics, sample sizes and simulation

- **S1 (identification, `compute/mech-sim.py`).** A NumPy gated delta-rule
  memory in six worlds (per-token clock; pure interference; both; null;
  the legacy simulator's duplicates; partial), three seeds x 600 episodes per
  load. The clamp's NIE equals TE in the per-token-clock world (share 1.00)
  and is exactly 0 when gates self-normalize (share 0.00); in the mixed world
  the share is 0.22 to 0.25 and in the partial world 0.15 to 0.17, and the
  registered rule reads MATERIAL, KILL, MATERIAL, MATERIAL and NO_COST (null
  world) in every replicate. The r = 2 contrast dG at K = 4 is -1.2 to -3.3
  points in the pure-interference world (no decay share), -1.5 to -2.2 in the
  mixed world (a quarter of the cost is decay) and -0.7 to +0.8 in the partial
  world, so it reads the wrong sign or nothing where the clamp reads the
  share. Magnitudes are not calibrated to the checkpoints.
- **S2 (power, `compute/power-sim.py`).** Under the paired design only the
  shift and the discordance d = P(Y(CLAMP) != Y(NAT)) set the sampling
  distribution; passage clustering is modelled with c = 4 episodes per passage
  per load and a between-passage SD of the shift of 0 or 2 points. At 1,500
  episodes per load and SD 2: P(KILL | beta = 0) is 1.00, 1.00, 0.98 and 0.91
  at d = 0.05, 0.10, 0.20, 0.30; P(KILL | beta = 3) is 0.05 to 0.11 (the false
  kill rate at the line); P(MATERIAL | beta = 5) is 0.98 to 1.00. At 1,000 per
  load P(KILL | beta = 0, d = 0.30) falls to 0.78, which is why 1,500 is
  registered. The cluster-normal interval used for speed covers at 0.86 to
  0.92 and the registered bootstrap at 0.85 to 0.93 (nominal 0.90; 400
  replicates per setting); their kill decisions agree on 99 to 100% of
  replicates. NO_COST at 1,000 per load: P = 0.99 at TE = 0 and d = 0.1, 0.05
  at TE = 3. The discordance values are assumptions, not measurements.
- **Floors.** With n = 1,000 and a design effect of 1.3 the floor gates
  misclassify with probability under 0.05 when the true accuracy is 3 points
  or more from the floor.
- **S3 (cost, `compute/cost-model.py`).** 3.48e7 tokens per subject
  (2.58e7 primary and gates). Central 0.47 GPU-h (G) and 0.79 (R); high 1.05
  and 2.24, on assumed throughputs (central 40,000 and 20,000 tok/s; high
  20,000 and 8,000). No inference throughput has been measured on this host.
- **Multiplicity.** One primary estimand per subject; the overall reading is
  a fixed conjunction. All secondary quantities are descriptive.
- **Missing data.** An episode lost to an infrastructure failure is rerun
  from its key; if it cannot be, it is dropped from every cell (pairing is
  preserved) and counted; more than 2% dropped on a subject makes that
  subject INCONCLUSIVE at best.

## Compute caps (D22 counting)

Smoke 0.25 + main G 1.25 + main R 2.5 = 4.0 GPU-h, at most 8.0. The caps are
fixed numbers, not a formula; the ladder applies inside them. This is the
experiment's compute, separate from the gauntlet's 0.3 GPU-h reviewer budget.

## Checkpoints and resume

Each main job writes completed (episode, cell) records (decisions, the four
string log-probabilities, l, the greedy string, ledger summaries) every 5
minutes to the persistent run directory. A fresh job skips completed keys and
continues the seeded order. The smoke's kill-and-resume test requires the
resumed records to equal an uninterrupted run's for every completed key
(decisions identical; l within 1e-4).

## Infrastructure failures and exclusions

An infrastructure failure is a job or process failure, an out-of-memory
error, or a node event, never a model output. Failed keys are rerun. No
episode is excluded for its outcome. Regenerated episodes under I6 are logged
with their derived seeds.

## Data rights

- Subject R: apache-2.0 (card; RWKV-7 paper states Apache-2.0 for code and
  models); frozen, not redistributed.
- Subject G: no licence, model card or README at 930ed6ae (HF API,
  2026-10-10); training data documented first-party in arXiv 2507.06457
  (FineWeb-Edu, 100B tokens). Use requires Kevin's ruling (decision 1); under
  either option no weights or derived weights are redistributed and the public
  repository holds aggregate metrics, ids and hashes only. The licensed
  fallback is apache-2.0.
- WikiText-103: CC BY-SA 3.0 and GFDL; text kept on the host and in the
  private archive, not in the public repository.
- Key lists and templates: written by the project (MIT).
- No personal data, no model-generated code executed (outputs are strings
  scored on CPU).

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: I1, I2/I2b, I3 and I6 run on the
   GPU before any analysis; the CPU doctor runs S1's worlds through the
   harness's own estimator.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot; the
   claim registry marks each claim's read status.
3. Hallucinated result: no result exists; S1 to S4 are labelled simulations
   or tokenizer measurements.
4. Shortcut reliance: canonical facts among fragmented text could cue what
   to store; the boundary arm and the ZERO cell bound it, and it is disclosed.
5. Bug reframed as insight: a NIE of the "wrong" sign is checked against I1
   and the SIL arm before any interpretation.
6. Methodology fabrication: every threshold is in `estimator.py`, with its
   operating characteristics in S2.
7. Frame lock: the r = 2 arm and the FILL ladder keep the dossier's and the
   closest prior's framings measurable beside the new one.

## Owner's prior forecast (not a decision input)

KILL 0.55, KILL_NO_COST 0.05, INCONCLUSIVE 0.15, SPLIT 0.05, MATERIAL 0.05,
INVALID or INFEASIBLE 0.15.

## Freeze procedure

After prerequisites 1 to 7 and Kevin's acceptance of the design decisions:
`uv run python scripts/preregister.py freeze e5-gate-fertility-decomposition-v1 program/preregistrations/e5-gate-fertility-decomposition-v1.md`,
then `verify`. Any material change after freeze is a new id.

## Design decisions (for the owner's acceptance)

1. Subject G's data rights: use m-a-p GDN-1.3B (no licence; research
   evaluation only, nothing redistributed) or replace it with the apache-2.0
   linear-moe-hub GDN-1.3B (different data, no short conv, not the closest
   prior's checkpoint). Kevin's ruling.
2. Scope: English only; no translation work.
3. Primary decay intervention: the per-token clamp to the canonical run;
   r = 2 secondary.
4. Primary statistic: the paired simple effect at f_p expressed as a secant
   per log-f unit; line 3 points.
5. Primary loads K in {1, 4} pooled with equal weight; K = 16 secondary.
6. Only the retention passage is re-segmented; facts, query and codes stay
   canonical; codes are never re-segmented in any cell.
7. Forced choice among four codes is primary; greedy exact match secondary.
8. Foils: other bound codes for K at least 4; fresh codes for K = 1.
9. Refinement rule R(f, seed) as in S4; splits at character boundaries only;
   byte-fallback pieces excluded on subject G.
10. Boundary-only arm B as in S4, descriptive only.
11. FILL ladder at K = 4 with n = 500.
12. WikiText-103 validation and test as the passage source, normalizer as
    above; passages of 512 subject-G tokens.
13. n = 1,500 per primary load (3 seeds x 500), 500 for secondary cells.
14. 90% percentile cluster bootstrap over passages, B = 2,000, seed 42.
15. Reading order: INVALID, NO_COST, KILL, MATERIAL, INCONCLUSIVE.
16. Overall conjunction as in `estimator.decide_overall`.
17. Fertility fallback ladder 2.7, 2.0, 1.5 on the native K = 4 floor of 30.
18. Canonical floor 50 at K = 4.
19. Clamp saturation rule on subject R and gate I5 thresholds (1% and 5%).
20. SIL implementation on both subjects as above.
21. Gates I1 to I7 with their tolerances.
22. Caps 0.25, 1.25 and 2.5 GPU-h; ladder order 1 to 6.
23. Episode length limit 1,900 tokens.
24. Three fact templates assigned per episode.
25. Missing-data rule (2%).
26. Consequences of each overall reading, including that MATERIAL funds no
    translation run by itself.
27. Predictions P1 to P5 are descriptive and cannot change the reading.
