"""Committed R04 run mirrors (``program/evidence/*/r04-nuisance*/*/plan.json``, the layout of
``r04_host.py``): every step that finished is in the mirror, nothing in a mirror is
git-ignored, and each mirror's ``analysis.json`` reproduces from the committed records.

This file is deliberately outside R04's code tree (``guard.CODE_TREE_ROOTS`` names
``tests/test_r04_nuisance.py`` only), so it checks evidence without moving the digest the
registration pins. It was added after the re-audit found dev-smoke-v5's build-arm score
directory missing from the commit (``.gitignore``'s ``build/``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from harness.r04_nuisance import analysis, levels

ROOT = Path(__file__).resolve().parents[1]
MIRRORS = sorted(
    p.parent
    # r04-nuisance/ holds the pre-freeze smokes; r04-nuisance-confirm/ the registered run
    for p in ROOT.glob("program/evidence/*/r04-nuisance*/*/plan.json")
    if "run_root" in json.loads(p.read_text(encoding="utf-8"))
)
V5 = ROOT / "program/evidence/2026-10-11/r04-nuisance/dev-smoke-v5"


def _plan(mirror: Path) -> dict[str, Any]:
    return json.loads((mirror / "plan.json").read_text(encoding="utf-8"))


def _local(mirror: Path, plan: dict[str, Any], run_dir: str) -> Path:
    return mirror / Path(run_dir).relative_to(plan["run_root"])


def _expected_files(mirror: Path) -> list[Path]:
    """What the mirror must hold for every step that finished (documents excepted)."""
    plan = _plan(mirror)
    want: list[Path] = []
    outs_with_saves = set()
    for step in plan["steps"]:
        if step["state"] != "done":
            continue
        where = _local(mirror, plan, step["run_dir"])
        want.append(where / f"receipt-{step['job']}.json")
        if step["kind"] == "items":
            want += [where / "items.jsonl", where / "items.report.json"]
        elif step["kind"] == "save":
            outs_with_saves.add(step["out"])
        elif step["kind"] == "score":
            unscored = step.get("not_scored") or {}
            want += [where / f"scores-{c}.jsonl" for c in step["cells"] if c not in unscored]
    want += [mirror / out / "saves-summary.json" for out in sorted(outs_with_saves)]
    if plan.get("rounds"):
        want += [mirror / "rounds" / "pending.json", mirror / "rounds" / "only.txt"]
    return want


def test_the_smoke_at_the_code_of_record_is_mirrored():
    assert V5 in MIRRORS


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda p: p.name)
def test_every_finished_step_is_in_the_mirror(mirror):
    plan = _plan(mirror)
    missing = [str(p.relative_to(mirror)) for p in _expected_files(mirror) if not p.is_file()]
    assert not missing, missing
    for step in plan["steps"]:
        if step["state"] == "done":
            where = _local(mirror, plan, step["run_dir"])
            receipt = json.loads((where / f"receipt-{step['job']}.json").read_text())
            assert str(receipt["job_id"]) == str(step["job"]), step["name"]
            assert receipt["exit_status"] == 0 and receipt["gpus_requested"] == 0, step["name"]


@pytest.mark.parametrize("mirror", MIRRORS, ids=lambda p: p.name)
def test_nothing_in_the_mirror_is_git_ignored(mirror):
    """A file present here but ignored is a file the commit silently leaves out."""
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    rel = mirror.relative_to(ROOT).as_posix()
    ignored = subprocess.run(
        ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert not ignored, ignored
    expected = [p.relative_to(ROOT).as_posix() for p in _expected_files(mirror)]
    hit = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=ROOT,
        input="\n".join(expected),
        capture_output=True,
        text=True,
    ).stdout.split()
    assert not hit, hit


def _without_input_paths(result: dict[str, Any]) -> dict[str, Any]:
    """The analysis records where it read its inputs; a reproduction may read them from
    another place (the host's run directory against the evidence copy)."""

    def strip(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in ("path", "dir")}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value

    return {**result, "inputs": strip(result["inputs"])}


def _reproducible(mirror: Path) -> bool:
    path = mirror / "analysis.json"
    if not path.is_file():
        return False
    inputs = json.loads(path.read_text(encoding="utf-8"))["inputs"]
    return inputs.get("mode") == "run" and "k2_report" not in inputs


@pytest.mark.parametrize("mirror", [m for m in MIRRORS if _reproducible(m)], ids=lambda p: p.name)
def test_analysis_reproduces_from_the_committed_mirror(mirror, tmp_path):
    """The evidence README's command: ``analysis --run MIRROR --src . --out OUT.json``."""
    out = tmp_path / "analysis.json"
    analysis.main(["--run", str(mirror), "--src", str(ROOT), "--out", str(out)])
    new = json.loads(out.read_text(encoding="utf-8"))
    old = json.loads((mirror / "analysis.json").read_text(encoding="utf-8"))
    assert _without_input_paths(new) == _without_input_paths(old)


def test_dev_smoke_v5_main_run_and_pending_list_reproduce_in_the_explicit_form(tmp_path):
    """Once ``confirm`` has written the rounds into plan.json, ``--run`` reads both rounds,
    so the main-run analysis and its pending list reproduce only in the explicit form."""
    plan = _plan(V5)
    main_dirs = [
        _local(V5, plan, s["run_dir"])
        for s in plan["steps"]
        if s["kind"] == "score" and s["out"] == "main" and s["state"] == "done"
    ]
    out, pending = tmp_path / "analysis-main.json", tmp_path / "pending.json"
    analysis.main(
        ["--items", str(V5 / "items/items.jsonl"), "--scores", *map(str, main_dirs),
         "--splits", "dev", "--reference", str(ROOT / levels.CONTROL_SUMMARIES["dev"][0]),
         "--out", str(out), "--pending-out", str(pending)]
    )  # fmt: skip
    assert pending.read_bytes() == (V5 / "pending.json").read_bytes()
    assert json.loads(pending.read_text()) == plan["rounds"]["pending"]
    new = json.loads(out.read_text(encoding="utf-8"))
    old = json.loads((V5 / "analysis-main.json").read_text(encoding="utf-8"))
    assert old["inputs"]["mode"] == "run" and new["inputs"]["mode"] == "explicit"
    for result in (new, old):
        for key in ("mode", "run", "jobs"):
            result["inputs"].pop(key, None)
    assert _without_input_paths(new) == _without_input_paths(old)
    assert not new["complete"] and new["validity"]["gate"] == "pass"
