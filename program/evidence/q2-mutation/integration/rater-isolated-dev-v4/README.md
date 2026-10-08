# D34 dev rerate with both raters: isolated Claude ingest and summary (exploratory)

Development evidence for decision D34. The 142 items of the D34 rerate audit
(`../rater-rerate-dev-v4/`, `dev-audit-v4`, Slurm 720, packets `5598e755...`)
were rated by Claude (claude-opus-5-5) through the agent harness, one agent
per item confined to that item's directory under the isolation root, started
with the registered prompt template (SHA-256 `0e9d4eb6...`). The answers were
audited from the harness transcripts, ingested with the registered path and
summarized with the thinking-on open-weight rater's answers (Qwen3.6-35B-A3B,
lane job 722). Dev split only; nothing here is a result of the registration,
which is not frozen.

| Step | Where | Record |
|---|---|---|
| Isolated rating | Workflow run `wf_65ce9899-24a`: labels `rate5:0`-`rate5:141`, one per item, 2026-10-08 03:10:26-03:43:30 UTC. The session ended once while raters were running and the workflow was resumed: 16 labels (`rate5:26`-`28`, `30`-`32`, `36`, `37`, `39`, `41`-`47`) have an interrupted agent (no journal result) and a completed rerun; the rating is the completed agent's | `claude-isolated/transcript-audit.json`: all 158 agents (142 completed, 16 interrupted), each tool call (tool, path relative to the item directory), transcript SHA-256, size, model ids, user turns |
| Strict transcript audit | `audit_transcripts.py`, independent of the registered audit and stricter (rule in its docstring and in the file) | 0 voids. Completed agents: 1,789 Read calls, all inside their own item directory, and 142 StructuredOutput answers, each naming its item; no other tool. Interrupted agents: 165 Read calls, all inside their own item directory, no other tool, no answer; none voids its item. Only claude-opus-5-5 (2,815 agent turns). In all 158 agents the computed-task turn is byte-identical to the template rendered for its item inside the harness's fixed wrapper; no transcript holds another item's id; every item tree re-hashes equal to its export; answers equal the journal results and the handed-over list (`claude-isolated/handed-over-answers.txt`) |
| Registered ingest | `rater_runner ingest-isolated` at `b29034e` (manifest `78d9a37b...`, iso root re-hashed) | `claude-isolated/calls.jsonl` (`896f3cdd...`), `receipt.json`, `ingest-stdout.json`: 32 `ok`, **110 `isolation_void`**, all for "the first user prompt is not the registered template rendered for this item" (see below) |
| Sensitivity ingest (not registered) | `claude-isolated-relay-excepted/ingest_relay_excepted.py`: the same `ingest_isolated` with one turn, byte-identical to the harness's relay of the session user's request (SHA-256 `8e7dbd00...`), not counted as a prompt; every other check unchanged | `claude-isolated-relay-excepted/calls.jsonl` (`176aa58d...`), `sensitivity-result.json`: 142 `ok`, 110 relay turns excepted |
| Salt revealed | Host `scratch/audit-salts/dev-audit-v4/salt.hex` (mode 600), copied after the ingest | `audit/salt.hex`: SHA-256 of its 64 hex characters is `1660a49d...`, the digest committed in `../rater-rerate-dev-v4/audit/sample-summary.json`; all 142 sample item ids recompute from it with `raters.opaque_item_id` |
| Held files released | Copied from the host's `held-after-isolated-ingest-v4/` after the ingest; the host's `SHA256SUMS` is byte-equal to `../rater-rerate-dev-v4/held/SHA256SUMS` and all 18 files match it | `audit/` (sample, spot-check list, items, baseline jobs), `open-weight/calls.jsonl` (`d1a3e00b...`), `../dev-mutants-v9/` (the campaign export) |
| Registered summary | `audit summarize` on the registered calls (10,000 bootstrap draws, seed 42) | `audit-summary/` (summary, decisions, adjudication pool) |
| Sensitivity summary | `audit summarize` on the sensitivity calls | `audit-summary-relay-excepted/` |
| Aggregates | `summarize_isolated_v4.py` | `summary.json` |

No GPU was used.

## Why the registered ingest voids 110 items

The registered transcript audit (D34, prereg section 9) takes an agent's
first user turn that is not a tool result as its prompt and requires it to be
the rendered template, bare or in the workflow harness's fixed wrapper. After
the workflow was resumed, the harness put one extra turn before the computed
task of every agent it started: a relay of the session user's request
("continue all work."), byte-identical in all 110 agents. Their computed-task
turn that follows is the rendered template exactly, but it is the second user
turn, so the registered rule voids them. The 32 `ok` items are the agents
that completed before the session ended (no relay turn); the 16 interrupted
agents also had none. The relay turn names no item, label, verdict or other
rater's answer. The registered rule is unchanged here; whether to register
the relay turn, or to require fresh (unresumed) rating runs, is open for
Kevin before the freeze.

## Findings (exploratory)

Registered (110 Claude answers void, so `unsure`): κ = **0.066** on the 121
real items (raw agreement 0.18). Claude sham accuracy 5/21, Qwen 20/21. Label
error, unresolved items as errors: equivalence 0.842, violation 0.923; K3
fires for both groups and K4 fires. 100 of 121 real items unresolved;
adjudication pool 113 (100 split, 1 concordant contradiction, 12 split gold
shams). These numbers measure the voids, not the raters.

Relay turn excepted (all 142 answers `ok`; sensitivity, not registered):

- κ = **0.575** on the 121 real items (raw agreement 0.843), below the
  registered 0.6. (If Claude had matched every label, κ would have been 0.578;
  `../rater-rerate-dev-v4/summary.json`.)
- Shams: Claude 19 of 21 right (gold 13 of 15, do-nothing 6 of 6), Qwen 20
  of 21 (gold 14 of 15). The P1 flip was accepted by both.
- Gold defects (D34 ii): one task (`e528b65e...`), whose gold sham both
  raters rejected; its 3 equivalence items leave the equivalence K3 group (1
  decided reject, 2 unresolved).
- Label error per K3 group (Hajek; unresolved items count as errors; gold
  defects removed): equivalence 0.070 (bootstrap 0.00-0.20; K3 bound 0.179 on
  57 items from 14 tasks, sufficient, above 0.10) and violation 0.577
  (0.19-0.89; 26 items from 5 tasks, too few for the bound). Both K3 groups
  fire (κ fires in any case); K4 does not fire. With unresolved items dropped:
  equivalence 0.000 (53 items), violation 0.154 (13 items).
- Unresolved: 20 of 121 real items (16.5%). Hajek share by class:
  equivalence 0.10, violation 0.50, alternative solution 0.04, extra change
  0. 16 of the 20 splits are Claude reject / Qwen accept (12 violation, 4
  equivalence).
- Adjudication pool (D34 iii): 24 items (20 splits, 3 concordant
  contradictions, 1 split gold sham), about 1.2-2.0 h at 3-5 minutes per
  item. With the 26-item spot check (2 of them also in the pool), Kevin's
  workload is 48 items.
- Each rater against the labels: Claude accepts 3 of 26 violation mutants,
  rejects 5 of 60 equivalence mutants (1 unsure), accepts 28 of 28
  alternative solutions and rejects 6 of 6 extra changes. Qwen with thinking
  accepts 14 of 26 violations.

**D34 (i).** Development κ is below 0.6 under the registered ingest (0.066)
and with the relay turn excepted (0.575), so the consequence does not depend
on how the 110 voids are read: no other rater is tried; P2-P5 leave the
confirmatory headline before the confirm campaign runs, and the campaign
reports P1 and the checker false-negative candidates descriptively.

Diligence (not a void condition): every completed agent opened `packet.txt`
and every page image in its directory (1,228 pages). 102 of 142 were shown
every line of `packet.txt`; 40 were not (the lowest saw 56% of its lines;
121 Read truncation notices in all).

The harness put the same context into every rater agent (disclosed in
section 9): the user and project `CLAUDE.md` files, the memory index, the git
status of `main`, the skill and tool listings, and session reminders. None of
it holds an item, label, verdict or other rater's answer.

Not committed, because they hold document text: the packets, the isolated
item directories, the agents' transcripts and answer files (each SHA-256 is
in `calls.jsonl`, `receipt.json` and `transcript-audit.json`) and the raw
response records. `SHA256SUMS` covers every file here.
