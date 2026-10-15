# Research Direction: G2-RL, does the GDN recurrent-state precision of RL rollouts (fp32, fp16, bf16) change GRPO training of a Gated-DeltaNet hybrid (Qwen3.5-4B), and does token-level truncated importance sampling recover it? (pilot of at most 8 GPU-h, then a staged training comparison)

**Status:** draft; gauntlet wave 1 synthesis by the single owner on 2026-10-15 (branch `gauntlet/g2rl-state-precision`, not pushed, not frozen); the draft registration for the pilot is `program/preregistrations/g2rl-state-precision-rl-v1.md` (DRAFT, new experiment id, no ledger row); the blind critic, the refute-first triad and the two reviewers have not run; no GPU job and no host job was submitted by the synthesis; the full training comparison is proposed here and registered separately after the pilot; its admission is Kevin's (D24, D92)
**Owner:** Kevin Liu (program owner); synthesis, mechanism statement, identification, contract and registration by a Claude agent acting as the gauntlet's single synthesis owner
**Source cutoff:** 2026-10-15
**Coverage limits:** orx 0.2.2 (reports itself outdated against 0.2.18) alphaXiv keyword and embedding search and OpenAlex: 98 counted orx discover queries across three cells (frontier 44, kill-shot 25, cross-domain 29), several bounded with `--published-after`; about 71 orx paper full-text or targeted-grep reads (uncounted); 8 web searches; about 51 GitHub issue and code searches (counted separately, see Budget accounting); GitHub file, release and API reads and Hugging Face API reads (uncounted). Not reached: OpenReview (bot challenge on every route; "Forgetting to Forget" 9LUInzhKZc is UNVERIFIABLE_ACCESS), X (HTTP 402), Notion-hosted blogs (did not render: the TIS blog, "When Speed Kills Stability", the IcePop blog; cited through papers that describe them), Wiley full text (403). Not searched: Semantic Scholar and Google Scholar citation graphs, the arXiv API, Reddit, Chinese-language sources (Zhihu, WeChat posts of the Qwen, slime and Ant teams), patents, the ACL Anthology. GitHub code search is incomplete (it returned nothing for repositories known to contain the setting). PRISMA-style: 418 ids returned by the orx discover queries (206 unique), plus web and GitHub hits, screened by title; 71 read beyond the abstract; 0 direct priors; 3 narrowing priors.
**Budgets:** queries=150; wall_minutes=720; tokens=10000000; dollars=150; waves=3; gpu_hours=0.5
**Novelty verdict:** NO_DIRECT_PRIOR_FOUND
**Safety verdict:** PASS
**Evidence bundle:** evidence/2026-10-15-g2rl-state-precision-rl/bundle.json

The budgets are this gauntlet's, cumulative; at least 30 queries are reserved for the three
refuters. The GPU budget (0.5 GPU-h) is for the open-weight reviewer's lane job only; the doctor
reads budgets as integers, parses it as 0 and flags it (left as declared). The novelty verdict
field uses the doctor's vocabulary; the merged kill-shot verdict is **NARROWED**, not OCCUPIED
(frontier and kill-shot cells independently).

## Budget accounting (read before the refuters run)

The synthesis ran no retrieval search. It made one full-text read (`orx paper 2510.19338 --full`,
Sections 5.2-5.2.2) and fetched source snapshots for the bundle (not searches).

| Cell | orx discover | Web search | GitHub issue/code search | Reads (uncounted) |
|---|---:|---:|---:|---|
| Frontier | 44 | 5 | about 41 | 35 paper reads, 7 fetches, about 25 file/API reads |
| Kill-shot | 25 | 0 | about 10 | 16 paper reads, about 12 file reads, 1 fetch |
| Cross-domain | 29 | 3 | 0 | 25 paper reads, 8 fetches |
| Asset and cost | 0 | 0 | 0 | GitHub release, file and HF API reads |
| Synthesis | 0 | 0 | 0 | 1 paper read; source snapshots |
| **Total** | **98** | **8** | **about 51** | |

- Literature searches (orx discover plus web search): **106 of 150**, leaving 44, above the
  refuters' reserve of 30.
- Counting every search that reached a backend, GitHub's search API included (the convention the
  last gauntlet run adopted, D75): **about 157 of 150**. The declared query budget is then
  already exceeded before any refuter runs, and the refuters' reserve is gone.
- The GitHub searches verified framework defaults and issues (verl, NeMo-RL, SGLang, slime, miles,
  vLLM); they are not literature retrieval, but the counting rule does not distinguish them. The
  orchestrator must rule on the convention before the refuters run. If the D75 convention holds,
  the honest exit is the query cap (exit 3), and this wave ends after synthesis.

## Scope

This gauntlet covers one decisive RL training comparison and its pilot.

- **The pilot** (registration draft v1, at most 7.92 cap-GPU-h): makes the stack run in the lane,
  checks the manipulation in verl's own training path, measures the step cost, and reads out at
  the start checkpoint the policy-gradient bias that bf16-state rollouts introduce and the share
  of it that token-TIS removes.
- **The full comparison** (proposed here, registered after the pilot): GRPO training runs with
  fp32 and bf16 state (5 seeds each), then, only if they differ, bf16 with token-TIS (5 seeds) and
  fp16 (3 seeds). It is large: about 640 GPU-h on the null path and about 1,150 GPU-h if Stage 2
  runs (central estimates; 500-1,560 across the step-time range). That is many times this
  program's total GPU use to date (about 10-25 GPU-h, `program/state.json` and the dossier's note),
  so its admission is an explicit Kevin ruling, not an automatic consequence of this gauntlet.

## Merged discovery cells, by mechanism

Four independent cells ran: frontier and novelty, kill-shot, cross-domain, asset and cost. Their
findings are merged below by mechanism, not by cell.

**1. Does a low-precision linear-attention state hurt hybrid RL? Partly published, qualitatively.**
Ring-linear (2510.19338) names a bf16 linear-attention "KVCache" in the inference engine as a
root cause of training-inference disparity ("errors will accumulate progressively during the
recurrent process") and shows RL reward improving as fixes are applied cumulatively, the first
being "Fix KVCache & LM_Head" (Fig. 10). The state fix is bundled with an fp32 LM head, on an
internal Ling stack, with no fp16 arm, no IS crossing, no seeds and no numbers; once aligned, the
report says no algorithmic correction is needed (Sec. 5.2.2). Read in full by the frontier and
kill-shot cells and by the synthesis owner.

**2. Concurrent RL on Qwen3.5 GDN hybrids found nulls at the fp32-state residual.** Yichuan Wang's
blog with the TorchTitan team (first-party, August 2026) compared bitwise trainer-generator parity
against default execution on Qwen3.5-9B-Base and 35B-A3B-Base, always with an fp32 GDN state
cache, mostly one seed, no TIS/MIS arm: an abs-mean log-prob gap of about 0.011 against 0.009 and
no reliable reward gain. IsoExec (vLLM blog, first-party, 2026-08-21) unified execution for the
same models in SkyRL: no meaningful reward improvement over 50 synchronous DAPO steps at 25.3%
step overhead. Neither varied state precision. Relax (2604.11554, first-party ablation) puts a
dense bf16 stack at 0.0122 abs log-prob difference with final reward comparable to FP16's. Prior
for this proposal: at an fp32-level gap (our 0.0078 at 16K), nulls are the norm; bf16 state
(0.0255 mean abs, k3 9-11x fp32 at 16K) is a different regime.

**3. The design template is established on dense and MoE models.** The FP16 paper (2510.26788) ran
precision x correction factorials (token-TIS prolongs but fails under BF16; sequence MIS stable
but slow; FP32 inference fully stable at about 3x cost). KV4-RL (2610.14448) is the closest
design analog: a rollout-only cache-precision lever (INT4 KV) with token-TIS (C = 5) and a common
BF16 evaluator, where KV4 "fails to match BF16's later improvement" (5.24 pp on MATH-500 avg@8)
and KV8 tracks BF16; it names hybrid-attention models as untested. Score Centering (2609.20807)
shows IS-family corrections losing ground as mismatch grows, but deliberately at 512-1,024 tokens
and at 6,180 H100-h. The kill-shot's sharpest point: a "recombination" of the FP16 factorial with
KV4-RL's lever, unless the recurrent-state mechanism and the length effect carry the delta.

**4. The recurrent-state error is a coherent, length-accumulating bias.** Inference-side primary
sources agree: Nemotron 3 Super (2604.12374, first-party on its own model) finds an FP16
round-to-nearest Mamba-2 SSM cache raises completion tokens 36.95% at equal pass@1 and stochastic
rounding removes it; Nemotron 3 Ultra (2606.15007) ships FP16+SR; Olmo Hybrid (2604.03444)
recovers scores with an fp32 GDN cache; the 2026 state-quantization preprints (2610.15709,
2609.39185) attribute it to round-to-nearest losing small updates, worse with decode length;
climate numerics (Paxton et al. 2104.15076; Croci and Giles) rank fp32 above fp16 far above bf16
for long recurrent integrations. This program measured the same on Qwen3.5 (D108, D109): k3
18-21x fp32 for bf16 state, growing within sequences, and longer reasoning; fp16 about 2-3x fp32
with fp32-like lengths.

**5. What IS correction can and cannot do here.** Token-level truncated IS is IMPALA's "1-step
IS" (1802.01561, Table 2): adequate when the deviation is small, insufficient as it grows. It
reweights the action probability given the prefix but not the prefix (state-visitation)
distribution (Liu et al. 1810.12429). Sequence-level IS needs about exp(KL) samples (Chatterjee
and Diaconis 1511.01437). The synthesis's CPU re-analysis of the committed G2b/G2c data
(`compute/mismatch-by-cap.json`) makes this concrete at a 16K cap: the median absolute log
trajectory ratio is 2.4 nats for fp32, 4.8 for fp16 and 30 for bf16 (4B; 3.7, 3.6 and 44 on the
9B), so sequence IS is infeasible for bf16; a sequence mask calibrated to remove 12.5% of fp32
sequences would remove 96% of bf16 sequences (92% on the 9B), a degenerate correction; IcePop's
[0.5, 5] token band masks 0.08-0.10% of bf16 tokens, nearly a no-op; and only 0.023-0.030% of
bf16 tokens have a weight above 2, so token-TIS at C = 2 acts by reweighting, not clipping. The
PSIS k-hat of the pooled token weights at 16K is 0.19-0.55 in every arm and model (below 0.7). Token-TIS is the
one correction that is neither infeasible nor degenerate, so it is the correction arm.

**6. Practice pins fp32 without a measured comparison.** NeMo-RL's Nemotron-3 GRPO recipes set
`mamba_ssm_cache_dtype: float32` plus IS correction; TorchTitan RL's vLLM GDN generator forces
float32 because decode "otherwise rounds the state through bfloat16 after every token"; prime-rl
PR #3214 says parity needs an fp32 SSM cache. The miles Qwen3.8-27B guide (first-party) offers
bf16 state as a rollout lever "at a precision cost worth checking", and slime exposes it. By code
reading of vLLM v0.31.0 (not runtime-verified), Qwen3-Next rollouts default to a bf16 GDN state
because its checkpoints lack `mamba_ssm_dtype`, while Qwen3.5 and SGLang default to fp32.

**7. Statistics: three seeds cannot carry a learning endpoint.** First-party computation (cross
cell, reproduced in `compute/power-g2rl.json`): a paired t on 3 pairs detects only 3.26 SD (3.29 in the cross cell's own computation); no
rank test reaches p 0.05 at 3 vs 3 (minimum 0.10); interactions need about 16x the sample of a
main effect (Gelman, blog); non-significance is not equivalence (Lakens). Run-to-run chaos
(Summers and Dinneen 2103.04514; Henderson et al. 1709.06560) makes the fp32 between-seed spread
the null, never zero. Hence: the run is the unit; Welch on per-run summaries; equivalence by TOST
with a registered margin; recovery as one planned contrast gated on an effect, not a factorial
interaction; the gradient-level readout as the pilot's mechanism probe (Ilyas et al. 1811.02553).

**8. Assets and cost.** No RL infrastructure exists in this repository or under `legacy/`. verl
(Apache-2.0; v0.9.1 pins vLLM 0.24.0, main pins 0.29.0; the 0.30 bump PR #8072 is open) forwards
`rollout.engine_kwargs.vllm` to `vllm serve`, has a packed varlen Qwen3.5 trainer patch (the path
G2b measured exact), and has TIS/RS/IcePop/SC presets. Its open Qwen3.5 issues bear on numerics
(#8154 RoPE `inv_freq` rounding on our exact torch/CUDA; #6829 nonzero ppo_kl unless micro-batch
sizes match) and modes (#7438, one_step_off fails, so async is out). flash-attn has no torch 2.13
wheel. The lane runs `--network none` with a read-only root; Ray on loopback is untested. The
asset cell's step model: about 350 s per GRPO step (270-470) for 256 rollouts at 16K on 4 GPUs.
In RL the 16-bit state's throughput gain is expected to be 10% or less (the 1.33-1.38x is a
saturation figure; rollout is about 45% of a co-located iteration in KV4-RL), so wall-clock is
not an outcome that separates the arms.

## Claim and Research Question

**Question.** For Qwen3.5-4B (a Gated-DeltaNet hybrid, thinking mode) trained by GRPO in verl with
vLLM 0.31.0 rollouts at a 16,384-token response cap, with weights, activations, the trainer, the
data, the learning-rate schedule and the seeds held fixed, does the recurrent-state number format
of the rollout engine (`mamba_ssm_cache_dtype` float32, the default; float16; bfloat16):

1. change what the policy learns, measured on held-out prompts by a common fp32-state evaluator;
2. change length and truncation dynamics during training;
3. change stability (pre-defined collapse events);

and 4. does token-level truncated importance sampling (C = 2, decoupled from the PPO clip)
applied to bf16-state rollouts recover the fp32-state outcome?

**The pilot's question** (registration v1): at the start checkpoint, in verl's real training path,
does the manipulation hold (k3 ratio), how large is the bf16-induced policy-gradient bias relative
to the fp32 sampling noise, what share of it does token-TIS remove, and does the stack run,
checkpoint and resume in the lane at an affordable step cost?

**Variables.** State dtype (three levels); correction (none or token-TIS, crossed only with bf16).
Outcomes: held-out pass@1 AUC (primary learning), collapse events, in-loop k3 and its position
profile, response length and truncation share, training reward, own-dtype deployment accuracy;
in the pilot, the gradient-bias ratio kappa and the TIS recovery fraction r.

**Claim scope:** `systems-pipeline`: a training-stack configuration effect for one model size on
one host and software stack. It is not an architecture claim. Every number is "not externally
anchored" until replicated.

## Strategic Fit and Why Now

- D103 opened GPU memory and acceleration for inference and RL. D108 and D109 measured the
  manipulation (first-party, exploratory) and named this comparison as G2's next step, through
  the gauntlet because it exceeds 8 GPU-h.
- The practical question is live: a 16-bit state frees half the state memory and gives 1.33-1.38x
  saturation throughput on this node; frameworks expose it as an RL lever (miles, slime);
  production recipes pin fp32 without published evidence (NeMo-RL, TorchTitan); and by code
  reading the stock vLLM default for Qwen3-Next is bf16. Whether the fp32 pin matters for
  learning, whether fp16 is safe, and whether TIS makes bf16 safe are unmeasured.
- Why now: the two concurrent GDN-RL studies (TorchTitan blog, IsoExec) kept fp32 state and found
  nulls at the residual mismatch; KV4-RL (2026-10-10) names hybrids as its open limitation; Score
  Centering avoided long sequences. The long-CoT, position-accumulating regime is the open cell.
- Fit with the program's assets: the model and the per-token anchors (G2b's committed seed-42
  arrays, the host-kept r1/r2 outputs) are on the host; the lane, receipts and image pipeline
  exist; only the RL framework is new.

## Primary-Source Evidence

Read levels: F = full text read with `orx paper --full` by a discovery cell (F* also by the
synthesis owner); A = abstract or report only; R = repository, code, release or dataset record;
1P = first-party page, blog or issue (labelled, not replicated); M = this program's committed
measurement (exploratory, not registered). Every URL is snapshotted in the bundle.

| ID | Claim | Source | Date | Read |
|---|---|---|---|---|
| C01 | A bf16 linear-attention state in the inference engine accumulates error through the recurrence; RL reward improves as fixes are applied cumulatively, the state fix bundled with an fp32 LM head; no seeds or numbers; no algorithmic correction needed once aligned | https://arxiv.org/abs/2510.19338 | 2025-10-22 | F* |
| C02 | Qwen3.5-9B/35B-A3B-Base RL on TorchTitan + vLLM, always fp32 GDN state; bitwise parity (BI) vs default execution: abs-mean log-prob gap about 0.011 without BI and 0.009 with it (as reported), AIME2025 peaks about 0.57 and 0.53 with the no-BI arm finishing higher; no reward gain at window 4, on MoE or on Search-R1; mostly one seed; no TIS/MIS arm; BI costs 2-3x trainer throughput | https://yichuan-w.github.io/blog/GDN-train-inference-mismatch-asyncRL/ | 2026-08 | 1P |
| C03 | IsoExec: unified execution for Qwen3.5-9B and 35B-A3B, synchronous DAPO 50 steps on 8xH100, no meaningful reward gain, step time 1,224.6 to 1,534.0 s (+25.3%); state dtype not stated | https://vllm.ai/blog/2026-08-21-isoexec | 2026-08-21 | 1P |
| C04 | BF16 token-TIS prolongs training but fails; sequence MIS stable but slow (95% vs 99% train accuracy; AIME24 34% vs 39%); BF16 training with FP32 vLLM inference fully stable at about 3x cost; no hybrid model | https://arxiv.org/abs/2510.26788 | 2025-10-30 | F |
| C05 | INT4 KV rollouts with BF16 learner and token-TIS (C = 5) on Qwen3-4B/8B-Base at 16,384: KV4 fails to match BF16's later improvement (5.24 pp lower MATH-500 avg@8), KV8 tracks BF16; KV4 mean conditional KL 8.14e-3; 4B 600 updates in 19.80 h on 4 GPUs; rollout about 47% of iteration; hybrids a stated limitation | https://arxiv.org/abs/2610.14448 | 2026-10-10 | F |
| C06 | Score centering matches or beats IS-family methods under sampler quantization, gap growing with mismatch; sequences 512-1,024 tokens; 6,180 H100-h; TIS 51% vs SC 52% (FP8 W/A + FP4 KV) but 12% vs 30% (INT8 + INT4 KV) | https://arxiv.org/abs/2609.20807 | 2026-09-17 | F |
| C07 | FP16 round-to-nearest Mamba-2 SSM cache: LiveCodeBench completion tokens +36.95% (21,769 to 29,812) at pass@1 72.91 to 73.24; stochastic rounding -1.73%; FP32 default (first-party on its own model) | https://arxiv.org/abs/2604.12374 | 2026-04-14 | F |
| C08 | FP16 SSM cache with stochastic rounding preserves FP32 accuracy and verbosity | https://arxiv.org/abs/2606.15007 | 2026-06-12 | F |
| C09 | Post-trained GDN hybrid scores drop without enforce-eager; an fp32 GDN cache recovers them (repeated low-precision downcasting) | https://arxiv.org/abs/2604.03444 | 2026-04-03 | F |
| C10 | vLLM v0.31.0: Qwen3.5 copies the checkpoint's `mamba_ssm_dtype` (float32) when auto; Qwen3-Next has no hook and resolves to the model dtype (code reading, not runtime-verified) | https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/config.py | 2026-10-05 | R |
| C11 | SGLang FP16 SSM stochastic rounding (Mamba; Triton needs SM100); the GDN SR PR #27975 closed unmerged | https://github.com/sgl-project/sglang/pull/26929 | 2026-06-29 | R |
| C12 | TorchTitan RL forces a float32 GDN state in its vLLM generator | https://github.com/pytorch/torchtitan/blob/main/torchtitan/rl/generator/vllm/gdn.py | 2026-10-14 | R |
| C13 | NeMo-RL Nemotron-3 GRPO recipe: `mamba_ssm_cache_dtype: float32`, IS correction on, `seq_logprob_error_threshold` 2 | https://github.com/NVIDIA-NeMo/RL/blob/main/examples/nemo_gym/grpo_nanov3.yaml | 2026-10-13 | R |
| C14 | Nemotron-3-Nano GRPO with fp32 state still shows a large generation-trainer divergence (median gen_kl_error 0.0166; 60-71% of eligible sequences masked) | https://github.com/NVIDIA-NeMo/RL/issues/4243 | 2026-09-22 | 1P |
| C15 | miles guide: GDN state about 151 MB per in-flight sequence for Qwen3.8-27B; bf16 state offered as a rollout lever at a precision cost | https://github.com/radixark/miles/blob/main/docs/models/qwen/qwen3-8.md | 2026-08-18 | 1P |
| C16 | verl v0.9.1 (pins vLLM 0.24.0); rollout correction: token and sequence IS, rejection sampling, Geo-RS, IcePop, score-centering presets | https://github.com/verl-project/verl/releases/tag/v0.9.1 | 2026-09-20 | R |
| C17 | verl rollout-correction documentation (presets, decoupled and bypass modes, default threshold 2.0) | https://github.com/verl-project/verl/blob/main/docs/algo/rollout_corr.md | 2026-09-23 | R |
| C18 | verl's Qwen3.5 trainer patch calls FLA `chunk_gated_delta_rule` with `cu_seqlens` (the packed path G2b found exact) | https://github.com/verl-project/verl/blob/main/verl/models/transformers/qwen3_5.py | 2026-10-14 | R |
| C19 | verl: the FSDP bf16 cast rounds the RoPE `inv_freq` buffer and changes log-probs (verl 0.9.1, torch 2.13.0+cu129) | https://github.com/verl-project/verl/issues/8154 | 2026-10-08 | 1P |
| C20 | verl: ppo_kl nonzero on Qwen3.5-4B unless log-prob and update micro-batch sizes match | https://github.com/verl-project/verl/issues/6829 | 2026-06-23 (open) | 1P |
| C21 | verl: one_step_off fails with Qwen3.5 (async modes out) | https://github.com/verl-project/verl/issues/7438 | 2026-08-16 (open) | 1P |
| C22 | Small token-level numerical disagreements can independently cause collapse; combinations of TIS and rejection sampling can closely match a zero-mismatch reference (dense and MoE) | https://arxiv.org/abs/2605.14220 | 2026-05-14 | F |
| C23 | Dense Qwen3-4B: FP16 lowers train-rollout abs log-prob difference 0.0122 to 0.0016 with comparable final reward (first-party ablation) | https://arxiv.org/abs/2604.11554 | 2026-04-13 | F |
| C24 | Trust-region error bounds grow with horizon; sequence masking by maximum token divergence | https://arxiv.org/abs/2512.23075 | 2025-12-28 | F |
| C25 | Lightning-attention hybrid: probability mismatch prevented reward growth; fp32 LM head raised correlation 0.987 to 0.997 | https://arxiv.org/abs/2506.13585 | 2025-06-16 | F |
| C26 | KDA hybrid RL adds TIS against precision mismatch; no state-dtype analysis | https://arxiv.org/abs/2510.26692 | 2025-10-30 | F |
| C27 | IcePop masks tokens with training/inference probability ratio outside [0.5, 5] | https://arxiv.org/abs/2510.18855 | 2025-10-21 | F |
| C28 | Training-inference mismatch escalates with gradient noise; a learning-rate schedule controls it | https://arxiv.org/abs/2602.01826 | 2026-02-02 | A |
| C29 | Qwen3.6-35B-A3B AIME 2026: FP32 state 85.46, FP16 84.58, BF16 79.71 (inference) | https://arxiv.org/abs/2608.27513 | 2026-08-27 | F |
| C30 | Round-to-nearest discards updates below half a step; low-bit state error is coherent and grows with decode length (preprints) | https://arxiv.org/abs/2610.15709 | 2026-10-11 | F |
| C31 | Weyl dither beats stochastic rounding in 15/15 settings for quantized recurrent caches (preprint) | https://arxiv.org/abs/2609.39185 | 2026-09-30 | F |
| C32 | 1-step IS about equals V-trace at negligible lag; the gap widens as data become more off-policy | https://arxiv.org/abs/1802.01561 | 2018-02-05 | F |
| C33 | IS needs a sample size of about exp(KL) | https://arxiv.org/abs/1511.01437 | 2015-11-04 | F |
| C34 | PSIS: k-hat above 0.7 means unreliable IS | https://arxiv.org/abs/1507.02646 | 2015-07-09 | F |
| C35 | IS variance over long horizons; correct state-visitation ratios instead | https://arxiv.org/abs/1810.12429 | 2018-10-29 | F |
| C36 | Decoupled proximal and behaviour policies in PPO | https://arxiv.org/abs/2110.00641 | 2021-10-01 | F |
| C37 | Bootstrap tests at fewer than about 10 samples have about 10% false positives at 5%; prefer Welch; size from pilot SD | https://arxiv.org/abs/1806.08295 | 2018-07-05 | F |
| C38 | With 3 runs, bootstrap CIs undercover; stratified bootstrap needs many tasks | https://arxiv.org/abs/2108.13264 | 2021-08-30 | F |
| C39 | Two groups of 5 identical TRPO runs differ significantly (t = -9.09, p = 0.0016) | https://arxiv.org/abs/1709.06560 | 2017-09-19 | F |
| C40 | Any nondeterminism source, even one bit, decorrelates training runs | https://arxiv.org/abs/2103.04514 | 2021-03-08 | F |
| C41 | Policy-gradient estimates at standard batch sizes correlate poorly with the true gradient | https://arxiv.org/abs/1811.02553 | 2018-11-06 | F |
| C42 | Lorenz in BFloat16 with round-to-nearest collapses; Float16 periodic; stochastic rounding tracks; compare to a high-precision control ensemble | https://arxiv.org/abs/2104.15076 | 2021-04-30 | F |
| C43 | "Forgetting to Forget": bf16 round-to-nearest GDN state on Qwen3.5-0.8B; fp32 on selected heads removes 75.4% of excess NLL; inference only (dossier verifier) | https://openreview.net/forum?id=9LUInzhKZc | 2026-09-18 | UNVERIFIABLE_ACCESS |
| C44 | vLLM batch composition shifts log-probs up to 0.198 on Qwen3.6-35B-A3B | https://github.com/vllm-project/vllm/issues/59764 | 2026-10-02 | 1P |
| C45 | Qwen3.5-4B, Apache-2.0 | https://huggingface.co/Qwen/Qwen3.5-4B | 2026 | R |
| C46 | DAPO-Math-17k, Apache-2.0, 1,791,700 rows (each prompt about 100x) | https://huggingface.co/datasets/BytedTsinghua-SIA/DAPO-Math-17k | 2026-10-15 (read) | R |
| C47 | MATH-500 (held-out evaluation; no HF licence tag; the program records MIT) | https://huggingface.co/datasets/HuggingFaceH4/MATH-500 | 2026-10-15 (read) | R |
| C48 | AIME 2024 and 2025 compilations, Apache-2.0 (problems MAA copyright) | https://huggingface.co/datasets/math-ai/aime25 | 2026-10-15 (read) | R |
| C49 | vLLM's stochastic-rounding option is documented for the Mamba SSM cache only, Triton path on SM100 | https://docs.vllm.ai/en/stable/api/vllm/config/mamba/ | 2026-10-03 | R |
| M1 | fp32 GDN state: 49.1 MiB per sequence on Qwen3.5-4B/9B; vLLM allocates the checkpoint's float32 | `program/evidence/2026-10-14/inference-baseline/README.md` | 2026-10-14 | M |
| M2 | bf16 state: saturation throughput 1.33x (4B) and 1.38x (9B); mean abs mismatch 0.0077 to 0.0357 (4.6x) and 0.0074 to 0.0365 (4.9x); k3 18-21x; ratios outside [0.8, 1.25] 0.02-0.03% to 3.7-3.9%; within-sequence slope +1.3e-3 and +1.5e-3 per 1K; 9B cap hits at 32K 35/72 vs 7/72 (sign test p 2.0e-9); drift in vLLM decode, not prefill; packed varlen trainer exact | `program/evidence/2026-10-15/g2b-state-dtype/README.md` | 2026-10-15 | M |
| M3 | fp16 state at bf16's memory: mismatch 2.0x (4B) and 1.7x (9B) fp32, k3 3.3x and 2.5x, fp32-like lengths, 1.34-1.38x throughput; bf16 at fp32's block keeps bf16's drift (4B ratio 1.00 [0.99, 1.01]) | `program/evidence/2026-10-15/g2c-precision-vs-layout/README.md` | 2026-10-15 | M |
| M4 | fp32-state mismatch flat in position at fixed entropy to 11.5K (unpacked) | `program/evidence/2026-10-14/g2-pilot/README.md` | 2026-10-14 | M |
| M5 | At a 16,384 cap (committed seed-42 rows): k3 ratio to fp32 bf16 8.9 [7.7, 9.9] (4B) and 11.1 [9.9, 12.0] (9B), fp16 2.0 and 1.8; at 8,192: bf16 5.4 and 5.8; at 4,096: 3.1 and 3.3; cut share at 16K 54% fp32, 58% bf16; tokens with weight above 2: 0.023% and 0.030% (bf16); median abs log trajectory ratio 2.4/30/4.8 nats (fp32/bf16/fp16, 4B); fp32-calibrated sequence mask removes 96% (4B) and 92% (9B) of bf16 sequences | `compute/mismatch-by-cap.json` (this bundle) | 2026-10-15 | M |

## Closest Prior Work

1. **Ring-linear (Ling Team, arXiv 2510.19338, 2025-10-22). The closest prior.** It already states
   the qualitative mechanism (a bf16 linear-attention state in the rollout engine accumulates
   error and hurts RL) and shows reward curves that improve once it is fixed. It does not isolate
   the state (bundled with the fp32 LM head and later fixes), tests no fp16 or other 16-bit
   format, crosses no IS correction with the state fix, reports no seeds, numbers or intervals,
   and runs on an internal lightning-attention MoE stack. Its own conclusion is to align modules
   and use rollout probabilities, not to correct algorithmically.
2. **The TorchTitan GDN blog and IsoExec (first-party, August 2026). Closest concurrent.** Same
   model family and the same question family, but the manipulated lever is exactness (bitwise
   parity or unified execution) at the fp32-state residual mismatch; nulls on reward; mostly one
   seed; no IS arms; state precision never varied.
3. **KV4-RL (2610.14448) and the FP16 paper (2510.26788). The design template.** A rollout-only
   precision lever crossed with corrections, judged by an RL outcome and a common evaluator, on
   dense and MoE models. KV4-RL's lever (static per-token KV rounding) is closest; it found token
   TIS insufficient for INT4 and benign at INT8, and lists hybrids as untested.

Also adjacent: Score Centering (2609.20807; a correction class, short sequences); Nemotron 3
Super and Ultra, Olmo Hybrid, DAMP and the state-quantization preprints (inference only);
MiniMax-M1 and Kimi Linear (hybrid RL with other mismatch fixes); VeXact (identification by a
zero-mismatch reference); framework practice (NeMo-RL, TorchTitan, miles, slime).

## Novelty Ledger

| Proposed component | Closest prior | Same | Delta | Confidence |
|---|---|---|---|---|
| A 16-bit linear-attention recurrent state in the rollout engine changes hybrid RL | Ring-linear 2510.19338 | The qualitative claim and the accumulation mechanism | State dtype isolated (LM head, kernels, trainer, data fixed); an fp16 arm (at bf16's memory, 2x fp32's k3 instead of 9x); 5 seeds per arm; public model and stock engine; effect sizes with intervals; position-resolved in-loop mismatch in every run | medium |
| RL on Qwen3.5 GDN hybrids under a mismatch manipulation | TorchTitan GDN blog (1P); IsoExec (1P) | Model class; question family | They manipulate exactness at an fp32-state residual (abs gap about 0.004-0.011) with mostly one seed and no IS arm; this manipulates the state dtype (k3 9-11x fp32 at 16K, growing with position) with seeds and a TIS arm | high |
| Rollout precision x correction, judged by RL outcomes | FP16 paper 2510.26788 | The design pattern | Only the recurrent state's format changes (weights and activations stay bf16 on both sides); the error accumulates with position; a hybrid; corrections chosen by measured feasibility (sequence IS and masking shown infeasible or degenerate here) | medium (the refuters' recombination risk) |
| A rollout-only cache-precision lever with token-TIS and a common evaluator | KV4-RL 2610.14448 | The closest design analog | A recurrent, accumulating state instead of static KV rounding; hybrids (their stated limitation); seeds; length dynamics as an endpoint | medium-high |
| Does an IS-family correction recover a severe, length-growing mismatch | Score Centering 2609.20807; FP16 paper | Correction comparison under mismatch | The long-CoT regime both avoided or did not reach; the state-precision source; the gradient-level split of the bias into a token-ratio part (TIS-removable) and a prefix-shift part, measured from replicate batches against an A/A floor | medium |
| A 16-bit recurrent state changes generation length | Nemotron 3 Super 2604.12374; Forgetting to Forget (UNVERIFIABLE_ACCESS); this program's G2b | The behaviour effect at inference | Whether RL absorbs, amplifies or is harmed by it, under a common evaluator | high |
| Practice pins the state to fp32 | NeMo-RL recipes; TorchTitan RL | The practice | A measured training comparison, including whether fp16 is a safe middle | high |

Novelty wording: No direct prior art found through 2026-10-15 under the coverage in the header
(orx 0.2.2 alphaXiv and OpenAlex: 98 discover queries with the ids recorded in `query-log.json`,
71 full or targeted reads; 8 web searches; about 51 GitHub issue and code searches; OpenReview,
X, Notion blogs, Semantic Scholar, Chinese-language sources and patents not reached). Never
"completely novel".

## Mechanism and Falsifiable Predictions

**Mechanism (M).** vLLM's decode kernel updates each GDN layer's per-head state matrix once per
generated token and stores it in the configured format; the trainer recomputes the same tokens
with FLA's chunk kernel, which accumulates the state in fp32. With round-to-nearest, updates
smaller than half a unit in the last place are lost, so the error is a coherent bias that builds
up over decode steps rather than averaging out (C30, C42). The rollout policy mu therefore departs
from the trainer policy pi_old by an amount that grows with position: on Qwen3.5-4B, k3 is flat
for fp32, about 2x for fp16 and about 9x for bf16 within a 16K cap (M5), and bf16 rollouts reason
longer (M2). In GRPO with recomputed old log-probs, that departure enters as (i) a per-token
likelihood-ratio bias, which token-level IS removes in expectation, and (ii) a shifted prefix
(state-visitation) distribution, which no per-token weight removes (C35). M predicts that (ii)
carries most of the bias and that the behavioural shift (length) feeds into advantages, so that
bf16-state training learns differently from fp32-state training and token-TIS recovers only part
of the difference, while fp16, with about a fifth of bf16's excess, stays within an equivalence
margin of fp32.

**The rival account (R0).** GRPO with group-normalized advantages and a clipped objective is
robust to a mismatch of this size: the dense bf16 stacks at 0.0122 (C23) and the fp32-state GDN
residual (C02, C03) train to comparable rewards, so the bf16 state's extra bias is absorbed. R0
predicts every learning contrast inside the margin.

**Pilot predictions** (registration v1, section 7; fixed before data):

- PR1: in-loop k3 ratio bf16/fp32 about 9 (8.9 [7.7, 9.9] offline at 16K); **kill criterion**:
  below 2 stops the full design (trainer-side mismatch swamps the arms, K5); 2-4 is a fix (K4).
- PR2: bf16's within-sequence slope positive, fp32's flat (within ±2e-4 per 1K).
- PR3: under 0.1% of bf16 tokens have a weight above 2 (TIS acts by reweighting).
- PR4: the bf16 gradient bias kappa exceeds 0; tested by an exact permutation test over 4 + 4
  replicate batches (smallest attainable p 0.029); DETECTED at p ≤ 0.05.
- PR5 (the mechanism's sharpest falsifier at the gradient level): if PR4 is DETECTED, the TIS
  recovery fraction r_hat is at most 0.5. **Falsified if r_hat ≥ 0.8** (then most of the bias is
  the token ratio, which TIS removes, and M's prefix-shift account is wrong for this regime).
- PR6: bf16 in-loop length and truncation at least fp32's (estimation).

**Full-design predictions** (provisional; registered after the pilot):

- F1 (manipulation persists): run-mean in-loop k3 ratio B/F at least 4 in every seed pair.
  Below 2 in any pair: that pair is a manipulation failure, not evidence for R0.
- F2 (learning, Q1): held-out pass@1 AUC lower for B than F. M predicts CHANGES; R0 predicts
  NO_CHANGE_AT_MARGIN. **M is falsified for this setting if F1 holds, the B minus F AUC passes
  TOST within ±3 points, collapse counts differ by at most one, and run-mean length differs by
  under 5%.**
- F3 (behaviour): B's run-mean response length and truncation share above F's.
- F4 (recovery, Q2; run only if F2 reads CHANGES): M predicts PARTIAL (BT differs from B but is not
  equivalent to F). **Falsified if BT passes TOST against F within ±3 points.**
- F5 (dose, fp16): H passes TOST against F within ±3 points (estimation at 3 seeds).

## Cheapest Decisive Pilot

The pilot is the registration draft `program/preregistrations/g2rl-state-precision-rl-v1.md`.
It is decisive for the go, fix, re-size or stop decision on the full comparison, and it yields a
mechanism readout (PR4, PR5) on its own. It cannot decide whether learning changes.

| Job | What | GPUs x limit | Cap GPU-h |
|---|---|---|---:|
| P0a-c | CPU: hash-pinned fetch (D1), offline overlay build on the vLLM 0.31.0 overlay (verl pinned, Ray, FLA 0.5.2, Math-Verify; flash-attn from source or the torch varlen patch), selftests (the state-dtype setting reaches `vllm serve`; the gradient-dump hook) | 0 | 0 |
| P1 | Trainer anchor: verl FSDP2 `compute_log_prob` on G2b's 48 seed-42 4B rollouts against G2b's r1, r2 and decode log-probs; RoPE `inv_freq` dtype (verl #8154) | 1 x 15 min | 0.25 |
| P2a | Smoke: fp32 3 steps (checkpoint, saved batch), bf16 and fp16 2 steps each, 4K cap; engine-logged state dtype | 2 x 35 min | 1.17 |
| P2b | Fresh-job resume: replay the saved step-3 batch from the step-2 checkpoint, compare parameters with the uninterrupted step 3; SIGUSR1 save-on-signal | 2 x 15 min | 0.50 |
| P3a | fp32 calibration: learning rate 0, 4 replicate batches of the same 32 prompts x 8 at 16K (sampling seeds 42-45); in-loop log-probs; full-gradient dumps | 4 x 40 min | 2.67 |
| P3b | bf16 calibration: as P3a, plus a second backward with token-TIS weights on every batch | 4 x 50 min | 3.33 |
| P4 | CPU: mismatch tables, gradient Gram matrix, readouts; dumps deleted | 0 | 0 |
| | **Total** | | **7.92** |

Gates (registration section 7): G1 stack; G2 resume equivalence at the trainer level (identical
batch, identical update: rollouts themselves are not reproducible on stock vLLM, which is batch
variant); G3 the trainer forward within 0.004 of G2b's r2 and the decode gaps within 0.67-1.5x of
offline; G4 manipulation ratio at least 4; G5 the fp32 floor at most 0.0115; G6 step time at most
525 s. Kill criteria K1-K6 map each failure to stop, fix or re-size.

Why replicate batches at a learning rate of 0 rather than a few training steps: four training
steps per arm (the asset cell's calibration) measure step time and in-loop mismatch but say
nothing about the question; replicate batches on the same prompts measure the same quantities and
also the bias-to-noise ratio of the policy gradient (C41), A/A against A/B, with and without TIS,
which no prior reports for any rollout-precision lever. Why R = 4: at R = 3 the exact permutation
test cannot go below p 0.10 (`compute/power-g2rl.json`, GRAD block).

### The full comparison the pilot gates (proposed; registered separately)

- **Model and loop.** Qwen3.5-4B thinking; verl GRPO as in the registration's common settings;
  4 GPUs per run; 32 prompts x 8 per step; 16,384-token cap; 150 steps; learning rate 1e-6 with a
  10-step warm-up, identical in every arm (C28).
- **Stage 0** (about 7 GPU-h, cap 10): 1,536 de-duplicated DAPO-Math prompts x 8 fp32-state samples;
  the learnable pool is the prompts with pass rate in [1/8, 7/8]; a hash-seeded 256-prompt
  held-out split H; base-checkpoint evaluation; 13-gram decontamination against MATH-500 and AIME.
- **Stage 1** (core): F (fp32) and B (bf16), seeds 42-46, 10 runs. Central 634 GPU-h (490-856).
- **Stage 2** (only if Stage 1 reads CHANGES): BT (bf16 + token-TIS, C = 2) seeds 42-46, and
  H (fp16) seeds 42-44. Central 512 GPU-h (395-691).
- **Paths.** Null or no-change: about 642 GPU-h central (496-866). Changes: about 1,153 central
  (891-1,557). Proposed full cap 1,600 GPU-h, re-derived from P3's measured step before
  registration. Arithmetic: `compute/caps-g2rl.json`.

## Controls, Baselines, and Ablations

- **Baseline.** fp32 state is vLLM's default for Qwen3.5 and the production pin (C12, C13). Every
  arm sets the dtype explicitly and records the engine's resolved value.
- **Noise floor.** The fp32 arm's between-seed spread (5 runs) is the null for unpaired contrasts;
  in the pilot, the fp32 replicate batches (A/A) are the floor for the gradient readout (C39, C40,
  C42). Arms are never compared against zero difference.
- **Blocking.** Seed index fixes the initial checkpoint, data order and per-request sampling seeds
  across arms; the analysis is unpaired (Welch) because rollouts diverge after a few hundred tokens
  in any two arms (G2c: median 220 tokens on the 9B), with the paired-by-seed analysis as a
  sensitivity check.
- **Single-factor manipulation.** Only `mamba_ssm_cache_dtype` changes. Weights, activations, the
  convolution state, the LM head, the attention backend, the trainer (FSDP2, fp32 master weights,
  bf16 compute, packed varlen FLA chunk), the learning-rate schedule (C28) and the reward are
  identical. G2c showed the 16-bit block layout does not drive the drift.
- **Decoupled correction.** Every arm recomputes pi_old with the trainer and clips pi_theta/pi_old;
  the TIS arm differs only in the detached weight min(pi_old/mu, 2) (C36), verl's `RolloutCorrectionConfig.decoupled_token_is()` (`rollout_is: token`, `rollout_is_threshold: 2.0`, `bypass_mode: false`; C17). The no-correction arm
  is named exactly: PPO with recomputed old log-probs and IS weight 1.
- **Common evaluator.** Learning is judged by one fp32-state vLLM evaluator on fixed prompts and
  seeds for every checkpoint of every arm; each B/BT/H run's final checkpoint is also evaluated
  with its own state dtype (the deployment gap).
- **Manipulation check in every run.** In-loop k3, its position profile and the TIS weight
  statistics per step.
- **Excluded arms, with evidence.** Stochastic-rounding fp16 (not stock for GDN on SM90: C11, C49;
  writing the kernel is barred by the R570 rule). Sequence-level IS (infeasible: median abs log
  trajectory ratio 30-44 nats for bf16 at 16K; C33, M5). Sequence masking (degenerate: removes
  92-96% of bf16 sequences when calibrated on fp32; M5). IcePop (masks 0.08-0.10% of bf16 tokens;
  M5). Score centering (C06; verl implements it only in bypass mode with a REINFORCE loss, `score_centering` "bypass + reinforce only" in C17, so it would change the loss and the PPO anchor as well as the correction; a Stage 2b candidate with its own matched bypass baseline if TIS reads PARTIAL or NO_RECOVERY). A 4K-cap
  negative control (cost; replaced by length-bucketed analysis within runs, since the k3 ratio is
  3.1 at 4K against 8.9 at 16K). The 9B (cost). Batch-invariant decoding (not runnable for Qwen3.5
  on stock v0.31.0, dossier O3). Async modes (verl #7438).

## Evaluation, Statistics, and Leakage Checks

**Unit and endpoints (full design).** The unit is a training run. Primary learning endpoint:
per-run held-out pass@1 AUC (mean over the checkpoints at steps 50, 100 and 150, minus the shared
step-0 value), on H (256 prompts x 4 samples, temperature 1.0, 16K cap) under the common fp32-state
evaluator. Collapse (binary, per run): held-out pass@1 at any checkpoint 10 or more points below
step 0, or the 10-step moving training reward 0.15 or more below its running maximum, or a
non-finite loss. Behaviour: run-mean response length and truncation share of training rollouts;
the evaluator's truncation share at step 150 (did the learned policy itself get longer?).
Secondary: training reward, final-checkpoint pass@1, MATH-500 x1 and AIME 2024/2025 x8 under the
evaluator, own-dtype deployment accuracy, entropy, gradient norm, TIS weight statistics.
Per-step points are never treated as independent samples (C39).

**Tests.** Q1: Welch t on B minus F AUC, two-sided alpha 0.05; equivalence by TOST with a 3-point
margin (90% CI inside ±3); collapse by Fisher's exact test. Reading CHANGES (CI excludes 0 or
Fisher p ≤ 0.05), NO_CHANGE_AT_MARGIN (TOST passes and collapse counts within one), else
INCONCLUSIVE with the interval reported. Q2 is tested only after Q1 reads CHANGES (gatekeeping, so
no multiplicity adjustment is needed for the pair): RECOVERS if BT minus F passes TOST and BT minus
B excludes 0 toward F; PARTIAL if BT minus B excludes 0 but BT minus F does not pass TOST;
NO_RECOVERY if BT minus B includes 0. fp16 (H, 3 seeds) is estimated with its interval and not
tested. No bootstrap test at these sample sizes (C37, C38).

**Power and operating characteristics** (`compute/power-g2rl.json`, seeds 42-44; simulated
before any data). Minimum detectable effects at alpha 0.05 and power 0.8: paired t 3.26 SD at 3
pairs, 1.68 at 5; two-sample t d = 3.07 at 3 per arm, 2.02 at 5, 1.80 at 6; smallest two-sided
rank-test p 0.10 at 3 vs 3, 0.008 at 5 vs 5. The full design's Stage 1 rule at 5 runs per arm
(no extension; 6,000 simulated designs per row):

| Per-run SD (points) | True B minus F (points) | B collapse probability | CHANGES | NO_CHANGE_AT_MARGIN | INCONCLUSIVE |
|---:|---:|---:|---:|---:|---:|
| 1.5 | 0 | 0 | 0.04 | 0.67 | 0.29 |
| 1.5 | -2 | 0 | 0.40 | 0.17 | 0.43 |
| 1.5 | -4 | 0 | 0.86 | 0.00 | 0.14 |
| 2.0 | 0 | 0 | 0.04 | 0.34 | 0.62 |
| 2.0 | -2 | 0 | 0.23 | 0.12 | 0.64 |
| 2.0 | -4 | 0 | 0.69 | 0.01 | 0.31 |
| 2.0 | -6 | 0 | 0.88 | 0.00 | 0.12 |
| 2.0 | -2 | 0.75 | 0.78 | 0.00 | 0.22 |
| 3.0 | 0 | 0 | 0.04 | 0.06 | 0.90 |
| 3.0 | -4 | 0 | 0.39 | 0.01 | 0.60 |
| 3.0 | -6 | 0 | 0.69 | 0.00 | 0.31 |

So the false-CHANGES rate is 0.04; collapse-scale effects and shifts of 4 points or more are
found with probability 0.69-0.88 at an SD of 2; a 2-point effect is mostly INCONCLUSIVE; and
equivalence is established only if the per-run SD is near 1.5 (0.67) or 2 (0.34). Four runs per
arm with an extension to 6 (the cheaper variant) gives 0.58 and 0.27 at SD 2; five with an
extension to 8 gives 0.74 and 0.45 at about 7% more runs. The design takes 5 without extension
and says so: a null reading at this scale bounds the effect; it does not certify it. The per-run SD is
unknown (evaluator noise alone is about 0.9 points over three checkpoints of 1,024 samples;
seed-to-seed training spread is unmeasured on this stack); Stage 1 measures it, and the results
report the interval whatever the reading.

**Pilot readouts.** The manipulation gate (G4) under the offline truth: a prompt-cluster
bootstrap of 32 prompts per arm from G2b's sequences cut at 16K gives a k3 ratio of 7.7-10.3 (4B,
95% range) and 9.6-12.6 (9B); P(ratio below 4) is 0 in 6,000 draws; the ratio reaches 4 only if
verl's trainer adds 1.6 fp32 floors of k3 to both arms (4.6e-4 on the 4B), and 2 only at 6.9
floors. The gradient readout in a Gaussian model (4 batches per arm, bf16 noise 20% larger,
600 simulated pilots per cell):

| Noise dimension d_eff | True kappa | kappa_hat 5-95% | P(permutation p ≤ 0.05) |
|---:|---:|---|---:|
| 10 | 0 | -0.35 to 0.63 | 0.04 |
| 10 | 0.5 | 0.10 to 1.24 | 0.32 |
| 10 | 1.0 | 0.49 to 1.90 | 0.86 |
| 100 | 0 | -0.13 to 0.15 | 0.04 |
| 100 | 0.1 | -0.05 to 0.24 | 0.16 |
| 100 | 0.25 | 0.11 to 0.41 | 0.73 |
| 100 | 0.5 | 0.33 to 0.69 | 1.00 |
| 1000 | 0 | -0.04 to 0.05 | 0.04 |
| 1000 | 0.05 | 0.00 to 0.10 | 0.36 |
| 1000 | 0.1 | 0.05 to 0.15 | 0.91 |

With 3 batches per arm no split reaches p 0.05 (smallest attainable 0.10), which is why P3 runs
4. The test holds its size (0.04 under kappa = 0). The TIS recovery estimator is usable once the
bias is detected: at d_eff 100 and true r 0.5, r_hat's 10-90% range is 0.33-0.92 at kappa 0.25 and
0.39-0.65 at kappa 0.5; at d_eff 1000 it is 0.44-0.59 and 0.46-0.54. So PR5's two readings (r_hat
at most 0.5 against at least 0.8) are separable when kappa is about 0.5 or more at d_eff 100, or
0.25 or more at d_eff 1000, and the falsifier can fire wrongly about 10-15% of the time at the
edge of detectability (d_eff 100, kappa 0.25, true r 0.5). The noise dimension of a real 4B
policy gradient is unknown; the pilot bounds it only from below.

**Leakage and contamination.** H is disjoint from the training pool by prompt hash; training
prompts are 13-gram decontaminated against MATH-500 and AIME before Stage 1. Qwen3.5's exposure to
MATH and AIME is likely and unknown; it is shared by every arm and disclosed. The evaluator's
prompts and seeds are fixed before any training run. No evaluation output feeds back into
training or into the choice of checkpoints.

**Missing data and failures.** A run lost to infrastructure is resumed from its last checkpoint;
a run that cannot be resumed is repeated with the same seed and counted once; an arm-level
exclusion is never made on outcome values. Every run's per-step logs are reported.

## Compute and Reproducibility

- **Images.** Base `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f`
  (vLLM v0.31.0, commit db9527a4), through the program's digest-pinned cu129 overlay (the G2c
  overlay's local image id is `sha256:7f6d49d75fe5d6cefd3fc348129c48e141ab607118a55b7897a47df8bf988ff3`).
  The pilot builds a new overlay from a hash-pinned wheelhouse (verl at a pinned commit, Ray,
  flash-linear-attention 0.5.2, Math-Verify 0.8.0; flash-attn 2.8.3 from source or a reviewed
  torch `varlen_attn` patch). No such image exists yet; its digest is recorded at P0.
- **Launch.** `python3 scripts/submit_docker_research_job.py manifests/g2rl-p3a.yaml --dry-run` (one manifest per job: p1, p2a, p2b, p3a, p3b),
  then `--test-only`, then submit, which runs
  `sbatch infra/slurm/host-single-node/docker-research.sbatch` with Slurm GRES and the job's limit.
  The manifests are rendered before the freeze.
- **Seeds.** seeds: [42, 43, 44, 45] for the pilot's replicate batches (identical across arms);
  verl, torch, Ray and analysis seeds 42; the full design's training seeds 42-46.
- **GPU budget.** gpu_hours: 8 (the pilot's caps sum to 7.9167; expected physical use about 6.0).
  The full design's proposed cap is 1,600 GPU-h, re-derived from the pilot's measured step.
- **Checkpoints and preemption.** FSDP checkpoints every 25 steps in the full design (two kept);
  the lane's SIGUSR1 (180 s before the limit) triggers a wrapper that saves a checkpoint and a
  marker; a run longer than the 64 GPU-h per-job ceiling continues as a fresh job through the
  lane's resume contract. Rule 7's resume equivalence is defined at the trainer level (P2b).
- **Artifacts.** Lane receipts, engine logs with the resolved state dtype, per-step metrics,
  per-token in-loop log-probs (pilot), the gradient Gram matrix and its input hashes, evaluator
  outputs per checkpoint, configs; rollout texts for the pilot's prompts.
- **This bundle's CPU evidence.** `compute/mismatch_by_cap.py` and `mismatch-by-cap.json` (the
  committed G2b/G2c data re-read under caps); `compute/power_g2rl.py` and `power-g2rl.json`;
  `compute/caps_g2rl.py` and `caps-g2rl.json`.

## Safety, Data Rights, and Monitorability

- **Licences.** Qwen3.5-4B Apache-2.0; DAPO-Math-17k Apache-2.0; MATH-500 (no tag on the Hub; the
  program records MIT; evaluation only); AIME compilations Apache-2.0 or MIT, problems MAA
  copyright (evaluation only, not redistributed); verl, vLLM, Ray, Math-Verify Apache-2.0;
  flash-linear-attention MIT; flash-attn BSD-3-Clause.
- **Host rules.** No model-generated GPU code (R570): only stock libraries and reviewed Python
  hooks run on the GPUs; no custom kernels. Jobs use only free GPUs and never preempt the D110
  or AM1 work. No sudo; the operator never touches the host's protected checkout.
- **Public repository.** No host addresses, credentials or private data; trained checkpoints stay
  on the host and are not published.
- **Monitorability.** Every run logs the resolved state dtype, in-loop mismatch, TIS weights,
  lengths, rewards and gradient norms per step; the collapse rule is mechanical.
- **No outward action.** Nothing is posted, sent or published by this work.

## Negative-Result Value

- **A null in the full design** (F1 holds, NO_CHANGE_AT_MARGIN) tells practitioners that, for
  GRPO on a 4B GDN hybrid with 16K reasoning, the fp32 state pin buys nothing measurable within
  ±3 points, so the 16-bit state's memory and throughput can be taken; it bounds the effect with an
  interval, which the concurrent nulls (single seeds, fp32 residual) cannot.
- **A pilot stop** (K5: verl's trainer-side mismatch swamps the state contrast) is itself a
  finding about Qwen3.5 in verl's path, with G2b's anchors to localize it.
- **PR5 falsified** (TIS removes most of the gradient bias) says the off-policy effect of a
  recurrent-state rounding bias is token-local, and token-TIS is sufficient.
- **A gradient bias inside the A/A floor** bounds the per-step bias relative to sampling noise at
  batch 256, which predicts how many steps any training effect would need.

## Preflight Doctors

| Doctor | Status | Evidence | Remediation |
|---|---|---|---|
| Source | PASS | orx alphaXiv and OpenAlex reachable; 98 counted orx discover queries with returned ids in `query-log.json`; 8 web searches; about 51 GitHub searches; cutoff 2026-10-15; degraded coverage recorded (orx outdated; OpenReview, X and Notion unreachable; no citation graphs, Chinese-language sources or patents) (`doctors/source.json`) | Semantic Scholar citer refresh for 2510.19338 and 2610.14448 through the host relay; a browser read of 9LUInzhKZc |
| Citation | PASS | Claim registry C01-C49 and M1-M5 with URLs, dates and read levels; every primary URL snapshotted with HTTP status and body hash; 9LUInzhKZc UNVERIFIABLE_ACCESS; blogs, issues and first-party ablations labelled 1P (`doctors/citation.json`) | Replace 1P numbers when replicated; re-read C02/C03 figures directly |
| Novelty | FAIL | NARROWED by two independent cells; no direct prior under the recorded coverage; the blind critic and the novelty refuter have not run; 9LUInzhKZc unread (`doctors/novelty.json`) | Run the blind critic on `blind/` and the novelty refuter within the query budget the orchestrator rules on |
| Design | PASS | Self-assessed; the identification refuter has not run. Single-factor manipulation; A/A floor; decoupled correction; common evaluator; gates G1-G6 and kill criteria K1-K6; falsifiers PR1, PR5, F2, F4; simulated operating characteristics (`doctors/design.json`) | Identification refuter; pre-freeze audit of the registration |
| Compute | FAIL | No verl image, manifest, container smoke, Slurm dry run or test-only run exists; the deterministic doctor's real-model-loop and adapter checks fail; the pilot's caps (7.92 GPU-h) and the full design's arithmetic are in `compute/caps-g2rl.json` (`doctors/compute.json`, `compute/attestations-not-run.md`) | P0 build and selftests, manifests, dry runs and test-only runs before a freeze |
| Safety | PASS | Permissive licences; R570 respected (stock libraries and reviewed Python only); host and public-repository rules; no outward action (`doctors/safety.json`) | none |

Protocols followed: Citation, the ARS claim-verification protocol (claim registry, locators,
verdicts, UNVERIFIABLE_ACCESS); Design, the vendored K-Dense `experimental-design` and
`statistical-power` skills (design before data; seed blocking; sample size from a stated minimum
effect by simulation, not habit); Evaluation, K-Dense `statistical-analysis` (Welch, TOST,
Fisher, no small-n bootstrap tests); Novelty, K-Dense `literature-review` (PRISMA counts in the
header). The integrity gate's seven failure modes are answered in the registration's section 14.

## Independent Adversarial Reviews

Reviewer A: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the reviewers run after the blind critic and the refute-first triad)

Reviewer B: FAIL | provider=not-run | model=not-run | run_id=not-run | artifact=none (the open-weight reviewer's lane job runs only on an empty queue, limit 20 minutes)

No review is signed: no trusted Ed25519 store exists (D24).

## Scorecard

| Dimension | Reviewer A | Reviewer B | Defect/evidence |
|---|---:|---:|---|
| Question and strategic fit | 0 | 0 | not yet reviewed |
| Primary-source evidence | 0 | 0 | not yet reviewed |
| Defensible novelty delta | 0 | 0 | not yet reviewed; the recombination risk against 2510.26788 and 2610.14448 is open |
| Mechanism and falsifiability | 0 | 0 | not yet reviewed |
| Controls and causal identification | 0 | 0 | not yet reviewed |
| Evaluation and statistics | 0 | 0 | not yet reviewed; the per-run SD is unmeasured |
| Feasibility and information per GPU-hour | 0 | 0 | not yet reviewed; the full design is 640-1,150 GPU-h central |
| Reproducibility and artifact contract | 0 | 0 | not yet reviewed; no image or manifest exists |
| Safety, data rights, and monitorability | 0 | 0 | not yet reviewed |
| Independent adversarial review quality | 0 | 0 | not yet reviewed |
| **Total** | **0** | **0** | Lower total is authoritative; caps that bind until fixed: 79 (no executable pilot run), 89 (unsigned reviews, D24) |

## Iteration Log

| Wave | Score | Highest-impact defect | Change | Result |
|---:|---:|---|---|---|
| wave-1 synthesis (2026-10-15) | not scored | Three seeds cannot carry a learning endpoint; the state contrast in verl's path is unmeasured; sequence-level corrections are infeasible or degenerate at 16K (M5); the full design's cost | Pilot rebuilt around replicate batches at learning rate 0 with an A/A floor and a TIS gradient readout (R = 4 for a reachable permutation test); full design staged with 5 seeds per primary arm, Welch/TOST/Fisher rules and a conditional Stage 2; correction arms chosen from measured feasibility; query-budget convention flagged | awaiting the blind critic, the triad and the reviewers |
