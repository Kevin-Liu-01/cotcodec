#!/usr/bin/env python3
"""Contained entrypoint for the natural held-out GAAMA graph falsifier."""

from __future__ import annotations

import json
from pathlib import Path

from harness.memory_trials.gaama_natural import run_natural_holdout


def main() -> int:
    dataset = Path("/opt/gaama-source/evals/locomo/locomo10.json")
    print(json.dumps(run_natural_holdout(dataset), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
