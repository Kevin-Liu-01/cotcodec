#!/usr/bin/env python3
"""Print the Q1 Stage 0 version card (``harness/q1/versions.py``) as JSON or Markdown.

The preregistration draft's "Frozen component versions" table must equal this
card; ``tests/test_q1_integration.py`` checks it. After any change to Q1 code
or data, and before the freeze, regenerate the table:

    python scripts/q1_version_card.py --markdown

Pure Python; runs without torch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.versions import version_card  # noqa: E402


def markdown(card: dict) -> str:
    lines = ["| Key | Value |", "|---|---|"]
    for key, value in card.items():
        text = json.dumps(value) if isinstance(value, list | int) else str(value)
        lines.append(f"| `{key}` | `{text}` |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--markdown", action="store_true", help="print the preregistration table")
    args = parser.parse_args(argv)
    card = version_card()
    print(markdown(card) if args.markdown else json.dumps(card, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
