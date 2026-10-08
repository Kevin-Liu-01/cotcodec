# q2-evaluator-mutation-v1, confirm campaign, stage B: ingest, audit summary, registered analysis

Operator record of the steps after the isolated Claude rating of the frozen
`q2-evaluator-mutation-v1` (ledger row 11, hash `dc39bfa2...`, registration
SHA-256 `57dc0092...`, frozen on main at `65bc2e2`). A pre-specified
descriptive protocol under D35 and D38: **nothing here is confirmatory**.
P1 is a replication, the checker candidates and S1-S7 are the descriptive
outputs, and P2-P5 are exploratory under D34 (i). The model raters' audit is
done; **Kevin's adjudication of the pool and the human spot check (D9) are
pending**, and every audit-dependent output below is stated as it stands
before them, with what each becomes once he answers.

The audit stage (rating, collector, ingest, salt, summary) is recorded in
`../audit/README.md`, section "Stage B". This file holds the analysis.

## What ran

All commands ran on this machine from a fresh `git archive` of `65bc2e2`
(3,744 files; `campaign pins` on it equals the frozen pins block, code tree
`58bee019...`; the harness has not changed on main since), with the
worktree's Python 3.13.14 (the modules run here use the standard library
only), `COTCODEC_GIT_SHA=65bc2e2b...`, default seeds and bootstrap sizes
(10,000 resamples, seed 42). No GPU was used and no host job ran; the host
was only read (the held directory and the audit salt).

| Step | Command | Record |
|---|---|---|
| Collector (D38) | `rater_runner collect-transcripts --run-dir <wf_138e30b5-c1a> --manifest iso-manifest.json` | `../audit/claude-isolated/collection.json` (`3a48f6f0...`), `collect-stdout.json` |
| Ingest | `rater_runner ingest-isolated` with both packet copies (`47d17b52...`, `f91104b4...`), the manifest (`f9c91d57...`), the isolation root, the answers, the collected transcripts and the collection | `../audit/claude-isolated/calls.jsonl` (`2120e6ce...`), `receipt.json`, `rerate.json`, `ingest-stdout.json` |
| Salt revealed | host `scratch/audit-salts/confirm-audit-v1/salt.hex` copied after the ingest | `../audit/salt.hex`, `../audit/salt-check.json` (`salt_check.py`) |
| Held files released | host `held-after-isolated-ingest-confirm-v1/` copied after the ingest, every file checked against the committed digests | A2 set in `../audit/released/` (7 files, `../audit/held/SHA256SUMS`), A1 set in `released/` (18 files, `../held/SHA256SUMS`) |
| Audit summary | `audit summarize --sample sample.jsonl --anthropic-calls calls.jsonl --open-calls calls-s000.jsonl calls-s001.jsonl` | `../audit/audit-summary/` |
| Registered analysis | `python -m harness.q2_mutation.analysis --outcomes released/confirm-mutants-v1/outcomes.jsonl --controls-summary released/controls/confirm-controls-v1.summary.json --reserve-controls-summary released/controls/reserve-controls-v1.summary.json --audit-summary ... --decisions ...` (no `--k2-report`: no K2 executor exists) | `analysis.json`, `analysis-stdout.json` |
| Aggregates | `summarize_confirm.py` (counts from the committed files only; no decision) | `summary.json` |

Every command exited 0 with an empty stderr.

## P1 gold fixed point (replication only)

92 counted golds (confirm 67, reserve 25), 14 not exposed (listed in
`analysis.json`), none not counted. Raw flips **4/92 = 4.35%** (exact 95%
1.20-10.76%): confirm 30e3e107, 9ec204e4, b8adbc24; reserve 3a7c8185.
Audit: both raters accept the saved gold of 3a7c8185, 9ec204e4 and b8adbc24,
both reject that of 30e3e107. **Audit-confirmed flips 3/92 = 3.26%** (exact
95% 0.68-9.23%). No P1 flip is in Kevin's pool, so this does not change with
his answers. (Headless scoping round trip, another save path: 7/63 and
1/26.)

## Checker candidates (descriptive, `analysis.checker_candidates`)

Population: the 444 evaluable mutants outside probe-touched cells (60
tasks). Every candidate was audited (census); each is listed in
`analysis.json` with mutant id, task, checker family, operator, label,
verdict, audit decision, reading and gold-defect flag (none is on a
gold-defect task, because no gold sham is decided reject yet).

**False negatives: 36 candidates**, all `should_pass_equiv`, all
`pptx.eq.zorder_nonoverlap` (35 `compare_pptx_files`, 1
`compare_pptx_files_tolerant`, 16 tasks); no alternative solution fails.

| Reading | Count |
|---|---:|
| confirmed (both raters accept) | 30 (29 `compare_pptx_files`, 1 `compare_pptx_files_tolerant`) |
| unresolved (raters split; in Kevin's pool) | 6 (`compare_pptx_files`) |
| label contradicted | 0 |

Task-equal candidate share (task-cluster percentile bootstrap, 10,000, seed
42): pooled **12.4% (7.2-18.3%)** of 348 evaluable should-pass mutants on 60
tasks; per label `should_pass_equiv` 12.4% (7.2-18.3%, 255 mutants),
`should_pass_alt_solution` 0 of 93 (16 tasks); per family
`compare_pptx_files` **40.2% (32.9-46.3%, 85 mutants, 16 tasks)**,
`compare_pptx_files_tolerant` 1 of 1, every other family 0 (`compare_table`
0 of 218 on 30 tasks, `compare_docx_files` 0 of 18, `compare_docx_images`,
`compare_docx_tables`, `compare_line_spacing` 0 of 6 each,
`compare_csv+compare_table` 0 of 5, `evaluate_strike_through_last_paragraph`
0 of 3); per operator `pptx.eq.zorder_nonoverlap` **91.7% (81.3-100%, 36 of
40 mutants, 16 tasks)**, every other should-pass operator 0
(`pptx.eq.subvisible_nudge` 0 of 46, `xlsx.eq.view_selection` 0 of 85,
`xlsx.eq.view_zoom` 0 of 37, `docx.eq.view_zoom` 0 of 36,
`xlsx.alt.literal_for_formula` 0 of 39, `xlsx.alt.absolute_refs` 0 of 34,
`xlsx.alt.sum_range_expand` 0 of 11, `xlsx.eq.active_sheet` 0 of 10, and
smaller cells). Audit-confirmed share (unresolved counts as not confirmed):
pooled **10.6% (5.8-16.2%)**, `compare_pptx_files` 33.5% (24.8-41.7%),
`pptx.eq.zorder_nonoverlap` 77.1% (61.5-90.6%).

**False positives: 5 candidates**, all `should_fail_violation` (no
extra change passes outside probe-touched cells).

| Mutant (task prefix, operator) | Family | Decision | Reading |
|---|---|---|---|
| 358aa0a7 `pptx.alt.textbox_for_placeholder` (2 mutants) | `compare_pptx_files` | both accept | label contradicted (pending Kevin) |
| 70bca0cc `pptx.viol.drop_char_format` | `compare_pptx_files` | both reject | confirmed |
| a434992a `pptx.viol.drop_char_format` | `compare_pptx_files_tolerant` | both accept | label contradicted (pending Kevin) |
| d53ff5ee `docx.viol.text_edit` | `compare_docx_files` | both reject | confirmed |

Task-equal candidate share: pooled **5.9% (0.8-12.3%)** of 96 evaluable
should-fail mutants on 26 tasks; per label violation 6.1% (0.8-13.1%, 91
mutants, 25 tasks), extra change 0 of 5; per family `compare_docx_files`
5.0% (0-15.0%), `compare_pptx_files` 6.7% (0-17.8%),
`compare_pptx_files_tolerant` 1 of 3, `compare_line_spacing` 0 of 7,
`compare_table` 0 of 21; per operator `pptx.viol.drop_char_format` 2 of 6,
`pptx.alt.textbox_for_placeholder` 2 of 6, `docx.viol.text_edit` 1 of 6,
every other 0 (`pptx.viol.delete_bound_shape` 0 of 34,
`docx.viol.delete_bound_paragraph` 0 of 14, `xlsx.viol.clear_bound_cell` 0
of 9, and smaller cells). Audit-confirmed share: pooled **2.1% (0-5.4%)**
(2 events).

Probe-touched cells (counted, never audited): no false-negative event; 28
false-positive events (15 extra changes, 13 violations): `compare_table`
12, `compare_docx_tables` 7, `compare_docx_images` 6, `compare_docx_files`
3. No family was dropped by K2 (no K2 report).

## P2-P5 (exploratory; out of the confirmatory headline)

Every one leaves the headline for "D34 (i): development kappa below 0.6",
and the confirm audit adds K3 reasons (below); they are reported with the
same tables.

- **P2** (equivalence mutants plus the 72 alternative solutions the audit
  accepted; 327 mutants, 60 tasks): **12.4% (7.2-18.3%)**;
  `compare_pptx_files` 40.2% (32.9-46.3%, 16 tasks, K7 flag: unreliable for
  P2, descriptive); `compare_table` 0 of 197 on 30 tasks (zero-event bound
  9.5%: K6b flag, no detected P2 error under this operator set,
  descriptive); every other family 0. Gate: 72 alternative solutions
  accepted, 3 rejected, 18 unresolved (the 21 not accepted stay out of P2
  and are in Kevin's pool).
- **P3** (91 violation mutants, 25 tasks): **6.1% (0.8-13.1%)**;
  `compare_pptx_files` 6.7% (0-17.8%, 15 tasks, at the family floor, no K7
  flag), `compare_docx_files` 5.0%, `compare_pptx_files_tolerant` 1 of 3.
- **P4** (5 extra changes the checker fails, none it passes): **0 of 5** on 2
  tasks; with unresolved passed items as events, the same.
- **P5** (60 evaluable tasks): **17 tasks with an FN or FP_R event, 28.3%**
  (exact 95% 17.5-41.4%).
- Gold defects: none decided; P2 without gold-defect tasks is therefore not
  computed (null).

## S1-S7

- S1 dependency flips: none (no venv disagreement; `released/confirm-mutants-v1/report.json` `s1`).
- S2 script-writer stratum: empty (the catalog has no such operator).
- S3 normalization: 23 of 1,232 admitted mutants lost their edit in the save
  (1.9%); the largest operator share 6/19 (`xlsx.extra.clear_unrelated_row`);
  K5 fires for no operator.
- S4 save timing: mutation run 96 of 1,300 saves slower than 0.5 s (7.4%,
  slowest 1.20 s); controls 7 of 135 (confirm), 0 of 52 (reserve).
- S5 nondeterministic checkers: none (repeat 2 and repeat 5).
- S6 audit agreement per label class (census; `../audit/audit-summary/audit-summary.json`):
  equivalence 36 audited, 30 accepted (agrees 83.3%), 6 unresolved (16.7%);
  violation 5, 2 rejected (agrees 40%), 3 accepted; alternative solution 93,
  72 accepted (gate share 77.4%), 3 rejected, 18 unresolved (19.4%); extra
  change 0 audited. Per rater and sham accuracy below.
- S7 null-mutant failures: 7 of 68 targets (10.3%); K9 does not fire.

Ambiguous labels (counts per witness rule and lock verdict, never rates; 186
mutants): `summary.json` `ambiguous_by_witness_rule_and_lock_verdict`.

## Audit statistics (model raters; adjudication and human check pending)

- Cohen's κ on the 138 real items (three answers): **0.343** (raw agreement
  114/138 = 82.6%), below 0.6. Adjudication never changes κ.
- Sham accuracy: Claude 36/40 (0.90: gold 29/33, do-nothing 7/7), Qwen 39/40
  (0.975: gold 32/33, one `unsure`, do-nothing 7/7).
- Call outcomes: Claude 177 `ok`, 1 `isolation_void`; Qwen 172 `ok`, 6
  `thinking_unfinished`; no refusal, timeout, rejected request or unrated
  item.
- Decisions by stratum (`summary.json` `decisions_by_group`): `fn_equiv` 30
  both accept, 6 split (3 each way); `fp_violation` 3 both accept, 2 both
  reject; `alt_gate` 72 both accept, 3 both reject, 18 split (12 Claude
  reject/Qwen accept, 5 Claude reject/Qwen unsure, 1 Claude void/Qwen
  accept); P1 flips 3 both accept, 1 both reject; gold shams 29 both accept,
  4 split (Claude rejects all four); do-nothing shams 7 both reject.
  Unresolved real items: 24 of 138 (17.4%).
- The four split gold shams are on 4 tasks that also hold 3 of the 6 split
  equivalence candidates, 14 of the 18 split alternative solutions and 2 of
  the 3 both-rejected ones: most of Claude's rejections of candidates sit on
  tasks whose gold it also rejects. If Kevin rejects a gold sham, that task
  is a gold-defect task (D34).
- K3 label error (Hajek; unresolved counted as errors): equivalence group
  **0.167** (36 items, 16 tasks, bootstrap 0.028-0.35, bound 0.314,
  sufficient), 0.000 with unresolved dropped (sensitivity); violation group
  **0.600** (5 items, 4 tasks, insufficiently audited). K3 fires for both
  groups and for κ: reported only (D35).

## K criteria

- K1: 70/74 PASS (stage A1).
- K2: no executor; the analysis carries the registered label "offline
  harness, VM fidelity unverified"; no family dropped.
- K3: fires (κ 0.343 < 0.6; equivalence bound 0.314 > 0.10; violation group
  insufficient); consequence reported only, after the D34 exit.
- K4: fires (both groups above 10%); reported only, no stop (D35).
- K5: no operator above 50% normalization.
- K6: retired (D35), reported blocked: by D35, D34 (i), κ and both K3 groups;
  P5 60 tasks with 17 escapes, 3 confirmed P1 flips.
- K6b (descriptive): `compare_table` for P2 (0 events on 30 tasks, bound
  9.5%).
- K7 (descriptive): `compare_pptx_files` for P2 (lower limit 32.9% > 5%).
- K8: not run here (before drafting a note).
- K9: 7/68 null-mutant failures, does not fire (families with a failing
  null: `check_tabstops`, `compare_pptx_files`, `compare_table`).

## Pending for Kevin (D9, D34, D38)

**Adjudication pool, 34 items** (`../audit/audit-summary/adjudication-pool.jsonl`,
ids only, in the registered seeded order; composition: 24 splits, 6
concordant contradictions, 4 split gold shams). Adjudicate from each item's
blind packet. The released `sample.jsonl`, `decisions.jsonl`,
`analysis.json`, `summary.json` and this file name labels, decisions and
sham status, so to stay blind, answer before reading them. Answers go to a
JSONL of `{item_id, answer}` (accept or reject), then rerun `audit summarize
... --adjudications <file>` and the analysis; an answer for an item outside
the pool is refused.

**Human spot check, 25 items** (`../audit/released/confirm-audit-v1/spot-check.jsonl`,
`raters.human_spot_check`: 10 alternative solutions, 5 equivalence
candidates, 5 violation candidates, 5 shams); 7 are also in the pool (52
distinct items in all). The check stays "pending" in every result until
done.

What each output becomes once he answers (bounds in `summary.json`
`pending_ranges`):

- False-negative candidates: 30 confirmed now; each of the 6 split items
  becomes confirmed (accept) or label contradicted (reject): 30-36
  confirmed.
- False-positive candidates: 2 confirmed now; the 3 both-accepted ones
  stand as label contradicted until he answers; his reject confirms them:
  2-5 confirmed.
- P2's gate: 72 alternative solutions in P2 now; his accept adds any of
  the 18 split and 3 both-rejected ones (72-93); P2's events do not change
  (the checker passes them), only its population.
- Gold defects: none now; each split gold sham he rejects makes its task a
  gold-defect task (0-4), whose equivalence items then leave the
  equivalence K3 group and P2 is also reported without them.
- K3 label errors fall as he resolves items (equivalence 0.167 to as low as
  0, violation 0.6 to as low as 0); K4 then fires only if both groups stay
  above 10%. κ, P1, P3, P4, P5 and the candidate shares do not change.

## Not committed

The transcripts, the per-item answer files (with reasons), the raw response
records, the packets and the isolated export (document text); each is
hashed in `calls.jsonl`, `receipt.json` and `collection.json`.

`SHA256SUMS` covers every file here.
