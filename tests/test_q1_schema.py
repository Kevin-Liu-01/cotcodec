"""Tests for the shared Q1 interface in harness/q1/schema.py."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from harness.q1 import schema

SHA40 = "a" * 40
SHA64 = "b" * 64


def _substrate(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "substrate_id": "inductor-L1-19_ReLU",
        "problem_id": "L1/19_ReLU",
        "level": 1,
        "kernelbench_revision": schema.KERNELBENCH_PROBLEMS_REVISION,
        "source_kind": "inductor",
        "source_repo": "https://github.com/pytorch/pytorch",
        "source_revision": SHA40,
        "source_license": "BSD-3-Clause",
        "origin_path": "torch/_inductor/codegen/triton.py",
        "transformations": [
            {
                "name": "strip-heuristics",
                "detail": "removed triton_heuristics",
                "diff_sha256": SHA64,
            }
        ],
    }
    record.update(overrides)
    return record


def _mutation(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "mutant_id": "inductor-L1-19_ReLU.m0001",
        "parent_substrate_id": "inductor-L1-19_ReLU",
        "operator": "relu-fmax-zero-remove",
        "family": "semantic",
        "site": "kernel.py:41:12",
        "seed": 42,
        "triton_disable_line_info": True,
        "dedup_hash": SHA64,
    }
    record.update(overrides)
    return record


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "kernel_id": "inductor-L1-19_ReLU",
        "gate": "a",
        "config_id": "native/trials-5/seed-42",
        "verdict": "accept",
        "max_abs_err": 0.0,
        "max_rel_err": 0.0,
        "tolerance": 1e-2,
        "tf32_policy": "torch-default",
        "gpu_seconds": 1.5,
        "wall_seconds": 2.0,
        "details": {"trials": 5},
    }
    row.update(overrides)
    return row


def test_problem_ids_round_trip() -> None:
    assert schema.problem_id_from_path("KernelBench/level1/19_ReLU.py") == "L1/19_ReLU"
    assert schema.parse_problem_id("L2/12_Gemm_Multiply_LeakyReLU") == (
        2,
        12,
        "Gemm_Multiply_LeakyReLU",
    )
    assert schema.problem_relpath("L1/4_Matrix_vector_multiplication_") == (
        "level1/4_Matrix_vector_multiplication_.py"
    )
    for bad in ("L1-19_ReLU", "L9/1_X", "level1/19_ReLU", "L1/ReLU"):
        with pytest.raises(schema.SchemaError):
            schema.parse_problem_id(bad)
    with pytest.raises(schema.SchemaError):
        schema.problem_id_from_path("other/19_ReLU.py")


def test_valid_substrate_and_tamper_cases() -> None:
    assert schema.validate_substrate(_substrate())["level"] == 1
    tampered = [
        _substrate(level=2),
        _substrate(level=True),
        _substrate(kernelbench_revision=schema.KERNELBENCH_GATE_A_REVISION),
        _substrate(source_kind="kernelbench-m"),
        _substrate(source_license="none"),
        _substrate(source_revision="abc1234"),
        _substrate(origin_path="/home/someone/x.py"),
        _substrate(origin_path="../x.py"),
        _substrate(substrate_id="bad/id"),
        _substrate(transformations=["strip"]),
        _substrate(transformations=[{"name": "x"}]),
        _substrate(extra_field=1),
    ]
    for record in tampered:
        with pytest.raises(schema.SchemaError):
            schema.validate_substrate(record)
    missing = _substrate()
    del missing["origin_path"]
    with pytest.raises(schema.SchemaError, match="missing keys"):
        schema.validate_substrate(missing)


def test_mutation_validation() -> None:
    assert schema.validate_mutation(_mutation(rule_origin="paper"))["family"] == "semantic"
    for record in (
        _mutation(triton_disable_line_info=False),
        _mutation(family="concurrency"),
        _mutation(site="kernel.py:0:1"),
        _mutation(site="kernel.py:12"),
        _mutation(seed=-1),
        _mutation(seed=True),
        _mutation(dedup_hash="B" * 64),
        _mutation(mutant_id="inductor-L1-19_ReLU"),
        _mutation(rule_origin="cuda"),
    ):
        with pytest.raises(schema.SchemaError):
            schema.validate_mutation(record)


def test_verdict_rows_are_strict_json() -> None:
    line = schema.dump_verdict_row(_row())
    assert line.endswith("\n")
    assert json.loads(line)["gate"] == "a"
    for row in (
        _row(verdict="pass"),
        _row(max_abs_err=math.inf),
        _row(max_rel_err=-1.0),
        _row(tf32_policy="tf32"),
        _row(gpu_seconds=None),
        _row(details=[]),
        _row(details={"x": math.nan}),
        _row(config_id=""),
        _row(attempt=0),
        _row(unknown=1),
    ):
        with pytest.raises(schema.SchemaError):
            schema.validate_verdict_row(row)
    with pytest.raises(schema.SchemaError):
        schema.validate_verdict_row(_row(gate="zz"), known_gates_only=True)
    assert schema.validate_verdict_row(_row(gate="zz"))["gate"] == "zz"


def test_make_verdict_row_maps_nonfinite_errors_to_null() -> None:
    row = schema.make_verdict_row(
        kernel_id="k1",
        gate="A1",
        config_id="native/seed-42",
        verdict="reject",
        tf32_policy="tf32-admissible",
        max_abs_err=math.inf,
        max_rel_err=math.nan,
        tolerance=1e-6,
        seed=42,
    )
    assert row["max_abs_err"] is None and row["max_rel_err"] is None
    assert row["details"]["nonfinite"] == ["max_abs_err", "max_rel_err"]
    assert row["seed"] == 42


def _write_dir(root: Path, name: str, files: dict[str, object]) -> Path:
    path = root / name
    path.mkdir()
    (path / "kernel.py").write_text("class ModelNew: ...\n", encoding="utf-8")
    for filename, content in files.items():
        (path / filename).write_text(json.dumps(content), encoding="utf-8")
    return path


def test_kernel_directories(tmp_path: Path) -> None:
    _write_dir(tmp_path, "inductor-L1-19_ReLU", {"substrate.json": _substrate()})
    _write_dir(
        tmp_path,
        "inductor-L1-19_ReLU.m0001",
        {"substrate.json": _substrate(), "mutation.json": _mutation()},
    )
    _write_dir(
        tmp_path,
        "ctl-identity-L1-19_ReLU",
        {
            "control.json": {
                "control_id": "ctl-identity-L1-19_ReLU",
                "problem_id": "L1/19_ReLU",
                "level": 1,
                "kernelbench_revision": schema.KERNELBENCH_PROBLEMS_REVISION,
                "control_kind": "reference-identity",
                "expected": {"a": "accept", "b1": "reject"},
                "source_repo": "https://github.com/ScalingIntelligence/KernelBench",
                "source_revision": schema.KERNELBENCH_PROBLEMS_REVISION,
                "source_license": "MIT",
                "origin_path": "KernelBench/level1/19_ReLU.py",
            }
        },
    )
    loaded = {item.kernel_id: item.kind for item in schema.iter_kernel_dirs(tmp_path)}
    assert loaded == {
        "ctl-identity-L1-19_ReLU": "control",
        "inductor-L1-19_ReLU": "substrate",
        "inductor-L1-19_ReLU.m0001": "mutant",
    }
    wrong_name = _write_dir(tmp_path, "renamed", {"substrate.json": _substrate()})
    with pytest.raises(schema.SchemaError, match="directory name"):
        schema.load_kernel_dir(wrong_name)
    wrong_parent = _write_dir(
        tmp_path,
        "x.m0002",
        {
            "substrate.json": _substrate(substrate_id="other"),
            "mutation.json": _mutation(mutant_id="x.m0002"),
        },
    )
    with pytest.raises(schema.SchemaError, match="parent"):
        schema.load_kernel_dir(wrong_parent)


def test_read_verdict_rows_rejects_torn_lines(tmp_path: Path) -> None:
    path = tmp_path / "v.jsonl"
    path.write_text(schema.dump_verdict_row(_row()) + '{"kernel_id": "k', encoding="utf-8")
    with pytest.raises(schema.SchemaError, match="not JSON"):
        schema.read_verdict_rows(path)
