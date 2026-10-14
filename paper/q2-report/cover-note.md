# Cover note to the Q2 report draft (internal; not part of the report)

This note travels with `paper/q2-report/draft.md` and is not part of the outward report. It holds
the program-record material that revision 1 carried in its section 9: the pending sign-offs keyed
to `program/state.json`, and the discrepancies in the program record found while drafting. Remove
it, or keep it out of any circulated copy, before the report is shared.

## Pending sign-offs, keyed to `program/state.json`

Indices are 0-based positions in `pending_decisions_for_kevin` at commit `360058d`. Each index
points at the same item at `08033ba7`, against which revision 3 updated the checker-study rows
and the successor-E row, and at `4ca30d03`, against which revision 6 updated the successor-E row
again and the review row (index 12, which now reads "Done (D92)").

| Item | Index | What it affects in the report |
|---|---:|---|
| Publication of the report | (D71 (iii); not an index) | everything; an outward action |
| Disclosure to xlang-ai of the checker defects (and the earlier OSWorld findings) | 3 | section 6; must be settled before publication (the owner may decline to disclose) |
| Checker-mutation adjudication, 34 items: done under D80-D82 by an isolated model, not human-validated; the outward actions and the registration's carried-over sign-offs stay the owner's | 8 | section 6.7's before-and-after table; a human adjudication could change the gold-defect calls and the audit-confirmed counts |
| Human spot check, 25 items (D9): optional, and the only independent validation; the isolated model that answered it under D80-D82 matched the Claude rater on all 25 | 6 | every audit-dependent output in section 6 |
| Release of the checker study's blind specs, published before sign-off | 13 | the public checker-study materials |
| Review of decisions taken on the owner's behalf: done for D1-D91 under D92 (the owner approved all pending items on 2026-10-12); D93 onward, including D96 and D97 cited for successor E, are not covered by it | 12 | D53 and D57 (action path accepted; S1a session-1 disclosures), D56 (S1a sign-off), D59-D62 (analysis-code defects), D66, D69, D79-D82 (K2 and the model adjudication, section 6), D85 (E's sign-off). The report's statements that these decisions await the owner's review ("Authorship and process", section 4.1, limitation 12 and section 12) predate D92; revision 6, which brings only successor E up to date, leaves them unchanged, and the next revision should correct them. D92 also gave the checker-mutation registration's carried-over sign-offs, the blind-spec release among them, which the rows for indices 8 and 13 (and index 13 itself) still list as open |
| Action path: shell-side observation of grabbed chords; the job 851 guest-server restart; the A4/A7 governance deviation | 14 | sections 2.6-2.7 and 11 |
| Host inotify limit (host administrator) | 16 | V* = 32 and the concurrency scope |
| Successor E: decided under the owner's delegation (D80 (iii)), signed off and frozen (D85, ledger row 19), run and analysed; its result is verified (D97): DR2 Near-equivalent, DR5 NO-GO. Nothing here is the owner's unless he wants an observation-factor study proposed. The item at index 17 still says the results wait for a fresh verifier (discrepancy D7) | 17 | sections 4.9-4.10, 5, 6.6, 7.1 and 11, and the summary |
| A valid Anthropic API key (the Claude rater ran through the agent harness, D25) | 9 | section 6's rater path |

Also open, not the owner's:

- the S1a runbook's step-12 verification record;
- a second check of the session-2 lane checks (`program/evidence/2026-10-10/q2-stage1-a1/RESULTS.md`,
  disclosures 4-5).

## Discrepancies in the program record found while drafting

These are in the program record, not in the evidence. Each should be corrected at its source
before the report is circulated.

- **D1. δ's direction in D66.** D66 calls pooled δ "H-OSW-fixed minus H-GA". The registration
  (`q2-stage1-rescoped-v1`, section 2) and S1a's RESULTS define δ = H-GA − H-OSW-fixed, and the
  value −3.1 pp follows that definition: success 26.56% against 28.91% at 4B, and 28.91% against
  32.81% at 9B. The report uses the registered definition.
- **D2. D69's variance shares.** D69's "rerun noise is 20-33% of outcome variance and
  task-by-harness variance 3-4%" are the probability-scale shares of `fit-base` (N0). That
  calibration fails the design study's extended check at 4B. Under the four passing calibrations,
  task-by-harness is about 3-4% at 9B and at most 1% at 4B, and rerun is about 21-27% (report
  section 5.3).
- **D3. "35 of 36" in `HANDOFF.md` (State table) and `program/state.json` pending decision 3.**
  Both say `compare_pptx_files` fails "35 of 36 equivalent edits". The evidence gives 35 of 39
  evaluable reorder mutants on `compare_pptx_files`, and 36 of 40 with the tolerant variant (S1a
  registration section 8; `harness/q2_stage1/zinv.py`; the checker study's results README). 36 is
  the total number of false-negative candidates. The disclosure text should be corrected before it
  is sent. Resolved at the source: D72 (iii) records the correction, and `HANDOFF.md` and
  pending decision 3 now give 35 of 39 for `compare_pptx_files`. Per the checker-mutation note
  (D83), any disclosure gives a confirmed count as 30 by both raters, or as 33 after the D82
  model adjudication with the D80 label.
- **D4. "Independently verified".** The phrase "independently verified (D66)" is in `HANDOFF.md`
  (State table, S1a row), not in D66. D66's own words are "Two fresh verifiers reproduced the
  analysis, one recomputing it from the raw records and one checking every claim". That
  overstates what ran: `program/log.md` (2026-10-10) records two review lenses, a recompute (which
  reproduced every re-runnable output off the host, but not the GLMM fits) and a claims check, and
  the runbook's own step-12 verification has no committed record (RESULTS, disclosure 5).
- **D5. 107,988 in the action-path README.** The README's "Independent verification of stage B"
  paragraph (`program/evidence/2026-10-08/q2-action-path-v2-acceptance/README.md`) says the
  verifier re-judged "all 107,988 ladder, A4 and A7 trials". The verifier's own `checks_run`
  (`independent-verification-stage-b.json`) gives the ladder 14,000, A4 64,028 and A7 30,960,
  which sum to 108,988.
- **D6. A stale status line.** `harness/q2/README.md` still calls `q2-action-path-v2` a draft
  whose acceptance trials wait for its freeze. It was frozen and accepted on attempt 1 (D53).
- **D7. E's verification status in `program/state.json`.** Pending item 17 at `4ca30d03` gives
  E's result "(RESULTS pending a fresh verifier)". E's RESULTS (its verification status and
  deviation 1) and D97 record that two fresh verifiers ran, reproduced every registered number
  and outcome and found no blocking item, and that their wording items were fixed (`fddff98e`).
  The report follows RESULTS.
