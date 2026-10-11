# E5 first step v2: how much of the recall cost of re-segmented English runs through the per-token decay pathway, and how much through its interaction with the extra writes, in attention-free delta-rule models? (e5-gate-fertility-decomposition-v2)

Status: DRAFT. Not frozen, not admitted, no ledger row. Written on 2026-10-10
by the single owner of E5's repair under D68, on branch `gauntlet/e5-d20`,
after gauntlet wave 1 (score 54; all three refuters refuted;
`program/gauntlet/2026-10-10-e5-gate-fertility-decomposition.jsonl`, row 1).
It supersedes `e5-gate-fertility-decomposition-v1` (DRAFT, left unedited under
the gauntlet's rule 3) and registers only E5's first step, the language-free
decomposition on English. Translation work of any kind is out of scope. The
design decisions at the end (1 to 30) need the program owner's acceptance;
decision 1 (the GDN subject's data rights) is a ruling only Kevin can make.
Registered caps sum to 6.25 GPU-h (D22 counting), under the 8 GPU-h line. No
host job of any kind runs while a Q2 job is running or pending. The gauntlet
proposal that argues and attacks this design is
`program/proposals/2026-10-10-e5-gate-fertility-decomposition.md`; its
evidence bundle is
`program/proposals/evidence/2026-10-10-e5-gate-fertility-decomposition/`, and
this version's CPU evidence is in its `compute/repair-d68/`.

## What changed from v1, and why

Each change answers a defect named in wave 1 (the record's `largest_defect`,
the refuters and both reviews).

1. **K = 1 is gone; one primary load, chosen for sensitivity on held-out
   episodes.** v1 pooled K = 1 and K = 4 with equal weight. At K = 1 the three
   foils were fresh codes absent from the episode, so recall was a presence
   test at ceiling in every arm, NIE(K = 1) was about 0 by construction, and a
   true K = 4 decay secant at the line read KILL with probability 0.954, 0.792
   and 0.655 at discordance 0.1, 0.2 and 0.3 (reproduced with v1's own
   estimator in S2v2). v2 has a single primary load K_p, the smallest K in
   (4, 8, 16) whose canonical accuracy on held-out smoke episodes is at most 90
   (the ceiling gate) and at least 50. All four candidates are always codes
   bound in the same episode. The fertility is the first f in (2.7, 2.0) whose
   held-out native accuracy at K_p is at least 30 (chance plus 5; its only job
   is to keep NAT off chance). f = 1.5 is dropped (power). A native floor of
   40 was tried first in the repair and dropped: S1v2 showed it refuses
   exactly the erase-dominated operating points where the factorial reads
   MASKED, and with PNIE co-primary a low NAT no longer biases the reading
   toward KILL.
   The selection never reads an analysis episode, so it cannot depend on the
   contrasts it gates.
2. **A 2 x 2 factorial separates pure decay from the decay-by-write
   interaction.** v1's clamp contrast is a noising estimate of a natural
   indirect effect and equals the pure indirect effect plus an interaction term
   (arXiv 2606.27510, Prop. 3.1); in v1's own simulation worlds the pure decay
   cost at canonical writes was 16 to 45 points against a clamp contrast of 8
   to 14. v2 adds the denoising arm DEC (canonical tokens carrying the
   re-segmented run's per-token decay mass), so the clamp's contrast (TNIE),
   the pure decay contrast (PNIE) and their difference (INT) are all estimated
   on the same episodes, and TE = PNIE + PNDE + INT holds exactly per episode.
   The "decay share" language is dropped.
3. **The kill needs both decay contrasts below the line and the gates not
   self-normalising.** KILL requires the upper ends of both TNIE and PNIE below
   the line and a median R_F of at least 1.5. A material PNIE with a TNIE below
   the line reads MASKED; a median R_F below 1.5 reads SELF_NORMALIZED (both
   decay contrasts are then near the identity, and the step does not test
   whether excess decay mass costs recall).
4. **The line is stated in calibrated units.** Under the high-threshold model
   of four-alternative forced choice an exact-match effect of x points appears
   as 0.75x forced-choice points, so raw forced-choice differences are divided
   by 0.75. The line is 3 points per log-f unit on that corrected scale (the
   dossier's exact-match unit), which is 2.25 raw forced-choice points. This is
   a stricter kill than v1's 3 raw points.
5. **Article-level clustering with a larger, cluster-rich passage supply.**
   WikiText-103 validation and test hold only 120 articles. v2 draws passages
   from the train split, one passage per article, so the article is the
   cluster, and uses 2,000 articles (8,000 episodes) at f_p = 2.7 or 3,000
   (12,000 episodes) at f_p = 2.0, fixed by f_p before any analysis episode
   runs.
6. **The registered interval is the one the simulations use.** The decision
   interval is the cluster-robust normal interval in `estimator_v2.py`; S1v2
   and S2v2 call that code. The percentile cluster bootstrap is reported
   beside it, and S2v2 checks coverage and decision agreement.
7. **Write-drift ledger, a positive control at c not equal to 1, and a
   piece-sum check.** The clamp and the transplant are applied layer by layer,
   so writes at higher layers respond; the ledger reports how far. I2 tests
   the hook against a weight edit at c = 0.5 and c = 2. I8 recomputes every
   clamped and transplanted per-token sum.
8. **Secondary arms keep every framing measurable**: the write-silenced pair
   (SIL-NAT, SIL-CLAMP), a uniform per-token-clock dose (DOSE), a
   last-piece distribution of the clamp (CLAMP-LAST), the elapsed-context
   ladder (FILL), the dossier's uniform halving (R2), boundary-only (BND) and
   no-passage (ZERO) cells.

## Question

On two frozen attention-free language models whose only memory is a
fixed-size recurrent state updated by a gated delta rule, when the same English
retention passage is re-tokenized into f times as many tokens, how much
forced-choice recall of facts stored before the passage is lost, and how much
of that loss runs through the per-token decay pathway at canonical writes, at
the re-segmented writes, and through the interaction of decay with the extra
writes?

## What the primary estimand identifies

Four paired arms at (K_p, f_p), with W the passage's tokens (canonical W0 or
re-segmented W1) and D the per-canonical-token decay mass at every layer and
head (subject G) or channel (subject R) (canonical D0, or the summed piece
decay of the re-segmented run D1): CAN = Y(W0, D0), DEC = Y(W0, D1),
CLAMP = Y(W1, D0), NAT = Y(W1, D1).

- **TNIE = CLAMP - NAT** (primary, governs the phase-1 loss) is the change in
  recall from restoring every canonical token's summed log-decay to its
  canonical value while the passage keeps its re-segmented tokens, with every
  downstream quantity, including the writes and decays of higher layers, free
  to respond. It is the oracle, inference-time benefit of per-canonical-token
  decay parity at the writes re-segmentation produces: the most a span-parity
  loss on forgetting mass could recover on this text if its only effect were
  to equalise decay mass. It is a noising estimate and contains the
  decay-by-write interaction.
- **PNIE = CAN - DEC** (co-primary, governs the mechanism claim) is the recall
  cost of the re-segmentation's extra decay mass when the writes are
  canonical: the denoising estimate, the pure indirect effect through decay.
- **INT = TNIE - PNIE** is the decay-by-write interaction. A negative INT
  means the extra writes and erasures of the re-segmented passage have already
  removed part of what restoring decay would save.
- **PNDE = CAN - CLAMP** is the re-segmentation effect at canonical decay mass
  (writes, erasures, convolution or token shift, unfamiliar segmentation).
- TE = CAN - NAT = PNIE + PNDE + INT exactly, per episode.

What none of them identifies: a unique "share" of the cost due to decay (with
INT not 0 no such share exists); the effect of a trained parity loss (training
would change the writes too); transfer to natural high-fertility text, whose
gates may self-normalise differently (R_F is measured on fragments only). The
"decay pathway" is a different object on the two subjects (scalar per-head
decay; per-channel decay coupled to in-context removal), so subject readings
are not pooled.

## Identity

| Item | Value |
|---|---|
| Experiment id | `e5-gate-fertility-decomposition-v2` |
| Code revision | the commit that adds the harness and the CPU doctor (recorded at freeze) |
| Subject G (GDN) | `m-a-p/1.3B-100B-GatedDeltaNet-pure` at `930ed6ae4ac629c86cb9855bb3dcb0a0974a29aa` (24 layers, 8 heads, head dim 256, short conv 4, fp32 shards 5,865,376,000 B, shard SHA-256 `9c0e888e...562c` and `b89b26e2...0bef`); fallback under decision 1: `linear-moe-hub/Gated-Deltanet-1.3B` at `871079371adab842ea82efc56d9c303c45460eee` (apache-2.0, 4 heads, no short conv, SlimPajama) |
| Subject R (RWKV-7) | `fla-hub/rwkv7-1.5B-world` at `004140baad7a62d49a26d97508ef19cf09672328` (apache-2.0; registered `rwkv7-1.5b-world`, receipt on the host; `models/registry.yaml` still records `trust_remote_code: true` and a vendoring blocker, cleared by prerequisite 2) |
| Tokenizers | G: `tokenizer.json` SHA-256 `1d5b9634c23bdd4540f633d327120e1fa4b57a2a723a56d7a92debfc4d15c061`; R: `rwkv_vocab_v20230424.txt` SHA-256 `e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89`, parsed with `ast.literal_eval` |
| Image | `127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9` (build 855 from ed5d5a93; fla and fla-core 0.5.2, torch 2.11.0, transformers 5.15.0) |
| Estimator | `compute/repair-d68/estimator_v2.py` of the evidence bundle, copied unchanged into the harness; its SHA-256 recorded at freeze |
| Seeds | `[42, 43, 44]`: each seed builds a disjoint third of the articles; derived seeds for every random choice are the first 8 bytes of SHA-256 of `[seed, article id, episode id, cell, purpose]` |

## Prerequisites before freeze (no GPU)

1. Kevin's ruling on subject G's data rights (decision 1).
2. A registry entry for subject G and a CPU-lane fetch with a full receipt,
   under D1, when no Q2 job is running; the rwkv7 registry entry updated
   (`trust_remote_code: false`, tokenizer vendored, blocker cleared).
3. The RWKV World tokenizer vendored with `ast.literal_eval` and the vocab
   SHA-256 pinned.
4. The episode builder (CPU): WikiText-103 raw train split under D1 with
   SHA-256, the frozen normalizer, one passage per article, noun-phrase lists,
   codes, templates, the rules R(f, seed), B(seed) and FILL as code, with
   decode-identity tests (`compute/resegment.py` is the reference).
5. The harness: fla 0.5.2 model loop; hooks for the clamp, the decay
   transplant, CLAMP-LAST, DOSE, r = 2 and write silencing; forced-choice
   scoring from the cached recurrent state; greedy decode; BPB; R_F, write-drift
   and piece-sum ledgers; checkpoint and resume keyed by (episode, cell).
6. A new versioned CPU doctor run as an orx `cpu-doctor` node: unit cases for
   `estimator_v2.py` (including `select_operating_point` on every branch and
   `decide_subject` on every reading), S1v2's worlds re-run through the
   harness's estimator and decision code, decode identity of R and B. The
   legacy doctor is not edited.
7. Manifests for the smoke and the two main jobs, a dry run and a test-only
   submission (host actions, when the host rule allows).

## Data

- **Retention passages.** WikiText-103 raw v1 (Salesforce/wikitext at
  `b08601e04326c79dfdd32d625aee71d232d685c3`, CC BY-SA 3.0 and GFDL), train
  split, heading lines removed, normalizer as in v1. Articles are drawn by
  seeded sampling among those with at least 1,450 canonical subject-G tokens of
  body text (FILL(2.7) needs about 1,382 contiguous tokens from the passage
  start); one passage of exactly 512 subject-G tokens per article, cut at a
  word boundary. The article is the cluster for every statistic. 50 further
  articles per load (200 episodes) are the held-out operating-point set; they
  are never analysed. Passage text stays off the public repository (ids,
  offsets and SHA-256 only).
- **Lead-in, facts, templates, codes** as in v1: 24 canonical lead-in tokens
  from a different article; keys "the {adjective} {noun}" from project lists
  (no key string occurs in any passage); three templates assigned per episode;
  codes uniform in 1000-9999, distinct within an episode, pairwise Hamming
  distance at least 2.
- **Candidates.** The target code plus three other codes bound in the same
  episode (K_p is at least 4). Each candidate is the canonical tokenization of
  " NNNN" in context. Codes are never re-segmented in any cell.
- **Episode layout.** Lead-in, facts, retention passage in the cell's
  tokenization, query. Four episodes per article, each with its own facts,
  codes and target. The longest registered episode is about 1,736 tokens
  (FILL(2.7) at K = 16), under the 1,900 limit.

## Re-segmentation rules (frozen as code)

As in v1: R(f, seed) refines canonical passage tokens into in-vocabulary
pieces at character boundaries until the passage has round(f x N) pieces
(byte-fallback pieces excluded on subject G; must decode to the canonical
bytes); B(seed) re-bounds adjacent tokens within a word at unchanged count
(descriptive only); FILL(f) extends the canonical passage with the next
canonical tokens of the same article to R(f)'s token count. S4 measured R and
B on both real tokenizers (`compute/resegment.json`).

## Operating point (held-out, before any analysis episode)

In the smoke, on the held-out set: canonical accuracy at K in {4, 8, 16} and
native accuracy at (K, f) for f in {2.7, 2.0}, 200 episodes per cell.
`estimator_v2.select_operating_point`: K_p is the smallest K whose canonical
accuracy is at most 90; if that accuracy is below 50, or no K is at most 90,
the subject is NOT_ADMISSIBLE. f_p is the first of 2.7, 2.0 whose native
accuracy at K_p is at least 30 (chance plus 5); otherwise NOT_ADMISSIBLE. The number of
analysis articles is then fixed: 2,000 at f_p = 2.7, 3,000 at f_p = 2.0. A
NOT_ADMISSIBLE subject is reported with its held-out accuracies and makes no
claim; it is not INVALID.

## Cells (at K_p; n in episodes)

Paired design: every cell of an episode reuses the same facts, codes, target,
passage and lead-in.

| Cell | Passage tokens | Decay pathway | n | Tier |
|---|---|---|---|---|
| CAN | canonical | native | 4 x N_art | primary |
| DEC | canonical | each canonical token's log-decay set to its pieces' summed log-decay in NAT, every layer and head or channel | 4 x N_art | primary |
| CLAMP(f_p) | R(f_p) | pieces rescaled so each canonical token's summed log-decay equals its value in CAN | 4 x N_art | primary |
| NAT(f_p) | R(f_p) | native | 4 x N_art | primary |
| DOSE(f_p) | canonical | every passage log-decay multiplied by f_p | 1,000 | L8 |
| SIL-NAT(f_p), SIL-CLAMP(f_p) | R(f_p), passage writes silenced | native / clamped to CAN | 1,000 | L7 |
| CLAMP-LAST(f_p) | R(f_p) | each token's canonical log-decay placed on its last piece, 0 on the others | 1,000 | L6 |
| FILL(f_p) | canonical, lengthened to R(f_p)'s count | native | 1,000 | L5 |
| R2(1), R2(f_p) | canonical / R(f_p) | every log-decay halved | 1,000 | L4 |
| BND, ZERO | B / none | native | 1,000 | L3 |
| NAT(f'), CLAMP(f') for the other f | R(f') | native / clamped | 1,000 | L2 |
| BPB subset | CAN, NAT(f_p), BND with full logits | native | 200 | L1 |

N_art is 2,000 at f_p = 2.7 and 3,000 at f_p = 2.0. Secondary cells use the
first 1,000 episodes (seed 42's articles, then seed 43's), so they pair with the
primary arms. CAN runs first in every batch (CLAMP needs its targets) and NAT
before DEC (DEC needs NAT's piece sums).

## Interventions

- **Decay clamp (CLAMP, SIL-CLAMP).** As in v1. For each canonical token u of
  the passage, each layer l and head h (G) or channel (R): target G_c(u) is
  u's log-decay in CAN; G_r(u) is the sum of the live log-decays of u's pieces;
  each piece's log-decay is multiplied by c = G_c / G_r. Applied layer by
  layer, so live values at layer l include the clamps below. Subject G: a
  forward hook on a_proj replaces a with softplus^-1(c softplus(a + dt_bias))
  - dt_bias (exact). Subject R: w = -0.6065306597 sigmoid(z), z the w_lora
  output; z' = logit(c sigmoid(z)); where c sigmoid(z) would reach 1 the piece
  saturates at 1 - 1e-6 and the unmatched mass moves to the token's other
  pieces (two passes).
- **Decay transplant (DEC).** For each canonical token u, layer l and head or
  channel: the target is G_r^NAT(u), the summed live log-decay of u's pieces in
  the NAT run of the same episode at that layer, and u's log-decay in the
  canonical run is set to it, layer by layer. Subject G: a' =
  softplus^-1(-G_r / exp(A_log)) - dt_bias (exact; softplus is unbounded).
  Subject R: z' = logit(G_r / -0.6065306597), saturating at
  1 - 1e-6 where G_r < -0.6065306597 (a single step cannot carry more decay);
  the unmatched mass is reported.
- **CLAMP-LAST.** As CLAMP, with the canonical log-decay placed entirely on
  the token's last piece and 0 on its other pieces (a different allocation of
  the same mass; reviewer 1's distribution concern).
- **DOSE.** Every passage position's log-decay multiplied by f_p at every
  layer (a pure per-token clock at fertility f_p, at canonical writes).
- **r = 2.** As in v1 (subject G: A_log - ln 2; subject R: z' =
  logit(sigmoid(z) / 2)).
- **Write silencing (SIL-NAT, SIL-CLAMP).** As in v1 (G: b_proj output -30 on
  passage positions; R: v_proj output 0 and v_lora, a_lora pre-activations -30
  on passage positions).

## Readouts

- **Primary.** Forced-choice correctness Y in {0, 100}: the candidate whose
  canonical string has the largest summed log-probability given the episode,
  from the recurrent state cached at the end of the query.
- **Secondary.** Target forced-choice log-probability l; greedy exact match;
  target logit margin.
- **Ledgers.** R_F(u, l, h) = G_r^NAT / G_c per split token (from NAT and CAN);
  the median over split tokens pooled over layers and heads or channels is the
  registered R_F, reported per layer too. Write drift: for NAT against CLAMP
  (same pieces) and CAN against DEC (same tokens), the mean relative change
  ||x' - x|| / ||x|| of the write key, value and write strength (G: k, v,
  beta; R: k, v, a) at every layer above the first, on passage positions.
  Piece-sum check (I8). Write-overlap mass; BPB per f on the subset.

## Stages

### Smoke (cap 0.75 GPU-h, one GPU, both subjects in sequence)

Load each model with `output_loading_info` (missing keys empty; unexpected
keys only subject G's 24 all-zero `attn.D` tensors). Gates I1, I2 or I2b, I3,
I7 on 200 held-out K = 16 episodes. The held-out operating-point cells (above)
and the selection. A kill-and-resume test on 40 episodes, a throughput
measurement on 64 episodes of every cell type, and a Slurm dry run of both main
manifests.

### Main jobs (one GPU each; caps 1.75 GPU-h for subject G, 3.75 for subject R)

Batches run every cell for their episodes (CAN, then NAT, then CLAMP and DEC,
then the secondaries). Records every 5 minutes keyed by (episode, cell). In the
first 10 minutes each job projects its time; if over the cap, secondary tiers
are dropped in the order L1 to L8; if the primary cells and gates alone exceed
the cap, the subject is INFEASIBLE (throughput floors per branch in
`compute/repair-d68/cost-model-v2.json`, between about 10,600 and 16,500 tok/s
for subject G and 4,500 and 7,100 for subject R). Primary cells are never cut.

## Instrument gates

| Gate | Pass condition | On failure |
|---|---|---|
| I1 hook identity | clamp and transplant hooks active with c = 1 (targets equal to the live values) against unhooked, 200 episodes at f = 1 and f = 2.7: decisions identical on at least 199, median abs difference in l at most 0.01 | subject INVALID |
| I2 two ways (G) | weight edit A_log - ln 2 against the a_proj hook with c = 0.5, and A_log + ln 2 against c = 2: decisions agree on at least 199 of 200 each, max abs difference in l at most 0.02 | subject INVALID |
| I2b reference recurrence (R) | 4 episodes x 64 tokens, native, clamped and transplanted: chunk kernel against a pure-torch recurrence on captured inputs; max relative error at most 1e-2 | subject INVALID |
| I3 padding | padded against unpadded batches: decisions identical on at least 199 of 200, median abs difference in l at most 0.01 | subject INVALID |
| I4 operating point | `select_operating_point` on the held-out set | NOT_ADMISSIBLE (reported, no claim) |
| I5 completeness (R) | unmatched log-decay mass of CLAMP and of DEC on retaining channels (canonical passage-total decay factor at least 1e-3) at most 1% of their total | 1 to 5%: reading stands, flagged; above 5%: subject INVALID; non-retaining channels reported |
| I6 decode identity | every re-segmented sequence decodes to the canonical bytes | episode regenerated with the next derived seed (logged) |
| I7 loader sanity | canonical WikiText-103 test perplexity at most 40 on 100 passages | subject INVALID |
| I8 piece sums | recomputed per-token sums equal their targets (CLAMP: G_c; DEC: G_r^NAT) within 1e-4 relative at every layer and head or channel, outside I5's saturated mass | subject INVALID |

## Primary estimands and decision rules

Per subject s at (K_p, f_p), per episode in raw forced-choice points: TNIE,
PNIE, INT, PNDE and TE as defined above. b_X = mean(X) / (0.75 ln f_p), with
the 90% cluster-robust normal interval over articles
(`estimator_v2.cluster_normal`). Line L = 3.

Reading per subject (`estimator_v2.decide_subject`), in order:

1. Any of I1, I2 or I2b, I3, I5 (above 5%), I7, I8 fails: INVALID. I4 fails:
   NOT_ADMISSIBLE.
2. b_TNIE at least L with its lower end above 0: **MATERIAL**.
3. Upper end of b_TNIE below L (the oracle decay-parity benefit is below the
   line), then:
   a. b_PNIE at least L with its lower end above 0: **MASKED**;
   b. otherwise, median R_F below 1.5: **SELF_NORMALIZED**;
   c. otherwise, upper end of b_PNIE below L: **KILL**;
   d. otherwise: **PARITY_NULL**.
4. Otherwise: **INCONCLUSIVE**.

Overall (`estimator_v2.decide_overall`): INVALID or NOT_ADMISSIBLE if either
subject is; the common reading if both agree; SPLIT if one is MATERIAL and the
other in {KILL, MASKED, SELF_NORMALIZED, PARITY_NULL}; LOSS_NULL_MIXED if both
are in that set with different labels; otherwise INCONCLUSIVE.

Consequences, fixed now:

- **KILL.** The phase-1 span-parity loss on forgetting mass is killed without
  translation work, and D20 is closed citing this result with arXiv
  2609.33093 and 2609.16183: in these checkpoints the per-token decay pathway
  carries less than the line at canonical and at re-segmented writes, with the
  gates charging fragments at least 1.5 times canonical decay.
- **MASKED.** The forgetting-mass loss is closed (its oracle benefit is below
  the line), and the record states that pure decay is material at canonical
  writes and that the re-segmentation cost runs through the decay-by-write
  interaction. Any successor targets write-side parity (the legacy loss's
  write-mass term) and needs its own gauntlet.
- **SELF_NORMALIZED.** The loss has nothing to fix on re-segmented English;
  whether excess decay costs recall is untested here (DOSE is reported). A
  successor would first measure R_F on natural high-fertility text in a
  multilingual attention-free subject (a forward-only ledger) under its own
  gauntlet; nothing is funded by this result.
- **PARITY_NULL.** The loss is closed (oracle benefit below the line); no
  mechanism claim beyond the intervals.
- **MATERIAL.** A successor gauntlet may design a translation-paired leg on an
  attention-free subject pretrained on the target languages; neither
  registered subject qualifies, so this funds nothing by itself.
- **SPLIT, LOSS_NULL_MIXED.** Subject-specific readings; no portable claim.
- **INCONCLUSIVE, NOT_ADMISSIBLE.** Reported; no second block without a new
  registration.
- **INVALID.** No claim; repair under a new id.

## Reported regardless of outcome

1. b_TE, b_TNIE, b_PNIE, b_INT and b_PNDE with intervals; the same on the l
   and exact-match scales; the percentile cluster bootstrap beside each.
2. The held-out operating-point table and the selected (K_p, f_p).
3. SIL: b of SIL-CLAMP - SIL-NAT (the decay effect with no passage writes) and
   TNIE minus it.
4. DOSE: b of CAN - DOSE (what a pure per-token clock would cost at canonical
   writes).
5. CLAMP-LAST against CLAMP (allocation sensitivity).
6. FILL: CAN - FILL(f_p) and the canonical extra-token count whose cost equals
   NAT's (the elapsed-context arm on GDN-1.3B and RWKV-7).
7. r = 2: G(1), G(f_p) and dG beside TNIE.
8. BND step; ZERO per load; the other fertility's TNIE.
9. R_F per layer and head or channel; write drift per layer for NAT-CLAMP and
   CAN-DEC; I5 unmatched mass; write-overlap mass; BPB; STRR and share split.
10. Per-seed estimates; all infrastructure events, regenerated episodes and
    dropped tiers.

## Predictions (falsifiable, stated before data; descriptive, cannot change the reading)

- P1 (ledger): median R_F at f_p above 1.5 on both subjects.
- P2 (primary): no subject reads MATERIAL.
- P3: b_TE at least 10 on both subjects.
- P4: CAN - FILL(f_p) smaller than TE on both subjects.
- P5: dG from r = 2 and TNIE differ by more than their combined 90% intervals
  on at least one subject.
- P6: INT is negative on both subjects (restoring decay at the re-segmented
  writes recovers less than the pure decay cost).

## Statistics, sample sizes and simulation

All three are CPU design evidence in the bundle's `compute/repair-d68/`, and
S1v2 and S2v2 import `estimator_v2.py`, so the rules whose operating
characteristics are reported are the rules that would be read.

- **S2v2 (operating characteristics, `power-sim-v2.py`, merged
  `power-sim-v2.json`).** Every replicate runs the registered path: held-out
  selection on 200 binomial episodes per cell, four paired arms from a latent
  probit model with article clustering (article share 0.3 of difficulty, a
  re-segmentation noise shared by NAT and CLAMP, article effect heterogeneity
  0 to 0.2 latent SD), the registered interval and `decide_subject` (the
  vectorised reading equals the scalar function on every checked replicate).
  1,000 replicates per cell. At the registered n and profile P1 (K = 4
  admissible), with TNIE discordance 0.10, 0.30, 0.41 and 0.46: a true null
  reads KILL with probability 1.000, 0.972, 0.929 and 0.903; effects of one
  third of the line read KILL with 0.994, 0.733, 0.564 and 0.520; a true effect
  at the line (TNIE, PNIE or both) reads KILL with probability at most 0.059 in
  every cell; twice the line reads MATERIAL with at least 0.999; a masked world
  (TNIE 0, PNIE 8) reads MASKED with 1.000, 0.976, 0.955 and 0.904; a
  self-normalising world reads SELF_NORMALIZED with 1.000, 0.975, 0.931 and
  0.912. Over the seven scenarios away from the line the mean probability of
  the correct decisive reading is 0.998, 0.919, 0.862 and 0.838. At 1,000
  articles the null would read KILL with only 0.796 at discordance 0.30, at
  1,500 with 0.935, hence 2,000. Other branches: K = 8 selected (P2), K = 16
  selected (P3), f_p = 2.0 selected because native accuracy is at chance at
  2.7 (P4) and canonical accuracy exactly at the ceiling (P5): the null reads
  KILL with 0.995 to 1.00 at low discordance and 0.92, 0.93, 0.82 and 0.92 at
  discordance about 0.40; KILL under a true effect at the line at most 0.061;
  NOT_ADMISSIBLE at most 0.009. The decision interval covers at 0.883 to
  0.918 across the grid; at three check settings the bootstrap covers
  at 0.885 to 0.915 and their below-line decisions agree in 97 to 100% of
  replicates. Selection near the gates: K = 4 is chosen with probability 0.995,
  0.916, 0.54, 0.067 and 0.0003 at true canonical accuracy 84, 87, 90, 93 and
  96; f_p = 2.7 with 0.03, 0.19, 0.50, 0.82 and 0.96 at true native accuracy
  24, 27, 30, 33 and 36 (NOT_ADMISSIBLE 0.11 at 24, at most 0.02 above). v1's dilution is reproduced with v1's own estimator:
  P(KILL) 0.954, 0.792 and 0.655 at a true K = 4 secant of 3. Discordance,
  accuracies and effects are scenario inputs, not measurements.
- **S1v2 (identification, `mech-sim-v2.py`, merged `mech-sim-v2.json`).** A
  two-layer gated delta-rule toy in which layer 2's keys, values, write
  strengths and decays depend on layer 1's reads, with a presence channel,
  the registered operating-point rule on held-out episodes, pools of 400
  articles as truth and the registered estimator resampled at the registered
  n. The ceiling gate moved eight of nine worlds from K = 4 (canonical 96 to
  98) to K = 16; the erase-dominated W9 (canonical 82.5 at K = 4) stayed at K = 4.
  TE = PNIE + PNDE + INT holds to floating error; every clamped and
  transplanted sum equals its target. Both decay contrasts are exactly 0 when
  pieces share the token's decay (SELF_NORMALIZED in W2 and W4); TNIE 27.7 and
  PNIE 28.2 with no extra interference (W1); 0.3 and 0.0 when decay is
  causally inert (KILL, W7); INT -0.5 (W3), -6.5 (W5), +6.8 (W6) and -15.6 in
  the erase-dominated W9 (TNIE 20.8 against PNIE 36.4 at (4, 2.0)); the direct
  probe (`int-sign-probe.json`) finds INT negative in 11 of 12 erase-dominated
  cells. In the line
  world W8 (TNIE 3.0 at the selected point) the v1 rule reads KILL with
  probability 1.00 and the v2 rule with 0.024. Effect sizes are not
  calibrated to the checkpoints.
- **S3v2 (cost, `cost-model-v2.py`).** Per branch, central 0.58 to 0.77 GPU-h
  (G) and 1.02 to 1.39 (R) with every secondary cell; high 1.33 to 1.80 and
  2.96 to 4.13 (the ladder drops secondary tiers above the caps); primary
  cells alone at the high scenario at most 1.48 and 3.34; smoke 0.31 to 0.71.
- **The native floor, changed during the repair.** The repair first
  registered a native floor of 40. S1v2 showed that floor refusing exactly the
  erase-dominated operating points where the factorial reads MASKED: two
  registered-path attempts returned NOT_ADMISSIBLE, and in the probe every cell
  with small TNIE and large PNIE had native accuracy under 40. With PNIE
  co-primary a low native accuracy no longer biases the reading toward KILL,
  so the floor's only job is to keep NAT off chance, and v2 registers 30
  (chance plus 5). S2v2 and the affected S1v2 worlds were re-run under 30; the
  floor-40 outputs are kept unedited in `compute/repair-d68/superseded-floor40/`.
  Residual risk: at native accuracy near 30 both re-segmented arms are close
  to chance, so TNIE is bounded by the floor; the reading then rests on PNIE
  (MASKED or KILL), which is measured at canonical writes under the ceiling
  and floor of K_p.
- **Multiplicity.** One primary estimand per subject for the consequence
  (TNIE); KILL is an intersection-union conjunction with PNIE; the overall
  reading is a fixed rule. All secondary quantities are descriptive.

## Compute caps (D22 counting)

Smoke 0.75 + main G 1.75 + main R 3.75 = 6.25 GPU-h, at most 8.0. The caps are
fixed numbers; the ladder applies inside them. This is the experiment's
compute, separate from the gauntlet's 0.3 GPU-h reviewer budget.

## Checkpoints and resume

As in v1: completed (episode, cell) records every 5 minutes; a fresh job skips
completed keys; the smoke's kill-and-resume test requires identical decisions
and l within 1e-4 for every completed key.

## Infrastructure failures and exclusions

As in v1. No episode is excluded for its outcome. Lost episodes are rerun
from their keys; if impossible they are dropped from every cell and counted;
more than 2% dropped on a subject caps it at INCONCLUSIVE.

## Data rights

As in v1, with the passage source changed to the train split of the same
corpus (same licence): subject R apache-2.0; subject G unlicensed, use
requires decision 1, nothing redistributed under either option; WikiText-103
text kept off the public repository; key lists and templates written by the
project (MIT); no personal data; no model-generated code executed.

## Integrity gate (the seven failure modes)

1. Implementation bug passing self-review: I1, I2/I2b, I3, I6 and I8 run before
   any analysis; the CPU doctor runs S1v2's worlds through the harness's own
   estimator and decision code.
2. Hallucinated citation: every cited arXiv id has a hashed snapshot; read
   status per claim.
3. Hallucinated result: no result exists; S1v2 to S3v2 are labelled
   simulations or arithmetic.
4. Shortcut reliance: K = 1's presence shortcut is removed; all foils are
   in-episode codes; canonical facts among fragmented text could still cue
   storage (BND and ZERO bound it; disclosed).
5. Bug reframed as insight: a TNIE or PNIE of the "wrong" sign is checked
   against I1, I8 and the write-drift ledger before interpretation.
6. Methodology fabrication: every threshold is in `estimator_v2.py`, with its
   operating characteristics in S2v2.
7. Frame lock: r = 2, FILL, SIL and DOSE keep the dossier's, the closest
   prior's and the pure-clock framings measurable beside the factorial.

## Owner's prior forecast (not a decision input)

KILL 0.30, MASKED 0.15, SELF_NORMALIZED 0.10, PARITY_NULL 0.05, INCONCLUSIVE
0.10, MATERIAL 0.05, SPLIT or mixed 0.10, INVALID, NOT_ADMISSIBLE or INFEASIBLE
0.15.

## Freeze procedure

After prerequisites 1 to 7 and Kevin's acceptance of the design decisions:
`uv run python scripts/preregister.py freeze e5-gate-fertility-decomposition-v2 program/preregistrations/e5-gate-fertility-decomposition-v2.md`,
then `verify`. Any material change after freeze is a new id.

## Design decisions (for the owner's acceptance)

1. Subject G's data rights (Kevin's ruling), as in v1.
2. Scope: English only; no translation work.
3. The 2 x 2 factorial CAN, DEC, CLAMP, NAT as the primary arms.
4. Primary estimand TNIE (consequence for the loss), co-primary PNIE
   (mechanism), INT and PNDE reported; no "share".
5. Guessing-corrected scale (divide raw forced-choice differences by 0.75);
   line 3 points per log-f unit on it.
6. One primary load K_p from (4, 8, 16) on held-out data, ceiling 90, floor
   50; K = 1 removed.
7. f_p from (2.7, 2.0) on held-out data, native floor 30 (chance plus 5);
   f = 1.5 removed. (A floor of 40 was tried and dropped in the repair; see
   "Statistics".)
8. N_art 2,000 at f_p = 2.7, 3,000 at f_p = 2.0; four episodes per article.
9. Passages from the WikiText-103 train split, one per article.
10. Cluster-robust normal 90% interval over articles as the decision interval;
    percentile bootstrap reported.
11. Reading order MATERIAL, then (TNIE below the line) MASKED,
    SELF_NORMALIZED, KILL, PARITY_NULL, then INCONCLUSIVE.
12. The R_F guard at 1.5 (P1's threshold).
13. Overall rule as in `decide_overall`.
14. Consequences of each reading, including that MATERIAL funds nothing by
    itself.
15. Only the passage is re-segmented; facts, query and codes canonical.
16. All foils are codes bound in the same episode.
17. Refinement rule R and boundary rule B as in S4; B descriptive only.
18. Clamp implementation and the RWKV saturation rule (as v1).
19. Transplant implementation (G exact; R saturating at one step's maximum,
    unmatched mass reported).
20. I5 on retaining channels (factor at least 1e-3), thresholds 1% and 5%.
21. I8 tolerance 1e-4 relative.
22. I2 at c = 0.5 and c = 2.
23. Secondary cells and the ladder order L1 to L8.
24. CLAMP-LAST as the allocation sensitivity arm.
25. DOSE at f_p as the transfer reference.
26. Caps 0.75, 1.75 and 3.75 GPU-h.
27. Episode length limit 1,900 tokens.
28. Missing-data rule (2%).
29. Predictions P1 to P6 are descriptive.
30. v1 is superseded and left unedited.
