# D34 development rerate: Qwen3.6-35B-A3B with thinking on (exploratory)

Decision D34 (program/decisions.md) answers the fourth review of the fifth
draft of `q2-evaluator-mutation-v1`: D27's consequence fired (development κ
0.270 with the isolated Claude rater and the thinking-off open-weight rater),
so the open-weight rater gets one retry with thinking on, and the audit gains
gold shams for every K3 task, a gold-defect rule, a wider adjudication pool, a
text-level difference for new-file end states, a save-drift rule, an off-slide
rule for `pptx.viol.delete_bound_shape`, salted item ids and a registered agent
prompt. This directory is the development evidence: the dev campaign rebuilt
with the new operator rule, a new dev audit (new sample, new salt) drawn from
it, every item rated by the thinking-on rater, and the items exported for the
isolated Claude rater. Dev split only; nothing here is a result of the
registration, which is not frozen.

| Step | Where | Record |
|---|---|---|
| Operator revalidation, synthetic documents | Slurm 717, CPU, LO-VM image `f5b4c40e`, code `34046e0` | `operators-revalidation/` (131 planned, 131 applied, 130 admitted, as jobs 431 and 684; catalog `3a5ff949`) |
| Dev campaign rebuild | `dev-mutants-v9` (Slurm 714-716, CPU), code `34046e0` | `ops/` (receipts, submission), `dev-mutants-v9-aggregates/` (report, build, save-stage, recheck and notes summaries): 275 planned, 271 admitted, 215 evaluable, the same counts as v8 |
| Audit sample, baseline saves, packets | `dev-audit-v4`, Slurm 720, CPU, LO-VM image, from `dev-mutants-v9` and `dev-controls-v9` | `audit/` (receipt, submission, sample summary with the salt's SHA-256, packet manifest: one 455 MB shard `5598e755...`, 142 items, 16 shortened in starting-file listings only); `packet-stats.json` (new-file text differences, save-drift counts; packet files only) |
| Source capsule | host clone of `34046e0` | `capsule/source-receipt.json` (archive `43995eb1...`, 3,379 files, worktree clean) |
| cu129 vLLM overlay | Slurm 718, one H100, 44 s | `overlay/` (image `sha256:d5fd5cd7...`, provenance PASS) |
| vLLM args and image-input doctor | Slurm 719, CPU only, in the overlay image, model metadata files whose SHA-256 match the receipt | `args-doctor-cpu/` (pass; 918 tokens per page; the thinking-on request fields parse) |
| Open-weight rater, thinking on | Slurm 722, docker-research lane, `container_profile: vllm`, one H100, 12 min 57 s (limit 28 min, cap 0.467 GPU-h from the GPU ledger) | `manifests/` (manifest, dry run, test-only, submission, `gpu-ledger.jsonl`), `open-weight/` (receipt, in-lane args doctor), `open-weight/lane/` |
| Isolated export for the Claude rater | `rater_runner export-isolated` at `34046e0`, outside the repository | `isolated-export/` (manifest: item ids in the Anthropic rater's seeded order, digests, each item's rendered-prompt SHA-256, the prompt template's SHA-256) |
| Summary | `summarize_rerate_v4.py` on the host | `summary.json` (aggregates only) |

GPU time: 0.0122 GPU-h (overlay, 44 s) + 0.2158 GPU-h (rater, 12 min 57 s) =
0.2281 GPU-h, inside the 0.5 GPU-h D34 allows (allocated: the 0.467 rater cap
in the ledger plus the 44 s overlay, 0.479).

The rater job ended on its own: every item rated before the lane's USR1
(`termination.env`: `reason=completed`, exit 0), engine stopped in 1.2 s, no
container left after the job. Engine ready 115 s after the workload started
(KV cache 409,539 tokens at 0.95 memory utilization, `max_model_len`
139,264), 142 items in 590 s (14.4 items per minute; 334.7 generated and
13,685 prompt tokens per second), median call 28 s, longest 134 s, no retry.
141 replies `ok`, 1 `thinking_unfinished` (cut at 8,192 tokens); generated
tokens per reply median 1,042, 90th percentile 2,822.

Findings (exploratory, one rater; `summary.json`):

- Shams 20 of 21 right (gold 14 of 15, do-nothing 6 of 6); the P1 flip
  accepted.
- Equivalence 57 accept / 2 reject / 1 unsure; alternative 27 / 1; violation
  14 accept / 12 reject (thinking off: 19 / 7); extra change 0 / 6 (thinking
  off: 5 / 1). Thinking makes the rater reject more should-fail mutants, but
  it still accepts more than half of the violations.
- If the Claude rater agreed with every label, κ would be 0.578 (thinking
  off: 0.27), with 18 of 121 real items split, still below the registered
  0.6.
- Projection with the D27 isolated Claude answers on the 119 real items
  matched by task, operator and site: κ 0.486, raw agreement 0.815 (thinking
  off on the same items: 0.289 and 0.773); 16 of the 22 splits are Claude
  reject / Qwen accept. The D27 answers were given on the D27 packets, which
  lacked the new-file text differences and the drift rule, so this is a
  projection; D34's κ condition is decided by the isolated Claude answers on
  these packets (pending).
- Throughput with thinking on sets the confirm cap re-registered in section 9
  of the preregistration (3.0 GPU-h for the 841-item maximum).

The off-slide rule does not reach the fourth review's item afb440d9: that
mutant deleted shape 19 of 4ed5abd0's slide 2 ('Google Shape;119;p12'), which
lies wholly on the slide; the 78% figure matches shape 20, which the rule now
excludes with shape 0. Shape 19 is deleted again in `dev-mutants-v9`.

Held on the host until the isolated Claude answers on these items are
ingested (no sample, label or other rater's answer on the rating side before
the ingest, section 9): the audit sample, spot-check list, item list and
baseline jobs, the open-weight call records and the label-bearing export of
`dev-mutants-v9`. Their SHA-256 are in `held/SHA256SUMS`; they are at
`~/cotcodec-runs/stage0/q2-evaluator-mutation/scratch/held-after-isolated-ingest-v4/`.
The audit's salt is on the host only (`scratch/audit-salts/dev-audit-v4/`,
mode 600); its SHA-256 is in `audit/sample-summary.json` and it is revealed
after the ingest. Not committed (document content): packets, items, saved
baselines, the isolated export, raw responses, the engine log.
`SHA256SUMS` covers every file here.
