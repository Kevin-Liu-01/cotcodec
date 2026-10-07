"""q2-action-path-v1 draft: the inputs it pins match the repository (review finding 5)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.q2.action_path import catalog as cat

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-action-path-v1.md"
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")


def _pinned() -> dict[str, str]:
    text = PREREG.read_text(encoding="utf-8")
    section = text.split("Frozen with this file", 1)[1].split("\n\n", 2)[1]
    rows = {}
    for line in section.splitlines():
        match = ROW.match(line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def test_every_pinned_input_matches_its_digest():
    rows = _pinned()
    assert len(rows) >= 20
    for relative, digest in rows.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == digest, f"{relative} changed; update the preregistration draft"


CODE = {"ir.py", "vocab.py", "catalog.py", "rdev.py", "l0_raw.py", "volume.py"}
CODE |= {"build_catalog.py", "build_derived.py"}


def test_the_pins_cover_every_suite_input_file():
    rows = set(_pinned())
    folder = ROOT / "harness/q2/action_path"
    suite = {
        f"harness/q2/action_path/{p.name}"
        for p in folder.iterdir()
        if p.suffix in (".yaml", ".json") or p.name in CODE
    }
    assert suite <= rows, suite - rows
    assert "harness/q2/vm/guest/xrecord_tap.py" in rows


def test_draft_passes_the_freeze_lint_and_states_the_committed_numbers():
    text = PREREG.read_text(encoding="utf-8")
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text)  # scripts/preregister.py rule
    assert "**Status: DRAFT. Not frozen.**" in text
    plan = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
    assert f"{plan['trials']:,} trials" in text
    assert f"{plan['sessions']:,}" in text and plan["order_sha256"] in text
    expressible = json.loads((ROOT / "harness/q2/action_path/expressible_entries.json").read_text())
    assert len(expressible["H-OSW"]["expressible"]) == 85 and "H-OSW 85" in text
    assert len(expressible["H-GA"]["expressible"]) == 79 and "H-GA 79" in text
    data = cat.load()
    certified = cat.certified_keysyms(data, cat.validate(data)["gating"])
    assert f"only the {len(certified)} keysyms" in text
    pattern = r"only the \d+ keysyms the\ngating entries use: (.*?)\n\(`catalog"
    listed = re.search(pattern, text, re.S)
    assert listed is not None
    assert sorted(re.findall(r"`([^`]+)`", listed.group(1))) == sorted(certified)
