"""q2-action-path-v2 (decision D40): what changed from v1 in the files a campaign executes.

v2 changes ``order.py``, ``manifest.py`` and ``driver.py`` (main preregistration section 24;
executor addendum section 9). Every realized order but C2's must stay v1's byte for byte:
the digests below were computed by v1's code (at ``124573a``, the commit D40 was recorded
at, whose planning code is v1's frozen code) with ``driver.acceptance_plan`` and
``driver.session_plan``, and ``order.order_sha256``. C2 moves from v1's seed-42 order
(``ca30ebf9...``, the order job 768 ran) to its own seed, 45.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.q2.action_path import order
from harness.q2.vm import driver
from harness.q2.vm.manifest import (
    CRITERIA,
    DEVELOPMENT_LAYERS,
    LADDER_RUNGS,
    RESERVED_SEEDS,
    ladder_reps,
)

ROOT = Path(__file__).resolve().parents[1]
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
VOLUME = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())
V1_C2_ORDER = "ca30ebf9ada0b174f7570d8d9573800f5783c80f3283ae3f1f71492916330276"
# (criterion, layer, seed[, rung]) -> (order_sha256, sessions), from v1's code.
V1_ORDERS = {
    "A1 L0-fixed 43": ("800f2a8be17ce1f7d885f9cd8990d764055ebaff7e093cca6d3169a6166469b7", 18),
    "A1 L0-fixed 44": ("96ae2be8a0f94272d877d415555004edcaf0efe36eb7a35bdf3e3210067baabf", 18),
    "A2 H-GA 43": ("1c27268754d151c56b7d2e975837e9bb35ea3134dfdcbb80da5adcad27c2d457", 16),
    "A2 H-OSW-fixed 43": ("e84acacfe4b10be60263988baf66e5c856ee828ca31dca761a50dc43003f7e83", 18),
    "A3 H-GA 43": ("320ea0c1b8cc771425738564b58516d9d63a6b0a0de911dde1dd4cb1a09861de", 24),
    "A3 H-OSW-fixed 43": ("bbda716e4b14fb71227cd141c5d7f8eb3895b690b3b0e5ab44ad0f9b0bf0148a", 30),
    "A3 L0-fixed 43": ("3bb33e4375ba3d5854f0abba9acf173f3996b036a8066f8d4681542a9505bbd5", 30),
    "A4 L0-fixed 43": ("d7c77687ab9e38f0b88ad82ada1cbff612f1a9dd5213696c217bb980217d8666", 1068),
    "A7 L0-fixed 43": ("d79f1c0d87ec973fa23fbda55faaf4f19d3af0b8a183259878c8fa1cbed78f27", 516),
    "C1 H-GA-buggy 42": ("35f06d88188788dd0d81d3101275676a29627a4b6213c39b525b89e57bea4740", 2),
    "C1 H-OSW-up 42": ("35f06d88188788dd0d81d3101275676a29627a4b6213c39b525b89e57bea4740", 2),
    "C3 H-GA 42": ("9e1352acabb5de05590ed83898e4c4e6ed2092a8bad64fa804ad753950f1ca60", 2),
    "C3 H-OSW-fixed 42": ("9432f175faab9a8e600586a8dc78ab825d9b96ffe7c327b9d54688f2b2de326b", 2),
    "C3 L0-fixed 42": ("f106d12202a37ac6e2725631052437d54de45d8f31964fd0e89d7da502da7c22", 2),
    "ladder 43 N8": ("ac8b222e0e5e4aa145bd9fb5e8743a6b6d88a420fc023146b9a0b6945b6806a0", 20),
    "ladder 43 N16": ("a18462913d199bf548e92772009e56f60fba351a02b2296672d3b3d505ff85f1", 34),
    "ladder 43 N24": ("f03d99e632cc300fc6a5360cf4fa8d316e7cc8460f0c68b09f01f6a62c64a044", 48),
    "ladder 43 N32": ("d63396f69ca0e483a72159bf0721cc287415fbbe14b6b72c49aa498409ae4ea8", 64),
    "ladder 43 N40": ("161c299a08f97c9bb11ac58e8bdef23d04fc354e6c2020ad094dc38e066ee084", 80),
}  # fmt: skip
V1_DEVELOPMENT_ORDER = ("25446cea694b075cb8ade71d03c5640a2534224a9f1ce02ffb48101689707983", 18)


def _manifest(criterion, layer, seed, reps, settings, cells, concurrency=1):
    return {
        "randomness": {"seeds": [seed]},
        "vm": {"concurrency": concurrency},
        "workload": {
            "kind": "suite-acceptance", "criterion": criterion, "layer": layer, "reps": reps,
            "settings": settings, "cells": cells, "session_trials": 60, "session_range": None,
        },
    }  # fmt: skip


def _v2_orders():
    out = {}
    for criterion, (layers, seeds, reps, settings, cells, _) in CRITERIA.items():
        want = ["screenshot", "screenshot+a11y"] if settings == "both" else [settings]
        for layer in layers:
            for seed in seeds:
                if reps == "rung":
                    for n in LADDER_RUNGS:
                        m = _manifest(criterion, layer, seed, ladder_reps(n), want, cells, n)
                        plan = driver.acceptance_plan(m, CELLS, VOLUME)
                        out[f"{criterion} {seed} N{n}"] = (
                            order.order_sha256(plan),
                            len(plan),
                        )
                    continue
                m = _manifest(criterion, layer, seed, reps[0], want, cells)
                plan = driver.acceptance_plan(m, CELLS, VOLUME)
                out[f"{criterion} {layer} {seed}"] = (order.order_sha256(plan), len(plan))
    return out


def test_every_order_but_c2s_is_v1s():
    v2 = _v2_orders()
    c2 = {key: value for key, value in v2.items() if key.startswith("C2 ")}
    assert {key: value for key, value in v2.items() if key not in c2} == V1_ORDERS
    assert list(c2) == [f"C2 L0-raw {order.C2_SEED}"]
    digest, sessions = c2[f"C2 L0-raw {order.C2_SEED}"]
    assert sessions == 9 and digest != V1_C2_ORDER


def test_v1s_c2_order_is_still_reproducible_at_seed_42():
    """v1's C2 order (job 768's session plan) is still what seed 42 builds."""
    ids = [c["id"] for c in CELLS["layers"]["L0-fixed"]]
    assert order.order_sha256(order.plan(ids, 42, 5, ["screenshot"])) == V1_C2_ORDER


def test_development_plans_are_v1s_and_l0_raw_gets_the_l0_fixed_cells():
    def dev(layer, cells="all"):
        return {
            "randomness": {"seeds": [42]},
            "workload": {
                "kind": "suite-development", "layer": layer, "cells": cells, "reps": 5,
                "settings": ["screenshot", "screenshot+a11y"], "session_trials": 60,
            },
        }  # fmt: skip

    plan = driver.session_plan(dev("L0-fixed"), CELLS)
    assert (order.order_sha256(plan), len(plan)) == V1_DEVELOPMENT_ORDER
    assert driver.session_plan(dev("L0-raw"), CELLS) == plan
    chords = ["chord_super_d", "chord_ctrl_c"]
    assert driver.session_plan(dev("L0-raw", chords), CELLS) == driver.session_plan(
        dev("L0-fixed", chords), CELLS
    )
    assert "L0-raw" in DEVELOPMENT_LAYERS
    assert not {"H-OSW-up", "H-GA-buggy"} & set(DEVELOPMENT_LAYERS)


def test_seed_45_is_reserved_and_c2s_only():
    assert order.C2_SEED == 45 and 45 in RESERVED_SEEDS
    assert {name for name, spec in CRITERIA.items() if 45 in spec[1]} == {"C2"}
    with pytest.raises(order.OrderError):
        order.check_seed(45, acceptance=True)
    order.check_seed(45, criterion="C2")


def test_v2_development_manifests_are_seed_42_development():
    """The four development runs of v2 (decision D40; main section 26) as submitted."""
    import yaml

    from harness.q2.vm.manifest import validate_manifest

    folder = ROOT / "experiments/manifests/q2-action-path-v2"
    manifests = sorted(folder.glob("dev-*.yaml"))
    assert len(manifests) == 4
    layers = []
    for path in manifests:
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate_manifest(manifest)
        assert manifest["purpose"] == "development"
        assert manifest["randomness"]["seeds"] == [42]
        assert manifest["experiment_id"] == "q2-action-path-v2"
        assert manifest["git_sha"].startswith("e66bf16")
        assert manifest["run_root"].startswith("/home/kevin/cotcodec-runs/q2-action-path-v2/dev")
        plan = driver.session_plan(manifest, CELLS)
        assert manifest["workload"]["sessions"] == len(plan)
        assert manifest["workload"]["trials"] == sum(len(s["trials"]) for s in plan)
        layers.append(manifest["workload"]["layer"])
    assert sorted(layers) == ["L0-fixed", "L0-fixed", "L0-fixed", "L0-raw"]
