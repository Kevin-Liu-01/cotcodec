"""E's episode entry point: S1a's episode driver with E's record labels.

The episode container runs ``python -m harness.q2_stage1e.driver --config /out/config.json``.
It runs ``harness.q2_stage1.driver.main`` unchanged (OSWorld setup, the guard warm-up, the
settles, the harness clients through the certified IR and executor, ``DesktopEnv.evaluate()``,
the D53 (iii) observation rule and the capture). The one difference: S1a's driver checks its
finished record with S1a's ``records.validate``, which accepts only sessions S1 and S2, so
here that check is ``harness.q2_stage1e.records.validate`` (E's sessions E1-E4 and rerun 1,
then S1a's ``validate`` on every other field). Nothing else in the episode changes.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from harness.q2_stage1 import driver as D1
from harness.q2_stage1e import records as RE


def use_e_labels() -> None:
    """Make S1a's driver check its record with E's ``validate`` (the driver looks the
    name up in its module at call time)."""
    D1.validate = RE.validate


def main(argv: Sequence[str] | None = None) -> int:
    use_e_labels()
    return D1.main(list(argv) if argv is not None else sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
