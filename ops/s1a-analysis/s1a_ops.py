"""Shared helpers of the S1a analysis operator scripts (D59). Not code of record.

Every script here imports the frozen modules of ``q2-stage1-rescoped-v1`` from a read-only
export of the freeze commit (``--export``, a ``git archive`` of ``d5f5798``) and calls them
unchanged. Nothing here edits, copies or re-implements a registered estimator, rule or set
definition: the scripts only call the registered functions, add the operator steps D59 (iii)
names, and record what they did. They run on the host's system ``python3`` (3.10, numpy 1.21,
scipy 1.8) with ``-E -s -B``, so they use the standard library and numpy only and keep to
Python 3.10 syntax.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import platform
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

FREEZE_COMMIT = "d5f57988ab94e0c098feddb744b78b73b5ad88ca"
REGISTRATION = "program/preregistrations/q2-stage1-rescoped-v1.md"
REGISTRATION_SHA256 = "f9db7cc38c4954b3144ac5a1afaf7bf5366449081b06c80bf89888bdf653afd8"
PLAN_PATH = "program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json"
PLAN_SHA256 = "6a3f0219448301d95a80d443ed75892eaac093e42349ef98fb985a5d87467d51"
PLAN_FILE_SHA256 = "a5f0aadce1208d9d9ab31ff572ca93e624dbd87e1b50dd194987ff8cc46e1806"
# G0 item 12: the GLMM image and the SHA-256 of its package lock /opt/q2/r-packages.json.
GLMM_IMAGE_ID = "sha256:b15584f3954f1c83fc3e5067e29c57c5c55e3b2a50ef28e4e68a394e595aabed"
R_PACKAGES_SHA256 = "abb8871de4549732cd396dc60fc1f2aec78bf1fffad788cb841e8bf61668bfc7"
# Section 4: the checker-mutation study's metric image (offline rescoring runs in it, G0 item 6).
METRIC_IMAGE_ID = "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230"
SCHEMA = "q2-s1a-ops-v1"


class OpsError(SystemExit):
    """An input outside what the operator step accepts; the step writes nothing."""


def use_export(export: str | Path) -> Path:
    """Put the export of the freeze commit first on ``sys.path`` and check that
    ``harness.q2_stage1`` is imported from it (never from another tree)."""
    root = Path(export).resolve()
    if not (root / "harness" / "q2_stage1" / "analysis.py").is_file():
        raise OpsError(f"{root} is not an export of the freeze commit (no harness/q2_stage1)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module("harness.q2_stage1.analysis")
    loaded = Path(str(module.__file__)).resolve()
    if root not in loaded.parents:
        raise OpsError(f"harness.q2_stage1 was imported from {loaded}, not from {root}")
    return root


def frozen(name: str) -> ModuleType:
    """One frozen module of ``harness.q2_stage1`` (after ``use_export``)."""
    return importlib.import_module(f"harness.q2_stage1.{name}")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dumps(value: Any) -> str:
    """The frozen report's serialisation (``analysis.main``)."""
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def write_new(path: str | Path, text: str) -> Path:
    """Write once: an operator output is never overwritten (as the frozen CLIs refuse)."""
    out = Path(path)
    if out.exists():
        raise OpsError(f"{out} exists; operator outputs are never overwritten")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def labels_from_guard(path: str | Path) -> dict[str, Any]:
    """The labels every analysis output carries (D59 (ii): incomplete; section 15: "not
    externally anchored"), read from ``run_report.py``'s ``guard.json`` so that an output
    written after the report carries the same labels as the report.

    ``run_report.py`` writes ``guard.json`` last, and names ``report-guarded.json`` in it only
    when the report step succeeded. A missing guard (the report job still running) or one
    without ``guarded_report`` (the report step failed: a stop condition) is refused, so a
    later step started too early writes nothing."""
    guard_path = Path(path)
    if not guard_path.is_file():
        raise OpsError(
            f"{guard_path} does not exist: the report step (run_report.py) has not finished; "
            "wait until its log ends with exit_status=0"
        )
    guard = read_json(guard_path)
    labels = guard.get("labels")
    if not isinstance(labels, dict) or "incomplete" not in labels:
        raise OpsError(f"{path} carries no labels block (it is not run_report.py's guard.json)")
    if not isinstance(guard.get("guarded_report"), dict):
        raise OpsError(f"{path} names no guarded report: the report step failed (a stop condition)")
    return {**labels, "source": f"guard.json (sha256 {sha256_file(path)})"}


def a1_job_of(run_dir: Path) -> str:
    """The A1 job a lane run directory holds, from its manifest (as ``rules.run_dir_dr0``)."""
    manifest = read_json(run_dir / "manifest.json")
    if manifest.get("purpose") != "a1":
        raise OpsError(f"{run_dir}: not an A1 run directory (purpose {manifest.get('purpose')!r})")
    a1 = manifest.get("a1") or {}
    return f"A1-{a1.get('size')}-{a1.get('session')}"


def run_dirs_by_job(run_dirs: Iterable[str | Path]) -> dict[str, Path]:
    """job -> lane run directory, one per A1 job that ran (an error on a duplicate job)."""
    out: dict[str, Path] = {}
    for item in run_dirs:
        run_dir = Path(item)
        job = a1_job_of(run_dir)
        if job in out:
            raise OpsError(f"{job} is named by two run directories: {out[job]} and {run_dir}")
        out[job] = run_dir
    return out


def episode_dir(run_dir: Path, record: Mapping[str, Any]) -> Path:
    """An attempt's directory in its own job's run directory (``rescore.main``'s naming:
    the slot id ``<job>:<block>:<index>`` with ``:`` as ``_``, then ``.a<attempt>``)."""
    return run_dir / "episodes" / f"{str(record['slot']).replace(':', '_')}.a{record['attempt']}"


def versions() -> dict[str, Any]:
    """Interpreter and library versions (no host name)."""
    out: dict[str, Any] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
    }
    for name in ("numpy", "scipy"):
        try:
            out[name] = importlib.import_module(name).__version__
        except ImportError:
            out[name] = None
    return out


def ops_files() -> dict[str, str]:
    """SHA-256 of every operator script in this directory (part of the provenance)."""
    here = Path(__file__).resolve().parent
    return {
        path.name: sha256_file(path)
        for path in sorted(here.iterdir())
        if path.is_file() and path.suffix in (".py", ".md", ".sbatch", ".sh")
    }
