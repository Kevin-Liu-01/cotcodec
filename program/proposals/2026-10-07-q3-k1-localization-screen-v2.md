# Research Direction: Q3 K1 Localization Screen v2 (cross-script selection recall of KL-distilled sparse-attention indexers)

**Status:** draft; gauntlet wave 1, synthesis by the single synthesis owner; blind closest-prior discrimination, refute-first triad and two provider-distinct reviews not yet run; not pilot-ready; a score of 100 cannot be certified in this repository (program decision D24)
**Owner:** Kevin Liu (program owner); wave-1 synthesis written by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-07
**Coverage limits:** orx 0.2.2 only (alphaXiv keyword and embedding search, OpenAlex) plus 2 WebSearch queries; the arXiv API, Semantic Scholar and the H100-host relay were not used, so there was no forward or backward citation-graph expansion; OpenReview, ACL Anthology full text, GitHub and Hugging Face code or model cards, patents, X, Reddit and blogs were not searched; one Chinese-language keyword query only; no title-phrase query was run for XProvence (its full text was read); full texts were read by targeted section and grep, not end to end; the production reports for GLM-5.3, MiniMax MSA, FlashMemory, DeepSeek-V4.1-Flash, LongCat LSA and LatentIndex were read in full by the frontier cell but only by abstract by the kill-shot cell; the declared 150-query budget was exceeded by the three discovery cells (159 queries) before synthesis, so synthesis ran no discover query of its own
**Budgets:** queries=150; wall_minutes=600; tokens=6000000; dollars=150; waves=3; gpu_hours=1
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-07-q3-k1-localization-screen-v2/bundle.json

## Claim and Research Question

The experiment under review is the draft registration
`program/preregistrations/q3-k1-localization-screen-v2.md` (v2). Its design is
`q3-k1-localization-screen-v1`'s, carried unchanged under program decision D20
(an engineering-only successor). The v2 throughput probe priced its registered
caps at 8.05 GPU-hours, over the 8 GPU-hour threshold, so v2 is not frozen and
runs this gauntlet (D22, D24). This proposal argues the case for that design
and states its defects. It changes nothing in the registration: under D20 a
change to the registered science needs a new experiment id.

Registered question (v2, "Question"): on frozen Qwen3-0.6B-Base, do
block-form (compress ratio 4) sparse-attention indexers distilled by KL from
the model's own attention, and trained without the evaluation languages, lose
more needle-selection recall than the dense block top-k of their own
distillation target when the question is a human translation in a different
script from the needle passage, compared with a same-language non-literal
question, at a matched achieved budget of 1,024 tokens in an 8,192-token
context?

Variable and statistic. For target T in {hs (head-sum), mp (QSA max-pool)},
xi_T is the macro over the 14 cross-script pairs of the family mean of
[R_ind(MN) − R_ind(CX)] − [R_T(MN) − R_T(CX)] in recall points. R_ind is the
seed-averaged indexer at the frozen learning rate, R_T the dense top-256 blocks
of its own target, MN the question in the needle's language and CX the
human-translated question in the other language. The co-statistic is
xi_rel_T = macro of G(MN) − G(CX), with G(c) = (R_ind(c) − R_rand(c)) / (R_T(c) − R_rand(c)).

Claim scope: **attachment-capability.** The indexers are trained KL-only on a
frozen backbone. That is the state the QSA report itself describes as
degrading quality until joint sparse training (C10). Routing Absorption reports
that post-hoc gates on a frozen checkpoint behave differently from co-trained
gates (C21). No outcome of this screen is a statement about production DSA or
QSA indexers, and none is an architecture claim (rule 8).

What this proposal claims:

1. The screen measures one quantity that no source in the stated coverage
   reports.
2. The registered design is reproducible and staged so that the cheapest
   decisive step runs first.

What it does not claim: that the screen is likely to be decisive at 0.6B. The
evidence assembled in this wave says its decisive outcomes are narrow (see
"Mechanism and Falsifiable Predictions"). It also says the NEGATIVE branch is
not identified against an indexer that retrieves nothing non-literal in either
leg. Both are stated as defects below; neither is argued away.

Decision this proposal serves: under D24, admission of any experiment over 8
GPU-hours waits on Kevin. Kevin can admit v2 as registered, defer it, or
replace it with a re-registered version under a new id.

## Strategic Fit and Why Now

- Production sparse attention trains learned indexers by KL to the model's own
  attention: DSA (C11), QSA (C10), and A.X K2's sparse-selection variant (C13).
  Frozen-backbone versions exist too: SeerAttention (C09), SpotAttention (C12)
  and Oracle-Guided Sparse Prefill (C08).
- None reports per-language or cross-script selection behaviour in any text read
  by this gauntlet (C10, C12, C13, C32). QSA's only multilingual comparison is
  the aggregate MMMLU score, 81.8 for full attention against 81.1 for QSA.
  A.X K2, a Korean-focused model, reports Korean long-context results only for
  the sparse model, and it removed the 87 LongBench v2 items that contain Han
  characters (C13).
- The cross-lingual long-context gap is documented only behaviourally:
  - for dense models, by MLNeedle, OneRuler, xMRC and the hybrid-attention
    study (C16, C17, C28, C40);
  - for selectors outside the model, by Lost in Compression and XProvence
    (C14, C15).
  None localizes a gap to an in-model selection component.
- Program fit. Q3 is the program's backfill question
  (`program/questions/q3-cross-script-indexer.md`) and K1 is its first
  experiment. v1 failed only its budget gate (SMOKE_PASS_OVER_BUDGET, smoke job
  452). v2 rewrote the engineering (D20). The probe (job 543,
  PROBE_COMPLETE) measured the rates, and the caps came out at 8.05 GPU-hours
  with the probe included.
- Why now, honestly stated. The harness, the 278.8 MB bundle and the measured
  rates exist, and the registered order runs a dense-only development
  pre-check before any registered indexer is trained, projected at about 0.19
  GPU-hours (smoke plus pre-check). The strategic weaknesses are three:
  - Q3 is backfill behind Q1 and Q2.
  - The 0.6B base is the weakest rung the contract allows.
  - The evidence below makes it likely that the screen ends at that pre-check
    or at an interpretability gate rather than at GO or NEGATIVE.
  The fit is therefore "cheap to ask, likely to answer 'not at 0.6B'". That
  answer is itself the input to the contract's next rung (Qwen3.5-4B-Base,
  3 to 5 times the cost).

## Primary-Source Evidence

### In-repository measurements (no new experiment ran in this wave)

- E1. v1 smoke job 452 (`program/evidence/2026-10-07/q3-k1/smoke-452/phase-0a-k1-receipt.json`,
  `recall_smoke`). It measured 20 units: the first 20 selection units of the
  development partition (`scripts/run_sparse_indexer_phase0a.py`,
  `phase_smoke`), MN and CX mixed in an unrecorded proportion. Values are the
  mean over the 28 layers.
  - Dense block top-256 recall: T:hs 26.45, T:mp 26.08 and T:hm 26.27.
  - Analytic random selection: 12.48. Union of per-head top-1,024 (U): 66.54.
    Union of per-head top-64 (U_k): 9.75.
  - The 4-step smoke indexers: 11.87 to 12.89.
  - Dense headroom over random is therefore about 14.0 (hs) and 13.6 (mp)
    points, pooled over MN and CX.
- E2. Throughput probe job 543 (`program/evidence/2026-10-07/q3-k1-v2/probe/`).
  - PROBE_COMPLETE in 3 min 18 s, using 0.055 GPU-hours.
  - Every TF32 tolerance gate passed on the H100.
  - Derived limits (`derive/derive-limits.json`): smoke 11 min (0.19 GPU-h),
    headroom-dev 11 (0.19), resume legs 15, 12 and 11 (0.25, 0.20, 0.19),
    main 50 min on 4 GPUs (3.34), extension 53 min on 4 GPUs (3.54), probe 9
    (0.15). The total with the probe is 8.05 GPU-hours, and the gauntlet is
    required.
- E3. Registered pre-freeze simulations (v2, "Seeds, sample sizes and
  sensitivity", with scripts in `program/evidence/2026-10-07/q3-k1-prefreeze-simulations/`).
  - H2a passes the 20-question development pre-check with probability
    0.05–0.07, 0.17–0.39, 0.46–0.76 and 0.72–0.95 at a true dense CX accuracy
    of 35, 40, 45 and 50 percent.
  - H2b needs a needle-present minus needle-absent effect of about 14–15
    points to pass with probability 0.8–0.9.
  - P(HOLD) is 0.47, 0.20, 0.06 and 0.002 at a true English ML gap of 0,
    −0.5, −1 and −2 points when the per-prompt SD is 6. When the SD is 10 it is
    0.74, 0.57, 0.39 and 0.13.
  - GO per target has probability 0.50, 0.82 and 0.97 at a true xi of 10, 11
    and 12 in the worked case. NEGATIVE for both targets has probability 0.92
    at a true xi of 0.
- E4. Bundle facts (v2, "Bundle").
  - Mean audit needle length in tokens: en 95, ja 138, he 142, ko 155, el 467,
    bn 482, ka 501 and ta 587. Against English, that is 1.45 to 6.2 times as
    many tokens.
  - Indexer training removed documents with more than 0.5 percent characters in
    the Hiragana, Katakana, Hangul, Bengali, Tamil, Greek, Hebrew or Georgian
    blocks, so every cross-script evaluation script except kanji is unseen by
    the indexer. Every same-script comparator (id, tr, sw, nl, it) uses the
    seen Latin script.
  - Half of the training stream is bilingual concatenations from 7 pairs that
    are not evaluated: en-de, en-fr, en-es, en-pl, en-th, en-hi and en-km.
- E5. Code (`harness/sparse_indexer_k1_stats.py`, tabled and unchanged from v1).
  - `TargetRead.negative` tests only the xi and xi_rel points and intervals.
  - `AdequacyRead.v1_pass` tests only English literal (ML) recall: R_ind ≥ R_T(ML) − 5 at every seed.
  - `k1_verdict` calls NEGATIVE when both targets pass V1, both are in the
    NEGATIVE region and H1 ≥ 20.
  - The Belebele dedup list (`harness/sparse_indexer_data.py`,
    `BELEBELE_LANGUAGES`) covers 18 languages. It omits the training languages
    de, fr, es, pl and ru.

### Claim registry

Statuses:

- **VERIFIED_SYNTHESIS**: re-read in full text by the synthesis owner on
  2026-10-07 (`orx paper --full`; the text digest is in the hashed query log).
- **VERIFIED_REPO**: read from the committed repository record.
- **CELL_READ**: read in full text by a discovery cell and not re-read by
  synthesis.
- **ABSTRACT_ONLY**: only the abstract was read.
- **FIRST_PARTY**: an author's or lab's claim about its own system.

Every cited arXiv and Hugging Face page has a hashed snapshot (HTTP 200) in
the evidence bundle. Dates are those shown in that snapshot.

| claim_id | claim | source and locator | date | status |
|---|---|---|---|---|
| C01 | v1 smoke dense and random recall as in E1 | program/evidence/2026-10-07/q3-k1/smoke-452/phase-0a-k1-receipt.json, recall_smoke | 2026-10-07 | VERIFIED_REPO |
| C02 | probe rates, limits and 8.05 GPU-h caps as in E2 | program/evidence/2026-10-07/q3-k1-v2/probe/derive/derive-limits.json; operator-log.txt | 2026-10-07 | VERIFIED_REPO |
| C03 | simulated operating characteristics as in E3 | v2 registration, Seeds, sample sizes and sensitivity | 2026-10-07 | VERIFIED_REPO (simulations not re-run) |
| C04 | needle lengths, script exclusions, training pairs as in E4 | v2 registration, Training stream and Bundle | 2026-10-07 | VERIFIED_REPO |
| C05 | NEGATIVE region and V1 code as in E5 | harness/sparse_indexer_k1_stats.py, TargetRead.negative, AdequacyRead.v1_pass, k1_verdict | 2026-10-07 | VERIFIED_REPO |
| C06 | Belebele dedup covers 18 languages, not de, fr, es, pl, ru | harness/sparse_indexer_data.py, BELEBELE_LANGUAGES | 2026-10-07 | VERIFIED_REPO |
| C07 | Qwen3-0.6B-Base at da87bfb6: apache-2.0, 28 layers, 16 Q and 8 KV heads, head dim 128 | https://huggingface.co/Qwen/Qwen3-0.6B-Base/tree/da87bfb608c14b7cf20ba1ce41287e8de496c0cd and the model receipt in the v2 registration | 2026-10-07 fetch | FIRST_PARTY; VERIFIED_REPO |
| C08 | Oracle-Guided Sparse Prefill (Wang et al.): frozen GQA backbone; head-averaged attention-mass top-k oracle; head-collapsed indexer KL-distilled from that distribution; error split into oracle, indexer and realization gaps; Table 9 RULER-32K Qwen3.5-0.8B dense 90.8, distilled 90.2 at top-k 1,024; no multilingual content | https://arxiv.org/abs/2606.07703 , §3 decomposition, §4.1, Table 9 | v1 2026-06-05 | VERIFIED_SYNTHESIS; FIRST_PARTY |
| C09 | SeerAttention (Gao et al.): learnable block gate on a pretrained LLM, all other parameters fixed; 2D-max-pooled attention map as ground truth; KL loss; 0.5B tokens for Llama-3.1-8B | https://arxiv.org/abs/2410.13276 , §3 and Figure 1 | v1 2024-10-17; v4 2025-02-17 | VERIFIED_SYNTHESIS |
| C10 | QSA (Qiu et al.): Stage 1 trains only the indexer for 1,000 steps (about 2B tokens), KL to head-summed L1-normalised attention over complete blocks; "directly applying the indexer" after dense initialization gives "a clear performance drop"; MMMLU 81.8 full attention vs 81.1 QSA; no per-language indexer table | https://arxiv.org/abs/2608.30320 , §2.1.2 Training Details, Table 2, paragraph after Figure 6 | v1 2026-08-31 | VERIFIED_SYNTHESIS; FIRST_PARTY |
| C11 | DSA: dense warm-up of 2.1B tokens with only the indexer trained, then 943.7B sparse-stage tokens | https://arxiv.org/abs/2512.02556 , §2 | v1 2025-12-02 | VERIFIED_SYNTHESIS; FIRST_PARTY |
| C12 | SpotAttention (Ahmad and Yun): plug-in KL selector on frozen Qwen3/Qwen3.5; behaviour on non-English data untested (Limitations) | https://arxiv.org/abs/2606.22874 , Limitations | v1 2026-06-22 | VERIFIED_SYNTHESIS |
| C13 | A.X K2 (Baek et al.): indexer warm-up KL over its own sparse top-k selection; LongBench v1 62.80 dense vs 62.99 sparse; 87 of 503 LongBench v2 items with Han characters removed | https://arxiv.org/abs/2608.30181 , abstract, Table 8, Table 9, Appendix B.7 | v1 2026-08-31 | VERIFIED_SYNTHESIS; FIRST_PARTY |
| C14 | Lost in Compression (Lukauskas): learned extractive compressors outside the model; Belebele items in each language (question in the context's language); gap is rate-dependent (near equal at keep-rate 0.75, large at 0.33) and tracks supervision language; multilingual XProvence v1 shows none | https://arxiv.org/abs/2608.26175 , abstract, §3 Audit Protocol | v1 2026-07-27 | VERIFIED_SYNTHESIS |
| C15 | XProvence (Mohamed et al.): multilingual query-aware context pruner robust when context language differs from query language and on unseen languages (MKQA) | https://arxiv.org/abs/2601.18886 , RQ4, Figure 2 b and c | v1 2026-01-26 | VERIFIED_SYNTHESIS |
| C16 | Multilinguality in Hybrid Attention LLMs (Bandarkar et al.): OneRULER NIAH at 8K, non-English, Granite-4.0-H-Micro 52.1 vs Granite-4.0-Micro 71.2; English 75.2 vs 80.4 | https://arxiv.org/abs/2609.35378 , Table 2 | v1 2026-09-28 | VERIFIED_SYNTHESIS |
| C17 | MLNeedle (Hengle et al.): the question language is kept fixed in English | https://arxiv.org/abs/2408.10151 , §2.1 | v1 2024-08-19 | VERIFIED_SYNTHESIS |
| C18 | Qwen3 Technical Report Table 37 (Belebele by family): no 0.6B row; Qwen3-1.7B non-thinking 43.3 to 62.7; Gemma-3-1B-IT 27.3 to 36.5 (post-trained models, no haystack, same-language question) | https://arxiv.org/abs/2505.09388 , Table 37 | v1 2025-05-14 | VERIFIED_SYNTHESIS; FIRST_PARTY |
| C19 | PHSA Table 2, Qwen3-0.6B-Base untrained column: arc_c 33.45, arc_c_zh 30.97, cmmlu 53.38, c-valid 54.90 | https://arxiv.org/abs/2601.02819 , Table 2 | v1 2026-01-06 | VERIFIED_SYNTHESIS |
| C20 | Causal Evidence Sets (Allchin): first-token attention sink takes budget in attention-imitation targets; router seeds within one teacher agree within 0.08 | https://arxiv.org/abs/2607.21692 , §5 and §7 | v1 2026-07-23; v4 2026-08-28 | VERIFIED_SYNTHESIS |
| C21 | Routing Absorption (Aquino-Michaels): a gate trained post hoc on a frozen dense checkpoint converges to near-oracle routing, co-trained gates are absorbed | https://arxiv.org/abs/2603.02227 , abstract and §1 | v1 2026-02-11; v2 2026-09-14 | VERIFIED_SYNTHESIS |
| C22 | Retrieval and retrieval-transition heads (Patel et al.): cross-lingual NIAH; conclusion warns that retrieval-prioritising KV compression may prune heads multilingual reasoning needs | https://arxiv.org/abs/2602.22453 , §6 Conclusion | v1 2026-02-25; v4 2026-09-11 | VERIFIED_SYNTHESIS |
| C23 | LAReQA (Roy et al.): weak versus strong cross-lingual alignment; same-language bias | https://arxiv.org/abs/2004.05484 , §2, Figure 1 | v1 2020-04-11 | VERIFIED_SYNTHESIS |
| C24 | Translate-Distill (Yang et al.): cross-language dense retrieval distilled from a cross-encoder; the teacher's input language and the training passages change student quality across languages | https://arxiv.org/abs/2401.04810 , §5.1 to §5.2 | v1 2024-01-09 | VERIFIED_SYNTHESIS |
| C25 | OOD-DiskANN (Jaiswal et al.): data-dependent ANN indexes lose much of their advantage for out-of-distribution queries, latency an order of magnitude worse at a fixed recall target; a 1 percent query sample at build time recovers most of it | https://arxiv.org/abs/2211.12850 , abstract | v1 2022-10-22; v2 2022-11-30 | VERIFIED_SYNTHESIS |
| C26 | Cross-lingual alignment with MoE routers (Bandarkar et al.): auxiliary KL on mean-pooled routing weights over parallel data during continued pretraining | https://arxiv.org/abs/2610.01921 , §1 | v1 2026-10-01; v2 2026-10-02 | VERIFIED_SYNTHESIS |
| C27 | Retrieval heads (Wu et al.): less than 5 percent of attention heads are retrieval heads | https://arxiv.org/abs/2404.15574 , abstract | v1 2024-04-24 | VERIFIED_SYNTHESIS |
| C28 | xMRC (Gao et al.): the cross-lingual context-retrieval bottleneck lies at the last model layers | https://arxiv.org/abs/2504.10906 , abstract | v1 2025-04-15; v2 2025-10-18 | VERIFIED_SYNTHESIS |
| C29 | Mind the Cap (Goyal and Ray): the measured multilingual gap swings by up to 57 points across output budgets | https://arxiv.org/abs/2608.04160 , abstract | v1 2026-08-04 | VERIFIED_SYNTHESIS |
| C30 | LatentIndex (Wang et al.): head-wise attention-mass recall against native DSA, up to 3.28 points over IndexCache; English benchmarks | https://arxiv.org/abs/2610.04635 , abstract | v1 2026-10-03 | VERIFIED_SYNTHESIS |
| C31 | NoLiMa (Modarressi et al.): removing literal overlap collapses long-context retrieval | https://arxiv.org/abs/2502.05167 , abstract | v1 2025-02-07; v3 2025-07-09 | VERIFIED_SYNTHESIS |
| C32 | No per-language indexer or selection analysis in DeepSeek-V4, DeepSeek-V4.1-Flash, MiniMax Sparse Attention, GLM-5 or LongCat LSA; LongCat reports only short-context CMMLU and C-Eval parity | https://arxiv.org/abs/2606.19348 ; https://arxiv.org/abs/2609.19969 ; https://arxiv.org/abs/2606.13392 ; https://arxiv.org/abs/2602.15763 ; https://arxiv.org/abs/2608.01662 | 2026-02-17 to 2026-09-17 | CELL_READ (frontier full text; kill-shot abstracts only) |
| C33 | SeerAttention-R extends the frozen self-distilled gate to long reasoning; English and reasoning benchmarks | https://arxiv.org/abs/2506.08889 | v1 2025-06-10 | CELL_READ |
| C34 | LOCOS (Gema et al.): non-literal retrieval heads found on English benchmarks only; asks practitioners to re-validate on target languages | https://arxiv.org/abs/2607.01002 | v1 2026-07-01 | CELL_READ |
| C35 | Parallel-data alignment of MoE routers also in SARA, RA-MoE and Multilingual Routing in MoE | https://arxiv.org/abs/2606.25821 ; https://arxiv.org/abs/2605.28306 ; https://arxiv.org/abs/2510.04694 | 2025-10-06 to 2026-09-30 | CELL_READ |
| C36 | Parallel data has limited effect on shared multilingual representations in controlled pretraining | https://arxiv.org/abs/2603.29026 | v1 2026-03-30 | ABSTRACT_ONLY |
| C37 | SAS trains a selector end-to-end with the LM loss instead of attention distillation | https://arxiv.org/abs/2609.13141 | v1 2026-09-11 | CELL_READ |
| C38 | KV-CoRE: key-cache effective rank varies more across 15 languages than across 5 English domains | https://arxiv.org/abs/2602.05929 , §4.2.1 | v1 2026-02-05; v2 2026-02-07 | CELL_READ |
| C39 | Quantization harms non-Latin-script languages most; 1.7 percent automatic vs 16.0 percent human drop for Japanese | https://arxiv.org/abs/2407.03211 , abstract | v1 2024-07-03; v2 2024-10-12 | CELL_READ |
| C40 | OneRuler (Kim et al.): instruction-versus-context language moves results by up to 20 percent | https://arxiv.org/abs/2503.01996 , abstract | v1 2025-03-03; v3 2025-09-30 | CELL_READ |
| C41 | R^2k (Wang et al.): the minimal embedding dimension for exact top-k retrieval is Θ(k) | https://arxiv.org/abs/2601.20844 , abstract | v1 2026-01-28; v3 2026-06-02 | CELL_READ |
| C42 | Luan et al.: low-dimensional fixed-length encodings have limited capacity for precise lexical matching | https://arxiv.org/abs/2005.00181 , §2 to §3 | v1 2020-05-01; v3 2021-02-16 | CELL_READ |
| C43 | Non-canonical tokenization robustness does not carry over from English; more fragmented languages are more sensitive | https://arxiv.org/abs/2607.26831 , abstract | v1 2026-07-29 | CELL_READ (abstract) |
| C44 | OPTICAL: optimal-transport distillation transfers a monolingual retriever to low-resource cross-lingual retrieval with bitext only | https://arxiv.org/abs/2301.12566 , abstract | v1 2023-01-29 | CELL_READ |
| C45 | MGAL: parallel multilingual long-context benchmark, monolingual per language, no selection component | https://arxiv.org/abs/2608.20853 | v1 2026-08-21 | CELL_READ |
| C46 | Belebele at 7899cdfa (CC-BY-SA-4.0); FineWeb-2 at af9c1333 and FineWeb at 9bb295dd (ODC-By-1.0); ParaDocs at f80095af (Apache-2.0 packaging); the ParaDocs filter tool at 88f4ed95 has no LICENSE file | https://huggingface.co/datasets/facebook/belebele/tree/7899cdfa4e1e0d733fd77c848e2c273cb1d32be2 ; https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/tree/af9c13333eb981300149d5ca60a8e9d659b276b9 ; https://huggingface.co/datasets/HuggingFaceFW/fineweb/tree/9bb295ddab0e05d785b879661af7260fed5140fc ; https://huggingface.co/datasets/jhu-clsp/paradocs/tree/f80095affa44545d18d0d64a574f9b8679017196 ; https://github.com/rewicks/ParaDocs/tree/88f4ed95dadc577605e775ad447eefde5229d611 | 2026-10-07 fetch | FIRST_PARTY; VERIFIED_REPO (v2 data-source table) |

Correction against the cells: the kill-shot cell read C19 as evidence that
Qwen3-0.6B-Base multiple-choice ability is near chance. The same table gives
CMMLU 53.38 and C-Eval 54.90 against a 4-way chance of 25. Only ARC-C (33.45)
and its Chinese translation (30.97) are near chance. The H2a risk below is
therefore stated as uncertain, not likely.

## Closest Prior Work

The three discovery cells (frontier, kill-shot, cross-domain) are merged here
by mechanism, not by wording.

| Mechanism cluster | What the cells found | Merged bearing on K1 v2 |
|---|---|---|
| A. KL-distilled block or token selectors on a frozen backbone | SeerAttention 2024 is the origin, with a max-pool target (C09; frontier); SeerAttention-R (C33); SpotAttention (C12); Oracle-Guided (C08); DSA warm-up (C11); QSA Stage 1 (C10); A.X K2 adds a sparse-selection KL variant (C13) | Baseline component: no novelty claimed. SeerAttention was missing from every program file and is added here. Claim boundary: Stage-1-type indexers only (C10, C21). |
| B. Approximate selector scored against an exact or oracle reference | Oracle-Guided splits oracle, indexer and realization gaps on task quality (C08); LatentIndex scores head-wise attention-mass recall (C30); OOD-DiskANN scores approximate against exact top-k recall under query distribution shift (C25); Translate-Distill compares a distilled student with its teacher across languages in IR (C24) | Narrows the measurement itself: indexer-versus-reference recall, and student-versus-teacher gaps across languages, are established practice. K1's remaining delta is the object (in-model block selection judged against its own dense target), a difference-in-differences against an equally non-literal same-language question, the literal ceiling and the matched achieved budget. |
| C. Cross-lingual audits of selectors and compressors | Lost in Compression (C14) and XProvence (C15) sit outside the model; the gap tracks supervision language and is rate-dependent. Also KV-CoRE (C38), quantization (C39), hybrid attention (C16), Mind the Cap (C29) | Narrows the "first cross-lingual selector audit" framing. Raises the prior for a small xi, because the K1 indexers train on a 10-language stream with 7 bilingual pairs. Adds identification inputs: budget binding by script and a single budget point. |
| D. Dense cross-lingual long-context behaviour | MLNeedle (C17), OneRuler (C40), MGAL (C45), xMRC (C28), retrieval and transition heads (C22, C27), LAReQA weak versus strong alignment (C23) | Motivation only. Identification notes: late-layer bottleneck versus the 28-layer mean, head dilution in head-summed targets, and weak alignment only (the haystack is always in the needle's language). |
| E. Remedy-stage priors (outside this screen) | MoE-router parallel alignment, four priors (C26, C35); causal-evidence supervision (C20); SAS (C37); OPTICAL (C44); limited utility of parallel data (C36) | Narrows the D21 alignment remedy (RQ3) beyond the dossier's verdict. Its remaining delta is the object (an in-context attention selector) and the label (sentence alignments in concatenated bilingual documents). Not tested by K1. |
| F. Internal evidence (kill-shot) | Smoke headroom (E1), simulations (E3), NEGATIVE region code (E5), script exposure (E4), dedup coverage (C06), budget (E2) | Not prior art; these set the feasibility and identification defects in the next sections. |

The three closest works:

1. **Oracle-Guided Sparse Prefill** (https://arxiv.org/abs/2606.07703 , Wang
   et al., v1 2026-06-05) is the closest single mechanism.
   - What it does: a frozen backbone; a reference top-k selector built from
     head-averaged dense attention mass; a learned head-collapsed indexer
     KL-distilled to the same distribution; and an error decomposition into
     oracle gap, indexer gap and realization gap. All are measured on task
     quality, monolingually.
   - Shared with K1: a frozen backbone, KL distillation to the model's own
     attention, and a reference that separates selector error from what the
     budget alone loses.
   - Delta: K1 measures per-prompt evidence-selection recall rather than task
     quality. Its contrast is cross-script against same-language non-literal
     questions, as a difference-in-differences against the target's own gap.
     It adds a literal ceiling, a random floor and dense headroom gates.
   - Its Table 9 also shows a 0.8B KL indexer within 0.6 points of dense on
     English RULER-32K at top-k 1,024. That is the outcome that makes the
     terminal HOLD branch likely in K1 (E3).
   - The anonymized mechanism paragraphs for the blind discrimination are in
     the bundle (`blind/`).
2. **Lost in Compression** (https://arxiv.org/abs/2608.26175 , Lukauskas, v1
   2026-07-27) is the closest cross-lingual audit.
   - What it does: parallel Belebele items in ten languages and five scripts,
     with budgets matched in the target tokenizer, auditing selectors outside
     the model.
   - Delta: K1's selector is inside the model and judged against its own dense
     attention. K1's question and needle languages differ; in this audit they
     never do.
   - Its finding that the gap tracks the selector's supervision language
     predicts a small xi for K1's multilingually trained indexers.
3. **XProvence** (https://arxiv.org/abs/2601.18886 , Mohamed et al., v1
   2026-01-26) is the closest published test of a learned selector under a
   query/context language mismatch.
   - What it does: a reranker-based sentence pruner, robust under the
     mismatch.
   - Delta: K1's selector is an attention indexer inside the LM, at the block
     level, with a dense-target reference.
   - It points the same way as Lost in Compression: toward a NEGATIVE-sized
     effect.

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---:|
| Detached block indexer KL-distilled from a frozen layer's head-sum or max-pool block attention (arms hs, mp) | SeerAttention https://arxiv.org/abs/2410.13276 ; QSA https://arxiv.org/abs/2608.30320 ; DSA https://arxiv.org/abs/2512.02556 ; SpotAttention https://arxiv.org/abs/2606.22874 | yes | none claimed; this is the re-implemented baseline | 0.95 |
| Indexer-versus-own-dense-target selection recall with random, union and literal references | Oracle-Guided https://arxiv.org/abs/2606.07703 (oracle versus indexer gap, task quality); LatentIndex https://arxiv.org/abs/2610.04635 (attention-mass recall); OOD-DiskANN https://arxiv.org/abs/2211.12850 (approximate versus exact top-k recall) | partly | per-prompt needle-selection recall at a matched achieved budget, reported per language, direction, layer and position | 0.55 |
| Difference-in-differences across question language with both legs non-literal (MN versus CX), crossed over 14 cross-script pairs, with a scale-free co-statistic | Translate-Distill https://arxiv.org/abs/2401.04810 (student versus teacher across languages, IR); Lost in Compression https://arxiv.org/abs/2608.26175 (same-language queries, outside the model); XProvence https://arxiv.org/abs/2601.18886 (mismatch, outside the model) | no | the subtraction of the dense target's own cross-lingual gap, inside the model, with the literal-versus-semantic confound removed by construction | 0.6 |
| Dense headroom and parametric-recall gates for a selection statistic (H1, H2a, H2b with needle-absent twins) | MLNeedle https://arxiv.org/abs/2408.10151 ; OneRuler https://arxiv.org/abs/2503.01996 (dense behavioural baselines) | partly | design element, not claimed as novelty | 0.5 |

Merged kill-shot verdict: **NARROWED.** The core measurement cell remains
STILL_OPEN. By cell:

- frontier: STILL_OPEN;
- kill-shot: STILL_OPEN on novelty, with feasibility and identification
  defects;
- cross-domain: STILL_OPEN, with the framing narrowed by Translate-Distill,
  LAReQA, Lost in Compression and XProvence.

No cell found a direct-prior match: nothing found measures whether a
KL-distilled in-model selector loses more evidence recall than its own dense
target under a cross-script question.

Novelty wording: No direct prior art found through 2026-10-07 under the
coverage listed here:

- 157 orx discover queries (frontier 77, kill-shot 40, cross-domain 40,
  including one cross-domain query that returned an error and no ids) and 2
  WebSearch queries, all listed below with their returned ids;
- full-text reads of the closest priors by the cells (frontier 35 plus 2
  report reads, kill-shot 16, cross-domain 18 plus 5 OpenAlex metadata
  records) and by synthesis (26 full texts, digests in the query log);
- arXiv version histories checked by the frontier cell for 38 ids, and by
  synthesis through hashed snapshots of 44 arXiv abstract pages.

This is a bounded statement about the stated coverage, not a global novelty
claim. The blind closest-prior discrimination and the novelty refuter have not
run.

Required query types (rule: at least six per candidate). The union of the
cells' queries meets the rule except for one title-phrase query:

- keyword with the mechanism's exact terms: F-Q1, F-Q2, F-Q4, F-Q37, F-Q57,
  K-2 and K-16;
- keyword with closest-prior title phrases:
  - Oracle-Guided Sparse Prefill: F-Q9 and K-6;
  - SeerAttention: F-Q48;
  - Lost in Compression: F-Q23 and K-4;
  - Multilinguality in Hybrid Attention LLMs: F-Q22 and K-5;
  - Cross-Lingual Alignment with MoE Routers: F-Q29 and K-7;
  - SpotAttention: F-Q10;
  - Translate-Distill: X-Q2;
  - LAReQA: X-Q4 and X-Q30;
  - OOD-DiskANN: X-Q37 (error) and X-Q39;
- embedding with the mechanism paragraph: F-Q6, F-Q36 and K-8;
- openalex: F-Q8, F-Q50 and K-14.

Gap: no title-phrase query for XProvence. It was surfaced by F-Q73 and F-Q75
and read in full.

PRISMA-style counts, from the cell reports and not de-duplicated across
cells: frontier about 744 identified, about 120 screened and 35 included;
kill-shot 423, about 35 and 16; cross-domain 23 included. Synthesis re-read
26.

Query listing. F = frontier, K = kill-shot, X = cross-domain. The exact
strings and returned ids are listed below; the hashed artifact is
`query-log.json` in the bundle.

Listing conventions: one line per call; tool flags as run; strings containing angle brackets or a URL scheme are shown with braces and without the scheme (the hashed query-log.json is exact). Returned ids follow the arrow.

Frontier cell:

- F-Q1 (orx discover keyword --limit 10): lightning indexer cross-lingual → 2608.01662, 2608.pretraining-fails-cross-lingual-knowledge, 2610.01921, 2609.19291, 2609.23231, 2607.28449, 2603.12201, 2606.24579, 2605.07363, 2606.06586
- F-Q3 (orx discover keyword --limit 15): DeepSeek Sparse Attention multilingual languages → 2609.19969, 2606.09079, 2606.19348, 2606.13392, 2610.04635, 2610.03367, 2609.30739, 2607.10371, 2609.08515, 2605.12623, 2605.18239, 2512.02556, 2605.26002, 2608.07727, 2606.19746
- F-Q5 (orx discover keyword --limit 15 --published-after 2025-06-01): top-k token selection non-English languages long context → 2610.07247, 2609.08450, 2609.39001, 2610.04162, 2607.27692, 2610.08463, 2608.11786, 2609.29828, 2609.22943, 2609.35869, 2607.29279, 2610.04295, 2608.07629, 2609.17888, 2609.34447
- F-Q4 (orx discover keyword --limit 15): sparse attention cross-lingual needle in a haystack → 2610.00973, 2608.01662, 2610.00348, 2609.35378, 2606.06467, 2609.23231, 2609.03085, 2607.02303, 2603.28458, 2605.07363, 2608.09095, 2608.27580, 2605.28640, 2606.24579, 2508.02124
- F-Q2 (orx discover keyword --limit 15): sparse attention indexer multilingual → 2605.07363, 2610.04635, 2607.11976, 2608.01662, 2607.24593, 2606.13392, 2606.09079, 2609.26368, 2608.07009, 2609.13205, 2603.12201, 2609.08450, 2606.06467, 2610.06801, 2603.28458
- F-Q8 (orx discover openalex --limit 15): sparse attention indexer cross-lingual retrieval long context → 10.17863/cam.30462, W7166902776, 10.1613/jair.4762, 10.1613/jair.1.11640, 10.18653/v1/2024.wikinlp-1.3, 10.18653/v1/2025.findings-emnlp.612, 10.1007/978-3-030-15712-8_34, 10.48550/arxiv.2510.07812, 10.18653/v1/2025.findings-emnlp.575, 10.18653/v1/2022.findings-naacl.142, 10.18653/v1/2022.emnlp-main.203, 10.6084/m9.figshare.3204040, 10.18653/v1/2026.acl-long.692, 10.48550/arxiv.2303.14991, 10.18653/v1/p17-1130
- F-Q6 (orx discover embedding --limit 20): A small learned indexer is distilled by KL divergence from a frozen language model's own attention to select the top-k key blocks for sparse attention. We measure whether this indexer loses more recall of the relevant passage than the dense model's own top-k attention when the question is written in a different script or language from the passage, at a matched token budget. → 2610.02875, 2609.37879, 2610.00694, 2609.34063, 2608.23296, 2609.38261, 2609.32579, 2608.27128, 2608.25230, 2609.13415, 2608.27760, 2608.03796, 2606.22874, 2609.18989, 2607.21692
- F-Q7 (orx discover embedding --limit 20): multilingual evaluation of sparse attention and KV cache compression methods on non-English long-context retrieval → 2610.06686, 2610.02953, 2610.00412, 2609.12913, 2608.00528, 2607.17715, 2609.13205, 2607.06519, 2606.24467, 2608.26175, 2607.06523, 2605.05971, 2603.22910, 2603.16435, 2607.05399
- F-Q10 (orx discover keyword --limit 10): SpotAttention selector frozen backbone → 2606.22874, 2608.19743, 2606.14153, 2609.24441, 2608.09124, 2608.07982, 2609.30751, 2609.03265, 2608.28316, 2609.33407
- F-Q11 (orx discover keyword --limit 15): KV cache compression multilingual non-English degradation → 2609.19969, 2610.06479, 2609.32831, 2609.03235, 2609.36322, 2609.37988, 2610.02815, 2610.02953, 2609.24298, 2609.35621, 2610.03198, 2610.06286, 2610.03027, 2609.07966, 2609.22158
- F-Q9 (orx discover keyword --limit 10): Oracle-Guided Sparse Prefill → 2606.07703, 2609.20971, 2609.26368, 2610.06917, 2608.19758, 2609.26333, 2609.33252, 2609.32259, 2605.16839, 2610.06801
- F-Q13 (orx discover keyword --limit 15): attention sparsity across languages → 2609.08690, 2609.19702, 2608.18545, 2609.20888, 2609.31967, 2609.20005, 2609.01788, 2606.18056, 2609.00097, 2610.03367, 2609.05910, 2609.33889, 2605.15508, 2608.03507, 2608.27848
- F-Q12 (orx discover keyword --limit 15): KV cache eviction multilingual languages → 2608.28293, 2609.03430, 2610.07643, 2610.06286, 2610.03007, 2610.06996, 2609.27981, 2609.08131, 2608.23296, 2609.23314, 2609.27470, 2609.06663, 2610.06479, 2610.03198, 2608.01247
- F-Q14 (orx discover keyword --limit 15 --published-after 2025-01-01): multilingual needle in a haystack benchmark → 2610.00973, 2610.00348, 2609.20945, 2609.03085, 2609.23490, 2609.34752, 2610.06339, 2609.01056, 2608.20853, 2609.02379, 2608.27580, 2607.02956, 2606.25343, 2604.20347, 2608.28641
- F-Q17 (orx discover keyword --limit 10): MLNeedle multilingual needle → 2408.10151, 2610.00348, 2609.18546, 2607.26337, 2604.20347, 2608.23037, 2608.27620, 2608.08201, 2607.25180, 2608.03559
- F-Q15 (orx discover keyword --limit 15): cross-lingual long-context retrieval benchmark needle different language → 2609.23231, 2608.21714, 2610.02875, 2609.38958, 2608.12820, 2606.24467, 2606.13100, 2606.24579, 2607.06008, 2607.06523, 2607.11215, 2606.24610, 2606.22910, 2606.18033, 2605.27243
- F-Q16 (orx discover keyword --limit 10): OneRuler multilingual long-context → 2608.20853, 2609.36218, 2503.01996, 2609.40181, 2604.20720, 2610.08463, 2605.12227, 2606.27306, 2608.10359, 2608.18474
- F-Q23 (orx discover keyword --limit 10): Lost in Compression cross-lingual audit extractive prompt compressors → 2608.26175, 2607.25335, 2609.14245, 2608.04569, 2609.23231, 2609.15184, 2609.32474, 2608.27848, 2610.06093, 2605.26596
- F-Q21 (orx discover openalex --limit 15): cross-lingual needle in a haystack → 10.48550/arxiv.2408.10151, 10.1145/2783258.2788580, 10.48550/arxiv.2604.18835, 10.18653/v1/2025.naacl-long.267, 10.18653/v1/2023.eacl-main.75, 10.1016/j.ajodo.2019.01.018, 10.18653/v1/2023.acl-long.524, 10.48550/arxiv.2208.05309, 10.48550/arxiv.2305.10266, 10.3233/ida-227347, 10.48550/arxiv.2207.01054, 10.48550/arxiv.2601.04036, W7119557247, 10.1145/3764112, 10.18653/v1/2025.acl-long.778
- F-Q22 (orx discover keyword --limit 10): Multilinguality in Hybrid Attention LLMs → 2609.35378, 2608.28383, 2609.26368, 2608.17088, 2608.30310, 2609.20751, 2609.32114, 2608.12149, 2610.08527, 2608.27875
- F-Q18 (orx discover embedding --limit 20): long-context benchmark where the question is in one language and the relevant passage (needle) is in another language, measuring cross-lingual retrieval inside the context window of large language models → 2610.00606, 2609.20945, 2608.21714, 2608.27481, 2606.15345, 2605.07249, 2605.27649, 2604.21096, 2601.20276, 2502.05167, 2511.14774, 2503.01996, 2509.13930, 2507.22411, 2504.10906
- F-Q20 (orx discover openalex --limit 15): multilingual long-context language models needle haystack benchmark → 10.18653/v1/2025.naacl-long.267, 10.48550/arxiv.2408.10151, 10.48550/arxiv.2503.01996, 10.48550/arxiv.2504.12845, 10.18653/v1/2026.eacl-long.290, 10.48448/dfmq-2b42, 10.18653/v1/2025.acl-long.1162, 10.48550/arxiv.2411.19360, 10.18653/v1/2025.codi-1.1, 10.52202/085713-2939, 10.18653/v1/2024.mrl-1.18, 10.48550/arxiv.2409.18006, 10.18653/v1/2024.emnlp-main.552, 10.15760/etd.4098, W7142582410
- F-Q19 (orx discover embedding --limit 20 --published-after 2025-06-01): multilingual long-context benchmark across many languages measuring needle retrieval degradation in low-resource languages → 2609.23416, 2609.20945, 2609.09349, 2608.20853, 2608.21714, 2608.02189, 2608.03803, 2607.23058, 2607.17173, 2606.15345, 2606.24200, 2607.00171, 2606.15643, 2605.07249, 2605.24556
- F-Q28 (orx discover keyword --limit 15): retrieval heads multilingual cross-lingual → 2609.23231, 2610.06216, 2610.02875, 2608.12820, 2608.21714, 2609.05976, 2608.22363, 2606.24579, 2608.26357, 2602.22453, 2606.06586, 2605.31171, 2606.24200, 2605.26575, 2604.05684
- F-Q29 (orx discover keyword --limit 10): Cross-Lingual Alignment for Decoder-Only Models using MoE Routers → 2610.01921, 2608.27115, 2609.06381, 2609.15184, 2609.30535, 2608.23149, 2609.19398, 2608.27867, 2609.12855, 2606.26466
- F-Q27 (orx discover keyword --limit 10): Understanding LLMs Cross-Lingual Context Retrieval → 2609.23231, 2609.21722, 2608.pretraining-fails-cross-lingual-knowledge, 2609.19291, 2610.01921, 2609.07687, 2608.21714, 2608.12820, 2609.27376, 2608.26357
- F-Q25 (orx discover embedding --limit 20 --published-before 2026-01-01): efficient attention and token eviction methods evaluated on multilingual long-context tasks show larger losses for languages other than English → 2512.10772, 2512.24410, 2510.19546, 2510.20647, 2505.20276, 2505.22888, 2507.00246, 2504.17720, 2509.05486, 2507.19699, 2504.20022, 2503.04360, 2406.14670, 2407.03211, 2502.12476
- F-Q24 (orx discover embedding --limit 20): KV cache compression or sparse attention disproportionately degrades non-English and low-resource languages; multilingual analysis of efficient inference methods → 2609.38106, 2608.19670, 2608.11786, 2608.26175, 2607.24276, 2606.21869, 2606.08451, 2608.09941, 2604.16656, 2603.21036, 2510.00231, 2602.05929, 2601.12033, 2601.13328, 2509.25138
- F-Q26 (orx discover openalex --limit 15): KV cache compression multilingual → 10.48550/arxiv.2410.15252, 10.48550/arxiv.2609.19969, 10.48550/arxiv.2607.06827, 10.21203/rs.3.rs-10297225/v1, 10.48550/arxiv.2606.14782, 10.18653/v1/2025.findings-emnlp.426, 10.48550/arxiv.2502.01941, W7161354758, 10.5753/sbbd.2025.247245, 10.18653/v1/2026.acl-long.1811, 10.48550/arxiv.2609.33334, 10.48550/arxiv.2511.16786, 10.18653/v1/2026.findings-acl.494, 10.5281/zenodo.21514619, 10.48550/arxiv.2602.05929
- F-Q31 (orx discover keyword --limit 15): parallel data auxiliary alignment loss attention decoder-only → 2610.01921, 2609.12855, 2609.11020, 2607.24439, 2607.25948, 2607.13929, 2605.31432, 2607.26164, 2607.18363, 2608.17913, 2606.17410, 2606.03967, 2606.24147, 2602.10622, 2604.09389
- F-Q33 (orx discover keyword --limit 15 --published-after 2025-06-01): cross-lingual attention alignment parallel sentences LLM → 2608.27115, 2610.01921, 2609.06381, 2608.23149, 2609.30535, 2609.15184, 2608.pretraining-fails-cross-lingual-knowledge, 2608.23390, 2609.05976, 2610.07524, 2608.28860, 2609.09953, 2609.23231, 2609.35378, 2609.19291
- F-Q35 (orx discover keyword --limit 10): AlignAtt alignment heads LLM translation → 2606.03967, 2606.23885, 2609.37991, 2608.27161, 2609.35225, 2609.07568, 2602.04613, 2610.05999, 2606.03948, 2608.30065
- F-Q34 (orx discover openalex --limit 15): supervised attention alignment parallel corpus neural machine translation guided alignment → 10.18653/v1/2020.emnlp-main.42, 10.1109/taslp.2021.3138719, 10.48550/arxiv.2103.17250, 10.5715/jnlp.27.531, 10.24963/ijcai.2022/587, 10.18293/seke2023-165, 10.48550/arxiv.2004.14837, 10.18653/v1/2021.emnlp-main.1, 10.18653/v1/2021.emnlp-main.664, 10.18653/v1/w17-4716, 10.18653/v1/2022.emnlp-main.689, 10.18653/v1/w17-3204, 10.48550/arxiv.2210.06716, 10.63317/4ggtazzyrfq2, 10.48550/arxiv.2012.07162
- F-Q32 (orx discover keyword --limit 15): supervised attention word alignment guided alignment loss → 2608.28508, 2608.18474, 2610.05306, 2609.34467, 2609.15150, 2609.05913, 2609.27413, 2608.21023, 2608.27950, 2609.38925, 2606.10675, 2609.12855, 2607.07230, 2608.25493, 2607.23944
- F-Q30 (orx discover embedding --limit 20): Train the top-k sparse-attention indexer of a decoder-only language model with an auxiliary loss on concatenated bilingual parallel documents so that query tokens in one language select the aligned sentence of the translation; supervision from corpus sentence alignments, main attention left untouched, evaluated on held-out languages → 2610.01921, 2608.04904, 2603.29026, 2603.24258, 2601.04768, 2601.10310, 2510.27254, 2503.06394, 2401.05811, 2401.04810, 2311.08089, 1911.01464, 2101.08231, 2210.06633, 2406.13195
- F-Q40 (orx discover openalex --limit 15 --published-after 2025-06-01): trainable sparse attention learned indexer distillation pretrained model → 10.48550/arxiv.2511.20102, 10.48550/arxiv.2607.10762, 10.48550/arxiv.2606.22874, 10.48550/arxiv.2606.13392, 10.48550/arxiv.2609.34044, 10.1109/tai.2025.3636862, 10.1145/3726302.3730185, 10.1021/acs.jmedchem.5c02620, 10.48550/arxiv.2603.22008, 10.48550/arxiv.2605.18753, 10.48550/arxiv.2603.23032, 10.48550/arxiv.2604.00004, 10.48550/arxiv.2512.08829, 10.48550/arxiv.2605.16928, 10.48550/arxiv.2608.16585
- F-Q37 (orx discover keyword --limit 15): indexer KL distillation frozen backbone attention distribution → 2606.20005, 2610.00317, 2609.33791, 2606.09079, 2608.25643, 2610.04635, 2606.07703, 2609.39319, 2610.02188, 2609.33407, 2609.33200, 2609.34581, 2607.19358, 2605.07363, 2608.01662
- F-Q39 (orx discover keyword --limit 15): Qwen sparse attention compressed block indexer max-pool → 2605.07363, 2609.22884, 2606.13392, 2607.09052, 2609.31093, 2610.04635, 2606.09079, 2608.07009, 2608.30320, 2610.08527, 2607.24593, 2607.11976, 2609.13205, 2609.26368, 2605.02568
- F-Q41 (orx discover keyword --limit 15): indexer recall dense attention top-k oracle selection error → 2610.04635, 2606.07703, 2609.08450, 2607.27692, 2607.24593, 2605.02568, 2610.06801, 2608.12780, 2607.11976, 2605.07363, 2609.13134, 2609.20734, 2609.32712, 2608.07009, 2604.22312
- F-Q38 (orx discover keyword --limit 15): indexer target retrieval heads distillation sparse attention → 2605.07363, 2609.39319, 2609.26368, 2608.01662, 2610.04635, 2606.13392, 2606.09079, 2607.11976, 2605.16928, 2608.06849, 2609.13205, 2608.03555, 2607.24593, 2608.27417, 2609.32704
- F-Q36 (orx discover embedding --limit 20 --published-after 2025-09-01): Retrofit a pretrained dense transformer with a lightweight learned token or block selector trained by KL divergence against the model's own aggregated attention distribution while the backbone stays frozen, then use top-k selection for sparse attention → 2609.13141, 2609.34650, 2610.07809, 2610.00426, 2609.34063, 2608.23296, 2609.32124, 2605.23872, 2609.30288, 2608.08853, 2606.22874, 2607.07724, 2605.26797, 2606.10722, 2604.05248
- F-Q43 (orx discover keyword --limit 15 --published-after 2025-09-01): mixture of block attention MoBA → 2511.11571, 2609.38428, 2609.31093, 2610.08527, 2609.22884, 2609.31261, 2609.38832, 2609.38978, 2606.13392, 2603.15619, 2605.09516, 2608.19758, 2607.09052, 2605.07363, 2608.01934
- F-Q45 (orx discover embedding --limit 20): sparse attention token budget and tokenizer fertility: languages that need more tokens per word lose more under a fixed top-k token budget → 2609.39001, 2610.01763, 2608.21541, 2608.12150, 2608.04160, 2607.24276, 2607.15232, 2608.26175, 2608.00582, 2608.21384, 2607.16117, 2609.00378, 2606.24460, 2606.28560, 2606.15044
- F-Q42 (orx discover keyword --limit 15): multilingual routing mixture-of-experts cross-lingual router alignment → 2610.01921, 2610.06216, 2609.36301, 2606.25821, 2609.24058, 2609.34634, 2610.02875, 2609.37751, 2609.02293, 2609.18176, 2609.02404, 2605.28306, 2610.04140, 2610.06677, 2608.07890
- F-Q44 (orx discover keyword --limit 15): native sparse attention NSA multilingual → 2609.38832, 2607.09052, 2606.13392, 2502.11089, 2608.07009, 2607.02980, 2510.02295, 2608.01662, 2609.31093, 2610.05416, 2610.04635, 2605.18753, 2508.18224, 2609.32882, 2604.21221
- F-Q46 (orx discover embedding --limit 20 --published-after 2025-06-01): learned token selector or router in a language model fails to transfer across languages; selection recall drops for queries in a different language from the evidence → 2608.25832, 2608.pretraining-fails-cross-lingual-knowledge, 2610.02762, 2609.19291, 2609.37104, 2609.01341, 2608.23023, 2608.11146, 2608.08032, 2609.27758, 2608.06506, 2608.02486, 2607.08731, 2607.04814, 2606.01196
- F-Q47 (orx discover openalex --limit 15 --published-after 2025-01-01): sparse attention multilingual evaluation language models → 10.5281/zenodo.20637041, 10.3390/electronics15071395, 10.48550/arxiv.2511.07498, 10.48550/arxiv.2601.02819, 10.1007/s11704-024-40579-4, 10.1016/j.ipm.2026.104627, 10.48550/arxiv.2504.07072, 10.7488/era/7299, 10.62311/nesx/rb14ag-978-81-68314-86-3, 10.48550/arxiv.2605.23036, 10.18653/v1/2026.trustnlp-main.24, 10.48550/arxiv.2605.26002, 10.21203/rs.3.rs-10218350/v1, 10.48550/arxiv.2501.05478, W7212200699
- F-Q52 (orx discover keyword --limit 10): Routing Absorption sparse attention random gates → 2603.02227, 2609.22884, 2609.20974, 2606.06467, 2609.31093, 2609.27373, 2606.13392, 2609.27150, 2608.11519, 2609.01925
- F-Q50 (orx discover openalex --limit 10): SeerAttention learning intrinsic sparse attention in your LLMs → 10.48550/arxiv.2410.13276, 10.48550/arxiv.2609.13205, 10.48550/arxiv.2602.05191, 10.48550/arxiv.2609.38830, 10.18653/v1/2025.acl-long.1126, 10.48550/arxiv.2605.07363, 10.48550/arxiv.2505.19578, 10.48550/arxiv.2510.13602, 10.48550/arxiv.2603.06274, 10.18653/v1/2026.findings-acl.348
- F-Q53 (orx discover keyword --limit 10): RTPurbo Full Attention Strikes Back retrieval subspace → 2605.16928, 2609.30601, 2609.31947, 2609.38978, 2609.32704, 2608.12780, 2608.24971, 2609.37879, 2607.02980, 2609.33913
- F-Q51 (orx discover embedding --limit 20): learnable gate predicts block-level attention sparsity, trained by self-distillation from the pooled attention map of the frozen pretrained model → 2609.13141, 2609.34650, 2608.23296, 2609.22005, 2609.10287, 2608.15787, 2608.06776, 2607.21692, 2606.30139, 2605.05222, 2602.01468, 2602.04784, 2511.18670, 2410.13276, 2510.13876
- F-Q48 (orx discover keyword --limit 10): SeerAttention learning intrinsic sparse attention → 2410.13276, 2506.08889, 2609.31093, 2607.02980, 2609.26368, 2606.13392, 2606.25010, 2609.32882, 2609.38830, 2606.04511
- F-Q49 (orx discover keyword --limit 15): AttnGate self-distillation max-pooled attention map block sparse → 2609.31093, 2609.26368, 2608.19758, 2609.22884, 2609.33200, 2609.38978, 2606.13392, 2609.25869, 2607.09052, 2608.16585, 2610.01013, 2610.08772, 2609.13141, 2610.05416, 2610.06801
- F-Q54 (orx discover keyword --limit 15): sparse attention Belebele → 2606.13392, 2609.26368, 2610.06801, 2609.32882, 2609.24202, 2607.02980, 2609.38832, 2610.04635, 2606.04511, 2608.19920, 2610.04424, 2607.09052, 2609.13205, 2608.10519, 2604.20920
- F-Q58 (orx discover embedding --limit 20 --published-after 2026-01-01): Does DeepSeek sparse attention or a learned top-k indexer degrade multilingual or cross-lingual long-context performance compared with dense attention? → 2609.02737, 2608.01662, 2610.01139, 2610.02875, 2609.35378, 2609.37879, 2609.38530, 2609.08574, 2609.34063, 2608.23296, 2609.11913, 2609.01341, 2607.24593, 2609.13205, 2608.15061
- F-Q59 (orx discover openalex --limit 15): DeepSeek sparse attention lightning indexer → 10.48550/arxiv.2606.09079, 10.48550/arxiv.2608.01662, 10.48550/arxiv.2607.19358, W7135429492, 10.48550/arxiv.2603.12201, 10.48550/arxiv.2603.28458, 10.48550/arxiv.2605.02568, 10.48550/arxiv.2605.07363, 10.48550/arxiv.2606.13392, 10.1093/nsr/nwag212, 10.48550/arxiv.2607.24593, 10.48550/arxiv.2606.06467, 10.18653/v1/2026.findings-acl.1926, 10.48550/arxiv.2604.20920, 10.48550/arxiv.2512.03494
- F-Q55 (orx discover keyword --limit 15): lightning indexer languages Japanese Korean → 2608.01662, 2609.11772, 2606.09079, 2608.30181, 2608.05802, 2608.20840, 2605.07363, 2606.25937, 2607.10114, 2607.16777, 2607.11976, 2603.12201, 2407.19400, 2605.29414, 2603.05883
- F-Q56 (orx discover keyword --limit 15 --published-after 2026-01-01): sparse attention low-resource languages long context → 2608.19758, 2608.19920, 2606.09079, 2609.23816, 2606.04511, 2609.20971, 2609.26368, 2607.02980, 2609.13205, 2609.36529, 2609.38832, 2607.25291, 2606.13392, 2609.08450, 2607.21927
- F-Q57 (orx discover keyword --limit 15): attention mass recall indexer per language → 2610.04635, 2609.20734, 2605.07363, 2609.02737, 2607.11976, 2607.24593, 2609.32712, 2606.09079, 2609.32704, 2608.30376, 2603.12201, 2609.36835, 2605.02568, 2608.07009, 2610.02235
- F-Q60 (orx discover keyword --limit 10): GLM-5 technical report DSA → 2602.15763, 2603.10910, 2608.glm-5, 2026.glm-5-2, 2512.14291, 2606.10651, 2608.30703, 2608.26990, 2608.04505, 2607.pangram-4
- F-Q63 (orx discover embedding --limit 20): per-language analysis of which context tokens a sparse attention selector keeps, comparing English with Chinese, Japanese, Arabic and other scripts → 2609.37879, 2609.36205, 2609.08322, 2609.00325, 2608.26576, 2607.16117, 2606.01800, 2606.09335, 2605.31363, 2605.17598, 2603.00432, 2510.04694, 2601.13328, 2601.04664, 2510.03315
- F-Q62 (orx discover keyword --limit 10): sparse indexer warmup Korean long-context → 2605.07363, 2606.09079, 2608.30181, 2607.11976, 2609.13205, 2609.08450, 2607.19358, 2606.04511, 2606.06467, 2608.01662
- F-Q61 (orx discover keyword --limit 10): Kimi linear attention MoBA multilingual long context → 2607.24653, 2609.36529, 2510.26692, 2609.08574, 2502.13189, 2609.38428, 2609.36062, 2609.24797, 2608.20853, 2609.38166
- F-Q65 (orx discover keyword --limit 15): query-aware KV cache selection language mismatch query context → 2609.36722, 2609.33503, 2609.39329, 2610.03198, 2610.03135, 2610.00412, 2610.06686, 2608.01247, 2609.32831, 2608.03276, 2610.06996, 2609.22158, 2609.08131, 2609.26300, 2609.35621
- F-Q67 (orx discover openalex --limit 15): cross-lingual KV cache compression query language different from context language → 10.48550/arxiv.2609.03235, 10.52202/085713-0966, 10.18653/v1/2026.acl-long.1811, 10.48550/arxiv.2608.26175, 10.48550/arxiv.2602.05929, 10.48550/arxiv.2609.32610, 10.48550/arxiv.2406.18139, 10.18653/v1/2024.findings-emnlp.235, 10.48550/arxiv.2608.22704, 10.48550/arxiv.2511.01815, 10.26153/tsw/64320, 10.48550/arxiv.2406.13035, 10.1109/tpami.2026.3708708, 10.48550/arxiv.2307.06435, 10.48550/arxiv.2410.07590
- F-Q68 (orx discover embedding --limit 20): Token selection for long-context inference is guided by the query; when the query is in a different language from the document, attention-based token selection may miss the relevant evidence → 2609.36534, 2610.00606, 2607.21692, 2605.08234, 2605.19274, 2604.21096, 2603.27859, 2603.18446, 2603.13911, 2601.06644, 2601.16934, 2602.11841, 2601.23223, 2511.19325, 2511.01380
- F-Q69 (orx discover keyword --limit 15): head-sum versus max-pool target indexer distillation ablation → 2605.07363, 2609.34250, 2609.17284, 2609.39319, 2609.39687, 2609.10317, 2606.01920, 2607.induction-head-ablation-repetition-dynamics, 2609.30837, 2609.32704, 2609.37041, 2610.00373, 2609.39275, 2609.39338, 2607.28590
- F-Q66 (orx discover keyword --limit 10): 稀疏注意力 多语言 → 2608.08650, 2608.10021, 2608.enterprise-ai-decision-support-systems, 2608.enterprise-information-systems-lifecycle-management, 2608.ai-enterprise-lightweight-transformation, 2608.cross-border-ecommerce-systems-globalization, 2608.ai-wireless-network-penetration-testing, 2605.22064, 2607.15686, 2607.13533
- F-Q64 (orx discover keyword --limit 15): SnapKV multilingual cross-lingual question answering → 2608.22363, 2608.27481, 2609.04409, 2609.23231, 2610.06216, 2608.13160, 2609.05976, 2607.19867, 2604.20531, 2608.20757, 2606.24579, 2606.25246, 2606.21954, 2604.10590, 2606.01464
- F-Q73 (orx discover embedding --limit 20 --published-after 2025-03-01): cross-lingual long-context question answering where the document and the question are in different languages, evaluated at increasing context lengths for many languages and scripts → 2610.00606, 2609.27376, 2609.04409, 2608.21714, 2608.27481, 2606.15345, 2606.27306, 2604.05684, 2601.15337, 2601.06644, 2601.18886, 2602.01451, 2511.19325, 2601.03025, 2511.14774
- F-Q72 (orx discover openalex --limit 15 --published-after 2025-01-01): multilingual long-context benchmark cross-lingual question context different languages → 10.3390/app15147800, 10.18653/v1/2025.acl-long.404, 10.48550/arxiv.2606.01464, 10.48550/arxiv.2604.20531, W7214129258, 10.48550/arxiv.2609.05976, 10.48550/arxiv.2609.04409, 10.18653/v1/2025.findings-acl.219, 10.3390/computers15020092, 10.1145/3777415, 10.18653/v1/2025.emnlp-main.1380, 10.48550/arxiv.2504.20484, 10.18653/v1/2026.findings-acl.1367, 10.18653/v1/2025.naacl-long.267, 10.63317/29b354pejyrt
- F-Q71 (orx discover keyword --limit 15 --published-after 2025-04-01): multilingual BABILong RULER languages long context evaluation → 2608.20853, 2609.36218, 2608.03297, 2610.03367, 2609.05910, 2608.24477, 2608.19981, 2609.32312, 2607.10371, 2609.13413, 2609.35820, 2609.30739, 2609.12686, 2607.02956, 2609.02379
- F-Q70 (orx discover keyword --limit 15): multilingual NoLiMa non-literal long-context → 2607.01002, 2502.05167, 2610.08463, 2608.20853, 2605.10544, 2609.12686, 2609.36218, 2609.33485, 2609.40181, 2606.02147, 2609.38137, 2609.34781, 2609.27590, 2608.21690, 2606.29718
- F-Q77 (orx discover openalex --limit 15): attention-based in-context re-ranking cross-lingual → 10.1007/s10791-022-09406-x, 10.1109/access.2020.3041605, 10.48550/arxiv.2304.01019, 10.1109/access.2020.2999568, 10.17863/cam.30462, 10.18653/v1/d18-1269, 10.18653/v1/2023.findings-acl.109, 10.48550/arxiv.2206.07587, 10.18653/v1/2022.findings-emnlp.384, 10.1613/jair.1.11640, 10.1145/3626772.3657864, 10.1162/tacl_a_00520, 10.18653/v1/2025.findings-emnlp.612, 10.48550/arxiv.2210.13693, 10.48550/arxiv.1809.05053
- F-Q76 (orx discover keyword --limit 15): attention supervision parallel corpus cross-lingual retrieval heads training → 2610.02875, 2609.23231, 2608.27115, 2609.28826, 2609.30535, 2609.09953, 2606.22910, 2608.21714, 2608.29890, 2608.12820, 2606.06586, 2602.22453, 2605.27243, 2604.05821, 2604.20666
- F-Q75 (orx discover embedding --limit 20): use the attention scores of a decoder LLM's heads as a zero-shot retriever or re-ranker for passages in other languages; cross-lingual in-context retrieval with attention → 2607.22042, 2605.07249, 2604.24608, 2604.05821, 2604.25182, 2604.19678, 2602.12192, 2602.08625, 2602.22453, 2601.04768, 2601.18886, 2511.07498, 2510.02219, 2506.09944, 2504.10906
- F-Q74 (orx discover keyword --limit 15): query-focused retrieval heads attention re-ranking multilingual → 2608.06849, 2609.23880, 2609.34650, 2607.04043, 2605.25165, 2609.30904, 2604.24608, 2608.27417, 2506.09944, 2609.14174, 2602.22453, 2510.02219, 2609.22990, 2608.20886, 2606.25249
- F-P1 (orx paper --full): closest-prior full-text reads (35 documents) → 2606.07703, 2606.22874, 2512.02556, 2608.30320, 2608.26175, 2609.35378, 2610.01921, 2408.10151, 2503.01996, 2608.20853, 2602.22453, 2607.01002, 2410.13276, 2506.08889, 2603.02227, 2605.16928, 2609.13141, 2606.13392, 2606.19348, 2504.10906, 2610.04635, 2606.03967, 2609.19969, 2606.25821, 2608.30181, 2602.15763, 2608.04505, 2607.24653, 2510.04694, 2607.21692, 2601.18886, 2606.09079, 2608.01662, 2607.24593, 2608.glm-5
- F-P2 (orx paper (report)): abstract/report reads → 2409.18006, 2504.12845
- F-P3 (curl export.arxiv.org/abs/{id} (version history)): version-history check of every named closest prior and new hit (38 ids) → 2606.07703, 2606.22874, 2512.02556, 2608.30320, 2608.26175, 2609.35378, 2610.01921, 2408.10151, 2503.01996, 2608.20853, 2602.22453, 2607.01002, 2605.16928, 2606.03967, 2411.04986, 2603.02227, 2607.24593, 2502.11089, 2608.01662, 2606.13392, 2606.09079, 2502.05167, 2607.21692, 2601.18886, 2410.13276, 2506.08889, 2606.25821, 2605.28306, 2510.04694, 2504.10906, 2608.30181, 2609.13141, 2610.04635, 2602.15763, 2606.19348, 2609.19969, 2608.06506, 2506.09944
- F-P4 (curl export.arxiv.org/pdf/2602.22453v1 + pdftotext): diff RTH v1 against v4 for the KV-compression implication paragraph → 2602.22453v1

Kill-shot cell:

- K-1 (orx discover keyword): lightning indexer multilingual cross-lingual recall → 2609.23231, 2610.06216, 2608.01662, 2609.05976, 2606.06586, 2608.22363, 2610.01921, 2606.24579, 2608.12820, 2609.14431, 2608.26357, 2606.21954, 2606.15345, 2607.04814, 2607.11215
- K-2 (orx discover keyword): sparse attention indexer cross-script needle retrieval → 2609.26368, 2610.04635, 2608.01662, 2605.07363, 2606.06467, 2607.11976, 2603.12201, 2606.09079, 2606.13392, 2609.13205, 2603.28458, 2607.24593, 2608.03555, 2605.16928, 2609.38978
- K-3 (orx discover keyword): DeepSeek Sparse Attention non-English languages degradation → 2609.19969, 2606.09079, 2608.11786, 2610.06801, 2606.19348, 2606.13392, 2608.22363, 2610.04635, 2610.05238, 2609.24202, 2608.01662, 2609.39001, 2608.13698, 2606.04511, 2608.04433
- K-4 (orx discover keyword): Lost in Compression cross-lingual prompt compression → 2608.26175, 2609.32474, 2609.36526, 2609.15184, 2608.27848, 2609.37017, 2609.12310, 2610.06093, 2609.06076, 2609.25963
- K-5 (orx discover keyword): Multilinguality in Hybrid Attention LLMs → 2609.35378, 2608.28383, 2609.26368, 2608.17088, 2608.30310, 2609.20751, 2609.32114, 2608.12149, 2610.08527, 2608.27875
- K-6 (orx discover keyword): Oracle-Guided Sparse Prefill → 2606.07703, 2609.20971, 2609.26368, 2610.06917, 2608.19758, 2609.26333, 2609.33252, 2609.32259, 2605.16839, 2610.06801
- K-7 (orx discover keyword): Cross-Lingual Alignment with MoE Routers → 2610.01921, 2609.06381, 2608.23149, 2609.15184, 2608.27115, 2609.32581, 2608.23390, 2609.23231, 2609.19398, 2608.27867
- K-8 (orx discover embedding): Does a learned top-k sparse attention indexer distilled by KL divergence from the model's full attention lose more needle retrieval recall when the question is in a different language or script from the passage than the dense attention it imitates? → 2610.01139, 2610.02875, 2609.34063, 2608.23296, 2609.01341, 2608.25717, 2608.21462, 2607.21692, 2606.02737, 2605.24556, 2606.00356, 2604.21096, 2603.14782, 2510.26271, 2511.19324
- K-9 (orx discover keyword): KV cache compression multilingual languages degradation → 2609.19969, 2610.06479, 2609.03235, 2609.37988, 2609.32831, 2610.02953, 2609.36322, 2610.02815, 2609.24298, 2610.03198, 2609.35621, 2610.06286, 2609.07966, 2610.03027, 2609.22158
- K-10 (orx discover keyword): KV cache eviction non-English low-resource languages long context → 2610.03007, 2608.28293, 2609.03430, 2606.24467, 2610.06286, 2610.06996, 2609.08131, 2610.07643, 2610.02815, 2605.25475, 2609.37988, 2609.27470, 2610.03198, 2609.27981, 2605.09649
- K-11 (orx discover keyword): sparse attention multilingual needle in a haystack → 2610.00973, 2610.00348, 2609.31947, 2608.28444, 2609.31093, 2609.03085, 2608.01662, 2608.27580, 2607.02303, 2609.38832, 2606.13392, 2608.19758, 2603.28458, 2605.28640, 2607.02980
- K-12 (orx discover keyword): retrieval heads multilingual cross-lingual long context → 2609.23231, 2610.06216, 2608.21714, 2608.12820, 2609.05976, 2608.22363, 2608.29613, 2605.27243, 2602.22453, 2606.24579, 2607.06008, 2606.06586, 2605.31171, 2604.25182, 2606.24200
- K-13 (orx discover embedding): Multilingual evaluation of sparse attention and KV cache selection methods: token selection recall drops for non-English and cross-lingual queries in long-context retrieval → 2610.02875, 2608.01631, 2608.30996, 2608.26175, 2607.21692, 2608.12333, 2606.24200, 2608.vorn-kv-cache-eviction, 2608.09941, 2605.07249, 2605.24556, 2605.24904, 2605.08234, 2604.21096, 2602.20986
- K-14 (orx discover openalex): sparse attention indexer multilingual cross-lingual retrieval → arXiv:2510.07812, 10.18653/v1/2025.findings-emnlp.575, 10.18653/v1/2022.findings-naacl.142, 10.18653/v1/2022.acl-long.288, arXiv:2204.08887, 10.1145/3777415, 10.17863/cam.30462, W2907395836, 10.1613/jair.1.11640, 10.1007/978-3-030-15712-8_34, 10.18653/v1/2025.findings-emnlp.612, 10.18653/v1/2022.emnlp-main.597, 10.1613/jair.4762, arXiv:2207.05737, 10.18653/v1/2025.acl-long.253
- K-15 (orx discover openalex): KV cache compression multilingual long context → 10.18653/v1/2025.findings-emnlp.426, arXiv:2410.15252, 10.18653/v1/2026.acl-long.1811, arXiv:2605.31105, 10.18653/v1/2026.findings-acl.494, arXiv:2609.19969, 10.21203/rs.3.rs-10297225/v1, arXiv:2606.14782, arXiv:2607.06827, arXiv:2604.08426, arXiv:2502.01941, arXiv:2605.25085, 10.5753/sbbd.2025.247245, W7161354758, arXiv:2412.05896
- K-16 (orx discover keyword): lightning indexer KL divergence attention distillation top-k selection recall → 2609.34447, 2610.04635, 2608.01662, 2609.33791, 2606.20005, 2608.14728, 2609.08450, 2610.03529, 2610.07247, 2605.02568, 2606.09079, 2609.01532, 2603.12201, 2607.19358, 2607.27692
- K-17 (orx discover keyword --published-after 2026-06-01): multilingual long-context sparse attention evaluation languages → 2608.19758, 2608.20853, 2608.19920, 2606.09079, 2609.20971, 2609.23816, 2606.04511, 2609.26368, 2607.02980, 2609.36218, 2606.13392, 2609.36529, 2609.38832, 2607.25291, 2609.13205, 2608.01676, 2608.24477, 2610.03367, 2609.05910, 2608.20427
- K-18 (orx discover keyword): MLNeedle multilingual needle in a haystack → 2610.00973, 2610.00348, 2408.10151, 2609.03085, 2608.27580, 2604.20347, 2609.18546, 2603.29187, 2607.26337, 2608.12687
- K-19 (orx discover keyword): OneRuler multilingual long-context benchmark → 2608.20853, 2609.36218, 2608.28411, 2609.40181, 2503.01996, 2609.01056, 2609.02379, 2609.20945, 2609.23490, 2609.23416
- K-20 (orx discover keyword): token premium tokenizer fertility long context budget non-English sparse → 2609.36194, 2610.01984, 2609.39001, 2608.26449, 2607.24276, 2608.14277, 2606.24460, 2608.09046, 2608.18062, 2609.34738, 2607.09598, 2607.25291, 2608.19920, 2608.30092, 2608.26175
- K-21 (orx discover keyword): Belebele contamination FLORES memorization → 2601.20858, 2608.09766, 2609.37647, 2607.12649, 2609.34933, 2606.31208, 2605.24818, 2603.03203, 2608.12771, 2607.23440, 2605.21856, 2609.02899, 2608.07341, 2607.20572, 2608.02052
- K-22 (orx discover embedding --published-after 2026-01-01): Sparse attention, token eviction or KV selection methods degrade more for low-resource and non-Latin-script languages because of tokenizer fertility and cross-lingual query-key mismatch → 2609.39001, 2610.00540, 2608.23358, 2608.28645, 2608.11786, 2609.27758, 2607.26831, 2607.24276, 2608.26175, 2608.21384, 2607.08362, 2607.10112, 2607.04814, 2609.00378, 2606.21869
- K-23 (orx discover openalex): lightning indexer DeepSeek sparse attention → arXiv:2606.09079, arXiv:2608.01662, arXiv:2607.19358, W7135429492, arXiv:2603.12201, arXiv:2603.28458, arXiv:2605.02568, arXiv:2605.07363, arXiv:2606.13392, 10.1093/nsr/nwag212, arXiv:2607.24593, arXiv:2606.06467, 10.18653/v1/2026.findings-acl.1926, arXiv:2604.20920, arXiv:2512.03494
- K-24 (orx discover openalex): multilingual needle in a haystack cross-lingual long context → arXiv:2408.10151, 10.18653/v1/2025.naacl-long.267, arXiv:2503.01996, arXiv:2504.12845, 10.18653/v1/2026.eacl-long.290, 10.3233/ida-227347, arXiv:2207.01054, 10.18653/v1/2023.eacl-main.75, arXiv:2604.18835, 10.18653/v1/2024.naacl-long.339, 10.18653/v1/2023.acl-long.524, arXiv:2404.04659, arXiv:2208.05309, arXiv:2305.10266, W7142582410
- K-25 (orx discover keyword --published-after 2026-09-01): sparse attention indexer language → 2610.04635, 2609.26368, 2609.02737, 2609.08450, 2609.38832, 2610.06801, 2609.31093, 2609.20971, 2609.24202, 2609.39661, 2610.04753, 2609.32704, 2609.13134, 2609.37538, 2609.22884, 2609.32882, 2609.36938, 2609.38830, 2609.33746, 2609.27373
- K-26 (orx discover keyword): multilingual sparse attention retrofit frozen indexer → 2610.04635, 2605.07363, 2608.20427, 2607.11976, 2608.01662, 2606.09079, 2607.24593, 2606.13392, 2609.26368, 2606.07703, 2608.07009, 2603.12201, 2609.13205, 2606.06467, 2609.08450
- K-27 (orx discover embedding --published-after 2026-06-01): We evaluate learned sparse attention token selectors (indexers) across many languages and scripts and find that selection recall of the relevant context drops for non-English and cross-lingual queries compared with dense attention → 2610.02875, 2610.01139, 2610.07266, 2609.35820, 2610.00540, 2609.32331, 2609.23231, 2609.27376, 2608.25089, 2608.27760, 2608.21714, 2608.20047, 2608.14886, 2608.28645, 2606.13537
- K-28 (orx discover keyword): attention sparsity multilingual low-resource languages top-k → 2608.30725, 2609.15758, 2608.14626, 2606.02147, 2607.02235, 2608.11146, 2608.07629, 2608.27753, 2605.27740, 2605.18239, 2606.09535, 2608.00533, 2607.11163, 2606.09553, 2606.26144
- K-29 (orx discover openalex --published-after 2025-06-01): sparse attention multilingual languages selection recall → arXiv:2601.02819, arXiv:2606.13392, arXiv:2609.35378, arXiv:2606.03780, 10.7488/era/7299, W7212200699, arXiv:2512.14082, 10.18653/v1/2026.acl-long.1706, arXiv:2608.30725, arXiv:2604.10627, 10.21203/rs.3.rs-8714867/v1, arXiv:2604.25578, 10.3390/drones10050361, 10.54501/jots.v3i3.330, arXiv:2609.24417
- K-30 (orx discover keyword): Retrieval Head Mechanistically Explains Long-Context Factuality → 2404.15574, 2609.38222, 2610.08463, 2609.30467, 2609.38958, 2609.07663, 2608.12218, 2609.02029, 2608.05228, 2609.32663
- K-31 (orx discover keyword): head-summed attention target indexer KL distillation retrieval heads dilution → 2609.39319, 2609.37991, 2609.32704, 2605.07363, 2609.38832, 2610.04635, 2609.34650, 2608.27417, 2610.01494, 2608.06849, 2606.20005, 2606.20097, 2606.07703, 2609.17284, 2607.08107
- K-32 (orx discover embedding): Qwen3-0.6B Belebele multilingual reading comprehension accuracy small language model → 2610.06216, 2607.17466, 2607.17173, 2607.03801, 2606.21954, 2606.16383, 2606.07069, 2603.11510, 2605.15763, 2602.11961, 2603.20854, 2602.20065, 2601.10310, 2512.13298, 2512.03976
- K-33 (orx discover keyword): Qwen3-0.6B Belebele → 2601.21337, 2505.09388, 2601.15621, 2609.when-does-distillation-help-reinforcement-learning, 2608.02689, 2610.04950, 2601.04720, 2509.17765, 2511.21631, 2607.26057, 2506.05176, 2609.16096, 2609.28430, 2609.28568, 2609.17848
- K-34 (orx discover keyword): Qwen3-0.6B-Base needle in a haystack long context retrieval 8K → 2610.00973, 2609.38958, 2610.08463, 2608.27580, 2607.25066, 2609.31947, 2610.04973, 2606.24467, 2605.27243, 2608.17616, 2609.38530, 2607.24882, 2610.00348, 2608.20427, 2608.23463
- K-35 (orx discover keyword): KV cache eviction cross-lingual multilingual long-context retrieval language → 2610.06996, 2609.03430, 2610.03007, 2605.25475, 2610.06286, 2606.24467, 2608.28293, 2609.08131, 2610.03135, 2610.07643, 2609.27470, 2609.39329, 2606.31145, 2608.05326, 2609.37988
- K-36 (orx discover keyword): native sparse attention multilingual evaluation languages → 2609.35820, 2609.38832, 2606.13392, 2610.03367, 2607.23242, 2608.24477, 2610.00540, 2609.05910, 2608.19981, 2609.30739, 2608.00533, 2608.14626, 2607.05992, 2607.10371, 2604.21221
- K-37 (orx discover embedding): Token eviction and KV cache compression methods such as SnapKV and H2O evaluated across languages show larger accuracy drops for non-English languages and for queries in a different language than the context → 2609.39001, 2609.35820, 2608.27128, 2608.19670, 2608.01631, 2608.20047, 2608.30996, 2608.28641, 2608.06506, 2607.26831, 2608.26175, 2608.21384, 2607.13205, 2608.09941, 2605.24904
- K-38 (orx discover openalex --published-after 2026-09-01): DeepSeek sparse attention lightning indexer → arXiv:2609.08450, arXiv:2609.22884, arXiv:2609.32704, arXiv:2609.39661, arXiv:2609.32712, arXiv:2609.25802, arXiv:2609.35378, arXiv:2609.14507, arXiv:2609.22258, arXiv:2609.12419, arXiv:2609.13537, arXiv:2609.18110, arXiv:2609.20807, arXiv:2609.06551, arXiv:2609.36860
- K-39 (orx discover keyword): attention sink local attention question tokens needle attention mass small model → 2609.08574, 2609.02737, 2609.31947, 2608.28444, 2609.37879, 2608.29539, 2608.14712, 2609.32712, 2605.22372, 2609.00746
- K-40 (orx discover openalex): Belebele benchmark contamination FLORES-200 pretraining → arXiv:2602.16763, 10.18653/v1/2025.findings-acl.578, 10.18653/v1/2024.acl-long.777, arXiv:2403.11009, 10.18653/v1/2025.findings-acl.1053, 10.13140/rg.2.2.27046.59201, arXiv:2609.03350, arXiv:2408.13585, 10.18653/v1/2025.naacl-long.314, 10.63317/5ceec3hhv4d5
- K-P1 (orx paper --full): 2608.30320 → 2608.30320
- K-P2 (orx paper --full): 2606.07703 → 2606.07703
- K-P3 (orx paper --full): 2608.26175 → 2608.26175
- K-P4 (orx paper --full): 2609.35378 → 2609.35378
- K-P5 (orx paper --full): 2610.01921 → 2610.01921
- K-P6 (orx paper --full): 2602.22453 → 2602.22453
- K-P7 (orx paper --full): 2606.22874 → 2606.22874
- K-P8 (orx paper --full): 2512.02556 → 2512.02556
- K-P9 (orx paper --full): 2505.09388 → 2505.09388
- K-P10 (orx paper --full): 2608.20427 → 2608.20427
- K-P11 (orx paper --full): 2606.19348 → 2606.19348
- K-P12 (orx paper --full): 2603.11510 → 2603.11510
- K-P13 (orx paper --full): 2602.20065 → 2602.20065
- K-P14 (orx paper --full): 2601.02819 → 2601.02819
- K-P15 (orx paper --full): 2608.02689 → 2608.02689
- K-P16 (orx paper --full): 2404.15574 → 2404.15574

Cross-domain cell:

- X-Q1 (orx discover keyword): cross-lingual dense retrieval distillation cross-encoder teacher student gap → 2609.21619, 2609.36246, 2609.11412, 2609.37243, 2607.02966, 2610.02516, 2609.23231, 2609.35319, 2610.02597, 2609.31785, 2609.18686, 2608.03610
- X-Q2 (orx discover keyword --prioritize historical): Translate-Distill cross-language dense retrieval translation distillation → 2401.04810, 2605.29755, 2609.38777, 2505.21549, 2608.12820, 2601.11269, 2405.00977, 2609.13916, 2608.14107, 2509.25100, 2410.01383, 2606.28089
- X-Q3 (orx discover keyword --prioritize historical): ColBERT-X cross-language late interaction retrieval → 2603.25248, 2503.19009, 2609.29652, 2601.06389, 2004.12832, 2604.19566, 2511.16528, 2605.10109, 2608.19204, 2609.07561, 2408.16672, 2404.13950
- X-Q4 (orx discover keyword --prioritize historical): language bias multilingual dense retrieval same-language preference LAReQA strong alignment → 2607.22042, 2605.07249, 2606.18801, 2502.14786, 2608.02189, 2606.13537, 2605.31171, 2509.25138, 2601.04768, 2601.02956, 2608.23149, 2604.20199
- X-Q5 (orx discover embedding): A cheap low-dimensional first-stage scorer is distilled from an expensive teacher's relevance scores; we measure whether the student's top-k recall falls further behind the teacher's own top-k when the query is in a different language and script from the passage than when query and passage share a language. → 2609.29769, 2610.06216, 2609.32331, 2609.00329, 2608.27760, 2608.28645, 2605.23857, 2607.11465, 2607.07050, 2607.08268, 2609.17542, 2604.03192
- X-Q6 (orx discover openalex): cross-language information retrieval knowledge distillation dense retriever recall teacher reranker → 10.18653/v1/2021.repl4nlp-1.17, 10.48550/arxiv.2401.04810, 10.1145/3805622.3810780, 10.48550/arxiv.2604.22722, 10.48550/arxiv.2303.13220, 10.1145/3626772.3657955, 10.48550/arxiv.2607.18152, 10.21203/rs.3.rs-6219315/v1, 10.1145/3570724, 10.48550/arxiv.2302.13400, 10.1145/3404835.3462891, 10.18653/v1/2024.findings-acl.692
- X-Q7 (orx discover keyword --prioritize historical): theoretical limitations of embedding-based retrieval top-k subsets embedding dimension sign rank → 2508.21038, 2601.20844, 2602.05062, 2606.11780, 2506.05176, 2609.01963, 2602.03992, 2608.13200, 2607.18666, 2601.06873, 2510.12709, 2608.13495
- X-Q8 (orx discover keyword): KV cache compression multilingual languages eviction SnapKV H2O non-English → 2609.33334, 2608.28293, 2610.06286, 2609.03430, 2610.06479, 2609.27981, 2610.07643, 2610.02815, 2609.08131, 2609.22157, 2609.16617, 2609.37988
- X-Q9 (orx discover keyword --prioritize historical): KV cache eviction cross-lingual → 2609.03430, 2608.28293, 2605.25475, 2606.03928, 2605.09649, 2605.08840, 2608.23296, 2512.14946, 2605.08317, 2606.15157, 2609.08131, 2605.07234
- X-Q10 (orx discover embedding): Auditing KV-cache eviction and sparse attention methods such as H2O, SnapKV and PyramidKV across many languages: does token eviction under a fixed cache budget hurt non-English and cross-lingual long-context retrieval more than English? → 2610.03109, 2610.05685, 2610.03007, 2610.07643, 2610.06251, 2608.23296, 2609.33759, 2609.30738, 2609.16617, 2609.08279, 2609.31678, 2608.01631
- X-Q11 (orx discover keyword --prioritize historical): KV cache compression low-resource languages multilingual long-context degradation → 2609.19969, 2606.24467, 2606.31145, 2607.00760, 2607.06519, 2606.08382, 2503.18893, 2509.17396, 2605.25475, 2608.08569, 2605.09649, 2605.22269
- X-Q12 (orx discover openalex): KV cache compression multilingual evaluation languages → 10.48550/arxiv.2410.15252, 10.48550/arxiv.2609.19969, 10.48550/arxiv.2606.14782, 10.48550/arxiv.2607.06827, W7152933851, 10.21203/rs.3.rs-10297225/v1, 10.18653/v1/2026.acl-long.594, 10.18653/v1/2025.findings-emnlp.426, 10.48550/arxiv.2605.25085, 10.48550/arxiv.2502.01941, 10.5753/sbbd.2025.247245, W7161354758
- X-Q13 (orx discover keyword --prioritize historical): How does quantization affect multilingual LLMs → 2407.03211, 2609.11716, 2505.21505, 2505.20276, 2609.11582, 2606.25444, 2605.11195, 2511.10840, 2602.08625, 2503.03592, 2502.12560, 2605.28710
- X-Q14 (orx discover keyword --prioritize historical): SnapKV PyramidKV multilingual languages Chinese Japanese Korean evaluation cache budget → 2406.02069, 2606.11164, 2608.05802, 2605.29414, 2609.33334, 2606.28884, 2407.19400, 2608.26700, 2604.11288, 2608.23037, 2607.11942, 2608.28641
- X-Q15 (orx discover embedding): Language-dependent degradation of long-context models under token-budgeted compression: tokenizer fertility means non-Latin scripts use more tokens per unit of content, so a fixed token budget keeps less information for those languages. → 2609.39001, 2608.26449, 2609.00329, 2608.04160, 2607.24276, 2608.09046, 2608.26175, 2607.26831, 2607.16117, 2608.21384, 2609.00378, 2606.14122
- X-Q16 (orx discover keyword --prioritize historical): Language Model Tokenizers Introduce Unfairness Between Languages → 2305.15425, 2609.15528, 2506.10766, 2606.13674, 2609.09143, 2607.23319, 2609.39001, 2606.15044, 2510.06128, 2507.06378, 2602.15397, 2510.05699
- X-Q17 (orx discover keyword): multilingual needle-in-a-haystack KV cache compression eviction OneRuler MLNeedle → 2610.06286, 2610.03198, 2610.06996, 2608.28293, 2610.02953, 2609.03430, 2606.24467, 2610.07643, 2610.06479, 2609.08131, 2609.33334, 2610.02815
- X-Q18 (orx discover keyword): sparse attention multilingual cross-lingual retrieval top-k selection non-English degradation → 2608.22363, 2609.23231, 2608.12820, 2610.02875, 2610.06216, 2608.21714, 2609.32331, 2609.27376, 2609.04409, 2608.03446, 2606.15345, 2604.20666
- X-Q19 (orx discover openalex --published-after 2024-01-01): multilingual KV cache eviction language disparity long context → 10.48550/arxiv.2511.16786, 10.48550/arxiv.2405.14256, 10.48550/arxiv.2605.17447, 10.18653/v1/2025.emnlp-main.1166, 10.1145/3809166, 10.48550/arxiv.2410.03090, 10.48550/arxiv.2604.08075, 10.48550/arxiv.2411.18191, 10.48550/arxiv.2604.09613, W7148176105, 10.18653/v1/2025.emnlp-main.209, 10.48550/arxiv.2401.08092
- X-P1 (orx paper --full): 2406.02069 → 2406.02069
- X-P2 (orx paper --full): 2502.01941 → 2502.01941
- X-P3 (orx paper --full): 2607.11942 → 2607.11942
- X-Q20 (orx discover embedding --published-after 2024-06-01): We evaluate KV cache compression methods across many languages and find that token eviction disproportionately harms non-English and low-resource languages in long-context question answering. → 2609.36322, 2608.27128, 2608.19670, 2608.22490, 2608.01631, 2608.09046, 2606.24467, 2608.26175, 2608.21384, 2606.15157, 2608.vorn-kv-cache-eviction, 2608.09941
- X-Q21 (orx discover keyword --published-after 2025-01-01): efficient attention multilingual fairness compression harms low-resource languages long context → 2608.14626, 2609.15528, 2606.24467, 2608.30725, 2608.20853, 2609.language-agnostic-whisper-adaptation-low-resource-asr, 2606.02147, 2609.15758, 2609.13205, 2608.27753, 2609.30739, 2607.02235
- X-Q22 (orx discover openalex): translation priming asymmetry meta-analysis masked priming L1 L2 non-cognate → 10.3758/s13423-016-1151-1, 10.3389/fpsyg.2018.00986, 10.5070/g601147, 10.31234/osf.io/dehrt, 10.3758/mc.37.5.569, 10.1017/s0272263122000249, W2910381970, 10.1017/s1366728926101679, 10.3389/fpsyg.2018.00267, W7217649758, 10.3389/fpsyg.2024.1500750, 10.1177/13670069231164257
- X-Q23 (orx discover openalex): bilingual memory search cross-language semantic retrieval cue language mismatch recall → W2325304666, 10.1111/j.1467-9450.2009.00744.x, 10.1080/09658211.2023.2171435, 10.1016/j.jml.2020.104155, 10.3390/electronics14153145, 10.1016/j.neuropsychologia.2021.107795, W2886668275, 10.48550/arxiv.2605.07249, 10.31234/osf.io/tbuzh, W2979638275, W2795226082, 10.1044/2020_jslhr-20-00007
- X-Q24 (orx discover openalex): language-dependent memory retrieval bilinguals encoding specificity language of retrieval cue → 10.1080/09658211.2013.873809, 10.3389/fpsyg.2014.00137, 10.9707/2307-0919.1034, 10.3389/fpsyg.2014.01369, 10.1086/595022, 10.4324/9781410603494-67, 10.18653/v1/n18-1183, 10.3758/bf03194123, 10.1080/09658211.2023.2171435, 10.3389/fpsyg.2023.1198117, 10.3389/fpsyg.2016.00120, 10.1080/01690960143000515
- X-Q25 (orx discover openalex): visual search target template specificity picture cue versus word cue guidance efficiency → 10.3758/s13423-020-01859-9, 10.3758/app.72.5.1283, 10.3758/s13414-024-02899-2, W2764924344, 10.3758/s13414-018-1520-0, 10.3758/s13414-020-02213-w, 10.3758/s13414-011-0153-3, 10.1167/16.2.3, 10.31390/gradschool_theses.4405, 10.1167/18.13.11, 10.1037/xhp0000156, W7132907836
- X-Q26 (orx discover openalex): language context guides memory content Marian Kaushanskaya → 10.3758/bf03194123, 10.3389/fnhum.2019.00364, 10.1016/j.learninstruc.2016.01.003, 10.3389/fpsyg.2017.00394, 10.3758/s13421-023-01415-5, 10.1075/hcp.21.05sut, 10.3389/fpsyg.2010.00162, 10.1038/s41539-020-0068-7, 10.3389/fpsyg.2023.1237471, 10.58445/rars.551, 10.1371/journal.pone.0169001, 10.32601/ejal.460617
- X-Q27 (orx discover keyword): rate-distortion attention sparsity top-k budget selection distortion bound sparse attention → 2606.13392, 2609.08450, 2609.26368, 2605.27740, 2608.12780, 2606.27321, 2609.34367, 2610.06801, 2610.04635, 2609.19702, 2607.27692, 2609.35593
- X-Q28 (orx discover embedding): Selecting a subset of context tokens under a fixed token budget is a lossy source-coding problem; how much of the relevant evidence survives depends on how many tokens the evidence costs in a given language's tokenization and on the budget operating point. → 2610.05685, 2609.39001, 2609.37879, 2609.38699, 2610.08722, 2609.35869, 2610.05126, 2610.02233, 2609.bite-morphology-guided-computational-mastication, 2609.33405, 2609.37575, 2608.01347
- X-Q29 (orx discover openalex --published-after 2023-01-01): budgeted selection recall curve operating point compression ratio cross-lingual evaluation → 10.48550/arxiv.2607.02966, 10.1007/s10489-024-05747-w, 10.48550/arxiv.2609.03235, 10.48550/arxiv.2608.15962, 10.1007/s40747-025-02019-z, 10.48550/arxiv.2606.20571, 10.48550/arxiv.2511.05747, 10.48550/arxiv.2608.18062, 10.1613/jair.1.13715, 10.48550/arxiv.2602.07574, 10.48550/arxiv.2607.29539, 10.48550/arxiv.2608.25735
- X-Q30 (orx discover keyword --prioritize historical): LAReQA language-agnostic answer retrieval multilingual pool strong alignment → 2004.05484, 2605.07249, 2607.22042, 2605.31171, 2609.06381, 2606.18801, 2608.02189, 2604.05684, 2601.04768, 2511.09984, 2510.00908, 2512.03514
- X-Q31 (orx discover keyword --prioritize historical): Sparse, Dense, and Attentional Representations for Text Retrieval embedding dimension capacity → 2608.02583, 2602.05062, 2608.22764, 2609.32671, 2508.16707, 2503.02453, 2506.05176, 2608.16918, 2608.14107, 2005.00181, 2608.18855, 2605.29507
- X-P4 (orx paper --full): 2401.04810 → 2401.04810
- X-P5 (orx paper --full): 2405.00977 → 2405.00977
- X-P6 (orx paper --full): 2302.13400 → 2302.13400
- X-P7 (orx paper --full): 2508.21038 → 2508.21038
- X-P8 (orx paper --full): 2005.00181 → 2005.00181
- X-P9 (orx paper --full): 2608.26175 → 2608.26175
- X-P10 (orx paper --full): 2608.04160 → 2608.04160
- X-P11 (orx paper --full): 2608.19670 → 2608.19670
- X-P12 (orx paper --full): 2305.15425 → 2305.15425
- X-P13 (orx paper --full): 2004.05484 → 2004.05484
- X-P14 (orx paper --full): 2601.20844 → 2601.20844
- X-P15 (orx paper --full): 2407.03211 → 2407.03211
- X-Q32 (orx discover keyword --published-after 2025-01-01 --prioritize default): KV cache compression across languages language-dependent token importance multilingual long-context benchmark eviction → 2610.06479, 2610.06286, 2609.03430, 2609.08131, 2610.02953, 2605.25475, 2609.37988, 2609.39329, 2608.28293, 2606.24467, 2610.02815, 2610.03007
- X-Q33 (orx discover openalex --published-after 2025-01-01): multilingual long-context KV cache eviction cross-lingual needle retrieval evaluation → 10.18653/v1/2026.acl-long.1811, 10.1109/tpami.2026.3708708
- X-Q34 (orx discover embedding): Cross-lingual robustness of query-aware KV cache selection: when the question and the document are in different languages, does attention-based token selection (SnapKV-style observation window) keep the relevant evidence? → 2608.25832, 2609.34049, 2610.03109, 2610.00606, 2609.33759, 2609.30738, 2609.04409, 2609.00155, 2608.21714, 2606.13537, 2606.15345, 2601.18527
- X-P16 (orx paper --full (found via WebSearch)): 2602.05929 → 2602.05929
- X-P17 (orx paper (openalex metadata)): 10.3758/s13423-016-1151-1 → 10.3758/s13423-016-1151-1
- X-P18 (orx paper (openalex metadata)): 10.3758/s13421-023-01415-5 → 10.3758/s13421-023-01415-5
- X-P19 (orx paper (openalex metadata)): 10.3758/s13423-020-01859-9 → 10.3758/s13423-020-01859-9
- X-P20 (orx paper (openalex metadata)): 10.3758/bf03194123 → 10.3758/bf03194123
- X-Q35 (orx discover openalex): Bjontegaard delta rate distortion curves average difference codec comparison → 10.1109/access.2021.3077116, 10.1109/tip.2023.3346695, 10.3390/electronics9101579, 10.1109/iccv48922.2021.00661, 10.48550/arxiv.2208.04303, 10.48550/arxiv.2401.17246, 10.15002/00025871, 10.48550/arxiv.2111.10302, W2968017848, 10.36227/techrxiv.170775802.27887173/v1, W18713181, 10.1109/access.2018.2870183
- X-Q36 (orx discover keyword --prioritize historical): Bjontegaard delta rate-distortion curve comparison interpolation reliability → 2609.30077, 2609.02107, 2606.13366, 2608.11636, 2602.15779, 2504.02216, 2605.06675, 2509.05929, 2601.19293, 2606.16592, 2605.14694, 2606.22888
- X-P21 (orx paper (openalex metadata)): 10.1109/tip.2023.3346695 → 10.1109/tip.2023.3346695
- X-Q37 (orx discover keyword --prioritize historical): OOD-DiskANN out-of-distribution queries approximate nearest neighbor search recall (returned 'error decoding response body'; zero ids) → no ids
- X-Q38 (orx discover embedding): Approximate nearest neighbor indexes built on one data distribution lose recall against exact top-k search when queries come from a different distribution, such as text queries over image embeddings or cross-lingual queries. → 2609.23036, 2609.00364, 2608.25185, 2607.24880, 2608.12333, 2605.17415, 2604.27674, 2604.20417, 2604.24469, 2604.01960, 2604.21645, 2604.16351
- X-Q39 (orx discover openalex): OOD-DiskANN efficient scalable graph ANNS out-of-distribution queries → 10.48550/arxiv.2211.12850, 10.48550/arxiv.2310.00402, 10.14778/3681954.3681959, 10.48550/arxiv.2408.13899, 10.1145/3627535.3638475, 10.48550/arxiv.2403.01797, 10.48550/arxiv.2305.04359, 10.1145/3736227.3736237, 10.1145/3769783, 10.1145/3639269, 10.48550/arxiv.2602.02057, 10.1145/3736716
- X-P22 (orx paper --full): 2211.12850 → 2211.12850
- X-Q40 (orx discover keyword --prioritize historical): OPTICAL optimal transport distillation low-resource cross-lingual information retrieval bitext → 2301.12566, 2609.06381, 2608.12820, 2605.31171, 2604.05684, 2609.23231, 2604.05821, 2605.10714, 2510.00908, 2608.21714, 2607.18693, 2608.11146
- X-P23 (orx paper --full): 2301.12566 → 2301.12566
- X-W1 (WebSearch (standard)): KV cache compression multilingual evaluation non-English languages SnapKV H2O degradation → 2502.00299, 2502.16886, 2602.05929, 2404.14469, aclanthology 2026.acl-long.1926 (The Pitfalls of KV Cache Compression)
- X-W2 (WebSearch (standard)): sparse attention token eviction cross-lingual query document different language long-context retrieval audit → 2602.03152, 2506.11498, 2602.05191, 2605.16928, 2510.20787

Synthesis (paper reads only):

- S-P1 (orx paper --full --no-telemetry): 2004.05484 → 2004.05484
- S-P2 (orx paper --full --no-telemetry): 2211.12850 → 2211.12850
- S-P3 (orx paper --full --no-telemetry): 2401.04810 → 2401.04810
- S-P4 (orx paper --full --no-telemetry): 2404.15574 → 2404.15574
- S-P5 (orx paper --full --no-telemetry): 2408.10151 → 2408.10151
- S-P6 (orx paper --full --no-telemetry): 2410.13276 → 2410.13276
- S-P7 (orx paper --full --no-telemetry): 2502.05167 → 2502.05167
- S-P8 (orx paper --full --no-telemetry): 2503.01996 → 2503.01996
- S-P9 (orx paper --full --no-telemetry): 2504.10906 → 2504.10906
- S-P10 (orx paper --full --no-telemetry): 2505.09388 → 2505.09388
- S-P11 (orx paper --full --no-telemetry): 2512.02556 → 2512.02556
- S-P12 (orx paper --full --no-telemetry): 2601.02819 → 2601.02819
- S-P13 (orx paper --full --no-telemetry): 2601.18886 → 2601.18886
- S-P14 (orx paper --full --no-telemetry): 2602.22453 → 2602.22453
- S-P15 (orx paper --full --no-telemetry): 2603.02227 → 2603.02227
- S-P16 (orx paper --full --no-telemetry): 2606.07703 → 2606.07703
- S-P17 (orx paper --full --no-telemetry): 2606.22874 → 2606.22874
- S-P18 (orx paper --full --no-telemetry): 2607.01002 → 2607.01002
- S-P19 (orx paper --full --no-telemetry): 2607.21692 → 2607.21692
- S-P20 (orx paper --full --no-telemetry): 2608.04160 → 2608.04160
- S-P21 (orx paper --full --no-telemetry): 2608.26175 → 2608.26175
- S-P22 (orx paper --full --no-telemetry): 2608.30181 → 2608.30181
- S-P23 (orx paper --full --no-telemetry): 2608.30320 → 2608.30320
- S-P24 (orx paper --full --no-telemetry): 2609.35378 → 2609.35378
- S-P25 (orx paper --full --no-telemetry): 2610.01921 → 2610.01921
- S-P26 (orx paper --full --no-telemetry): 2610.04635 → 2610.04635

## Mechanism and Falsifiable Predictions

Mechanism statement. This is the paragraph given to the blind critic,
anonymized: a frozen pretrained decoder language model is fitted, at every
attention layer, with a small learned selector that scores four-token blocks
of the context. The selector uses a few query projections of the current
token, one pooled key per block, and a gated sum of rectified dot products. It
is trained only by minimizing the KL divergence between its block-score
distribution and a block aggregation of that layer's own attention: either the
head-summed attention mass in each block, or its within-block maximum. The
training text excludes the evaluation languages and their scripts, and the
backbone receives no gradient. At a fixed budget of the top 256 blocks (1,024
of 8,192 context tokens), the selector's recall of a known evidence passage is
compared with the recall of the exact top-256 blocks of its own training
target. The quantity of interest is a difference-in-differences: how much more
evidence recall the selector loses than its target when the question is a
human translation in a different writing system from the passage, compared
with a question in the passage's own language that also does not copy the
passage verbatim. A verbatim-copy question serves as an adequacy ceiling and
random block choice as a floor. Pre-registered gates require the dense model
to show selection and answering headroom before any difference is interpreted.

Hypothesis under test (H_loc). A low-rank selector fitted to aggregated
attention reproduces its target's ranking where the question and the passage
match lexically or within one language. It fails to reproduce the target's
cross-lingual matching, so xi_T is greater than 0. The null is xi_T = 0: the
selector inherits the target's cross-lingual gap without adding to it.

Two mechanisms could produce xi greater than 0. The screen separates them only
descriptively.

- M1, capacity or subspace. The four-head, 128-dimensional scorer drops the
  part of the attention subspace that carries cross-lingual matching (D21's
  original hypothesis). The R^2k bound (C41) makes capacity alone an unlikely
  limit: 4 × 128 = 512 gated score dimensions serve k = 256.
- M2, input-distribution shift. Every cross-script evaluation script was
  removed from indexer training (E4). Query rows in an unseen script are
  therefore out of distribution for the indexer's projections, as data-built
  ANN indexes lose recall on out-of-distribution queries (C25).
  - The crossed design places the unseen-script question in the MN leg for the
    7 (needle X, query X) pairs. It places it in the CX leg for the 7 (needle
    en, query X) pairs.
  - M2's query-side effect therefore enters xi with opposite signs in the two
    directions, and the macro cancels it only if the two directions are
    symmetric.
  - Per-direction tables are registered as descriptive.

Registered predictions and decision rules (v2, "Decision rules"; thresholds
fixed before any audit read):

- P1, GO (H_loc supported). Some target T has xi_T ≥ 10, with the combined 99
  percent lower bounds of xi_T and xi_rel_T both above 0. V1 to V3 must pass
  for that T, with H1 ≥ 10 and H2a and H2b passing. Next step: the label-free
  remedy arms. The result is labelled "cross-script" only if
  xi_CX − xi_CS ≥ 5 (descriptive).
- P0, NEGATIVE: the falsifier and kill criterion for H_loc at 0.6B. Every
  condition below must hold for both targets:
  - xi_T ≤ 5, with the combined upper bound below 10 and half-width at most 5;
  - xi_rel_T ≤ 0.1, with its upper bound below 0.2;
  - V1 to V3 pass, H1 ≥ 20, and H2a and H2b pass.
  The Q3 kill criterion: publish the localization negative and stop.
- UNINTERPRETABLE: H1 below 10, or H2a or H2b failing on the audit read. At the
  development pre-check the same failures give ESCALATE_OR_STOP, and K1 does
  not run on 0.6B. The next rung is Qwen3.5-4B-Base under a new contract
  version, or stop.
- HOLD (terminal for the id): a V2 bug tell, meaning English ML R_ind above
  R_T(ML) + 1 at any seed.
- VOID: an integrity failure.
- INCONCLUSIVE: everything else, including any half-width above 5.

Falsifier defects found in this wave (stated plainly):

1. **The NEGATIVE branch is not identified against a degenerate indexer.**
   - Take an indexer that passes V1 (English literal copy) but scores at
     random on both non-literal legs. It has R_ind(MN) = R_ind(CX) = R_rand.
   - Then xi_T = −(R_T(MN) − R_T(CX)) = −Delta_T, and
     xi_rel_T = G(MN) − G(CX) = 0.
   - Both lie inside the NEGATIVE region whenever Delta_T ≥ −5. No registered
     rule puts a floor under the indexer's own non-literal retrieval: V1 reads
     only the literal leg (E5).
   - A NEGATIVE could therefore mean "the selector fails non-literal
     retrieval everywhere". That is not "the selector adds no cross-lingual
     loss". Delta_ind and G(MN) are reported, but only descriptively.
   - Repair needs a new experiment id (D20, rule 3).
2. **The NEGATIVE branch is probably unreachable at 0.6B.**
   - NEGATIVE needs H1 = max over T of macro [R_T(CX) − R_rand(CX)] ≥ 20, that
     is, macro dense CX recall of about 32.5 or more.
   - v1's development smoke measured 26.45 (hs) and 26.08 (mp) pooled over MN
     and CX, against 12.48 random (E1).
   - For CX alone to reach 32.5 while the pooled mean stays at 26.5, MN would
     have to sit about 12 points below CX on these units. That is the opposite
     of the expected ordering.
   - So the NEGATIVE branch is reachable only if those 20 lexicographically
     first development units are unrepresentative by several points. Their
     MN/CX split was never computed.
3. **"Cross-script" attribution is confounded** with script exposure (unseen
   scripts in CX, seen Latin in CS), with tokenizer fertility (1.45 to 6.2
   times English needle length, E4) and with how tightly the 1,024-token budget
   binds. The attribution rule xi_CX − xi_CS ≥ 5 changes all of these at once.
   No registered condition holds the script seen while crossing scripts.

Outcome map at 0.6B. These ranges are the synthesis owner's judgement from E1
to E3, C18 and C19, not measurements. They are written down so the reviewers
can dispute them.

- The dense development pre-check stops 0.6B (ESCALATE_OR_STOP): about 0.4 to
  0.6.
  - H2a passes the 20-question pre-check with probability 0.17 to 0.39 at a
    true accuracy of 40 percent and 0.46 to 0.76 at 45 percent.
  - The capability evidence for 0.6B is mixed: ARC-C near chance, CMMLU and
    C-Eval near 54 (C19).
  - H2b needs a retrieval effect of about 14 to 15 points.
  - H1 ≥ 10 on CX needs CX headroom close to the 14 points pooled.
- Conditional on proceeding:
  - HOLD, about 0.1 to 0.4 (E3: 0.47 to 0.74 at an exact English ML match,
    0.06 to 0.39 at a 1-point deficit);
  - GO, about 0.1 to 0.25 (C14 and C15 point to a small effect);
  - NEGATIVE, at most about 0.05 (point 2 above);
  - INCONCLUSIVE or UNINTERPRETABLE for the remainder.

## Cheapest Decisive Pilot

The pilot is the registered screen itself, run in its registered order. That
order already places the cheapest decisive step first. Costs are the
probe-derived projections and caps (E2).

| Stage | What it decides | Projected GPU-h | Cap GPU-h |
|---|---|---:|---:|
| done: v1 smoke 452 | v1 plumbing passes; v1 budget fails; pooled dense headroom about 14 points | 0.04 | 0.04 (v1) |
| done: probe 543 | v2 code equals v1's within TF32 gates; rates; caps total 8.05 | 0.055 | 0.15 |
| 1. smoke (1 GPU) | v2 plumbing and timing on registered data; gates main and extension budgets (SMOKE_PASS) | 0.095 | 0.19 |
| 2. headroom-dev pre-check (1 GPU, dense only) | H1, H2a, H2b on 280 development families plus needle-absent twins and no-haystack references: PROCEED_TO_K1 or ESCALATE_OR_STOP | 0.095 | 0.19 |
| 3. resume legs R0, R1, R2 (1 GPU) | fresh-job resume equals the uninterrupted run bit for bit | 0.33 | 0.64 |
| 4. main (4 GPUs) | 18 indexers per layer on 28 layers, LR freeze on stream-dev KL, one audit read: GO, NEGATIVE, UNINTERPRETABLE, HOLD, VOID, INCONCLUSIVE or V1_EXTENSION_REQUIRED | 2.24 | 3.34 |
| 5. V1 extension (4 GPUs, only when called, then mandatory) | re-read of V1-failing targets after epochs 2 and 3 | 2.38 | 3.54 |

Expected spend. If stage 2 stops 0.6B, the screen ends after about 0.19
projected GPU-hours (0.38 of caps). If it proceeds without the extension, about
2.76; with the extension, about 5.14. The registered caps are 8.05 including
the probe.

The result that would kill H_loc is a NEGATIVE, and the pilot can produce one.
Given falsifier defects 1 and 2, though, the pilot is decisive mainly in two
directions. It can answer "0.6B has no usable cross-script headroom" (stage 2,
cheap), or it can produce a GO.

Zero-GPU steps that would sharpen the admission decision, none of them taken in
this wave:

- (a) Split v1 smoke 452's 20 development units into MN and CX. Their per-unit
  chunks are on the host. This would test falsifier defect 2 directly. It is a
  new look at development data that a later registration would have to
  disclose, so it needs the owner's approval. It never touches the audit
  partition.
- (b) Decide, before admission, whether to repair falsifier defect 1 under a
  new id. One option is a non-literal adequacy floor on NEGATIVE, for example
  G_T(MN) with a 99 percent lower bound of at least 0.5.
  - Changing the tabled statistics code would need a new probe id under v2
    decision 44.
  - Splitting the pre-check off to run under its own id would lower v2's caps
    below 8 GPU-hours. That is exactly the after-measurement cut that D20, D22
    and D24 rule out unless Kevin decides otherwise.

## Controls, Baselines, and Ablations

Registered (unchanged from v1):

- References:
  - own-target dense top-256 blocks (R_T) for each target;
  - an analytic random baseline (R_rand);
  - the union of each head's top 1,024 tokens (U) and top 64 tokens (U_k);
  - a descriptive head-max selector (hm).
- Two target aggregations (hs, mp). These are the DSA-style and QSA-style
  recipes.
- Three learning rates, frozen per target on stream-dev KL before any audit
  read. This guards against an undertrained indexer that passes V1 and loses
  more on CX (v2 decision 42).
- Three seeds (42, 43, 44), which vary initialization only.
- ML literal ceiling: 200 prompts.
- 300 needle-absent CX twins (H2b), which separate retrieval from parametric
  answering of possibly memorised FLORES passages.
- No-haystack references at the pre-check.
- Crossed design: all 230 audit questions in all 14 cross-script pairs, which
  removes item difficulty as a language confound.
- Same-script pairs (id, tr, sw, nl, it), descriptive.

Not registered. These are the gaps found in this wave, ranked by the synthesis
owner:

1. A floor on the indexer's own non-literal retrieval in the NEGATIVE rule
   (falsifier defect 1).
2. A seen-script cross-script condition that separates script exposure from
   cross-lingual matching (falsifier defect 3). One example is a training-pair
   language such as en-hi, which the claim boundary currently excludes by
   design.
3. A mixed-language haystack with distractors in the question's language. This
   is the strong-alignment regime of LAReQA (C23); K1 tests weak alignment
   only, so a NEGATIVE is scoped to it.
4. A recall-versus-budget curve. The language gap of external selectors is
   strongly rate-dependent (C14, C29), and K1 reads one keep-rate (0.125). A
   larger top-k returns each smaller budget as a prefix of the same scores, so
   the curve would cost no extra forward passes. Adding it still needs new code
   and a new id.
5. The share of each selector's budget spent on block 0, the sink at token
   151643 (C20). It enters R_ind and R_T alike and largely cancels in xi, but
   it shrinks both.
6. A monolingually distilled indexer arm (D21 arm a). Half of K1's training
   stream is bilingual from 7 non-evaluated pairs, so any NEGATIVE applies to
   an indexer with cross-lingual attention exposure (C24 by analogy).
7. A width arm that separates M1 from M2. It is deferred, as in D21.

Ablations already registered as descriptive tables: per-language, per-direction,
per-layer (important given C28's late-layer bottleneck), per-position,
same-script rows, Lambda = R(ML) − R(MN), S_T against U and U_k, and boundary
tie counts.

## Evaluation, Statistics, and Leakage Checks

Statistics (v2, "Metrics" and "Interval"):

- Recall is per prompt: per layer, the mean over query rows of the fraction of
  needle tokens selected, then the mean over 28 layers.
- se_cluster comes from a passage-cluster bootstrap over the 122 audit links
  (B = 10,000, NumPy seed 42, macro inside each replicate).
- s_seed is the SD of the three per-seed values.
- The decision interval is point ± t(0.995, df) × sqrt(se_cluster² + s_seed²/3),
  with Welch–Satterthwaite df.
- The interval is not a full 99 percent interval in every regime. In the
  pre-freeze simulations its coverage was 96.3 to 96.7 percent when the two
  variance terms were comparable. The point thresholds still keep P(GO) near 0
  at a true xi of 5 or below, and P(NEGATIVE) near 0 at 9 or above (E3).
- Multiplicity: two targets, each at 99 percent. GO from either target inflates
  GO near the threshold: 0.16 to 0.32 with both targets at a true xi of 9, in
  four of five regimes. Every other table is descriptive and uncorrected.
- Effect sizes are reported with point, combined interval, percentile interval,
  df and the per-seed values.
- Seed count is justified by simulation, not habit. GO detects a true xi of
  about 10.9 with power 0.8 in the worked case. A seed-dominated NEGATIVE needs
  a seed SD of xi of at most about 0.87.

Sensitivity this wave adds, descriptively:

- Macro-averaging over both directions halves an effect confined to one
  direction, so a GO at 10 would need about 20 points in that direction. Human
  translation-priming asymmetry (doi 10.3758/s13423-016-1151-1, meta-analysis,
  OpenAlex metadata only) makes a one-direction effect plausible.
- The 28-layer mean dilutes a late-layer effect (C28).
- Head-summed targets dilute retrieval heads, which are less than 5 percent of
  heads (C27).

Leakage and partitions:

- Belebele passages are split by link into development (122), audit (122) and
  primary (244) with `split_passage_ids(seed=42)`. This screen reads only the
  audit partition, plus development for the smoke and the pre-check. A read
  outside the declared partition raises and exits 3, and the primary partition
  is never read.
- The learning-rate freeze is recorded and hashed before any audit prompt is
  read.
- Dedup: exact 50-gram and MinHash Jaccard of at least 0.8 against Belebele in
  18 languages. It does not cover the training languages de, fr, es, pl and ru
  (C06), so FLORES-derived text in those languages inside training data would
  go undetected. The impact is low: a 660K-parameter attention imitator is
  unlikely to memorise content, and H2b guards the dense model's parametric
  answering.
- Disclosure: this proposal was written after v1's pooled development recall
  (E1) was seen. No audit statistic exists. No threshold is changed here.

## Compute and Reproducibility

The gauntlet's own budget (gpu_hours=1 in the header) covers reviewer
inference only. It is not the pilot's budget.

Pilot compute: gpu_hours: 8.05. That is the sum of the registered caps,
including the probe, under the D22 counting rule. Admission is Kevin's
decision (D24).

- Image.
  - The screen's own image B2 does not exist. It is built only from the commit
    holding the frozen registration and its ledger row, so it cannot exist
    while v2 is unfrozen.
  - The image of record for the tabled v2 code is the probe image from build
    533 at commit 4b9d6c4: 127.0.0.1:5000/cotcodec-research@sha256:2eb02b0fb1a8622d47089019eb7168e4dbea467857f3784db77d1551e2583f7e
    (image id sha256:e59d9cc18c0db05fa0ae20a0f65492268112d07fef20f00af799323ae02ce6d3;
    torch 2.11.0+cu128, CUDA 12.8.1).
  - Both K1 doctors passed in it: v1 7/7 (Slurm 534) and v2 5/5 (Slurm 536).
    Probe 543 passed every device tolerance gate in it.
- Launch.
  - Every GPU job goes through `scripts/submit_docker_research_job.py`
    (dry-run, test-only, submit) from an orx `slurm-manifest` node on the
    host's ssh backend.
  - The submitter issues `sbatch --parsable --partition=research --nodes=1 --ntasks=1 --gres=gpu:h100:4 --time=00:50:00 --signal=B:USR1@180 infra/slurm/host-single-node/docker-research.sbatch`
    for the main job. The probe's dry-run of this form is in the bundle under
    `compute/`.
  - Manifests are filled by `scripts/fill_sparse_indexer_k1_v2_manifests.py`.
    It enforces SMOKE_PASS, PROCEED_TO_K1 and resume validity before it fills
    the main job.
- Seeds: seeds: [42, 43, 44] for indexer initialization. Stream order, the
  passage split, prompts and the bootstrap use seed 42 or SHA-256 orders, and
  there is no unseeded randomness.
- Checkpoints and preemption.
  - Periodic checkpoints during training; SIGUSR1 180 s before the limit
    triggers a confirmed signal checkpoint (exit 75).
  - The main job gets one continuation within its remaining minutes, which must
    be at least 5. The extension is never continued.
  - Resume test: R2, resumed in a fresh job from R1's signal checkpoint, must
    equal the uninterrupted R0 bit for bit
    (`scripts/compare_sparse_indexer_resume.py`).
- Artifacts: receipts, `main-read.json`, the LR-freeze record, per-unit
  evaluation chunks and per-step loss logs under the registered run roots;
  evidence copied to `program/evidence/` with SHA-256 indexes.
- Cost ceiling: 8.05 GPU-hours of caps; expected use under E2 is 0.19, 2.76 or
  5.14 GPU-hours by branch.
- Contract: `experiments/architectures/translation-supervised-sparse-indexer-k1-screen-v2.yaml`.
  It passes `scripts/validate_architecture_experiments.py` (PASS, contract
  BLOCKED) with `execution.enabled: false` and `job_limits: null` until a
  freeze applies the probe-derived limits.

Known mismatch, recorded and not repaired here (rule 3: no doctor is edited to
make an output pass). The deterministic research-direction doctor validates the
compute manifest with `scripts/submit_research_job.validate_manifest`. That
function requires an OCI digest in an `image` field. The Docker discovery lane
the probe actually ran under declares `image_id` (a local image ID). The real,
executed probe manifest therefore fails the doctor's schema ("image must
contain a full immutable OCI digest").

A second mismatch has the same cause. The doctor's real-model-loop check reads
`harness/runner.py`, a path that does not exist in the current repository. It
therefore reports "repository real model loop is still a stub" whatever the
bundle says. The K1 loop lives in `scripts/run_sparse_indexer_phase0a_v2.py`
and `harness/sparse_indexer_bank.py`, and it ran on the H100 in probe 543.

## Safety, Data Rights, and Monitorability

Data rights (v2 data-source table, C46):

| Source | Revision | Licence | Use |
|---|---|---|---|
| Belebele | 7899cdfa | CC-BY-SA-4.0 | needles, questions, options |
| FineWeb-2 | af9c1333 | ODC-By-1.0 (Common Crawl terms of use apply, not opened) | monolingual training text and non-English haystacks |
| FineWeb | 9bb295dd | ODC-By-1.0 (Common Crawl terms of use apply, not opened) | English haystacks |
| ParaDocs | f80095af | Apache-2.0 packaging; the ParaCrawl text is not owned by the packager | bilingual training documents |
| ParaDocs filter tool | 88f4ed95 | no LICENSE file | semantics reimplemented, not vendored |
| Qwen3-0.6B-Base | da87bfb6 | apache-2.0 | frozen teacher |

TED2020 is excluded (D4). Only identifiers and digests of web text are
published, and no prompt dump or receipt carries training text. No employer
data, customer translation memory or private dataset is used. The repository
is public and the bundle holds only metadata extracts (arXiv metadata is CC0),
never paper full texts.

Monitorability. The selection set is an inspectable trace. Per-language
selection recall is an audit instrument for sparse models, including any case
where a foreign-script block is over- or under-selected (cross-lingual prompt
injection carried in another script). There is no chain-of-thought effect.

Red lines (stop and report):

- any held-out evaluation language entering indexer training;
- any read of the primary partition;
- publication of training text;
- any GPU job outside the digest-pinned image and Slurm lane;
- running any model-generated or untrusted code on GPUs (D7: the harness is
  reviewed project code and generates no code at run time).

Two further issues are not red lines but are not met: the Common Crawl terms of
use were never opened, and the remediation is to read and record them.

### Integrity gate

The seven failure modes as named in the gauntlet rule's integrity-gate row. The
ARS protocol file itself was not opened in this wave.

1. Implementation bug passing self-review: PARTIAL.
   - In favour: the v1 doctor passed 7/7 and the v2 doctor 5/5 in the probe
     image; the probe gated bank-versus-v1 equivalence on the H100 under TF32;
     V2 (bug tell) and V3 (integrity) are registered.
   - Not yet run: the v2 evaluation path on real Belebele units (v1's ran in
     smoke 452).
   - The NEGATIVE-floor hole is a design bug that the code implements
     faithfully.
2. Hallucinated citation: CLEAR for cited URLs. Every cited arXiv and Hugging
   Face page has a hashed HTTP-200 snapshot. Claims carried from cells without
   a synthesis re-read are marked CELL_READ or ABSTRACT_ONLY. One cell reading
   was corrected (C19).
3. Hallucinated experimental result: CLEAR. No experiment ran in this wave.
   Measured numbers come from committed receipts (smoke 452, probe 543) and
   registered simulations. The outcome ranges are labelled as judgement.
4. Shortcut reliance: PARTIAL. The literal-versus-semantic confound is removed
   by the non-literal MN leg. Script exposure, fertility and budget binding,
   the sink and layer averaging remain and are listed above.
5. Bug reframed as insight: FLAGGED. A NEGATIVE from an indexer that is flat on
   both non-literal legs would be a failure reframed as robustness. This is
   falsifier defect 1. Until it is repaired, any NEGATIVE must be reported
   beside G(MN) and Delta_ind.
6. Methodology fabrication: CLEAR. Only registered methods are described. The
   proposed controls are labelled not registered.
7. Frame-lock: MANAGED. The cross-lingual selector literature (C14, C15)
   predicts a small effect. This wave records that prior and the possibility
   that the screen cannot answer at 0.6B, instead of defending a GO frame.

## Negative-Result Value

Every branch yields a result:

- **ESCALATE_OR_STOP at the pre-check.** The first measurement of a 0.6B
  base's dense cross-script selection headroom and answering accuracy at 8K,
  with needle-absent and no-haystack references, for about 0.19 GPU-hours. It
  settles the 0.6B rung and prices the 4B decision. It is the most likely
  branch.
- **UNINTERPRETABLE on the audit read.** The same, at audit precision and with
  per-language tables.
- **HOLD.** The KL indexer matches its target on English literal retrieval
  within the registered tolerance. That is a distillation-fidelity finding,
  consistent with Oracle-Guided Table 9. Its terminal status for the id is the
  registered cost.
- **NEGATIVE (if reached).** A localization negative for 0.6B block-form
  indexers trained without the evaluation languages. It must be read beside
  G(MN) until falsifier defect 1 is repaired, and it is scoped to weak
  alignment and to an indexer with bilingual exposure.
- **GO.** The first component-level localization of a cross-lingual
  long-context gap in a selection mechanism. It is labelled "cross-lingual
  excess on cross-script pairs" unless the descriptive attribution and the M2
  per-direction pattern allow more.
- **Any branch** also publishes:
  - the seed SD of indexer recall, which no indexer paper reports;
  - per-language dense block top-k recall;
  - the LR-freeze record;
  - a portable per-language selection-recall instrument.
- **This gauntlet's own negative value.** It documents, before any GPU is
  spent, that the screen's decisive outcomes at 0.6B are narrow and why. That
  is the input Kevin needs for D24.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx (alphaXiv, OpenAlex) reachable and used by all three cells; cutoff 2026-10-07; degraded coverage recorded in the header (no arXiv API, Semantic Scholar or relay; no OpenReview, code, patents, social media); 50 cited primary pages snapshotted with HTTP 200 and hashed (bundle snapshots/) | Use the host relay for Semantic Scholar and the arXiv API in any later wave; record OpenReview access |
| Citation | PASS | Claim registry C01–C46 with locator, date and status. 32 claims re-read in full text by synthesis or read from the repository. The rest are marked CELL_READ or ABSTRACT_ONLY and are not load-bearing. Dates and authors come from hashed abs-page snapshots. One cell misreading corrected (C19). Followed the rule's claim-registry, tracing and cross-reference structure; the ARS file was not opened | Independent line-by-line audit by a fresh reader; re-read C32 production reports in full by synthesis |
| Novelty | FAIL | No direct prior found by any cell (NARROWED, core STILL_OPEN), but coverage is incomplete: no citation-graph expansion, no code or model-card search, no OpenReview, no XProvence title-phrase query, one Chinese query. Blind closest-prior discrimination (paragraphs in bundle blind/) and the novelty refuter have not run | Run the blind discrimination on the bundle's two paragraphs. Expand forward citations of 2606.07703, 2608.26175, 2601.18886 and 2410.13276 through OpenAlex or the relay. This needs new query budget, since the declared 150 is spent |
| Design | FAIL | Intervention, controls, metrics, statistics and leakage checks are fully specified (validator PASS, contract BLOCKED), but the falsifier is defective. NEGATIVE is not identified against an indexer flat on both non-literal legs (xi = −Delta_T, xi_rel = 0; E5), and it is probably unreachable (H1 ≥ 20 against about 14 points pooled development headroom; E1). The cross-script attribution is confounded with script exposure and fertility (E4) | New experiment id with a non-literal adequacy floor on NEGATIVE, plus either a seen-script cross-script condition or attribution scoped to "trained without these scripts". The owner decides whether to repair before admission |
| Compute | FAIL | Registered caps 8.05 GPU-h exceed the 8 GPU-h threshold (D22), so v2 is not frozen. Image B2, filled v2 manifests, the v2 smoke and a v2 Slurm dry-run do not exist. What exists is the tabled code's real model loop in probe 543 (digest-pinned image, Slurm, provenance PASS, dry-run and test-only exit 0). No signed compute attestation can exist yet (D24). The doctor's manifest schema rejects the executed probe manifest | Kevin's admission decision (D24); then freeze, build image B2, run both doctors in it, fill manifests, dry-run, and the registered gate jobs |
| Safety | PASS | Licences stated per source (C46), TED2020 excluded (D4), no text redistribution, no employer or private data, monitorability and red lines stated, integrity gate answered for seven modes | Open and record the Common Crawl terms of use; keep the bundle free of full texts |

Deterministic doctor (`uv run python scripts/research_direction_doctor.py program/proposals/2026-10-07-q3-k1-localization-screen-v2.md`),
output verbatim from the run on this file and its bundle:

```json
{
  "acceptedScore": 0,
  "doctorStatus": {
    "Citation": "PASS",
    "Compute": "FAIL",
    "Design": "FAIL",
    "Novelty": "FAIL",
    "Safety": "PASS",
    "Source": "PASS"
  },
  "evidenceBundleLoaded": true,
  "hardCaps": [
    89
  ],
  "issues": [
    "Novelty doctor lacks PASS plus concrete evidence",
    "Design doctor lacks PASS plus concrete evidence",
    "Compute doctor lacks PASS plus concrete evidence",
    "Reviewer A lacks structured PASS attestation",
    "Reviewer B lacks structured PASS attestation",
    "evidence bundle requires exactly two review artifacts",
    "protected external trust store is not configured; set COTCODEC_TRUSTED_ATTESTORS_PATH in trusted CI",
    "reviewers must use different providers; degraded review cannot score 100",
    "reviewers must have distinct nonempty run IDs",
    "two distinct trusted reviewer signatures are required for 100",
    "repository real model loop is still a stub",
    "compute manifest is invalid: image must contain a full immutable OCI digest",
    "compute container_smoke did not pass",
    "compute slurm_test did not pass",
    "compute provenance_verification did not pass",
    "doctor artifact 2 did not pass",
    "doctor artifact 3 did not pass",
    "doctor artifact 4 did not pass",
    "evidence bundle lacks audit_log artifact"
  ],
  "path": "/Users/kevinliu/repos/cotcodec-wt-gauntlet-k1/program/proposals/2026-10-07-q3-k1-localization-screen-v2.md",
  "remediation": [
    "Novelty doctor lacks PASS plus concrete evidence"
  ],
  "reviewerTotals": {
    "A": 0,
    "B": 0
  },
  "sourceCounts": {
    "allUrls": 50,
    "recognizedPrimaryUrls": 50
  },
  "status": "FAIL"
}
```

## Independent Adversarial Reviews

Reviewer A: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Reviewer B: NOT_RUN | provider=none-yet | model=none-yet | run_id=none-yet | artifact=none-yet

Wave 1 has produced only the synthesis. The loop's order is blind closest-prior
discrimination, then the refute-first triad, then two provider-distinct
reviewers. None has run. Even when they do, no review can count toward a 100:

- That requires Ed25519-signed review receipts whose keys come from an external
  trust store pinned by protected CI.
- That store does not exist, and only Kevin can set it up (D24).
- D23 also records that no OpenAI key is available and that the Moonshot
  account is suspended, so a second provider for this gauntlet would be
  self-hosted open-weight inference within the declared 1 GPU-hour.

The accepted score is capped at 89 by the missing independent review, and
cannot exceed 74 until the novelty coverage and blind discrimination are
complete.

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | Not yet reviewed in wave 1 (0 means unreviewed). Synthesis notes: Q3 is backfill; 0.6B is the weakest rung |
| Primary-source evidence | 0 | 0 | Not yet reviewed. Synthesis notes: 46-claim registry, 50 hashed snapshots, C32 cell-read only |
| Defensible novelty delta | 0 | 0 | Not yet reviewed. Synthesis notes: NARROWED; delta is the in-model own-target difference-in-differences; blind discrimination pending |
| Mechanism and falsifiability | 0 | 0 | Not yet reviewed. Synthesis notes: NEGATIVE not identified and probably unreachable at 0.6B |
| Controls and causal identification | 0 | 0 | Not yet reviewed. Synthesis notes: script-exposure and fertility confound of the attribution; weak alignment only |
| Evaluation and statistics | 0 | 0 | Not yet reviewed. Synthesis notes: simulated operating characteristics registered; interval coverage 96.3 to 96.7 in one regime |
| Feasibility and information per GPU-hour | 0 | 0 | Not yet reviewed. Synthesis notes: cheap pre-check first (0.19 projected); caps 8.05 over threshold |
| Reproducibility and artifact contract | 0 | 0 | Not yet reviewed. Synthesis notes: image B2 and v2 manifests do not exist; probe attestations only |
| Safety, data rights, and monitorability | 0 | 0 | Not yet reviewed. Synthesis notes: Common Crawl terms not opened |
| Independent adversarial review quality | 0 | 0 | No review exists; no trust store (D24) |
| **Total** | **0** | **0** | Unreviewed. Caps 74 (novelty coverage and blind discrimination), 79 (no executable pilot of the screen itself), 89 (no provider-distinct signed review) apply |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| 1 | 0 (unreviewed) | Synthesis owner's ranking: the registered falsifier is weak at 0.6B. NEGATIVE needs H1 ≥ 20 against about 14 points of pooled development headroom (E1), and the NEGATIVE region admits an indexer that is flat on both non-literal legs (E5). Second: the cross-script attribution is confounded with script exposure and fertility (E4) | Proposal written from the draft v2 registration and three discovery cells merged by mechanism. SeerAttention added as the 2024 origin of the baseline component. Claim boundary narrowed to Stage-1-type indexers and weak alignment. Kill-shot's C19 reading corrected. Registration not edited (D20) | Pending blind discrimination, refute-first triad and reviewers. The query budget was exceeded by the cells (159 against 150) before synthesis. D24 caps the gauntlet at an honest exit below 100 |

The evidence bundle `evidence/2026-10-07-q3-k1-localization-screen-v2/bundle.json`
holds the following, each hashed:

- 50 source snapshots;
- the query log;
- six doctor records;
- the compute record (probe attestations, with the screen's own attestations
  marked not run);
- the two anonymized mechanism paragraphs;
- the deterministic doctor's output.

It holds no review receipts and no audit JSONL row. The wave-1 row is appended
to `program/gauntlet/` after the reviewers score, so that the score in the
hash-chained row is a reviewer score and not a placeholder.
