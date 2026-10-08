"""Version card of the Q1 Stage 0 stack: what the preregistration freezes.

Pure Python (no torch, no Triton). Each component gets a SHA-256 over its
source files (relative POSIX path and file SHA-256, in sorted order), plus the
identifiers its own owner already records:

- ``schema``: ``harness/q1/schema.py`` (binding on all components);
- ``gate_code``: gates (a)-(c), problem access, shape rules, runner, worker,
  journal, timing and the reference store (``refstore.py``, decision D31);
- ``gate_data``: the vendored KernelBench files, problem hashes, KBV
  configuration table and committed shape manifest;
- ``audit_code``: :data:`harness.q1.audit.tiers.AUDIT_FILES`, the files
  :func:`~harness.q1.audit.tiers.audit_version_hash` freezes as audit v1 after
  calibration (that hash also folds in the calibrated multiplier, so it can only
  be computed at calibration time);
- ``analysis``: the analysis module, the report script that computes every
  preregistered metric, and the audit-hole replay and calibration drivers;
- ``driver``: what decides what Stage 0 scores and how it runs (second review):
  the trimming rule and its sampler (``trim.py``), the reference-item schedule
  (``refschedule.py``, decision D31), the pilot module whose size rules it uses
  (``pilot.py``: watchdog limits, the exclusive class), the cost card that
  projects it (``cost_card.py`` and its script), the Stage 0, pilot and re-pilot
  drivers with the re-pilot rule (``repilot.py``) and corpus script, and the
  pilot-records script that lists the pilot-exposed kernels;
- ``mutator``: the mutator's own ``package_sha256`` and operator
  ``registry_fingerprint`` (both recorded in every corpus manifest);
- ``substrates``: the substrate package with its vendored S2 sources, the
  builder version strings and the frozen S1 split.

``scripts/q1_version_card.py`` prints the card; ``tests/test_q1_integration.py``
fails when the preregistration draft names other values, so the draft cannot
silently drift from the code it will freeze. The worker writes the matching
``code_sha256`` (gate or audit code) on every verdict row.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

Q1_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Q1_ROOT.parents[1]
CARD_SCHEMA = "q1-version-card/2"

#: Gate implementation and the execution path every gate row goes through.
GATE_CODE_PATHS = (
    "__init__.py",
    "problems.py",
    "shapes.py",
    "journal.py",
    "runner.py",
    "worker.py",
    "timing.py",
    "versions.py",
    "controls.py",
    "refstore.py",
    "gates",
)
#: Data the gates read: vendored KernelBench, problem hashes, KBV and shape tables.
GATE_DATA_PATHS = ("data", "third_party")
#: Metric definitions (relative to the project root).
ANALYSIS_PATHS = (
    "harness/q1/analysis.py",
    "scripts/report_q1_stage0.py",
    "scripts/q1_audit_hole_replay.py",
    "scripts/q1_calibrate_audit.py",
)
#: Substrate builders and their vendored upstream sources.
SUBSTRATE_PATHS = ("substrates",)
#: The Stage 0 plan and execution (relative to the project root).
DRIVER_PATHS = (
    "harness/q1/trim.py",
    "harness/q1/refschedule.py",
    "harness/q1/pilot.py",
    "harness/q1/cost_card.py",
    "harness/q1/data/pilot_exposed.json",
    "scripts/run_q1_stage0.py",
    "scripts/run_q1_gpu_pilot.py",
    "harness/q1/repilot.py",
    "scripts/run_q1_repilot.py",
    "scripts/q1_prepare_repilot_corpus.py",
    "scripts/q1_pilot_cost_card.py",
    "scripts/q1_pilot_records.py",
)


def _files(root: Path, entries: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for entry in entries:
        path = root / entry
        if path.is_dir():
            files.extend(
                p
                for p in path.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and not any(part.startswith(".") for part in p.relative_to(root).parts)
                and p.suffix not in {".pyc", ".pyo"}
            )
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"version card input {path} is missing")
    return sorted(set(files))


def tree_sha256(root: Path, entries: Iterable[str]) -> str:
    """SHA-256 over (relative path, file SHA-256) of every file under ``entries``."""
    digest = hashlib.sha256()
    for path in _files(root, entries):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()


def gate_code_sha256() -> str:
    return tree_sha256(Q1_ROOT, GATE_CODE_PATHS)


def audit_code_sha256() -> str:
    from harness.q1.audit.tiers import AUDIT_FILES

    return tree_sha256(Q1_ROOT, AUDIT_FILES)


@lru_cache(maxsize=4)
def row_code_sha256(gate: str) -> str:
    """``code_sha256`` for a verdict row: audit code for audit channels and the
    audit-hole replay, else gate code."""
    audit = gate.startswith(("A", "ref_A")) or gate == "audit_hole"
    return audit_code_sha256() if audit else gate_code_sha256()


def version_card() -> dict[str, Any]:
    """Every identifier the Stage 0 preregistration names (see the module docstring)."""
    from harness.q1 import problems, trim
    from harness.q1.mutate.corpus import package_sha256
    from harness.q1.mutate.operators import OPERATORS, registry_fingerprint
    from harness.q1.mutate.sampling import SPLIT_SEED, SPLIT_VERSION
    from harness.q1.schema import SCHEMA_VERSION, sha256_file
    from harness.q1.substrates import admission, inductor_convert, s2_catalog
    from harness.q1.substrates import split as s1_split

    split = s1_split.calibration_split(problems.list_problem_ids(include_excluded=True), seed=42)
    return {
        "schema": CARD_SCHEMA,
        "schema_py_sha256": sha256_file(Q1_ROOT / "schema.py"),
        "schema_version": SCHEMA_VERSION,
        "gate_code_sha256": gate_code_sha256(),
        "gate_data_sha256": tree_sha256(Q1_ROOT, GATE_DATA_PATHS),
        "shape_manifest_sha256": sha256_file(Q1_ROOT / "data" / "shape_manifest.json"),
        "audit_code_sha256": audit_code_sha256(),
        "analysis_sha256": tree_sha256(PROJECT_ROOT, ANALYSIS_PATHS),
        "driver_sha256": tree_sha256(PROJECT_ROOT, DRIVER_PATHS),
        "trim_rule": trim.RULE_VERSION,
        "mutator_package_sha256": package_sha256(),
        "mutator_registry_fingerprint": registry_fingerprint(),
        "mutator_operators": len(OPERATORS),
        "mutant_split": f"{SPLIT_VERSION}/seed={SPLIT_SEED}",
        "substrates_sha256": tree_sha256(Q1_ROOT, SUBSTRATE_PATHS),
        "substrate_builders": [
            inductor_convert.CONVERTER_VERSION,
            s2_catalog.S2_BUILD_VERSION,
            admission.ADMISSION_VERSION,
        ],
        "s2_catalog_entries": len(s2_catalog.CATALOG),
        "s1_split_sha256": split["sha256"],
        "s1_split_sizes": [len(split["calibration"]), len(split["evaluation"])],
    }


__all__ = [
    "CARD_SCHEMA",
    "audit_code_sha256",
    "gate_code_sha256",
    "row_code_sha256",
    "tree_sha256",
    "version_card",
]
