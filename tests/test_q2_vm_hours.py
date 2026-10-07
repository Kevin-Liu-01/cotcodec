"""VM-hour sizing (preregistration section 9, "Cost"): vm_hours.json reproduces from the
measured trial times, and the preregistration states its totals."""

from __future__ import annotations

import json
from pathlib import Path

from harness.q2.action_path import vm_hours

ROOT = Path(__file__).resolve().parents[1]
TIMES = ROOT / "harness/q2/action_path/trial_times.json"
HOURS = ROOT / "harness/q2/action_path/vm_hours.json"
PREREG = ROOT / "program/preregistrations/q2-action-path-v1.md"


def test_vm_hours_reproduces_from_the_measured_trial_times():
    measured = json.loads(TIMES.read_text(encoding="utf-8"))
    assert json.loads(HOURS.read_text(encoding="utf-8")) == json.loads(
        json.dumps(vm_hours.plan(measured))
    )


def test_every_layer_and_setting_was_measured_on_every_cell():
    measured = json.loads(TIMES.read_text(encoding="utf-8"))
    cells = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
    for layer in ("L0-fixed", "H-OSW-fixed", "H-GA"):
        ids = {c["id"] for c in cells["layers"][layer]}
        for setting in ("screenshot", "screenshot+a11y"):
            assert set(measured["trials"][layer][setting]) == ids, (layer, setting)
    pairs = {
        f"{app}:{entry}"
        for app, spec in cells["canary"]["apps"].items()
        for entry in spec["entries"]
    }
    assert set(measured["canary"]) == pairs


def test_the_preregistration_states_the_a4_and_total_vm_hours():
    hours = json.loads(HOURS.read_text(encoding="utf-8"))
    text = " ".join(PREREG.read_text(encoding="utf-8").split())
    assert f"{hours['campaigns']['A4']['vm_hours']:.1f} VM-hours" in text
    assert f"{hours['total_vm_hours']:.1f} VM-hours" in text
