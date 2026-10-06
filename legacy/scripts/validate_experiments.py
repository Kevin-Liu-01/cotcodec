"""Validate experiment YAML files against the current harness schema."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.config import ExperimentConfig  # noqa: E402


def main() -> int:
    experiment_dir = Path("experiments")
    paths = sorted(experiment_dir.glob("*.yaml"))
    if not paths:
        print("No experiment YAML files found.")
        return 1

    print("Experiment validation")
    print("=====================")

    for path in paths:
        config = ExperimentConfig.from_yaml(path)
        print(f"\n{path}")
        print(f"  benchmark: {config.benchmark}")
        print(f"  tasks: {config.tasks}")
        print(f"  seeds: {config.seeds}")
        print(f"  run_specs: {len(config.iter_run_specs())}")
        for run_spec in config.iter_run_specs():
            conditions = ", ".join(condition.value for condition in run_spec.conditions)
            print(
                f"    - group={run_spec.group} model={run_spec.model} "
                f"conditions=[{conditions}]"
            )

    print("\nAll experiment YAMLs parsed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
