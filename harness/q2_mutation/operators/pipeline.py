"""Plan, apply and verify mutants for one task file.

1. ``make_context``: snapshot the LibreOffice-saved gold (the base) and the
   LibreOffice-saved initial file, take their structural diff as the task
   delta, and bind every spec requirement to units of the base.
2. ``plan_task``: run every operator of the family; each keeps at most three
   sites, seeded 42, 43, 44. Records follow ``schema.MutationResult`` with
   empty ``purity_checks``.
3. ``apply_manifest`` / ``apply_text_records``: office recipes go to
   ``uno_apply.py`` inside the LibreOffice container; text recipes are applied
   here.
4. ``verify``: snapshot base and mutant, run the purity checks, and validate
   the finished record strictly against the schema.

No step reads checker code, gold-vs-checker verdicts or task evaluator
configs; the base and initial files are inputs supplied by the harness.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from harness.q2_mutation.operators import CATALOG_VERSION, for_family
from harness.q2_mutation.operators._base import (
    OFFICE_FAMILIES,
    SEEDS,
    Context,
    plan_operator,
)
from harness.q2_mutation.operators._diff import diff
from harness.q2_mutation.operators._purity import Expectation, PurityCheck, admitted, check
from harness.q2_mutation.operators._snapshot import SnapshotError, family_of, snapshot
from harness.q2_mutation.operators._spec import bind_all, delta_units
from harness.q2_mutation.operators.apply_text import TextApplyError, apply_file
from harness.q2_mutation.schema import MutationResult, RequirementSpec


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_context(
    task_id: str,
    spec: RequirementSpec,
    base_path: str | Path,
    initial_path: str | Path | None = None,
    family: str | None = None,
    target_path_in_vm: str | None = None,
) -> Context:
    if spec.task_id != task_id:
        raise ValueError("spec is for a different task")
    family = family or family_of(base_path)
    base = snapshot(base_path, family)
    delta: dict[str, set[str]] = {}
    if initial_path is not None:
        delta = delta_units(diff(base, snapshot(initial_path, family)), family)
    source_text = None
    if family not in OFFICE_FAMILIES:
        source_text = Path(base_path).read_bytes().decode("utf-8")
    return Context(
        task_id=task_id,
        family=family,
        spec=spec,
        base=base,
        delta=delta,
        bindings=bind_all(spec, base, delta),
        input_sha256=sha256_file(base_path),
        target_path_in_vm=target_path_in_vm,
        source_text=source_text,
    )


def plan_task(
    ctx: Context, operators: Iterable[str] | None = None, seeds: tuple[int, ...] = SEEDS
) -> tuple[list[dict], list[dict]]:
    """Plan every operator of ``ctx.family`` (or the named subset)."""
    wanted = set(operators) if operators is not None else None
    records: list[dict] = []
    skipped: list[dict] = []
    for op_class in for_family(ctx.family):
        if wanted is not None and op_class.name not in wanted:
            continue
        planned, skips = plan_operator(op_class(), ctx, seeds, CATALOG_VERSION)
        records.extend(p.record for p in planned)
        skipped.extend(skips)
        if not planned and not skips:
            skipped.append({"operator": op_class.name, "unit": None, "reason": "no site"})
    return records, skipped


def apply_manifest(records: list[dict], input_rel: str, output_dir_rel: str) -> list[dict]:
    """Rows for ``uno_apply.py``: one per office mutant, paths relative to its root."""
    rows = []
    name = Path(input_rel).name
    for record in records:
        if record["family"] not in OFFICE_FAMILIES:
            continue
        rows.append(
            {
                "mutant_id": record["mutant_id"],
                "family": record["family"],
                "input": input_rel,
                "input_sha256": record["recipe"]["input_sha256"],
                "output": f"{output_dir_rel}/{record['mutant_id']}/{name}",
                "steps": record["recipe"]["params"]["steps"],
            }
        )
    return rows


def resave_row(mutant_id: str, family: str, input_rel: str, output_rel: str) -> dict:
    """A no-edit row: LibreOffice-save of ``input_rel`` (the base, or a fixed-point check)."""
    return {"mutant_id": mutant_id, "family": family, "input": input_rel, "output": output_rel,
            "steps": []}


def apply_text_records(records: list[dict], base_path: str | Path,
                       out_dir: str | Path) -> list[dict]:
    log = []
    for record in records:
        if record["family"] in OFFICE_FAMILIES:
            continue
        dst = Path(out_dir) / record["mutant_id"] / Path(base_path).name
        entry = {"mutant_id": record["mutant_id"], "applier": "q2-text-apply-v1"}
        try:
            entry["output_sha256"] = apply_file(
                base_path, dst, record["recipe"]["params"]["steps"],
                record["recipe"]["input_sha256"],
            )
            entry["status"] = "ok"
        except (TextApplyError, ValueError, KeyError) as exc:
            entry["status"] = "error"
            entry["error"] = f"{exc.__class__.__name__}: {exc}"
        log.append(entry)
    return log


def verify(
    record: dict,
    base_path: str | Path,
    mutant_path: str | Path | None,
    apply_log: dict | None,
) -> dict:
    """Fill ``purity_checks`` and ``output_sha256``; validate against the schema."""
    out = dict(record)
    checks: list[PurityCheck] = []
    status = (apply_log or {}).get("status", "missing")
    if status != "ok" or mutant_path is None or not Path(mutant_path).exists():
        detail = (apply_log or {}).get("error", "no apply record")
        checks.append(PurityCheck("applied", False, str(detail)[:500]))
    else:
        checks.append(PurityCheck("applied", True, (apply_log or {}).get("lo_build", "python")))
        family = record["family"]
        try:
            base = snapshot(base_path, family)
            actual = snapshot(mutant_path, family)
            expectation = Expectation.from_dict(record["recipe"]["params"]["expectation"])
            checks.extend(check(base, actual, expectation))
        except (SnapshotError, KeyError, ValueError) as exc:
            checks.append(PurityCheck("snapshot", False, f"{exc.__class__.__name__}: {exc}"))
        out["output_sha256"] = sha256_file(mutant_path)
    out["purity_checks"] = [c.as_dict() for c in checks]
    MutationResult.from_dict(out)
    return out


def is_admitted(record: dict) -> bool:
    return bool(record["purity_checks"]) and admitted(
        [PurityCheck(c["name"], c["passed"], c["detail"]) for c in record["purity_checks"]]
    )


def read_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
