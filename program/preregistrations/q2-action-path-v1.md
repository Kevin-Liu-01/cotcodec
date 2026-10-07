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
  after an independent review (section 15 lists what changed and why).
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
verdicts per layer, the suite's own mutation score, and upper bounds on
residual failure rates per Stage-1 action class and per VM boot.

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
  unmodified upstream parsers they read, the code that judges a trial, and
  the VM lane every scored campaign runs on. Its own validation is
  infrastructure only (HMP input into the probe, no-input canary read-back;
  job 484).
- **`q2-action-path-v1-executor`** (`program/preregistrations/q2-action-path-v1-executor.md`),
  frozen when development ends and before the scored C1 and C3 runs and the
  first acceptance trial: the file digests of L0-fixed, the H-OSW-fixed and
  H-GA adapters, the acceptance workload code (`harness/q2/vm/*.py` and the
  batch script, pinned again), the regression corpus (`suite_cells.json` and
  its generator), the mutation kit, `harness_design_diffs.md`, and the canary
  target coordinates (`canary_targets.json`); its ledger row's git head is the
  executor SHA.

Both addenda were written in one development pass with L0-fixed, before any
freeze, not in the order the first draft gave (design decision 25).
Acceptance and scored-control campaigns are admitted by `manifest.py` only
when the ledger freezes this file and the addenda they need (C2: inputs;
C1, C3 and A1-A6: both), checked by the submitter and again inside the job.

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
| `harness/q2/action_path/mutation_operators.yaml` | `eabef01f55e51e9d8f774ba58206bfff394bee0f8c506b8e9cd6dab79cd4ea57` |
| `harness/q2/action_path/l0_raw_prediction.yaml` | `8b947acafeae1d2bf4fda5a715888556d9ca672e57d488a4c31dadc420f9302a` |
| `harness/q2/action_path/canary.yaml` | `5221c8a6e337a448352d4a5372f2a727294154450b255a16ff5f7bac76cd62ab` |
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
a failure of that setting.

## 6. Infrastructure failures and the guard

### 6.1 Infrastructure failures

An infrastructure failure is any of: a boot that does not serve a valid
`/screenshot` within 300 s of container start; an `/execute` call that does not
return HTTP 200 within 30 s; a `/screenshot` failure; the probe absent at a
guard; the QEMU monitor unreachable during a reference capture; a key event
inside an entry's window on a keycode range the tap's `mapping_check` marks
unverified; a campaign receipt with `infra_gates_pass` false or a Slurm state
other than COMPLETED with exit code 0:0.

Infrastructure failures are **not excluded** from any gating verdict: an entry
that hits one fails that repetition. They are counted and reported separately.
A whole campaign that ends with a non-COMPLETED Slurm state is rerun as a new
attempt with a new output path, and both attempts are reported.

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
setting. The session counts below follow from that rule.

- **A1 (runtime layer).** L0-fixed passes 100% of G at 5 repetitions in the
  seed-43 and seed-44 shuffles, each under both observation settings, at N = 1
  VM; and passes the seed-43 shuffle under both observation settings at the
  operating concurrency N* (section 9). All 100 entries run; G gates. Trials at
  N = 1: 100 x 5 x 2 x 2 = 2,000 in 36 sessions (gating trials 1,720).
- **A2 (harness layer).** H-OSW-fixed and H-GA each pass 100% of their
  expressible entries (85 and 79) and of their gating and declared-deviation R
  cells, 5 repetitions, judged against their own spec, under both observation
  settings.
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
  Repetitions are split evenly between the two observation settings.
- **A4 (volume).** L0-fixed runs `volume_plan.json` (built by `volume.py`)
  with zero failures: 64,028 trials over the 86 G entries, each entry's
  repetitions split evenly between the observation settings, in 1,068
  sessions (534 per setting), order fixed by `random.Random(43)` (`sessions`,
  SHA-256 of the realized order `87a70e10bb18d8d81bde77b1c9ce89cc5c8cb212dc6d22f3b36c30964d2e82dd`),
  spread over the N* VMs. Every G entry runs at least 70 times; each of the
  seven Stage-1 device-action classes (left click; other click: right,
  middle, double, triple or with modifiers; move; drag; scroll; type; key or
  chord) gets at least 10,148 executed actions. What this bounds is in section 9.
- **A5 (reset and hygiene).** A boot-reset campaign at the frozen source SHA
  shows 20 of 20 pristine reset-sentinel checks; every acceptance campaign's
  receipt shows `System.qcow2` unchanged and zero leaked labelled containers
  or volumes.
- **A6 (cross-app canary).** L0-fixed passes 100% of `canary.yaml` (frozen
  with this file) in each of LibreOffice Writer, Google Chrome (a local
  `file://` textarea page), Visual Studio Code and GNOME Terminal, 5
  repetitions per app and entry, screenshot setting. `canary.yaml` fixes each
  app's configuration (autocorrect, auto-closing, auto-indent and completion
  off, so the app does not rewrite typed text), each fixture's initial text,
  each entry's actions and its exact expected final text, and the read-back
  (Writer: paragraph texts joined with `\n` from the accessibility tree;
  Chrome: the textarea value, which the page mirrors into its title on every
  input event, read from the window title once stable; VS Code: the saved
  file, once it has changed and is stable; Terminal: the file written by
  `cat`). Changed before the freeze after development runs 501 and 506:
  Chrome's accessibility text was stale after edits that the screen showed,
  and a fresh VS Code profile opened its first-run walkthrough over the file
  (turned off in `canary.yaml`; the driver also waits until VS Code's status
  bar shows the text editor's items). The entries are the text
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

All of A1-A6 must hold. If any fails, Stage 1 does not start.

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
  An entry fails unless it is PASS in 5 of 5 repetitions. **Any deviation in
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
  when at least one of its layer's cells is not PASS; outside-spec cells run
  and are reported but never kill. A mutant is equivalent only if its XRecord
  stream without timestamps, text buffer and terminal action are
  byte-identical to the unmutated code's on every cell of its layer.
  Required: 100% of scored, non-equivalent mutants killed. The detection
  controls H-OSW-up and H-GA-buggy are not mutated: they carry known defects
  and have no spec they are expected to pass. When: once, after the executor
  addendum is frozen, at the frozen executor and adapter SHA with the frozen
  corpus, seed-42 order, N = 1, screenshot setting. Development runs of the
  mutants are informative only.
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
action" was wrong: they bound only the uniform-mixture rate.

**Other sizes.** Gym-anything PR #53 reports intermittent entries failing
4-20% of the time that 5 repetitions missed; the 60-repetition stress subset
(A3) detects a 5% failure rate with probability 1 − 0.95^60 = 95.4%, and the
20 A1 repetitions per entry detect a 10% rate with probability 1 − 0.9^20 =
87.8%.

**Cost.** One entry trial takes about 1-3 s of VM time (measured `/execute`
no-op 15 ms, `/screenshot` 0.56 s, `/accessibility` 1.3 s median in job 374);
a session adds a cold boot of about 20 s plus settling and probe start, under
45 s. A1 + A2 + A3 + A4 total about 74,000 trials in about 1,250 sessions,
roughly 40-80 VM-hours, CPU only (no GPU is used anywhere in this
experiment).

**Concurrency rule.** N* is the largest N in {1, 8, 16, 24, 32, 40} such that,
at that rung: at least 20 cold boots were measured; boot p95 (container start
to first valid `/screenshot`) ≤ 180 s; step p95 ≤ 2 x the N = 1 value; A1's
seed-43 shuffle passes under both observation settings; and no foreign-load
abort occurred. A rung aborts if a foreign Slurm job starts or foreign load
exceeds 8 CPUs; the snapshots go into the receipt. VMs are pinned to CPUs from
their Slurm allocation; the ladder never exceeds 160 vCPUs. If N* < 40, the
program kill criterion applies: cut the Stage-1 task count before adding GPUs.

## 10. Seeds, order and the development/acceptance split

- **Order.** For shuffle seed s, the run order is built with
  `rng = random.Random(s)`; for each of the 5 repetitions, `ids` = the 100
  catalog IDs in catalog order, `rng.shuffle(ids)`, appended. It is computed
  by Python 3.10.12 in the runner image, and the realized order file's SHA-256
  goes into each receipt. The order is cut into sessions as in section 7.
- **Seed 42: development, never evidence.** Catalog order and the seed-42
  shuffle; L0-fixed, the adapters and the canary target coordinates may be
  iterated freely. Only L0-fixed, H-OSW-fixed, H-GA and the canary run in
  development; L0-raw and the detection controls never do (`manifest.py`
  refuses them). The inputs addendum lists every change to its components
  made after an L0-fixed development run. C2 is scored once at seed 42 after
  the inputs addendum; C1 and C3 are scored once after the executor addendum
  (section 8). Seeds 43 and 44 are refused for every campaign until the
  ledger admits acceptance.
- **Freeze of the executor.** When development ends, the git SHA of L0-fixed
  and the adapters is frozen in `q2-action-path-v1-executor`.
- **Seeds 43 and 44: acceptance.** Fresh VMs (every session is a cold boot of
  a new container), the frozen executor SHA, both observation settings.
  Stress, volume and canary orders use `random.Random(43)`. There is no
  unseeded randomness.

## 11. Repairs and kill criteria

- A failed acceptance attempt is repaired only as a new versioned attempt
  (`-a2`, then `-a3`) with a new output path and a new executor SHA frozen in a
  new executor addendum. The catalog, its references, G, the volume plan, the
  canary and the predictions stay frozen.
- If any gating entry still fails at the third attempt, the affected layer is
  not admitted and Stage 1 does not start.
- A failed validity control (C1-C4) is not repaired within v1; the suite is
  invalid and a corrected suite is a new preregistration.
- If the reset sentinel fails, it is debugged before any concurrency work.
- A finding that a harness "bug" is a design difference goes into
  `harness_design_diffs.md` and never relaxes a verdict after the fact.

## 12. Reported regardless of outcome

Per-entry tables for every layer, attempt, shuffle and observation setting,
including development-run counts; FLAKY entries with their pass fractions;
infrastructure failures by type, including unverified tap ranges; the
mutation score per operator and per layer with the observed killers next to
the predicted ones, and every excluded or not-applicable pair with its
reason; the L0-raw prediction table against the observed results; the R-dev
reference stability per entry; which entries rest on a self-specified oracle;
per-app canary results; the A4 per-class action counts and bounds, per-entry
bounds and per-session results; the concurrency table (boot p50/p95, step
p50/p95, CPU steal and utilization, overlay growth, pass rate per rung); every
design difference per harness; every non-gating entry's results; and the
certified keysym set.

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
    reported separately, never excluded.
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
