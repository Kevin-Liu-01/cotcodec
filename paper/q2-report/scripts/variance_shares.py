"""Probability-scale variance shares under the design study's calibrations (model-based).

    PYTHONPATH=. python paper/q2-report/scripts/variance_shares.py \
        > paper/q2-report/data/variance-shares.json

The shares of N0 (`fit-base`), P0 (`fit-pool`), PR (`fit-pool-rhob0`) and P4 (`fit-pool-4b0`)
are read from each committed fit's `prob_scale_components`. P4sf is P4 with sigma_f = 1.0 in
both sizes (the design study's definition, `successor.override(params, ["sigma_f=1.0"])`).
No committed file holds its shares, so they are computed here with the committed function
`model.prob_scale_components` and its defaults (4,000 tasks x 400 sessions, seed 42), after
checking that the same call reproduces P4's committed shares. CPU only, about a minute.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from harness.q2_design import model as M
from harness.q2_design import study as ST
from harness.q2_design.successor import override

DS1 = Path("program/evidence/2026-10-10/q2-design-study")
DS2 = Path("program/evidence/2026-10-10/q2-next-step-design-study")
COMMITTED = {
    "N0": DS1 / "fit-base.json",
    "P0": DS1 / "fit-pool.json",
    "PR": DS2 / "fit-pool-rhob0.json",
    "P4": DS2 / "fit-pool-4b0.json",
}


def rounded(components: dict) -> dict:
    return {z: {k: round(v, 4) for k, v in components[z]["shares"].items()} for z in M.SIZES}


def main() -> int:
    out: dict = {"source": {k: str(v) for k, v in COMMITTED.items()}, "shares": {}}
    for name, path in COMMITTED.items():
        fit = json.loads(path.read_text())
        out["shares"][name] = rounded(fit["prob_scale_components"])
    fit, params = ST.load_fit(COMMITTED["P4"])
    check = M.prob_scale_components(params)
    for z in M.SIZES:
        for key, value in check[z]["shares"].items():
            stored = fit["prob_scale_components"][z]["shares"][key]
            if abs(value - stored) > 2e-6:
                raise SystemExit(f"P4 not reproduced: {z} {key} {value} != {stored}")
    out["P4_reproduced"] = True
    out["shares"]["P4sf"] = rounded(M.prob_scale_components(override(params, ["sigma_f=1.0"])))
    out["source"]["P4sf"] = f"{COMMITTED['P4']} with sigma_f=1.0 (computed here)"
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
