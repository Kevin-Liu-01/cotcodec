"""Suite-mutation kit: every scored mutant applies, and parser mutants change a kill cell's IR."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from harness.q2.action_path import adapters, mutants

ROOT = Path(__file__).resolve().parents[1]
OPERATORS = yaml.safe_load((ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text())
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
PAIRS = mutants.scored_pairs(OPERATORS)
PARSER_PAIRS = [p for p in PAIRS if p[1] != "L0-fixed"]
PREDICTED_EQUIVALENT = {
    (op["id"], layer)
    for op in OPERATORS["operators"]
    for layer, spec in op["applies"].items()
    if spec.get("predicted") == "equivalent"
}


def test_the_kit_covers_exactly_the_scored_pairs():
    assert len(PAIRS) == 44
    assert set(mutants.PATCHES) == set(PAIRS)
    unscored = [
        (op["id"], layer)
        for op in OPERATORS["operators"]
        for layer, spec in op["applies"].items()
        if spec["status"] != "scored"
    ]
    assert sorted(unscored) == sorted(
        [
            ("M01-modifier-released-early", "H-GA"),
            ("M13-hscroll-to-vscroll", "H-GA"),
            ("M28-modifier-text-ignored", "H-GA"),
        ]
    )


@pytest.mark.parametrize("pair", PAIRS, ids=lambda p: f"{p[0]}@{p[1]}")
def test_every_scored_mutant_applies_and_changes_the_source(pair):
    sources = mutants.build(*pair)
    assert sources
    for path, text in sources.items():
        assert text != (ROOT / path).read_text(encoding="utf-8")


@pytest.fixture
def restore_modules():
    names = list(mutants.MODULE_NAMES.values())
    saved = {name: sys.modules.get(name) for name in names}
    controls = adapters.controls
    yield
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module
    adapters.controls = controls


def _ir(parse, cell):
    out = []
    for turn in cell["turns"]:
        try:
            out.append(json.dumps(parse(turn), sort_keys=True))
        except Exception as exc:  # noqa: BLE001 - a raising parser is a changed outcome
            out.append(f"raise {type(exc).__name__}")
    return out


@pytest.mark.parametrize("pair", PARSER_PAIRS, ids=lambda p: f"{p[0]}@{p[1]}")
def test_parser_mutants_change_the_ir_of_a_predicted_kill_cell(pair, restore_modules):
    operator, layer = pair
    cells = {c["id"]: c for c in CELLS["layers"][layer]}
    original = {cid: _ir(adapters.LAYERS[layer], cell) for cid, cell in cells.items()}
    parse = mutants.load_layer(layer, mutants.build(operator, layer))
    changed = {cid for cid, cell in cells.items() if _ir(parse, cell) != original[cid]}
    spec = next(o for o in OPERATORS["operators"] if o["id"] == operator)["applies"][layer]
    if pair in PREDICTED_EQUIVALENT:
        assert not changed
        return
    in_spec = {cid for cid in changed if cells[cid]["status"] != "outside"}
    assert in_spec, f"{operator} on {layer} changes no in-spec cell"
    assert set(spec["kill_cells"]) & changed, (operator, layer, sorted(changed))
