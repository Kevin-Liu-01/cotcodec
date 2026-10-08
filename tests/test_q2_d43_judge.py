"""Decision D43: the judge stops reading a modifier state the XRecord tap cannot observe.

A key event the tap records without the lock bit the entry guard guarantees (Mod2, Num Lock)
was recorded while the X server held it queued under a synchronous GNOME Shell grab, before
it computed the event's state; the judge reads it on kind, keycode (through its keysym) and
order only. These tests re-run the judge on real development records (``program/evidence/
2026-10-08/q2-action-path-v2-d43/records/``, copied from the host by
``ops/extract_trials.py``; the lock-bit scan by ``ops/lock_bits_scan.py``) through the
campaign's own path (``suite.observation``), and on records changed only where a test says.
"""

from __future__ import annotations

import copy
import json
import types
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


def test_the_rule_reads_only_key_events_and_only_the_taps_channel():
    press = {"kind": "KeyPress", "keysym0": 0x64, "state": 0}
    assert not verdict.modifier_state_observable(press)
    assert verdict.modifier_state_observable(dict(press, state=MOD2 | 64))
    assert verdict.state_not_observed([press], recorded_by_tap=False) == []
    assert verdict.state_not_observed([press], recorded_by_tap=True) == [0]
    reference = [["KeyPress", "d", ["Mod4"]]]
    assert verdict.rdev_matches([press], reference, recorded_by_tap=True)
    assert not verdict.rdev_matches([press], reference, recorded_by_tap=False)
    assert not verdict.rdev_matches([dict(press, keysym0=0x65)], reference, recorded_by_tap=True)
    assert not verdict.rdev_matches([dict(press, kind="KeyRelease")], reference, True)
    assert not verdict.rdev_matches([press, press], reference, recorded_by_tap=True)
    # Processed (Mod2 present): the state is judged.
    assert not verdict.rdev_matches([dict(press, state=MOD2)], reference, recorded_by_tap=True)
    # The catalog-oracle path reads the tap the same way.
    ok, _ = verdict.match_events(reference, [press], 2, recorded_by_tap=True)
    assert ok and not verdict.match_events(reference, [press], 2)[0]


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
