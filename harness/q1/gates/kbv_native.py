"""``c1_kbv_native``: run UNMODIFIED KernelBench-Verified's hidden check (fidelity only).

Acceptance criterion 1 (preregistration section 8.2) requires gate (c1) in
KBV-compatibility mode to agree with KBV@3fdf6fec ``run_hidden_correctness_check``
on KBV's own problem copy. This module runs that upstream function from a clone
outside the repository (``KBV_SRC`` or an explicit path; MIT, but kept out of
the repository like the other fidelity references) and turns its verdict into
rows. Nothing it returns feeds a ladder gate.

What runs upstream, unmodified: ``src/eval.py`` (loaded from the clone by path,
under a private package name), its ``load_original_model_and_inputs``,
``set_seed``, ``_process_input_tensor``, ``get_hidden_test_path`` and
``run_hidden_correctness_check``, KBV's own ``KernelBench/levelN`` problem copy
and its ``hidden_tests/levelN/<n>_hidden.py`` file.

Two documented adaptations, neither of which touches upstream code:

- ``src/eval.py`` imports its sibling ``utils``, which imports LLM clients
  (together, openai, google-genai, anthropic) and transformers for generation
  helpers, and registers the ``torch.rand_mix`` aliases. The evaluation path
  uses none of them, so a stub ``utils`` module (``read_file`` only) stands in.
  KBV's ``src/__init__.py`` is not executed.
- KBV's ``load_custom_model`` ``exec``s the candidate string, which cannot host
  ``@triton.jit`` (Triton reads the function source). The candidate is loaded
  with the harness's file-backed loader (KernelBench's tempfile loader for the
  Triton backend), then constructed exactly as KBV's ``eval_kernel_against_ref``
  constructs it (``set_seed(seed)``, ``ModelNew(*init_inputs)``). The reference
  is loaded with KBV's own loader.

Model construction mirrors KBV's ``eval_kernel_against_ref`` line by line, and
``run_hidden_correctness_check`` is called right after it (KBV calls it after
the standard trials; the fidelity target is the hidden check itself, and the
harness's ``c1_kbv_compat`` draws from the same RNG position, so both runs see
byte-identical hidden inputs when the problem copies agree).
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

from harness.q1.gates.outcome import GateOutcome, exception_details
from harness.q1.schema import KBV_REVISION, parse_problem_id

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = "_q1_kbv_upstream"


class NativeKbvError(RuntimeError):
    """Raised when the KBV clone is missing, misplaced or at the wrong revision."""


def clone_revision(clone: Path) -> str | None:
    """Git HEAD of the clone (only when the clone is the repository top level),
    or the ``REVISION`` file of an exported tree."""
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                "safe.directory=*",
                "-C",
                str(clone),
                "rev-parse",
                "--show-toplevel",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        toplevel, head = completed.stdout.split()
        if Path(toplevel).resolve() == clone.resolve():
            return head
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    marker = clone / "REVISION"
    return marker.read_text(encoding="utf-8").strip() if marker.is_file() else None


def resolve_clone(path: str | os.PathLike[str] | None = None) -> Path:
    raw = path if path is not None else os.environ.get("KBV_SRC")
    if not raw:
        raise NativeKbvError("set KBV_SRC to an unmodified kernel_bench_verified clone")
    clone = Path(raw).resolve()
    if clone == REPO_ROOT or REPO_ROOT in clone.parents:
        raise NativeKbvError("the KBV clone must live outside this repository")
    if not (clone / "src" / "eval.py").is_file() or not (clone / "hidden_tests").is_dir():
        raise NativeKbvError(f"{clone} is not a kernel_bench_verified checkout")
    revision = clone_revision(clone)
    if revision != KBV_REVISION:
        raise NativeKbvError(f"KBV clone is at {revision}, expected {KBV_REVISION}")
    return clone


def load_upstream_eval(clone: Path) -> types.ModuleType:
    """Load ``src/eval.py`` unmodified, with a stub sibling ``utils``."""
    name = f"{PACKAGE}.eval"
    if name in sys.modules:
        return sys.modules[name]
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(clone / "src")]  # type: ignore[attr-defined]
    sys.modules[PACKAGE] = package
    utils = types.ModuleType(f"{PACKAGE}.utils")

    def read_file(file_path: str) -> str:  # KBV utils.read_file semantics
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist")
            return ""
        with open(file_path) as handle:
            return handle.read()

    utils.read_file = read_file  # type: ignore[attr-defined]
    sys.modules[f"{PACKAGE}.utils"] = utils
    package.utils = utils  # type: ignore[attr-defined]
    spec = importlib.util.spec_from_file_location(name, clone / "src" / "eval.py")
    if spec is None or spec.loader is None:
        raise NativeKbvError("cannot load KBV src/eval.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def kbv_problem_path(clone: Path, problem_id: str) -> Path:
    level, number, name = parse_problem_id(problem_id)
    return clone / "KernelBench" / f"level{level}" / f"{number}_{name}.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_kbv_native(
    problem_id: str,
    kernel_source: str,
    *,
    clone: str | os.PathLike[str] | None = None,
    seed: int = 42,
    device: Any = None,
    ours_problem_source: str | None = None,
) -> list[GateOutcome]:
    """Per-config rows (``kbv/config_<i>``) and an ``aggregate`` row, gate ``c1_kbv_native``."""
    import torch

    from harness.q1.gates.common import load_candidate, resolve_device

    start = time.perf_counter()
    dev = resolve_device(device)
    root = resolve_clone(clone)
    upstream = load_upstream_eval(root)
    level, number, _ = parse_problem_id(problem_id)
    problem_path = kbv_problem_path(root, problem_id)
    hidden = upstream.get_hidden_test_path(level, number)
    details: dict[str, Any] = {
        "kbv_revision": KBV_REVISION,
        "seed": seed,
        "kbv_problem_sha256": _sha256(problem_path) if problem_path.is_file() else None,
        "hidden_test_sha256": _sha256(Path(hidden)) if hidden else None,
        "adaptations": ["stub-utils", "file-backed-candidate-loader"],
    }
    if ours_problem_source is not None and problem_path.is_file():
        theirs = problem_path.read_text(encoding="utf-8")
        details["kbv_problem_equals_ours_after_header"] = _strip_header(theirs) == (
            ours_problem_source
        )
    if hidden is None or not problem_path.is_file():
        details["reason"] = "no-kbv-hidden-test" if hidden is None else "no-kbv-problem"
        return [
            GateOutcome(
                "c1_kbv_native",
                "aggregate",
                "error",
                details=details,
                wall_seconds=time.perf_counter() - start,
            )
        ]
    precision = torch.float32
    if dev.type == "cuda":
        torch.cuda.set_device(dev)
    context: dict[str, Any] = {}
    Model, get_init_inputs, _ = upstream.load_original_model_and_inputs(
        problem_path.read_text(encoding="utf-8"), context
    )
    upstream.set_seed(seed)
    init_inputs = [upstream._process_input_tensor(x, dev, precision) for x in get_init_inputs()]
    with torch.no_grad():
        upstream.set_seed(seed)
        original = Model(*init_inputs)
    loaded = load_candidate(kernel_source)
    metadata: dict[str, Any] = {}
    try:
        with torch.no_grad():
            upstream.set_seed(seed)
            custom = loaded.model_class(*init_inputs)
            original = original.to(device=dev, dtype=precision)
            custom = custom.to(device=dev, dtype=precision)
        # Nothing may draw from the RNG between construction and the hidden
        # check (KBV's get_hidden_inputs draws every config back to back), so
        # the config count comes from the committed table parsed from the same
        # hidden-test files, cross-checked against KBV's own pass message.
        n_configs = _expected_configs(problem_id)
        try:
            passed = upstream.run_hidden_correctness_check(
                original, custom, hidden, metadata=metadata, device=dev, precision=precision
            )
            raised = None
        except Exception as exc:  # KBV marks the sample failed and moves on
            passed, raised = False, exc
    finally:
        loaded.cleanup()
    failed = set(metadata.get("hidden_failed_configs", []))
    trials = str(metadata.get("hidden_correctness_trials", ""))
    if trials.startswith("(") and "/" in trials:
        reported = int(trials[1:].split("/", 1)[0])
        if reported != n_configs:
            details["config_count_mismatch"] = {"table": n_configs, "kbv": reported}
            n_configs = reported
    rows = []
    for index in range(1, n_configs + 1):
        label = f"config_{index}"
        rows.append(
            GateOutcome(
                "c1_kbv_native",
                f"kbv/{label}",
                "reject" if label in failed or raised is not None else "accept",
                tolerance=upstream.get_tolerance_for_precision(precision),
                details={"label": label},
            )
        )
    details.update(
        {
            "configs": n_configs,
            "failed_configs": sorted(failed),
            "metadata": {key: str(value)[:500] for key, value in metadata.items()},
        }
    )
    if raised is not None:
        details.update({"reason": "upstream-raised", **exception_details(raised)})
    rows.append(
        GateOutcome(
            "c1_kbv_native",
            "aggregate",
            "accept" if passed else "reject",
            tolerance=upstream.get_tolerance_for_precision(precision),
            details=details,
            wall_seconds=time.perf_counter() - start,
        )
    )
    return rows


def _expected_configs(problem_id: str) -> int:
    from harness.q1.gates.gate_c import kbv_configs

    labels = kbv_configs()["problems"].get(problem_id, {}).get("configs", ["D1", "D2", "D3", "D4"])
    return len(labels)


def _strip_header(text: str) -> str:
    """KBV prepends a 6-line Meta licence header to KernelBench problem files."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# Copyright (c) Meta Platforms"):
        return "".join(lines[6:])
    return text


__all__ = [
    "NativeKbvError",
    "kbv_problem_path",
    "load_upstream_eval",
    "resolve_clone",
    "run_kbv_native",
]
