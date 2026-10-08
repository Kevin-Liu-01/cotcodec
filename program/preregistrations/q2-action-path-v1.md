# q2-action-path-v1: action-path suite on the nested-KVM desktop runtime

**Status: DRAFT. Not frozen.** The program owner reviews and freezes it with
`uv run python scripts/preregister.py freeze q2-action-path-v1 program/preregistrations/q2-action-path-v1.md`.
No acceptance trial may run before that ledger entry exists.

- Experiment id: `q2-action-path-v1`
- Question: Q2 (calibrated computer-use instrument), Stage 0b. Program kill
  criterion it implements: "No GPU episodes until the action-path suite passes
  100%" (`program/questions/q2-calibrated-cua-instrument.md`), read here as
  100% of the gating set G defined in section 4.
- Drafted: 2026-10-07, on branch `stage0/q2-action-path`. Revised the same day
  after an independent review (section 15 lists what changed and why), and
  again to apply decisions D30 and D33 on guest-server restarts before the
  freeze (branch `stage0/q2-action-path-d30`; sections 18 and 20).
- Reviewed plan this follows: the Stage-0 workflow's reviewed plan
  `q2-action-path-and-vm`, corrected order (catalog and expectations before any
  executor; independent device reference; mutation testing of the suite; one
  IR and one executor; per-harness specs; cross-app canary; both observation
  settings; volume certification split from development).

## 1. What this experiment decides

Whether the action path from a Qwen3.5 tool call to the desktop's input events
is correct enough that Stage-1 task outcomes can be attributed to the model,
the harness design and the observation type rather than to dropped, reordered
or wrong input. It does not measure any model. Its outputs are pass or fail
verdicts per layer, the suite's own mutation score, upper bounds on residual
failure rates per Stage-1 action class and per VM boot, and (decision D30) an
upper bound on guest-server restarts per accessibility call.

## 2. Frozen inputs

### 2.1 Runtime

| Input | Pin |
|---|---|
| OSWorld runtime | `xlang-ai/OSWorld` at `b138d348256078fa634fc3b73567a7337c793e6b` (`DesktopEnv.step`, `PythonController`) |
| VM image | `happysixd/osworld-docker@sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9`, local image ID `sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4` |
| Guest disk | `xlangai/ubuntu_osworld` at `a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133`, `Ubuntu.qcow2.zip` 12,273,896,463 B, SHA-256 `b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712`; member `Ubuntu.qcow2` 24,460,197,888 B, SHA-256 `6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313`, read-only on the host |
| VM settings | `RAM_SIZE=4G`, `CPU_CORES=4`, `DISK_SIZE=32G`, container memory limit 6 GiB, CPUs from the Slurm allocation |
| Guest facts (boot report, job 374) | Ubuntu 22.04.3, Xorg, GNOME Shell 42.9, 1920x1080, xkb evdev / pc105 / us, PyAutoGUI 0.9.54, python-xlib 0.33, RECORD and XTEST present, 19 spare keycodes, guest server `main.py` SHA-256 `41376a5c4f0b68ed7bbbbcc73ece60427f4a58dd8bd4710176f9911de726339e` |
| Network layout | `none-netns`: VM container with `--network none` and no published ports; the runner joins its namespace (decision D13) |
| Step pause | `DesktopEnv.step(action, pause=0.0)`, the Stage-1 value (OSWorld `bfd62bdc` `run_multienv_qwen35vl.py`, `--sleep_after_execution` default 0.0) |
| Observation settings | both `require_a11y_tree=False` (screenshot) and `require_a11y_tree=True` (screenshot plus accessibility tree) |
| Lane | `infra/slurm/host-single-node/vm-campaign.sbatch` through `scripts/submit_vm_campaign.py` (decision D12) |
| Runner image | GPU-less image `sha256:ac2b5815bcc2ed193116aa2d4bdee773b5a457c545453a6c91956768634a6002`, kept as a `docker save` tarball (SHA-256 `ec434c04f03b8534e7ef61e1e88a6721b687ad8c3959e24a1dfea10d76d427b3`) and recorded with its package versions in `infra/q2-vm-runner/image-lock.json` |

### 2.2 Suite inputs and when each is frozen

Every suite input that exists when this file is frozen is pinned here by its
SHA-256 (table below), so freezing this file freezes them; the ledger row adds
the repository's git head. Inputs that cannot exist yet are frozen in two
addenda, each its own ledger entry made with `scripts/preregister.py`:

- **`q2-action-path-v1-inputs`** (`program/preregistrations/q2-action-path-v1-inputs.md`),
  frozen after this file and before C2 is scored: the guest probe (event log,
  text buffer, marker block, entry delimiters), the marker decoder, the entry
  guard, the canary driver (app launch, fixture writing and read-back for
  `canary.yaml`), the two detection controls' translators (H-OSW-up's
  PyAutoGUI strings to IR, H-GA-buggy's action dicts to IR) with the
  unmodified upstream parsers they read, the code that judges a trial, the
  acceptance analysis that turns campaigns into the verdicts of A1-A7, C1-C4
  and N* (`acceptance.py`, decision 32; frozen here so that C2's analysis is
  fixed before C2 is scored, decision 34), and the VM lane every scored
  campaign runs on. Its own validation is infrastructure only (HMP input into
  the probe, no-input canary read-back; job 484).
- **`q2-action-path-v1-executor`** (`program/preregistrations/q2-action-path-v1-executor.md`),
  frozen when development ends and before the scored C1 and C3 runs and the
  first acceptance trial: the file digests of L0-fixed, the H-OSW-fixed and
  H-GA adapters, the acceptance workload code (`harness/q2/vm/*.py` and the
  batch script, pinned again), the regression corpus (`suite_cells.json` and
  its generator), the mutation kit, `harness_design_diffs.md`, the canary
  target coordinates (`canary_targets.json`), the acceptance analysis
  (`acceptance.py`, pinned again) and the VM-hour sizing with the measured
  trial times it uses (`vm_hours.py`, decision 33); its ledger row's git head
  is the executor SHA. A repair attempt k (section 11) runs under its own
  executor addendum (`q2-action-path-v1-executor-a2`, then `-a3`).

Both addenda were written in one development pass with L0-fixed, before any
freeze, not in the order the first draft gave (design decision 25).
Acceptance and scored-control campaigns are admitted by `manifest.py` only
when the ledger freezes this file and the addenda they need (C2: inputs;
C1, C3 and A1-A7: both), every file the frozen tables of those registrations
list holds its frozen digest in the exported source tree, and, for every
campaign that needs the executor addendum, no file under `harness/q2/`
(Markdown aside) is left unpinned (design decision 35); the submitter checks
this and the job checks it again.

Every acceptance and scored-control receipt verifies this file, every
addendum frozen by then, and the runner image ID.

Frozen with this file (SHA-256 of the committed bytes):

| File | SHA-256 |
|---|---|
| `harness/q2/action_path/catalog.yaml` | `5934c4281cb85a8309be32cb98442b038054a2bba0e7ec3755e20112710b7bba` |
| `harness/q2/action_path/rdev_reference.json` | `5cc48d5177a7f07baed36b90ab76ce3e10de835b42596fc6a53427add49b518a` |
| `harness/q2/action_path/rdev_plan.json` | `5c9b7215c89aadfa6308bdd94c629a716c7c822a8ca626315157e84bd1495d89` |
| `harness/q2/action_path/gating_set.json` | `fe2afcaa5fcb6710f54510555633bcd86bc8d516f01211253cfd46271fdf5a6a` |
| `harness/q2/action_path/expressible_entries.json` | `380e058e9aced24e30cbfc93ebace901a5cb02b567b42f0cceb7543c87c822ac` |
| `harness/q2/action_path/volume_plan.json` | `9567d257b769273788153c4193981f1c7eb1e8664b4d1ef36389b4fbd211802a` |
| `harness/q2/action_path/mutation_operators.yaml` | `429cbc389238404b1b6c345b883db9ada5b470ebad3594a8895187aa377e1259` |
| `harness/q2/action_path/l0_raw_prediction.yaml` | `8b947acafeae1d2bf4fda5a715888556d9ca672e57d488a4c31dadc420f9302a` |
| `harness/q2/action_path/canary.yaml` | `16e15b6a48a6a560958500b1e6507e1be7368fd0fff2348cb5ed7188e66881ff` |
| `harness/q2/action_path/keysyms.json` | `a1ea436d9bd4ae8d9fbc8305772f7dca776858b023092ce1cea059a693924acb` |
| `harness/q2/action_path/ir.py` | `33dc24771b823597eef453a4994faf730d0364bd090488aa13e9de5e3498d305` |
| `harness/q2/action_path/vocab.py` | `f26dd7d34988aebf8e8bbeb3ea118e6da3b9d37505ba8433a6eb6d9f0f186792` |
| `harness/q2/action_path/catalog.py` | `2223a05b4e88dbc8af52751c9c87b10db99a121cdb93e5289979c657bf92126b` |
| `harness/q2/action_path/rdev.py` | `c526f7ed5b8cc560c5419f9f5e25541b46178f2c375b24cbbee84e0093daab83` |
| `harness/q2/action_path/l0_raw.py` | `391249f7900dfc327947505526b22710f7dd6bf70f71a230d9865ae7da174f84` |
| `harness/q2/action_path/volume.py` | `91cbbb7f2bf7cd8715ae7c3c88fb8744ff40bd89955283eb680578c24d2a09c7` |
| `harness/q2/action_path/build_catalog.py` | `f7b5b9650c8d416b99507ebaf8522f8075aad928ead7e4c3b702bd2ee63435d8` |
| `harness/q2/action_path/build_derived.py` | `c3e05c8f72c3f49849be7ce59a7b655067c61679e5dbdfa8ac2c130c5299c4e0` |
| `harness/q2/vm/guest/xrecord_tap.py` | `6a6e9453f138776b0717a9087767be0f97460f1ea0d5302f31e21ae1a4a80a74` |
| `infra/q2-vm-runner/image-lock.json` | `380f721b03b8941f30a792b67e804d6a2bf4b424c0131c630594af824c0131a4` |

A test (`tests/test_q2_prereg_inputs.py`) recomputes every digest in this table
from the repository, so no listed file can change without changing this file.
After the freeze, a change to any of them is a new preregistration.

## 3. Layers under test

One canonical action IR (`harness/q2/action_path/ir.py`: the Table 21
vocabulary of arXiv 2609.40284 plus explicit holds, buttons 8-9 and the
horizontal wheel) feeds one executor. Upstream input strings survive only in
the L0-raw control.

| Layer | Definition |
|---|---|
| L0-fixed | the project's executor: one base64-transported guest script per IR action sent through `DesktopEnv.step`; holds within one process with release in `finally`; XTest buttons 1-9; explicit key-name map, unknown keys raise; zero spare keycodes raises |
| L0-raw (control) | each IR action as its natural PyAutoGUI 0.9.54 call, one `DesktopEnv.step` per IR action, built by `l0_raw.py` (frozen with this file) |
| H-OSW-up (control) | OSWorld `bfd62bdc` `Qwen35VLAgent.parse_response`, unmodified; its PyAutoGUI strings are mapped call-for-call to IR by a fixed translator (inputs addendum), then run on L0-fixed |
| H-GA-buggy (control) | gym-anything `bf965cde0` `agents/agents/qwen35vl.py` with `agents/shared/qwen_computer_use.py`, unmodified; its action dicts are mapped to IR by a fixed translator (inputs addendum) |
| H-OSW-fixed (Stage-1 harness) | `bfd62bdc` with its emit boundary patched to IR and only its own-spec bugs fixed: terminate(status=failure) becomes FAIL; key names go through an explicit map and unknown names raise; text goes through the IR `type` action exactly (edge whitespace kept); `wait` waits its `time` (decision 23). Changes are marked under Apache-2.0 §4 |
| H-GA (Stage-1 harness) | gym-anything `aae6f7607`, unmodified; an adapter maps its action dicts to IR and `metadata.status == "failure"` to terminate(failure) |

**IR boundary rules (both Stage-1 harnesses, frozen here).** (1) Every pointer
coordinate a harness produces passes through `ir.clamp_point` before it
becomes IR: truncate to an integer, then clamp to x in 0-1919 and y in 0-1079.
Both harnesses scale the 0-999 grid with `int(v * size / 999)`, so 999 becomes
1920 or 1080, one pixel off screen; upstream, PyAutoGUI passes that point to
XTest and the X server clamps it to the last pixel. The clamp reproduces that
upstream behaviour while the IR itself still rejects off-screen points. It is
neither a harness fix nor a design difference. (2) Key names map to X keysym
names; the IR accepts every name X.Org's `keysymdef.h` defines
(`keysyms.json`, 2,109 names) and stores aliases under one canonical name.

**Per-harness spec.** A harness is judged against its own system-prompt tool
description. Where that description is silent, Table 21 semantics apply. A
deviation the description itself declares (H-OSW: triple_click "simulated as
double-click", hscroll "mapped to regular scroll"; H-GA: scroll magnitude 1 to
10 per call, which its parser enforces by clamping to 10) is a design
difference, logged as part of the harness factor in `harness_design_diffs.md`,
never fixed and never counted as a failure. A parameter an action's
description does not mention is outside that action's spec. Expressible sets
computed by `vocab.py`: H-OSW 85 entries, H-GA 79 (`scroll_down_25` is outside
H-GA's declared magnitude).

**Regression set R (Table 20 call forms).** Each case is a rendered model
response. Expected IR follows Table 21 semantics, except where the harness's
own prompt declares a deviation (judged against the declared behaviour) or
does not cover the call form (outside spec). The status of each cell is also
in `mutation_operators.yaml` (`regression_cases`), which a test checks.

| Case | H-OSW-fixed | H-GA |
|---|---|---|
| R01 middle_click at a coordinate | gating | gating |
| R02 left_click with `text="ctrl"` | gating | outside spec |
| R03 left_click with `keys=["ctrl"]` | outside spec | outside spec |
| R04 shift-, alt- and ctrl+shift-click via `text` | gating | outside spec |
| R05 mouse_move then scroll, two calls in one response | gating | gating |
| R06 mouse_move then one-point left_click_drag, two calls | gating | outside spec |
| R07 three calls in one response (click, type, key) | gating | gating |
| R08 triple_click | declared deviation (expects double click) | gating |
| R09 scroll with a coordinate | outside spec | outside spec |
| R10 hscroll | declared deviation (expects vertical scroll) | outside spec |
| R11 terminate(status=failure) gives FAIL | gating | gating |
| R12 type with non-ASCII text (the five Unicode catalog strings) | gating | gating |
| R13 key `kp_enter`, `menu`, `super` (one call each) | gating | gating |
| R14 left_click at (999, 999) lands on (1919, 1079), exactly (0 px tolerance) | gating | gating |

Outside-spec cells still run and are reported with the IR each harness emits.
Pointer positions are judged within ±2 px except R14, which is exact: scaling
by width/1000 instead of /999 (mutation operator M24) moves the corner by one
or two pixels, inside the usual tolerance.

**Corpus.** Each harness-expressible catalog entry and each R case is rendered
as model responses with the official template of `Qwen/Qwen3.5-9B` at
`c202236235762e1c871ad0ccb60c8ee5ba337b9a` (`chat_template.jinja`, XML tool
calls, list values rendered as JSON), one tool call per turn (both prompts
ask for a single call per step; a positioned H-OSW scroll and a two-point
H-OSW drag take a `mouse_move` turn first), multi-call turns only in R05-R07,
plus three perturbations: an `Action:` sentence before the calls, a closed
think block before the calls, and (H-GA only, which documents it) the JSON
tool-call fallback. A2 runs the plain renderings; every perturbation must
parse to exactly the plain rendering's IR on every gating and declared cell
(decision 22). A catalog
pixel is rendered as the 0-999 grid value whose scaled pixel is nearest to it
(ties to the smaller value); the rendering error is at most one pixel, inside
the ±2 px tolerance. Real model responses enter only in a later
preregistration.

## 4. Catalog, gating set and oracles

### 4.1 Catalog

`catalog.yaml` is an independent reimplementation that uses the 100 public
entry IDs, their order and group sizes (clicks 18, drags 11, keys and chords
34, scrolls 12, mixed 8, typing 17) from sandweave@99ba1abe as facts. Every
action, coordinate, string and expectation was written for this repository.
The file is pure ASCII; non-ASCII text is escaped, so no editor can normalize
it. Results are never presented as reproducing the paper's 83/11 or 94/94.

### 4.2 Gating set G

G is the set of entries whose every action is expressible by at least one
Stage-1 harness (`vocab.py`). |G| = 86. The 14 non-gating entries are frozen by
name: `click_button_back`, `click_button_forward`, `press_hold_release_left`,
`press_hold_release_right`, `drag_multipoint_l_shape`, `drag_right_button`,
`drag_middle_button`, `drag_shift_held`, `drag_ctrl_held`, `drag_alt_held`,
`scroll_left_3`, `scroll_right_3`, `scroll_diagonal`, `mixed_gesture_state`.
They run in every pass and are reported; they do not gate.

### 4.3 Oracles

- **Pointer and scroll entries (self-specified oracle):** the catalog's own
  expectation: X button numbers, counts and order; press and release positions
  within ±2 px; wheel buttons 4-7 with their counts; modifier masks on button
  events; the timing bounds `min_gap_ms` and `max_gap_ms` (double and triple
  clicks: successive presses within 300 ms); at least 3 motion events inside
  drags; the final pointer position within ±2 px where given. These
  expectations were written by the suite's authors, not measured on an
  independent device, and every report labels these entries (and the pointer
  part of mixed entries) "self-specified oracle". The one convention an
  independent device can check, the numbering, was checked: in job 374, HMP
  `mouse_button` left, middle and right reached X as buttons 1, 2 and 3, and
  HMP wheel `dz` −1 and +1 as buttons 5 and 4, in 22 of 22 boots, which is
  the catalog's convention. Design decision 11 says why no R-dev reference
  was captured for pointer entries.
- **Text entries:** code-point equality, no normalization, between the
  catalog's `text` and what the probe's text buffer gained, under the
  catalog's buffer rules (printable code points appended; Return and KP_Enter
  append `\n`; Tab appends `\t`; BackSpace deletes the last code point). The
  expected string is the typed string itself.
- **Key, chord and Caps Lock entries (35):** the R-dev reference. Each entry's
  `rdev_input` chords are sent through the QEMU human monitor (`sendkey`) of a
  fresh VM, 5 repetitions, and the guest's XRecord stream is recorded. The
  reference is the projection (event kind, keysym at index 0 of the keycode,
  modifier mask restricted to Shift, Control, Mod1, Mod4) with timestamps
  removed. An entry gets a reference only if all 5 repetitions give the same
  projection, every key pressed in the window is released in it, and the guard
  after the entry is clean; otherwise it is labelled "self-specified oracle"
  and its claim is downgraded in every report. Caps Lock additionally requires
  the Caps LED bit to toggle on and back off. Infrastructure validation (job
  374) measured the HMP path: `sendkey` reaches X for letters, Shift chords,
  KP_Enter (keycode 104), KP_Add (86), the 102nd key (94, `less`), Caps Lock
  with LED toggle, and qcode `compose` gives Menu (135) while qcode `menu`
  gives no event.
- The R-dev capture is a reference measurement on the input device, not a
  trial of any system under test. Job 393 captured all 35 entries: every one
  stable over 5 repetitions, balanced, with a clean guard, and the Caps Lock
  LED toggling on and back off in 5 of 5. An earlier capture (job 387) let the
  first recovery press of four side-effect entries fall inside their windows;
  it is superseded and kept on the host. Job 468 re-captured the same plan
  with the rewritten tap (section 4.4) to check that the tap change leaves the
  reference unchanged (section 13).

### 4.4 The XRecord oracle channel

`harness/q2/vm/guest/xrecord_tap.py` (frozen with this file) records, in the X
server's processing order, the core device events and every core
`ChangeKeyboardMapping` request, and resolves keysyms from its own keymap: the
full mapping read at start, updated by each recorded request in stream order.
A key event is therefore projected with the mapping in force when the server
processed it, including after a spare keycode is remapped. The raw keycode
and every mapping change are recorded, so any projection can be recomputed.
A second connection records each keyboard MappingNotify with the keymap it
then reads. A MappingNotify that no recorded core request explains is benign
when that keymap equals the tap's table under the core protocol's keysym-list
rules (`core_groups`): the server re-sends the whole keymap when the master
keyboard switches between the PS/2 and the XTest device, in XKB's
four-column core form. Otherwise the range is unverified (section 6.1).

### 4.5 Certified keysyms

The IR accepts every X keysym name, but A1-A6 certify only the 33 keysyms the
gating entries use: `Alt_L`, `BackSpace`, `Caps_Lock`, `Control_L`,
`Delete`, `Down`, `End`, `Escape`, `F1`, `F4`, `F5`, `F9`, `F12`, `Home`,
`Insert`, `KP_Add`, `KP_Enter`, `Left`, `Menu`, `Next`, `Prior`, `Return`,
`Right`, `Shift_L`, `Super_L`, `Tab`, `Up`, `a`, `c`, `d`, `r`, `space`, `t`
(`catalog.certified_keysyms`). Text is certified per code point class through
the typing entries. No claim is made for a key or chord action naming any
other keysym; the Stage-1 preregistration must count, per episode, the key
actions that name an uncertified keysym and report them as uncertified
action-path exposure.

## 5. Unit and verdict

The unit is one catalog entry (or R case) times one repetition. It is PASS
only if all of these hold:

1. The entry guard is clean before and after it (section 6.2).
2. The event channel matches the oracle exactly as in section 4.3, judged on
   the probe's own event log for `observable: app` entries and on the XRecord
   stream for `raw-only` entries (desktop shortcuts). Each entry's window on
   both channels runs from the probe's begin delimiter to its end delimiter
   (two core `ChangeKeyboardMapping` requests on a reserved spare keycode,
   which both channels see in the X server's own order; design decision 19).
3. For `observable: app` entries, the screenshot returned by the
   `DesktopEnv.step` of the entry's last action decodes to the probe's final
   marker (sequence number and CRC-16 of the text buffer). The screenshot
   includes the compositor's latency; an entry with no action is judged on a
   screenshot taken after the probe's begin, which returns only once the screen
   shows the entry's sequence number (decision 21).
4. `no_action_control` records zero key, button and motion events on every
   channel.
5. For harness layers, the terminal action matches (terminate success or
   failure, or none).

An entry passes a pass at k of k repetitions. Any mixed result is FLAKY and
counts as a failure. An entry that is PASS in one setting and not another is
a failure of that setting. Validity control C2 reads L0-raw trials under its
own rule (section 8, design decision 34); every other criterion uses this
section as written, except that A1-A4 and the concurrency ladder leave out a
trial excused for a guest-server restart (decisions D30 and D33, section
6.1): A1-A3 judge an entry's k of k on its counted repetitions, and an
excused trial alone never makes an entry FLAKY.

## 6. Infrastructure failures and the guard

### 6.1 Infrastructure failures

An infrastructure failure is any of: a boot that does not serve a valid
`/screenshot` within 300 s of container start; an `/execute` call whose first
attempt does not return HTTP 200 within 30 s (`DesktopEnv` would retry it, and a
retry can run the action twice); a `/screenshot` failure, meaning no valid image
after `DesktopEnv`'s own three attempts; in the screenshot-plus-accessibility
setting, an `/accessibility` failure, meaning no tree after its three attempts;
a restart of the guest server during an entry (the guard's two reports name
different server processes, or, when the guard before the entry could not
run, its report after the entry names a server other than the last one
seen); a `DesktopEnv.reset` observation (taken before each suite session's
first trial, design decision 30) that `DesktopEnv`'s retries do not deliver,
charged to the session's first trial;
the probe absent at a guard; the QEMU monitor unreachable during a reference
capture; a key event inside an entry's window on a keycode range the tap's
`mapping_check` marks unverified; a campaign receipt with `infra_gates_pass`
false or a Slurm state other than COMPLETED with exit code 0:0. An observation
that a retry of `DesktopEnv`'s delivers is what a Stage-1 agent would see; it
is not a failure, and every such retry is counted and reported per type
(`observation_retries`). Changed before the freeze: the judging code had
counted any retried `/screenshot` or `/accessibility` call as a failure, which
this section did not say; development run 537 had one (the boot's first
`/accessibility` call answered HTTP 500 and its retry 200, in 1 of 2,415
accessibility calls over runs 484-541), and each session now takes
`DesktopEnv.reset`'s observation before its first trial (design decision 30).

Infrastructure failures are **not excluded** from any gating verdict: an entry
that hits one fails that repetition. They are counted and reported separately.
The one exception is a trial excused for a guest-server restart in A1-A4 and
the concurrency ladder, below.

**Guest-server restarts** (decisions D30 and D33, decided before the freeze).
The probe and the tap run in their own systemd scope, outside the guest
server's unit (design decision 42), so a restart of the server leaves both
running and costs at most the entry it hits. That entry still fails with
`guest_server_restart`. A1-A4 and the concurrency ladder **excuse** it: a
trial whose only reasons are `guest_server_restart` and, from the same
restart, an undelivered accessibility tree (`accessibility`) is reported and
not counted (`acceptance.restart_only`). That reason set is how a trial's
record shows a restart during an observation call that `DesktopEnv`'s
retries absorbed. Any other reason in that trial counts as usual: a restart
during an `/execute` call or a guard, or one slower than the retries, leaves
an `execute`, `screenshot` or `guard_script` failure (or a missing probe, tap
window or marker) in the trial it hits, and that trial counts (design
decision 40); the same server delivers the actions. A6 and C1-C3 run the
screenshot setting, which makes no accessibility call, and excuse nothing
(a restart there is an infrastructure failure under their own rules); A5
judges no trial, and A7 judges the restarts themselves.

A1-A3 judge an entry on its counted repetitions (section 5), and an entry
needs all but at most one of its repetitions counted: a second excused
trial in one entry fails that entry (`RESTART_LIMIT`, reported as such and
never as FLAKY; decision D33). The count runs over all of the entry's
repetitions in the criterion: both observation settings, every attempt
(below) and, in A1, both shuffles. An A1 entry can therefore lose at most
one of its 20 repetitions, an A2 cell one of its 10 and an A3 entry one of
its 60 on each layer (design decision 44 gives the reason for this reading).
A ladder rung reads "every gating trial passes" (section 9) over its counted
gating trials and does not qualify with more than two excused trials, gating
or not, over its attempts (an aborted attempt's trials never count); an
excused trial's steps stay in the rung's step p95, and in A1's. A4 sets no
limit on excused trials: A7 bounds the restarts. Every excused trial is
listed in its criterion's restart report beside A4's and A7's (section 12).

An undelivered reset observation is charged to the session's first trial as
an infrastructure type and a reason of that trial (`reset_observation`), so
it is never excused along with a restart during that entry. The one
exception is the same fault at the reset observation: when the server
restarted across it (the server process the warm-up's report names differs
from the one the first trial's pre guard names) and only its tree was not
delivered, the first trial is excused on the same terms
(`acceptance.reset_restart`), in every criterion that excuses trials. A lost
reset screenshot, or a first pre guard that could not run, still counts. The
observation service that restarts gets its own bound, A7 (section 7). Each
session records the server's unit and its `NRestarts` counter at its start and
end; a session's restart count is the larger of that counter's difference and
the number of changes of server process across its guard reports
(`suite.session_restarts`).

**End state and reruns** (design decision 37). A campaign counts only when it
ended COMPLETED with exit code 0:0, its receipt's `infra_gates_pass` is true,
`System.qcow2` is unchanged and nothing labelled was left. Slurm accounting is
off on this host and Slurm forgets a finished job within minutes, so the end
state is read from the batch script's own last record (`driver_exit=0
labelled_containers_left=0` in the run directory's `preflight.txt`, written
immediately before it exits 0; a job ended by a signal, a time limit or a
node failure never writes it) and, when the operator or a watcher read it in
time, from `scontrol show job`; when both exist they must agree. A campaign
that does not count may be rerun once, as a new attempt with a new output
path; a campaign that counted is never rerun, and no campaign has a third
attempt. Every trial of every attempt is reported, and a failed trial in an
earlier attempt counts against its criterion exactly as if the attempt had
counted: cancelling or rerunning a campaign never removes a failure. Like a
counting attempt's trials, it counts on the cells the criterion judges (G
for A1 and the ladder, the in-spec cells for A2, the stress entries for A3,
every trial for A4) and not when the criterion excuses it, and an earlier
attempt's excused trials count toward A1-A3's and the ladder's limits above,
so a rerun never resets them (decision D33). The only exception is a
concurrency-ladder rung aborted on foreign load (section 9). The same holds
for A7's count of restarts, which sums the restarts of every attempt but
divides by the accessibility calls of the counting attempts only, capped at
the plan's 39,036 calls: an attempt that was cancelled or did not count adds
its restarts and none of its calls, so stopping a run and rerunning it can
never raise A7's chance of passing (section 7, design decision 41).

### 6.2 Entry guard

Before and after every entry: (a) `XQueryKeymap` shows no pressed key and the
pointer shows no pressed button; (b) the LED mask equals the session baseline;
(c) the probe window is mapped, focused and covers 1920x1080 at (0, 0); (d) no
GNOME screen recording is running (no file in `~/Videos/Screencasts` is
growing); (e) before the entry, outside its window, the pointer is moved to
the catalog's `guard.park_pointer` (1234, 777), a point no entry uses (a test
checks it), so an entry that moves the pointer always produces motion:
`move_only` ends where `drag_vertical` ends, and without the park it would see
no motion after it. After an entry with a declared side effect the guard first
runs that effect's restoration (screencast: the chord again while a file
grows, at most three times, then Escape; closes_window: relaunch the probe;
shows_desktop and switches_window: re-activate the probe; hot_corner: Escape;
lock_state: none, the entry must leave the LED at baseline; after a
screencast, closed, shown or switched window and the hot corner the probe is
re-activated) and then requires a clean state. R13's Super key opens the
shell's overview and is restored as the hot corner. Any violation is charged
as a failure to the preceding entry, and the guard restores state (releases
every key and button, toggles the LEDs back, presses Escape, re-activates or
relaunches the probe). The implementation is frozen in the inputs addendum
(`harness/q2/vm/guest/guard.py`).

## 7. Acceptance criteria (gate Stage-1 GPU episodes)

Every acceptance campaign runs its realized trial order in **sessions** of at
most 60 consecutive trials, near-equal in size (`ceil(n / 60)` sessions for n
trials), each session a cold boot of a new VM container in one observation
setting. The session counts below follow from that rule. Every campaign runs
one VM at a time (N = 1) except the concurrency ladder, A4 and A7 (section 9);
`manifest.py` refuses any other concurrency.

- **A1 (runtime layer).** L0-fixed passes 100% of G at 5 repetitions in the
  seed-43 and seed-44 shuffles, each under both observation settings, at N = 1
  VM; and, if N* > 1, passes the seed-43 shuffle under both observation
  settings at the operating concurrency N*, which the ladder rung N* shows (its
  first five repetitions are that shuffle; section 9). All 100 entries run; G
  gates. Trials at N = 1: 100 x 5 x 2 x 2 = 2,000 in 36 sessions (gating
  trials 1,720). Decided before the freeze (decision D33): a trial excused
  for a guest-server restart is left out of its entry's repetitions, and an
  entry with a second excused trial over its 20 repetitions (both shuffles
  and settings) fails (section 6.1). The same holds for A2 and A3 below.
- **A2 (harness layer).** H-OSW-fixed and H-GA each pass 100% of their
  expressible entries (85 and 79) and of their gating and declared-deviation R
  cells, 5 repetitions, judged against their own spec, under both observation
  settings: 990 trials in 18 sessions (H-OSW-fixed, 99 cells) and 930 in 16
  (H-GA, 93 cells). A cell is judged on its counted repetitions and fails on
  a second excused trial among its 10 (decision D33, section 6.1).
- **A3 (stress).** 30 timing- and state-sensitive entries, 60 repetitions
  each, zero failures, on L0-fixed and on each Stage-1 harness where the entry
  is expressible: `click_double_left`, `click_triple_left`, `click_ctrl_left`,
  `click_shift_left`, `click_alt_left`, `click_ctrl_shift_right`,
  `click_burst_5`, `click_double_slow`, `drag_short`, `drag_slow_small`,
  `drag_long_diagonal`, `chord_ctrl_c`, `chord_ctrl_shift_t`,
  `chord_ctrl_shift_arrow`, `chord_shift_tab`, `chord_shift_alone`,
  `chord_ctrl_alone`, `key_kp_enter`, `key_menu`, `caps_lock_roundtrip`,
  `scroll_ctrl_down_3`, `scroll_shift_down_3`, `scroll_down_then_up_net_zero`,
  `type_symbols_shifted`, `type_unicode_bmp`, `type_emoji_zwj`,
  `type_combining`, `type_long_500`, `type_with_correction`, `seq_long_mixed`.
  Repetitions are split evenly between the two observation settings: 1,800
  trials in 30 sessions on L0-fixed, 1,740 in 30 on H-OSW-fixed (29 entries
  expressible) and 1,440 in 24 on H-GA (24 expressible). "Zero failures" is
  read over the counted trials: an entry fails on a second excused trial
  among its 60 on a layer (decision D33, section 6.1).
- **A4 (volume).** L0-fixed runs `volume_plan.json` (built by `volume.py`)
  with zero failures: 64,028 trials over the 86 G entries, each entry's
  repetitions split evenly between the observation settings, in 1,068
  sessions (534 per setting), order fixed by `random.Random(43)` (`sessions`,
  SHA-256 of the realized order `87a70e10bb18d8d81bde77b1c9ce89cc5c8cb212dc6d22f3b36c30964d2e82dd`),
  spread over the N* VMs. Every G entry runs at least 70 times; each of the
  seven Stage-1 device-action classes (left click; other click: right,
  middle, double, triple or with modifiers; move; drag; scroll; type; key or
  chord) gets at least 10,148 executed actions. What this bounds is in section 9.
  Decided before the freeze (decision D30): a trial whose only failure is a
  guest-server restart does not count against A4's zero failures (section
  6.1); it is reported with every restart, and the development rate's
  single-event uncertainty (section 16, item 9) is reported with A4, with
  the exposure that remains (section 9; decision D33 states and accepts it).
- **A5 (reset and hygiene).** A boot-reset campaign at the frozen source SHA
  shows 20 of 20 pristine reset-sentinel checks; every acceptance campaign's
  receipt shows `System.qcow2` unchanged and zero leaked labelled containers
  or volumes.
- **A6 (cross-app canary).** L0-fixed passes 100% of `canary.yaml` (frozen
  with this file) in each of LibreOffice Writer, Google Chrome (a local
  `file://` textarea page), Visual Studio Code and GNOME Terminal, 5
  repetitions per app and entry (300 trials in 5 sessions), screenshot
  setting. `canary.yaml` fixes each
  app's configuration (autocorrect, auto-closing, auto-indent and completion
  off, so the app does not rewrite typed text), each fixture's initial text,
  each entry's actions and its exact expected final text, and the read-back
  (Writer: paragraph texts joined with `\n` from the accessibility tree;
  Chrome: the textarea value, which the page mirrors percent-encoded into its
  title on every input event, read from the window title once stable; VS Code: the saved
  file, once it has changed and is stable; Terminal: the file written by
  `cat`). Changed before the freeze after development runs 501 and 506:
  Chrome's accessibility text was stale after edits that the screen showed,
  and a fresh VS Code profile opened its first-run walkthrough over the file
  (turned off in `canary.yaml`; the driver also waits until VS Code's status
  bar shows the text editor's items); and after run 522, where Chrome's "Can't
  update Chrome" bubble (the guest's Chrome build is older than its clock
  allows) opened mid-trial and took the keyboard focus, `canary.yaml` starts
  Chrome with a flag that keeps the bubble closed; and after run 613, where
  VS Code dropped its first keys while still loading on a busy host, the
  driver also waits until the trial's processes are idle (inputs addendum).
  The entries are the text
  entries `type_plain`, `type_symbols_shifted`, `type_unicode_bmp`,
  `type_emoji`, `type_combining`, `type_rtl`, `type_multiline_tabs`,
  `type_with_correction`, `type_long_200`, `type_spaces`, `type_digits`
  (expected: the catalog string), `key_kp_enter` (expected `\n`), and four
  composites: `select_all_copy_end_paste` on "copy me" (expected "copy
  mecopy me"), `triple_click_line` on "replace this line" then type X
  (expected "X"), `drag_select_word` on "keep word keep", select "word", then
  type Y (expected "keep Y keep"), and `ctrl_home_insert` on two lines "line
  a" and "line b" then type Z (expected "Zline a" and "line b"). GNOME
  Terminal runs the text entries and `key_kp_enter` only. Single-line
  fixtures keep triple-click and drag-select semantics the same in every app.
  The two pointer composites' target coordinates are measured in development
  and frozen in the executor addendum; their expected text is frozen here.
  Each read-back is validated before the inputs addendum with no input at all
  (every fixture reads back unchanged).
- **A7 (observation service).** Decision D30. OSWorld's guest server, which
  Stage 1 runs unchanged, restarts at most 5 x 10^-4 times per `/accessibility`
  call: with k restarts in n calls, the exact one-sided 95% Poisson upper
  bound on the rate (`acceptance.poisson_upper(k) / n`) is at most 5 x 10^-4.
  The campaign is dedicated to it: L0-fixed runs the 86 G entries in the
  screenshot-plus-accessibility setting only, 360 repetitions in
  `random.Random(43)` shuffles, 30,960 trials in 516 sessions, under attempt
  1 at attempt 1's N* (section 11; `acceptance.observation_plan`). It plans
  39,036 accessibility calls: 516 reset observations and 38,520 step
  observations (an observation that `DesktopEnv` retries is one call). k is
  the sum of the sessions' restart counts over every attempt (section 6.1),
  and n the calls the records of the counting attempts show, capped at the
  plan's 39,036 (decision D33), so no record can divide by more calls than
  the plan makes: an attempt that was cancelled or did not count adds its
  restarts and not its calls, so cancelling a run and rerunning it never
  helps (design decision 41). Trial verdicts are reported, not judged: A1-A4
  and the ladder judge the action path. A7 has no
  repair attempt (section 11). A7 gates the screenshot-plus-accessibility
  setting only: if it fails, no Stage-1
  episode uses that setting under this suite, and whether Stage 1 then runs
  screenshot-only or waits for a changed runtime is decided in the Stage-1
  preregistration. Sizing and pass probabilities are in section 9.

All of A1-A6 must hold. If any fails, Stage 1 does not start. A7 must also
hold before any Stage-1 episode uses the screenshot-plus-accessibility
setting.

**What Stage 1 inherits from D30.** Stage 1 counts guest-server restarts per
episode as infrastructure failures: an episode during which the guest
server's unit restarted (its `NRestarts` counter changed, or a different
server process answered) is an infrastructure failure of that episode,
counted and reported per observation setting with the episode's
accessibility calls. How an infrastructure-failed episode enters the Stage-1
analysis is stated in the Stage-1 preregistration.

## 8. Validity controls

If any control fails, the suite is invalid and no acceptance may be claimed.
Each control is scored once, at the point named, and only on frozen code.

- **C1 (detection).** H-GA-buggy (whose prompt also takes modifiers in
  `text`) fails R01 (middle click gives no action), R02 (Ctrl is pressed and
  released before the click) and each of R05, R06 and R07 (only the first call
  runs) in 5 of 5 repetitions. H-OSW-up, judged against Table 21 semantics,
  fails R08 (triple click), R09 (scroll at a coordinate), R10 (hscroll) and
  R11 (terminate failure) in 5 of 5. These are deterministic parser defects,
  so 1 to 4 of 5 is itself a defect. When: after the executor addendum is
  frozen and before the first acceptance trial, with the control translators
  frozen in the inputs addendum, on the frozen L0-fixed, N = 1, screenshot
  setting, R cases in seed-42 shuffle order. Earlier runs are informative
  only, and the translators cannot change after them.
- **C2 (L0-raw prediction).** L0-raw fails exactly the set in
  `l0_raw_prediction.yaml`: `type_unicode_bmp`, `type_emoji`, `type_rtl`,
  `type_combining`, `type_emoji_zwj`, `key_kp_enter`, `click_button_back`,
  `click_button_forward`; every other entry passes, notably every click, drag
  and hold on buttons 1-3, `type_shell_hostile` and `type_symbols_shifted`.
  An entry fails unless it is PASS in 5 of 5 repetitions, where an L0-raw
  trial is judged on the event and text channels (design decision 34): it is
  PASS under section 5's conditions 1, 2, 4 and 5 and the infrastructure rule
  of section 6.1, with two differences. Condition 3 (the marker in the last
  step's screenshot) is reported but not judged, and an R-dev projection is
  compared with the modifier state of every key release left out (key
  presses keep theirs). Both are timing effects of the transport, not of the
  key and button names C2 predicts: L0-raw has none of L0-fixed's settling
  (no key hold, no repaint request, no quiet-screen wait; PyAutoGUI's own
  0.1 s pause only), and development showed what that does to L0-fixed
  (job 486, with no settle and no hold: `chord_ctrl_alt_shift_r`'s four
  releases arrived with no modifier state while its presses matched, and the
  screenshots of `type_with_correction` and `no_action_control` showed a
  stale marker; job 489, with a 0.1 s
  settle: `type_plain`'s marker stale in 1 of 2; runs 504-541, with the quiet
  wait but no repaint request: 31 of 941 typing trials). Every predicted
  failure is a missing or wrong event or text, so the rule keeps every
  prediction testable. `acceptance.c2` applies it (frozen in the inputs
  addendum, before C2 runs) and also reports the section-5 verdicts.
  **Any deviation in
  either direction invalidates the suite for q2-action-path-v1**; the
  investigation is reported but never rescues v1, and a corrected prediction
  can only enter a new preregistration. When: once, after the inputs addendum
  is frozen (it needs the probe, guard and marker), with the translator and
  the prediction frozen here, N = 1, screenshot setting, the 100 entries in
  the seed-42 shuffle.
- **C3 (mutation score).** `mutation_operators.yaml` (frozen here) fixes, for
  each of the 28 operators and each scored layer (L0-fixed, H-OSW-fixed,
  H-GA), whether the mutant is scored, excluded (it can change only cells
  outside that harness's spec; M01 on H-GA) or not applicable (no code path;
  M13 and M28 on H-GA), and which cells can kill it. A scored mutant is killed
  when at least one of its layer's cells that can kill is not PASS in the
  mutant's run without an infrastructure failure on that cell, and the
  unmutated reference run of the same layer (run with the mutants, same
  source tree) passed that cell without one (design decision 36). A failing
  cell with an infrastructure failure never kills, and a cell the reference
  did not pass cleanly never kills; both are reported per mutant. Outside-spec
  cells run and are reported but never kill. A mutant is equivalent only if
  its XRecord stream without timestamps, text buffer and terminal action are
  byte-identical to the unmutated code's on every cell of its layer; a mutant
  neither killed nor equivalent survives, whatever the reason.
  Required: 100% of scored, non-equivalent mutants killed. The detection
  controls H-OSW-up and H-GA-buggy are not mutated: they carry known defects
  and have no spec they are expected to pass. When: once, after the executor
  addendum is frozen, at the frozen executor and adapter SHA with the frozen
  corpus, seed-42 order, N = 1, screenshot setting. Development runs of the
  mutants are informative only. The scored run repeats development's
  conditions (the same seed-42 order and setting; development ran every
  mutant on its predicted kill cells at `b603347` and saw 42 of 44 killed and
  M12 and M13 on H-OSW-fixed equivalent, as predicted), so its outcome is
  largely known in advance: C3 checks that the frozen code and the frozen
  kit still detect every mutant, and is reported as that, not as an
  independent estimate of the suite's sensitivity. M12 and M13 on
  H-OSW-fixed are comment-only patches, because that harness's own prompt
  already declares the behaviour the operator would introduce; they stay
  scored and predicted equivalent as negative controls of the equivalence
  rule (a no-op mutant must come out equivalent, never killed).
- **C4 (R-dev agreement).** For every key, chord and Caps Lock entry with a
  reference, L0-fixed's projected stream equals the reference, in every A1
  trial. Entries without a stable reference are listed as self-specified in
  every report.

## 9. Sample sizes, power and concurrency

**Zero-failure bounds.** With n trials (or actions, or sessions) and no
failure, the one-sided upper confidence bound at level 1 − α on the failure
probability is 1 − α^(1/n). At α = 0.05: n = 5 gives 45.1%; 20 gives 13.9%;
60 gives 4.9%; 70 gives 4.2%; 90 gives 3.3%; 276 gives 1.08%; 6,020 gives
0.050%.

**Target.** The Stage-1 paired minimum detectable effect is about 7-8 pp
(estimate, `program/questions/q2-calibrated-cua-instrument.md`). The suite
should keep the action path's loss per Stage-1 episode of up to 20 device
actions near 1.5 pp, about a fifth of that effect, whatever mix of actions the
episode uses. By the union bound an episode loses at most 20·p_max + b, where
p_max is the largest per-action failure rate over the action classes and b
the per-boot failure rate (Stage-1 episodes are cold boots, so a failure that
strikes once per boot needs power over boots, not over trials).

**What A4 bounds.** Eight statements are made together at family-wise 95%
(Bonferroni, α = 0.05 / 8 = 0.00625 each), all following from zero failures:

- For each of the seven action classes, the per-action failure rate over the
  catalog's instances of that class, weighted as the plan weights them, is at
  most 5 × 10^-4. This needs 10,148 executed actions per class
  (`volume.ACTIONS_PER_CLASS`); the plan gives 10,148 to 10,216.
- The per-session (per-boot) failure rate is at most 0.5%. This needs 1,013
  sessions (`volume.MIN_SESSIONS`); the plan has 1,068 (bound 0.47%).
- Together: 20 × 5 × 10^-4 + 0.5% = 1.5 pp per 20-action episode.

What A4 does not bound: any single entry at that level. Each entry's own
bound (A4 alone, α = 0.05) is listed in `volume_plan.json`: 4.2% for the six
mixed entries (70 trials), 1.08% for each key entry (276), 0.49% for each
typing entry (608), 0.36% for each left-click entry (830), 0.30% for each
scroll entry (1,008), 0.24% for each other-click entry (1,260), 0.15% for each
drag entry (2,002) and 0.030% for `move_only` (10,078). An entry failing 1% of
the time therefore passes A1 and A4 together with probability 0.99^90 = 40%
if it is a mixed entry, and 0.99^296 = 5.1% if it is a key entry. Nor does A4
bound the rate of Stage-1 instances (coordinates, strings, chords) that the
catalog does not contain; the class bounds are over the catalog's instances.
The bound treats actions within a session as independent; failure modes that
are correlated within a boot are what the per-session bound covers. The
earlier draft's claim that 6,020 uniform trials bound "p ≤ 5 × 10^-4 per
action" was wrong: they bound only the uniform-mixture rate. A trial that A4
does not count because a restart hit it (section 6.1) still counts its device
actions toward the class bounds: the action path was judged on that trial and
showed no difference.

**What A7 bounds.** With n calls and k restarts, A7 passes when the exact
one-sided 95% upper bound on the Poisson rate, `poisson_upper(k) / n`, is at
most 5 x 10^-4. At the planned n = 39,036 calls a pass allows at most 12
restarts (the bound is 4.98 x 10^-4 at 12 and 5.29 x 10^-4 at 13). The pass
probability at a true rate r is P(Poisson(r n) ≤ 12):

| True restarts per call | Expected restarts | P(A7 passes) |
|---|---:|---:|
| 0 | 0 | 1.000 |
| 1.0 x 10^-4 | 3.9 | 1.000 |
| 1.23 x 10^-4 (development: 1 in 8,114) | 4.8 | 0.999 |
| 2.0 x 10^-4 | 7.8 | 0.945 |
| 2.5 x 10^-4 (half the bound) | 9.8 | 0.814 |
| 3.0 x 10^-4 | 11.7 | 0.609 |
| 4.0 x 10^-4 | 15.6 | 0.220 |
| 5.0 x 10^-4 (the bound) | 19.5 | 0.048 |
| 6.87 x 10^-4 (development, upper 95%) | 26.8 | 0.001 |

The size follows one rule: a pass must have probability at least 0.80 when
the true rate is half the bound, about twice the development point estimate.
359 repetitions are the fewest that meet it (0.816); 360 is used, and 350
would allow only 11 restarts and pass with probability 0.75 at that rate. At
the bound itself a pass has probability at most 0.05, by the construction of
the exact bound, and no rerun strategy can raise it: n counts only the
counting attempts' calls, capped at the plan's 39,036 (section 7). Had the
calls of a cancelled attempt
been pooled, an operator who cancelled a run at its 13th restart and reran
the plan would pass at the bound with probability 0.071 instead of 0.048
(0.36 instead of 0.22 at 4 x 10^-4; simulation, 20,000 runs per rate); under
the registered rule a cancelled attempt's restarts only add to k, so
continuing a run is never worse than restarting it. A7's sessions average
75.7 calls (A4's accessibility sessions 68.4; a Stage-1 episode of 20 steps
about 21). Two development
faults cannot show whether restarts cluster at a session's start, so A7 also
reports restarts per session with their exact bound (reported, not judged).
What A7 does not bound: the guest server under Stage-1 task applications,
whose accessibility trees are larger than the probe's desktop; Stage 1
measures that rate itself by counting restarts per episode (section 7).

**Restarts in A1-A3 and the ladder (decision D33).** A1-A3 and the five
ladder rungs make 16,639 accessibility calls (A1 1,298, A2 1,452, A3 4,422,
the rungs 9,467, from 778 at N = 8 to 3,112 at N = 40). At the development
rate (1 in 8,114 calls) they see no restart with probability 0.13 (A1-A3
alone 0.41), and under the strict rule any restart would have failed its
criterion or left its rung unqualified. Since D33 that is no longer a pass
condition. What remains, with every restart taken to land in an
observation call (the excused case) and Poisson in the calls, are the
limits of section 6.1: an A1-A3 entry fails on a second excused trial,
which needs two restarts among one entry's accessibility calls (at most 80
per entry in A1, 50 in A2 and 300 in A3 on one layer, all
`seq_long_mixed`), and a rung on a third. The probability that some A1-A3
entry reaches its limit is 0.004 at the development rate, 0.015 at half A7's
bound (2.5 x 10^-4) and 0.057 at the bound; that some rung exceeds two
excused trials, 0.013, 0.083 and 0.37; and that the N = 40 rung does, which
alone keeps N* below 40 (concurrency rule below), 0.007, 0.044 and 0.21.
Not sized, as for A4 (design decision 40): a restart outside an observation
call, or one slower than `DesktopEnv`'s retries (about 10 s against a
measured 5.6 to 6.0 s), still counts in the trial it hits, and one during a
post guard can cost the next entry too. D33 states this remainder and
accepts it. Counting the limit per observation setting and per shuffle
instead (design decision 44) would change these probabilities by less than
10^-4, because only the accessibility setting calls the service.

**Other sizes.** Gym-anything PR #53 reports intermittent entries failing
4-20% of the time that 5 repetitions missed; the 60-repetition stress subset
(A3) detects a 5% failure rate with probability 1 − 0.95^60 = 95.4%, and the
20 A1 repetitions per entry detect a 10% rate with probability 1 − 0.9^20 =
87.8%. With one repetition excused (decision D33) an entry keeps 59 and 19
counted repetitions: 95.2% and 86.5%.

**Cost.** Sized in `vm_hours.json` (`vm_hours.py`, design decision 33) from
the measured times of the final development runs at the candidate executor
(jobs 609, 633, 611, 635, 612, 636, 620, 637; job 374 for the boot-reset
cycle). VM-hours count the time one VM is occupied; at concurrency N the
wall-clock time is about VM-hours / N when per-trial time does not grow with N
(the same 14 sessions had step p95 2.98 s on 8 VMs, job 610, and 2.83 s on
one, job 609). A session costs 24.6 s beyond its trials (cold boot to settled
screen, probe and tap, warm-up, reset observation, teardown) and a job 37 s.
A4's 64,028 trials average 2.06 s in its mix of entries and settings, so A4
needs 44.0 VM-hours: about 44 hours of wall-clock time at N = 1, 5.5 at N = 8
and 1.1 at N = 40; whenever one job's worst-case budget exceeds the lane's
24-hour limit, A4 runs as several jobs over consecutive session ranges. A7's
30,960 accessibility-setting trials need 31.1 VM-hours (31 hours at N = 1,
split the same way; 3.9 at N = 8 and 0.8 at N = 40). The other campaigns: A1
1.5, A2 1.6, A3 4.8, A5 0.3, A6 0.9, C1 0.12, C2 0.25, C3 2.8 (44 mutants and
three reference runs) and the five ladder rungs 11.0; in all 98.4 VM-hours,
CPU only (no GPU is used anywhere in this experiment). Replaced before the
freeze: the draft estimated 40-80 VM-hours for A1-A4 from per-call latencies;
A7 (decision D30) raised the total from 67.3 VM-hours.

**Concurrency rule.** The ladder has rungs N = 8, 16, 24, 32 and 40; at N = 1
the reference is A1 (both shuffles, 36 cold boots). Rung N runs L0-fixed on N
concurrent VMs over the seed-43 order of the 100 entries extended to r_N
repetitions, the smallest r ≥ 5 that gives each observation setting at least
max(N, 10) sessions (`manifest.ladder_reps`: r_N = 6, 10, 14, 19 and 24, so
1,200, 2,000, 2,800, 3,800 and 4,800 trials in 20, 34, 48, 64 and 80
sessions). Every one of its N VMs is therefore busy at once and it has at
least 20 cold boots; its first five repetitions are A1's seed-43 shuffle (the
order of `order.py` is built repetition by repetition from one generator). N*
is the largest rung N that qualifies, and 1 when none does (A1 gates N = 1
itself). A rung qualifies when: at least 20 cold boots were measured; boot p95
(container start to first valid `/screenshot`) ≤ 180 s; step p95 (one
`DesktopEnv.step`, both settings pooled, excused trials included) ≤ 2 x A1's
step p95 (both shuffles pooled, excused trials included); every counted
gating trial passes (non-gating entries are reported); at most two of its
trials were excused for a guest-server restart (decision D33, section 6.1);
its campaigns count under section 6.1; and no foreign-load abort occurred. A rung
aborts if, at any of the host snapshots the driver takes before and after
every session, a Slurm job other than the rung's own is running that was not
running at the rung's first snapshot (a foreign job started), or the running
foreign Slurm jobs hold more than 8 CPUs in total (foreign load); the
snapshots go into the receipt. The abort is decided by `acceptance.foreign_abort`
from those snapshots alone, never by the operator, and while a rung runs the
operator submits no Slurm job of any kind. An aborted rung is rerun once as a
new attempt and both attempts are reported; the aborted attempt neither
qualifies nor disqualifies its N, and its failed and excused trials are
reported but not counted (the one exception to section 6.1's rule; D33 left
the abort rule unchanged). A rung that aborts twice,
or a rung that ran without aborting and is rerun anyway, does not qualify.
VMs are pinned to CPUs from their Slurm allocation; the ladder never exceeds
160 vCPUs. The N runners of a rung (and of A4 and A7 at N*) share
`manifest.runner_cpus(N)` CPUs, half a CPU per runner rounded up, at most 20
(1, 4, 8, 12, 16 and 20 CPUs at N = 1, 8, 16, 24, 32 and 40; development at
N = 8 used 4), so a rung's step p95 measures the VMs rather than starved
runners; `manifest.py` refuses any other count for a scored campaign, and
every receipt records the CPU sets (design decision 38). If N* < 40, the
program kill criterion applies: cut the Stage-1 task count before adding
GPUs. Changed before the freeze: the draft ran each rung
on A1's seed-43 shuffle alone, 18 sessions, which can never show 20 cold boots
and never loads more than 18 VMs, so no rung above N = 1 could have qualified
(design decision 29).

## 10. Seeds, order and the development/acceptance split

- **Order.** For shuffle seed s, the run order is built with
  `rng = random.Random(s)`; for each of the 5 repetitions, `ids` = the 100
  catalog IDs in catalog order, `rng.shuffle(ids)`, appended. It is computed
  by Python 3.10.12 in the runner image, and the realized order file's SHA-256
  goes into each receipt. The order is cut into sessions as in section 7.
- **Seed 42: development, never evidence.** Catalog order and the seed-42
  shuffle; L0-fixed, the adapters and the canary target coordinates may be
  iterated freely, and suite development may run sessions on concurrent
  VMs. Only L0-fixed, H-OSW-fixed, H-GA and the canary run in development;
  L0-raw and the detection controls never do (`manifest.py` refuses them).
  The inputs addendum lists every change to its components made after an
  L0-fixed development run. C2 is scored once at seed 42 after the inputs
  addendum; C1 and C3 are scored once after the executor addendum (section
  8). Seeds 43 and 44 are refused for every campaign until the ledger admits
  acceptance.
- **Freeze of the executor.** When development ends, the git SHA of L0-fixed
  and the adapters is frozen in `q2-action-path-v1-executor`. The ledger row
  is written after that commit, so scored campaigns run from an export of the
  later commit that records the row; what ties that export to the frozen code
  is the admission check of every pinned file's content (design decision 35),
  not the SHA the manifest names.
- **Seeds 43 and 44: acceptance.** Fresh VMs (every session is a cold boot of
  a new container), the frozen executor SHA, both observation settings.
  Stress, volume, observation-service (A7) and canary orders use
  `random.Random(43)`. There is no unseeded randomness.

## 11. Repairs and kill criteria

- A failed acceptance attempt is repaired only as a new versioned attempt
  (`-a2`, then `-a3`) with a new output path and a new executor SHA frozen in a
  new executor addendum, `q2-action-path-v1-executor-a2` (then `-a3`), at
  `program/preregistrations/q2-action-path-v1-executor-a2.md`; a campaign's
  `workload.attempt` names the addendum `manifest.py` requires
  (`manifest.executor_addendum`). The catalog, its references, G, the volume
  plan, the canary and the predictions stay frozen, and so do the inputs
  addendum's components (probe, guard, judge, analysis and lane): a repair
  that needs one of them changed is a new preregistration. A repair attempt
  is not a rerun (section 6.1): it changes the executor, and every earlier
  attempt is reported. A repair attempt is judged on its own campaigns and
  their reruns: neither the failed nor the excused trials of an earlier
  repair attempt carry over to it (decision D33's limits count within one
  repair attempt, over its reruns, section 6.1).
- An entry that fails only on D33's limit (`RESTART_LIMIT`: a second
  trial excused for a guest-server restart) fails its criterion like any
  other failure. It is reported as an observation-service fault, which no
  executor change addresses; a counted campaign is never rerun (section
  6.1), so only a repair attempt runs that criterion again, and its report
  says the earlier attempt failed on that limit alone.
- If any gating entry still fails at the third attempt, the affected layer is
  not admitted and Stage 1 does not start.
- A failed validity control (C1-C4) is not repaired within v1; the suite is
  invalid and a corrected suite is a new preregistration (`manifest.py`
  refuses a C1-C3 campaign with an attempt other than 1).
- A7 has no repair attempt either: a repair changes the executor, never the
  upstream observation service A7 bounds, so A7's attempt-1 result stands for
  every later attempt (`manifest.py` refuses an A7 campaign with an attempt
  other than 1, and `acceptance.a7` refuses one too). A campaign that did not
  count may still be rerun once under section 6.1. A7 runs at attempt 1's N*:
  `acceptance.n_star` over attempt 1's A1 campaigns and attempt 1's ladder,
  which runs in full before A7 is submitted, whatever attempt 1's other
  results (a rung qualifies only when its gating trials pass, so a ladder run
  under a failing executor can give N* = 1, and A7 then runs at N = 1 in
  session-range jobs as A4 does). If attempt 1 is repaired before A7 has run,
  A7 still runs from an export of the attempt-1 source at that N*. A7 is
  judged once, at that N*: a repair attempt whose ladder gives another N*
  neither reruns nor re-judges it, and the report gives both values. Its
  call count is the counting attempt's, capped at the plan's 39,036
  (decision D33, which confirms these A7 rules). Stage 1 counts restarts per
  episode at its own concurrency in any case (section 7).
- If the reset sentinel fails, it is debugged before any concurrency work.
- A finding that a harness "bug" is a design difference goes into
  `harness_design_diffs.md` and never relaxes a verdict after the fact.

## 12. Reported regardless of outcome

Per-entry tables for every layer, attempt, shuffle and observation setting,
including development-run counts; FLAKY entries with their pass fractions;
infrastructure failures by type, including unverified tap ranges; the
mutation score per operator and per layer with the observed killers next to
the predicted ones, and every excluded or not-applicable pair with its
reason, each mutant's cells that failed with an infrastructure failure, and
each cell the unmutated reference did not pass cleanly; the statement that
C3 repeated development's conditions; the L0-raw prediction table against the
observed results under C2's rule and under section 5 as written; the R-dev
reference stability per entry; which entries rest on a self-specified oracle;
per-app canary results; the A4 per-class action counts and bounds, per-entry
bounds and per-session results; the concurrency table (boot p50/p95, step
p50/p95, CPU steal and utilization, overlay growth, pass rate per rung, the
host snapshots and any aborted rung with its reason); observation retries by
type; each session's warm-up and reset-observation records, with the trials
charged for an undelivered reset observation; every attempt of every
campaign, rerun or repaired, with its end state (batch record and, when read,
Slurm state) and its failed trials; every guest-server restart with the
entry it hit (inside the entry or across the session's reset observation),
its session, any probe or tap relaunch and, in A1-A4 and the ladder,
whether the trial counted or was excused (decisions D30 and D33), so every
excused trial is listed in its criterion's restart report; per criterion
and per rung, the number of excused trials over every attempt, and in A1-A3
each entry over its limit (`RESTART_LIMIT`) with its excused repetitions;
every session whose restarts exceed those attributed to its trials
(a restart that hit no trial); restarts and accessibility calls per session
and per campaign; A7's restarts, calls (of the counting attempts before and
after the cap at the plan's 39,036, and of every attempt), rate, upper
bound and restarts per session, and the N* it ran at next to any later
attempt's N*;
the development restart rate with its exact interval; every design
difference per harness; every non-gating entry's results; and the certified
keysym set.

## 13. Infrastructure validation already done (not evidence for A1-A6)

Allowed before the freeze and reported as infrastructure validation only:

- Job 369 (2 cycles) and job 374 (22 cycles): cold boots in the `none-netns`
  layout with boot time, settle time, guest facts, reset sentinel (file, dconf
  key, gsettings key), latency of `/screenshot`, `/accessibility` and
  `/execute`, and HMP input reachability (section 4.3).
- Jobs 387 and 393: the R-dev reference capture (section 4.3); oracle
  construction, no system under test.
- Job 372 (2 cycles): the bridge-unpublished fallback. A separate container
  on Docker's default bridge reached the guest's `/platform` through the
  image's DNAT (HTTP 200), which is the exposure decision D13 records; the
  fallback is therefore not used.
- Job 456 (3 cycles, run by the reviewer at a4c76ca): reproduced job 374's
  boot, sentinel and HMP results.
- Jobs 467, 469, 470 and 471 (15 cycles): the tap's oracle self-test
  (section 4.4). One spare keycode remapped to `eacute`, U+0416 and NoSymbol
  and pressed with XTest after each change: the tap reported all six events'
  keysyms correctly in 15 of 15 cycles, where a keymap read at tap start gives
  0x0 for all six. The first three jobs failed their gate on the mapping
  check, which was refined twice (unexplained MappingNotify events judged by
  content, then under the core protocol's keysym-list rules after job 470
  showed XKB's four-column form of the same row); job 471 (5 cycles) passed
  every gate. Summaries: `program/evidence/2026-10-07/q2-action-path-stage0b/`.
- Job 468: the R-dev plan re-captured with the rewritten tap: 35 of 35
  entries stable, and every projection identical to job 393's, so the
  reference file is unchanged.

## 14. Design decisions

Each was open in the reviewed plan or raised by the review, and is settled
here with its reason.

1. **Lane:** CPU-only Slurm jobs through `vm-campaign.sbatch` (decision D12).
   The shared Docker submitter requires a GPU.
2. **Network:** `--network none` for the VM container with the image's NAT on
   loopback, and the runner in the VM's namespace. Stronger than D13's
   default: the guest is unreachable from every other container (measured in
   job 372 for the bridge alternative) and has no egress, so the suite is
   web-free by construction. No Docker network is created (D13).
3. **H-GA is aae6f7607 unmodified.** Its documented deviations (one-point
   drags degrade to a two-point drag at the target, no hscroll, coordinate-less
   middle, double and triple clicks dropped, scroll magnitude clamped to 10,
   terminate failure reported through metadata) fall outside its own prompt's
   spec, are declared by it, or are handled by the adapter, so they are
   excluded from its expressible set with a recorded effect rather than
   patched. Patching would turn it into a different harness.
4. **H-OSW-fixed fixes only own-spec bugs.** Terminate failure, key names and
   non-ASCII text are fixed; triple-as-double and hscroll-as-scroll are
   declared in its own prompt and stay as design differences; `keys` on
   clicks and coordinates on scroll are not in its prompt and are not added.
5. **Step pause 0.0 s**, the upstream Stage-1 run-script value, so the
   visual check tests the screenshots Stage 1 will see.
6. **L0-raw uses natural PyAutoGUI calls with PyAutoGUI's own names** for
   keys and buttons (where one exists), so it tests the runtime path rather
   than a harness's name mapping; harness name mapping is tested at the
   harness layer. Buttons 8 and 9 have no PyAutoGUI name and are passed as
   integers; PyAutoGUI 0.9.54 `_normalizeButton` calls `button.lower()` first,
   so those calls raise before sending anything. The draft passed every
   button as an integer, which would have failed every click for a reason
   unrelated to the runtime; the translator is now code frozen with this file.
7. **Volume is planned per action class, not uniformly over G.** A mined
   Qwen3.5 action mix would need a range read of a 25.3 GB archive and would
   still be another harness's mix; a bound that holds for every class holds
   for every mix. Seven classes plus the per-boot bound at family-wise 95%
   give 10,148 actions per class and 1,013 sessions (section 9).
8. **Menu key reference uses QEMU qcode `compose`.** Measured: qcode `menu`
   gives no X event, `compose` gives keysym Menu (keycode 135).
9. **Keymap-dependent predictions use the measured keymap.** C2 predicts
   `type_symbols_shifted` passes because keycode 94 carries `less` at index 0
   in this guest (xmodmap, job 374) and b138d348 excludes `<` from its Linux
   shift set.
10. **Infrastructure failures count as failures** for gating and are
    reported separately, never excluded, with one exception decided before
    the freeze: a trial excused for a guest-server restart in A1-A4 and the
    ladder (decisions D30 and D33; design decisions 40 and 44).
11. **Pointer entries keep a self-specified oracle, labelled as such.** An
    R-dev reference through HMP cannot reproduce them: `mouse_move` is
    relative and passes through the guest's pointer acceleration, so HMP
    cannot place a press at a catalog coordinate; `sendkey` releases its keys
    on its own timer, so a modifier held across a button event (the Table 20
    order) cannot be produced deterministically; the gap bounds would measure
    monitor latency; and HMP pointer input passes through evdev and libinput
    (where, for example, natural scrolling applies) while XTest does not, so
    it is a different path. What an independent device can check, button and
    wheel numbering, was checked in job 374 and matches the catalog.
12. **IR-boundary clamp.** Harness coordinates are clamped to the screen
    before they become IR (`ir.clamp_point`), which reproduces what X does
    with PyAutoGUI's off-screen point upstream; without it R14 would fail by
    construction in both harnesses, and with it R14 is judged exactly so
    that M24 stays killable.
13. **The IR accepts every X keysym name; certification covers 33.** A closed
    table would make legitimate Stage-1 key actions fail at the IR boundary
    without being counted; accepting every name and certifying a stated set
    moves that exposure into an explicit Stage-1 count.
14. **C2 is strict.** Any deviation from the frozen prediction invalidates
    v1. The alternative, reporting a deviation without consequence, would
    let an unexplained miss in either direction pass as a footnote.
15. **C3 scores L0-fixed and the two Stage-1 parsers only**, with per-layer
    kill cells; the detection controls are not mutated, and a mutant that can
    change only outside-spec cells is excluded by name before any run.
16. **The guard parks the pointer** at (1234, 777) before every entry, so an
    entry's motion never depends on where the previous entry left the
    pointer.
17. **The tap tracks keymap changes in the RECORD stream** (core
    `ChangeKeyboardMapping` requests) instead of trusting a per-connection
    cache, and judges other MappingNotify events by content; the planned
    executor types Unicode by remapping spare keycodes, which the old tap
    would have projected as 0x0.
18. **The runner image is kept as a saved tarball** because its Dockerfile's
    apt step is not reproducible; the lock records every package version.
19. **Entry windows are delimited by requests, not timestamps.** The probe
    opens and closes each entry with a core `ChangeKeyboardMapping` request on
    a reserved spare keycode and processes its queue up to the MappingNotify
    it causes; the tap records the same request. The X server orders requests
    and device events in one sequence, so the probe's log and the XRecord
    stream split at exactly the same point (validated in job 484: 153
    delimiter requests, each matched in both channels). Server timestamps were
    rejected because a property-change time need not be fresher than the last
    input event's.
20. **The guard re-activates the probe after every restoration** that can take
    its focus (screencast, closed, shown or switched windows, the hot
    corner), and R13's Super key, which opens the shell's overview, is
    restored like the hot corner. Without it the guard would charge the next
    entry with a focus loss the restoration did not undo.
21. **The marker check includes the compositor.** The probe's marker is read
    from the screenshot the entry's last `DesktopEnv.step` returns, so the
    compositor's latency counts against the action path: in development the
    probe's drawing reached the screen 72 ms after it was made at the median
    and 110 ms at the 99th percentile (784 measurements, runs 489-499). The
    probe's `begin` returns only once the screen shows the new marker, so
    an entry never starts from a stale screen.
22. **A2 runs the plain renderings; perturbations are judged at the IR
    level.** Each perturbation must parse to exactly the plain rendering's
    IR on every gating and declared cell (a test checks it for the frozen
    corpus); the same IR then runs on the same executor, so a VM run of each
    perturbation would add nothing. H-GA's R10 differs between perturbations
    (its parser waits one second when a call it does not know comes without an
    `Action:` line); R10 is outside H-GA's spec.
23. **H-OSW-fixed has five own-spec fixes, not three.** Development found two
    more bugs against its own prompt, fixed by the same rule: `type` lost edge
    whitespace (upstream stripped every parameter; `type_spaces` could never
    pass), and `wait` ignored its `time` (upstream `WAIT` sleeps
    `DesktopEnv.step`'s `pause`, 0.0 s in Stage 1; run 491's
    `click_double_slow` clicks came 381 ms apart against a 500 ms minimum).
    Both are marked in the source and listed in `harness_design_diffs.md`.
24. **L0-fixed waits for its effect to be visible.** Keys and chords are held
    0.1 s (QEMU `sendkey`'s hold in the R-dev capture; run 486's
    `chord_ctrl_alt_shift_r` released its keys 10 ms after pressing them while
    the shell opened its screenshot UI, and the releases lost their modifier
    state). Every action then waits for the desktop shell to answer on D-Bus,
    re-damages every viewable top-level window (XDamage `DamageAdd`, so the
    compositor repaints each from its current contents), and waits for the
    screen to be unchanged for 0.25 s (the root window's image read every
    50 ms, as `/screenshot` reads it; at least 0.1 s, PyAutoGUI's default
    pause, at most 2 s). Text that needs spare keycodes remaps them in one
    burst first and waits until the shell is idle, because the shell (the
    compositor) repaints nothing while it rebuilds its keymap (runs 486-499:
    screenshots after Unicode typing showed only the first character). Without
    the repaint request, the probe's last drawing never reached the screen in
    31 of 941 typing trials (runs 504-541, where the quiet wait saw no change
    for 0.3 s and the drawing was still missing 2 s later); with it, none of
    the 2,114 typing trials of runs 545-637 did (one-sided 95% upper bound
    0.14%).
25. **Build order.** The inputs addendum's components were written in the same
    development pass as L0-fixed, before any freeze, not before it as the
    first draft said. The protection that remains is the one the controls
    need: C2 is scored once after the inputs freeze, with the L0-raw
    translator and prediction frozen here; C1 and C3 are scored once after
    the executor freeze, with the control translators frozen in the inputs
    addendum; and every change to an inputs component after the first L0-fixed
    run is listed in that addendum.
26. **Acceptance is admitted by the ledger.** `manifest.py` admits an
    acceptance or scored-control campaign only when
    `program/preregistrations/ledger.jsonl` (hash chain verified) freezes this
    file and the addenda it needs with the digests the manifest names and the
    source tree holds, and every file their frozen tables pin holds its
    digest there (decision 35); the submitter and the job both check. The
    acceptance code is therefore frozen in the addenda and needs no change
    after the freeze. Seeds 43 and 44 are refused for every other campaign,
    and development admits only L0-fixed, H-OSW-fixed, H-GA and the canary.
27. **The corpus uses one tool call per turn.** Both prompts ask for a single
    call per step; a positioned H-OSW scroll and a two-point H-OSW drag take a
    `mouse_move` turn first. Multi-call turns appear only in R05-R07, which
    test them.
28. **Canary targets are measured from screenshots.** LibreOffice's
    accessibility extents had the right x but a y 24 px too high (run 501);
    Chrome's agreed with its screenshots. `canary_targets.json` records each
    app's targets and how they were measured.
29. **Ladder rungs load every VM.** Rung N repeats the seed-43 order until
    each setting has max(N, 10) sessions (section 9). A rung that ran A1's
    seed-43 shuffle alone (18 sessions) could never show the 20 cold boots
    the rule asks for, and above N = 18 could not load N VMs at once, so its
    N* would have been 1 by construction. The extra repetitions extend the
    same order, so the rung still contains A1's seed-43 shuffle.
30. **Observations as Stage 1 sees them.** Each session takes
    `DesktopEnv.reset`'s observation before its first trial (a Stage-1 episode
    always starts with one, so its first step never makes the boot's first
    `/accessibility` call), and an observation counts as an infrastructure
    failure only when `DesktopEnv`'s own retries do not deliver it (section
    6.1); every retry is reported. A delivered retry gives the agent the same
    screenshot or a tree taken 5 s later from a screen that has been quiet
    since the action; it changes neither the desktop's input nor what the
    agent is shown. `/execute` keeps the strict rule because a retried
    `/execute` can run an action twice.
31. **Session warm-up.** The X server's master keyboard follows the slave
    device that sent the last key event. A boot leaves it on a device other
    than the XTest keyboard, so the session's first XTest key switches it, and
    the server re-sends the keymap and recomputes the modifier state at that
    moment. Development runs 549 and 574 (the same 14 sessions on 8 VMs and on
    one) showed `chord_super_d` fail in the two sessions whose first key event
    was its Super_L press: the `d` press arrived with state 0. Before any
    trial, the guard presses and releases a keycode that has no keysym and
    waits for the shell to be idle (`guard.py warmup`), so the switch happens
    outside every entry. Stage 1 runs the same warm-up once per boot, after
    `DesktopEnv.reset`; without it an agent's first key chord of an episode
    can lose its modifier.
32. **The acceptance analysis is code.** `acceptance.py` (frozen in the
    inputs addendum, before C2 is scored, and pinned again in the executor
    addendum) applies sections 5-9 to campaign receipts: end states,
    reruns, infrastructure gates, the realized order of each criterion, C2's
    reading of L0-raw trials, the kill and equivalence rules of C3 and the
    ladder's N*, including the foreign-load abort. The draft had prose rules
    and no code; a test drives every rule on synthetic campaigns. It was
    first frozen with the executor, after C2; the review of `2b492cd` noted
    that this would have left C2's analysis open after C2's data existed.
33. **Cost from measured trial times.** `vm_hours.py` sizes every scored
    campaign from the development runs' measured per-entry trial times and
    session overheads (section 9, "Cost"); `trial_times.json` and
    `vm_hours.json` are frozen in the executor addendum.
34. **C2 is judged on the event and text channels.** The prediction is about
    PyAutoGUI's key and button names and its handling of non-ASCII text,
    which change which events and text reach the guest. L0-raw also lacks
    every settling step development added to L0-fixed, so its screenshots
    can lag the probe's last drawing and its chords release their keys a few
    milliseconds after pressing them, while the shell may be grabbing the
    keyboard for a side effect. Development measured both on L0-fixed
    without those steps (section 8, C2), and neither is something the
    prediction could state from code reading. Under the strict section-5
    reading, C2 would have failed v1 with probability of about 0.84 or more
    on stale markers alone: L0-fixed with the quiet wait but without the
    repaint request lost the last drawing in 3.3% of typing trials, and C2
    runs 60 predicted-pass typing trials (12 entries, 5 repetitions) with
    neither (1 - 0.967^60 = 0.87). The rule keeps every predicted failure
    testable (each is a missing or wrong event or text) and leaves the
    transport as it is, so
    L0-raw is still the natural upstream call; giving it L0-fixed's settling
    would have made it a different control. The section-5 verdicts are
    reported beside it.
35. **Admission checks content, not only registrations.** `manifest.check_ledger`
    verifies, besides the ledger rows and the registrations' own digests,
    every file listed in the frozen table of each registration a campaign
    needs, in the exported source tree it runs from, and, for a campaign that
    needs the executor addendum, that no file under `harness/q2/` (Markdown
    aside; the package `__init__.py` files are pinned in the inputs addendum)
    is outside those tables. Before this, an edit to `l0_fixed.py` after the
    freeze, with the Markdown files unchanged, would have been admitted.
    The manifest's `git_sha` is not compared with the executor row's
    `git_head_at_freeze`: the row is written after that commit, so the export
    that holds the row is always a later commit; the content check is what
    binds the run to the frozen code.
36. **A C3 kill is a clean kill.** An infrastructure failure (a missing tap
    window, a guest-server restart, an absent probe) says nothing about the
    mutant, and a cell the unmutated code also fails cannot attribute its
    failure to the mutation. Kills are counted only from cells that fail
    without an infrastructure failure where the reference run passed
    cleanly; the rest is reported per mutant.
37. **End state and reruns are rules, not operator choices.** The batch
    script's own last record decides the end state when Slurm has forgotten
    the job; one rerun at most, only of a campaign that did not count; every
    failed trial of every attempt counts (section 6.1). Without this, a
    failing campaign could be cancelled and run again, and the Slurm state
    the analysis required could be lost minutes after the job ended.
38. **Runner CPUs are registered.** The N runners of a rung share
    `manifest.runner_cpus(N)` CPUs (section 9); the renderer's default was one
    CPU for any N, so a rung's step p95 could have measured runner starvation.
39. **A guest-server restart costs the entry it hits, not the session.** The
    restart stops the tap with the probe; the session relaunched only the
    probe, so every later trial of the session lost its oracle channel (55
    trials in run 622). The session now relaunches the tap into a new file
    when its process is gone, checks each tap's records against that tap's
    own keymap (`suite.segment_check`), and charges a restart that happens
    between entries to the next entry. Development run 662 killed the guest
    server on purpose after the tenth trial of each session: only the next
    trial failed in each session (inputs addendum, section 5). This changes
    no verdict rule; it changes how much of a session one restart costs.
    Since design decision 42 the probe and the tap survive a restart; the
    relaunch remains for a probe or tap that stops for another reason (the
    probe after `chord_alt_f4`, for example).
40. **A4 does not count guest-server restarts** (decision D30). A4 certifies
    the action path; a crash of OSWorld's guest server inside `/accessibility`
    is a fault of the upstream observation service, which Stage 1 runs
    unchanged, and patching the server would make the runtime differ from
    the one the leaderboard uses. At the development rate A4 as first
    registered would have failed with probability about 0.99 on this alone
    (section 16, item 9). The exclusion is narrow: only a trial whose
    reasons are the restart and, from that restart, an undelivered tree
    (its own, or the session's reset observation's when the server restarted
    across that observation; section 6.1); every other failure in that trial
    still counts and every restart is reported. Decision D33 extends the
    same exclusion to A1-A3 and the ladder (design decision 44); A6 and
    C1-C3 still count restarts. It also covers only a restart that
    `DesktopEnv`'s retries absorb.
    A restart inside an `/accessibility` call is excused when the server
    answers again before the entry's next call to it, which in practice
    means within the observation's own retries: they come about 5 s and 10 s
    after the failed attempt, and the server answered 5.6 to 6.0 s after a
    kill in development (runs 694 and 703, on a host at load average up to
    180), a margin of about 4 s. A restart that
    takes longer, or one that lands in an `/execute` call or a guard, leaves
    an `execute`, `screenshot` or `guard_script` failure in the trial it hits
    (a restart during a post guard can cost the next entry too, whose pre
    guard meets the restarting server), and A4 counts it. That remaining
    exposure is not sized: the one crash on record (run 622) came inside
    `/accessibility`, and the retry after the restart delivered the tree.
    Decision D33 states this remainder and accepts it, for A4 and for the
    criteria it extends the exclusion to.
    The development hook (`kill_guest_server_during_seq`) kills the server
    after an entry's last observation and waits for it before the post
    guard, so it shows that the scopes keep the oracle channels and that the
    restart-only reading works, not that the retries absorb a restart in a
    middle step's call; run 622 is the only instance of that.
41. **The observation service has its own bound, A7** (decision D30): at most
    5 x 10^-4 restarts per accessibility call on the exact one-sided 95%
    Poisson upper bound, from a campaign dedicated to it rather than from A4's
    accessibility half, so the bound has a registered size and power (section
    9: 39,036 calls; pass probability 0.81 at half the bound, at most 0.05 at
    the bound). It runs the suite's own sessions (L0-fixed on G), the kind
    of session the development rate came from. It gates the screenshot-plus-
    accessibility setting only, the one that calls the service, and has no
    repair attempt, because no executor repair changes the service; it runs
    at attempt 1's N* and is not re-judged when a later attempt's N* differs
    (section 11). Its k sums the restarts of every attempt and its n the
    calls of the counting attempts only, capped at the plan's 39,036 calls
    (decision D33), so cancelling a run heading for failure and rerunning it
    cannot help (decision 37's principle; pooling the calls would have raised
    the pass probability at the bound from 0.048 to about 0.071, section 9),
    and no record can divide by more calls than the plan makes.
42. **The probe and the tap run in their own systemd scope** (decision D30).
    The guest server's unit restarts on failure with the default
    `KillMode=control-group`, which stops every process the server launched,
    and so the oracle channels (run 622). `suite.SCOPE_LAUNCHER` starts each
    with `systemd-run --user --scope` (the server runs as the desktop user)
    and returns only once the process is in its scope; a launch that cannot
    reach its scope fails the session. The server is unchanged. Development
    runs 694 and 703 killed the server inside the tenth trial of each session
    and between the twentieth and the twenty-first: the probe and the tap
    kept running (no relaunch, one tap segment, mapping check clean), the
    trial killed inside failed with `guest_server_restart` alone, the trial
    after the kill between entries failed (its pre guard could not run), and
    every other trial passed (section 18).
43. **Stage 1 counts restarts per episode as infrastructure failures**
    (decision D30). The Stage-1 harness reads the guest server's restart
    counter around each episode, as the suite does around each session, so
    A7's bound and Stage 1's own count are measured the same way (section 7).
44. **A1-A3 and the ladder excuse restarts too, within limits** (decision
    D33). They certify the action path, as A4 does, and A7 now bounds the
    observation service on its own; under the strict rule one restart (no
    restart in their 16,639 accessibility calls has probability about 0.13
    at the development rate) would have failed the suite for a construct
    those criteria do not measure. The exclusion is A4's (design decision
    40, `acceptance.restart_only`), with limits A4 does not need: an A1-A3
    entry is judged on its counted repetitions and fails on a second
    excused trial, and a ladder rung with more than two excused trials does
    not qualify; excused trials' steps stay in the step p95, and the
    foreign-load abort is unchanged. An excused trial alone never makes an
    entry FLAKY. The limit's reading follows D33's text: an entry "needs all
    but at most one of its repetitions counted", and section 5 judges one
    entry over both observation settings, while section 9 counts A1's 20
    repetitions per entry over both shuffles. So the limit counts excused
    trials over all of an entry's repetitions in the criterion: both
    settings, every attempt and, in A1, both shuffles. A reading that
    allowed one excused trial per setting and per campaign would let an A1
    entry lose up to 4 of its 20 repetitions (2 shuffles x 2 settings),
    which D33's text rules out; it was not adopted (it changes the pass
    probabilities by less than 10^-4, section 9). An earlier attempt's
    failed trials now count only on the cells the criterion judges, as a
    counting attempt's would (section 6.1): before, an expected failure of
    an outside-spec R cell in an earlier A2 attempt failed every rerun.

## 15. Changes after the 2026-10-07 review

The review found the draft not ready to freeze. Each finding and its
disposition:

1. L0-raw prediction wrong for integer buttons: fixed (design decision 6;
   `l0_raw.py` frozen here; reasons corrected).
2. A4 power claim misstated: fixed (section 9 restated; per-class and
   per-boot plan, decision 7).
3. R14 and H-GA `scroll_down_25` failing by construction: fixed (decision 12;
   H-GA expressible set 79).
4. C3 kill semantics undefined for outside-spec cells and control parsers:
   fixed (section 8, decision 15).
5. Analysis choices left open: C2 rule chosen (decision 14); input digests in
   this file (section 2.2); control translators, tap and canary driver
   frozen before use (sections 2.2 and 8); canary fixtures and expected text
   frozen (`canary.yaml`).
6. Tap keymap snapshot never refreshed: fixed (section 4.4, decision 17;
   jobs 467-471).
7. Pointer oracles unlabelled: labelled self-specified, decision 11.
8. Closed IR keysym table: fixed (section 4.5, decision 13).
9. Tap structure followed an LGPL example without attribution: credited in
   the NOTICE and the tap rewritten.
10. Runner image not rebuildable: tarball and lock kept (decision 18).
11. Incomplete source table: completed in `harness/q2/README.md`.
12. Found while fixing: `move_only` could see no motion after
    `drag_vertical`; fixed by the pointer park (decision 16).
13. Found while fixing: the draft counted A1's gating trials at N = 1 as
    3,440 (and bounded them at 0.087%); 86 x 5 x 2 x 2 is 1,720. Section 7
    now gives the trial and session counts.

## 16. Changes found while finishing development (2026-10-07)

Development runs 486-637 (seed 42, never evidence; listed with their outcomes
in `program/evidence/2026-10-07/q2-action-path-stage0b/README.md`) and the
work of writing the acceptance code found these, all before any freeze:

1. The ladder could not qualify any rung above N = 1 (18 sessions per rung):
   rungs now repeat the seed-43 order (section 9, decision 29).
2. The judging code counted every retried `/screenshot` or `/accessibility`
   call as an infrastructure failure, which section 6.1 did not say; aligned
   with 6.1 and stated there, with retries reported (decision 30).
3. A session's first XTest key event changes the master keyboard device and
   can strip a chord's modifier (runs 549 and 574): every session now warms
   the keyboard up first (decision 31).
4. The compositor sometimes never painted the probe's last drawing after
   typing (31 of 941 typing trials, runs 504-541): L0-fixed now re-damages
   the top-level windows after every action (decision 24, executor addendum;
   0 of 2,114 typing trials since).
5. Chrome's "Can't update Chrome" bubble opened mid-trial and took the
   keyboard (run 522): `canary.yaml` starts Chrome with a flag that keeps it
   closed (A6).
6. No code implemented the acceptance rules, and no test exercised acceptance
   admission: both added (decision 32; `tests/test_q2_acceptance_admission.py`
   freezes a ledger with `scripts/preregister.py` in a temporary tree and
   checks that the repository's own ledger still refuses every acceptance
   campaign).
7. Campaigns other than the ladder and A4 now must run at N = 1 (section 7),
   which the draft implied but `manifest.py` did not enforce.
8. On a busy host VS Code showed its editor before it accepted input and
   dropped the first keys of three canary trials (run 613): the canary driver
   now also waits until the trial's processes are idle (A6, inputs addendum).
9. The guest server can crash inside `/accessibility`: OSWorld's handler
   walks the accessibility tree from a thread pool, and its systemd unit
   (`Restart=on-failure`, default `KillMode`) then stops every process the
   server launched, including the probe and the tap, and restarts the server
   5 s later. Run 622 saw this once in the 8,114 accessibility calls of runs
   484-622 (one later session charged with 55 failed trials, its tap gone;
   the first count, 7,969, missed some calls).
   A restart during an entry is now an infrastructure failure of its own
   type (section 6.1; the guard reports the server's process id). With that
   rate, A4's 64,028 zero-failure trials (36,515 accessibility calls:
   35,981 steps and 534 reset observations; first given as 36,550) would
   expect about 4.5 restarts, so A4 as registered would pass with
   probability about 0.01 on this alone; the rate rests on one event, and
   its exact 95% interval puts the expected number of restarts in A4
   between about 0.11 and 25 (pass probability between about 0.89 and
   zero). The rule is left as registered; whether to change the
   runtime, the observation settings or the criterion is the owner's decision
   before the freeze (the inputs addendum, section 6, lists the options).
   Since the review of `2b492cd` a restart costs the entry it hits, not the
   rest of the session (decision 39). Decided before the freeze as D30
   (section 18): A4 does not count restarts, A7 bounds them, the probe and
   the tap run in their own scope, and Stage 1 counts restarts per episode.
10. Writer once read back "done", the emoji, then a space, for "done", a
    space, then the emoji (run 620, on a loaded host): the two arrived in
    Writer in the other order although the executor typed them in order. That
    is 1 of the 336 Writer trials of the canary runs 501-632 (the 160 of jobs
    631 and 632, which typed each Writer entry five times, all passed). GNOME's
    input-method daemon (IBus) sits between X and GTK applications. Reported,
    not changed; at that rate A6's 80 Writer trials would see it with
    probability about 0.2.

## 17. Changes after the 2026-10-07 review of `2b492cd`

An independent review of the branch at `2b492cd` found it not ready to
freeze. Each finding and its disposition (the fix commits and development
runs 662-667 are in the inputs and executor addenda):

1. C2's prediction ignored the timing failures development had found in
   L0-fixed, so v1 would very likely have failed C2 for a reason unrelated to
   the names it tests: fixed by judging C2 on the event and text channels
   (section 8, decision 34). The prediction file is unchanged.
2. The A4 decision about guest-server restarts: still the owner's decision
   (state.json, pending decisions); taken afterwards as D30 (section 18). The single-event uncertainty is stated
   (section 16, item 9); a boot-time accessibility warm-up is added to the
   options, with the evidence against it; the tap is now relaunched with the
   probe, so a restart costs one entry (decision 39).
3. C3 counted infrastructure failures as kills, and its outcome was largely
   seen in development: kills are clean kills against a clean reference
   (decision 36), and the report says C3 repeats development's conditions
   (section 8).
4. The lane did not check the code it ran against the frozen digests:
   admission now checks every pinned file and, with the executor addendum,
   refuses unpinned files (decision 35). Comparing the manifest's `git_sha`
   with the executor row's git head was not adopted, because the row's own
   commit can never contain it (section 10).
5. Reruns, aborts and the Slurm end state left the operator choices: one
   rerun at most, only of a campaign that did not count, failures of every
   attempt count, the end state comes from the batch script's own record or
   the watcher `scripts/record_slurm_end_states.sh` (section 6.1, decision
   37); a rung aborts only on the snapshots, the
   operator submits nothing during a rung, and an aborted rung is rerun once
   (section 9); repair attempts name their executor addenda (section 11).
6. The reset observation was recorded but never judged: an undelivered one
   is an infrastructure failure charged to the session's first trial
   (section 6.1).
7. The template-rendering check was always skipped (no jinja2 in the dev
   extra): jinja2 added; the check runs.
8. M12 and M13 on H-OSW-fixed are comment-only patches: kept, scored and
   predicted equivalent, as negative controls of the equivalence rule, with
   the reason stated (section 8 and `mutation_operators.yaml`).
9. The ladder's runner CPUs were not registered: registered per N (section
   9, decision 38).
10. The branch had not merged main, the NOTICE was stale and ruff's exclusion
    covered the project-written H-OSW-fixed copy: main merged, NOTICE
    corrected, the copy linted with only its upstream typing style and line
    length exempt.
11. Found while fixing: C2 could not have been submitted between the inputs
    and the executor freeze, because `manifest.py` required both addenda in
    every acceptance manifest and the renderer omitted the unfrozen one; an
    acceptance manifest now carries the inputs addendum and, once frozen, the
    executor addendum, and each campaign's needs are checked
    (`check_ledger`).
12. Found while fixing: a restart between two entries left the guard before
    the next entry unable to run, so the restart was not typed; it is now
    charged to the next entry as `guest_server_restart` (section 6.1).

## 18. Changes applying decision D30 (2026-10-07)

Decision D30 (`program/decisions.md`) settled the question of section 16,
item 9 before the freeze. Applied on branch `stage0/q2-action-path-d30`:

1. **A4 does not count guest-server restarts** (sections 6.1 and 7, design
   decision 40; `acceptance.restart_only`, `acceptance.a4`). A trial whose
   only reasons are the restart and the tree it left undelivered is reported,
   not counted; every other failure counts. A4's verdict reports every
   restart, the trials they hit, A4's restarts and accessibility calls, and
   the development rate with its exact two-sided 95% interval (one restart in
   8,114 calls: 3.1 x 10^-6 to 6.9 x 10^-4 per call; `acceptance.development_rate`).
2. **A7, the observation-service bound** (sections 7 and 9, design decision
   41; `acceptance.a7`, `manifest.CRITERIA`, `vm_hours.py`): at most 5 x 10^-4
   restarts per accessibility call on the exact one-sided 95% Poisson upper
   bound, from a dedicated campaign of 39,036 planned calls (a pass allows 12
   restarts; pass probability 0.999 at the development rate, 0.81 at half the
   bound, at most 0.05 at the bound), 31.1 VM-hours, no repair attempt. It
   gates the screenshot-plus-accessibility setting of Stage 1.
3. **The probe and the tap run in their own systemd scope** (design decision
   42; `suite.SCOPE_LAUNCHER`), and each session records the server's unit and
   its restart counter; a development-only hook kills the server inside an
   entry (`kill_guest_server_during_seq`). Validated in development (seed 42
   only, `vm-campaign.sbatch`, CPU only; inputs addendum, section 5): runs 694
   (at `34f79e4`) and 703 (at `7653799`, the runtime commit) killed the server
   inside the tenth trial of each of two sessions, one per setting, and after
   the twentieth. In all four sessions the probe and the tap ran in scopes of
   the desktop user's manager (`user@1000.service/app.slice`) while the server
   ran in `system.slice/osworld.service`; neither was relaunched, each
   session's tap stream stayed one segment with a clean mapping check, and the
   server answered again 5.6 to 6.0 s after each kill. The trial killed inside
   failed with `guest_server_restart` alone, so A4 would not count it; the
   trial after the kill between entries failed (its pre guard met the
   restarting server, so its window never opened, and it is charged under
   decision 39); the other 26 trials of each session passed. Both runs
   counted two restarts in every session, by the unit's counter and by the
   server ids alike, and 38 accessibility calls in each accessibility
   session. The counter already read 1 when every session began: the server
   restarts once while the guest boots, before any session starts, and no
   session counts that restart. Why it always comes first: in all 34 suite
   sessions of jobs 694 and 703-707 the boot's facts read, taken once the
   boot had served its first valid screenshot and the screen had settled
   (guest uptime 14.7 to 17.8 s), named the same server process as the
   session's baseline check, its warm-up and every later guard report up to
   the injected kills, so the boot restart had happened before the boot
   completed; a session's first counter read comes after its tap, probe,
   baseline check and warm-up. The restart's cause is not recorded (the
   guest's journal is not kept). Should a boot restart ever come after a
   session's first counter read, both the counter and the server ids would
   count it, so it could add a restart to A7 (an error toward failing) but
   never hide one. The final validation at `7653799` (jobs
   704-708: L0-fixed on one VM and on 8 VMs, H-OSW-fixed, H-GA and the
   canary) passed every in-spec cell, with no restart in its 1,070
   accessibility calls (executor addendum, section 9).
4. **Stage 1 counts restarts per episode as infrastructure failures**
   (section 7, design decision 43).
5. **Every other rule was left unchanged by D30.** Section 6.1 still typed a
   restart during an entry as an infrastructure failure, and A1-A3 and the
   ladder still failed a trial it hit (A6 and C1-C3 run the screenshot
   setting, which makes no accessibility call). That was a real exposure,
   stated here so it was decided rather than discovered: at the development
   rate, A1-A3 and the five ladder rungs make 16,639 accessibility calls
   among them (A1 1,298, A2 1,452, A3 4,422, the rungs 9,467) and see no
   restart with probability about 0.13 (A1-A3 alone, 7,172 calls: 0.41). A
   restart there would have failed that criterion, or left that rung
   unqualified. A4's own exclusion has a remainder too (design decision 40):
   a restart outside an observation call, or one slower than `DesktopEnv`'s
   retries (about 10 s against a measured 5.6 to 6.0 s), still fails A4; it
   is not sized, because the one crash on record came inside
   `/accessibility` and its retry delivered. The owner decided both before
   the freeze as D33 (section 20): the exclusion extends to A1-A3 and the
   ladder, within limits, and the remainder is stated and accepted.
6. The frozen tables of all three registrations carry the digests of the
   changed files, and the executor addendum's byte-identity check names
   `7653799` (executor addendum, section 9).

## 19. Changes after the 2026-10-07 review of `13c6790`

An independent review of the D30 branch at `13c6790` found it not ready to
freeze. Each finding and its disposition:

1. The owner had not decided whether D30's exclusion extends to A1-A3 and
   the ladder (section 18, item 5). Confirmed: it was the owner's decision,
   not one this branch could make, so the branch was not called ready to
   freeze until it was taken. Decided before the freeze as D33
   (`program/decisions.md`) and applied in section 20: the exclusion
   extends to A1-A3 and the ladder within limits, and A4's remaining
   exposure (item 4 below) is stated and accepted.
2. A7 pooled the accessibility calls of every attempt, so cancelling a
   failing run and rerunning it raised A7's pass probability at the bound
   from 0.048 to about 0.071 (reproduced: 20,000 simulated runs per rate).
   Fixed: k sums the restarts of every attempt and n the calls of the
   counting attempts only (sections 6.1, 7 and 9, design decision 41;
   `acceptance.a7`, with a test of a cancelled attempt that pooling would
   have passed).
3. `restart_only` read only a trial's reasons, and the loader charged an
   undelivered reset observation to the first trial's infrastructure types
   but not its reasons, so a restart-only trial that had also lost its reset
   observation was excused. Fixed: the charge is a reason too, and
   `restart_only` requires both the types and the reasons to be excused. A
   restart across the reset observation that left only its tree
   undelivered is now excused on the same terms as one inside an entry
   (`acceptance.reset_restart`; section 6.1, design decision 40); a lost
   reset screenshot or a first pre guard that could not run still counts.
   Tests cover each case.
4. A4's exclusion covers only a restart inside an observation call that
   `DesktopEnv`'s retries absorb, and the development hook waits for the
   server before the post guard. Stated in design decision 40 and section
   18, item 5, and put to the owner, who accepted it in D33. The optional
   development job that would kill the server inside a middle step's
   `/accessibility` call is not run: it needs a new hook in `suite.py`, a file campaigns
   execute, and the executor addendum's rule (section 9 there) would then
   require new final development runs before the freeze; run 622 is the one
   observed instance of that path.
5. How A7 meets repair attempts and N* was not stated. Registered (section
   11): A7 runs under attempt 1 at attempt 1's N*, after attempt 1's full
   ladder, and is not rerun or re-judged when a later attempt's N* differs;
   `acceptance.a7` also refuses an A7 attempt other than 1. D33 confirms
   items 2, 3 and 5 as written here and adds the cap of A7's calls at the
   plan's 39,036 (section 20).
6. The restart report lacked each hit trial's session and the restarts that
   hit no trial. Fixed: each row carries its session (`cycle`) and where the
   restart came (entry or reset observation), and the report lists every
   session whose restarts exceed those attributed to its trials (section
   12).
7. Two text points. A4's accessibility calls are 36,515 (35,981 steps and
   534 reset observations), not 36,550 (section 16, item 9, and the inputs
   addendum, section 6; the probabilities do not change at the precision
   given). The boot restart's order is now explained from the 34 sessions'
   records (section 18, item 3); its cause is not recorded.

The only code changed is `acceptance.py` (commit `13ad91e`, with
`tests/test_q2_acceptance_analysis.py`), which no campaign executes; the
executor addendum's byte-identity check against `7653799` still lists only
`harness/q2/README.md` and `acceptance.py`. The fixed loader read
development runs 694 and 703-707 with the same results as before: two
restarts and two hit trials per fault-injection session (the trial killed
inside restart-only, the one after the kill between entries counted), no
restart elsewhere, no undelivered reset observation and no restart that hit
no trial.

## 20. Changes applying decision D33 (2026-10-07)

Decision D33 (`program/decisions.md`) settled the question of section 18,
item 5, before the freeze. Applied on branch `stage0/q2-action-path-d30`:

1. **A1-A3 and the ladder excuse restart-only trials** (sections 5, 6.1, 7
   and 9; design decisions 10, 40 and 44; `acceptance.restart_only`, `a1`,
   `a2`, `a3`, `rung`). The rule is A4's: a trial whose only failures are a
   guest-server restart during an observation call and the tree that
   restart left undelivered, or the same fault across the session's reset
   observation, is excused and reported. Any other failure in that trial
   counts, including one a restart during `/execute` or a guard leaves.
2. **A1-A3's limit.** An entry is judged on its counted repetitions, an
   excused trial alone never makes it FLAKY, and a second excused trial in
   one entry fails it (`RESTART_LIMIT`), counted over both observation
   settings, every attempt and, in A1, both shuffles. The working brief for
   this pass read the limit "per setting, per campaign"; D33's text ("needs
   all but at most one of its repetitions counted: a second excused trial
   in one entry counts as a failure") and section 5's entry over both
   settings rule that reading out, so the registered limit is per entry
   (design decision 44). Should the owner have meant the wider reading, D33
   is amended before the freeze; the pass probabilities differ by less than
   10^-4 (section 9).
3. **The ladder.** "Every gating trial passes" reads over a rung's counted
   gating trials; a rung with more than two excused trials, gating or not,
   over its attempts (an aborted attempt aside) does not qualify; excused
   trials' steps stay in the step p95 (the rung's and A1's); the
   foreign-load abort is unchanged.
4. **Reporting.** Every excused trial in A1-A3 and the ladder is listed in
   its criterion's restart report beside A4's and A7's, with the excused
   trials per criterion and rung and each entry over its limit (section
   12).
5. **A7.** The rules fixed at `13ad91e` (section 19) match D33's wording:
   restarts from every attempt, calls from the counting attempt only, A7 run
   under attempt 1 at attempt 1's N* and not re-judged. Added: n is capped
   at the plan's 39,036 calls (`acceptance.OBSERVATION_PLAN_CALLS`, which a
   test checks against the plan through `observation_plan_calls`), so a
   record showing more calls than the plan makes cannot lower the bound.
6. **Earlier attempts' failures** (found while applying D33). An earlier
   attempt's failed trials were counted on every cell, so an outside-spec R
   cell's expected failure in an earlier A2 attempt (R03 fails on both
   harnesses by design) would have failed every rerun of A2. They now count
   on the cells the criterion judges, less its excused trials, as a
   counting attempt's would (section 6.1).
7. **Exposure.** No restart in A1-A3 and the ladder (probability about 0.13
   at the development rate) is no longer a pass condition. What remains is
   in section 9: some A1-A3 entry reaches its limit with probability 0.004
   at the development rate (0.015 at half A7's bound, 0.057 at the bound),
   some rung exceeds two excused trials with probability 0.013 (0.083,
   0.37), and the N = 40 rung 0.007 (0.044, 0.21). The unsized remainder,
   restarts outside an observation call or slower than the retries and a
   post-guard restart that costs two entries, is stated with A4 (design
   decision 40) and accepted by D33.
8. **Code, tests and checks.** The only code changed is `acceptance.py`
   (commit `3ad255a`, with `tests/test_q2_acceptance_analysis.py`), which
   no campaign executes (no file of the lane imports it); the executor
   addendum's byte-identity check against `7653799` still lists only
   `harness/q2/README.md` and `acceptance.py`, and the frozen tables of both
   addenda carry its new digest. The tests drive each rule: an excused
   trial left out of its entry's k of k and never FLAKY; a second excused
   trial failing the entry in one setting, across the settings, across
   A1's shuffles and across a rerun, while one each in two entries passes;
   a restart during `/execute`, during a guard, slower than the retries or
   with an event difference still counting in A1, A3 and the ladder; a
   rung allowing two excused trials and refusing a third, counting a
   non-aborted earlier attempt's and not an aborted one's, and keeping
   excused steps in its step p95; an earlier attempt's failures counted
   only on judged cells; and A7's cap. The D33 loader read development runs
   694 and 703-708 (seed 42) again: the restart counts and hit trials are as
   before (two restarts per fault-injection session; the trial killed inside
   each session restart-only, now excused, and the trial after the kill
   between entries counted), with no restart in 704-708, no undelivered
   reset observation and no restart that hit no trial. The only status that
   changed is `chord_ctrl_c` in runs 694 and 703, killed inside in both of
   each run's sessions: FAIL becomes `RESTART_LIMIT` (two excused trials and
   no counted repetition, still a failure); read as a rung, its gating
   failures drop from `chord_ctrl_c` and `drag_short` to `drag_short`.
   Every other entry's status in 694 and 703-708 is unchanged.
