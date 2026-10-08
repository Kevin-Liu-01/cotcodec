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
    executor_addendum,
    frozen_table,
    ladder_reps,
    ledger_paths,
    ledger_view,
    runner_cpus,
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
    manifest["runner"]["cpus"] = runner_cpus(concurrency)
    manifest["slurm"] = {
        "cpus": concurrency * 4 + runner_cpus(concurrency),
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


def export_tree(target: Path, freeze: tuple[str, ...] = tuple(FILES)) -> Path:
    """An export: the harness tree, every file the registrations pin, and a fresh ledger
    freezing the registrations named in ``freeze``."""
    shutil.copytree(
        ROOT / "harness", target / "harness", ignore=shutil.ignore_patterns("__pycache__")
    )
    for relative in FILES.values():
        pinned = frozen_table((ROOT / relative).read_text(encoding="utf-8"))
        for listed in [relative, *pinned]:
            destination = target / listed
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / listed, destination)
    ledger = target / "program/preregistrations/ledger.jsonl"
    for experiment in freeze:
        relative = FILES[experiment]
        preregister.freeze(target / relative, experiment, ledger=ledger, root=target)
    return target


@pytest.fixture()
def frozen_tree(tmp_path: Path) -> Path:
    """An export with the three preregistration files frozen in a fresh ledger."""
    return export_tree(tmp_path)


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


def a7_manifest(**changes) -> dict:
    """Criterion A7 (decision D30): G, 360 seed-43 shuffles, screenshot-plus-accessibility."""
    from harness.q2.vm.manifest import OBSERVATION_REPS

    workload = {
        "reps": OBSERVATION_REPS,
        "settings": ["screenshot+a11y"],
        "cells": "gating",
        "sessions": 516,
        "trials": 30960,
    }
    workload.update(changes)
    return acceptance("A7", concurrency=workload.pop("concurrency", 40), **workload)


def test_the_observation_service_campaign_is_admitted_as_registered(frozen_tree):
    from harness.q2.action_path import acceptance as analysis

    manifest = a7_manifest()
    validate_manifest(manifest, _ledger(frozen_tree, manifest))
    plan = driver.acceptance_plan(manifest, CELLS, VOLUME)
    assert plan == analysis.observation_plan()
    calls = sum(
        len([a for a in cell["actions"] if a["op"] != "terminate"])
        for session in plan
        for _, cell_id in session["trials"]
        for cell in CELLS["layers"]["L0-fixed"]
        if cell["id"] == cell_id
    )
    # Section 9: 38,520 step calls and 516 reset observations, 39,036 accessibility calls.
    assert calls == 38520 and calls + len(plan) == 39036
    one = a7_manifest(concurrency=1, session_range=[0, 20], sessions=20, trials=1200)
    validate_manifest(one, _ledger(frozen_tree, one))
    for changes, message in (
        ({"settings": ["screenshot", "screenshot+a11y"]}, "settings"),
        ({"cells": "all"}, "cells"),
        ({"reps": 5}, "repetitions"),
        ({"concurrency": 12}, "concurrency"),
        ({"attempt": 2}, "A7 has no repair attempts"),
    ):
        bad = a7_manifest(**changes)
        with pytest.raises(ManifestError, match=message):
            validate_manifest(bad, _ledger(frozen_tree, bad))


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


# --- fix pass after the 2026-10-07 review of 2b492cd ---------------------------------------------


def test_admission_checks_every_frozen_file_not_only_the_registrations(frozen_tree):
    """Design decision 35: an edited executor file is refused although no .md changed."""
    manifest = acceptance()
    validate_manifest(manifest, _ledger(frozen_tree, manifest))
    executor = frozen_tree / "harness/q2/vm/guest/l0_fixed.py"
    executor.write_text(executor.read_text() + "\n# edited after the freeze\n")
    with pytest.raises(ManifestError, match="l0_fixed.py in the source tree is not the file"):
        validate_manifest(manifest, _ledger(frozen_tree, manifest))


def test_admission_refuses_files_no_frozen_table_pins(frozen_tree):
    extra = frozen_tree / "harness/q2/action_path/helper.py"
    extra.write_text("PATCH = True\n")
    manifest = acceptance()
    with pytest.raises(ManifestError, match="files no frozen table pins"):
        validate_manifest(manifest, _ledger(frozen_tree, manifest))
    # C2 needs only the main registration and the inputs addendum; their tables still hold.
    c2 = acceptance("C2", seed=42, layer="L0-raw", settings=["screenshot"], sessions=9, trials=500)
    validate_manifest(c2, _ledger(frozen_tree, c2))


def test_c2_is_admitted_before_the_executor_freeze_with_the_inputs_addendum_only(tmp_path):
    tree = export_tree(tmp_path, freeze=(PREREG_ID, ADDENDA_IDS["inputs"]))
    c2 = acceptance("C2", seed=42, layer="L0-raw", settings=["screenshot"], sessions=9, trials=500)
    del c2["addenda"]["executor"]
    validate_manifest(c2, _ledger(tree, c2))
    a1 = acceptance()
    del a1["addenda"]["executor"]
    with pytest.raises(ManifestError, match="needs the executor addendum"):
        validate_manifest(a1, _ledger(tree, a1))


def test_a_repair_attempt_runs_under_its_own_executor_addendum(tmp_path):
    tree = export_tree(tmp_path)
    experiment, path = executor_addendum(2)
    assert experiment == "q2-action-path-v1-executor-a2"
    repair = acceptance(attempt=2)
    with pytest.raises(ManifestError, match="runs under"):
        validate_manifest(repair, _ledger(tree, repair))
    shutil.copyfile(tree / FILES[ADDENDA_IDS["executor"]], tree / path)
    ledger = tree / "program/preregistrations/ledger.jsonl"
    with pytest.raises(ManifestError, match="not frozen"):
        repair["addenda"]["executor"] = {"path": path, "sha256": _sha(tree / path)}
        validate_manifest(repair, _ledger(tree, repair))
    (tree / path).write_text((tree / path).read_text() + "\nRepair attempt 2.\n")
    preregister.freeze(tree / path, experiment, ledger=ledger, root=tree)
    repair["addenda"]["executor"] = {"path": path, "sha256": _sha(tree / path)}
    validate_manifest(repair, _ledger(tree, repair))
    # Validity controls are never repaired within v1 (section 11).
    c3 = acceptance("C3", seed=42, settings=["screenshot"], reps=1, mutant="none", attempt=2)
    with pytest.raises(ManifestError, match="no repair attempts"):
        validate_manifest(c3, _ledger(tree, c3))


def test_runner_cpus_are_registered_per_concurrency(frozen_tree):
    assert [runner_cpus(n) for n in (1, 8, 16, 24, 32, 40)] == [1, 4, 8, 12, 16, 20]
    reps = ladder_reps(8)
    rung = acceptance("ladder", concurrency=8, reps=reps, sessions=20, trials=200 * reps)
    validate_manifest(rung, _ledger(frozen_tree, rung))
    starved = copy.deepcopy(rung)
    starved["runner"]["cpus"] = 1
    with pytest.raises(ManifestError, match="runner.cpus must be 4"):
        validate_manifest(starved, _ledger(frozen_tree, starved))


def test_the_guest_server_fault_hook_is_development_only(frozen_tree):
    manifest = base_manifest()
    manifest["purpose"] = "development"
    manifest["randomness"] = {
        "contract": "seeded",
        "seeds": [42],
        "seed_binding": {"flag": "--seed"},
    }
    manifest["workload"] = {
        "kind": "suite-development",
        "layer": "L0-fixed",
        "cells": ["key_enter", "type_plain"],
        "reps": 1,
        "settings": ["screenshot"],
        "session_trials": 60,
        "boot_timeout_s": 300,
        "settle_timeout_s": 60,
        "cells_sha256": "4" * 64,
        "sessions": 1,
        "trials": 2,
        "max_trial_s": 60,
        "kill_guest_server_after_seq": 0,
    }
    validate_manifest(manifest)
    manifest["workload"]["kill_guest_server_during_seq"] = 1
    validate_manifest(manifest)
    for hook in ("kill_guest_server_after_seq", "kill_guest_server_during_seq"):
        bad = copy.deepcopy(manifest)
        bad["workload"][hook] = "0"
        with pytest.raises(ManifestError, match=hook):
            validate_manifest(bad)
        a1 = acceptance(**{hook: 0})
        with pytest.raises(ManifestError, match="unknown"):
            validate_manifest(a1, _ledger(frozen_tree, a1))
