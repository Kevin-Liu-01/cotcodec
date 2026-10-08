# Q2 blind requirement specs

One YAML spec per sanitized OSWorld-Verified task (`<task_id>.yaml`, 205 files),
written by `blind-model-author-v1` from the sanitized instruction and the initial
documents only. Each spec follows the binding `RequirementSpec` schema in
`harness/q2_mutation/schema.py` (copied verbatim from `stage0/q2-mut-harness`).

Check them with:

```
python program/evidence/q2-mutation/specs/check_specs.py
# specs_valid=205 invalid=0 missing=0 tasks=205
```

## Blind protocol followed

The author did not read:

- any checker or evaluator code, anything under `desktop_env/evaluators`, or
  OSWorld's GitHub repository;
- any OSWorld task field named evaluator, expected, result, postconfig, metric or
  options (the sanitized JSON files carry none of them; `schema.py` checks this
  recursively);
- any research plan, review or probe result. That rules out `AGENTS.md`,
  `memory.json`, `HANDOFF.md`, `README.md`, `wiki/*` (including SOUL/USER/HEARTBEAT),
  `docs/`, `experiments/`, `tests/` and `legacy/`, and every `program/` path except
  `program/evidence/q2-mutation/sanitized-tasks/` and this directory. The project
  `CLAUDE.md` asks every session to read `memory.json` and the wiki heartbeat
  files at start-up. The author skipped them on purpose, because they describe the
  program's current direction;
- any harness or operator code other than `schema.py`. The harness branch was not
  merged. Only two paths were checked out from it:
  `git checkout stage0/q2-mut-harness -- program/evidence/q2-mutation/sanitized-tasks harness/q2_mutation/schema.py`;
- files in `/private/tmp/claude-501` or any other scratchpad, or other agents'
  run directories.

### Exactly what was read

Repository (this worktree):

1. `harness/q2_mutation/schema.py`
2. `program/evidence/q2-mutation/sanitized-tasks/*.json` (all 205)
3. `pyproject.toml`, only the `[tool.ruff]` section (via grep), to lint `check_specs.py`
4. `uv.lock`, a grep for `pyyaml` only
5. Git metadata: `git worktree list`, `git branch -a`, and
   `git ls-tree -r --name-only stage0/q2-mut-harness`. The ls-tree output was filtered
   by grep to the sanitized-tasks paths and `schema.py`, so no other file names were
   printed.
6. The author's own spec files.

Initial documents:

- All 296 initial files listed in the sanitized tasks were downloaded from their
  `huggingface.co` URLs. Every sha256 matched the sanitized record.
- For every task, the author opened the initial files listed in that task's
  sanitized JSON, with the exceptions below. "Opened" means parsing the file with
  python-docx, python-pptx, openpyxl, pypdf, pdftotext, ffprobe, PIL or a small
  XCF parser; reading text files; or viewing thumbnails.
- These initial files were **not opened**:
  - `53ad5833`: `vscodeEvalExtension.zip` (deliberately skipped: the name suggests
    evaluation tooling), plus `project/main.py`, `project/README.md` and
    `project/.vscode/settings.json`.
  - `415ef462`: `.projects.tar.xz`. Only the member names were listed with
    `tar -t`; they include `codes/quick_evaluate.py`. No member was extracted or
    read. Receipts other than `aws-invoice-2311.pdf` were not opened; their names
    were listed.
  - `70745df8` and `c6bf789c`: the downloaded project zips.
  - `a097acff`: `Secrets-of-Monetizing-Video.pptx`.
  - `d38192b0`: `aws-bill.pdf` and `.aws-bill-mail-body.html`.
  - `386dbd0e`: `lecture.pdf` and the mp3.
  - `3a93cae4`: everything except `Course Timetable.xlsx` (the student docx files,
    the grammar PDFs and the teaching plan are distractors).
  - `1f18aa87`: the grammar-rule PDFs and `Public Lecture Teaching Plan.docx`.
  - `7e287123`: everything except `grf19.pdf` to `grf23.pdf`.
  - `881deb30`: everything except `ecs15.pdf` to `ecs23.pdf` and
    `supported_rate.xlsx`.
- Thunderbird profiles: the author read `prefs.js` (only lines on
  mail/account/identity/theme keys, with password/token/oauth lines excluded),
  `xulstore.json`, `compatibility.ini`, the mbox headers of INBOX, Bills, Trash,
  Unsent Messages and daily, `msgFilterRules.dat` and `abook.sqlite`. The author
  did not read `logins.json`, `key4.db` or `encrypted-openpgp-passphrase.txt`. Of
  the 15 profile tarballs, 12 are byte-identical (the base profile). The other three
  (`415ef462`, `c867c42d`, `d9b7c649`) were inspected separately.
- Media was inspected with ffprobe only, except `aa4b5023`. For that task, frames
  at 20 s and 40 s were extracted to determine the flip axis.

Rendering environment:

- One slide (`5c1a6c3d`, slide 1) was rendered to decide which shape is the
  "title". The render used LibreOffice 7.3.7 (Ubuntu 22.04 `libreoffice-impress`)
  in a fresh `ubuntu:22.04` container built on `fal-h100-01`
  (image `q2-specs-blind-lo:v1`, scratch `~/cotcodec-runs/stage0/q2-mut-specs/`,
  run with `--network=none`).
- The same container supplied LibreOffice's own palette file
  `share/palette/standard.soc`. That file fixes the named colors used below.
- No other image on that host was used. The pre-existing `cotcodec-q2-*` images
  were not run or inspected. The author saw only the output of `docker images` and
  the top-level directory names of `~/cotcodec-runs`.

Local scratch was `~/cotcodec-runs/stage0/q2-mut-specs/` on the author's machine. It
holds a uv venv with python-docx, python-pptx, openpyxl, pypdf, pdfplumber and
PIL; the downloaded files; and thumbnails.

### Disclosure

The author is a language model and may have been exposed to the public OSWorld
repository, including evaluator configs, during pretraining. Nothing from that
repository was consulted in this session. Every expected value in an observable was
recomputed from the initial documents (computed values are stated explicitly).
Prior exposure still cannot be ruled out, so an independent second blind author is
the stronger control.

## Spec conventions

- `R0` / statements prefixed `(implicit)`: requirements the instruction does not
  state but a careful human would assume. Examples: the edited document is saved in
  place in its original format, and unrelated content is preserved. When the
  instruction explicitly says "don't touch irrelevant regions", the requirement is
  not marked implicit.
- `[AMBIGUOUS]`: where the instruction admits more than one reasonable end state, the
  spec says so instead of guessing. The marker appears at the start of a requirement
  statement (often `req_id` ending `-AMB`) or of an `allowed_variations` entry, names
  the competing readings, and asks the scorer to record which one a candidate
  follows. 115 of 205 specs carry at least one ambiguity marker.
- `observable` tells a human how to test the requirement on the end-state file
  without any checker. Most observables give concrete expected values computed from
  the initial documents: cell values, run colors, positions in cm, page ranges,
  e-mail rows and so on.
- `allowed_variations` lists aspects the instruction does not constrain, such as
  formulas vs constants, styling, placement, or the tool used to get there.
- Named LibreOffice colors come from `standard.soc` in LibreOffice 7.3.7:
  Yellow `#FFFF00`, Red `#FF0000`, Orange `#FF8000`, Green `#00A933`,
  Blue `#2A6099`, Purple `#800080`, Dark Red 2 `#C9211E`.
- `check_kind` choices: `file_exists` (170 requirements), `cell_value` (87),
  `text_run` (79), `other` (69), `image_property` (50), `config_value` (47),
  `slide_object` (42), `paragraph_format` (22), `cell_format` (19),
  `table_cell` (13). `other` covers code behaviour, PDFs, archives and mail stores.

## Coverage

| domain | tasks | requirements | specs with [AMBIGUOUS] |
|---|---:|---:|---:|
| libreoffice_calc | 46 | 175 | 21 |
| libreoffice_impress | 46 | 160 | 27 |
| multi_apps | 40 | 108 | 23 |
| libreoffice_writer | 22 | 69 | 14 |
| gimp | 15 | 28 | 12 |
| vs_code | 13 | 20 | 8 |
| thunderbird | 12 | 23 | 5 |
| vlc | 11 | 15 | 5 |
| **total** | **205** | **598** | **115** |

## Known limits

- Many GIMP, VLC, Thunderbird and VS Code tasks change application configuration or
  open-window state, not a document. Their observables name the config key (gimprc,
  vlcrc, prefs.js, xulstore.json, settings.json, keybindings.json) or the UI state;
  the key names come from the author's general knowledge of those applications, not
  from any checker.
- Tasks whose target depends on state the sanitized task does not show (cursor
  position, current playback time, which page is "this one") are marked
  `[AMBIGUOUS]`, with the most likely state assumed: `66399b0d`, `6ada715d`,
  `ecc2413d`, `fba2c100`.
- Where the instruction names no output path, the spec assumes the input's
  directory and marks the assumption.
