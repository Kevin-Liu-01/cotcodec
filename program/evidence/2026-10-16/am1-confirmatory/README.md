# am1-memory-credit-v1: operations record of the confirmatory run (artifact, image, selftest, GPU job, hand-check sample)

**CONFIRMATORY run of a frozen registration; operations only.** This directory records how the
registered run of `program/preregistrations/am1-memory-credit-v1.md` (frozen in
`program/preregistrations/ledger.jsonl`, row 23, `git_head_at_freeze` `c50017af`; freeze commit
`9ad36b10`, the commit that adds the row) was operated: the post-freeze steps of the
registration's section 16 and the registered commands of section 17, up to the blind hand-check
sample. **No analysis ran and no outcome was read.** `analyze` and `aa` (section 17) have not
run; the hand-check sample has not been labelled; G2 is PENDING. The operator who ran this did
not draft the registration.

**Status: the registered GPU job ran once and completed; the blind hand-check sample is drawn,
unlabelled.** Job 1458 (2 H100, Slurm limit 90 minutes) COMPLETED 0:0 in 00:45:49, with every
phase and every worker complete, both reader passes finished (190,156 of 190,156 requests each)
and neither stopped by its 3,600 s budget, so the reader-cap contingency of section 8 did not
arise; every primary-judge, second-judge and attention item finished. Nothing was rerun. GPU use:
1.5444 physical GPU-h (build 0.0172, job 1.5272) of the registration's 3.1 cap. The directory
date (2026-10-16) is the one the orchestrator assigned; every step ran on 2026-10-15 UTC.

What remains, in the registration's order (section 17): the 120-item sample
(`~/cotcodec-runs/stage0/am1-memory-credit-v1/hand-check-sample.jsonl`, SHA-256
`cebfe191...`, no judge label in it) is labelled blind from question, reference answer and reply
alone; the labels file's SHA-256 is committed; then `analyze --hand-labels ... --hand-labels-sha256
...` and `aa` run on the host with `--run-dir .../runs/main/1458/am1` and
`--expected-evidence-sha256 f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7`.
Under D9 and D111 an agent labels unless Kevin chooses to; the report says which. D111's
disclosure applies to every result of this run: it carries no gauntlet score, and blind
discrimination and the two provider-distinct reviews did not run.

## What ran (2026-10-15 UTC, host `fal-h100-01`)

| Step | What | GPUs | Time (UTC) | GPU-h | Outcome |
|---|---|---:|---|---:|---|
| source | clean clone of the freeze commit on the host from a git bundle; section 17's pins re-hashed | 0 | 03:17 | 0 | 19 of 19 pins match; `git archive` of `9ad36b10` byte-identical on Mac and host |
| capsule | `create_source_archive.py --discovery` on the clean clone (`ops/am1c-capsule.sh`) | 0 | 03:17 | 0 | `a46be5ed...`, 12,492 files, carries ledger row 23 |
| artifact | the registered `memcredit_study_prepare.py artifact ... --split heldout` (`ops/am1c-artifact.sh`, login node, outside Slurm) | 0 | 03:18:47-03:18:52 | 0 | exit 0; 347 questions, `f23bca04...`; rebuild byte-identical |
| 1454 | cotcodec-vllm cu129 overlay build from the capsule (`ops/am1c-build-vllm-overlay.sh`) | 1 | 03:19:02, RunTime 00:01:02 | 0.0172 | COMPLETED 0:0, `sha256:abcd2b56...`, build status PASS |
| 1455 | post-build CPU selftest of the baked `9ad36b10` with the held-out artifact mounted, under the registration's config (`ops/am1c-selftest-cpu.sbatch`, no GRES) | 0 | 03:20:19, RunTime 00:02:20 | 0 | selftest exit 0 (`ok`: 190,156 reader prompts, 107-1,633 tokens, fit; thinking disabled; 694 of 694 pools' memory spans ordered and complete; 1,387 judge prompts fit both judges' windows; attention code on Qwen3-0.6B-Base on CPU ok); plan exit 0 (347 questions, 694 pools, 190,156 requests: 177,664 table, 11,104 swap, 1,388 reorder; 1,040 validation items) |
| tests | `tests/test_memcredit_study.py` and `tests/test_memcredit.py` on the host clone (`uv run --locked --offline --extra dev`) | 0 | 03:22 | 0 | 80 passed |
| 1458 | **the registered GPU job** (`ops/am1c-submit-main.sh`; manifest `manifests/main-9ad36b10.yaml`) | 2 | 03:23:39-04:09:28, RunTime 00:45:49 | 1.5272 | COMPLETED 0:0; lane `reason=completed`, no signal, no checkpoint marker, container not killed |
| hand sample | the registered `memcredit_analyze.py hand-sample` (`ops/am1c-hand-sample.sh`, login node) | 0 | 04:12 | 0 | 120 items, SHA-256 `cebfe1911deeab24f139beebf41bf327403014254dfd43ada4fb78f061ebf94c`; fields `item_index`, `question_id`, `question_type`, `question`, `reference_answer`, `reply`, `reply_sha256` only (no label); read-only, host only |
| | **total** | | | **1.5444** of the 3.1 cap | |

Run times are `scontrol` RunTime. The submissions (1454 and 1458) were made by the preflight
script with no other GPU job of this program queued or running and enough free H100s in Slurm
(`ops/preflight.log`, section 11).

## Identities

| Item | Identity |
|---|---|
| Code | the freeze commit `9ad36b10dcbd324647e4a98c3a150f954f7123f6` (tree `5c954d2d`); every file of section 17 re-hashed on the operator's Mac and on the host clone: 19 of 19 pins match (`ops/pins.sha256`, with the registration file `51d0abb1...`, the ledger row's SHA-256) |
| Host source | a clean clone of a git bundle of the freeze commit (`334c88fe...`, full history) into `~/cotcodec-runs/stage0/am1-memory-credit-v1/checkout`, detached at `9ad36b10`, `git status` empty before and after every step; `git archive --format=tar 9ad36b10` gives SHA-256 `8806cd7b6c78030e9a6f958cf6894ad549c8635f17f0d3bed4fd0d66c1112204` on both the operator's Mac (git 2.55.0) and the host clone (git 2.34.1). No working-tree tar was made |
| Source capsule | `scripts/create_source_archive.py --discovery` on that clone: `a46be5ed22ff177c4e789e0dde7197673cbc62ee1e894ed3dbb8e7c7e8de6077`, 12,492 files, data excluded, git `9ad36b10`; it carries the ledger row (`builds/source-receipt-9ad36b10.json`, `file_manifest` omitted) |
| Image | `cotcodec-vllm:a46be5ed-cu129-overlay`, `sha256:abcd2b56eddd61ea7cc9243122ffa615bfcfdec4cc83e0bf257aa06e626ed0ee`, built offline by `scripts/build_vllm_overlay_on_h100.sh` (builder `aa43283e...`, extractor `9b4d21a8...`, both the pinned files) from that capsule: vLLM 0.31.0 (`db9527a4`) on `vllm/vllm-openai@sha256:b18abb2d...` (base id `sha256:423783aa...`), as in the pilot (`builds/vllm-overlay-9ad36b10-build-receipt.json`) |
| Data | LongMemEval-S `xiaowu0162/longmemeval-cleaned` @ `98d7416c`, `longmemeval_s_cleaned.json`, SHA-256 `d6f21ea9...` checked before the build, MIT; on the host since Step 0 (D1) |
| Study artifact | the registered `memcredit_study_prepare.py artifact` command under the registration's config, `--split heldout`, from the clean clone: SHA-256 `f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7`, 12,669,196 bytes, 347 questions (the confirmatory set; the script checked the split file, held-out and confirmatory digests and the ledger row). Rebuilt with the same command into a scratch path: byte-identical (copy deleted). Read-only; host only. Text-free summary `prepare/pools-summary-9ad36b10.json.gz` (`7e2a73cf...` uncompressed) |
| Models | the lane verified the judge `Qwen/Qwen3-32B` @ `9216db57` (receipt `06e4a7e9...`, artifact root `8fcd9106...`); the driver re-verified the reader `Qwen/Qwen3-8B` @ `b968826d` against its full receipt in `cotcodec-receipts-cpu-lane` |

## Job 1458: the registered command and the per-job checks

The lane ran exactly section 17's command in the image above, with the artifact mounted
read-only at `/inputs/study-artifact.json` and hash-bound by the lane (`job.env`
`study_artifact_sha256`, `jobs/1458-main/study-artifact.sha256`):

```
python scripts/memcredit_study.py run --config experiments/am1/am1-memory-credit-v1.yaml \
  --seeds 42 43 44 --output-dir /outputs/am1 --allocation-minutes 90 \
  --evidence /inputs/study-artifact.json \
  --expected-evidence-sha256 f23bca047dc7246c5a8db12f67a76a2ea36304d8669dc5c62ae6c42821f73eb7
```

Slurm gave it host GPUs 2 and 3 (UUID prefixes `a485003c`, PCI bus 0x63, and `0524ae85`, bus
0x64); D110's other project held GPUs 0 and 1 throughout (jobs `transcreate-*` 1450 and 1452
running, 1451 and 1453 pending on dependencies), untouched. Lane checks: provenance PASS (git
`9ad36b10`, source `a46be5ed...`), container doctor PASS (2 visible H100), the judge's model
verification by the lane, the batch script `2a10c9c7...` (the pinned file). Driver:
`claim_level` confirmatory, split heldout, 347 questions, 190,156 reader requests, deadline
04:50:10Z from `job.env`, the reader re-verified file by file in 12.0 s, no signal.

| Phase (start) | Worker | GPU | Engine init | Pass | Requests finished | Pass wall | Finish reasons | Prefix cache |
|---|---|---|---:|---|---:|---:|---|---:|
| reader (03:24:41) | `reader-gpu0` | `a485003c` | 29.3 s | canonical (smoke 16 ok) | 190,156 of 190,156 | 1,281.4 s | stop 189,288, length 868 | 61.3% |
| | `reader-gpu1` | `0524ae85` | 29.5 s | shuffled, seed 43 (smoke 16 ok) | 190,156 of 190,156 | 2,296.8 s | stop 189,288, length 868 | 21.4% |
| judge (04:06:10) | `judge32-gpu0` | `a485003c` | 36.8 s | canonical | 10,230 of 10,230 | 72.6 s | stop 10,230 | 76.9% |
| | `judge32-gpu1` | `0524ae85` | 36.8 s | shuffled | 10,230 of 10,230 | 83.4 s | stop 10,230 | 72.9% |
| extra (04:08:26) | `judge8-gpu0` | `a485003c` | 28.0 s | canonical | 10,230 of 10,230 | 16.3 s | stop 10,230 | 77.9% |
| | `attention-gpu1` | `0524ae85` | 7.3 s load | HF eager attention | 694 of 694 pools ok | 44.5 s | | |

The per-job checks, all met:

- every phase `complete`, every worker `complete` with exit 0, none killed (`summary.json`,
  `done.json`); the job exit code 0 and the lane's `reason=completed`;
- both reader passes finished every request with `finish_reason` stop or length, `aborted`,
  `not_started` and `unmatched` 0, and `stopped_by` none: neither reader pass was stopped by its
  3,600 s budget (1,281 s and 2,297 s), so the reader-cap contingency (sections 8 and 11) does
  not apply and nothing about a rerun arises;
- the judge items were written from the GPU-0 reader pass: 10,230 (9,190 distinct reader items
  and 1,040 validation items), and both primary-judge passes and the second judge finished all
  of them; no log-prob was missing in any pass;
- the attention forward succeeded on 694 of 694 pools (attention masses `[694, 36, 32, 8]`);
- the reader passes ran within the registration's time estimates (section 11: about 1,350 s
  canonical, 2,400-2,700 s shuffled); the job ended 41 minutes before its deadline.

The driver's closing A/A identity summaries (`summary.json`, `identity`) were staged but not
read by the operator: G1, like every gate and verdict, is computed by `analyze` and the A/A
report by `aa`, which have not run.

## Deviations and disclosures

No deviation from the registration's commands, seeds, config, caps or contingency rules. Operator
details that the registration does not fix:

- **Source transfer.** The host got the freeze commit as a clean clone of a git bundle (as the
  pilot did), not as an extracted tar, because the capsule script needs a git checkout; the
  capsule it made is itself a `git archive` of `9ad36b10`. The equality of `git archive
  --format=tar 9ad36b10` on the Mac and on the host clone (`8806cd7b...`) shows the host tree
  is the freeze commit's. No macOS tar touched any input.
- **Artifact rebuild.** After the registered build, the same command was run once more into a
  scratch path as a determinism check (the pilot built its artifact twice too); the copy was
  byte-identical and was deleted. Not part of section 17's commands; nothing depends on it.
- **The CPU selftest** passes `--config experiments/am1/am1-memory-credit-v1.yaml` to `selftest`
  and `plan` (the driver's default config is the pilot's, which refuses a held-out artifact),
  runs the image's baked code (post-build), and drops the pilot's in-image `pytest` step (the
  image has no pytest; the pilot's selftests recorded that step failing). The tests ran on the
  host clone instead: the first invocation, without the `dev` extra, found no pytest
  (`ops/pytest-host-9ad36b10-without-dev-extra.txt`, kept); with `--extra dev`, 80 passed.
- **CPU work outside Slurm.** The capsule, the artifact, the tests and the hand sample ran on the
  login node outside Slurm, for seconds each, as in the pilot. D110's other project ran its two
  inference jobs on GPUs 0-1 throughout; their CPU load was not measured.
- **Dates.** Everything ran on 2026-10-15 UTC; the evidence directory carries the date the
  orchestrator assigned (2026-10-16).
- **Blinding.** The operator read no judge label, reply, reference answer or sample item, and
  did not read the driver's A/A identity summaries; the hand-sample command prints only the item
  count, and only the sample's field names were checked (no label field). The reader passes'
  per-request finish reasons and totals (`<pass>.json.gz`) and the attention worker's pool
  records were read as completion checks.

## Files

- `ops/`: the operator scripts run on the host (`am1c-*.sh`, `am1c-selftest-cpu.sbatch`), the
  pins file, `jobs.log` (every step with UTC times), `preflight.log` (the queue, Slurm's GPU
  allocation and `nvidia-smi` before each GPU submission), and the host test logs.
- `prepare/`: the artifact build's stdout and the rebuild's, the prepare log (digests), the
  text-free pools summary.
- `builds/`: the overlay build receipt and its source-validation, provenance and fixup records,
  the build's Slurm log and `scontrol`, the source capsule receipt (`file_manifest` omitted).
- `selftests/`: the post-build CPU selftest of the image with the held-out artifact mounted
  (`exits.txt`, `study-selftest.json`, `study-plan.json`), its Slurm log and `scontrol`.
- `manifests/`: the GPU job's lane manifest, dry run, test-only output and submission.
- `jobs/1458-main/`: lane records (job, termination, manifest, command, model and provenance
  verification, GPU prolog, container doctor, `scontrol`, the lane's Slurm log), the batch
  script's and the mounted artifact's SHA-256; `am1/` with the driver's `summary.json` and
  `environment.json`, GPU samples, worker logs, per-worker records (`session.json`,
  `done.json`, `worker-progress.jsonl`, per-pass metadata `<pass>.json.gz`, `attention.json` for
  the attention worker) and the SHA-256 of every raw pass file, and a text-free copy of the judge
  items (`judge-items-public.json.gz`: indices, question ids, sources, reply SHA-256).
- `hand-check/`: the hand-check sample's SHA-256 and the command's stdout (the item count).

Raw outputs stay on the host under `~/cotcodec-runs/stage0/am1-memory-credit-v1/`
(`runs/main/1458/am1/`): token ids, log-probs and reply texts, the judge items with replies, the
study artifact and the hand-check sample never leave it (registration section 12).
