# Evidence bundle: q3-k1-localization-screen-v2 gauntlet, wave 1

Proposal: `program/proposals/2026-10-07-q3-k1-localization-screen-v2.md`.
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`.

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (50). Each record holds the HTTP status, the fetch time, the SHA-256 and size of the full response body, and a metadata extract. For arXiv pages the extract is the title, authors, version history and abstract; arXiv metadata is CC0. For other pages it is the HTML title. Full page bodies and paper full texts are not stored here. |
| `query-log.json` | Every retrieval call of the three discovery cells and the synthesis paper reads, with returned ids and counts against the 150-query budget (159 used). |
| `doctors/` | The six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Copies of the probe 543 attestations: filled manifest, submitter dry-run argv, provenance, container doctor, orx log, both K1 doctors and the derived limits. Also a note that the screen's own attestations do not exist yet. |
| `blind/` | The two anonymized mechanism paragraphs for the blind closest-prior discrimination. File names carry no role. |

Not present, by design or because it does not exist yet:

- **Review receipts.** No reviewer has run. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** It is appended after the reviewers score.
- **The screen's own image B2, manifests and gate-job attestations.** They require a freeze, which requires admission (D24).

The deterministic doctor therefore reports FAIL. That is the expected and honest state for wave 1.
