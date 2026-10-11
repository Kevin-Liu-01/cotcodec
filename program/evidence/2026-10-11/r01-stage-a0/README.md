# R01 Stage A0: records-only census of S1a's greedy rerun disagreement

CPU only, model-free, 2026-10-11. Part of the draft registration
`program/preregistrations/r01-rerun-noise-sources-v1.md` (section 5.1); a post hoc description
of S1a's data that enters no decision rule.

| File | What |
|---|---|
| `derive_digests.py` | Builds the hashes-only per-step table from a read-only copy of S1a's 3,616 host step and reply logs; refuses any file whose SHA-256 differs from the committed per-job host listings (`../../2026-10-10/q2-stage1-a1/*/vm-*/raw-sha256sums.txt`) |
| `s1a-step-digests.jsonl.gz` | 1,808 episode rows, 22,274 steps: 16-hex prefixes of the request, messages, prompt-id, screenshot and IR digests and of the reply text's SHA-256, token counts, latencies, finish reason; no text, image or host name (SHA-256 `91f84843...`) |
| `derive-report.json` | Input verification counts and the common-prefix statistics of the natural replays' replies (these need the text) |
| `census.json` | Output of `scripts/run_r01_stage_a0_doctor.py` (SHA-256 `5568bc7f...`) |
| `orx-run-83ee815a-...log` | The orx cpu-doctor run (node `ff110047`, branch `orx/r01-stage-a0-records-census`, commit `ca3cdbf`, local backend): `ORX_RESULT ... exit=0`; its receipt is byte-identical to `census.json` |

Headline counts (all labelled "not externally anchored"): 27 natural identical-request replays
(19 within-session pairs), reply text differs on 16 (0.59, Wilson 0.41-0.75) and IR on 2;
identical step-1 inputs did not lower outcome discordance (2 of 19 against 90 of 885); 227 rerun
pairs with identical IR sequences, 0 verdict-discordant (exact one-sided 95% upper bound 1.31%
per pair, 4.95% per size-task unit), 162 of them with different checker-input digests; 10 of 25
clearly same-minute pairs have different step-1 screenshots, all in LibreOffice and GIMP tasks.
