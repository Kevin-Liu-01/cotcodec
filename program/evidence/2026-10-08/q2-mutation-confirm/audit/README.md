# q2-evaluator-mutation-v1, confirm campaign, stage A2: audit sample, packets, open-weight rater, isolated export

Operator record of the audit stage of the frozen `q2-evaluator-mutation-v1`
(ledger row 11, hash `dc39bfa2...`, registration SHA-256 `57dc0092...`,
frozen on main at `65bc2e2`), following section 9 of the registration. A
pre-specified descriptive protocol under D35 and D38; nothing here is
confirmatory. Every container ran from the staged export or a clean clone of
`65bc2e2` (code tree unchanged since the freeze). The isolated Claude rating
is not part of this stage: it runs as its own workflow session whose agents
are the raters only (D38).

| Step | Where | Record |
|---|---|---|
| Audit salt (D34) | host `scratch/audit-salts/confirm-audit-v1/salt.hex`: 32 random bytes as 64 hex characters, file mode 600 in a mode-700 directory holding nothing else, written by `secrets.token_hex` on the host and never printed | its SHA-256 `194ee66ccc11f93c16bffdc7cf54d0b0f5398f35cbdb3541bb9d9d511c40451e` (`sample/sample-summary.redacted.json`, `salt_sha256`); revealed after the isolated ingest |
| Sample, saved baselines, packets | `submit_audit.sh 65bc2e2... confirm-mutants-v1 confirm-controls-v1 confirm-audit-v1 <metric> <LO-VM> 16 reserve-controls-v1` with `Q2M_PREREG_FROZEN` (`check_frozen.py`: frozen, ledger hash `dc39bfa2...`); Slurm 815, CPU only, LO-VM image `f5b4c40e`, 2 min 25 s, exit 0, `--network=none`, no `/dev/nvidia*` | `sample/` (submission, receipt, packet manifest, redacted sample summary), `ops/submit-confirm-audit.log`, `ops/scontrol-815.txt` |
| Source capsule | fresh host clone of `65bc2e2` from a bundle of `main` (`git status` clean, identical to the staged export but for `.git_sha`); `scripts/create_source_archive.py --discovery` | `capsule/source-receipt.json`: schema 3, 3,744 files, `worktree_clean: true`, git tree `9b2477ee...`, archive `a8559f89ea0333cfd2b6bab73c70c45e8a01340f7b098d906968fa5478592e04`; `capsule/archives.sha256` |
| cu129 vLLM overlay | `scripts/build_vllm_overlay_on_h100.sh` (builder `aa43283e...`, extractor `9b4d21a8...`), Slurm 817, one H100, 43 s; base `vllm/vllm-openai@sha256:b18abb2d...` (image `423783aa...`, vLLM 0.31.0 `db9527a4...`) | `overlay/`: image `sha256:7d4595f98601d50f7393c447a1d0618d55cda1b7cf60e2d016ab5c6f47cc872e`, provenance PASS (git `65bc2e2`, source `a8559f89...`), torchcodec 0.17.0 removed as in every earlier build; the refused first attempt (816) in `overlay-816-refused/` |
| Args and image-input doctor | `rater_runner args-doctor --model-dir`, Slurm 819, CPU only (`q2-mutation-cpu.sbatch`), in the overlay image, on the 12 model metadata files, each re-hashed equal to the model receipt (`18c2a128...`, the registered receipt) | `args-doctor-cpu/`: pass, no problems; engine argv as registered (bf16, seed 42, TP 1, `max_model_len` 139,264, 0.95, 8 sequences, no prefix caching, `generation_config vllm`, 40 images); `Qwen3_5MoeForConditionalGeneration` multimodal, 918 image tokens per 100-dpi page (registered estimate 947) |
| Lane manifests | `infra/q2-mutation/run/render_rater_manifest.py --kind audit --audit-id confirm-audit-v1 --gpu-ledger <q2 root>/raters/gpu-ledger.jsonl` from a worktree at `65bc2e2` (uv venv, `uv sync --frozen`); `submit_docker_research_job.py` `--dry-run`, `--test-only` (exit 0), submit | `manifests/`: per shard the YAML, render output, dry run, test-only and submission; `gpu-ledger.jsonl` (the host ledger: this audit's two rows sum to 0.584 GPU-h of the 3.0 cap) |
| Open-weight rater (Qwen3.6-35B-A3B, thinking on) | docker-research lane, `container_profile: vllm`, one H100 per shard, 160 GiB, `--signal=B:USR1@180`: Slurm 823 (shard 000) and 824 (shard 001), concurrently | `open-weight/s000/`, `open-weight/s001/` (receipt, in-lane args doctor, `lane/` records), `open-weight/call-stats.json` (aggregates only), `ops/scontrol-823.txt`, `ops/scontrol-824.transcribed.txt` |
| Isolated export for the Claude rater | `rater_runner export-isolated` run from a local `git archive` of `65bc2e2`, on the two packet shards copied to this machine outside the root (digests verified against the packet manifest) | `isolated-export/` (`iso-manifest.json`, SHA-256 `f9c91d57ca5644ccecbb53ec9b2d48d8b2f7faeb8deb0736dfe06d50255c2b9a`, and the command's output) |

## Sample (`sample/`)

The census (D35; `raters.draw_audit_sample`, seed 42), no fallback: 178
items, `audit_scope.scope = census`, capacity 1,139, planned 0.5833 GPU-h,
and every (stratum, checker family) cell drawn whole.

| Stratum | Items | Cells |
|---|---:|---|
| `fn_equiv` (equivalence mutants the checker fails) | 36 | 35 `compare_pptx_files`, 1 `compare_pptx_files_tolerant` |
| `fp_violation` (violations the checker passes) | 5 | 3 `compare_pptx_files`, 1 `compare_docx_files`, 1 `compare_pptx_files_tolerant` |
| `alt_gate` (alternative solutions the checker passes) | 93 | 90 `compare_table`, 3 `compare_docx_files` |
| `p1_flip` (every P1 flip of the confirm and reserve control runs) | 4 | 3 confirm + 1 reserve, as stage A1 counted |
| `sham` | 40 | 33 gold (one for every audited task), 7 do-nothing |

No `fn_alt` or `fp_extra` candidate exists outside probe-touched cells (as
the A1 preview found). The candidate pool is the 444 evaluable mutants
outside probe-touched cells (255 equivalence, 93 alternative, 91 violation,
5 extra change). Kevin's spot-check list (D9, `raters.human_spot_check`)
holds 25 items. Baselines: 33 saved-start jobs, all saved, none failed; 167
items take the mutation save stage's baseline and 11 the control run's.

`sample-summary.json` lists the four P1 flip task ids, which stay held until
the isolated ingest (the A1 rule), so it is held whole and committed as
`sample-summary.redacted.json`: the same fields with `p1_flip_tasks` replaced
by its count and the full file's SHA-256 (`1a74f5c4...`).

## Packets (`sample/packets-manifest.json`)

Two shards under the 480 MiB study-artifact limit: `packets-000.jsonl` (133
items, 486,306,133 B, `47d17b52f48279e876480dd476b5e5a6f5aa780b931342846db1e3b118fb37b9`)
and `packets-001.jsonl` (45 items, 111,140,718 B,
`f91104b4257ee2087c75494a12d9ba7415a48a2370fcbffbd247c4931de07585`).
Token budget (`audit.fit_packet`, 129,024 tokens): 16 packets shortened in
the registered order (13,507 listing lines not shown, no page dropped), the
largest estimate 128,997 after fitting (178,075 before), none left over the
budget. 22 files reached the 20-page render cap.

## Open-weight rater (`open-weight/`)

Registered settings in both receipts: `enable_thinking` true, `max_tokens`
8,192, temperature 1.0, top_p 0.95, top_k 20, min_p 0, presence penalty 1.5,
repetition penalty 1.0, seed 42, timeout 600 s, 8 in flight; model
`Qwen/Qwen3.6-35B-A3B` at `995ad96e...`, receipt `18c2a128...` verified by the
lane in each job; git `65bc2e2`.

| Shard | Job | Items | Limit (4 + items/10 + 4 min) | Ran | Engine ready | Rating | Outcomes | Calls SHA-256 |
|---|---|---:|---|---|---|---|---|---|
| 000 | 823 | 133 | 22 min (cap 0.367 GPU-h) | 14 min 49 s | 119 s | 699.8 s (11.4 items/min) | 127 `ok`, 6 `thinking_unfinished` | `8c8db1721edc3729e33fb5c6fae30d0ee3c3282b1d33b8563569c5851f2b4b43` |
| 001 | 824 | 45 | 13 min (cap 0.217 GPU-h) | 6 min 21 s | 119 s | 195.9 s (13.8 items/min) | 45 `ok` | `52ba6865308392013c7e010c5e723a1a7b782d3b5de6143421c6936d0f24239f` |

Every item rated once: 178 calls on 178 distinct items (the sample's ids,
which are also the isolated export's; sorted-id SHA-256 `48f9c65f...`), no
retry, every HTTP status 200, `unrated` empty, nothing dropped after a stop.
The 6 `thinking_unfinished` replies reached the 8,192-token limit inside the
thinking (stop reason `length`) and are `unsure` by the registered answer
rule (dev rerate: 1 of 142). Median call 30.2 s, 90th percentile 69.9 s,
longest 149.5 s; generated tokens per reply median 902, 90th percentile
4,122; prompt tokens at most 119,294, inside the 131,072 the window leaves
after the reply. Both jobs ended on their own before the USR1 lead
(`termination.env`: `reason=completed`, `exit_code=0`,
`container_killed_by=none`; the receipts' `stop.signalled` is false), the
engine stopped in 1.1 s and 1.0 s, and no container was left after either
job. No rerun is needed.

## Isolated export (`isolated-export/`)

Isolation root (fresh, on this machine):
`/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/q2m-confirm-iso`.
It holds 178 item directories and nothing else; each holds only
`packet.txt` and `pages/`, every file read-only. The manifest is outside the
root (`.../scratchpad/q2m-confirm-iso-export/iso-manifest.json`) and lists the
item ids in the Anthropic rater's seeded order (`order`), the SHA-256 of every
exported file, directory listing and rebuilt request body, and each item's
rendered-prompt SHA-256. Registered prompt template
`harness/q2_mutation/templates/isolated_rater_prompt.txt`, SHA-256
`0e9d4eb6597c347d40db7f8ae150e3345fc8a88820d6e8501d02543c9ccbed44` (the pin);
`RATER_PROMPT_V1` `c4cf81c9...`, isolated instructions `1bd8f98d...`, answer
line `7ab894f2...`, all as in the development export. No sample, label,
verdict or rater output is on the rating side.

## GPU time (physical, scontrol RunTime x 1 H100)

| Job | What | Limit | Used |
|---|---|---|---|
| 816 | overlay build, refused by the extractor before any build (below) | 5 min | 1 s |
| 817 | overlay build | 5 min | 43 s |
| 823 | open-weight rater, shard 000 | 22 min | 889 s |
| 824 | open-weight rater, shard 001 | 13 min | 381 s |

1,314 s = **0.3650 GPU-h** (rater 0.3528 of the 3.0 GPU-h cap, with 0.584
allocated in the ledger; overlay 0.0122 of its 0.167, the two 5-minute limits
together being the registered 10 minutes). With the pre-freeze development
rater work (0.574 GPU-h) the experiment has used 0.939 GPU-h of its 4.52.
Jobs 815 and 819 requested no GPU.

## Operational notes

1. Overlay job 816. The first capsule receipt was written with
   `--ref 65bc2e2...`, so it recorded `selected_ref` as the commit; the
   registered extractor accepts only `HEAD` and refused the receipt (exit 2
   after 1 s, before any image build). The capsule was written again from the
   same clone at `HEAD` = `65bc2e2` (the same archive SHA-256 `a8559f89...`,
   receipt `e8aabe25...`), validated by the extractor on the CPU, and the
   build ran as 817 under a new build root (`overlay-65bc2e2bf7bb-r2`; the
   builder refuses to reuse one). Both attempts are reported (section 8).
2. Job 824 had left slurmctld by collection time (accounting storage is
   disabled on this host); its record is transcribed from `scontrol` output
   read shortly after it ended and agrees with the lane's `job.env` and
   `termination.env`.
3. Other jobs without a GPU request shared the host (813 and 825
   `cotcodec-build-arch-image`, 813 from the q3-dense-v2 run root; 814 and
   826 `q3v2-host-suite`; 818 `q3v2-sigrace`); none was touched. No other
   GPU job ran, and every GPU was idle at each preflight
   (`ops/preflight.log`).

## Held on the host until the isolated ingest (`held/SHA256SUMS`)

`~/cotcodec-runs/stage0/q2-evaluator-mutation/scratch/held-after-isolated-ingest-confirm-v1/`:
`confirm-audit-v1/` (sample with labels and verdicts, items, baseline jobs,
spot-check list, full sample summary) and `open-weight/` (the two shards'
per-item call records); the host keeps the same list as `SHA256SUMS.audit`
beside the A1 `SHA256SUMS`. Not committed (document content): packets,
saved baselines, the isolated export, raw responses and engine logs (host
run directories and this machine's scratchpad).

## Next (as written at stage A2; done in stage B below)

The isolated Claude rating over the export as one workflow session of rater
agents only (D38), `collect-transcripts`, `ingest-isolated`, `audit
summarize` with the two open-weight calls files; then the salt and the held
files are released, the registered analysis runs, and Kevin adjudicates the
pool and does the spot check (D9).

## Stage B: isolated Claude rating, collector, ingest, salt, summary

Commands ran on this machine from a fresh `git archive` of `65bc2e2` (pins
equal the frozen block), Python 3.13.14, standard library only, no GPU. The
analysis is in `../results/README.md`.

| Step | Record |
|---|---|
| Isolated Claude rating: workflow run `wf_138e30b5-c1a`, one session whose agents are the raters only, labels `rate:0`-`rate:177`, one agent per item started with the registered template rendered for it (`claude-isolated/q2m-confirm-raters.js`, SHA-256 `659040bf...`), 2026-10-08 11:28:02Z, 532.9 s; every agent answered, none was interrupted, the run was never resumed | `claude-isolated/rating-run.json`: journal `bb12d4bd...` (1 launched, 178 started, 178 results), 21,100,472 tokens, 2,319 tool calls; the returned list in `handed-over-answers.txt` (ids and answers: 141 accept, 37 reject), equal to the journal's 178 results, every returned `item_id` equal to its item |
| Collector (D38): `rater_runner collect-transcripts` on the run directory with the export manifest `f9c91d57...` | `claude-isolated/collection.json` (`3a48f6f0...`): 178 transcripts mapped to 178 items by their rendered task turn, 178 answered, no unmappable agent, no exported item without a transcript, no second attempt (`collect-stdout.json`) |
| Answers | the run's returned ratings as one `<item_id>.json` per item (`{item_id, answer, reason}`; the workflow's extra `item_id_returned` key, equal to `item_id` for all 178, is not a registered answer key and was dropped); kept outside the repository (reasons quote documents), each file's SHA-256 in `receipt.json` |
| Ingest: `rater_runner ingest-isolated` with both packet copies (re-hashed `47d17b52...`, `f91104b4...`), the manifest, the isolation root (every item tree re-hashed), the answers, the collected transcripts and the collection | `claude-isolated/calls.jsonl` (`2120e6ce...`), `receipt.json`, `rerate.json`, `ingest-stdout.json`: **177 `ok`, 1 `isolation_void`**; answers 140 accept, 37 reject, 1 unsure; model `claude-opus-5-5` only; no relay frame (none expected: the run was never resumed), so `rerate.json` lists no item and there is no re-rate; attachment types are the 15 registered ones only (178 each of `auto_mode`, `credential_org`, `date`, `environment`, `instructions`, `mcp_instructions_delta`, `model`, `remote_session_change`, `session_context`, `skill_listing`, `structured_output`; 356 `deferred_tools_delta`, 356 `prompt_snapshot`, 888 `total_tokens_reminder`, 153 `read_truncation_notice`) |
| Salt revealed (D34) | `salt.hex`; `salt-check.json` (`salt_check.py`): SHA-256 `194ee66c...` equals the committed digest, and all 178 sample item ids recompute from it with `raters.opaque_item_id`; the sample ids equal the exported ids |
| Held files released (section 16) | `released/`: the A2 held set (sample, items, baseline jobs, spot-check list, full sample summary, both open-weight calls files), every file equal to `held/SHA256SUMS` (7 of 7), and the host's `SHA256SUMS.audit` byte-equal to it; the A1 set is in `../results/released/` |
| Audit summary: `audit summarize` with the Claude calls and the two open-weight calls files (10,000 resamples, seed 42) | `audit-summary/` (`audit-summary.json`, `decisions.jsonl`, `adjudication-pool.jsonl`, `summarize-stdout.json`); no relay frame in any calls file |
| Diligence aggregates (not a void condition) | `claude-isolated/transcript-stats.json` (`transcript_stats.py`) |

**The one void.** Item `fd455942d783ba01` (order index 76): its agent read
`packet.txt`, then issued one Read of a mistyped path outside its item
directory (`<session root>/pages/p01.png`, the item directory left out),
which does not exist and returned "File does not exist"; it then read its
own page images and answered through the structured output. The registered
audit counts a Read of any path outside the item directory, a missing path
included, as a breach, so the item is `isolation_void` (`unsure`) as
registered; its structured answer is not used. With the open-weight
rater's accept it is a split item and is in Kevin's pool. The void
stands; the re-rate of D38 covers only relay-frame voids.

Diligence: 2,141 Read calls and 178 structured answers, no other tool; 3,192
agent turns, all `claude-opus-5-5`; 1,453 of 1,457 exported page images
read, 176 of 178 agents read every page image; 153 agents received a read
truncation notice (a packet longer than one Read shows).

Results (`audit-summary/audit-summary.json`): κ **0.343** on 138 real items
(raw agreement 82.6%); sham accuracy Claude 0.90, Qwen 0.975; 24 of 138
real items unresolved; no gold-defect task decided (4 gold shams split);
P1 flips 3 accepted, 1 rejected by both raters; K3 fires for both groups and
for κ, K4 fires (reported only, D35). **Adjudication pool: 34 items** (24
splits, 6 concordant contradictions, 4 split gold shams), ids only in
`adjudication-pool.jsonl`; **human spot check: 25 items**
(`released/confirm-audit-v1/spot-check.jsonl`), 7 of them also in the pool.
Both are Kevin's and pending. The released sample and decisions name labels
and decisions: Kevin adjudicates from the blind packets before reading them.

Not committed (document text): the transcripts, the answer files with
reasons, the raw responses, the packets and the isolated export.

`SHA256SUMS` covers every file here.
