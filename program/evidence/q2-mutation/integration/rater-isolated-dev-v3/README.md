# D27 dev rerate with both raters: isolated Claude ingest and summary (exploratory)

Development evidence for decisions D25 and D27. The 133 items of the D27 rerate
audit (`../rater-rerate-dev-v3/`, Slurm 700, packets `4a56ba5e...`) were rated
by Claude (claude-opus-5-5) through the agent harness: one agent for each item,
confined to that item's directory under the isolation root. The answers were
audited from the harness transcripts and ingested with the registered path.
They were then summarized with the open-weight rater's answers (Qwen3.6-35B-A3B,
lane job 702). This is the dev split only. Nothing here is a result of the
registration, which is not frozen.

| Step | Where | Record |
|---|---|---|
| Isolated rating | Workflow run `wf_2301520e-159`: 133 agents labelled `rate:0`-`rate:132`, one per item, 2026-10-08 00:18:52-00:28:42 UTC | `claude-isolated/transcript-audit.json`: each agent's tool calls (tool, path relative to its item directory), transcript SHA-256, size and model ids |
| Strict transcript audit | `audit_transcripts.py`, independent of the registered audit and stricter than it (only Read inside the item directory, plus the single StructuredOutput answer) | Same file: 133 transcripts, 1,711 Read calls all inside their own item directory, 133 StructuredOutput answers, no other tool, only claude-opus-5-5. 0 voids. Answers match the journal results and the handed-over list (`claude-isolated/handed-over-answers.txt`) |
| Registered ingest | `rater_runner ingest-isolated` at `2dad9e1` (manifest `84058232...`, iso root re-hashed) | `claude-isolated/calls.jsonl` (`bd364efb...`; answers and digests, with reasons kept only as SHA-256) and `receipt.json`. 133 `ok`, 0 `isolation_void`, every answer taken from the transcript's StructuredOutput, every item tree unchanged since export |
| Held files released | Copied from the host's `held-after-isolated-ingest/` after the ingest. Their SHA-256 match `../rater-rerate-dev-v3/held/SHA256SUMS` | `audit/` (sample, spot-check list, items, baseline jobs), `open-weight/calls.jsonl` (`d6f7346d...`) and `../dev-mutants-v8/` (the campaign export) |
| Registered summary | `audit summarize` (10,000 bootstrap draws, seed 42) | `audit-summary/audit-summary.json`, `audit-summary/decisions.jsonl` |
| Aggregates | `summarize_isolated.py` | `summary.json` |

No GPU was used. The Claude rater ran through the agent harness.

## Findings (exploratory)

- **κ = 0.270** on the 121 real items (raw agreement 0.76). That is below the
  registered 0.6, so κ fires. Under D27 the design goes back to review, and
  the κ rule stays as it is.
- Shams: 12 of 12 right for each rater. The P1 flip was accepted by both.
- Label error, registered (Hajek; items still unresolved count as errors):
  should_pass_equiv 0.133 (bootstrap 0.00-0.29; K3 bound 0.255 on 60 items
  from 15 tasks) and should_fail_violation 0.731 (0.26-1.00; 26 items from 5
  tasks, too few for the K3 bound). Both K3 groups fire, and K4 fires. With
  unresolved items dropped, the estimates are 0.000 (equiv, 52 items) and
  0.300 (violation, 10 items).
- 29 of the 121 real items (24.0%) are split between the raters: 16
  violation, 8 equivalence and 5 extra-change. In 26 of them Claude rejects
  and Qwen accepts. That is about 1.5-2.4 hours of blind adjudication at 3-5
  minutes per item. With the 26-item spot check (4 of which are also split),
  Kevin's workload is 51 items. Unresolved share by class: equiv 0.13,
  violation 0.62, extra-change 0.83, alternative solution 0.
- Each rater against the labels: Claude agrees on 112 of 121 real items. It
  accepts 3 of 26 violation mutants, rejects 5 of 60 equivalence mutants and
  is unsure on 1. Qwen agrees on 94 of 121. It accepts 19 of 26 violations
  and 5 of 6 extra-change mutants, and rejects 3 equivalence mutants. The
  disagreement comes from the open-weight rater accepting should-fail
  mutants, across every violation operator: text edit, deleted bound
  paragraph or shape, and dropped character format.
- Isolation barely changes Claude's answers. On the 109 real items matched to
  the earlier shared-directory (non-blind) answers, the two sets agree on
  93.6% of items (κ 0.84): 5 accept→reject and 2 reject→accept. The earlier
  set's κ against Qwen on those items was 0.34.
- 13 item ids (the 12 shams and the P1 flip) are equal to ids named in the
  committed `rater-smoke-dev-v2` sample. No transcript read outside its own
  item directory, so that file was not reachable through any recorded tool
  call. Claude got all 13 right.
- 12 of the 133 agents did not open every page image in their directory (59
  of 1,114 pages in total). This is a diligence note, not a void condition.

The harness put the same context into every rater agent: the user and
project `CLAUDE.md` files, the memory index, the git status of `main`, and
the skill and tool listings. None of it holds an item, label, verdict or
other rater's answer. The agents' sampling and thinking are not fixed on
this path (disclosed under D25).

Not committed, because they hold document text: the packets, the isolated
item directories, the agents' transcripts and answer files (each SHA-256 is
in `calls.jsonl` and `receipt.json`), the raw response records, and the
earlier non-blind answers (SHA-256 in `summary.json`). `SHA256SUMS` covers
every file here.
