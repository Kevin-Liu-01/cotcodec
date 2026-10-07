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
