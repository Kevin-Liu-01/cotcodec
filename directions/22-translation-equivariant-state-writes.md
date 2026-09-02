# Direction 22: Translation-Equivariant State Writes

**Status:** DRAFT on 2026-09-01 — wave-5 repair applied (executable phase-0 CPU doctor registered as `reference_doctor` and passed on synthetic inputs; simulation-derived phase-1 decision rule; receipted `qwen3.5-4b-base` substrate; rebuilt fla image cited); frozen within-model kill screen must pass before any from-scratch run; not pilot-ready (no container smoke, manifest or dry run; no signed reviews)
**Priority:** rerun the CPU object doctor inside the pilot container, then the 3.4 GPU-h frozen screen on the receipted `qwen3.5-4b-base`, then the 1.2 GPU-h selection/floor-gate stage, before the 11.4 GPU-h 57M grid
**Phase-0 doctor:** `uv run python scripts/run_translation_equivariant_state_writes_doctor.py --output data/results/translation-equivariant-state-writes/phase0-doctor.json` (harness `harness/translation_equivariant_state_writes.py`; tests `tests/test_translation_equivariant_state_writes_doctor.py`; last run 2026-09-01: PASS, 11/11 gates, 0.4 s, synthetic-case numbers only)
**Experiment contract:** `experiments/architectures/translation-equivariant-state-writes.yaml`
**Proposal:** `research/proposals/2026-09-01-translation-equivariant-state-writes.md`

## Research question

Does a fixed-size recurrent state store meaning or surface? Two translations of
the same span, behind a bitwise-identical prefix, should produce the same
**write** into a Gated DeltaNet head if the state stores meaning. Phase 0 asks,
on a frozen registered 2026 GDN hybrid and within that model, whether the state
carries cross-lingual recall at all, whether the cross-lingual gap is a
storage-format effect rather than readout interference, whether a training-free
linear transport already closes it, and whether the write is even numerically
distinct from the projections that feed it on sentence-length spans. Phase 1
asks whether supervising the write on public bitext closes the gap in 57M
from-scratch hybrids and beats the same loss on the projections — *given* that
the 57M instrument is above floor (gate G1) and the write and its pooling are
distinct (gate G2).

The wave-2 version supervised the raw segment delta `D = S(c⊕a) − S(c)`. Both
wave-2 judges showed `D` contains a content-independent prefix term shared by
every translation pair, so the loss could be satisfied without equivariance.
Wave 3 supervised the pure write instead. The wave-3 judges then showed that a
57M/200M-token grid with every arm at floor would be unreadable, that the
decisive control could equal the treatment for short spans, that no phase-0
kill had a runnable registered arm, and that the launch line targeted a file the
submitter does not consume. Wave 4 fixed those four things. The wave-4 judges
then showed that every phase-0 object and gate was still prose (no code existed
for `W`, the fp64 identity, the TP-MQAR-v2 builder or the leakage controls) and
that the phase-1 promotion rule passed a true 5-point effect only 12.5% of the
time. Wave 5 makes the doctor executable code and re-derives the rule by
simulation.

## Mechanism

Per layer and head the fla recurrence is `S_t = S_{t−1} α_t (I − β_t k_t k_tᵀ) + β_t v_t k_tᵀ`
(written `v kᵀ`; fla and the Qwen3.5/Olmo modules store the transpose). It is
affine in the state, so for a span `a` after prefix `c`:

```text
S(c⊕a) = S(c) · ∏_t α_t (I − β_t k_t k_tᵀ)                       # prefix carry (decay + erase)
       + Σ_t β_t v_t k_tᵀ · ∏_{s>t} α_s (I − β_s k_s k_sᵀ)          # pure write W(a|c)

W(a|c) := S(c⊕a) − S_{v=0}(c,a)     # second chunk_gated_delta_rule pass from S(c) with v ≡ 0
                                    # equals the state from S_0 = 0 with the same projections

P(a)   := Σ_t β_t v_t k_tᵀ          # A2 control: decay-free, erase-free, no recurrence
G2     : mean_{(l,h)∈E} cos(vec W, vec P) ≤ 0.9   # else A1 − A2 is a null by construction

L = L_LM + λ_arm [ mean_{(l,h)∈E} (1 − cos(W^A, W^B))
                 − log exp(s(W^A, W^B)/τ) / Σ_{B'} exp(s(W^A, W^{B'})/τ) ]

negatives B': ≥2 same-prefix random language-B sentences + ≥2 same-prefix
entity/number-sharing hard negatives (all behind the identical c), plus in-batch extras
τ = 0.07, λ_arm ∈ {0.1, 0.3} selected per arm (A1, A2, A3) on a dev TP-MQAR-v2 from FLORES+ dev
E = half the heads of every GDN layer

A3 placebo: same loss, content-independent same-prefix language-B sentence, own λ
```

Phase-1 hybrids use sliding-window attention (window 512) so a fact placed more
than 512 tokens before the query is recalled only through the state. The
instrument is TP-MQAR-v2: N facts of the form "key sentence in language A, separator, 4-digit code",
query in language B, digit-only exact match, surface-disjoint keys (token and
subword filters) as the primary subset, N in {8, 32, 128}. Chance is 1e-4, so
the gates use absolute EM.

Why a span-write loss should move recall at all (reasoning, not evidence): every
GDN layer emits `S_t q_t` into the residual stream, so the key projected at the
digit-code positions and the query projected at `sep_B` in later layers are
functions of the state the key sentence left behind; aligning `W(key_A|c)` with
`W(key_B|c)` moves those downstream vectors closer. A pre-registered mediation
diagnostic logs the cross-language cosines of the code-position key and the
query-position query per layer for A0, A1, A2.

## Closest work and delta

| Prior | What it occupies | Delta here |
|---|---|---|
| Arivazhagan et al. [1903.07091](https://arxiv.org/abs/1903.07091); Pham et al. [1906.08584](https://arxiv.org/abs/1906.08584) | auxiliary losses making NMT encoder representations language-invariant for zero-shot translation (2019) | the loss form's ancestor; here the object is a recurrent-state write inside a decoder-only hybrid behind a shared prefix, with a recall endpoint the loss never sees |
| Gated DeltaNet-2 [2605.22791](https://arxiv.org/abs/2605.22791) | channel-wise erase and write gates as architecture (2026-05) | makes the write a first-class object but neither supervises it nor studies language; the natural next substrate |
| WriteSAE [2605.12770](https://arxiv.org/abs/2605.12770) | post-hoc write interventions and rank-1 write atoms on GDN/Mamba-2/RWKV-7 caches | interventions are applied to a cross-lingual recall question with a matched perturbation control; the write is also supervised |
| Cross-lingual alignment without joint training [2608.27115](https://arxiv.org/abs/2608.27115) | bitext-fitted Procrustes rotation between monolingual transformers, patched into residuals | the recurrent within-model analogue is a pre-registered kill gate (rank-capped transport), not a contribution |
| MLNeedle [2408.10151](https://arxiv.org/abs/2408.10151), OneRuler [2503.01996](https://arxiv.org/abs/2503.01996) | cross-lingual needle retrieval on dense models | recall framing, key x query language matrix, state interventions, hybrid substrate, instrument-sensitivity gate |
| Token-level Olmo pair comparison [2606.20936](https://arxiv.org/abs/2606.20936) | the Olmo Hybrid/Olmo 3 pair as a monolingual matched instrument | cross-lingual axis; the pair is used descriptively only (see confounds) |
| Gather-and-Aggregate [2504.18574](https://arxiv.org/abs/2504.18574), Attention Amnesia [2606.11052](https://arxiv.org/abs/2606.11052) | hybrid recall lives in few softmax heads | motivates D-zero and the SWA-512 design |
| GI-SAE [2608.23809](https://arxiv.org/abs/2608.23809) | functional-swap criterion | applied to writes; secondary endpoint because it is monotone in the trained cosine |
| Leino & Tiedemann [2603.29026](https://arxiv.org/abs/2603.29026); Middle-Layer Alignment [2502.14830](https://arxiv.org/abs/2502.14830) | bitext exposure and residual alignment in transformers | live A5/A0 contrast; object is the write, not the residual |
| Multilingual SSM evaluations [2607.01502](https://arxiv.org/abs/2607.01502), [2502.01673](https://arxiv.org/abs/2502.01673) (title-only) | multilingual ASR / QA with Mamba-family models | task-level; no state-level or cross-lingual recall analysis visible from the titles |
| Olmo Hybrid [2604.03444](https://arxiv.org/abs/2604.03444); Qwen3.5-4B | the substrates | no cross-lingual or state-level analysis |

No direct prior art found through 2026-09-01 under the arXiv, Hugging Face
papers, OpenReview (titles unresolved) and bookmark coverage recorded in the
proposal, now including a wave-4 search whose query strings name the write, the
delta rule and translation together (53 records title-screened, 5 abstracts
opened, 0 occupying). The loss form is standard; the object and the instrument
are the delta. Collision risk for the instrument half is medium.

## Phase-0 substrates

- **Registered and receipted, primary (wave 5):** `qwen3.5-4b-base` = `Qwen/Qwen3.5-4B-Base` revision `1001bb4d826a52d1f399e183466143f4da7b741b` (Apache-2.0; registered 2026-09-01; receipt `data/model-receipts/qwen3.5-4b-base.json`, `artifact_root_sha256 c7fbfd6b…`, 9.34 GB, host copy under `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/`). Its post-trained sibling `Qwen/Qwen3.5-4B` (revision `851bf6e8…`, config fetched 2026-09-01) has 32 layers, 24 `linear_attention` (GDN) + 8 `full_attention` at 3, 7, ..., 31 — the same layout as Olmo Hybrid — hidden 2560, linear key heads 16 × 128, value heads 32 × 128, conv kernel 4; the base checkpoint is assumed to share that layout until its own config.json is read in the container smoke. The transformers `qwen3_5` module reads `cache_params.layers[i].recurrent_states[0]` and passes `initial_state` to the chunked gated delta rule, so `S(c)`, `S(c⊕a)` and `S_{v=0}(c,a)` are all reachable without custom code. Moving to the base checkpoint removes the post-training confound of wave 4; remaining confounds: a multimodal wrapper used text-only and no architecture-matched dense sibling. The phase-0 manifest is compiled from `infra/slurm/host-single-node/qwen35-4b-competence-screen.yaml` with the base receipt substituted.
- **Registered dense floor:** `qwen3-0.6b-base` supplies the dense cross-lingual EM floor (≥ 40% at N = 8 proves the instrument solvable; failing at 0.6B is inconclusive) and the descriptive P0a comparison.
- **Registered replication pair, receipts pending:** `olmo-hybrid-7b` = `allenai/Olmo-Hybrid-7B` revision `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` and `olmo-3-1025-7b` = `allenai/Olmo-3-1025-7B` revision `a81bae42db3975be1671e27b9c9a56da1a9f980f` (Apache-2.0; registered 2026-09-01 with blocker "no artifact receipt yet"). Ai2 describes the pair as **throughput-matched**, not architecture-matched: different data mixes, stage-1 tokens (5.50T vs 5.93T), LR schedules, widths (3840/30 heads vs 4096/32), stage-2 merging, and NoPE vs RoPE+YaRN in the shared attention layers (configs re-fetched 2026-09-01). The pair is a descriptive reference and, once its receipts exist, the replication substrate; no kill depends on the hybrid-minus-dense difference. The receipted GDN 3:1 hybrids `gdn-340m-isp-hybrid-3to1-10b` and `gdn-1.3b-isp-hybrid-3to1-50b` are candidate instrument-only extensions, not budgeted.

## Cheapest decisive pilot

1. **CPU object doctor (0 GPU-h) — executable since wave 5.**
   `uv run python scripts/run_translation_equivariant_state_writes_doctor.py --output data/results/translation-equivariant-state-writes/phase0-doctor.json`
   (NumPy/SciPy only, 0.4 s; 16 pytest tests incl. a tampered counterfactual). Registered as
   `reference_doctor` in the contract; run once on 2026-09-01: `PHASE0_OBJECT_DOCTOR_PASS`, 11/11
   gates, payload `e94aefff…`, reproduced bitwise twice. As code: the GDN head recurrence; `W`,
   `D`, `P`, `S_{v=0}`; fp64 identity `S_{S0=0}(a) == S(c⊕a) − S_{v=0}(c,a)` on a seeded 2-layer
   NumPy GDN (residual 1.2e-15); bitwise-identical `S(c)` across a pair with a perturbed prefix
   detected; prefix-floor ledger for `W`/`D`/`P` on 24 synthetic translation pairs (positive
   control passes 4/4 heads, shuffled pairing rejected 0/4); the write-shrinkage counterfactual
   (`D`'s non-translation floor 0.34 → 0.89 while `W` is exactly invariant; the `||W||` falsifier
   fires); causality perturbation; G2 `cos(W, P)` with an α × β regime sweep (> 0.9 whenever
   per-token decay is slower than ≈ 0.05 at 30-token spans on random projections — a live risk,
   not a formality); synthetic TP-MQAR-v2 with retrieval-impossible and value-permutation
   controls at chance under an oracle reader and a sealed manifest hash; the surface-disjoint
   filter (tokenizer-free stand-in); the promotion-rule simulation; degenerate-input rejection.
   **All numbers are synthetic-case numbers** (evidence grade executability-and-gate-semantics-only).
   Still pending: TP-MQAR-v2 from FLORES+ devtest/dev text with the subword filter under both
   tokenizers, the negative sampler, the fla cross-check (skipped without CUDA), dedup, the
   selection-ledger format, and `cos(W, P)` on the 57M A0 at init (model definition absent).
2. **Frozen within-model kill screen (3.4 GPU-h incl. reserve, 2 GPUs) on `qwen3.5-4b-base`.** 9 language
   cells x N in {8, 32, 128} x 100 prompts on surface-disjoint keys plus surface-shared keys at N = 8;
   `qwen3-0.6b-base` at N = 8 only; D-zero on the fact span vs D-zero on an equal-length distractor
   span; rank-capped (r ≤ 64) dual-form transport fitted on 997 FLORES+ dev pairs x 8 prefixes
   with identity and random-rotation controls; swap; prefix-floor table for `W` and `D`;
   distinctness table `cos(W, P)` per E head. Gates: hybrid monolingual EM ≥ 60% at N = 8 per
   language pair; dense floor ≥ 40% (P0c provisional if the 0.6B floor fails); `cos(W, P)` ≤ 0.9.
3. **Selection and floor-gate stage (1.2 GPU-h net incl. reserve).** Seed 42, 200M-token schedule
   truncated at 60M: A0 LR sweep (4 values), λ ∈ {0.1, 0.3} for each of A1, A2, A3 on the dev
   TP-MQAR-v2, A4 seed 42 to 60M. Gate G1 on the sealed test at N = 8, surface-disjoint,
   beyond-window: A0 monolingual EM ≥ 60% and cross-lingual EM ≥ 15%, or dense A4 ≥ 25%
   (rescue); `cos(W, P)` ≤ 0.9 on the 57M A0 at init and 60M (G2); smoke throughput
   ≥ 90K tok/s/GPU. Winners resume from their 60M checkpoints as the seed-42 grid runs
   (licensed by the fresh-job resume-equivalence test). On G1 failure phase 1 is deferred and
   revised under a new versioned contract; on G2 failure the treatment/control pair is redesigned.
4. **57M from-scratch grid (11.4 GPU-h ceiling incl. reserve).** A0 seed 42 runs to 200M first and
   G1 is re-read; then A0 baseline, A1 write equivariance, A2 projection alignment, A3
   language-marginal placebo, A4 dense, A5 no-bitext, each x 3 seeds at 200M tokens (75%
   monolingual, 20% prefix-sharing bitext, 5% same-language recall curriculum); conditional A4′
   (dense + A2's loss) only if the smoke run measures ≥ 200K tok/s/GPU. Primary endpoint: A1 − A2
   in EM points on surface-disjoint beyond-window keys at N = 8. **Decision rule (wave 5,
   simulation-derived):** promote if the seed mean ≥ 5 with all 3 pairs positive and the pooled
   prompt-clustered 95% CI excluding 0; kill if any pair is negative or the mean is negative;
   otherwise underpowered → +2-seed line under a new contract. Floor-compressed (no inference)
   if A1 and A2 are both below 10% in every seed.

Planned total 15.9 GPU-h under a 16 GPU-h ceiling (stage ceilings 3.4 + 1.2 + 11.4 = 16.0).
Three seeds are a kill screen. Simulated operating characteristics under a seed SD of 3
(doctor, 200k draws): the wave-5 rule promotes 0.002 / 0.121 / 0.490 / 0.952 / 0.997 and
kills 0.875 / 0.404 / 0.137 / 0.012 / 0.001 at a true effect of 0 / 3 / 5 / 8 / 10 EM points;
the retired wave-4 every-pair rule promoted a true 5-point effect 0.125 of the time.

## Controls

- A2 same-layer projection alignment (decisive; identical loss, τ, same-prefix negatives, heads, pooling shape; own λ; no recurrence; interpretable only under G2).
- A3 language-marginal placebo (own λ; reads out language-ID removal on the write).
- A4 iso-parameter dense transformer (descriptive; G1 rescue read); A5 iso-token no-bitext hybrid; A0 λ = 0 baseline (LR sweep; G1 reads).
- G1 instrument-sensitivity gate and G2 distinctness floor, both in the contract's promotion gates and falsifiers.
- Per-arm λ selection and A0 LR selection on FLORES+ dev only; selection ledger released; every pre-grid sealed-test read enumerated.
- D-zero with a matched distractor-span perturbation; rank-capped transport with identity and rotation controls; swap on never-trained prefixes.
- Surface-disjoint vs surface-shared keys with token and subword filters; entity/number hard negatives; digit-only EM; retrieval-impossible and value-permutation controls.
- Published baselines: MLNeedle, OneRuler, WriteSAE, 2608.27115, Arivazhagan/Pham for the loss form; QED (2608.13668), MARCH and SWA+sinks (2608.28444) become mandatory only if a recall-improvement claim is made.

## Falsifiers

- D-zero on the fact span exceeds its matched perturbation by ≤ 10 points (state is not the carrier).
- `G(8)` at most 3 points (states already store meaning at low load) or `G(128)/G(8)` at least 2 (readout interference dominates).
- Rank-capped transport closes ≥ 80% of the gap (training redundant).
- Redesign: mean `cos(W, P)` over E heads > 0.9 on the 57M A0 at init or 60M (control equals treatment by construction).
- Defer: G1 fails (A0 monolingual < 60% or cross-lingual < 15% at N = 8, and dense A4 < 25%) — instrument at floor at 57M/200M, new versioned contract.
- Floor-compressed: A1 and A2 both < 10% cross-lingual EM in every seed — no inference either way.
- Kill: any seed pair A1 − A2 negative, or the seed mean negative. Promote only on seed mean ≥ 5 with all pairs positive and the pooled prompt-clustered CI excluding 0; anything else is an underpowered band → +2-seed line (wave-5 rule; the wave-4 every-pair-≥-5 rule is retired, not erased).
- A3 closes ≥ 50% of A1's closure; closure appears only on surface-shared keys.
- LM loss > 1% worse; mean `||W||` in E heads shrinks > 30%; A5 ≈ A0 while A1 beats only A5.
- Prefix-floor check fails: `W` translation-pair cosine is not above its same-prefix floor by ≥ 0.05 in ≥ 2/3 of E heads.

## Compute

Pilot image (rebuilt with fla, Slurm job 353 from commit `999f5583`, 2026-09-01):
`cotcodec-research:999f5583-architecture`, image ID
`sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad`, digest
`127.0.0.1:5000/cotcodec-research@sha256:bde90daa78c26cd2fb9d05036b0c9f9613c2386b9d7561816b541d2736c79f5d`
(torch 2.11.0+cu128, transformers 5.15.0, flash-linear-attention 0.5.2, fla-core 0.5.2,
triton 3.6.0). The older discovery image `…@sha256:15d6abc0…` lacks fla and is no longer
cited. Pending: a tilelang rebuild, because fla 0.5.2 guards the gated GDN backward on
Hopper under Triton < 3.7.1 (fla #640) and torch 2.11.0 pins triton 3.6.0 — `tilelang>=0.1.13`
is in the `architecture` extra (commit `0b3ecef`) and the phase-1 image must be re-pinned
after the rebuild; `sentencepiece`, `datasets` and `datasketch` still to be added. Checkpoint
receipts (job 356) exist on the host under `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/`
for `qwen3.5-4b-base`, `qwen3-1.7b-base`, `transformer-1.3b-100b`, `gla-1.3b-100b`,
`transformer-340m-10b`, `gla-340m-15b`, `gdn-1.3b-isp-hybrid-3to1-50b`,
`gdn-340m-isp-hybrid-3to1-10b`, `e2-ttt-mlp-1.3b-15b`, `rwkv7-1.5b-world` (repo copies in
`data/model-receipts/`); the Olmo pair is registered without receipts. The CPU doctor runs
outside Slurm on any CPU and must be rerun inside the container as the first phase-0 step.
The submitter
`scripts/submit_docker_research_job.py` consumes a **compiled job manifest**
(`runtime: docker-single-node-discovery-v1`, `image_id`, `git_sha`, `source_sha256`,
model receipt, seeds, resources, budget, command), not the contract — pointing it at the
contract exits with `runtime must be docker-single-node-discovery-v1` (reproduced
2026-09-01). Three manifests, `infra/slurm/host-single-node/tesw-phase0-frozen-screen.yaml`,
`tesw-phase1-selection-gate.yaml` and `tesw-phase1-grid.yaml`, are declared in the
contract's `execution.job_manifests` and do not exist yet; the dry run (`--dry-run`) then
the real submit go through `sbatch infra/slurm/host-single-node/docker-research.sbatch` on
the single-node Slurm; seeds 42, 43, 44; 16 GPU-h ceiling; 15-minute atomic checkpoints to
`/home/kevin/cotcodec-runs`; SIGUSR1 checkpoint and fresh-job resume test on the smoke run
(this test also licenses resuming the selection checkpoints as seed-42 grid runs).
Slurm 21.08.5 without cgroup-v2 makes this the discovery lane, not the publication lane.
Execution is disabled in the contract until the blockers listed there are cleared.

## Kevin advantage

Not required for the pilot, which uses FLORES+, FineWeb/FineWeb-2, ParaCrawl,
SCB-MT and Apache-2.0 Qwen3.5/Qwen3/Olmo checkpoints. Real but optional: General
Translation's span-aligned corpora and translators could extend the instrument to
sub-sentence spans and to Bn/Ja/Ar — but the 2026-09-01 inventory
(`research/data/gt-parallel-corpus-inventory-2026-09-01.md`) excludes customer
translation memory under ToS §3.1 and clears only GT-owned 8-locale docs pairs as a
small evaluation set; never customer content; the 8xH100 node with the Docker/Slurm/checkpoint harness and
an existing receipt lineage for `qwen3.5-4b` make phase 0 a same-day job and the
18-run grid a two-day job; registered `qwen3.5-9b` (GDN) and
`kimi-linear-48b-a3b-base` (KDA) support instrument-only extensions.

## Negative-result value

Phase 0 alone yields the first within-model, state-intervention measurement of
cross-lingual recall in a 2026 GDN hybrid on a registered checkpoint: "state is a
bystander", "readout interference, not storage", or "meaning up to a rank-64
linear transform" each closes sweep gap G2 and is publishable; the `W`-vs-`D`
table documents a shortcut every future recurrent-state alignment loss must
avoid, and the `W`-vs-`P` table says whether the write is even a distinct object
from its projections on sentence-length spans. Phase-1 negatives: G1 deferral
(a 57M/200M hybrid cannot do translated recall on FLORES+ keys — an instrument-scaling
fact); A1 ≈ A2 (the write adds nothing over projection alignment); A3 ≈ A1
(language-ID removal, not equivariance); surface-shared-only closure (copy
shortcut); A5 ≈ A0 with A1 > A5 only (bitext exposure). TP-MQAR-v2, the
intervention toolkit and the selection ledger remain the G2/G20 instrument in
every branch.
