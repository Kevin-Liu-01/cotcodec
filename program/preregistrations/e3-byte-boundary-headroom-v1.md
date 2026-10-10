# Draft registration: E3 Stage-0 headroom probe (`e3-byte-boundary-headroom-v1`)

**Status:** DRAFT. Not frozen, not admitted, no ledger row. Written 2026-10-10
by the E3 gauntlet's single synthesis owner (a Claude agent) under D67, with the
proposal `program/proposals/2026-10-10-e3-byte-boundary-headroom.md`. It may be
frozen only after the gauntlet, a pre-freeze audit, the prerequisites listed at
the end, and Kevin's reserved sign-offs. Any material change after a freeze is a
new id with a new output path.

**Experiment id:** `e3-byte-boundary-headroom-v1` (new; no earlier E3 id exists
in `program/preregistrations/ledger.jsonl`).

**Scope:** E3's Stage 0 only: aligned-span boundary correspondence on FLORES+
for released learned-boundary byte-level checkpoints, against rate calibration.
Nothing is trained. Stage 1 (training a boundary-transport loss) needs its own
gauntlet.

**Evidence this draft depends on:** simulation S1
(`program/proposals/evidence/2026-10-10-e3-byte-boundary-headroom/compute/instrument_sim.py`
and `instrument-sim.json`) for every threshold below, and cost model S2
(`compute/cost_model.py`, `cost-model.json`) for every cap.

## 1. Question and verdicts

On FLORES+ devtest, for the English-Chinese pair with an in-distribution
H-Net on each side, do rate-calibrated stage-1 boundaries already reach the
budget-matched ceiling of aligned-span boundary correspondence?

Verdicts for the decision pair (section 10): NO_HEADROOM, HEADROOM,
HEADROOM_MONOLINGUAL, INDETERMINATE, INSTRUMENT_INVALID, INCOMPLETE.

Consequences, fixed now:

- NO_HEADROOM: E3 stops; the negative is recorded in the decision log.
- HEADROOM_MONOLINGUAL: E3's translation-specific delta is not supported; any
  boundary work moves to monolingual supervision, outside E3.
- HEADROOM: E3 may propose building Stage 1's prerequisites (licensed parallel
  corpus, terminology and tool-schema evaluation set, differentiable loss,
  training code) as a new gauntlet. Nothing else is licensed.
- INDETERMINATE, INSTRUMENT_INVALID, INCOMPLETE: no verdict; recorded; no repair
  inside this id.

## 2. Data

- **Source:** FLORES+ (`openlanguagedata/flores_plus`), revision
  `e707e62e762a...` (full hash pinned at freeze; modified 2026-10-01),
  CC-BY-SA-4.0, gated with automatic approval.
- **Files:** `dev/{eng_Latn,cmn_Hans,kor_Hang,pol_Latn}.jsonl` (997 sentences
  each) and `devtest/...` (1,012 each). Each file's SHA-256 is recorded at fetch.
- **Use:** dev for instrument gates and calibration-threshold fitting only;
  devtest for the decision only, read once by the frozen analysis script.
- **Pairs:** EN-ZH (decision), EN-KO and EN-PL (descriptive), aligned by the
  FLORES+ sentence id.
- **Normalization:** Unicode NFC; no other change; byte sequences are UTF-8.
- **Access:** accepting the gate and creating a read token are Kevin's actions.
  The fetch runs on the host as a CPU job (`fetch-model-cpu.sbatch` pattern,
  adapted for a dataset) and writes to the private run directory only.
- **Rights and hygiene:** no FLORES+ text, per-sentence boundary file,
  per-sentence alignment file or per-sentence score enters this public
  repository; only aggregates, revisions and hashes. Logs never contain sentence
  text. Belebele is not used as a substitute for the gated files.
- **Q3 overlap:** FLORES sentences overlap Belebele passages that Q3 never reads
  (366 of 488). E3 reads them programmatically, trains nothing and reports
  aggregates; whether that is acceptable is reserved sign-off R1.

## 3. Boundary systems

Checkpoints (Hugging Face `cartesia-ai`, licence undeclared, not
publication-eligible):

| Checkpoint | Revision | File, bytes, LFS SHA-256 prefix | Role |
|---|---|---|---|
| `hnet_2stage_XL` | c56e23e0 | `hnet_2stage_XL.pt`, 6,414,086,360, d1338625f706d8a9 | English side of EN-ZH (decision); both sides of EN-KO and EN-PL (descriptive) |
| `hnet_2stage_XL_chinese` | 01db28db | `hnet_2stage_XL_chinese.pt`, 7,021,270,658, a92dd4b2c19e1135 | Chinese side of EN-ZH (decision) |
| `hnet_1stage_XL` | 68f11d72 | `hnet_1stage_XL.pt`, 5,083,413,223, 87e16296f8682ef5 | descriptive: English 1-stage boundaries on all pairs |

Code: `goombalab/hnet` at commit 3673fe12 (MIT) with its JSON configs.

Systems scored on every pair (each on the same sentences):

1. **H-Net native:** boundary where the code's argmax selects it (p above 0.5),
   stage 1 and stage 2 of each 2-stage model, and the single stage of the
   1-stage model.
2. **H-Net rate-calibrated (primary system):** the English side keeps the native
   rule; the other side's threshold on p is fitted on dev so that its mean
   chunks per sentence equal the English side's (section 7).
3. **H-Net rate-calibrated, symmetric (sensitivity):** both sides' thresholds
   fitted on dev to the pair's geometric-mean chunk count.
4. **Same-model variants for EN-ZH:** the English model on both sides; the
   Chinese model on both sides (native and calibrated).
5. **Tokenizer references (CPU):** the OLMo-2 tokenizer
   (`allenai/OLMo-2-0425-1B`, revision a1847dff, Apache-2.0; Bolmo-1B's source)
   and the Qwen3 tokenizer (`Qwen/Qwen3-8B-Base`, revision 49e3418f,
   Apache-2.0; Bwen-8B's source). A boundary is placed at each token's end
   offset. Tokenizers emit hard boundaries with no probability to threshold, so
   they are reported native only, at their own budget.
6. **Word segmentation (line M):** English and Polish whitespace words with
   Unicode punctuation split off; Korean eojeol (whitespace) with punctuation
   split; Chinese words from `jieba` (MIT) at a pinned release in its default
   accurate mode with its default dictionary.
7. **Every character gap** on both sides.
8. **Bernoulli at matched rate** (gate I2): independent boundaries at each
   primary system's per-side canonical-gap rate, seeds 42, 43, 44.

Bolmo-1B and Bwen-8B are not run: their boundaries are trained to emulate their
source tokenizers (Bolmo Sec. 3.2.1), so their source tokenizers stand in for
them. The residual between them and their tokenizers is not measured, which is
disclosed.

## 4. Byte-to-gap mapping

- A byte sequence of length L has L - 1 byte gaps; gap g lies between bytes g
  and g + 1 (0-based).
- **H-Net:** p_t (t = 0 .. L - 1) marks a chunk start at byte t; p_0 is padded
  to 1 and dropped; p_t for t of at least 1 is the boundary probability of byte
  gap t - 1. Stage-2 boundaries are defined on stage-1 chunks: a stage-2
  boundary at stage-1 chunk j maps to the byte gap before the first byte of
  chunk j.
- **Tokenizers:** a boundary at byte gap e - 1 for each token ending at byte e
  (patch-end convention), from the tokenizer's byte offsets.
- **Word segmentation:** a boundary at the gap after each word's last byte.
- Unit tests on hand-built strings (ASCII, 2-byte Polish, 3-byte Chinese and
  Hangul, mixed spacing, punctuation) must pass before freeze.

## 5. Canonicalization

Every boundary is mapped to a canonical character gap before scoring:

- Canonical gaps lie between consecutive non-whitespace characters of the NFC
  string (whitespace runs are collapsed).
- A boundary at a gap adjacent to whitespace (before or after it) maps to the
  canonical gap after the last non-whitespace character before it.
- A boundary at the gap after a character's last byte maps to the canonical gap
  after that character.
- A boundary at a gap inside a multi-byte character maps to the canonical gap
  before that character (the character's start).
- Duplicate canonical boundaries merge; boundaries before the first or after the
  last non-whitespace character are dropped.

S1 shows this makes the patch-end and chunk-start conventions identical (round
trip identity 1.0 on every synthetic pair, S difference 0.0000).

## 6. Aligners and consistent cuts

- **Aligner A:** CTFAlign (`ZurichNLP/CTFAlign`, MIT, pip `ctfalign`, revision
  pinned at freeze) with LaBSE (`sentence-transformers/LaBSE`, Apache-2.0,
  revision 836121a0) as the embedder, its default extraction settings.
- **Aligner B:** SimAlign (`cisnlp/simalign`, MIT, revision pinned at freeze)
  with XLM-R base (`FacebookAI/xlm-roberta-base`, MIT, revision e73636d4), its
  "itermax" method, layer 8.
- **Aligner units:** English and Polish whitespace words with punctuation split;
  Korean eojeol with punctuation split; Chinese characters (no segmenter, so the
  aligner does not inherit jieba's choices).
- **Consistent cut:** for aligner units 0 .. n - 1 on side a, the gap after unit
  i is consistent if units at or before i and units after i are both linked, and
  the largest side-b index linked from the left block is smaller than the
  smallest side-b index linked from the right block. Its side-b range is the set
  of unit gaps between those two indices. Consecutive side-a gaps with the same
  side-b range (separated only by unlinked units) form one cut. Each cut is
  converted to canonical gaps on both sides.
- Unit gaps inside an aligner unit are never cuts.

## 7. Instrument

**Projected boundary Dice (PBD).** For one sentence pair, boundary sets B_a and
B_b on canonical gaps, and the cut list of one aligner: a cut is hit when B_a
has a boundary in its side-a range and B_b has a boundary in its side-b range.
Pooled over sentences, PBD = 2 x (cuts hit) / (|B_a| + |B_b|).

**Normalization.** S = (PBD_sys - PBD_floor) / (PBD_ceiling - PBD_floor), all
three pooled over the same sentences:

- **Floor:** side b's boundary array circularly shifted within the sentence by an
  offset drawn uniformly from 1 .. (gaps - 1), 20 shifts per sentence, mean cut
  hits (rate- and spacing-preserving).
- **Ceiling (self, primary):** per sentence, budget n = round((|B_a| + |B_b|) /
  2); n cuts of the same aligner drawn at random (same draw on both sides, the
  last canonical gap of each range), or all cuts plus random extra canonical
  gaps independently per side when n exceeds the number of cuts; scored under
  the same aligner.
- **Ceiling (cross-fit, reported only):** the other aligner's cuts scored under
  this aligner. S1 shows it overshoots the truth by 14% to 99% (perfect
  system, by noise level and profile), so it decides nothing.

**Rate calibration.** For a model with probabilities p on side b, the threshold
is the value at which the dev mean of boundaries per sentence on side b equals
the dev mean on side a under side a's native rule (ties broken by keeping the
higher-probability gap). The threshold is applied unchanged to devtest; achieved
matching is gate I5.

## 8. Instrument gates (dev, before any devtest read)

Computed on FLORES+ dev for each pair and both aligners. A failed gate makes the
pair INSTRUMENT_INVALID; nothing is tuned to pass a gate.

| Gate | Requirement | Simulated basis (S1) |
|---|---|---|
| I1 alignment sensitivity | PBD of the primary system under a permuted alignment (side-b unit indices relabelled at random, seed 42) at most 0.25 x its PBD under the aligner | permuted at most 0.027 against 0.27 to 0.91 for structured systems |
| I2 rate robustness | Bernoulli boundaries at the primary system's per-side rates give absolute S at most 0.03 (each seed 42, 43, 44) | at most 0.019 at 400 pairs per seed, rates 0.05 to 0.5 |
| I3 convention invariance | re-mapping every boundary through the other convention and back changes no canonical boundary (identity share 1.000) | 1.000 on every pair |
| I4 aligner agreement | cut Dice between aligners A and B (cuts as side-a canonical gaps) at least 0.75 for any verdict; at least 0.85 for the 0.85 HEADROOM line | attenuation of S about 0.02 at Dice 0.88, about 0.06 at 0.77; KO-like 0.53 to 0.72 |
| I5 rate matching | rate-calibrated mean chunks per sentence on the two sides within 1% on dev (where the threshold is fitted) and within 5% on devtest | dev-fitted thresholds matched held-out means within 3.3% (mean 1.1%) in S1 part 4 |
| I6 completeness | at most 2% of pairs dropped by either aligner (no links or no consistent cut); zero in-character boundaries after canonicalization | not simulated |

## 9. Line M (translation-specificity guard)

The word-segmentation reference (system 6) is scored at its own budget with its
own floor and self ceiling. If its S is at least 0.90 under both aligners, a
HEADROOM verdict on the decision pair becomes HEADROOM_MONOLINGUAL. S1 shows
word segmentation reaching S of 0.99 to 1.00 in the synthetic world, so this
guard can fire.

## 10. Decision rule (EN-ZH devtest, stage-1, rate-calibrated system)

For each aligner X in {A, B}: S_X with its 90% interval [L_X, U_X], and the
inter-aligner cut Dice a on devtest.

- If any gate fails or a is below 0.75: INSTRUMENT_INVALID.
- Per aligner: NO_HEADROOM if S_X at least 0.88 and L_X at least 0.85; HEADROOM
  if U_X below h, where h = 0.85 if a is at least 0.85 and h = 0.80 if a is in
  [0.75, 0.85); otherwise INDETERMINATE.
- The pair's verdict is the common per-aligner verdict; if the two differ, it is
  INDETERMINATE.
- Then line M: HEADROOM becomes HEADROOM_MONOLINGUAL if the word reference's S is
  at least 0.90 under both aligners.
- If either GPU job reaches its cap or fails, INCOMPLETE.

**Why these numbers.** The dossier's line is 90% of the ceiling. S under the
self ceiling is attenuated by aligner noise (it reads low), so a literal 0.90
rule declares false HEADROOM (S1: probability 1.00 at true S 0.933 with high
aligner noise). The registered lines were chosen from S1's operating
characteristics before any real data:

| Synthetic condition (cut Dice) | P(NO_HEADROOM) at true S about 0.93 | P(wrong-side call) | P(HEADROOM) at true S about 0.83 |
|---|---|---|---|
| ZH-like, low noise (0.935) | 1.00 | NO_HEADROOM 0.97 at true 0.897 | 1.00 |
| ZH-like, base (0.877) | 1.00 | NO_HEADROOM 0.03 at true 0.897 | 1.00 |
| PL-like, base (0.793) | 1.00 | NO_HEADROOM 0.17 at true 0.887 | INDETERMINATE 1.00 at true 0.842; HEADROOM 1.00 at 0.776 |
| ZH-like, high (0.770) | 0.01 (INDETERMINATE 0.99) | none | 1.00 |
| KO-like (0.531, 0.720) | INSTRUMENT_INVALID 1.00 | none | INSTRUMENT_INVALID 1.00 |

HEADROOM was never declared at true S of 0.90 or more. The rule's tolerance is
NO_HEADROOM down to true S of about 0.887 (0.013 under the dossier's line),
disclosed.

## 11. Statistics

- Pooled ratio estimators from per-sentence counts (cut hits, boundaries per side,
  floor hits, ceiling hits).
- 90% percentile interval from a cluster bootstrap, B = 2,000, seed 42, resampling
  FLORES+ source articles (the `url` field) if the pinned files carry it,
  otherwise sentences (disclosed). Floor and ceiling counts are resampled with
  the system.
- Seeds: [42, 43, 44]. The floor shifts and the ceiling draws use seed 42 for
  the decision; seeds 43 and 44 repeat them, and the range of S over the three
  seeds is reported. S1 did not isolate this draw-only spread; the total
  standard deviation of the estimate, sentence sampling included, was at most
  0.007.
- Precision: S1 gives a standard deviation of the S estimate of 0.002 to 0.008 at
  1,012 pairs, so no power gap exists at this N; the decision risk is aligner
  attenuation, handled by gate I4 and section 10.
- One primary quantity. Everything in section 12 is reported without a verdict.

## 12. Reported regardless of outcome

- S (self and cross-fit ceilings), raw PBD, floor and ceiling for every system,
  pair, stage and aligner, on dev and devtest.
- The calibration split: S_native, S_rate, and their difference.
- Per-side boundaries per sentence and per canonical gap, by script.
- The lag profile: S with side b shifted by -3 .. +3 canonical gaps.
- The token-alignability form: the raw share of one-to-one chunk alignments per
  direction (S1 shows its normalized form is ill-conditioned).
- The legacy UOT cost on 300 devtest pairs per pair (seed 42 sample) for the
  primary system, its permuted-alignment ratio and its convention ratio, from
  the restored evaluator (gate I7 below); S1 predicts it fails alignment
  sensitivity.
- Boundary similarity B (segeval) between sides through the cut projection.
- Aligner statistics: links per unit, unlinked share, cut counts, cut Dice.

**I7 (secondary only):** the legacy evaluator, moved to `harness/` with its
doctor in `scripts/`, passes its six gates to a fresh output path before the UOT
secondary runs. If it does not, the UOT secondary is not reported.

## 13. Compute

**Jobs (one GPU each, network off, `scripts/submit_docker_research_job.py`
dry run, test-only, then submit; never while a Q2 job runs):**

| Job | Cap (GPU-h) | Content |
|---|---:|---|
| smoke | 0.20 | imports; `torch.load(weights_only=True)` of all three checkpoints (fail closed); one forward of `hnet_2stage_XL` on 64 synthetic byte strings (no FLORES text); two runs bit-identical; kill-and-resume of per-checkpoint output files |
| probe | 0.60 | boundary probabilities of the three checkpoints on dev and devtest in four languages (stage 1 and stage 2); aligners A and B on the three pairs, dev and devtest; per-file SHA-256 |
| **Sum of caps (D22)** | **0.80** | under the 8 GPU-h threshold |

**Arithmetic (S2).** Bytes: 2,009 sentences x (130 + 125 + 140 + 140) bytes =
1,074,815 (central; estimated, FLORES+ not downloaded), 1,612,222 high (x1.5).
Upper-bound FLOPs per byte: 2 x (1.6e9 + 1.755e9 + 1.3e9) = 9.31e9. High compute:
1.612e6 x 9.31e9 = 1.50e16 FLOP at an assumed 20 TFLOPS effective in fp32 = 12.5
minutes; central: one third of the FLOPs at 30 TFLOPS = 1.9 minutes. Overheads:
container 3 to 4 minutes, checkpoint load and kernel JIT 2.5 to 4 minutes x 3,
aligners 2 to 3 minutes, hashing 1.5 to 2 minutes. Totals: central 15.9 minutes
(0.26 GPU-h), high 33.5 minutes (0.56 GPU-h). The probe cap 0.60 is 1.075 x the
high estimate. Nothing here is measured on the host.

**Host CPU jobs (0 GPU-h, still host jobs):** the overlay image build (hnet at
3673fe12, mamba-ssm, causal-conv1d and flash-attn at upstream's pins, on
`127.0.0.1:5000/cotcodec-research@sha256:13a9de831cff50461d8ecee3c2794f0c6d6bcffe9d602968fe2ee06e5a1096e9`);
the checkpoint and FLORES+ fetches with receipts.

**Mac CPU (0 GPU-h):** PBD scoring, gates, bootstrap (about 26 CPU-minutes);
UOT secondary (about 4 CPU-hours, about 30 minutes on 8 processes).

**Determinism and resume:** fp32 with TF32 disabled for the boundary
computation; outputs written atomically per checkpoint and language; a fresh job
skips files whose hashes verify. A job at its cap is killed and the run is
INCOMPLETE; no extension under this id.

## 14. Outputs

- Private run directory on the host and the private archive: per-checkpoint
  boundary probability files, aligner link files, the FLORES+ files, receipts.
- Public repository: the analysis code and its tests, the frozen script digests,
  aggregate result JSON (no per-sentence rows), the verdict, and every hash.

## 15. Deviations

Any change to a number, rule, system, aligner, revision or script after freeze is
a new id. A bug found after freeze is fixed only under a new id, with the
original output kept and the reason recorded.

## 16. Reserved sign-offs (Kevin)

- **R1:** E3 may read FLORES+ sentences that overlap Q3's sealed Belebele
  passages, programmatically and without logging text.
- **R2:** accept the FLORES+ gate and provide a read token on the host.
- **R3:** the pinned upstream H-Net, mamba-ssm, causal-conv1d and flash-attn code
  is a trusted input under D7 and D29 (human-written library code, not code
  produced during an experiment).
- **R4:** H-Net weights with an undeclared licence may be fetched and used for an
  aggregate-only measurement, recorded as not publication-eligible.
- **R5 (optional):** request XL-WA's en-zh and en-ko gold sets (an outward action;
  CC BY-NC-SA 4.0) to measure aligner error on EN-ZH; the verdict does not wait
  on it.

## 17. Prerequisites before freeze

1. The PBD scorer, canonicalization, cut builder and byte mappings in
   `harness/` with unit tests, run as an orx `cpu-doctor` node that also
   re-runs S1's gates against the restored code.
2. The legacy evaluator and doctor restored to `harness/` and `scripts/` with a
   fresh doctor output (for the UOT secondary).
3. Aligner and tokenizer revisions pinned; their licences re-checked at the pinned
   revisions.
4. The overlay image built and its digest pinned; the three checkpoints fetched
   with receipts; a `models/registry.yaml` entry for each.
5. Manifests for the smoke and probe jobs, dry run and test-only passed.
6. A pre-freeze audit by a fresh reviewer.
7. R1 to R4 signed off.
