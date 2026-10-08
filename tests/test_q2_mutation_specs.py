"""Blind requirement specs: coverage, schema, and no trace of checker access."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from harness.q2_mutation.schema import FORBIDDEN_TASK_KEYS, RequirementSpec

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "program" / "evidence" / "q2-mutation"
SPECS = sorted((EVIDENCE / "specs").glob("*.yaml"))


def test_every_sanitized_task_has_one_valid_blind_spec() -> None:
    tasks = {p.stem for p in (EVIDENCE / "sanitized-tasks").glob("*.json")}
    seen = set()
    for path in SPECS:
        spec = RequirementSpec.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
        assert spec.task_id == path.stem
        assert spec.author == "blind-model-author-v1"
        seen.add(spec.task_id)
    assert seen == tasks and len(tasks) == 205


def test_specs_name_no_checker_function_or_evaluator_field() -> None:
    """A spec that names an OSWorld metric function or evaluator field saw the checker."""
    scope = json.loads((EVIDENCE / "harness" / "task-scope.json").read_text(encoding="utf-8"))
    funcs = sorted({func for task in scope["tasks"] for func in task["funcs"]})
    assert len(funcs) > 100
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, funcs)) + r")\b")
    fields = re.compile(
        r"\b(postconfig|evaluator|cloud_file|vm_file|compare_\w+|check_(?!kind\b)\w+)\b"
    )
    for path in SPECS:
        text = path.read_text(encoding="utf-8")
        assert not pattern.search(text), (path.name, pattern.search(text))
        assert not fields.search(text), (path.name, fields.search(text))
        keys = _keys(yaml.safe_load(text))
        assert not keys & set(FORBIDDEN_TASK_KEYS), (path.name, keys & set(FORBIDDEN_TASK_KEYS))


def test_blind_author_readme_declares_no_checker_access() -> None:
    readme = (EVIDENCE / "specs" / "README.md").read_text(encoding="utf-8")
    flat = " ".join(readme.split())
    for phrase in (
        "any checker or evaluator code, anything under `desktop_env/evaluators`",
        "any harness or operator code other than `schema.py`",
        "The harness branch was not merged",
        "any research plan, review or probe result",
    ):
        assert phrase in flat, phrase
    # The repository files the author lists as read are the schema, the
    # sanitized tasks, two tooling greps and its own specs; nothing on the
    # harness side (task-scope, receipts, probe output) is among them.
    read_section = flat.split("### Exactly what was read", 1)[1].split("Initial documents:", 1)[0]
    assert "harness/q2_mutation/schema.py" in read_section
    for forbidden in ("task-scope", "probe_touched", "offline_eval", "evaluation_examples"):
        assert forbidden not in read_section


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for item in value.values() for k in _keys(item)}
    if isinstance(value, list):
        return {k for item in value for k in _keys(item)}
    return set()
