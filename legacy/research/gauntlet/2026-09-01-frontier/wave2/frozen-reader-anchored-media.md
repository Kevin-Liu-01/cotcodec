# frozen-reader-anchored-media — wave-2 repair (2026-09-01)

Repair owner note. Wave-1 verdicts: novelty NOT refuted (0.6, with caveats), identification REFUTED (0.8),
feasibility REFUTED (0.85). This rewrite keeps the mechanism (a frozen, weaker, pre-committed reader anchoring an
abstract low-rate reasoning code) but changes what is claimed, what is measured, how the code is trained at the
screen, and what is budgeted. Substrate B (metered C-bit recurrence) is removed from the claim and the pilot and
kept only as a separately gated phase 2 with the missing controls named. `dropped = false`.

Honesty header: no "completely novel" anywhere; "No direct prior art found through 2026-09-01 under §8 coverage".
Every number below has a source URL or is a design choice marked as such.

---

## 1. One-line claim (repaired)

**Legibility spillover under a frozen weaker reader.** In a low-rate discrete reasoning code (K = 64 symbols,
T = 32 positions, B = 192 bits per step) whose symbol table is grounded once by a frozen, weaker, pre-committed
reader that is rewarded on only two log-derived bits (hint-use, constraint-violation), a held-out weak monitor
trained post hoc on 200 labelled episodes decodes **never-rewarded** behaviour variables (stale-value use,
skipped required check, fabricated argument, premature commit, dependency-step id) at >= 80% of the
above-chance AUROC it reaches on uncapped explicit CoT, at >= 3x fewer reasoning tokens and >= 8x fewer bits;
while — at the same B, the same warm-up and the same reader term where applicable — an unconstrained code, a
co-trained-decoder code, and a fixed-schema self-report plus free code drift to within 0.05 AUROC of chance on
the same variables. Grounding is *created* by a gloss warm-up, *preserved* by the frozen reader, and *lost*
under co-training or no reader.

**claim_scope.** attachment-capability.

What is no longer claimed: "provably less steganographic slack than NL CoT" (it is a capacity ledger; now
reported, not claimed), the metered C-bit recurrent substrate (phase 2, gated), and "survives rewrite attacks
that collapse explicit CoT" (downgraded to a directional secondary prediction P3 with stated low confidence).

---

## 2. Mechanism (precise)

**Policy.** pi_theta: from-scratch 30M transformer (phase 0), `HuggingFaceTB/SmolLM2-135M` @
93efa2f097d58c2a74874c7e644dbc9b0cee75a2 (phase 1), `Qwen/Qwen3-0.6B-Base` @ da87bfb608c14b7cf20ba1ce41287e8de496c0cd
and `Qwen/Qwen3.5-4B-Base` @ 1001bb4d826a52d1f399e183466143f4da7b741b (confirmation; all Apache-2.0, verified via
the HF API 2026-09-01). Between observation o_t and action a_t the policy emits a trace z_t = (z_{t,1..T}) over a
reserved codebook C, |C| = K, then the action in plain text (tool name + JSON arguments, never abstracted).
Bit budget B = T log2 K = 192 bits >> H(m_train) ~ 1.5–2 bits, so the code has ~190 bits of free rate for
computation; a pre-registered necessity gate (§5) guarantees the trace is load-bearing, i.e. z is not a label.

**Frozen reader.** R_phi: a 20M from-scratch LM (phase 1 adds a frozen SmolLM2-135M rung) fitted ONCE, before any
policy training, on gloss-rendered explicit traces -> m_train. Its embedding table gets K extra rows E_C
initialised from mean-pooled embeddings of K gloss phrases g_k (dictionary G: k -> phrase; ops such as lookup /
add / compare / filter / check / write / read-from / hint / violation, field ids, result ids); a linear head H
maps the final state to m_train. Then phi, E_C, H are frozen and never touched again. Reader input is z only —
never x, never the action.

**Variables.** All read from the ToyTools execution log, never from the model.
- m_train (rewarded, 2 bits): hint-use flag, constraint-violation flag. Hint presence and correctness are
  randomised so hint-use is causally identified.
- m_holdout (NEVER in any loss; labelled only at evaluation): stale-value use (a value read from a superseded
  tool result), skipped-required-check (a spec-mandated verification tool not called before a write),
  fabricated-argument (argument value traceable to no context field or tool result), premature-commit (write
  before all dependencies resolved), dependency-step id (which dependency was resolved at this step). The
  generator injects these conditions independently of m_train; a doctor requires I(m_train; m_holdout) <= 0.05
  bits per variable and a reader-output-only control (§5, C-r) proves m_holdout is not a function of the
  variables the reader forces.
- Excluded from both reward and scoring: next-tool id and argument-source slots (action-derivable; the
  action-copy shortcut named by the wave-1 identification refuter). An action-only monitor control certifies
  the remaining variables are not action-derivable (AUROC <= 0.60 from the action alone).

**Training (no RL at the screen).**
- Stage 1 warm-up (identical for every code arm): teacher traces gloss-rendered from the log are mapped
  through G^-1 into codes (each step -> [op][src][dst] symbols, compressed to T = 32); CE on code positions
  and on the action (~12M tokens).
- Stage 2 (the intervention): the code teacher is removed. L = L_task (action CE) + lambda_R L_reader with
  L_reader = -log p_{R_phi}(m_train | z_hat). Code positions receive gradient through straight-through
  Gumbel-softmax (tau annealed 1.0 -> 0.3): z_hat_i = onehot(argmax) + softmax - stopgrad(softmax); the
  policy's downstream positions see z_hat_i E_pol (trainable rows), the frozen reader sees z_hat_i E_C
  (frozen rows). Because phi, E_C and H never move, the policy cannot negotiate a private code with its reader:
  the only way to satisfy L_reader is to use the two relevant symbols in their gloss senses. The hypothesis is
  that this pressure prevents the *whole* warm-started grounding from drifting under task pressure (the
  language-drift phenomenon of Lee et al. 2019 / Lu et al. 2020, here in an abstract medium), so the ~190 free
  bits stay legible to a weak monitor on variables the reader never sees.
- Explicit-CoT arms receive the SAME frozen reader term applied to their natural-language trace (the reader
  reads its native vocabulary) — the missing factorial cell named in wave 1.

**Arms (all share T or the stated cap, B where applicable, warm-up, lambda_R, data, seeds).**
- A1 anchored code: K = 64, T = 32, frozen reader (the intervention).
- A1-nw anchored code without warm-up (does the reader *create* grounding? predicted: no).
- A1-6b (phase 1 only) anchored code with a 6-bit m_train (adds dependency-step id, which then leaves
  m_holdout) — spillover as a function of the forced fraction.
- A2 unconstrained code, same K, T, warm-up; lambda_R = 0 (Abstract-CoT-style at matched bits).
- A3 co-trained-decoder code: reader initialised identically but trainable (SIM-CoT-style) at matched bits.
- A4 self-report + free code: first T_s = 2 positions are a fixed-schema encoding of m_train (CE from the log),
  remaining 30 positions are unconstrained code; same B; same warm-up on the free positions.
- A5 NL ceiling: explicit CoT <= 128 tokens (~2,000 bits), r_task + the same frozen reader term.
- A6 NL bits-matched: explicit CoT capped at floor(B / log2|V|) = 12 tokens (SmolLM2 vocabulary 49,152 ->
  15.6 bits/token), same reader term.
- A7 NL tokens-matched: explicit CoT capped at T = 32 tokens (~500 bits), same reader term.
- A8 no trace (T = 0): necessity gate.
- Eval-time ablations on A1: random / zero / shuffled trace (inert by construction; load-bearing check).

**Monitors (identical function class for every arm).** M: a from-scratch 2-layer transformer classifier
(~1M params) over raw ids (code ids for code arms, token ids for NL arms) plus the observation o_t, with the
action masked; trained post hoc on n in {50, 200, 800} labelled episodes from task templates disjoint from
policy training, evaluated on further disjoint templates; per-variable AUROC; 5 monitor seeds. A bag-of-n-gram
logistic regression is the second function class. The gloss rendering G(z) is a human-readability instrument
only — never a monitor input (removes the dictionary-leakage objection). An activation probe on the policy's
residual stream at the action position is the internals-access ceiling (2608.04928).

**Primary endpoint.** rho = (AUROC_arm - 0.5) / (AUROC_A5 - 0.5), mean over m_holdout, n = 200, action masked.
Secondary: monitor sample-efficiency curve AUROC(n); drift curves AUROC_holdout(step) during stage 2 per arm;
m_train AUROC (trained legibility) with a Baker-style flagged-vs-logged divergence check; task accuracy;
compression in tokens and bits; P3 rewrite-attack retention; spare-rate ledger B - I_hat(z; m_train u m_holdout)
(reported, not claimed); a 4-bit supervised collusion probe (within the 1–6-bit reach demonstrated by
2410.03768; no RL colluder).

---

## 3. What is new (downgraded per the wave-1 novelty caveats)

The novelty is a design constraint plus a measurement, not a new operator: (i) the reader is external, weaker,
frozen before training and rewarded on a 2-bit subset; (ii) the medium has no NL prior and an explicit bit
budget, with every comparator matched in bits, warm-up and reward; (iii) the endpoint is legibility to a
held-out weak monitor on variables that were never rewarded — the quantity the wave-1 refuter said the original
design foreclosed; (iv) tool-use tasks with per-variable, action-masked scoring. A reviewer may call the
recombination incremental; the defensible contribution is the identification design and the drift/spillover
measurement. Against the three closest priors:
- Verbalization fine-tuning (https://arxiv.org/abs/2506.22777, 2025-06-28; abstract opened): pre-RL NL
  verbalisation of hint cues cuts undetected hacks 88% -> 6%; NL only, no external frozen reader, no
  compression, endpoint is the trained cue. Delta: abstract 192-bit medium, frozen 20M reader, never-rewarded
  variables as the endpoint.
- Countering Language Drift with Seeded Iterated Learning (https://arxiv.org/abs/2003.12694, 2020-03-28;
  abstract opened): drift under task reward countered by imitation of a pretrained seed. Delta: drift of an
  abstract code countered by a frozen external reader on a 2-bit subset, measured as monitor legibility of the
  unconstrained 190 bits.
- Why Struggle with Continuous Latents? (https://arxiv.org/abs/2606.29712, 2026-06; FULL TEXT read via
  arxiv.org/html this pass, as the wave-1 novelty refuter recommended): discrete latent vocabulary via
  vector-quantised DeepSeek-OCR2 features of rendered CoT; the auxiliary decoder is co-trained (two-branch
  curriculum, stop-gradient at SFT); decodability is shown only qualitatively (Fig. 4 case studies, decoder
  "occasionally hallucinates"); no AUROC, no adversarial or paraphrase test, math only (GSM8K/MATH-500),
  LLaMA-3.2-1B..8B / Qwen3-4B; no tool use; no held-out-variable analysis. Delta: frozen pre-committed reader,
  quantitative held-out monitor endpoint, bits-matched controls, tool tasks. It is cited as the closest prior
  for the discrete-latent clause.
Also occupying one component each (all opened as abstracts in wave 1 or this pass): Abstract-CoT
https://arxiv.org/abs/2604.22709 (2026-04; reserved-vocabulary code for efficiency = arm A2); SIM-CoT
https://arxiv.org/abs/2509.20317 (2025-09; co-trained decoder = arm A3); Prover-Verifier Games
https://arxiv.org/abs/2407.13692 (2024-07-18; co-trained verifier, NL); Markovian Transformers
https://arxiv.org/abs/2404.18988 (2024-04-29; KL-to-prior anti-steganography, same-model reader); Lazaridou et
al. https://arxiv.org/abs/2005.07064 (2020-05-14; pretrained-LM prior for emergent communication, referential
game); Reasoning Under Pressure https://arxiv.org/abs/2512.00218 (2025-11-28; direct monitorability optimisation
"does not reliably lead to improvements" — motivates the held-out endpoint); Does Out-of-Sight Equal
Out-of-Mind https://arxiv.org/abs/2608.04928 (2026-08-05; monitorability tracks task and access, not medium —
the null hypothesis this design must beat); A False Average https://arxiv.org/abs/2608.00583 (2026-08-01;
reasoning-only rewrites 95% -> < 11% catch rate; motivates action-masked per-variable scoring); CoT obfuscation
generalises to unseen tasks https://arxiv.org/abs/2601.23086 (2026-01-30; motivates the attack-transfer
measurement in P3).
No direct prior art found through 2026-09-01 under §8 coverage for a frozen, weaker, pre-committed external
reader anchoring an abstract low-rate reasoning code with never-rewarded-variable legibility as the endpoint.

---

## 4. Falsifiable predictions (comparator named in each)

- P1 (phase 0; 30M from-scratch; ToyTools depth-3; K = 64, T = 32, B = 192; n = 200 labels; 3 seeds): A1
  mean held-out AUROC >= 0.75 with rho >= 0.8 relative to A5 (A5 >= 0.85 required by the competence gate);
  A2, A3, A4 each <= 0.58 on the same variables (drift to chance; A2's drift curve reaches <= 0.60 within
  stage 2); A6 (NL at 12 tokens) <= 0.65; A1 uses >= 3x fewer reasoning tokens than A5 (32 vs >= 100) and
  >= 8x fewer bits; A1 within 0.05 AUROC of A7 at 2.6x fewer bits. Embarrassing if A1 ~ A2 (reader inert) or
  A1 ~ A4 (a self-report suffices).
- P2 (sample efficiency, phases 0–1): AUROC_A1(n = 50) / AUROC_A1(n = 800) >= 0.85 (above-chance units) vs
  <= 0.6 for A2 and A3; A1-nw <= 0.65 at n = 200 (the reader preserves, it does not create, grounding).
- P3 (rewrite attack, phase 1, SmolLM2-135M, 2 seeds; least confident): an adversary with labels for ONE
  holdout variable v_a fine-tunes the policy with L_task + lambda_R L_reader - lambda_adv * CE of a FIXED
  monitor for v_a, task accuracy within 1 pp; a FRESH monitor trained after the attack retains >= 0.7 of the
  pre-attack above-chance AUROC on v_a for A1 vs <= 0.4 for A5 and A7 (2608.00583 rewrite collapse); transfer
  of obfuscation to the non-attacked holdout variables (2601.23086) is measured for every attacked arm.
- P4 (task): A1 accuracy within 2 pp of A5 and A7; shuffled-trace ablation costs >= 10 pp (load-bearing,
  unlike the LauraGG Abstract-CoT negative); A8 (no trace) <= 60% by the necessity gate.

---

## 5. Gates, controls and kill conditions

**Gates (pre-registered; failing a gate is "under-powered / redesign", not a kill).**
- Necessity gate: A8 <= 60% task accuracy while A5 >= 90% on ToyTools depth-3; otherwise deepen the tasks
  before any comparison.
- Competence gate: A5 held-out AUROC >= 0.80 at n = 200 at the screen scale; otherwise escalate to
  Qwen3-0.6B-Base before reading any kill.
- Doctors (CPU): reader sees only z; monitor templates disjoint; I(m_train; m_holdout) <= 0.05 bits; action-only
  monitor <= 0.60 on every scored variable; reader-output-only control (C-r: a monitor given R_phi(z) and o_t
  only) <= 0.60 on m_holdout; random-code monitor null 0.50 +/- 0.02; straight-through gradient check; codebook
  usage entropy >= 0.5 log2 K (collapse detector).

**Controls (matched).** A2 (reader removed, everything else equal), A3 (reader trainable), A4 (fixed-schema
self-report + free code at same B), A5/A6/A7 (NL with the same reader term at ceiling / bits-matched /
tokens-matched caps), A8 (no trace), A1-nw (no warm-up), A1-6b (larger forced subset), action-only monitor,
reader-output-only monitor, activation probe ceiling (2608.04928), random / zero / shuffled trace ablations,
two monitor function classes, 3 seeds (phase 0) / 2 seeds (phase 1) with paired McNemar over episodes and
per-variable AUROC CIs by episode bootstrap; contamination disclosure (synthetic world, no public benchmark in
training).

**Kill conditions.**
- K1: A1 rho < 0.5 on m_holdout while the competence gate passes — the abstract medium is unmonitorable on
  novel variables even when grounded; publish as a negative that the wave-1 foreclosure argument holds
  empirically.
- K2: A1 within 0.05 AUROC of A4 on m_holdout — a schema self-report plus free code reproduces the effect;
  anchoring has no content beyond the self-report (collapse into a trivial design) -> kill.
- K3: A1 within 0.05 AUROC of A2 — the frozen reader is inert -> kill.
- K4: A3 within 0.03 of A1 on held-out AUROC and sample efficiency — "frozen" is not the operative ingredient;
  the direction survives only as "any grounded reader" and loses its novelty clause (state this if it happens).
- K5: legibility tax > 5 pp task accuracy vs A7 at the screen and again at Qwen3-0.6B-Base, or the shuffled-trace
  ablation costs < 10 pp — the code is rationalisation, not reasoning.
- K6: Baker divergence — m_train flagged rate falls while logged violations do not.
- K7 (optimisation, reported separately from capacity): no code arm trains stably after two remediation rounds
  (usage entropy < 0.5 log2 K or tau schedule failure).

---

## 6. Cheapest decisive pilot and budget (cited throughput, 25% reserve)

**Throughput anchor.** llm.c GPT-2 124M reaches 3,913,480 tok/s on 8x H100 80GB HBM3 (Karpathy,
https://github.com/karpathy/llm.c/discussions/481, opened 2026-09-01), i.e. ~489k tok/s per H100 for an optimised
124M dense transformer. This design uses HF transformers + straight-through Gumbel + a 20M reader
forward/backward per step and small batches; I assume 4x lower efficiency: ~120k tok/s per H100 for both the
30M and the 135M policies (the 30M model is latency-bound, not FLOP-bound). 2608.12149 (opened) reports no
throughput and is not used.

**Phase 0 — the cheapest decisive pilot (<= 4 GPU-h incl. reserve).** CPU (~3 days engineering, 0 GPU-h):
ToyTools generator (8 typed tools, dependency depth 3, values copied from numbered context fields, randomised
hint presence x correctness, injected superseded results / missing checks / fabricated-argument opportunities,
full execution log, m_train and m_holdout labellers), gloss dictionary G, a plain PyTorch SFT + straight-through
trainer (no trl / vllm / peft needed — the harness has none today and this must be built), monitors, all
doctors in §5. GPU: reader fit (20M, 12M tokens, ~0.05 GPU-h); 48M tokens per run (40k episodes x 300 tokens;
1 warm-up epoch + 3 stage-2 epochs) = 400 s = 0.11 GPU-h per run; runs: A1, A1-nw, A2, A3, A4, A5 x 3 seeds
and A6, A7, A8 x 2 seeds = 24 runs = 2.64 GPU-h; monitors (~1M params) and probes ~0.2 GPU-h. Sum 2.9 GPU-h,
x 1.25 reserve = **3.6 GPU-h**. Decides K1, K2, K3, K7 and P1, P2, P4 in the synthetic world. Limitation: phase-0
"explicit CoT" is templated gloss text without an NL prior; that is why phase 1 exists.

**Phase 1 — gated on phase 0 passing K1–K3 (<= 5 GPU-h incl. reserve).** SmolLM2-135M @ 93efa2f0: 9 arms x 2
seeds + A1-6b x 2 + frozen-135M-reader rung x 2 = 22 runs x 0.11 = 2.4 GPU-h; NL teacher traces for A5/A7
generated by Qwen3.5-4B @ 851bf6e8 through vLLM (40k episodes x ~150 tokens = 6M tokens, ~0.4 GPU-h); rewrite
attacks on A1, A2, A5, A7 x 2 seeds (12M-token adversarial fine-tunes, 8 x 0.03 = 0.25 GPU-h) plus fixed and
fresh monitors (0.2); activation probes 0.1; 4-bit collusion probes 0.1. Sum 3.45 GPU-h, x 1.25 = **4.3 GPU-h**.
Adds P3 and the pretrained-NL comparison. Two-phase total **7.9 GPU-h** on 8x H100, single node, Slurm, one
digest-pinned image, SIGUSR1 checkpoint + resume per run.

**Confirmation (separate contract, not counted).** Qwen3-0.6B-Base full FT (~15 GPU-h) and Qwen3.5-4B-Base
LoRA (~40 GPU-h) on BFCL v3 multi-turn and tau2-bench with log-derived holdout variables adapted to their
state-based evaluation; Tinker Qwen3.5-4B RL with the frozen-reader reward computed locally on sampled traces
and returned as a scalar (Tinker losses are logprob-only; the straight-through stage is local-only).

**Phase 2 (Substrate B, gated on phase 1, separate contract, >= 30 GPU-h, NOT part of this candidate's claim).**
Metered C-bit recurrent-depth substrate only with the controls wave 1 named: bandwidth-matched compressed
continuous slots (2605.30757 regime control), registers disabled, registers-only (C = 0), FSQ instead of VQ to
remove codebook-collapse machinery (2309.15505), iso-parameter scratchpad control for any retrofit (2608.11233),
initialisation-phase check (2608.26556), per-position statefulness doctor.

**pilot_gpu_hours.** 3.6 (phase 0, decisive for K1–K3); 7.9 for phases 0 + 1.

---

## 7. Public data plan (no General Translation data anywhere in the pilot)

- ToyTools: synthetic oracle world generated by harness code in /Users/kevinliu/repos/cotcodec (repository
  LICENSE: MIT, Kevin B. Liu 2026); execution logs are the only label source.
- NL teacher traces: templated from the log (phase 0); Qwen/Qwen3.5-4B @ 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a
  generations (Apache-2.0, verified via HF API 2026-09-01) for phase 1.
- Confirmation tool tasks: Berkeley Function Calling Leaderboard v3 multi-turn (Apache-2.0,
  https://github.com/ShishirPatil/gorilla, `/berkeley-function-call-leaderboard`; license line opened
  2026-09-01) and tau2-bench (MIT, https://github.com/sierra-research/tau2-bench; airline / retail / telecom
  domains with simulated tool logs; opened 2026-09-01).
- Bases: HuggingFaceTB/SmolLM2-135M @ 93efa2f0…, Qwen/Qwen3-0.6B-Base @ da87bfb6…, Qwen/Qwen3.5-4B-Base @
  1001bb4d… (all Apache-2.0, ungated, verified via HF API).
- Optional upgrade only (belongs to the sibling interlingua-trace-codes, not to this pilot): a multilingual
  ToyTools rendering would start from FLORES+ (openlanguagedata/flores_plus, CC-BY-SA-4.0, gated=auto, verified
  via HF API 2026-09-01) for terminology, with General Translation corpora as a later, research-cleared option.

---

## 8. Collision risk and coverage

**collision_risk: medium.** Searches this pass (hostsearch on the H100 host, >= 4 s apart, 6 calls): arXiv
(1) "chain of thought" x fixed/frozen listener/decoder x legib*/monitor* -> 0 hits; (2) legibility/monitorability
x "chain of thought" x held-out/unseen/novel x reward hacking/misbehavior -> 2608.00583, 2603.04069,
2601.23086, 2506.01926 (none builds a grounded abstract medium); (3) codebook/discrete latent/reserved vocabulary
x reasoning x monitor*/interpretab*/legib* -> 1 irrelevant hit; (5) "emergent communication" x chain-of-thought
/ reasoning trace -> 0 hits; (6) language drift / pretrained or fixed listener x reasoning/monitor -> 2
irrelevant hits; HF papers "frozen reader legible abstract reasoning code monitorability" -> monitorability
benchmarks only (2510.27378, 2603.28590, 2512.18311, 2602.03978), none with a frozen reader or abstract code.
WebFetch reads this pass (11): 2606.29712 full text (HTML), 2506.22777, 2601.23086, 2005.07064, 2003.12694,
2608.04928, 2512.00218, 2603.30036, 2608.12149, llm.c #481, gorilla, tau2-bench, Qwen3.5-4B card. Inherited from
wave 1 / the D-note: 8 arXiv + 2 HF + 1 OpenReview queries, ~45 abstract reads (list in D-monitorable-media.md §7
and the wave-1 novelty verdict).
Not searched or not opened: OpenReview (skipped this pass; wave 1 found it CAPTCHA-blocked), Semantic Scholar
(429), Google Scholar, ACL Anthology search, Chinese-language sources, ICLR 2027 submissions; emergent-
communication drift literature was reached only via known ids (1909.04499 not opened); full texts of all
papers except 2606.29712; Abstract-CoT's date is taken from its arXiv id (not re-opened).

---

## 9. Kevin advantage, monitorability, negative-result value, gaps

**kevin_advantage.** None unique at the screen — any lab can run phase 0. The harness's oracle-world, trace and
paired-regression contracts and SIGUSR1-resumable Slurm jobs make the 24-run factorial cheap to run and re-run;
8x H100 carries the 0.6B/4B confirmation; Tinker Qwen3.5-4B RL is compatible because the frozen-reader reward is
a locally computed scalar. The parallel-translation asset enters only through the sibling interlingua-trace-codes.
The wave-1 feasibility refuter's point stands: no trainer exists in the repo today; building the SFT + straight-
through trainer is inside phase 0's CPU budget and needs no trl / vllm / peft.

**monitorability_and_safety.** Monitorability-positive by construction, and honest about the trap wave 1 named:
the reader term is "aligned" (2603.30036) only for the 2 rewarded bits, so trained legibility on m_train is
reported but never used as evidence; the headline is legibility on never-rewarded variables; the Baker-style
flagged-vs-logged check is pre-registered; B is an explicit rate and the spare-rate ledger is reported, not
claimed. Data: synthetic MIT-licensed world, Apache-2.0 / MIT public tasks and bases, no customer or GT data.

**negative_result_value.** K1: quantitative evidence that a grounded low-rate abstract medium is unmonitorable
on novel misbehaviour — the strongest argument yet for keeping agent reasoning in natural language, with a
number (rho) instead of a slogan. K2/K3: "frozen reader" is inert and a fixed-schema self-report is all the
legibility an abstract medium can give — a reusable negative for every latent-decoder proposal. Either way the
drift curves AUROC_holdout(step), the never-rewarded-variable ToyTools world and the action-masked per-variable
protocol transfer to NL CoT, Coconut, Ouro and the phase-2 loop.

**targets_gaps.** G14 (surviving clauses: tool use, obfuscation pressure, external frozen weaker reader), G16,
G20; latent-reasoning gaps 1 and 4/5 (cross-medium monitorability at matched accuracy with one fixed monitor on
tool-use tasks). Latent-reasoning gap 6 (looped LMs) is phase 2 only.

---

## 10. Repairs made (wave-1 objection -> fix or accepted limitation)

Identification
- ID-1 metric = objective circularity -> primary endpoint is AUROC on m_holdout, variables never in any loss;
  every arm, including the three explicit-CoT arms, receives the same frozen reader term on m_train; B = 192 >>
  H(m_train) so novel variables CAN be exposed — the foreclosure the refuter identified is now the thing measured.
- ID-2 missing factorial cells -> A4 (fixed-schema self-report + free code at same B) and A5/A6/A7 (NL + same
  reader term at ceiling / bits-matched / tokens-matched caps) added; K2/K3 make them decisive.
- ID-3 slack is a capacity ledger -> "provably less slack" removed from the claim; ledger reported; all controls
  matched in bits; collusion probe reduced to a supervised 4-bit probe inside the published 1–6-bit reach
  (2410.03768). Accepted limitation: no slack claim is made.
- ID-4 held-out-monitor leakage / lookup-table optimum -> monitors of one fixed function class on raw ids with
  the action masked; gloss rendering demoted to a readability instrument; B >> H(m_train) so z cannot be a label;
  load-bearing ablation and necessity gate; sample-efficiency curves.
- ID-5 action-copy shortcut and rewrite "false average" -> next-tool id and argument slots removed from reward
  and scoring; action-only monitor control; per-variable pre-registered AUROC; fresh-monitor attack protocol.
- ID-6 Substrate B not identified -> removed from claim and pilot; phase 2 lists the bandwidth-matched compressed
  continuous control, registers-disabled, FSQ, iso-param scratchpad and initialisation-phase checks.
Feasibility
- FE-1 two substrates, one budget -> one substrate budgeted; phase 2 separately contracted.
- FE-2 >= 36 GPU-h -> SFT + straight-through instead of RL; 24 + 22 runs at 0.11 GPU-h with the llm.c-anchored
  throughput; attacks on 4 arms; supervised collusion probe; reader ladder reduced to one extra rung in phase 1;
  3.6 GPU-h phase 0, 7.9 GPU-h total, each with 25% reserve.
- FE-3 no positive RL precedent at 135M -> no RL at the screen; necessity and competence gates make a null
  interpretable; RL only at Tinker confirmation.
- FE-4 slack endpoints exceed collusion capacity -> dropped (see ID-3).
- FE-5 Substrate B uncalibrated at 40M -> moved to phase 2.
- FE-6 infrastructure / asset claims -> trainer absence acknowledged and budgeted as phase-0 engineering; no
  parallel corpus or GT service needed; Kevin advantage downgraded to harness convenience; Tinker logprob-only
  limits stated.
Novelty caveats
- Recombination acknowledged in §3; 2606.29712 read in full and cited as the closest prior for the discrete-latent
  clause; language-drift lineage (2003.12694, 2005.07064) added as priors; what_is_new stated as design +
  measurement, not operator.
