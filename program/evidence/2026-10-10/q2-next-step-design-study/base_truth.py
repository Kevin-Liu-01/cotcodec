"""Population truth on S1a's 32 base tasks, the analysis set of the K32 designs (A, A6), for each
passing calibration and scenario. The design runs report the truth over all 113 pool tasks; a
K32 design reads only the base, whose posterior share is lower.

Run from the repository root (CPU, deterministic: the posterior bank uses seed 42):
    PYTHONPATH=. python program/evidence/2026-10-10/q2-next-step-design-study/base_truth.py \
        > program/evidence/2026-10-10/q2-next-step-design-study/base-truth.json
The scenario specs (lam for piM / pi2M, c for null) are the ones the design runs resolved, read
from each calibration's merged ``designs-<calibration>.json`` (``scenario_spec``).
"""
import json
import subprocess
from pathlib import Path

from harness.q2_design import data as D
from harness.q2_design import model as M
from harness.q2_design import successor as SU

N = Path("program/evidence/2026-10-10/q2-next-step-design-study")
E = Path("program/evidence/2026-10-10/q2-design-study")
CAL = {"P0": (E / "fit-pool.json", []), "PR": (N / "fit-pool-rhob0.json", []),
       "P4": (N / "fit-pool-4b0.json", []), "P4sf": (N / "fit-pool-4b0.json", ["sigma_f=1.0"])}
s1a = D.load()
out = {"git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                  text=True).stdout.strip(), "calibrations": {}}
for name, (fit, setp) in CAL.items():
    _, params, bank = SU.load_calibration(str(fit), setp, s1a)
    cells = json.loads((N / f"designs-{name}.json").read_text())["cells"]
    sub = dict(bank)
    sub["eta0"], sub["beta"] = bank["eta0"][:32], bank["beta"][:32]
    out["calibrations"][name] = {}
    for sc in ("fitted", "piM", "null", "pi2M"):
        scen = M.Scenario(**cells[f"A6-K32-S6R2|{sc}"]["scenario_spec"])
        pb = M.population(params, scen, source="pool", bank=sub)
        pa = M.population(params, scen, source="pool", bank=bank)
        out["calibrations"][name][sc] = {
            "base32": {"pi_small": pb["pi_small"], "pi_4B": pb["4B"]["pi"],
                       "pi_9B": pb["9B"]["pi"], "delta_pooled": pb["delta_pooled"]},
            "pool113": {"pi_small": pa["pi_small"], "pi_4B": pa["4B"]["pi"],
                        "pi_9B": pa["9B"]["pi"], "delta_pooled": pa["delta_pooled"]}}
print(json.dumps(out, indent=1))
