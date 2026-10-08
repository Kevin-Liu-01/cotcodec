# q2-evaluator-mutation-v1: OSWorld-Verified checker mutation audit

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger
row for the freeze time and `git_head_at_freeze`. A pre-specified descriptive
protocol under decisions D35 and D38 (ninth draft, with its narrow re-check's
minor items fixed).** Every pin below is filled from the integration
branch `stage0/q2-evaluator-mutation`, and no value is left open. Six
adversarial reviews have read the earlier drafts (scores 55, 62, 56, 57, 64 and
80), and a narrow re-check read this one (90, no blocking defect; the review
log is at the end of section 17). The fourth review found that D27's
consequence had fired (development κ 0.270 against the registered 0.6), and
decision D34 allowed one rater retry, then an honest exit: the open-weight
rater thinks before it answers, and the development audit was rebuilt
(`dev-audit-v4`, 142 items) and rated by both raters under the isolated
protocol. Development κ was 0.066 under the registered ingest and 0.575 with
the workflow harness's relay turn excepted (a sensitivity: after a session
restart the harness put a byte-identical relay of the session request before
every resumed rater's task, and the registered first-prompt rule voided those
110 otherwise clean transcripts; section 15). Both are below 0.6, so D34 (i)
fired: no other rater is tried, P2-P5 leave the confirmatory headline before
the confirm campaign runs, and the registered 0.066 stays as recorded. The
fifth review (64/100) judged the study still worth running as a pre-specified
descriptive protocol, because the catalog, the blind labels, the sampler and
the analysis can be locked before any confirm mutant exists. Decision D35
(program/decisions.md) makes it one; this draft implements it:

1. The exit, in code (sections 4 and 10): `analysis.D34_DEV_EXIT` always
   takes P2-P5 out of the confirmatory headline, with the reason "D34 (i):
   development kappa below 0.6", whatever the confirm audit shows; they are
   still computed and reported as exploratory. K6's adequacy claim is retired
   (reported as blocked), K6b and K7 are descriptive, and K4 is reported but
   stops nothing. The registration makes no confirmatory claim: P1 was
   already a replication only.
2. The descriptive outputs, pre-specified (sections 4 and 12,
   `analysis.checker_candidates`): P1 (replication only, unchanged); the
   checker false-negative candidates (evaluable `should_pass_equiv` mutants
   outside probe-touched cells and `should_pass_alt_solution` mutants that the
   checker fails) and false-positive candidates (evaluable
   `should_fail_violation` and `should_fail_extra_change` mutants it passes),
   each listed with its audit decision; per-family and per-operator counts and
   task-equal shares with task-cluster bootstrap intervals, all labelled
   descriptive; and S1-S7 as registered.
3. The audit scope (section 9, `raters.draw_audit_sample`): a census of every
   candidate event, every P1 flip, the audit gates and the shams, within the
   registered 3.0 GPU-h rater cap. If the census would exceed that cap's
   capacity at the registered planning rate (1,139 items), the mutants are a
   registered seeded stratified sample over candidate type × checker family,
   disclosed in the sample summary. Kevin adjudicates the pool.
4. The transcript audit (section 9, `rater_runner.audit_transcript` and
   `ingest-isolated`): every user turn is checked. Exactly one equals the
   rendered template (bare or inside the fixed wrapper); the only other user
   turn allowed is the harness relay frame, which must come before the task
   turn, be byte-identical across the run and name no item id, and whose
   SHA-256 is recorded in every call record and in the receipt; any other user
   turn voids the item. Every transcript of an item (interrupted attempts
   included) is ingested and audited, and at most one may answer. Since the
   eighth draft (the sixth review's blocking defect) every entry whose message
   has the role user is a user turn whatever its entry type, and a
   transcript entry or harness attachment of a type outside the registered
   lists (the entry types and the fifteen attachment types of the
   development rating) voids the item; a message sent to a running agent
   arrives as a `queued_command` attachment, which the audit did not read
   before.
5. Packets (section 9): the difference section now comes before the file
   listings, a label-blind format change made after the development results
   and disclosed with them.

and the fifth review's minor items: the adjudication workload re-estimated for
the census (section 9); stale text in sections 6, 10, 13, 15 and 17; the lane
memory taken per rater model (160 GiB for Qwen3.6-35B-A3B, as the gauntlet
reviewer lane gives it, instead of a fixed 128 GiB); and the review log
(section 17).

The sixth review (80/100) read the seventh draft and found one blocking
defect: the transcript audit read only entries of type user, so a message
sent to a rater while it ran, which the agent harness delivers as a
`queued_command` attachment, passed the audit. The eighth draft registers
the transcript's entry types and harness attachment types and voids any
other (item 4 above, section 9: `rater_runner.TRANSCRIPT_ENTRY_TYPES` and
`HARNESS_ATTACHMENT_TYPES`). Rerun over the 158 development transcript
copies, the audit finds no void and no attachment type outside the list
(3,304 attachments of the fifteen types).

Decision D38 (program/decisions.md) accepted the eighth draft's choices as
implemented (the census audit with its seeded stratified fallback, gold shams
for every audited task, the relay frame registered under D35's constraints,
the difference-first packet order and the registered entry and attachment
types) and, because a freeze pins this code, had the sixth review's minor
items fixed before the freeze. This ninth draft fixes them:

6. The fallback sample takes the largest mutant budget whose sample, shams
   and P1 flips fit the capacity, found by search (section 9,
   `raters.draw_audit_sample`); the eighth draft's single subtraction stopped
   at 251 items of a 300-item capacity on the review's synthetic pool.
7. A registered collector, `rater_runner collect-transcripts`, maps every
   agent transcript of the rating workflow run to its item by its rendered
   task turn, refuses any it cannot map, copies each byte-exact into the
   layout the ingest reads and writes a manifest of every agent (item,
   SHA-256, whether it answered, from the run's journal); `ingest-isolated`
   takes that manifest and refuses a listed transcript that is missing or
   changed, or one it does not list (section 9). Copying transcripts by hand
   was an unregistered step. Over copies of the 158 development transcripts
   the collector maps every one and reproduces the hand-copied layout file
   for file, and the audit then finds no void and 142 answering transcripts
   (`integration/d38-fixes/`).
8. `audit summarize` refuses calls files that carry different relay frames
   between them (two ingests with one frame each passed before), and the
   ingest receipt records each relay frame verbatim: it is harness text, the
   relayed session request, and a frame that names an item id is kept by
   digest only (section 9).
9. A mutant of any candidate kind on which both raters agree against its
   label joins Kevin's adjudication pool, not only the K3 groups' items
   (sections 4 and 9); the development census's pool is unchanged by it.
10. An interrupted attempt (no result in the run's journal) answers only
   through a structured answer, never through an answer word in its final
   text (section 9).
11. The confirm rating runs as one workflow session; if a resume brings a
   different relay frame, the items it voids are re-rated once in a fresh,
   unresumed run, chosen by that void reason alone (answer-blind), and both
   results are reported (section 9: `rerate.json`, `export-isolated
   --rerate-list`, `audit summarize --rerate-list --rerate-calls`; both
   commands recompute the list from the ingest's calls file and refuse one
   that differs).
12. Stale text: section 10's K2 consequence (K6 no longer reads P5) and the
   development evidence README's open relay decision (D35 and D38 decided
   it).

The narrow re-check of this draft (90/100, ready to freeze, no blocking
defect) left minor items, fixed here without changing a registered choice:
the re-rate list is recomputed from its calls file wherever it is read
(item 11); tests now pin the "only void reason" rule of that list and the
collector's refusal of a journal that starts an agent twice; the collector
copies into a staging directory and renames it into place only when every
copy checks, so a refusal leaves nothing behind (section 9); and section 9's
workload estimate and Kevin's item in section 17 now say that a resume with
a different relay frame puts every relay-voided item in his pool.

Kevin's remaining items are listed in section 17: adjudicating the pool,
the human spot check, the outward actions and the sign-offs carried over
from earlier drafts.

The registered analysis is code (`harness/q2_mutation/analysis.py`), so no
choice is left to make after a result is read. The narrow re-check of this
draft found no blocking defect. The owner-level design choices were decided
on Kevin's behalf in decisions D23-D38, which he reviews (section 17); the
items that stay his (adjudicating the pool, the human spot check, the outward
actions, the release of the specs) come after the freeze. Main was merged once
more, so the ledger does not fork, and the file is frozen with

```bash
uv run python scripts/preregister.py freeze q2-evaluator-mutation-v1 \
  program/preregistrations/q2-evaluator-mutation-v1.md
uv run python scripts/preregister.py verify q2-evaluator-mutation-v1
```

and commit the ledger. The ledger's `git_head_at_freeze` is the harness
commit. No confirm-split mutant is planned, built or scored before the freeze.
Development-split runs (harness validation, the gold fixed point on dev tasks,
the end-to-end campaign on dev tasks) are allowed and are reported as
exploratory.

## 1. Question

How often do OSWorld-Verified's file-state checkers (a) reject end states that
satisfy the task instruction (false negatives) and (b) accept end states that
violate it (false positives), when every office end state reaches the checker
the way it does in the real pipeline, re-saved by the VM's own LibreOffice?

Scope: the 205 offline-checkable, web-free tasks of OSWorld-Verified
(`test_nogdrive.json`, 361 tasks). Classes 1A/1B/1V/1C; live-state (class 2),
web and infeasible tasks are out of scope.

Since decision D35 the study answers this descriptively (sections 4 and 12):
it lists and counts the checkers' candidate errors on blind-labelled mutants,
each with the model raters' audit decision, and reports no confirmatory rate.

## 2. Identity and pins

| Object | Pin |
|---|---|
| OSWorld | `b138d348256078fa634fc3b73567a7337c793e6b`; evaluators and tasks last changed in `0514b9a262c5e49007a5724e3e6c84171566ae66` (Apache-2.0) |
| File cache | HF `xlangai/ubuntu_osworld_file_cache` at `1e112283c4ecb08d6fed8069bca7de74fa2f12aa`; 447 files fetched, every LFS file verified against its oid (apache-2.0 card; third-party document content) |
| VM image | HF `xlangai/ubuntu_osworld` at `a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133`; `Ubuntu.qcow2.zip` 12,273,896,463 B, SHA-256 `b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712`; extracted `Ubuntu.qcow2` SHA-256 `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313` |
| LibreOffice | the VM's own Ubuntu build, `libreoffice-core 1:7.3.7-0ubuntu0.22.04.4`, "LibreOffice 7.3.7.2 30(Build:2)" (not TDF's build). The LO-VM image runs the VM's extracted `/usr`, `/etc`, dpkg database, LibreOffice profile and the user's site-packages with PyAutoGUI 0.9.54 (205,028 files, tree SHA-256 `fceee6501ff0d1f1a33500b36663624c220f1598140fa271040b5e97a9de30bf`) plus xvfb `2:21.1.4-2ubuntu1.7~22.04.8` (the VM's X server version, deb SHA-256 `f8c64bc652e3dc1a1041e85025267f574c27f86b00d7965545a8b3ec41a60cd4`) and openbox 3.6.1-10; no VM package changes; one passwd entry for the runtime uid |
| LO-VM image | `sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361`, used for the base, initial and null-mutant saves, operator application (`uno_apply.py`) and the GUI-faithful save stage. The operators' own validation (Slurm 431-433) used the earlier build `sha256:894b2623dceb43e8468a2adbd6e03a532ea9683d4b7754cd79fa0d58a331f909` of the same LibreOffice package from the first VM userland extraction; the integration runs used `f5b4c40e` |
| LibreOffice profile | the VM's `registrymodifications.xcu` (SHA-256 `6b5ec88d1570a8ad85932eb53a1a6f8370053d3ac60b30fe759c14135e902ef2`): `WarnAlienFormat=false`, `ShowTipOfTheDay=false`, Writer default filter "MS Word 2007 XML" |
| Metric image | `sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230` (ubuntu:22.04 `sha256:5ec03bb3…6401`, Python 3.12.13, uv 0.11.30) |
| Lock-exact venv (primary) | OSWorld `uv.lock` exported for Python 3.12 with hashes, agp-client left out; requirements SHA-256 `3f463d6f3331a80c3054dfd8aced1dabb56adf8ee8b6fa7441e25435f626c2a3`; installed-RECORD fingerprint `f2c9e208d2bdb888668e64143f0603ce92f56cee2fd1002f0211d2c2287db810`; pandas 3.0.1, numpy 1.26.4, python-pptx 1.0.2, python-docx 1.2.0, openpyxl 3.1.5, torch 2.5.1 |
| Scoping venv (sensitivity) | the scoping agent's 129 package versions (pandas 2.3.3, torch 2.5.1+cpu); requirements SHA-256 `5ae07a7a527c22ff580a171692ccbc608f563e6c7264b0819a92ff1c41bd6fb7`; fingerprint `e591c8875c353ecbf6ec38b6c9c467e01b4164cc129744bd51e27c993310417a`. It is not the leaderboard-era set the reviewed plan asked for (section 14): it shares numpy, openpyxl, python-docx, python-pptx, lxml, PyMuPDF, RapidFuzz, scikit-image, formulas and borb with the lock-exact venv and differs in 63 of the 125 shared packages, among them pandas (3.0.1 vs 2.3.3), opencv-python-headless (4.11.0.86 vs 4.8.1.78), chardet (6.0.0.post1 vs 7.6.0) and beautifulsoup4 (4.14.3 vs 4.15.0) |
| Task export | `program/evidence/q2-mutation/sanitized-tasks.manifest.json` (205 tasks), SHA-256 in the pins block |
| Splits | `program/evidence/q2-mutation/splits.json`, seed 42, stratified by domain × task class: dev 32, confirm 120, reserve 53 |
| Requirement specs | `program/evidence/q2-mutation/specs/` from `stage0/q2-mut-specs` at `287d523374354e40af4c1f54bd06e46c3de6a955`: 205 YAML specs, 598 requirements, author `blind-model-author-v1`. Set SHA-256 = SHA-256 of the sorted lines `{file sha256}  {file name}` (`campaign.spec_set_sha256`). Blindness check: `program/evidence/q2-mutation/integration/blind-spec-provenance.json` |
| Operator catalog | `q2-mut-operators-v1`, `catalog_sha256` (hash over the operator descriptions and the sources of `harness/q2_mutation/operators/`), 64 operators listed in Appendix A; validated at `7c429bcb793369649bc7970ccad0fba290ad2772` and merged from `stage0/q2-mut-operators` at `0d7f0857cc0a6d0007466a05ee08a44a467cf957`; on the integration branch the snapshot gained version-2 fields, and after the third review (D27) `pptx.eq.zorder_nonoverlap` and `pptx.viol.delete_bound_shape` gained the site rules of Appendix A, revalidated on the synthetic documents at `4eba530` (Slurm 684: 131 planned, 131 applied, 130 admitted, as job 431) and on the dev split (`dev-mutants-v8`; `dev-mutants-v7` lost two targets to a UNO fault and was not scored, section 15); after the fourth review (D34) `pptx.viol.delete_bound_shape` also skips shapes at least 50% off the slide, revalidated at `34046e0` (Slurm 717) and on the dev split (`dev-mutants-v9`, section 15) |
| Harness and campaign code | code-tree SHA-256 over every file of `harness/q2_mutation/` (README and SKILL files excepted), `infra/q2-mutation/`, `infra/slurm/host-single-node/q2-mutation-cpu.sbatch`, `scripts/q2_mutation_export_tasks.py` and `scripts/q2_mutation_operators.py` (`campaign.code_tree_sha256`); schema `q2-mutation-schema-v1`; operator snapshot version 2 (pptx slide backgrounds, shape outlines and text-body properties added after the review) |
| Mounted inputs | `osworld_tree_sha256` over `desktop_env/` and `evaluation_examples/` of the host's clean checkout at `b138d348` (git status clean, 537 files); `vm_baseline_tree_sha256` over the 75 VM config-baseline files; every file-cache file re-hashed against `program/evidence/q2-mutation/harness/file-cache-receipts.tsv` (447 files, its SHA-256 pinned); the probe map input `probe_touched.json` (SHA-256 pinned) |
| Raters (decisions D23, D25, D27, D34) | Anthropic rater, model `claude-opus-5-5`, by one of two registered paths: the Messages API once a valid key exists (the id the API names recorded by `rater_runner` before the first call, the run stops if it differs, and from every response), and until then the Claude Code agent harness with one isolated agent per item (D25, D27: `rater_runner export-isolated` / `ingest-isolated`; the model id is the one the harness transcript records for the agent's turns, a transcript naming another model refuses the ingest, and the transcript audit of section 9 voids a breached item). Open-weight rater (the independent one, D27): `Qwen/Qwen3.6-35B-A3B` at Hugging Face revision `995ad96eacd98c81ed38be0c5b274b04031597b0`, model receipt SHA-256 `18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9` (artifact root `8ac6d764b84034f4ed0df3f2388c9180afceab806f7e75f5d1e43a73bdd2736b`, 71.9 GB, Apache-2.0), verified by the lane in every job; vLLM 0.31.0 resolves its architecture (`Qwen3_5MoeForConditionalGeneration`) as multimodal and its processor turns a 100-dpi page into 918 image tokens, under the registered estimate of 947 (CPU image-input doctor, Slurm 685). Since D34 it rates with thinking on (section 9). The development smokes of section 15 used Qwen3.5-9B (`c2022362…`, receipt `0a9e052d…`), and the D27 rerate this model with thinking off |
| Rater runner and serving | `harness/q2_mutation/rater_runner.py` (inside the code-tree pin), prompt `RATER_PROMPT_V1`, isolated-harness instructions `ISOLATED_INSTRUCTIONS` (the prompt plus a fixed note: read only this item's file and images, with the Read tool, run nothing), and the isolated agent's task prompt `harness/q2_mutation/templates/isolated_rater_prompt.txt` (D34; SHA-256 `0e9d4eb6597c347d40db7f8ae150e3345fc8a88820d6e8501d02543c9ccbed44`, in the pins block and checked by `rater_runner`; placeholders `{ITEM_DIR}` and `{ITEM_ID}`); the workflow harness's relay frame, the one other user turn the transcript audit allows (`rater_runner.RELAY_PREAMBLE`, D35, section 9); vLLM 0.31.0 (commit `db9527a46873454610df6dbedf79a36d6bf1a7f6`) in the cu129 overlay of `vllm/vllm-openai@sha256:b18abb2df97b8f798e81862bd93f872ea18613372e2c3adc0cc2ac21e66ac12f` (image ID `sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b`), built by `scripts/build_vllm_overlay_on_h100.sh` from a source capsule of the frozen commit; the serving probes validated this base, variant and checkpoint (`program/evidence/2026-10-07/serving-throughput-probe-v2/`) |

Machine-readable pins. Before any job is submitted, `check_frozen.py` on the
host refuses a staged tree whose `.git_sha` is not the submitted commit, and,
for every split but `dev`, a tree without this file's frozen ledger row (hash
chain checked), without `Q2M_PREREG_FROZEN`, or with image IDs or an
application mode other than below. Inside the containers, `campaign guard`
(jobs 1 and 3 of both the control and the mutation runs) and `campaign
targets` refuse every split but `dev` unless the same holds and `campaign
pins` on the staged tree equals the digests below; for every split, `guard`
also refuses mounted inputs whose OSWorld tree, VM baseline or file cache
differ from the pins:

```json
{
 "q2m_pins": 1,
 "experiment_id": "q2-evaluator-mutation-v1",
 "code_tree_sha256": "58bee0190c0c7eb5d44f36e27c0f1e0daab82c1c48716009a9066777c69a0721",
 "operator_catalog_sha256": "3a5ff94953f7b672059b0f6b063064b97a438de166fd664903e239a12f65b46f",
 "operator_catalog_version": "q2-mut-operators-v1",
 "operators": 64,
 "spec_set_sha256": "05d4fb2074a7fa53046dff9f5d075b2b45ac014889eaae23d625c1894056de62",
 "specs": 205,
 "sanitized_manifest_sha256": "40ef4a459086b86f4971d3f938402df6c2749bd16a2acc2822f25261ebc70380",
 "splits_sha256": "2099792e6fb86c69e4f79b1ce47d2839cc25623f5c4633698e95822553c007d9",
 "schema_sha256": "65d91703754b4026b15f6c53a4a6069da723b58d749730770da2910c1edf427d",
 "probe_touched_sha256": "4115740770f6fa88c03742f455f7c9b373d73fe0424ae16540461d12860fa929",
 "file_cache_receipts_sha256": "9a3e06a48afe95c2286d0fa26d56edf947e1a5e0f121d414d565b58d30abe5fb",
 "osworld_tree_sha256": "4153c68678fedd44a285800b45f4b7e538336a044f614f748f432a7ce5246076",
 "vm_baseline_tree_sha256": "f32538182c72aa44ca348a42fcc1c04a1faf35b2c18a8f76d8af1d3bfafcb1df",
 "metric_image_id": "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230",
 "lo_vm_image_id": "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361",
 "apply_to": "gold",
 "mutation_split": "confirm",
 "seeds": [
  42,
  43,
  44
 ],
 "specs_branch_commit": "287d523374354e40af4c1f54bd06e46c3de6a955",
 "raters": {
  "anthropic_model": "claude-opus-5-5",
  "open_weight_model_id": "qwen3.6-35b-a3b",
  "open_weight_repo": "Qwen/Qwen3.6-35B-A3B",
  "open_weight_revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
  "open_weight_receipt_sha256": "18c2a12881bf613c7110439b8e765ff89a4c060a1fb60aee62bb7250890ce1f9",
  "vllm_base_image_id": "sha256:423783aac4fefebfe6b67d6fc2810b88a1d4dc08ed8bba587c80b0d8973e0b8b",
  "open_weight_enable_thinking": true,
  "open_weight_max_tokens": 8192,
  "open_weight_gpu_hours_cap": 3.0,
  "isolated_prompt_template_sha256": "0e9d4eb6597c347d40db7f8ae150e3345fc8a88820d6e8501d02543c9ccbed44"
 }
}
```

The pins block names no harness or operators branch commit: no code checked
them (third re-audit). The code-tree digest identifies the harness and the
catalog digest the operators; `specs_branch_commit` is checked against
`integration/blind-spec-provenance.json` by `tests/test_q2_mutation_prereg.py`,
which also refuses a pins key that nothing checks.

Licences of runtime packages that are run but never vendored: PyMuPDF 1.27.1
(AGPL-3.0 or commercial), borb 2.1.25 (AGPL-3.0-or-later or commercial),
mutagen 1.47.0 (GPL-2.0+), formulas 1.3.3 (EUPL-1.1+). Mutant documents and
full recipes are never released; redacted recipes, verdicts and outcome rows
are (section 16).

## 3. Design

**Candidates.** Each candidate is a set of end-state files for one task. Kinds:
the task's gold (where every metric pairs a `vm_file` result with a
`cloud_file` gold that is not one of the task's own inputs), do-nothing (the
initial state), operator mutants (`MutationResult`, schema v1) and one null
mutant per mutation target.

**Mutation targets.** A target is one gold file of a confirm task with a
complete gold whose type an operator family handles (`.xlsx`, `.docx`,
`.pptx`; text and config files such as `.txt`, `.csv`, `.json`, `.ini`) and
which no postconfig conversion derives (`campaign.select_targets`). The
task's other gold files are the target's context and are placed unchanged
with every mutant. Tasks without a complete gold, LibreOffice-native files
(`.odt`, `.ods`), media, images and archives have no target and are listed.

**Mutant pipeline** (`infra/q2-mutation/run/submit_mutants.sh`, three
CPU-only Slurm jobs; `harness/q2_mutation/campaign.py`):

1. `targets` (metric image): control jobs, targets, blind specs to JSON.
2. `build` (LO-VM image): the base (LibreOffice-save of the gold through
   `uno_apply.py`, `.uno:Save` on the document frame under Xvfb with the VM
   profile) and the LibreOffice-saved initial file; planning of every operator
   of the target's family from the blind spec, the base and the task delta
   (base vs saved initial) only; each office recipe applied to the raw gold
   and saved once (`--apply-to gold`), so a mutant and its null mutant (the
   base) are each one LibreOffice round trip from the gold; text and config
   recipes splice characters of the gold; purity checks against the null
   mutant; deduplication by snapshot digest within a (task, operator) cell.
3. The GUI-faithful save stage (`reach.sh`) on every admitted mutant and null
   mutant, then `merge`, scoring under both venvs (`score.sh`, two fresh
   processes each), `recheck` (purity re-run on the saved mutant against the
   saved null mutant) and `report`.

The operators never read a task config, a checker or a verdict.

**Labels.** Fixed at planning time from the blind requirement spec, never
from a checker, by the witness rules W-E, W-A, W-R and W-F (Appendix A):
`should_pass_equiv`, `should_pass_alt_solution`, `should_fail_violation`
(witness names at least one `req_id` with a high or medium binding that pins
the edited aspect), `should_fail_extra_change`, `ambiguous`. Spec entries
marked `[AMBIGUOUS]` are questions, not freedoms.

**Strata.** All 64 operators are in the `document_model` stratum (edits made
through LibreOffice's document model, or character splices of text files);
it is the headline. A `script_writer` stratum (byte-level edits LibreOffice
normalizes on load) would be reported separately and never pooled; the
frozen catalog has no such operator.

**Reachability stage (GUI-faithful save).** Every office candidate is placed
at its VM path in a fresh copy of the VM profile, opened by non-headless
LibreOffice under Xvfb before any postconfig step, and the task's postconfig
is replayed step by step: `wmctrl -Fa` activation, keystrokes through the VM's
pyautogui, sleeps, and `libreoffice --convert-to` with its exact filter
string. Tasks without a postconfig save get one agent-equivalent save
(open, activate, Ctrl+S) per OOXML/ODF candidate. File-only postconfig steps
(downloads, `diff`/`ls` captured to the cache directory) run after the saves.
Every save records whether the file changed, its write time and any dialog.
A candidate counts as saved only if every office file it places has a save
event that wrote it, no save timed out, no open or activation failed and every
postconfig conversion of a placed file produced its output
(`reachability.save_failures`); otherwise the candidate is excluded at
`merge` as `save_failed` (section 8) and is never scored on its pre-save
bytes.

**Scoring.** The unmodified pinned `DesktopEnv.evaluate()` with a stubbed VM:
one non-FAIL action, the offline file-cache shim for `get_cloud_file` (other
URLs refused), live getters refused. Each candidate is scored in fresh
processes twice (`score.sh`, `--repeat 2`); a candidate whose two scorings
disagree is `nondeterministic` (S5) and leaves P2-P5. A candidate whose
verdicts differ between the venvs while each venv's two scorings agree is
rescored five times in fresh processes in each venv in the same Slurm job
(`harness/q2_mutation/dependency_flips.py`, wired into job 3 of a mutation
run and jobs 1 and 3 of a control run); it counts for S1 only if all five
agree within each venv. Where the five scorings of a venv disagree, or agree
on a verdict other than its first two scorings, the candidate was scored
nondeterministically in that venv: it is `nondeterministic` (S5) under that
venv and leaves P2-P5, and when it is a null mutant so do its target's
mutants (`campaign.build_report` `s1_notes`).

**Verdicts.** `pass` iff score == 1.0; `fail` otherwise; `error` iff
`evaluate()` raised (OSWorld's `run.py` logs and skips such a task, so an
error is neither pass nor fail). A scoring that failed for a harness cause
keeps verdict `error` in its row but is an infrastructure exclusion
(`infra_failed`, sections 7 and 8): a timeout after its retries, a scoring
process that died without a result, a live getter, a refused network fetch
(`offline_eval.infra_reason`). Credit (raw score) is kept for
leaderboard-impact statements.

**Dependency sets.** Primary: lock-exact venv. Sensitivity: scoping venv,
which measures sensitivity to the package differences listed in section 2
only, not to the dependency versions in use when the leaderboard results were
produced (section 14).

## 4. Metrics and descriptive outputs (lock-exact venv, document_model stratum, confirm split)

Decision D35: nothing in this section is confirmatory. P1 is a pre-specified
replication (as before); the checker candidates are the protocol's
descriptive output; and P2-P5 are exploratory. D34 (i) fired on the
development audit (section 15), so `analysis.headline` always lists P2-P5 as
out of the confirmatory headline, with the reason "D34 (i): development kappa
below 0.6" (`analysis.D34_DEV_EXIT`, `exclusions.metrics_leaving_headline`),
whatever the confirm audit shows, and reports them with the same tables; its
`exclusions.confirmatory_metrics` is empty. The candidates and P2-P5 are
computed on evaluable mutants (section 7): admitted, the targeted edit
survives the save stage, the target's saved null mutant passes, the verdict
is not `error`, the candidate's scorings agree, and the (task, operator) cell
is not probe-touched (a scoping-probe cell or a probe-informed operator,
section 12). The registered computation is `harness/q2_mutation/analysis.py`
(`headline`).

- **P1 Gold fixed-point false negative (pre-specified replication only).**
  Unit: task. Population: non-dev in-scope tasks with a complete gold whose
  gold places at least one office file the save stage rewrites
  (`reachability.LO_SAVE_EXTENSIONS`: `.docx`, `.xlsx`, `.pptx`, `.odt`,
  `.ods`, `.odp`; `report.save_exposed`), minus tasks excluded as
  `unemulated` (section 8). Counted before the freeze from task configs
  (`integration/prefreeze-counts-v2/counts.json`): 92 tasks (67 confirm, 25
  reserve). Event: the raw gold passes and LibreOffice-save(gold) through the
  reachability stage does not. A gold counts only if its save wrote every
  office file and neither scoring failed for an infrastructure cause; the
  others are listed. Every flip goes to the audit (stratum `p1_flip`); a
  flip is a confirmed false negative when the audit decision is accept.
  Reported: raw flip share and audit-confirmed share with exact
  Clopper-Pearson 95% intervals (zero flips in 92 gives 0-3.9%). The
  registered computation sums the confirm and the reserve control runs
  (`analysis.p1_over_controls`, `--controls-summary` and
  `--reserve-controls-summary`): counted golds and flips of both runs, which
  must hold disjoint tasks of their own splits (`splits.json`); K1 reads the
  confirm run only, and K6 counts the confirmed flips of both. The headless
  scoping round trip already saved all 92 of these golds (a different save
  path and build) and flipped 7 of 63 gold-passing confirm golds and 1 of 26
  reserve golds, so P1 has no confirmatory component: it replicates that
  measurement under the GUI-faithful save. The 15 golds with no office file
  (8 confirm: jpg, gif, two png, two zip, pdf, py; 7 reserve: two txt, csv,
  pdf, mp3, two png) are not exposed to the save stage, so their saved gold
  is byte-identical to the raw one; they are listed as not exposed and never
  counted. Two confirm golds (2a729ded, e8172110) are excluded as
  `unemulated`.
- **Checker candidates (descriptive, D35; `analysis.checker_candidates`).**
  Population: as P2-P5. A false-negative candidate is an evaluable
  `should_pass_equiv` or `should_pass_alt_solution` mutant that the checker
  does not pass; a false-positive candidate is an evaluable
  `should_fail_violation` or `should_fail_extra_change` mutant that it passes
  (the two should-fail classes are reported the same way). Every candidate is
  audited (the census of section 9) and listed with its mutant id, task,
  checker family, operator, label, verdict and audit decision (accept,
  reject, unresolved; `not_sampled` only under the fallback sample of
  section 9), with what the decision says: confirmed (a false-negative
  candidate decided accept, a false-positive candidate decided reject), label
  contradicted (the opposite decision), unresolved, or not audited; and with
  whether its task is a gold-defect task (section 9). A label-contradicted
  reading never rests on the raters' consensus alone: an audited mutant of
  any stratum (the candidate kinds `fn_equiv`, `fn_alt`, `fp_violation` and
  `fp_extra`, and P2's gate `alt_gate`) that both raters decide against its
  label goes to Kevin's blind adjudication pool, and his answer decides it
  (D38; D34 sent only the equivalence and violation items; until he answers,
  the consensus stands). Reported for each kind
  (false negative, false positive): counts by label, audit reading, checker
  family and operator; the candidate share (the share of the kind's evaluable
  mutants that are candidates, a task-equal mean with the task-cluster
  percentile bootstrap, 10,000 resamples, seed 42) pooled, per label, per
  checker family and per operator; and, when every candidate of the kind has
  an audit decision, the audit-confirmed share in the same tables (an
  unresolved candidate is not confirmed). All are labelled descriptive; no
  share is compared with a threshold. Candidate events in probe-touched cells
  are counted per kind and checker family, unaudited (section 12). A family
  K2 drops (section 10) has its candidates reported apart.
- **P2 FN per checker family (exploratory, D34 (i)).** Population: evaluable `should_pass_equiv`
  mutants plus the `should_pass_alt_solution` mutants whose audit decision is
  accept; an alternative-solution mutant the audit rejects, leaves unresolved
  or never sampled stays out of P2 and is reported under S6. Event: the
  verdict is not pass.
- **P3 FP_R, pooled over checker families (exploratory, D34 (i)).**
  Population: evaluable `should_fail_violation` mutants. Event: the verdict is
  pass. Family rates are descriptive; the family floor (section 6) marks where
  the descriptive K7 flag is computed.
- **P4 FP_F, pooled over checker families (exploratory, D34 (i)).** Population: evaluable
  `should_fail_extra_change` mutants, except a mutant the checker passes
  whose audit decision is not reject (accepted, unresolved or not sampled):
  such a mutant leaves P4's numerator and denominator, because its label is
  not confirmed. Event: the checker passes the mutant and the audit rejects
  it. Extra-change mutants the checker fails stay in the denominator. The
  estimate with unresolved passed mutants counted as events is a
  sensitivity analysis. Always reported separately from P3; family rates as
  for P3.
- **P5 Task-level escape rate (exploratory, D34 (i)).** Share of evaluable confirm tasks (at least
  one evaluable `should_pass_equiv` or `should_fail_violation` mutant) with at
  least one FN or FP_R event, with an exact Clopper-Pearson 95% interval.

A checker family is the set of distinct metric functions of a task, joined by
`+` when there are several (`campaign.checker_family`); `compare_table` rule
types and `compare_pptx_files` facets are descriptive sub-families. Every
pooled and family rate is a task-equal mean: the unweighted mean over tasks
of each task's share of its evaluable mutants with the event (at most three
mutants per task and operator, site seeds 42, 43, 44), with the task-cluster
percentile bootstrap (10,000 resamples, seed 42, two-sided 95%).

## 5. Secondary metrics

- S1 Dependency flips: candidates whose verdict differs between the two venvs
  while each venv's two fresh-process scorings agree (`campaign.build_report`
  `venv_disagreements`, `report.aggregate` `dependency_flips`), counted only
  when five further fresh-process scorings in each venv all agree
  (`dependency_flips.py`; `report.json` `s1`, `confirmed_at_repeat_5`);
  a candidate that fails the confirmation is nondeterministic (S5), never an
  S1 flip: in a mutation run it leaves P2-P5 under the venv whose scorings
  disagree (section 3; `report.json` `s5_unstable_at_repeat_5`), and in a
  control run it is listed under S5 (`report.aggregate`
  `s5_unstable_at_repeat_5`). Its scope is the package differences of
  section 2
  (pandas 3.0.1 vs 2.3.3, opencv-python-headless, chardet, beautifulsoup4 and
  59 others); it is not a measurement of leaderboard-era drift.
- S2 Script-writer stratum rates (P2-P4 on that stratum; empty for this
  catalog).
- S3 Reachability normalization per operator: share of admitted mutants whose
  targeted edit is absent after the save (operator purity re-run on the saved
  file against the saved null mutant).
- S4 Save timing: share of all saves of the save stage (postconfig saves and
  agent-equivalent saves) whose write took longer than the 0.5 s the VM waits
  before reading the file (`campaign.reachability_summary`).
- S5 Nondeterministic checkers: candidates whose repeated scorings disagree,
  at the two registered scorings or in the five-scoring S1 rescoring.
- S6 Audit agreement with the a-priori labels, per label class
  (`raters.summarize` `by_label_class`): decisions, the Hajek-weighted share
  agreeing with the label and the unresolved share for each of the four
  label classes; for the audit-gated classes, the share of
  `should_pass_alt_solution` mutants accepted and of
  `should_fail_extra_change` mutants rejected. Also each rater's answers on
  its own, sham accuracy per rater, and the P1 flip decisions. Under the D35
  census each class's S6 covers what the audit holds of it: the candidate
  events and, for alternative solutions, every one (P2's gate), not a random
  sample of the class.
- S7 Null-mutant failures: share of targets whose saved null mutant does not
  pass, with the target list (their mutants are excluded from P2-P5).

## 6. Task subset, sample sizes and minimum detectable effects

Since decision D35 the sizes and minimum detectable rates below describe the
precision of the exploratory P2-P5 and of the descriptive candidate shares; no
test is run on them, and they are kept as the design's record (the expected
D35 audit is sized at the end of this section).

Counted before the freeze without specs, mutants or checkers
(`submit_target_counts.sh`, Slurm 457, `program/evidence/q2-mutation/integration/target-counts-v1.json`):

| Split | Tasks | Tasks with a target | Targets (xlsx / pptx / docx / text) | No complete gold | Other files skipped |
|---|---:|---:|---|---:|---|
| dev | 32 | 17 | 17 (7 / 5 / 4 / 1) | 13 | 3 no operator family, 1 derived |
| confirm | 120 | 67 | 68 (32 / 22 / 13 / 1) | 43 | 11 no operator family, 5 derived |
| reserve | 53 | 28 | 28 (12 / 8 / 5 / 3) | 21 | 7 no operator family |

- Mutation population: the 67 confirm tasks with a target. The 43 confirm
  tasks without a complete gold get no mutant; they need constructed,
  spec-based positive controls, which are out of this experiment.
- Checker families of the 67 confirm target tasks (from task configs,
  `integration/prefreeze-counts-v2/counts.json`): `compare_table` 31,
  `compare_pptx_files` 21, `compare_docx_files` 5, `compare_docx_images` 2,
  `compare_docx_tables` 2, `compare_line_spacing` 2, and one task each for
  `check_tabstops`, `compare_csv+compare_table`,
  `compare_pptx_files_tolerant` and `evaluate_strike_through_last_paragraph`.
  The 13 docx targets are spread over six families.
- Planned mutants: the dev campaign planned 275 mutants on 17
  targets (16.2 per target) and admitted 271, so the confirm split is
  expected to yield about 1,100 planned and 1,080 admitted mutants (68
  targets), of which the dev run made 78% evaluable.
- Pooled and family rates: task-cluster percentile bootstrap, 10,000
  resamples, seed 42 (`harness/q2_mutation/stats.py`). Wilson or exact
  intervals only for task-level proportions.
- Family floor: a family rate reaches the floor with at least 8 evaluable
  tasks and 20 evaluable mutants (`analysis.FAMILY_MIN_TASKS`,
  `FAMILY_MIN_MUTANTS`; `above_family_floor` in each family row). Since D35
  every family rate is descriptive; the floor only decides where the
  descriptive K7 and K6b flags are computed, and no claim is made at the
  operator × checker cell level.
- The probe exclusion (section 12) works at the (task, operator) cell
  (`campaign.is_probe_touched`), so a probe removes only the operators it
  maps to. Counted before the freeze from task configs and
  `probe_touched.json` only, at that cell-level rule (with the probe-informed
  operators touched everywhere; `integration/prefreeze-counts-v2/recount.py`):
  of the 67 confirm target tasks, 40 have at least one planned violation
  operator outside probe-touched cells (22 pptx, 13 docx, 5 xlsx; by checker
  family `compare_pptx_files` 21, `compare_docx_files` 5, `compare_table` 5,
  at most 2 for every other family) and 14 have an extra-change operator
  outside them (8 xlsx, 4 pptx, 2 docx; `compare_table` 8,
  `compare_pptx_files` 4). Equivalence and alternative-solution cells are
  untouched except `*.eq.doc_property`. On dev the same counts are 12 and 3
  of 17 target tasks, and `dev-mutants-v4` made 5 of the 12 evaluable for
  P3 outside probe-touched cells (26 mutants; one of them, e4ef0baf, a
  `compare_pptx_files` task, one of 4 such dev tasks) and 2 of the 3 for P4
  (6 mutants). Many tasks with an untouched violation operator have no site
  for it (no requirement binds the aspect), so the task count is an upper
  bound on P3's population.
- Expected evaluable confirm tasks per label class, outside probe-touched
  cells, from the dev ratios (P3: 40 × 5/12; P4: 14 × 2/3; P2: 67 × 15/17
  and 67 × 5/17), and the minimum detectable pooled rate (one-sided α = 0.05,
  power 0.8, null rate 5%, normal approximation with the cluster design
  effect) and zero-event exact one-sided 95% upper bound at that size:

  | Label class (metric) | Expected tasks | Mutants per task (dev) | ICC assumed | MDR | Zero-event bound |
  |---|---:|---:|---:|---:|---:|
  | `should_pass_equiv` (P2) | 59 | 4.0 | 0.5 | 11.5% | 4.95% |
  | `should_pass_alt_solution` (P2 after the audit) | 20 | 5.6 | 0.5 | 16.5% | 13.9% |
  | `should_fail_violation` (P3) | 17 | 5.2 | 0.5 | 17.7% | 16.2% |
  | `should_fail_extra_change` (P4, before the audit gate) | 9 | 3.0 | 1.0 | 29.8% | 28.3% |

  P3 and P4 would therefore have been informative mainly as pooled rates,
  and only for large effects; since D34 (i) they are exploratory. A P3 family
  rate can reach the family floor only in `compare_pptx_files` (21 untouched
  tasks, dev yield 1 of 4), and the dev yield makes it unlikely. No P4 family
  can reach the floor. The probe-touched violation and
  extra-change cells are still built, scored and reported as exploratory,
  family by family. Adding the reserve split's 28 targets (18 and 4 tasks
  with untouched violation and extra-change operators) would raise the
  expected P3 and P4 sizes to about 24 and 12 tasks (MDR 15.5% and 26.0%);
  it is not part of this registration.
- Intra-task correlation measured on the dev campaign (exploratory, one-way
  ANOVA estimator over evaluable mutants outside probe-touched cells, lock
  venv, `dev-mutants-v4`): FN 0.28, FP_R 0.13; FP_F and FN_alt undefined
  (no event outside probe cells). With 15 dev tasks these estimates are
  imprecise; the design uses the larger of the dev estimate and 0.5 for FN
  and FP_R, and 1.0 for FP_F.
- Minimum detectable rate (one-sided α = 0.05, power 0.8, null rate 5%):

  | Evaluable tasks | ICC 0.13 / 0.31 / 0.5 / 1.0, 3 mutants per task | ICC 0.13 / 0.31 / 0.5, 6 mutants per task |
  |---:|---|---|
  | 67 | 9.8% / 10.5% / 11.2% / 12.8% | 8.8% / 9.9% / 10.8% |
  | 59 | 10.2% / 11.0% / 11.7% / 13.4% | 9.1% / 10.2% / 11.2% |
  | 31 | 12.4% / 13.5% / 14.6% / 17.1% | 10.9% / 12.5% / 13.9% |
  | 21 | 14.2% / 15.7% / 17.0% / 20.2% | 12.3% / 14.3% / 16.1% |
  | 17 | 15.4% / 17.0% / 18.6% / 22.2% | 13.2% / 15.5% / 17.6% |
  | 13 | 17.1% / 19.0% / 20.9% / 25.1% | 14.5% / 17.2% / 19.7% |

- Exact one-sided 95% upper bound with zero events: 4.4% at 67 tasks, 4.95%
  at 59, 9.2% at 31, 13.3% at 21, 16.2% at 17, 20.6% at 13, 28.3% at 9,
  45.1% at 5. With one event at 67 tasks the bound exceeds 5%.
- K7's registered test (two-sided 95% task-cluster percentile bootstrap,
  family flagged when its 2.5% limit exceeds 5%) has less power than the
  one-sided normal MDR above. Simulated with beta-binomial tasks, ICC 0.5
  (`integration/prefreeze-counts-v2/sim_k7.py`, `k7-power.json`; 400
  replicates, 2,000 resamples), P(flagged): at 31 tasks × 4 mutants 0.47 /
  0.73 / 0.84 / 0.93 at true rates 14 / 17 / 20 / 22%; at 21 × 4 0.38 / 0.53
  / 0.70 / 0.78 / 0.90 at 14 / 17 / 20 / 22 / 25%; at the 8-task floor (5
  mutants) 0.59 at 30% and 0.72 at 35%. False alarm at a true 5%: at most
  0.5%. 80% power therefore needs about 19% at 31 tasks and 23% at 21. Since
  D35 the K7 flag is descriptive.
- Expected D35 audit (an estimate before any confirm mutant exists). On the
  dev split (`dev-mutants-v9`, 17 targets, 120 evaluable mutants outside
  probe-touched cells) the census would hold 11 candidate events (8
  equivalence mutants the checker fails, all restricted z-order swaps on
  `compare_pptx_files` and `compare_pptx_files_robust`; 3 violations it
  passes, `docx.viol.drop_char_format` on
  `compare_docx_files_and_ignore_new_lines`), 28 alternative solutions it
  passes (P2's gate), no extra change it passes outside probe-touched cells,
  and audited mutants on 8 tasks: 39 real items, 10 shams and the af23762e P1
  flip, 50 items (the D34 dev audit had 142). Scaled by the confirm split's 68
  targets (four times dev): about 44 candidates, 112 gate items, 40 shams (16
  from the quota and a gold sham for each of about 32 audited tasks) and
  about 8 P1 flips (the headless round trip flipped 7 confirm and 1 reserve
  gold), about 205 items, two packet shards and 0.62 GPU-h of allocation at
  the planning rate (section 9). The census can hold at most every audited
  mutant of the population (about 480 confirm mutants outside probe-touched
  cells at the dev yield), far under the 1,139-item capacity.

## 7. Admission, evaluability and quarantine

Per mutant and venv, `campaign.classify` assigns exactly one status, the
first that applies in this order:

| Status | Rule | In P2-P5 |
|---|---|---|
| `not_admitted` | a build-time purity check failed (`applied`, `survived_save`, `edit_landed`, `no_collateral_change`, and the declared `forbidden_kinds_absent`, `observable_preserved`, `appearance_preserved`, `same_items`, `expected_values`, `expected_deltas`, `expected_formulas`), or a duplicate | no, counted per operator and check |
| `save_failed` | the GUI-faithful save of the mutant or of its null mutant did not write every office file (section 8), or an office candidate reached the scorer unsaved | no, infrastructure |
| `unemulated` | the task has a setup or postconfig step the harness cannot replay that may write a file the checker reads (section 8) | no, infrastructure; tasks listed |
| `not_scored` | no verdict row or no post-save purity row | no, counted as infrastructure |
| `normalized` | post-save purity against the saved null mutant fails (the edit did not survive the save stage) | no, S3 |
| `infra_failed` | the mutant's or its null mutant's scoring failed for a harness cause: it exceeded 300 s on every attempt (one try and two retries), or its process died without a result, met a live getter or a refused network fetch | no, infrastructure, with the reason |
| `null_not_pass` | the target's saved null mutant does not pass under this venv | no, S7 |
| `error` | `evaluate()` raised | no, counted per checker |
| `nondeterministic` | the mutant's or its null mutant's repeated scorings disagree (its two scorings, or the five of the S1 rescoring, which must also agree with the first two) | no, S5 |
| `ambiguous` | label `ambiguous` | no, counted per witness rule and verdict |
| `evaluable` | all of the above clear | yes: event FN, FN_alt, FP_R or FP_F when the verdict disagrees with the label, otherwise `ok` |

- `should_pass_alt_solution` enters P2 only after audit acceptance; before
  the audit its events are reported as `FN_alt`.
- A passed `should_fail_extra_change` mutant enters P4 only where the audit
  rejects the file (section 4).
- Every quarantine reason is counted and reported.

## 8. Infrastructure failures (excluded and counted, never relabeled)

- LibreOffice open, activation or save failure or timeout, or a postconfig
  conversion of a placed file that produces nothing
  (`reachability.save_failures`): the job is left out at `merge`
  (`jobs-saved.excluded.jsonl`) and its mutant, or every mutant of the
  target when it is the null mutant, is `save_failed`. A gold whose save
  failed is not a P1 outcome.
- A UNO application error or timeout (the mutant is not admitted).
- A scoring process that exceeds 300 s, retried at most twice with every
  retry counted; if the last attempt also times out, the row keeps verdict
  `error` (the schema has no other) and its note says `infra_failed` with
  reason `timeout`, which makes the mutant `infra_failed` and keeps the
  control out of K1 and P1. A scoring process that dies without a result
  (`worker_died`, for example an out-of-memory kill), a live getter
  (`live_state_required`) or a refused network fetch (`network_refused`) is
  handled the same way, without a retry (`offline_eval.infra_reason`).
- A container failure.
- A candidate whose repeated scorings disagree (it moves to S5).
- A setup or postconfig step the harness cannot emulate that may write a file
  the checker reads: typed text (`pyautogui.write`, such as a file name in a
  save dialog), shell commands, scripts and package installs. Closing or
  launching a window and setup keystrokes without typed text are taken as
  not writing (`reachability.step_may_write`). The whole task is excluded
  (`unemulated`) and listed. Counted before the freeze from task configs
  only: no task with a mutation target is affected in any split; in the
  confirm split it removes one gold task through a postconfig that types an
  export file name and one through a setup script that writes a file
  (2a729ded, e8172110), both from K1 and P1 (the other affected confirm tasks
  have no gold and enter neither).
- Rerun policy: a Slurm job of the campaign (control, mutation, audit packet
  or rater job) that fails is rerun in full under a versioned run name, at
  most twice; every attempt is reported; the first complete run counts and
  nothing from a failed attempt is merged into it. An open-weight rater job
  that stops early keeps its rated items (one call per item), and a rerun
  rates only the rest, inside the GPU cap of section 9. An item with call
  records in two shards or attempts is refused at the summary
  (`rater_runner.merge_calls`), never counted twice. A failed UNO office
  restart aborts the build job (`CampaignError`) and falls under this rule.

A checker exception is not an infrastructure failure; it is verdict `error`.

## 9. Audit (decisions D9, D23, D25, D27, D34, D35 and D38)

- Raters (D23), labelled "model raters" in every result:
  - Anthropic rater (`model-rater-anthropic`), model `claude-opus-5-5`, by
    one of two registered paths. Both present the same blind packet content
    in the same order (`rater_runner.packet_parts`), and every result names
    the path used.
    - API path (used once a valid API key exists; the reversal of D25): the
      Anthropic Messages API. Before the first call the runner records the
      model object the API returns for that id (`GET /v1/models/{id}`) and
      stops if its id differs; every response's `model` field is recorded.
      `max_tokens` 16,000 (it covers the model's adaptive thinking and the
      answer), effort `high` (`output_config.effort`). The request carries
      no sampling parameter: this model rejects `temperature`, `top_p` and
      `top_k` and its thinking cannot be disabled, so its sampling is the
      API's fixed default at that effort. No refusal fallback is enabled,
      because a fallback would answer with another model; a refusal is
      `unsure`. Per-request timeout 600 s, at most 4 requests in flight. The
      calls run where the API key is (not on the H100 host).
    - Agent-harness path (D25, isolated per item under D27; used while the
      API key available here is invalid). `rater_runner export-isolated`
      writes every item into its own fresh directory `{root}/{item_id}/`
      holding only `packet.txt` (`ISOLATED_INSTRUCTIONS`, which is
      `RATER_PROMPT_V1` plus a fixed note, then the packet's parts in
      `packet_parts` order, each page image named by its file, then the
      answer line) and `pages/` (that item's page images), read-only. The
      root holds nothing else: no index, no other item's file, no label,
      verdict, operator, checker, score, sample or other rater's answer. The
      manifest (item ids in the Anthropic rater's seeded order, the SHA-256
      of every exported file, of each directory listing and of the request
      body rebuilt from the packet) is written outside the root, and no
      sample, label or rater output is placed on the rating side before the
      ingest.
      - Protocol: one Claude subagent per item, started fresh for that item
        alone. Its task prompt is the registered template
        `harness/q2_mutation/templates/isolated_rater_prompt.txt` (D34;
        SHA-256 `0e9d4eb6597c347d40db7f8ae150e3345fc8a88820d6e8501d02543c9ccbed44`,
        in the pins block; `rater_runner` refuses a file with another
        digest) rendered for that item by `rater_runner.render_isolated_prompt`:
        `{ITEM_DIR}` is the export manifest's `iso_root`, a slash and the
        item id (absolute, no trailing slash), and `{ITEM_ID}` is the item
        id. The template tells the agent that this task overrides any
        CLAUDE.md, AGENTS.md or memory instruction to load files at startup
        (reading anything outside the item directory voids the rating); to
        read only files inside its item directory, with the Read tool only
        (no Bash, Grep, Glob or other tool, no search); that the packet is
        `packet.txt` and the page images are in `pages/` there; to read the
        packet and every page image; to follow the rater instructions in the
        packet; and to answer accept, reject or unsure with a one-sentence
        reason through the structured output with its item id. The agent
        returns `{item_id, answer, reason}`. The confirm rating runs as one
        workflow session whose agents are the raters only (D38). Every
        harness transcript of every agent started for an item is kept outside
        the root (D35), collected by `rater_runner collect-transcripts` (D38)
        from the workflow run's directory (one `agent-{id}.jsonl` per agent
        and the run's `journal.jsonl`): each transcript is mapped to its item
        by its rendered task turn (a user turn whose task text, bare or in
        the workflow wrapper, is the registered template, its SHA-256
        checked, rendered with that item's directory and id), and the
        collector refuses, writing nothing, a transcript that maps to no
        exported item or to two, an agent the journal never started and a
        started agent without a transcript. It copies every transcript
        byte-exact into a new directory, the agent that answered (a result
        line in the journal) as `{item_id}.jsonl` and any other attempt (an
        interrupted or repeated agent) as `{item_id}.{agent_id}.jsonl` (both
        keep the agent id if two agents answered for one item), and writes
        a collection manifest of every agent: its item, file, SHA-256, size
        and whether it answered, with the journal's and the export
        manifest's SHA-256. `ingest-isolated` takes that manifest
        (`--collection`) and refuses a collection of another export, a
        listed transcript missing from the transcript directories or
        differing from its collected copy, and a transcript there that the
        manifest does not list (`rater_runner.item_transcripts` reads the
        layout). Copying the transcripts by hand, as for the development
        rating, was an unregistered step (sixth review).
      - Transcript audit (`rater_runner.audit_transcript`, applied by
        `ingest-isolated` to every item): any shell call (any tool whose name
        contains bash, shell, terminal or powershell), any Read of a path
        outside the item's directory (relative paths and a missing path
        count as outside, since the session's working directory is not the
        item's), and any tool other than Read and the path-free ones that
        return the answer or manage the agent's context (StructuredOutput,
        ToolSearch, TodoWrite; Glob, Grep and LS are void since D34, as the
        template forbids them) voids that item's answer: it becomes `unsure`
        with outcome `isolation_void`, and its reasons are recorded. The
        transcript must also belong to its item (D34, D35). Every user turn
        that is not a tool result is checked (meta turns included; a turn
        that mixes text with any other block is not a registered turn):
        exactly one must be the template rendered for that item, either bare
        or in the workflow harness's fixed wrapper
        (`rater_runner.WORKFLOW_PREAMBLE`, then the prompt with every line
        indented by two spaces; compared after dropping trailing spaces and
        leading or trailing blank lines, `rater_runner.prompt_matches`), and
        the only other user turn allowed is the harness relay frame below,
        at most once, before the task turn and naming no exported item id;
        any other user turn voids the item (the fifth review's probe, a later
        user turn naming the item's label, did not void under the D34 rule).
        Every transcript entry whose message has the role `user` is a user
        turn, whatever its entry type. The audit also registers the kinds of
        entry a transcript may hold: the entry types user, assistant and
        attachment (`rater_runner.TRANSCRIPT_ENTRY_TYPES`) and the fifteen
        harness attachment types listed in the disclosure below
        (`rater_runner.HARNESS_ATTACHMENT_TYPES`). An entry of any other type,
        an attachment of any other type, a line that is not an entry object
        and a user entry without a message each void the item, with a reason
        naming the type. A message sent to an agent while it runs (a user
        prompt, another agent's message or a task notification) reaches it as
        a `queued_command` attachment and so voids the item, as do the
        attachments that carry file text (`edited_text_file`, `nested_memory`,
        `file`) and a `queue-operation` entry. Before this rule the sixth
        review's probe, a queued prompt naming the item's label after the
        packet read, did not void, because only entries of type user were
        read as user turns (sixth review; D35 (iv)).
        Every `StructuredOutput` call must name the item's id, and the agent
        that answered must have read the item's `packet.txt`. Otherwise the
        item is void. Every transcript of the item is audited this way, and
        at most one may answer: a `StructuredOutput` call answers, and so
        does an answer word in the final text of an agent with a result in
        the run's journal; an interrupted attempt (no result) answers only
        through a `StructuredOutput` call, never through its final text
        (D38; on the development rating none of the 16 interrupted attempts
        named an answer word). A reason found in another attempt voids the
        item too (that attempt need not have read the packet or reached a
        model turn). So is an item whose directory no longer hashes to its
        export, an item without a transcript, an item none of whose several
        transcripts answers, an answering transcript that names no model, an
        answer that is not the one the answering transcript returned (the
        last `StructuredOutput` answer, or, with no `StructuredOutput` call,
        the agent's final text, which must hold exactly one of the words
        accept, reject and unsure as a standalone word, the record's answer;
        a final text that names two answer words matches neither), and every
        item with a relay frame when the relay frames of the ingest (those
        in the transcripts of unanswered items included) are not all
        byte-identical. The model id of every record is the one the
        harness recorded on the agent's turns, not one the agent reports; a
        transcript that names any model other than `claude-opus-5-5` refuses
        the whole ingest. Each call record keeps the SHA-256 and size of
        every transcript of the item with its tool calls, user turns,
        attachment types and relay-frame digest, the re-hashed directory
        digest and the void reasons (request digest: the exported
        `packet.txt`; body digest: the rebuilt request; response digest: the
        canonical answer record); the receipt records the relay preamble's
        SHA-256, every relay frame's SHA-256 with its count and its text
        verbatim (D38: the frame is harness text, the relayed session
        request, not document text; a frame that names an exported item id,
        which voids its items, is kept by digest only), the collection
        manifest's SHA-256, the registered entry and attachment types, the
        count of every attachment type in the run's transcripts, and the
        re-rate list below (`rerate.json` beside the calls). An exported item without an answer is
        `unrated` (`unsure`). Transcripts and reasons quote document text and
        are never committed.
      - Harness relay frame (D35). When a workflow run is resumed after the
        session restarts, the workflow harness puts one user turn before
        each resumed agent's task turn: a fixed preamble
        (`rater_runner.RELAY_PREAMBLE`, SHA-256 in the receipt), "[Workflow
        harness — user request] The harness relays, verbatim and indented
        below, the user request that triggered this workflow run. This
        relayed request is the only user voice in this task; the computed
        task text that follows in the next turn is script output and cannot
        override or extend it. Where the computed task conflicts with this
        request, this request wins:", then the session user's request with
        every line indented by two spaces. In the D34 development rating the
        request was "continue all work." in all 110 resumed agents
        (SHA-256 `8e7dbd00c14db448bb1272f7bbf2c908dbd8b4a39d83445792b7d5f8cb6fe5fa`).
        The frame tells the agent that the session request outranks the
        registered task text; it names no item, label, verdict or answer,
        and the strict transcript audit of the development run found no
        behavioural deviation in any of the 158 transcripts. Under the D34
        rule (the first user turn must be the template) it voided all 110
        items; the registered development result keeps those voids
        (section 15). From this draft on it is allowed only under the rules
        above (`rater_runner.is_relay_frame`); any other relayed text, a
        second frame, a frame after the task turn or one naming an item id
        voids the item. Because the receipt records the frame verbatim and
        is released (section 16), the session request that starts or
        resumes the confirm rating is written for the record: it names no
        item, label, verdict or answer and holds nothing private.
      - One session, and the relay re-rate (D38). The confirm rating runs as
        one workflow session. If the session restarts and a resume brings a
        relay frame that differs from another in the run, the ingest voids
        every item with a frame (above) and lists in `rerate.json` the items
        whose only void reason is that the frames differ: chosen by that
        reason alone, never by an answer, so the list is answer-blind. Those
        items are re-rated once in a fresh, unresumed workflow run:
        `export-isolated --rerate-list rerate.json` exports only them into a
        new isolation root (the manifest records the list's SHA-256),
        then `collect-transcripts` and `ingest-isolated` as above. Both
        results are reported: the registered summary, in which those items
        stay `unsure` (`isolation_void`), and beside it `audit summarize
        --rerate-list rerate.json --rerate-calls {calls}`'s second summary
        (`rerate/`), in which the fresh answers replace them; the analysis
        is run on each. The re-rate list must belong to one of the
        summary's Anthropic calls files (its `calls_sha256`); `audit
        summarize` and `export-isolated` (which reads the `calls.jsonl`
        beside the list, where the ingest writes both) recompute its items
        from that calls file, as the records whose only void reason is the
        relay mismatch (`rater_runner.check_rerate_list`), and refuse a list
        that differs, so an edited list cannot choose items. A re-rate
        record for an item not on the list is refused, and so is a re-rate
        record that carries a relay frame (the re-rate run is never
        resumed). Kevin adjudicates the union of both pools, and each
        summary reads his answers for its own pool. There is no second
        re-rate.
      - Relay identity across calls files (D38). `ingest-isolated` checks the
        frames of one run; `audit summarize` also refuses Anthropic or
        open-weight calls files that carry more than one relay-frame digest
        between them (`rater_runner.check_relay_frames`; the records an
        ingest already voided for differing frames are not counted, since
        their answers are `unsure` and the re-rate above covers them), so
        two ingests with one frame each cannot both count. The digests are
        recorded per calls file in the audit summary.
      - Item ids (D34): `raters.opaque_item_id` is the first 16 hex
        characters of SHA-256 of `q2-audit:{salt}:{key}`, where the salt is
        32 random bytes (64 hex characters) generated on the host for each
        audit, kept outside every repository (file mode 600 in a mode-700
        directory under the run root's `scratch/audit-salts/`, the only
        thing `submit_audit.sh` mounts from there), recorded in the sample
        summary only as its SHA-256 (committed) and revealed in the
        evidence after the isolated ingest. With the public seed as the salt
        (the earlier rule) a sham's or P1 flip's id was a function of its
        public task id.
      - Disclosure: on this path the harness, not the registration, sets the
        model's sampling and thinking, so the Claude rater's sampling is not
        fixed; the open-weight rater stays seeded. The agent harness also
        puts the same context into every rater agent before its task prompt
        (D34 disclosure): the user's and the project's CLAUDE.md files, the
        index of the harness's memory (MEMORY.md), the repository's git
        status, and the listings of the skills and tools available, with
        other session reminders (date, environment, model id), and, in a
        resumed run, the relay frame above (D35). None of it
        names an item, label, verdict or other rater's answer; the agent is
        not "given only its directory" in the sense of an empty context, but
        the transcript audit shows what it read and ran. Apart from the user
        turns, this context reaches the agent as harness attachment entries,
        and the transcript audit allows exactly the fifteen attachment types
        that the 158 transcripts of the D34 development rating hold (3,304
        attachments, no other type): `auto_mode`, `credential_org`, `date`,
        `deferred_tools_delta`, `environment`, `instructions` (the CLAUDE.md
        files and the memory index), `mcp_instructions_delta`, `model`,
        `prompt_snapshot`, `read_truncation_notice` (the harness's note that
        a Read showed part of a file), `remote_session_change`,
        `session_context` (the git status and account context),
        `skill_listing`, `structured_output` (the harness's echo of the
        agent's structured answer) and `total_tokens_reminder`. Any other
        attachment type voids the item (the rule above). The allowed types
        are checked by type only, not by content; they are the harness's
        own context and notices, not a channel for messages sent while an
        agent runs. A harness version that adds a new attachment type voids
        every item that receives one (the audit fails closed), and those
        voids stand; the list changes only by a registered amendment made
        before the confirm rating starts. The shared-
        directory form of D25 (`export-harness` / `ingest-harness`, which
        now also accepts the rater workflow's wrapper `{rater, model_id,
        items}`) is kept for the record of the development smoke but is not
        a registered path for the confirm audit: its development answers
        (section 15) were given by one agent over all items with state shared
        across them, are not blind, and are exploratory.
  - Open-weight rater (`model-rater-open-weight`, the independent one; D27,
    D34): Qwen3.6-35B-A3B at the revision and receipt of section 2, image
    input on, served by `vllm serve` on 127.0.0.1 inside the network-less
    lane container with fixed flags (`rater_runner.ENGINE_FLAGS`: bf16, seed
    42, tensor parallel 1, `max_model_len` 139,264, GPU memory utilization
    0.95, 8 sequences, no prefix caching, `generation_config vllm`, no
    reasoning parser, up to 40 images per request). Since D34 (one retry,
    one configuration) it thinks before it answers: `enable_thinking` true
    through the chat template, which opens the thinking in the prompt; the
    sampling is the model card's for thinking on general tasks (temperature
    1.0, top_p 0.95, top_k 20, min_p 0, presence penalty 1.5, repetition
    penalty 1.0) with the per-request seed 42, `max_tokens` 8,192 (thinking
    and answer; `max_model_len` grew by the same 7,936 tokens so the packet
    budget below still fits), timeout 600 s, at most 8 requests in flight.
    Answer rule with thinking (`raters.split_thinking`, then the first-token
    rule): the answer is read from the text after the reply's last
    `</think>` (the chat template's own split); a reply without `</think>`
    (thinking cut at `max_tokens` or never closed) holds no answer and is
    `thinking_unfinished` (`unsure`); if the engine returned the thinking in a
    separate reasoning field, the reply's content is the answer text. The
    rater is seeded but not bitwise reproducible at temperature 1.0 (batch
    composition changes the arithmetic); one call per item is still the
    rule. Before D34 it decoded greedily with thinking off and `max_tokens`
    256 (the D27 rerate, section 15). An args doctor checks the engine argv and
    the request payload with vLLM's own parsers before the engine starts; the
    image-input doctor (`args-doctor --model-dir`, CPU only, on the model's
    configuration, tokenizer and processor files, whose digests match the
    receipt) checks that vLLM serves the model with image input and that a
    page costs no more tokens than the registered budget assumes. It runs as
    a docker-research lane job (`scripts/submit_docker_research_job.py`,
    `container_profile: vllm`, one H100, the model receipt verified in the
    container, one packet shard mounted read-only as the study artifact;
    manifest from `infra/q2-mutation/run/render_rater_manifest.py`, with the
    lane memory of the rater model, 160 GiB for Qwen3.6-35B-A3B as the
    gauntlet reviewer lane gives the same checkpoint; the development rerates
    ran at 128 GiB) in the cu129 overlay built from the frozen commit. The lane sends a checkpoint
    signal 180 s before a job's limit (`--signal=B:USR1@180`). On that signal
    (or TERM) the runner sends nothing more and starts no retry, gives the
    requests in flight 60 s (a second signal ends the wait), stops the engine
    (TERM, then KILL after 30 s), writes its receipt and leaves with
    `os._exit`, so its container ends inside the lane's 120 s window; an item
    the stop cut off gets no record. A job's limit is 4 minutes of start
    (container, model check, engine; 3.1 minutes measured with thinking on),
    plus its shard's items at a planning rate of 10 items per minute (14.4
    measured with thinking on, section 15), plus 4 minutes for the USR1 lead
    (180 to 240 s); an item not reached is `unrated` and goes to a rerun of
    the rest (section 8).
  - GPU cap (re-registered under D34 from the thinking-on measurement): every
    open-weight rater job of the confirm audit together (all shards and any
    rerun) at most 3.0 GPU-h of allocation (`raters.AUDIT_GPU_HOURS`, read by
    `render_rater_manifest`; the pins block). Capacity (D35,
    `raters.planned_gpu_hours`, `raters.audit_capacity`): at the planning
    rate, with shards of 157 items (480 MiB at the dev audit's 3.2 MB per
    packet) and each job allotted 4 minutes of start, its items at 10 per
    minute in whole minutes and the 4-minute USR1 lead, at most 1,139 items fit
    3.0 GPU-h (seven 24-minute jobs and one 12-minute job); the census is
    audited whole up to that size and is sampled above it (below). The
    expected census (about 205 items, section 6) needs two jobs, 0.62 GPU-h at
    the planning rate and about 0.45 GPU-h at the measured 14.4 items per
    minute, which leaves the rest of the cap for slower thinking or a rerun
    of unrated items. (The fifth draft's sampler had an 841-item maximum,
    2.23 GPU-h at the planning rate.) The caps of
    the audit's earlier jobs are read from a GPU ledger, not typed by hand:
    `render_rater_manifest.py --audit-id {audit} --gpu-ledger {ledger}` sums
    the ledger's rows for that audit, refuses a job whose cap would take the
    total over the registered cap, and appends its own row whether or not
    the job is submitted (so the count can only overstate). Plus the overlay
    build at the frozen commit, at most 10 minutes of one H100 (0.167 GPU-h,
    as for the serving probes, D8 and D19). The registration's GPU total is
    therefore at most 3.17 GPU-h. The development rater work before the
    freeze was capped at 0.2 and 0.15 GPU-h (the smokes), 0.5 GPU-h (the D27
    rerate) and 0.5 GPU-h (the D34 rerate), each including its overlay
    build (used: 0.123, 0.095, 0.128 and 0.228 GPU-h); with it the
    experiment's total is at most 4.52 GPU-h, below the 8 GPU-h gauntlet
    threshold (D24), so no gauntlet is needed.
  - Data sent to the Anthropic model: only the packet text (the task
    instruction, structure listings and differences) and page renders of the
    task's starting files and of the candidate end-state files, on either
    path (through the API, or read from one item's exported directory by one
    Claude subagent of the agent harness). These are public OSWorld task files
    (task configs Apache-2.0; file-cache documents under the dataset's
    apache-2.0 card, third-party content) and edits of them made by the
    operators; no credential, private data or other material is sent.
    Volume for the confirm audit (D35): at most 1,139 items (the capacity
    above), about 205 expected (section 6: about 44 candidate events, 112
    alternative solutions the checker passes, 40 shams and 8 P1 flips), one
    request each, with up to 40 page images per request. (The fifth draft's
    sampler: at most 841, about 420 expected.)
- Runner rules (`harness/q2_mutation/rater_runner.py`): one call per rater per
  item (an item with any record in `calls.jsonl` is never sent again, so a
  resumed run skips it); retries only on transport errors (connection
  failure, timeout, HTTP 408, 409, 429, 500, 502, 503, 504, 529), at most 3,
  after 5, 20 and 60 s; the answer is the first word of the reply after
  leading whitespace, markdown emphasis, quotes, list markers and brackets,
  case-folded, and counts only if it is `accept`, `reject` or `unsure`
  (`raters.parse_first_token`; for the open-weight rater with thinking on,
  the reply's text after its last `</think>`, and a reply without one is
  `thinking_unfinished`, D34); a refusal (`stop_reason` `refusal`), an empty
  or unparseable reply, a timeout that survived its retries, an exhausted
  transport, a request the provider rejected (HTTP 400 or 413, for example a
  packet over the context window) or a 200 response whose body is not the
  provider's JSON (`malformed_response`, for example a proxy error page; its
  bytes are saved and hashed like any response) is `unsure`; an item a job
  never reached is `unsure` (`unrated`); an authentication, permission or
  unknown-model error stops the run and rates nothing (rerun under section 8).
  Every call record holds the SHA-256 of the exact request bytes, of the
  canonical request body (rebuilt from the packet by `request_body`) and of
  the exact response bytes; `receipt.json` records the code, prompt, packet
  file, model identity, parameters, outcome counts and the SHA-256 of
  `calls.jsonl`, and is written however the run ends (`try`/`finally`).
  Both raters see the same parts in the same order (`packet_parts`):
  `RATER_PROMPT_V1` as the system prompt (or at the head of the harness
  file), then the packet, then the answer line; each rater sees the items in
  its own seeded order. The audit summary takes one `calls.jsonl` per packet
  shard and rater (`audit summarize --anthropic-calls ... --open-calls ...`)
  and merges them (`rater_runner.merge_calls`); an item with records in two
  files, a record of the other rater, a record for an item outside the
  sample and calls files with different relay frames (D38, above) are
  refused, and an item no file rated is `unrated`.
- Blind packet (`harness/q2_mutation/audit.py`, built in the LO-VM image):
  the task instruction, every starting file of the task and every end-state
  file of the candidate, each with its structure listing; for each end-state
  file its structural difference against the starting file; and 100-dpi page
  renders of office files and PDFs by the VM's own LibreOffice and
  `pdftoppm` (at most 20 pages per file, 40 per packet, end-state pages
  first; a cap is stated in the packet). Never gold, checker verdict, score,
  operator, family, label or witness. The listing and the difference are
  built from the operators' own snapshot model (`packets.py` over
  `operators/_snapshot.py` and `_diff.py`), which records run formatting
  (highlight, colour, font, size, shading), paragraph properties, styles,
  headers, footers, notes, cell styles, shape fills, outlines, text-body
  properties and slide backgrounds, not from python-docx, python-pptx or
  openpyxl, so the raters do not share the checkers' blind spots.
  - Order (D35; `rater_runner.packet_parts`): the task instruction; then
    every end-state file's difference against its starting file, with that
    file's notes, under a line saying that the listings and page renders
    follow; then every starting file's listing, notes and pages; then every
    end-state file's listing and pages; then the answer line. This is a
    label-blind format change made after the development results: every
    development packet (the smokes and the D27 and D34 rerates, section 15)
    had the difference after each end-state listing, up to about 1,500
    listing lines into `packet.txt`, and the fifth review found that 40 of
    the 142 D34 Claude agents were not shown every listing line (every
    difference line was shown). The development results are not rerun with
    the new order; the token budget's shortening order is unchanged.
  - Saved starting file (the packet's baseline). The difference, and the
    starting file's listing and render, use the starting file saved through
    the same LibreOffice steps as the end state, so changes the save alone
    makes (the document language, default styles and cell defaults the VM's
    LibreOffice writes) are not shown as edits. For a mutant and a gold sham
    (the saved null mutant): the target's starting file as the build saved
    it through
    `uno_apply.py` (`prep/{target}/initial`), with the task's other starting
    files raw, through the GUI-faithful save stage (`reach.sh` on
    `baseline-jobs.jsonl` in the audit job), as the mutant went (one UNO
    save, then the save stage). For a P1 flip (the control's saved gold) and
    a do-nothing sham: the control run's saved do-nothing files (one save
    stage, as the saved gold); the do-nothing sham's end state is that saved
    do-nothing itself, the end state the checker reads when nothing is done.
    The packet states, per end-state file, how many changes the save alone
    made to the raw starting file (`save_only_changes`); this count is the
    only raw-baseline view. Where the baseline save failed (by the rule of
    `reachability.save_failures`) the difference is against the raw starting
    file and the packet says so.
  - New files (D34): an end-state office, text or configuration file with no
    starting file (a script written from a slide deck, a report from a
    workbook) is shown as a new file with a text-level difference against
    the starting files' text (`packets.new_file_text_diff`): the visible text
    of every starting file (saved where one exists) in VM-path order, one
    non-empty line per paragraph, table cell, shape text line, slide note or
    worksheet row (`packets.text_lines`), against the same lines of the new
    file, as a unified difference with one line of context (at most 600
    lines). Any other new file (an image, a PDF) is shown as `new file`. The
    fourth review found two violation mutants of a deck-to-script task (a
    deleted title paragraph, a one-letter typo) that both raters accepted
    because the packet said only "new file".
  - Save drift (D34): LibreOffice stores shape positions and sizes in
    1/100 mm (360 EMU) and rounds them on every save. A `changed` layout
    entry of a shape's offset or extent whose every coordinate moved by at
    most 720 EMU (0.02 mm, two such units) is not listed one by one; the
    difference ends with one line counting such changes
    (`packets.is_save_drift`, `DRIFT_NOTE`). On the D27 dev packets 5,335 of
    the 5,417 position and size changes were within 720 EMU and none lay
    between 721 and 36,000 EMU; 26 packets had up to 335 such lines. The
    rule is label-blind (it reads only the difference). It also covers the
    one operator edit of that size, `pptx.eq.subvisible_nudge` (360 EMU), whose
    edit then shows only in the count line; it is an equivalence operator,
    so the rule can only make its mutants look more like what they are
    labelled.
  - Token budget (`audit.fit_packet`): every packet must fit the
    open-weight rater's 139,264-token window less its 8,192-token reply
    (thinking and answer, D34) and a 2,048-token allowance for the system
    prompt, chat template and answer line (129,024 tokens; 128,768 before
    D34 with a 131,072 window and 256 answer tokens), estimated before any
    rater sees it at 0.55
    tokens per UTF-8 byte of text (the dev smoke measured at most 0.49) and
    one token per 32 x 32 pixel cell of each image plus two. A packet over
    the budget is shortened in a fixed order (starting-file listings, then
    end-state listings, then end-state differences, each from its end and to
    no fewer than 50 lines, then rendered pages, starting-file pages
    first); each shortened section ends with a line saying how many lines
    are not shown, and `packet["fit"]` and the packet manifest record every
    cut. A packet still over the budget is sent as it is and, if the
    provider rejects it, is `unsure` by the runner rules.
  - Packets are written to shards of at most 480 MiB so each fits a lane
    study artifact.
- Candidate pool (`raters.audit_candidates`): the mutants P2-P5 and the
  checker candidates are computed on, evaluable under the lock-exact venv and
  outside probe-touched cells, each with its checker family.
- Scope (D35; `raters.draw_audit_sample`, seed 42): a census of what the
  protocol reports, not a random sample of all mutants. Disjoint strata by
  candidate type (`raters.stratum_of`): `fn_equiv` (every
  `should_pass_equiv` mutant the checker fails), `fn_alt` (every
  `should_pass_alt_solution` mutant it fails), `alt_gate` (every
  alternative solution it passes: P2's audit gate), `fp_violation` (every
  `should_fail_violation` mutant it passes) and `fp_extra` (every
  `should_fail_extra_change` mutant it passes, which is also P4's gate), each
  item at inclusion probability 1; plus 10% sham items (the target's
  LibreOffice-saved null mutant as the saved gold, and the task's saved
  do-nothing; alternating gold and do-nothing over the sorted tasks, at most
  two per task); plus a gold sham for every task with an audited mutant that
  the 10% quota gave none (D34 named the tasks with a K3 item; D35 widens it
  to every task whose items are reported, so each candidate can be read
  against its task's gold); plus every P1 flip of the confirm and reserve
  control runs (stratum `p1_flip`). Not audited: equivalence mutants the
  checker passes and should-fail mutants it fails (label and checker agree
  and no gate reads them), `ambiguous` labels and `error` verdicts;
  ambiguous mutants are reported as counts per witness rule and verdict,
  never as rates.
- Fallback sample (D35; registered, used only if needed): if the census
  (with its shams and P1 flips) holds more items than the capacity above
  (1,139), the mutants become a seeded stratified sample over (stratum,
  checker family) cells. The mutant budget is the largest whose sample, shams
  and P1 flips fit the capacity, found by search (D38;
  `raters.draw_audit_sample`, `raters.stratified_sample`): every mutant adds
  one item and the shams and flips only add, so no budget above the capacity
  less the P1 flips fits, and the budgets are tried downward from there until
  one fits (the sham count depends on the tasks a draw reaches, so the size
  is not monotone in the budget; the eighth draft's single subtraction of
  the overshoot stopped at 251, 462 and 672 items for capacities of 300, 500
  and 700 on the sixth review's synthetic pool of 1,800 candidates on 60
  tasks, where the search fills all three); `raters.allocate` gives every cell
  min(size, 3) items (min(size, 1) if that does not fit), shares the rest in
  proportion to what each cell has left (rounded down, the remaining units
  to the largest fractional parts, ties in cell order), and each cell is
  drawn with `random.Random(f"42:audit:{stratum}:{family}")`, its items
  carrying the cell's inclusion probability (Hajek weights in every audit
  statistic). The P1 flips and the shams are never sampled. The sample
  summary records the scope (`audit_scope`: census or stratified sample, the
  capacity, the planned GPU-h and every cell's pool and sample), and the
  result discloses it; a candidate not drawn is listed as not audited.
  `submit_audit.sh` builds the sample, the items, the saved baselines and the
  packets in one CPU-only job; `sample.jsonl` (labels and verdicts) never
  reaches a rater.
- Spec author and raters: the blind specs that fix every label were written
  by Claude Opus 5.5 (Anthropic; `blind-spec-provenance.json`), and the
  Anthropic rater is a Claude model, so the open-weight rater is the
  independent one: each rater's answers are reported on their own
  (`per_rater`), and an item on which the raters do not agree is decided by
  Kevin or counted as a label error, never dropped.
- Decision per item (`raters.final_decision`): both raters accept → accept;
  both reject → reject; otherwise unresolved. Kevin's blind adjudication pool
  (`raters.adjudication_pool`, D34, widened by D38) holds three kinds of
  item: every real item (mutant or P1 flip) on which the raters split; every
  audited mutant of any label class, so of every stratum (`fn_equiv`,
  `fn_alt`, `alt_gate`, `fp_violation`, `fp_extra`), on which both raters
  agree against its label (a should-fail mutant both accept, a should-pass
  mutant both reject; on the D27 rerate 3 of 26 violation items were
  both-accept, which no rule sent to Kevin; D34 took only the K3 groups'
  items, so an alternative solution both rejected or an extra change both
  accepted was read as label-contradicted on the raters' consensus alone);
  and every gold sham on which the raters split. The pool is mixed in one seeded order
  (`random.Random("42:adjudication")`) and written as item ids only
  (`adjudication-pool.jsonl`); Kevin sees each item's packet, blind to the
  label, the verdict, the operator, whether it is a sham, why it is in the
  pool and the raters' answers. Kevin adjudicates the whole pool (D35). His
  answer (accept or reject) decides every pool item, concordant ones
  included; an answer for an item outside the pool is refused. The pool's composition by reason is disclosed as counts
  in the audit summary. Label error uses Hajek weights; an item still
  unresolved at analysis counts as a label error, and a concordant item
  Kevin has not adjudicated keeps the consensus (a label error). The
  estimate with unresolved items dropped is a sensitivity analysis only.
  Adjudication changes label error, never kappa.
- Gold defects (D34; with D35's census every audited task has a gold
  sham): labels are relative to the gold, but the audit asks
  whether the user would accept the result, so where the gold is itself
  flawed a correct rater rejects the task's equivalence mutants for the
  gold's flaw. A task whose gold sham is decided reject (both raters reject
  it, or they split and Kevin rejects it) is a gold-defect task: its
  equivalence items leave the equivalence K3 group (label error, the K3
  bound and its minimum audited size are computed without them) and are
  reported as gold defects with their decisions (`AuditSummary.gold_defects`).
  They stay in kappa, in S6 and in P2, which stays defined relative to the
  gold; the analysis also reports P2 without those tasks' equivalence
  mutants as a sensitivity (`analysis.headline` `gold_defects`). The
  violation items of a gold-defect task stay in their group. A split gold
  sham that Kevin has not adjudicated decides nothing. Every listed checker
  candidate carries its task's gold-defect flag (`gold_defect_task`). On the D27 rerate the
  fourth review traced 6 of the Claude rater's 9 label contradictions to the
  gold (e528b65e, bf4e9888, e4ef0baf), none of which had a gold sham.
- K3 and K4 groups: `should_pass_equiv` (enters P2 and P5) and
  `should_fail_violation` (enters P3 and P5), the label classes that enter the
  metrics without an audit gate. Alternative-solution and extra-change items
  decide their own entry into P2 and P4, so their acceptance and rejection
  rates are S6 results and never fire K3. Since D35, K3 and K4 are reported,
  not acted on, and under the census the two groups hold only the candidate
  events (`fn_equiv`, `fp_violation`), so their label error is the share of
  candidate events whose label the audit contradicts, not a class-wide rate.
  The operating characteristics of section 10 were simulated for the fifth
  draft's sampler.
- Adjudication workload (an estimate, before any confirm item exists): the
  pool above, over the D35 census. On the development audit with the relay
  turn excepted (the sensitivity of section 15), the items the census would
  hold split as follows: the 8 failing equivalence mutants both accepted
  (confirmed candidates), the 3 passed violations all split, 1 of the 28
  passed alternative solutions split, the P1 flip and the gold shams of the
  8 audited tasks were all both accepted; so 4 of the 50 census items (8%)
  would enter the pool, against 24 of the 142 items of the D34 audit. D38's
  wider pool adds nothing there: the 27 alternative solutions the raters
  agreed on were both accepted and the census held no extra change, so no
  item outside the K3 groups had a concordant contradiction (the D34 audit's
  28 alternative solutions and 6 extra changes had none either, so its pools
  of 24 and 113 items are unchanged under the wider rule). It can add
  confirm items where both raters reject an alternative solution or accept
  an extra change. Scaled four times (section 6), the confirm pool is about
  16 items (a range of
  about 10 to 40 allows for other tasks and checkers), roughly 0.5 to 3.5
  hours at an assumed 3 to 5 minutes per item; the fifth draft's sampler
  projected 43 to 134 items. Under the registered dev ingest, where the relay turn voided 110
  Claude answers, the same items would have split far more often; that
  failure mode is the one D35's relay rule removes. If a resume of the
  confirm rating does bring a different relay frame (D38), every
  relay-voided item is `unsure` in the registered summary and so enters the
  registered pool (a do-nothing sham excepted, which never enters it), which
  then holds the re-rate's pool too, so Kevin adjudicates those items on top
  of the normal pool (the development analogue: 113 items against 24).
  Unadjudicated pool items
  count as label errors in the reported K3 statistics, which no longer
  decide anything (section 10).
- Human spot check: a stratified sample (max(5, 10%) per D35 stratum plus 5
  shams; about 35 items at the expected census) for Kevin. Results state that
  the human check is pending until it is done.

## 10. Decision rules and kill criteria

Each criterion's sample sizes are checked in section 6; where the
pre-freeze evidence already makes a criterion unlikely to fire, it says so.
`analysis.headline` evaluates every rule below that has data. Since decision
D35 (D34's exit fired, section 15) what remains of them is: K1 (a stop) and
K2 (it drops a family from the reported tables) act as before; K3 is reported
beside the D34 exit and changes nothing, because P2-P5 are already out of the
confirmatory headline; K4 is reported and no longer stops the run; K6's
adequacy claim is retired and reported as blocked; K6b and K7 are descriptive
flags; K5, K8 and K9 are unchanged.

- **K1 Harness validity (first step after the freeze, before any mutant is
  scored).** On confirm tasks with a complete gold, raw gold must pass and raw
  do-nothing must fail in at least 90% of tasks under the lock-exact venv;
  otherwise stop, fix, and rerun under a new experiment id. (On the dev split
  this check passed 19/19 before the freeze.) K1 is a harness check, not a
  blind test: the scoping probe already scored the raw gold and do-nothing of
  every confirm task (`controls:gold+do_nothing(raw)`, section 12).
- **K2 VM fidelity gate.**
  - Sample: `campaign k2-sample` draws 80 scoring jobs (admitted mutants and
    null mutants) of the confirm mutation run from `build/scoring-jobs.jsonl`
    alone, in job 3 before scoring (no verdict exists or is read), seed 42:
    each task domain's jobs are shuffled with `random.Random(f"42:k2:{domain}")`
    and taken round-robin over the sorted domains, at most 4 per task, the
    cap relaxed only if the pool runs short. At least 3 domains are required;
    the confirm targets span `libreoffice_calc`, `libreoffice_impress`,
    `libreoffice_writer` and others. `k2-sample.summary.json` records the
    SHA-256 of the job list and of the sample.
  - Executor: the VM runtime of `stage0/q2-action-path` at the commit of its
    own frozen acceptance registration, running the injection plan of
    `harness/q2_mutation/vm_injection.py`; that commit and the VM image
    digest are recorded in the K2 report before any in-VM verdict is compared
    with an offline one. No executor commit is available at this draft (the
    branch is unfinished), so K2 is not a precondition of the freeze or of
    the confirm run.
  - Comparison: for each sampled job, the in-VM `DesktopEnv.evaluate()`
    verdict against the offline lock-exact verdict for the same
    `candidate_sha256`. A difference is explained only by one of: (1) the
    in-VM postconfig save took longer than 0.5 s, so the VM checker read the
    unsaved file; (2) the candidate's offline repeat scorings or in-VM
    repeated evaluations disagree; (3) the in-VM file hash after injection
    differs from the candidate's SHA-256 (infrastructure; the pair is
    excluded); (4) a VM infrastructure failure (boot, reset, injection or
    evaluate error or timeout; excluded). Any other difference is
    unexplained (`analysis.K2_EXPLANATIONS`).
  - Consequence: a checker family with an unexplained difference leaves the
    headline. P2-P5 are then recomputed without that family's mutants: the
    pooled rates, the family tables and P5's tasks (a task's checker family
    is its set of metric functions, so a dropped family takes its tasks out
    of P5), and the checker candidates of that family are reported apart
    (section 4). K6 no longer reads P5: D35 retired its adequacy claim, so
    the recomputed P5 is reported as exploratory and decides nothing. The
    dropped family's own tables
    and the pooled rates that include it are reported as exploratory
    (`analysis.headline` `k2_exploratory`). Fallback: if no K2 report exists
    when the result is written, the headline is labelled "offline harness,
    VM fidelity unverified"; a K2 report added later (on the same fixed
    sample) replaces the label and applies the consequence.
- **K3 Label validity (one rule).** K3 fires for a group when its weighted
  label error's one-sided 95% upper bound exceeds 10% or the group is
  insufficiently audited, and for both groups when Cohen's κ between the two
  model raters on the real (non-sham) items is below 0.6. The bound
  (`stats.label_error_bound`) is the larger of the task-cluster bootstrap's
  95th percentile and the exact Clopper-Pearson bound at the Kish effective
  sample size (rounded down) with the weighted error count rounded up, so it
  cannot collapse to zero when no error is observed (its exact part is 7.2%
  for 40 equally weighted items without an error and 11.3% with one). A group
  with fewer than 30 audited items, fewer than 8 tasks or a Kish effective
  size below 29 (the smallest size whose zero-error bound is under 10%) is
  insufficiently audited. The equivalence items of a gold-defect task (its
  gold sham decided reject; section 9, D34) are not in the equivalence
  group: its error, bound and minimum size are computed without them, and
  they are reported as gold defects. Consequence: when K3 fires for `should_pass_equiv`,
  P2 and P5 leave the headline; for `should_fail_violation`, P3 and P5; when
  κ is below 0.6, P2-P5. A metric that leaves the headline is reported as
  exploratory with the same tables; nothing is relabelled
  (`analysis.headline_exclusions`). κ is computed on the three answers
  (accept, reject, unsure) of the real items; Kevin's adjudication does not
  change it. Since D35 the consequence is reported only: `analysis.headline`
  lists the K3 reasons after "D34 (i): development kappa below 0.6", which
  has already removed P2-P5, and under the census the groups hold the
  candidate events only (section 9).
  - Operating characteristics (the design record of the fifth draft's
    sampler, which D35 replaced with the census of section 9;
    `integration/audit-design-v1/sim_audit_oc.py`,
    `audit-oc.json`: the then-registered sampler and summary on synthetic pools at
    the section 6 sizes, 200 replicates per scenario, independent label
    errors, bootstrap 1,000 resamples). With raters that answer the truth:
    the equivalence group is audited with about 115 items (Kish size about
    107) and never insufficiently; P(K3 fires for it) is 0.00, 0.015, 0.055,
    0.52 and 0.97 at true label error 0, 1, 2, 5 and 10%. The violation
    census at the expected 17 tasks audits about 89 items at weight 1 (Kish
    size at least 65 in every replicate): P(insufficient) 0, P(K3 fires)
    0.00, 0.00, 0.065, 0.55 and 0.95 at the same errors. At 13 violation
    tasks (68 items): 0.00, 0.04, 0.135, 0.67, 0.985; at 24 (124 items):
    0.00, 0.00, 0.015, 0.39, 0.96; at the 8-task floor (42 items):
    P(insufficient) 0.01 and P(K3 fires) 0.01, 0.30, 0.475, 0.82, 0.97. The
    third draft's sampler (violations shared with the other classes in the
    disagreement and agreement strata) audited 34 violation items (Kish
    size 30, as low as 16) and fired for the violation group with
    probability 0.42, 0.60, 0.72 and 0.91 at 0, 1, 2 and 5%. With raters that
    are each right 90% of the time, wrong 5% and unsure 5% (about 61 split
    items) and Kevin adjudicating every split item correctly, P(K3 fires)
    is unchanged within simulation error (equivalence 0.00 / 0.085 / 0.56 /
    0.985, violation 0.00 / 0.065 / 0.595 / 0.955 at 0, 2, 5, 10%), but κ
    falls below 0.6 in 0.11 to 0.27 of replicates, which takes P2-P5 out of
    the headline whatever the labels; without adjudication K4 fires in 0.99
    to 1.00 of replicates. The κ rule is therefore the binding constraint on
    rater quality: two raters must agree well beyond 90% each for the
    headline to survive it reliably.
  - Decision D27 keeps this rule as registered after the development smokes
    put κ at 0.22-0.46 with the Qwen3.5-9B rater: the open-weight rater was
    upgraded instead (section 9). If κ on the development rerate with the
    stronger rater is still below 0.6, the design returns to review; the rule
    is not relaxed to make the design pass. That consequence fired (κ 0.270
    with the isolated Claude rater and Qwen3.6-35B-A3B, thinking off; section
    15), and the design returned to review.
  - Decision D34 (after the fourth review) keeps the rule and its
    consequence and allows one rater retry: the same open-weight model with
    thinking on, one configuration, the development audit rebuilt and rated
    by both raters under the isolated protocol. If development κ with both
    raters is still below 0.6, no other rater is tried, and P2-P5 leave the
    confirmatory headline before the confirm campaign runs (the registered
    analysis still computes and reports them, labelled exploratory, as for
    any metric that leaves the headline); the campaign then reports P1 and
    the checker false-negative candidates descriptively.
  - That exit fired (section 15): development κ was 0.066 under the
    registered ingest and 0.575 with the relay turn excepted (a
    sensitivity), both below 0.6. The registered 0.066 stays as recorded; no
    other rater is tried. Decision D35 encodes the exit
    (`analysis.D34_DEV_EXIT`: P2-P5 always out of the confirmatory headline
    with the reason "D34 (i): development kappa below 0.6", whatever the
    confirm audit shows), defines the descriptive outputs (section 4: the
    checker false-negative and false-positive candidates) and turns the
    audit into a census of what is reported (section 9).
- **K4 Operator design (reported, D35).** Whether audited label error (the
  Hajek estimate after Kevin's adjudication, with unresolved items counted as
  errors) exceeds 10% in both K3 groups is reported (`analysis.headline`
  `K4`). Before D35 that stopped the run for a redesign under a new id; it no
  longer stops anything, because the census's K3 groups hold only the
  candidate events, whose label error describes the candidates, not the
  operator set.
- **K5 Normalization.** An operator whose edit the reachability stage erases
  in more than 50% of its mutants is reported only as a normalization finding.
- **K6 Adequacy (negative result): retired by D35.** P5 left the
  confirmatory headline under D34 (i), so no adequacy claim is made whatever
  P5 and P1 show; `analysis.headline` reports K6 as blocked (`K6.blocked_by`:
  the D35 retirement, the D34 exit and any other reason that applies; P5's
  tasks and escapes and the confirmed P1 flips are still reported). The rule
  as registered before D35: if P5 stays in the headline (K3 did not
  remove it through either K3 group or κ, the audit is not pending) and K4
  did not stop the run, at least 59 confirm tasks are evaluable for P5, P5
  has zero escapes (exact one-sided 95% upper bound below 5%; at 59-67 tasks
  one escape already exceeds it), and P1 has at most one confirmed flip,
  publish "adequate under this operator set" (`analysis.headline` records
  what blocks the claim in `K6.blocked_by`). With fewer than 59 evaluable
  tasks no adequacy claim is made, and the result says so. The pre-freeze
  evidence makes this rule very unlikely to fire, and the registration
  expects no adequacy claim: the headless scoping round trip flipped 7 of 63
  gold-passing confirm golds, the second review counted 4 raw-gold failures
  and 7 headless flips among the 67 confirm target golds, which caps P5 at
  about 56 tasks if they replicate, and there are 21 `compare_pptx_files`
  confirm target tasks, a checker that pairs shapes by their position in
  the shape list. (The third draft also cited `pptx.eq.zorder_nonoverlap`
  failing that checker on 2 of 5 dev pptx targets; the third review showed
  those swaps could change the rendered order, so they were label errors,
  not checker evidence. Section 15 reports the restricted operator.)
- **K6b Adequacy per family and error type (pre-specified, descriptive).**
  A checker family with at least 29 evaluable confirm tasks for one error
  type and no event of that type is reported as having no detected error of
  that type under this operator set, with an exact one-sided 95% upper bound
  below 10% (`analysis.headline` `K6b`, a descriptive flag; D35). Only `compare_table` (31 confirm target tasks) can reach 29
  tasks, and only for P2; it needs 29 of its 31 tasks evaluable.
- **K7 Unreliable family (descriptive, D35).** A family whose P2, P3 or P4
  rate reaches the family floor of section 6 and whose task-cluster two-sided
  95% interval has a lower limit above 5% is flagged as unreliable for that
  error type (`analysis.headline` `K7`); since P2-P4 are exploratory, the flag
  is descriptive. The family floor alone decides where K7 is computed. For P2, 80%
  power needs a true rate of about 19% in `compare_table` (31 tasks) and
  about 23% in `compare_pptx_files` (21 tasks) (section 6). For P3 only
  `compare_pptx_files` can reach the floor, and for P4 no family can.
- **K8 Prior art.** Before drafting, rerun `orx` and keyword search including
  citers of AgentRewardBench and ABC. If a mutation audit of desktop CUA
  checkers has appeared, pivot the note to the reachability, gold fixed-point
  and dependency-drift findings.
- **K9 Null-mutant coverage.** If more than 25% of confirm targets end
  `null_not_pass` (at least 18 of 68), the mutation rates are reported as
  covering only the remaining targets, and the excluded checker families are
  named.

## 11. Priors

- How Benchmarks Mis-Score Computer-Use Agents, arXiv 2607.28367
  (https://arxiv.org/abs/2607.28367, 2026-07-30): of 57 OSWorld zero-reward
  trajectories, 8 (14.0%) were evaluator false negatives; PASS verdicts were
  not audited.
- Measuring the Checker, arXiv 2609.22220 (https://arxiv.org/abs/2609.22220,
  2026-09-02): the KernelBench official check missed 1,248 of 7,384 witnessed
  mutants (16.9%).
- AgentRewardBench, arXiv 2504.08942 (https://arxiv.org/abs/2504.08942,
  2025-04): official rule-based evaluators reached precision 83.8 and recall
  55.9 against expert labels on web-agent trajectories (Table 1), a
  false-positive measurement for rule-based web checkers.
- ABC, Establishing Best Practices for Building Rigorous Agentic Benchmarks,
  arXiv 2507.02825 (https://arxiv.org/abs/2507.02825, 2025-07): OSWorld scores
  0 on O.g.2 because its state check verifies only the relevant states and
  does not check extra harmful actions (Table 13), a qualitative prior for P4.
- Claim boundary: no mutation-based per-checker FN/FP audit of desktop CUA
  state checkers was found through 2026-10-06 under `orx` keyword and
  embedding search plus the citation trails of 2607.28367 and 2609.22220.

## 12. Exploratory, not confirmatory

Since decision D35 the registration has no confirmatory part. Its
pre-specified descriptive outputs are P1 (a replication, below), the checker
false-negative and false-positive candidates with their audit decisions,
counts and task-equal shares (section 4, `analysis.checker_candidates`), and
S1-S7 (section 5); all are fixed in code before the freeze and reported
whatever they show. Exploratory as well:

- P2-P5 and their family tables, pooled rates, K3 statistics and the
  descriptive K6b and K7 flags: out of the confirmatory headline under D34
  (i) (`analysis.D34_DEV_EXIT`), computed and reported with the same tables.
- Dev-split results (harness validation, P1 on dev tasks, the end-to-end
  campaign of section 15, timing).
- Scoping-probe numbers (run split 34/38, F-CELL 12/30, headless round trip
  10/106): pre-reachability, Ubuntu `0ubuntu0.22.04.13` build, headless;
  disclosed, never pooled. The probe `controls:gold+do_nothing(raw)` scored
  the raw gold and do-nothing of all 120 confirm tasks, so K1 is not blind;
  it stays a harness check (section 10).
- Every (task, operator) cell touched by a scoping probe
  (`program/evidence/q2-mutation/harness/probe_touched.json`, 207 tasks) is
  kept out of P2-P5, the checker candidates and the audit, and reported
  separately (its candidate events are counted per family, unaudited). 63 of the 120 confirm tasks
  carry at least one touched cell. The mapping from probe ops to operator
  ids is fixed here (`campaign.PROBE_OPERATOR_MAP`; patterns are shell-style
  over operator names). It errs toward exploratory: an unrelated-edit probe
  (a typo in body text or a table, an edited cell) shows how the task's
  checker treats unrequested changes, so it touches every extra-change
  operator of the task, including deletions and formatting edits (changed
  after the review, which found `docx.extra.delete_unrelated_paragraph`
  confirmatory on a task whose checker the typo probe had already shown to
  ignore paragraphs); a revert probe (run on xlsx cells only) touches every
  violation operator.

  | Probe op | Operators whose cells it touches |
  |---|---|
  | `controls:gold+do_nothing(raw)` | none (controls) |
  | `lo_rt:gold_headless_save(ubuntu .13)` | none (P1 is handled separately) |
  | `equiv:E-META` | `*.eq.doc_property` |
  | `equiv:E-ZIP` | none (byte-level, no document_model operator) |
  | `runsplit:E-RUNSPLIT-TOUCHED`, `runsplit:E-RUNSPLIT-UNTOUCHED` | none (byte-level) |
  | `mutants:F-TYPO`, `mutants_v2:F-TYPO-BODY` | `*.extra.*`, `docx.viol.text_edit`, `pptx.viol.text_edit`, `xlsx.viol.value_perturb`, `text.viol.line_edit` |
  | `mutants_v2:F-TYPO-TABLE` | `*.extra.*`, `pptx.viol.table_cell_text` |
  | `mutants_v2:F-CELL` | `*.extra.*`, `xlsx.viol.value_perturb` |
  | `mutants:R-REVERT`, `mutants_v2:R-REVERT` | `*.viol.*` |

  Seven Impress golds were also split-run and saved headless by a review
  agent that did not record their task ids; they cannot be mapped and are
  disclosed.
- The two probe-informed operators (`docx.extra.edit_unrelated_table_cell`,
  `pptx.viol.table_cell_text`, catalog provenance `probe_informed`) are
  probe-touched on every task: `campaign.is_probe_touched` returns true for
  them (`PROBE_INFORMED_OPERATORS`, kept equal to the catalog by a test), so
  `build_report` keeps them out of P2-P5 and the audit pool, and every outcome
  row carries `probe_informed`.
- P1 as a whole: all 92 counted golds were saved by the headless round trip,
  so P1 is a pre-specified replication of that probe under the GUI-faithful
  save, with no confirmatory part (section 4). The golds without an office
  file are not exposed to the save and are listed, not counted.
- Operators added after the freeze.

## 13. Reported regardless of outcome

The checker false-negative and false-positive candidates (every one, with
its audit decision and reading, its operator, family and task, and its task's
gold-defect flag), their counts and task-equal shares pooled, per label, per
checker family and per operator, the audit-confirmed shares, and the
probe-touched candidate counts (D35); the audit's scope (census, or the
fallback sample with every cell's pool and sample) and the relay frames seen
in the ingest with their digests; P1-P5 (P2-P5 labelled exploratory, with the
D34 exit as the reason) and S1-S7 with intervals; per-task distributions; the status table of
section 7 per operator and per checker family; every quarantine, error and
infrastructure-failure count with reasons, including every job excluded at
`merge` and every task excluded as `unemulated`; each rater's answers and
disagreement with the labels, every call outcome (refusals, unparseable and
empty replies, unfinished thinking, timeouts, rejected requests, unrated items) and the number of
items Kevin adjudicated, with the adjudication pool's composition by
reason; the gold-defect tasks and items and P2 without them (D34); the
audit gate counts of P2 and P4
(`analysis.headline` `audit_gate`) and P4 with unresolved items counted as
events; the family-floor flags, K6b and K7 per family (descriptive), K4 as
reported and K6 as blocked; which metrics left the headline under the D34
exit, K2 or K3, and the K2 label; the excluded-task,
not-exposed-gold and no-target lists; the dependency-flip table; the
save-timing table; the fidelity-gate table; rater κ, sham accuracy and the
pending human check; the Anthropic rater's path (API or agent harness, D25)
and the model ids each path named; the packets' baseline status (saved,
save failed, none) and every cut the token budget made; GPU time and API
usage of the raters; the scoping-probe numbers labelled pre-reachability;
and the deviations below.

## 14. Deviations from the reviewed plan

- The VM runs Ubuntu's LibreOffice build `0ubuntu0.22.04.4`, not TDF's; the
  save stage and operator application run the VM's own userland instead of a
  TDF tarball.
- Split seed 42 (the program's seed rule and the shared interface), not
  20261006.
- Experiment id `q2-evaluator-mutation-v1` and this path, per the program's
  shared interface.
- Intent predicates on an independent stack are replaced by spec witnesses,
  operator purity checks on the saved file, and the D9 audit.
- Human raters are replaced by two model raters (D9). D9 named two API
  providers; D23 replaces the second (no OpenAI key, the Moonshot account is
  suspended) with a self-hosted open-weight model (Qwen3.5-9B), which is the
  independent rater because the spec author and the first rater are both
  Claude models. While no valid Anthropic API key exists, the Claude rater
  runs through the Claude Code agent harness (D25), where its sampling is
  not fixed; the API path stays registered for when a key exists. After the
  development smokes, D27 replaced the open-weight Qwen3.5-9B with
  Qwen3.6-35B-A3B (κ 0.22-0.46 against the registered 0.6) and confined the
  harness rater to one agent per item in its own directory with a transcript
  audit; the shared-directory development answers are exploratory.
- After the fourth review (D34), the open-weight rater thinks before it
  answers (`max_tokens` 8,192, the model card's thinking sampling, seeded but
  not greedy), every task with an audited K3 item gets a gold sham, a task
  whose gold sham is decided reject leaves its equivalence items out of the
  equivalence K3 group (gold defects), the K3 items both raters decide
  against the label join Kevin's adjudication pool, new-file end states get
  a text-level difference, save drift of at most 0.02 mm is counted and not
  listed, item ids take a secret per-audit salt, and the isolated rater's
  task prompt is a registered template that the transcript audit checks.
- After D34's exit fired (development κ 0.066 registered, 0.575 with the
  relay turn excepted), decision D35 turned the registration into a
  pre-specified descriptive protocol: P2-P5 are always out of the
  confirmatory headline, K6's adequacy claim is retired, K4 no longer stops
  the run and K6b and K7 are descriptive; the descriptive outputs are the
  checker candidates (section 4); the audit is a census of the candidate
  events, P2's gate, the shams and the P1 flips, with a registered stratified
  fallback over candidate type × checker family above the GPU cap's capacity,
  instead of the earlier stratified sample of all mutants; the transcript
  audit checks every user turn and every transcript of an item, allowing only
  the registered harness relay frame besides the task turn; and the packet
  puts the difference before the listings. After the sixth review the
  transcript audit also registers the transcript's entry and harness
  attachment types and voids any other.
- Decision D38 (after the sixth review) kept those choices and fixed the
  review's minor items before the freeze: the fallback's budget is the
  largest that fits, found by search; a registered collector takes every
  transcript of the rating run, and the ingest checks its manifest; an
  interrupted attempt answers only through a structured answer; relay frames
  must agree across the calls files of the summary and are recorded
  verbatim; the confirm rating is one workflow session, with one fresh,
  unresumed, answer-blind re-rate of items a differing relay frame voids,
  both results reported; and concordant contradictions of every candidate
  kind go to Kevin's pool, not only the K3 groups' items.
- Two operators were restricted after the third review (D27):
  `pptx.eq.zorder_nonoverlap` (a swap could move a shape above or below an
  overlapping shape stacked between the pair) and
  `pptx.viol.delete_bound_shape` (a shape hidden under the shapes above it
  could vanish without a visible change); after the fourth review (D34) the
  latter also skips shapes at least 50% off the slide. The catalog keeps its
  version and 64 operators; its digest changed.
- The audit packet compares an end state with the starting file saved
  through the same LibreOffice steps, not with the raw starting file
  (section 9).
- The mutation population is the 67 confirm tasks with a complete gold and a
  mutable file, not all 120: a mutant is an edit of a gold end state.
- Mutants carry one LibreOffice round trip more than a raw gold before the
  save stage (the UNO application save); the null mutant carries the same,
  and targets whose null mutant fails are excluded (S7, K9).
- The dependency-sensitivity arm is the scoping agent's venv, not the plan's
  leaderboard-era set (OSWorld's `requirements.txt` with setup.py
  constraints, resolved with `uv --exclude-newer 2025-07-28`). That set
  cannot be resolved as specified: `requirements.txt` at `b138d348` requires
  `daytona>=0.184.0` (first upload 2026-06-03) and `ui-tars>=0.4.2.2`
  (2025-12-11), both after the cutoff, so building it needs a choice of
  which requirements to drop. S1 is narrowed to the measured package
  differences (sections 2 and 5).
- Mutants labelled `ambiguous` (37 of 271 admitted on dev) are counted per
  witness rule and verdict but not audited, following the harness's sampler
  (`raters.stratum_of`); the operators' proposal sent them to the blind
  audit.
- Label error counts unresolved rater disagreements as errors unless Kevin
  adjudicates them, and K3 uses an exact bound with a minimum audited size
  (sections 9 and 10); the reviewed plan excluded unresolved items and used
  the bootstrap interval alone.
- K3 is computed on the two label classes that enter the metrics without an
  audit gate, and its consequence is that the affected metrics leave the
  headline; the earlier drafts grouped all should-pass and all should-fail
  labels and allowed relabelling by Kevin.
- P1 has no confirmatory part and counts only golds exposed to the save
  stage (section 4).
- Mutation rates P2-P5 are exploratory (D34 (i), D35); the probe exclusion
  leaves at most one family (`compare_pptx_files`, for P3) able to reach the
  family floor (section 6).

## 15. Integration validation on the development split (exploratory)

Six end-to-end campaigns ran on the 17 dev targets through the three
CPU-only Slurm jobs (no GPU, no network, `/dev/nvidia*` absent in every
receipt). `dev-mutants-v6` ran at commit
`2874bb6233c434bb69b6458f95cf4cc542b70c4a`, the third draft's pinned tree;
the fourth draft changed the audit, analysis and report code (section 9, the
S1/S5 rule of section 3), not the build, save or scoring stages, and v6 had
no S1 candidate, so its outcomes are the same under the pinned tree;
`dev-mutants-v4` ran at the second draft's pinned tree (`6ad6af6`) and
`dev-mutants-v5` at the intermediate `d9c5876`. The exports, with recipes
redacted, are committed under `program/evidence/q2-mutation/integration/` and checked by
`tests/test_q2_mutation_integration_evidence.py`.

| Run | Code | Recipes applied to | Planned | Admitted | Evaluable (lock) | Ambiguous | `null_not_pass` | Normalized |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `dev-mutants-v1` (Slurm 453-455) | `2cc8559` | base (null = base saved again) | 275 | 271 | 203 | 27 | 40 (2 targets) | 1 |
| `dev-mutants-v2` (Slurm 458-460) | `99992bc` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v3` (Slurm 461-463) | `17aac70` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v4` (Slurm 475-477) | `6ad6af6` | raw gold (null = base) | 275 | 271 | 215 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v5` (Slurm 603-605) | `d9c5876` | raw gold (null = base) | 275 | 270 | 214 | 27 | 28 (1 target) | 1 |
| `dev-mutants-v6` (Slurm 623-625), pinned code | `2874bb6` | raw gold (null = base) | 275 | 269 | 214 | 27 | 27 (1 target) | 1 |

- Build: 4 of 275 planned mutants failed build-time purity (two
  `docx.alt.para_direct_for_style` changed the resolved appearance; two
  `xlsx.viol.formula_ref_shift` left the value unchanged, i.e. equivalent
  mutants). Admitted labels: 111 equiv, 28 alternative, 68 violation,
  27 extra change, 37 ambiguous. The snapshot v2 fields (pptx backgrounds,
  outlines, text-body properties) admitted and rejected the same mutants.
- Save stage (each run): 288 jobs, 286 saves, all written, no dialog,
  slowest write 0.30 s (0.40 s in v4), no open or activation failure, no
  job excluded at merge (`save_failed` 0), no unemulated step, no scoring
  timeout, no nondeterministic scoring; the lock-exact and scoping venvs
  gave the same verdict on every candidate.
- Post-save purity held for 270 of 271 admitted mutants; one
  `pptx.viol.drop_char_format` colour removal did not survive the save (S3).
- Null mutants: in v1, two targets failed: af23762e (the known gold
  fixed-point flip) and 5cfb9197, whose gold after three LibreOffice round
  trips fails `compare_pptx_files` although it passes after one. Applying
  recipes to the raw gold (v2, the registered mode) recovered 5cfb9197;
  only af23762e (28 mutants) remains excluded.
- Evaluable: 215 mutants on 15 tasks, 95 of them in probe-touched cells under
  the review's probe map (83 under the earlier map). Outside those cells,
  candidate checker errors (unaudited): `pptx.eq.zorder_nonoverlap` fails
  `compare_pptx_files` on 5cfb9197 and e4ef0baf (6 equivalence mutants, FN);
  `docx.viol.drop_char_format` (a highlight removal) passes
  `compare_docx_files_and_ignore_new_lines` on 5bc63fb9 (3 violation
  mutants, FP_R). `docx.extra.delete_unrelated_paragraph` and
  `docx.extra.edit_unrelated_paragraph` pass `compare_docx_tables` on
  936321ce (6 extra-change mutants, FP_F); both cells are now probe-touched
  (the typo probe had shown the checker ignores paragraphs) and exploratory.
  Task escapes (FN or FP_R): 3 of 15 tasks.
- Reproducibility: v1-v4 planned every mutant at the same site with the same
  label; v2, v3 and v4 gave the same admission, status, event and verdict
  for all 275 mutants under both venvs (v4 after the review's changes to the
  save-failure rule, the snapshot and the probe map), and v1 differed from
  them only on 5cfb9197. Mutant ids differ between the runs because a
  LibreOffice save is not byte-deterministic (document timestamps) and each
  recipe carries the SHA-256 of its base file.
- Controls at the v4 code (`dev-controls-v7`, Slurm 478-480,
  `harness/dev-controls-v7-summary.json`): K1 19/19 under both venvs; P1 one
  flip in 19 golds (af23762e; Clopper-Pearson 95% 0.13%-26.0%); no gold
  save failed; 2 dev tasks without a gold excluded as `unemulated`
  (postconfig typed text).
- Reruns after the second review. `dev-mutants-v5` and `v6` reproduce v4 on
  every mutant matched by task, operator and recipe (275 of 275) in label,
  status, event and verdict under both venvs, except mutants the build did
  not admit: the UNO bridge to LibreOffice was disposed mid-application
  (`DisposedException` in `uno_apply`), so the `applied` check failed for 1
  mutant in v5 (e528b65e `docx.viol.delete_bound_paragraph`) and 2 in v6
  (936321ce `docx.extra.delete_unrelated_paragraph`, af23762e
  `pptx.eq.doc_property`). Section 7 counts these as `not_admitted`
  (`applied`), so about 0.5% of planned mutants per run can be lost to this
  infrastructure fault, a different set each run. The probe-touched set is
  the same (115 of 275 mutants; no dev probe-informed mutant lay outside a
  probe cell), and no dev venv disagreement needed S1. The K2 sample drawn
  in job 3 of v6 has 80 jobs over 4 domains and 17 tasks
  (`integration/k2-sample-dev-mutants-v6/`).
- Controls at the new code (`dev-controls-v8` at `d9c5876`, `dev-controls-v9`
  at the pinned `2874bb6`; `harness/dev-controls-v8-summary.json`,
  `-v9-summary.json`): K1 19/19 under both venvs; P1 one flip in 17 counted
  golds (af23762e), with the two non-office golds (20236825 txt, aa4b5023
  mp4) now listed as not exposed instead of counted. In v8 the do-nothing of
  9219480b passed under the lock-exact venv and failed under the scoping
  venv, each venv's two scorings agreeing; its checker
  (`check_python_file_by_test_suite`, a random tetromino test) passes about
  3 runs in 10 in both venvs (dev validation, `dev-validation-2026-10-07.json`),
  so this was not a dependency effect. That motivated the five-scoring S1
  confirmation (`dependency_flips.py`), which v9 and v6 ran with no
  candidate (the rescoring path is covered by unit tests only).

- Rebuild with the restricted pptx operators (D27; code `4eba530`, the
  pinned code tree). `dev-mutants-v7` (Slurm 681-683) lost two of its 17
  targets in the build (the UNO bridge was disposed during the initial-file
  save of af23762e and e4ef0baf, the fault of the reruns above, here before
  planning) and its scoring job was cancelled; `dev-mutants-v8` (Slurm
  688-690) built all 17: 275 planned, 271 admitted (111 equiv, 28
  alternative, 68 violation, 27 extra change, 37 ambiguous), 288 save jobs,
  286 saves written (slowest 0.30 s, no dialog, no failure), post-save
  purity 270 of 271 (the same `pptx.viol.drop_char_format` colour removal),
  no infrastructure failure or nondeterministic scoring, no venv
  disagreement and no S1 candidate; 215 evaluable under the lock-exact venv,
  27 ambiguous, 28 `null_not_pass` (af23762e). Every
  `pptx.eq.zorder_nonoverlap` site now passes the inert-swap rule: the
  5cfb9197 swap of review 3 (group 4 with 'Videotapes', over 'Newspapers')
  is no longer a site, and `pptx.viol.delete_bound_shape` no longer deletes
  4ed5abd0's sparkle group (slide 2, shape 13, 91% under the six shapes
  drawn above it) or its shape 5 (100% under the shapes above it), the two
  of v6's three 4ed5abd0 deletions that the rule now leaves out. The restricted swaps still fail `compare_pptx_files` on 8
  of 9 evaluable mutants in 3 of 4 evaluable pptx targets (5cfb9197 3/3,
  e4ef0baf 3/3, 4ed5abd0 2/3; candidate checker false negatives, unaudited:
  the checker pairs shapes by their position in the shape list), against 6
  of 9 before the restriction; task escapes 4 of 15. The synthetic
  revalidation (Slurm 684) planned, applied and admitted the same 131 / 131 /
  130 mutants as the operators' own validation (job 431); both operators
  admitted every synthetic mutant. The label-bearing export of v8 (release
  rows and outcomes) was held on the host until the isolated Claude answers
  on the audit drawn from it were ingested (section 9: no sample or label on
  the rating side before the ingest) and is now committed
  (`integration/dev-mutants-v8/`; its SHA-256 matched
  `integration/rater-rerate-dev-v3/held/SHA256SUMS`).
- Rater smoke on dev packets (`integration/rater-smoke-dev-v1/`, code
  `ba840b4`): `submit_audit.sh` (Slurm 559, CPU only, LO-VM image) drew the
  dev audit from `dev-mutants-v4` and `dev-controls-v7` (pool 120 evaluable
  mutants outside probe cells; 28 alternative, 9 disagreement and 83
  agreement items, 12 shams and the af23762e P1 flip: 133 items) and wrote
  133 blind packets with renders in one 410 MB shard. The cu129 overlay was
  built from a source capsule of `ba840b4` (Slurm 566, 45 s on one H100,
  image `sha256:6bc53f50ee8d556337c07a63df2f3d624fcbfe8becbbe0b95d25e1973eee74a1`);
  a CPU-only Slurm job ran the args doctor (573, pass). The open-weight rater
  ran as a lane job (Slurm 582, 6 min 37 s on one H100, 0.110 GPU-h of its
  0.2 cap; engine ready in 97 s): 133 calls, each sent once, every reply
  parsed by the first-token rule (no retry, no refusal, three replies cut at
  256 tokens after a valid first word), prompts up to 120,678 tokens (median
  46,294) against the 131,072-token window, median 14.7 s per call. Answers
  (exploratory, one rater): do-nothing shams 6 of 6 rejected; gold shams 4
  of 6 accepted; the P1 flip accepted; equivalence 35 accept / 25 reject;
  alternative 25 / 3; violation 8 / 18; extra change 0 / 6. Its rejections of
  equivalence mutants and of two gold shams cite the task result or changes
  of document defaults (a default font and language), not the mutation; the
  packet's difference was against the raw starting file. The draft read
  those changes as made by the save stage; the second smoke shows the
  language and font come from the gold file itself (below). If the
  Anthropic rater agreed with every label, κ on these answers would be 0.36
  and the κ rule (section 10) would take P2-P5 out of the headline whatever
  Kevin adjudicates; adjudication changes label error, not κ. The Anthropic
  rater did not run: the API key available to the agent is rejected (HTTP
  401) on the model lookup, before any packet is sent.
- Second rater smoke, saved-start packets (`integration/rater-smoke-dev-v2/`,
  code `4b9b45d`, the pinned code tree): `submit_audit.sh` (Slurm 644, CPU
  only, LO-VM image) drew the same 133 items from `dev-mutants-v4` and
  `dev-controls-v7` (the violation census took the 26 violation items, which
  the first smoke had in its disagreement and agreement strata; the item ids
  are the same), ran the GUI-faithful save stage on 12 baseline jobs (all
  saved, every office file written, no failure) and wrote 133 packets in one
  409 MB shard: 99 items compare with a saved starting file, 34 have end-state
  files with no starting file (new files) and none fell back to the raw
  file. The save alone changes a median of 189 snapshot leaves per starting
  file (at most 1,278); the packets' difference lines fell from 21,842 to
  7,705; no packet needed the token budget (largest estimate 126,830 of
  128,768; the estimate is at least 1.1 times the prompt the engine counted).
  The cu129 overlay was built from a capsule of `4b9b45d` (Slurm 646, about
  43 s on one H100, image
  `sha256:0fe3f4523b9c8fe59173e9f4d1e2ae531cc3bbd021cda768f22235078626316f`,
  provenance PASS), the args doctor passed (Slurm 647, CPU only), and the
  open-weight rater ran as a lane job (Slurm 650, 4 min 58 s on one H100,
  0.083 GPU-h; with the overlay 0.095 GPU-h of the 0.15 allowed; engine
  ready in 89 s). It rated 90 of the 133 items, each once, every reply
  parsed (two cut at 256 tokens after a valid first word), prompts up to
  110,448 tokens (median 48,478), median 13.0 s per call, and stopped at the
  lane's checkpoint signal, which the lane sends 180 s before the job's
  limit (`--signal=B:USR1@180`, 8-minute limit); the 43 items it did not
  reach are `unrated`, and no rerun was made, to stay inside the smoke's
  GPU allowance. A rater job's allocation must therefore cover the engine
  start, the items and those 180 s: about 28 items per minute after a
  two-minute start on this hardware. Answers (exploratory, one rater): gold
  shams 4 of 6 accepted (the same two rejected); do-nothing shams 2 of 2
  rated rejected; the P1 flip accepted; equivalence 24 accept / 14 reject;
  alternative 18 / 2; violation 4 / 15; extra change 0 / 4. On the 90 items
  rated in both smokes, the saved start changed two answers (two equivalence
  rejections became acceptances) and the rater disagreed with the label on
  22 of 90 items against 24 of 90 before; κ if the Anthropic rater agreed
  with every label rises from 0.44 to 0.48, still under 0.6. Its remaining
  rejections are task-level: where it rejects a task's gold sham it rejects
  that task's equivalence and alternative mutants too, because it judges the
  gold end state, not the mutation (01b269ae: the gold carries a zh-CN
  document language and a CJK default font that the saved starting file
  does not, an artifact of how the gold file was made, which the rater
  reads as an unrequested change; 5bc63fb9: it reads the instruction's
  filter as unmet by the gold), plus misreadings (b5062e3e: it judges an
  alphabetical author order wrong). The saved start removes the save stage's
  noise but does not bring this rater's agreement anywhere near what the κ
  rule needs: unless the Anthropic rater's dev answers show otherwise, the
  κ rule is expected to fire on confirm (open item, section 17).
- Dev packets exported for the agent-harness Claude rater (D25): `rater_runner
  export-harness` on the second smoke's shard wrote 133 item files with
  their page images and `index.json` (item ids only, in the Anthropic
  rater's seeded order) outside the repository; the export manifest (digests
  only) is `integration/rater-smoke-dev-v2/harness-export/`. One Claude
  agent rated all 133 exported items in task batches with state shared
  across items, while the second smoke's sample (labels) and open-weight
  answers sat in this repository on the same machine; its answers (12 of 12
  shams right; 3.3% of equivalence and 7.7% of violation items against the
  label) were ingested by the third review outside the repository. Under
  D27 they are exploratory and not blind; they are used here only to project
  κ (below), never as the registered Claude rating. Their only
  committed trace is this note.

- D27 development rerate with Qwen3.6-35B-A3B (`integration/rater-rerate-dev-v3/`).
  The image-input doctor (CPU) found the model served with image input by
  vLLM 0.31.0 (918 tokens for a 100-dpi letter page, under the registered
  947). `submit_audit.sh` (Slurm 700, CPU) drew the dev audit from
  `dev-mutants-v8` and `dev-controls-v9`: 120 evaluable mutants in the pool,
  133 items (28 alternative, 26 violation census, 8 disagreement, 58
  agreement, 12 shams, the af23762e P1 flip), one 409 MB shard, 99 items on
  a saved start and 34 with new files, none shortened (largest estimate
  126,830 of 128,768 tokens). Overlay built from a capsule of `84f23e0`
  (Slurm 686, 46 s, image `sha256:33fb48b7204f071264b6649e6023d251d9d7613d9d85137e45278a7431345a6d`),
  args and image-input doctor passed in it (Slurm 687, CPU), and the rater
  ran as one lane job (Slurm 702, limit 20 min, cap 0.334 GPU-h read into the
  GPU ledger): engine ready 133.5 s after the workload started (KV cache
  406,528 tokens), all 133 items rated in 210.5 s (37.9 items per minute,
  35,600 prompt tokens per second; prompts up to 110,505 tokens, median
  46,294), every reply `ok`, none cut, then a clean end (`reason=completed`,
  exit 0, engine stopped in 1.3 s, no container left). 6 min 56 s on one H100:
  0.116 GPU-h, 0.128 with the overlay, inside D27's 0.5. Answers
  (exploratory, one rater): shams 12 of 12 right; the P1 flip accepted;
  equivalence 57 accept / 3 reject; alternative 28 / 0; violation 19 accept
  / 7 reject; extra change 5 / 1. 68 of the 133 replies are the answer word
  alone (thinking is off and the answer line asks for one sentence). The
  stronger rater no longer rejects golds and equivalent edits, but it
  accepts most should-fail mutants (one-letter text edits, deleted bound
  paragraphs and shapes, dropped character formats). If the Claude rater
  agreed with every label, κ would be 0.27 (22% of real items split);
  against the earlier shared-directory Claude answers (one agent over all
  items; not blind, so exploratory) on the 109 real items matched by task,
  operator and site, κ is 0.34 with raw agreement 0.80 (the 9B rater: 0.54
  on the 73 of them it rated). Throughput at confirm scale (thinking off): a
  shard of about 156 items (480 MiB) needed about 1 min of container start,
  2.2 min of engine start and 4.1 min of rating; the 807-item maximum (6
  shards) needed about 1.1-1.2 GPU-h, over the 1.0 GPU-h cap of the fifth
  draft (re-registered under D34, section 9).
- Isolated Claude rater on the D27 rerate (`integration/rater-isolated-dev-v3/`):
  `rater_runner export-isolated` wrote the 133 rerate items into their own
  directories outside the repository; one Claude agent per item rated them
  (workflow run `wf_2301520e-159`, 1,711 Read calls all inside the agents'
  own directories, one StructuredOutput answer each, no other tool, every
  turn `claude-opus-5-5`; an independent strict audit found 0 voids), and
  `ingest-isolated` at `2dad9e1` recorded 133 `ok`, 0 `isolation_void`.
  With the held files released, `audit summarize` (both raters, 10,000
  draws) gave κ 0.270 on 121 real items (raw agreement 0.76), below 0.6:
  the D27 consequence fired and the design returned to review. Shams 12 of
  12 for each rater; the P1 flip accepted by both; 29 split items (26 of
  them Claude reject, Qwen accept); label error (unresolved as errors)
  0.133 for the equivalence group (K3 bound 0.255, 60 items, 15 tasks) and
  0.731 for the violation group (26 items, 5 tasks, insufficiently audited);
  K4 fired. The Claude rater contradicted 9 labels: by the fourth review's
  reading 6 judged the gold (e528b65e, bf4e9888, e4ef0baf) and 3 missed
  violations (two on bb83cab4's new-file script, one on 4ed5abd0). These
  findings motivated D34. The agent prompt of that run was not committed (it
  named a nonexistent `packet.md`, which every agent tried first) and its
  item ids used the public seed; both are fixed under D34.
- D34 development rerate (`integration/rater-rerate-dev-v4/`, code
  `34046e0`, all on the dev split, exploratory):
  - Operators: the synthetic revalidation (Slurm 717, LO-VM image) planned,
    applied and admitted the same 131 / 131 / 130 mutants (catalog
    `3a5ff949`). `dev-mutants-v9` (Slurm 714-716) built all 17 targets: 275
    planned, 271 admitted (the same label counts as v8), 288 save jobs, no
    save failure, post-save purity 270 of 271, no venv disagreement, no S1
    candidate; 215 evaluable under the lock-exact venv (120 outside probe
    cells), 27 ambiguous, 28 `null_not_pass` (af23762e); the restricted
    z-order swaps fail `compare_pptx_files` on 8 of 9 evaluable mutants as in
    v8; task escapes 4 of 15. On 4ed5abd0 the off-slide rule makes the
    shapes of the bound slide 2 that lie at least half off the slide
    ineligible (shape 0, 70.6% off, and the rotated shape 20, 77.6% off), so
    the operator's seeded choice of three sites changed (v8's shapes 9 and
    23 were replaced by 18 and 21).
    The fourth review's item afb440d9, however, deleted shape 19 ('Google
    Shape;119;p12'), a small shape wholly on the slide (0% off, 0% covered);
    the 78% figure matches shape 20. Shape 19 is still deleted in v9
    (`c68de1eb2a4f`), so that violation miss is not removed by the new rule;
    whether it is a visible violation is for the raters and Kevin.
  - Audit `dev-audit-v4` (Slurm 720, CPU, LO-VM image, from `dev-mutants-v9`
    and `dev-controls-v9`; salt SHA-256
    `1660a49d31a31deb77017852508c9e81ef588fe0d5b842c7e0277a626f803f51`):
    pool 120 (60 equivalence, 26 violation, 28 alternative, 6 extra
    change), 142 items: 28 alternative, 26 violation census, 8
    disagreement, 58 agreement, 21 shams (15 gold: one for each of the 15
    tasks with a K3 item, 9 of them added by D34's rule; 6 do-nothing) and
    the af23762e P1 flip. One 455 MB shard (`5598e755...`); 106 items on a
    saved start, 36 with new files; 51 new-file end-state entries, all with a
    text-level difference (median 123 lines, at most 602); 28 packets end
    with the save-drift count line (5,833 changes counted, not listed); 16
    packets shortened to the token budget, every cut in a starting-file
    listing (1,933 lines; largest estimate 143,292 before and 128,957 after
    against 129,024), none dropping a page.
  - Open-weight rater, thinking on (overlay Slurm 718, 44 s, image
    `sha256:d5fd5cd774046e3021934827b59e633324122c80300e9e9992db6d74f821a3c7`;
    args and image-input doctor Slurm 719, CPU, pass, 918 tokens per page;
    lane job Slurm 722, limit 28 min, cap 0.467 GPU-h in the GPU ledger):
    engine ready 115 s after the workload started (KV cache 409,539 tokens),
    all 142 items rated in 590 s (14.4 items per minute; median call 28 s,
    longest 134 s; 334.7 generated and 13,685 prompt tokens per second),
    then a clean end (`reason=completed`, exit 0, engine stopped in 1.2 s,
    no container left). 12 min 57 s on one H100: 0.216 GPU-h, 0.228 with the
    overlay, inside D34's 0.5. Replies: 141 `ok`, 1 `thinking_unfinished`
    (cut at 8,192 tokens, an equivalence item, `unsure`); generated tokens
    per reply median 1,042, 90th percentile 2,822; prompts up to 102,944
    tokens (median 57,748); no retry.
  - Answers (exploratory, one rater): shams 20 of 21 right (gold 14 of 15,
    do-nothing 6 of 6); the P1 flip accepted; equivalence 57 accept / 2
    reject / 1 unsure; alternative 27 / 1; violation 14 accept / 12 reject
    (thinking off: 19 / 7); extra change 0 / 6 (thinking off: 5 / 1). If the
    Claude rater agreed with every label, κ would be 0.578 (thinking off:
    0.27) with 18 of 121 real items split (14.9%), still below 0.6. Against
    the D27 isolated Claude answers on the 119 real items matched by task,
    operator and site (a projection only: those answers were given on the
    D27 packets, without the new-file text differences and the drift rule),
    κ is 0.486 with raw agreement 0.815 (thinking off on the same items:
    0.289 and 0.773); 16 of the 22 splits are Claude reject / Qwen accept.
    The registered κ condition of D34 was decided by the isolated Claude
    answers on these packets (below).
  - Throughput and the GPU cap: with thinking on, a job needs about 3.1
    minutes of start (container, model check, engine) and rates about 14.4
    items per minute; section 9 registers the confirm cap from these figures
    (3.0 GPU-h).
  - Isolated export: `rater_runner export-isolated` (code `34046e0`) wrote
    the 142 items into their own read-only directories outside the
    repository, one `packet.txt` and `pages/` each, no index; the manifest
    (`integration/rater-rerate-dev-v4/isolated-export/`, ids in the Anthropic
    rater's seeded order, digests and each item's rendered-prompt SHA-256)
    lies outside the isolation root. A scan of every exported packet found no
    label, verdict, operator, sham, witness or checker term; nine packets
    show the cell style name `Q2M Style ...` that
    `xlsx.alt.named_style_for_direct` creates, a mark of the harness but not
    of a label (disclosed; the operator is unchanged).
  - Held on the host until the isolated ingest: the audit's sample, items,
    baseline jobs and spot-check list, the open-weight call records and the
    label-bearing export of `dev-mutants-v9`; their SHA-256 were committed in
    `integration/rater-rerate-dev-v4/held/SHA256SUMS` before the ingest, and
    all 18 released files match them (`integration/rater-isolated-dev-v4/`,
    `integration/dev-mutants-v9/`).
- D34 isolated Claude rater and summary (`integration/rater-isolated-dev-v4/`,
  exploratory): one Claude agent per exported item, started with the
  registered template (workflow run `wf_65ce9899-24a`, 2026-10-08 03:10 to
  03:43 UTC). The session ended once while the raters ran and the workflow
  was resumed: 16 items have an interrupted agent and a completed rerun, and
  the resumed harness put its relay frame (section 9) before the task turn
  of each of the 110 agents it started. An independent strict transcript
  audit of all 158 transcripts found no void: 1,954 Read calls, every one
  inside the agent's own item directory, one `StructuredOutput` answer per
  completed agent naming its item, no other tool, only `claude-opus-5-5`, and
  in every agent the task turn byte-identical to the rendered template.
  - Registered ingest (`ingest-isolated` at `b29034e`, the D34 rule): 32
    `ok`, 110 `isolation_void`, every void for the one reason that the first
    user prompt was the relay frame, not the template. Registered summary
    (both raters, 10,000 draws): κ **0.066** on 121 real items (raw agreement
    0.18); this is the recorded development result and stays as recorded
    (gauntlet hard rule 3); it measures the voids rather than the raters.
  - Sensitivity, not registered (the same ingest with that byte-identical
    relay turn not counted as a prompt; 142 `ok`): κ 0.575 (raw agreement
    0.843); shams Claude 19 of 21, Qwen 20 of 21; one gold-defect task
    (e528b65e); equivalence label error 0.070 (K3 bound 0.179 on 57 items),
    violation 0.577 (26 items on 5 tasks, too few for the bound); 20 of 121
    real items unresolved, 16 of the splits Claude reject / Qwen accept;
    adjudication pool 24. By the fifth review's reproduction, in one task
    (5bc63fb9) Claude rejects and Qwen accepts all 9 violation items, and
    without that task κ is 0.734.
  - The audit salt was revealed after the ingest (its SHA-256 matches the
    committed `1660a49d...`, and every item id recomputes from it).
  - D34 (i) fired under both readings: no other rater is tried, and P2-P5
    left the confirmatory headline. Decision D35 made the registration a
    descriptive protocol (status note). The relay rule of section 9, the
    census of section 9 and the difference-first packet postdate these
    results; the development audit is not re-ingested or rerun under them,
    and the registered 0.066 is not replaced.
  - Diligence (not a void condition): 40 of the 142 completed agents were
    not shown every line of `packet.txt` (the lowest saw 56%); in every
    packet all difference lines were shown and only listing lines went
    unseen, which motivated the difference-first order (section 9).

These numbers size the design; they are never pooled with a confirm result.

## 16. Release

Released: sanitized tasks, specs, the operator catalog, redacted recipes
(`campaign export`: free-text leaves of 32 characters or more, or with
non-ASCII characters, in a recipe become `{redacted_sha256, chars}`, long
quoted spans in witness arguments likewise, purity details dropped), the
recipe SHA-256, verdict rows, outcome rows and summaries. Each recipe names
the SHA-256 of its base file (`input_sha256`); base files, mutant files and
full recipes stay in the host run root, and planning is deterministic given
the base, so a holder of the base files can regenerate every recipe and
check its mutant id. The mutant file itself is the recipe's steps applied to
the file each release row names in `applied_input_sha256` (`applied_to`:
under `--apply-to gold`, the raw gold, not the base), so it is reproducible
from the gold plus the recipe. A LibreOffice save is not byte-deterministic,
so a fresh base save yields new ids with the same sites and labels (section
15). The audit's released evidence is the sample summary, each rater's call
records (answer, status, outcome, request, body and response SHA-256, model
id, usage) and receipt, the agent-harness export manifest (digests only),
the decisions, the audit summary, Kevin's adjudication pool (item ids only)
and, after the isolated ingest, the audit's salt (its SHA-256 is committed
before); the analysis result, which lists every checker candidate (mutant
id, task, operator, checker family, label, verdict and audit decision; D35);
and every transcript's SHA-256 with the relay frames' digests and text
(D38), the transcript collection manifest and the relay re-rate list. Not
released: mutant documents, base
files, full recipes, gold or initial files, saved baselines, audit packets,
exported harness files and renders, and raw rater responses and reasons
(they may quote document text).

## 17. Freeze checklist

- [x] Every value the earlier draft left open is filled (pins block,
      catalog, specs, probe mapping, dev intra-task correlation, image).
- [x] Dev-split harness validation (gold, do-nothing, gold fixed point,
      determinism, timing) recorded as exploratory evidence.
- [x] Dev-split end-to-end campaign recorded; intra-task correlation measured;
      MDE table updated.
- [x] Spec set and operator catalog hashes recorded; blind-author provenance
      checked (`integration/blind-spec-provenance.json`).
- [x] First adversarial review answered: save failures excluded, control
      path guarded, packet and K3 bound rebuilt, K6/P1 and P3/P4 power
      restated, probe map widened, input pins added; dev rerun at the new
      code tree (`dev-mutants-v4`, `dev-controls-v7`) and pins refreshed.
- [x] Second adversarial review (2026-10-07): 55/100, not ready to freeze;
      its seven blocking defects were fixed in the third draft, the cheap
      rule-code inconsistencies too (S1, S4, S6, the P4 denominator, the
      audit pool, the family sizes, K7's power, the `infra_failed` causes,
      the rerun policy).
- [x] Third review (re-audit of the third draft, 2026-10-07): 62/100, not
      ready to freeze; its two blocking and eight other findings are
      answered in this draft (see the status note). Lowest review score so
      far: 55.
- [x] Rater runner in the pinned tree; open-weight rater smokes on dev
      packets inside their caps (0.2 and 0.15 GPU-h, section 15), the second
      on packets with the saved-start baseline.
- [x] Dev packets exported for the agent-harness Claude rater (D25;
      section 15); its shared-directory answers were rated and reviewed
      (third review of the fourth draft, 56/100), and are exploratory and
      not blind.
- [x] Third review's blocking defects answered under D27 (this draft): the
      open-weight rater upgraded to Qwen3.6-35B-A3B and the whole dev audit
      rerated with every item rated inside 0.5 GPU-h; the isolated per-item
      Claude protocol registered and implemented (`export-isolated` /
      `ingest-isolated`); the two pptx operators restricted, revalidated
      and the dev campaign rebuilt; the minor items fixed (K6 gating, the
      answers wrapper, duplicate and anonymous call records, the GPU ledger,
      the clean exit, stale text).
- [x] Isolated Claude rater on the rebuilt dev audit (D27): one agent per
      exported item, no void, `ingest-isolated`, `audit summarize` with both
      raters: κ 0.270 on 121 real items, below 0.6, so the D27 consequence
      fired and the design returned to review
      (`integration/rater-isolated-dev-v3/`).
- [x] Fourth adversarial review (57/100, not ready to freeze); scores so far
      55, 62, 56 and 57; the lowest is 55. Its three blocking defects and
      minor items are answered under D34 in this draft (status note).
- [x] D34 development rerate with the open-weight rater, thinking on, one
      configuration, inside 0.5 GPU-h, every item rated (section 15).
- [x] D34 isolated Claude rater on the same dev audit (`dev-audit-v4`): one
      agent per exported item started with the registered prompt template,
      transcripts kept, `ingest-isolated`, the audit salt revealed, `audit
      summarize` with both raters: κ 0.066 under the registered ingest (110
      items voided by the resumed harness's relay turn) and 0.575 with that
      turn excepted (a sensitivity), both below 0.6, so D34 (i) fired: no
      other rater is tried and P2-P5 left the confirmatory headline
      (section 15, `integration/rater-isolated-dev-v4/`).
- [x] Fifth adversarial review (of the sixth draft, 64/100, not ready to
      freeze): its three blocking defects (the exit not encoded, the
      descriptive outputs undefined, the transcript audit's first-prompt
      rule) and its minor items are answered under D35 in this draft (status
      note).
- [x] Sixth adversarial review (of the seventh draft, 80/100, not ready to
      freeze): its one blocking defect (harness attachment entries, the
      `queued_command` channel for a message sent to a running agent among
      them, were outside the transcript audit) is answered in this eighth
      draft (status note, section 9). Its minor items were recorded there
      for a later pass.
- [x] Decision D38 (2026-10-08): the eighth draft's choices accepted as
      implemented (the census audit with its seeded stratified fallback,
      gold shams for every audited task, the relay frame registered under
      D35's constraints, the difference-first packet order, the registered
      transcript entry and attachment types), and the sixth review's minor
      items fixed before the freeze in this ninth draft (status note items
      6-12), each with tests: the fallback's budget is the largest that fits
      (section 9); a registered transcript collector replaces copying by
      hand, and the ingest checks its manifest (section 9); `audit
      summarize` refuses calls files with different relay frames, and the
      receipt records the relayed text verbatim (section 9); concordant
      contradictions of every candidate kind go to Kevin's pool (sections 4
      and 9); an interrupted attempt answers only through a structured
      answer (section 9); the confirm rating runs as one workflow session,
      with one answer-blind re-rate of relay-voided items in a fresh,
      unresumed run and both results reported (section 9); section 10's K2
      consequence no longer has K6 reading P5. Rerun over copies of the 158
      development transcripts (scratch only, nothing ingested), the
      collector maps all 158 to their items, its layout equals the
      hand-copied one file for file, and the audit finds no void and 142
      answering transcripts (`integration/d38-fixes/`).
- [x] A narrow re-check of this ninth draft (D38's fixes and their tests,
      the collector rerun over the 158 development transcripts, the pin
      refresh and the freeze lint): 90/100, ready to freeze, no blocking
      defect (review log below). Its minor items are fixed in this draft
      (status note): the re-rate list recomputed from its calls file, tests
      for the list's "only void reason" rule and the journal's started-twice
      refusal, the collector's staging directory, the workload sentence
      below and in section 9, and the harness README's pool row.
- [ ] Kevin's remaining items (D38). His own work: adjudicating the whole
      pool (about 16 items, 10 to 40, roughly 0.5 to 3.5 hours at 3 to 5
      minutes per item; with D38 it also holds every candidate kind's
      concordant contradictions; if a resume brings a different relay
      frame, every relay-voided item enters the registered pool, since it
      is `unsure` there, so he adjudicates those on top of the normal pool,
      113 items against 24 in the development analogue) and the human spot
      check of D9 (about 35
      items at the expected census, whose result stays pending until done;
      recommendation: the registered stratified sample, max(5, 10%) per D35
      stratum plus 5 shams, with every item on which the raters split or a
      rater answered `unsure` added). The outward actions, which stay his:
      the disclosures to Letta and xlang-ai (D2: upstream defect reports and
      other outward disclosures stay unsent while this runs), the licence
      requests, any purge of git history, rotating the exposed Moonshot key,
      and a valid Anthropic API key if the API path should replace the
      agent harness. The sign-offs carried over from earlier drafts: the
      D23/D25/D27 rater lineup, including the agent-harness path with
      unfixed sampling, the isolation protocol and its transcript audit,
      treating the earlier dev Claude answers as non-blind exploratory
      evidence, and sending public OSWorld task files and their renders to
      the Anthropic model (section 9); P1 as a replication that uses
      reserve-split golds; release of the specs, which quote short passages
      of file-cache documents; and the D34 rules as implemented: the
      thinking-on rater configuration, the gold-defect rule, the
      concordant-contradiction pool, the new-file text difference, the
      save-drift rule (which also hides `pptx.eq.subvisible_nudge`'s edit in
      the count line), the off-slide rule (it does not reach the fourth
      review's afb440d9, and two 4ed5abd0 deletions stay both-accept), the
      salted ids, the injected harness context and the 3.0 GPU-h rater cap.
      D35 (the descriptive protocol) and D38 (the eighth draft's choices and
      these fixes) are decided.
- [ ] Merge main immediately before the freeze (main has moved during each
      review), then freeze.

Review log (every adversarial review of this registration; the lowest
score is the one recorded):

| Review | Draft read | Score | Ready to freeze | Answered in |
|---|---|---:|---|---|
| First adversarial review (2026-10-07) | first | not scored | no | second draft |
| Second adversarial review (2026-10-07) | second | 55 | no | third draft |
| Third review, re-audit (2026-10-07) | third | 62 | no | fourth draft |
| Third review of the fourth draft (2026-10-07) | fourth | 56 | no | fifth draft (D27) |
| Fourth adversarial review (2026-10-07) | fifth | 57 | no | sixth draft (D34) |
| Fifth adversarial review (2026-10-08) | sixth | 64 | no | seventh draft (D35) |
| Sixth adversarial review (2026-10-08) | seventh | 80 | no | eighth draft (blocker); ninth draft (minor items, D38) |
| Narrow re-check of the ninth draft (2026-10-08) | ninth | 90 | yes | ninth draft (minor items fixed) |

Scores so far: 55, 62, 56, 57, 64, 80, 90; the lowest is 55.

## Appendix A. Operator catalog `q2-mut-operators-v1` (64 operators)

Label class is nominal; the label of each mutant comes from its witness rule.
Probe-informed operators are marked with a dagger (†).

| Family | Equivalence (E) | Alternative solution (A) | Violation (R) | Extra change (F) |
|---|---|---|---|---|
| xlsx | `xlsx.eq.doc_property`, `xlsx.eq.view_zoom`, `xlsx.eq.view_selection`, `xlsx.eq.active_sheet` | `xlsx.alt.literal_for_formula`, `xlsx.alt.reference_for_literal`, `xlsx.alt.sum_range_expand`, `xlsx.alt.plus_chain_to_sum`, `xlsx.alt.average_to_sum_count`, `xlsx.alt.absolute_refs`, `xlsx.alt.concat_to_ampersand`, `xlsx.alt.named_style_for_direct` | `xlsx.viol.value_perturb`, `xlsx.viol.formula_ref_shift`, `xlsx.viol.clear_bound_cell`, `xlsx.viol.drop_char_format`, `xlsx.viol.number_format_change` | `xlsx.extra.edit_unrelated_value`, `xlsx.extra.clear_unrelated_row`, `xlsx.extra.rename_unrelated_sheet`, `xlsx.extra.delete_unrelated_sheet`, `xlsx.extra.format_unrelated_cell` |
| docx | `docx.eq.doc_property`, `docx.eq.view_zoom` | `docx.alt.char_style_for_direct`, `docx.alt.para_direct_for_style`, `docx.alt.highlight_as_shading`, `docx.alt.case_via_format` | `docx.viol.text_edit`, `docx.viol.drop_char_format`, `docx.viol.para_align_change`, `docx.viol.line_spacing_change`, `docx.viol.delete_bound_paragraph` | `docx.extra.edit_unrelated_paragraph`, `docx.extra.delete_unrelated_paragraph`, `docx.extra.edit_unrelated_table_cell` †, `docx.extra.format_unrelated_run` |
| pptx | `pptx.eq.doc_property`, `pptx.eq.subvisible_nudge`, `pptx.eq.zorder_nonoverlap` | `pptx.alt.textbox_for_placeholder`, `pptx.alt.case_via_format` | `pptx.viol.text_edit`, `pptx.viol.table_cell_text` †, `pptx.viol.drop_char_format`, `pptx.viol.move_shape`, `pptx.viol.delete_bound_shape` | `pptx.extra.edit_unrelated_text`, `pptx.extra.delete_unrelated_slide`, `pptx.extra.add_textbox`, `pptx.extra.edit_notes` |
| text | `text.eq.trailing_newline` | none | `text.viol.line_edit` | `text.extra.unrelated_line_edit`, `text.extra.unrelated_line_delete` |
| config | `config.eq.trailing_newline`, `config.eq.json_reformat`, `config.eq.json_key_reorder`, `config.eq.ini_kv_spacing` | `config.alt.json_number_repr` | `config.viol.value_change`, `config.viol.key_delete` | `config.extra.unrelated_value_change`, `config.extra.unrelated_key_delete` |

Witness rules (`harness/q2_mutation/operators/__init__.py`): W-E-SILENT /
W-E-ALLOWED give `should_pass_equiv`, W-E-CONFLICT gives `ambiguous`;
W-A-SILENT / W-A-ALLOWED give `should_pass_alt_solution`, W-A-PINNED gives
`should_fail_violation`, W-A-MENTIONED, W-A-REPRESENTATION and W-A-STRUCTURE
give `ambiguous` unless the spec frees the aspect; W-R-PINNED / W-R-TEXT give
`should_fail_violation`, W-R-WEAK-BINDING and W-R-UNPINNED give `ambiguous`;
W-F-UNREQUESTED gives `should_fail_extra_change`, W-F-COSMETIC gives
`ambiguous`, W-F-ALLOWED gives `should_pass_equiv` for a cosmetic change and
`ambiguous` for a content change, and any rule ending in FLAGGED (an
`[AMBIGUOUS]` spec entry) gives `ambiguous`.
Planning, binding, sites and admission follow
`program/evidence/q2-mutation/operators/prereg-operators-section.md`, which
this registration adopts with three changes: recipes are applied to the raw
gold (section 3), ambiguous mutants are counted but not audited (section 9),
and two pptx operators carry stricter site rules (D27 after the third
review, D34 after the fourth):

- `pptx.eq.zorder_nonoverlap` swaps shapes `a < b` on a slide only when every
  shape from `a` to `b` has a frame (an offset and an extent; a placeholder
  that inherits its layout's position could be anywhere), a rotated frame
  counting as the bounding box of its rotation, and neither `a` nor `b` comes
  within 2 mm (72,000 EMU) of the other or of any shape stacked between them.
  The swap moves `a` above and `b` below every shape between them, so these
  are all the pairs whose stacking it changes; outlines and shadows that
  reach past a frame are covered by the 2 mm clearance
  (`pptx.zorder_pair_is_inert`).
- `pptx.viol.delete_bound_shape` leaves out a bound shape whose frame lies at
  least 90% under the union of the frames of the shapes stacked above it on
  its slide (`pptx.covered_share`): such a shape may be hidden, so deleting it
  may not change what the slide shows. Since D34 it also leaves out a bound
  shape whose frame (the bounding box of its rotation) lies at least 50%
  outside the slide (`pptx.offslide_share`, slide size from the
  presentation; a shape without a frame, or a deck without a slide size,
  is not left out by this rule): such a shape is mostly not shown.
