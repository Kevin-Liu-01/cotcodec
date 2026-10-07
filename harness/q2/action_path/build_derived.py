"""Author tool that writes the files derived from ``catalog.yaml``.

``gating_set.json`` (G and the non-gating entries with reasons),
``expressible_entries.json`` (per Stage-1 harness), ``rdev_plan.json`` and
``volume_plan.json`` are all functions of the catalog and the committed rules
in ``vocab.py``, ``rdev.py`` and ``volume.py``. Tests check that this module
reproduces each committed file byte for byte, so none can drift by hand.

Run ``python -m harness.q2.action_path.build_derived`` from the repository root.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.q2.action_path import catalog as cat
from harness.q2.action_path import rdev, volume
from harness.q2.action_path.ir import parse_sequence
from harness.q2.action_path.vocab import harness_expressible

HERE = Path(__file__).resolve().parent


def _dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def render_gating(data: dict[str, Any]) -> str:
    return cat.gating_set_json(cat.validate(data)) + "\n"


def render_expressible(data: dict[str, Any]) -> str:
    entries = [(e["id"], parse_sequence(e["actions"])) for e in data["entries"]]
    return _dump(harness_expressible(entries))


def render_rdev_plan(data: dict[str, Any]) -> str:
    return rdev.plan_json(rdev.build_plan(data))


def render_volume_plan(data: dict[str, Any]) -> str:
    return _dump(volume.build_plan(data))


RENDERERS = {
    "gating_set.json": render_gating,
    "expressible_entries.json": render_expressible,
    "rdev_plan.json": render_rdev_plan,
    "volume_plan.json": render_volume_plan,
}


def main() -> int:
    data = cat.load()
    for name, render in RENDERERS.items():
        (HERE / name).write_text(render(data), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
