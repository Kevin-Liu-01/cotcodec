"""q2-action-path-v2 and its two addenda: the inputs they pin match the repository.

v1 (q2-action-path-v1 and its addenda) is frozen in the ledger and invalid on C2 (decision
D40); its files must stay as frozen, and v2's tables must equal v1's except for the rows
v2's section 24 names.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import corpus

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "program/preregistrations/q2-action-path-v2.md"
INPUTS = ROOT / "program/preregistrations/q2-action-path-v2-inputs.md"
EXECUTOR = ROOT / "program/preregistrations/q2-action-path-v2-executor.md"
DOCS = (PREREG, INPUTS, EXECUTOR)
V1 = {
    "q2-action-path-v1": ROOT / "program/preregistrations/q2-action-path-v1.md",
    "q2-action-path-v1-inputs": ROOT / "program/preregistrations/q2-action-path-v1-inputs.md",
    "q2-action-path-v1-executor": ROOT / "program/preregistrations/q2-action-path-v1-executor.md",
}
# The rows of v2's frozen tables that decision D40 changes (main section 24, item 7);
# every other row must equal v1's.
D40_ROWS = {
    PREREG: {"harness/q2/action_path/l0_raw_prediction_v2.yaml"},
    INPUTS: {
        "harness/q2/action_path/order.py",
        "harness/q2/vm/manifest.py",
        "harness/q2/vm/driver.py",
        "harness/q2/action_path/acceptance.py",
    },
    EXECUTOR: {
        "harness/q2/action_path/acceptance.py",
        "scripts/render_q2_action_path_manifest.py",
        "harness/q2/vm/driver.py",
        "harness/q2/vm/manifest.py",
    },
}
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


FROZEN_STATUS = (
    "**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger\n"
    "row for the freeze time and `git_head_at_freeze`.**"
)
FREEZE_ORDER = ("`q2-action-path-v2`", "`q2-action-path-v2-inputs`", "`q2-action-path-v2-executor`")


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_drafts_pass_the_freeze_lint_with_the_frozen_status(doc):
    """A frozen file cannot be edited, so each status paragraph has the frozen wording
    before the freeze (decision D39, as D32 required for Q3): the ledger row, the freeze
    order and what may not run before the row exists."""
    text = doc.read_text(encoding="utf-8")
    assert not LINT.search(text)
    status = text.split("\n\n")[1]
    assert status.startswith(FROZEN_STATUS)
    for stale in ("DRAFT", "Draft", "Not frozen", "not frozen", "owner reviews", "owner freezes"):
        assert stale not in status
    positions = [status.find(name) for name in FREEZE_ORDER]
    assert -1 not in positions and positions == sorted(positions), positions
    assert "No acceptance trial" in status and "may run before this row exists" in status
    controls = "no C1 or C3" if doc == EXECUTOR else "no C2, C1 or C3"
    assert controls in status
    assert "q2-action-path-v1" not in status


def test_v1_stays_as_frozen_in_the_ledger():
    """v1's three registrations are unchanged since their ledger rows (decision D40)."""
    from scripts import preregister

    for experiment, path in V1.items():
        row = preregister.verify(experiment)
        assert row["path"] == path.relative_to(ROOT).as_posix()


@pytest.mark.parametrize("doc", DOCS, ids=lambda d: d.stem)
def test_v2_tables_are_v1s_except_the_rows_d40_changes(doc):
    v1 = _pinned(V1[doc.stem.replace("-v2", "-v1")])
    v2 = _pinned(doc)
    assert set(v1) <= set(v2)
    differ = {path for path, digest in v2.items() if v1.get(path) != digest}
    assert differ == D40_ROWS[doc], sorted(differ ^ D40_ROWS[doc])


def test_v2_names_its_changes_from_v1_and_v1s_outcome():
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        assert "Changes from v1 (D40)" in text, doc.name
        changes = " ".join(text.split("Changes from v1 (D40)", 1)[1].split())
        for path in D40_ROWS[doc]:
            assert path.split("/")[-1] in changes, (doc.name, path)
    main = " ".join(PREREG.read_text(encoding="utf-8").split())
    assert "program/evidence/2026-10-08/q2-action-path-acceptance/" in main
    assert "not an a-priori prediction test" in main
    assert "one unpredicted failure" in main and "verified real at the X event level" in main
    assert "seed-45 shuffle" in main


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
