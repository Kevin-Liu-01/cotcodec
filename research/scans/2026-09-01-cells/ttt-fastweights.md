# Cell: ttt-fastweights — Test-time training, fast weights, memory-in-weights

Sweep date: 2026-09-01. Prior sweep cutoff: 2026-08-10. Author: research cell "ttt-fastweights".
Honesty: every quantitative claim below is tied to a primary URL that was opened in this session
(arXiv abs/HTML page, arXiv API record, GitHub README/issue, HF model card). "First-party" = author
blog/README/preprint; "peer-reviewed" = accepted venue confirmed from a badge/README/search record.
No claim of complete novelty is made anywhere; gaps are stated as "no direct prior art found through
2026-09-01 under the coverage recorded at the end of this note."

## 0. Executive summary

1. The field moved from "TTT layer vs attention" to **drop-in fast-weight adaptation of released
   checkpoints** (In-Place TTT ICLR 2026 Oral; TTT-NTP EMNLP 2026 Findings; TTCD; MoNe; FAAST; Locas)
   and to **chunk-parallel exactness** (E²-TTT, 2026-08-21) and **component ablation** (Modular TTT,
   2026-08-07). Both post-cutoff papers are small-compute (340M–1.45B, 15B–100B tokens) and release code;
   E²-TTT releases checkpoints. This regime is inside Kevin's 8xH100 envelope.
2. **Exact recall beyond the attention window is still the contested axis.** TTT-E2E's own Table 2 gives
   pass-key 0.06 vs 0.99 for full attention at 128K, and an unanswered June 2026 issue reports no exact
   retrieval outside the SWA window. SR-TTT v2 retracted all exact-recall gains (0% exact match in 2,250
   paired trials) after finding an off-by-one label leak and noncausal cache attention. Modular TTT concedes
   "precise long-context recall remains a limitation". Against this, E²-TTT reports 93.6% S-NIAH-1 at 16K
   (8× training length, needle outside the 512 window) and FwPKM reports 4K→128K NIAH generalization — both
   first-party, neither with causality self-tests reported. Independent causality-verified replication of
   any beyond-window TTT-layer recall claim was not found.
3. **Negative results and retractions are now a visible sub-literature**: SR-TTT v2 (retraction), Beyond
   Perplexity (24-paper audit; 0.0% free-form recall after one-step LoRA writes despite ~1 nat loss drop),
   the DT-TTT independent audit (Claims 5–6 falsified), TTT-KVB "is secretly linear attention", write-in vs
   read-out dissociation, and In-Place TTT reproduction issues (update-path collapse; paper–code clipping
   discrepancy; no public checkpoints).
4. **Stability, poisoning, reset, deletion remain unsolved at the architectural-layer level.** Stability
   theory exists only for the linear Titans memory (momentwo); nonlinear fast weights are handled by
   empirical tricks (Muon+norm, small-lr init, scalar decay, EWC anchors, Frobenius clipping). Poisoning
   work targets LoRA-TTT and TTRL, not fast-weight layers. Reset is per-document by convention; RW-TTT adds
   owner/version tagging for serving correctness, not verified deletion. No certified deletion or rollback
   attestation for test-time-learned state was found.

## 1. Findings (each opened at the primary source)

Format: title — URL — date — source type — claim — occupies — relevance — confidence.

### 1.1 Retractions, negative results, and protocol papers

F1. **SR-TTT Does Not Learn Retrieval: A Correction and Mechanistic Post-Mortem of Surprisal-Aware Residual
Test-Time Training** — https://arxiv.org/abs/2603.06642v2 (v1 2026-02-26; v2 2026-07-22) — arXiv, single
author, first-party retraction; repo https://github.com/swamynathanvp/Surprisal-Aware-Residual-Test-Time-Training
(1 star; last push 2026-07-22).
Claim: v1's +23% / +20% NIAH gains were evaluation artifacts: (a) loss and metric read logits at the answer
positions instead of one position earlier, so both models were trained to copy an answer already visible in
input (a model trained on retrieval-impossible data reaches 100% under the flawed metric); (b) the residual
cache attended non-causally over future tokens, including the answer. Corrected protocol: startup causality
self-tests asserting bit-identical logits with cache on/off at unperturbed positions (`test_causality_leak.py`
measured 0.21 cache leak and 0.31 TTT-window leak before the fix), `test_copy_leak.py` (100% on
retrieval-impossible data under v1 metric vs chance under corrected indexing), `test_v2_retrieval.py`
positive control (43% vs 10% chance). Under correction: exact match 0% in all 2,250 paired trials, pooled
McNemar p = 1.0. Failure decomposes: storage (surprisal gating position-biased; 0–1% containment at depth 0.1),
addressing (oracle storage + trainable read projections raise addressing mass 2.5×, 0.06→0.15, token accuracy
unchanged; ≈0.06 nats of the 2.30-nat needle extracted), readout (small fusion gate attenuates).
Occupies: surprise-gated residual exact-attention cache on a TTT LM; a reusable causality self-test protocol.
Relevance: kill-shot for surprise-gated memory (already in the prior sweep's Rejected table); the protocol is
the template every CoTCodec memory experiment must pass. Confidence 0.95 (numbers are from the paper itself;
the mechanism verdict is one author's; repo has 1 star).

F2. **Beyond Perplexity: A Behavioral Evaluation Framework for Deployment-Memory Claims in LLM Test-Time
Training** — https://arxiv.org/abs/2607.00368 (2026-07-01) — arXiv preprint (Song, Chen, Kong, Xie, Dong,
Chen, Zhang).
Claim: proposes a claim-calibrated evidence ladder — S (stream/domain adaptation proxies), B (bridge
internalization / parametric memory), D (deployment-time behavioral learning: later recall, paraphrase,
delay, locality, conflict, action-use after the support context is removed). Names the failure mode
"evidence migration". Audits 24 papers (TTT-layers, PERK, SEAL, TTT-Discover…) and finds most remain at S/B.
Diagnostic: Qwen3 1.7B/4B/8B, LoRA one-step updates on 48 nonce access-code facts: support NLL −0.966 to
−1.218, answer loss −0.463 to −0.674, yet generated free-form recall 0.0% in all conditions (direct,
paraphrased, delayed).
Occupies: the evaluation-protocol axis for TTT memory claims. Relevance: gives CoTCodec the exact behavioral
battery to attach to any memory-in-weights claim; confirms loss deltas are not memory. Confidence 0.9.

F3. **Test-Time Training with KV Binding Is Secretly Linear Attention** — https://arxiv.org/abs/2602.21204
(v1 2026-02-24; latest 2026-05-12) — arXiv (Liu, Elflein, Litany, Gojcic, Li; NVIDIA-affiliated authors).
Claim: multiple phenomena contradict the memorization interpretation of TTT-KVB layers; a broad class of TTT
architectures is a learned linear-attention operator; yields simplifications and fully parallel formulations.
Occupies: theory of what TTT layers compute. Relevance: undermines "memory-in-weights" framing for KV-binding
TTT; any CoTCodec claim must show behavior linear attention cannot produce. Confidence 0.8 (abstract-level).

F4. **A Decision-Theoretic View of Test-Time Training** (arXiv:2606.15569) + independent audit
https://github.com/MachineLearning-Nerd/icml26-decision-theoretic-test-time-training (created 2026-07-29,
updated 2026-08-20; 0 stars; CLAIM_EVIDENCE.md opened).
Claim: audit status `PARTIAL … C5_C6_FALSIFIED`. Claim 5 (evidence-selected adaptation improves digit-shift):
evidence-selected was worse by +0.0024147 MSE, 95% CI [+0.0007339, +0.0041119] (seed 26061569); cross-check
seed 2574 reversal +0.0012526 with CI crossing zero. Claim 6 ("Query-Aware consistently beats Trace-TopK"):
losses/ties at budgets 8/16/32; Trace-TopK won prompt fit at all six budgets. Claims 1–4 retain a historical
record only. Occupies: theory of when/how-far to adapt. Relevance: shows claim-by-claim reproduction audits
of TTT papers are feasible and productive; a model for the Gauntlet. Confidence 0.65 (unaffiliated repo).

F5. **Test-time training and the write-in / read-out of new knowledge in small language models** —
https://github.com/sxewc/ttt-knowledge-writein-readout (created 2026-08-09; pre-registered; MIT).
Claim: on Qwen2.5-0.5B-Instruct (1.5B exploratory), 22-run aggregate with disjoint exploration/confirmation
seed pools (13/37/73 vs 101/137/173), a double dissociation: parameter-efficient TTT drives large write-in
(gold-token rank collapses by orders of magnitude; several nats log-prob gain) while read-out QA accuracy
stays at floor; layer band, training stream, and budget move write-in and read-out differently; keep-set
tracks collateral forgetting (RAU metric). Occupies: write-in vs read-out diagnostics for TTT knowledge
injection. Relevance: independent confirmation of F2's proxy–behavior gap at a scale Kevin can rerun on one
GPU; a template for pre-registration. Confidence 0.55 (0-star repo, tiny scale).

F6. **momentwo: momentum turns Titans' delta-rule forgetting into an exact second-order recurrence** —
https://github.com/v-code01/momentwo (2026-07-22; proof + fp64).
Claim: for Titans' quadratic loss the retrieval error obeys e_t = b e_{t−1} − d e_{t−2} + c with
b = (1−α)+η−2θc, d = η(1−α), c = ‖k‖²; closure error 5.7e−16 vs full simulation; stable iff
θc < (1+η)(2−α)/2 (delta rule: θc < 1), i.e. momentum roughly doubles the LR ceiling; oscillatory-regime
retention modulus is √(η(1−α)), not (1−α), so the forgetting horizon is set by momentum, not decay.
Occupies: closed-form stability of the linear Titans memory. Relevance: the only formal stability result
found; it does not cover nonlinear (MLP) fast weights. Confidence 0.55 (unreviewed, 0 stars; math is
checkable on CPU).

F7. **In-Place TTT reproduction issues (community negative signals)** — repo
https://github.com/ByteDance-Seed/In-Place-TTT (created 2026-04-07; 283 stars; last push 2026-04-21).
Issue #3 (2026-04-28): no public checkpoints; author reply (2026-05-05): "We don't have public checkpoints…
you'll typically need around 1000–2000 steps for the TTT layers to become functional"; a second user
(2026-06-05) cannot reproduce the 500M SWA perplexity from appendix parameters. Issue #5 (2026-05-15, open):
on Qwen3-4B-Base at 32K with the public recipe, `ttt_mode=True` long-context inference collapses (NIAH probes
produce empty/repeated/newline output) from accumulated `present_w` drift; author attributes it to too-few
steps and PG-19 data. Issue #7 (2026-07-15, open, unanswered): Appendix C.2 says inference updates are
Frobenius-clipped at τ=1e−5 but the public code has no clipping; in a Qwen3-0.6B diagnostic the first nonzero
fast state raised future NLL 1.86→10.81 and max ‖F_prefix z‖/‖W z‖ reached 62.5 (15.2 even with per-chunk
clipping to norm 1). Issue #9 (2026-08-23): asks for data mixture to reproduce.
Occupies: reproducibility status of the ICLR 2026 Oral drop-in method. Relevance: concrete evidence that
fast-weight stability is unsolved in practice and that paper–code parity is not established. Confidence 0.85
(primary issue text read; authors partially responded).

F8. **TTT-E2E exact-recall failure (author table + open issue)** — https://arxiv.org/abs/2512.23675
(v1 2025-12-29; v2 2025-12-31); HTML body read; issue https://github.com/test-time-training/e2e/issues/8
(2026-06-02, open, no reply as of 2026-09-01; official JAX repo 689 stars).
Claim: 3B/164B tokens; TTT-E2E scales with context like full attention on perplexity while being 2.7× faster
at 128K (0.0086 s per 1K tokens prefill on H100 vs 0.017 for TTT-KVB); but Table 2 pass-key retrieval at 128K:
full attention 0.99 vs TTT-E2E 0.06 ("the strength of full attention lies in its nearly lossless recall…
our approach relies on compression"); training latency 3.4× slower than full attention at 8K; documents <8K
were discarded "to avoid resetting the updated MLPs across document boundaries". Issue #8 reports zero exact
retrievals when the needle lies outside the SWA window and accuracy tracking the SWA-covered fraction.
Occupies: continual-learning framing of long context with standard architecture. Relevance: the cleanest
evidence that weight-compression TTT does not deliver exact recall; the reset-at-boundary convention is
undocumented at test time. Confidence 0.9.

### 1.2 Post-cutoff architecture papers (after 2026-08-10)

F9. **E²-TTT: Rethinking Expressivity and Efficiency in Test-Time Training** —
https://arxiv.org/abs/2608.21308 (v1 2026-08-21; v2 2026-08-26) — arXiv (Zhong, Chen, Martin, Diederichs,
Gall, Beyerer; KIT/NUS/Fraunhofer/Bonn); code https://github.com/zeyun-zhong/E2-TTT (0 stars); checkpoints
https://huggingface.co/zeyun-zhong/e2-ttt-swiglu-1.3B-15B (+ mlp/340M variants; 2026-08-30).
Claim: under the standard approximation of taking gradients at chunk-start weights, a closed-form state
transition reproduces the chunk-end fast-weight and momentum states of the per-token recurrence (relative L2
deviation from sequential reference < 2×10⁻⁶ over 128 chunks); 340M/1.3B trained from scratch on 15B
FineWeb-Edu tokens with SWA window 512 and TTT chunk 512; S-NIAH-1 (needle outside the window, 1.3B):
2K 95.6 vs LaCT 100.0; 4K 95.0 vs 81.0; 8K 95.4 vs 37.4; 16K 93.6 vs 3.0 (8× training length). No causality
or leakage checks reported; no negative results reported. Occupies: exact chunk-parallel per-token dynamics
(lr/momentum/decay) for TTT layers. Relevance: the strongest post-cutoff beyond-window recall claim; released
checkpoints make an SR-TTT-style causality audit feasible on one H100. Confidence 0.8 (first-party).

F10. **Modular TTT: Rethinking Test-Time Training as Composable Modules** — https://arxiv.org/abs/2608.07110
(2026-08-07) — arXiv (Tang, Qin, Pan, Li, Liu, Zhang; SJTU / Shanghai Innovation Institute / ByteDance Seed);
code https://github.com/ByteDance-Seed/Modular-TTT (46 stars; last push 2026-08-10; code+configs, no
checkpoints or data).
Claim: inner learner as a DAG over Linear/Act/Norm/Add/Mul + loss; ablations at 160M: linear learner
3.0380 val loss, Linear-SiLU-Linear 3.1240, Linear-Linear-Norm and Linear-Norm-Linear-Norm diverge ("×";
the 1/σ(z) factor amplifies gradients when σ(z) is small); small-lr init helps (3.3035→3.0380 at 160M;
2.8054→2.7938 at 410M); scalar decay helps (2.9343→2.7949 at 410M) at equal throughput (34,978 vs 35,709
tok/GPU/s). 100B tokens: 410M 2.5582 ppl / 50.99% vs Gated DeltaNet 2.5559 / 50.45%; 1.45B 2.3150 / 56.44%
vs 2.3042 / 56.30%. "LLaMA remains substantially stronger, especially at 8k, indicating that precise
long-context recall remains a limitation." Occupies: systematic TTT component ablation; parity-with-GDN
result. Relevance: negative result on deep/normalized fast-weight learners; another concession on exact
recall. Confidence 0.85.

F11. **Fast Weight Attention for Continual Learning (Falcon)** — https://arxiv.org/abs/2608.27763
(2026-08-27) — arXiv (Zhang, Ta, Zhang, Feng, Li, Zhang, Liu, Yuan, Wang, Gu, Yao); project repo
https://github.com/yifanzhang-pro/fast-weight-attention (21 stars; last push 2026-08-31).
Claim: under read-after-write autoregressive semantics with prefix-prediction objectives, derives
normalized first-order updates (Falcon-1 scalar NLMS; Falcon-2 per-column; Falcon-3 sliding-window
mini-batch; -A inner-product variants); competitive LM; improved length extrapolation on variable-digit
addition. Numbers not in abstract. Occupies: normalized online-learning update rules for fast weights.
Relevance: another occupant of the "learned/normalized update rule" axis. Confidence 0.65 (abstract only).

F12. **MoNe: Modular Neural Memory for Efficient Long Context Inference** — https://arxiv.org/abs/2608.17616
(2026-08-18) — arXiv (Cho, Chae, Orekondy, Park, Park, Kim, Behboodi, Hwang, Yun).
Claim: attaches a fast-weight neural memory to any frozen pretrained Transformer without retraining; reads
context in fixed segments via layer-localized test-time gradient updates; at query time generates K/V from
the query alone (no re-read); O(N) preprocessing, O(1) query cost; at 128K ≈80% less compute and peak GPU
memory than ICL with 6.4% parameter overhead; strong on RULER NIAH/word extraction beyond the native window.
Occupies: bolt-on fast-weight memory for frozen models. Relevance: directly occupies "strap-on memory in
weights for a frozen base"; first-party recall claims unverified. Confidence 0.7 (abstract only).

F13. **The Query Knows What to Forget: A Second Erase Direction for Linear Attention (QED)** —
https://arxiv.org/abs/2608.13668 (2026-08-13) — arXiv (Gupta, Das, Gupta).
Claim: delta-rule erase vectors derive from the key, but read interference is measured through the query;
adds a query-derived erase direction orthogonal to the key; improves retrieval at every length past the
training window and about doubles usable context on S-NIAH-1 vs Gated DeltaNet-2. Occupies: retention/erase
gating in fast-weight linear attention. Relevance: retention gates are still being redesigned; recall-length
doubling claims here are first-party and small-scale. Confidence 0.65.

### 1.3 Drop-in fast-weight adaptation of released checkpoints

F14. **In-Place Test-Time Training** — https://arxiv.org/abs/2604.06169 (2026-04-07) — ICLR 2026 Oral
(badge in README); ByteDance Seed (Feng, Luo, Hua, Zhang, He, Huang, Cai).
Claim: treats MLP down-projection matrices as fast weights; NTP-aligned objective; chunk-wise updates with
parallel scan "mathematically equivalent to a strictly causal sequential process"; a 4B model with contexts to
128K outperforms competing TTT approaches from scratch; drop-in for Qwen3-8B / LLaMA-3.1-8B recipes.
Occupies: drop-in fast weights in MLP blocks. Relevance: the reference drop-in; see F7 for reproduction
status. Confidence 0.85 (peer-reviewed; reproduction contested).

F15. **Test-Time Training with Next-Token Prediction (TTT-NTP)** — https://arxiv.org/abs/2606.21803
(v1 2026-06-19; v2 2026-08-30) — EMNLP 2026 Findings (README); UW–Madison (Ouyang, Cai, Hu); code
https://github.com/yancyou/TTT-NTP (3 stars).
Claim: value target = linear projection of the next-position contextual hidden state; rank-one writes
accumulated as an exclusive causal chunk prefix-sum (chunk 1024) in training, single closed-form ridge write
before decoding; RULER Full-13 (avg 4k–32k) +3.9 Llama-3.1-8B, +3.0 Mistral-7B-v0.3, +4.1 Qwen3-4B,
+2.9 Qwen3-0.6B — "the only method that consistently improves the released backbone" across four models;
LongBench-v2 +5.6 / +3.7. Occupies: NTP-supervised drop-in fast weights. Relevance: shows the write target is
the live design variable for drop-in TTT; Qwen3-4B/0.6B are local models Kevin has pinned. Confidence 0.8.

F16. **Learning What to Remember: Test-Time Training via Context Distillation (TTCD / IP-TTCD)** —
https://arxiv.org/abs/2608.01672 (2026-08-03) — arXiv (Wang, Dang, Zhu, Wen, Fu, Chai, Lee).
Claim: a long-window teacher supervises the fast weights of a short-window student via hidden-state
discrepancy — a self-supervised future-utility signal; IP-TTCD beats DeltaNet, Gated DeltaNet, SWA, and TTT
from scratch and lets pretrained transformers gain long-context ability via continual pretraining.
Occupies: "what to write" objectives for fast weights (future utility). Relevance: occupies the
future-utility write-objective axis that CoTCodec's causal-holdout gate also touches. Confidence 0.7.

F17. **Let's (not) just put things in Context: Test-Time Training for Long-Context LLMs** —
https://arxiv.org/abs/2512.13898 (2025-12-15) — arXiv (Bansal, Zhang, Tiwari, Madaan, Duvvuri, Khatri,
Brandfonbrener, Alvarez-Melis, Bhargava, Kale, Jelassi).
Claim: inference-time scaling (thinking tokens) shows rapidly diminishing returns and fails at long context
("score dilution" of static attention); targeted gradient updates on the context give +12.6 and +14.1 pp for
Qwen3-4B on LongBench-v2 and ZeroScrolls subsets. Occupies: TTT vs test-time-compute for long context.
Relevance: negative result for thinking-token scaling at long context; positive for context-specific
training. Confidence 0.8.

F18. **Self-Guided Test-Time Training for Long-Context LLMs (S-TTT)** — https://arxiv.org/abs/2607.09415
(2026-07-10) — arXiv (Zhu et al.).
Claim: TTT is highly sensitive to span quality — on LongBench-v2, TTT on randomly sampled spans hurts,
oracle spans help; S-TTT selects evidence spans then applies LM loss only there; up to 15% relative gain on
Qwen3-4B-Thinking-2507 and Llama-3.1-8B-Instruct (LongBench-v2, LongBench-Pro). Occupies: span selection for
TTT. Relevance: a documented negative (random-span TTT hurts) and another occupant of write-selection.
Confidence 0.75.

F19. **Self-Consolidating Language Models (SCoL)** — https://arxiv.org/abs/2605.07076 (v1 2026-05-08;
v2 2026-05-12) — arXiv (Wang, Gupta, Dong, MacLellan).
Claim: LLM generates textual update instructions naming which of its own layers to update; trained with
meta-RL over an evolving model state; beats prompting, summarization, batch TTT, sequential finetuning on
SQuAD incorporation and LongBench v2 consolidation; learned sparse update locations align with high-Fisher
layers. Occupies: learned layer-selection for consolidation into weights. Relevance: occupies "model chooses
where to write". Confidence 0.7.

F20. **Locas: Your Models are Principled Initializers of Locally-Supported Parametric Memories** —
https://arxiv.org/abs/2602.05085 (2026-02-04) — Tencent AI Lab technical report (Lu, Liang, Ma, Wang, Mi, Yu).
Claim: FFN/GLU-shaped low-rank sideway memory that can be offloaded from or merged into model parameters;
principled initialization from model params/activations/gradients; 0.02% extra parameters (lowest case);
PG-19 whole-book LM and LoCoMo QA; MMLU check for capability loss after memorizing a whole book.
Occupies: offloadable/mergeable parametric memory (a portability move). Relevance: closest existing
"detachable memory-in-weights" artifact; no deletion verification. Confidence 0.7.

F21. **FAAST: Forward-Only Associative Learning via Closed-Form Fast Weights for Test-Time Supervised
Adaptation** — https://arxiv.org/abs/2605.04651 (v1 2026-05-06; v2 2026-05-08) — arXiv (Bao et al.); code
https://github.com/baoguangsheng/faast (3 stars); HF models gshbao/faast-{gpt2-xl, Qwen2.5-3B-Instruct,
Qwen2.5-7B-Instruct}.
Claim (body read): labeled examples compiled analytically into fast weights in one forward pass; >90%
adaptation-time reduction and up to 95% memory reduction vs context-based approaches; IWSLT2017 MT
(Table 5), Qwen2.5-3B-Instruct zero-shot → 1-shot → full-data BLEU: En-De 23.22→23.35→25.22; De-En
32.92→33.23→36.40; En-Fr 30.56→31.12→35.09; Fr-En 39.24→39.46→42.47; Qwen2.5-7B: En-De 25.53→26.77→27.75;
De-En 34.69→35.34→37.10; En-Fr 34.82→35.67→37.08; Fr-En 41.40→42.08→43.93. Limitation (authors): weaker for
compositional reasoning / long-range planning. Occupies: closed-form supervised fast weights, with MT as an
evaluation task. Relevance: the only fast-weight paper found that touches translation — but parallel data is
used as labels, not as the update rule's supervision or for cross-lingual readout. Confidence 0.8.

### 1.4 Google neural-memory line and retention gates

F22. **ATLAS: Learning to Optimally Memorize the Context at Test Time** — https://arxiv.org/abs/2505.23735
(2025-05-29) — ICML 2026 (search record; OpenReview blocked) — Behrouz, Li, Kacham, Daliri, Deng, Zhong,
Razaviyayn, Mirrokni.
Claim: memory optimized w.r.t. current and past tokens (Omega rule) rather than online-only; DeepTransformers
and OmegaNet; +80% accuracy at 10M-token BABILong; no code found. Occupies: context-window memory
optimization / higher-capacity deep memory. Relevance: first-party, no release, no independent replication
found. Confidence 0.8 (venue), claims unreplicated.

F23. **It's All Connected (MIRAS)** — https://arxiv.org/abs/2504.13173 (2025-04-17) — ICLR 2026 (search
record) — Behrouz, Razaviyayn, Zhong, Mirrokni.
Claim: four design choices — associative memory architecture, attentional bias objective, retention gate
(forgetting reinterpreted as retention regularization), memory learning algorithm; Moneta/Yaad/Memora beyond
linear RNNs. Occupies: the retention-gate design space as regularization. Relevance: any "new retention gate"
must be positioned against MIRAS's taxonomy. Confidence 0.8.

F24. **Trellis: Learning to Compress Key-Value Memory in Attention Models** — https://arxiv.org/abs/2512.23852
(2025-12-29) — COLM 2025 (abs page) — Karami, Behrouz, Kacham, Mirrokni (Lattice successor).
Claim: fixed-size memory replacing the KV cache; two-pass recurrent compression trained with online gradient
descent and a forget gate at test time; gains grow with sequence length. Occupies: learned KV compression with
forget gate. Relevance: the Lattice/Trellis line is the Google occupant of "compress the cache with online GD".
Confidence 0.75.

F25. **Nested Learning: The Illusion of Deep Learning Architectures (HOPE)** — https://arxiv.org/abs/2512.24695
(2025-12-31; NeurIPS 2025 per abs) + blog https://research.google/blog/introducing-nested-learning-a-new-ml-paradigm-for-continual-learning/
(2025-11-07) + reproduction https://github.com/kmccleary3301/nested_learning (712 stars; last push 2026-02-25).
Claim: HOPE = self-modifying Titans + continuum memory system (multi-frequency updates); blog: lower perplexity
than Titans/Samba/Transformer, better NIAH — no numbers; no official code or checkpoints. The most-starred
reproduction states it "targets mechanism-auditing fidelity, not full paper-scale results parity"; stable
default uses stop-grad online writes; multi-GPU online updates unsupported. Occupies: multi-timescale
self-modifying memory. Relevance: no independent paper-scale replication exists. Confidence 0.85.

F26. **Gated DeltaNet-2: Decoupling Erase and Write in Linear Attention** — https://arxiv.org/abs/2605.22791
(2026-05-21) — NVIDIA technical report (Hatamizadeh, Choi, Kautz); code github.com/NVlabs/GatedDeltaNet-2.
Claim: channel-wise erase gate b_t and write gate w_t replace the scalar tie in GDN/KDA; fast-weight update
view, chunkwise WY algorithm; at 1.3B on 100B FineWeb-Edu tokens strongest overall vs Mamba-2, GDN, KDA,
Mamba-3 variants. Occupies: erase/write decoupling in delta-rule fast weights. Relevance: the production
lineage (Kimi KDA → GDN-2 → QED) is where retention gating is actually being iterated. Confidence 0.75.

### 1.5 Sparse-slot fast-weight memory and stability regularization

F27. **Fast-weight Product Key Memory (FwPKM)** — https://arxiv.org/abs/2601.00671 (v1 2026-01-02;
v2 2026-02-22) — Sakana AI (Zhao, Jones); code https://github.com/SakanaAI/fast-weight-product-key-memory
(22 stars); 8 HF checkpoints (SakanaAI/fwpkm-l12-*, 2026-07-27).
Claim: sparse PKM slots updated at train and test time by chunk-level gradient descent on a local
memory-rewrite objective; significant perplexity reductions on long-context data; trained on 4K, generalizes
to 128K NIAH. Occupies: sparse slot memory with TTT-style updates. Relevance: released small checkpoints
(GDN/FA/SWA hybrids) suitable for local causality audits. Confidence 0.8 (first-party numbers).

F28. **Fast Spatial Memory with Elastic Test-Time Training (LaCET)** — https://arxiv.org/abs/2604.07350
(2026-04-08) — arXiv (Ma, Yu, Zhen, Yang, Chai, Gan); builds on LaCT https://arxiv.org/abs/2505.23884
(2025-05-29; chunks 2K–1M tokens; nonlinear state up to 40% of parameters; Muon + L2 weight normalization
against magnitude explosion/decayed memory).
Claim: LaCT's "fully plastic inference-time updates remain vulnerable to catastrophic forgetting and
overfitting", so LaCT is typically run as one chunk spanning the whole input; LaCET adds a Fisher-weighted
elastic prior around an EMA anchor of past fast weights. No quantified failure of plain LaCT in the abstract.
Occupies: stability regularization of nonlinear fast weights (EWC-style). Relevance: shows stability is
handled by regularizers, not theory. Confidence 0.8.

### 1.6 Security and serving of test-time-learned state

F29. **Test-Time Training Undermines Safety Guardrails** — https://arxiv.org/abs/2605.22984 (2026-05-21) —
arXiv (Antonelli, Akhondzadeh, Bojchevski).
Claim: three threat models for TTT; under LoRA TTT, few-shot and generation-phase threat models reach average
ASR@10 of 95% and 93% across model families/scales; transfers to production fine-tuning APIs; TTT-induced
overfitting yields degenerate outputs that inflate ASR under standard judges → validity-aware evaluation;
proposes a provider-side perplexity-shift detector on a private harmful holdout. Scope: fine-tuning-style TTT,
not fast-weight layers. Occupies: TTT jailbreak threat models. Relevance: poisoning of architectural
fast-weight layers is not covered. Confidence 0.85. Related: Amplification Effects in Test-Time RL
https://arxiv.org/abs/2603.15417 (2026-03-16): harmful prompt injection during TTRL amplifies base behavior;
"reasoning tax"; HarmInject prompts. Vision TTA poisoning: https://arxiv.org/abs/2410.04682 (ICLR 2025)
finds TTA "more robust than previously believed" under realistic attacker assumptions.

F30. **RW-TTT: Batched Serving for Request-Owned Test-Time Training State** — https://arxiv.org/abs/2605.28053
(2026-05-27) — arXiv (Yang, Kou, Tian, Zhang, Chen, Han, Guo).
Claim: request-owned state (fast weights, low-rank deltas, learner state) breaks batched serving; tags each
decode step with owner/version/READ-WRITE effect, batches compatible phases, commits only to the owner; eight
In-Place-TTT streams on one GPU: 274.61 tok/s, 9.31× over sequential and 3.44× over per-stream replicas;
preserves RULER; passes owner/version checks. Occupies: isolation of per-request TTT state for serving.
Relevance: the closest thing to "reset/isolation" found — a serving-correctness mechanism, not verified
deletion or rollback. Confidence 0.75.

### 1.7 Additional items opened (not in the 30-item structured list)

- Titans — https://arxiv.org/abs/2501.00663 (2024-12-31; NeurIPS 2025 poster per search record): >2M
  context; higher NIAH accuracy than baselines; no code. Already in prior sweep.
- M+: Extending MemoryLLM — https://arxiv.org/abs/2502.00592 (ICML 2025): 1B-parameter memory pool;
  retention extended from <20k to >160k tokens; code github.com/wangyu-ustc/MemoryLLM. No 2026 successor
  found (search #8, #28 returned only M+ and unrelated agent-memory papers).
- Lifelong In-Context Learning with Transformers Requires Parametric Forms of Attention —
  https://arxiv.org/abs/2606.25342 (2026-06-24): position paper; parametric attention "currently fall short
  of lifelong learning due to limited memory capacity or costly online updates".
- REFINE: Reinforced Fast Weights with Next-Sequence Prediction — https://arxiv.org/abs/2602.16704
  (2026-02-18): GRPO on entropy-selected positions for LaCT-760M and DeltaNet-1.3B; beats NTP SFT on NIAH,
  long-context QA, LongBench.
- EASE-TTT — https://arxiv.org/abs/2606.06906 (2026-06-05): evidence-aligned attention supervision for
  query-side TTT on six LongBench QA tasks.
- Words & Weights (ROSA2) — https://arxiv.org/abs/2603.01375 (2026-03-02): joint text-gradient +
  parameter-update adaptation; +30% MATH, −40% turns (first-party).
- Do Language Models Need Sleep? — https://arxiv.org/abs/2605.26099 (2026-05-25): offline recurrent passes
  convert recent context into SSM fast weights before clearing the KV cache; gains grow with sleep length N.
- Learning, Fast and Slow (FST) — https://arxiv.org/abs/2605.12484 (2026-05-12): optimized context as "fast
  weights", parameters as slow; up to 3× sample efficiency vs RL, up to 70% less KL drift.
- Learning to Forget: Sleep-Inspired Memory Consolidation (SleepGate) — https://arxiv.org/abs/2603.14517
  (2026-03-15): learned forgetting gate over the KV cache; 793K-parameter transformer; 99.5%/97.0% retrieval
  at PI depth 5/10 vs <18% baselines. KV-level, not weights.
- Rethinking Machine Unlearning: Models Designed to Forget via Key Deletion (MUNKEY) —
  https://arxiv.org/abs/2603.15033 (2026-03-16): unlearning by deleting an instance key in an external
  memory; vision benchmarks; not fast weights.
- Mela: Test-Time Memory Consolidation — https://arxiv.org/abs/2605.10537 (2026-05-11): dual-frequency
  hierarchical memory; single author; no code mentioned.
- A Trained Fast-Weight Memory: Continual Rule Binding at Inference Without Backward (thought-bank /
  Fractale) — https://github.com/kkuette/thought-bank (Zenodo DOI 10.5281/zenodo.21225721; 4 stars;
  pre-registration v1.0 dated 2026-08-17): 3.08M-parameter trunk with an 8-slot self-written fast-weight
  bank; claims TTT "transfers exactly nothing" at 138× cost on the same task while the bank binds a rule at
  0.79–1.00 accuracy; memory exposed as a save/restore/reset/swap object in https://github.com/fractale-lm/fractale.
  First-party, tiny scale, two seeds.
- matrix-states — https://github.com/saml212/matrix-states: negative result "The Gradient Does Not See
  Rank" (ICML 2026 MI Workshop per README); matrix ops lose at matched FLOPs.
- ARC-AGI-1 recursive transformer — https://github.com/devchaitanya/ARC-AGI-1: 15-run ablation; 2.75% with
  50 TTT steps vs 0.25% without (McNemar p=0.021); architecture variants 0.75–2.25%. Hobby-scale.
- ICLR 2026 3rd Workshop on Test-Time Updates — https://ttu-iclr2026.github.io/ (2026-04-27; organizers
  Shelhamer, Croce, Yeo, Niu, Bozorgtabar, Li); accepted-papers page returned 404.
- HF third-party artifacts: paulzy/e2e-3b-tttbin-cad2-… (2026-08-17; a 3B TTT-E2E variant with a binary
  router; no published scores) and ChavyvAkvar/atma-10b-babilong-2k-ft-atma-raven-titans (2026-08-02; a
  Titans-variant 10B "ATMA" adapted on BABILong 0–2K; "not an official leaderboard submission"; base card
  not retrievable).

## 2. Occupied axes

| Axis | What is already taken | Representative URLs |
|---|---|---|
| Chunk-parallel TTT-layer design space | Exact chunk-end dynamics (E²-TTT), DAG component ablations (Modular TTT), large-chunk nonlinear states (LaCT), NLMS-normalized updates (Falcon), TTT-KVB ≡ learned linear attention | 2608.21308, 2608.07110, 2505.23884, 2608.27763, 2602.21204 |
| Drop-in fast weights for released checkpoints | MLP down-proj fast weights (In-Place TTT), NTP-supervised writes (TTT-NTP), teacher–student future-utility (IP-TTCD), bolt-on memory for frozen models (MoNe), closed-form supervised fast weights (FAAST), offloadable FFN memory (Locas), targeted context gradient updates (2512.13898) | 2604.06169, 2606.21803, 2608.01672, 2608.17616, 2605.04651, 2602.05085, 2512.13898 |
| Deep neural memory with surprise/retention gating (Google line) | Titans (NeurIPS 2025), MIRAS retention-gate taxonomy (ICLR 2026), Atlas Omega rule (ICML 2026), Trellis KV compression (COLM 2025), HOPE/Nested Learning (NeurIPS 2025) | 2501.00663, 2504.13173, 2505.23735, 2512.23852, 2512.24695 |
| Erase/write gating in delta-rule fast weights | Channel-wise erase vs write gates (GDN-2), query-derived erase direction (QED), KDA lineage | 2605.22791, 2608.13668 |
| Sparse-slot / bank fast-weight memory | FwPKM (Sakana), thought-bank 8-slot bank, MemoryLLM/M+ latent pool | 2601.00671, github.com/kkuette/thought-bank, 2502.00592 |
| Stability control of fast weights | Linear Titans stability recurrence (momentwo); Muon + weight norm (LaCT); small-lr init + scalar decay + shallow learners (Modular TTT); EWC anchor (LaCET); Frobenius clipping τ (In-Place TTT App. C.2) | github.com/v-code01/momentwo, 2505.23884, 2608.07110, 2604.07350, 2604.06169 |
| Choosing what to write | Future-utility distillation (TTCD), span selection (S-TTT), evidence-aligned attention targets (EASE-TTT), model-chosen layers (SCoL), RL next-sequence rewards (REFINE) | 2608.01672, 2607.09415, 2606.06906, 2605.07076, 2602.16704 |
| Evaluation protocol for TTT memory claims | Causality self-tests + storage/addressing/readout decomposition (SR-TTT v2); S/B/D evidence ladder with 24-paper audit (Beyond Perplexity); write-in vs read-out dissociation | 2603.06642v2, 2607.00368, github.com/sxewc/ttt-knowledge-writein-readout |
| TTT security | LoRA-TTT jailbreak threat models with ASR@10 95%/93% and validity-aware judging; TTRL amplification; vision TTA poisoning benchmarks | 2605.22984, 2603.15417, 2410.04682 |
| Serving isolation of request-owned TTT state | Owner/version/READ-WRITE tagging and batched commits (RW-TTT) | 2605.28053 |

## 3. What a rigorous causality/leakage protocol must include (synthesized from F1, F2, F5, F7, F8, F9, F15)

1. **Index audit of the metric.** Assert that the loss and every accuracy metric read logits at position
   t−1 for a target at t; ship a retrieval-impossible control corpus that must score at chance (SR-TTT's
   leaky metric scored 100% on it).
2. **Startup causality self-tests on every memory path.** Perturb tokens at position j and assert
   bit-identical logits at all positions < j for the residual/exact cache, the TTT window, and the chunked
   fast-weight prefix (SR-TTT measured 0.21 and 0.31 leaks before fixing). Chunk-wise methods must show the
   within-chunk exclusive prefix property (TTT-NTP: exclusive chunk prefix-sum; E²-TTT: gradients at
   chunk-start weights). Kernel-vs-sequential equivalence (E²-TTT rel-L2 < 2e-6) is necessary but is not a
   causality test.
3. **Needle placement outside every non-parametric path**, stratified by depth and by whether the needle is
   inside the SWA window or exact cache (TTT-E2E issue #8; E²-TTT Appendix B.2). Report the SWA-covered
   fraction alongside accuracy.
4. **Generation exact match with paired trials** (McNemar), not logit-at-answer accuracy; report
   storage (containment), addressing (attention mass to the needle slot), and readout (nats extracted)
   separately.
5. **Positive and negative controls before any headline**: a synthetic task the read path provably can learn
   (SR-TTT: 43% vs 10% chance) and the retrieval-impossible negative control.
6. **Behavioral D-level battery after support removal** (Beyond Perplexity): later recall, paraphrase,
   delay, locality, conflict, action-use; report generated free-form recall, not loss deltas (0.0% recall
   coexisted with ≈1-nat loss drops).
7. **Write-in vs read-out separated** (gold-token rank/log-prob vs QA/completion accuracy) with a keep-set
   for collateral forgetting and pre-registered disjoint seed pools.
8. **Boundary and session semantics declared and tested**: where fast weights reset (document, request,
   session), with a cross-document contamination test; TTT-E2E currently avoids the question by discarding
   documents <8K; RW-TTT's owner/version checks are the serving-side analogue.
9. **Stability telemetry as a reported artifact**: fast-weight norm ratios (‖F z‖/‖W z‖), future-NLL after
   the first write, divergence flags, and the exact clipping/decay constants used in the reported runs
   (In-Place TTT issue #7: paper τ=1e-5 absent from code; ratio 62.5; NLL 1.86→10.81).
10. **Validity-aware judging for safety/quality claims** — TTT overfitting produces degenerate text that
    inflates ASR under standard judges (2605.22984).
11. **Frozen, hashed reproduction bundle**: data manifests with SHA-256, configs, per-run logs, and a
    self-check that recomputes headline numbers (as in writein-readout and SR-TTT repos).

## 4. Where stability, poisoning, reset, and deletion remain unsolved

- **Stability.** Only the linear Titans memory has a closed-form stability condition (momentwo, unreviewed).
  Nonlinear fast weights rely on empirical stabilizers: Muon + L2 norm (LaCT), small-lr init + scalar decay +
  shallow learners (Modular TTT; deeper/normalized learners diverge), EWC anchors (LaCET), Frobenius clipping
  (In-Place TTT). Community reproductions of In-Place TTT report update-path collapse and 62.5× prefix output
  ratios. No Lyapunov/spectral analysis for MLP/SwiGLU fast weights was found.
- **Poisoning.** Threat models exist for LoRA-style TTT (ASR@10 95%/93%) and TTRL (HarmInject), and for
  vision TTA (ICLR 2025, "more robust than believed"). No attack or defense paper targets architectural
  fast-weight layers (Titans/TTT-linear/In-Place/E²-TTT) in language models.
- **Reset.** Per-document reset is a convention (TTT-E2E discards short documents to avoid it in training;
  test-time behavior across prompts is undocumented). RW-TTT tags request-owned state for batched serving
  and passes owner/version checks, but does not define or verify reset/rollback semantics.
- **Deletion.** No certified or audited deletion of test-time-learned state was found. MUNKEY provides
  deletion-by-design via external keys for vision classifiers; Locas provides offload/merge but no deletion
  proof; "Unlearning at Scale" (2508.12220, not opened) is training-time. The right-to-be-forgotten question
  for fast weights is open under this coverage.

## 5. Open gaps (searched and not found; each with Kevin's advantage)

G1. **Causality-verified independent replication of beyond-window exact recall by a TTT layer.**
Searched: WebSearch #27, #32; GitHub issues on test-time-training/e2e and ByteDance-Seed/In-Place-TTT; HF
third-party artifacts; the arXiv TTT listing (76 records) — no third-party audit of E²-TTT's 93.6%@16K,
FwPKM's 4K→128K, or MoNe's RULER claims under SR-TTT-style self-tests; TTT-E2E issue #8 is unanswered.
Why open: SR-TTT v2 shows how easily such gains are artifacts; the two 2026 papers report no leakage checks.
Kevin advantage: E²-TTT's 340M/1.3B checkpoints and FwPKM's l12 checkpoints run on one H100; the
Docker/Slurm harness with SIGUSR1 checkpointing can host the SR-TTT self-tests as a capsule; the CMHT
CPU-oracle design already exists.

G2. **Verifiable reset, rollback, and deletion of test-time-learned fast-weight state.**
Searched: WebSearch #13, #29; GitHub "fast weights unlearning", "test-time training unlearning" (0 repos);
arXiv listings (only RW-TTT serving isolation; MUNKEY external-key deletion for vision). Why open: RW-TTT
proves isolation for throughput, not deletion; no work attests that a request's writes are gone or reverts
them bitwise. Kevin advantage: the harness's deterministic replay, hash-chained audit log, and
checkpoint/resume contract are exactly the machinery for bitwise rollback attestations; 8xH100 is enough for
the small TTT layers involved.

G3. **Poisoning/backdoor attacks and defenses for architectural fast-weight layers in LMs.**
Searched: WebSearch #9, #23, #30; GitHub "test-time training poisoning" (0 repos); arXiv listing — only
LoRA-TTT (2605.22984), TTRL (2603.15417), vision TTA (2410.04682). Why open: fast-weight layers write
context into weights by design, so a context-borne poison persists for the request/session; nobody has
measured it. Kevin advantage: open TTT-layer checkpoints to attack locally; Tinker LoRA on Qwen3.5 as the
LoRA-TTT control arm; paired deterministic replay gives clean attack/defense estimands.

G4. **Cross-lingual fast-weight memory and parallel-data-supervised update rules.**
Searched: WebSearch #15, #26, #31; GitHub "test-time training translation", "fast weights multilingual"
(0 relevant); arXiv listings — FAAST uses IWSLT MT only as a labeled evaluation task; MultiSynt/MT and CLAS
are pretraining-data and activation-steering work. Why open: no paper tests whether a fast-weight memory
written in language A is readable in language B, or uses parallel sentence pairs as the inner-loop target
(a translation-equivariant write objective). Kevin advantage: General Translation's parallel corpora and
translation-aware tooling; multilingual Qwen3.5 bases on Tinker plus pinned local Qwen3-0.6B-Base; the
byte-boundary direction already builds multilingual paired probes.

G5. **Formal stability analysis for nonlinear (MLP/SwiGLU) fast weights.**
Searched: WebSearch #14, #33; arXiv fast-weights listing (only quantum-FWP "bounded memory gates"
2607.02363, not LMs); momentwo covers the linear quadratic case only. Why open: Modular TTT documents
divergence of deeper/normalized learners and In-Place TTT users report 62.5× output ratios, but no analysis
predicts safe (lr, decay, momentum, clipping) regions. Kevin advantage: fp64 CPU oracle plus tiny pinned
models (SmolLM2-135M, Qwen3-0.6B-Base) for sweeps under checkpointed Slurm jobs; the momentwo recurrence is a
starting point that can be extended and tested empirically on 8xH100.

G6. **Independent paper-scale replication of the Google neural-memory line (Titans/Atlas/HOPE).**
Searched: WebSearch #16, #25; GitHub (community repos target mechanism fidelity, not results parity; no
official code); no reproduction paper found. Why open: all headline numbers (BABILong 10M +80%, >2M NIAH)
are first-party without code. Kevin advantage: 8xH100 suffices for 340M–760M replications on 15–30B tokens
(E²-TTT precedent); digest-pinned images give an auditable trail. Limit: Google-scale claims are out of
reach on one node — the replication would be partial by construction.

## 6. Queries run (123 search invocations; ~45 primary-source fetches)

WebSearch (35 run; 3 blocked by the session budget of 200):
1. SR-TTT v2 retraction exact recall test-time training noncausal leakage arXiv 2603.06642
2. "TTT-E2E" end-to-end test-time training long context 2026
3. "Rethinking Expressivity and Efficiency in Test-Time Training" E2-TTT arXiv
4. "Test-Time Training with Next-Token Prediction" TTT-NTP EMNLP 2026
5. Atlas "learning to optimally memorize" Behrouz OmegaNet DeepTransformers 2026 follow-up
6. Lattice compressed memory attention test-time recurrence memory tokens 2026
7. LaCT large chunk test-time training Zhang 2025 2026 follow-up
8. MemoryLLM M+ latent-space memory long-term retention 2026 follow-up Yu Wang
9. test-time training poisoning attack fast weights memory injection adversarial 2026
10. "test-time training" language model negative result OR "does not improve" OR "fails" 2026 arXiv
11. Behrouz "Nested Learning" HOPE continuum memory system Titans successor 2026 arXiv
12. "retention gate" OR "forget gate" test-time training memory fast weights 2026 arXiv language model
13. test-time training fast weights unlearning OR deletion OR "reset" learned state "right to be forgotten" 2026
14. test-time training instability divergence "learning rate" stability analysis fast weights Titans momentum 2026
15. "test-time training" machine translation OR multilingual OR cross-lingual language model 2026 arXiv
16. Titans reproduction "could not reproduce" OR "fails to reproduce" OR "replication" neural memory Google 2026
17. "Beyond Perplexity" "Behavioral Evaluation Framework" deployment-memory claims test-time training
18. "Test-Time Training Done Better" elastic memory consolidation TTT arXiv 2026
19. "Falcon" "Fast Weight Attention for Continual Learning" arXiv 2026
20. Sakana AI "fast weight" product key memory 2026 paper
21. "Modular TTT" "Rethinking Test-Time Training as Composable Modules" arXiv 2608.07110
22. test-time training "exact recall" OR "associative recall" capacity bound fast weights information-theoretic limit 2026
23. "test-time training" OR "fast weights" prompt injection persistent memory attack weights inference adversarial context 2026 arXiv
24. Titans OR Atlas OR MIRAS Behrouz ICLR 2026 OR NeurIPS 2025 OR ICML 2026 accepted openreview
25. "Hope" nested learning reproduction OR implementation OR "open source" Titans code 2026 github
26. "test-time training" document-level translation OR "parallel data" OR bilingual fast weights adaptation 2026
27. "test-time training" OR "TTT layers" long context "does not scale" OR "underperforms" OR "worse than" Gated DeltaNet Mamba benchmark 2026
28. MemoryLLM OR "M+" 2026 arXiv latent memory self-updatable LLM successor Yu Wang Zexue He
29. "fast weights" OR "test-time training" verifiable "state reset" OR "session isolation" OR "certified deletion" learned state inference-time updates 2026
30. "test-time training" "language model" poisoning OR "backdoor" fast weights context injection inference-time weight update attack 2026 arXiv
31. cross-lingual OR multilingual "fast weights" OR "test-time training" memory "written in one language" readout retrieval another language 2026
32. "test-time training" OR "fast weights" causality OR "future leakage" OR "off-by-one" evaluation harness benchmark self-test long-context memory 2026
33. nonlinear fast weights MLP test-time training stability "activation" blow-up OR divergence OR Lyapunov analysis normalization 2026
34. ICLR 2026 workshop "Test-Time Updates" OR "TTU" accepted papers site
35. "test-time training" OR Titans OR "fast weights" Kimi OR Qwen OR DeepSeek OR GLM production model 2026 "test-time" memory layer architecture release
36–38 (blocked, budget): TTT-E2E independent reproduction …; arXiv August 2026 "test-time training" OR "fast weights" …; "In-Place Test-Time Training" ByteDance-Seed github code release (resolved via `gh api orgs/ByteDance-Seed/repos`).

arXiv API (22 calls; 5 returned data):
- http://export.arxiv.org (301, not followed) ×3; https 0-byte/429 ×4 (incl. id_list of 20 ids); control `all:electron` (200);
- 429 (rate-limited after a parallel burst) ×10: abs:"test-time training"; abs:"fast weights"…; Titans/neural memory;
  G1 (fast weights|TTT) AND (unlearning|deletion|certified|reset); G2 TTT AND (poison|poisoning|backdoor|jailbreak|adversarial);
  G3 (TTT|fast weights) AND (multilingual|cross-lingual|translation|bilingual); G4 TTT AND (leakage|causality|"evaluation protocol"|retract|artifact);
  G5 (fast weights|TTT) AND (stability|Lyapunov|divergence|blow-up); two retries;
- successes: `abs:"test-time training" AND (abs:"language model" OR abs:"fast weight" OR abs:"fast weights")` sorted by submittedDate, 50 of 76 read;
  `id_list=2605.28053,2608.01672,2607.09415,2606.25342,2605.07076,2602.16704,2602.05085,2606.06906,2603.01375,2603.15417`;
  `abs:"fast weights" OR abs:"fast weight" OR abs:"fast-weight"` sorted by submittedDate, 40 of 94 read;
  `id_list=2608.17616,2608.13668,2605.22791,2605.26099,2605.12484,2608.30695`.

Semantic Scholar (3 calls, all HTTP 429 "blocked from performing anonymous queries due to bad network reputation (AS7018)").

Kevin's X bookmarks via `ft search` (27 queries): "test-time training" (error: no such column: time), "fast weights", "test time training", "TTT", "Titans", "Atlas memory", "LaCT", "learn at test time", "memory at test time", "Nested Learning", "Behrouz", "continual learning weights", "long context weights", "TTT-E2E" (error), "Yu Sun", "Karan Dalal", "learns at inference", "Sakana", "MemoryLLM", "inference-time learning" (error), "surprise", "neural memory", "context into weights", "HOPE", "Google Research memory", "linear attention", "DeltaNet". Result: no bookmark on TTT or fast weights; tangential hits only (Kimi FlashKDA kernels 2026-07-27; Kimi K3 KDA 2026-07-16).

Hugging Face model API (17 searches): ttt, titans, memoryllm, ttt-e2e, lact, "in-place ttt" (unencoded, error), fast-weight, "nested learning" (error), "hope architecture" (error), in-place%20ttt, nested%20learning, hope%20titans, inplace-ttt, ttt-ntp, falcon%20fast%20weight, modular-ttt, fwpkm. Model cards read: zeyun-zhong/e2-ttt-swiglu-1.3B-15B; paulzy/e2e-3b-tttbin-…; ChavyvAkvar/atma-10b-babilong-2k-ft-atma-raven-titans (base card, tao-titans, Luxel, SakanaAI fwpkm cards not retrievable).

GitHub (`gh search repos`, 16): "test-time training"; "titans neural memory"; "fast weights"; "atlas memorize test time"; "lact test-time"; "ttt-e2e OR end-to-end test-time training"; "titans pytorch memorize"; "ttt-lm OR ttt-video OR test-time-training"; "in-place test-time training"; "titans memory" (by stars); "fast weights unlearning"; "test-time training unlearning"; "test-time training translation"; "test-time training poisoning"; "causality leak test-time training"; "fast weights multilingual". `gh api` reads: zeyun-zhong/E2-TTT; yancyou/TTT-NTP; MachineLearning-Nerd/icml26-decision-theoretic-test-time-training; v-code01/momentwo; sxewc/ttt-knowledge-writein-readout; fractale-lm/fractale; kkuette/thought-bank; kmccleary3301/nested_learning; test-time-training/e2e (issues list, #8, #3); test-time-training/ttt-lm-pytorch (issues); ByteDance-Seed org repos, In-Place-TTT README/tags/issues #3 #5 #7; baoguangsheng/faast; SakanaAI/fast-weight-product-key-memory; yifanzhang-pro/fast-weight-attention; swamynathanvp/… (via WebFetch).

Primary pages opened with WebFetch (Jina blocked): arXiv abs/HTML for 2603.06642v2, 2512.23675 (abs+html), 2606.21803, 2608.07110 (abs+html), 2608.21308 (abs+html), 2607.00368 (abs+html), 2602.21204, 2604.06169, 2505.23735, 2504.13173, 2512.23852, 2604.07350, 2605.10537, 2605.22984, 2410.04682, 2603.14517, 2603.15033, 2605.04651 (abs+html), 2608.27763, 2601.00671, 2512.13898, 2502.00592, 2505.23884, 2501.00663, 2512.24695; Google Research Nested Learning blog; GitHub READMEs for SR-TTT, Modular-TTT, ARC-AGI-1, matrix-states, fast-weight-attention, lucidrains/fast-weight-product-key-memory, DT-TTT CLAIM_EVIDENCE.md; ttu-iclr2026.github.io (index; /papers/ 404); arXiv search listing pages (429).

## 7. Coverage limits (honest)

- Semantic Scholar: zero coverage (all calls 429/blocked for this network).
- Jina reader: 401 blocked; WebFetch used instead (summaries by a small model; I quoted only numbers that
  appeared verbatim in the returned text).
- arXiv API: rate-limited (429) for ~30 minutes after a parallel burst; only 5 of 22 calls returned data;
  listings limited to the newest 50 (TTT × LM/fast-weight, total 76) and newest 40 (fast weights, total 94)
  by abstract match; arXiv web search pages also 429. Full-text search not available.
- WebSearch: session budget exhausted (200/200) with three planned queries unrun (independent TTT-E2E
  replication; a post-2026-08-10 catch-all; In-Place TTT code — the last resolved via `gh`).
- OpenReview pages blocked by a browser check; venue acceptances for Atlas (ICML 2026), MIRAS (ICLR 2026),
  Titans and Nested Learning (NeurIPS 2025) come from search-result records and the arXiv abs page, not
  opened decision pages; In-Place TTT (ICLR 2026 Oral) and TTT-NTP (EMNLP 2026 Findings) come from repo badges.
- Paper bodies were read only for SR-TTT v2, TTT-E2E, E²-TTT, Modular TTT, Beyond Perplexity, FAAST; all
  other papers are abstract-level (arXiv abs or API summary), so their quantitative detail is limited.
- ICLR 2026 TTU workshop accepted-paper list not obtained (404).
- X bookmarks: `ft search` rejects hyphenated queries; no relevant bookmarks exist for this cell, so X
  coverage is effectively nil.
- HF: several third-party model cards were unavailable; no evaluation numbers for third-party TTT-E2E or
  Titans-variant checkpoints.
- Not searched: Chinese-language sources (Zhihu/WeChat), Google Scholar, paywalled venues, code-level audits
  of any TTT kernel for causality. Video/3D TTT papers (LongVU-TTT, StreamTTT, Mem3R, Spatial-TTT) were noted
  in listings but not opened.
