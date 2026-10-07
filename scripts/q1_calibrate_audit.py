#!/usr/bin/env python3
"""Calibrate the audit multiplier M on S1 calibration substrates and freeze audit v1 (prereg 6.1).

    python scripts/q1_calibrate_audit.py --journal CAL/journal.jsonl --corpus SUBSTRATES \\
        --output CAL/audit-v1.json

The journal holds the calibration run's A1 rows (replicate 42, default M = 16)
for the admitted S1 calibration-half substrates. The output names M, whether
it was raised, every substrate's status and required multiplier, the fault
candidates to adjudicate, and the audit version record
(``tiers.audit_version_hash``) that every later audit row must match. Rules:
``harness/q1/audit/calibration.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1 import analysis  # noqa: E402
from harness.q1.audit.calibration import calibrate  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    table = analysis.kernel_table(args.corpus)
    split = analysis.s1_split()
    result = calibrate(Journal(args.journal).final_rows(), table, split["calibration"])
    result["s1_split_sha256"] = split["sha256"]
    args.output.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(
        json.dumps(
            {
                "multiplier": result["multiplier"],
                "raised": result["multiplier_raised"],
                "counts": result["counts"],
                "audit_version_sha256": result["audit_version"]["audit_version_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
