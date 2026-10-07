# Q3 K1 throughput probe (q3-k1-throughput-probe-v1)

Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row
for the freeze time and `git_head_at_freeze`. The probe job verifies this
file's digest against its ledger row at start-up. A material change to this
file or to the tabled code after the freeze is a new experiment id.

## Purpose and claim level

Program decision D20 keeps the registered design of
`q3-k1-localization-screen-v1` for its successor,
`q3-k1-localization-screen-v2`, changes only code efficiency, limits and caps,
and requires the limits to come from a measurement taken first, under its own
id, on synthetic tokens. This probe is that measurement. It times the v2 code
(the batched indexer bank and the vectorised evaluation) at the registered
shapes on one H100 and reports the rates from which the registered formula of
`harness/sparse_indexer_k1_budget_v2.py` gives every v2 job limit.

It decides limits, never science. No quantity it measures enters any K1
statistic, gate or verdict; it trains no indexer that is used again and reads
no recall that is interpreted. A probe result can only (a) set the v2 limits
and caps, (b) show that those caps with the probe exceed 8 GPU-hours, in which
case the research gauntlet applies to v2 before any freeze (D20: v2 is then
not cut), or (c) fail, in which case no v2 limit exists.

## Identity

Code. The probe job runs from the source baked into the probe image, built by
`infra/slurm/host-single-node/build-architecture-image.sbatch` from a fresh
clean clone of the commit that holds this file's ledger row. The manifest
filler (`scripts/fill_sparse_indexer_k1_probe_manifest.py`) refuses to fill
the manifest unless every file below has this SHA-256, and the probe writes
the digests of the files it ran into its receipt. The v2 registration tables
the same digests for the files they share, and the v2 manifest filler refuses
a probe receipt that measured any other version: changing any of this code
after the probe makes the probe's rates inapplicable, and a new probe id is
needed.

| File | SHA-256 |
|---|---|
| scripts/probe_sparse_indexer_k1_throughput.py | a3207e10ea1662a3111c43d1378eb4d58cd166c96644bc7f4bd4af66a756115f |
| harness/sparse_indexer_bank.py | e96653eb3eb5b9876201347c2fa8d452efc3ebb1043a516ac03c366ff8b89f88 |
| harness/sparse_indexer_k1_budget_v2.py | c86568a62fe12cbcb5ad91eed25fc0afd9e9a09078a43345b18277e6922ea4fe |
| harness/sparse_indexer_k1_equivalence_v2.py | 3c8b6caf8dc14fb62096cfa205e2e459f774227a73229e5d62e72bdb6ff3e9a1 |
| harness/sparse_indexer_k1_runtime_v2.py | 5bd8cb0a5e05fa49c82da1154d7ae7bb335741a0da84d78953ac36377f2a8547 |
| harness/sparse_indexer_torch.py | f21301a49634af07d5ae0385c34011400c83af15b984a96238dc6fe1d4ee9457 |
| harness/sparse_indexer_k1_runtime.py | 6fbddc91b6f7224f909901edb82278a68f68a208b558526c1a778ec9da6812fd |
| harness/sparse_indexer_k1_marker.py | 7bc69aa4d27a7d6de92f69a2f7b8e71d98b32101a2f34709fbaef2bdf84c3f1a |
| scripts/run_sparse_indexer_phase0a.py | ee11c38c3d84e691133b9563a3945331831ceb84ad7207d4c4f7a72e0906aef8 |
| scripts/fill_sparse_indexer_k1_probe_manifest.py | a5133df261e012ec94d300d174a6e13d636c41b100965f1fd57663ead970c7e0 |

The last four v1 files are `q3-k1-localization-screen-v1`'s tabled files,
unchanged (same SHA-256 as in its registration): the probe imports v1's
capture path, target functions, checkpoint store and capture check.

Model. Qwen/Qwen3-0.6B-Base at `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`
(apache-2.0; 28 layers, 16 query and 8 key-value heads, head dimension 128),
receipt `/home/kevin/cotcodec-runs/hf-cache/cotcodec-receipts/qwen3-0.6b-base.json`,
SHA-256 `e7f36f05e6c87ec50b3736cf133fda60775abccb38f60fa9d3c134c432cf46df`,
artifact root `7040f418762c61dd00b540e482527e0d8c8a916cce80eee56408bd10a6179ae0`.
The lane verifies the receipt and the artifact root; the probe refuses any
receipt other than this model at this revision, and a model that does not have
28 layers.

Lane. One job through `scripts/submit_docker_research_job.py`
(`experiments/manifests/q3-k1-throughput-probe-v1/q3-k1-throughput-probe.yaml`):
one H100, 9 minutes, `max_gpu_hours` 0.15, `container_profile: default`, 16
CPUs, 96 GB of memory, seeds [42, 43, 44] bound to `--seeds`
(`seed_binding`), run root
`/home/kevin/cotcodec-runs/translation-supervised-sparse-indexer/k1-throughput-probe-v1`.
The manifest binds no study artifact and the probe refuses a manifest that
does.

## Data

Synthetic token ids only, from NumPy's `default_rng`: uniform over the regular
vocabulary (ids below 151643), every training and evaluation sequence opening
with the registered sink token 151643, seed 42 for the training batches and
the stream-dev sequences, 43 for the evaluation units, 44 for the capture
check, and 52 to 55 for the four concurrent workers. No Belebele text, no K1
bundle, no FineWeb or ParaDocs text and no partition is read. The seeds 42, 43
and 44 passed with `--seeds` are the registered indexer initialisation seeds
(each indexer is initialised by v1's `BlockIndexer.initialised` from SHA-256
of seed, layer and target).

## Arms

The parent process holds no GPU memory. Each arm runs in a child process
spawned the way the v2 entry point spawns its workers, so start-up (process
start, imports, teacher load, indexer initialisation) is measured from the
spawn, apart from the steady-state times. All arms use the registered
determinism settings (deterministic algorithms, TF32 matmuls allowed, no
`torch.compile`). Arms run in this order, each with a timeout:

1. **tolerance** (150 s). The device gates of
   `harness/sparse_indexer_k1_equivalence_v2.py` on one synthetic
   8,192-token sequence through the teacher, at layer 15 with the 18
   registered indexers:

   | Gate | Tolerance |
   |---|---|
   | KL loss, bank against v1's per-indexer forward and `kl_block_loss` on the same targets | max relative difference 1e-3 |
   | Per-indexer gradient-norm (clip) | max relative difference 1e-2 |
   | Every gradient tensor before clipping, per indexer | relative Frobenius difference 1e-2 |
   | Adam step on identical clipped gradients and states, three steps | max relative difference 1e-6 (bitwise reported) |
   | Chunked targets against v1's `sequence_targets` | max relative difference 1e-4, and no mass in a dropped block |
   | Changing one indexer's parameters | every other indexer's loss and gradients bit-identical |
   | Block selection and the U and U_k unions on the device | equal to v1's functions on the CPU, exactly (exact ties and signed zeros included) |
   | One selection unit (34 query rows), `evaluate_unit` against v1's evaluation loop | dense selectors, U, U_k and the random baseline within 1e-3 recall points; indexer columns reported |

   The parameters after one Adam step of the full path are reported, not
   gated (decision 8). A failed gate ends the probe `PROBE_TOLERANCE_FAIL`: no
   rates are reported and no limit exists.
2. **train** (180 s). The binding shard of the registered layout (layers 15
   to 21: 7 trained layers behind a 22-layer teacher prefix) as one worker on
   the GPU: 8 steps of the 18-indexer bank at batch 4 x 8,192 tokens (steps 0
   and 1 excluded from every steady-state mean), one checkpoint save of the
   shard (timed, then deleted), 6 steps with the V1 extension's 6 trainable
   indexers (learning rate 1e-3 for both targets, the other 12 carried; steps
   0 and 1 excluded), and 4 stream-dev KL sequences of 8,192 tokens at batch 1
   (the first excluded). Every step is timed as the training worker times it:
   the teacher capture, each layer (targets, bank forward and backward,
   clipping and Adam for the 4 sequences), each closed by a device
   synchronisation, and the whole step including the loss copy and log. A
   descriptive split of one layer and one sequence follows the 8 steps (the
   targets alone, the targets plus the bank's forward and backward, the
   host's time to enqueue the latter, and the clipping; three repeats, the
   last reported): an enqueue time close to the wall time would show the
   bank launch-bound, which no rate depends on.
3. **eval** (150 s). One worker with 6 indexers per layer on all 28 layers
   (the frozen-learning-rate layout of the audit evaluation): 13 selection-only,
   13 selection plus multiple-choice and 13 multiple-choice-only units at 34
   query rows in contexts of 8,192 tokens (needle of 150 tokens at depth 0.5;
   four options of 24 tokens), interleaved, and 5 selection-only units at 220
   query rows. The first unit of each kind is excluded. The 220-row units are
   descriptive (the per-row slope).
4. **capture** (120 s). v1's smoke capture and eager check
   (`scripts/run_sparse_indexer_phase0a.smoke_capture_check`) on a synthetic
   8,192-token prompt; only its time is used, its numbers are descriptive (the
   v2 smoke gates the real check).
5. **concurrent** (240 s). The four registered shards ([0-7], [8-14],
   [15-21], [22-27]) as four workers started together on the one GPU (the
   resume legs' layout), 6 steps each of the 18-indexer bank (steps 0 and 1
   excluded); each worker's start-up, steady step time and peak memory.

## Outputs

The receipt (`/outputs/probe/receipt.json`) holds every arm's records, the
code digests, the model receipt and preregistration digests, and, when every
arm completed and the tolerance gates passed, the rates (seconds):

| Rate | From |
|---|---|
| `teacher_layer_seq_s` | train: steady teacher capture time / (4 sequences x 22 prefix layers) |
| `layer_step_s` | train: steady sum of the 7 layer times / 7 |
| `layer_step_ext_s` | train, extension steps: the same / 7 |
| `step_overhead_s` | train: steady step time minus teacher and layers (at least 0) |
| `devkl_teacher_layer_seq_s` | train, stream-dev: mean teacher time / 22 |
| `devkl_layer_seq_s` | train, stream-dev: mean sum of layer times / 7 |
| `save_layer_s` | train: the checkpoint save time / 7 |
| `train_startup_s` | train: spawn to the first step |
| `eval_startup_s` | eval: spawn to the first unit |
| `eval_select_s`, `eval_select_mc_s`, `eval_mc_only_s` | eval: mean seconds per unit of each kind |
| `eval_rows` | eval: mean query rows of the measured selection units (34) |
| `capture_check_s` | capture: the check's wall time |
| `concurrent_step_s` | concurrent: the slowest worker's steady step time |
| `concurrent_startup_s` | concurrent: the slowest worker's spawn to first step |

For convenience it also writes the limits and caps that
`derive_limits` gives for these rates and whether the caps with the probe
exceed 8 GPU-hours. The formula itself, and what the limits mean, belong to
the v2 registration; `scripts/derive_sparse_indexer_k1_v2_limits.py`
recomputes them from the rates and refuses a receipt whose stated limits
differ.

## Outcomes

- `PROBE_COMPLETE` (exit 0): every arm completed and every tolerance gate
  passed; the rates and limits are reported.
- `PROBE_TOLERANCE_FAIL` (exit 3): a device gate failed; the later arms do not
  run and no rate is reported. The v2 code is not equivalent enough on the
  device as registered; the defect is investigated and any fix needs new code
  digests and a new probe id.
- `PROBE_INCOMPLETE` (exit 3): an arm failed, timed out or was stopped by a
  signal. No rate is reported. A rerun needs a new id and a new budget line
  from the program owner (D20 gives this probe 0.15 GPU-h).
- A start-up check that fails (seeds other than [42, 43, 44], a preregistration
  or model receipt digest that differs, a ledger row that does not match, a
  study artifact in the manifest, more than one GPU) exits 2 before any work.

Slurm's USR1 (180 s before the 9-minute limit) or a SIGTERM stops the probe at
once: it kills the running arm, writes a `PROBE_INCOMPLETE` receipt and exits
3. The probe holds no state worth saving, so it writes no checkpoint marker
(the lane records `signal_USR1_checkpoint_missing`). The expected wall time is
3 to 5 minutes (central and conservative design scenarios).

## Budget

1 GPU x 9 minutes = 0.15 GPU-h, the cap D20 sets. It is counted in the K1
successor's total that the 8 GPU-hour gauntlet threshold applies to.

## Infrastructure failures and exclusions

The probe is void, with no rate used, when the job does not end COMPLETED with
exit code 0:0, provenance or model verification fails, the receipt's status is
not `PROBE_COMPLETE`, or its orx node lacks its ORX_RESULT line. A void probe
is reported with its receipt; a rerun is a new id.

## Reported regardless of outcome

- The receipt with every arm's records (per-step and per-unit times, start-up,
  save time, peak memory per arm and per concurrent worker), the tolerance
  report (every measured difference, Adam bitwise or not, the GPU name, torch
  and CUDA versions) and the failures.
- When complete: the rates, the derived limits and caps per job, the total with
  the probe and whether the gauntlet applies.
- The 220-row unit time against the 34-row time and the per-layer component
  split (descriptive).

## Design decisions

1. Synthetic tokens instead of the bundle (D20). The probe must not read the
   data whose limits it sets. The training and selection cost does not depend
   on token values; the evaluation's top-k work can depend weakly on the score
   distribution. The v2 smoke re-measures every rate on the registered data
   and gates the main job and the extension against the limits, with 15
   percent headroom for that difference.
2. One binding shard instead of four solo shards. The design review found
   worker 2 (layers 15-21) binding under the batched engine; per-layer rates
   compose to every shard as `4 x prefix x teacher + layers x layer_step +
   overhead`, the same composition the v2 smoke uses, so the probe and the
   smoke project with one formula.
3. Steady state excludes steps 0 and 1, and the first unit of each evaluation
   kind; start-up is measured from the spawn. v1's smoke counted the
   evaluation worker's 15.7 s start-up in its per-unit rate (1.361 s instead
   of 0.533 s per unit), which inflated its projection.
4. 34 query rows for the regular units, at or above the audit mean of 33.2
   (bundle metadata: 289,330 selection rows over 8,710 selection units); the
   formula scales the selection cost up, never down, by the ratio of a unit
   mix's mean rows to the measured rows. The 220-row units (the audit maximum)
   are descriptive.
5. Multiple-choice units are measured (none was in v1's smoke). Options of 24
   tokens: one option is a key-value-cache continuation of a few tokens, whose
   cost is dominated by the cached 8K context, not by the option length.
6. The concurrent arm measures the resume legs' layout (four workers sharing
   one GPU), as the design review asked; v1's R0 needed about 10 minutes
   against a USR1 at minute 5.
7. The capture check is timed with v1's own function on synthetic tokens.
8. The device tolerance gates run before any timing and on the real teacher.
   Both paths run fp32 with TF32 matmuls (registered decision 25 of v1), so
   they differ by accumulation order and occasional TF32 input-rounding
   flips; the thresholds are loose enough for that and tight enough that a
   coupled clip norm, a shared Adam state or a wrong target (all O(1)
   differences) fail. Slot independence and the selection rule are exact. The
   Adam step is elementwise and bitwise on the CPU (tested); on the device
   bitwise equality is reported and the gate allows float32 rounding. The
   parameters after a full step are not gated on the device: Adam's first step
   is about the learning rate times the sign of each gradient element, so a
   rounding difference in a near-zero gradient element flips that element's
   whole update, and the head-gate matrix starts at zero, so its post-step
   value is that update alone; the step on identical inputs and the gradients
   are gated instead (in float64 the post-step parameters are gated at 1e-11).
9. Considered and not built: CUDA graphs (the bank already removes the
   per-indexer launches and host synchronisations; capturing autograd adds a
   memory-pool and determinism path of its own), one teacher forward shared by
   the four workers (cross-process tensors; about 2 minutes of the central
   main projection), context-prefix reuse in evaluation (a key-value-cache
   capture path that would need its own capture gate) and several prompts per
   forward (at most about 5 percent). If the probe's caps exceed 8 GPU-hours,
   the gauntlet decides what happens next, not a silent change of code.
10. One GPU and 9 minutes (0.15 GPU-h, D20), with per-arm timeouts and the
    concurrent arm last, so a slow probe loses the least important arm first
    and reports `PROBE_INCOMPLETE` rather than a partial rate.
11. The probe binds the code it measured: its receipt records the digests and
    the v2 manifest filler refuses limits from a probe that measured other
    code.
