"""D59 (iii): the provenance of the S1a analysis outputs. An operator script, not code of
record.

Usage (host, first and last step of the runbook)::

    python3 -E -s -B provenance.py --export X --plan PLAN [--input FILE ...] \
        [--ops-commit SHA] [--guard A/report/guard.json] --out A/provenance.json

Checks, each recorded with its values (exit 3 if any fails, after writing the file):

* the registration: ``lane.frozen_registration`` on the export (the ledger's hash chain, the
  row naming the registration, the file's SHA-256 equal to the row's), and that SHA-256 equal
  to the frozen ``f9db7cc3...``;
* the frozen plan: the file's SHA-256 (``a5f0aadc...``), its ``plan_sha256`` recomputed with
  ``plan.digest`` and equal to the frozen ``6a3f0219...``, and the export's own copy equal to
  the ``--plan`` given;
* the code of record: every file of the registration's section 20 tables, hashed in the
  export, against the table (this identifies the tree as the freeze commit's ``d5f5798``);
* the interpreter and library versions, the operator scripts' digests (and ``--ops-commit``);
* the SHA-256 of every ``--input`` (records, merged files, costs, receipts, outputs); an input
  that does not exist is listed under ``inputs_missing`` (it fails no check);
* with ``--guard``, the labels of the analysis outputs (incomplete, "not externally anchored").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s1a_ops as O  # noqa: E402

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*$")


def code_of_record(export: Path) -> dict[str, Any]:
    """Section 20's tables against the export's files."""
    text = (export / O.REGISTRATION).read_text(encoding="utf-8")
    start = text.index("## 20. Code of record")
    end = text.index("\n## 21.", start)
    table = {m.group(1): m.group(2) for m in map(ROW.match, text[start:end].splitlines()) if m}
    mismatched, missing = [], []
    for rel, digest in sorted(table.items()):
        path = export / rel
        if not path.is_file():
            missing.append(rel)
        elif O.sha256_file(path) != digest:
            mismatched.append(rel)
    return {
        "files": len(table),
        "missing": missing,
        "mismatched": mismatched,
        "pass": bool(table) and not missing and not mismatched,
    }


def registration(export: Path) -> dict[str, Any]:
    lane = O.frozen("lane")
    try:
        row = lane.frozen_registration(export)
    except Exception as exc:  # noqa: BLE001 - recorded as a failed check
        return {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "sha256": row.get("sha256"),
        "expected_sha256": O.REGISTRATION_SHA256,
        "ledger_row_hash": row.get("hash"),
        "experiment_id": row.get("experiment_id"),
        "pass": row.get("sha256") == O.REGISTRATION_SHA256,
    }


def frozen_plan(export: Path, plan_path: Path) -> dict[str, Any]:
    P = O.frozen("plan")
    plan = O.read_json(plan_path)
    recomputed = P.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
    own = export / O.PLAN_PATH
    file_sha = O.sha256_file(plan_path)
    out = {
        "file_sha256": file_sha,
        "expected_file_sha256": O.PLAN_FILE_SHA256,
        "plan_sha256": plan.get("plan_sha256"),
        "recomputed_plan_sha256": recomputed,
        "expected_plan_sha256": O.PLAN_SHA256,
        "export_copy_equal": own.is_file() and O.sha256_file(own) == file_sha,
    }
    out["pass"] = (
        file_sha == O.PLAN_FILE_SHA256
        and plan.get("plan_sha256") == recomputed == O.PLAN_SHA256
        and out["export_copy_equal"]
    )
    return out


def input_digests(inputs: Sequence[Path]) -> tuple[dict[str, Any], list[str]]:
    """SHA-256 and size of each input; an input that does not exist (for example a glob that
    matched nothing) is recorded as missing instead of failing the whole record."""
    digests: dict[str, Any] = {}
    missing: list[str] = []
    for path in inputs:
        if path.is_file():
            digests[str(path)] = {"sha256": O.sha256_file(path), "bytes": path.stat().st_size}
        else:
            digests[str(path)] = {"missing": True}
            missing.append(str(path))
    return digests, missing


def provenance(
    export: Path,
    plan_path: Path,
    inputs: Sequence[Path],
    ops_commit: str | None,
    guard: Path | None = None,
) -> dict[str, Any]:
    digests, missing = input_digests(inputs)
    out: dict[str, Any] = {
        "schema": O.SCHEMA + "-provenance",
        "freeze_commit": O.FREEZE_COMMIT,
        "export": str(export),
        "export_named_by_commit": export.name == O.FREEZE_COMMIT,
        "registration": registration(export),
        "frozen_plan": frozen_plan(export, plan_path),
        "code_of_record": code_of_record(export),
        "environment": O.versions(),
        "ops_commit": ops_commit,
        "ops_files": O.ops_files(),
        "inputs": digests,
        "inputs_missing": missing,
    }
    if guard is not None:
        out["labels"] = O.labels_from_guard(guard)
    out["pass"] = all(out[k]["pass"] for k in ("registration", "frozen_plan", "code_of_record"))
    return out


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--ops-commit", help="the commit the operator scripts were exported from")
    parser.add_argument("--guard", type=Path, help="run_report.py's guard.json (its labels)")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    export = O.use_export(args.export)
    if args.out.exists():
        raise O.OpsError(f"{args.out} exists; operator outputs are never overwritten")
    out = provenance(export, args.plan, args.input, args.ops_commit, args.guard)
    O.write_new(args.out, O.dumps(out))
    print(
        json.dumps(
            {
                **{k: out[k]["pass"] for k in ("registration", "frozen_plan", "code_of_record")},
                "inputs": len(out["inputs"]),
                "inputs_missing": out["inputs_missing"],
            }
        )
    )
    return 0 if out["pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
