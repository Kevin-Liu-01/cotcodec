"""Q2 cross-app canary (A6): fixtures and expected final text are frozen (review finding)."""

from __future__ import annotations

from pathlib import Path

import yaml

from harness.q2.action_path import catalog as cat
from harness.q2.action_path.ir import parse_sequence

HERE = Path(cat.__file__).resolve().parent


def _load():
    return yaml.safe_load((HERE / "canary.yaml").read_text(encoding="utf-8"))


def test_every_canary_entry_has_a_fixture_and_an_exact_expected_text():
    canary = _load()
    catalog = {e["id"]: e for e in cat.load()["entries"]}
    assert canary["reps"] == 5
    ids = [e["id"] for e in canary["entries"]]
    assert len(ids) == len(set(ids)) == 16
    for entry in canary["entries"]:
        assert entry["fixture"] in canary["fixtures"], entry["id"]
        if entry.get("expect_from") == "catalog":
            source = catalog[entry["id"]]
            assert entry["actions"] == "catalog"
            assert isinstance(source["expect"]["text"], str) and source["expect"]["text"]
            assert entry["fixture"] == "empty"
        else:
            assert isinstance(entry["expect"], str), entry["id"]
            ir_actions = [a for a in entry["actions"] if "target" not in a]
            parse_sequence(ir_actions)
    composite = {e["id"]: e for e in canary["entries"] if "expect" in e}
    assert composite["select_all_copy_end_paste"]["expect"] == "copy mecopy me"
    assert composite["triple_click_line"]["expect"] == "X"
    assert composite["drag_select_word"]["expect"] == "keep Y keep"
    assert composite["ctrl_home_insert"]["expect"] == "Zline a\nline b"
    assert composite["key_kp_enter"]["expect"] == "\n"
    # Single-line fixtures keep triple-click semantics the same in every app.
    for fixture in ("triple_line", "drag_word", "copy_paste"):
        assert "\n" not in canary["fixtures"][fixture]


def test_apps_are_configured_not_to_rewrite_typed_text():
    apps = _load()["apps"]
    assert set(apps) == {"writer", "chrome", "vscode", "terminal"}
    settings = apps["vscode"]["settings"]
    for key in ("editor.autoClosingBrackets", "editor.autoClosingQuotes", "editor.autoSurround"):
        assert settings[key] == "never"
    assert settings["editor.autoIndent"] == "none"
    assert settings["files.insertFinalNewline"] is False
    assert "Tab" in apps["chrome"]["page"] and "spellcheck" in apps["chrome"]["page"]
    assert any("AutoCorrect" in item for item in apps["writer"]["config"])
    terminal = set(apps["terminal"]["entries"])
    entries = {e["id"] for e in _load()["entries"]}
    assert terminal < entries
    assert not terminal & {"select_all_copy_end_paste", "triple_click_line", "drag_select_word"}
