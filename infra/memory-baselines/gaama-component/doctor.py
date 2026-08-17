#!/usr/bin/env python3
"""Contained entrypoint for the model-free GAAMA component falsifier."""

from __future__ import annotations

import json

from harness.memory_trials.gaama_component import run_component_doctor


def main() -> int:
    print(json.dumps(run_component_doctor(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
