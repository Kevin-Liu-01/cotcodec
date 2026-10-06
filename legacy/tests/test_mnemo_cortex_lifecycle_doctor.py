from __future__ import annotations

import runpy
from pathlib import Path
from types import SimpleNamespace


def test_route_paths_tolerates_and_traverses_internal_routers(
    monkeypatch,
) -> None:
    monkeypatch.setenv("COTCODEC_RUN_TOKEN", "TEST")
    monkeypatch.setenv("COTCODEC_PHASE", "1")
    doctor = runpy.run_path(
        str(
            Path(__file__).parents[1]
            / "infra/memory-baselines/mnemo-cortex/doctor.py"
        )
    )
    leaf = SimpleNamespace(path="/memory/purge")
    internal = SimpleNamespace(routes=[leaf])
    app = SimpleNamespace(
        routes=[SimpleNamespace(path="/writeback"), internal, object()]
    )
    assert doctor["_route_paths"](app) == ["/memory/purge", "/writeback"]
