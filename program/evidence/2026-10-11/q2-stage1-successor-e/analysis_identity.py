"""E's registered analysis is S1a's estimators and rules, and the design study's power path.

CPU only, seeded, at the registered 10,000 resamples and 10,000 flips. Two checks:

1. On S1a's own records (``a1.jsonl``), ``harness.q2_stage1e.analysis.analyse_array``
   reproduces S1a's committed registered readings (``report-guarded.json``): the primary set
   (32 base tasks) and the registered secondary set (113 tasks), every estimate S1a reports
   that E's analysis also computes, the delta paired t, the X sign-flip and label-permutation
   p-values, the session sign-flip test, DR2 and DR5.
2. On simulated E data (S = 4, R = 1, both sizes, 113 tasks; seeds 42, 43, 44), it gives the
   same p_X, pi_small bounds, delta, DR2 and DR5 as ``harness.q2_design.analyse.analyse``, the
   function the design study's operating characteristics for E were computed with.

Usage, from the repository root::

    python program/evidence/2026-10-11/q2-stage1-successor-e/analysis_identity.py --out OUT.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from harness.q2_design import analyse as DA  # noqa: E402
from harness.q2_design import data as D  # noqa: E402
from harness.q2_stage1e import analysis as AE  # noqa: E402

SETS = {"primary": "y_base", "secondary_base_plus_completed_extension": "y_pool"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_s1a(s1a: D.S1aData, report: dict) -> dict:
    out = {}
    for name, attr in SETS.items():
        mine = AE.analyse_array(getattr(s1a, attr))
        theirs = report[name]
        shared = [k for k in mine["estimates"] if k in theirs["estimates"]]
        differ = [k for k in shared if mine["estimates"][k] != theirs["estimates"][k]]
        tests = {
            "delta_paired_t": mine["tests"]["delta_paired_t"] == theirs["tests"]["delta_paired_t"],
            "x_signflip_p": mine["tests"]["x_signflip_p"] == theirs["tests"]["x_signflip_p"],
            "x_label_permutation_p_sensitivity": (
                mine["tests"]["x_label_permutation_p_sensitivity"]
                == theirs["tests"]["x_label_permutation_p_sensitivity"]
            ),
            "session_signflip_p": (
                mine["tests"]["session_signflip_p_by_pair"]["E1-E2"]
                == theirs["tests"]["session_signflip_p"]
            ),
            "delta_session_heterogeneity": (
                mine["delta_session_heterogeneity_by_pair"]["E1-E2"]
                == theirs["delta_session_heterogeneity"]
            ),
            "success_by_size_harness": (
                mine["success_by_size_harness"] == theirs["success_by_size_harness"]
            ),
            "DR1_drop_4B": mine["DR1_drop_4B"] == theirs["DR1_drop_4B"],
        }
        out[name] = {
            "tasks": mine["tasks"],
            "estimates_compared": len(shared),
            "estimates_differing": differ,
            "tests_equal": tests,
            "DR2_equal": mine["DR2"]["class"] == theirs["DR2"]["class"],
            "DR5_equal": mine["DR5"]["outcome"] == theirs["DR5"]["outcome"],
            "readings": {"DR2": mine["DR2"]["class"], "DR5": mine["DR5"]["outcome"],
                         "p_x": mine["tests"]["x_signflip_p"],
                         "pi_small_one_sided_95": mine["estimates"]["pi_small"]["one_sided_95"]},
        }  # fmt: skip
    return out


def compare_design_study(seeds=(42, 43, 44)) -> dict:
    out = {}
    for seed in seeds:
        rng = np.random.default_rng([seed, 99])
        logit = rng.normal(-1.0, 2.0, size=(1, 2, 113, 1, 1, 1)) + rng.normal(
            0, 0.8, size=(1, 2, 113, 2, 1, 1)
        )
        y = (rng.random((1, 2, 113, 2, 4, 1)) < 1 / (1 + np.exp(-logit))).astype(float)
        mine = AE.analyse_array(y[0])
        theirs = DA.analyse(y, ("4B", "9B"), rng=np.random.default_rng(AE.SEED))
        lb, ub = mine["estimates"]["pi_small"]["one_sided_95"]
        out[str(seed)] = {
            "p_x": [mine["tests"]["x_signflip_p"], float(theirs["p_x"][0])],
            "pi_small_bounds": [[lb, ub], [float(theirs["pi_small_lb"][0]),
                                           float(theirs["pi_small_ub"][0])]],
            "DR2": [mine["DR2"]["class"], str(theirs["dr2"][0])],
            "DR5": [mine["DR5"]["outcome"], str(theirs["dr5"][0])],
            "equal": (
                mine["tests"]["x_signflip_p"] == float(theirs["p_x"][0])
                and [lb, ub] == [float(theirs["pi_small_lb"][0]), float(theirs["pi_small_ub"][0])]
                and mine["DR2"]["class"] == str(theirs["dr2"][0])
                and mine["DR5"]["outcome"] == str(theirs["dr5"][0])
            ),
        }  # fmt: skip
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    s1a = D.load(ROOT)
    report = json.loads((ROOT / D.REPORT).read_text(encoding="utf-8"))
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        head = None
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", "harness", "scripts", "program"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    out = {
        "method": __doc__,
        "n_boot": AE.N_BOOT,
        "n_randomization": AE.N_RANDOMIZATION,
        "s1a_committed_readings": compare_s1a(s1a, report),
        "design_study_analyse_at_S4_R1": compare_design_study(),
        "inputs": {str(D.RECORDS): sha256(ROOT / D.RECORDS),
                   str(D.REPORT): sha256(ROOT / D.REPORT)},
        "provenance": {"git_head": head, "tree_dirty": bool(dirty),
                       "python": platform.python_version(), "numpy": np.__version__,
                       "argv": sys.argv},
    }  # fmt: skip
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: {n: (v["estimates_differing"], v["tests_equal"], v["DR2_equal"],
                              v["DR5_equal"]) for n, v in out[k].items()}
                      for k in ("s1a_committed_readings",)}, indent=1))  # fmt: skip
    print(json.dumps({s: v["equal"] for s, v in out["design_study_analyse_at_S4_R1"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
