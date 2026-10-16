# Novelty audit: memory credit, abstention keep rule, GDN state precision, local giant models

- Date: 2026-10-16. Repository: main at `b897c0dd`. Scope: decisions D111-D130 and
  their evidence bundles, and `paper/memory-keepset-note/note.md`.
- Question (Kevin): "is this a good novel finding?"
- Method: for each finding, one auditor and one adversarial refuter searched for
  prior work. This synthesis then re-checked the load-bearing priors and numbers.
  Where a refuter cited concrete prior work, the more skeptical rating is used.

## Short answer

No. None of the four is a new phenomenon, and as they stand none would change
what practitioners do.

- Two findings have a direct prior on nearly the same setup:
  - the abstention keep rule (B): Wang, Ma and Kumar, 2025-12-29;
  - the bf16 GDN-state accuracy loss (C): LeapQuant, 2026-09-29, on the same
    model family, the same engine and the same 81,920-token budget.
- What the program has, and the priors lack, is measurement quality:
  - exact 256-subset outcome tables;
  - preregistration;
  - bit-exact replay of 190,156 of 190,156 reader requests;
  - byte-identical independent reruns;
  - placebo arms.

The best result is the memory-credit table (A). It is the only measurement for
which no direct prior was found: keep-set regret, in correct answers, against
the exact optimum, on a real agent-memory benchmark. The claim it supports is
narrower than the current wording:

- leave-one-out (LOO) picks bad keep sets mainly because it measures marginals
  only at the full pool;
- exact Shapley and exact Banzhaf are near-optimal;
- about two-thirds of LOO's loss comes from the 27% of pools that the 8B reader
  gets wrong even with all 8 memories.

It is not evidence that "memory interactions defeat per-memory credit".

## Verdicts

| Finding | Novelty | Importance | Closest prior | Genuinely new | Bar it clears |
|---|---|---|---|---|---|
| A. Memory credit (AM1; H-A of `am1-keepset-search-v1`) | INCREMENTAL | LOW | Nematov et al. 2025 (exact 2^10 reference); MaxShapley 2025 (exact 2^6 Shapley, judged utility); theory: Wang et al. ICML 2024, Chi et al. 2025 | Keep-set regret against the exact optimum on LongMemEval-S; exact-truth scores for CMP's SNIPW and MeClear's permutation Shapley-16; the replay rigour | Workshop paper or technical report now; a main venue only after the experiments under "Best result" |
| B. Abstention keep rule (AM1d, H-C, AM3, AM5) | INCREMENTAL; the rule itself is KNOWN | LOW | Wang, Ma, Kumar 2025 (same stop rule over BM25-ranked windows); ChunkRank 2026; Self-Route 2024 | Overlapping-subset variant on agent-memory pools; three open readers; size-matched cost-against-gain accounting | Not on its own; a section of A's report, framed as a replication |
| C. GDN state precision (G2b, G2c, G3, G3b) | INCREMENTAL; the headline is KNOWN | LOW | LeapQuant 2026; DAMP 2026; ReplaySSM 2026 | The 4B; a vLLM fp16 arm; precision separated from block layout; a load and preemption dependence that is not yet identified | Blog post or engineering note; a workshop note only if a controlled preemption test confirms the load effect |
| D. Local 700B-1T models (dossier, G2, LM1, LM2) | KNOWN | LOW | ds4 `SSD_STREAMING.md`; Anemll README; GSQ 2026; Zhao et al. 2025 | V4 Flash 0731 ds4 Q2 against Q8 on unit-tested code: -13.3 [-26.7, 0.0] on 20 items | Internal note or blog post; not a research result |

Rating changes from the auditors:

- A's importance falls from MEDIUM to LOW. The refuter cited MaxShapley,
  Chi et al. 2025, Data Banzhaf and Beta Shapley.
- C's importance falls from MEDIUM to LOW. The refuter showed that fp32 is
  already the engine default, and cited the Qwen and NVIDIA model-card guidance
  and the ROCm/ATOM counter-example.
- B is rated INCREMENTAL by both agents. The synthesis read Wang, Ma and Kumar
  Section 2: it is the same stop rule. So the rule is rated KNOWN, and only the
  setting and the cost accounting are incremental.

## Best result, and what would make it strong

**Best: Finding A's exact keep-set table.** It is the only result where:

- the measurement itself has no direct prior under this coverage;
- the rigour is beyond any prior read;
- a reusable asset remains: 694 text-free exhaustive tables with bit-exact
  replay, against which any memory or context credit estimator can be scored.

Two experiments would most raise its importance.

1. **A stronger reader, with the full-pool-correct split as the registered primary estimand.**
   - Use fresh questions where possible (LongMemEval-M or LoCoMo); otherwise
     disclose the reuse.
   - Use one 32B-class open reader, and ideally a dense retriever as a second
     pool arm.
   - The 8B value to beat is LOO minus exact Shapley = +0.124 on the 182 pools
     the reader gets right (post hoc).
   - If the gap survives at 32B, the result is not a weak-reader artifact. If
     it collapses, as set-packing gains do with reader scale in What Survives
     Into Context (2607.00725), report that.
   - Cost: AM1's 8B tables took 1.54 GPU-h. A 32B reader is several times that
     (an estimate, not measured), so check it against the 8 GPU-h gauntlet
     threshold.
2. **The retention decision on a shared memory store.**
   - Setting: LoCoMo, where many questions share one conversation's memories.
     It is MeClear's setting.
   - Build exact tables per question over a common candidate pool.
   - Choose what to retain on training questions, either by pooled credit (LOO,
     permutation Shapley-16, SNIPW, exact Banzhaf) or by keep-set search.
   - Score the choice on held-out questions of the same conversation against
     the exact optimum.
   - Why it matters:
     - Deployed memory learners make this decision: MeClear, CMP, Hindsight
       Memory-PRM.
     - CMP itself says per-query utility is not enough for it.
     - No prior found scores it against exact truth.
     - It answers the refuter's strongest objection, that per-query
       keep-4-of-8 is only query-time context pruning (ContextCite, Nematov,
       MaxShapley).
   - This is the one experiment that could produce a new result rather than a
     better measurement of a known one.

## What is not novel and should not be claimed

- "Memory interactions defeat per-memory credit." Exact Shapley and Banzhaf,
  both additive per-memory credits, keep optimal sets in 95.6% and 96.4% of
  retrieved tables. A content-free reorder flips 17.1% of full-pool answers, so
  part of the order ≥ 2 share is position brittleness.
- "LOO is worse than Shapley or Banzhaf for selection" as a finding. This is
  shown in Ghorbani and Zou 2019, Nematov 2025, MaxShapley 2025, TracLLM 2025
  and MeClear 2026.
- "Top-k by credit is not the best k-subset" as a finding. This is shown in
  Wang et al. 2024 and Chi et al. 2025.
- "Search over keep sets beats credit at equal calls" as a general result:
  - its utility is an oracle that needs the reference answer;
  - there are only 70 candidates, and 37.5% of them are optimal on average;
  - its registered verdict is INCONCLUSIVE.
- That abstention-gated subset selection, or its cost on unanswerable
  questions, is new. See Wang, Ma and Kumar 2025, ChunkRank 2026, Self-Route
  2024 and RobustRAG 2024.
- "Token confidence is anti-informative" as a finding:
  - it was measured on 38 development tables for one reader;
  - the prompt asks for "I don't know";
  - ChunkRank finds that confidence works once abstentions are removed.
- That G3 "adds the accuracy number for vLLM's stock per-step cast" (D124).
  LeapQuant Table 1 already gives it: Qwen3.5-9B, vLLM, 81,920 tokens, AIME
  87.9 to 72.1.
- These parts of C, as new:
  - "fp16 is milder than bf16" (DAMP; Nemotron 3 Ultra);
  - "the loss is failure to finish" (ReplaySSM E.4.6-7; Lotfi et al. 2026);
  - "the throughput gain is eaten by longer reasoning" (Quantization Inflates
    Reasoning 2026).
- Any 700B-1T streaming speed as a program measurement. These are first-party
  numbers from ds4 and Anemll.
- "2-bit loses code accuracy" as new. Zhao et al. 2025 measured LiveCodeBench
  -12.8 for DeepSeek-V3-0324 at Q2_K_L.
- "No difference among resident models" as equivalence. The minimum detectable
  difference is 16-30 points.

## Finding A: memory credit

**Claim.** LongMemEval-S; Qwen3-8B reader; Qwen3-32B judge; exact 256-subset
tables over BM25 top-8 user-turn pools; keep 4 of 8.

1. Keeping the top 4 by LOO credit has regret 0.277 [0.223, 0.333], which is
   +0.233 [0.194, 0.273] over exact Shapley (0.044). Exact Banzhaf's regret is
   0.025. All five registered rules are MISSPECIFIED.
2. The order ≥ 2 Fourier share is +0.156 above an AND/OR baseline
   (descriptive).
3. With an oracle utility, best-of-m random search beats the sampled credit
   rules in 6 of 7 comparisons. H-A is INCONCLUSIVE.

**Rating.** INCREMENTAL / LOW.

**Why it is not new.**

- LOO is worse than Shapley when items are redundant or complementary:
  - Ghorbani and Zou 2019, for data;
  - Nematov et al. 2025, against an exhaustive 2^10 reference;
  - MaxShapley 2025, with exact 2^6 Shapley on an LLM-judge utility that sees
    the reference answer;
  - TracLLM 2025;
  - MeClear 2026, +25.5 pp [+20.9, +29.8] over LOO on LoCoMo memory faults.
- Top-k by per-item credit need not be the best k-subset:
  - Wang et al. 2024: Theorem 2, and Remark 4 for all semivalues including LOO
    and Banzhaf;
  - Chi et al. 2025: semivalue top-k as a myopic approximation of the exact
    optimum.
- The observed ordering (exact Banzhaf ≤ exact Shapley < sampled estimators <
  LOO) is what data-valuation work predicts:
  - Beta Shapley: LOO weights only size n-1, where marginals are noisy;
  - Data Banzhaf: Banzhaf is the most robust semivalue;
  - Wang et al. 2024, Theorem 6: Shapley top-k is optimal for
    monotone-transformed modular utilities.
- Joint need and set-level selection on memory benchmarks are already shown:
  CMP 2026, DRSR 2026, Relevance Is Not Sufficiency 2026 and MemPursuit 2026.
- Claim 3 is the wrapper-versus-filter point (Kohavi and John 1997). It is
  routine in DSPy and is reported for in-context examples by Schoch and Ji
  2025.

**What is genuinely new.**

- Keep-set regret in correct answers against the exact keep-4 optimum, from 694
  exhaustive judged tables, on a real agent-memory benchmark. MaxShapley scores
  rank agreement with exact Shapley, and Nematov scores removal-set precision on
  a log-likelihood utility; neither scores keep-set regret. No direct prior art
  found through 2026-10-16 under the coverage in the Appendix.
- The first exact-truth scores found for two rules that 2026 memory learners
  use: CMP's SNIPW-64 (0.094; 0.085 over 200 seeds, with no 99% interval) and
  MeClear's permutation Shapley-16 (0.138).
- Rigour that no prior read matches:
  - preregistration in a hash-chained ledger;
  - bit-exact replay (190,156 of 190,156 reader requests; 10,230 of 10,230
    judge items);
  - byte-identical reruns;
  - an independent reimplementation;
  - content-swap and reorder placebos.

**Synthesis recomputation.** From
`program/evidence/2026-10-16/am1-confirmatory/analysis/tables.json.gz`, on the
retrieved arm's non-constant tables at B = 4 (post hoc, not registered):

| Pools | Tables | LOO regret | Exact Shapley | Exact Banzhaf |
|---|---:|---:|---:|---:|
| All non-constant | 251 | 0.277 | 0.044 | 0.025 |
| Reader right with all 8 | 182 | 0.135 | 0.011 | 0.005 |
| Reader wrong with all 8 | 69 | 0.651 | 0.130 | 0.075 |

- 64.6% of LOO's total regret comes from the 69 full-pool-wrong tables. In 25
  of them all LOO credits are tied. In 19 of the 182 full-correct tables all LOO
  credits are zero, which is the redundancy failure Ghorbani and Zou describe.
- On full-correct pools, LOO minus exact Shapley is 0.124. The auditor's post
  hoc bootstrap gives [0.098, 0.153], about half the registered +0.233.
- Exact Shapley's keep set is optimal in 95.6% of retrieved tables (96.1% over
  both arms, 539 tables). Exact Banzhaf's is optimal in 96.4%, and LOO's in
  45.4%.
- Optimal 4-subsets per table: mean 0.375, median 0.400. In 97.6% of tables an
  optimal 4-subset answers correctly. This corrects the auditor's "36%, median
  0.386"; the refuter's figures are right.

**Bounds on the claim.**

- One reader (Qwen3-8B, thinking off, 64 tokens), one dataset, BM25 pools of 8,
  a budget of 4, and a binary judge validated only by agent hand labels (κ 0.867).
- The 347 held-out questions were reused across three registrations, and there
  is no gauntlet score.
- Set-selection gains shrink with reader scale (2607.00725).

**Bar.** A workshop paper or technical report as it stands, with the narrower
claim and the priors below. The tables plus the replay harness are a plausible
benchmark-track resource. A main-venue paper needs experiments 1 and 2 above.

### Prior art, Finding A

Read levels:

- full: full text read;
- part: the named sections;
- abs: abstract or search snippet;
- S: the synthesis re-fetched the source and confirmed the quoted number or
  passage.

| Prior | Date | URL | Read | Overlap |
|---|---|---|---|---|
| Nematov et al., Source Attribution in Retrieval-Augmented Generation | 2025-07-06 (ECML-PKDD 2025) | https://arxiv.org/abs/2507.04480 | full (auditor); S | Exact 2^10 Shapley reference, LOO and sampled estimators, and an exhaustive search for the k-document removal set; log-likelihood utility, removal precision |
| Patel, Zhou, Fanti, MaxShapley | 2025-12-05 (v2 2026-05-19) | https://arxiv.org/abs/2512.05958 | part, Sections 1-4 (refuter); S | Exact Shapley over 2^6 sources with an LLM-judge utility that sees the reference answer; LOO under-credits redundancy |
| Wang, Yang, Zou, Kwon, Jia, Rethinking Data Shapley for Data Selection Tasks | 2024-05-06 (ICML 2024) | https://arxiv.org/abs/2405.03875 | part, through Section 5 (auditor) | Credit-based subset selection can be no better than random; Shapley top-k is optimal for monotone-transformed modular utilities |
| Chi et al., Unifying and Optimizing Data Values for Selection via Sequential Decision-Making | 2025-02-06 (v2 2026-05-29) | https://arxiv.org/abs/2502.04554 | part, Sections 3-4 and Appendix G (refuter); exists (S) | LOO, Shapley, Banzhaf and Beta Shapley top-k are myopic approximations of the exact DP optimum; (1-c)^2 bound |
| MeClear | 2026-09-08 | https://arxiv.org/abs/2609.09115 | part (auditor); S | LOO blind spot for redundant harm; permutation Shapley-16 beats LOO by +25.5 pp [+20.9, +29.8] on LoCoMo |
| DRSR | 2026-09-23 | https://arxiv.org/abs/2609.27276 | part, Sections 1-3 and 5.1 (auditor) | Singleton deletion scores do not determine set-deletion risk (58.9% pair accuracy) |
| CMP, Causal Memory Policy | 2026-10-01 (v3 2026-10-08) | https://arxiv.org/abs/2610.02070 | part (auditor) | SNIPW memory utility on LongMemEval and LoCoMo; memories needed jointly; never scored against an exact optimum |
| Ghorbani and Zou, Data Shapley | 2019-04 (ICML 2019) | https://arxiv.org/abs/1904.02868 | abs (refuter) | LOO fails under duplicates |
| Wang and Jia, Data Banzhaf | 2022-05 (AISTATS 2023) | https://arxiv.org/abs/2205.15466 | header only (refuter) | Banzhaf is the most noise-robust semivalue; the source of the MSR estimator tested here |
| Kwon and Zou, Beta Shapley | 2021-10 (AISTATS 2022) | https://arxiv.org/abs/2110.14049 | abs (refuter) | Large-cardinality marginals are noisy; LOO weights only size n-1 |
| ContextCite | 2024-09-01 (NeurIPS 2024) | https://arxiv.org/abs/2409.00729 | part, Sections 4-5.2 (auditor) | Top-k context pruning by attribution, with an LOO baseline; no exact-optimum regret |
| TracLLM | 2025-06 (USENIX Security 2025) | https://arxiv.org/abs/2506.04202 | abs and excerpts (auditor) | LOO is sub-optimal when texts jointly cause the output |
| Shapley Context Pruning | 2026-05-10 | https://arxiv.org/abs/2607.16209 | part (auditor) | LOO collapses under redundancy and Shapley resists it; learned value function |
| SETR, Shifting from Ranking to Set Selection for RAG | 2025-07-09 | https://arxiv.org/abs/2507.06838 | abs (refuter) | Set selection beats independent ranking for RAG |
| Relevance Is Not Sufficiency | 2026-10-07 | https://arxiv.org/abs/2610.09348 | abs (auditor) | Set-level memory sufficiency on LongMemEval-S, 72.4% to 82.2% |
| MemPursuit, Recall What Is Missing | 2026-10-11 | https://arxiv.org/abs/2610.15642 | abs (synthesis) | Set-level composition of memory evidence under a budget; +7.2 pp on LoCoMo at top-10 |
| What Survives Into Context | 2026-07-01 | https://arxiv.org/abs/2607.00725 | abs (refuter); exists (S) | The set-packing edge at 3B is absorbed by 7B and reverses by 14B; a reader-scale caveat |
| ProxySPEX (and SPEX, 2502.13870) | 2025-05-23 (NeurIPS 2025) | https://arxiv.org/abs/2505.17495 | abs (auditor) | Sparse interactions under context masking (relevant to claim 2) |
| Fryer, Strumke, Nguyen, Shapley values for feature selection | 2021-02 (IEEE Access) | https://arxiv.org/abs/2102.10936 | abs (auditor) | Shapley's axioms can work against subset selection |
| Kohavi and John, Wrappers for Feature Subset Selection | 1997 | https://doi.org/10.1016/S0004-3702(97)00043-X | not read; bibliographic | Wrapper versus filter (claim 3); outside the 2019-2026 window |
| Schoch and Ji, Monte Carlo Sampling for Analyzing In-Context Examples | 2025-05 (Insights workshop) | https://aclanthology.org/2025.insights-1.7/ | abs (refuter) | Valuation-inspired example selection loses to random sampling |
| Khattab et al., DSPy | 2023-10 | https://arxiv.org/abs/2310.03714 | introduction (refuter) | Random search over demonstration sets with a label-seeing metric |

## Finding B: abstention-aware keep rule

**Claim.** Read the 70 4-subsets in BM25 order and keep the first whose reply
does not abstain.

1. Token confidence is anti-informative (within-table AUROC 0.326; 38
   development tables; exploratory).
2. Preregistered on 347 held-out questions, the rule beats BM25 top 4 by:
   - +0.112 for Qwen3-8B (39:0);
   - +0.101 for OLMo-2-7B (35:0);
   - +0.089 for Qwen3.5-9B (31:0).
3. With the evidence removed, at K = 8, the cost is below the gain for the two
   Qwen readers (6/31 and 6/26). For OLMo-2 they are not separated (22/27).

**Rating.** INCREMENTAL / LOW. The rule itself is KNOWN.

**Why it is not new.**

- Wang, Ma and Kumar (2512.23836, 2025-12-29). The synthesis re-read Section 2.
  - The rule: a sliding window over BM25-ranked pages. If a window yields the
    answer, the model answers and stops; otherwise it says "Answer not found" and
    moves to the next window.
  - The gain: 57.8 EM on NQ, against 57.2 for feeding the top 100 pages at once.
  - So the program's rule is this one, with overlapping 4-subsets in place of
    disjoint windows.
- ChunkRank (2609.29828, 2026-09-24). No content ranker beats "first non-empty
  answer", and it states that abstention, not ranking, does the work.
- Two older uses of the same signal:
  - Self-Route (2024) escalates to the full context when the model says it
    cannot answer;
  - RobustRAG (2024) drops groups that say "I don't know".
- The confidence half is expected:
  - the prompt asks for "I don't know";
  - a generic "I don't know" is a known high-likelihood reply (Khayrallah and
    Sedoc 2020);
  - abstention inflation is a known prompt artifact (2507.16199);
  - ChunkRank finds that confidence works once abstentions are removed.

**What is genuinely new.**

- The rule tested on agent-memory pools, with overlapping subsets, for three
  open readers from two families, under frozen registrations with blind checks
  and byte-identical verification.
- A size-matched evidence-removed cost test, with break-even unanswerable
  shares of 0.84, 0.81 and 0.55. Mondal et al. (2609.32269) show why size
  matching matters.
- No paper found tests this exact overlapping-subset variant or its
  cost-against-gain trade-off in a memory keep-set setting.

**Synthesis recomputation.** This reran the auditor's post hoc comparison
against the Self-Route-style fallback (BM25 top 4, else all 8) on
`program/evidence/2026-10-15/am3-nonabstain-generality-v1/per-table.json.gz`.
The script is not committed. Every number matches the auditor's:

| Reader | Fallback vs BM25 top 4, answerable | Rule vs fallback, answerable | Exact p | Fallback vs rule, 30 abstention questions |
|---|---|---|---:|---|
| Qwen3-8B | 23:0 | 18:2 | 4e-4 | 4:0 |
| OLMo-2-7B | 15:0 | 25:5 | 3e-4 | 8:1 |
| Qwen3.5-9B | 24:0 | 10:3 | 0.09 | 1:0 |

Reading (post hoc, licenses nothing):

- The fallback, which is the prior-art baseline, recovers 43-78% of the rule's
  gain.
- Overlapping-subset search adds something beyond escalation for two readers.
- The fallback is safer on unanswerable questions.

The registered test was close to guaranteed:

- the judge marks every "I don't know" wrong on answerable questions;
- BM25 top 4 is itself 0.066 behind keeping all 8.

**Bar.** Not a standalone result. It is a section of A's report, citing Wang,
Ma and Kumar and ChunkRank as the direct priors. To stand alone it would need a
fresh-question registration against the Self-Route fallback, net of cost, in a
setting where the full pool does not fit in the reader's context.

### Prior art, Finding B

| Prior | Date | URL | Read | Overlap |
|---|---|---|---|---|
| Wang, Ma, Kumar, Retrieval Augmented Question Answering: When Should LLMs Admit Ignorance? | 2025-12-29 | https://arxiv.org/abs/2512.23836 | full (refuter); S | The same stop rule over BM25-ranked windows; compared against feeding all top-K at once; Gemini 1.5 Pro answers falsely on 54.3% of windows without the answer |
| ChunkRank | 2026-09-24 | https://arxiv.org/abs/2609.29828 | part, through Sections 7.1-8 (refuter); exists (S) | First non-empty answer is not beaten by content rankers; abstention does the work |
| Self-Route (Li et al.) | 2024-07-23 (EMNLP 2024 industry track) | https://arxiv.org/abs/2407.16833 | full (auditor); exists (S) | Abstention triggers escalation to the full context |
| RobustRAG | 2024-05 (v2 2026-04-01; SaTML 2026) | https://arxiv.org/abs/2405.15556 | full (auditor) | Isolated groups; drops groups whose reply says "I don't know" |
| Speculative RAG | 2024-07-11 (ICLR 2025) | https://arxiv.org/abs/2407.08223 | part (auditor) | Per-subset drafts selected by a label-free likelihood score |
| Sufficient Context (Joren et al.) | 2024-11-09 (ICLR 2025) | https://arxiv.org/abs/2411.06037 | full (auditor) | Insufficient context yields wrong answers more often than abstention; the mechanism behind the cost |
| Before Answering (Mondal et al.) | 2026-09-26 | https://arxiv.org/abs/2609.32269 | abs (auditor) | Deletion-built insufficient-evidence sets leak through size; AM5 is size-matched |
| LLM Abstention Can Be a Prompt Artifact | 2025-07-22 | https://arxiv.org/abs/2507.16199 | abs (refuter) | Offering an "Unknown" option inflates abstention |
| Khayrallah and Sedoc, the "I don't know" problem | 2020-10-24 | https://arxiv.org/abs/2010.12786 | abs and introduction (auditor) | "I don't know" is scored above the reference reply |
| Clark and Gardner, Simple and Effective Multi-Paragraph RC | 2017 (ACL 2018) | https://arxiv.org/abs/1710.10723 | abs (refuter) | Per-paragraph confidences are not comparable; outside the window |
| Answer-Convergence Stopping | 2026-09-28 | https://arxiv.org/abs/2609.34590 | abs (refuter) | Verbalized self-stop gates stop early on 8.4-45.6% of questions |
| Intrinsic Sequence-Likelihood Confidence (Lee et al.) | 2026-09-17 | https://arxiv.org/abs/2609.19942 | abs (auditor) | Preregistered: likelihood confidence fails as a RAG routing signal |
| LangChain MapRerankDocumentsChain | API reference v0.2 (2024; first release date unverified) | https://python.langchain.com/v0.2/api_reference/_modules/langchain/chains/combine_documents/map_rerank.html | snippets (refuter) | Answer per document and select by a reader-derived score; practitioner tooling |

## Finding C: GDN recurrent-state precision

**Claim.** Qwen3.5-4B and 9B, stock vLLM 0.31.0, Triton GDN decode path.

- bf16 state:
  - gives 1.33-1.38x tok/s on 2K waves;
  - costs about 10 points of MATH-500 level 5 at a 32K cap, almost all through
    rollouts that reach the cap;
  - loses 13-22 points on 51 hard questions at 81,920 tokens.
- fp16 costs about 3 points (marginal).
- The gap is about 15 points larger with no preemption. Concurrency also
  changed.
- Solved problems per engine-second fall about 20%.

**Rating.** INCREMENTAL / LOW. The headline is KNOWN.

**Why it is not new.** The synthesis confirmed the numbers below from the full
texts.

- LeapQuant Table 1: Qwen3.5-9B in vLLM, model-card sampling, an 81,920-token
  budget, per-step BF16 state:
  - AIME 87.9 to 72.1;
  - GPQA-D 81.3 to 66.2;
  - LCB 64.1 to 49.6.
- DAMP, on Qwen3.6-35B-A3B in SGLang: BF16 AIME 2026 85.46 to 79.71, and FP16
  within 0.2-1.75 points of FP32.
- Other parts already shown:
  - the length mechanism and the stochastic-rounding fix: Nemotron 3 Super and
    Ultra;
  - the budget-hit accounting, and "prefill computes the state at full
    precision": ReplaySSM;
  - the end-to-end cost of token inflation: Quantization Inflates Reasoning.
- The practical lesson is already the default and already documented:
  - fp32 is what vLLM's `auto` resolves to;
  - NVIDIA's Nano 2 card (2025-08-18), Olmo Hybrid and the Qwen3.5-397B
    discussion say the same.

**What is genuinely new.**

- Coverage of the 4B, which LeapQuant does not test.
- A three-arm fp32/fp16/bf16 test in vLLM.
- G2c's separation of precision from the block-layout change.
- A recomputable per-request dataset.
- Load and preemption dependence. No prior found through 2026-10-16 under this
  coverage, but it is weakly identified:
  - the G3b contrast also changes concurrency (23 against 114-128);
  - one run per arm;
  - 51 questions selected on G3's outcomes;
  - no per-request preemption record;
  - the 9B seed pattern does not track the hypothesis;
  - it follows from ReplaySSM's prefill statement and from LeapQuant's
    per-window recovery.
- The model dependence cuts against importance. ROCm/ATOM #2403 reports
  identical GPQA-D (0.808 against 0.808) for bf16 and fp32 on Qwen3.8-27B at
  229,376 tokens.

**Bar.** A blog post or engineering note that cites LeapQuant as the source of
the headline. It becomes a workshop-level methods note only if a controlled
test supports the claim that "evaluations on loaded servers understate 16-bit
state cost". That test runs at fixed concurrency, toggles preemption, and
records per-request preemption counts.

### Prior art, Finding C

| Prior | Date | URL | Read | Overlap |
|---|---|---|---|---|
| LeapQuant (Pan, Xi, Zhu et al.) | 2026-09-29 | https://arxiv.org/abs/2609.38166 | full (auditor, refuter); S | Same model family, engine, budget and sampling; BF16 state costs 15+ points on long reasoning |
| DAMP | 2026-08-27 | https://arxiv.org/abs/2608.27513 | full (auditor); S | bf16 is worse than fp16 on a Qwen GDN hybrid in SGLang |
| ReplaySSM (Liou ... Dao) | 2026-10-09 | https://arxiv.org/abs/2610.13778 | full (auditor, refuter); S | Prefill at full precision; budget-hit accounting (20.7% against 5.7%); Qwen3.5-4B Math-L5 |
| Nemotron 3 Super technical report, Section 4.3 | 2026-04-14 | https://arxiv.org/abs/2604.12374 | part (auditor) | FP16 RTN Mamba cache lengthens LCB outputs by 36.95%; SR fixes it |
| Nemotron 3 Ultra technical report, Section 4.5 | 2026-06-12 | https://arxiv.org/abs/2606.15007 | part (auditor) | FP16 RTN: -1.07% accuracy and +9.98% verbosity; SR shipped |
| Olmo Hybrid, Section 5.3 | 2026-04 (v4) | https://arxiv.org/abs/2604.03444 | part (auditor) | A 16-bit GDN cache in vLLM costs accuracy; keep fp32 |
| NVIDIA-Nemotron-Nano-9B-v2 model card | 2025-08-18 | https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2 | relevant section (auditor) | "Without this option, the model's accuracy may degrade" (fp32 SSM cache) |
| Qwen3.5-397B-A17B discussion #2 | Feb 16 (no year shown; Qwen3.5 release window) | https://huggingface.co/Qwen/Qwen3.5-397B-A17B/discussions/2 | WebFetch (refuter) | vLLM reads the mamba ssm dtype from the config; quality warning for bf16 |
| ROCm/ATOM PR #2403 | 2026-09-25 (S, via gh) | https://github.com/ROCm/ATOM/pull/2403 | full (refuter) | Counter-example: bf16 equals fp32 on GPQA-D for Qwen3.8-27B |
| mlx-serve issue #814 | 2026-10-11 (S, via gh) | https://github.com/ddalcu/mlx-serve/issues/814 | full (refuter) | bf16 GDN state hurts the per-token decode path more than chunked prefill; weak evidence |
| Low-Discrepancy Dither for Quantized Recurrent State Caches | 2026-09-30 | https://arxiv.org/abs/2609.39185 | part (auditor) | RTN error grows over long decoding; short evaluations pass |
| When Dynamic Scaling Fails (scale-state feedback) | 2026-10 | https://arxiv.org/abs/2610.15139 | full (auditor) | Per-step state quantization errors compound in the recurrence |
| Quantization Inflates Reasoning | 2026-06-24 | https://arxiv.org/abs/2606.25519 | abs and grep (refuter) | Token inflation consumes the per-token speedup |
| Lotfi et al., Quantized Reasoning Models Think They Need to Think Longer | 2026-05-29 | https://arxiv.org/abs/2606.00206 | abs (refuter) | Loss through failure to finish under weight PTQ |
| Yuan et al., Give Me FP32 or Give Me Death? | 2025-06-11 (v2 2025-10-24) | https://arxiv.org/abs/2506.09501 | search summary (refuter) | bf16 reasoning evaluations vary with batch size and GPU count |
| vLLM blog, 25K TPS/GPU on Qwen3.5 | 2026-08-06 | https://vllm.ai/blog/2026-08-06-qwen35-25k-tps | WebFetch (auditor) | Practice context: recommends bf16 state, validated only on GSM8K |

## Finding D: 700B-1T open MoE models on a 128 GB machine

**Claim.**

- GLM 5.3 streams at about 4-5 tok/s and Kimi K2.5 at about 2-3 tok/s.
- Kimi loses knowledge at about 2 bits.
- LM2 (20 items × 3 seeds, chat tier, CUDA):
  - no resolved difference among resident models;
  - V4 Flash ds4 Q2 minus Q8 on code is -13.3 [-26.7, 0.0].
- G2 and LM1 were closed at gauntlet scores of 53 and 56.

**Rating.** KNOWN / LOW. Both agents agree.

**Why it is not new.**

- The speeds are first-party measurements by others: the ds4 maintainer
  (2026-09-06) and Anemll's README.
- The Kimi knowledge loss is GSQ's number. GSQ's own K2.6 run with broader
  calibration shrinks it to 4.05 points, and the program never ran Kimi on
  tasks.
- The resident-model tie was already published on the target machine:
  GitButler, 2026-08-12, 122/132 each.
- The 2-bit code loss is the pattern Zhao et al. measured on DeepSeek-V3-0324
  (Q2_K_L LiveCodeBench 49.73 to 36.95, confirmed by the synthesis), with
  3-bit near-lossless.
- D130's advice appears in a public 128 GB guide dated 2026-08-15.

**What is genuinely new.**

- A checkpoint-specific paired comparison (V4 Flash 0731 ds4 Q2 and UD-IQ3_XXS
  against UD-Q8_K_XL) on post-cutoff tasks, with unit-tested code and a
  reproducible analysis script. It is weak:
  - the interval reaches 0.0;
  - 20 items;
  - a budget chosen after the runs;
  - CUDA, not Metal;
  - no thinking modes.
- An audited dossier with byte-per-token figures from the GGUF tensor tables.

**Bar.** An internal note or blog post. A powered ladder evaluation would
mainly reproduce Zhao et al.'s pattern on a newer checkpoint.

### Prior art, Finding D

| Prior | Date | URL | Read | Overlap |
|---|---|---|---|---|
| antirez/ds4, `docs/SSD_STREAMING.md`, "M5 Max measurements" (first-party) | measurements 2026-09-06 | https://github.com/antirez/ds4/blob/master/docs/SSD_STREAMING.md | full (auditor) | GLM 5.3 IQ2_XXS at 4.09-5.11 tok/s on a 128 GB M5 Max |
| Anemll/anemll-flash-llama.cpp README (first-party) | repo 2026-03-31, last push 2026-10-07 | https://github.com/Anemll/anemll-flash-llama.cpp | Kimi section in full (auditor) | Kimi K2.5 at 2.2 tok/s at top-8 and 3.2-3.3 at top-4 |
| GSQ | 2026-04 (v2 2026-05-15) | https://arxiv.org/abs/2604.18556 | part, Section 4.3 and Appendix D (auditor) | Kimi K2.5 at 2.13 bits: GPQA-D 89.29 to 76.57; K2.6 with broader calibration: -4.05 |
| Zhao et al., Quantitative Analysis of Performance Drop in DeepSeek Model Quantization | 2025-05 (v2 2025-06-13) | https://arxiv.org/abs/2505.02390 | full (refuter); S | DeepSeek-V3-0324 Q2_K_L: LCB -12.8, GPQA -13.7; 3-bit variants within about 1-3 points |
| GitButler, Local Model Performance on an M5 Max | 2026-08-12 | https://blog.gitbutler.com/local-llm-gauntlet | WebFetch (auditor) | gpt-oss-120B and V4 Flash ds4 2-bit tie at 122/132 |
| Unsloth Dynamic GGUFs on Aider Polyglot | 2025 (page undated; the dossier records 2025-09-10) | https://unsloth.ai/docs/basics/unsloth-dynamic-ggufs-on-aider-polyglot | WebFetch (auditor) | DeepSeek-V3.1 at 2 bits loses 6-9 points on Aider |
| oobabooga benchmark | updated 2026-01-08 | https://oobabooga.github.io/benchmark.html | WebFetch (auditor) | Size-sorted matched-memory table; the giant at about 1.8 bits loses |
| AtomicChat dsv4-eval-artifacts | 2026-08-03 | https://huggingface.co/datasets/AtomicChat/dsv4-eval-artifacts | dossier extraction (auditor) | V4 Flash 0731 KLD ladder predicts LM2's ranking |
| kingy.ai, DeepSeek V4 Flash IQ2 vs IQ3 | 2026-08-02 (modified 2026-10-14) | https://kingy.ai/ai/ai-guides/deepseek-v4-flash-0731-best-quant/ | WebFetch (auditor) | IQ2_M against IQ3_XXS: 318 against 320 of 426; no Q8 |
| openclawdc, DeepSeek V4 Flash vs gpt-oss-120b | 2026-08-15 | https://openclawdc.com/blog/deepseek-v4-flash-vs-gpt-oss-120b/ | WebFetch (refuter) | The same advice as D130, with no measurements |
| Dettmers and Zettlemoyer, k-bit Inference Scaling Laws | 2022-12-19 | https://arxiv.org/abs/2212.09720 | abs (refuter) | 4-bit is near-optimal at fixed total bits |
| Giagnorio et al., Quantizing LLMs for Code Generation | 2025-03 | https://arxiv.org/abs/2503.07103 | secondary (auditor) | Code is sensitive below 4 bits (dense models) |
| LLM in a flash (Apple) | 2023-12 (v3 2024-07-30) | https://arxiv.org/abs/2312.11514 | full (auditor) | The origin of flash streaming on Macs |
| SSD-LLaMA | 2026-09-16 | https://arxiv.org/abs/2609.18110 | abs (auditor) | A 1T MoE at more than 1 tok/s from SSD on a consumer PC |
| MawForge | 2026-06-17 | https://arxiv.org/abs/2607.09686 | part (refuter) | Bounded expert cache on an M5 Pro; hit-rate and speed trade-offs |
| Deltafin write-up (self-reported) | 2026-09-09 | https://umesh-malik.com/blog/run-kimi-k3-locally-macbook-ssd-streaming | WebFetch (refuter) | Kimi K3 (2.8T) at about 1 tok/s on a 128 GB M5 Max |

## Corrections the program's records need

These are listed here only. This audit edits no other file.

- **D124 and the G3 README.** Replace "G3 adds the accuracy number for vLLM's
  stock per-step round-to-nearest cast" with a replication framing, and cite
  LeapQuant (2609.38166) and DAMP (2608.27513).
- **The memory note, Section 8.**
  - For Result 1, add MaxShapley, Wang et al. 2024, Chi et al. 2025, Data
    Banzhaf, Beta Shapley, Ghorbani and Zou, TracLLM, and ContextCite Section
    5.2. Also state MeClear's +25.5 pp over LOO and DRSR's singleton-aggregation
    failure as direct directional priors.
  - For Result 2, add Kohavi and John, DSPy, and Schoch and Ji.
  - For Result 3, add Wang, Ma and Kumar 2025, ChunkRank, Self-Route and
    RobustRAG as the direct priors.
  - The note's current "no novelty claim for Results 2 and 3" is correct and
    should stay.
- **Wording of the memory line (D112, D117, D126).** "Per-memory deletion credit
  picks the wrong memories" is accurate for LOO. Do not generalise it to
  per-memory credit as such: exact Shapley and Banzhaf are near-optimal.
- **D130.** Cite Zhao et al. 2025 for the 2-bit code deficit, and the openclawdc
  guide for the advice.
- **The Finding A auditor.** The optimal-set density is mean 0.375 and median
  0.400. Exact Shapley's 96.1% optimal rate is over both arms; on the retrieved
  arm it is 95.6%.

## Coverage and limits

- Per finding, the auditor and the refuter together ran these searches (exact
  queries in the Appendix):

  | Finding | orx queries | Web searches | Other |
  |---|---:|---:|---|
  | A | about 30 | about 12 | GitHub and Hugging Face API searches |
  | B | about 45 | 6 | GitHub and Hugging Face searches |
  | C | about 20 | 10 | GitHub issue searches across vLLM and SGLang |
  | D | about 28 | 14 | GitHub API calls and WebFetch |

- OpenAlex returned HTTP 429 for every agent, so venue and citation-graph
  coverage is thin.
- The alphaXiv index skews to 2026, and pre-2025 coverage relied on
  date-bounded queries and web search.
- Not searched directly: Reddit, X, Chinese-language sources.
- OpenReview-only items cited by the earlier sweep ("MemAttr", "Write-Back
  Redundancy Breaks LOO Attribution") could not be found.
- Several 2026 priors were read at abstract level only, as the tables mark.
- Not re-verified by the synthesis: the Hugging Face discussion, the
  openclawdc, GitButler and kingy.ai pages, and the ds4 and Anemll READMEs.
  These rely on the agents' reads.
- No direct prior art found through 2026-10-16 under this coverage for:
  - A's exact keep-set regret measurement;
  - B's overlapping-subset variant with size-matched cost accounting;
  - C's load and preemption dependence.
- None of these absences is evidence of novelty beyond that coverage.

## Appendix: queries

### Synthesis (this author, 2026-10-16)

orx `discover`:

1. embedding, after 2025-06-01: "exhaustive evaluation of every subset of an
   agent's retrieved memories to find the best keep set; regret of
   leave-one-out and Shapley memory credit against the exact optimum". Found
   MemPursuit 2610.15642, What Should an Agent Remember 2610.00366 and
   UpliftMem.
2. embedding, after 2025-06-01: "accuracy evaluation of a low-precision
   recurrent state on a loaded inference server understates the cost because
   preemption recomputes the state at full precision during prefill". Found
   2610.15139 and 2609.39185, both already cited, and nothing on preemption.
3. keyword: "preemption recompute mamba state precision". Nothing relevant.
4. embedding: "leave-one-out context attribution fails when the model answers
   incorrectly with the full context; marginal contributions at the grand
   coalition are zero". Nothing relevant.
5. embedding, after 2025-01-01: "query the reader on successive subsets of
   retrieved passages in ranked order and stop at the first subset whose answer
   is not a refusal". Found SERBench 2609.20050 (set sufficiency for coding
   agents), and nothing closer than Wang, Ma and Kumar.
6. keyword: "DeepSeek-V4-Flash quantization LiveCodeBench". No task-level quant
   evaluation.
7. keyword: "Banzhaf memory agent keep". Nothing relevant.
8. embedding, after 2025-06-01: "set-level evidence selection benefit shrinks or
   reverses as the reader language model gets larger under a fixed context
   budget". Nothing closer than 2607.00725.
9. keyword: "mamba-ssm-cache-dtype bfloat16 MATH-500". Found ReplaySSM, already
   cited.

orx `paper` checks:

- Existence: 2512.05958, 2512.23836, 2609.29828, 2609.38166, 2505.02390,
  2507.04480, 2608.27513, 2502.04554, 2407.16833, 2609.09115, 2607.00725,
  2609.14245.
- `--full` with grep: 2609.38166, 2512.05958, 2505.02390, 2512.23836,
  2608.27513, 2609.09115, 2507.04480, 2610.13778.

Web and GitHub:

- WebSearch: "vLLM preemption recompute mamba ssm state bf16 accuracy long
  reasoning Qwen3.5". No source on accuracy under preemption.
- WebSearch: "exact Shapley all subsets agent memory keep set leave-one-out
  regret LongMemEval 2026". Nothing matching; the nearest is 2606.20954
  (session-level eviction on LongMemEval-S, snippet only).
- `gh pr view 2403 -R ROCm/ATOM` and `gh issue view 814 -R ddalcu/mlx-serve`.

### Finding A (auditor and refuter)

- orx embedding:
  - LOO attribution of retrieved documents fails to select the best context
    subset;
  - per-document attribution against subset search with interacting passages
    (historical);
  - exhaustive evaluation of all subsets of retrieved passages against
    per-passage attribution (historical);
  - Shapley-based selection is suboptimal for subset selection (historical);
  - LOO against Shapley data valuation for subset selection (before
    2025-06-30);
  - set selection of RAG passages instead of independent ranking (before
    2025-12-31);
  - agent memory eviction by deletion or Shapley credit on LongMemEval (after
    2025-06-01);
  - Shapley interaction index between retrieved documents;
  - random search over in-context demonstrations against selection methods
    (before 2025-12-31);
  - oracle access to subset correctness, credit estimation against direct
    search at matched calls;
  - plus 9 refuter embedding queries on data valuation, semivalues, set
    selection and reader scale.
- orx keyword:
  - "leave-one-out Shapley context selection RAG subset";
  - "context attribution leave-one-out exact Shapley retrieved documents"
    (decode error);
  - "Rethinking Data Shapley for Data Selection Tasks";
  - "Source Attribution in Retrieval-Augmented Generation";
  - "context pruning Shapley retrieved documents subset" (before 2025-12-31);
  - "LongMemEval Shapley memory";
  - "keep set memories leave-one-out regret";
  - "Banzhaf context attribution language model documents";
  - "spectral explainer interactions LLM context Fourier sparse";
  - "best subset retrieved passages exhaustive 2^k LLM answer correctness
    oracle";
  - plus 3 refuter keyword queries.
- orx openalex: "data Shapley data selection misleads merits" and "Rethinking
  data Shapley for data selection tasks", both HTTP 429.
- WebSearch:
  - exhaustive subset evaluation against attribution top-k;
  - LOO against Shapley for context pruning (ContextCite, TracLLM);
  - random search over demonstration subsets;
  - ProxySPEX and SPEX;
  - Fryer et al.;
  - "Write-Back Redundancy Breaks LOO" (not found);
  - 2026 memory selection with exact Shapley and LongMemEval;
  - plus 8 refuter web searches.
- GitHub repository searches (no results). Hugging Face datasets and papers
  search on LongMemEval and LOO-Shapley context selection.

### Finding B (auditor and refuter)

- orx keyword:
  - "unanswerable fall back long context self-route";
  - "self-route unanswerable RAG long-context fallback";
  - "retrieve again when model says I don't know";
  - "LongMemEval abstention retrieval subset reader";
  - "token probability confidence abstention I don't know most confident
    anti-calibrated";
  - "Self-Route unanswerable long-context RAG routing" (before 2025-12-31);
  - "sufficient context RAG selective generation" (before 2025-12-31);
  - "sufficient context selective generation abstention RAG hallucinate
    insufficient context";
  - title checks for FLARE, CRAG, Self-RAG and DRAGIN;
  - "generic responses I don't know high probability maximum likelihood
    decoding" (before 2023);
  - "isolate-then-aggregate abstained responses retrieved passages groups";
  - "Chain-of-Note unknown irrelevant retrieved documents reading notes"
    (before 2024).
- orx embedding:
  - reader abstention as a label-free keep signal;
  - per-subset answers ignoring refusing subsets;
  - likelihood-based selection prefers refusals;
  - per-subset drafts with a verifier (before 2025-12-31);
  - a sequential cascade over contexts with abstention as the deferral signal;
  - selecting among context answers by likelihood fails;
  - moving down the ranked list until the model stops saying "unanswerable".
- About 22 further refuter orx queries, keyword and embedding, with date bounds
  and popular or historical ranking.
- OpenAlex (3 attempts, HTTP 429), then the OpenAlex API directly, with 3
  queries.
- WebSearch:
  - Speculative RAG;
  - ADAPT-LLM;
  - IDK confidence calibration;
  - RAG retry with a different passage subset on "unanswerable";
  - plus 4 refuter searches.
- GitHub: "self-route rag unanswerable long context", with no results, and
  further repository searches. Hugging Face papers API: abstention-triggered
  retrieval fallback.

### Finding C (auditor and refuter)

- orx keyword:
  - "mamba ssm cache dtype bf16 accuracy" (after 2024-01-01);
  - "recurrent state precision bfloat16 linear attention inference verbosity";
  - "Gated DeltaNet state quantization inference";
  - "stochastic rounding SSM state cache";
  - "preemption recompute prefill recurrent state precision serving" (after
    2025-01-01);
  - "Qwen3.5 reinforcement learning rollout SSM state fp32 mismatch" (after
    2025-06-01);
  - plus 8 refuter keyword queries.
- orx embedding:
  - low-precision recurrent state lengthens reasoning and lowers math accuracy;
  - bf16 against fp32 SSM state cache in serving;
  - the train-inference mismatch in RL with GDN;
  - plus 2 refuter embedding queries.
- orx openalex: 4 queries, all HTTP 429.
- WebSearch:
  - vLLM `mamba_ssm_cache_dtype` with Qwen3-Next and GDN;
  - the Nemotron Nano 9B v2 card;
  - SGLang `mamba-ssm-dtype`;
  - Qwen3.5 bf16 state and longer reasoning;
  - Qwen3-Next RL mismatch;
  - the vLLM recipes for Qwen3.5;
  - plus 5 refuter searches.
- GitHub issue searches for `mamba_ssm_cache_dtype` and `mamba-ssm-cache-dtype`
  in vllm-project/vllm, and for `mamba-ssm-dtype` in sgl-project/sglang (read:
  #55291, #54308, sglang #40706). Plus 8 refuter issue searches.

### Finding D (auditor and refuter)

- orx keyword:
  - "expert offloading SSD flash memory MoE consumer device decode tokens per
    second";
  - "2-bit quantization DeepSeek task accuracy code generation degradation
    GGUF";
  - "Kimi K2 2-bit quantization benchmark GPQA";
  - "DeepSeek-V4-Flash quantization GGUF evaluation";
  - "Apple Silicon unified memory mixture-of-experts streaming MacBook";
  - "quantization code generation LiveCodeBench low-bit degradation pass@1";
  - "k-bit inference scaling laws total model bits 4-bit optimal".
- orx embedding:
  - streaming trillion-parameter MoE experts from SSD on a laptop;
  - large low-bit against smaller higher-precision models at a fixed memory
    budget;
  - LLM in a flash;
  - extremely low-bit trillion-parameter MoE against smaller models at the
    same footprint.
- orx openalex: 2 queries, both HTTP 429.
- 14 refuter orx queries, keyword and embedding.
- WebSearch:
  - V4 Flash 2-bit coding;
  - Anemll Kimi on the M5 Max;
  - ds4 GLM 5.3 streaming;
  - Unsloth V4 Flash GGUF benchmarks;
  - the best local LLM for a 128 GB M5 Max;
  - r/LocalLLaMA V4 Flash Q2 against IQ3 against Q8;
  - GitButler;
  - Kimi K2 1-2 bit GGUF knowledge loss;
  - the Hugging Face local Moore's-law blog;
  - AtomicChat dsv4-eval-artifacts;
  - plus 7 refuter searches.
- GitHub API: Anemll repository and README; antirez/ds4 issue searches.
- WebFetch: ds4 `SSD_STREAMING.md`, oobabooga, Unsloth Aider, kingy.ai,
  GitButler, the G. Cull gist, openclawdc and Deltafin. The Towards AI page
  returned 403.
