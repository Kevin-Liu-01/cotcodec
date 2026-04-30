"""Check whether the local environment is ready for CoTCodec harness work."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(frozen=True)
class DependencyCheck:
    name: str
    kind: str
    required_for: str


PYTHON_MODULES = [
    DependencyCheck("yaml", "python", "native YAML parsing"),
    DependencyCheck("rich", "python", "rich terminal output"),
    DependencyCheck("tiktoken", "python", "token fertility measurement"),
    DependencyCheck("numpy", "python", "degradation statistics"),
    DependencyCheck("scipy", "python", "McNemar/Fisher significance tests"),
    DependencyCheck("pandas", "python", "trace analysis"),
]

EXECUTABLES = [
    DependencyCheck("ruby", "exec", "YAML fallback parser"),
    DependencyCheck("pdflatex", "exec", "paper compilation"),
]


def check_python_module(name: str) -> bool:
    return find_spec(name) is not None


def check_executable(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    print("CoTCodec harness environment check")
    print("================================")

    missing_core: list[str] = []

    print("\nPython modules")
    for dep in PYTHON_MODULES:
        ok = check_python_module(dep.name)
        status = "OK" if ok else "MISSING"
        print(f"- {dep.name:8} {status:7} {dep.required_for}")
        if not ok and dep.name in {"numpy", "pandas", "scipy", "tiktoken"}:
            missing_core.append(dep.name)

    print("\nExecutables")
    for dep in EXECUTABLES:
        ok = check_executable(dep.name)
        status = "OK" if ok else "MISSING"
        print(f"- {dep.name:8} {status:7} {dep.required_for}")

    print("\nReadiness")
    yaml_ok = check_python_module("yaml") or check_executable("ruby")
    print(f"- config parsing: {'ready' if yaml_ok else 'blocked'}")
    print("- canary smoke runs: ready")
    print(
        f"- full stats stack: {'ready' if not missing_core else 'blocked'}"
        + ("" if not missing_core else f" (missing: {', '.join(sorted(missing_core))})")
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
