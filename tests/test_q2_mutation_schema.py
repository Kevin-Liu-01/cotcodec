import hashlib
import json
from pathlib import Path

import pytest

from harness.q2_mutation import schema

TASK_ID = "4188d3a4-077d-46b7-9c86-23e1a036f6c1"
SHA = "a" * 64
EXPORT = Path(__file__).resolve().parents[1] / "program" / "evidence" / "q2-mutation"


def _task() -> dict:
    return {
        "task_id": TASK_ID,
        "domain": "libreoffice_calc",
        "instruction": "Freeze A1:B1.",
        "related_apps": ["libreoffice_calc"],
        "initial_files": [
            {"url": "https://example.org/a.xlsx", "path_in_vm": "/home/user/a.xlsx", "sha256": SHA}
        ],
        "snapshot": "libreoffice_calc",
    }


def _spec() -> dict:
    return {
        "task_id": TASK_ID,
        "author": schema.SPEC_AUTHOR,
        "requirements": [
            {
                "req_id": "R1",
                "statement": "Rows above 2 and columns left of C are frozen.",
                "check_kind": "other",
                "observable": "sheetView pane has xSplit=2, ySplit=1, state=frozen",
            }
        ],
        "allowed_variations": ["active cell"],
    }


def _mutation(label: str = "should_fail_violation", req_ids: list[str] | None = None) -> dict:
    recipe = {"seed": 42, "input_sha256": SHA, "params": {"cell": "B7"}}
    return {
        "mutant_id": schema.make_mutant_id(TASK_ID, "S-R1", recipe),
        "task_id": TASK_ID,
        "operator": "S-R1",
        "family": "spreadsheet",
        "label": label,
        "witness": {"req_ids": ["R1"] if req_ids is None else req_ids, "argument": "unfreezes"},
        "purity_checks": [{"name": "single-atom", "passed": True, "detail": ""}],
        "recipe": recipe,
    }


def _verdict(**overrides: object) -> dict:
    row = {
        "mutant_id": "m1",
        "task_id": TASK_ID,
        "checker_funcs": ["compare_table"],
        "score": 1.0,
        "verdict": "pass",
        "saved_via": "gui_faithful_lo_save",
        "lo_build": "7.3.7.2 / build-id",
        "venv_lock_sha256": SHA,
        "seconds": 1.5,
    }
    row.update(overrides)
    return row


def test_sanitized_task_round_trip() -> None:
    task = schema.SanitizedTask.from_dict(_task())
    assert task.to_dict() == _task()


@pytest.mark.parametrize("key", ["evaluator", "postconfig", "expected", "options", "hint"])
def test_sanitized_task_refuses_evaluator_keys_at_any_depth(key: str) -> None:
    top = _task() | {key: {}}
    with pytest.raises(schema.SchemaError, match="forbidden"):
        schema.SanitizedTask.from_dict(top)
    nested = _task()
    nested["initial_files"][0][key] = "x"
    with pytest.raises(schema.SchemaError, match="forbidden"):
        schema.SanitizedTask.from_dict(nested)


def test_sanitized_task_refuses_relative_vm_path_and_bad_hash() -> None:
    bad_path = _task()
    bad_path["initial_files"][0]["path_in_vm"] = "Downloads/a.xlsx"
    with pytest.raises(schema.SchemaError, match="absolute"):
        schema.SanitizedTask.from_dict(bad_path)
    bad_hash = _task()
    bad_hash["initial_files"][0]["sha256"] = "ABC"
    with pytest.raises(schema.SchemaError, match="hex"):
        schema.SanitizedTask.from_dict(bad_hash)


def test_spec_validation() -> None:
    spec = schema.RequirementSpec.from_dict(_spec())
    assert spec.req_ids() == {"R1"}
    wrong_author = _spec() | {"author": "someone-who-read-the-checker"}
    with pytest.raises(schema.SchemaError, match="author"):
        schema.RequirementSpec.from_dict(wrong_author)
    bad_kind = _spec()
    bad_kind["requirements"][0]["check_kind"] = "checker_rule"
    with pytest.raises(schema.SchemaError, match="check_kind"):
        schema.RequirementSpec.from_dict(bad_kind)
    dup = _spec()
    dup["requirements"].append(dict(dup["requirements"][0]))
    with pytest.raises(schema.SchemaError, match="duplicate"):
        schema.RequirementSpec.from_dict(dup)


def test_mutation_id_is_bound_to_recipe() -> None:
    result = schema.MutationResult.from_dict(_mutation())
    assert result.stratum == "document_model"
    result.check_against_spec(schema.RequirementSpec.from_dict(_spec()))
    tampered = _mutation()
    tampered["recipe"]["params"]["cell"] = "B8"
    with pytest.raises(schema.SchemaError, match="mutant_id"):
        schema.MutationResult.from_dict(tampered)


def test_violation_needs_a_req_id_and_known_ids() -> None:
    with pytest.raises(schema.SchemaError, match="req_id"):
        schema.MutationResult.from_dict(_mutation(req_ids=[]))
    equiv = schema.MutationResult.from_dict(_mutation("should_pass_equiv", req_ids=[]))
    assert equiv.label == "should_pass_equiv"
    unknown = schema.MutationResult.from_dict(_mutation(req_ids=["R9"]))
    with pytest.raises(schema.SchemaError, match="not in the spec"):
        unknown.check_against_spec(schema.RequirementSpec.from_dict(_spec()))


def test_recipe_requires_seed_and_input_hash() -> None:
    bad = _mutation()
    del bad["recipe"]["seed"]
    with pytest.raises(schema.SchemaError, match="seed"):
        schema.MutationResult.from_dict(bad)


def test_verdict_rules() -> None:
    assert schema.VerdictRow.from_dict(_verdict()).verdict == "pass"
    assert schema.verdict_for_score(0.9999) == "fail"
    assert schema.verdict_for_score(None) == "error"
    with pytest.raises(schema.SchemaError, match="contradicts"):
        schema.VerdictRow.from_dict(_verdict(score=0.5))
    with pytest.raises(schema.SchemaError, match="error"):
        schema.VerdictRow.from_dict(_verdict(score=None, verdict="error"))
    row = schema.VerdictRow.from_dict(_verdict(score=None, verdict="error", error="KeyError"))
    assert json.loads(row.to_jsonl())["error"] == "KeyError"
    with pytest.raises(schema.SchemaError, match="lo_build"):
        schema.VerdictRow.from_dict(_verdict(lo_build=None))
    no_save = schema.VerdictRow.from_dict(_verdict(saved_via="none", lo_build=None))
    assert no_save.lo_build is None
    with pytest.raises(schema.SchemaError, match="unknown"):
        schema.VerdictRow.from_dict(_verdict(gold_path="/x"))


def test_read_verdict_rows_reports_line() -> None:
    good = json.dumps(_verdict())
    with pytest.raises(schema.SchemaError, match="line 2"):
        schema.read_verdict_rows([good, "{not json"])


def test_committed_export_is_sanitized() -> None:
    files = sorted((EXPORT / "sanitized-tasks").glob("*.json"))
    assert len(files) == 205
    manifest = json.loads((EXPORT / "sanitized-tasks.manifest.json").read_text())
    for path in files:
        text = path.read_text(encoding="utf-8")
        task = schema.SanitizedTask.from_dict(json.loads(text))
        assert path.stem == task.task_id
        assert (
            manifest["sanitized_task_sha256"][task.task_id]
            == hashlib.sha256(text.encode("utf-8")).hexdigest()
        )
    splits = json.loads((EXPORT / "splits.json").read_text())
    ids = splits["dev"] + splits["confirm"] + splits["reserve"]
    assert len(ids) == len(set(ids)) == 205
    assert len(splits["confirm"]) == 120
