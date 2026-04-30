"""YAML loading helpers with a zero-network fallback.

The project expects PyYAML, but some bare environments do not have it. When
that happens, fall back to Ruby's stdlib YAML parser rather than blocking basic
config validation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - env-specific fallback
    yaml = None


def load_yaml_file(path: str | Path) -> Any:
    """Load YAML from disk.

    Preferred path: PyYAML. Fallback path: Ruby stdlib YAML -> JSON.
    """
    path = Path(path)

    if yaml is not None:
        with open(path) as f:
            return yaml.safe_load(f)

    command = [
        "ruby",
        "-e",
        (
            "require 'yaml'; "
            "require 'json'; "
            "data = YAML.safe_load(File.read(ARGV[0]), permitted_classes: [], aliases: false); "
            "print JSON.generate(data)"
        ),
        str(path),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout or "null")
