# D27 development rerate: Qwen3.6-35B-A3B on the rebuilt dev audit (exploratory)

Decision D27 (program/decisions.md) upgrades the open-weight rater of
`q2-evaluator-mutation-v1` and restricts two pptx operators. This directory is
the development evidence for both: the dev campaign rebuilt with the
restricted operators, a new dev audit drawn from it, every item rated by the
new rater, and the items exported for the isolated Claude rater. Dev split
only; nothing here is a result of the registration.

| Step | Where | Record |
|---|---|---|
| Image-input check (vLLM 0.31.0, Qwen3.6-35B-A3B) | Slurm 677-680 (CPU probes) and 685 (the new `args-doctor --model-dir` run from the staged tree in the earlier overlay) | `image-doctor-probes/`: the registry resolves `Qwen3_5MoeForConditionalGeneration` with `supports_multimodal`; the model config keeps image input; vLLM's `Qwen3VLMultiModalProcessor` turns one 850 x 1100 page into 918 image tokens (registered estimate 947) |
| Operator revalidation, synthetic documents | Slurm 684, CPU, LO-VM image `f5b4c40e`, code `4eba530` | `operators-revalidation/` (131 planned, 131 applied, 130 admitted, as job 431; catalog `07e50a6f`) |
| Dev campaign rebuild | `dev-mutants-v7` (Slurm 681-683): 2 of 17 targets lost to a UNO bridge fault in the initial save, scoring cancelled; `dev-mutants-v8` (Slurm 688-690), code `4eba530` | `ops/` (receipts, v7 build summary), `dev-mutants-v8-aggregates/` (report, build, save-stage, recheck and notes summaries) |
| Audit sample, baseline saves, packets | Slurm 700, CPU, LO-VM image, from `dev-mutants-v8` and `dev-controls-v9` | `audit/` (receipt, submission, sample summary, packet manifest: one 409 MB shard `4a56ba5e...`, 133 items, none shortened) |
| Source capsule | host clone of `84f23e0` (the code tree of `4eba530` plus docs) | `capsule/source-receipt.json` (archive `6a0ceb1c...`, 2,553 files, worktree clean) |
| cu129 vLLM overlay | Slurm 686, one H100, 46 s | `overlay/` (image `sha256:33fb48b7...`, provenance PASS) |
| vLLM args and image-input doctor | Slurm 687, CPU only, in the overlay image, model metadata files whose SHA-256 match the receipt | `args-doctor-cpu/` (pass; `qwen36-meta.digests.json`) |
| Open-weight rater | Slurm 702, docker-research lane, `container_profile: vllm`, one H100, 6 min 56 s (limit 20 min, cap 0.334 GPU-h from the GPU ledger) | `manifests/` (manifest, dry run, test-only, submission, `gpu-ledger.jsonl`), `open-weight/` (receipt, in-lane args doctor), `open-weight/lane/` |
| Isolated export for the Claude rater | `rater_runner export-isolated`, outside the repository | `isolated-export/` (manifest: item ids in the Anthropic rater's seeded order and digests only) |
| Summary | `summarize_rerate.py` on the host | `summary.json` (aggregates only) |

GPU time: 0.0128 GPU-h (overlay, 46 s) + 0.1156 GPU-h (rater, 6 min 56 s) =
0.1284 GPU-h, inside the 0.5 GPU-h D27 allows (allocated: 0.334 rater cap in
the ledger plus the 46 s overlay).

The rater job ended on its own: every item rated before the lane's USR1
(`termination.env`: `reason=completed`, exit 0), engine stopped in 1.3 s, no
container left after the job (`docker ps -a --filter name=cotcodec-702` empty).
Engine ready 133.5 s after the workload started (KV cache 406,528 tokens at
0.95 memory utilization with image input), 133 items in 210.5 s (37.9 items
per minute, 35,600 prompt tokens per second; prompts up to 110,505 tokens,
median 46,294), 133 replies, all `ok`, none cut at 256 tokens; 68 replies are
the answer word alone.

Findings (exploratory, one rater; `summary.json`):

- Shams 12 of 12 right (the 9B rater: 6 of 8 rated); the P1 flip accepted.
- Equivalence 57 accept / 3 reject; alternative 28 / 0; violation 19 accept /
  7 reject; extra change 5 / 1. The rater no longer rejects golds and
  equivalent edits, but it accepts most should-fail mutants: one-letter text
  edits, deleted bound paragraphs and shapes, dropped character formats.
- If the Claude rater agreed with every label, κ would be 0.27 (it was 0.48
  for the 9B rater on its 90 items), with 22% of real items split. Against
  the earlier shared-directory Claude answers (not blind) on 109 matched real
  items: κ 0.34, raw agreement 0.80 (the 9B rater: κ 0.54 on the 73 of them it
  rated). Both are below the registered 0.6, so on the D27 rule the design
  goes back to review unless the isolated Claude answers differ greatly.

Held on the host until the isolated Claude answers on these items are
ingested (no sample, label or other rater's answer on the rating side before
the ingest, section 9): the audit sample, spot-check list and item list, the
open-weight call records and the label-bearing export of `dev-mutants-v8`.
Their SHA-256 are in `held/SHA256SUMS`; they are at
`~/cotcodec-runs/stage0/q2-evaluator-mutation/scratch/held-after-isolated-ingest/`.
Not committed (document content): packets, items, saved baselines, the
isolated export, raw responses, the engine log. `SHA256SUMS` covers every file
here.
