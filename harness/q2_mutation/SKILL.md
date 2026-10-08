---
name: harness-q2-mutation-skill
description: Procedure for the Q2 OSWorld checker-mutation harness (q2-evaluator-mutation-v1) in harness/q2_mutation/.
---

# cotcodec / harness / q2_mutation

## Purpose
<!-- agent-docs:fill:purpose -->

q2-evaluator-mutation-v1 measures how often OSWorld-Verified's file-state
checkers reject correct end states and accept wrong ones. Blind requirement
specs label each mutant; operators edit gold files; the VM's own LibreOffice
re-saves every office candidate before the pinned `DesktopEnv.evaluate()`
scores it. Runbook: `README.md` in this directory.

## Mental model & key files
<!-- agent-docs:fill:model -->

- `schema.py` is binding across branches; copy it verbatim, never edit it here.
- `campaign.py` drives a run: `targets` -> `build` -> `reach.sh` -> `merge` ->
  scoring -> `recheck` -> `report` -> `export`; `guard` and `pins` enforce
  the preregistration.
- `reachability.py` is the GUI-faithful save stage; `save_failures` decides
  whether a candidate was really saved, and `step_may_write` which unemulated
  steps exclude a task.
- `controls.py` builds gold and do-nothing jobs and merges saved files;
  `offline_eval.py` scores; `report.py` summarizes control runs (K1, P1).
- `operators/` is the 64-operator catalog with its stdlib snapshot, diff and
  purity oracle; its sources are hashed into `catalog_sha256`.
- `raters.py`, `packets.py` and `stats.py` hold the D9/D23 audit: the D35
  census of the checker candidates and P2's gate (stratified fallback at the
  largest budget that fits the GPU cap's capacity, D38), blind
  packet (built from the operators' snapshot), answer rule, consensus,
  adjudication and the K3 bound; `audit.py` builds samples, saved-start
  baselines, packets fitted to the token budget and the summary (one calls
  file per shard and rater); `rater_runner.py` makes the model calls (one per
  rater per item, hashed receipts), runs the open-weight rater
  (Qwen3.6-35B-A3B, D27, thinking on since D34) and exports/ingests the
  agent-harness Claude rater one item per directory with a transcript audit
  tied to the registered prompt template `templates/isolated_rater_prompt.txt`
  (D25, D27, D34) that checks every user turn and every transcript of an item
  (D35), collected from the rating run by `collect-transcripts` (D38);
  `analysis.py` is the registered analysis, descriptive since D35
  (`D34_DEV_EXIT` keeps P2-P5 out of the confirmatory headline;
  `checker_candidates` is the descriptive output).

## Patterns to follow / invariants
<!-- agent-docs:fill:patterns -->

- An office candidate is scored only after its save wrote every office file;
  otherwise it is an infrastructure exclusion, never a verdict.
- Every exclusion has its own status in `campaign.classify`; nothing is
  relabelled or silently dropped.
- Committed evidence goes through `campaign export` only: recipes can quote
  gold text, mutant files are third-party content and stay on the host.
- Every code change inside the pinned tree moves `code_tree_sha256`; refresh
  the preregistration's pins block (`campaign pins`) and rerun the dev
  campaign before the freeze. README and SKILL files are outside the digest.

## Common tasks → first action
<!-- agent-docs:fill:tasks -->

| Task | First action |
|---|---|
| Change harness, operator or infra code | Run the Q2 tests, then `uv run python -m harness.q2_mutation.campaign pins --root .` and update the pins block. |
| Run on the host | Stage `git archive HEAD` under `src/<sha>`; dev split only before the freeze. |
| Add a release file | Route it through `campaign export` and extend `tests/test_q2_mutation_integration_evidence.py`. |

## Gotchas
<!-- agent-docs:fill:gotchas -->

- `reachability.py` runs under the LO-VM image's Python 3.10 with the
  standard library only; `uno_apply.py` must stay Python 3.8 compatible.
- A LibreOffice save is not byte-deterministic, so mutant ids change between
  runs while sites, labels and outcomes reproduce.
- The GPU device files on the host are world-writable: every container runs
  without `--gpus` through `q2-mutation-cpu.sbatch`.
- A rater lane job must end before the lane's USR1 (180 s before its limit)
  or stop on it: `rater_runner open` gives requests in flight 60 s, stops
  the engine and leaves with `os._exit`. Size the limit from the measured
  rate, and read the GPU cap from the ledger (`render_rater_manifest.py
  --gpu-ledger`), never by hand.
- Isolated Claude rater: never put an index, label, sample or other item
  under the isolation root; the manifest lives outside it. Start each agent
  with the registered template rendered for its item, verbatim (the audit
  needs exactly one user turn equal to it; the only other turn allowed is the
  harness relay frame of a resumed run). Run the rating as one workflow
  session of rater agents only, and take the transcripts with
  `rater_runner collect-transcripts` (D38), never by hand: it maps every
  `agent-*.jsonl` to its item, refuses one it cannot map, writes
  `<item>.jsonl` and `<item>.<agent id>.jsonl` and the manifest
  `ingest-isolated --collection` checks; all are audited (D35). A resume
  with another session request voids every framed item; re-rate the
  `rerate.json` items once in a fresh, unresumed session (D38).
  Never message a rater agent while it runs: the harness delivers the message
  as a `queued_command` attachment, which voids the item, as does any entry
  or attachment type outside `rater_runner.TRANSCRIPT_ENTRY_TYPES` and
  `HARNESS_ATTACHMENT_TYPES`.
- Audit salts (D34) live only on the host (`scratch/audit-salts/<audit>/`,
  mode 600); commit the SHA-256 and reveal the salt only after the ingest.
