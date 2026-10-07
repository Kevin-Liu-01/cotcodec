"""Shared Q1 interfaces: substrate, mutant and control layouts, and verdict rows.

This file is binding on all three Q1 component owners (core, mutator,
substrates). It is written by the core owner and copied verbatim into the
other branches. Do not edit it in a component branch; record a needed change
as an open issue for the core owner instead.

It has no third-party dependencies (no torch, no numpy), so every component
and every CPU doctor can import it.

Layouts
-------

A **substrate** is a directory ``<root>/<substrate_id>/`` holding

- ``kernel.py``: defines ``class ModelNew`` whose constructor arguments and
  ``forward`` arguments match the KernelBench problem's ``Model``;
- ``substrate.json``: :data:`SUBSTRATE_REQUIRED_KEYS` (see
  :func:`validate_substrate`).

A **mutant** is the same layout plus ``mutation.json``
(:data:`MUTATION_REQUIRED_KEYS`). The mutant directory is named after its
``mutant_id``; its ``substrate.json`` is the parent's file copied byte for
byte, so ``substrate.json["substrate_id"] == mutation.json["parent_substrate_id"]``.

A **control** (core-owned positive controls such as the reference ``Model``
re-exported as ``ModelNew``) is a directory with ``kernel.py`` and
``control.json`` (:data:`CONTROL_REQUIRED_KEYS`). Controls are not substrates
and never enter false-reject-rate denominators.

Verdict rows
------------

Every gate and audit channel writes JSONL rows with exactly the keys in
:data:`VERDICT_REQUIRED_KEYS` plus any of :data:`VERDICT_OPTIONAL_KEYS`.
Floats are finite or ``null``; a non-finite error is recorded as ``null`` with
the reason in ``details``. Rows are serialised with :func:`dump_verdict_row`
(sorted keys, ``allow_nan=False``).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "q1-schema/1"

# --- Pinned upstream revisions -------------------------------------------------

#: KernelBench revision the problems (``Model``, ``get_inputs``) come from.
KERNELBENCH_PROBLEMS_REVISION = "423217d9fda91e0c2d67e4a43bf62f96f6d104f1"
#: KernelBench revision whose ``src/eval.py`` gate (a) follows (1e-2, integer
#: dtypes preserved; the parent of PR #80's ``2c3dbda``).
KERNELBENCH_GATE_A_REVISION = "44130946562d633cfb8e893986c5762a609c551c"
#: KernelGYM revision whose released hacking check gate (b) reimplements.
KERNELGYM_REVISION = "3a84417f8c0efaadb215ef638b37d12e71ed20f3"
#: KernelBench-Verified revision whose hidden transforms gate (c1) follows.
KBV_REVISION = "3fdf6fec7372a4d0cb682635f00e7bdcbc55d50e"
#: lethe revision whose contract checks A5 reimplements.
LETHE_REVISION = "eaff0bb6bd6d3a1c510fa7b4708ceb0f07a5ac9e"
#: KernelBench-M revision (read-only reference; no licence, never vendored).
KERNELBENCH_M_REVISION = "d04d6fc72504750804c4f4b45b4a8d7dc7c1880d"

# --- Closed vocabularies -------------------------------------------------------

SOURCE_KINDS = ("inductor", "flaggems", "liger", "triton-tutorial")
#: Licences admissible for substrates and controls in this MIT repository.
SOURCE_LICENSES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause")
MUTATION_FAMILIES = (
    "arithmetic",
    "indexing",
    "semantic",
    "boundary",
    "synchronization",
    "precision",
)
#: ``paper`` = a KernelBench-M / 2609.22220 rule ported to Triton;
#: ``triton-only`` = an extension with no CUDA counterpart.
RULE_ORIGINS = ("paper", "triton-only")
VERDICTS = ("accept", "reject", "error", "timeout", "refuse")
#: ``torch-default`` = the process's untouched torch flags (matmul TF32 off,
#: cuDNN TF32 on in torch 2.11); gates (a)-(c) run here because upstream
#: code never sets them. The audit records one of the two D14 policies.
TF32_POLICIES = ("tf32-admissible", "strict-fp32", "torch-default", "not-applicable")
CONTROL_KINDS = (
    "reference-identity",
    "kernelbench-adversarial",
    "hack-emulating-mutant",
    "synthetic",
)

#: Gate and audit-channel identifiers known to the core owner. Rows may use
#: other ids matching :data:`GATE_ID_RE` unless ``known_gates_only`` is set.
KNOWN_GATES = (
    # gate (a) and its secondaries
    "a",
    "a_head_1e-4",
    "a_head_1e-2",
    "a_static",
    "a_1e-3",
    # gate (b) = a and b1 and b2; b_native is the unmodified upstream run
    "b",
    "b1",
    "b2",
    "b_native",
    # gate (c) = b and c1 and c2 and c3, plus secondaries
    "c",
    "c1",
    "c2",
    "c3",
    "c_1e-2",
    "c_kbv_raw",
    "c_lite",
    "validity",
    # independent audit channels and tiers
    "A1",
    "A1_strict",
    "A2",
    "A3",
    "A4",
    "A5",
    "audit_N",
    "audit_G",
    "audit_G_strict",
    "audit_c_disjoint",
    # substrate admission (substrate owner)
    "admission_hook",
    "admission_audit",
)

# --- Identifier grammar --------------------------------------------------------

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
#: ``L1/19_ReLU``; the name part is the KernelBench file stem.
PROBLEM_ID_RE = re.compile(r"^L([1-4])/([0-9]+)_([A-Za-z0-9_.-]+)$")
#: Directory-safe ids for substrates, mutants and controls.
KERNEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
GATE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@+-]{0,63}$")
CONFIG_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@+/=:,-]{0,199}$")
#: ``kernel.py:41:12``: relative file, 1-based line, 0-based column.
SITE_RE = re.compile(r"^([A-Za-z0-9_./-]+):([1-9][0-9]*):([0-9]+)$")
OPERATOR_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")

SUBSTRATE_REQUIRED_KEYS = (
    "substrate_id",
    "problem_id",
    "level",
    "kernelbench_revision",
    "source_kind",
    "source_repo",
    "source_revision",
    "source_license",
    "origin_path",
    "transformations",
)
#: ``files``: list of {path, sha256} for every file in the directory except
#: substrate.json itself; ``notes``: free text; ``schema_version``.
SUBSTRATE_OPTIONAL_KEYS = ("files", "notes", "schema_version")
#: Each transformation records one normalisation step applied to upstream code.
TRANSFORMATION_REQUIRED_KEYS = ("name", "detail")
TRANSFORMATION_OPTIONAL_KEYS = ("diff_sha256",)

MUTATION_REQUIRED_KEYS = (
    "mutant_id",
    "parent_substrate_id",
    "operator",
    "family",
    "site",
    "seed",
    "triton_disable_line_info",
    "dedup_hash",
)
MUTATION_OPTIONAL_KEYS = ("rule_origin", "kernelbench_m_rule", "description", "schema_version")

CONTROL_REQUIRED_KEYS = (
    "control_id",
    "problem_id",
    "level",
    "kernelbench_revision",
    "control_kind",
    "expected",
    "source_repo",
    "source_revision",
    "source_license",
    "origin_path",
)
CONTROL_OPTIONAL_KEYS = ("notes", "schema_version")

VERDICT_REQUIRED_KEYS = (
    "kernel_id",
    "gate",
    "config_id",
    "verdict",
    "max_abs_err",
    "max_rel_err",
    "tolerance",
    "tf32_policy",
    "gpu_seconds",
    "wall_seconds",
    "details",
)
#: ``seed``: input seed of the scoring replicate (42/43/44);
#: ``run_id``: journal run id; ``attempt``: 1-based retry index after an
#: infrastructure failure; ``code_sha256``: sha256 of the gate implementation.
VERDICT_OPTIONAL_KEYS = ("schema_version", "seed", "run_id", "attempt", "code_sha256")


class SchemaError(ValueError):
    """Raised when a record does not satisfy the shared Q1 interface."""


# --- Helpers -------------------------------------------------------------------


def canonical_json(value: Any) -> str:
    """Sorted-key, compact, strict JSON (no NaN or infinity)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def problem_id_from_path(path: str) -> str:
    """``level1/19_ReLU.py`` (or ``.../KernelBench/level1/19_ReLU.py``) -> ``L1/19_ReLU``."""
    parts = PurePosixPath(path).parts
    if len(parts) < 2 or not parts[-1].endswith(".py"):
        raise SchemaError(f"not a KernelBench problem path: {path!r}")
    match = re.fullmatch(r"level([1-4])", parts[-2])
    if not match:
        raise SchemaError(f"not a KernelBench problem path: {path!r}")
    problem_id = f"L{match.group(1)}/{parts[-1][:-3]}"
    parse_problem_id(problem_id)
    return problem_id


def parse_problem_id(problem_id: str) -> tuple[int, int, str]:
    """Return ``(level, number, name)`` for ``L1/19_ReLU``."""
    if not isinstance(problem_id, str):
        raise SchemaError("problem_id must be a string")
    match = PROBLEM_ID_RE.fullmatch(problem_id)
    if not match:
        raise SchemaError(f"problem_id {problem_id!r} must look like 'L1/19_ReLU'")
    return int(match.group(1)), int(match.group(2)), match.group(3)


def problem_relpath(problem_id: str) -> str:
    """``L1/19_ReLU`` -> ``level1/19_ReLU.py`` inside ``KernelBench/``."""
    level, number, name = parse_problem_id(problem_id)
    return f"level{level}/{number}_{name}.py"


def _require_keys(
    record: Mapping[str, Any], required: Iterable[str], optional: Iterable[str], what: str
) -> None:
    if not isinstance(record, Mapping):
        raise SchemaError(f"{what} must be a JSON object")
    required = tuple(required)
    allowed = set(required) | set(optional)
    missing = [key for key in required if key not in record]
    if missing:
        raise SchemaError(f"{what} missing keys: {', '.join(missing)}")
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise SchemaError(f"{what} has unknown keys: {', '.join(unknown)}")


def _require_str(record: Mapping[str, Any], key: str, what: str) -> str:
    value = record[key]
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{what}.{key} must be a non-empty string")
    return value


def _require_relpath(value: str, what: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or value.startswith("~"):
        raise SchemaError(f"{what} must be a relative POSIX path without '..': {value!r}")


def _check_provenance(record: Mapping[str, Any], what: str) -> None:
    level, _, _ = parse_problem_id(record["problem_id"])
    if record["level"] != level or isinstance(record["level"], bool):
        raise SchemaError(f"{what}.level must equal the problem_id level ({level})")
    if record["kernelbench_revision"] != KERNELBENCH_PROBLEMS_REVISION:
        raise SchemaError(f"{what}.kernelbench_revision must be {KERNELBENCH_PROBLEMS_REVISION}")
    _require_str(record, "source_repo", what)
    if not HEX40_RE.fullmatch(str(record["source_revision"])):
        raise SchemaError(f"{what}.source_revision must be a full 40-hex git SHA")
    if record["source_license"] not in SOURCE_LICENSES:
        raise SchemaError(f"{what}.source_license must be one of {SOURCE_LICENSES}")
    _require_relpath(_require_str(record, "origin_path", what), f"{what}.origin_path")


# --- Validators ----------------------------------------------------------------


def validate_substrate(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a ``substrate.json`` object and return a plain-dict copy."""
    what = "substrate.json"
    _require_keys(record, SUBSTRATE_REQUIRED_KEYS, SUBSTRATE_OPTIONAL_KEYS, what)
    if not KERNEL_ID_RE.fullmatch(str(record["substrate_id"])):
        raise SchemaError(f"{what}.substrate_id {record['substrate_id']!r} is not directory-safe")
    if record["source_kind"] not in SOURCE_KINDS:
        raise SchemaError(f"{what}.source_kind must be one of {SOURCE_KINDS}")
    _check_provenance(record, what)
    transformations = record["transformations"]
    if not isinstance(transformations, list):
        raise SchemaError(f"{what}.transformations must be a list")
    for index, step in enumerate(transformations):
        label = f"{what}.transformations[{index}]"
        _require_keys(step, TRANSFORMATION_REQUIRED_KEYS, TRANSFORMATION_OPTIONAL_KEYS, label)
        _require_str(step, "name", label)
        _require_str(step, "detail", label)
        if "diff_sha256" in step and not HEX64_RE.fullmatch(str(step["diff_sha256"])):
            raise SchemaError(f"{label}.diff_sha256 must be 64 lowercase hex characters")
    if "files" in record:
        files = record["files"]
        if not isinstance(files, list):
            raise SchemaError(f"{what}.files must be a list")
        for index, entry in enumerate(files):
            label = f"{what}.files[{index}]"
            _require_keys(entry, ("path", "sha256"), (), label)
            _require_relpath(_require_str(entry, "path", label), f"{label}.path")
            if not HEX64_RE.fullmatch(str(entry["sha256"])):
                raise SchemaError(f"{label}.sha256 must be 64 lowercase hex characters")
    if "schema_version" in record and record["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"{what}.schema_version must be {SCHEMA_VERSION}")
    return dict(record)


def validate_mutation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a ``mutation.json`` object and return a plain-dict copy."""
    what = "mutation.json"
    _require_keys(record, MUTATION_REQUIRED_KEYS, MUTATION_OPTIONAL_KEYS, what)
    for key in ("mutant_id", "parent_substrate_id"):
        if not KERNEL_ID_RE.fullmatch(str(record[key])):
            raise SchemaError(f"{what}.{key} {record[key]!r} is not directory-safe")
    if record["mutant_id"] == record["parent_substrate_id"]:
        raise SchemaError(f"{what}.mutant_id must differ from parent_substrate_id")
    if not OPERATOR_RE.fullmatch(str(record["operator"])):
        raise SchemaError(f"{what}.operator must be kebab/snake case, at most 80 characters")
    if record["family"] not in MUTATION_FAMILIES:
        raise SchemaError(f"{what}.family must be one of {MUTATION_FAMILIES}")
    site = SITE_RE.fullmatch(str(record["site"]))
    if not site:
        raise SchemaError(f"{what}.site must look like 'kernel.py:41:12'")
    _require_relpath(site.group(1), f"{what}.site file")
    seed = record["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise SchemaError(f"{what}.seed must be a non-negative integer")
    if record["triton_disable_line_info"] is not True:
        raise SchemaError(f"{what}.triton_disable_line_info must be true")
    if not HEX64_RE.fullmatch(str(record["dedup_hash"])):
        raise SchemaError(f"{what}.dedup_hash must be 64 lowercase hex characters")
    if "rule_origin" in record and record["rule_origin"] not in RULE_ORIGINS:
        raise SchemaError(f"{what}.rule_origin must be one of {RULE_ORIGINS}")
    if "kernelbench_m_rule" in record and record["kernelbench_m_rule"] is not None:
        _require_str(record, "kernelbench_m_rule", what)
    if "schema_version" in record and record["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"{what}.schema_version must be {SCHEMA_VERSION}")
    return dict(record)


def validate_control(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a ``control.json`` object and return a plain-dict copy.

    ``expected`` maps gate ids to the verdict the control must receive, for
    example ``{"a": "accept", "b1": "reject"}``.
    """
    what = "control.json"
    _require_keys(record, CONTROL_REQUIRED_KEYS, CONTROL_OPTIONAL_KEYS, what)
    if not KERNEL_ID_RE.fullmatch(str(record["control_id"])):
        raise SchemaError(f"{what}.control_id {record['control_id']!r} is not directory-safe")
    if record["control_kind"] not in CONTROL_KINDS:
        raise SchemaError(f"{what}.control_kind must be one of {CONTROL_KINDS}")
    _check_provenance(record, what)
    expected = record["expected"]
    if not isinstance(expected, Mapping) or not expected:
        raise SchemaError(f"{what}.expected must be a non-empty object")
    for gate, verdict in expected.items():
        if not GATE_ID_RE.fullmatch(str(gate)):
            raise SchemaError(f"{what}.expected has an invalid gate id {gate!r}")
        if verdict not in VERDICTS:
            raise SchemaError(f"{what}.expected[{gate!r}] must be one of {VERDICTS}")
    if "schema_version" in record and record["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"{what}.schema_version must be {SCHEMA_VERSION}")
    return dict(record)


def _optional_nonneg_float(row: Mapping[str, Any], key: str) -> None:
    value = row[key]
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SchemaError(f"verdict.{key} must be a number or null")
    if not math.isfinite(value) or value < 0:
        raise SchemaError(f"verdict.{key} must be finite and non-negative (use null)")


def validate_verdict_row(
    row: Mapping[str, Any], *, known_gates_only: bool = False
) -> dict[str, Any]:
    """Validate one verdict row and return a plain-dict copy."""
    _require_keys(row, VERDICT_REQUIRED_KEYS, VERDICT_OPTIONAL_KEYS, "verdict")
    if not KERNEL_ID_RE.fullmatch(str(row["kernel_id"])):
        raise SchemaError(f"verdict.kernel_id {row['kernel_id']!r} is not a valid id")
    gate = str(row["gate"])
    if not GATE_ID_RE.fullmatch(gate):
        raise SchemaError(f"verdict.gate {gate!r} is not a valid gate id")
    if known_gates_only and gate not in KNOWN_GATES:
        raise SchemaError(f"verdict.gate {gate!r} is not in KNOWN_GATES")
    if not isinstance(row["config_id"], str) or not CONFIG_ID_RE.fullmatch(row["config_id"]):
        raise SchemaError(f"verdict.config_id {row['config_id']!r} is not a valid config id")
    if row["verdict"] not in VERDICTS:
        raise SchemaError(f"verdict.verdict must be one of {VERDICTS}")
    for key in ("max_abs_err", "max_rel_err", "tolerance"):
        _optional_nonneg_float(row, key)
    if row["tf32_policy"] not in TF32_POLICIES:
        raise SchemaError(f"verdict.tf32_policy must be one of {TF32_POLICIES}")
    for key in ("gpu_seconds", "wall_seconds"):
        value = row[key]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise SchemaError(f"verdict.{key} must be a number")
        if not math.isfinite(value) or value < 0:
            raise SchemaError(f"verdict.{key} must be finite and non-negative")
    if not isinstance(row["details"], Mapping):
        raise SchemaError("verdict.details must be a JSON object")
    try:
        canonical_json(row["details"])
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"verdict.details is not strict JSON: {exc}") from exc
    if "seed" in row and (not isinstance(row["seed"], int) or isinstance(row["seed"], bool)):
        raise SchemaError("verdict.seed must be an integer")
    if "attempt" in row and (
        not isinstance(row["attempt"], int)
        or isinstance(row["attempt"], bool)
        or row["attempt"] < 1
    ):
        raise SchemaError("verdict.attempt must be a positive integer")
    if "code_sha256" in row and not HEX64_RE.fullmatch(str(row["code_sha256"])):
        raise SchemaError("verdict.code_sha256 must be 64 lowercase hex characters")
    if "schema_version" in row and row["schema_version"] != SCHEMA_VERSION:
        raise SchemaError(f"verdict.schema_version must be {SCHEMA_VERSION}")
    return dict(row)


def finite_or_none(value: float | None) -> float | None:
    """Map NaN and infinities to ``None`` so a row stays strict JSON."""
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def make_verdict_row(
    *,
    kernel_id: str,
    gate: str,
    config_id: str,
    verdict: str,
    tf32_policy: str,
    max_abs_err: float | None = None,
    max_rel_err: float | None = None,
    tolerance: float | None = None,
    gpu_seconds: float = 0.0,
    wall_seconds: float = 0.0,
    details: Mapping[str, Any] | None = None,
    **optional: Any,
) -> dict[str, Any]:
    """Build and validate a verdict row; non-finite errors become ``null``.

    When an error value is non-finite, ``details["nonfinite"]`` lists the
    affected keys so the information is not lost.
    """
    detail_map = dict(details or {})
    nonfinite = [
        key
        for key, value in (("max_abs_err", max_abs_err), ("max_rel_err", max_rel_err))
        if value is not None and not math.isfinite(float(value))
    ]
    if nonfinite:
        detail_map["nonfinite"] = sorted(set(detail_map.get("nonfinite", [])) | set(nonfinite))
    row: dict[str, Any] = {
        "kernel_id": kernel_id,
        "gate": gate,
        "config_id": config_id,
        "verdict": verdict,
        "max_abs_err": finite_or_none(max_abs_err),
        "max_rel_err": finite_or_none(max_rel_err),
        "tolerance": finite_or_none(tolerance),
        "tf32_policy": tf32_policy,
        "gpu_seconds": float(gpu_seconds),
        "wall_seconds": float(wall_seconds),
        "details": detail_map,
    }
    row.update(optional)
    return validate_verdict_row(row)


def dump_verdict_row(row: Mapping[str, Any]) -> str:
    """Validate and serialise one row as a JSONL line (with trailing newline)."""
    return canonical_json(validate_verdict_row(row)) + "\n"


def read_verdict_rows(path: Path) -> list[dict[str, Any]]:
    """Read and validate a verdict JSONL file. A torn final line is an error."""
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"{path}:{number}: not JSON: {exc}") from exc
        try:
            rows.append(validate_verdict_row(row))
        except SchemaError as exc:
            raise SchemaError(f"{path}:{number}: {exc}") from exc
    return rows


# --- Kernel directories --------------------------------------------------------


@dataclass(frozen=True)
class KernelDir:
    """A validated substrate, mutant or control directory."""

    kind: str  # "substrate" | "mutant" | "control"
    kernel_id: str
    path: Path
    problem_id: str
    substrate: dict[str, Any] | None
    mutation: dict[str, Any] | None
    control: dict[str, Any] | None

    @property
    def kernel_path(self) -> Path:
        return self.path / "kernel.py"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaError(f"{path.name} must hold a JSON object")
    return value


def load_kernel_dir(path: Path) -> KernelDir:
    """Validate ``path`` as a substrate, mutant or control directory."""
    path = Path(path)
    if not (path / "kernel.py").is_file():
        raise SchemaError(f"{path.name}: kernel.py is missing")
    control_file = path / "control.json"
    substrate_file = path / "substrate.json"
    mutation_file = path / "mutation.json"
    if control_file.exists():
        if substrate_file.exists() or mutation_file.exists():
            raise SchemaError(f"{path.name}: a control must not carry substrate or mutation files")
        control = validate_control(_load_json(control_file))
        if control["control_id"] != path.name:
            raise SchemaError(f"{path.name}: directory name must equal control_id")
        return KernelDir("control", path.name, path, control["problem_id"], None, None, control)
    if not substrate_file.exists():
        raise SchemaError(f"{path.name}: substrate.json is missing")
    substrate = validate_substrate(_load_json(substrate_file))
    if mutation_file.exists():
        mutation = validate_mutation(_load_json(mutation_file))
        if mutation["mutant_id"] != path.name:
            raise SchemaError(f"{path.name}: directory name must equal mutant_id")
        if mutation["parent_substrate_id"] != substrate["substrate_id"]:
            raise SchemaError(
                f"{path.name}: substrate.json must be the parent's (parent_substrate_id mismatch)"
            )
        return KernelDir(
            "mutant", path.name, path, substrate["problem_id"], substrate, mutation, None
        )
    if substrate["substrate_id"] != path.name:
        raise SchemaError(f"{path.name}: directory name must equal substrate_id")
    return KernelDir("substrate", path.name, path, substrate["problem_id"], substrate, None, None)


def iter_kernel_dirs(root: Path) -> list[KernelDir]:
    """Load every kernel directory directly under ``root``, sorted by id."""
    root = Path(root)
    return [
        load_kernel_dir(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and not child.name.startswith(".")
    ]


__all__ = [
    "CONTROL_KINDS",
    "KBV_REVISION",
    "KERNELBENCH_GATE_A_REVISION",
    "KERNELBENCH_M_REVISION",
    "KERNELBENCH_PROBLEMS_REVISION",
    "KERNELGYM_REVISION",
    "KNOWN_GATES",
    "KernelDir",
    "LETHE_REVISION",
    "MUTATION_FAMILIES",
    "RULE_ORIGINS",
    "SCHEMA_VERSION",
    "SOURCE_KINDS",
    "SOURCE_LICENSES",
    "SchemaError",
    "TF32_POLICIES",
    "VERDICTS",
    "canonical_json",
    "dump_verdict_row",
    "finite_or_none",
    "iter_kernel_dirs",
    "load_kernel_dir",
    "make_verdict_row",
    "parse_problem_id",
    "problem_id_from_path",
    "problem_relpath",
    "read_verdict_rows",
    "sha256_bytes",
    "sha256_file",
    "validate_control",
    "validate_mutation",
    "validate_substrate",
    "validate_verdict_row",
]
