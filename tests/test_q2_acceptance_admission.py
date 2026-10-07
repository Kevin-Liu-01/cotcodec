"""Acceptance admission (preregistration sections 7-10, decision 26): ledger, seeds, ladder.

Acceptance and scored-control campaigns are admitted only when the ledger freezes the main
preregistration and the addenda they need; seeds 43 and 44 are refused for everything else.
These tests build a ledger with ``scripts/preregister.py`` in a temporary tree, so the
admitted path is exercised before the real freeze, and check that the repository's own
ledger still refuses every acceptance campaign.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import shutil
from pathlib import Path

import pytest

from harness.q2.action_path import order, volume
from harness.q2.vm import driver
from harness.q2.vm.manifest import (
    ADDENDA_IDS,
    LADDER_RUNGS,
    PREREG_ID,
    ManifestError,
    ladder_reps,
    ledger_paths,
    ledger_view,
    validate_manifest,
)
from scripts import preregister
from tests.test_vm_campaign import base_manifest

ROOT = Path(__file__).resolve().parents[1]
PREREGS = ROOT / "program/preregistrations"
FILES = {
    PREREG_ID: "program/preregistrations/q2-action-path-v1.md",
    ADDENDA_IDS["inputs"]: "program/preregistrations/q2-action-path-v1-inputs.md",
    ADDENDA_IDS["executor"]: "program/preregistrations/q2-action-path-v1-executor.md",
}
CELLS = json.loads((ROOT / "harness/q2/action_path/suite_cells.json").read_text())
VOLUME = json.loads((ROOT / "harness/q2/action_path/volume_plan.json").read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acceptance(criterion: str = "A1", seed: int = 43, concurrency: int = 1, **workload) -> dict:
    manifest = base_manifest()
    manifest["purpose"] = "acceptance"
    manifest["preregistration"] = {
        "path": FILES[PREREG_ID],
        "status": "frozen",
        "sha256": _sha(ROOT / FILES[PREREG_ID]),
    }
    manifest["addenda"] = {
        key: {"path": FILES[experiment], "sha256": _sha(ROOT / FILES[experiment])}
        for key, experiment in ADDENDA_IDS.items()
    }
    manifest["randomness"] = {
        "contract": "seeded",
        "seeds": [seed],
        "seed_binding": {"flag": "--seed"},
    }
    manifest["vm"]["concurrency"] = concurrency
    manifest["slurm"] = {
        "cpus": concurrency * 4 + 1,
        "memory_gb": concurrency * 7 + 2,
        "minutes": 1440,
    }
    manifest["workload"] = {
        "kind": "suite-acceptance",
        "criterion": criterion,
        "layer": "L0-fixed",
        "cells": "all",
        "reps": 5,
        "settings": ["screenshot", "screenshot+a11y"],
        "mutant": None,
        "session_range": None,
        "attempt": 1,
        "session_trials": 60,
        "boot_timeout_s": 300,
        "settle_timeout_s": 60,
        "cells_sha256": "4" * 64,
        "sessions": 18,
        "trials": 1000,
        "max_trial_s": 30,
    }
    manifest["workload"].update(workload)
    return manifest


@pytest.fixture()
def frozen_tree(tmp_path: Path) -> Path:
    """A copy of the three preregistration files frozen in a fresh ledger."""
    for relative in FILES.values():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    ledger = tmp_path / "program/preregistrations/ledger.jsonl"
    for experiment, relative in FILES.items():
        preregister.freeze(tmp_path / relative, experiment, ledger=ledger, root=tmp_path)
    return tmp_path


def _ledger(tree: Path, manifest: dict) -> dict:
    return ledger_view(str(tree), ledger_paths(manifest))


def test_the_repository_ledger_refuses_every_acceptance_campaign_before_the_freeze():
    """Until the owner's freeze, the real ledger has no row for any q2 file."""
    rows = [json.loads(line) for line in (PREREGS / "ledger.jsonl").read_text().splitlines()]
    assert not {row["experiment_id"] for row in rows} & set(FILES)
    for seed in (43, 44):
        manifest = acceptance(seed=seed)
        with pytest.raises(ManifestError, match="not frozen in the ledger"):
            validate_manifest(manifest, ledger_view(str(ROOT), ledger_paths(manifest)))


def test_a_frozen_ledger_admits_a1_at_seeds_43_and_44(frozen_tree):
    for seed in (43, 44):
        manifest = acceptance(seed=seed)
        validate_manifest(manifest, _ledger(frozen_tree, manifest))


def test_admission_needs_every_addendum_and_matching_digests(frozen_tree):
    manifest = acceptance()
    view = _ledger(frozen_tree, manifest)
    missing = copy.deepcopy(view)
    del missing["rows"][ADDENDA_IDS["executor"]]
    with pytest.raises(ManifestError, match="not frozen"):
        validate_manifest(manifest, missing)
    drifted = copy.deepcopy(view)
    drifted["files"][FILES[ADDENDA_IDS["inputs"]]] = "0" * 64
    with pytest.raises(ManifestError, match="changed after it was frozen"):
        validate_manifest(manifest, drifted)
    other = copy.deepcopy(manifest)
    other["addenda"]["executor"]["sha256"] = "9" * 64
    with pytest.raises(ManifestError, match="disagree"):
        validate_manifest(other, view)
    # C2 needs only the inputs addendum.
    c2 = acceptance("C2", seed=42, layer="L0-raw", settings=["screenshot"], sessions=9, trials=500)
    c2_view = copy.deepcopy(_ledger(frozen_tree, c2))
    del c2_view["rows"][ADDENDA_IDS["executor"]]
    validate_manifest(c2, c2_view)


def test_a_broken_ledger_chain_is_refused(frozen_tree):
    ledger = frozen_tree / "program/preregistrations/ledger.jsonl"
    rows = ledger.read_text().splitlines()
    tampered = json.loads(rows[1])
    tampered["sha256"] = "0" * 64
    rows[1] = json.dumps(tampered, sort_keys=True)
    ledger.write_text("\n".join(rows) + "\n")
    with pytest.raises(ManifestError, match="hash chain"):
        ledger_view(str(frozen_tree), [FILES[PREREG_ID]])


@pytest.mark.parametrize(
    "criterion, seed, changes, message",
    [
        ("A1", 42, {}, "layer or seed"),
        ("A1", 45, {}, "layer or seed"),
        ("A1", 43, {"reps": 4}, "repetitions"),
        ("A1", 43, {"layer": "H-GA"}, "layer or seed"),
        ("A1", 43, {"settings": ["screenshot"]}, "settings"),
        ("A2", 44, {"layer": "H-GA"}, "layer or seed"),
        ("C1", 43, {"layer": "H-OSW-up", "settings": ["screenshot"]}, "layer or seed"),
        ("C3", 42, {"settings": ["screenshot"], "reps": 1}, "mutant"),
        ("A4", 43, {"cells": "all", "reps": 1}, "cells"),
    ],
)
def test_shapes_outside_the_preregistration_are_refused(
    frozen_tree, criterion, seed, changes, message
):
    manifest = acceptance(criterion, seed=seed, **changes)
    with pytest.raises(ManifestError, match=message):
        validate_manifest(manifest, _ledger(frozen_tree, manifest))


def test_only_the_ladder_and_a4_run_concurrent_vms(frozen_tree):
    manifest = acceptance("A1", concurrency=8)
    with pytest.raises(ManifestError, match="concurrency"):
        validate_manifest(manifest, _ledger(frozen_tree, manifest))
    a4 = acceptance("A4", concurrency=40, reps=1, cells="volume", sessions=1068, trials=64028)
    validate_manifest(a4, _ledger(frozen_tree, a4))
    odd = acceptance("A4", concurrency=12, reps=1, cells="volume", sessions=1068, trials=64028)
    with pytest.raises(ManifestError, match="concurrency"):
        validate_manifest(odd, _ledger(frozen_tree, odd))


def test_ladder_rungs_load_every_vm_and_boot_at_least_twenty_times(frozen_tree):
    for rung in LADDER_RUNGS:
        reps = ladder_reps(rung)
        per_setting = math.ceil(reps * 100 / order.SESSION_TRIALS)
        assert reps >= 5 and per_setting >= rung and 2 * per_setting >= 20
        # The smallest such count: one repetition fewer would not do.
        fewer = math.ceil((reps - 1) * 100 / order.SESSION_TRIALS)
        assert reps == 5 or fewer < max(rung, 10)
        manifest = acceptance(
            "ladder", concurrency=rung, reps=reps, sessions=2 * per_setting, trials=200 * reps
        )
        validate_manifest(manifest, _ledger(frozen_tree, manifest))
        plan = driver.acceptance_plan(manifest, CELLS, VOLUME)
        assert len(plan) == 2 * per_setting and sum(len(s["trials"]) for s in plan) == 200 * reps
        # Its first five repetitions are A1's seed-43 shuffle.
        a1 = order.shuffle_order([c["id"] for c in CELLS["layers"]["L0-fixed"]], 43, 5, True)
        rung_order = [cell for s in plan if s["setting"] == "screenshot" for _, cell in s["trials"]]
        assert rung_order[:500] == a1
        wrong = acceptance("ladder", concurrency=rung, reps=5, sessions=18, trials=1000)
        if reps != 5:
            with pytest.raises(ManifestError, match="repetitions"):
                validate_manifest(wrong, _ledger(frozen_tree, wrong))
    with pytest.raises(ManifestError, match="concurrency"):
        bad = acceptance("ladder", concurrency=1)
        validate_manifest(bad, _ledger(frozen_tree, bad))


def test_acceptance_plans_match_the_preregistered_counts(frozen_tree):
    a1 = acceptance()
    plan = driver.acceptance_plan(a1, CELLS, VOLUME)
    assert len(plan) == 18 and sum(len(s["trials"]) for s in plan) == 1000
    a4 = acceptance("A4", concurrency=40, reps=1, cells="volume", sessions=1068, trials=64028)
    plan = driver.acceptance_plan(a4, CELLS, VOLUME)
    assert len(plan) == VOLUME["sessions"] == 1068
    assert sum(len(s["trials"]) for s in plan) == VOLUME["trials"] == 64028
    assert volume.order_sha256(VOLUME) == VOLUME["order_sha256"]
    part = copy.deepcopy(a4)
    part["workload"]["session_range"] = [100, 200]
    sliced = driver.acceptance_plan(part, CELLS, VOLUME)
    assert sliced == plan[100:200]
    a3 = acceptance("A3", reps=30, cells="stress", sessions=30, trials=1800)
    plan = driver.acceptance_plan(a3, CELLS, VOLUME)
    assert {cell for s in plan for _, cell in s["trials"]} == set(order.STRESS_ENTRIES)
    assert sum(len(s["trials"]) for s in plan) == 30 * 30 * 2


def test_development_may_run_concurrent_vms_only_for_the_suite():
    manifest = base_manifest()
    manifest["purpose"] = "development"
    manifest["randomness"] = {
        "contract": "seeded",
        "seeds": [42],
        "seed_binding": {"flag": "--seed"},
    }
    manifest["vm"]["concurrency"] = 8
    manifest["slurm"] = {"cpus": 33, "memory_gb": 58, "minutes": 1440}
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
    validate_manifest(manifest)
    canary = copy.deepcopy(manifest)
    canary["workload"] = {
        k: v for k, v in manifest["workload"].items() if k not in ("layer", "cells", "settings")
    }
    canary["workload"].update(
        kind="canary-development", apps=["writer"], entries="all", measure_targets=False
    )
    with pytest.raises(ManifestError, match="one VM at a time"):
        validate_manifest(canary)
    manifest["randomness"]["seeds"] = [43]
    with pytest.raises(ManifestError, match="reserved for acceptance"):
        validate_manifest(manifest)
