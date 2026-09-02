# Frontier Systems Research Program — 2026-09-01

Supersedes `frontier-systems-program-2026-08-10.md` for direction ranking and
compute planning. Signals and their sources are in
[`scans/2026-09-01.md`](scans/2026-09-01.md); raw cell notes with every URL are
in `scans/2026-09-01-cells/` (manifest
`bebdcf7c365bf77aaf7134a28086d953bb7976c81f131276d476a98831d01957`). This
document does not claim global novelty; it reports what was and was not found
through 2026-09-01 under the coverage recorded in the scan, and it labels
collision risk. Every promoted direction must still pass the loop in
`.claude/rules/research-gauntlet-loop.md` before any GPU-hour is spent.

## Executive verdict

1. **Do not design another sequence operator.** Fixed-ratio linear/global
   hybrids, learned sparse indexers, delta-rule gate geometry, depth-axis
   residuals, MTP heads, learned sinks, and per-token operator routing are each
   held by two or more production labs (Kimi K3, Qwen3.8-Next, GLM-5.3-Flash,
   DeepSeek-V4, Nemotron 3.5, Motif 3, A.X K2) plus a dense August preprint
   stream. The 2026-08-10 rejections stand, and that program's "Budgeted
   Mixture of Sequence Operators" is now occupied on the layer, token, head,
   block, and serving axes.
2. **The unique-asset bet is language as a controlled variable inside the
   architecture** — with the 2026-09-01 correction that the asset is parallel
   data GT can lawfully use (public corpora plus GT-owned content), not
   customer translation memory. Every cell independently found this region empty:
   recurrent-state recall and hybrid-ratio behaviour with content held fixed
   across translations; learned-indexer selection across translations;
   parallel-data-supervised byte boundaries; translation-equivariant abstract
   reasoning codes with cross-language monitor transfer; cross-lingual
   fast-weight readout. Production parallel translation data is the defining
   input here, not an aid.
3. **Portability after PorTAL survives only across operator families, label-free,
   or at the update-rule level.** "Train once, port a LoRA" among softmax
   transformers (including MoE, local/global, multimodal, cross-tokenizer
   distillation) and "frozen object + thin target-side reader" (Engram reader
   transfer, KV translation) are occupied.
4. **Current directions:** D16 NARROWED (update-rule portability only); D17
   NARROWED (prospective randomized identification only; Hindsight Memory-PRM
   holds post-hoc deletion credit); D18 STILL_OPEN with five new control arms;
   D15 NARROWED to tool-use × monitorability and translation-equivariant codes;
   Coded Delta Memory reduced to a negative-result cell; Bidirectional Plan
   Repair has a novelty collision (CID); Rollout-Value Operator Scheduling and
   Rank-Adaptive Edit Summaries are largely occupied — park both.
5. **Methodology is now a hard gate.** SR-TTT v2's retraction and "The Mask Is
   Not the Model" make a two-forward-pass causality audit, generation-based
   exact-match evaluation, SWA+sinks and tail-replay controls, per-arm
   hyperparameter search, ≥3-size scaling ladders, and ≥3–5 seeds mandatory for
   any small-scale architecture claim. They are encoded in the gauntlet rule.

## What the frontier occupies (merged by mechanism)

| Axis | Held by | Remaining gap |
|---|---|---|
| 3:1 linear/global hybrid layouts | Kimi K3, Qwen3.5/3.8, GLM-5.3-Flash, Solar Open 2, Nemotron 3.5, MiMo-V2-Flash; 72-model ratio sweep | behaviour across scripts/languages with content fixed; no sub-10B open KDA base; no released 2026 KDA/QSA base |
| Sparse global attention with learned indexer | DSA, QSA, CSA/HCA, LongCat LSA, IndexShare, MiniMax MSA, A.X K2 SGA | cross-lingual behaviour of indexers |
| Delta-rule state geometry | KDA lower-bounded decay, GDN-2, QED, MARCH, SANE, Kaczmarz/OSDN/preconditioned variants, Falcon rules; NVIDIA patent filing US20260105282A1 | closed for new gates; LM-scale complex decay with kernels unclaimed |
| Depth-axis residual operators | AttnRes/Block AttnRes (four third-party replications with gains; one 1B negative with routing collapse), mHC/xHC, Gated Residual, Deep Delta Learning | independent iso-compute multi-seed comparison at 0.1–1B; depth weights as a probe |
| Operator placement/routing | FlashMorph, NAtS-L, LoGo, Switch Attention, HydraHead, Mixture of Layers, RouteSparse | only rollout-valued stateful continuation; structurally capped |
| Positional encoding in hybrids | NoPE (Kimi, Solar), RoPE kept (Qwen3.8-Next), partial RoPE, HyPE, PaTH | mechanism of the NoPE disagreement |
| MTP heads | standard everywhere; AdaMTP, LoopMTP, Windowed-MTP | controlled MTP ablation on ≤1B hybrids |
| Hybrid serving state algebra | DASC, Tail-Replay, DeltaLog, TreeWY, DAMP, HARTS | non-suffix edits on long-retention units only |
| Test-time training / fast weights | E²-TTT, Modular TTT, LaCT, MesaNet, Falcon, In-Place TTT, MoNe, Titans/MIRAS/Atlas (no code) | causality-verified independent replication; reset/deletion/poisoning; nonlinear stability theory |
| Adapter portability / hypernetworks | PorTAL, SHINE, HypeLoRA, Text-to-LoRA, Trans-LoRA, Cross-LoRA, Engram reader transfer, KV translation, ACTD, UpgradeBench | cross-operator-family port; label-free alignment; update-rule port |
| Latent reasoning media | Coconut, Abstract-CoT, Huginn, Ouro, MUX, J-CoT, DiscoLoop, SELR, looped LMs for tools | monitorability on tool-use tasks; translation-equivariant codes; controlled Abstract-CoT replication |
| Byte / tokenizer-free | BLT, H-Net, Bolmo, When Tokenizers Fail, Autocompleting Tokenizers, MAGNET, parity-aware BPE | parallel-translation supervision of boundary formation (D18) |
| Diffusion LMs | LLaDA2.2, DiffusionGemma, Mercury 2, CID, dLLM acceleration stack | iso-wall-time agent comparison with CPU dispatch charged; language-dependent serial depth |
| Harness science | HarnessLens, StarHarness, PILOT, OpsHarness, UHP, Same Model Different Harness | factorial attribution on real open models; multilingual harness effects |

## Open gaps (22, deduplicated; full text in the synthesis)

G1 parallel-translation supervision of byte/patch boundaries (D18) · G2
language/script-controlled probes of recurrent state · G3 porting a task adapter
across operator families · G4 label-free base alignment calibrated on parallel
data · G5 porting an update rule (D16) · G6 causality-verified replication of
beyond-window TTT recall · G7 verifiable reset/rollback/deletion and poisoning of
fast weights · G8 stability theory for nonlinear fast weights · G9 iso-compute
multi-seed depth-operator comparison · G10 NoPE-in-hybrids mechanism · G11 MTP
ablation on small hybrids · G12 open ≤1B K3-stack reference and training-side
numbers · G13 cross-lingual behaviour of learned indexers · G14 monitorability of
latent media on tool-use tasks · G15 translation-equivariant abstract codes ·
G16 controlled Abstract-CoT reproduction · G17 diffusion iso-wall-time agent
comparison · G18 randomized identification of memory value (D17) · G19
compute-per-semantic-unit parity only (its routing half is **occupied** by SARA,
Findings of ACL 2026, and RA-MoE) · G20 missing 0.1–1B evaluation instruments ·
G21 harness-layer measurement gaps · G22 Tinker-specific knowledge gaps.

Verification-pass amendments (`scans/2026-09-01-cells/verify-*.md`): G2 must be
stated as *recurrent-state and hybrid* behaviour with content held fixed across
translations — cross-lingual needle retrieval on softmax transformers already
exists (MLNeedle, NAACL 2025; ONERULER); G14's "interpretable-by-construction
latents as a monitor channel" is partly occupied by ALCA (ACL 2026, auditable
latent CoT with restricted self-decoding), leaving tool-use tasks, obfuscation
pressure, and cross-lingual monitor transfer; the NVIDIA "Gated delta networks"
filing (US20260105282A1, pending) and Google's compressive-memory filing
(WO2025230701A1) sit over delta-rule gating and linear-attention memory — any
kernel-level contribution there carries IP exposure to check before release.

## Gauntlet wave 1 (2026-09-01): sixteen candidates, all refuted before judging

Ten inventor angles (translation-supervised architecture, portability after
PorTAL, state semantics, monitorable media, causal fast weights, compute equity,
agent-native architecture, cross-domain import, LoRA-only probes, depth/hybrid
mechanisms) produced 27 candidates; one owner merged them into 16 canonical
mechanisms (`gauntlet/2026-09-01-frontier/wave1-candidates.md`). Each faced a
refute-first triad with default `refuted=true` under uncertainty. Result: **0
ranked, 16 killed** (`wave1-ledger.md`, `wave1-verdicts.json`; audit row in
`data/research-gauntlet/2026-09-01-frontier.jsonl`).

- Novelty **not refuted** (8): `semantic-clock-gate-parity`,
  `translation-supervised-sparse-indexer`, `cross-family-adapter-port`,
  `icl-rule-distillation-port`, `translation-equivariant-state-writes`,
  `commit-gated-observation-state`, `frozen-reader-anchored-media`,
  `interlingua-trace-codes`.
- Novelty **refuted** (8): `meaning-indexed-compute-allocation` (SARA/RA-MoE and
  H-Net-class chunking), `hybrid-state-provenance-ledger` and
  `read-free-record-blocked-memory` (both occupied by "Subtract or Replay?",
  2607.27539 v2), `provenance-typed-attention`, `tag-and-capture-delta-memory`,
  `lora-footprint-routing-probe`, `nope-hybrid-clock-tiebreak` (Kimi Linear's
  own design rationale), `global-anchor-skip-read-depth-operators` (SANA-Video
  2.0 states the mechanism).
- Every candidate failed **identification** (0.8) and **feasibility** (0.7–0.9).
  The recurring defects are instructive: pilots assumed parallel data the
  repository does not hold; GPU-hour budgets rested on the unmeasured "125M to
  1000N tokens ≈ 8 h at 40% MFU" assumption; matched controls were missing
  (full-attention arm, parity-aware BPE arm, uniform-regularizer arm,
  training-free state surgery); several primary endpoints equalled the training
  objective; counterfactual references were mixed across arms.

Wave 2 (in progress at this writing) assigns one repair owner to each of the
eight novelty-survivors with a fixed work order: add the named controls, make the
endpoint a held-out quantity, run the pilot on a named public license-cleared
corpus with General Translation data as an optional upgrade, and re-budget from
cited throughput with a 25% reserve — then the same triad, blind discrimination,
and two judges.

## Ranked portfolio after gauntlet wave 2 (2026-09-01)

Scores are the lower of two independent judge totals on the ten-dimension
gauntlet rubric, capped at 89 because no provider-distinct signed review exists;
none is pilot-ready. Every survivor still carries an identification defect the
judges agree on; wave 3 (the spec phase) applies exactly that fix and produces a
proposal, an experiment contract, and a direction file (19–22) per candidate.

| Rank | Direction | Wave-2 score | Claim scope | Phase-0 GPU-h | Gaps | Collision | Judges' highest-impact fix |
|---:|---|---:|---|---:|---|---|---|
| 1 | `icl-rule-distillation-port` | 62 | architecture-causal | 6 | G5, G2, G6, G7 | high | Make the placebo symmetric and add teacher fidelity as the primary endpoint: (1) include the teacher's own shuffled-label episodes in the distillation set for every rule (R_theta, R_GD, label-trained  … |
| 2 | `semantic-clock-gate-parity` | 61 | architecture-causal | 4 | G2, G20, seq-operators, benchmarks-eval, | low | Make phase 0 a within-model, GDN-borne, confound-breaking dose-response before spending anything on phase 1. (a) Decorrelate fertility from resourcedness in the language grid: add rus (f 1.42, 6.9% CC … |
| 3 | `translation-supervised-sparse-indexer` | 61 | attachment-capability | 4 | synthesis, synthesis, synthesis, seq-ope | medium | Re-register the identification so L_x must beat the strongest label-free repair and xi isolates language from literalness: (1) make the primary counterfactual (f)+L_x vs (f) and (g)+L_x vs (g) (QSA ma … |
| 4 | `translation-equivariant-state-writes` | 57 | architecture-causal | 3.2 | G2, G20, benchmarks-eval, seq-operators | medium | Redefine the supervised object and the negatives so the loss cannot be satisfied through prefix identity: (1) compute a decay-only counterfactual state by running the span with writes disabled (beta_t … |

1. **`icl-rule-distillation-port`** (→ `directions/19`): distil a frozen
   transformer's content-dependent in-context update into an explicit rank-8
   fast-weight write rule at a canonical 64-d interface, freeze it, and port it
   through label-free maps onto pure-recurrent bases (DeltaNet/GLA/RetNet/Mamba/
   HGRN2/GSA at 1.3B) that have no KV cache to receive state; compare against a
   preconditioned-GD superset rule at the same interface and compute; a
   write-A/read-B held-out-language probe tests what the writes carry. Public
   data: Function Vectors task suite (MIT), FineWeb-Edu. Fix: symmetric
   shuffled-label placebo across all rules plus a teacher-fidelity primary
   endpoint.
2. **`semantic-clock-gate-parity`** (→ `directions/20`): the GDN/KDA forgetting
   and write clocks tick once per token, so equal content costs high-fertility
   languages more forgetting; phase 0 is a within-model dose-response on
   Qwen3.5-4B-Base with NTREX-128 n-way parallel sentences and MLNeedle/ONERULER
   baselines. Fix: decorrelate fertility from resourcedness in the language grid
   and add an attention-path control so the readout is the GDN clock, not the
   eight full-attention layers.
3. **`translation-supervised-sparse-indexer`** (→ `directions/21`,
   attachment-capability): learned sparse-attention indexers distilled from full
   attention are a cross-lingual retrieval bottleneck; supervise the indexer with
   aligned bilingual documents (ParaDocs/ParaCrawl, TED2020). Fix: the
   counterfactual must be the strongest label-free repair (QSA max-pool and
   retrieval-head-weighted targets) and the kill statistic must use a
   non-literal monolingual reference query.
4. **`translation-equivariant-state-writes`** (→ `directions/22`): a fixed-size
   recurrent state that stores meaning should write the same segment delta for
   two translations of a span; supervise that in half the heads of a GDN hybrid
   on FLORES+ multi-way sentences. Fix: supervise the pure write with the
   decay/erase counterfactual removed so the loss cannot be satisfied through the
   shared prefix.

Killed in wave 2 (retained in `gauntlet/2026-09-01-frontier/wave2-ledger.md`):
`cross-family-adapter-port` (retention pattern not attributable to softmax
coverage; budget arithmetic failed), `commit-gated-observation-state` (strongest
control present but inert in the decision rule), `frozen-reader-anchored-media`
(novelty refuted under the recombination rule), `interlingua-trace-codes`
(effect not attributable to parallel data over the objective itself).

## Gauntlet wave 3 (2026-09-01): proposals, contracts, and direction files written

| Direction | Proposal | Contract (validator PASS, `execution.enabled: false`) | Wave-2 → wave-3 score |
|---|---|---|---:|
| `directions/21-translation-supervised-sparse-indexer.md` | `proposals/2026-09-01-translation-supervised-sparse-indexer.md` | `experiments/architectures/translation-supervised-sparse-indexer.yaml` | 61 → **66** |
| `directions/20-semantic-clock-gate-parity.md` | `proposals/2026-09-01-semantic-clock-gate-parity.md` | `experiments/architectures/semantic-clock-gate-parity.yaml` | 61 → **64** |
| `directions/22-translation-equivariant-state-writes.md` | `proposals/2026-09-01-translation-equivariant-state-writes.md` | `experiments/architectures/translation-equivariant-state-writes.yaml` | 57 → **63** |
| `directions/19-icl-rule-distillation-port.md` | `proposals/2026-09-01-icl-rule-distillation-port.md` | `experiments/architectures/icl-rule-distillation-port.yaml` | 62 → **57** (dip: reviewers require an iso-capacity nonlinear GD-form control) |

The deterministic doctor (`scripts/research_direction_doctor.py`) reports
`status: FAIL` for all four — correctly: no evidence bundle exists, Compute is
FAIL (no real model loop, container smoke, or Slurm dry-run attested), and the
reviews are internal and unsigned. Wave-4 work orders are the reviewers'
highest-impact fixes recorded in `gauntlet/2026-09-01-frontier/wave3-ledger.md`.
Exit state for this session: best score 0 → 62 → 66 over three waves; nothing is
pilot-ready; the loop continues under `.claude/rules/research-gauntlet-loop.md`.

### What must happen before any GPU-hour is spent on these

1. Parallel-data inventory (blocking input above); every phase-0 pilot is
   written to run on named public corpora so this does not block the kill
   screens, only the General Translation upgrade arms.
2. Rebuild and digest-pin the research image with `flash-linear-attention`
   0.5.2 — in flight 2026-09-01: `flash-linear-attention==0.5.2` is pinned in the
   `architecture` extra and lock; Slurm job 353 built
   `cotcodec-research:999f5583-architecture` (image ID `sha256:9d832a59fe34…`, local-registry digest
   `bde90daa…`, fla 0.5.2 verified inside); the throughput doctor
   (`scripts/fla_throughput_doctor.py`) and the pilot-checkpoint fetch run next (and `mamba_ssm`/`causal-conv1d` where a contract needs them); the
   cited image `sha256:15d6abc0…` is the current discovery image and lacks them.
3. ~~Register the pilot checkpoints~~ — fifteen entries added to
   `models/registry.yaml` on 2026-09-01 (revisions pinned; licenses as stated,
   `unresolved` for three fla-hub repos; all blocked pending receipts). Still
   needed: `fetch_open_model.py fetch/verify` receipts on persistent storage and
   a compiled job manifest per contract for `scripts/submit_docker_research_job.py`.
   Original item: register the unregistered pilot checkpoints named in directions 19–22
   (fla-hub 340M/1.3B/2.7B ladders, startlux GDN hybrids, Qwen3-1.7B-Base,
   Qwen3.5-4B-Base, RWKV-7, Olmo checkpoints) in `models/registry.yaml` with
   receipts; compile a job manifest per contract for
   `scripts/submit_docker_research_job.py`.
4. Write the CPU phase-0 doctors (two-forward-pass causality audit, TP-MQAR
   builder, gate-ledger extractor) and their tamper tests; a contract may only
   flip `execution.enabled` after its doctor passes twice.
5. Measure throughput on the node (one timing job) to replace the assumed MFU in
   every budget ledger.


## Gauntlet wave 4 and Stage-0 execution (2026-09-01, later)

| Direction | Wave 3 → 4 | Binding defect now |
|---|---:|---|
| `19-icl-rule-distillation-port` | 57 → **65** | no executable Stage-A doctor; attribution-tree power mis-stated |
| `20-semantic-clock-gate-parity` | 64 → **63** | estimand not headroom-invariant; needs a synthetic-fertility positive control |
| `21-translation-supervised-sparse-indexer` | 66 → **62** | decision rule derived from an unmeasured noise model; λ_x selection step missing |
| `22-translation-equivariant-state-writes` | 63 → **60** | pilot not decisive at its own minimum effect; CPU object doctor is prose |

Ledger: `gauntlet/2026-09-01-frontier/wave4-ledger.md`. Every reviewer's binding
defect is the missing executable pilot (cap 79); wave 5 implements the CPU
phase-0 doctors as tested code.

Stage-0 execution on `fal-h100-01` (discovery lane, no root, no publication claim):

- **Image rebuilt with fla.** Slurm job 353 built `cotcodec-research:999f5583-architecture`
  (image ID `sha256:9d832a59fe348d149d2e4587ac6af90223e2956ebb646d7b19295298954ca5ad`,
  local-registry digest `sha256:bde90daa…`): torch 2.11.0+cu128, transformers
  5.15.0, flash-linear-attention 0.5.2, triton 3.6.0. The host's default Docker
  bridge has no DNS; the build uses `--network=host`.
- **Pilot checkpoints fetched with receipts** (job 356; `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/`):

| registry id | revision | artifact root SHA-256 | size |
|---|---|---|---|
| `e2-ttt-mlp-1.3b-15b` | `6bac56e26c2b…` | `8052dbeb590dd63e…` | 3.04 GB |
| `gdn-1.3b-isp-hybrid-3to1-50b` | `0ced446e7677…` | `34b36f5b54a4f719…` | 5.73 GB |
| `gdn-340m-isp-hybrid-3to1-10b` | `eec9dbb045dd…` | `1c0150cbb95dd393…` | 1.57 GB |
| `gla-1.3b-100b` | `46b15820a4df…` | `da4eb9fb3ebb1186…` | 2.73 GB |
| `gla-340m-15b` | `6e04029dc090…` | `8fff2f27e0de2e80…` | 0.69 GB |
| `qwen3-1.7b-base` | `ea980cb0a6c2…` | `231d93ceda83766b…` | 3.45 GB |
| `qwen3.5-4b-base` | `1001bb4d826a…` | `c7fbfd6bd1c73b9a…` | 9.34 GB |
| `rwkv7-1.5b-world` | `004140baad7a…` | `8c662db05dedb86a…` | 3.06 GB |
| `transformer-1.3b-100b` | `d6f66f4181fa…` | `7b6675e3f5e9dccd…` | 2.73 GB |
| `transformer-340m-10b` | `b838e8e11784…` | `8bd8a855c1f85260…` | 0.69 GB |

- **Measured throughput, corrected geometry** (job 359; image `cotcodec-research:0b3ecef0-architecture`
  = `sha256:38044666…`, fla 0.5.2 + tilelang 0.1.13; one H100 80GB; eager, no compile, no fused
  cross-entropy; head_dim = hidden/heads, expand_v 1; receipts sealed in
  `evidence/infrastructure/fla-throughput-h100-2026-09-01.json`):

  | shape (actual params) | batch × seq | tokens/s | s/step | achieved TFLOPS | MFU (dense BF16 peak) | peak GiB |
  |---|---|---:|---:|---:|---:|---:|
  | gdn-hybrid-125m (134M) | 16 × 2048 | **282,501** | 0.116 | 243 | **24.6%** | 27.7 |
  | gdn-hybrid-350m (422M) | 8 × 2048 | **73,045** | 0.224 | 196 | **19.8%** | 26.9 |

  An earlier run with fla's default 256-dim heads (job 358) gave 104,185 tok/s and 7.5% MFU for the
  same 125M plan and ran out of memory at 350M — geometry, not kernels, explained most of that gap.
  Consequence for every budget ledger: the assumed 40% MFU is replaced by 20–25% eager; 1000N tokens
  for the 134M model costs ≈ 132 GPU-hours on one H100 (≈ 2× the assumed 8 h on eight at perfect
  scaling), 1000N for 422M ≈ 1,600 GPU-hours, and a 16 GPU-hour pilot buys ≈ 16 B tokens for the 134M
  model (≈ 120N) — a training-speed regime, which each proposal must state explicitly (believability
  bar item 3). torch.compile, fused cross-entropy, and larger batches are untested upside.
- **Throughput doctor blocked by a kernel-correctness guard** (job 354, before tilelang):
  `fla 0.5.2` raises "Triton >= 3.4.0 and < 3.7.1 on Hopper GPUs produces
  incorrect results for gated chunk_bwd_dqkwg (see fla #640); upgrade Triton
  to >= 3.7.1 or install tilelang". torch 2.11.0 pins triton 3.6.0, so the
  supported path is `tilelang`; it was added to the `architecture` extra and
  the image rebuilt as `cotcodec-research:0b3ecef0-architecture` (job 357),
  after which the gated backward ran. Consequence for every proposal: any GDN training
  number produced with fla 0.5.2 on H100 without tilelang is invalid, and the
  budget ledgers' MFU stays unmeasured until the doctor runs.
- **Credentials.** Moonshot's console is signed in (no key exists yet; the
  create-key dialog needs a human click); Tinker and Hugging Face consoles are
  signed out. Template: `~/.config/cotcodec/secrets.env` (mode 600).

## Compute and access boundary (verified 2026-09-01)

- **Local (fal-h100-01, 8 × H100 80GB, 208 CPUs, 1.7 TB RAM):** full
  fine-tuning is easy to ~12B, feasible to ~27–31B, LoRA easy to ~120B; from-scratch
  0.1–1.5B hybrids with `fla ≥ 0.5.2` kernels (KDA, GDN-2, Mamba3, AttnRes)
  fit comfortably (a 125M model to 1000N tokens ≈ 8 hours at 40% MFU). Kimi-K2.6
  (~1T INT4), Kimi-K3 (2.8T), GLM-5.3, DeepSeek-V4-Pro are not local objects.
- **Tinker:** LoRA-only (five fields, no per-module targeting), target-token
  log-probs only, AdamW only, no hidden states or gradients, no adapter import,
  Kimi-K2.6 at 32K/128K. Anything that needs internals, architecture changes,
  full-vocabulary logits, or custom optimizers runs locally. The pinned SDK
  0.23.3 must be re-verified (PyPI 0.27.0); `TINKER_API_KEY` is not present in
  the current environment.
- **Scheduler:** Slurm 21.08.5 is discovery-only; the publication lane needs
  Slurm 25.11.7 + Pyxis 0.24.0 + Enroot 4.2.1 built from source
  (`research/infrastructure/h100-publication-upgrade-2026-09-01.md`).
- **Every GPU run:** digest-pinned image, `sbatch` through
  `scripts/submit_docker_research_job.py`, persistent checkpoints under
  `/home/kevin/cotcodec-runs`, SIGUSR1 checkpoint plus fresh-job resume,
  `tmux` for the operator session only.

## Blocking inputs the program cannot supply itself

| Input | Why it blocks | Owner |
|---|---|---|
| Parallel translation corpus inventory | **Resolved 2026-09-01** in [`data/gt-parallel-corpus-inventory-2026-09-01.md`](data/gt-parallel-corpus-inventory-2026-09-01.md): customer translation memory is excluded by ToS §3.1 purpose limitation and the internal purpose-limitation policy (no research processing activity recorded); GT-owned 8-locale site/docs translations (99 pages × 8 locales) and 473 English doc pages remain usable as a small evaluation set. All phase-0 pilots already run on public corpora. | Decision on a research processing activity for de-identified customer data rests with GT, not this repository |
| `TINKER_API_KEY` (and `MOONSHOT_API_KEY` for live Kimi cells) | Tinker capability doctor, SDK-version check, and any Kimi-K2.6 rung cannot run | Kevin |
| Root access window on `fal-h100-01` for the Slurm/Pyxis/Enroot upgrade | Publication lane; discovery lane is unaffected | Kevin / host admin |
| Full-text reads of the K3, Qwen3.8-Next, DeepSeek-V4, and LLaDA2.2 reports | Several verdict numbers rest on abstracts or snippets | next session |

## Staged path

| Stage | Weeks | Work | Gate before GPU |
|---|---|---|---|
| 0 — receipts and controls | 0–2 | parallel-data inventory; Tinker SDK/capability doctor; two-forward-pass causality doctor and SWA+sinks / tail-replay control adapters added to the architecture validator; load-and-checkpoint smoke of the released 340M/1.3B GDN hybrids, E²-TTT, and FwPKM checkpoints under Slurm | CPU doctors pass twice |
| 1 — language as a controlled variable inside architecture | 2–10 | G2 translation-paired recall/state probes over released controls, then G1 boundary transport with the five new arms and G13 indexer probes on one shared substrate | Stage 0; preregistered contract; ≤16 GPU-hours per screen |
| 2 — portability across operator families | 6–14 | reframe D16 as G3/G4/G5: port a PorTAL-style adapter from Qwen3-0.6B-Base / Qwen3.5-4B onto Qwen3.5-0.8B (GDN hybrid), Mamba-130M, Kimi-Linear-48B-A3B, LLaDA-8B with parallel sentences as the label-free alignment stimulus; update-rule port as the moonshot cell | portallib reproduction with shuffled choices; iso-capacity baselines |
| 3 — reproducible-negative lane | 4–16 | open ≤1B K3-stack reference (G12) feeding G9/G10/G11 ablations with 5 seeds and per-arm HP search | Stage 0 |
| 4 — reasoning-media measurement | 8–16 | G14/G15: one fixed monitor across media at matched accuracy on tool-use tasks; translation-equivariant code with cross-language monitor | Stage 0; 4B–8B fits the node |
| 5 — D17 as randomized identification | after 0 | CPU paired oracle with Hindsight-PRM, AdmitOR, noise-placebo, reward-SNR gates before any Tinker spend | reward-SNR floor estimate |

Parked: Coded Delta Memory (negative cell only), Bidirectional Plan Repair
(until the four new deltas and a LLaDA2.x-mini/DiffusionGemma arm are
affordable), Rollout-Value Operator Scheduling, Rank-Adaptive Edit Summaries.

## What this sweep did not settle

Whether any small-scale advantage survives to ~1000N tokens; whether parallel
data moves anything beyond token-level alignment (representation alignment
barely moves per 2603.29026; boundary formation and recurrent-state behaviour
are untested); whether Tinker's shared-outer MoE LoRA changes routing at 1T;
whether SIGUSR1 propagates through Pyxis; and every first-party number that the
verification pass could not re-open (marked † in the scan).
