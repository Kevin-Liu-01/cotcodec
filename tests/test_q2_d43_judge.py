"""Decisions D43 and D45: the judge stops reading a modifier state the XRecord tap cannot observe.

A key event the tap records without the lock bit the entry guard guarantees (Mod2, Num Lock),
after a key press it records with Mod2 in the same window (decision D45's narrowing), was
recorded while the X server held it queued under a synchronous grab, before it computed the
event's state; the judge reads it on kind, keycode (through its keysym) and order only. A key
event without Mod2 that no such press precedes is judged on its state as recorded. These
tests re-run the judge on real development records (``program/evidence/2026-10-08/
q2-action-path-v2-d43/records/``, copied from the host by ``ops/extract_trials.py``; the
lock-bit scan by ``ops/lock_bits_scan.py``; ``q2-action-path-v2-d45/records/`` for the runs
repeated at D45's commit) through the campaign's own path (``suite.observation``), and on
records changed only where a test says.
"""

from __future__ import annotations

import copy
import json
import types
from collections import Counter
from pathlib import Path

import pytest
import yaml

from harness.q2.action_path import acceptance, verdict
from harness.q2.vm import manifest as manifest_mod
from harness.q2.vm import runner, suite
from harness.q2.vm.guest import guard, l0_fixed

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "program/evidence/2026-10-08/q2-action-path-v2-d43/records"
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
L0 = {c["id"]: c for c in CELLS["layers"]["L0-fixed"]}
SHELL_GRAB_KEY = {"chord_super_d": "Super_L", "chord_alt_f4": "F4", "chord_alt_tab": "Tab",
                  "chord_ctrl_alt_shift_r": "r"}  # fmt: skip
MOD2 = 0x10


def _trials(name: str) -> list[dict]:
    return json.loads((RECORDS / name).read_text(encoding="utf-8"))["trials"]


V1_C2_AND_V2_DEV = _trials("trials-v1-c2-and-v2-dev.json")
V1_DEV = _trials("trials-v1-dev-queued-and-m11.json")
SCAN = json.loads((RECORDS / "lock-bits-scan-v1.json").read_text(encoding="utf-8"))


def _judge(row: dict, trial: dict | None = None, window: list | None = None) -> dict:
    obs = suite.observation(trial or row["trial"], row["window"] if window is None else window,
                            row["check"])  # fmt: skip
    cell = L0[row["trial"]["cell"]]
    out = verdict.judge(cell, obs)
    out["c4"] = verdict.rdev_agreement(cell["expect"], obs["tap_events"] or [])
    return out


def _keys(window: list[dict]) -> list[dict]:
    return [r for r in window if r["kind"] in verdict.KEY_KINDS]


def _name(record: dict) -> str:
    return verdict.keysym_name(record.get("keysym0"))


def test_the_guard_guarantees_mod2_and_the_judge_reads_that_bit():
    """Every development session's baseline has the Num Lock LED on, Num_Lock on Mod2 and Mod2
    in the modifier state; every guard check with no key pressed saw Mod2; the guard now
    requires it (condition f) and the judge's lock bit is the same bit."""
    assert verdict.GUARD_LOCKED_MODS == guard.NUMLOCK_MOD == MOD2
    baselines = {json.dumps(json.loads(k), sort_keys=True): v for k, v in SCAN["baseline"].items()}
    assert baselines == {
        json.dumps({"baseline_check_led": 2, "led_mask": 2, "numlock_mask": 16,
                    "pointer_mods": 16, "tap_ready_led": 2}, sort_keys=True): SCAN["sessions"]
    }  # fmt: skip
    assert SCAN["sessions"] == 424
    for row, count in SCAN["guard_checks"].items():
        led, mods, keys_pressed, probe_absent = json.loads(row)
        assert led == 2
        assert probe_absent or mods & MOD2, (row, count)
    clean = {"keys": [], "buttons": [], "led_mask": 2, "mods": 16,
             "probe": {"mapped": True, "focused": True, "covers_screen": True},
             "screencast": {"growing": False}}  # fmt: skip
    assert guard.violations(clean, 2) == []
    assert guard.violations(dict(clean, mods=0), 2) == ["f"]
    assert guard.violations(dict(clean, mods=0, led_mask=0), 2) == ["b", "f"]
    assert guard.violations({k: v for k, v in clean.items() if k != "mods"}, 2) == ["f"]


def test_every_tap_key_event_without_mod2_follows_a_shell_grab_key_and_reads_state_0():
    """519,344 tap key events, 517,032 probe key events and 1,550 QEMU-monitor key events of
    every action-path run: only 172 tap events lack Mod2, every one after the press of the key
    that activates the shell's grab on a shell-grabbed chord, every one with state 0."""
    assert SCAN["tap_key_events"] == 519344 and SCAN["probe_key_events"] == 517032
    assert SCAN["capture_key_events"] == 1550
    assert SCAN["probe_without_mod2"] == [] and SCAN["capture_without_mod2"] == []
    without = SCAN["tap_without_mod2"]
    assert len(without) == 172
    assert SCAN["summary"]["tap_without_mod2_not_after_grab_key"] == []
    assert {r["cell"] for r in without} == set(SHELL_GRAB_KEY)
    assert {r["state"] for r in without} == {0}
    assert {r["layer"] for r in without} == {"L0-raw", "L0-fixed"}
    # L0-fixed only before the warm-up (runs 549 and 574) and without a key hold (run 486).
    assert sorted({r["job"] for r in without if r["layer"] == "L0-fixed"}) == ["486", "549", "574"]


def _l0_raw(cell: str) -> list[dict]:
    return [r for r in V1_C2_AND_V2_DEV if r["layer"] == "L0-raw" and r["trial"]["cell"] == cell]


def test_v1_c2_and_dev_784_l0_raw_chord_super_d_now_pass_on_the_state_point():
    """Jobs 768 (v1's C2) and 784: the runner failed all 15 on the R-dev projection alone;
    re-judged, all 15 pass, C4 agrees and C2's reading passes, with the `d` press, the `d`
    release and the Super_L release judged without their state."""
    rows = _l0_raw("chord_super_d")
    assert sorted((r["job"], len([x for x in rows if x["job"] == r["job"]])) for r in rows) == (
        [("768", 5)] * 5 + [("784", 10)] * 10
    )
    for row in rows:
        old = row["runner_verdict"]
        assert not old["pass"] and len(old["reasons"]) == 1
        assert old["reasons"][0].startswith("R-dev projection differs")
        keys = _keys(row["window"])
        assert [(k["kind"], _name(k)) for k in keys] == [
            ("KeyPress", "Super_L"), ("KeyPress", "d"), ("KeyRelease", "d"),
            ("KeyRelease", "Super_L"),
        ]  # fmt: skip
        assert keys[0]["state"] == MOD2 and [k["state"] for k in keys[1:]] == [0, 0, 0]
        new = _judge(row)
        assert new["pass"], new["reasons"]
        assert new["state_not_observed"] == [1, 2, 3]
        assert new["c4"] is True
        assert row["runner_c4"] is False
        c2 = {"pass": new["pass"], "infra": new["infra"], "reasons": new["reasons"],
              "events": [], "probe_events": None}  # fmt: skip
        assert acceptance.c2_trial_pass(c2, L0["chord_super_d"])


def test_the_other_shell_chords_under_l0_raw_pass_and_ungrabbed_chords_are_unchanged():
    for cell in SHELL_GRAB_KEY:
        rows = _l0_raw(cell)
        assert len(rows) == 15
        for row in rows:
            new = _judge(row)
            assert new["pass"] and new["state_not_observed"], (cell, new)
            keys = _keys(row["window"])
            presses = [_name(k) if k["kind"] == "KeyPress" else None for k in keys]
            grab = presses.index(SHELL_GRAB_KEY[cell])
            assert all(i > grab for i in new["state_not_observed"]), (cell, new)
    ungrabbed = {r["trial"]["cell"] for r in V1_C2_AND_V2_DEV} - set(SHELL_GRAB_KEY)
    assert len(ungrabbed) == 9
    for row in V1_C2_AND_V2_DEV:
        if row["trial"]["cell"] in ungrabbed:
            new = _judge(row)
            assert new["state_not_observed"] == []
            assert all(k["state"] & MOD2 for k in _keys(row["window"]))
            assert new["pass"] == row["runner_verdict"]["pass"]
            assert new["reasons"] == row["runner_verdict"]["reasons"]


def test_l0_fixed_records_judge_as_before_except_the_queued_ones():
    """Jobs 785-787 (L0-fixed, warmed up): every verdict unchanged. Runs 549 and 574 (before
    the warm-up, the session's first key event): the failed `chord_super_d` trials pass, the
    shell having acted on the chord; run 486 (no key hold): `chord_ctrl_alt_shift_r` passes."""
    for row in V1_C2_AND_V2_DEV:
        if row["layer"] == "L0-fixed":
            new = _judge(row)
            assert new["pass"] == row["runner_verdict"]["pass"] is True
            assert new["state_not_observed"] == []
    changed = []
    for row in V1_DEV:
        if row["mutant"]:
            continue
        new = _judge(row)
        assert new["pass"], (row["job"], new["reasons"])
        if not row["runner_verdict"]["pass"]:
            changed.append((row["job"], row["trial"]["cell"], new["state_not_observed"]))
    assert sorted(changed) == [
        ("486", "chord_ctrl_alt_shift_r", [4, 5, 6, 7]),
        ("549", "chord_super_d", [1]), ("549", "chord_super_d", [1]),
        ("574", "chord_super_d", [1]), ("574", "chord_super_d", [1]),
    ]  # fmt: skip


def test_a_grabbed_chord_whose_grab_key_was_never_pressed_has_no_queued_event():
    """Run 572 (M11 on L0-fixed: Super_L dropped): `d` alone is no shell keybinding, so no
    grab activates, the press is processed with Mod2 and its missing Mod4 fails the trial."""
    rows = [r for r in V1_DEV if r["mutant"] == "M11-unknown-key-dropped"]
    assert len(rows) == 1
    row = rows[0]
    keys = _keys(row["window"])
    assert [(k["kind"], _name(k), k["state"]) for k in keys] == [
        ("KeyPress", "d", MOD2), ("KeyRelease", "d", MOD2),
    ]  # fmt: skip
    new = _judge(row)
    assert not new["pass"] and new["state_not_observed"] == [] and new["c4"] is False


def _ctrl_c() -> dict:
    return next(r for r in _l0_raw("chord_ctrl_c") if r["job"] == "784")


def test_an_ungrabbed_chord_with_a_dropped_modifier_still_fails():
    """A real `chord_ctrl_c` record (job 784, L0-raw) with the Control state removed from the
    `c` events: processed events keep Mod2, so their state is judged and the trial fails on
    the probe's channel, on the tap's (C4) and as a raw-only cell would be read."""
    row = _ctrl_c()
    assert _judge(row)["pass"]
    trial = copy.deepcopy(row["trial"])
    for event in trial["post"]["end"]["events"]:
        if event[0] in verdict.KEY_KINDS and event[6] == 0x63:
            event[2] = MOD2  # Control dropped, Num Lock kept
    window = copy.deepcopy(row["window"])
    for record in window:
        if record["kind"] in verdict.KEY_KINDS and record["keysym0"] == 0x63:
            record["state"] = MOD2
    new = _judge(row, trial, window)
    assert not new["pass"] and new["c4"] is False and new["state_not_observed"] == []
    raw_only = dict(L0["chord_ctrl_c"], observable="raw-only")
    obs = suite.observation(trial, window, row["check"])
    assert not verdict.judge(raw_only, obs)["pass"]


def test_an_event_without_the_lock_bit_for_another_reason():
    """Num Lock unlocked inside an entry. By a key event: the Num_Lock press and release are
    in the stream, which no expectation contains, so the trial fails on its events whatever
    their states; a lasting change fails the post guard (b, f). On the probe's channel an
    event without Mod2 is a processed one and is judged as before."""
    row = _l0_raw("chord_super_d")[0]
    window = copy.deepcopy(row["window"])
    first = next(i for i, r in enumerate(window) if r["kind"] == "KeyPress")
    numlock = [{"kind": kind, "detail": 77, "state": MOD2 if kind == "KeyPress" else 0,
                "keysym0": 0xFF7F, "server_time": window[first]["server_time"]}
               for kind in ("KeyPress", "KeyRelease")]  # fmt: skip
    window[first:first] = numlock
    assert not _judge(row, window=window)["pass"]
    trial = copy.deepcopy(row["trial"])
    trial["post"]["violations"] = ["b", "f"]
    new = _judge(row, trial=trial)
    assert not new["pass"] and "guard post: bf" in new["reasons"]
    # Probe channel: a `c` press without Mod2 and without Control is judged on its state.
    app = _ctrl_c()
    trial = copy.deepcopy(app["trial"])
    for event in trial["post"]["end"]["events"]:
        if event[0] == "KeyPress" and event[6] == 0x63:
            event[2] = 0
    assert not _judge(app, trial=trial)["pass"]


def test_the_rule_reads_a_state_as_unobserved_only_after_a_processed_press():
    """Decision D45: an event lacking Mod2 is read without its state only when a key press
    recorded with Mod2 comes before it in the same window; otherwise its state is judged as
    recorded. Only key presses count as that press, and only the tap's channel is read so."""
    press = {"kind": "KeyPress", "keysym0": 0x64, "state": 0}
    grab = {"kind": "KeyPress", "keysym0": 0xFFEB, "state": MOD2}
    assert verdict.modifier_state_observable(press, after_processed_press=False)
    assert not verdict.modifier_state_observable(press, after_processed_press=True)
    assert verdict.modifier_state_observable(dict(press, state=MOD2 | 64), True)
    assert verdict.state_not_observed([press], recorded_by_tap=True) == []
    assert verdict.state_not_observed([grab, press], recorded_by_tap=True) == [1]
    assert verdict.state_not_observed([grab, press], recorded_by_tap=False) == []
    # Neither a key release nor a button press with Mod2 is a processed key press.
    release = {"kind": "KeyRelease", "keysym0": 0xFFEB, "state": MOD2}
    button = {"kind": "ButtonPress", "detail": 1, "state": MOD2, "x": 0, "y": 0}
    assert verdict.state_not_observed([release, press], recorded_by_tap=True) == []
    assert verdict.state_not_observed([button, press], recorded_by_tap=True) == []
    # The press must come before: an event after the queued one does not reach back.
    assert verdict.state_not_observed([press, grab], recorded_by_tap=True) == []
    reference = [["KeyPress", "Super_L", []], ["KeyPress", "d", ["Mod4"]]]
    assert verdict.rdev_matches([grab, press], reference, recorded_by_tap=True)
    assert not verdict.rdev_matches([grab, press], reference, recorded_by_tap=False)
    # Alone (no processed press before it), the `d` press is judged on its state 0.
    assert not verdict.rdev_matches([press], reference[1:], recorded_by_tap=True)
    assert not verdict.rdev_matches([grab, dict(press, keysym0=0x65)], reference, True)
    assert not verdict.rdev_matches([grab, dict(press, kind="KeyRelease")], reference, True)
    assert not verdict.rdev_matches([grab, press, press], reference, recorded_by_tap=True)
    # Processed (Mod2 present): the state is judged.
    assert not verdict.rdev_matches([grab, dict(press, state=MOD2)], reference, True)
    # The catalog-oracle path reads the tap the same way, ordered and as a multiset.
    for multiset in (False, True):
        ok, _ = verdict.match_events(reference, [grab, press], 2, multiset, recorded_by_tap=True)
        assert ok and not verdict.match_events(reference, [grab, press], 2, multiset)[0]
        assert not verdict.match_events(reference[1:], [press], 2, multiset, True)[0]


def test_c2_reading_leaves_out_the_state_of_presses_the_tap_did_not_observe():
    cell = L0["chord_super_d"]
    queued = [["KeyPress", 133, 16, 0xFFEB], ["KeyPress", 40, 0, 0x64],
              ["KeyRelease", 40, 0, 0x64], ["KeyRelease", 133, 0, 0xFFEB]]  # fmt: skip
    trial = {"events": queued}
    projection = acceptance.c2_projection(trial, cell)
    assert projection == [["KeyPress", "Super_L", []], ["KeyPress", "d"],
                          ["KeyRelease", "d"], ["KeyRelease", "Super_L"]]  # fmt: skip
    assert acceptance.c2_matches(projection, acceptance.c2_reference(cell))
    dropped = [["KeyPress", 40, 16, 0x64], ["KeyRelease", 40, 16, 0x64]]
    assert not acceptance.c2_matches(
        acceptance.c2_projection({"events": dropped}, cell), acceptance.c2_reference(cell)
    )
    wrong_state = [list(r) for r in queued]
    wrong_state[1][2] = MOD2  # processed without Mod4
    assert not acceptance.c2_matches(
        acceptance.c2_projection({"events": wrong_state}, cell), acceptance.c2_reference(cell)
    )
    # Decision D45: with no processed press before them (all four at state 0), every press
    # keeps its recorded state, and the `d` press lacks Mod4.
    frozen = [[r[0], r[1], 0, r[3]] for r in queued]
    projection = acceptance.c2_projection({"events": frozen}, cell)
    assert projection == [["KeyPress", "Super_L", []], ["KeyPress", "d", []],
                          ["KeyRelease", "d"], ["KeyRelease", "Super_L"]]  # fmt: skip
    assert not acceptance.c2_matches(projection, acceptance.c2_reference(cell))
    assert not acceptance.c2_matches(None, acceptance.c2_reference(cell))


class _Recorder:
    def __init__(self):
        self.calls: list[tuple[str, list]] = []

    def press_keys(self, keysyms):
        self.calls.append(("press", list(keysyms)))
        return list(keysyms)

    def release_keys(self, keycodes):
        self.calls.append(("release", list(keycodes)))


def _patched_key(mode: str):
    module = types.ModuleType("l0_fixed_fault")
    exec(compile(runner.drop_modifier_source(mode), "l0_fixed.py", "exec"), module.__dict__)  # noqa: S102
    module.time = types.SimpleNamespace(sleep=lambda s: None)
    return module.Executor.key


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("omit", [("press", [0x64]), ("release", [0x64])]),
        ("release_first", [("press", [0xFFEB]), ("release", [0xFFEB]),
                           ("press", [0x64]), ("release", [0x64])]),
    ],
)  # fmt: skip
def test_the_development_fault_drops_a_chords_modifier_and_nothing_else(mode, expected):
    key = _patched_key(mode)
    recorder = _Recorder()
    key(recorder, [0xFFEB, 0x64])
    assert recorder.calls == expected
    single = _Recorder()
    key(single, [0xFF0D])
    assert single.calls == [("press", [0xFF0D]), ("release", [0xFF0D])]
    unpatched = l0_fixed.Executor.key
    plain = _Recorder()
    l0_fixed.time, saved = types.SimpleNamespace(sleep=lambda s: None), l0_fixed.time
    try:
        unpatched(plain, [0xFFEB, 0x64])
    finally:
        l0_fixed.time = saved
    assert plain.calls == [("press", [0xFFEB, 0x64]), ("release", [0xFFEB, 0x64])]


def _dev_manifest(**workload) -> dict:
    path = ROOT / "experiments/manifests/q2-action-path-v2/dev-l0fixed-superd-n8-v1.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["workload"].update(workload)
    return manifest


def test_the_fault_is_admitted_for_l0_fixed_development_only(tmp_path):
    for mode in manifest_mod.DROP_MODIFIER_MODES:
        manifest_mod.validate_manifest(_dev_manifest(fault_drop_modifier=mode))
    with pytest.raises(manifest_mod.ManifestError):
        manifest_mod.validate_manifest(_dev_manifest(fault_drop_modifier="swap"))
    with pytest.raises(manifest_mod.ManifestError):
        manifest_mod.validate_manifest(_dev_manifest(fault_drop_modifier="omit", layer="L0-raw"))
    with pytest.raises(manifest_mod.ManifestError):
        manifest_mod.validate_manifest(
            _dev_manifest(fault_drop_modifier="omit", mutant="M11-unknown-key-dropped")
        )
    with pytest.raises(manifest_mod.ManifestError):
        manifest_mod.validate_manifest(
            _dev_manifest(fault_drop_modifier="omit", kill_guest_server_after_seq=3)
        )
    from tests.test_q2_acceptance_admission import acceptance as acceptance_manifest
    from tests.test_q2_acceptance_admission import export_tree

    tree = export_tree(tmp_path)  # the three registrations frozen in a scratch ledger
    scored = acceptance_manifest()
    view = manifest_mod.ledger_view(str(tree), manifest_mod.ledger_paths(scored))
    manifest_mod.validate_manifest(scored, view)
    with pytest.raises(manifest_mod.ManifestError, match="unknown keys.*fault_drop_modifier"):
        manifest_mod.validate_manifest(acceptance_manifest(fault_drop_modifier="omit"), view)


D43_DEV = _trials("trials-d43-dev.json")


def _dev(job: str, cell: str | None = None) -> list[dict]:
    return [r for r in D43_DEV if r["job"] == job and (cell is None or r["trial"]["cell"] == cell)]


def test_d43_development_runs_judge_as_the_runner_did_at_the_development_commit():
    """Jobs 830-833 ran at 126ff8b, D43's judge: D45's judge gives every chord trial the
    verdict, the events read without state and the C4 value the runner recorded (decision
    D45 changes none of the 280 development events read without their state)."""
    assert len(D43_DEV) == 300
    for row in D43_DEV:
        new = _judge(row)
        old = row["runner_verdict"]
        assert (new["pass"], new["reasons"], new["state_not_observed"]) == (
            old["pass"], old["reasons"], old["state_not_observed"],
        )  # fmt: skip
        assert new["c4"] == row["runner_c4"]


def test_d43_l0_raw_shell_chords_pass_with_queued_events_and_l0_fixed_has_none():
    """Job 830 (L0-raw): the four shell-grabbed chords pass 10 of 10, every event read without
    its state comes after the grab key; the four ungrabbed chords pass with every state read.
    Job 831 (L0-fixed, 8 VMs): every chord passes and no event is read without its state."""
    for cell, key in SHELL_GRAB_KEY.items():
        rows = _dev("830", cell)
        assert len(rows) == 10
        for row in rows:
            verdict_ = row["runner_verdict"]
            assert verdict_["pass"] and verdict_["state_not_observed"]
            keys = _keys(row["window"])
            presses = [_name(k) if k["kind"] == "KeyPress" else None for k in keys]
            grab = presses.index(key)
            assert all(i > grab for i in verdict_["state_not_observed"])
            assert all(keys[i]["state"] == 0 for i in verdict_["state_not_observed"])
    for cell in ("chord_ctrl_c", "chord_shift_tab", "chord_ctrl_shift_t", "chord_ctrl_alone"):
        for row in _dev("830", cell):
            assert row["runner_verdict"]["pass"]
            assert row["runner_verdict"]["state_not_observed"] == []
            assert all(k["state"] & MOD2 for k in _keys(row["window"]))
    rows = _dev("831")
    assert len(rows) == 80
    assert all(r["runner_verdict"]["pass"] and not r["runner_verdict"]["state_not_observed"]
               for r in rows)  # fmt: skip


@pytest.mark.parametrize("job", ["832", "833"])
def test_d43_negative_case_every_chord_with_a_dropped_modifier_fails(job):
    """Jobs 832 (``omit``) and 833 (``release_first``): every chord, grabbed or not, fails in
    10 of 10 trials, C4 disagrees, and no key event is read without its state: with the
    modifier dropped the shell's grab never holds a key back."""
    rows = _dev(job)
    assert len(rows) == 70
    assert {r["fault"] for r in rows} == {"omit" if job == "832" else "release_first"}
    for row in rows:
        verdict_ = row["runner_verdict"]
        assert not verdict_["pass"] and verdict_["state_not_observed"] == []
        assert row["runner_c4"] is False
        assert all(k["state"] & MOD2 for k in _keys(row["window"]))
    super_d = _dev(job, "chord_super_d")
    if job == "832":
        # The grab key is never pressed: `d` alone, processed with Mod2 and without Mod4.
        for row in super_d:
            assert [(k["kind"], _name(k), k["state"]) for k in _keys(row["window"])] == [
                ("KeyPress", "d", MOD2), ("KeyRelease", "d", MOD2),
            ]  # fmt: skip
    else:
        # Super_L pressed and released first: every event processed, the `d` press without
        # Mod4, and the order differs from the reference.
        for row in super_d:
            keys = _keys(row["window"])
            assert [(k["kind"], _name(k)) for k in keys] == [
                ("KeyPress", "Super_L"), ("KeyRelease", "Super_L"),
                ("KeyPress", "d"), ("KeyRelease", "d"),
            ]  # fmt: skip
            assert keys[2]["state"] == MOD2
        # The ungrabbed chord: the `c` press is processed with Mod2 and without Control, so
        # its state is judged (C4 fails on it as well as on the order).
        for row in _dev(job, "chord_ctrl_c"):
            press = next(k for k in _keys(row["window"])
                         if k["kind"] == "KeyPress" and _name(k) == "c")  # fmt: skip
            assert press["state"] == MOD2


def _without_mod2(rows: list[dict]) -> list[tuple[dict, int, list[dict]]]:
    out = []
    for row in rows:
        keys = _keys(row["window"])
        out += [(row, i, keys) for i, k in enumerate(keys) if not k["state"] & MOD2]
    return out


def test_every_event_without_mod2_follows_the_processed_press_of_its_grab_key():
    """Section 27, case 6, and section 4.4: the 280 key events the tap recorded without Mod2
    in development (the scan's 172 in jobs 486, 549, 574, 768 and 784, and 108 in job 830)
    all have state 0 and follow, in their own window, the press of the key that activates the
    shell's grab, recorded with Mod2 (processed). So D45's narrowed rule, which reads an event
    without its state only after a key press with Mod2 in its window, still reads every one
    of them without its state: the judge lists exactly them, and nothing else."""
    rows = V1_C2_AND_V2_DEV + V1_DEV + D43_DEV
    found = _without_mod2(rows)
    by_job: dict[str, int] = {}
    listed: dict[int, list[int]] = {}
    for row, i, keys in found:
        by_job[row["job"]] = by_job.get(row["job"], 0) + 1
        listed.setdefault(id(row), []).append(i)
        assert keys[i]["state"] == 0
        cell = row["trial"]["cell"]
        grab = [j for j, k in enumerate(keys[:i])
                if k["kind"] == "KeyPress" and _name(k) == SHELL_GRAB_KEY[cell]]  # fmt: skip
        assert grab and keys[grab[0]]["state"] & MOD2, (row["job"], cell, i)
    assert len(found) == 280
    assert by_job.pop("830") == 108
    scan: dict[str, int] = {}
    for record in SCAN["tap_without_mod2"]:
        scan[record["job"]] = scan.get(record["job"], 0) + 1
    assert by_job == scan and sum(scan.values()) == 172
    for row in rows:
        if row["mutant"]:
            continue
        assert _judge(row)["state_not_observed"] == listed.get(id(row), []), row["job"]


def _job_785(cell: str) -> dict:
    return next(r for r in V1_C2_AND_V2_DEV if r["job"] == "785" and r["trial"]["cell"] == cell)


def test_a_grab_already_active_before_the_entry_now_fails():
    """Section 27, case 6, under decision D45: were a synchronous grab already active when an
    entry's first key arrives, every key event would be recorded without Mod2, the first
    included, so none follows a processed press and each is judged on its recorded state.
    Job 785's real L0-fixed records, changed only in their states: with every tap key state
    0, `chord_super_d` fails (the `d` press lacks Mod4), C4 disagrees, C2's reading fails and
    the section-12 report lists the trial. What D45 leaves: an event after a processed press
    is still read without its state (here the F4 press of `chord_alt_f4` after its processed
    Alt_L press), whatever grab queued it (section 27, case 6)."""
    row = _job_785("chord_super_d")
    window = copy.deepcopy(row["window"])
    for record in _keys(window):
        record["state"] = 0
    new = _judge(row, window=window)
    assert not new["pass"] and new["state_not_observed"] == [] and new["c4"] is False
    assert len(new["reasons"]) == 1 and new["reasons"][0].startswith("R-dev projection differs")
    trial = {"events": [suite._compact_tap(r)[:-1] for r in _keys(window)]}
    cell = L0["chord_super_d"]
    projection = acceptance.c2_projection(trial, cell)
    assert not acceptance.c2_matches(projection, acceptance.c2_reference(cell))
    c2 = {"pass": False, "infra": [], "reasons": new["reasons"], "events": trial["events"],
          "probe_events": None}  # fmt: skip
    assert not acceptance.c2_trial_pass(c2, cell)
    report = acceptance.state_not_observed_report([_c3_attempt(row, window)])
    assert report["read_without_state"] == []
    (listed,) = report["no_processed_press_before"]
    assert listed["cell"] == "chord_super_d" and listed["pass"] is False
    assert [(e["kind"], e["keysym"], e["state"]) for e in listed["events"]] == [
        ("KeyPress", "Super_L", 0), ("KeyPress", "d", 0), ("KeyRelease", "d", 0),
        ("KeyRelease", "Super_L", 0),
    ]  # fmt: skip
    # The same with every key of `chord_alt_f4` at state 0: the F4 press lacks Mod1.
    row = _job_785("chord_alt_f4")
    window = copy.deepcopy(row["window"])
    for record in _keys(window):
        record["state"] = 0
    new = _judge(row, window=window)
    assert not new["pass"] and new["state_not_observed"] == []
    # What D45 leaves: only the F4 press at state 0, after the processed Alt_L press.
    window = copy.deepcopy(row["window"])
    f4 = next(k for k in _keys(window) if k["kind"] == "KeyPress" and _name(k) == "F4")
    assert f4["state"] == MOD2 | 8  # Mod1 recorded on the processed F4 press
    f4["state"] = 0
    new = _judge(row, window=window)
    assert new["pass"] and new["state_not_observed"] == [1]
    # The guard reads no grab: a check with the probe mapped, focused and covering the screen,
    # no key pressed and Mod2 set is clean whatever any client has grabbed.
    clean = {"keys": [], "buttons": [], "led_mask": 2, "mods": 16,
             "probe": {"mapped": True, "focused": True, "covers_screen": True},
             "screencast": {"growing": False}}  # fmt: skip
    assert guard.violations(clean, 2) == []


def test_job_833_shows_the_guard_blind_to_a_grab_on_the_keyboard():
    """Section 27, case 6: in both sessions of job 833 (`release_first`), after
    `chord_super_d`'s Super_L was pressed and released alone (opening the shell's overview),
    the probe received no key event in seq 3-21 and 28-34 while every pre check was clean;
    the tap recorded every key event with Mod2 (that grab did not freeze the keyboard), every
    trial failed, and the 22 lost-focus post checks all fall in those spans."""
    rows = _dev("833")
    spans = set(range(3, 22)) | set(range(28, 35))
    for cycle in ("00", "01"):
        session = sorted((r for r in rows if r["cycle"] == cycle), key=lambda r: r["trial"]["seq"])
        assert [r["trial"]["seq"] for r in session] == list(range(35))
        for row in session:
            seq, trial = row["trial"]["seq"], row["trial"]
            probe_keys = [e for e in trial["post"]["end"]["events"] if e[0] in verdict.KEY_KINDS]
            assert trial["pre"]["violations"] == []
            assert all(k["state"] & MOD2 for k in _keys(row["window"]))
            assert not row["runner_verdict"]["pass"]
            if seq in spans or trial["cell"] == "chord_super_d":
                assert probe_keys == [], (cycle, seq)
            else:
                assert probe_keys, (cycle, seq)
            if trial["post"]["violations"]:
                assert trial["post"]["violations"] == ["c"] and seq in spans, (cycle, seq)
        assert [r["trial"]["seq"] for r in session if r["trial"]["cell"] == "chord_super_d"] == [
            2, 10, 16, 27, 34,
        ]  # fmt: skip
    lost_focus = [r for r in rows if r["trial"]["post"]["violations"]]
    assert len(lost_focus) == 22
    assert {r["trial"]["cell"] for r in lost_focus} <= {"chord_ctrl_c", "chord_shift_tab",
                                                         "chord_ctrl_shift_t"}  # fmt: skip


def _c3_attempt(row: dict, window: list[dict]) -> dict:
    raw = dict(copy.deepcopy(row["trial"]), verdict=_judge(row, window=window),
               tap_window=[suite._compact_tap(r) for r in window])  # fmt: skip
    trial = acceptance._trial(raw, row["setting"])
    return {"job": row["job"], "sessions": [{"setting": row["setting"], "trials": [trial]}]}


def test_c3_equivalence_reads_the_state_as_the_judge_does():
    """Decision D45 (ii): C3's stream signature and earlier-attempt comparison read a key
    event's state as the judge does. A slow shell answer on a real `chord_super_d` record
    (job 785: the `d` press, the `d` release and the Super_L release recorded with state 0
    after the processed Super_L press) passes the judge and C4 and now equals the unchanged
    record in C3's comparison; a state the judge does read still differs."""
    row = _job_785("chord_super_d")
    slow = copy.deepcopy(row["window"])
    for record in _keys(slow)[1:]:
        record["state"] = 0
    new = _judge(row, window=slow)
    assert new["pass"] and new["state_not_observed"] == [1, 2, 3] and new["c4"] is True
    reference = _c3_attempt(row, row["window"])
    mutant = _c3_attempt(row, slow)
    assert mutant["sessions"][0]["trials"][0]["pass"]
    signature = acceptance._signature([reference])
    assert acceptance._signatures_equal(acceptance._signature([mutant]), signature)
    assert acceptance._signatures_equal(signature, acceptance._signature([mutant]))
    assert acceptance._stream_differences(mutant, signature) == ([], [])
    assert acceptance._stream_differences(reference, acceptance._signature([mutant])) == ([], [])
    marked = acceptance._signature([mutant])["chord_super_d"][0][0]
    assert [e[2] for e in marked if e[0] in verdict.KEY_KINDS] == [
        MOD2, *[acceptance.STATE_NOT_OBSERVED] * 3,
    ]  # fmt: skip
    # A state the judge reads still differs: the `d` press processed (Mod2) without Mod4,
    # or every key at state 0 (no processed press before them, decision D45).
    for change in ("processed", "frozen"):
        window = copy.deepcopy(row["window"])
        keys = _keys(window)
        if change == "processed":
            keys[1]["state"] = MOD2
        else:
            for record in keys:
                record["state"] = 0
        other = _c3_attempt(row, window)
        assert not acceptance._signatures_equal(acceptance._signature([other]), signature)
        assert acceptance._stream_differences(other, signature) == (["chord_super_d"], [])


def test_c3_leaves_m12_and_m13_equivalent_after_a_slow_shell_answer():
    """Section 27: M12 and M13 on H-OSW-fixed are no-op mutants predicted equivalent. With
    the slow answer of job 785's real record in M12's `chord_super_d` trial, in M13's earlier
    attempt (decision D39 compares it too), or in the H-OSW-fixed reference run, C3 still
    passes with both equivalent (decision D45); a processed `d` press without Mod4 in M12's
    run makes M12 a survivor and fails C3."""
    from tests.test_q2_acceptance_analysis import _timed_out, campaign, ids

    row = _job_785("chord_super_d")
    slow = copy.deepcopy(row["window"])
    for record in _keys(slow)[1:]:
        record["state"] = 0
    wrong = copy.deepcopy(row["window"])
    _keys(wrong)[1]["state"] = MOD2

    def events(window: list[dict]) -> list[list]:
        return [suite._compact_tap(r)[:-1] for r in window if r["kind"] in verdict.KEY_KINDS]

    def with_super_d(run: dict, window: list[dict]) -> dict:
        for session in run["sessions"]:
            for trial in session["trials"]:
                if trial["cell"] == "chord_super_d":
                    trial["events"] = events(window)
        return run

    import yaml

    from harness.q2.action_path import mutants as kit
    from harness.q2.action_path import order

    operators = yaml.safe_load(
        (ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text(encoding="utf-8")
    )
    pairs = kit.scored_pairs(operators)
    plans = {layer: order.plan(ids(layer), 42, 1, ["screenshot"]) for layer in acceptance.C3_LAYERS}
    no_ops = [p for p in pairs if p[1] == "H-OSW-fixed" and p[0].startswith(("M12", "M13"))]
    assert len(no_ops) == 2

    def setup(reference_window, m12_window, m13_earlier_window):
        references = {layer: [with_super_d(campaign(plans[layer], job=f"ref-{layer}"),
                                           row["window"])]
                      for layer in acceptance.C3_LAYERS}  # fmt: skip
        references["H-OSW-fixed"] = [with_super_d(campaign(plans["H-OSW-fixed"], job="ref"),
                                                  reference_window)]  # fmt: skip
        runs = {(op, layer): [with_super_d(campaign(plans[layer], fail={"R14", "key_enter"}),
                                           row["window"])]
                for op, layer in pairs}  # fmt: skip
        m12, m13 = no_ops
        runs[m12] = [with_super_d(campaign(plans["H-OSW-fixed"], job="m12"), m12_window)]
        counting = with_super_d(campaign(plans["H-OSW-fixed"], job="m13"), row["window"])
        earlier = with_super_d(_timed_out(counting, "m13-early"), m13_earlier_window)
        runs[m13] = [dict(counting, earlier=[earlier])]
        return acceptance.c3(runs, references)

    for case in ((row["window"], slow, slow), (slow, row["window"], row["window"])):
        result = setup(*case)
        assert result["pass"], result["problems"]
        for op, layer in no_ops:
            assert result["mutants"][f"{op} {layer}"]["outcome"] == "equivalent"
    result = setup(row["window"], wrong, row["window"])
    assert not result["pass"]
    assert result["mutants"][f"{no_ops[0][0]} H-OSW-fixed"]["outcome"] == "survived"


def test_section_12_reports_every_event_read_without_its_state():
    """Decision D45 (iii): the analysis reports each key event read without its state with
    its offset from the preceding processed press, and each trial with an event without Mod2
    that no processed press preceded. Job 830's real L0-raw chord records: the 108 events of the
    four shell chords, each 0-3 ms after the processed press of its grab key, every one read
    so by the trial's verdict, and no event without Mod2 left unpreceded."""
    rows = _dev("830")
    report = acceptance.state_not_observed_report([_c3_attempt(r, r["window"]) for r in rows])
    assert report["trials"] == len(rows) == 80  # the chord trials (records hold chords only)
    assert report["no_processed_press_before"] == []
    events = [(t["cell"], e) for t in report["read_without_state"] for e in t["events"]]
    assert len(events) == 108
    for cell, event in events:
        assert event["press_keysym"] == SHELL_GRAB_KEY[cell]
        assert 0 <= event["after_press_ms"] <= 3 and event["in_verdict"] is True
        assert event["state"] == 0
    assert report["by_entry"] == {
        cell: {"trials_read_without_state": 10, "events_read_without_state": n,
               "trials_no_processed_press_before": 0, "events_no_processed_press_before": 0}
        for cell, n in Counter(cell for cell, _ in events).items()
    }  # fmt: skip
    assert set(report["by_entry"]) == set(SHELL_GRAB_KEY)
