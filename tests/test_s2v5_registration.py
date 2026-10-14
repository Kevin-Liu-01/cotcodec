"""S2 v5 registration: v4's text with exactly D96's change, the K0 commitment and freeze hygiene."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.s2_locale import ap_delta as D
from harness.s2_locale import ap_delta_v5 as V
from harness.s2_locale import k0_v4 as K
from harness.s2_locale import pins_table, pins_table_v5
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / V.REGISTRATION
V4 = ROOT / "program/preregistrations/s2-arabic-cua-locale-v4.md"
EXPERIMENT_ID = "s2-arabic-cua-locale-v5"
# K0's section as v4 committed it before any Phase 0 result (tests/test_s2v4_registration.py)
K0_SECTION_SHA256 = "ed38b953c7934169fcede7b45ec5dc1b568afd5855c6008830aada68cf131a03"
FROZEN = ("**Status: frozen in `program/preregistrations/ledger.jsonl`; see the ledger row for the "
          "freeze time and `git_head_at_freeze`.**")  # fmt: skip
# v4's sections that v5 copies byte for byte, and the ones it replaces or adds (D96's change and
# the id-level changes; section "What changed from v4, and why").
VERBATIM = (
    "## What changed from v3.1, and why", "## Question", "## Tasks (", "## Phase 0 (",
    "## Images built", "## K0: ", "## What the D53 certification", "## Development smoke",
    "## Phase 1 (", "## Estimands", "## Decision rules", "## Predictions and falsifiers",
    "## Statistics, sample sizes", "## Seeds", "## Compute caps", "## Infrastructure failures",
    "## Data rights", "## Integrity gate", "## Changes in the repair round",
    "## Changes in the third round", "## Changes in round 4",
)  # fmt: skip
REPLACED = (
    "## Identity",
    "## K1: ",
    "## Kill criteria",
    "## Owner's prior forecast",
    "## Freeze procedure",
    "## Code and inputs of record",
    "## Design decisions",
)
ADDED = ("## What changed from v4, and why",
         "## Fixed screen coordinates in every v5 check and capture step (D94's process gap)",
         "## v5 development: step 0 and the confirmation (a pre-freeze gate)",
         "## Disclosures (v5)",
         "## v5's review log")  # fmt: skip
# v5's own files of record at the digests the development confirmation ran (Slurm 1278 and 1291,
# D98; harness/ and infra/ unchanged since), and step 0's result at its pinned digest. The status
# fill re-fills the table from the tree, so without these a change to one of them after the
# confirmation would pass unnoticed (the round's pre-freeze audit, D98). v4's files and
# harness/q2 are fixed by v4's frozen table.
V5_CONFIRMED = {
    "harness/s2_locale/ap_delta_v5.py":
        "fee65229fa7148b1d8a436cf62bd3dd6e5545d2c1186ed91b694f96c0237ba1e",
    "harness/s2_locale/lane_v5.py":
        "864060628b3813cf7c4bff81b4ce8a669ba17e0c13a62965101399ef77b30b37",
    "harness/s2_locale/canary_v5/suite_cells-ER.json":
        "464c9ab2aecf11c5e6405afac3a3f5ef8d5fa6f33b286bfcbd960624f049f070",
    "harness/s2_locale/canary_v5/suite_cells-AR.json":
        "b81b63c6973fd21598965c1fd06247401c63e8c6bf979c2fc15e74ac3dfa4726",
    "infra/slurm/host-single-node/s2v5-apdelta.sbatch":
        "df6b936db2291864884bbb2f1a028c4cf12bf417ebd608b367ce2c2fbd918bb7",
    "infra/slurm/host-single-node/s2v5-vm.sbatch":
        "ccc0fcd542ce2dd33e779e9fae3b6410d5d8c1f5db1896454d12fcc42f5d6514",
    "program/evidence/2026-10-13/s2v5-step0/step0-result.json":
        "18d8b910175ffe084a20f6a3e6963e71e205cfd170d4fcd24d16c0633f85e5d6",
}  # fmt: skip


def _chunks(text: str) -> dict[str, str]:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    out = {}
    for k, i in enumerate(starts):
        j = starts[k + 1] if k + 1 < len(starts) else len(lines)
        out[lines[i].strip()] = "".join(lines[i:j])
    return out


def _one(chunks: dict[str, str], prefix: str) -> str:
    keys = [k for k in chunks if k.startswith(prefix)]
    assert len(keys) == 1, (prefix, keys)
    return chunks[keys[0]]


def _k0_text(path: Path) -> str:
    m = re.search(r"<!-- K0:BEGIN -->\n(.*?)<!-- K0:END -->", path.read_text(encoding="utf-8"),
                  re.S)  # fmt: skip
    assert m, "the K0 markers are missing"
    return m.group(1)


def test_k0_section_is_v4s_committed_text():
    assert hashlib.sha256(_k0_text(REG).encode()).hexdigest() == K0_SECTION_SHA256
    assert _k0_text(REG) == _k0_text(V4)


def test_k0_code_constants_match_the_text():
    text = _k0_text(REG)
    assert f"at least {K.K_MIN} tasks are admitted" in text
    assert "at least 95%" in text and K.SHARE == 0.95
    assert "at least 90%" in text and K.DESCRIPTOR_SHARE == 0.90
    assert f"max({K.TOL_FLOOR_PX}\npx" in text or f"max({K.TOL_FLOOR_PX} px" in text
    assert f"rows 0-{K.SHELL_ROWS - 1}" in text
    for task in K.PD_VISIBLE_DEV + K.C1_TASKS:
        assert f"`{task}`" in text


def test_v4_is_the_frozen_file_and_is_not_edited():
    row = V.ledger_row(ROOT, V.V4_ID)
    assert row is not None and row["path"] == "program/preregistrations/s2-arabic-cua-locale-v4.md"
    assert row["sha256"] == hashlib.sha256(V4.read_bytes()).hexdigest()


def test_v5_is_v4_with_exactly_the_listed_sections_changed():
    v4, v5 = _chunks(V4.read_text(encoding="utf-8")), _chunks(REG.read_text(encoding="utf-8"))
    for prefix in VERBATIM:
        assert _one(v5, prefix) == _one(v4, prefix), prefix
    assert sorted(v5) == sorted([*v4, *ADDED]), "the section list is v4's plus v5's five"
    for prefix in REPLACED:
        assert _one(v5, prefix) != _one(v4, prefix), prefix
    # Kill criteria: only K1's row
    k4, k5 = _one(v4, "## Kill criteria"), _one(v5, "## Kill criteria")
    diff = [(a, b) for a, b in zip(k4.splitlines(), k5.splitlines(), strict=True) if a != b]
    assert len(diff) == 1 and diff[0][0].startswith("| K1 |") and diff[0][1].startswith("| K1 |")
    assert "S2 ends at an honest exit" in diff[0][1] and "last registration" in diff[0][1]
    # Design decisions: v4's list, then 104-109
    d4, d5 = _one(v4, "## Design decisions"), _one(v5, "## Design decisions")
    assert d5.startswith(d4.rstrip() + "\n\nAdded in v5 (D94, D96):")
    assert [int(n) for n in re.findall(r"^(\d+)\. ", d5[len(d4) :], re.M)] == list(range(104, 110))
    # Identity: v4's bullets after the first, verbatim
    i4, i5 = _one(v4, "## Identity"), _one(v5, "## Identity")
    rest = i4[i4.index("- Model: ") :]
    assert i5.endswith(rest)
    # K1: v4's table rows but A6's, and v4's rung rule, verbatim
    q4, q5 = _one(v4, "## K1: "), _one(v5, "## K1: ")
    rows4 = [x for x in q4.splitlines() if x.startswith("| ")]
    rows5 = [x for x in q5.splitlines() if x.startswith("| ") and x in q4.splitlines()]
    assert [x for x in rows4 if not x.startswith("| A6 ")] == [
        x for x in rows5 if not x.startswith("| A6 ")
    ]
    rung = q4[q4.index("The rung qualifies") : q4.index("Total about 44.3")]
    assert rung in q5


def test_the_change_is_d96s_targets():
    text = " ".join(REG.read_text(encoding="utf-8").split())
    q5 = " ".join(_one(_chunks(REG.read_text(encoding="utf-8")), "## K1: ").split())
    for cell in ("E", "A", "ER", "AR", "PL"):
        t = V.targets(ROOT, cell)["writer"]
        d, c = t["drag_select_word"], t["triple_click_line"]
        bold = "**" if cell in ("ER", "AR") else ""
        drag = f"{bold}({d['from'][0]}, {d['from'][1]}) to ({d['to'][0]}, {d['to'][1]}){bold}"
        click = f"{bold}({c['x']}, {c['y']}){bold}"
        assert f"| {cell} | {drag} | {click} | q2's |" in q5, cell
    assert V.STEP0_RESULT_SHA256 in text
    for cell, sha in V.CELLS_SHA256.items():
        assert sha in text and V.CELLS_FILES[cell].split("/")[-1] in text
    assert "v5 is S2's last registration" in text
    assert "a repair is a new image" in text and "is set aside" in text


def test_every_fixed_coordinate_is_inventoried():
    """The D94 process gap: the coordinate section names every fixed coordinate of the code."""
    import yaml

    from harness.s2_locale import vm_probe as P

    sec = " ".join(_one(_chunks(REG.read_text(encoding="utf-8")),
                        "## Fixed screen coordinates").split())  # fmt: skip
    x, y = P.POINTER_TARGET
    assert f"({x}, {y})" in sec
    catalog = yaml.safe_load((ROOT / "harness/q2/action_path/catalog.yaml").read_text())
    px, py = catalog["guard"]["park_pointer"]
    assert f"({px}, {py})" in sec
    from harness.q2.vm.guest import probe

    assert f"({probe.MARKER_ORIGIN[0]}, {probe.MARKER_ORIGIN[1]})" in sec
    assert f"{probe.MARKER_BITS} cells of {probe.CELL} x {probe.CELL} px" in sec
    for cell in V.K1_CELLS:
        for app, entries in V.targets(ROOT, cell).items():
            d, c = entries["drag_select_word"], entries["triple_click_line"]
            assert f"({d['from'][0]}, {d['from'][1]}) to ({d['to'][0]}, {d['to'][1]})" in sec, app
            assert f"({c['x']}, {c['y']})" in sec, app
    assert f"rows 0-{K.SHELL_ROWS - 1}" in sec and "rows 1060-1079" in sec
    assert "`66399b0d`" in sec and "`6ada715d`" in sec and "(1728, 972)" in sec


def test_freezable_and_names_itself():
    text = REG.read_text(encoding="utf-8")
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text), "freeze refuses placeholders"
    assert "@@" not in text, "an unfilled marker"
    assert (
        "preregister.py freeze s2-arabic-cua-locale-v5 "
        "program/preregistrations/s2-arabic-cua-locale-v5.md"
    ) in text
    assert text.startswith("# S2 v5:") and "(s2-arabic-cua-locale-v5)" in text.splitlines()[0]


def _status_line(text: str) -> str:
    return next(line for line in text.splitlines() if line.startswith("**Status: "))


def test_status_wording_follows_the_ledger():
    """The D32 defect class: before the freeze the status line is DRAFT, or (the status-fill
    commit) the frozen wording; once this id has a ledger row, only the frozen wording, and the
    file is the one the row froze."""
    text = REG.read_text(encoding="utf-8")
    status = _status_line(text)
    row = V.ledger_row(ROOT)
    if row is not None:
        assert status.startswith("**Status: frozen in") and "DRAFT" not in status
        assert row["path"] == V.REGISTRATION
        assert row["sha256"] == hashlib.sha256(REG.read_bytes()).hexdigest()
    else:
        assert status.startswith(("**Status: DRAFT", "**Status: frozen in"))
    flat = " ".join(text.split())
    assert " ".join(FROZEN.split()) in flat


def test_registration_freezes_against_a_scratch_ledger(tmp_path):
    """The freeze command accepts this file; the real ledger is not touched."""
    from scripts import preregister

    ledger = tmp_path / "ledger.jsonl"
    real = (ROOT / L.LEDGER).read_bytes()
    row = preregister.freeze(REG, EXPERIMENT_ID, ledger=ledger)
    assert row["path"] == V.REGISTRATION
    assert row["sha256"] == hashlib.sha256(REG.read_bytes()).hexdigest()
    assert (ROOT / L.LEDGER).read_bytes() == real


def test_code_and_inputs_of_record_table_is_the_tree():
    text = REG.read_text(encoding="utf-8")
    table = pins_table_v5.read(text)
    assert table == pins_table_v5.digests(ROOT)
    # every file v4's frozen table pins has v4's digest
    v4 = pins_table.read(V4.read_text(encoding="utf-8"))
    assert {f: table[f] for f in v4} == v4
    for f in pins_table_v5.V5_FILES:
        assert f in table


def test_v5s_own_files_are_the_files_the_confirmation_ran():
    """After the confirmation, a re-fill of the table cannot absorb a change to v5's own files: each
    holds the digest the confirmation ran, in the tree and in the table (D98)."""
    assert set(V5_CONFIRMED) == set(pins_table_v5.V5_FILES)
    table = pins_table_v5.read(REG.read_text(encoding="utf-8"))
    for f, sha in V5_CONFIRMED.items():
        assert hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha, f
        assert table[f] == sha, f
    assert V5_CONFIRMED[V.STEP0_RESULT] == V.STEP0_RESULT_SHA256
    for cell, sha in V.CELLS_SHA256.items():
        assert V5_CONFIRMED[V.CELLS_FILES[cell]] == sha, cell


def test_code_of_record_includes_the_shared_code_the_lanes_import():
    from harness.q2.vm.manifest import closed_world

    listed = set(pins_table_v5.read(REG.read_text(encoding="utf-8")))
    closure = set(pins_table.import_closure(ROOT, pins_table_v5.ENTRIES))
    for shared in (
        "harness/q2/vm/driver.py",
        "harness/s2_locale/ap_delta.py",
        "harness/s2_locale/vm_lane.py",
        "harness/s2_locale/k0_v4.py",
        "harness/s2_locale/ap_delta_v5.py",
        "harness/s2_locale/lane_v5.py",
    ):
        assert shared in closure, shared
    assert closure | set(pins_table.GUEST) | set(closed_world(str(ROOT))) <= listed


def test_registration_states_the_pinned_digests():
    flat = " ".join(REG.read_text(encoding="utf-8").split())
    assert L.CENSUS_SHA256 in flat and L.PD_CACHE_FILES_SHA256 in flat
    assert D.K1_PLAN_SHA256 in flat
    golds = hashlib.sha256((ROOT / L.GOLDS).read_bytes()).hexdigest()
    assert golds in flat
    pins = json.loads((ROOT / L.IMAGES).read_text())
    assert pins["build"]["derived_base"]["sha256"] in flat
    for cell, entry in pins["cells"].items():
        assert f"| {cell} | `{entry['sha256']}` |" in flat, cell


def test_registration_states_the_one_infrastructure_rule_everywhere():
    text = REG.read_text(encoding="utf-8")
    p07 = text.split("### P0.7", 1)[1].split("### P0.8", 1)[0]
    phase1 = text.split("## Phase 1 (", 1)[1].split("## Estimands", 1)[0]
    infra = text.split("## Infrastructure failures and exclusions", 1)[1].split("## Data rights")[0]
    for section in (p07, phase1, infra):
        flat = " ".join(section.split())
        assert "status of 500 or above" in flat and "infrastructure loss" in flat
        assert "returncode" in flat


def test_step0s_record_and_pinned_files_are_unchanged():
    from harness.s2_locale import canary_targets_v5 as R

    pins = R.check_pins(ROOT)  # raises if any file step0-rule.json pins differs
    assert "program/preregistrations/s2-arabic-cua-locale-v5-step0.md" in pins
