"""Validate the blind requirement specs against the binding Q2 schema.

Usage: python program/evidence/q2-mutation/specs/check_specs.py
Exit code 0 iff every sanitized task has exactly one schema-valid spec.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from harness.q2_mutation.schema import RequirementSpec  # noqa: E402

EVIDENCE = ROOT / "program" / "evidence" / "q2-mutation"


def main() -> int:
    tasks = {
        p.stem: json.loads(p.read_text())["domain"] for p in EVIDENCE.glob("sanitized-tasks/*.json")
    }
    seen: set[str] = set()
    errors = 0
    for path in sorted((EVIDENCE / "specs").glob("*.yaml")):
        try:
            spec = RequirementSpec.from_dict(yaml.safe_load(path.read_text()))
        except Exception as exc:  # report every malformed spec, then fail
            print(f"INVALID {path.name}: {exc}")
            errors += 1
            continue
        if spec.task_id != path.stem or spec.task_id not in tasks:
            print(f"MISMATCH {path.name}: task_id {spec.task_id}")
            errors += 1
            continue
        seen.add(spec.task_id)
    missing = sorted(set(tasks) - seen)
    for task_id in missing:
        print(f"MISSING {task_id} ({tasks[task_id]})")
    print(f"specs_valid={len(seen)} invalid={errors} missing={len(missing)} tasks={len(tasks)}")
    return 1 if errors or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
