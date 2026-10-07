"""Author tool that writes ``suite_cells.json``: every cell the VM runner executes.

The runner image has the standard library only (no YAML), so the cells it
runs are derived here, deterministically, from the frozen inputs:
``catalog.yaml`` (L0-fixed cells), ``expressible_entries.json`` and
``corpus.py`` (the H-OSW-fixed and H-GA cells with their perturbation
variants, and the C1 control cells), ``canary.yaml`` with
``canary_targets.json`` when it exists (the A6 canary), and the probe's
guard settings. ``tests/test_q2_corpus.py`` checks that this module
reproduces the committed file byte for byte.

Run ``python -m harness.q2.action_path.build_suite`` from the repository root.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import corpus
from harness.q2.action_path.ir import parse_sequence

HERE = Path(__file__).resolve().parent
SCHEMA = "cotcodec-q2-suite-cells-v1"
LAYERS = ("L0-fixed", "H-OSW-fixed", "H-GA", "H-OSW-up", "H-GA-buggy")
INPUTS = ("catalog.yaml", "expressible_entries.json", "gating_set.json", "canary.yaml")


def _sha256(name: str) -> str:
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


def canary_cells(
    canary: dict[str, Any], data: dict[str, Any], targets: dict[str, Any]
) -> dict[str, Any]:
    by_id = {e["id"]: e for e in data["entries"]}
    entries: dict[str, Any] = {}
    for entry in canary["entries"]:
        fixture = canary["fixtures"][entry["fixture"]]
        if entry.get("actions") == "catalog":
            actions = [a.to_dict() for a in parse_sequence(by_id[entry["id"]]["actions"])]
            expect = by_id[entry["id"]]["expect"]["text"]
            needs = None
        elif any("target" in a for a in entry["actions"]):
            actions = [dict(a) for a in entry["actions"]]
            expect = entry["expect"]
            needs = entry["id"]
        else:
            actions = [a.to_dict() for a in parse_sequence(entry["actions"])]
            expect = entry["expect"]
            needs = None
        entries[entry["id"]] = {
            "fixture": entry["fixture"],
            "fixture_text": fixture,
            "actions": actions,
            "expect": expect,
            "needs_targets": needs,
        }
    apps: dict[str, Any] = {}
    for name, app in canary["apps"].items():
        ids = list(entries) if app["entries"] == "all" else list(app["entries"])
        spec: dict[str, Any] = {"entries": ids, "readback": app["readback"]}
        if name == "chrome":
            spec["flags"] = re.findall(r"--[a-z][a-z-]*(?:=[a-z]+)?", app["program"])
            spec["page"] = app["page"]
        if name == "vscode":
            spec["settings"] = app["settings"]
        if name == "terminal":
            spec["finish_rule"] = "ctrl_d_once_if_empty_or_newline_else_twice"
        else:
            spec["finish_keys"] = app.get("finish_keys") or []
        spec["targets"] = targets.get(name, {})
        apps[name] = spec
    return {"reps": canary["reps"], "apps": apps, "entries": entries}


def build(data: dict[str, Any] | None = None) -> dict[str, Any]:
    import yaml

    data = data or cat.load()
    summary = cat.validate(data)
    expressible = json.loads((HERE / "expressible_entries.json").read_text(encoding="utf-8"))
    canary = yaml.safe_load((HERE / "canary.yaml").read_text(encoding="utf-8"))
    targets_path = HERE / "canary_targets.json"
    targets = {}
    if targets_path.exists():
        targets = json.loads(targets_path.read_text(encoding="utf-8"))["apps"]
    layers = {
        "L0-fixed": corpus.l0_cells(data, summary["gating"]),
        "H-OSW-fixed": corpus.harness_cells(data, expressible, "H-OSW"),
        "H-GA": corpus.harness_cells(data, expressible, "H-GA"),
        "H-OSW-up": corpus.control_cells(data, "H-OSW-up"),
        "H-GA-buggy": corpus.control_cells(data, "H-GA-buggy"),
    }
    inputs = {name: _sha256(name) for name in INPUTS}
    if targets_path.exists():
        inputs["canary_targets.json"] = _sha256("canary_targets.json")
    return {
        "schema": SCHEMA,
        "inputs": inputs,
        "template": corpus.TEMPLATE,
        "guard": data["guard"],
        "layers": layers,
        "canary": canary_cells(canary, data, targets),
    }


def render() -> str:
    return json.dumps(build(), indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main() -> int:
    (HERE / "suite_cells.json").write_text(render(), encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
