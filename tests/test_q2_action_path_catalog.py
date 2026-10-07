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


def test_rdev_entries_carry_the_captured_reference(catalog):
    summary = cat.validate(catalog)
    assert summary["rdev_pending"] == []
    entries = {e["id"]: e for e in catalog["entries"]}
    keys = set(cat.PUBLIC_GROUPS["keys_chords"]) | {"caps_lock_roundtrip"}
    assert {e for e, v in entries.items() if v["expect"]["oracle"] == "rdev"} == keys
    assert entries["key_menu"]["expect"]["rdev_input"] == [["compose"]]
    assert entries["key_menu"]["expect"]["events"] == [
        ["KeyPress", "Menu", []],
        ["KeyRelease", "Menu", []],
    ]
    assert entries["chord_ctrl_shift_t"]["expect"]["rdev_input"] == [["ctrl", "shift", "t"]]
    reference = json.loads((HERE / "rdev_reference.json").read_text(encoding="utf-8"))
    for entry_id in keys:
        assert reference["entries"][entry_id]["stable"] is True
        assert entries[entry_id]["expect"]["events"] == reference["entries"][entry_id]["events"]


def test_frozen_catalog_refuses_pending_references(catalog):
    frozen = copy.deepcopy(catalog)
    frozen["status"] = "frozen"
    cat.validate(frozen)
    frozen["entries"][29]["expect"]["events"] = None
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


def _expressible() -> dict[str, list[str]]:
    data = json.loads((HERE / "expressible_entries.json").read_text(encoding="utf-8"))
    return {name: data[name]["expressible"] for name in data}


def test_mutation_operator_manifest_is_frozen_ready():
    manifest = yaml.safe_load((HERE / "mutation_operators.yaml").read_text(encoding="utf-8"))
    operators = manifest["operators"]
    assert len(operators) == 28
    ids = [op["id"] for op in operators]
    assert len(set(ids)) == len(ids)
    assert manifest["equivalence_rule"].startswith("A mutant is equivalent only if")
    assert set(manifest["scored_layers"]) == {"L0-fixed", "H-OSW-fixed", "H-GA"}
    assert set(manifest["unscored_layers"]) == {"H-OSW-up", "H-GA-buggy"}
    layers_for = {
        "executor": {"L0-fixed"},
        "parser": {"H-OSW-fixed", "H-GA"},
        "both": {"L0-fixed", "H-OSW-fixed", "H-GA"},
    }
    for op in operators:
        assert set(op) == {"id", "layer", "description", "applies"}, op["id"]
        assert set(op["applies"]) == layers_for[op["layer"]], op["id"]
        assert any(v["status"] == "scored" for v in op["applies"].values()), op["id"]


def test_every_scored_mutant_can_be_killed_by_an_in_spec_cell():
    """Review finding: M01 on H-GA could change only outside-spec cells, so it was unkillable."""
    manifest = yaml.safe_load((HERE / "mutation_operators.yaml").read_text(encoding="utf-8"))
    cases = manifest["regression_cases"]
    assert list(cases) == [f"R{i:02d}" for i in range(1, 15)]
    assert cases["R14"]["tolerance_px"] == 0  # M24 moves (999, 999) by under 2 px
    expressible = _expressible()
    killable = {
        "L0-fixed": set(cat.PUBLIC_IDS),
        "H-OSW-fixed": set(expressible["H-OSW"])
        | {r for r, c in cases.items() if c["H-OSW-fixed"] in ("gating", "declared")},
        "H-GA": set(expressible["H-GA"])
        | {r for r, c in cases.items() if c["H-GA"] in ("gating", "declared")},
    }
    for op in manifest["operators"]:
        for layer, verdict in op["applies"].items():
            assert verdict["status"] in ("scored", "excluded", "not-applicable"), op["id"]
            if verdict["status"] != "scored":
                assert len(verdict["reason"]) > 20, (op["id"], layer)
                continue
            cells = set(verdict["kill_cells"])
            assert cells <= killable[layer], (op["id"], layer, cells - killable[layer])
            if verdict.get("predicted") == "equivalent":
                assert not cells and verdict["reason"]
            else:
                assert cells, (op["id"], layer)
    m01 = next(op for op in manifest["operators"] if op["id"].startswith("M01"))
    assert m01["applies"]["H-GA"]["status"] == "excluded"
    assert "R03" not in killable["H-GA"] and "R03" not in killable["H-OSW-fixed"]


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
    assert set(prediction["reasons"]) <= set(cat.PUBLIC_IDS)


def test_gating_set_file_matches_the_catalog(catalog):
    frozen = json.loads((HERE / "gating_set.json").read_text(encoding="utf-8"))
    summary = cat.validate(catalog)
    assert frozen["gating"] == summary["gating"]
    assert frozen["non_gating"] == summary["non_gating"]


def test_derived_files_are_reproduced_byte_for_byte(catalog):
    from harness.q2.action_path import build_derived

    for name, render in build_derived.RENDERERS.items():
        assert render(catalog) == (HERE / name).read_text(encoding="utf-8"), name


def test_guard_parks_the_pointer_away_from_every_entry(catalog):
    park = tuple(catalog["guard"]["park_pointer"])
    for entry in catalog["entries"]:
        assert all(
            abs(x - park[0]) > 2 or abs(y - park[1]) > 2 for x, y in cat.entry_points(entry)
        ), entry["id"]
    # move_only ends where drag_vertical ends: without the park, move_only after
    # drag_vertical would see no motion and fail by construction.
    entries = {e["id"]: e for e in catalog["entries"]}
    assert entries["move_only"]["expect"]["final_pointer"] == [1500, 900]
    assert entries["drag_vertical"]["expect"]["final_pointer"] == [1500, 900]
    tampered = copy.deepcopy(catalog)
    tampered["guard"]["park_pointer"] = [1500, 900]
    with pytest.raises(cat.CatalogError, match="park_pointer"):
        cat.validate(tampered)


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
    assert len(computed["H-GA"]["expressible"]) == 79
    assert "click_triple_left" in computed["H-OSW"]["excluded"]
    assert "click_ctrl_left" in computed["H-GA"]["excluded"]
    # Review finding: H-GA's prompt limits scroll magnitude to 1-10 and its parser
    # clamps 25 ticks to 10, a declared deviation, so scroll_down_25 is not H-GA's.
    assert "magnitude" in computed["H-GA"]["excluded"]["scroll_down_25"][0]
    assert "scroll_down_25" in computed["H-OSW"]["expressible"]
    assert "scroll_down_10" in computed["H-GA"]["expressible"]


def test_every_declared_deviation_is_applied_by_the_vocabulary():
    from harness.q2.action_path.vocab import H_GA_SCROLL_LIMIT, HARNESSES, expressible

    assert HARNESSES["H-GA"]["declared_deviations"] == ["scroll magnitude 1..10 per call"]
    at_limit = parse_action({"op": "scroll", "x": 5, "y": 5, "wheel_y": -H_GA_SCROLL_LIMIT})
    over = parse_action({"op": "scroll", "x": 5, "y": 5, "wheel_y": H_GA_SCROLL_LIMIT + 1})
    assert expressible("H-GA", at_limit)[0] is True
    assert expressible("H-GA", over)[0] is False
    assert expressible("H-OSW", over)[0] is True
    triple = parse_action({"op": "click", "x": 5, "y": 5, "count": 3})
    hscroll = parse_action({"op": "scroll", "x": 5, "y": 5, "wheel_x": 2})
    assert expressible("H-OSW", triple)[0] is False
    assert expressible("H-OSW", hscroll)[0] is False


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
