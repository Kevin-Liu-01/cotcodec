# Evidence bundle: q1-stage0-gate-validation gauntlet, wave 1

Proposal: `program/proposals/2026-10-08-q1-stage0-gate-validation.md`.
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`.

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (36: arXiv abstract pages, GitHub repositories, the KernelBench-M dataset page). Each holds the HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract; arXiv metadata is CC0; other pages: the HTML title). Bodies and paper full texts are not stored. |
| `query-log.json` | Every retrieval call of the frontier, kill-shot and cross-domain cells and of synthesis, with returned ids; 136 orx discover queries against the 150-query budget; paper, metadata and API reads listed but not counted; synthesis full-text reads with their SHA-256. |
| `doctors/` | The six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Copies of the D37 validation job's attestations (Slurm 752, branch `stage0/q1-exec2-validation` at 13f3180, not merged): image build receipt 746, filled manifest, submitter dry-run argv, test-only, provenance, Slurm record, lane files, driver summary, plan, phases, adversarial-control comparison, the pre-specified analysis and the post hoc regime split. Also a note that the Stage 0 run's own attestations do not exist. |
| `analysis/` | Synthesis analyses with their scripts: `tf32_threshold_check.py` (the verification of finding F1 on job 713's journal, SHA-256 ddbfbbf6..., equal to the committed record) and `stop_point_estimate.py` (where the registered 8 GPU-h stop falls under each projection row; an approximation). |
| `blind/` | The two anonymized mechanism paragraphs for the blind closest-prior discrimination. File names carry no role. |

Not present, by design or because it does not exist yet:

- **Review receipts.** No reviewer has run. No trusted Ed25519 store exists (D24), so the signed-review requirement fails.
- **The hash-chained audit row.** It is appended after the reviewers score.
- **The Stage 0 run's own image, manifest, smoke and dry-run.** They need a freeze, which needs admission (D24, D31, D37).

The deterministic doctor therefore reports FAIL. That is the expected and honest state for wave 1.
