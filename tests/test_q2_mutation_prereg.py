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


CHECK = ROOT / "infra" / "q2-mutation" / "run" / "check_frozen.py"
CONTROLS = ROOT / "infra" / "q2-mutation" / "run" / "submit_controls.sh"
SHA = "a" * 40


def _staged(tmp_path: Path, *, frozen: bool = True, tamper: bool = False) -> Path:
    """A staged tree with this preregistration, frozen in a scratch ledger."""
    src = tmp_path / "src"
    prereg = src / campaign.PREREG_PATH
    prereg.parent.mkdir(parents=True)
    prereg.write_text(_text(), encoding="utf-8")
    (src / ".git_sha").write_text(SHA + "\n", encoding="utf-8")
    if frozen:
        sys.path.insert(0, str(ROOT / "scripts"))
        import preregister

        ledger = src / campaign.LEDGER_PATH
        preregister.freeze(prereg, campaign.EXPERIMENT_ID, ledger=ledger, root=src)
        if tamper:
            row = ledger.read_text(encoding="utf-8").replace('"frozen_at": "', '"frozen_at": "x')
            ledger.write_text(row, encoding="utf-8")
    return src


def _check(src: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    import os

    environ = {k: v for k, v in os.environ.items() if k != "Q2M_PREREG_FROZEN"}
    environ.update(env or {})
    return subprocess.run(
        [sys.executable, str(CHECK), "--src", str(src), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environ,
    )


FROZEN = {"Q2M_PREREG_FROZEN": campaign.EXPERIMENT_ID}


@pytest.mark.parametrize(
    ("metric", "lo", "apply_to", "ok"),
    [
        (METRIC, LO_VM, "gold", True),
        (METRIC, LO_VM, None, True),
        (METRIC, LO_VM, "base", False),
        (METRIC, "sha256:" + "0" * 64, "gold", False),
    ],
)
def test_host_check_compares_images_with_the_pins(
    tmp_path: Path, metric: str, lo: str, apply_to: str | None, ok: bool
) -> None:
    src = _staged(tmp_path)
    extra = ["--apply-to", apply_to] if apply_to else []
    run = _check(
        src, "--sha", SHA, "--split", "confirm", "--metric", metric, "--lo", lo, *extra, env=FROZEN
    )
    assert (run.returncode == 0) is ok, run.stderr


def test_host_check_refuses_unfrozen_or_mismatched_trees(tmp_path: Path) -> None:
    base = ["--split", "confirm", "--metric", METRIC, "--lo", LO_VM]
    src = _staged(tmp_path / "a")
    assert _check(src, "--sha", "b" * 40, *base, env=FROZEN).returncode == 2
    no_env = _check(src, "--sha", SHA, *base)
    assert no_env.returncode == 2 and "dev split" in no_env.stderr
    unfrozen = _check(_staged(tmp_path / "b", frozen=False), "--sha", SHA, *base, env=FROZEN)
    assert unfrozen.returncode == 2 and "frozen" in unfrozen.stderr
    tampered = _check(_staged(tmp_path / "c", tamper=True), "--sha", SHA, *base, env=FROZEN)
    assert tampered.returncode == 2 and "row hash" in tampered.stderr
    edited = _staged(tmp_path / "d")
    with (edited / campaign.PREREG_PATH).open("a", encoding="utf-8") as handle:
        handle.write("\nedited after the freeze\n")
    assert _check(edited, "--sha", SHA, *base, env=FROZEN).returncode == 2
    dev = _check(src, "--sha", SHA, "--split", "dev", "--metric", "x", "--lo", "y")
    assert dev.returncode == 0, dev.stderr


@pytest.mark.parametrize("script", [SUBMIT, CONTROLS])
def test_submit_scripts_run_the_host_check_and_the_container_guard(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    assert "check_frozen.py" in text and '--sha "${sha}"' in text
    assert "campaign guard --split ${split}" in text
    # Jobs 1 and 3 (metric image) start with the guard and carry the frozen env.
    assert text.count('hex "${frozen_env[@]}" sh -c "${guard} &&') == 2
    assert 'Q2M_PREREG_FROZEN:-}" != "q2-evaluator-mutation-v1"' not in text


def test_build_default_matches_the_registered_application_mode() -> None:
    source = (ROOT / "harness" / "q2_mutation" / "campaign.py").read_text(encoding="utf-8")
    assert re.search(r'"--apply-to",\s*choices=\["base", "gold"\],\s*default="gold"', source)
    assert 'apply_to="${7:-gold}"' in SUBMIT.read_text(encoding="utf-8")


def test_prereg_rater_pins_match_the_runner() -> None:
    from harness.q2_mutation import rater_runner, raters

    declared = campaign.prereg_pins(_text())["raters"]
    open_weight = raters.RATERS[1]
    assert declared["anthropic_model"] == raters.RATERS[0]["registry_id"]
    assert declared["anthropic_model"] == rater_runner.ANTHROPIC["model"]
    assert declared["open_weight_model_id"] == open_weight["registry_id"]
    assert (
        declared["open_weight_repo"]
        == open_weight["repo_id"]
        == rater_runner.OPEN_WEIGHT["repo_id"]
    )
    assert declared["open_weight_revision"] == open_weight["revision"]
    assert declared["open_weight_revision"] == rater_runner.OPEN_WEIGHT["revision"]
    assert declared["open_weight_receipt_sha256"] == open_weight["receipt_sha256"]
    assert declared["open_weight_receipt_sha256"] == rater_runner.OPEN_WEIGHT["receipt_sha256"]
    # Decision D34: the open-weight rater thinks, within a registered reply budget,
    # and the isolated Claude rater starts from the committed prompt template.
    assert declared["open_weight_enable_thinking"] is rater_runner.OPEN_WEIGHT["enable_thinking"]
    assert declared["open_weight_max_tokens"] == rater_runner.OPEN_WEIGHT["max_tokens"]
    template = rater_runner.ISOLATED_PROMPT_TEMPLATE.read_bytes()
    assert (
        declared["isolated_prompt_template_sha256"]
        == rater_runner.ISOLATED_PROMPT_TEMPLATE_SHA256
        == rater_runner.sha256_bytes(template)
    )
    sys.path.insert(0, str(ROOT / "infra" / "q2-mutation" / "run"))
    import render_rater_manifest

    assert declared["open_weight_gpu_hours_cap"] == render_rater_manifest.AUDIT_GPU_HOURS
    builder = (ROOT / "scripts" / "build_vllm_overlay_on_h100.sh").read_text(encoding="utf-8")
    assert f'base_id="{declared["vllm_base_image_id"]}"' in builder


def test_prereg_pins_block_holds_only_checked_keys() -> None:
    """Every key of the pins block is checked by code or by these tests (review 3)."""
    import json

    declared = campaign.prereg_pins(_text())
    checked = {
        "q2m_pins",
        "experiment_id",
        *campaign.PINNED_KEYS,
        *campaign.INPUT_PIN_KEYS,
        "metric_image_id",
        "lo_vm_image_id",
        "apply_to",
        "mutation_split",
        "seeds",
        "specs_branch_commit",
        "raters",
    }
    assert set(declared) == checked
    provenance = json.loads(
        (ROOT / "program/evidence/q2-mutation/integration/blind-spec-provenance.json").read_text(
            encoding="utf-8"
        )
    )
    assert declared["specs_branch_commit"] == provenance["specs_head"]
