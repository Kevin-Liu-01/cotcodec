"""Session workloads of the VM lane: development at seed 42 only, acceptance refused."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from harness.q2.vm import driver
from harness.q2.vm.manifest import ManifestError, validate_manifest
from tests.test_vm_campaign import base_manifest

ROOT = Path(__file__).resolve().parents[1]
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())


def development(**workload) -> dict:
    manifest = base_manifest()
    manifest["purpose"] = "development"
    manifest["randomness"] = {
        "contract": "seeded",
        "seeds": [42],
        "seed_binding": {"flag": "--seed"},
    }
    manifest["slurm"]["minutes"] = 1440
    manifest["workload"] = {
        "kind": "suite-development",
        "layer": "L0-fixed",
        "cells": "all",
        "reps": 1,
        "settings": ["screenshot"],
        "session_trials": 60,
        "boot_timeout_s": 300,
        "settle_timeout_s": 60,
        "cells_sha256": "4" * 64,
        "sessions": 2,
        "trials": 100,
        "max_trial_s": 60,
    }
    manifest["workload"].update(workload)
    return manifest


def test_development_at_seed_42_is_admitted():
    validate_manifest(development())


@pytest.mark.parametrize("seeds", [[43], [44], [42, 43], [7]])
def test_other_seeds_are_refused(seeds):
    manifest = development()
    manifest["randomness"]["seeds"] = seeds
    with pytest.raises(ManifestError):
        validate_manifest(manifest)


@pytest.mark.parametrize("layer", ["L0-raw", "H-OSW-up", "H-GA-buggy", "H-OSW"])
def test_controls_never_run_in_development(layer):
    with pytest.raises(ManifestError):
        validate_manifest(development(layer=layer))


def test_acceptance_is_refused_even_with_a_frozen_preregistration():
    manifest = development()
    manifest["purpose"] = "acceptance"
    with pytest.raises(ManifestError, match="frozen"):
        validate_manifest(manifest)
    manifest["preregistration"]["status"] = "frozen"
    with pytest.raises(ManifestError, match="before the freeze"):
        validate_manifest(manifest)


def test_budget_and_shape_checks():
    with pytest.raises(ManifestError):
        validate_manifest(development(trials=5000))
    with pytest.raises(ManifestError):
        validate_manifest(development(settings=["a11y"]))
    with pytest.raises(ManifestError):
        validate_manifest(development(session_trials=61))
    canary = development()
    canary["workload"] = {
        k: v for k, v in canary["workload"].items() if k not in ("layer", "cells", "settings")
    }
    canary["workload"].update(
        kind="canary-development", apps=["writer"], entries="all", measure_targets=False
    )
    validate_manifest(canary)
    bad = copy.deepcopy(canary)
    bad["workload"]["apps"] = ["notepad"]
    with pytest.raises(ManifestError):
        validate_manifest(bad)


def test_inputs_validation_is_infrastructure_only():
    manifest = base_manifest()
    manifest["workload"] = {
        "kind": "inputs-validation",
        "reps": 2,
        "canary_readback": True,
        "plan_sha256": "5" * 64,
        "boot_timeout_s": 300,
        "settle_timeout_s": 60,
        "cells_sha256": "4" * 64,
        "sessions": 1,
        "trials": 80,
        "max_trial_s": 30,
    }
    manifest["slurm"]["minutes"] = 180
    validate_manifest(manifest)
    manifest["purpose"] = "development"
    with pytest.raises(ManifestError):
        validate_manifest(manifest)


def test_driver_session_plan_matches_declared_counts():
    manifest = development(
        cells=["click_left_center", "type_plain", "key_enter"],
        reps=2,
        settings=["screenshot", "screenshot+a11y"],
        session_trials=4,
    )
    plan = driver.session_plan(manifest, CELLS)
    assert [len(s["trials"]) for s in plan] == [3, 3, 3, 3]
    assert {s["setting"] for s in plan} == {"screenshot", "screenshot+a11y"}
    with pytest.raises(driver.DriverError):
        driver.session_plan(development(cells=["not_a_cell"]), CELLS)
