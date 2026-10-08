# q2-action-path-v2: action-path suite on the nested-KVM desktop runtime

**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger
row for the freeze time and `git_head_at_freeze`.** The three registrations
are frozen in this order, each with its own row: `q2-action-path-v2` (this
file), then `q2-action-path-v2-inputs`, then `q2-action-path-v2-executor`
(`uv run python scripts/preregister.py freeze` with each id and its path).
No acceptance trial and no C2, C1 or C3 run may run before this row exists.

- Experiment id: `q2-action-path-v2`, the successor of `q2-action-path-v1`
  (decision D40). v1's first scored campaign, C2 (job 768), failed, so v1 is
  invalid and no v1 acceptance criterion may be claimed. v2 keeps v1's
  catalog, oracles, executor, acceptance rules and development evidence, and
  changes three things (section 24): the L0-raw prediction's entry for
  `chord_super_d` is disclosed as informed by v1's C2 run; C2 is read as a
  reproduction test on a new order seed (45), with v1's C2 reported as the
  a-priori result (section 25); and the manifest renderer takes the host run
  root as a parameter. Section 26 reports the development (seed 42) that
  characterised v1's C2 failure: it is in the tap's record of a key event
  queued during the shell's keyboard grab, not in the chord's delivery,
  which corrects the cause D40 stated (decision D43). D43 also changes the
  judge: a key event the XRecord tap records without the lock bit the entry
  guard guarantees (Mod2, Num Lock), after a key press it records with that
  bit in the same entry (decision D45's narrowing), is judged on its kind,
  keycode, keysym and order, not its modifier state; C3's stream comparison
  reads it the same way (D45); and the guard now checks that bit (sections
  4.4, 5, 6.2 and 27). Under that rule `chord_super_d` is predicted to pass
  L0-raw, as v1 predicted, for a reason informed by v1's C2. No v1 data enters
  a v2 verdict.
- Question: Q2 (calibrated computer-use instrument), Stage 0b. Program kill
  criterion it implements: "No GPU episodes until the action-path suite passes
  100%" (`program/questions/q2-calibrated-cua-instrument.md`), read here as
  100% of the gating set G defined in section 4.
- Drafted: 2026-10-08, on branch `stage0/q2-action-path-v2`, from v1's frozen
  text (ledger row 8). v1 was drafted on 2026-10-07 on branch
  `stage0/q2-action-path`, revised the same day after an independent review
  (section 15), and again to apply decisions D30 and D33 on guest-server
  restarts and D39's freeze details before its freeze (branch
  `stage0/q2-action-path-d30`; sections 18, 20 and 23). Sections 15-23 are
  v1's history as v1 froze it; sections 24-27 are v2's.
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

- **`q2-action-path-v2-inputs`** (`program/preregistrations/q2-action-path-v2-inputs.md`),
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
- **`q2-action-path-v2-executor`** (`program/preregistrations/q2-action-path-v2-executor.md`),
  frozen when development ends and before the scored C1 and C3 runs and the
  first acceptance trial: the file digests of L0-fixed, the H-OSW-fixed and
  H-GA adapters, the acceptance workload code (`harness/q2/vm/*.py` and the
  batch script, pinned again), the regression corpus (`suite_cells.json` and
  its generator), the mutation kit, `harness_design_diffs.md`, the canary
  target coordinates (`canary_targets.json`), the acceptance analysis
  (`acceptance.py`, pinned again) and the VM-hour sizing with the measured
  trial times it uses (`vm_hours.py`, decision 33); its ledger row's git head
  is the executor SHA. A repair attempt k (section 11) runs under its own
  executor addendum (`q2-action-path-v2-executor-a2`, then `-a3`).

Both addenda were written in one development pass with L0-fixed, before any
freeze, not in the order the first draft gave (design decision 25). v2's
addenda are v1's with the changes their own "Changes from v1 (D40)" sections
list.
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
| `harness/q2/action_path/l0_raw_prediction_v2.yaml` | `5ce6beeb6736560e9a0fc9f84557aa3c9e35d7d30ac423b3541863613e35b489` |
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

Development for v2 found one limit of this channel (section 26), and decisions
D43 and D45 change how the judge reads it (section 27). A device event that
arrives while a synchronous grab has frozen the keyboard (GNOME Shell grabs
its overlay key and every keybinding that way) is recorded when the X server
queues it, before its state is computed, so its core state reads 0; the server
delivers it later from the queue with its state, and RECORD does not report it
again. Such an event is recorded in the order it arrived and on its keycode,
so its kind, keycode, keysym and position are observed and its modifier state
is not. Every key event the server processes inside an entry carries the
locked Mod2 bit, because the entry guard requires Num Lock locked before and
after every entry (section 6.2, conditions b and f) and no catalog entry
presses Num_Lock; development found exactly that in every record of the lane
(424 sessions: 172 of 519,344 tap key events lacked Mod2, every one after the
press that activates a shell grab and every one with state 0; none of 517,032
probe key events and 1,550 QEMU-monitor key events did). So the judge treats
the modifier state of a key event the tap recorded without Mod2, after a key
press it recorded with Mod2 in the same entry's window, as unobservable and
judges that event on its kind, keycode (through the keysym the tap resolves
from it) and order only (`verdict.modifier_state_observable`; decision D45
added the condition on the preceding press). A key event without Mod2 that no
such press precedes is judged on its state as recorded, as is every other
event, and every event on the probe's channel, which receives events after
their state is computed. The preceding press shows that the server was
processing the entry's events when it arrived, so an event after it that lacks
Mod2 was queued by a grab that activated after that press. Among the clients
this guest runs, as development observed them, a queued event needed an active
shell grab, and a shell grab activates only on the press of its grab key with
the modifiers its keybinding needs (Super_L, the overlay key, needs none):
each of the 280 key events recorded without Mod2 in development (the 172 above
and 108 in job 830, section 27) has state 0 and follows, in its own entry, the
processed press of the key that activates the shell's grab, so D45's condition
changes none of them. So a chord whose grab never activates, because its grab
key was never pressed or was pressed without those modifiers (as when a
modifier is dropped), is processed event by event and judged on its state. A
synchronous grab already active when an entry's first key arrives (any
client's; an active grab needs no key press, and the guard cannot see one)
would queue every key event of the entry, the first included: none would
follow a processed press, so each is judged on its recorded state, and a chord
fails (decision D45). That the grab which queued an event after a processed
press was the shell's, activated by the entry's own key, is what development
observed. That is a property of this guest's clients, not of the X server, and
neither the judge nor the guard checks it: a synchronous grab another client
activated inside an entry, after a processed press, would have the events it
queued read without their state too. Section 27 states the rule for an event
that lacks Mod2 for any other reason (its case 6 for a grab).

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
   On the XRecord stream a key event recorded without the lock bit the guard
   guarantees (Mod2), after a key press recorded with it in the same window,
   is matched on its kind, keycode, keysym and order, not its modifier state
   (decisions D43 and D45, section 4.4); a key event without Mod2 that no
   such press precedes is matched with its state as recorded. Each verdict
   reports the key events it read without their state
   (`state_not_observed`), which is never a failure.
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
record shows a restart during or after the entry's observation calls,
before its post guard, that cost the entry no action: one during an
observation call that `DesktopEnv`'s retries absorbed, or one after the
entry's last observation call that only the post guard sees. Excusing the
second kind is harmless: every action of the entry had completed, and been
observed, before the restart, and the trial shows no other failure, so the
action path was judged in full and showed no difference (the reason A4
counts such a trial's actions, section 9). Any other reason in that trial
counts as usual: a restart
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
repetitions in the criterion: both observation settings, every rerun
(below; a campaign's first run and its rerun, within one repair attempt,
section 11) and, in A1, both shuffles. An A1 entry can therefore lose at
most one of its 20 repetitions, an A2 cell one of its 10 and an A3 entry
one of its 60 on each layer (design decision 44 gives the reason for this
reading, which is the one D33 means). That limit is A1's at N = 1: A1 at
the operating concurrency N* > 1 is read from the ladder rung N* (section
7) under the rung's rule, which allows two excused trials in the rung,
even in one entry. A ladder rung reads "every gating trial passes" (section
9) over its counted gating trials and does not qualify with more than two
excused trials, gating or not, over every rerun (an aborted rung's trials
never count); an excused trial's steps stay in the rung's step p95, and in
A1's. A4 sets no limit on excused trials: A7 bounds the restarts, and
under a repair attempt, which A7 does not judge again, A4 reports its own
restarts per accessibility call against A7's bound (section 11). Every
excused trial is listed in its criterion's restart report beside A4's and
A7's (section 12).

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

**End state and reruns** (design decision 37). A campaign counts only when
it ended COMPLETED with exit code 0:0, its receipt's `infra_gates_pass` is
true, `System.qcow2` is unchanged and nothing labelled was left. Slurm
accounting is off on this host and Slurm forgets a finished job within
minutes, so the end state is read from the batch script's own last record
(`driver_exit=0 labelled_containers_left=0` in the run directory's
`preflight.txt`, written immediately before it exits 0; a job ended by a
signal, a time limit or a node failure never writes it) and, when the
operator or a watcher read it in time, from `scontrol show job`; when both
exist they must agree. A campaign that does not count may be rerun once, as
a new attempt with a new output path; a campaign that counted is never
rerun, and no campaign has a third attempt. In this section an attempt of a
campaign is one of its runs, the first or its rerun (the earlier attempt and
the counting attempt), always under one executor: a repair attempt (section
11) is a new executor version, never a rerun, and every rule here, D33's
limits included, runs within one repair attempt. A job killed before its
driver wrote its receipt (the driver writes it last) is still an attempt:
the analysis reads it from its manifest, its batch record and the sessions
it finished (`acceptance.load`), and it does not count; a session the kill
cut short left only unjudged trial records (the runner judges a session's
trials at its end, against the tap's stream), so its trials are reported as
not run. The driver and the runner write a run's receipt, cycle and record
files whole but not atomically, so a kill during a write can leave one cut
short. Such a file, one that does not parse, is read as missing (decision
D39): a receipt as no receipt, a cycle file as a session not run, a record
file as a session without host snapshots. The analysis lists each one
(`unreadable`), and the attempt does not count, so a write cut short can
never leave a criterion without a verdict. Every trial of every attempt is
reported, and a failed trial in an earlier attempt counts against its
criterion exactly as if the attempt had counted: cancelling or rerunning a
campaign never removes a failure, with one registered exception: C2 judges
its predicted cells on the counting attempt only (below), so an earlier
attempt's pass of a predicted cell is reported, not counted (the predicted
failures are deterministic mapping gaps). Like a counting attempt's trials, it
counts on the cells the criterion judges (G for A1 and the ladder, the
in-spec cells for A2, the stress entries for A3, every trial for A4 and A6)
and not when the criterion excuses it, and an earlier attempt's excused
trials count toward A1-A3's and the ladder's limits above, so a rerun never
resets them (decision D33). The validity controls read an earlier attempt's
trials by their own rules, because their known-defect cells, predicted
failures and kills fail by design and such a failure is not one against them
(design decision 45): in C1 each known-defect cell must fail in every trial
of every attempt (an earlier pass counts against C1, an earlier failure does
not, and C1 judges no other cell); in C2 an earlier failure counts only on a
cell outside the predicted set, read as C2 reads every trial
(`acceptance.c2_trial_pass`), and the predicted cells are judged on the
counting attempt; in C3 a mutant's kills are read from its counting attempt,
and it is equivalent only if its counting attempt's stream signature equals
the reference's and so does each earlier attempt's on every cell that
attempt ran without an infrastructure failure (decision D39; each earlier
attempt is reported), while a cell the unmutated reference failed, or failed
with an infrastructure failure, in any of the reference's attempts cannot
kill; C4 reads every A1 trial of every attempt. An earlier attempt never
supplies what a control needs (C1's and C2's required failures, C3's kills),
and it can take a C3 mutant's equivalence away, never give it. The only
exception is a concurrency-ladder rung aborted on foreign load (section 9);
a rung attempt missing its host snapshots is not aborted, and its trials
count. The same holds for A7's count of restarts, which sums the restarts of
every attempt but divides by the accessibility calls of the counting
attempts only, capped at the plan's 39,036 calls: an attempt that was
cancelled or did not count adds its restarts and none of its calls, so
stopping a run and rerunning it can never raise A7's chance of passing
(section 7, design decision 41). A5 is judged on the counting attempts'
receipts only: a killed job can leave labelled containers by design (a kill
or a node failure can skip the batch script's cleanup) and writes no
receipt, so judging an earlier attempt's receipt would let one killed job
fail A5 with no repair. Each earlier attempt's receipt (or its absence) is
reported with A5 (`acceptance.a5`, `earlier_attempts`), and that attempt,
which did not count, is read above.

### 6.2 Entry guard

Before and after every entry: (a) `XQueryKeymap` shows no pressed key and the
pointer shows no pressed button; (b) the LED mask equals the session baseline;
(c) the probe window is mapped, focused and covers 1920x1080 at (0, 0); (d) no
GNOME screen recording is running (no file in `~/Videos/Screencasts` is
growing); (f) Mod2, the modifier Num_Lock is mapped to, is in the logical
modifier state (`QueryPointer`'s mask; decision D43): with (a) and (b), whose
baseline has the Num Lock LED on in every development session, Num Lock is
locked, so every key event the server processes inside the entry carries
Mod2, which the judge relies on (section 4.4); (e) before the entry, outside
its window, the pointer is moved to
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
  That limit is A1's at N = 1. At N* > 1 the seed-43 shuffle is read from
  the rung N* under the rung's rule (section 9): at most two excused trials
  in the rung, which may both fall in one entry.
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
- **C2 (L0-raw failing set, a reproduction test in v2).** L0-raw fails
  exactly the set in `l0_raw_prediction_v2.yaml`: `type_unicode_bmp`,
  `type_emoji`, `type_rtl`, `type_combining`, `type_emoji_zwj`,
  `key_kp_enter`, `click_button_back` and `click_button_forward`; every other
  entry passes, notably every click, drag and hold on buttons 1-3,
  `type_shell_hostile`, `type_symbols_shifted` and `chord_super_d`. The
  failing set is v1's prediction, written from code reading before any
  L0-raw trial existed. `chord_super_d`'s pass is not predicted a priori: v1
  predicted it to pass, it failed 5 of 5 in v1's C2 (job 768), and v2
  predicts it to pass because of decision D43, taken after that run. Under
  L0-raw the tap records the `d` press, the `d` release and the Super_L
  release while they are queued during the shell's synchronous grab, without
  their state, after the Super_L press it records with Mod2 (section 4.4),
  and D43's judge, as D45 narrows it, reads them on kind, keycode, keysym
  and order, which the tap records correctly (the prediction file and
  section 27). **In v2, C2 is therefore a reproduction test of the L0-raw
  failing set on a new order seed, not an a-priori prediction test.** The
  a-priori result is v1's: one unpredicted failure, `chord_super_d`,
  recorded in the XRecord stream (the tap's `d` press has core state 0,
  without Mod4, in every repetition), and every other entry as predicted
  (section 25). Section 26 shows that this is how RECORD reports a key event
  queued during the shell's synchronous grab, and that the shell received
  Super+d: what failed is the oracle channel's record of a delivered chord
  (section 4.4), not the transport. Decision D43 corrects D40's statement
  that the failure was a genuine transport defect and has the judge stop
  reading the state of such an event; v1's verdict, judged by v1's rules,
  stands (section 25).
  An entry fails unless it is PASS in 5 of 5 repetitions, where an L0-raw
  trial is judged on the event and text channels (design decision 34): it is
  PASS under section 5's conditions 1, 2, 4 and 5 and the infrastructure rule
  of section 6.1, with two differences. Condition 3 (the marker in the last
  step's screenshot) is reported but not judged, and an R-dev projection is
  compared with the modifier state of every key release left out (key
  presses keep theirs, except that on the XRecord stream a key press
  recorded without the guard's lock bit after a key press recorded with it
  is compared without its state, as section 5 already reads it; decisions
  D43 and D45). Both are timing effects of the
  transport, not of the key and button names C2 predicts: L0-raw has none of
  L0-fixed's settling
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
  either direction invalidates the suite for q2-action-path-v2**; the
  investigation is reported but never rescues v2, and a corrected prediction
  can only enter a new preregistration. When: once, after the inputs addendum
  is frozen (it needs the probe, guard and marker), with the translator and
  the prediction frozen here, N = 1, screenshot setting, the 100 entries in
  the seed-45 shuffle: C2's own order seed, which no v1 campaign and no
  development run used (section 10, decision D40). v1's C2 a-priori result is
  reported beside v2's C2 (section 12).
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
  did not pass cleanly (in any of its attempts, section 6.1) never kills;
  both are reported per mutant. Outside-spec
  cells run and are reported but never kill. A mutant is equivalent only if
  its XRecord stream without timestamps, text buffer and terminal action are
  byte-identical to the unmutated code's on every cell of its layer in its
  counting attempt, and in each earlier attempt (section 6.1) on every cell
  that attempt ran without an infrastructure failure (decision D39): kills
  are read from the counting attempt only, and a stream that differed in an
  attempt that did not count keeps the mutant from being equivalent, so a
  rerun can never turn a survivor into an equivalent mutant. The comparison
  reads a recorded key event's state as the judge does (decision D45): the
  state of a key event recorded without the guard's lock bit after a key
  press recorded with it in the same window is not compared (its kind,
  keycode and keysym are), and every other byte is, the state of a key
  event without the bit that no such press precedes included (section 27).
  A mutant neither killed nor equivalent survives, whatever the reason.
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
  trial of every attempt (section 6.1), read as section 5 reads the XRecord
  stream (decisions D43 and D45: a key event recorded without the guard's
  lock bit after a key press recorded with it in the same window is
  compared on kind, keycode, keysym and order, not its state;
  `verdict.rdev_agreement`). Entries without a stable reference are listed
  as self-specified in every report.

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
instead (design decision 44) would lower the probability that some A1-A3
entry reaches its limit by about 8 x 10^-5 at the development rate, 3 x
10^-4 at half A7's bound and 1.2 x 10^-3 at the bound (0.0036, 0.0146 and
0.0557 instead of 0.0037, 0.0149 and 0.0569). Only A1's limit would change,
because only the accessibility setting calls the service and A2 and A3 run
one shuffle per layer; the rung probabilities are unchanged.

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
its campaigns count under section 6.1; every session's host snapshots are
present; and no foreign-load abort occurred. A rung
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
Only a foreign job starting and foreign load abort a rung. The driver
writes a session's host snapshots into its record file after the VM's
teardown, so a job killed while its first sessions ran, or a run directory
copied without its record files, lacks them for those sessions. Such an
attempt cannot show that no abort occurred, so it does not count for its
rung: it does not qualify and may be rerun once. It is not an abort, so its
failed and excused trials count under section 6.1
(`acceptance.snapshot_problems`; design decision 45).
A known limitation: the driver takes each snapshot's Slurm queue with
`squeue` without checking its exit status, and records only the other
jobs' rows (`squeue_foreign`). A `squeue` that exits non-zero with no
output therefore records no foreign job, which reads as no foreign load
(fail-open). The analysis cannot detect it: a snapshot keeps neither
`squeue`'s exit status nor the job's own row, which a successful `squeue`
always lists, so such a snapshot is indistinguishable from an idle queue
(checked on the snapshots of development runs 694 and 703-708, which hold
only the time, the load average, `squeue_foreign` and two container
counts). The driver is a file the campaigns execute and stays
byte-identical to `7653799` (executor addendum, section 9), so this is not
changed before the freeze. A `squeue` that times out or is missing raises
in the driver, and that job does not count. What guards against foreign
load in that case is the operator's rule above (no Slurm job is submitted
while a rung runs) and the snapshots' load averages and container counts,
which are reported, not judged.
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
  iterated freely, and suite development may run sessions on concurrent VMs.
  Only L0-fixed, H-OSW-fixed, H-GA, the canary and (in v2) L0-raw run in
  development; the detection controls never do (`manifest.py` refuses them).
  v1 refused L0-raw in development too, so that its C2 prediction stayed a
  priori; v2's C2 is a reproduction test (section 8), and decision D40 lets
  development characterise the mechanism of v1's C2 failure, at seed 42 only
  (section 26), where decision D43's judge rule, and decision D45's narrowing
  of it, were also developed and checked (section 27). The inputs addendum
  lists every change to its components made after an L0-fixed development run.
  C2 is scored once at seed 45 after the inputs addendum; C1 and C3 are scored
  once at seed 42 after the executor addendum (section 8). Seeds 43 and 44 are
  refused for every campaign until the ledger admits acceptance.
- **Seed 45: C2 only** (decision D40). No v1 campaign and no development run
  used it: v1's one scored campaign (C2, job 768) and the 124 run manifests
  of v1's development root used seed 42 or none, and 43 and 44 are the
  acceptance seeds. `order.py` builds an order from it only for criterion
  C2, and `manifest.py` admits it only in a C2 campaign (`CRITERIA`),
  refusing it, like 43 and 44, in every manifest that is not a scored
  campaign.
- **Freeze of the executor.** When development ends, the git SHA of L0-fixed
  and the adapters is frozen in `q2-action-path-v2-executor`. The ledger row
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
  new executor addendum, `q2-action-path-v2-executor-a2` (then `-a3`), at
  `program/preregistrations/q2-action-path-v2-executor-a2.md`; a campaign's
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
- A failed validity control (C1-C4) is not repaired within v2; the suite is
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
  episode at its own concurrency in any case (section 7). Because A7 is not
  judged again and A4 sets no limit on excused trials, a repair attempt's
  A4 report also gives A4's own restarts per accessibility call against
  A7's bound, on A7's rule (the restarts of every rerun, every session
  included, over the calls of the counting attempts, exact one-sided 95%
  bound): reported, not judged (`acceptance.repair_restart_rate`). An
  executor that itself caused restarts during observation calls would show
  there.
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
each cell the unmutated reference did not pass cleanly, and each mutant's
earlier attempts with their failed cells, whether their streams matched
the reference's, the cells whose stream differed without an infrastructure
failure (any of which keeps the mutant from being equivalent, decision
D39) and the cells left out for an infrastructure failure; the statement that
C3 repeated development's conditions; the L0-raw prediction table against the
observed results under C2's rule and under section 5 as written, with v1's C2
a-priori result (job 768, section 25) beside it and the statement that v2's
C2 is a reproduction test, not an a-priori one (decisions D40 and D43); every
trial, in every criterion and control, with a key event read without its
modifier state (decisions D43 and D45: each verdict's `state_not_observed`
for the channel it judges, and the same rule over every trial's XRecord
window, which C2, C3 and C4 read), by entry, with each such event's offset
from the preceding processed press (the latest key press recorded with Mod2
before it in its window) and that press's keysym, and every trial with a
key event recorded without Mod2 that no such press preceded, whose state was
judged as recorded (decision D45; section 27, case 6), both as
`acceptance.state_not_observed_report` gives them in every criterion's
analysis; the R-dev
reference stability per entry; which entries rest on a self-specified oracle;
per-app canary results; the A4 per-class action counts and bounds, per-entry
bounds and per-session results; the concurrency table (boot p50/p95, step
p50/p95, CPU steal and utilization, overlay growth, pass rate per rung, the
host snapshots, any aborted rung with its reason and any rung attempt
missing host snapshots); observation retries by
type; each session's warm-up and reset-observation records, with the trials
charged for an undelivered reset observation; every attempt of every
campaign, rerun or repaired, with its end state (batch record and, when read,
Slurm state), any run file that did not parse and was read as missing
(`unreadable`, section 6.1) and its failed trials; every guest-server
restart with the entry it hit (inside the entry or across the session's
reset observation), its session, any probe or tap relaunch and, in A1-A4
and the ladder, whether the trial counted or was excused (decisions D30
and D33), so every excused trial is listed in its criterion's restart
report; per criterion,
the number of excused trials over every rerun (A4's as well, beside those
of its counting attempts), and per rung over every rerun that did not
abort; aborted attempts' counts are in `earlier_attempts`; in A1-A3 every
entry with two or more excused trials, whatever its status (a counted
failure makes it FLAKY or FAIL first) and whether or not the criterion
judges it, with its
excused repetitions (`entries_over_restart_limit`); under a repair
attempt, A4's restarts per accessibility call against A7's bound (section
11); each earlier attempt's receipt, or its absence, with A5 (section 6.1);
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
    the suite version (v1, and in v2 the same rule on v2's prediction). The
    alternative, reporting a deviation without consequence, would let an
    unexplained miss in either direction pass as a footnote. v1's C2 failed
    under this rule (section 25).
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
    seed 45 for every campaign but C2 (decision D40), and development admits
    only L0-fixed, H-OSW-fixed, H-GA, the canary and (in v2, at seed 42)
    L0-raw.
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
    can lose its modifier. (Development for v2, section 26, reread runs 549
    and 574: their `d` press came 12-17 ms after Super_L and was recorded with
    state 0 while the shell still acted on Super+d, the signature of an event
    queued during the shell's synchronous grab; the slow device switch
    delayed the shell's answer past L0-fixed's 10 ms gap. The warm-up still
    moves that switch outside every entry.)
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
    settings, every rerun and, in A1, both shuffles. D33's author confirmed
    before the freeze that this per-entry reading is the one D33 means;
    decision D39 (`program/decisions.md`) records the confirmation. A
    reading that allowed one excused trial per setting and per campaign
    would let an A1
    entry lose up to 4 of its 20 repetitions (2 shuffles x 2 settings),
    which D33's text rules out; it was not adopted (it would lower the
    probability that some A1-A3 entry reaches its limit by about 8 x 10^-5
    at the development rate, 3 x 10^-4 at half A7's bound and 1.2 x 10^-3
    at the bound, section 9). An earlier attempt's
    failed trials now count only on the cells the criterion judges, as a
    counting attempt's would (section 6.1): before, an expected failure of
    an outside-spec R cell in an earlier A2 attempt failed every rerun.
45. **An earlier attempt is read by its criterion's own rule** (review of
    the D33 pass). Section 6.1 counts an earlier attempt's failed trials
    "exactly as if the attempt had counted". Read as every failed trial on
    every cell, that made every rerun of a validity control fail: C1's
    known-defect cells, C2's predicted failures and each mutant's kills fail
    by design, so one C1-C3 campaign that did not count (a boot over 300 s,
    a runner error, a time limit or a node failure, among about 50) would
    have invalidated the suite, and a failed control is not repaired within
    v2 (section 11). Each control now reads an earlier attempt by its own
    rule: a C1 defect that passed in any attempt fails C1, an unpredicted C2
    failure in any attempt fails C2, and a cell the C3 reference did not
    pass cleanly in any attempt cannot kill, while C1's and C2's required
    failures and C3's kills are read from the counting attempt. C3's
    equivalence fails closed (decision D39, section 23): the counting
    attempt's streams must equal the reference's on every cell, and each
    earlier attempt's on every cell it ran without an infrastructure
    failure. This pass had first read equivalence from the counting attempt
    alone, because an attempt that did not count may carry infrastructure
    failures (a lost tap window, for one) whose streams differ for reasons
    that say nothing about the mutant. That reason covers only the cells
    with an infrastructure failure, which are left out; on the others an
    earlier difference is as much the mutant's as a counting one, and
    ignoring it let a cancel and rerun turn a survivor whose stream varies
    between runs into an equivalent mutant, the rescue design decision 37
    rules out. Kills stay the counting attempt's, so an earlier attempt can
    take equivalence away and never supply a kill. C4,
    whose mismatches are never by design, now reads every attempt, as A1-A4
    do (section 21, item 4). The same review found that the ladder read a
    rung attempt with no host snapshots as a foreign-load abort, whose
    failed and excused trials do not count; section 9 registers two abort
    reasons and missing snapshots is neither, so a rerun could have dropped
    the gating failure or the excused trials of an attempt that otherwise
    counted. Such an attempt now counts its trials, does not qualify and may
    be rerun (`acceptance.snapshot_problems`).
46. **A killed attempt is read, and what an earlier attempt adds is
    reported** (section 22). The driver writes a campaign's receipt last,
    so a job ended by a signal, a time limit or a node failure, the usual
    reason for a rerun, has none (development runs 695-699). The analysis
    had opened the receipt unconditionally and could not have read such an
    attempt at all, which would have left any criterion with a killed
    earlier attempt without a verdict and the frozen analysis without a
    repair. Such an attempt is now read from its manifest, its batch record
    (whose `job_id=` line names the job) and its finished sessions, and it
    does not count. A5 judges the counting attempts' receipts only and
    reports the earlier attempts' (a killed job can leave labelled
    containers by design and has no receipt), and under a repair attempt A4
    reports its own restarts per accessibility call against A7's bound,
    because A7 is not judged again (section 11). Neither report is judged.
47. **The judge does not read a modifier state the tap could not observe**
    (decisions D43 and D45, v2; sections 4.4, 5 and 27). RECORD reports a key
    event that arrives while a synchronous shell grab has frozen the keyboard
    before the X server computes its state, so the tap's record of it reads
    state 0 although the shell received the chord. Keeping v1's reading would
    fail a trial whose chord was delivered whenever the shell answered later
    than the executor's next key: every L0-raw Super chord, and, at the
    development bound, a fraction of L0-fixed's A1, A2, A4 and ladder trials,
    after which the suite could fail on an artifact of its own oracle. The
    rule is narrow: it applies to key events on the tap's channel whose state
    lacks the one bit the guard guarantees in every processed event and that
    follow, in the same window, a key press recorded with that bit (decision
    D45); it leaves kind, keycode, keysym and order judged, and the probe's
    channel, which receives events after their state is computed, keeps every
    check. Every reading of the tap applies it the same way: the judge's
    channel for `raw-only` entries, C2's reading, C4 and, since D45, C3's
    equivalence comparison, which under D43 alone still compared the recorded
    state byte for byte and could fail C3 on a slow shell answer in a no-op
    mutant's run (section 27). The preceding processed press is D45's answer
    to a precondition D43's wording did not check: a synchronous grab already
    active when an entry's first key arrives queues every key event of the
    entry, the first included, and under D43 every one would have been read
    without its state, so a `raw-only` chord the server never processed could
    pass, while the guard cannot see a grab; under D45 none of them follows a
    processed press, each is judged on its recorded state, and the chord fails
    (section 27, case 6). What the rule still rests on, unchecked, is that a
    grab which activates inside an entry after a processed press is the
    shell's, activated by the entry's own key, as for each of the 280
    development events without Mod2; section 12 reports every event read
    without its state with its offset from that press. An alternative,
    observing the shell's side of a grabbed chord directly, would need a new
    oracle channel and its own development; whether a later registration
    should add one stays with Kevin.
48. **The guard guarantees the bit the judge relies on** (decision D43, v2).
    v1's guard checked the LED mask, which on this guest follows the locked
    Num Lock but is not the modifier state itself. Condition (f) requires Mod2
    in the logical modifier state before and after every entry; with (a) and
    (b) that is a locked Num Lock. A session whose baseline lacks it fails
    every trial at its guard rather than widening the judge's rule, and no
    development session did (424 of 424 had the Num Lock LED on and Mod2 set).
    The same bit marks the processed key press that D45's rule needs before an
    event it reads without its state. A development-only executor fault that
    drops a chord's modifiers (`fault_drop_modifier`, admitted for L0-fixed
    suite development at seed 42 only) gives the rule its negative case
    (section 27).
49. **D45: the rule needs a processed press, reaches C3, and is reported**
    (decision D45, v2; section 27). Two adversarial reviews of D43's
    implementation found that its rule rests on a precondition nothing checked
    (case 6 above) and that C3's equivalence comparison still read the state
    the judge does not, an oracle artifact of the kind D43 removed elsewhere.
    D45 decides: (i) an event is read without its state only when a key press
    recorded with Mod2 comes before it in the same window; (ii) the same rule
    applies inside C3's stream signature and earlier-attempt comparison; (iii)
    the analysis produces section 12's report of every event read without its
    state, with its offset from the preceding processed press, and of every
    event without Mod2 that no such press preceded. None of the 280
    development events read without their state changes. Because `verdict.py`,
    a file every campaign executes, changed, the seed-42 final development
    runs were repeated at `c74eae0` (jobs 845-854, section 27) and the
    executor addendum's byte-identity rule names that commit.

## 15. Changes after the 2026-10-07 review

Sections 15-23 are v1's history, kept as v1 froze it: their ids, branches,
commits and runs are v1's. v2's changes are in sections 24-27.

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
   settings, every rerun and, in A1, both shuffles. This per-entry reading
   is the one D33 means: D33's text says an entry "needs all but at most
   one of its repetitions counted: a second excused trial in one entry
   counts as a failure", section 5 judges one entry over both settings,
   and D33's author confirmed the reading before the freeze, as decision
   D39 records (sections 22 and 23; design decision 44). The working brief
   for this pass had read the limit "per setting, per campaign"; that
   reading is not registered. It would have lowered the probability that
   some A1-A3 entry reaches its limit by about 8 x 10^-5 at the
   development rate, 3 x 10^-4 at half A7's bound and 1.2 x 10^-3 at the
   bound, with the rung probabilities unchanged
   (section 9; first given here as less than 10^-4, which holds at the
   development rate only; section 21).
3. **The ladder.** "Every gating trial passes" reads over a rung's counted
   gating trials; a rung with more than two excused trials, gating or not,
   over every rerun (an aborted rung aside) does not qualify; excused
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
   excused steps in its step p95; a restart across the reset observation
   excused in A1 and the ladder, and the same lost tree without a restart
   across it counted; an earlier attempt's failures counted only on judged
   cells; and A7's cap. The D33 loader read development runs
   694 and 703-708 (seed 42) again: the restart counts and hit trials are as
   before (two restarts per fault-injection session; the trial killed inside
   each session restart-only, now excused, and the trial after the kill
   between entries counted), with no restart in 704-708, no undelivered
   reset observation and no restart that hit no trial. The only status that
   changed is `chord_ctrl_c` in runs 694 and 703, killed inside in both of
   each run's sessions: FAIL becomes `RESTART_LIMIT` (two excused trials and
   no counted repetition, still a failure). Read under the rung rule
   (`acceptance.rung`), 694's and 703's gating entries not PASS stay
   `chord_ctrl_c` and `drag_short`: the rung rule does not read a gating
   entry with no counted trial as passing, and `chord_ctrl_c` has none left
   (its two excused trials are within a rung's limit of two). A scored rung
   cannot reach that case: each entry runs at least 12 trials there
   (r_N >= 6 per setting) and at most two may be excused. Every other
   entry's status in 694 and 703-708 is unchanged.

## 21. Changes after the 2026-10-07 review of the D33 pass

The review of the D33 pass (branch head `59bd551`) found two defects in
the acceptance analysis and one wrong number, and fixing them found a
third defect; all are fixed before the freeze with no scored data (code in
`acceptance.py`, with `tests/test_q2_acceptance_analysis.py`, commits
`a3ee335` and `c9b4771`):

1. **Reruns of the validity controls** (section 6.1, design decision 45).
   C1-C3 counted every failed trial of an earlier attempt, so the expected
   failures of C1's known-defect cells, of C2's predicted set and of each
   mutant's kill cells made any rerun of a C1-C3 campaign fail its control,
   the mechanism section 20, item 6, fixed for A2. Each control now reads
   an earlier attempt by its own rule: C1 counts a known-defect cell that
   passed in an earlier attempt and never its failures; C2 counts an
   earlier failure only on a cell outside the predicted set, read by
   `c2_trial_pass`; C3 reads a mutant's kills and equivalence from the
   counting attempt and reports each earlier attempt (its failed cells and
   whether its streams matched the reference's), and a cell the reference
   did not pass cleanly in any of its attempts cannot kill. (Decision D39
   later made C3's equivalence fail closed over earlier attempts; section
   23.)
2. **A rung attempt without host snapshots** (section 9). `foreign_abort`
   returned "no host snapshots" for an attempt with none, and the rung rule
   read that as a foreign-load abort: the attempt's gating failures (since
   `81fd5f3`) and excused trials (since `3ad255a`) were dropped and a rerun
   was allowed, so a rerun could qualify after an attempt that otherwise
   counted and failed. Only the two registered reasons abort now. An
   attempt missing the snapshots of any session does not qualify and may be
   rerun, and its failed and excused trials count
   (`acceptance.snapshot_problems`).
3. **The exposure of the per-setting, per-shuffle reading** (section 9,
   design decision 44, section 20, item 2). The text said that reading
   changed the pass probabilities by less than 10^-4. Recomputed twice
   (once by the review, once independently for this change), it would lower
   the probability that some A1-A3 entry reaches its limit by 8.1 x 10^-5
   at the development rate, 3.3 x 10^-4 at half A7's bound and 1.25 x 10^-3
   at the bound; only A1's limit is affected and the rung probabilities are
   unchanged. Text only.
4. **C4 over every attempt** (section 6.1; found while fixing item 1).
   C4 read the counting A1 attempts only. It reads the tap's stream, which
   A1 does not judge for an entry the probe observes (its trials are judged
   on the probe's log), so a projection mismatch in an earlier A1 attempt
   on such an entry would have disappeared with the rerun. C4 now reads
   every attempt. No mismatch is by design, and a trial that lost its tap
   has an infrastructure failure on a gating entry that already counts
   against A1, so this adds no case in which a rerun alone fails C4.
5. **Code, tests and checks.** `acceptance.py` is still the only code file
   changed since `7653799`, and no campaign executes it, so the executor
   addendum's byte-identity check lists only `harness/q2/README.md` and
   `acceptance.py` and the development runs at `7653799` stand; both
   addenda pin its new digest. New tests drive a rung attempt without
   snapshots (alone; as an earlier attempt that is clean, carries a gating
   failure or carries three excused trials; one session's snapshots
   missing; a foreign-load abort still dropping its trials), and C1, C2 and
   C3 reruns that pass with their by-design failures and fail on an earlier
   pass of a known defect, an unpredicted earlier failure (and not on a
   marker-only one), a counting mutant attempt that kills nothing however
   its earlier attempt fared, or an earlier reference failure on the only
   killing cell, and an earlier A1 attempt's C4 mismatch counting. Each
   new test fails on the `acceptance.py` before it.

## 22. Wording and reporting closed before the freeze (2026-10-07)

The two reviews of the D33 pass left non-blocking notes; each is closed
here before the freeze, with no scored data (code in `acceptance.py`, with
`tests/test_q2_acceptance_analysis.py`, commit `2518241`):

1. **What the excused reason set shows** (section 6.1). The text said the
   set {`guest_server_restart`, `accessibility`} shows a restart during an
   observation call. It shows a restart during or after the entry's
   observation calls, before its post guard: a restart after the entry's
   last observation call that only the post guard sees leaves the same set.
   Excusing it is harmless, because every action of the entry had completed
   and been observed and the trial shows no other failure.
2. **The reading of D33's limit** (section 20, item 2; design decision 44).
   Section 20 had left a conditional ("Should the owner have meant the
   wider reading, D33 is amended before the freeze"). D33's author
   confirmed that the per-entry reading is the one D33 means, so the text
   states it plainly, and the pending item for it is removed from
   `program/state.json`. Decision D39 (`program/decisions.md`) records the
   confirmation (section 23).
3. **"Attempt"** (sections 6.1, 12, 20 and design decision 44). Where those
   sections mean a campaign's first run and its rerun they now say "every
   rerun", and section 6.1 defines an attempt of a campaign as one of its
   runs under one executor: a repair attempt (section 11) is never a rerun,
   and every rule of section 6.1, D33's limits included, runs within one
   repair attempt, as section 11 already said. The code and the earlier
   text keep "earlier attempt" and "counting attempt" in that sense.
4. **A1 at N\*** (sections 6.1 and 7). A1 at N* > 1 is read from the ladder
   rung N* under the rung's rule (two excused trials in the rung, which may
   both fall in one entry), while A1 at N = 1 allows one per entry. This
   was D33's text, but no section said it.
5. **Reporting** (section 12; `acceptance.py`). `entries_over_restart_limit`
   listed only entries whose status was `RESTART_LIMIT`, by name: an entry
   with two excused trials and also a counted failure (FLAKY or FAIL) was
   left off. It now lists every entry with two or more excused trials,
   whatever its status and whether or not the criterion judges it, with
   each excused repetition (job, session, setting, sequence number; in A1
   over both seeds). A4's `restart_only_trials` counted the counting
   attempts only; it now counts every rerun, with the counting attempts'
   count beside it. Under a repair attempt, A4 reports its own restarts per
   accessibility call against A7's bound on A7's rule (section 11,
   `acceptance.repair_restart_rate`), reported and not judged: A7 runs
   under attempt 1 only, and A4 excuses restart-only trials without a
   limit, so an executor that itself caused restarts would otherwise go
   unmeasured.
6. **A5 and earlier attempts** (section 6.1). A5 stays judged on the
   counting attempts' receipts only, because a killed job can leave
   labelled containers by design; each earlier attempt's receipt, or its
   absence, is reported with A5 (`earlier_attempts`).
7. **A failed `squeue` in a host snapshot** (section 9). The driver's
   snapshot reads a `squeue` that fails with no output as no foreign load.
   The driver cannot change (executor addendum, section 9), and the
   analysis cannot detect such a snapshot: the snapshot keeps neither
   `squeue`'s exit status nor the job's own row (checked on the snapshots
   of runs 694 and 703-708). Section 9 states it as a known limitation.
8. **A killed attempt could not be read** (section 6.1, design decision
   46; found while closing item 6). `acceptance.load` opened `receipt.json`
   unconditionally, and the driver writes it last, so the attempt that most
   often makes a rerun (a job ended by a signal, a time limit or a node
   failure; development runs 695-699 have no receipt) could not be read,
   and a criterion with such an earlier attempt would have had no verdict.
   Such an attempt is now read from its manifest, its batch record (whose
   `job_id=` line, written before the driver starts, names the job; the
   run directory's name otherwise) and its finished sessions, and it does
   not count. A session the kill cut short left only unjudged trial
   records (`cycle-NN.trials.jsonl`; the runner judges a session's trials
   at its end, against the tap's stream), so its trials are reported as
   not run, which section 6.1 now says.
9. **Code, tests and checks.** `acceptance.py` is still the only code file
   changed since `7653799`, and no campaign executes it, so the executor
   addendum's byte-identity check lists only `harness/q2/README.md` and
   `acceptance.py` and the development runs at `7653799` stand; both
   addenda pin its new digest. New tests drive the list of entries over the
   limit (FLAKY with two excused trials, a non-gating entry, one excused
   trial in each seed, one excused trial not listed), A4's excused trials
   over every rerun, A4's rate against A7's bound under a repair attempt
   (absent under attempt 1, within and over the bound, never judged), A5's
   report of earlier receipts with its counting receipt still judged, and
   loading an attempt without a receipt (from its preflight record, as an
   earlier attempt whose gating failure counts, and with no finished
   session). Each fails on the `acceptance.py` before it. The final loader
   read development runs 694 and 703-708 again, next to the loader before
   it (`ced21d32`): restarts, accessibility calls, the trials each restart
   hit, every entry's status, the rung reading (`chord_ctrl_c` and
   `drag_short` not PASS in 694 and 703), the snapshots and the abort
   reading are unchanged. The only difference is the new list:
   `chord_ctrl_c` in 694 and 703 is listed over the limit with status
   `RESTART_LIMIT` and its two excused repetitions, where the old list gave
   its name. The cancelled runs 695-699, which the old loader could not
   read (no `receipt.json`), now read as attempts with no finished session,
   Slurm state CANCELLED 143:0 and no batch end, which cannot count.

## 23. Changes for decision D39 (2026-10-07)

The final pre-freeze verifier of branch head `ae2a6d7` found one defect in
the acceptance analysis and one freeze blocker in the text, and noted three
smaller items. Decision D39 (`program/decisions.md`) settled them before
the freeze, with no scored data (code in `acceptance.py`, with
`tests/test_q2_acceptance_analysis.py`, commit `280ccbf`):

1. **C3 equivalence fails closed** (sections 6.1, 8 and 12; design
   decision 45; `acceptance.c3`). C3 read a mutant's equivalence from its
   counting attempt alone and only reported an earlier attempt's streams.
   A mutant that survived in an attempt that did not count (one cancelled
   mid-run, say) therefore came out equivalent if its rerun happened to
   match the reference, and C3 passed: a cancel and rerun removed a
   failure, which section 6.1 says never happens and design decision 37
   exists to prevent. The verifier's synthetic probe showed it: an
   L0-fixed mutant whose counting attempt matched the reference and killed
   nothing, with an earlier attempt that hit its time limit and in which
   `type_plain` passed with different text, read as equivalent, and so did
   one whose only clean kill was in the earlier attempt. Now a mutant is
   equivalent only if its counting attempt's stream signature equals the
   reference's on every cell and every earlier attempt's stream equals the
   reference's on each cell it ran without an infrastructure failure. A
   trial with an infrastructure failure is not compared, because its
   stream may differ for reasons that say nothing about the mutant (design
   decision 45 gave that reason for ignoring earlier attempts altogether;
   it covers only those trials). Kills stay the counting attempt's, so an
   earlier attempt can take equivalence away but never supply a kill. Both
   probe cases now survive and fail C3, the outcome the same streams get
   in a counting attempt; an earlier attempt that differs only on cells
   with an infrastructure failure leaves the mutant equivalent. Each
   earlier attempt is reported with the cells whose stream differed and
   the cells not compared (section 12). The cost: a stream that varies
   between runs on a cell without an infrastructure failure now keeps a
   mutant from being equivalent in any attempt, not only in the counting
   one. Only M12 and M13 on H-OSW-fixed are predicted equivalent
   (comment-only patches, section 8); every other scored mutant is
   predicted killed, and a counting attempt's kill makes earlier streams
   irrelevant. Development saw both equivalent, so the added exposure
   arises only if their campaign is rerun and the rerun's earlier attempt
   shows a stream difference.
2. **An unparseable run file** (section 6.1; `acceptance.load`). The
   driver and the runner write `receipt.json`, `cycle-NN.json` and
   `record-NN.json` whole but not atomically, so a kill during a write can
   leave one cut short, and `load` then raised on it: a criterion with
   such an attempt would have had no verdict, and the frozen analysis no
   repair (the concern of design decision 46, in a narrower window). Such
   a file now reads as missing: a receipt as no receipt, a cycle file as a
   session not run (its trials, restarts, C3 stream differences and C4
   flags are not read, as for a session the kill cut short), a record file as a session without host snapshots.
   The analysis lists each one with its attempt (`unreadable`), and the
   attempt does not count, whatever its end state, so it may be rerun.
3. **Status lines** (all three registrations; `tests/test_q2_prereg_inputs.py`).
   Each status paragraph read "DRAFT. Not frozen.", and a frozen file
   cannot be edited; D32 called the same a freeze blocker for Q3, whose
   line was rewritten before its freeze (`de5657c`). Each now has the
   frozen wording: the ledger row, the freeze order (`q2-action-path-v1`,
   then `q2-action-path-v1-inputs`, then `q2-action-path-v1-executor`) and
   what may not run before that row exists. The test requires it.
4. **The record of D33's reading** (sections 20 and 22, design decision
   44). Those sections said D33's author confirmed the per-entry reading of
   the A1-A3 limit, and the only record was this branch's log. D39 records
   the confirmation in `program/decisions.md`, and the three places now
   point to it.
5. **Section 12's per-rung count.** Section 12 said each rung's excused
   trials are counted over every rerun; `acceptance.rung` counts them over
   every rerun that did not abort (an aborted attempt's trials never count,
   section 9) and gives each earlier attempt's count, aborted or not, in
   `earlier_attempts`. The text now says so. Text only.
6. **Code, tests and checks.** `acceptance.py` is still the only code file
   changed since `7653799`, and no campaign executes it, so the executor
   addendum's byte-identity check lists only `harness/q2/README.md` and
   `acceptance.py` and the development runs at `7653799` stand; both
   addenda pin its new digest. New tests drive the verifier's probe (an
   earlier attempt that timed out, in which `type_plain` passed with
   different text: survived and C3 fails, as when the same streams are
   the counting attempt's), an earlier-only clean kill next to a counting
   attempt identical to the reference (survived), an earlier attempt whose
   only differences are on cells with an infrastructure failure
   (equivalent) and the same with a clean difference elsewhere (survived),
   an earlier attempt cut short (compared on the cells it reached), a
   counting kill (killed whatever the earlier streams), and unparseable
   receipt, cycle and record files (a record cut inside a multi-byte
   character, a cycle file cut short, an empty receipt, a receipt that is
   not an object), read as an earlier attempt that may be rerun and whose
   readable gating failure counts. Each fails on the `acceptance.py`
   before it. The final loader read development runs 694 and 703-708 and
   the cancelled 695-699 again, next to the loader before it (at
   `ae2a6d7`): restarts, accessibility calls, the trials each restart hit,
   every entry's status, the rung reading, the entries over the limit,
   snapshots, the abort reading and the counting problems are unchanged;
   the only difference is the new list of unreadable files, empty in every
   run. Every receipt, cycle and record file in the 124 development run
   directories on the host (996 files) parses.

## 24. Changes from v1 (D40)

Decision D40 (`program/decisions.md`; D30, D33 and D39 carry over) makes v2 v1
with three changes; decision D43, recorded after v2's development (section
26), corrects the cause D40 stated for v1's C2 failure and changes how the
judge reads the XRecord stream, which changes what D40's first item predicts
(item 9; section 27 lists D43's changes). Each change, and each file it
touches, is listed here or in section 27; every other rule, number and file
is v1's (the frozen tables of the three v2 registrations equal v1's except
for the rows item 7 names, and `tests/test_q2_prereg_inputs.py` checks
that). v1 itself (ledger rows 8-10) is unchanged.

1. **The L0-raw prediction's entry for `chord_super_d` is disclosed as
   informed by v1's C2** (D40 i, as decision D43 changes it).
   `harness/q2/action_path/l0_raw_prediction_v2.yaml` is v1's prediction
   file with v1's failing set and predicted passes, `chord_super_d`'s reason
   replaced and three basis notes added (v1's C2 result, the shell's grab
   and D43's judge rule). D40 had moved `chord_super_d` to the predicted
   failures, because v1's judge reads the state of the queued `d` press;
   under D43's judge that state is not read and the entry is predicted to
   pass (section 27). The file says plainly that this entry is informed by
   v1's C2 run (job 768), by D43 and by seed-42 development, not predicted
   a priori; every other line is v1's. v1's file, `l0_raw_prediction.yaml`, is kept
   unchanged as v1's record; no v2 code reads it, and it stays in this file's
   table only so that every file under `harness/q2/` is pinned (design
   decision 35). `acceptance.c2` reads the v2 file (`acceptance.PREDICTION`).
   The translator `l0_raw.py` is unchanged (its docstring still names v1's
   file).
2. **C2 is a reproduction test on its own order seed** (D40 ii). Section 8
   states that v2's C2 is not an a-priori prediction test and reports v1's C2
   as the a-priori result (one unpredicted failure, `chord_super_d`, recorded
   in the XRecord stream with its `d` press at core state 0, without Mod4, in
   every repetition; section 25), and section 12 reports v1's result beside
   v2's. Section 26 shows that this is how RECORD reports a key event queued
   during the shell's synchronous grab, and that the shell received Super+d
   (item 9); under D43's judge the same records pass (section 27).
   C2 runs the 100 entries in the seed-45 shuffle, an order seed no v1
   campaign and no development run used (section 10): v1's C2 ran seed 42,
   whose order v1's development also used. Code: `order.py` adds
   `C2_SEED = 45`, built only for `criterion="C2"` (`check_seed`,
   `shuffle_order` and `plan` take the criterion); `manifest.py`'s `CRITERIA`
   gives C2 seed 45 only, and seed 45 joins 43 and 44 as a seed only a scored
   campaign may declare (`RESERVED_SEEDS`); `driver.acceptance_plan` passes
   the criterion to the order; `acceptance.c2` checks the realized order
   against the seed-45 plan. Every other campaign's realized order is v1's,
   byte for byte (a test checks the order digests of A1-A7, the ladder rungs,
   C1, C3 and a development plan against v1's code's).
3. **The manifest renderer takes the host run root** (D40 iii).
   `scripts/render_q2_action_path_manifest.py --host-root ROOT` names the
   export at `ROOT/src/` followed by the git SHA and puts the run directories
   under `ROOT/runs`. There is no default: a rendering without `--host-root`
   is refused, and so is the development root that v1's renderer hard-coded
   (`~/cotcodec-runs/stage0/q2-action-path`), so the operator step v1's C2
   needed (moving two manifest fields after rendering; evidence README of job
   768) is no longer needed. The renderer's only other changes are the v2
   registration paths and ids. It is not a file any campaign executes.
4. **Development may characterise the mechanism, on seed 42 only** (D40).
   `manifest.py` admits L0-raw as a development layer, at seed 42 like every
   development run (section 10; the detection controls stay refused), and
   `driver.session_plan` gives an L0-raw development run the L0-fixed cells,
   as `acceptance_plan` and the runner already did for C2. Section 26 reports
   the runs; they are development evidence only and change no rule by
   themselves, and D43's rule was developed and checked there (section 27).
   A1 then tests L0-fixed on `chord_super_d` as registered.
5. **Ids, paths and cross-references.** The three registrations are
   `q2-action-path-v2`, `q2-action-path-v2-inputs` and
   `q2-action-path-v2-executor` (repair attempts `-executor-a2`, `-a3`);
   `manifest.py` (`PREREG_ID`, `ADDENDA_IDS`, `executor_addendum`), the
   renderer, `acceptance.py`'s docstring and the tests name them. Files that
   no change touches keep their v1 wording (for example the comments of
   `canary.yaml`, `mutation_operators.yaml` and `harness_design_diffs.md`, and
   `osworld_bfd62bdc_fixed.py`'s header), so their digests stay v1's.
6. **Text added without a rule change.** Section 4.4 states the limit of the
   XRecord channel that development found (section 26), design decision 31
   notes what runs 549 and 574 show when reread, and design decisions 14, 26
   and 45 name v2. Sections 4.4, 8, 25 and 26 and item 2 state the corrected
   cause (item 9). The oracle, the C2 judging rule (design decision 34) and
   every other criterion are unchanged, apart from D43's reading of the tap
   (item 9 and section 27: the judge's channel for `raw-only` entries, C2's
   reading of the tap window and C4, and, as decision D45 narrows the rule and
   extends it, C3's stream comparison).
7. **Frozen tables.** Rows that differ from v1's: here,
   `l0_raw_prediction_v2.yaml` (added); in the inputs addendum, `order.py`,
   `manifest.py`, `driver.py` and `acceptance.py` (D40), and `verdict.py`,
   `guest/guard.py`, `suite.py` and `runner.py` (D43, which also changes
   `manifest.py`, `driver.py` and `acceptance.py`); in the executor addendum,
   `acceptance.py`, `scripts/render_q2_action_path_manifest.py`, `driver.py`
   and `manifest.py` (D40), and `guest/guard.py`, `suite.py` and `runner.py`
   (D43). Decision D45 changes `verdict.py`, `acceptance.py` and the
   prediction file again, adding no row. All but `acceptance.py`, the renderer
   and the prediction file are files a campaign executes; the executor
   addendum's byte-identity rule names each and why, and the commit of the
   development runs they must equal (its section 9).
8. **What does not change.** The catalog, R-dev reference and every oracle's
   expectation; the probe, tap and marker; L0-fixed, the adapters and the
   corpus; G (86 entries), the volume plan, the canary; the session,
   concurrency and ladder rules; A1-A7, C1, C3 and C4 with their seeds, and
   their rules apart from D43's reading of the tap (item 9 and section 27: the
   judge's channel for `raw-only` entries, whose verdicts every criterion
   uses, and C4; C3's equivalence comparison reads the tap's state as the
   judge does since decision D45, which also narrows the rule); the
   infrastructure, restart and rerun rules of decisions D30, D33 and D39; the
   VM-hour sizing (C2's 0.25 VM-hours do not depend on the order seed: the
   same 500 trials in 9 sessions); and v1's development evidence, which v2
   keeps. No v1 data enters a v2 verdict: v2's C2, C1, C3 and A1-A7 run afresh
   from v2's frozen code.
9. **The cause D40 stated is corrected, and the judge stops reading what
   the tap cannot observe** (decision D43). D40 read the X event record as
   showing a real press-state loss, and so a genuine transport defect.
   Section 26 shows that the shell received Super+d and that the tap
   recorded the queued `d` press before the X server computed its state:
   the failure is in the oracle channel's record, not in delivery, and v1's
   a-priori prediction (pass) was right about delivery and wrong about the
   record C2 judges. A draft decision on this branch kept the oracle's
   reading of events queued under a grab and accepted the exposure section
   26 states for L0-fixed (a slow shell answer would fail a delivered chord
   in A1, A2, A4 or the ladder, and the suite could then fail, after three
   repair attempts, on an artifact of its oracle). D43 decides instead that
   v2's judge reads a key event the tap recorded without the guard's lock
   bit on kind, keycode, keysym and order only, and that the guard checks
   that bit (section 27). Decision D45, after two reviews of D43's
   implementation, reads an event so only after a key press recorded with
   that bit in the same window, applies the rule to C3's comparison, and has
   the analysis report every event read so (section 27, design decision
   49). Items 2-4 stand as drafted; item 1's prediction follows from the new
   rule. Whether a later registration should observe the shell's side of a
   grabbed chord directly is Kevin's.

## 25. v1's outcome (C2, job 768)

Evidence: `program/evidence/2026-10-08/q2-action-path-acceptance/` (README,
`acceptance/c2-verdict.json`, `independent-verification.json`).

- **What ran.** `q2-action-path-v1`, `-inputs` and `-executor` were frozen on
  2026-10-08 (ledger rows 8-10). C2 ran once, as registered: job 768, L0-raw,
  the 100 entries in the seed-42 shuffle, 5 repetitions, screenshot setting,
  N = 1, attempt 1, from a content-checked export of `a9948ee`; 500 trials in
  9 cold boots, CPU only, 0.17 VM-hours. The campaign counted (COMPLETED 0:0
  from the batch record and Slurm, gates passed, `System.qcow2` unchanged,
  nothing leaked), with no infrastructure failure, observation retry or
  guest-server restart.
- **Result: C2 failed, and v1 is invalid.** The frozen `acceptance.c2` gave
  `pass: false`: unpredicted failures `['chord_super_d']`, predicted but
  passing `[]`. All 8 predicted failures failed 5 of 5 by the mechanisms the
  prediction file names, and the other 91 entries passed 5 of 5 under C2's
  rule. Under sections 8 and 11 no v1 acceptance criterion may be claimed; C1,
  C3 and A1-A7 did not run, and no v1 campaign will.
- **The a-priori result.** This is the only a-priori test of the L0-raw
  prediction: one unpredicted failure, `chord_super_d` (predicted to pass
  because `'winleft'` maps to Super_L), in 5 of 5 repetitions. The failure is
  in the tap's record: in every repetition the tap recorded the right four
  key events on the right keycodes, and recorded the `d` press, 0 to 1 ms
  after the Super_L press (server time), with core state 0, without Mod4 (and
  without Mod2, the NumLock bit the Super_L press carried), where the R-dev
  reference has Mod4; C2 compares key presses with their state. Section 26
  shows that this is how RECORD reports a key event queued during the
  shell's synchronous grab, and that the shell received Super+d: the chord
  was delivered, so v1's prediction was right about delivery and wrong about
  the record C2 judges, and decision D43 corrects D40's reading of it as a
  genuine transport defect. v1's verdict stands as its section 8 gives it:
  v1's judge reads the queued press's state. An independent verifier
  reproduced the verdict byte for byte from the frozen code and the raw
  records. Re-judged with v2's judge (decision D43, section 27), the five
  trials pass, so v1's a-priori prediction would have held under v2's rule;
  that is said after the rule was chosen with these records in view, and no
  v1 data enters a v2 verdict. `chord_super_d` was never a session's first trial,
  and every session ran the keyboard warm-up.
- **Reported, not judged.** Under section 5 as written, 435 of 500 trials
  passed: the three other shell chords (`chord_alt_f4`, `chord_alt_tab`,
  `chord_ctrl_alt_shift_r`) failed on key-release states only, which C2's rule
  leaves out, and `seq_type_chord_type`, `type_shell_hostile` and
  `type_symbols_shifted` were FLAKY on stale markers only. Two disclosed
  operator deviations (the manifest's host paths moved after rendering, which
  v2's renderer parameter removes; the C2 manifest pinned the executor
  addendum as well) did not affect the verdict.

## 26. Development characterisation of v1's C2 failure (seed 42, D40)

Development evidence only. It changes no rule by itself: it informs the
mechanism text of `chord_super_d` in `l0_raw_prediction_v2.yaml`, and the
correction of D40's stated cause and the judge rule that decision D43
records (section 27), and it is reported with v2's C2. Summaries, the scripts that made them and each run's
records: `program/evidence/2026-10-08/q2-action-path-v2-development/`; the
manifests: `experiments/manifests/q2-action-path-v2/`.

**Runs.** Four CPU-only jobs through `vm-campaign.sbatch`, seed 42, at
`e66bf16` (the commit that holds v2's code), from a read-only export under
`~/cotcodec-runs/q2-action-path-v2/dev/` on the host. Each ended COMPLETED 0:0
by both the batch record and Slurm, with its infrastructure gates passed,
`System.qcow2` unchanged, no GPU and nothing left behind; no trial had an
infrastructure failure.

| Job | Campaign | What ran | Trials |
|---|---|---|---:|
| 784 | `q2ap-v2-dev-l0raw-chords-v1` | L0-raw on the 13 chord entries, 5 repetitions per setting, one VM | 130 |
| 785 | `q2ap-v2-dev-l0fixed-superd-n8-v1` | L0-fixed on `chord_super_d`, the three other shell chords, `type_unicode_bmp` and `type_emoji` (which remap keycodes, so the shell rebuilds its keymap), `key_menu` and `type_plain`; 5 repetitions per setting, 10 trials per session, 8 VMs | 80 |
| 786 | `q2ap-v2-dev-l0fixed-superd-n16-v1` | the same, 5 trials per session, 16 VMs | 80 |
| 787 | `q2ap-v2-dev-l0fixed-superd-n8-v2` | the same, 8 trials per session, 8 VMs | 80 |

Jobs 785-787 ran at the same time (32 VMs at once). In all, about 1.0 VM-hours
(each job's run time times its VMs). The same read-only script also read the
records of v1's development runs (482-708) and of job 768.

**The failure reproduces, and only on chords the shell grabs.** Under L0-raw
`chord_super_d` failed 10 of 10 (both settings): the `d` press 1 to 2 ms after
the Super_L press, recorded with core state 0, then the `d` and Super_L
releases with state 0, as in job 768 (5 of 5). Of the 13 chord entries, sent
by L0-raw at the same speed (each next key 0 to 2 ms after the one before),
the nine the shell does not grab (`chord_ctrl_c`, `chord_ctrl_a`,
`chord_ctrl_shift_t`, `chord_ctrl_shift_arrow`, `chord_shift_tab`,
`chord_ctrl_home`, `chord_shift_arrow_left`, `chord_shift_alone`,
`chord_ctrl_alone`) passed 10 of 10 with every state right (Control+Mod2 on
every event of `chord_ctrl_c`, for example). The four it grabs (Super+d, show
desktop; Alt+F4; Alt+Tab; Ctrl+Alt+Shift+R) failed 10 of 10, each the same
way: every key event after the key that activates the shell's grab (Super_L,
F4, Tab, r) was recorded with state 0, without even Mod2, the NumLock bit that
every other event in these sessions carries (in 1 of 15 `chord_alt_f4` trials
the last release came after the shell's answer and kept its state). For the
three other shell chords only release states differ, which C2's rule leaves
out, so they pass C2, as in job 768.

**The mechanism.** GNOME Shell 42.9 (mutter 42.9, `src/core/keybindings.c`)
grabs its overlay key, Super_L, and every keybinding with `XIGrabKeycode` in
`XIGrabModeSync`: when the grab activates, the X server freezes the keyboard
and queues every later key event until the shell calls `XIAllowEvents` (on the
overlay key it answers `XISyncDevice`, which releases one event and freezes
again). The X server's RECORD extension reports a device event that arrives
while the device is frozen when it is queued (`EnqueueEvent` in
`dix/events.c`), before the server has computed the event's state (in
`ProcessDeviceEvent`, `Xi/exevents.c`), and does not report it again when the
queue is replayed. The tap therefore records such an event with core state 0.
The server source was read at the GitHub mirror `mirror/xserver` (master); the
guest runs Ubuntu 22.04's Xorg 21.1 release, which was not read, but the
guest's records show the same behaviour: a processed event could not lack the
locked NumLock bit.

**The shell received Super+d.** Under L0-raw the probe received no key event,
lost the focus and left the screen (its marker was not in the step's
screenshot) in 15 of 15 trials (jobs 768 and 784), exactly as under L0-fixed
in 30 of 30 (jobs 785-787), where the `d` press carries Mod4. Had the shell
received `d` without Mod4, it would have found no keybinding and replayed `d`
to the probe, which logs every key it receives. So the press-state loss that
decision D40 read as a genuine transport defect is in the X event record
only, not on the way to the shell: the chord was delivered, and C2 failed on
what the tap records for an event queued during the shell's grab (decision
D43 corrects D40's stated cause accordingly). (For Alt+Tab and
Ctrl+Alt+Shift+R the shell's response does differ between the executors: under
L0-raw the releases arrive before the window switcher or the screen recorder
takes its own grab, so the probe saw one more key release. C2 leaves release
states out.)

**Timing.** The `d` press is recorded with Mod4 when it comes after the
shell's answer and with state 0 when it comes before:

| Executor and condition | Second key after Super_L (server ms) | `d` press state | `chord_super_d` passed |
|---|---|---|---:|
| L0-raw (`pyautogui.hotkey`, no interval or hold; jobs 768, 784) | 0-2 | 0 | 0 of 15 |
| L0-fixed (10 ms between presses, 0.1 s hold; directly or under H-OSW-fixed or H-GA), keyboard warmed up (v1 development and jobs 785-787) | 10-14 | Mod4 | 127 of 127 |
| L0-fixed, no warm-up, not the session's first key event (v1 development before the warm-up) | 10-12 | Mod4 | 63 of 63 |
| L0-fixed, no warm-up, the session's first key event (runs 549, 574) | 12-17 | 0 | 0 of 4 |
| QEMU monitor (`sendkey`, the R-dev reference's device) | 99 | Mod4 | 2 of 2 |

In runs 549 and 574 the shell acted on the chord in every trial too (no key
reached the probe, which lost the focus): the master keyboard's switch to the
XTest device, which re-sends the keymap, delayed the shell's answer past
L0-fixed's 10 ms gap. Design decision 31's warm-up moves that switch outside
every entry, which is why it works; its reading (the modifier state recomputed
at the switch) describes the same record. No `xinput` trace was taken: the
lane has no hook to run a command in the guest during a session, and adding
one would change files a campaign executes; the tap's server timestamps give
the timing. The catalog has no other Super chord, so the three other shell
chords (each with the same signature after its own grab-activating key) and
the nine ungrabbed chords (the same speed, no grab) are the comparisons. No
held chord can be sent through L0-raw without a new catalog entry; L0-fixed is
that chord (10 ms between the presses, held 0.1 s), and its second key comes
after the shell's answer.

**L0-fixed's exposure.** With the keyboard warmed up, as A1-A7 and Stage 1 run
it, `chord_super_d` on the L0-fixed path passed 127 of 127 trials (L0-fixed
107, under H-OSW-fixed 10 and under H-GA 10; v1's development runs 97 and v2's
30), 109 of them not the session's first key event and 18 the first after the
warm-up; in v2's runs, on 8 and 16 concurrent VMs with 32 running at once, 22
were not the first key event and 8 were. The `d` press came 10 to 14 ms after
Super_L, with Mod4, in every one. So L0-fixed was not exposed in development
when `chord_super_d` was not a session's first key event (0 of 109; one-sided
95% upper bound 2.7% per trial), nor in any trial with the warm-up (0 of 127;
2.3%). Development cannot exclude a rare slow answer from the shell, though:
at the 2.3% bound A1's 20 `chord_super_d` trials would meet one with
probability up to 0.38 and A4's 276 almost surely, and at the observed rate
(none) neither would. Under v1's judge a slow answer would fail an L0-fixed
trial whose chord the shell received correctly, and the failure would count
against A1, A2, A4 or the ladder and call for a repair attempt (section 11).
Under D43's judge, as decision D45 narrows it (section 27), such a trial is
read on the kind, keycode, keysym and order of its key events, which the tap
records correctly, and passes when they match (the queued `d` press follows
the Super_L press, which the tap records with Mod2), so the exposure is gone
from every trial verdict, from C2's reading and from C4; each verdict reports
the key events it read without their state (`state_not_observed`), and section
12 reports every such trial. Under D43 alone, C3's equivalence test still
compared each cell's XRecord stream byte for byte, state included, so a slow
answer in C3's H-OSW-fixed reference run or in M12's or M13's run would have
kept that no-op mutant from being equivalent and failed C3; decision D45 has
that comparison read the state as the judge does (section 27). A1, A2, A4 and
the ladder test the L0-fixed path on `chord_super_d` as registered. Only
`chord_super_d` sends a key that soon after a grab activates: the other shell
chords release their keys 0.1 s after the key that activates the grab, and
passed 30 of 30 each in jobs 785-787.

**What D43 decides, and what it leaves.** D43 corrects D40's stated cause,
keeps D40's other changes and C2's rule, and has the judge read a key event
the tap recorded without the guard's lock bit on kind, keycode, keysym and
order only, with the guard checking that bit (section 27); decision D45
narrows that reading to events that follow a key press recorded with the bit
in their window and applies it to C3's comparison. Whether a later
registration should observe the shell's side of a grabbed chord directly
(the tap records what the shell's grab held back, not what the shell
received) is Kevin's (`program/state.json`, pending decisions); the answer
could only enter a later registration.

## 27. Changes for decisions D43 and D45 (2026-10-08)

Decision D43 (`program/decisions.md`), recorded after v2's development
(section 26) and before v2's freeze, corrects the cause D40 stated for v1's
C2 failure and has v2's judge stop reading a modifier state the XRecord tap
cannot observe. Decision D45, recorded after two adversarial reviews of
D43's implementation and also before v2's freeze, narrows that rule to
events that follow a processed key press in their window, applies it inside
C3's equivalence comparison, and has the analysis produce section 12's
report of the events read without their state. This section lists what the
two decisions change, the bit the rule rests on, the rule for an event that
lacks that bit for any other reason, the prediction that follows, and the
seed-42 development at `126ff8b` (D43) and its repetition at `c74eae0`
(D45), the commit that holds every changed file a campaign executes.
Evidence, with the scripts that made each summary:
`program/evidence/2026-10-08/q2-action-path-v2-d43/` and
`program/evidence/2026-10-08/q2-action-path-v2-d45/`.

**The bit the guard guarantees.** v1's guard checked the LED mask against the
session's baseline (condition b) and not the modifier state. Every session the
lane ran (a read-only scan of every run directory: v1's development runs, job
768 and jobs 784-787; 424 sessions) started with the Num Lock LED on and Caps
Lock off (LED mask 2), Num_Lock on Mod2 (the probe's `numlock_mask` 16) and
Mod2 in the modifier state; every one of 36,251 guard checks with no key
pressed read LED mask 2 and modifier state Mod2 (two checks with a key still
pressed read Control and Mod2, and six with the probe absent read no state).
So the bit is Mod2, and Lock is not one (Caps Lock is off at the baseline and
`caps_lock_roundtrip` toggles it inside its entry). The guard now checks it
directly: condition (f) requires Mod2 in the logical modifier state
(`QueryPointer`'s mask) before and after every entry (section 6.2); with (a)
and (b) that is a locked Num Lock. No catalog entry presses Num_Lock, so every
key event the X server processes inside an entry carries Mod2. The same bit
marks a processed key press, which decision D45's rule needs before an event
it reads without its state.

**The rule.** `verdict.modifier_state_observable`: a key event the tap
recorded without Mod2, after a key press it recorded with Mod2 in the same
window (the entry's stream between its delimiters), is read as one recorded
while queued under a synchronous grab that activated after that processed
press (in development, always a shell grab that the entry's own press of its
grab key activated; case 6 below), so its modifier state is unobservable, and
the judge reads it on its kind, its keycode (through the keysym at index 0 the
tap resolves from it with the keymap then in force) and its order only. A key
event without Mod2 that no such press precedes is judged on its state as
recorded (decision D45: under D43 as worded it, too, was read without its
state), and every other event is judged as before. The rule reads the tap's
channel only, and every reading of it the same way: the judge's channel for
`raw-only` entries (the four shell chords and R13; R13's expectation has no
state), C4's stream (`rdev_agreement`), C2's reading of the tap window
(`acceptance.c2_projection`) and, since D45, C3's stream comparison (below).
The probe receives events after the server has computed their state, and its
channel keeps every check. Each verdict lists the key events it read without
their state (`state_not_observed`), which is never a failure and never makes a
trial pass by itself: kind, keycode, keysym, order, the text, the marker, the
guard and the infrastructure rules still decide. Every criterion's analysis
reports, over every trial of every attempt, each key event read without its
state, with its offset from the preceding processed press (the latest key
press recorded with Mod2 before it) and that press's keysym, and each event
without Mod2 that no processed press preceded, with its trial's verdict
(`acceptance.state_not_observed_report`; section 12; decision D45 iii). The
scan bears the reading out: of 519,344 tap key events, 172 lacked Mod2, every
one after the press that activates the shell's grab on one of the four
shell-grabbed chords (L0-raw in jobs 768 and 784, and L0-fixed in runs 486,
549 and 574, before the key hold and the warm-up existed), and every one with
state 0; none of 517,032 probe key events and none of 1,550 QEMU-monitor key
events lacked it. D45's condition changes none of the 280 development events
without Mod2 (the scan's 172 and job 830's 108): each follows, in its own
window, the processed press of the key that activates the shell's grab, and
the judge still reads exactly those events without their state
(`tests/test_q2_d43_judge.py`).

**C3's equivalence test (decision D45).** C3 calls a mutant equivalent only if
its XRecord stream without timestamps, its text buffer and its terminal action
equal the reference run's on every cell (section 8). Under D43 as first
implemented, `acceptance._signature` and `_stream_differences` compared each
recorded key event's state byte for byte, a state the judge does not read. A
slow shell answer (section 26) on `chord_super_d` in C3's H-OSW-fixed
reference run or in M12's or M13's run (the comment-only patches predicted
equivalent, the only mutants no cell kills) would have recorded the `d` press,
the `d` release and the Super_L release with state 0 where the other runs
record Mod4 and Mod2; the trial still passes, but that mutant (both, if it was
the reference run) would have come out neither killed nor equivalent, and C3,
and with it v2, would have failed (section 11): up to 6.7% at the development
bound of 2.3% per `chord_super_d` trial over those three trials, more with a
rerun, which decision D39 compares too. D45 (ii) applies the rule inside the
comparison: each trial's stream marks the state of a key event the judge reads
without it (`acceptance._stream`), two key events of which either is so marked
are equal when their kind, keycode and keysym are (`_events_equal`), and every
other byte is compared as before, the state of a key event without Mod2 that
no processed press precedes included, so the comparison still keeps a mutant
from being equivalent on any difference the judge could see. On a real
`chord_super_d` record of job 785, the slow answer now leaves M12 and M13
equivalent and C3 passing, whether it is in a mutant's counting attempt, in an
earlier attempt or in the reference run, while a processed `d` press without
Mod4, or every key at state 0, still differs and leaves M12 a survivor
(`tests/test_q2_d43_judge.py`). No development trial showed a slow answer
(none of section 26's 127 warmed-up L0-fixed-path `chord_super_d` trials, and
no L0-fixed or harness trial of jobs 831, 834-839, 846 and 849-854 read an
event without its state).

**Why a dropped modifier still fails.** Among this guest's clients, as
development observed them (section 4.4), a key event is queued only while a
shell grab holds the keyboard, and a shell grab activates only when its grab
key is pressed: the overlay key Super_L, or a keybinding's key with its
modifiers held. A chord whose grab key is never pressed, or whose modifier is
released before its key, is processed event by event, every event carries
Mod2, and its state is judged; an ungrabbed chord is never queued. The records
show each case. Run 572 (mutant M11, Super_L dropped) and job 832 recorded
`chord_super_d`'s `d` alone with Mod2 and without Mod4, and failed. Job 833
pressed and released each chord's modifiers before its last key: every event
was processed with Mod2, the last key's press lacked its modifier, and every
trial failed. Under L0-raw, the nine chords the shell does not grab, sent as
fast as the shell chords, kept every state in jobs 768, 784 and 830. D45's
condition changes none of these readings: in those records every key event
carries Mod2, and jobs 847 and 848 repeat 832 and 833 at `c74eae0` (below).

**An event without Mod2 for another reason.** Under D43 as worded, any key
event the tap recorded without Mod2 was read without its state; under D45
only one that follows a key press recorded with Mod2 in its window is. Other
ways such an event could arise, and what the suite then does:

1. Num Lock unlocked inside the entry by a key event. The Num_Lock press and
   release are in the stream, and no catalog expectation contains them, so
   the trial fails on its events whatever their states; a lasting change
   also fails the post guard (b and f).
2. Num Lock unlocked inside the entry by a client request, with no key event
   the tap records, and locked again before the post guard. Events the server
   processed in between would lack Mod2 and, after a processed press in their
   window, be read without their state. The trial would still pass only if
   every event's kind, keycode, keysym and order matched, and an event's
   modifier state follows from the modifier keys recorded before it on the one
   XTest keyboard, so hiding a wrong state would need a second, independent
   fault. Nothing in the session sends such a request, and development saw no
   such event.
3. A session whose baseline lacks Num Lock. Condition (f) fails before and
   after every entry, so every trial fails at its guard; the rule is never
   widened to a whole session. No development session did.
4. A queued event recorded with some modifier bits but not Mod2. RECORD
   reports a queued event before any state is computed, so this does not
   arise; every one of the 280 in development (the scan's 172 and job
   830's 108) was state 0. Under D45's rule its state is not read after a
   processed press and is read otherwise.
5. Events from another device. The QEMU monitor's keyboard (the R-dev
   reference and the inputs validation) is processed like any other, and
   its events carried Mod2.
6. A synchronous grab already active when the entry's first key arrives. The X
   server freezes the keyboard for any client's synchronous grab, not only the
   shell's, and an active grab needs no key press; a shell grab an earlier
   entry left active would do the same. Every key event of the entry would
   then be queued and recorded without Mod2, including the press that would
   otherwise activate a shell grab. Under D43 as worded every one would have
   been read without its state, so a `raw-only` shell chord would have passed
   on kind, keycode, keysym and order even if the server had processed none of
   its events by the post guard. Under D45 none follows a processed press, so
   each is judged on its recorded state (0), which lacks the modifier every
   shell chord's later events are expected to carry: the chord fails, C4
   disagrees, C2's reading fails, and section 12's report lists the trial
   under the events no processed press preceded (job 785's records with every
   key state set to 0, `tests/test_q2_d43_judge.py`). An `app` entry is judged
   on the probe's channel, which receives an event only once the server has
   processed it, with its state. Neither the judge nor the guard detects such
   a grab: (a) reads `QueryKeymap`, which shows only keys the server has
   processed; (c) reads the input focus (`GetInputFocus`), which a grab does
   not change; (b) and (f) read the lock, which a grab does not touch. Job 833
   shows the guard's blind spot with a grab that did not freeze the keyboard:
   in each of its two sessions, after `release_first` pressed and released
   `chord_super_d`'s Super_L alone (which opens the shell's overview, as R13's
   Super key does; `chord_super_d`'s restoration re-activates the probe and
   presses no Escape, section 6.2), the probe received no key event in seq
   3-21 and seq 28-34 (26 trials per session, each span starting right after a
   `chord_super_d` trial), while every pre check of those trials was clean,
   condition (c) included; the tap recorded every key event with Mod2, and
   every trial failed on its events. Development saw no event of this case:
   each of the 280 key events recorded without Mod2 (the 172 of the scan and
   108 in job 830) has state 0 and follows, in its own window, the processed
   press (with Mod2) of the key that activates the shell's grab, and the runs
   repeated at `c74eae0` saw none either (below). What D45 leaves: a grab that
   activates inside the entry after a processed press, by a client other than
   the shell or by the shell on a key the entry did not send as its grab key,
   would queue the events after it, and they would be read without their
   state, the chord then judged on their kind, keycode, keysym and order and
   on every state recorded before the grab. Section 12's report gives each
   such event's offset from the preceding processed press and that press's
   keysym; in development every event read without its state came 0-3 ms after
   a processed press of its own chord, its grab key's in every trial but one
   (job 845, below).

**The prediction.** Under L0-raw, `chord_super_d`'s `d` press, `d` release and
Super_L release are queued during the overlay-key grab and recorded without
Mod2, after the Super_L press, which the tap records with Mod2 (processed), so
the judge, under D45's rule as under D43's, reads them on kind, keycode,
keysym and order, which the tap records correctly, and the entry passes; the
three other shell chords already passed C2 and now also pass section 5. v2's
prediction file therefore keeps v1's failing set and predicted passes, with
`chord_super_d`'s reason replaced and disclosed as informed by v1's C2, D43
and development (section 24, item 1). The rule touches nothing else C2 judges:
the eight predicted failures are entries the probe observes (or pointer
entries), whose channel the rule never reads. v2's C2 stays a reproduction
test of the L0-raw failing set on its own order seed (45), not an a-priori
prediction test. Re-judged with this judge, v1's C2 records and job 784's pass
`chord_super_d` 15 of 15, and v1's development runs 549 and 574 (before the
warm-up) and 486 (before the key hold) pass the trials they failed this way;
no other recorded chord verdict of jobs 768 and 784-787 changes
(`tests/test_q2_d43_judge.py`), and no other entry's can, since the rule reads
only `raw-only` entries and C4.

**Files.** `verdict.py` (the rule and its report), `guest/guard.py` (condition
f), `acceptance.py` (C2's reading of the tap window), `runner.py`, `driver.py`
and `manifest.py` (a development-only executor fault, `fault_drop_modifier`,
the rule's negative case: `omit` presses only a key action's last key,
`release_first` presses and releases its other keys first; admitted for
L0-fixed suite development at seed 42 only, never with a mutant or another
fault and never in a scored campaign), `suite.py` (a stale docstring),
`l0_raw_prediction_v2.yaml` (section 24, item 1) and the tests
(`tests/test_q2_d43_judge.py` re-judges real records through the campaign's
own `suite.observation`). Decision D45 changes `verdict.py` again (the
condition on the preceding processed press, `carries_guard_lock_bit`, and the
docstrings that state the precondition), `acceptance.py` (C2's reading and
C3's comparison by the same rule, `tap_state_unread`, `_stream` and
`_events_equal`, and `state_not_observed_report`, which every criterion's
analysis returns) and the prediction file's `d43_judge` note and
`chord_super_d` reason (the preceding press); `tests/test_q2_d43_judge.py`
checks each on real records. The frozen tables change as section 24, item 7
lists; the executor addendum's byte-identity rule names every file a campaign
executes that differs from a development commit, and why (its section 9).

**Development at `126ff8b`** (seed 42, never evidence). Ten CPU-only jobs
through `vm-campaign.sbatch`, from a read-only export of `126ff8b` under
`~/cotcodec-runs/q2-action-path-v2/dev/` on the host (tree digest
`a303c1e2...`, the same locally and on the host), each COMPLETED 0:0 by the
batch record and Slurm, with its infrastructure gates passed, `System.qcow2`
unchanged, no GPU and nothing left behind; 2.4 VM-hours in all (run time
times VMs). Jobs 834-839 repeat v1's final development runs 703-708 with
their workloads and Slurm resources unchanged, because the judge, the guard
and the lane are files a campaign executes.

| Job | Campaign | What ran | Trials | Result |
|---|---|---|---:|---|
| 830 | `q2ap-v2-d43-l0raw-sample-v1` | L0-raw: the four shell chords, four ungrabbed chords, ten gating entries; 5 repetitions per setting, one VM | 180 | the eight chords pass 10 of 10, the shell chords with their queued events read without state (40 trials); `key_kp_enter` and `type_unicode_bmp` fail 10 of 10, as predicted; `seq_type_chord_type` passes 1 of 10 under section 5 on stale markers only, which C2 does not judge; the other gating entries pass |
| 831 | `q2ap-v2-d43-l0fixed-sample-n8-v1` | L0-fixed: the same 18 entries, 10 trials per session on 8 VMs | 180 | 180 of 180; no event read without its state |
| 832 | `q2ap-v2-d43-drop-omit-v1` | negative: L0-fixed with `fault_drop_modifier: omit` on the four shell chords and three ungrabbed chords | 70 | 0 of 70; no event read without its state |
| 833 | `q2ap-v2-d43-drop-release-first-v1` | negative: the same with `release_first` | 70 | 0 of 70; no event read without its state |
| 834 | `q2ap-v2-d43-l0-restart-v1` | as job 703: the guest-server fault injection | 56 | 52 of 56, as 703: the two trials each session's kills hit |
| 835 | `q2ap-v2-d43-l0-fixed-v1` | as job 704: L0-fixed, all 100 entries, one VM | 400 | 400 of 400 |
| 836 | `q2ap-v2-d43-l0-fixed-n8-v1` | as job 705: L0-fixed, all 100 entries, 8 VMs | 800 | 800 of 800 |
| 837 | `q2ap-v2-d43-hosw-fixed-v1` | as job 706: H-OSW-fixed, every corpus cell | 198 | 194 of 198, as 706: R03 and R09 (outside spec) |
| 838 | `q2ap-v2-d43-hga-v1` | as job 707: H-GA, every corpus cell | 186 | 178 of 186, as 707: R02, R04, R06 and R10 (outside spec) |
| 839 | `q2ap-v2-d43-canary-v1` | as job 708: the canary, every app and entry | 60 | 60 of 60 |

What they show. The positive case: under L0-raw every shell chord passes
with its queued events (state 0, 0-3 ms after the grab key) read without
their state, and the ungrabbed chords pass with every state read. The
negative case: with a modifier dropped every chord fails, grabbed or not, and
no event is read without its state. With `omit` the grab key is never
pressed and `d` arrives alone with Mod2; with `release_first` every event is
processed and the last key's press lacks its modifier. C4 disagrees in all
140 negative trials, and in 22 of the 30 ungrabbed `release_first` trials the
probe had lost the focus by the post guard (condition c, charged to the
trial); all 22 fall in job 833's spans in which the probe received no key
event (case 6 above). The repeated final runs: every in-spec cell of every
layer passes in every repetition and setting, and the only failures are
those of jobs 703, 706 and 707; no L0-fixed or harness trial read an event
without its state; C4 agreed in 140 of 140 (835) and 280 of 280 (836) key,
chord and Caps Lock trials; each session's restart count was 0 except the
four injected restarts of job 834; the accessibility calls (260 and 519)
equal 704's and 705's; step p95 2.71 s on one VM and 2.76 s on 8 (704: 2.92
s, 705: 3.02 s). Across all ten jobs, 4,394 guard checks read Mod2, and the
only guard violations were the 22 above. The runner's recorded verdicts of
the 300 chord trials of jobs 830-833 equal the judge's on their records, D45's
judge included (`tests/test_q2_d43_judge.py`).

**Development repeated at `c74eae0`** (decision D45; seed 42, never evidence).
D45 changes `verdict.py`, which judges every trial, so the ten D43 jobs were
repeated at `c74eae0` with their workloads, VMs, runners and Slurm resources
unchanged (`experiments/manifests/q2-action-path-v2/d45-*.yaml`, written by
the evidence's `ops/make_dev_manifests.py`, each equal to its `d43-*` manifest
but for its names, commit, export and registration digest; a test checks it),
through `vm-campaign.sbatch` from a read-only export of `c74eae0` under
`~/cotcodec-runs/q2-action-path-v2/dev/` on the host (tree digest
`4f66fe7e...`, the same locally and on the host). Each job ended COMPLETED 0:0
by the batch record and Slurm, with its infrastructure gates passed,
`System.qcow2` unchanged, no GPU and nothing left behind; 2.4 VM-hours in all.
Jobs 849-854 repeat 834-839, and so v1's final development runs 703-708.

| Job | Campaign | Repeats | Trials | Result |
|---|---|---|---:|---|
| 845 | `q2ap-v2-d45-l0raw-sample-v1` | 830 (L0-raw sample) | 180 | 151 of 180, as 830: the eight chords pass 10 of 10, the shell chords with 108 events read without state (40 trials), each 0-3 ms after a processed press; `key_kp_enter` and `type_unicode_bmp` fail 10 of 10, as predicted; `seq_type_chord_type` passes 1 of 10 under section 5 on stale markers only |
| 846 | `q2ap-v2-d45-l0fixed-sample-n8-v1` | 831 (L0-fixed sample, 8 VMs) | 180 | 180 of 180; no event read without its state |
| 847 | `q2ap-v2-d45-drop-omit-v1` | 832 (negative, `omit`) | 70 | 0 of 70; no event read without its state |
| 848 | `q2ap-v2-d45-drop-release-first-v1` | 833 (negative, `release_first`) | 70 | 0 of 70; no event read without its state |
| 849 | `q2ap-v2-d45-l0-restart-v1` | 834 (703: guest-server fault injection) | 56 | 52 of 56, as 834: the two trials each session's kills hit |
| 850 | `q2ap-v2-d45-l0-fixed-v1` | 835 (704: L0-fixed, one VM) | 400 | 400 of 400 |
| 851 | `q2ap-v2-d45-l0-fixed-n8-v1` | 836 (705: L0-fixed, 8 VMs) | 800 | 799 of 800: one trial failed with `guest_server_restart` alone (an unprovoked guest-server restart, below) |
| 852 | `q2ap-v2-d45-hosw-fixed-v1` | 837 (706: H-OSW-fixed) | 198 | 194 of 198, as 837: R03 and R09 (outside spec) |
| 853 | `q2ap-v2-d45-hga-v1` | 838 (707: H-GA) | 186 | 178 of 186, as 838: R02, R04, R06 and R10 (outside spec) |
| 854 | `q2ap-v2-d45-canary-v1` | 839 (708: the canary) | 60 | 60 of 60 |

What they show. Every cell's PASS count, failure reasons and number of trials
with an event read without its state equal those of the D43 job it repeats,
but for one trial of job 851. The number of events read without their state
is not equal in every cell, since it counts the events of each trial that the
shell's grab held queued: job 845 read 108, as job 830 did, but per entry 29
in `chord_super_d`, 19 in `chord_alt_f4`, 20 in `chord_alt_tab` and 40 in
`chord_ctrl_alt_shift_r` (830: 30, 18, 20 and 40), in all ten trials of each.
Under L0-raw (845) each of the 108 events read without its state follows a
processed press in its window, 0-3 ms after it: the press of the chord's grab
key, except in one `chord_super_d` trial whose `d` press was processed, with
Mod4 and Mod2, 1 ms after Super_L, so that only its two releases were queued
and read without their state (the `d` press, recorded with its state, was
judged on it; every other `chord_super_d` trial of 830 and 845 had three
events queued). In every `chord_alt_f4` trial of 830 and 845 the F4 release
was queued, and so was the Alt_L release except in one trial of 845 and two
of 830, where it was recorded with its state (Mod1 and Mod2) and judged on
it. No key event without Mod2 lacked a
preceding processed press in any job: section 12's report, run with the
analysis at `c74eae0` over v1's C2 and every v2 run (`section12-report.json`),
reads 54 events without their state in job 768, 110 in 784, 108 in 830 and 108
in 845, none elsewhere, and lists no event without Mod2 that no processed
press preceded. The negative case fails 140 of 140 again, with nothing read
without its state and C4 disagreeing in every trial, and job 848 repeats job
833's 22 lost-focus post checks in the same spans. In the repeated final runs
every in-spec cell of every layer passes in every repetition and setting but
for that one trial of job 851; no L0-fixed or harness trial read an event
without its state; C4 agreed in 140 of 140 (850) and 280 of 280 (851) key,
chord and Caps Lock trials; the accessibility calls (260 and 519) equal 835's
and 836's; step p95 2.71 s on one VM and 2.77 s on 8. Job 851's failure: in
its ninth session (the accessibility setting) the guest server restarted
during the `/accessibility` call of `drag_vertical`'s step (the call's retry
was delivered; systemd's restart counter went from 1, the boot's, to 2), and
that trial failed with `guest_server_restart` alone: a restart-only trial,
which A1-A4 and the ladder excuse and A7 counts (decisions D30 and D33,
`acceptance.restart_only`). It is the lane's second unprovoked restart, after
run 622's, and the only one in the 2,726 accessibility calls of jobs 830-839
and 845-854 outside the fault-injection runs 834 and 849; the registered
development rate (one in 8,114 calls, runs 484-622, section 9) is not revised
by it, and A7 bounds the rate on its own campaign. Across all ten jobs, 4,394
guard checks read Mod2, and the only guard violations were the 22 above. The
runner's recorded verdicts of the 300 chord trials of jobs 845-848 equal the
judge's on their records (`tests/test_q2_d43_judge.py`), and the executor
addendum's byte-identity rule now names `c74eae0` (its section 9).

**What D43 and D45 leave.** Whether a later registration should observe the
shell's side of a grabbed chord directly (for example from the shell's own
record of the keybindings it ran) is Kevin's; the answer could only enter a
later registration.
