# commit-gated-observation-state — wave-2 repair (2026-09-01)

Repair owner note. Inputs: candidates.md section 9 (G1 + G3 merge), G-agent-native-architecture.md sections 1 and 3,
wave1-verdicts.json (novelty: not refuted, conf 0.6, with caveats; identification: refuted, conf 0.85; feasibility: refuted,
conf 0.8). This wave: 7 hostsearch calls (abs 2608.12149, arxiv x2, hfpapers x1, abs 2607.02911, abs 2607.02303,
abs 2510.11967), 10 WebFetch calls (flame README, GDN HTML, Massive-Activations-HLA repo, gorilla/BFCL README +
TEST_CATEGORIES, 2608.11859 HTML, 2608.21308 HTML + PDF, 2608.12149v2 HTML, 2507.06457 HTML, fla README), HF API
for every model/dataset revision and license quoted below. Nothing below is called novel; the standing is "no direct prior
art found through 2026-09-01 under the coverage named in section 11".

## 0. What changed and why (one paragraph)

Wave 1 showed that the three "guarantees" in the original claim — bitwise abort containment, replay-free exact retraction,
arrival-order invariance — are either (a) already the frozen-input transport algebra of arXiv 2607.27539 Proposition 1 on a
plain GDN, (b) achievable training-free by snapshot/restore (TreeWY, HARTS, DeltaLog) or by sorting concurrent results in
the harness, or (c) delivered by Set-LLM's masking construction. The original additive set-commit was also algebraically
unsound (it multiplies the persistent state by sum_i a_i - (m-1), which is negative for short-horizon units). The repaired
candidate therefore (1) demotes all by-construction properties to Phase-0 doctors that every arm — including the
training-free state-surgery control — must pass; (2) makes the architecture-causal claim exclusively about the CAPABILITY
COST of the semantics: does training a GDN/softmax hybrid under receipt-gated observation commits make those semantics
free, where imposing them at inference on a plain-trained hybrid is not; (3) replaces the additive set-commit by canonical
affine composition of isolated segment operators; (4) adds the missing controls (training-free state surgery, truncation-
trained hybrid without gating, never-commit, full-attention reference, iso-wall-time); (5) moves the primary endpoint to
held-out task success on sealed worlds with unseen tool families — a quantity the training loss never sees; (6) removes
the predictive/surprise variant from the claim and the pilot; (7) re-budgets on a released, Apache-2.0, fla-native 340M
3:1 GDN hybrid with cited H100 throughput and a 25% reserve, on public license-named data only.

## 1. Slug and claim

**slug.** commit-gated-observation-state

**claim.** In a GDN/softmax hybrid continued-pretrained under receipt-gated observation commits — each tool observation is
processed on a forked recurrent state, its raw tokens survive in the softmax KV only as a B_obs = 64-token stub, and its
content reaches later decisions only through a receipt-gated, logged, affine commit to the persistent state — held-out
tool-world task success recovers to within 1.0 pt of the unconstrained plain hybrid, whereas the identical semantics
imposed at inference on the plain-trained hybrid (training-free state surgery, the TreeWY/CommitKV-class harness) lose
>= 5 pt, and a truncation-trained hybrid without receipt gating and sibling isolation trails CGOS by >= 3 pt on
concurrent-call decisions and >= 5 pt on invalid-receipt decisions. The by-construction properties (abort leaves the state
bitwise unchanged; set-commit is invariant to arrival order; single-observation retraction equals the frozen-input
counterfactual) are Phase-0 doctors shared with the training-free control, not results of this work.

**claim_scope.** architecture-causal (the intervention is the training-time semantics of the sequence operator at typed
boundaries; iso-init, iso-data, iso-tokens across arms; the pilot's scope is continued pretraining of a released 340M
hybrid, the from-scratch 3-size ladder is the promotion stage).

## 2. Mechanism

Notation (GDN convention, state d_k x d_v per head): per-token transition A_t = alpha_t (I - beta_t k_t k_t^T) (d_k x d_k),
write u_t = beta_t k_t v_t^T, recurrence S_t = A_t S_{t-1} + u_t, read o_t = S_t^T q_t. For any contiguous span
t1..t2 the map S_{t1-1} -> S_{t2} is affine: S_{t2} = Aseg S_{t1-1} + Wseg with Aseg = A_{t2} ... A_{t1} and
Wseg = sum_t (A_{t2} ... A_{t+1}) u_t. Every construction below is an affine edit of the state between calls of the
unmodified fused chunkwise kernel (fla `chunk_gated_delta_rule` with `cu_seqlens` and per-sequence `initial_state`); no
kernel is modified.

Token types tau_t in {sys, usr, rsn, act, obs, rcpt} are assigned by the trace format (roles, tool-call/result delimiters,
a receipt token emitted by the tool layer), never by content or by the model.

- Non-observation token: P <- A_t P + u_t; read from P.
- obs-start(j): fork Q_j <- P. Observation tokens of j: Q_j <- A_t Q_j + u_t, read from Q_j, P frozen. (During the
  observation this is numerically identical to plain in-place processing; the fork changes nothing until the receipt.)
- Receipt r_j (type rcpt; carries exit code, schema-validity bit valid_j, byte length, hash prefix; produced by the
  harness's receipted tool runtime, never by the model): per head, gate g_j = valid_j * sigmoid(W_g h_{r_j} + b_g) in
  [0,1]^{d_v}. Commit as the affine map
      T_j(X) = X (I - diag g_j) + (Aseg_j X + Wseg_j) diag g_j,   P <- T_j(P) = P + (Q_j - P) diag g_j = P + C_j.
  g_j = 1 recovers plain GDN exactly; valid_j = 0 gives T_j = identity (abort containment, bitwise). Q_j is discarded.
  In the softmax layers the obs-typed KV of segment j is truncated to a B_obs-token stub (first/last B_obs/2 tokens plus
  the receipt) once the next act token is emitted, so later decisions see the observation only through C_j and the stub.
- Ledger: (j, C_j) for the K most recent commits; for t > r_j, C_j <- A_t C_j (linearity in the state; O(d_k d_v) per entry
  per token). Retraction of j at time T: P_T - C_j^{(T)} equals the state produced with g_j = 0 AND all later per-token
  (k, v, alpha, beta) held fixed. This is exactly Proposition 1 ("frozen-input transport") of arXiv 2607.27539 applied to a
  gated commit; CGOS inherits its scope limit — the indirect channel through tokens generated after reading the
  observation is not covered — and claims no stronger guarantee than checkpoint replay, only O(d_k d_v)-per-token cost
  instead of replay. The indirect residual against a true replay is reported descriptively for every arm.
- Set-commit (repaired). Concurrent results {j_1..j_m}: all Q_{j_i} fork from the same P and are processed in isolation
  (recurrent: separate varlen sequences with the same initial_state; softmax: sibling-to-sibling attention masked and
  siblings share one start position id — Set-LLM's construction, arXiv 2505.15433, used with credit and applied to EVERY
  arm including the plain hybrid). Per sibling we obtain (Aseg_i, Wseg_i) by running the segment kernel twice more with
  initial_state = I and initial_state = 0 (2x cost on concurrent segments only; a WY-form alternative is noted). The
  persistent state is updated by composing the gated affine maps in canonical call-id order:
      P <- T_{c_m}( ... T_{c_1}(P) ... ),  c = sort_by_call_id({j_i}).
  Because the composition order is a function of the call-id set and each (Aseg_i, Wseg_i, g_i) was computed in isolation,
  the result is invariant to arrival order (bitwise under deterministic kernels) while each result is processed on arrival.
  The wave-1 additive form P + sum_i (Q_i - P) is withdrawn: it multiplies P by (sum_i a_i - (m-1)) for composed decay a_i
  and goes negative for short-horizon units (identification refuter, point 3). Ledger entries for a set store per-sibling
  marginals M_i = compose_with_i - compose_without_i at the set boundary and are propagated like C_j; single-sibling
  retraction is P_T - M_i^{(T)} under the same frozen-input scope; multi-sibling retraction recomposes from the stored
  pairs at the boundary plus one propagation pass (still replay-free for the recurrent state).
- Training: next-token loss on non-obs tokens (agentic-SFT convention; unmasked ablation). The wave-1 ledger regularizer
  lambda_r sum_j ||C_j||^2/||Delta_j||^2 is REMOVED from the base arm (it pushes g -> 0 and confounds the commit-path
  test); if ever reinstated it must be paired with a uniform control (the same penalty on the plain hybrid's write mass
  sum_t beta_t) — not in this pilot.
- Predictive/surprise variant (wave-1 G3 arm): removed from the claim and the pilot. It survives only as a separately
  gated extension whose contract must pre-register a length-matched design (poisoned/unexpected observations generated at
  matched byte length and schema; per-token-normalized forecast target; length-only logistic baseline; within-length-bin
  AUROC; SR-TTT position stratification), answering identification point 4. If Phase 1 kills CGOS it is dead too.

Why training-in could matter (the hypothesis under test, not a guarantee): under the B_obs stub the recurrent commit is
the only carrier of observation content to later decisions, and the gate lets the model make the commit conditional on
the external receipt at the moment the receipt arrives — a plain hybrid has already written a poisoned observation into
its state by then and can only undo it by learned erasure or by harness snapshot/restore. Whether a model trained under
these semantics writes observation content into state more usefully than a truncation-trained plain hybrid, and whether
a plain-trained hybrid tolerates the semantics without training, are empirical questions the arms below separate.

## 3. What is new (downgraded per the novelty caveats)

Stated against the closest priors; each delta is one sentence.

1. Subtract, Transport, or Replay? (arXiv 2607.27539, v1 2026-07-30, v2 2026-08-13; opened by refuters and inventor):
   CGOS inherits their Proposition-1 frozen-input transport verbatim and its scope limit; the delta is not a stronger
   guarantee but (i) a receipt-gated commit that makes the transported object the observation's gated contribution,
   (ii) isolation set-commit for concurrent results, and (iii) TRAINING the model under those semantics, with the
   capability cost as the endpoint — their paper audits a frozen KDA and retrofits an external memory.
2. CommitKV (arXiv 2608.07855, 2026-08-08; opened): training-free KV-page eviction around tool-call commits in
   transformers; CGOS commits into the recurrent state of a hybrid, is trained in, and treats CommitKV-style
   eviction as the harness control it must beat at equal delivered KV.
3. Context-Folding (arXiv 2510.11967, 2025-10-13; abstract opened this wave) with FoldAct (2512.22733) and U-Fold
   (2601.18285) (listing only): RL-trained textual folding of sub-trajectories into summaries at the harness level; CGOS
   folds a tool observation into the recurrent state at a typed boundary with an external receipt as the gate, generates
   no summary tokens, and has algebraic (frozen-input) retraction — Context-Folding is a mandatory conceptual baseline
   for the "architecture subsumes context policy" reading and CGOS makes no efficiency claim against it in this pilot.
4. Set-LLM (arXiv 2505.15433, 2025-05-21; refuter-opened): permutation-invariant attention via masks and shared
   positions over set inputs; CGOS reuses it for the softmax half with credit and adds canonical affine composition for
   the recurrent half; arrival-order invariance is NOT claimed as CGOS's contribution (the harness can also sort).
5. TreeWY (2608.20961), HARTS (2608.28158), DeltaLog (2608.15533) (refuter-opened, abstract level): training-free
   fork/rollback/logging of GDN/KDA state for speculation, RL and serving; CGOS uses them as the training-free
   state-surgery control and asks only whether training-in beats them at capability under the semantics.
6. RW-TTT (2605.28053, 2026-05-27; inventor-opened): request-owned TTT state tags for batched serving; CGOS types state
   within a request by provenance.
7. CoACT (arXiv 2607.02911, 2026-07-03; abstract opened this wave): trained text-level observation compressor with a
   next-action-preservation (NAP) reward; CGOS compresses into state rather than text and ADOPTS NAP as a secondary
   endpoint (does the commit-only path induce the same next action as the raw observation).
8. Learnable token eviction in hybrid sparse attention (arXiv 2510.20787, 2025-10-23; listing only): learned KV eviction
   inside hybrids; a control for the fixed B_obs stub if the stub choice is challenged.

No direct prior art found through 2026-09-01 under the coverage in section 11 for a receipt-gated, trained-in commit of
tool observations into the recurrent state of a GDN hybrid with isolation composition of concurrent results. The
recombination is specific but modest; the scientific content is the capability-cost comparison, not the algebra.

## 4. Falsifiable predictions

- P1 (Phase 0, frozen, no training). (a) Permuting the arrival order of m = 3 concurrent tool results changes the argmax
  next action at >= 10% of 500 decision points on Qwen3.5-4B (chat template) and shifts the next-token distribution over
  a fixed candidate-action set by mean TV >= 0.05 on startlux gdn-340m-isp-hybrid-3to1-10b and Kimi-Linear-48B-A3B-Base
  (few-shot, base models). (b) Training-free surgery (fork/commit with g = 1, canonical set-commit, restore on invalid
  receipt, B_obs = 64 stub) on the frozen startlux 340M loses G0 >= 5 pt held-out task success versus plain inference.
  The retraction half of wave-1 P1 is withdrawn (already answered by 2607.27539).
- P2 (Phase 1, primary). CGOS closes >= 80% of G0: CGOS >= P - 1.0 pt on sealed held-out worlds (paired over 3 seeds,
  clustered SEs), and CGOS >= (P + surgery) + 5 pt.
- P3 (Phase 1, strata). CGOS >= TT + 3 pt on concurrent-call decisions and >= TT + 5 pt on invalid-receipt decisions;
  poisoned-content adoption from invalid-receipt observations: CGOS 0.0% (doctor, by construction), TT and P >= 20%,
  P + harness restore 0.0% (parity acknowledged: adoption does not favour CGOS over harness restore; only accuracy under
  the semantics does).
- P4 (commit path carries information). CGOS >= NC (never-commit, g = 0) + 10 pt on observation-dependent decisions;
  median learned g on valid receipts in [0.3, 0.95]; NAP agreement (commit-only vs raw-observation next action) >= 0.9
  for CGOS vs <= 0.7 for TT under the same stub.
- P5 (cost). Held-out FineWeb-Edu BPB within +0.02 nats of P after continued training; CGOS training throughput >= 0.6x
  plain in the measured cell.

## 5. Kill conditions

- K1 (cheapest, Phase 0): G0 <= 1 pt — the semantics are free on a frozen hybrid, so training-in has nothing to buy;
  the architecture claim dies and the result is "do it in the harness".
- K2 (Phase 0): P1(a) below 3% / TV 0.02 on all three frozen hybrids AND G0 <= 1 pt — motivation collapses.
- K3 (Phase 1): CGOS - TT <= MDE overall and on both strata — receipt gating and isolation add nothing beyond
  truncation-aware training.
- K4: CGOS - NC <= MDE — the commit path is vestigial; invariance and containment were properties of masking and the
  stub, not of the mechanism.
- K5: CGOS <= (P + surgery) + MDE — training-in is unnecessary.
- K6: CGOS <= P - 3 pt while TT >= P - 1 pt — gating/isolation costs capability.
- K7: the two-forward-pass prefix-invariance audit (2608.22876) finds a leak in the fork/commit path that cannot be fixed.
- Inconclusive (not a kill): P itself < 70% held-out success after continued training (substrate incompetence), or the
  measured throughput forces the token budget below 40M per run — escalate to startlux gdn-1.3b-isp-hybrid-3to1-50b
  under a new contract.
MDE rule: threshold = max(1.0 pt, 2.5 x paired SE estimated from the P arm's 3 seeds, which run first).

## 6. Cheapest decisive pilot (planned 11.6 GPU-h + 25% reserve = 14.4 GPU-h on 8xH100)

Phase 0 — kill screen, CPU + <= 2.0 GPU-h (must pass before Phase 1 is enabled).
- CPU (fp64 NumPy reference of the GDN recurrence, ~1 day): doctors (a) T_j with g = 1 equals plain to 1e-12 and with
  valid = 0 is the identity bitwise; (b) canonical affine set-commit is invariant to arrival order bitwise and the
  withdrawn additive form is shown to fail on a 3-sibling example with composed decay 0.5; (c) single-observation
  retraction equals the g = 0 frozen-input counterfactual to 1e-12 (fp64) and <= 1e-3 relative Frobenius in bf16, and the
  indirect residual vs true replay is reported for the same traces; (d) two-forward-pass prefix-invariance audit with
  injected faults localizes 100%; (e) pre-receipt logits are invariant to observation content; (f) ledger cost vs
  checkpoint replay. The synthetic oracle tool-world generator (section 9) is built, seeded and hashed here.
- Infrastructure gate (0.5 GPU-h): digest-pinned image with fla v0.5.2 (commit 9c8e42e762fce087c27b673af4922795d9edb85e,
  the startlux pin), torch 2.7, CUDA 12.6; one Slurm GPU smoke job; one-cell throughput measurement of the plain 340M
  hybrid and of the CGOS path at seq 4096 (the repo's contract requires this before any screen; the same blocker is
  recorded on coded-delta-memory.yaml).
- Frozen probes (1.5 GPU-h): P1(a) on startlux-models/gdn-340m-isp-hybrid-3to1-10b (rev eec9dbb045ddeb90bc53750ac1c68a493af1aa0f,
  Apache-2.0; to be added to models/registry.yaml), qwen3.5-4b (Qwen/Qwen3.5-4B rev 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a,
  Apache-2.0, registered), kimi-linear-48b-a3b-base (rev 3b171c17bfc4ee348599b6781a2ca8715c21c8dc, MIT, registered; bf16
  on 2 GPUs); 500 decision points each from the synthetic worlds plus BFCL `parallel` / `parallel_multiple` cases
  (Apache-2.0) as a real-schema probe. P1(b) surgery gap G0 on the startlux 340M (fla-native) and, if the transformers
  GDN path exposes the state, on Qwen3.5-4B.

Phase 1 — decisive training comparison (~9.6 GPU-h planned), enabled only if K1/K2 do not fire.
- Substrate: continued pretraining of startlux gdn-340m-isp-hybrid-3to1-10b (24 layers: 16 GDN + 8 softmax at every third
  layer; hidden 1024; 4 heads x head_dim 256; vocab 32000; max positions 4096; no short conv, which removes the
  conv-state caveat of 2607.27539). Same init, data, token count, optimizer (AdamW, LR 1e-4 continued, cosine, batch
  32 x 4096) and seeds [42, 43, 44] for every arm; 60M tokens per run (60% synthetic tool-world, 40% FineWeb-Edu).
- Arms: P (plain, no semantics) x3; TT (truncation-trained: B_obs stub during training, in-place writes, no gate, no
  isolation) x3; CGOS x3; NC (CGOS with g = 0: never-commit) x2; FA-ref (SmolLM2-135M, Apache-2.0, registered rev
  93efa2f097d58c2a74874c7e644dbc9b0cee75a2, fine-tuned on the same data with the same Set-LLM masking) with full obs KV
  and with the B_obs stub, x2 seeds each — a softmax-only reference for the "raw tokens" ceiling and "no state channel"
  floor, labelled non-iso-parameter.
- Inference-time arms on trained checkpoints (no training cost): P + state surgery (fork/commit g = 1, canonical
  set-commit, restore on invalid receipt, B_obs stub); TT + surgery; P + harness sort-and-restore; P + CommitKV-style
  boundary eviction at equal delivered KV; CGOS with B_obs = 0 at inference (state-only channel stress test).
- Evaluation (1.0 GPU-h): sealed held-out worlds with unseen tool families (primary), strata, adoption, NAP, BPB, doctors
  (a)-(e) on every arm, all-k-of-k reliability and false-completion rate per the brief's protocol mandates.
- Budget arithmetic at the pre-registered pessimistic throughput (section 7): P/TT 0.56 GPU-h per run x 6 = 3.3; CGOS
  0.88 x 3 = 2.6; NC 0.88 x 2 = 1.8; FA-ref 0.21 x 4 = 0.8; eval 1.0; Phase 0 GPU 2.0 -> 11.6 planned; reserve 25% ->
  14.4 <= 16. Ordering: P seeds first (variance estimate and substrate gate), then CGOS, TT, NC, FA-ref.
- Pre-registered use of headroom if the measured plain throughput is >= 45 kTPS/GPU (plan then costs ~7 GPU-h): in
  order, NC seed 3; CGOS B_obs = 0 trained x2; iso-wall-time P (96M tokens) x1; 2-point LR check (0.5x, 2x) on P and
  CGOS at 30M tokens. Scaling rule if the measured throughput is < 20 kTPS/GPU: 40M tokens per run and FA-ref at 1 seed;
  if < 12 kTPS/GPU: switch to a from-scratch 60M substrate under a new contract.
- No Tinker stage: Kimi-K2.6 is an MLA transformer and Tinker exposes no hidden state; a 1T-scale probe would not measure
  the GDN mechanism (feasibility refuter, point 6).

**pilot_gpu_hours.** 14.4 (11.6 planned + 2.9 reserve).

## 7. Throughput and cost basis (cited)

- E2-TTT, arXiv 2608.21308 (2026-08-28), Appendix B.1: 340M and 1.3B models trained on 15B tokens "takes about 132 and
  348 total GPU hours on H100 GPUs" (=> ~31.6k tokens per H100-second aggregate for a 340M sequence-mixer model at
  seq 2048, plain PyTorch, no Triton kernels); Appendix B.5 / Fig. 5: single H100, 340M, seq 2K, batch 4: 17.6-23.7 kTPS,
  58-70 TFLOPS. First-party, opened (PDF text extracted this wave).
- flash-linear-attention README kernel benchmarks (first-party; GB200, CUDA 12.9): B=4, T=4096, H=64, D=128 fwd+bwd:
  chunk_gdn 5.964 ms vs flash_attn 10.815 ms — the GDN layers are not the bottleneck relative to the softmax layers.
- Gated DeltaNet paper (arXiv 2412.06464) Fig. 3, single H100: GDN throughput ~ DeltaNet, slightly below Mamba2; hybrids
  with SWA faster than pure mixers (qualitative; absolute numbers are in a figure image, not text).
- Pre-registered assumptions: plain 340M hybrid 30 kTPS/GPU (the E2-TTT aggregate figure, taken as a floor because fla's
  Triton path should be faster); CGOS path 1.6x slower (segment-serial varlen launches per observation boundary — one
  launch per boundary index across the whole batch, affine state edits between launches, flex-attention block masks, two
  extra segment passes on concurrent segments only); SmolLM2-135M 80 kTPS/GPU. The 0.5 GPU-h cell replaces these
  assumptions with measurements before Phase 1 spends anything; the scaling rule in section 6 is fixed in advance.
- HP confound (2608.11859 "Small models are much more sensitive to their hyperparameters"): accepted as a limitation.
  Mitigation: all arms share init, optimizer and LR; CGOS is a strict generalization of the plain forward at g = 1, so HP
  transfer is plausible; a 2-point LR check runs only if throughput headroom exists (section 6), otherwise the
  limitation is reported.

## 8. Controls

Iso-init / iso-data / iso-tokens / iso-optimizer across all trained arms (shared startlux checkpoint, shared corpus hash,
shared seeds); Set-LLM masking applied to every arm so invariance-by-masking is a shared property; training-free
state-surgery control on P and on TT (fork/commit g = 1, canonical set-commit, restore on invalid receipt, B_obs stub —
the TreeWY/HARTS/DeltaLog/CommitKV class); truncation-trained hybrid without gating or isolation (TT); never-commit
(NC, g = 0); full-attention reference (SmolLM2-135M, full KV and stub; non-iso-parameter, labelled); harness controls at
inference (sort-then-feed for order, snapshot/restore for abort, mechanical shortening 2608.26218, observation masking
2508.21433, CommitKV-style eviction at equal delivered KV); data-only permutation control is built into every arm (all
training traces carry shuffled arrival orders); iso-wall-time P (conditional); checkpoint replay as the retraction
reference (2607.27539's verified path) with the indirect residual reported for all arms; two-forward-pass audit on every
arm; the fla-hub/transformer-340M-10B iso-parameter softmax model is EXCLUDED from publication arms because its model
card carries no license (same blocker class as delta-net-1.3b-8k in the registry). Tokenizer arms are irrelevant here (all
hybrid arms share the startlux 32K tokenizer); a parity-aware tokenizer arm is not applicable to this candidate.

## 9. Public data plan (no General Translation data required)

- Training, 60%: synthetic oracle tool-world traces from a generator written for this contract (MIT, in-repo,
  deterministic seeds, generator source hash frozen before enablement, the coded-delta-memory.yaml convention): typed
  roles, tool schemas, forward-generated solvable tasks, receipts from harness/receipted_tool_runtime.py semantics, 20%
  invalid-receipt/poisoned observations, parallel-call batches with shuffled arrival, 8-12 subtasks per trace within 4096
  tokens. Sealed held-out worlds use tool families never seen in training.
- Training, 40%: HuggingFaceFW/fineweb-edu, config sample-10BT, revision 87f09149ef4734204d70ed1d046ddc9ca3f2b8f9,
  license ODC-By 1.0 (https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu).
- Format/realism references (no training on model outputs; schema and phrasing statistics only) and optional realism
  eval: NousResearch/hermes-function-calling-v1 (Apache-2.0, rev dae3e1d28cfbcf4b915c04ea1e072030529b4bda),
  glaiveai/glaive-function-calling-v2 (Apache-2.0, rev e7f4b6456019f5d8bcb991ef0dd67d8ff23221ac), Team-ACE/ToolACE
  (Apache-2.0, rev 6bda777c88d21e5a204703c1ee45597a8fa4f734).
- Frozen-model order-sensitivity probes: BFCL `parallel` and `parallel_multiple` categories from
  https://github.com/ShishirPatil/gorilla (Apache-2.0 per README; category counts not in the README — read from
  `bfcl test-categories` at contract time).
- Dropped from training: postmanlabs/apiflow-bench-transcripts (Apache-2.0 repo, but model outputs remain subject to
  generating providers' terms — unresolved for training use; format reference only). Salesforce/xlam-function-calling-60k
  (CC-BY-4.0, gated auto) optional eval only.
- Optional multilingual probe (not required): openlanguagedata/flores_plus (CC-BY-SA-4.0, gated auto, rev
  5fec6c13f9e5a4db2f745d4ec0d7c9721ddc4f06) to translate task instructions with observations fixed. General Translation
  parallel data is an optional upgrade for this probe only.

## 10. Kevin advantage

The harness, not the data: harness/receipted_tool_runtime.py already produces hash-chained receipts (the rcpt token's
source), harness/causal_memory_trials.py implements paired audits and assignment journals (the paired replay oracle and
the surgery-gap scoring), and the Docker/Slurm/SIGUSR1 machinery runs the 15 short continued-training jobs as one
sbatch array with resume. 8xH100 covers the frozen probes on Kimi-Linear-48B-A3B-Base and the whole Phase 1 in a day.
Parallel translation data is honestly secondary (optional multilingual probe only) — accepted as noted by the
feasibility refuter.

## 11. Collision risk: medium

Searches this wave (hostsearch, >= 5 s spacing): arXiv `abs:"context folding" AND abs:agent` -> 4 (Context-Folding, FoldAct,
U-Fold, Agent Banana; all harness/text level); arXiv `abs:agent AND abs:tool AND abs:observation AND (recurrent state |
linear attention | state space) AND (compress | summar | fold)` -> 0; HF papers "compress tool observations into recurrent
state hybrid linear attention agent boundary" -> 20 (CoACT, Squeez, learnable token eviction 2510.20787, HOLA 2607.02303,
AsyncTool, SIT-Graph — none commit observations into recurrent state at typed boundaries); abstracts opened: 2608.12149,
2607.02911, 2607.02303, 2510.11967. Wave-1 coverage (19 host queries, 3 WebSearch, 6 papers) stands. Coverage limits:
Semantic Scholar and full-text search unavailable; arXiv host queries are conjunctive; a typed-state linear-RNN agent
paper under different vocabulary could exist. The KV-lifecycle and serving-algebra axes gained five papers in August 2026,
so a KV-side or serving-side version is likely within months; the trained-in capability-cost question is less exposed.

## 12. Monitorability and safety

Auditability increases (per-observation commit ledger; receipt-gated writes; exact abort containment as a
right-to-be-forgotten primitive for tool content at the recurrent layer, scoped to the frozen-input counterfactual). CoT
tokens are untouched. Risks: the B_obs stub removes raw observation tokens from later attention, so later claims about
tool outputs are checkable only against the persisted tool log (the harness persists raw outputs and receipts); type
assignment is a new trust boundary (HarnessRisk 2608.17597) — a mistyped-injection threat arm is mandatory at
evaluation; the removed predictive arm's "acts before receipt" risk no longer applies. IP: NVIDIA's pending
US20260105282A1 "Gated delta networks" covers the GDN operator; CGOS modifies no kernel (affine state edits between
unmodified kernel calls) which reduces but does not remove exposure — legal review before publication. Data rights: every
source is license-named in section 9; no proprietary traces; no General Translation data required.

## 13. Negative-result value

K1 (surgery is free): a publishable "observation-boundary semantics are a harness property on GDN hybrids" result with
the first order-sensitivity numbers for open KDA/GDN hybrids and a verified fork/commit/set-commit/retraction doctor
reusable for hybrid-state-provenance-ledger and provenance-typed-attention. K3/K4 (gating/isolation add nothing beyond
truncation-aware training): supports the 2026 harness-layer consensus (CommitKV, Context-Folding) and closes G20/G21 as
architecture. Either way the fla v0.5.2 image, the registry entry for the first open small GDN 3:1 hybrid base, and the
hashed tool-world generator are infrastructure the program needs regardless.

## 14. Gaps targeted

G7 (reset/deletion guarantees for recurrent state, scoped honestly), G20, G21 (agent-native architecture; harness
context policy internalized — now tested against the harness), G6 (evaluation protocol adopted), and the brief's
still-open "stability, poisoning, reset and deletion guarantees for fast weights" axis. The predictive-arm gaps (G14
surprise receipt) are no longer targeted by this candidate.

## 15. Repairs ledger (wave-1 objection -> fix or accepted limitation)

Identification 1 (retraction counterfactual mixed; tautological half is 2607.27539 Prop. 1; plain GDN is already exact
under frozen inputs): FIXED — retraction is scored only against the frozen-input counterfactual, credited to Prop. 1,
demoted to a Phase-0 doctor; the "plain GDN drifts >= 10%" contrast and the retraction half of P1 are withdrawn; the
indirect residual vs true replay is reported descriptively for all arms.
Identification 2 (containment is a harness/inference property; state-surgery control missing): FIXED — training-free
state surgery on P and TT is now the primary comparator; containment/adoption is a doctor with parity to harness restore
stated explicitly; the claim is about capability cost under the semantics.
Identification 3 (additive set-commit unsound; commit likely vestigial; no g = 0 arm): FIXED — canonical affine
composition replaces the additive form (with the refuter's counterexample as a Phase-0 doctor); never-commit arm and K4
added; lambda_r removed; Set-LLM credited and applied to all arms; B_obs = 0 stress variant added.
Identification 4 (length shortcut in the surprise receipt): FIXED by removal — the predictive arm is out of the claim
and pilot; its future contract must be length-matched.
Feasibility 1 (predictive arm outside budget): FIXED — removed from the claim.
Feasibility 2 (unmeasured throughput; no fla stack; sequential launches): FIXED — cited H100 figures (E2-TTT App. B.1/
B.5; fla kernel table), pessimistic pre-registered assumptions, a 0.5 GPU-h measurement cell as a hard gate, a
pre-registered scaling rule, a digest-pinned fla v0.5.2 image as a Phase-0 deliverable, and a substrate switch from
125M-from-scratch to continued training of a released Apache-2.0 340M 3:1 GDN hybrid.
Feasibility 3 (HP confound, 2608.11859): ACCEPTED LIMITATION with mitigation (shared init/optimizer/LR; strict
generalization at g = 1; conditional 2-point LR check).
Feasibility 4 (endpoints hold by construction; KL-vs-replay ill-posed; no variance estimate): FIXED — by-construction
properties are doctors; primary endpoint is held-out task success on sealed worlds with unseen tool families; MDE rule
from the P arm's seeds run first; NAP adopted as a secondary endpoint.
Feasibility 5 (no generator; APIFlow license): FIXED — generator is a hashed Phase-0 deliverable; APIFlow dropped from
training; all data sources license-named.
Feasibility 6 (Tinker leg irrelevant; base-model scaffolding): FIXED — Tinker stage removed; frozen probes use
candidate-set next-token distributions with few-shot prompts on base models and the chat template on Qwen3.5-4B.
Feasibility 7 (does not use parallel data): ACCEPTED — kevin_advantage is the harness and the node; parallel data is an
optional probe only.
Novelty caveats (retraction advantage is efficiency not guarantee; recombination modest): ACCEPTED — what_is_new
downgraded accordingly in section 3.
