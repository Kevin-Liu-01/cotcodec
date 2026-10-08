# Evidence bundle: q3-k1-localization-screen-v3 gauntlet, wave 1

Proposal: `program/proposals/2026-10-08-q3-k1-v3-qwen35-4b.md`.
Draft registration: `program/preregistrations/q3-k1-localization-screen-v3.md` (DRAFT, not frozen).
Schema: `program/proposals/evidence/_schema.json`. Index and hashes: `bundle.json`.

| Path | Contents |
|---|---|
| `snapshots/` | One record per cited primary URL (42). Each holds the HTTP status, fetch time, SHA-256 and size of the full response body, and a metadata extract (arXiv: title, authors, version history, abstract, which are CC0; other pages: the HTML title). No page bodies or paper full texts. |
| `query-log.json` | Every retrieval call of the four discovery cells and of synthesis, with returned ids; 148 counted queries of the declared 150; uncounted paper reads with text digests. |
| `doctors/` | Six preflight doctor records (Source, Citation and Safety PASS; Novelty, Design and Compute FAIL) and the verbatim output of `scripts/research_direction_doctor.py`. |
| `compute/` | Supplementary attestations of the dense pre-check v2's 4B lane (Slurm 862) and its image (build 855): filled manifest, submitter dry-run argv, provenance, container doctor, orx log, CPU doctor, build receipt, the combined read. A note that v3's own attestations do not exist. The synthesis cost and power scripts. |
| `blind/` | Anonymized mechanism paragraphs for the blind closest-prior discrimination: this proposal, the closest prior and a supplementary prior. File names carry no role; the role mapping is in `bundle.json`. |

Not present, by design or because it does not exist yet:

- **Review receipts.** No reviewer has run. No trusted Ed25519 store exists (D24).
- **The hash-chained audit row.** It is appended after the reviewers score.
- **v3's code, images, probe, smoke and manifests.** They need the v3 code, a probe under its own id, Kevin's admission and a freeze.

The deterministic doctor therefore reports FAIL. That is the expected and honest state for wave 1.
