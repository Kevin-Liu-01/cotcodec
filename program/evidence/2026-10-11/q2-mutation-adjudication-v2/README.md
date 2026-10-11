# q2-evaluator-mutation-v1: the pool and spot check adjudicated (D81 run 2), with the parent analysis rerun

**Adjudicated by an isolated model on the owner's instruction (D80); not
human-validated.**

This is the record of D81's run 2 for the checker-mutation study
`q2-evaluator-mutation-v1` (ledger row 11, frozen at `65bc2e2`, descriptive
under D35 and D38) and its K2 addendum (row 17, VERIFIED, D79). It covers the
34-item adjudication pool and the 25-item spot check: 52 distinct items, 7 of
them in both lists. Each item was answered by a fresh, isolated
`claude-opus-5-5` agent started with the registered rater template. The
registered isolation audit ran over that session. Then `audit summarize
--adjudications` and the parent analysis with `--k2-report` were rerun from a
git archive of the freeze commit. Two sensitivities from D81 are reported
beside it, and neither replaces the record. Nothing here is confirmatory.

**Blind warning.** D9's human spot check is still pending as a human
validation. Anyone who does it, or who adjudicates the pool as a human, should
answer from the blind packets before reading anything in this directory. The
files here name labels, decisions, sham status and answers.

## What was registered

- **D9** used provider-distinct model raters in place of the two human raters
  of the reviewed plan. A stratified sample was kept for a human spot check by
  Kevin, and every result states that check as pending. D23, D25 and D27 set
  the raters: the isolated Claude agent, `claude-opus-5-5`, and the
  self-hosted Qwen3.6-35B-A3B.
- **Section 9, adjudication.** `raters.adjudication_pool` collects three kinds
  of item: every real item on which the raters split, every audited mutant
  that both raters judged against its label, and every gold sham on which they
  split. The items are put in one seeded order and written as ids only. The
  adjudicator sees each blind packet only. An answer of accept or reject
  decides the item, concordant items included. An answer for an item outside
  the pool is refused, and an unsure answer is not a registered adjudication.
  A split left unadjudicated counts as a label error. A concordant item left
  unadjudicated keeps the raters' consensus. Adjudication changes label error
  but never kappa.
- **Section 9, gold defects (D34).** A task whose gold sham is decided reject
  is a gold-defect task. Its equivalence items leave the equivalence K3 group
  and are reported as gold defects. They stay in kappa, S6 and P2, and P2 is
  also reported without them as a sensitivity.
- **Section 9, spot check.** `raters.human_spot_check` draws max(5, 10%) items
  per D35 stratum plus 5 shams: 25 items, asked the same blind question.
- **Section 9, isolation (D25, D27, D34, D35, D38).** One agent per item,
  started with the template `isolated_rater_prompt.txt` (`0e9d4eb6...`)
  rendered for that item. The agent may use the Read tool only, and only
  inside its own item directory. The audit is `rater_runner
  collect-transcripts` followed by `ingest-isolated`, which runs
  `audit_transcript` on every transcript. An answer is void if the agent made
  a shell call, used any tool other than Read and the neutral ones, or read a
  path outside its directory. It is also void if any user turn is neither the
  rendered template nor the one allowed relay frame, if any entry or
  attachment type is unregistered, if the packet was never read, if the answer
  differs from the transcript's, or if the item tree does not re-hash to the
  export. An item the audit voids stays unadjudicated. The model pin is not a
  per-item void: a transcript whose harness-recorded model is anything but
  `claude-opus-5-5` refuses the whole ingest.

## D80 and D81

- **D80 (ii).** Kevin delegated his pending decisions. The pool and the spot
  check are done by fresh, isolated model adjudicators, one per item, blind to
  both raters' labels, under the template's isolation rules. This is a
  disclosed deviation from D9, because the spot check was meant to be a human
  validation of the model raters. Every output carries the label above.
- **D81: run 1 is void.** The first run, workflow `wf_cdd11126-1a7` on branch
  `ops/q2-mutation-adjudication` at `2944557c`, did not start its agents with
  the registered template. The orchestrator's prompt told each agent to fetch
  its packet over ssh, and it gave context beyond the item. All 52 agents used
  Bash, which the template forbids, so all 52 answers are void under the
  registered audit. Run 1 is cited here only as void, and none of its answers
  or numbers is used. This collector read run 1's two helper scripts and, in
  the process, saw that branch's commit message, which states run 1's numbers.
  Nothing from it is used. `summarize_adjudication_v2.py` takes its
  spot-check and before/after layout from run 1's `summarize_adjudication.py`.
  `audit_runs.py` is new.
- **D81: run 2's rules** were committed on `main` in `9890d11b` at
  2026-10-11 19:04:07Z, before any run-2 answer existed. The three sessions
  started at 19:04:26Z, 19:04:37Z and 19:04:45Z.
  - **(a)** is the record: one workflow session that holds the adjudicator
    agents and nothing else. It starts one agent per distinct item, 52 in
    `item_id` order. Each agent gets exactly the registered template, rendered
    with the export's `iso_root`, as its task turn. The model is
    `claude-opus-5-5` and the schema is `{item_id, answer, reason}`. The
    session is audited with the registered tooling, and an item that audit
    voids stays unadjudicated.
  - **(b)** is the independence sensitivity: the same 52 items and prompts
    with `claude-fable-5-1`. It is reported as agreement with (a) and as an
    alternative analysis, and it never replaces (a).
  - **(c)** is the notation sensitivity: the 12 items whose packet shows the
    differ's added-sheet marker, run with the template plus D81's fixed
    sentence (`d81-notation-sentence.txt`, `87f97110...`).

## What ran

The three workflow sessions belong to the orchestrating session. Each record
is in `isolation/<run>/rating-run.json`, without reasons, and each workflow
script is copied there byte for byte.

| Run | Workflow | Model (harness record) | Items | Ran | Journal | Tokens | Tool calls |
|---|---|---|---:|---|---|---:|---:|
| (a) record | `wf_843930b8-5af`, script `6fee2b4c...` | `claude-opus-5-5` x 52 | 52 | 19:04:26Z, 418.5 s | 1 launched, 52 started, 52 results | 6,266,775 | 763 |
| (b) Fable | `wf_4d1fa210-001`, script `6d5e01b2...` | `claude-fable-5-1` x 52 | 52 | 19:04:37Z, 581.3 s | 1 launched, 52 started, 52 results | 7,889,955 | 795 |
| (c) notation | `wf_d750e081-ae1`, script `3ab0f8e9...` | `claude-opus-5-5` x 12 | 12 | 19:04:45Z, 136.5 s | 1 launched, 12 started, 12 results | 1,435,493 | 136 |

- In every script, the `TEMPLATE` string equals the registered template file
  byte for byte. The `NOTE` in (c) equals D81's sentence followed by one
  newline.
- The `IDS` of (a) and (b) are the 52 distinct pool and spot-check ids, in
  sorted order. The 12 ids of (c) are exactly those of the 52 packets that
  contain `sheets/%2B`. The collector checked this on every exported
  `packet.txt`, and each of the 12 contains one occurrence.
- Besides the task turn, every agent got the harness's injected context,
  which section 9 registers and discloses. The `session_context` attachment
  (the git status and account context) was identical in all 116 agents of
  (a), (b) and (c). Its git status listed the latest commit title, D81's own:
  `9890d11b decisions: D81 (first D80 adjudication run void; run 2 rules fixed
  before answers)`. It names none of the 178 exported item ids, and no label,
  verdict or answer.
- Every agent ran once, none was interrupted, and no run was resumed. Every
  returned `item_id` equals its item.
- The returned answer files are kept outside the repository, because their
  reasons quote documents. Their SHA-256 are in `isolation/a/receipt.json`
  (`answers_files_sha256`) and in `isolation/{b,c}/audit_runs.json`. The
  workflows' returned outputs are `wuf4bjyya.output` (`e8b9618a...`),
  `wmr2pdwki.output` (`593efd94...`) and `wc6j7ll2h.output` (`9ffa4c82...`).
- The collector worked from a fresh `git archive` of `65bc2e2`: 3,744 files,
  `campaign.check_pins` passes, and the code tree is `58bee019...`, the
  frozen pins. The interpreter was the worktree's Python 3.13.14 with
  `-E -s -B` and `COTCODEC_GIT_SHA=65bc2e2b...`. No GPU was used and no host
  job ran.

## Isolation audit: outcome

| Run | Tool | Outcome |
|---|---|---|
| (a) | `collect-transcripts` and `ingest-isolated`, frozen, unmodified | **52 `ok`, 0 void** |
| (b) | frozen collector: accepted. Frozen ingest: refused on the model pin. Then `audit_runs.py --model claude-fable-5-1` | strict: **52 void**, every one only for the unregistered attachment type `batching_reminder_sent`. Every other check passes |
| (c) | frozen collector: refused on the task turn. Then `audit_runs.py --suffix-file d81-notation-sentence.txt` | **12 `ok`, 0 void** |

**(a), the registered audit, run end to end.**

- **Collector.** The 52 transcripts map one-to-one to 52 exported items by
  their rendered task turn, and all 52 answered. The 126 other exported items
  have no transcript, because they are not part of this run. The collection
  is `18db95f0...`.
- **Ingest inputs.** Both packet copies (`47d17b52...`, `f91104b4...`, every
  exported packet's rebuilt request checked), the export manifest
  (`f9c91d57...`, equal to the committed `iso-manifest.json`), the isolation
  root, the 52 answer files and the collection.
- **Ingest result** (`calls.jsonl` `34a8be1d...`):
  - 52 `ok`: 32 accept, 20 reject, no unsure.
  - Every agent turn is `claude-opus-5-5` (1,051 turns).
  - Tools: 711 Read and 52 StructuredOutput, nothing else.
  - Every Read is inside the agent's own item directory, and every agent read
    its `packet.txt`.
  - Each transcript has exactly one user turn, and it is the rendered
    template.
  - No relay frame, so `rerate.json` lists no item.
  - Only the 15 registered attachment types appear.
  - Every rated item's tree re-hashes equal to its export.
  - The root holds only exported items.
  - The code digests equal the 2026-10-08 receipt's.
- No check had to be replaced for (a).

**Which checks could not run through the frozen tool, and why.** Neither
reason is an isolation failure, and no frozen code was edited.

- **(b):** `ingest_isolated` refuses the whole ingest when any transcript
  names a model other than `claude-opus-5-5` (`isolation/b/ingest-refusal.txt`),
  and it wrote nothing. The frozen collector did accept (b): 52 transcripts
  mapped and 52 answered (`isolation/b/collection.json`).
- **(c):** `collect_transcripts` maps a transcript only by the bare rendered
  template, so D81's added sentence makes it refuse the first agent, and it
  wrote nothing (`isolation/c/collector-refusal.txt`).
- `audit_runs.py` applies the same collector and ingest checks by calling the
  frozen functions of the archive, unmodified and with no monkeypatching. It
  imports `read_journal`, `task_text`, `_text_user_turns`,
  `render_isolated_prompt`, `hash_tree`, `audit_transcript`, `_answer_source`,
  `isolated_answers`, `isolated_body` and `answer_for`. Two parameters are
  explicit: the model every agent turn must name, and a suffix appended to the
  rendered template to form the expected task turn.
- **Equivalence.**
  - On (a), it gives the frozen ingest's per-item outcome, answer, void
    reasons, tool counts, models, transcript digest, attachment types, user
    and task turns, packet read and answer source for all 52 items, with no
    mismatch (`isolation/a/audit_runs-equivalence-check.json`).
  - On the 2026-10-08 registered rating (`wf_138e30b5-c1a`, 178 items), it
    reproduces the committed `calls.jsonl`: 177 `ok` and the one
    `isolation_void` (`fd455942...`) with the same reason, every item equal
    (`isolation/validation/`). That run also re-hashed all 178 item trees, and
    all are equal to the export.

**(b) under the same rules.**

- Every other check passes:
  - each transcript maps to exactly one item, and its single user turn is the
    rendered template;
  - Read is used only inside the item directory (743 Reads, 52 structured
    answers);
  - every packet was read and every tree re-hashes equal;
  - every agent turn is `claude-fable-5-1`;
  - there is no relay frame, and every answer matches its transcript.
- Every (b) transcript, though, also holds the harness attachment
  `batching_reminder_sent`: 171 entries in 52 transcripts. The registered
  allow-list does not include it. All 171 carry one fixed, model-scoped
  harness sentence, a nudge to batch independent tool requests, with
  `clearAt: next_user_message`. They name no item, label or answer. They
  appear only in the Fable session's transcripts, and none of (a), (c) or the
  2026-10-08 rating has one.
- The registered audit fails closed on an unregistered attachment type, and
  section 9 says such voids stand. So under the strict rules all 52 (b)
  answers are void. The strict (b) sensitivity then has no adjudication, and
  its analysis is the pre-adjudication K2 rerun.
- The (b) sensitivity below therefore uses the answers with that one
  attachment type excepted. That is a disclosed departure that applies only
  to this sensitivity. It never touches (a).

**(c) under the same rules.** 12 `ok`. The single user turn is the template
plus the sentence. Tools are 124 Read and 12 structured answers, all inside
the item directory, every turn `claude-opus-5-5`, with registered attachment
types only and every tree equal.

## Answers (`adjudications.jsonl`, `spot-check-answers.jsonl`)

From (a)'s ingested `calls.jsonl`, ids and answers only:

- `adjudications.jsonl`: the 34 pool items in the registered pool order, as
  `{item_id, answer}`, the registered `--adjudications` format. 17 accept and
  17 reject, with no unsure, so nothing is left out.
- `spot-check-answers.jsonl`: the 25 items in the registered list order,
  19 accept and 6 reject.
- The 7 items in both lists have one answer, used for both.

The two JSONL files keep the registered `{item_id, answer}` format, so they
carry no label field. The label is in this README. The same holds for every
file whose bytes are fixed elsewhere: the frozen tools' outputs and stdout
(the collector's and the ingest's files in `isolation/a/` and `isolation/b/`,
`audit-summary/`, `analysis/` and their sensitivity copies; the frozen
`audit-summary.json` keeps its own `label` field), the registered-format
JSONL files and the workflow scripts copied byte for byte. Each directory
that holds them has a README with the label, and every JSON file the
collector wrote (`summary.json`, `controls.json`, the `audit_runs` outputs and
the `rating-run.json` files) has a `label` field with it.

What each pool answer did, out of 34 (`summary.json`
`pool_effect_by_reason_and_stratum`):

| Pool reason | Stratum | Raters (Claude / Qwen) | n | Adjudicator (a) |
|---|---|---|---:|---|
| concordant contradiction | `alt_gate` | reject / reject | 3 | 3 uphold (reject) |
| concordant contradiction | `fp_violation` | accept / accept | 3 | 3 uphold (accept) |
| split | `fn_equiv` | accept / reject | 3 | 3 accept |
| split | `fn_equiv` | reject / accept | 3 | 3 reject |
| split | `alt_gate` | reject / accept | 12 | 9 accept, 3 reject |
| split | `alt_gate` | reject / unsure | 5 | 5 reject |
| split | `alt_gate` | unsure / accept | 1 | 1 accept |
| split gold sham | `sham_gold` | reject / accept | 3 | 1 accept, 2 reject |
| split gold sham | `sham_gold` | reject / unsure | 1 | 1 reject |

## Commands (step 3)

All commands ran from the archive root. `<C>` is
`program/evidence/2026-10-08/q2-mutation-confirm`, `<K2>` is the K2 job
directory, and `<scratch>` is the session scratchpad.

```bash
python -m harness.q2_mutation.rater_runner collect-transcripts --run-dir <wf_843930b8-5af> \
  --manifest <scratch>/q2m-confirm-iso-export/iso-manifest.json \
  --out <scratch>/adjudication-v2/a/transcripts --collection-out <scratch>/adjudication-v2/a/collection.json
python -m harness.q2_mutation.rater_runner ingest-isolated \
  --packets <scratch>/q2m-confirm-packets/packets-000.jsonl <scratch>/q2m-confirm-packets/packets-001.jsonl \
  --manifest <scratch>/q2m-confirm-iso-export/iso-manifest.json --iso-root <scratch>/q2m-confirm-iso \
  --answers <scratch>/adjudication-v2/a/answers --transcripts <scratch>/adjudication-v2/a/transcripts \
  --collection <scratch>/adjudication-v2/a/collection.json --out <scratch>/adjudication-v2/a/ingest
python -m harness.q2_mutation.audit summarize --sample <C>/audit/released/confirm-audit-v1/sample.jsonl \
  --anthropic-calls <scratch>/q2m-confirm-b/claude-isolated/calls.jsonl \
  --open-calls <scratch>/q2m-confirm-b/held/open-weight/calls-s000.jsonl <scratch>/q2m-confirm-b/held/open-weight/calls-s001.jsonl \
  --adjudications adjudications.jsonl --out audit-summary
python -m harness.q2_mutation.analysis --outcomes <C>/results/released/confirm-mutants-v1/outcomes.jsonl \
  --controls-summary <C>/results/released/controls/confirm-controls-v1.summary.json \
  --reserve-controls-summary <C>/results/released/controls/reserve-controls-v1.summary.json \
  --audit-summary audit-summary/audit-summary.json --decisions audit-summary/decisions.jsonl \
  --k2-report <K2>/report/k2-report.json --out analysis/analysis.json > analysis/analysis-stdout.json
```

- The calls files are the same bytes, at the same paths, as the 2026-10-08
  summary used: Claude `2120e6ce...`, Qwen `8c8db172...` and `52ba6865...`.
  `audit-summary.json` records those paths.
- Default seeds and 10,000 resamples. Every command exited 0 with an empty
  stderr.

**Controls** (`controls/controls.json`, same archive and interpreter), all
byte for byte:

1. `audit summarize` without `--adjudications` reproduces the committed
   2026-10-08 `audit-summary.json`, `decisions.jsonl`,
   `adjudication-pool.jsonl` and `summarize-stdout.json`.
2. The analysis with the pre-adjudication summary and decisions plus
   `--k2-report` reproduces the K2 rerun's `analysis.json` (`ee66aa39...`)
   and `analysis-stdout.json`.
3. The same without `--k2-report` reproduces the committed 2026-10-08
   `analysis.json` (`a7c21902...`).

The adjudicated summary's `adjudication-pool.jsonl` equals the committed pool.

## What changed against the K2 rerun

Before means `../q2-mutation-k2/k2-confirm-v1-job1186/analysis-with-k2/` and
the 2026-10-08 audit summary. After means `analysis/` and `audit-summary/`
here. Both read with the D80 label.

- **Gold shams and gold-defect tasks.** Of the 4 split gold shams, 3 were
  rejected: `5c1a6c3d` (`compare_pptx_files`), `881deb30` and `8e116af7`
  (both `compare_table`). Those 3 are now gold-defect tasks, where there were
  none before. The fourth, `035f41ba`, was accepted.
- **False-negative candidates** (36, all `pptx.eq.zorder_nonoverlap`):
  - Before: 30 confirmed and 6 unresolved.
  - After: **33 confirmed and 3 label-contradicted**. The 3 newly confirmed
    are on tasks `57667013`, `70bca0cc` and `eb303e01`.
  - The 3 rejected are all of `5c1a6c3d`'s candidates. They sit on a
    gold-defect task, carry `gold_defect_task: true`, and are reported as
    gold defects.
  - By family: `compare_pptx_files` 32 confirmed and 3 contradicted;
    `compare_pptx_files_tolerant` 1 confirmed.
  - Confirmed task-equal shares (unresolved counted as not confirmed before):

    | Share | Before | After |
    |---|---|---|
    | pooled | 10.6% (5.8-16.2%) | **11.6% (6.4-17.3%)** |
    | `compare_pptx_files` | 33.5% (24.8-41.7%) | **37.1% (28.3-44.6%)** |
    | `pptx.eq.zorder_nonoverlap` | 77.1% (61.5-90.6%) | **85.4% (68.8-97.9%)** |

  - The candidate shares do not change: 12.4%, 40.2% and 91.7%.
- **False-positive candidates.** No change. The 3 both-accepted violation
  candidates were upheld as accept, so they stay label-contradicted: the two
  `358aa0a7` `pptx.alt.textbox_for_placeholder` mutants and the `a434992a`
  `pptx.viol.drop_char_format` mutant. Still 2 confirmed (`70bca0cc`,
  `d53ff5ee`), and the confirmed share is 2.1% (0-5.4%).
- **Label contradictions overall.** Before: 3 FP plus 0 FN, with 6 FN
  unresolved. After: 3 FP plus 3 FN, and the 3 FN are on a gold-defect task.
  The equivalence label-class agreement goes from 30 of 36 accepted (83.3%)
  to 33 of 36 (91.7%), with 3 rejected.
- **Alternative solutions (P2's gate, 93).**
  - Before: 72 accepted, 3 rejected, 18 unresolved.
  - After: **82 accepted, 11 rejected, 0 unresolved**. The gate share goes
    from 77.4% to 88.2%.
  - Of the 18 splits, the 10 accepted are on no gold-defect task. The 8
    rejected are all on the two `compare_table` gold-defect tasks.
  - The 3 both-rejected items were upheld: 2 on those tasks and 1 on
    `4f07fbe9`. So all 10 alternative solutions of `881deb30` (6) and
    `8e116af7` (4) are rejected. Outside gold-defect tasks, 82 of 83 are
    accepted.
  - Rejected, by operator: `xlsx.alt.literal_for_formula` 7,
    `xlsx.alt.named_style_for_direct` 3, `xlsx.alt.absolute_refs` 1.
  - The gold-defect rule moves only equivalence items. These alternative
    solutions stay rejected in the gate, which reads them against a gold the
    adjudicator rejected.
- **P2.**
  - The rate is unchanged at 12.4% (7.2-18.3%) on 60 tasks. The population
    goes from 327 to **337** mutants, because the 10 newly accepted
    `compare_table` alternative solutions join, and the checker passes them,
    so the events do not change. `compare_table` is 0 of 207 on 30 tasks,
    zero-event bound 9.5%. `compare_pptx_files` is unchanged at 40.2%
    (32.9-46.3%).
  - **P2 without the gold-defect tasks' equivalence mutants**, the registered
    sensitivity, is computed here for the first time: **12.2% (6.7-18.1%), 323
    mutants on 57 tasks**. In it, `compare_pptx_files` is 39.6% (32.0-45.8%,
    79 mutants, 15 tasks), and `compare_table` is 0 of 199 on 28 tasks with a
    zero-event bound of 10.1%. That bound is above 10%, so K6b's
    `compare_table` flag does not hold in this sensitivity. It still holds in
    P2 proper.
- **K3** (reported only, D35):
  - Equivalence group: 0.167 (36 items, 16 tasks, bound 0.314) becomes
    **0.000** (33 items, 15 tasks, exact upper 0.087, sufficient). The group
    still fires, but only because κ = 0.343 < 0.6, which adjudication never
    changes. On its bound alone it would not fire. The frozen reason string
    still reads `K3: should_pass_equiv label error` (under P2 and P5 in
    `metrics_leaving_headline`, and in K6's `blocked_by`), because the frozen
    code writes it whenever the group's K3 flag fires, and that flag is κ or
    the bound. Here the cause is κ, not the label error.
  - Violation group: unchanged at 0.600 (5 items, 4 tasks, insufficient),
    and it fires.
  - κ fires.
- **K4: fired before, does not fire now.** The equivalence group is now below
  10%. K4 is reported only and is not a stop (D35).
- Every other K is unchanged. K1 70/74; K5 no operator; K6 retired, with the
  same blocked list, because the K3 reasons stay through κ; K6b
  `compare_table` for P2; K7 `compare_pptx_files` for P2; K9 7/68. The
  `metrics_leaving_headline` lists are identical.

## What did not change

`summary.json` `unchanged_by_adjudication` records these as identical before
and after:

- κ 0.343 on 138 real items, and the per-rater sham accuracy (0.90 and
  0.975);
- P1 (4/92 raw, 3/92 audit-confirmed; no P1 flip was in the pool);
- P3 6.1%, P4 0 of 5, and P5 17 of 60 tasks;
- the false-positive table and shares, and every candidate share;
- S1-S7 and the population;
- the violation K3 group;
- the raters' own split count (24 real items);
- K1, K5, K6 and K9;
- the protocol and metric roles.

## Sensitivities (each a full `audit summarize` plus analysis)

**(b) Fable answers as the adjudications** (`sensitivity/b-fable/`). Fable
answered 31 accept, 20 reject and 1 unsure. The unsure is `0fd24b93`, an
equivalence split (Claude accept, Qwen reject), so it is left out and stays
unresolved. The other 33 pool answers equal (a)'s. Everything else equals (a)
except what follows from that one item:

- FN candidates: 32 confirmed, 1 unresolved, 3 contradicted.
- Confirmed shares: pooled 11.2% (6.2-17.0%), `compare_pptx_files` 35.8%
  (26.9-43.5%), `pptx.eq.zorder_nonoverlap` 82.3% (66.6-95.8%).
- Equivalence K3: 0.030, upper 0.136.
- K4 does not fire.
- The same 3 gold-defect tasks, the same gate (82, 11, 0), the same P2 and
  gold-defect sensitivity, and the same FP table.

This reading excepts the `batching_reminder_sent` attachment. Under the strict
registered audit, all 52 Fable answers are void, and (b) is the K2 rerun
unchanged.

**(c) notation** (`sensitivity/c-notation/`). (a) answered accept on all 12
marker items, without D81's sentence, and (c) answered accept on all 12 with
it. So swapping in (c)'s answers changes nothing, and (c)'s audit summary and
analysis are byte-identical to (a)'s.

- 9 of the 12 items are in the pool and 3 in the spot check.
- In the registered rating, the Claude rater rejected 9 of these 12 items
  and Qwen accepted all 12. That is descriptive only.
- The sentence changed no answer of the record.

## Agreement (`summary.json` `agreement`, `spot_check`)

| Comparison | Items | Agree | κ |
|---|---:|---:|---:|
| (a) vs (b), all items | 52 | 51 (the other: (b) unsure) | 0.96 (accept/reject only: 1.00) |
| (a) vs (b), the 28 pool splits | 28 | 27 | 0.93 |
| (a) vs (b), the 6 concordant contradictions | 6 | 6 | 1.00 |
| (a) vs (c), the 12 marker items | 12 | 12 | - |
| (a) vs the Claude rater, all items | 52 | 41 (78.8%) | 0.60 |
| (a) vs the Qwen rater, all items | 52 | 35 (67.3%) | 0.34 |
| (a) vs Claude, the 28 splits | 28 | 17 | 0.24 |
| (a) vs Qwen, the 28 splits | 28 | 11 | 0.00 |
| (b) vs Claude / Qwen, all items | 52 | 40 / 35 | 0.57 / 0.36 |
| Claude vs Qwen, all items | 52 | 24 | 0.12 |

(b)'s answers are used here with `batching_reminder_sent` excepted. Under the
strict registered audit all 52 (b) answers are void (see the isolation audit
above).

**Spot check, adjudicator against the raters' consensus by stratum, 25
items.** (a) and (b) answered identically on all 25 ((b) with the attachment
excepted, as above).

| Stratum | Items | Raters concordant | Adjudicator agrees with the consensus | Raters split | Adjudicator = Claude / Qwen | Agrees with label or sham truth |
|---|---:|---:|---:|---:|---|---:|
| `alt_gate` | 10 | 9 | 9 | 1 | 10 / 9 | 7 |
| `fn_equiv` | 5 | 4 | 4 | 1 | 5 / 4 | 5 |
| `fp_violation` | 5 | 5 | 5 | 0 | 5 / 5 | 2 |
| gold sham | 4 | 4 | 4 | 0 | 4 / 4 | 4 |
| do-nothing sham | 1 | 1 | 1 | 0 | 1 / 1 | 1 |
| **all** | **25** | **23** | **23** | **2** | **25 / 23** | **19** |

- The adjudicator agrees with the model raters' consensus on every concordant
  spot-check item, and it sides with the Claude rater on both splits.
- It contradicts the label on 6 items: 3 `alt_gate` rejects and 3
  `fp_violation` accepts. On 5 of them both raters already contradicted the
  label (`alt_gate` `e5bce1a7` and `1050d491`, both raters reject;
  `fp_violation` `1519df64`, `7a23bbe1` and `d1959ff9`, both raters accept).
  The sixth, `aa3331db` (`alt_gate`, in the spot check and the pool), is a
  split (Claude reject, Qwen accept), and on it the adjudicator sided with the
  Claude rater.
- All 5 shams are correct.

## Correlated-judge caveat

The record's adjudicator, (a), is `claude-opus-5-5`, the same model as the
Anthropic rater, and D81 accepts this.

- (a) agrees with the Claude rater more than with Qwen: 41 against 35 of 52
  items.
- On the 28 splits it sides with Claude 17 times and with Qwen 11 times.
- It sides with Claude on all 6 equivalence splits and on all 25 spot-check
  items.
- Run (b), `claude-fable-5-1`, is a model that is neither rater's, but it
  comes from the same provider. It agrees with (a) on 51 of 52 items and on
  27 of 28 splits, with `batching_reminder_sent` excepted (under the strict
  registered audit all 52 (b) answers are void). That measures the stability
  of the answers across two Anthropic models. It does not measure
  independence from the Anthropic rater's provider.

So the adjudication is not an independent tie-break. Because the judges are
correlated, the adjudicated reading may lean toward the Claude rater where
the raters split. In particular, it rejects 8 split alternative solutions and
3 split gold shams where Qwen accepted or was unsure. D9's human spot check
stays pending as the human validation.

## Image coverage

| Who | Items | Page images | Opened with Read | Agents opening every image |
|---|---:|---:|---:|---:|
| Registered rating, all items | 178 | 1,457 | 1,453 | 176 |
| Registered rating, these 52 items | 52 | 506 | 502 | 50 (`0fd24b93` 14/15, `cbcf768b` 4/7) |
| (a) record | 52 | 506 | 503 | 50 (`0fd24b93` 14/15, `11fa9afa` 22/24) |
| (b) Fable | 52 | 506 | 506 | 52 |
| (c) notation | 12 | 73 | 73 | 12 |

- In (a), 43 of 52 agents got a read-truncation notice, meaning the packet
  was longer than one Read shows. The median agent made 4 Reads of
  `packet.txt`, with a range of 1-13.
- Coverage is a diligence count, not a void condition.

## What the result licenses

- **It is a descriptive reading.** The registered protocol's adjudicated
  outputs exist, with an isolated model in Kevin's role (D80). They are
  labelled "adjudicated by an isolated model on the owner's instruction
  (D80); not human-validated".
- **It is not confirmatory.** P2-P5 stay exploratory under D34 (i). K3 and K4
  are reported, not acted on (D35). κ, which stays at 0.343, is a rater
  statistic that adjudication cannot change.
- **It is not a human validation.** D9's spot check is pending as one. The
  frozen tool still writes `human_spot_check: "pending"` in every
  `audit-summary.json`, and that field stays true as a statement about humans.
- **The adjudicated FN reading is stable across both model adjudicators.**
  The z-order false negatives of `compare_pptx_files` hold: 33 of 36
  confirmed, and the 3 others sit on a gold-defect task.
- **What it cannot tell apart.** For the alternative-solution and gold-sham
  splits, the reading rests on Claude-family judgment. This record cannot
  separate a gold defect from a shared Claude-family reading.

## Files

| Path | What |
|---|---|
| `adjudications.jsonl`, `spot-check-answers.jsonl` | (a)'s answers, ids and answers only, in the registered order |
| `audit-summary/` | `audit summarize --adjudications` (frozen output, unmodified) |
| `analysis/` | parent analysis with that summary and `--k2-report` (frozen output, unmodified) |
| `isolation/a/` | (a): collector (`collection.json`, `collect-stdout.json`), ingest (`calls.jsonl`, `receipt.json`, `rerate.json`, `ingest-stdout.json`), `rating-run.json`, the workflow script, and `audit_runs-equivalence-check.json` |
| `isolation/b/` | (b): frozen collector output, the frozen ingest's refusal, `audit_runs.json`, `rating-run.json`, script |
| `isolation/c/` | (c): the frozen collector's refusal, `audit_runs.json`, `rating-run.json`, script |
| `isolation/validation/` | `audit_runs.py` on the 2026-10-08 registered rating (equivalence check) |
| `sensitivity/b-fable/`, `sensitivity/c-notation/` | each: `adjudications.jsonl`, `audit-summary/`, `analysis/` |
| `controls/controls.json` | the three byte-for-byte controls |
| `audit_runs.py` | equivalent isolation audit through the frozen functions |
| `summarize_adjudication_v2.py`, `summary.json` | aggregates and agreement tables from committed files only (run from the repository root) |
| `d81-notation-sentence.txt` | D81's sentence as (c) appended it |
| `SHA256SUMS` | every file here |

**Not committed**, because they quote document text: the transcripts, the
answer files with reasons, the ingest's `responses/`, the packets and the
isolated export. They are under the session scratchpad
(`adjudication-v2/`), hashed in `calls.jsonl`, `receipt.json`,
`collection.json` and `audit_runs.json`.
