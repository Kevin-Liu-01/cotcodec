# Inventor note — angle G: agent-native sequence architecture (2026-09-01)

Inventor cell: `G-agent-native-architecture`. Brief: architecture (not harness) that treats tool
calls, tool results and receipts as typed inputs — action/observation-boundary-aware attention,
state resets at tool boundaries, provenance-typed KV; must not be a strap-on.

Inputs read in full: `context.md`, `design/brief.md`, `sweep/synthesis.md` (sections 0–6; section 7
is the URL appendix), `sweep/harness-ecosystem.md`, `sweep/arxiv-triage-agents-eval-ml.md`,
`sweep/killshot-current.md`; targeted sections of `sweep/latent-reasoning.md` (tool-use × monitorability
gaps), `sweep/ttt-fastweights.md` (section 4–5: stability/poisoning/reset/deletion), `sweep/seq-operators.md`
(F28–F29), `sweep/benchmarks-eval.md` (agent-benchmark integrity, G4), `sweep/arxiv-triage-arch.md`
(tool/agent rows); repo: `research/frontier-systems-program-2026-08-10.md` (occupied + rejected
tables), `models/registry.yaml`, `research/proposals/_template.md`, `experiments/architectures/causal-memory-holdout.yaml`
(harness vocabulary: stage0 doctors, arms, paired audit, output contract).

Honesty rules applied: no "completely novel"; every prior below carries a URL and a date; every
abstract marked **opened** was read through WebFetch (a summarizer, so numbers are as returned and
may carry transcription error); items marked **not opened** are cited from search listings only.
Gaps are stated as "No direct prior art found through 2026-09-01 under <coverage>".

---

## 0. Where the angle sits after the sweep

What is occupied around this angle (all dates 2026 unless noted):

- Harness-level treatment of tool boundaries is dense and largely settled as *policy outside the
  model*: mechanical shortening of older tool results (Same Model, Different Harness 2608.26218:
  F2PF 28% → 49% on a 20,480-token window), observation masking (Complexity Trap 2508.21433 halves
  cost; regime map 2606.00408 across 4B–284B), per-tool retention policies by RL (TRACER 2608.29363,
  29–46% token reduction), programmatic context management (2608.21690), semantic-object working
  memory measurement (2608.31057), pixels-as-history (VERA 2608.29897), StateM's "durable states,
  phase-local context, checked transitions" (2608.15089, 95.3% TB2.1).
- KV-side typed lifecycle is occupied *training-free*: MemDecay (2607.10582; region-aware eviction
  over system/scratchpad/user/retrieved/tool regions; Qwen2.5-1.5B/3B; system-token half-lives
  148–189 vs scratchpad 14–16 decode steps) and CommitKV (2608.07855; page removal keyed to
  tool-call commit transitions in ReAct agents; numbers not in abstract).
- Recurrent-state algebra for hybrids is occupied at the serving/training-systems layer: DeltaLog
  (2608.15533, bounded update log, semantics unchanged), TreeWY (2608.20961, tree WY for draft
  trees), Tail-Replay (2608.30310, 5–10% suffix replay reconstructs state at 92.8–99.9% quality),
  DASC, HARTS (2608.28158, chunk-boundary state recovery for agentic RL — explicitly a systems
  concern), RW-TTT (2605.28053, owner/version/READ-WRITE tagging for batched serving; no
  reset/rollback/deletion semantics).
- Instruction/data separation inside the architecture exists at the *embedding* level only: ISE
  (2410.09102, ICLR 2025; +15.75%/+18.68% robust accuracy on StruQ/IH) and ASIDE (2503.10566, ICLR
  2026; orthogonal rotation of data-token embeddings). Everything else is training-only (OpenAI
  Instruction Hierarchy 2404.13208; GW-DPO 2606.10860, 5 levels) or system-level (CaMeL 2601.09923,
  not opened).
- Agent-level world models are occupied at the harness layer (DreamGuard 2608.05695 external
  recurrent risk model, 25 ms/call; SafeMCP 2606.01991; COMAP 2606.02372; MCP-Cosmos 2605.09131 —
  the last three listed, not opened) and inside a GUI policy as a screenshot-alignment objective
  (MIRAGE 2606.04627). Diffusion-native typed tool interaction is staked as a concept without
  empirics (CID 2608.10438, read-only tools).
- Measurements that motivate the angle: FACE-Eval (2608.29464): all 15 models (4B–1.60T) verbalize
  tool-return cues less than user-message cues and adopt them unverbalized more; Utility Under
  Attack (2608.21230): 1.2% poisoned memories drop LongMemEval 0.850 → 0.300, a four-stage screener
  rejects 0/360 poisons, provenance weighting is indistinguishable from no defense (p = 0.80);
  Auditable Deletion (2607.27539, F29): native KDA fails the "subtract" receipt class (12–49% drift;
  8–49% after a decay ledger), checkpoint replay is the only verified path; APIFlow-Bench
  (2608.29128): 93% → 61% over 20-subtask chains, 77% of clean failures reached the correct state and
  failed at delivery, provenance canary grading; OmnilingualGAIA2 (2608.08775, benchmarks-eval cell):
  scale-invariant 8.8–18.4 pass@3 multilingual gap concentrated in tool orchestration.
- Theory: tools with external read/write state make a finite-precision *selective* SSM controller
  Turing-complete with O(log|Q| + log|Γ|) controller bits (2607.06155, opened) — the controller
  should be small and selective and the tool carries state; 2510.06828 argues recurrence-complete
  models are needed for long agentic action sequences (untyped).

What every cell left empty and this angle can take (with the synthesis gap ids): verifiable
reset/rollback/deletion and poisoning containment for recurrent/fast-weight state (G7); an
instrument separating environment nondeterminism from agent effects (G20 — arrival order of
parallel tool results is one such source); explicit confidence/syndrome inside recurrent state
(triage open axis, no G id); monitorability of tool influence on tool-use tasks by a non-CoT
channel (G14); harness context policy internalized as architecture (G21, which the synthesis
recorded as harness-layer only).

Design rule used for all three candidates: the type of a token comes from the trace format (chat
roles, tool-call / tool-result delimiters, a receipt token emitted by the tool layer), never from
content, so typing adds no content classifier; and every mechanism lives inside the sequence
operator (recurrence, attention logits, value path), so none is a strap-on layer.

---

## 1. Candidate A (architecture-causal, core) — `commit-gated-observation-state` (CGOS)

### Claim
In GDN/KDA-style hybrids, forking the recurrent state at each tool-observation boundary and
committing the observation's aggregate state effect through a receipt-gated, logged commit gives, by
construction, (i) bitwise containment of un-receipted observations, (ii) replay-free exact
retraction of an observation's *direct* state contribution (the receipt class native KDA fails in
2607.27539), and (iii) permutation invariance over concurrently returned tool results — at ≤ 0.5 pt
tool-world accuracy and ≤ +0.02 nats BPB cost at matched parameters — and it can replace the
harness's mechanical observation-shortening policy at equal delivered tokens.

### Mechanism
Tokens carry a provenance type tau_t in {sys, usr, rsn, act, obs, rcpt}. Each gated-delta-rule
layer keeps a persistent state P (d_k x d_v per head) and, per open observation segment j, a
scratch state Q_j. Transition in GDN convention: A_t = alpha_t (I - beta_t k_t k_t^T),
u_t = beta_t k_t v_t^T.
- tau_t not in {obs}: P <- A_t P + u_t; read o_t = P^T q_t.
- obs-start(j) (tool-result delimiter): Q_j <- P (fork).
- tau_t = obs inside j: Q_j <- A_t Q_j + u_t; read o_t = Q_j^T q_t; P unchanged.
- receipt token r_j (type rcpt; the tool layer always emits it, carrying exit code, schema-validity
  bit, byte length, hash prefix): Delta_j = Q_j - P; g_j = valid_j * sigmoid(W_g h_{r_j} + b_g)
  in [0,1]^{d_v} (valid_j is the hard external receipt bit); commit C_j = Delta_j diag(g_j);
  P <- P + C_j; append (j, C_j) to a ledger L of the K most recent commits; discard Q_j; in the
  softmax-attention layers, obs-typed KV entries of segment j are truncated to a fixed budget B_obs
  (first/last B_obs/2 tokens plus the receipt) once the next act token is emitted.
- Concurrent tool results {j_1..j_m} (parallel calls): all Q_{j_i} fork from the same P and are
  processed without seeing siblings (isolation); commits are summed in canonical call-id order,
  P <- P + sum_i C_{j_i}; in attention layers sibling segments share one starting position id and
  sibling-to-sibling attention is masked, so the next token's attention over siblings is a set
  operation. The next-action distribution is therefore invariant to arrival order, bitwise up to
  the canonical summation order.
- Ledger propagation for t > r_j: C_j <- A_t C_j (the transition is linear in the state; cost
  O(d_k d_v) per entry per token; rank(C_j) ≤ rank(Delta_j)). Retraction of observation j at
  time T: P_T^{(-j)} = P_T - C_j^{(T)}, exactly the state that results from g_j = 0 with all later
  tokens' (k, v, alpha, beta) held fixed — the "subtract" receipt class. Abort (valid_j = 0)
  leaves P bitwise unchanged and drops the obs KV — containment.
- Training: next-token loss on non-obs tokens (agentic-SFT convention; ablation: unmasked) plus a
  ledger regularizer lambda_r * sum_j ||C_j||_F^2 / ||Delta_j||_F^2 (ablation: lambda_r = 0).
- Honest scope: the retraction guarantee covers the observation's direct state contribution.
  Indirect effects through tokens the model already generated after reading the observation are
  outside any state-level receipt (F29 names the same limit for "later transition and write
  terms"); we measure that indirect residual explicitly against a clean replay without the
  observation and report it alongside the direct guarantee.

### What is new (three closest priors, all opened)
1. **Subtract, Transport, or Replay? Auditable Deletion from Language-Model Memory** —
   https://arxiv.org/abs/2607.27539 — v1 2026-07-30, v2 2026-08-13. Native KDA fails the subtract
   receipt (12–49% drift; 8–49% after a decay ledger); checkpoint replay is the only verified path;
   constructive part is a support-vector memory retrofit on frozen Gemma 3 (1.85% ppl at 4B).
   Delta: CGOS changes the recurrence so that the observation's direct contribution is one logged,
   forward-propagated object; the subtract receipt becomes satisfiable by construction and abort is
   bitwise exact — an architecture, not an audit or an external memory.
2. **RW-TTT: Batched Serving for Request-Owned Test-Time Training State** —
   https://arxiv.org/abs/2605.28053 — 2026-05-27. Tags each decode step with owner, version and
   READ/WRITE effect to batch compatible phases and commit updates only to the owner. Delta: CGOS
   types state *within* a request by provenance and defines fork/commit/abort/set-commit inside the
   operator; RW-TTT defines no reset, rollback or deletion semantics (serving correctness only).
3. **CommitKV: Lifecycle-Aware KV Cache Compression via Commit Transitions for Multi-Turn Agents** —
   https://arxiv.org/abs/2608.07855 — 2026-08-08. Training-free removal of KV pages whose deletion
   effect is measured before a tool-call commit and after the returned observation is incorporated.
   Delta: CGOS acts on the recurrent state of GDN/KDA hybrids where token-addressable eviction is
   impossible, is trained in so the model learns to write across the boundary, and yields exact
   retraction and order invariance rather than eviction.
Adjacent (opened unless noted): DeltaLog 2608.15533 (bounded update log for serving; semantics
unchanged), TreeWY 2608.20961 (branch WY for draft trees), Tail-Replay 2608.30310 (mandatory
deletion/state-summary control), HARTS 2608.28158 (training-systems state recovery), Agentic
Transaction 2608.13900 (system-level semantic ACID — naming collision; CGOS avoids "transactional"
as its headline term), PINE 2407.01100 (softmax-only document order invariance), Stable-RAG
2601.02993 (ACL 2026; permutation sensitivity of retrieved documents; decoding-side fix), 2607.06155
(theory), MemDecay 2607.10582 and TRACER 2608.29363 (typed retention at KV/harness level), 2510.06828
(recurrence-complete action models, untyped), Verified Tool Calls 2608.02645 (harness-layer
postcondition verification and idempotency keys — the receipt vocabulary CGOS consumes).

### Falsifiable predictions
- P1 (the problem exists; frozen models, no training): on APIFlow-style synthetic worlds and BFCL
  parallel-call cases, permuting the arrival order of m = 3 concurrent tool results changes the
  next action at ≥ 10% of decision points for `qwen3.5-4b` and `kimi-linear-48b-a3b-base`, and
  retracting one consumed observation shifts the recurrent contribution by ≥ 10% (F29's range is
  12–49%). If both fall below 3%, the motivation collapses.
- P2 (containment and retraction, CGOS-125M): abort leaves P bitwise identical to never-read in
  100% of 10,000 audited observations; retraction vs replay-with-g_j = 0 has relative Frobenius
  error ≤ 1e-3 in bf16 and next-token KL ≤ 1e-4 nats; the plain GDN control drifts ≥ 10% and
  Tail-Replay at 5–10% suffix budget shows KL ≥ 1e-2 (its own 92.8–99.9% quality band).
- P3 (order invariance): total-variation distance between next-action distributions under sibling
  permutation is 0 (bitwise) for CGOS set-commit and ≥ 0.05 on average for the plain hybrid trained
  on the same shuffled traces.
- P4 (capability): held-out tool-world accuracy within 0.5 pt (paired, 3 seeds, clustered SEs) of
  the plain 3:1 hybrid; natural-text validation BPB within +0.02 nats.
- P5 (architecture subsumes the context policy): at a 20K delivered-token budget on 20-subtask
  chains, CGOS with scratch discard (B_obs = 64) ≥ plain hybrid + the 2608.26218 mechanical
  shortening policy at equal delivered tokens.
- P6 (poison containment, oracle world): adoption of content from an aborted (invalid-receipt)
  poisoned observation in later actions = 0.0% for CGOS vs ≥ 20% for the plain hybrid.

### Kill conditions
P1 below thresholds on both frozen hybrids; P4 loss ≥ 1 pt or BPB ≥ +0.05 nats at matched
params/FLOPs; the two-forward-pass prefix-invariance audit (2608.22876) finds a leak in the
fork/commit kernel that cannot be fixed; the gate saturates at g ≈ 1 everywhere and the ledger costs
more than checkpoint replay at equal deletion fidelity (CGOS degenerates to "GDN + DeltaLog"); a
data-only control (plain hybrid trained on all sibling permutations) reaches order invariance
within 0.5 pt accuracy (set-commit unnecessary); P5 loses to the harness policy by ≥ 2 pt (kills
only the internalized-context-policy claim).

### Cheapest decisive pilot (≤ 16 GPU-hours on 8×H100)
- Phase 0 — CPU, no LM (~1 day): NumPy fp64 reference of the GDN recurrence with fork/commit/ledger.
  Doctors: (a) algebra — P_T - C_j^{(T)} equals replay with g_j = 0 to 1e-12; (b) set-commit
  permutation invariance bitwise under canonical order; (c) two-forward-pass prefix-invariance audit
  (2608.22876) on the fused chunkwise kernel with injected faults — must localize 100%; (d) leakage —
  perturb observation content, all pre-receipt logits unchanged; (e) ledger memory/time vs
  checkpoint replay. Phase-0 must pass before any GPU.
- Phase 1 — frozen models (~2 GPU-h): order-sensitivity and retraction-drift on `qwen3.5-4b`,
  `kimi-linear-48b-a3b-base` (bf16 on 8×H100), `delta-net-1.3b-8k`; 500 decision points each; P1.
- Phase 2 — from-scratch screen (~13 GPU-h): 125M 3:1 GDN/softmax hybrid (fla ≥ 0.5.2 kernels),
  1.5B tokens per run (a screen, ~12N tokens; promotion needs the 3-size ≥ 10× compute ladder);
  data: 60% synthetic long-horizon tool-world traces generated forward with oracle solvability
  (APIFlow-Bench recipe; its 44,362 released transcripts as format reference), 20% of observations
  poisoned or invalid-receipt, parallel-call batches with shuffled arrival; 40% FineWeb-Edu. Arms
  (3 seeds each): plain hybrid; CGOS; CGOS lambda_r = 0; CGOS without set-commit; plain hybrid +
  SWA-with-sinks (2608.28444); evaluation-time harness arms on the plain hybrid: mechanical
  shortening (2608.26218), observation masking (2508.21433), CommitKV-style boundary-keyed KV
  eviction; Tail-Replay 5%/10% and checkpoint replay as deletion controls. ~1 GPU-h per run at
  30–40% MFU → 15 runs ≈ 13 GPU-h + 1 GPU-h evaluation.
- Tinker stage (evaluation only, ~5M sampled tokens): Kimi-K2.6 and Qwen3.5-35B-A3B order-sensitivity
  probes through the sampling API to test whether P1 persists at 1T; Tinker cannot change the
  operator, so this is a scale-only measurement.
- Model ids: `qwen3.5-4b`, `kimi-linear-48b-a3b-base`, `delta-net-1.3b-8k`, `smollm2-135m` (loader
  and tokenizer reference). Seeds [42, 43, 44]. gpu_hours: 16.

### Controls
Iso-parameter plain 3:1 GDN hybrid with per-arm HP search at the smallest rung (2608.11859);
SWA+sinks (2608.28444, mandatory); Tail-Replay 5%/10% (2608.30310, mandatory for any state-summary
or deletion claim); checkpoint replay (F29's verified path); QED-GDN2 (2608.13668) and MARCH
(2608.12435) on the same MQAR-style recall probes; data-only permutation augmentation; harness
controls: mechanical shortening (2608.26218), observation masking (2508.21433 / 2606.00408),
CommitKV-style eviction; two-forward-pass audit on every arm; paired scoring with token ledger,
all-k-of-k reliability and false-completion rate (APIFlow-Bench, FrontierChallenge mandates).

### Kevin advantage
The harness's deterministic replay, hash-chained receipts and SIGUSR1 checkpoint/resume are exactly
the machinery for the retraction/containment audits and the paired replay oracle (the CMHT spine in
`harness/causal_memory_trials.py` already implements paired audits and assignment journals);
8×H100 covers the frozen-model measurement on Kimi-Linear-48B-A3B-Base and the 125M grid in a day;
Kimi-Linear-48B-A3B-Base and Qwen3.5-4B/9B are the only registered KDA/GDN hybrids where P1 can be
measured today. Parallel translation data is secondary: translated task instructions with fixed
observations give an optional language-controlled probe of whether typed boundaries shrink the
tool-orchestration multilingual gap (OmnilingualGAIA2, 8.8–18.4 pts).

### Collision risk: medium
Searches run (host relay, 5 s spacing): arXiv API `abs:agent AND abs:tool AND (recurrent state |
linear attention | state space model) AND observation` → 2 (2607.06155 theory; one unrelated);
`abs:rollback AND agent AND (recurrent state | fast weight | test-time training)` → 0; `abs:"tool
output" AND (KV cache | compression) AND agent` → 14 (TRACER, CommitKV-adjacent MemDecay, Paritok,
Context-as-Environment, 2608.31057 — all KV/harness level); DDG "parallel tool calls order of tool
results sensitivity" → 0; HF papers "transactional commit rollback tool call recurrent state" →
StateM, Agentic Transaction (system level), Verified Tool Calls, LedgerAgent; HF papers "recurrent
state reset tool boundary agent linear attention" → nothing typed; arXiv search UI `"tool results"
order OR permutation agent position bias` → 0 results; `gh search repos` x5 → 0. No direct prior art
found through 2026-09-01 under this coverage for provenance-typed fork/commit inside a delta-rule
recurrence. The surrounding KV-lifecycle and serving-algebra axes gained five papers in August
2026, so a KV-side or serving-side version could appear within months.

### Monitorability and safety
Auditability increases: a per-observation commit ledger, receipt-gated writes, and exact
containment give a right-to-be-forgotten primitive for tool content at the recurrent layer. CoT
tokens are untouched, so CoT monitorability is unchanged. Risks: scratch discard removes raw
observation tokens from later attention, so later claims about tool outputs are checkable only
against the tool log (the harness must persist raw outputs — it already does); type assignment is
a new trust boundary — HarnessRisk (2608.17597) finds harness configuration the most vulnerable
phase, so a "mistyped injection" threat arm is mandatory. Data rights: synthetic worlds, FineWeb-Edu
(ODC-By), APIFlow transcripts (license to verify), no proprietary traces.

### Negative-result value
If typed fork/commit costs capability or the gate saturates, we learn that observation-boundary
discipline belongs in the harness (supporting the 2026 harness-layer consensus) and still deliver
the first quantified order-sensitivity and retraction-drift numbers for open KDA/GDN hybrids plus a
verified retraction doctor (ledger algebra + prefix-invariance audit) reusable for G7.

### Gaps targeted
G7, G20, G21 (as architecture), G6 (protocol adopted).

---

## 2. Candidate B (cheap-decisive) — `provenance-typed-attention` (PTA)

### Claim
Typing tokens by provenance at the attention level — a per-head learned type-pair logit bias, a
typed value path for observation tokens, and per-head type gates — lets a 135M–0.6B tool-using
model separate data-to-copy from instructions-to-follow better than embedding-level typing (ISE,
ASIDE) at matched parameters, halving tool-output injection success in multi-turn loops at ≤ 0.5 pt
utility cost, and exposes a provenance attention-mass channel that a weak monitor can read to detect
unverbalized tool-return influence (FACE-Eval's failure mode).

### Mechanism
Types tau in T = {sys, usr, rsn, act, obs, rcpt}, |T| = 6, from the trace format. In layer l,
head h: logit_ij = q_i · k_j / sqrt(d) + b^{l,h}[tau_i, tau_j] + causal mask, with b a learned 6×6
table (36 parameters per head). Typed value path: v_j = (W_V + D_{tau_j}) x_j with D_tau a rank-8
delta that is zero for tau in {sys, usr, rsn, act} and non-zero for obs and rcpt, so data provenance
has its own value subspace. Per-head type gate: p_ij <- gamma^{l,h}[tau_i, tau_j] · softmax_j(logit_ij),
renormalized over j, gamma in [0,1], with an L1 penalty lambda_g * sum |gamma| pushing heads to
specialize by provenance pair. PTA-hard: gamma[act, obs] = 0 on a designated half of the heads in
the top third of layers, so action queries can read observations only through the remaining heads
whose value path is the typed D_obs subspace — the structural falsifier for "instruction-following
from data can be removed by construction while copying survives". Monitor channel:
M_i[tau] = (1/H) sum_h sum_{j: tau_j = tau} p^{h}_{ij}, logged at every act/answer position; the weak
monitor is a logistic regression on (M_i[obs], M_i[usr], M_i[sys]) with no access to text.
Retrofit form for a frozen checkpoint: add b, D_obs, D_rcpt, gamma (≈ 0.5M parameters on
`qwen3-0.6b-base`) and fine-tune on typed traces.

### What is new (three closest priors, all opened)
1. **Instructional Segment Embedding: Improving LLM Safety with Instruction Hierarchy** —
   https://arxiv.org/abs/2410.09102 — v1 2024-10-09, v2 2025-03-01, ICLR 2025. BERT-style segment
   embeddings by priority; +15.75% / +18.68% robust accuracy on StruQ / Instruction Hierarchy,
   +4.1% AlpacaEval. Delta: PTA types at the attention level (per-head type-pair bias, typed value
   path, per-head gates) rather than at the input embedding, covers multi-turn tool loops with a
   receipt type, admits a structural ablation (PTA-hard) that embedding typing cannot express, and
   adds a provenance-mass monitor channel evaluated against unverbalized tool-return adoption.
2. **ASIDE: Architectural Separation of Instructions and Data in Language Models** —
   https://arxiv.org/abs/2503.10566 — v1 2025-03-13, v4 2026-02-09, ICLR 2026. Orthogonal rotation
   of data-token embeddings, no new parameters, higher instruction–data separation and injection
   robustness without safety training. Delta: as above; ASIDE fixes one binary instruction/data
   split, PTA has six provenance types including receipts and reasoning, and is evaluated
   multi-turn with cross-lingual instruction control.
3. **Training LLMs to Enforce Multi-Level Instruction Hierarchies via Gravity-Weighted DPO** —
   https://arxiv.org/abs/2606.10860 — 2026-06-09. Five-level hierarchy, ten pairwise relations,
   preference optimization on top of delimiter tokens + ISE; Llama-3.1-8B-Instruct; training-only.
   Delta: PTA is architectural and testable by structural ablation; GW-DPO is the strongest
   training-only control and is included as an arm.
Adjacent: OpenAI Instruction Hierarchy 2404.13208 (data-level, opened), StruQ 2402.06363 (listed,
not opened), FACE-Eval 2608.29464 (measurement instrument, opened), Utility Under Attack 2608.21230
(provenance *ranking* at retrieval fails — motivates typed *processing*; opened), MemDecay
2607.10582 (typed KV eviction, opened), AgentDojo 2406.13352 (97 tasks, 629 security cases; opened),
2510.05106 (attention-entropy analysis of rule encodings; analysis only; opened), 2608.24022
(attention-matrix adjudication of unauthorized behavior; listed, not opened), CaMeL 2601.09923
(system-level; not opened).

### Falsifiable predictions
- P1: injection attack success on AgentDojo-style multi-turn tool tasks (0.6B retrofit) and on
  synthetic tool worlds with injected instructions inside observations (135M): PTA ≤ 0.5× the ASR
  of the ISE and ASIDE arms at matched utility (e.g., 40% → ≤ 20%); PTA-hard ≤ 5% ASR with ≤ 2 pt
  utility drop.
- P2: unverbalized tool-return adoption (FACE-Eval protocol adapted to the 0.6B model): the weak
  monitor on M_i reaches AUROC ≥ 0.80; the same monitor on an untyped model's attention mass over
  the tool-return span ≤ 0.65.
- P3: tool-call and argument accuracy within 0.5 pt of the untyped control; BPB within +0.01 nats.
- P4 (Kevin arm): with task instructions translated into six languages (General Translation
  parallel data) and observations fixed, PTA's cross-language injection-ASR spread (max − min) is
  ≤ 0.5× the untyped model's spread.

### Kill conditions
ISE or ASIDE at matched parameters within noise of PTA on P1 and P2 (PTA becomes a replication,
not an architecture result); PTA-hard costs ≥ 2 pt utility; monitor AUROC < 0.7; the mistyping
threat arm (harness assigns wrong types) breaks PTA worse than the baselines (typing creates a
larger attack surface than it removes).

### Cheapest decisive pilot (≈ 11 GPU-hours)
- Phase 0 — CPU: typed attention in NumPy; doctors: type-pair bias equals an additive ALiBi-style
  bias numerically; PTA-hard gradient-flow check (zero gradient from obs keys to act queries in
  gated heads); type ids come only from delimiters (leakage check); monitor-channel algebra.
- Phase 1 — from scratch (~8.5 GPU-h): 135M dense transformer (SmolLM2-135M shape; `smollm2-135m`
  as loader/tokenizer reference), 1B tokens (60% synthetic tool worlds with injected instructions,
  40% FineWeb-Edu); arms: untyped + delimiters, ISE, ASIDE, PTA, PTA-hard; 3 seeds; ≈ 0.56 GPU-h per
  run → 15 runs.
- Phase 2 — retrofit (~2 GPU-h): `qwen3-0.6b-base` + PTA parameters, fine-tuned on 50M tokens of
  typed agent traces (APIFlow-Bench transcripts, SWE-smith / mini-swe-agent trajectories, Tmax),
  same five arms × 3 seeds (~8 min each); evaluate AgentDojo (97 tasks, 629 cases), FACE-Eval-style
  probes, the mistyping threat arm, and P4 with translated instructions.
- Tinker stage (control at scale, 30M tokens): Qwen3.5-4B LoRA with typed delimiters + GW-DPO-style
  preference data — the "can training alone do it" control.
- Seeds [42, 43, 44]. gpu_hours: 11.

### Controls
Iso-parameter untyped model with delimiter tokens; ISE; ASIDE; GW-DPO-style preference training
at 0.6B (data-only); StruQ-style structured queries; MemDecay typed KV eviction at inference (does
typed retention alone reduce injection?); mistyping threat arm (HarnessRisk); 2026 evaluation
mandates: paired passes with token ledger, all-k-of-k reliability (APIFlow-Bench), false-completion
rate (FrontierChallenge); per-arm HP search at the 135M rung (2608.11859).

### Kevin advantage
`qwen3-0.6b-base` is registered for retrofit; the harness has agent-loop, oracle and
paired-regression contracts; parallel translation data yields the language-controlled injection
probe (P4) that other groups do not have at hand; 8×H100 covers everything in a day. Honest: the
core mechanism needs none of Kevin's unique assets.

### Collision risk: medium-high
Searches: arXiv API `abs:"segment embedding" AND instruction AND "language model"` → ISE only;
`abs:"prompt injection" AND architectur AND attention AND agent` → one analysis paper (2510.05106);
`abs:provenance AND attention AND "language model" AND (tool | agent)` → nothing relevant;
OpenReview "architectural separation instructions data" → ASIDE only; HF papers x2 → ISE, ASIDE,
GW-DPO, StruQ, IH, Soft De-escalation, CaMeL, 2608.05430 (detection); arXiv search UI `"segment
embedding" OR "role embedding" tool agent attention` (277 results; first 25 reviewed by summary,
none introduce typed attention or masks); `gh search repos` x2 → 0. No direct prior art found through
2026-09-01 under this coverage for attention-level provenance typing in tool loops; the
instruction-hierarchy axis is crowded and a typed-attention paper could appear any month.

### Monitorability and safety
Adds a non-CoT monitor channel (provenance mass) — a positive; CoT untouched. Risks: type ids are a
new trust boundary (mistyping attack); a typed value path could make the model ignore legitimate
instructions embedded in data (README instructions in a repository) — measure under-following on a
"legitimate instruction in tool output" set alongside AgentDojo utility. Data rights: AgentDojo
(MIT), SWE-smith (MIT), FineWeb-Edu (ODC-By), APIFlow transcripts (license to verify).

### Negative-result value
If embedding-level typing suffices, the field learns attention-level typing is unnecessary; we
still deliver the first tool-loop, multi-turn, cross-lingual evaluation of ISE/ASIDE with a
monitor-channel test and a mistyping threat measurement.

### Gaps targeted
G14 (a non-CoT monitor channel on tool-use tasks), G21 (multilingual instruction effects, as
architecture), the OmnilingualGAIA2 tool-orchestration gap, FACE-Eval's tool-return unfaithfulness.

---

## 3. Candidate C (moonshot) — `predictive-observation-commit` (POC)

### Claim
If the actor emits, when it issues a tool call, a forecast of the observation's aggregate state
effect, and the boundary commit writes only the residual between realized and forecast effect, then
(i) routine tool results commit near-zero state, (ii) the residual norm is an architecture-native,
causally clean "surprise receipt" that a weak monitor can read to flag unexpected or poisoned tool
outputs with AUROC ≥ 0.9 in an oracle world, and (iii) the model can continue decoding on the
forecast during tool latency with a bounded, ledger-backed correction — an AR-hybrid analog of
CID's asynchronous tool interaction.

### Why the surprise-gated-memory rejection does not hold here
The brief rejects Titans/TRIM-KV-style surprise gating because the axis is occupied and because
SR-TTT v2 (2603.06642, v2 2026-07-22) showed token-level gradient surprise is position-biased
(0–1% needle containment at depth 0.1: the reconstruction loss needs burn-in) and its recall gains
were causality artifacts (0% exact match in 2,250 corrected trials). POC differs in object and use:
the forecast is action-conditioned and emitted before any observation token exists, so its
causality is auditable by construction (perturbing the observation must leave the forecast bitwise
unchanged); it is computed on the observation's aggregate state effect at a typed boundary, not
per token, so there is no burn-in; and it is used for commit sparsity, monitoring and containment,
not for memory retention — no exact-recall claim is made. If the screen shows position bias or an
uninformative residual, the result is that the rejection extends to boundary-level surprise.

### Mechanism
Builds on CGOS fork/commit. At the act token a_j that issues call j: forecast Dhat_j = F_j G_j^T with
F_j = reshape(W_F h_{a_j}) in R^{d_k × r_f}, G_j = reshape(W_G h_{a_j}) in R^{d_v × r_f}, r_f = 8;
pre-commit P <- P + Dhat_j (the model may keep decoding on the forecast while the tool runs). On
receipt r_j: Q_j is forked from the pre-forecast P and processed as in CGOS; Delta_j = Q_j − P_fork;
residual eps_j = Delta_j − Dhat_j; commit C_j = valid_j · eps_j diag(g_j); P <- P + C_j; the ledger
stores (Dhat_j, C_j) so both are retractable. Surprise receipt
s_j = ||eps_j||_F / (||Delta_j||_F + ||Dhat_j||_F + c), logged per observation. Training: LM loss
on non-obs tokens + lambda_f · ||stopgrad(Delta_j) − Dhat_j||_F^2 / (||stopgrad(Delta_j)||_F^2 + c)
(the stop-gradient blocks the collapse mode "make Delta predictable by writing nothing"; the
||Delta_j|| distribution is monitored and collapse is a kill) + the CGOS ledger regularizer. Async
mode (optional, off by default): between a_j and r_j the model decodes with P + Dhat_j and no obs
KV; on receipt, if s_j exceeds a threshold the pre-commit is rolled back through the ledger and
decoding resumes from a_j.

### What is new (three closest priors, all opened)
1. **Titans: Learning to Memorize at Test Time** — https://arxiv.org/abs/2501.00663 — 2024-12-31.
   Neural long-term memory module; its write signal is the token-level gradient-based surprise
   described in the paper body (the abstract page does not define it). Delta: boundary-level,
   action-conditioned forecast made before the observation exists; residual used for sparsity,
   monitoring and containment; causality auditable; no retention claim; SR-TTT's position-bias
   failure is a pre-registered kill test.
2. **MIRAGE: Mobile Agents with Implicit Reasoning and Generative World Models** —
   https://arxiv.org/abs/2606.04627 — v1 2026-06-03, v2 2026-06-06. Latent reasoning vectors aligned
   with future screenshots (world-model objective inside a GUI policy); AndroidWorld parity with
   CoT-SFT at 3–5× fewer decoded tokens. Delta: the forecast target is the observation's state
   effect inside the sequence operator, the residual is committed, logged and evaluated as a
   monitor/poison signal, in text tool loops, with retraction through the ledger.
3. **DreamGuard: Efficient Runtime Guardrail for LLM Agents via Risk-Aware World Model** —
   https://arxiv.org/abs/2608.05695 — 2026-08-06. A separate runtime world model with a compact
   recurrent latent predicting future latent states to gate actions before execution (25 ms/call).
   Delta: the forecast lives in the policy's own recurrent state (no second model), gates writes
   rather than actions, and is evaluated for calibration and position bias under the SR-TTT
   protocol.
Adjacent (opened unless noted): DreamLedger 2608.23863 (execution-settled credit for world-model
predictions, robotics), CID 2608.10438 (typed cognitive tensor with persistent bindings; diffusion;
no empirics), SR-TTT v2 2603.06642, LongVU-TTT 2608.25729 (fast weights aggregate rather than
remember), SafeMCP 2606.01991 / COMAP 2606.02372 / MCP-Cosmos 2605.09131 (harness-level world
models; not opened), 2601.03905 (agents fail to use world models as tools; not opened), AsyncTool
2605.27995 (asynchronous function-calling benchmark; not opened).

### Falsifiable predictions
- P1: in the oracle tool world (designed unexpected outcomes: failures, schema drift, injected
  poison), s_j separates unexpected from routine observations with AUROC ≥ 0.90; a weak monitor
  (logistic on s_j and type) reaches ≥ 0.85 vs ≤ 0.70 for a text-only monitor of equal size reading
  the observation text.
- P2: write sparsity — ≥ 60% of routine observations commit ||C_j|| ≤ 0.1 ||Delta_j|| with task
  accuracy within 0.5 pt of CGOS.
- P3: no position bias — detection AUROC in the first 10% of a trajectory vs the last 10% differs
  by ≤ 0.05 (SR-TTT's failure mode was 0–1% containment at depth 0.1).
- P4: causality — the two-forward-pass audit finds zero leaks and the forecast is bitwise invariant
  to observation content in 100% of 10,000 audited calls.
- P5 (async): decoding on the pre-commit for routine observations changes the next action in
  ≤ 2% of cases relative to waiting for the observation.

### Kill conditions
AUROC < 0.7 or a position-bias gap > 0.1; collapse of ||Delta_j|| that the stop-gradient does not
prevent; an adaptive poison crafted to match the forecast reaches ≥ 50% adoption with s_j below
threshold (the receipt is gameable by an adversary who can query the model); task accuracy loss
≥ 1 pt versus CGOS.

### Cheapest decisive pilot (≈ 13 GPU-hours; depends on Candidate A's Phase-2 checkpoints)
- Phase 0 — CPU: forecast/residual algebra; causality-ordering doctor; Gaussian-world
  identifiability (can a rank-8 forecast recover designed residuals; what fraction of designed
  surprise is detectable at each rank).
- Phase 1 (~13 GPU-h): CGOS-125M vs CGOS+POC, 3 seeds, 1.5B tokens on the oracle tool world with
  designed surprise labels (≈ 1 GPU-h per run → 6 runs); a Titans-style token-gradient surprise
  gate on a matched-size TTT layer as the rejected-axis control (3 runs); adaptive-attack
  evaluation, monitor training, position-bias stratification (~2 GPU-h). Baseline monitors:
  text-only weak monitor (SmolLM2-135M classifier), per-token loss spikes on the plain hybrid, a
  DreamGuard-style external recurrent predictor of equal parameter count.
- Model ids: `smollm2-135m` (monitor and loader reference); CGOS-125M from Candidate A. Seeds
  [42, 43, 44]. gpu_hours: 13. No Tinker stage: the mechanism cannot be hosted through LoRA-only
  access, and a 1T-scale probe of tool-output predictability would be evaluation only.

### Controls
CGOS without forecast; plain hybrid with perplexity-based surprise over the observation; Titans-style
gradient-surprise gate on a matched TTT layer; text-only weak monitor; DreamGuard-style external
predictor at equal parameters; permutation-augmented data; two-forward-pass audit; paired scoring;
SR-TTT-style startup causality self-tests and depth stratification.

### Kevin advantage
The paired replay oracle and receipts label "unexpected" without an LLM judge (Memory Reward
Inflation, 2608.00017, warns that LLM-scored utility inflates); otherwise none — parallel data is
irrelevant here and Tinker cannot host the mechanism.

### Collision risk: medium
Searches: arXiv API `abs:agent AND tool AND "world model" AND (predict the outcome | predicted
observation | tool output prediction)` → 2 (reasoning world models for parallel code 2604.20926;
policy-guided trajectory diffusion 2312.08533); HF papers "predict tool output before execution
world model residual" → ToolGym, AsyncTool, "Can We Predict Before Executing ML Agents"
(2601.05930), MICE for CATs — none architectural; arXiv search UI (tool predicted observation world
model residual | surprise; 25 reviewed by summary) → DreamGuard, SafeMCP, COMAP at harness level;
abstracts opened: Titans, MIRAGE, DreamGuard, DreamLedger, CID, SR-TTT v2, LongVU-TTT. No direct
prior art found through 2026-09-01 under this coverage for an action-conditioned forecast of the
observation's state effect committed as a residual inside the recurrence; world-models-for-agents
is a fast-moving harness-level field and the surprise-gating axis is explicitly rejected, so the
burden of proof is on the identifiability screen.

### Monitorability and safety
Adds a non-CoT surprise receipt (positive). Risks: a model decoding on its own forecast can act on
hallucinated tool results — async mode stays off by default, is gated by s_j and receipts, and the
"acts before receipt" rate is a reported metric; adversarial low-surprise poisons must be tested
adaptively; the forecast head is an internal world model that could reduce grounding. Data rights:
synthetic worlds only.

### Negative-result value
If boundary-level, action-conditioned surprise is uninformative or position-biased, the rejection
of surprise-gated designs extends to the boundary level, LongVU-TTT's "aggregation, not memory"
finding gets a controlled agentic confirmation, and the CID-style asynchronous AR variant is shown
not to be free.

### Gaps targeted
Triage open axis "explicit error syndrome / confidence inside recurrent state" (no G id; nearest
G7 and G14), G6 (causality protocol), G7 (poisoning).

---

## 4. Collision ledger (mechanism → closest occupant → status)

| Component | Closest occupant (URL, date, opened?) | Status under coverage |
|---|---|---|
| Fork/commit of recurrent state at typed observation boundaries | RW-TTT 2605.28053 (2026-05-27, opened): request-owned isolation for serving | not found; adjacent only |
| Replay-free exact retraction of an observation's direct state contribution | Auditable Deletion 2607.27539 (v2 2026-08-13, opened): native KDA fails; replay only | negative prior; construction not found |
| Bounded ledger of state updates | DeltaLog 2608.15533 (2026-08-16, opened): serving, semantics unchanged | occupied for serving; typed/retractable use not found |
| Boundary-keyed KV lifecycle | CommitKV 2608.07855 (2026-08-08, opened); MemDecay 2607.10582 (2026-07-12, opened); TRACER 2608.29363 (2026-08-29, opened) | occupied (training-free / harness); trained-in recurrent version not found |
| Order invariance over concurrent tool results | PINE 2407.01100 (2024-07-01, opened; documents, softmax, training-free); Stable-RAG 2601.02993 (ACL 2026, opened; decoding-side) | not found for tool results or recurrent models |
| ACID vocabulary for agents | Agentic Transaction 2608.13900 (2026-08-14, opened): system-level semantic ACID | naming collision; CGOS avoids "transactional" as headline |
| Attention-level provenance typing | ISE 2410.09102 (ICLR 2025, opened); ASIDE 2503.10566 (ICLR 2026, opened) — embedding level | not found at attention level; crowded axis |
| Provenance attention mass as monitor channel | FACE-Eval 2608.29464 (2026-08-29, opened) measures the failure; 2608.24022 (not opened) analyzes attention matrices | not found as an architectural channel |
| Action-conditioned forecast of observation state effect, residual commit | Titans 2501.00663 (opened); MIRAGE 2606.04627 (opened); DreamGuard 2608.05695 (opened); CID 2608.10438 (opened) | not found; rejected-axis proximity acknowledged |

## 5. Coverage limits (this cell)

- WebSearch budget was exhausted before this cell started; not used.
- Host-relay searches: exactly 12 (`hostsearch.sh`: 7 arXiv API, 1 DDG, 2 HF papers, 1 OpenReview,
  1 arXiv API), 5 s spacing, run as one background batch. arXiv API queries are exact-term matches
  and miss paraphrased abstracts; DDG returned 0 (likely bot challenge).
- From this Mac: HF papers API × 8, `gh search repos` × 5 (all 0 — queries likely too specific),
  arXiv search UI × 3 via WebFetch (one returned 0 results; two returned 25-of-N pages whose
  entries were reviewed by the WebFetch summarizer, not read verbatim), `ft search` × 6 on Kevin's
  bookmarks (no architecture-level agent signal; harness/context-engineering posts only — interest
  evidence).
- 40 abstract pages opened through WebFetch (summarizer output; numbers quoted as returned). No
  full texts, no code, no OpenReview reviews beyond one search, no Semantic Scholar, no ACL
  Anthology, no Chinese-language sources, no ICLR 2027 submissions.
- Not verified: licenses of APIFlow-Bench transcripts and Tmax data; whether fla ≥ 0.5.2 exposes a
  chunkwise GDN kernel that admits a fork/commit hook without a custom kernel (Phase 0 must settle
  this before Phase 2 of Candidate A).
- All 2026 items are first-party preprints unless a venue is stated (ISE ICLR 2025; ASIDE ICLR 2026;
  Stable-RAG ACL 2026; Harness-RL "PCC 2026" per its page; SINKFLEX-RL COLM 2026 workshop).
