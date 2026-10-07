"""Committed end-to-end evidence of the mutation campaign on the development split.

Each ``program/evidence/q2-mutation/integration/dev-mutants-v*`` directory is
the ``campaign export`` of one host run (spec -> operator -> mutant -> GUI-
faithful save -> checker verdict -> verdict row). These tests check that the
committed files are what the export wrote, touch only development-split tasks,
carry no document text, and agree with each other.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from harness.q2_mutation import campaign
from harness.q2_mutation.schema import read_verdict_rows

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "program" / "evidence" / "q2-mutation" / "integration"
RUNS = sorted(p for p in INTEGRATION.glob("dev-mutants-v*") if p.is_dir())
DEV = set(json.loads((ROOT / campaign.SPLITS_PATH).read_text(encoding="utf-8"))["dev"])


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_there_is_committed_end_to_end_evidence() -> None:
    assert RUNS, "no dev-split campaign export is committed"


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_export_is_intact_dev_only_and_consistent(run: Path) -> None:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "dev" and manifest["confirmatory"] is False
    assert manifest["experiment_id"] == campaign.EXPERIMENT_ID
    for name, digest in manifest["exported_sha256"].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == digest, name
    assert all(p.is_file() for p in run.iterdir()), "an export holds no mutant files"

    released = _jsonl(run / "mutations.release.jsonl")
    outcomes = _jsonl(run / "outcomes.jsonl")
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    assert {r["task_id"] for r in released} <= DEV
    assert [r["mutant_id"] for r in released] == [o["mutant_id"] for o in outcomes]
    for row in released:
        assert row["mutant_id"] == (
            f"{row['task_id']}__{row['operator']}__{row['recipe_sha256'][:12]}"
        )
        assert not campaign.free_text_leaves(row["recipe_release"]), row["mutant_id"]
        assert all(set(check) == {"name", "passed"} for check in row["purity_checks"])

    for arm in ("lock", "scout"):
        path = run / f"verdicts-{arm}.jsonl"
        if not path.is_file():
            continue
        rows = read_verdict_rows(path.read_text(encoding="utf-8").splitlines())
        assert {r.task_id for r in rows} <= DEV
        assert all(r.extras.get("dep_set") == arm for r in rows)
        scored = {r.mutant_id: r for r in rows}
        for outcome in outcomes:
            verdict = scored.get(outcome["mutant_id"])
            assert outcome[f"{arm}_verdict"] == (verdict.verdict if verdict else None)
            if outcome[f"{arm}_status"] == "evaluable":
                assert verdict is not None and verdict.saved_via in {
                    "gui_faithful_lo_save",
                    "none",
                }
        assert dict(Counter(o[f"{arm}_status"] for o in outcomes)) == report["status"][arm]
    assert report["planned"] == len(released)
    assert report["admitted"] == sum(1 for o in outcomes if o["admitted"])


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_no_evaluable_office_mutant_was_scored_unsaved(run: Path) -> None:
    """Every evaluable office mutant's verdict row says the GUI-faithful save ran."""
    released = {r["mutant_id"]: r for r in _jsonl(run / "mutations.release.jsonl")}
    path = run / "verdicts-lock.jsonl"
    rows = {r.mutant_id: r for r in read_verdict_rows(path.read_text().splitlines())}
    for outcome in _jsonl(run / "outcomes.jsonl"):
        if outcome["lock_status"] != "evaluable":
            continue
        if released[outcome["mutant_id"]]["family"] in {"xlsx", "docx", "pptx"}:
            assert rows[outcome["mutant_id"]].saved_via == "gui_faithful_lo_save"


def test_reviewed_run_names_what_each_recipe_was_applied_to() -> None:
    """From dev-mutants-v4 on, release rows carry the applier input (section 16)."""
    run = INTEGRATION / "dev-mutants-v4"
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    rows = _jsonl(run / "mutations.release.jsonl")
    assert {r["applied_to"] for r in rows} == {manifest["apply_to"]} == {"gold"}
    targets = {t["target_id"]: t for t in _jsonl(run / "targets-built.jsonl")}
    for row in rows:
        assert len(row["applied_input_sha256"]) == 64
        if row["family"] != "text":
            # Office recipes were planned on the base but applied to the gold.
            assert row["applied_input_sha256"] != row["recipe_release"]["input_sha256"]
    assert all(t["status"] == "planned" for t in targets.values())


SMOKES = sorted(p for p in INTEGRATION.glob("rater-smoke-dev-v*") if p.is_dir())


@pytest.mark.parametrize("smoke", SMOKES, ids=lambda p: p.name)
def test_rater_smoke_evidence_is_intact_dev_only_and_blind(smoke: Path) -> None:
    """Every file is in SHA256SUMS; the sample is dev-only; no reply text or packet bytes."""
    sums = {}
    for line in (smoke / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        sums[name.removeprefix("./")] = digest
    files = {
        str(p.relative_to(smoke))
        for p in smoke.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS"
    }
    assert set(sums) == files
    for name, digest in sums.items():
        assert hashlib.sha256((smoke / name).read_bytes()).hexdigest() == digest, name
    sample = _jsonl(smoke / "audit" / "sample.jsonl")
    assert sample and {row["task_id"] for row in sample} <= DEV
    calls = _jsonl(smoke / "open-weight" / "calls.jsonl")
    items = {row["item_id"] for row in sample}
    assert calls and {c["item_id"] for c in calls} <= items
    for call in calls:
        assert "text" not in call and "content" not in json.dumps(call)
    for path in smoke.rglob("*.json*"):
        assert "data_b64" not in path.read_text(encoding="utf-8"), path


def test_harness_export_manifest_holds_digests_only() -> None:
    manifest = json.loads(
        (
            INTEGRATION / "rater-smoke-dev-v2" / "harness-export" / "dev-export-manifest.json"
        ).read_text(encoding="utf-8")
    )
    sample = _jsonl(INTEGRATION / "rater-smoke-dev-v2" / "audit" / "sample.jsonl")
    assert sorted(manifest["order"]) == sorted(row["item_id"] for row in sample)
    text = json.dumps(manifest)
    for word in ("should_", "verdict", "label", "operator", "mutant"):
        assert word not in text
