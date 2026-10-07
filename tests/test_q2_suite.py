"""Suite components: verdicts, executor transport, order, controls, adapters, corpus, vendor."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

from harness.q2.action_path import adapters, controls, corpus, executor, order, verdict
from harness.q2.action_path import catalog as cat
from harness.q2.action_path.ir import KEYSYM_VALUES, IRError
from harness.q2.vm.guest import l0_fixed, probe

ROOT = Path(__file__).resolve().parents[1]
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())


def _cell(layer: str, cell_id: str) -> dict:
    return next(c for c in CELLS["layers"][layer] if c["id"] == cell_id)


# --- verdicts ------------------------------------------------------------------------


def _obs(events, **kw):
    base = {
        "probe_events": events,
        "tap_events": events,
        "text": "",
        "end_pointer": [960, 540],
        "marker": {"ok": True, "seq": 3, "crc": probe.text_crc("")},
        "probe_final": [3, probe.text_crc("")],
        "guard_violations": {"pre": [], "post": []},
        "infra": [],
        "errors": [],
        "terminal": None,
    }
    base.update(kw)
    return base


def _ev(kind, detail, x=960, y=540, state=0, time=0, keysym0=None):
    out = {"kind": kind, "detail": detail, "state": state, "x": x, "y": y, "time": time}
    if keysym0 is not None:
        out["keysym0"] = keysym0
    return out


def test_click_passes_and_each_condition_can_fail_it():
    cell = _cell("L0-fixed", "click_left_center")
    good = [_ev("ButtonPress", 1, 961, 539), _ev("ButtonRelease", 1, 961, 539)]
    assert verdict.judge(cell, _obs(good))["pass"]
    assert not verdict.judge(cell, _obs([_ev("ButtonPress", 3), _ev("ButtonRelease", 3)]))["pass"]
    assert not verdict.judge(cell, _obs(good[:1]))["pass"]
    far = [_ev("ButtonPress", 1, 963, 540), _ev("ButtonRelease", 1, 963, 540)]
    assert not verdict.judge(cell, _obs(far))["pass"]
    stale = {"ok": True, "seq": 2, "crc": probe.text_crc("")}
    assert not verdict.judge(cell, _obs(good, marker=stale))["pass"]
    dirty = {"pre": [], "post": ["a"]}
    assert not verdict.judge(cell, _obs(good, guard_violations=dirty))["pass"]
    result = verdict.judge(cell, _obs(good, infra=["screenshot"]))
    assert not result["pass"] and result["infra"] == ["screenshot"]
    assert not verdict.judge(cell, _obs(good, end_pointer=[100, 100]))["pass"]


def test_double_click_gap_bound_and_modifier_mask():
    cell = _cell("L0-fixed", "click_double_left")
    events = [
        _ev(k, 1, 960, 700, time=t)
        for k, t in (
            ("ButtonPress", 0),
            ("ButtonRelease", 20),
            ("ButtonPress", 80),
            ("ButtonRelease", 100),
        )
    ]
    assert verdict.judge(cell, _obs(events, end_pointer=None))["pass"]
    slow = copy.deepcopy(events)
    slow[2]["time"] = slow[3]["time"] = 400
    assert not verdict.judge(cell, _obs(slow, end_pointer=None))["pass"]
    ctrl = _cell("L0-fixed", "click_ctrl_left")
    events = [
        _ev("KeyPress", 37, keysym0=0xFFE3),
        _ev("ButtonPress", 1, 500, 300, state=4),
        _ev("ButtonRelease", 1, 500, 300, state=4 | 256),
        _ev("KeyRelease", 37, state=4, keysym0=0xFFE3),
    ]
    assert verdict.judge(ctrl, _obs(events))["pass"]
    events[1]["state"] = 0
    assert not verdict.judge(ctrl, _obs(events))["pass"]


def test_rdev_projection_text_and_no_action_control():
    chord = _cell("L0-fixed", "chord_ctrl_c")
    ok = [
        _ev("KeyPress", 37, state=0, keysym0=0xFFE3),
        _ev("KeyPress", 54, state=4, keysym0=0x63),
        _ev("KeyRelease", 54, state=4, keysym0=0x63),
        _ev("KeyRelease", 37, state=4, keysym0=0xFFE3),
    ]
    assert verdict.judge(chord, _obs(ok))["pass"]
    assert verdict.rdev_agreement(chord["expect"], ok) is True
    swapped = [ok[0], ok[1], ok[3], ok[2]]
    assert not verdict.judge(chord, _obs(swapped))["pass"]
    typing = _cell("L0-fixed", "type_unicode_bmp")
    text = typing["expect"]["text"]
    final = [3, probe.text_crc(text)]
    marker_ok = {"ok": True, "seq": 3, "crc": probe.text_crc(text)}
    assert verdict.judge(typing, _obs([], text=text, probe_final=final, marker=marker_ok))["pass"]
    assert not verdict.judge(typing, _obs([], text=text[:-1], probe_final=final, marker=marker_ok))[
        "pass"
    ]
    none = _cell("L0-fixed", "no_action_control")
    assert verdict.judge(none, _obs([]))["pass"]
    assert not verdict.judge(none, _obs([], tap_events=[_ev("MotionNotify", 0)]))["pass"]


def test_summarize_marks_mixed_results_flaky():
    trials = [
        {"cell": "a", "verdict": {"pass": True}},
        {"cell": "a", "verdict": {"pass": False}},
        {"cell": "b", "verdict": {"pass": True}},
    ]
    out = verdict.summarize(trials)
    assert out["cells"]["a"]["status"] == "FLAKY" and out["cells"]["b"]["status"] == "PASS"


# --- executor transport ------------------------------------------------------------------


def test_step_command_carries_the_action_inside_base64_only():
    action = {"op": "type", "text": "$(true) `x` 'q' \"d\" 日"}
    command = executor.step_command(action)
    assert "$(true)" not in command and "日" not in command
    encoded = re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)", command).group(1)
    payload = base64.b64decode(encoded).decode("utf-8")
    assert payload.startswith(executor.l0_source())
    call = payload[len(executor.l0_source()) :]
    assert json.loads(eval(call.split("json.loads(", 1)[1].rsplit("))", 1)[0])) == action  # noqa: S307
    keyed = executor.device_action({"op": "key", "keys": ["Control_L", "Page_Up"]})
    assert keyed == {"op": "key", "keysyms": [KEYSYM_VALUES["Control_L"], KEYSYM_VALUES["Prior"]]}
    with pytest.raises(ValueError):
        executor.device_action({"op": "terminate", "status": "success"})


def test_l0_fixed_pure_helpers():
    assert l0_fixed.char_keysym("a") == 0x61
    assert l0_fixed.char_keysym("é") == 0xE9
    assert l0_fixed.char_keysym("日") == 0x010065E5
    assert l0_fixed.char_keysym("\n") == 0xFF0D
    with pytest.raises(ValueError):
        l0_fixed.char_keysym("\x07")
    keymap = {38: [0x61, 0x41, 0x61, 0x41], 59: [0x2C, 0x3C], 94: [0x3C, 0x3E], 60: [0x2E, 0x3E]}
    assert l0_fixed.find_keycode(keymap, 0x3C) == (94, False)
    assert l0_fixed.find_keycode(keymap, 0x41) == (38, True)
    assert l0_fixed.find_keycode(keymap, 0x3E) == (60, True)
    assert l0_fixed.find_keycode(keymap, 0xE9) is None
    for row in ([0x61], [0x61, 0x41], [0x31, 0x21, 0x31, 0x21], [0xE9, 0xE9], [0xFF8D, 0, 0xFF8D]):
        assert l0_fixed.core_group(row) == probe.core_group(row, 0)


def test_catalog_drags_produce_motion_and_hit_every_vertex():
    data = cat.load()
    for entry in data["entries"]:
        for action in entry["actions"]:
            if action["op"] != "drag":
                continue
            path = action["path"]
            points = l0_fixed.drag_points(path[0], path[1:], action.get("duration_ms", 500))
            positions = [p for p, _ in points]
            assert len(positions) >= 3, entry["id"]
            assert all(tuple(v) in positions for v in path[1:]), entry["id"]
            assert positions[-1] == tuple(path[-1])
            assert tuple(data["guard"]["park_pointer"]) not in positions


# --- order ------------------------------------------------------------------------------


def test_order_is_seeded_and_refuses_acceptance_seeds_in_development():
    ids = [f"e{i}" for i in range(100)]
    first = order.shuffle_order(ids, 42, 5)
    assert first == order.shuffle_order(ids, 42, 5) and len(first) == 500
    for seed in (43, 44, 7):
        with pytest.raises(order.OrderError):
            order.shuffle_order(ids, seed, 1)
    sessions = order.plan(ids, 42, 5, ["screenshot", "screenshot+a11y"])
    assert len(sessions) == 18 and all(len(s["trials"]) <= 60 for s in sessions)
    sizes = {len(s["trials"]) for s in sessions}
    assert sizes <= {55, 56}


# --- controls (C1) at the parse level ----------------------------------------------------


def _ir(layer: str, cell_id: str) -> list[list[dict]]:
    cell = _cell(layer, cell_id)
    return [adapters.turn_ir(layer, turn) for turn in cell["turns"]]


def test_ga_buggy_drops_middle_click_releases_ctrl_early_and_runs_only_the_first_call():
    assert _ir("H-GA-buggy", "R01") == [[]]
    r02 = _ir("H-GA-buggy", "R02")[0]
    assert r02[0] == {"op": "key", "keys": ["Control_L"]} and r02[1]["op"] == "click"
    assert [a["op"] for a in _ir("H-GA-buggy", "R05")[0]] == ["move"]
    assert [a["op"] for a in _ir("H-GA-buggy", "R06")[0]] == ["move"]
    assert [a["op"] for a in _ir("H-GA-buggy", "R07")[0]] == ["click"]


def test_osw_up_triple_scroll_hscroll_and_terminate_defects():
    assert _ir("H-OSW-up", "R08")[0][0]["count"] == 2
    r09 = _ir("H-OSW-up", "R09")[0]
    assert r09 == [{"op": "scroll", "wheel_y": 3}]  # the coordinate is dropped
    assert _ir("H-OSW-up", "R10")[1] == [{"op": "scroll", "wheel_y": 3}]
    assert _ir("H-OSW-up", "R11") == [[{"op": "terminate", "status": "success"}]]
    assert _ir("H-OSW-up", "R13") == [[], [], []]  # PyAutoGUI drops kp_enter, menu, super


# --- Stage-1 adapters --------------------------------------------------------------------


def test_stage1_harnesses_fix_what_their_spec_requires():
    assert _ir("H-OSW-fixed", "R11") == [[{"op": "terminate", "status": "failure"}]]
    assert _ir("H-GA", "R11") == [[{"op": "terminate", "status": "failure"}]]
    for layer in ("H-OSW-fixed", "H-GA"):
        r13 = [a["keys"] for turn in _ir(layer, "R13") for a in turn]
        assert r13 == [["KP_Enter"], ["Menu"], ["Super_L"]]
        r14 = _ir(layer, "R14")[0][0]
        assert (r14["x"], r14["y"]) == (1919, 1079)
    r02 = _ir("H-OSW-fixed", "R02")[0][0]
    assert r02["modifiers"] == ["Control_L"]
    spaces = _ir("H-OSW-fixed", "type_spaces")[0][0]["text"]
    assert spaces == cat.load()["entries"][PUBLIC_INDEX["type_spaces"]]["expect"]["text"]
    with pytest.raises(IRError):
        adapters.turn_ir("H-OSW-fixed", corpus.render_turn([{"action": "key", "keys": ["nokey"]}]))


PUBLIC_INDEX = {entry_id: i for i, entry_id in enumerate(cat.PUBLIC_IDS)}


def test_perturbations_parse_to_the_plain_ir_on_every_in_spec_cell():
    for layer in ("H-OSW-fixed", "H-GA"):
        for cell in CELLS["layers"][layer]:
            if cell["status"] == "outside":
                continue
            plain = [adapters.turn_ir(layer, t) for t in cell["turns"]]
            for variant, turns in cell["variants"].items():
                assert [adapters.turn_ir(layer, t) for t in turns] == plain, (
                    layer,
                    cell["id"],
                    variant,
                )


def test_rendered_catalog_cells_stay_within_one_pixel_of_the_catalog():
    l0 = {c["id"]: c for c in CELLS["layers"]["L0-fixed"]}
    for layer, harness in (("H-OSW-fixed", "H-OSW"), ("H-GA", "H-GA")):
        for cell in CELLS["layers"][layer]:
            if cell["source"] != "catalog":
                continue
            ir = [a for t in cell["turns"] for a in adapters.turn_ir(layer, t)]
            want = [p for a in l0[cell["id"]]["actions"] for p in _points(a)]
            got = [p for a in ir for p in _points(a)]
            assert set(map(tuple, want)) <= {tuple(p) for p in want}
            for x, y in want:
                assert any(abs(x - gx) <= 1 and abs(y - gy) <= 1 for gx, gy in got), (
                    harness,
                    cell["id"],
                    (x, y),
                )


def _points(action: dict) -> list[list[int]]:
    out = []
    if "x" in action:
        out.append([action["x"], action["y"]])
    out += [list(p) for p in action.get("path") or []]
    return out


# --- corpus and derived files -------------------------------------------------------------


def test_suite_cells_reproduce_byte_for_byte():
    from harness.q2.action_path import build_suite

    committed = (ROOT / "harness/q2/action_path/suite_cells.json").read_text(encoding="ascii")
    assert build_suite.render() == committed


def test_r_case_statuses_match_mutation_operators_table():
    import yaml

    table = yaml.safe_load((ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text())
    names = {"H-OSW-fixed": "H-OSW-fixed", "H-GA": "H-GA"}
    for layer, key in names.items():
        for cell in CELLS["layers"][layer]:
            if cell["source"] == "r-case":
                assert table["regression_cases"][cell["id"]][key] == cell["status"]
                assert table["regression_cases"][cell["id"]]["tolerance_px"] == cell["expect"].get(
                    "tolerance_px", 2
                )


def test_grid_rendering_is_within_one_pixel_and_r_case_pixels_agree_across_harnesses():
    for harness in ("H-OSW", "H-GA"):
        scale = corpus.SCALES[harness]
        for px in range(0, 1920, 7):
            assert abs(scale(corpus.grid_value(px, 1920, scale), 1920) - px) <= 1
        for px in range(0, 1080, 5):
            assert abs(scale(corpus.grid_value(px, 1080, scale), 1080) - px) <= 1
    osw = {c["id"]: c["expect"] for c in CELLS["layers"]["H-OSW-fixed"] if c["source"] == "r-case"}
    ga = {c["id"]: c["expect"] for c in CELLS["layers"]["H-GA"] if c["source"] == "r-case"}
    for cid in ("R01", "R02", "R05", "R06", "R09", "R14"):
        assert osw[cid]["events"] == ga[cid]["events"], cid


def test_render_turn_matches_the_chat_template():
    jinja2 = pytest.importorskip("jinja2")
    template_path = ROOT / "harness/q2/action_path/qwen35_chat_template.jinja"
    if not template_path.exists():
        pytest.skip("template copy not present")
    data = template_path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == corpus.TEMPLATE_SHA256
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    env.filters["tojson"] = lambda x, **k: json.dumps(x, ensure_ascii=False)
    env.filters.setdefault("items", lambda mapping: list(mapping.items()))  # jinja2 < 3.1

    def raise_exception(message):
        raise RuntimeError(message)

    env.globals["raise_exception"] = raise_exception
    template = env.from_string(data.decode("utf-8"))
    calls = [
        {"action": "left_click", "coordinate": [500, 300], "text": "ctrl"},
        {"action": "key", "keys": ["ctrl", "c"]},
    ]
    for content in ("", corpus.ACTION_SENTENCE):
        message = {
            "role": "assistant",
            "content": content,
            "tool_calls": [{"function": {"name": "computer_use", "arguments": c}} for c in calls],
        }
        rendered = template.render(messages=[{"role": "user", "content": "go"}, message])
        body = rendered.split("<|im_start|>assistant\n", 1)[1].split("<|im_end|>", 1)[0]
        body = body.split("</think>\n\n", 1)[1] if "</think>" in body else body
        assert body == corpus.render_turn(calls, content=content)


def test_vendored_upstream_blocks_match_their_recorded_digests():
    upstream = ROOT / "harness/q2/action_path/upstream"
    provenance = json.loads((upstream / "PROVENANCE.json").read_text())
    from harness.q2.action_path.upstream import vendor

    for name, module in provenance["modules"].items():
        text = (upstream / name).read_text(encoding="utf-8")
        for block, part in zip(
            module["blocks"],
            [p for p in vendor.MODULES[name]["parts"] if isinstance(p, tuple)],
            strict=True,
        ):
            assert block["lines"] == [part[1], part[2]]
            length = part[2] - part[1] + 1
            found = [
                "".join(text.splitlines(keepends=True)[i : i + length])
                for i in range(len(text.splitlines()))
            ]
            digests = {hashlib.sha256(chunk.encode("utf-8")).hexdigest() for chunk in found}
            assert block["sha256"] in digests, (name, block["lines"])
    for key, source in provenance["sources"].items():
        assert source["sha256"] == vendor.SOURCES[key]["sha256"]


def test_controls_reject_what_they_cannot_translate():
    with pytest.raises(controls.TranslationError):
        controls.translate_pyautogui("os.system('x')")
    with pytest.raises(controls.TranslationError):
        controls.translate_pyautogui("pyautogui.click(__import__('os'))")
