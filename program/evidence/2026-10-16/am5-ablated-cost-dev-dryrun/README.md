# am5-ablated-cost-v1: the development dry run (EXPLORATORY, before the freeze)

**EXPLORATORY. DEVELOPMENT DATA ONLY. Nothing here is decided.** The registration
(`program/preregistrations/am5-ablated-cost-v1.md`) is a draft, not frozen. This is the record
of its pre-freeze dry run, which its section 15 summarises.

- **What ran.** The whole new pipeline on the development population: AM5's 63 development
  questions with their evidence sessions removed (AM5's artifact `f6d27d4c...`, unchanged). That
  covered the GPU job, extract with the replay checks, the blind hand check under the registered
  protocol, analyze, the comparison with AM5's committed outputs, the power computation and the
  tests.
- **Held-out data.** Before the freeze the held-out ablated artifact was built and pinned on the
  host CPU, and the image's CPU selftest rendered its prompts with the tokenizers and recorded only
  their lengths. No reader or judge ran on it, and no model output of it exists.
- **Outcome.** The dry run reproduced AM5 exactly: 24 of 24 checks
  (`dryrun-compare.json`).
- **GPU-hours.** 0.1325 physical GPU-h, against the 0.3 allowed. Build 1502 took 0.0197 and job
  1507 took 0.1128.

## Commits and host

| Commit | What |
|---|---|
| `ca661cd9` | code, config, tests, operator scripts, the draft |
| `c16437bc` | the held-out ablated artifact pinned (the dry run's image, job and analysis) |
| `351dc062` | the hand-label receipt, committed before the join |
| `cf9f9ebb`, `943348f4`, `8128800a` | the runbook rehearsal script, and two fixes to it |
| `fc355d10` | pre-freeze check 1's fixes (code, scripts, tests, draft); the CPU parts rerun at it (section 9) |
| `21eb1210` | the round-1 hand-label receipt, committed before the join |

Host root `~/cotcodec-runs/stage0/am5r-dev-dryrun/`, mode `dev` of every `ops/am5r/` script, from
clean checkouts made by `am5r-checkout.sh` from Mac bundles. Slurm partition `research`. D110's
`transcreate-lama` jobs held their own GPUs and were not touched. The first build attempt found
two GPU jobs of another workstream of this program running (`g3-pilot-*`). The preflight refused
it, and the build was submitted once they had ended (`ops/preflight.log`).

## 1. The held-out ablated artifact (host CPU, no model)

`am5r-prepare-heldout.sh dev ca661cd9` ran `memcredit_am5r.py prepare-heldout`. The text-free
summary and output are in `prepare/` (`heldout-ablated-summary.json`,
`prepare-heldout-ca661cd9.json`).
- **The artifact.** `68a75dcf1bc37ebe54fde61ec288d9c393adc1d0197b88168d7c153be34c1ce6`,
  2,493,448 bytes, host only and read-only. Its summary is `c68b1da9...`. Both are pinned in the
  config at `c16437bc`.
- **Builder checks.** On the unablated records, the pool builder reproduces AM1's held-out
  retrieved pools, 347 of 347. The ablation rebuilds AM5's 63 development ablated pools exactly,
  63 of 63; these ride along unchanged as the replay control.
- **Leakage, by LongMemEval's flags.**
  - 700 evidence sessions were removed, with no repeated id.
  - The 691 `has_answer` turns all lay inside those sessions; none is left in any ablated
    haystack or pool.
  - No pool memory equals an evidence-session user turn.
- **Leakage, by the crude string check** (the normalized reference answer as words; short answers
  match by chance). 27 of the 347 ablated pools hold a memory containing the answer, and 91
  questions have it in a remaining user turn. For AM5's development pools the figures were 4 and
  10 of 63.
- **Overlap.** The ablated pools share 1,493 of their 2,776 memories with the original pools.
- **Types.** Temporal-reasoning 106, multi-session 101, knowledge-update 59, single-session-user
  52, single-session-preference 25, single-session-assistant 4.
- **Prompt size.** The longest full-pool prompt has 7,518 characters.

## 2. A CPU precheck on AM5's job 1487

Before any GPU time, at `ca661cd9`, the registration's CPU steps ran on a scratch copy of AM5's
job 1487. It used links to the passes, with the summary's experiment and population renamed. The
steps were `extract` (development), `analyze` and `dryrun-compare`.
- All 24 comparison checks passed (`precheck/dryrun-compare-job1487-cpu.json`).
- Fed AM5's own run, the new code reproduces AM5's committed figures, AM5's per-pool table byte
  for byte included.

## 3. Build, selftests, GPU job (code `c16437bc`)

| Job | What | GPUs | Run time | GPU-h |
|---|---|---:|---:|---:|
| 1502 | cotcodec-vllm cu129 overlay build from the capsule of `c16437bc` (`003eb3c1...`); image `sha256:a16f70c1bc732961f1c9dd44bc13767a8ec292df2000206cdaafaafa8a328ab8`, provenance PASS, the build record's checks pass | 1 | 00:01:11 | 0.0197 |
| 1503 | CPU selftest, development (no GRES) | 0 | 00:00:17 | 0 |
| 1504 | CPU selftest, held-out (no GRES; tokenizers only, no model output) | 0 | 00:01:05 | 0 |
| 1507 | GPU job, development: the three readers and judge32 | 1 | 00:06:46 | 0.1128 |
| | **total** | | | **0.1325** of the 0.3 allowed |

- **Selftests.** Every prompt fits.
  - Development: 4,473 requests per reader, prompts of at most 1,148 (Qwen3-8B), 1,077 (OLMo-2)
    and 1,164 (Qwen3.5-9B) tokens. These match AM5's.
  - Held-out with the control: 29,110 requests per reader, at most 1,778, 1,699 and 1,803 tokens.
    Its 1,638 placeholder judge items have at most 349 tokens.
  - vLLM 0.31.0 resolves the three architectures.
- **Job 1507.** It ran within a 13-minute limit, so the dry run fits 0.3 GPU-h even at the limits.
  - Every step completed, and OLMo-2's fallback was not needed.
  - Engine starts took 27.8, 28.1 and 41.2 s, then 37.2 s for the judge.
  - The passes took 32.4, 34.3 and 58.6 s, then 3.5 s for the judge on 460 items.
  - The rerun rule said `complete` (`ops/rerun-decision-development-1507.json`).

## 4. The replay against AM5's job 1487 (extract)

| Reader | cells | identical tokens and finish | identical log-prob bits | primary labels equal |
|---|---:|---:|---:|---:|
| Qwen3-8B | 4,473 | 4,473 | 4,473 | 4,473 |
| OLMo-2-1124-7B-Instruct | 4,473 | 4,473 | 4,473 | 4,473 |
| Qwen3.5-9B | 4,473 | 4,473 | 4,473 | 4,473 |

- **Judge items.** The judge-item list is byte-identical to job 1487's (`4bbb7f5c...`), and the
  judge's 460 item labels equal job 1487's.
- **Qwen3.5-9B.** It runs in default mode, but with the same request list and order it repeated
  job 1487 exactly, as am3g's dry run repeated AM3.
- **Features.** `753ea702...`, host only.

## 5. The comparison with AM5 (`dryrun-compare.json`, 24 of 24)

- **Replies and judge.** The replies and labels are as above, and the judge-item list is
  byte-identical.
- **Feature cells.** The features' per-pool cells equal AM5's features (`16bbd385...`) for all
  three readers.
- **AM5's analysis on these features.** `memcredit_am5.analyze`, run with AM5's receipted hand
  labels and plan (`9da82b41...`, `171707ec...`), reproduces AM5's committed outputs:
  - `per-table.json.gz` byte for byte (`58bec838...`);
  - its `readers`, `leakage`, `leakage_by_type`, `judge_validation`, `labelled_items` and
    `hand_check`.
- **This registration's blocks.**
  - Its ablated block equals AM5's committed figures in every judge-based field, at K = 8 and 70.
  - Its development gain side equals AM5's original-pool gains: 1, 4 and 3 at both caps.

So the cost side is AM5's.
- At K = 8: switches 1, 6 and 3, costs 0, 5 and 3.
- At K = 70: switches 2, 10 and 3, costs 1, 9 and 3.
- The order is Qwen3-8B, OLMo-2, Qwen3.5-9B.

## 6. The blind hand check under the registered protocol

- **The sample.** `hand-sample` drew 34 items in one chunk. Plan `2bcd07af...`, sample
  `e0b77ed6...`, instructions `ee50ff25...`. By use:
  - 2 switched replies judged correct;
  - 8 switched replies at K = 8 judged wrong (7 distinct);
  - 3 of the 5 judged-wrong switches beyond K = 8, the seeded half rounded up per reader;
  - 5 answering top-4 replies;
  - 18 distractors, with no shortfall.
- **The CLI launch.** `am5r-hand-label-mac.sh dev c16437bc first W cli` claimed the stage and ran
  the CLI. It could not start a session: an authentication error, reported as a synthetic
  assistant line and an error result, at 18:41:11Z. It exited 3.
- **The fallback.** One fresh subagent of the operator session, model `claude-opus-5-5`, received
  `prompt-01-abs.txt` as its whole prompt. `push subagent` found exactly one matching transcript
  among 45 and copied it unmodified.
- **The audit passed** (`hand-check/hand-merge-first-c16437bc.json`):
  - three tool calls (a Read of each input and a Write of the output);
  - every assistant line from `claude-opus-5-5`;
  - one agent id;
  - every line after the CLI's failure.
  - The context held the user's and the project's `CLAUDE.md` and `MEMORY.md`.
- **Labels.** 34 valid rows, so there was no repair stage. Labels `36f3e23d...`.
- **The receipt** was committed at `351dc062` before `analyze` joined the labels.
  `logs/analyze-c16437bc.log` names that commit.
- **Agreement with the judge.**
  - Hand against judge: 34 of 34 (kappa 1.00), with 6 labelled correct. No switched reply was
    labelled a decline outside the four patterns.
  - Against AM5's own receipted labels: 16 of AM5's 18 items are in this plan, and all 16 labels
    agree. The other 2 are judged-wrong switches beyond K = 8 that the seeded half left out.
- **Hand-based costs.** They equal the judge-based ones at K = 8 (0, 5 and 3). At K = 70 the two
  unlabelled OLMo-2 replies make the hand-based cost 7 to 9 under the two registered assignments.

## 7. Analyze (development mechanics; decides nothing; round 0, `c16437bc`, now in `round0-c16437bc/`; round 1 in section 9)

`am5r-analyze.sh dev c16437bc` ran `analyze` twice, with byte-identical outputs:
`results.json` `b6455ca0...`, `per-table.json.gz` `fe2612ea...`, `tables.md` `9df87ff8...`.
Then it ran `dryrun-compare` (24 of 24), `power` (`power.json` `df7e8e62...`) and the memcredit
tests (221 passed on the host). The whole suite on the host at `943348f4` gave 3,770 passed, 64
skipped and 2 failed (`logs/pytest-full-suite-943348f4-summary.txt`). The two failures are in
another experiment's tests, `test_r04_evidence.py` and `test_r04_nuisance.py`, the same two that
fail on `main`.

| Development, K = 8 | cost | gain | cost only | gain only | D [exact 95%] | judge reading | hand label | break-even share [95%] |
|---|---:|---:|---:|---:|---|---|---|---|
| Qwen3-8B | 0 | 1 | 0 | 1 | -0.016 [-0.016, +0.015] | NOT_SEPARATED | NOT_SEPARATED | 1.00 [1.00, 1.00] |
| OLMo-2 | 5 | 4 | 5 | 4 | +0.016 [-0.082, +0.104] | NOT_SEPARATED | NOT_SEPARATED | 0.44 [0.11, 0.80] |
| Qwen3.5-9B | 3 | 3 | 3 | 3 | +0.000 [-0.073, +0.073] | NOT_SEPARATED | NOT_SEPARATED | 0.50 [0.00, 1.00] |

- **Validity.** V3 (the replay of every request) passes. G-J1 passes on the development items:
  - reference yes 58 of 58;
  - "I don't know." no 63 of 63;
  - other-answer decoys yes 4 of 62, reported.
- **No separation.** At 63 questions no reader separates at either cap. As AM5 said, the
  development gains are far below the held-out ones, so none of this predicts a held-out
  reading.

## 8. The runbook rehearsal (`rehearsal/`)

`rehearsal/am5r-rehearse.sh` runs section 16's host scripts under a fake HOME on the host. It
stubs `sbatch`, `scontrol`, `squeue` and `nvidia-smi`, and for the Mac's labelling script `ssh`,
`scp` and the `claude` CLI (its authentication failure). No job is submitted, no GPU or model is
used, and no held-out output exists.
- **Inherited cases.** It covers am3g's 56 cases, adapted to these scripts.
- **This registration's cases:**
  - dev mode refuses to submit or extract the held-out population;
  - `prepare-heldout` refuses reg mode and an existing artifact;
  - the held-out tokenizer-only selftest submits in dev mode.
- **The first run**, at `cf9f9ebb`, stopped after two cases. An apostrophe inside a parameter
  expansion's message made bash read the next variables as part of it. The fix is `943348f4`.
- **The second run**, at `943348f4`, passed 60 of 61 (`rehearse-943348f4.log`). The one failure
  was in the rehearsal itself: the held-out refusal case reused the "no sbatch call" check after
  an earlier case had legitimately submitted. The refusal itself was right; the output says
  "mode dev does not run population heldout on a GPU".
- **The third run** used the rehearsal script of `8128800a` (SHA-256 `9b4704ec...`), which counts
  sbatch calls instead. It tested the operator scripts of `943348f4` (the same as `c16437bc`'s)
  and passed 61 of 61 (`rehearse-943348f4-fixed.log`): 56 inherited cases and 5 of this
  registration's.

## 9. Round 1: pre-freeze check 1's fixes, and the CPU parts rerun at `fc355d10`

No GPU time and no model on held-out data. The GPU job's code is unchanged (`run`, `worker` and what
they call); the held-out job's limit changed in the config (80 minutes), which the development job
does not use.
- **The inputs directory.** `chmod a-w` on the host's
  `~/cotcodec-runs/stage0/am5-ablated-cost-v1/inputs` (it is now `dr-xr-xr-x`; its two files were
  already read-only; `ops/jobs.log`).
- **Round 0 set aside.** The CPU outputs of `c16437bc` (features, hand directory, receipts, analysis
  outputs and logs) were moved on the host to `round0-c16437bc/`; their committed copies are in
  `round0-c16437bc/` here, the round-0 receipt included.
- **Extract** at `fc355d10` read job 1507 with its rerun-rule record (`complete`), refused nothing,
  and wrote features `0f6984d4...` that record the job id (1507) and the record's digest; the replay
  checks are as before (all three readers 4,473 of 4,473; judge items byte-identical).
- **The blind hand check, relabelled under the new instructions** (`HAND_INSTRUCTIONS`
  `1745340a...`, which ask for a note starting "decline:" on a 1 given for a decline). The plan is
  the same (`2bcd07af...`, 34 items, one chunk). The CLI launch failed at 21:11:43Z; one fresh
  subagent (`claude-opus-5-5`) labelled the chunk with the pinned prompt; its transcript (three tool
  calls, one agent id, every line after the failure) passed the audit; 34 valid rows, no repair.
  The receipt was committed at `21eb1210` before the join (`hand-check/`). Labels `d21c25b9...`:
  equal to round 0's on all 34 items; 34 of 34 with the judge (kappa 1.00); no 1 was given for a
  decline (no decline note), so no switched reply on these pools declined outside the patterns.
- **Analyze** twice at `fc355d10` (byte-identical): `results.json` `8e3a090e...`,
  `per-table.json.gz` `fe2612ea...` (unchanged), `tables.md` `c7a6043d...`. New in them: the
  labelled items with their leakage facts and decline flags, the decline-note counts, and the split
  by the two crude leak flags (no reader switched on a flagged development pool). `dryrun-compare`:
  24 of 24 (`50317af3...`). `power.json` (`cac6186f...`) adds the power averaged over the
  development uncertainty (Jeffreys' prior): Qwen3-8B COST_BELOW_GAIN 0.976-0.985, OLMo-2 either
  direction 0.152-0.238, Qwen3.5-9B 0.253-0.366. The memcredit tests: 227 passed on the host, and
  `tests/test_memcredit_am5r.py` 68 passed locally.
- **The rehearsal** at `fc355d10`, in a new directory on the host that was deleted afterwards: 72 of
  72 (`rehearsal/rehearse-fc355d10.log`), the 61 above and 11 for round 1: a rebuild refused after
  a successful build; a job scontrol forgot recorded from the lane's termination record and then
  decided; a forgotten job without a termination record left unrecorded (exit 2); rerun-decision
  refusing a job with no saved record; extract refusing a job without a rerun-rule record, three
  whose record does not say complete, and existing features; hand-sample refusing features of
  another job.

## Files

- `results.json`, `per-table.json.gz`, `tables.md`: the development analysis (text-free).
- `dryrun-compare.json`: the comparison with AM5.
- `power.json`: section 9's operating characteristics.
- `prepare/`: the held-out ablated artifact's text-free summary and the prepare output.
- `precheck/`: the CPU precheck's comparison on job 1487.
- `hand-check/`: the round-1 receipt and its text-free records, as committed before the join.
- `round0-c16437bc/`: the first analysis (`c16437bc`) and its receipt, set aside in round 1.
- `jobs/1507-development/`, `builds/`, `selftests/`, `manifests/`, `ops/`, `logs/`: the lane and
  operator records, with every raw output's SHA-256 and the judge items with each response
  replaced by its SHA-256.
- **Text search.** The staging script searched every staged file for 3,989 texts and found none.
  The texts were every reply of at least 12 characters and every question, answer and memory text
  of both artifacts.
- **What stays on the host.** The replies, the artifacts, the features, the hand-check texts and
  the labeller's transcript stay under `~/cotcodec-runs/stage0/am5r-dev-dryrun/` and
  `~/cotcodec-runs/stage0/am5-ablated-cost-v1/inputs/`.
