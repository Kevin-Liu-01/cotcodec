"""Q2 action-path catalog, canonical IR, gating set and frozen-input manifests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from harness.q2.action_path import catalog as cat
from harness.q2.action_path.ir import IRError, held_after, parse_action, parse_sequence
from harness.q2.action_path.vocab import entry_gating

HERE = Path(cat.__file__).resolve().parent
EXPECTED_NON_GATING = {
    "click_button_back", "click_button_forward", "press_hold_release_left",
    "press_hold_release_right", "drag_multipoint_l_shape", "drag_right_button",
    "drag_shift_held", "drag_ctrl_held", "drag_middle_button", "drag_alt_held",
    "scroll_left_3", "scroll_right_3", "scroll_diagonal", "mixed_gesture_state",
}  # fmt: skip


@pytest.fixture(scope="module")
def catalog():
    return cat.load()


def test_catalog_validates_with_public_ids_and_group_sizes(catalog):
    summary = cat.validate(catalog)
    assert summary["entries"] == 100
    sizes = {group: len(ids) for group, ids in cat.PUBLIC_GROUPS.items()}
    assert sizes == {
        "clicks": 18, "drags": 11, "keys_chords": 34, "scrolls": 12, "mixed": 8, "typing": 17,
    }  # fmt: skip
    assert set(summary["non_gating"]) == EXPECTED_NON_GATING
    assert len(summary["gating"]) == 86


def test_catalog_is_ascii_so_no_editor_can_normalize_it():
    raw = cat.CATALOG_PATH.read_bytes()
    assert all(byte < 0x80 for byte in raw)


def test_unicode_entries_keep_exact_code_points(catalog):
    entries = {e["id"]: e for e in catalog["entries"]}
    assert entries["type_combining"]["expect"]["text"] == "é ä ñ"
    assert "‍" in entries["type_emoji_zwj"]["expect"]["text"]
    assert any(ord(ch) > 0xFFFF for ch in entries["type_emoji"]["expect"]["text"])
    assert len(entries["type_long_200"]["expect"]["text"]) == 200
    assert len(entries["type_long_500"]["expect"]["text"]) == 500


def test_rdev_entries_cover_every_key_entry_and_are_pending(catalog):
    summary = cat.validate(catalog)
    keys = set(cat.PUBLIC_GROUPS["keys_chords"]) | {"caps_lock_roundtrip"}
    assert set(summary["rdev_pending"]) == keys
    entries = {e["id"]: e for e in catalog["entries"]}
    assert entries["key_menu"]["expect"]["rdev_input"] == [["compose"]]
    assert entries["chord_ctrl_shift_t"]["expect"]["rdev_input"] == [["ctrl", "shift", "t"]]


def test_frozen_catalog_refuses_pending_references(catalog):
    frozen = copy.deepcopy(catalog)
    frozen["status"] = "frozen"
    with pytest.raises(cat.CatalogError, match="pending R-dev"):
        cat.validate(frozen)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda c: c["entries"].pop(), "public IDs"),
        (lambda c: c["entries"].reverse(), "public IDs"),
        (lambda c: c.update(screen=[1280, 800]), "screen"),
        (lambda c: c["entries"][0]["actions"][0].update(x=1920), "x must be"),
        (lambda c: c["entries"][0]["expect"]["events"][0].__setitem__(2, 5000), "outside"),
        (lambda c: c["entries"][29]["expect"]["rdev_input"][0].append("bogus"), "qcode"),
        (lambda c: c["entries"][83]["expect"].update(text="plain text chek"), "buffer rules"),
        (lambda c: c["entries"][0].update(group="drags"), "group"),
        (lambda c: c["entries"][0]["expect"].update(oracle="executor"), "oracle"),
        (lambda c: c["entries"][0].update(side_effects=["reboots"]), "side effect"),
    ],
)
def test_tampered_catalog_fails(catalog, mutate, message):
    tampered = copy.deepcopy(catalog)
    mutate(tampered)
    with pytest.raises((cat.CatalogError, IRError), match=message):
        cat.validate(tampered)


def test_ir_rejects_unknown_keys_and_fields():
    with pytest.raises(IRError, match="unknown keysym"):
        parse_action({"op": "key", "keys": ["kp_enter"]})
    with pytest.raises(IRError, match="does not take"):
        parse_action({"op": "type", "text": "x", "x": 3})
    with pytest.raises(IRError, match="modifier keysyms"):
        parse_action({"op": "click", "x": 1, "y": 1, "modifiers": ["a"]})
    with pytest.raises(IRError, match="non-zero"):
        parse_action({"op": "scroll", "x": 1, "y": 1})
    with pytest.raises(IRError, match="two points"):
        parse_action({"op": "drag", "path": [[1, 1]]})
    one_point = parse_action({"op": "drag", "path": [[5, 5]], "from_current": True})
    assert one_point.from_current is True
    with pytest.raises(IRError, match="success or failure"):
        parse_action({"op": "terminate", "status": "done"})


def test_ir_round_trips_and_tracks_holds():
    raw = [
        {"op": "key_down", "keys": ["Shift_L"]},
        {"op": "click", "x": 10, "y": 20, "button": 3, "count": 2, "modifiers": ["Control_L"]},
        {"op": "key_up", "keys": ["Shift_L"]},
    ]
    actions = parse_sequence(raw)
    assert held_after(actions) == []
    assert parse_sequence([a.to_dict() for a in actions]) == actions
    with pytest.raises(IRError, match="without release|twice"):
        held_after(parse_sequence([raw[0], raw[0]]))


def test_gating_rule_uses_each_harness_prompt():
    triple = parse_sequence([{"op": "click", "x": 1, "y": 1, "count": 3}])
    assert entry_gating(triple)[0] is True  # H-GA documents triple_click
    hscroll = parse_sequence([{"op": "scroll", "x": 1, "y": 1, "wheel_x": 2}])
    gating, reasons = entry_gating(hscroll)
    assert gating is False and "maps hscroll to vertical" in reasons[0]
    held_drag = parse_sequence([{"op": "drag", "path": [[1, 1], [9, 9]], "modifiers": ["Shift_L"]}])
    assert entry_gating(held_drag)[0] is False


def test_mutation_operator_manifest_is_frozen_ready():
    manifest = yaml.safe_load((HERE / "mutation_operators.yaml").read_text(encoding="utf-8"))
    operators = manifest["operators"]
    assert len(operators) >= 20
    ids = [op["id"] for op in operators]
    assert len(set(ids)) == len(ids)
    for op in operators:
        assert set(op) >= {"id", "layer", "description", "detected_by"}
        assert op["layer"] in ("executor", "parser", "both")
        assert op["detected_by"], op["id"]
        for entry in op["detected_by"]:
            assert entry in cat.PUBLIC_IDS or entry.startswith(("regression:", "guard:")), entry
            if entry.startswith("guard:"):
                assert entry.split(":", 1)[1] in cat.PUBLIC_IDS
    assert manifest["equivalence_rule"].startswith("A mutant is equivalent only if")


def test_l0_raw_prediction_names_catalog_entries():
    prediction = yaml.safe_load((HERE / "l0_raw_prediction.yaml").read_text(encoding="utf-8"))
    fail = set(prediction["predicted_fail"])
    unsupported = set(prediction["predicted_unsupported"])
    assert fail | unsupported <= set(cat.PUBLIC_IDS)
    assert not fail & unsupported
    assert {"type_unicode_bmp", "type_emoji", "type_rtl", "type_combining"} <= fail
    assert {"type_shell_hostile", "type_symbols_shifted"} <= set(
        prediction["predicted_pass_notable"]
    )
    for name in prediction["key_names"].values():
        assert name is None or name == name.lower()


def test_gating_set_file_matches_the_catalog(catalog):
    frozen = json.loads((HERE / "gating_set.json").read_text(encoding="utf-8"))
    summary = cat.validate(catalog)
    assert frozen["gating"] == summary["gating"]
    assert frozen["non_gating"] == summary["non_gating"]


def test_build_catalog_reproduces_the_committed_yaml():
    from harness.q2.action_path import build_catalog

    assert build_catalog.render() == cat.CATALOG_PATH.read_text(encoding="utf-8")


def test_rdev_plan_matches_the_catalog(catalog):
    from harness.q2.action_path import rdev

    committed = (HERE / "rdev_plan.json").read_text(encoding="utf-8")
    assert committed == rdev.plan_json(rdev.build_plan(catalog))
    plan = json.loads(committed)
    assert len(plan["entries"]) == 35
    assert next(e for e in plan["entries"] if e["id"] == "caps_lock_roundtrip")["caps_lock"]


def test_rdev_projection_and_stability():
    from harness.q2.action_path import rdev

    events = [
        {"kind": "KeyPress", "keysym0": 0xFFE3, "state": 16},
        {"kind": "MotionNotify", "state": 0},
        {"kind": "KeyPress", "keysym0": 0x63, "state": 20},
        {"kind": "KeyRelease", "keysym0": 0x63, "state": 20},
        {"kind": "KeyRelease", "keysym0": 0xFFE3, "state": 20},
    ]
    projection = rdev.project(events)
    assert projection == [
        ["KeyPress", "Control_L", []],
        ["KeyPress", "c", ["Control"]],
        ["KeyRelease", "c", ["Control"]],
        ["KeyRelease", "Control_L", ["Control"]],
    ]
    trial = {"id": "chord_ctrl_c", "projection": projection, "guard_clean": True}
    stable = rdev.summarize_capture({"trials": [trial] * 5})
    assert stable["entries"]["chord_ctrl_c"]["stable"] is True
    flipped = dict(trial, projection=projection[:2])
    unstable = rdev.summarize_capture({"trials": [trial] * 4 + [flipped]})
    assert unstable["entries"]["chord_ctrl_c"]["stable"] is False
    assert unstable["entries"]["chord_ctrl_c"]["events"] is None
    dirty = rdev.summarize_capture({"trials": [dict(trial, guard_clean=False)] + [trial] * 4})
    assert dirty["entries"]["chord_ctrl_c"]["stable"] is False


def test_expressible_entries_file_matches_the_vocabularies(catalog):
    from harness.q2.action_path.vocab import harness_expressible

    entries = [(e["id"], parse_sequence(e["actions"])) for e in catalog["entries"]]
    computed = harness_expressible(entries)
    committed = json.loads((HERE / "expressible_entries.json").read_text(encoding="utf-8"))
    assert committed == computed
    assert len(computed["H-OSW"]["expressible"]) == 85
    assert len(computed["H-GA"]["expressible"]) == 80
    assert "click_triple_left" in computed["H-OSW"]["excluded"]
    assert "click_ctrl_left" in computed["H-GA"]["excluded"]


def test_rdev_reference_rejects_an_unbalanced_window():
    from harness.q2.action_path import rdev

    leaked = [
        ["KeyPress", "F1", []],
        ["KeyRelease", "F1", []],
        ["KeyPress", "Escape", []],
    ]
    assert rdev.balanced(leaked[:2]) and not rdev.balanced(leaked)
    trial = {"id": "key_f1", "projection": leaked, "guard_clean": True}
    summary = rdev.summarize_capture({"trials": [trial] * 5})
    assert summary["entries"]["key_f1"]["stable"] is False
