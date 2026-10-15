# g2rl-state-precision-rl-v1: the pilot for "does the GDN recurrent-state precision of RL rollouts change GRPO training of a Gated-DeltaNet hybrid, and does token-level truncated importance sampling recover it?" (Qwen3.5-4B, verl, vLLM 0.31.0)

**Status: DRAFT. Not frozen, not admitted, no ledger row.** Drafted on 2026-10-15 by the single
owner of the G2-RL gauntlet's synthesis, on branch `gauntlet/g2rl-state-precision`, together with
the proposal `program/proposals/2026-10-15-g2rl-state-precision-rl.md`. The blind critic, the
refute-first triad and the two reviewers have not run. Nothing in this file has touched a GPU.
A freeze follows the checklist of section 15, by an operator who did not draft this file; a
material change after the freeze is a new experiment id.

Origin: D108 and D109 name an RL training comparison of fp32, fp16 and bf16 state as G2's next
step, through the gauntlet because it exceeds 8 GPU-h. This registration covers only the pilot
(at most 8 GPU-h of Slurm caps). The full training comparison is described in the proposal and
in section 16, and gets its own registration after this pilot answers.

## 1. Question

At the start checkpoint of GRPO on Qwen3.5-4B, in verl's real training path with vLLM 0.31.0
rollouts at a 16,384-token response cap:

1. **Manipulation.** Does the rollout engine's GDN recurrent-state dtype (`mamba_ssm_cache_dtype`
   float32 against bfloat16) reproduce, against verl's own trainer forward, the rollout-trainer
   mismatch contrast that G2b and G2c measured offline against HF+FLA?
2. **Gradient bias.** How large is the systematic difference between the full policy gradient
   estimated from bf16-state rollouts and from fp32-state rollouts, relative to the batch-to-batch
   sampling noise of the fp32 gradient?
3. **Correction.** What share of that bias does token-level truncated importance sampling (TIS,
   weight min(pi_old/mu, 2), decoupled from the PPO clip) remove when applied to the same bf16
   batches?
4. **Behaviour.** How do response length, truncation share and reward differ in-loop?
5. **Feasibility and cost.** Does the stack run, checkpoint and resume in the docker-research lane
   with each state dtype, and what does one step cost?

## 2. What it decides and what it does not

It decides whether the full training comparison (section 16) is run as designed, re-sized, or
stopped, and it supplies the inputs the full design's registration needs: the step time, the
in-loop manipulation strength, the length and truncation regime on the training data, and an
effect-size prior at the gradient level.

It does not decide whether state precision changes RL training. No learning happens in it (the
learning rate is 0 in P3). A gradient-level bias at step 0 is a mechanism readout, not a training
outcome. Every number is exploratory-confirmatory in the narrow sense of section 7: the gates and
predictions below are fixed before any data exist, and their readings are reported as registered.

## 3. Identity and pins

| Item | Pin |
|---|---|
| Model | Qwen3.5-4B (thinking, GDN hybrid), Apache-2.0, revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, host receipt `75ebfc53...` (the G2b/G2c revision); `config.json` `mamba_ssm_dtype: float32` |
| Rollout engine | vLLM 0.31.0 (commit `db9527a4`), from the program's digest-pinned cu129 overlay over `docker.io/vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` |
| RL framework | verl, a pinned commit: tag v0.9.1 (2026-09-20) or main `f724e7f2` (2026-10-15), chosen in P0 by which one imports and resolves against vLLM 0.31.0 and torch 2.13.0+cu129 without changing the vLLM install (`pip install --no-deps`); the chosen commit is recorded and pinned before the freeze |
| Other libraries | ray (pinned), flash-linear-attention 0.5.2 (MIT), Math-Verify 0.8.0 (Apache-2.0); attention through flash-attn 2.8.3 built from source in the image build, or, if that build fails, a reviewed patch to torch `varlen_attn` (the G2b r2 path), whichever P0 produces; the choice is pinned before the freeze |
| Images | a new overlay built offline from a hash-pinned wheelhouse fetched under D1 (`pip download --require-hashes`); its local image id and provenance receipt are recorded at P0 |
| Training data | BytedTsinghua-SIA/DAPO-Math-17k, Apache-2.0, revision `65877096c24f`, de-duplicated by exact prompt text (about 17.9K unique of 1,791,700 rows) |
| P3 prompt batch | 32 prompts drawn from the de-duplicated set with `numpy.random.default_rng(42).choice(N, 32, replace=False)` over the prompts sorted by SHA-256 of their text; the 32 ids are committed before any GPU job |
| P1 anchor data | G2b's 48 seed-42 Qwen3.5-4B rollouts (942,608 tokens): the token ids and decode log-probs (`tokens.npz`) and the teacher-forcing outputs r1 and r2 kept on the host under the hashes in `program/evidence/2026-10-15/g2b-state-dtype/analysis/SHA256SUMS-host.txt` |
| Code | the P0-P4 drivers, the gradient-dump hook and the analysis script, written before the freeze and pinned by SHA-256 in section 17 of the frozen file |

## 4. Design: jobs

All GPU jobs run in the docker-research lane through `scripts/submit_docker_research_job.py`
(dry run, test-only, then submit), digest-pinned image, Slurm GRES and time limits, lane receipts.
Jobs are submitted only when the GPUs they need are free and only after the operator records the
queue state; nothing preempts another workstream.

| Job | What | GPUs | Limit | Cap GPU-h |
|---|---|---:|---:|---:|
| P0a | CPU: hash-pinned wheel and source fetch (D1) | 0 | 60 min | 0 |
| P0b | CPU: offline overlay build; provenance receipt | 0 | 120 min | 0 |
| P0c | CPU: selftests: imports; verl's Hydra config resolves `actor_rollout_ref.rollout.engine_kwargs.vllm.mamba_ssm_cache_dtype` into the `vllm serve` argv for each dtype; the gradient-dump hook's unit test on a tiny CPU model | 0 | 20 min | 0 |
| P1 | Trainer anchor: verl's FSDP2 `compute_log_prob` (remove-padding, packed varlen) on G2b's 48 seed-42 4B rollouts; per-token log-probs compared with G2b's r1, r2 and both arms' decode log-probs; records the RoPE `inv_freq` dtype after FSDP wrapping (verl issue #8154) | 1 | 15 min | 0.2500 |
| P2a | Smoke: fp32 state, 3 GRPO steps (checkpoint after step 2; the step-3 rollout batch saved); bf16 and fp16 state, 2 steps each; 8 prompts x 4, 4,096-token cap; each engine's resolved state dtype read from its log | 2 | 35 min | 1.1667 |
| P2b | Resume: a fresh job loads P2a's step-2 checkpoint, replays the saved step-3 batch through the update, and compares every parameter with P2a's step-3 checkpoint; then waits for the lane's SIGUSR1 and checks that the wrapper writes a complete checkpoint and marker within 150 s | 2 | 15 min | 0.5000 |
| P3a | Calibration, fp32 state: learning rate 0; R = 4 replicate batches of the same 32 prompts x 8 samples (256 rollouts) at a 16,384-token cap, vLLM sampling seeds 42, 43, 44, 45; per-token rollout and recomputed log-probs; the full gradient of every batch dumped (fp32 shards, per rank) | 4 | 40 min | 2.6667 |
| P3b | Calibration, bf16 state: as P3a; on every batch a second backward with token-TIS weights min(exp(logp_old - logp_rollout), 2); both gradients dumped | 4 | 50 min | 3.3333 |
| P4 | CPU: in-loop mismatch tables, gradient Gram matrix (shard-wise dot products over the 12 dumps), readouts; then the dumps are deleted | 0 | 60 min | 0 |
| | **Total** | | | **7.9167** |

Arithmetic (also `program/proposals/evidence/2026-10-15-g2rl-state-precision-rl/compute/caps-g2rl.json`):
GPUs x limit / 60 per job; expected physical use 6.0 GPU-h. P3 per batch: generation 175 s +
old-log-prob recompute 42 s + backward 127 s + dump 30 s = 374 s (fp32), plus a second backward
and dump for bf16 = 531 s; start-up about 300 s; so 1,796 s and 2,424 s expected against limits of
2,400 s and 3,000 s. At the high step estimate (470 s generation-plus-overhead), P3a needs about
2,470 s and P3b about 3,350 s: P3b's fourth batch is then cut. **A P3 job cut before its fourth
batch reports R = 3 and its gradient test is not run (estimation only; at R = 3 the exact
permutation p cannot go below 0.10).**

Common GRPO settings (P2 and P3; the full design uses the same): verl GRPO, group size 8,
temperature 1.0, top-p 1.0, no top-k; reward 1 if Math-Verify judges the last boxed answer
equivalent to the reference, else 0; a truncated response gets 0; no overlong shaping, no KL
loss, no entropy bonus; token-mean loss aggregation; PPO clip 0.2 below and 0.28 above; one
optimizer step per batch (one mini-batch, so pi_theta equals pi_old at the update and the only
off-policy term is the engine mismatch); AdamW (0.9, 0.999, weight decay 0.01), gradient clip
1.0; FSDP2 with bf16 compute and fp32 master weights; log-prob and update micro-batch sizes
equal (verl issue #6829); old log-probs recomputed by the trainer (decoupled PPO); rollout
log-probs recorded (`calculate_log_probs`); `rollout_is` null (metrics only) except where TIS is
named. vLLM: `gpu_memory_utilization` 0.6 colocated with sleep mode, prefix caching off, CUDA
graphs on, `logprobs_mode` raw.

## 5. Arms and manipulation

| Arm | `mamba_ssm_cache_dtype` | Correction | Jobs |
|---|---|---|---|
| F | float32 (the checkpoint's `mamba_ssm_dtype`, set explicitly) | none (IS weight 1) | P2a, P2b, P3a |
| B | bfloat16 | none | P2a, P3b |
| BT | bfloat16 (the same batches as B) | token-TIS, C = 2, decoupled (verl `RolloutCorrectionConfig.decoupled_token_is()`: `rollout_is: token`, `rollout_is_threshold: 2.0`, `bypass_mode: false`) | P3b (second backward) |
| H | float16 | none | P2a only (the dtype path is exercised; no calibration) |

Only the state dtype changes between F, B and H: weights, activations, the convolution state
(bf16), the trainer, data, prompts and sampling seeds are identical. vLLM 0.31.0 halves the hybrid
block for 16-bit states (528 to 272 tokens); G2c showed the block layout does not drive the drift
on these models (4B ratio 1.00 [0.99, 1.01]).

## 6. Estimands

On the rollout's own tokens, d = logp_rollout - logp_old (verl's recomputed trainer log-prob);
the TIS weight is w = exp(-d).

- **E1, in-loop mismatch per arm** (P3, 4 x 256 rollouts): mean |d|, p99 |d|, k3 = mean of
  (w - 1) - log w, the share of w outside [0.8, 1.25], above 2 and below 0.5; by 1,024-position
  bin; the within-sequence slope of |d| on position (sequence fixed effects), with a 95% bootstrap
  over prompts (2,000 draws, seed 42).
- **E2, manipulation ratio:** k3(B) / k3(F) pooled over all tokens, bootstrap over the 32 prompts
  (shared by the arms).
- **E3, gradient bias** (P3): with g the flattened full gradient of one batch and
  D_XY the mean squared distance ||g_x - g_y||^2 over distinct batch pairs,
  ||b||^2_hat = D_FB - (D_FF + D_BB) / 2, kappa_hat = ||b||^2_hat / (D_FF / 2) (bias over the
  per-batch noise variance of F), and rho_hat = ||b||^2_hat / mean(g_F,i . g_F,j) (bias over
  the squared norm of the mean fp32 gradient, i != j).
- **E4, TIS recovery** (P3b): r_hat = 1 - ||b_T||^2_hat / ||b||^2_hat, with
  ||b_T||^2_hat = D_F,BT - (D_FF + D_BT,BT) / 2.
- **Intervals for E3 and E4:** a leave-one-batch-out jackknife (8 replicates: one batch dropped
  from F or from B and BT together), reported beside the simulated 5-95% band of section 8 at the
  measured noise dimension. The noise-dimension proxy is the participation ratio
  (sum of eigenvalues)^2 / (sum of squared eigenvalues) of the centred Gram matrix of the F
  batches, which is at most R - 1 = 3 and is reported only as a lower bound on d_eff.
- **E5, behaviour** (P3): mean response length, truncation share (cap hit) and reward per arm,
  paired by prompt (32 prompt means per arm).
- **E6, cost** (P2, P3): wall time per phase (generation, old-log-prob, backward, sync, dump),
  peak GPU memory per phase, vLLM block-pool use.
- **E7, trainer anchor** (P1): mean |verl - r2|, mean |verl - r1| per token; mean |decode - verl|
  per G2b arm.

## 7. Hypotheses, gates and decision rules

Gates decide what happens next; predictions are registered readings of the mechanism. Thresholds
are fixed here.

**Gates (feasibility and manipulation).**

| Gate | Rule | Reading |
|---|---|---|
| G1 stack | P0c passes; P2a completes every arm's steps with the engine log showing the requested state dtype for that arm | FAIL: K1 |
| G2 resume | P2b: every parameter of the resumed step 3 equals P2a's step 3 (max abs difference 0 in bf16 storage, or at most 1e-6 in fp32 master weights), and the SIGUSR1 checkpoint and marker are complete | FAIL: K2 |
| G3 anchor | P1: mean abs(verl - r2) ≤ 0.004 per token, and mean abs(decode - verl) between 0.67x and 1.5x of the offline value on these 48 rollouts for each arm (decode minus r1: fp32 0.0079, bf16 0.0346; `mismatch-by-cap.json`, no cap) | FAIL: K3 |
| G4 manipulation | E2 ≥ 4 | between 2 and 4: K4 (fix); below 2: K5 (stop) |
| G5 floor | F's in-loop mean abs(d) ≤ 0.0115 (1.5x G2b's 16K-capped 0.0078) | FAIL: K4 (fix) |
| G6 cost | measured P3a step time (generation + recompute + backward + sync, no dump) ≤ 525 s (1.5x the 350 s model) | FAIL: K6 (re-size) |

**Kill criteria and actions.**

- K1: the stack does not run in the lane after the fix budget (two P0 rebuilds, one repeat of
  P2a): STOP; report infeasibility with the failing component.
- K2: resume is not equivalent: no full run until the checkpoint path is fixed and P2b repeated.
- K3: verl's trainer forward departs from G2b's anchors: FIX (verl #8154 inv_freq dtype, #6829
  micro-batch sizes, attention backend), repeat P1 once; if still failing, the full design uses a
  trainer forward that passes P1, or stops.
- K4: manipulation compressed (E2 between 2 and 4) or fp32 floor inflated: FIX the trainer path as
  in K3 and repeat P3a and P3b once (a second pilot under a new id if it would exceed the caps).
- K5: E2 below 2 after the fix: STOP the full design as specified; report that in verl's path the
  state-dtype contrast is swamped by trainer-side mismatch.
- K6: re-size the full design before its registration (fewer steps, a 12,288 or 8,192 cap, or
  fewer arms), with the arithmetic redone on the measured step.

**Registered predictions (readings, not gates).**

- PR1 (manipulation, E2): about 9 (8.9 [7.7, 9.9] for G2b's MATH-500 L5 rollouts cut at 16K);
  lower if the DAPO batch's responses are shorter (5.4 at an 8K cut; 3.1 at 4K).
- PR2 (position, E1): bf16's within-sequence slope positive with a 95% interval above 0; fp32's
  interval includes 0 or lies within ±2e-4 per 1,000 tokens.
- PR3 (TIS clipping, E1): the share of bf16 tokens with w above 2 is below 0.1% (offline at 16K:
  0.023%), so TIS acts by reweighting, not by clipping.
- PR4 (gradient bias, E3): kappa_hat above 0. **Tested** only when both P3 jobs reach R = 4: one-sided
  exact permutation test over the 70 splits of the 8 batches (the statistic is symmetric under
  swapping the groups, so the smallest attainable p is 2/70 = 0.029); DETECTED if p ≤ 0.05.
- PR5 (mechanism, E4): if PR4 is DETECTED, **r_hat ≤ 0.5**: most of the bias that bf16 rollouts
  put into the policy gradient comes from the shifted prefix (state-visitation) distribution,
  which a per-token weight cannot remove. **Falsified if r_hat ≥ 0.8.** Between 0.5 and 0.8: not
  resolved. If PR4 is not DETECTED, r_hat is reported without a reading.
- PR6 (behaviour, E5): bf16 mean length and truncation share at least fp32's (offline at 16K:
  58% against 54% cut); estimation only, with paired-by-prompt 95% intervals.

**What goes forward to the full registration.** E6's measured step time; E1/E2 on the training
distribution; E5's truncation share (if fp32's exceeds 50%, the full design trains on the Stage 0
learnable pool, section 16); kappa_hat and r_hat with their simulated uncertainty as effect-size
priors, never as gates.

## 8. Operating characteristics (simulated before any data)

From `program/proposals/evidence/2026-10-15-g2rl-state-precision-rl/compute/power-g2rl.json`
(seeds 42, 43, 44; `power_g2rl.py --reps 2000 --grad-reps 200`) and `mismatch-by-cap.json`:

- **G4 under the offline truth.** A prompt-cluster bootstrap of 32 prompts per arm from G2b's
  seed-42 sequences cut at 16K gives E2 of 7.7-10.3 (4B, 95% range) and 9.6-12.6 (9B); E2 below 4
  occurred in none of 6,000 draws. E2 falls to 4 only if verl's trainer adds about 1.6 fp32
  floors of k3 to both arms (4.6e-4 on the 4B), and to 2 only at about 6.9 floors: G4 separates
  "manipulation intact" from "trainer noise dominates", and G5 catches the intermediate case. The
  DAPO batch's length distribution is not MATH-500 L5's; a shorter one lowers E2 toward 5.4 (8K
  cut) or 3.1 (4K cut), and G4 then reads a weaker manipulation, which is information, not a
  fault.
- **PR4 and PR5 in a Gaussian gradient model** (R batches per arm; noise of total variance
  sigma^2 over d_eff directions; bf16 noise 20% larger; a bias of squared norm kappa sigma^2;
  600 simulated pilots per cell). At R = 3 no split reaches p ≤ 0.05 (smallest p 0.10). At
  R = 4 the test holds its size (0.04 at kappa 0) and detects the bias with probability
  0.73 at kappa 0.25 and 1.00 at kappa 0.5 when d_eff = 100; 0.36 at kappa 0.05 and 0.91 at
  kappa 0.1 when d_eff = 1000; 0.32 at kappa 0.5 and 0.86 at kappa 1 when d_eff = 10. Given
  detection, r_hat's 10-90% range at a true r of 0.5 is 0.33-0.92 (d_eff 100, kappa 0.25),
  0.39-0.65 (d_eff 100, kappa 0.5) and 0.44-0.59 (d_eff 1000, kappa 0.25): PR5's readings are
  separable once kappa is about 0.5 at d_eff 100 or 0.25 at d_eff 1000, and the falsifier can
  fire wrongly about 10-15% of the time at the edge of detectability. d_eff is unknown and only
  bounded below by the pilot's proxy (section 6).
- **Minimum detectable effects** (alpha 0.05, power 0.8): paired t 3.26 SD at 3 pairs, 1.68 at 5;
  two-sample t d = 3.07 at 3 per arm, 2.02 at 5; smallest two-sided rank-test p 0.10 at 3 vs 3,
  0.029 at 4 vs 4, 0.008 at 5 vs 5. They are why the pilot tests no learning endpoint and why the
  full design uses 5 runs per arm (its operating characteristics are in the proposal).

## 9. Seeds

- P3 sampling seeds: replicate batch r uses vLLM per-request seed 1e6 x s + 100 x prompt + j with
  s = 42, 43, 44, 45 for r = 1-4, identical across arms (the arms differ in state dtype only).
- P2: data order seed 42; sampling seeds as P3 with s = 42.
- Analysis bootstraps: seed 42; the simulations: seeds 42, 43, 44.
- verl, torch and Ray seeds: 42 in every job. No unseeded randomness; GPU kernels are not
  bitwise deterministic across batch compositions (vLLM batch variance), which is why G2 compares
  trainer updates on replayed batches rather than rollouts.

## 10. Compute plan and caps

Total cap 7.9167 GPU-h (section 4), under the 8 GPU-h line of D22/D24. Jobs run sequentially on
free GPUs; with GPUs 0-3 held by other work until about 2026-10-20 (D110, AM1), P3a and P3b
need four free GPUs each. Storage: 12 gradient dumps of about 17 GB (about 204 GB) in the run
directory, deleted after P4 commits the Gram matrix and its hashes; checkpoints from P2 (about
52 GB each, at most 3) deleted after P2b.

## 11. Data and licences

| Asset | Licence | Use |
|---|---|---|
| Qwen3.5-4B | Apache-2.0 | policy |
| DAPO-Math-17k | Apache-2.0 | prompts (32 in P3; 8 in P2) |
| G2b rollouts (this program) | MIT (repository) | P1 anchor |
| verl, vLLM, Ray, Math-Verify | Apache-2.0 | software |
| flash-linear-attention | MIT | software |
| flash-attn | BSD-3-Clause | software (if built) |

No data leave the host except the committed tables, hashes and summaries. Rollout texts committed
for P3 are the 32 prompts' samples (DAPO-derived, Apache-2.0).

## 12. Infrastructure failures and exclusions

- A job that fails before producing its first batch is an infrastructure failure: it is
  repeated once with the same manifest; a second failure reads K1.
- A P3 job cut by its limit keeps every completed batch; R is the number of completed batches.
- A rollout with a non-finite log-prob is excluded from E1 and counted; more than 1% non-finite
  tokens in any arm reads K3 (fix).
- No batch, prompt or rollout is excluded for its value.

## 13. Reported regardless of outcome

Every gate's reading with its numbers; E1-E7 in full; the job table with physical GPU-h;
the failing component if K1-K5 fire; the gradient readouts with their simulated uncertainty
and the d_eff proxy; every deviation from this file.

## 14. Integrity gate (the seven AI-research failure modes)

1. Implementation bug passing self-review: P0c's hook test, P1's anchors against G2b's
   independent HF+FLA outputs, and P2b's parameter-equality check; a fresh checker reviews the
   drivers before the freeze.
2. Hallucinated citation: every source in the proposal is snapshotted with its HTTP status
   and body hash; inaccessible ones are UNVERIFIABLE_ACCESS.
3. Hallucinated experimental result: every number comes from a committed file whose hash is in
   the evidence; the pilot's receipts are lane receipts.
4. Shortcut reliance: G3 and G5 stop a stack whose trainer noise would make any arm contrast
   uninterpretable.
5. Bug reframed as insight: K3 reads a trainer departure as a FIX, not as a finding.
6. Methodology fabrication: the jobs, limits and thresholds are fixed here before any data.
7. Frame-lock: the pilot can stop the full design (K5), and the proposal states the null's value.

## 15. Freeze checklist

- [ ] P0 fetch list with hashes; overlay recipe reviewed; R570: no model-generated GPU code
      (stock libraries and reviewed Python only)
- [ ] drivers, hook and analysis code committed with tests passing on CPU against fakes
- [ ] manifests for P1, P2a, P2b, P3a, P3b rendered; dry runs and test-only runs recorded
- [ ] the 32 P3 prompt ids and the 8 P2 prompt ids committed
- [ ] verl commit and attention path pinned
- [ ] the gauntlet's reviews recorded, and Kevin's admission ruling if the gauntlet ends below 100
      (D24, D92)

## 16. Consequences for the full design (provisional; registered separately)

The full comparison (proposal, "Cheapest Decisive Pilot" and "Evaluation, Statistics, and
Leakage Checks"): Qwen3.5-4B, 4 GPUs per run, 256 rollouts per step at 16K, 150 steps, learning
rate 1e-6; Stage 0 builds a learnable pool from DAPO-Math (pass rate in [1/8, 7/8] over 8 fp32
samples) and a held-out split; Stage 1 trains F and B with 5 seeds each (42-46); Stage 2 (only if
Stage 1 reads CHANGES) trains BT with 5 seeds and H with 3. Primary learning endpoint: per-run
held-out pass@1 AUC at steps 50, 100, 150 under a common fp32-state evaluator; Welch with a 3-point
equivalence margin; collapse by Fisher exact; manipulation and behaviour endpoints in every run.
This pilot can change that design only through G6/K6 (re-size), K3-K5 (trainer path), and E5
(the learnable-pool rule).
