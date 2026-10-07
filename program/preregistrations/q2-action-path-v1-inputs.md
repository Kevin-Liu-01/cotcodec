# q2-action-path-v1-inputs: inputs addendum to q2-action-path-v1

**Status: DRAFT. Not frozen.** The program owner freezes it after
`q2-action-path-v1` with
`uv run python scripts/preregister.py freeze q2-action-path-v1-inputs program/preregistrations/q2-action-path-v1-inputs.md`.
Validity control C2 may be scored only after this ledger entry exists.

- Experiment id: `q2-action-path-v1-inputs`, an addendum to `q2-action-path-v1`
  (`program/preregistrations/q2-action-path-v1.md`, section 2.2). It changes no
  rule of that file; it pins the components that file says are frozen here.
- Drafted: 2026-10-07, on branch `stage0/q2-action-path`.
- What it freezes: the guest probe (event log, text buffer, marker block,
  entry delimiters), the marker decoder, the entry guard (including the
  pointer park and the side-effect restorations), the canary driver (app
  preparation, launch, wait, read-back, close), the two detection controls'
  translators with the unmodified upstream parsers they read, the code that
  judges a trial, and the VM lane that runs every scored campaign.

## 1. Frozen files

Every file below is pinned by its SHA-256, so freezing this file freezes
them; the ledger row adds the repository's git head
(`git_head_at_freeze`). A test (`tests/test_q2_prereg_inputs.py`) recomputes
every digest from the repository, so no listed file can change without
changing this file. Every scored campaign runs from a source tree exported
at a commit where these digests hold; its receipt records the tree digest.

Frozen with this file (SHA-256 of the committed bytes):

| File | SHA-256 |
|---|---|
| `harness/q2/vm/guest/probe.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest/guard.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest/canary.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest/facts.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest/sentinel.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest/tap_selftest.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/marker.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/canary_run.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/suite.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/desktop.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/validation.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/guest_http.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/hmp.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/runner.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/driver.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/vm/manifest.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/verdict.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/order.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/controls.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/keynames.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/upstream/gym_anything_bf965cde0.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/upstream/vendor.py` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `harness/q2/action_path/upstream/PROVENANCE.json` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `infra/slurm/host-single-node/vm-campaign.sbatch` | `0000000000000000000000000000000000000000000000000000000000000000` |
| `scripts/submit_vm_campaign.py` | `0000000000000000000000000000000000000000000000000000000000000000` |

The main preregistration already pins the catalog, the R-dev reference, the
L0-raw translator and prediction, the XRecord tap and the runner image. C2's
cells are the `L0-fixed` layer of `suite_cells.json`, a deterministic function
of the frozen `catalog.yaml` (`corpus.l0_cells`; a test checks the committed
file equals it), so freezing the catalog fixes them.

## 2. The components (normative details are in each file's docstring)

- **Probe** (`guest/probe.py`). A fullscreen X window (1920x1080 at (0, 0))
  that logs every key, button and motion event it receives with the keycode
  or button, state, root position, server time and, for keys, the keysym at
  index 0 and the keysym selected under the core protocol's rules. Its text
  buffer follows the catalog's buffer rules: for a KeyPress with no Control,
  Mod1 or Mod4 bit, Return and KP_Enter append a newline, Tab a tab,
  BackSpace deletes the last code point, and a keysym that encodes a printable
  code point (Latin-1, Unicode keysyms, the keypad's ASCII keysyms) appends
  it. It re-reads the keyboard mapping on every MappingNotify. Its marker
  block (56 cells of 16 px at (512, 32)) encodes 8 sync bits, the 24-bit
  sequence number, the CRC-16/CCITT-FALSE of the buffer's UTF-8 bytes and a
  CRC-8 check, clear of every point the catalog uses.
- **Entry delimiters.** The probe opens and closes each entry's window by
  sending a core `ChangeKeyboardMapping` request for one reserved spare
  keycode (rows `[0x0100F0B0 or 0x0100F0E0, 0x01100000 + seq]`) and processing
  its own event queue up to the MappingNotify that request causes. The X
  server orders requests and device events in one sequence, so both the
  probe's log and the XRecord tap's stream (which records the same request)
  split at exactly the same point, with no timestamps involved. The reserved
  keycode is never empty while the probe runs, so the executor never uses it.
- **Marker decoder** (`marker.py`). Decompresses only the first 48 PNG rows,
  reverses the row filters, samples each cell on a 3 x 3 grid and decodes;
  disagreeing samples (for example under the cursor image the guest server
  pastes) make the marker unreadable, never wrong.
- **Entry guard** (`guest/guard.py`). Before and after every entry it checks
  (a) no pressed key or button, (b) the LED mask equals the session baseline,
  (c) the probe is mapped, focused and covers the screen, (d) no screencast
  file grows over 0.4 s; before the entry it parks the pointer at the
  catalog's `guard.park_pointer` (1234, 777). After an entry with a declared
  side effect it first restores: screencast, the chord again while a file
  grows (at most three times) and then Escape; hot corner (also used for
  R13's Super key, which opens the overview), Escape; for screencast, closed,
  shown or switched windows and the hot corner, the probe is re-activated;
  lock state, nothing. A violation charges the entry; the guard then releases
  every pressed key and button through XTest, toggles the LEDs back, presses
  Escape and re-activates the probe, and the runner relaunches the probe (with
  the same reserved keycode) if it is gone.
- **Canary driver** (`guest/canary.py`, `canary_run.py`). Per trial: write the
  fixture and a fresh profile (Writer: a new LibreOffice user installation
  whose `registrymodifications.xcu` turns AutoCorrect while typing, word
  completion and automatic spell checking off; Chrome: a new user-data
  directory, the `canary.yaml` flags and the textarea page with the fixture as
  a JSON literal; VS Code: a new user-data directory with the `canary.yaml`
  settings, extensions disabled, `--password-store=basic`; Terminal: a new
  window running `cat > out.txt`), launch through `/setup/launch`, wait for
  the app's window to be active (and its text object in the accessibility
  tree for Writer and Chrome), run the actions and finish keys through
  L0-fixed, read back as `canary.yaml` says, and terminate every process of
  the trial.
- **Detection-control translators** (`controls.py`, `keynames.py`). H-OSW-up
  runs OSWorld `bfd62bdc`'s `parse_response` unmodified
  (`upstream/osworld_bfd62bdc.py`) and maps each PyAutoGUI string call for
  call to IR, reproducing PyAutoGUI 0.9.54's key-name resolution (names it
  does not know are dropped, as upstream drops them), `scroll(n)` as `-n`
  notches at the current pointer, `WAIT` as a zero wait and `DONE` as
  terminate(success). H-GA-buggy runs gym-anything `bf965cde0`'s
  `_parse_response` unmodified (`upstream/gym_anything_bf965cde0.py`) and maps
  its action dicts with gym-anything's step rule, key names and scroll
  convention. Both clamp coordinates with `ir.clamp_point` and fix nothing
  else. The vendored parsers are byte-for-byte line ranges of the pinned
  upstream files (`upstream/vendor.py`, digests in `PROVENANCE.json`).
- **Judging** (`verdict.py`, `suite.py`, `desktop.py`). `desktop.py`
  reproduces OSWorld `b138d348`'s `DesktopEnv.step` and controller calls
  (retries, timeouts, the PyAutoGUI prefix) and records the infrastructure
  failure types of section 6.1. `suite.py` runs a session (tap, probe, pre and
  post guards, actions, marker) and assembles each trial's observation;
  `verdict.py` applies sections 4.3 and 5. The lane (`runner.py`,
  `driver.py`, `manifest.py`, the batch script and the submitter) runs every
  campaign as a CPU-only Slurm job (decisions D12, D13); `manifest.py` admits
  an acceptance or scored-control campaign only when the ledger freezes the
  main preregistration and the addenda it needs, and refuses seeds 43 and 44
  for every other purpose.

## 3. Validation before this freeze (infrastructure only)

No system under test ran in these jobs.

- Job 482 (`inputs-validation-v1`) stopped in the driver before any
  container started (the workload declared `sessions`, the driver read
  `cycles`); fixed, rerun as v2.
- Job 484 (`inputs-validation-v2`, one cold boot, COMPLETED 0:0): QEMU
  monitor input into the probe. All 35 R-dev entries, typed text through HMP
  (`hI <<\n\t`, including a Shift chord, the 102nd key and a BackSpace),
  buttons 1-3 and one wheel notch each way at the park point, and a no-input
  trial, each twice: 76 of 76 trials PASS on the probe's channel (raw-only
  entries on the tap's), the tap's projection equal to the R-dev reference in
  70 of 70 key trials, the marker read back in every app-observable trial,
  every guard clean before and after (side-effect restorations included),
  and the tap's mapping check clean (153 delimiter requests, each explained).
  Then every canary fixture opened with no input and read back unchanged: 16
  of 16 (Writer and Chrome through the accessibility tree, VS Code and the
  terminal from the file).

## 4. Build order

The main preregistration's draft said this addendum would be frozen before
any L0-fixed code was written. In fact the components above and the L0-fixed
executor were written in one development pass on 2026-10-07, before any
freeze (commit `7ec94d2` and later; the git history shows each file's
changes). What protects the controls is unchanged: C2 is scored once, after
this freeze, with the L0-raw translator and its prediction frozen in the main
preregistration; C1 and C3 are scored once after the executor addendum, with
the control translators frozen here. Every change to a file listed above
after an L0-fixed development run is listed in section 5, so a reader can
see whether the probe, guard or judge changed in response to executor
results.

## 5. Changes after L0-fixed development runs

None yet.
