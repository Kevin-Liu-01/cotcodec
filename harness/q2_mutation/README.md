# harness/q2_mutation

Offline harness for the Q2 OSWorld-Verified checker-mutation study
(preregistration draft: `program/preregistrations/q2-evaluator-mutation-v1.md`).
Branches: harness `stage0/q2-mut-harness` (this code), specs
`stage0/q2-mut-specs`, operators `stage0/q2-mut-operators`, integration
`stage0/q2-evaluator-mutation`.

## Modules

| Module | Runs in | Role |
|---|---|---|
| `schema.py` | anywhere (stdlib) | Binding record formats, `q2-mutation-schema-v1`. Other branches copy it verbatim. |
| `tasks.py` | repo venv | Scope (205 offline-checkable, web-free tasks), classification, sanitization, seeded splits |
| `controls.py` | metric image | Gold and do-nothing jobs; merges the save stage's outputs |
| `reachability.py` | LO-VM image (Python 3.10, stdlib) | GUI-faithful LibreOffice save: Xvfb + openbox, the VM's LibreOffice and profile, postconfig replay, pyautogui keys |
| `offline_eval.py` | metric image, per venv | The pinned `DesktopEnv.evaluate()` with a stub VM; fresh processes, repeat scoring, `error` verdicts |
| `stats.py` | anywhere | Task-cluster bootstrap, Wilson and Clopper-Pearson intervals, zero-event bounds, MDE, Hajek audit weights, the K3 label-error bound (exact at the Kish effective size), κ |
| `raters.py` | anywhere | D9/D23 model-rater audit: candidate pool, D35 census (every checker candidate event and P2's audit gate, shams with a gold sham for every audited task, P1 flips; a seeded stratified fallback over candidate type x checker family above the 3.0 GPU-h cap's capacity, `audit_capacity` 1,139 items), salted opaque item ids, blind packets, first-token answer rule (after the last `</think>` for the thinking rater), consensus, Kevin's blind adjudication pool (splits, concordant contradictions of every label class since D38, split gold shams), gold defects, K3/K4 on the ungated label classes, S6 per label class |
| `rater_runner.py` | Anthropic API (local) / agent harness (D25, D27, D34) / vLLM lane (H100) | One call per rater per item (a calls file with a second record for an item is refused), transport-only retries (at most 3), malformed bodies `unsure`, request and response hashes, receipts; shard merge for the summary (one relay frame across the calls files, D38); `export-isolated` / `collect-transcripts` / `ingest-isolated` for the Claude rater through the agent harness (the collector maps every transcript of the rating run to its item and writes nothing if it refuses, D38; relay re-rate list, recomputed from the ingest's calls file wherever it is read), one agent per item in its own directory with a transcript audit of every user turn and every transcript of the item (D35: the registered template once, and only the harness relay frame besides it) (`export-harness` / `ingest-harness` is the earlier shared-directory form); the open-weight rater serves Qwen3.6-35B-A3B (D27; thinking on since D34) with vLLM in the cu129 overlay, stops cleanly on the lane's signals and leaves with `os._exit`; `templates/isolated_rater_prompt.txt` is the registered task prompt of each isolated rater agent |
| `audit.py` | anywhere / LO-VM image | Audit sample and items from a scored run, saved-start baseline jobs, blind packets with 100-dpi renders fitted to the registered token budget (sharded), audit summary over per-shard call files and decisions |
| `analysis.py` | anywhere | Registered analysis, a descriptive protocol since D35: P1 (replication, confirm plus reserve control runs), the checker false-negative and false-positive candidates with their audit decisions, counts and task-equal shares; P2-P5 (exploratory: `D34_DEV_EXIT` always keeps them out of the confirmatory headline) with the audit gates, family floor, K2 (recomputed without dropped families), K3 and K4 reported, K5, K6 retired (blocked), K6b and K7 descriptive, K9 |
| `dependency_flips.py` | metric image | S1: venv flip candidates from the repeat-2 scorings, confirmed only at five agreeing fresh-process scorings per venv |
| `packets.py` | anywhere (stdlib) | Rater packet artifacts: listing and structural difference from the operators' snapshot (save drift of at most 0.02 mm counted, not listed), a text-level difference for new-file end states, render commands (100 dpi) |
| `vm_injection.py` | anywhere | Corrected in-VM injection plan for the fidelity gate (executed later on the VM runtime): opens agent-created outputs, agent-equivalent saves, save path per target |
| `report.py` | anywhere | Summary of a control run (K1, P1 with exact intervals; save failures and unemulated tasks listed) |
| `operators/` | LO-VM image (planning, UNO application) and anywhere (snapshots, purity) | The 64-operator catalog (`q2-mut-operators-v1`), spec binding and witness rules, `uno_apply.py`, the stdlib purity oracle |
| `campaign.py` | metric image, LO-VM image, anywhere (per subcommand) | Joins blind specs, operators and the scorer: `targets`, `build`, `merge`, `recheck`, `report`, `export`, `pins`, `guard` |

## Images (H100 host, CPU-only, built through `q2-mutation-cpu.sbatch`)

| Image | ID | Contents |
|---|---|---|
| metric | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` | `/opt/venv-lock` (OSWorld uv.lock, Python 3.12.13, pandas 3.0.1) and `/opt/venv-scout` (scoping venv, pandas 2.3.3) |
| LO-VM | `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361` | The VM's own userland (LibreOffice `1:7.3.7-0ubuntu0.22.04.4`, profile, pyautogui) plus xvfb at the VM's X server version and openbox |
| vmprobe | `sha256:0cde2db147f4eefea82b1807ac2f4c4bfc725157eedf2d3e678fd2d3c969a1f9` | qemu-img and debugfs, to read the VM disk without root |

Every input is listed with revision, size, SHA-256 and licence in
`program/evidence/q2-mutation/harness/inputs-manifest.json`.

## Running a control run (dev split only before the freeze)

```bash
# local: commit, then stage the exact tree on the host
SHA=$(git rev-parse HEAD)
git archive --format=tar HEAD | ssh fal-h100-01 \
  "d=~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA; mkdir -p \$d && tar -x -C \$d && echo $SHA > \$d/.git_sha"
# host: three dependent CPU-only Slurm jobs (raw scoring, save, saved scoring)
bash ~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA/infra/q2-mutation/run/submit_controls.sh \
  $SHA dev dev-controls-vN <metric-image-id> <lo-vm-image-id> 16
# then summarize
python -m harness.q2_mutation.report runs/dev-controls-vN --out summary.json
```

`submit_controls.sh` carries the same guards as `submit_mutants.sh`: on the
host, `check_frozen.py` checks `.git_sha` and, for any split but `dev`, the
frozen ledger row (hash chain and digest), `Q2M_PREREG_FROZEN` and the pinned
image IDs; in jobs 1 and 3, `campaign guard` checks the code, catalog, spec,
split, probe-map and receipt digests (non-dev) and the mounted OSWorld tree,
VM baseline and file cache (every split).

## A mutation run (spec -> operator -> mutant -> save -> verdict)

`infra/q2-mutation/run/submit_mutants.sh` submits three dependent CPU-only
Slurm jobs through `q2-mutation-cpu.sbatch`:

1. metric image: control jobs for the split (`make_jobs.sh`), then
   `campaign targets`: every gold file an operator family can mutate (office
   OOXML, text and config files that no postconfig conversion derives), with
   the task's other gold files as context; the blind specs are validated and
   copied to JSON.
2. LO-VM image: `campaign build` saves the gold (the base) and the initial
   file with `uno_apply.py`, plans every operator of the family from the
   blind spec and the base only, applies each office recipe to the raw gold
   (`--apply-to gold`, the registered mode: mutant and null mutant are each
   one LibreOffice round trip from the gold, and the null mutant is the base;
   `--apply-to base` edits the base and saves it once more for the null),
   checks purity against the null mutant and dedupes; then `reach.sh` runs
   the GUI-faithful save stage on every admitted mutant and one null job per
   target.
3. metric image: `campaign merge` (MutationResult ids kept), `score.sh` under
   both venvs (VerdictRow JSONL), `campaign recheck` (operator purity on the
   saved mutant against the saved null mutant) and `campaign report`.

```bash
bash ~/cotcodec-runs/stage0/q2-evaluator-mutation/src/$SHA/infra/q2-mutation/run/submit_mutants.sh \
  $SHA dev dev-mutants-vN <metric-image-id> <lo-vm-image-id> 16 gold
# locally, after copying the run's prep/, build/ and score/ JSON files:
uv run python -m harness.q2_mutation.campaign export --run <run copy> \
  --out program/evidence/q2-mutation/integration/dev-mutants-vN
```

Outcome per mutant and venv (`campaign.classify`, first match): `not_admitted`,
`save_failed` (the GUI-faithful save of the mutant or its null mutant did not
write every office file; `merge` leaves such jobs out and lists them in
`jobs-saved.excluded.jsonl`), `unemulated` (a setup or postconfig step the
harness cannot replay may write a checker-read file), `not_scored`,
`normalized` (the edit did not survive the save), `infra_failed` (scoring
timed out after its retries, or the scoring process died, met a live getter or
a refused network fetch), `null_not_pass` (the saved null mutant of the
target does not pass, so no label can be read), `error`, `nondeterministic`,
`ambiguous`, or `evaluable` with event `FN` / `FN_alt` / `FP_R` / `FP_F` or
`ok`. Cells a scoping probe touched (`PROBE_OPERATOR_MAP`) and the two
probe-informed operators (`PROBE_INFORMED_OPERATORS`) are kept out of the rate
tables.

Every split but `dev` is refused unless the staged tree carries the frozen
ledger row of `q2-evaluator-mutation-v1` (hash chain verified),
`Q2M_PREREG_FROZEN` is set, and the tree's digests equal the
preregistration's `q2m_pins` block (`campaign pins --root . [--inputs DIR]`
prints them); `check_frozen.py` also checks the image IDs and the application
mode against that block before any job is submitted. `submit_target_counts.sh` only counts targets
per split (no spec, mutant or checker) and runs for every split.

The controls-only path is still available: `controls.py mutation-jobs`
builds scoring jobs from any `MutationResult` JSONL whose files follow
`<files_root>/<mutant_id>/<VM path without the leading slash>`.

Released evidence (`campaign export`) carries redacted recipes: free text of
32 characters or more in a recipe (a `must_equal` value holds a whole gold
paragraph) is replaced by its SHA-256 and length, and purity details are
dropped. Each release row names what the recipe's steps were applied to
(`applied_to`, `applied_input_sha256`: the raw gold under `--apply-to gold`).
Mutant documents and full recipes stay on the host.

## Invariants

- No container gets a GPU, a network, or capabilities; the batch script
  refuses to run if `/dev/nvidia*` is visible.
- Nothing from `evaluator`, gold files or this harness's checker-derived
  outputs reaches the blind spec author or the raters.
- Mutant documents and full recipes stay on the host; only redacted recipes,
  hashes, outcomes and verdicts are committed.
- Operators read only the blind spec, the LibreOffice-saved gold and the
  LibreOffice-saved initial file: `campaign build` gets no task config, no
  checker and no verdict.

## Rating the audit packets

Open-weight rater (one lane job per packet shard; dev smokes and the confirm
audit alike). Render each job's manifest on the host with
`infra/q2-mutation/run/render_rater_manifest.py ... --audit-id <audit>
--gpu-ledger <q2 root>/raters/gpu-ledger.jsonl`: the renderer sums the caps
already in the ledger for that audit, refuses a job that would pass the
audit's cap (3.0 GPU-h confirm since D34, 0.5 GPU-h per dev smoke) and appends its own
row. The lane memory is the rater model's (160 GiB for Qwen3.6-35B-A3B, as the
reviewer lane). Size `--minutes` as 4 minutes of start (container, model check, engine) plus
the shard's items at 10 per minute (thinking on; 14.4 measured) plus the
lane's USR1 lead (up to 240 s); a job stopped early leaves the rest `unrated`, which a
rerun on a shard of those items rates. Check image input first with the CPU
args doctor: `rater_runner args-doctor --model-dir <dir with the model's
config, tokenizer and processor files>`.

Each audit's item ids take a secret salt (D34): before `submit_audit.sh`,
write 32 random bytes as 64 hex characters to
`<run root>/scratch/audit-salts/<audit>/salt.hex` (file 600, directory 700,
nothing else in it); commit only its SHA-256 (the sample summary's
`salt_sha256`) and reveal the salt after the isolated ingest.

Claude rater through the agent harness (D25, isolation per D27, D34):

```bash
# 1. One fresh directory per item; the manifest goes outside the root.
uv run python -m harness.q2_mutation.rater_runner export-isolated \
  --packets packets-000.jsonl --iso-root <root> --manifest-out <outside>/iso-manifest.json
# 2. One workflow session whose agents are the raters only (D38): one subagent per
#    item. Its task prompt is templates/isolated_rater_prompt.txt with
#    {ITEM_DIR} = <root>/<item> (the manifest's iso_root, no trailing slash) and
#    {ITEM_ID} = <item>, verbatim; keep its answer as <answers>/<item>.json
#    ({item_id, answer, reason}). The session request is recorded verbatim in the
#    receipt if a resume relays it: name no item and nothing private in it.
# 3. Collect every transcript of the run (D38): mapped to its item by its rendered
#    task turn, copied byte-exact as <item>.jsonl (the agent with a journal result)
#    and <item>.<agent id>.jsonl (any other attempt); refuses an unmappable agent.
uv run python -m harness.q2_mutation.rater_runner collect-transcripts \
  --run-dir <workflow run dir with agent-*.jsonl and journal.jsonl> \
  --manifest <outside>/iso-manifest.json --out <transcripts> \
  --collection-out <outside>/collection.json
# 4. Ingest: re-hash every item directory, model id and audit from every transcript;
#    refuses transcripts the collection does not list, or a listed one missing.
uv run python -m harness.q2_mutation.rater_runner ingest-isolated \
  --packets packets-000.jsonl --manifest <outside>/iso-manifest.json --iso-root <root> \
  --answers <answers> --transcripts <transcripts> --collection <outside>/collection.json \
  --out <calls dir>
# 5. Only if a resume brought a different relay frame (D38): <calls dir>/rerate.json
#    lists the items voided for that alone; re-rate them once in a fresh, unresumed
#    session (export-isolated --rerate-list <calls dir>/rerate.json into a new root,
#    then steps 2-4), and summarize with --rerate-list and --rerate-calls: both
#    results are written (rerate/ beside the registered summary). Both commands
#    recompute the list from <calls dir>/calls.jsonl and refuse an edited one.
#    Every relay-voided item is in the registered pool, so Kevin adjudicates them too.
```

The transcript audit voids an item's answer (`isolation_void`, `unsure`)
unless, in every transcript of the item, exactly one user turn is the template
rendered for that item (bare or in the workflow harness's wrapper) and any
other user turn is the harness relay frame (`RELAY_PREAMBLE`, once, before the
task turn, naming no item id, byte-identical across the run; D35). Any entry
whose message has the role user is a user turn, whatever its entry type, and
an entry type outside `TRANSCRIPT_ENTRY_TYPES` (user, assistant, attachment)
or an attachment type outside `HARNESS_ATTACHMENT_TYPES` (the fifteen of the
D34 development rating) voids the item: a message sent to a running agent
arrives as a `queued_command` attachment (sixth review). It also
voids on two transcripts that answer, a StructuredOutput naming another item, a
packet.txt never read, a shell call, a tool other than Read (and the
path-free StructuredOutput, ToolSearch, TodoWrite), a path outside the item
directory, a changed item directory, a missing transcript or model id, or an
answer the transcript did not return (a final-text fallback needs exactly one
answer word, and counts only for an agent with a journal result: an interrupted
attempt answers only through StructuredOutput, D38); a transcript naming another
model refuses the ingest. The receipt records each relay frame verbatim (harness
text; a frame naming an item id by digest only), and `audit summarize` refuses
calls files that carry different relay frames (D38). Transcripts and answers quote document text: keep them outside the
repository; the call records keep their SHA-256.

