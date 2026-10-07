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
| `harness/q2/vm/guest/probe.py` | `ba5c0f1d364c80d5f8190f3c357b915cd504d754891285c3772ba959a804efeb` |
| `harness/q2/vm/guest/guard.py` | `0ef7e2e6d5025e4937b0611a9c33e7ff8776428aad04338015ea287917f7ca62` |
| `harness/q2/vm/guest/canary.py` | `32742019db56b4f09905c50c71159c2ef3fe024a044d07f4bffb31cd41fcea1e` |
| `harness/q2/vm/guest/facts.py` | `4a071a39d4586a58b62419796a57b678568bdbc3bfd77ec6d50e841414dcd255` |
| `harness/q2/vm/guest/sentinel.py` | `98f46a7faafc58e9c65466b19ae3547288fc8829378ad7aa169b09a17161b18b` |
| `harness/q2/vm/guest/tap_selftest.py` | `7e051c0bcb45ba81c2b1fb855a9dc70115957fafa3ec7f333c8b3be5ab3bf835` |
| `harness/q2/vm/marker.py` | `b786b347fc5573425f14090bd67621294ac5c84671bf67f47e663d693ab17fb9` |
| `harness/q2/vm/canary_run.py` | `295bdd0916869adf79015bc6da6cba4aff2a0ab9f0dab089e4ed3a3565abb119` |
| `harness/q2/vm/suite.py` | `fdf71cce160194d3ca8dfbe0cd5e3d5bc414d2864084cab330d4ad0343ebe11e` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/validation.py` | `2ab5508e5a42269d447312e481b58c9f491d815d73e4977ba9c55d235231116f` |
| `harness/q2/vm/guest_http.py` | `13e34f874c89b0b32f7f82ffae658682d2608bc9a0614a569742459d6b796ceb` |
| `harness/q2/vm/hmp.py` | `34b10c2661c6cf40039ca172a704fb5613d0a805e60223acc729f040caf4776a` |
| `harness/q2/vm/runner.py` | `14e7ae59e3abe9afd9d4cbd0464811b82cba8710cea034c9fed8c622e07f7c9c` |
| `harness/q2/vm/driver.py` | `5afb36ec8a31f749d0275c5909f2c22a858c05f48d6c289ff1560ed0b0bf7a4e` |
| `harness/q2/vm/manifest.py` | `6271124d660136db1c5921a05628f2e4d96831c2c7cc9568ab349908cda40538` |
| `harness/q2/action_path/verdict.py` | `6cbcd5a3f32ab873bc1807c2d7d4bab8f16819d56b925918c9c696a3d6ea7d43` |
| `harness/q2/action_path/order.py` | `346d47374aec1b088ebe5eee6cec33f634819228a32b0a6b71ca2cb9159778cb` |
| `harness/q2/action_path/controls.py` | `d96e7b2acdecfef134c08c22f23113c8d78fae9d8a35d0e5ad826a2f0af9cc72` |
| `harness/q2/action_path/keynames.py` | `ed7afec8fd66e1f1ba1a08e2df6eccd834a24f9f22e6bd4a79604153e3816b72` |
| `harness/q2/action_path/upstream/osworld_bfd62bdc.py` | `9e21622823994721407dc04f606b58c8cbd8848e780e4657e8ee13cb363c77ab` |
| `harness/q2/action_path/upstream/gym_anything_bf965cde0.py` | `f5fb13d2ab6eb024be48f28a439ecb3147308f126217054d4587649f9b1b818f` |
| `harness/q2/action_path/upstream/vendor.py` | `afae1b5d89cf47709727281eab01b1104e6f6b5eabf1c6960e0947c3b23d236f` |
| `harness/q2/action_path/build_keysyms.py` | `1a977f6c4e8981f3f0ce2040f2ecae28c87f8cf8c730977c9480db900ff91cbf` |
| `harness/q2/action_path/upstream/PROVENANCE.json` | `5bef93df835c560b1f8dc6e8cfe7d6c207ba7fbe2e26c861541878563062744d` |
| `infra/slurm/host-single-node/vm-campaign.sbatch` | `3d86820d176e3a9f0699814a19f62154cde00f88da1777a33c804e884288ac8a` |
| `scripts/submit_vm_campaign.py` | `f08aafc8bc693cd6eb6850ff972a3401f3bddc99f3c14e03187b4d313fcc5917` |

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
  the same reserved keycode) if it is gone. Its `warmup` mode runs once per
  session (suite and canary), before the first trial and outside every entry
  window: one XTest press and release of a keycode with no keysym, then D-Bus
  round trips until GNOME Shell answers twice within 50 ms. The session's
  first XTest key event moves the X server's master keyboard to the XTest
  device, which re-sends the keymap and recomputes the modifier state; without
  the warm-up that happens inside the first entry that presses a key (main
  preregistration, design decision 31).
- **Canary driver** (`guest/canary.py`, `canary_run.py`). Per trial: write the
  fixture and a fresh profile (Writer: a new LibreOffice user installation
  whose `registrymodifications.xcu` turns AutoCorrect while typing, word
  completion and automatic spell checking off; Chrome: a new user-data
  directory, the `canary.yaml` flags and the textarea page with the fixture as
  a JSON literal; VS Code: a new user-data directory with the `canary.yaml`
  settings, extensions disabled, `--password-store=basic`; Terminal: a new
  window running `cat > out.txt`), launch through `/setup/launch`, wait for
  the app's window to be active and for the app's own sign of readiness
  (Writer: its text object in the accessibility tree; Chrome: the page's
  mirrored title; VS Code: the text editor's status-bar items), then for
  Writer, Chrome and VS Code until the trial's processes use under 10% of one
  CPU in two consecutive 0.5 s windows (at most 20 s), run the actions and
  finish keys through L0-fixed, read back as `canary.yaml` says, and
  terminate every process of the trial.
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
  failure types of main section 6.1: an `/execute` whose first attempt is not
  HTTP 200 within 30 s, a screenshot or (in the accessibility setting) a tree
  that `DesktopEnv`'s three attempts do not deliver; a retry that delivers is
  reported (`observation_retries`), not a failure. `suite.py` adds
  `guest_server_restart` when the guard's reports before and after an entry
  name different guest-server processes. `suite.py` runs a session
  (tap, probe, the guard's warm-up, `DesktopEnv.reset`'s observation, pre and
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

The first L0-fixed development run (job 486) ran at commit `29b056e`. Every
later change to a file listed in section 1 (from `git log 29b056e..`):

| Commit | File | Change and reason |
|---|---|---|
| `e026893` | `guest/probe.py` | `begin` returns only once the screen shows the entry's marker (read back from the root window), and `end` reports the marker the screen shows. Run 486: `no_action_control`'s screenshot, taken right after `begin`, still showed the previous entry's marker; the probe's own drawing reaches the screen one compositor frame later (72 ms median). No verdict rule changed. |
| `7c1bb02` | `canary_run.py`, `runner.py` | Development-only measurement of the canary's pointer targets (accessibility extents and screenshots, `guest/canary_targets.py`); acceptance runs never take this path. |
| `1ce92a6` | `guest/canary.py`, `canary_run.py` | Read-backs retry for 5 s; VS Code's read-back waits until the saved file changed and is stable; screenshots after the pointer composites (development only). Run 501: VS Code's file was read before its save landed, and Chrome's accessibility node was missing right after typing. |
| `44a30dd` | `guest/canary.py` | Chrome is read back from the window title the page mirrors its value into (with `canary.yaml`'s page and read-back changed in the main preregistration); VS Code is ready when its status bar shows the text editor's items (and `canary.yaml` turns its first-run walkthrough off). Runs 501 and 506: Chrome's accessibility text stayed at the fixture after edits the screen showed (`keep Y keep` on screen, `keep word keep` read back), and the walkthrough took the keyboard from the file. |
| `fe92765` | `guest/canary.py`, `canary_run.py`, `guest/probe.py`, `manifest.py` | Chrome's mirrored title is percent-decoded (run 515: `document.title` collapses runs of spaces, so the JSON form lost them) and every window title is listed when the mirror is missing; a Chrome screenshot after each trial in measurement mode (development only); the probe records when it last handled input and last drew (diagnostic); a development manifest may name a mutant (informative mutant runs; C3 is still scored only after the executor freeze). |
| `b603347` | `desktop.py`, `suite.py`, `verdict.py`, `driver.py`, `runner.py`, `manifest.py` | The observation-failure rule now says what main section 6.1 says (a screenshot or tree that `DesktopEnv`'s retries do not deliver; a delivered retry is reported); the code had counted every retried `/screenshot` or `/accessibility` call. Run 537: the boot's first `/accessibility` call answered HTTP 500 and its retry 200, 1 of 2,415 accessibility calls in runs 484-541. Each suite session takes `DesktopEnv.reset`'s observation before its first trial, as Stage 1 does. `manifest.py`: ladder rungs repeat the seed-43 order until every VM is busy and the rung has 20 cold boots (main design decision 29), only the ladder and A4 run concurrent VMs, and suite development may run concurrent VMs at seed 42. |
| `dba0580` | `suite.py` | A trial's compact tap window keeps each mapping notify's kind and keycode range (diagnostic, never judged). Run 549 could not otherwise tell which notifies surrounded its `chord_super_d` failures. |
| `a6623ae` | `guest/guard.py`, `suite.py`, `runner.py` | The session warm-up described in section 2. Runs 549 (8 VMs) and 574 (one VM, the same 14 sessions): `chord_super_d` failed in the two sessions whose first key event was its Super_L press, the `d` press arriving with state 0, and in every session of runs 546 and 549 the keymap was re-sent right after the session's first key. |
| `59697b3` | `guest/canary.py` | Writer, Chrome and VS Code trials also wait until the trial's processes are idle before the first action (section 2). Run 613, on a loaded host: three VS Code trials lost their first keys or clicks (`type_symbols_shifted` read back empty, `type_emoji` lost its first word and emoji, `triple_click_line` became a click inside the word) although the editor's status-bar items were showing; VS Code was still loading. |

| `d0c4cec` | `guest/guard.py`, `suite.py` | Every guard report names the guest server process that ran it, and an entry whose two reports name different processes gets the infrastructure failure `guest_server_restart` (main section 6.1). Run 622: the server crashed inside `/accessibility`; its systemd unit stopped every process it had launched, the probe and the tap included, and restarted it 5 s later, so the rest of that session was charged with missing tap windows. |

The probe change makes the no-action entry's screenshot start from a settled
screen, the canary changes make the read-back report what the app holds, and
the warm-up and the reset observation move once-per-boot effects out of the
first entry. One change touches how a trial is judged: the observation-failure
rule of `b603347`, which aligns the code with main section 6.1 (a recovered
retry had been counted as a failure, which 6.1 did not say); the retries stay
in every report.

## 6. A decision before the freeze: guest-server restarts and A4

Main section 16, item 9: in development the OSWorld guest server crashed once
in 7,969 `/accessibility` calls (its tree walk runs on a thread pool), and its
systemd unit then stopped every process the server had launched. A crash is an
infrastructure failure (main section 6.1), and A4 needs zero failures over
36,550 accessibility calls (36,016 steps and 534 reset observations in its
screenshot-plus-accessibility sessions): about 4.6 expected crashes at that
rate, so A4 would pass with probability about 0.01. The
registration keeps the strict rule; the options the owner can take before the
freeze, each with its cost:

1. Keep the rule. A4 will then very likely fail on a defect of the observation
   service rather than of the action path, and Stage 1 stays blocked until the
   runtime changes.
2. Patch the guest server so the walk runs on one thread (or catches the
   crash) and pin the patched `main.py`. The accessibility tree's content does
   not change, but the runtime no longer matches upstream OSWorld exactly.
3. Run the screenshot-plus-accessibility setting only where Stage 1 uses it,
   or drop it from A4 and bound the observation service separately (for
   example, at most 5 x 10^-4 restarts per accessibility call from a
   dedicated campaign), with Stage 1 counting restarts per episode.
4. Make the probe and the tap survive a restart (start them in their own
   systemd scope) so a restart costs one trial instead of a session; this
   improves the accounting under any of the options above but changes no
   verdict on its own.
