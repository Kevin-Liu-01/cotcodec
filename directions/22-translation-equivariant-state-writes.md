# Direction 22: Translation-Equivariant State Writes

**Status:** DRAFT on 2026-09-01 — wave-3 identification repair applied; frozen within-model kill screen must pass before any from-scratch run
**Priority:** CPU object doctor, then the 3.8 GPU-h frozen screen, before the 12 GPU-h 57M grid
**Experiment contract:** `experiments/architectures/translation-equivariant-state-writes.yaml`
**Proposal:** `research/proposals/2026-09-01-translation-equivariant-state-writes.md`

## Research question

Does a fixed-size recurrent state store meaning or surface? Two translations of
the same span, behind a bitwise-identical prefix, should produce the same
**write** into a Gated DeltaNet head if the state stores meaning. Phase 0 asks,
on a frozen 2026 GDN hybrid and within that model, whether the state carries
cross-lingual recall at all, whether the cross-lingual gap is a storage-format
effect rather than readout interference, and whether a training-free linear
transport already closes it. Phase 1 asks whether supervising the write on
public bitext closes the gap in 57M from-scratch hybrids and beats the same loss
on the projections that feed the write.

The wave-2 version supervised the raw segment delta `D = S(c⊕a) − S(c)`. Both
wave-2 judges showed `D` contains a content-independent prefix term shared by
every translation pair, so the loss could be satisfied without equivariance.
This direction supervises the pure write instead.

## Mechanism

Per layer and head the fla recurrence is `S_t = S_{t−1} α_t (I − β_t k_t k_tᵀ) + β_t v_t k_tᵀ`.
It is affine in the state, so for a span `a` after prefix `c`:

```text
S(c⊕a) = S(c) · ∏_t α_t (I − β_t k_t k_tᵀ)                       # prefix carry (decay + erase)
       + Σ_t β_t v_t k_tᵀ · ∏_{s>t} α_s (I − β_s k_s k_sᵀ)          # pure write W(a|c)

W(a|c) := S(c⊕a) − S_{v=0}(c,a)     # second chunk_gated_delta_rule pass from S(c) with v ≡ 0
                                    # equals the state from S_0 = 0 with the same projections

L = L_LM + λ [ mean_{(l,h)∈E} (1 − cos(W^A, W^B))
             − log exp(s(W^A, W^B)/τ) / Σ_{B'} exp(s(W^A, W^{B'})/τ) ]

negatives B': ≥2 same-prefix random language-B sentences + ≥2 same-prefix
entity/number-sharing hard negatives (all behind the identical c), plus in-batch extras
τ = 0.07, λ ∈ {0.1, 0.3}, E = half the heads of every GDN layer

A2 control: same loss on P(a) = Σ_t β_t v_t k_tᵀ (decay-free, erase-free, no recurrence)
A3 placebo: same loss, content-independent same-prefix language-B sentence
```

Phase-1 hybrids use sliding-window attention (window 512) so a fact placed more
than 512 tokens before the query is recalled only through the state. The
instrument is TP-MQAR-v2: N facts of the form "key sentence in language A, separator, 4-digit code",
query in language B, digit-only exact match, surface-disjoint keys (token and
subword filters) as the primary subset, N in {8, 32, 128}.

## Closest work and delta

| Prior | What it occupies | Delta here |
|---|---|---|
| WriteSAE [2605.12770](https://arxiv.org/abs/2605.12770) | post-hoc write interventions on GDN/Mamba-2/RWKV-7 caches | interventions are applied to a cross-lingual recall question with a matched perturbation control; the write is also supervised |
| Procrustes residual patching [2608.27115](https://arxiv.org/abs/2608.27115) | bitext-fitted rotation patched into transformer residuals | the recurrent analogue is a pre-registered kill gate (rank-capped transport), not a contribution |
| MLNeedle [2408.10151](https://arxiv.org/abs/2408.10151), OneRuler [2503.01996](https://arxiv.org/abs/2503.01996) | cross-lingual needle retrieval on dense models | recall framing, key x query language matrix, state interventions, hybrid substrate |
| Token-level Olmo pair comparison [2606.20936](https://arxiv.org/abs/2606.20936) | the Olmo Hybrid/Olmo 3 pair as a monolingual matched instrument | cross-lingual axis; the pair is used descriptively only (see confounds) |
| Gather-and-Aggregate [2504.18574](https://arxiv.org/abs/2504.18574), Attention Amnesia [2606.11052](https://arxiv.org/abs/2606.11052) | hybrid recall lives in few softmax heads | motivates D-zero and the SWA-512 design |
| GI-SAE [2608.23809](https://arxiv.org/abs/2608.23809) | functional-swap criterion | applied to writes; demoted to a secondary endpoint because it is monotone in the trained cosine |
| Leino & Tiedemann [2603.29026](https://arxiv.org/abs/2603.29026); Middle-Layer Alignment [2502.14830](https://arxiv.org/abs/2502.14830) | bitext exposure and residual alignment in transformers | live A5/A0 contrast; object is the write, not the residual |
| Olmo Hybrid [2604.03444](https://arxiv.org/abs/2604.03444) | the substrate | no cross-lingual or state-level analysis |

No direct prior art found through 2026-09-01 under the arXiv, Hugging Face
papers, OpenReview (titles unresolved) and bookmark coverage recorded in the
proposal. The loss form is standard; the object and the instrument are the
delta. Collision risk for the instrument half is medium.

## Unregistered checkpoints named by this direction

- `allenai/Olmo-Hybrid-7B` revision `4f1cc566f9fdf3ce68da2ab6a788a83d89896dcf` (Apache-2.0; 24 GDN + 8 full-attention layers; NoPE attention; `transformers ≥ 5.8.1` exposes recurrent states).
- `allenai/Olmo-3-1025-7B` revision `a81bae42db3975be1671e27b9c9a56da1a9f980f` (Apache-2.0; 24 SWA-4096 + 8 full-attention layers; RoPE + YaRN).

Ai2 describes the pair as **throughput-matched**, not architecture-matched: the
model cards report different data mixes (Olmo 3 32B mix vs 7B mix), stage-1
tokens (5.50T vs 5.93T), LR schedules (cosine vs piecewise), widths (3840/30
heads vs 4096/32), stage-2 merging, and NoPE vs RoPE in the shared attention
layers. The pair is therefore a descriptive reference and a source of the dense
cross-lingual EM floor gate; no kill depends on the hybrid-minus-dense
difference. The contract YAML uses registered `qwen3.5-4b` and `qwen3-0.6b-base`
as stand-ins until both Olmo checkpoints are added to `models/registry.yaml`.

## Cheapest decisive pilot

1. **CPU object doctor (0 GPU-h).** fp64 identity `S_{S0=0}(a) == S(c⊕a) − S_{v=0}(c,a)`;
   bitwise-identical `S(c)` across a pair; TP-MQAR-v2 from FLORES+ devtest (En, De, Es)
   with leakage controls at chance; dedup of FLORES+ against phase-1 streams.
2. **Frozen within-model kill screen (3.8 GPU-h incl. reserve, 2 GPUs).** 9 language
   cells x 2 key types x N in {8, 32, 128} x 100 prompts on the hybrid (dense at N in
   {8, 32}); D-zero on the fact span vs D-zero on an equal-length distractor span;
   rank-capped (r ≤ 64) dual-form transport fitted on 997 FLORES+ dev pairs x 8
   prefixes with identity and random-rotation controls; swap; prefix-floor table for
   `W` and `D`. Gates: monolingual EM ≥ 60% in both models and dense cross-lingual
   EM ≥ 40% at N = 8 per language pair.
3. **57M from-scratch grid (≤ 12.0 GPU-h incl. reserve, gated on the screen).** Arms
   A0 baseline, A1 write equivariance, A2 projection alignment, A3 language-marginal
   placebo, A4 dense, A5 no-bitext, each x 3 seeds at 200M tokens (75% monolingual,
   20% prefix-sharing bitext, 5% same-language recall curriculum); LR sweep on A0 only;
   conditional A4′ (dense + A2's loss) only if the smoke run measures ≥ 200K tok/s/GPU.
   Primary endpoint: A1 − A2 closure on surface-disjoint beyond-window keys, ≥ 5 EM
   points, same-signed in all 3 seed pairs, prompt-clustered CI excluding 0.

Total 15.8 GPU-h under a 16 GPU-h ceiling. Three seeds are a kill screen
(power 0.37 at 5 points for a seed SD of 3); +2 seeds are a separate line.

## Controls

- A2 same-layer projection alignment (decisive; identical loss, λ, τ, same-prefix negatives, heads, pooling shape; no recurrence).
- A3 language-marginal placebo (reads out language-ID removal on the write).
- A4 iso-parameter dense transformer; A5 iso-token no-bitext hybrid; A0 λ = 0 baseline.
- D-zero with a matched distractor-span perturbation; rank-capped transport with identity and rotation controls; swap on never-trained prefixes.
- Surface-disjoint vs surface-shared keys with token and subword filters; entity/number hard negatives; digit-only EM; retrieval-impossible and value-permutation controls.
- Published baselines: MLNeedle, OneRuler, WriteSAE, 2608.27115; QED (2608.13668), MARCH and SWA+sinks (2608.28444) become mandatory only if a recall-improvement claim is made.

## Falsifiers

- D-zero on the fact span exceeds its matched perturbation by ≤ 10 points (state is not the carrier).
- `G(8)` at most 3 points (states already store meaning at low load) or `G(128)/G(8)` at least 2 (readout interference dominates).
- Rank-capped transport closes ≥ 80% of the gap (training redundant).
- A1 − A2 < 5 EM points paired over seeds, or any seed pair opposite-signed.
- A3 closes ≥ 50% of A1's closure; closure appears only on surface-shared keys.
- LM loss > 1% worse; mean `||W||` in E heads shrinks > 30%; A5 ≈ A0 while A1 beats only A5.
- Prefix-floor check fails: `W` translation-pair cosine is not above its same-prefix floor by ≥ 0.05 in ≥ 2/3 of E heads.

## Compute

Discovery image `127.0.0.1:5000/cotcodec-research@sha256:15d6abc06fa53ab466087a92107da9c58e469615e2f56a683fefd0a7600277f3`
(CUDA 12.8.1, torch 2.11.0+cu128, transformers 5.15.0; no fla) covers only the
CPU doctor. The pilot needs a rebuilt image with `flash-linear-attention≥0.5.2`,
`sentencepiece`, `datasets` and `datasketch`, re-pinned by digest. Jobs go through
`scripts/submit_docker_research_job.py` (dry run first) onto the single-node
Slurm via `sbatch`; seeds 42, 43, 44; 16 GPU-h ceiling; 15-minute atomic
checkpoints to `/home/kevin/cotcodec-runs`; SIGUSR1 checkpoint and fresh-job
resume test on the smoke run. Slurm 21.08.5 without cgroup-v2 makes this the
discovery lane, not the publication lane. Execution is disabled in the contract
until the blockers listed there are cleared.

## Kevin advantage

Not required for the pilot, which uses FLORES+, FineWeb/FineWeb-2, ParaCrawl,
SCB-MT and Apache-2.0 Olmo checkpoints. Real but optional: General Translation's
span-aligned corpora and translators extend the instrument to sub-sentence spans
and to Bn/Ja/Ar (license and consent status unknown; never customer content);
the 8xH100 node with the Docker/Slurm/checkpoint harness makes the 18-run grid a
two-day job; registered `qwen3.5-4b` (GDN) and `kimi-linear-48b-a3b-base` (KDA)
support instrument-only extensions.

## Negative-result value

Phase 0 alone yields the first within-model, state-intervention measurement of
cross-lingual recall in a 2026 GDN hybrid: "state is a bystander", "readout
interference, not storage", or "meaning up to a rank-64 linear transform" each
closes sweep gap G2 and is publishable, and the `W`-vs-`D` prefix-floor table
documents a shortcut every future recurrent-state alignment loss must avoid.
Phase-1 negatives: A1 ≈ A2 (the write adds nothing over projection alignment);
A3 ≈ A1 (language-ID removal, not equivariance); surface-shared-only closure
(copy shortcut); A5 ≈ A0 with A1 > A5 only (bitext exposure). TP-MQAR-v2 and the
intervention toolkit remain the G2/G20 instrument in every branch.
