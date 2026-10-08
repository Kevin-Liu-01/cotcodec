# q2-action-path-v1-inputs: inputs addendum to q2-action-path-v1

**Status: DRAFT. Not frozen.** The program owner freezes it after
`q2-action-path-v1` with
`uv run python scripts/preregister.py freeze q2-action-path-v1-inputs program/preregistrations/q2-action-path-v1-inputs.md`.
Validity control C2 may be scored only after this ledger entry exists.

- Experiment id: `q2-action-path-v1-inputs`, an addendum to `q2-action-path-v1`
  (`program/preregistrations/q2-action-path-v1.md`, section 2.2). It changes no
  rule of that file; it pins the components that file says are frozen here.
- Drafted: 2026-10-07, on branch `stage0/q2-action-path`; decisions D30 and
  D33 applied before the freeze on branch `stage0/q2-action-path-d30`
  (sections 5 and 6).
- What it freezes: the guest probe (event log, text buffer, marker block,
  entry delimiters), the marker decoder, the entry guard (including the
  pointer park and the side-effect restorations), the canary driver (app
  preparation, launch, wait, read-back, close), the two detection controls'
  translators with the unmodified upstream parsers they read, the code that
  judges a trial (including the systemd scopes the probe and the tap run in,
  decision D30), the acceptance analysis (`acceptance.py`, which decides C2
  and so must be fixed before C2 runs), and the VM lane that runs every
  scored campaign, with the package files it imports.

## 1. Frozen files

Every file below is pinned by its SHA-256, so freezing this file freezes
them; the ledger row adds the repository's git head
(`git_head_at_freeze`). A test (`tests/test_q2_prereg_inputs.py`) recomputes
every digest from the repository, so no listed file can change without
changing this file. Every scored campaign runs from a source tree exported
at a commit where these digests hold; `manifest.py` refuses it otherwise, at
submission and again inside the job (main preregistration, design decision
35), and its receipt records the tree digest.

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
| `harness/q2/vm/suite.py` | `6d0831210e5efb41a94399c73fdd7b80b65a4208cef9721993882336b69cc924` |
| `harness/q2/vm/desktop.py` | `67030d6b5d79753e2db65b33bc12af2b5faaee2eacbaa5e49b4eb2de0a31c188` |
| `harness/q2/vm/validation.py` | `2ab5508e5a42269d447312e481b58c9f491d815d73e4977ba9c55d235231116f` |
| `harness/q2/vm/guest_http.py` | `13e34f874c89b0b32f7f82ffae658682d2608bc9a0614a569742459d6b796ceb` |
| `harness/q2/vm/hmp.py` | `34b10c2661c6cf40039ca172a704fb5613d0a805e60223acc729f040caf4776a` |
| `harness/q2/vm/runner.py` | `0b20f70d9681c7772223d0ecb4d449743a9be3260a1054a99bc9849241a82c9f` |
| `harness/q2/vm/driver.py` | `7a4b1d685954fa42915259025bca6a66d3b5ba5070949ff46ccdba1512ae24b2` |
| `harness/q2/vm/manifest.py` | `c927267716affd1d5b3fc72b94411b4111ce6e45c02507c2a11b5f19f2f391a6` |
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
| `harness/q2/action_path/acceptance.py` | `0ef925cfc8c5a13b18e35d2ddfc8b3634e1edb09117dd5681e12be7ec08cf665` |
| `harness/__init__.py` | `17dac2704be26050e324aa36aba6d2c855abbd592e4d72f750b9b6e9c4399fec` |
| `harness/q2/__init__.py` | `0932bda132c1dab03f40e460874a6827c4609424815e65eedcfefd3cd0b943a1` |
| `harness/q2/action_path/__init__.py` | `8ce4d0afdd20f6b09dbb4e9d40d24acead2fc1992fccebd1ddf3891ec402613f` |
| `harness/q2/action_path/upstream/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `harness/q2/vm/__init__.py` | `43fce1e08200acef9b9b82c914eba0713c0d60716bd2be0feaaade042dee3b19` |
| `harness/q2/vm/guest/__init__.py` | `99215662111076fd8ca080805ee2b36156cdec720470d16b612954c50f83362f` |

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
  name different guest-server processes, or, when the guard before the entry
  could not run, when the report after it names a server other than the last
  one seen. `suite.py` runs a session
  (tap, probe, the guard's warm-up, `DesktopEnv.reset`'s observation, whose
  delivery the runner records, pre and post guards, actions, marker) and
  assembles each trial's observation. It starts the tap and the probe each in
  its own transient systemd scope (`SCOPE_LAUNCHER`: `systemd-run --user
  --scope`, returning only once the process's control group is the scope's;
  a launch that cannot reach its scope fails the session), so a guest-server
  restart, which stops every process left in the server's unit, leaves both
  running (decision D30). It records the server's unit and its `NRestarts`
  counter at the session's start and end, and `session_restarts` and
  `accessibility_calls` count a session's restarts and `/accessibility`
  calls (criterion A7). When the probe is gone after an entry and the tap's
  process is gone too, it still relaunches the tap into a new file, each in
  a new scope, before relaunching the probe, and `segment_check` judges each
  tap's records against that tap's own keymap. `verdict.py` applies sections
  4.3 and 5.
- **Acceptance analysis** (`acceptance.py`). The main preregistration's
  sections 5-9 as code (its design decision 32): end states from the batch
  script's own record and, when read, Slurm; the rerun rules; an undelivered
  reset observation charged to the session's first trial; the realized order
  and one source tree per criterion; A1-A6, with A1-A4 and the ladder not
  counting a trial whose only failure is a guest-server restart (decisions
  D30 and D33), A1-A3 judging an entry on its counted repetitions and failing
  it on a second excused trial, and a ladder rung not qualifying with more
  than two; A7, the restarts per accessibility call on the exact one-sided
  95% Poisson bound, its calls capped at the plan's 39,036; C1; C2's
  reading of L0-raw trials (main section 8, decision 34); C3's clean kills
  (decision 36); C4; and the ladder's N* with the foreign-load abort and its
  rerun cap.
- **Lane** (`runner.py`, `driver.py`, `manifest.py`, the batch script and
  the submitter). Every campaign runs as a CPU-only Slurm job (decisions
  D12, D13). `manifest.py` admits an acceptance or scored-control campaign
  only when the ledger freezes the main preregistration and the addenda it
  needs, every file their frozen tables pin holds its digest in the exported
  source tree, and, when the executor addendum is needed, no file under
  `harness/q2/` (Markdown aside) is unpinned; it names the executor addendum
  of each repair attempt, fixes the runner CPUs per concurrency, and refuses
  seeds 43 and 44 for every other purpose. It admits A7 at N* with no repair
  attempt. Development manifests may name a trial after which the runner
  SIGKILLs the guest server (`kill_guest_server_after_seq`) or a trial inside
  which it does so before the post guard (`kill_guest_server_during_seq`), to
  exercise the restart handling; no scored campaign can.

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
| `30d8c7f` | `suite.py`, `runner.py`, `driver.py` | After the review of `2b492cd`: when the probe is gone after an entry and the tap's process is gone too, the tap is relaunched into a new file before the probe, and each tap's records are checked against its own keymap; a restart between entries, when the guard before the next entry cannot run, is charged to that entry as `guest_server_restart`; the runner records whether `DesktopEnv.reset`'s observation was delivered; a development-only hook SIGKILLs the guest server after a given trial. Run 622 had charged 55 trials of one session to a single restart (its tap gone). Development run 662 (the hook after the tenth trial of each of its two sessions, one per setting) then failed only that next trial in each session, with `guest_server_restart` typed and the tap and probe relaunched; 27 of 28 trials passed in each session, every tap segment's mapping check clean. |
| `30d8c7f` | `manifest.py` | After the review: admission checks every file the needed registrations' tables pin and, with the executor addendum, refuses any unpinned file under `harness/q2/` (main design decision 35); repair attempts name `q2-action-path-v1-executor-a2` or `-a3`, and C1-C3 have none; C2's manifest needs only the inputs addendum (it could not have been submitted before the executor freeze); the runner CPUs of a scored campaign are `runner_cpus(N)` (main decision 38); the development fault hook is admitted for suite development only. Development manifests are judged as before. |
| `30d8c7f` | `acceptance.py` (pinned here from this commit on; it was in the executor addendum) | After the review (and, one commit later, reading the end state that `scripts/record_slurm_end_states.sh` records next to a run directory): C2's reading of L0-raw trials (main decision 34), C3's clean kills (decision 36), end states and reruns (decision 37), the reset-observation charge and one source tree per criterion. No scored data exists; every rule is driven on synthetic campaigns by `tests/test_q2_acceptance_analysis.py`. |
| `34f79e4` | `suite.py`, `runner.py`, `driver.py`, `manifest.py` | Decision D30, recorded in `program/decisions.md` before the freeze in answer to run 622's restart, not to any scored outcome. The tap and the probe start in their own transient systemd scopes (`SCOPE_LAUNCHER`), so a guest-server restart leaves them running; each session records the server's unit and its `NRestarts` counter at its start and end, and `session_restarts` and `accessibility_calls` count a session's restarts and calls; the development-only hook `kill_guest_server_during_seq` kills the server inside an entry before its post guard (the runner's `kill_guest_server` moved to `suite.py`); the driver plans A7 and adds the counts to its session summary; `manifest.py` admits A7 (G, 360 repetitions, accessibility setting, at N*). Run 694 at this commit killed the server inside the tenth trial and after the twentieth of each of its two sessions: the probe and the tap ran on in their scopes (no relaunch, one tap segment each, mapping checks clean), the trial killed inside failed with `guest_server_restart` alone, the trial after the second kill failed as decision 39 charges it, and the other 26 trials of each session passed. |
| `34f79e4` | `acceptance.py` | Decision D30: A4 does not count a trial whose only failure is a guest-server restart (`restart_only`; it is reported), A7 judges restarts per accessibility call on the exact one-sided 95% Poisson bound, and `load` reads each session's restart and call counts. No scored data exists; `tests/test_q2_acceptance_analysis.py` drives both rules on synthetic campaigns, and the loader read runs 694 and 703 (two restarts and, in the accessibility session, 38 calls per session; the two trials killed inside counted as restart-only, the two after a kill between entries not). |
| `7653799` | `manifest.py`, `suite.py` | `manifest.py` refuses an A7 campaign under a repair attempt (main section 11); `suite.py`'s comment states what run 694 measured. Jobs 703-708 ran at this commit (executor addendum, section 9); 695-699, the same campaigns at `34f79e4`, were cancelled while booting when this change was made. |
| `13ad91e` | `acceptance.py` | After the review of `13c6790`, before any freeze and with no scored data: A7 divides the restarts of every attempt by the accessibility calls of the counting attempts only, so cancelling a failing run and rerunning it cannot raise its chance of passing (main design decision 41), and refuses an attempt other than 1; an undelivered reset observation is charged to the first trial as a reason as well as an infrastructure type, and `restart_only` checks both, so a restart-only trial that also lost its reset observation is counted; a restart across the reset observation that left only its tree undelivered is excused on A4's terms (`reset_restart`, main section 6.1); the restart report names each hit trial's session and every session whose restarts hit no trial. `tests/test_q2_acceptance_analysis.py` drives each rule; the loader read runs 694 and 703-707 again with the same restart counts and restart-only trials. No file a campaign executes changed. |
| `3ad255a` | `acceptance.py` | Decision D33, recorded in `program/decisions.md` before the freeze and with no scored data: A1-A3 and the ladder excuse a restart-only trial as A4 does; A1-A3 judge an entry on its counted repetitions and fail it on a second excused trial over both settings, every attempt and, in A1, both shuffles (`RESTART_LIMIT`, never FLAKY); a ladder rung does not qualify with more than two excused trials over its attempts (an aborted attempt aside), and excused trials' steps stay in the step p95; an earlier attempt's failed trials count only on the cells the criterion judges, less its excused ones (an outside-spec R cell's expected failure in an earlier A2 attempt had failed every rerun); A7 caps its calls at the plan's 39,036; each criterion's restart report lists its excused trials. `tests/test_q2_acceptance_analysis.py` drives each rule; the loader read runs 694 and 703-708 again (main section 20). No file a campaign executes changed. |

The probe change makes the no-action entry's screenshot start from a settled
screen, the canary changes make the read-back report what the app holds, and
the warm-up and the reset observation move once-per-boot effects out of the
first entry. Two changes touch how a trial is judged: the observation-failure
rule of `b603347`, which aligns the code with main section 6.1 (a recovered
retry had been counted as a failure, which 6.1 did not say; the retries stay
in every report), and the restart rule of `30d8c7f`, which types a restart
between entries that the guard could not see before. The analysis rules of
`30d8c7f` (C2, C3, end states, reruns, the reset observation) were written in
answer to the review of the registration, not to any trial's outcome. The D30
changes (`34f79e4`, `7653799`) apply decision D30 on run 622's
restart: the scopes change how much a restart costs, not how a trial is
judged, and A4's restart exclusion and A7 change only how A4 counts and what
else is bounded (section 6). `13ad91e` answers the review of `13c6790`: it
narrows A4's exclusion where it was too wide, adds the reset observation's
restart on the same terms, and closes A7 to cancel-and-rerun; it changes no
trial verdict. `3ad255a` applies decision D33, which the owner took before
the freeze on the exposure main section 18 stated, not on any scored
outcome: it changes how A1-A3 and the ladder count a restart-only trial,
never how a trial is judged. No scored campaign has run.

## 6. A decision before the freeze: guest-server restarts and A4

Main section 16, item 9: in development the OSWorld guest server crashed once
in the 8,114 `/accessibility` calls of runs 484-622 (8,117 attempts with
retries; the first count, 7,969, missed some calls; its tree walk runs on a
thread pool), and its systemd unit then stopped every process the server had
launched. A crash is an infrastructure failure (main section 6.1), and A4
needs zero failures over 36,515 accessibility calls (35,981 steps and 534
reset observations in its screenshot-plus-accessibility sessions; first given
as 36,550 and 36,016, corrected after the review of `13c6790`): about 4.5
expected crashes at that rate, so A4 would pass with probability about 0.01.
That rate rests on a single event. The exact Poisson 95% interval for one
event (0.025 to 5.57 events) puts the expected number of crashes in A4
between about 0.11 and 25, so A4's pass probability under the current rule
lies between about 0.89 and zero; the point estimate is the one above.

Where the faults struck (recounted from the receipts): there were two
observation-service faults in the 113 accessibility-setting sessions of runs
484-622, both in a session's first trial. Run 537's was an HTTP 500 on the session's first `/accessibility` call
(before the reset observation existed), which its retry recovered. Run 622's
crash came on the session's third call (the reset observation and the first
step's call had both answered), and the retry after the restart delivered the
tree. Per session, the crash (1 of 113 sessions) gives about 4.7 expected crashes
over A4's 534 accessibility sessions, close to the per-call figure; the HTTP
500 was delivered by its retry and would not count against A4. Two events cannot
show whether faults cluster at a session's start.

The registration keeps the strict rule; the options the owner can take before
the freeze, each with its cost:

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
   systemd scope). Since `30d8c7f` the suite relaunches the tap with the
   probe after a restart, so a restart already costs the entry it hits rather
   than the rest of the session (development run 662; section 5); a separate
   scope would also spare that entry. Neither changes a verdict on its own.
5. Warm the accessibility service up at boot (suggested by the review of
   `2b492cd`): after `DesktopEnv.reset`, call `/accessibility` until two
   consecutive calls deliver, and have Stage 1 do the same. It is cheap and
   leaves the runtime as upstream ships it, but the one crash on record came
   after two consecutive delivered calls in its session, so this would not
   have prevented it; on the present evidence it is not expected to change
   A4's outlook.

Whichever is chosen, the decision and its reason go into
`program/decisions.md` before `q2-action-path-v1` is frozen, and the
single-event uncertainty above is reported with A4.

**Decided (D30, 2026-10-07), options 3 and 4 together.** A4's zero-failure
count excludes guest-server restarts, which are reported (a trial whose only
failure is the restart, with the tree it left undelivered, is not counted;
main section 6.1). The observation service gets its own registered bound, A7:
at most 5 x 10^-4 restarts per accessibility call on the exact one-sided 95%
Poisson upper bound, from a dedicated campaign of 39,036 planned calls (main
sections 7 and 9). The probe and the tap start in their own systemd scope,
so a restart costs at most the entry it hits (section 2; runs 694 and 703,
section 5). Stage 1 counts restarts per episode as infrastructure failures
(main section 7). The single-event uncertainty is reported with A4 and A7.
D30 rejects option 2 because patching the server would make the runtime
differ from the one the leaderboard uses; option 5 is not taken because the
one crash on record came after two delivered calls. Every other rule was
left unchanged; main section 18 states what that left exposed.

**Extended (D33, 2026-10-07).** The owner extended the exclusion to A1-A3
and the concurrency ladder before the freeze: a trial whose only failures
are a guest-server restart during an observation call and the tree it left
undelivered is excused and reported there too, while a restart during
`/execute` or a guard still counts. An A1-A3 entry is judged on its counted
repetitions and fails on a second excused trial; a ladder rung with more
than two excused trials does not qualify, and excused trials' steps stay in
the step p95. A7's call count is the counting attempt's, capped at the
plan's 39,036. The remaining exposure (restarts outside an observation
call or slower than the retries, and a post-guard restart that costs two
entries) is stated with A4 and accepted (main sections 6.1, 9 and 20).
