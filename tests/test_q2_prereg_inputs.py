"""q2-action-path-v1 and its two addenda: the inputs they pin match the repository."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import corpus

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-action-path-v1.md"
INPUTS = ROOT / "program/preregistrations/q2-action-path-v1-inputs.md"
EXECUTOR = ROOT / "program/preregistrations/q2-action-path-v1-executor.md"
DOCS = (PREREG, INPUTS, EXECUTOR)
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
LINT = re.compile(r"\bTBD\b|<[A-Za-z_ -]+>")  # scripts/preregister.py's freeze rule


def _pinned(doc: Path = PREREG) -> dict[str, str]:
    text = doc.read_text(encoding="utf-8")
    section = text.split("Frozen with this file", 1)[1].split("\n\n", 2)[1]
    rows = {}
    for line in section.splitlines():
        match = ROW.match(line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_every_pinned_input_matches_its_digest(doc):
    rows = _pinned(doc)
    assert len(rows) >= 20
    for relative, digest in rows.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == digest, f"{relative} changed; refresh {doc.name}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_drafts_pass_the_freeze_lint(doc):
    text = doc.read_text(encoding="utf-8")
    assert not LINT.search(text)
    assert "**Status: DRAFT. Not frozen.**" in text


CODE = {"ir.py", "vocab.py", "catalog.py", "rdev.py", "l0_raw.py", "volume.py"}
CODE |= {"build_catalog.py", "build_derived.py"}


def test_the_pins_cover_every_suite_input_file():
    main = set(_pinned(PREREG))
    every = main | set(_pinned(INPUTS)) | set(_pinned(EXECUTOR))
    folder = ROOT / "harness/q2/action_path"
    suite = {
        f"harness/q2/action_path/{p.name}"
        for p in folder.iterdir()
        if p.suffix in (".yaml", ".json", ".jinja") or p.name in CODE
    }
    assert suite <= every, suite - every
    assert {f"harness/q2/action_path/{name}" for name in CODE} <= main
    assert "harness/q2/vm/guest/xrecord_tap.py" in main
    code = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "harness/q2").rglob("*")
        if p.is_file()
        and p.suffix in (".py", ".json", ".yaml", ".md", ".jinja")
        and p.name not in ("__init__.py", "README.md")
        and "__pycache__" not in p.parts
    }
    unpinned = code - every
    assert not unpinned, sorted(unpinned)


def test_c2_cells_are_a_function_of_the_frozen_catalog():
    data = cat.load()
    cells = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
    expected = json.loads(json.dumps(corpus.l0_cells(data, cat.validate(data)["gating"])))
    assert cells["layers"]["L0-fixed"] == expected


def test_draft_passes_the_freeze_lint_and_states_the_committed_numbers():
    text = PREREG.read_text(encoding="utf-8")
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
