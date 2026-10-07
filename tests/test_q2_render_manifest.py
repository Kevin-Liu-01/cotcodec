"""The scored-campaign manifest renderer refuses before the freeze and renders admissible
manifests after it (here against a scratch ledger frozen with scripts/preregister.py)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from harness.q2.vm.manifest import validate_manifest
from scripts import preregister
from scripts import render_q2_action_path_manifest as render

ROOT = Path(__file__).resolve().parents[1]
SHA = "b" * 40


@pytest.fixture()
def export(tmp_path: Path) -> Path:
    """A minimal export: the harness tree and the three registrations frozen in a ledger."""
    shutil.copytree(
        ROOT / "harness", tmp_path / "harness", ignore=shutil.ignore_patterns("__pycache__")
    )
    ledger = tmp_path / "program/preregistrations/ledger.jsonl"
    for experiment, relative in render.PREREG_PATHS.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        preregister.freeze(target, experiment, ledger=ledger, root=tmp_path)
    return tmp_path


def _render(export: Path, tmp_path: Path, *argv: str) -> dict:
    out = tmp_path / "m.yaml"
    code = render.main([*argv, "--source-dir", str(export), "--git-sha", SHA,
                        "--campaign-id", "q2ap-accept-test", "--out", str(out)])  # fmt: skip
    assert code == 0
    return yaml.safe_load(out.read_text())


def test_refused_before_the_freeze(tmp_path):
    shutil.copytree(
        ROOT / "harness", tmp_path / "harness", ignore=shutil.ignore_patterns("__pycache__")
    )
    out = str(tmp_path / "m.yaml")
    code = render.main(
        [
            "A1",
            "--source-dir",
            str(tmp_path),
            "--git-sha",
            SHA,
            "--campaign-id",
            "q2ap-x",
            "--out",
            out,
        ]
    )
    assert code == 2 and not (tmp_path / "m.yaml").exists()


def test_renders_admissible_scored_campaigns(export, tmp_path):
    from harness.q2.vm.manifest import ledger_paths, ledger_view

    cases = [
        (("A1", "--seed", "43"), 18, 1000),
        (("A1", "--seed", "44"), 18, 1000),
        (("A2", "--layer", "H-GA"), 16, 930),
        (("A3", "--layer", "L0-fixed"), 30, 1800),
        (("ladder", "--concurrency", "8", "--runner-cpus", "4"), 20, 1200),
        (("A4", "--concurrency", "40", "--runner-cpus", "8"), 1068, 64028),
        (("A4", "--session-range", "0", "30"), 30, None),
        (("A6",), 5, 300),
        (("C1", "--seed", "42", "--layer", "H-OSW-up"), 2, 70),
        (("C2", "--seed", "42", "--layer", "L0-raw"), 9, 500),
        (
            ("C3", "--seed", "42", "--layer", "H-GA", "--mutant", "M24-grid-1000-instead-of-999"),
            2,
            93,
        ),
        (("C3", "--seed", "42", "--layer", "L0-fixed", "--mutant", "none"), 2, 100),
    ]
    for argv, sessions, trials in cases:
        manifest = _render(export, tmp_path, *argv)
        assert manifest["workload"]["sessions"] == sessions, argv
        if trials is not None:
            assert manifest["workload"]["trials"] == trials, argv
        assert manifest["slurm"]["minutes"] <= 1440
        validate_manifest(manifest, ledger_view(str(export), ledger_paths(manifest)))
    reset = _render(export, tmp_path, "A5")
    assert reset["purpose"] == "infrastructure-validation" and reset["workload"]["cycles"] == 21


def test_a4_on_one_vm_must_be_split(export, tmp_path):
    out = str(tmp_path / "m.yaml")
    code = render.main(
        [
            "A4",
            "--source-dir",
            str(export),
            "--git-sha",
            SHA,
            "--campaign-id",
            "q2ap-x",
            "--out",
            out,
        ]
    )
    assert code == 2
