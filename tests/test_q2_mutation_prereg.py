"""The q2-evaluator-mutation-v1 preregistration names the exact code it will run."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from harness.q2_mutation import campaign

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / campaign.PREREG_PATH
SUBMIT = ROOT / "infra" / "q2-mutation" / "run" / "submit_mutants.sh"
METRIC = "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230"
LO_VM = "sha256:f5b4c40eefd2b92f846652910ba34db35e1ae7bf90fa474595cc745cc5895361"


def _text() -> str:
    return PREREG.read_text(encoding="utf-8")


def test_prereg_has_no_open_values_and_passes_the_freeze_text_check() -> None:
    text = _text()
    assert "FILL-AT-FREEZE" not in text
    assert "@@" not in text
    # The same check scripts/preregister.py freeze applies.
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text)


def test_prereg_pins_match_the_tree() -> None:
    declared = campaign.prereg_pins(_text())
    actual = campaign.pins(ROOT)
    assert {key: declared[key] for key in campaign.PINNED_KEYS} == {
        key: actual[key] for key in campaign.PINNED_KEYS
    }, "code, catalog, specs or splits changed: refresh the pins block (campaign pins)"
    assert declared["metric_image_id"] == METRIC
    assert declared["lo_vm_image_id"] == LO_VM
    assert declared["experiment_id"] == campaign.EXPERIMENT_ID
    assert declared["apply_to"] == "gold"
    assert declared["seeds"] == [42, 43, 44]
    assert declared["mutation_split"] == "confirm"


def _submit_image_check() -> str:
    script = SUBMIT.read_text(encoding="utf-8")
    return script.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


@pytest.mark.parametrize(
    ("metric", "lo", "apply_to", "ok"),
    [
        (METRIC, LO_VM, "gold", True),
        (METRIC, LO_VM, "base", False),
        (METRIC, "sha256:" + "0" * 64, "gold", False),
    ],
)
def test_submit_script_checks_images_against_the_pins(
    metric: str, lo: str, apply_to: str, ok: bool
) -> None:
    run = subprocess.run(
        [sys.executable, "-", str(PREREG), metric, lo, apply_to],
        input=_submit_image_check(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert (run.returncode == 0) is ok, run.stderr


def test_build_default_matches_the_registered_application_mode() -> None:
    source = (ROOT / "harness" / "q2_mutation" / "campaign.py").read_text(encoding="utf-8")
    assert re.search(r'"--apply-to",\s*choices=\["base", "gold"\],\s*default="gold"', source)
    assert 'apply_to="${7:-gold}"' in SUBMIT.read_text(encoding="utf-8")
